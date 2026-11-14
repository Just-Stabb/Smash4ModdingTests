#!/usr/bin/env python3
"""Kirby's Hero copy, v6: Hero's sword-spell scripts (reference/brave_sword_spells_acmd.txt: his built game / effect /
sound scripts for Flame Slash, Kacrackle Slash, Metal Slash, Hatchet Man, slots 0x27A-0x27D / 0x286-0x289) as MSC
calls on Kirby, for fighters/kirby/kirby.c "v6" (khm_sw_game / khm_sw_fx / khm_sw_end / khm_sw_cancel /
khm_sw_window, between the GENERATED markers).

  python3 tools/kirby_hero_sword_msc.py [REFERENCE]          prints the C
  python3 tools/kirby_hero_sword_msc.py --events [REFERENCE]  prints the events (frame, kind, values) as JSON

fighters/kirby/specials.md "v6". What it does with Hero's scripts:
- Timing: each command's motion frame -> frames since the cast (khm_frame), the motion played at the scripts'
  Set_Frame_Duration rates (FT_MOTION_RATE: a frame of the motion takes that many game frames; Flame / Kacrackle
  Slash 0.5 on 1-7 and 0.8 / 0.7 on 12-40): the first frame whose motion frame reaches it. The motions' ends and
  cancel frames (Ultimate's motion_list, brave.zip motion/body/c00: special_lw17 / 18 skill3, 61 frames, cancel 47;
  19 skill1, 61, 40; 20 skill2, 107, 88) the same way.
- Hitboxes: Special_Hitbox / Extra_Special_Hitbox -> AttackModule op 0x272C (the ACMD Extended_Special_Hitbox's own
  path: 0x02C0D210, docs/acmd-params/hitbox.md): FP slots 0-39 as Hero's, then the capsule's end X2 / Y2 / Z2 = the
  centre + 0.01 along Y (a sphere; never a zero-length capsule). IDs + 5 (5-9) and Part 1, so they don't replace
  the stone's own hitboxes (IDs 0-4, Part 0); Remove_All_Hitboxes -> AttackModule(0x2718, id) for those five.
  Extra_Special_Hitbox's extras (Metal Slash: HitstunMul -6, 6 frames more hitstun) have no MSC op: left out.
- Bones: Hero's script bones are his joint ids (model.jtb table 0: 0x16 RArmJ, 0x19 RHaveN = Ultimate's Sword1);
  the sword is on Kirby's LHaveN (0x18, the held model's bone: tools/kirby_copy_sword.py), so a Sword1-frame offset
  (x, y, z) is (0.2023 - y, x, z) there, and an effect on it is turned 90 about Z (its X along the blade, as Hero's);
  0 -> 0. Fix v6 (the swing, tools/kirby_hero_sword_anim.py): LHaveN now moves along Hero's HaveR path, so 0x16
  (Hero's forearm) -> LHaveN too, at ArmR's origin in HaveR's frame at that frame (PATH "arm", the stone has no arm;
  before: Kirby's LArmJ 0x10, still in the stone pose); and with a path scale other than 1 (PATH "scale", the sword
  model rescaled the same) the sword offsets and the sword effects' sizes are scaled by it.
- Effects: External_Graphic (EFFECT_FOLLOW) -> EffectModule 0x2712 (bone-following, as Robin's MSC uses it);
  Graphic_Effect2 / 3 (EFFECT / LANDING_EFFECT) -> 0x2710; Terminate_Graphic_Effect -> 0x2723 (id, kill, kill
  light). Sword_Glow / Terminate_Sword_Glow (the trail) are left out: the stone doesn't swing the sword, so the trail
  would draw nothing.
- Sounds: Sound_Effect -> SoundModule 0x2710, Stop_Sound_Effect -> 0x2714 (Hero's ids: his bank, as v5).
- Ground / air: the air scripts where they differ (Kacrackle Slash and Hatchet Man have no landing dust in the air).
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, '..', 'reference', 'brave_sword_spells_acmd.txt')
PATH = os.path.join(HERE, '..', 'reference', 'kirby_hero_sword_path.json')     # fix v6 (kirby_hero_sword_anim.py)
SPELLS = {'Flame Slash': 0x11, 'Kacrackle Slash': 0x12, 'Metal Slash': 0x13, 'Hatchet Man': 0x14}
# Ultimate's motion_list (brave.zip): motion length (frames), cancel frame
MOTION = {0x11: (61, 47), 0x12: (61, 47), 0x13: (61, 40), 0x14: (107, 88)}
SWORD_BONE, ARM_BONE = 0x19, 0x16
K_SWORD, K_ARM = 0x18, 0x10
SWORD1_TO_HAVE = 0.2023        # Sword1's origin in HaveR's frame (x), tools/kirby_copy_sword.py
ID_SHIFT, PART = 5, 1
EFFECT_ROT_Z = 90.0
# Special_Hitbox's 41 FP parameters, then Extra's six
FP = ['ID', 'Part', 'Bone', 'Damage', 'Angle', 'KBG', 'FKB', 'BKB', 'Size', 'X', 'Y', 'Z', 'Effect', 'Trip', 'Hitlag',
      'SDI', 'Clang', 'Rebound', 'ShieldDamage', 'SFXLevel', 'SFXType', 'Ground/Air', 'Direct/Indirect', 'Type',
      'HitBits', 'Unk41', 'CollisionPart', 'NoScale', 'Shieldable', 'Reflectable', 'Absorbable', 'Rehit',
      'IgnoreInvuln', 'HitAllStates', 'FacingRestrict', 'NoGrabRelease', 'TeamDamage', 'DisableHitlag', 'NoGFX',
      'Flinchless', 'Shape']
FLOATS = {'Damage', 'Size', 'X', 'Y', 'Z', 'Trip', 'Hitlag', 'SDI'}


def num(v):
    v = v.strip()
    return int(v, 16) if v.lower().startswith('0x') else (float(v) if '.' in v or 'e' in v.lower() else int(v))


def parse(path=REF):
    """{(spell, 'ground' / 'air', 'game' / 'effect' / 'sound'): [(motion frame, name, {param: value})]}"""
    out, key, frame = {}, None, 0.0
    for line in open(path):
        line = line.rstrip('\n')
        m = re.match(r'== (.+) (ground|air) slot 0x[0-9A-F]+ (game|effect|sound)$', line)
        if m:
            key, frame = (SPELLS[m.group(1)], m.group(2), m.group(3)), 0.0
            out[key] = []
            continue
        m = re.match(r'\s+(\w+)\((.*)\)$', line)
        if not m or key is None:
            continue
        name = m.group(1)
        args = {}
        for kv in filter(None, (x.strip() for x in m.group(2).split(','))):
            k, v = kv.split('=', 1)
            args[k] = num(v)
        if name == 'FRAME':
            frame = float(args['Frames'])
        else:
            out[key].append((frame, name, args))
    return out


def timing(game):
    """motion frame -> frames since the cast, from the game script's Set_Frame_Duration commands"""
    rates = sorted((f, a['Speed']) for f, n, a in game if n == 'Set_Frame_Duration')

    def at(m):
        mf, g = 0.0, 0
        while mf < m - 1e-6:
            dur = 1.0
            for f, d in rates:
                if f <= mf + 1e-6:
                    dur = d
            mf += 1.0 / dur
            g += 1
        return g
    return at


def load_path(path=PATH):
    """(scale, {spell: [arm offset a cast frame]}) from kirby_hero_sword_anim.py's path.json; (1, None) without it"""
    if not path or not os.path.exists(path):
        return 1.0, None
    p = json.load(open(path))
    return p['scale'], {int(k, 16): v['arm'] for k, v in p['spells'].items()}


SCALE, ARMS = load_path()


def sword_point(x, y, z):
    return tuple(round(v * SCALE, 4) for v in (SWORD1_TO_HAVE - y, x, z))


def fl(v):
    s = ('%.4f' % v).rstrip('0')
    return (s + '0' if s.endswith('.') else s) + 'f'


def events(ref):
    """{spell: {'ground' / 'air': [(f, kind, values)]}, 'end' / 'cancel' / 'hitbox' frames}"""
    out = {}
    for n in sorted(set(k[0] for k in ref)):
        at = timing(ref[(n, 'ground', 'game')])
        e = {'end': at(MOTION[n][0]), 'cancel': at(MOTION[n][1])}
        for sit in ('ground', 'air'):
            ev = []
            for part in ('game', 'effect', 'sound'):
                for mf, name, a in ref[(n, sit, part)]:
                    f = at(mf)
                    if name in ('Special_Hitbox', 'Extra_Special_Hitbox'):
                        vals = [a[k] for k in FP[:40]]
                        bone = a['Bone']
                        x, y, z = a['X'], a['Y'], a['Z']
                        if bone == SWORD_BONE:
                            kb, (x, y, z) = K_SWORD, sword_point(x, y, z)
                        elif bone == ARM_BONE and ARMS is not None:      # fix v6: the forearm at the grip
                            assert (x, y, z) == (0, 0, 0), (n, name, x, y, z)
                            kb, (x, y, z) = K_SWORD, tuple(ARMS[n][min(f, len(ARMS[n]) - 1)])
                        elif bone == ARM_BONE:
                            kb = K_ARM
                        else:
                            assert bone == 0, bone
                            kb = 0
                        vals[0] += ID_SHIFT
                        vals[1] = PART
                        vals[2] = kb
                        vals[9:12] = [x, y, z]
                        vals += [x, y + 0.01, z]
                        ev.append((f, 'hitbox', vals))
                    elif name == 'Remove_All_Hitboxes':
                        ev.append((f, 'remove', []))
                    elif name in ('External_Graphic', 'Graphic_Effect2', 'Graphic_Effect3'):
                        bone = a['Bone']
                        pos = (a['X'], a['Y'], a['Z'])
                        rot = [a['XRot'], a['YRot'], a['ZRot']]
                        size = a['Size']
                        if bone == SWORD_BONE:
                            bone, pos = K_SWORD, sword_point(*pos)
                            rot[2] += EFFECT_ROT_Z
                            size = round(size * SCALE, 4)
                        else:
                            assert bone == 0, bone
                        if name == 'External_Graphic':
                            ev.append((f, 'follow', [a['Graphic'], bone] + list(pos) + rot + [size, a['Terminate']]))
                        else:
                            ev.append((f, 'effect', [a['Graphic'], bone] + list(pos) + rot + [size]
                                       + [a[k] for k in ('RandomX', 'RandomY', 'RandomZ', 'RandomXRot', 'RandomYRot',
                                                         'RandomZRot', 'Terminate')]))
                    elif name == 'Terminate_Graphic_Effect':
                        ev.append((f, 'kill', [a['Graphic'], a['KillParticles'], a['KillImmediately']]))
                    elif name == 'Sound_Effect':
                        ev.append((f, 'sound', [a['SFX']]))
                    elif name == 'Stop_Sound_Effect':
                        ev.append((f, 'stop', [a['SFX']]))
                    elif name in ('Set_Frame_Duration', 'Sword_Glow', 'Terminate_Sword_Glow'):
                        pass
                    else:
                        raise SystemExit('unhandled %s' % name)
            ev.sort(key=lambda x: x[0])         # stable: game, effect, sound at the same frame
            e[sit] = ev
        hb = [f for f, k, _v in e['ground'] if k in ('hitbox', 'remove')]
        e['hitbox'] = (min(hb), max(hb))
        out[n] = e
    return out


def is_float(kind, i):
    """whether value i of an event of this kind is passed as a float"""
    if kind == 'hitbox':
        return i >= 40 or FP[i] in FLOATS
    if kind == 'follow':
        return 2 <= i <= 8
    if kind == 'effect':
        return 2 <= i <= 14
    return False


def call(kind, v):
    if kind == 'hitbox':
        args = [fl(float(x)) if is_float(kind, i) else '0x%x' % x for i, x in enumerate(v)]
        return 'AttackModule(0x272c, %s);' % ', '.join(args)
    if kind == 'remove':
        return 'khm_sw_remove();'
    if kind == 'follow':
        return 'EffectModule(0x2712, 0x%x, 0x%x, %s, 0x%x);' % (v[0], v[1], ', '.join(fl(float(x)) for x in v[2:9]), v[9])
    if kind == 'effect':
        return 'EffectModule(0x2710, 0x%x, 0x%x, %s, 0x%x);' % (v[0], v[1], ', '.join(fl(float(x)) for x in v[2:15]), v[15])
    if kind == 'kill':
        return 'EffectModule(0x2723, 0x%x, 0x%x, 0x%x);' % tuple(v)
    if kind == 'sound':
        return 'SoundModule(0x2710, 0x%x);' % v[0]
    if kind == 'stop':
        return 'SoundModule(0x2714, 0x%x);' % v[0]
    raise ValueError(kind)


def block(ev, indent):
    out = []
    frames = sorted(set(f for f, _k, _v in ev))
    for i, f in enumerate(frames):
        out.append('%s%sif (f == %d)' % (indent, 'else ' if i else '', f))
        out.append(indent + '{')
        out += [indent + '    ' + call(k, v) for g, k, v in ev if g == f]
        out.append(indent + '}')
    return out


def c_source(ev):
    names = {0x11: 'Flame Slash', 0x12: 'Kacrackle Slash', 0x13: 'Metal Slash', 0x14: 'Hatchet Man'}
    out = ['// GENERATED by tools/kirby_hero_sword_msc.py from reference/brave_sword_spells_acmd.txt: do not edit by hand']
    for part, fn, kinds in (('game', 'khm_sw_game', ('hitbox', 'remove')),
                            ('effect / sound', 'khm_sw_fx', ('follow', 'effect', 'kill', 'sound', 'stop'))):
        out += ['// the sword spell n\'s %s commands at frame f of its cast (Hero\'s scripts, Kirby\'s bones)' % part,
                'void %s(int n, int f)' % fn, '{']
        for i, n in enumerate(sorted(ev)):
            g = [x for x in ev[n]['ground'] if x[1] in kinds]
            a = [x for x in ev[n]['air'] if x[1] in kinds]
            out.append('    %sif (n == 0x%x)        // %s' % ('else ' if i else '', n, names[n]))
            out.append('    {')
            if g == a:
                out += block(g, '        ')
            else:
                out += ['        if (global18 == 0x2)    // the air script', '        {']
                out += block(a, '            ')
                out += ['        }', '        else', '        {']
                out += block(g, '            ')
                out.append('        }')
            out.append('    }')
        out += ['}', '']
    out.append('')
    out.append('// the motion\'s end, its cancel frame and the hitbox frames, in frames since the cast')
    for key, fn in (('end', 'khm_sw_end'), ('cancel', 'khm_sw_cancel')):
        out.append('int %s(int n)' % fn)
        out.append('{')
        for n in sorted(ev):
            out.append('    if (n == 0x%x) { return %d; }' % (n, ev[n][key]))
        out.append('    return 0;')
        out.append('}')
        out.append('')
    out.append('int khm_sw_window(int n, int f)')
    out.append('{')
    for n in sorted(ev):
        a, b = ev[n]['hitbox']
        out.append('    if (n == 0x%x) { return f >= %d && f <= %d; }' % (n, a, b))
    out.append('    return 0;')
    out.append('}')
    out.append('// END GENERATED')
    return '\n'.join(out)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    ev = events(parse(args[0] if args else REF))
    if '--events' in sys.argv:
        print(json.dumps({'0x%x' % n: e for n, e in ev.items()}, indent=1))
    else:
        print(c_source(ev))


if __name__ == '__main__':
    main()
