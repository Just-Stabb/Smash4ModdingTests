#!/usr/bin/env python3
"""Supamario's Kamehameha (neutral special) from Dragon Ball Xenoverse 2's 000_GOK_KMH package.

  python3 tools/supamario_kame_build.py PKG_DIR SUPAMARIO_V4 SUPAMARIO_V5 OUT_DIR [--rpx IN.rpx]
                                        [--taunts [--diag | --diag2]]

PKG_DIR: the extracted .vfxpackage. SUPAMARIO_V4 / _V5: the fighter/supamario folders of the v4 and
v5 packages (v4's ptcl is the base; v5 has the .efc entry 0x16, the scripts and the fireball's
files). Writes under OUT_DIR/fighter/supamario/:
- effect/supamario/: .ptcl = v4's + PtcSupamarioKameCharge (tools/supamario_kame_fx.py, set 19:
  keeps v5's entry 0x16) + the EMPs (tools/xv2_to_ptcl.py: PtcSupamarioKmh*, one set each, 4ptcl in
  two); effect models: the three EMOs (tools/xv2_to_nud.py: EffSupamarioKameFire / Bas / Hand), the
  three beam bodies (the ETR traces, tools/xv2_trace_to_nud.py: EffSupamarioKameBeam / 2 / 3, the
  taunt test's) and the projectile's body pieces (EffSupamarioKameSeg1 / 2 / 3, one per charge
  level: Segment, KAME_SPEED x SEG_EVERY long); .efc: one entry per new set and model (0x0341nnnn);
- the move: script/msc/supamario.mscsb from fighters/supamario/supamario.c (status 0x152: hold to
  charge, release fires; KAME_* replaced), script/animcmd/body/{game,effect,sound}.bin with
  SpecialN / SpecialAirN rewritten (no fireball: no GENERATE_ARTICLE, the XV2 release at the hand
  at frame 14, the charge / fire sounds);
- the projectile, article 5 (weapon kind 0x18B "kamehameha", tools/weapon_expand.py; copy of the
  fireball): model/kamehameha/c00 (the fireball's, nothing drawn: nud.hidden), motion/kamehameha/
  (the fireball's main.pac), script/msc/kamehameha/kamehameha.mscsb (fighters/supamario/weapons/
  kamehameha.c), script/animcmd/weapon/kamehameha/ (motion.mtable fly1 / fly2 / fly3 / finish1 / 2 / 3:
  the multi-hits, the head effects per level (EEPK effects 3 / 4 / 5), the finishing launchers);
- with --rpx: OUT_DIR/code/cross_f.rpx = IN.rpx + tools/weapon_expand.py (the 0x18B kind with
  its own hit method: a hit holds the beam instead of removing it);
- with --taunts: the earlier taunt test too (up: charge, side: release + beam body, down: head).
"""
import os
import shutil
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import efc  # noqa: E402
import nud  # noqa: E402
import ptcl  # noqa: E402
import supamario_kame_fx  # noqa: E402
import xv2_trace_to_nud  # noqa: E402
import xv2_to_ptcl  # noqa: E402
import xv2vfx  # noqa: E402

UNIT = xv2_to_ptcl.UNIT
BANK = 0x0341
HAND = 0x11                       # the bone Mario's fireball throw uses (SpecialN)
FRONT = (0.0, 7.0, 14.0)          # the beam head: bone 0 (Top), 7 up, 14 in front
# the XV2 parts at TRS face their -Z (test 1, 2026-10-23: with +Z forward the head did not point the
# way Supamario faces): turned 180 degrees about Y, so their z offsets change sign too
HEAD_YROT = 180.0
DOWN_END = 96                     # the down taunt (100 frames) ends its looping parts here
# model conversion options (tools/xv2_to_nud.py): --plain 1 everywhere (only the material settings
# the game's effect models use); Kmh_Hand without its subtractive 'hand' mesh. Test 1 crashed on the
# second down taunt with the model renderer's skinned-vertex buffer overflowing (Cemu log:
# GX2RSetAttributeBuffer offset exceeds buffer size, from NU::DeviceWiiU)
# Test 2: the head read too white without the dark layer: the glow and the core tinted blue
MODEL_OPTS = {'Kmh_Fire': ['--plain', '1'], 'Kmh_Bas': ['--plain', '1', '--tint', 'Cor=0.7,0.9,1.0'],
              'Kmh_Hand': ['--plain', '1', '--skip', 'hand', '--tint', 'cor=0.45,0.75,1.0']}
SND_CHARGE, SND_FIRE, SND_HEAD = 0x0CB1008B, 0x0CB1008C, 0x0CB1008D
MODEL_PREFIX = 'EffSupamarioKame'

# (frame, effect, bone, (x, y, z) offset, scale); effect = set name or model folder
UP = [(0, 'PtcSupamarioKmhCrg', HAND, None, 0.4), (0, 'PtcSupamarioKmhtsubu', HAND, None, 1.0),
      (42, 'PtcSupamarioKmhCrg', HAND, None, 0.6), (42, 'PtcSupamarioKmhCrgON', HAND, None, 0.8),
      (78, 'PtcSupamarioKmhCrg', HAND, None, 1.0), (78, 'PtcSupamarioKmhCrgON', HAND, None, 1.2),
      (118, 'PtcSupamarioKmhCrg', HAND, None, 1.0), (158, 'PtcSupamarioKmhCrg', HAND, None, 1.0)]
# the beam body (the ETR traces as models, tools/xv2_trace_to_nud.py): bone 0, from BODY_POS
# forward (its models are built along +Z, not turned); BODY marks it in the part lists
BODY, BODY_POS = -1, (0.0, 7.0, 3.0)
TRACES = ('Beam', 'Beam2', 'Beam3')         # the three charge levels (EEPK effects 3 / 4 / 5)
# test 7: the body's white core ribbon (trace node 0, beam00) read too solid: mostly transparent
TRACE_ALPHA = {0: 0.3}
# ... and the white cloud of the tubes' textures (T2_UV01) too: near-white texels mostly transparent
TRACE_WHITE_FADE = 0.85
# test 8: "brightened a bit" (1.3, test 9: right) and "much faster"; test 9: "slightly slower" and
# "about double the length": grows at 5 units a frame to 4 units per XV2 extrude frame
# (240 / 320 / 400 units: 48 / 64 / 80 frames); the move's projectile flies at TRACE_SPEED too
TRACE_GAIN, TRACE_SPEED, TRACE_LENGTH_RATE = 1.3, 5.0, 4.0
SIDE = [(0, MODEL_PREFIX + 'Fire', HAND, None, 1.0), (0, 'PtcSupamarioKmhRing', HAND, None, 0.8),
        (0, MODEL_PREFIX + 'Beam', BODY, None, 1.0)]
DOWN = [(0, MODEL_PREFIX + 'Bas', 0, (0, 0, 0), 1.6), (0, 'PtcSupamarioKmhFireptcl', 0, (0, 0, -0.3), 1.6),
        (0, 'PtcSupamarioKmhWav', 0, (0, 0, 0), 1.8), (0, 'PtcSupamarioKmh4ptcl', 0, (0, 0, -0.15), 1.6),
        (0, 'PtcSupamarioKmh4ptcl_2', 0, (0, 0, -0.15), 1.6), (0, 'PtcSupamarioKmhLineAll', 0, (0, 0, 0), 1.0),
        (0, MODEL_PREFIX + 'Hand', 0, (0, 0, -0.3), 0.45)]
# taunt -> (parts, sound, frame to terminate them or None)
TAUNTS = {'AppealHi': (UP, SND_CHARGE, None), 'AppealS': (SIDE, SND_FIRE, None),
          'AppealLw': (DOWN, SND_HEAD, DOWN_END)}
# --diag2 (test 4): test 3 crashed with the down taunt's particles (not the models); the
# converter now keeps emitters inside the vanilla ranges (xv2_to_ptcl.sanitize). The down taunt
# plays the whole beam head again; the up / side taunts its particle sets in two halves
HEAD_SETS = [p for p in DOWN if not p[1].startswith(MODEL_PREFIX)]
DIAG2 = {'AppealHi': ([p for p in HEAD_SETS if p[1].endswith(('Fireptcl', 'Wav'))], SND_HEAD, 176),
         'AppealS': ([p for p in HEAD_SETS if not p[1].endswith(('Fireptcl', 'Wav'))], SND_HEAD, DOWN_END),
         'AppealLw': (DOWN, SND_HEAD, DOWN_END)}
# --diag (test 3): test 2 still crashed some time after a down taunt (one is enough; the side
# taunt, with the Fire model, never): the down taunt's pieces one per taunt, to find the one
DIAG = {'AppealHi': ([p for p in DOWN if p[1] == MODEL_PREFIX + 'Bas'], SND_HEAD, 176),
        'AppealS': ([p for p in DOWN if p[1] == MODEL_PREFIX + 'Hand'], SND_HEAD, DOWN_END),
        'AppealLw': ([p for p in DOWN if not p[1].startswith(MODEL_PREFIX)], SND_HEAD, DOWN_END)}



# ---- the projectile (charge levels 1 / 2 / 3): each a little faster (user, 2026-10-23); lengths as
# the taunt test's body (240 / 320 / 400 units: TRACE_LENGTH_RATE x ExtrudeDuration)
KAME_SPEED = (5.0, 5.5, 6.0)
KAME_LENGTH = (240.0, 320.0, 400.0)
KAME_LIFE = tuple(int(round(l / v)) for l, v in zip(KAME_LENGTH, KAME_SPEED))   # 48 / 58 / 67 frames
SEG_EVERY = 2                     # a body piece every 2 frames, KAME_SPEED x 2 long
KAME_HOLD = 30                    # frames the beam holds on what it hit (multi-hitting)
KAME_FINISH = 12                  # the finish status: the launcher, then removed
# body pieces stay at full width this long (the longest beam: fly + hold + finish), then fade
SEG_HOLD = max(KAME_LIFE) + KAME_HOLD + KAME_FINISH + 8
SEG_TEX_BASE = 0x15141A60         # after the traces' 0x15141A30-0x15141A5F
ARTICLE = 5                       # Supamario's article list: fireball .. dokan, kamehameha
WEAPON_BONE = 0x7D0               # the fireball's own following effects use this bone
MOTIONS = ('fly1', 'fly2', 'fly3', 'finish1', 'finish2', 'finish3')   # weapon_expand "motions": 6
# hitboxes: head (ID 0) and body capsule (ID 1, from the head back to the spawn point) multi-hit
# every REHIT frames while flying and holding; the finish (Part 1: its own hit log) launches
REHIT = 5
HEAD_SIZE = (4.5, 5.5, 6.5)
BODY_SIZE = (3.5, 4.0, 4.5)
TICK_DAMAGE = (1.0, 1.3, 1.6)
FINISH = [dict(Damage=6.0, KBG=85, BKB=50, Size=7.0), dict(Damage=8.0, KBG=90, BKB=55, Size=8.0),
          dict(Damage=10.0, KBG=95, BKB=60, Size=9.0)]
FINISH_FRAMES = 3
# the charge (fighter MSC): Mario's throw frozen at HOLD_FRAME; level 2 at 42, 3 at 78 charge
# frames (the XV2 charge effect's steps), fires by itself at 100; the beam comes out at FIRE_FRAME
N_HOLD_FRAME, N_FIRE_FRAME, N_LV2, N_LV3, N_FULL = 10.0, 14.0, 42, 78, 100


def cmd(name, *params):
    return acmd.Command(acmd.BY_NAME[name], list(params))


def taunt_script(parts, ids, end=None):
    """External_Graphic per part at its frame (XV2 offsets are units x UNIT, in front for bone 0,
    turned HEAD_YROT); with end, Terminate_Graphic_Effect for every part at that frame"""
    out, frame = [], 0
    for f, name, bone, off, size in sorted(parts, key=lambda x: x[0]):
        if f > frame:
            out.append(cmd('frame', float(f)))
            frame = f
        yrot = 0.0
        if bone == BODY:
            bone, (x, y, z) = 0, BODY_POS
        elif bone == 0:
            off = off or (0, 0, 0)
            x, y = FRONT[0] + off[0] * UNIT, FRONT[1] + off[1] * UNIT
            z = FRONT[2] + (-off[2] if HEAD_YROT == 180.0 else off[2]) * UNIT
            yrot = HEAD_YROT
        else:
            x = y = z = 0.0
        out.append(cmd('external_graphic', (BANK << 16) | ids[name], bone, float(x), float(y), float(z),
                       0.0, float(yrot), 0.0, float(size), 1))
    if end is not None:
        out.append(cmd('frame', float(end)))
        for name in dict.fromkeys(p[1] for p in parts):
            out.append(cmd('terminate_graphic_effect', (BANK << 16) | ids[name], 1, 1))
    return out


def hitbox(name, **kw):
    """a hitbox command from its parameter names (acmd_info syntax), the rest defaulted"""
    d = dict(ID=0, Part=0, Bone=0, Damage=1.0, Angle=0x16E, KBG=100, FKB=30, BKB=0, Size=1.0, X=0.0, Y=0.0,
             Z=0.0, Effect=0, Trip=0, Hitlag=0.5, SDI=0.5, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=1,
             SFXType=1, **{'Ground/Air': 3, 'Direct/Indirect': 0}, Type=0, HitBits=0x3F, Unk41=0,
             CollisionPart=0xF, NoScale=0, Shieldable=1, Reflectable=1, Absorbable=1, Rehit=0, IgnoreInvuln=0,
             HitAllStates=0, FacingRestrict=1, NoGrabRelease=0, TeamDamage=0, DisableHitlag=0, NoGFX=0,
             Flinchless=0, Shape=0, X2=0.0, Y2=0.0, Z2=0.0)
    d.update(kw)
    ident = acmd.BY_NAME[name.lower()]
    return acmd.Command(ident, [d[n] for n in acmd.INFO[ident]['syntax']])


def head_parts(pkg):
    """per charge level (EEPK effects with IndexNum 3 / 4 / 5): [(effect name, (x, y, z), scale)] of
    the head (models and particle sets; 4ptcl's second half with it)"""
    import xv2vfx
    eepk = pkg['eepk']
    names = {}
    for c in eepk['AssetContainers']:
        for ai, a in enumerate(c.get('Assets', [])):
            f = a.get('Files') or []
            if f:
                names[(f[0].rsplit('.', 1)[1].upper(), ai)] = f[0].rsplit('.', 1)[0]
    out = []
    for idx in (3, 4, 5):
        eff = [e for e in eepk['Effects'] if e['IndexNum'] == idx][0]
        parts = []
        for p in eff['EffectParts']:
            if p['AssetType'] == 'EMO':
                n = MODEL_PREFIX + names[('EMO', p['AssetIndex'])].split('_', 1)[1]
            elif p['AssetType'] == 'PBIND':
                n = 'PtcSupamario' + names[('EMP', p['AssetIndex'])].replace('_', '')
            else:
                continue
            parts.append((n, tuple(p['Position']), p['ScaleMin']))
            if n.endswith('4ptcl'):
                parts.append((n + '_2', tuple(p['Position']), p['ScaleMin']))
        out.append(parts)
    return out


def weapon_scripts(heads, ids):
    """the kamehameha's game / effect / sound scripts and motion.mtable"""
    eid = lambda n: (BANK << 16) | ids[n]   # noqa: E731
    game, effect, sound = {}, {}, {}
    for lv in range(3):
        name = MOTIONS[lv]
        tick = dict(Damage=TICK_DAMAGE[lv], Rehit=REHIT)
        g = [hitbox('Special_Hitbox', ID=0, Size=HEAD_SIZE[lv], **tick)]
        for f in range(4, KAME_LIFE[lv] + 1, 4):        # the body capsule grows with the flight
            g.append(cmd('frame', float(f)))
            g.append(hitbox('Extended_Special_Hitbox', ID=1, Size=BODY_SIZE[lv], Z2=-KAME_SPEED[lv] * f, **tick))
        game[name] = g
        e = []
        for n, (x, y, z), size in heads[lv]:
            e.append(cmd('external_graphic', eid(n), WEAPON_BONE, float(x * UNIT), float(y * UNIT),
                         float((-z if HEAD_YROT == 180.0 else z) * UNIT), 0.0, HEAD_YROT, 0.0, float(size), 1))
        effect[name] = e
        sound[name] = [cmd('sound_effect', SND_HEAD)]
    for lv in range(3):
        f = FINISH[lv]
        name = MOTIONS[3 + lv]
        game[name] = [cmd('remove_all_hitboxes'),
                      hitbox('Special_Hitbox', ID=0, Part=1, Damage=f['Damage'], Angle=40, KBG=f['KBG'], FKB=0,
                             BKB=f['BKB'], Size=f['Size'], Hitlag=1.5, SDI=1.0, SFXLevel=2),
                      cmd('frame', float(FINISH_FRAMES)), cmd('remove_all_hitboxes')]
        scale = (1.0, 1.25, 1.5)[lv]
        effect[name] = [cmd('external_graphic', eid(n), WEAPON_BONE, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, size * scale, 0)
                        for n, size in ((MODEL_PREFIX + 'Fire', 1.5), ('PtcSupamarioKmhRing', 1.5),
                                        ('PtcSupamarioKmhWav', 2.3))]
        sound[name] = [cmd('sound_effect', SND_FIRE)]
    files = {}
    for fn, sc in (('game', game), ('effect', effect), ('sound', sound)):
        f = acmd.ACMDFile({acmd.crc(n): v + [acmd.Command(acmd.END)] for n, v in sc.items()})
        files[fn] = f
    mtable = b''.join(struct.pack('>I', acmd.crc(n)) for n in MOTIONS)
    return files, mtable


def special_scripts(v5, ids):
    """SpecialN / SpecialAirN: the fireball's throw without the fireball and its fire; the release
    (Fire model + Ring) at the hand at frame 14; the charge sound from the start, the fire sound at
    the release (stopping the charge's)"""
    eid = lambda n: (BANK << 16) | ids[n]   # noqa: E731
    body = os.path.join(v5, 'script/animcmd/body')
    out = {}
    for fn in ('game', 'effect', 'sound'):
        out[fn] = acmd.ACMDFile.load(os.path.join(body, fn + '.bin'))
    release = [cmd('external_graphic', eid(MODEL_PREFIX + 'Fire'), HAND, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0),
               cmd('external_graphic', eid('PtcSupamarioKmhRing'), HAND, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.8, 0)]
    g = out['game'].script('SpecialN')
    assert [c.name for c in g] == ['Set_Frame_Duration', 'FRAME', 'GENERATE_ARTICLE', 'END'] or \
        acmd.BY_NAME['generate_article'] in [c.ident for c in g], 'not v5\'s SpecialN'
    out['game'].scripts[acmd.crc('SpecialN')] = [c for c in g if c.ident != acmd.BY_NAME['generate_article']
                                                and c.ident != acmd.BY_NAME['frame']]
    for anim, ground in (('SpecialN', True), ('SpecialAirN', False)):
        e = []
        if ground:      # the throw's dust
            e += [c for c in out['effect'].script(anim) if c.ident == acmd.BY_NAME['graphic_effect3']][:1]
        e += [cmd('frame', N_FIRE_FRAME)] + release
        out['effect'].scripts[acmd.crc(anim)] = e + [acmd.Command(acmd.END)]
    out['sound'].scripts[acmd.crc('SpecialN')] = [
        cmd('sound_effect', SND_CHARGE), cmd('frame', N_FIRE_FRAME - 1), cmd('stop_sound_effect', SND_CHARGE),
        cmd('sound_effect', SND_FIRE), acmd.Command(acmd.END)]
    return out


def substitute(path, values):
    s = open(path).read()
    for k in sorted(values, key=len, reverse=True):
        s = s.replace(k, values[k])
    code = '\n'.join(line.split('//')[0] for line in s.split('\n'))
    left = [w for w in code.split() if 'KAME_' in w]
    assert not left, left[:5]
    return s


def compile_msc(src_text, out_path, tmp):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    c = os.path.join(tmp, os.path.basename(out_path) + '.c')
    open(c, 'w').write(src_text)
    subprocess.run([sys.executable, os.path.join(HERE, 'msclang/msclang.py'), '-x', os.path.join(HERE, 'mscinfo.xml'),
                    c, '-o', out_path], check=True, capture_output=True)
    assert os.path.getsize(out_path) > 0


def fl(v):
    return '%sf' % repr(float(v))


def main():
    argv = sys.argv[1:]
    rpx_in = None
    if '--rpx' in argv:
        rpx_in = argv[argv.index('--rpx') + 1]
        del argv[argv.index('--rpx'):argv.index('--rpx') + 2]
    args = [a for a in argv if not a.startswith('--')]
    if len(args) != 4:
        sys.exit(__doc__)
    pkg, v4, v5, out = args
    with_taunts = '--taunts' in argv
    taunts = DIAG2 if '--diag2' in argv else DIAG if '--diag' in argv else TAUNTS
    sup = os.path.join(out, 'fighter/supamario')
    fx = os.path.join(sup, 'effect/supamario')
    body = os.path.join(sup, 'script/animcmd/body')
    shutil.rmtree(os.path.join(out, 'fighter'), ignore_errors=True)
    os.makedirs(os.path.join(fx, 'model'))
    os.makedirs(body)
    base = 'effect/supamario/supamario.010d0000'
    tmp = os.path.join(out, '_tmp')
    os.makedirs(tmp, exist_ok=True)

    # particles
    p, _si = supamario_kame_fx.build(open(os.path.join(v4, base + '.ptcl'), 'rb').read())
    assert _si == 19, _si
    made, log = xv2_to_ptcl.convert_package(p, pkg)
    data = p.build()
    q = ptcl.Ptcl(data)
    assert q.validate() == [], q.validate()
    open(os.path.join(fx, 'supamario.010d0000.ptcl'), 'wb').write(data)

    # models
    for name, opts in MODEL_OPTS.items():
        subprocess.run([sys.executable, os.path.join(HERE, 'xv2_to_nud.py'), pkg, name, os.path.join(fx, 'model'),
                        '--prefix', MODEL_PREFIX] + opts, check=True, capture_output=True)
    xv2_trace_to_nud.convert(pkg, os.path.join(fx, 'model'), MODEL_PREFIX, alpha=TRACE_ALPHA,
                             white_fade=TRACE_WHITE_FADE, speed=TRACE_SPEED, length_rate=TRACE_LENGTH_RATE,
                             gain=TRACE_GAIN)
    segs = []
    for lv, trace in enumerate(TRACES):
        folder = MODEL_PREFIX + 'Seg%d' % (lv + 1)
        xv2_trace_to_nud.segment(pkg, 'Kmh_%s.etr' % trace, os.path.join(fx, 'model'), folder,
                                 KAME_SPEED[lv] * SEG_EVERY, KAME_SPEED[lv], SEG_HOLD,
                                 tex_base=SEG_TEX_BASE + 0x10 * lv, alpha=TRACE_ALPHA,
                                 white_fade=TRACE_WHITE_FADE, gain=TRACE_GAIN)
        segs.append(folder)
    models = [MODEL_PREFIX + m for m in ('Fire', 'Bas', 'Hand') + TRACES] + segs
    for m in models:
        assert os.path.exists(os.path.join(fx, 'model', m, 'model.nud')), m
    for m in os.listdir(os.path.join(v5, 'effect/supamario/model')):
        shutil.copytree(os.path.join(v5, 'effect/supamario/model', m), os.path.join(fx, 'model', m))

    # effect list
    e = efc.Efc(open(os.path.join(v5, base + '.efc'), 'rb').read())
    assert len(e.entries) == 0x17 and e.entries[0x16][1] == 20, 'not v5\'s .efc'
    ids = {}
    for si, name, _chunk in made:
        assert q.set_name(si) == name
        ids[name] = e.add(si + 1)
    for m in models:
        ids[m] = e.add(0, m)
    open(os.path.join(fx, 'supamario.010d0000.efc'), 'wb').write(e.build())
    eid = lambda n: '0x%08X' % ((BANK << 16) | ids[n])   # noqa: E731

    # the move: fighter scripts and MSC
    sp = special_scripts(v5, ids)
    if with_taunts:
        for anim, (parts, sound, end) in taunts.items():
            for side in 'RL':
                name = anim + side
                sp['effect'].scripts[acmd.crc(name)] = taunt_script(parts, ids, end) + [acmd.Command(acmd.END)]
                s = [c for c in (sp['sound'].script(name) or [])
                     if c.ident not in (acmd.BY_NAME['sound_effect'], acmd.END)
                     or (c.ident == acmd.BY_NAME['sound_effect'] and c.params[0] not in (SND_CHARGE, SND_FIRE, SND_HEAD))]
                sp['sound'].scripts[acmd.crc(name)] = [cmd('sound_effect', sound)] + s + [acmd.Command(acmd.END)]
    for fn, f in sp.items():
        f.save(os.path.join(body, fn + '.bin'))
    compile_msc(substitute(os.path.join(HERE, '..', 'fighters/supamario/supamario.c'), {
        'KAME_N_HOLD_FRAME': fl(N_HOLD_FRAME), 'KAME_N_FIRE_FRAME': fl(N_FIRE_FRAME), 'KAME_N_LV2': str(N_LV2),
        'KAME_N_LV3': str(N_LV3), 'KAME_N_FULL': str(N_FULL), 'KAME_ARTICLE': str(ARTICLE),
        'KAME_HAND': '0x%X' % HAND, 'KAME_FX_CRGON': eid('PtcSupamarioKmhCrgON'),
        'KAME_FX_CRG': eid('PtcSupamarioKmhCrg'), 'KAME_FX_TSUBU': eid('PtcSupamarioKmhtsubu')}),
        os.path.join(sup, 'script/msc/supamario.mscsb'), tmp)

    # the projectile
    src = os.path.join(v5, 'model/fireball/c00')
    dst = os.path.join(sup, 'model/kamehameha/c00')
    shutil.copytree(src, dst)
    open(os.path.join(dst, 'model.nud'), 'wb').write(nud.hidden(os.path.join(src, 'model.nud')))
    os.makedirs(os.path.join(sup, 'motion/kamehameha'))
    shutil.copy(os.path.join(v5, 'motion/fireball/main.pac'), os.path.join(sup, 'motion/kamehameha/main.pac'))
    vals = {'KAME_SEG_EVERY': str(SEG_EVERY), 'KAME_HOLD': str(KAME_HOLD), 'KAME_FINISH': str(KAME_FINISH)}
    for lv in range(3):
        vals['KAME_SPEED_%d' % (lv + 1)] = fl(KAME_SPEED[lv])
        vals['KAME_LIFE_%d' % (lv + 1)] = str(KAME_LIFE[lv])
        vals['KAME_SEG_%d' % (lv + 1)] = eid(segs[lv])
    compile_msc(substitute(os.path.join(HERE, '..', 'fighters/supamario/weapons/kamehameha.c'), vals),
                os.path.join(sup, 'script/msc/kamehameha/kamehameha.mscsb'), tmp)
    wdir = os.path.join(sup, 'script/animcmd/weapon/kamehameha')
    os.makedirs(wdir)
    pkgd = xv2vfx.load_package(pkg)
    files, mtable = weapon_scripts(head_parts(pkgd), ids)
    for fn, f in files.items():
        f.save(os.path.join(wdir, fn + '.bin'))
    open(os.path.join(wdir, 'motion.mtable'), 'wb').write(mtable)

    # the executable
    if rpx_in:
        import weapon_expand
        B, _info = weapon_expand.build()
        os.makedirs(os.path.join(out, 'code'), exist_ok=True)
        subprocess.run([sys.executable, os.path.join(HERE, 'rpx_patch.py'), rpx_in,
                        os.path.join(out, 'code/cross_f.rpx')] + weapon_expand.args(B), check=True,
                       capture_output=True)
    shutil.rmtree(tmp)

    for si, name, chunk in made:
        print('0x%08X  %-26s set %d, %d emitters' % ((BANK << 16) | ids[name], name, si, len(chunk)))
    for m in models:
        print('0x%08X  %s (model)' % ((BANK << 16) | ids[m], m))
    print('kamehameha: speed %s, life %s frames, a %s-unit body piece every %d frames' % (
        KAME_SPEED, KAME_LIFE, tuple(v * SEG_EVERY for v in KAME_SPEED), SEG_EVERY))
    for line in log:
        print(line)


if __name__ == '__main__':
    main()
