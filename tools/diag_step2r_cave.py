#!/usr/bin/env python3
"""TEMPORARY diagnostic executable for Smash Run step 2r: tools/diag_step2q_cave.py's lines at their exe_v35 addresses
(hb, sp, st, vis, whole, rb, mot, k2, dm, kd, bk, sv, sr, bl; its near / hit / hs / pd replaced) plus the lines that
settle the stomp area and the Big Goomba's bounce (docs/smash-run-port.md "Step 2r"):

  nk    the stomp test (u_body, the word that stores this frame's relative y), each frame a live fighter is near a
        stompable enemy (|fighter x - enemy x| < 30 and the fighter's feet within 30 of the tread box's top): kind,
        state, slot, the fighter's status | situation << 16, its KineticModule kind (+0x11C), the y of its sum speed
        of energy mask 1 (what the game's auto-tread tests: < 0 = falling) and of all energies (float bits).
  nr    the same frame: the fighter's x / y, the enemy's x / y (its posture, or the tread node's position), the feet's
        y relative to the box top this frame and last frame (0 = no last frame), and the box half width.
  nb    the same frame: the box centre / half height (above the posture / node), the fighter's area 0 min x / max x
        (its own box, 0xEE = none), the fighter box's x extent the test uses (left / right, clamped), the pending
        bounce entry's count word for the slot.
        The test passes when: rel now <= 0, rel last >= -2 x half height, rel now < rel last, the x ranges meet
        (enemy x +- half width against fighter x - left .. x + right), status != 0xB3, situation 2, no pending entry
        for this fighter, and speed y (mask 1) < 0: then an `hs` line follows.
  hs    a stomp taken (ub_take): kind, state, the fighter's status, its y, its tread target (int 0x10000008, before
        u_bounce writes the invalid id), its kinetic kind and speed y (mask 1). Starts `wy` for the fighter.
  pd    each pending bounce entry each cave-enemy update (u_pend, before the applied-phase test): slot, the fighter's
        status, the entry's count word (bit 16 StepJump seen, 17 the bounce applied, 18 applied again), multiplier,
        posture y, kinetic kind, speed y (mask 1).
  ap    the bounce applied (u_apply: mode int 0x11000000 = 1, float 0x1000006 = the multiplier, change_kinetic(1)):
        slot, status, the count word, kinetic kind before, speed y (mask 1) before, step count int 0x10000006.
  wy    the stomping fighter each cave-enemy update for WY_UPDATES updates after `hs` (u_pend's start): status |
        situation << 16, kinetic kind, posture y, speed y mask 1, speed y all, the int 0x11000000 (the kinetic mode),
        float 0x1000006 (the multiplier). About 20-30 frames with 3-4 enemies on the field.

  python3 tools/rpx_patch.py exe_v35.rpx OUT.rpx $(python3 tools/diag_step2r_cave.py --rpx exe_v35.rpx)

Each hook: the step 2n stub (r0, r2-r12, LR, CTR, XER, CR, f0-f13 saved; the replaced word replayed), its own cap.
Space 0x04BCC000-0x04BD0000 (zero in exe_v35; step 2q's 0x04BCE000 limit grown: 8 more lines). Sites from the
assembled cave (smashrun_walker_cave.py labels), each checked against the executable's word.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_step2n_cave as N  # noqa: E402
import diag_step2o_cave as O  # noqa: E402
import diag_step2q_cave as Q  # noqa: E402

SLOT = N.SLOT
FPR = lambda n: N.FPR_S + 8 * n  # noqa: E731
WY_UPDATES = 90
LIMIT = 0x04BD0000                # step 2r: the cave grown to region H's end (zero in exe_v35 from 0x04BC9A34)
NEAR_X, NEAR_Y = 30.0, 30.0
DROP = ('near', 'hit', 'hs', 'pd')


def kin_y(dst, mask):
    """r<dst> = the fighter (r3 on entry: its accessor)'s KineticModule sum speed y of energy mask `mask` (bits)"""
    return """
        lwz r3, 0x%(KMA)X(r3)
        cmpwi r3, 0
        li r%(D)d, 0xEE
        beq ky%(U)d
        lwz r12, 0(r3)
        lwz r12, 0x%(KMS)X(r12)
        mtctr r12
        li r4, %(M)d
        bctrl
        mr r%(D)d, r4
    ky%(U)d:
    """


def hooks_for(img):
    import smashrun_walker_cave as W
    A, _B, d = W.assemble(W.read_vt(img))
    fn = dict(A.labels)
    D = d.addr
    u32 = img.u32
    out = [h for h in Q.hooks_for(img) if h[0] not in DROP]
    k = dict(KMA=W.KM_ACC, KMS=W.KM_SPEED, KMK=0x11C, SK=W.STATUS_KIND, SITU=W.STATUS_SITU, PREV=W.PREV,
             FAM=W.FT_AREA, PH=W.ha(D['pend']), PL=W.sx(D['pend']), SKH=W.ha(D['stompk']), SKL=W.sx(D['stompk']),
             ENT=N.FIGHTER_ENTRY, R11=SLOT(11), R0=SLOT(0), F1=FPR(1), F2=FPR(2), NX=NEAR_X, NY=NEAR_Y,
             WY=WY_UPDATES, TH=W.I_TREAD_TARGET >> 16, TL=W.I_TREAD_TARGET & 0xFFFF, IM=W.I_JUMP_MODE >> 16,
             FTH=W.F_TREAD_MUL >> 16, FTL=W.F_TREAD_MUL & 0xFFFF, ICH=W.I_STEP_COUNT >> 16,
             ICL=W.I_STEP_COUNT & 0xFFFF)

    uniq = [0]

    def ky(dst, mask):
        uniq[0] += 1
        return kin_y(dst, mask) % dict(k, D=dst, M=mask, U=uniq[0])

    # the near filter: the stub has r11 / r0 in their slots, f1 = rel now, r24 the fighter's accessor, r28 the
    # enemy's position; the fighter's posture is [r24 + 0x18]
    near = """
        lwz r9, 0x18(r24)
        lfs f3, 0x10(r9)
        lfs f4, 0x10(r28)
        fsubs f3, f3, f4
        fabs f3, f3
        lis r12, rconst@ha
        addi r12, r12, rconst@l
        lfs f0, 0(r12)
        fcmpu cr0, f3, f0
        bge skip
        fabs f3, f1
        lfs f0, 4(r12)
        fcmpu cr0, f3, f0
        bge skip
    """ % k
    ub = fn['u_body']
    st_prev = O.find(u32, ub, 0xD0000000 | (1 << 21) | (10 << 16) | W.PREV)     # stfs f1, PREV(r10)
    cmp0 = st_prev + 4
    assert u32(cmp0) == 0x2C000000 and u32(cmp0 + 8) == 0xFC011000, 'u_body layout'   # cmpwi r0, 0 / fcmpu f1, f2
    out.append(('nk', st_prev, u32(st_prev), 4000, ('k', 's', 'sl', 'fst', 'kin', 'y1', 'ya'), near + """
        lwz r4, 8(r31)
        lwz r5, 4(r31)
        mr r6, r25
        lwz r9, 0x20(r24)
        lwz r7, 0x%(SK)X(r9)
        lwz r0, 0x%(SITU)X(r9)
        slwi r0, r0, 16
        or r7, r7, r0
        lwz r9, 0x%(KMA)X(r24)
        li r8, 0xEE
        cmpwi r9, 0
        beq nk_nokm
        lwz r8, 0x%(KMK)X(r9)
    nk_nokm:
        lis r11, scr@ha
        addi r11, r11, scr@l
        stw r4, 0(r11)
        stw r5, 4(r11)
        stw r7, 8(r11)
        stw r8, 0xC(r11)
        mr r3, r24
    """ % k + ky(9, 1) + """
        lis r11, scr@ha
        addi r11, r11, scr@l
        stw r9, 0x10(r11)
        mr r3, r24
    """ + ky(10, -1) + """
        lis r11, scr@ha
        addi r11, r11, scr@l
        lwz r4, 0(r11)
        lwz r5, 4(r11)
        mr r6, r25
        lwz r7, 8(r11)
        lwz r8, 0xC(r11)
        lwz r9, 0x10(r11)
    """ % k))
    out.append(('nr', cmp0, 0x2C000000, 4000, ('fx', 'fy', 'ex', 'ey', 'rn', 'rp', 'hw'), near + """
        lwz r9, 0x18(r24)
        lwz r4, 0x10(r9)
        lwz r5, 0x14(r9)
        lwz r6, 0x10(r28)
        lwz r7, 0x14(r28)
        stfs f1, 8(r1)
        lwz r8, 8(r1)
        stfs f2, 8(r1)
        lwz r9, 8(r1)
        lwz r10, 0(r27)
    """ % k))
    out.append(('nb', cmp0 + 8, 0xFC011000, 4000, ('c', 'hh', 'a0', 'a1', 'el', 'er', 'pc'), near + """
        lwz r4, 4(r27)
        lwz r5, 8(r27)
        li r6, 0xEE
        li r7, 0xEE
        lwz r9, 0x18(r24)
        lfs f6, 0x10(r9)
        lis r12, 0x%(SKH)04X
        lfs f11, %(SKL)d(r12)
        fsubs f0, f6, f6
        fmr f9, f0
        fmr f10, f0
        lwz r9, 0x%(FAM)X(r24)
        cmpwi r9, 0
        beq nb_x
        lwz r9, 0xC(r9)
        cmpwi r9, 0
        beq nb_x
        lwz r0, 4(r9)
        cmpwi r0, 1
        blt nb_x
        lwz r9, 8(r9)
        cmpwi r9, 0
        beq nb_x
        lwz r9, 4(r9)
        cmpwi r9, 0
        beq nb_x
        lwz r6, 0x2C(r9)
        lwz r7, 0x34(r9)
        lfs f12, 0x2C(r9)
        fsubs f9, f6, f12
        fsel f9, f9, f9, f0
        fsubs f12, f9, f11
        fsel f9, f12, f11, f9
        lfs f12, 0x34(r9)
        fsubs f10, f12, f6
        fsel f10, f10, f10, f0
        fsubs f12, f10, f11
        fsel f10, f12, f11, f10
    nb_x:
        stfs f9, 8(r1)
        lwz r8, 8(r1)
        stfs f10, 8(r1)
        lwz r9, 8(r1)
        lis r12, 0x%(PH)04X
        addi r12, r12, %(PL)d
        mulli r0, r25, 12
        add r12, r12, r0
        lwz r10, 8(r12)
    """ % k))
    take = O.find(u32, fn['ub_take'], 0x7FE3FB78) + 4         # lwz r12, 0xE0(r3), after mr r3, r31
    assert take == fn['ub_take'] + 4
    out.append(('hs', take, 0x818300E0, 300, ('k', 's', 'fst', 'fy', 'tgt', 'kin', 'y1'), """
        lis r12, wat@ha
        addi r12, r12, wat@l
        stw r24, 0(r12)
        li r0, %(WY)d
        stw r0, 4(r12)
        lwz r3, 0x28(r24)
        lwz r12, 0(r3)
        lwz r12, 0x84(r12)
        mtctr r12
        lis r4, 0x%(TH)04X
        ori r4, r4, 0x%(TL)04X
        bctrl
        stw r3, 8(r1)
        mr r3, r24
    """ % k + ky(10, 1) + """
        lwz r8, 8(r1)
        lwz r4, 8(r31)
        lwz r5, 4(r31)
        lwz r6, 0x20(r24)
        lwz r6, 0x%(SK)X(r6)
        lwz r7, 0x18(r24)
        lwz r7, 0x14(r7)
        lwz r9, 0x%(KMA)X(r24)
        lwz r9, 0x%(KMK)X(r9)
    """ % k))
    # pd: u_pend at `rlwinm. r0, r10, 0, 14, 14` (r28 the slot, r27 the entry, r10 its count word, r12 the status)
    pdw = 0x54000000 | (10 << 21) | (0 << 16) | (0 << 11) | (14 << 6) | (14 << 1) | 1
    pd = O.find(u32, fn['upd_loop'], pdw)
    out.append(('pd', pd, pdw, 1500, ('sl', 'fst', 'cnt', 'mul', 'fy', 'kin', 'y1'), """
        lwz r3, 0(r27)
    """ + ky(10, 1) + """
        mr r4, r28
        lwz r5, %(R12)d(r1)
        lwz r6, 8(r27)
        lwz r7, 4(r27)
        lwz r9, 0(r27)
        lwz r8, 0x18(r9)
        lwz r8, 0x14(r8)
        lwz r9, 0x%(KMA)X(r9)
        lwz r9, 0x%(KMK)X(r9)
    """ % dict(k, R12=SLOT(12))))
    # ap: u_apply's first word (r27 the entry, r28 the slot)
    out.append(('ap', fn['u_apply'], 0x9421FFF0, 300, ('sl', 'fst', 'cnt', 'kin', 'y1', 'stp'), """
        lwz r3, 0(r27)
    """ + ky(8, 1) + """
        stw r8, 8(r1)
        lwz r3, 0(r27)
        lwz r3, 0x28(r3)
        lwz r12, 0(r3)
        lwz r12, 0x84(r12)
        mtctr r12
        lis r4, 0x%(ICH)04X
        ori r4, r4, 0x%(ICL)04X
        bctrl
        mr r9, r3
        lwz r8, 8(r1)
        mr r4, r28
        lwz r10, 0(r27)
        lwz r5, 0x20(r10)
        lwz r5, 0x%(SK)X(r5)
        lwz r6, 8(r27)
        lwz r7, 0x%(KMA)X(r10)
        lwz r7, 0x%(KMK)X(r7)
    """ % k))
    # wy: u_pend's first word, while `hs` armed it
    out.append(('wy', fn['u_pend'], 0x9421FFE0, 1500, ('fst', 'kin', 'fy', 'y1', 'ya', 'mode', 'mul'), """
        lis r12, wat@ha
        addi r12, r12, wat@l
        lwz r9, 4(r12)
        cmpwi r9, 0
        ble skip
        addi r9, r9, -1
        stw r9, 4(r12)
        lwz r3, 0(r12)
    """ + ky(9, 1) + """
        lis r11, scr@ha
        addi r11, r11, scr@l
        stw r9, 0(r11)
        lis r12, wat@ha
        lwz r3, wat@l(r12)
    """ + ky(10, -1) + """
        lis r11, scr@ha
        addi r11, r11, scr@l
        stw r10, 4(r11)
        lis r12, wat@ha
        lwz r3, wat@l(r12)
        lwz r3, 0x28(r3)
        lwz r12, 0(r3)
        lwz r12, 0x84(r12)
        mtctr r12
        lis r4, 0x%(IM)04X
        bctrl
        lis r11, scr@ha
        addi r11, r11, scr@l
        stw r3, 8(r11)
        lis r12, wat@ha
        lwz r3, wat@l(r12)
        lwz r3, 0x28(r3)
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        lis r4, 0x%(FTH)04X
        ori r4, r4, 0x%(FTL)04X
        bctrl
        lis r11, scr@ha
        addi r11, r11, scr@l
        stfs f1, 0xC(r11)
        lis r12, wat@ha
        lwz r3, wat@l(r12)
        lwz r9, 0x20(r3)
        lwz r4, 0x%(SK)X(r9)
        lwz r0, 0x%(SITU)X(r9)
        slwi r0, r0, 16
        or r4, r4, r0
        lwz r5, 0x%(KMA)X(r3)
        lwz r5, 0x%(KMK)X(r5)
        lwz r6, 0x18(r3)
        lwz r6, 0x14(r6)
        lwz r7, 0(r11)
        lwz r8, 4(r11)
        lwz r9, 8(r11)
        lwz r10, 0xC(r11)
    """ % k))
    return out


def build(orig):
    """diag_step2q_cave.build (step 2p's: k2n / kdn) with `wat` (the watched fighter, its update count) and `rconst`
    (the near window) after them"""
    real_asm = N.Asm.asm

    def asm(self, text):
        if text.startswith('cnt:\n.word 0\nmcnt:\n.word 0'):
            text = (text + '\nwat:\n.word 0\n.word 0\nscr:\n' + '.word 0\n' * 6 +
                    'rconst:\n.float %r\n.float %r' % (NEAR_X, NEAR_Y))
        return real_asm(self, text)
    N.Asm.asm = asm
    try:
        return Q.build(orig)
    finally:
        N.Asm.asm = real_asm


def args(rpx):
    import smashrun_enemy_cave as E
    img = E.Image(rpx)
    N.LIMIT = LIMIT
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
    ap.add_argument('--rpx', required=True, help='the executable it goes on (exe_v35): hook words checked')
    a = ap.parse_args()
    print(' '.join(args(a.rpx)))


if __name__ == '__main__':
    main()
