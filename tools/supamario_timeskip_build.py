#!/usr/bin/env python3
"""Supamario's Time Skip (the SIDE special, status 0x153 on the ground and in the air; Dragon Ball Xenoverse 2's Super
skill 1352_HIK_DSH, Hit's "Time-Skip"; the user also calls it "Jump Spike"): the package, built over Sledgehammer's
(tools/supamario_sledgehammer_build.py, which runs Fake Death's, Core Breaker's and the Super God Fist's first; their
files stay theirs: only the side special's motions / scripts, one new effect set, seven new tones and the MSC change).

  python3 -I tools/supamario_timeskip_build.py SUPAMARIO_DIR OUT_DIR --ts-skill 1352_HIK_DSH_DIR --ts-se-wav WAV_DIR
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
CHARGE = 40                         # ChargeTime 40: held this long -> BacEntryCharge 2 (the long dash)
HIT_FROM = int(real0(54))           # 29: the connect box BAC 54-83 (skill BDM #0: no damage, type 10)
HIT_LAST = int(real0(82))           # 57: its last active frame
MOVE_FROM = int(real0(56))          # 31: Movement 56-85 (entry 2: 56-135)
MOVE_N, MOVE_N_CH = 85 - 56, 135 - 56          # 29 / 79 movement frames
MOVE_V = round(0.7 * SCALE, 4)      # 3.528 units a frame (XV2: 0.7 m a frame forward)
MOVE_DRAG = round(0.003 * SCALE, 5)  # 0.01512 less each frame (XV2's drag 0.003)
LOOP_FROM = int(real0(60))          # 35: entry 2 replays the dash pose (EAN 60-85) twice: motion 35-59, from 60 back
LOOP_AT = int(real0(85))            # 60
LOOP_LEN = LOOP_AT - LOOP_FROM      # 25
DASH_END = int(real0(120))          # 95: the stop's last frame (entry 0 ends at 120)
HAZURE_K = MOVE_N                   # Hazure (skill SE 2) at BAC 86: the frame after the movement (the MSC)
HIT_LATE = 3.0                      # the MSC still looks for the hit 3 frames after a box's last frame
# entry 4 (the user on connect): SpecialAirS 1:1
STRIKE = 16                         # BAC 16: Damage 140 (the victim's entry 5 function 0x2), TimeScale 16-22 x0.1
CONNECT_END = 80                    # entry 4's last frame
SND = {'basa': 6, 'dash': MOVE_FROM, 'timestop': 0, 'punch': 8, 'away': None}
# the victim's entry 6 plays CMN cue 64 CharaAway_HKT at its frame 16: entry 5's 51 frames (16 + 4 at x0.1 + 31) =
# 87 real frames, + 16 = 103 after the connect, 47 after the launch (entry 5's BAC 20 = real 56): the connect motion's
# STRIKE + 47 (its freeze over, the motion runs 1:1 again)
AWAY_AFTER = 103 - 56
SND['away'] = STRIKE + AWAY_AFTER   # 63

# ---------------------------------------------------------------- the boxes (XV2's places; the user's earlier rules)
HIT_Z, HIT_Y, HIT_SIZE = round(1.0 * SCALE, 2), round(0.5 * SCALE, 2), round(0.5 * SCALE, 2)   # b_C_Base + (0, 0.5,
                                    # -1.0 m), 0.5 m: 5.04 ahead, 2.52 up, 2.52
CATCH = dict(Damage=2.0, Angle=0, KBG=0, FKB=0, BKB=1)        # a catch: knockback 1 (Fake Death's grounded hit: no
                                    # launch), the MSC holds it; XV2's box does no damage (the 140 is the strike's)
CATCH_FREEZE = 3
HOLD_X, HOLD_Y = round(1.5 * SCALE, 2), round(0.1 * SCALE, 2)  # ThrowHandler: 1.5 m in front of g_x_LND, 0.1 m up
VICTIM_MID, VICTIM_HEAD = 5.0, 9.0
VICTIM_R2 = (HIT_SIZE + 12.0) ** 2
# the strike: 14% (with the catch's 2: 16%; XV2's 140 is the charged Sledgehammer's 145 (20%) level: 19% at its
# ratio; God Fist 4 + 11, Core Breaker 26, Fake Death 6, Sledgehammer 8 / 20), angle 10 (XV2's blow-away: (0, 0.025,
# 0.43) m a frame, ~3 degrees; 10 keeps a grounded victim off the floor), BKB 60 / KBG 75: Mario weight, no DI,
# knockback 85 at 0% (~64 units away: XV2's 13.3 m x 5.04 = 67 of entry 5's blow), 127 at 50%, 169 at 100%, 211 at 150%
STRIKE_HIT = dict(Damage=14.0, Angle=10, KBG=75, FKB=0, BKB=60)
STRIKE_FREEZE = 30                  # XV2's time lock: the victim at x0.1 for 40 real frames, the user 60
STRIKE_SIZE = round(1.0 * SCALE, 2)
STRIKE_Z, STRIKE_Y = HOLD_X, round(HOLD_Y + VICTIM_MID, 2)
INV_STEP = 2.0
TURN_STICK, TURN_WINDOW = 0.5, 4    # the B-reverse (Sledgehammer's)
ST_SIDE = 0x153

# ---------------------------------------------------------------- variables (VAR_22-27: Sledgehammer uses VAR_0-21)
V_PH, V_CHG, V_SLOT, V_K, V_USED, V_BREV = (0x0F000316 + i for i in range(6))

# ---------------------------------------------------------------- effects / sounds
FX_SCALE = 1.75                     # xv2_smash_fx.SIZE (the God Fist's settled size over XV2's)
HIT_EMPS = ['Btl_HitL.emp']         # BTL_CMN effect 2 (skill BDM #1's Effect1): Btl_HitLOD x1.5 (Sledgehammer's set),
                                    # Btl_HitL x0.8 (new) and x0.05 (a dot: left out), Btl_Sweat00 x2.0 on the head
                                    # (Sledgehammer's set), its CBIND (no Smash equivalent)
EEPK_SCALE = {'Btl_HitLOD.emp': 1.5, 'Btl_HitL.emp': 0.8, 'Btl_Sweat00.emp': 2.0}
FX_IDS = {'hitl': 0x0341005F, 'hitl_2': 0x03410060}   # Btl_HitL has more than 16 emitters: the
                                    # converter splits it in two sets (both played together)
SH_FX = {'hitlod': 0x0341005C, 'sweat': 0x0341005E}
FX_DUST = 0x1000009                 # Smash's dash cloud: XV2's Stage BG 60 at BAC 56 (the stage's own, not in the files)
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
    return {'TS_VROOT_CODE': FD.vel_code(root_speed), 'TS_V_PH': '0x%X' % V_PH, 'TS_V_CHG': '0x%X' % V_CHG,
            'TS_V_SLOT': '0x%X' % V_SLOT, 'TS_V_K': '0x%X' % V_K, 'TS_V_USED': '0x%X' % V_USED,
            'TS_V_BREV': '0x%X' % V_BREV, 'TS_ST_SIDE': fl(ST_SIDE), 'TS_TURN_STICK': fl(TURN_STICK),
            'TS_TURN_WINDOW': fl(TURN_WINDOW), 'TS_CHARGE': fl(CHARGE), 'TS_WIND_END': fl(WIND_END),
            'TS_VICTIM_R2': fl(VICTIM_R2), 'TS_HIT_Z': fl(HIT_Z), 'TS_HIT_Y': fl(HIT_Y), 'TS_VICTIM_MID': fl(VICTIM_MID),
            'TS_VICTIM_HEAD': fl(VICTIM_HEAD), 'TS_HOLD_X': fl(HOLD_X), 'TS_HOLD_Y': fl(HOLD_Y),
            'TS_INV_STEP': fl(INV_STEP), 'TS_FX_HITLOD': '0x%X' % SH_FX['hitlod'], 'TS_FX_HITL': '0x%X' % FX_IDS['hitl'],
            'TS_FX_SWEAT': '0x%X' % SH_FX['sweat'], 'TS_FX_HITL_2': '0x%X' % FX_IDS['hitl_2'],
            'TS_FX_HITLOD_SIZE': fl(round(EEPK_SCALE['Btl_HitLOD.emp'] * FX_SCALE, 4)),
            'TS_FX_HITL_SIZE': fl(round(EEPK_SCALE['Btl_HitL.emp'] * FX_SCALE, 4)),
            'TS_FX_SWEAT_SIZE': fl(round(EEPK_SCALE['Btl_Sweat00.emp'] * FX_SCALE, 4)),
            'TS_SND_HIT': '0x%X' % SE_IDS['ts_hit'], 'TS_SND_HAZURE': '0x%X' % SE_IDS['ts_hazure'],
            'TS_MOVE_N': fl(MOVE_N), 'TS_MOVE_N_CH': fl(MOVE_N_CH), 'TS_LOOP_AT': fl(LOOP_AT),
            'TS_LOOP_LEN': fl(LOOP_LEN), 'TS_LOOP_FROM': fl(LOOP_FROM), 'TS_HIT_FROM': fl(HIT_FROM),
            'TS_HIT_LATE': fl(HIT_LATE), 'TS_MOVE_FROM': fl(MOVE_FROM), 'TS_MOVE_V': fl(MOVE_V),
            'TS_MOVE_DRAG': fl(MOVE_DRAG), 'TS_STRIKE': fl(STRIKE), 'TS_CONNECT_END': fl(CONNECT_END),
            'TS_DASH_END': fl(DASH_END)}


def knockback(hit, pct):
    import supamario_fakedeath_build as FD
    return FD.knockback(hit, pct)


def travel(charged=False, root=None):
    """his travel over the dash (units): the root's plus XV2's Movement"""
    n = MOVE_N_CH if charged else MOVE_N
    mv = sum(MOVE_V - MOVE_DRAG * k for k in range(n))
    return round(mv + (sum(root) if root else 0.0), 1)


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


def catch_box():
    """the connect box (ID 0, Part 0): XV2's place and size, 2%, knockback 1, no clank (Clang 0: a grab-like box never
    loses a clank), shieldable, hits fighters lying down (Ground/Air 3), Smash's own small spark"""
    return hitbox(ID=0, Part=0, Size=HIT_SIZE, Y=HIT_Y, Z=HIT_Z, SDI=0.0, Clang=0, Rebound=0, NoGFX=0, SFXLevel=0,
                  SFXType=1, HitstopFrames=CATCH_FREEZE, SelfHitstopFrames=CATCH_FREEZE, **CATCH)


def strike_box():
    """the strike (ID 0, Part 1: its own hit record, the catch's Part 0 record on the victim stays): on the held
    victim's middle, the time lock's freeze both sides, no SDI, NoGFX (XV2's hit look from the MSC), Clang 0"""
    return hitbox(ID=0, Part=1, Size=STRIKE_SIZE, Y=STRIKE_Y, Z=STRIKE_Z, SDI=0.0, Clang=0, Rebound=0, NoGFX=1,
                  SFXLevel=2, SFXType=1, HitstopFrames=STRIKE_FREEZE, SelfHitstopFrames=STRIKE_FREEZE, **STRIKE_HIT)


DASHING, CHARGING = 2.5, 1.5        # TS_V_PH > 2.5: the dash; < 1.5: the wind-up


def game_scripts():
    """specials: the connect box at HIT_FROM only in the dash (the script's clock runs on while the charge holds the
    pose; the MSC restarts the motion at WIND_END after a held charge, and removes the box: AttackModule 0x2719);
    specialairs: the strike at STRIKE, off 2 frames later"""
    dash = [cmd('frame', float(HIT_FROM))] + if_(V_PH, 5, DASHING, [catch_box()])
    connect = [cmd('frame', float(STRIKE)), cmd('hit_log_clear', 1), strike_box(),
               cmd('frame', float(STRIKE + 2)), cmd('remove_all_hitboxes')]
    return dash, connect


def effect_scripts():
    """XV2's Stage BG 60 (the stage's dust, at the dash's start BAC 56) as Smash's dash cloud on the ground. The skill's
    own effects (EEPK effects 0 at BAC 0 and 11 at the strike) and BTL_CMN 108 (HIT_DmgGrs2, a model on the camera
    0-16 of the connect) aren't there / can't be: none; the strike's hit look is the MSC's"""
    dash = [cmd('frame', float(MOVE_FROM))] + if_(0x0F000116, 0, 0, if_(V_PH, 5, DASHING, [
        cmd('graphic_effect', FX_DUST, 0, 0.0, 0.0, -2.0, 0.0, 0.0, 0.0, 1.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1)]))
    return dash, []


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
def convert_fx(cmn_dir, fx_dir, halo=True):
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
    out = p.build()
    assert ptcl.Ptcl(out).validate() == []
    open(os.path.join(fx_dir, base + '.ptcl'), 'wb').write(out)
    open(os.path.join(fx_dir, base + '.efc'), 'wb').write(e.build())
    bad = FX.facing_emitters(p, [s['set_index'] for s in sets.values()])
    return {'sets': sets, 'skipped': log, 'notes': notes, 'halos': halos, 'ptcl_bytes': [before, len(out)],
            'facing_problems': bad}


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
def build(sm_dir, out_dir, ts_skill, ts_se_wav, sh_args, png=None, halo=True):
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
    speed = info['info'][anim.DASH]['root_speed']
    ref = os.path.join(HERE, '..', 'reference', 'xv2', 'timeskip_root.json')
    want = {'source': '1352_HIK_DSH.ean #0 b_C_Base Z, SpecialS frames (tools/supamario_timeskip_anim.py root_speed): '
                      'the MSC\'s ts_vroot', 'speed': speed}
    if not os.path.exists(ref) or json.load(open(ref)) != want:
        with open(ref, 'w') as fh:
            json.dump(want, fh)
    js = {m: anim.joints(info['frames'][m], info['smash']) for m in anim.MOTIONS}
    doc = {'dash_frames': anim.frames_of(anim.DASH), 'connect_frames': anim.frames_of(anim.CONNECT),
           'hit': [HIT_FROM, HIT_LAST], 'move': [MOVE_FROM, MOVE_N, MOVE_N_CH, MOVE_V, MOVE_DRAG],
           'loop': [LOOP_FROM, LOOP_AT], 'strike': STRIKE, 'travel': [travel(False, speed), travel(True, speed)],
           'root_speed': speed, 'joints': js, 'info': {m: {k: v for k, v in info['info'][m].items()}
                                                         for m in anim.MOTIONS}}
    os.makedirs(os.path.join(out_dir, 'preview'), exist_ok=True)
    hb = {anim.DASH: {f: (HIT_Z, HIT_Y, HIT_SIZE) for f in (HIT_FROM, 40, HIT_LAST)},
          anim.CONNECT: {STRIKE: (STRIKE_Z, STRIKE_Y, STRIKE_SIZE)}}
    anim.sheet(outs, bones, png or os.path.join(out_dir, 'preview', 'timeskip_anim.png'),
               {m: info['info'][m]['root_z'] for m in anim.MOTIONS}, hitboxes=hb)
    rep = convert_fx(sh_args['fd']['cb']['gf']['cmn_vfx'], os.path.join(fdir, 'effect', 'supamario'), halo)
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
    keys = ('--ts-skill', '--ts-se-wav', '--sh-skill', '--sh-se-wav', '--fd-skill', '--fd-se-wav', '--skill', '--se-wav',
            '--ean', '--cmn-vfx', '--skill-vfx', '--cmn-se', '--stb', '--png')
    for k in keys:
        if k in a:
            i = a.index(k)
            opts[k] = a[i + 1]
            del a[i:i + 2]
    if len(a) != 2 or any(k not in opts for k in keys[:10]):
        sys.exit(__doc__)
    gf = {'ean': opts['--ean'], 'cmn_vfx': opts['--cmn-vfx'], 'skill_vfx': opts.get('--skill-vfx'),
          'cmn_se': opts.get('--cmn-se'), 'stb': opts.get('--stb')}
    cb = {'skill': opts['--skill'], 'se_wav': opts['--se-wav'], 'gf': gf}
    fd = {'fd_skill': opts['--fd-skill'], 'fd_se_wav': opts['--fd-se-wav'], 'cb': cb}
    sh = {'sh_skill': opts['--sh-skill'], 'sh_se_wav': opts['--sh-se-wav'], 'fd': fd}
    print(build(a[0], a[1], opts['--ts-skill'], opts['--ts-se-wav'], sh, opts.get('--png'), halo))
    print('sounds: ' + ', '.join('%s 0x%08X' % kv for kv in SE_IDS.items()))
    print('effects: ' + ', '.join('%s 0x%08X' % kv for kv in FX_IDS.items()))
    for pct in (0, 50, 100, 150):
        import supamario_fakedeath_build as FD
        kb = knockback(STRIKE_HIT, pct + CATCH['Damage'])
        print('at %d%% (+ the catch): strike knockback %.1f, hitstun %d, ~%.0f units away' % (
            pct, kb, int(kb * 0.4), FD.flight(kb, STRIKE_HIT['Angle'])[0]))


if __name__ == '__main__':
    main()
