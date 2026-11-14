#!/usr/bin/env python3
"""Kirby's Hero / Sephiroth copy fix v1 (fighters/kirby/specials.md "Hero copy fix v1"): runs the patched executable's
own code in unicorn.

  python3 tools/kirby_hero_copy_fix_test.py PATCHED.rpx BASE.rpx [fighters/kirby/kirby.c]

PATCHED = BASE + tools/copy_fx_cave.py's SILENCE (exe_v45g = exe_v45f + it, exe_v46e = exe_v46d + it).
- the words: only copy_fx_cave.py's cave differs from BASE in the code, and its hook / trampoline are as before;
- SILENCE through the real chain (MotionAnimcmdModule vt +0x6C 0x02760CE4 -> the trampoline -> the cave -> the
  game's agent clear 0x02BEE9B8): the four agents (game, expression, sound, effect) of a module whose agents hold
  a script are cleared, the late bind is cancelled (+0x1C = -2: the late update 0x02760DB0 skips -2), callee-saved
  registers kept; set 0 still goes on to the game's +0x6C;
- Kirby's New_Var slots from MSC with no New_Var declared (the user's hypothesis, crash fix v2's khm_* state):
  the game's MSC WorkModule handler 0x0200E898 (op 7 set int, op 6 get int, op 0 set float) and the fighters'
  get_float (vt +0x44) on a fighter WorkModule (vtable 0x1013A1C0) for every slot in kirby.c's table: unset slots
  read 0, every write is kept and read back, ints and floats, another object's slots apart, the copy-state int
  0x1000008A (Kirby's panel gauge) as a plain int.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import copy_fx_cave as FX  # noqa: E402
import rpx_patch as R  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_6,  # noqa: E402
                               UC_PPC_REG_FPR1, UC_PPC_REG_LR, UC_PPC_REG_MSR)

FAIL = []
MEM = 0x7E000000
MSC_WM = 0x0200E898              # MSC WorkModule handler (r3 WorkModule, r4 {args, count})
FGET = 0x02F1DBE4                # fighters' WorkModule get_float (vt +0x44)
FIGHTER_WM_VT = 0x1013A1C0
LATE_SKIP = 0x02760E48           # the late update: lwz r0, 0x1C(r31); cmpwi r0, -2; beq (no bind)


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        FAIL.append(what)


def r32(mu, a):
    return struct.unpack('>I', mu.mem_read(a, 4))[0]


def w32(mu, a, v):
    mu.mem_write(a, struct.pack('>I', v & 0xFFFFFFFF))


def f2b(v):
    return struct.unpack('>I', struct.pack('>f', v))[0]


def run(mu, start, regs, fpr1=None, count=2000000):
    mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
    for r, v in regs.items():
        mu.reg_write(r, v & 0xFFFFFFFF)
    if fpr1 is not None:
        mu.reg_write(UC_PPC_REG_FPR1, struct.unpack('>Q', struct.pack('>d', fpr1))[0])
    for r in range(14, 32):
        mu.reg_write(UC_PPC_REG_3 + r - 3, 0x1000 + r)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    mu.emu_start(start, RET, count=count)
    bad = [r for r in range(14, 32) if mu.reg_read(UC_PPC_REG_3 + r - 3) != 0x1000 + r]
    return mu.reg_read(UC_PPC_REG_3), struct.unpack('>d', struct.pack('>Q', mu.reg_read(UC_PPC_REG_FPR1)))[0], bad


def text_words(path):
    d, _s, _e, secs = R.load(path)
    text = next(s for s in secs if s[1] == 1 and s[3] == 0x02000020)
    return text[3], R.section_data(d, text)


def slot_table(src):
    return {n: (t, int(i, 16)) for n, t, i in re.findall(r'^//\s+(khm_\w+)\s+(int|float)\s+0x([0-9A-Fa-f]{8})\s*$',
                                                         open(src).read(), re.M)}


def main():
    patched, base = sys.argv[1:3]
    src = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, '..', 'fighters', 'kirby', 'kirby.c')
    a, words = FX.assemble()
    expect = {FX.CAVE + 4 * i: w for i, w in enumerate(words)}
    # ---- words: the code section differs from BASE only in the cave
    b0, bd = text_words(base)
    p0, pd = text_words(patched)
    n = min(len(bd), len(pd))
    diff = [b0 + o for o in range(0, n, 4) if bd[o:o + 4] != pd[o:o + 4]]
    check('code: only copy_fx_cave.py\'s cave differs from the base', [hex(x) for x in diff
                                                                      if not FX.CAVE <= x < FX.LIMIT], [])
    check('the cave as built', {x: struct.unpack('>I', pd[x - p0:x - p0 + 4])[0] for x in expect}, expect)
    check('the cave ends below its limit', FX.CAVE + 4 * len(words) <= FX.LIMIT, True)
    pm = machine(patched)
    check('the +0x6C hook and trampoline unchanged', (r32(pm, FX.HOOK), [r32(pm, FX.TRAMP + 4 * i) for i in range(4)]),
          ((18 << 26) | ((FX.TRAMP - FX.HOOK) & 0x3FFFFFC), FX.trampoline(a.labels['copy_fx'])))
    check('the late update skips a pending motion of -2 (0x02760E48: lwz r0, 0x1C(r31); cmpwi r0, -2; beq)',
          [r32(pm, LATE_SKIP + 4 * i) for i in range(3)], [0x801F001C, 0x2C00FFFE, 0x4182001C])
    pm.mem_map(MEM, 0x100000)

    # ---- SILENCE through the real chain
    this = MEM + 0x1000
    for k in range(4):
        ag = this + FX.AGENTS + FX.AGENT_SIZE * k
        for off in (0, 4, 8, 0xC, 0x20):
            w32(pm, ag + off, 0x5C00 + k)
        w32(pm, ag + 0x34, 0)
    w32(pm, this + 0x1C, 0x44B)
    w32(pm, this + 0x28, 8)
    pm.mem_write(this + 0x2E, b'\1')
    _r, _f, bad = run(pm, FX.HOOK, {UC_PPC_REG_3: this, UC_PPC_REG_4: FX.SILENCE, UC_PPC_REG_5: 0, UC_PPC_REG_6: 8})
    check('SILENCE: every agent\'s script and state cleared (the game\'s 0x02BEE9B8)',
          [[r32(pm, this + FX.AGENTS + FX.AGENT_SIZE * k + off) for off in (0, 4, 8, 0xC, 0x20)] for k in range(4)],
          [[0] * 5] * 4)
    check('SILENCE: no late bind (+0x1C -2), no override (+0x28 -1, +0x2E 0)',
          (r32(pm, this + 0x1C), r32(pm, this + 0x28), pm.mem_read(this + 0x2E, 1)[0]), (0xFFFFFFFE, 0xFFFFFFFF, 0))
    check('SILENCE: callee-saved registers kept', bad, [])
    check('debug: +0x6C calls counted', r32(pm, a.labels['dbg']) >= 1, True)

    # ---- New_Var slots from MSC, undeclared
    args = MEM + 0x8000

    def obj(at, vt=FIGHTER_WM_VT):
        acc, wm, cats, cat0, ints = at, at + 0x100, at + 0x200, at + 0x300, at + 0x400
        w32(pm, acc + 0x28, wm)
        w32(pm, wm, vt)
        w32(pm, wm + 8, cats)
        w32(pm, cats, cat0)
        w32(pm, cat0 + 0xC, ints)
        w32(pm, cat0 + 8, 0xA8)
        return wm, ints

    def msc(wm, *ws):
        for i, v in enumerate(ws):
            w32(pm, args + 0x10 + 4 * i, v)
        w32(pm, args, args + 0x10)
        w32(pm, args + 4, len(ws))
        r, _f, bad_ = run(pm, MSC_WM, {UC_PPC_REG_3: wm, UC_PPC_REG_4: args})
        assert not bad_, bad_
        return r

    def fget(wm, ident):
        return round(run(pm, FGET, {UC_PPC_REG_3: wm, UC_PPC_REG_4: ident})[1], 4)
    me, me_ints = obj(MEM + 0x10000)
    foe, _ = obj(MEM + 0x11000)
    slots = slot_table(src)
    check('kirby.c\'s khm_* slot table read (37 slots, 0x0F00039B-0x0F0003BF)',
          (len(slots), min(i for _t, i in slots.values()), max(i for _t, i in slots.values())), (37, 0x0F00039B, 0x0F0003BF))
    check('unset slots read 0 (MSC get int / get_float)',
          [msc(me, 6, i) if t == 'int' else fget(me, i) for t, i in slots.values()], [0] * len(slots))
    for k, (t, i) in enumerate(slots.values()):
        if t == 'int':
            msc(me, 7, 1000 + k, i)
        else:
            msc(me, 0, f2b(1.5 + k), i)
    check('every slot written from MSC with no New_Var reads back (WorkModule(0x7) / WorkModule(0))',
          [msc(me, 6, i) if t == 'int' else fget(me, i) for t, i in slots.values()],
          [1000 + k if t == 'int' else 1.5 + k for k, (t, i) in enumerate(slots.values())])
    check('an int slot as a float (the value kept as a float)', fget(me, 0x0F0003BF), float(1000 + list(slots).index(
        'khm_state')))
    check('another object\'s slots apart', [msc(foe, 6, i) for t, i in slots.values() if t == 'int'][:5], [0] * 5)
    msc(me, 7, -3, 0x0F0003BF)
    check('negative ints', msc(me, 6, 0x0F0003BF), 0xFFFFFFFD)
    msc(me, 7, 0x4D506450, 0x1000008A)
    check('the panel gauge int 0x1000008A: a plain int (the int array)', (msc(me, 6, 0x1000008A), r32(pm, me_ints + 0x228)),
          (0x4D506450, 0x4D506450))
    print('%d failures' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
