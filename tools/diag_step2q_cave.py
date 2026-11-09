#!/usr/bin/env python3
"""TEMPORARY diagnostic executable for Smash Run step 2q: tools/diag_step2p_cave.py's lines at their exe_v34 addresses
(hb, sp, st, vis, whole, rb, mot, near, hit, k2, hs, dm, kd, bk, sv, sr), `pd` with the fighter's kinetic kind, and
`bl` for the enemy sound banks:

  pd    each pending bounce entry each cave-enemy update (before u_pend's `cmpwi r12, 0xB3`): slot, the fighter's
        status, the entry's count word, the multiplier, posture y, and the fighter's KineticModule kind (acc+0x34
        +0x11C: 1 = Jump's kinetic, 0x32 = Jump re-entered keeping the speed, 0x33 = StepJump's).
  bl    each kind's sound bank made at a battle's start (the pool loader 0x02DAE564, after 0x033EDD24 and the holder
        store, at 0x02DAE83C `addi r3, r1, 0x2C`): the kind, the type-4 file's handle word (the resource object; 0
        = sound/se/snd_se_enemy_<Kind>.nus3bank was not found), its +0x10 flags (0xEE when the handle is not an
        address in 0x10000000-0x7FFFFFFF), and the bank made ([r1+0x2C] / [r1+0x30]: 0 = none: the file had no
        data, so no `bk` line).

  python3 tools/rpx_patch.py exe_v34.rpx OUT.rpx $(python3 tools/diag_step2q_cave.py --rpx exe_v34.rpx)

Space 0x04BCC000-0x04BCE000 (zero in exe_v34). Sites from the assembled cave (smashrun_walker_cave.py labels) and
the game's words, each checked against the executable's word.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_step2n_cave as N  # noqa: E402
import diag_step2o_cave as O  # noqa: E402
import diag_step2p_cave as P  # noqa: E402

SLOT = N.SLOT
BANK_MADE = 0x02DAE83C          # addi r3, r1, 0x2C: after 0x033EDD24 / 0x033EBFBC in the pool loader 0x02DAE564
KD_FRAMES = P.KD_FRAMES
build = P.build


def hooks_for(img):
    import smashrun_walker_cave as W
    out = [h for h in P.hooks_for(img) if h[0] != 'pd']
    A, _B, _d = W.assemble(W.read_vt(img))
    fn = dict(A.labels)
    pd = O.find(img.u32, fn['u_pend'], 0x2C0C0000 | W.STEP_JUMP)
    out.append(('pd', pd, 0x2C0C0000 | W.STEP_JUMP, 1500, ('sl', 'fst', 'cnt', 'mul', 'fy', 'kin'), """
        mr r4, r28
        lwz r5, %(R12)d(r1)
        lwz r6, 8(r27)
        lwz r7, 4(r27)
        lwz r10, 0(r27)
        lwz r8, 0x18(r10)
        lwz r8, 0x14(r8)
        lwz r9, %(KMA)d(r10)
        lwz r9, 0x11C(r9)
    """ % dict(R12=SLOT(12), KMA=W.KM_ACC)))
    out.append(('bl', BANK_MADE, 0x3861002C, 120, ('k', 'h', 'fl', 'b', 'b4'), """
        lwz r4, 0xC(r30)
        addi r12, r1, %(FR)d
        lwz r5, 8(r12)
        li r6, 0xEE
        lis r0, 0x1000
        cmplw r5, r0
        blt bl_n
        lis r0, 0x8000
        cmplw r5, r0
        bge bl_n
        lhz r6, 0x10(r5)
    bl_n:
        lwz r7, 0x2C(r12)
        lwz r8, 0x30(r12)
    """ % dict(FR=N.FRAME)))
    return out


def args(rpx):
    import smashrun_enemy_cave as E
    img = E.Image(rpx)
    N.HOOKS = hooks_for(img)
    used = [x for x in range(N.CAVE, N.LIMIT, 4) if img.u32(x)]
    assert not used, 'the diagnostic cave space is in use in %s (0x%08X)' % (rpx, used[0])
    vw = [img.u32(N.OSREPORT_VENEER + 4 * i) for i in range(len(N.VENEER_WORDS))]
    assert all(w == x for w, x in zip(vw, N.VENEER_WORDS) if x is not None), 'not the OSReport veneer'
    words, _labels, hooks = build(img.u32)
    out = ['0x%08X=0x%08X' % (N.CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % (at, w) for at, w in sorted(hooks.items())]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', required=True, help='the executable it goes on (exe_v34): hook words checked')
    a = ap.parse_args()
    print(' '.join(args(a.rpx)))


if __name__ == '__main__':
    main()
