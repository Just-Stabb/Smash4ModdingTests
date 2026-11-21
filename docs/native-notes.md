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

## Kirby copy abilities: how the game grants one (traced)

MSC never sets the copy variables. All of this is native.

### `copy_grant` = `0x02EFCD8C` (Kirby specializer code)

Arguments: `r3` = Kirby's specializer object (`0x02E669F0(8)`), `r4` = Kirby's
module accessor, `r5` = a value stored in int `0x100000A5` (costume/colour of
the copied fighter, probably), `r6` = **fighter kind to copy**, `r7` = 1.

1. Returns if kind == 8 (Kirby) or kind ≥ `0x3A`.
2. Clears copy flags `0x20000078`–`0x20000095` (30), zeroes copy ints
   `0x10000083`–`0x100000A0`, and sets copy floats `0x2F`–`0x4C` to a default.
3. Writes `r5` to int `0x100000A5` (store at `+0x294`). If int `0x100000AD`
   is non-zero, it calls `0x02EFDB88(spec, kind)` and
   `0x02EFDDFC(spec, kind, r5)`.
4. Calls `0x02EFC940(r3, r4, kind)` (copy setup).
5. Writes kind to **int `0x100000A4`** (copy kind; inlined store
   `stw kind, 0x290(ints)`).
6. Sets flags **`0x2000009A`** (has copy) and `0x2000009C` (`oris 0x1400` on
   flag word 4). Kind `0x1C` sets an extra bit; kind `0x10` does extra setup.

"Lose copy" stores -1 to `0x100000A4` and clears `0x2000009A`
(`0x02EF5CC8`, `0x02EF5FDC`).

**Losing the copy when hit (removed).** Kirby's specializer vtable (`0x10135440`) points its
on-damage handler at `0x02EF7360`: when Kirby has a copy (flag word bit 5 set, bit 4 clear) and the
hit isn't type 7, it rolls the game's xorshift RNG (`0x105759C0`) `% 100` against
`(int)(rate × damage)` (rate from the per-kind table `[[0x102FF448]+0x113C]+0xFC` + kind × 0x88,
`+0x24`), and below it calls `0x02EF6F2C` (lose the copy with the star) at **`0x02EF74A8`**.
`0x02EF74A8=0x60000000` (in the standard build) skips that call, so damage never removes the copy;
the RNG still advances as before. Other ways of losing it (`0x02EF6F2C` from `0x02EFB6D8`, KO,
the copy-discard taunt) are separate and untouched.

### Its only caller: Swallow status handler `0x0279666C`

Kirby's setup (`0x02EF5940`…) fills a per-status table at `(obj+0x44)+4*status`.
The object with vtable `0x1009664C` goes in slot `0x167` (Swallow), and
`0x0279666C` is that vtable's `+0x34` entry. What it does:

1. Gets Kirby's specializer: `0x02E669F0(8)`.
2. Returns unless **status flag `0x21000012`** is set (the swallow ACMD sets
   it). Then it clears it and sets `0x21000013`.
3. Reads ints `0x11000008`–`0x1100000A` and plays something via module
   `+0x50` vtable `+0x74`.
4. **Target**: module `+0x68` vtable `+0xA4`, argument 0 → the captured
   object's ID. `0x02BF2108` resolves it. `0x02BEF5F4` tests "not a fighter".
   `0x02BEF604` gives the **fighter kind**. `0x02BEF610` gives a value passed as
   `r5` (costume/colour). The kind becomes -1 for non-fighters or when the
   target has flag `0x20000058`.
5. If the target is a Kirby: kind = that Kirby's copy (`0x02EFD128`), and the
   value from `0x02EFB624`.
6. `copy_grant(spec, kirby, r5, kind, 1)`.

### What this means for "copy on the 12th star hit"

Granting is one call with four inputs we can produce natively: the
specializer (`0x02E669F0(8)`), Kirby's accessor, the target's kind (and
costume value), and 1. What's missing:

- Native code that runs at the right moment with the target. For example, a
  code cave hooked into an unused Kirby `BattleObject` command (dispatcher
  `0x02EF90D8`, cmd `0x3E8`–`0x40C`) that calls `copy_grant` with a kind MSC
  passes in.
- A way for the star (weapon) to know which fighter it hit, and to tell Kirby
  (hit count + target kind). Not found yet.

## Star missile hits: where the hit target lives (traced)

### The star missile's native code

- **Weapon kind `0x0B`**: index in the weapon-name table at `0x10419604`
  (`fireball` = 0). The second `starmissile` (`0x28`) is presumably King
  Dedede's.
- Weapon-kind switches (`cmplwi 0x184`) at `0x02B650EC`, `0x02B68944`,
  `0x02B6B794`, …, `0x0320D77C`, `0x0321099C` dispatch per weapon. Case `0x0B`
  returns two star singletons: `0x10342F08`, and `0x10550148` (vtable
  `0x100E0BD8`, the star's specializer). A weapon keeps its specializer
  pointer at `weapon+0x1BF0`.
- Specializer vtable entries are `(0, fn)` pairs, so a slot is the printed
  offset + 4. Star-specific slots:
  - `+0x5C` → `0x02B037B8`: event handler. Acts on event `0x1A`: sets
    `0x21000000`, calls `0x02BEED58`, sets `0x20000004`.
  - `+0xAC` → `0x02B03C34`: hit-result callback. Gets `(weapon, result
    bits)`, not the target.
- The base weapon class vtable is `0x100F78F8`. Its `+0x374` is
  `0x02B89C38` (calls the specializer's `+0xAC`) and `+0x30C` is
  `0x02B894C4` (calls `+0x5C`; event kind at `+8`).

### MSC `AttackModule` (syscall `0x2E`)

`0x030B50F0` calls `AttackModule(+0x50 of the module accessor)` vtable
`+0x334` = `0x02C0ACFC`, a switch over commands `0x2710`–`0x2740` (49
cases). It confirms `0x271A` = set damage and `0x271E` = add damage.
`0x2726` reads `AttackModule+0xC4` (hit this frame) and `0x2727` reads
`+0xC8` (hit since start; `0x2724` clears it). There's no command that
returns the hit target.

A hitbox can be made from MSC with op `0x272C` (ACMD Extended_Special_Hitbox's own path: `0x02C0D210`, parser
`0x02C0AA64`): `AttackModule(0x272c, 40 FP params, X2, Y2, Z2)`, the args as raw words (ints, floats as float bits:
Damage, Size, X/Y/Z, Trip, Hitlag, SDI and X2/Y2/Z2 floats), 44 words with the op (the count is checked: 42 + 2).
Kirby's Hero copy's sword spells use it (fighters/kirby/specials.md "v6"; not checked in game yet).

### Kirby's copy held model (article 26)

The held model of a copy (marthsword, ikesword, ...) is Kirby's article 26 "simple" (weapon kind 0x11), made by the
copy model function `0x02EFE138` (generate at `0x02EFE748`) only for the kinds with one (the compare chain from
`0x02EFE664`), removed on a copy's loss (its -1 call); its model is the copied player's slot resource of type 0x11
(the copy-resource loader `0x030C4694` loads types 0xC / 0x11 / 0x164 / 0x165 = Kirby's article weapon kinds hat /
simple / simple2r / simple2l per match entry), named from `0x1041A8A0` (read at `0x030C487C`); `0x02B02534` is that
article's per-frame update (r27 the owner's module accessor), showing it by the owner's status
(`tools/copy_held_cave.py`, `tools/kirby_hero_sword_cave.py`). Its init `0x02B02078` links it to a Kirby joint by the copy kind (0x18
LHaveN for the swords, 0x19 RHaveN by default, 1000 for Sonic's sphere) with LinkModule constraint flags (vt +0x314). Its
drawing also follows Kirby's: the weapon VisibilityModule's is_visible (vt +0xA4 = `0x02C77004`) is its own flag (+8) AND,
when its LinkModule has attribute 7 on a link (set_attribute vt +0x3BC = `0x02C5847C`, link `[+0xC] + 0x38 n` +0x30;
module mask +0x84), the parent's is_visible (LinkModule vt +0xDC = `0x02C560C8`). The update sets link 3's attribute 7
every frame except in the Sonic copy's spin motions 0x318-0x31A, where Kirby is hidden and the sphere shows; so a held
model can't show while Kirby is invisible (e.g. the stone) unless that attribute is cleared (Kirby's Hero copy fix v5,
fighters/kirby/specials.md). How it is drawn (measured on a game clip, Hero copy fix v7): the item's
model is placed at joint @ K with K a -90 degree turn about the joint's Z (the item's +Y along the joint's +X;
marthsword's blade comes out along LHaveN's +Y), and a fighter's drawn pose leaves out the root TransN's translation
(the root's motion: Kirby's stone pose holds TransN at (0, 9, 0)).

### Collision records (the hit target)

`0x02C09C0C` (sets `+0xC4`/`+0xC8`) walks the attack module's **per-hitbox
collision records**:

```
count  = *(u32*)(AM + 0x18)                 // hitboxes
array  = *(u8**)(AM + 0x14)                 // stride 0x174 per hitbox
for each hitbox h:
    sentinel = array + h*0x174 + 0x124
    node     = *(array + h*0x174 + 0x128)   // first node; node+4 = next
    while node != sentinel:
        target_id = *(u32*)(node + 0x18)    // object that was hit (resolve: 0x02BF2108)
        type      = *(u8*)(node + 0x1C)     // 0 = hurtbox, 2 = …
        state     = *(u8*)(node + 0x23)
        hitbox_id = *(u8*)(node + 0x27)
        node = *(node + 4)
```

These records are the "don't hit the same target twice" log, so they're
still there right after the hit.

**Correction (Sephiroth bisect 70):** the 0x174 entries are per **Part**, not per hitbox. `AM + 0x18` is
the highest Part in use + 1 and `AM + 0x10` how many there are; a hitbox's 0x84 entry (`[AM + 0x40] + id
x 0x84`, `AM + 0x3C` of them) holds its Part at `+0x74`, and `set_attack` (`0x02C08848(AM, id, part)`)
indexes the groups with it **unchecked** (no compare with `AM + 0x10` or `AM + 0x3C`).

### AttackModule sizes (hitbox IDs, Parts)

Set once per object: the module accessor's init (`0x02BF4F08`) passes each module its part of a
parameter block (AttackModule: vt `+0x1C`, `0x02C079E0`, with block `+0xD4`), and that block is filled
per object class beforehand:

| class | filled at | hitbox IDs (`+0xDC`) | Parts (`+0xEC`) |
|---|---|---|---|
| fighters (module set `0x02E54660`) | `0x02E53FA4` / `0x02E5407C` | 10 | 20 |
| weapons: the kind's own object (`0x02BCBD84`: `0x03210C30(kind)` -> vt `+0xC`) | dein (kind `0x22`) `0x032107B4` | 7 | 2 |
| `0x02DA2AA4` (another class) | | 10 | 10 |

So a dein copy has IDs 0-6, Parts 0-1. A hitbox with Part 2+ on one writes its hit record over the
memory after the groups when it connects (Shadow Flare's orbs, Parts 2-4: the game crashed on the hit,
with only `GX2RSetAttributeBuffer` errors in Cemu's log). `tools/port_check.py` W4 checks the new
articles' scripts against `WEAPON_ATTACK_SLOTS`.

Clearing records: `0x02C10660(group, list, 0)` frees a group list's records of the group's current round
(`+0x16A`, copied to each record's `+0x28` when it's added); `0x02C0ECDC(AM + 8)` does that for every
group's current list (`+0x130`) and `+0x124`. vt `+0x34` (`0x02C081C8`, object set-up `0x02BF5D88`) runs it
when `AM + 0x118` is set, else `0x02C0EDE0`, which also zeroes each group's hitbox count (`+0x164`: not safe
with hitboxes out). No MSC command reaches it (`0x2718` remove and `0x2719` clear-all keep the records), so
ACMD `Hit_Log_Clear(Part)` (`docs/acmd-extra-commands.md`) was added for it.

### Step 2 plan (copy on the 12th star hit)

A small code cave (new PPC code in unused space), reached from a spare
command:

1. Gets the star's attack module and reads hitbox 0's newest record →
   `target_id`.
2. Resolves the target (`0x02BF2108`). It skips non-fighters
   (`0x02BEF5F4`) and reads the target's kind (`0x02BEF604`) and costume
   value (`0x02BEF610`).
3. Finds the owner Kirby (weapon owner/link), adds 1 to a counter in Kirby's
   work memory, and on the 12th calls
   `copy_grant(0x02E669F0(8), kirby, costume, kind, 1)`, then resets the
   counter.

The star's MSC calls it on the hit frame (`AttackModule(0x2726)`), just
before it deletes itself. Still to find: a spare weapon-side command (or
Kirby-side `BattleObject` case) to hook, the weapon → owner link, and free
code space in the RPX.

## Implemented: copy ability on the 12th star missile hit

Generator: `tools/starcopy_cave.py` (prints `ADDR=VALUE` words for
`tools/rpx_patch.py`; `--list` prints one per line).

- **Weapon command path**: MSC `BattleObject(cmd)` on a weapon → message
  (kind 6) → `obj vtable(+0x24)[+0x21C]` = `0x02B88030`. `cmd ≤ 8` →
  `0x02B938E0`; `9…0x15` → switch (`9` = remove); anything else →
  `0x02B89180` → **specializer `+0x54`** `(spec, weapon, msg)`, command at
  `***(msg+8)`. For Kirby's star that's `0x02B037B0` (`li r3,0; blr`), which
  only the star's vtable references (`0x100E0C2C`). The vanilla star calls
  `BattleObject(0x19)`, which also lands here.
- **Owner**: `weapon+0x1BF8` (base weapon vtable `+0x254`). At creation the
  star stores its own ID in the owner's int `0x100000A6` (`0x02B03174`).
- **Handle helpers**: `0x02BF2108(*(0x102F6C30), &h, id, 0)`. From the handle:
  `0x02BEF61C` valid, `0x02BEF5F4` category (0 = fighter), `0x02BEF604` kind,
  `0x02BEF610` costume value, `0x02BEF5DC` module accessor. `0x02BF05C8(h,
  value, id)` sets an int on the target. WorkModule: `+0x84` get_int(id),
  `+0x8C` set_int(value, id).
- **Patch**: `0x02B037B0` = `b 0x037ED898`. The cave overwrites an
  unreferenced Havok function (`TtrcCapsule`, `0x037ED898`, 0xEA8 bytes; no
  relocations or outside branches into it; the only export is `0x03374E7C`).
  It handles command `0x1F4` only: newest collision record of hitbox 0 →
  target. It must be a fighter, and the owner must be Kirby. Kirby int
  `0x1000009D` (unused by MSC and native code) counts the hits; at 12 it calls
  `copy_grant(0x02E669F0(8), kirby, costume, kind, 1)` (not for Kirby
  targets) and resets the count. It returns 0 like the stub.
- **MSC**: `starmissile.c` `func_57` calls `BattleObject(0x1F4)` when the
  hitbox connects, just before `BattleObject(0x9)`.
- **Crash on the first star hit (fixed).** The first cave read the attack
  module as `*(*(weapon+0x28)+0x50)`. The weapon passed to the hook is the
  weapon table entry itself (`0x02BF4B24`: `0x1E20`-byte entries, ID at
  `+0`, vtable at `+0x24`, specializer `+0x1BF0`, owner `+0x1BF8`). Its
  module accessor is at `+0xC`, the same field the handle getter
  `0x02BEF5DC` reads, so the attack module is `*(*(weapon+0xC)+0x50)`.
  `+0x28` is something else, so the old chain read a garbage pointer.
- **Data addresses**: absolute, like the game's own code uses them
  (`lis r12,0x1035; lwz 0x184C(r12)` in `0x02BF205C`); data sits at its link
  address. An intermediate build rebuilt them position-independently with
  `bl +4; mflr`. That froze and then crashed Cemu as soon as it ran twice
  (crash-bisect stage 3; host access violation at `0x2C8`). Cemu's
  recompiler treats `bl` as a call that must return. Don't use `bl +4`
  tricks in cave code.
- **Lookups**: before resolving an ID, the game's callers check
  `0x02BF3D8C(manager, id)` (object exists and is alive). The cave does the
  same for the target and for the owner. A failed resolve hands back a static
  placeholder (`*(0x10496740)` = `0x10496748`), which reads as not valid.
- **Crash bisecting**: `starcopy_cave.py --stage` 1, 1a, 1b, 1c, 2, 3, 4a,
  4 (see the docstring). Each one runs a bit more of the cave than the one
  before it. Results: everything up to counting the hits works.
  `copy_grant` called from the star's update crashed.
- **Root cause of the cave crashes: relocations inside the cave.** The dead
  function used for the cave (`0x037ED898`, 0xEA8 bytes) has **38 entries in
  `.rela.text`** (section 9) located inside it: `ADDR16_HA`/`LO` (types 6/4)
  and `REL24` (type 10). The loader applies them at load time and rewrites
  those spots in the cave code. For example, a `beq` at `0x037ED9C0` became a
  branch to garbage, and Cemu crashed executing `0x40E104C2` (`bca` to
  `0x4C0`). The earlier "no relocations" check only looked at relocations
  pointing *to* the function. Fix: `rpx_patch.py` argument
  `reloc:LO-HI=DUMMY` moves every relocation located in the cave onto its last
  word (`0x037EE73C`/`+2`), which is never executed. `starcopy_cave.py` emits
  it. Several earlier theories (`bl +4`, data relocation, Cemu register
  mix-up, `message+0xC`) were probably this same problem at different spots.
- **The same in reverse: a hook on a relocated word** (Kirby copy crash fix v3). A hook `bl` replacing an
  instruction that carries a relocation is rewritten by the loader too: `0x030C470C` `lwz r7, -0x5930(r8)` has an
  `ADDR16_LO` (addend `0x41A6D0`), so the `bl` put there got its low half set to `0xA6D0` and became
  `b 0x04BAEDDC` (zeros, no link): every Kirby match with a non-Kirby fighter hung while loading (exe_v44-v46). A
  static image or unicorn run of the patched RPX never sees it (the relocations are applied by the loader).
  `lis` / `addi` / `lwz` / `stw` with a `@ha` / `@l` of a data address, and calls to other modules, carry one;
  register forms (`lwzx`, `mr`, `cmpw`) don't. `rpx_patch.py` now refuses a patched word that a relocation would
  rewrite to something else: hook the next instruction (its use) or move the relocation with `reloc:` onto the
  cave's replayed copy.
- **Kirby's copy pools and new fighters' weapons** (crash fix v4). A copy's pool builder (`0x02EFDB88`) makes `max`
  instances of every record in the copy's list. A weapon_expand.py weapon's param getter reads its new owner's vl slot
  (`mgr + 0x25B0 + 4 x kind`), which is empty while that fighter isn't in the match. So a copy list holding another
  fighter's weapon (Mario's: the Kamehameha; Robin's: Hero's / Sephiroth's) crashed on gaining the copy
  (`lwz 0x160(0)`). `tools/kirby_copy_pool_cave.py` gives such a record 0 instances while its owner's vl is not loaded.
- **FighterParamManager vl pointers are never cleared** (crash fix v5). The constructor clears the reference counts
  (`mgr + 0x2730 + 4k` with kind_expand.py) but not the vl arrays, so a fighter that was never loaded has heap garbage
  in its slot (`0x9F16CDAC` in the user's log), not 0. "Is it loaded" is the reference count. A new kind's vl load
  loads its base's too, so code that runs as another kind (Kirby's copies granted as Robin's) needs that kind's vl:
  the Sephiroth copy (base Zelda, granted Robin) now loads Robin's with Sephiroth's (`kirby_copy_pool_cave.py`).
- **BattleObject return values**: the syscall (`0x030B2E48`) builds a message
  on its stack (`+4` kind 6, `+8` args, `+0xC` result = 0) and returns
  `message+0xC` to the MSC, not `r3`. Storing a value there from the star
  cave crashed the game on the first hit (cause not found), so the cave
  doesn't do that.
- **Grant from Kirby's own update.** The swallow code calls `copy_grant`
  while Kirby is the object being updated (from his own command handler),
  and it does more setup with him first. So the star cave now only hands the
  copy over:
  - on the 12th hit it stores kind + 1 in Kirby's int `0x1000009E` and the
    costume value in `0x1000009B`; the counter is `0x1000009D`;
  - these are copy ints (`0x83`–`0xA0`, cleared by `copy_grant` when it
    grants; the pending copy is read before that), unused by Kirby's MSC;
  - `0x100000A8`/`AA`/`AC` were tried first and didn't work: the writes were
    lost, so Kirby's int table probably ends at `0xA6` (the star's ID is
    stored there). Reads past the end seem to return 0 silently.

  Kirby's MSC main loop (`func_74` → `starcopy_update`) calls
  `BattleObject(0x40A)` while `0x1000009E > 0`. Case `0x40A` of Kirby's
  command dispatcher (`0x02EF94E4` = jump table `0x02EF912C` + `0x22`×4; it
  was first mislabelled as `0x409`, whose case is `0x02EF949C`; neither is
  used by his MSC) is patched to
  `b CAVE2` (`CAVE + 0x800`). In that case `r31` is Kirby's module accessor,
  the same object `copy_grant` takes. The cave clears `0x1000009E`, then
  calls `copy_grant(GETSPEC(0x104D1632, 8), accessor, costume, kind, 1)` and
  branches to the dispatcher epilogue (`0x02EF9688`).

## Transformation fighters (Mega Lucario armor / grab immunity)

Fighter kinds come from the name table at `0x102FF484` (kind = index from
`miifighter` = 0): Kirby `0x08`, Lucario `0x1E`, Giga Bowser (`koopag`)
`0x3A`, Wario-Man `0x3B`, Giga Mac (`littlemacg`) `0x3C`, Mega Lucario
(`lucariom`) `0x3D`.

Mega Lucario's MSC has no armor or grab code of its own. Its module calls
match a normal fighter's, and resetting the armor state from MSC didn't help.
So the behaviour is native.

Candidate: `0x02704F44`, a hit/collision result builder. It's called for
collision events `0x6010` (`0x0270A9A8`) and `0x6030` (`0x0270B368`), and from
`0x0270F00C`. It sets bit `0x800` in the result flags (`+0x10C`) when the
target's kind (`+0x18`) is `0x3A`, `0x3C` or `0x3D`. It skips Wario-Man,
who isn't armored. It also sets the bit when `+0x4C` == 4 or `+0x30` has bit
`0x2000`. The test patch `0x02704FD4: 2C00003D -> 2C007FFF` (`cmpwi r0, 0x3D`
→ `cmpwi r0, 0x7FFF`) takes Mega Lucario out of that check. The all-transformations version also patches
`0x02704FC4` (`0x3A`) and `0x02704FCC` (`0x3C`) the same way, so the check never matches.

Other kind helpers found along the way:
- `0x03058B8C`: returns 0 for kinds `0x3A`–`0x3D`, else 1. Called from
  `0x0275EC94`.
- `0x03058B6C`: returns 0 for `0x3A` / `0x3C`. Called from `0x02E159E8` and
  `0x034FC03C`.
- `0x030BF9C0` / `0x030C1FDC`: transform kind → base kind.

**Tested: the `0x02704F44` patch did NOT remove Mega Lucario's armor or grab immunity.** Go back
to the normal build.

### Armor ("no reaction") in the DamageModule

- DamageModule vtable around `0x10105B88` (8-byte entries: function, 0). The MSC `DamageModule`
  syscall (`0x030B2F8C`) goes through the module accessor's `+0x54` (DamageModule) and its
  vtable `+0x1E4`.
- `0x02C24AB0`: set armor (the MSC `DamageModule(0xB, mode, value)`). It calls
  `0x02C24D34(this+0x10, slot 0, mode, f1, f2, r6)`. `0x02C24AC4` resets it (`0x02C24D68`).
- `0x02C24D34(container, slot, mode, f1, f2, r6)`: the armor container has 16-byte slots at
  `+4 + slot*16` (mode, two floats, int). Slot 0 is the status armor that MSC sets. Slot 1 is
  set natively:
  - `0x02F05E6C` (`fighter_koopag.cpp` area): Giga Bowser, slot 1, mode 2 (knockback-based) with a
    param value.
  - `0x02F07270` (`fighter_koopa.cpp` area): Bowser's Tough Guy, slot 1, mode 2.
  - `0x02E1A170(fighter, on, r5, f1)`: slot 1, mode 1 (super armor), and bit `0x20000` in a
    status flag word. It's turned on through `0x02E47828` ← `0x02E51410` ← `0x036343F4`
    (looks like item / state code, not the transformations).
- Fighter object: `+0x74C0` = DamageModule (its armor container at `+0x10`), `+0x74D8` = effect
  module?, `+0x75A8` = a kind number used by `0x02E1A338`. `0x02E1A338` is called for kind
  `0x3C` / `0x3D` from `0x02E1B3F8` and looks scale / size related, not armor.
- The Mega Lucario specializer vtable is at `0x100977D0` (96 entries, functions around
  `0x027A1CB4`–`0x027A3xxx`). No direct armor or capture setter calls were found in it.

### Armor check (`0x02C24C88`) and the DamageModule command handler

- `0x02C24C88(container, r4, f1, f2)` = "no reaction?" It returns 1 if:
  - byte `container+0x25` is set (DamageModule `+0x35`; set by vtable `+0xCC` = `0x02C24ACC`),
  - or, with `r4 == 0`: byte `+0x24` is set, or word `+0` == 1 (flag; vtable `+0x10C` on /
    `+0x114` off; also `0x02C24DA4` directly from the fighter update `0x02E25710`),
  - or either slot (`+4`, `+0x14`; checked by `0x02C24BF4`) matches: mode 1 always, mode 2 when
    knockback <= threshold, mode 3 when damage <= threshold (`fcmpu`, the GT bit taken out: a value equal to the
    threshold is armored). The MSC command 0xB (case `0x02C2391C`) puts its value in the knockback threshold (f1,
    slot `+4`) for mode 2 and in the damage threshold (f2, slot `+8`) for mode 3; mode 0 clears the slot. Unicorn:
    `tools/edge_armor_test.py` (Sephiroth test 149: held Octaslash's `DamageModule(0xb, 3, 3.0f)`).
- DamageModule vtable base `0x10105B7C`. `+0x1E4` = MSC `DamageModule` handler (`0x02C2366C`,
  jump table for commands 0–0x13), `+0x1EC` = MSC float handler (`0x02C23C38`). MSC command 0xB
  only ever writes slot 0. Slot 1 is set natively (Bowser / Giga Bowser `0x02F07270` /
  `0x02F05E6C`, `0x02E1A170`). So MSC can't clear slot 1 or the override flags.
- Callers found: vtable `+0xCC` from `0x02B57054`, `0x031FDE6C`, `0x03437858`; `+0x10C` from
  `0x02C26188` (in `0x02C25F78`); `+0x114` from `0x02C75518`.
- **Diagnostic build** `build/armor_test/cross_f.rpx` (normal build plus):
  `0x02C24CA8=0x60000000` (ignore byte `+0x25`), `0x02C24CBC=0x60000000` (ignore byte `+0x24`),
  `0x02C24CC8=0x48000018` (ignore flag `+0`). Slots are untouched, so MSC armor and Bowser's
  Tough Guy still work.

**Result:** the diagnostic build removes Mega Lucario's armor, so his armor is one of the three
override flags, not a slot. Single-flag builds to narrow it down:
`build/armor_test_a` (only `0x02C24CA8`, byte `+0x25`), `build/armor_test_b` (only `0x02C24CBC`,
byte `+0x24`), `build/armor_test_c` (only `0x02C24CC8`, word flag `+0`). The word flag is
recomputed every frame in the fighter update (`0x02E25E3C`): on while the global battle state
(`[0x102F7024]+0x80`, `0x02E50320`) is 0 and `0x02C15EB8([fighter+0x74A4], 1)` returns 0.

**Result:** build A (ignore byte `+0x25`, i.e. DamageModule `+0x35`) removes Mega Lucario's
armor. The only fighter code that writes DamageModule `+0x35` is `0x02E175D0`, a timed fighter
state toggle (`r4` = on). Turning it on:
- sets `+0x35` = 1 (`0x02E176A0`, the armor);
- sets `[fighter+0x7520]+0x6E` = 1 (visual? module `0x020078D4`);
- sets status word bit `0x80000`;
- sets `[+0x74BC]+0x11F`;
- plays effect / sound `0x045F0008`;
- sends event `0x59` (`0x02C55B04`);
- starts a timer: 780 frames × a param, kept at `[..]+0xA0`. It's counted down in
  `0x02E22930`, and `0x02E441D4(player, 0)` turns the state off when it runs out.

`0x02E441D4` / `0x02E44770` turn it on per player. `0x02E17A60` restores it from saved state
bits (e.g. respawn).

**Fix:** `0x02E176A0=0x60000000` (don't set the no-reaction byte when the state turns on).
Build: `build/armor_fix/cross_f.rpx`. It's narrower than build A, which also ignored the byte for
non-fighter objects (`0x02B57054`, `0x031FDE6C`, `0x03437858`).

    python3 tools/rpx_patch.py build/cave_fix_s4/cross_f.rpx build/cross_f.rpx $(python3 tools/starcopy_cave.py) 0x02E176A0=0x60000000

Grab immunity is still unknown. It isn't the Final Smash state (`BattleObject(0x26)` every frame
didn't help), and the readers of bit `0x80000` checked so far (`0x0278BA48`: a sound choice,
`0x02E22930`: the state timer) aren't a grab check.

**Result:** `0x02E176A0` alone did NOT remove the armor, so something else also sets DamageModule
`+0x35` for Mega Lucario (probably a vtable `+0xCC` call my search didn't match; there are 36
`+0xCC` virtual calls in fighter code). **Use build A as the fix:** `0x02C24CA8=0x60000000`, so
the no-reaction check ignores byte `+0x35`. Slot armor (MSC `DamageModule(0xB)`, smash-charge
armor, Bowser's Tough Guy, Giga Bowser's slot 1) still works. What loses its armor: anything else
that used the `+0x35` byte (this fighter state, and the non-fighter objects at `0x02B57054`,
`0x031FDE6C`, `0x03437858`).

    python3 tools/rpx_patch.py build/cave_fix_s4/cross_f.rpx build/cross_f.rpx $(python3 tools/starcopy_cave.py) 0x02C24CA8=0x60000000

### Grab immunity (in progress)

- StatusModule: accessor `+0x20`, vtable base `0x1012D42C`. `+0x144` = MSC handler (`0x02E882AC`).
  `StatusModule(0x2713, a, b, c, d, e, ...)` packs its args into the status data word at
  StatusModule `+0xA0` (upper half = status kind). Bits: a → `0x8000`, b → `0x6000`,
  c → `0x1000`, d (grab immunity per the notes) → `0x800`, e → `0x400`. vtable `+0x104`
  (`0x02E885E8`) stores the data pointer at StatusModule `+0x58`. No direct reader of bit `0x800`
  was found (plain loads via `+0xA0` / `+0x58` / getter results).
- `0x02E175D0` is an item-style timed state. `0x02E44770` turns all such states off for a
  player (`0x02E441D4(player, 0)`). It isn't the transformation, so patching `0x02E176A0` didn't
  help.
- Test `build/grab_test/cross_f.rpx` = build A + the transform-kind patch in `0x02704F44`
  (`0x02704FC4` / `FCC` / `FD4` → `cmpwi r0, 0x7FFF`). The kind patch was first tested with the
  older `lucariom.mscsb` that didn't disable the Final Smash state every frame, so the two
  together are untested.

**Result:** `grab_test` (build A + the kind patch, with the per-frame `BattleObject(0x26)`) did
NOT remove the grab immunity.

### The status's attack log and staling (Core Breaker v6)

What the code and the data show:
- MSC `StatusModule(0x2713, a, b, c, d, e, f, g, h, i)` (handler `0x02E882AC`, exe_v46j) packs its values into the
  status data at StatusModule `+0xA0`:
  - the 6th, `f` (args `+0x18`), goes into `+0xA4` bits 31-12 (`rlwimi r30, r0, 12, 0, 19` at `0x02E883C4`);
  - `g` is bit-spread into `+0xA4` bits 11-0 and `+0xA8`;
  - `h` (`+0x20`) into `+0xA8`, `i` (`+0x24`) into `+0xAC`;
  - the previous status's words are kept at `+0xB4`-`+0xC4`;
  - vtable `+0x104` / `+0x10C` then take `+0xA0` / `+0xB4`.
- In Ultimate the same call is `FighterStatusModuleImpl::set_fighter_status_data(arousal, treaded_kind,
  disable_passive, ..., log_mask_flag, status_attr, power_up_attack_bit, ...)`. `f` sits where `log_mask_flag` is:
  the attack kind the move is logged under (the stale queue's entry) plus its category / trigger bits.
- The vanilla values read that way:
  - Mario's specials: 0x1412 side special (0x153), 0x1422 up special (0x154), 0x1442 status 0x156;
  - 0 for the neutral special (0x152: its fireball, an article, does the damage), 0x1 for the down special (0x155);
  - normal attacks: 0x832, 0x772 and so on; non-attacks: 0.
  - Mario's own up special (`func_2286`, status 0x154) logs 0x1422, but 0 for custom move 2 (Super Jump,
    `0x1000004a` = 1, a no-damage version): the game's own way of leaving a move out of the log.

Applied: Core Breaker (Supamario's 0x154) always passes 0, so its hits aren't logged (they don't stale and aren't
staled). This covers every Core Breaker hitbox: catch, body, detection, burn, crash, explosion; all are in that
status.

**Not proven to the instruction:** a scan for code reading `+0xA4 >> 12` (`lwz 0xa4` then `srwi 12`) found nothing.
The reader goes through the data pointer, so the stale queue's use of the field isn't traced. The in-game check:
repeat Core Breaker on a training dummy; with staling the dive's 3% and the crash's 17% would drop after a few uses.
There is no hitbox field for it: the Special_Hitbox fields in reference/spreadsheets (Hitbox sheet) have none, and the
staling factors are per fighter in `fighter_param_etc` group 3 (0.05, 0.08, 0.07594, ...).

### Fighter specializer vtables (98 entries, 8-byte stride)

These are per-fighter tables, e.g. lucariom `0x100977D0`, littlemacg `0x1009710C`, koopag
`0x10136F30`, warioman `0x1009D484`. Fighter kind table: name list at `0x102FF484`, kind =
index − 2 (Kirby 8, koopag `0x3A`, warioman `0x3B`, littlemacg `0x3C`, lucariom `0x3D`). Each
fighter has its own stub functions, so comparing stub bodies slot by slot across all 62 tables
shows:
- **Slot 70** (`+0x230`): `li r3, 1; blr` for 58 fighters, `li r3, 0; blr` for exactly the
  four transformations (`0x027A4570` lucariom, `0x0279EE90` littlemacg, `0x02F05B14` koopag,
  `0x027DCA40` warioman). Candidate for "can be grabbed".
- Slot 74 returns a fighter-specific code (`0x7FAD` etc.), slot 93 is 4 for warioman.

Test `build/grab_test2/cross_f.rpx` = build A + slot 70 → `li r3, 1` (`0x38600001`) for all four.

**Result:** slot 70 → 1 did NOT remove the grab immunity. Slot 70 is the specializer hook called
from `0x02E15E28` (inside `0x02E15DE4`). The specializer hooks are called one per fighter method,
via `[fighter+0x7538]` vtable `+0xC + 8*slot` (list from the call scan: `0xC` at `0x02E137D0` …
`0x30C` at `0x02E281F8`).

Also ruled out for grabs:
- lucariom's per-status grab-immunity flag (`StatusModule(0x2713)` 4th value) matches Meta
  Knight's for every common status;
- `0x02715D04` (kind `0x3A`–`0x3D` range check) is AI code (called from `0x02DF4F06`);
- the bit-`0x800` testers on the fighter flags word (`0x02E24378`, `0x02E2A008`) are a timed
  state.

Grab immunity is still unknown. The standard build stays build A (armor fix only).

### Grab debug build (Cemu breakpoint)

- Fighter StatusModule vtable `+0x2C` = `0x02E88810` "change status to `r4`" (it also stores the
  request at `+0x54`). MSC `StatusModule(3, kind, …)` → base handler `0x0200D8FC` stores `+0x54`.
  CapturePull = status `0x3F`; CatchPull = `0x36`.
- `build/grab_debug/cross_f.rpx` = build A + a hook. `0x02E88810` → `b 0x037EE6A0` (free space
  at the end of the star cave):
  `cmpwi r4, 0x3F; bne +8; nop (breakpoint 0x037EE6A8); stwu r1, -0x30(r1); b 0x02E88814`.
  The patch list is in `docs/grab_debug_patch.txt`. On a normal grab the breakpoint hits with
  LR = the code that requested CapturePull; the stack back chain gives the callers above it.

**Result:** trap A (`0x02E88810` with `r4 == 0x3F`) did not hit on a normal grab, so CapturePull isn't
requested through that function. Second debug build adds trap B: the fighter status setup handler
(MSC `StatusModule(0x2713)`, `0x02E882AC`) gets the new status kind from vtable `+0x8C` at
`0x02E88354`. The hook at `0x02E88358` → `0x037EE6C0`:
`cmpwi r3, 0x3F; bne +8; nop (breakpoint 0x037EE6C8); lwz r4, 0(r30); b 0x02E8835C`.
This hits while the grabbed fighter's CapturePull setup script runs. Sanity breakpoint:
`0x037EE6C0` runs on every status change of every fighter. Patch list:
`docs/grab_debug_patch.txt`.

**Result:** trap B hit on a normal grab (LR was just `0x02E88358`, the vtable call's return).
Debug build 3 moves trap B to `0x037EE600`. On `r3 == 0x3F` it walks the stack back chain (16
frames) and copies each frame's saved LR (`[frame+4]`) to `0x037EE6E0`–`0x037EE71F`. Breakpoint
after the walk: `0x037EE63C`. Trap A is unchanged.

## Grab-immunity fix test (build/grab_fix/cross_f.rpx)

Fighter update 0x02E25710 sets HitModule catch-enable every frame (bl 0x2C42F50 with r4):

```
0x02E25288 lwz   r0,0(r7)          ; fighter flags word
0x02E2528C rlwinm r0,r0,0,4,4      ; test 0x08000000 ("forced not catchable")
0x02E25290 addic r5,r0,-1
0x02E25294 subfe. r9,r5,r0         ; CR0 = (bit set)
0x02E25298 li    r4,0
0x02E2529C bne   skip              ; bit set -> catch disabled
0x02E252A0 ... r4 = !(status data & 0x800)   ; normal grab-immunity bit
```

The 0x08000000 bit is set by 0x02E1CD54 (`oris r6,r9,0x800` at 0x02E1CE84)
when its mode argument is > 3, which the transformation finals use.

Patch: `0x02E2528C=0x38000000` (`li r0,0`), so catchability always follows the
status-data grab-immunity bit. Build = starcopy cave + patch A + this patch:

```
python3 tools/rpx_patch.py build/cave_fix_s4/cross_f.rpx build/grab_fix/cross_f.rpx \
  $(python3 tools/starcopy_cave.py) 0x02C24CA8=0x60000000 0x02E2528C=0x38000000
```

Fallback if this doesn't work: `0x02E1CE84=0x61260000` (`ori r6,r9,0`) so the bit is never set.

**Result:** `0x02E2528C=0x38000000` made Mega Lucario freeze permanently during his
transformation. The bit is also set by the dead/rebirth-style code (`0x02E1CA64`, together with
catch off), so the transformation probably goes through that path, and being catchable during
it breaks the sequence.

**Second try (narrow):** `tools/transform_grab_cave.py` hooks both readers of the bit
(`0x02E2528C` → cave `0x037EE600`, `0x02E28D50` → cave `0x037EE63C`). The bit is ignored only when
the fighter kind (`[fighter+4]`) is `0x3A`–`0x3D` AND the current status kind
(`[[fighter+0x7494]+0x48]`) is outside `0x139`–`0x151` (the special common statuses: entry,
rebirth, final, dead). Everyone else is unchanged.

    python3 tools/rpx_patch.py build/cave_fix_s4/cross_f.rpx build/grab_fix/cross_f.rpx \
      $(python3 tools/starcopy_cave.py) 0x02C24CA8=0x60000000 $(python3 tools/transform_grab_cave.py)

**Result:** no freeze, but Mega Lucario still couldn't be grabbed. Site 2 (`0x02E28D50`, in the
status-change function) also needs flags `+4` bit `0x20000`, which only the post-respawn timer
(site 1, `[..+0xC]+0x160` counting down) sets. The transformations never run that timer.

**Third try:** for kinds `0x3A`–`0x3D` outside statuses `0x139`–`0x151`, the site 2 cave now
skips both checks (whatever the 0x08000000 bit is) and jumps to `0x02E28D78`
(catch = !(status data & `0x800`)). The catch state is set on every status change, so they
become grabbable from their first normal status after the transformation.

**Result:** confirmed, Mega Lucario can be grabbed (and doesn't freeze). This is now the
standard build (`build/cross_f.rpx` = starcopy cave + patch A + `transform_grab_cave.py`).
Giga Mac, Giga Bowser and Wario-Man use the same kind range but are untested.

**Known issue (won't fix):** with armor and grab immunity gone, the game can crash if a
transformation detransforms during some hit states, and Giga Mac / Giga Bowser sometimes handle
hit states oddly. In the user's setup these characters never detransform, so this is left as is.

## Kirby copy abilities: custom neutral specials (test build build/copy_custom/cross_f.rpx)

- WorkModule special-param loader `0x02F1BF88(WM, r4)`: for each special it copies the param
  block of the fighter's custom slot, e.g. N: src = `[[mgr+kind*4+0x111C]+0xFC]` +
  custom(`0x10000048`) * `[WM+0x1578]`*4 → `WM+0xD30` (S: `+0x110`, `0x10000049`, `+0x1594`, …).
  `WM+0x18` = fighter kind, param manager = `[0x102FF448]` (`lis 0x1030; lwz -0xBB8`).
- For Kirby it then calls `0x02F1B8B0`: if copy kind (`0x100000A4`, = the copied fighter's kind)
  < `0x3A`, it overwrites `WM+0xD30` with the copied fighter's N block, always variant 0:
  src = `[[mgr+copy*4+0x111C]+0xFC]`, size = byte table `0x02EA9104(copy)` (`0x1012F6BC+kind`:
  Bowser 96 = 24 values, Kirby 136). Variants follow each other with that stride.
- Swallow → copy: `0x0279666C`; at `0x02796900` (just before `copy_grant 0x02EFCD8C`) r24 =
  victim's module accessor, r26 = copy kind, r25 = costume, r31 = Kirby's accessor.
- `copy_grant` (`0x02EFCD8C`) clears Kirby ints `0x83`–`0xA0`, writes the copied costume to int
  `0xA5` (`stw r27, 0x294`) and the copy kind to `0xA4` (`stw r28, 0x290`, after the clear).
  **First test used `0xA5` for the slot and got the costume → always a "custom" variant.**
- `tools/copy_custom_cave.py`: CAVE_A (`0x037EE680`, hook `0x02796900`) stores the victim's
  `0x10000048` (a swallowed Kirby: its `0x1000009F`) in Kirby's int `0x1000009F` before
  copy_grant; copy_grant's clear count (`0x02EFCE14`, `li r11, 0x1E`) becomes `0x1C`, so it clears
  `0x83`–`0x9E` and `0x9F`/`0xA0` survive. CAVE_B (`0x037EE6E0`, hook `0x02F1B910`) adds
  slot * size to the copy loader's source.
- **Second test** wrote `0x9F` after copy_grant returned: hitboxes matched, params didn't, so
  the params are loaded inside copy_grant (after the clear and the kind write).
- Weapon custom number: generated weapons take it from the init struct (+0x5C, filled at
  `0x02F062C0` from the owner's int `0x10000048` = `[int array]+0x120`). It picks the weapon's
  param block (getter per weapon, e.g. Bowser breath `0x031ABB8C`: `[koopa]+0x150` + custom*0x14 =
  life / hit frames / speeds) and its motion (ACMD variant, via the weapon's `0x10000005`).
  Found with a Cemu breakpoint on `0x031ABB8C`: LR `0x02BCC414` (`0x02BCC3BC`, r5 = custom) ←
  `0x02B61A94` (`(s8)[init+0x5C]`) ← `0x02C073DC` ← `0x02F062D8`. CAVE_C (`0x037EE400`) uses
  Kirby's `0x9F` there when Kirby (kind 8) has a copy. In that function r26 is not the fighter
  base (its WorkModule is at `r26+0x726C`), so the kind comes from `[[r26+0x726C]+0x18]`; v4
  read `[r26+4]` and never fired (the user saw base hitboxes / lifetime with custom params). (The first MSC fix, switching the
  breath article's motion with `ArticleModule(0x2715)`, only fixed the hitboxes.)
- Effects / sounds: Kirby's Bowser copy runs Bowser's own ACMD (`MotionAnimcmdModule(0, 0, motion,
  0xF)`, kind `0xF` = koopa) for motions `0x211`/`0x215`/…; each has 4 slots, so Kirby's MSC uses
  motion + slot (`copy_custom_motion`, in `func_2863` / `func_2864`). Now every copy does this
  (below).
- Star-missile copies: the star cave (`starcopy_cave.py`, 12th hit) writes the hit fighter's
  `0x10000048` to Kirby's `0x9F` before it hands the copy over. Confirmed working.
- **Weapon spawners**: every weapon kind has its own spawner, named by its article record
  `{kind, max count, spawner, extra}` (`reference/FighterArticles.xml`: CountAddr - 4 / + 4). Kirby's
  copies use the copied fighter's records (Kirby's copy tables, `0x10135000`-`0x10136D20`), so the
  copied fighter's spawner runs with Kirby as the owner. CAVE_C's hook (`0x02F062C0`) is in Bowser's
  breath spawner (`0x02F0601C`, kind `0x5F`), not a shared one. 36 of the 329 spawners (357 calls to
  the weapon create `0x02C073A8`) read the owner's `0x10000048` themselves (`lwz rX, 0x120(int
  array)` into the init block's `+0x5C`), so on Kirby they read his own Inhale custom; 32 reads are
  in spawners his copy tables use (31 fighters' neutral-B weapons: Mario / Luigi fireball, Samus
  charge shot, Dr. Mario capsule, Link / Toon Link bow and arrow, Pit / Dark Pit arrow, Pikachu Thunder
  Jolt, Ness PK Flash, Lucas PK Freeze, Sheik needles, Falco blaster, ZSS paralyzer, Peach Toad,
  Lucario aura sphere, Mewtwo shadow ball, Game & Watch chef, Olimar Pikmin (2 reads), Dedede star
  (2), R.O.B. beam, Charizard breath, Wii Fit sun salutation, Robin thunder, Duck Hunt can, Bowser Jr.
  cannonball, Greninja shuriken, and Kirby's own Rosalina-copy Luma shot), plus Kirby's star missile
  (left alone). `copy_custom_cave.py` `SPAWNERS` gives each of them CAVE_C's check (owner Kirby with a
  copy: the copied slot `0x1000009F`). Per site: the owner register (forward dataflow from r4 at
  entry, matching the int array's `[[[OWNER+0x726C]+8]+0]+0xC` chain), a volatile scratch register
  and cr0 dead on every path from the hook to the create call (a path-following liveness pass). Hooks
  below `0x02B00000` use the Havok cave (`0x037EE400`-`0x037EE4DC`), the rest the grown code space at
  `0x04B9E000` (`trail_table_cave.py`'s limit lowered to it). Diddy Kong's gun / peanuts / explosion
  spawners leave `+0x5C` at the init block's 0 (as for Diddy himself), and the weapon init
  (`0x02B61A64`) has no fallback, so his variants come from the neutral-B params (CAVE_B: already the
  copy's). Unicorn test: `tools/copy_custom_cave_test.py` (every site, 4 owners each, no register
  other than the result and the scratch changed).

    python3 tools/rpx_patch.py build/cave_fix_s4/cross_f.rpx build/copy_custom/cross_f.rpx \
      $(python3 tools/starcopy_cave.py) 0x02C24CA8=0x60000000 $(python3 tools/transform_grab_cave.py) \
      $(python3 tools/copy_custom_cave.py)

Star missile max count: `0x10136C58=9` is added to that command (the base `cave_fix_s4` has 5).

**Result (v5):** confirmed: Kirby's Bowser copy matches the swallowed Bowser's custom Fire Breath
(params, projectile lifetime, hitboxes, effects). This is now the standard build:

    python3 tools/rpx_patch.py build/cave_fix_s4/cross_f.rpx build/cross_f.rpx \
      $(python3 tools/starcopy_cave.py) 0x02C24CA8=0x60000000 $(python3 tools/transform_grab_cave.py) \
      $(python3 tools/copy_custom_cave.py)

(Current standard build adds `0x10136C58=9 $(python3 tools/kirby_stat_cave.py)
$(python3 tools/position_vars_cave.py) 0x02EF74A8=0x60000000` at the end; see "WorkModule stat
reads", "Position variables" and "Losing the copy when hit" above.)

    python3 tools/rpx_patch.py build/cave_fix_s4/cross_f.rpx build/cross_f.rpx \
      $(python3 tools/starcopy_cave.py) 0x02C24CA8=0x60000000 $(python3 tools/transform_grab_cave.py) \
      $(python3 tools/copy_custom_cave.py) 0x10136C58=9 $(python3 tools/kirby_stat_cave.py) \
      $(python3 tools/position_vars_cave.py) 0x02EF74A8=0x60000000 $(python3 tools/strike_cave.py) \
      $(python3 tools/copy_fx_cave.py)

(Then `$(cat build/marthsword/rpx_args.txt) $(python3 tools/stage_slot_cave.py)
$(python3 tools/copy_held_cave.py)`: the Marth copy sword aerials' motion tables, the new stage slot,
and the copy held model shown in those aerials; see `fighters/kirby/specials.md`. Then
`$(python3 tools/stage_script_cave.py) 0x0311CE50=0x38600001`: stage scripts and My Music group
names read from `bgm_mymusic.mmb`; see `docs/minecraft-world.md`.)

Other copies: the native part (params, weapon custom number) is generic. The body ACMD is picked
by MSC: every copy's pair of motion helpers (`[Copy: shared] helper`, e.g. Captain Falcon
`func_2785`/`2786`, Little Mac `func_3653`/`3654`) calls `MotionAnimcmdModule(0, 0, motion, kind)`
with the copied fighter's own motion number, and all of them now go through
`copy_custom_motion(motion, kind)` = motion + custom slot (except the Mii Fighters, kinds 0-2).
That relies on the motion list layout: each special motion has 4 entries in a row, default /
`_c2` / `_c3` / one more. Checked in Captain Falcon's `motion.mtable` (`0x211` specialn, `0x212`
specialn_c2, `0x213` specialn_c3, `0x215` specialnturn, ...; also side / up / down B), and it
matches Bowser's (confirmed in game) and Little Mac's motion numbers (`0x22D`, `0x231`, ... step 4).
Fighters without customs (DLC) always have slot 0. Copies that read the custom slot themselves
(weapon articles: `copy_custom_article`) are separate.

## Fighter jump init (0x02E79940)

Horizontal: `0x300000D`/`0x300000E`/`0x300000F` (jump x speed, ×, max). Vertical speed:
attribute `0x300015F` (full hop) or `0x3000160` (short hop, when status flag `0x21000005` is
set; Kirby's JumpSquat sets it from `0x2000004C`, and the Jump status picks the JumpMini motions
`0x1A`/`0x1C` from it), × work float `0x1000006`. Flag `0x21000012` picks a different getter
(`0x02F1D940`). Used by Kirby's superjump (`crouchjump_update`).

## WorkModule stat reads (copy-ability trait boosts)

- `WorkModuleImpl` (`app\battle_object\modules\work\work_module_impl.cpp`, code around
  `0x0200E500`–`0x02010600`) is the only WorkModule class; its vtable is `0x10003224` (entries every 8
  bytes, function at `+4+8k`): `+0x44` get_float `0x0200F628`, `+0x4C` set_float `0x0200F648`,
  `+0x84` get_int `0x0200F7F0`, `+0x8C` set_int `0x0200F810`, `+0xE4` is_flag `0x0200FA38`.
  Constructor `0x0200E520` (0x1C bytes); init (`+0x14`, `0x0200E5C0`) takes the category table.
- Values: `[WM+8]` = table of category containers, index = `id >> 24 & 0xF` (0/1 = instance/status
  work, 2 = fighter_param_common, 3 = fighter_param, 5–8 = specials...). A container is
  `+0` float count, `+4` floats, `+8` int count, `+0xC` ints, `+0x10` flag count, `+0x14` flags (counts
  in entries, top 2 bits are flags; cleared by `0x0200FD9C` → memset-like `0x04AE0B14`). get_float is
  `[[container]+4][(id & 0xFFFFFF)*4]` with no checks; set_float writes the same way.
- Native movement code reads stats through vtable `+0x44` too (e.g. jump init `0x02E79940` reads
  `0x0300000D`/`E`/`F`), so hooking get_float covers native and MSC reads, as long as every
  class's copy is hooked (fighters: `0x02F1DBE4`; see "Position variables").
- Category 3 (`fighter_param`) is the character's entry of the shared table (one per kind, per the
  MSC note sheet), so it isn't rewritten per Kirby; `tools/kirby_stat_cave.py` scales on read instead
  (`docs/character-traits.md`). Cave at `0x037EE160`, table after it; hook `0x0200F628 = b cave`.
  Tested in an emulator (Unicorn) against fake WorkModules; not yet in game.
- Stat names: `reference/fighter_param_attributes.csv` (Sammi Husky's sheet from
  `docs/resources.md`, tab "706249581").

## Position variables (WorkModule float category F)

`tools/position_vars_cave.py`; user docs in `docs/position-variables.md`.

- **Target 12, "the fighter this attack hit" (exe_v46k, ACMD position commands v1).** Asked: can target 2 / its
  variables (`0x0F000055`-`57`, ...) be cleared? Target 2 = the newest hit record of self's attack (AttackModule
  `+0x50`: `+0x4C` records on, `+0x18` hitbox count, `+0x14` hitboxes of `0x174`, list `+0x124` / first node `+0x128`,
  node `+0x18` object ID), else (`ext_last_fb`) the fighter whose int `0x10000065` (last attacker, also the KO
  credit: not ours to wipe) is self's slot. Target 12 is the same walk with no fallback: `nb_entry` (IDs
  `0x2C8`-`0x2FF`, past the ACC block, where `inp_entry_acc` used to give 0) stores the mirrored family's quantity
  code and enters `ext_t_last_pre` with r22 = 12; `ext_last_fb`'s first word (`li r22, 0`) is now `b nb_fb`, which
  gives nobody for 12 (r22 is untouched by `ext_t_last_pre` / `ext_t_last` / `slot` / `ext_msc`). Two words of the
  old code change (`0x04B79360`, `0x04B79974`), the rest is new
  at `NB_CODE` `0x04B7AE00` (EXT_REGIONS' second region cut to end there: pack()'s placement is unchanged, checked
  word for word against exe_v46j). The ACMD side (`acmd_ext_cave.py`): `nc_tid` 12 -> 12, `nc_target` reads ACC
  `0x2FB`, `vid` goes through `nc_vid` (target 12: `NB_MAP` from target 0's ID), `in_id`'s first word branches to
  `in_id_x`. `Position_Place` / `Position_Offset_Get` and the holds: `apc_code` at `0x04B7B000`
  (docs/acmd-extra-commands.md). Not tried in game yet: the record timing (the hit's records exist from the frame
  after the hitbox's) is the same as target 2's.

- **WorkModuleImpl has four subclasses with their own copies** of get / set / add / sub / mul / div
  float (identical code): vtables `0x10003224` (base), `0x100F93CC`, `0x1012132C`, `0x1013A1C0` /
  `0x1013AFFC` (**fighters**: get `0x02F1DBE4`, set `0x02F1DC04`), `0x10153184` (all share the MSC
  handler `+0x1CC` `0x0200E898`). Hooking only the base copies did nothing for fighters: the stat
  cave never ran for them, and SET_FLOAT on `0x0F00000C` wrote into the missing category-F float
  table and crashed. Both caves now hook every copy (`CLASSES` / `HOOKS`).
- Float IDs `0x0F0000xx` (category F; the game's MSC uses float categories 0–9 only, and ints in
  category F) are answered by the cave instead of the WorkModule tables. Hooks on the first
  instruction of each copy of get_float (base `0x0200F628`; other IDs → the stat cave), set_float
  (`0x0200F648`), and add / sub / mul / div float (`0x0200F73C` / `0x0200F764` / `0x0200F78C` /
  `0x0200F7B4`) (vtable `+0x64`/`+0x6C`/`+0x74`/`+0x7C`; these edit the tables in place, so for these
  IDs they become a read plus a write). Only index < 0x100 is taken; other category F floats go to
  the original code.
- MSC `WorkModule(op, value, id)` (syscall 0x16 → WM vtable `+0x1CC`, handler `0x0200E898`): op 0 =
  set float (`+0x4C`), 1 = random (`+0x5C`, calls set_float), 2 add, 3 sub, 4 mul, 5 div, 6 get int
  (`+0x84`), 7 set int (`+0x8C`)... `WorkModuleF(0, id)` = get float.
- Fighter table: `[[0x1035184C] + 0]` (the object resolver `0x02BF205C` uses `[0x1035184C] + cat*4`):
  `+0` entries, `+8` count; entry = entries + slot × `0x76B0` (`0x02BF4A88`), `+0` object ID, byte
  `+0x1E` ≥ 4 = live (`0x02BEF61C`), `+0xC` module accessor (`0x02BEF5DC` reads `[handle]+0xC`).
- Accessor `+0x18` PostureModule, `+0x28` WorkModule. The WorkModule has no owner pointer, so
  "self" = the live entry whose accessor's WorkModule is the one being read.
- PostureModule: position `+0x10`/`+0x14`/`+0x18`, facing `+0x60`; vtable `+0x4C` set_pos(this,
  vec3*) (fighter version `0x02E5CDD8` stores the three floats, then updates when they changed).
- Code at `0x037EDC78` (reads/writes) and `0x037EE280` (add/sub/mul/div). Tested in Unicorn with
  fake fighter tables and the game's own WorkModule code for the other IDs. Every pointer the cave
  follows is range-checked (data 0x10000000–0x4FFFFFFF, code 0x02000000–0x09FFFFFF, word aligned);
  a bad one reads 0 / skips the write instead of crashing.
- **ACMD handlers:** table of function pointers at `0x10350ED8`, indexed by the command index the
  loader puts in place of the CRC (`0x02BEE154`, CRC → index table `0x100FAAB8`; the executor
  near `0x02BEE6F0` reads the table). Handlers get r3 = module accessor, r5 = script state,
  r6 = flags (`lbz 8(r6)`), r7 = the command's parameters. SET_FLOAT (`0x1D7`, `0x02BDA054`)
  builds `WorkModule(0, value, var)` and calls the WorkModule MSC handler (vtable `+0x1CC`) →
  set_float, and Float_Var_Compare (`0xC8`, `0x02BE6730`) calls get_float, so both reach the
  position hooks. Some other handlers read float variables **inline** from the WorkModule tables
  (e.g. IT_CREATE `0x02BE97A0`, IT_CREATE_ANGLE `0x02BE9880`), which the hooks don't see: don't
  pass `0x0F0000xx` to those. ADD_FLOAT `0x02BE6E80`, SUB_FLOAT_2 `0x02BDA100`,
  Add/Set_Momentum `0x02BD7FA4`.

## Combat variables (hitstun / hitstop / last fighter hit)

`tools/position_vars_cave.py` (IDs `0x0F000040`–`0x0F000097`, user docs in
`docs/position-variables.md`). The hooks send every `0x0F0000xx` to `var_entry`, which keeps
indices < 0x40 in the position code and sends the rest to `ext`.

- **Running MSC commands on another fighter:** every MSC module syscall wrapper (table
  `0x104187A0`) is `wrapper(ctx, args)`, reading only `ctx+4` = module accessor, then calling the
  module's MSC handler with `args` = `{u32* words, count}`; the result is in r3 (float bits for the
  `F` variants: e.g. WorkModuleF's handler `stfs f1, 0xC(r1); lwz r3, 0xC(r1)`). So a fake
  context whose +4 is another fighter's accessor runs that command on that fighter
  (`ext_msc`). Wrappers used: WorkModule `0x030B2B28`, DamageModule `0x030B2F8C`, DamageModuleF
  `0x030B2FC4`, StopModule `0x030B5160` (accessor `+0x48`, handler `+0xAC`), ShakeModule
  `0x030B5C50`.
- Hitstun left = int `0x1000003E` (the Damage statuses count it down; the game itself rescales it,
  e.g. Kirby `func_888` / `func_905`); hitstun of the last hit = `DamageModuleF(1)`; hitstop of the
  last hit = `DamageModule(8)`; `StopModule(1)` = in (non-moving) hitlag; `StopModule(2, n)` =
  hitlag for n frames; `ShakeModule(0, mode, frames, 0, 0, intensity)` = hit shake.
- Last fighter hit: the attack module's hit records (see "Collision records"), first non-empty
  hitbox list, a fighter ID other than self (`id >> 28 == 0`, slot `(id >> 16) & 0xFFF`). With the
  records off (`AM+0x4C == 0`): a fighter whose int `0x10000065` (last attacker's player number,
  used for the hit effects' colour) equals self's fighter-table slot.
- **Code space: grow `.text`.** `.text` (section 2) ends at `0x04B77E1C`, but the RPL file info's
  text region (`textRegionSize` 0x2BB8670 from `0x02000000`) reaches `0x04BB8670`, and Cemu
  (`rpl.cpp`) allocates, maps and recompiles the whole region (trampolines live elsewhere, in the
  lower code area). `rpx_patch.py grow:0x04B79000` extends `.text` with zeros up to there (it still
  recompresses into its slot in the file; otherwise the section is moved to the end of the file),
  and the combat variables' code sits at `0x04B78000`. `pack()` spreads the code blocks over the free
  regions and turns branches between blocks into `.far` (inverted short branch + `b`).
- **Not dead: `0x04AD2164` is the RPX entry point** (ELF `e_entry`), run by the loader at startup;
  the first version of the combat variables wrote code there and the game crashed on launch at
  `0x04AD2178`. A function with no calls or relocations can still be the entry point (check
  `e_entry`). `0x04AE6258` (0x234) and `0x037EE858` (0x124) do look unused but aren't used now.
- **Hitstun × for a move's hits** (`0x0F000052`): writing it stores (multiplier, StatusModule(0)) for
  the writer's slot in `hs_pending` (in the grown `.text`, zero at load). `set_int` of every WorkModule
  class (`0x0200F810`, `0x02BCDA88`, `0x02DA6208`, `0x02F1DDCC` fighters, `0x03060A68`; `set_int(this,
  value, id)`) is hooked: when a fighter's int `0x1000003E` is set to the hit's own hitstun
  (`(int)DamageModuleF(1)`, what the Damage status init writes; later rescales like Kirby `func_888`
  don't match), the attacker is the fighter whose attack's hit records hold the victim, and if its
  multiplier is set and it's still in the same status, the value is multiplied; a stale one is cleared.

## Controller (ControlModule) and the input / state variables

`tools/position_vars_cave.py`, IDs `0x0F000100`–`0x0F00025F` (user docs: `docs/position-variables.md`
"Inputs and state"). The hooks now take category-F indices < `0x400`; `var_entry` sends `>= 0x100`
to `inp_entry`. Code in `.text` grown to `0x04B7C000` (`0x04B79000`–`0x04B7C000`).

- **ControlModule:** accessor `+0x24`. Classes: ControlModuleImpl (vtable `0x10104D3C`, 0xB4 bytes,
  `control_module_impl.cpp`, code `0x02C1B000`–`0x02C1F000`), another `0x101053DC`, fighters'
  `0x1012B30C` (`0x02E7xxxx`). MSC handlers: int vtable `+0x2F4` (`0x02C1C7D0`, ops 0–`0x1E` and
  `0x2710`–`0x2727`), float `+0x2FC` (`0x02C1D53C`, ops 0–8). `+0xA0` → the controller struct
  (inline at `+0x10`), `+0xA4` the pad source (an object with vtable: `+0x1C` prepare, `+0x24`
  stick (r3 / r4 float bits), `+0x34` buttons, `+0x3C` triggers, `+0x7C` C-stick), `+0xA8` flips
  stick X for ControlModuleF(0) / (7).
- **Struct** (class with vtable `0x100006B0` at `+0x8C`, constructor `0x02003314`): `+0` / `+4` stick
  X / Y (X screen-space: + = right), `+8` / `+C` last frame's, `+0x30` analog shield, `+0x3C` held
  buttons, `+0x40` last frame's, `+0x48` pressed this frame, `+0x4C` released, `+0x50`… per-button
  frame counters, `+0x70`… stick flick counters, `+0x7C` / `+0x80` C-stick X / Y.
  ControlModule(`0x2710` / `0x2711` / `0x2712` / `0x2713`, button) = pressed / released / held /
  not held; ControlModuleF(0, 1) stick, (7, 8) C-stick.
- **Button bits** (MSC button → bit, table `0x10000670`): 0 attack `0x1`, 1 special `0x2`, 2 jump
  `0x4`, 3 shield `0x8`, 4 smash (A+B / C-stick) `0x20`, 5–8 d-pad up / down / left / right `0x400`
  / `0x1000` / `0x2000` / `0x4000` (taunts), 9 grab (Z) `0x10`, 10 / 11 C-stick `0x40` / `0x80`,
  12 `0x8000` (the tap jump setting is on: the input frame carries it), 13 `0x100` (A and B both
  held), 14 `0x200` (attack, not taken by A+B smash), 15 `0x800` (special, ditto). See "Controls
  settings and input frames" for where they come from.
- **Update** `0x020035FC(struct, source, accumulate)`, called by the fighter control module's
  `0x02E729E4` (twice when accumulating). It reads the source and derives presses, releases and
  flicks from the result, so the hooks change the read values: buttons after `+0x34`
  (`0x0200379C` / `0x02003810`), stick after it's stored (`0x02003750` / `0x020037BC`), C-stick at
  the epilogue (`0x02003DBC`). The hook sites branch to trampolines in the first cave (only there are
  they in reach), which jump to `inp_far`. Per-slot forced state (`inp_state`, 0x20 a slot: held,
  tapped, inputs off, sticks-forced bits, stick / C-stick values) is cleared in status `0xB1`
  Dead, `0xB2` Rebirth, `0x14F`–`0x151` Entry / Win / Lose. The update uses paired-single
  saves (Unicorn can't run them: the emulator test nops them) and calls sqrt at `0x02000AE0`.
- **State:** situation = StatusModule(1) / (2, value). Damage = DamageModuleF(0); DamageModule(9, %)
  adds (negative heals; the counter updates). Jumps: ints `0x10000001` used / `0x10000002` max.
  Shield health: float `0x3` (WorkModuleF wrapper `0x030B2B60`). HitModule (accessor `+0x58`,
  wrapper `0x030B50B8`, vtable `0x10107774`): state sets at `+0x40` (0x38 each): `+0x1C` the status's
  body state (op 0), `+0x24` intangible frames (op 2), `+0x28` invincible frames (op 1), `+0x20`
  their result (2 / 1 / 0); vtable `+0x10C(this, 0)` = max of the two. DamageModule (accessor
  `+0x54`): armor op `0xB(type, threshold)` → `+0x14` type, `+0x18` knockback threshold, `+0x1C`
  damage threshold.
- Float_Var_Compare / the compare functions (`0x02BEE010`, table `0x10351804`): method 0 `==`,
  1 `!=`, 2 `<=`, 3 `>=`, 4 `<`, 5 `>`.

## The input buffer (exe_v46l: Buffer_Clear / Buffer_Set)

Read from the fighters' ControlModule code (class vtable `0x1012B30C`, accessor `+0x24`; MSC handler `0x02C1C7D0`,
op table `0x02C1C850` for 0-0x1E and `0x02C1C8EC` for 0x2710-0x2727, vtable entries 8 bytes, the function at +4).

- **Where it's built.** The control update `0x02E729E4` (per fighter, every frame it reads its pad) runs the
  controller struct update `0x020035FC(cm + 0x10, ...)` (presses / releases / flicks, where position_vars' forced
  inputs go in), then at its end: `+0x1B4` set -> clear_command again (`0x02E72B5C`), `0x02E71324`, and the
  **command builder** `0x02E71774` (`bl` at `0x02E72B9C`, no relocation: exe_v46l's hook). The builder reads the
  struct through `[cm + 0xA0]` (`+0x48` pressed this frame, `+0x4C` released, `+0x3C` held, `+0` / `+4` stick X
  (screen, negated when `[cm + 0xA8]`) / Y, `+0x70` / `+0x72` frames since the stick flicked X / Y) and the
  global params `[0x1030F448]` (thresholds at `+0x7C` ... `+0x18C`; `+0x38` the buffer life).
- **The commands** are 4 categories at `cm + 0x158 + 0x10 c` (MSC `ControlModule(0xA, c)` = `0x02E74978`; common
  MSC keeps category 0 in `global24`, 1-3 in `global31` / `global29` / `global45`): `+0` the flag word (buffered
  commands), `+4` the count, `+8` a timer byte per command, `+0xC` a state byte (0 / 1 read, 2 not: a direction
  that needs a turn). A triggered command: flag set, timer = `[cm + 0x198]` (`[[0x1030F448] + 0x38] + 1`, stored
  every build; fighter_param_common 0 = 11.0, "buffer window = 10 F") when `cm + 0x1B8` (buffering on,
  `0x02E74AF0`) is set, else 2; state 0 (or 1 / 2). At the builder's end (`0x02E728C4`) every set flag's timer
  counts down and the flag clears at 0: a command stays readable 10 frames after its press (1 with buffering off).
  Category 0 bits read from the builder: `0x1` attack (any), `0x2` / `0x4` / `0x8` S3 / HI3 / LW3 (tilt by stick),
  `0x10` / `0x20` / `0x40` S4 / HI4 / LW4 (C-stick / A+B smash, or attack with a flick), `0x1000` / `0x2000` /
  `0x4000` / `0x8000` specials N / S / HI / LW, `0x20000`-`0x80000` stick commands (dash / turn: flicks
  sideways), `0x100000` the stick (tap) jump (flick up within `[+0x80]`, when the tap jump setting is on), `0x200000`
  the jump button, `0x400000` shield pressed (guard / air dodge), `0x1000000` spot dodge, `0x2000000` /
  `0x4000000` rolls (shield held + flick), `0x8000000` / `0x10000000` from `cm vt +0x11C` (+1 / -1), `0x20000000` grab
  (shield held + attack: a Z press sets attack `0x201` in the struct update, `0x02003878`). Category 1: taunts
  (`0x1` side, `0x2` up, `0x4` down: d-pad presses) and, from `0x02E738AC`, more (throw directions and others,
  bits `0x8`-`0x20000`: not each named). Categories 2 / 3: not decoded (cleared by "everything").
- **The trigger buffer**: `cm + 0xB4` (MSC `ControlModule(9)`, `global38`), 8 bits: attack / special / jump / shield
  pressed (`0x1` / `0x4` / `0x10` / `0x40`) and released (`0x2` / `0x8` / `0x20` / `0x80`), timers `+0xB8 + i` = the
  same life, counted down at the builder's end (`0x02E7286C`).
- **"Pressed within N frames"**: the struct's per-button counters `+0x50 + 2 n` (frames since pressed / released;
  MSC `ControlModule(0x2723 / 0x2722, button)` -> vt `+0x18C` / `+0x184`), 0xFE = long ago.
- **The game's clears**: `0x02E70FB4` clear_command (every category's flags and timers, the trigger buffer) is
  MSC `ControlModule(0x271F, 0)` (vt `+0x244`, `0x02E72BC4`: clear, and `+0x1B4` = 1 to clear once more at the next
  update before the builder); `ControlModule(0x271B)` (vt `+0x94` -> `0x02003568`) is reset_trigger (pressed = 0,
  the per-button counters 0xFE); `0x2719` / `0x271A` reset the flick counters (`cm + 0x80` / `+0x82` = 0xFE, `+0x81`
  / `+0x83` = 0). Common MSC calls `0x271B` / `0x271F` at many status starts. (`0x2714` / `0x2718`: vt `+0x1CC`, the
  pad's `+0x4C`: rumble, not the buffer.)
- **exe_v46l** (`tools/acmd_ext_cave.py` `buf_code`): `Buffer_Clear` clears groups of the above (or everything as
  the game's clear + reset_trigger + the flicks) now and, with Frames, again after each of the next builds
  (`buf_build`, the `0x02E72B9C` hook, wraps the builder). `Buffer_Set` asks for a press: at the target's next
  build the press (and held) bits, the stick (forward = its facing, PostureModule `+0x60`, flipped back when
  `cm + 0xA8`) and the flick counters (1: flicked, 0xFE: not) are put in the struct, the builder makes the game's
  own commands of them, then the struct is put back; with Frames the commands this build made (timer = the fresh
  value) get that timer. `BUFFER_CLEAR` (`0x0F0003C9`, user_entry -> hv_var's zero -> `buf_var`): MSC's way.
  Tested in unicorn with a stand-in builder (`tools/acmd_ext_test.py` `buf_tests`); the real builder's mapping is
  read from the code, not run. Not tried in game yet.

## Buffered aerials out of ground statuses (edge-cancel bug)

Base-game bug (user): an aerial buffered during landing lag that edge-cancels into Fall always came out as
neutral air. The aerial is picked by common MSC `func_311` (AttackAir `0x34` main → `func_312` → `func_310`)
from `ControlModule(0x10)` (1 N, 2 F, 3 B, 4 Hi, 5 Lw; anything else → N): a virtual call (int handler
`0x02C1C7D0` → vtable `+0x284`, fighters `0x02E74AA4`) returning the control module's `+0x1A8`. The
command builder `0x02E71774` fills `+0x1A8` on an attack press (`0x02E71B58`: from the stick: neutral
(`0x02E71458` / `0x02E71514` against common `+0x100` / `+0x104`) → 1, else sideways by stick X x facing → 2 / 3,
else up / down → 4 / 5), only while it's 0, and only when the situation (StatusModule vtable `+0xDC`) is
1 or 2 (air), or the status is JumpSquat `0xA`, Pass `0x71` or `0xAE` (jump out of water). It's cleared
(`0x02E72988`) on a frame the attack buffer byte has run out. So a press in landing lag (ground) was
buffered with `+0x1A8` = 0, and the aerial it became read neutral.

Fix: `0x02E71B54=0x60000000` (the `bne` past the computation → nop): the kind is stored on every attack
press. Nothing else reads `+0x1A8` (only `0x02E71B58` and the getter); MSC reads `ControlModule(0x10)` only in
`func_311`. Part of the standard build from now on (`build/aerial_buffer_fix.zip`: squirtle_v6's RPX + this word).

## Controls settings and input frames

`tools/smash_button_cave.py` (user docs: `docs/controls.md`).

- **Save records:** a name's controls are 0x3C bytes (save data, the per-port copies in the input
  manager below): GC at +0x00 (12 bytes), REMOTE +0x0C, FREE_STYLE (Wii Remote + Nunchuk) +0x14,
  STANDARD (Pro / GamePad / Classic) +0x21, CTR (3DS) +0x2E (13 bytes each; accessors `0x030C8A68`,
  `0x030C8AAC`, `0x030C8ADC`, `0x030C8B24`, `0x030C8B6C`; the record at +0x2E also holds the flags
  byte, 0x3B). Each
  button byte is an action (`PAD_BUTTON_OPE_*`): 0 attack, 1 special, 2 jump, 3 shield, 4 grab,
  5 smash, 6-8 smash up / side / down, 9 taunt, 10-12 taunt up / side / down. Byte 0x3B: A+B smash
  ("Smash Attack") per type, 0x80 CTR, 0x40 GC, 0x20 FREE_STYLE, 0x10 STANDARD (getters `0x030C8A00`
  / `0x030C83D8` / `0x030C86A0` / `0x030C8858`, setters +0x10 / +0x10 / +0x10 / +0x10); its low
  four bits were unused (now Stick Smash off: 0x08 / 0x04 / 0x02 / 0x01). Tap Jump: a bool byte per
  type, GC record byte 0x0B, STANDARD 0x2D, CTR 0x3A (getters `0x030C83B8` / `0x030C8838` /
  `0x030C89E0`: originally `!= 0`, now bit 0; setters +0x14: the whole byte). A test build kept a
  "Stick F-Smash" setting in its bit 1 (taken out; the load hook clears the other bits). Don't put
  more settings in the record: with Stick Smash or that one OFF, exiting the Controls screen (the
  save) crashed in the user's game (cause not found yet). STANDARD's Tap Jump byte (record 0x2D) now
  holds the stick clicks' action codes in bits 1-3 / 4-6 (`smash_button_cave.py` 5.; the load hook
  keeps them for STANDARD).
- **Pad state buttons** (the mappings' `[state + 0]`): GamePad (`0x03370A78`, from VPAD) and Pro
  Controller (`0x033715D4`, KPAD URCC) give left 0x1 / right 0x2 / down 0x4 / up 0x8, A 0x10, B 0x20,
  X 0x80, Y 0x100, L 0x1000, R 0x2000, ZL 0x4000, ZR 0x8000, + 0x10000, - 0x20000, HOME 0x40000, **left
  stick click 0x00800000, right stick click 0x10000000** (the mappings never read the clicks).
- **Input frames:** the input manager (`0x030B9A38`, and `0x030BA218`; per-port records at +0xC,
  frames at +0x314, 4 bytes a port) calls `0x030B8F08(records, port, frame, pad, ..)` per port and
  frame; it picks the mapping by the pad state's type (pad +4 vtable +0x1C, then +0x7C): 1 / 9 CTR
  `0x030B6F7C`, 2 / 5 / 6 / 8 STANDARD `0x030B7330`, 3 REMOTE `0x030B7B58`, 4 FREE_STYLE
  `0x030B8620`, 7 GC `0x030B76E8`. A frame is a u16 of action bits and the stick (s8, x 127). A
  button's action gives bit `1 << op` (grab `0x18`); then attack -> +`0x200`, special -> +`0x800`;
  A+B smash on: attack + special -> smash `0x20` (attack and special cleared, latched in the port's
  mapping state byte 8 until both are released); tap jump on -> `0x8000`; A and B held -> `0x100`.
  The C-stick (`0x030B6C54`, substick_parameter.bin: deadzone 50, length 105, tilt scale 0.32)
  replaces the stick: smash -> `0x21` the first frames then `0x41`; attack (tilts) -> `0x1` with the
  stick at 105 x 0.32. Mapping state: 9 bytes a port at records +0x1E0 (C-stick 0-5, STANDARD 1 / 6 / 7,
  A+B latch 8; byte 2 unused: now the cave's attack-held-last-frame).
- **Fighters' pad source** (vtable `0x101047E0`, 0x34 bytes: +4 port, +0x2C the port's frame
  (`0x030BA208(mgr, port)` = mgr + 0x314 + port * 4); prepare `0x02C1B80C`): stick = byte / D,
  clamped to +-1, then a dead zone (`0x02C1B75C`; D = float `[[0x102FDC70] + 0]`, dead zone +4),
  buttons the frame's u16. The controller struct update `0x020035FC` (from `0x02E729E8`, sometimes
  twice a frame) takes the stick (+0x24) and buttons (+0x34) from it.
- **Fighter side** (`0x02E71774`, command flags at the control module +0x158; locals: +0x10 the
  common params (fighter_param_common at mgr+0x38), +0x14 pressed, +0x18 released, +0x1C held,
  +0x20 / +0x24 stick, +0x28 / +0x2C flick counters): side smash `0x02E71464`: the smash bit with
  the stick not up / down (common 0xE8 usmash 0.66 / 0xF0 dsmash -0.66), or attack with |x| >= 0.83
  (0x1C) within 2 frames (0x20) of the stick crossing 0.25; up / down smash: the smash bit with the
  stick up / down, or attack with the flick within 4 frames (0xEC / 0xF4). Tilts: 0.25 (0xC4 /
  0xD0 / 0xD4). The flick counters (control struct +0x70..) restart when the stick crosses 0.25.
- **Controls menu natives:** OptionPadAssign (`0x10303180` class) holds the five pad types'
  bytes (CTR +0, GC +0xE, STANDARD +0x1C, FREE_STYLE +0x2B, REMOTE +0x3A); `gc` etc. return
  OptionPadAssignGc ... objects on those (members bound by `0x033C4FB8(class, name, {fn, arg
  types, flags})` in `0x021B6B9C` CTR / `0x021B6EA0` GC / `0x021B71A4` STANDARD / `0x021B7498` /
  `0x021B778C`; a native's frame: +0x10 / +0x14 this, +0x18 the argument; bools are 2 / 3).
  load_parameter_* / save_parameter_*: `0x021B49DC` / `0x021B53DC` CTR, `0x021B4B64` / `0x021B5568`
  GC, `0x021B4CF4` / `0x021B56F4` STANDARD, `0x021B4E8C` / `0x021B588C` FREE_STYLE (r31 = the
  OptionPadAssign data).
- **The menu's script** is Xtal bytecode (`ui/script/app/option/option_view_button.xtal`,
  `tools/xtal.py`): `equip_table` (pad -> key -> [popup window typ_NM, actions]) decides what a
  button's popup lists (N = rows); BTN_NAME_TABLE / BTN_ID_TABLE / CURSOR_TABLE per pad;
  refresh_key_assign / state_set / is_diff per pad type. Layout `ui/lumen/option_button/
  option_button.lm`: toggle rows are instances of sprite 186 in btn_group (420) named sub_1 /
  sub_2 / sub_10 / sub_3; their labels are frames of sprites 166 / 171 named like the row; a text
  object's msbt label is its instance name (`MmenOption_button_17$0`).

## MotionModule rates (animation speed)

MotionModuleImpl (`app\battle_object\modules\motion\motion_module_impl.cpp`, code
`0x02C5B000`–`0x02C66000`), vtable `0x1010A3EC` (functions at `+4+8k`), accessor `+0x44`:

| field | get / set (vtable) | set by |
|---|---|---|
| `+0x48` | `+0x9C` / `+0xA4` | the motion's own rate: MSC `MotionModule(0x4, rate)`, ACMD `Set_Frame_Speed` (`0x02BDA5E8`, through the MSC handler) |
| `+0xF0` | `+0x2EC` / `+0x2F4` | ACMD `Set_Frame_Duration` (FT_MOTION_RATE, 1/x, `0x02BE7EC4`), MSC `MotionModule(0x35, rate)` |
| `+0xF4` | `+0x2FC` / `+0x304` | ACMD `MII_ENABLE_RATE` (`0x02BE83E4`, WorkModuleF `0x1E` if > threshold) / `MII_UNABLE_RATE` (1.0); no MSC op |

MSC handlers: int `+0x2D4` (`0x02C6164C`, ops 0–`0x38`, `0x2710`+), float `+0x2DC`
(`0x02C63118`, ops 0–`0xF`). `MotionModuleF(0xA)` is the effective speed = `+0x48` × `+0xF0` ×
`+0xF4` × another object rate. `+0xF0` / `+0xF4` are only written by the module's init / reset
(`0x02C5B30C`, `0x02C5BAEC`) besides the commands above, so `+0xF4` stays put across motions:
`tools/position_vars_cave.py` exposes it as float ID `0x0F000098` (self), used by Kirby's
Overdrive (×1.2 animations).

### The motion's intangible window (vl group 1 bytes 3 / 4; Core Breaker v11)

The fighter update (`0x02E24270`, called from the object loop at `0x02BF2E2C`, vtable `+0x1E4`) ends
(`0x02E24D1C`-`0x02E24F90`) by reading the current motion kind (MotionModule `[fighter+0x74AC]` `+0x38`; -1 skips)
and its 6 bytes in the kind's vl group 1 (`[[mgr+0x25B0+4*kind]+0xC] + motion*6`, the expanded vl array of
docs/kind-expansion.md; `0x02E3BD08` returns the same entry):
- byte 2 > 0: the cancel frame (its crossing calls `[fighter+0x74D4]`'s `0x02E6FB1C` / `0x02E6FBF8`);
- byte 4 > 0 (the window's end; dodges `0x4B`-`0x4E`, `0xDC`-`0xDD`, `0xE6`-`0xE7` scale it, `0x02E67354`): byte 3 is
  its start. With the frame now (`+0x3C`) and the frame before (`+0x40`; both less 1 when `0x02C61538`): the start
  crossed (now >= start > before) -> `0x02C42F00(hit, 2, 0)`, the status's body state intangible (the MSC's
  `HitModule(0, 2)`); **else** the end crossed -> `0x02C42F00(hit, 0, 0)`.

The `else` is a trap: a motion that jumps over both in one frame (a rate jump, `MotionModule(0x4, big)`) gets 2 and
never 0; the status change's reset is the next to clear it. Mario's SpecialHi / SpecialAirHi (kinds `0x221` /
`0x225`) have 3 / 7 (Super Jump Punch: intangible 3-6); Supamario's Core Breaker v10 jumped 0 -> 30 at its second
up special and stayed intangible to its end (the user's "invincible" blink after the landing; diag log `S4HS op=0 v=2
lr=02E24F70 lr2=02BF2E30`). v11: his vl file has 0 / 0 there, and the status sets `HitModule(0, 0)` every frame.

## Weapon modules: each kind's row (Sephiroth test 82)

The weapon set-up (`0x02BCB42C`, at `0x02BCB5C0`: `mulli r8, r30, 0x70`) calls the 28 constructors of the kind's
row in `0x103464A8` (`0x70` a row) and hands each result to a setter that stores it in the module accessor; a
constructor that is `li r3, 0; blr` leaves the kind without that module (the setter puts a shared do-nothing module
there). The slots with a module for some weapon:

| slot | accessor | module | dein | light arrow | fireball |
|---|---|---|---|---|---|
| 0 | `+0x34` | Kinetic | yes | yes | yes |
| 1 | `+0x4C` | ? | yes | - | - |
| 2 | `+0x50` | Attack | yes | yes | yes |
| 3 | `+0x24` | ? | yes | - | - |
| 4 | `+0xA0` | ? | yes | yes | yes |
| 5 | `+0x2C` | ? | yes | - | yes |
| 7 | `+0x44` | **Motion** | yes | **-** | yes |
| 8 | `+0x1C` | ? | yes | yes | yes |
| 9 | `+0x7C` | ? | yes | yes | yes |
| 11 | `+0xA4` | ? | yes | yes | yes |
| 12 | `+0xA8` | ? | yes | yes | - |
| 14 | `+0xB4` | ? | yes | yes | - |
| 26 | `+0xC4` | MotionAnimcmd | yes | yes | yes |

Zelda's light arrow (kind `0x25`) has no MotionModule: its ACMD (empty in vanilla) never runs. A weapon's scripts
follow its motion, so a copy of it with scripts (Sephiroth's held forward air's point) got no hitbox and no trail.
`tools/weapon_expand.py` `"modules"` gives a new kind its own row (the base's, some slots another kind's);
`port_check` W5 flags a copy left without one.

Other per-kind data a copy inherits (`0x1018A970` u16 flags): `0x40` the kind has a model (the model set-up
`0x02B62F50`, the file loader `0x030C3C7C`); `0x10` the model in the owner's colour (`0x02B62F88`: held / attached
things, Mario's cape, the bow and arrow); `0x80` / `0x1` / `0x100` the resource request's categories (`0x030C37AC`:
`0x320E6AC` / `0x320E634` / `0x320E6C0`; none of them: 2, loaded with the fighter). The article list entry's
callback is its spawner: dein's (`0x02F97C90`) makes it at the owner's joint `0x13`, free; the light arrow's
(`0x02F9815C`) and the bow's (`0x02F980BC`) on joint `0x19` / `0x18` in mode 4 (on the hand). Both kinds'
AttackModule set-up is the same (`0x032107B4`: 7 hitbox IDs, 2 Parts).

## Joint overrides (MSC ModelModule ops 0 / 1 / 7, Sephiroth tests 79 - 86)

The override list (`0x02C64078` scale and its rotate / translate siblings, the resolver `0x02C5B4D8`) is
MotionModuleImpl's (`0x02C5B000`-`0x02C66000`, accessor `+0x44`): a weapon without a MotionModule takes none. The
joint is named as ACMD names it:
- a fighter: below 1000 an entry of model.jtb table 0 (Sephiroth's has 26: IDs 0-25; tests 82-84's 26 was past it
  and did nothing), from 1000 table 1 (test 79's 1005+ were taken, 15 entries, and overran the list). His
  EdgeBladeL (bone 26) is table 1's 4th entry: 1003. 0x7EA (test 85) did nothing either.
- a weapon: 0x7D0 + its jtb entry (Mario's pump `ModelModule(1, 0x7D2, ...)`: entry 2, bone 4 ControlN).
- `ModelModule(2, joint)` does not undo an override (Sephiroth test 86: the blade stayed hidden in every move);
  setting it back (scale 1) does.

The weapon flag accessors (`0x0320E634` + 0x14 i) aren't one per bit in order: each is `rlwinm r3, r0, SH, 31, 31`,
bit (32 - SH): `0x0320E670` is 0x10, `0x0320E698` 0x40 (a model), `0x0320E6AC` 0x80.

## Hitboxes and hitstop (Kirby's Strike trait)

- **Hitbox creation:** every hitbox command (ACMD `Hitbox` `0x02BDB0EC`, `Special_Hitbox`, ...,
  table at `0x10350ED8`) builds 0x68 bytes of attack data and calls AttackModule (accessor `+0x50`)
  vtable `+0x54` = `AttackModuleImpl::set_attack` `0x02C086A8(this, id, part, data)` (vtable
  `0x10103524`, the only AttackModule class). It copies the data to slot `[this+0x40] + id*0x84`.
  Data: `+0x18` damage, `+0x1C` size, `+0x30` trip, `+0x34` hitlag multiplier, `+0x38` SDI,
  `+0x43` effect. AttackModule `+4` = the owner's **module accessor** (constructor `0x02C077F4`
  stores its argument there; the fighter set-up `0x02E53764` passes the accessor and then stores
  the module at accessor `+0x50` through setter `0x02BF6340`). The same set-up gives the accessor's
  other slots, e.g. `+0x28` WorkModule (`0x02F1B32C`), `+0x44` Motion, `+0x48` Stop, `+0x50`
  Attack, `+0xC4` MotionAnimcmd.
- `Extended_Special_Hitbox` (`0x02BDD46C`) goes through AttackModule's MSC handler (op `0x272C`,
  like `0x272B`): that case calls vtable `+0x39C` (`0x02C0D210`), which builds the data and calls
  set_attack too. So every hitbox kind reaches set_attack.
- **Ground/Air bit 31: misses fighters lying down** (Supamario's God Fist v9). The hitbox's Ground/Air
  (situation) parameter keeps its low byte at attack data `+0x40`; bit 31 (`0x80000000`) sets the byte
  `+0x56` to 1: the ACMD Hitbox handler (`0x02BDB214`, its parameter 21) and the MSC builder every
  `0x272B` / `0x272C` hitbox goes through (`0x02C0A96C` from `0x02C0AA64`, at `0x02C0AA04`: MSC argument 22,
  the parameter + 1). The collision set-up (`0x02C0E77C`, at `0x02C0E7CC`) then gives the hitbox the target
  class mask 1 instead of 3 (the class 2 bit off) in its packed collision word. Vanilla: Diddy Kong's dash
  attack's multi-hits (`0x80000003`); the community sheet's Hitbox tab: "the hitbox won't hit against downed
  opponent". Which statuses count as lying (the hurt side's class 2) is not traced here.
- **Hitstop:** `0x02C26724(f1 damage, f2 0.3846154, f3 5, f4 multiplier, f5 30)` =
  floor(min((damage × 0.3846154 + 5) × multiplier, 30)). `0x02C2678C(r3, r4 hitbox data, f1
  damage, f2 multiplier, r5 side, r6 use the hitbox's multiplier)` multiplies by the data's `+0x34`
  (and an electric factor for effect 3, ...), constants from the common params `[0x102FDC70]`
  `+0x90`/`+0x94`/`+0x8C`. Every battle object's hit handling goes through its vtable `+0x1B4`
  (fighters: `0x02E77930`, special values for reaction kinds `0x18`/`0x19`, else) the generic
  `0x02C27638(this, r4 accessor, r5 hit info, r6 side, r7, f1 multiplier)`: damage = hit info
  `+0xC`, hitbox data = hit info `+0x44`. The victim side calls it from `0x02C25318` with `r6 = 0`,
  the attacker side from `0x02C2639C` with `r6 = 1`; both then scale by a rate (accessor `+0x58`
  vtable `+0x17C`) and set StopModule (accessor `+0x48`) vtable `+0x8C(frames, 1)`
  (= `0x0200DDB4`: `+4` frames, `+0x11` in hitstop).
- **Throws:** `Throw_Specifier` (`0x02BE6E88`), `Throw_Specifier2`, `Intensity_Throw_Specifier`
  pack their parameters as MSC arguments and call AttackModule's MSC handler (vtable `+0x334`,
  `0x02C0ACFC`) with op `0x2716` / `0x2717`; that case builds the throw's attack data at `0x78(r1)`
  (damage first, from argument 3) and passes it to vtable `+0x64` at `0x02C0B790`. Its layout: `+0`
  damage (float), then ints `+4` angle, `+8` knockback growth, `+0xC` set knockback, `+0x10` base
  knockback (`0x02C0B5A0`-`0x02C0B650`; `0x2717`'s extra floats are added onto growth / set / base as
  ints by `0x02C0ACAC`).
- `tools/strike_cave.py` (cave `0x04B78A00`, tested in `tools/strike_test.py`) hooks `0x02C08730`
  (in set_attack, after the copy: Strike Kirby's slot damage ×1.15, hitlag ×1.2; crit bit `0x10`:
  damage ×2 more, hitlag ×2 × (s·k + 5) / (2s·k + 5) so the opponent's hitstop is exactly 2× the
  Strike one), `0x02C27638` (attacker side, Strike Kirby: damage / 1.15 (crit / 2.3 and the
  crit ratio undone), multiplier / 1.2, so his own hitstop is vanilla, or 2× on a crit) and `0x02C0B77C` (throw data:
  damage ×1.15).

### Strike: owner lookup and debug counters

The first two in-game tests showed no Strike effect at all (damage, hitstop, crit damage). Both
owner lookups were wrong: v1 took AttackModule `+4` for the battle object and read its `+0xC`; v2
scanned the fighter table (`[[0x1035184C]+0]`, entry `+0xC` as the accessor). AttackModule `+4` is
the accessor itself (above), so the hooks now read the WorkModule as `[[AM+4]+0x28]`, after
checking `[[AM+4]+0x50] == AM`. Projectiles / articles have their own accessor and WorkModule
(no Kirby marker), so they're still never changed. The cave keeps debug words at the `counters` label (printed by
`python3 -c "import sys; sys.path.insert(0, 'tools'); import strike_cave as S; a, w = S.assemble(); print(hex(a.labels['counters']))"`,
currently `0x04B78DD8`), 12 words:

| word | offset | meaning |
|---|---|---|
| 0 | `+0x00` | hitboxes seen by the set_attack hook |
| 1 | `+0x04` | hitboxes scaled (Strike) |
| 2 | `+0x08` | own-hitstop adjustments |
| 3 | `+0x0C` | throws scaled |
| 4 | `+0x10` | hitboxes whose owner lookup worked |
| 5–8 | `+0x14`–`+0x20` | last hitbox: AttackModule, its `+4` (accessor), accessor `+0x50` (should equal word 5), accessor `+0x28` (WorkModule) |
| 9 | `+0x24` | last hitbox's owner's int `0x1000008E` |
| 10 | `+0x28` | last value of it with Kirby's `0x4B49` magic (Strike = bit `0x8`) |
| 11 | `+0x2C` | hitboxes from a fighter with the magic |

Every fighter's hitboxes overwrite words 5–9, so read them in training with only Kirby attacking.
**The first counters never went past 1:** `inc()` did `addi r0, r0, 1`, which is `li r0, 1` (r0 as
a base reads 0); the user's `00 00 00 01` meant nothing. Now it counts in r10. The pointer check
(`chk`) was also widened from `0x10000000`–`0x4FFFFFFF` to `0x10000000`–`0x8FFFFFFF`.

**Third test (user): seen `0x85`, owner found `0x85`, scaled 0.** So the owner lookup works and
the marker read failed. Int `0x1000008E` is in WorkModule category **0** (get_int `0x0200F7F0`:
container `[[WM+8] + ((id >> 24) & 0xF) * 4]`, ints at container `+0xC`, index `id & 0xFFFFFF`), but
the Strike cave and `tools/kirby_stat_cave.py` read category 1 (`[table + 4]`, the status ints).
Both now read `[table]`. So the Rush / Overdrive stat scaling never worked in game either before
this (`tools/kirby_stat_test.py` now tests it).

### Hero's buffs and Oomph's downside (`tools/hero_buff_cave.py`)

- More of the attack data (the 0x68 bytes set_attack copies): `+0x20` angle, `+0x24` knockback
  growth, `+0x28` set (weight-based) knockback, `+0x2C` base knockback (ints), `+0x58` the added shield
  damage (signed half; the Hitbox command's ShieldDamage, its parameter 18).
- strike_cave.py's set_attack and throw paths end by branching to the jump table at `0x04B9F000`
  (`HB_ATK`, `HB_THROW`); the cave scales the slot by Hero's marker bits (int `0x1000008E`, `0x4B49xxxx`):
  `0x20` Oomph (damage ×1.6, knockback ×1.1), `0x40` Psyche Up (knockback ×1.2, damage + shield damage
  ×1.65), both together knockback ×1.32; throws ×1.6 with Oomph.
- **Damage taken:** the victim hit handler `0x02C25318` (first word `stwu r1, -0x110(r1)`; `r4` the
  victim's accessor, `r5` the hit info: `+0xC` damage, `+0x10` knockback, already worked out) is
  hooked: with bit `0x80` the damage is ×1.2.
- PPC trap met again here: `addi rD, r0, imm` reads 0, not r0, so the arithmetic is in r12.

### Robin's int countdown (Hero's ints)

Robin's specializer per-frame code (`0x02F635F0`, his vtable entry at `0x1014186C`) decrements his
instance ints `0x10000098`-`0x1000009C` by 1 each frame while they're positive (his tomes' recharge
timers). Anything Hero (built on Robin's kind) keeps there loses 1 a frame: the crit flag (`0x9A`) read
0 by the hit when written 1 (fix 62: written 1000, compared `!= 0`). The MP gauge int `0x9C` loses one too.

### Robin's tome code (ints 0x9F-0xA1 on Robin, Hero and Kirby's Robin copy)

`0x02F613B8(F, book)` (F: WorkModule at `+0x726C`; ten callers, among them Robin's thunder spawner `0x02F643A4` at
`0x02F645BC`, with book 0, before the spawner reads the custom number at `0x02F64650`): book -1 sets VisibilityModule
(`F+0x72B0`) group 1 to 1; any other book sets it to 0, calls the `F+0x727C` module's op 7 (`0x02C5C99C`) with the book
as a float, and stores the book into the owner's instance ints `0x9F`, `0xA0`, `0xA1` (`0x02F61458`-`0x02F61460`) and
`0x90`, clearing a flag (`[[cat0]+0x14]+0xC` bit 31). Robin's per-frame code (`0x02F62D88`) and set-up (`0x02F60270`)
write the same three ints. On Kirby they are his copy custom slot `0x9F` (copy_custom_cave.py) and the copy marker
`0xA0` (kirby_copy_new_cave.py): every Hero-copy projectile zeroed both before the custom was read (Kirby's Hero copy
fix v2; `tools/kirby_robin_book_cave.py` skips the function for a Kirby whose marker is 2 / 3). Anything stored in a
Robin-kind fighter's 0x9F-0xA1 / 0x90 is overwritten by his tome code.

### The Metal Box flag

Work flag `0x20000012` ("Has Metal Box Item", note sheet) is read every frame by fighter code:
`0x02F1CC4C` (the movement params: with it, run speed, jump / hop speeds, gravity, fall / fast-fall
speeds and weight are × common params `0x2DE`-`0x2E4`), `0x02E76320` (knockback resistance, common
param `0x241`, except for hitbox effects 9 / 0xA / 0xB / 0x16) and `0x027625C8` / `0x02762674` (the
metal footsteps). So MSC can give a fighter the Metal Box's physics with `WorkModule(0x2710,
0x20000012)` (Hero's Kaclang). No code builds `0x20000012` to set it (the item sets it some other way),
and the metal look doesn't follow it (user: Kaclang with only the flag had no metal look). See "Item
states" below.

### Item states (the items' own functions; fix 59)

Static research (not traced in game). The fighter object F is the fighter-table entry (0x76B0 bytes);
its module accessor A = [F+0xC] = F+0x230 (so F = A - 0x230). The item pickup dispatcher
`0x02E30D00(F, item)` switches on the item kind (table `0x10415A00`, 0x24-byte entries: curry 0xF,
metalblock 0x13, mushd 0x14, mushroom 0x15, slow (Timer) 0x16, superstar 0x17, thunder 0x18,
ripstickflower 0x36). Work flags are set as bits in the flag words (`oris`), not through on_flag, so
no code builds the constant 0x20000012 (WorkModule vt on_flag `+0xEC`, off_flag `+0xFC`, set_flag `+0x10C`).

- **Metal** `0x02E15DE4(F, f1, r4 on, r5 frames)`; the item: (F, -1.0, 1, -1), then sound `0x350042`.
  On: flag `0x20000012`, int `0x10000027` = frames (-1: common int 0x23F x fighter float 0xEE),
  float `0x0000000C` = f1 (-1: common float 0x240, the metal HP), ModelModule byte `+0x6D` = 1 then
  `0x020078D4(MM)` (the metal model / shader; `+0x6E` blocks it, `+0x71` overrides). Event 0x59; the
  specializer ([F+0x7538] vt `+0x23C`) can veto. `0x02E228C0` counts it down each frame and turns it off
  (F, -1.0, 0, -1) at 0 or when the HP float runs out. No ModelModule MSC op (`0x02007A84`: ops
  0/1/2/6/7/0xA/0xB) touches `+0x6D`.
- **Super / Poison Mushroom** `0x02E1E148(F, cause, dir)`: mushroom (F, 1, 0), poison (F, 1, 1), lightning
  (F, 2, 1). Ints `0x10000026` = cause, `0x10000025` = 4 / 6, status `0xDD` / `0xDE` (refused with flag
  0x25, 0x37 or 0x1B); the statuses' native helpers (enter `0x02FA2D04`, exit `0x02FA39A0`) grow / shrink
  and on exit call `0x02E1F3B4` (the scale at [F+0x7514]+0x5C, flag 0x17 / 0x18, timer int `0x10000022`,
  counted down by `0x02E24270`, reverted by `0x02E1EF30`).
- **Super Star** `0x02E16F4C(F, on, frames, r6)`; the item (F, 1, -1, 0): int `0x1000001F` frames,
  invincibility `0x02C43188`, effect `0x1000054`; counted down by `0x02E22838`.
- **Lip's Stick** `0x02E1FB78(F, on, owner, r6, f1 extra frames, f2 growth)` (fighter vt `+0x17C`): attaches the
  ripstickflower item (ItemModule `0x02C48294(IM, 0x36, 0, owner)`), or with one on (flag 0x20000009)
  extends it.
- **Timer** `0x02E16A14(F, on, rate, frames, owner)`: SlowModule slot 3 (owner 0x50000000 none); the item
  goes through `0x02E47968(entry, on, owner, rate, frames)` per player.

`tools/position_vars_cave.py` calls these from MSC / ACMD: variable `0x0F000099` (docs/position-variables.md
"Item states").

## Copy abilities: ACMD script sets

`MotionAnimcmdModule(0, set, motion, kind)` (MSC handler `0x02760F4C`, FighterMotionAnimcmdModuleImpl
vtable `0x10093B80`): op 0 calls vtable `+0x6C(this, set, motion, kind)` (`0x02760CE4`), which
stores the fighter kind for script set `set` (`[this+8+4*set]`). The module has three script
agents (`this+0x50+0x38*set`): 0 game, 1 effect, 2 sound. A motion change (`0x027606C0`, from
vtable `+0x44`: sets 0–2) binds all three to the default kind (`+0x18`):
`script = 0x02E42518([0x102FF68C], kind, motion)` (the kind's script for that motion),
`table = 0x02E424D8([0x102FF68C], kind, set)`, `0x02BEE560(table, [this+4], agent, script)`.
`+0x6C` rebinds **set 0 only** (the motion is its third argument); for any other set it only
stores the kind. So the copy helpers' `(0, 0, motion, kind)` ran the copied fighter's ACMD (and
the custom's, with `copy_custom_motion()`), but the experimental `(0, 1, custom, kind)` did nothing
to effects / sounds (user: still Kirby's).

**Set `0x11` (SILENCE, exe_v45g / exe_v46e, Kirby's Hero copy fix v1):** `copy_fx_cave.py` clears the four agents
(`this + 0x50 + 0x38 k`, k = 0 game, 1 expression, 2 sound, 3 effect) with the game's agent clear `0x02BEE9B8` (what
`0x027606C0` does for a motion whose mtable hash is 0) and cancels the late bind (`+0x1C` = -2: the late update
`0x02760E48` skips it; `+0x28` = -1, `+0x2E` = 0), so the motion just set runs no script. An agent bound to a hash its
set's table doesn't hold is cleared too (`0x02BEE404` leaves `+4` = 0), which is why set `0x10` with Kirby's slot
`0x446` (no scripts) silenced sound / effect only: sets 0-1 are bound by the motion change itself. Tested with the
game's code: `tools/kirby_hero_copy_fix_test.py`.

`tools/copy_fx_cave.py` (cave `0x04B78E80`, trampoline `0x037EE5F0`, hook = `+0x6C`'s first
instruction) adds set `0x10`: bind sets 1 and 2 (effect, sound) to `kind`'s scripts for `motion`,
exactly as above, and store the kind for them. `copy_custom_motion()` calls it for customs only
(`copy_fx_all()`), before the helper's set-0 call. Defaults keep Kirby's own effect / sound
scripts (bones match Kirby's); a custom's come from the copied fighter's files, so an effect on a
bone ID Kirby doesn't have may sit somewhere else.

**First test: still Kirby's effects / sounds.** (Notes from then: the motion change `0x027608B0`
(vtable `+0x4C`) binds only sets 0–1, and the frame set (MSC op 1, `0x02760EB0`) syncs only sets
0–1; agents `+0x130` on are a second group, `0x027605C0`.) The cave now has debug words at `dbg`
(`0x04B78F90`; `0x04B78FA8` since exe_v45g / v46e, tested in `tools/copy_fx_test.py`): `+0x00` every `+0x6C` call, `+0x04` bind-all
calls, `+0x08` last motion, `+0x0C` last kind, `+0x10` the motion's script (0 = the kind has none),
`+0x14` / `+0x18` the set 1 / set 2 tables (0 = none). Breakpoint for the bind-all path:
`0x04B78EB0`.

Second test (user): `0xA7` `+0x6C` calls, 4 bind-all calls, motion `0x239`, kind 4 (Donkey Kong).
The breakpoint at `0x04B78EB0` froze. Third test: script `0x96F2BA18`, tables `0x1278165C` /
`0x12781024`, and the bind call `0x04B78F6C` froze: everything was found and bound, yet the effects
stayed Kirby's. Why:

- The script sets are **0 game, 1 expression, 2 sound, 3 effect** (the loader `0x02E421C0` stores
  game.bin, expression.bin, sound.bin, effect.bin at the kind's entry `+0x10 + 8·set`). Group 1
  has four agents (`+0x50` … `+0x118`), one per set.
- A motion change (`0x027608B0`) binds sets 0–1 at once and leaves the motion at `+0x1C`. The
  module's late update (`0x02760DB0`, every frame) binds sets 2–3 for it with `0x027606C0(this,
  2, 3)`, to the default kind, then sets `+0x1C = -2`. So the cave's early bind of sets 1–2
  hit expression and sound, and the late update put Kirby's sound / effect back anyway.
- (Fighter set-up `0x02E13048` also keeps the kind's own effect table at `[[F+0x74D8]+0x4C]`.)

v2 bound sets 2–3, frame-synced them like `0x027606C0` and set `+0x1C = -2` itself: confirmed
working (user), but when Kirby landed mid-move the effects and sounds played again from the start.
The copy helpers' ground / air swap restarts the motion at the current frame and then sets the
frame with op 1 flag 1 (`+0x2C`, "continue": the frame sync skips the earlier events); the cave
ran before that, so it synced as a fresh start.

v3 binds nothing itself: it uses the late bind's own override. `0x027606C0` takes the kind from
`+0x28` instead of `+0x18` when `+0x2E` is set (a motion change resets both, and `+0x1C`). The
bind-all sets `+0x28 = kind`, `+0x2E = 1`, `+0x1C = motion` (when the kind has a script for it), and
the late update binds and syncs sets 2–3 with the flags op 1 has stored by then. Debug words
(`dbg`, now `0x04B78F38`): `+0x6C` calls, bind-all calls, last motion, last kind, last script.

`0x02ED1ED4` (fighter vtable `0x10130DD8` + `0x24`) is **not** called on a shield hit (Cemu
breakpoint, user).


## Damage panel (battle HUD) and Kirby's trait badge

The damage panel is `data/ui/info/dmg/dmg.flx` (flx2: docs/flx2-format.md, tools/flx.py); the
GamePad's is `dmg_drc/dmg_drc.flx` (its own class, 0x02668000-0x02676000).
- Panel object `P = [[0x1033BCB4] + 0x754]`, vtable `P+0x98` = `0x100871D8`; the UI manager
  (`0x028F9E5C`) advances the flx runtime (`0x030920FC`), then calls vt+0x3C, the per-frame update
  `0x02661808(P)` (at `0x028FA088`), which calls `0x02661674(P, slot)` for each player.
- Slot `S = P + 0xC0 + slot * 0x30C0` (8): +0 s16 entry id, +8 s16 2 = empty, +0xA s8 fighter kind
  (the starting one), +0x5C the player's panel clip (`dmg_k`), +0x60 a panel element (its alpha byte
  +0x74 follows the panel's fade), +0x18C `ko_mc`, +0x1A4 `mnd_mc` (cached children).
- Slot → fighter: `FM = [0x102F7024]`, `FE = [FM + 0x24 + entry * 4]` (entry < `[FM+0x18]`),
  `obj = [FE + 0xDC0 + 4 * lbz FE+0x14E9]` (< `[FE+0xDB4]`): +4 kind, +0xC module accessor.
- flx runtime: names are interned atoms (`0x032CB1B8([0x102FCAA4]+0x24, char*, len)`; the loader
  interns every string in a file); `0x032CCAA0(inst, &atom)` child by instance name,
  `0x032CDFFC(inst, visible)`, `0x032CE00C(inst)` frame (1-based), `0x032CCC44(inst, frame)` /
  `0x032CCCA0(inst, &label)` goto and play (then `sth 1, 0x9C(inst)` to stop),
  `0x032CDF6C(inst, alpha)`, x / y `0x032CDD4C` / `0x032CDD6C`, scale `0x032CDDA0` / `0x032CDE28`.
  The game's own name atoms: `G = [0x102FCE14]`, names at `0x10086678` (`ko_mc` 0x40, `mnd_mc` 0x42).
- Little Mac's KO meter (`ko_mc`, sprite 6): shown only for kind 0x29 (`0x0265F684`);
  `0x02663C54(P, slot, v)`: v 0 → label `num_0`, 1-99 → `num_1`..`num_10` (stopped), 100 → `ko`
  (blinks). Shulk (`mnd_mc`, sprite 9): Shulk's code calls the panel (`0x02666E54` etc.) with the art,
  labels `mode_1..5`.
- A new element: a sprite appended to dmg.flx (index 0x5F and up) must have no frame actions
  (keyframe action 0xFFFF: the native per-sprite action table `0x102FCEB4` has 0x5F entries); it's
  placed by name in the panel sprites 1-4 (one per layout) and found by name in code.
- **Kirby's trait badge** (tools/trait_badge_cave.py, test trait_badge_test.py; the flx side
  tools/dmg_trait_badge.py): the vtable's +0x3C (0x10087214, its relocation moved to the dead word
  0x037EE73C) points at the cave (0x04B84000; 0x02661674 is out of a branch's reach from the grown
  code), which calls the original update, then for each non-empty slot shows `trait_mc` at the
  frame of Kirby's trait (marker int 0x1000008E bits 8-11) or hides it.
  **Works in game** (user, with the current executable, Kirby's latest MSC and the ui/info/dmg files
  built in). `trait_badge_cave.py --debug` adds step counters (at `0x04B843B0`) for a future check.
- **Manifold confirms / adds** (Manifold by Fitz Null, zlib License,
  https://gitlab.com/fitz.lol/manifold: `src/cross/flx2/InfoGadgetDmg.*`, `MovieClip.*`; overview
  in docs/manifold-notes.md; every item checked against the RPX):
  - **Panel class `InfoGadgetDmg`, 0x2AA80 bytes.** Base `InfoGadget` (0x9C bytes: 32 resource
    slots at +0x10, vtable at +0x98). flx player at +0x9C. Slots at +0xC0, 0x30C0 bytes each.
    These match ours.
  - **Slot clip list from +0x5C:** +0x5C root (`dmg_k`), +0x60 the faded element, +0x64 `face_mc`,
    +0x68 `mark_mc`, +0x6C `name_bg_mc`, +0x70 `name_col_mc`, +0x74 `mii_name_mc`, +0x78 `num_mc`,
    +0x18C `ko_mc`, +0x190 `shtdwn_mc`, +0x194 `pt_p_mc`, +0x1A8 `press_mc`; our +0x1A4 `mnd_mc` is
    unnamed there.
  - **`0x02661674(P, slot)`** is the slot's alpha fade (in / out). It sets the alpha of the +0x60
    element, `face_mc`, `mark_mc` and `ko_mc`.
  - **Vtable `0x100871D8`** (8-byte stride, function in the second word): +0x3C = `0x02661808`, the
    update (ours); +0x4C = `0x02661A8C`. The draw pass `0x028FA188` calls +0x4C after the flx draw
    `0x030923E4`, so it draws extra per-slot geometry (`0x0265A950`, 10 x 0x7C at slot +0x2A18).
    Manifold changed clips in a +0x4C hook. Those changes show a frame late. **Our +0x3C hook
    (after the flx advance `0x030920FC`, before the draw) is the better place for the badge.**
  - **Element API (flx2 `MovieClip`, 0xEC bytes):** all ours confirmed: `0x032CCAA0` child,
    `0x032CCC44` goto frame and play, `0x032CCCA0` goto label and play, `0x032CDFFC` visible,
    `0x032CE00C` frame (`lhz +0x3C` + 1), `sth 1, 0x9C` = stopped (u16).

    New: `0x032CDEDC` set rotation (degrees), `0x032CDF80` set colour transform (12 bytes: u8 mul
    A/R/G/B, s16 add A/R/G/B; stored at +0x74).

    Fields: +0x74 colour transform (our alpha byte is its multiplier A), +0xD8 / +0xDC x / y,
    +0xE0 / +0xE4 scale x / y.

    **Flags:**
    - visible is bit `0x4000` of the word at +0xE8;
    - x / y setters clear `0x2000` there;
    - +0x8C is a dirty mask (2 colour, 4 transform);
    - every setter ends with `b 0x03402B24`.

    So a cave that writes fields directly must set +0x8C itself and make that call; using the
    setters, as ours does, needs nothing more.
  - **Other panel calls:** `0x0265B494(P, slot)` sets up the slot's player name;
    `0x02663DD8(P, slot, id, costume, ?, ?, kind, use_character_name)` sets the name plate;
    `0x0265F138(P, slot, is_stamina)` sets the damage display type. Names come from `0x0300074C`
    (8 player slots of 0x1D00 bytes, UTF-16 name at +0x66).

## New ACMD commands (dispatch, Extra hitboxes)

`tools/acmd_ext_cave.py` (cave `0x04B90000`–`0x04B94000`, extras table `0x04B92000`), user docs
`docs/acmd-extra-commands.md`, test `tools/acmd_ext_test.py`.

- **Loading:** the script loaders `0x02BEE1CC` / `0x02BEE2F8` replace each command CRC by its index.
  - The index comes from the binary search `0x02BEE154` over `{crc, index}` at `0x100FAAB8` (584
    pairs, sorted by CRC).
  - Each loader steps over the command with the size table `0x100FA198` (words, header included).
  - Hooks: the search's not-found `li r3, -1` (`0x02BEE1BC`) and the two size reads (`0x02BEE2C0`,
    `0x02BEE3C0`).
- **Running:** the interpreter `0x02BEE63C` calls `handler[index]` (table `0x10350ED8`, read at
  `0x02BEE84C`; r12 is live there).
  - Call: `handler(r3 module accessor, r4, r5 script state, r6 (+8: execute flag), r7 parameters)`.
  - The handler moves the script on itself: `state +4 += size × 4` when `state +8 == -1`, then
    returns 2.
- **Hitbox data at hit time:** the hit info's `+0x44` is a 0x68-byte copy of the hitbox's data (copy
  loop `0x02C213E4` from the slot, AttackModule vt `+0x194`), not a pointer. Its `+0x10` is the
  knockback and `+0xC` the damage.
- **Victim:** `0x02C25318`.
  - Hitstun = knockback × common param `+0x2C` (0.4) in f28, stored at `0x02C25C88` to the damage
    record `+0x30` (= `DamageModuleF(1)`).
  - Final hitstop frames in r20 at `0x02C25A78` (after the slowdown rate).
- **Attacker:** `0x02C2639C`. Hitstop before the rate in r3 at `0x02C2645C`, after it at `0x02C264C4`.
- **Hitstop setter:** StopModule (accessor `+0x48`) vt `+0x8C(frames, r5)`. In the fighters' vtable
  it is `0x02E8991C`, which (frames > 0) calls `0x0200DDB4` (`+4` = max(frames, `+8`), `+8` = 0,
  `+0x11` = 1, `+0x12` = r5) and stops the motion if `+0x10` was 0. The base vtable's `+0x8C`
  (`0x0200DDA4`) only tail-calls vt `+0xA4`. (The notes above called `0x0200DDB4` the vtable entry.)
- **Hit info:** `0x02C21360` fills an array of 0xE4-byte hit infos (`+0x44` the slot copy, `+0x2C` the
  attacker's object ID, `+0x3A` the hitbox ID, `+0xB0`-`+0xD4` the rest); `0x02C251D8` passes one as r5
  to the victim handler (vt `+0xD4` = `0x02C25318`, fighters too: vtables `0x1012B9A4` /
  `0x10130DD8`) and the attacker handler (vt `+0xEC` = `0x02C2639C`).
- **Input commands:** `Input_Compare` / `Input_Get` / `Input_Set` read a fighter's own buttons with
  the ControlModule MSC wrapper `0x030B2968` (vt `+0x2F4`; ops `0x2710` pressed, `0x2712` held, MSC
  button 0 attack, 1 special, 2 jump, 3 shield, 9 grab, 5-8 d-pad up / down / left / right; the
  float one is `0x030B29A0`), everything else through the input variables' `get_float` /
  `set_float`. The compare is `Float_Var_Compare`'s (`0x02BEE010`), its result at script state `+0xC`.
- **Hit_Reset:** AttackModule MSC (wrapper `0x030B50F0`, vt `+0x334` = `0x02C0ACFC`) op `0x2724`
  (case at `0x02C0BC18`) stores 0 to `+0xC8`, which `0x2727` reads.
- **Debug counters** at `0x04B93900` (after the DI table): `docs/acmd-extra-commands.md`.
- **Per frame:** every object's motion step (fighters `0x02E408B8`, weapons `0x02BAD64C`, a third
  class `0x03048064`) calls `0x02C5F3BC` when it isn't stopped (StopModule byte `+0x10`). That runs the
  frame's ACMD (accessor `+0xC4` → `0x02C2986C` → the interpreter).
  - `0x02C5F430` (`li r0, 1`) comes right after, with r31 = MotionModule (`+4` = accessor). It never
    runs in hitlag.
- **Object set-up:** `0x02BF57B0` resets each module. At `0x02BF5864`, `lwz r3, 0x28(r31)` loads the
  WorkModule before its reset (vt `+0x24`, `0x0200E650`). Weapons are pooled, so this is where a
  reused one starts over.
- **User variables (`0x0F000300`+):** `position_vars_cave.py`'s `var_entry` (`0x04B79000`, reached
  from the get / set / add / sub / mul / div float hooks of all five WorkModule classes for category-F
  indices < `0x400`) has its first instruction replaced by `b user_gate`, which sends indices
  `>= 0x300` to `user_entry(r3 WorkModule, r4 ID, r5 write, f1)`. The state is a 48-entry table at
  `0x04B94000` (0x100 bytes each) keyed by the WorkModule: `+0x20` timers, `+0x60` `VAR_0`–`31`.
  - **Order matters:** `position_vars_cave.py`'s own output writes `var_entry`'s original first word
    (`0x04B79000=0x548C05BE`), so it must come before `acmd_ext_cave.py`'s in one `rpx_patch.py` call,
    and re-applying it alone over an executable that has this cave turns every `0x0F0003xx` variable
    off (reads 0, writes ignored). Sephiroth's test 63 executable had this: re-apply
    `acmd_ext_cave.py`'s output after it.
  - **Shared variables** `0x340 + 8s + k` (s, k = 0–7): `ue_shared` takes fighter table entry s
    (`[[0x1035184C]]`: `+0` entries, `+8` count; entry `+0x76B0 × s`, live when byte `+0x1E >= 4`,
    `+0xC` accessor, as the position variables' `slot`), and runs the normal variable path with that
    fighter's WorkModule (accessor `+0x28`) in place of the caller's, at `+0x60 + 4 × (24 + k)`. Every
    pointer is range-checked (word aligned, `0x10000000`–`0x8FFFFFFF`); a failed check, an index past
    the count or a not-live entry reads 0 and writes nothing. A write creates the fighter's entry
    (as its own write would), a read never does. `0x339`–`0x33F` and `0x3C0`–`0x3FF` read 0; `0x380`–`0x3BF` are
    New_Var's (below, exe_v40); `0x337` / `0x338` are Gravity_Set's GRAVITY / MAX_FALL (below, exe_v42).
- **KineticModule:** accessor `+0x34`.
  - Fields: kinetic type at `+0x11C`, energies at `+0x18` (0x10 each).
  - Methods: set the type with vt `+0xEC`, get an energy with vt `+0x54(id)`, get the speed sum with
    vt `+0xA4(mask)` (x in r3, y in r4).
  - An energy holds its speed at `+0` / `+4`, its enabled byte at `+0x18`, and acceleration / limit
    at `+0x20` / `+0x24`.
  - A weapon's own movement is energy 0 and gravity is energy 2. A fighter's gravity is energy 1, its own class
    with another layout (below, "Gravity_Set").
  - Set_Kinetic_Handler sends op 0 `{0, ID}` through vt `+0x114`, so it works on any object.
  - MSC handler (vt `+0x114`, Sephiroth test 154, `tools/kinetic_push_test.py`): fighters' `0x02E79100`
    (fighter_kinetic_module_impl.cpp) takes ops 0xF / 0x11 / 0x15 / 0x19 and passes the rest to
    kinetic_module_impl's `0x02C510C4` (a jump table of ops 0 - 0x18). Op 0x11 (an energy's speed) knows energies 0 -
    3 only (vt `+0x54` get energy, then `+0` / `+4`); any other goes to its assert (`0x032C4E20`, line 0xA9) and sets
    nothing. Op 0xE (8 words: energy, type, x, y, 3 more) gets that energy and calls its reset (`[energy + 0x1C]` vt
    `+0x1C`) for any energy: energy 4 (the guard damage pushback, type 0xB: func_460) is set only this way.
    Set_Kinetic_Handler_Aerial is fighter-only.
- **Reflection:** the weapon's reflect module (accessor `+0x7C`, vtable `0x1010B00C`) records a hit
  on a reflector (`0x02C6C7DC` / `0x02C6CA00`).
  - Fields: `+8` reflector's ID (reset every frame), `+0xC` its team, `+0x10` / `+0x14` / `+0x18`
    damage / speed / life ×, and `+0x1C` the reflect count (kept until set-up).
  - The hit callback's result bit `0x8` then flips the facing, gives the weapon the reflector's
    team, and sets owner module `+0x34` (accessor `+0x6C`, the current owner's ID) to the reflector
    (`0x0200E13C`). It also reverses the speed (`0x0320EFF0`).
  - LinkModule link 0 stays the original owner, so the projectile is reflected when `+0x34`
    differs from link 0's ID.
  - Weapon MSC isn't involved.
- **Reflector groups** (a fighter's own reflector, ShieldModule kind 3): ACMD REFLECTOR (`0x412fe17`,
  handler `0x02BDA27C`, op `0x2717`), SHIELD_ON (`0x02BDA1C0`, op `0x2710`) and Shield_Off2 (`0x02BD6F8C`,
  `0x2711`) go through the ShieldModule handler (accessor `+0x80`, vt `+0x16C`); the fighter's (`0x02E60FCC`)
  sends kind 3 to the reflector module at `fighter+0x72F8` (kind 4: `+0x72FC`); MSC `ShieldModule(0x2717 /
  0, 3, ...)` takes the same path.
  - Storage for every fighter (the constructor `0x02E52960`): 20 shapes of 0x24 bytes at `+0x4E90`, 5
    groups of 0x34 at `+0x58A4`; a group starts empty (first shape -1, `0x02C6F45C`).
  - Only the kind's own setup gives a group its shape(s) (`0x02C6F5FC`): Kirby's `0x02EF57E8` (group 3,
    one shape, at `0x02EF5A94`-`0x02EF5B04`), Zelda's; Robin's (`0x02F60194`) none. Without one, the
    commands write slot -1 (`fighter+0x4E6C`-`0x4E8F`, unused) and the per-frame update (`0x02C6F794`)
    skips the group: no reflector, no crash. `tools/brave_reflect_cave.py` gives Robin's kind (Hero) one.
  - Hero's Bounce still doesn't reflect in game (fix 56 test: items and projectiles hit him, the barrier
    shows). Checked statically: the cave's setup matches Kirby's call for call, MSC `ShieldModule(0x2717,
    ...)` packs its arguments as ACMD REFLECTOR does and op 0 is SHIELD_ON's. No vanilla ACMD uses
    REFLECTOR (every reflector's shape comes from its kind's setup), so giving a shape at run time is
    unproven. User: Kirby's air side B (ACMD REFLECTOR + SHIELD_ON in one status) does reflect. The
    MSC op 0x2717 reads its arguments as ACMD's (`0x0200C478`: 4-byte slots, floats with lfs, the group
    the last) and op 0 / 0x2710 both end in vt `+0x6C` (`0x0200BD8C`, the group state); setting a shape
    writes the group's own slot (`0x02E566EC` -> `0x02C6F640`). Fix 58 turns Hero's on again every
    frame while Bounce lasts (it went on once at the cast and then lived through status changes).
- **Panel alpha** (the damage panel's elements, `0x032CDF6C(inst, alpha)` stores the byte at `+0x74`):
  0-100, not 0-255 (the panel's fade writes its opacity x 100, `0x02661744`). 255 hid Hero's menu.
- **Teams:** the team module is at accessor `+0x6C` (vtable `0x10002EC8`, 8-byte vtable entries).
  - It holds three team objects (vtable `0x10002E70`, each with its id at `+4`). Getters: vt `+0x34`
    → `+4`, team (id `+8`); vt `+0x44` → `+0x14`, hurt team (id `+0x18`); vt `+0x54` → `+0x24`, attack
    team (id `+0x28`). -1 means none.
  - The AttackModule registers the attack team with its hitboxes (`0x02C07F7C`) and the HitModule
    registers the hurt team (`0x02C42718`).
  - Weapons and items get their owner's team at spawn (`0x02B64740`), with the hurt team equal to
    it.
  - The clank check `0x02C0F180` compares team ids, unless TeamDamage is set (hitbox data `+0x51`).
  - Not found: the team-attack rule global, where fighters' teams are set at match start, and the
    attack-versus-hurt filter.
- **Time: global slow, per-object slow, stage stop** (exe_v46n's Time_Scale / Target_Time_Scale / Stage_Freeze,
  docs/acmd-extra-commands.md):
  - **The battle frame.** The battle scene's update `0x0309BE34` calls the battle step `0x029108D0(battle)`, with
    `battle = [0x102F732C]`: `[battle]` is its state, `+0x88` running, `+0x8C` / `+0x8D` paused paths. The scene's
    next callback `0x0309BEF4` calls the step's second half `0x0291100C(battle)` when `0x0334CCE8()`
    (`[0x10423DC8] != 0`). The step runs the global slow manager's update, the battle object world's phases
    (`[0x102F6C30]`: `0x02BF2544`, `0x02BF29F0`, ...), the stage manager (`[0x102F7020]`: `0x031649D4`, ...,
    `0x03164B80`), and the rest.
  - **Global slow manager** `[0x102F7004]`. 16 requests {active, rate} at `+0x10` and a dirty byte `+0x30`.
    `0x02FB35AC(mgr, rate)` makes one (0xFF when full); `0x02FB3600(mgr, i)` frees it; `0x02FB3694(mgr, i)` reads its
    rate; `0x02FB3498` clears them all. `0x02FB34C0`, in the battle step, gives the slowest (`+0x31`) to the speed
    controller.
  - **Speed controller** (`0x02FFFB4C(0x104D162C)`).
    - Fields: `+0x18` the rate N, `+0x19` the rate asked for (`0x02FFA140` clamps it to 1-100: no faster than
      normal), `+0x1A` the phase, `+0x1C` 1/N (`0x02FFA104`), `+0x14` / `+0x20` counters.
    - `0x02FFA168` is its tick. `0x02FFA10C` / `0x02FFA11C` read the phase.
  - **Frame state** `[0x102F6C04]`, filled each frame by `0x02BFB97C` (from `0x02BF2568`): `+8` 1 while N isn't 1,
    `+4` 1/N, `+0` 0 / 1 / 2 the phase. Every object step wrapper (`0x02E40B90` fighters, `0x02BAD9xx` weapons,
    `0x030483xx` items, ...) runs the step only when `+8` is 0 or `+0` is 2: one frame in N; otherwise the fighter's
    `0x02E40B24` runs only its status agent's vt `+0x44`. MSC SlowModule op 0 ("slow all fighters": the module's vt
    `+0x8C`, `0x0200CCE0`) asks this manager.
  - **SlowModule** `[accessor +0xB8]` (fighter object `+0x7534`; vtable `0x101211D4`, MSC handler vt `+0xC4`
    `0x0200CDC0`):
    - Slots: `+0x20` the count, `+0x24` the slots, `0x14` bytes each {frames, integer rate, 1/rate, owner
      (`0x50000000` none), byte}.
    - Module fields: `+0x18` the product of the rates, `+8` the object's rate this frame, `+0xC` skip this frame,
      `+0x10` an accumulator.
    - Methods: vt `+0x44` `0x0200CC14(slot, rate, frames, byte, owner)` sets a slot (frames + 1 when frames > 0 and
      rate > 1; frames <= 0: no count); vt `+0x6C` clears one (`0x02DA6BDC`); vt `+0x64` / `+0x24` clear them all;
      the tick `0x0200CFC8` counts each slot's frames down and works out `+8` / `+0xC`.
    - Readers: the motion step `0x02C5F3BC` multiplies its rate by vt `+0x7C` (`+8`), so the animation and the ACMD
      frame run at 1/N; vt `+0x84` (`+0xC`) skips the MSC status agent (`0x02E408F4`) and other per-frame work.
    - Slot users: the Timer item slot 3 (`0x02E16A14`), the game slots 0-3. The object set-up `0x02BF57B0` calls vt
      `+0x24` (all cleared).
  - **Stage manager** `[0x102F7020]`.
    - `0x03164B80` (the stage's update) returns at once when byte `+0xD0` is set. Otherwise its step is
      `+0xF8 = 1/N (0x03022994) x two eased factors (+0xD4-+0xF0, kept in 0x104D162C's +0x1910 / +0x1914) x +0xFC`;
      it calls the stage's vtable (`[stage +0x111C]`) `+0x2C(stage, f1)` and `+0x4C(f1)`.
    - `0x03164EA4` (the second half) skips the same way, then calls `+0x34(f1)`.
    - `0x0316505C(manager, on)` stores `+0xD0` and calls `0x031427D0(stage, !on)`, only when a stage is loaded
      (`+0` non-zero).
    - The game's callers: Final Smash code `0x02772694`, `0x02783B94`, `0x027C4ECC`, `0x027D115C`, ...; and
      `0x029C6BE0` (on) / `0x029C6790` (off).
- **ACMD threads:** the object step entries (fighters `0x02E408B8`, weapons `0x02BAD64C`, items?
  `0x03048064`) start with `stwu r1, -0x38(r1)` and get `[r4]` = accessor. They run every unpaused
  frame: the hitlag check is inside, and nothing checks status, so they run in KO statuses too.
  - **r4 is a slot on the caller's stack** (`0x02E40B90` / `0x02BAD8xx` / `0x030483xx`: `addi r4, r1, 0xC;
    stw r31, 0xC(r1)`; the vtable entry `0x02E40C4C` passes a heap holder, `[r3 +0x28]`). The game's update thread's
    stack is outside `0x10000000`-`0x8FFFFFFF` in Cemu, so a heap-pointer check on r4 fails every frame: up to
    exe_v46l the thread runner did that and no thread ever ran in game (exe_v46m: fixed, docs/acmd-extra-commands.md
    "Thread_Start").
  - The fighter's frame: the fighter update `0x02E24270` calls `0x02E40B90` once. It skips the whole frame (only
    `0x02E40B24`, the status agent's vt `+0x44`) when the global `[0x102F6C04]` has byte `+8` set and mode `+0` not 2;
    otherwise `0x02E408B8`: (not in hitlag) `[acc +0x60]` `0x02E6D1F0`, `[acc +0x64]` `0x02C44FFC`, the motion step
    `[acc +0x44]` `0x02E87428` -> `0x02C5F3BC` (the game script), the status change queue (`[acc +0x20]` `+8` count,
    vt `+0x16C`), the second agent `[acc +0xA0]` -> `0x02C2986C`, the MSC status agent (`+0x8C` vt `+0x34` / `+0x3C`),
    `[acc +0xBC]` `0x0275E720`.
  - Interpreter wrapper: `0x02BEE950(table, accessor, state, exec, f1 frames, f2 target)`. The
    MotionAnimcmd agent's per-frame call `0x02C2986C` uses `(agent +0x4C, agent +4, agent +0x48, 1,
    1.0, 0.0)`.
  - The state is 0x38 bytes: `+0` start, `+4` current command, `+8` -1 while running (0 at the end),
    `+0xC` condition result, `+0x18` frame, `+0x1C` advance factor, `+0x34` nested CALL state.
    Reset (and free the nested state) with `0x02BEE9B8`.
  - Handlers return 2 to go on, 1 to wait, 0 to end (Script_End `0x02BE5814`).
  - True / Else jump `Offset` words from their own header.
- **Thread files in Sm4shCommand:** a file's scripts used to be read up to the first `Script_End`
  (`ACMDFile.ParseEventList`): a thread block's own `Script_End` cut the script there. The game's loader doesn't
  stop at `Script_End`: it converts the file header's command count (`+0xC`) commands one after another
  (`0x02BEE2B4`), so the game side always had the whole script.
- **What an attack connected with:** `0x02C09C0C` sets `AttackModule +0xC4` (this frame) to `OR 1 << kind` over its
  hit records (record byte `+0x23`; kind 5 is skipped) and ORs it into `+0xC8` (since the start, cleared by
  `0x2724`). MSC `0x2726` / `0x2727` (cases at `0x02C0BC6C`) call vt `+0x2BC` / `+0x2C4` for them and return
  `(kinds & mask) != 0`, the mask being the op's second word, else `0x7F`. Ryu's specials cancel on `0x6`, Kirby's
  star missile checks `0x2`: kind 1 a hurtbox, 2 a shield; the others (0 clank, 3 reflector, 4 absorber, 5 search,
  6) are Ultimate's numbering, unconfirmed. ACMD `Hit_Check` / `Hit_Get`.
- **Set hitbox** (AttackModule vt `+0x54` = `0x02C086A8`, every hitbox command and MSC): copies the 0x68-byte data
  (tag halfword `+0x66` included, whatever the builder's buffer held) into the slot (`r26`), then vt `+0x5C`.
  `0x02C08730` (after the copy) is `strike_cave.py`'s hook; `acmd_ext_cave.py` clears the Extra tag at `0x02C0874C`.
  The Extra extras used to be found again by the slot's tag with a record reused per slot: a hit info whose copy
  was taken before the script re-issued the ID read the new record (the hitstun "on the next hit").
- **MSC module ops the new commands use** (on any object through its wrapper with a fake context): PostureModule
  `0x030B2AB8` (3: position x, y, z; 4: rotation x, y, z in degrees), PostureModuleF `0x030B2AF0` (0 facing, 1-3
  position, 4-6 rotation), MotionModule `0x030B2A48` (1: kind, frame, rate; 4: rate; 7: current kind; 0x2713:
  frame), MotionModuleF `0x030B2A80` (1 frame, 9 rate), WorkModule `0x030B2B28` (6, `0x10000065`: the slot that
  last hit a fighter). The targets come from `position_vars_cave.py`'s `0x0F0002BC + target` (the accessor's bits
  as the float).
- **A weapon's owner:** LinkModule (accessor `+0x68`) vt `+0x5C(0)` says whether it has a link 0.
  vt `+0x6C(0, 1)` gives that object's ID, which matches the fighter table entry's `+0`.
- **DI isn't native.** Every fighter's MSC damage code (Kirby `func_885`) turns the launch angle by
  `WorkModuleF(0, 0x0200011A)` (max DI angle) × the stick, then LSI (`0x0200011B` / `0x0200011C`) and
  `KineticModule(0xD, …)`. The only native code is SDI (`0x02E5AF10`, `0x02E5B340`), which uses the
  hitbox's SDI.

## Leave_Ground_Cancel (grounded moves into the air)

`tools/acmd_ext_cave.py` (`lgc_code`), user docs `docs/acmd-extra-commands.md`, test `tools/leave_ground_test.py`.
First in exe_v39; working from exe_v41 (below).

- **How a grounded move ends when it leaves the ground (vanilla):** nothing in the executable changes the status.
  The executable only changes the situation (StatusModule `+0x84`, 0 ground / 1 cliff / 2 air; `+0x88` the last
  one) when the fighter leaves the ground: with a ground correction that lets it (GroundModule correct kind 1), or
  by moving up. The fighter's MSC per-frame main (`func_11` in the decompiled fighters) reads it every frame,
  `global18 = StatusModule(0x1)` (base StatusModule MSC handler `0x0200D6D8` op 1 -> vt `+0xDC` = `0x02E885E0`,
  `lwz r3, 0x84(r3)`), then runs the status loop (`global16`), which for every grounded move does
  `if (global18 == 0x2) { func_16(0xE, 0); return; }` (AttackDash `func_273`, the same in every fighter) after the
  cancel-window check (`CancelModule(0x2713) == 1 && func_39()`: its transitions all check `global18 != 0` first,
  so none fires in the air). `func_16` -> `global11` (`func_79`) -> `StatusModule(0x3, 0xE, 0)`: op 3
  (`0x0200D8FC`) calls vt `+0x12C` (`0x02E88618`, byte `+0x96` = arg != 0) and stores the request at `+0x54`.
  The change itself is vt `+0x16C` = `0x02E88B28` (`+0x4C` = the new kind at `0x02E88B40`, the old status's end
  scripts, `+0x48` = the new kind at `0x02E88D00`, the new one's scripts), reached from the pending request.
  - Ground correction: `StatusModule(0x5, situation, kinetic, correct, ...)` (op 5, vt `+0x13C` = `0x02E89154`,
    "init settings") stores the correction at `+0x78` (vt `+0xF4` = `0x0200D6CC`) and the kinetic kind at `+0x60`
    (vt `+0x114`). Every dash attack's is `(0, 0xF, 0x2, ...)`: ground, MOTION, cliff stop (common MSC, Diddy's
    `func_245` = Captain Falcon's), so it never leaves the ground sideways. Fall's is `(2, 0x13, 0x5, ...)`.
  - The game's own ground / air switch for moves that go on in both (`func_101` / `func_102` in every fighter's
    MSC): `KineticModule(0, 6); func_20(0); GroundModule(0x2710, 1)` / `KineticModule(0, 0); func_20(2);
    GroundModule(0x2710, 5)`.
- **CancelModule:** accessor `+0x94` (MSC sys `0x23`, wrapper `0x030B2F58`, vt `+0x4C`). The fighters'
  (vtable `0x1012B0C4`, handler `0x02E6FCFC`): `0x2713` returns byte `+0x10` (the cancel window is open), `0x2710`
  opens it (`0x02E6FBF8`, ACMD `ENABLE_CANCEL`), `0x2711` shuts it (`0x02E6FAC8`: `+0x10` = 0, `+0xC` = -1).
- **MSC module wrappers:** the syscall table is at `0x104187A0` (`sys_N` = word N): Status `0x18` -> `0x030B2B98`,
  Ground `0x1A` -> `0x030B2C78` (accessor `+0x2C`, vt `+0x4BC`), Cancel `0x23` -> `0x030B2F58`, Motion `0x12` ->
  `0x030B2A48` (accessor `+0x44`, vt `+0x2D4`; handler `0x02C6164C`), Kinetic `0x10` -> `0x030B29D8`.
- **The patch (exe_v39, fixed in exe_v41):** a 16-entry table at `0x04B93A00` (`+0` the fighter's StatusModule,
  `+4` state: 1 off, 2 in the air through it, 4 edges kept; `+8` the kinetic type it had; `+0xC` its module accessor,
  stored by the command; then a round-robin word), code from `0x04B93B10` (both in acmd_ext_cave.py's space between
  the debug counters and `OBJS`).
  - **StatusModule `+4` is not the module accessor** (unlike CancelModule / MotionModule `+4`): the base constructor
    `0x0200D588` makes an embedded list there (`0x0200D5C4`: `+4` = 8, a count; `+0x14` vtable `0x10002854`); the
    fighters' constructor `0x02E881A8` stores its fighter at `+0x9C` and no accessor. exe_v39 / v40's hooks read the
    accessor at `+4`, got 8, failed their pointer check and did nothing: the fighter was never marked in the air, the
    move's Fall request went through, and with `Enabled=0`'s correction 1 the move slid off the edge straight into
    Fall (user: "forces into edge slide ... rather than continuing the move"). exe_v41 takes the accessor from the
    entry (`+0xC`). `tools/leave_ground_test.py` now builds its StatusModules with `0x02E881A8` (the old code fails
    it the way the game did). Nothing requests MissFoot (`0x7D`) there: vanilla MSC asks for it only in the guard
    (`0x1B`-`0x1D`, GuardDamage), Damage (`0x45`) and SlipDown (`0x84`) loops (`GroundModule(0x2727)`), and no native
    fighter code does.
  - The command (`h_lgc`, index 617, CRC `0x224CF650`, 2 words): fighters only (StatusModule vtable
    `0x1012D42C`); sets the state; on the ground, an edge-stopping move (`+0x78` 2 / 3) gets `GroundModule(0x2710,
    1)` while off (Enabled 0) and its own back otherwise.
  - `0x0200D868` (op 1, `lwz r10, 0(r31)`) -> trampoline `0x037EE598` -> `hk_lgc_sit`: off and the situation 2 with
    a grounded status (`+0x78` 1-3): the kinetic type (KineticModule `+0x11C`) kept, `KineticModule(0, 0)`,
    `GroundModule(0x2710, 5)`; marked in the air and situation 0 again: that kinetic type and the move's correction
    back. Returns to `0x0200D86C` by ctr (the cave is out of `b` range).
  - `0x0200D91C` (op 3, `lwz r11, 0(r31)`; r29 = the words) -> trampoline `0x037EE59C` -> `hk_lgc_req`: a request
    for Fall (`0xE`) in the air while off and marked in the air, with `MotionModule(0x2712)` (motion ended) and
    `CancelModule(0x2713)` both 0, is dropped: `0x10(r1)` = r30 and on at `0x0200D948` (no vt `+0x12C`, no `+0x54`).
    Anything else goes on at `0x0200D920`.
  - `0x02E88B40` (`stw r28, 0x4C(r30)` in the status change) -> `hk_lgc_chg`: the store, then the fighter's entry
    cleared (LR is free there: `0x02E88B28` saved it).
  - The trampolines are the last two words of copy_custom_cave.py's Havok-cave space (its `SPAWN_LIMIT` now
    `0x037EE598`; zero in exe_v38).

## New_Var (named variables, exe_v40)

`tools/acmd_ext_cave.py` (`nv_code`), user docs `docs/acmd-extra-commands.md` "New_Var", test `tools/new_var_test.py`
(and the Mono test of Sm4shCommand v1.4.9's compiler). First in exe_v40 (= exe_v39 + this).

- **IDs** `0x0F000380 + k` (k < 64, any top nibble: the WorkModule ignores it). The float path is the user variables'
  (`var_entry` → `user_gate` → `user_entry`): `ue_shared`'s out-of-range branch now goes to `ue_nv` (through
  `ue_nv_far`, a `b` after the main part's `scratch`: `bge` can't reach the new region).
- **Storage:** `0x04BD0000` + 48 × 0x100: one block of 64 floats per `OBJS` entry, at the entry's address +
  `0x3C000` (`NV_OFF`). The entry's free words hold the masks: `+0xE8` / `+0xEC` declared (slots 0–31 / 32–63),
  `+0xF0` / `+0xF4` int-typed (a float write is truncated toward 0). `obj_find`'s take (`of_take`, was `li r0, 0`)
  branches to `nv_take`, which clears the entry's block, so a reused entry (a reset object, or the round robin
  past 48 objects) starts at 0; the set-up hook only forgets the entry, as before.
- **Space:** the text region was grown 16 KB: file info textRegionSize `0x2BD0000` → `0x2BD4000`, section 2 to
  `0x04BD4000` (`textregion:` / `grow:` in the cave's output). Pool `0x04BD0000`–`0x04BD3000`, code from `0x04BD3000`
  (323 words). Anything grown later goes past `0x04BD4000`.
- **Int ops:** the WorkModule's int functions read / write the category tables directly (`[wm + 8][cat] + 0xC`,
  index = the ID's low 24 bits, no bounds check), so a category-F int at index 0x380 would land past the table. The
  six WorkModule vtables (`0x10003224`, `0x100F93CC`, `0x1012132C`, `0x1013A1C0` / `0x1013AFFC` fighters,
  `0x10153184`) get `nvi_*` at `+0x84` get, `+0x8C` set, `+0xA4` inc, `+0xAC` dec, `+0xB4` add, `+0xBC` sub, `+0xC4` mul,
  `+0xCC` div (by 0: nothing, as the game's), `+0xD4` count-down (`(id, v)`: > v → −1, returns new == v); `+0x9C`
  (random) calls set through the vtable. A New_Var ID goes to `nvi_op` (read with `user_entry`, the op, written
  back as a float); any other ID jumps (ctr) to the base class's copy, the same code in every class (`0x0200F7F0`
  ...; set's first word is position_vars' `seti_hook` branch in every copy). The vtable words' ADDR32 relocations are
  moved to the dead word `0x037EE73C` (or the loader would write the old functions back). ACMD `SET_INT`
  (`0x02BD9D18`), `ADD_INT` (`0x02BD9D98`, get + set), `INC_INT` (`0x02BD6E60`, vt `+0xA4`), `Int_Var_Compare`
  (`0x02BE62C8`, get + `0x02BEE028`, the int compare table `0x1035181C`: 0 ==, 1 !=, 2 <=, 3 >=, 4 <, 5 >) and
  `INT_VAR_COMPARE_VAR` (`0x02BE636C`), and MSC's WorkModule handler (`0x0200E898`) all call these through the vtable.
- **The command** (`h_newvar`, index 618, CRC `0xA321746C`, 11 words: ID, Type, Initial (float), Scope, the name's
  ASCII in 6 words): sets the int bit to Type == 1, then, with Scope 1 or the declared bit clear, sets the declared
  bit and stores Initial (truncated for an int). Not executed: only steps. A non-New_Var ID or a bad accessor /
  WorkModule: nothing.
- **The declared / int masks gate only the command:** `ue_nv` (every read and write of a slot, float or through
  `nvi_*`) never tests the declared bit; the int bit only truncates float writes. So a slot no New_Var declared
  works from MSC as from ACMD: reads 0 until written, keeps what is written (checked with the game's own MSC
  WorkModule handler `0x0200E898` ops 7 / 6 / 0 and get_float on Kirby's 37 `khm_*` slots:
  `tools/kirby_hero_copy_fix_test.py`, Kirby's Hero copy fix v1).

## Gravity_Set (a fighter's gravity, exe_v42)

`tools/acmd_ext_cave.py` (`gs_code`), user docs `docs/acmd-extra-commands.md` "Gravity_Set", test
`tools/gravity_set_test.py` (the game's own constructor, reset and update in unicorn).

- **The fighters' KineticModule** (vtable `0x1012C5C0`, constructor `0x02E78B58`, 0x540 bytes, accessor `+0x34`):
  energies built in place and registered by `0x02C4FE4C(module, energy, index, ...)`: 0 at `+0x2C0` (`0x02E81F6C`),
  **1 = gravity at `+0x334`** (`0x02E814B0`, 0x3C bytes), 2 at `+0x370`, 3 at `+0x3D8`, 4 at `+0x430`. The table at
  module `+0x18` (0x10 a slot: `+0` the energy, `+8` its mask), count `+0xC`. Module `+4` = the accessor.
- **The update** `0x02C50058(module, mask)` calls, for every energy with `+0x18` (enabled) set and `+0x19` clear,
  `[[energy + 0x1C] + 0x14](energy, module +4 = accessor)`. Energy vtables are 8-byte entries (`+0x14` update, `+0x1C`
  reset, `+0x24` speed clear).
- **The gravity energy** (vtable `0x1012C8F8`): `+4` the vertical speed, `+0x24` the acceleration (negative: -gravity),
  `+0x28` the max fall speed, `+0x2C` the brake back to it, `+0x30` an absolute limit, `+0x34` a multiplier (1.0),
  `+0x38` the limit mode (-1 none, 0 down, 1 up, 2 both), `+0x20` the reset type. The constructor sets `+0x24` 0, the
  rest -1, `+0x34` 1.
- **Its reset** (vt `+0x1C`, `0x02E818A8(energy, type, speed vector, -, accessor)`: what every kinetic type change and
  MSC `KineticModule(0xE, 1, ...)` run): speed from the vector, `+0x34` from the fighter data (`[0x102F7024]` lookup
  `0x02E4E55C`, `+0x518`), then by type (a jump table of 9): type 0 `+0x24` = -param `0x03000018` (Gravity), `+0x28` =
  `0x03000019` (Maximum Fall Speed), `+0x2C` = `0x0300001A` (V acceleration), `+0x30` = `0x03000023`, mode 0; type 1 the
  same with mode 1 and `+0x24` unnegated; types 2-8 other params (`0x0300009B`, `0x0300009C`, `0x02000192`, ... ×
  `0x030000A0`, work float `0x0100000A`). So a kinetic type change puts the fighter's own values back.
- **Its update** (vt `+0x14`, `0x02E8159C(energy, accessor)`): f29 / the rate = `[[0x102F6C48] + 4]` /
  `[[0x102F6C48] + 0]`.
  - Fast-fall flag `0x21000001` on: speed = -(work float `0x24` if > 0, else param `0x0300001B` Fastfall Speed) ×
    rate × `+0x34`. Nothing else.
  - Else a = `+0x24` × `+0x34` × rate. With flag `0x21000000` and `0x02E6910C(accessor)`: only `v += a` when v and a
    have opposite signs. Normally, if (v + a) × a > 0 (moving further the way gravity pulls), a = `0x02C54890(v, a,
    +0x28 × f29 × +0x34, +0x2C)`: past -max (falling faster than the max fall speed) the step becomes +brake, and
    the result is clamped at -max (so a fighter falling faster than its max fall slows by `+0x2C` a frame, and one
    accelerating stops exactly at -max); max < 0 or brake <= 0: a as it is. Then `v += a`.
  - Then the limit `+0x30` by mode `+0x38` (mode 0: down only, flag `0x21000007` uses work float `0x02000312`).
  - Exit at `0x02E81860` (every path), then `0x0275FF54(accessor, energy)`.
  - MSC: fighter op 0xF (`0x02E79100`) on energy 1 writes `+0x24`, 0x15 `+0x28`, base op 0x14 (`0x02C52254`) `+0x30`
    (energy 1 takes one value; the others two, at `+0x20 / +0x24`, `+0x28 / +0x2C`, `+0x38 / +0x3C`).
- **The patch:** a 16-entry table at `0x04BD3E00` (0x20 each: `+0` the accessor, `+4` its StatusModule, `+8` Accel,
  `+0xC` MaxFall, `+0x10` Mode), code from `0x04BD3600` (after New_Var's, in the grown region; up to the table).
  - The command (`h_gs`, index 619, CRC `0x8F468450`, 4 words): fighters only (StatusModule vtable `0x1012D42C`); an
    entry for the accessor (a free one, else round robin) with the values; Accel and MaxFall < 0 and Mode & 6 == 0:
    the entry cleared.
  - `0x02E8159C` (`stwu r1, -0x48(r1)`) -> `gs_upd`: the accessor's live entry (`gs_get`, below): `+0x24` / `+0x28`
    kept in `gs_cur` with the energy, Gravity_Set's put in (`gs_eff`: Accel -> -Accel, or × the energy's own with
    Mode 1; MaxFall as given or × its own; < 0 the energy's own); Mode 2: v < -max -> v = -max; Mode 4:
    `WorkModule(0x2711, 0x21000001)` through the MSC wrapper. Then the replaced `stwu` and back to `0x02E815A0`.
  - `0x02E81860` (`mr r3, r29`) -> `gs_end`: if `gs_cur` is this energy (r28), its own `+0x24` / `+0x28` back. So
    the energy never holds Gravity_Set's values outside its update: a reset or an MSC change in between is the
    game's, and ending Gravity_Set needs no restore (the entry is just cleared).
  - `0x02E76BB4` (`mflr r0`; the fighters' DamageModule owner vt `+0x14C`, called from DamageModule vt `+0x94`
    `0x02C22EF0` after its armor check `0x02C24C88`, r4 the accessor, r5 the hit, r6 armored) -> `gs_hit`: runs the
    function (`mflr r0; b 0x02E76BB8` with LR back into the wrapper); a result of 0 (the hit takes effect: the
    hit code at `0x02C24F08` goes on with the reaction) clears the entry at once, in the hit itself. Non-zero (no
    reaction: armor with no override, knockback <= work float `0x2A`) keeps it.
  - `hk_lgc_chg` (every status change, `0x02E88B40`) now ends with `b gs_chg` (was `b 0x02E88B44`): the entry whose
    StatusModule is r30 is cleared, then back to `0x02E88B44`.
  - `gs_get` (every lookup by the update and the variables) clears the entry first when the fighter is on a ledge:
    StatusModule `+0x84` (situation) 1, or `+0x48` (status; vt `+0x8C`) or `+0x4C` (being changed to) a cliff status
    `0x72`–`0x7A` or `0xF3` / `0xF4` (tether), so a ledge grab ends it whatever path set it.
  - GRAVITY / MAX_FALL (`0x0F000337` / `338`): `ue_nv`'s out-of-range branch (`bge.far ue_zero`) now goes to `gs_var`,
    which for these two reads (writes ignored) -`+0x24` / `+0x28` of the fighter's gravity energy (KineticModule
    vtable `0x1012C5C0`, energy `+0x334` of class `0x1012C8F8`) through `gs_eff` when an entry is live; anything else
    goes on to `ue_zero`.

## Hitbox variables (Extra hitboxes' fields from variables, exe_v43)

`tools/acmd_ext_cave.py` (`hv_code`, `HV_*`), user docs `docs/acmd-extra-commands.md` "Variables in Extra hitboxes",
tests `tools/hitbox_var_test.py` (unicorn: `--synthetic` the cave with stubs; `PATCHED BASE` the executables) and
`tools/Sm4shCommand/hitbox_var_test.cs` (the compiler). First in exe_v43 (= exe_v42 + this).

- **Encoding:** Extra_Special_Hitbox / Extra_Extended_Special_Hitbox parameters 3-8 (Damage f, Angle i, KBG i, FKB i,
  BKB i, Size f): a word in `0x01000000`-`0x1FFFFFFF` is a variable (no real value is there: ints 16M+, floats
  2.4e-38-1e-19); bits 20-23 are flags (`0x00100000` FOLLOW, `0x00200000` WORLD, `0x00400000` NEG), the rest is the ID
  (`rlwinm r4, w, 0, 12, 7`). Type nibble 1 (ints): WorkModule vt `+0x84` (get_int, New_Var's `nvi_get` for
  `0x1F00038x`) and `i2f`; the rest vt `+0x44` (get_float: the mod's `0x0F000xxx` through position_vars' hooks).
- **Space:** code `0x04B97200`-`0x04B97A0C`, FOLLOW table `0x04B97B00` (16 × 0x48), in the free space after
  `ACC_CACHE` (`0x04B97000` + 64 × 8) and before `THREADS` (`0x04B98000`): grown .text, zero in exe_v42.
- **Words changed outside it (5):** the handler table entries of the two commands (`cmd_handlers`, `0x04B99C98` /
  `0x04B99C9C`: `h_extra` / `h_extra_ext` -> `hv_extra` / `hv_extra_ext`), `FRAME_HOOK` `0x02C5F430` (`b hk_frame` ->
  `b hv_fhook`), `WM_RESET` `0x02BF5864` (`b hk_wmreset` -> `b hv_wmreset`), and `gs_var`'s `gv_zero` `0x04BD3AC8`
  (`b ue_zero` -> `b hv_var`).
- **`hv_extra`** (the handler, `(r3 accessor, r4, r5 state, r6 exec, r7 params)`): when executed (`[r6 + 8]` byte),
  each variable field's value is converted (`hv_value`: NEG; Damage / Size >= 0; KBG / FKB / BKB rounded (halves
  away from 0, `fctiwz` of v ± 0.5) and >= 0; Angle: WORLD with PostureModuleF(0) < 0 -> 180 - v, rounded, 361-368
  kept, else `divw` mod 360 into 0-359) and written into the script's own parameter word; then `h_extra` (unchanged:
  the game's handler `0x02BDBB20` / `0x02BDD46C` reads the words, builds the data and calls set_attack; then
  `ext_record` tags the slot) runs with the same registers, and the words are put back. In place rather than a copy,
  so whatever the game's handler reads (r7 or the state) sees the values. Skipped (not executed): nothing read or
  written. No variable field: just the `h_extra` call.
- **FOLLOW:** after the call, any earlier entry for the same slot is dropped; with a FOLLOW field, an entry (free,
  else round robin `hv_rr`): `+0` accessor, `+4` AttackModule, `+8` the slot (`[AM + 0x40] + ID × 0x84`, ID <
  `[AM + 0x3C]`), `+0xC` the slot's tag halfword (`TAG | n`, just set by `ext_record`; the entry is only made when
  the extras entry n's `+0` is this slot), `+0x10` the FOLLOW fields (bits 0-5), `+0x14 + 4k` field k's word,
  `+0x2C + 4k` its coefficient: Damage / Size slot value (`+0x18` / `+0x1C`) / the value written (1 if 0), ints slot
  value (`+0x20 + 4 (k - 1)`) - the value written; `+0x44` the hitbox ID. So whatever the game's path does to a value (Strike's damage
  × 1.15 at set_attack) carries over.
- **`hv_fhook`** (`FRAME_HOOK`: every object, every frame it moves, after its ACMD; r31 MotionModule, `+4` the
  accessor): `hv_frame(accessor)`, then `b hk_frame` (the timers / tracking, which ends with the replaced `li r0, 1`).
  `hv_frame`: for each of its entries, the hitbox must still be the one recorded (`[acc + 0x50]` the AttackModule,
  the slot's tag, extras entry n's slot), else the entry is freed; the FOLLOW fields are read and converted again
  and written: Damage × ratio and Size × ratio through AttackModule vt `+0xB4` (`0x02C090D0(id, f1, 0)`: slot
  `+0x18`) and vt `+0xCC` (`0x02C09128(id, f1)`: slot `+0x1C`), the calls the vanilla Change_Hitbox_Damage
  (`0x02BDAEE0`, index 36) and Change_Hitbox_Size (`0x02BDAF64`, index 42) handlers make (both only store the float:
  the collision reads the slot's size every frame); `+0x20 / 24 / 28 / 2C` Angle / KBG / FKB / BKB + offset, and the ints into the extras entry's check words (`+4`-`+0x10`, what `ext_find` compares), so the extras
  still apply. Not run in hitlag (the hook isn't). A later plain hitbox in the slot: `slot_set` clears the tag; a
  later Extra one: a new tag; either way the next frame frees the entry without writing.
- **`hv_wmreset`** (`WM_RESET`, r31 the accessor; r0 r10 ctr free): frees the object's entries, then `b hk_wmreset`.
- **Variables `0x0F0003C0`-`3C8`** (`hv_var`, from `gv_zero`: user_entry's frame, r31 WorkModule, r30 index, r29
  write; writes ignored): `0x3C0 + 3c + q` (c 0 stick / 1 C-stick): x = get_float(`0x0F000110 + 2c`, along the
  facing) or (q 1) `0x0F000260 + c` (on screen), y = get_float(`0x0F000111 + 2c`); q 0 / 1 atan2 in degrees 0-360
  (`hv_atan2`: octant reduction, atan z = z (a1 + a3 z² + ... + a9 z⁸), Abramowitz & Stegun 4.4.49, within 1e-5 rad;
  (0, 0) -> 0), q 2 √(x² + y²) (`fsqrt`). `0x3C6`-`0x3C8`: PostureModuleF(4-6) (`nc_msc`, the accessor from
  `acc_of`). Others (and `0x337` / `0x338` for a non-fighter) -> `ue_zero` as before.
- **The game's hitbox handler** (`0x02BDBB20`, Special_Hitbox) reads every parameter from `r7` (Damage `+0xC` -> data
  `+0x18`, Size `+0x20` -> `+0x1C`, Angle / KBG / FKB / BKB `+0x10`-`+0x1C` -> `+0x20`-`+0x2C`), gets the battle object
  (`0x0347B1B8(accessor)`, its vt `+0x1CC` sees the data) and calls set_attack (`0x02C086A8`: the Part's hit record
  `0x02C108C4`, the 0x68-byte copy, vt `+0x5C` `0x02C08848`, then `0x02C0E77C`). `hitbox_var_test.py PATCHED BASE`
  runs it with the AttackModule and its Parts made by their own constructors (`0x02C077F4`, `0x02C10478`), the hit
  record pool and the battle object stubbed.
- **Not checked in game yet:** the rotation axis / sign that matches a given move.

## Sword trails (trail textures by id)

- `Sword_Glow` / `Sword_Glow2` / `Sword_Trace` take trail texture ids (Ike 4 / 143, Marth 9 / 144,
  Cloud 242...): a 1-based index into a table of 259 name pointers at `0x10423E60` (`TexLinkSwordTrace`,
  `TexLinkArrowTrace`, `TexPitSwordTrace`, `TexIkeSwordTrace`, ... `TexKamuiSpearTrace07`).
- The trail set-up `0x032F515C` reads `table[id]` with `lwzx` from `0x10423E5C` (`lis` / `addi r25`
  at `0x032F53A4` / `0x032F53B0`, the table's only reference), no bound check, formats `"%s.nut"`
  (`0x10192344`) and looks the texture up by that name through the manager at `[0x10423DC8]`
  (vt `+0x4C`): the textures are the fighters' `effect/<name>/trail/*.nut` (vanilla: NTP3, one mip,
  128 x 128, DXT5 / DXT1 for the "Add" ones, id 0).
- The words after the table are other variables (referenced by code), so new names need a copy of
  the table: `tools/trail_table_cave.py`.

### The trail shaders (`shader/effect_trail.nsh`)

`Sword_Glow`'s Shader argument n loads shader `0x4F000000 + n`; the game's `shader/effect_trail.nsh`
has four (`tools/nsh_dump.py`, disassembled with `tools/latte_dis`, decaf-emu's Latte disassembler:
`tools/latte_dis/build.sh` builds it). One vertex program for all: the position through
`LocalToProjectionMatrix`, the vertex colour and UV passed on. The pixel programs (t0 / t1 = the
trail's two textures, v = the vertex colour, `hdrRange` a constant of the frame):
- **1** (almost every trail): rgb = (t0.rgb x t0.a + t1.rgb x t1.a) x v.a x hdrRange,
  a = t0.a x v.a. The two textures add (each premultiplied by its own alpha).
- **2** (one Roy set): rgb = (t0.rgb x t0.a x (1 - t1.a) + t1.rgb x t1.a) x v.a x hdrRange,
  a = t1.a x v.a: the second texture over the first.
- **1001 / 1002** (the second shader loaded for 1001: Greninja): one texture's alpha x v.a bends the
  frame buffer behind the trail (`Sampler11` = FB3: uv = screen position + alpha x (-0.026, -0.046)),
  x2 x hdrRange: a refraction pass.
The vertex colour's rgb is never used: a trail's colour is its textures' alone; v.a is the trail's
fade along its length. No brightness or scroll constant: Ultimate's two `AFTER_IMAGE4_ON` floats
(1.4 / 0.1, its own trail shader's) have nowhere to go but the textures.

**The trail's code** (the same design as Ultimate's, docs/ultimate-fighter-port.md):
- Tick `0x032F6624` (from `0x032F9000`, each trail of the list; f1 = the frame step): step =
  max(step x rate +0x3C, 1/16); a delay +0x24 counts down (step / 60) and then sets the fading flag
  +0xCC; while fading, +0x28 (seconds left) counts down the same way (at 0 the trail ends) and
  **+0x30 -= +0x2C x step, +0x34 += +0x2C x step**. `Terminate_Sword_Glow(n, delay)`
  (`0x032F5DF8`): +0x28 = n / 60, +0x24 = delay / 60, +0x2C = 1 / n; set-up: +0x30 = 1, +0x34 = 0. So +0x30 is the fade
  (1 -> 0 over the n frames) and +0x34 = 1 - fade.
- Draw `0x032F877C`: +0x14 (a ring count) != 0 -> `0x032F7608` (tube trails), else `0x032F804C`.
  The set-up's +0xC2 = how many trail textures (0 / 1 / 2). Untextured (0): vertices of 0x20
  bytes (position, w = 1, colour). Textured, `0x032F84D0`: 4 vertices a point across the blade
  (0x28 bytes): position (x, y, z, 1), colour (**1, 1, 1, (1 - t) x fade**), texcoord (**1 -
  min(slide + p, 1)**, 1 - k / 3), with t = the time so far / the trail's whole time (f30) and p =
  the time so far / (blur - 1) frames, from slide = +0x34 (f24): the texture slides off by 1 - fade
  as the trail fades.

**Shader 3** (`tools/trail_shader.py`, for trails converted from Ultimate): Ultimate's 101 on these
vertices. Two stores of the textured vertex writer (`0x032F8520` / `0x032F8538`) put t and the fade
in the colour's red and green (unused by 1, 2, 1001, 1002: `tools/trail_shader_test.py` checks);
`tools/shaders/trail_retract.psh` (assembled with `tools/latte_dis/latte-asm`, decaf-emu's
latte-assembler: `tools/latte_dis/build_asm.sh`) samples the mask (the second texture's alpha) at
U = 1 - t / fade and the colour texture at U + (1 - fade) / 2, so the trail retracts into the sword
as Ultimate's does, and takes the colour gain from the second texture's rgb (x 2). The nsh's header
word 2 is 0x02000000 + the record count (every nsh); records are self-relative (id, program count,
descriptor offsets, size; a descriptor: GX2 file offset, 1, size) and the game finds a trail shader
by its name `0x4f%06x` (`0x032F5640`), so shader 3 is a new record (after 2, ids sorted).
(`texas_cross.nsh`, the model shaders, lays its records out differently: not read by `nsh_dump.py` yet.)

## SoundModule (MSC)

- The MSC wrapper (syscall 0x1E, `0x030B2D58`) calls SoundModule (accessor `+0xA4`) vtable `+0x18C`,
  the handler `0x02C73C34` (`sound_module_impl.cpp`): ops `0x2710`-`0x272F`, jump table at
  `0x02C73CA4`. `0x2710` (id[, ...]) = play (vt `+0x54`); `0x2714` (id[, n]) = stop (vt `+0x11C`, the
  same call as ACMD's Stop_Sound_Effect handler `0x02BED1D8`); `0x272C` (id) is vt `+0x5C`, another
  play (vanilla uses it at status starts), not a stop.
- A motion change inside a status (e.g. landing: SpecialAirN -> SpecialN) runs the new motion's
  sound script from its start, so a move that keeps its status across it plays its sounds from the
  MSC (Supamario's Kamehameha, test 26).
- ACMD `Motion_Set` on the fighter itself (motion_set_fix v1, exe_v46j): the motion change binds the
  game agent to the new motion's script (`0x027608B0` -> `0x02BEE560`: state `+0` = `+4` = new script,
  `+8` = 0), so after the handler returns the interpreter (`0x02BEE874`: `+8 != -1` -> return) stops
  the old script; the new script runs from its start on the next frame. If the change's frame sync
  (`0x02760EB0`, nested `0x02BEE950` on `this+0x50` / `+0x88`) ran the new script at once, `+8` is
  -1 again and v40-v46i's handler stepped `+4` 5 words into the new script and returned 2 (the
  interpreter went on reading it misaligned). v46j: the handler saves `[state+0]` before the call;
  if it changed, it sets `+8 = 0` and returns 0 without touching `+4` (`ms_fix_code`;
  `acmd_ext_test.py` simulates both rebinds). Whether the in-game change runs that nested sync is
  unverified. User case: Link AirCatch `Motion_Set(0, 42, 1, 1)` + `Set_Frame_Duration(0.1)` at
  frame 11 - 42 = 0x2A FallSpecial is right; the duration never runs (script ended), AirCatch
  stays the status (Fall at the motion's end, not helpless): special fall is `Status_Set(0, 0x10)`.

## Fighter sound banks: one bank an id (new kinds' sound fix v1)

User: "players other than player 1 don't get sound effects or voice lines" with Hero (maybe Sephiroth). Read and run
natively (exe_v45h / exe_v46g; tools/sound_alias_cave_test.py, scratchpad emulations):
- **Per player, the same code for every kind.** Each player has a resource loader (`[[0x102F9028] + 0x58 + 4 entry]`,
  getter `0x030C3368`); its sound request `0x030C0C34` registers snd_se (id kind * 0x11 + 6), snd_vc (+ 7), the
  cheer (+ 9), the sequences (+ 0xA / 0xB), voiceanim (+ 0xC) in that loader's refcounted id -> file map
  (`0x030BEEE0`; ids, not an array, so kinds past 0x40 are fine), with the costume's `_cNN` se / vc when it exists
  (a kind past 0x39: the costume number as is). Run for Hero 0x45, Sephiroth 0x42, Supamario 0x41, Robin, Zelda:
  the same ids and paths (new kinds only lack the Kirby-copy voice bank, + 0xF, bound `0x030C0FF8`).
- The fighter SoundModule (vtable `0x10093C64`; +8 kind, +0xC player) set-up (vt +0x2CC = `0x02761C50`) takes the
  files from its own player's loader (`0x030BF0FC`) and makes a bank handle of each with the sound manager
  (`0x033EDD24` -> `0x033EDC58`: a bank already made from the same file is shared (`0x033EDA1C`, by the resource);
  else a free slot of 120 -> `0x033EDABC` -> nus3 `0x03673A94`): +0x18 se, +0x24 vc, +0x30 cheer, then registers
  them with its voice player (`0x03121FA8`, 7 slots, an alias each). A sound (row << 16 | label) is played only from
  the playing fighter's handles: `0x02C71B24` -> finder `0x02C71898`: the row's bank id (`0x0311EDBC`) = a handle's
  BINF id (`0x033EC060`), or the se / vc alias +0x5C0 / +0x5C4 (vt +0x344 = `0x02762B74`). Run for kinds 0x45 / 0x42
  / 0x2C in players 0-3: identical.
- **The cause: nus3 loads one bank an id.** nus3's load (`0x036771D8` -> parse `0x03685DB8` -> `0x0367CF98`) looks the
  bank's BINF id up in its bank list (`0x036774A4`, list 0xE) and refuses a second bank of an id already loaded
  (error `0x80000021`); `0x033EDABC` then returns 0 and the fighter's handle stays empty: every sound and voice of
  that player is silent, the first one's plays. Natively: snd_se_Brave then snd_se_Brave_c01 (both 2051) ->
  0, 0x80000021; the same file twice (vanilla snd_se_Kirby) -> 0, 0x80000021; snd_se_Brave then c01 with its own id
  -> 0, 0. Players load in order, so it is always the later player. Hero's costume banks (fix 71: `_c01`-`_c03`,
  `_c05`-`_c07`, se and vc) all kept the main ids 2051 / 6059: a Hero ditto (the second Hero takes costume 1) or
  any second Hero in another costume was silent; Sephiroth's se `_c06` / `_c07` keep 2018 (his SE only). The same
  rule bites a port and its base (Hero 2051 / 6059 = Robin's, Sephiroth 2018 / 6014 = Zelda's, Supamario's vc 6001
  = Mario's) and two ports on one base's ids (Squirtle's banks are Mario's: with Supamario, the later one's voices).
- How vanilla does costume banks: their own ids (Bowser Jr.'s Koopalings, Robin's se_common 2052 / 2053), and
  `fightermodelbanktable.mtb` gives the fighter the base id they stand for: the set-up reads it by the fighter's
  Capitalised name (`0x02A64C68(MTB, name, 0 se / 1 vc / 2 cheer)`) into +0x5C0 / +0x5C4 / +0x5C8 (0xFFFF when there
  is no record). The MTB names its 13 records from the executable's table at `0x10340CA4` (Littlemac, Reflet, Cloud,
  Bayonetta, Wiifit, KoopaJr, KoopaJr_ouen, Pikmin_ouen, Kamui), so a new kind never has one.
- **Fix v1** (new kinds' sound fix v1): costume banks of their own ids, +0x5C0 / +0x5C4 set for Hero / Sephiroth
  (hook `0x03121FA8`, its call from the set-up, LR `0x027620B8`).
- **Fix v2** (ported sound ids v1): EVERY bank of a new kind its own id (`tools/sound_bank_ids.own_id`: 46000 +
  (kind - 0x41) x 32 + slot: se 0, vc 1, cheer 2, se_common 3, se_cNN 8 + NN, vc_cNN 16 + NN, se_common_cNN 24 + NN),
  so a port never collides with its base or another port; the soundlabeltable rows keep the base's ids (no script,
  MSC, sequence, csb or executable sound id moves: Robin's specializer, which Hero runs, plays Robin's row ids
  natively) and `tools/sound_alias_cave.py` v2 gives the kind's banks the old ids as aliases, per kind from
  `reference/port_sound_ids.json`: hook SETUP `0x03127990` (the sound manager's +0x2A4 getter) for its call at
  `0x02761E44` (LR `0x02761E48`, right after the MTB lookups, before the handles): +0x5C0 se, +0x5C4 vc, +0x5C8 cheer
  (the audience gets it with the cheer handle +0x90 at `0x02761FBC`); hook FS `0x03121FA8` for its call at
  `0x02761598` (LR `0x0276159C`, the Final Smash's se_common handle +0x84, set up when the Smash Ball's banks load at
  `0x02761500`): +0x580 and the voice player slot's alias. The finder takes +0x84 for +0x580 (`0x02C71A90`), the
  se / vc handles for +0x5C0 / +0x5C4. Other users of a fighter's banks, read: Kirby's copy banks (+0x5DC, 7 slots,
  `0x02761B00` from `0x02EFDE88`) are only the copied player's Kirby-copy voice bank (kind * 0x11 + 0xF, never
  registered for kinds past 0x39), never his se / vc; the Final Smash holder `[[0x102F9028] + 0x34]` (kind * 9 + n:
  `0x030C1BBC` Fin effect / se_common / the costume-mapped vc through `0x030C1B34`); stage / common objects match
  only their own handles and the common banks (`0x03125C78`). Not read: the results screen (its fighters come from
  the per-player loaders too, mode 1 at `0x030C2E04` skipping only sequences / voice animation / Kirby-copy voice,
  so presumably the same SoundModule set-up) and the Vault sound test (`0x02A7912C`, by character id).
- Diagnostic: `tools/diag_sound_cave.py` (OSReport `S4SND setup / bankfail / gated / nobank / filtered / ok` per
  player: the handles' ids, nus3's error, every refused sound).

## EffectModule requests (effect placement)

- Class vtables `0x10105FE8` / `0x101228F8` (+ `0x101545A0`, another layout); MSC handler (vt
  `+0x2EC`) `0x02C2CEC8` (ops `0x2710`-`0x2742`); request on a bone vt `+0x4C` `0x02C29F50` →
  vt `+0x54` `0x02C2A040` (hash, bone, &pos, &rot, &random pos, &random rot, flag, size in f1).
- ACMD `Graphic_Effect` (`0x02BE1444`) calls vt `+0x4C` with its parameters unchanged; External_Graphic
  `0x02BDF7DC`, Graphic_Effect2 `0x02BDEBAC`, EFFECT_FLIP `0x02BE0EA8`, EFFECT_FOLLOW_FLIP `0x02BE0710`,
  Terminate_Graphic_Effect `0x02BE25AC` (builds `EffectModule(0x2723, ...)`).
- The flag (Graphic_Effect's / 0x2710's last argument): 1 = the bone's full matrix (vt `+0xDC`):
  offsets and rotation in the bone's frame; 0 = the bone's position (vt `+0xEC`), X offset x the
  owner's facing (PostureModule vt `+0x74`), Y rotation + pi/2 x the facing, Z offset = world depth.
- The random ranges step the battle RNG (instance 0, `0x105759C0`) on every request, even when 0
  (rollback: effects are part of the simulated state).

### EffectModule MSC ops by handle (Sephiroth's aim arrow)

From the MSC handler `0x02C2CEC8` (int ops 3 - 0x35 switch at `0x02C2CF94`, the `0x2710` family at
`0x02C2F8DC`; the arguments are words after the op):
- `0x3` (id, x, y, z, rx, ry, rz, size, a, n): a request at a world place (vt `+0x44` `0x02C29D10`, rotation in
  radians); n >= 0 plays `NN.mta` (n + 1) on the effect's model (`0x0334FF08`): the KO blast passes
  `FighterUtil(0x8)` (the player / team colour), -1 none. It tints effect *models* only, not particles.
- `0x17` (handle, x, y, z) world position (vt `+0x11C`), `0x18` (handle, rx, ry, rz) rotation in degrees,
  `0x19` (handle, sx, sy, sz) scale, `0x6` / `0x8` kill by handle, `0x30` the last request's handle (vt `+0x2FC`:
  `+0x14`).
- `0x272C` / `0x273C`: `0x2710`'s request on a bone (id, bone, pos, rot, size, random pos, random rot, flag)
  plus r, g, b in 0 - 255 (divided by 255, vt `+0x27C` on the new handle: `LAST_EFFECT_SET_COLOR`'s);
  `0x2730` / `0x273D` the same after the following request (vt `+0x64`). They return 1, not the handle: read
  it with `0x30`.
- In game (Sephiroth test 65): `0x17` / `0x18` on a `0x272C` request's handle put the effect off and drifting
  (the bone request's own frame, inferred); on a `0x3` request they place it in the world (Smash 4's `func_1764`).

## Manifold cross-reference (other native findings)

Manifold by Fitz Null (zlib License), https://gitlab.com/fitz.lol/manifold, targets this same RPX
(overview and file map: docs/manifold-notes.md). Native-code items not covered elsewhere:

- **It confirms:**
  - `BattleObject`: +4 kind, +0xC module accessor, +0x1E state byte (`>= 4` = live, the test the
    Minecraft cave uses);
  - the fighter kind name readers `0x0275DB24` / `0x0275DB38`;
  - transform → base `0x030C1FDC`.
- **Allocator:** `operator new` `0x03374578(size)`, `operator delete` `0x0337460C`, heap alloc
  `0x03374530`.
- **Resource API (`lib::Resource`, a one-word handle):**

  | function | address |
  |---|---|
  | ctor (path, flags) | `0x032D7220` |
  | `load` | `0x032D9434` |
  | `is_exist` (the "file exists" test the fighter sound loaders use) | `0x032D9600` |
  | `request` | `0x032D9894` |
  | dtor (`(h, 2)` after use) | `0x032D4200` |

  Loader internals:
  - pack path `0x032D51D0`;
  - patch list `0x032E0450`;
  - name table `0x032EA7CC`;
  - `ResourceContext` (0x133FC0 bytes; region code string "(us_en)" at +0x133EA0).
- **Kind predicate `0x028E25C0`:** kind <= 2 (Mii fighters).
- **Character id predicate `0x030A04C0`:** `ui_character_db` `+0x1C`, 104 callers.

  See docs/new-fighter-slot.md for both.
- **Not confirmed:** Manifold's `motionscript.hpp` treats the function table at `0x1012C220`
  (built at `0x02E788B0`) as the MSC module table and labels `+0x1C4` (`0x02C489FC`) "WorkModule".
  The WorkModule MSC handler is `0x0200E898` on `WorkModuleImpl`'s vtable `0x10003224` (above), so
  those labels are guesses.
- **Console addresses:** Manifold's console builds add `0x0A000000` to code and `0x00503000` to data
  addresses; the addresses in these notes are the ELF / Cemu ones.

## Effect requests and following (EffectModule, effect manager)

- ACMD `EFFECT_FOLLOW` (0xFC061097, handler `0x02BDF7DC`) calls EffectModule (accessor `+0xA0`)
  vt `+0x2EC` with an 11-word request; `EFFECT_FLW_POS` (0x089EBF6C, `0x02BE0334`) calls vt `+0x64`
  (`0x02C2AF98`; the vtable at `0x10105FE8`, (function, 0) pairs) with flags 0x8000 (| 0x4000 with
  Terminate) and 1 in r8.
- `0x02C2AF98` creates the effect (`0x0334C5C0`) and hands the follow set-up to the effect manager
  (`0x032F0508` via `0x0334C79C`): each effect's 0x1C0-byte record (manager `+0x1540` + index × 0x1C0)
  takes the follow target (`+0x34`), bone (`+0x38`) and flags (`+0x144`): r8 = 1 (position only) ->
  0x1000.
- Per frame (`0x0334E4A8`): with 0x1000 the effect's matrix is the bone's translation plus the
  effect's offset *unturned* (and its own rotation: `0x03373478`, R = Rz Ry Rx of the angles,
  sincos `0x033723D8` writing sin to r3, cos to r4); without it the bone's whole
  matrix times the offset. So Smash 4's `EFFECT_FLW_POS` offsets don't turn with the bone (Ultimate's
  do): `tools/ultimate_acmd.py` follows fully when the offset isn't zero.
- **Effects follow the model's visibility** (Kirby's Hero copy fix v8, `tools/kirby_hero_sword_fx_vis_test.py` runs
  it): every frame an object's VisibilityModule update (`0x02C76F70`, from the object updates, e.g. `0x02B94164`)
  passes its is_visible (vt `+0xA4`) to EffectModule vt `+0x34C` (`0x02C317A4`), which, while the module's byte
  `+0x9B` is set (1 from its reset, `0x02C28528`), calls set_visible vt `+0x17C` (`0x02C2C178`): `+0x9A` = the value
  and, on a change, every effect of the module switched through the manager (`0x0334CA64`). A following request
  (vt `+0x64`) made while `+0x9A` is 0 is hidden at once (`0x02C2B4A8` -> `0x0334CA4C(handle, 0)`); one-shot
  requests (vt `+0x4C` / `+0x54`) aren't checked, sword trails aren't module effects. So a fighter hidden with MSC
  `VisibilityModule(0x2710, 0)` (Kirby's Stone) draws one-shot effects and trails but no following effect. MSC
  `EffectModule(0x26, v)` sets `+0x9B` (vt `+0x21C`; `0x27` reads it, vt `+0x224`), `EffectModule(0x1C, v)` is
  set_visible; the native hide paths (`0x0275DF1C`, `0x027F4xxx`-`0x027F7xxx`) call vt `+0x17C` themselves.

## Fighter colours for the common attack effects (Sm4shCommand v1.7.1)

Why Dr. Mario's forward-air arc is orange-yellow in game while the common bank's `PtcCommonAttackArcB` (entry 0x90) is
white / grey (colour 0 white, colour 1 grey 0.32-0.83, a greyscale BC4 texture, emitter colours and colour scale 1)
and his effect script sets no colour (one `EFFECT_FOLLOW_FLIP 0x1000090`):
- **Each fighter's EffectModule keeps a colour table.** Fighter set-up `0x02E13048` (at `0x02E136C8`-`0x02E136EC`)
  calls the module's vt `+0x254` (`0x02C2CA98`, fighter `+0x74D8`) with fighter_param_etc g14's count / list
  (`etc + 0x130` / `+ 0x134`: 141, 146, 142, 144 = common 0x8D, 0x92, 0x8E, 0x90) and the fighter's fighter_param
  entry `+0x4F0` (words 0x13C-0x147: an r, g, b per id, in that order). The module stores the ids `+0x34`, colours
  `+0x38` (12 bytes each), count `+0x3C` and the smallest / largest id + 0x01000000 at `+0x40` / `+0x44`.
- **Every request looks its id up** (`0x02C29EB0` in vt `+0x4C`/`+0x54`'s path, `0x02C2ABF0`, `0x02C2B4D0` in vt `+0x64`'s,
  the following one): an id in range and in the table gets `0x0334C938(handle, r, g, b)`, the emitter set's colour
  (`0x032F0CB0` -> `0x0334F834`: set `+0x278`-`+0x280`), the same call `LAST_EFFECT_SET_COLOR` makes (vt `+0x27C` =
  `0x02C2CB40`), so a colour command after the request replaces it.
- **The set's colour multiplies both emitter colours**: eft's emitter calc (`0x04A65B2C`) writes the dynamic uniform
  block's colour 0 as set colour x colour scale (`0x778`) x the emitter's colour 0 (`+0x218`), and colour 1 likewise
  with `+0x238`. Values over 1 brighten (an additive core saturates to white, the edges keep the hue).
- Vanilla values (fighter_param.bin; `reference/params/fighter_param.csv` `attack_effect_colour_*`, mislabelled
  "motion_blend" before): Mario, Luigi, Dr. Mario, Sonic 0x8D / 0x92 (2, 0.8, 0.35), 0x8E (3, 0.7, 0.2), 0x90
  (3, 0.7, 0.25); Pac-Man and Mewtwo (2, 0.65, 0.55) / (2, 0.6, 0.5); Fox, Lucario (0.7, 0.5, 3) blue; Samus, Ness,
  Lucas, Villager green; Falco red; R.O.B. dark (0.22, 0.06, 0.04); Link, Marth, Ike and 24 others 1, 1, 1 (white).
  A kind past 0x40 needs an entry of its own (the table is filled from the fighter's own fighter_param entry).
- The Hitbox Viewer (v1.7.1) applies it: `EffectLibrary.FighterColour` (the game folder's
  `data/param/fighter/fighter_param.bin` when found above the fighter's, else the vanilla table), on the call's colour
  unless the call sets one.

## Script binding on a motion change (threads / time test v2)

- `0x02BEE560(files, accessor, agent, hash)` binds an animcmd agent: `0x02BEE404(files, agent, hash, 0)` walks the set's
  list of ACMD files (`[files]` -> nodes {file, next}) and binary-searches each file's header table (`+8` count, `+0x10`
  {crc, offset} pairs, compared **unsigned**: tools/acmd.py sorts them so) for the hash; found: `agent +4` = the
  script, r3 0; not found: `+4` = 0, r3 -1 (the agent runs nothing). Run on a game.bin with taunt scripts added (new
  crcs: vanilla Mario's game.bin has no `appeal*`): they are found like any other (tools/diag_taunt_time_test.py).
- The motion change `0x027606C0` calls it at `0x02760860` for sets r29 .. r28 with r30 = the fighter kind and the
  hash from the kind's motion table (`0x02E42518`). The sets (in game, the user's v2 log against the files' contents):
  **0 game, 1 expression, 2 sound, 3 effect** (the user's effect.bin lacks AppealSR / SL: set 3 found 0 for those two
  only; vanilla game.bins lack most motions' game scripts: set 0 found 0 for them, DK's included). In that test the
  game held the user's own game.bin / effect.bin (set 0 found 0 for every taunt, set 3 the old file's pattern): the
  package's `supamario/fighter/supamario/...` had been copied inside fighter/supamario, so the test files never
  loaded. Packages now put install files under `INSTALL_TO_data/` (docs/ultimate-port-guide.md "Packages").
- The fighter status set-up (MSC `StatusModule(0x2713)`, `0x02E882AC`) takes the new status kind from vt `+0x8C`
  (`0x02E88354`; r3 the kind, r31 the StatusModule): Appeal is `0x14D`, the smash taunt `0x14E`
  (reference/msc-note-sheet/Actions_Fighters.csv).
- `tools/diag_taunt_time_cave.py` logs both (`S4ST`, `S4MO`), the new commands' handler entries (`S4TC`) and the time
  state the battle scene sees (`S4TS`).
- **Three battle scenes step a battle** (`bl 0x029108D0`, each gated by `0x02910164(battle)`): A update `0x020AFD1C`
  (sets up `[0x102F732C]` itself; call `0x020AFE18`, next callback `0x020B02C4`: stage `0x03164FE0`, `0x0290E428` /
  `0x02D88C18`), B update `0x020E84D4` (call `0x020E8504`, next `0x020E851C`, the same calls), C update `0x0309BE34`
  (call `0x0309BE54`, next `0x0309BEF4` -> the step's second half `0x0291100C`). exe_v46n's ts_scene was on C only; the
  user's training match never ran C (the v2 diag's S4TS, printed on ts_scene's first call, never came), so Time_Scale's
  speed-up and every Frames countdown never ran there. **exe_v46t_threads** (`tools/ts_scene_sites_cave.py` on
  exe_v46s) puts A's and B's calls through the same work (ts_sitea / ts_siteb at `0x04BD4800`, trampolines at
  `0x037EE550` / `0x037EE560`: the sites can't branch that far): `tools/ts_scene_sites_test.py`. Which scene VS /
  training actually use is for the v2 test's log (`S4TS site=`).
- **Training runs none of A / B / C** (threads / time test v2 on exe_v46t_threads_diag, log 0a921016: every command ran,
  not one S4TS from any of the three sites). Every fighter step (0x02E40B90, the fighter vtable 0x10126E7C's update)
  comes from the battle object world's phases; the first, `0x02BF2544` (frame state fill `0x02BFB97C`, then the
  objects), has exactly three callers: the battle step `0x029108D0` (scenes A / B / C, at `0x02910F28`), `0x02913310`
  (`0x02913E04`) and `0x02FF4DF8` (`0x02FF4F4C`), the per-frame virtual of the battle sequence classes (24 vtables,
  `0x100A1A44` ... `0x1014E67C`), whose start / restart / end virtuals (`0x02FF1F18`, `0x02FF5E7C`, `0x02FF8D64`) clear
  every slow-motion request (`0x02FB3498`), as the battle set-up `0x029104D0` does.
  **exe_v46u_threads** (`tools/ts_tick_cave.py` on exe_v46t_threads, `tools/ts_tick_test.py`): the Frames countdown in
  `0x02BF2544` (its `bl` at `0x02BF2568` -> tsu_frame: the fill, then ts_count unless a speed-up's extra step runs:
  ts_data `+0x30`); the clear-all `0x02FB3498` -> tsu_clear (our state off, the stage going on: a training reset,
  restart, match end); `0x02FF4DF8`'s first word -> tsu_seq (a speed-up there: the sequence's frame 1 + extra times);
  scenes A / B / C -> tsu_scenea / b / c (ts_tick, the extra steps with `busy`, no count of their own). The diag
  (`tools/diag_tick_cave.py`) prints S4TS from the tick with the battle step it came from.
- **Graphic_Effect can be refused** (the v2 test: its frame-0 star and flash never showed, a thread's Graphic_Effect
  stars showed during the taunt and not after it, the taunt's own External_Graphic always did). Of every effect
  command, only Graphic_Effect's handler (`0x02BE1444`) asks EffectModule vt `+0x32C` (`0x02C31610`: 1 when bytes
  `+0x9F` and `+0xA0` are both 0) and skips the request otherwise. `+0xA0` is only cleared (constructor / reset);
  `+0x9F` is EffectModule vt `+0x324` (`0x02C31604`: `+0x9F` = !enable), called every frame by the fighter's update
  (`0x02E261A8`, at `0x02E26338` / `0x02E263F8`) with the answer of `0x02C15EB8` on another of its modules (a list of
  0x14-byte entries checked against a global's current one; an empty list = enabled). Graphic_Effect2 (the same
  vt `+0x4C` request), External_Graphic and the EFFECT_* family don't check it. Not changed in the exe (the game's
  rule for every script); tests and thread examples use Graphic_Effect2. The v3 diag's S4GE line shows the bytes at
  each Graphic_Effect.
  - **v3 test (exe_v46u_threads_diag, training): the switch never closed.** Every S4GE line had `+0x9F` = `+0xA0` = 0,
    the thread's Graphic_Effect stars (0x100000F) were accepted every 10 frames for all 60 frames (Supamario's up
    taunt outlasts them, so effects after the move's end are still untested). So the switch is not what hid v2's markers; that cause is unconfirmed (v2 still ran the old tick-less
    exe). Graphic_Effect2 stays the recommended marker as it has no switch at all.
  - **Byleth v11 / v12: refused in the air.** Graphic_Effect is the game's FOOT_EFFECT (0xC84B610E in
    reference/spreadsheets' ACMD events sheet; every vanilla use is ground dust). Byleth's catch effects requested with
    it in an air status (0x15B) never showed, the grounded taunts' always did. port_check E14 flags a fighter's own
    effects requested this way in an air move.

## The eft runtime (particles: cross_f.rpx 0x04A40000-0x04A90000)

- Emitter set-up `0x04A5BDCC` (buffer sizing), GPU uniforms `0x04A5AA30` (per texture slot
  `0x04A5A6AC`, flipbook `0x04A5A858`), particle emission `0x04A5C628` (r29 emitter instance, r30
  particle, r31 emitter data = instance `+0x140`), emitter calc `0x04A64CE8` / `0x04A65FC0` (fade,
  emission). Field meanings found there: `docs/ptcl-format.md` (0x2F9, 0x2FC-0x2FE, 0x310, 0x82C,
  flipbook block, complex header).


### PostureModuleF arguments (Hero fix 68)

`PostureModuleF(0)` is the facing (LR, -1 / 1), `1` - `3` the position, `7` the model's scale (the MSC
note sheet's "Get posture data"); `PostureModule(0, lr)` sets the facing. Hero's roll-off aerial and
Command Selection's turn round used `0x7` as the facing (always > 0: every input read as facing right).
`ControlModuleF(0)` / `(1)` are the stick on screen (X, Y; `7` / `8` unclamped); the game turns X along
the facing with `x PostureModuleF(0)` (`global48`).

### The aerial kind (`ControlModule(0x10)`, Hero fix 69)

The MSC's `ControlModule(0x10)` (int handler `0x02C1C7D0` -> vt `+0x284`) returns the fighter control
module's `+0x1A8` (`0x02E74AA4`): the aerial kind (1 neutral, 2 forward, 3 back, 4 up, 5 down) kept
from the frame attack was taken, not the stick now (why an aerial buffered in a roll took the roll's
stick). It's worked out in the update `0x02E71774` (from `0x02E71B78`): neutral when two stick
measures (`0x02E71458`, `0x02E71514`) are under the params at `+0x100` / `+0x104` of the block at
`0x10(r1)`; else a side aerial when |angle| < 50 degrees (`0x1055113C` = 0.8727 rad, set by the static
initialiser `0x02C1D790` with 90 / -90 beside it; the angle is vt `+0x3C` `0x02E73608` = atan2(y, |x|)),
forward / back by stick X x facing; else up / down by Y's sign. Statuses `1`, `2`, `0xA`, `0x71`,
`0xAE` keep a kind already set.

## Sephiroth's counter shape (`tools/edge_counter_cave.py`)

Scintilla (down special) blocks a hit with a shield shape, as Smash 4's counters do. Sephiroth (kind
`0x42`) runs Zelda's native code (specializer vtable `0x10147F34`), which has no counter, so the cave
adds one for kind `0x42` only. Research: `$S/edgenro/smash4_counter.md` (S = the session scratchpad).
Test: `tools/edge_counter_cave_test.py` (unicorn, against Marth's own setup). Applied by
`tools/edge_specials_build.py --rpx`. Not yet run in game.

**How a vanilla counter works:**
- The shape is group 1 of the fighter's kind-2 ShieldModule `M = [acc+0x72F4]` (group 0 is the guard
  bubble, built in the common fighter setup `0x02E13048` at `0x02E13430`).
  - Storage for every fighter (constructor `0x02E52960`): 5 shapes of `0x24` at `+0x4594`, 5 collision
    objects of `0x174` at `+0x4648`, 5 groups of `0x34` at `+0x4D8C`.
- Only the kind's own setup builds group 1, from specializer slot 0. Examples: Marth `0x02F1E468`,
  Link `0x02F0769C`.
  - The group init is `0x0200C858(M, desc, group)`, which calls `0x02C6F5C0`; the setups inline it.
  - `desc` = `{shapes, count, u8 x4}`. The 4 bytes go to group `+0x28`, `+0x29`, `+0x2A`, `+0x2C`:
    - Marth: `0, 0, 0, 1`.
    - Link's shield: `2, 0, 0, 1`. Its `+0x28` is copied to the collision object `+0x16D` with the LR,
      so it is probably "front only".
    - The guard: all 0.
  - `shape` (`0x20` bytes): `x1 y1 z1 x2 y2 z2 radius`, `u16` joint, `u8` type.
    - Type 2 is a capsule: `0x02C14634` uses both ends.
    - Marth writes his vl offset to both ends (a sphere).
  - Shapes are placed with the joint's world matrix (model vt `+0xDC`, in `0x02C14634`). So the
    offsets are in the joint's own frame: x sideways, y up, z forward.
  - Each group starts off. `ShieldModule(0, 2, 0, on, 1)` (vt `+0x6C`, `0x0200BD8C` -> `0x02C6F954`)
    switches it, and "on" raises `M+0x28` (the groups updated) past it.
- A hit on the shape sends the shield-hit event `0x02E35794`. That calls specializer **slot 42**
  (`+0x15C`) with the hit message:
  - `+8`: the attacker's AttackModule. vt `+0x194(id, part)` gives the hit data; hit data `+0x54` != 0
    means it can't be countered, and `+0x4F` is used for the side.
  - `+0xC`: the damage.
  - `+0x10`: the collision record: `+0x18` the attacker's object id, `+0x1C` its category,
    `+0x26` hitbox id, `+0x29` part.
  - `+0x14`: the group hit (1 = the counter).
  - `+0x18` / `+0x1C`: floats for the side function `0x02C22684`.

  Outside the guard statuses (`0x1B`-`0x1E`), that event does nothing else to the victim: no damage
  and no hitstop.
- ~~A body hit sends the damage event `0x02E35EE4`.~~ **Corrected (Supamario's Ultra Instinct v5, the in-game
  log):** `0x02E35EE4` is event 0x12, the shield DAMAGE that follows a hit on a shield shape (event 0x10, slot 42),
  not a body hit. It calls **slot 43** (`+0x164`); 0 skips that shield damage and its reaction. Marth queues his
  counter status there and sets his 16-frame hitstop (`0x0200DDB4`). A body hit is events 0xB / 0xC, which ask no
  specializer slot before adding the damage.
- **The record's category** (`+0x1C`) is the attacker AttackModule owner's object id `>> 28`. It is
  set by `0x02C0EEB4` from `0x02C0800C`: `r7 = id >> 28`.
  - 0 fighter, 1 weapon, 2 item, 3 stage gimmick. Default 6, with id `0x50000000` = none. **Corrected (Supamario's
    Ultra Instinct v5, the in-game log): an item (a placed Killer Eye) is 4 (`0x4001000x`)**; 2 / 3 unverified.
  - A projectile's AttackModule is the weapon's own, so a projectile reads 1.
  - Marth / Ike use it for their "item" flag (category 2, or a weapon whose int `0x10000000` is an
    item).

**What the cave does** (space `0x04B9D000`-`0x04B9E000`; `trail_table_cave.py`'s limit lowered):
- Kind test: `[fighter+4]`, the fighter table entry's kind.
  - The same field the object handles read (`0x02BEF604`).
  - The fighter setup also uses it (`0x02E130D4`, kind × `0x11`).
- **Setup.** Zelda's slot 0 (`0x02F97824`, `mflr r0`) becomes `b` to the cave. For kind `0x42` the cave
  calls:
  - `0x0200C858(M, desc, 1)`, with `desc` `{shape, 1, 0, 0, 0, 1}` and the shape below;
  - `0x0200BD8C(M, 0, 0, 1)` (off).

  Then it goes back to Zelda's code.
  - The shape is Ultimate's vl `special_lw_shield_data` (joint `virtualflashshield`, size 6.0,
    offset1 (0, 2, 8.3), offset2 (0, 20, 8.3)), put on joint 0.
  - It is shape index 1, after the guard's.
- **Slot 42.** Zelda's `blr` at `0x02F982F8` becomes `b` to the cave. It acts for kind `0x42`, message
  `+0x14 == 1`, status `0x155`, flag `0x21000010` off and hit data `+0x54 == 0`. It writes:
  - float `0x01000006` = message `+0xC`;
  - float `0x01000007` = the side. This is Marth's: `0x02C22684`, or for hit data `+0x4F == 6` +1.0
    when he is left of the attacker and -1.0 otherwise. It is the facing that faces the attacker
    (Marth turns to it).
  - flag `0x21000010` on;
  - flag `0x21000011` on when the record's category != 0.

  It doesn't freeze the attacker (Marth's `0x02BEFDBC`) and sets no hitstop.
- **Slot 43.** Zelda's `li r3, 1` at `0x02F982FC` becomes `b` to the cave. For kind `0x42`, status
  `0x155` and flag `0x21000010` on, it sets message `+8 |= 1` and returns 0. It queues no status and
  doesn't turn him. Otherwise it returns 1.

**MSC (his down-special stance 0x155):**
- `ShieldModule(0, 0x2, 0, 0x1, 0x1)` turns the shape on and `ShieldModule(0, 0x2, 0, 0, 0x1)`
  turns it off. Ike's pattern (latch flag; off again in the status end).
- `WorkModule(0x10, 0x21000010)` means a hit landed. Then read `WorkModuleF(0, 0x1000006)` (damage),
  `WorkModuleF(0, 0x1000007)` (side) and `WorkModule(0x10, 0x21000011)` (not a fighter).
- `StopModule(2, n)` gives him hitlag.
- `ShieldModule(0x2716, 0x2, 0, joint, radius, x1, y1, z1, x2, y2, z2, 0x1)` reshapes the shape and
  switches it on. The radius comes first: handler `0x0200C478`; with 12 arguments the last is the
  group.

**Risks / unknowns:**
- A cave-built shield group is unproven in game: Hero's cave-built reflector never reflected. The
  differences:
  - Hero's group was built with an empty shape and given its shape at run time (op `0x2717`, which no
    vanilla script does).
  - This one has its real shape from the setup and is only switched by op 0, Ike's vanilla path.
  - The specializer slots that reflector kinds have and Robin's lacks (10 `+0x5C`, 56 `+0x1CC`) only
    clear flags, so no per-kind reflect hook was found there.
- Facing: the forward offset follows him only if joint 0's world matrix includes the facing turn.
- Whether a hit on both the shape and a hurtbox hits the shape first. Slot 43 covers body hits once
  the flag is on.

### Effect heap (Sephiroth tests 61 / 62)

Every effect bank in a match (both fighters', final smashes', the stage's, the common and item effects) loads into
ONE eft heap: a MEMExpHeap (`0x032EF824`) of 44 MiB (size getter `0x02010B08` `lis r3, 0x2C0`; only `0x033FA2E4` /
`0x033FA39C` call it); the effect manager's `+0x20` (`0x032F1648`), eft::System's pools from the same one
(`0x032EF86C`). The ptcl files themselves sit in the 460 MiB resource heap (`0x02010AF8` `lis r3, 0x1CC0`).
eft's loader (`0x032F1388` -> `0x04A55160` -> `0x04A6D6EC` -> `0x04A6CD18`) allocates there per shader entry a
0x6E8 object (`0x04A6CEA4`) and its own copy of each program part (`0x04A57F88` -> `0x04A594B8` / `0x04A59618` /
`0x04A59778`, + a fetch shader `0x04A5A108`), `count x 4` pointers, 0x34 a set and 0xA00 an emitter; a failed
0x6E8 allocation is written through as NULL (+0x47C): the crash at match load. No count limit: bytes. Sephiroth's
bank 680 shaders (~13.5 MiB) crashed, 670 (~13.3) loaded (1v1 with DK; the user's bisect: P3 = a loading bank + 12
unused shader copies crashed). `tools/effect_heap_patch.py`: the effect heap 44 -> 60 MiB, the resource heap 460
-> 444 MiB (MEM_ARENA_2's total `0x02010AE8` 0x34E00000 is the sum of its blocks: an overflow isn't caught, the
blocks would overlap, so never grow one without shrinking another). `port_check` E9: a bank's estimate
(`effect_heap_estimate`).

### Effect manager: bank slots (Smash Run's enemy banks, exe_v18)

The effect manager (one object, `[0x10353CA4]`, made by `0x032EE380` from the facade `0x0334C3F4`; methods
`0x032EE09C`-`0x032F2000`, facade `0x0334C3C8`-`0x0334CC40`) is 0xC490 bytes:
- `+0x20` the eft heap (`0x032EF824`), `+0x38` the eft System, `+0x44` a sub-object, `+0xB1` "not ready" (set by the
  constructor, cleared when eft is up at `0x032EF9C0`: requests are refused while set), `+0xB4` the handle serial.
- `+0xB8` **the slots**: 41 x 0x80 (ctor `0x032F1EAC`, dtor `0x032F1F50`): `+0` bank id (0 free), `+4` eft resource id
  (= the slot number; -1 without a .ptcl), `+8` the .efc, `+0xC` its entries, `+0x10` / `+0x14` / `+0x18` path objects,
  `+0x1C` mesh records, `+0x20` the .ptcl data, `+0x24` / `+0x28` / `+0x2C` / `+0x30` models, `+0x6C` names, `+0x74`,
  `+0x78` refcount, `+0x7C` a "temporary" byte (released when the count reaches 0).
- `+0x1540` the effect-instance pool, 100 x 0x1C0 (`0x0334CFAC`; `+0` handle, 0 free, `+4` effect id, `+8` owner key,
  `+0x34` / `+0x38` follow target / bone, `+0x144` flags); `+0xC440` its live count (100, `0x032EE0A0` / `0x032F1D00`);
  `+0xC444` an OSMutex (every method locks it); `+0xC470` a 0x1C-byte camera block (`0x032EFAE4`).
- Categories (`bank >> 8`), read only by the slot finder `0x032EFEA0(mgr, bank, create)`: count
  `[0x101906D4 + 4 * cat]`, first `[0x10423B2C + 4 * cat]`: 1 common 0, 2 1, 3 fighters 2-9, 4 Final Smashes 10-17,
  5 18-25, 7 enemies 26-35, 9 37-40 (0, 6, 8 none; slot 36 never used). It returns -1 when the bank isn't there (or,
  creating, the category is full); every caller then tests `cmplwi slot, 0x29`.
- Slot users: registration `0x032F1388` (stores the bank before loading; `0x04A55160(System, heap, ptcl, slot)`),
  request `0x032F00A0` (the slot pointer goes to the instance set-up `0x0334D8D8`; instances keep the pointer),
  efc-flag getters `0x032F1040` / `0x032F10E0` / `0x032F1180`, `0x032EFF5C`, `0x032F05BC`, facade `0x0334C4D8`; the loops
  over all 41: per-frame release `0x032EE2DC`, unload-all `0x032EEA44`, find-by-bank `0x032F1344`, unregister-by-bank
  `0x032F1CCC`, the constructor / destructor's array calls. Nothing outside reads the manager past `+0x44` (the other
  users of `[0x10353CA4]`: `0x02E44D34` / `0x02E4AF68` / `0x03424BE4` call methods, `0x03331xxx` / `0x03446xxx` write
  `+0x40` / `+0x3C`).
- Handles are `(pool index << 24) | serial` (`0x032F01E0`): the pool limits them (100), not the slots.
- eft: the System (`0x04A53F08`, one only) gets its resource count from the manager's config (`0x032EF850` `li r0,
  0x29` -> config `+0x18`); eft makes `+0x18` + `+0x2C` (0x20, unused) entries at System `+8` (`0x04A5374C`).
  `0x04A55160` has no bound; `0x04A55BF0` checks the id against System `+0xC`. Ids are words everywhere.

`tools/effect_slots_patch.py` (exe_v18 = exe_v17 + it): 127 slots, category 7 = 41-126 (86; count `0x101906F0` 10 ->
86, first `0x10423B48` 26 -> 41; 26-35 left unused, every other category's slots unchanged). The slot array grows in
place: the tail (pool, count, mutex, camera block) moves up by 86 x 0x80 = 0x2B00 and the allocation grows by the
same. Immediates only (74 words): 15 slot counts / bounds, 37 `0x1540`, 5 `0x1380` (pool loops that pre-increment by
0x1C0), 3 `-0x3BC0` / 11 `-0x3BBC` after `addis rX, mgr, 1` (the constructor's also sizes the allocation and finds the
camera block), `ori r0, r0, 0xC470` `0x032EFB88`, the eft config, the two table words. `effect_slots_patch_test.py`
re-finds the sites in the base (every immediate in the tail's range) and runs the constructor, registration (86 + 1
enemy banks, the others' slots), request, the getters, the slot and pool loops on both executables (47 checks; a
reverted pool / count / camera word fails it). Limits that remain: the effect heap's bytes (above) and the 100
instances.

## Animation heap (two Sephiroths hang at load, multi-instance bugs v3)

exe_diag_v3b (Cemu OSReport crumbs): the second Sephiroth's 17th trail article (0x19C) entered its set-up (the pooled
object's vt `+0x24` = `0x02B63268`) and never reached its ACMD lookup (`0x0320D588`), so the hang is in the model /
motion set-up `0x02B62F14` (kinds with weapon flag 0x40): the model resource (`0x030C4128` -> `0x030BE54C` map, keyed
`(category << 28) | kind x 0x29 + file`, refcounted at node `+0x10`; category = the costume only for kinds with flag
0x200, so both Sephiroths share one), `0x02006FCC` (the handle into the ModelModule, accessor `+0x1AA4`, vtable
`0x100F99F4`, whose vt `+0x29C` returns its `+4`), the motion resource (type 8, `0x030C40A8` / `0x03306AC0`), the
MotionModule's vt `+0x44` (`0x02C5C044`: `0x0332637C` a 0x340 motion object, `0x0330BE2C` its set-up, `0x0330DE58`
the bind to the model) and accessor `+0x38` vt `+0x34`. No fixed-count pool or wait loop there: the handles are plain
copies, the resource map has no cap, and vanilla matches pool more instances of one article than he did (8 Diddys: 80
of kind 0x31; 8 Villagers 224 articles), so a count cap is ruled out. What can stop it is bytes: the motion objects
and the per-bone arrays (`0x036B34A0` / `0x036B32C4` bones x 64, `0x036B8040` x 16 and x 0x88, `0x036AA2FC` x 0xA0,
`0x036B4968` x 0xC ...) come from one heap, `0x036C9350(mutex [0x104470F4], size, align)` -> the allocator at
`[0x1057DBD8]` (vt `+0x1C`), made at `0x03326328` over a MEM_ARENA_2 block of `0x02010B18` (`lis r3, 0x160`: 22 MiB);
each of those allocations ends `li r3, 0; twu r31, r31` when it fails (an assert: Cemu's debugger stops the thread on
`tw`, so the game hangs with no crash log), as do the render side's (`0x033347E4`: a model part's clone). Per
Sephiroth, 41 model-bearing article instances (phantom 1 x 24 bones, snake 12 x 4, snaketip 1 x 4, trail 24 x 49, fill
3 x 7: ~1270 bone-instances against his body's 172); the hang came at ~2130 (his full set + the second's phantom,
snakes, point and 16 trails). Not confirmed in game (no heap readout): `tools/diag_crumbs_cave.py` v4 logs every
such assert of 0x0330xxxx - 0x0347xxxx / 0x036Axxxx - 0x036Dxxxx (`S4DIAG trap a=<address>`).

Confirmed in game (exe_diag_v4 = exe_v11 + crumbs, four Sephiroths): with the 46 MiB heap the first three load
completely; the fourth stops at `S4DIAG trap a=36B356C b=0` during his 11th trail article's set-up: `0x036B355C`
`bl 0x036C9350` (bones x 64, align 0x40) returned 0, then the assert. So the animation heap is the limit, and 24 MiB
held about 2250 more bone-instances (~11 KB each, the motion object and its per-bone arrays): four full Sephiroths
(~5090) need about 56 MiB plus the other users'.

MEM_ARENA_2 (`0x03374F38`): the top `0x02010AE8` bytes (`lis r3, 0x34E0`) of MEM2's free space (Cemu: ~1007 MiB) are a
bump arena (`0x03374558` set-up, `0x033746FC` take: a block past the end is still handed out, then the arena is marked
spent), the rest the default heap (`operator new`); the getters' blocks: 2 MiB `0x02010AF0`, resource `0x02010AF8`,
280 MiB `0x02010B00`, effect `0x02010B08`, 3 MiB `0x02010B10`, animation `0x02010B18`, 14 MiB small-block
`0x02010B20` (`0x03375EF0`, `0x03376098`'s buckets), plus 21 MiB of fixed-size blocks. `tools/effect_heap_patch.py`
(exe_v11): the animation heap 22 -> 46 MiB with the arena's total grown by the same 24 MiB (the default heap gives it:
~162 -> ~138 MiB on Cemu), `effect_heap_patch_test.py`; `port_check` W11 weapon-models.

### Extended Memory (graphic pack + exe_v12)

exe_v11 (46 MiB) loads three Sephiroths; the fourth runs it out (above). Cemu's graphic packs (version 6+) can
move an MMU range's end with `[RAM] mappingN = start-end` (the start must be a range's base; Cemu
src/Cafe/HW/MMU/MMU.cpp `memory_mapForCurrentTitle`, as BotW's "Extended Memory" pack does), and Cemu's
OSGetMemBound(MEM2) is that range's end minus the loader's part (coreinit_Memory.cpp), so the game sees the larger
MEM2 by itself: its MEM_ARENA_2 set-up (`0x03374F38`, r29 = MEM2's free bytes, the `freeBytes=` OSReport) keeps the
arena at a fixed total and gives the rest to the default heap. `tools/extended_memory.py`: the pack (MEM2
0x10000000-0x80000000, 1.75 GiB, every address below 0x80000000) and three hooks: the total's getter call at
`0x03374F38` and the animation getter's calls `0x03326310` / `0x03326320` -> a cave (0x04BAF000) that, when the free
bytes are >= 0x50000000, grows the total and the animation heap by the same (46 -> 160 MiB); otherwise exe_v11's
sizes. Test `tools/extended_memory_test.py` (unicorn, against exe_v11). v1 crashed at boot (the user's log: Cemu
applied the mapping, the game printed `freeBytes=788111236` = 0x6EF99F84 - 1 GiB): the game's own cap at
`0x03374EC8` -- when MEM2's allocatable size is above 0x40000000 it allocates 1 GiB from the heap's tail and never
uses it (a dev kit's extra RAM) -- left the arena less than its total. v2 skips it (`0x03374ED0` ble -> b).
User result of v2: four Sephiroths load with the pack on (confirmed in game).
v3 also grows, with the pack, the effect heap (getter 0x02010B08, its calls 0x033FA2E4 / 0x033FA39C: 60 -> 128 MiB)
and the file resource heap (0x02010AF8, its calls 0x033FA278 / 0x033FA284 / 0x033FA330 / 0x033FA33C, two boot
paths each taking the block and making the heap (0x032D2DAC: nothing in it scales with the size): 444 -> 704 MiB);
the arena total grows by the sum, the default heap keeps ~463 MiB (>3x the normal ~138). `extended_memory.py` POOLS.
User result of v3: works, four Sephiroths load.

## Article instance cap (64 a fighter)

Found from Sephiroth test 123's load crash (Cemu: access violation at `0x02C0337C`, from `0x02C057F4`). A fighter's
ArticleModule (made by `0x02C01254`, 0x148 bytes) keeps at `+0x120` a holder (0x11C bytes, allocated at
`0x02C03458`): `+4` the instance count, `+0x10` - `+0x10C` one pointer per pooled instance (64), `+0x110` the
article list's pooled entry count, `+0x114` the article list `{entries, count}` (set at `0x02C0261C` / `0x02C02824`),
`+0x118` -1. `+0x124` of the ArticleModule is another pool, 0 unless set (`0x02C01C58`). Instances are counted from the
list's `max` counts (entries before the first special one, bit 31) and stored from `+0x10` up with no bound check, so
past 64 they overwrite `+0x110` / `+0x114`; the next lookup by article id (`0x02C05790`: `+0x124` empty, so
`0x02C03378` reads `[[holder + 0x114] + 4]`) goes through a null. Not memory: a bigger heap doesn't help. Raising it
would mean a bigger holder and moving its `+0x110` / `+0x114` / `+0x118` everywhere they're read. Per fighter today
(the base's + the new articles'): Sephiroth 9 + 39, Hero 13 + 18, Squirtle 9 + 6, Supamario 9 + 1. `port_check` W8.

## Special angles 365 - 367 (the pull hitboxes)

Read from cross_f.rpx (exe_v46q; not yet confirmed in game). The hit info a hit builds (AttackModule, 0x02C25xxx; r30 the
hit info, r28 the attack's collision slot, its angle at +0x64):
- `+0x5F` = angle 365; `+0x61` = angle 367, or 366 when the victim's situation (its StatusModule vt +0xDC, +0x84) is
  not 0 (on the ground): 0x02C25CB4 - 0x02C25D0C. So **366 pulls only a victim off the ground; 367 pulls a grounded one
  too**. The game knows the special angles 361 - 368 (0x02EF7F14: 361 + 0..8 skip the fighter's angle handling).
- `+0x20` / `+0x24` = the slot's `+0xBC` / `+0xC0` (0x02C25C24): the hitbox's own movement over the frame (its
  position now - last frame's, per frame: 0x02C17B60 - 0x02C17BDC).
- The victim (fighter kinetic code): 365 sets its damage energy's `+0x54` (0x02E7BFC0 -> `+0x55`: its speed scaled,
  0x02E84558); 366 / 367 copy the vector to the damage energy's `+0x44` / `+0x48` (clamped by 0x02C26B18: y at least
  the common param struct's `+0x6C`, length at most its `+0x68`) with `+0x56` set (0x02E7C030); the energy then eases
  its speed toward it over common int 0x12000103 frames (`+0x57` the count, 0x02E845B0 - 0x02E84640).
- There is **no target point** (Ultimate's 368 + `set_vec_target_pos`): ports do it in MSC (`tools/vec_target.py`).

## Item pick-up boxes (fighter_param 0x8F - 0x96; research, not yet used by the port tools)

- Smash 4: fighter_param 0x8F - 0x92 the ground pick-up box (centre x, centre y, width, height), 0x93 - 0x96 the air
  catch box, copied (0x02E6ED58, from the fighter set-up 0x02E12C54) into the fighter AreaModule's 11-area template
  (0x10353984, 0x20 bytes each: area 4 ground item, flags 0x0484, area 5 air item, 0x0504). An area's box
  (0x02BFCC30, type 0): centre (x x facing when flag 4, y), full width / height, all x the PostureModule scale (unless
  flag 0x40): min = position + centre - size / 2. The fighter's area update 0x02E6CD34 changes only area 1 (area 0 +
  fighter_param 0x32 / 0x33): **no running extension** in Smash 4.
- Ultimate (main.bin 0x6B5160 - 0x6B54F8, areas 4 / 5 at [x9 + 0x1E8] / [+0x258]): fighter_param.prc
  `item_range_front / back / h / offset_y` (air: `item_range_air_*`): x from -back to front + ext along the facing, y
  offset_y +- h / 2, x PostureModule scale. ext = r x (`item_range_front_max` - front): r = the stick forward (stick x
  x facing, >= 0) in WALK / DASH / RUN / TURN / TURN_DASH / SQUAT_F, 1 in ATTACK_DASH / ATTACK_S3, kept through
  ITEM_HEAVY_PICKUP (and ITEM_LIGHT_PICKUP on a condition, 0x6B55DC), else 0.
- The units are the same (Bowser: Smash 4 front 19.5 / back 5.5 / height 15, Ultimate 19 / 10.1 / 15.75, both x
  scale 0.82): x = (front - back) / 2, width = front + back, y = offset_y, height = h. The running extension would
  need an executable hook (e.g. 0x02E6CF24 in the fighter area update; Smash 4 statuses Walk 1, Dash 3, Run 4, Turn 6,
  TurnDash 7, SquatF 0x13, AttackDash 0x27, AttackS3 0x28, LightGet 0x8A, HeavyGet 0x8B; status kind
  [StatusModule + 0x48], stick x [[ControlModule + 0xA0] + 0], negated when [ControlModule + 0xA8]).

## Costume groups and the result scene's cameras (Byleth v3)

- **Motion folders per costume** (`tools/costume_group_cave.py`): the path builder 0x030BB18C(r3, out, kind, type,
  costume) (types 0 body, 1 entry, 2 result, 3 route map; >3 empty) sends Bayonetta (0x38) to 0x030BAE08, whose
  costumes 4-7 but 2 take `body2` / `bodyentry2` / `bodyresult2` / `bodyroutemap2` (rodata 0x101587A4 / 0x10158860 /
  0x1015882C / 0x10158850; format 0x10158838 `fighter/%s/motion/%s/`). In battle each player's resource loader
  (`[[0x102F9028] + 0x58 + 4 entry]`, 0x030C3368; +0x20 mode, +0x24 kind, +0x28 costume) registers id -> path
  (0x030BEEE0: an id already there only gains a reference, whatever the path; 0x030BF0FC reads it): kind x 0x11 + 0
  the model (+1 c01's in mode 3, picked by the player record's byte +0x23 at 0x02E130E4), + 3 the body motions (mode 1;
  the route map otherwise), + 4 / + 5 / + 0xD / + 0x10 other packs. The entry / result packs are in shared loaders
  (`[[0x102F9028] + 0x30]` / `+ 0x34`) under kind x 9 + 1, Bayonetta's second group + 2. The fighter's MotionModule
  binds by path (0x02C5BFB8 -> 0x03306AC0). The record's +0x23 is also Kirby's copy resources' category
  (`+0x23 << 28 | id`, 0x030C5240).
- **The result scene** is an Xtal script (`data/script/xscene_result.xtal`, compiled; `script/%s.xtal` 0x101660A0).
  Its bindings are registered at 0x030D.... (function, signature 0x033C1A94, name 0x033C5050): a scene camera class
  (`start_motion` 0x0310861C: mode +0x470 = 2, its motion player +0x38 = 0x02D38734, the one stage / Final Smash
  cameras use; `look_at` 0x031089C8, `start_spline`, `set_projection_param` 0x03108854, `switch_camera`), `load_motion`
  0x03111AC8 (a motion folder resource), `get_fighter_model_name_from_fighter_kind` 0x030ED508 (0x0275DB24's name).
  The script loads `motion/camera/result/<model name>/<n>/` for the winner ("NOT FOUND CAMERA!" -> `default/1/`; teams
  `team/%d/`, no contest `nocontest/%d/`). `param/ui/result_param.bin` (bound at 0x030D37C4) is its other framing.

## Clanks (Supamario's Sledgehammer v4)

Read from cross_f.rpx (exe_v46u; not yet confirmed in game):
- **Hitbox data:** the packed-hitbox prefix `0x02C0A96C` puts Damage at `+0x18`, the Hitlag multiplier at `+0x34`,
  **Clang at `+0x46`** and **Rebound at `+0x47`** (args 3, 14, 16, 17).
- **The collision masks** (`0x02C0E77C`, a hitbox's two category words): its target mask is HitBits (`+0x3F`, bits 0-5)
  | 0x22-or-0x23 << 6, where Clang sets bit 6, the constant 0x22 sets bits 7 and 11, Shieldable `+0x49` | 4, Reflectable
  `+0x4A` | 8, Absorbable `+0x4B` | 0x10 (each << 6). So **Clang 0: the hitbox meets no other hitbox**, and HitBits 0
  with Clang 1 and Shieldable / Reflectable / Absorbable 0 gives a box that meets only other hitboxes.
- **Detection:** the attack-vs-attack pass `0x02C0F6F0` (its team filter `0x02C0F180`, a facing / position check `0x02C0F2E8` (not traced further),
  the bounding boxes and shapes `0x02D42C44` / `0x02D42CEC` / `0x02D430D8`) records each overlapping pair on both sides
  (`0x02C10F40`).
- **Resolution, each side on its own record** (`0x02C0A708`, f1 = its own damage): the other's damage is its hitbox's
  (AttackModule vt `+0x104`) x two multipliers of its owner (vt `+0x344`, `+0x234`); **battle_object param 55** (9.0, the
  table at `[0x102FDC70]`, param n at `+4n`, read at `0x02C0A7C4`) is the margin: own - 9 >= other's -> the record is
  dropped (`0x02C10B54`), that side goes on untouched; else it loses: Rebound 1 -> the rebound (its duration and pushback
  from the larger of the two damages, stored with the larger one's Hitlag multiplier), Rebound 0 -> its module's
  `+0x120` set (the attack cancelled). A side loses if any of its records loses.
- Not traced: where the aerial / grounded clank rule lives (no situation test in the pass above).

## Stage line test (Byleth v9: `tools/line_test_cave.py`, exe_v46v_line)

**Space:** code + data `0x04BCA000`-`0x04BCB800` (zero in exe_v46v: the free end of Smash Run's region H, before the
temporary diag caves' `0x04BCC000`); variables `0x0F0003D0`-`0x0F0003DA`; command index `584 + 0x200` (1096,
`Line_Test`, CRC `0x71F1A048`).

- **The game's test:** GroundModule (accessor `+0x2C`) vt entries `0x02C39F18` ray_check(GM, V2 *from, V2 *dir, V2 *out,
  bool all) and `0x02C39FB4` the same with V2 *normal before the bool (the hit line's `+0x48` / `+0x4C`): from + dir is
  the end; `all` 1 -> `0x02D4CD68(stage [0x102F7DB4], out, GM+0x18 -> +0x244, from, &end)`, 0 -> `0x02D4E724` with mask
  `0x102000` (the passable platforms left out); r3 the line (non-zero: met). In six GroundModule vtables (`0x100D35EC`,
  ...). Posture: the MSC PostureModuleF wrapper `0x030B2AF0` (accessor `+0x18`, vt `+0x154`: 0 lr, 1 x, 2 y).
- **Hooks, all chaining** (each word asserted as acmd_ext_cave.py wrote it, or a `b` an earlier cave put there, which is
  then replayed): acmd_ext's `lk_none` (`li r3, -1`), `s1_orig` / `s2_orig` (the game's size-table reads), `f_orig`
  (its handler-table read), and hv_var's `hvv_zero` (`b buf_var`: the user_entry IDs nothing answers). **Order with
  tools/var_reset_cave.py (exe_v46w_vars):** var_reset first (it asserts the original words there), then this one
  (it chains on var_reset's branches): exe_v46v_threads -> var_reset_cave -> line_test_cave; tested both ways round
  this one allows (`tools/line_test_test.py` on exe_v46v_threads and on exe_v46w_vars: 29 / 31 checks).
- **Per object:** 32 entries of 0x40 (round robin): +0 WorkModule, +4..+0x10 the points, +0x14 the mode, +0x18 hit,
  +0x1C distance, +0x20 / +0x24 the point, +0x28 kind, +0x2C / +0x30 the normal. The accessor from acmd_ext's cache
  (`acc_of`, filled by its per-frame hook).
- **Diag on top:** tools/diag_godfist_cave.py chains on `hvv_zero` too (its stub then goes on to `lt_var`).

## Variable resets (exe_v46w_vars: New_Var's Reset, Var_Reset_Set)

`tools/var_reset_cave.py` (on exe_v46v_threads), test `tools/var_reset_test.py` (unicorn, 81 checks), user docs
`docs/acmd-extra-commands.md` "Variable resets". **Claimed region: `0x04BD8000`-`0x04BE0000`** (code `0x04BD8000`-
`0x04BD88C4`, data `0x04BD9F00`, the reset lists `0x04BDA000`; `textregion:0x2BE0000 grow:0x04BE0000`).
`0x04BD6000`-`0x04BD8000` (between ts_data's end and this) was free; `0x04BD6000`-`0x04BD7000` is now the whip motion
table's (Byleth v15, below), `0x04BD7000`-`0x04BD8000` the hitbox hold's (rapid_setoff v1, below). `0x04BE0000`-`0x04BE2000`
(past this region, the text region grown again) is the camera effects' (camera_effects v1, "Camera effects" below). `0x04BE2000`-`0x04BE3000` (grown again) is the screen invert's (screen_invert v1, "Screen colour" below). `0x04BE3000`-`0x04BE4000` (grown again) is the outline's and `0x04BE4000`-`0x04BE5000` (grown again) the mesh visibility's (model_commands v1, "Outline" / "Mesh visibility" below). `0x04BE5000`-`0x04BE8000` (grown again; to `0x04BE7000` before exe_v46z_outline4) is the outline shell's (model_commands v2, "Outline shell" below). `0x04BE8000`-`0x04BEA000` (grown again; to `0x04BE9000` before exe_v46z_ui2) is Supamario's Ultra Instinct cave (exe_v46z_ui / exe_v46z_ui2, "Supamario's Ultra Instinct" below). The combined exe the user runs:
exe_v46v_threads -> var_reset_cave.py (exe_v46w_vars) -> tools/line_test_cave.py (exe_v46w_vars_line, which chains on
four of these hooks).

- **Lists:** 48 blocks of 0x200 keyed by the owner's WorkModule (`+0`; round robin past 48), 31 items of 0x10 from
  `+0x10`: {ID (0 free), value (float), mask, 0}. IDs compare without their top nibble (`0x1F000380` = `0x0F000380`).
  `vr_event(WorkModule, bit)` writes each item with the bit through the WorkModule's own set_float (vt `+0x4C`, the
  path SET_FLOAT / MSC take, position_vars' and acmd_ext's hooks included); a KO write drops the item's KO bit, an item
  left with no bits is freed. A busy count (data `+0`) makes the MSC selection IDs ignore writes while an event writes.
  Counters at data `+0x20`: KO / landing / ledge / hit events, items written, items set, refused (list full), set-up
  KO fires.
- **Owner's WorkModule from a fighter's StatusModule:** `[sm +0x9C]` the fighter, `[fighter +0x28]` its module accessor
  (the step wrapper `0x02E40C4C` passes it), checked by `[acc +0x20] == sm`, then `[acc +0x28]`.
- **The events, found where the game handles them:**
  - **KO / ledge** - `0x02E88D00` (`stw r28, 0x48(r30)`: the status change `0x02E88B28` storing the new kind, after the
    old status's end scripts; every status change of every fighter, MSC requests and native ones alike; r0 r3-r12 and
    LR free there) -> `vr_chg`: the old kind read first; new == old: nothing; Dead `0xB1` (reference/msc-note-sheet:
    "KO'd"; position_vars' input reset uses the same status) -> KO; CliffCatchMove / CliffCatch `0x72` / `0x73`,
    AirCatchHit / AirCatchHang `0xF3` / `0xF4` from a status outside those four -> ledge. (`0x02E88B40`, earlier in the
    same function, is acmd_ext's hk_lgc_chg.)
  - **landing** - `0x02E890EC` (`stw r28, 0x84(r29)`: the fighters' StatusModule set_situation, vt `+0xEC` =
    `0x02E88FFC`, which every situation change goes through: MSC `StatusModule(2)` and op 5's init settings call it,
    the native leave-the-ground code too; it has already copied the old one to `+0x88`; the only other `+0x84` stores,
    `0x02E88774` / `0x02E887F0`, are the module's reset / constructor) -> `vr_sit`: old 2 (air) and new 0 (ground).
  - **hit** - acmd_ext's `gs_hit` (`0x04BD3990`, the DamageModule owner vt `+0x14C` hook Gravity_Set added: the
    damage reaction decision `0x02E76BB4`, called from DamageModule vt `+0x94` `0x02C22EF0` after the armor check
    `0x02C24C88`): its word at `+0x20` (`lwz r3, 0x10(r1)`, reached only when the decision returned 0, the hit takes
    effect) -> `vr_hit`: the accessor gs_hit saved at `0x10(r1)`, its WorkModule, bit 8; back to `+0x24`. Armor with
    no override and knockback under work float `0x2A` return non-zero (no reaction): no event. Shield hits never reach
    the DamageModule; an invincible / intangible hurtbox gives no damage call.
  - **set-up** - `0x02BF5864` (the object set-up's WorkModule reset, already a `b` to the hv_wmreset chain, kept: the
    cave ends with a `b` to whatever the word held) -> `vr_wmreset`: everything saved (only r0 r10 ctr are free there);
    a fighter's (StatusModule vtable `0x1012D42C`) unfired KO items fire (the Dead status may come first or not: once
    per KO either way), then the block is freed.
- **New_Var:** `cmd_handlers[34]` (New_Var's, `0x04B99EB0`) -> `vr_newvar`: Scope's word put to `& 0xFF` in place,
  `h_newvar` called with the same registers, the word put back; executed, for a New_Var ID: `vr_put(ID, Initial,
  (word >> 8) & 0xF)` on this object (Reset 0 removes an item, creates nothing). Old scripts: the same h_newvar call
  with the same words; the test compares the variables' memory after the same New_Vars with exe_v46v's handler.
- **Var_Reset_Set** (CRC `0x048FC81B`, index 2000, 5 words: Variable, Reset, Value, Owner): `nc_target(accessor,
  Owner)`, that object's WorkModule, `vr_put`. The command tables: acmd_ext's `lk_none` (`li r3, -1`) -> `vr_lookup`,
  `s1_orig` / `s2_orig` (the game's size reads) -> `vr_size1` / `vr_size2`, `f_orig` (`slwi r6, r7, 2`; the next word
  replayed) -> `vr_fetch` (r12 kept). A later cave adds its command the same way after these (line_test_cave.py does).
- **MSC IDs** `0x0F0003CA`-`3CD`: buf_var's `bv_zero` (`b ue_zero`, `0x04B7BF4C`) -> `vr_var` (user_entry's frame);
  others go on to ue_zero. Selection kept globally (write the four together).
- **Not confirmed in game:** that every landing passes set_situation (static reading says so); the order of Dead and
  the respawn's set-up; the KO / ledge / hit events' timing against the MSC (the test runs each hook site with the
  game's code around it, not a match).

## Whip motion table (Byleth v15: `tools/master_whip_motion_cave.py`, exe_v46x_whipmot)

**Claimed region: `0x04BD6000`-`0x04BD7000`** (half of the gap left free above: zero in exe_v46w_vars_line; inside the
text region since exe_v46w_vars, nothing grown). `0x04BD7000`-`0x04BD8000` is now the hitbox hold's (rapid_setoff v1, "Hitbox hold" below). Order: exe_v46v_threads ->
var_reset_cave -> line_test_cave (exe_v46w_vars_line) -> this one (exe_v46x_whipmot); it touches none of their words, so it
also goes on v11's TEST_ONLY diag exe (exe_v46w_vars_line + diag_godfist_cave) unchanged.

- **A weapon's motion info is a static table**, not built at run time: the descriptor (`0x0320D934(_, kind)`) `+8` ->
  `{entries, count, 0, 0, 0, 0, -90.0f, 90.0f}`, an entry `{zlib.crc32(.omo name without the extension, 0xFFFFFFFF), 0}`
  (the pack loader's key, `tools/mtable.py` anim_hash: `FitSZerosuitWhipMainC03AttackS4S` = `0xBB5DDD33`; a raw
  `crc32(name)` search finds nothing, which the v14 handover took for a run-time table). The article set-up copies the
  pointer into the init block (`0x02BCBB20`: `lwz r9, 8(r28)` -> `+0x58`); the motion number the article is given
  (ACMD Set_Anchored_Article_Action: ArticleModule MSC op `0x2715` (article, motion), handler `0x02BD62A0` (v17 reading; v15
  wrote `0x271B` / `0x02BD8AF8`): below, "Article ops (Byleth v17)"; its own MSC
  MotionModule) plus its custom number (whip.mscsb func_40: int `0x10000005`) indexes it. ZSS's whip: 15 animations x 4
  (custom moves 0 - 3).
- **Byleth's whip (0x1A0)**: weapon_expand_append.py's descriptor copy `0x04B9C680`, motion info `0x04B9C438` ->
  `{0x04B9C458, 60}`. The cave writes a new entries table at `0x04BD6000` (her 60, then 4 per new motion, each the hash of
  `FitSZerosuitWhipMain` + `master_whip.NEW_NAMES[slot]`: 112 entries) and the motion info's `+0` / `+4`: 2 words in place,
  asserted (her copy's values or the cave's own), the region asserted zero. The whip's `motion.mtable` grows to the same
  112 (its scripts by motion number) and its `main.pac` holds the new animations.
- **Test** `tools/master_whip_motion_test.py PATCHED BASE [PAC]` (unicorn: the game's descriptor getter for every weapon
  kind 0 - 0x1BF on both executables; only 0x1A0's motion info differs; her 60 entries kept; the new ones' hashes; every
  entry has its animation in the pac; nothing else changed but the region and the 2 words; idempotent): 20 checks on
  exe_v46x_whipmot vs exe_v46w_vars_line and on the diag pair. Not run: the weapon MotionModule's own change of motion
  (slots past a base's count are used by Sephiroth's flash, dein's 8 -> 12, which plays them in game).
- `port_check` X7 article-motion-slot (ERROR): a body script's Set_Anchored_Article_Action slot (+ 3) past the install
  executable's motion info for that article's weapon kind, or whose entry names no animation in its `motion/<article>/
  main.pac`.

## Ledge boxes, energy suspend, the catch record (Byleth v10)

- **The ledge box as the game checks it** (`0x02D62D74(out, ground collision, pos)`, from GroundModule's use-box
  `0x02C36A34`, which stores vl group 7 entry n at the ground collision's `+0x204` x, `+0x208` y (x scale), `+0x20C` w,
  `+0x210` h (x scale x the size factor), `+0x214` 0.6 w, `+0x218` h): the anchor = the collision's position `+0x1D0`
  (the fighter's, set by `0x02D6493C`) + (x along the facing `+0x1F4`, y); mode `+0x1FC` 0: front only [anchor,
  anchor + w] x [y, y + h]; 1: behind only (0.6 w, h `+0x218`); 2: both (height max(h, h2)). The mode comes from the
  status's cliff check kind (StatusModule(0x5, situation, kinetic, correct, **kind**, ...), StatusModule `+0x7C`) through
  GroundModule `0x02C368B0`: kind 0 -> mode 3 (none), 1 -> 0, 2 / 4 -> 2, 3 -> 0 only while falling. ZSS's AirCatch
  (func_123) uses kind 1: a tether's box is checked in front only. `ultimate_vl_shapes.tether_box` maps Ultimate's
  cliff_hang_data rectangle to it exactly.
- **KineticModule 0x2715 - 0x2718** (kinetic_module_impl `0x02C510C4`, from `0x02C528FC`): 0x2715 / 0x2716 set / clear an
  energy's `+0x18` (enabled), 0x2717 / 0x2718 set / clear its `+0x19` (suspended: the update `0x02C50058` skips it; its
  speed stays). Captain Falcon's MSC pairs 0x2717 / 0x2718 on energy 1 (gravity); Byleth's SpecialAirHiHit and wall jump
  do too (`tools/kinetic_suspend_test.py`, unicorn).
- **The catch**: the capturer's CatchModule (vtable `0x10104410`, constructor `0x02C17F80`, 0x60 bytes) applies a catch in
  vt +0x8C `0x02C18DC8` from a record at `+0x1C` (the victim's object id `+0x34`, the grab box index `+0x43`; the
  victim's CaptureModule vt +0xBC with the box's TargetStatus / flag); no direct store to the record was found (a struct
  copy from the collision pass, not traced). The victim's catchability each frame: `0x02E2528C` (status data `& 0x800`;
  Damage 0x46 leaves it catchable).

## Facing and the model's turn (Byleth v16)

- The fighter PostureModule (accessor `+0x18`, vtable `0x10129264`) keeps the facing `lr` at `+0x60` and the model's
  turn `rot_y` at `+0x64` (= lr x 90 when they agree). `vt+0x7C` set_lr(f) (`0x02E5CF18`) writes `+0x60` and posts a
  facing event; `vt+0x84` reverse_lr (`0x02E5D020`) = set_lr(-lr); `vt+0xC4` update_rot_y_lr (`0x02E5D2AC`) writes
  `+0x64` = lr x 90 and tells the model; `vt+0xCC` (`0x02E5D3E0`) negates `+0x64` (and tells the model).
- ACMD: `Reverse_Direction` (0x63623560, handler `0x02BD42E0`, index 454) calls vt+0x84 only: the hits and the
  movement face the new way, the model doesn't turn. `REVERSE_ROT` (0x1A019B6B, `0x02BD4A54`, index 455) calls vt+0xCC:
  the model's turn alone. MSC `PostureModule(1)` / `(2)` (the int handler, vt+0x14C = `0x02009D0C`) are vt+0x84 /
  vt+0xC4. The game updates the turn on a status change, so a turn inside one status needs `PostureModule(2)` (or
  `REVERSE_ROT` in the script) where the model should face the new way. No vanilla game script uses REVERSE_ROT;
  vanilla's 11 Reverse_Direction (ZSS: escapef at 16, throwb at 9, ...) end their status soon after, with an animation
  authored for it. Byleth's SpecialLwTurn (Ultimate's turn motion turns his hip 157 degrees over 12 frames and ends on
  SpecialLw's pose turned 180): master.c turns the model where SpecialLw resumes (port_check S26 turn-rot).

## Article ops and the results scene's params (Byleth v17)

- **ArticleModule's MSC dispatcher** `0x02C05FB0` (ArticleModule vtable `0x10102D08` `+0x17C`; 8-byte entries, the
  function at `+4`): `op - 0x2710` indexes a jump table at `0x02C06058`. `0x2713` (ACMD Set_Remote_Article_Action,
  STATUS_CHANGE_ARTICLE, handler `0x02BD7A74`) and `0x2714` (Set_Remote_Article_Action2, STATUS_CHANGE_EXIST_ARTICLE,
  `0x02BD7B24`) share one case (`0x02C06B44`; 0x2714 first asks vt `+0xFC` "exists"): vt `+0x8C` (`0x02C045B0`) ->
  every instance of the article, `0x02BEED10` = the weapon's StatusModule (accessor `+0x20`) vt `+0x2C(status)`: a status
  request, applied at the weapon's next status shift (its MSC line). `0x2715` (Set_Anchored_Article_Action,
  MOT_CHANGE_ARTICLE, `0x02BD62A0`) -> vt `+0x74` (`0x02C04340`) -> `0x02BEEC18`: MotionModule (accessor `+0x44`) vt
  `+0x64` change_motion(motion, frame 0, rate 1) at once; nothing about the link or the space. `0x2712` Remove_Article
  -> vt `+0xEC` (`0x02C05594`) -> vt `+0xE4`. `0x271C` Article_Visibility (`0x02BD661C`) -> case `0x02C06960`.
- **The whip's generation callback** (Byleth's article table entry `0x04B9C750`: `{0x1A0, max 1, 0x02F8172C, 0}`, ZSS's
  the same callback): reads the owner's status (`+0x7264` -> `+0x48`) into the init data: byte `+0x68` = status
  0x153 / 0x154, `+0x69` = 0x35 / 0x37 / 0x39 / 0xF1 (her grabs and AirCatch). Kind 0x38 / 0x1A0 has its own native
  handlers in the weapon switches `0x02B651AC` (case `0x02B65D20`), `0x02B6B7A8` (`0x02B6C468`), `0x02B73AA4`
  (`0x02B74374`) and shares 0x29 / 0x42's in `0x02B75A88`, `0x02B77FAC`, `0x02B7A4DC` (not read further).
- **`param/ui/result_param.bin`**: a generic param file whose fighter group (61 entries in 1.1.7: "missing", the 58
  fighters' model names, ...) has 22 values an entry, named by the Xtal bindings registered at `0x030D37C4`: `name`
  (type byte 0x0A: a u32 length and the model name reversed, XOR "Smash" repeated), win1 - win5, mvp_motion,
  mvp_motion_x / _z, team_motion, team_motion_x / _z, mvp_camera_x / _y / _z, team_pos_scale_factor, eyex / eyey / eyez,
  tox / toy / toz (a loser panel's camera). "missing" is all 0: a kind without an entry gets a loser panel with its camera
  on its target (empty). `tools/result_param.py`; port_check R2. The name is 0x0275DB24's: `lis r0, 0x04BA; slwi
  r12, r3, 2; addic r0, r0, 0x148; lwzx r3, r12, r0`, the kind-indexed lowercase name table at 0x04BA0148 in the expanded
  executables (exe_v46x: 0x41 - 0x47 `supamario`, `edge`, `gaogaen`, `pickel`, `brave`, `pzenigame`, `master`), the
  folder names. Vanilla's win N is 80 - 100 % of the fighter's J02WinN length (24 poses of 8 fighters, median 0.957).

## Hitbox hold (rapid_setoff v1: `tools/hitbox_hold_cave.py`, exe_v46y_hold)

**Claimed region: `0x04BD7000`-`0x04BD8000`** (the last free part of the gap before var_reset's region; zero in
exe_v46x_whipmot, inside the text region; code `0x04BD7000`-`0x04BD72F8`, HH_EXT `0x04BD72F8` (128 x 8)). Order:
exe_v46x_whipmot -> this (exe_v46y_hold). Test `tools/hitbox_hold_test.py EXE` (unicorn, the game's code around every
hook: 54 checks on exe_v46x_whipmot).

**Ultimate's setoff (ExeFS main.bin, dynsym + .rela.dyn):** `AttackData__store_l2c_table_impl` (0x1FEECD0 -> 0x1FEEDA0)
stores each field under its member's hash40: `set_off_` is the byte at **AttackData +0x62** (`power_` +0x20, `vector_`
+0x28, `r_eff_` / `r_fix_` / `r_add_` +0x2C-0x34, `slip_` +0x38, `stop_frame_` +0x3C, `target_category_` +0x50,
`lr_check_` +0x6A, `no_stop_` +0x6D, ...). AttackModuleImpl's vtable is 0x4F695B8 (`set_attack` vt +0x68 = 0x3DC180,
`set_set_off` vt +0x728 = 0x3E2DA0: it writes the kind into EVERY slot's data +0x62 and sets / clears bit 0 of the
slot's collision word). set_attack (0x3DC398) builds the hitbox's collision word with 0x22 | (set_off != ON), the
layout of Smash 4's (0x22 / 0x23 << 6 there, "Clanks" below). The clank resolution (0x3E0A50, battle_object
`rebound_power_diff` 9 as Smash 4's param 55): the losing side with set_off ON (0) or THRU (2) gets its cancel flag
(module +0x244: the rebound), OFF (1) / NO_STOP (3) go on, NO_STOP with no clank hitlag. So **the setoff kind is the
clank kind** (ON / OFF / THRU = Smash 4's Clang + Rebound 1 + 1 / 1 + 0 / 0 + 0: `ultimate_acmd.SETOFF`); nothing of
it reaches the victim's knockback. Ultimate's knockback speed (0x403A20, a DamageModule virtual): reaction x
`damage_speed_mul` 0.03 (367: the hitbox's motion), and **for 361 with the resolved angle 0 (a grounded victim under
`damage_angle_ground_reaction_min` 60): x `damage_angle_ground_zero_speed_mul` 0.8** (battle_object.prc); 60 - 88 ramp
to `damage_angle_ground_max` 38 degrees. Smash 4 (battle_object params 18 - 21): the same 0 under 60, 40 at 88, no
0.8. So an Ultimate rapid-jab victim slides 80 % of what Smash 4's does: Ultimate holds better, not completely.

**Smash 4, where a hit moves its victim:** the victim handler `0x02C25318` (r27 the victim's accessor, r28 the hit info
with the hitbox data's copy at +0x44, r19 = StatusModule vt +0xDC: the victim's situation, 0 ground) computes the speed
with `0x02C25208` (reaction x param 21 0.03; 366 with the flag: the hitbox's motion), the vector on its stack 0xC /
0x10 (0x02C25798 - 0x02C257C8: x = speed cos(angle) (-lr), y = speed sin; 365: the hitbox's motion), decides the
reaction kind / ground bounce from it, and at **0x02C25BF4 - 0x02C25C00** stores it into the damage event's +0xC /
+0x10 (event +0 the knockback, +0x30 the hitstun at 0x02C25C88: acmd_ext's HIT_STUN). The fighter's event handler
(`0x02E7A4DC`, a switch on the event kind) reads +0xC / +0x10 (e.g. 0x02E7BF50), adds work floats 0xF / 0x10 and gives
it to the damage energy (`0x02C5474C`). DamageModule's add_damage (`0x02C21A1C`, from 0x02C22648 with its own copy of
the data at sp+0x24) resolves 361 into that copy's angle (0x02C21DC0) and records the reaction at record +0x10: the
hit info's copy keeps the hitbox's own angle.

**Hooks:**
- VEC `0x02C25BF4` (`lwz r8, 0xC(r1)`, asserted with the next three words) -> `hh_vec`: loads the vector into r8 /
  r11 as the game does, 0 / 0 for a held hit, back to `0x02C25BFC` (its stores). Free there: r0 r5-r7 r9 r10 r12.
- SLOTSET `0x02C0874C` (acmd_ext's `b slot_set`, asserted to be it) -> `hh_slotset`: clears the HH_EXT entries of the
  slot set (r26), then `b slot_set` (which zeroes the tag).
- The command tables: line_test_cave.py's `find` (lk_none / s1 / s2 / f), chained in front of whatever is there.
  Hitbox_Hold index 2100, CRC 0xAB0FC57C, 3 words.

**The mark:** the hitbox data's +0x66 halfword (acmd_ext's Extra tag; no game code reads it, the hit info carries the
0x68 bytes): a plain hitbox gets 0xED00 | Mode (acmd_ext reads only a 0xECxx tag: find_copy / ext_find / hv see no Extra
hitbox); an Extra hitbox (0xEC00 | n) keeps its tag and gets HH_EXT[n] = {slot, Mode}, valid at hit time while acmd_ext's
entry n names that slot and the hit's data matches its check words (angle, KBG, FKB, BKB, bone: find_copy's). Hold:
Mode 2 always; Mode 1 when r19 == 0 and the vector's y word as an int is <= 0 (0, -0, downward).

**Not confirmed in game:** that every reaction path of the fighter's event handler takes its speed from the event's
+0xC / +0x10 (the ones read do); the tumble with a zero vector (Mode 2 on a big hit); items / projectiles as victims.

## Camera effects (camera_effects v1: `tools/camera_effect_cave.py`, exe_v46z_camfx)

**Claimed region: `0x04BE0000`-`0x04BE2000`** (past var_reset's region, the end of exe_v46y_hold's text; the text region
grown: `textregion:0x2BE2000 grow:0x04BE2000`; code `0x04BE0000`-`0x04BE0928`, the table `cf_tab` `0x04BE0928`-`0x04BE0E28`
(16 x 0x50)). Order: exe_v46y_hold -> this (exe_v46z_camfx); it chains on the earlier caves' command-table fallbacks
(line_test_cave.py's `find`, now hitbox_hold's branches) and asserts every other word it replaces is the original.
Test `tools/camera_effect_test.py EXE` (unicorn, the game's own code around every hook: 59 checks on exe_v46y_hold).
User docs: docs/acmd-extra-commands.md "Effect_Camera".

**No eft camera mode.** Checked first: Smash 4's eft (NW4F, docs/ptcl-format.md) has nothing that puts an emitter set in
camera / screen space: an emitter's follow type (0x310: 0 follow the set's matrix, 1 none, 2 position only) is relative
to its emitter set; the particle types (0x4BC) turn single particles (billboards, Y billboards), not the set; the camera
offset (0x4D0) is a clip-space depth bias. The effect manager has two camera-aware instance modes, both still world
placed: flag `0x20` / `0x40` (`0x0334E59C` / `0x0334E76C`: the set's matrix turned toward the eye, the look-at
`0x033737E8` from the effect camera's eye) and `+0x150` (`0x0334E96C`: moved that far toward the eye). So the cave
writes the instance's matrix from the camera every frame.

**The camera the game draws with:**
- **Camera manager** `[0x10352470]` (getter `0x02D29634`, 678 callers; made by `0x02D29018`, 0x7C0 bytes, vtable
  `0x1011E1C8`): vt `+0x54(kind 0-12)` a camera controller (`+0x10`... `+0x3C`), vt `+0x5C` the render camera (`+0x4E0`,
  102 callers), vt `+0x3C` the update (`0x02D2A584`: the controllers, then the render camera into the **snapshot block**
  `+0x780`: `+0` FOV (the render camera's `+0xE4`), `+8` near (`+0xE8`), `+0xC` far (`+0xF0`), `+0x10` eye (`+0x8C`
  + the shake `+0xBC`), `+0x1C` target (`+0x80` + shake), `+0x28` up (`+0xA4`); a matrix camera (flag `0x104 & 2`) gives
  eye = its position `+0x70`, target = eye - its Z axis x `+0xE0`).
- **Camera object** (the update `0x02D27F58`; Xtal's `set_camera_pos` `0x02914120` / `set_camera_look_at`
  `0x02914254` write it): `+0x80` target, `+0x8C` eye, `+0xA4` up, `+0xE4` vertical FOV in radians (clamped 0.01 -
  pi - 0.01), `+0xE8` / `+0xF0` near / far, `+0xF8` a zoom (`+0xFC` = 2 atan(tan(fov / 2) / zoom)), `+0x100` aspect
  (16/9), `+0x10C` / `+0x110` tan of the half horizontal / vertical FOV, `+0x00` its view matrix, `+0x40` the inverse
  (rows: right, up, back, eye). Defaults (`0x02D28CB8`): FOV 0.7156 (41 degrees), near 2, far 100000, aspect 16/9.
- **Effect camera table** `0x10573CC0` (`0x0334A368()`; 2 entries of 0xE0: the TV, the GamePad; ctor `0x0334A0F0`):
  entry `+0xC` the current source, `+0x10` the next, `+0x14` three source slots. The camera manager registers its
  snapshot block as entry 0's slot 0 (`0x02D29FCC`: `0x0334A080(table, 0, 0, mgr + 0x780)`) and makes it current. The
  update `0x0334A02C` (after the manager's, `0x02FC8940`) runs `0x03349D24` per entry: the source's vt `+0x14`, then
  `0x03349A38(entry + 0x50, entry + 0x90, source + 0x10)` (the look-at `0x033496A0(view, &eye, &target, &up)`, a 4x4
  with the translation in row 3; then its rigid inverse at `+0x90`: rows right, up, back (eye - target), eye), copies
  eye / target / up to `+0x20`, and gives the renderer (`+0xD0`, the render manager `[0x10423DCC]`'s view) the source
  (`0x0330043C`: projection from `+0` FOV, `+4`, `+8` near, `+0xC` far, `0x0332C518`) and the eye block (`0x033001E0`).
  The effect manager's own camera-facing modes read entry 0's eye (`0x0334A0B8(table, 0, 0)` = `+0x20`).
- **Frame order:** the battle sequence (`0x02FF4DF8`) runs the objects (`0x02BF2544`: ACMD scripts, effect requests), the
  camera manager's update (`0x02FF51B8`), the effect frame (`0x02FF5368` -> `0x02D88A00`: the step rate, the manager's
  update `0x032EFAE4`), then the effect calc (`0x02FF54A4` -> `0x02D88C18`, once a frame (byte `[0x10352569]`) ->
  `0x032EFD04`); the battle step `0x029108D0` the same (`0x02910FC8`, `0x02911068`).

**Effect instances** (manager `[0x10353CA4]`, pool `+0x4040` in the exe_v18+ layout, 100 x 0x1C0): `+0` handle, `+4` the
effect id, `+8` the owner key (the module's `+0x10` | the request's flags), `+0x34` / `+0x1A1` follow target, `+0x50` the
3x4 matrix (rows, translation in column 3), `+0xB0` scale, `+0xBC` rotation, `+0xC8` position, `+0x138` / `+0x13C` /
`+0x140` the step, `+0x144` flags. The calc pass `0x032EFD04` (mutex `+0xEF44`) runs `0x0334E0C8` on each instance, then
eft's calc (`0x04A56B18` per group): the matrix is rebuilt from scale / rotation / position (`0x03373478`, Rz Ry Rx;
`0x033730A0` builds that rotation) unless **flag `0x8000`**; an instance with no follow target takes `+0x50` as it is
(copied at `0x0334E28C`), applies the billboard modes and `+0x150`, and gives it to eft (`0x032FF744(inst + 0x20, &m)`,
`0x0334EAA8`). Flag `0x01000000`: the step isn't multiplied by the global slow rate `[0x10439078]` (the effect frame's
1 / N). The world request EffectModule vt `+0x44` `0x02C29D10(module, id, &pos, &rot, flags, mta -1, 1, 0, f1 size)`
(MSC EffectModule's world op): its flags `0x00800000` = rate 1, not the owner's (else `0x00100000` / `0x00200000` with
the module's rate `+0x70` / `+0x6C x +0x74`); the handle in module `+0x14`. Terminate_Graphic_Effect (MSC `0x2723`,
vt `+0xC4` `0x02005AF0`) kills by id with the key masked `0x01003FFF` / `0xFF003FFF`: the request's flag bits (20-23) don't
matter. Kill by handle: `0x0334C6A8(handle, 0)` (vt `+0xAC`'s: the emitter set fades). The manager and these calls
were run in unicorn for the parts the test needs (the instance update up to its matrix, with and without `0x8000`).

**Hooks:**
- CALC `0x032EFD04` (`stwu r1, -0x28(r1)`, asserted) -> `cf_calc`: each tracked effect (its instance still has its handle,
  else it is dropped): Frames counted down (at 0 the kill facade, it stays attached while it fades), the camera read once
  a frame (`cf_camera`: table entry 0's current source, `0x03349A38` into the cave's own view / inverse, tanf `0x04ADE970`
  of FOV / 2), its matrix (`cf_mat`) written to `+0x50` and `+0x144 |= 0x8000` (| `0x01000000` unslowed); then the
  pass's own first word and `b 0x032EFD08`. No camera (no source): left where it was.
- The command tables: line_test_cave.py's `find` (lk_none / s1 / s2 / f), chained in front of whatever is there (hitbox_hold's
  branches in exe_v46y_hold). Effect_Camera index 2200, CRC `0xF20DCF58`, 12 words.
- **Handler** `h_camfx`: the accessor's EffectModule (`+0xA0`), its vt `+0x44` must be `0x02C29D10` (the fighter and
  weapon module classes `0x10105FE8` / `0x101228F8`); the local turn built once (`0x033730A0`), the camera read, the matrix
  computed; the request at the matrix's translation, rotation 0, size = the matrix's scale; then the new instance's `+0x50`
  and flags set at once (its first frame is already at the camera) and the handle tracked (16 entries; the 17th fades
  the oldest out). Anything missing (no module, another vt, no camera, a refused request): nothing tracked.
- **The matrix** (`camera_effect_cave.matrix()` is the Python reference): dist = Z (Mode 1: <= 0 -> 20), at least near + 1;
  k = dist x tan(FOV / 2) in Mode 1, else 1; P = eye + right X k + up Y k - back dist; W = [right up back] x L x Size k
  (Mode 2: L x Size k), rows of W with P as the 4th column.

**camera_effects v3 (exe_v46z_camfx3; clip 1f7de3cf, the user's Dr. Mario on v2's split test).**
- **What the clip shows** (60 fps, frame by frame): the up taunt's Stage_Freeze(1, 120) whites the 3D picture out
  from frame 20 to 139 (mean luma 123 -> 219 -> 123), the HUD intact; frame 20 has the stage washed out and the
  fighters still drawn. The black quad (Frames 120, fade 1/8) was killed at frame 140 and shows over 140-144 as a
  small dark blob left of the centre, fading: it is black, alpha-blended and not over the screen. The side taunt's
  dizzy stars (Mode 1, X 1.4, Y 0.7, Size 0.08) appear at frame 238 under the top platform's left end, up and right of
  Dr. Mario, 8-14 px each, and stay with the platform (frames 244 -> 337: stars (-25, -5) px, the platform's end
  (-22, -13), the far arch (-5, +7)): fixed in the world near the stage's depth; nothing at the top-right corner.
  The down taunt's ice smoke (Mode 0, Z 30, Size 0.25) is centred both times (the camera elsewhere the second time),
  about 0.75 screen heights across: what Z 30 gives.
- **Traced** (beyond v1's notes): the calc pass `0x032EFD04` skips everything while the manager's byte `+0xB1` is set
  and eft's calc while `+0xB0`; the instance update `0x0334E0C8` (only caller `0x032EFD7C`) gives eft the matrix
  through `0x032FF744(inst + 0x20, &m)`: `[inst + 0x28]` (the emitter set) `+0x350` = the 3x4, then `0x03425100` with
  the column-major 4x4 (translation `+0x320`, the X axis' length as the set's scale `+0x7AC`, `+0x340` = M x `+0x330`).
  An instance whose request had `r9` set (the world request passes 1; MSC's too) gets `+0x1A3`, so its emitter set's
  `+0x2CC` = 0.07 at creation (`0x0334DC70`) and its `+0x7C4` = 0.07 every frame (`0x0334EAC8`): eft's emitter calc
  puts `+0x2CC` in the dynamic uniform block's emp1.z (`0x04A65DF0`), and every eft vertex program tests it
  (`SETGT 1.0, emp1.z`): below 1 the particle skips the billboard matrix bm (it stays in the world's XY plane);
  `+0x7C4` flattens an effect *model*'s depth (`0x034243B0`). Flag `0x8000` is also the game's own "keep the follow
  target's scale out" in the follow path (`0x0334E30C`). The detach `0x0334F540` keeps a lost target's last matrix
  (`+0x1A1` 1, `+0x34` 0). The instance list `[0x10439088]` (by `+0x18`) is what the key-matched calls walk
  (`0x032F0F10`: `+0x19E` paused; `0x032F0F88` -> `0x0334FD60`: `+0x1A0` visible, applied by `0x0334FBFC` through eft
  vt `+0x64`). The battle camera fits its near / far clips to the stage's box every frame (`0x02D27D74(cam + 0x12C,
  cam, &near, &far)` from the camera update at `0x02D28B74`, after `+0xE8` / `+0xF0` = `+0xEC` / `+0xF4`): the
  snapshot's near (`+8`) is that fitted value, not the default 2.
- **v3's cave** (same region, `0x04BE0000`-`0x04BE2000`; `tools/camera_effect_cave.py`, 79 unicorn checks on
  exe_v46y_hold): cf_upd replaces the calc pass's `bl 0x0334E0C8` (`0x032EFD7C`): the game's update, then, for a tracked
  instance with `0x8000`, its emitter set alive (`+0x199`) and valid (`0x032FF640`), `0x032FF744(inst + 0x20,
  inst + 0x50)` again (the test runs it against an update that gives eft a matrix of its own: the camera's is the last
  eft gets); cf_flags also writes the matrix's translation to `+0xC8` and its scale to `+0xB0`-`+0xB8`; cf_camera falls
  back to `[0x10352470] + 0x780` (the camera manager's snapshot) when the table has no current source; Stage_Freeze's
  stop calls are hooked (`0x04BD4334` -> cf_sfz_on, `0x04BD4268` -> cf_sfz_off: On 1 `+0xD0` only, 2 the game's
  stop, 3 the Final Smash stop; docs/acmd-extra-commands.md "Time_Scale / Target_Time_Scale / Stage_Freeze").
- **The diag build** (`camera_effect_cave.py --diag`, TEST ONLY, exe_v46z_camfx3_diag): OSReport lines, an effect's
  first 30 calc passes then every 30th: `S4CC n cur nxt src cam mgrblk tan` (the effect camera table's current / next
  source, the block read, whether a camera was found, the camera manager's block, tan(fov / 2) as hex float), `S4CV
  eye tgt` and `S4CN fov near far up` (that block); (v4) `S4CS id h i why x y z` at every Effect_Camera (the handle and
  instance, 0 when not reached; why = started 0 / not 1 << 8 | Mode), and per camera effect (its first 30 calc passes,
  then every 30th) `S4CF k h i fl set fo b` (passes, handle, instance, `+0x144`, its emitter set `+0x12C`, follow
  target `+0x34`, bytes `+0x199` `+0x19A` `+0x19E` `+0x1A3`), `S4CM t x` (its `+0x50`: translation, X axis) and `S4CE
  em t x` (the emitter set's emitter count `+0x1DC` and its own matrix, read from `+0x1E4`: one word early, v5 fixes it); `S4SF n on mode mgr d0` (each
  Stage_Freeze stop / resume). Floats are printed as their hex words.

**camera_effects v4 (exe_v46z_camfx4): why the particles never followed (v3's log a5622166 and clips f0b4803a /
4b5545bf).** v3's diag printed the camera every frame (eye about (9.5, 26, 97), target (19, 14, 0), FOV 0.524, near 2,
the table's source = the camera manager's block) and no per-effect line: cf_upd's work depended on `0x032FF640(inst +
0x20)`, and `inst + 0x20` is the effect's **model** handle (the instance init `0x0334DD64`-`0x0334DDEC`: only when the
efc entry has a model, `0x033050BC` instantiates it; `0x032FF744` sets the model's matrix). The particles are eft's
emitter set `inst + 0x12C` (created by `0x04A55BF0` with a copy of `+0x50`: eft keeps its own, `set + 0x1E8` SRT,
`+0x218` RT (v5: v4 wrote 0x1E4 / 0x214), `+0x248` scales, written by `SetMtx` `0x04A4AFB8`). The instance update calls that `SetMtx` only at
`0x0334EEB0`, and only when r26 is set: by the rebuild from position / turn / scale (`0x0334E284`, which flag `0x8000`
skips: `0x0334E264`), the billboard paths (`0x0334E734` / `0x0334E760`) or the `+0x150` move (`0x0334EA10`). So every
camera effect since v1 drew its particles with the matrix it was created with (the request's place, turn 0), in the
world: the smoke and the square started at the screen's centre looked right, the stars were never in their corner,
and v3's clips show the square (a disc: the RayGunShotFlash2 texture is round) staying in the world as the camera
pans. Extra emitter sets: `+0x158` {set, id} x `+0x170` (three at most), the same check (`0x0334EF6C`). v4's cf_upd
(`tools/camera_effect_cave.py`) calls `SetMtx(set, inst + 0x50)` on each live set before the game's update and after
it (cf_eftset; the game's own gate words are asserted), then the model's `0x032FF744` if there is one; cf_dlog prints
for every tracked effect (its own frame count in the entry, `+0x50`; entries now `0x60`), S4CS at every
Effect_Camera. `tools/camera_effect_test.py` (82 checks) runs the game's own update to the gate (r26 1 without
`0x8000`, 0 with it: the cause, in the game's code) and cf_upd against a stubbed update and eft setter (both sets before
and after, dead / emitterless sets skipped, others untouched).

**camera_effects v5 (exe_v46z_camfx5): the game's 2.5D depth squash (v4's clips 9a9b6ead / 200b18be, log
bb4113b4).** v4's test: the squares and the smoke followed the camera; the corner dizzy stars (Mode 1, X +-1.4, Y +-0.7,
Size 0.08) were drawn as two clusters of 8-14 px stars about 0.25 half heights above the centre, ~100 px apart (the
corners are 1020 px apart, the stars at 20 units would be ~110 px), still while the camera was still, drifting with the
stage (a third of its motion) when it panned. The log: each star set's own matrix (S4CE) = the corner matrix (S4CM),
so the hand-off worked; S4CF's last byte (`+0x1A3`) 1.
- **`+0x1A3` is Smash's 2.5D mode.** The instance init stores the request's r9 there (`0x0334DBAC`; the world request
  `0x02C29D10`, and so Effect_Camera, passes 1). With it: the emitter set's `+0x2CC` (eft's emp1.z, default 1.0 at
  `0x04A55D84`) = 0.07 at creation (`0x0334DC70`, unless instance flag `0x00400000`; the vertex programs skip the
  billboard matrix while emp1.z < 1: `SETGT R0.y, 1.0, emp1.z`); the plane `+0x11C` (and `+0x114` / `+0x118`) = 0
  (`0x0334F2D4`); the model's depth x 0.07 (`0x0334EAAC` -> `0x032FF920`); and the **particle callbacks** the game
  registers in eft's system (`0x032EF93C`-`0x032EF9B0`: `+0xA68` slot 0 `0x033508C0`, slot 2 `0x0335086C`, slot 1's
  `0x033504F4` ending at `0x03350814`; the slot is the emitter's user-callback byte `0x034`) move the particle's world Z
  (`p + 0x40`) to plane + (Z - plane) x 0.07 (`[0x10196028]` = 0.07).
- **Only CPU particles run it.** eft's CPU emitter class (vtable `0x102C8C28`: emitter calc `0x04A64CE8`, particle
  calc `0x04A65480`) fetches the `+0xA68` callback for each particle after placing it (`0x04A65624` / `0x04A65680` ->
  `0x04A58678`: system `+0x9D4` override, else the emitter's `+0x34` slot) and calls it with {emitter instance,
  particle}; the GPU class (`0x102C8C7C`: `0x04A65FC0`) never does. A CPU particle's place: `p + 0x38`-`0x40` = its
  matrix `[p + 0x108]` x its local place `p + 0x14` (`0x04A629CC`); follow type 0 points `p + 0x104` / `+0x108` at the
  emitter's live RT / SRT (`+0x84` = set `+0x218` x local `+0x2A8`, `+0xB4` = set `+0x1E8` x local `+0x2D8`, every
  frame in the emitter calc), 1 / 2 at copies made at emission (`0x04A5C984`); the vertex program adds the quad to
  `v_inWldPos` (= `p + 0x38`) and projects with vpm (CB1 8-11; programs 506 / 507 read no emm). So a camera effect's
  CPU particles 185 units out (20 in front of a camera at 205) were drawn at Z 13, on the stage, near the screen's
  centre and ~10 x smaller; GPU particles (emitter flag `0x00800000`: the square, the smoke) were right. The common
  dizzy stars (efc 0x2C, PtcCommonPiyopiyo) are complex CPU emitters (flags `0x00380000`): `PiyopiyoStar` /
  `PiyopiyoStar02` (follow 0, a 4.3-unit circle 3 up, 5 stars every 30 frames, the emitter's Y rotation keyed 0 ->
  72 degrees over 30 frames, scale 2.4 / 4) and four flash / ring emitters (follow 1, 0.4 a frame).
- **eft's emitter set matrix** (`SetMtx` `0x04A4AFB8`): the 3x4 copied to `+0x1E8`-`+0x214` (not `+0x1E4`: v4's notes
  and diag read one word early), the RT (columns normalised) at `+0x218`-`+0x244`, the column lengths at `+0x248`
  (and x `+0x254` / `+0x258` at `+0x264` / `+0x268`).
- **v5's cave:** cf_flags (at the request and every frame) clears `+0x1A3`; cf_eftset writes `+0x2CC` = 1.0 on each
  live set before its SetMtx. `FLAT_SIG` asserts the game words. Draw path (emitter `0x31C`, 1 << it tested in the draw:
  the stars 5, the square / smoke 2) only picks the render state callback (`0x032EEBA0`, blend), not the view.
  `tools/camera_effect_test.py` (92 checks): the game's callback run on a particle with and without `+0x1A3` (Z 184.63
  -> 12.92 / kept), on an Effect_Camera effect after cf_flags (kept), the CPU / GPU calc's calls, emp1.z on live sets
  only, the diag's S4CE (emp1.z, the translation from `+0x1F4` / `+0x204` / `+0x214`, m00, the scale).

**Not confirmed in game:** that the TV's entry 0 is the camera every battle view draws with (Final Smash cameras register
their own sources? they would be read the same way, through the current source); the vertical FOV's use by the renderer
(Mode 1's scale follows the source's FOV as the projection gets it); the overlay's draw order against other effects.

## Screen colour (screen_invert v1: `tools/screen_invert_cave.py`, exe_v46z_inv)

**Claimed region: `0x04BE2000`-`0x04BE3000`** (past the camera effects' region, the end of exe_v46z_camfx5's text; the
text region grown: `textregion:0x2BE3000 grow:0x04BE3000`; code and data `0x04BE2000`-`0x04BE2710`, the diag build to
`0x04BE2A90`). Order: exe_v46z_camfx5 -> this (exe_v46z_inv); it chains on the earlier caves' command-table fallbacks
(Effect_Camera's branches) and on ts_tick_cave.py's tsu_clear, and asserts every other word it replaces. Test
`tools/screen_invert_test.py EXE` (61 checks on exe_v46z_camfx5). User docs: docs/acmd-extra-commands.md "Screen_Invert".

**How the 3D picture gets its colour (read from cross_f.rpx and shader/copy_color.nsh):**
- **The pass.** The 3D picture is copied at the end of the 3D passes with one of copy_color.nsh's programs, ids
  `0x441xxxxx` from the table `0x10428344` (96 ids), picked by `0x0332E398(mgr, colour, ?, b4, b8, b16, b32+)`: bit 0 of
  the index is r4, **colour correction**. The odd programs (`0x44100001` ...) read uniform block **PostEffectSettings**
  (CB6: `correct_param[0..2]`) and do `out.rgb = dot4(correct_param[i], (rgb, 1))`, alpha kept: a 3x4 affine colour
  matrix (rows R / G / B, column 3 an offset); the even ones are plain copies (`0x44100010` / `0x44100011` add an edge
  blend: luma 0.299 / 0.587 / 0.114 differences x 5 - 0.1). The 3D copy's call (`0x033333F0`, in `0x03333064`) passes
  r4 = 1 always; other callers (`0x0332E5FC`, `0x03336F60`, `0x03337038`, ...) pass 0 (captures, other copies).
- **The matrix.** The post-effect object (`[0x10423DCC] + 0x1FF0`, made by `0x034332C0`: 0x400 bytes, vtable `0x101A0D40`,
  ctor `0x03433068`; init `0x03433154`: a 0x100-byte uniform buffer at `+0x200` through the device's vt `+0x1C`, its
  binding `+0x300` vt `+0x24`). `0x034333B0` (called once a frame by the render manager's frame prep, `0x0333616C`, its
  only caller) builds the matrix from the parameters and writes it to `+0x100`-`+0x12C` (every word, paired-single
  stores), then `[+0x200]` vt `+0x3C` (lock; the `bctrl` at `0x03433544`), `0x04B811C0` copies `+0x100` (0x100 bytes)
  into the locked buffer, vt `+0x44` (unlock). Parameters (ctor defaults in brackets): `+0x304` luma scale [1], `+0x318`
  luma offset [0] (vt `+0x24`'s levels: centre c, width d -> scale 1 / d, offset -(c - d / 2) / d), `+0x30C` / `+0x310`
  chroma scale [1] (saturation) and `+0x320` / `+0x328` chroma offsets [0] (vt `+0x2C`), `+0x36C`-`+0x374` RGB gains
  [1] (vt `+0x1C`), `+0x35C`-`+0x368` a tint RGBA [0] and `+0x378` = 1 - its alpha (vt `+0xC`, mode 0), `+0x354` /
  `+0x358` [1]. Composed through RGB -> YCbCr (`0x105772B0`: 0.2989 / 0.5866 / 0.1145, -0.1687 / -0.3313 / 0.5, 0.5 /
  -0.4187 / -0.0813) and back (`0x105772F0`: 1.402, -0.3441 / -0.7141, 1.772), written at static init by `0x034335A8`.
  The constructor's values give the identity; a tint of colour C at alpha A gives `(1 - A) x + A C`.
- **The screen-effect manager** `[0x102F6C38]` (Screen_Tint's: EffectModule vt `+0x19C` `0x02003F80` -> `0x0334B77C`
  builds two 26-float parameter blocks, from (RGB, alpha 0) to (RGB, A), the rest neutral, -> `0x0334AD70`: an entry of
  10 x 0x15C, layer `+0xC` < 9, priority `+8`, owner key `+0x1C`, transition frames `+0x14`, blocks `+0x20` (current),
  `+0x84` (from), `+0xEC` (to); End_Screen_Tint vt `+0x1B4`). Its update `0x0334B250` (from the effect manager's frame,
  `0x032EFB78`, its only caller) adds 1 to each entry's frame, picks the highest priority of layer != 0 (`+0xE6C`, lerped
  into `+0xD98`) and of layer 0 (`+0xE70` -> `+0xE00`); the calc `0x0334B444` (`0x032EFE78`) gives the layer != 0 winner
  to the post-effect through `0x0334AC8C` -> `0x03302660()` = `[0x10423DCC] + 0x200C` (wrapper objects of vtable
  `0x101A20D0` around `+0x1FF0`): vt `+0xC` colour, `+0x1C` gains, `+0x24` levels, `+0x2C` chroma; with no winner it
  puts the neutral values back once (`+0xE79`). The **layer 0** winner goes to the stage instead (`0x0334C150` /
  `0x0334C158` read by the stage base method `0x02D1D308`, every stage's vtable: the stage's own colour `0x03301604`
  and its effects' visibility, key `0x01800000`). `0x0334B5FC` clears every entry (`0x032EE8D4`, `0x030E9C48`).

**The cave** (each word asserted):
- **LOCK** `0x03433544` `bctrl` -> `bl si_lock`: r3 / r4 / CTR saved; when a filter shows, `M' = A M` in place on
  `r30 + 0x100` (the 3x4 just written; A affine, its column 3 added to the offsets); then `bctr` into the lock with LR =
  `0x03433548`. The game's own matrix (and so Screen_Tint) is kept and filtered.
- **TICK** `0x032EFB78` `bl 0x0334B250` -> `bl si_tick`: the game's update, then the filter's frame (phase 1 fade in by
  1 / FadeIn, 2 held with Frames counted, 3 fade out by 1 / FadeOut, 0 off) and A recomputed: A = (1 - w) [I | 0] +
  w [F | f], F = Brightness (1 - 2 Strength) Sat, Sat[i][j] = k d_ij + (1 - k) luma_j, f_i = Brightness Strength +
  add_i (`screen_invert_cave.filter_matrix()` is the Python reference).
- **CLEAR** tsu_clear's last word (`b 0x02FB349C`, found from `0x02FB3498`'s `b`) -> `b si_clear`: phase 0, w 0, then
  back (r3 / r10 kept): the game's clear-all of the slow-motions (training reset, restart, match start / end).
- The command tables: line_test_cave.py's `find` sites, chained in front of Effect_Camera's branches. Screen_Invert
  index 2300, CRC `0x370CA2AD`, 11 words.
- **Tested** (`tools/screen_invert_test.py`, 61 checks): the command tables (vanilla, acmd_ext, Line_Test, Var_Reset_Set,
  Hitbox_Hold, Effect_Camera, Screen_Invert; both loaders, the fetch); the handler; the tick through the game's
  `0x0334B250` on an empty manager (fades frame by frame, Frames, Mode 0, replacing); the lock with a recording lock
  stub in CTR (the matrix it sees = `compose(filter_matrix(...), M)`, r3 / r4 / LR / sp / callee-saved kept, nothing
  done with no filter); the clear through the real tsu_clear; the builder `0x034333E4`-`0x03433540` run in a Python
  interpreter of its own words (paired singles: unicorn can't), on the YCbCr constants `0x034335A8` writes: the
  constructor's parameters -> identity, Screen_Tint's (0.08, 0.09, 0.17) at 70 % -> `0.3 x + 0.7 C`, chroma 0 -> the
  luma rows; every word of `+0x100`-`+0x12C` written each call.
- **The diag build** (`--diag`, TEST ONLY, exe_v46z_inv_diag): OSReport lines `S4IC mode s fr in out sat bri` and `S4ID
  add(3) ph w` at each command; per locked frame (the first 30 after a command, then every 30th; with no filter every
  600th lock, to show the builder runs) `S4IS n lock ph w left on` (frames ticked, locks seen, phase, w, Frames left,
  matrices changed), `S4IG` / `S4IH` the game's 12 matrix words, `S4IO` / `S4IP` ours. Floats as hex words.

**XV2 (adam_shader, read for this):** `NegaposiFilter_PS` (shader_default_ps.emz, DXBC) is `out = tex x (-1, -1, -1, 1)
+ (1, 1, 1, 0)`: a plain negative, alpha kept, no strength; `LerpFilter_PS` blends two pictures by `g_vLerp_PS.x`.
The clip's stop (b66e8a38) fits 0.8 x luma(negative) + (19, 37, 60) on the background (the fighters keep their colours:
XV2's negative is applied to the world before the characters).

**Not confirmed in game:** that the 3D copy is the colour-correct program in every battle view (r4 = 1 at `0x033333F0`
is read from the code; Screen_Tint's visible darkening says the matrix reaches the screen); that the HUD is drawn after
it (Screen_Tint leaves it); the colour pass's place relative to the stage's own layer-0 colour; GamePad views.

## Outline (model_commands v1: `tools/outline_cave.py`, exe_v46z_ol -> exe_v46z_outline)

**Claimed region: `0x04BE3000`-`0x04BE4000`** (past the screen invert's, the end of exe_v46z_inv's text; the text region
grown: `textregion:0x2BE4000 grow:0x04BE4000`; code `0x04BE3000`-`0x04BE3D28`, the diag build to `0x04BE3FF8`; the table
`ol_tab` 16 x 0x50). Order: exe_v46z_inv -> this (exe_v46z_ol) -> tools/mesh_vis_cave.py (exe_v46z_outline). It chains on
Screen_Invert's command-table fallbacks, its tick (si_tick) and its clear (si_clear), and asserts every other word it
replaces. Test `tools/outline_test.py EXE` (unicorn, 59 checks on exe_v46z_inv). User docs: docs/acmd-extra-commands.md
"Outline_Set".

**How a fighter's rim is drawn (shader/texas_cross.nsh, 620 NUD shaders; `nsh_dump.py`'s GX2 headers parsed for the
uniform blocks):**
- The NUD materials name their shader by their flags (Dr. Mario: 0x9601106B, 0x9A011063, 0x9A211067, 0x9AE11165). A lit
  fighter pixel program (e.g. 0x9A011063) reads two uniform blocks: **MC** (CB4, 0x70 bytes: aoMinGain, specularColor,
  **fresnelColor** +0x20, colorSamplerUV, specularParams, **fresnelParams** +0x50, alphaBlendParams: the material's NU_
  properties) and **FB1** (CB7, 0x2A0 bytes: lightMapMatrix, **blinkColor +0x40**, g_constantVolume / Offset,
  uvScrollCounter, spycloakParams +0x80, compressParam +0x90, **g_fresnelColor +0xA0**, depthOffset +0xB0, outlineColor
  +0xC0 (read by no texas_cross pixel program), the model's lights (ceiling / ground / ambient / three directional),
  fogColor, **g_fresnelOffset +0x1D0**, ShadowMapParam, charShadowColor, ..., g_constantMin +0x250, characterColor +0x290).
- The rim: `rim = (1 - N.V)^(fresnelParams.x + 1) x (vsRim x sat + g_fresnelOffset.rgb) x clamp(N.y + 1)`; vsRim =
  fresnelColor x g_fresnelColor (the vertex program, clause 05), sat = (c - max(c)) x fresnelColor.w + 1 (c the colour
  texture); added to the lit colour, then the overlay: `out = lit x (1 - blink.a) + blink.rgb x blink.a` (the vertex
  program computes both terms per vertex from blinkColor). Dr. Mario's materials: fresnelParams.x 1.02-3.08 (exponents
  2-4), fresnelColor 0.18-3.0.
- 120 of the 187 lit shaders with fresnelParams read g_fresnelOffset (families 0x94 / 0x95 / 0x96 / 0x98 / 0x9A / 0x9C /
  0x9E / 0xD4-0xDA / 0xF4-0xFC); 67 (0x...3063 / 0x...5061, fresnelParams.y / z used) and the unlit 0x92 / 0xA0+ don't.
- **FB1 is per model instance**: MI + 0x2A0 is its buffer object; MI vt +0x2C (0x0341E038 for the class of vtable
  0x101A0128, 0x03423E78 for 0x101A0338) locks it (vt +0x3C), DCZeroRange's it (0x2A0 bytes), writes blinkColor from the
  instance's colours (MI +0x40 / +0x60, the ColorBlendModule's), the lights (0x03423628), compressParam, characterColor
  (MI +0x290) ..., and unlocks it (vt +0x44: the `bctrl`s at 0x0341E2C0 / 0x0341E2DC, 0x034247B0 / 0x0342484C; r30 / r31
  the instance, r28 / r27 the locked data). A write before the unlock reaches that model's next draw only.
- **The instance of an object**: accessor +0x3C is ModelModule (MSC sys 0x27; vtable 0x10001648, source path
  "model_module_impl.cpp" at 0x10001596), +4 its model handle (0x032FF640 valid, 0x032FF668 / 0x032FF68C visible,
  0x032FF744 matrix, 0x032FF944 / 0x0342633C a mesh's visibility by name), the handle's +8 the instance: MI =
  [[acc + 0x3C] + 0xC]. MSC module offsets from the syscall table 0x104187A0 (entry = sys - 1): +0x38 ColorBlendModule
  (0x42; vtable 0x10104618: vt +0x4C set the overlay of a priority slot, 0x4C bytes each; FLASH / Color_Overlay's handler
  0x02BE3858), +0x44 MotionModule (0x12), +0xA8 VisibilityModule (0x39).
- GX2 calls found from the rpx's import relocations (R_PPC_REL24 to the .fimport symbols): GX2SetVertex / PixelUniformBlock
  in the device layer 0x036F3AC4 (a cached bind of buffer objects: +0xC size, +0x10 data), the material state's slot-4
  (MC) binds 0x036DFE2C (from 0x036DFFBC: [state + 0x14 + stage x 4]); DCZeroRange at 0x0341E0E0.

**The cave:** ol_fbA / ol_fbB (the four unlock `bctrl`s -> bl): the outline of the instance (if any) written into FB1:
g_fresnelOffset += colour x Alpha / 255 x weight; Tint > 0: blinkColor = the overlay mixed toward the colour by t = Tint
/ 255 x weight (A = a0 (1 - t) + t, rgb = (rgb0 a0 (1 - t) + colour t) / A); then the unlock with the game's r3 / CTR /
return address. ol_tick (TICK 0x032EFB78, before it screen_invert's si_tick): fades, Frames, the pulse (tri = |2 (t mod
F) / F - 1|, f = tri^2 (3 - 2 tri)), drops an outline whose object is KO'd (the fighters' StatusModule vtable 0x1012D42C,
status 0xB1) or whose model changed. ol_clear on the clear-all chain (after si_clear). The handler resolves the Target with
acmd_ext's nc_target (0x04B98A00). `outline_cave.apply_ref` / `pulse` are the Python references.

**The diag build** (`--diag`, TEST ONLY, in exe_v46z_outline_diag): `S4OC tgt acc mi rgb a` / `S4OD tint fr in out flash
k ph` at each command; `S4OT n k acc ph w eff left` per outline frame and `S4OF n mi off(3) blink.r blink.a` per FB1 write
(the first 30 frames after a command, then every 30th). Floats as hex words.

**Not confirmed in game:** that the fighters' draws bind MI + 0x2A0 as FB1 (CB7) (the layout matches field for field:
blinkColor +0x40, compressParam +0x90, g_constantMin +0x250, characterColor +0x290); which of the two instance classes the
fighters use (both hooked); how strong Alpha 255 looks against each stage's lights (g_fresnelOffset is added unscaled by
the stage's fresnel light).

## Mesh visibility (model_commands v1: `tools/mesh_vis_cave.py`, exe_v46z_outline)

**Claimed region: `0x04BE4000`-`0x04BE5000`** (past the outline's; `textregion:0x2BE5000 grow:0x04BE5000`; code
`0x04BE4000`-`0x04BE4C14`, the diag build to `0x04BE4D94`; the table `mv_tab` 32 x 0x20). Order: exe_v46z_ol -> this
(exe_v46z_outline). It chains on the outline's tables, tick (ol_tick) and clear (ol_clear). Test `tools/mesh_vis_test.py
EXE` (unicorn, 55 checks on exe_v46z_ol). User docs: docs/acmd-extra-commands.md "Mesh_Visibility".

**How the game shows a model's meshes (cross_f.rpx):**
- Per mesh a byte at `[[MI + 0x7DC] + 4] + index` (count `[[MI + 0x6E4] + 0x44]`): bits 0-1 the set state (0 hidden, 1
  shown, 2 follow the animation), bit 2 the animation's value, bits 4-7 last frame's result. The only writer is
  0x034232FC(MI, mesh, value, which) (44 callers): which 0 sets bits 0-1, which 1 bit 2.
- The visibility groups (Model_Changer = VIS_SET -> VisibilityModule vt +0xCC op 0x2711 -> vt +0x4C 0x02C762C8: the
  group's state byte, dirty flag +0x20, an event to the model) end in 0x03426140(MI, group) -> 0x034232FC(which 0) on the
  group's meshes (MI + 0x734's table; MI + 0x738 the linked ones). The by-name setter 0x0342633C(MI, name, value, which)
  walks the meshes ([MI + 0x6E4] + [+0x3C] x 0x14 the resource, its vt +0xA4(res, i, 0) the mesh, the mesh's vt +0x2C its
  name, strcmp): the game's own code uses it with names such as "Masterhand_End_VIS_O_OBJ". The motion's visibility
  animation writes bit 2 (which 1). Visibility(State) (VIS_WHOLE) is VisibilityModule +8 (vt +0x94), applied by its
  update 0x02C76F70 through ModelModule vt +0x164 (the whole model).
- What is drawn: the instance's vt +0x74 (0x03424E88, five vtables at 0x101A0128 ...): shown = bits 0-1 == 2 ? bit 2 :
  bits 0-1; the result per mesh into the model data's array, the visible list to the listener [MI + 0x7EC] when anything
  changed, then bits 4-7 = bits 0-3.

**The cave:** an override forces bits 0-1 to 0 / 1 and keeps the game's bits 0-1 (taken when it starts) in its entry;
mv_set (0x034232FC's first word -> b): a which-0 write to an overridden mesh goes into the entry instead (r3 1), so a
group change during the override comes back when it ends; mv_tick (TICK, before it ol_tick): Persist 0 ends when the
object's motion kind ([[acc + 0x44] + 0x38]) changes, a KO ends it, a changed model drops it, the others are written
again; mv_clear (after ol_clear) ends every override, writing the byte back while the object still has that model (the
accessor -> instance chain checked). The handler finds the mesh by the CRC32 of its name (the same walk as 0x0342633C,
zlib's CRC32 in the cave: mv_crc) or an index 0-255; Mesh -1 ends the object's overrides; Visible 2 one.

**The diag build** (`--diag`, TEST ONLY, exe_v46z_outline_diag): `S4MC tgt mesh vis per acc mi hit` at each command (hit:
meshes changed) and `S4MF n k mesh byte forced per kind` per override and frame (the first 30 frames after a command,
then every 30th).

**Not confirmed in game:** that the fighters' MotionModule keeps its kind at +0x38 (read from motion_module_impl's code and
earlier notes) and so that Persist 0 ends at the motion change; meshes drawn by another path than 0x03424E88's (none
found: 0x03420300 reads the same bits); articles' models (the same classes).

**v2 (model_commands v2, exe_v46z_outline2): meshes with several parts.** The user: "Mesh_Visibility doesn't disable the
mesh visibility for meshes with multiple parts, e.g. HammerM2_O_OBJ can't be disabled because it has Polygon_0 and
Polygon_1". What the code says about the entries:
- The resource the walk uses ([MI + 0x6E4] + its +0x3C x 0x14) is a NU::ActorObject (RTTI; its vtable's pointer is the
  typeinfo word - 4: vt +0x8C 0x0370F0A0 = +0x58 the mesh count, vt +0x94 0x0370F0A8 = +0x5C the LOD count, vt +0xA4
  0x0370F0B0 get(mesh, lod) = [+0x60][mesh + lod x count], vt +0xAC its setter, vt +0x19C / +0x1A4 the subset
  control +0xE0). Its counts come from the model resource's header (0x0370E9FC: [[model + 0x10] + 0x20] meshes, +0x24
  LODs, +0x1C bones). The model loader (0x036DD278) builds per NUD mesh (polyset: bounding sphere, name at +0x20,
  polygon count at +0x2A) one 0x40 entry (+0x20 its polygon count, +0x24 its first part) and per polygon a 0x30 part
  (0x036DD0C8: +0x20 the mesh's name object, +0x2A 1, +0x2C the polygon), so **one visibility entry per NUD mesh, with
  all its polygons**: the visible-index list goes to NU::ActorSubsetControl (vt +0x24: [MI + 0x7EC]), and
  NU::ActorRenderablePartSet (0x037306EC builds, 0x037301D0 / 0x03730390 walk) draws for each visible mesh index its
  list of parts (polygons). Each part is drawn by one NU::CommandDrawModel (0x03717514 builds it from the 0x30 part:
  [part + 4]'s +0x2A / +0x2C), skipping polygons whose material has no shader for the pass ([material + 0xC] 0).
- The game's own by-name setter (0x0342633C) stops at the first match; v1's walk already changed every match.
So by the code a mesh's entry covers its polygons, and v1 should have hidden HammerM2 whole; the cause of the user's
case isn't found statically (not confirmed: the mesh in another model (an article / a held item: Target 0 is the
script's own object), a part drawn through a path the subset list doesn't gate). v2 makes the name match cover any
layout: every entry whose name matches, **and every entry right after a match that has no name of its own** (a null
name or an empty string: a part of that mesh) until the next named one, for the hide / show and the restore (each gets
its own override entry, so the game's state of each comes back). The index form is the game's mesh index (NUD mesh
order, all its polygons). The diag build adds `S4MH mesh=%d part=%d` per entry changed (part 1: an unnamed one after a
match), so a log shows what each command reached (S4MC's hit= counts them). Test: `tools/mesh_vis_test.py` (63 checks:
a two-part mesh whose second entry has no name, two entries with the same name, a one-part mesh followed by a named
one; the group write to a part kept aside and given back). Dr. Mario's own two-part meshes (model.nud):
stethoscope_VIS_O_OBJ (shaders 0x9601106B / 0x9A011063) and MarioD_hair_O_OBJ (a blended polygon, src 1 / dst 1, and
an opaque one): the v2 in-game test hides both (tools/outline_shell_ingame_test_build.py, down taunt facing left).

**v3 (exe_v46z_ui4; `mesh_vis_cave.py` chk_str): names at unaligned addresses.** The walk checked the name pointer (the
mesh's vt `+0x2C`) with `chk`, which also requires 4-alignment. The model loader copies a model's mesh names into one
buffer back to back (`0x036DC8E8`: the buffer `[res + 0x90]`, a running offset `+0xA0`, strlen + 1 a name, no
alignment; its size from `0x036DB424`'s count), so most names start at an odd address: the walk read them as "no name",
never matched them, and swept them into the run of the mesh matched before (v2's rule). The user's Supamario v4 log
(S4UV): by name, his own meshes 6-8 changed with Mario_Nohat's command (5), Mario_Hair (32) and meshes 34-39 never;
laid out from the buffer's start, exactly meshes 0, 4, 5, 9, 13, 26, 29, 30 and 40-43 have aligned names. The fix: the
string pointer checked for the range only (the `andi.` a nop, the same size: exe_v46z_ui4 patches exe_v46z_outline4's
word `0x04BE4200`). This may also be the v2 report's cause (HammerM2_O_OBJ "can't be disabled"). `mesh_vis_test.py`:
names packed back to back (4 of 5 unaligned) each found. The index form never searched names.

## Outline shell (model_commands v2: `tools/outline_shell_cave.py`, exe_v46z_outline2; fixed in exe_v46z_outline4)

**v3 (exe_v46z_outline3, the user's outline_v2 test): no band ever drew.** The diag log (Dr. Mario's taunts): S4ST
`drawn=0 checked=~227 a frame refused=0`, S4SF writing the mark into the instance's FB1 (`fb=64F5C000`) every frame,
Mesh_Visibility working. So every draw was turned down before the block-table test, at the mark. The cause:
**NU::ConstantBufferWiiU's unlock (vt +0x44 = `0x037291BC`, its vtable's RTTI name at `0x10209E48`) swaps the block
in place** (`lwzx` / `stwbrx` per word over its size) and then `GX2Invalidate(0x40, data, size)`: the GPU reads uniform
blocks little-endian. The game writes FB1 big-endian before the unlock, as the outline's rim and this cave's colour do
(the GPU sees them right); but by the draw the CPU copy is swapped, so `lwz` of the mark read `0x534F3453`, never
`MAGIC`. os_chk now takes the mark both ways (SMAGIC = MAGIC byte-swapped). The width (`lfs`, only tested against 0)
and the blend word (only tested against 0) are the same either way. The same swap applies to every constant buffer the game builds through
that class: a cave that reads back a uniform block after its unlock reads it swapped. The diag build's S4SF adds
`marked=` (the draws that carried the mark: os_g +0x24). `outline_shell_cave.draws()` tells an exe_v46z_outline3 shell
from v2's (port_check X13 errors on v2's).

**v4 (TEST ONLY, the user's v3 test): the game crashed on the first shell drawn.** Log: S4SF marked=0 for two frames,
then nothing more after a frame's draws (the first mark taken: no S4SR, no S4SX). Read so far, none conclusive: Cemu maps
virtual = physical (MMU.cpp `memory_virtualToPhysical`), so programs in the code area are readable; GX2SetVertexShader /
GX2SetPixelShader read only the structs' registers and program pointer; special.nsh exports a masked PARAM0 too. The
game records draws into GX2 display lists per core (`0x032EF244`: 11 passes, each sized by its pool's room;
`0x032EEFC4`: 0x400 bytes on the stack; `0x04A58018`: 0x200), and Cemu's display-list writes don't stop at the end
(GX2Command.cpp: a flush is a no-op in a display list), so the shell's extra commands (~300 words a mesh) could overrun
one. The v4 diag build logs S4SP per step (1 the mark taken, 2 the programs set, 3 the states, 4 the draw, 5 the
restore) for the first 24 shells, with the core (OSGetCoreId's stub `0x04B80340`) and four return addresses up the
stack; `--variant noprog` (the game's programs for the second draw) and `--variant nodraw` (no second draw) isolate
the programs and the draw. The programs moved to `0x04BE6A00` / `0x04BE6E00` to make room (os_g grew a word): the
release words differ from exe_v46z_outline3's, not shipped yet.

**v5 (TEST ONLY): the v4 logs were empty for a reason.** All three v4 exes crashed, with no S4SP line, the nodraw one
too. Cemu's log is written by its own thread from a queue (CemuLogging.cpp `cemuLog_thread`), so the lines just
before a crash are lost: v3 / v4's logs only say the crash comes within milliseconds of the first marked draw. The
v5 diag build pauses 50 ms (OSSleepTicks, stub `0x04B80970`, 3107812 ticks) after each line, and logs S4SM the moment
a draw's pixel-stage FB1 carries the mark (os_dmark, called before os_chk: the context, FB1, the vertex stage's FB1,
the geometry shader, the pixel shader, its blocks), then S4SP's steps for the first 4 shells (DIAG_STEPS 4).
Diag format strings shortened to fit below the programs.

**v6 (exe_v46z_outline4): the crash was the GX2 calls.** The v5 log ended in Cemu's crash report: IP `0x04B80974`, in
the NU::CommandManager thread, from os_dmark's pause (stack: os_dmark <- os_draw <- CommandDrawModel `0x037174EC`).
`0x04B80970` is not OSSleepTicks: it is where the FILE's `bl OSSleepTicks` points. **Cemu resolves every import to an
HLE entry of its own and rewrites the game's REL24 calls at load** (rpl.cpp: a relative `bl` when in reach, else an
absolute `bla` (AA set) to a trampoline `addi / addis r11, mtctr, bctr`), so the file's targets mean nothing at run
time; they lie in the grown text, i.e. other caves' code (`0x04B7BD08`, "GX2SetVertexShader", is in APC_CODE). The
shell's 14 GX2 calls (v2-v5) and v4 / v5's OSGetCoreId / OSSleepTicks all went there: the first shell drawn jumped
into other code. (diag_crumbs_cave.py v1 hit the same trap decoding a `bl OSReport` at run time; it missed the AA bit.)
Now `os_resolve` reads the game's own call at a site per import (IMPORTS: the GX2 sites, OSSleepTicks `0x03335974`,
OSGetCoreId `0x032EF0F8`) as Cemu left it, honouring AA, once, into `os_fn`; every call goes through CTR; a site that
isn't a `bl` / `bla` leaves no shell drawn. The region grew to `0x04BE8000` (`textregion:0x2BE8000`), the programs at
`0x04BE7400` / `0x04BE7800`. `tools/import_call_check.py` lists any cave word calling an import at a file target (0 in
every other cave of the user's exe); outline_shell_test runs it on both builds and emulates Cemu's relocated sites
(a relative bl, absolute blas to trampolines). port_check X13 errors on exe_v46z_outline2 and 3 (`draws()` wants the
swapped mark and the os_site table).
**Confirmed in game (exe_v46z_outline4, the user's clip of Time Skip v9):** no crash; a light band outside
Supamario's silhouette through the charge and dash (inner edges too, e.g. the arm across the body: an inverted hull's
look), light around him on the stop's negative (the black-over band inverted), gone at the punch.
**Rule for every cave: never `bl` an import's file target.** Call imports through a site's run-time target
(os_resolve) or a relocated veneer.

**Claimed region: `0x04BE5000`-`0x04BE7000`** (past the mesh visibility's; `textregion:0x2BE7000 grow:0x04BE7000`; code
and data `0x04BE5000`-`0x04BE6244`, the diag build to `0x04BE66FC`; the programs at `0x04BE6800` (vertex, 0x348 bytes)
and `0x04BE6C00` (pixel, 0x120), 256-aligned; the table `os_tab` 16 x 0x50). Order: exe_v46z_ol -> tools/mesh_vis_cave.py
v2 -> this (exe_v46z_outline2); it also builds on exe_v46z_outline (v1 mesh visibility). It chains on the outline
cave's FB1 hook (ol_fbgo's `bl ol_apply`), the mesh visibility's tick (mv_tick), clear (mv_clear) and table fallbacks.
Test `tools/outline_shell_test.py EXE` (unicorn, 97 checks on the v2 mesh visibility's exe). User docs:
docs/acmd-extra-commands.md "Outline_Shell".

**Why a shell:** Outline_Set (v1) colours the fighter shaders' rim term, which is a lighting term on the model's own
pixels: in game (the user's Time Skip clip) it reads as lighting, inside the silhouette and thin. The user wants a band
outside the silhouette (XV2's BPE 85). Options: (1) an inverted hull: the meshes drawn again, pushed out along their
normals, front faces culled, flat colour; (2) a screen-space silhouette (mask, dilate, composite): the game has a mask
pass (shader/special.nsh: the fighter vertex transform, a one-channel PIX0 = 0) but no hook to dilate / composite and
no spare target was found; (3) a stronger rim (v1's limits). (1) was feasible: the draw path, the device's state
caches and the GX2 programs are all reachable, so it is what this does.

**How a fighter's mesh is drawn (cross_f.rpx; RTTI names from the NU library's typeinfo):**
- NU::CommandDrawModel (vtable 0x10207DC0, execute 0x037173EC = [0x10207DCC]) draws one polygon part (see "Mesh
  visibility" v2): the vertex declaration ([cmd + 8] -> device +0x28), PerDraw (CB2) bound to the vertex and pixel
  stages (0x036F3AC4 stage 0 / 4, slot 2), per sub-draw (0x40 each at [cmd + 0x24]) the material (0x036E1450,
  0x036E157C, 0x036DFFBC: the shaders, the material's blocks MC / FB1 through 0x036DFE2C / 0x036F3AC4, the
  blend / depth / rasterizer states 0x036F464C / 0x036F4C2C ...), the vertex buffers (0x036F38E8), the index buffer
  (0x036F4338), then the draw: 0x037174D8 `bl 0x036F3EDC` (DrawIndexed, instances [cmd + 0x1C]) or 0x037174E8
  `bl 0x036F3EC8` (vt +0xB4 with one instance). DrawIndexed (NU::DeviceContextWiiU, vtable 0x10206444: +0xB4)
  flushes the attributes / fetch shader (0x036F3CE0, GX2SetAttribBuffer / GX2SetFetchShader through its caches) and
  calls GX2RDrawIndexed.
- The device context's caches (each read off the code that fills it): +0x1C4 the GX2VertexShader (0x036F4340), +0x1C8
  the geometry shader (0x036F43FC), +0x1CC the GX2PixelShader (0x036F453C), +0x1D0 + 8 x slot the vertex uniform
  blocks {data, size} and +0x2B0 + 8 x slot the pixel ones (0x036F3AC4), +0x3B0 the blend state (0x036F464C: +0xC + 8 x
  target the GX2BlendControlReg pairs, +0x4C the GX2AlphaTestReg, +0x58 the channel masks), +0x438 the depth / stencil
  state (0x036F4AE0: +0x440 DB_DEPTH_CONTROL, +0x444 the stencil masks), +0x44C the rasterizer state (0x036F4C2C: +0x450
  PA_SU_SC_MODE_CNTL, +0x454 the polygon offset), +0x468 the colour control (+4 logic op, +8 blend mask, +0xC
  multi-write, +0x10 colour buffer on). GX2 import stubs: SetVertexShader 0x04B7BD08, SetPixelShader 0x04B7BBC0,
  SetPolygonControlReg 0x04B7BC08, SetDepthStencilControlReg 0x04B7BB18, SetBlendControlReg 0x04B7BA48,
  SetColorControl 0x04B7BA70, SetAlphaTestReg 0x04B7BA10 (the rpx's import relocations).
- The programs: all 620 texas_cross vertex programs take a_Position at attribute location 0 and a_Normal at 1 (the
  fetch shaders' semantics); PerDraw (CB2) vec4 0-3 are the LocalToWorld rows (row-vector: world = p.x L0 + p.y L1 +
  p.z L2 + L3), PerView (CB3) vec4 0-3 the WorldToProjection rows, FB1 (CB7) vec4 9 compressParam (world z = C.x (z -
  C.y) + C.y), read off special.nsh's vertex program (the same opening clause as the lit ones). No program in
  texas_cross, special, only_alpha, instancing, mii, primitive or lumen reads FB1 vec4 12-15 (outlineColor and
  padding), so the cave owns them. The lit pixel programs declare uniform blocks MC (4) and FB1 (7, 0x2A0); the mask /
  shadow ones (special, only_alpha) don't have MC.

**The cave:**
- os_fb (ol_fbgo's `bl ol_apply` -> bl): ol_apply, then the instance's shell (if any) into its FB1 before the unlock:
  vec4 12 = (r, g, b, alpha), vec4 13 = (Width x weight, 'S4OS' (0x53344F53), blend, weight). Every other model's FB1
  has zeros there (DCZeroRange'd every frame by the game).
- os_drawI / os_drawN (the two draw calls -> bl): the game's draw; then os_chk: a shell in use, the pixel stage's slot
  7 data carries the mark (size 0x2A0), the vertex stage's slot 7 the same buffer, no geometry shader, the caches
  filled, the pixel program's block table (absolute, or the .gsh file's 0xD06xxxxx offsets from the struct) has 4 and
  7 (0x2A0), the width not 0. Then GX2SetVertexShader / PixelShader (the cave's), the cached PA_SU_SC_MODE_CNTL with
  the front faces culled (the back ones if the material culls front), DB_DEPTH_CONTROL with Z test / write on and
  stencil / back-face stencil off (its compare kept), CB_BLEND0_CONTROL 0x21000504 (Blend 0: SRC_ALPHA /
  INV_SRC_ALPHA) or 0x21000104 (Blend 1: SRC_ALPHA / ONE; alpha kept: ZERO / ONE, separate), the colour control with
  target 0's blend bit, alpha test off; the same draw again (r3-r9 as the game passed them); then the game's
  programs and every state set again from the caches (SetPolygonControlReg(ctx + 0x450), SetDepthStencilControlReg(ctx
  + 0x440), SetBlendControlReg(ctx + 0x3BC), SetColorControl(the cached four), SetAlphaTestReg(ctx + 0x3FC)), so the
  caches stay true.
- The programs (latte-asm sources in the cave script; one ALU instruction a group: no GPR read-port conflicts):
  vertex: nw = n L3x3 normalized (RECIPSQRT_IEEE; MUL's 0 x inf = 0 for a zero normal), world = p L + compress, Width
  < 0: world += nw |Width|; clip = world P; Width > 0: nc = nw P2x2, clip.xy += nc / |(640 nc.x, 360 nc.y)| x Width x
  clip.w (Width pixels of a 1280 x 720 picture). Exports POS0 and a masked PARAM0, as special.nsh's. Pixel: PIX0 =
  FB1 vec4 12. Registers: special.nsh's vertex ones (9 GPRs, NUM_SQ_VTX_SEMANTIC 2: semantic 0 -> R1, 1 -> R2) and
  pixel ones (no inputs). GX2 structs: those registers, size, program, mode 1 (uniform block), no metadata.
- os_tick (TICK, before it mv_tick) / h_shell / os_clear: Outline_Set's timing (fades, Frames, the pulse; a KO or a
  changed model drops it); the weight scales the width (the band grows / shrinks), the alpha stays.
- Depth write on: the stage drawn after the fighter can't paint over the band; a see-through band (Alpha < 255) mixes
  with what was drawn before it, not the final background (documented: Alpha 255 / Blend 1 recommended).

**The diag build** (`--diag`, TEST ONLY, exe_v46z_outline2_diag): `S4SC tgt acc mi rgb a` / `S4SD width fr in out flash
blend k` per command; `S4ST n k ph eff drawn checked refused` per shell frame (shells drawn, draws checked while a shell
is in use, marked FB1s refused); `S4SF n mi fb width a blend` per FB1 write; `S4SR n ctx vs ps fb width poly ds` per
shell drawn; `S4SX n ctx ps blocks ptr fb` per marked FB1 refused (the first 30 frames after a command, then every
30th). Read: checked 0 -> the fighters aren't drawn through CommandDrawModel's calls; checked > 0, drawn 0, refused 0 ->
the FB1 isn't bound through the device's cache (the mark not seen); refused > 0 -> the pixel program's block table
isn't as read (S4SX shows it).

**Not confirmed in game:** that the fighters' polygons are drawn through those two CommandDrawModel calls with FB1
bound through the device's cache (0x036F3AC4) in the main pass; that no other pass (shadow, reflection, the loupe)
uses a pixel program with MC and FB1 (it would get the band too); Cemu's / the GPU's acceptance of the cave's programs
in the text region (256-aligned, uniform-block mode) and of a fetch shader with more semantics than the vertex program
maps; the band's look at Width 1.5 / 3 (pixels of 1280 x 720) on Dr. Mario; the draw order (depth write keeps the band
when the background is drawn after the fighter; a part drawn after another may lose a sliver behind the first's band).

## Supamario's Ultra Instinct (`tools/supamario_ui_cave.py`, exe_v46z_ui; v5: exe_v46z_ui4)

**Claimed region: `0x04BE8000`-`0x04BEA000`** (v1-v3 to `0x04BE9000`; `textregion:0x2BEA000 grow:0x04BEA000`). Base:
exe_v46z_outline4 (the user's). Test `tools/supamario_ui_cave_test.py BASE [PATCHED]` (unicorn, 144 checks).
`tools/import_call_check.py` 0 (only game functions are called, through ctr). User-side: fighters/supamario/README.md
"Ultra Instinct v1".

- **Mario's specializer** (vtable `0x10139E60`; slot n at `+0xC + 8n`): slot 0 `0x02F1A6F0` (`li r5, 1; b 0x02F1A598`, his
  set-up: it builds the Cape's reflector, ReflectorModule `[acc + 0x72F8]` group 3; ShieldModule group 1 is free), slot 42
  `0x02F1B218` (`blr`), slot 43 `0x02F1B21C` (`li r3, 1`). Each is referenced once (its vtable entry). Kind test `[fighter
  + 4] == 0x41` (Mario is 3 in this numbering): nothing changes for Mario or any other kind.
- **Set-up:** Marth's group-1 build (`0x0200C858(M, desc, 1)`, then `0x0200BD8C(M, 0, 0, 1)` off); a capsule on joint 0
  (0, 2.5, 0)-(0, 9.5, 0), radius 6.5.
- **Slot 42** (shield hit, message +8 AM / +0xC damage / +0x10 record / +0x14 group): kind 0x41, group 1, status 0x157 or
  0x155, flag `0x21000010` off, record category < 3 (0x157: 0 only), hit data `+0x54 == 0`: status floats 6 damage, 7 side,
  8 / 9 the X / Y of the fighter to answer (category 0: the record's object; 1 / 2: the object's owner module `[acc +
  0x6C] +0x34`, the current owner, when it is a fighter id), flags `0x21000010` (+ `11` not a fighter, + `12` found).
  Handles: `0x02BF2108` / `0x02BEF50C` / `0x02BEF640` (edge_counter_cave.py's).
- **Slot 43** (the damage event `0x02E35EE4`, event id 0x12; its message is only read at +8, the handled byte, by the
  game's handler and by Marth's slot 43: no attacker fields are known): 0x157 -> 0; 0x155 with `0x21000010` -> 0; the
  autododge: Wait / Walk / WalkBrake / Squat .. SquatRv, TIMER_0 (`0x0F000320`, through his WorkModule's get_float vt
  `+0x44`) > 1500, and a live other fighter (table `[[0x1035184C]]`, entries of `0x76B0`, `+0x1E >= 4`) whose
  AttackModule (`[[entry + 0xC] + 0x50]`, records on `+0x4C`) has his object id in a part's record list (`[AM + 0x14] +
  part x 0x174`: sentinel `+0x124`, first node `+0x128`, node `+0x18` the object hit, `+0x27` the hitbox id), hit data
  `+0x54 == 0`: TIMER_1 (attacker to his right) / TIMER_2 = 4.0 through set_float (vt `+0x4C`), the handled bit, 0.
- **v4 (exe_v46z_ui2; region now `0x04BE8000`-`0x04BEA000`, `textregion:0x2BEA000 grow:0x04BEA000`):**
  - **Slot 42's owner CHAIN** (the user's v3 test: Secret Sensation blocked a Killer Eye's shot (an item placed by
    Donkey Kong) and didn't slide: v3 took the hit object's `[acc + 0x6C] + 0x34` once and required a fighter id, so a
    shot owned by an item failed): each step takes the object's `[acc + 0x6C] + 0x34` (the current owner: the
    reflector after a reflect, docs "Reflection"), else its LinkModule (`acc + 0x68`) link 0 (vt `+0x5C(0)` has it,
    vt `+0x6C(0, 1)` its id: "A weapon's owner"), an id of category 0-2 that isn't the object itself; a fighter ends
    it, a weapon / item is resolved (handle, alive) and followed, at most 4 steps; none (a stage item, a gimmick's, a
    loop): the stance plays out as before. Static reading + unicorn (`supamario_ui_cave_test.py`: the Killer Eye's
    chain both ways, Link's arrow by link 0, Samus's missile by `+0x34`, an article's shot, a stage item, a gimmick
    owner, a loop, a 5-step chain, a gone thrower). Not confirmed in game: which of the two fields the game fills for
    a placed item (the chain tries both).
  - **Mesh_Visibility Persist 2**: `mv_apply` (`0x04BE4294` in exe_v46z_outline4, its first four words asserted)
    branches to `mvp2` first: Persist 2 -> the game's setter `0x034232FC(MI, mesh, Visible (0-2), 0)` (mv_set still
    keeps it aside under an override), no table entry; else mv_apply's own first word and on.
  - **Why v3's copies always showed** (the user: silver eyes / white mustache at 0%): every model the repo holds has
    `model.moi` table 1's count = its NUD's mesh count (one entry per mesh, in order; table 2 the VIS names -> mesh
    index); v3 appended 13 meshes to the NUD and none to the moi (47 / 34). The game's own binding of a visibility
    track (`0x03427B58`: each track's name against the model resource's meshes, `0x0347A078`) and the mesh walk read
    `[[MI + 0x6E4] + 0x44]` (= the resource's vt `+0x94`, `0x03478A6C`); which count the moi feeds wasn't traced: v4
    gives the copies moi entries (`tools/moi.py`), so both counts agree whichever it is. A new mesh's byte starts
    `0xFE` (`0x03420B4C`: follow the animation, the animation's bit on): a copy the animation can't reach is drawn.
  - **The transformation's scripts (the user: no effects, sounds or hair change in SpecialLwLight):** motion 0x231's
    hash (`0x9221C757`) is in the motion table and in every installed .bin (sorted), so the lookup by files is right.
    Prime suspect, not confirmed: Mario's native code special-cases statuses **0x157 / 0x158** (F.L.U.D.D.'s shoot /
    end, `0x02F169D0`: transitions 0x152 -> 0x157 -> 0x158 -> 0x159, and for 0x157 / 0x158 a table at `0x101393A0`),
    and the motion change `0x027606C0` clears all three script agents when its byte `+0x2E` (set through vt `+0x4C`
    `0x027608B0`) asks for the linked object's kind and no link 0 exists (`0x02760750`): F.L.U.D.D.'s scripts are the
    pump article's (vanilla game.bin has none for the down special). The transformation, its counter (0x157) and the
    dodge (0x158) would then run no body scripts. The diag build logs it (S4UM / S4UB below); the fix, once
    confirmed: the transformation in another status (0x155 with a phase, as Fake Death's scripts run there).
  - **--diag (TEST ONLY, exe_v46z_ui2_diag)**, OSReport through the veneer `0x0288B4D4`, no pauses: `S4U2 st grp cat
    obj flags x y` per slot-42 call of kind 0x41 (flags: 0x10000 answered, 0x20000 not a fighter, 0x40000 found; x / y
    float bits), `S4U5 chain n ids` (the owner chain), `S4U3 st t0 found att unc ret` per slot-43 call (t0 TIMER_0's
    bits as slot 43 read it, att the attacker found in the hit records, unc the hit's uncounterable byte (-1 not read),
    ret 0 = no damage / dodge signalled), `S4UV mi mesh val before after` per Persist-2 write, `S4UM kind motion hash
    n` (`0x02E42518` hooked: its call from the motion change for kind 0x41; motions 0x229 / 0x231 / 0x235 / 0x239 /
    0x241 / 0x245 always, 20 others), `S4UB hash found set kind n` (`0x02BEE580`'s `bl 0x02BEE404`: the bind from the
    motion change for kind 0x41 and the UI / Entry / Wait1 / Fake Death / Sledgehammer hashes; set 0 game 1 expression
    2 sound 3 effect). At most 1500 S4UM / S4UB lines.
- **v5 (exe_v46z_ui3): the statuses and the script bind, read to the instruction (unicorn: `supamario_ui_test.py
  --exe`).**
  - The motion change's link-kind byte (`+0x2E`, the "0x157 lead"): `MotionAnimcmdModule` is the accessor's `+0xC4`
    (set by `0x02BF6A0C`; the fighter's `+0x72DC`); its vt `+0x4C` (`0x027608B0`: `+0x1C` motion, `+0x2C` r5, `+0x2D` r6,
    `+0x2E` r7, `+0x20` / `+0x24` f1 / f2, `+0x28` = -1, then `0x027606C0(this, 0, 1)`) has one caller that sets r7,
    the MotionModule's change `0x02C5E5EC` (vtable slot `+0xCC` of `0x1010A3EC` / `0x1012CCEC` / `0x10154C98`): r7 =
    MotionModule vt `+0x1F4(motion)` = `0x02C639E0`: `[this + 0x1C] + 8 x motion`, halfword `+6` bit 0x8 (the motion
    table, descriptor `+0x1C`; `0x02EA9008` adds only byte `+4` and bit 0x80 from vl group 1). Mario's (and kind
    0x41's) table has bit 0x8 on 0x7C-0x87, 0x96-0xC2, 0x1BE-0x20F only (catch / throw / thrown motions: the
    thrower's scripts), on no down-special motion. So the lead does not apply.
  - Mario's status-keyed code: `0x02F169D0` (vtable `0x101393C4` + 0x14, a status-change callback (this, accessor,
    new status); the current status from `[acc + 0x20]` vt `+0x8C`; kind 8 (Kirby, through `0x02BEF604`) takes
    0x1EB-0x1EE instead of 0x152 / 0x157-0x159): on leaving 0x157 / 0x158 (and 0x152 -> not 0x157 / 0x159, 0x159
    with the pump out) `0x02F1124C(acc, 0, 0)` (flag `0x20000078` off, a word at WorkModule +0x20C), then for a new
    status in the table `0x101393A0` (0x1B, 0x1F-0x22, 0x35) the pump kept (`[acc + 0xA0]` vt `+0x1DC(0x1A)`), else
    `[acc + 0xA0]` vt `+0x1E4(0x1A)` and ArticleModule (`[acc + 0x4C]`) vt `+0xEC(0, 0)` (the pump removed). Entering
    them: nothing. `0x02F11C0C` (`0x10138B7C`, the pump's per-frame placement) reads its owner's status 0x152 /
    0x157-0x159; `0x02F0FE84` / `0x02F0F2FC` / ... (the pump weapon) its owner's 0x157 / 0x158. None touches the
    script agents. Checked in unicorn on exe_v46z_ui3: the decision 0 for the UI motions (1 for 0x1BE), the placement
    reached for 0x152 / 0x157-0x159 only, the callback silent for every 0x155 transition (and acting when leaving
    0x157 / 0x158).
  - The move anyway (the user's v3 report stands unexplained): the transformation / counter / dodge are 0x155 modes
    (TIMER_4, README "v4, second build"); the cave tells them apart by TIMER_4 (`ui_isform`, get_float `0x0F000324`
    > 5.5). Diag: S4UM gains the status (`[[r27 + 4] + 0x7264] + 0x48`, r27 = `0x027606C0`'s module), and **S4U4** `st
    t1 t2 mode left`: after slot 43 writes a dodge signal (`ui_drec` +0x28 his module block, +0x2C 8 lines), the
    script module's late update `0x02760DB0` logs his status / TIMER_1 / 2 / 4 each frame; hooked at its one call
    `0x02E4133C` (`bl`; `0x02760DB0` itself is 0x2487000 from the cave, out of a `b`'s reach), the hook goes on to it
    through ctr. (`addi rX, r0, n` is `li`: the countdown uses r12.)
- **Not confirmed in game:** the hit records' timing against the damage event (records are the collision's "don't hit
  twice" log: present when the hit is dealt, by static reading); a stale record of an earlier hit of the same move could
  make a projectile hit in the same move's lifetime dodge.
- **ui4 (exe_v46z_ui4; README "Ultra Instinct v5"), from the user's v4 diag log (exe_v46z_ui3_diag, RPX hash 0946ac90):**
  - **Slot 43 is NOT the body's damage.** The fighter's event handlers are registered at `0x02E14288`... through
    `0x02E3C1BC(listener, id, r5, {flags, fn})`: event **0xB** `0x02E2AFBC` and **0xC** `0x02E2B59C` (the body hit's
    damage: they add it, `0x02E29C28(F, 1, f1)`, before asking any specializer slot; 0xB asks slot 56 afterwards: Kirby's
    "lose the copy when hit"), 0xA `0x02E31A90` (a generic notification, message type at `+8`: slot 38 first, 0 skips
    it), 0x10 `0x02E35794` (the shield hit: slot 42), 0x11 `0x02E35ED0`, **0x12 `0x02E35EE4` (slot 43: the shield
    DAMAGE that follows a shield hit**; Marth's counter queues its status there), 0x13-0x17 the reflector / absorb
    events (slots 44-47; Mario's 44 / 45 his cape's reflector). The log: S4U3 only at the same timestamp as an S4U2,
    never for DK's punches on his body ("Sephiroth's counter shape" corrected). The damage REACTION is DamageModule vt
    `+0x94` (`0x02C22EF0`) -> the owner's vt `+0x14C` (`0x02E76BB4` for fighters, acmd_ext's gs_hit), not a slot. The
    v1-v4 hit-record search (TIMER_0 read, fighters' AttackModule records) is gone with it.
  - So the autododge is the counter shape (`supamario.c` ui_shape keeps it on while transformed in Wait / Walk /
    WalkBrake / Squat .. SquatRv on the ground; TIMER_5 its marker) and slot 42 in those statuses (`s42_dg`): TIMER_0 >
    1500 through get_float, the side from the hitting object's place (handle; Marth's side when gone), TIMER_1 / 2 = 4
    through set_float; slot 43 there returns 0 + the handled bit (no guard damage / stun). Any category: the shape
    blocks whatever reaches it.
  - **Items are category 4** (`id >> 28`; the Killer Eye 0x4001000x in the log: `S4U2 st=155 grp=1 cat=4
    obj=40010000`); the handle lookup `0x02BF205C` has cases 0-4 (object managers `[0x1035184C] + 4 x cat`). Slot 42
    (Secret Sensation) and the owner chain (`ui_id_ok`) take 0, 1, 2 and 4 (3 still excluded).
  - **Mesh_Visibility's name walk** (mesh_vis_cave.py in exe_v46z_outline4) rejected unaligned name pointers (`chk`'s
    `andi. r0, r3, 3`): "Mesh visibility" v3. `WALK_FIX` `0x04BE4200` -> nop. The Ultra Instinct scripts use mesh
    indices anyway.
  - **The installed effect.bin was not the build's:** S4UB for SpecialAirLwHeavy (0x064F2A11) found no effect script
    (set 3), which the build's effect.bin has and Time Skip v10's lacks; SpecialLwLight's hash is in every vanilla-based
    .bin (F.L.U.D.D.'s scripts), so "found" there proved nothing. v5 ships every file the build changes.
  - **Diag (exe_v46z_ui4_diag):** **S4UF** `bank slot entries res motion` (the motion change of 0x231 / 0x245: bank
    0x341's slot `0x032EFEA0(mgr [0x10353CA4], 0x341, 0)`, the .efc's entry count `lha [[slot + 8] + 8]`, the .ptcl
    resource `[slot + 4]`); the effect runtime's print `0x04A58A8C` (a no-op in this build: "Emitter is Empty.",
    "Particle is Empty.", "Emitter Set is Empty.", "EmitterSet Remove Failed.", ...) branched to OSReport with its own
    arguments (at most 300 lines); S4U3 is now `st t0 ret`; S4U2's flags `| 0x321 / 0x322` when the autododge signalled
    TIMER_1 / 2 (then S4U4).
  - eft's emitter-set creation `0x04A55BF0` fails ("Emitter is Empty.") when the set's emitter count is above the free
    emitters (`[eft + 0x23C]`, from the config's `+8`), "Emitter Set is Empty." when no set instance is free
    (`0x04A54D48`); an effect id's index must be below the .efc's entry count (`0x0334D8D8`); the instance pool holds
    100 (`0x032F0110`).
