#!/usr/bin/env python3
"""Kirby's Hero copy fix v7: Hero's sword trails on the Stone's sword spells (ACMD effect scripts for the swing slots).

  python3 tools/kirby_hero_sword_acmd.py KIRBY_ANIMCMD_BODY OUT_DIR

KIRBY_ANIMCMD_BODY: Kirby's fighter/kirby/script/animcmd/body (motion.mtable, effect.bin: the user's installed ones,
the Drive's fighter-modded-scripts-only copy). OUT_DIR gets motion.mtable and effect.bin.

During a sword spell Kirby plays motion 0x304-0x307 (tools/kirby_hero_sword_anim.py: LHaveN on Hero's sword path).
Those slots had no motion.mtable name, so no ACMD ran. Now they're named BraveSword17-20 (motion.mtable: the
names' crc32, as every script's key; tools/Sm4shCommand ModAnimNames.txt labels them) and their effect scripts hold
Hero's trail: his built effect scripts' Sword_Glow / Terminate_Sword_Glow (reference/brave_sword_spells_acmd.txt,
Ultimate's AFTER_IMAGE4_ON / AFTER_IMAGE_OFF as tools/ultimate_acmd.py converted them for his port): his trail
textures (ids 264-269, tools/trail_table_cave.py: TexBraveSwordTrace / Add / Fire / Lightning / Final / 3, loaded
with Hero, who is in the match whenever Kirby has his copy) and shader 3, so Kirby's trail is drawn exactly as
Hero's own. Converted:
- bones: Hero's 0x19 (Sword1) -> Kirby's LHaveN 0x18, offsets (x, y, z) -> (x, y - 0.2023, z) (LHaveN is Sword1's
  frame since fix v7: kirby_hero_sword_msc.sword_point); the trail's effect bone rotation as Hero's;
- frames: Hero's motion frames -> cast frames (kirby_hero_sword_msc.timing, the hitboxes' clock), which are the swing
  motion's frames (khm_sw_motion starts it at the cast's first frame and keeps it there);
- the ground scripts (the air ones have the same trail).
The other effects stay MSC calls (khm_sw_fx) and the slots get no game / sound / expression scripts.

Fix v8 (fighters/kirby/specials.md "Hero copy fix v8"; user: the moves' own effects "don't appear"): the effect
scripts also hold Hero's sword-following effects (his External_Graphic on his sword: Flame Slash's fire blade
0x3450078, Kacrackle Slash's ice 0x3450076, Hatchet Man's dark blade 0x3450072, Hero's own turned variants
brave_*_sword@0,0,-90 of fighters/brave/brave_effects.json) and their Terminate_Graphic_Effect, from
kirby_hero_sword_msc.sword_effect_events: on LHaveN with the v7 offsets, rotations and sizes Hero's, no colour or
alpha set on the call (Hero's scripts set none: the emitters' own colours, his .ptcl's), Terminate 0, and only while
the sword is drawn (the trail's window). They were MSC calls (khm_sw_fx, EffectModule 0x2712) through fix v7.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd  # noqa: E402
import kirby_hero_sword_anim as A  # noqa: E402
import kirby_hero_sword_msc as SW  # noqa: E402

TRAIL = ('Sword_Glow', 'Terminate_Sword_Glow')


def name(n):
    return 'BraveSword%d' % (n - 0x11 + 17)


def trail_events(n, ref):
    """[(cast frame, command name, {param: value})] of spell n's trail, Kirby's bones"""
    at = SW.timing(ref[(n, 'ground', 'game')])
    out = []
    for mf, nm, a in ref[(n, 'ground', 'effect')]:
        if nm not in TRAIL:
            continue
        a = dict(a)
        if nm == 'Sword_Glow':
            for b, xyz in (('Bone1', ('X1', 'Y1', 'Z1')), ('Bone2', ('X2', 'Y2', 'Z2')), ('Bone3', ('X', 'Y', 'Z'))):
                assert a[b] == SW.SWORD_BONE, (n, b, a[b])
                a[b] = SW.K_SWORD
                for k, v in zip(xyz, SW.sword_point(*(a[k] for k in xyz))):
                    a[k] = v
        out.append((at(mf), nm, a))
    return out


def fx_events(n, ref):
    """fix v8: the trail and the sword-following effects, by cast frame (stable: the trail first)"""
    ev = trail_events(n, ref) + SW.sword_effect_events(ref, n)
    return sorted(ev, key=lambda e: e[0])


def command(nm, a):
    ident = acmd.BY_NAME[nm.lower()]
    info = acmd.INFO[ident]
    params = [float(a[k]) if f == 1 else int(a[k]) for k, f in zip(info['syntax'], info['format'])]
    return acmd.Command(ident, params)


def script(events):
    out, t = [], 0.0
    for f, nm, a in events:
        if f > t:
            out.append(acmd.Command(acmd.BY_NAME['frame'], [float(f)]))
            t = f
        out.append(command(nm, a))
    out.append(acmd.Command(acmd.END))
    return out


def build(src, out):
    ref = SW.parse()
    mt = open(os.path.join(src, 'motion.mtable'), 'rb').read()
    table = list(struct.unpack('>%dI' % (len(mt) // 4), mt))
    eff = acmd.ACMDFile.load(os.path.join(src, 'effect.bin'))
    made = {}
    for n in sorted(A.SLOT):
        h = acmd.crc(name(n))
        assert table[A.SLOT[n]] in (0, h), 'motion 0x%X is named already (0x%08X)' % (A.SLOT[n], table[A.SLOT[n]])
        assert h not in eff.scripts or table[A.SLOT[n]] == h, '%s: a script of that name exists' % name(n)
        table[A.SLOT[n]] = h
        ev = fx_events(n, ref)
        eff.scripts[h] = script(ev)
        made[n] = ev
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'motion.mtable'), 'wb').write(struct.pack('>%dI' % len(table), *table))
    eff.save(os.path.join(out, 'effect.bin'))
    return made


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    made = build(sys.argv[1], sys.argv[2])
    for n, ev in sorted(made.items()):
        print('%s (0x%X): %s' % (name(n), A.SLOT[n], '; '.join('%d %s' % (f, nm) for f, nm, _a in ev)))


if __name__ == '__main__':
    main()
