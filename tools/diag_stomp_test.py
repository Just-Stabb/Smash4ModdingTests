#!/usr/bin/env python3
"""Test tools/diag_stomp_cave.py: each hook run in unicorn on the diagnostic executable and on the one it was built
on, from the hook to the word after it: every register (and the fake structs) as the original leaves them, OSReport
(stubbed at its loader-relocated import address, clobbering what a C function may) called with the line's format
and values only when its filter passes, the upd line every UPD_EVERY-th call, the line cap.

  python3 tools/diag_stomp_test.py DIAG.rpx BASE.rpx      (BASE = exe_v10's cross_f.rpx)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_stomp_cave as D  # noqa: E402
from diag_crumbs_test import M, setup, check, FPRS  # noqa: E402
import diag_crumbs_test as T  # noqa: E402
import unicorn.ppc_const as PC  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402


def run(e, at, stop):
    """from a prelude that sets XER's carry through r12 (r0 is an input here: near's last y), then the hook:
    `li r12, -1; addic r12, r12, 1; lis r12, 0x5A5A; ori r12, r12, 0xC; b at` (r12 as setup() leaves it)"""
    pre = e.pre
    e.pre += 20
    e.mu.mem_write(pre, struct.pack('>5I', 0x3980FFFF, 0x318C0001, 0x3D805A5A, 0x618C000C,
                                    (18 << 26) | ((at - (pre + 16)) & 0x3FFFFFC)))
    h = e.mu.hook_add(UC_HOOK_CODE, lambda mu, a, size, ud: mu.emu_stop(), None, stop, stop)
    try:
        e.mu.emu_start(pre, stop, count=4000)
    finally:
        e.mu.hook_del(h)
    pc = e.mu.reg_read(PC.UC_PPC_REG_PC)
    assert pc == stop, 'stopped at 0x%08X, not 0x%08X' % (pc, stop)


def f2w(x):
    return struct.unpack('>I', struct.pack('>f', x))[0]


def main():
    diag, base = sys.argv[1], sys.argv[2]
    E1, E0 = M(diag, False), M(base, False)
    F = E0.alloc(0x1000, b'\0')
    assert E1.alloc(0x1000, b'\0') == F
    for e in (E0, E1):
        e.pre = D.LIMIT - 0x800                 # preludes in the cave's unused tail (b reach of every hook)
    this, cfg, fpos, epos, tab, ent = F + 0x100, F + 0x300, F + 0x400, F + 0x500, F + 0x600, F + 0x700
    labels = D.build(E0.w)[1]
    lines_at, cnt_at = labels['lines'], labels['cnt']
    hook = {t: at for t, at, _w, _b in D.HOOKS}
    fmts = {t: D.fmt_bytes(t)[:-1].decode() for t, _a, _w, _b in D.HOOKS}

    def case(tag, regs, mem, fregs=None):
        res = []
        for e in (E0, E1):
            e.calls = []
            setup(e, regs, mem)
            for i, v in (fregs or {}).items():
                e.mu.reg_write(FPRS[i], v)
            run(e, hook[tag], hook[tag] + 4)
            res.append(e.state())
        s0, s1 = res
        for st in res:                          # FPSCR's FPRF (the stubs' fcmpu result): read by nothing
            st['fpscr'] &= ~0x1F000
        diff = {r: (hex(s0[r]), hex(s1[r])) for r in s0 if s0[r] != s1[r]}
        return diff, E1.calls

    def fake_report(e):
        """M.osreport takes (fmt, r4 as a string, r5-r8): here every r4-r10"""
        e.calls.append((e.cstr(e.r(3)),) + tuple(e.r(i) for i in range(4, 11)))
        for i in [0] + list(range(3, 13)):
            e.mu.reg_write(T.REGS[i], 0xBAD00000 + i)
        for i in range(14):
            e.mu.reg_write(FPRS[i], 0x7FF8DEAD00000000 + i)
        e.mu.reg_write(PC.UC_PPC_REG_CTR, 0xBADC7)
        e.mu.reg_write(PC.UC_PPC_REG_CR, 0x12345678)
    E1.stub(E1.imports['OSReport'], lambda e: fake_report(e))

    # --- upd: r31 this, r30 CFG; the fighter table [[FIGHTERS]] -> tab (+8 count)
    mgr = F + 0x800
    mem = {this + 4: 2, cfg + 0x78: 8, cfg + 0x20: 7, cfg: 0, tab + 8: 1}
    for e in (E0, E1):
        e.setw(lines_at, 0)
        e.setw(cnt_at, 0)
        e.setw(D.FIGHTERS, mgr)
        e.setw(mgr, tab)
    seen = []
    for k in range(D.UPD_EVERY + 2):
        diff, calls = case('upd', {31: this, 30: cfg}, mem)
        if diff:
            check('upd call %d: every register as the original leaves it' % k, diff, {})
            break
        seen += [(k, c) for c in calls]
    want = [(0, (fmts['upd'], this, 2, cfg, 8, 7, tab, 1)), (D.UPD_EVERY, (fmts['upd'], this, 2, cfg, 8, 7, tab, 1))]
    check('upd: registers kept, a line on the 1st and the %dth+1 calls (this, st, cfg, tread, dead, tab, n)'
          % D.UPD_EVERY, seen, want)
    for e in (E0, E1):
        e.setw(D.FIGHTERS, 0)
        e.setw(cnt_at, 0)
    diff, calls = case('upd', {31: this, 30: cfg}, mem)
    check('upd: no fighter table -> tab 0, n = -1', (diff, calls), ({}, [(fmts['upd'], this, 2, cfg, 8, 7, 0, 0xFFFFFFFF)]))
    for e in (E0, E1):
        e.setw(D.FIGHTERS, mgr)

    # --- near: r25 slot, r28 enemy posture, r31 this, r11 fighter posture, r0 last y (bits)
    def near(fx, fy, ex, ey):
        m = {fpos + 0x10: f2w(fx), fpos + 0x14: f2w(fy), epos + 0x10: f2w(ex), epos + 0x14: f2w(ey), this + 4: 2}
        return case('near', {25: 1, 28: epos, 31: this, 11: fpos, 0: f2w(fy + 3)}, m)
    for args, want in (((10.0, 20.0, 5.0, 0.0), True), ((10.0, 20.0, 30.0, 0.0), False),
                       ((-3.0, -5.0, 0.0, 0.0), True), ((0.0, -7.0, 0.0, 0.0), False),
                       ((0.0, 41.0, 0.0, 0.0), False), ((0.0, 39.0, 2.0, -1.0), True)):
        diff, calls = near(*args)
        fx, fy, ex, ey = args
        exp = [(fmts['near'], 1, f2w(fy), f2w(fy + 3), f2w(fx), f2w(ey), f2w(ex), 2)] if want else []
        check('near fighter (%g, %g), enemy (%g, %g): registers kept, %s' % (fx, fy, ex, ey,
              'a line' if want else 'no line'), (diff, calls), ({}, exp))

    # --- hit: r25 slot, r31 this, r24 accessor, r29 TREAD (replayed: mr r3, r31)
    diff, calls = case('hit', {25: 2, 31: this, 24: 0x1234, 29: 8}, {this + 4: 2})
    check('hit: registers kept (r3 = this, replayed), a line (s, st, acc, tread)', (diff, calls),
          ({}, [(fmts['hit'], 2, 2, 0x1234, 8, calls[0][5] if calls else 0, calls[0][6] if calls else 0,
                 calls[0][7] if calls else 0)]))

    # --- the cap
    for e in (E0, E1):
        e.setw(lines_at, D.MAX_LINES)
    diff, calls = case('hit', {25: 2, 31: this, 24: 0x1234, 29: 8}, {this + 4: 2})
    check('at MAX_LINES lines: no more', (diff, calls), ({}, []))
    # formats
    check('formats', [fmts[t] for t in ('upd', 'near', 'hit')],
          ['S4STOMP upd this=%X st=%X cfg=%X tread=%X dead=%X tab=%X n=%X\n',
           'S4STOMP near s=%X fy=%X pv=%X fx=%X ey=%X ex=%X st=%X\n',
           'S4STOMP hit s=%X st=%X acc=%X tread=%X\n'])
    print('%d failed' % T.fails)
    sys.exit(1 if T.fails else 0)


if __name__ == '__main__':
    main()
