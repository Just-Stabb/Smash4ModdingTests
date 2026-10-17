#!/usr/bin/env python3
"""Kirby back throw (throwb) ACMD edit: height damage tiers; bury slam only from 2.5x.

  python3 tools/kirby_throwb_acmd.py IN_game.bin OUT_game.bin

Kirby int 0x10000095 = damage tier t (set by throwb_land() in kirby.c): 0 = 1.0x .. 20 = 3.0x,
damage = the throw's original damage (8) x (1 + t/10).
- t < BURY_TIER (below 2.5x): the normal back throw release (throw 0 at frame 41, original angle,
  BKB), knockback growth x KBG_SCALE, no bury. Tiers above BIG_TIER (more than 2.0x) get
  HITLAG_BIG x hitstop.
- t >= BURY_TIER (2.5x and up): a weak release (0 damage, 270 degrees, fixed knockback
  RELEASE_WBKB, so the opponent stays on the ground), then at HIT_FRAME a Special_Hitbox with the
  bury effect (0xB, copied from Kirby's Stone), 270 degrees, the throw's original knockback,
  HITLAG_BIG x hitstop, for HIT_FRAMES frames.
Run it on an unedited throwb (it refuses a script that already has the tiers). With
`--retune` on an edited throwb, it only sets the bury slams' Size (SIZE) and SDI (SDI).

  python3 tools/kirby_throwb_acmd.py IN OUT --retune
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

TIER_VAR = 0x10000095
TIERS = 20
BURY_TIER = 15       # 2.5x
BIG_TIER = 10        # above: 3x hitstop
HITLAG_BIG = 3.0
KBG_SCALE = 0.6
BURY = 0xB
SPIKE = 270
HIT_FRAME = 42
HIT_FRAMES = 2
RELEASE_WBKB = 10
SIZE = 18.0         # bury slam size (was 12; bigger so it catches opponents still slightly airborne)
SDI = 0.0

IVC = acmd.BY_NAME["int_var_compare"]
TRUE = acmd.BY_NAME["true"]
SPEC = acmd.BY_NAME["throw_specifier"]
APPLY = acmd.BY_NAME["throw_applier"]
HITBOX = acmd.BY_NAME["special_hitbox"]
FRAME = acmd.BY_NAME["frame"]
WAIT = acmd.BY_NAME["wait"]
REMOVE = acmd.BY_NAME["remove_all_hitboxes"]


def when(t, cmd):
    return [acmd.Command(IVC, [TIER_VAR, 0, t]), acmd.Command(TRUE, [2 + cmd.info["size"]]), cmd]


def damage(base, t):
    return round(base * (1 + t / 10.0), 2)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = acmd.ACMDFile.load(src)
    s = f.script("throwb")
    if any(c.ident in (IVC, HITBOX) for c in s):
        if "--retune" not in sys.argv[3:]:
            sys.exit("throwb already edited (use --retune to only update the slam's Size / SDI)")
        for c in s:
            if c.ident == HITBOX and c.params[c.info["syntax"].index("Effect")] == BURY:
                c.params[c.info["syntax"].index("Size")] = SIZE
                c.params[c.info["syntax"].index("SDI")] = SDI
        f.save(dst)
        return
    stone = next(c for c in f.script(0xBD5B3ADE) if c.ident == HITBOX)  # Kirby's Stone (bury effect 0xB)
    base = next(c for c in s if c.ident == SPEC and c.params[0] == 0)
    orig = list(base.params)  # ID, Bone, Damage, Angle, KBG, WBKB, BKB, Effect, ?, Hitlag, ...
    dmg = float(orig[2])

    def normal(t):
        p = list(orig)
        p[2] = damage(dmg, t)
        p[4] = int(round(orig[4] * KBG_SCALE))
        if t > BIG_TIER:
            p[9] = HITLAG_BIG
        return acmd.Command(SPEC, p)

    def weak():
        p = list(orig)
        p[2], p[3], p[4], p[5], p[6], p[7] = 0.0, SPIKE, 0, RELEASE_WBKB, 0, 0
        return acmd.Command(SPEC, p)

    def slam(t):
        syn = stone.info["syntax"]
        h = acmd.Command(HITBOX, list(stone.params))
        for name, v in (("ID", 0), ("Bone", 0), ("Damage", damage(dmg, t)), ("Angle", SPIKE),
                        ("KBG", orig[4]), ("WBKB", orig[5]), ("BKB", orig[6]), ("Size", SIZE),
                        ("X", 0.0), ("Y", 3.0), ("Z", 0.0), ("Effect", BURY), ("SDI", SDI),
                        ("Hitlag", HITLAG_BIG if t > BIG_TIER else 1.0), ("Ground/Air", 3)):
            h.params[syn.index(name)] = v
        return h

    base.params = normal(0).params  # tier 0
    i = next(i for i, c in enumerate(s) if c.ident == APPLY and c.params[0] == 0)
    before = []
    for t in range(1, TIERS + 1):
        before += when(t, normal(t) if t < BURY_TIER else weak())
    after = [acmd.Command(FRAME, [float(HIT_FRAME)])]
    for t in range(BURY_TIER, TIERS + 1):
        after += when(t, slam(t))
    after += [acmd.Command(WAIT, [float(HIT_FRAMES)]), acmd.Command(REMOVE, [])]
    s[i + 1:i + 1] = after
    s[i:i] = before
    f.save(dst)


if __name__ == "__main__":
    main()
