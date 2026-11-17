#!/usr/bin/env python3
"""Test of tools/screen_invert_cave.py (Screen_Invert) on an executable with exe_v46z_camfx5's patches:

  python3 tools/screen_invert_test.py EXE.rpx

The cave's words are written into the emulated image (the file isn't patched). Run with the game's own code around
the hooks (unicorn):
  - the command tables (the game's CRC search, both script loaders, the handler fetch) for Screen_Invert and every
    earlier cave's commands (acmd_ext's, Line_Test, Var_Reset_Set, Hitbox_Hold, Effect_Camera);
  - Screen_Invert's handler (start / replace / end, fades, the step);
  - the tick (0x032EFB78: the game's screen-effect update 0x0334B250 on a manager with no Screen_Tint, then the
    filter's frame): fades in / held / out frame by frame;
  - the lock (0x03433544, r30 a post-effect object): the matrix the lock sees (a recording stub in CTR) = the filter
    after the game's matrix (screen_invert_cave.compose / filter_matrix, the Python reference), r3 / r4 / the return
    address the game's; untouched with no filter;
  - the clear (0x02FB3498 -> ts_tick_cave.py's tsu_clear -> si_clear -> 0x02FB349C): the filter off;
  - the diag build's lines (the OSReport veneer replaced by a recorder).
The builder 0x034333B0 is paired-single code, which unicorn can't run: its straight-line matrix part
(0x034333E4-0x03433540) runs here in a small Python interpreter of the instructions it uses (lfs / stfs / fmuls /
fmadds / fsubs / psq_l / psq_st / ps_muls0/1 / ps_madds0/1 / ps_merge00), on the game's own constants (the YCbCr
matrices 0x034335A8 writes): neutral parameters give the identity, Screen_Tint's give the tint, and every word of
+0x100-+0x12C is written each call (so the cave can change it in place); the cave's own maths then runs on that
matrix in unicorn.
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_cave as C  # noqa: E402
import screen_invert_cave as SI  # noqa: E402
import acmd_ext_test  # noqa: E402
from acmd_ext_test import check, r32, w32, run, RET, CRC_TABLE, COUNT, SIZES, HANDLERS, BUF  # noqa: E402
from stage_slot_test import machine  # noqa: E402
from ppcasm import Asm  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_0, UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5,  # noqa: E402
                               UC_PPC_REG_6, UC_PPC_REG_7, UC_PPC_REG_10, UC_PPC_REG_12, UC_PPC_REG_29,
                               UC_PPC_REG_LR, UC_PPC_REG_CTR, UC_PPC_REG_MSR, UC_PPC_REG_PC)

REG = lambda n: UC_PPC_REG_0 + n          # noqa: E731
ACC, PARAMS, STATE, FLAG = 0x7F001000, 0x7F001400, 0x7F001600, 0x7F001700
OBJ = 0x7F002000                          # a post-effect object (0x400 bytes)
LREC = 0x7F002800                         # the lock stub's record
SMGR = 0x7F010000                         # a screen-effect manager with no entries (0xE80 bytes)
STUB = 0x04BE4000                         # stubs past the cave (in the emulated code's grown end)
TOL = 2e-5


def fb(v):
    return struct.unpack('>I', struct.pack('>f', v))[0]


def rf(mu, a, n):
    return list(struct.unpack('>%df' % n, mu.mem_read(a, 4 * n)))


def wf(mu, a, vals):
    mu.mem_write(a, struct.pack('>%df' % len(vals), *vals))


def flat(m):
    return [x for row in m for x in row]


def close(a, b, tol=TOL):
    a, b = flat(a) if isinstance(a[0], list) else a, flat(b) if isinstance(b[0], list) else b
    return len(a) == len(b) and all(abs(x - y) <= tol * max(1, abs(y)) for x, y in zip(a, b))


def ensure(mu, lo, hi):
    mapped = [(b, e) for b, e, _p in mu.mem_regions()]
    a = lo & ~0xFFF
    while a < hi:
        if not any(b <= a <= e for b, e in mapped):
            mu.mem_map(a, 0x1000)
        a += 0x1000


# ---- the builder's straight-line matrix code, in Python (paired singles) --------------------------------------------
def f32(v):
    return struct.unpack('>f', struct.pack('>f', v))[0]


def builder(orig, fields):
    """run 0x034333E4-0x03433540 (the builder's matrix part) on a post-effect object whose fields (+0x300-+0x37C) are
    `fields` {offset: float}; the YCbCr matrices as 0x034335A8 writes them. -> {offset: float} of what it stored"""
    fl = lambda a: struct.unpack('>f', struct.pack('>I', orig(a)))[0]     # noqa: E731
    mem = {}
    # 0x034335A8's stores (static init): replayed from its own words
    regs_f = {}
    gpr = {}
    a = 0x034335A8
    while orig(a) != 0x4E800020:
        x = orig(a)
        op, d, ra = x >> 26, (x >> 21) & 31, (x >> 16) & 31
        simm = x & 0xFFFF
        simm -= 0x10000 if simm & 0x8000 else 0
        if op == 15:
            gpr[d] = (simm << 16) & 0xFFFFFFFF
        elif op == 14:
            gpr[d] = ((gpr[ra] if ra else 0) + simm) & 0xFFFFFFFF
        elif op == 48:
            regs_f[d] = fl(gpr[ra] + simm)
        elif op == 52:
            mem[gpr[ra] + simm] = regs_f[d]
        else:
            raise ValueError('init 0x%08X: 0x%08X' % (a, x))
        a += 4
    obj = 0x80000000
    for off, v in fields.items():
        mem[obj + off] = f32(v)
    gpr = {30: obj}
    fpr = {}
    stored = {}

    def rd(addr):
        if addr in mem:
            return mem[addr]
        if obj <= addr < obj + 0x400:
            return 0.0
        return fl(addr)
    a = 0x034333E4
    while a < 0x03433544:
        x = orig(a)
        op, d, ra, rb, rc = x >> 26, (x >> 21) & 31, (x >> 16) & 31, (x >> 11) & 31, (x >> 6) & 31
        simm = x & 0xFFFF
        simm -= 0x10000 if simm & 0x8000 else 0
        d12 = x & 0xFFF
        d12 -= 0x1000 if d12 & 0x800 else 0
        if op == 15:
            gpr[d] = (simm << 16) & 0xFFFFFFFF
        elif op == 14:
            gpr[d] = ((gpr[ra] if ra else 0) + simm) & 0xFFFFFFFF
        elif op == 48:
            v = rd(gpr[ra] + simm)
            fpr[d] = (v, v)
        elif op == 52:
            mem[gpr[ra] + simm] = fpr[d][0]
            stored[gpr[ra] + simm] = fpr[d][0]
        elif op == 59:
            xo = (x >> 1) & 31
            A_, B_, C_ = fpr.get(ra, (0, 0))[0], fpr.get(rb, (0, 0))[0], fpr.get(rc, (0, 0))[0]
            r = {25: lambda: A_ * C_, 29: lambda: A_ * C_ + B_, 28: lambda: A_ * C_ - B_, 20: lambda: A_ - B_,
                 21: lambda: A_ + B_}[xo]()
            fpr[d] = (f32(r), f32(r))
        elif op == 56:
            b = gpr[ra] + d12
            fpr[d] = (rd(b), rd(b + 4))
        elif op == 60:
            b = gpr[ra] + d12
            mem[b], mem[b + 4] = fpr[d]
            stored[b], stored[b + 4] = fpr[d]
        elif op == 4:
            xo5, xo10 = (x >> 1) & 31, (x >> 1) & 1023
            A_, B_, C_ = fpr[ra], fpr.get(rb, (0, 0)), fpr.get(rc, (0, 0))
            if xo10 == 528:
                r = (A_[0], B_[0])
            elif xo5 == 12:
                r = (A_[0] * C_[0], A_[1] * C_[0])
            elif xo5 == 13:
                r = (A_[0] * C_[1], A_[1] * C_[1])
            elif xo5 == 14:
                r = (A_[0] * C_[0] + B_[0], A_[1] * C_[0] + B_[1])
            elif xo5 == 15:
                r = (A_[0] * C_[1] + B_[0], A_[1] * C_[1] + B_[1])
            else:
                raise ValueError('ps 0x%08X at 0x%08X' % (x, a))
            fpr[d] = (f32(r[0]), f32(r[1]))
        elif op in (31, 32, 19):       # mtctr / lwz / the rest: not in the matrix
            pass
        else:
            raise ValueError('op %d at 0x%08X' % (op, a))
        a += 4
    return {k - obj: v for k, v in stored.items() if obj <= k < obj + 0x400}


NEUTRAL = {0x304: 1, 0x308: 1, 0x30C: 1, 0x310: 1, 0x32C: 1, 0x330: 1, 0x334: 1, 0x338: 1, 0x354: 1, 0x358: 1,
           0x36C: 1, 0x370: 1, 0x374: 1, 0x378: 1}       # the post-effect's constructor (0x03433068)


def builder_tests(orig):
    out = builder(orig, NEUTRAL)
    m = [[out[0x100 + 16 * i + 4 * j] for j in range(4)] for i in range(3)]
    check('builder (Python, its own words): every word of +0x100-+0x12C written each call',
          sorted(o for o in out if 0x100 <= o < 0x130), list(range(0x100, 0x130, 4)))
    check('... the constructor\'s parameters give the identity (rows R / G / B, offsets 0)',
          close(m, [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]], 2e-3), True)
    # Screen_Tint's colour (0x0334AC8C -> vt +0xC -> 0x03448034: +0x35C-+0x368 RGBA, +0x378 = 1 - A)
    t = dict(NEUTRAL)
    t.update({0x35C: 0.08, 0x360: 0.09, 0x364: 0.17, 0x368: 0.7, 0x378: 0.3})
    out = builder(orig, t)
    m2 = [[out[0x100 + 16 * i + 4 * j] for j in range(4)] for i in range(3)]
    want = [[0.3, 0, 0, 0.08 * 0.7], [0, 0.3, 0, 0.09 * 0.7], [0, 0, 0.3, 0.17 * 0.7]]
    check('... Screen_Tint\'s (0.08, 0.09, 0.17) at 70 %%: x 0.3 + colour x 0.7 (the tint the game shows): %s' %
          [round(v, 3) for v in flat(m2)], close(m2, want, 2e-3), True)
    # saturation 0 (vt +0x2C: +0x30C / +0x310 the chroma scale)
    g = dict(NEUTRAL)
    g.update({0x30C: 0, 0x310: 0})
    out = builder(orig, g)
    m3 = [[out[0x100 + 16 * i + 4 * j] for j in range(4)] for i in range(3)]
    check('... chroma scale 0 (vt +0x2C): every row the luma (0.299, 0.587, 0.114)',
          close(m3, [list(SI.LUMA) + [0]] * 3, 2e-3), True)
    return m2


def main():
    exe = sys.argv[1]
    orig = SI.rpx_reader(exe)
    words, lab, s = SI.build(orig)
    om, pm = machine(exe), machine(exe)
    for at, w in words.items():
        w32(pm, at, w)
    check('present() on the patched words', SI.present(lambda x: words.get(x, orig(x))), True)
    check('present() on the unpatched exe', SI.present(orig), False)
    try:
        SI.build(lambda x: words.get(x, orig(x)))
        check('building over itself refused', False, True)
    except AssertionError:
        check('building over itself refused', True, True)
    inside = [a for a in words if SI.CAVE <= a < SI.LIMIT]
    check('the cave inside its region (0x04BE2000-0x04BE3000)', (min(inside), max(inside) < SI.LIMIT),
          (SI.CAVE, True))
    others = sorted(a for a in words if not SI.CAVE <= a < SI.LIMIT)
    check('words outside the cave: the lock, the tick, tsu_clear\'s last word and the 4 command-table fallbacks',
          others, sorted([SI.LOCK_AT, SI.TICK_AT, s['clear_at'], s['lk_none'], s['s1'], s['s2'], s['f']]))
    check('... the lock and the tick are bl (to the cave), the clear a b',
          [words[SI.LOCK_AT] & 3, words[SI.TICK_AT] & 3, words[s['clear_at']] & 3], [1, 1, 0])
    check('... the earlier caves\' fallbacks were Effect_Camera\'s (0x04BE0000-0x04BE2000): chained',
          [0x04BE0000 <= LT_target(s[k], s[k + '_word']) < 0x04BE2000 for k in ('lk_none', 's1', 's2', 'f')],
          [True] * 4)

    # ---- command tables
    pairs = [(r32(om, CRC_TABLE + 8 * i), r32(om, CRC_TABLE + 8 * i + 4)) for i in range(COUNT)]
    check('Screen_Invert CRC not a game command', SI.CMD_CRC in dict(pairs), False)
    check('... nor an acmd_ext command', SI.CMD_CRC in [C.crc(c[0]) for c in C.COMMANDS], False)

    def lookup(mu, crc):
        run(mu, 0x02BEE154, RET, {UC_PPC_REG_3: crc})
        return mu.reg_read(UC_PPC_REG_3)
    check('vanilla CRCs keep their index', [hex(c) for c, i in pairs[::7] if lookup(pm, c) != i], [])
    check('acmd_ext CRCs keep theirs', [lookup(pm, C.crc(c[0])) for c in C.COMMANDS],
          [C.NEW_BASE + k for k in range(len(C.COMMANDS))])
    earlier = {n: zlib.crc32(n.encode()) & 0xFFFFFFFF
               for n in ('Line_Test', 'Var_Reset_Set', 'Hitbox_Hold', 'Effect_Camera')}
    check('earlier caves\' commands (Line_Test, Var_Reset_Set, Hitbox_Hold, Effect_Camera) keep their index',
          [lookup(pm, c) for c in earlier.values()], [lookup(om, c) for c in earlier.values()])
    check('... which the unpatched exe has (1096, 2000, 2100, 2200)', [lookup(om, c) for c in earlier.values()],
          [1096, 2000, 2100, 2200])
    check('Screen_Invert -> its index (2300)', lookup(pm, SI.CMD_CRC), SI.SI_INDEX)
    check('unknown CRC -> -1', lookup(pm, 0x12345678), 0xFFFFFFFF)
    idx = dict(pairs)
    size = {i: r32(om, SIZES + 4 * i) for _, i in pairs}
    script = [0xB738EABD, SI.CMD_CRC, 0x42ACFE7D, earlier['Effect_Camera'], earlier['Line_Test'],
              earlier['Hitbox_Hold'], SI.CMD_CRC]
    want_idx = [idx[0xB738EABD], SI.SI_INDEX, idx[0x42ACFE7D], 2200, 1096, 2100, SI.SI_INDEX]
    want_size = [size[want_idx[0]], 11, size[want_idx[2]], 12, 11, 3, 11]
    for loop, (start, stop, regs) in enumerate([
            (0x02BEE2B4, 0x02BEE2D8, {REG(28): BUF, UC_PPC_REG_29: 0, REG(30): len(script), UC_PPC_REG_4: SIZES}),
            (0x02BEE3B4, 0x02BEE3D8, {REG(28): BUF, UC_PPC_REG_4: 0, UC_PPC_REG_29: len(script), REG(30): SIZES})]):
        pm.mem_write(BUF, b'\0' * 0x1000)
        o, offs = 0, []
        for c, sz in zip(script, want_size):
            w32(pm, BUF + 4 * o, c)
            offs.append(o)
            o += sz
        run(pm, start, stop, regs)
        check('loader %d: indices (Hitbox, Screen_Invert, FRAME, Effect_Camera, Line_Test, Hitbox_Hold, '
              'Screen_Invert)' % (loop + 1), [r32(pm, BUF + 4 * x) for x in offs], want_idx)
        check('loader %d: words stepped (Screen_Invert 11)' % (loop + 1),
              pm.reg_read(UC_PPC_REG_29 if loop == 0 else UC_PPC_REG_4), sum(want_size))

    def fetch(mu, i):
        run(mu, 0x02BEE84C, 0x02BEE854, {UC_PPC_REG_7: i, UC_PPC_REG_29: HANDLERS, UC_PPC_REG_12: 0x55})
        return mu.reg_read(UC_PPC_REG_0)
    check('vanilla handlers unchanged', [i for _, i in pairs[::11] if fetch(pm, i) != r32(om, HANDLERS + 4 * i)], [])
    check('acmd_ext handlers unchanged', [fetch(pm, C.NEW_BASE + k) for k in range(len(C.COMMANDS))],
          [fetch(om, C.NEW_BASE + k) for k in range(len(C.COMMANDS))])
    check('Line_Test / Var_Reset_Set / Hitbox_Hold / Effect_Camera handlers kept',
          [fetch(pm, i) for i in (1096, 2000, 2100, 2200)], [fetch(om, i) for i in (1096, 2000, 2100, 2200)])
    check('Screen_Invert handler', fetch(pm, SI.SI_INDEX), lab['h_inv'])

    pm.reg_write(UC_PPC_REG_MSR, pm.reg_read(UC_PPC_REG_MSR) | 0x2000)
    st = lab['si_st']

    def state():
        return dict(ph=r32(pm, st), w=rf(pm, st + 4, 1)[0], left=r32(pm, st + 0x10), A=rf(pm, st + 0x30, 12))

    def inv(mode, strength=1.0, frames=0, fin=0, fout=0, sat=1.0, bri=1.0, rgb=(0.0, 0.0, 0.0), execute=1):
        w32(pm, STATE + 4, 0x1000)
        w32(pm, STATE + 8, 0xFFFFFFFF)
        pm.mem_write(FLAG + 8, bytes([execute]))
        pm.mem_write(PARAMS, struct.pack('>ifiiifffff', mode, strength, frames, fin, fout, sat, bri, *rgb))
        for r in range(14, 32):
            pm.reg_write(REG(r), 0x1000 + r)
        run(pm, lab['h_inv'], RET, {UC_PPC_REG_3: ACC, UC_PPC_REG_5: STATE, UC_PPC_REG_6: FLAG,
                                     UC_PPC_REG_7: PARAMS})
        kept = [r for r in range(14, 32) if pm.reg_read(REG(r)) != 0x1000 + r]
        return dict(ret=pm.reg_read(UC_PPC_REG_3), step=r32(pm, STATE + 4) - 0x1000, kept=kept)

    # ---- the tick: the effect manager's bl 0x0334B250 at 0x032EFB78, r3 a screen-effect manager with no entries
    ensure(pm, SMGR, SMGR + 0x1000)
    pm.mem_write(SMGR, b'\0' * 0xE80)

    def tick(n=1):
        out = []
        for _ in range(n):
            pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
            pm.reg_write(UC_PPC_REG_3, SMGR)
            pm.reg_write(REG(30), 0x7F00E000)      # (the effect manager's r30: read after the call, not by it)
            pm.emu_start(SI.TICK_AT, SI.TICK_AT + 4, count=100000)
            out.append(state())
        return out

    def A_ref(w, s_, k, b, rgb):
        return flat(SI.filter_matrix(w, s_, k, b, rgb))

    r = inv(1, 1.0, 0, 0, 0)
    check('Screen_Invert(1, full): returns 2, steps 11 words, callee-saved kept', (r['ret'], r['step'], r['kept']),
          (2, 44, []))
    s0 = state()
    check('... showing at once (FadeIn 0): phase held, w 1, A = the negative (-I, offsets 1)',
          (s0['ph'], s0['w'], close(s0['A'], [-1, 0, 0, 1, 0, -1, 0, 1, 0, 0, -1, 1])), (2, 1.0, True))
    tk = tick(3)
    check('... ticks: held with Frames 0 (no count), w 1', [(t['ph'], t['w']) for t in tk], [(2, 1.0)] * 3)
    check('... the game\'s screen-effect update ran (its 10 entries looked at: the winners -1)',
          (r32(pm, SMGR + 0xE6C), r32(pm, SMGR + 0xE70)), (0xFFFFFFFF, 0xFFFFFFFF))
    inv(0, fout=4)
    tk = tick(5)
    check('Mode 0, FadeOut 4: w 0.75, 0.5, 0.25, 0, off', [round(t['w'], 4) for t in tk[:4]] + [tk[4]['ph']],
          [0.75, 0.5, 0.25, 0.0, 0])
    check('... A at w 0.5 = (1 - w) I + w F (the grey: 0 x, offsets 0.5)',
          close(tk[1]['A'], A_ref(0.5, 1.0, 1.0, 1.0, (0, 0, 0))) and close(tk[1]['A'], [0, 0, 0, 0.5, 0, 0, 0, 0.5,
                                                                                        0, 0, 0, 0.5]), True)
    inv(0, fout=4)
    check('Mode 0 with nothing showing: nothing', state()['ph'], 0)
    inv(1, 0.5, 6, 4, 2, 1.0, 1.0)
    tk = tick(14)
    check('Strength 0.5, Frames 6, FadeIn 4, FadeOut 2: w by frame (from 0 at the command\'s frame; full on the 4th, '
          'its 6 Frames counted after that, out over 2)',
          [round(t['w'], 4) for t in tk], [0.25, 0.5, 0.75, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.0, 0.0, 0.0])
    check('... phases (1 in, 2 held, 3 out, 0 off)', [t['ph'] for t in tk],
          [1, 1, 1, 2, 2, 2, 2, 2, 2, 3, 3, 0, 0, 0])
    xv2 = (1.0, 0.0, 0.8, (19.0, 37.0, 60.0))
    inv(1, xv2[0], 0, 0, 0, xv2[1], xv2[2], xv2[3])
    check('XV2\'s time-stop filter (negative, grey, x 0.8, + (19, 37, 60)): A = the reference',
          close(state()['A'], A_ref(1, *xv2)), True)
    inv(1, 1.0, 0, 10, 0)
    tk = tick(2)
    check('a new Screen_Invert over a showing one fades from where it is (w 1 -> held, FadeIn ignored at 1)',
          [(t['ph'], round(t['w'], 3)) for t in tk], [(2, 1.0), (2, 1.0)])
    inv(1, 1.0, 1, 0, 0)
    tk = tick(3)
    check('Frames 1, FadeOut 0: one held frame, then off the next', [(t['ph'], t['w']) for t in tk],
          [(3, 1.0), (0, 0.0), (0, 0.0)])
    inv(1, 1.0, 0, 0, 0)
    inv(0, fout=0)
    check('Mode 0, FadeOut 0: off at once', (state()['ph'], state()['w']), (0, 0.0))
    inv(1, 1.0, 0, 0, 0, execute=0)
    check('not executing: nothing, still stepped', state()['ph'], 0)
    inv(1, 1.0, -5, 3, -1)
    check('negative Frames / FadeOut: 0 (held / at once)', (state()['left'], state()['ph']), (0, 1))

    # ---- the lock: 0x03433544 (bctrl) -> si_lock, r30 the object, ctr a recording lock stub
    ensure(pm, OBJ, OBJ + 0x1000)
    stub = Asm(STUB)
    stub.asm("""
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        stw r3, 0(r12)
        stw r4, 4(r12)
        mflr r0
        stw r0, 8(r12)
        lwz r9, 0xC(r12)
        addi r9, r9, 1
        stw r9, 0xC(r12)
        li r10, 0
lk_cp:
        add r11, r30, r10
        lwz r0, 0x100(r11)
        add r11, r12, r10
        stw r0, 0x10(r11)
        addi r10, r10, 4
        cmplwi r10, 0x30
        blt lk_cp
        li r3, 0x5150
        blr
""" % (LREC >> 16, LREC & 0xFFFF))
    for i, w in enumerate(stub.words()):
        w32(pm, STUB + 4 * i, w)
    pm.mem_write(LREC, b'\0' * 0x40)
    game_m = builder_tests(orig)                     # the tint matrix the builder makes (Python run of its words)

    nlock = [0, 0]

    def lock(m):
        nlock[0] += 1
        nlock[1] += r32(pm, st) != 0
        wf(pm, OBJ + 0x100, flat(m))
        for r in range(14, 32):
            pm.reg_write(REG(r), 0x3000 + r)
        pm.reg_write(REG(30), OBJ)
        pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
        pm.reg_write(UC_PPC_REG_3, 0x7F00ABC0)
        pm.reg_write(UC_PPC_REG_4, 0)
        pm.reg_write(UC_PPC_REG_CTR, STUB)
        pm.emu_start(SI.LOCK_AT, SI.LOCK_AT + 4, count=100000)
        seen = rf(pm, LREC + 0x10, 12)
        kept = [r for r in range(14, 32) if pm.reg_read(REG(r)) != (OBJ if r == 30 else 0x3000 + r)]
        return dict(seen=seen, after=rf(pm, OBJ + 0x100, 12), r3=r32(pm, LREC), r4=r32(pm, LREC + 4),
                    lr=r32(pm, LREC + 8), ret=pm.reg_read(UC_PPC_REG_3), sp=pm.reg_read(UC_PPC_REG_1), kept=kept)
    inv(0, fout=0)
    ident = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]
    lk = lock(game_m)
    check('lock, no filter: the lock sees the game\'s matrix as it was; r3 / r4 its own, it returns to 0x03433548, '
          'sp / callee-saved kept', (close(lk['seen'], flat(game_m)), lk['r3'], lk['r4'], lk['lr'], lk['ret'],
                                     lk['sp'], lk['kept']),
          (True, 0x7F00ABC0, 0, SI.LOCK_AT + 4, 0x5150, 0x7F00F000, []))
    inv(1, 1.0, 0, 0, 0)
    lk = lock(ident)
    check('full negative on the identity: the lock sees -I with offsets 1 (out = 1 - in)',
          close(lk['seen'], [-1, 0, 0, 1, 0, -1, 0, 1, 0, 0, -1, 1]), True)
    lk = lock(game_m)
    check('full negative after Screen_Tint\'s matrix: compose(A, M) (the tint inverted with the picture)',
          close(lk['seen'], flat(SI.compose(SI.filter_matrix(1, 1, 1, 1, (0, 0, 0)), game_m))), True)
    for args_ in ((0.5, 1.0, 1.0, (0, 0, 0)), xv2, (0.0, 0.0, 1.0, (0, 0, 0)), (1.0, 0.3, 1.2, (-10, 5, 40))):
        inv(1, args_[0], 0, 0, 0, args_[1], args_[2], args_[3])
        lk = lock(game_m)
        check('Strength %g, Saturation %g, Brightness %g, add %s: compose(A, M)' % (args_[0], args_[1], args_[2],
                                                                                   args_[3]),
              close(lk['seen'], flat(SI.compose(SI.filter_matrix(1, *args_), game_m))), True)
    inv(0, fout=0)
    inv(1, 1.0, 0, 4, 0)
    tick(2)
    lk = lock(game_m)
    check('half-way through a fade-in (w 0.5): the negative at 0.5',
          close(lk['seen'], flat(SI.compose(SI.filter_matrix(0.5, 1, 1, 1, (0, 0, 0)), game_m))), True)
    px = [0.8, 0.2, 0.4]
    inv(1, 1.0, 0, 0, 0)
    lk = lock(ident)
    m = [lk['seen'][0:4], lk['seen'][4:8], lk['seen'][8:12]]
    out = [sum(m[i][j] * px[j] for j in range(3)) + m[i][3] for i in range(3)]
    check('a pixel (0.8, 0.2, 0.4) through the shader\'s dot4 with the lock\'s matrix: (0.2, 0.8, 0.6)',
          close(out, [0.2, 0.8, 0.6]), True)

    # ---- the clear: the slow manager's clear-all (b tsu_clear at 0x02FB3498) -> si_clear -> back at 0x02FB349C
    inv(1, 1.0, 0, 0, 0)
    ensure(pm, 0x102F7020, 0x102F7024)
    for r in range(14, 32):
        pm.reg_write(REG(r), 0x4000 + r)
    pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
    pm.reg_write(UC_PPC_REG_3, 0x7F00BB00)
    pm.reg_write(UC_PPC_REG_LR, RET)
    pm.emu_start(SI.SLOW_CLEAR, SI.CLEAR_BACK, count=200000)
    check('clear (training reset / match start / end): back at 0x02FB349C, r3 / r10 as the game left them, the '
          'filter off', (pm.reg_read(UC_PPC_REG_PC), pm.reg_read(UC_PPC_REG_3), pm.reg_read(UC_PPC_REG_10),
                         state()['ph'], state()['w']), (SI.CLEAR_BACK, 0x7F00BB00, 0x10, 0, 0.0))
    lk = lock(game_m)
    check('... and the next lock leaves the game\'s matrix alone', close(lk['seen'], flat(game_m)), True)
    dbg = [r32(pm, st + o) for o in (0x60, 0x68, 0x6C)]
    check('counters: commands run, locks seen, matrices changed (%d, %d)' % tuple(nlock), (dbg[0] > 15, dbg[1], dbg[2]),
          (True, nlock[0], nlock[1]))
    diag_tests(exe, orig)
    sys.exit(1 if acmd_ext_test.fails else 0)


def LT_target(at, w):
    import line_test_cave as LT
    return LT.bdecode(at, w) if w >> 26 == 18 else 0


def diag_tests(exe, orig):
    """the diag build: its lines (the OSReport veneer replaced by a recorder)"""
    import diag_godfist_cave as G
    words, lab, _s = SI.build(orig, diag=True)
    mu = machine(exe)
    for at, w in words.items():
        w32(mu, at, w)
    check('diag build: in the region', max(a for a in words if a >= SI.CAVE) < SI.LIMIT, True)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    rec = 0x7F006000
    ensure(mu, rec, rec + 0x8000)
    ensure(mu, OBJ, OBJ + 0x1000)
    mu.mem_write(rec, b'\0' * 0x8000)
    st = Asm(STUB + 0x200)
    st.asm("""
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        lwz r11, 0(r12)
        addi r11, r11, 1
        stw r11, 0(r12)
        slwi r11, r11, 5
        add r11, r11, r12
        stw r3, 0(r11)
        stw r4, 4(r11)
        stw r5, 8(r11)
        stw r6, 0xC(r11)
        stw r7, 0x10(r11)
        stw r8, 0x14(r11)
        stw r9, 0x18(r11)
        stw r10, 0x1C(r11)
        blr
lockstub:
        li r3, 0
        blr
""" % (rec >> 16, rec & 0xFFFF))
    for i, w in enumerate(st.words()):
        w32(mu, STUB + 0x200 + 4 * i, w)
    for i, w in enumerate((0x3D800000 | (STUB + 0x200) >> 16, 0x618C0000 | ((STUB + 0x200) & 0xFFFF), 0x7D8903A6,
                           0x4E800420)):
        w32(mu, G.OSREPORT_VENEER + 4 * i, w)
    fmts = {lab[n]: f.split()[0] for n, f in SI.DIAG_FMTS}

    def lines():
        n = r32(mu, rec)
        out = []
        for k in range(1, n + 1):
            v = [r32(mu, rec + 32 * k + 4 * i) for i in range(8)]
            out.append((fmts.get(v[0], '?'), v[1:]))
        mu.mem_write(rec, b'\0' * 4)
        return out
    w32(mu, STATE + 4, 0x1000)
    w32(mu, STATE + 8, 0)
    mu.mem_write(FLAG + 8, b'\1')
    mu.mem_write(PARAMS, struct.pack('>ifiiifffff', 1, 1.0, 90, 0, 10, 0.0, 0.8, 19.0, 37.0, 60.0))
    run(mu, lab['h_inv'], RET, {UC_PPC_REG_3: ACC, UC_PPC_REG_5: STATE, UC_PPC_REG_6: FLAG, UC_PPC_REG_7: PARAMS})
    ls = lines()
    check('diag: a command prints S4IC (mode, strength, frames, in, out, saturation, brightness) and S4ID (the add, '
          'phase, w)', [(n, v[:7] if n == 'S4IC' else v[:5]) for n, v in ls],
          [('S4IC', [1, fb(1.0), 90, 0, 10, fb(0.0), fb(0.8)]),
           ('S4ID', [fb(f32(v) * f32(1 / 255)) for v in (19, 37, 60)] + [2, fb(1.0)])])
    m = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]
    out = []
    for f in range(32):
        wf(mu, OBJ + 0x100, m)
        mu.reg_write(REG(30), OBJ)
        mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
        mu.reg_write(UC_PPC_REG_CTR, STUB + 0x200 + 4 * len(st.words()) - 8)
        mu.emu_start(SI.LOCK_AT, SI.LOCK_AT + 4, count=100000)
        out.append([n for n, _v in lines()])
    check('diag: each lock of the first 30 after a command prints S4IS, S4IG / S4IH (the game\'s), S4IO / S4IP '
          '(ours)', out[0], ['S4IS', 'S4IG', 'S4IH', 'S4IO', 'S4IP'])
    check('... the 31st (the 30th since) does, the 32nd doesn\'t (every 30th after the first 30)',
          (len(out[29]), len(out[30]), out[31]), (5, 5, []))
    wf(mu, OBJ + 0x100, m)
    mu.reg_write(UC_PPC_REG_CTR, STUB + 0x200 + 4 * len(st.words()) - 8)
    mu.reg_write(REG(30), OBJ)
    mu.emu_start(SI.LOCK_AT, SI.LOCK_AT + 4, count=100000)
    mu.mem_write(rec, b'\0' * 4)
    wf(mu, OBJ + 0x100, m)
    mu.reg_write(UC_PPC_REG_CTR, STUB + 0x200 + 4 * len(st.words()) - 8)
    mu.reg_write(REG(30), OBJ)
    mu.emu_start(SI.LOCK_AT, SI.LOCK_AT + 4, count=100000)
    v = dict((n, vv) for n, vv in lines())
    want = flat(SI.compose(SI.filter_matrix(1, 1.0, 0.0, 0.8, (19, 37, 60)), [m[0:4], m[4:8], m[8:12]]))
    check('... the 34th lock: none', v, {})
    sst = lab['si_st']
    w32(mu, sst + 0x64, 60)
    wf(mu, OBJ + 0x100, m)
    mu.reg_write(UC_PPC_REG_CTR, STUB + 0x200 + 4 * len(st.words()) - 8)
    mu.reg_write(REG(30), OBJ)
    mu.emu_start(SI.LOCK_AT, SI.LOCK_AT + 4, count=100000)
    v = dict((n, vv) for n, vv in lines())
    got = [struct.unpack('>f', struct.pack('>I', x))[0] for x in v.get('S4IO', [0] * 7)[:6] + v.get('S4IP', [0] * 7)[:6]]
    check('... the 61st: S4IG the game\'s identity, S4IO / S4IP the filtered matrix (XV2\'s stop)',
          (v.get('S4IG', [])[:6], close(got, want)), ([fb(x) for x in m[:6]], True))
    w32(mu, sst, 0)
    w32(mu, sst + 0x68, SI.DIAG_IDLE - 1)
    wf(mu, OBJ + 0x100, m)
    mu.reg_write(UC_PPC_REG_CTR, STUB + 0x200 + 4 * len(st.words()) - 8)
    mu.reg_write(REG(30), OBJ)
    mu.emu_start(SI.LOCK_AT, SI.LOCK_AT + 4, count=100000)
    check('no filter: every %dth lock prints S4IS / S4IG / S4IH (the builder runs; the game\'s own matrix)' %
          SI.DIAG_IDLE, [n for n, _v in lines()], ['S4IS', 'S4IG', 'S4IH'])


if __name__ == '__main__':
    main()
