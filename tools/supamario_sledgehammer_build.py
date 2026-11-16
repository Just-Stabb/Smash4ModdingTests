#!/usr/bin/env python3
"""Supamario's Sledgehammer (the AIR down special, status 0x155 in the air; Dragon Ball Xenoverse 2's Super skill
164_VGT_HMR, Vegeta's): the package, built over Fake Death's (tools/supamario_fakedeath_build.py, which runs Core
Breaker's and the Super God Fist's first; their files stay theirs: only the air down special's motions / scripts, the
effect bank's new sets, three new tones and the MSC change).

  python3 -I tools/supamario_sledgehammer_build.py SUPAMARIO_DIR OUT_DIR --sh-skill 164_VGT_HMR_DIR
        --sh-se-wav SH_WAV_DIR [Fake Death's: --fd-skill ... --fd-se-wav ... --skill ... --se-wav ... --ean ...
        --cmn-vfx VFX_CMN_DIR --skill-vfx ... --cmn-se ... --stb ...] [--png SHEET.png]

SH_WAV_DIR: the skill SE (CAR_BTL_S164_HMR_SE.acb cues 0 Charge / 1 Furi) and CAR_BTL_CMN.acb cue 42 swing_42
(tools/supamario_sledgehammer_xv2.py se-extract / tools/xv2acb.py extract + tools/xv2acb_decode.mjs + `se`). Writes
OUT_DIR/fighter/supamario (Fake Death's build, then): motion/body (SpecialAirLwStart / SpecialAirLwHold:
tools/supamario_sledgehammer_anim.py), script/animcmd/body (specialairlwstart / specialairlwhold in game / effect /
sound / expression), effect/supamario (the skill's Hmr_Crg / Hmr_Crg02 / Hmr_Fire / Hmr_Fire_L and BTL_CMN effect 0's
Btl_HitLOD / Btl_HitS / Btl_Sweat00, with their fake-glow halos), sound (SH_SE in his bank, the soundlabeltable's row
3249 grown), script/msc (supamario.c's sh_*), OUT_DIR/sledgehammer_frames.json, sledgehammer_fx.json, preview/.

The move: fighters/supamario/README.md "Sledgehammer".
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import supamario_sledgehammer_anim as anim  # noqa: E402

# ---------------------------------------------------------------- XV2's timeline (BAC frames; reference/xv2/sledgehammer_skill.json)
# entry 0 (uncharged, BCM #1 BacEntryPrimary) / 2 (charged, BacEntryCharge) / 3 (on hit: BCM #2, OnAttackHit, played
# from the hit on the same clock: its items are entry 0's minus the hitboxes / effects, its TimeScales 0-12 x0.5 and
# 32-44 x0.5 only, its BcmCallback "Combos" 26-44 the on-hit cancel window)
BAC_CHARGE = 6                      # ChargeControl 6-8, ChargeTime 30
CHARGE_FRAMES = 30                  # held this long at the charge pose: charged (entry 2)
CHARGE_FRAMES = 24                  # v4 (user: "make Sledgehammer's charge time slightly shorter"): XV2's ChargeTime 30
                                    # -> 24, from the pose (start frame 12): the charged swing on game frame 35 (v1-v3 41)
BAC_HIT = (16, 20)                  # entry 0's hitbox (frames 16-19); entry 2's 15-19
BAC_HIT_CH = (15, 19)
BAC_CANCEL_HIT = 26                 # entry 3's BcmCallback (Combos) 26-44: the on-hit cancel window
BAC_IASA = 37                       # entry 0 / 2's BcmCallback Movement / Guard / FlyingAndStepDash 37-44: free
TS_HIT = [(0, 12, 0.5), (12, 32, 1.0), (32, 44, 0.5)]           # entry 3
TS_CHARGED = [(0, 12, 0.5), (12, 22, 1.0), (22, 26, 0.23), (26, 37, 0.5), (37, 44, 1.0)]   # entry 2

# ---------------------------------------------------------------- our frames (motion frames; anim's timing)
START_LAST = anim.START_FRAMES - 1                       # 12: SpecialAirLwStart's last frame = BAC 6, the charge pose
HF = anim.hold_frame                                     # SpecialAirLwHold's frame of a BAC frame (entry 0's timing)
HIT_FROM, HIT_TO = int(HF(BAC_HIT[0])), int(HF(BAC_HIT[1]))          # 16, 20: active 16-19
HIT_FROM_CH, HIT_TO_CH = int(HF(BAC_HIT_CH[0])), int(HF(BAC_HIT_CH[1]))   # 15, 19: active 15-18
CANCEL_HIT = HF(BAC_CANCEL_HIT)                          # 35.33: specials (not the down special) once he has hit
IASA = HF(BAC_IASA)                                      # 57.33: anything (whiff or hit)
HOLD_END = anim.HOLD_FRAMES - 1                          # 64: Fall after it (the slot loops: its wrap ends it too)
HIT_LATE = 3.0                                           # the MSC still looks for the hit 3 frames past the hitbox


def rate_segments():
    """[(from frame, to frame, uncharged hit rate, charged whiff rate)] of SpecialAirLwHold: each BAC span's speed in
    the entry played over its speed in entry 0 (the baked motion). A hit is entry 3 whether charged or not"""
    out = []
    edges = sorted({b for a, z, _s in anim.TS_ENTRY0 + TS_HIT + TS_CHARGED for b in (a, z) if b >= BAC_CHARGE})
    for a, z in zip(edges, edges[1:]):
        s0 = next(s for x, y, s in anim.TS_ENTRY0 if x <= a < y)
        sh = next(s for x, y, s in TS_HIT if x <= a < y)
        sc = next(s for x, y, s in TS_CHARGED if x <= a < y)
        out.append((HF(a), HF(z), sh / s0, sc / s0))
    return out


# ---------------------------------------------------------------- the hit (the user's spec; XV2's ratios)
# XV2: one hitbox each, b_C_Base + (0, 0, 0.75 m ahead), 1.0 m; entry 0 60 damage (skill BDM #0: stun 10 / 10, a
# knock down-forward (0, -0.35, 0.05) for 70 frames), entry 2 145 (BDM #1: stun 30 / 30, (0, -1.5, 0.05) for 100,
# camera shake 60); both BDMs' hit effect BTL_CMN 0, sounds CMN Hit_L (52) / Hit_LL (53). A second hitbox on the same
# frames (CMN.bdm #0, 0 damage, flags 0x8) is left out (no damage, XV2's own bookkeeping)
HIT_Z, HIT_Y = round(0.75 * anim.SCALE, 2), 0.0                  # XV2's 0.75 m ahead (3.78), at his feet
HIT_SIZE_V1 = round(1.0 * anim.SCALE, 2)                          # v1: XV2's 1.0 m (5.04)
SIZE_V2 = 1.2                       # v2 (user: "increase the size of the effects and the hitbox slightly")
HIT_SIZE = round(HIT_SIZE_V1 * SIZE_V2, 2)   # 6.05; its centre stays (the fists, 1.5 ahead, are 2.3 from it)
# uncharged: "a weak, low knockback spiking hit that barely has any knockback growth and slightly above average
# hitstun": 5% (XV2 60 : 145 = the charged one's 12 x 0.41), 270 (straight down), BKB 40, KBG 10 (knockback 42 at 0%,
# 47 at 100%: Mario weight; 16-18 frames of hitstun from it) + HITSTUN_ADD (22-24), XV2's 10 frames of hitstop
HIT_V1 = dict(Damage=5.0, Angle=270, KBG=10, FKB=0, BKB=40)
# v2 (user: "slightly more base knockback and slightly more growth, it barely sends the opponent down at all", and 8%):
# 8%, BKB 50, KBG 20: knockback 54.7 / 61.7 / 68.7 at 0 / 50 / 100% (v1 42.0 / 44.5 / 46.9), hitstun 27-33 with +6
HIT = dict(Damage=8.0, Angle=270, KBG=20, FKB=0, BKB=50)
HITSTUN_ADD = 6
HITSTOP = 10                         # XV2 BDM #0 UserStun / VictimStun 10
# charged: "a strong spike with increased damage that has good knockback growth": 12% (XV2 145 / 60 = 2.4x), 270,
# BKB 25, KBG 95 (53 at 0%, 146 at 100%), the game's hitstun; 20 frames of hitstop (XV2 30: past Smash's 30 cap feel)
HIT_CH_V1 = dict(Damage=12.0, Angle=270, KBG=95, FKB=0, BKB=25)
# v2 (user: 20%, the launch about v1's): BKB 23, KBG 61: knockback 52.8 / 99.7 / 146.7 at 0 / 50 / 100% (v1 53.3 /
# 99.8 / 146.4; within 1 from 0 to 150%)
HIT_CH = dict(Damage=20.0, Angle=270, KBG=61, FKB=0, BKB=23)
HITSTOP_CH = 20
# v3 (user: the charged hit on a grounded opponent "bounces just like the uncharged hit rather than forcing the opponent
# down into the laying-down hurt state"): the charged swing is two hitboxes on the same frames and place, one hit a
# target (Part 0): ID 0 the spike above, aerial only (Ground/Air 2); ID 1 grounded only (Ground/Air 1), the same 20%
# and hitlag but knockback 1 (BKB 1, KBG 0, angle 0: Fake Death's grounded hit, fine in game since its v1), so a
# fighter on the ground is never launched (v2's 99.7 / 146.7 at 50 / 100% bounced it off the floor as Smash's ground
# spike does: DamageFly, which ended v2's hold) and the MSC puts it straight down (sh_down_start)
HIT_CH_GROUND = dict(Damage=20.0, Angle=0, KBG=0, FKB=0, BKB=1)
# v2 (user): shield damage by the charge (fractions of the common max shield health) and held shieldstun (Core
# Breaker's cb_shield_tick): charged 80% / 30 frames; uncharged 24% / 8 (Smash's own for an 8% hit: INT(8 x 0.58 + 4))
SHIELD_TAKE, SHIELD_STUN = 0.24, 8
SHIELD_TAKE_CH, SHIELD_STUN_CH = 0.80, 30
DOWN_HOLD = 40                       # v2 (user): a charged hit on the ground: lying 40 frames, untechable (v4: counted
                                     # from the first frame it lies after the bounce)
DOWN_HOLD = 28                       # v5 (user: "28 frames instead of 40"): still from the first frame it lies after the
                                     # bounce. Sledgehammer's own: the Super God Fist's knockdown is GF_DOWN_FRAMES
# v5 (user: no bounce / hold on invincible, intangible, shielding, countering or armored opponents; then: "Charged
# Sledgehammer should bypass armor though"): ST_DAMAGE_LO-HI / ST_DOWNDAMAGE are the reactions that count (a hit that
# took effect); ST_GUARD_LO-HI and the break are shields; ST_DEAD / ST_REBIRTH / ST_ENTRY-ST_LOSE (KO, respawn, entry,
# results) let a held victim go. The charged swing lifts the armor (ARMOR = 0) of every fighter its hitbox overlaps on
# its active frames, before the collision (sh_unarmor), and gives it back to those it didn't hit (sh_rearmor)
ST_DAMAGE_LO, ST_DAMAGE_HI = 0x45, 0x4C
ST_GUARD_LO, ST_GUARD_HI = 0x1B, 0x1E
ST_DEAD, ST_REBIRTH, ST_ENTRY, ST_LOSE = 0xB1, 0xB2, 0x14F, 0x151
BODY_W, BODY_H = 3.5, 10.0          # a fighter's body for sh_unarmor's overlap (the test model's: feet to +10, 3.5 wide)
BOUNCE_MAX = 30                      # v4: the charged hit's bounce: put down if it is still bouncing after this
TURN_STICK = 0.5                     # v4: the B-reverse (Core Breaker's TURN_STICK / TURN_WINDOW): the stick back
TURN_WINDOW = 4                      # past this along his facing on the move's first 4 frames
ST_DOWNBOUND, ST_DOWNWAIT, ST_SHIELD_BREAK = 0x4D, 0x50, 0x59
# v3: the down statuses (DownBound 0x4D .. 0x53: lying), DownStand (0x54, the neutral getup: an uncharged hit on it
# isn't a bounce: the user's jab-lock loop), DownDamage (0x57: hit while lying)
ST_DOWN_LO, ST_DOWN_HI, ST_DOWNSTAND, ST_DOWNDAMAGE = 0x4D, 0x53, 0x54, 0x57
LAND_LAG = 10                        # v2 (user: "standardize Sledgehammer's landing lag to 10 frames"), his light
                                     # landing's animation over them (v1: 18, 10 after a hit, LandingFallSpecial's pose)
VICTIM_MID = 5.0                     # a fighter's middle above its feet (the contact point)
VICTIM_HEAD = 9.0                    # its head (the sweat)
VICTIM_R2 = (HIT_SIZE + 12.0) ** 2   # the fallback victim search: within this of the hitbox centre

# ---------------------------------------------------------------- variables (New_Var slots 0x2F / 0x3E / 0x3F, VAR_0 / 1)
V_SH = 0x0F000380 + 0x3E             # sh: 0 off, 1 the wind-up, 2 charging, 3 the swing
V_CHG = 0x0F000380 + 0x3F            # sh_chg: frames charged; >= CHARGE_FRAMES charged (the game / effect scripts read it)
V_VIC = 0x0F000380 + 0x2F            # sh_vic: the hit fighter's player slot (+), -1 a hit, no follow / its follow over
V_VY = 0x0F000300                    # VAR_0: the followed fighter's Y last frame (MSC only; VAR_n unused by him)
V_LASTFR = 0x0F000301                # VAR_1: the swing's motion frame last frame (the slot loops: the end is the wrap)
V_SHD = 0x0F000303                   # VAR_3 (v2): his shield hit handled this move
V_GS = 0x0F000304                    # VAR_4 (v2): a grounded victim's slot (+ uncharged bounce, - charged held down)
V_GN = 0x0F000305                    # VAR_5 (v2): 0 its hitstop not over yet, then the frames held down
V_T = 0x0F000302                     # VAR_2 (v2): the move's frames (sh_fastfall: a flick younger than the move)
V_ST = 0x0F000306                    # VAR_6-13 (v3): each slot's status the last frame it wasn't frozen (sh_rec)
V_GX = 0x0F00030E                    # VAR_14 (v3): the held-down victim's X at the hit
V_GY = 0x0F00030F                    # VAR_15 (v3): its Y at the hit (the floor it stood on); v4: where it lies
V_BREV = 0x0F000310                  # VAR_16 (v4): the B-reverse done this move
V_GP = 0x0F000311                    # VAR_17 (v4): the charged grounded victim's phase (0 hitstop, 1 bounce, 2 lying)
V_ARM = 0x0F000312                   # VAR_18-21 (v5): armor the charged swing lifted (slot x 1e6 + type x 1e5 + thr x 10)
ARM_N = 4
VARS = [('sh', V_SH), ('sh_chg', V_CHG), ('sh_vic', V_VIC)]

# ---------------------------------------------------------------- effects / sounds
SH_FX_SCALE_V1 = 1.75                # xv2_smash_fx.SIZE: the God Fist's settled size over XV2's (Core Breaker 2.25)
SH_FX_SCALE = round(SH_FX_SCALE_V1 * SIZE_V2, 3)   # v2: 2.1
ARC_WIDTH = 3.0                      # v2 (user: "the release arc is drawn flat ... instead of a thick yellow trail"):
                                     # Hmr_Fire's arcs' strip x3 (XV2: 0.15 m over a 1.15 m radius, 13%; glared)
# v3 (user: "Sledgehammer's glow is extremely bright", screenshot 25: a white-yellow dome over him at the swing): the
# swing arcs. v1 drew them flat (edge-on to the camera: a thin streak); v2 stood them in his YZ plane facing the camera,
# their strip x3, the effects x1.2 and following him (the 3 arcs each emitter lays over 3 frames stay on him and stack),
# all still at the HDR gain (x2, capped at 2.0) meant for small glowing points. fx_render's Smash 4 side (black
# background, his body left out): v2's charged swing 144 square units over 1.0 (bloom), 296 over 0.5, energy 738; the
# God Fist's brightest frame 2 over 1.0 (6.4 at most), 33 over 0.5, energy 95; Core Breaker's charge aura 0.1 over 1.0
# at its brightest (one burst frame 62), energy 690; Sledgehammer's charge glow (2.6 / 12) and hit burst (3.1 / 87) are
# within the God Fist's (tools/supamario_fx_glow.py). So the
# arcs' colour keys x ARC_GAIN: each arc's drawn colour 2.0 -> 0.9 (XV2's yellow kept); where two arcs overlap they
# reach 0.85, under Smash 4's bloom: charged 0 over 1.0 from the arcs (4.4 is the fist's flash), energy 345;
# uncharged 0 over 1.0, energy 180 (v2 73 / 399)
# v4 (user, screenshot 26: "the arc is still too bright", a yellow-white glow round him on a grass stage): x0.45 kept
# them under 1.0 on black, but they add onto the stage. tools/supamario_fx_glow.py --bg 0.5,0.65,0.3 (a grass stage),
# v3: the arcs push 107 (uncharged) / 193 (charged) square units past 1.0, everything else 8 (the fist's flash 6.5,
# the sparks 1.6). Now per channel (R, G, B) x0.2 / x0.14 / x0.2 (B is 0): the overlap adds at most ~0.38 red, 0.27
# green, under 1.0 on that grass (its green 0.65), and the hue goes from XV2's yellow (1.4, 1.4, 0) to a yellow-orange
# (1.4, 0.98, 0) that reads as fire on green or grey instead of turning lime / white
ARC_GAIN = (0.2, 0.14, 0.2)
# v5 (user, screenshot 27: "make the Sledgehammer's arcs slightly brighter", v4's a faint yellow streak): +35%, the hue
# kept (R : G 1 : 0.7)
ARC_GAIN = (0.27, 0.19, 0.27)
# v4: the charged fist flash (Hmr_Crg02, at the arcs' frame): its white core drawn at 2.0 (alpha blend: it replaces
# the stage with 2.0, the bloom's white); its colour capped at FLASH_PEAK (its halo copy follows: halved too)
FLASH_PEAK = 1.0
# v5 (user: "draw the charge glow closer to the camera, so it shows in front of his head rather than inside it"): the
# charge glow (Hmr_Crg) and the charged fist flash (Hmr_Crg02) on LHandN with External_Graphic's last word 0 (the
# request's flag, docs/native-notes.md "EffectModule requests": 1 the bone's full matrix, 0 its position only, X x the
# facing, Z = world depth) and Z = GLOW_DEPTH toward the camera: the hand's place, a world-space depth whichever way he
# faces. GLOW_DEPTH: his head's half-depth beside the left hand at the charge pose (the head's mesh points, start frame
# 12) + GLOW_MARGIN (build(): sledgehammer_frames.json 'glow_depth')
GLOW_MARGIN = 1.0
GLOW_DEPTH = None                    # set by build() from the model
FOLLOW_EMPS = ('Hmr_Crg.emp', 'Hmr_Crg02.emp', 'Hmr_Fire.emp', 'Hmr_Fire_L.emp')   # v2: particles follow him
LHAND = 0x10                         # LHandN (XV2's b_L_Hand: Hmr_Crg / Hmr_Crg02)
SKILL_EMPS = ['Hmr_Crg.emp', 'Hmr_Crg02.emp', 'Hmr_Fire.emp', 'Hmr_Fire_L.emp']
HIT_EMPS = ['Btl_HitLOD.emp', 'Btl_HitS.emp', 'Btl_Sweat00.emp']          # BTL_CMN effect 0 (its CBIND left out)
# their EEPK scales: skill effect 0 Crg 1.0; 1 Fire 1.0; 3 Fire_L 1.2 + Crg02 1.2; BTL_CMN 0: HitLOD 1.5, HitS 0.8,
# Sweat00 1.0 (on the victim's head)
EEPK_SCALE = {'Hmr_Crg.emp': 1.0, 'Hmr_Fire.emp': 1.0, 'Hmr_Fire_L.emp': 1.2, 'Hmr_Crg02.emp': 1.2,
              'Btl_HitLOD.emp': 1.5, 'Btl_HitS.emp': 0.8, 'Btl_Sweat00.emp': 1.0}
FX_AT = {'crg_on': anim.START_FRAMES - 3,                # BAC 5 (real 10): Hmr_Crg on the left fist
         'crg_off': int(HF(8)),                          # BAC 8 (swing 4): off (uncharged)
         'crg_off_ch': int(HF(13)),                      # BAC 13 (swing 13): off (charged, entry 2)
         'fire': int(HF(12))}                            # BAC 12 (swing 12): Hmr_Fire (1) / Hmr_Fire_L + Crg02 (3)
FX_IDS = {'crg': 0x03410058, 'crg02': 0x03410059, 'fire': 0x0341005A, 'fire_l': 0x0341005B,
          'hitlod': 0x0341005C, 'hits': 0x0341005D, 'sweat': 0x0341005E}
EMP_KEY = {'Hmr_Crg.emp': 'crg', 'Hmr_Crg02.emp': 'crg02', 'Hmr_Fire.emp': 'fire', 'Hmr_Fire_L.emp': 'fire_l',
           'Btl_HitLOD.emp': 'hitlod', 'Btl_HitS.emp': 'hits', 'Btl_Sweat00.emp': 'sweat'}
SH_SE = {'sh_charge': ('BRD_S164_HMR_Charge', 0.0),     # skill SE cue 0, BAC 6 (the MSC at the charge pose)
         'sh_furi': ('BRD_S164_HMR_Furi', 0.0),         # skill SE cue 1, BAC 9 (swing 6)
         'sh_swing': ('swing_42', 0.0)}                  # CMN SE cue 42, BAC 1 (start 2)
SE_IDS = {'sh_charge': 0x0CB1009A, 'sh_furi': 0x0CB1009B, 'sh_swing': 0x0CB1009C}
SND_HIT = 0x0CB10097                 # Core Breaker's cb_hit_l: CMN Hit_L (BDM #0's cue 52)
SND_HIT_CH = 0x0CB1008F              # the God Fist's gf_hit_ll: CMN Hit_LL (BDM #1's cue 53)
SND_AT = {'swing': 2, 'furi': int(HF(9))}


def fl(v):
    return '%sf' % repr(float(v))


def rate_code():
    """sh_rate's body: `if (fr < b) { return hit ? x : (ch ? y : 1); }` per span"""
    out = []
    for a, z, rh, rc in rate_segments():
        if abs(rh - 1.0) < 1e-6 and abs(rc - 1.0) < 1e-6:
            continue
        out.append('if (fr > %s && fr < %s) { if (hit != 0) { return %s; } if (ch != 0) { return %s; } return 1.0f; }'
                   % (fl(a - 0.001), fl(z - 0.001), fl(round(rh, 5)), fl(round(rc, 5))))
    return ' '.join(out)


def msc_values():
    """the SH_* names in fighters/supamario/supamario.c"""
    return {'SH_V': '0x%X' % V_SH, 'SH_V_CHG': '0x%X' % V_CHG, 'SH_V_VIC': '0x%X' % V_VIC, 'SH_V_VY': '0x%X' % V_VY,
            'SH_V_LASTFR': '0x%X' % V_LASTFR, 'SH_V_T': '0x%X' % V_T, 'SH_START_LAST': fl(START_LAST), 'SH_CHARGE': fl(CHARGE_FRAMES),
            'SH_HIT_FROM': fl(HIT_FROM_CH), 'SH_HIT_TO': fl(HIT_TO + HIT_LATE), 'SH_CANCEL_HIT': fl(CANCEL_HIT),
            'SH_IASA': fl(IASA), 'SH_HOLD_END': fl(HOLD_END), 'SH_RATE_CODE': rate_code(),
            'SH_HIT_Z': fl(HIT_Z), 'SH_HIT_Y': fl(HIT_Y), 'SH_VICTIM_MID': fl(VICTIM_MID),
            'SH_VICTIM_HEAD': fl(VICTIM_HEAD), 'SH_VICTIM_R2': fl(VICTIM_R2), 'SH_LAND_LAG': fl(LAND_LAG), 'SH_V_SHD': '0x%X' % V_SHD,
            'SH_V_GS': '0x%X' % V_GS, 'SH_V_GN': '0x%X' % V_GN, 'SH_DMG': fl(HIT['Damage']), 'SH_DMG_CH': fl(HIT_CH['Damage']),
            'SH_SHIELD_TAKE': fl(SHIELD_TAKE), 'SH_SHIELD_STUN': fl(SHIELD_STUN), 'SH_SHIELD_TAKE_CH': fl(SHIELD_TAKE_CH),
            'SH_SHIELD_STUN_CH': fl(SHIELD_STUN_CH), 'SH_DOWN_HOLD': fl(DOWN_HOLD), 'SH_ST_DOWNBOUND': fl(ST_DOWNBOUND),
            'SH_ST_DOWNWAIT': fl(ST_DOWNWAIT), 'SH_ST_SHIELD_BREAK': fl(ST_SHIELD_BREAK),
            'SH_V_ST': '0x%X' % V_ST, 'SH_V_GX': '0x%X' % V_GX, 'SH_V_GY': '0x%X' % V_GY,
            'SH_ST_DOWN_LO': fl(ST_DOWN_LO), 'SH_ST_DOWN_HI': fl(ST_DOWN_HI), 'SH_ST_DOWNSTAND': fl(ST_DOWNSTAND),
            'SH_ST_DOWNDAMAGE': fl(ST_DOWNDAMAGE), 'SH_V_BREV': '0x%X' % V_BREV, 'SH_V_GP': '0x%X' % V_GP,
            'SH_BOUNCE_MAX': fl(BOUNCE_MAX), 'SH_TURN_STICK': fl(TURN_STICK), 'SH_TURN_WINDOW': fl(TURN_WINDOW),
            'SH_FX_CRG': '0x%X' % FX_IDS['crg'],
            # v5: the reactions, shields and ends that count; the charged swing's armor lift (VAR_18-21: up to 4
            # fighters' armor, slot x 1e6 + type x 1e5 + threshold x 10)
            'SH_ST_DAMAGE_LO': fl(ST_DAMAGE_LO), 'SH_ST_DAMAGE_HI': fl(ST_DAMAGE_HI), 'SH_ST_GUARD_LO': fl(ST_GUARD_LO),
            'SH_ST_GUARD_HI': fl(ST_GUARD_HI), 'SH_ST_DEAD': fl(ST_DEAD), 'SH_ST_REBIRTH': fl(ST_REBIRTH),
            'SH_ST_ENTRY': fl(ST_ENTRY), 'SH_ST_LOSE': fl(ST_LOSE), 'SH_V_ARM': '0x%X' % V_ARM,
            'SH_ARM_N': str(ARM_N), 'SH_BODY_W': fl(BODY_W), 'SH_BODY_H': fl(BODY_H), 'SH_HIT_SIZE': fl(HIT_SIZE),
            'SH_HIT_FROM_CH': fl(HIT_FROM_CH), 'SH_HIT_TO_CH': fl(HIT_TO_CH),
            'SH_FX_HITLOD': '0x%X' % FX_IDS['hitlod'], 'SH_FX_HITS': '0x%X' % FX_IDS['hits'],
            'SH_FX_SWEAT': '0x%X' % FX_IDS['sweat'],
            'SH_FX_HITLOD_SIZE': fl(EEPK_SCALE['Btl_HitLOD.emp'] * SH_FX_SCALE),
            'SH_FX_HITS_SIZE': fl(EEPK_SCALE['Btl_HitS.emp'] * SH_FX_SCALE),
            'SH_FX_SWEAT_SIZE': fl(EEPK_SCALE['Btl_Sweat00.emp'] * SH_FX_SCALE),
            'SH_SND_CHARGE': '0x%X' % SE_IDS['sh_charge'], 'SH_SND_HIT': '0x%X' % SND_HIT,
            'SH_SND_HIT_CH': '0x%X' % SND_HIT_CH}


# ---------------------------------------------------------------- knockback (Smash 4's), as Fake Death's
def knockback(hit, pct_before, weight=100.0):
    import supamario_fakedeath_build as FD
    return FD.knockback(hit, pct_before, weight)


def hitstun(hit, pct_before, add=0):
    return int(knockback(hit, pct_before) * 0.4) + add


# ---------------------------------------------------------------- ACMD
def cmd(name, *params):
    return acmd.Command(acmd.BY_NAME[name.lower()], list(params))


def size(cmds):
    return sum(acmd.INFO[c.ident]['size'] for c in cmds)


def if_(var, method, value, body, else_body=None):
    """Float_Var_Compare(var, method, value) True{ body } [Else{ else_body }]"""
    out = [cmd('float_var_compare', var, method, float(value)), cmd('true', 2 + size(body)
                                                                    + (2 if else_body else 0))] + body
    if else_body:
        out += [cmd('else', 2 + size(else_body))] + else_body
    return out


def hitbox(**kw):
    d = dict(ID=0, Part=0, Bone=0, Damage=1.0, Angle=0, KBG=0, FKB=0, BKB=0, Size=1.0, X=0.0, Y=0.0, Z=0.0,
             Effect=0, Trip=0.0, Hitlag=1.0, SDI=1.0, Clang=1, Rebound=0, ShieldDamage=0, SFXLevel=1, SFXType=1,
             **{'Ground/Air': 3, 'Direct/Indirect': 1}, Type=1, HitBits=0x3F, Unk41=0, CollisionPart=0xF, NoScale=0,
             Shieldable=1, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0, HitAllStates=0, FacingRestrict=3,
             NoGrabRelease=0, TeamDamage=0, DisableHitlag=0, NoGFX=1, Flinchless=0, Shape=0, HitstunMul=0.0,
             HitstopMul=0.0, HitstopFrames=0, SelfHitstopMul=0.0, SelfHitstopFrames=0, DIMul=0.0)
    d.update(kw)
    ident = acmd.BY_NAME['extra_special_hitbox']
    return acmd.Command(ident, [d[n] for n in acmd.INFO[ident]['syntax']])


def hit_uncharged():
    """ID 0: the weak spike. NoGFX 1: XV2's own hit effect (BTL_CMN 0) comes from the MSC at the contact point. v4:
    Clang 0 (it meets no other hitbox; hit_clank does the clanking) and the clank box"""
    return [hitbox(ID=0, Size=HIT_SIZE, Y=HIT_Y, Z=HIT_Z, HitstunMul=-float(HITSTUN_ADD), HitstopFrames=HITSTOP,
                   SelfHitstopFrames=HITSTOP, SFXLevel=1, Clang=0, **HIT), hit_clank()]


# v4 (user: "make it so Sledgehammer wins any clanks"). Smash 4's clank (exe_v46u, docs/native-notes.md "Clanks"): the
# attack-vs-attack pass (0x02C0F6F0) records each pair of overlapping hitboxes whose collision masks take each other
# (a hitbox's mask, 0x02C0E77C: HitBits | Clang << 6 | ...: Clang 0 meets no hitbox); each side then resolves its own
# record (0x02C0A708): it wins when its damage - battle_object param 55 (9.0, at [0x102FDC70] + 0xDC) >= the other's
# (x the other's attack multipliers): its record is dropped and it goes on untouched; else it loses: Rebound 1 rebounds
# (the duration and pushback from the larger of the two damages), Rebound 0 has its attack cancelled (+0x120). One
# losing record is enough to lose. So the real hitboxes are Clang 0 (they never meet another hitbox, never lose one)
# and ID 2 is a clank-only box on the same place, size and frames: Clang 1, CLANK_DMG damage, HitBits 0 (no fighter,
# item, enemy or floor category: it hits nobody), Shieldable / Reflectable / Absorbable 0, no knockback, NoGFX, Rebound
# 0: it beats any hitbox doing up to CLANK_DMG - 9 = 41% (after its owner's multipliers). The loser's clank hitlag is
# from the larger damage x the larger one's Hitlag multiplier: CLANK_HITLAG keeps it near a 15% clank's
CLANK_DMG = 50.0
CLANK_HITLAG = 0.3


def hit_clank():
    return hitbox(ID=2, Size=HIT_SIZE, Y=HIT_Y, Z=HIT_Z, Damage=CLANK_DMG, Angle=0, KBG=0, FKB=0, BKB=0,
                  Hitlag=CLANK_HITLAG, SDI=0.0, Clang=1, Rebound=0, HitBits=0, Shieldable=0, Reflectable=0,
                  Absorbable=0, NoGFX=1, SFXLevel=0, SFXType=0, Flinchless=1)


def hit_charged():
    """v3: ID 0 the spike (aerial targets), ID 1 grounded targets: knockback 1, put down by the MSC"""
    return [hitbox(ID=0, Size=HIT_SIZE, Y=HIT_Y, Z=HIT_Z, HitstopFrames=HITSTOP_CH, SelfHitstopFrames=HITSTOP_CH,
                   SFXLevel=2, Clang=0, **{'Ground/Air': 2}, **HIT_CH),
            hitbox(ID=1, Size=HIT_SIZE, Y=HIT_Y, Z=HIT_Z, HitstopFrames=HITSTOP_CH, SelfHitstopFrames=HITSTOP_CH,
                   SFXLevel=2, SDI=0.0, Clang=0, **{'Ground/Air': 1}, **HIT_CH_GROUND),
            hit_clank()]


CH, NCH = 3, 4                        # Float_Var_Compare methods: >= / <


def new_vars():
    return [acmd.new_var(n, v - 0x0F000380, 0, 0.0, 0) for n, v in VARS]


def game_scripts():
    """the start: nothing timed (the MSC holds the charge); the swing: the charged hitbox at 15-18, the uncharged one at
    16-19 (sh_chg read when it comes out)"""
    start = new_vars()
    hold = new_vars() + [
        cmd('frame', float(HIT_FROM_CH))] + if_(V_CHG, CH, CHARGE_FRAMES, hit_charged()) + [
        cmd('frame', float(HIT_FROM))] + if_(V_CHG, NCH, CHARGE_FRAMES, hit_uncharged()) + [
        cmd('frame', float(HIT_TO_CH))] + if_(V_CHG, CH, CHARGE_FRAMES, [cmd('remove_all_hitboxes')]) + [
        cmd('frame', float(HIT_TO)), cmd('remove_all_hitboxes')]
    return start, hold


def gfx(name, graphic, bone, x, y, z, size_=1.0, rot=(0.0, 0.0, 0.0), terminate=1):
    if name == 'external_graphic':
        return cmd(name, graphic, bone, x, y, z, rot[0], rot[1], rot[2], size_, terminate)
    return cmd(name, graphic, bone, x, y, z, rot[0], rot[1], rot[2], size_, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, terminate)


def effect_scripts(fire_y):
    """XV2's skill effects at their frames: the charge glow on the left fist from BAC 5 (on through the charge), off at
    BAC 8 (uncharged) / 13 (charged); at BAC 12 the falling fire rings round his waist (Hmr_Fire; charged: Hmr_Fire_L
    x1.2 and the fist's flash Hmr_Crg02 x1.2). The rings on bone 0 at his hips' height (up only: facing-safe), the
    fist's effects on LHandN (no offset, no turn)"""
    ids = FX_IDS
    sc = SH_FX_SCALE
    dz = float(GLOW_DEPTH or 0.0)                       # v5: world depth toward the camera, the request's flag 0
    start = [cmd('frame', float(FX_AT['crg_on'])),
             gfx('external_graphic', ids['crg'], LHAND, 0.0, 0.0, dz, EEPK_SCALE['Hmr_Crg.emp'] * sc, terminate=0)]
    hold = new_vars() + [
        cmd('frame', float(FX_AT['crg_off']))] + if_(V_CHG, NCH, CHARGE_FRAMES, [
            cmd('terminate_graphic_effect', ids['crg'], 1, 0)]) + [
        cmd('frame', float(FX_AT['fire']))] + if_(V_CHG, CH, CHARGE_FRAMES, [
            gfx('external_graphic', ids['fire_l'], 0, 0.0, float(fire_y), 0.0, EEPK_SCALE['Hmr_Fire_L.emp'] * sc),
            gfx('external_graphic', ids['crg02'], LHAND, 0.0, 0.0, dz, EEPK_SCALE['Hmr_Crg02.emp'] * sc,
                terminate=0)], [
            gfx('external_graphic', ids['fire'], 0, 0.0, float(fire_y), 0.0, EEPK_SCALE['Hmr_Fire.emp'] * sc)]) + [
        cmd('frame', float(FX_AT['crg_off_ch']))] + if_(V_CHG, CH, CHARGE_FRAMES, [
            cmd('terminate_graphic_effect', ids['crg'], 1, 0)])
    return start, hold


def sound_scripts():
    """XV2's: CMN swing_42 at BAC 1, the skill's Furi at BAC 9 (the Charge at BAC 6: the MSC, at the charge pose). No
    voice (the user's rule)"""
    return ([cmd('frame', float(SND_AT['swing'])), cmd('sound_effect', SE_IDS['sh_swing'])],
            [cmd('frame', float(SND_AT['furi'])), cmd('sound_effect', SE_IDS['sh_furi'])])


def expression_scripts():
    return [], [cmd('frame', float(HIT_FROM_CH))] + if_(V_CHG, CH, CHARGE_FRAMES, [cmd('rumble', 0x12, 0)]) + [
        cmd('frame', float(HIT_FROM))] + if_(V_CHG, NCH, CHARGE_FRAMES, [cmd('rumble', 0x10, 0)])


SCRIPT_NAMES = ('specialairlwstart', 'specialairlwhold')


def scripts(body_dir, fire_y):
    makers = {'game': game_scripts(), 'effect': effect_scripts(fire_y), 'sound': sound_scripts(),
              'expression': expression_scripts()}
    for part, (start, hold) in makers.items():
        path = os.path.join(body_dir, part + '.bin')
        f = acmd.ACMDFile.load(path)
        for name, body in zip(SCRIPT_NAMES, (start, hold)):
            # the air F.L.U.D.D.'s scripts replaced (its start / hold: sounds, effects, rumble; no hitboxes)
            f.scripts[acmd.crc(name)] = body + [acmd.Command(acmd.END)]
        f.save(path)


# ---------------------------------------------------------------- effects (the skill's, BTL_CMN effect 0)
def _cmn_pkg(cmn_dir, tmp):
    for fn in os.listdir(cmn_dir):                  # BTL_CMN.eepk alone (vfx/cmn holds five), as the God Fist's
        if not fn.lower().endswith('.eepk') or fn == 'BTL_CMN.eepk':
            os.symlink(os.path.abspath(os.path.join(cmn_dir, fn)), os.path.join(tmp, fn))
    return tmp


ARC_EMPS = ('Hmr_Fire.emp', 'Hmr_Fire_L.emp')


def arc_turn():
    """v2: the emitter turn putting a polygon (eft type 1: drawn in its emitter's XY plane) in bone 0's YZ plane, its
    X along his facing (bone 0 +Z) and its Y up: facing the side camera (bone 0's X is the screen's depth). XV2's
    Hmr_Fire arcs are open ShapeDraw outlines (~110-130 degrees, 40 down to -70 / -90 round their X) spinning 15
    degrees a frame: the swing's trail, sweeping round in front of him. v1 laid them flat (X 90): seen edge-on from
    the side camera they were the user's "thin, flat yellow streak along his body" (screenshot 24)"""
    import numpy as np
    import xv2_to_ptcl as XP
    m = np.array([[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]])
    e = XP.matrix_euler(m)
    assert np.allclose(XP.euler_matrix([math.degrees(v) for v in e]), m, atol=1e-6)
    return e


def flat_ring(p, d, arc=True):
    """arc (Hmr_Fire / Hmr_Fire_L's ShapeDraw arcs): the polygon turned by arc_turn() (v1: X 90, flat); everything else
    (and every emitter of the hit effects, which the MSC puts at a world position unturned: their polygons in the
    world's XY plane, facing the camera as XV2's Camera-oriented hit effect): the God Fist's facing_safe (unturned,
    a full-sphere spread). A spinning arc in the screen's plane reads the same both facings but for its sweep's way"""
    import xv2_smash_fx as FX
    FX.facing_safe(p, d)
    if arc and p.field(d, 'particle_type') == 1:
        p.set_emitter_srt(d, tuple(p.field(d, 'emitter_scale')), arc_turn(), (0.0, 0.0, 0.0))
        # its spin the swing's way (forward and down; XV2's +15 a frame turned it up and back in this plane: the viewer)
        p.set_field(d, 'rotation_velocity', [-v for v in p.field(d, 'rotation_velocity')])


def arc_dim(p, d, gain=None):
    """v3: a swing arc's colour keys (both tracks) x ARC_GAIN (v4: per channel; the glow: ARC_GAIN's note)"""
    g = gain or ARC_GAIN
    for track in (0, 1):
        p.set_color_keys(d, track, [(k[0] * g[0], k[1] * g[1], k[2] * g[2], k[3]) for k in p.color_keys(d, track)])


def flash_cap(p, d):
    """v4: an emitter's colour keys scaled so its brightest drawn channel is at most FLASH_PEAK"""
    pk = arc_peak(p, d)
    if pk > FLASH_PEAK:
        f = FLASH_PEAK / pk
        arc_dim(p, d, (f, f, f))


def arc_peak(p, d):
    """the brightest channel an emitter's colour 0 keys draw (x its colour scale)"""
    return max(max(k[:3]) for k in p.color_keys(d, 0)) * p.field(d, 'color_scale')


def follow(p, d):
    """v2 (user: "the charge effects don't follow Supamario"): the emitter's particles on its live matrix (ptcl +0x310
    follow type 0; v1's templates gave the charge glow 1, none: emitted particles stayed where they were born while he
    drifted / fell). XV2's EEPK flags for them: PositionUpdate (+ RotateUpdate / InstantUpdate on the charge)"""
    import struct
    struct.pack_into('>I', d, 0x310, 0)


def convert_fx(skill_dir, cmn_dir, fx_dir, halo=True):
    """the seven sets into his bank (fx_dir: effect/supamario, changed in place), vibrant (xv2_smash_fx.hdr_emitter:
    XV2's glare tint x2, capped at HDR_CAP), facing-safe, with fake-glow halos (HALO_ALPHA) on the glowing emitters;
    FX_IDS checked"""
    import tempfile
    import efc
    import ptcl
    import xv2_smash_fx as FX
    import xv2_to_ptcl
    import xv2vfx
    base = 'supamario.010d0000'
    p = ptcl.Ptcl(open(os.path.join(fx_dir, base + '.ptcl'), 'rb').read())
    e = efc.Efc(open(os.path.join(fx_dir, base + '.efc'), 'rb').read())
    before = len(p.build())
    mats = FX.material_table(xv2vfx.load_package(skill_dir, strict=False))
    made = []
    old = xv2_to_ptcl.TEX_MAX
    try:
        xv2_to_ptcl.TEX_MAX = 128
        xv2_to_ptcl.RING_WIDTH_MUL = ARC_WIDTH          # v2: the swing arcs' strip x3
        m1, log1 = xv2_to_ptcl.convert_package(p, skill_dir, 'PtcSupamarioSh', unit=FX.UNIT, emps=SKILL_EMPS,
                                               strict=False)
        xv2_to_ptcl.RING_WIDTH_MUL = 1.0
        # Btl_HitS / Btl_HitLOD animate a (Parameter 3, Component 1) on their sphere emitters that xv2vfx has no name
        # for: read leniently (only here: the earlier moves' conversions read vfx/cmn as before)
        xv2vfx.LENIENT_TARGETS = True
        with tempfile.TemporaryDirectory() as tmp:
            pkg = _cmn_pkg(cmn_dir, tmp)
            mats.update(FX.material_table(xv2vfx.load_package(pkg, strict=False)))
            xv2_to_ptcl.TEX_MAX = 64
            m2, log2 = xv2_to_ptcl.convert_package(p, pkg, 'PtcSupamarioSh', unit=FX.UNIT, emps=HIT_EMPS, strict=False)
    finally:
        xv2_to_ptcl.TEX_MAX = old
        xv2_to_ptcl.RING_WIDTH_MUL = 1.0
        xv2vfx.LENIENT_TARGETS = False
    made = m1 + m2
    sets, notes, got = {}, [], {}
    for si, name, chunk in made:
        emp = name[len('PtcSupamarioSh'):] + '.emp'
        assert emp in EMP_KEY, ('a split set?', name)
        idx = e.add(si + 1)
        got[EMP_KEY[emp]] = 0x03410000 | idx
        names = [en for _b, en, _n in chunk]
        k = 0
        for em in p.sets[si]['emitters']:
            d = em['data']
            if d is None:
                continue
            en = names[k] if k < len(names) else None
            k += 1
            notes.append('%s %s: %s' % (name, en, FX.hdr_emitter(p, d, mats.get(emp, {}).get(en))))
            flat_ring(p, d, emp in ARC_EMPS)
            if emp in ARC_EMPS and p.field(d, 'particle_type') == 1:
                arc_dim(p, d)
                notes[-1] += '; v4: the arc x%s (drawn peak %.2f)' % (ARC_GAIN, arc_peak(p, d))
            if emp == 'Hmr_Crg02.emp':
                flash_cap(p, d)
                notes[-1] += '; v4: the flash capped at %.2f' % arc_peak(p, d)
        sets[emp] = {'set': name, 'set_index': si, 'efc': idx, 'id': '0x%08X' % (0x03410000 | idx), 'emitters': names}
    assert got == FX_IDS, ('FX_IDS is out of date', {k: hex(v) for k, v in got.items()})
    halos = {}
    if halo:
        glow, dropped = {}, {}
        for emp, s in sets.items():
            si = s['set_index']
            ks = [k for k, em in enumerate(p.sets[si]['emitters']) if em['data'] is not None and
                  p.field(em['data'], 'alpha_init') > 0 and
                  (mats.get(emp, {}).get(p.emitter_name(em['data'])) or (0, 0, {}))[2].get('Glare') and
                  not FX.is_refraction(mats[emp][p.emitter_name(em['data'])][1],
                                       mats[emp][p.emitter_name(em['data'])][0])]
            if emp in ARC_EMPS:     # v2: no halo on the swing arcs (a halo copy of an open arc is a soft full disc:
                ks = [k for k in ks if p.field(p.sets[si]['emitters'][k]['data'], 'particle_type') != 1]   # facing
                # the camera now, a big glowing circle behind him)
            room = 16 - len(p.sets[si]['emitters'])
            if len(ks) > room:              # a set's halos stay in it (no companion set for the MSC / Else calls):
                dropped[emp] = len(ks) - room      # the first glowing emitters get one, as many as fit
                ks = ks[:max(0, room)]
            if ks:
                glow[si] = ks
        comp = FX.add_halos(p, e, glow, FX.HALO_ALPHA, {})
        assert not comp, 'a set needs a companion halo set: its calls / kills would need it too'
        halos = {'glowing': sum(len(v) for v in glow.values()), 'alpha': FX.HALO_ALPHA,
                 'by_set': {p.set_name(si): len(v) for si, v in glow.items()}, 'no_room': dropped}
        # (the halo copies keep their emitters' transform: no arc has one, v2)
    for emp in FOLLOW_EMPS:                             # v2: the charge glow / flash and the arcs (+ halos) follow him
        for em in p.sets[sets[emp]['set_index']]['emitters']:
            if em['data'] is not None:
                follow(p, em['data'])
    out = p.build()
    assert ptcl.Ptcl(out).validate() == []
    open(os.path.join(fx_dir, base + '.ptcl'), 'wb').write(out)
    open(os.path.join(fx_dir, base + '.efc'), 'wb').write(e.build())
    arc_sets = [s['set_index'] for emp, s in sets.items() if emp in ARC_EMPS]
    bad = FX.facing_emitters(p, [s['set_index'] for s in sets.values() if s['set_index'] not in arc_sets])
    # the arcs' own turn is arc_turn() (allowed); their spread is still checked
    bad += [b for b in FX.facing_emitters(p, arc_sets) if 'turned / offset' not in b]
    return {'sets': sets, 'skipped': log1 + log2, 'notes': notes, 'halos': halos, 'ptcl_bytes': [before, len(out)],
            'facing_problems': bad}, p


# ---------------------------------------------------------------- the sound bank
def sound_bank(fdir, out_dir, wav_dir):
    """SH_SE into his bank (Fake Death's build's) and the soundlabeltable: the God Fist's sound_bank, these tones"""
    import supamario_godfist_build as GB
    table = os.path.join(out_dir, 'sound', 'config', 'soundlabeltable.bin')
    old_se, old_ids = dict(GB.CMN_SE), dict(GB.SE_IDS)
    try:
        GB.CMN_SE.clear()
        GB.CMN_SE.update(SH_SE)
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


# ---------------------------------------------------------------- preview
def preview(out_png, outs, bones, fire_y, p, rep):
    """the hit frames with the hitbox, the rings at their call, side view, facing right and left"""
    from PIL import Image, ImageDraw
    import omo
    size_px, span = 300, 44.0
    sc = size_px / span
    rows = [('swing f%d (uncharged hit, BAC 16)' % HIT_FROM, HIT_FROM, True),
            ('swing f%d (charged hit, BAC 15)' % HIT_FROM_CH, HIT_FROM_CH, True),
            ('swing f%d: rings (BAC 12) x%.2f' % (FX_AT['fire'], SH_FX_SCALE), FX_AT['fire'], False)]
    o = outs[('main', anim.HOLD)]
    tiles = []
    for label, f, hb in rows:
        w = omo.world(o, bones, f)
        for face in (1.0, -1.0):
            im = Image.new('RGB', (size_px, size_px + 18), (18, 18, 24))
            d = ImageDraw.Draw(im)
            cy0 = size_px * 0.6

            def pt(z, y):
                return size_px / 2 + face * z * sc, cy0 - y * sc
            d.line([(size_px / 2 - 5, cy0), (size_px / 2 + 5, cy0)], fill=(90, 90, 90))
            for n, par, _h in bones:
                if par < 0 or par >= len(bones) or any(k in n for k in anim.SKIP) or n in ('ThrowN', 'RotN', 'HipN'):
                    continue
                d.line([pt(w[bones[par][0]][2][3], w[bones[par][0]][1][3]), pt(w[n][2][3], w[n][1][3])],
                       fill=(230, 230, 230), width=3)
            if hb:
                cx, cy = pt(HIT_Z, HIT_Y)
                r = HIT_SIZE * sc
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 90, 60), width=2)
            else:
                for key in ('fire', 'fire_l'):
                    si = rep['sets'][{'fire': 'Hmr_Fire.emp', 'fire_l': 'Hmr_Fire_L.emp'}[key]]['set_index']
                    for em in p.sets[si]['emitters']:
                        dd = em['data']
                        if dd is None or p.field(dd, 'particle_type') != 1 or p.field(dd, 'alpha_init') <= 0:
                            continue
                        r = max(p.field(dd, 'scale')) * SH_FX_SCALE * EEPK_SCALE[{'fire': 'Hmr_Fire.emp',
                                                                                  'fire_l': 'Hmr_Fire_L.emp'}[key]]
                        r *= 2.35 / 8.06                    # Fake Death's drawn radius per unit of scale (screenshot)
                        cx, cy = pt(0.0, fire_y)
                        col = (255, 220, 90) if key == 'fire' else (255, 150, 60)
                        d.ellipse([cx - r * sc, cy - 0.17 * r * sc, cx + r * sc, cy + 0.17 * r * sc], outline=col)
            d.text((4, size_px + 2), '%s, facing %s' % (label, 'right' if face > 0 else 'left'), fill=(230, 230, 120))
            tiles.append(im)
    sh = Image.new('RGB', (size_px * 2, (size_px + 18) * len(rows)))
    for i, t in enumerate(tiles):
        sh.paste(t, ((i % 2) * size_px, (i // 2) * (size_px + 18)))
    sh.save(out_png)


# ---------------------------------------------------------------- v5: the charge glow's depth
def glow_depth(info, f=None):
    """his head's half-depth (model X, the side camera's axis: Smash's world depth once he faces either way) beside the
    left hand at the charge pose (start frame 12): max |head point X - LHandN X| over the head's mesh points; and the
    hand's / head's centres for the record"""
    import numpy as np
    frames, smash = info['frames'][anim.START], info['smash']
    f = anim.START_FRAMES - 1 if f is None else f
    rest = anim.world([{b[0]: (b[3], b[4], b[5]) for b in smash}], smash, 0)
    w = anim.world(frames, smash, f)
    pts = []
    for bn, v in anim.HEAD:
        m = np.array(w[bn]) @ np.linalg.inv(np.array(rest[bn]))
        pts.append((m @ np.array([v[0], v[1], v[2], 1.0]))[:3])
    pts = np.array(pts)
    hand = anim._pos(w, 'LHandN')
    half = float(np.max(np.abs(pts[:, 0] - hand[0])))
    return {'head_half_depth': round(half, 3), 'hand': [round(float(c), 3) for c in hand],
            'head_centre': [round(float(c), 3) for c in pts.mean(axis=0)], 'margin': GLOW_MARGIN,
            'depth': round(half + GLOW_MARGIN, 2)}


# ---------------------------------------------------------------- build
def build(sm_dir, out_dir, sh_skill, sh_se_wav, fd_args, png=None, halo=True):
    import omo
    import supamario_fakedeath_build as FD
    import supamario_godfist_build as GB
    fdir = FD.build(sm_dir, out_dir, fd_args['fd_skill'], fd_args['fd_se_wav'], fd_args['cb'], fd_args.get('png'),
                    halo)
    assert GB.SE_IDS.get('gf_hit_ll') == SND_HIT_CH, GB.SE_IDS
    mo = os.path.join(fdir, 'motion', 'body')
    vbn = os.path.join(sm_dir, 'model', 'body', 'c00', 'model.vbn')
    outs, bones, info = anim.build(mo, vbn, os.path.join(sh_skill, '164_VGT_HMR.ean'), mo)
    trans = [h for n, _p, h in bones if n == 'TransN'][0]
    for m in anim.MOTIONS:
        o = outs[('main', m)]
        assert o.frames == anim.frames_of(m)
        assert all(max(abs(v) for v in o.sample(trans, f)[0]) < 1e-6 for f in range(o.frames)), 'TransN moves'
    js = {m: anim.joints(info['frames'][m], info['smash']) for m in anim.MOTIONS}
    fire_y = round(js[anim.HOLD][FX_AT['fire']]['HipN'][1], 2)
    global GLOW_DEPTH
    glow = glow_depth(info)
    GLOW_DEPTH = glow['depth']
    with open(os.path.join(out_dir, 'sledgehammer_frames.json'), 'w') as fh:
        json.dump({'start_frames': anim.START_FRAMES, 'hold_frames': anim.HOLD_FRAMES, 'rate_segments': rate_segments(),
                   'hit': [HIT_FROM, HIT_TO], 'hit_charged': [HIT_FROM_CH, HIT_TO_CH], 'cancel_hit': CANCEL_HIT,
                   'iasa': IASA, 'joints': js, 'fire_y': fire_y, 'info': info['info'], 'glow_depth': glow,
                   'overhead': anim.OVERHEAD,
                   # v4: each fist's side-view distance to his head and height over its top (anim.fist_clearance)
                   'fist_clearance': {m: [anim.fist_clearance(info['frames'][m], info['smash'], f, anim.HEAD)
                                          for f in range(anim.frames_of(m))] for m in anim.MOTIONS}}, fh)
    os.makedirs(os.path.join(out_dir, 'preview'), exist_ok=True)
    anim.pose_sheet(os.path.join(sh_skill, '164_VGT_HMR.ean'), vbn, os.path.join(out_dir, 'preview',
                                                                              'sledgehammer_pose_v3_v4.png'))
    if png:
        anim.sheet(outs, bones, png, hitbox=(HIT_Z, HIT_Y, HIT_SIZE), hit_frames=range(HIT_FROM_CH, HIT_TO))
    rep, p = convert_fx(sh_skill, fd_args['cb']['gf']['cmn_vfx'], os.path.join(fdir, 'effect', 'supamario'), halo)
    assert not rep['facing_problems'], rep['facing_problems']
    os.makedirs(os.path.join(out_dir, 'preview'), exist_ok=True)
    preview(os.path.join(out_dir, 'preview', 'sledgehammer_hitbox_fx.png'), outs, omo.vbn_read(vbn), fire_y, p, rep)
    with open(os.path.join(out_dir, 'sledgehammer_fx.json'), 'w') as fh:
        json.dump(dict(rep, fire_y=fire_y, size=SH_FX_SCALE), fh, indent=1)
    scripts(os.path.join(fdir, 'script', 'animcmd', 'body'), fire_y)
    sound_bank(fdir, out_dir, sh_se_wav)
    GB.msc(os.path.join(fdir, 'script', 'msc', 'supamario.mscsb'))
    return fdir


def main():
    a = sys.argv[1:]
    opts = {}
    halo = '--no-halo' not in a
    if not halo:
        a.remove('--no-halo')
    for k in ('--sh-skill', '--sh-se-wav', '--fd-skill', '--fd-se-wav', '--skill', '--se-wav', '--ean', '--cmn-vfx',
              '--skill-vfx', '--cmn-se', '--stb', '--png'):
        if k in a:
            i = a.index(k)
            opts[k] = a[i + 1]
            del a[i:i + 2]
    need = ('--sh-skill', '--sh-se-wav', '--fd-skill', '--fd-se-wav', '--skill', '--se-wav', '--ean', '--cmn-vfx')
    if len(a) != 2 or any(k not in opts for k in need):
        sys.exit(__doc__)
    gf = {'ean': opts['--ean'], 'cmn_vfx': opts['--cmn-vfx'], 'skill_vfx': opts.get('--skill-vfx'),
          'cmn_se': opts.get('--cmn-se'), 'stb': opts.get('--stb')}
    cb = {'skill': opts['--skill'], 'se_wav': opts['--se-wav'], 'gf': gf}
    fd = {'fd_skill': opts['--fd-skill'], 'fd_se_wav': opts['--fd-se-wav'], 'cb': cb}
    print(build(a[0], a[1], opts['--sh-skill'], opts['--sh-se-wav'], fd, opts.get('--png'), halo))
    print('sounds: ' + ', '.join('%s 0x%08X' % kv for kv in SE_IDS.items()) + '; hits 0x%08X / 0x%08X' % (
        SND_HIT, SND_HIT_CH))
    print('effects: ' + ', '.join('%s 0x%08X' % kv for kv in FX_IDS.items()))
    print('swing: hit %d-%d (charged %d-%d), on-hit cancel %.2f, IASA %.2f, end %d; rates %s' % (
        HIT_FROM, HIT_TO - 1, HIT_FROM_CH, HIT_TO_CH - 1, CANCEL_HIT, IASA, HOLD_END,
        [(round(a, 2), round(z, 2), round(h, 3), round(c, 3)) for a, z, h, c in rate_segments()]))
    for pct in (0, 50, 100, 150):
        print('at %d%%: uncharged knockback %.1f, hitstun %d (+%d); charged knockback %.1f, hitstun %d' % (
            pct, knockback(HIT, pct), hitstun(HIT, pct, HITSTUN_ADD), HITSTUN_ADD, knockback(HIT_CH, pct),
            hitstun(HIT_CH, pct)))


if __name__ == '__main__':
    main()
