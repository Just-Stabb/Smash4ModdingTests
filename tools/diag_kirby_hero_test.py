#!/usr/bin/env python3
"""Test tools/diag_kirby_hero_cave.py (Kirby's Hero copy fix v4 diagnostic): each hook run in unicorn on the diagnostic
executable and on the one it was built on, from the hook to the word after it: every register (and the fake structs)
as the original leaves them, OSReport (stubbed at its loader-relocated import address, clobbering what a C function
may) called with the line's format and values only when its filter passes, the per-tag caps.

  python3 tools/diag_kirby_hero_test.py DIAG.rpx BASE.rpx      (exe_v46g_diag, exe_v46g)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_kirby_hero_cave as D  # noqa: E402
from diag_crumbs_test import M, setup, check, FPRS  # noqa: E402
import diag_crumbs_test as T  # noqa: E402
import unicorn.ppc_const as PC  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402


def run(e, at, stop):
    """from a prelude that sets XER's carry through r12, then the hook (as diag_stomp_test.py)"""
    pre = e.pre
    e.pre += 20
    e.mu.mem_write(pre, struct.pack('>5I', 0x3980FFFF, 0x318C0001, 0x3D805A5A, 0x618C000C,
                                    (18 << 26) | ((at - (pre + 16)) & 0x3FFFFFC)))
    h = e.mu.hook_add(UC_HOOK_CODE, lambda mu, a, size, ud: mu.emu_stop(), None, stop, stop)
    try:
        e.mu.emu_start(pre, stop, count=6000)
    finally:
        e.mu.hook_del(h)
    pc = e.mu.reg_read(PC.UC_PPC_REG_PC)
    assert pc == stop, 'stopped at 0x%08X, not 0x%08X' % (pc, stop)


def f2w(x):
    return struct.unpack('>I', struct.pack('>f', x))[0]


def main():
    diag, base = sys.argv[1], sys.argv[2]
    E1, E0 = M(diag, False), M(base, False)
    F = E0.alloc(0x2000, b'\0')
    assert E1.alloc(0x2000, b'\0') == F
    for e in (E0, E1):
        e.pre = D.LIMIT - 0x600                 # preludes in the cave's unused tail
    words, labels, hk = D.build(E0.w)
    hooks = D.hooks()
    fmts = {t: D.fmt_bytes(t)[:-1].decode() for t in D.NAMES}
    check('the cave fits and is free in the base', (D.CAVE + 4 * len(words) <= D.LIMIT,
                                                    [hex(a) for a in range(D.CAVE, D.LIMIT, 4) if E0.w(a)][:1]),
          (True, []))
    check('every hook in the diagnostic executable', [hex(a) for a, w in sorted(hk.items()) if E1.w(a) != w], [])

    def case(at, regs, mem):
        res = []
        for e in (E0, E1):
            e.calls = []
            setup(e, regs, mem)
            run(e, at, at + 4)
            res.append(e.state())
        s0, s1 = res
        for st in res:
            st['fpscr'] &= ~0x1F000
        diff = {r: (hex(s0[r]), hex(s1[r])) for r in s0 if s0[r] != s1[r]}
        return diff, E1.calls

    def fake_report(e):
        e.calls.append((e.cstr(e.r(3)),) + tuple(e.r(i) for i in range(4, 11)))
        for i in [0] + list(range(3, 13)):
            e.mu.reg_write(T.REGS[i], 0xBAD00000 + i)
        for i in range(14):
            e.mu.reg_write(FPRS[i], 0x7FF8DEAD00000000 + i)
        e.mu.reg_write(PC.UC_PPC_REG_CTR, 0xBADC7)
        e.mu.reg_write(PC.UC_PPC_REG_CR, 0x12345678)
    E1.stub(E1.imports['OSReport'], lambda e: fake_report(e))
    at = {}
    for tag, a, _w, _b in hooks:
        at.setdefault(tag, a)
    nv = lambda c, n: c[1:1 + n]            # noqa: E731

    # cpy: r27 kind, r23 prev, r26 fighter; the grant word
    for e in (E0, E1):
        e.setw(D.GRANT, 0x45)
    diff, calls = case(at['cpy'], {27: 0x2C, 23: 0xFFFFFFFF, 26: F}, {})
    check('cpy: registers kept, a line (kind 0x2C, prev -1, grant 0x45, the fighter)',
          (diff, [(c[0],) + nv(c, 4) for c in calls]), ({}, [(fmts['cpy'], 0x2C, 0xFFFFFFFF, 0x45, F)]))
    # gen: r27 kind, r3 handle
    diff, calls = case(at['gen'], {27: 0x2C, 3: 0x1234}, {})
    check('gen: registers kept (the cmpwi replayed), a line (kind, handle)', (diff, [(c[0],) + nv(c, 2) for c in calls]),
          ({}, [(fmts['gen'], 0x2C, 0x1234)]))
    # res: r29 type, r28 kind, r30 costume, r31 entry; the caller's r1 + 8 found, + 0x5C the name
    sp = T.STACK + 0xF0000
    for typ, want in ((0x11, True), (0xC, True), (0x164, False)):
        mem = {sp + 8: 0x77, sp + 0x5C: 0x62726176, sp + 0x60: 0x6573776F, sp + 0x64: 0x72642F63}
        diff, calls = case(at['res'], {29: typ, 28: 0x2C, 30: 3, 31: 1}, mem)
        exp = [(fmts['res'], typ, 0x2C, 0x301, 0x77, 0x62726176, 0x6573776F, 0x72642F63)] if want else []
        check('res type 0x%X: registers kept (r0 = the found word, replayed), %s' % (typ, 'a line' if want else 'no line'),
              (diff, [(c[0],) + nv(c, 7) for c in calls]), ({}, exp))
    # stn: r3 status, every STN_EVERY-th call in the stone
    seen = []
    for k in range(D.STN_EVERY + 2):
        diff, calls = case(at['stn'], {3: 0x175, 27: 0x111, 30: 0x222}, {})
        if diff:
            check('stn call %d: registers kept' % k, diff, {})
            break
        seen += [(k, (c[0],) + nv(c, 3)) for c in calls]
    check('stn: in the stone, a line on the 1st and the %dth+1 calls (status, accessor, article)' % D.STN_EVERY, seen,
          [(0, (fmts['stn'], 0x175, 0x111, 0x222)), (D.STN_EVERY, (fmts['stn'], 0x175, 0x111, 0x222))])
    diff, calls = case(at['stn'], {3: 0x16, 27: 0x111, 30: 0x222}, {})
    check('stn: not in the stone: no line', (diff, calls), ({}, []))
    # swd: r3 the int; the article's +0xA8 module, vt +0xA4 -> visible
    mod, vt, fn = F + 0x100, F + 0x200, F + 0x300
    art = F + 0x400
    for e in (E0, E1):
        e.stub(fn, lambda e: 0)
    mem = {art + 0xA8: mod, mod: vt, vt + 0xA4: fn}
    for v, want in ((1, True), (0, False), (2, False)):
        diff, calls = case(at['swd'], {3: v, 27: 0x111, 30: art}, mem)
        exp = [(fmts['swd'], 1, 0, 0x111, art)] if want else []
        check('swd int %d: registers kept (cr0 as cmpwi r3, 1), %s' % (v, 'a line (visible before 0)' if want else 'no line'),
              (diff, [(c[0],) + nv(c, 4) for c in calls]), ({}, exp))
    # spawn: r27 the owner fighter (+0x726C -> +0x18 kind; +0x72E4 posture +0x10 x / +0x18 z), r1 + 0x50 the struct
    info, post = F + 0x500, F + 0x600
    for kind, want in ((8, True), (0x45, True), (0x2C, False)):
        mem = {F + 0x800 + 0x726C: info, info + 0x18: kind, F + 0x800 + 0x72E4: post, post + 0x10: f2w(30.0),
               post + 0x18: f2w(0.0), sp + 0x54: f2w(34.0), sp + 0x58: f2w(10.7), sp + 0x5C: f2w(5.0),
               sp + 0xAC: 0x01000000}
        diff, calls = case(at['spawn'], {27: F + 0x800, 28: 0x999}, mem)
        exp = [(fmts['spawn'], kind, 1, f2w(34.0), f2w(10.7), f2w(5.0), f2w(0.0), f2w(30.0))] if want else []
        check('spawn by kind 0x%X: registers kept (r3 = r28, replayed), %s' % (kind, 'a line' if want else 'no line'),
              (diff, [(c[0],) + nv(c, 7) for c in calls]), ({}, exp))
    # hit: each kind's method; r4 the weapon (+0x28 accessor, +0x18 posture), r5 the bits
    wpn, acc, pst = F + 0x900, F + 0xA00, F + 0xB00
    mem = {wpn + 0x28: acc, acc + 0x18: pst, pst + 0x10: f2w(1.0), pst + 0x14: f2w(2.0), pst + 0x18: f2w(5.0)}
    got = []
    for tag, a, _w, body in hooks:
        if tag != 'hit':
            continue
        kind = int(body.split('li r4, ')[1].split()[0], 16)
        diff, calls = case(a, {4: wpn, 5: 0x2}, mem)
        got.append((hex(kind), diff, [(c[0],) + nv(c, 6) for c in calls]))
    check('hit: every method (0x190, 0x193-0x197): registers kept (cr0 as andi. r0, r5, 0x13), a line (kind, bits, '
          'x / y / z, the weapon)', got,
          [(hex(k), {}, [(fmts['hit'], k, 2, f2w(1.0), f2w(2.0), f2w(5.0), wpn)]) for k in sorted(D.HIT_METHODS)])
    # caps
    for e in (E0, E1):
        e.setw(labels['cap_gen'], D.CAPS['gen'])
    diff, calls = case(at['gen'], {27: 0x2C, 3: 0x1234}, {})
    check('gen at its cap (%d lines): no more' % D.CAPS['gen'], (diff, calls), ({}, []))
    print('%d failed' % T.fails)
    sys.exit(1 if T.fails else 0)


if __name__ == '__main__':
    main()
