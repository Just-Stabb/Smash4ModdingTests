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
import struct
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import mesh_vis_cave as MV  # noqa: E402
import supamario_ui_anim as anim  # noqa: E402
import supamario_ui_cave as cave  # noqa: E402
import supamario_ui_model as model  # noqa: E402
import supamario_sf_build as SF  # noqa: E402

# ---------------------------------------------------------------- the rules (the user's spec)
TRIGGER_PCT = 100.0                  # his first actionable frame at 100% or more
FORM_N = anim.frames_of(anim.FORM)   # 60: the transformation (XV2 entry 0's 0-229, the user's "about 60 frames")
STRIKE_N = anim.part_len('counter')             # 349: XV2's BAC 1 from 151 to 499, 1:1 (v10: the long rush; the
                                                # motion's animation goes on with the short one)
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
SWAY_INV = 8
SWAY_CW_ON, SWAY_CW_OFF = 1, 24
SWAY_IASA = 25
SWAY_LINE_AT = (0, 1)
SWAY_SND_AT = 1
# the sway's counter: v7 played CMN.bac 706's strike (README "Ultra Instinct v7" 3: its data and conversion); v8 (the
# user: "the rush from their clip": the vanish and the multi-hit rush) plays the transformation's counter (SpecialLwHeavy,
# STRIKE_N frames, ui_counter: XV2's BAC 1, the same entry every counter root of the skill's BCM plays) from the sway's
# window and the spot dodge; 706's motion part, its slot 0x242 script and effects are gone
MOT_SWAY_B, MOT_SWAY_F = 0x241, 0x243      # SpecialAirLwLight and its custom-move slot 0x243 (one animation)
# v10 (the user: "make it so the autododge alternates between animations"): XV2's four auto sways (CMN.bac 260-263 /
# 765-768: CMN.ean #189 B_L, #190 B_R, #191 F_L, #192 F_R); the attacker in front -> a back sway, behind -> a forward one
# (v7), and successive dodges alternate L / R (TIMER_7, V_SWAY: his MSC's parity, renewed every frame). The R sways play
# through SpecialAirLwLight's other custom-move slots (0x242 from 74, 0x244 from 111: the motion table gives 0x241-0x244
# one animation; their vanilla scripts were F.L.U.D.D.'s, unreachable)
MOT_SWAY_BR, MOT_SWAY_FR = 0x242, 0x244
SWAY_BR_AT, SWAY_FR_AT = anim.part_start('sway_br_in'), anim.part_start('sway_fr_in')
V_SWAY = 0x0F000327                  # TIMER_7: the next sway's side (> 0.5: R), his MSC's (renewed every frame)
SWAY_SCRIPTS = {'specialairlwlight_c3': 'sway_f', 'specialairlwlight_c2': 'sway_br', 'specialairlwlight_c4': 'sway_fr'}
SWAY_AT = {'specialairlwlight': 0, 'specialairlwlight_c3': SWAY_F_AT, 'specialairlwlight_c2': SWAY_BR_AT,
           'specialairlwlight_c4': SWAY_FR_AT}
# v10 (the user: "make the autododge counter use the fast version that does less hits and make it only happen from a
# special button input"; then "the transformation version of the rush counter should use the long animation with more
# hits, the autododge version should use the short animation with far less hits"). No XV2 file has a shorter rush (the
# skill's counter entries 1 / 2 / 5 / 6 / 9 / 10 all hold the 16 hitboxes, CMN.bac has no multi-hit entry), so the
# dodge's rush is built from the user's clips (udclip e, 60 fps): the vanish at 36, the first impact at 92 (56 later; the
# long rush's is 59), the HUD's count 2 .. 11 at 100 .. 144: 11 hits ~5.2 frames apart (10 rush hits and the finisher),
# the finisher's ring at ~150, the camera back on him standing at ~158. SpecialLwHeavy's animation goes on after the long
# rush with it (supamario_ui_anim 'counter_s_*', motion 0x236 speciallwheavy_c2 from STRIKE_S_AT): STRIKE_S_N frames;
# its rush hits at RUSH_S_AT, the finisher at STRIKE_S_HIT (its own frames); XV2's 170 vanish, 335 sound, 350 end
# placed by its parts' timing. The sway's counter (special only, its window) and the spot dodge's use it; the
# transformation's counter keeps the long one
MOT_STRIKE_S = 0x236
STRIKE_S_AT = anim.part_start('counter_s_in')                        # 349
STRIKE_S_N = sum(anim.part_len(n) for n in ('counter_s_in', 'counter_s_rush', 'counter_s_end'))   # 150
RUSH_S_N = 10
RUSH_S_GAP = 5.2                     # the clip's 11 counts over 52 frames
RUSH_S_AT = [anim.part_frame('counter_s_rush', 210) - STRIKE_S_AT + int(round(RUSH_S_GAP * k)) for k in range(RUSH_S_N)]
STRIKE_S_HIT = anim.part_frame('counter_s_end', 280) - STRIKE_S_AT                 # 108: the 11th hit
CNT_S_VANISH2 = anim.part_frame('counter_s_in', 170) - STRIKE_S_AT                 # XV2's second vanish (170)
CNT_S_SND = anim.part_frame('counter_s_end', 335) - STRIKE_S_AT                    # skill SE cue 1 (335)
CNT_S_END = STRIKE_S_N - 1                                                         # the white body off (XV2 350)
EXTRA_SCRIPTS = list(SWAY_SCRIPTS) + ['speciallwheavy_c2', SF.SCRIPT_START, SF.SCRIPT_REL]   # the custom-move slots'
                                                                    # scripts the build writes (v11: Soaring Fist's)
ST_ESCAPE_N = cave.ST_ESCAPE_N
# v7 Secret Sensation (the user: "slow time for everyone during its traveling and until reaching, do a slight zoom
# between Supamario and the opponent, then on Supamario ... similar to how it looks in Dragon Ball FighterZ"; the DBFZ
# clips ss/a.mp4, b.mp4: the counter at ~0.25 s, the camera in by ~0.55 s with both in the frame, closer round the
# arrival behind the opponent at ~1.05-1.10 s (~0.8 s of slowed travel), back out by ~1.45 s): the whole match at
# 1 / SS_SLOW from the counter's read to the arrival (the slide's 14 frames -> 42 screen frames = 0.70 s), at most
# SS_SLOW_FRAMES (its own end, should the MSC miss it); the camera in on him SS_CAM1_D over SS_CAM1_T frames at the read
# (slight: the fighter he passes stays in the frame), SS_CAM2_D over SS_CAM2_T from the slide's frame SS_CAM2_AT (the
# last 6 frames = 18 screen frames on him), back to normal at the arrival
SS_SLOW, SS_SLOW_FRAMES = 3, 48      # v7-v9 (v10: the world stop below replaces it)
# v9 (the user's v7 test: "the camera shift for Secret Sensation is too close, it should be a slight zoom rather than a
# close one"): CameraModule 0x2714's distance is how far the camera stays (higher = farther: Kirby's MSC, tuned in game,
# has 4.0 for "a slight zoom on Kirby", 2.0 for the back throw's big hit and the Final Smash's, and notes 1.4 as "much
# closer"; Ryu's critical 1.1); v7's 1.2 / 1.5 were close-ups. DBFZ's (ss/a.mp4) is about a 2x zoom from its own wide
# frame, both fighters in it, then closer on Goku: here SS_CAM1_D 5.5 (both in the frame), SS_CAM2_D 4.0 (on him, Kirby's
# "slight"), both at least SS_CAM_MIN
SS_CAM1_T, SS_CAM1_D = 6, 5.5
SS_CAM2_AT, SS_CAM2_T, SS_CAM2_D = 8, 6, 4.0
SS_CAM_MIN = 3.5                     # a slight zoom: no closer than this (supamario_ui_test checks both)
# v10 (the user: "make secret sensation work closer to how it does in DBFZ. The counter once activated should stop the
# world, all effects, projectiles and stage until Supamario reaches his target (or a long timer elapses as a fallback)
# along with a time slowdown for Supamario. His movement speed should stop and then accelerate quickly"; the DBFZ clip
# 060b49a3, 60 fps: the counter at ~0.40 s, the beam and the opponent frozen from then on (still frozen at 1.4 s), Goku
# rising slowly over it to ~0.67 s (~16 frames), then across it in ~8 frames, landing behind the opponent with motion
# lines by ~0.80-0.97 s). The world stop: his MSC asks it (TIMER_6, V_STOP, renewed every frame: SS_STOP_ASK) from the
# counter's read until SS_ARRIVE frames after his arrival, at most SS_STOP_MAX frames (the fallback); the cave
# (exe_v46z_ui7, supamario_ui_cave.py ws_*) stops every other object (each frame a slowed frame in which nothing steps,
# his own step a normal one), pauses every effect but his and stops the stage, and lets them go when the asks stop (2
# frames' lease: a KO, a reset, the match's end or leaving the status ends it). He runs at SS_RATE (his slide's motion
# rate, the user's "3/4"); his travel holds (SS_HOLD frames, SS_HOLD_FRAC of the way, easing out) then accelerates over
# SS_DASH frames (ease-in: the speed grows to the arrival): SS_SLIDE_N frames, then SS_ARRIVE frames held behind the
# fighter (DBFZ: he lands, the world still stopped), then Fall and the world goes on
V_STOP = 0x0F000326                  # TIMER_6: the world stop asked (his MSC renews it; the cave reads > 0.5)
SS_STOP_ASK = 2.0
SS_HOLD, SS_DASH, SS_HOLD_FRAC = 16, 8, 0.08
SS_ARRIVE = 6
SS_STOP_MAX = 240                    # 4 s: the fallback (the slide always arrives at SS_SLIDE_N + SS_ARRIVE)
SS_RATE = 0.75
SS_CAM2_AT_V10 = SS_HOLD             # the closer zoom from the dash's start
SS_FX_FLASH_SIZE, SS_FX_BURST_SIZE = 0.7, 0.45
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
SS_SLIDE_N, SS_DEPTH = 14, 6.0       # v1-v9 (v10: SS_HOLD + SS_DASH)
SS_SLIDE_N = SS_HOLD + SS_DASH       # v10: 24 frames (the hold, then the dash)
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
      # v7: the sway's (BTL_CMN 493), converted after the others (its id follows; v8: 706's 492 / 230 gone)
      ('sway_line', 'BTL_CMN.eepk', 'SKI_lineX_S.emp', 'TransN', (0.0, 0.0, 0.0), 0.35),
      # v10 Secret Sensation's startup (the user: "the Ultra Instinct transformation has a built-in charge skill"; his
      # XV2 clip ui_in/charge_clip/charge.mp4: transformed, holding ki charge: a tall white-violet flame round him over
      # the aura, a burst as he lets go). XV2's ki charge is the character's aura row (aura_setting.aur): CMN.bac's
      # charge entry (453) switches its KiaiCharge on (BAC Aura type 3) and ends with KiryokuMax (type 4) and KiaiCharge
      # off. The transformed Ultra Instinct's row is aura 51: its HenshinStart 806 is the FOK aura (the same EMPs as the
      # skill's 848: Aura_LoopFOK, FOK_FootL, Aura_HLoopFOK ...), its KiaiCharge 803 = KTN_GKS_Loop on the pelvis (x0.6,
      # LoopCancel: it fades), KiryokuMax 804 = BoostGKS_End (x0.8 + x0.5). (Which row the skill's CUS aura 1 (MGT's cus
      # entry) selects is XV2's CusAuraData, in the executable; aura 51's content identifies it.) The charge from the
      # stance's start, faded at its recovery (SS_OFF) or at the counter's read, where KiryokuMax's burst plays (the
      # clip's burst as the charge ends). (1511_GKS_KTM, the user's first pick, is dropped: it plays the same aura types)
      ('ss_charge', 'BTL_AURA.eepk', 'KTN_GKS_Loop.emp', 'HipN', (0.0, 0.0, 0.0), 0.6),
      ('ss_release', 'BTL_AURA.eepk', 'BoostGKS_End.emp', 'HipN', (0.0, 0.0, 0.0), 0.8),
      # v10 (the user's XV2 idle clip ui_in/idle_clip/idle.mp4: "our version lacks the rising sparkles"): the transformed
      # aura row's own loop (aura 51's HenshinStart 806: the FOK parts the skill's 848 plays too, PLUS Aura_FOKpiace on
      # the pelvis x1.0 and x0.5, LoopCancel) has the sparkles the skill's 848 lacks: Aura_FOKpiace (small white
      # additive sprites, 30-frame life, rising): a sixth part of the MSC's aura (UI_FX_AURA6, the pelvis), XV2's
      # emission and colours (white stays white under the hue map), following him
      ('aura_piace', 'BTL_AURA.eepk', 'Aura_FOKpiace.emp', 'HipN', (0.0, 0.0, 0.0), 1.0)]
FX_V7 = ('sway_line',)
FX_V10 = ('ss_charge', 'ss_release', 'aura_piace')
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
AURA_SETS_V10 = AURA_SETS + ('aura_piace',)    # v10: the sparkles: colours / follow / life as the aura's (not smoothed:
                                               # XV2's rate and alpha kept, they're tiny)
AURA_SAT_MIN = 0.45                  # v6: every aura colour at least this saturated (XV2's pale smoke colours came out white
                                     # once additive: the steady render's big sprites hue 262 at 0.15-0.19); a soft
                                     # blue-violet (the user: "a slightly blue purple glow")
AURA_GAIN = 1.6                      # v6: every aura emitter's alpha x this (v5's smoothing kept XV2's average coverage; in
                                     # game the sprites round the bone centres are half inside his body: the halo outside
                                     # the silhouette wants more, the user: "clearly visible")
# v9: XV2's big pale sprites (Ref_FOK) are the distortion now, not light, so the aura's light is its flames and soft
# glows alone: rendered steady on a dark stage (supamario_ui_aura_render.py) v8 added 0.30, v9 at v6's gains 0.048; at
# AURA_GAIN / AURA_ADD_ALPHA below 0.12, white cores, sky-blue glows and violet flames apart (approximated: XV2's glare,
# its bloom round those additive sprites, has no Smash 4 counterpart)
AURA_GAIN, AURA_ADD_ALPHA = 3.5, 0.6
AURA_GENERATIONS = 2                 # v6: aura instances alive per part at most (the renewing one and the fading one)
# v6: the glow on the body while transformed (XV2's UI form: a white-lavender rim on the body and a blue-violet halo
# round the silhouette, the user's clips): Outline_Set (the fighter shaders' own rim light, inside the silhouette, with
# a slight tint) and Outline_Shell (the band outside it, added: a glow; its colour shows as given from exe_v46z_outline5),
# both held (Frames 0) until a KO / the match end / a training reset: at the burst, at the counter's end and in Wait1
# while transformed (again after a training reset or another move's outline)
# v9 (the user's v7 test: "the glow outline is very thick and bright and still only white"). The v7 clip (60 fps,
# 1302 x 806): the band outside his silhouette over the night sky (23, 20, 26) is (254, 251, 255), 4-6 px wide, and the
# body inside it washed pale lavender (his blue overalls (190, 183, 246)). v6-v8's band, (150, 135, 255) at 200 ADDED
# (Blend 1), adds at most 106 x k to green where k is what the game's encoding does to the shell's colour (1 if
# exe_v46z_outline5's hdrRange scaling did what it was meant to): green went up by 231, so k >= 2.2 (one layer), and with
# k >= 1.7 every channel of that light colour clips: white, whatever k is exactly. Not the hull's layering: drawn once
# per polygon part, Supamario's 13 parts (transformed, Wait) cover 87 % of the band once, 8 % twice (the bind pose,
# tools/outline_shell_layers.py). Inside, Outline_Set's rim at Alpha 600 (2.35 x the colour at the edges) with Tint 18
# lit and tinted the whole body. So: the band DRAWN OVER (Blend 0: no sum, it can't get past its own colour however many parts
# overlap) in a deep blue-violet that stays blue-violet for any k up to ~4 (k 1: (60, 40, 255); k 2: (120, 80, 255);
# k 4: (240, 160, 255), lavender), half see-through (130), thin (1.5 px of 1280 x 720); the rim a light lavender at 255
# (the colour at full only at the very edge), no tint. Approximated: k itself (not measured in game)
GLOW_RIM_RGB, GLOW_RIM_A, GLOW_RIM_TINT = (175.0, 165.0, 255.0), 255.0, 0.0
GLOW_SHELL_RGB, GLOW_SHELL_A, GLOW_SHELL_W = (60.0, 40.0, 255.0), 130.0, 1.5
GLOW_SHELL_BLEND = 0
GLOW_SHELL_K_MAX = 4.0               # the encoding scale (k) up to which the band stays blue-violet (tested)
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
SF_CMN = {}                          # v11: BTL_CMN's GHit / GHitSmk converted for Soaring Fist (SF.effects)
SF_SKILL = []                        # v11: (the skill's folder, vfx/cmn) for SF.effects
UI_SE = {'ui_start': ('CAR_BTL_M1510_MGT_00_Start_F22', 0.0),     # skill SE cue 0: entry 0 at 22
         'ui_success': ('CAR_BTL_M1510_MGT_01_Success', 0.0),     # skill SE cue 1: entry 0 at 205
         'ui_vanish': ('Vanish', 0.0),                             # CAR_BTL_CMN cue 96: entry 1 at 151
         'ui_sway': ('swing_05', 0.0)}                             # v7: CAR_BTL_CMN cue 5: the sway (CMN.bac 260) at 7
UI_SE.update(SF.SE)                  # v11: Soaring Fist's skill SE cues 0 (Bishi) / 1 (Fire)
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
         'UI_SWAY_F_AT': fl(SWAY_F_AT), 'UI_SWAY_N': fl(SWAY_N),
         'UI_SWAY_INV': fl(SWAY_INV), 'UI_SWAY_CW_ON': fl(SWAY_CW_ON), 'UI_SWAY_CW_OFF': fl(SWAY_CW_OFF),
         'UI_SWAY_IASA': fl(SWAY_IASA),
         'UI_SS_SLOW': '0x%X' % SS_SLOW, 'UI_SS_SLOW_FRAMES': '0x%X' % SS_SLOW_FRAMES, 'UI_SS_CAM1_T': '0x%X' % SS_CAM1_T,
         'UI_SS_CAM1_D': fl(SS_CAM1_D), 'UI_SS_CAM2_AT': fl(SS_CAM2_AT), 'UI_SS_CAM2_T': '0x%X' % SS_CAM2_T,
         'UI_SS_CAM2_D': fl(SS_CAM2_D)}
    # v10: the alternating sways, the dodge's short rush, Secret Sensation's world stop / travel / effects
    v.update({'UI_MOT_SWAY_BR': '0x%X' % MOT_SWAY_BR, 'UI_MOT_SWAY_FR': '0x%X' % MOT_SWAY_FR,
              'UI_SWAY_BR_AT': fl(SWAY_BR_AT), 'UI_SWAY_FR_AT': fl(SWAY_FR_AT), 'UI_V_SWAY': '0x%X' % V_SWAY,
              'UI_MOT_STRIKE_S': '0x%X' % MOT_STRIKE_S, 'UI_STRIKE_S_AT': fl(STRIKE_S_AT), 'UI_STRIKE_S_N': fl(STRIKE_S_N),
              'UI_V_STOP': '0x%X' % V_STOP, 'UI_SS_STOP_ASK': fl(SS_STOP_ASK), 'UI_SS_HOLD': fl(SS_HOLD),
              'UI_SS_DASH': fl(SS_DASH), 'UI_SS_HOLD_FRAC': fl(SS_HOLD_FRAC), 'UI_SS_ARRIVE': fl(SS_ARRIVE),
              'UI_SS_STOP_MAX': fl(SS_STOP_MAX), 'UI_SS_RATE': fl(SS_RATE), 'UI_SS_CAM2_AT': fl(SS_CAM2_AT_V10),
              'UI_FX_SS_CHARGE': '0x%X' % fx_id('ss_charge'), 'UI_FX_SS_RELEASE': '0x%X' % fx_id('ss_release'),
              'UI_FX_SS_CHARGE2': '0x%X' % fx_id('ss_charge_2'), 'UI_FX_AURA6': '0x%X' % fx_id('aura_piace'),
              'UI_FX_BURST': '0x%X' % fx_id('burst'), 'UI_SS_FX_BURST_SIZE': fl(round(0.9 * SCALE * SS_FX_BURST_SIZE, 3)),
              'UI_SS_RELEASE_SIZE': fl(round(0.8 * SCALE, 3)), 'UI_BONE_TRANS': '0x%X' % BONES['TransN']})
    import supamario_ui_fx11 as FX11
    v['UI_PIACE_Y'] = fl(FX11.PIACE_Y)   # v11: the sparkles on TransN at his hip's height (supamario_ui_fx11.piace)
    v.update(SF.msc_values())        # v11: Soaring Fist (tools/supamario_sf_build.py)
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


def freeze_box(hold=None):
    """XV2's BDM #0 at the counter's start: no damage, the attacker held (its hitstop to the first rush hit), Part 1"""
    import supamario_sledgehammer_build as SB
    return SB.hitbox(ID=1, Part=1, Bone=0, Damage=0.0, Angle=0, KBG=0, FKB=0, BKB=0, Size=FREEZE_SIZE, Y=5.0, Z=0.0,
                     Hitlag=0.0, SDI=0.0, Clang=0, Rebound=0, SFXLevel=0, SFXType=0, NoGFX=1, Flinchless=1,
                     HitstopFrames=RUSH_AT[0] if hold is None else hold, SelfHitstopFrames=0)


def sway_scripts():
    """v7: {script name: {part: body}} of the sways (SpecialAirLwLight's animation: the back sway from frame 0 (motion
    0x241, its own script), the forward sway from SWAY_F_AT (0x243, specialairlwlight_c3): a motion started at frame F
    starts its scripts' clock at F (the motion change's start frame, MotionAnimcmdModule vt +0x4C +0x20), so the
    script's first command waits for its F). v8: no counter script (the rush's own, speciallwheavy)"""
    def sway(at):
        return {'game': [], 'expression': [],
                'effect': timeline([(at + f, [graphic('sway_line', follow=False)]) for f in SWAY_LINE_AT]),
                'sound': timeline([(at + SWAY_SND_AT, [cmd('sound_effect', se_id('ui_sway'))])])}
    return {name: sway(at) for name, at in SWAY_AT.items()}     # v10: the R sways (0x242, 0x244) too


def white_on(frames):
    return [cmd('color_overlay', *WHITE_RGB, WHITE_A),
            cmd('outline_shell', 0, *RIM_RGB, RIM_A, RIM_WIDTH, int(frames), 4, 10, 0, 1)]


def white_off():
    return [cmd('terminate_overlays'), cmd('outline_shell', 0, 0.0, 0.0, 0.0, 0.0, RIM_WIDTH, 0, 0, 10, 0, 1)]


def glow_on():
    """v6: the transformed glow, held: the rim light (Outline_Set) and the blue-violet band (Outline_Shell: it replaces
    the white body's band, growing from where that one is); v9: the band drawn over (GLOW_SHELL_BLEND 0), thin"""
    return [cmd('outline_set', 0, *GLOW_RIM_RGB, GLOW_RIM_A, GLOW_RIM_TINT, 0, GLOW_IN, GLOW_OUT, 0),
            cmd('outline_shell', 0, *GLOW_SHELL_RGB, GLOW_SHELL_A, GLOW_SHELL_W, 0, GLOW_IN, GLOW_OUT, 0,
                GLOW_SHELL_BLEND)]


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
    return cmd('graphic_effect2', fx_id(key), b, x, y, z, 0.0, 0.0, 0.0, e[5] * SCALE * size, 0.0, 0.0, 0.0, 0.0, 0.0,
               0.0, 1)


# v10: the non-following effects are Graphic_Effect2 (v1-v9 Graphic_Effect: the game's FOOT_EFFECT, whose handler
# 0x02BE1444 asks EffectModule vt +0x32C and plays nothing when foot effects are off, as in the air: docs/native-notes.md
# "Graphic_Effect can be refused"; the transformation's counter starts where he was, in the air too)
# v10 (the user: "the counter still doesn't have any visual effects"): XV2's rush hits (BDM #1) and finisher (#2) carry
# Effect1 = BTL_CMN effect 0 (Btl_HitLOD x1.5 + Btl_HitS x0.8, camera-facing, at the hit): the yellow bursts on every hit
# of the user's clips (udclip e 92-150); the scripts had none (only the vanish). Btl_HitLOD is Sledgehammer's converted
# set already (0x0341005C), Btl_HitS isn't in the vfx/cmn files sent (BTL_CMN.eepk names it, its .pbind.emb doesn't hold
# it): Time Skip's Btl_HitL (BTL_CMN 2's, the same burst bigger: 0x0341005F / 60) stands in for it, x HIT_S_FOR_L; the
# LOD burst is Time Skip's capped copy of it (0x03410061, the user found the uncapped one too bright)
HIT_FX = (('hitlod', 1.5), ('hitl', 0.8), ('hitl_2', 0.8))
HIT_S_FOR_L = 0.7                    # Btl_HitS's 0.8 against Btl_HitL's 0.8: HitS is the smaller hit (approximated)


def hit_fx_ids():
    import supamario_timeskip_build as TS
    return {'hitlod': TS.FX_LOD_ID, 'hitl': TS.FX_IDS['hitl'], 'hitl_2': TS.FX_IDS['hitl_2']}   # (Time Skip's own capped
                                                                                                # LOD copy: its hit's)


def hit_fx(size=1.0):
    """v10: XV2's hit effect (BTL_CMN 0) at the rush hitbox's centre (in front of him)"""
    ids = hit_fx_ids()
    out = []
    for key, sc in HIT_FX:
        k = 1.0 if key == 'hitlod' else HIT_S_FOR_L
        out.append(cmd('graphic_effect2', ids[key], BONES['TransN'], 0.0, RUSH_Y, RUSH_Z, 0.0, 0.0, 0.0,
                       round(sc * SCALE * size * k, 3), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1))
    return out


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
                                     (anim.frame_of(anim.STRIKE, 1, 170), [graphic('vanish', follow=False)])] +
                                    [(f, hit_fx()) for f in RUSH_AT] + [(STRIKE_AT, hit_fx(FINISH_FX))] + [
                                     # v6: no aura here: the counter ends the transformation, so the MSC's aura
                                     # (ui_aura, renewed by fading) is on from its first frame; this one doubled it
                                     (CNT_END, white_to_glow())]),
              anim.DODGE: sway_scripts()['specialairlwlight']['effect'], anim.SS: ss_stance_fx()}
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


FINISH_FX = 1.6                      # v10: the finisher's hit effect x this (XV2's BDM #2: the same effect 0; the clips'
                                     # finisher burst and its ring are bigger than a rush hit's)


def short_rush_scripts():
    """v10: the dodge's short rush (motion 0x236 speciallwheavy_c2, from STRIKE_S_AT of SpecialLwHeavy's animation: its
    scripts' clock starts there): the freeze to the first hit, RUSH_S_N held hits at RUSH_S_AT, the finisher at
    STRIKE_S_HIT, XV2's hit effect on each, the vanish at 0 and CNT_S_VANISH2, the white body to CNT_S_END"""
    at = STRIKE_S_AT
    rush = []
    for f in RUSH_S_AT:
        rush += [(at + f, [cmd('hit_log_clear', 0), rush_box(), cmd('hitbox_hold', 0, 2)]),
                 (at + f + 2, [cmd('remove_all_hitboxes')])]
    game = timeline([(at, [freeze_box(RUSH_S_AT[0])]), (at + 1, [cmd('remove_all_hitboxes')])] + rush +
                    [(at + STRIKE_S_HIT, [cmd('hit_log_clear', 0), strike_box()]),
                     (at + STRIKE_S_HIT + 3, [cmd('remove_all_hitboxes')]), (at + CNT_S_END, silver_on())])
    effect = timeline([(at, [graphic('vanish', follow=False)] + white_on(CNT_S_END)),
                       (at + CNT_S_VANISH2, [graphic('vanish', follow=False)])] +
                      [(at + f, hit_fx()) for f in RUSH_S_AT] + [(at + STRIKE_S_HIT, hit_fx(FINISH_FX)),
                                                                 (at + CNT_S_END, white_to_glow())])
    sound = timeline([(at, [cmd('sound_effect', se_id('ui_vanish'))]),
                      (at + CNT_S_SND, [cmd('sound_effect', se_id('ui_success'))])])
    expression = timeline([(at + STRIKE_S_HIT, [cmd('rumble', 0x12, 0)])])
    return {'game': game, 'effect': effect, 'sound': sound, 'expression': expression}


def ss_stance_fx():
    """v10: Secret Sensation's stance (SpecialAirLwHeavy's effect script): his transformed aura's ki charge (KiaiCharge:
    KTN_GKS_Loop,
    following his pelvis) from its frame 0, faded (Terminate 0: emission stopped, the sprites live out) at its recovery
    (SS_OFF: the counter window's end); the counter's read fades it too (his MSC, ss_counter)"""
    on = [graphic('ss_charge')]
    off = [cmd('terminate_graphic_effect', fx_id('ss_charge'), 0, 0)]
    if 'ss_charge_2' in FX_IDS or not FX_IDS:     # KTN_GKS_Loop's 17 emitters: two sets, played together
        on.append(cmd('external_graphic', fx_id('ss_charge_2'), *on[0].params[1:]))
        off.append(cmd('terminate_graphic_effect', fx_id('ss_charge_2'), 0, 0))
    return timeline([(0, on), (SS_OFF, off)])


def extra_scripts():
    """{script name: {part: body}}: the custom-move slots the build writes (v7 / v10's sways, v10's short rush)"""
    out = dict(sway_scripts())
    del out['specialairlwlight']
    out['speciallwheavy_c2'] = short_rush_scripts()
    if FX_IDS:                   # v11: Soaring Fist (the transformed forward smash: specialairlwheavy_c2 / _c3)
        import supamario_godfist_build as GB
        out.update(SF.body_scripts(se_id, dict(SF_CMN, MHitSmk=GB.CMN_FX['MHitSmk'], MHit=GB.CMN_FX['MHit'])))
    return out


# v9 (the user's v7 test: "the aura and glowing outline disappear after Time Skip / Jump Spike is used until he
# lands"). The glow: Time Skip's outline is its own Outline_Shell (one shell per object), renewed through the dash /
# the stop and ended (Alpha 0) at its end (the dash's 75, the punch): the transformed band was replaced and then ended,
# and only Wait1's game script (silver_scripts) put it back, i.e. at the landing. Now every effect script that ends an
# Outline_Shell and isn't Ultra Instinct's own gets, after its last command, the glow again when transformed (TIMER_0 >
# 1500: glow_on, which replaces Time Skip's fading band); and the motions a move can end in before its own end runs
# (GLOW_AFTER: the falls and landings) put it on at their frame 0 when transformed. (The aura's part was its emitters
# left in the world: aura_follow below)
GLOW_AFTER = ('fall', 'fallf', 'fallb', 'fallaerial', 'fallaerialf', 'fallaerialb', 'landinglight', 'landingheavy',
              'landingfallspecial')


def glow_restore():
    """the glow put back while transformed: Float_Var_Compare(TIMER_0 > UI_TRANSFORMED_OVER) True { glow_on() }"""
    return if_var(cave.V_FORM, 5, UI_TRANSFORMED_OVER, glow_on())


def strip_glow_restore(cmds):
    """the commands without any glow_restore() block (the earlier moves' tests compare their scripts without it)"""
    blk = [(c.ident, c.params) for c in glow_restore()]
    out, i = [], 0
    while i < len(cmds):
        if [(c.ident, c.params) for c in cmds[i:i + len(blk)]] == blk:
            i += len(blk)
            continue
        out.append(cmds[i])
        i += 1
    return out


def restore_glow(f, own):
    """v9: glow_restore() after the last command of every effect script (not in `own`) ending an Outline_Shell, and at
    frame 0 of the GLOW_AFTER motions' (new ones made); [(script hash, 'end' / 'start')]"""
    shell = acmd.BY_NAME['outline_shell']
    done = []
    for h in sorted(f.scripts):
        body = f.scripts[h]
        if h in own or not any(c.ident == shell and c.params[4] == 0.0 for c in body):
            continue
        assert body[-1].ident == acmd.END, hex(h)
        f.scripts[h] = body[:-1] + glow_restore() + body[-1:]
        done.append((h, 'end'))
    for name in GLOW_AFTER:
        h = acmd.crc(name)
        assert h not in own, name
        f.scripts[h] = glow_restore() + (f.scripts.get(h) or [acmd.Command(acmd.END)])
        done.append((h, 'start'))
    return done


def scripts(body_dir):
    own = {acmd.crc(n) for n in list(SCRIPT.values()) + EXTRA_SCRIPTS + list(silver_scripts())}
    for part, bodies in scripts_for().items():
        path = os.path.join(body_dir, part + '.bin')
        f = acmd.ACMDFile.load(path)
        for m, body in bodies.items():
            f.scripts[acmd.crc(SCRIPT[m])] = body + [acmd.Command(acmd.END)]     # F.L.U.D.D.'s replaced
        if part == 'effect':
            restore_glow(f, own)
        for name, bodies in extra_scripts().items():   # v7 / v10: the custom-move slots' scripts (F.L.U.D.D.'s replaced)
            f.scripts[acmd.crc(name)] = bodies[part] + [acmd.Command(acmd.END)]
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
            if em is None or p.field(em, 'shader_index') in REF_SHADERS:
                continue                    # v9: XV2's refraction emissions keep XV2's rate and strength
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


# ---------------------------------------------------------------- v9: the aura on him, XV2's colours, XV2's distortion
# v9 (the user's v7 test: "the aura seems to trail behind Supamario rather than stay attached to him", "the aura and
# glowing outline disappear after Time Skip / Jump Spike until he lands", "the aura doesn't have any of its blue or
# white hue mixed in", "please add the slight distortion around the aura like Xenoverse does"; the v7 clip: the aura's
# sprites left in a trail as he moves, his Time Skip dash / the jump without them near him).
# 1. The trail: every converted aura emitter had follow type 1 (ptcl 0x310: none; the particles copy the emitter's
#    matrices at birth and stay where they were born, docs/ptcl-format.md), the converter's default. XV2 attaches 848's
#    parts to their bones with PositionUpdate + RotateUpdate (BTL_AURA.eepk). Now AURA_FOLLOW 2 (position only: the
#    particles move with the bone, upright: his rotations don't spin the sprites), every vertex program of theirs drawing
#    it (eft_vertex.features 'follow'). The same was the Time Skip "disappearance": at the dash's / the jump's speed the
#    particles (alpha 0 at birth, faded in over a fifth of their life) were all behind him.
AURA_FOLLOW = 2
# 2. The colours: XV2's aura nodes have two colours (EnableSecondaryColor: Color2 the texture's bright core, Color1 its
#    edge: white cores, blue / cyan edges; 15 of 19 nodes), and none animates its colour (only its transparency keys):
#    the converter kept Color1 alone, and v3-v8's tint_aura turned every key to hue 262 with a saturation floor of
#    0.45: one flat violet. Now (aura_colours): the two-colour programs (combiner 2: colour 1 + (colour 0 - colour 1) x
#    texture) get Color2 as colour 0 (the core) and Color1 as colour 1 (the edge); the one-colour ones (combiner 1) the
#    mean of the two (Time Skip's _secondary rule); each colour's hue moved from XV2's blue / cyan range onto the clip's
#    (AURA_HUE_MAP: XV2 180 -> 215 sky blue, 240 -> 280 violet, linear: the clip's mix of blue glow and violet wisps),
#    its saturation and value XV2's (white stays white: the v6 floor gone)
AURA_HUE_MAP = ((180.0, 215.0), (240.0, 280.0))
# 3. The distortion: XV2's aura draws its heat haze with two emissions of its own, Aura_LoopFOK's and FOK_FootL's
#    sprite_2_1_* (material Ref_FOK_L / Ref_FOK_R: a refraction shader; MatScale0 (+-0.05, -0.5)), which the converter
#    drew as big pale colour sprites (the 64 x 64 smoke: v4-v8's "purple patches"), and v5-v8's UiHaze (the fireball's
#    refraction, appended at 3-5 units, 0.45 strength, left behind as he moved) was too small and faint to see. Now those
#    four ARE the distortion (aura_refraction): each takes Mario's fireball's refraction emitter (PtcMarioFireball
#    'refraction1': its program reads the frame buffer, frameBufferTexture_CROSS, and draws it offset by its distortion
#    map: draw path 11, the vanilla way Smash 4 bends the picture) with XV2's emission kept (where, how many, how long,
#    how big, its 0 -> 0.6 -> 0 transparency as the bend's strength x REF_STRENGTH), following him (AURA_FOLLOW)
REF_MATERIALS = ('Ref_FOK_L', 'Ref_FOK_R')
REF_STRENGTH = 1.0
# v10 (the user's XV2 idle clip: "our distortion haze is less aggressive and closer to the user"; the clip, 1080p, his
# body ~560 px tall: the background is bent up to ~120-190 px over his head and ~150 px beyond his sides, i.e. a quarter
# to a third of his height round him, the rocks behind him visibly bent): the bend twice as strong (REF_STRENGTH x2: the
# program's offset is its alpha x its distortion map) and the refraction sprites and their emission volume x REF_WIDE
REF_STRENGTH = 2.0
REF_WIDE = 1.5
REF_COPY = ('one_time', 'volume_type', 'volume_radius', 'volume_sweep_start', 'volume_sweep_param',
            'volume_surface_random', 'volume_sweep_start_random', 'emitter_matrix', 'emitter_scale',
            'emitter_rotation', 'emitter_translation', 'emit_rate', 'start_frame', 'emit_start', 'end_frame',
            'emit_interval', 'emit_interval_random', 'figure_velocity', 'init_velocity_random', 'emitter_velocity',
            'emit_direction', 'dispersion_angle', 'spread_vec', 'air_resistance', 'gravity', 'world_gravity',
            'ptcl_life', 'ptcl_life_random', 'alpha_init', 'alpha_diff21', 'alpha_diff32', 'alpha_section1',
            'alpha_section2', 'scale_sections', 'scale_random', 'scale', 'scale_init_ratio', 'scale_diff21',
            'scale_diff32', 'rotation_init', 'rotation_random', 'rotation_velocity', 'rotation_velocity_random',
            'rotation_attenuation')


def aura_set_names():
    return ['PtcSupamarioUi' + [x for x in FX if x[0] == key][0][2][:-4] for key in AURA_SETS_V10]


def xv2_aura_nodes(cmn_dir):
    """{(set name, emitter name): XV2's emission node} of the aura's EMPs (BTL_AURA.eepk's package)"""
    import xv2vfx
    out = {}
    with tempfile.TemporaryDirectory() as pkg:
        for fn in os.listdir(cmn_dir):
            if not fn.lower().endswith('.eepk') or fn == 'BTL_AURA.eepk':
                os.symlink(os.path.abspath(os.path.join(cmn_dir, fn)), os.path.join(pkg, fn))
        pk = xv2vfx.load_package(pkg, strict=False)
    for key in AURA_SETS_V10:
        emp = [x for x in FX if x[0] == key][0][2]
        for _d, n in xv2vfx.emp_nodes(pk['emp'][emp]):
            if n['NodeType'] == 'Emission':
                k = ('PtcSupamarioUi' + emp[:-4], n['Name'])
                assert k not in out, k
                out[k] = n
    return out


def hue_map(h):
    """XV2's hue (degrees) onto the aura's (AURA_HUE_MAP, linear, clamped to its ends)"""
    (a0, b0), (a1, b1) = AURA_HUE_MAP
    t = min(1.0, max(0.0, (h - a0) / (a1 - a0)))
    return b0 + (b1 - b0) * t


def ui_colour(rgb):
    """an XV2 colour (0-1) with its hue moved by hue_map, its saturation and value kept"""
    import colorsys
    v = max(rgb)
    if v <= 0:
        return tuple(float(c) for c in rgb)
    h, s_, _v = colorsys.rgb_to_hsv(*[c / v for c in rgb])
    return tuple(c * v for c in colorsys.hsv_to_rgb(hue_map(h * 360.0) / 360.0, s_, 1.0))


def aura_colours(p, rep, nodes):
    """v9: XV2's two colours per emitter (EnableSecondaryColor), their hues moved (ui_colour); {set: [(emitter,
    combiner, colour 0, colour 1)]}"""
    done = {}
    for name in aura_set_names():
        si = p.find_set(name)
        for e in p.sets[si]['emitters']:
            em = e['data']
            if em is None or p.field(em, 'shader_index') in REF_SHADERS:
                continue
            n = nodes[(name, p.emitter_name(em))]
            t = n['EmissionNode']['Texture']
            c1 = tuple(t['Color1'])
            c2 = tuple(t['Color2']) if 'EnableSecondaryColor' in n['NodeFlags_names'] else c1
            comb = struct.unpack_from('>I', em, 0x314)[0]
            if comb == 2:
                k0, k1 = ui_colour(c2), ui_colour(c1)
            else:
                k0 = k1 = ui_colour(tuple((a + b) / 2.0 for a, b in zip(c1, c2)))
            for track, k in ((0, k0), (1, k1)):
                keys = p.color_keys(em, track)
                p.set_color_keys(em, track, [tuple(k) + tuple(x[3:]) for x in keys])
            done.setdefault(name, []).append((p.emitter_name(em), comb, tuple(round(c, 3) for c in k0),
                                              tuple(round(c, 3) for c in k1)))
        rep[name]['colours'] = done.get(name, [])
    return done


REF_SHADERS = set()                  # the refraction template's shader index (filled by aura_refraction / ref_shader)


def ref_shader(p):
    """the shader index of the refraction template (PtcMarioFireball 'refraction1'), noted in REF_SHADERS"""
    src = p.find_set(HAZE_SRC[0])
    em = [e['data'] for e in p.sets[src]['emitters'] if e['data'] is not None and
          p.emitter_name(e['data']) == HAZE_SRC[1]][0]
    REF_SHADERS.add(p.field(em, 'shader_index'))
    return p.field(em, 'shader_index')


def aura_refraction(p, rep, nodes):
    """v9: XV2's Ref_FOK emissions as the fireball's refraction (its bytes, XV2's emission fields); [(set, name)]"""
    src = p.find_set(HAZE_SRC[0])
    ks = [k for k, e in enumerate(p.sets[src]['emitters']) if e['data'] is not None and
          p.emitter_name(e['data']) == HAZE_SRC[1]]
    assert ks, HAZE_SRC
    base = p.emitter_bytes(src, ks[0])
    REF_SHADERS.clear()
    REF_SHADERS.add(p.field(base, 'shader_index'))
    done = []
    for name in aura_set_names():
        si = p.find_set(name)
        for e in p.sets[si]['emitters']:
            em = e['data']
            if em is None:
                continue
            n = nodes[(name, p.emitter_name(em))]
            if n['EmissionNode']['Texture']['MaterialRef'] not in REF_MATERIALS:
                continue
            new = bytearray(base)
            struct.pack_into('>I', new, 0x38, struct.unpack_from('>I', em, 0x38)[0])     # its own name
            for fld in REF_COPY:
                p.set_field(new, fld, p.field(em, fld))
            for fld in ('alpha_init', 'alpha_diff21', 'alpha_diff32'):
                p.set_field(new, fld, p.field(new, fld) * REF_STRENGTH)
            for fld in ('scale', 'volume_radius'):                 # v10: wider
                v = p.field(new, fld)
                p.set_field(new, fld, [x * REF_WIDE for x in v] if isinstance(v, (list, tuple)) else v * REF_WIDE)
            e['data'] = new
            p.dirty_layout = True
            done.append((name, p.emitter_name(new)))
        rep[name]['refraction'] = [x[1] for x in done if x[0] == name]
    return done


# v10 (the user's v9 clips: "the aura still follows a bit behind Supamario than stay attached to him"; the jump in clip
# 3407709b: a bright purple blob left on the stage's edge where he took off and a column of white specks up to him, for
# ~0.8 s). eft's two particle kinds follow differently (the game's code):
# - CPU particles (emitter flag 0x00800000 off): at emission a follow-0 particle points at the emitter's live matrices,
#   1 / 2 at copies (0x04A5C89C); every frame the CPU update (0x04A624E4 / 0x04A62AE8) copies the emitter's
#   translation into a follow-2 particle's copies (`cmpwi r0, 2` at 0x04A62554 / 0x04A62AFC): v9's follow 2 works there.
# - GPU particles (flag 0x00800000: the converter's additive billboards, shader 39, the flare template's, and v9's
#   refraction, shader 7): their record is written once at emission (0x04A6680C-0x04A6690C: the local place p + 0x14,
#   the emitter matrix [p + 0x108] copied into the record's EmtMat), never again (the GPU calc 0x04A65FC0 calls neither
#   update), and the program places the particle with that birth matrix (v_inEmtMat0-2): it stays where it was born
#   whatever the follow type. eft compiles each program per follow kind: key byte 4 bit 0x04 is the variant that
#   reads the LIVE emitter matrix (emm) instead; every vanilla emitter on such a variant has follow 0 (c6 / c4 / 06
#   keys: Pit's flash1, Ganon's Majinken, Lucas's PK Freeze, Mario's own refraction1_Copy1), every one on the plain
#   variant follow 1. 10 of the 19 aura emitters were GPU ones (the glows and the refraction): the trail.
# Now (aura_follow): a GPU emitter gets its program's follow variant (the same key but byte 4 | 0x04 and the same pixel
# program: Supamario's own shader 8 for the refraction (7's), Pit's shader 13 for the glows (39's), Rosalina's 59 for
# KTN_GKS_Loop's streaks (62's): imported from TWIN_PTCL, vanilla .ptcl files) and follow 0 (it reads the live matrix: on him every frame, XV2's PositionUpdate +
# RotateUpdate); a CPU emitter keeps follow 2 (refreshed every frame). The look (pixel program, colours) unchanged
AURA_FOLLOW_CPU = 2
AURA_FOLLOW_GPU = 0
GPU_FLAG = 0x00800000
TWIN_PTCL = []                       # the vanilla .ptcl the follow variants come from (main's --twin-ptcl)
FOLLOW_SETS = AURA_SETS_V10 + ('ss_charge',)


def is_gpu(em):
    return bool(struct.unpack_from('>I', em, 4)[0] & GPU_FLAG)


def follow_variant(p, sh, others):
    """v10: the follow variant of shader `sh` (its key entry with byte 4 | 0x04, every other key byte the same, the same
    pixel program), in p or imported from one of `others` (vanilla Ptcls): its index in p"""
    import eft_pixel
    want = bytearray(p.shader_entry(sh))
    if want[4] & 0x04:
        return sh
    want[4] |= 0x04
    pix = eft_pixel.disassemble(p.shader_binary(sh))
    for q in [p] + list(others):
        for i in range(q.shader_count()):
            e = q.shader_entry(i)
            if e[:0x68] == bytes(want[:0x68]) and eft_pixel.disassemble(q.shader_binary(i)) == pix:
                return i if q is p else p.import_shader(q, i)
    raise SystemExit('supamario_ui_build: no follow variant of shader %d (key %s) in %s' % (
        sh, bytes(want[:0x10]).hex(), [getattr(q, 'path', '?') for q in others]))


def aura_follow(p, rep):
    """v9: every aura emitter's particles follow him; v10: CPU ones follow 2, GPU ones follow 0 on their program's
    follow variant (follow_variant)"""
    import ptcl
    others = []
    for path in TWIN_PTCL:
        q = ptcl.Ptcl(open(path, 'rb').read())
        q.path = path
        others.append(q)
    n = 0
    names = []
    for key in FOLLOW_SETS:
        name = 'PtcSupamarioUi' + [x for x in FX if x[0] == key][0][2][:-4]
        names.append(name)
        if name + '_2' in rep:
            names.append(name + '_2')
    for name in names:
        si = p.find_set(name)
        for e in p.sets[si]['emitters']:
            em = e['data']
            if em is None:
                continue
            if is_gpu(em):
                p.set_field(em, 'shader_index', follow_variant(p, p.field(em, 'shader_index'), others))
                struct.pack_into('>I', em, 0x310, AURA_FOLLOW_GPU)
            else:
                struct.pack_into('>I', em, 0x310, AURA_FOLLOW_CPU)
            n += 1
        rep.setdefault(name, {})['follow'] = {'cpu': AURA_FOLLOW_CPU, 'gpu': AURA_FOLLOW_GPU}
    return n


# v10: the sparkles' spread. XV2's Aura_FOKpiace is a hierarchy: edge_1_1 (a filled Circle, EmitFromArea, radius 0.3 m,
# 0.5 m under the pelvis) -> omni / omni_1 (points, 0.3 m/s up) -> sprite / sprite_1 (30 frames): the converter keeps
# the emissions' own point and the parents' offset (-0.5 m), not the grandparent's circle: every sparkle from one point.
# piace_volume gives them XV2's circle (volume type 3, circle fill, XZ plane, radius PIACE_RADIUS)
PIACE_RADIUS = round(0.3 * 8.5, 3)       # xv2_to_ptcl.UNIT


def piace_volume(p, rep):
    name = 'PtcSupamarioUiAura_FOKpiace'
    for e in p.sets[p.find_set(name)]['emitters']:
        if e['data'] is not None:
            p.set_field(e['data'], 'volume_type', 3)
            p.set_field(e['data'], 'volume_radius', [PIACE_RADIUS, 0.0, PIACE_RADIUS])
    rep[name]['volume'] = (3, PIACE_RADIUS)


FLIP_PTCL = []                       # v11: vanilla .ptcl files holding the aura programs' flipbook variants (--flip-ptcl)
FRT_SKILL = []                       # v11: Time Skip's skill folder (its streaks' node types)


def v11_fixes(p, cmn_dir, rep):
    """v11 (tools/supamario_ui_fx11.py): the type-3 streaks' rotBasis (Secret Sensation's / Time Skip's aura far
    below him), the aura sprites' sprite sheets (flipbooks) and spread, the sparkles"""
    import ptcl
    import xv2vfx
    import supamario_ui_fx11 as FX11
    aura_pkg = xv2vfx.load_package(FX11.pkg_dir(cmn_dir, 'BTL_AURA.eepk'), strict=False)
    others = []
    for path in FLIP_PTCL:
        q = ptcl.Ptcl(open(path, 'rb').read())
        q.path = path
        others.append(q)
    names = []
    for key in AURA_SETS + ('ss_charge',):
        name = 'PtcSupamarioUi' + [x for x in FX if x[0] == key][0][2][:-4]
        names.append(name)
        if name + '_2' in rep:
            names.append(name + '_2')
    FX11.aura_flipbook(p, aura_pkg, names, others, rep)
    FX11.aura_spread(p, aura_pkg, names[:len(AURA_SETS)], rep)
    FX11.piace(p, rep)
    pkgs = [aura_pkg]
    for d in FRT_SKILL + SF_SKILL[:1]:
        pkgs.append(xv2vfx.load_package(FX11.pkg_dir(d), strict=False))
    FX11.streak_basis(p, pkgs, rep)


def aura_life(p):
    """v6: the longest particle life (+ its random part) of the aura sets' emitters (haze included): a faded generation
    is gone this long after its fade"""
    out = 0
    for key in AURA_SETS_V10:
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
    batches = [(ep, [x[2] for x in FX if x[1] == ep and x[0] not in FX_V7 + FX_V10])
               for ep in ('BTL_AURA.eepk', 'BTL_CMN.eepk')]
    batches.append(('BTL_CMN.eepk', [x[2] for x in FX if x[0] in FX_V7]))   # v7: after (the earlier ids kept)
    for ep in ('BTL_CMN.eepk', 'BTL_AURA.eepk'):                        # v10: after (the earlier ids kept)
        emps = [x[2] for x in FX if x[0] in FX_V10 and x[1] == ep]
        if emps:                                                        # (an empty list converts the whole EEPK)
            batches.append((ep, emps))
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
        by_emp, by_emp2 = {}, {}
        for si, name, chunk in made:
            idx = e.add(si + 1)
            by_emp.setdefault(name.replace('PtcSupamarioUi', '') + '.emp', idx)
            if name.endswith('_2'):              # v10: an EMP of more than 16 emitters: its second set (KTN_GKS_Loop)
                by_emp2[name[len('PtcSupamarioUi'):-2] + '.emp'] = idx
            rep[name] = {'set': si, 'emitters': [en for _b, en, _n in chunk]}
        for key, ep, emp, _bone, _o, _s in FX:
            if ep == eepk and emp in emps:
                FX_IDS[key] = 0x03410000 | by_emp[emp]
                if emp in by_emp2:
                    FX_IDS[key + '_2'] = 0x03410000 | by_emp2[emp]
    nodes = xv2_aura_nodes(cmn_dir)
    aura_refraction(p, rep, nodes)       # v9: XV2's own distortion (v5-v8: haze(), the fireball's, appended)
    aura_colours(p, rep, nodes)          # v9: XV2's two colours (v3-v8: tint_aura, one flat violet)
    piace_volume(p, rep)                 # v10: the sparkles from XV2's circle
    smooth_aura(p, rep)
    aura_follow(p, rep)                  # v9: on him (v1-v8: left where they were born)
    if SF_SKILL:                         # v11: Soaring Fist's effects, after every earlier set
        SF_CMN.update(SF.effects(p, e, SF_SKILL[0], SF_SKILL[1], rep))
    v11_fixes(p, cmn_dir, rep)           # v11: the streaks' place, the aura's flipbooks and spread, the sparkles
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
                                    os.path.join(ts_args['ts_skill'], '1352_HIK_DSH.ean'),
                                    os.path.join(ts_args['sf_skill'], '1510_GKS_HKN.ean'))
    SF_SKILL[:] = [ts_args['sf_skill'], ts_args['sh']['fd']['cb']['gf']['cmn_vfx']]
    FRT_SKILL[:] = [ts_args['frt']]
    rep = effects(ts_args['sh']['fd']['cb']['gf']['cmn_vfx'], os.path.join(fdir, 'effect', 'supamario'))
    sound_bank(fdir, out_dir, ui_se_wav)
    import nud
    base_meshes = nud.read(os.path.join(sm_dir, 'model', 'body', 'c00', 'model.nud'))
    OVERLAYS[:] = [o['name'] for o in model.overlays(base_meshes)]
    MESH_INDEX.clear()
    MESH_INDEX.update(mesh_indices([m.name for m in base_meshes]))
    scripts(os.path.join(fdir, 'script', 'animcmd', 'body'))
    GB.msc(os.path.join(fdir, 'script', 'msc', 'supamario.mscsb'))
    with tempfile.TemporaryDirectory(dir=out_dir) as tmp:      # v11: Soaring Fist's projectile (article 0)
        SF.write_weapon(fdir, sm_dir, tmp)
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
            '--png', '--cmn-ean', '--twin-ptcl', '--sf-skill', '--flip-ptcl')
    for k in keys:
        if k in a:
            i = a.index(k)
            opts[k] = a[i + 1]
            del a[i:i + 2]
    if len(a) != 2 or any(k not in opts for k in keys[:13]):
        sys.exit(__doc__)
    if '--flip-ptcl' in opts:
        FLIP_PTCL[:] = opts['--flip-ptcl'].split(',')   # v11: vanilla .ptcl files holding the flipbook variants
    if '--twin-ptcl' in opts:
        TWIN_PTCL[:] = opts['--twin-ptcl'].split(',')   # v10: vanilla .ptcl files holding the programs' follow variants
    gf = {'ean': opts['--ean'], 'cmn_vfx': opts['--cmn-vfx'], 'skill_vfx': opts.get('--skill-vfx'),
          'cmn_se': opts.get('--cmn-se'), 'stb': opts.get('--stb')}
    cb = {'skill': opts['--skill'], 'se_wav': opts['--se-wav'], 'gf': gf}
    fd = {'fd_skill': opts['--fd-skill'], 'fd_se_wav': opts['--fd-se-wav'], 'cb': cb}
    sh = {'sh_skill': opts['--sh-skill'], 'sh_se_wav': opts['--sh-se-wav'], 'fd': fd}
    ts = {'ts_skill': opts['--ts-skill'], 'ts_se_wav': opts['--ts-se-wav'], 'frt': opts['--frt-skill'], 'sh': sh,
          'png': opts.get('--png'), 'halo': halo, 'cmn_ean': opts.get('--cmn-ean'), 'sf_skill': opts['--sf-skill']}
    print(build(a[0], a[1], opts['--ui-skill'], opts['--ui-se-wav'], ts))
    print('sounds: ' + ', '.join('%s 0x%08X' % kv for kv in SE_IDS.items()))
    print('effects: ' + ', '.join('%s 0x%08X' % kv for kv in FX_IDS.items()))
    print('transformation %d frames (window %d-%d), counter %d (rush %s, finisher %d); v7 sway %d (intangible %d, the '
          'counter window %d-%d: the rush)' % (
              FORM_N, CW_ON, CW_OFF, STRIKE_N, RUSH_AT, STRIKE_AT, SWAY_N, SWAY_INV, SWAY_CW_ON, SWAY_CW_OFF))


if __name__ == '__main__':
    # through the module itself: supamario_kame_build's MSC values import supamario_ui_build, whose FX_IDS / SE_IDS
    # must be the ones this run fills (not __main__'s copy)
    import supamario_ui_build
    supamario_ui_build.main()
