#!/usr/bin/env python3
"""Hitboxes along the Marth copy's sword in Kirby's Strike neutral air (air jab 2), back air and up air.

  python3 tools/kirby_marth_sword_hitboxes.py KIRBY_GAME.bin MARTH_GAME.bin OUT_GAME.bin

The sword aerials (tools/kirby_marth_sword.py, fighters/kirby/specials.md) play the sword slots and
bind Kirby's own move script (marth_sword_play() in kirby.c). With this, they bind game scripts of
their own instead, named as the slots' effect / sound scripts (MarthSwordAttack12 / ...AttackAirB /
...AttackAirHi, motion.mtable 0x301-0x303): Kirby's move script with three spheres along the sword
added (only the Marth copy plays these, so Kirby's moves without it are unchanged).

The sword is Marth's model on Kirby's LHaveN (script bone 0x18), its blade along the bone's +Y at
twice Marth's size (the blade mesh runs 1.79-10.68 on Marth's sword: 3.6-21.4 on Kirby's). Hitbox
offsets are in the bone's frame without its scale (as Smash Forge places them), so the spheres sit at
Y = SPHERES on the blade: base, middle, tipper.

User: as Marth's (their Marth's own aerials, the comparison): each sphere is a copy of Marth's blade
hitbox (base, middle) or tipper (last) for the same move, damage / angle / knockback / size / effect
/ sound as his, so the tipper sends the other way from the blade as Marth's does (nair 0 vs 150,
back air 361 vs 180, up air 80 vs 270). Kirby's own hitboxes keep priority (user): the sword's are
in the same part with higher IDs, and the lower ID wins when both connect. Back air: Marth turns
around (Reverse_Direction) and hits in front (FacingRestrict 3); Kirby hits behind without turning
(FacingRestrict 4), so the sword's take Kirby's facing value and Marth's angles keep their meaning
(blade away from Kirby, tipper back the other way).

Timing: in Kirby's active window, from the frame the sword is out:
- Strike nair (attack12): with Kirby's hitbox (frame 3, the sword's first frame), removed with it.
- back air: from frame 7 (the sword appears; Kirby's strong hit is from 6) for Marth's 5 frames
  (Remove_Hitbox at 12); Kirby's weak hit at 8 keeps its ID 0.
- up air: with Kirby's hitboxes (frames 10-15; the sword is out from 4), removed with them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

BONE = 0x18                     # Kirby's LHaveN
SPHERES = (5.0, 11.5, 18.0)     # along the blade: base, middle, tipper
NAMES = {'attack12': 'MarthSwordAttack12', 'attackairb': 'MarthSwordAttackAirB',
         'attackairhi': 'MarthSwordAttackAirHi'}
# Marth's move for each, and the IDs of his blade / tipper hitboxes in it
MARTH = {'attack12': ('attackairn', 0, 3), 'attackairb': ('attackairb', 0, 2), 'attackairhi': ('attackairhi', 0, 3)}
HITBOX = acmd.BY_NAME['hitbox']
SPECIAL = acmd.BY_NAME['special_hitbox']
FRAME = acmd.BY_NAME['frame']
WAIT = acmd.BY_NAME['wait']
REMOVE = acmd.BY_NAME['remove_hitbox']
REMOVE_ALL = acmd.BY_NAME['remove_all_hitboxes']
HITBOXES = {HITBOX, SPECIAL, acmd.BY_NAME['extended_hitbox'], acmd.BY_NAME['extended_special_hitbox']}


def idx(cmd, name):
    return [s.lower() for s in cmd.info['syntax']].index(name.lower())


def marth_hitbox(mscript, hid):
    return next(c for c in mscript if c.ident in (HITBOX, SPECIAL) and c.params[0] == hid)


def sword(mscript, blade_id, tip_id, first_id, facing=None):
    """the three spheres: copies of Marth's blade (x2) and tipper, on Kirby's sword"""
    out = []
    for n, y in enumerate(SPHERES):
        src = marth_hitbox(mscript, tip_id if n == len(SPHERES) - 1 else blade_id)
        c = acmd.Command(src.ident, list(src.params))
        c.params[idx(c, 'ID')] = first_id + n
        c.params[idx(c, 'Part')] = 0
        c.params[idx(c, 'Bone')] = BONE
        c.params[idx(c, 'X')], c.params[idx(c, 'Y')], c.params[idx(c, 'Z')] = 0.0, y, 0.0
        if facing is not None:
            c.params[idx(c, 'FacingRestrict')] = facing
        out.append(c)
    return out


def kirby_ids(script):
    return {c.params[0] for c in script if c.ident in HITBOXES}


def edit_nair(k, m):
    s = [acmd.Command(c.ident, list(c.params)) for c in k]
    first = max(kirby_ids(s)) + 1
    # the first WAIT after Kirby's frame-3 hitboxes (the strike / normal branches end before it)
    f3 = next(i for i, c in enumerate(s) if c.ident == FRAME and abs(c.params[0] - 3) < 1e-6)
    w = next(i for i in range(f3, len(s)) if s[i].ident == WAIT)
    assert any(c.ident in HITBOXES for c in s[f3:w]), 'no hitbox at frame 3'
    s[w:w] = sword(m, *MARTH['attack12'][1:], first)
    return s


def edit_bair(k, m):
    s = [acmd.Command(c.ident, list(c.params)) for c in k]
    first = max(kirby_ids(s)) + 1
    f6 = next(i for i, c in enumerate(s) if c.ident == FRAME and abs(c.params[0] - 6) < 1e-6)
    w = next(i for i in range(f6, len(s)) if s[i].ident == WAIT)
    assert abs(s[w].params[0] - 2) < 1e-6, 'expected WAIT(2) after the frame-6 hitbox'
    facing = s[f6 + 1].params[idx(s[f6 + 1], 'FacingRestrict')]
    s[w:w + 1] = ([acmd.Command(WAIT, [1.0])] + sword(m, *MARTH['attackairb'][1:], first, facing) +
                  [acmd.Command(WAIT, [1.0])])
    f15 = next(i for i, c in enumerate(s) if c.ident == FRAME and abs(c.params[0] - 15) < 1e-6)
    s[f15:f15] = [acmd.Command(FRAME, [12.0])] + [acmd.Command(REMOVE, [first + n]) for n in range(len(SPHERES))]
    return s


def edit_uair(k, m):
    s = [acmd.Command(c.ident, list(c.params)) for c in k]
    first = max(kirby_ids(s)) + 1
    f10 = next(i for i, c in enumerate(s) if c.ident == FRAME and abs(c.params[0] - 10) < 1e-6)
    w = next(i for i in range(f10, len(s)) if s[i].ident == WAIT)
    s[w:w] = sword(m, *MARTH['attackairhi'][1:], first)
    return s


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    kf, mf = acmd.ACMDFile.load(sys.argv[1]), acmd.ACMDFile.load(sys.argv[2])
    for move, fn in (('attack12', edit_nair), ('attackairb', edit_bair), ('attackairhi', edit_uair)):
        k, m = kf.script(move), mf.script(MARTH[move][0])
        assert k and m, move
        kf.scripts[acmd.crc(NAMES[move])] = fn(k, m)
        print('%s (from %s, Marth %s):' % (NAMES[move], move, MARTH[move][0]))
        print(acmd.fmt_script(kf.scripts[acmd.crc(NAMES[move])]))
    kf.save(sys.argv[3])


if __name__ == '__main__':
    main()
