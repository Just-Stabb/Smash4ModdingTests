#!/usr/bin/env python3
"""Kirby back throw (throwb) ACMD edit: weak release + bury slam hitbox with height damage tiers.

  python3 tools/kirby_throwb_acmd.py IN_game.bin OUT_game.bin

The throw itself can't bury (tested), so:
- Throw 0 (the release, Throw_Applier at frame 41) becomes a weak downward release:
  0 damage, 270 degrees, small fixed knockback, so the opponent stays on the ground.
- At frame HIT_FRAME a Special_Hitbox with the bury effect (0xB, the same effect Kirby's
  Stone uses) hits them, spiking (270). One block per damage tier: if Kirby int 0x10000095
  == t (set by throwb_land() in kirby.c), damage = the throw's old damage x (1 + t/10),
  t = 0..20 (1.0x .. 3.0x). Tiers above BIG_TIER (more than 2.0x) get HITLAG_BIG x hitstop.
Run it on an unedited throwb (it refuses a script that already has the tiers).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

TIER_VAR = 0x10000095
BURY = 0xB
SPIKE = 270
TIERS = 20
BIG_TIER = 10
HITLAG_BIG = 3.0
HIT_FRAME = 42       # one frame after the release
HIT_FRAMES = 2       # active frames
RELEASE_WBKB = 10    # weak fixed knockback of the release
SIZE = 12.0

IVC = acmd.BY_NAME["int_var_compare"]
TRUE = acmd.BY_NAME["true"]
SPEC = acmd.BY_NAME["throw_specifier"]
APPLY = acmd.BY_NAME["throw_applier"]
HITBOX = acmd.BY_NAME["special_hitbox"]
FRAME = acmd.BY_NAME["frame"]
WAIT = acmd.BY_NAME["wait"]
REMOVE = acmd.BY_NAME["remove_all_hitboxes"]


def hitbox(stone, base, damage, hitlag):
    syn = stone.info["syntax"]
    h = acmd.Command(HITBOX, list(stone.params))
    p = h.params
    def put(name, v):
        p[syn.index(name)] = v
    put("ID", 0)
    put("Bone", 0)
    put("Damage", damage)
    put("Angle", SPIKE)
    put("KBG", base.params[4])
    put("WBKB", base.params[5])
    put("BKB", base.params[6])
    put("Size", SIZE)
    put("X", 0.0)
    put("Y", 3.0)
    put("Z", 0.0)
    put("Effect", BURY)
    put("Hitlag", hitlag)
    put("Ground/Air", 3)
    return h


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = acmd.ACMDFile.load(src)
    s = f.script("throwb")
    if any(c.ident in (IVC, HITBOX) for c in s):
        sys.exit("throwb already edited")
    stone = next(c for c in f.script(0xBD5B3ADE) if c.ident == HITBOX)  # Kirby's Stone (bury effect 0xB)
    base = next(c for c in s if c.ident == SPEC and c.params[0] == 0)
    dmg = float(base.params[2])
    old = list(base.params)
    base.params[2] = 0.0           # damage
    base.params[3] = SPIKE         # angle
    base.params[4] = 0             # KBG
    base.params[5] = RELEASE_WBKB  # WBKB
    base.params[6] = 0             # BKB
    base.params[7] = 0             # effect
    old_spec = acmd.Command(SPEC, old)
    i = next(i for i, c in enumerate(s) if c.ident == APPLY and c.params[0] == 0)
    block = [acmd.Command(FRAME, [float(HIT_FRAME)])]
    for t in range(0, TIERS + 1):
        h = hitbox(stone, old_spec, round(dmg * (1 + t / 10.0), 2), HITLAG_BIG if t > BIG_TIER else 1.0)
        block.append(acmd.Command(IVC, [TIER_VAR, 0, t]))
        block.append(acmd.Command(TRUE, [2 + h.info["size"]]))
        block.append(h)
    block.append(acmd.Command(WAIT, [float(HIT_FRAMES)]))
    block.append(acmd.Command(REMOVE, []))
    s[i + 1:i + 1] = block
    f.save(dst)


if __name__ == "__main__":
    main()
