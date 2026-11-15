#!/usr/bin/env python3
"""Supamario's Fake Death (the GROUNDED down special, status 0x155; Dragon Ball Xenoverse 2's Super skill 116_YMC_DIE,
Yamcha's): the package, built over Core Breaker's (tools/supamario_corebreaker_build.py, which runs the Super God Fist's
first; their files stay theirs: only the down special's motions / scripts, the effect bank's new sets, two new tones
and the MSC change).

  python3 -I tools/supamario_fakedeath_build.py SUPAMARIO_DIR OUT_DIR --fd-skill 116_YMC_DIE_DIR --fd-se-wav FD_WAV_DIR
        --cmn-vfx VFX_CMN_DIR [Core Breaker's: --skill 2070_FIT_COR_DIR --se-wav COR_WAV_DIR --ean 030_GOD_CSA.ean
        --skill-vfx 002_GOK_CSG_DIR --cmn-se GF_WAV_DIR --stb SOUNDLABELTABLE] [--png SHEET.png]

FD_WAV_DIR: the skill's SE (CAR_BTL_S116_DIE_SE.acb cues 0 FakeDown / 1 WakeUp: tools/supamario_fakedeath_xv2.py
se-extract + tools/xv2acb_decode.mjs + `se`). Writes OUT_DIR/fighter/supamario (Core Breaker's build, then): motion/body
(SpecialLwStart = the collapse and the lying loop, SpecialLwHold = the wake-up: tools/supamario_fakedeath_anim.py),
script/animcmd/body (speciallwstart / speciallwhold in game / effect / sound / expression), effect/supamario (the revive
ring PtcSupamarioFdBtl_RvlRingON, XV2's BTL_CMN effect 26, with its fake-glow halos), sound (FD_SE in his bank, the
soundlabeltable's row 3249 grown), script/msc (supamario.c's fd_*), OUT_DIR/fakedeath_frames.json and preview/.

The move (fighters/supamario/README.md "Fake Death"): ground only; the collapse (intangible 0-18), lying while the
special button is held (up to FD_HOLD_MAX frames from the start), the wake-up attack (intangible to its frame
INT_B): a ground-only hitbox (no displacement, FD_HITSTUN frames of hitstun, less on repeats) and an air-only one
(a weak launch, the game's own hitstun).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import supamario_fakedeath_anim as anim  # noqa: E402

# ---------------------------------------------------------------- the timeline (motion frames)
LIE_FROM = 32                       # the collapse 0-31 (XV2 0-31), lying from 32 (XV2's loop start)
LIE_LAST = LIE_FROM + anim.LIE_LOOP - 1   # 51: the lying loop's last frame
LIE_BACK = anim.LIE_LOOP - 1        # 19: set back to LIE_FROM from LIE_LAST
WAKE_FRAMES = 66                    # the wake-up: XV2 92-157
WAKE_END = WAKE_FRAMES              # Wait when the frame reaches this (66: after its last frame, 65)
INT_A = 18                          # the collapse intangible 0-18 (XV2 entry 0: Invulnerability "All Attacks Miss" 0-19)
INT_B = 52                          # the wake-up intangible 0-52 (XV2 92-144: the end of XV2's own movement / guard
                                    # cancel window 122-144; the user: "intangibility until near its end")
INT_STEP = 2.0                      # frames written each frame (renewed: Core Breaker v7's rule)
TURN_AT = 2                         # XV2 94: TrackForwardAndBackwards 94-101: turned toward the nearest opponent
HOLD_MAX = 300                      # the user: the lying held at most ~5 s from the collapse's start, then the attack
HIT_FROM, HIT_TO = 20, 23           # XV2 112-116 (BDM #20, CMN.bdm): the hitboxes on wake frames 20-23
HIT_LATE = 3.0                      # the MSC still looks for its victims 3 frames past them (and through the hitlag)
assert anim.SEGMENTS[0][5] == LIE_FROM and sum(s[5] for s in anim.SEGMENTS if s[1] == anim.HOLD) == WAKE_FRAMES

# ---------------------------------------------------------------- his travel (units a frame along his facing)
# XV2's b_C_Base Z each frame (MoveWithAxis Z), as tools/supamario_fakedeath_anim.root_z builds it (checked at build),
# and the BAC's Movement 0.2 m a frame forward XV2 110-116 (wake 18-23) on top: the collapse's hop back (-5.9), the
# wake-up's wind-up back (-1.7), its spring forward (+5.7 + 6.0) and the recovery's last step (+1.9)
VC = [-0.474, -0.802, -0.401, -0.358, -0.33, -0.301, -0.284, -0.273, -0.258, -0.248, -0.234, -0.219, -0.214, -0.207,
      -0.209, -0.217, -0.229, -0.246, -0.054, -0.079, -0.079, -0.074, -0.054, -0.03, -0.02, -0.005]
VW_ANIM = [-0.005, -0.01, -0.02, -0.034, -0.039, -0.054, -0.069, -0.084, -0.108, -0.123, -0.148, -0.153, -0.167,
           -0.167, -0.167, -0.157, -0.143, 0.477, 0.487, 0.438, 0.699, 0.755, 0.647, 0.898, 0.877, 0.428, -0.014, -0.112,
           -0.161, -0.155, -0.092, -0.026, -0.005, 0.0, 0.001, 0.0, 0.0, 0.0, 0.001, 0.001, 0.001, 0.001, 0.002, 0.002,
           0.003, 0.004, 0.004, 0.005, 0.005, 0.006, 0.049, 0.125, 0.18, 0.223, 0.246, 0.255, 0.248, 0.229, 0.192,
           0.153, 0.12, 0.088, 0.06, 0.034, 0.011]
BAC_MOVE = 0.2 * anim.SCALE         # 1.008 a frame
BAC_MOVE_FRAMES = range(18, 24)     # XV2 110-115
EXTRA_PUSH = 1.0                    # v2 (user: "should move him a bit forward"): +1 a frame more over the same frames:
                                    # +6.0 units (the attack's forward travel 11.9, v1 5.9)
VW = [round(v + (BAC_MOVE + EXTRA_PUSH if f in BAC_MOVE_FRAMES else 0.0), 4) for f, v in enumerate(VW_ANIM)]

# ---------------------------------------------------------------- the hit
# XV2: one hitbox, b_C_Base + (0, 0.5 m, 0.75 m ahead), 0.75 m, BDM #20 of CMN.bdm (a Standard hit: 30 frames of
# stun, 9 / 9 hitstop, a 0.25 m push; struck in a floating hit: a knock away 32 frames), 20 damage (2 guarded)
HIT_Z, HIT_Y, HIT_SIZE = round(0.75 * anim.SCALE, 2), round(0.5 * anim.SCALE, 2), round(0.75 * anim.SCALE, 2)
GROUND_HIT = dict(Damage=6.0, Angle=0, KBG=0, FKB=0, BKB=1)        # the user: a grounded victim stays where it is
# v2 (user: 6% both; "should knock opponents away about 4x further than it does now at 0%"): BKB 80 -> 165 (KBG 25,
# 45 degrees): ~183 units at 0% (v1 ~46), knockback() / flight()
AIR_HIT = dict(Damage=6.0, Angle=45, KBG=25, FKB=0, BKB=165)
AIR_HIT_V1 = dict(Damage=3.0, Angle=45, KBG=25, FKB=0, BKB=80)
HITSTOP = 9                          # XV2 BDM #20: UserStun / VictimStun 9 (the ground hit)
HITSTUN = 66                         # the ground hit's hitstun (v2, the user: 66; v1 60; XV2's stun is 30)
REP_MUL = (1.0, 0.6, 0.35, 0.2)     # v2: the n-th ground hit on a fighter still in the previous one's hitstun
REHIT = HITSTOP + 3                  # a hold broken by a new hitstop this many frames ago still counts (fd_tick may
                                     # see the hit first; HIT_LATE: the MSC finds the victim within 3 frames)
VICTIM_MID = 5.0                     # a fighter's middle above its feet (the victim search)
VICTIM_R = HIT_SIZE + 10.0
ST_DAMAGE, ST_DAMAGE_AIR = 0x45, 0x46

# ---------------------------------------------------------------- variables (New_Var slots 0x00-0x1F, 0x3D: MSC only)
V_REP = 0x0F000380 - 1               # + slot 1-8: the ground hits in a row on that slot (slots 0x00-0x07)
V_LAST = 0x0F000388 - 1              # + slot: FD_V_CLOCK at its last ground hit (0x08-0x0F)
V_HS = 0x0F000390 - 1                # + slot: its hitstun held (fd_tick: >0 in the hit's hitstop, <0 -left) (0x10-0x17)
V_HX = 0x0F000398 - 1                # + slot: its X when hit (0x18-0x1F)
V_CLOCK = 0x0F0003BD                 # frames counted by fd_tick (slot 0x3D)

# ---------------------------------------------------------------- effects / sounds
# v2 (user, v1's screenshot: "it should surround Supamario horizontally"): the rings lie flat (X 90) round his lying
# body. Sized from the screenshot: at v1's 1.36 the main ring was ~3.2 units in radius (6.5 across on a ~10.8-unit
# lying Supamario), so ~2.35 a unit of size; 2.6 makes it ~6.1: round him head to boots (his lying body spans
# z -6.7 .. +4.1 from TransN)
FD_FX_SCALE = 2.6
RING_Z = -1.3                        # the call: centred on his lying body along his facing (bone 0, forward offset)
RING_HEIGHTS = {'line': 0.9, 'line_1': 0.0, '9': 0.45, 'sprite': 0.0}   # each emitter's height over the call
                                     # (units at the final size: XV2's 0.8 / 0.3 / 0.6 / 0.2 m stack kept low round him)
FX_DUST = 0x1000009                  # Smash's dash cloud: XV2's Stage BG effect 20 at frame 1 (the stage's own, not
                                     # in the files)
RING_DRAWN = 2.35 / 8.06             # a ring's drawn radius per unit of its emitter scale x the call's size (v1's
                                     # screenshot: radius ~3.2 at size 1.36, scale 8.06): the preview's
RING_Y = 1.8                         # v2: the call's height: his lying body's middle (hips 2.8, the floor 0)
RING_AT = 30                         # XV2: BTL_CMN 26 (Btl_RvlRingON, the knocked-out revive ring) at 30, b_C_Pelvis
RING_EMP = 'Btl_RvlRingON.emp'
SE_ROW = 0xCB1
FD_SE = {'fd_fakedown': ('BRD_S116_DIE_FakeDown', 0.0),   # skill SE cue 0, BAC entry 0 frame 1
         'fd_wakeup': ('BRD_S116_DIE_WakeUp', 0.0)}       # skill SE cue 1, frame 95 (wake 3)
SE_IDS = {'fd_fakedown': 0x0CB10098, 'fd_wakeup': 0x0CB10099}
SND_FAKEDOWN_AT, SND_WAKEUP_AT = 1, 3
FX_RING = 0x03410057                 # the ring's ACMD id (its .efc entry after Core Breaker's; convert_fx checks it)
FX_IDS = {'ring': FX_RING}


def fl(v):
    return '%sf' % repr(float(v))


def vel_code(table, tol=0.02):
    """`if (f < b) { return v; }` pieces: runs of frames within tol of their mean (the motion frame's speed)"""
    pieces, a = [], 0
    while a < len(table):
        b = a + 1
        while b < len(table) and max(table[a:b + 1]) - min(table[a:b + 1]) <= tol:
            b += 1
        pieces.append((a, b, sum(table[a:b]) / float(b - a)))
        a = b
    return ' '.join('if (f < %sf) { return %rf; }' % (float(b) - 0.5, round(v, 4)) for a, b, v in pieces)


def msc_values():
    """the FD_* names in fighters/supamario/supamario.c"""
    return {'FD_VC_CODE': vel_code(VC), 'FD_VW_CODE': vel_code(VW), 'FD_INT_A': fl(INT_A), 'FD_INT_B': fl(INT_B),
            'FD_INT_STEP': fl(INT_STEP), 'FD_LIE_FROM': fl(LIE_FROM), 'FD_LIE_LAST': fl(LIE_LAST),
            'FD_LIE_BACK': fl(LIE_BACK), 'FD_HOLD_MAX': fl(HOLD_MAX), 'FD_TURN_AT': fl(TURN_AT),
            'FD_HIT_FROM': fl(HIT_FROM), 'FD_HIT_TO': fl(HIT_TO), 'FD_HIT_LATE': fl(HIT_LATE),
            'FD_WAKE_END': fl(WAKE_END), 'FD_HIT_Z': fl(HIT_Z), 'FD_HIT_Y': fl(HIT_Y),
            'FD_VICTIM_MID': fl(VICTIM_MID), 'FD_VICTIM_R2': fl(VICTIM_R ** 2), 'FD_HITSTUN': fl(HITSTUN),
            'FD_REP_MUL2': fl(REP_MUL[1]), 'FD_REP_MUL3': fl(REP_MUL[2]), 'FD_REP_MUL4': fl(REP_MUL[3]),
            'FD_REHIT': fl(REHIT), 'FD_V_REP': '0x%X' % V_REP, 'FD_V_LAST': '0x%X' % V_LAST,
            'FD_V_HS': '0x%X' % V_HS, 'FD_V_HX': '0x%X' % V_HX, 'FD_V_CLOCK': '0x%X' % V_CLOCK,
            'FD_ST_DAMAGE_AIR': fl(ST_DAMAGE_AIR), 'FD_ST_DAMAGE': fl(ST_DAMAGE),
            'FD_FX_RING': '0x%X' % FX_RING}


# ---------------------------------------------------------------- knockback (Smash 4's formula), the air hit's flight
def knockback(hit, pct_before, weight=100.0, rage=1.0):
    """Smash 4: ((((p/10 + p*d/20) * 200/(w+100) * 1.4) + 18) * KBG/100 + BKB) * rage, p the % after the hit"""
    d = hit['Damage']
    p = pct_before + d
    if hit.get('FKB'):
        p = hit['FKB']
    return ((((p / 10.0 + p * d / 20.0) * 200.0 / (weight + 100.0) * 1.4) + 18.0) * hit['KBG'] / 100.0 +
            hit['BKB']) * rage


def flight(kb, angle=45.0, gravity=0.09, max_fall=1.5):
    """the launched fighter's horizontal travel (units) and its hitstun (frames): launch speed kb x 0.03 decaying
    0.051 a frame along it, its own gravity once launched (no DI); the travel until the launch speed is spent"""
    v = kb * 0.03
    hs = int(kb * 0.4)
    a = math.radians(angle)
    x = y = vy_g = 0.0
    while v > 0:
        x += v * math.cos(a)
        vy_g = max(-max_fall, vy_g - gravity)
        y += v * math.sin(a) + vy_g
        v -= 0.051
    return round(x, 1), hs


# ---------------------------------------------------------------- ACMD
def cmd(name, *params):
    return acmd.Command(acmd.BY_NAME[name.lower()], list(params))


def hitbox(**kw):
    d = dict(ID=0, Part=0, Bone=0, Damage=1.0, Angle=0, KBG=0, FKB=0, BKB=0, Size=1.0, X=0.0, Y=0.0, Z=0.0,
             Effect=0, Trip=0.0, Hitlag=1.0, SDI=1.0, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=1, SFXType=2,
             **{'Ground/Air': 3, 'Direct/Indirect': 1}, Type=6, HitBits=0x3F, Unk41=0, CollisionPart=0xF, NoScale=0,
             Shieldable=1, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0, HitAllStates=0, FacingRestrict=3,
             NoGrabRelease=0, TeamDamage=0, DisableHitlag=0, NoGFX=0, Flinchless=0, Shape=0, HitstunMul=0.0,
             HitstopMul=0.0, HitstopFrames=0, SelfHitstopMul=0.0, SelfHitstopFrames=0, DIMul=0.0)
    d.update(kw)
    ident = acmd.BY_NAME['extra_special_hitbox']
    return acmd.Command(ident, [d[n] for n in acmd.INFO[ident]['syntax']])


def ground_hitbox():
    """ID 0, grounded fighters only (Ground/Air 1): no displacement (knockback 1, angle 0, no SDI / DI), the hitstun
    from HitstunMul (a negative value adds that many frames: Ultimate's add_reaction_frame; the MSC's fd_tick then
    holds it at HITSTUN x the repeat's multiplier, and the fighter's X where it was hit)"""
    return hitbox(ID=0, Size=HIT_SIZE, Y=HIT_Y, Z=HIT_Z, SDI=0.0, DIMul=0.001, Trip=0.0, SFXLevel=1,
                  HitstunMul=-float(HITSTUN), HitstopFrames=HITSTOP, SelfHitstopFrames=HITSTOP,
                  **{'Ground/Air': 1}, **GROUND_HIT)


def air_hitbox():
    """ID 1, airborne fighters only (Ground/Air 2): a weak launch with the game's own hitstun and hitstop"""
    return hitbox(ID=1, Size=HIT_SIZE, Y=HIT_Y, Z=HIT_Z, SFXLevel=0, **{'Ground/Air': 2}, **AIR_HIT)


def game_scripts():
    start = []                                    # the collapse / lying: nothing timed (the MSC does it all)
    hold = [cmd('frame', float(HIT_FROM)), ground_hitbox(), air_hitbox(),
            cmd('frame', float(HIT_TO + 1)), cmd('remove_all_hitboxes')]
    return start, hold


def gfx(name, graphic, bone, x, y, z, size_=1.0, rot=(0.0, 0.0, 0.0), terminate=1):
    if name == 'external_graphic':
        return cmd(name, graphic, bone, x, y, z, rot[0], rot[1], rot[2], size_, terminate)
    return cmd(name, graphic, bone, x, y, z, rot[0], rot[1], rot[2], size_, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, terminate)


def effect_scripts(ring_y):
    """the collapse: Smash's dust where XV2 plays the stage's (frame 1), the revive ring at his hips from 30 (bone 0:
    up only, unturned: facing-safe; its rings turned to face the side camera in the ptcl, a symmetric ring); the
    wake-up: the ring ended at its first frame (XV2: off at 93; the MSC kills it too, at the wake-up and the status's
    end)"""
    ring = FX_IDS['ring']
    start = [cmd('frame', 1.0), gfx('graphic_effect', FX_DUST, 0, 0.0, 0.0, 0.0, 1.0),
             cmd('frame', float(RING_AT)), gfx('external_graphic', ring, 0, 0.0, float(ring_y), RING_Z, FD_FX_SCALE)]
    hold = [cmd('terminate_graphic_effect', ring, 1, 0)]
    return start, hold


def sound_scripts():
    """XV2's two skill SE at their frames (no voice: the user's rule)"""
    return ([cmd('frame', float(SND_FAKEDOWN_AT)), cmd('sound_effect', SE_IDS['fd_fakedown'])],
            [cmd('frame', float(SND_WAKEUP_AT)), cmd('sound_effect', SE_IDS['fd_wakeup'])])


def expression_scripts():
    return [], [cmd('frame', float(HIT_FROM)), cmd('rumble', 0x10, 0)]


def scripts(body_dir, ring_y):
    makers = {'game': game_scripts(), 'effect': effect_scripts(ring_y), 'sound': sound_scripts(),
              'expression': expression_scripts()}
    hold_crc, air_crc = acmd.crc('speciallwhold'), acmd.crc('specialairlwhold')
    for part, (start, hold) in makers.items():
        path = os.path.join(body_dir, part + '.bin')
        f = acmd.ACMDFile.load(path)
        # vanilla's specialairlwhold sound / expression JUMP into speciallwhold (and that expression JUMPs to itself:
        # its rumble loop): the air F.L.U.D.D. hold gets its own copy of them first, the JUMPs aimed at itself, so
        # replacing speciallwhold doesn't reach it
        air = f.script('specialairlwhold')
        if air is not None and any(acmd.INFO[c.ident]['name'] == 'JUMP' and c.params == [hold_crc] for c in air):
            f.scripts[air_crc] = [acmd.Command(c.ident, [air_crc]) if acmd.INFO[c.ident]['name'] == 'JUMP' and
                                  c.params == [hold_crc] else c for c in f.script('speciallwhold')]
        for name, body in (('speciallwstart', start), ('speciallwhold', hold)):
            # game.bin has none for them (F.L.U.D.D. has no hitboxes): added
            f.scripts[acmd.crc(name)] = body + [acmd.Command(acmd.END)]
        f.save(path)


# ---------------------------------------------------------------- effects (XV2's BTL_CMN effect 26)
def facing_ring(p, d):
    """the revive ring facing-safe: its emitter at the effect's origin but for its height (RING_HEIGHTS); a ring
    (polygon, type 1: drawn in its emitter's XY plane) turned X 90 to lie flat round him (v2, the user: "it should
    surround Supamario horizontally"; v1 turned it Y 90 to face the camera: a flat circle behind him); a flat ring is
    symmetric under the facing's turn, so both facings agree; particles unturned with a full-sphere spread (the God
    Fist's facing_safe)"""
    ty = RING_HEIGHTS.get(p.emitter_name(d), 0.0) / FD_FX_SCALE
    if p.field(d, 'particle_type') == 1:
        p.set_emitter_srt(d, tuple(p.field(d, 'emitter_scale')), (math.pi / 2, 0.0, 0.0), (0.0, ty, 0.0))
    else:
        p.set_emitter_srt(d, tuple(p.field(d, 'emitter_scale')), (0.0, 0.0, 0.0), (0.0, ty, 0.0))
        if p.field(d, 'dispersion_angle') > 0 or p.field(d, 'emitter_velocity') or p.field(d, 'figure_velocity'):
            p.set_field(d, 'dispersion_angle', 180.0)


def convert_fx(cmn_dir, fx_dir, out_dir, halo=True):
    """the ring into his bank (fx_dir: effect/supamario, changed in place); its glowing emitters' halos (the shared
    HALO_ALPHA); FX_IDS['ring']"""
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
    with tempfile.TemporaryDirectory() as pkg:
        for fn in os.listdir(cmn_dir):              # BTL_CMN.eepk alone (vfx/cmn holds five), as the God Fist's
            if not fn.lower().endswith('.eepk') or fn == 'BTL_CMN.eepk':
                os.symlink(os.path.abspath(os.path.join(cmn_dir, fn)), os.path.join(pkg, fn))
        mats = FX.material_table(xv2vfx.load_package(pkg, strict=False)).get(RING_EMP, {})
        old = xv2_to_ptcl.TEX_MAX
        xv2_to_ptcl.TEX_MAX = 128
        try:
            made, log = xv2_to_ptcl.convert_package(p, pkg, 'PtcSupamarioFd', unit=FX.UNIT, emps=[RING_EMP],
                                                    strict=False)
        finally:
            xv2_to_ptcl.TEX_MAX = old
    assert len(made) == 1, made
    si, name, chunk = made[0]
    notes = []
    for em, (_b, en, n) in zip(p.sets[si]['emitters'], chunk):
        d = em['data']
        if d is None:
            continue
        notes.append('%s: %s; %s' % (en, FX.hdr_emitter(p, d, mats.get(en)), '; '.join(n)))
        facing_ring(p, d)
    idx = e.add(si + 1)
    FX_IDS['ring'] = 0x03410000 | idx
    assert FX_IDS['ring'] == FX_RING, ('FX_RING is out of date', hex(FX_IDS['ring']))
    halos = {}
    if halo:
        glow = {si: [k for k, em in enumerate(p.sets[si]['emitters']) if em['data'] is not None and
                     p.field(em['data'], 'alpha_init') > 0 and (mats.get(p.emitter_name(em['data'])) or (0, 0, {}))[2]
                     .get('Glare') and not FX.is_refraction(mats[p.emitter_name(em['data'])][1],
                                                            mats[p.emitter_name(em['data'])][0])]}
        glow = {k: v for k, v in glow.items() if v}
        comp = FX.add_halos(p, e, glow, FX.HALO_ALPHA, {})
        assert not comp, 'the ring needs a companion halo set: its calls / kills would need it too'
        halos = {'glowing': sum(len(v) for v in glow.values()), 'alpha': FX.HALO_ALPHA}
    out = p.build()
    assert ptcl.Ptcl(out).validate() == []
    open(os.path.join(fx_dir, base + '.ptcl'), 'wb').write(out)
    open(os.path.join(fx_dir, base + '.efc'), 'wb').write(e.build())
    rep = {'set': name, 'set_index': si, 'efc': idx, 'id': '0x%08X' % FX_IDS['ring'], 'skipped': log, 'notes': notes,
           'halos': halos, 'ptcl_bytes': [before, len(out)]}
    return rep, p


# ---------------------------------------------------------------- the sound bank
def sound_bank(fdir, out_dir, wav_dir):
    """FD_SE into his bank (Core Breaker's build's) and the soundlabeltable: the God Fist's sound_bank, these tones"""
    import supamario_godfist_build as GB
    table = os.path.join(out_dir, 'sound', 'config', 'soundlabeltable.bin')
    old_se, old_ids = dict(GB.CMN_SE), dict(GB.SE_IDS)
    try:
        GB.CMN_SE.clear()
        GB.CMN_SE.update(FD_SE)
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


# ---------------------------------------------------------------- previews
def preview(out_png, p, rep, outs, bones, ring_y):
    """the ring at its frame and size over his lying pose, and the hitboxes over the wake-up's hit frames (bone 0
    offsets, his travel to that frame), facing right and left: a side view (screen x = his facing's axis)"""
    from PIL import Image, ImageDraw
    import omo
    size_px, span = 360, 44.0
    sc = size_px / span
    tiles = []
    vw_acc = [0.0]
    for v in VW:
        vw_acc.append(vw_acc[-1] + v)
    rows = [('ring (lying, start f%d), x%.2f' % (RING_AT, FD_FX_SCALE), anim.START, RING_AT, 0.0),
            ('hit f%d (both hitboxes)' % HIT_FROM, anim.HOLD, HIT_FROM, vw_acc[HIT_FROM]),
            ('hit f%d' % HIT_TO, anim.HOLD, HIT_TO, vw_acc[HIT_TO])]
    for label, m, f, travel in rows:
        o = outs[('main', m)]
        w = omo.world(o, bones, f)
        for face in (1.0, -1.0):
            im = Image.new('RGB', (size_px, size_px + 18), (18, 18, 24))
            d = ImageDraw.Draw(im)
            fy = size_px * 0.8

            def pt(z, y):
                return size_px / 2 + face * (z + travel) * sc - (0 if face > 0 else 0), fy - y * sc
            d.line([(0, fy), (size_px, fy)], fill=(90, 90, 90), width=2)
            for n, par, _h in bones:
                if par < 0 or par >= len(bones) or any(k in n for k in anim.SKIP) or n in ('ThrowN', 'RotN', 'HipN'):
                    continue
                a = pt(w[bones[par][0]][2][3], w[bones[par][0]][1][3])
                b = pt(w[n][2][3], w[n][1][3])
                d.line([a, b], fill=(230, 230, 230), width=3)
            if m == anim.START:
                for em in p.sets[rep['set_index']]['emitters']:
                    dd = em['data']
                    if dd is None:
                        continue
                    ty = p.field(dd, 'emitter_translation')[1] * FD_FX_SCALE
                    rgb = [c * p.field(dd, 'color_scale') for c in p.color_keys(dd, 0)[0][:3]]
                    col = tuple(int(255 * c / max(max(rgb), 1e-6)) for c in rgb)     # the hue (drawn past 1: bloom)
                    r = max(p.field(dd, 'scale')) * FD_FX_SCALE * RING_DRAWN
                    cx, cy = pt(RING_Z, ring_y + ty)
                    if p.field(dd, 'particle_type') == 1:        # flat: seen from the side camera (~10 degrees up)
                        d.ellipse([cx - r * sc, cy - 0.17 * r * sc, cx + r * sc, cy + 0.17 * r * sc], outline=col,
                                  width=2)
                    else:
                        d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=col)
            else:
                for col in ((255, 80, 80), (80, 160, 255)):
                    cx, cy = pt(HIT_Z, HIT_Y)
                    r = HIT_SIZE * sc
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=2)
            d.text((4, size_px + 2), '%s, facing %s' % (label, 'right' if face > 0 else 'left'), fill=(230, 230, 120))
            tiles.append(im)
    sh = Image.new('RGB', (size_px * 2, (size_px + 18) * len(rows)))
    for i, t in enumerate(tiles):
        sh.paste(t, ((i % 2) * size_px, (i // 2) * (size_px + 18)))
    sh.save(out_png)


# ---------------------------------------------------------------- build
def build(sm_dir, out_dir, fd_skill, fd_se_wav, cb_args, png=None, halo=True):
    import omo
    import supamario_corebreaker_build as CB
    import supamario_godfist_build as GB
    fdir = CB.build(sm_dir, out_dir, cb_args['skill'], cb_args['se_wav'], cb_args['gf'], cb_args.get('png'), halo)
    # the motions over Core Breaker's pacs
    mo = os.path.join(fdir, 'motion', 'body')
    vbn = os.path.join(sm_dir, 'model', 'body', 'c00', 'model.vbn')
    outs, bones, info = anim.build(mo, vbn, os.path.join(fd_skill, '116_YMC_DIE.ean'), mo)
    roots = {m: info['info'][m]['root_z'] for m in anim.MOTIONS}
    vc = [roots[anim.START][f + 1] - roots[anim.START][f] for f in range(LIE_FROM - 1)]
    vw = [roots[anim.HOLD][f + 1] - roots[anim.HOLD][f] for f in range(WAKE_FRAMES - 1)]
    assert all(abs(a - b) < 0.01 for a, b in zip(vc, VC + [0.0] * 10)), 'VC is out of date'
    assert all(abs(a - b) < 0.01 for a, b in zip(vw, VW_ANIM)), 'VW_ANIM is out of date'
    trans = [h for n, _p, h in bones if n == 'TransN'][0]
    for m in anim.MOTIONS:
        o = outs[('main', m)]
        assert all(max(abs(v) for v in o.sample(trans, f)[0]) < 1e-6 for f in range(o.frames)), 'TransN moves'
    js = {m: anim.joints(info['frames'][m], info['smash']) for m in anim.MOTIONS}
    ring_y = RING_Y
    with open(os.path.join(out_dir, 'fakedeath_frames.json'), 'w') as fh:
        json.dump({'segments': [{'name': n, 'motion': s[1], 'start': a0, 'end': b0 - 1, 'src': [s[3], s[4]]}
                                for m in anim.MOTIONS for n, a0, b0, s in anim.timeline(m)],
                   'root_z': roots, 'joints': js, 'ring_y': ring_y}, fh)
    if png:
        anim.sheet(outs, bones, png, roots)
    # the effects, the scripts, the sounds, the MSC
    fx_rep, p = convert_fx(os.path.join(cb_args['gf']['cmn_vfx']), os.path.join(fdir, 'effect', 'supamario'), out_dir,
                           halo)
    os.makedirs(os.path.join(out_dir, 'preview'), exist_ok=True)
    preview(os.path.join(out_dir, 'preview', 'fakedeath_fx_hitboxes.png'), p, fx_rep, outs, omo.vbn_read(vbn), ring_y)
    with open(os.path.join(out_dir, 'fakedeath_fx.json'), 'w') as fh:
        json.dump(dict(fx_rep, ring_y=ring_y, size=FD_FX_SCALE), fh, indent=1)
    scripts(os.path.join(fdir, 'script', 'animcmd', 'body'), ring_y)
    sound_bank(fdir, out_dir, fd_se_wav)
    GB.msc(os.path.join(fdir, 'script', 'msc', 'supamario.mscsb'))
    return fdir


def main():
    a = sys.argv[1:]
    opts = {}
    halo = '--no-halo' not in a
    if not halo:
        a.remove('--no-halo')
    for k in ('--fd-skill', '--fd-se-wav', '--skill', '--se-wav', '--ean', '--cmn-vfx', '--skill-vfx', '--cmn-se',
              '--stb', '--png', '--cb-png'):
        if k in a:
            i = a.index(k)
            opts[k] = a[i + 1]
            del a[i:i + 2]
    need = ('--fd-skill', '--fd-se-wav', '--skill', '--se-wav', '--ean', '--cmn-vfx')
    if len(a) != 2 or any(k not in opts for k in need):
        sys.exit(__doc__)
    gf = {'ean': opts['--ean'], 'cmn_vfx': opts['--cmn-vfx'], 'skill_vfx': opts.get('--skill-vfx'),
          'cmn_se': opts.get('--cmn-se'), 'stb': opts.get('--stb')}
    cb = {'skill': opts['--skill'], 'se_wav': opts['--se-wav'], 'gf': gf, 'png': opts.get('--cb-png')}
    print(build(a[0], a[1], opts['--fd-skill'], opts['--fd-se-wav'], cb, opts.get('--png'), halo))
    print('sounds: ' + ', '.join('%s 0x%08X' % kv for kv in SE_IDS.items()))
    print('ring: 0x%08X' % FX_IDS['ring'])
    for pct in (0, 50, 100, 150):
        kb = knockback(AIR_HIT, pct)
        print('air hit at %d%%: knockback %.1f, travel %.1f, hitstun %d' % ((pct, kb) + flight(kb)))


if __name__ == '__main__':
    main()
