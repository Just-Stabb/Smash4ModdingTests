#!/usr/bin/env python3
"""Kirby back throw (throwb) ACMD edit: bury + height damage tiers.

  python3 tools/kirby_throwb_acmd.py IN_game.bin OUT_game.bin

- Throw 0 (the release) gets the bury effect (0xB).
- Before the Throw_Applier, one block per damage tier: if Kirby int 0x10000095 == t
  (set by throwb_land() in kirby.c), throw 0 is re-specified with damage x (1 + t/10),
  t = 1..14 (1.1x .. 2.4x). Tier 0 keeps the normal damage.
Run it on an unedited throwb (it refuses a script that already has the tiers).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

TIER_VAR = 0x10000095
BURY = 0xB
TIERS = 14

IVC = acmd.BY_NAME["int_var_compare"]
TRUE = acmd.BY_NAME["true"]
SPEC = acmd.BY_NAME["throw_specifier"]
APPLY = acmd.BY_NAME["throw_applier"]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = acmd.ACMDFile.load(src)
    s = f.script("throwb")
    if any(c.ident == IVC for c in s):
        sys.exit("throwb already has the damage tiers")
    base = next(c for c in s if c.ident == SPEC and c.params[0] == 0)
    base.params[7] = BURY
    dmg = float(base.params[2])
    i = next(i for i, c in enumerate(s) if c.ident == APPLY and c.params[0] == 0)
    block = []
    for t in range(1, TIERS + 1):
        spec = acmd.Command(SPEC, list(base.params))
        spec.params[2] = round(dmg * (1 + t / 10.0), 2)
        block.append(acmd.Command(IVC, [TIER_VAR, 0, t]))
        block.append(acmd.Command(TRUE, [2 + spec.info["size"]]))
        block.append(spec)
    s[i:i] = block
    f.save(dst)


if __name__ == "__main__":
    main()
