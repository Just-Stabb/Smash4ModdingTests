# Link (link)

Trait: not set yet (ask the user: CLAUDE.md "Character traits"). Link's fighter MSC (`link.mscsb`) is the
universal-mechanics one in `fighters_rolloff_hero_v1` and isn't changed here (not in this folder).

## Arrow (Hero's Bow): `weapons/bowarrow.c`

`fighter/link/script/msc/bowarrow/bowarrow.mscsb` (the weapon's own MSC; a vanilla weapon's MSC sits in a folder of
its name, as `zelda/script/msc/dein/dein.mscsb`), decompiled from the user's upload (vanilla; it rebuilds to the
same 64 functions, `tools/msc_fingerprint.py`).

Build:

    python3 tools/msclang/msclang.py -x tools/mscinfo.xml fighters/link/weapons/bowarrow.c -o build/link/bowarrow.mscsb

How the arrow's life works (read in the MSC; statuses: 0 on the bow, 1 flying, 2 stuck in the ground):
- Status 0's init (`func_63`, `global4 == 0`): the vl param group 19 entry 0 (`0x12000000`: **40** frames;
  custom 1 25, custom 2 11; `reference/params/vl/Link.csv`) into weapon ints `0x10000003` and `0x10000004`.
  The community sheet calls this entry "Lifetimes after stage impact"; it is the **flight** life. (The sheet's
  "Projectile lifetimes" gives Link's arrow "∞"; it isn't, the MSC removes it.)
- Status 1 (flying, main `func_53`): `func_61` every frame counts `0x10000004` down and removes the arrow
  (`BattleObject(0x9)`) at 0. Status 1's own init only sets damage / speed / gravity (vl entries 1-5, 7, 8).
- Status 2 (stuck in the ground, `func_55`): its init sets `0x10000004` to vl entry 6 (`0x12000006`: **80** frames;
  the sheet calls it "Time to fully charge") and a 3-5 damage; `func_62` counts it down and removes the arrow at 0
  or when the ground under it goes.
- The arrow's own MSC has no other life. Kirby's Link copy fires this same weapon (Kirby's articles are reserve
  slots filled by the copied fighter's), so its arrow should change the same way (its value is Kirby's vl copy of
  entry 0); not checked in game.

**Changed (user: "Make Link's arrow lifetime twice as long"):** status 0's init stores `vl entry 0 x 2`
(`func_63`): 80 frames of flight (customs 50 / 22). In MSC rather than the vl file, so every custom doubles. The
stuck-in-ground life (80) is unchanged.

Test: `tools/link_samus_test.py --arrow ORIGINAL NEW` (the flight lasts twice the original's frames for 40 / 25 /
11, the stuck life is the same); `tools/msc_stack_check.py`: no stack problems.

Package: `link_samus_v1` (`fighter/link/script/msc/bowarrow/bowarrow.mscsb`).
