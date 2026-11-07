#!/usr/bin/env python3
"""Test tools/diag_effect_cave.py: each hook run in unicorn on the diagnostic executable and on the one it was built
on, from the hook to the word after it: every register as the original leaves it (the replayed word included: the
`cmplwi` sets cr0 as the original does), OSReport called with the line's format and values only for enemy banks
(bank >> 8 == 7), the .efc read only through a word-aligned pointer in 0x10000000-0x7FFFFFFF, the line cap.

  python3 tools/diag_effect_test.py DIAG.rpx BASE.rpx
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_effect_cave as D  # noqa: E402
from diag_crumbs_test import M, setup, check, FPRS  # noqa: E402
import diag_crumbs_test as T  # noqa: E402
from diag_stomp_test import run  # noqa: E402
import unicorn.ppc_const as PC  # noqa: E402


def main():
    diag, base = sys.argv[1], sys.argv[2]
    E1, E0 = M(diag, False), M(base, False)
    F = E0.alloc(0x2000, b'\0')
    assert E1.alloc(0x2000, b'\0') == F
    for e in (E0, E1):
        e.pre = D.LIMIT - 0x800
    labels = D.build(E0.w)[1]
    lines_at = labels['lines']
    hook = {t: at for t, at, _w, _b in D.HOOKS}
    fmts = {t: D.fmt_bytes(t)[:-1].decode() for t, _a, _w, _b in D.HOOKS}

    def case(tag, regs, mem):
        res = []
        for e in (E0, E1):
            e.calls = []
            setup(e, regs, mem)
            run(e, hook[tag], hook[tag] + 4)
            res.append(e.state())
        for st in res:
            st['fpscr'] &= ~0x1F000
        s0, s1 = res
        return {r: (hex(s0[r]), hex(s1[r])) for r in s0 if s0[r] != s1[r]}, E1.calls

    def fake_report(e):
        e.calls.append((e.cstr(e.r(3)),) + tuple(e.r(i) for i in range(4, 11)))
        for i in [0] + list(range(3, 13)):
            e.mu.reg_write(T.REGS[i], 0xBAD00000 + i)
        for i in range(14):
            e.mu.reg_write(FPRS[i], 0x7FF8DEAD00000000 + i)
        e.mu.reg_write(PC.UC_PPC_REG_CTR, 0xBADC7)
        e.mu.reg_write(PC.UC_PPC_REG_CR, 0x12345678)
    E1.stub(E1.imports['OSReport'], lambda e: fake_report(e))
    for e in (E0, E1):
        e.setw(lines_at, 0)

    # reg: r3 slot, r4 bank, r23 the resource
    diff, calls = case('reg', {3: 0x1B, 4: 0x757, 23: 0x1234}, {})
    check('reg bank 0x757: registers kept, a line (bank, slot, res)', (diff, [c[:4] for c in calls]),
          ({}, [(fmts['reg'], 0x757, 0x1B, 0x1234)]))
    diff, calls = case('reg', {3: 0x5, 4: 0x341, 23: 0x1234}, {})
    check('reg bank 0x341 (a fighter\'s): no line', (diff, calls), ({}, []))

    # req: r29 id, r3 slot, r28 the manager (slot entries at +0xB8, 0x80 each)
    mgr = F + 0x100
    efc = F + 0x1800
    ent = mgr + 0xB8 + 0x1B * 0x80
    for slot, efcp, want_n in ((0x1B, efc, 7), (0x1B, 0, 0xFFFFFFFF), (0x1B, 0x9FFF0000, 0xFFFFFFFF), (0x1B, 0x60001802, 0xFFFFFFFF), (0x29, 0, None)):
        mem = {ent: 0x757, ent + 4: 0x22, ent + 8: efcp, efc + 8: 0x00070000}
        diff, calls = case('req', {3: slot, 29: 0x7570003, 28: mgr}, mem)
        if want_n is None:
            want = [(fmts['req'], 0x7570003, slot, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF)]
        else:
            want = [(fmts['req'], 0x7570003, slot, 0x757, 0x22, efcp, want_n)]
        check('req 0x7570003 slot 0x%X efc 0x%X: registers kept (cr0 from the replayed cmplwi), a line' % (slot, efcp),
              (diff, [c[:7] for c in calls]), ({}, want))
    diff, calls = case('req', {3: 0x2, 29: 0x1000026, 28: mgr}, {})
    check('req 0x1000026 (a common effect): no line', (diff, calls), ({}, []))

    # made: r29 id, r30 handle (replayed: mr r3, r30)
    diff, calls = case('made', {29: 0x7570004, 30: 0}, {})
    check('made 0x7570004 handle 0: registers kept (r3 = r30), a line', (diff, [c[:3] for c in calls]),
          ({}, [(fmts['made'], 0x7570004, 0)]))
    diff, calls = case('made', {29: 0x3030004, 30: 9}, {})
    check('made 0x3030004 (a fighter\'s): no line', (diff, calls), ({}, []))

    for e in (E0, E1):
        e.setw(lines_at, D.B.MAX_LINES)
    diff, calls = case('made', {29: 0x7570004, 30: 0}, {})
    check('at MAX_LINES lines: no more', (diff, calls), ({}, []))
    check('formats', [fmts[t] for t in ('reg', 'req', 'made')],
          ['S4FX reg bank=%X slot=%X res=%X\n', 'S4FX req id=%X slot=%X bank=%X eft=%X efc=%X n=%X\n',
           'S4FX made id=%X h=%X\n'])
    print('%d failed' % T.fails)
    sys.exit(1 if T.fails else 0)


if __name__ == '__main__':
    main()
