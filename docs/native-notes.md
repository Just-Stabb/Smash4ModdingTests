# Native code notes (cross_f.rpx)

Findings from reading Smash 4's executable (`cross_f.rpx`, SHA-1
`3b7e1b3f421f330e259a3200d391f47ee6b5931a`). Addresses are memory addresses.
The code is PowerPC and has no symbols. Functions were found through
developer source-path strings and the RPX relocation table (`.rela.text`).

## How to look things up

1. Decompress a section (`tools/rpx_patch.py` has the loader; `.text` is at
   `0x02000020`, `.rodata` at `0x10000000`).
2. Find a string in `.rodata`.
3. Find relocations in `.rela.text` whose symbol value + addend equals the
   string's address. These are `R_PPC_ADDR16_HA`/`_LO` pairs, i.e. a
   `lis`/`addi` that loads the string.
4. Disassemble around them (capstone, `CS_ARCH_PPC`, 32-bit big-endian).

## Source files with paths in .rodata

`app\fighter\specializer\<fighter>\fighter_<fighter>.cpp` for ganon, kirby,
koopa, koopag, link, littlemac, littlemacg, lucario, lucariom, miiswordsman,
mewtwo, sonic, toonlink, wario, warioman and wiifit. Also
`app\battle_object\modules\kinetic\kinetic_module_impl.cpp`,
`app\fighter\modules\kinetic\fighter_kinetic_module_impl.cpp`, and
`app\weapon\modules\kinetic\weapon_kinetic_module_impl.cpp`.

| String | Address | Used by code at |
|---|---|---|
| `fighter_kirby.cpp` path | `0x1013520C` | `0x02EF966A` |
| Kirby `"SpecialNSearch"` | `0x101351FC` | `0x02EF938C` |
| `fighter_sonic.cpp` path | `0x10144628`, `0x10144734` | `0x02F7E02A`, `0x02F7E7FA` |
| Sonic `"SpecialNSearch"` (+ `_C2/_C3/_C4`), `"SpecialSDashAttack"` (+ `_C2/_C3/_C4`) | `0x10144710`, `0x1014468C`… | `0x02F7E846`… |

## Kirby's BattleObject (sys_21) commands 0x3E8–0x40C

The function at `0x02EF90D8` runs Kirby's character-specific `BattleObject`
commands. It takes `cmd - 0x3E8`, rejects anything above `0x24`, and jumps
through the branch table at `0x02EF912C`.

- `0x3E8`–`0x3FB` → `0x02EF959C` (shared/default path)
- `0x3FC`–`0x40C` → individual cases (`0x02EF91C0` … `0x02EF95D4`)

Cases that call `0x02760AF4(obj->[0x72DC], slot, name, kind)`:

| Command | Slot | Name | Kind |
|---|---|---|---|
| `0x403` | 3 | `"MetaknightSpecialNSpinGroundEffect"` | -1 (current) |
| `0x404` | 2 | `"KirbyToonLinkBowChargeMax"` | -1 |
| `0x405` | 0 | `"SpecialNSearch"` | `0x22` (Sonic copy) |

`0x02760AF4` takes a slot (0–3) and a kind (-1 means the object's own), looks
up a resource for that kind, then starts it by name at a frame rate. It
plays a named animation or effect, so `BattleObject(0x405)` (called once by
the Sonic copy's charge, `func_3469` in `kirby.c`) is probably the lock-on
visual, **not** the target search.

## Still to find: homing (kinetic type 0x68)

Kinetic types `0x64`+ are character-specific. For Kirby, `0x68` is the Sonic
copy's homing (set in the pre of Sonic-copy status `0x193`). Setting it from
side B (mid-status, or in the pre) doesn't home, so the target must come
from somewhere tied to the Sonic-copy statuses. Next steps:

1. In `fighter_kinetic_module_impl.cpp` / Kirby's specializer, find where the
   kinetic type is turned into energies (a switch over type values
   `0x64`+), and follow the `0x68` case.
2. See what that homing energy reads for its target (a search hit stored on
   the fighter, an opponent ID in work memory, …).
3. If the target is stored in a work variable or set by a `BattleObject`
   command, side B can supply it from MSC.
