#!/usr/bin/env python3
"""Test tools/diag_step2o_cave.py (step 2n's lines at their exe_v32 addresses, plus k2 / hs / pd): each hook run in
unicorn on the diagnostic executable and on the one it was built on (exe_v32), from the hook to the word after it: every register (and the fake structs) as the original leaves them,
OSReport (stubbed, clobbering what a C function may) called with the line's format and values only when its filter
passes (hb every 60th call, mot a Paratroopa's every 30th update, vis only a change, near only near), each tag's cap;
k2 every run (Lethinium's object, slots 0x57 / 0x12, its loader byte and +0x19C), hs at a stomp (the fighter's
status, y), pd each pending bounce entry (slot, status, count, multiplier, y).

  python3 tools/diag_step2o_test.py DIAG.rpx BASE.rpx
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_step2n_cave as D  # noqa: E402
import diag_step2o_cave as D2  # noqa: E402
from diag_crumbs_test import M, setup, check, FPRS  # noqa: E402
import diag_crumbs_test as T  # noqa: E402
import unicorn.ppc_const as PC  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402


def run(e, at, stop):
    """a prelude that sets XER's carry through r12, then the hook (r12 as setup() leaves it)"""
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
    import smashrun_enemy_cave as EC
    import smashrun_walker_cave as W
    D.HOOKS = D2.hooks_for(EC.Image(base))
    E1, E0 = M(diag, False), M(base, False)
    F = E0.alloc(0x4000, b'\0')
    assert E1.alloc(0x4000, b'\0') == F
    for e in (E0, E1):
        e.pre = D.LIMIT - 0x800                 # preludes in the cave's unused tail
    labels = D2.build_with_k2n(E0.w)[1]
    lines_at, cnt_at, mcnt_at = labels['lines'], labels['cnt'], labels['mcnt']
    hook = {t: at for t, at, _w, _c, _n, _b in D.HOOKS}
    idx = {t: i for i, (t, _a, _w, _c, _n, _b) in enumerate(D.HOOKS)}
    fmts = {t: D.fmt_bytes(t, n)[:-1].decode() for t, _a, _w, _c, n, _b in D.HOOKS}

    def case(tag, regs, mem, fregs=None):
        res = []
        for e in (E0, E1):
            e.calls = []
            setup(e, regs, mem)
            for i, v in (fregs or {}).items():
                e.mu.reg_write(FPRS[i], v)
            run(e, hook[tag], hook[tag] + 4)
            res.append(e.state())
        for st in res:
            st['fpscr'] &= ~0x1F000
        s0, s1 = res
        diff = {r: (hex(s0[r]), hex(s1[r])) for r in s0 if s0[r] != s1[r]}
        return diff, [c[:1 + len(D.HOOKS[idx[tag]][4])] for c in E1.calls]

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
        for i in range(len(D.HOOKS)):
            e.setw(lines_at + 4 * i, 0)
        e.setw(cnt_at, 0)
        e.setw(mcnt_at, 0)

    # hb: r3 the manager; a line on the 1st and the 61st call
    seen = []
    for k in range(62):
        diff, calls = case('hb', {3: 0x1234}, {})
        if diff:
            check('hb call %d: registers kept' % k, diff, {})
            break
        seen += [(k, c) for c in calls]
    check('hb: registers kept, a line on calls 1 and 61 (n, mgr)', seen,
          [(0, (fmts['hb'], 1, 0x1234)), (60, (fmts['hb'], 61, 0x1234))])

    # sp: the create param at the caller's r1 + 0x20 (r4 = r1 + 0x20 replayed)
    sp = F + 0x100
    diff, calls = case('sp', {1: sp}, {sp + 0x20: 0x11, sp + 0x24: 2, sp + 0x40: 7, sp + 0x44: 9})
    # setup() puts r1 on the Emu's stack: this case writes r1 itself
    check('sp: registers kept (r4 = r1 + 0x20), a line (kind, variation, +0x20, +0x24)', (diff, calls),
          ({}, [(fmts['sp'], 0x11, 2, 7, 9)]))

    # st: r3 this (kind +8, var +0xC, state +4), r4 the new state, r11 the function
    this = F + 0x200
    diff, calls = case('st', {3: this, 4: 5, 11: 0x026A3A44}, {this + 4: 3, this + 8: 0x23, this + 0xC: 1})
    check('st: registers kept, a line (kind, var, state, new, function, this)', (diff, calls),
          ({}, [(fmts['st'], 0x23, 1, 3, 5, 0x026A3A44, this)]))

    # vis: r31 the ModelModule (+0xC the model), r4 the mesh, r30 the value; h_vis's frame (the caller's r1) +0x1C
    # the behaviour
    mm, mdl, data, arr, frame = F + 0x300, F + 0x400, F + 0x500, F + 0x600, F + 0x700
    beh = F + 0x800
    mem = {mm + 0xC: mdl, mdl + 0x6E4: data, data + 0x44: 3, mdl + 0x7DC: arr, arr + 4: arr + 0x10,
           arr + 0x10: 0xFEFDFC00, frame + 0x1C: beh, beh + 8: 0x11}
    diff, calls = case('vis', {1: frame, 31: mm, 4: 0, 30: 0}, mem)
    check('vis: mesh 0 (bits 2) set to 0: registers kept, a line (mesh, kind, old, new, model, count)',
          (diff, calls), ({}, [(fmts['vis'], 0, 0x11, 2, 0, mdl, 3)]))
    diff, calls = case('vis', {1: frame, 31: mm, 4: 1, 30: 1}, mem)
    check('vis: mesh 1 already 1: no line', (diff, calls), ({}, []))
    diff, calls = case('vis', {1: frame, 31: mm, 4: 5, 30: 1}, mem)
    check('vis: mesh 5 past the count 3: a line with old 0xEE', (diff, calls),
          ({}, [(fmts['vis'], 5, 0x11, 0xEE, 1, mdl, 3)]))

    # whole: r3 the behaviour, r4 the value
    diff, calls = case('whole', {3: beh, 4: 0}, {beh + 8: 0x0F})
    check('whole: registers kept (r3 = [r3] replayed), a line (kind, value, this)', (diff, calls),
          ({}, [(fmts['whole'], 0x0F, 0, beh)]))

    # rb (game code): r31 the model, r30 the visible count
    diff, calls = case('rb', {31: mdl, 30: 2}, {mdl + 0x7EC: 0xC1, mdl + 0x7F0: 0xC2})
    check('rb: registers kept (r3 = +0x7EC replayed), a line (model, count, command list, list)', (diff, calls),
          ({}, [(fmts['rb'], mdl, 2, 0xC1, 0xC2)]))

    # mot: r3 the behaviour (kind 3), [acc+0x30F0] the MotionModule; a line every 30th Paratroopa update
    acc, mot = F + 0x900, F + 0x4000 - 0x100
    pt = F + 0xA00
    mem = {pt: acc, pt + 4: 2, pt + 8: 3, pt + 0xC: 1, acc + 0x30F0: mot, mot + 0x38: 11, mot + 0x3C: f2w(4.0),
           mot + 0x50: f2w(1.0)}
    seen = []
    for k in range(31):
        diff, calls = case('mot', {3: pt}, mem)
        if diff:
            check('mot call %d: registers kept' % k, diff, {})
            break
        seen += [(k, c) for c in calls]
    other = case('mot', {3: beh}, {beh + 8: 0x01})
    check('mot: a Paratroopa: registers kept, lines on its 1st and 31st update (state, motion, frame, rate, var); '
          'a Goomba: none', (seen, other), ([(0, (fmts['mot'], 2, 11, f2w(4.0), f2w(1.0), 1)),
                                            (30, (fmts['mot'], 2, 11, f2w(4.0), f2w(1.0), 1))], ({}, [])))

    # near: r25 slot, r26 the fighter table, r28 the enemy posture, r31 this
    tab, ent, facc, fpos, epos = F + 0xB00, F + 0xC00, F + 0x1000, F + 0x1100, F + 0x1200
    thisn = F + 0x1300

    def near(kind, fx, fy, ex, ey, live=4):
        m = {tab: ent - 1 * D.FIGHTER_ENTRY, ent + 0xC: facc, facc + 0x18: fpos, fpos + 0x10: f2w(fx),
             fpos + 0x14: f2w(fy), epos + 0x10: f2w(ex), epos + 0x14: f2w(ey), thisn + 4: 3, thisn + 8: kind,
             ent + 0x1C: live << 8}
        return case('near', {25: 1, 26: tab, 28: epos, 31: thisn}, m)
    for args, want in (((0x23, 10.0, 20.0, 5.0, 0.0), True), ((0x23, 30.0, 20.0, 5.0, 0.0), False),
                       ((0x03, -3.0, -5.0, 0.0, 0.0), True), ((0x03, 0.0, -11.0, 0.0, 0.0), False),
                       ((0x03, 0.0, 41.0, 0.0, 0.0), False), ((0x01, 0.0, 5.0, 0.0, 0.0), False)):
        diff, calls = near(*args)
        k, fx, fy, ex, ey = args
        exp = [(fmts['near'], k, 3, f2w(fx), f2w(fy), f2w(ex), f2w(ey))] if want else []
        check('near kind 0x%X fighter (%g, %g), enemy (%g, %g): registers kept, %s' % (
            k, fx, fy, ex, ey, 'a line' if want else 'no line'), (diff, calls), ({}, exp))

    # hit: r31 this, r25 the slot
    diff, calls = case('hit', {31: thisn, 25: 2}, {thisn + 4: 3, thisn + 8: 0x23})
    check('hit: registers kept (r3 = r31 replayed), a line (kind, state, slot)', (diff, calls),
          ({}, [(fmts['hit'], 0x23, 3, 2)]))

    # k2: at k2t_o; k2_objs (Lethinium's, then Darios / Stalfos / Zima), [PARAM_MGR] slots 0x57 / 0x12
    _A, _B, dd = W.assemble(W.read_vt(EC.Image(base)))
    objs = dd.addr['k2_objs']
    pm, pw = F + 0x1400, F + 0x1800
    mem = {objs: pw, objs + 4: 0, objs + 8: 0x77, objs + 0xC: 0x78, W.PARAM_MGR: pm, pm + W.SLOTS + 4 * 0x57: pw,
           pm + W.SLOTS + 4 * 0x12: pw, pw + W.TWIN_LOADER[0x57] + 8: 0x01000000, pw + 0x19C: 0xABC0}
    diff, calls = case('k2', {}, mem)
    diff2, calls2 = case('k2', {}, {**mem, W.PARAM_MGR: 0})
    check('k2: registers kept (lmw replayed), a line per run (run 1, 2: Lethinium\'s object, slots 0x57 / 0x12, its '
          'loader byte, +0x19C, the others kept as bits); no manager: slots 0, loader 0xEE',
          (diff, calls, diff2, calls2), ({}, [(fmts['k2'], 1, pw, pw, pw, 1, 0xABC0, 6)], {},
                                          [(fmts['k2'], 2, pw, 0, 0, 0xEE, 0, 6)]))
    # hs: at the stomp (lwz r12, 0xE0(r3) replayed); r24 the fighter's accessor, r31 this
    fa, fst, fpo = F + 0x1900, F + 0x1A00, F + 0x1B00
    diff, calls = case('hs', {3: thisn, 24: fa, 31: thisn}, {thisn + 4: 3, thisn + 8: 0x23, thisn + 0xE0: 0x5555,
                                                             fa + 0x20: fst, fst + W.STATUS_KIND: 0x1D, fa + 0x18: fpo,
                                                             fpo + 0x14: f2w(9.5)})
    check('hs: registers kept, a line (kind, state, the fighter\'s status, y)', (diff, calls),
          ({}, [(fmts['hs'], 0x23, 3, 0x1D, f2w(9.5))]))
    # pd: before `cmpwi r12, 0xB3`; r28 the slot, r27 the entry {acc, float, count}, r12 the status
    ent2 = F + 0x1C00
    # (run()'s prelude leaves r12 = 0x5A5A000C: the line's status is the r12 the hook saw)
    diff, calls = case('pd', {28: 1, 27: ent2}, {ent2: fa, ent2 + 4: f2w(0.9), ent2 + 8: 0x10027,
                                                          fa + 0x18: fpo, fpo + 0x14: f2w(9.5)})
    check('pd: registers kept (the compare replayed: cr0 as the original), a line (slot, status, count, '
          'multiplier, y)', (diff, calls), ({}, [(fmts['pd'], 1, 0x5A5A000C, 0x10027, f2w(0.9), f2w(9.5))]))

    # caps
    for e in (E0, E1):
        e.setw(lines_at + 4 * idx['hit'], D.HOOKS[idx['hit']][3])
    diff, calls = case('hit', {31: thisn, 25: 2}, {thisn + 4: 3, thisn + 8: 0x23})
    check('hit at its cap: no more lines', (diff, calls), ({}, []))
    diff, calls = case('whole', {3: beh, 4: 1}, {beh + 8: 0x0F})
    check('another tag under its own cap still logs', len(calls), 1)

    print('%d failed' % T.fails)
    sys.exit(1 if T.fails else 0)


if __name__ == '__main__':
    main()
