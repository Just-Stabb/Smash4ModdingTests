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

**Result:** `grab_test` (build A + the kind patch, with the per-frame `BattleObject(0x26)`) did
NOT remove the grab immunity.

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
      $(python3 tools/position_vars_cave.py) 0x02EF74A8=0x60000000 $(python3 tools/strike_cave.py)

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

## Hitboxes and hitstop (Kirby's Strike trait)

- **Hitbox creation:** every hitbox command (ACMD `Hitbox` `0x02BDB0EC`, `Special_Hitbox`, ...,
  table at `0x10350ED8`) builds 0x68 bytes of attack data and calls AttackModule (accessor `+0x50`)
  vtable `+0x54` = `AttackModuleImpl::set_attack` `0x02C086A8(this, id, part, data)` (vtable
  `0x10103524`, the only AttackModule class). It copies the data to slot `[this+0x40] + id*0x84`.
  Data: `+0x18` damage, `+0x1C` size, `+0x30` trip, `+0x34` hitlag multiplier, `+0x38` SDI,
  `+0x43` effect. AttackModule `+4` = the owning battle object (constructor `0x02C077F4`); a
  battle object's `+0` is its ID (category = ID >> 28, 0 = fighter) and a fighter's `+0xC` its
  module accessor.
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
  (damage first, from argument 3) and passes it to vtable `+0x64` at `0x02C0B790`.
- `tools/strike_cave.py` (cave `0x04B78C00`, tested in `tools/strike_test.py`) hooks `0x02C08730`
  (in set_attack, after the copy: Strike Kirby's slot damage ×1.15, hitlag ×1.2; crit bit `0x10`:
  ×2 more each), `0x02C27638` (attacker side, Strike Kirby: damage / 1.15 (crit / 2.3),
  multiplier / 1.2, so his own hitstop is vanilla, or 2× on a crit) and `0x02C0B77C` (throw data:
  damage ×1.15).

