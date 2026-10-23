#!/usr/bin/env python3
"""Supamario's Kamehameha effects from Dragon Ball Xenoverse 2's 000_GOK_KMH package, played from
his taunts as an in-game test (before the move exists).

  python3 tools/supamario_kame_build.py PKG_DIR SUPAMARIO_V4 SUPAMARIO_V5 OUT_DIR [--diag | --diag2]

PKG_DIR: the extracted .vfxpackage. SUPAMARIO_V4 / _V5: the fighter/supamario folders of the v4 and
v5 packages (v4's ptcl is the base; v5 has the .efc entry 0x16 and the scripts). Writes
OUT_DIR/fighter/supamario/effect/supamario/ (.ptcl, .efc, model/EffSupamarioKame*) and
OUT_DIR/fighter/supamario/script/animcmd/body/effect.bin + sound.bin.

- .ptcl: v4's + PtcSupamarioKameCharge (tools/supamario_kame_fx.py, set 19: keeps v5's entry
  0x16) + the EMPs (tools/xv2_to_ptcl.py: PtcSupamarioKmh*, one set each, 4ptcl in two);
- effect models: the three EMOs (tools/xv2_to_nud.py: EffSupamarioKameFire / Bas / Hand);
- .efc: one entry per new set and per model (ids 0x0341nnnn, printed);
- taunts, timed as the XV2 effects (EEPK parts, their start frames and scales):
  up taunt (180 frames): the charge at the hand (EEPK effects 0 and 15): Crg x0.4 + tsubu at 0,
  Crg x0.6 + CrgON x0.8 at 42, Crg x1.0 + CrgON x1.2 at 78, Crg again at 118 and 158;
  the charge sound;
  side taunt: the release at the hand (effect 1), at frame 0: the Fire model + Ring x0.8; the fire sound;
  down taunt: the beam head (effect 3) in front of him: Bas model x1.6, Fireptcl x1.6, Wav x1.8,
  4ptcl x1.6, LineAll, Hand model x0.45; the beam-head sound.
  All with Terminate = 1 (they end with the taunt; the beam parts loop until then, and the down
  taunt also stops its parts with Terminate_Graphic_Effect at frame 96). The beam-head parts are
  turned 180 degrees (HEAD_YROT); the models get MODEL_OPTS. The taunts'
  own effect scripts (the up taunt's colour flashes) are replaced; their sound scripts keep their
  sounds, with ours at frame 0.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import efc  # noqa: E402
import ptcl  # noqa: E402
import supamario_kame_fx  # noqa: E402
import xv2_to_ptcl  # noqa: E402

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
SIDE = [(0, MODEL_PREFIX + 'Fire', HAND, None, 1.0), (0, 'PtcSupamarioKmhRing', HAND, None, 0.8)]
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
        if bone == 0:
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


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--diag')]
    if len(args) != 4:
        sys.exit(__doc__)
    pkg, v4, v5, out = args
    taunts = DIAG2 if '--diag2' in sys.argv else DIAG if '--diag' in sys.argv else TAUNTS
    fx = os.path.join(out, 'fighter/supamario/effect/supamario')
    body = os.path.join(out, 'fighter/supamario/script/animcmd/body')
    shutil.rmtree(os.path.join(out, 'fighter'), ignore_errors=True)
    os.makedirs(os.path.join(fx, 'model'))
    os.makedirs(body)
    base = 'effect/supamario/supamario.010d0000'

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
    for m in ('Fire', 'Bas', 'Hand'):
        assert os.path.exists(os.path.join(fx, 'model', MODEL_PREFIX + m, 'model.nud')), m
    for m in os.listdir(os.path.join(v5, 'effect/supamario/model')):
        shutil.copytree(os.path.join(v5, 'effect/supamario/model', m), os.path.join(fx, 'model', m))

    # effect list
    e = efc.Efc(open(os.path.join(v5, base + '.efc'), 'rb').read())
    assert len(e.entries) == 0x17 and e.entries[0x16][1] == 20, 'not v5\'s .efc'
    ids = {}
    for si, name, _chunk in made:
        assert q.set_name(si) == name
        ids[name] = e.add(si + 1)
    for m in ('Fire', 'Bas', 'Hand'):
        ids[MODEL_PREFIX + m] = e.add(0, MODEL_PREFIX + m)
    open(os.path.join(fx, 'supamario.010d0000.efc'), 'wb').write(e.build())

    # taunts
    eff = acmd.ACMDFile.load(os.path.join(v5, 'script/animcmd/body/effect.bin'))
    snd = acmd.ACMDFile.load(os.path.join(v5, 'script/animcmd/body/sound.bin'))
    for anim, (parts, sound, end) in taunts.items():
        for side in 'RL':
            name = anim + side
            eff.scripts[acmd.crc(name)] = taunt_script(parts, ids, end) + [
                acmd.Command(acmd.END)]
            s = [c for c in (snd.script(name) or []) if c.ident not in (acmd.BY_NAME['sound_effect'], acmd.END)
                 or (c.ident == acmd.BY_NAME['sound_effect'] and c.params[0] not in (SND_CHARGE, SND_FIRE, SND_HEAD))]
            snd.scripts[acmd.crc(name)] = [cmd('sound_effect', sound)] + s + [acmd.Command(acmd.END)]
    eff.save(os.path.join(body, 'effect.bin'))
    snd.save(os.path.join(body, 'sound.bin'))

    for si, name, chunk in made:
        print('0x%08X  %-26s set %d, %d emitters' % ((BANK << 16) | ids[name], name, si, len(chunk)))
    for m in ('Fire', 'Bas', 'Hand'):
        print('0x%08X  %s (model)' % ((BANK << 16) | ids[MODEL_PREFIX + m], MODEL_PREFIX + m))
    for line in log:
        print(line)


if __name__ == '__main__':
    main()
