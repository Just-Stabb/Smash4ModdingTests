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
import math
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
# v5 (user: "high landing lag after using Time Skip if it ended in the air, similarly to how Bayonetta ... even after doing
# other moves"): his next landing after an air end is LandingFallSpecial (0x19) this long (frames: a Bayonetta-like high
# special landing; Sledgehammer's is 10); VAR_31 = TS_LAG_FLAG marks it outside the move
LAND_LAG, LAG_FLAG, ST_LANDING = 30, 100.0, 0x16
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
E0_FOLLOW = ('Frt_CrgAuraH.emp', 15, 0.5)   # b_L_Elbow -> LArmJ (bone 15, Mario's elbow joint), the EEPK's x0.5; XV2's
                                    # Orientation User (his axes, not the bone's): External_Graphic's last word 0, the
                                    # bone's place only (Sledgehammer's charge glow), its streaks rising as XV2's
AURA_SIZE = 1.75                    # xv2_smash_fx.SIZE: XV2's x1.0
AURA_EVERY = 20                     # again every 20 frames of a held charge (v3's; the EMP emits 40 frames)
# effect 11 (the punch: the user's "purple speed lines" and "the long purple line along the victim's flight"):
# Frt_Hit.emp on g_R_Hand, Orientation AttachmentBone (the hand's axes), RotateUpdate only (world-fixed), x1.0,
# Deactivation Never. Its speed lines are emitted along the hand's -Z (their emitters turned X -90) and drawn as
# streaks along their motion (VisibleOnSpeed; Smash's type 3: Line_Hit.dds's line runs from the particle back along
# its motion, tools/fx_render.py): in the user's XV2 clip (fc8b90ed, 64-100) the lines run from the fist forward
# through the victim and past it, so the hand's -Z is his back and +Z the punch: baked onto the set's -X / +X
# (E11_TURN, Y +90); the burst sprites (Z -0.4) sit at his wrist. The MSC turns it to his facing. Placed at his right
# fist at the punch (SpecialAirS frame 16, RHandN: E11_AT ahead / up; checked against the motion at build time)
E11_EMP = 'Frt_Hit.emp'
E11_AT = (6.85, 8.13)               # RHandN at SpecialAirS 16 (z ahead, y up)
E11_SIZE = 1.75                     # xv2_smash_fx.SIZE: XV2's x1.0
E11_SIZE = 2.6                      # v5 (user: "much weaker and compressed compared to the massive aura escaping the
                                    # opponent"; XV2's screenshots: the burst as tall as the fighters, the lines far past
                                    # the victim): x1.5
E11_TURN = (0.0, 90.0, 0.0)         # the hand's +Z (the punch) onto +X
# brightness (supamario_fx_glow.py ts_e11 / ts_e0 on grass and grey; the user's tolerance: at most 1.0 square unit over
# 1.0 in any frame): each emitter's brightest drawn channel capped by its name's start (Sledgehammer's arc_dim)
E11_CAP = (('sprite_2', 0.12), ('sprite_BG', 0.5), ('line_add', 0.15), ('wave_add', 0.07), ('wave_nml', 0.9),
           ('sprite_1', 0.25), ('sprite', 0.5), ('line_BG', 0.9), ('BG', 0.9), ('ring', 0.5))   # v4: from 2.0 each (the
           # vibrant gain): uncapped the set drew 155 square units over 1.0 at its first frame on grass (12.4 peak: the burst's
           # white sparkle sprite_2, the opaque disc sprite_BG, the stacked lines / waves)
# v5 (user: "much weaker and compressed"; "keep brightness sane by limiting the white blow-out, not the size or the
# purple"): the purple lines / slashes / glows brighter (the check is now the white area: purple past 1 blooms purple),
# the sparkle dots (0.01 m: under a pixel at Smash's camera) x SPARK_GROW, the navy flames lilac and translucent
E11_CAP = (('sprite_2', 0.12), ('sprite_BG', 0.5), ('line_add', 0.38), ('wave_add', 0.25), ('wave_nml', 1.0),
           ('sprite_1', 0.4), ('sprite', 0.45), ('line_BG', 1.0), ('BG', 1.0), ('ring', 0.5))
SECONDARY_V5, SECONDARY_LIFT, SECONDARY_ALPHA, BLACK_ALPHA = True, 0.6, 0.55, 0.35
SPARK_GROW, SPARKS = 6.0, ('sprite', 'sprite_3')
E0_CAP = (('stripe', 0.32),)       # v4: the streaks from 2.0 (uncapped, alpha 1: 8.6 / 13.6 square units over 1.0 on grass / grey)
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
# v6: on. The user's v5 clip (d8c96e8e): the glass over an undarkened stage (130-146), the MSC's Screen_Tint showing only
# from the punch (148: the mean picture 146 -> 66, then fading to 160): the tint doesn't advance while the stage is
# frozen (Stage_Freeze), so the stop wasn't dark and the punch was. Effect_Camera (confirmed in game, unslowed) draws
# through the freeze: the darkening is the camera's quad now, from the connect's 0 to the punch (XV2's 44-58)
CAMERA_FX = True
FX_DARK_ID = 0x03410065
TINT = (0, 4, 0x14, 0x16, 0x2C, 0xB4, 0, 0xFF)  # slot 0, 4 frames in, R G B, A 0xB4, layer 0, priority (Sonic's FS's form)
TINT_OUT = 15
GLASS_SIZE, GLASS_Z = 0.36, 15.0    # the default glass: in front of the victim, toward the camera, XV2's scale
DARK_RGBA = (0.08, 0.09, 0.17, 0.7)  # the clip's dark blue-grey at 70%
DARK_Z, DARK_SIZE = 20.0, 2.2
GLASS_CAM_Z, GLASS_CAM_SIZE = 25.0, 0.1   # the shards (~140 x 100 units at x1 by their frame 49) over the screen at 25
# v5 (user: "the glass break effect on the punch is supposed to be clear and apply to the screen"; exe_v46z_camfx5's
# Effect_Camera confirmed in game): the glass on the camera in every build, Mode 1 (fixed to the screen), from the
# connect's frame 0 to the punch (XV2: BTL_CMN 108 at entry 4's 0, off at 16; the clip: the cracks over the stopped world
# 44-58, gone at the punch 59). Its pane (frames 0-8) is 38.6 x 28.8 units: GLASS_SCREEN_SIZE half screen heights a unit
# (3.67 x 2.74: over a 16:9 screen, 3.56 x 2). Clear: XV2 draws it with T1_VFX_MTN_REFRACT (DATA0.dds is a refraction
# offset map: drawn as a colour it was the user's yellow panes); Smash 4 has no screen refraction, so the shards' own
# outlines (each mesh's border edges, its UVs a planar projection of the pane) baked into its texture, light blue-white
# (XV2's MatCol0 0.5 / 0.8 / 1.0 lifted), the panes black: additive (the material's own blend), only the cracks show
GLASS_SCREEN_SIZE, GLASS_SCREEN_Z = 0.095, 20.0
GLASS_LINE_RGB, GLASS_PANE, GLASS_TEX_N, GLASS_LINE_W = (0.75, 0.9, 1.0), 0.03, 512, 2.0
GLASS_TEX = 0x15141F00
OUTLINE_A, OUTLINE_IN, OUTLINE_OUT = 110.0, 4, 10   # v3: the white outline; v4: FLASH (Color_Overlay) white at 110 of 255
# v5 (user: "the outline made Supamario glow harshly"): Smash 4 has no rim-only colour command (the ACMD events list: FLASH /
# FLASH_FRM / FLASH_NO_STOP / COL_NORMAL overlay the whole body; LIGHT_SHINE / LIGHT_AXIS are light sources), so the
# overlay much fainter and light blue-white
OUTLINE_A = 40.0
OUTLINE_RGB = (215.0, 230.0, 255.0)
# v6 (user: "the outline still turns Supamario into a glow instead of outlining him"; his v5 clip d8c96e8e 44-94: from
# the charge's first held frame his whole body goes light blue-white, opaque white by ~64, blooming to 94). The overlay
# is gone (OVERLAY_OUTLINE False): Smash 4's overlays tint the whole body, and Change_Overlay's fade ran on past its 40
# while the charge holds the motion's frame (MotionModule 0x2713 every frame), ~10 a frame (40 / 4) to 255. The
# outline is an effect now: XV2's BPE 85 draws a soft white glow just outside his silhouette (clip b66e8a38 8-41),
# so a soft white ring billboard on each body part's bone (OUTLINE_BONES: Mario's rest-pose part radii + OUTLINE_PAD),
# drawn at the bone's centre: the part's own front half hides the ring's inside, only the glow past his edge shows
OVERLAY_OUTLINE = False
# v7 (exe_v46z_outline, model_commands_v1: Outline_Set confirmed in game): v6's 16 ring billboards (PtcSupamarioTsOutline
# 0x0341006A) are gone. The outline is Outline_Set now: the fighter shaders' own rim term (g_fresnelOffset, per model
# instance), edge only (Tint 0): XV2's BPE 85 "Flashing White Body Outline 3".
#  - When (reference/xv2/timeskip_skill.json, flag word 2 = BPE 85's off form): BAC 0 on at 20 (the charge's start:
#    WIND_END), off at 100 (real 75: OL_OFF, the whiff's stop); BAC 2 (charged) on again at 100, off at 160 (its stop:
#    our charged dash is the same motion, so 75 too); BAC 4 (the connect) off at 16 (the punch). Clip b66e8a38: the rim
#    from 15-21 (faint at 15, clear by 21) through the dash (32-41) and the whole stop (46-58), gone under the punch's
#    white (59).
#  - Look (clip b66e8a38, the stop 46-50 against the dark world): a thin rim, 2-3 px at 1080p on his edge (plus a faint
#    +10-20 haze past it that Smash's rim can't draw), adding about (+55, +59, +58) / 255 to the background and taking
#    his dark hair's edge from ~10 to 120-142 (~0.45-0.5 of white at the very edge): a neutral white, faint.
#    OL_ALPHA 140 (0.55 of the colour at a fully edge-on pixel; the material's exponent 2-4 thins it inward).
#    The colour kept light blue-white (v5's 215, 230, 255).
#  - No pulse: the rim's peak is steady through the stop (46, 48, 50: +55-60 each frame) and the dash; the BAC holds no
#    rate (BPE 85's own entry is in XV2's system BPE file, not in the user's files). Flash 0.
#  - Ending it on every exit: Outline_Set is an ACMD command (the MSC can't send it), so the scripts renew it every
#    OL_KEEP frames, each held OL_HOLD frames (the catch's 3-frame freeze and its retries between the dash's last renewal
#    and the connect's first: up to ~10), then fading over OL_CUT_OUT: a cut move (a hit, a ledge, any status change)
#    leaves it at most OL_IN + OL_HOLD + OL_CUT_OUT frames (the hold counts once it is full; 18 at worst in the test's
#    model); a KO / the match's end / a training reset drop it at once (the cave).
#    A held charge keeps it: the scripts' clock runs on while the MSC holds the pose (MotionModule 0x2713; Core Breaker
#    v4's finding, the test model's), so the renewals go on through it, and the restart at WIND_END renews it again.
#    Normal ends: Alpha 0 at OL_OFF (out over OL_OUT) and at the punch (at once: XV2's off at 16, under the white
#    negative / flash)
OL_RGB = (215.0, 230.0, 255.0)
OL_ALPHA, OL_TINT, OL_FLASH = 140.0, 0.0, 0
OL_IN, OL_OUT, OL_PUNCH_OUT = 4, 4, 0
OL_KEEP, OL_HOLD, OL_CUT_OUT = 4, 12, 4
# v9 (user, v8: "looks good aside from the aura and lack of outline"; Outline_Set's rim is inside the silhouette and
# barely shows): the outline is Outline_Shell now (exe_v46z_outline4: model_commands v3), a band OUTSIDE his silhouette.
# Clip b66e8a38's rim is 2-3 px at 1080p plus a faint haze past it: OL_WIDTH 2.5 px of the 1280 x 720 picture (~3.75 at
# 1080p), added as a glow (OL_BLEND 1: XV2's outline brightens what is behind it) at OL_SH_ALPHA. Same timing (OL_*).
OL_WIDTH, OL_BLEND, OL_SH_ALPHA = 2.5, 1, 220.0
# The connect (the stop) runs under Screen_Invert's INV_STOP (Strength 1, Saturation 0, Brightness 0.8, + (19, 37, 60)):
# out = 0.8 - 0.8 x luma + add, so a white band (added) would come out dark; a BLACK band drawn over (Blend 0) comes out
# (223, 241, 255), the outline's own light blue-white. So the connect's outline is OL_INV_RGB over (screen_invert_cave
# filter_matrix; the test checks the band's colour through it).
OL_INV_RGB, OL_INV_BLEND = (0.0, 0.0, 0.0), 0
# v10 (user, v9 clip: "There's no blue tint and the glow is slightly too bright"; the stop's band "is persisting, it's
# just hardly noticeable because of the color"): added at 220, (215, 230, 255) saturated to white over most of the
# stage. Now OL_SH_RGB (150, 195, 255) at 165: over a mid grey (100) it comes out (197, 226, 255), a clear blue-white.
# The stop: black over came out (223, 241, 255), the brightest the greyed negative allows, and a dark stage's negative
# is light (Smashville at night: ~200 round him), so it barely showed. The stop's band is now white drawn over at
# OL_INV_ALPHA 230, which the negative turns dark navy (~35, 52, 75): a clear line on a light negative (the user had
# no preference between this, a thicker light band and a darker stop; a bright stage's negative is dark, where this
# line is faint).
OL_SH_RGB, OL_SH_ALPHA = (150.0, 195.0, 255.0), 165.0
OL_INV_RGB, OL_INV_ALPHA = (255.0, 255.0, 255.0), 230.0
OL_ON = WIND_END
OL_OFF = int(real0(100))            # 75
# v6 (user: "add XV2's photo-negative look after the punch"). XV2's BAC: BPE 78 "Invert World Colors" on at the connect's
# 0 (the dark blue-grey world of the stop, clip 44-58, the fighters not inverted), its second entry (flag word 2, BPE
# 85's off form) at 17: off again; BPE 2 "Weak White Flash" at 16. Measured on the clip's stage: during the charge
# (30-42) the ground (177, 193, 206), the stop (48-54) (72, 83, 100), after the punch (60-100) (220, 228, 235), back
# to (175, 193, 202) by 120: the "negative" after the punch is the stage's own pale colours washed ~55% white, not an
# inversion. Here: a white wash on the camera (Effect_Camera Mode 1) at the punch: WASH_FLASH over WASH_FLASH_N
# frames (BPE 2) on WASH_A held to the slow motion's end, faded out over WASH_OUT; INVERT_FX (the exe's Screen_Invert,
# another package) replaces the stop's tint by a real inversion once its command is known
INVERT_FX = True                    # v6 (coordinator: the user asked for the negative): Screen_Invert (screen_invert_v1,
                                    # exe_v46z_inv) for the stop and after the punch; False: the camera darkening + the wash
INV_STOP = (1, 1.0, STRIKE, 2, 4, 0.0, 0.8, 19.0, 37.0, 60.0)   # XV2's dark blue-grey stop (its example 1)
INV_WHITE = (1, 1.0, 34, 0, 14, 0.15, 0.35, 165.0, 170.0, 180.0)   # the white negative after the punch, held to +34, out
                                    # by +48 (the clip's white to +36, normal by +50); screen_invert's preset (Bright 0.6,
                                    # + (102, 104, 110)) brightened: the clip's world after the punch is (220, 228, 235),
                                    # the preset drew Smashville mid-grey (cmp_invert6): 0.65-1.0, low contrast
# v7 (the user's Screen_Invert test: partial strengths show grey, by design: a picture half way to its negative is flat).
# A fade shows (1 - w) x + w f(x): its contrast is 1 - w (1 + Brightness x Strength). v6's stop faded in over 2 (the
# flat grey at w 0.5) and, cut, out over 4; the white negative (contrast -0.35) out over 14 went flat at w = 1 / 1.35 =
# 0.74 (its 4th frame) and stayed a contrastless light grey (|contrast| < 0.3) for ~6 of the 14. Now every switch is
# straight on / off: the stop at once at the connect's 0 (XV2's BPE 78 is a cut: the clip's 44 -> 45), held to the punch
# (+ the catch's freeze and 2 frames: its own end if the move is cut, at once), replaced at once by the white negative,
# which the script ends at once at the punch's frame + INV_END (the punch's 30 frozen frames + 4: v6's +34) under a white
# quad on the camera fading out (FADE_*: alpha-blended white from FADE_A to 0 over FADE_N: the clip's white after the
# punch fading back to the stage by +50): the picture goes from the pale negative to the pale stage (the same mean
# brightness) and its contrast only rises (1 - alpha: 0.3 -> 1), never through grey. The white negative's own Frames
# (INV_WHITE_SAFE) ends it should the script not get there
INV_STOP = (1, 1.0, STRIKE + CATCH_FREEZE + 2, 0, 0, 0.0, 0.8, 19.0, 37.0, 60.0)
INV_END = 4
INV_WHITE_SAFE = STRIKE_FREEZE + INV_END + 4
INV_WHITE = (1, 1.0, INV_WHITE_SAFE, 0, 0, 0.15, 0.35, 165.0, 170.0, 180.0)
INV_OFF = (0, 0.0, 0, 0, 0, 1.0, 1.0, 0.0, 0.0, 0.0)
FX_FADE_ID = 0x0341006B
FADE_A, FADE_N = 0.7, 14            # the negative's mean ~0.84 (x 0.5) = 0.3 x 0.5 + 0.7 x 0.97: no step in brightness
FX_WASH_ID = 0x0341006A             # v7: the outline's set gone, the wash (INVERT_FX off only) moved up one
WASH_RGB, WASH_A, WASH_IN, WASH_LIFE, WASH_OUT = (0.94, 0.97, 1.0), 0.48, 2, 48, 14   # the clip: white to +36, normal by +50
WASH_FLASH, WASH_FLASH_N = 0.45, 8
WASH_Z, WASH_SIZE = 20.0, 2.2
# v6 (user: "use the real XV2 glass break / make it look less 2D"): the shards (HIT_DmgGrs2's 3D meshes and their .ema
# animation: flat to its frame 10, breaking apart from 12) kept on the screen past the punch, GLASS_BREAK frames of his
# script (his 30-frame hit freeze between: ~36 real frames of the shards flying apart, unslowed); each shard's pane
# lit by its own sheen (XV2 refracts each shard by its own offset: pale wedges over the stopped world), the cracks
# thinner with a highlight along one side
GLASS_BREAK = 6
GLASS_SHEEN = (0.03, 0.2)           # a shard's pane: low .. high (the narrow wedges brightest, as the clip's)
GLASS_LINE_W6, GLASS_HI = 1.5, 0.55
# v6 (user: "use Mario's normal landing lag animation after Time Skip falls from the air"): the 30 frames of
# LandingFallSpecial kept, LandingHeavy (motion 0x3B) played over them (func_586, Sledgehammer's LandingLight way)
LAG_ANIM = 300.0                    # TS_V_RETRY's mark while that landing starts
MOT_LANDING_HEAVY = 0x3B
# v6 (user: "fix the purple aura during the charging"): effect 0's streaks were capped at 0.32 (all but invisible in
# game under the overlay's white) and CrgAuraB took v5's Frt_Hit secondary lift (cyan-white). XV2 (clip 8-29): thin
# lavender streaks with white cores rising round him: E0_RGB / E0_CAP6; not replayed as the dash starts
E0_RGB = {'Frt_CrgAura.emp': (0.55, 0.33, 1.0), 'Frt_CrgAuraB.emp': (0.45, 0.28, 1.0), 'Frt_CrgAuraH.emp': (0.55, 0.33, 1.0)}
E0_B_LIFT, E0_B_ALPHA = 0.3, 0.4      # the alpha-blended CrgAuraB: its violet lifted 30% to white, at 40% of its alpha
E0_CAP6 = 0.34                      # supamario_fx_glow ts_e0: 0.6 lavender stacked to 8.6 square units of white on grass;
                                    # at 0.34 violet 0.5 white (grass) / 0.0 (grey), the picture changed 15.8 (v5 9.7)
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
            'TS_FX_FADE': '0x%X' % FX_FADE_ID, 'TS_FX_WASH': '0x%X' % FX_WASH_ID, 'TS_LAG_ANIM': fl(LAG_ANIM),
            'TS_MOT_LANDING_HEAVY': '0x%X' % MOT_LANDING_HEAVY,
            'TS_CAMFX': '1' if CAMERA_FX else '0', 'TS_TINT_SLOT': str(TINT[0]), 'TS_TINT_IN': str(TINT[1]),
            'TS_TINT_R': '0x%X' % TINT[2], 'TS_TINT_G': '0x%X' % TINT[3], 'TS_TINT_B': '0x%X' % TINT[4],
            'TS_TINT_A': '0x%X' % TINT[5], 'TS_TINT_OUT': str(TINT_OUT), 'TS_GLASS_SIZE': fl(GLASS_SIZE),
            'TS_GLASS_Z': fl(GLASS_Z),
            'TS_TRACK_STRONG': fl(TRACK_STRONG), 'TS_TRACK_SOFT': fl(round(math.radians(TRACK_SOFT), 6)),
            'TS_DRIFT': fl(DRIFT), 'TS_RETRY_N': fl(RETRY_N), 'TS_LAND_LAG': fl(LAND_LAG), 'TS_LAG_FLAG': fl(LAG_FLAG),
            'TS_ST_LANDING': fl(ST_LANDING), 'TS_ST_LANDFALL': '0x%X' % (ST_LANDING + 3)}
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


def timeline(events):
    """(frame, commands) pairs, in frame order (a stable sort: same-frame ones as given) -> one script: FRAME(f) before
    each later frame's commands"""
    out, at = [], 0
    for f, cmds in sorted(events, key=lambda e: e[0]):
        if f > at:
            out.append(cmd('frame', float(f)))
            at = f
        out += cmds
    return out


def effect_scripts():
    """XV2's Stage BG 60 (the stage's dust, at the dash's start BAC 56) as Smash's dash cloud on the ground. v4: skill
    effect 0's following part (Frt_CrgAuraH on the left elbow, x0.5) at frame 0; its world parts and effect 11 are the
    MSC's (ts_aura / ts_e11), as the strike's hit look and BTL_CMN 108 (the glass). v6: the white wash at the punch
    (wash_on: INVERT_FX off); the glass on GLASS_BREAK frames past the punch (its shards breaking apart). v7: the outline
    Outline_Set (XV2's BPE 85: from the charge's start OL_ON through the dash, renewed every OL_KEEP frames, off at the
    whiff's OL_OFF or at once at the punch); the white negative ended by the script at the punch + INV_END under the
    fading white quad (invert_end)"""
    dash = [(0, [cmd('external_graphic', FX_E0H_ID, E0_FOLLOW[1], 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                     E0_FOLLOW[2] * AURA_SIZE, 0)]),
            (MOVE_FROM, if_(0x0F000116, 0, 0, if_(V_PH, 5, DASHING, [
                cmd('graphic_effect', FX_DUST, 0, 0.0, 0.0, -2.0, 0.0, 0.0, 0.0, 1.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1)])))]
    dash += [(f, outline_on(OL_HOLD)) for f in range(OL_ON, OL_OFF, OL_KEEP)]
    dash += [(OL_OFF, outline_off(OL_OUT))]
    connect = [(0, (time_stop_look() if CAMERA_FX and not INVERT_FX else []) + invert_on() + glass_on_screen() +
                outline_on(OL_HOLD, True))]
    connect += [(f, outline_on(OL_HOLD, True)) for f in range(OL_KEEP, STRIKE, OL_KEEP)]
    connect += [(STRIKE, outline_off(OL_PUNCH_OUT) + wash_on() + invert_off()),
                (STRIKE + INV_END, invert_end()),
                (STRIKE + GLASS_BREAK, [cmd('terminate_graphic_effect', FX_GLASS_ID, 1, 1)])]
    return timeline(dash), timeline(connect)


def invert_on():
    """v6 INVERT_FX: XV2's BPE 78 at the connect's 0: Screen_Invert's dark blue-grey negative (INV_STOP). v7: at once,
    held to the punch + the catch's freeze + 2 (the punch replaces it); cut before the punch, it ends by itself at once"""
    return [cmd('screen_invert', *INV_STOP)] if INVERT_FX else []


def invert_off():
    """v6 INVERT_FX: at the punch the white negative (INV_WHITE) replaces the stop's at once. v7: ended by invert_end;
    its own Frames (INV_WHITE_SAFE, then at once) end it should the script not get there (no exit leaves it on)"""
    return [cmd('screen_invert', *INV_WHITE)] if INVERT_FX else []


def invert_end():
    """v7 INVERT_FX: the punch + INV_END (its frozen frames + 4: v6's +34 real frames): the white fade quad on the
    screen first (FX_FADE_ID: Effect_Camera Mode 1 as the wash, unslowed, FADE_A -> 0 over FADE_N real frames), then
    the white negative off at once (Mode 0, FadeOut 0): the cut from the negative to the stage under the white, which
    fades back to the stage (no fade through grey)"""
    if not INVERT_FX:
        return []
    return [cmd('effect_camera', FX_FADE_ID, 0.0, 0.0, WASH_Z, 0.0, 0.0, 0.0, WASH_SIZE, 1, 0, 1),
            cmd('screen_invert', *INV_OFF)]


def wash_on():
    """v6: the white wash at the punch (wash_set), on the screen, unslowed (its own fade: WASH_LIFE real frames); not
    with INVERT_FX (the filter would turn the white quad dark: the white negative is Screen_Invert's)"""
    if INVERT_FX:
        return []
    return [cmd('effect_camera', FX_WASH_ID, 0.0, 0.0, WASH_Z, 0.0, 0.0, 0.0, WASH_SIZE, 1, 0, 1)]


def time_stop_look():
    """v3: the time stop on the camera at the connect's frame 0: the darkening (to the punch, then faded) and the glass.
    v5: the darkening only in the camera build (CAMERA_FX); the glass is glass_on_screen's in every build"""
    return [cmd('effect_camera', FX_DARK_ID, 0.0, 0.0, DARK_Z, 0.0, 0.0, 0.0, DARK_SIZE, 1, STRIKE, 1)]


def glass_on_screen():
    """v5: the glass (its cracks) fixed to the screen (Effect_Camera Mode 1, unslowed) from the connect's frame 0, ended
    at the punch (XV2 turns BTL_CMN 108 off at 16; the clip: gone at the punch); every exit before it: ts_stop_look_off"""
    return [cmd('effect_camera', FX_GLASS_ID, 0.0, 0.0, GLASS_SCREEN_Z, 0.0, 0.0, 0.0, GLASS_SCREEN_SIZE, 1, 0, 1)]


# ---------------------------------------------------------------- the outline: its only two commands
# v8: every outline command of both scripts comes from outline_on / outline_off (effect_scripts only decides when): to
# move to another outline mode or command, change these two (and OL_*); the test reads its expected commands from them
OUTLINE_CMD = 'outline_shell'


def outline_on(frames, inverted=False):
    """v3 (user: "Time Skip wraps the user in a faint white translucent glowing outline"; XV2's BPE 85 "Flashing White
    Body Outline 3", BAC entry 0 at 20 and 100, entry 4 at the punch). v3: a light (LIGHT_SHINE), v4 / v5 the colour
    overlay (FLASH): both tint the whole body; v6: 16 ring billboards on his bones (an effect-only rim). v7: Outline_Set
    (exe_v46z_outline): his own edges lit (the shaders' rim), edge only (Tint 0), OL_RGB at OL_ALPHA, steady (Flash 0),
    in over OL_IN (a renewal fades from where it is: none once on), held `frames`, then out over OL_CUT_OUT if not
    renewed (a cut move).
    v9: Outline_Shell (exe_v46z_outline4): a band OL_WIDTH pixels wide outside his silhouette, OL_RGB added at
    OL_SH_ALPHA (Blend OL_BLEND), the same timing; `inverted` (the connect, under Screen_Invert's stop): OL_INV_RGB
    drawn over (Blend OL_INV_BLEND) at OL_INV_ALPHA; v10: OL_SH_RGB, and white over in the stop (dark navy through the
    negative)"""
    if OUTLINE_CMD == 'outline_shell' and inverted and INVERT_FX:
        return [cmd(OUTLINE_CMD, 0, *OL_INV_RGB, OL_INV_ALPHA, OL_WIDTH, int(frames), OL_IN, OL_CUT_OUT, OL_FLASH,
                    OL_INV_BLEND)]
    if OUTLINE_CMD == 'outline_shell':
        return [cmd(OUTLINE_CMD, 0, *OL_SH_RGB, OL_SH_ALPHA, OL_WIDTH, int(frames), OL_IN, OL_CUT_OUT, OL_FLASH,
                    OL_BLEND)]
    return [cmd(OUTLINE_CMD, 0, *OL_RGB, OL_ALPHA, OL_TINT, int(frames), OL_IN, OL_CUT_OUT, OL_FLASH)]


def outline_off(fade):
    """v7: Outline_Set's end (Alpha 0) over `fade` frames; v9 Outline_Shell's"""
    if OUTLINE_CMD == 'outline_shell':
        return [cmd(OUTLINE_CMD, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, int(fade), 0, 0)]
    return [cmd(OUTLINE_CMD, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, int(fade), 0)]


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
        wash = wash_set(p, e, sets['hitl']['set_index'])         # 0x6A (v6; v7: the outline's rings 0x6A gone)
        fade = fade_set(p, e, sets['hitl']['set_index'])         # 0x6B (v7)
    finally:
        xv2_to_ptcl.TEX_MAX, xv2_to_ptcl.CONE_STREAKS = old
        xv2vfx.LENIENT_TARGETS = False
    out = p.build()
    assert ptcl.Ptcl(out).validate() == []
    open(os.path.join(fx_dir, base + '.ptcl'), 'wb').write(out)
    open(os.path.join(fx_dir, base + '.efc'), 'wb').write(e.build())
    bad = FX.facing_emitters(p, [s['set_index'] for s in sets.values()] + [lod['set_index']])
    return {'sets': sets, 'skipped': log, 'notes': notes, 'halos': halos, 'ptcl_bytes': [before, len(out)],
            'facing_problems': bad, 'lod': lod, 'e11': e11, 'aura': e0,
            'e0_follow': e0h, 'glass': glass, 'dark': dark, 'wash': wash, 'fade': fade,
            'outline': {'command': acmd.INFO[acmd.BY_NAME[OUTLINE_CMD]]['name'],
                        'rgb': OL_SH_RGB if OUTLINE_CMD == 'outline_shell' else OL_RGB, 'stop_rgb': OL_INV_RGB,
                        'stop_alpha': OL_INV_ALPHA,
                        'alpha': OL_SH_ALPHA if OUTLINE_CMD == 'outline_shell' else OL_ALPHA, 'tint': OL_TINT,
                        'width': OL_WIDTH, 'blend': OL_BLEND, 'flash': OL_FLASH,
                        'on': OL_ON, 'off': OL_OFF, 'keep': OL_KEEP, 'hold': OL_HOLD, 'in': OL_IN, 'out': OL_OUT,
                        'cut_out': OL_CUT_OUT, 'punch_out': OL_PUNCH_OUT}}


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
                    em, name, notes = X.convert_emission(p, pkg, images, c, FX.UNIT, n['Name'], spawn)
                    out.append((em, name, notes + _secondary(p, em, n, emp, images)))
            walk(n['ChildParticleNodes'], c)
    walk(emp['ParticleNodes'], [])
    return out, log


def _secondary(p, em, node, emp, images):
    """XV2's secondary colour (EnableSecondaryColor: Color2 over the texture's bright core, Color1 its edges; the
    converter keeps Color1 alone) on the normal-blend emissions: Frt_Hit's dark navy waves / backing lines ((0, 0,
    0.5) / (0, 0, 0.2) to white) would draw as dark smudges over the stage; the clip shows them blue-violet with light
    cores. Their colour the mean of Color1 and Color2, x the texture's tint (the converter's way), both tracks"""
    import xv2_to_ptcl as X
    tex = node['EmissionNode'].get('Texture') or {}
    if 'EnableSecondaryColor' not in node['NodeFlags_names'] or p.field(em, 'blend_type') != 0 or 'Color2' not in tex:
        return []
    refs = [r for r in tex.get('TextureEntryRef', []) if r is not None and r >= 0]
    smp = emp['Textures'][refs[0]] if refs else None
    img = images.get(smp['TextureRef']) if smp else None
    tint = X.shape_texture(X.first_cell(img, smp))[1] if img is not None else (1.0, 1.0, 1.0)
    rgb = tuple(float((a + b) / 2.0 * t) for a, b, t in zip(tex['Color1'], tex['Color2'], tint))
    note = 'secondary colour mixed: (%.2f, %.2f, %.2f)' % rgb
    if SECONDARY_V5:
        # v5 (the user: XV2's burst is big translucent violet flames; v4's were deep blue and opaque in game): XV2 draws
        # these on its white time-stop world as lilac at part alpha: Color2 x the tint lifted halfway to white, alpha x
        # SECONDARY_ALPHA; a black pair (wave_nml_4's thin black spikes, not seen in the screenshots) at x BLACK_ALPHA
        c2 = [float(b * t) for b, t in zip(tex['Color2'], tint)]
        black = max(tex['Color2']) < 0.05 and max(tex['Color1']) < 0.05
        rgb = tuple(c + (1.0 - c) * SECONDARY_LIFT for c in c2) if not black else (0.0, 0.0, 0.0)
        f = BLACK_ALPHA if black else SECONDARY_ALPHA
        note = 'secondary colour (v5): (%.2f, %.2f, %.2f), alpha x%.2f' % (rgb + (f,))
    for track in (0, 1):
        p.set_color_keys(em, track, [rgb + (1.0,)])
    return [note]


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


def _cone_alpha(p, d, pkg, emp, name):
    """v4: a ConeExtrude streak's alpha (effect 0's stripes: 0 -> 0.6 at 5% of the head's life -> 0 at 40%, the ribbon
    staying on after its head): eft's 3-key ramp can't fall by 40%, and the converter's least-squares fit (0 -> 0.3 at
    5% -> 0 at 100%) drew it at half; and hdr_emitter's alpha x2 (xv2_smash_fx.ALPHA, XV2's glare) only reaches
    alpha_init (0 here). Now 0 -> the peak x ALPHA (at most 1) at 5%, held to 15%, -> 0 at 100%"""
    import xv2_smash_fx as FX
    import xv2vfx
    node = next(n for _d, n in xv2vfx.emp_nodes(pkg['emp'][emp]) if n.get('Name') == name and n['NodeType'] == 'Emission')
    if node['NodeSpecificType'] != 'ConeExtrude':
        return ''
    ks = [k['Value'] for kv in node['KeyframedValues'] if kv['Target'] == 'Color1_Transparency' for k in kv['Keyframes']]
    a = min(1.0, max(ks or [node['EmissionNode']['Texture']['Color1_Transparency']]) * FX.ALPHA)
    for k, v in (('alpha_init', 0.0), ('alpha_diff21', a), ('alpha_diff32', -a), ('alpha_section1', 0.05),
                 ('alpha_section2', 0.15)):
        p.set_field(d, k, v)
    return '; streak alpha 0 -> %.2f (5-15%%) -> 0' % a


def _e0_colour(p, d, emp):
    """v6: effect 0's streaks lavender (E0_RGB: XV2's clip, its glare's violet over white cores) at E0_CAP6 (v4 / v5:
    the glare tint capped at 0.32, CrgAuraB v5's secondary lift: pale cyan, all but invisible in game)"""
    rgb = E0_RGB[emp]
    f = E0_CAP6 / max(rgb)
    if p.field(d, 'blend_type') == 0:
        # an alpha-blended streak (CrgAuraB: XV2's normal blend) can't be dimmed by its colour (it would draw dark):
        # light violet, translucent
        f = 1.0
        rgb = tuple(c + (1.0 - c) * E0_B_LIFT for c in rgb)
        for k in ('alpha_diff21', 'alpha_diff32'):
            p.set_field(d, k, p.field(d, k) * E0_B_ALPHA)
    for track in (0, 1):
        p.set_color_keys(d, track, [tuple(c * f for c in rgb) + (1.0,)])
    p.set_field(d, 'color_scale', 1.0)
    return '; v6 colour (%.2f, %.2f, %.2f)' % tuple(c * f for c in rgb)


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
        if name in SPARKS:
            p.set_field(d, 'scale', [v * SPARK_GROW for v in p.field(d, 'scale')])
            n0 = n0 + ['v5: x%g (the sparkle dots visible at Smash\'s camera)' % SPARK_GROW]
        notes.append('%s: %s; %s' % (name, '; '.join(n0), _vibrant(p, d, mats, E11_EMP, name, E11_CAP)))
        sec = [x for x in n0 if x.startswith('secondary colour (v5)')]
        if sec:                         # v5: the translucent flames' alpha, after hdr_emitter's x2
            f = float(sec[0].rsplit('x', 1)[1])
            for k in ('alpha_init', 'alpha_diff21', 'alpha_diff32'):
                p.set_field(d, k, p.field(d, k) * f)
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
            notes.append('%s %s at %s: %s; %s%s%s' % (emp, name, bone, '; '.join(n0),
                                                      _vibrant(p, d, mats, emp, name, E0_CAP),
                                                      _cone_alpha(p, d, pkg, emp, name), _e0_colour(p, d, emp)))
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
    by the effect script at the bone's place (External_Graphic's last word 0: its place only, not its turn: XV2's
    Orientation User), its particles following (XV2's PositionUpdate), rising as XV2's"""
    import supamario_sledgehammer_build as SB
    import xv2_smash_fx as FX
    pkg, images, mats = _frt_pkg(frt_dir)
    emp = E0_FOLLOW[0]
    made, _log = frt_emissions(p, pkg, images, emp)
    ems, notes = [], []
    for d, name, n0 in made:
        d = bytearray(d)
        notes.append('%s: %s; %s%s%s' % (name, '; '.join(n0), _vibrant(p, d, mats, emp, name, E0_CAP, world=False),
                                         _cone_alpha(p, d, pkg, emp, name), _e0_colour(p, d, emp)))
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
    texture made solid white), DARK_RGBA, one particle that lives until the call's Frames fade it, follow type 0 (it
    moves with the camera); v8: _screen_quad's size (QUAD_W) and no spin"""
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
    _screen_quad(p, d)                                  # v8: QUAD_W across, no spin; follow 0 (moves with the camera)
    si = p.new_set('PtcSupamarioTsDark', [bytes(d)], ['dark'])
    idx = e.add(si + 1)
    assert 0x03410000 | idx == FX_DARK_ID, ('FX_DARK_ID is out of date', hex(0x03410000 | idx))
    return {'set': 'PtcSupamarioTsDark', 'set_index': si, 'efc': idx, 'id': '0x%08X' % FX_DARK_ID, 'rgba': DARK_RGBA}


# v8 (the user's v7 clip 869ac5f5, 156-171: "a rotating square appears during / after the punch"): the fade quad drew as
# a white square about 1.1 screen heights wide (64% of the screen's width), turning a little each frame. Two things kept
# from Btl_HitL's flash_1, the converted emitter every screen quad here is cut from: its random spin
# (rotation_velocity_random Z 0.035 rad = 2 degrees a frame; v6 / v7 zeroed rotation_velocity only) and its scale 1,
# which is 1 unit across, not 2 (Effect_Camera Mode 1: a particle W wide is W x Size / 2 screen heights): at Size 2.2
# it was 1.1 screen heights. Every screen quad (the fade, the wash, the darkening) now: QUAD_W 2 units (-1 to 1: 2.2
# screen heights at Size 2.2, over a 16:9 screen's 1.78), no turn of any kind, no camera offset, the alpha keys only
QUAD_W = 2.0


def _screen_quad(p, d):
    """v8: a screen-filling quad's emitter fields: QUAD_W across, no rotation (initial, random, velocity, random
    velocity), no camera offset / drag / interval spread; follow type 0 (it moves with its set, so with the camera)"""
    import struct
    for name, v in (('scale', [QUAD_W, QUAD_W]), ('scale_random', [0.0, 0.0]), ('scale_init_ratio', [1.0, 1.0]),
                    ('scale_diff21', [0.0, 0.0]), ('scale_diff32', [0.0, 0.0]), ('rotation_init', [0.0, 0.0, 0.0]),
                    ('rotation_random', [0.0, 0.0, 0.0]), ('rotation_velocity', [0.0, 0.0, 0.0]),
                    ('rotation_velocity_random', [0.0, 0.0, 0.0]), ('camera_offset', 0.0), ('air_resistance', 1.0),
                    ('emit_interval_random', 0), ('velocity_stretch', 0.0)):
        p.set_field(d, name, v)
    struct.pack_into('>I', d, 0x310, 0)


def _quad(p, hitl_si, rgb, a, life):
    """v6: an alpha-blended (or additive) billboard from Btl_HitL's flash_1 (dark_set's way): one particle, `life`
    frames (0: forever), colour rgb, constant alpha a, follow type 0. v8: _screen_quad's (QUAD_W across, no spin)"""
    src = next(em['data'] for em in p.sets[hitl_si]['emitters'] if em['data'] is not None and
               p.emitter_name(em['data']) == 'flash_1')
    d = bytearray(src)
    for name, v in (('one_time', 1), ('end_frame', 1), ('emit_rate', 1.0), ('emit_interval', 0), ('start_frame', 0),
                    ('emit_start', 0), ('volume_type', 0), ('volume_radius', [0.0, 0.0, 0.0]), ('figure_velocity', 0.0),
                    ('init_velocity_random', 0.0), ('emitter_velocity', 0.0), ('dispersion_angle', 0.0),
                    ('gravity', [0.0, 0.0, 0.0]), ('ptcl_life', life or 0x7FFFFFFF), ('ptcl_life_random', 0),
                    ('scale', [1.0, 1.0]), ('scale_random', [0.0, 0.0]), ('scale_init_ratio', [1.0, 1.0]),
                    ('scale_diff21', [0.0, 0.0]), ('scale_diff32', [0.0, 0.0]), ('rotation_init', [0.0, 0.0, 0.0]),
                    ('rotation_random', [0.0, 0.0, 0.0]), ('rotation_velocity', [0.0, 0.0, 0.0]),
                    ('alpha_init', a), ('alpha_diff21', 0.0), ('alpha_diff32', 0.0), ('color_scale', 1.0)):
        p.set_field(d, name, v)
    p.set_key_anims(d, [])
    p.set_emitter_srt(d)
    for track in (0, 1):
        p.set_color_keys(d, track, [tuple(rgb) + (1.0,)], 0)
    _screen_quad(p, d)
    return d


def _ramp(p, d, a, t_in, t_out, life):
    """alpha 0 -> a over t_in frames, held, -> 0 over the last t_out of `life` (eft's 3 keys)"""
    for k, v in (('alpha_init', 0.0), ('alpha_diff21', a), ('alpha_diff32', -a),
                 ('alpha_section1', t_in / float(life)), ('alpha_section2', (life - t_out) / float(life))):
        p.set_field(d, k, v)


def wash_set(p, e, hitl_si):
    """v6: the white wash after the punch (WASH_*): a white quad on the camera (Effect_Camera Mode 1, unslowed), alpha
    0 -> WASH_A over WASH_IN, held, out over the last WASH_OUT of WASH_LIFE real frames; a second quad the punch's flash
    (XV2's BPE 2: WASH_FLASH, out over WASH_FLASH_N). Alpha blended: it whitens, never past white (no bloom)"""
    import numpy as np
    wash = _quad(p, hitl_si, WASH_RGB, WASH_A, WASH_LIFE)
    _ramp(p, wash, WASH_A, WASH_IN, WASH_OUT, WASH_LIFE)
    flash = _quad(p, hitl_si, WASH_RGB, WASH_FLASH, WASH_FLASH_N)
    _ramp(p, flash, WASH_FLASH, 1, WASH_FLASH_N - 1, WASH_FLASH_N)
    for d in (wash, flash):
        assert p.field(d, 'blend_type') == 0
        p.set_texture(d, 0, np.full((16, 16, 4), 255, np.uint8))
    si = p.new_set('PtcSupamarioTsWash', [bytes(wash), bytes(flash)], ['wash', 'flash'])
    idx = e.add(si + 1)
    assert 0x03410000 | idx == FX_WASH_ID, ('FX_WASH_ID is out of date', hex(0x03410000 | idx))
    return {'set': 'PtcSupamarioTsWash', 'set_index': si, 'efc': idx, 'id': '0x%08X' % FX_WASH_ID,
            'rgb': WASH_RGB, 'alpha': WASH_A, 'flash': WASH_FLASH, 'life': WASH_LIFE}


def fade_set(p, e, hitl_si):
    """v7 (INVERT_FX): the white quad that covers the white negative's cut (invert_end): alpha-blended (0.94, 0.97, 1)
    from FADE_A straight down to 0 over FADE_N real frames (eft's 3 keys: FADE_A at 0, held to 0, -> 0 at the end)"""
    import numpy as np
    d = _quad(p, hitl_si, WASH_RGB, FADE_A, FADE_N)
    for k, v in (('alpha_init', FADE_A), ('alpha_diff21', 0.0), ('alpha_diff32', -FADE_A), ('alpha_section1', 0.0),
                 ('alpha_section2', 0.0)):
        p.set_field(d, k, v)
    assert p.field(d, 'blend_type') == 0
    p.set_texture(d, 0, np.full((16, 16, 4), 255, np.uint8))
    si = p.new_set('PtcSupamarioTsFade', [bytes(d)], ['fade'])
    idx = e.add(si + 1)
    assert 0x03410000 | idx == FX_FADE_ID, ('FX_FADE_ID is out of date', hex(0x03410000 | idx))
    return {'set': 'PtcSupamarioTsFade', 'set_index': si, 'efc': idx, 'id': '0x%08X' % FX_FADE_ID, 'rgb': WASH_RGB,
            'alpha': FADE_A, 'life': FADE_N}


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
    cracks = glass_cracks(os.path.join(fx_dir, 'model', folder))
    inv = glass_invert(os.path.join(fx_dir, 'model', folder)) if INVERT_FX else None
    if inv:
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'xv2_to_nud.py'), 'verify',
                            os.path.join(fx_dir, 'model', folder)], capture_output=True, text=True)
        assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
    idx = e.add(0, folder)
    assert 0x03410000 | idx == FX_GLASS_ID, ('FX_GLASS_ID is out of date', hex(0x03410000 | idx))
    return {'folder': folder, 'efc': idx, 'id': '0x%08X' % FX_GLASS_ID, 'cracks': cracks,
            'sheens': getattr(glass_cracks, 'sheens', []), 'inverted': inv}


def glass_cracks(folder):
    """v5: the glass's texture made of its shards' outlines (GLASS_*): each mesh's border edges (edges of one triangle
    only), drawn in UV space (the UVs are a planar projection of the pane, wrapped: frac), in GLASS_LINE_RGB; the rest
    GLASS_PANE (a faint sheen). v6 (user: "less 2D"): each shard's pane its own sheen (GLASS_SHEEN: the narrow wedges
    brightest, XV2's refraction showing them as pale wedges), the cracks GLASS_LINE_W6 wide, lit on the side facing the
    upper left (full) and GLASS_HI on the others (a bevel). model.nut rewritten (BC1); returns the line count"""
    import numpy as np
    import nud
    import nut
    from PIL import Image, ImageDraw
    n = GLASS_TEX_N
    fill = Image.new('L', (n, n), int(255 * GLASS_PANE))
    lines_im = Image.new('L', (n, n), 0)
    df, dl = ImageDraw.Draw(fill), ImageDraw.Draw(lines_im)
    lines = 0
    rng = np.random.RandomState(1352)
    sheens, shards = [], []
    for m in nud.read(os.path.join(folder, 'model.nud')):
        for pg in m.polygons:
            uv = np.array(pg.uvs, float).reshape(len(pg.pos), -1)[:, :2] * [n, n] + [0.0, n]   # V -1 .. 0 -> 0 .. n
            idx = list(pg.idx)
            cnt = {}
            area = 0.0
            for k in range(0, len(idx) - 2, 3):
                tri = idx[k:k + 3]
                pa, pb, pc = uv[tri[0]], uv[tri[1]], uv[tri[2]]
                area += abs((pb[0] - pa[0]) * (pc[1] - pa[1]) - (pc[0] - pa[0]) * (pb[1] - pa[1])) / 2.0
                for a_, b_ in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
                    key = (min(a_, b_), max(a_, b_))
                    cnt[key] = cnt.get(key, 0) + 1
            border = [k for k, c in cnt.items() if c == 1]
            per = sum(float(np.hypot(*(uv[a_] - uv[b_]))) for a_, b_ in border)
            thin = per * per / (4.0 * math.pi * max(area, 1e-6))          # 1 a disc; the slivers 5-20
            shards.append((thin + rng.rand(), uv, idx))
            cen = uv[list({j for e_ in border for j in e_})].mean(0) if border else uv.mean(0)
            for a_, b_ in border:
                pa, pb = uv[a_], uv[b_]
                nrm = np.array([pb[1] - pa[1], -(pb[0] - pa[0])])          # the edge's normal, turned outward
                if np.dot(nrm, (pa + pb) / 2 - cen) < 0:
                    nrm = -nrm
                lit = np.dot(nrm / (np.linalg.norm(nrm) + 1e-9), [-0.7071, -0.7071]) > 0   # faces the upper left
                dl.line([tuple(pa), tuple(pb)], fill=255 if lit else int(255 * GLASS_HI),
                        width=max(1, int(round(GLASS_LINE_W6))))
                lines += 1
    # the panes by rank of thinness (+ a random 0-1): the slivers brightest, spread over GLASS_SHEEN
    order = sorted(range(len(shards)), key=lambda k: shards[k][0])
    for rank, k in enumerate(order):
        _t, uv, idx = shards[k]
        v = GLASS_SHEEN[0] + (GLASS_SHEEN[1] - GLASS_SHEEN[0]) * (rank / max(1, len(shards) - 1)) ** 1.5
        sheens.append(round(v, 3))
        for j in range(0, len(idx) - 2, 3):
            df.polygon([tuple(uv[i]) for i in idx[j:j + 3]], fill=int(255 * v))
    a = np.maximum(np.asarray(fill, np.float32), np.asarray(lines_im, np.float32)) / 255.0
    rgb = (a[..., None] * np.array(GLASS_LINE_RGB, np.float32) * 255 + 0.5).astype(np.uint8)
    img = np.concatenate([rgb, np.full((n, n, 1), 255, np.uint8)], 2)
    tid = nut.load(os.path.join(folder, 'model.nut'))[1][0].tex_id     # the converter's own texture ID
    open(os.path.join(folder, 'model.nut'), 'wb').write(nut.write_ntwu([(tid, 0x31, img)]))
    glass_cracks.sheens = sheens
    glass_cracks.alpha = a
    return lines


def glass_invert(folder):
    """v6, INVERT_FX: Screen_Invert turns the whole 3D picture, the glass in it, into a negative, so additive light
    cracks would show dark. Drawn pre-inverted instead: alpha-blended (NUD src 5 / dst 1, the converter's normal
    blend) black, the cracks / panes in the alpha (BC3): under the stop's filter (0.8 x the negative's luma + (19, 37,
    60)) black comes out (0.87, 0.95, 1.0), the light blue-white of v5's cracks; the header's sphere kept"""
    import struct
    import numpy as np
    import nud
    import nut
    path = os.path.join(folder, 'model.nud')
    raw = open(path, 'rb').read()
    meshes = nud.read(path)
    for m in meshes:
        for pg in m.polygons:
            for mat in pg.materials:
                mat.src, mat.dst = 5, 1
    data = bytearray(nud.write(meshes))
    data[0x20:0x30] = raw[0x20:0x30]
    open(path, 'wb').write(bytes(data))
    a = glass_cracks.alpha
    img = np.zeros(a.shape + (4,), np.uint8)
    img[..., 3] = (np.clip(a, 0.0, 1.0) * 255 + 0.5).astype(np.uint8)
    tid = nut.load(os.path.join(folder, 'model.nut'))[1][0].tex_id
    open(os.path.join(folder, 'model.nut'), 'wb').write(nut.write_ntwu([(tid, 0x33, img)]))
    return {'blend': [5, 1], 'texture': 'BC3 black, the cracks in the alpha'}


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
