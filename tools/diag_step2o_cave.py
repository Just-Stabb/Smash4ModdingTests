#!/usr/bin/env python3
"""TEMPORARY diagnostic executable for Smash Run step 2o: tools/diag_step2n_cave.py's lines (hb, sp, st, vis, whole,
rb, mot, near, hit) at their exe_v32 addresses, plus the lines that settle what step 2o could not prove offline:

  k2    each run of k2_twins (the twins' own param objects; at its end, k2t_o): the run count, Lethinium's object
        kept (k2_objs[0]), slot 0x57 / slot 0x12 (what Lethinium's AI and its weapons read), slot 0x57's loader +8
        byte (1: a clean parse; 0xEE: no object) and its +0x19C (the cannon shot's data; 0 = the crash), bits 0-2:
        Darios's / Stalfos's / Zima's objects kept.
        Two or more k2 lines in one battle = the param load runs more than once per battle.
  hs    a stomp taken (u_body before the kind's slot 20): kind, state, the fighter's status kind and posture y.
  pd    the stomp bounce's pending re-write (u_pend, each entry each cave-enemy update, before the 0xB3 test): the
        fighter slot, its status kind, the entry's count / seen bits, the multiplier written (float bits), the
        fighter's posture y (bits). A status other than 0xB3 right after a Big Goomba stomp (e.g. a damage status
        from its walk push box / run head box, still active in Stepped) is why it gives no height.

  python3 tools/rpx_patch.py exe_v32.rpx OUT.rpx $(python3 tools/diag_step2o_cave.py --rpx exe_v32.rpx)

Each hook: the step 2n stub (r0, r2-r12, LR, CTR, XER, CR, f0-f13 saved; the replaced word replayed), its own cap.
Space 0x04BCC000-0x04BCE000 (zero in exe_v32: region H's code ends at 0x04BC59B0). Sites from the assembled cave
(smashrun_walker_cave.py labels), each checked against the executable's word.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_step2n_cave as N  # noqa: E402

SLOT = N.SLOT
FRAME = N.FRAME


def find(u32, start, word, limit=0x200):
    for a in range(start, start + limit, 4):
        if u32(a) == word:
            return a
    raise KeyError('0x%08X not found after 0x%08X' % (word, start))


def hooks_for(img):
    """step 2n's hooks at this executable's addresses, then k2 / hs / pd"""
    import smashrun_walker_cave as W
    A, _B, d = W.assemble(W.read_vt(img))
    fn = dict(A.labels)
    D = d.addr
    u32 = img.u32
    site = {'hb': 0x04B7D28C, 'sp': 0x04B7D4A8, 'st': fn['w_chg2'], 'vis': find(u32, fn['hv_loop'], 0x387F0004),
            'whole': fn['h_whole'], 'rb': 0x03424F74, 'mot': fn['w_upd'], 'near': fn['u_body'],
            'hit': find(u32, fn['u_body'], 0x7FE3FB78)}
    out = []
    for tag, at, w0, cap, names, body in N.HOOKS:
        out.append((tag, site[tag], w0, cap, names, body))
    # k2: at k2t_o (lmw r26, 0x48(r1)); r28 = [PARAM_MGR] or 0 (the run that found no manager)
    out.append(('k2', fn['k2t_o'], 0xBB410048, 200, ('n', 'pw', 's57', 's12', 'ok', 'g8', 'oth'), """
        lis r12, k2n@ha
        lwz r4, k2n@l(r12)
        addi r4, r4, 1
        stw r4, k2n@l(r12)
        lis r12, 0x%(OH)04X
        addi r12, r12, %(OL)d
        lwz r5, 0(r12)
        li r10, 0
        lwz r0, 4(r12)
        cmpwi r0, 0
        beq k2_b1
        ori r10, r10, 1
    k2_b1:
        lwz r0, 8(r12)
        cmpwi r0, 0
        beq k2_b2
        ori r10, r10, 2
    k2_b2:
        lwz r0, 0xC(r12)
        cmpwi r0, 0
        beq k2_b3
        ori r10, r10, 4
    k2_b3:
        li r6, 0
        li r7, 0
        lis r12, 0x%(MH)04X
        lwz r12, %(ML)d(r12)
        cmpwi r12, 0
        beq k2_nm
        lwz r6, 0x%(S57)X(r12)
        lwz r7, 0x%(S12)X(r12)
    k2_nm:
        li r8, 0xEE
        li r9, 0
        cmpwi r6, 0
        beq k2_no
        lbz r8, 0x%(LB)X(r6)
        lwz r9, 0x19C(r6)
    k2_no:
    """ % dict(OH=W.ha(D['k2_objs']), OL=W.sx(D['k2_objs']), MH=W.ha(W.PARAM_MGR), ML=W.sx(W.PARAM_MGR),
               S57=W.SLOTS + 4 * 0x57, S12=W.SLOTS + 4 * 0x12, LB=W.TWIN_LOADER[0x57] + 8)))
    # hs: at the stomp (the word after 'hit': lwz r12, 0xE0(r3)); r24 the fighter's accessor, r31 this
    hs = site['hit'] + 4
    out.append(('hs', hs, 0x818300E0, 300, ('k', 's', 'fst', 'fy'), """
        lwz r4, 8(r31)
        lwz r5, 4(r31)
        lwz r6, 0x20(r24)
        lwz r6, %(SK)d(r6)
        lwz r7, 0x18(r24)
        lwz r7, 0x14(r7)
    """ % dict(SK=W.STATUS_KIND)))
    # pd: u_pend before `cmpwi r12, 0xB3` (r28 the slot, r27 the entry {acc, float, count}, r12 the status)
    pd = find(u32, fn['upd_loop'], 0x2C0C0000 | W.STEP_JUMP)
    out.append(('pd', pd, 0x2C0C0000 | W.STEP_JUMP, 1500, ('sl', 'fst', 'cnt', 'mul', 'fy'), """
        mr r4, r28
        lwz r5, %(R12)d(r1)
        lwz r6, 8(r27)
        lwz r7, 4(r27)
        lwz r8, 0(r27)
        lwz r8, 0x18(r8)
        lwz r8, 0x14(r8)
    """ % dict(R12=SLOT(12))))
    return out


def args(rpx):
    import smashrun_enemy_cave as E
    img = E.Image(rpx)
    N.HOOKS = hooks_for(img)
    used = [x for x in range(N.CAVE, N.LIMIT, 4) if img.u32(x)]
    assert not used, 'the diagnostic cave space is in use in %s (0x%08X)' % (rpx, used[0])
    vw = [img.u32(N.OSREPORT_VENEER + 4 * i) for i in range(len(N.VENEER_WORDS))]
    assert all(w == x for w, x in zip(vw, N.VENEER_WORDS) if x is not None), 'not the OSReport veneer'
    words, _labels, hooks = build_with_k2n(img.u32)
    out = ['0x%08X=0x%08X' % (N.CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % (at, w) for at, w in sorted(hooks.items())]
    return out


def build_with_k2n(orig):
    """diag_step2n_cave.build with a `k2n` word after `mcnt`"""
    real_asm = N.Asm.asm

    def asm(self, text):
        if text.startswith('cnt:\n.word 0\nmcnt:\n.word 0'):
            text = text + '\nk2n:\n.word 0'
        return real_asm(self, text)
    N.Asm.asm = asm
    try:
        return N.build(orig)
    finally:
        N.Asm.asm = real_asm


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', required=True, help='the executable it goes on (exe_v32): hook words checked')
    a = ap.parse_args()
    print(' '.join(args(a.rpx)))


if __name__ == '__main__':
    main()
