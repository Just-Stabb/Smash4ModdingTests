#!/usr/bin/env python3
"""TEMPORARY diagnostic executable for Smash Run step 2p: tools/diag_step2o_cave.py's lines (hb, sp, st, vis, whole,
rb, mot, near, hit, k2, pd) at their exe_v33 addresses, `hs` with the fighter's tread target, plus the lines for
what step 2p could not settle offline (the Paratroopa after a hit, the enemy sounds):

  hs    a stomp taken (u_body before the kind's slot 20): kind, state, the fighter's status kind, posture y, and its
        tread target int 0x10000008 BEFORE u_bounce writes the invalid id (0x50000000): the object StepJump's
        func_1149 would have linked to (step 2o's stale-target finding).
  dm    a Paratroopa / Koopa (kind 3) notified of damage (the fliers' slot 10, f_v10): variation, state, the
        framework's common state (+0xE4), HP (float bits). Starts `kd` for 240 kind-3 updates.
  kd    a kind-3 update while `kd` runs (w_upd after u_pend): this (low half), state, common state +0xE4, the motion
        (MotionModule +0x38), its frame (+0x3C, float bits), posture x / y (float bits).
  bk    a nus3bank parsed (0x03685DD4, after the game's bank parser 0x036872D8): its result (0 = accepted), the BINF id,
        and name bytes 11-22 (e.g. "my_Patapata\\0").
  sv    a sound id resolved for a SoundModule play (0x02C71BC4, in 0x02C71B24 after 0x02C71898): the id, its bank id
        (0x0311EDBC), its tone (0x0311EF88), the bank handle the module found (0 = no loaded bank of that id: silent),
        the module. Only ids of rows >= 0x280 (Smash Run's rows; fighters' and the common rows are lower).
  sr    snd_rows done (cave_s at a battle's start): 1 Smash Run stage / 0 other, the table, its row count, the bank id
        in row 0x28D (the Goomba's: 5002 = 0x138A once registered; 0xEE: the table has fewer rows).

  python3 tools/rpx_patch.py exe_v33.rpx OUT.rpx $(python3 tools/diag_step2p_cave.py --rpx exe_v33.rpx)

Each hook: the step 2n stub (r0, r2-r12, LR, CTR, XER, CR, f0-f13 saved; the replaced word replayed), its own cap.
Space 0x04BCC000-0x04BCE000 (zero in exe_v33). Sites from the assembled cave (smashrun_walker_cave.py labels) and
the game's words, each checked against the executable's word.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_step2n_cave as N  # noqa: E402
import diag_step2o_cave as O  # noqa: E402

SLOT = N.SLOT
BANK_PARSED = 0x03685DD4        # cmpwi r3, 0 after bl 0x036872D8 (r31 the bank object, +0x7C the parser's state)
SOUND_RESOLVED = 0x02C71BC4     # mr r28, r3 after bl 0x02C71898 (r23 id, r26 bank id, r25 tone, r30 the module)
KD_FRAMES = 240


def hooks_for(img):
    import smashrun_walker_cave as W
    A, _B, _d = W.assemble(W.read_vt(img))
    fn = dict(A.labels)
    u32 = img.u32
    out = [h for h in O.hooks_for(img) if h[0] != 'hs']
    hs = O.find(u32, fn['u_body'], 0x7FE3FB78) + 4
    out.append(('hs', hs, 0x818300E0, 300, ('k', 's', 'fst', 'fy', 'tgt'), """
        lwz r3, 0x28(r24)
        lwz r12, 0(r3)
        lwz r12, 0x84(r12)
        mtctr r12
        lis r4, 0x%(TH)04X
        ori r4, r4, 0x%(TL)04X
        bctrl
        mr r8, r3
        lwz r4, 8(r31)
        lwz r5, 4(r31)
        lwz r6, 0x20(r24)
        lwz r6, %(SK)d(r6)
        lwz r7, 0x18(r24)
        lwz r7, 0x14(r7)
    """ % dict(TH=W.I_TREAD_TARGET >> 16, TL=W.I_TREAD_TARGET & 0xFFFF, SK=W.STATUS_KIND)))
    out.append(('dm', fn['f_v10'], 0x81830168, 300, ('v', 's', 'cs', 'hp'), """
        lwz r9, %(S3)d(r1)
        lwz r0, 8(r9)
        cmpwi r0, 3
        bne skip
        lis r12, kdn@ha
        li r0, %(KD)d
        stw r0, kdn@l(r12)
        lwz r4, 0xC(r9)
        lwz r5, 4(r9)
        lwz r6, 0xE4(r9)
        lwz r7, 0(r9)
        lwz r7, 0x3130(r7)
        lwz r7, 8(r7)
        lwz r7, 0(r7)
        lwz r7, 4(r7)
        lwz r7, 0(r7)
    """ % dict(S3=SLOT(3), KD=KD_FRAMES)))
    out.append(('kd', O.find(u32, fn['w_upd'], 0x83DF0168), 0x83DF0168, 3000,
                ('o', 's', 'cs', 'm', 'fr', 'x', 'y'), """
        lwz r0, 8(r31)
        cmpwi r0, 3
        bne skip
        lis r12, kdn@ha
        lwz r11, kdn@l(r12)
        cmpwi r11, 0
        ble skip
        addi r11, r11, -1
        stw r11, kdn@l(r12)
        clrlwi r4, r31, 16
        lwz r5, 4(r31)
        lwz r6, 0xE4(r31)
        lwz r10, 0(r31)
        lwz r11, 0x30F0(r10)
        li r7, 0
        li r8, 0
        cmpwi r11, 0
        beq kd_nm
        lwz r7, 0x38(r11)
        lwz r8, %(MF)d(r11)
    kd_nm:
        lwz r11, 0x311C(r10)
        lwz r9, 0x10(r11)
        lwz r10, 0x14(r11)
    """ % dict(MF=N.MOT_FRAME)))
    out.append(('bk', BANK_PARSED, 0x2C030000, 300, ('r', 'id', 'n0', 'n1', 'n2'), """
        mr r4, r3
        lwz r9, 0xAC(r31)
        li r5, 0
        li r6, 0
        li r7, 0
        li r8, 0
        cmpwi r9, 0
        beq skip
        lbz r10, 0x10(r9)
        addi r10, r10, 12
        rlwinm r10, r10, 0, 0, 29
        addi r10, r10, 8
        lwbrx r5, r9, r10
        lwz r6, 0x1C(r9)
        lwz r7, 0x20(r9)
        lwz r8, 0x24(r9)
    """))
    out.append(('sv', SOUND_RESOLVED, 0x7C7C1B78, 600, ('id', 'bank', 'tone', 'h', 'mod'), """
        srwi r0, r23, 16
        cmplwi r0, 0x280
        blt skip
        cmplwi r0, 0xFFFF
        beq skip
        mr r7, r3
        mr r4, r23
        mr r5, r26
        mr r6, r25
        mr r8, r30
    """))
    out.append(('sr', O.find(u32, fn['snd_rows'], 0xBB410018, 0x400), 0xBB410018, 50, ('m', 'tab', 'n', 'b28d'), """
        mr r4, r26
        li r5, 0
        li r6, 0
        li r7, 0xEE
        lis r12, 0x%(MH)04X
        lwz r12, %(ML)d(r12)
        cmpwi r12, 0
        beq sr_o
        lwz r12, 0(r12)
        cmpwi r12, 0
        beq sr_o
        lwz r12, 0x29C(r12)
        cmpwi r12, 0
        beq sr_o
        lwz r5, 4(r12)
        cmpwi r5, 0
        beq sr_o
        li r11, 8
        lwbrx r6, r11, r5
        cmplwi r6, 0x28E
        blt sr_o
        li r11, 0x28E0
        lwbrx r7, r11, r5
    sr_o:
    """ % dict(MH=W.ha(W.SND_MGR), ML=W.sx(W.SND_MGR))))
    return out


def build(orig):
    """diag_step2n_cave.build with `k2n` and `kdn` words after `mcnt`, and the extra local labels"""
    real_asm = N.Asm.asm

    def asm(self, text):
        if text.startswith('cnt:\n.word 0\nmcnt:\n.word 0'):
            text = text + '\nk2n:\n.word 0\nkdn:\n.word 0'
        return real_asm(self, text)
    real_build = N.build

    N.Asm.asm = asm
    try:
        return real_build(orig)
    finally:
        N.Asm.asm = real_asm


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
    ap.add_argument('--rpx', required=True, help='the executable it goes on (exe_v33): hook words checked')
    a = ap.parse_args()
    print(' '.join(args(a.rpx)))


if __name__ == '__main__':
    main()
