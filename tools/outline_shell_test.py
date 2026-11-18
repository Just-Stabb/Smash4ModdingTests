#!/usr/bin/env python3
"""Test of tools/outline_shell_cave.py (Outline_Shell) on an executable with tools/mesh_vis_cave.py's patches
(exe_v46z_outline or the v2 mesh visibility's):

  python3 tools/outline_shell_test.py EXE.rpx

The cave's words are written into the emulated image (the file isn't patched). Run with the game's own code around
the hooks (unicorn):
  - the command tables for Outline_Shell and every earlier cave's command (Outline_Set, Mesh_Visibility included);
  - the handler on a fighter-like object: start, the colour / alpha / width (clamped) / blend kept, replace, Alpha 0
    (fade out / at once), Frames, the 17th object;
  - the tick (0x032EFB78 -> os_tick -> mesh_vis's mv_tick -> ... -> the game's screen-effect update): grow in / held /
    shrink, the pulse (outline_cave.pulse), a KO and a changed model drop the shell;
  - the FB1 unlock sites (outline_cave.py's hooks, chained): ol_apply's rim as before and the shell's colour / width /
    mark written into FB1 vec4 12-13 as apply_ref computes them, another instance's FB1 untouched;
  - CommandDrawModel's two draw calls (0x037174D8 / 0x037174E8) on a fake device context laid out as the device's code
    fills it, the game's draw and every GX2 call replaced by recorders: no shell (no mark, a stale mark with no shell
    in use, no material blocks, a geometry shader, the vertex stage's FB1 another) -> the game's draw only; a shell ->
    the game's draw, the cave's programs and states (front faces culled, depth on / write on / stencil off, the blend
    of Blend 0 / 1, blending on target 0, alpha test off), the same draw again, every state back from the caches;
    the pixel program's block table as absolute pointers or as the .gsh file's 0xD06xxxxx offsets;
  - the programs: re-assembled from their sources (when tools/latte_dis/latte-asm is built) = the cave's bytes; run by
    tools/latte_exec.py on random skinned positions / normals / matrices: = shell_ref for a pixel width, a game-unit
    width and none (compressParam on); the pixel program outputs FB1 vec4 12; the GX2 shader structs in the cave;
  - the clear (0x02FB3498 -> ... -> mv_clear -> os_clear -> 0x02FB349C): every shell off;
  - the diag build's lines (S4SC / S4SD at the command, S4ST at the tick with its counts, S4SR at a shell drawn, S4SX at
    a marked FB1 refused).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import outline_shell_cave as SC  # noqa: E402
import outline_cave as OL  # noqa: E402
import mesh_vis_cave as MV  # noqa: E402
import line_test_cave as LT  # noqa: E402
import acmd_ext_test  # noqa: E402
from acmd_ext_test import check, r32, w32, run, RET, HANDLERS  # noqa: E402
from stage_slot_test import machine  # noqa: E402
from outline_test import (table_tests, World, ensure, rf, wf, close, EARLIER, PARAMS, STATE, FLAG, FB, SMGR,  # noqa: E402
                          SREC, REG)
from ppcasm import Asm  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_5, UC_PPC_REG_6, UC_PPC_REG_7,  # noqa: E402
                               UC_PPC_REG_10, UC_PPC_REG_LR, UC_PPC_REG_CTR, UC_PPC_REG_MSR, UC_PPC_REG_PC)

ALL = dict(EARLIER, Mesh_Visibility=2500, Outline_Set=2400)
STUB = 0x04BE9800                         # the unlock stub / recorders (past the emulated code's grown end)
CTXA = 0x7F050000                         # a fake device context (0x500), its shaders and block tables after it
LOG = 0x7F058000                          # the recorders' log: count, then 0x20 a call (id, r3-r9)
GAME_VS, GAME_PS = 0x7F051000, 0x7F051200


def main():
    exe = sys.argv[1]
    orig = SC.rpx_reader(exe)
    words, lab, s = SC.build(orig)
    om, pm = machine(exe), machine(exe)
    for at, w in words.items():
        w32(pm, at, w)
    check('present() on the patched words / the unpatched exe',
          (SC.present(lambda x: words.get(x, orig(x))), SC.present(orig)), (True, False))
    check('... the mesh visibility and outline caves present in the exe it builds on',
          (MV.present(orig), OL.present(orig)), (True, True))
    try:
        SC.build(lambda x: words.get(x, orig(x)))
        check('building over itself refused', False, True)
    except AssertionError:
        check('building over itself refused', True, True)
    inside = [a for a in words if SC.CAVE <= a < SC.LIMIT]
    check('the cave inside its region (0x04BE5000-0x04BE7000), the code below the programs',
          (min(inside), max(inside) < SC.LIMIT, max(a for a in inside if a < SC.VS_PROG) < SC.VS_PROG), (SC.CAVE, True,
                                                                                                         True))
    others = sorted(a for a in words if not SC.CAVE <= a < SC.LIMIT)
    check('words outside the cave: the 2 draw calls, the FB1 hook, the tick, the clear chain\'s end, the 4 table '
          'fallbacks', others, sorted([SC.DRAW_I, SC.DRAW_N, s['fb_at'], OL.TICK_AT, s['clear_at'], s['lk_none'],
                                       s['s1'], s['s2'], s['f']]))
    check('... the draws, the FB1 hook and the tick are bl, the clear a b',
          [words[a] & 3 for a in (SC.DRAW_I, SC.DRAW_N, s['fb_at'], OL.TICK_AT, s['clear_at'])], [1, 1, 1, 1, 0])
    check('... the FB1 hook inside the outline cave (ol_fbgo\'s bl ol_apply), the tick / clear / tables chained on '
          'the mesh visibility\'s', (OL.CAVE <= s['fb_at'] < OL.LIMIT, OL.CAVE <= s['ol_apply'] < OL.LIMIT,
                                     MV.CAVE <= s['tick_prev'] < MV.LIMIT, MV.CAVE <= s['clear_at'] < MV.LIMIT,
                                     [MV.CAVE <= LT.bdecode(s[k], s[k + '_word']) < MV.LIMIT
                                      for k in ('lk_none', 's1', 's2', 'f')]), (True, True, True, True, [True] * 4))
    table_tests(pm, om, s, words, lab, 'os', SC.CMD_NAME, SC.OS_INDEX, SC.CMD_CRC, 1 + SC.NPARAMS, 'h_shell', ALL)

    pm.reg_write(UC_PPC_REG_MSR, pm.reg_read(UC_PPC_REG_MSR) | 0x2000)
    W = World(pm)
    tab, g = lab['os_tab'], lab['os_g']

    def entry(k):
        a = tab + SC.ENT * k
        return dict(acc=r32(pm, a), mi=r32(pm, a + 4), ph=r32(pm, a + 8), w=rf(pm, a + 0xC, 1)[0],
                    left=r32(pm, a + 0x18), c=rf(pm, a + 0x1C, 3), a=rf(pm, a + 0x28, 1)[0],
                    width=rf(pm, a + 0x2C, 1)[0], blend=r32(pm, a + 0x30), flash=r32(pm, a + 0x38),
                    t=r32(pm, a + 0x3C), eff=rf(pm, a + 0x40, 1)[0])

    def find_e(acc):
        for k in range(SC.N_ENT):
            if r32(pm, tab + SC.ENT * k) == acc:
                return entry(k)
        return None

    def sh(acc, target, rgb, alpha, width, frames=0, fin=0, fout=0, flash=0, blend=0, execute=1):
        w32(pm, STATE + 4, 0x1000)
        w32(pm, STATE + 8, 0xFFFFFFFF)
        pm.mem_write(FLAG + 8, bytes([execute]))
        pm.mem_write(PARAMS, struct.pack('>ifffffiiiii', target, rgb[0], rgb[1], rgb[2], alpha, width, frames, fin,
                                         fout, flash, blend))
        for r in range(14, 32):
            pm.reg_write(REG(r), 0x1000 + r)
        run(pm, lab['h_shell'], RET, {UC_PPC_REG_3: acc, UC_PPC_REG_5: STATE, UC_PPC_REG_6: FLAG,
                                       UC_PPC_REG_7: PARAMS})
        kept = [r for r in range(14, 32) if pm.reg_read(REG(r)) != 0x1000 + r]
        return dict(ret=pm.reg_read(UC_PPC_REG_3), step=r32(pm, STATE + 4) - 0x1000, kept=kept)

    ensure(pm, SMGR, SMGR + 0x1000)
    pm.mem_write(SMGR, b'\0' * 0xE80)

    def tick(n=1):
        for _ in range(n):
            pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
            pm.reg_write(UC_PPC_REG_3, SMGR)
            pm.reg_write(REG(30), 0x7F00E000)
            pm.reg_write(UC_PPC_REG_LR, RET)
            pm.emu_start(OL.TICK_AT, OL.TICK_AT + 4, count=400000)

    a0 = W.acc(0)
    r = sh(a0, 0, (255.0, 255.0, 255.0), 255.0, 1.5, frames=120)
    check('Outline_Shell(self, white, 255, Width 1.5, Frames 120): returns 2, steps 12 words, callee-saved kept',
          (r['ret'], r['step'], r['kept']), (2, 48, []))
    e = find_e(a0)
    check('... an entry for the object\'s instance, held at once (w 1), Frames 120, weight 1',
          (e['mi'], e['ph'], e['w'], e['left'], e['eff']), (W.mi(0), 2, 1.0, 120, 1.0))
    check('... colour (1, 1, 1), alpha 1, width 1.5, blend 0, no pulse',
          (e['c'], e['a'], e['width'], e['blend'], e['flash']), ([1.0, 1.0, 1.0], 1.0, 1.5, 0, 0))
    check('... entries in use 1', r32(pm, g), 1)
    sh(a0, 0, (255.0, 51.0, 0.0), 300.0, -0.5, blend=7)
    e = find_e(a0)
    check('replaced: colour (1, 0.2, 0), Alpha 300 -> 1, width -0.5 (game units) kept, Blend 7 -> 1',
          (close(e['c'], [1.0, 0.2, 0.0]), e['a'], e['width'], e['blend']), (True, 1.0, -0.5, 1))
    sh(a0, 0, (255.0, 0.0, 0.0), 127.5, 500.0)
    check('Width 500 -> 64, Alpha 127.5 -> 0.5', (find_e(a0)['width'], find_e(a0)['a']), (64.0, 0.5))
    sh(a0, 0, (255.0, 0.0, 0.0), 255.0, -100.0)
    check('Width -100 -> -64', find_e(a0)['width'], -64.0)
    r = sh(a0, 0, (0.0, 0.0, 0.0), 255.0, 3.0, execute=0)
    check('not executed (execute flag 0): stepped, nothing changed', (r['step'], find_e(a0)['width']), (48, -64.0))
    sh(a0, 0, (255.0, 255.0, 255.0), 255.0, 3.0, frames=120)
    tick(119)
    e = find_e(a0)
    check('ticks: held 119 frames, 1 left, w 1, t 119', (e['ph'], e['left'], e['w'], e['t']), (2, 1, 1.0, 119))
    check('... the game\'s screen-effect update ran (screen_invert\'s si_tick first: its winners -1)',
          (r32(pm, SMGR + 0xE6C), r32(pm, SMGR + 0xE70)), (0xFFFFFFFF, 0xFFFFFFFF))
    tick(1)
    check('... Frames over with FadeOut 0: off at once', (find_e(a0), r32(pm, g)), (None, 0))
    sh(a0, 0, (255.0, 0.0, 0.0), 255.0, 3.0, frames=3, fin=4, fout=2)
    seq = []
    for _ in range(10):
        e = find_e(a0)
        seq.append((e['ph'], round(e['w'], 4)) if e else None)
        tick(1)
    check('FadeIn 4, Frames 3, FadeOut 2: w frame by frame', seq,
          [(1, 0.0), (1, 0.25), (1, 0.5), (1, 0.75), (2, 1.0), (2, 1.0), (2, 1.0), (3, 1.0), (3, 0.5), None])
    sh(a0, 0, (0.0, 0.0, 255.0), 255.0, 3.0, fin=4)
    tick(2)
    sh(a0, 0, (0.0, 255.0, 0.0), 255.0, 3.0, fin=4)
    e = find_e(a0)
    check('a new shell on an object with one grows from where it is (w 0.5, the new colour)',
          (e['ph'], e['w'], e['c']), (1, 0.5, [0.0, 1.0, 0.0]))
    sh(a0, 0, (0.0, 0.0, 0.0), 0.0, 0.0, fout=4)
    tick(1)
    e = find_e(a0)
    check('Alpha 0 with FadeOut 4: shrinking from 0.5 (0.25 after a frame)', (e['ph'], round(e['w'], 4)), (3, 0.25))
    tick(1)
    check('... gone at 0', find_e(a0), None)
    sh(a0, 0, (255.0, 255.0, 255.0), 255.0, 3.0)
    sh(a0, 0, (0.0, 0.0, 0.0), 0.0, 3.0)
    check('Alpha 0 with FadeOut 0: off at once', (find_e(a0), r32(pm, g)), (None, 0))
    sh(a0, 0, (255.0, 0.0, 0.0), 255.0, 3.0, flash=20)
    got = []
    for t in range(1, 26):
        tick(1)
        got.append(find_e(a0)['eff'])
    check('Flash 20: the drawn weight follows outline_cave.pulse', close(got, [OL.pulse(t, 20) for t in range(1, 26)],
                                                                         1e-5), True)
    w32(pm, a0 + 0x348, OL.DEAD)
    tick(1)
    check('a KO (fighter status 0xB1) drops the shell', find_e(a0), None)
    w32(pm, a0 + 0x348, 0)
    sh(a0, 0, (255.0, 0.0, 0.0), 255.0, 3.0)
    w32(pm, a0 + 0x10C, W.mi(5))
    tick(1)
    check('the object\'s model changed: dropped', find_e(a0), None)
    w32(pm, a0 + 0x10C, W.mi(0))
    w32(pm, W.acc(3) + 0x3C, 0)
    r = sh(W.acc(3), 0, (255.0, 0.0, 0.0), 255.0, 3.0)
    check('an object with no ModelModule: nothing (stepped)', (r['step'], find_e(W.acc(3))), (48, None))
    w32(pm, W.acc(3) + 0x3C, W.acc(3) + 0x100)
    for k in range(17):
        sh(W.acc(k), 0, (255.0, 0.0, 0.0), 255.0, 3.0)
    check('17 objects: 16 entries in use, the 17th took one (round robin)',
          (r32(pm, g), find_e(W.acc(16)) is not None), (16, True))
    for k in range(SC.N_ENT):
        w32(pm, tab + SC.ENT * k, 0)
    w32(pm, g, 0)

    # ---- the FB1 unlock sites (outline_cave.py's hooks; ol_fbgo's bl ol_apply -> os_fb)
    ensure(pm, STUB, STUB + 0x1000)
    ensure(pm, SREC, SREC + 0x100)
    st = Asm(STUB)
    st.asm("""
        lis r12, 0x%X
        stw r3, 0x%X(r12)
        mflr r0
        stw r0, 0x%X(r12)
        lwz r0, 0x%X(r12)
        addi r0, r0, 1
        stw r0, 0x%X(r12)
        blr
""" % (SREC >> 16, SREC & 0xFFFF, (SREC & 0xFFFF) + 4, (SREC & 0xFFFF) + 8, (SREC & 0xFFFF) + 8))
    for i, x in enumerate(st.words()):
        w32(pm, STUB + 4 * i, x)
    run(pm, 0x02BEE84C, 0x02BEE854, {REG(7): OL.OL_INDEX, REG(29): HANDLERS, REG(12): 0x55})
    h_outline = pm.reg_read(REG(0))           # (Outline_Set's handler, through the game's table: a v1 outline too)

    def unlock(site, mi, fbuf, mreg, dreg):
        pm.mem_write(fbuf, b'\0' * 0x2A0)
        wf(pm, fbuf + OL.FRES_OFF, [0.05, 0.04, 0.03])
        w32(pm, SREC + 8, 0)
        for r in range(14, 32):
            pm.reg_write(REG(r), 0x2000 + r)
        pm.reg_write(REG(mreg), mi)
        pm.reg_write(REG(dreg), fbuf)
        pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
        pm.reg_write(UC_PPC_REG_3, 0x7F00BB00)
        pm.reg_write(UC_PPC_REG_CTR, STUB)
        pm.reg_write(UC_PPC_REG_LR, 0x12345670)
        pm.emu_start(site, site + 4, count=100000)
        kept = [r for r in range(14, 32) if r not in (mreg, dreg) and pm.reg_read(REG(r)) != 0x2000 + r]
        return dict(col=rf(pm, fbuf + SC.FB_COL, 4), width=rf(pm, fbuf + SC.FB_SHELL, 1)[0],
                    magic=r32(pm, fbuf + SC.FB_SHELL + 4), blend=r32(pm, fbuf + SC.FB_SHELL + 8),
                    weight=rf(pm, fbuf + SC.FB_SHELL + 12, 1)[0], off=rf(pm, fbuf + OL.FRES_OFF, 3),
                    seen=(r32(pm, SREC), r32(pm, SREC + 4), r32(pm, SREC + 8)), pc=pm.reg_read(UC_PPC_REG_PC),
                    sp=pm.reg_read(UC_PPC_REG_1), kept=kept)
    sites = [(OL.FB_A[0], 30, 28), (OL.FB_A[1], 30, 28), (OL.FB_B[0], 31, 27), (OL.FB_B[1], 31, 27)]
    for site, mreg, dreg in sites:
        u = unlock(site, W.mi(1), FB, mreg, dreg)
        check('FB1 unlock 0x%08X with no shell: vec4 12-13 left 0, the unlock called with the game\'s r3 / return'
              % site, (u['col'], u['width'], u['magic'], u['seen'], u['pc'], u['sp'], u['kept']),
              ([0.0] * 4, 0.0, 0, (0x7F00BB00, site + 4, 1), site + 4, 0x7F00F000, []))
    sh(W.acc(1), 0, (255.0, 128.0, 0.0), 204.0, 2.5, blend=1)
    for site, mreg, dreg in (sites[0], sites[3]):
        u = unlock(site, W.mi(1), FB, mreg, dreg)
        ref = SC.apply_ref({'rgb': (255.0, 128.0, 0.0), 'alpha': 204.0, 'width': 2.5, 'blend': 1}, 1.0)
        check('0x%08X: an orange glow (Alpha 204, Width 2.5, Blend 1): FB1 vec4 12 = colour / alpha, vec4 13 = '
              'width, the mark, blend, weight' % site,
              (close(u['col'], ref['col']), u['width'], u['magic'], u['blend'], u['weight'], u['seen'][2], u['kept']),
              (True, 2.5, SC.MAGIC, 1, 1.0, 1, []))
        u2 = unlock(site, W.mi(2), FB + 0x300, mreg, dreg)
        check('... another instance\'s FB1 untouched', (u2['col'], u2['magic']), ([0.0] * 4, 0))
    sh(W.acc(6), 0, (255.0, 0.0, 0.0), 255.0, 4.0, fin=4)
    tick(2)
    e = find_e(W.acc(6))
    u = unlock(OL.FB_A[1], W.mi(6), FB, 30, 28)
    check('a red shell half grown in (weight %.2f): the width x weight (2), the weight' % e['eff'],
          (round(u['width'], 5), round(u['weight'], 5), u['magic']), (2.0, 0.5, SC.MAGIC))
    # a v1 outline and a shell on the same instance: both written
    w32(pm, STATE + 4, 0x1000)
    w32(pm, STATE + 8, 0xFFFFFFFF)
    pm.mem_write(FLAG + 8, b'\x01')
    pm.mem_write(PARAMS, struct.pack('>ifffffiiii', 0, 255.0, 255.0, 255.0, 255.0, 0.0, 0, 0, 0, 0))
    run(pm, h_outline, RET, {UC_PPC_REG_3: W.acc(6), UC_PPC_REG_5: STATE, UC_PPC_REG_6: FLAG,
                                      UC_PPC_REG_7: PARAMS})
    u = unlock(OL.FB_B[0], W.mi(6), FB, 31, 27)
    check('Outline_Set (v1) and Outline_Shell on one model: the rim (g_fresnelOffset + 1) and the shell both written',
          (close(u['off'], [1.05, 1.04, 1.03]), u['magic']), (True, SC.MAGIC))

    # ---- CommandDrawModel's draw calls on a fake device context, the GX2 calls and the game's draw recorded
    env = DrawEnv(pm)
    ctx, draw, fbset, only_draw, C = env.ctx, env.draw, env.fbset, env.only_draw, SC.CTX

    w32(pm, g, 1)                              # a shell in use somewhere
    ctx()
    fbset(3.0, 0, magic=0)
    check('a draw whose FB1 has no mark: the game\'s draw only, as called (r3-r9), back at the call site',
          only_draw(draw()), True)
    fbset(3.0, 0)
    w32(pm, g, 0)
    check('a marked FB1 but no shell in use (stale): the game\'s draw only', only_draw(draw()), True)
    w32(pm, g, 1)
    d = draw()
    seq = [c[0] for c in d['calls']]
    want_seq = ['draw', 'SetVertexShader', 'SetPixelShader', 'SetPolygonControlReg', 'SetDepthStencilControlReg',
                'SetBlendControlReg', 'SetColorControl', 'SetAlphaTestReg', 'draw', 'SetVertexShader',
                'SetPixelShader', 'SetPolygonControlReg', 'SetDepthStencilControlReg', 'SetBlendControlReg',
                'SetColorControl', 'SetAlphaTestReg']
    check('a shell (Width 3, Blend 0): the game\'s draw, the cave\'s programs and states, the draw again, every state '
          'back', seq, want_seq)
    c = d['calls']
    check('... the same draw both times (r3-r9), back at the call site, r14-r31 and r1 kept',
          (c[0][1], c[8][1], d['pc'], d['sp'], d['kept']), (d['args'], d['args'], SC.DRAW_I + 4, 0x7F00F000, []))
    check('... the cave\'s GX2VertexShader / GX2PixelShader', (c[1][1][0], c[2][1][0]),
          (lab['os_vs'], lab['os_ps']))
    check('... rasterizer: the game\'s (cull back, face bit) with the front faces culled instead', c[3][2][0],
          (0x00080006 & ~3) | SC.CULL_FRONT)
    check('... depth: test + write on, stencil / back-face stencil off, the compare kept', c[4][2][0],
          (0xB7 & ~0x81) | 6)
    check('... blend target 0: colour x alpha over what is behind (SRC_ALPHA / INV_SRC_ALPHA), its alpha kept',
          c[5][2], (0, SC.BLEND_REG[0]))
    check('... colour control: the game\'s logic op / multi-write / buffer, blending on target 0 (mask 2 | 1)',
          c[6][1][:4], [0xCC, 3, 0, 1])
    check('... alpha test off', c[7][2], (0, 0))
    check('... back: the game\'s programs, the cached rasterizer / depth / blend target 0 / colour control / alpha '
          'test', (c[9][1][0], c[10][1][0], c[11][1][0], c[12][1][0], c[13][1][0], c[14][1][:4], c[15][1][0]),
          (GAME_VS, GAME_PS, CTXA + C['rsreg'], CTXA + C['dsreg'], CTXA + C['blend0'], [0xCC, 2, 0, 1],
           CTXA + C['atest']))
    check('... the cached values the restore reads', (c[11][2][0], c[12][2][0], c[13][2], c[15][2]),
          (0x00080006, 0xB7, (0, 0x00010101), (0x77, 0x3F000000)))
    fbset(3.0, 1)
    d = draw(SC.DRAW_N)
    check('the other call site (0x037174E8, bl 0x036F3EC8 -> the device\'s vt +0xB4 -> DrawIndexed, one instance): '
          'the same, Blend 1 adds (SRC_ALPHA / ONE)', ([x[0] for x in d['calls']] == want_seq,
                                                       d['calls'][5][2], d['calls'][0][1][6], d['pc']),
          (True, (0, SC.BLEND_REG[1]), 1, SC.DRAW_N + 4))
    fbset(3.0, 1, swapped=True)
    d = draw()
    check('the FB1 as the game leaves it at the draw (byte-swapped in place by the unlock): a shell, Blend 1 adds',
          ([x[0] for x in d['calls']] == want_seq, d['calls'][5][2]), (True, (0, SC.BLEND_REG[1])))
    fbset(3.0, 0, swapped=True)
    check('... Blend 0 over', draw()['calls'][5][2], (0, SC.BLEND_REG[0]))
    fbset(0.0, 0, swapped=True)
    check('... Width 0: the game\'s draw only', only_draw(draw()), True)
    fbset(3.0, 0, magic=0x12345678, swapped=True)
    check('... another mark: the game\'s draw only', only_draw(draw()), True)
    ctx(rs=0x00080005)
    fbset(3.0, 0)
    check('a material that culls front faces: the shell culls the back ones', draw()['calls'][3][2][0],
          (0x00080005 & ~3) | SC.CULL_BACK)
    ctx(rs=0x00080004)
    check('a two-sided material (no culling): front faces culled', draw()['calls'][3][2][0], 0x00080005)
    ctx(rel=True)
    check('the pixel program\'s block table as the .gsh file\'s offsets (0xD06xxxxx from the struct): a shell',
          [x[0] for x in draw()['calls']], want_seq)
    refused = r32(pm, g + 0x1C)
    ctx(blk=((7, 0x2A0),))
    check('a pixel program without the material block (4): the game\'s draw only', only_draw(draw()), True)
    ctx(blk=((4, 0x40), (7, 0x100)))
    check('... FB1 at 7 of another size: the game\'s draw only', only_draw(draw()), True)
    check('... (refusals are counted in the diag build only)', r32(pm, g + 0x1C) - refused, 0)
    ctx(gs=0x7F052300)
    check('a geometry shader in use: the game\'s draw only', only_draw(draw()), True)
    ctx(vfb=FB + 0xC00)
    check('the vertex stage\'s FB1 another: the game\'s draw only', only_draw(draw()), True)
    ctx()
    fbset(0.0, 0)
    check('Width 0 (shrunk away): the game\'s draw only', only_draw(draw()), True)
    fbset(-0.5, 0)
    check('a game-unit width (-0.5): a shell', [x[0] for x in draw()['calls']], want_seq)
    w32(pm, g, 0)

    # ---- the programs
    progs_tests(pm, lab)

    # ---- the clear
    sh(W.acc(2), 0, (255.0, 0.0, 0.0), 255.0, 3.0)
    for r in range(14, 32):
        pm.reg_write(REG(r), 0x4000 + r)
    pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
    pm.reg_write(UC_PPC_REG_3, 0x7F00BB00)
    pm.reg_write(UC_PPC_REG_10, 0x10)
    pm.reg_write(UC_PPC_REG_LR, RET)
    ensure(pm, 0x102F7020, 0x102F7024)
    check('before the clear: shells in use', r32(pm, g) > 0, True)
    pm.emu_start(OL.SLOW_CLEAR, OL.CLEAR_BACK, count=400000)
    check('clear (training reset / match start / end): back at 0x02FB349C, r3 / r10 / LR as the game left them, '
          'every shell off', (pm.reg_read(UC_PPC_REG_PC), pm.reg_read(UC_PPC_REG_3), pm.reg_read(UC_PPC_REG_10),
                              pm.reg_read(UC_PPC_REG_LR), r32(pm, g),
                              [r32(pm, tab + SC.ENT * k) for k in range(SC.N_ENT)]),
          (OL.CLEAR_BACK, 0x7F00BB00, 0x10, RET, 0, [0] * SC.N_ENT))
    diag_tests(exe, orig)
    sys.exit(1 if acmd_ext_test.fails else 0)



class DrawEnv:
    """CommandDrawModel's draw calls on a fake device context (laid out as the device's code fills it), the game's
    draw and the GX2 calls replaced by recorders"""

    def __init__(self, pm):
        self.pm = pm
        ensure(pm, STUB, STUB + 0x1000)
        stubs = {}
        rec = Asm(STUB + 0x100)
        names = ['draw'] + sorted(SC.GX2)
        text = ''
        for k, nm in enumerate(names):
            text += """
        rec_%(k)d:
            li r0, %(k)d
            b rec_all""" % dict(k=k)
        text += """
        rec_all:
            lis r12, 0x%X
            ori r12, r12, 0x%X
            lwz r11, 0(r12)
            addi r10, r11, 1
            stw r10, 0(r12)
            slwi r11, r11, 6
            add r12, r12, r11
            stw r0, 0x20(r12)
            stw r3, 0x24(r12)
            stw r4, 0x28(r12)
            stw r5, 0x2C(r12)
            stw r6, 0x30(r12)
            stw r7, 0x34(r12)
            stw r8, 0x38(r12)
            stw r9, 0x3C(r12)
            cmplwi r3, 0x7F00
            blt rec_out
            lwz r0, 0(r3)
            stw r0, 0x40(r12)
            lwz r0, 4(r3)
            stw r0, 0x44(r12)
        rec_out:
            li r3, 0x5A5A
            li r4, 0x5A5B
            blr
        """ % (LOG >> 16, LOG & 0xFFFF)
        rec.asm(text.replace('cmplwi r3, 0x7F00\n        blt rec_out', 'srwi r0, r3, 16\n        cmplwi r0, 0x7F00\n'
                             '        blt rec_out'))
        for i, x in enumerate(rec.words()):
            w32(pm, STUB + 0x100 + 4 * i, x)
        for k, nm in enumerate(names):
            stubs[nm] = rec.addr('rec_%d' % k)
        for nm, (stub, _site) in SC.GX2.items():
            w32(pm, stub, LT.branch(stub, stubs[nm]))
        w32(pm, SC.DRAW_FN_I, LT.branch(SC.DRAW_FN_I, stubs['draw']))
        ensure(pm, CTXA, CTXA + 0x3000)
        w32(pm, CTXA + 0x1800 + 0xB4, stubs['draw'])     # the device's vtable: +0xB4 DrawIndexed
        ensure(pm, LOG, LOG + 0x2000)
        fbd = FB + 0x900                       # the FB1 this draw has bound
        blocks = CTXA + 0x1400
        C = SC.CTX

        def ctx(fbuf=fbd, vfb=None, gs=0, blk=((4, 0x40), (7, 0x2A0)), rel=False, rs=0x00080006, ds=0x000000B7):
            pm.mem_write(CTXA, b'\0' * 0x1000)
            w32(pm, CTXA, CTXA + 0x1800)
            w32(pm, CTXA + C['vs'], GAME_VS)
            w32(pm, CTXA + C['gs'], gs)
            w32(pm, CTXA + C['ps'], GAME_PS)
            w32(pm, CTXA + C['vcb'] + 8 * 7, fbuf if vfb is None else vfb)
            w32(pm, CTXA + C['vcb'] + 8 * 7 + 4, 0x2A0)
            w32(pm, CTXA + C['pcb'] + 8 * 7, fbuf)
            w32(pm, CTXA + C['pcb'] + 8 * 7 + 4, 0x2A0)
            w32(pm, CTXA + C['blend'], 0x7F052000)
            w32(pm, CTXA + C['blend0'], 0)
            w32(pm, CTXA + C['blend0'] + 4, 0x00010101)
            w32(pm, CTXA + C['atest'], 0x77)
            w32(pm, CTXA + C['atest'] + 4, 0x3F000000)
            w32(pm, CTXA + C['ds'], 0x7F052100)
            w32(pm, CTXA + C['dsreg'], ds)
            w32(pm, CTXA + C['rs'], 0x7F052200)
            w32(pm, CTXA + C['rsreg'], rs)
            w32(pm, CTXA + C['cc'] + 4, 0xCC)
            pm.mem_write(CTXA + C['cc'] + 8, b'\x02')
            w32(pm, CTXA + C['cc'] + 0xC, 0)
            w32(pm, CTXA + C['cc'] + 0x10, 1)
            pm.mem_write(GAME_PS, b'\0' * 0x100)
            w32(pm, GAME_PS + 0xB0, len(blk))
            w32(pm, GAME_PS + 0xB4, (0xD0600000 | (blocks - GAME_PS)) if rel else blocks)
            for i, (loc, size) in enumerate(blk):
                w32(pm, blocks + 12 * i, 0x7F053000)
                w32(pm, blocks + 12 * i + 4, loc)
                w32(pm, blocks + 12 * i + 8, size)

        def draw(site=SC.DRAW_I):
            w32(pm, LOG, 0)
            for r in range(14, 32):
                pm.reg_write(REG(r), 0x3000 + r)
            args = [CTXA, 4, 0x7F054000, 0x7F054100, 0x200, 7, 1]
            for k, v in enumerate(args):
                pm.reg_write(REG(3 + k), v)
            pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
            pm.reg_write(UC_PPC_REG_LR, 0x12345670)
            pm.emu_start(site, site + 4, count=100000)
            kept = [r for r in range(14, 32) if pm.reg_read(REG(r)) != 0x3000 + r]
            calls = []
            for i in range(r32(pm, LOG)):
                b = LOG + 0x40 * i + 0x20
                nm = names[r32(pm, b)]
                a = [r32(pm, b + 4 + 4 * j) for j in range(7)]
                calls.append((nm, a, (r32(pm, b + 0x20), r32(pm, b + 0x24))))
            return dict(calls=calls, kept=kept, pc=pm.reg_read(UC_PPC_REG_PC), sp=pm.reg_read(UC_PPC_REG_1),
                        args=args)

        def fbset(width, blend, alpha=1.0, magic=SC.MAGIC, swapped=False):
            pm.mem_write(fbd, b'\0' * 0x2A0)
            wf(pm, fbd + SC.FB_COL, [1.0, 1.0, 1.0, alpha])
            wf(pm, fbd + SC.FB_SHELL, [width])
            w32(pm, fbd + SC.FB_SHELL + 4, magic)
            w32(pm, fbd + SC.FB_SHELL + 8, blend)
            if swapped:                    # as the game leaves it at the draw: NU::ConstantBufferWiiU's unlock
                b = bytes(pm.mem_read(fbd, 0x2A0))      # (0x037291BC) swaps every word in place
                pm.mem_write(fbd, b''.join(b[i:i + 4][::-1] for i in range(0, 0x2A0, 4)))

        def only_draw(d):
            return [c[0] for c in d['calls']] == ['draw'] and d['calls'][0][1] == d['args'] and d['pc'] == SC.DRAW_I + 4 \
                and d['sp'] == 0x7F00F000 and d['kept'] == []
        self.ctx, self.draw, self.fbset, self.only_draw, self.fbd, self.names = ctx, draw, fbset, only_draw, fbd, names

def progs_tests(pm, lab):
    import numpy as np
    vs_regs = [r32(pm, lab['os_vs'] + 4 * i) for i in range(52)]
    vs_f = [r32(pm, lab['os_vs'] + 0xD0 + 4 * i) for i in range(3)]
    ps_regs = [r32(pm, lab['os_ps'] + 4 * i) for i in range(41)]
    ps_f = [r32(pm, lab['os_ps'] + 0xA4 + 4 * i) for i in range(3)]
    check('GX2VertexShader in the cave: special.nsh\'s registers (9 GPRs, semantics 0 -> R1, 1 -> R2), its size, '
          'program, uniform-block mode', (vs_regs, vs_f), (SC.VS_REGS, [len(SC.VS_PROGRAM), SC.VS_PROG, 1]))
    check('GX2PixelShader in the cave: special.nsh\'s registers, its size, program, uniform-block mode',
          (ps_regs, ps_f), (SC.PS_REGS, [len(SC.PS_PROGRAM), SC.PS_PROG, 1]))
    check('... the structs\' other counts 0 (no metadata the GX2 calls need)',
          ([r32(pm, lab['os_vs'] + 0xDC + 4 * i) for i in range((0x134 - 0xDC) // 4)],
           [r32(pm, lab['os_ps'] + 0xB0 + 4 * i) for i in range((0xE8 - 0xB0) // 4)]),
          ([0] * ((0x134 - 0xDC) // 4), [0] * ((0xE8 - 0xB0) // 4)))
    check('the programs in the cave, 256-aligned', (bytes(pm.mem_read(SC.VS_PROG, len(SC.VS_PROGRAM))) == SC.VS_PROGRAM,
                                                     bytes(pm.mem_read(SC.PS_PROG, len(SC.PS_PROGRAM))) == SC.PS_PROGRAM,
                                                     SC.VS_PROG % 256, SC.PS_PROG % 256), (True, True, 0, 0))
    if not os.path.exists(os.path.join(HERE, 'latte_dis', 'latte-asm')):
        print('skip the programs\' assembly and runs (tools/latte_dis/build_asm.sh builds latte-asm)')
        return
    import latte_exec as LE
    check('the programs re-assembled from their sources = the cave\'s bytes', SC.assemble(),
          (SC.VS_PROGRAM, SC.PS_PROGRAM))
    V = LE.VertexProgram(SC.gsh('vs'))
    check('vertex program: inputs a_Position (R1), a_Normal (R2); reads PerDraw rows 0-3, PerView rows 0-3, FB1 '
          'compressParam (9) and the width (13)', (V.attributes, sorted({(cb, i) for cb, i, _c in V.reads})),
          (['a_Position', 'a_Normal'], sorted({(2, i) for i in range(4)} | {(3, i) for i in range(4)} |
                                               {(7, 9), (7, 13)})))
    rng = np.random.default_rng(7)
    n = 64
    L = rng.normal(size=(4, 4)).astype(np.float32) * 0.5
    L[:3, :3] += np.eye(3, dtype=np.float32) * 1.5
    L[:, 3] = [0, 0, 0, 1]
    P = rng.normal(size=(4, 4)).astype(np.float32)
    for width, comp in ((3.0, (1.0, 0.0)), (-0.75, (0.6, 2.0)), (0.0, (1.0, 0.0)), (12.5, (0.3, -1.0))):
        pos = rng.normal(size=(n, 3)).astype(np.float32) * 5
        nor = rng.normal(size=(n, 3)).astype(np.float32)
        nor /= np.linalg.norm(nor, axis=1, keepdims=True)
        fb1 = np.zeros((42, 4), np.float32)
        fb1[9, :2] = comp
        fb1[13, 0] = width
        attrs = np.stack([np.concatenate([pos, np.ones((n, 1), np.float32)], 1),
                          np.concatenate([nor, np.zeros((n, 1), np.float32)], 1)], 1)
        out, _ = V.run(attrs, {2: L, 3: P, 7: fb1})
        ref = SC.shell_ref(pos.astype(np.float64), nor.astype(np.float64), L.astype(np.float64),
                           P.astype(np.float64), comp, width)
        err = float(np.abs(out - ref).max() / max(1.0, np.abs(ref).max()))
        check('vertex program, Width %g, compressParam %s: clip positions = shell_ref (relative error < 1e-5)'
              % (width, comp), err < 1e-5, True)
        if width > 0:
            fb1[13, 0] = 0.0
            base, _ = V.run(attrs, {2: L, 3: P, 7: fb1})
            px = np.linalg.norm((out[:, :2] - base[:, :2]).astype(np.float64) / base[:, 3:4] * [640.0, 360.0], axis=1)
            check('... every vertex moved %g pixels of a 1280 x 720 picture on screen' % width,
                  bool(np.allclose(px, width, rtol=1e-3, atol=0.01)), True)
    Pp = LE.PixelProgram(SC.gsh('ps'))
    fb1 = np.zeros((42, 4), np.float32)
    fb1[12] = [1.0, 0.25, 0.5, 0.75]
    check('pixel program: FB1 vec4 12 (r, g, b, alpha), every pixel', Pp.run(np.zeros((3, 0, 4), np.float32), {7: fb1},
                                                                             {}).tolist(),
          [[1.0, 0.25, 0.5, 0.75, 1.0]] * 3)


def diag_tests(exe, orig):
    import diag_godfist_cave as G
    words, lab, _s = SC.build(orig, diag=True)
    check('diag build inside the region (below the programs)', max(a for a in words if SC.CAVE <= a < SC.VS_PROG) <
          SC.VS_PROG, True)
    pm = machine(exe)
    for at, w in words.items():
        w32(pm, at, w)
    rec = 0x7F00C000
    ensure(pm, rec - 0x1000, rec + 0x2000)
    st = Asm(G.OSREPORT_VENEER)
    st.asm("""
        lis r12, 0x%X
        ori r12, r12, 0x%X
        lwz r11, 0(r12)
        addi r0, r11, 1
        stw r0, 0(r12)
        slwi r11, r11, 5
        add r12, r12, r11
        stw r3, 0x20(r12)
        stw r4, 0x24(r12)
        stw r5, 0x28(r12)
        stw r6, 0x2C(r12)
        stw r7, 0x30(r12)
        stw r8, 0x34(r12)
        stw r9, 0x38(r12)
        stw r10, 0x3C(r12)
        blr
""" % (rec >> 16, rec & 0xFFFF))
    for i, x in enumerate(st.words()):
        w32(pm, G.OSREPORT_VENEER + 4 * i, x)
    pm.reg_write(UC_PPC_REG_MSR, pm.reg_read(UC_PPC_REG_MSR) | 0x2000)
    W = World(pm)
    w32(pm, STATE + 4, 0x1000)
    w32(pm, STATE + 8, 0xFFFFFFFF)
    pm.mem_write(FLAG + 8, b'\x01')
    pm.mem_write(PARAMS, struct.pack('>ifffffiiiii', 0, 255.0, 255.0, 255.0, 255.0, 1.5, 0, 0, 0, 0, 1))
    run(pm, lab['h_shell'], RET, {UC_PPC_REG_3: W.acc(0), UC_PPC_REG_5: STATE, UC_PPC_REG_6: FLAG,
                                   UC_PPC_REG_7: PARAMS})

    def lines(frm=0):
        out = []
        for i in range(frm, r32(pm, rec)):
            f = r32(pm, rec + 0x20 * (i + 1))
            out.append((bytes(pm.mem_read(f, 4)).decode('latin1'),) +
                       tuple(r32(pm, rec + 0x20 * (i + 1) + 4 * j) for j in range(1, 8)))
        return out
    got = lines()
    check('diag: S4SC (target 0, the accessor) / S4SD (the width, blend 1) at the command',
          [(x[0], x[2]) for x in got[:1]] + [(x[0], x[1], x[6]) for x in got[1:2]],
          [('S4SC', W.acc(0)), ('S4SD', struct.unpack('>I', struct.pack('>f', 1.5))[0], 1)])
    ensure(pm, SMGR, SMGR + 0x1000)
    pm.mem_write(SMGR, b'\0' * 0xE80)
    pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
    pm.reg_write(UC_PPC_REG_3, SMGR)
    pm.reg_write(UC_PPC_REG_LR, RET)
    n0 = r32(pm, rec)
    pm.emu_start(OL.TICK_AT, OL.TICK_AT + 4, count=400000)
    check('diag: S4ST at the tick', [x[0] for x in lines(n0)], ['S4ST'])
    env = DrawEnv(pm)
    env.ctx()
    env.fbset(1.5, 1)
    stub = Asm(SC.OS_GET_CORE_ID)                     # OSGetCoreId: core 2
    stub.asm('\n        li r3, 2\n        blr\n')
    for i, x in enumerate(stub.words()):
        w32(pm, SC.OS_GET_CORE_ID + 4 * i, x)
    sleep = Asm(SC.OS_SLEEP_TICKS)                    # OSSleepTicks: records its ticks (r3:r4) at rec - 8, returns
    sleep.asm('''
        lis r12, 0x%X
        ori r12, r12, 0x%X
        lwz r11, 0(r12)
        addi r11, r11, 1
        stw r11, 0(r12)
        stw r4, 4(r12)
        blr
''' % ((rec - 8) >> 16, (rec - 8) & 0xFFFF))
    for i, x in enumerate(sleep.words()):
        w32(pm, SC.OS_SLEEP_TICKS + 4 * i, x)
    w32(pm, rec - 8, 0)
    chain = [(0x7F00F000, 0x7F00F100, 0x037174DC), (0x7F00F100, 0x7F00F200, 0x11111111),
             (0x7F00F200, 0x7F00F300, 0x22222222), (0x7F00F300, 0, 0x33333333)]
    for f, nxt, lr in chain:                          # the stack above os_draw: back chain + saved LR per frame
        w32(pm, f, nxt)
        w32(pm, f + 4, lr)
    n0 = r32(pm, rec)
    env.draw()
    got = lines(n0)
    check('diag: S4SP at each step of a shell drawn (1 mark, 2 programs, 3 states, 4 draw, 5 back), shell 1, the core, '
          'the return addresses up the stack', [x[:8] for x in got if x[0] == 'S4SP'],
          [('S4SP', k, 1, 2, 0x037174DC, 0x11111111, 0x22222222, 0x33333333) for k in range(1, 6)])
    check('diag: S4SM the moment the draw\'s FB1 carries the mark (the context, FB1, the vertex stage\'s FB1, no '
          'geometry shader, the pixel shader, its 2 blocks), before os_chk\'s tests', [x[:8] for x in got if x[0] == 'S4SM'],
          [('S4SM', CTXA, env.fbd, env.fbd, 0, GAME_PS, 2, r32(pm, GAME_PS + 0xB4))])
    check('diag: a 50 ms pause (OSSleepTicks %d ticks) after S4SM and each S4SP: 6' % SC.DIAG_PAUSE,
          (r32(pm, rec - 8), r32(pm, rec - 4)), (6, SC.DIAG_PAUSE))
    check('diag: S4SM / S4SP first, so a crash after them leaves them in the log', [x[0] for x in got][:6],
          ['S4SM'] + ['S4SP'] * 5)
    got = [x for x in got if x[0] not in ('S4SP', 'S4SM')]
    check('diag: S4SR at a shell drawn (shells drawn 1, the device context, its programs, FB1, the width, the rasterizer '
          'state set)', [(x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7]) for x in got],
          [('S4SR', 1, CTXA, GAME_VS, GAME_PS, env.fbd, struct.unpack('>I', struct.pack('>f', 1.5))[0],
            (0x00080006 & ~3) | SC.CULL_FRONT)])
    env.ctx(blk=((7, 0x2A0),))
    n0 = r32(pm, rec)
    env.draw()
    got = lines(n0)
    check('diag: S4SX at a marked FB1 refused (refusals 1, the context, the pixel shader, its block count, FB1)',
          [(x[0], x[1], x[2], x[3], x[4], x[6]) for x in got if x[0] != 'S4SM'], [('S4SX', 1, CTXA, GAME_PS, 1, env.fbd)])
    n0 = r32(pm, rec)
    pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
    pm.reg_write(UC_PPC_REG_3, SMGR)
    pm.reg_write(UC_PPC_REG_LR, RET)
    pm.emu_start(OL.TICK_AT, OL.TICK_AT + 4, count=400000)
    got = lines(n0)
    check('diag: S4ST\'s counts: shells drawn 1, draws checked 2, refused 1', [(x[0], x[5], x[6], x[7]) for x in got],
          [('S4ST', 1, 2, 1)])
    # v4 TEST ONLY variants: noprog (the game's programs kept for the shell's draw), nodraw (no second draw)
    env.ctx()
    env.fbset(1.5, 1)
    full = [c[0] for c in env.draw()['calls']]
    for var, want in (('noprog', [x for i, x in enumerate(full) if i not in (1, 2)]),
                      ('nodraw', full[:8] + full[9:])):
        vw, vlab, _s = SC.build(orig, diag=True, variant=var)
        for at in range(SC.CAVE, SC.VS_PROG, 4):
            w32(pm, at, vw.get(at, 0))
        for at, w in vw.items():
            w32(pm, at, w)
        w32(pm, vlab['os_g'], 1)
        pm.ctl_remove_cache(SC.CAVE, SC.LIMIT)        # (the emulator's translated blocks of the old code)
        env.ctx()
        env.fbset(1.5, 1)
        d = env.draw()
        check('diag --variant %s: the calls (%s)' % (var, 'no programs set' if var == 'noprog' else 'no second draw'),
              ([c[0] for c in d['calls']], d['pc'], d['sp'], d['kept']), (want, SC.DRAW_I + 4, 0x7F00F000, []))


if __name__ == '__main__':
    main()
