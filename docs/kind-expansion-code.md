# More fighter kinds: code and tables

Status: **scoping research (static analysis of `cross_f.rpx`), nothing built or tested.** Goal: kinds
`0x41`, `0x42`, ... up to `N - 1` (e.g. `N = 0x60`), each a first-class kind with its own files, params and
UI entry, instead of the reused-slot clone of `docs/new-fighter-slot.md` (Option C). This page covers the
**code and static tables**: every switch, bound, loop and table indexed or sized by fighter kind (and by
UI character id). The per-kind arrays inside RAM objects (FighterParamManager `0x25B0` bytes, AI records)
are in `docs/kind-expansion-ram.md`; this page only lists the instructions that touch them.

Addresses: this repo's `cross_f.rpx` (`build/cave_fix_s4/cross_f.rpx`).

**Tool:** `python3 tools/kind_code_scan.py` prints the reviewed inventory below, checked against the RPX
(every compare / `li` / jump table / table is re-read; an `!!` means the RPX no longer matches), with the
new immediates for `--n N`. `--scan` reruns the scanners the inventory came from and marks every hit
`inv` (in the inventory), `ok` (reviewed: a kind compare that a new kind already passes), `no` (reviewed:
not a fighter kind) or `?`. `--params DIR` lists the data files keyed by kind / character id.
`--plan FILE` turns an "extra kinds" table (section 3.3) into the per-kind patch list.

## Summary

| category | sites | what a kind `>= 0x41` does today | change |
|---|---|---|---|
| 65-case kind switches | 6 | default: specializer 0, **descriptor aborts**, vl load / unload skip, AI generic | extend each jump table in a cave (6) |
| switches over part of the kinds | 23 (+17 HUD on character id) | default = "not special" | none |
| per-kind tables | 3 name tables, 6 value tables | read past the end (the sound-class getter has no bound) | cave copies with `N` entries, readers repointed (9 tables, 9 readers, 18 relocations) |
| kind-count bounds | 10 + 5 getter bounds | rejected (no AI files, no resources, no sound bank, no character id, never random) | 15 immediates |
| loops / arrays in RAM | 25 immediates | out of the `[0x41]` arrays | `docs/kind-expansion-ram.md` |
| predicates, range checks | 20 listed + 47 reviewed | answer "no" (not Mii, not a transformation, not DLC) | none |
| Kirby's copy | 11 | never copied (`copy_grant` refuses `>= 0x3A`) | optional: 6 tables + 5 bounds |
| UI character ids | name table, 2 counts | ids `<= 0xC7` are positional; room for ids 59-199 | 1 table, 2 immediates; data files |
| IDs that encode the kind | 4 | effect `0x3KK....` (8 bits), resource IDs `kind*0x11+n`, `kind*9+n` (map keys) | none found; to test |
| unsure | 4 | `0x02FCD770`, `0x02748648` / `0x0274868C`, AI map `0x0274EB90` | verify |

**Must change for one new kind (minimum):** 6 switches + 10 tables (3 names, 6 values, character names) +
17 immediates (10 bounds, 5 getter bounds, 2 UI counts) = **33 sites**, ~20 relocations to move, plus the
RAM work and the data files. All of it is cave work of the kind `docs/stage-expansion.md` already did.

## 1. Inventory

### 1.1 Kind switches

The six full switches (`cmplwi kind, 0x40; bgt default` + a table of 65 `b`):

| compare | function | table | default (kind `>= 0x41` today) | a new kind's case |
|---|---|---|---|---|
| `0x02E669F0` | specializer getter (r4) | `0x02E66A10` | `0x02E66C18`: returns 0. `fighter+0x7538` = 0; 3 unchecked reads (`0x02E284BC`, `0x02E285E8`, `0x02E28890`) crash | the base fighter's case (its static singleton) |
| `0x02E43148` | descriptor getter `0x02E4313C` (r4) | `0x02E43168` | `0x02E43780` → **abort** `0x04ADC364` | its own descriptor (copy of the base's, own motion table) |
| `0x02EA6C94` | vl param load `0x02EA6BC4` (r4) | `0x02EA6CB4` | `0x02EA6DB8`: reads `mgr+0x111C+4k` without loading | a copy of the base's case storing into the new kind's fields (RAM doc), also loading the base |
| `0x02EA5DA0` | vl param unload `0x02EA5D64` | `0x02EA5DC4` | `0x02EA6AFC` | copy of the base's case, the new kind's fields |
| `0x02E02458` | AI on `[ai+0x18]` | `0x02E02474` | `0x02E034A0`: generic AI | default is fine; the base's case for its AI |
| `0x0275B44C` | AI `0x0275B440` (r5) | `0x0275B46C` | `0x0275BA84`: returns 0 | default is fine; or the base's case |

Switches that stop before `0x40` (the kinds past their bound already go to the default, which is the
"no special handling" path): 20 AI switches on `[+0x18]` (`0x026F4C24`, `0x026F4F10`, `0x026F5114`,
`0x026F5240`, `0x027011B4`, `0x02701B9C`, `0x02701F7C`, `0x027030FC`, `0x027047CC`, `0x02704930`,
`0x02704C94`, `0x02705054`, `0x027051BC`, `0x02707EF8`, `0x0270810C`, `0x02709740`, `0x02717488`,
`0x0271CF30`, `0x02DF0054`, `0x02E0CEC4`), a 58-case handler on the BattleObject kind `0x02010BFC`,
Kirby's copy set-up `0x02EFC944` (`0x33`), and `0x0274EB90` (an AI kind → group map, `<= 0x3C`, to
verify). The 17 HUD switches (`0x0267E228` ... `0x02687514`, Palutena's Guidance / Smash taunts) are on
**character id - 1** (`<= 0x3A`); new ids go to their default (no special lines).

`--scan` found 5354 jump tables; the 72 with 49-65 cases are all classified (`inv` / `no`: statuses,
article kinds `0xE2-0x113` at `0x02E0A74C`, ids `- 0x2710`, byte codes).

### 1.2 Kind-count bounds (immediates)

| site | instruction | what | new value |
|---|---|---|---|
| `0x021ED1A0` / `0x021ED1B0` / `0x021ED1E0` | `li r4,0x41` / `cmpwi 0x41` / `cmplwi 0x41` | random fighter: `rand(0x41)`, wrap, retry bound | `N` |
| `0x021E6E30` | `li r4, 0x41` | **second** random fighter pick (`0x021E4DD0`: `rand(0x41)` → character id → availability) | `N` |
| `0x0309FE68` | `cmpwi r4, 0x41; ble` | kind → character id `0x0309FE50` (already one too many) | `N - 1` |
| `0x02A79158` | `cmplwi r29, 0x41` | sound bank loader | `N` |
| `0x0275BAC0` | `cmpwi r4, 0x41` | kind → motion count (AI `attack_data.bin` check) | `N` |
| `0x02DE1DDC` | `cmplwi r6, 0x41` | AI file loader (`[+0x1BB0]`) | `N` |
| `0x02AC3F7C` / `0x02761528` | `cmplwi 0x41` | fighter resource holder loaded by Cap name | `N` |
| `0x02EA90E0`, `0x02EA9104`, `0x02EA9120`, `0x02EA913C`, `0x02EA9158` | `cmplwi r4, 0x40` | size-table getters (with the tables, 1.3) | `N - 1` |
| `0x02FCD770` | `cmplwi r4, 0x41; bge` | picks `[+0x10]` or `[+0xC]` by `r4 < 0x41` | verify |
| `0x02748648` / `0x0274868C` | `cmplwi r12, 0x41` | AI `[+0xA4] >= 0x41` (same field tested `0x33-0x35` at `0x0270BE10`) | verify |

Every `cmpwi` / `cmplwi` / `li` with `0x41` in `.text` (66 compares, 151 `li`) was looked at: the rest are
characters (`'A'`), sizes, rule / status ids, stage kinds (`[[0x102F7020]]`), the `ATKD` magic, copies of
0x41 words (Manifold's four non-kind "bounds") and library code.

### 1.3 Static tables

| table | entries | reader(s) | note |
|---|---|---|---|
| `0x102FF484` | 65 ptr | `0x0275DB24` | lowercase names |
| `0x102FF588` | 65 ptr | `0x0275DB38` | Capitalised names |
| `0x10353DB4` | 65 ptr | `0x02EA6C40` / `4C` (vl load) | `fighter_param_vl_<name>` |
| `0x1012F638` | 65 u16 | `0x02EA90E0` | special-block size |
| `0x1012F6BC` / `F700` / `F744` / `F788` | 65 u8 each | `0x02EA9104` / `9120` / `913C` / `9158` (`addis r12, r4, 0x1013; lbz`) | special N / S / Hi / Lw block sizes |
| `0x100D21D8` | 65 u32 | `0x02AB8CB0` | sound class 0-3; **no bound** |
| `0x1033BE68` | `{-1, ""}` + 82 `{id, name}` | `0x0293DCCC` (`li r4, 0x53`) | character id → UI name (1.6) |
| `0x10340BBC` | 58 ptr (kinds 0-0x39) | sound-side parser `0x02A63954` (`cmplwi r25, 0x3A` at `0x02A63AFC`) | name-matched records; optional |
| `0x10340F8C` | 62 ptr (other order: Mario first, transformations / Miis at `0x30`-`0x36`) | `0x02ABA37C` (`cmplwi r28, 0x3E` at `0x02ABA4C8`) | the same order as `commonsoundtable.csb`'s 62 entries; optional |
| Kirby: `0x1038281C` | 58 ptr | 6 sites `0x02EFD83C`-`0x02EFDF84` (index `fighter+0xB9CC`) | per-kind copy record `{entries, count}` |
| Kirby: `0x1041A6D0`, `7B8`, `8A0`, `988`, `A70` | 5 x 58 ptr | `0x030C46DC`-`0x030C470C` | copy owner, hat, item, Bayonetta guns |

Per-kind descriptors (e.g. Mario `0x103A7BDC`, Purin `0x103DBE74`) and specializer singletons are one static
object a kind, reached only through the switches. There are no other pointer tables of 56-66 entries
(relocation runs, nulls allowed) and no other value table of that size indexed by a kind (structural scan
of every constant-base indexed access; the binary has no small-data `r2` / `r13` addressing, so every
static address comes from a relocated `lis` pair and is found).

### 1.4 Loops over kinds (RAM arrays)

`0x02EA5C9C`, `0x02EA5CBC` (maps `fighter_param.bin` entries by word 0: **entries for kinds `> 0x40` are
never looked up**), `0x02EA6B8C` (param manager); AI record inits `0x0274EAA8`, `0x0274EAC8`,
`0x027588BC`, `0x027588DC`; 14 `li 0x41` in `0x0275233C`; float / double `[0x41]` arrays at
`0x03B2EED4` / `0x03B2EEF4` (`0x03B2EDA8`) and `0x03B36454` / `0x03B36B5C` (`0x03B35F1C`). The
immediates become `N` only together with the arrays they index: `docs/kind-expansion-ram.md`.

### 1.5 Predicates and range checks

A kind `>= 0x41` is already answered correctly ("no") by: isMii `0x02E694AC`, isMiiEnemy `0x02E694E8`,
`0x028E25C0`, has-transformation `0x02E69510`, `0x02E69560`, `0x03058B6C`, `0x03058B8C`, transform → base
(`0x030BF9C0`, `0x030C1FDC`: other kinds returned unchanged), the AI armor check `0x02704F44`, and the 10
inline Mii-enemy range tests. The data flow found 47 more compares on a kind in the `0x39-0x3F` range
(`--scan`, marked `ok`): all are closed ranges (`0x3A-0x3D`, `{0x2F, 0x32, 0x38-0x39}`, ...) or the
compiler's binary-search splits of equality switches. **No open-ended "kind `>= 0x3A` = special" test was
found outside Kirby's copy code** (1.7).

### 1.6 UI character ids

- `ui_character_db` accessors (`0x0309FB94`-`0x030A0C58`, 19 of them) look ids `<= 0xC7` up **by position**
  and read the id as a byte (`0xFF` = none): new ids 59-199 need entries at those positions (the specials,
  ids `>= 200`, are searched for, so they can move).
- Character id → UI name `0x1033BE68` (`0x0293DCCC`): cave copy with one `{id, "Name"}` a new id, the count
  `li r4, 0x53` at `0x0293DCD4` raised, the `lis` / `addi` relocations moved (as the stage name table).
- Random select `0x02FFB610`: `li r23, 0x51` at `0x02FFB644` (database entries scanned) + new entries. The
  set is 12 bytes copied to `+0x98`: **at most 96 database entries** (82 now, so 14 new characters) without
  widening it.
- Character select layout: `num_%03d` arrangements and `face_001`-`face_096` (`lumen/chara/chara.lm`): 96
  slots.
- Unlock index `0x030A0A3C`: a non-DLC id not in `unlock_condition_of_fighters.bin` is unlocked.
- HUD switches on id - 1 (1.1): default.
- `ui_character_mask.bin` is in the data folder (57 ids, a flag each) but no string in the executable names
  it; the mask check `0x0293C378` returns 0 (hidden) for an id missing from a loaded mask, so if anything
  does load it, new ids need a row.

### 1.7 Kirby's copy ability (optional)

`copy_grant` refuses kinds `>= 0x3A` (`0x02EFCDC8`), so a new kind is simply not copied and nothing else
runs. To let Kirby copy one: raise that bound and the three copy-resource bounds (`0x030C46C8`,
`0x030C526C`, `0x030C5BDC`, all `cmplwi 0x3A`) and the copy voice bank bound (`0x030C0FF8`, `> 0x39`), and
give the six 58-entry tables (`0x1038281C`, `0x1041A6D0`...`0x1041AA70`) rows for the new kinds. The copy
set-up switch `0x02EFC944` defaults to no set-up. Kirby's vl file also has a per-kind copy table
(`0x88` bytes a kind, `[[mgr+0x113C]+0xFC]`): a data / RAM item.

### 1.8 IDs that encode the kind

- **ACMD effect IDs** `0x3KKnnnn` (kind KK's own effects) and `0x4KKnnnn` (Final Smash): an 8-bit kind
  field, room up to `0xFF`. The decoder was not located; the effect folder itself is loaded by name.
  To test with the first new kind.
- **Fighter resource IDs** `kind*0x11 + 6..0xF` (`0x030C010C`, the sound / effect / model holders) and
  `kind*9 + 1..8` (`0x030C1848`, `0x030C1BBC`, `0x030C20F4`): keys of a map (`0x030BF00C` searches a
  tree), not array indices, so no bound. Kind `0x5F` gives `0x655-0x65E` / `0x358-0x35F`; whether another
  ID space shares those values in the same holder was not checked (others seen: `base + 0x1EC...`,
  `slot << 28`).
- **Sound IDs** are `soundlabeltable` row `<< 16 | label` (by the bank's BINF id), not the kind; new banks
  need new rows (`docs/params/fighter_files.md` section 6). `.sqb` set ids are per file.
- Costume → voice variant `0x030C1B34`: unlisted kinds use variant 0.

### 1.9 Data files with one entry per kind / per id

| file | keyed by | entries | for a new kind |
|---|---|---|---|
| `fighter/fighter_param.bin` | kind (value 0) | 65 | add an entry (the manager's entry array is sized by the file; the kind map is a RAM array) |
| `ai/fighter_ai_fighter_param.bin` | kind (value 0) | 65 | add |
| `ai/fighter_ai_nfp_learning_param.bin` | kind (value 0) | 65 | add (amiibo) |
| `simple/simple_character_db_cafe.bin` | kind (value 0) | 65 | add |
| `sound/audience_ouen_param.bin` | kind (+ variant) | 70 (kinds 0-0x39) | add (crowd cheers) |
| `fighter_param_vl_<name>.bin` | name | 1 a kind | new file |
| `ui/ui_character_db.bin` | id (position) + kind (`+0x10`) | 82 | entry at position id |
| `ui/ui_layout_db.bin` | (id, variant) | 101 | rows (else random's layout) |
| `ui/ui_skill_db.bin` | id 0-58 | 59 | row |
| `ui/ui_sound_call_voice_db.bin` | id 1-58 | 58 | row (announcer call) |
| `ui/ui_sound_voice_db_cafe.bin` | 0-62 (two groups) | 63 | probably the 62-entry sound order + 1; verify |
| `ui/ui_nfp_db.bin` | id | 66 | amiibo only |
| `ui/record_vs_param(_cafe).bin` | 0-78 / 0-74 | 79 / 75 | VS records; not traced |
| `sound/config/soundlabeltable.bin`, `commonsoundtable.csb` (62, voice-bank order) | bank / sound order | | rows for new banks |
| `ui/message/melee.msbt`, portraits, `unlock_condition_of_fighters.bin` | name / id | | as in `new-fighter-slot.md` |

### 1.10 How complete

- Jump tables: complete (every `bctr` table in `.text`; the 49-65-case ones are all classified).
- `0x41` compares and `li 0x41`: complete (all reviewed).
- Tables: complete for tables whose address is built in code (relocation-based; no small-data addressing).
- Compares in `0x39-0x42` on a kind: the data flow follows parameters / returns of known kind functions and
  fields a function passes to one. 71 compares are inventory sites and 47 more are reviewed kind compares
  that need no change (`ok`); of the remaining relational
  compares in that range, 299 test a loaded value whose field isn't known as a kind and 341 a computed value.
  Samples of both were sizes, characters, statuses and switch splits; they were **not all reviewed**. The
  realistic miss: a kind read from a field the data flow doesn't know, compared with `0x3A-0x40` in an
  open-ended way. None was found among the ~60 reviewed by hand.

## 2. A fighter with no native code of its own: what each case needs

A new kind whose moveset is MSC / ACMD still needs these native pieces (the game has no "generic fighter"):

| piece | why it can't be skipped | the new kind's case |
|---|---|---|
| specializer | `fighter+0x7538` is read unchecked at 3 sites | the base's singleton (shared: it is already shared by every fighter of that kind). Smallest: miienemyf (4 slots, 82 instructions; Mii-specific), purin (4), donkey (5), samus / ganon (6), mario (8, 169 instructions). Its hooks run for the new kind as for the base; `--vtables` in `fighter_kind_tables.py` lists them |
| descriptor | the getter aborts | a copy of the base's descriptor with `+0` = the kind, `+4` its own motion table (CRC32 hashes of its `.omo` names, `docs/params/fighter_files.md` 4.2), `+0x1C` = 0 (filled at run time: the copy must be in **writable** memory) |
| vl param load / unload | the parsed params and the slot | the base's parser / free functions storing into the new kind's fields (RAM doc), and the base's own file loaded as well: the specializer reads the base's slot by fixed offset |
| size tables, sound class | specials' work blocks; sound class | the base's values |
| AI | | both 65-case switches default to generic AI; the base's case gives the base's AI. AI files load once `0x02DE1DDC` is raised |
| everything else | | defaults (1.1, 1.5) |

What the new kind gets from the base: native special-move hooks, articles (weapon kinds belong to an owner
name: new articles would need the 389-entry weapon tables grown, out of scope), and the inline `kind == base`
checks don't fire for it. Statuses, motions, ACMD, MSC, params, model, sounds, effects are its own.

## 3. Patch strategy and size

### 3.1 Per item

- **Switch** (6): patch the `bgt default` after the compare into `bgt CAVE` (1 word). The cave:
  `cmplwi rK, N-1; bgt <old default>; addi r12, rK, -0x41; slwi r12, r12, 2; lis/ori r0, TABLE; add; mtctr;
  bctr`, and `TABLE` = one `b` per new kind (branch offsets computed for the cave address). r0 / r12 are
  the scratch registers the original dispatch uses. No relocation is touched (the original table stays).
  ~9 words + 1 a kind, per switch.
- **Table** (9 + UI names): cave copy with the new rows (pointer tables: absolute addresses, the RPX loads
  at its link address); repoint the `lis` / `addi` (or `addis` / `lbz`) pair of each reader and move those
  two relocations to the dead word with `reloc:` (stage work, `docs/stage-expansion.md` v5). 9 readers = 18
  relocations; character names 1 reader = 2. The size getters also get `cmplwi r4, N-1`. The sound-class
  getter has no bound: the copy needs all `N` rows.
- **Immediate** (17): one word each (`--n N` prints them).
- **Strings**: new names in the cave.
- **Descriptor and motion table**: data in the cave. The game writes descriptor `+0x1C`, so the copy must be
  writable: the grown code space is writable on Cemu (the existing caves keep variables there, e.g.
  `position_vars_cave.py`); on a console the text segment may not be. Alternatives: build the copy at run
  time into `.bss` / heap from the descriptor case.
- **Space**: the grown code space ends at `0x04BB8670` (text region of the RPL file info); the caves use up
  to `0x04B84800` (`trait_badge_cave.py`), leaving ~207 KB. Per new kind ~3 KB (descriptor + a ~600-motion table ~2.4 KB, names,
  table rows, 2 vl cases ~0x100 bytes), so 31 kinds fit.

### 3.2 Totals

| | sites | words patched in place | relocations moved | cave |
|---|---|---|---|---|
| switches | 6 | 6 | 0 | 6 x (9 + n) words |
| tables (names, values, character names) | 10 | 20 (reader pairs) + 5 bounds | 20 | names 3 x 4N + strings; values 2N + 4N + 4N + 4N bytes; character names 8 x (0x53 + n) |
| immediates | 17 | 17 | 0 | |
| vl cases, descriptors | per kind | | | ~3 KB a kind |
| **must, total** | **33** | **~48** | **~20** | |
| Kirby copy (optional) | 11 | 5 bounds + 12 reader words | 12 + 10 | 6 tables of N |
| RAM (other doc) | 25 immediates | | | |

### 3.3 The "extra kinds" table

One record per new kind; a generator (to write, like `stage_slot_cave.py`) turns it into the patches above,
and `add_fighter.py` (to write) into the data rows. `tools/kind_code_scan.py --plan FILE` already resolves the
per-kind values (base cases, table values) and prints the immediates; `--plan -` uses the example.

```json
{
  "n": "0x60",
  "cave": "0x04B7F000",
  "kinds": [
    {
      "kind": "0x41", "name": "wolf", "cap": "Wolf",
      "base": "fox",
      "descriptor": {"from": "fox", "motion_hashes": "fighter/wolf/motion/list.txt"},
      "ai": "base",
      "ui": {"id": 59, "name": "Wolf", "series": 2, "costumes": 8, "sort": [59, 59, 59]},
      "sound": {"se_row": 3252, "vc_row": 3253, "sqb_set": "0x70"},
      "kirby": {"copy": false}
    }
  ]
}
```

- `kind`: consecutive from `0x41`; `n` = the last + 1 (all immediates and table sizes follow it).
- `name` / `cap`: folder and file names (`fighter/<name>/`, `fighter_param_vl_<name>.bin`, `snd_se_<Cap>`).
- `base`: the existing kind whose native cases (specializer, vl parser layout, AI, size tables, sound class)
  it uses.
- `descriptor`: whose descriptor to copy and the motion list for its own hash table (none: the base's).
- `ui`: character id (its position in `ui_character_db.bin`) and the name in the character-name table
  (portraits / `MmelChara*` labels).
- `sound`: rows for its banks (`soundlabeltable`), `.sqb` set id.
- `kirby.copy`: whether Kirby copies it (adds the 1.7 items).

## 4. Risks

- **RAM arrays** (the other doc) dominate the work; this page's 25 loop immediates are useless without them.
- **vl parsers write fixed fields** of `[mgr+0x2574]` (`+0x320 + 4k`): a new kind's case needs storage
  outside that struct (RAM doc).
- **Writable descriptor** on a console (3.1).
- **Effect IDs**: the `0x3KK` decoder wasn't found; an 8-bit kind fits, but per-kind arrays behind it would
  not show up in this scan if they are heap arrays.
- **Resource ID collisions** above `0x450` in the fighter resource map: not checked.
- **Two unidentified name-matched sound parsers** (`0x02A63954`, `0x02ABA37C`): if their files need a row per
  fighter, new kinds have none (probably silent).
- **Unreviewed compares** (1.10) and the 4 `verify` sites.
- **Save data / records** by character id (`record_vs_param*`, VS records): untested, as in
  `new-fighter-slot.md`.

## 5. Notes

The scanners and the data flow are in `tools/kind_code_scan.py` (`--scan`); the inventory there is the
source of the tables above. Manifold's 15 bound sites (`docs/manifold-notes.md`) are all classified here: 9
real ones in 1.2 / 1.4, `0x0309FE68` / `0x0275BAC0` in 1.2, and its 4 copies of `0x41` words (`no` in
`--scan`). New since `docs/new-fighter-slot.md`: the second random pick `0x021E6E30`, the 58-entry Kirby
copy tables and their 5 bounds, the 58 / 62-entry name tables of two sound-side parsers, the 96-entry cap of
the random-select set, the sound-class getter without a bound, and the `--plan` record format.
