#!/usr/bin/env python3
"""Supamario's Ultra Instinct v1 (his gimmick; Dragon Ball Xenoverse 2's Awoken Skill 1510_GKS_MGT, "Ultra Instinct
-Sign-"): the package, built over Time Skip's (tools/supamario_timeskip_build.py, which runs Sledgehammer's, Fake
Death's, Core Breaker's and the Super God Fist's first; their files stay theirs: only the three motion slots' motions /
scripts, the new effect sets, three new sounds and the MSC change).

  python3 -I tools/supamario_ui_build.py SUPAMARIO_DIR OUT_DIR --ui-skill 1510_GKS_MGT_DIR --ui-se-wav WAV_DIR
        [Time Skip's: --ts-skill ... --ts-se-wav ... --frt-skill ... --sh-skill ... --sh-se-wav ... --fd-skill ...
        --fd-se-wav ... --skill ... --se-wav ... --ean ... --cmn-vfx VFX_CMN_DIR --skill-vfx ... --cmn-se ... --stb ...]
        [--png SHEET.png]

--ui-skill: XV2's data/skill/MET/1510_GKS_MGT (the .ean; the .bac / _PLAYER.bcm / .bdm the timings and the counter's
rules come from: fighters/supamario/README.md "Ultra Instinct v1", read with tools/xv2bac.py). --ui-se-wav: the skill SE bank CAR_BTL_M1510_MGT_SE.acb's cues 0 / 1 and CAR_BTL_CMN.acb's
cue 96 "Vanish", levelled (tools/xv2acb.py extract + tools/xv2acb_decode.mjs + tools/supamario_timeskip_xv2.py se).
--cmn-vfx: XV2's vfx/cmn (BTL_AURA.eepk: the skill's effects 846-851 with the Ultra Instinct aura; BTL_CMN.eepk:
effect 82, the vanish's lines).
Writes OUT_DIR/fighter/supamario (Time Skip's build, then): motion/body (SpecialLwLight 0x231 = the transformation,
SpecialLwHeavy 0x235 = the counter, SpecialAirLwLight 0x241 = the autododge, SpecialAirLwHeavy 0x245 = Secret
Sensation's stance: tools/supamario_ui_anim.py),
script/animcmd/body (their game / effect / sound / expression scripts), effect/supamario (the converted sets after
every earlier one), sound (UI_SE in his bank, the soundlabeltable's row grown), script/msc (supamario.c's ui_*),
OUT_DIR/ultrainstinct.json.
The executable is tools/supamario_ui_cave.py's (exe_v46z_ui).

The move: fighters/supamario/README.md "Ultra Instinct v1".
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import mesh_vis_cave as MV  # noqa: E402
import supamario_ui_anim as anim  # noqa: E402
import supamario_ui_cave as cave  # noqa: E402
import supamario_ui_model as model  # noqa: E402

# ---------------------------------------------------------------- the rules (the user's spec)
TRIGGER_PCT = 100.0                  # his first actionable frame at 100% or more
FORM_N = anim.frames_of(anim.FORM)   # 60: the transformation (XV2 entry 0's 0-229, the user's "about 60 frames")
STRIKE_N = anim.frames_of(anim.STRIKE)          # 349: XV2's BAC 1 from 151 to 499, 1:1
STRIKE_AT = anim.frame_of(anim.STRIKE, 1, 280)     # 129: the finisher (BDM #2)
# v2 (the user's XV2 clip of the counter: the attacker held in front of him, 14 strike flashes, the finisher, 15 hits):
# XV2's rush entry. The BCM: the five roots share their conditions; roots #1 / #4 / #7 play BAC 4 (counter children
# BAC 5 / 6: the finisher alone), #10 BAC 8 (-> 9 / 10) and #13 BAC 0 (-> 1 / 2: the rush). The clip shows the rush, and
# BAC 0 is the stance with entry 4's functions (0x5C / 0x21, as the player's), so BAC 1 (root #13's first child:
# CounterMelee + 0x400000) is used; BAC 2 differs only by function 0x2B (100) at 151.
# BAC 1, from 151 (motion frame = XV2 - 151): BDM #0 at 0 (the hold), the vanish (BTL_CMN 82, CMN SE 96), Movement to the
# target 156-176 + 2.5 m a frame 159-161 (here: a gap closed only, ui_gap), 82 again at 170, the aura (848) at 176, the
# rush BDM #1 (5 each, hitstop 0 / 2) at 210, 215 .. 275, the finisher BDM #2 (10, type 7 launch, hitstop 7 / 7) at 280,
# skill SE cue 1 at 335, the end effects (850 / 849) at 350, invulnerable throughout.
RUSH_AT = [anim.frame_of(anim.STRIKE, 1, f) for f in range(210, 280, 5)]   # 59, 64 .. 124
# Damage (XV2's numbers are its own scale): Core Breaker's conversion (the user's, README "Core Breaker"): XV2's dive 10
# -> 3%, its 9-damage hold hits -> 1.5% each, its 405 crash -> 17%. So the rush's 5s -> RUSH_DMG each (under the 9s'
# 1.5) and the finisher's 10 -> FINISH_DMG (a launch, more than the dive's 3: it ends the combo): 14 x 1.2 + 8 = 24.8%
RUSH_DMG, FINISH_DMG = 1.2, 8.0
GAP_FROM, GAP_TO = anim.frame_of(anim.STRIKE, 1, 156), anim.frame_of(anim.STRIKE, 1, 161)
GAP_V = round(2.5 * 5.04, 2)         # XV2's 2.5 m a frame
RUSH_REACH = 9.0                     # the attacker this far in front of him at most after the gap's close
CW_ON = anim.frame_of(anim.FORM, 0, 30)
CW_OFF = anim.frame_of(anim.FORM, 0, 151)
FREEZE_SIZE = round(3.0 * 5.04, 2)   # BDM #0's 3 m sphere
STRIKE_HIT = dict(Angle=35, KBG=75, FKB=0, BKB=80)
STRIKE_SIZE, STRIKE_Y, STRIKE_Z = 6.0, 7.0, 7.0
RUSH_SIZE, RUSH_Y, RUSH_Z = 6.0, 7.0, 7.0
# v2: the white body (XV2's ECF 846 / 847 / 849: the whole model bright white with a blue-white rim, from the gold burst
# at 10 to the purple-white burst at 220; the counter keeps it to its 350): Color_Overlay white WHITE_A, Outline_Shell
# RIM_RGB at RIM_A (added, RIM_WIDTH px), Terminate_Overlays / the shell's end at the burst
WHITE_RGB, WHITE_A = (255.0, 255.0, 255.0), 200.0
RIM_RGB, RIM_A, RIM_WIDTH = (190.0, 215.0, 255.0), 200.0, 2.5
GAP = 9.0                            # beside the fighter to answer: this far on his side of it
GROUND_DY = 6.0                      # its feet within this of his: on the ground, the X only
DODGE_N = 16                         # v1-v6's dodge (EAN #1 151-167); v7: the sway below
DODGE_INV = 12                       # the user: invincible ~12 frames, then actionable
DODGE_MOVE, DODGE_V = 4, 1.0         # v2 (the user's XV2 clip: a sway almost in place): 4 units away over 4 frames (v1: 16
                                     # over 8); XV2's own dodge motion / afterimage are not in the skill's files
# v7 (the user: "The dodge should be able to chain into itself and should be cancelable into the short ranged counter
# when an attack button is pressed during most of the dodge's animation length. XV2 Sway, sounds and effects should be
# used"; "Different motion"; "Projectiles shouldn't trigger"): XV2's sway (CMN.bac 260-263 / 765-768: CMN.ean #189-192;
# the attacker in front -> the back sway #189, behind -> the forward sway #191), its first 7 frames in one (TimeScale
# x7) then 1:1: SWAY_N frames; intangible SWAY_INV (XV2's invulnerability 0-13 = ours 0-7); the counter cancel (an
# attack button) SWAY_CW_ON-SWAY_CW_OFF = XV2's 7-30 (260's BcmCallback 0xF80 window: Combos / BackHits / Supers /
# Ultimates / ZVanish; 765-768 have the counter's own link 0x8 through all of it) = 24 of its 37 frames; other actions
# from SWAY_IASA; Wait at SWAY_N. The sway's effects: BTL_CMN 493 (SKI_lineX_S, 0.35, at his feet) at XV2 1 and 4 (ours
# 0 and 1), 911 / 900 are ECFs (colour over the body: not drawn); its sound: CAR_BTL_CMN cue 5 (swing_05) at XV2 7 (ours 1)
SWAY_N = anim.part_start('sway_f_in')         # 37: each sway (1 + 36)
SWAY_F_AT = anim.part_start('sway_f_in')     # 37: the forward sway's first frame in the motion
CTR_AT = anim.part_start('ctr_out')          # 74: the counter's
CTR_N = anim.frames_of(anim.DODGE) - CTR_AT  # 22
SWAY_INV = 8
SWAY_CW_ON, SWAY_CW_OFF = 1, 24
SWAY_IASA = 25
SWAY_LINE_AT = (0, 1)
SWAY_SND_AT = 1
# the counter: CMN.bac 706 (707 the same on the other hand): animation 0-5 (the character's own EAN #30: ours the skill's
# finisher punch), its hitbox 0-6 (frames 0-5), BDM #0 (CMN.bdm), 1.5 m in front at 0.75 m, 1 m; BTL_CMN 492 (SKI_lineX_L
# on the pelvis) and CMN 230 (Btl_RHit) at 0, 491 (SKI_lineX_S, 0.35) at 4; no sound; its link 0x8 0-6: actionable at
# (its animation, the character's EAN #30, isn't in the files: XV2's straight punch of Hit's Time Skip, supamario_ui_anim)
# CTR_IASA. Damage: BDM #0 sub-entry 0 (the standing victim): DamageType 3, DamageAmount 0, user / victim stun 5, a
# 30-frame stagger (KnockbackDuration 30, strength Y 0.1 / Z 0.04 a frame). Smash 4: CTR_DMG (the smallest whole
# percent: XV2's 0 is a stagger, the hit still lands: its hitlag 5 = XV2's stun 5), knockback set (WKB) for XV2's
# 30-frame stagger (CTR_WKB 75, KBG 100: knockback 71.9 at weight 100 -> 28.8 frames of hitstun), its angle the push's
# (atan(0.1 / 0.04) = 68)
CTR_IASA = 6
CTR_HIT_N = 6
CTR_DMG, CTR_WKB, CTR_ANGLE = 1.0, 75, 68
CTR_SIZE, CTR_Y, CTR_Z = round(1.0 * 5.04, 2), round(0.75 * 5.04, 2), round(1.5 * 5.04, 2)
CTR_LINE2_AT = 4
MOT_SWAY_B, MOT_CTR, MOT_SWAY_F = 0x241, 0x242, 0x243      # SpecialAirLwLight and its custom-move slots (one animation)
SWAY_SCRIPTS = {'specialairlwlight_c2': 'counter', 'specialairlwlight_c3': 'sway_f'}
ST_ESCAPE_N = cave.ST_ESCAPE_N
# v7 Secret Sensation (the user: "slow time for everyone during its traveling and until reaching, do a slight zoom
# between Supamario and the opponent, then on Supamario ... similar to how it looks in Dragon Ball FighterZ"; the DBFZ
# clips ss/a.mp4, b.mp4: the counter at ~0.25 s, the camera in by ~0.55 s with both in the frame, closer round the
# arrival behind the opponent at ~1.05-1.10 s (~0.8 s of slowed travel), back out by ~1.45 s): the whole match at
# 1 / SS_SLOW from the counter's read to the arrival (the slide's 14 frames -> 42 screen frames = 0.70 s), at most
# SS_SLOW_FRAMES (its own end, should the MSC miss it); the camera in on him SS_CAM1_D over SS_CAM1_T frames at the read
# (slight: the fighter he passes stays in the frame), SS_CAM2_D over SS_CAM2_T from the slide's frame SS_CAM2_AT (the
# last 6 frames = 18 screen frames on him), back to normal at the arrival
SS_SLOW, SS_SLOW_FRAMES = 3, 48
SS_CAM1_T, SS_CAM1_D = 6, 1.2
SS_CAM2_AT, SS_CAM2_T, SS_CAM2_D = 8, 6, 1.5
# v6 (the user's v5 clip: no aura after the burst, only faint wisps): the MSC's renewal every 30 frames killed the aura AT
# ONCE (EffectModule 0x2723 (id, 1, 1): the effect manager's kill -> eft's KillEmitterSet 0x04A55714, its particles
# gone) and made it again, so its sprites (48-96 frames long, fading in over their life) never got past 29 frames: in
# game the faint puffs growing and vanishing twice a second (rendered: 4-36 % of the steady glow). Now the renewal FADES
# the old ones (0x2723 (id, 0, 0): eft's fade 0x04A4B25C, emission stopped, the particles live out) and makes new ones
# at once, so the emission never stops (the steady glow), every AURA_EVERY frames (at least the aura sprites' longest
# life: at most two generations alive, AURA_GENERATIONS)
AURA_EVERY = 120.0
SCALE = 1.75                         # xv2_smash_fx.SIZE (the earlier XV2 ports': XV2's x1.0)

ST_UI, ST_DODGE = cave.ST_UI, cave.ST_DODGE
MOT_FORM, MOT_STRIKE, MOT_DODGE, MOT_SS = 0x231, 0x235, 0x241, 0x245
MOT_ESCAPE_N = 0x4B                  # Mario's spot dodge (Secret Sensation's slide, the user's)
SCRIPT = {anim.FORM: 'speciallwlight', anim.STRIKE: 'speciallwheavy', anim.DODGE: 'specialairlwlight',
          anim.SS: 'specialairlwheavy'}
# Secret Sensation (the user's, Dragon Ball FighterZ's; the transformed grounded down special): the counter shape on
# frames 5-30 of a 45-frame stance (Marth-like); a counter: a 14-frame slide (EscapeN) behind the fighter to answer, a
# little into the background (Z out to -6 and back), ending airborne: 10 past a grounded one, 6 above its feet; 10 past
# and 10 above an airborne one; no hitbox
SS_ON, SS_OFF, SS_END = 5, 30, anim.frames_of(anim.SS)
SS_SLIDE_N, SS_DEPTH = 14, 6.0
SS_BEHIND, SS_UP_GROUND, SS_BEHIND_AIR, SS_UP_AIR = 10.0, 6.0, 10.0, 10.0
V_SS = 0x0F000324                    # TIMER_4: Secret Sensation's mark; v5 status 0x155's mode (cave.V_MODE)
assert V_SS == cave.V_MODE
BONES = {'TransN': 0, 'HipN': 2, 'LFootJ': 5, 'RFootJ': 9, 'BustN': 12, 'HeadN': 22, 'LHandN': 16, 'RHandN': 20}
V_AURA = 0x0F000323                  # TIMER_3: the aura's renewal
V_SHAPE = 0x0F000325                 # ui4 TIMER_5: the autododge's counter shape is on (his MSC's ui_shape, renewed)

# v3: the silver hair and eyes (tools/supamario_ui_model.py: the colours there, model.SILVER): silver copies of his
# hair / full hair / eye meshes, hidden by their visibility tracks; at the burst (and at the counter's white body's end)
# Mesh_Visibility Persist 1 hides his own hair / full hair / eyes and shows the copies (until a KO, the match end or a
# training reset). The full hair shows only in the side taunt's frames 17-72 (cap off): its copy is shown there by the
# taunt's game script while transformed (TIMER_0 > 1500). Wait1's game script applies the swap again while transformed
# and ends it otherwise (a training reset, a respawn); Entry's ends it
SILVER_MESHES = model.MESHES
# the mustache / eyebrow overlays (model.overlays, from the base's c00 model.nud: build() fills it before the scripts):
# hidden by Mesh_Visibility Persist 1 while he isn't transformed (Entry, Wait1: Rebirth plays Wait1), their overrides
# ended at the burst (they follow their expressions' visibility tracks)
OVERLAYS = []
UI_TRANSFORMED_OVER = 1500.0         # TIMER_0 (UI_V_FORM) above this: transformed (the MSC writes 2000 every frame)

# ---------------------------------------------------------------- XV2's effects (BTL_AURA.eepk / BTL_CMN.eepk)
# (key, EEPK, EMP, the Smash bone, offset (m), EEPK scale): BAC entry 0 plays 846 at 10 (MGT_HENSIN01 on b_C_Chest),
# 848 at 40 (the aura: loops on the feet, knees, legs, pelvis, chest, head, arms, hands), 851 / 849 at 220
# (MGT_HENSIN02 on b_C_Base 0.3 m down: the burst; 849 an ECF), entry 1 82 at 151 (BTL_CMN: Ski_Ref.emo + SKI_line.emp,
# the vanish), 850 at 350 (MGT_HENSIN00 on f_L_Eye). 847 / 849 / 846's first part are ECFs (colour over the body): no
# Smash 4 equivalent here (approximated: not drawn)
FX = [('start', 'BTL_AURA.eepk', 'MGT_HENSIN01.emp', 'BustN', (0.0, 0.0, 0.0), 1.0),
      ('burst', 'BTL_AURA.eepk', 'MGT_HENSIN02.emp', 'TransN', (0.0, -0.3, 0.0), 0.9),
      ('aura_hip', 'BTL_AURA.eepk', 'Aura_LoopFOK.emp', 'HipN', (0.0, 0.0, 0.0), 1.0),
      ('aura_head', 'BTL_AURA.eepk', 'Aura_HLoopFOK.emp', 'HeadN', (0.0, 0.2, 0.0), 1.0),
      ('aura_foot', 'BTL_AURA.eepk', 'FOK_FootL.emp', 'LFootJ', (0.0, 0.0, 0.0), 0.8),
      ('aura_chest', 'BTL_AURA.eepk', 'Aura_LoopFOK2.emp', 'BustN', (0.0, 0.0, 0.0), 1.0),
      ('aura_hand', 'BTL_AURA.eepk', 'Aura_HandLoopFOK.emp', 'RHandN', (0.0, 0.0, 0.0), 0.65),
      ('vanish', 'BTL_CMN.eepk', 'SKI_line.emp', 'HipN', (0.0, 0.0, 0.0), 1.0),
      # v7: the sway's / counter's (BTL_CMN 493 / 491, 492, 230), converted after the others (their ids follow)
      ('sway_line', 'BTL_CMN.eepk', 'SKI_lineX_S.emp', 'TransN', (0.0, 0.0, 0.0), 0.35),
      ('ctr_line', 'BTL_CMN.eepk', 'SKI_lineX_L.emp', 'HipN', (0.0, 0.0, 0.0), 1.0),
      ('ctr_hit', 'BTL_CMN.eepk', 'Btl_RHit.emp', 'TransN', (0.0, 0.75, 1.5), 0.9)]
FX_V7 = ('sway_line', 'ctr_line', 'ctr_hit')
# v3: the aura's colour. The converted emitters keep XV2's EMP colours (blue / cyan / white: rendered with fx_render's
# Smash 4 side, the drawn pixels' median hue 192 deg, saturation 0.26); the user's XV2 clip after the burst shows a
# lavender / purple-white flicker (the aura pixels' median hue 281-287 deg, saturation 0.16-0.18, value 0.88-0.96, four
# frames 5.6-6.9 s). XV2's own data has no purple for it: effect 848's EMP colours, its EMM materials (glare / refraction)
# and the body ECFs (847 Mgt_Aura.ecf: diffuse 0.42 0.60 0.68, ambient 0.63 0.75 1.0) are blue-white, and
# aura_setting.aur holds only effect ids (aura 1: BTL_AURA 40-44), no colours; the purple is the game's rendering
# (glare / screen effects). So the clip's colour is applied: every colour key of the aura's sets (AURA_SETS) turned to
# AURA_HUE and its saturation scaled by AURA_SAT (its value kept). An approximation, from the clip
AURA_HUE, AURA_SAT = 262.0, 0.8      # v4 (the user: "splotchy and purple"; wanted a slightly blue purple): blue-violet, x 0.45;
                                     # v5 x 0.8: additive now, the light itself carries the colour (x 0.45 came out white)
AURA_SETS = ('aura_hip', 'aura_head', 'aura_foot', 'aura_chest', 'aura_hand')
# v5 (the user: "splotchy and purple instead of a slightly blue purple glow with distortion"). What made it splotchy
# (the converted sets, read with ptcl.emitter_params): every emitter emits ONE particle every 19-39 frames (XV2's
# rates converted to intervals: 1-4 big sprites alive at a time, each popping in and out), and the big ones are
# alpha-blended smoke (blend 0: the 64x64 cloud texture and the 16x32 flame, 3.4-5.5 units at the call's size 1.75): a
# few opaque purple patches over him, not a glow. smooth_aura(): the intervals / AURA_DENSITY (at least 1 frame) with
# the alpha scaled by the same ratio (the same coverage on average, spread over many overlapping sprites), every
# emitter ADDITIVE (blend 1: shader 11 is drawn with blend 1 by 32 other emitters in this file, 39 already is): a soft
# glow round him, not patches. The heat haze: haze() adds Mario's fireball's refraction emitter (PtcMarioFireball
# 'refraction1', shader 7: the distortion pass, a 64x64 distortion map, 128 grey = none; Supamario's Kamehameha charge
# carries copies, KameShimmer) to the three sets the MSC keeps on him (hip, head, feet), soft (HAZE_*): it bends
# the picture behind him as XV2's aura does (its EMM refraction materials)
AURA_DENSITY = 6.0
AURA_ADD_ALPHA = 0.3                 # the alpha-blended (smoke) emitters' alpha x this once additive (added light, not
                                     # cover: at their old alpha they burn white on a bright stage)
AURA_SMOOTH_SETS = AURA_SETS
AURA_SAT_MIN = 0.45                  # v6: every aura colour at least this saturated (XV2's pale smoke colours came out white
                                     # once additive: the steady render's big sprites hue 262 at 0.15-0.19); a soft
                                     # blue-violet (the user: "a slightly blue purple glow")
AURA_GAIN = 1.6                      # v6: every aura emitter's alpha x this (v5's smoothing kept XV2's average coverage; in
                                     # game the sprites round the bone centres are half inside his body: the halo outside
                                     # the silhouette wants more, the user: "clearly visible")
AURA_GENERATIONS = 2                 # v6: aura instances alive per part at most (the renewing one and the fading one)
# v6: the glow on the body while transformed (XV2's UI form: a white-lavender rim on the body and a blue-violet halo
# round the silhouette, the user's clips): Outline_Set (the fighter shaders' own rim light, inside the silhouette, with
# a slight tint) and Outline_Shell (the band outside it, added: a glow; its colour shows as given from exe_v46z_outline5),
# both held (Frames 0) until a KO / the match end / a training reset: at the burst, at the counter's end and in Wait1
# while transformed (again after a training reset or another move's outline)
GLOW_RIM_RGB, GLOW_RIM_A, GLOW_RIM_TINT = (205.0, 195.0, 255.0), 600.0, 18.0
GLOW_SHELL_RGB, GLOW_SHELL_A, GLOW_SHELL_W = (150.0, 135.0, 255.0), 200.0, 3.0
GLOW_IN, GLOW_OUT = 10, 10
HAZE_SRC = ('PtcMarioFireball', 'refraction1')
HAZE = {'aura_hip': dict(scale=5.0, radius=2.0), 'aura_head': dict(scale=3.6, radius=1.2),
        'aura_foot': dict(scale=3.0, radius=1.0)}
HAZE_LIFE = 30                       # frames (the fireball's 14)
HAZE_INTERVAL = 2                    # one every 2 frames (the fireball's every frame)
HAZE_ALPHA = 0.45                    # its strength at the peak (the fireball's 1.0)
HAZE_RISE = 0.03                     # units a frame, up (heat rising)
FX_IDS = {}                          # key -> the ACMD / MSC id (0x0341xxxx), filled by effects()
FX_DEFAULT = 0x1000009               # before the build has made them (the earlier builds compile the MSC too)
METRE = 5.04

# ---------------------------------------------------------------- sounds
UI_SE = {'ui_start': ('CAR_BTL_M1510_MGT_00_Start_F22', 0.0),     # skill SE cue 0: entry 0 at 22
         'ui_success': ('CAR_BTL_M1510_MGT_01_Success', 0.0),     # skill SE cue 1: entry 0 at 205
         'ui_vanish': ('Vanish', 0.0),                             # CAR_BTL_CMN cue 96: entry 1 at 151
         'ui_sway': ('swing_05', 0.0)}                             # v7: CAR_BTL_CMN cue 5: the sway (CMN.bac 260) at 7
SE_IDS = {}
SND_START = anim.frame_of(anim.FORM, 0, 22)
SND_SUCCESS = anim.frame_of(anim.FORM, 0, 205)
FX_START_AT = anim.frame_of(anim.FORM, 0, 10)
FX_AURA_AT = anim.frame_of(anim.FORM, 0, 40)
FX_BURST_AT = anim.frame_of(anim.FORM, 0, 220)
CNT_END = anim.frame_of(anim.STRIKE, 1, 350)       # the counter's white body off (849 at 350)


def fl(v):
    return '%sf' % repr(float(v))


def fx_id(key):
    return FX_IDS.get(key, FX_DEFAULT)


def msc_values():
    """the UI_* names in fighters/supamario/supamario.c"""
    v = {'UI_ST_DODGE_F': fl(ST_DODGE), 'UI_ST_DODGE': '0x%X' % ST_DODGE, 'UI_ST_F': fl(ST_UI), 'UI_ST': '0x%X' % ST_UI,
         'UI_ST_DEAD': fl(0xB1), 'UI_ST_REBIRTH': fl(0xB2), 'UI_ST_ENTRY': fl(0x14F),
         'UI_V_FORM': '0x%X' % cave.V_FORM, 'UI_V_DODGE_R': '0x%X' % cave.V_DODGE_R,
         'UI_V_DODGE_L': '0x%X' % cave.V_DODGE_L, 'UI_V_AURA': '0x%X' % V_AURA, 'UI_V_SHAPE': '0x%X' % V_SHAPE,
         'UI_FORMING': fl(1000.0), 'UI_FORMED': fl(2000.0), 'UI_TRIGGER_PCT': fl(TRIGGER_PCT),
         'UI_CW_ON': fl(CW_ON), 'UI_CW_OFF': fl(CW_OFF), 'UI_GAP_FROM': fl(GAP_FROM), 'UI_GAP_TO': fl(GAP_TO),
         'UI_GAP_V': fl(GAP_V), 'UI_RUSH_REACH': fl(RUSH_REACH),
         'UI_GROUND_DY': fl(GROUND_DY), 'UI_FORM_N': fl(FORM_N), 'UI_STRIKE_N': fl(STRIKE_N),
'UI_DODGE_N': fl(DODGE_N), 'UI_DODGE_INV': fl(DODGE_INV),
         'UI_DODGE_MOVE': fl(DODGE_MOVE), 'UI_DODGE_V': fl(DODGE_V), 'UI_AURA_EVERY': fl(AURA_EVERY),
         'UI_MOT_FORM': '0x%X' % MOT_FORM, 'UI_MOT_STRIKE': '0x%X' % MOT_STRIKE, 'UI_MOT_DODGE': '0x%X' % MOT_DODGE,
         'UI_FX_AURA1': '0x%X' % fx_id('aura_hip'), 'UI_FX_AURA2': '0x%X' % fx_id('aura_head'),
         'UI_FX_AURA3': '0x%X' % fx_id('aura_foot'), 'UI_FX_VANISH': '0x%X' % fx_id('vanish'),
         'UI_BONE_HIP': '0x%X' % BONES['HipN'], 'UI_BONE_HEAD': '0x%X' % BONES['HeadN'],
         'UI_BONE_LFOOT': '0x%X' % BONES['LFootJ'], 'UI_BONE_RFOOT': '0x%X' % BONES['RFootJ'],
         'UI_HEAD_UP': fl(round(0.2 * METRE, 3)), 'UI_AURA_SIZE': fl(SCALE), 'UI_FOOT_SIZE': fl(round(0.8 * SCALE, 3)),
         # v6: the chest and the hands kept by the MSC too (all seven of XV2's parts the effect script plays)
         'UI_FX_AURA4': '0x%X' % fx_id('aura_chest'), 'UI_FX_AURA5': '0x%X' % fx_id('aura_hand'),
         'UI_BONE_CHEST': '0x%X' % BONES['BustN'], 'UI_BONE_RHAND': '0x%X' % BONES['RHandN'],
         'UI_BONE_LHAND': '0x%X' % BONES['LHandN'], 'UI_HAND_SIZE': fl(round(0.65 * SCALE, 3)),
         'UI_VANISH_SIZE': fl(SCALE), 'UI_SND_VANISH': '0x%X' % se_id('ui_vanish'),
         'UI_SS_MOT': '0x%X' % MOT_SS, 'UI_SS_SLIDE_MOT': '0x%X' % MOT_ESCAPE_N, 'UI_SS_ON': fl(SS_ON),
         'UI_SS_OFF': fl(SS_OFF), 'UI_SS_END': fl(SS_END), 'UI_SS_SLIDE_N': fl(SS_SLIDE_N), 'UI_SS_DEPTH': fl(SS_DEPTH),
         'UI_SS_BEHIND_AIR': fl(SS_BEHIND_AIR), 'UI_SS_BEHIND': fl(SS_BEHIND), 'UI_SS_UP_GROUND': fl(SS_UP_GROUND),
         'UI_SS_UP_AIR': fl(SS_UP_AIR), 'UI_V_SS': '0x%X' % V_SS,
         # v5: status 0x155's modes in TIMER_4 (= V_SS; the cave reads them too)
         'UI_MODE_FORM': fl(cave.MODE_FORM), 'UI_MODE_DODGE': fl(cave.MODE_DODGE),
         'UI_MODE_FORM_ON': fl(cave.MODE_FORM_ON), 'UI_MODE_DODGE_ON': fl(cave.MODE_DODGE_ON),
         # v7: the sway, its counter, the spot dodge's counter; Secret Sensation's slow-motion and camera
         'UI_MODE_COUNTER': fl(cave.MODE_COUNTER), 'UI_MODE_SWAY_ON': fl(cave.MODE_SWAY_ON),
         'UI_ST_ESCAPE_N': fl(ST_ESCAPE_N), 'UI_MOT_SWAY_B': '0x%X' % MOT_SWAY_B, 'UI_MOT_SWAY_F': '0x%X' % MOT_SWAY_F,
         'UI_MOT_CTR': '0x%X' % MOT_CTR, 'UI_SWAY_F_AT': fl(SWAY_F_AT), 'UI_CTR_AT': fl(CTR_AT), 'UI_SWAY_N': fl(SWAY_N),
         'UI_SWAY_INV': fl(SWAY_INV), 'UI_SWAY_CW_ON': fl(SWAY_CW_ON), 'UI_SWAY_CW_OFF': fl(SWAY_CW_OFF),
         'UI_SWAY_IASA': fl(SWAY_IASA), 'UI_CTR_IASA': fl(CTR_IASA), 'UI_CTR_N': fl(CTR_N),
         'UI_SS_SLOW': '0x%X' % SS_SLOW, 'UI_SS_SLOW_FRAMES': '0x%X' % SS_SLOW_FRAMES, 'UI_SS_CAM1_T': '0x%X' % SS_CAM1_T,
         'UI_SS_CAM1_D': fl(SS_CAM1_D), 'UI_SS_CAM2_AT': fl(SS_CAM2_AT), 'UI_SS_CAM2_T': '0x%X' % SS_CAM2_T,
         'UI_SS_CAM2_D': fl(SS_CAM2_D)}
    return v


# ---------------------------------------------------------------- ACMD
def cmd(name, *params):
    return acmd.Command(acmd.BY_NAME[name.lower()], list(params))


def timeline(events):
    out, at = [], 0
    for f, cmds in sorted(events, key=lambda e: e[0]):
        if f > at:
            out.append(cmd('frame', float(f)))
            at = f
        out += cmds
    return out


def strike_box():
    """XV2's finisher (BDM #2): FINISH_DMG, a launch"""
    import supamario_sledgehammer_build as SB
    return SB.hitbox(ID=0, Part=0, Bone=0, Damage=FINISH_DMG, Size=STRIKE_SIZE, Y=STRIKE_Y, Z=STRIKE_Z,
                     Hitlag=1.5, SDI=0.5, Clang=0, Rebound=0, SFXLevel=2, SFXType=1, NoGFX=0, **STRIKE_HIT)


def rush_box():
    """a rush hit (BDM #1): RUSH_DMG, held in place (angle 361, no growth, low base: the rapid-jab loops' way, with
    Hitbox_Hold mode 2 after it), its own small hitstop (XV2's 0 / 2)"""
    import supamario_sledgehammer_build as SB
    return SB.hitbox(ID=0, Part=0, Bone=0, Damage=RUSH_DMG, Angle=361, KBG=0, FKB=0, BKB=15, Size=RUSH_SIZE, Y=RUSH_Y,
                     Z=RUSH_Z, Hitlag=0.5, SDI=0.0, Clang=0, Rebound=0, SFXLevel=0, SFXType=1, NoGFX=0)


def freeze_box():
    """XV2's BDM #0 at the counter's start: no damage, the attacker held (its hitstop to the first rush hit), Part 1"""
    import supamario_sledgehammer_build as SB
    return SB.hitbox(ID=1, Part=1, Bone=0, Damage=0.0, Angle=0, KBG=0, FKB=0, BKB=0, Size=FREEZE_SIZE, Y=5.0, Z=0.0,
                     Hitlag=0.0, SDI=0.0, Clang=0, Rebound=0, SFXLevel=0, SFXType=0, NoGFX=1, Flinchless=1,
                     HitstopFrames=RUSH_AT[0], SelfHitstopFrames=0)


def ctr_box():
    """v7: the counter's hit (CMN.bac 706's hitbox, CMN.bdm #0: a stagger): CTR_DMG, set knockback for XV2's 30-frame
    stagger, at XV2's 1.5 m in front, 0.75 m up, 1 m"""
    import supamario_sledgehammer_build as SB
    return SB.hitbox(ID=0, Part=0, Bone=0, Damage=CTR_DMG, Angle=CTR_ANGLE, KBG=100, FKB=CTR_WKB, BKB=0, Size=CTR_SIZE,
                     Y=CTR_Y, Z=CTR_Z, Hitlag=1.0, SDI=1.0, Clang=1, Rebound=0, SFXLevel=0, SFXType=1, NoGFX=0)


def sway_scripts():
    """v7: {script name: {part: body}} of the sways and the counter (SpecialAirLwLight's animation: the back sway from
    frame 0 (motion 0x241, its own script), the forward sway from SWAY_F_AT (0x243, specialairlwlight_c3), the counter
    from CTR_AT (0x242, specialairlwlight_c2): a motion started at frame F starts its scripts' clock at F (the motion
    change's start frame, MotionAnimcmdModule vt +0x4C +0x20), so each script's first command waits for its F"""
    def sway(at):
        return {'game': [], 'expression': [],
                'effect': timeline([(at + f, [graphic('sway_line', follow=False)]) for f in SWAY_LINE_AT]),
                'sound': timeline([(at + SWAY_SND_AT, [cmd('sound_effect', se_id('ui_sway'))])])}
    ctr = {'game': timeline([(CTR_AT, [ctr_box()]), (CTR_AT + CTR_HIT_N, [cmd('remove_all_hitboxes')])]),
           'effect': timeline([(CTR_AT, [graphic('ctr_line', follow=False), graphic('ctr_hit', follow=False)]),
                               (CTR_AT + CTR_LINE2_AT, [graphic('sway_line', follow=False)])]),
           'sound': [], 'expression': []}
    return {'specialairlwlight': sway(0), 'specialairlwlight_c3': sway(SWAY_F_AT), 'specialairlwlight_c2': ctr}


def white_on(frames):
    return [cmd('color_overlay', *WHITE_RGB, WHITE_A),
            cmd('outline_shell', 0, *RIM_RGB, RIM_A, RIM_WIDTH, int(frames), 4, 10, 0, 1)]


def white_off():
    return [cmd('terminate_overlays'), cmd('outline_shell', 0, 0.0, 0.0, 0.0, 0.0, RIM_WIDTH, 0, 0, 10, 0, 1)]


def glow_on():
    """v6: the transformed glow, held: the rim light (Outline_Set) and the blue-violet band (Outline_Shell: it replaces
    the white body's band, growing from where that one is)"""
    return [cmd('outline_set', 0, *GLOW_RIM_RGB, GLOW_RIM_A, GLOW_RIM_TINT, 0, GLOW_IN, GLOW_OUT, 0),
            cmd('outline_shell', 0, *GLOW_SHELL_RGB, GLOW_SHELL_A, GLOW_SHELL_W, 0, GLOW_IN, GLOW_OUT, 0, 1)]


def white_to_glow():
    """v6: the white body's end into the transformed glow (the overlay ended; the white band replaced by the glow's)"""
    return [cmd('terminate_overlays')] + glow_on()


# ui4: Mesh_Visibility by the mesh's INDEX (the game's: NUD mesh order, every costume's model.nud and metal.nud the same,
# checked), not by its name: v4's by-name commands went through mesh_vis_cave's name walk, which took the unaligned names
# the model loader packs back to back for "no name" (docs/native-notes.md "Mesh visibility" v3; exe_v46z_ui4 fixes the
# walk too): the v4 log has Mario_Nohat's command hiding meshes 5-8 (Nohat, Eye, Halfblink1 / 2), Mario_Hair (the
# sideburns: the black boxes beside the silver hair), the full hair / eye copies and 6 overlays (the silver at 0%) never
# reached. MESH_INDEX: name -> index, filled by build() from the base's c00 model.nud and the copies' order
MESH_INDEX = {}


def mesh_index(mesh):
    if mesh in MESH_INDEX:
        return MESH_INDEX[mesh]
    return MV.crc32(mesh)                # before build() fills it (the earlier builds compile the scripts' tests)


def meshvis(mesh, visible, persist):
    i = mesh_index(mesh)
    assert MESH_INDEX == {} or 0 <= i < 256, (mesh, i)
    return cmd('mesh_visibility', 0, i, visible, persist)


P2 = 2            # Mesh_Visibility Persist 2 (exe_v46z_ui2): the mesh's own set state, no override entry (v4)
HAT_OFF_AT = FX_START_AT              # v4 (the user): the cap off from the transformation's gold start (frame 10, the
                                      # white body over him) until Ultra Instinct ends


def hat_off():
    """v4: the cap hidden, his sideburns hidden, his own (brown) full hair shown: the transformation's start"""
    return ([meshvis(m, 0, P2) for m in model.HAT + (model.HAIR,)] +
            [meshvis(SILVER_MESHES['nohat'][0], 1, P2)])


def silver_on():
    """transformed (v4, Persist 2: each mesh's own set state, no override entry): his cap, sideburns, full hair and
    eyes hidden; the silver full hair / eyes and the mustache / eyebrow overlays follow their visibility tracks (the
    eyes his blinks, the overlays his expressions)"""
    return ([meshvis(m, 0, P2) for m in model.HAT + (model.HAIR,) + tuple(SILVER_MESHES[k][0] for k in ('nohat', 'eye'))] +
            [meshvis(SILVER_MESHES[k][1], 2, P2) for k in ('nohat', 'eye')] + [meshvis(o, 2, P2) for o in OVERLAYS])


def silver_off():
    """his own look (v4, Persist 2): his cap, sideburns, full hair and eyes follow their tracks again (the game's own
    state), the copies and overlays hidden"""
    return ([meshvis(m, 2, P2) for m in model.HAT + (model.HAIR,) + tuple(SILVER_MESHES[k][0] for k in ('nohat', 'eye'))] +
            [meshvis(SILVER_MESHES[k][1], 0, P2) for k in ('nohat', 'eye')] + [meshvis(o, 0, P2) for o in OVERLAYS])


def mesh_indices(base_names):
    """{name: the game's mesh index} for the meshes the scripts name: his own (the base model's order) and the copies
    model.costume appends after them (MESHES' copies in order, then the overlays)"""
    out = {n: i for i, n in enumerate(base_names)}
    added = [SILVER_MESHES[k][1] for k in SILVER_MESHES] + list(OVERLAYS)
    for k, n in enumerate(added):
        out[n] = len(base_names) + k
    want = [m for m in model.HAT + (model.HAIR,)] + [n for k in SILVER_MESHES.values() for n in k] + list(OVERLAYS)
    missing = [n for n in want if n not in out]
    assert not missing, missing
    return {n: out[n] for n in want}


def if_var(var, method, value, body):
    """Float_Var_Compare(var method value) True { body }"""
    return [cmd('float_var_compare', var, method, float(value)),
            cmd('true', 2 + sum(acmd.INFO[c.ident]['size'] for c in body))] + body


def silver_scripts():
    """{script name: game script body} of the swap's other scripts (none of them had a game script): Wait1 (Rebirth
    plays it) applies the transformed look or his own by TIMER_0, Entry his own. v4: no side taunt script (the full
    hair's copy follows its track, shown all through; his own full hair and cap stay hidden by their set state)"""
    wait = if_var(cave.V_FORM, 5, UI_TRANSFORMED_OVER, silver_on() + glow_on()) + if_var(cave.V_FORM, 2, UI_TRANSFORMED_OVER,
                                                                              silver_off())
    return {'wait1': wait, 'entryl': silver_off(), 'entryr': silver_off()}


def graphic(key, bone=None, follow=True, size=1.0):
    e = [x for x in FX if x[0] == key][0]
    b = BONES[bone or e[3]]
    x, y, z = (c * METRE for c in e[4])
    if follow:
        return cmd('external_graphic', fx_id(key), b, x, y, z, 0.0, 0.0, 0.0, e[5] * SCALE * size, 0)
    return cmd('graphic_effect', fx_id(key), b, x, y, z, 0.0, 0.0, 0.0, e[5] * SCALE * size, 0.0, 0.0, 0.0, 0.0, 0.0,
               0.0, 1)


def scripts_for():
    """{script name: {part: body}}"""
    aura = [graphic('aura_hip'), graphic('aura_chest'), graphic('aura_head'), graphic('aura_foot'),
            graphic('aura_foot', 'RFootJ'), graphic('aura_hand'), graphic('aura_hand', 'LHandN')]
    rush = []
    for f in RUSH_AT:
        rush += [(f, [cmd('hit_log_clear', 0), rush_box(), cmd('hitbox_hold', 0, 2)]), (f + 2, [cmd('remove_all_hitboxes')])]
    game = {anim.FORM: timeline([(HAT_OFF_AT, hat_off()), (FX_BURST_AT, silver_on())]),
            anim.STRIKE: timeline([(0, [freeze_box()]), (1, [cmd('remove_all_hitboxes')])] + rush +
                                  [(STRIKE_AT, [cmd('hit_log_clear', 0), strike_box()]),
                                   (STRIKE_AT + 3, [cmd('remove_all_hitboxes')]), (CNT_END, silver_on())]),
            anim.DODGE: [], anim.SS: []}
    effect = {anim.FORM: timeline([(FX_START_AT, [graphic('start')] + white_on(FX_BURST_AT - FX_START_AT)),
                                   (FX_AURA_AT, aura), (FX_BURST_AT, [graphic('burst', follow=False)] + white_to_glow())]),
              anim.STRIKE: timeline([(0, [graphic('vanish', follow=False)] + white_on(CNT_END)),
                                     (anim.frame_of(anim.STRIKE, 1, 170), [graphic('vanish', follow=False)]),
                                     # v6: no aura here: the counter ends the transformation, so the MSC's aura
                                     # (ui_aura, renewed by fading) is on from its first frame; this one doubled it
                                     (CNT_END, white_to_glow())]),
              anim.DODGE: sway_scripts()['specialairlwlight']['effect'], anim.SS: []}
    sound = {anim.FORM: timeline([(SND_START, [cmd('sound_effect', se_id('ui_start'))]),
                                  (SND_SUCCESS, [cmd('sound_effect', se_id('ui_success'))])]),
             anim.STRIKE: timeline([(0, [cmd('sound_effect', se_id('ui_vanish'))]),
                                    (anim.frame_of(anim.STRIKE, 1, 335), [cmd('sound_effect', se_id('ui_success'))])]),
             anim.DODGE: sway_scripts()['specialairlwlight']['sound'], anim.SS: []}
    expression = {anim.FORM: timeline([(FX_BURST_AT, [cmd('rumble', 0x12, 0)])]),
                  anim.STRIKE: timeline([(STRIKE_AT, [cmd('rumble', 0x12, 0)])]), anim.DODGE: [], anim.SS: []}
    return {'game': game, 'effect': effect, 'sound': sound, 'expression': expression}


def se_id(key):
    return SE_IDS.get(key, 0)


def scripts(body_dir):
    for part, bodies in scripts_for().items():
        path = os.path.join(body_dir, part + '.bin')
        f = acmd.ACMDFile.load(path)
        for m, body in bodies.items():
            f.scripts[acmd.crc(SCRIPT[m])] = body + [acmd.Command(acmd.END)]     # F.L.U.D.D.'s replaced
        for name in SWAY_SCRIPTS:                # v7: the custom-move slots' scripts (vanilla's replaced or new)
            f.scripts[acmd.crc(name)] = sway_scripts()[name][part] + [acmd.Command(acmd.END)]
        if part == 'game':
            for name, body in silver_scripts().items():
                assert acmd.crc(name) not in f.scripts, name
                f.scripts[acmd.crc(name)] = body + [acmd.Command(acmd.END)]
        f.save(path)


# ---------------------------------------------------------------- effects / sounds
def lavender(rgb):
    """an emitter colour turned to the clip's lavender: hue AURA_HUE, saturation x AURA_SAT (v6: at least AURA_SAT_MIN),
    its value kept"""
    import colorsys
    v = max(rgb)
    if v <= 0:
        return tuple(rgb)
    h, s_, _v = colorsys.rgb_to_hsv(*[c / v for c in rgb])
    return tuple(c * v for c in colorsys.hsv_to_rgb(AURA_HUE / 360.0, max(s_ * AURA_SAT, AURA_SAT_MIN), 1.0))


def tint_aura(p, rep):
    """lavender() over every colour key (both tracks) of the aura's converted sets; {set: [emitters]}"""
    done = {}
    for key in AURA_SETS:
        emp = [x for x in FX if x[0] == key][0][2]
        name = 'PtcSupamarioUi' + emp[:-4]
        si = p.find_set(name)
        for e in p.sets[si]['emitters']:
            em = e['data']
            if em is None:
                continue
            for track in (0, 1):
                keys = [tuple(k) for k in p.color_keys(em, track)]
                p.set_color_keys(em, track, [lavender(k[:3]) + tuple(k[3:]) for k in keys])
            done.setdefault(name, []).append(p.emitter_name(em))
        rep[name]['tint'] = [AURA_HUE, AURA_SAT]
    return done


def smooth_aura(p, rep):
    """v5: the aura sets' emitters many and soft instead of few and big (AURA_DENSITY), all additive"""
    done = {}
    for key in AURA_SMOOTH_SETS:
        emp = [x for x in FX if x[0] == key][0][2]
        name = 'PtcSupamarioUi' + emp[:-4]
        si = p.find_set(name)
        for e in p.sets[si]['emitters']:
            em = e['data']
            if em is None:
                continue
            old = p.field(em, 'emit_interval')
            new = max(1, int(round(old / AURA_DENSITY))) if old > 0 else old
            f = (float(new) / old) if old > 0 else 1.0
            if p.field(em, 'blend_type') == 0:
                f *= AURA_ADD_ALPHA
            f *= AURA_GAIN
            p.set_field(em, 'emit_interval', new)
            for fld in ('alpha_init', 'alpha_diff21', 'alpha_diff32'):
                p.set_field(em, fld, p.field(em, fld) * f)
            p.set_field(em, 'blend_type', 1)
            done.setdefault(name, []).append((p.emitter_name(em), old, new, round(f, 3)))
        rep[name]['smooth'] = done[name]
    return done


def haze(p, rep):
    """v5: the fireball's refraction emitter, soft and rising, appended to the hip / head / feet aura sets"""
    import struct
    src = p.find_set(HAZE_SRC[0])
    ks = [k for k, e in enumerate(p.sets[src]['emitters']) if e['data'] is not None and
          p.emitter_name(e['data']) == HAZE_SRC[1]]
    assert ks, HAZE_SRC
    base = p.emitter_bytes(src, ks[0])
    for key, prm in HAZE.items():
        emp = [x for x in FX if x[0] == key][0][2]
        name = 'PtcSupamarioUi' + emp[:-4]
        si = p.find_set(name)
        em = bytearray(base)
        struct.pack_into('>I', em, 0x38, p.add_name('UiHaze'))
        p.set_field(em, 'ptcl_life', HAZE_LIFE)
        p.set_field(em, 'emit_interval', HAZE_INTERVAL)
        p.set_field(em, 'scale', [prm['scale'], prm['scale']])
        p.set_field(em, 'volume_radius', [prm['radius']] * 3)
        a1, a2 = p.field(em, 'alpha_diff21'), p.field(em, 'alpha_diff32')
        p.set_field(em, 'alpha_diff21', a1 * HAZE_ALPHA)
        p.set_field(em, 'alpha_diff32', a2 * HAZE_ALPHA)
        p.set_field(em, 'emit_direction', [0.0, 1.0, 0.0])
        p.set_field(em, 'emitter_velocity', HAZE_RISE)
        p.sets[si]['emitters'].append({'pos': 0, 'rt': (0, 0, 0), 'data': em})
        p.dirty_layout = True
        rep[name]['haze'] = dict(prm, life=HAZE_LIFE, interval=HAZE_INTERVAL, alpha=HAZE_ALPHA, rise=HAZE_RISE)


def aura_life(p):
    """v6: the longest particle life (+ its random part) of the aura sets' emitters (haze included): a faded generation
    is gone this long after its fade"""
    out = 0
    for key in AURA_SETS:
        name = 'PtcSupamarioUi' + [x for x in FX if x[0] == key][0][2][:-4]
        for e in p.sets[p.find_set(name)]['emitters']:
            if e['data'] is not None:
                out = max(out, p.field(e['data'], 'ptcl_life') + max(0, p.field(e['data'], 'ptcl_life_random')))
    return out


def effects(cmn_dir, fx_dir):
    """FX's EMPs (XV2's vfx/cmn) into his ptcl / efc after every earlier set; FX_IDS their ids"""
    import efc
    import ptcl
    import xv2_to_ptcl
    base = 'supamario.010d0000'
    p = ptcl.Ptcl(open(os.path.join(fx_dir, base + '.ptcl'), 'rb').read())
    e = efc.Efc(open(os.path.join(fx_dir, base + '.efc'), 'rb').read())
    rep = {}
    batches = [(ep, [x[2] for x in FX if x[1] == ep and x[0] not in FX_V7]) for ep in ('BTL_AURA.eepk', 'BTL_CMN.eepk')]
    batches.append(('BTL_CMN.eepk', [x[2] for x in FX if x[0] in FX_V7]))   # v7: after (the earlier ids kept)
    for eepk, emps in batches:
        with tempfile.TemporaryDirectory() as pkg:
            for fn in os.listdir(cmn_dir):
                if not fn.lower().endswith('.eepk') or fn == eepk:
                    os.symlink(os.path.abspath(os.path.join(cmn_dir, fn)), os.path.join(pkg, fn))
            old = xv2_to_ptcl.TEX_MAX
            xv2_to_ptcl.TEX_MAX = 64
            try:
                made, log = xv2_to_ptcl.convert_package(p, pkg, 'PtcSupamarioUi', emps=emps, strict=False)
            finally:
                xv2_to_ptcl.TEX_MAX = old
        by_emp = {}
        for si, name, chunk in made:
            by_emp.setdefault(name.replace('PtcSupamarioUi', '') + '.emp', e.add(si + 1))
            rep[name] = {'set': si, 'emitters': [en for _b, en, _n in chunk]}
        for key, ep, emp, _bone, _o, _s in FX:
            if ep == eepk and emp in emps:
                FX_IDS[key] = 0x03410000 | by_emp[emp]
    tint_aura(p, rep)
    smooth_aura(p, rep)
    haze(p, rep)
    life = aura_life(p)
    assert AURA_EVERY >= life, ('v6: the renewal must outlast the aura sprites (at most %d generations)'
                                % AURA_GENERATIONS, AURA_EVERY, life)
    rep['aura_life'] = life
    out = p.build()
    assert ptcl.Ptcl(out).validate() == []
    open(os.path.join(fx_dir, base + '.ptcl'), 'wb').write(out)
    open(os.path.join(fx_dir, base + '.efc'), 'wb').write(e.build())
    return rep


def sound_bank(fdir, out_dir, wav_dir):
    """UI_SE into his bank and the soundlabeltable (Time Skip's sound_bank way); SE_IDS their ids"""
    import supamario_godfist_build as GB
    table = os.path.join(out_dir, 'sound', 'config', 'soundlabeltable.bin')
    old_se, old_ids = dict(GB.CMN_SE), dict(GB.SE_IDS)
    try:
        GB.CMN_SE.clear()
        GB.CMN_SE.update(UI_SE)
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
    SE_IDS.clear()
    SE_IDS.update(got)
    return got


# ---------------------------------------------------------------- build
def build(sm_dir, out_dir, ui_skill, ui_se_wav, ts_args):
    import supamario_godfist_build as GB
    import supamario_timeskip_build as TS
    fdir = TS.build(sm_dir, out_dir, ts_args['ts_skill'], ts_args['ts_se_wav'], ts_args['sh'], ts_args.get('png'),
                    ts_args.get('halo', True), ts_args['frt'])
    mo = os.path.join(fdir, 'motion', 'body')
    vbn = os.path.join(sm_dir, 'model', 'body', 'c00', 'model.vbn')
    outs, _bones, info = anim.build(mo, vbn, os.path.join(ui_skill, '1510_GKS_MGT.ean'), mo, ts_args.get('cmn_ean'),
                                    os.path.join(ts_args['ts_skill'], '1352_HIK_DSH.ean'))
    rep = effects(ts_args['sh']['fd']['cb']['gf']['cmn_vfx'], os.path.join(fdir, 'effect', 'supamario'))
    sound_bank(fdir, out_dir, ui_se_wav)
    import nud
    base_meshes = nud.read(os.path.join(sm_dir, 'model', 'body', 'c00', 'model.nud'))
    OVERLAYS[:] = [o['name'] for o in model.overlays(base_meshes)]
    MESH_INDEX.clear()
    MESH_INDEX.update(mesh_indices([m.name for m in base_meshes]))
    scripts(os.path.join(fdir, 'script', 'animcmd', 'body'))
    GB.msc(os.path.join(fdir, 'script', 'msc', 'supamario.mscsb'))
    silver = model.build(sm_dir, fdir)
    for c, rep_c in silver.items():
        assert list(rep_c['overlays']) == OVERLAYS, (c, 'the overlays differ from c00\'s: the scripts name c00\'s')
        for fn in ('model.nud', 'metal.nud'):
            path = os.path.join(fdir, 'model', 'body', c, fn)
            if os.path.exists(path):
                names = [m.name for m in nud.read(path)]
                bad = [(n, i) for n, i in MESH_INDEX.items() if i >= len(names) or names[i] != n]
                assert not bad, (c, fn, bad[:3], 'the scripts\' mesh indices name other meshes')
    doc = {'silver': {'colours': model.SILVER, 'sheen': model.SHEEN, 'meshes': model.MESHES, 'overlays': OVERLAYS,
                      'costumes': silver},
           'frames': {m: anim.frames_of(m) for m in anim.MOTIONS}, 'strike_at': STRIKE_AT,
           'counter_window': [CW_ON, CW_OFF],
           'events': {'snd_start': SND_START, 'snd_success': SND_SUCCESS, 'fx_start': FX_START_AT,
                      'fx_aura': FX_AURA_AT, 'fx_burst': FX_BURST_AT},
           'fx_ids': {k: '0x%08X' % v for k, v in FX_IDS.items()}, 'se_ids': {k: '0x%08X' % v for k, v in SE_IDS.items()},
           'mesh_index': dict(MESH_INDEX),
           'fx': rep, 'source': {m: info['info'][m]['source'] for m in anim.MOTIONS}}
    with open(os.path.join(out_dir, 'ultrainstinct.json'), 'w') as fh:
        json.dump(doc, fh, indent=1)
    return fdir


def main():
    a = sys.argv[1:]
    opts = {}
    halo = '--no-halo' not in a
    if not halo:
        a.remove('--no-halo')
    keys = ('--ui-skill', '--ui-se-wav', '--ts-skill', '--ts-se-wav', '--frt-skill', '--sh-skill', '--sh-se-wav',
            '--fd-skill', '--fd-se-wav', '--skill', '--se-wav', '--ean', '--cmn-vfx', '--skill-vfx', '--cmn-se', '--stb',
            '--png', '--cmn-ean')
    for k in keys:
        if k in a:
            i = a.index(k)
            opts[k] = a[i + 1]
            del a[i:i + 2]
    if len(a) != 2 or any(k not in opts for k in keys[:13]):
        sys.exit(__doc__)
    gf = {'ean': opts['--ean'], 'cmn_vfx': opts['--cmn-vfx'], 'skill_vfx': opts.get('--skill-vfx'),
          'cmn_se': opts.get('--cmn-se'), 'stb': opts.get('--stb')}
    cb = {'skill': opts['--skill'], 'se_wav': opts['--se-wav'], 'gf': gf}
    fd = {'fd_skill': opts['--fd-skill'], 'fd_se_wav': opts['--fd-se-wav'], 'cb': cb}
    sh = {'sh_skill': opts['--sh-skill'], 'sh_se_wav': opts['--sh-se-wav'], 'fd': fd}
    ts = {'ts_skill': opts['--ts-skill'], 'ts_se_wav': opts['--ts-se-wav'], 'frt': opts['--frt-skill'], 'sh': sh,
          'png': opts.get('--png'), 'halo': halo, 'cmn_ean': opts.get('--cmn-ean')}
    print(build(a[0], a[1], opts['--ui-skill'], opts['--ui-se-wav'], ts))
    print('sounds: ' + ', '.join('%s 0x%08X' % kv for kv in SE_IDS.items()))
    print('effects: ' + ', '.join('%s 0x%08X' % kv for kv in FX_IDS.items()))
    print('transformation %d frames (window %d-%d), counter %d (rush %s, finisher %d), dodge %d (intangible %d)' % (
        FORM_N, CW_ON, CW_OFF, STRIKE_N, RUSH_AT, STRIKE_AT, DODGE_N, DODGE_INV))


if __name__ == '__main__':
    # through the module itself: supamario_kame_build's MSC values import supamario_ui_build, whose FX_IDS / SE_IDS
    # must be the ones this run fills (not __main__'s copy)
    import supamario_ui_build
    supamario_ui_build.main()
