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
  UPDATE  0x032EFD7C  bl 0x0334E0C8        (v3 / v4) -> cf_upd: a camera effect's particle emitter sets get its matrix
                                           from eft's SetMtx before and after the game's update (the game gives them one
                                           only when its update rebuilt it, which flag 0x8000 skips: v1-v3's particles
                                           stayed where they started), its model too
  (v5) the game's 2.5D depth squash off for camera effects: cf_flags clears the instance's +0x1A3 (the game's eft
       particle callback 0x033508C0 moved every CPU particle's Z to 0 + Z x 0.07: v4's dizzy stars, 20 units in front
       of the camera, were drawn near the stage, around the screen's centre) and cf_eftset gives each emitter set
       emp1.z 1.0 (+0x2CC, eft's default: the vertex programs' billboard on, not the squash's 0.07)
  SFZ     0x04BD4334 / 0x04BD4268          (v3) Stage_Freeze's stop / resume: On 1 the update only (no white
                                           screen, confirmed in game), 2 the game's full stop, 3 the Final Smash stop
  --diag: TEST ONLY OSReport lines (S4CS / S4CF / S4CM / S4CE per effect, S4CC / S4CV / S4CN the camera, S4SF).
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
ENTRY = 0x60                    # (v4: +0x50 the calc passes it has been through, for the diag)

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
# camera_effects v3 ---------------------------------------------------------------------------------------------------
UPD_AT = 0x032EFD7C             # the calc pass's bl 0x0334E0C8 (the instance update, then eft's matrix): -> cf_upd
UPDATE = 0x0334E0C8
SETMTX = 0x032FF744             # (inst + 0x20, &3x4): the emitter set's matrix (eft set +0x350, its scale +0x7AC)
SETMTX_SIG = (0x7C0802A6, 0x7C2B0B78, 0x9421FF60)
VALID = 0x032FF640              # (inst + 0x20) -> 1 while its model is there (efc entries with a model)
EFT_SETMTX = 0x04A4AFB8         # (v4) eft EmitterSet::SetMtx(set, &3x4): set +0x1E8 SRT, +0x218 RT, +0x248 scales
EFT_SETMTX_SIG = (0x9421FF90, 0xDB610020, 0x7C0802A6)
GATE_SIG = {0x0334EEB0: 0x2C1A0000, 0x0334EEB4: 0x41820010, 0x0334EEBC: 0x38810010, 0x0334EEC0: 0x496FC0F9,
            0x0334E264: 0x55260421, 0x0334E268: 0x40820024, 0x0334E284: 0x3B400001}   # the game's r26 gate
VALID_SIG = (0x81830000, 0x2C0CFFFF)
# (v5) the game's 2.5D depth squash ("depth flatten"): an instance whose request passed r9 = 1 (the world request
# does) gets byte +0x1A3 (0x0334DBAC). Then: its emitter set's +0x2CC = 0.07 at creation (0x0334DC70: eft's emp1.z,
# below 1 the vertex programs skip the billboard matrix), the plane +0x11C = 0 (0x0334F2D4), its model's depth x 0.07
# (0x0334EAAC), and the game's eft particle callbacks (registered at 0x032EF93C-0x032EF9B0 into the system's +0xA68
# table, run by eft's CPU particle calc 0x04A65480 on every CPU particle after its place: 0x04A65624 / 0x04A65680)
# move each CPU particle's world Z (p + 0x40) to plane + (z - plane) x 0.07. Harmless at the stage (z about 0); a
# camera effect 20 units in front of a camera at z 200 had its CPU particles (the dizzy stars) squashed onto the stage,
# near the screen's centre (camera_effects v4's clips). GPU particles (flag 0x00800000) never run the callback.
FLAT = 0x1A3                    # instance byte: the squash on
SET_EMP1Z = 0x2CC               # eft emitter set: emp1.z (1.0 eft's default, 0x04A55D84; 0.07 squashed)
FLAT_SIG = {0x0334DBAC: 0x9BD701A3, 0x0334DC6C: 0xC0046028, 0x0334DC70: 0xD01002CC,
            0x033508CC: 0x880B01A3, 0x033508DC: 0xC1AB011C, 0x033508E0: 0xC18C0040, 0x033508EC: 0xC00B6028,
            0x033508F4: 0xD00C0040, 0x10196028: 0x3D8F5C29,
            0x032EF9A8: 0x38A508C0, 0x032EF9AC: 0x38800000, 0x04A5856C: 0x90AC0A68,
            0x04A65DF0: 0xC16702CC}
CAMMGR = 0x10352470             # [CAMMGR] the camera manager; +0x780 its snapshot block (entry 0 slot 0's source)
CAMMGR_SIG = {0x02D29634: 0x3C601035, 0x02D29638: 0x80632470}
CAMBLK = 0x780
# Stage_Freeze (exe_v46n's ts code in exe_v46y_hold): its two calls of the stage manager's stop
STAGE_STOP = 0x0316505C         # (manager, on): +0xD0 = on, and the stage told (0x031427D0: its objects' models and
                                # effects paused / hidden, stage vt +0x214): the Final Smash / pause stop
SFZ_ON_AT, SFZ_OFF_AT = 0x04BD4334, 0x04BD4268    # h_sfreeze's bl STAGE_STOP (r4 1), ts_stage_off's (r4 0)
SFZ_SIG = {0x04BD4304: 0x801E0000, 0x04BD4330: 0x38800001, 0x04BD4264: 0x38800000}
FX_VIS, FX_PAUSE = 0x0334CA64, 0x0334CA30   # (key, mask, on[, 0]): what the Final Smashes' stop (0x02772658) also does
FS_KEY, FS_MASK = 0x01080000, 0xFF080000
FX_SIG = {FX_VIS: 0x7C6B1B78, FX_PAUSE: 0x7C6C1B78, 0x027726A0: 0x3C600108, 0x0277269C: 0x3C80FF08}
SFZ_LIGHT, SFZ_FULL, SFZ_FS = 1, 2, 3
DIAG_EVERY = 30                 # the diag logs an effect's first 30 frames, then every 30th

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


def _bl_target(at, w):
    """the target of a relative bl at at (None if w isn't one)"""
    if w >> 26 != 18 or w & 3 != 1:
        return None
    off = w & 0x3FFFFFC
    return at + (off - 0x4000000 if off & 0x2000000 else off)


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
    # v3: the instance update's call, eft's matrix setter, the camera manager, Stage_Freeze's stop calls
    assert _bl_target(UPD_AT, orig(UPD_AT)) == UPDATE, 'update call 0x%08X: 0x%08X' % (UPD_AT, orig(UPD_AT))
    for base, sig, what in ((SETMTX, SETMTX_SIG, 'model matrix'), (VALID, VALID_SIG, 'model valid'),
                            (EFT_SETMTX, EFT_SETMTX_SIG, 'eft SetMtx')):
        for i, want in enumerate(sig):
            assert orig(base + 4 * i) == want, '%s 0x%08X: 0x%08X' % (what, base + 4 * i, orig(base + 4 * i))
    for at, want in list(CAMMGR_SIG.items()) + list(SFZ_SIG.items()) + list(FX_SIG.items()) + list(GATE_SIG.items()) + \
            list(FLAT_SIG.items()):
        assert orig(at) == want, '0x%08X: 0x%08X, not 0x%08X' % (at, orig(at), want)
    for at in (SFZ_ON_AT, SFZ_OFF_AT):
        w = orig(at)
        assert _bl_target(at, w) == STAGE_STOP, \
            'Stage_Freeze stop call 0x%08X: 0x%08X (want bl 0x%08X: exe_v46n\'s ts code)' % (at, w, STAGE_STOP)
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


DIAG_FMTS = [
    ('s_cc', 'S4CC n=%d cur=%d nxt=%d src=%08X cam=%d mgrblk=%08X tan=%08X\n'),
    ('s_cv', 'S4CV eye=%08X %08X %08X tgt=%08X %08X %08X\n'),
    ('s_cf', 'S4CN fov=%08X near=%08X far=%08X up=%08X %08X %08X\n'),
    ('s_ef', 'S4CF k=%d h=%08X i=%08X fl=%08X set=%08X fo=%08X b=%08X\n'),
    ('s_em', 'S4CM t=%08X %08X %08X x=%08X %08X %08X\n'),
    ('s_ee', 'S4CE em=%d d=%08X t=%08X %08X %08X x=%08X s=%08X\n'),
    ('s_cs', 'S4CS id=%08X h=%08X i=%08X why=%03X x=%08X y=%08X z=%08X\n'),
    ('s_sf', 'S4SF n=%d on=%d mode=%d mgr=%08X d0=%d\n'),
]


def _words(s):
    b = s.encode() + b'\0'
    b += b'\0' * (-len(b) % 4)
    return ''.join('        .word 0x%08X\n' % struct.unpack_from('>I', b, i)[0] for i in range(0, len(b), 4))


def _diag_data():
    out = 'cf_dg:                                  # diag: effects started seen, frames since, log now\n' + \
          '        .word 0\n' * 3
    for lab, fmt in DIAG_FMTS:
        out += '%s:\n' % lab + _words(fmt)
    return out


def _v3_src(diag):
    """camera_effects v3: cf_upd (eft gets the camera matrix after the game's instance update), Stage_Freeze's modes
    (cf_sfz_on / cf_sfz_off) and, with diag, the OSReport lines (cf_dcam, cf_dlog, cf_dsfz)"""
    import diag_godfist_cave as G
    D = dict(update=UPDATE, setmtx=SETMTX, valid=VALID, eftset=EFT_SETMTX, emp1z=SET_EMP1Z, flat=FLAT, ntab=NTAB,
             entry=ENTRY, stop=STAGE_STOP, vis=FX_VIS, pause=FX_PAUSE, kh=FS_KEY >> 16, mh=FS_MASK >> 16, full=SFZ_FULL, fs=SFZ_FS, every=DIAG_EVERY,
             vh=G.OSREPORT_VENEER >> 16, vl=G.OSREPORT_VENEER & 0xFFFF, crclr=G.CRCLR_CR1EQ,
             cmh=(CAMMGR + 0x8000) >> 16, cml=CAMMGR & 0xFFFF, cblk=CAMBLK, tbl_h=CAMTBL >> 16, tbl_l=CAMTBL & 0xFFFF)
    rep = """
        lis r12, 0x%(vh)X
        ori r12, r12, 0x%(vl)X
        mtctr r12
        .word 0x%(crclr)08X
        bctrl""" % D
    out = """
# --- (v4) the calc pass's instance update (r3 an instance). The game gives a particle emitter set a new matrix only
#     when its update rebuilt or turned it this frame (0x0334EEB0: cmpwi r26, 0 -> eft's SetMtx 0x04A4AFB8), and the
#     cave's flag 0x8000 skips the rebuild: v1-v3's particles kept the matrix they were created with (the request's
#     place, turn 0), and +0x20 (0x032FF744, which v3 gave the matrix again) is the effect's MODEL, absent from
#     particle-only effects. So for a camera effect: its emitter sets get +0x50 from eft's own setter before the update
#     (the frame's emission uses it) and again after it (the draw), its model too ----------------------------------
cf_upd:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        stw r30, 0x18(r1)
        stw r29, 0x14(r1)
        mr r31, r3
        bl cf_track                     # r3: its entry (a camera effect, flag 0x8000), else 0
        mr. r29, r3
        beq cfd_game
        mr r3, r31
        bl cf_eftset
cfd_game:
        mr r3, r31
        bl 0x%(update)08X
        cmpwi r29, 0
        beq cfd_out
        lwz r0, 0(r31)                  # still the same effect (not ended by the update)
        lwz r11, 0(r29)
        cmplw r0, r11
        bne cfd_out
        mr r3, r31
        bl cf_eftset
        lbz r0, 0x199(r31)              # its model (efc entries with one): +0x20
        cmpwi r0, 0
        beq cfd_log
        addi r3, r31, 0x20
        bl 0x%(valid)08X
        cmpwi r3, 0
        beq cfd_log
        addi r3, r31, 0x20
        addi r4, r31, 0x50
        bl 0x%(setmtx)08X
cfd_log:
        lwz r11, 0x50(r29)              # calc passes this effect has been through
        addi r0, r11, 1
        stw r0, 0x50(r29)
        mr r3, r31
        mr r4, r11
        bl cf_dlog                      # (diag build: S4CF / S4CM / S4CE; else a blr)
cfd_out:
        lwz r29, 0x14(r1)
        lwz r30, 0x18(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# cf_track(r3 instance) -> r3 its cf_tab entry when it is a tracked camera effect with flag 0x8000, else 0. r0 r11 r12
cf_track:
        lwz r12, 0(r3)
        cmpwi r12, 0
        beq cft_no
        lwz r0, 0x144(r3)
        andi. r0, r0, 0x8000
        beq cft_no
        lis r11, cf_tab@ha
        addi r11, r11, cf_tab@l
        li r0, %(ntab)d
        mtctr r0
cft_find:
        lwz r0, 0(r11)
        cmplw r0, r12
        beq cft_yes
        addi r11, r11, %(entry)d
        bdnz cft_find
cft_no:
        li r3, 0
        blr
cft_yes:
        mr r3, r11
        blr

# cf_eftset(r3 instance): eft's SetMtx(set, inst + 0x50) on its emitter set (+0x12C, alive: +0x19A, the set's +0x1D0 =
# +0x130, +0x1DC > 0) and its extra ones (+0x158: {set, id} x +0x170), as the update checks them (0x0334EE60 /
# 0x0334EF6C). The count in cf_dbg +0x1C
cf_eftset:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        stw r30, 0x18(r1)
        mr r31, r3
        lbz r0, 0x19A(r31)
        cmpwi r0, 0
        beq ces_more
        lwz r3, 0x12C(r31)
        lwz r4, 0x130(r31)
        bl ces_one
ces_more:
        li r30, 0
ces_loop:
        lwz r0, 0x170(r31)
        cmplw r30, r0
        bge ces_out
        slwi r12, r30, 3
        add r12, r12, r31
        lwz r3, 0x158(r12)
        lwz r4, 0x15C(r12)
        bl ces_one
        addi r30, r30, 1
        cmpwi r30, 3                    # (the array holds 3: +0x170 follows it)
        blt ces_loop
ces_out:
        lwz r30, 0x18(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
ces_one:                                # (r3 set, r4 its id; r31 the instance) leaf until the tail call
        andi. r0, r3, 3
        bnelr
        addis r12, r3, -0x1000
        srwi r12, r12, 28
        cmplwi r12, 8
        bgelr
        lwz r0, 0x1D0(r3)
        cmplw r0, r4
        bnelr
        lwz r0, 0x1DC(r3)
        cmpwi r0, 0
        blelr
        lis r12, cf_dbg@ha
        addi r12, r12, cf_dbg@l
        lwz r11, 0x1C(r12)              # matrices given to eft's sets
        addi r11, r11, 1
        stw r11, 0x1C(r12)
        lis r0, 0x3F80                  # (v5) emp1.z 1.0: eft's own billboards (the squash's 0.07 off)
        stw r0, %(emp1z)d(r3)
        addi r4, r31, 0x50
        b 0x%(eftset)08X

# --- (v3) Stage_Freeze's stop (h_sfreeze's bl, r3 the stage manager, r4 1, r30 its parameters): On 1 (and anything
#     but 2 / 3) only the stage's update (+0xD0), the stage not told (no 0x031427D0: the Final Smash / pause stop that
#     brought the white screen); 2 the game's stop as before; 3 the game's stop and what the Final Smashes do with it
#     (0x02772658: the effects of key 0x01080000 / mask 0xFF080000 hidden and paused) ----------------------------------
cf_sfz_on:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        stw r30, 0x18(r1)
        mr r31, r3
        lwz r30, 0(r30)                 # On
        cmpwi r30, %(full)d
        beq cfz_mode
        cmpwi r30, %(fs)d
        beq cfz_mode
        li r30, 1
cfz_mode:
        lis r12, cf_sfz@ha
        stw r30, cf_sfz@l(r12)
        cmpwi r30, 1
        bne cfz_game
        li r0, 1
        stb r0, 0xD0(r31)               # the update skipped (the stage manager's own flag), nothing else
        b cfz_done
cfz_game:
        mr r3, r31
        li r4, 1
        bl 0x%(stop)08X
        cmpwi r30, %(fs)d
        bne cfz_done
        lis r3, 0x%(kh)X
        lis r4, 0x%(mh)X
        li r5, 0                        # hidden
        li r6, 0
        bl 0x%(vis)08X
        lis r3, 0x%(kh)X
        lis r4, 0x%(mh)X
        li r5, 1                        # paused
        bl 0x%(pause)08X
cfz_done:
        li r4, 1
        mr r5, r30
        mr r6, r31
        bl cf_dsfz
        lwz r30, 0x18(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# --- (v3) Stage_Freeze's resume (ts_stage_off's bl, r3 the manager, r4 0): the game's resume (after a light stop the
#     stage was never told: 0x031427D0 sees it active and does nothing; +0xD0 cleared); mode 3 shows the effects again
cf_sfz_off:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        stw r30, 0x18(r1)
        mr r31, r3
        lis r12, cf_sfz@ha
        lwz r30, cf_sfz@l(r12)
        li r0, 0
        stw r0, cf_sfz@l(r12)
        li r4, 0
        bl 0x%(stop)08X
        cmpwi r30, %(fs)d
        bne cfo_done
        lis r3, 0x%(kh)X
        lis r4, 0x%(mh)X
        li r5, 1
        li r6, 0
        bl 0x%(vis)08X
        lis r3, 0x%(kh)X
        lis r4, 0x%(mh)X
        li r5, 0
        bl 0x%(pause)08X
cfo_done:
        li r4, 0
        mr r5, r30
        mr r6, r31
        bl cf_dsfz
        lwz r30, 0x18(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
""" % D
    if not diag:
        return out + """
cf_dcam:
cf_dlog:
cf_dsfz:
cf_dspawn:
        blr
"""
    out += """
# --- diag: S4CC / S4CV / S4CN, the camera of this calc pass (an effect's first %(every)d frames, then every %(every)dth) --
cf_dcam:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r28, 0x20(r1)
        lis r31, cf_dg@ha
        addi r31, r31, cf_dg@l
        li r0, 0
        stw r0, 8(r31)
        lis r12, cf_dbg@ha
        addi r12, r12, cf_dbg@l
        lwz r11, 4(r12)                 # effects started
        lwz r10, 0(r31)
        cmpw r11, r10
        beq cdc_any
        stw r11, 0(r31)
        li r0, 0
        stw r0, 4(r31)
cdc_any:
        lis r9, cf_tab@ha
        addi r9, r9, cf_tab@l
        li r0, %(ntab)d
        mtctr r0
cdc_scan:
        lwz r0, 0(r9)
        cmpwi r0, 0
        bne cdc_some
        addi r9, r9, %(entry)d
        bdnz cdc_scan
        b cdc_out
cdc_some:
        lwz r10, 4(r31)
        addi r0, r10, 1
        stw r0, 4(r31)
        cmpwi r10, %(every)d
        blt cdc_log
        li r9, %(every)d
        divwu r8, r10, r9
        mullw r8, r8, r9
        cmpw r8, r10
        bne cdc_out
cdc_log:
        li r0, 1
        stw r0, 8(r31)
        lis r30, cf_state@ha
        addi r30, r30, cf_state@l
        lis r29, %(tbl_h)d
        ori r29, r29, %(tbl_l)d
        lis r3, s_cc@ha
        addi r3, r3, s_cc@l
        lis r12, cf_dbg@ha
        addi r12, r12, cf_dbg@l
        lwz r4, 0x18(r12)
        lwz r5, 0xC(r29)
        lwz r6, 0x10(r29)
        lwz r7, 0x10(r30)
        lwz r8, 0(r30)
        lis r9, %(cmh)d
        lwz r9, %(cml)d(r9)
        addi r9, r9, %(cblk)d
        lwz r10, 4(r30)
""" % D + rep + """
        lwz r28, 0x10(r30)              # the source read
        mr r3, r28
        bl cf_ptr
        cmpwi r0, 0
        bne cdc_out
        lis r3, s_cv@ha
        addi r3, r3, s_cv@l
        lwz r4, 0x10(r28)
        lwz r5, 0x14(r28)
        lwz r6, 0x18(r28)
        lwz r7, 0x1C(r28)
        lwz r8, 0x20(r28)
        lwz r9, 0x24(r28)
""" + rep + """
        lis r3, s_cf@ha
        addi r3, r3, s_cf@l
        lwz r4, 0(r28)
        lwz r5, 8(r28)
        lwz r6, 0xC(r28)
        lwz r7, 0x28(r28)
        lwz r8, 0x2C(r28)
        lwz r9, 0x30(r28)
""" + rep + """
cdc_out:
        lmw r28, 0x20(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- diag: S4CF / S4CM / S4CE (r3 the instance, r4 the calc passes it has been through: its first %(every)d, then
#     every %(every)dth): the instance, the matrix it holds (+0x50) and the one eft's emitter set holds (+0x12C: +0x1E8,
#     rows, translation in column 3) after cf_upd ---------------------------------------------------------------------
cf_dlog:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r28, 0x20(r1)
        mr r31, r3
        mr r29, r4
        cmpwi r29, %(every)d
        blt cdl_go
        li r9, %(every)d
        divwu r8, r29, r9
        mullw r8, r8, r9
        cmpw r8, r29
        bne cdl_out
cdl_go:
        lbz r10, 0x199(r31)
        slwi r10, r10, 8
        lbz r0, 0x19A(r31)
        or r10, r10, r0
        slwi r10, r10, 8
        lbz r0, 0x19E(r31)
        or r10, r10, r0
        slwi r10, r10, 8
        lbz r0, 0x1A3(r31)
        or r10, r10, r0
        lis r3, s_ef@ha
        addi r3, r3, s_ef@l
        mr r4, r29
        lwz r5, 0(r31)
        mr r6, r31
        lwz r7, 0x144(r31)
        lwz r8, 0x12C(r31)
        lwz r9, 0x34(r31)
""" % D + rep + """
        lis r3, s_em@ha
        addi r3, r3, s_em@l
        lwz r4, 0x5C(r31)
        lwz r5, 0x6C(r31)
        lwz r6, 0x7C(r31)
        lwz r7, 0x50(r31)
        lwz r8, 0x60(r31)
        lwz r9, 0x70(r31)
""" + rep + """
        lwz r28, 0x12C(r31)             # eft's emitter set
        mr r3, r28
        bl cf_ptr
        cmpwi r0, 0
        bne cdl_out
        lis r3, s_ee@ha
        addi r3, r3, s_ee@l
        lwz r4, 0x1DC(r28)
        lwz r5, 0x2CC(r28)              # (v5) emp1.z: 1.0, or the squash's 0.07
        lwz r6, 0x1F4(r28)              # (v5) its SRT is at +0x1E8 (v4 read one word early): translation
        lwz r7, 0x204(r28)
        lwz r8, 0x214(r28)
        lwz r9, 0x1E8(r28)              # m00
        lwz r10, 0x248(r28)             # the X axis' length (SetMtx's scale)
""" + rep + """
cdl_out:
        lmw r28, 0x20(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- diag: S4CS (r3 the parameters, r4 the handle or 0, r5 the instance or 0, r6 0 started / 1 not): every
#     Effect_Camera, with what it was given -----------------------------------------------------------------------------
cf_dspawn:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        mr r12, r3
        lwz r0, 0x20(r12)               # Mode
        slwi r7, r6, 8
        or r7, r7, r0
        mr r6, r5
        mr r5, r4
        lwz r4, 0(r12)                  # Graphic
        lwz r8, 4(r12)                  # X, Y, Z
        lwz r9, 8(r12)
        lwz r10, 0xC(r12)
        lis r3, s_cs@ha
        addi r3, r3, s_cs@l
""" + rep + """
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# --- diag: S4SF (r4 on, r5 mode, r6 the stage manager) -----------------------------------------------------------
cf_dsfz:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        mr r7, r6
        mr r6, r5
        mr r5, r4
        li r8, -1
        cmpwi r7, 0
        beq cds_go
        lbz r8, 0xD0(r7)
cds_go:
        lis r3, s_sf@ha
        addi r3, r3, s_sf@l
        lis r12, cf_dbg@ha
        addi r12, r12, cf_dbg@l
        lwz r4, 0x18(r12)
""" + rep + """
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
"""
    return out


def src(s, hand, diag=False):
    D = dict(base=CF_INDEX, crc_h=CMD_CRC >> 16, crc_l=CMD_CRC & 0xFFFF, s1b=s['s1_back'], s2b=s['s2_back'],
             fb=s['f_back'], hand_h=hand >> 16, hand_l=hand & 0xFFFF, size=1 + NPARAMS, step=4 * (1 + NPARAMS),
             mgr_ha=(MGR + 0x8000) >> 16, mgr_l=MGR & 0xFFFF, pool=POOL, pool_n=POOL_N, inst=INST,
             tbl_h=CAMTBL >> 16, tbl_l=CAMTBL & 0xFFFF, lookat=LOOKAT_INV, tanf=TANF, rot=ROT, kill=KILL,
             req=WORLD_REQ, req_h=WORLD_REQ >> 16, req_l=WORLD_REQ & 0xFFFF, em=EM_ACC, keep=FLAG_KEEP,
             unslow=FLAG_UNSLOWED, rate1=REQ_RATE1, ntab=NTAB, entry=ENTRY, calc_back=CALC_AT + 4,
             cmh=(CAMMGR + 0x8000) >> 16, cml=CAMMGR & 0xFFFF if CAMMGR & 0x8000 == 0 else (CAMMGR & 0xFFFF) - 0x10000,
             cblk=CAMBLK, flat=FLAT, emp1z=SET_EMP1Z)
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
        li r26, 0                       # (v4 diag: no handle, no instance yet)
        li r25, 0
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
        li r0, 0
        stw r0, 0x50(r27)
        mr r3, r30
        mr r4, r26
        mr r5, r25
        li r6, 0
        bl cf_dspawn                    # (diag build: S4CS; else a blr)
        lis r12, cf_dbg@ha
        addi r12, r12, cf_dbg@l
        lwz r11, 4(r12)                 # effects started
        addi r11, r11, 1
        stw r11, 4(r12)
        b cf_step
cf_refused:
        mr r3, r30
        mr r4, r26
        mr r5, r25
        li r6, 1
        bl cf_dspawn
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

# cf_flags(r3 entry, r4 instance): +0x144 |= keep (| unslowed); (v3) its position / scale fields mirror the matrix
# (+0xC8 = the translation, +0xB0 = the scale: what the game reads of an instance besides +0x50); (v5) the game's
# 2.5D depth squash off (+0x1A3 = 0: its CPU particles' Z was squashed x 0.07 toward z 0). r0 r12 f0
cf_flags:
        li r0, 0
        stb r0, %(flat)d(r4)
        lfs f0, 0x5C(r4)
        stfs f0, 0xC8(r4)
        lfs f0, 0x6C(r4)
        stfs f0, 0xCC(r4)
        lfs f0, 0x7C(r4)
        stfs f0, 0xD0(r4)
        lis r12, cf_state@ha
        addi r12, r12, cf_state@l
        lfs f0, 0xC(r12)
        stfs f0, 0xB0(r4)
        stfs f0, 0xB4(r4)
        stfs f0, 0xB8(r4)
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
        bgt cfc_mgr
        slwi r4, r4, 2
        add r4, r4, r3
        lwz r30, 0x14(r4)
        mr r3, r30
        bl cf_ptr
        cmpwi r0, 0
        beq cfc_src
cfc_mgr:                                # (v3) none: the camera manager's own snapshot block
        lis r3, %(cmh)d
        lwz r3, %(cml)d(r3)
        bl cf_ptr
        cmpwi r0, 0
        bne cfc_no
        addi r30, r3, %(cblk)d
cfc_src:
        stw r30, 0x10(r31)              # (the source read, for the diag)
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
        lis r12, cf_dbg@ha
        addi r12, r12, cf_dbg@l
        lwz r11, 0x18(r12)              # (v3) calc passes (the diag's frame number)
        addi r11, r11, 1
        stw r11, 0x18(r12)
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
        bl cf_dcam                      # (v3 diag build: the camera this frame; else a blr)
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
    out += _v3_src(diag)
    out += _mat_src()
    out += """
cf_k:                                   # 0, 1, 20, pi / 180, 0.5
        .float 0
        .float 1
        .float 20
        .float 0.017453292519943295
        .float 0.5
cf_dbg:                                 # commands run, effects started, matrices set, ended by Frames, ended on
        .word 0                         # their own, refused, (v3) calc passes, matrices given to eft after the update
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
cf_rr:
        .word 0
cf_sfz:                                 # (v3) the Stage_Freeze mode in force (0 none, 1 light, 2 full, 3 Final Smash)
        .word 0
cf_state:                               # camera there, tan(fov / 2), near, the last matrix's scale, the source read
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
""" + (_diag_data() if diag else '') + """
cf_view:
""" + '        .word 0\n' * 16 + """cf_inv:
""" + '        .word 0\n' * 16 + """cf_tab:
"""
    return out


def build(orig, diag=False):
    s = find(orig)
    hand = 0
    for _p in range(2):
        a = Asm(CAVE)
        a.asm(src(s, hand, diag))
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
    out[UPD_AT] = LT.branch(UPD_AT, a.addr('cf_upd')) | 1
    out[SFZ_ON_AT] = LT.branch(SFZ_ON_AT, a.addr('cf_sfz_on')) | 1
    out[SFZ_OFF_AT] = LT.branch(SFZ_OFF_AT, a.addr('cf_sfz_off')) | 1
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
    p.add_argument('--diag', action='store_true', help='TEST ONLY: the OSReport build (S4CC / S4CV / S4CN / S4CF / '
                   'S4CM / S4CE / S4SF lines, docs/native-notes.md "Camera effects")')
    args = p.parse_args()
    if args.labels:
        labels(args.labels)
        return
    if not args.rpx:
        p.error('--rpx or --labels')
    words, lab, _s = build(rpx_reader(args.rpx), args.diag)
    print(' '.join(['textregion:0x%X' % TEXT_REGION, 'grow:0x%08X' % LIMIT] +
                   ['0x%08X=0x%08X' % kv for kv in sorted(words.items())]))
    sys.stderr.write('camera effects: %d words, Effect_Camera index %d (0x%08X), h_camfx 0x%08X, cf_calc 0x%08X, '
                     'cf_tab 0x%08X-0x%08X\n' % (len(words), CF_INDEX, CMD_CRC, lab['h_camfx'], lab['cf_calc'],
                                                 lab['cf_tab'], lab['cf_tab'] + NTAB * ENTRY))


if __name__ == '__main__':
    main()
