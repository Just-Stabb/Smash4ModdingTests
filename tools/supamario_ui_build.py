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
import supamario_ui_anim as anim  # noqa: E402
import supamario_ui_cave as cave  # noqa: E402

# ---------------------------------------------------------------- the rules (the user's spec)
TRIGGER_PCT = 100.0                  # his first actionable frame at 100% or more
FORM_N = anim.frames_of(anim.FORM)   # 60: the transformation (XV2 entry 0's 0-229, the user's "about 60 frames")
STRIKE_N = anim.frames_of(anim.STRIKE)
STRIKE_AT = anim.frame_of(anim.STRIKE, 1, 280)     # XV2's finisher (BDM #2) at entry 5's 280
STRIKE_SAFE = STRIKE_AT + 3          # intangible to the strike's last active frame + 1 (XV2: invulnerable to the end)
# XV2's counter (1510_GKS_MGT_PLAYER.bcm: the stance's children #2 / #3, PrimaryActivatorConditions CounterMelee, NOT
# CounterProjectile, linked through BAC entry 0's BcmCallback "Counters / Supers" 30-152 -> BAC entries 5 / 6): its
# window is entry 0's 30-151 (motion frames CW_ON-CW_OFF); BAC 5 at 151: BDM #0 (damage type 18, 0 damage, 150-frame
# hold: the attacker frozen) in a 3 m sphere, invulnerable, the vanish (BTL_CMN 82, CMN SE 96), Movement to the target
# (flags 0x80) and 2 frames at 2.5 m, the finisher at 280: BDM #2 (type 7, a launch, hitstop 7 / 7), damage 10.
# Damage: XV2's 10 taken as 10% (XV2's numbers are its own scale: Fake Death's 20 / Core Breaker's 405 were the user's
# own % in Smash; open to the user); the launch's angle / knockback (not in XV2's units): angle 35, BKB 80, KBG 75
CW_ON = anim.frame_of(anim.FORM, 0, 30)
CW_OFF = anim.frame_of(anim.FORM, 0, 151)
STRIKE_DMG = 10.0
FREEZE_SIZE = round(3.0 * 5.04, 2)   # BDM #0's 3 m sphere
STRIKE_HIT = dict(Angle=35, KBG=75, FKB=0, BKB=80)
STRIKE_SIZE, STRIKE_Y, STRIKE_Z = 6.0, 7.0, 7.0
GAP = 9.0                            # beside the fighter to answer: this far on his side of it
GROUND_DY = 6.0                      # its feet within this of his: on the ground, the X only
DODGE_N = anim.frames_of(anim.DODGE)  # 16
DODGE_INV = 12                       # the user: invincible ~12 frames, then actionable
DODGE_MOVE, DODGE_V = 8, 2.0         # a sidestep of 16 units away, over the first 8 frames (energy 3)
AURA_EVERY = 30.0                    # the aura made again every 30 frames
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
V_SS = 0x0F000324                    # TIMER_4: Secret Sensation's mark
BONES = {'TransN': 0, 'HipN': 2, 'LFootJ': 5, 'RFootJ': 9, 'BustN': 12, 'HeadN': 22, 'LHandN': 16, 'RHandN': 20}
V_AURA = 0x0F000323                  # TIMER_3: the aura's renewal

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
      ('vanish', 'BTL_CMN.eepk', 'SKI_line.emp', 'HipN', (0.0, 0.0, 0.0), 1.0)]
FX_IDS = {}                          # key -> the ACMD / MSC id (0x0341xxxx), filled by effects()
FX_DEFAULT = 0x1000009               # before the build has made them (the earlier builds compile the MSC too)
METRE = 5.04

# ---------------------------------------------------------------- sounds
UI_SE = {'ui_start': ('CAR_BTL_M1510_MGT_00_Start_F22', 0.0),     # skill SE cue 0: entry 0 at 22
         'ui_success': ('CAR_BTL_M1510_MGT_01_Success', 0.0),     # skill SE cue 1: entry 0 at 205
         'ui_vanish': ('Vanish', 0.0)}                             # CAR_BTL_CMN cue 96: entry 1 at 151
SE_IDS = {}
SND_START = anim.frame_of(anim.FORM, 0, 22)
SND_SUCCESS = anim.frame_of(anim.FORM, 0, 205)
FX_START_AT = anim.frame_of(anim.FORM, 0, 10)
FX_AURA_AT = anim.frame_of(anim.FORM, 0, 40)
FX_BURST_AT = anim.frame_of(anim.FORM, 0, 220)


def fl(v):
    return '%sf' % repr(float(v))


def fx_id(key):
    return FX_IDS.get(key, FX_DEFAULT)


def msc_values():
    """the UI_* names in fighters/supamario/supamario.c"""
    v = {'UI_ST_DODGE_F': fl(ST_DODGE), 'UI_ST_DODGE': '0x%X' % ST_DODGE, 'UI_ST_F': fl(ST_UI), 'UI_ST': '0x%X' % ST_UI,
         'UI_ST_DEAD': fl(0xB1), 'UI_ST_REBIRTH': fl(0xB2), 'UI_ST_ENTRY': fl(0x14F),
         'UI_V_FORM': '0x%X' % cave.V_FORM, 'UI_V_DODGE_R': '0x%X' % cave.V_DODGE_R,
         'UI_V_DODGE_L': '0x%X' % cave.V_DODGE_L, 'UI_V_AURA': '0x%X' % V_AURA,
         'UI_FORMING': fl(1000.0), 'UI_FORMED': fl(2000.0), 'UI_TRIGGER_PCT': fl(TRIGGER_PCT),
         'UI_CW_ON': fl(CW_ON), 'UI_CW_OFF': fl(CW_OFF), 'UI_GAP': fl(GAP),
         'UI_GROUND_DY': fl(GROUND_DY), 'UI_FORM_N': fl(FORM_N), 'UI_STRIKE_N': fl(STRIKE_N),
         'UI_STRIKE_SAFE': fl(STRIKE_SAFE), 'UI_DODGE_N': fl(DODGE_N), 'UI_DODGE_INV': fl(DODGE_INV),
         'UI_DODGE_MOVE': fl(DODGE_MOVE), 'UI_DODGE_V': fl(DODGE_V), 'UI_AURA_EVERY': fl(AURA_EVERY),
         'UI_MOT_FORM': '0x%X' % MOT_FORM, 'UI_MOT_STRIKE': '0x%X' % MOT_STRIKE, 'UI_MOT_DODGE': '0x%X' % MOT_DODGE,
         'UI_FX_AURA1': '0x%X' % fx_id('aura_hip'), 'UI_FX_AURA2': '0x%X' % fx_id('aura_head'),
         'UI_FX_AURA3': '0x%X' % fx_id('aura_foot'), 'UI_FX_VANISH': '0x%X' % fx_id('vanish'),
         'UI_BONE_HIP': '0x%X' % BONES['HipN'], 'UI_BONE_HEAD': '0x%X' % BONES['HeadN'],
         'UI_BONE_LFOOT': '0x%X' % BONES['LFootJ'], 'UI_BONE_RFOOT': '0x%X' % BONES['RFootJ'],
         'UI_HEAD_UP': fl(round(0.2 * METRE, 3)), 'UI_AURA_SIZE': fl(SCALE), 'UI_FOOT_SIZE': fl(round(0.8 * SCALE, 3)),
         'UI_VANISH_SIZE': fl(SCALE), 'UI_SND_VANISH': '0x%X' % se_id('ui_vanish'),
         'UI_SS_MOT': '0x%X' % MOT_SS, 'UI_SS_SLIDE_MOT': '0x%X' % MOT_ESCAPE_N, 'UI_SS_ON': fl(SS_ON),
         'UI_SS_OFF': fl(SS_OFF), 'UI_SS_END': fl(SS_END), 'UI_SS_SLIDE_N': fl(SS_SLIDE_N), 'UI_SS_DEPTH': fl(SS_DEPTH),
         'UI_SS_BEHIND_AIR': fl(SS_BEHIND_AIR), 'UI_SS_BEHIND': fl(SS_BEHIND), 'UI_SS_UP_GROUND': fl(SS_UP_GROUND),
         'UI_SS_UP_AIR': fl(SS_UP_AIR), 'UI_V_SS': '0x%X' % V_SS}
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
    """XV2's finisher (BDM #2): STRIKE_DMG, a launch"""
    import supamario_sledgehammer_build as SB
    return SB.hitbox(ID=0, Part=0, Bone=0, Damage=STRIKE_DMG, Size=STRIKE_SIZE, Y=STRIKE_Y, Z=STRIKE_Z,
                     Hitlag=1.5, SDI=0.5, Clang=0, Rebound=0, SFXLevel=2, SFXType=1, NoGFX=0, **STRIKE_HIT)


def freeze_box():
    """XV2's BDM #0 at the counter's start: no damage, the attacker held (its hitstop to the finisher), Part 1 (the
    finisher's record stays its own)"""
    import supamario_sledgehammer_build as SB
    return SB.hitbox(ID=1, Part=1, Bone=0, Damage=0.0, Angle=0, KBG=0, FKB=0, BKB=0, Size=FREEZE_SIZE, Y=5.0, Z=0.0,
                     Hitlag=0.0, SDI=0.0, Clang=0, Rebound=0, SFXLevel=0, SFXType=0, NoGFX=1, Flinchless=1,
                     HitstopFrames=STRIKE_AT, SelfHitstopFrames=0)


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
    game = {anim.FORM: [], anim.STRIKE: timeline([(0, [freeze_box()]), (1, [cmd('remove_all_hitboxes')]),
                                                  (STRIKE_AT, [strike_box()]),
                                                  (STRIKE_AT + 3, [cmd('remove_all_hitboxes')])]),
            anim.DODGE: [], anim.SS: []}
    effect = {anim.FORM: timeline([(FX_START_AT, [graphic('start')]), (FX_AURA_AT, aura),
                                   (FX_BURST_AT, [graphic('burst', follow=False)])]),
              anim.STRIKE: timeline([(0, [graphic('vanish', follow=False)])]),
              anim.DODGE: timeline([(0, [graphic('vanish', follow=False)])]), anim.SS: []}
    sound = {anim.FORM: timeline([(SND_START, [cmd('sound_effect', se_id('ui_start'))]),
                                  (SND_SUCCESS, [cmd('sound_effect', se_id('ui_success'))])]),
             anim.STRIKE: timeline([(0, [cmd('sound_effect', se_id('ui_vanish'))])]),
             anim.DODGE: timeline([(0, [cmd('sound_effect', se_id('ui_vanish'))])]), anim.SS: []}
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
        f.save(path)


# ---------------------------------------------------------------- effects / sounds
def effects(cmn_dir, fx_dir):
    """FX's EMPs (XV2's vfx/cmn) into his ptcl / efc after every earlier set; FX_IDS their ids"""
    import efc
    import ptcl
    import xv2_to_ptcl
    base = 'supamario.010d0000'
    p = ptcl.Ptcl(open(os.path.join(fx_dir, base + '.ptcl'), 'rb').read())
    e = efc.Efc(open(os.path.join(fx_dir, base + '.efc'), 'rb').read())
    rep = {}
    for eepk in ('BTL_AURA.eepk', 'BTL_CMN.eepk'):
        emps = [x[2] for x in FX if x[1] == eepk]
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
            if ep == eepk:
                FX_IDS[key] = 0x03410000 | by_emp[emp]
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
    outs, _bones, info = anim.build(mo, vbn, os.path.join(ui_skill, '1510_GKS_MGT.ean'), mo)
    rep = effects(ts_args['sh']['fd']['cb']['gf']['cmn_vfx'], os.path.join(fdir, 'effect', 'supamario'))
    sound_bank(fdir, out_dir, ui_se_wav)
    scripts(os.path.join(fdir, 'script', 'animcmd', 'body'))
    GB.msc(os.path.join(fdir, 'script', 'msc', 'supamario.mscsb'))
    doc = {'frames': {m: anim.frames_of(m) for m in anim.MOTIONS}, 'strike_at': STRIKE_AT,
           'counter_window': [CW_ON, CW_OFF],
           'events': {'snd_start': SND_START, 'snd_success': SND_SUCCESS, 'fx_start': FX_START_AT,
                      'fx_aura': FX_AURA_AT, 'fx_burst': FX_BURST_AT},
           'fx_ids': {k: '0x%08X' % v for k, v in FX_IDS.items()}, 'se_ids': {k: '0x%08X' % v for k, v in SE_IDS.items()},
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
            '--png')
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
          'png': opts.get('--png'), 'halo': halo}
    print(build(a[0], a[1], opts['--ui-skill'], opts['--ui-se-wav'], ts))
    print('sounds: ' + ', '.join('%s 0x%08X' % kv for kv in SE_IDS.items()))
    print('effects: ' + ', '.join('%s 0x%08X' % kv for kv in FX_IDS.items()))
    print('transformation %d frames, strike %d (hit at %d), dodge %d (intangible %d)' % (FORM_N, STRIKE_N, STRIKE_AT,
                                                                                         DODGE_N, DODGE_INV))


if __name__ == '__main__':
    # through the module itself: supamario_kame_build's MSC values import supamario_ui_build, whose FX_IDS / SE_IDS
    # must be the ones this run fills (not __main__'s copy)
    import supamario_ui_build
    supamario_ui_build.main()
