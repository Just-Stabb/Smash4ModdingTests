#!/usr/bin/env python3
"""Supamario's Time Skip (the SIDE special, status 0x153 on the ground and in the air; Dragon Ball Xenoverse 2's Super
skill 1352_HIK_DSH, Hit's "Time-Skip"; the user also calls it "Jump Spike"): the package, built over Sledgehammer's
(tools/supamario_sledgehammer_build.py, which runs Fake Death's, Core Breaker's and the Super God Fist's first; their
files stay theirs: only the side special's motions / scripts, one new effect set, seven new tones and the MSC change).

  python3 -I tools/supamario_timeskip_build.py SUPAMARIO_DIR OUT_DIR --ts-skill 1352_HIK_DSH_DIR --ts-se-wav WAV_DIR
        --frt-skill 1350_HIK_FRT_DIR (v4: the skill's EEPK folder, data/skill/SPA/1350_HIK_FRT)
        [Sledgehammer's: --sh-skill ... --sh-se-wav ... --fd-skill ... --fd-se-wav ... --skill ... --se-wav ... --ean ...
        --cmn-vfx VFX_CMN_DIR --skill-vfx ... --cmn-se ... --stb ...] [--png SHEET.png]

WAV_DIR: the skill SE (CAR_BTL_S1352_DSH_SE.acb cues 0-5) and CAR_BTL_CMN.acb cue 64 CharaAway_HKT, levelled
(tools/xv2acb.py extract + tools/xv2acb_decode.mjs + tools/supamario_timeskip_xv2.py se). Writes OUT_DIR/fighter/supamario
(Sledgehammer's build, then): motion/body (SpecialS = the dash, SpecialAirS = the connect:
tools/supamario_timeskip_anim.py), script/animcmd/body (specials / specialairs in game / effect / sound / expression),
effect/supamario (BTL_CMN effect 2's Btl_HitL with its fake-glow halo; Btl_HitLOD / Btl_Sweat00 are Sledgehammer's sets),
sound (TS_SE in his bank, the soundlabeltable's row 3249 grown), script/msc (supamario.c's ts_*), OUT_DIR/timeskip.json,
preview/.

The move: fighters/supamario/README.md "Time Skip".
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import supamario_timeskip_anim as anim  # noqa: E402

SCALE = anim.SCALE

# ---------------------------------------------------------------- XV2's timeline (reference/xv2/timeskip_skill.json)
# entry 0 (uncharged, BCM BacEntryPrimary), its real frames (TimeScale 20-50 x6): BAC b < 20 -> b, 20-50 -> 20 + (b -
# 20) / 6, >= 50 -> b - 25. SpecialS's motion frame IS that real frame (tools/supamario_timeskip_anim.py)
def real0(b):
    return b if b <= 20 else (20 + (b - 20) / 6.0 if b <= 50 else b - 25.0)


WIND_END = 20                       # BAC 20: ChargeControl 20-50 (the pose held while the button is), the BPE flash
CHARGE = 40                         # ChargeTime 40: the full charge (XV2: BacEntryCharge 2, the long dash)
HIT_FROM = int(real0(52)) - 1       # v2: 26, the frame before the dash (XV2's box BAC 54-83 is 29: from 29 a
                                    # fighter on top of him was already behind him, user: "won't activate the punch on
                                    # opponents touching Supamario at point blank")
HIT_LAST = int(real0(82))           # 57: its last active frame
DASH_END = int(real0(120))          # 95: the stop's last frame (entry 0 ends at 120)
HIT_LATE = 3.0                      # the MSC still looks for the hit 3 frames after a box's last frame
# the moving part (the user's spec over XV2's: a constant speed by the charge, the direction tracked; XV2 moves him by
# its root's launch from BAC 52 and Movement 0.7 m a frame 56-85, the charge lengthening it to 135): BAC 52-84
MOVE_FROM = int(real0(52))          # 27
MOVE_N = int(real0(85)) - MOVE_FROM  # 33 frames (27-59); the stop (the root's slide) from 60 on the ground
MOVE_EASE = 8                       # a miss: the speed eased down to VSTOP over the moving part's last 8 frames
# the user: "Uncharged: medium-slow. Fully charged: fast-medium", constant. His (Mario's fighter_param) dash initial
# speed 1.6, run 1.6 a frame; the Super God Fist's burst 4.53 a frame (motion 9-15); XV2's own 0.7 m = 3.53
VMIN, VMAX = 1.5, 3.36              # units a frame. v3 (user): uncharged a bit under his run (1.6), fully charged -20%
                                    # (v2 2.1 / 4.2, v1 2.4 / 4.2); linear between by the frames held
VSTOP = 1.85                        # the stop's first root speed (SpecialS frame 60): the eased miss meets it
SND = {'basa': 6, 'dash': int(real0(56)), 'timestop': 0, 'punch': 8, 'away': None}
# entry 4 (the user on connect): SpecialAirS 1:1
STRIKE = 16                         # BAC 16: Damage 140 (the victim's entry 5 function 0x2), TimeScale 16-22 x0.1
CONNECT_END = 80                    # entry 4's last frame
# the victim's entry 6 plays CMN cue 64 CharaAway_HKT at its frame 16: entry 5's 51 frames (16 + 4 at x0.1 + 31) =
# 87 real frames, + 16 = 103 after the connect, 47 after the launch (entry 5's BAC 20 = real 56): the connect motion's
# STRIKE + 47 (its freeze over, the motion runs 1:1 again)
AWAY_AFTER = 103 - 56
SND['away'] = STRIKE + AWAY_AFTER   # 63
# tracking (the user): the nearest opponent in front within 80 units, up to 65 degrees above or below; direction only
TRACK_RANGE = 80.0
TRACK_DEG = 65.0
# v3 (user: "strong at release, then soft"): the first TRACK_STRONG moving frames the aim is the target's direction,
# then it turns toward it at most TRACK_SOFT degrees a frame
TRACK_STRONG, TRACK_SOFT = 3, 1.5
DRIFT = 0.3                         # v3 (user): the charge hold's drift, units a frame at full tilt (his walk ~1.1)
RETRY_N = 3                         # v3: the catch looked at again while the hit fighter is frozen (the first-frame hit)
# after the move in the air (the user): his gravity eased back in over EASE_FRAMES; a faster fall clamped down to his
# normal one by FALL_EASE a frame
EASE_FRAMES = 45.0                  # v3 (user: a slower fall after an air punch; v2 20 / 0.05)
FALL_EASE = 0.02

# ---------------------------------------------------------------- the boxes
HIT_Z, HIT_Y, HIT_SIZE = round(1.0 * SCALE, 2), round(0.5 * SCALE, 2), round(0.5 * SCALE, 2)   # b_C_Base + (0, 0.5,
                                    # -1.0 m), 0.5 m: 5.04 ahead, 2.52 up, 2.52
# v2 (user: "The 2% detection hit won't activate the punch on opponents touching Supamario at point blank"): XV2's box
# covers 2.52-7.56 ahead only; a fighter on top of him (its body from about his centre) never met it. ID 1 (Part 0: one
# hit a fighter, the same record) at his middle: 1.5 ahead, 4.5 up, radius 4.0 (-2.5 to 5.5 ahead, 0.5 to 8.5 up),
# overlapping XV2's box: from his body's centre forward without a gap
HIT2_Z, HIT2_Y, HIT2_SIZE = 1.5, 4.5, 4.0
CATCH = dict(Damage=2.0, Angle=0, KBG=0, FKB=0, BKB=1)        # the detection: knockback 1 (Fake Death's grounded hit:
                                    # no launch), the MSC holds it; XV2's box does no damage (the 140 is the punch's)
CATCH_FREEZE = 3
HOLD_X, HOLD_Y = round(1.5 * SCALE, 2), round(0.1 * SCALE, 2)  # ThrowHandler: 1.5 m in front of g_x_LND, 0.1 m up
VICTIM_MID, VICTIM_HEAD = 5.0, 9.0
VICTIM_R2 = (HIT_SIZE + 12.0) ** 2
# the punch (the user: 18% with the detection's 2, "strong base knockback, good knockback growth"): 16%, angle 10
# (XV2's blow-away is ~3 degrees: (0, 0.025, 0.43) m a frame), BKB 70, KBG 70. Mario weight, no DI, from 0 / 50 /
# 100% before the move: knockback 98.5 / 142.6 / 186.7 (Sledgehammer charged 52.8 / 99.7 / 146.7, Core Breaker's
# crash 75.5 / 125.3 / 175.2)
STRIKE_HIT = dict(Damage=16.0, Angle=10, KBG=40, FKB=0, BKB=82)   # v3 (user: the same knockback at 0%, KO much later):
                                    # KBG 70 -> 40, BKB 70 -> 82 (an int field: 98.3 at 0% with the detection's 2, v2 98.5)
STRIKE_FREEZE = 30                  # XV2's time lock: the victim at x0.1 for 40 real frames, the user 60
STRIKE_SIZE = round(1.0 * SCALE, 2)
STRIKE_Z, STRIKE_Y = HOLD_X, round(HOLD_Y + VICTIM_MID, 2)
# shields (the user): uncharged, high shield damage and shieldstun, Supamario at an advantage: SH_TAKE of the max
# shield, SH_STUN frames held (cb_shield_tick), he acts from SH_IASA (STRIKE + 16): he acts on the 16th frame after the
# shared freeze, the shielder on the 27th: +11. Fully charged: unblockable, SH_BONUS more on a shielding fighter
SH_TAKE, SH_STUN = 0.5, 26
SH_IASA = STRIKE + 16
SH_BONUS = 6.0
STAGE_FREEZE_RENEW = 8              # v3: Stage_Freeze(1, 4) renewed every frame of the stopped time by the connect's game
                                    # script (v2: once, 30 frames): a move cut before the punch lets the stage go within 4
                                    # frames (the script stops). v4: 8: the user's clip shows the stage let go for 2 frames
                                    # after the catch (its freeze holds the script on frame 0 for 4 frames, not 3)
INV_STEP = 2.0
TURN_STICK, TURN_WINDOW = 0.5, 4    # the B-reverse (Sledgehammer's)
ST_SIDE, ST_FALL = 0x153, 0xE

# ---------------------------------------------------------------- variables (VAR_22-30: Sledgehammer uses VAR_0-21)
V_PH, V_CHG, V_SLOT, V_K, V_USED, V_BREV, V_EASE, V_AIM, V_SHV, V_RETRY = (0x0F000316 + i for i in range(10))   # v3:
                                    # VAR_31 TS_V_RETRY (the catch looked at again while the hit fighter is frozen)
USED_INDEX = V_USED - 0x0F000000     # the variable reset's index (VAR_26: 0x31A)

# ---------------------------------------------------------------- effects / sounds
FX_SCALE = 1.75                     # xv2_smash_fx.SIZE (the God Fist's settled size over XV2's)
HIT_EMPS = ['Btl_HitL.emp']         # BTL_CMN effect 2 (skill BDM #1's Effect1): Btl_HitLOD x1.5 (Sledgehammer's set),
                                    # Btl_HitL x0.8 (new) and x0.05 (a dot: left out), Btl_Sweat00 x2.0 on the head
                                    # (Sledgehammer's set), its CBIND (no Smash equivalent)
EEPK_SCALE = {'Btl_HitLOD.emp': 1.5, 'Btl_HitL.emp': 0.8, 'Btl_Sweat00.emp': 2.0}
FX_IDS = {'hitl': 0x0341005F, 'hitl_2': 0x03410060}   # Btl_HitL has more than 16 emitters: the
                                    # converter splits it in two sets (both played together)
SH_FX = {'hitlod': 0x0341005C, 'sweat': 0x0341005E}
# the brightness (the user found Sledgehammer's arcs too bright twice): Btl_HitL's white flash discs (flash_1 / _1_1,
# XV2's glare 1.0 but drawn at the HDR cap 2.0) were 28.6 square units over 1.0 on a grass stage and its glaring streaks
# (line / line_2 / line_1_1, glare 2.5) 8.9 (tools/supamario_fx_glow.py ts_hit --bg 0.5,0.65,0.3): each emitter's
# brightest drawn channel capped (Sledgehammer's flash_cap way), by its name's start
PEAK_CAP = (('flash', 0.2), ('line', 0.25), ('Line00', 0.5), ('grd00', 0.6), ('LINE', 0.8), ('stripe', 0.8))   # v1: flash
                                    # 0.35, line 0.5, Line00 1.0 (v2: the white flash, LOD_CAP)
FX_DUST = 0x1000009                 # Smash's dash cloud: XV2's Stage BG 60 at BAC 56 (the stage's own, not in the files)
# v2 (user: "Does a massive white flash when it hits an opponent"): BTL_CMN effect 2's Btl_HitLOD (v1: Sledgehammer's own
# set 0x0341005C at x1.5 x 1.75) starts with a white flash disc (flash_1_1) that covers ~55 square units of a grass stage
# on its first frame (supamario_fx_glow ts_hit: 54.6 of the 70.5 energy at frame 0), and the punch's 30-frame freeze is
# when it plays. Time Skip now has its own copy (Sledgehammer's set untouched) with its emitters' brightest drawn
# channel capped by name (LOD_CAP), and Btl_HitL's caps lowered (PEAK_CAP): every frame under the user's earlier
# tolerance (Sledgehammer v5's arcs: 1.0 / 3.6 square units over 1.0 on grass, uncharged / charged), the colours kept
LOD_CAP = (('flash', 0.22), ('grd01', 0.45), ('ptcl', 0.8), ('line', 0.8))
FX_LOD_ID = 0x03410061
# v4: XV2's own skill effects. system/custom_skill.cus (tools/xv2cus.py): skill 1352's EEPK is SPA/1350_HIK_FRT's, so the
# BAC's type 5 effects (skill 1352) are data/skill/SPA/1350_HIK_FRT/1350_HIK_FRT.eepk's (the user's folder: two containers,
# EMO Frt_Bas (.emo / .emm / .emb / .mat.ema / .obj.ema) and PBIND 1350_HIK_FRT.pbind.emb (Frt_Line, Frt_CrgAura,
# Frt_CrgAuraB, Frt_CrgAuraH, Frt_Sucses, Frt_Hit .emp) with its .ptcl.emm / .ptcl.emb; effects 0-6 and 10-12). The 1352 BAC
# plays two of them (every other effect item is BTL_CMN's or the stage's): effect 0 (entry 0 item 2, frame 0) and
# effect 11 (entries 4 / 9 / 10 / 11 item 16, frame 16). Each part's bone is the EEPK's (ESK), not the BAC's b_C_Base
# (effect 0's four parts name three bones, effects 3 / 4 differ by their bone alone)
# effect 0 (the user's "purple aura at the start ... left behind after the movement begins"): Frt_CrgAura on b_C_Pelvis
# at (0, -0.3, 0) m, Frt_CrgAuraB on b_C_Pelvis, Frt_CrgAura on b_R_Foot, none with PositionUpdate (they stay where
# they were made), x1.0; Frt_CrgAuraH on b_L_Elbow x0.5, following (PositionUpdate / RotateUpdate). Each EMP: one
# ConeExtrude ribbon (a stripe extruded behind a particle rising off a 0.3-0.5 m circle, Vortex-spun) emitted every 2
# frames for 40 (CrgAuraH 20): xv2_to_ptcl's CONE_STREAKS (a streak along the velocity, the ribbon's length)
E0_WORLD = (('Frt_CrgAura.emp', 'HipN', (0.0, -0.3, 0.0)),     # (EMP, the Smash bone for its ESK, the EEPK offset in m)
            ('Frt_CrgAuraB.emp', 'HipN', (0.0, 0.0, 0.0)),     # b_C_Pelvis -> HipN, b_R_Foot -> RFootJ: their places at
            ('Frt_CrgAura.emp', 'RFootJ', (0.0, 0.0, 0.0)))    # SpecialS frame 0 (tools/supamario_timeskip_anim.py)
E0_FOLLOW = ('Frt_CrgAuraH.emp', 15, 0.5)   # b_L_Elbow -> LArmJ (bone 15, Mario's elbow joint), the EEPK's x0.5
AURA_SIZE = 1.75                    # xv2_smash_fx.SIZE: XV2's x1.0
AURA_EVERY = 20                     # again every 20 frames of a held charge (v3's; the EMP emits 40 frames)
# effect 11 (the punch: the user's "purple speed lines" and "the long purple line along the victim's flight"):
# Frt_Hit.emp on g_R_Hand, Orientation AttachmentBone (the hand's axes), RotateUpdate only (world-fixed), x1.0,
# Deactivation Never. Its forward is the hand's -Z (the burst sprites at Z -0.4 / -1 / -1.8 / -2.5 born 0-3 frames
# apart, the speed lines' emitters turned X -90): baked onto the set's +X (E11_TURN, Y -90), the MSC turns it to his
# facing. Placed at his right fist at the punch (SpecialAirS frame 16, RHandN: E11_AT ahead / up; checked against the
# motion at build time)
E11_EMP = 'Frt_Hit.emp'
E11_AT = (6.85, 8.13)               # RHandN at SpecialAirS 16 (z ahead, y up)
E11_SIZE = 1.75                     # xv2_smash_fx.SIZE: XV2's x1.0
E11_TURN = (0.0, -90.0, 0.0)        # XV2's -Z (the punch) onto +X
# brightness (supamario_fx_glow.py ts_e11 / ts_e0 on grass and grey; the user's tolerance: at most 1.0 square unit over
# 1.0 in any frame): each emitter's brightest drawn channel capped by its name's start (Sledgehammer's arc_dim)
E11_CAP = ()
E0_CAP = ()
FX_E11_IDS = {'hit': 0x03410062, 'hit_2': 0x03410066, 'hit_h': 0x03410067, 'hit_2h': 0x03410068}
FX_AURA_ID, FX_GLASS_ID, FX_E0H_ID = 0x03410063, 0x03410064, 0x03410069
# v2 / v3 (item 11, the clip's time stop, frames 44-58): XV2 inverts the world (BPE 78) under BTL_CMN effect 108's glass
# (HIT_DmgGrs2, on the camera). v3: both on the camera (Effect_Camera, exe_v46z_camfx): the darkening an alpha-blended
# quad fixed to the screen (Mode 1, DARK_SIZE half heights: wider than a 16:9 screen), DARK_RGBA, unslowed, faded out
# after STRIKE frames (the punch); the glass in front of the camera (Mode 0, GLASS_CAM_Z, x GLASS_CAM_SIZE), unslowed.
# v2's Screen_Tint / world-placed glass are gone; any exit before the punch kills both (ts_stop_look_off)
CAMERA_FX = False                   # v3: the camera build (Effect_Camera, needs exe_v46z_camfx): off until camera_effects is
                                    # confirmed in game (its v1 test drew a screen-filling white flash); the default is the
                                    # MSC's Screen_Tint (TINT) and the glass model in front of the victim (GLASS_*)
FX_DARK_ID = 0x03410065
TINT = (0, 4, 0x14, 0x16, 0x2C, 0xB4, 0, 0xFF)  # slot 0, 4 frames in, R G B, A 0xB4, layer 0, priority (Sonic's FS's form)
TINT_OUT = 15
GLASS_SIZE, GLASS_Z = 0.36, 15.0    # the default glass: in front of the victim, toward the camera, XV2's scale
DARK_RGBA = (0.08, 0.09, 0.17, 0.7)  # the clip's dark blue-grey at 70%
DARK_Z, DARK_SIZE = 20.0, 2.2
GLASS_CAM_Z, GLASS_CAM_SIZE = 25.0, 0.1   # the shards (~140 x 100 units at x1 by their frame 49) over the screen at 25
GLASS_TEX = 0x15141F00
OUTLINE_A, OUTLINE_IN, OUTLINE_OUT = 110.0, 4, 10   # v3: the white outline; v4: FLASH (Color_Overlay) white at 110 of 255
TS_SE = {'ts_basa': ('CAR_S1352_DSH_Basa', 0.0),          # skill SE cue 0, BAC 6
         'ts_dash': ('CAR_S1352_DSH_Dash', 0.0),          # cue 1, BAC 56
         'ts_hazure': ('CAR_S1350_FRT_Hazure', 0.0),      # cue 2, BAC 86 (the whiff)
         'ts_timestop': ('CAR_S1350_FRT_TimeStop', 0.0),  # cue 3, entry 4 at 0
         'ts_punch': ('CAR_S1350_FRT_PumchiFuri', 0.0),   # cue 4, entry 4 at 8
         'ts_hit': ('CAR_S1350_FRT_Hit_TmLck', 0.0),      # cue 5, entry 4 at 16 (the MSC, on the hit)
         'ts_away': ('CharaAway_HKT', 0.0)}               # CMN cue 64, the victim's entry 6 at 16
SE_IDS = {'ts_basa': 0x0CB1009D, 'ts_dash': 0x0CB1009E, 'ts_hazure': 0x0CB1009F, 'ts_timestop': 0x0CB100A0,
          'ts_punch': 0x0CB100A1, 'ts_hit': 0x0CB100A2, 'ts_away': 0x0CB100A3}


def fl(v):
    return '%sf' % repr(float(v))


def msc_values(root_speed=None):
    """the TS_* names in fighters/supamario/supamario.c (root_speed: SpecialS's root travel a frame, from the EAN;
    reference/xv2/timeskip_root.json when not given)"""
    import supamario_fakedeath_build as FD
    if root_speed is None:
        root_speed = json.load(open(os.path.join(HERE, '..', 'reference', 'xv2', 'timeskip_root.json')))['speed']
    import math
    vals = {'TS_VROOT_CODE': FD.vel_code(root_speed), 'TS_ST_SIDE': fl(ST_SIDE), 'TS_ST_FALL': fl(ST_FALL),
            'TS_TURN_STICK': fl(TURN_STICK), 'TS_TURN_WINDOW': fl(TURN_WINDOW), 'TS_CHARGE': fl(CHARGE),
            'TS_WIND_END': fl(WIND_END), 'TS_VICTIM_R2': fl(VICTIM_R2), 'TS_HIT_Z': fl(HIT_Z), 'TS_HIT_Y': fl(HIT_Y),
            'TS_HIT_SIZE': fl(HIT_SIZE), 'TS_VICTIM_MID': fl(VICTIM_MID), 'TS_VICTIM_HEAD': fl(VICTIM_HEAD),
            'TS_HOLD_X': fl(HOLD_X), 'TS_HOLD_Y': fl(HOLD_Y), 'TS_INV_STEP': fl(INV_STEP),
            'TS_FX_HITLOD': '0x%X' % FX_LOD_ID, 'TS_FX_HITL': '0x%X' % FX_IDS['hitl'],
            'TS_HIT2_Z': fl(HIT2_Z), 'TS_HIT2_Y': fl(HIT2_Y), 'TS_HIT2_SIZE': fl(HIT2_SIZE),
            'TS_FX_E11': '0x%X' % FX_E11_IDS['hit'], 'TS_FX_E11_2': '0x%X' % FX_E11_IDS['hit_2'],
            'TS_FX_E11_H': '0x%X' % FX_E11_IDS['hit_h'], 'TS_FX_E11_2H': '0x%X' % FX_E11_IDS['hit_2h'],
            'TS_E11_Z': fl(E11_AT[0]), 'TS_E11_Y': fl(E11_AT[1]), 'TS_E11_SIZE': fl(E11_SIZE),
            'TS_FX_AURA': '0x%X' % FX_AURA_ID, 'TS_FX_GLASS': '0x%X' % FX_GLASS_ID,
            'TS_AURA_EVERY': fl(AURA_EVERY), 'TS_AURA_SIZE': fl(AURA_SIZE),
            'TS_FX_HITL_2': '0x%X' % FX_IDS['hitl_2'], 'TS_FX_SWEAT': '0x%X' % SH_FX['sweat'],
            'TS_FX_HITLOD_SIZE': fl(round(EEPK_SCALE['Btl_HitLOD.emp'] * FX_SCALE, 4)),
            'TS_FX_HITL_SIZE': fl(round(EEPK_SCALE['Btl_HitL.emp'] * FX_SCALE, 4)),
            'TS_FX_SWEAT_SIZE': fl(round(EEPK_SCALE['Btl_Sweat00.emp'] * FX_SCALE, 4)),
            'TS_SND_HIT': '0x%X' % SE_IDS['ts_hit'], 'TS_SND_HAZURE': '0x%X' % SE_IDS['ts_hazure'],
            'TS_MOVE_N': fl(MOVE_N), 'TS_MOVE_FROM': fl(MOVE_FROM), 'TS_MOVE_EASE': fl(MOVE_EASE),
            'TS_VMIN': fl(VMIN), 'TS_VMAX': fl(VMAX), 'TS_VSTOP': fl(VSTOP), 'TS_HIT_FROM': fl(HIT_FROM),
            'TS_HIT_LATE': fl(HIT_LATE), 'TS_STRIKE': fl(STRIKE), 'TS_CONNECT_END': fl(CONNECT_END),
            'TS_DASH_END': fl(DASH_END), 'TS_TRACK_RANGE': fl(TRACK_RANGE),
            'TS_TRACK_TAN2': fl(round(math.tan(math.radians(TRACK_DEG)) ** 2, 4)),
            'TS_EASE_FRAMES': fl(EASE_FRAMES), 'TS_FALL_EASE': fl(FALL_EASE), 'TS_USED_INDEX': fl(USED_INDEX),
            'TS_STRIKE_DMG': fl(STRIKE_HIT['Damage']), 'TS_SH_TAKE': fl(SH_TAKE), 'TS_SH_STUN': fl(SH_STUN),
            'TS_SH_IASA': fl(SH_IASA), 'TS_FX_DARK': '0x%X' % FX_DARK_ID,
            'TS_CAMFX': '1' if CAMERA_FX else '0', 'TS_TINT_SLOT': str(TINT[0]), 'TS_TINT_IN': str(TINT[1]),
            'TS_TINT_R': '0x%X' % TINT[2], 'TS_TINT_G': '0x%X' % TINT[3], 'TS_TINT_B': '0x%X' % TINT[4],
            'TS_TINT_A': '0x%X' % TINT[5], 'TS_TINT_OUT': str(TINT_OUT), 'TS_GLASS_SIZE': fl(GLASS_SIZE),
            'TS_GLASS_Z': fl(GLASS_Z),
            'TS_TRACK_STRONG': fl(TRACK_STRONG), 'TS_TRACK_SOFT': fl(round(math.radians(TRACK_SOFT), 6)),
            'TS_DRIFT': fl(DRIFT), 'TS_RETRY_N': fl(RETRY_N)}
    for n, v in (('PH', V_PH), ('CHG', V_CHG), ('SLOT', V_SLOT), ('K', V_K), ('USED', V_USED), ('BREV', V_BREV),
                 ('EASE', V_EASE), ('AIM', V_AIM), ('SHV', V_SHV), ('RETRY', V_RETRY)):
        vals['TS_V_' + n] = '0x%X' % v
    return vals


def knockback(hit, pct):
    import supamario_fakedeath_build as FD
    return FD.knockback(hit, pct)


def move_speeds(charge_frames=0):
    """the moving part's speed frame by frame (ts_dash_go)"""
    v = speed(charge_frames)
    out = []
    for k in range(MOVE_N):
        x = v
        if k > MOVE_N - MOVE_EASE - 0.5 and v > VSTOP:
            x = v + (VSTOP - v) * (k - (MOVE_N - MOVE_EASE - 1.0)) / MOVE_EASE
        out.append(x)
    return out


def speed(charge_frames):
    """the dash's speed after a charge of that many frames (ts_vdash)"""
    c = min(float(charge_frames), CHARGE)
    return VMIN + (VMAX - VMIN) * c / CHARGE


def travel(charge_frames=0, root=None, air=False):
    """his travel on a straight miss (units): the root's step before the moving part, the moving part (the last
    MOVE_EASE frames eased down to VSTOP when faster), and the stop's root slide (v3: in the air too; `air` kept for the
    callers)"""
    v = speed(charge_frames)
    mv = 0.0
    for k in range(MOVE_N):
        x = v
        if k > MOVE_N - MOVE_EASE - 0.5 and v > VSTOP:
            x = v + (VSTOP - v) * (k - (MOVE_N - MOVE_EASE - 1.0)) / MOVE_EASE
        mv += x
    if root:
        mv += sum(root[:MOVE_FROM]) + sum(root[MOVE_FROM + MOVE_N:])
    return round(mv, 2)


# ---------------------------------------------------------------- ACMD
def cmd(name, *params):
    return acmd.Command(acmd.BY_NAME[name.lower()], list(params))


def size(cmds):
    return sum(acmd.INFO[c.ident]['size'] for c in cmds)


def if_(var, method, value, body):
    """Float_Var_Compare(var, method, value) True{ body } (methods: 0 ==, 2 <=, 3 >=, 4 <, 5 >)"""
    return [cmd('float_var_compare', var, method, float(value)), cmd('true', 2 + size(body))] + body


def hitbox(**kw):
    import supamario_sledgehammer_build as SB
    return SB.hitbox(**kw)


def catch_box(ident=0):
    """the connect box (ID 0, Part 0): XV2's place and size, 2%, knockback 1, no clank (Clang 0: a grab-like box never
    loses a clank), shieldable, hits fighters lying down (Ground/Air 3), Smash's own small spark. v2: ID 1 the same at
    his middle (HIT2_*: point blank), Part 0 too (one hit a fighter)"""
    z, y, r = (HIT_Z, HIT_Y, HIT_SIZE) if ident == 0 else (HIT2_Z, HIT2_Y, HIT2_SIZE)
    return hitbox(ID=ident, Part=0, Size=r, Y=y, Z=z, SDI=0.0, Clang=0, Rebound=0, NoGFX=0, SFXLevel=0,
                  SFXType=1, HitstopFrames=CATCH_FREEZE, SelfHitstopFrames=CATCH_FREEZE, **CATCH)


def strike_box(unblockable=False, bonus=0.0):
    """the punch (ID 0, Part 1: its own hit record, the detection's Part 0 record on the victim stays): on the held
    victim's middle, the time lock's freeze both sides, no SDI, NoGFX (XV2's hit look from the MSC), Clang 0. Fully
    charged: unblockable (Shieldable 0), + bonus on a fighter caught shielding"""
    hit = dict(STRIKE_HIT, Damage=STRIKE_HIT['Damage'] + bonus)
    return hitbox(ID=0, Part=1, Size=STRIKE_SIZE, Y=STRIKE_Y, Z=STRIKE_Z, SDI=0.0, Clang=0, Rebound=0, NoGFX=1,
                  SFXLevel=2, SFXType=1, HitstopFrames=STRIKE_FREEZE, SelfHitstopFrames=STRIKE_FREEZE,
                  Shieldable=0 if unblockable else 1, **hit)


DASHING, CHARGING = 2.5, 1.5        # TS_V_PH > 2.5: the dash; < 1.5: the wind-up
FULL = CHARGE - 0.5                 # TS_V_CHG > FULL: fully charged


def freeze_loop():
    """v3: the stage stopped for the stopped time, renewed every frame (Stage_Freeze(1, STAGE_FREEZE_RENEW) then WAIT 1,
    STRIKE times): it lasts only while this script runs, so a move cut before the punch lets the stage go within
    STAGE_FREEZE_RENEW frames. The darkening is the MSC's (ts_tint: v2 had Screen_Tint here, which nothing ended on a cut)"""
    return GBloop(STRIKE, [cmd('stage_freeze', 1, STAGE_FREEZE_RENEW), cmd('wait', 1.0)])


def GBloop(n, body):
    return [cmd('set_loop', n)] + body + [cmd('goto', -size(body))]


def game_scripts():
    """specials: the detection box at HIT_FROM only in the dash (the script's clock runs on while the charge holds the
    pose; the MSC restarts the motion at WIND_END after a held charge, and removes the box: AttackModule 0x2719);
    specialairs: the stopped time (Stage_Freeze, the stage and background) from its frame 0 to the punch at STRIKE;
    the punch (uncharged: shieldable; fully charged: unblockable, + SH_BONUS on a fighter caught shielding), off 2
    frames later"""
    dash = [cmd('frame', float(HIT_FROM))] + if_(V_PH, 5, DASHING, [catch_box(0), catch_box(1)])
    connect = (freeze_loop() + [cmd('frame', float(STRIKE)), cmd('stage_freeze', 0, 0)] +
               [cmd('hit_log_clear', 1)] +
               if_(V_CHG, 4, FULL, [strike_box()]) +
               if_(V_CHG, 5, FULL, if_(V_SHV, 5, 0.5, [strike_box(True, SH_BONUS)]) +
                   if_(V_SHV, 4, 0.5, [strike_box(True)])) +
               [cmd('frame', float(STRIKE + 2)), cmd('remove_all_hitboxes')])
    return dash, connect


def effect_scripts():
    """XV2's Stage BG 60 (the stage's dust, at the dash's start BAC 56) as Smash's dash cloud on the ground. v4: skill
    effect 0's following part (Frt_CrgAuraH on the left elbow, x0.5) at frame 0; its world parts and effect 11 are the
    MSC's (ts_aura / ts_e11), as the strike's hit look and BTL_CMN 108 (the glass)"""
    dash = outline_on() + [cmd('external_graphic', FX_E0H_ID, E0_FOLLOW[1], 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               E0_FOLLOW[2] * AURA_SIZE, 1)] + [cmd('frame', float(MOVE_FROM))] + if_(0x0F000116, 0, 0, if_(V_PH, 5, DASHING, [
        cmd('graphic_effect', FX_DUST, 0, 0.0, 0.0, -2.0, 0.0, 0.0, 0.0, 1.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1)])) + [
        cmd('frame', float(DASH_END - OUTLINE_OUT))] + outline_off() + [cmd('frame', float(DASH_END)),
                                                                         cmd('terminate_overlays')]
    connect = ((time_stop_look() if CAMERA_FX else []) + outline_on() + [cmd('frame', float(CONNECT_END - OUTLINE_OUT))] +
               outline_off() + [cmd('frame', float(CONNECT_END)), cmd('terminate_overlays')])
    return dash, connect


def time_stop_look():
    """v3: the time stop on the camera at the connect's frame 0: the darkening (to the punch, then faded) and the glass"""
    return [cmd('effect_camera', FX_DARK_ID, 0.0, 0.0, DARK_Z, 0.0, 0.0, 0.0, DARK_SIZE, 1, STRIKE, 1),
            cmd('effect_camera', FX_GLASS_ID, 0.0, 0.0, GLASS_CAM_Z, 0.0, 0.0, 0.0, GLASS_CAM_SIZE, 0, 0, 1)]


def outline_on():
    """v3 (user: "Time Skip wraps the user in a faint white translucent glowing outline"; XV2's BPE 85 "Flashing White
    Body Outline 3", BAC entry 0 at 20 and 100, entry 4 at the punch; the clip: on him through the whole move). v4 (user:
    "no outline" in game): v3's LIGHT_SHINE (Flash_Light_Effect) is a light source, Mario's fireball's warm light on
    him (its vanilla use: (255, 230, 180, 160, 75, -10) faded out by LIGHT_COL_FRM over 5 frames): white at 110 it
    lit nothing visibly on him (and in the user's point-blank clip the opponent beside him looked washed). Now Smash 4's
    colour overlay, FLASH (Color_Overlay: the smash charge's glow; Mario's own scripts use FLASH (200, 255, 255, 110)),
    white at OUTLINE_A, faded in over OUTLINE_IN (FLASH_FRM)"""
    return [cmd('color_overlay', 255.0, 255.0, 255.0, 0.0),
            cmd('change_overlay', float(OUTLINE_IN), 255.0, 255.0, 255.0, OUTLINE_A)]


def outline_off():
    """faded out over OUTLINE_OUT, then COL_NORMAL (Terminate_Overlays) at the motion's end"""
    return [cmd('change_overlay', float(OUTLINE_OUT), 255.0, 255.0, 255.0, 0.0)]


def sound_scripts():
    """the skill's SE at XV2's frames: Basa at BAC 6 (in the wind-up only: a charge restart can't replay it), Dash at
    BAC 56; the connect's TimeStop at 0, PumchiFuri at 8, CMN CharaAway at STRIKE + 47 (the victim's entry 6). Hazure
    (the whiff) and Hit_TmLck (the strike) are the MSC's. No voices (the user's rule)"""
    dash = [cmd('frame', float(SND['basa']))] + if_(V_PH, 4, CHARGING, [cmd('sound_effect', SE_IDS['ts_basa'])]) + [
        cmd('frame', float(SND['dash']))] + if_(V_PH, 5, DASHING, [cmd('sound_effect', SE_IDS['ts_dash'])])
    connect = [cmd('sound_effect', SE_IDS['ts_timestop']), cmd('frame', float(SND['punch'])),
               cmd('sound_effect', SE_IDS['ts_punch']), cmd('frame', float(SND['away'])),
               cmd('sound_effect', SE_IDS['ts_away'])]
    return dash, connect


def expression_scripts():
    return ([cmd('frame', float(MOVE_FROM))] + if_(V_PH, 5, DASHING, [cmd('rumble', 0x10, 0)]),
            [cmd('frame', float(STRIKE)), cmd('rumble', 0x12, 0)])


SCRIPT_NAMES = ('specials', 'specialairs')


def scripts(body_dir):
    makers = {'game': game_scripts(), 'effect': effect_scripts(), 'sound': sound_scripts(),
              'expression': expression_scripts()}
    for part, bodies in makers.items():
        path = os.path.join(body_dir, part + '.bin')
        f = acmd.ACMDFile.load(path)
        for name, body in zip(SCRIPT_NAMES, bodies):
            assert f.script(name) is not None, (part, name)
            f.scripts[acmd.crc(name)] = body + [acmd.Command(acmd.END)]     # the Cape's replaced
        f.save(path)


# ---------------------------------------------------------------- effects (BTL_CMN effect 2's Btl_HitL)
def convert_fx(cmn_dir, fx_dir, halo=True, frt_dir=None, joints0=None):
    """Btl_HitL into his bank (fx_dir: effect/supamario, changed in place), as Sledgehammer's hit effects: vibrant
    (xv2_smash_fx.hdr_emitter: XV2's glare tint, colour x2, capped at HDR_CAP 2.0), facing-safe (world-placed and
    unturned by the MSC), fake-glow halos (HALO_ALPHA) on its glowing emitters; FX_IDS checked"""
    import tempfile
    import efc
    import ptcl
    import supamario_sledgehammer_build as SB
    import xv2_smash_fx as FX
    import xv2_to_ptcl
    import xv2vfx
    base = 'supamario.010d0000'
    p = ptcl.Ptcl(open(os.path.join(fx_dir, base + '.ptcl'), 'rb').read())
    e = efc.Efc(open(os.path.join(fx_dir, base + '.efc'), 'rb').read())
    before = len(p.build())
    old = xv2_to_ptcl.TEX_MAX
    try:
        xv2vfx.LENIENT_TARGETS = True
        xv2_to_ptcl.TEX_MAX = 64
        with tempfile.TemporaryDirectory() as tmp:
            pkg = SB._cmn_pkg(cmn_dir, tmp)
            mats = FX.material_table(xv2vfx.load_package(pkg, strict=False))
            made, log = xv2_to_ptcl.convert_package(p, pkg, 'PtcSupamarioTs', unit=FX.UNIT, emps=HIT_EMPS, strict=False)
    finally:
        xv2_to_ptcl.TEX_MAX = old
        xv2vfx.LENIENT_TARGETS = False
    sets, notes, got = {}, [], {}
    for si, name, chunk in made:
        key = {'PtcSupamarioTsBtl_HitL': 'hitl', 'PtcSupamarioTsBtl_HitL_2': 'hitl_2'}[name]
        emp = 'Btl_HitL.emp'
        idx = e.add(si + 1)
        got[key] = 0x03410000 | idx
        names = [en for _b, en, _n in chunk]
        k = 0
        for em in p.sets[si]['emitters']:
            d = em['data']
            if d is None:
                continue
            en = names[k] if k < len(names) else None
            k += 1
            notes.append('%s %s: %s' % (name, en, FX.hdr_emitter(p, d, mats.get(emp, {}).get(en))))
            SB.flat_ring(p, d, False)
            cap = next((c for pre, c in PEAK_CAP if (en or '').startswith(pre)), None)
            if cap is not None and 'subtractive' not in notes[-1] and SB.arc_peak(p, d) > cap:
                f = cap / SB.arc_peak(p, d)
                SB.arc_dim(p, d, (f, f, f))
                notes[-1] += '; capped at %.2f' % cap
        sets[key] = {'set': name, 'set_index': si, 'efc': idx, 'id': '0x%08X' % (0x03410000 | idx), 'emitters': names}
    assert got == FX_IDS, ('FX_IDS is out of date', {k: hex(v) for k, v in got.items()})
    halos = {}
    if halo:
        glow = {}
        dropped = {}
        for key, s in sets.items():
            si = s['set_index']
            emp = 'Btl_HitL.emp'
            ks = [k for k, em in enumerate(p.sets[si]['emitters']) if em['data'] is not None and
                  p.field(em['data'], 'alpha_init') > 0 and
                  (mats.get(emp, {}).get(p.emitter_name(em['data'])) or (0, 0, {}))[2].get('Glare') and
                  not FX.is_refraction(mats[emp][p.emitter_name(em['data'])][1],
                                       mats[emp][p.emitter_name(em['data'])][0])]
            room = 16 - len(p.sets[si]['emitters'])
            if len(ks) > room:
                dropped[key] = len(ks) - room
            ks = ks[:max(0, room)]
            if ks:
                glow[si] = ks
        comp = FX.add_halos(p, e, glow, FX.HALO_ALPHA, {})
        assert not comp, 'a set needs a companion halo set'
        halos = {'glowing': sum(len(v) for v in glow.values()), 'alpha': FX.HALO_ALPHA, 'no_room': dropped,
                 'by_set': {p.set_name(si): len(v) for si, v in glow.items()}}
    lod = lod_copy(p, e)
    import xv2_to_ptcl
    import xv2vfx
    old = xv2_to_ptcl.TEX_MAX, xv2_to_ptcl.CONE_STREAKS
    try:
        xv2vfx.LENIENT_TARGETS = True
        xv2_to_ptcl.TEX_MAX, xv2_to_ptcl.CONE_STREAKS = 64, True
        e11 = e11_sets(p, e, frt_dir, halo)                     # 0x62 (v2 / v3: the stand-in lines)
        e0 = e0_world_set(p, e, frt_dir, joints0, halo)          # 0x63 (v3: Hit's aura)
        glass = glass_model(cmn_dir, fx_dir, e)                  # 0x64
        dark = dark_set(p, e, sets['hitl']['set_index'])         # 0x65
        e11 = e11_rest(p, e, e11)                                # 0x66 - 0x68
        e0h = e0_follow_set(p, e, frt_dir, halo)                 # 0x69
    finally:
        xv2_to_ptcl.TEX_MAX, xv2_to_ptcl.CONE_STREAKS = old
        xv2vfx.LENIENT_TARGETS = False
    out = p.build()
    assert ptcl.Ptcl(out).validate() == []
    open(os.path.join(fx_dir, base + '.ptcl'), 'wb').write(out)
    open(os.path.join(fx_dir, base + '.efc'), 'wb').write(e.build())
    bad = FX.facing_emitters(p, [s['set_index'] for s in sets.values()] + [lod['set_index']])
    return {'sets': sets, 'skipped': log, 'notes': notes, 'halos': halos, 'ptcl_bytes': [before, len(out)],
            'facing_problems': bad + FX.facing_emitters(p, [e0h['set_index']]), 'lod': lod, 'e11': e11, 'aura': e0,
            'e0_follow': e0h, 'glass': glass, 'dark': dark}


def lod_copy(p, e):
    """v2: Time Skip's own Btl_HitLOD (Sledgehammer's set cloned, so Sledgehammer keeps its own byte for byte), each
    emitter's brightest drawn channel capped by LOD_CAP (by its name's start: the white flash disc flash_1_1 first)"""
    import supamario_sledgehammer_build as SB
    src = e.entries[SH_FX['hitlod'] & 0xFFFF][1] - 1
    si = p.clone_set(src, 'PtcSupamarioTsBtl_HitLOD')
    idx = e.add(si + 1)
    assert 0x03410000 | idx == FX_LOD_ID, ('FX_LOD_ID is out of date', hex(0x03410000 | idx))
    notes = []
    for em in p.sets[si]['emitters']:
        d = em['data']
        if d is None:
            continue
        en = p.emitter_name(d)
        cap = next((c for pre, c in LOD_CAP if en.startswith(pre)), None)
        pk = SB.arc_peak(p, d)
        if cap is not None and p.field(d, 'blend_type') != 2 and pk > cap:
            f = cap / pk
            SB.arc_dim(p, d, (f, f, f))
            notes.append('%s: peak %.2f -> %.2f' % (en, pk, cap))
    return {'set': 'PtcSupamarioTsBtl_HitLOD', 'set_index': si, 'efc': idx, 'id': '0x%08X' % FX_LOD_ID,
            'from': '0x%08X' % SH_FX['hitlod'], 'capped': notes}


def struct_pack_follow_none(d):
    """the particles stay where they were born (ptcl +0x310 follow type 1): a world-placed burst, the fighters move on"""
    import struct
    struct.pack_into('>I', d, 0x310, 1)


def frt_emissions(p, pkg, images, emp_name):
    """an EMP of 1350_HIK_FRT.eepk converted emission by emission (xv2_to_ptcl.convert_emission, as convert_emp, without
    making sets): [(emitter bytes, emission name, notes)], skipped lines. ConeExtrude ribbons as streaks (CONE_STREAKS)"""
    import xv2_smash_fx as FX
    import xv2_to_ptcl as X
    emp = pkg['emp'][emp_name]
    spawn = X.simulate(emp)
    out, log = [], []

    def walk(nodes, chain):
        for n in nodes:
            n['_emp'] = emp
            c = chain + [n]
            if n['NodeType'] == 'Emission':
                if X.emission_kind(n) is None or 'Hide' in n['NodeFlags_names']:
                    log.append('%s %s: %s skipped' % (emp_name, n['Name'], n['NodeSpecificType']))
                else:
                    out.append(X.convert_emission(p, pkg, images, c, FX.UNIT, n['Name'], spawn))
            walk(n['ChildParticleNodes'], c)
    walk(emp['ParticleNodes'], [])
    return out, log


def _frt_pkg(frt_dir):
    import xv2_smash_fx as FX
    import xv2_to_ptcl as X
    import xv2vfx
    pkg = xv2vfx.load_package(frt_dir, strict=False)
    return pkg, X.emb_images(pkg), FX.material_table(pkg)


def _vibrant(p, d, mats, emp, name, caps, world=True):
    """the God Fist / Sledgehammer way: XV2's glare tint, colour x2 capped at HDR_CAP, alpha x2 (hdr_emitter); world
    sets' particles stay where they were born (follow none); the brightest drawn channel capped by caps (name prefix)"""
    import supamario_sledgehammer_build as SB
    import xv2_smash_fx as FX
    note = FX.hdr_emitter(p, d, mats.get(emp, {}).get(name))
    if world:
        struct_pack_follow_none(d)
    cap = next((c for pre, c in caps if name.startswith(pre)), None)
    if cap is not None and p.field(d, 'blend_type') != 2 and SB.arc_peak(p, d) > cap:
        f = cap / SB.arc_peak(p, d)
        SB.arc_dim(p, d, (f, f, f))
        note += '; capped at %.2f' % cap
    return note


def _glowing(p, mats, emp, k_names):
    """the indices of a set's emitters XV2 draws with glare (EMM Glare on), not refraction, visible: halo candidates"""
    import xv2_smash_fx as FX
    out = []
    for k, d, name in k_names:
        m = mats.get(emp, {}).get(name)
        if m and m[2].get('Glare') and not FX.is_refraction(m[1], m[0]) and p.field(d, 'alpha_init') + \
                max(0.0, p.field(d, 'alpha_diff21')) > 0:
            out.append(k)
    return out


def _turn(p, d, deg):
    """the emitter's transform turned by deg (X, Y, Z degrees, Rz.Ry.Rx) about the set's origin, its offset too"""
    import numpy as np
    import xv2_to_ptcl as X
    b = X.euler_matrix(deg)
    m = X.euler_matrix([float(np.degrees(v)) for v in p.field(d, 'emitter_rotation')])
    t = np.array(p.field(d, 'emitter_translation'), float)
    p.set_emitter_srt(d, tuple(p.field(d, 'emitter_scale')), X.matrix_euler(b @ m), [float(v) for v in b @ t])


def e11_sets(p, e, frt_dir, halo=True):
    """v4: XV2's skill effect 11 (Frt_Hit.emp, 1350_HIK_FRT.eepk; README "Time Skip v4"): its emissions converted as the
    other XV2 effects (vibrant, world-placed: follow none), turned so its forward (XV2's -Z) is +X (E11_TURN), capped by
    E11_CAP, split in two sets (16 emitters at most: FX_E11_IDS hit / hit_2); fake-glow halos on its glaring emitters
    in a companion set each (hit_h / hit_2h). The efc entries: hit here, hit_2 / the halos by e11_rest (FX_E11_IDS'
    order, after the glass / dark entries v2 / v3 made)"""
    pkg, images, mats = _frt_pkg(frt_dir)
    made, log = frt_emissions(p, pkg, images, E11_EMP)
    notes, ems = [], []
    for d, name, n0 in made:
        d = bytearray(d)
        _turn(p, d, E11_TURN)
        notes.append('%s: %s; %s' % (name, '; '.join(n0), _vibrant(p, d, mats, E11_EMP, name, E11_CAP)))
        ems.append((bytes(d), name))
    sets = []
    for part in range(0, len(ems), 16):
        chunk = ems[part:part + 16]
        name = 'PtcSupamarioTsFrt_Hit' + ('' if part == 0 else '_%d' % (part // 16 + 1))
        sets.append((p.new_set(name, [c[0] for c in chunk], [c[1] for c in chunk]), name, [c[1] for c in chunk]))
    assert len(sets) == 2, [x[1] for x in sets]
    idx = e.add(sets[0][0] + 1)
    assert 0x03410000 | idx == FX_E11_IDS['hit'], ('FX_E11_IDS is out of date', hex(0x03410000 | idx))
    return {'sets': [{'set': n, 'set_index': si, 'emitters': en} for si, n, en in sets], 'skipped': log,
            'notes': notes, 'efc': {'hit': idx}, 'halo': halo, 'mats': mats}


def e11_rest(p, e, rep):
    """the second set's efc entry and the halo companions (FX_E11_IDS)"""
    import xv2_smash_fx as FX
    s0, s1 = rep['sets']
    idx = e.add(s1['set_index'] + 1)
    assert 0x03410000 | idx == FX_E11_IDS['hit_2'], ('FX_E11_IDS is out of date', hex(0x03410000 | idx))
    rep['efc']['hit_2'] = idx
    mats = rep.pop('mats')
    glow = {}
    for s_ in (s0, s1):
        si = s_['set_index']
        kn = [(k, em['data'], p.emitter_name(em['data'])) for k, em in enumerate(p.sets[si]['emitters'])
              if em['data'] is not None]
        ks = _glowing(p, mats, E11_EMP, kn)
        if ks and rep['halo']:
            glow[si] = ks
    # every halo in a companion set (none in the sets themselves: one call list for the MSC whatever the room)
    comp = {}
    if glow:
        for si, ks in sorted(glow.items()):
            hs = [FX.halo_emitter(p, p.sets[si]['emitters'][k]['data'], FX.HALO_ALPHA, {}) for k in ks]
            ns = p.new_set(p.set_name(si) + FX.HALO_SUFFIX, hs, [p.emitter_name(h) for h in hs])
            comp[si] = (ns, e.add(ns + 1), len(hs))
    got = [0x03410000 | comp[s_['set_index']][1] for s_ in (s0, s1) if s_['set_index'] in comp]
    assert got == [FX_E11_IDS['hit_h'], FX_E11_IDS['hit_2h']], ('FX_E11_IDS is out of date', [hex(g) for g in got])
    rep['halos'] = {'alpha': FX.HALO_ALPHA, 'by_set': {p.set_name(si): n for si, (_ns, _i, n) in comp.items()},
                    'companions': [p.set_name(ns) for ns, _i, _n in comp.values()]}
    return rep


def e0_world_set(p, e, frt_dir, joints0, halo=True):
    """v4: XV2's skill effect 0's three world parts (E0_WORLD; README "Time Skip v4") in one set: each EMP's ConeExtrude
    stripe as a streak (CONE_STREAKS), vibrant, follow none (left where it was made), at its bone's place at SpecialS
    frame 0 (joints0: {bone: (z ahead, y up)}) + the EEPK offset, in the set's space (+X his forward, / AURA_SIZE: the
    call's size scales it); fake-glow halos on the glaring ones (in the set: room)"""
    import xv2_smash_fx as FX
    pkg, images, mats = _frt_pkg(frt_dir)
    ems, notes, kn = [], [], []
    for emp, bone, off in E0_WORLD:
        made, _log = frt_emissions(p, pkg, images, emp)
        for d, name, n0 in made:
            d = bytearray(d)
            z, y = joints0[bone]
            t = list(p.field(d, 'emitter_translation'))
            t = [t[0] + (z + off[2] * SCALE) / AURA_SIZE, t[1] + (y + off[1] * SCALE) / AURA_SIZE, t[2]]
            p.set_emitter_srt(d, tuple(p.field(d, 'emitter_scale')), tuple(p.field(d, 'emitter_rotation')), t)
            notes.append('%s %s at %s: %s; %s' % (emp, name, bone, '; '.join(n0),
                                                  _vibrant(p, d, mats, emp, name, E0_CAP)))
            kn.append((len(ems), d, name, emp))
            ems.append((bytes(d), '%s_%s' % (emp[4:-4], bone)))
    if halo:
        for k, d, name, emp in kn:
            if _glowing(p, mats, emp, [(k, d, name)]):
                ems.append((bytes(FX.halo_emitter(p, d, FX.HALO_ALPHA, {})), ems[k][1] + FX.HALO_SUFFIX))
    si = p.new_set('PtcSupamarioTsFrt_CrgAura', [x[0] for x in ems], [x[1] for x in ems])
    idx = e.add(si + 1)
    assert 0x03410000 | idx == FX_AURA_ID, ('FX_AURA_ID is out of date', hex(0x03410000 | idx))
    return {'set': 'PtcSupamarioTsFrt_CrgAura', 'set_index': si, 'efc': idx, 'id': '0x%08X' % FX_AURA_ID,
            'emitters': [x[1] for x in ems], 'notes': notes}


def e0_follow_set(p, e, frt_dir, halo=True):
    """v4: XV2's skill effect 0's following part (E0_FOLLOW: Frt_CrgAuraH on the left elbow, x0.5): its own set, played
    by the effect script on the bone (External_Graphic, no offset / turn), facing-safe (the God Fist's rule), its
    particles on the bone's live matrix (XV2's PositionUpdate)"""
    import supamario_sledgehammer_build as SB
    import xv2_smash_fx as FX
    pkg, images, mats = _frt_pkg(frt_dir)
    emp = E0_FOLLOW[0]
    made, _log = frt_emissions(p, pkg, images, emp)
    ems, notes = [], []
    for d, name, n0 in made:
        d = bytearray(d)
        notes.append('%s: %s; %s' % (name, '; '.join(n0), _vibrant(p, d, mats, emp, name, E0_CAP, world=False)))
        FX.facing_safe(p, d)
        SB.follow(p, d)
        ems.append((bytes(d), name))
    if halo:
        for k, (d, name) in enumerate(list(ems)):
            if _glowing(p, mats, emp, [(k, d, name)]):
                ems.append((bytes(FX.halo_emitter(p, bytearray(d), FX.HALO_ALPHA, {})), name + FX.HALO_SUFFIX))
    si = p.new_set('PtcSupamarioTsFrt_CrgAuraH', [x[0] for x in ems], [x[1] for x in ems])
    idx = e.add(si + 1)
    assert 0x03410000 | idx == FX_E0H_ID, ('FX_E0H_ID is out of date', hex(0x03410000 | idx))
    return {'set': 'PtcSupamarioTsFrt_CrgAuraH', 'set_index': si, 'efc': idx, 'id': '0x%08X' % FX_E0H_ID,
            'emitters': [x[1] for x in ems], 'notes': notes}


def dark_set(p, e, hitl_si):
    """v3: the time stop's darkening for Effect_Camera: one alpha-blended billboard (Btl_HitL's flash_1, blend 0, its
    texture made solid white), 1 x 1 at size 1, DARK_RGBA, one particle that lives until the call's Frames fade it,
    follow type 0 (it moves with the camera)"""
    import struct
    import numpy as np
    src = next(em['data'] for em in p.sets[hitl_si]['emitters'] if em['data'] is not None and
               p.emitter_name(em['data']) == 'flash_1')
    d = bytearray(src)
    assert p.field(d, 'blend_type') == 0
    for name, v in (('one_time', 1), ('end_frame', 1), ('emit_rate', 1.0), ('emit_interval', 0), ('start_frame', 0),
                    ('emit_start', 0), ('volume_type', 0), ('volume_radius', [0.0, 0.0, 0.0]), ('figure_velocity', 0.0),
                    ('init_velocity_random', 0.0), ('emitter_velocity', 0.0), ('dispersion_angle', 0.0),
                    ('gravity', [0.0, 0.0, 0.0]), ('ptcl_life', 0x7FFFFFFF), ('ptcl_life_random', 0),
                    ('scale', [1.0, 1.0]), ('scale_random', [0.0, 0.0]), ('scale_init_ratio', [1.0, 1.0]),
                    ('scale_diff21', [0.0, 0.0]), ('scale_diff32', [0.0, 0.0]), ('rotation_init', [0.0, 0.0, 0.0]),
                    ('rotation_random', [0.0, 0.0, 0.0]), ('rotation_velocity', [0.0, 0.0, 0.0]),
                    ('alpha_init', DARK_RGBA[3]), ('alpha_diff21', 0.0), ('alpha_diff32', 0.0), ('color_scale', 1.0)):
        p.set_field(d, name, v)
    p.set_key_anims(d, [])
    p.set_emitter_srt(d)
    for track in (0, 1):
        p.set_color_keys(d, track, [DARK_RGBA[:3] + (1.0,)], 0)
    p.set_texture(d, 0, np.full((16, 16, 4), 255, np.uint8))
    struct.pack_into('>I', d, 0x310, 0)                 # follow: an overlay moving with the camera
    si = p.new_set('PtcSupamarioTsDark', [bytes(d)], ['dark'])
    idx = e.add(si + 1)
    assert 0x03410000 | idx == FX_DARK_ID, ('FX_DARK_ID is out of date', hex(0x03410000 | idx))
    return {'set': 'PtcSupamarioTsDark', 'set_index': si, 'efc': idx, 'id': '0x%08X' % FX_DARK_ID, 'rgba': DARK_RGBA}


def glass_model(cmn_dir, fx_dir, e, preview=None):
    """v2: BTL_CMN effect 108 (BAC entry 4 item 7 at the connect, frame 0; turned off at 16): HIT_DmgGrs2.emo, the
    glass that shatters as time stops (XV2: on the camera, scale 0.36, LoopCancel). Smash 4 can't attach an effect to
    the camera (until camera_effects_v1): its model (tools/xv2_to_nud.py) played by the MSC in front of the victim,
    Effect_Camera (v3: on the camera as XV2, time_stop_look)"""
    import subprocess
    r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'xv2_to_nud.py'), cmn_dir, 'HIT_DmgGrs2',
                        os.path.join(fx_dir, 'model'), '--prefix', 'EffSupamarioTs', '--tex-base', hex(GLASS_TEX),
                        '--plain', '1', '--scale', str(SCALE)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    folder = 'EffSupamarioTsDmgGrs2'
    args = [sys.executable, '-I', os.path.join(HERE, 'xv2_to_nud.py'), 'verify', os.path.join(fx_dir, 'model', folder)]
    if preview:
        args += ['--preview', preview]
    r = subprocess.run(args, capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
    idx = e.add(0, folder)
    assert 0x03410000 | idx == FX_GLASS_ID, ('FX_GLASS_ID is out of date', hex(0x03410000 | idx))
    return {'folder': folder, 'efc': idx, 'id': '0x%08X' % FX_GLASS_ID}


# ---------------------------------------------------------------- the sound bank
def sound_bank(fdir, out_dir, wav_dir):
    """TS_SE into his bank and the soundlabeltable (Sledgehammer's sound_bank way)"""
    import supamario_godfist_build as GB
    table = os.path.join(out_dir, 'sound', 'config', 'soundlabeltable.bin')
    old_se, old_ids = dict(GB.CMN_SE), dict(GB.SE_IDS)
    try:
        GB.CMN_SE.clear()
        GB.CMN_SE.update(TS_SE)
        tmp = table + '.in'
        with open(table, 'rb') as fh, open(tmp, 'wb') as fo:
            fo.write(fh.read())
        got = dict(GB.sound_bank(fdir, tmp, wav_dir, out_dir))
        os.remove(tmp)
    finally:
        GB.CMN_SE.clear()
        GB.CMN_SE.update(old_se)
        GB.SE_IDS.clear()
        GB.SE_IDS.update(old_ids)
    assert got == SE_IDS, ('SE_IDS is out of date', {k: hex(v) for k, v in got.items()})
    return got


# ---------------------------------------------------------------- build
def build(sm_dir, out_dir, ts_skill, ts_se_wav, sh_args, png=None, halo=True, frt_dir=None):
    import supamario_godfist_build as GB
    import supamario_sledgehammer_build as SB
    fdir = SB.build(sm_dir, out_dir, sh_args['sh_skill'], sh_args['sh_se_wav'], sh_args['fd'], sh_args.get('png'), halo)
    mo = os.path.join(fdir, 'motion', 'body')
    vbn = os.path.join(sm_dir, 'model', 'body', 'c00', 'model.vbn')
    outs, bones, info = anim.build(mo, vbn, os.path.join(ts_skill, '1352_HIK_DSH.ean'), mo)
    trans = [h for n, _p, h in bones if n == 'TransN'][0]
    for m in anim.MOTIONS:
        o = outs[('main', m)]
        assert o.frames == anim.frames_of(m)
        assert all(max(abs(v) for v in o.sample(trans, f)[0]) < 1e-6 for f in range(o.frames)), 'TransN moves'
    rs = info['info'][anim.DASH]['root_speed']
    ref = os.path.join(HERE, '..', 'reference', 'xv2', 'timeskip_root.json')
    want = {'source': '1352_HIK_DSH.ean #0 b_C_Base Z, SpecialS frames (tools/supamario_timeskip_anim.py root_speed): '
                      'the MSC\'s ts_vroot', 'speed': rs}
    if not os.path.exists(ref) or json.load(open(ref)) != want:
        with open(ref, 'w') as fh:
            json.dump(want, fh)
    js = {m: anim.joints(info['frames'][m], info['smash']) for m in anim.MOTIONS}
    doc = {'dash_frames': anim.frames_of(anim.DASH), 'connect_frames': anim.frames_of(anim.CONNECT),
           'hit': [HIT_FROM, HIT_LAST], 'move': [MOVE_FROM, MOVE_N, MOVE_EASE, VMIN, VMAX, VSTOP], 'strike': STRIKE,
           'travel': {'uncharged': travel(0, rs), 'charged': travel(CHARGE, rs), 'uncharged_air': travel(0, rs, True),
                      'charged_air': travel(CHARGE, rs, True)},
           'root_speed': rs, 'joints': js, 'info': {m: {k: v for k, v in info['info'][m].items()}
                                                         for m in anim.MOTIONS}}
    os.makedirs(os.path.join(out_dir, 'preview'), exist_ok=True)
    hb = {anim.DASH: {f: (HIT_Z, HIT_Y, HIT_SIZE) for f in (HIT_FROM, 40, HIT_LAST)},
          anim.CONNECT: {STRIKE: (STRIKE_Z, STRIKE_Y, STRIKE_SIZE)}}
    anim.sheet(outs, bones, png or os.path.join(out_dir, 'preview', 'timeskip_anim.png'),
               {m: info['info'][m]['root_z'] for m in anim.MOTIONS}, hitboxes=hb)
    hand = js[anim.CONNECT][STRIKE]['RHandN']
    assert abs(hand[0] - E11_AT[0]) < 0.01 and abs(hand[1] - E11_AT[1]) < 0.01, ('E11_AT is out of date', hand)
    rep = convert_fx(sh_args['fd']['cb']['gf']['cmn_vfx'], os.path.join(fdir, 'effect', 'supamario'), halo, frt_dir,
                     js[anim.DASH][0])
    assert not rep['facing_problems'], rep['facing_problems']
    doc['fx'] = rep
    with open(os.path.join(out_dir, 'timeskip.json'), 'w') as fh:
        json.dump(doc, fh, indent=1)
    scripts(os.path.join(fdir, 'script', 'animcmd', 'body'))
    sound_bank(fdir, out_dir, ts_se_wav)
    GB.msc(os.path.join(fdir, 'script', 'msc', 'supamario.mscsb'))
    return fdir


def main():
    a = sys.argv[1:]
    opts = {}
    halo = '--no-halo' not in a
    if not halo:
        a.remove('--no-halo')
    keys = ('--ts-skill', '--ts-se-wav', '--frt-skill', '--sh-skill', '--sh-se-wav', '--fd-skill', '--fd-se-wav', '--skill', '--se-wav',
            '--ean', '--cmn-vfx', '--skill-vfx', '--cmn-se', '--stb', '--png')
    for k in keys:
        if k in a:
            i = a.index(k)
            opts[k] = a[i + 1]
            del a[i:i + 2]
    if len(a) != 2 or any(k not in opts for k in keys[:11]):
        sys.exit(__doc__)
    gf = {'ean': opts['--ean'], 'cmn_vfx': opts['--cmn-vfx'], 'skill_vfx': opts.get('--skill-vfx'),
          'cmn_se': opts.get('--cmn-se'), 'stb': opts.get('--stb')}
    cb = {'skill': opts['--skill'], 'se_wav': opts['--se-wav'], 'gf': gf}
    fd = {'fd_skill': opts['--fd-skill'], 'fd_se_wav': opts['--fd-se-wav'], 'cb': cb}
    sh = {'sh_skill': opts['--sh-skill'], 'sh_se_wav': opts['--sh-se-wav'], 'fd': fd}
    print(build(a[0], a[1], opts['--ts-skill'], opts['--ts-se-wav'], sh, opts.get('--png'), halo, opts['--frt-skill']))
    print('sounds: ' + ', '.join('%s 0x%08X' % kv for kv in SE_IDS.items()))
    print('effects: ' + ', '.join('%s 0x%08X' % kv for kv in FX_IDS.items()))
    import supamario_fakedeath_build as FD
    for pct in (0, 50, 100, 150):
        kb = knockback(STRIKE_HIT, pct + CATCH['Damage'])
        print('at %d%% (+ the detection): punch knockback %.1f, hitstun %d, ~%.0f units away' % (
            pct, kb, int(kb * 0.4), FD.flight(kb, STRIKE_HIT['Angle'])[0]))


if __name__ == '__main__':
    main()
