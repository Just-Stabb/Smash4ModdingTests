#!/usr/bin/env python3
"""Test tools/diag_kirby_hero_cave.py (Kirby's Hero copy fix v4 diagnostic): each hook run in unicorn on the diagnostic
executable and on the one it was built on, from the hook to the word after it: every register (and the fake structs)
as the original leaves them, OSReport (stubbed at its loader-relocated import address, clobbering what a C function
may) called with the line's format and values only when its filter passes, the per-tag caps.

  python3 tools/diag_kirby_hero_test.py DIAG.rpx BASE.rpx      (exe_v46h_diag, exe_v46h; fix v5: the lnk / vis lines,
  stn / swd as rewritten, the hooks out of reach through TRAMP)
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
    e.pre += 32
    if -0x1F00000 < at - pre < 0x1F00000:
        e.mu.mem_write(pre, struct.pack('>5I', 0x3980FFFF, 0x318C0001, 0x3D805A5A, 0x618C000C,
                                        (18 << 26) | ((at - (pre + 16)) & 0x3FFFFFC)))
    else:                               # fix v5: a hook out of a branch's reach: through ctr (the same in both runs)
        e.mu.mem_write(pre, struct.pack('>8I', 0x3980FFFF, 0x318C0001, 0x3D805A5A, 0x618C000C,
                                        0x3C000000 | (at >> 16), 0x60000000 | (at & 0xFFFF), 0x7C0903A6, 0x3C005A5A)
                       + struct.pack('>I', 0x4E800420))
        e.pre += 4
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
    # fake modules: Kirby's accessor KA (+0x20 status, +0x28 work, +0xA8 visibility), the article's AA (+0x68 link,
    # +0xA8 visibility with vt +0xA4)
    KA, AA = F + 0x1000, F + 0x1200
    kst, kwk, kvi, avi, aln = F + 0x1400, F + 0x1440, F + 0x1480, F + 0x14C0, F + 0x1500
    vst, vwk, vav = F + 0x1600, F + 0x1700, F + 0x1800
    fst, fwk, fav = F + 0x1900, F + 0x1910, F + 0x1920
    box = {'st': 0x175, 'v': 1, 'drawn': 1}
    for e in (E0, E1):
        e.stub(fst, lambda e: box['st'])
        e.stub(fwk, lambda e: box['v'] if e.r(4) == D.SWORD_INT else 0x55)
        e.stub(fav, lambda e: box['drawn'])
    mods = {KA + 0x20: kst, KA + 0x28: kwk, KA + 0xA8: kvi, AA + 0x68: aln, AA + 0xA8: avi,
            kst: vst, kwk: vwk, avi: vav, vst + 0x8C: fst, vwk + 0x84: fwk, vav + 0xA4: fav,
            kvi + 8: 0x00010000, avi + 8: 0x01010000, aln + 0x84: 0x80}
    # lnk: the link call's entry, LR in the held article's init, r31 the kind, r5 the joint
    for lr, want in ((0x02B022FC + 4, True), (0x02B02254 + 4, True), (0x02B10000, False), (0x02B02000, False)):
        diff, calls = case(at['lnk'], {31: 0x2C, 5: 0x18, 'lr': lr}, {})
        exp = [(fmts['lnk'], 0x2C, 0x18, lr)] if want else []
        check('lnk from 0x%08X: registers kept (stwu replayed), %s' % (lr, 'a line (kind, joint, caller)' if want else
                                                                     'no line (not the held article\'s init)'),
              (diff, [(c[0],) + nv(c, 3) for c in calls]), ({}, exp))
    # stn: at held_stone (r31 the kind), Kirby's status read, every STN_EVERY-th call in the stone
    seen = []
    box['st'] = 0x175
    for k in range(D.STN_EVERY + 2):
        diff, calls = case(at['stn'], {31: 0x2C, 27: KA, 30: AA}, mods)
        if diff:
            check('stn call %d: registers kept' % k, diff, {})
            break
        seen += [(k, (c[0],) + nv(c, 4)) for c in calls]
    check('stn: in the stone, a line on the 1st and the %dth+1 calls (status, kind, accessor, article)' % D.STN_EVERY,
          seen, [(0, (fmts['stn'], 0x175, 0x2C, KA, AA)), (D.STN_EVERY, (fmts['stn'], 0x175, 0x2C, KA, AA))])
    box['st'] = 0x16
    diff, calls = case(at['stn'], {31: 0x2C, 27: KA, 30: AA}, mods)
    check('stn: not in the stone: no line, registers kept (cr0 as cmplwi r31, 0x2C)', (diff, calls), ({}, []))
    # swd: r3 the int: a line while 1 and the call after
    got = []
    for v in (0, 1, 1, 0, 0, 2):
        diff, calls = case(at['swd'], {3: v, 27: KA, 30: AA}, mods)
        got.append((v, diff, [(c[0],) + nv(c, 4) for c in calls]))
    line = lambda v: [(fmts['swd'], v, 1, 0, 0x80)]       # noqa: E731
    check('swd: registers kept (cr0 as cmpwi r3, 1); a line (int, own, Kirby, attribute mask) while the int is 1 and '
          'the call after', got, [(0, {}, []), (1, {}, line(1)), (1, {}, line(1)), (0, {}, line(0)), (0, {}, []),
                                  (2, {}, [])])
    # vis: the update's end, the Hero copy's article (r31 0x2C): while the int is 1 or its own flag is set, and after
    got = []
    for kind, v, own, drawn in ((0x2C, 0, 0, 0), (0x2C, 1, 1, 1), (0x12, 1, 1, 1), (0x2C, 0, 0, 0), (0x2C, 0, 0, 0),
                                (0x2C, 0, 1, 0)):
        box['v'], box['drawn'] = v, drawn
        m = dict(mods)
        m[avi + 8] = (own << 24) | 0x010000
        diff, calls = case(at['vis'], {31: kind, 27: KA, 30: AA}, m)
        got.append((hex(kind), v, own, diff, [(c[0],) + nv(c, 5) for c in calls]))
    check('vis: registers kept (lmw replayed); a line (int, own, Kirby, attribute mask, drawn) for the Hero copy\'s '
          'article while the int is 1 or its own flag set, and the frame after; none for another kind',
          got, [('0x2c', 0, 0, {}, []), ('0x2c', 1, 1, {}, [(fmts['vis'], 1, 1, 0, 0x80, 1)]), ('0x12', 1, 1, {}, []),
                ('0x2c', 0, 0, {}, [(fmts['vis'], 0, 0, 0, 0x80, 0)]), ('0x2c', 0, 0, {}, []),
                ('0x2c', 0, 1, {}, [(fmts['vis'], 0, 1, 0, 0x80, 0)])])
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
