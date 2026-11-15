#!/usr/bin/env python3
"""Supamario's Core Breaker (up special, status 0x154; Dragon Ball Xenoverse 2's Ultimate 2070_FIT_COR): the package,
built over the Super God Fist's (v17: tools/supamario_godfist_build.py, run first with its own inputs).

  python3 -I tools/supamario_corebreaker_build.py SUPAMARIO_DIR OUT_DIR --skill 2070_FIT_COR_DIR
        --se-wav COR_WAV_DIR [the God Fist's: --ean 030_GOD_CSA.ean --cmn-vfx VFX_CMN_DIR --skill-vfx 002_GOK_CSG_DIR
        --cmn-se GF_WAV_DIR --stb SOUNDLABELTABLE] [--png SHEET.png]

COR_WAV_DIR: the skill's SE (CAR_BTL_U2070_COR_SE.acb, cues 1-5 decoded: `python3 -I tools/xv2acb.py extract ...` +
`node tools/xv2acb_decode.mjs ...`) and CMN's Hit_L (CAR_BTL_CMN.acb cue 52). Writes OUT_DIR/fighter/supamario (the
God Fist's v17 files, then): motion/body (SpecialHi / SpecialAirHi: tools/supamario_corebreaker_anim.py, no TransN),
script/animcmd/body (specialhi: game / effect / expression; specialairhi JUMPs to it as vanilla's), script/msc
(fighters/supamario/supamario.c: cb_* with CB_* from msc_values()), effect/supamario (PtcSupamarioCb*,
EffSupamarioCbCrg / Fire: tools/supamario_corebreaker_fx.py, tools/xv2_smash_fx.py's settings), sound (CB_SE in his
bank, the soundlabeltable's row 3249 grown) and OUT_DIR/corebreaker_fx.json.

The move (fighters/supamario/README.md "Core Breaker"; his movement is speeds the MSC sets, the user's answers):
- 0-5 crouch, 6-29 the rise (CB_RISE_V a frame slowing by CB_RISE_DECEL: RISE_HEIGHT up), super armor; 30-59 the
  hover (still, no armor; the stick back turns him); 60- the dive (CB_DIVE_V at CB_DIVE_DEG below level, light homing,
  super armor, ledges): the catch box on his fist (CATCH_DMG); landing -> the miss's landing (CB_LAND_LAG frames);
  CB_DIVE_MAX frames or the height he started from -> FallSpecial.
- a catch (a fighter's body, not lying down, not invincible / intangible): he's invincible, holds it at his fist
  (36 frames: BURN_HITS x BURN_DMG), then drives it down 45 degrees: on the ground the crash (CRASH_DMG; it's put down
  on the stage as the God Fist's victim and slides: no tech, no KO), else (off the stage: CB_DRIVE_MAX frames or the
  floor height) the explosion in the air (CRASH_DMG, KO knockback EXPLOSION_KB) and FallSpecial.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import supamario_corebreaker_anim as anim  # noqa: E402

# ---------------------------------------------------------------- the timeline (the motion's segments)
SEG = {}
_f = 0
for _s in anim.SEGMENTS:
    SEG[_s[0]] = (_f, _f + _s[4] - 1)
    _f += _s[4]
RISE_FROM = SEG['rise'][0]                 # 6
HOVER_FROM = SEG['charge'][0]              # 30
FLARE_FROM = SEG['flare'][0]               # 40
DIVE_FROM = SEG['dive'][0]                 # 60
DIVE_LAST = SEG['dive_loop2'][1]           # 103
LAND, LAND_END = SEG['land_miss']          # 104, 163
HOLD, HOLD_END = SEG['grab_hold']          # 164, 199
DRIVE = SEG['grab_dive'][0]                # 200
CRASH, CRASH_END = SEG['crash']            # 238, 305
AIRREL, AIRREL_END = SEG['air_release']    # 306, 349

# ---------------------------------------------------------------- speeds (units a frame; the MSC sets them)
RISE_FRAMES = HOVER_FROM - RISE_FROM       # 24
RISE_V = anim.RISE_HEIGHT / (RISE_FRAMES / 2.0 - 0.25)  # 4.66: up, slowing evenly to 0 at the hover (the -0.25:
                                                       # whether the game adds the acceleration before or after
                                                       # moving him is unknown: within ~2 of RISE_HEIGHT either way)
RISE_DECEL = RISE_V / RISE_FRAMES                      # 0.19 a frame
RISE_VX = 0.4                              # XV2: 0.1 m a frame forward over the launch (entry 0 Movement 9-25)
DIVE_DEG = 48.0                            # XV2 entries 3 / 4: Movement (0, -1.0, 1.1 forward) a frame
DIVE_V = 1.4866 * 5.04                     # 7.49: XV2's 1.49 m a frame at the body's 5.04 units a metre
DIVE_MAX = 40                              # frames (XV2: up to 46)
FLOOR_MARGIN = 3.0                         # the dive / drive never go below the height he started at, less this
HOME_RANGE = 50.0                          # light homing (user): fighters ahead and below within this
HOME_CONE = 30.0                           # degrees either side of the dive's line
HOME_TURN = 1.5                            # degrees a frame
HOME_MAX = 10.0                            # degrees from DIVE_DEG at most
DRIVE_DEG = 45.0                           # XV2 entry 10 from 281: (0, -0.9, 0.9) a frame
DRIVE_V = 0.9 * math.sqrt(2.0) * 5.04      # 6.41
DRIVE_MAX = 30                             # frames, then the explosion in the air (XV2: 64, then entry 13)
HOLD_RISE = 10.0                           # XV2 entry 10: 2 m up at the catch
HOLD_RISE_N = 6
FALL_LIMIT = 30.0                          # gravity's limit while his speeds are set (above any of them)
FALL_VX = 1.0                              # his speed along his facing into FallSpecial after a dive
CRASH_BACK_V = 1.6                         # XV2 entry 12: a 6.5 m slide back (x0.5 here), ground friction stops it
TURN_STICK = 0.5                           # the hover's B-reverse: the stick this far back

# ---------------------------------------------------------------- the victim, the hits
HOLD_X, HOLD_Y = 9.0, -2.0                 # its feet at his fist (the dive pose's RHandN: 6.3 ahead, 3.1 up)
CRASH_X = 9.0
HOLD_HITSTUN = 30.0
HANDOFF = CRASH + 3                        # the victim to gf_tick's put-down (God Fist v17: no tech)
FALL_WAIT = 27.0                           # gf_tick's wait for a down (off the edge)
LAND_LAG = LAND_END - LAND + 1             # 60: the miss's landing (user: "very long"; XV2 entry 5 is 59 frames)
# damage (user: "The total damage should be 26%"): 3 + 4 x 1.5 + 17
CATCH_DMG = 3.0
BURN_HITS = 4
BURN_DMG = 1.5
CRASH_DMG = 17.0
assert abs(CATCH_DMG + BURN_HITS * BURN_DMG + CRASH_DMG - 26.0) < 1e-6
BURN_AT = [HOLD + 4 + 8 * k for k in range(BURN_HITS)]      # 168, 176, 184, 192
EXPLOSION_KB = dict(Angle=40, KBG=60, FKB=0, BKB=30)          # off the stage: KOs (README "Core Breaker": ~75% before)
CRASH_KB = dict(Angle=0, KBG=0, FKB=0, BKB=20)                # on the stage: a flinch; the MSC puts it down
INVINCIBLE = (CRASH_END - HOLD) + 10        # from the catch through the crash / the explosion
CATCH_FREEZE = 6

# ---------------------------------------------------------------- variables (New_Var slots 0x20-0x21)
CB_VAR = 0x0F000380 + 0x20                  # the phase (the MSC's cb_ph; the catch: the game script's 3)
CB_V_SLOT = 0x0F000380 + 0x21               # the victim's player slot (Target_Slot_Get)
# v3: every one per object (scope 0): a move-scoped New_Var is reset to 0 by the script's start, after the MSC's init
# has set cb (1: the second up special's hover), which would skip the hover's detection box
VARS = [('cb', CB_VAR, 0), ('cb_slot', CB_V_SLOT, 0), ('cb_tmp', 0x0F000380 + 0x22, 0),
        ('cb_used', 0x0F000380 + 0x23, 0), ('cb_rise_y', 0x0F000380 + 0x24, 0)]
CB_USED = 0x0F000380 + 0x23               # v3: per fighter (object scope): 0 none used, 1 the rise, 2 the hover / dive
CB_RISE_Y = 0x0F000380 + 0x24             # v3: his height at the rise's start (the dive's floor)
RISE_CANCEL = RISE_FROM + 10              # v3: the rise cancellable into an attack from here (its burst: 10 frames,
                                          # ~37 of its ~55 units, the speed 4.7 -> 2.7)
DIVE_MIN_DROP = 30.0                      # v3: the dive may always go this far below where it starts
LASTHIT_STATUS = 0x0F0000B2
LASTHIT_BODY = 0x0F000100 + 0x20 * 2 + 0x1B
NO_DOWN = 0x80000000
DOWN_LO, DOWN_HI, DOWN_FURAFURA = 0x4D, 0x57, 0x5B
HOLD_STATUS = 0x46                          # v3: a downed fighter caught by the hover's box is put in Damage (hitstun)

# ---------------------------------------------------------------- sounds (his bank 2144, row 3249: after the God Fist's)
SE_ROW = 0xCB1
CB_SE = {'cb_rise': ('CAR_BTL_U2070_COR_SE_Rise', 0.0),                   # BAC skill SE cue 1 (entry 0 at 0)
         'cb_charge': ('CAR_BTL_U2070_COR_SE_Ki_Rservoir', 0.0, 50, 10),  # cue 2 (entry 1 at 25), cut to the hover
         'cb_release': ('CAR_BTL_U2070_COR_SE_Ki_Rlease', 0.0),           # cue 3 (entry 2 at 110)
         'cb_rush': ('CAR_BTL_U2070_COR_SE_Rush', 0.0),                   # cue 4 (the dive; cue 6 = its stop)
         'cb_explosion': ('CAR_BTL_U2070_COR_SE_Explosion', 0.0),         # cue 5 (entries 12 / 13)
         'cb_hit_l': ('Hit_L', 0.0)}                                      # CMN cue 52 (the victim, entry 19)
SE_IDS = {'cb_rise': 0x0CB10092, 'cb_charge': 0x0CB10093, 'cb_release': 0x0CB10094, 'cb_rush': 0x0CB10095,
          'cb_explosion': 0x0CB10096, 'cb_hit_l': 0x0CB10097}
GF_DOWN_SE = 0x0CB10090                     # the God Fist's Down (CMN cue 106), at the hand-off
RELEASE_SND_AT = FLARE_FROM - HOVER_FROM    # the hover's frame of Ki_Rlease (XV2 entry 2 at 110: our flare)
# v2: the charge orb (BAC effect 0, XV2 45 -> 111 of its 72-frame animation) on screen from its frame to the flare
ORB_ON = HOVER_FROM + int(round((45 - 40) * (SEG['charge'][1] - SEG['charge'][0] + 1) / 70.0))
ORB_FRAMES = int(round(72 * (FLARE_FROM - ORB_ON) / 66.0))


def fl(v):
    return '%sf' % repr(float(v))


def msc_values():
    """the CB_* names in fighters/supamario/supamario.c"""
    return {'CB_VAR': '0x%X' % CB_VAR, 'CB_V_SLOT': '0x%X' % CB_V_SLOT,
            'CB_RISE_FROM': fl(RISE_FROM), 'CB_HOVER_FROM': fl(HOVER_FROM), 'CB_DIVE_FROM': fl(DIVE_FROM),
            'CB_LAND_END': fl(LAND_END), 'CB_LAND': fl(LAND), 'CB_HOLD_RISE_N': str(HOLD_RISE_N),
            'CB_HOLD_RISE_V': fl(HOLD_RISE / HOLD_RISE_N), 'CB_HOLD_HITSTUN': fl(HOLD_HITSTUN),
            'CB_HOLD_X': fl(HOLD_X), 'CB_HOLD_Y': fl(HOLD_Y), 'CB_HOLD': fl(HOLD),
            'CB_DRIVE_V': fl(DRIVE_V), 'CB_DRIVE_COS': fl(math.cos(math.radians(DRIVE_DEG))),
            'CB_DRIVE_SIN': fl(math.sin(math.radians(DRIVE_DEG))), 'CB_DRIVE_MAX': str(DRIVE_MAX),
            'CB_DRIVE': fl(DRIVE), 'CB_CRASH_END': fl(CRASH_END), 'CB_CRASH_BACK_V': fl(CRASH_BACK_V),
            'CB_CRASH_X': fl(CRASH_X), 'CB_CRASH': fl(CRASH), 'CB_HANDOFF': fl(HANDOFF),
            'CB_AIRREL_END': fl(AIRREL_END), 'CB_AIRREL': fl(AIRREL), 'CB_FALL_WAIT': fl(FALL_WAIT),
            'CB_RISE_VX': fl(RISE_VX), 'CB_RISE_V': fl(RISE_V), 'CB_RISE_DECEL': fl(RISE_DECEL),
            'CB_DIVE_DEG': fl(DIVE_DEG), 'CB_DIVE_V': fl(DIVE_V), 'CB_DIVE_MAX': str(DIVE_MAX),
            'CB_FLOOR_MARGIN': fl(FLOOR_MARGIN), 'CB_FALL_LIMIT': fl(FALL_LIMIT), 'CB_FALL_VX': fl(FALL_VX),
            'CB_HOME_D2': fl(HOME_RANGE ** 2), 'CB_HOME_CONE': fl(HOME_CONE), 'CB_HOME_TURN': fl(HOME_TURN),
            'CB_HOME_MAX': fl(HOME_MAX), 'CB_DOWN_LO': fl(DOWN_LO), 'CB_DOWN_HI': fl(DOWN_HI),
            'CB_TURN_STICK': fl(TURN_STICK), 'CB_RELEASE_SND_AT': str(RELEASE_SND_AT),
            'CB_SND_RISE': '0x%X' % SE_IDS['cb_rise'], 'CB_SND_CHARGE': '0x%X' % SE_IDS['cb_charge'],
            'CB_SND_RELEASE': '0x%X' % SE_IDS['cb_release'], 'CB_SND_RUSH': '0x%X' % SE_IDS['cb_rush'],
            'CB_SND_EXPLOSION': '0x%X' % SE_IDS['cb_explosion'], 'CB_SND_HIT': '0x%X' % SE_IDS['cb_hit_l'],
            'CB_SND_DOWN': '0x%X' % GF_DOWN_SE,
            # v3: the split (the rise; up special again: the hover / dive)
            'CB_USED': '0x%X' % CB_USED, 'CB_RISE_Y': '0x%X' % CB_RISE_Y, 'CB_RISE_CANCEL': fl(RISE_CANCEL),
            'CB_DIVE_MIN_DROP': fl(DIVE_MIN_DROP), 'CB_RESET_LO': fl(0x3F), 'CB_RESET_HI': fl(0x4C),
            'CB_CLIFF_LO': fl(0x72), 'CB_CLIFF_HI': fl(0x7A), 'CB_DEAD': fl(0xB1), 'CB_REBIRTH': fl(0xB2),
            'CB_ENTRY': fl(0x14F), 'CB_DOWN_FURAFURA': fl(DOWN_FURAFURA), 'CB_HOLD_STATUS': fl(HOLD_STATUS)}


# ---------------------------------------------------------------- ACMD helpers (the God Fist's)
def cmd(name, *params):
    return acmd.Command(acmd.BY_NAME[name.lower()], list(params))


def size(cmds):
    return sum(acmd.INFO[c.ident]['size'] for c in cmds)


def if_(var, method, value, body):
    return [cmd('float_var_compare', var, method, float(value)), cmd('true', 2 + size(body))] + body


def setf(value, var):
    return cmd('set_float', float(value), var)


def hitbox(**kw):
    d = dict(ID=0, Part=0, Bone=0, Damage=1.0, Angle=0, KBG=0, FKB=0, BKB=0, Size=1.0, X=0.0, Y=0.0, Z=0.0,
             Effect=0, Trip=0.0, Hitlag=1.0, SDI=1.0, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=1, SFXType=1,
             **{'Ground/Air': 3, 'Direct/Indirect': 1}, Type=4, HitBits=0x3F, Unk41=0, CollisionPart=0xF, NoScale=0,
             Shieldable=1, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0, HitAllStates=0, FacingRestrict=3,
             NoGrabRelease=0, TeamDamage=0, DisableHitlag=0, NoGFX=0, Flinchless=0, Shape=0, HitstunMul=0.0,
             HitstopMul=0.0, HitstopFrames=0, SelfHitstopMul=0.0, SelfHitstopFrames=0, DIMul=0.0)
    d.update(kw)
    ident = acmd.BY_NAME['extra_special_hitbox']
    return acmd.Command(ident, [d[n] for n in acmd.INFO[ident]['syntax']])


def gfx(name, graphic, bone, x, y, z, size_=1.0, rot=(0.0, 0.0, 0.0), terminate=1):
    if name == 'external_graphic':
        return cmd(name, graphic, bone, x, y, z, rot[0], rot[1], rot[2], size_, terminate)
    return cmd(name, graphic, bone, x, y, z, rot[0], rot[1], rot[2], size_, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, terminate)


def timeline(blocks):
    """[(frame, [commands])] -> one script, frames in order (several blocks at a frame kept in their order)"""
    out, last = [], None
    for f, body in sorted(blocks, key=lambda b: b[0]):
        if not body:
            continue
        if f != last and f > 0:
            out.append(cmd('frame', float(f)))
        last = f
        out += body
    return out


# ---------------------------------------------------------------- the game script
FIST = (6.3, 3.1)                            # the dive pose's RHandN (ahead, up of TransN)
DETECT_SIZE = 2.5                            # v3: the hover's detection box (his body is ~4 across): not scaled
# v3 (user: "I'd like for the hitboxes to match the adjustments"): the hitboxes sized to an effect grow with it, by
# the effect's new scale over its v2 one, centred on the effect: (v2 size, v3 size)
#   catch (the dive's fist box): the fist fire, 1.75 -> CB_FX_SCALE; the body box (ID 1, 4.5) is his body: unchanged
#   burn (the hold's hits): the hit loop on the fist, 1.75 -> CB_FX_SCALE
#   crash / explosion: the explosion (effect 3), v2's half of 1.75 -> CB_FX_SCALE; at the explosion's place (his fist)
_CB_SCALE = 2.25                             # supamario_corebreaker_fx.CB_FX_SCALE (asserted in build())
HB = {'catch': (5.5, round(5.5 * _CB_SCALE / 1.75, 2)), 'burn': (7.0, round(7.0 * _CB_SCALE / 1.75, 2)),
      'crash': (9.0, round(9.0 * _CB_SCALE / 0.875, 2)), 'explosion': (11.0, round(11.0 * _CB_SCALE / 0.875, 2)),
      'detect': (DETECT_SIZE, DETECT_SIZE), 'body': (4.5, 4.5)}
CRASH_AT = (6.26, 1.93)                      # the crash explosion's place (the crash pose's RHandN, effect 3's call)
DETECT_AT = (1.0, 6.5)                       # at his middle (ahead, up)
VICTIM_MID = (HOLD_X, HOLD_Y + 5.0)          # the held victim's middle


def game_script():
    s = [acmd.new_var(n, v - 0x0F000380, 0, 0.0, scope) for n, v, scope in VARS]
    blocks = []
    # the dive (60-): the catch box on his fist and his body (3%; misses a fighter lying down: Ground/Air bit 31),
    # ledges on (vanilla's Allow/Disallow_Ledgegrab 1, the MSC's func_56)
    blocks.append((DIVE_FROM, [cmd('allow/disallow_ledgegrab', 1),
                               hitbox(ID=0, Bone=0, Damage=CATCH_DMG, BKB=20, Size=HB['catch'][1], Y=FIST[1], Z=FIST[0],
                                      HitstopFrames=CATCH_FREEZE, SelfHitstopFrames=CATCH_FREEZE,
                                      **{'Ground/Air': NO_DOWN | 3}),
                               hitbox(ID=1, Bone=0, Damage=CATCH_DMG, BKB=20, Size=4.5, Y=5.3, Z=2.0,
                                      HitstopFrames=CATCH_FREEZE, SelfHitstopFrames=CATCH_FREEZE,
                                      **{'Ground/Air': NO_DOWN | 3})]))
    # the catch, checked every dive frame while diving (cb 2): a fighter's body (Hit_Check kinds 2: not a shield),
    # not lying down (LASTHIT_STATUS), not invincible / intangible (LASTHIT_BODY 0); a refused one ends the checks
    # (cb 2.25: the MSC dives on)
    def catch_check(refused, downed=False):
        take = [setf(3, CB_VAR), cmd('target_slot_get', 2, CB_V_SLOT), cmd('remove_all_hitboxes'),
                cmd('body_state_set', 0, 1, INVINCIBLE)]
        ok = [setf(1, 0x0F000380 + 0x22)]
        if not downed:              # the dive: not a fighter lying down (v3's hover box: yes, the user)
            ok += if_(LASTHIT_STATUS, 3, DOWN_LO, if_(LASTHIT_STATUS, 2, DOWN_HI, [setf(0, 0x0F000380 + 0x22)]))
            ok += if_(LASTHIT_STATUS, 0, DOWN_FURAFURA, [setf(0, 0x0F000380 + 0x22)])
        ok += if_(LASTHIT_BODY, 1, 0, [setf(0, 0x0F000380 + 0x22)])
        ok += if_(0x0F000380 + 0x22, 0, 1, take)
        ok += if_(0x0F000380 + 0x22, 0, 0, [setf(refused, CB_VAR), cmd('remove_all_hitboxes')])
        return [cmd('hit_check', 0, 0, 2), cmd('true', 2 + size(ok))] + ok
    check = catch_check(2.25)
    for f in range(DIVE_FROM + 1, DIVE_LAST + 1):
        blocks.append((f, if_(CB_VAR, 0, 2, check)))
    # v3 (user: "The moment the button is pressed for the hover, there should be a very small detection box (smaller
    # than Supamario's hurtbox) that checks if it hit an opponent. If it hits an opponent it should skip Supamario to
    # the catch part of the dive"): the hover's first frame (both ways in: the second up special's jump to it, or up
    # special again in the rise), DETECT_SIZE at his middle, the catch's damage and rules; caught (cb 3) -> the MSC's
    # hold; refused (cb 1.25) -> the hover goes on
    # (user: "The detection box for Core Breaker should be able to hit a downed opponent": Ground/Air 3, no bit 31,
    # no down-status refusal; shields, invincible and intangible fighters still aren't caught)
    blocks.append((HOVER_FROM, [hitbox(ID=0, Bone=0, Damage=CATCH_DMG, BKB=20, Size=DETECT_SIZE, Y=DETECT_AT[1],
                                       Z=DETECT_AT[0], HitstopFrames=CATCH_FREEZE, SelfHitstopFrames=CATCH_FREEZE,
                                       **{'Ground/Air': 3})]))
    blocks.append((HOVER_FROM + 2, [cmd('remove_all_hitboxes')]))
    det = catch_check(1.25, downed=True)
    for f in range(HOVER_FROM + 1, HOVER_FROM + 4):
        blocks.append((f, if_(CB_VAR, 0, 1, det)))
    # the dive starts with a clean hit record (a refused detection hit can't catch later)
    blocks.append((DIVE_FROM, [cmd('hit_reset'), cmd('hit_log_clear', 0)]))
    # every later segment starts with no hitboxes (the dive's gone)
    for f in (LAND, HOLD, CRASH, AIRREL):
        blocks.append((f, [cmd('remove_all_hitboxes')]))
    # the burn (cb 3): BURN_HITS x BURN_DMG on the held victim (Part 1, its record cleared before each)
    for f in BURN_AT:
        blocks.append((f, if_(CB_VAR, 0, 3, [cmd('hit_log_clear', 1),
                                             hitbox(ID=0, Part=1, Bone=0, Damage=BURN_DMG, BKB=10, Size=HB['burn'][1],
                                                    Y=VICTIM_MID[1], Z=VICTIM_MID[0], SFXLevel=0, SFXType=4,
                                                    Effect=1, HitstopFrames=3, SelfHitstopFrames=0,
                                                    Shieldable=0, DIMul=0.001, SDI=0.0)])))
        blocks.append((f + 1, if_(CB_VAR, 0, 3, [cmd('remove_all_hitboxes')])))
    # the crash on the stage (cb 6): CRASH_DMG, a flinch (the MSC puts it down at HANDOFF: no launch, no tech)
    blocks.append((CRASH + 1, if_(CB_VAR, 0, 6, [cmd('hit_log_clear', 2), hitbox(
        ID=0, Part=2, Bone=0, Damage=CRASH_DMG, Size=HB['crash'][1], Y=CRASH_AT[1], Z=CRASH_AT[0], SFXLevel=2,
        SFXType=1, Effect=1,
        HitstopFrames=8, SelfHitstopFrames=6, Shieldable=0, SDI=0.0, DIMul=0.001, **CRASH_KB)])))
    blocks.append((CRASH + 2, [cmd('remove_all_hitboxes')]))
    # the explosion off the stage (cb 7): CRASH_DMG, KO knockback; the MSC lets the victim go the same frame
    blocks.append((AIRREL + 1, if_(CB_VAR, 0, 7, [cmd('hit_log_clear', 2), hitbox(
        ID=0, Part=2, Bone=0, Damage=CRASH_DMG, Size=HB['explosion'][1], Y=FIST[1], Z=FIST[0], SFXLevel=2, SFXType=1,
        Effect=1, HitstopFrames=10, SelfHitstopFrames=6, Shieldable=1, **EXPLOSION_KB)])))
    blocks.append((AIRREL + 2, [cmd('remove_all_hitboxes')]))
    return s + timeline(blocks)


# ---------------------------------------------------------------- effects
FX_DASH_CLOUD, FX_BIG_CLOUD = 0x1000009, 0x1000020
SIZE_MUL = {}                                 # v3 (user, v2's clip: "The effects for Core Breaker are too small"): no
                                              # halving (v1 / v2 halved the charge orb, its end flash and the explosion:
                                              # the Q10 default); every effect at supamario_corebreaker_fx.CB_FX_SCALE
GUARD = {9: 5, 8: 3, 12: 3, 3: 6}             # BAC effect -> the phase whose segment it plays in (cb)


def effect_script(fx, bones, cmn_fx):
    """the BAC's skill effects at their frames (corebreaker_fx.json's placements), on bone 0 following him
    (External_Graphic: offsets up / forward only, no turn: the God Fist's facing rule) or on his body bones (the
    aura), guarded by the phase where the segment is reached by a jump; the fire / hit loops terminated as the
    dive, the hold and the drive end"""
    bi = {b[0]: i for i, b in enumerate(bones)}
    blocks = []
    ids = {}
    for x in fx['effects']:
        eid = x['bac_effect']
        body = []
        for pt in x['parts']:
            sets = pt.get('ptcl') or []
            mdl = pt.get('model') or {}
            graphics = [int(s['id'], 16) for s in sets] + ([int(mdl['id'], 16)] if 'id' in mdl else [])
            if not graphics:
                continue
            ids.setdefault(eid, []).extend(graphics)
            sz = pt['size'] * SIZE_MUL.get(eid, 1.0)
            for g in graphics:
                if pt['bone'] == 'bone 0 (TopN)':
                    body.append(gfx('external_graphic', g, 0, 0.0, float(pt['offset'][1]), float(pt['offset'][2]),
                                    sz))
                else:
                    body.append(gfx('external_graphic', g, bi[pt['bone']], 0.0, 0.0, 0.0, sz))
        if eid in GUARD:
            body = if_(CB_VAR, 0, GUARD[eid], body)
        blocks.append((x['frame'], body))
    # the air release (cb 7): the explosion (effect 3) and XV2 entry 13's effect 9 where his fist is
    rel = []
    for eid in (3, 9):
        x = [e for e in fx['effects'] if e['bac_effect'] == eid][0]
        for pt in x['parts']:
            for s in (pt.get('ptcl') or []):
                rel.append(gfx('external_graphic', int(s['id'], 16), 0, 0.0, FIST[1], FIST[0],
                               pt['size'] * SIZE_MUL.get(eid, 1.0)))
    blocks.append((AIRREL, if_(CB_VAR, 0, 7, rel)))
    # the charge (0) ends as the flare starts (XV2: off at 111, our FLARE_FROM); the fist's fire (2), the wind (7),
    # the hit loop (8) and the flare (12) end as their part ends
    blocks.append((FLARE_FROM, [cmd('terminate_graphic_effect', g, 1, 0) for g in ids.get(0, [])]))
    stop = [cmd('terminate_graphic_effect', g, 1, 0) for e in (2, 7) for g in ids.get(e, [])]
    for f in (LAND, HOLD, AIRREL):
        blocks.append((f, list(stop)))
    stop2 = [cmd('terminate_graphic_effect', g, 1, 0) for e in (8, 12) for g in ids.get(e, [])]
    for f in (CRASH, AIRREL):
        blocks.append((f, list(stop2)))
    # XV2's ground effects (StageBG 140 / 640 / 440 / 160) with Smash's own and the God Fist's converted BTL_CMN ones
    blocks.append((RISE_FROM, if_(CB_VAR, 0, 0, [gfx('graphic_effect', FX_DASH_CLOUD, 0, 0.0, 0.0, 0.0, 1.0)])))
    land = [gfx('graphic_effect', FX_BIG_CLOUD, 0, 0.0, 0.0, 4.0, 0.8)]
    blocks.append((LAND, if_(CB_VAR, 0, 5, land)))
    crash = [gfx('graphic_effect', FX_BIG_CLOUD, 0, 0.0, 0.0, CRASH_X, 1.2)]
    if cmn_fx.get('PHitSmk'):
        crash.append(gfx('graphic_effect', cmn_fx['PHitSmk'], 0, 0.0, 0.0, CRASH_X, 5.04 / 8.5 * 1.5))
    blocks.append((CRASH, if_(CB_VAR, 0, 6, crash)))
    if cmn_fx.get('MHit'):
        blocks.append((HOLD, if_(CB_VAR, 0, 3, [gfx('graphic_effect', cmn_fx['MHit'], 0, 0.0, VICTIM_MID[1],
                                                       VICTIM_MID[0], 5.04 / 8.5)])))
    return timeline(blocks)


def expression_script():
    blocks = [(DIVE_FROM, [cmd('rumble', 0x10, 0)]),
              (HOLD, if_(CB_VAR, 0, 3, [cmd('rumble', 0x12, 0)])),
              (CRASH, if_(CB_VAR, 0, 6, [cmd('rumble', 0x12, 0), cmd('quake', 4)])),
              (AIRREL + 1, if_(CB_VAR, 0, 7, [cmd('rumble', 0x12, 0), cmd('quake', 3)]))]
    return timeline(blocks)


def scripts(body_dir, fx, bones, cmn_fx):
    """specialhi and specialairhi (the same motion and script: in game / sound vanilla's specialairhi JUMPs to
    specialhi, in effect / expression it is its own) replaced in game / effect / sound / expression; the sounds are the
    MSC's (the Kamehameha's test 25: a motion change re-runs a sound script), so the sound scripts are empty"""
    makers = {'game': game_script, 'effect': lambda: effect_script(fx, bones, cmn_fx), 'sound': lambda: [],
              'expression': expression_script}
    for part, make in makers.items():
        path = os.path.join(body_dir, part + '.bin')
        f = acmd.ACMDFile.load(path)
        for name in ('specialhi', 'specialairhi'):
            assert f.script(name) is not None, (part, name)
            f.scripts[acmd.crc(name)] = make() + [acmd.Command(acmd.END)]
        f.save(path)


# ---------------------------------------------------------------- the sound bank
def sound_bank(fdir, out_dir, wav_dir):
    """CB_SE into his bank (the God Fist build's, in fdir/sound) and the soundlabeltable (out_dir/sound/config): the
    God Fist's sound_bank with this move's tones; SE_IDS checked"""
    import supamario_godfist_build as GB
    table = os.path.join(out_dir, 'sound', 'config', 'soundlabeltable.bin')
    old_se, old_ids = dict(GB.CMN_SE), dict(GB.SE_IDS)
    try:
        GB.CMN_SE.clear()
        GB.CMN_SE.update(CB_SE)
        with open(table, 'rb') as fh:
            data = fh.read()
        tmp = table + '.in'
        with open(tmp, 'wb') as fh:
            fh.write(data)
        ids = GB.sound_bank(fdir, tmp, wav_dir, out_dir)
        os.remove(tmp)
        got = dict(ids)
    finally:
        GB.CMN_SE.clear()
        GB.CMN_SE.update(old_se)
        GB.SE_IDS.clear()
        GB.SE_IDS.update(old_ids)
    assert got == SE_IDS, ('SE_IDS is out of date', {k: hex(v) for k, v in got.items()})
    return got


# ---------------------------------------------------------------- build
def build(sm_dir, out_dir, skill_dir, se_wav, gf_args, png=None, halo=True):
    import omo
    import supamario_godfist_build as GB
    import supamario_corebreaker_fx as CF
    import xv2_smash_fx as FX
    fdir = GB.build(sm_dir, out_dir, gf_args['ean'], gf_args.get('cmn_vfx'), None, gf_args.get('skill_vfx'),
                    gf_args.get('cmn_se'), gf_args.get('stb'))
    cmn_fx = dict(GB.CMN_FX)
    # the motion: SpecialHi / SpecialAirHi over the God Fist's pacs
    mo = os.path.join(fdir, 'motion', 'body')
    vbn = os.path.join(sm_dir, 'model', 'body', 'c00', 'model.vbn')
    ean = os.path.join(skill_dir, '2070_FIT_COR.ean')
    out, bones, info = anim.build(mo, vbn, ean, mo)
    frames_json = os.path.join(out_dir, 'corebreaker_frames.json')
    doc = {'segments': [{'name': n, 'start': s, 'end': e - 1, 'anim': g[1], 'src': [g[2], g[3]], 'loop': g[5],
                         'ground': g[7]} for n, s, e, g in anim.timeline()],
           'joints': anim.joints(info['frames'], info['smash'])}
    with open(frames_json, 'w') as fh:
        json.dump(doc, fh)
    trans = [h for n, _p, h in bones if n == 'TransN'][0]
    o = out[('main', anim.MOTIONS[0])]
    assert all(max(abs(v) for v in o.sample(trans, f)[0]) < 1e-6 for f in range(o.frames)), 'TransN moves'
    assert o.frames == AIRREL_END + 1
    if png:
        anim.sheet(o, bones, png, anim.sheet_frames())
    # the effects onto the God Fist's bank
    fx_dir = os.path.join(fdir, 'effect', 'supamario')
    conv, p, made, pkg = CF.convert(skill_dir, fx_dir, fdir, preview_dir=os.path.join(out_dir, 'preview'))
    # v2: the charge orb's own 72-frame animation in the frames it is on screen (XV2: 66 of them, 45 -> 111; ours
    # from its start to the flare), so it is seen whole (fading in, swirling) instead of only its first frames
    orb = conv['models']['Cor_Crg.emo']['folder']
    FX.retime_model(os.path.join(fx_dir, 'model', orb), ORB_FRAMES)
    assert CF.CB_FX_SCALE == _CB_SCALE, 'HB is out of date'
    fx_doc, facing = CF.placements(pkg, doc, conv)
    assert not facing and not conv['emitter_facing_problems'], (facing, conv['emitter_facing_problems'])
    fx = {'effects': fx_doc, 'settings': {'hdr_cap': FX.HDR_CAP, 'size': CF.CB_FX_SCALE, 'size_mul': SIZE_MUL}}
    fx.update({k: v for k, v in conv.items() if k != 'emitter_facing_problems'})
    with open(os.path.join(out_dir, 'corebreaker_fx.json'), 'w') as fh:
        json.dump(fx, fh, indent=1)
    # the scripts, the sound bank, the MSC
    scripts(os.path.join(fdir, 'script', 'animcmd', 'body'), fx, omo.vbn_read(vbn), cmn_fx)
    if halo:
        # v3 (user): the fake-glow halos on, both moves (they share the bank): tools/supamario_halo_test.py's pass
        # over the finished effect files, at xv2_smash_fx.HALO_ALPHA
        import supamario_halo_test as HT
        rep, _p, _g = HT.build(out_dir, out_dir, {'PtcSupamarioCb': skill_dir,
                                                  'PtcSupamarioGfCsg_': gf_args.get('skill_vfx'),
                                                  'PtcSupamarioGfBtl_': gf_args.get('cmn_vfx')}, FX.HALO_ALPHA)
        with open(os.path.join(out_dir, 'halo_report.json'), 'w') as fh:
            json.dump(rep, fh, indent=1)
    sound_bank(fdir, out_dir, se_wav)
    GB.msc(os.path.join(fdir, 'script', 'msc', 'supamario.mscsb'))
    return fdir


def main():
    a = sys.argv[1:]
    opts = {}
    halo = '--no-halo' not in a
    if not halo:
        a.remove('--no-halo')
    for k in ('--skill', '--se-wav', '--ean', '--cmn-vfx', '--skill-vfx', '--cmn-se', '--stb', '--png'):
        if k in a:
            i = a.index(k)
            opts[k] = a[i + 1]
            del a[i:i + 2]
    if len(a) != 2 or '--skill' not in opts or '--se-wav' not in opts or '--ean' not in opts:
        sys.exit(__doc__)
    gf = {'ean': opts['--ean'], 'cmn_vfx': opts.get('--cmn-vfx'), 'skill_vfx': opts.get('--skill-vfx'),
          'cmn_se': opts.get('--cmn-se'), 'stb': opts.get('--stb')}
    print(build(a[0], a[1], opts['--skill'], opts['--se-wav'], gf, opts.get('--png'), halo))
    print('sounds: ' + ', '.join('%s 0x%08X' % kv for kv in SE_IDS.items()))


if __name__ == '__main__':
    main()
