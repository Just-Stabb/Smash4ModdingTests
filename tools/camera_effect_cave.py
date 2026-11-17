#!/usr/bin/env python3
"""Effect_Camera (exe_v46z_camfx, camera_effects v1): an effect attached to the camera. It is requested like any effect
of the object (its fighter's / article's bank or the common one, through the object's own EffectModule, so
EFFECT_OFF_KIND / LAST_EFFECT_SET_* / the module's kills work on it) and, every frame until it ends, its matrix is set
from the camera the game draws with: offsets in camera space (X right, Y up, Z forward from the eye), the effect's own
X / Y / Z axes along the screen's right / up / toward the viewer, its size kept to the same part of the screen when the
camera zooms (Mode 1). Xenoverse 2's camera-attached screen effects (BTL_CMN 108 HIT_DmgGrs2, the time-stop darken
with glass shattering) need it. Prints rpx_patch.py arguments for an executable with exe_v46y_hold's patches (or any
later chain of the same caves); asserts every word it replaces.

  python3 tools/rpx_patch.py exe_v46y_hold.rpx exe_v46z_camfx.rpx $(python3 tools/camera_effect_cave.py --rpx exe_v46y_hold.rpx)
  python3 tools/camera_effect_cave.py --labels tools/Sm4shCommand/param_labels.json     (Sm4shCommand's entry)

Why a per-frame matrix, not an eft flag: Smash 4's eft (NW4F, docs/ptcl-format.md) has no camera / screen-space emitter
mode. An emitter's follow type (0x310: 0 follow the emitter set, 1 none, 2 position only), its particle types
(billboards turn each particle to the camera, not the set), its camera offset (0x4D0: a depth bias toward the camera)
and the effect manager's own instance modes (flag 0x20 / 0x40: the set turned toward the eye; +0x150: moved toward
the eye by a distance) all keep the effect where it was requested in the world. So the cave writes the effect
instance's matrix from the camera each frame (docs/native-notes.md "Camera effects").

What the game gives (read from cross_f.rpx, docs/native-notes.md "Camera effects"):
  - the camera the renderer draws with: the effect camera table [0x0334A368()] = 0x10573CC0 (2 entries of 0xE0, TV /
    GamePad; entry +0xC the current source, +0x14 three source slots). The camera manager ([0x10352470], 0x7C0 bytes)
    registers its snapshot block (+0x780: +0 vertical FOV in radians, +8 near, +0xC far, +0x10 eye, +0x1C target, +0x28
    up, the shake offset included; written by the manager's update, vt +0x3C 0x02D2A584) as entry 0's slot 0. The
    table's update builds the view from it with 0x03349A38(view, inverse, &eye) (look-at 0x033496A0, then the rigid
    inverse: rows right, up, back (eye - target), eye) and hands it to the renderer (entry +0xD0). The cave runs the
    same function on the same source every frame, so it has the camera of the frame being drawn.
  - effect instances: the manager [0x10353CA4], pool +0x4040 (exe_v18's effect_slots_patch.py; vanilla +0x1540), 100 x
    0x1C0, +0 handle ((index << 24) | serial), +0x50 its 3x4 matrix (rows, translation in column 3), +0x144 flags. The
    calc pass 0x032EFD04 (once a frame, from 0x02D88C18 after the effect frame) runs 0x0334E0C8 on each instance: with
    flag 0x8000 it keeps +0x50 as it is (no rebuild from its position / rotation / scale) and an instance with no follow
    target gives +0x50 to eft (the emitter set's matrix, 0x032FF744). Flag 0x01000000: its step isn't multiplied by the
    global slow-motion rate ([0x10439078], Time_Scale's).
  - the request: EffectModule (accessor +0xA0) vt +0x44 0x02C29D10(module, id, &pos, &rot, flags, mta -1, 1, 0, f1 size),
    the world-placed request (MSC EffectModule's own world op); flags 0x00800000: rate 1, not tied to the owner's
    (hitlag / Target_Time_Scale). The handle is the module's last (+0x14), as LAST_EFFECT_SET_* use it.
  - kill: 0x0334C6A8(handle, 0) (EffectModule vt +0xAC's call: the emitter set fades out).

Command: Effect_Camera(Graphic, X, Y, Z, XRot, YRot, ZRot, Size, Mode, Frames, Flags) (index CF_INDEX, CRC of the name),
12 words.
  Graphic  the effect id, as EFFECT / EFFECT_FOLLOW take it (0x1000000 + n common, 0x3KK0000 + n the fighter's bank).
  X, Y     offset from the screen's centre: right / up (Mode 0 / 2: units; Mode 1: half the screen's height).
  Z        distance in front of the eye (units). At least near + 1 (3 at the default near 2): closer would be clipped.
           Mode 1: 0 or less is 20.
  XRot, YRot, ZRot   the effect's own turn in degrees (Rz Ry Rx, the EFFECT commands' order), in camera space (Mode 2:
           in world space).
  Size     its scale (Mode 1: one effect unit = Size half screen heights: a quad 2 units across (-1 to 1) at Size 1
           covers the screen's height; a bank particle of scale W is W x Size / 2 screen heights wide).
  Mode     0 follow the camera (position and turn); 1 fixed to the screen (as 0, and X / Y / Size scaled with the
           distance x tan(FOV / 2): the same part of the screen when the camera zooms or moves); 2 position only (it
           moves with the camera, its turn stays the world's). Other values: 0.
  Frames   0: until it ends by itself or is killed (EFFECT_OFF_KIND, ...); N > 0: faded out after N frames.
  Flags    bit 0 (1): unslowed: Time_Scale's slow-motion and the owner's own rate (hitlag, Target_Time_Scale) don't slow
           its animation. Other bits: reserved (0).

Hooks (each word asserted):
  CALC    0x032EFD04  stwu r1, -0x28(r1)   the effect manager's calc pass (instance matrices -> eft, then eft's calc)
                                           -> cf_calc: every tracked effect's matrix from the camera, then the pass
  LOOKUP / SIZE1 / SIZE2 / FETCH: as tools/hitbox_hold_cave.py (chained in front of the earlier caves' fallbacks).
Space: 0x04BE0000-0x04BE2000 (docs/native-notes.md "Camera effects": past var_reset's region, the text region grown).
Test: tools/camera_effect_test.py (unicorn).
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

CAVE, LIMIT = 0x04BE0000, 0x04BE2000
TEXT_REGION = LIMIT - 0x02000000           # textregion: (the code section grows to LIMIT)
CF_INDEX = 2200                 # Effect_Camera's command index (acmd_ext 584 + k, Line_Test 1096, Var_Reset_Set 2000,
                                # Hitbox_Hold 2100)
CMD_NAME = 'Effect_Camera'
CMD_CRC = zlib.crc32(CMD_NAME.encode()) & 0xFFFFFFFF
NPARAMS = 11
NTAB = 16                       # camera effects at once
ENTRY = 0x50

CALC_AT = 0x032EFD04
CALC_WORD = 0x9421FFD8          # stwu r1, -0x28(r1)
CALC_SIG = {0x032EFD08: 0xBF21000C, 0x032EFD60: 0x3B200064, 0x032EFD64: 0x3BBC4040, 0x032EFD7C: 0x4805E34D}
MGR = 0x10353CA4                # [MGR]: the effect manager
MGR_SIG = {0x0334C594: 0x3C601035, 0x0334C598: 0x80633CA4, 0x0334C59C: 0x4BFA3768}   # the calc facade: lis/lwz/b calc
POOL, POOL_N, INST = 0x4040, 100, 0x1C0
CAMTBL = 0x10573CC0             # the effect camera table (0x0334A368: lis r3, 0x1057; addi r3, r3, 0x3CC0; blr)
CAMTBL_SIG = {0x0334A368: 0x3C601057, 0x0334A36C: 0x38633CC0, 0x0334A370: 0x4E800020}
LOOKAT_INV = 0x03349A38         # (view out, inverse out, &{eye, target, up})
LOOKAT_SIG = (0x7C0802A6, 0x9421FFE8, 0x93E10014, 0x7C9F2378, 0x7CA42B78)
TANF = 0x04ADE970
TANF_SIG = (0x7C0802A6, 0xFD600890, 0x90010004, 0x9421FFE8)
ROT = 0x033730A0                # (out 3x4, f1 rx, f2 ry, f3 rz): Rz Ry Rx, radians
ROT_SIG = (0x9421FF50, 0xDB810070)
KILL = 0x0334C6A8               # (handle, 0): fade the emitter set out
KILL_SIG = (0x7C601B78, 0x7C852378, 0x3C601035, 0x80633CA4, 0x7C040378)
WORLD_REQ = 0x02C29D10          # EffectModule vt +0x44
EM_VTABLES = (0x10105FE8, 0x101228F8)
EM_ACC = 0xA0
FLAG_KEEP = 0x8000              # instance +0x144: keep +0x50 (no rebuild from position / rotation / scale)
FLAG_UNSLOWED = 0x0100          # (oris) 0x01000000: not slowed by the global slow-motion
REQ_RATE1 = 0x0080              # (lis) 0x00800000: vt +0x44's "rate 1" (not the owner's)
MODES = (0, 1, 2)

NEW_CMDS = [
    (CMD_NAME, 'h_camfx', [
        ('Graphic', 0, 'The effect\'s ID, as EFFECT / EFFECT_FOLLOW take it: 0x1000000 + n a common effect, 0x3KK0000 + '
                       'n one of the fighter\'s bank (KK its kind).'),
        ('X', 1, 'Right of the screen\'s centre. Mode 0 / 2: in units; Mode 1: in half the screen\'s height (1 = the '
                 'top / right edge at the height\'s scale; the sides are at +-1.78 on a 16:9 screen).'),
        ('Y', 1, 'Up from the screen\'s centre (units; Mode 1: half screen heights, 1 = the top edge).'),
        ('Z', 1, 'Distance in front of the camera (units, from the eye). At least the camera\'s near clip + 1 (3): '
                 'closer is put there. Mode 1: 0 or less is 20.'),
        ('XRot', 1, 'The effect\'s turn about X, degrees (camera space; Mode 2: world space).'),
        ('YRot', 1, 'The effect\'s turn about Y, degrees.'),
        ('ZRot', 1, 'The effect\'s turn about Z, degrees (Rz Ry Rx, as the EFFECT commands).'),
        ('Size', 1, 'Its scale. Mode 1: one effect unit = Size half screen heights (a quad 2 units across at Size 1 covers '
                    'the screen\'s height; a bank particle of scale W is W x Size / 2 screen heights wide: bank effects '
                    'are 10-40 units, so Mode 1 sizes of 0.02-0.2).'),
        ('Mode', 0, '0: follows the camera (position and turn). 1: fixed to the screen (as 0, and X / Y / Size scaled '
                    'with the distance x tan(FOV / 2), so it covers the same part of the screen when the camera zooms '
                    'or moves). 2: position only (moves with the camera, keeps the world\'s turn). Other values: 0.'),
        ('Frames', 0, '0: until it ends by itself or is killed (EFFECT_OFF_KIND...). N > 0: fades out after N frames.'),
        ('Flags', 0, 'Bit 1: unslowed (Time_Scale\'s slow-motion and the owner\'s hitlag / Target_Time_Scale don\'t slow '
                     'its animation). Other bits: 0.')],
     'Starts an effect attached to the camera: placed in front of it every frame (X right, Y up, Z forward from the '
     'eye), facing it, following its moves and zooms; Mode 1 keeps it on the same part of the screen (full-screen '
     'overlays). EFFECT_OFF_KIND / LAST_EFFECT_SET_* work on it. New command: needs the patched cross_f.rpx '
     '(tools/camera_effect_cave.py, exe_v46z_camfx).'),
]


def find(orig):
    s = LT.find(orig)
    w = orig(CALC_AT)
    assert w == CALC_WORD or w >> 26 == 18, 'calc 0x%08X: 0x%08X (want stwu r1, -0x28(r1) or an earlier cave\'s b)' % (
        CALC_AT, w)
    if w >> 26 == 18:
        assert not CAVE <= LT.bdecode(CALC_AT, w) < LIMIT, 'already patched (calc hook goes into this cave)'
    s['calc_word'] = w
    for at, want in list(CALC_SIG.items()) + list(MGR_SIG.items()) + list(CAMTBL_SIG.items()):
        assert orig(at) == want, '0x%08X: 0x%08X, not 0x%08X' % (at, orig(at), want)
    for base, sig, what in ((LOOKAT_INV, LOOKAT_SIG, 'look-at + inverse'), (TANF, TANF_SIG, 'tanf'),
                            (ROT, ROT_SIG, 'rotation'), (KILL, KILL_SIG, 'kill facade')):
        for i, want in enumerate(sig):
            assert orig(base + 4 * i) == want, '%s 0x%08X: 0x%08X, not 0x%08X' % (what, base + 4 * i,
                                                                                orig(base + 4 * i), want)
    assert LT.bdecode(KILL + 0x14, orig(KILL + 0x14)) == 0x032F0268, 'kill facade: not the manager\'s kill'
    for vt in EM_VTABLES:
        assert orig(vt + 0x44) == WORLD_REQ, 'EffectModule vtable 0x%08X +0x44: 0x%08X' % (vt, orig(vt + 0x44))
    for k in ('lk_none', 's1', 's2', 'f'):
        if s[k + '_word'] >> 26 == 18:
            assert not CAVE <= LT.bdecode(s[k], s[k + '_word']) < LIMIT, 'already patched (%s)' % k
    return s


def _mat_src():
    """cf_mat(r3 entry, r4 out 3x4): the effect's matrix from cf_inv / cf_state (leaf: r0 r5 r11 r12, f0-f13)"""
    out = """
cf_mat:
        lis r9, cf_k@ha
        addi r9, r9, cf_k@l             # 0, 1, 20, pi / 180, 0.5
        lis r10, cf_state@ha
        addi r10, r10, cf_state@l       # +4 tan(fov / 2), +8 near, +0xC the scale (out)
        lis r12, cf_inv@ha
        addi r12, r12, cf_inv@l         # rows: +0 right, +0x10 up, +0x20 back, +0x30 eye
        lwz r5, 4(r3)                   # mode
        lfs f0, 0x18(r3)                # dist = Z
        lfs f1, 4(r9)                   # 1.0
        cmpwi r5, 1
        bne cfm_near
        fneg f3, f0                     # Mode 1: Z <= 0 -> 20
        lfs f2, 8(r9)
        fsel f0, f3, f2, f0
cfm_near:
        lfs f2, 8(r10)                  # near
        fadds f2, f2, f1                # near + 1
        fsubs f3, f0, f2
        fsel f0, f3, f0, f2             # dist = max(dist, near + 1)
        fmr f4, f1                      # k = 1
        cmpwi r5, 1
        bne cfm_k
        lfs f4, 4(r10)                  # Mode 1: k = dist x tan(fov / 2)
        fmuls f4, f4, f0
cfm_k:
        lfs f5, 0x10(r3)
        fmuls f5, f5, f4                # x
        lfs f6, 0x14(r3)
        fmuls f6, f6, f4                # y
        lfs f13, 0x1C(r3)
        fmuls f13, f13, f4              # s
        stfs f13, 0xC(r10)              # (the request's size)
"""
    for i in range(3):          # P = eye + right x + up y - back dist
        out += """        lfs f7, %d(r12)
        lfs f8, %d(r12)
        fmadds f7, f8, f5, f7
        lfs f8, %d(r12)
        fmadds f7, f8, f6, f7
        lfs f8, %d(r12)
        fnmsubs f7, f8, f0, f7
        stfs f7, %d(r4)
""" % (0x30 + 4 * i, 4 * i, 0x10 + 4 * i, 0x20 + 4 * i, 16 * i + 12)
    out += """        cmpwi r5, 2
        beq cfm_world
"""
    for i in range(3):          # W = C L s, C's columns right, up, back: W[i][j] = R[i] L0j + U[i] L1j + B[i] L2j
        for j in range(3):
            out += """        lfs f7, %d(r12)
        lfs f8, %d(r3)
        fmuls f9, f7, f8
        lfs f7, %d(r12)
        lfs f8, %d(r3)
        fmadds f9, f7, f8, f9
        lfs f7, %d(r12)
        lfs f8, %d(r3)
        fmadds f9, f7, f8, f9
        fmuls f9, f9, f13
        stfs f9, %d(r4)
""" % (4 * i, 0x20 + 4 * j, 0x10 + 4 * i, 0x30 + 4 * j, 0x20 + 4 * i, 0x40 + 4 * j, 16 * i + 4 * j)
    out += """        blr
cfm_world:                              # Mode 2: W = L s (the world's turn)
"""
    for i in range(3):
        for j in range(3):
            out += """        lfs f9, %d(r3)
        fmuls f9, f9, f13
        stfs f9, %d(r4)
""" % (0x20 + 16 * i + 4 * j, 16 * i + 4 * j)
    out += """        blr
"""
    return out


def src(s, hand):
    D = dict(base=CF_INDEX, crc_h=CMD_CRC >> 16, crc_l=CMD_CRC & 0xFFFF, s1b=s['s1_back'], s2b=s['s2_back'],
             fb=s['f_back'], hand_h=hand >> 16, hand_l=hand & 0xFFFF, size=1 + NPARAMS, step=4 * (1 + NPARAMS),
             mgr_ha=(MGR + 0x8000) >> 16, mgr_l=MGR & 0xFFFF, pool=POOL, pool_n=POOL_N, inst=INST,
             tbl_h=CAMTBL >> 16, tbl_l=CAMTBL & 0xFFFF, lookat=LOOKAT_INV, tanf=TANF, rot=ROT, kill=KILL,
             req=WORLD_REQ, req_h=WORLD_REQ >> 16, req_l=WORLD_REQ & 0xFFFF, em=EM_ACC, keep=FLAG_KEEP,
             unslow=FLAG_UNSLOWED, rate1=REQ_RATE1, ntab=NTAB, entry=ENTRY, calc_back=CALC_AT + 4)
    out = """
# --- the command tables' fallbacks --------------------------------------------------------------------------------
cf_lookup:                              # r3 = a CRC no table before has
        lis r12, %(crc_h)d
        ori r12, r12, %(crc_l)d
        cmplw r3, r12
        bne cfl_none
        li r3, %(base)d
        blr
""" % D + LT.replay(s['lk_none'], s['lk_none_word'], s['lk_none'] + 4, 'cfl_none') + """
cf_size1:                               # r3 index -> r0 its size
        cmplwi r3, %(base)d
        bne cfs1_orig
        li r0, %(size)d
        b 0x%(s1b)08X
""" % D + LT.replay(s['s1'], s['s1_word'], s['s1_back'], 'cfs1_orig') + """
cf_size2:                               # r3 index -> r12 its size
        cmplwi r3, %(base)d
        bne cfs2_orig
        li r12, %(size)d
        b 0x%(s2b)08X
""" % D + LT.replay(s['s2'], s['s2_word'], s['s2_back'], 'cfs2_orig') + """
cf_fetch:                               # r7 index -> r0 its handler (r6 free)
        cmplwi r7, %(base)d
        bne cff_orig
        lis r6, %(hand_h)d
        ori r0, r6, %(hand_l)d
        b 0x%(fb)08X
""" % D + ("""
cff_orig:
        b 0x%08X
""" % LT.bdecode(s['f'], s['f_word']) if s['f_word'] >> 26 == 18 else """
cff_orig:
        slwi r6, r7, 2
        lwzx r0, r6, r29
        b 0x%08X
""" % s['f_back'])
    out += """
# --- Effect_Camera(Graphic, X, Y, Z, XRot, YRot, ZRot, Size, Mode, Frames, Flags):
#     (r3 accessor, r5 script state, r6 (+8 execute), r7 parameters) ---------------------------------------------
h_camfx:
        stwu r1, -0x90(r1)
        mflr r0
        stw r0, 0x94(r1)
        stmw r25, 0x70(r1)
        mr r31, r5
        mr r30, r7
        mr r29, r3
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq cf_step
        lis r12, cf_dbg@ha
        lwz r11, cf_dbg@l(r12)          # commands run
        addi r11, r11, 1
        stw r11, cf_dbg@l(r12)
        bl cf_ptr
        cmpwi r0, 0
        bne cf_refused
        lwz r28, %(em)d(r29)            # EffectModule
        mr r3, r28
        bl cf_ptr
        cmpwi r0, 0
        bne cf_refused
        lwz r3, 0(r28)
        bl cf_ptr
        cmpwi r0, 0
        bne cf_refused
        lwz r12, 0x44(r3)               # its world request must be the one known (0x02C29D10)
        lis r11, %(req_h)d
        ori r11, r11, %(req_l)d
        cmplw r12, r11
        bne cf_refused
        bl cf_pick                      # r3: a free entry (else the oldest, its effect faded out)
        mr r27, r3
        li r0, 0
        stw r0, 0(r27)
        lwz r0, 0x20(r30)               # Mode (0 - 2, else 0)
        cmplwi r0, 2
        ble cf_m
        li r0, 0
cf_m:
        stw r0, 4(r27)
        lwz r0, 0x24(r30)               # Frames (negative: 0)
        cmpwi r0, 0
        bge cf_f
        li r0, 0
cf_f:
        stw r0, 8(r27)
        lwz r0, 0x28(r30)               # Flags
        stw r0, 0xC(r27)
        lwz r0, 4(r30)                  # X, Y, Z
        stw r0, 0x10(r27)
        lwz r0, 8(r30)
        stw r0, 0x14(r27)
        lwz r0, 0xC(r30)
        stw r0, 0x18(r27)
        lwz r0, 0x1C(r30)               # Size
        stw r0, 0x1C(r27)
        lis r12, cf_k@ha
        addi r12, r12, cf_k@l
        lfs f0, 0xC(r12)                # pi / 180
        lfs f1, 0x10(r30)
        fmuls f1, f1, f0
        lfs f2, 0x14(r30)
        fmuls f2, f2, f0
        lfs f3, 0x18(r30)
        fmuls f3, f3, f0
        addi r3, r27, 0x20              # L = Rz Ry Rx (the game's own builder)
        bl 0x%(rot)08X
        bl cf_camera
        cmpwi r3, 0
        beq cf_refused                  # no camera (not in a match): nothing started
        mr r3, r27
        addi r4, r1, 0x10               # the matrix (3x4) on the stack
        bl cf_mat
        lfs f0, 0x1C(r1)                # pos = its translation, rot 0
        stfs f0, 0x40(r1)
        lfs f0, 0x2C(r1)
        stfs f0, 0x44(r1)
        lfs f0, 0x3C(r1)
        stfs f0, 0x48(r1)
        li r0, 0
        stw r0, 0x4C(r1)
        stw r0, 0x50(r1)
        stw r0, 0x54(r1)
        lis r12, cf_state@ha
        addi r12, r12, cf_state@l
        lfs f1, 0xC(r12)                # size: the matrix's scale
        mr r3, r28
        lwz r4, 0(r30)                  # Graphic
        addi r5, r1, 0x40
        addi r6, r1, 0x4C
        li r7, 0
        lwz r0, 0xC(r27)
        andi. r0, r0, 1
        beq cf_rq
        lis r7, %(rate1)d               # unslowed: rate 1, not the owner's
cf_rq:
        li r8, -1
        li r9, 1
        li r10, 0
        lwz r12, 0(r28)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl
        lwz r26, 0x14(r28)              # the module's last handle
        cmpwi r26, 0
        beq cf_refused
        mr r3, r26
        bl cf_inst
        mr. r25, r3
        beq cf_refused
        addi r4, r1, 0x10               # its matrix now (no frame at the request's place)
        li r0, 12
        mtctr r0
        li r5, 0
cf_cp:
        add r6, r4, r5
        lwz r0, 0(r6)
        add r6, r25, r5
        stw r0, 0x50(r6)
        addi r5, r5, 4
        bdnz cf_cp
        mr r3, r27
        mr r4, r25
        bl cf_flags
        stw r26, 0(r27)                 # tracked
        lis r12, cf_dbg@ha
        addi r12, r12, cf_dbg@l
        lwz r11, 4(r12)                 # effects started
        addi r11, r11, 1
        stw r11, 4(r12)
        b cf_step
cf_refused:
        lis r12, cf_dbg@ha
        addi r12, r12, cf_dbg@l
        lwz r11, 0x14(r12)              # refused
        addi r11, r11, 1
        stw r11, 0x14(r12)
cf_step:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne cf_ret
        lwz r11, 4(r31)
        addi r11, r11, %(step)d
        stw r11, 4(r31)
        li r3, 2
cf_ret:
        lmw r25, 0x70(r1)
        lwz r0, 0x94(r1)
        mtlr r0
        addi r1, r1, 0x90
        blr

# cf_flags(r3 entry, r4 instance): +0x144 |= keep (| unslowed). r0
cf_flags:
        lwz r0, 0x144(r4)
        ori r0, r0, %(keep)d
        stw r0, 0x144(r4)
        lwz r0, 0xC(r3)
        andi. r0, r0, 1
        beqlr
        lwz r0, 0x144(r4)
        oris r0, r0, %(unslow)d
        stw r0, 0x144(r4)
        blr

# cf_ptr(r3) -> r0 0 when r3 is a word-aligned pointer in 0x10000000-0x8FFFFFFF, else 1. r12
cf_ptr:
        li r0, 1
        andi. r12, r3, 3
        bnelr
        addis r12, r3, -0x1000
        srwi r12, r12, 28
        cmplwi r12, 8
        bgelr
        li r0, 0
        blr

# cf_inst(r3 handle) -> r3 its instance (live: +0 == handle), else 0. r11 r12
cf_inst:
        srwi r11, r3, 24
        cmplwi r11, %(pool_n)d
        bge cfi_no
        lis r12, %(mgr_ha)d
        lwz r12, %(mgr_l)d(r12)
        cmpwi r12, 0
        beq cfi_no
        mulli r11, r11, %(inst)d
        add r12, r12, r11
        addi r12, r12, %(pool)d
        lwz r11, 0(r12)
        cmplw r11, r3
        bne cfi_no
        mr r3, r12
        blr
cfi_no:
        li r3, 0
        blr

# cf_pick() -> r3 an entry: the first free one, else the round robin's next (its effect faded out first)
cf_pick:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        lis r3, cf_tab@ha
        addi r3, r3, cf_tab@l
        li r0, %(ntab)d
        mtctr r0
cfp_free:
        lwz r0, 0(r3)
        cmpwi r0, 0
        beq cfp_ret
        addi r3, r3, %(entry)d
        bdnz cfp_free
        lis r12, cf_rr@ha
        lwz r11, cf_rr@l(r12)
        addi r0, r11, 1
        andi. r0, r0, %(ntab_m)d
        stw r0, cf_rr@l(r12)
        mulli r11, r11, %(entry)d
        lis r3, cf_tab@ha
        addi r3, r3, cf_tab@l
        add r31, r3, r11
        lwz r3, 0(r31)
        li r4, 0
        bl 0x%(kill)08X                 # the oldest one fades out (no longer attached)
        li r0, 0
        stw r0, 0(r31)
        mr r3, r31
cfp_ret:
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# cf_camera() -> r3 1 and cf_inv / cf_state filled (the camera the renderer draws with), else 0
cf_camera:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        stw r30, 0x18(r1)
        lis r31, cf_state@ha
        addi r31, r31, cf_state@l
        li r0, 0
        stw r0, 0(r31)
        lis r3, %(tbl_h)d
        ori r3, r3, %(tbl_l)d
        lwz r4, 0xC(r3)                 # entry 0's current source (0 - 2; -1 none)
        cmplwi r4, 2
        bgt cfc_no
        slwi r4, r4, 2
        add r4, r4, r3
        lwz r30, 0x14(r4)
        mr r3, r30
        bl cf_ptr
        cmpwi r0, 0
        bne cfc_no
        lfs f0, 8(r30)                  # near
        stfs f0, 8(r31)
        lis r3, cf_view@ha
        addi r3, r3, cf_view@l
        lis r4, cf_inv@ha
        addi r4, r4, cf_inv@l
        addi r5, r30, 0x10              # eye, target, up
        bl 0x%(lookat)08X
        lfs f1, 0(r30)                  # vertical FOV (radians)
        lis r12, cf_k@ha
        addi r12, r12, cf_k@l
        lfs f0, 0x10(r12)               # 0.5
        fmuls f1, f1, f0
        bl 0x%(tanf)08X
        stfs f1, 4(r31)
        li r0, 1
        stw r0, 0(r31)
        li r3, 1
        b cfc_ret
cfc_no:
        li r3, 0
cfc_ret:
        lwz r30, 0x18(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# --- the calc pass (0x032EFD04, r3 the manager): every tracked effect, then the pass --------------------------
cf_calc:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r26, 0x28(r1)
        mr r31, r3
        lis r30, cf_tab@ha
        addi r30, r30, cf_tab@l
        li r29, %(ntab)d
        li r28, 0                       # camera: 0 not read yet, 1 there, 2 none
cfu_loop:
        lwz r27, 0(r30)
        cmpwi r27, 0
        beq cfu_next
        mr r3, r27
        bl cf_inst
        mr. r26, r3
        beq cfu_drop                    # ended (or killed): no longer tracked
        lwz r11, 8(r30)                 # Frames (addi rD, r0 would read 0: r11)
        cmpwi r11, 0
        beq cfu_live
        addi r11, r11, -1
        stw r11, 8(r30)
        cmpwi r11, 0
        bne cfu_live
        mr r3, r27                      # its time is up: fade it out
        li r4, 0
        bl 0x%(kill)08X
        lis r12, cf_dbg@ha
        addi r12, r12, cf_dbg@l
        lwz r11, 0xC(r12)               # ended by Frames
        addi r11, r11, 1
        stw r11, 0xC(r12)               # (Frames is 0 now: it stays attached while it fades, until it ends)
cfu_live:
        cmpwi r28, 0
        bne cfu_cam
        bl cf_camera
        li r28, 2
        cmpwi r3, 0
        beq cfu_cam
        li r28, 1
cfu_cam:
        cmpwi r28, 1
        bne cfu_next                    # no camera this frame: it stays where it is
        mr r3, r30
        addi r4, r26, 0x50
        bl cf_mat
        mr r3, r30
        mr r4, r26
        bl cf_flags
        lis r12, cf_dbg@ha
        addi r12, r12, cf_dbg@l
        lwz r11, 8(r12)                 # matrices set
        addi r11, r11, 1
        stw r11, 8(r12)
        b cfu_next
cfu_drop:
        lis r12, cf_dbg@ha
        addi r12, r12, cf_dbg@l
        lwz r11, 0x10(r12)              # ended on their own
        addi r11, r11, 1
        stw r11, 0x10(r12)
cfu_free:
        li r0, 0
        stw r0, 0(r30)
cfu_next:
        addi r30, r30, %(entry)d
        addi r29, r29, -1
        cmpwi r29, 0
        bne cfu_loop
        mr r3, r31
        lmw r26, 0x28(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
""" % dict(D, ntab_m=NTAB - 1)
    if s['calc_word'] >> 26 == 18:
        out += """        b 0x%08X
""" % LT.bdecode(CALC_AT, s['calc_word'])
    else:
        out += """        .word 0x%08X
        b 0x%08X
""" % (s['calc_word'], CALC_AT + 4)
    out += _mat_src()
    out += """
cf_k:                                   # 0, 1, 20, pi / 180, 0.5
        .float 0
        .float 1
        .float 20
        .float 0.017453292519943295
        .float 0.5
cf_dbg:                                 # commands run, effects started, matrices set, ended by Frames, ended on
        .word 0                         # their own, refused
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
cf_rr:
        .word 0
cf_state:                               # camera there, tan(fov / 2), near, the last matrix's scale
        .word 0
        .word 0
        .word 0
        .word 0
cf_view:
""" + '        .word 0\n' * 16 + """cf_inv:
""" + '        .word 0\n' * 16 + """cf_tab:
"""
    return out


def build(orig):
    s = find(orig)
    hand = 0
    for _p in range(2):
        a = Asm(CAVE)
        a.asm(src(s, hand))
        hand = a.addr('h_camfx')
    words = a.words()
    tab = a.addr('cf_tab')
    end = tab + NTAB * ENTRY
    assert end <= LIMIT, 'cave too big: 0x%08X' % end
    for x in range(CAVE, LIMIT, 4):
        assert orig(x) == 0, 'cave word 0x%08X not free' % x
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    out[s['lk_none']] = LT.branch(s['lk_none'], a.addr('cf_lookup'))
    out[s['s1']] = LT.branch(s['s1'], a.addr('cf_size1'))
    out[s['s2']] = LT.branch(s['s2'], a.addr('cf_size2'))
    out[s['f']] = LT.branch(s['f'], a.addr('cf_fetch'))
    out[CALC_AT] = LT.branch(CALC_AT, a.addr('cf_calc'))
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
    """Effect_Camera's entry in tools/Sm4shCommand/param_labels.json (apply_param_labels.py then puts it in Events.cfg
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
    """the executable has this cave (Effect_Camera's CRC in cf_lookup) - for port_check"""
    hi, lo = 0x3D800000 | (CMD_CRC >> 16), 0x618C0000 | (CMD_CRC & 0xFFFF)
    try:
        return any(img_w(x) == hi and img_w(x + 4) == lo for x in range(CAVE, CAVE + 0x40, 4))
    except Exception:              # noqa: BLE001
        return False


def matrix(eye, target, up, fov, near, mode, x, y, z, rot_deg, size):
    """the 3x4 matrix the cave gives an effect (Python reference, for the test and the docs): rows, translation in
    column 3"""
    import math

    def sub(a, b): return [a[i] - b[i] for i in range(3)]

    def cross(a, b): return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]

    def norm(a):
        n = math.sqrt(sum(v * v for v in a))
        return [v / n for v in a]
    back = norm(sub(eye, target))
    right = norm(cross(up, back))
    upv = cross(back, right)
    dist = z
    if mode == 1 and dist <= 0:
        dist = 20.0
    dist = max(dist, near + 1)
    k = dist * math.tan(fov / 2) if mode == 1 else 1.0
    px, py, s = x * k, y * k, size * k
    p = [eye[i] + right[i] * px + upv[i] * py - back[i] * dist for i in range(3)]
    ax, ay, az = [math.radians(v) for v in rot_deg]
    cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    rx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]

    def mm(a, b): return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    L = mm(rz, mm(ry, rx))
    if mode == 2:
        W = L
    else:
        C = [[right[i], upv[i], back[i]] for i in range(3)]
        W = mm(C, L)
    return [[W[i][0] * s, W[i][1] * s, W[i][2] * s, p[i]] for i in range(3)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', help='the executable to patch (exe_v46y_hold or later)')
    p.add_argument('--labels', help='update this param_labels.json with Effect_Camera')
    args = p.parse_args()
    if args.labels:
        labels(args.labels)
        return
    if not args.rpx:
        p.error('--rpx or --labels')
    words, lab, _s = build(rpx_reader(args.rpx))
    print(' '.join(['textregion:0x%X' % TEXT_REGION, 'grow:0x%08X' % LIMIT] +
                   ['0x%08X=0x%08X' % kv for kv in sorted(words.items())]))
    sys.stderr.write('camera effects: %d words, Effect_Camera index %d (0x%08X), h_camfx 0x%08X, cf_calc 0x%08X, '
                     'cf_tab 0x%08X-0x%08X\n' % (len(words), CF_INDEX, CMD_CRC, lab['h_camfx'], lab['cf_calc'],
                                                 lab['cf_tab'], lab['cf_tab'] + NTAB * ENTRY))


if __name__ == '__main__':
    main()
