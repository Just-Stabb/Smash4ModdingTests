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

## Homing (kinetic type 0x68): traced

### 1. Kirby's custom kinetic types follow the current copy ability

Kirby's kinetic-type setup is `0x02F03AC8`. Types `<= 0x63` go to the common
setup (`0x02E7EE14`). For `0x64`+ it reads the **copy ability** (work int
`0x100000A4`) and jumps to that copy's helper object:

| Copy | Helper (global pointer) |
|---|---|
| `0x0D` | `*0x105544E4` |
| `0x0E` | `*0x1055453C` |
| `0x10` | `*0x105566E0` |
| `0x17` | `*0x10554438` |
| `0x18` | `*0x105545DC` |
| `0x22` (**Sonic**) | `*0x1056B3EC` |
| `0x26`, `0x27`, `0x2E`, `0x35` | other helpers |
| anything else | **returns without setting any energy** |

The per-frame kinetic update `0x02F03DD8` reads `0x100000A4` the same way.

**So `KineticModule(0, 0x68)` on Kirby only does something while Kirby has
the Sonic copy.** With no copy (or a different one), the type changes but
no energy is set up or updated. That is why side B with `0x68` never homed.

### 2. The Sonic homing helper (shared by Sonic and Kirby's Sonic copy)

`0x1056B3EC` is set at startup (`0x032158E4`) to a static object whose
vtable is `0x1018B2A0`. Sonic stores the same pointer at `module+0x1A8`
(`0x02F7D7E0`). Vtable entries:

- `+0x1C` → `0x03214020`: kinetic setup. For `0x64`+ it jumps through a
  table over `type - 0x64`; type `0x68` → `0x0321230C`.
- `+0x24` → `0x032155A0`: per-frame update (the homing step is `0x03215314`).

### 3. What the homing aims at

The setup at `0x0321230C` and the update at `0x03215314` both do the same
thing (the accessor's `+0x28` is WorkModule, `+0x18` is the position):

```
target_x = WorkModuleF(0, 0x1000006)
target_y = WorkModuleF(0, 0x1000007)
dir = normalize(target - my_position)
```

Then they add a random angle spread (RNG at `0x105659C0`), scaled by param
floats `0x5000006`/`0x5000007`, and set the speed along `dir`. The update
also counts down work int `0x11000005`, which the Sonic copy's main sets
from param `0x1500000C`.

**The "target" is just a point in two status work floats**, `0x1000006`
(X) and `0x1000007` (Y).

### 3b. Who writes the target: Sonic's search-hit code

Work memory layout (from the inlined accessors): `work+8` → group table.
In a group: `+0x04` = floats, `+0x0C` = ints, `+0x14` = flag words.
`0x1000006`/`7` are group 1 floats at `+0x18`/`+0x1C`. Searching for paired
`stfs …,0x18/0x1C` found the writer: **`0x02F7E4D8`**, slot `+0x14C` of
Sonic's specializer vtable (`0x1014479C`; the object is `0x105564FC`).

```
ok_kirby = (kind == 8 /*Kirby*/ && status == 0x192)
if (event has a hit object && (status == 0x152 || ok_kirby)):
    obj = hit object (ID at event+0x18), skipped if invalid
    (x, y, z) = obj's node position (vtable 0x19C, node from event+0x24/0x26)
    (some fighter kinds use another point, via 0x02BF00E4(…, 0xD))
    if !flag 0x2100000D:      write (x, y) to 0x1000006/7, set 0x2100000D
    elif flag 0x2100000E:     clear 0x2100000E, write
    else:                     write only if nearer than the stored point
                              (own position from obj+0x72F0)
```

How Kirby gets there: Kirby's slot `+0x14C` is `0x02EFB4FC`. It returns
unless int `0x100000AD` is non-zero, then calls `0x02F00140`. That function
switches on the copy kind cached in the specializer (`+0xB9CC`):

- `0x16`, `0x1C` → that copy's vtable `+0xEC`;
- `0x2A` → its own code;
- `0x22`, `0x2B` → `0x02E669F0(kind)` (fighter kind → specializer;
  `0x22` → `0x105564FC`), then vtable `+0x14C`;
- anything else returns.

So a search box only produces a homing target for Kirby with the Sonic copy
in status `0x192`. The patch that opens this up to side B (air swing `0x171`) is listed
in `fighters/kirby/specials.md`.

### 4. Status flow of Kirby's Sonic copy (MSC side, for reference)

- `0x192` charge: at the release frame `func_3469` calls `BattleObject(0x405)`,
  which starts `"SpecialNSearch"` for kind `0x22`.
- `func_3467`: if flag `0x2100000D` is set, next = `0x193` (homing, kinetic
  `0x68`); otherwise next = `0x195` (straight, kinetic `0x65`). It goes
  through `0x194` (4 frames, kinetic `0x33`) first.

### What we did with it

Side B now gets its target from this code through a 10-word RPX patch. MSC
steers toward `0x1000006`/`0x1000007` itself, so kinetic `0x68` isn't needed.
See `fighters/kirby/specials.md`.
