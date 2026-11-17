#!/usr/bin/env python3
"""Screen_Invert (exe_v46z_inv, screen_invert v1): the 3D picture as a photo-negative, with a strength, a saturation,
a brightness and a colour lift, faded in / out, through the game's own colour-correction pass. Xenoverse 2's BPE 78
"Invert World Colors" (Hit's Time Skip) needs it. Prints rpx_patch.py arguments for an executable with
exe_v46z_camfx5's patches (or any later chain of the same caves); asserts every word it replaces.

  python3 tools/rpx_patch.py exe_v46z_camfx5.rpx exe_v46z_inv.rpx $(python3 tools/screen_invert_cave.py --rpx exe_v46z_camfx5.rpx)
  python3 tools/screen_invert_cave.py --labels tools/Sm4shCommand/param_labels.json     (Sm4shCommand's entry)

How Smash 4 colours its 3D picture (read from cross_f.rpx; docs/native-notes.md "Screen colour (Screen_Invert)"):
  - The last 3D pass copies the scene with shader/copy_color.nsh's colour-correct programs (0x44100001 and the other
    odd ids: out.rgb = dot(correct_param[i], (rgb, 1)), alpha kept; uniform block PostEffectSettings, CB6, three vec4:
    a 3x4 colour matrix, rows R / G / B, the 4th column an offset). The shader selector 0x0332E398 picks the odd
    (colour-correct) variant from its r4; the 3D copy's call (0x033333F0) passes 1.
  - The matrix is built every frame by the post-effect object ([render manager 0x10423DCC] + 0x1FF0, class vtable
    0x101A0D40, 0x400 bytes): 0x034333B0, called once a frame from the render manager's frame prep (0x0333616C). It
    composes the object's parameters (+0x304-+0x378: luma levels, chroma scale / offset (saturation, hue), RGB gains,
    a tint colour with its alpha) through the YCbCr matrices at 0x105772B0 / 0x105772F0 (0.299 / 0.587 / 0.114,
    1.402, ...), writes the 3x4 to +0x100-+0x12C (every word, every call), then locks the uniform buffer (+0x200, vt
    +0x3C, the `bctrl` at 0x03433544), copies +0x100 (0x100 bytes) into it and unlocks it.
  - Screen_Tint (EffectModule vt +0x19C, MSC EffectModule(0, ...)) drives those parameters: the screen-effect manager
    [0x102F6C38] (10 entries of 0x15C, layer < 9, priority, a 26-float parameter block lerped over the transition
    frames, update 0x0334B250 in the effect manager's frame, 0x032EFB78) hands the highest-priority entry of a layer
    other than 0 to the post-effect's setters (0x0334AC8C -> [render manager + 0x200C] vt +0xC colour / +0x1C gains /
    +0x24 levels / +0x2C chroma). Layer 0 goes to the stage instead (0x02D1D308, the stage's own colour).
  So an inversion is one more affine colour transform composed after the game's own: M' = A x M, applied to the
  matrix the builder has just written, before it goes to the GPU. No new draw, no shader change; whatever the game's
  own tint does stays, inverted with the rest.

Command: Screen_Invert(Mode, Strength, Frames, FadeIn, FadeOut, Saturation, Brightness, Red, Green, Blue) (index
SI_INDEX, CRC of the name), 11 words. One screen filter at a time (a new one replaces it).
  Mode       0: end it (fades out over this command's FadeOut, 0 at once); 1: start / replace it.
  Strength   the negative: 0 none, 1 full (out = 1 - in), between a blend (0.5: an even grey: half a negative is grey).
  Frames     held this many frames after the fade-in, then fades out over FadeOut; 0: until Mode 0 / the match ends.
  FadeIn     frames to fade in (0 at once); a filter already showing fades from where it is.
  FadeOut    frames to fade out at the end of Frames (Mode 0: this command's own).
  Saturation after the negative: 1 kept, 0 grey (Rec. 601 luma, the game's own weights), above 1 stronger.
  Brightness after that, a multiply (1 kept, 0.8 a fifth darker).
  Red, Green, Blue   then added, 0-255 (0 none; negative darkens). Brightness 1 - a with Red / Green / Blue a x C is
             a mix toward the colour C by a.
  Per channel: f(x) = Brightness x Sat(Strength x (1 - x) + (1 - Strength) x x) + RGB / 255, shown as
  (1 - w) x + w f(x), w the fade (0-1). Frames are counted in the effect manager's frame (as Screen_Tint's own fades:
  not while paused).

Hooks (each word asserted):
  LOCK    0x03433544  bctrl               the builder's uniform-buffer lock (r30 the post-effect object, its matrix at
                                          +0x100 done) -> si_lock: M' = A M in place when a filter shows, then the lock
  TICK    0x032EFB78  bl 0x0334B250       the screen-effect manager's update in the effect frame -> si_tick: the
                                          game's update, then the filter's frame (fades, Frames)
  CLEAR   tsu_clear's last word (ts_tick_cave.py, b 0x02FB349C): the game's "clear every slow-motion" (training reset,
          restart, match start / end) -> si_clear: the filter off, then back
  LOOKUP / SIZE1 / SIZE2 / FETCH: as tools/camera_effect_cave.py (chained in front of the earlier caves' fallbacks).
  --diag: TEST ONLY OSReport lines (S4IC / S4ID per command; per locked frame S4IS state, S4IG / S4IH the game's
  matrix, S4IO / S4IP ours: the first 30 frames after a command, then every 30th; with no filter, every 600th lock).
Space: 0x04BE2000-0x04BE3000 (docs/native-notes.md "Screen colour": past the camera effects', the text region grown).
Test: tools/screen_invert_test.py (unicorn, and the builder's paired-single code in a Python interpreter).
"""
import argparse
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402
import line_test_cave as LT  # noqa: E402

CAVE, LIMIT = 0x04BE2000, 0x04BE3000
TEXT_REGION = LIMIT - 0x02000000
SI_INDEX = 2300                 # (acmd_ext 584 + k, Line_Test 1096, Var_Reset_Set 2000, Hitbox_Hold 2100, Effect_Camera
                                # 2200)
CMD_NAME = 'Screen_Invert'
CMD_CRC = zlib.crc32(CMD_NAME.encode()) & 0xFFFFFFFF
NPARAMS = 10
LUMA = (0.299, 0.587, 0.114)

LOCK_AT = 0x03433544            # bctrl: the post-effect builder's buffer lock
LOCK_WORD = 0x4E800421
BUILDER = 0x034333B0            # the post-effect's matrix builder (r3 the object; r30 in it)
BUILDER_SIG = {0x034333B0: 0x9421FFC8, 0x034333CC: 0x7C7E1B78, 0x03433510: 0x800A003C, 0x03433520: 0x7C0903A6,
               0x03433540: 0xF1BE0100, 0x0343353C: 0x3BFE0100, 0x03433548: 0x38800100, 0x03433554: 0x38A00100,
               0x03433558: 0x7FE4FB78, 0x03433508: 0xF15E0108, 0x0343351C: 0xF13E0110, 0x03433528: 0xF15E0118,
               0x03433530: 0xF1BE0120, 0x03433538: 0xF11E0128}
BUILD_CALL = 0x0333616C         # the render manager's frame prep: bl BUILDER (its only caller)
TICK_AT = 0x032EFB78            # bl 0x0334B250 (the screen-effect manager's update), in the effect manager's frame
SCREEN_UPD = 0x0334B250
SCREEN_MGR = 0x102F6C38         # [SCREEN_MGR]: the screen-effect manager (Screen_Tint's)
TICK_SIG = {0x032EFB70: 0x3C60102F, 0x032EFB74: 0x80636C38}
SLOW_CLEAR = 0x02FB3498         # b tsu_clear (ts_tick_cave.py): the slow manager's clear-all
CLEAR_BACK = 0x02FB349C
TSU_CLEAR_END = 0x3C            # tsu_clear + 0x3C: b 0x02FB349C (its last word; + 0x38: li r10, 0x10)
YCC = {0x034335B8: 0x3D401057, 0x034335C0: 0x394A72B0, 0x03433610: 0x3D601057, 0x03433620: 0x396B72F0}
DIAG_EVERY = 30
DIAG_IDLE = 600


def _bl_target(at, w):
    if w >> 26 != 18 or w & 3 != 1:
        return None
    off = w & 0x3FFFFFC
    return at + (off - 0x4000000 if off & 0x2000000 else off)


NEW_CMDS = [
    (CMD_NAME, 'h_inv', [
        ('Mode', 0, '0: end it (it fades out over this command\'s FadeOut; 0 at once). 1: start it, or replace the one '
                    'showing (it fades from where that one is).'),
        ('Strength', 1, 'The negative: 1 full (white is black, blue is orange), 0 none (Saturation / Brightness / '
                        'colour only), between a blend: 0.5 is an even grey (half a picture and half its negative).'),
        ('Frames', 0, 'Held this many frames once faded in, then it fades out over FadeOut. 0: until Mode 0 or the '
                      'match ends.'),
        ('FadeIn', 0, 'Frames to fade in (0: at once). The fade passes through grey half-way when Strength is 1.'),
        ('FadeOut', 0, 'Frames to fade out when Frames run out (with Mode 0: over this many).'),
        ('Saturation', 1, 'After the negative: 1 keeps the colours, 0 grey, 0.3 washed out, above 1 stronger.'),
        ('Brightness', 1, 'Then a multiply: 1 kept, 0.8 a fifth darker, 1.2 brighter.'),
        ('Red', 1, 'Then added, 0-255 (0 none; negative takes away). With Brightness 1 - a, Red / Green / Blue = a x '
                   'a colour mixes toward that colour by a.'),
        ('Green', 1, 'Added green, 0-255.'),
        ('Blue', 1, 'Added blue, 0-255.')],
     'Turns the 3D picture (fighters, stage, effects; not the HUD) into a photo-negative, with a strength, saturation, '
     'brightness and colour lift, faded in and out: the game\'s own colour-correction pass (the one Screen_Tint uses). '
     'One at a time; ends with Mode 0, its Frames, or the match / a training reset. New command: needs the patched '
     'cross_f.rpx (tools/screen_invert_cave.py, exe_v46z_inv).'),
]


def find(orig):
    s = LT.find(orig)
    for k in ('lk_none', 's1', 's2', 'f'):
        if s[k + '_word'] >> 26 == 18:
            assert not CAVE <= LT.bdecode(s[k], s[k + '_word']) < LIMIT, 'already patched (%s)' % k
    assert orig(LOCK_AT) == LOCK_WORD, 'lock 0x%08X: 0x%08X (want bctrl)' % (LOCK_AT, orig(LOCK_AT))
    for at, want in list(BUILDER_SIG.items()) + list(TICK_SIG.items()) + list(YCC.items()):
        assert orig(at) == want, '0x%08X: 0x%08X, not 0x%08X' % (at, orig(at), want)
    assert _bl_target(BUILD_CALL, orig(BUILD_CALL)) == BUILDER, 'builder call 0x%08X' % BUILD_CALL
    assert _bl_target(TICK_AT, orig(TICK_AT)) == SCREEN_UPD, 'tick 0x%08X: 0x%08X' % (TICK_AT, orig(TICK_AT))
    w = orig(SLOW_CLEAR)
    assert w >> 26 == 18 and not w & 3, 'slow clear 0x%08X: 0x%08X (want ts_tick_cave.py\'s b tsu_clear)' % (
        SLOW_CLEAR, w)
    tsu = LT.bdecode(SLOW_CLEAR, w)
    s['clear_at'] = tsu + TSU_CLEAR_END
    assert orig(tsu + TSU_CLEAR_END - 4) == 0x39400010, 'tsu_clear: no li r10, 0x10 at 0x%08X' % (tsu + 0x38)
    cw = orig(s['clear_at'])
    assert cw >> 26 == 18 and not cw & 3, 'tsu_clear end 0x%08X: 0x%08X' % (s['clear_at'], cw)
    s['clear_to'] = LT.bdecode(s['clear_at'], cw)
    assert s['clear_to'] == CLEAR_BACK or not CAVE <= s['clear_to'] < LIMIT, 'already patched (clear)'
    return s


DIAG_FMTS = [
    ('s_ic', 'S4IC mode=%d s=%08X fr=%d in=%d out=%d sat=%08X bri=%08X\n'),
    ('s_id', 'S4ID add=%08X %08X %08X ph=%d w=%08X\n'),
    ('s_is', 'S4IS n=%d lock=%d ph=%d w=%08X left=%d on=%d\n'),
    ('s_ig', 'S4IG %08X %08X %08X %08X %08X %08X\n'),
    ('s_ih', 'S4IH %08X %08X %08X %08X %08X %08X\n'),
    ('s_io', 'S4IO %08X %08X %08X %08X %08X %08X\n'),
    ('s_ip', 'S4IP %08X %08X %08X %08X %08X %08X\n'),
]


def _words(s):
    b = s.encode() + b'\0'
    b += b'\0' * (-len(b) % 4)
    return ''.join('        .word 0x%08X\n' % struct.unpack_from('>I', b, i)[0] for i in range(0, len(b), 4))


def _mat_src():
    """si_mat(): A (si_a, 3x4) from the state: A = (1 - w) [I | 0] + w [F | f]; F = Bri (1 - 2 s) Sat,
    Sat[i][j] = k d_ij + (1 - k) luma_j; f_i = Bri s + add_i. Leaf: r12, f0-f13"""
    out = """
si_mat:
        lis r12, si_st@ha
        addi r12, r12, si_st@l
        lfs f1, 4(r12)                  # w
        lfs f2, 0x14(r12)               # s
        lfs f3, 0x18(r12)               # k
        lfs f4, 0x1C(r12)               # Bri
        lis r11, si_k@ha
        addi r11, r11, si_k@l
        lfs f5, 4(r11)                  # 1
        lfs f6, 8(r11)                  # 2
        fnmsubs f7, f6, f2, f5          # 1 - 2 s
        fmuls f7, f7, f4                # c = Bri (1 - 2 s)
        fmuls f7, f7, f1                # w c
        fsubs f8, f5, f3                # 1 - k
        fmuls f8, f8, f7                # w c (1 - k)
        fmuls f9, f7, f3                # w c k
        fsubs f10, f5, f1               # 1 - w
        fadds f9, f9, f10               # diagonal extra: w c k + 1 - w
        fmuls f11, f4, f2               # Bri s
"""
    for i in range(3):
        for j in range(3):
            out += """        lfs f12, %d(r11)
        fmuls f12, f12, f8
""" % (0x10 + 4 * j)
            if i == j:
                out += "        fadds f12, f12, f9\n"
            out += "        stfs f12, %d(r12)\n" % (0x30 + 16 * i + 4 * j)
        out += """        lfs f12, %d(r12)
        fadds f12, f12, f11
        fmuls f12, f12, f1
        stfs f12, %d(r12)
""" % (0x20 + 4 * i, 0x30 + 16 * i + 12)
    out += "        blr\n"
    return out


def _apply_src():
    """si_apply(r3 the 3x4 matrix, in place): M' = A M (A affine: its 4th column added to the offsets). Leaf: r12,
    f0-f13"""
    out = """
si_apply:
        lis r12, si_st@ha
        addi r12, r12, si_st@l
"""
    for n in range(12):
        out += "        lfs f%d, %d(r3)\n" % (n, 4 * n)
    for i in range(3):
        for j in range(4):
            for k in range(3):
                out += "        lfs f13, %d(r12)\n" % (0x30 + 16 * i + 4 * k)
                src = 4 * k + j
                if k == 0:
                    out += "        fmuls f12, f13, f%d\n" % src
                else:
                    out += "        fmadds f12, f13, f%d, f12\n" % src
            if j == 3:
                out += "        lfs f13, %d(r12)\n        fadds f12, f12, f13\n" % (0x30 + 16 * i + 12)
            out += "        stfs f12, %d(r3)\n" % (16 * i + 4 * j)
    out += "        blr\n"
    return out


def src(s, hand, diag=False, pad=False):
    D = dict(base=SI_INDEX, crc_h=CMD_CRC >> 16, crc_l=CMD_CRC & 0xFFFF, s1b=s['s1_back'], s2b=s['s2_back'],
             fb=s['f_back'], hand_h=hand >> 16, hand_l=hand & 0xFFFF, size=1 + NPARAMS, step=4 * (1 + NPARAMS),
             upd=SCREEN_UPD, clear_to=s['clear_to'], every=DIAG_EVERY, idle=DIAG_IDLE)
    out = """
# --- the command tables' fallbacks --------------------------------------------------------------------------------
si_lookup:                              # r3 = a CRC no table before has
        lis r12, %(crc_h)d
        ori r12, r12, %(crc_l)d
        cmplw r3, r12
        bne sil_none
        li r3, %(base)d
        blr
""" % D + LT.replay(s['lk_none'], s['lk_none_word'], s['lk_none'] + 4, 'sil_none') + """
si_size1:                               # r3 index -> r0 its size
        cmplwi r3, %(base)d
        bne sis1_orig
        li r0, %(size)d
        b 0x%(s1b)08X
""" % D + LT.replay(s['s1'], s['s1_word'], s['s1_back'], 'sis1_orig') + """
si_size2:                               # r3 index -> r12 its size
        cmplwi r3, %(base)d
        bne sis2_orig
        li r12, %(size)d
        b 0x%(s2b)08X
""" % D + LT.replay(s['s2'], s['s2_word'], s['s2_back'], 'sis2_orig') + """
si_fetch:                               # r7 index -> r0 its handler (r6 free)
        cmplwi r7, %(base)d
        bne sif_orig
        lis r6, %(hand_h)d
        ori r0, r6, %(hand_l)d
        b 0x%(fb)08X
""" % D + ("""
sif_orig:
        b 0x%08X
""" % LT.bdecode(s['f'], s['f_word']) if s['f_word'] >> 26 == 18 else """
sif_orig:
        slwi r6, r7, 2
        lwzx r0, r6, r29
        b 0x%08X
""" % s['f_back'])
    out += """
# --- Screen_Invert(Mode, Strength, Frames, FadeIn, FadeOut, Saturation, Brightness, Red, Green, Blue):
#     (r3 accessor, r5 script state, r6 (+8 execute), r7 parameters) ---------------------------------------------
h_inv:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stw r31, 0x2C(r1)
        stw r30, 0x28(r1)
        stw r29, 0x24(r1)
        mr r31, r5
        mr r30, r7
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq si_step
        lis r29, si_st@ha
        addi r29, r29, si_st@l
        lwz r11, 0x60(r29)              # commands run
        addi r11, r11, 1
        stw r11, 0x60(r29)
        li r0, 0
        stw r0, 0x64(r29)               # (diag: locks since this command)
        lwz r0, 0(r30)                  # Mode
        cmpwi r0, 0
        bne si_start
        lwz r0, 0(r29)                  # Mode 0: nothing showing -> nothing
        cmpwi r0, 0
        beq si_done
        lwz r3, 0x10(r30)               # FadeOut
        bl si_rate                      # f1 = 1 / FadeOut, or 0 (FadeOut <= 0: at once)
        stfs f1, 0xC(r29)
        li r0, 3
        stw r0, 0(r29)
        lis r12, si_k@ha
        lfs f0, si_k@l(r12)             # 0
        fcmpu cr0, f1, f0
        bne si_done
        li r0, 0                        # FadeOut 0: off at once
        stw r0, 0(r29)
        stfs f0, 4(r29)
        b si_done
si_start:
        lwz r0, 4(r30)                  # Strength, Saturation, Brightness
        stw r0, 0x14(r29)
        lwz r0, 0x14(r30)
        stw r0, 0x18(r29)
        lwz r0, 0x18(r30)
        stw r0, 0x1C(r29)
        lis r12, si_k@ha
        addi r12, r12, si_k@l
        lfs f0, 0xC(r12)                # 1 / 255
        lfs f1, 0x1C(r30)               # Red, Green, Blue
        fmuls f1, f1, f0
        stfs f1, 0x20(r29)
        lfs f1, 0x20(r30)
        fmuls f1, f1, f0
        stfs f1, 0x24(r29)
        lfs f1, 0x24(r30)
        fmuls f1, f1, f0
        stfs f1, 0x28(r29)
        lwz r0, 8(r30)                  # Frames (negative: 0)
        cmpwi r0, 0
        bge sis_fr
        li r0, 0
sis_fr:
        stw r0, 0x10(r29)
        lwz r3, 0x10(r30)               # FadeOut: its rate (0: at once, a rate of 1)
        bl si_rate
        lis r12, si_k@ha
        addi r12, r12, si_k@l
        lfs f0, 0(r12)
        fcmpu cr0, f1, f0
        bne sis_out
        lfs f1, 4(r12)                  # 1
sis_out:
        stfs f1, 0xC(r29)
        lwz r0, 0(r29)                  # nothing showing: from 0
        cmpwi r0, 0
        bne sis_from
        stfs f0, 4(r29)
sis_from:
        lwz r3, 0xC(r30)                # FadeIn
        bl si_rate
        lis r12, si_k@ha
        addi r12, r12, si_k@l
        lfs f0, 0(r12)
        fcmpu cr0, f1, f0
        beq sis_now
        stfs f1, 8(r29)
        li r0, 1
        stw r0, 0(r29)
        b si_done
sis_now:
        lfs f1, 4(r12)                  # FadeIn 0: full at once
        stfs f1, 4(r29)
        li r0, 2
        stw r0, 0(r29)
si_done:
        bl si_mat
        mr r3, r30
        bl si_dcmd                      # (diag build: S4IC / S4ID; else a blr)
si_step:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne si_ret
        lwz r11, 4(r31)
        addi r11, r11, %(step)d
        stw r11, 4(r31)
        li r3, 2
si_ret:
        lwz r29, 0x24(r1)
        lwz r30, 0x28(r1)
        lwz r31, 0x2C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# si_rate(r3 frames) -> f1 1 / frames (frames > 0), else 0. r0 r12 f0
si_rate:
        lis r12, si_k@ha
        addi r12, r12, si_k@l
        lfs f1, 0(r12)
        cmpwi r3, 0
        blelr
        stwu r1, -0x20(r1)
        xoris r3, r3, 0x8000
        stw r3, 0xC(r1)
        lis r0, 0x4330
        stw r0, 8(r1)
        lfd f1, 8(r1)
        lfd f0, 0x28(r12)               # 2^52 + 2^31
        fsub f1, f1, f0
        frsp f1, f1
        lfs f0, 4(r12)
        fdivs f1, f0, f1
        addi r1, r1, 0x20
        blr

# --- the filter's frame (si_tick: bl from 0x032EFB78 in the effect manager's frame, r3 the screen-effect manager) ----
si_tick:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        bl 0x%(upd)08X                  # the game's screen-effect update (Screen_Tint's fades), as before
        bl si_frame
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

si_frame:
        lis r12, si_st@ha
        addi r12, r12, si_st@l
        lwz r0, 0(r12)
        cmpwi r0, 0
        beqlr
        lwz r11, 0x2C(r12)              # frames ticked
        addi r11, r11, 1
        stw r11, 0x2C(r12)
        lfs f1, 4(r12)                  # w
        lis r11, si_k@ha
        addi r11, r11, si_k@l
        lfs f5, 4(r11)                  # 1
        lfs f6, 0(r11)                  # 0
        cmpwi r0, 1
        bne sif_hold
        lfs f2, 8(r12)                  # fade in
        fadds f1, f1, f2
        fcmpu cr0, f1, f5
        blt sif_w
        fmr f1, f5
        li r0, 2
        stw r0, 0(r12)
        b sif_w
sif_hold:
        cmpwi r0, 2
        bne sif_out
        lwz r11, 0x10(r12)              # Frames (0: held)
        cmpwi r11, 0
        beq sif_w
        addi r11, r11, -1
        stw r11, 0x10(r12)
        cmpwi r11, 0
        bne sif_w
        li r0, 3                        # its time is up: the fade out from the next frame
        stw r0, 0(r12)
        b sif_w
sif_out:
        lfs f2, 0xC(r12)                # fade out
        fsubs f1, f1, f2
        fcmpu cr0, f1, f6
        bgt sif_w
        fmr f1, f6
        li r0, 0
        stw r0, 0(r12)
sif_w:
        stfs f1, 4(r12)
        b si_mat

# --- si_clear: tsu_clear's last word (the game's clear-all of the slow-motions: training reset, restart, match start /
#     end): the filter off, then on as before (r3 / r10 kept) ---------------------------------------------------------
si_clear:
        lis r12, si_st@ha
        addi r12, r12, si_st@l
        li r0, 0
        stw r0, 0(r12)
        stw r0, 4(r12)
        b 0x%(clear_to)08X

# --- si_lock: the builder's lock call (bctrl at 0x03433544: r3 the buffer, r4 0, ctr the lock; r30 the post-effect
#     object, its matrix at +0x100 written): the filter on the matrix, then the lock (its return: 0x03433548) --------
si_lock:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stw r3, 0x10(r1)
        stw r4, 0x14(r1)
        .word 0x7C0902A6                # mfctr r0
        stw r0, 0x18(r1)
        lis r12, si_st@ha
        addi r12, r12, si_st@l
        lwz r11, 0x68(r12)              # locks seen
        addi r11, r11, 1
        stw r11, 0x68(r12)
        addi r3, r30, 0x100
        bl si_dgame                     # (diag: the game's matrix; else a blr)
        lis r12, si_st@ha
        addi r12, r12, si_st@l
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq sil_go
        lwz r11, 0x6C(r12)              # matrices changed
        addi r11, r11, 1
        stw r11, 0x6C(r12)
        addi r3, r30, 0x100
        bl si_apply
        addi r3, r30, 0x100
        bl si_dours                     # (diag: ours)
sil_go:
        lwz r0, 0x18(r1)
        mtctr r0
        lwz r3, 0x10(r1)
        lwz r4, 0x14(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        bctr
""" % D
    out += _mat_src() + _apply_src()
    if not diag:
        out += """
si_dcmd:
si_dgame:
si_dours:
        blr
"""
    else:
        out += _diag_src()
    out += ('        .word 0\n' if pad else '') + """
si_k:                                   # 0, 1, 2, 1 / 255, luma R G B, (pad), 2^52 + 2^31 (a double, 8-aligned)
        .float 0
        .float 1
        .float 2
        .float 0.00392156862745098
        .float %r
        .float %r
        .float %r
        .word 0
        .word 0
        .word 0
        .word 0x43300000
        .word 0x80000000
si_st:                                  # +0 phase (0 off, 1 in, 2 held, 3 out), +4 w, +8 in rate, +0xC out rate,
""" % LUMA + """\
        .word 0                         # +0x10 Frames left, +0x14 Strength, +0x18 Saturation, +0x1C Brightness,
        .word 0                         # +0x20 add R G B (0-1), +0x2C frames ticked, +0x30 A (3x4), +0x60 commands,
""" + '        .word 0\n' * 0x1E + (_diag_data() if diag else '')
    return out


def _diag_src():
    import diag_godfist_cave as G
    rep = """
        lis r12, 0x%X
        ori r12, r12, 0x%X
        mtctr r12
        .word 0x%08X
        bctrl""" % (G.OSREPORT_VENEER >> 16, G.OSREPORT_VENEER & 0xFFFF, G.CRCLR_CR1EQ)

    def six(lab, base_reg, off):
        return """
        lis r3, %s@ha
        addi r3, r3, %s@l
        lwz r4, %d(%s)
        lwz r5, %d(%s)
        lwz r6, %d(%s)
        lwz r7, %d(%s)
        lwz r8, %d(%s)
        lwz r9, %d(%s)""" % ((lab, lab) + sum(((off + 4 * i, base_reg) for i in range(6)), ())) + rep
    return """
# --- diag: S4IC / S4ID at every command (r3 its parameters) --------------------------------------------------------
si_dcmd:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r29, 0x24(r1)
        mr r31, r3
        lis r3, s_ic@ha
        addi r3, r3, s_ic@l
        lwz r4, 0(r31)
        lwz r5, 4(r31)
        lwz r6, 8(r31)
        lwz r7, 0xC(r31)
        lwz r8, 0x10(r31)
        lwz r9, 0x14(r31)
        lwz r10, 0x18(r31)""" + rep + """
        lis r30, si_st@ha
        addi r30, r30, si_st@l
        lis r3, s_id@ha
        addi r3, r3, s_id@l
        lwz r4, 0x20(r30)
        lwz r5, 0x24(r30)
        lwz r6, 0x28(r30)
        lwz r7, 0(r30)
        lwz r8, 4(r30)""" + rep + """
        lmw r29, 0x24(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- diag: si_dgame(r3 the game's matrix) decides whether this lock is logged (the first %(every)d after a command,
#     then every %(every)dth; with no filter every %(idle)dth) and prints S4IS / S4IG / S4IH; si_dours(r3) S4IO / S4IP ----
si_dgame:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r29, 0x24(r1)
        mr r31, r3
        lis r30, si_st@ha
        addi r30, r30, si_st@l
        lis r12, si_dg@ha
        addi r12, r12, si_dg@l
        li r0, 0
        stw r0, 0(r12)
        lwz r11, 0x64(r30)              # locks since the last command
        addi r0, r11, 1
        stw r0, 0x64(r30)
        lwz r0, 0(r30)
        cmpwi r0, 0
        bne sdg_on
        lwz r11, 0x68(r30)              # no filter: every %(idle)dth lock
        li r9, %(idle)d
        b sdg_mod
sdg_on:
        cmpwi r11, %(every)d
        blt sdg_log
        li r9, %(every)d
sdg_mod:
        divwu r8, r11, r9
        mullw r8, r8, r9
        cmpw r8, r11
        bne sdg_out
sdg_log:
        lis r12, si_dg@ha
        li r0, 1
        stw r0, si_dg@l(r12)
        lis r3, s_is@ha
        addi r3, r3, s_is@l
        lwz r4, 0x2C(r30)
        lwz r5, 0x68(r30)
        lwz r6, 0(r30)
        lwz r7, 4(r30)
        lwz r8, 0x10(r30)
        lwz r9, 0x6C(r30)""" % dict(every=DIAG_EVERY, idle=DIAG_IDLE) + rep + six('s_ig', 'r31', 0) + \
        six('s_ih', 'r31', 0x18) + """
sdg_out:
        lmw r29, 0x24(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

si_dours:
        lis r12, si_dg@ha
        lwz r0, si_dg@l(r12)
        cmpwi r0, 0
        beqlr
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r29, 0x24(r1)
        mr r31, r3""" + six('s_io', 'r31', 0) + six('s_ip', 'r31', 0x18) + """
        lmw r29, 0x24(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
"""


def _diag_data():
    out = 'si_dg:                                  # diag: this lock logged\n        .word 0\n'
    for lab, fmt in DIAG_FMTS:
        out += '%s:\n' % lab + _words(fmt)
    return out


def build(orig, diag=False):
    s = find(orig)
    hand, pad = 0, False
    for _p in range(3):
        a = Asm(CAVE)
        a.asm(src(s, hand, diag, pad))
        hand = a.addr('h_inv')
        if a.addr('si_k') % 8:
            pad = not pad
    words = a.words()
    end = CAVE + 4 * len(words)
    assert end <= LIMIT, 'cave too big: 0x%08X' % end
    assert a.addr('si_k') % 8 == 0, 'si_k not 8-aligned (its double)'
    for x in range(CAVE, LIMIT, 4):
        assert orig(x) == 0, 'cave word 0x%08X not free' % x
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    out[s['lk_none']] = LT.branch(s['lk_none'], a.addr('si_lookup'))
    out[s['s1']] = LT.branch(s['s1'], a.addr('si_size1'))
    out[s['s2']] = LT.branch(s['s2'], a.addr('si_size2'))
    out[s['f']] = LT.branch(s['f'], a.addr('si_fetch'))
    out[LOCK_AT] = LT.branch(LOCK_AT, a.addr('si_lock')) | 1
    out[TICK_AT] = LT.branch(TICK_AT, a.addr('si_tick')) | 1
    out[s['clear_at']] = LT.branch(s['clear_at'], a.addr('si_clear'))
    return out, a.labels, s


def rpx_reader(path):
    """the executable's words; the grown end (up to LIMIT) reads 0"""
    import kind_expand as K
    img = K.Image(path)

    def orig(addr):
        try:
            return img.w(addr)
        except KeyError:
            if CAVE <= addr < LIMIT:
                return 0
            raise
    return orig


def labels(path):
    """Screen_Invert's entry in tools/Sm4shCommand/param_labels.json (apply_param_labels.py then puts it in Events.cfg
    and tools/acmd_info.json; its group, help and examples come from acmd_ext_help.py)"""
    import json
    from acmd_ext_help import GROUP, HELP, EXAMPLES
    d = json.load(open(path))
    for name, _h, params, desc in NEW_CMDS:
        e = {'_command': name, '_new': True, '_name': name, '_size': 1 + len(params), '_desc': desc,
             '_format': [t for _n, t, _d in params]}
        for k, (pname, _t, pdesc) in enumerate(params):
            e[str(k)] = {'name': pname, 'desc': pdesc, 'confidence': 'high'}
        e['_example'] = EXAMPLES.get(name, [])
        e['_group'], e['_help'] = GROUP.get(name), HELP.get(name, [])
        d['%08X' % LT.crc(name)] = e
    json.dump(dict(sorted(d.items())), open(path, 'w'), indent=1)


def present(img_w):
    """the executable has this cave (Screen_Invert's CRC in si_lookup) - for port_check"""
    hi, lo = 0x3D800000 | (CMD_CRC >> 16), 0x618C0000 | (CMD_CRC & 0xFFFF)
    try:
        return any(img_w(x) == hi and img_w(x + 4) == lo for x in range(CAVE, CAVE + 0x40, 4))
    except Exception:              # noqa: BLE001
        return False


def filter_matrix(w, strength, saturation, brightness, rgb255):
    """A (3x4, rows, the offset in column 3) the cave applies after the game's matrix (Python reference)"""
    c = brightness * (1 - 2 * strength)
    A = []
    for i in range(3):
        row = [(1 - w) * (i == j) + w * c * (saturation * (i == j) + (1 - saturation) * LUMA[j]) for j in range(3)]
        row.append(w * (brightness * strength + rgb255[i] / 255.0))
        A.append(row)
    return A


def compose(A, M):
    """A after M (both 3x4 affine)"""
    return [[sum(A[i][k] * M[k][j] for k in range(3)) + (A[i][3] if j == 3 else 0) for j in range(4)]
            for i in range(3)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', help='the executable to patch (exe_v46z_camfx5 or later)')
    p.add_argument('--labels', help='update this param_labels.json with Screen_Invert')
    p.add_argument('--diag', action='store_true', help='TEST ONLY: the OSReport build (S4IC / S4ID / S4IS / S4IG / '
                   'S4IH / S4IO / S4IP lines, docs/native-notes.md "Screen colour")')
    args = p.parse_args()
    if args.labels:
        labels(args.labels)
        return
    if not args.rpx:
        p.error('--rpx or --labels')
    words, lab, _s = build(rpx_reader(args.rpx), args.diag)
    print(' '.join(['textregion:0x%X' % TEXT_REGION, 'grow:0x%08X' % LIMIT] +
                   ['0x%08X=0x%08X' % kv for kv in sorted(words.items())]))
    sys.stderr.write('screen invert: %d words, Screen_Invert index %d (0x%08X), h_inv 0x%08X, si_lock 0x%08X, '
                     'end 0x%08X\n' % (len(words), SI_INDEX, CMD_CRC, lab['h_inv'], lab['si_lock'],
                                       max(a for a in words if a >= CAVE) + 4))


if __name__ == '__main__':
    main()
