# Shared fighter attribute tables (fighter_param*.bin)

Static analysis of `cross_f.rpx` (Smash 4 Wii U, 1.1.x) and the param dump. Covers the five shared
files in `data/param/fighter/`:

| file | what | per-attribute table |
|---|---|---|
| `fighter_param.bin` | one 354-word entry per fighter kind (movement, sizes, landing lag, flags, nodes ...) | `reference/params/fighter_param.csv` |
| `fighter_param_common.bin` | 849 words shared by every fighter (input windows, status constants, item/size factors ...) | `reference/params/fighter_param_common.csv` |
| `fighter_param_etc.bin` | 33 nested groups (item throws, staling, colours, Mii body scaling, equipment caps ...) | `reference/params/fighter_param_etc.csv` |
| `fighter_param_power_up.bin` | Smash Run / Smash Tour power-up categories: which fighter_param stats each one scales | `reference/params/fighter_param_power_up.csv` |
| `fighter_param_equipment_ability.bin` | equipment: 186 per-level values + 93 abilities listing the fighter_param stats they scale | `reference/params/fighter_param_equipment_ability.csv` |

Tool: `tools/fighter_param.py` (dump / get / set by name, add a fighter entry, byte-exact round trip
for all five files; see its docstring).

**Which copy is vanilla.** In the dump `param - Copy/`, the top-level `fighter_param.bin` and
`fighter_param_common.bin` (dated 2025-03-06, identical to the community sheet values) are vanilla.
The `fighter/` subfolder copies of those two files are the user's latest experiment (same bytes as
`new/post-luigi/newtestwariochomp/new/2/`): 15 fighters changed in fighter_param (Mii Gunner,
Samus, Pikachu, Luigi, Captain Falcon, G&W, Wario, Charizard, Sonic, Wii Fit Trainer, Little Mac,
Duck Hunt, Mewtwo, Ryu, Bayonetta) and 9 common words (0xB, 0xBF, 0xC0, 0xF8, 0x1A7-0x1AB; listed in the common CSV column
`user_mod_value`). `etc`, `power_up` and `equipment_ability` are identical in both places. All
statistics in the CSVs use the vanilla copies.

## 1. File format and the game's loader

Generic param format: `FF FF 00 00` + 4 bytes, then values, each a type byte + big-endian data
(1 u8, 2 s8, 3 u16, 4 s16, 5 u32, 6 s32, 7 float, 8 string, `0x20` group + u32 entry count).
The file itself does not say where an entry ends; the game binds each file to a fixed C++ layout:

- Param manager singleton `[0x102FF448]` (0x25B0 bytes, ctor `0x02EA5848`), created and loaded by
  `0x02E4E654` → load `0x02EA5BC0`, which opens each file and runs the generic binder
  `0x033B4770(binder, file)`:

| file | object in manager | ctor | bind function |
|---|---|---|---|
| fighter_param | mgr+0x0 (vector: count +8, data +0xC) | `0x02E8F81C` | element `0x02EA9198` → schema `0x1012D724` |
| common | mgr+0x38 (849 words = 0xD44 bytes, inline) | `0x02E8F910` | schema `0x1012D754` |
| etc | mgr+0xDA0 | `0x02E8F9D4` | `0x02E89E88` |
| power_up | mgr+0x1058 | `0x02E8FF78` | `0x02E8A048` |
| equipment_ability | separate singleton `[0x10353FC0]`, pointer at mgr+0x2574 | `0x02E901E4` | `0x02E8A0A8` |

- Binder primitives: `0x033B5448` = a group (vector; element callback op 0 constructs, op 2 binds),
  `0x033B5500` = inline fields described by a nibble string (low nibble first; bits 0-1 size class
  u8/u16/u32/skip, bits 2-3 count-1; skip x4 = end), `0x033B5418` / `0x033B5424` = one u32 / float.
  `0x033B4D58` checks each value's type byte against the expected size class (table `0x1019C258`);
  **a value of the wrong size class is not consumed and the field is left unset**, so types must
  stay 4-byte (5/6/7) where the layout expects words (u32 and float are interchangeable to the
  binder; the reading code decides the interpretation).
- The decoded layouts are in `LAYOUTS` in `tools/fighter_param.py`; they reproduce the group
  structure of all five vanilla files exactly (the old `s4param.py` split cannot handle etc /
  equipment_ability, which contain groups of groups and loose values after a group).

## 2. fighter_param.bin: kinds and IDs

- One group of 65 entries x 354 words (0x588 bytes). **Word 0 is the fighter kind.** After loading,
  `0x02EA5C9C` loops kinds 0..64 and stores, for each kind, the index of the entry whose word 0
  equals it (`mgr+0x1630 + kind*4`; also clears `+0x1324/+0x1428/+0x152C`). Entry order is
  therefore irrelevant; duplicate kinds resolve to the first entry; kinds above 64 are ignored (the
  per-kind arrays have 0x41 slots), so a genuinely new kind needs an executable change. The tool's
  `add` command appends a copy of a base fighter with a new kind number anyway (useful together
  with an extended executable, or to replace an unused kind).
- Kind numbers: 0 miifighter, 1 miiswordsman, 2 miigunner, 3 mario ... 57 kamui, 58 koopag,
  59 warioman, 60 littlemacg, 61 lucariom, 62-64 miienemyf/s/g (list in the tool).
- Per-fighter copy: the fighter WorkModule (vtable `0x1013AFFC`, 0x15F4 bytes) copies the entry to
  `WM+0x20` when the fighter is set up (`0x02F1BF88`; Mii Fighters take a body-shape-scaled copy built
  by `0x02F1BCF0` from fighter_param_etc g20). Then `0x02F1BEE0` overwrites the derived words
  0x158-0x161 (below). Because every fighter reads its own copy, run-time systems (size items,
  power-ups, equipment, Mii body) modify that copy, not the shared table.
- WorkModule category table (built in `0x02E53E98` at fighter+0xCC+0xFA8, 10 categories):
  `0` instance work, `1` status work, **`2` fighter_param_common** (container mgr+0x2578: floats = ints =
  mgr+0x38), **`3` fighter_param** (container WM+0x1540: floats = ints = WM+0x20, 0x162 entries),
  `4` fighter_param_vl block (WM+0xB30), `5-8` special N/S/Hi/Lw blocks (WM+0xD30/0xF30/0x1130/0x1330),
  **`9` fighter_param_equipment_ability** inline words (container mgr+0x2594 → `[mgr+0x2574]`).
- So an ID is `(int ? 0x10 : 0) << 24 | category << 24 | word`: `0x03000021` = fighter_param word
  0x21 as float, `0x13000022` = word 0x22 as int, `0x02000010` / `0x12000008` = common words,
  `0x19000000` = equipment word 0. The float and int arrays of a container are the same memory: the
  `0x10` bit only says which getter is meant (`get_float` vtable +0x44 `0x0200F628` / fighter copy
  `0x02F1DBE4`, `get_int` +0x84 `0x0200F7F0`).

### Derived words (0x02F1BEE0)

`v(h, g) = sqrt(2h/g)*g + g/2` (`0x02C5483C`) turns a height into an initial speed:

| word | value |
|---|---|
| 0x158 jump_speed_y | v(0x11 jump_height, 0x18 gravity) |
| 0x159 mini_jump_speed_y | v(0x12, g) |
| 0x15A jump_aerial_speed_y | v(0x13, g) |
| 0x15B cliff_jump_speed_y | v(0x44 ledge jump height, g) |
| 0x15E shield_break_speed_y | v(0x2E shield-break height, g) |
| 0x15F step_jump_speed_y | 0x158 * 0x36 |
| 0x160 step_mini_jump_speed_y | 0x15F * 0x37 |
| 0x161 | 0x158 * 0xBA |

The file stores 0 in these words; whatever is there is overwritten. 0x15C / 0x15D are real
multipliers (1.0) that power-ups and equipment change.

### Run-time modifiers that list fighter_param IDs

- Size items: pair table `0x1013A3E8` maps stats to common words 0x28F-0x2AD (Super/Poison Mushroom)
  and 0x2AF-0x2CD (Lightning); stat x (1 + (size - 1) x factor). (The community common sheet labels
  0x291 as "dash"; the table maps 0x291 to the walk stats, 0x292 to dash, 0x293 to run ...)
- Stat lists of 24-byte records `{ID, mul, ...}` used by the fighter WorkModule (`0x02F1C354` and
  callers 0x02F1C6xx-0x02F1D5xx): `0x1013A608`, `0x1013A848`, `0x1013A9C8`, `0x1013ABA8` (the
  equipment stat order, = etc g28 caps), plus `0x10143EF8..` (used by `0x02F7B3A4`).
- `fighter_param_power_up`: each category group starts with a header record naming a category stat
  (0xD0 Speed, 0xD1 Jump, 0xD2, 0xD3 Attack, 0xD8 Arms, 0xD9 Defense) followed by `{fighter_param
  ID, mul_a, mul_b, 0, rate, 0}` records.
- `fighter_param_equipment_ability` g1: 93 abilities, each a list of `{fighter_param ID, lv1, lv2,
  lv3}` + the ability number.
- fighter_param_etc g20: Mii body table, `{fighter_param ID, ..., fattest, ..., skinniest, ...,
  tallest, ..., shortest, ...}`.

These lists were used as extra evidence (column `evidence`, "modified by").

## 3. Method

1. Loader / layouts: disassembly of the manager ctor and load function, then a symbolic decoder of
   the binder calls (`scratchpad/fp/binder.py`, `schema.py`), verified against all five files.
2. Readers: a linear constant/tag propagation pass over the whole `.text`
   (`scratchpad/fp/flow.py`, ~15 s) recording
   - param IDs (`lis 0x300/0x1300 + addi/ori`, chained `addi rX, rBase, n`) reaching a call
     (`bctrl` through vtable +0x44 / +0x84, or `bl` to the inline getters `0x02E3CD54` (float) /
     `0x02E3CDC8` (int)): ~110 fighter_param IDs, 264 common IDs;
   - direct entry reads: `[mgr+0xC] + [mgr+0x1630+kind*4]*0x588` then `lfs/lwz/addi` (camera
     `0x02E4F7E8`, inhale star `0x02ECA7E0`, fighter setup `0x02E53E98`, AI jump `0x02F7B3A4` ...);
     pointers into the entry passed to other modules (blocks 0x7A, 0x7F, 0x84, 0x97, 0x13C);
   - reads of manager offsets (common / etc / power_up members).
3. ID tables in rodata/data (24-byte stat lists, attack-kind table `0x101830B8`, pair table).
4. MSC: decompiled common scripts of 13 fighters (Kirby, Marth, Mario, Captain Falcon, Luigi, Sonic,
   Meta Knight, Ryu, Greninja, Charizard, Corrin, Giga Mac, Mega Lucario; the common part is the same
   in all), `WorkModuleF(0, 0x03xxxxxx)` / `WorkModule(6, 0x13xxxxxx)`, including computed IDs
   (landing lag `0x300001C + aerial kind`). Function numbers map to the MSC Note Sheet's common
   scripts (`reference/msc-note-sheet/Cmn_Scripts_Fighters.csv`).
5. Each reader was read in the annotated disassembly (`scratchpad/fp/ann.py`) to fix the meaning,
   unit and confidence. Community labels (Sammi Husky / Meshima sheets, all five tabs downloaded to
   `scratchpad/fp/sheets/`) were checked against the code; corrections are listed below.

Scripts and intermediate data: `scratchpad/fp/` (flow.pkl, cover*.pkl, msc_lines.txt,
labels_fp.py = the hand labels, gen_*.py = CSV generators).

## 4. fighter_param attributes: summary

354 words (index 0 = kind). Confidence in `fighter_param.csv`: **171 high, 102 medium, 81 low**.
Column `new_fighter`: 229 words differ between fighters ("set per fighter"), 116 are the same for
everyone ("keep default"), 8 are derived (leave 0), word 0 = kind.

| range | content |
|---|---|
| 0x01-0x1B | walk / dash / run / jump-squat / jump speeds and heights / air drift / gravity / fall speeds (kinetic energies `0x02E83AA8` stop, `0x02E8044C` air control, `0x02E818A8` gravity, jump init `0x02E79938`) |
| 0x1C-0x20 | aerial landing lag N/F/B/Hi/Lw |
| 0x21-0x2A | weight, jump count, vertical/horizontal speed limits, landing lag, hard-landing fall frames, air-dodge autocancel |
| 0x2C-0x33 | scale, shield size, shield-break height, effect scale, AreaModule extensions |
| 0x36-0x47 | footstool, heavy-item / shooting-item walking, item throw, ledge and wall jumps |
| 0x49-0x5D | damage, KO voice, run brake, turn, jab/tilt/smash combo windows, rapid jab inputs, jab/dtilt pushback, smash charge frames |
| 0x5E-0x89 | setup values, respawn platform, knockback trail effect nodes, wall-jump stick, weight-dependent throws, camera boxes / nodes |
| 0x8A-0xA8 | SearchModule shapes (item pickup boxes), swimming, hand nodes |
| 0xAA-0xCF | sound weight class, bury, freeze (ice block), inhaled star, egg lay, event body hitbox, Speed Crasher effect |
| 0xD0-0x105 | power-up categories, attack-kind damage multipliers, item / heal / shield / dodge / ledge / respawn / status multipliers (1.0 in the file), Speed Crasher hitbox |
| 0x106-0x126 | move-set flags: jab type and count, rapid jab, # of f-tilts/f-smashes, jump type, glide, walk/run animation frame thresholds, heavy walk frames, crawl, wall jump/cling, tether, thrown / grabbed types, model mirroring |
| 0x127-0x13B | upper-body nodes, KO / screen-KO placement, item body sizes, hip/head nodes |
| 0x13C-0x147 | 4 x 3 floats paired with etc g14 |
| 0x148-0x157 | Find Mii colours (unreferenced on Wii U) |
| 0x158-0x161 | derived jump speeds (+ two multipliers) |

### Corrections to the community labels (Sammi Husky's fighter_param sheet)

- Word 0 is the fighter kind (the sheet starts at 1).
- 0x158-0x161 are not "height multipliers": they are initial speeds computed at load from the
  heights and gravity (file value 0, overwritten); only 0x15C/0x15D are multipliers.
- 0x1A "V acceleration" → vertical brake of the gravity energy (deceleration when faster than the
  max fall speed); 0x23 "max ground speed? (super speed jumpsquat)" → hard limit of the vertical
  speed (gravity energy limit, 10); 0x4E "speed related" → ground speed limit of the momentum
  energy (3.0); 0x24 confirmed as the air counterpart (2.5).
- 0x32/0x33 "GFX size type 2"/blank → the fighter AreaModule box extension front/back.
- 0x6A-0x6F "GFX type 1/2 bone + offsets" → knockback smoke/streak effect node and offsets for
  DamageFly and DamageFlyRoll (and the Deadly Blow effect).
- 0x75 "unknown" → camera target centre height; 0x7A "same as 117" → zoom-camera centre height.
- 0xAA "metal box stepping SFX pitch" → sound weight class (0 light, 1 middle, 2 heavy) used for
  splash / step sounds; 0xAC is read next to it but its value is ignored by the code.
- 0xB6-0xB8 (blank) → frozen ice-block node and Y/Z offsets (0xB9 = its size, as labelled).
- 0xC6-0xCA (blank) → node / offset / size of a body hitbox created from attack data sent in a
  fighter event (`0x02E578BC`).
- 0xCB "instance KO GFX bone" → also the Speed Crasher effect node; 0xCD-0xCF its offsets.
- 0x12E-0x132 "KO related / star KO" → screen KO (KO into the camera): length correction, rotation
  angle range, depth, Y offset.
- 0xD0-0xD9 (blank / "item related") → Smash Run/Tour power-up category stats.
- 0xE7/0xE8 "attack ratio" → meteor and upward-launch damage multipliers (Meteor Master / Moon
  Launcher).
- 0x30 = 0x2D x 0.35 for every fighter: a hitbox size (MSC func_2229), not a hurtbox.

### Still unknown / unreferenced

No reader was found (executable or common MSC) for 57 words. 47 of them are not listed anywhere
else either: 0x2B, 0x34, 0x35, 0x48, 0x4A, 0x4B, 0x67, 0x69, 0x9D, 0xA2, 0xA3, 0xA9, 0xAD-0xB4,
0xCC, 0xD4-0xD7, 0x122, 0x124, 0x125, 0x133, 0x138, 0x139, 0x148-0x157 (Find Mii colours). The
other 10 (0x26, 0x60, 0x63-0x66, 0x71, 0x72, 0x134, 0x135) are listed in the Mii body table (etc
g20), so the game treats them as size-dependent, but nothing reading them was found. Several
multipliers (0xEA, 0xEE, 0xF0, 0xF3, 0xFA, 0xFB, 0xFF ...) appear only in power-up / equipment lists:
their consumers must build the ID at run time. Such words may also be read by fighter-specific
MSC that was not decompiled, or be dead. Low-confidence readers: 0x2F, 0x45, 0x5F, 0x70, 0xA1,
0xAB, 0x127, 0x12B-0x12D, 0x136-0x13B.

## 5. Building a new fighter

Copy a similar fighter's entry (`fighter_param.py add`), give it a free kind number, then:

1. **Must set** (they differ between fighters): everything marked `set per fighter` in the CSV:
   movement (0x01-0x1B), landing lags, weight, jump count, scale, shield size/break height, effect
   scale, camera boxes, item pickup boxes, freeze / effect / camera node values, move-set flags
   (0x106-0x126), animation frame thresholds (0x10E-0x11A, taken from your walk/run/heavy-walk
   animations), KO placement values, Find Mii colours (harmless).
2. **Node values** (0x6A, 0x6D, 0x7F, 0x84, 0xA4, 0xA5, 0xB6, 0xC6, 0xCB, 0x128-0x12A, 0x138,
   0x139) index the model's skeleton (VBN); values >= 1000 (e.g. 1050, 1066, 1067) appear for some
   fighters and look like a second node numbering; copy them from a fighter with the same skeleton
   layout or check them against the model.
3. **Keep default**: the 116 words that are identical for every fighter (e.g. 0x23 = 10, 0x24 = 2.5,
   0x4E = 3, swim values, all 1.0 multipliers 0xD0-0x102).
4. **Leave 0**: the derived words 0x158-0x15B, 0x15E-0x161.
5. Size-related values usually scale together: tumble/body hitbox 0x30 = 0x2D x 0.35, 0x63 ≈ 0x31,
   0x7A = 0x75, camera zoom box = camera box - offsets.

## 6. The other four files

- **fighter_param_common** (category 2, 849 words): community labels for 581 words, checked
  against 264 getter IDs, 297 MSC IDs and direct reads; the size-item factor block 0x28F-0x2CD is
  now mapped stat by stat. Confidence: 57 high, 439 medium (labelled and referenced), 353 low.
- **fighter_param_etc** (33 nodes, struct offsets in the CSV): item throw table (g00), jostle
  pushback (g02), audience reactions (g03), staling (g04), colours, player colours (g15), screen-KO
  thresholds (g18, read by `0x030AF760`), Mii body scaling (g20, `0x02F1BCF0`), equipment caps (g28,
  read 35x by `0x027B14F8`) and power curve (g29); many small groups are only located (reader
  address) but not explained.
- **fighter_param_power_up**: 8 groups of `{ID, mul_a, mul_b, 0, rate, 0}`; group headers name the
  category stat (0xD0, 0xD1, 0xD2, 0xD3, 0xD8, 0xD9); g6 is a 2-word table (1.0.4).
- **fighter_param_equipment_ability**: g0 = 62 triples (level 1/2/3 values, WorkModule category 9:
  `0x09xxxxxx` / `0x19xxxxxx`), g1 = 93 abilities with their stat lists (names from the community
  sheet, which follows the file order).
