# Samus (samus)

`samus.c` is decompiled from `fighters_rolloff_hero_v1`'s `samus.mscsb` (the universal mechanics and Hero's
roll-off momentum already in it, with Samus's roll not held to the ground speed limit; it rebuilds to the same
2431 functions, `tools/msc_fingerprint.py`). Trait: **Shooter** (`docs/character-traits.md`).

Build:

    python3 tools/msclang/msclang.py -x tools/mscinfo.xml fighters/samus/samus.c -o build/samus/samus.mscsb

(The decompile's `printf` strings with a line break are written `\n`; mscdec writes the break itself.)

## Charge Shot (neutral special)

Statuses: `0x152` SpecialN (pre `func_2252` picks the start), `0x157` ground start (`func_2261`; at its end
`func_2263`: a full stored charge or a quick press shoots, else the hold), `0x158` hold / charging (main
`func_2264`, loop `func_2265` -> `func_2344`: charge + 1 a frame, at full `0x159`; special shoots `0x15A`, shield
`0x1B`; shield / dodge out on the ground `0x20` / `0x21`), `0x159` full-charge end, `0x15A` / `0x15C` shoot
(ground / air; the init moves the charge into `0x11000002` and clears the stored one), `0x15B` air start.

The charge is fighter instance int **`0x10000084`** (frames; full at vl `0x5000002`, `func_2343`), so it lasts
across statuses. The full charge's glow is the effect handle in `0x10000083`. Each status's exit (status table
key 6) decides whether it's kept: the hold's (`func_2346`) keeps it when the next status is `0x159`, `0x1B`
(shield), `0x1F` (spot dodge), `0x20` / `0x21` (rolls) (removes the charging shot, article 0, and at full makes
the glow); the starts' (`func_2338` ground, `func_2341` air) keep it only into the move's own next statuses.
Anything else (a hit) cleared it: `0x10000084 = 0`, the shot and the glow removed.

**Changed (user: "when Samus is hit while charging, she doesn't lose her current charge"):**
- Hold exit `func_2346`: a hit (next status `0x45`-`0x4C`: Damage (ground, air), DamageFly, DamageFlyRoll, wall /
  ceiling / floor bounce, DamageFall) keeps the charge as a shield does (the same branch: the charging shot is
  removed, a full charge gets its glow).
- Start exits `func_2338` / `func_2341`: a hit in the start keeps the stored charge (and the glow of a stored full
  charge); only the shot article is removed.
- Not changed: being grabbed (`0x3F`), shield break / sleep / stun, being buried or frozen still clear it as
  before (not damage statuses); a hit in the shooting statuses (`0x15A` / `0x15C`) doesn't matter (the charge is
  already the shot's).

Kirby's Samus copy had the same loss; the same change is in `fighters/kirby/kirby.c` (`func_2720` hold
`0x1F1`, `func_2722` / `func_2725` starts `0x1F0` / `0x1F4`; specials.md).

Tests: `tools/link_samus_test.py --samus ORIGINAL NEW [--kirby ORIGINAL NEW]` (every next status 0-0x1FF through
the three exits, charge 30 and full: a hit keeps it and removes the shot, every other status as the original);
`tools/msc_stack_check.py`: no stack problems; `tools/rolloff_hold_test.py`: Samus's roll-off as Hero's.

Package: `link_samus_v1` (`fighter/samus/script/msc/samus.mscsb`).
