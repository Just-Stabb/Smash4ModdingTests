#!/usr/bin/env python3
"""Runs the game's fighter KineticModule MSC handler in unicorn (Sephiroth test 154): why test 153's shield push
(position variable q 7 -> KineticModule(0x11, 4, x, 0) on the shielder) didn't move it, and that test 154's
(KineticModule(0xe, 4, 0xb, x, 0, 0, 0, 0) then (0xb, 4): the guard damage status's own pushback setup, func_460)
reaches the energy.

  python3 tools/kinetic_push_test.py [RPX]        (default build/cross_f.rpx: the code is the base game's)

The handler: fighter_kinetic_module_impl's MSC command (0x02E79100, its assert file string 0x1012C548) takes ops 0xF /
0x11 / 0x15 / 0x19 itself and passes the rest to kinetic_module_impl's (0x02C510C4, string 0x10108C04: a jump table of
ops 0 - 0x18). Its op 0x11 (set an energy's speed) knows energies 0 - 3 only (vt +0x54 get energy, then its +0 / +4):
energy 4 goes to its assert (0x032C4E20, line 0xA9) and nothing is set. The base op 0xE (8 words) gets energy arg 1 and
calls that energy's vt +0x1C (reset: type arg 2, speed (arg 3, arg 4)), any energy. The kinetic module and its energies
are fakes here (vtables of stubs that log their calls); the paired-single saves / loads (psq_st / psq_l, which unicorn
can't run) are made nops.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from unicorn.ppc_const import UC_PPC_REG_MSR  # noqa: E402
from kind_expand_test import Emu  # noqa: E402

FIGHTER_HANDLER = 0x02E79100
BASE_HANDLER = 0x02C510C4
ASSERT = 0x032C4E20
FAILS = []


def check(what, got, want):
    ok = got == want
    print('%s %s: %r%s' % ('ok  ' if ok else 'FAIL', what, got, '' if ok else ' (want %r)' % (want,)))
    if not ok:
        FAILS.append(what)


def f2w(v):
    return struct.unpack('>I', struct.pack('>f', v))[0]


def w2f(w):
    return struct.unpack('>f', struct.pack('>I', w))[0]


def main():
    rpx = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'build', 'cross_f.rpx')
    e = Emu(rpx)
    e.mu.reg_write(UC_PPC_REG_MSR, e.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    for lo, n in ((FIGHTER_HANDLER, 0x300), (BASE_HANDLER, 0x1000)):       # paired-single saves / loads: nops
        for i in range(n):
            a = lo + 4 * i
            if e.w(a) >> 26 in (4, 56, 57, 60, 61):
                e.setw(a, 0x60000000)
    log = []
    e.stub(ASSERT, lambda em: log.append(('assert', em.r(4))))
    # energies 0 - 5: each a fake object (speed at +0 / +4) with a vtable whose +0x1C (reset) logs
    energies = {}
    evt = e.alloc(0x100, b'\0')
    reset = e.alloc(8, b'\0')
    e.mu.mem_write(reset, struct.pack('>II', 0x38600000, 0x4E800020))
    e.stub(reset, lambda em: log.append(('reset', em.r(3), em.r(4), w2f(em.w(em.r(5))), w2f(em.w(em.r(5) + 4)))))
    for o in range(0, 0x100, 4):
        e.setw(evt + o, reset if o == 0x1C else e.alloc(8, b'\0'))
        if o != 0x1C:
            e.mu.mem_write(e.w(evt + o), struct.pack('>II', 0x38600000, 0x4E800020))
    for k in range(6):
        en = e.alloc(0x40, b'\0')
        e.setw(en, 0)
        e.setw(en + 0x1C, evt)
        energies[k] = en
    # the kinetic module: vt +0x54(id) = energy id
    kvt = e.alloc(0x200, b'\0')
    get = e.alloc(8, b'\0')
    e.mu.mem_write(get, struct.pack('>II', 0x38600000, 0x4E800020))

    def get_energy(em):
        log.append(('get', em.r(4)))
        return energies.get(em.r(4), 0)
    e.stub(get, get_energy)
    for o in range(0, 0x200, 4):
        e.setw(kvt + o, get)
    km = e.alloc(0x200, b'\0')
    e.setw(km, kvt)

    def msc(*words):
        args = e.alloc(0x40, b'\0')
        for i, w in enumerate(words):
            e.setw(args + 4 * i, w)
        frame = e.alloc(0x10, b'\0')
        e.setw(frame, args)
        e.setw(frame + 4, len(words))
        del log[:]
        e.call(FIGHTER_HANDLER, km, frame)
        return list(log)

    # energies' reset (+0x1C) reads its type from r4 and the speed from *r5 when called through the energy's vtable:
    # the energy objects' vtable pointer is at +0 for the fighter handler's get / set path, at +0x1C for the base op
    # 0xE (lwz r12, 0x1C(r3); lwz r0, 0x1C(r12))
    got = msc(0x11, 3, f2w(-2.5), 0)
    check('op 0x11 energy 3 (stop): gets energy 3', got[:1], [('get', 3)])
    check('  its speed x set', w2f(e.w(energies[3])), -2.5)
    got = msc(0x11, 4, f2w(-2.5), 0)
    check('op 0x11 energy 4 (test 153\'s push): no energy got, the assert (line 0xA9)',
          [g for g in got if g[0] in ('get', 'assert')], [('assert', 0xA9)])
    check('  energy 4 untouched', w2f(e.w(energies[4])), 0.0)
    got = msc(0xE, 4, 0xB, f2w(-2.5), 0, 0, 0, 0)
    check('op 0xE energy 4 (test 154\'s): gets energy 4 and resets it (type 0xB, speed (-2.5, 0))',
          [(g[0],) + tuple(g[2:]) if g[0] == 'reset' else g for g in got if g[0] in ('get', 'reset', 'assert')],
          [('get', 4), ('reset', 0xB, -2.5, 0.0)])
    got = msc(0xE, 4, 0xB, f2w(-2.5), 0, 0, 0)
    check('op 0xE with 7 words: refused (assert, line 0x2F6)', [g for g in got if g[0] == 'assert'], [('assert', 0x2F6)])
    print('%d failed' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
