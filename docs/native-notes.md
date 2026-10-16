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
    knockback < threshold, mode 3 when damage < threshold.
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
