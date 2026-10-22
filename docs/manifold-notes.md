# Manifold: cross-reference with this repo's research

**Manifold** by Fitz Null (zlib License), https://gitlab.com/fitz.lol/manifold. It is a runtime mod
framework for Smash 4 (Wii U): an Aroma / WUMS module that replaces `cross_f.rpx` functions by text
offset (FunctionPatcherModule) and rewrites single instructions, with C++ reconstructions of the
game's classes. The repository's last commit (`a81e10a`) is "last time before archiving this".
Its code was read as data. Nothing was copied from it: this page and the "Manifold" notes in the
other docs summarise what it says, with addresses, and how that compares with our own findings.
Every address quoted as checked was checked against our `cross_f.rpx`.

It targets **the same `cross_f.rpx`** as this repo. These match: the kind descriptor getter
`0x02E4313C`, the vl param loader `0x02EA6BC4`, the param-manager kind loop `0x02EA5C9C`, and all
15 instruction words that `fighter::AddPatches()` rewrites. Each of those words matches its expected
original (`li` / `cmpwi` / `cmplwi ..., 0x41`). Manifold's addresses are ELF addresses, the same as
ours and Cemu's. On a console its macros add **`0x0A000000` to code addresses** (`CODE_OFFSET`,
`PROVIDE_FUNC`) and **`0x00503000` to data addresses** (`DAT_OFFSET`). Use these offsets to read
console memory with addresses from our docs.

## What it covers, and where it lands in our docs

| Manifold | What it has | Our doc | Result |
|---|---|---|---|
| `src/cross/fighter.cpp` / `.hpp`, `docs/add-new-fighter.md` | fighter kind enum, name tables, a real kind `0x41` attempt ("Wolf", `WOLF_TEST`; the final commit enables a `WARIOMAN_TEST` enum value only), 15 kind-count bounds, 104 "is Mii" call sites, unlock check, costume voice mapping, transform → base | `new-fighter-slot.md` "Manifold cross-reference" | confirms our tables. It adds 2 real bounds sites; 4 of its 15 are not kind bounds. Its Mii sites are a UI-id predicate that the clone plan doesn't need. Details there |
| `src/cross/ui.hpp` / `ui.cpp` | `ui_character_db` entry (`FighterParamEntry`, 0x4C), database vtable, `0x0293FD40` | `new-fighter-slot.md` | matches. Adds field names (`+0x18` "powerLimit", two 16-byte per-costume arrays) |
| `src/cross/flx2/*`, `InfoFlxSystem.hpp`, `flx.cpp` | flx2 runtime classes (`Object` 0x1C, `DisplayObject` 0x3C, `MovieClip` 0xEC), element API, `InfoGadgetDmg` (damage panel) layout | `flx2-format.md`, `native-notes.md` (damage panel) | confirms our offsets and functions. Adds names, rotation / colour-transform setters, dirty flags, slot child list. Our badge hook (vt `+0x3C`) is the better place. Notes there |
| `src/cross/lumen*`, `task/MenuLumenTask*`, `scene/*`, `docs/scene-hierarchy.md` | Lumen (`.lm`) menu runtime: `MovieClipInterface` `0x03268704`-`0x0326B160`, `MenuLumenTask` `0x030999C8`-`0x0309A854`; scene classes and their hierarchy | (menus not researched here) | new. Lumen is a different runtime from flx2. See the naming note in `flx2-format.md` |
| `scripts/decode_param_format.js` | packed-struct nibble descriptor decoder | `params/fighter_param_vl.md` section 1 | confirms it. Adds the nibble order and what padding means |
| `src/cross/stage*`, `stage/*`, `StageManager.hpp`, `StageDrawModel.hpp`, `StageDynamicObject.hpp` | stage kind table functions, `StageBase` (0x1120) / `StageBaseCafe` (0x1140) layouts and the full vtable (+0x14 ... +0x3AC), `StageManager` `[0x102F7020]` (0x110), stage-select patches | `stage-expansion.md` (Manifold already credited there), `minecraft-world.md` | confirms them. Adds the vtable slot names, LVD element filter hooks and model helpers. One naming disagreement (frame setter); notes there |
| `src/cross/gimmick/*` | `GimmickControllerBase` (0x34, vtable layout), `GconEventLadder`, `GconEventSpring`, `GconXMansionPillar` (Luigi's Mansion pillar, 0x74), `GconArea` | `minecraft-world.md` (v18 breakable blocks) | confirms `0x03133A8C` / `0x03133DAC` / `0x03133E4C`. Adds the classes |
| `src/cross/article.cpp`, `weapon.cpp` | item kind table (0x138 items) and weapon tables (0x185 = 389 weapons, four parallel tables) | `new-fighter-slot.md` (weapons) | confirms it: weapon tables `0x10419604` (name), `0x10419C18` (folder), `0x104189DC` (root), `0x10418FF0` (owner), loaded at `0x030BCB80`-`0x030BCBF0` in our builder `0x030BCB10`. Items: `0x104157A0`, 0x138 x 0x24 bytes, getter `0x0305368C` |
| `src/cross/BattleObject.cpp` | `BattleObject` (+4 kind, +0xC module accessor, +0x1E state byte), `BattleObjectManager` (0x16C) | `native-notes.md`, `minecraft-world.md` | confirms `obj+4` kind, `+0xC` module accessor, and the `+0x1E >= 4` live test used by our Minecraft cave |
| `src/cross/motionscript.*` | a 0x280-byte function table at `0x1012C220` (built at `0x02E788B0`) labelled "WorkModule" / "ItemModule" / "maybe DamageModule" | `native-notes.md` (WorkModule) | **unconfirmed labels**. Its "WorkModule" slot (`+0x1C4` = `0x02C489FC`) is not `WorkModuleImpl` (vtable `0x10003224`, MSC handler `0x0200E898`). Our WorkModule notes stand |
| `src/cross/resource*`, `resource/*`, `memory*` | resource system: `lib::Resource` ctor `0x032D7220`, `load` `0x032D9434`, `is_exist` `0x032D9600`, `request` `0x032D9894`, dtor `0x032D4200`; pack path `0x032D51D0`; patch list `0x032E0450`; name table `0x032EA7CC`; `ResourceContext` (0x133FC0); allocator `operator new` `0x03374578`, `delete` `0x0337460C`, heap alloc `0x03374530` | `native-notes.md` (short list) | adds these. `0x032D9600` is the "file exists" test in the fighter sound loaders (`params/fighter_files.md`) |
| `src/cross/xtal.cpp`, `testing.cpp` | xtal debug print hooks; `0x028E25C0` patched to return true (a kind-based "is Mii fighter", kinds 0-2); `0x030C1BBC` note: "seemingly only affects loading result screen motions" | `new-fighter-slot.md` | adds `0x028E25C0` (not in our predicate list) |

## Things Manifold gets wrong (checked)

- **`getCostumeVoiceId` (`0x030C1B34`)**: its replacement has two off-by-one thresholds. Olimar /
  Bayonetta switch at costume >= 4 in the game (Manifold: >= 3) and Little Mac at >= 8
  (Manifold: >= 7). Its own comments describe the right patterns. It also leaves out **Robin
  (0x2C)**, whose odd costumes use voice bank c01. `params/fighter_files.md` already had the right
  mapping.
- **`_CheckCosmeticUnlockState` (`0x0293FD40`)**: its version returns 1 for unlock type 0 before
  the usable check. For a DLC id with type 2 it returns 0, where the game requires `+0x4C`. These
  differences may be deliberate (its "unlock all DLC" option). The game's logic is written out in
  `new-fighter-slot.md`.
- **Kind bounds**: 4 of its 15 rewritten words are not fighter-count checks. They are copy loops of
  0x41 words (0x104 bytes). See `new-fighter-slot.md`.

## Status of its fighter work

Manifold's real-kind route (`0x41`) never worked. The "Wolf" redirects to Fox are commented out:
descriptor, vl load, module set-up `0x02E3F32C`, motion table `0x02EA9064` and specializer. In the
final commit `fighterNames` has 65 entries, so every bound it raises is written back to `0x41`.
`miiBullshit()` (the 70 forced "is Mii" sites) is defined but never called. It also never grows
the per-kind arrays in the FighterParamManager (`0x25B0` bytes) or the AI records. Those are the
blockers in our Option A. A kind `0x41` there writes into the next array (`mgr+0x111C+4*0x41` is
`mgr+0x1220`, the refcount of kind 0). This supports our choice of Option C, the clone in a
Fighting Mii Team slot.
