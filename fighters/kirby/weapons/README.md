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

`build/acmd/weapon/starmissile/game.bin` adds a script for `0x92008FA0`
with a **weak windbox**: a copy of the vanilla star's `Special_Hitbox` with:
- damage 1.8, angle 20, KBG 20, BKB 35;
- **Flinchless = 1**: it pushes, no hitstun;
- hitlag 0, SDI 0;
- indirect, reflectable, hits each target once.

Tune it in FITX: BKB/KBG for push strength, angle for direction.

The star disappears when it hits: `func_57` (status 1's per-frame script)
calls `BattleObject(0x9)` (the same removal the lifetime timer uses) when
`AttackModule(0x2726)` or `AttackModule(0x2727, 0x2)` reports a hit.

Lifetime: 32 frames (`WorkModule(0x7, 32, 0x11000002)` in `func_59`).

### Damage set from MSC

The ACMD damage (1.8) didn't apply in-game. Vanilla star hitboxes all have 0
damage in ACMD, so the game sets the power natively when Kirby spits
something, and that leaves inhale stars at 0. `func_57` now calls
`AttackModule(0x271E, 0, starmissile_damage())` every frame. That's the same
call Kirby's Sonic copy uses to set its hitbox damage, and
`starmissile_damage()` is 1.8.
