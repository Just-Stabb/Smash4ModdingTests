#!/usr/bin/env python3
"""Supamario's Super God Fist (dash attack; Dragon Ball Xenoverse 2's 030_GOD_CSA "Super God Fist"): the package.

  python3 tools/supamario_godfist_build.py SUPAMARIO_DIR OUT_DIR --ean 030_GOD_CSA.ean [--cmn-vfx VFX_CMN_DIR]
                                           [--png SHEET.png]

SUPAMARIO_DIR: his installed fighter/supamario folder (the user's supamario.zip: supamario_universal_v1 + the
ported sound ids; its motion/body, script/animcmd/body and effect/supamario are the base). --ean: the skill's
animations (XV2's 030_GOD_CSA.ean, the default body). --cmn-vfx: XV2's vfx/cmn (BTL_CMN.eepk and its files): the
common effects the BAC plays, converted into his bank. Writes OUT_DIR/fighter/supamario/:
  motion/body/{main,lhand,rhand,mariopt1}.pac   AttackDash replaced (tools/supamario_godfist_anim.py)
  script/animcmd/body/{game,effect,sound,expression}.bin   the attackdash scripts replaced (below)
  script/msc/supamario.mscsb   fighters/supamario/supamario.c (gf_init / gf_update in the AttackDash status)
  effect/supamario/supamario.010d0000.{ptcl,efc}   with --cmn-vfx: + PtcSupamarioGfBtl_MHit / _MHitSmk / _PHitSmk

v3 (fighters/supamario/README.md "Super God Fist v3"): XV2's own animation; the frame numbers below are v2's (v3:
the punch 14-17, the check 18, the God Fist part from 46, the hold 46-95 (#0 0-40 at x0.8), the launch at 96 with an
8-frame freeze, acting from 141; the constants hold them).

The move (fighters/supamario/README.md "Super God Fist" has the XV2 skill read, frame by frame; v2: the victim's
motion from XV2's own CMN.ean animations, reference/xv2/godfist_victim_cmn.json):
- frames 7-10: the dash punch (4%, a 9-frame freeze on both: CMN.bdm #160's stun 9 / 9). Frame 11: if it hit a
  fighter's body (Hit_Check kinds 2) the God Fist starts: `gf` = 1 (New_Var slot 0x30, the MSC reads it), the
  victim's player slot kept (`gf_slot`), Supamario invincible (XV2: invulnerable 0-40 of the follow-up); the MSC
  jumps the motion to frame 40 (the God Fist part). Else the whiff ends at frame 38 (vanilla Mario's dash attack
  acts from 39).
- 40-49: the victim held 11 in front of him on the ground (the position variables each frame), in hitstun, frozen,
  no stage collision (an aerial victim is pulled down to him), leaning back 29 -> 57 degrees (XV2 #179 0-40).
- 50: the God Fist (11%, a 24-frame freeze on both: XV2 holds the fist in the victim through its 0.8x slow-down);
  low knockback: the launch is scripted.
- the flight (a thread, from the end of the freeze): GF_FLIGHT (44) frames: XV2's launch (#179 40-58, 18 frames: the
  fast backward tumble) then its tumbling slide along the ground (#96, 77 frames in 26), its travel scaled to GF_DIST
  (60), its pelvis height x GF_HSCALE as the body's middle, its tilt (XV2: 935 degrees) scaled to end lying on its
  back (GF_PHI_END 810); frozen in hitstop (so its own status can't move or turn it), whatever its percent or
  weight; its controller is ignored from the launch. Supamario acts only when it's over (GF_IASA: he doesn't move
  meanwhile, and the victim is placed relative to him, as the move's last hit). It drops onto the ground lying, and
  goes to DownWait (status 0x50), upright again there, for GF_DOWN (50) frames with the controller still ignored.
- downed: a hit that launches it (its status leaves the down statuses) gives the controller back; a hit that
  doesn't (DownDamage 0x57) makes it stand up (DownStand 0x54) once the down damage is over; else the controller
  comes back after GF_DOWN frames (it can then get up, roll or attack as from any down).
"""
import json
import math
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import supamario_godfist_anim as anim  # noqa: E402

# ---------------------------------------------------------------- numbers
GF_SLOT_BASE = 0x30                     # New_Var slots 0x30-0x38 (0x0F0003B0-8)
GF_VAR = 0x0F000380 + GF_SLOT_BASE      # gf: 0 dash punch / whiff, 1 caught, 2 struck (the MSC reads it)
V_SLOT, V_ST, V_SIT, V_PHASE, V_CNT, V_ONE, V_LOCK, V_ROT = (0x0F000380 + GF_SLOT_BASE + k for k in range(1, 9))
# v4: gf_spin 1 while the victim in gf_slot may be turned (Rotation_Set; every release zeroes it), gf_wd 1 while
# the hold watchdog (thread GF_WATCH) is on duty, gf_tmp / gf_tmp2 scratch (the watchdog's reads, the diag logs)
V_SPIN, V_WD, V_TMP, V_TMP2 = (0x0F000380 + GF_SLOT_BASE + k for k in range(9, 13))
VARS = [('gf', GF_VAR, 1), ('gf_slot', V_SLOT, 0), ('gf_st', V_ST, 0), ('gf_sit', V_SIT, 0),
        ('gf_phase', V_PHASE, 0), ('gf_cnt', V_CNT, 0), ('gf_one', V_ONE, 0), ('gf_lock', V_LOCK, 0),
        ('gf_rot', V_ROT, 0), ('gf_spin', V_SPIN, 0), ('gf_wd', V_WD, 0), ('gf_tmp', V_TMP, 0),
        ('gf_tmp2', V_TMP2, 0)]
# gf values: 0 the dash punch / whiff, 1 caught (held), 2 struck (the flight thread has the victim), 3 the strike
# missed (the victim let go at STRIKE + 1)
GF_MISSED = 3
PUNCH, PUNCH_END = anim.GF_PUNCH, anim.GF_PUNCH_END   # the hitbox 14-17 (the BAC's), the hit check at 18
JUMP_TO, STRIKE = anim.GF_JUMP_TO, anim.GF_STRIKE      # 46, 96 (#0 frame 40: the launch)
WHIFF_END = float(anim.GF_WHIFF_END)     # the whiff's end (MSC): 44
HOLD_X = 11.5                           # the victim held this far in front of him (his fist 7.3-7.5 ahead, + 4)
PUNCH_DMG, STRIKE_DMG = 4.0, 11.0
PUNCH_FREEZE = 9                        # the punch's hitstop, both: CMN.bdm #160's stun 9 / 9 (the BDM the hitbox
                                        # names: #160 isn't in GOK_PLAYER.bdm)
STRIKE_FREEZE = 8                       # the launch's hitstop, both (the slow hold is the animation's: #0 0-40 x0.8)
INVINCIBLE = 75                         # Supamario invincible from the catch (XV2: 0-40 of #0 at x0.8, +the launch)
# the victim's motion: XV2's own (CMN.ean #179 held / launched, then #96 the tumbling slide; tools/
# supamario_godfist_xv2.py -> reference/xv2/godfist_victim_cmn.json): its travel, its pelvis height and its tilt
# toward the travel, frame by frame
XV2_CURVES = os.path.join(HERE, '..', 'reference', 'xv2', 'godfist_victim_cmn.json')
GF_LAUNCH = 18                          # #179 40-58 at XV2's speed (launched: the fast tumble)
GF_SLIDE = 26                           # #96's 77 frames (the slide on the ground) ~3x faster
GF_FLIGHT = GF_LAUNCH + GF_SLIDE        # 44
GF_DIST = 60.0                          # XV2's 20.0 m from the launch -> 60 units (3 a metre): lands 71 in front
GF_HSCALE = 5.0                         # the pelvis' height (metres, ~1 standing) -> the body's middle (units)
GF_PHI_END = 810.0                      # its last tilt: XV2 turns 935 degrees to lie on its back (57 -> 993);
                                        # 810 (57 -> 810, x0.8) leaves it on its back facing up as Smash's DownWaitU
GF_PIVOT = 5.0                          # the body's middle above its feet (the spin is kept around it)
GF_THICK = 1.5                          # half its thickness (lying, its middle at least this high)
GF_LAND_WAIT = 20                       # frames it may take to reach the ground after the flight
GF_DOWN = 50                            # the downed frames with the controller off (v1 60: the slide is longer)
GF_THREAD = 0x47                        # the flight thread's ID
GF_WATCH = 0x46                         # the hold watchdog thread's ID (v4)
GF_WATCH_FRAMES = 160                   # its lifetime: the catch (18) to well past the strike (97 + the freeze)
STATUS_ATTACK_DASH = 0x27               # Supamario's AttackDash status (func_272 / func_273)
STRIKE_PART = 1                         # v4: the strike's hitboxes on Part 1, a hit record of their own (v3 had
                                        # Part 0, the punch's: its record already held the victim, so the strike
                                        # could never connect: no launch, the lean left on the victim)
# diagnostics (the diag build, --diag): a write to 0x0F0003F0 + k is an OSReport line with the diag executable
# (tools/diag_godfist_cave.py: `S4GF k=.. v=.. n=..`); the normal executables ignore these writes (0x3C9-0x3FF
# read 0, writes do nothing: acmd_ext_cave.py hv_var), so the diag scripts are harmless without it
DIAG = False
DIAG_BASE = 0x0F0003F0
D_CATCH_KINDS, D_SLOT, D_HOLD_FRAME, D_HOLD_ROT, D_STRIKE_KINDS, D_FLIGHT, D_WD_RELEASE, D_ROT_AFTER, \
    D_MISSED, D_MSC_JUMP, D_MSC_RATE1, D_MSC_EXIT, D_PHASE, D_WD_STATUS = range(14)
IASA = float(STRIKE + 1 + GF_FLIGHT)    # the God Fist's cancel frame (MSC): the victim's flight is over (141)
ROOT_Z = [0.0] * anim.FRAMES             # his TransN z by motion frame (build() sets it from the animation)
DOWN_HELD = (0x4D, 0x53)                # DownBound .. DownWait (0x53): still down; 0x57 DownDamage
DOWN_DAMAGE, DOWN_WAIT, DOWN_WAIT2, DOWN_STAND = 0x57, 0x50, 0x51, 0x54
# position variables (docs/position-variables.md), target 2 = the last fighter hit
LH_OFFX, LH_OFFY, LH_GROUND = 0x0F000055, 0x0F000056, 0x0F0000B6
# effects (common 0x01000000 + id, Supamario's bank 0x0341xxxx) and sounds
FX_DASH, FX_DASH_CLOUD, FX_FLASH, FX_GLOW, FX_CHARGE = 0x100008C, 0x1000009, 0x1000075, 0x10000BF, 0x100000F
FX_FIRE, FX_RINGS, FX_BIG_CLOUD = 0x341000E, 0x100003A, 0x1000020
SND_DASH, SND_HEAVY, SND_FIRE, SND_BURST, SND_START = 0xCB10071, 0x5E0007, 0xCB10027, 0x0CB1008D, 0x0CB1008E
VOICE = 0x80000007
FIST = 0x14                             # bone RHandN: XV2's God Fist is a right (b_R_Arm2 holds the victim)
# XV2's common effects the BAC plays (EEPK type 1 = vfx/cmn/BTL_CMN.eepk): converted into his bank by effects()
# ({name: ACMD id}; empty: Smash's own stand-ins). The skill's own (030_GOD_CSA.eepk: skill effects 0, 1, 2, 11)
# and CMN 180 (not in BTL_CMN.eepk) are still missing.
CMN_EFFECTS = {'MHit': ('Btl_MHit.emp', 220), 'MHitSmk': ('Btl_MHitSmk.emp', 120),
               'PHitSmk': ('Btl_PHitSmk.emp', 160)}
CMN_FX = {}
CMN_SIZE = 5.04 / 8.5                   # xv2_to_ptcl makes 8.5 units a metre; his body is 5.04 a metre


def msc_values():
    """the GF_* names in fighters/supamario/supamario.c"""
    return {'GF_VAR': '0x%X' % GF_VAR, 'GF_WHIFF_END': '%sf' % WHIFF_END, 'GF_JUMP_TO': '%sf' % float(JUMP_TO),
            'GF_IASA': '%sf' % IASA}


# ---------------------------------------------------------------- ACMD building
def cmd(name, *params):
    return acmd.Command(acmd.BY_NAME[name.lower()], list(params))


def size(cmds):
    return sum(acmd.INFO[c.ident]['size'] for c in cmds)


def if_(var, method, value, body):
    """Float_Var_Compare(var, method, value) True{ body } (True's offset: its own 2 words + the block)"""
    return [cmd('float_var_compare', var, method, float(value)), cmd('true', 2 + size(body))] + body


def loop(n, body):
    """Set_Loop(n){ body } Goto(back to the block's start: minus its words)"""
    return [cmd('set_loop', n)] + body + [cmd('goto', -size(body))]


def thread(tid, flags, body):
    """Thread_Start(Offset, ID, Flags){ body } + the block's own Script_End; Offset = the words from Thread_Start
    to past that Script_End (tools/acmd_ext_test.py thread_tests: 4 + block + 1)"""
    return [cmd('thread_start', 4 + size(body) + 1, tid, flags)] + body + [acmd.Command(acmd.END)]


def setf(value, var):
    return cmd('set_float', float(value), var)


def per_slot(make):
    """make(target) for the victim's player slot (gf_slot 1-8 -> targets 3-10), so it still finds it after the
    move (target 2 is only "the last fighter hit" while the move lasts)"""
    out = []
    for s in range(1, 9):
        out += if_(V_SLOT, 0, s, make(2 + s))
    return out


def hitbox(name, **kw):
    d = dict(ID=0, Part=0, Bone=0, Damage=1.0, Angle=0x16E, KBG=100, FKB=0, BKB=0, Size=1.0, X=0.0, Y=0.0, Z=0.0,
             Effect=0, Trip=0.0, Hitlag=1.0, SDI=1.0, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=1, SFXType=1,
             **{'Ground/Air': 3, 'Direct/Indirect': 1}, Type=4, HitBits=0x3F, Unk41=0, CollisionPart=0xF, NoScale=0,
             Shieldable=1, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0, HitAllStates=0, FacingRestrict=3,
             NoGrabRelease=0, TeamDamage=0, DisableHitlag=0, NoGFX=0, Flinchless=0, Shape=0, HitstunMul=0.0,
             HitstopMul=0.0, HitstopFrames=0, SelfHitstopMul=0.0, SelfHitstopFrames=0, DIMul=0.0)
    d.update(kw)
    ident = acmd.BY_NAME[name.lower()]
    return acmd.Command(ident, [d[n] for n in acmd.INFO[ident]['syntax']])


def gfx(name, graphic, bone, x, y, z, size_=1.0, rot=(0.0, 0.0, 0.0), terminate=1):
    if name == 'external_graphic':
        return cmd(name, graphic, bone, x, y, z, rot[0], rot[1], rot[2], size_, terminate)
    return cmd(name, graphic, bone, x, y, z, rot[0], rot[1], rot[2], size_, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, terminate)


_CURVES = None


def xv2_curves():
    """{'179': [(s, h, phi) by frame], '96': [...]} from XV2_CURVES"""
    global _CURVES
    if _CURVES is None:
        d = json.load(open(XV2_CURVES))
        out = {}
        for a, f, sv, h, ph in d['rows']:
            out.setdefault(a, []).append((sv, h, ph))
        _CURVES = out
    return _CURVES


def _at(rows, f):
    f = max(0.0, min(len(rows) - 1.0, f))
    i = int(math.floor(f))
    j = min(len(rows) - 1, i + 1)
    t = f - i
    return tuple(a + (b - a) * t for a, b in zip(rows[i], rows[j]))


def xv2_victim(k):
    """XV2's (travel m, pelvis height m, tilt degrees) at flight frame k (0 = the launch, #179 frame 40): #179 40-58
    at its speed, then #96 77 frames in GF_SLIDE. The two animations don't meet: #96 starts 1.1 m lower (eased in
    over its first 6 frames) and 75 degrees back (all of #96 turned on by that, so the tumble never turns back)"""
    c = xv2_curves()
    held, slide = c['179'], c['96']
    if k <= GF_LAUNCH:
        return _at(held, 40 + k)
    u = (k - GF_LAUNCH) * (len(slide) - 1) / float(GF_SLIDE)
    sv, h, ph = _at(slide, u)
    end, start = held[-1], slide[0]
    w = max(0.0, 1.0 - u / 6.0)
    return sv, h + (end[1] - start[1]) * w, ph + (end[2] - start[2])


def place(cx, cy, phi):
    """feet offset (in front of him, up) and the Rotation_Set X (degrees) for its middle at (cx, cy) tilted phi
    toward the travel (away from him: it faces him, so that is backward, X = -phi): the feet go where the middle
    stays put (the spin assumed about the feet), and no part of the body (the middle +- GF_PIVOT along its up axis,
    +- GF_THICK across it) below the ground"""
    r = math.radians(phi)
    low = cy - GF_PIVOT * abs(math.cos(r)) - GF_THICK * abs(math.sin(r))
    if low < 0:
        cy -= low
    return cx - GF_PIVOT * math.sin(r), cy - GF_PIVOT * math.cos(r), -phi


def hold_lean(k, n):
    """its tilt at hold frame k of n (XV2: #179 0-40, leaning back 29 -> 57 degrees as the fist goes in)"""
    return _at(xv2_curves()['179'], 40.0 * k / max(1, n - 1))[2]


def flight_offset(k):
    """flight_frame(k) as written at flight frame k: less the way he has moved since the launch (his TransN:
    #0's travel through the flip; thread frame k is his motion frame STRIKE + 1 + k)"""
    x, y, a = flight_frame(k)
    f = min(STRIKE + 1 + k, len(ROOT_Z) - 1)
    return x - (ROOT_Z[f] - ROOT_Z[STRIKE + 1]), y, a


# the victim's slide: XV2's CMN effects on it (BAC entry 3: CMN 160 at #96 20 and 42, CMN 120 at 62), at the
# flight frames those #96 frames fall on
SLIDE_FX = [(GF_LAUNCH + int(round(u * GF_SLIDE / 77.0)), n) for u, n in ((20, 'PHitSmk'), (42, 'PHitSmk'),
                                                                        (62, 'MHitSmk'))]


def flight_frame(k):
    """the victim's feet offset (in front of him, up) and Rotation_Set X at flight frame k (1 .. GF_FLIGHT)"""
    s0, _h0, p0 = xv2_victim(0)
    s_end, _h, p_end = xv2_victim(GF_FLIGHT)
    sv, h, ph = xv2_victim(k)
    cx = HOLD_X + (sv - s0) * GF_DIST / (s_end - s0)
    phi = p0 + (ph - p0) * (GF_PHI_END - p0) / (p_end - p0)
    return place(cx, h * GF_HSCALE, phi)


def dlog(k, var=None, value=None):
    """diag build only: OSReport line k with a variable's value (or a constant)"""
    if not DIAG:
        return []
    if var is None:
        return [setf(value, DIAG_BASE + k)]
    # DIAG = 0 - (0 - var): SUB_FLOAT_2 is a read and a write for these IDs; a diag ID reads 0
    return [setf(0, V_TMP2), cmd('sub_float_2', V_TMP2, var), cmd('sub_float_2', DIAG_BASE + k, V_TMP2)]


def dlog_get(k, get):
    """diag: run `get` (a command filling V_TMP) and log V_TMP"""
    return [get] + dlog(k, V_TMP) if DIAG else []


def unspin():
    """the victim (gf_slot) upright, its stage collision back (air: it drops to the floor), gf_spin 0"""
    out = per_slot(lambda t: [cmd('rotation_set', t, 0.0, 0.0, 0.0)])
    if DIAG:
        out += per_slot(lambda t: dlog_get(D_ROT_AFTER, cmd('rotation_get', t, 0, V_TMP)))
    return out + [setf(0, V_SPIN)]


def hold_release(reason):
    """the hold ends without the launch (Supamario's move interrupted / replaced, the strike missed, time):
    the victim upright, its stage collision back, the watchdog off"""
    return (dlog(D_WD_RELEASE, value=reason) + unspin()
            + per_slot(lambda t: [cmd('stage_collision_set', t, 5)]) + [setf(0, V_WD)])


def watchdog():
    """GF_WATCH (Flags 1: it runs in hitlag too), from the catch: every frame, while gf_wd is 1 (until the flight
    thread has the victim, or a release): his status (Status_Get(0)) not AttackDash any more (hit, grabbed, KO'd:
    the game script that holds the victim is gone) or gf back to 0 (a new dash attack) -> let go; gf 2 (struck:
    the flight thread's) or GF_MISSED (the main script let go) -> off duty; gf still 1 past the strike's frame (his
    motion frame, Motion_Get) -> let go. At the end (GF_WATCH_FRAMES) still on duty and not struck -> let go.
    A thread survives status changes (acmd_ext_cave.py: threads are dropped only at the object's set-up)."""
    body = [cmd('status_get', 0, V_TMP)]
    body += if_(V_TMP, 1, STATUS_ATTACK_DASH, dlog(D_WD_STATUS, V_TMP) + hold_release(1))
    body += if_(V_WD, 0, 1, if_(GF_VAR, 0, 0, hold_release(2)))
    body += if_(V_WD, 0, 1, if_(GF_VAR, 0, 2, [setf(0, V_WD)]))
    body += if_(V_WD, 0, 1, if_(GF_VAR, 0, GF_MISSED, [setf(0, V_WD)]))
    body += if_(V_WD, 0, 1, [cmd('motion_get', 0, 1, V_TMP)] + if_(V_TMP, 5, STRIKE + 2.5, hold_release(3)))
    b = loop(GF_WATCH_FRAMES, if_(V_WD, 0, 1, body) + [cmd('wait', 1.0)])
    b += if_(V_WD, 0, 1, if_(GF_VAR, 1, 2, hold_release(4)))
    return b


def game_script():
    s = [acmd.new_var(n, v - 0x0F000380, 0, 0.0, scope) for n, v, scope in VARS]
    s += [setf(1, V_ONE), cmd('frame', float(PUNCH))]
    s += [hitbox('extra_special_hitbox', ID=0, Bone=FIST, Damage=PUNCH_DMG, Angle=0, KBG=0, FKB=0, BKB=20,
                 Size=4.5, X=0.0, SFXLevel=1, SFXType=1, Type=4, HitstopFrames=PUNCH_FREEZE,
                 SelfHitstopFrames=PUNCH_FREEZE),
          hitbox('extra_special_hitbox', ID=1, Bone=0, Damage=PUNCH_DMG, Angle=0, KBG=0, FKB=0, BKB=20, Size=4.0,
                 Y=6.5, Z=4.0, SFXLevel=1, SFXType=1, Type=4, HitstopFrames=PUNCH_FREEZE,
                 SelfHitstopFrames=PUNCH_FREEZE)]
    s += [cmd('frame', float(PUNCH_END)), cmd('remove_all_hitboxes')]
    s += dlog_get(D_CATCH_KINDS, cmd('hit_get', 0, 0, V_TMP))
    # the catch: a fighter's body hit (not a shield)
    caught = [setf(1, GF_VAR), cmd('target_slot_get', 2, V_SLOT),
              cmd('body_state_set', 0, 1, INVINCIBLE),                 # invincible (XV2: 0-40 of the follow-up)
              cmd('hitstun_set', 2, 20), setf(HOLD_X, LH_OFFX), setf(0, LH_OFFY)]
    caught += dlog(D_SLOT, V_SLOT)
    caught += [setf(1, V_SPIN), setf(1, V_WD)] + thread(GF_WATCH, 1, watchdog())
    # an earlier God Fist's victim (still flying / down): its flight thread stopped, upright, controller back
    earlier = [cmd('thread_stop', GF_THREAD)] + if_(V_SPIN, 0, 1, unspin())
    caught = earlier + per_lock_release() + [setf(0, V_PHASE)] + caught
    s += [cmd('hit_check', 0, 0, 2), cmd('true', 2 + size(caught))] + caught
    # the hold, 46-95 (only reached when caught: the MSC jumps here; guarded anyway)
    for f in range(JUMP_TO, STRIKE):
        s.append(cmd('frame', float(f)))
        # XV2's lean (#179 0-40, back 29 -> 57 degrees), about its feet, frozen in place (hitstop) as it's held
        hold = [setf(HOLD_X, LH_OFFX), setf(0, LH_OFFY), setf(0, LH_GROUND), cmd('hitstun_set', 2, 20),
                cmd('hitstop_set', 2, 2, 0),
                cmd('rotation_set', 2, -hold_lean(f - JUMP_TO, STRIKE - JUMP_TO), 0.0, 0.0)]
        if f in (JUMP_TO, STRIKE - 1):
            hold += dlog_get(D_HOLD_FRAME, cmd('motion_get', 0, 1, V_TMP))
            hold += dlog_get(D_HOLD_ROT, cmd('rotation_get', 2, 0, V_TMP))
        if f == STRIKE - 1:
            hold += [cmd('hit_reset'), cmd('hit_log_clear', STRIKE_PART)]
        s += if_(GF_VAR, 0, 1, hold)
    # 96: the God Fist (Part STRIKE_PART: a hit record of its own; the punch's Part 0 record holds the victim)
    strike = [hitbox('extra_special_hitbox', ID=0, Part=STRIKE_PART, Bone=FIST, Damage=STRIKE_DMG, Angle=0, KBG=0,
                     FKB=0, BKB=25, Size=6.0, X=0.0, Hitlag=1.0, SDI=0.0, SFXLevel=2, SFXType=1, Type=4,
                     IgnoreInvuln=0, HitstopFrames=STRIKE_FREEZE, SelfHitstopFrames=STRIKE_FREEZE, DIMul=0.001),
              hitbox('extra_special_hitbox', ID=1, Part=STRIKE_PART, Bone=0, Damage=STRIKE_DMG, Angle=0, KBG=0,
                     FKB=0, BKB=25, Size=6.0, Y=6.5, Z=HOLD_X, Hitlag=1.0, SDI=0.0, SFXLevel=2, SFXType=1, Type=4,
                     HitstopFrames=STRIKE_FREEZE, SelfHitstopFrames=STRIKE_FREEZE, DIMul=0.001)]
    s += [cmd('frame', float(STRIKE))] + if_(GF_VAR, 0, 1, strike)
    # 97 (after the freeze: the script waits through his hitstop): struck -> the flight thread; else let go
    launched = [setf(2, GF_VAR), cmd('remove_all_hitboxes')] + thread(GF_THREAD, 1, flight_thread())
    s += [cmd('frame', float(STRIKE + 1)), cmd('remove_all_hitboxes')]
    s += if_(GF_VAR, 0, 1, dlog_get(D_STRIKE_KINDS, cmd('hit_get', 0, 0, V_TMP)))
    s += if_(GF_VAR, 0, 1, [cmd('hit_check', 0, 0, 2), cmd('true', 2 + size(launched))] + launched)
    s += if_(GF_VAR, 0, 1, dlog(D_MISSED, value=1) + hold_release(5) + [setf(GF_MISSED, GF_VAR)])
    return s


def per_lock_release():
    """the slot gf_lock names (a victim whose controller an earlier God Fist turned off): back on, gf_lock 0"""
    out = []
    for s in range(1, 9):
        out += if_(V_LOCK, 0, s, [cmd('input_set', 2 + s, 21, 0.0)])
    return out + [setf(0, V_LOCK)]


def flight_thread():
    """the thread: flight (target 2: still the move's last hit), then the landing and the downed state (the
    victim's slot: the move may be over)"""
    b = per_slot(lambda t: [cmd('input_set', t, 21, 1.0)]) + per_slot_lock()    # controller off from the launch
    b += dlog(D_FLIGHT, V_SLOT)
    fx = dict(SLIDE_FX)
    for k in range(1, GF_FLIGHT + 1):
        x, y, a = flight_offset(k)
        b += [setf(x, LH_OFFX), setf(y, LH_OFFY), setf(0, LH_GROUND), cmd('hitstop_set', 2, 2, 0),
              cmd('hitstun_set', 2, 40), cmd('rotation_set', 2, float(a), 0.0, 0.0)]
        if k in fx and fx[k] in CMN_FX:
            # at the victim (its feet's offset from him, on the ground): bone 0, Z forward
            b.append(gfx('graphic_effect', CMN_FX[fx[k]], 0, 0.0, 0.0, float(x), CMN_SIZE))
        b.append(cmd('wait', 1.0))
    # the end: lying on its back (kept turned until DownWait has taken over), 0.5 higher, stage collision back
    # (air): it drops onto the ground
    x, y, a = flight_offset(GF_FLIGHT)
    b += [setf(x, LH_OFFX), setf(y + 0.5, LH_OFFY), setf(5, LH_GROUND), cmd('hitstun_set', 2, 40),
          setf(1, V_PHASE), setf(GF_LAND_WAIT, V_CNT), setf(0, V_ROT)]
    lie = per_slot(lambda t: [cmd('rotation_set', t, float(a), 0.0, 0.0)])
    upright = per_slot(lambda t: [cmd('rotation_set', t, 0.0, 0.0, 0.0)])
    # landing wait (phase 1): on the ground -> DownWait, controller off (phase 2, GF_DOWN frames)
    # v4: every release zeroes the rotation (unspin), whatever was done before (v3: only if gf_rot said it wasn't)
    release = dlog(D_PHASE, V_PHASE) + per_lock_release() + unspin() + [setf(1, V_ROT), setf(0, V_PHASE)]
    land = [setf(2, V_SIT)] + per_slot(lambda t: [cmd('input_get', t, 22, V_SIT)])
    to_down = (per_slot(lambda t: [cmd('status_set', t, DOWN_WAIT)]) + [setf(2, V_PHASE), setf(GF_DOWN, V_CNT)]
               + dlog(D_PHASE, value=2))
    phase1 = lie + land + if_(V_SIT, 0, 0, to_down)
    # still phase 1 (in the air): count down, then give up and give the controller back (it fell off the stage)
    phase1 += if_(V_PHASE, 0, 1, [cmd('sub_float_2', V_CNT, V_ONE)] + if_(V_CNT, 2, 0, release))
    read = per_slot(lambda t: [cmd('status_get', t, V_ST)])
    # phase 2 (down, controller off): DownDamage -> 3; out of the down statuses -> release; time -> release
    # its first frame in DownWait (asked for the frame before): upright again, the down animation lies it down
    phase2 = if_(V_ROT, 0, 0, if_(V_CNT, 3, GF_DOWN - 0.5, upright + [setf(1, V_ROT)]))
    phase2 += if_(V_ST, 0, DOWN_DAMAGE, [setf(3, V_PHASE)])
    # (not in its first frames: the DownWait asked for takes effect on its next frame)
    phase2 += if_(V_PHASE, 0, 2, if_(V_CNT, 4, GF_DOWN - 3, out_of_down(release)))
    phase2 += if_(V_PHASE, 0, 2, [cmd('sub_float_2', V_CNT, V_ONE)] + if_(V_CNT, 2, 0, release))
    # phase 3 (a hit that didn't launch it): once the down damage is over (DownWait) it stands up; launched -> release
    stand = per_slot(lambda t: [cmd('status_set', t, DOWN_STAND)]) + release
    phase3 = if_(V_ST, 0, DOWN_WAIT, stand) + if_(V_PHASE, 0, 3, if_(V_ST, 0, DOWN_WAIT2, stand))
    phase3 += if_(V_PHASE, 0, 3, if_(V_ST, 1, DOWN_DAMAGE, out_of_down(release)))
    # (later phases first: a phase entered this frame starts on the next)
    body = if_(V_PHASE, 0, 3, read + phase3) + if_(V_PHASE, 0, 2, read + phase2) + if_(V_PHASE, 0, 1, phase1)
    b += loop(GF_LAND_WAIT + GF_DOWN + 60, body + [cmd('wait', 1.0)])
    # the thread's end: never leave a controller off, nor the victim turned
    b += if_(V_PHASE, 1, 0, release)
    b += if_(V_SPIN, 0, 1, unspin())
    return b


def per_slot_lock():
    """gf_lock = gf_slot (the slot whose controller is off)"""
    out = []
    for s in range(1, 9):
        out += if_(V_SLOT, 0, s, [setf(s, V_LOCK)])
    return out


def out_of_down(then):
    """then, when gf_st isn't a held-down status (DownBound .. DownWait 0x4D-0x53, DownDamage 0x57)"""
    lo, hi = DOWN_HELD
    return (if_(V_ST, 4, lo, then) + if_(V_PHASE, 1, 0, if_(V_ST, 5, hi, if_(V_ST, 1, DOWN_DAMAGE, then))))


def effect_script():
    """XV2's BAC timings: entry 0 (the dash punch, 1:1 to its frame 18) CMN 220 at 10; entry 1 (the follow-up, #0:
    0-40 x0.8 = 46-96, then 1:1) CMN 120 at #0 60 = 116. The skill's own effects (gold, 030_GOD_CSA.eepk) are
    missing: Smash's stand in (the glow on the fist while it's held, the fire burst / rings at the launch)"""
    hit = CMN_FX.get('MHit')
    s = [cmd('frame', 1.0), gfx('graphic_effect', FX_DASH, 0, 0.0, 0.0, 0.0, 1.0),
         cmd('frame', 10.0)]
    s += [gfx('graphic_effect', hit, 0, 0.0, 5.0, 0.0, 0.8 * CMN_SIZE)] if hit else []
    s += [cmd('frame', 12.0), gfx('graphic_effect', FX_DASH_CLOUD, 0, 0.0, 0.0, 0.0, 0.7)]
    if not hit:
        s += [cmd('frame', float(PUNCH)), gfx('graphic_effect', FX_FLASH, FIST, 2.0, 0.0, 0.0, 0.6)]
    s += [cmd('frame', float(JUMP_TO))] + if_(GF_VAR, 1, 0, [
        gfx('external_graphic', FX_GLOW, FIST, 1.0, 0.0, 0.0, 1.2)])
    s += [cmd('frame', float(STRIKE - 8))] + if_(GF_VAR, 1, 0, [gfx('graphic_effect', FX_CHARGE, FIST, 2.0, 0.0,
                                                                     0.0, 1.3)])
    s += [cmd('frame', float(STRIKE))] + if_(GF_VAR, 1, 0, [
        cmd('terminate_graphic_effect', FX_GLOW, 1, 1),
        gfx('graphic_effect', FX_FIRE, 0, 0.0, 5.0, HOLD_X, 1.6),
        gfx('graphic_effect', FX_RINGS, 0, 0.0, 5.0, HOLD_X, 1.5),
        gfx('graphic_effect', FX_FLASH, 0, 0.0, 5.0, HOLD_X, 2.0)])
    s += [cmd('frame', float(STRIKE + 1))] + if_(GF_VAR, 1, 0, [
        gfx('graphic_effect', FX_BIG_CLOUD, 0, 0.0, 0.0, 0.0, 1.0)])
    smoke = CMN_FX.get('MHitSmk')
    land = [gfx('graphic_effect', smoke, 0, 0.0, 0.0, 0.0, CMN_SIZE)] if smoke else [
        gfx('graphic_effect', FX_DASH_CLOUD, 0, 0.0, 0.0, 0.0, 0.6)]
    s += [cmd('frame', float(STRIKE + 20))] + if_(GF_VAR, 1, 0, land)       # #0 60: the flip's landing
    return s


def sound_script():
    """stand-ins (the skill's own sounds aren't among the files: BAC entry 0 plays the skill's SE / voice cue 0 at
    0, entry 1 cue 81 (ACB type 3) at 0, the victim's entries common SE cue 53 / 74 at 0, entry 9 type 3 cue 35;
    CAR_BTL_GOK_SE.acb holds Goku's throw sounds, cues 0-5, none of these)"""
    s = [cmd('frame', 1.0), cmd('low_voice_clip', VOICE), cmd('frame', 10.0), cmd('sound_effect', SND_DASH)]
    s += [cmd('frame', float(JUMP_TO))] + if_(GF_VAR, 1, 0, [cmd('sound_effect', SND_START)])
    s += [cmd('frame', float(STRIKE))] + if_(GF_VAR, 1, 0, [
        cmd('sound_effect', SND_HEAVY), cmd('sound_effect', SND_FIRE), cmd('sound_effect', SND_BURST)])
    return s


def expression_script():
    s = [cmd('slope_full2', 1, 4, 1), cmd('frame', float(PUNCH)), cmd('rumble', 0x10, 0)]
    s += [cmd('frame', 34.0), cmd('slope_full', 6, 6)]          # the whiff's (vanilla: 38 of 54); the jump runs it
    s += [cmd('frame', float(STRIKE))] + if_(GF_VAR, 1, 0, [cmd('rumble', 0x12, 0), cmd('quake', 4)])
    return s


def scripts(body_dir, out_dir):
    name = 'attackdash'
    for part, make in (('game', game_script), ('effect', effect_script), ('sound', sound_script),
                       ('expression', expression_script)):
        f = acmd.ACMDFile.load(os.path.join(body_dir, part + '.bin'))
        assert f.script(name) is not None
        f.scripts[acmd.crc(name)] = make() + [acmd.Command(acmd.END)]
        os.makedirs(out_dir, exist_ok=True)
        f.save(os.path.join(out_dir, part + '.bin'))


def msc(out_path):
    import supamario_kame_build as kb
    import supamario_kame_values
    vals = kb.supamario_values(supamario_kame_values.SUPAMARIO_FX)      # GF_* included (msc_values)
    src = kb.substitute(os.path.join(HERE, '..', 'fighters/supamario/supamario.c'), vals)
    if DIAG:
        src = src.replace('//GFD ', '')
    code = '\n'.join(line.split('//')[0] for line in src.split('\n'))
    assert 'GF_' not in code.replace('gf_', ''), [w for w in code.split() if 'GF_' in w][:5]
    with tempfile.TemporaryDirectory(dir=os.path.dirname(os.path.abspath(out_path))) as tmp:
        kb.compile_msc(src, out_path, tmp)


def effects(sm_dir, cmn_dir, fdir):
    """XV2's common effects (CMN_EFFECTS, from vfx/cmn's BTL_CMN.eepk) into his bank: new ptcl sets
    PtcSupamarioGf* (tools/xv2_to_ptcl.py, 64-pixel textures) and .efc entries; CMN_FX = their ACMD ids"""
    import efc
    import ptcl
    import xv2_to_ptcl
    src = os.path.join(sm_dir, 'effect', 'supamario')
    dst = os.path.join(fdir, 'effect', 'supamario')
    os.makedirs(dst, exist_ok=True)
    base = 'supamario.010d0000'
    p = ptcl.Ptcl(open(os.path.join(src, base + '.ptcl'), 'rb').read())
    with tempfile.TemporaryDirectory() as pkg:
        # a package of BTL_CMN.eepk alone (vfx/cmn holds five .eepk): links to everything else
        for fn in os.listdir(cmn_dir):
            if not fn.lower().endswith('.eepk') or fn == 'BTL_CMN.eepk':
                os.symlink(os.path.abspath(os.path.join(cmn_dir, fn)), os.path.join(pkg, fn))
        old = xv2_to_ptcl.TEX_MAX
        xv2_to_ptcl.TEX_MAX = 64
        try:
            made, _log = xv2_to_ptcl.convert_package(p, pkg, 'PtcSupamarioGf', emps=[v[0] for v in CMN_EFFECTS.values()],
                                                     strict=False)
        finally:
            xv2_to_ptcl.TEX_MAX = old
    out = p.build()
    assert ptcl.Ptcl(out).validate() == []
    open(os.path.join(dst, base + '.ptcl'), 'wb').write(out)
    e = efc.Efc(open(os.path.join(src, base + '.efc'), 'rb').read())
    by_emp = {}
    for si, name, _chunk in made:
        by_emp.setdefault(name.replace('PtcSupamarioGf', '') + '.emp', e.add(si + 1))
    open(os.path.join(dst, base + '.efc'), 'wb').write(e.build())
    CMN_FX.clear()
    for k, (emp, _xid) in CMN_EFFECTS.items():
        CMN_FX[k] = 0x03410000 | by_emp[emp]
    return made


def build(sm_dir, out_dir, ean_path, cmn_dir=None, png=None):
    fdir = os.path.join(out_dir, 'fighter', 'supamario')
    mo = os.path.join(fdir, 'motion', 'body')
    out, bones, _info = anim.build(os.path.join(sm_dir, 'motion', 'body'),
                                   os.path.join(sm_dir, 'model', 'body', 'c00', 'model.vbn'), ean_path, mo)
    trans = [h for n, _p, h in bones if n == 'TransN'][0]
    ROOT_Z[:] = [out['main'].sample(trans, f)[0][2] for f in range(out['main'].frames)]
    if png:
        import supamario_godfist_render
        supamario_godfist_render.sheet(out['main'], bones, png, anim.SHEET)
    if cmn_dir:
        effects(sm_dir, cmn_dir, fdir)
    scripts(os.path.join(sm_dir, 'script', 'animcmd', 'body'), os.path.join(fdir, 'script', 'animcmd', 'body'))
    os.makedirs(os.path.join(fdir, 'script', 'msc'), exist_ok=True)
    msc(os.path.join(fdir, 'script', 'msc', 'supamario.mscsb'))
    return fdir


def main():
    a = sys.argv[1:]
    opts = {}
    global DIAG
    if '--diag' in a:
        a.remove('--diag')
        DIAG = True
    for k in ('--png', '--ean', '--cmn-vfx'):
        if k in a:
            i = a.index(k)
            opts[k] = a[i + 1]
            del a[i:i + 2]
    if len(a) != 2 or '--ean' not in opts:
        sys.exit(__doc__)
    print(build(a[0], a[1], opts['--ean'], opts.get('--cmn-vfx'), opts.get('--png')))


if __name__ == '__main__':
    main()
