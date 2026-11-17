#!/usr/bin/env python3
"""Test of tools/outline_cave.py (Outline_Set) on an executable with exe_v46z_inv's patches:

  python3 tools/outline_test.py EXE.rpx

The cave's words are written into the emulated image (the file isn't patched). Run with the game's own code around
the hooks (unicorn):
  - the command tables (the game's CRC search, both script loaders, the handler fetch) for Outline_Set and every
    earlier cave's command (acmd_ext's, Line_Test, Var_Reset_Set, Hitbox_Hold, Effect_Camera, Screen_Invert);
  - Outline_Set's handler on a fighter-like object (ModelModule at accessor +0x3C, its handle's instance at +0xC;
    acmd_ext's nc_target resolves the Target): start, replace, Alpha 0 (fade out / at once), the 17th object;
  - the tick (0x032EFB78: screen_invert's si_tick, so the game's screen-effect update 0x0334B250, then the outlines'
    frame): fades in / held / out frame by frame, Frames, the pulse (outline_cave.pulse), a KO (the fighters'
    StatusModule vtable, status 0xB1) and a changed model drop the outline;
  - the four FB1 unlock sites (0x0341E2C0 / 0x0341E2DC: r30 the instance, r28 FB1; 0x034247B0 / 0x0342484C: r31,
    r27): g_fresnelOffset / blinkColor as outline_cave.apply_ref (the Python reference) computes them, the unlock (a
    recording stub in CTR) called with the game's r3 and return address, another instance's FB1 untouched;
  - the clear (0x02FB3498 -> tsu_clear -> si_clear -> ol_clear -> 0x02FB349C): every outline off;
  - the diag build's lines (the OSReport veneer replaced by a recorder).
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_cave as C  # noqa: E402
import outline_cave as OL  # noqa: E402
import line_test_cave as LT  # noqa: E402
import acmd_ext_test  # noqa: E402
from acmd_ext_test import check, r32, w32, run, RET, CRC_TABLE, COUNT, SIZES, HANDLERS, BUF  # noqa: E402
from stage_slot_test import machine  # noqa: E402
from ppcasm import Asm  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_0, UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5,  # noqa: E402
                               UC_PPC_REG_6, UC_PPC_REG_7, UC_PPC_REG_10, UC_PPC_REG_12, UC_PPC_REG_29,
                               UC_PPC_REG_LR, UC_PPC_REG_CTR, UC_PPC_REG_MSR, UC_PPC_REG_PC)

REG = lambda n: UC_PPC_REG_0 + n          # noqa: E731
PARAMS, STATE, FLAG = 0x7F001400, 0x7F001600, 0x7F001700
OBJS = 0x7F020000                         # fake objects: accessor, ModelModule, StatusModule, 0x100 each, 0x400 apart
FB = 0x7F030000                           # FB1 buffers (0x2A0 each)
SMGR = 0x7F010000                         # a screen-effect manager with no entries (0xE80 bytes)
STUB = 0x04BE5000                         # the unlock stub (past the cave, in the emulated code's grown end)
SREC = 0x7F006000
TOL = 2e-5
EARLIER = {'Line_Test': 1096, 'Var_Reset_Set': 2000, 'Hitbox_Hold': 2100, 'Effect_Camera': 2200,
           'Screen_Invert': 2300}


def fb(v):
    return struct.unpack('>I', struct.pack('>f', v))[0]


def rf(mu, a, n):
    return list(struct.unpack('>%df' % n, mu.mem_read(a, 4 * n)))


def wf(mu, a, vals):
    mu.mem_write(a, struct.pack('>%df' % len(vals), *vals))


def close(a, b, tol=TOL):
    return len(a) == len(b) and all(abs(x - y) <= tol * max(1, abs(y)) for x, y in zip(a, b))


def ensure(mu, lo, hi):
    mapped = [(b, e) for b, e, _p in mu.mem_regions()]
    a = lo & ~0xFFF
    while a < hi:
        if not any(b <= a <= e for b, e in mapped):
            mu.mem_map(a, 0x1000)
        a += 0x1000


def table_tests(pm, om, s, words, lab, prefix, name, index, crc, size, hand_label, earlier):
    """the command tables: the new command and every earlier one (shared with mesh_vis_test.py)"""
    pairs = [(r32(om, CRC_TABLE + 8 * i), r32(om, CRC_TABLE + 8 * i + 4)) for i in range(COUNT)]
    check('%s CRC not a game command, nor an acmd_ext one' % name,
          (crc in dict(pairs), crc in [C.crc(c[0]) for c in C.COMMANDS]), (False, False))

    def lookup(mu, c):
        run(mu, 0x02BEE154, RET, {UC_PPC_REG_3: c})
        return mu.reg_read(UC_PPC_REG_3)
    check('vanilla CRCs keep their index', [hex(c) for c, i in pairs[::7] if lookup(pm, c) != i], [])
    check('acmd_ext CRCs keep theirs', [lookup(pm, C.crc(c[0])) for c in C.COMMANDS],
          [C.NEW_BASE + k for k in range(len(C.COMMANDS))])
    ecrc = {n: zlib.crc32(n.encode()) & 0xFFFFFFFF for n in earlier}
    check('earlier caves\' commands keep their index (%s)' % ', '.join(earlier),
          [lookup(pm, c) for c in ecrc.values()], [lookup(om, c) for c in ecrc.values()])
    check('... which the unpatched exe has (%s)' % ', '.join(str(v) for v in earlier.values()),
          [lookup(om, c) for c in ecrc.values()], list(earlier.values()))
    check('%s -> its index (%d)' % (name, index), lookup(pm, crc), index)
    check('unknown CRC -> -1', lookup(pm, 0x12345678), 0xFFFFFFFF)
    idx = dict(pairs)
    sz = {i: r32(om, SIZES + 4 * i) for _, i in pairs}
    last = list(earlier)[-1]
    script = [0xB738EABD, crc, 0x42ACFE7D, ecrc[last], ecrc['Line_Test'], crc]
    want_idx = [idx[0xB738EABD], index, idx[0x42ACFE7D], earlier[last], 1096, index]
    esize = {'Line_Test': 11, 'Var_Reset_Set': 5, 'Hitbox_Hold': 3, 'Effect_Camera': 12, 'Screen_Invert': 11,
             'Outline_Set': 11}
    want_size = [sz[want_idx[0]], size, sz[want_idx[2]], esize[last], 11, size]
    for loop, (start, stop, regs) in enumerate([
            (0x02BEE2B4, 0x02BEE2D8, {REG(28): BUF, UC_PPC_REG_29: 0, REG(30): len(script), UC_PPC_REG_4: SIZES}),
            (0x02BEE3B4, 0x02BEE3D8, {REG(28): BUF, UC_PPC_REG_4: 0, UC_PPC_REG_29: len(script), REG(30): SIZES})]):
        pm.mem_write(BUF, b'\0' * 0x1000)
        o, offs = 0, []
        for c, n in zip(script, want_size):
            w32(pm, BUF + 4 * o, c)
            offs.append(o)
            o += n
        run(pm, start, stop, regs)
        check('loader %d: indices (Hitbox, %s, FRAME, %s, Line_Test, %s)' % (loop + 1, name, last, name),
              [r32(pm, BUF + 4 * x) for x in offs], want_idx)
        check('loader %d: words stepped (%s %d)' % (loop + 1, name, size),
              pm.reg_read(UC_PPC_REG_29 if loop == 0 else UC_PPC_REG_4), sum(want_size))

    def fetch(mu, i):
        run(mu, 0x02BEE84C, 0x02BEE854, {UC_PPC_REG_7: i, UC_PPC_REG_29: HANDLERS, UC_PPC_REG_12: 0x55})
        return mu.reg_read(UC_PPC_REG_0)
    check('vanilla handlers unchanged', [i for _, i in pairs[::11] if fetch(pm, i) != r32(om, HANDLERS + 4 * i)], [])
    check('acmd_ext handlers unchanged', [fetch(pm, C.NEW_BASE + k) for k in range(len(C.COMMANDS))],
          [fetch(om, C.NEW_BASE + k) for k in range(len(C.COMMANDS))])
    check('earlier caves\' handlers kept', [fetch(pm, i) for i in earlier.values()],
          [fetch(om, i) for i in earlier.values()])
    check('%s handler' % name, fetch(pm, index), lab[hand_label])


class World:
    """fake objects: obj k = accessor OBJS + 0x400 k (+0x3C ModelModule at +0x100, its +0xC the instance at +0x200,
    +0x20 a StatusModule at +0x300 with the fighters' vtable)"""

    def __init__(self, mu, n=20):
        self.mu = mu
        ensure(mu, OBJS, OBJS + 0x400 * n)
        ensure(mu, FB, FB + 0x300 * 4)
        for k in range(n):
            a = self.acc(k)
            mu.mem_write(a, b'\0' * 0x400)
            w32(mu, a + 0x3C, a + 0x100)
            w32(mu, a + 0x10C, self.mi(k))
            w32(mu, a + 0x20, a + 0x300)
            w32(mu, a + 0x300, OL.FIGHTER_SM_VT)
            w32(mu, a + 0x348, 0)

    @staticmethod
    def acc(k):
        return OBJS + 0x400 * k

    @staticmethod
    def mi(k):
        return OBJS + 0x400 * k + 0x200


def main():
    exe = sys.argv[1]
    orig = OL.rpx_reader(exe)
    words, lab, s = OL.build(orig)
    om, pm = machine(exe), machine(exe)
    for at, w in words.items():
        w32(pm, at, w)
    check('present() on the patched words / the unpatched exe',
          (OL.present(lambda x: words.get(x, orig(x))), OL.present(orig)), (True, False))
    try:
        OL.build(lambda x: words.get(x, orig(x)))
        check('building over itself refused', False, True)
    except AssertionError:
        check('building over itself refused', True, True)
    inside = [a for a in words if OL.CAVE <= a < OL.LIMIT]
    check('the cave inside its region (0x04BE3000-0x04BE4000)', (min(inside), max(inside) < OL.LIMIT),
          (OL.CAVE, True))
    others = sorted(a for a in words if not OL.CAVE <= a < OL.LIMIT)
    check('words outside the cave: the 4 FB1 unlocks, the tick, the clear chain\'s end and the 4 table fallbacks',
          others, sorted(list(OL.FB_A + OL.FB_B) + [OL.TICK_AT, s['clear_at'], s['lk_none'], s['s1'], s['s2'],
                                                    s['f']]))
    check('... the unlocks and the tick are bl, the clear a b',
          [words[a] & 3 for a in OL.FB_A + OL.FB_B + (OL.TICK_AT, s['clear_at'])], [1, 1, 1, 1, 1, 0])
    check('... the tick chained on screen_invert\'s si_tick, the clear on its si_clear (0x04BE2000-0x04BE3000)',
          (0x04BE2000 <= s['tick_prev'] < 0x04BE3000, 0x04BE2000 <= s['clear_at'] < 0x04BE3000), (True, True))
    check('... the table fallbacks were Screen_Invert\'s: chained',
          [0x04BE2000 <= LT.bdecode(s[k], s[k + '_word']) < 0x04BE3000 for k in ('lk_none', 's1', 's2', 'f')],
          [True] * 4)
    table_tests(pm, om, s, words, lab, 'ol', OL.CMD_NAME, OL.OL_INDEX, OL.CMD_CRC, 1 + OL.NPARAMS, 'h_outline',
                EARLIER)

    pm.reg_write(UC_PPC_REG_MSR, pm.reg_read(UC_PPC_REG_MSR) | 0x2000)
    W = World(pm)
    tab, g = lab['ol_tab'], lab['ol_g']

    def entry(k):
        a = tab + OL.ENT * k
        return dict(acc=r32(pm, a), mi=r32(pm, a + 4), ph=r32(pm, a + 8), w=rf(pm, a + 0xC, 1)[0],
                    left=r32(pm, a + 0x18), cs=rf(pm, a + 0x1C, 3), c=rf(pm, a + 0x28, 3), tint=rf(pm, a + 0x34, 1)[0],
                    flash=r32(pm, a + 0x38), t=r32(pm, a + 0x3C), eff=rf(pm, a + 0x40, 1)[0])

    def find_e(acc):
        for k in range(OL.N_ENT):
            if r32(pm, tab + OL.ENT * k) == acc:
                return entry(k)
        return None

    def ol(acc, target, rgb, alpha, tint=0.0, frames=0, fin=0, fout=0, flash=0, execute=1):
        w32(pm, STATE + 4, 0x1000)
        w32(pm, STATE + 8, 0xFFFFFFFF)
        pm.mem_write(FLAG + 8, bytes([execute]))
        pm.mem_write(PARAMS, struct.pack('>ifffffiiii', target, rgb[0], rgb[1], rgb[2], alpha, tint, frames, fin,
                                         fout, flash))
        for r in range(14, 32):
            pm.reg_write(REG(r), 0x1000 + r)
        run(pm, lab['h_outline'], RET, {UC_PPC_REG_3: acc, UC_PPC_REG_5: STATE, UC_PPC_REG_6: FLAG,
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
            pm.emu_start(OL.TICK_AT, OL.TICK_AT + 4, count=200000)

    a0 = W.acc(0)
    r = ol(a0, 0, (255.0, 255.0, 255.0), 255.0, frames=120)
    check('Outline_Set(self, white, 255, Frames 120): returns 2, steps 11 words, callee-saved kept',
          (r['ret'], r['step'], r['kept']), (2, 44, []))
    e = find_e(a0)
    check('... an entry for the object\'s instance ([[acc + 0x3C] + 0xC]), held at once (w 1), Frames 120, weight 1',
          (e['mi'], e['ph'], e['w'], e['left'], e['eff']), (W.mi(0), 2, 1.0, 120, 1.0))
    check('... the colour x strength (1, 1, 1), the tint 0, no pulse', (e['cs'], e['tint'], e['flash']),
          ([1.0, 1.0, 1.0], 0.0, 0))
    check('... entries in use 1', r32(pm, g), 1)
    r = ol(a0, 0, (255.0, 0.0, 0.0), 255.0, execute=0)
    check('not executed (execute flag 0): stepped, nothing changed', (r['step'], find_e(a0)['cs']),
          (44, [1.0, 1.0, 1.0]))
    tick(119)
    e = find_e(a0)
    check('ticks: held 119 frames, 1 left, w 1, t 119', (e['ph'], e['left'], e['w'], e['t']), (2, 1, 1.0, 119))
    check('... the game\'s screen-effect update ran (screen_invert\'s si_tick first: its winners -1)',
          (r32(pm, SMGR + 0xE6C), r32(pm, SMGR + 0xE70)), (0xFFFFFFFF, 0xFFFFFFFF))
    tick(1)
    check('... Frames over with FadeOut 0: off at once (entry freed, none in use)', (find_e(a0), r32(pm, g)), (None, 0))

    # fades
    ol(a0, 0, (255.0, 0.0, 0.0), 510.0, frames=3, fin=4, fout=2)
    seq = []
    for _ in range(10):
        e = find_e(a0)
        seq.append((e['ph'], round(e['w'], 4)) if e else None)
        tick(1)
    check('FadeIn 4, Frames 3, FadeOut 2: w frame by frame (in over 4, held 3, out over 2)', seq,
          [(1, 0.0), (1, 0.25), (1, 0.5), (1, 0.75), (2, 1.0), (2, 1.0), (2, 1.0), (3, 1.0), (3, 0.5), None])
    ol(a0, 0, (0.0, 0.0, 255.0), 255.0, fin=4)
    tick(2)
    ol(a0, 0, (0.0, 255.0, 0.0), 255.0, fin=4)
    e = find_e(a0)
    check('a new outline on a glowing object fades from where it is (w 0.5, still fading in, the new colour)',
          (e['ph'], e['w'], e['c']), (1, 0.5, [0.0, 1.0, 0.0]))
    ol(a0, 0, (0.0, 0.0, 0.0), 0.0, fout=4)
    tick(1)
    e = find_e(a0)
    check('Alpha 0 with FadeOut 4: fading out from 0.5 (0.25 after a frame)', (e['ph'], round(e['w'], 4)), (3, 0.25))
    tick(1)
    check('... gone at 0', find_e(a0), None)
    ol(a0, 0, (255.0, 255.0, 255.0), 255.0)
    ol(a0, 0, (0.0, 0.0, 0.0), 0.0)
    check('Alpha 0 with FadeOut 0: off at once', (find_e(a0), r32(pm, g)), (None, 0))
    r = ol(a0, 0, (0.0, 0.0, 0.0), 0.0)
    check('Alpha 0 on an object with no outline: nothing', (r['ret'], r32(pm, g)), (2, 0))

    # the pulse
    ol(a0, 0, (255.0, 0.0, 0.0), 255.0, flash=20)
    got = []
    for t in range(1, 26):
        tick(1)
        got.append(find_e(a0)['eff'])
    check('Flash 20: the drawn weight follows outline_cave.pulse (full, off at 10, full at 20)',
          close(got, [OL.pulse(t, 20) for t in range(1, 26)], 1e-5), True)
    check('... off at frame 10, full at 20', (round(got[9], 5), round(got[19], 5)), (0.0, 1.0))

    # KO / a changed model / the 17th object
    w32(pm, a0 + 0x348, OL.DEAD)
    tick(1)
    check('a KO (fighter status 0xB1) drops the outline', find_e(a0), None)
    w32(pm, a0 + 0x348, 0)
    w32(pm, a0 + 0x300, 0x10000000)
    ol(a0, 0, (255.0, 0.0, 0.0), 255.0)
    w32(pm, a0 + 0x348, OL.DEAD)
    tick(1)
    check('... not an article\'s (another StatusModule class) with that status', find_e(a0) is not None, True)
    w32(pm, a0 + 0x300, OL.FIGHTER_SM_VT)
    w32(pm, a0 + 0x348, 0)
    w32(pm, a0 + 0x10C, W.mi(5))
    tick(1)
    check('the object\'s model changed: dropped', find_e(a0), None)
    w32(pm, a0 + 0x10C, W.mi(0))
    w32(pm, W.acc(3) + 0x3C, 0)
    r = ol(W.acc(3), 0, (255.0, 0.0, 0.0), 255.0)
    check('an object with no ModelModule: nothing (stepped)', (r['step'], find_e(W.acc(3))), (44, None))
    w32(pm, W.acc(3) + 0x3C, W.acc(3) + 0x100)
    for k in range(17):
        ol(W.acc(k), 0, (255.0, 0.0, 0.0), 255.0)
    check('17 objects: 16 entries in use, the 17th took one (round robin)',
          (r32(pm, g), find_e(W.acc(16)) is not None), (16, True))

    # ---- the FB1 unlock sites
    ensure(pm, STUB, STUB + 0x100)
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
    for k in range(OL.N_ENT):
        w32(pm, tab + OL.ENT * k, 0)
    w32(pm, g, 0)

    def unlock(site, mi, fbuf, off, blink, mreg, dreg):
        wf(pm, fbuf + OL.FRES_OFF, off)
        wf(pm, fbuf + OL.BLINK, blink)
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
        return dict(off=rf(pm, fbuf + OL.FRES_OFF, 3), blink=rf(pm, fbuf + OL.BLINK, 4),
                    seen=(r32(pm, SREC), r32(pm, SREC + 4), r32(pm, SREC + 8)), pc=pm.reg_read(UC_PPC_REG_PC),
                    sp=pm.reg_read(UC_PPC_REG_1), kept=kept)
    base_off, base_blink = [0.05, 0.04, 0.03], [0.2, 0.3, 0.4, 0.25]
    for site, mreg, dreg in [(OL.FB_A[0], 30, 28), (OL.FB_A[1], 30, 28), (OL.FB_B[0], 31, 27), (OL.FB_B[1], 31, 27)]:
        u = unlock(site, W.mi(1), FB, base_off, base_blink, mreg, dreg)
        check('FB1 unlock 0x%08X with no outline: FB1 untouched, the unlock called with the game\'s r3 / return' % site,
              (close(u['off'], base_off), close(u['blink'], base_blink), u['seen'], u['pc'], u['sp'], u['kept']),
              (True, True, (0x7F00BB00, site + 4, 1), site + 4, 0x7F00F000, []))
    ol(W.acc(1), 0, (255.0, 128.0, 0.0), 382.5, tint=0.0)
    for site, mreg, dreg in [(OL.FB_A[0], 30, 28), (OL.FB_B[1], 31, 27)]:
        u = unlock(site, W.mi(1), FB, base_off, base_blink, mreg, dreg)
        ref = OL.apply_ref({'off': base_off, 'blink': base_blink}, (255.0, 128.0, 0.0), 382.5, 0.0, 1.0)
        check('0x%08X: an edge-only orange outline (Alpha 382.5): g_fresnelOffset += colour x 1.5, blinkColor kept'
              % site, (close(u['off'], ref['off']), close(u['blink'], base_blink), u['seen'][2], u['kept']),
              (True, True, 1, []))
        u2 = unlock(site, W.mi(2), FB + 0x300, base_off, base_blink, mreg, dreg)
        check('... another instance\'s FB1 untouched', (close(u2['off'], base_off), close(u2['blink'], base_blink)),
              (True, True))
    ol(W.acc(6), 0, (255.0, 0.0, 0.0), 255.0, tint=128.0, fin=4)
    tick(2)
    e = find_e(W.acc(6))
    u = unlock(OL.FB_A[1], W.mi(6), FB, base_off, base_blink, 30, 28)
    ref = OL.apply_ref({'off': base_off, 'blink': base_blink}, (255.0, 0.0, 0.0), 255.0, 128.0, e['eff'])
    check('a red outline with a tint of 128, half faded in (weight %.2f): g_fresnelOffset and blinkColor (the '
          'overlay mixed toward red) as apply_ref' % e['eff'],
          (close(u['off'], ref['off']), close(u['blink'], ref['blink']), round(e['eff'], 4)), (True, True, 0.5))
    check('... the blink alpha grew (%.3f -> %.3f)' % (base_blink[3], u['blink'][3]), u['blink'][3] > base_blink[3],
          True)

    # ---- the clear
    for r in range(14, 32):
        pm.reg_write(REG(r), 0x4000 + r)
    pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
    pm.reg_write(UC_PPC_REG_3, 0x7F00BB00)
    pm.reg_write(UC_PPC_REG_10, 0x10)
    pm.reg_write(UC_PPC_REG_LR, RET)
    ensure(pm, 0x102F7020, 0x102F7024)
    check('before the clear: outlines in use', r32(pm, g) > 0, True)
    pm.emu_start(OL.SLOW_CLEAR, OL.CLEAR_BACK, count=200000)
    check('clear (training reset / match start / end): back at 0x02FB349C, r3 / r10 / LR as the game left them, '
          'every outline off', (pm.reg_read(UC_PPC_REG_PC), pm.reg_read(UC_PPC_REG_3), pm.reg_read(UC_PPC_REG_10),
                                pm.reg_read(UC_PPC_REG_LR), r32(pm, g),
                                [r32(pm, tab + OL.ENT * k) for k in range(OL.N_ENT)]),
          (OL.CLEAR_BACK, 0x7F00BB00, 0x10, RET, 0, [0] * OL.N_ENT))
    u = unlock(OL.FB_A[0], W.mi(1), FB, base_off, base_blink, 30, 28)
    check('... the next FB1 build untouched', (close(u['off'], base_off), close(u['blink'], base_blink)), (True, True))
    diag_tests(exe, orig)
    sys.exit(1 if acmd_ext_test.fails else 0)


def diag_tests(exe, orig):
    import diag_godfist_cave as G
    words, lab, _s = OL.build(orig, diag=True)
    check('diag build inside the region', max(words) < OL.LIMIT or max(a for a in words if a >= OL.CAVE) < OL.LIMIT,
          True)
    pm = machine(exe)
    for at, w in words.items():
        w32(pm, at, w)
    rec = 0x7F00C000
    ensure(pm, rec, rec + 0x2000)
    st = Asm(G.OSREPORT_VENEER)        # the veneer replaced by a recorder of (r3, r4 ... r10)
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
    pm.mem_write(PARAMS, struct.pack('>ifffffiiii', 0, 255.0, 255.0, 255.0, 255.0, 0.0, 0, 0, 0, 0))
    run(pm, lab['h_outline'], RET, {UC_PPC_REG_3: W.acc(0), UC_PPC_REG_5: STATE, UC_PPC_REG_6: FLAG,
                                     UC_PPC_REG_7: PARAMS})
    n = r32(pm, rec)
    lines = []
    for i in range(n):
        f = r32(pm, rec + 0x20 * (i + 1))
        s = bytes(pm.mem_read(f, 4)).decode('latin1')
        lines.append((s, r32(pm, rec + 0x20 * (i + 1) + 4), r32(pm, rec + 0x20 * (i + 1) + 8)))
    check('diag: S4OC / S4OD at the command (target 0, the accessor)', [(x[0], x[2]) for x in lines[:1]] +
          [x[0] for x in lines[1:2]], [('S4OC', W.acc(0)), 'S4OD'])
    ensure(pm, SMGR, SMGR + 0x1000)
    pm.mem_write(SMGR, b'\0' * 0xE80)
    pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
    pm.reg_write(UC_PPC_REG_3, SMGR)
    pm.reg_write(UC_PPC_REG_LR, RET)
    pm.emu_start(OL.TICK_AT, OL.TICK_AT + 4, count=200000)
    m = r32(pm, rec)
    check('diag: S4OT at the tick', bytes(pm.mem_read(r32(pm, rec + 0x20 * m), 4)).decode('latin1'), 'S4OT')


if __name__ == '__main__':
    main()
