# Adding a new fighter (research)

Status: **research only (static analysis of `cross_f.rpx`), nothing built or tested in game.**
Goal: a new fighter on the character select with its own model, animations, scripts and params, the
way `docs/stage-expansion.md` added a stage slot. Addresses are this repo's `cross_f.rpx` (the base the
caves patch, `build/cave_fix_s4/cross_f.rpx`). `tools/fighter_kind_tables.py` dumps the tables below.

## Summary

- **Fighter kinds are dense: 65 kinds, `0x00`-`0x40`, every one used.** There is no unused or dummy
  kind. (`fighter_param_vl_testfighter.bin` is in the data, but nothing in the executable names it.)
- **A 66th kind (`0x41`) isn't practical.** The stage kinds were read through three small functions,
  and the stage factory already handled unknown kinds. Fighter kinds are indexed directly all over the
  game. The worst problem is per-kind arrays sized `[0x41]` inside fixed-size objects:
  - the FighterParamManager (`0x25B0` bytes), with roughly a thousand hard-coded `0x111C + 4*kind`-style
    offsets;
  - the AI's per-player records (`8 x 0x488` bytes), each of which ends with two `[0x41]` arrays.

  On top of that, six kind switches have no case for `0x41`, and one of them aborts. Details under
  "Option A".
- **Recommended: reuse a kind no player picks and make it a clone of a base fighter.**
  - Take one of the Fighting Mii Team kinds (`0x3E`-`0x40`). As far as found, only Multi-Man Smash's
    Fighting Mii Team uses them (preloaded at `0x02825CA8`; `0x02FE3F18` also sets them up).
  - Rename it in place (folder name, Cap name, vl param file name).
  - Point its specializer, descriptor and AI cases at a base fighter X.
  - Write a small cave so its vl param load / unload store into its own slot.
  - Turn off the Mii-enemy checks for it.
  - Add a `ui_character_db` entry with a new character id (59). This mirrors the stage work: a name
    table cave plus database entry, portraits and MSBT labels.

  The roster gains a fighter and nothing playable is replaced. It gets its own `fighter/<name>/`
  folder (model, motions, ACMD, MSC, sounds, effects), its own `fighter_param.bin` attributes and its
  own vl param file. Its native behaviour (specializer hooks, status / motion layout, articles) is
  X's. Its MSC, ACMD and animations must follow X's motion and status layout, as Lucina's do Marth's.

## Fighter kinds

Name tables in `.data`: lowercase `0x102FF484` (folder / file names), Capitalised `0x102FF588`, and vl
param file names `0x10353DB4`. Each has 65 entries. Readers: `0x0275DB24` (lower) and `0x0275DB38`
(Cap), `lis/slwi/lwzx` with no bounds check.

| kinds | |
|---|---|
| `0x00`-`0x02` | miifighter, miiswordsman, miigunner |
| `0x03`-`0x39` | mario ... kamui (`0x24` mariod, `0x25` lucina, `0x26` pitb, `0x2E` koopajr; DLC `0x33`-`0x39`) |
| `0x3A`-`0x3D` | transformations: koopag, warioman, littlemacg, lucariom (base: `0x030BF9C0` / `0x030C1FDC`) |
| `0x3E`-`0x40` | miienemyf, miienemys, miienemyg (Fighting Mii Team) |

`python3 tools/fighter_kind_tables.py` prints the full list, with every per-kind address below.

Weapons (articles) have their own enum: 389 weapon kinds. Tables: name `0x10419604`, folder
`0x10419C18`, owner fighter name `0x10418FF0` (`mario`, ...), root `0x104189DC` (`fighter`).
Weapon resources are found by the weapon's owner name. A clone that uses X's articles therefore
loads X's article files.

## Kind-indexed code and data in the executable

### Kind switches (`cmplwi kind, 0x40` + jump table)

| switch | function | table | default (kind > 0x40) | what a case does |
|---|---|---|---|---|
| specializer | `0x02E669F0` | `0x02E66A10` | returns 0 | tail-calls the kind's getter → static singleton (e.g. lucariom `0x104FB944`, vtable `0x100977C4`) |
| kind descriptor | `0x02E4313C` | `0x02E43168` | **abort** (`0x04ADC364`) | returns the kind's static descriptor in `.data` (`+0` kind, `+4` {table, count (Mario `0x24B`), ...}, `+8` resource list with code pointers, `+0x10`-`+0x30`); 16 callers (fighter set-up `0x02E13870` / `0x02E14B90`, resources `0x030BFB08`, `0x030C0BE4`...) |
| vl param load | `0x02EA6BC4` | `0x02EA6CB4` | reads `mgr+0x111C+4k` without loading | kind's own parser into `[mgr+0x2574]+0x320+4k`, stores `mgr+0x111C+4k` (**fixed offsets in each case**), then a common tail (`0x02EA8D50`, more per-kind branches) |
| vl param unload | `0x02EA5D64` | `0x02EA5DC4` | - | frees `[mgr+0x2574]+0x320+4k` with the kind's own free functions |
| AI | `0x02E02440` (on `[ai+0x18]`) | `0x02E02474` | generic AI | per-kind AI routine (`0x026F....`) |
| AI | `0x0275B440` | `0x0275B46C` | returns 0 | per-kind AI routine |

Other kind switches stop at the playable kinds and send the rest to the default:
- AI: `0x026F4F0C`, `0x02704930`, `0x02704C94`, `0x02709740`, `0x0271CF30` (`0x39`),
  `0x02717488` (`0x3A`), `0x027011B4`, `0x027030FC` (`0x3D`), `0x02701B9C` (`0x3C`);
- HUD: Palutena's Guidance / Fox's Smash Taunt by character id (`0x0267E1A8` ..., `0x3A` on `id - 1`);
- Kirby's copy set-up `0x02EFC940` (`0x33`).

`tools/fighter_kind_tables.py --scan` lists all of them.

The specializer pointer is stored at `fighter+0x7538` (`0x02E11CC0`, in the fighter set-up
`0x02E11C60`, which also calls the vl param load). Of 120 reads of it, 112 are null-checked. The
unchecked ones are `0x02E284BC` (vt `+0x11C`), `0x02E285E8` and `0x02E28890` (vt `+0x2F4`). Every kind
has a specializer (98 slots, 8-byte stride from vtable `+0xC`). Each one has 4-31 non-stub slots, so
**no fighter is free of per-kind native code**. The smallest are miienemyf (4 slots, 82 instructions),
purin (4), donkey (5), samus and ganon (6), and mario (8, 169 instructions).

### Per-kind arrays in RAM (the blocker for a kind `0x41`)

- **FighterParamManager** `[0x102FF448]`: allocated with a fixed size, `li r3, 0x25B0` at `0x02E4E684`,
  then `0x02EA5848`; initialised at `0x02EA5BC0`.
  - Per-kind arrays from `+0x111C` to about `+0x2574`:
    - word arrays at `+0x111C` (vl param), `+0x1220` (refcount), `+0x1324`, `+0x1428`, `+0x152C`,
      `+0x1630` (`fighter_param.bin` entry index), `+0x1734` (the vl param `+0x50`);
    - `0x24`-byte records at `+0x1838`;
    - 8-byte records at `+0x215C`.
  - Loops over `0x41` at `0x02EA5C9C`, `0x02EA5CBC` and `0x02EA6B8C` (unload all).
  - There are about 970 reads of the manager pointer. About 3000 `lwz` use displacements in
    `0x111C`-`0x1220` (a heuristic that also catches other structures). Fighter, weapon and AI code
    read their own kind's params with the kind built into the offset, e.g. Kirby's `+0x113C`.
- **AI**:
  - an object of `0x26D0` bytes (`0x02758574`) holds 8 per-player records of `0x488` bytes;
  - each record ends with two `[0x41]` word arrays at `+0x280` / `+0x384` (init `0x0274E8D0`, loops
    `0x0274EAA8` / `0x0274EAC8`, read in `0x0275233C`).
- **Specializers and descriptors** are per-kind static objects, one per kind. There is nothing to grow,
  but a new kind needs one (or another kind's).
- **ACMD script manager** `[0x102FF68C]`: 16 slots of `0x40` bytes **keyed** by kind (`0x02E424D8`,
  `0x02E42518`). Not kind-indexed, so it has no limit at `0x40`.

### Per-kind tables in `.rodata` / `.data`

| address | size | holds | reader |
|---|---|---|---|
| `0x102FF484` / `0x102FF588` | 65 x ptr | names (followed by `0x102FF68C`, the ACMD manager pointer) | `0x0275DB24` / `0x0275DB38` |
| `0x10353DB4` | 65 x ptr | `fighter_param_vl_<name>` (followed by effect names) | `0x02EA6BC4` |
| `0x1012F638` | 65 x u16 | per-kind size (meaning not checked; read next to the special sizes, `0x02F1C1BC`) | `0x02EA90E0` (`> 0x40` → 0) |
| `0x1012F6BC` / `F700` / `F744` / `F788` | 65 x u8 (+3 spare) | special N / S / Hi / Lw param block sizes (stride of a custom variant) | `0x02EA9104` / `9120` / `913C` / `9158`; used by the WorkModule special loader `0x02F1BF88` and Kirby's copy loader `0x02F1B8B0` |
| `0x100D21D8` | 65 x u32 | 0-3 (3 for koopag / littlemacg); a class used by sound code (meaning not checked) | `0x02AB8CB0` |
| descriptors | 1 a kind | see above (e.g. mario `0x103A7BDC`) | `0x02E4313C` |
| `0x10418FF0`, `0x10419604`, `0x10419C18` | 389 x ptr | weapon owner / name / folder | `0x030BC8E4`, `0x030BCB10` |

### Kind count / bound checks

- `0x41`:
  - random fighter pick `0x021ED1A0` (rand `0x41`, wraps at `0x41` `0x021ED1B0` / `0x021ED1E0`);
  - kind → character id `0x0309FE50` (accepts `<= 0x41`);
  - sound bank loader `0x02A79158` (character id → kind `0x0309FDC8`, then `kind < 0x41`);
  - not classified (they look like kind checks or loops): `0x02761528`, `0x02AC3F7C`, `0x02FCD770`,
    `0x029B7F14`, `0x02DE1DDC`; loops `0x0275233C` (12 x `li 0x41`, the AI arrays), `0x03B2EED4` /
    `EF4`, `0x03B36454` / `0x03B36B5C`.
- `0x3A`: Kirby's `copy_grant` `0x02EFCDC8` (kinds `>= 0x3A` are never copied).
- Kind predicates:
  - `0x02E694AC` isMii(kind, with_enemies): 0-2, plus `0x3E`-`0x40` when asked; 26 callers;
  - `0x02E694E8` isMiiEnemy; 8 callers;
  - `0x02E69510` has-transformation;
  - `0x02E69560` (`0x33`-`0x3C`);
  - `0x03058B6C`, `0x03058B8C` (`0x3A`-`0x3D` → 0);
  - `0x030BF9C0` / `0x030C1FDC` transform → base;
  - `0x02704F44` armor check (`0x3A`, `0x3C`, `0x3D`).
- Inline Mii-enemy range checks (`0x3E`-`0x40`): `0x02542FD4`, `0x0265FC74` (damage panel),
  `0x026F4ACC`, `0x026F4B50` (AI), `0x0270EDCC`, `0x027294C8`, `0x02A65928` (sound), `0x02DE6A98`,
  `0x02DEA014`, `0x02FE3FC4`.
- Equality checks against single kinds (`cmpwi kind, 0x3E` and so on) are mixed in with status-kind
  compares, so they need a per-site review.
- Mii-enemy resources: `0x030C2F14` keeps dedicated holders for `0x3E` / `0x3F` / `0x40` (`+0x20` /
  `+0x24` / `+0x28` of `[0x102F9028]`). A mode set-up (probably Fighting Mii Team) preloads the
  three at `0x02825CA8`.

### Files (by name, so a renamed kind gets its own folder)

Path builder `0x030BB464` (type 0-14) uses the lowercase / Cap names:
- model: `fighter/%s/model/body/c%02d/`, `l%02d/`;
- motion: `fighter/%s/motion/%s/`;
- `fighter/%s/script/animcmd/body/`, `script/msc/%s.mscsb`, `script/ai/`;
- effects: `effect/%s/`, `effect/Fin%s/`;
- `camera/final/`;
- sound: `snd_se_%s[_c%02d][_common].nus3bank`, `snd_vc_%s[_c%02d][_ouen].nus3bank`,
  `soundseq_%s.sqb`, `voiceanim_%s.vat`, `snd_se_vc_Kirby_copy_%s.nus3bank`.

Weapons: `fighter/%s/script/animcmd/weapon/%s/` with the weapon's owner name. Params:
`param/fighter/fighter_param_vl_<name>.bin`.

## Data files keyed by kind (one entry per kind already)

- `fighter/fighter_param.bin`: 65 entries x 354 values. The first value is the kind; the manager
  searches by it (`+0x1630`). Attribute names are in `reference/fighter_param_attributes.csv`.
- `ai/fighter_ai_fighter_param.bin`: 65 entries, first value is the kind.
- `simple/simple_character_db_cafe.bin`: Classic mode, keyed by kind.
- `fighter_param_vl_<name>.bin`: one file a kind. Kirby's includes a per-kind copy table (`0x88` a
  kind, `[[mgr+0x113C]+0xFC]`).

Because a reused slot already has an entry in each of these, nothing needs resizing.

## The UI side

### `ui_character_db.bin`

- File: `param/ui/ui_character_db.bin`, string at `0x101562C4`.
- Loader `0x030A0DD0` builds a `0x44`-byte database at `[0x102F7188]`.
- Entries are `0x4C` bytes in RAM; the vanilla file has 82.
- **Character ids `<= 0xC7` are looked up by position** (entry index = id). Ids `>= 0xC8` are searched
  for. Each accessor (`0x030A04C0`, `0x030A05D8`, ...) repeats the same pattern, and a bad id falls back
  to index 4 (Mario).

| RAM | value # | meaning |
|---|---|---|
| `+0x00` | 0 | character (UI) id: 0 random, 1-3 Miis, 4-58 fighters, 200+ special |
| `+0x04` | 1 | 1 for fighters / 200 |
| `+0x05` | 2 | shown (availability `0x0293F038`, `0x030A0660`; `0x0309FB24` with flag) |
| `+0x08` | 4 | series |
| `+0x0C` | 5 | is a fighter (kind → id search `0x0309FE50` skips 0) |
| `+0x10` | 6 | **fighter kind** (`0x0309FDC8`) |
| `+0x14` | 7 | costume count (Little Mac 16) |
| `+0x1C` | 9 | Mii (skipped by the CSS list builder) |
| `+0x1D` | 10 | DLC (`0x030A05D8`): second CSS list, unlock index `id - 0x34 + 8`, DLC content check |
| `+0x20`-`+0x22` | 13-15 | sort keys |
| `+0x2C`-`+0x33` | 21-28 | per-costume name index (`MmelCharaN_%02d_...`; Koopalings 1-8) |
| `+0x3C`-`+0x43` | 37-44 | per-costume (voice) index |

- Character id → kind: `+0x10` via `0x0309FDC8`.
- Kind → character id: `0x0309FE50`, the first entry with `+0x0C` set and the kind, so a new entry at
  index 59 is found before entry 219 (Miienemyf, kind 62).

### Names, portraits and text

- **Character id → UI name**: `{u32 id, char *name}` table at `0x1033BE68`, 83 entries including the
  `-1` sentinel. Read by `0x0293DCCC` (`lis r3` / `li r4, 0x53` / `addi r3` / `b 0x0293E92C`, a linear
  search). This mirrors the stage cosmetic-name table (`0x1033C100` / `0x0293DCE0`). The database
  copies the names into its `+0x38` list when it loads (`0x0293DEEC`, through vtable `0x1015628C`).
- **Portraits** come from `0x0291673C` and the root picker `0x029165D8` (the DLC root `append/` first,
  as for stages), with the UI name:
  - `chr_%02d/chr_%02d_<Name>_%02d`; sets 0, 10, 11, 13, 40, 90;
  - `chrn_%02d/chrn_%02d_<Name>_%02d` (`0x029169A8`); sets 11, 12, 40, 41;
  - `stock_%02d/stock_%02d_<Name>_%02d` (`0x02916B44`); set 90.
- **Text** in `ui/message/melee.msbt`, built by `0x030A00EC`-`0x030A033C`:
  - `MmelCharaN_%02d_<Name>` (name);
  - `MmelCharaC_%02d_<Name>` (capitals);
  - `MmelCharaA_%02d_<Name>` (title);
  - `MmelCharaR_%02d_<Name>`;
  - `MmelCharaN_%02d_<Name>_snd`.
- **Other databases keyed by character id**:
  - `ui_sound_call_voice_db.bin` (58 entries: announcer call, narration ids `0x0038xxxx`);
  - `ui_sound_voice_chara_db.bin` (128);
  - `ui_skill_db.bin` (59).

  How strictly the game needs entries in these is not checked.

### The character select

- **List builder `0x028BF6AC`**:
  1. Goes through every database entry.
  2. Skips Mii entries (`+0x1C`) and entries that fail the availability check `0x0301BA44(id, 4)` →
     `0x0293FD40`.
     - The character wrapper is a static at `0x1054F400`, vtable `0x100BAA84`.
     - `+0x1C` "exists": id not -1 / `0xFF`, `+0x05` set, and the mask `0x0293C378([0x1034069C], id)`.
       The mask passes when none is loaded; we don't know what loads it.
     - `+0x24`: DLC.
     - `+0x4C`: has a name.
     - `+0x6C`: unlocked.
     - `+0x74`: DLC content `0x026F2EC8`.
  3. Puts DLC entries in a second list, sorts both (`0x028BE798`), and adds random (id 0).
- **Unlock index `0x030A0A3C`**: a DLC id takes `id - 0x34 + 8`; any other id takes its position in
  `unlock_condition_of_fighters.bin` (8 fighters), or -1 (always available) if it isn't listed.
  **A new non-DLC id 59 isn't listed, so it is unlocked.**
- **Layout `0x028BEE20`**: `lumen/chara/chara.lm`, arrangement `num_%03d` by count (`0x100AEA68`),
  slots `face_%03d` bound to the ids in order (`0x028BE920`). The vanilla layout has `num_013`-`num_096`
  and `face_001`-`face_096`, so **one more fighter only changes the arrangement number**. That's like
  the stage select, but check the user's modded `chara.lm`: their stage layout had renamed arrangements.
- Random-select bitset `0x02FFB610`: loops over the first `0x51` (81) database entries (`li r23, 0x51`
  at `0x02FFB644`) into a 96-bit set. Raise it to `0x52` when an entry is inserted.

## Feasibility

### Option A: a real kind `0x41` (like the stage kinds `0x80`+): not practical

What it would take:
1. Move or grow every `[0x41]` array in RAM objects:
   - the FighterParamManager (`0x25B0` bytes; more than 7 arrays, with hard-coded offsets in roughly a
     thousand instructions);
   - the AI records (`0x488` stride, arrays at their end).
2. Add cases to the six `0x40` switches. The descriptor default aborts. The vl param parser for a new
   kind would need a new storage field in `[mgr+0x2574]`, whose layout is fixed.
3. Move the name tables (each is followed by other data, e.g. `0x102FF68C`).
4. Raise the `0x41` bounds listed above.
5. Make a specializer and descriptor for the new kind.

Items 3-5 are cave work like the stages (moved tables, relocations moved with `reloc:`). Items 1-2 are
not: every instruction using those offsets would have to change. **Confidence: high that it's
impractical.** The arrays and the fixed allocation sizes were read directly.

### Option B: reuse a kind as it is

Candidates:
- **Mii enemies `0x3E`-`0x40`.** As far as found, only Fighting Mii Team uses them (the modes behind
  `0x02825CA8` / `0x02FE3F18` weren't identified by name). They are Mii-based: Mii checks, Mii vl
  param layouts, Mii AI, and probably the Mii head article (`miipartshead`). Small specializers.
- **Transformations `0x3A`-`0x3D`.** Real fighters with full folders. But their bases' Final Smashes
  use them, there are armor / grab / detransform / Kirby-copy special cases, and the user plays with
  them (`docs/native-notes.md`). Not recommended.

A new fighter that kept the slot's own native code would behave like a Mii Brawler / Swordfighter /
Gunner. That's only useful if the new fighter is designed on a Mii moveset.

### Option C (recommended): reused slot + base-fighter redirection ("clone kind")

Kind SLOT (say `0x3E`) becomes a clone of base X (any fighter whose native behaviour fits; a fighter
with little special native code is safest, e.g. mario, captain, samus, ganon).

| piece | change | how |
|---|---|---|
| names | `miienemyf` / `MiiEnemyF` / `fighter_param_vl_miienemyf` → `<name>` (≤ 11 / 11 / 10 chars) | in place: each string has one reference, so the relocated table pointers stay valid |
| specializer, descriptor, AI x2 | the slot's jump-table entry → X's case | 4 words (`--plan` prints them) |
| special block sizes, sound class | slot entries = X's | 6 words |
| vl param load / unload | X's parser / free functions, but SLOT's fields (`[mgr+0x2574]+0x320+4*SLOT`, `mgr+0x111C+4*SLOT`) | a cave per case (X's case copied, two offsets changed). It must also load / unload kind X: X's specializer, weapons and AI read X's own slot by fixed offset |
| Mii-ness | `0x02E694AC` / `0x02E694E8` exclude SLOT; review the inline sites listed above | patches |
| Kirby | optional: `copy_grant` bound `0x02EFCDC8`, hats, Kirby MSC | later |

What the clone gets:
- **Its own:** files (model, motions, ACMD, MSC, sounds, effects, AI scripts), `fighter_param.bin`
  attributes (entry SLOT), and special param blocks read through WorkModule (`0x02F1BF88` copies them
  from `mgr+0x111C+4*kind`, i.e. its own vl file).
- **Shared with X:** native special-move code and its params (read from X's vl slot), articles
  (weapon kinds and their files are X's), motion / status layout (X's descriptor), and X-specific
  inline `kind == X` checks, which won't fire for the clone.
- **Fixed by X's descriptor:** the animation each motion plays. Descriptor `+4` is the motion table:
  one CRC32 hash of the `.omo` file name per motion (`docs/params/fighter_files.md` 4.2). The clone's
  animations must keep X's file names (`FitMarthBody...`), or the slot needs its own copy of the table
  with patched hashes.
- **Sound ids follow the bank's BINF id** (`soundlabeltable.bin` row, `docs/params/fighter_files.md`
  section 6). A clone bank that keeps X's BINF id plays with X's ids, and probably can't be loaded next
  to X in the same match. A separate set of sounds needs its own row and BINF id, and ACMD using the
  new ids.

`docs/params/fighter_files.md` (the per-fighter files research) covers the folder, motion, sound,
vl param shapes and AI files in detail; its section 9 checklist applies to the clone's folder.

**Confidence:**
- that the redirections cover the dispatch points: medium-high;
- that nothing else breaks: medium. Unknowns are below.

## Plan (Option C)

1. **Pick the slot and the base.** SLOT `0x3E` (or `0x40`, which leaves only Fighting Mii Team's Gunner
   variant affected), and base X. `python3 tools/fighter_kind_tables.py --plan 0x3E:X:<name>:<Name>` prints
   the word patches for names, switches and size tables, and what's left to do.
2. **RPX cave script** (`tools/fighter_slot_cave.py`, to write, in the style of `stage_slot_cave.py`):
   1. the `--plan` words;
   2. vl load / unload cases for SLOT: copy X's case, re-encode its branches, change the two field
      offsets, and call the loader / unloader for X as well;
   3. `0x02E694AC` / `0x02E694E8` without SLOT;
   4. the character name table `0x1033BE68` copied into a cave with `{59, "<Name>"}` added, and
      `0x0293DCCC` pointed at it with count `0x54`. Move the `lis` / `addi` relocations to the dead word
      (`reloc:`), as the stage name table needed;
   5. `0x02FFB644` `li r23, 0x52`.

   A unicorn test like `stage_slot_test.py`: names, getters, character name lookup.
3. **Data** (`tools/add_fighter.py`, to write, like `add_stage.py`):
   1. `ui_character_db.bin`: entry at index 59 (copied from X's), id 59, kind SLOT, `+0x05` = 1,
      `+0x0C` = 1, DLC 0, sort keys, per-costume name indices 1;
   2. `fighter_param.bin` entry SLOT = X's values (then the new stats); `fighter_ai_fighter_param.bin`
      entry SLOT = X's; `simple_character_db_cafe.bin` SLOT = X's;
   3. `fighter_param_vl_<name>.bin` = copy of X's;
   4. `ui_sound_call_voice_db.bin` (id 59), `ui_skill_db.bin` (id 59), `ui_sound_voice_chara_db.bin`:
      copy X's;
   5. `melee.msbt` `MmelCharaN` / `C` / `A` / `R` `_01_<Name>`;
   6. portraits `chr_00` / `10` / `11` / `13` / `40` / `90`, `chrn_11` / `12` / `40` / `41`, `stock_90`
      (copies of X's, renamed, with unique texture ids as for stages);
   7. `fighter/<name>/`: X's folder, files renamed (`snd_se_<name>`, `<name>.mscsb`, ...).
4. **First test:** an exact copy of X under the new name. It should be selectable, load, fight, and work
   in a match against X. Then swap in the new model, motions, ACMD, MSC and params.
5. **Later:** a Kirby copy (`copy_grant` bound, hat, Kirby MSC; per CLAUDE.md the fighter's trait goes
   in `kirby_copy_trait()`), its own articles (new weapon kinds: not planned), its own AI routines
   (redirect more AI switches).

The minimum for "selectable and playable with its own model / animations / scripts / params" is
steps 1-3: the switch redirects, the vl caves, the name table cave, and the database / portrait / text
/ folder files.

## Risks and unknowns

- **Save data / records by character id.** VS records, Classic / All-Star clears and similar data may
  be fixed-size per id `0`-`58`, and id 59 could write past them. Not checked. Find with a debug
  recorder, as the stage work did.
- **Sound ids:**
  - ACMD sound ids are X's. Two banks with the same BINF id (X and the clone in one match) are
    untested.
  - The announcer needs a narration id; use X's or none.
- **Inline `kind == X` checks** in X's native code don't fire for the clone. The effect depends on X,
  so audit X's sites.
- **Mii-enemy sites:** the 10 inline sites and the equality compares need review. If SLOT is `0x3E`,
  the set-up at `0x02825CA8` (probably Fighting Mii Team) loads the new fighter as its Brawler.
  Patch it, or pick `0x40`.
- **`ui_character_mask` / `show_character_mask`:** no loader string was found. If the mask
  `[0x1034069C]` is loaded, ids missing from it are hidden.
- **Online, replays, amiibo / FP** (the AI arrays per kind) with an id or kind they don't expect:
  untested.
- **Descriptor `+0`** holds X's kind. No caller seen reads it, but this wasn't exhaustive.

## Tools

`tools/fighter_kind_tables.py [RPX]` reads the RPX (default `build/cave_fix_s4/cross_f.rpx`).

| option | prints |
|---|---|
| (none) | the per-kind table: names, specializer singleton, descriptor, vl param case / field / slot, AI cases, size tables, sound class; and the character id → name table |
| `--kind K` | one kind in detail |
| `--ui PARAMDIR` | the `ui_character_db.bin` entries |
| `--vtables` | each specializer's vtable |
| `--scan` | every jump table bounded by `0x39`-`0x41` |
| `--plan SLOT:BASE[:name[:Cap]]` | the word patches for Option C's names / switches / size tables, and the caves still to write. **Untested in game.** |
