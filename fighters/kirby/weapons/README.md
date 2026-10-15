# Kirby weapons

## starmissile (article 0x17, the spit / inhale star)

- `starmissile.mscsb`: the weapon's compiled MSC (as provided).
- `starmissile.c`: decompiled with `tools/mscdec`; edit this one.

Build with:
```sh
python3 tools/msclang/msclang.py -x tools/mscinfo.xml fighters/kirby/weapons/starmissile.c -o build/starmissile.mscsb
```
The unedited `starmissile.c` compiles back to identical code.

| Status | Scripts | What it is |
|---|---|---|
| 0 | `func_49`/`func_50` | Created / held. Motion 0, no lifetime |
| 1 | `func_54`/`func_55`, per frame `func_57` | Flying. Motion 4. `func_57` counts down `0x11000002` and removes the star (`BattleObject(0x9)`) at 0 or when it touches the ground |

Shared by both statuses: init `func_59` (status 1 sets the lifetime), exec
`func_60` (spin, plus speed decay unless `0x11000001 == 2`), and key 5
`func_61`.

**Changed:** the lifetime is 32 frames. `func_59` used to read it from
weapon parameter `0x12000013`; it now sets `WorkModule(0x7, 32, 0x11000002)`.

## Hitboxes for the inhale stars (ACMD)

The stars that neutral special fires are put in status 1, which plays
animation 4 (`func_24(0x4, ...)` in `func_55`). The star's ACMD
(`animcmd/weapon/starmissile/game.bin`) had no script for animation 4, which
is hash `0x92008FA0` in its `motion.mtable`, so those stars had no hitbox.
The only scripts are for animations 0 and 2, and their `Special_Hitbox` has
0 damage (vanilla presumably sets the spit star's damage natively).

`build/acmd/weapon/starmissile/game.bin` adds a script for `0x92008FA0` with a
copy of the vanilla star's `Special_Hitbox`, with **Damage 5**: angle 45,
KBG 78, BKB 70, size 2.5, indirect, reflectable, hits each target once.
Change the damage in FITX if needed.

Lifetime: 32 frames (`WorkModule(0x7, 32, 0x11000002)` in `func_59`).
