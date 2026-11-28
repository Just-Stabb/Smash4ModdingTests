# Sm4shCloneTool: internals

The tool for other creators (`tools/sm4shclonetool/`, user guide in its `README.md`): clones fighters and stages into
new slots on a **vanilla** game, BrawlEx-Clone-Engine style. It is built on the research generators in `tools/`
(kind expansion, weapon kinds, effect banks, custom moves, stage slots) but carries none of this repository's own
executable patches or fighters: it starts from the creator's own cross_f.rpx and data.

## Layout

```
tools/sm4shclonetool/
  cli.py, gui.py                 command line, Tkinter window (PNG -> tk.PhotoImage: no ImageTk needed)
  sm4shclonetool/
    _paths.py                    imports from ../vendor (in the repository too)
    rpx.py                       an RPX in memory: words by address, resize .text, relocations, save (rpx_patch / rpx_compact)
    exe.py                       detection, the marker, the vanilla view, running the generators, the patch
    roster.py                    fighters / stages from the databases, the CSS order, the project file
    fighter.py                   a fighter clone's data (add_fighter.py's functions), customs, sound config
    stage.py                     a stage clone's data (add_stage.py's helpers)
    textures.py                  .nut decode (nut.py), PNG -> portrait in a set's format, new NTWU icons
    preview.py                   CSS (chara.lm via chara_layout.py, or a grid) and SSS previews
    clone_extras.py              (1.3) the executable's sound aliases, results announcer call, Kirby copy hooks
    narration.py, music.py       (1.3) the clone's own announcer call / victory fanfare (data side)
    voices.py, audio.py          (1.3) every voice line by category, WAV replace; nus3bank tones, IDSP, WAV, preview
    plates.py, languages.py      (1.3) name plates in the game's style (fonts/), names in every region's melee.msbt
    session.py                   folders, registry, plan (Check), build (the package), post-build checks
  tests/                         repository-only: fixtures, the vanilla stand-in, run_all.py, repo_test.py
  make_vendor.py                 regenerates vendor/ (the tool's adapted copies of the research modules)
  make_package.py                the standalone zip
```

`vendor/` holds the tool's own copies of the research modules it runs on, made by `make_vendor.py` from `tools/`:
`rpx_patch`, `rpx_compact`, `ppcasm`, `kind_expand` (+ `kind_expand_ram.json`), `weapon_expand`, `base_effects_cave`,
`base_customs_cave`, `stage_slot_cave`, `s4param`, `msbt`, `add_fighter`, `add_stage`, `add_fighter_customs`, `acmd`
(+ `acmd_info.json`), `nut`, `chara_layout`. Adapted, not verbatim: comments and docstrings taken out (they described
this repository's builds and fighters; the tool's docs describe what it uses), a header of their own, the defaults
pointed at the tool's code space instead of `tools/extra_kinds.json` / `build/` and the research's dummy word, and the
parts written for this repository's own fighters taken out (below). `make_vendor.py` refuses a copy that still names
them. The repository's tool imports these copies too (`_paths.py`), so it runs the code it ships. Dependencies:
Python 3.9+, numpy (nut.py), Pillow, Tkinter.

What was specific to this repository's own mod in the code, and what the copies do instead:

| module | what | in the tool |
|---|---|---|
| `weapon_expand` | `kirby_copy()`: a brand-new article added to Kirby's copy-article lists (`KIRBY_COPY_TABLE`, `KIRBY_RESERVE`, `KIRBY_COPY_RES`, `extra_relocs`), written for one fighter's custom Kirby copy | removed with its spec key; Kirby's copy lists are untouched |
| `kind_expand`, `weapon_expand`, `base_effects_cave`, `base_customs_cave`, `stage_slot_cave` | defaults: `SPEC` = `tools/extra_kinds.json` (the repository's seven fighters), `RPX` = `build/...`, caves in the repository's layout (`0x04BA0000`, `0x04BB0000`, `0x04B88000`, `0x04B8A000`, `0x04B7C000`), relocation dummy `0x037EE73C` (a word of a function the repository's own caves reuse) | no default spec / RPX (the tool always passes them), caves = the tool's parts, the dummy = the tool's marker block |
| `acmd` | `_new_commands()` merged the repository's own new ACMD commands (`acmd_ext_cave.NEW_CMDS`, `New_Var`) into the table | removed; `acmd_info.json` without those 33 commands (602, the game's) |
| `chara_layout` | `user4` / `user5` / `relayout` / `sheet`: one creator's honeycomb select layout and its rewriting | removed (the tool only reads layouts) |
| `add_fighter` | `KINDS` from `fighter_param.py`, `load_records()` reading `extra_kinds.json` | removed (the tool builds the records) |
| `nut` | `np.pad(mode='edge')` | `mode='symmetric'` (the padding is outside the picture) |
| `kind_expand_ram.json` | its `about` named the repository's scanner | reworded; the 164 sites are the game's |

Nothing else in the code was specific to those fighters: kind_expand's `tail_vector` / `motions` / `motion_group2`
record keys and weapon_expand's brand-new-article keys (`on_hit`, `nop`, `modules`, `spawn_from`, `flags_set`) are
generic features the tool doesn't use (its records never set them). `tests/package_clean_test.py` fails the package if
any name of this repository's fighters (every name in `tools/extra_kinds.json`), its executable builds or caves, its
paths or its authors appears in it.

## The executable

### Code space

The game's `.text` ends at `0x04B77E1C`; its text region (RPL file info `textRegionSize` 0x2BB8670) reaches
`0x04BB8670`. The tool's code space starts at `0x04B78000` (`exe.PARTS`, offsets from the base; `exe.configure(base,
registry)` sets each generator's `CAVE` / `LIMIT`):

| part | offset | |
|---|---|---|
| marker | 0x0000-0x4000 | the registry and the originals; its last 8 bytes = the relocation dummy (`DUMMY_OFF`) |
| stage | 0x4000-0x5000 | `stage_slot_cave` |
| customs | 0x5000-0x6000 | `base_customs_cave` |
| effects | 0x6000-0x8000 | `base_effects_cave` (kept at v1's place: the game's calls to imported functions point into this space in the file, and a wrapper on one of those addresses would look like such a call to `import_call_check`) |
| random | 0x8000-0x8100 | `random_select.py` (the allow mask, the store stub) |
| extras (1.3) | after the weapons, `0x800 + 0x1C0` per fighter (rounded to 0x1000) | `clone_extras.py` |
| weapons | 0xA000- (past the file's import-call targets, which end at 0x04B811D0), 0x10000 + 0x1800 per own article | `weapon_expand` |
| kinds | after the extras, up to `MAX_SPACE` (3 MB) | `kind_expand` (about 5-6 KB a fighter: descriptor, motion table, vl cases) |

The code section is grown to the last word written, at least to `0x04BB8000` (`SIZE`); past the text region's end
the region is raised (`textregion`). The marker records the end. `MAX_SPACE` keeps the copied vl load / unload cases'
calls into the game (`0x02EA....`) inside a branch's reach (the generators assert it). Moved relocations go to the
tool's own dummy word.

### Detection

`exe.inspect()`:
- **patched**: the marker (`b'Sm4shCloneTool\0\0'`, u32 format 1, u32 length, u32 CRC32, zlib(JSON)) found on a
  0x1000 boundary from `0x04B78000` up to the code section's end;
- **vanilla**: no marker, `.text` ends at or before `0x04B78000`, the text region at least the game's, and the
  generators' own checks pass in a dry run (`check_sites()`: a one-kind spec with a weapon and customs; every hooked
  word must hold the game's original: the six switch bounds, the 164 per-kind array sites, the table readers, the
  immediates, the AI guard, the 13 weapon switches and their dispatch, the weapon tables' relocated readers, the 13
  effect call sites, the two custom-move functions);
- **modified** otherwise. Hooked words that differ: refused. Only the code space in use: `--force` / "Patch anyway"
  puts the base at the next 64 KB after the code and raises the text region (`textregion`), the generators' text-end
  check pointed at that base.

The SHA-1 of the research's executable (`3b7e1b3f421f330e259a3200d391f47ee6b5931a`, docs/native-notes.md) is reported
when it matches but not required.

### Building (`exe.build`)

1. **Vanilla view** (`vanilla_view`): a patched input gets the marker's `orig` words written back, its moved
   relocations' `r_offset`s put back (section, entry offset, old offset), `.text` cut to the recorded end and the text
   region restored. A vanilla input is used as is. The view is saved to a temporary file (the generators read files).
2. The registry becomes the generators' spec (`kind_spec`): kinds 0x41.. in registry order, ui ids 59.., the native
   base (a vanilla kind: a clone of a clone keeps its source's base), weapon kinds numbered from 0x185 over the
   records' `weapons`, `ui.base_id` for customs.
3. `kind_expand.build`, `weapon_expand.build` (if any weapons), `base_effects_cave.build`, `base_customs_cave.build`
   (clones with customs), `stage_slot_cave.build` (stages) on the view. Two parts writing one word with different
   values is an error.
4. Every word outside the code space is recorded with the view's value (`orig`), the code section grown to the code
   space's end, the words written, the relocations moved (`reloc_args()` sites, the stage table sites, weapon_expand's
   `extra_relocs`) and recorded, `rpx_patch.reloc_clashes` checked, the marker written, the file saved
   (recompressed, CRCs, packed).

So the output depends only on the vanilla view and the registry: three builds one clone at a time give the same
memory image as one build of all three (files differ only in section placement), and patching again with the same
registry gives the same bytes.

The spec's capacity grows with the clones: kinds `max(0x60, 0x41 + n rounded up to 0x10)` (kind_expand's bound is
0x13F), weapon kinds `max(0x1C0, 0x185 + articles rounded up)`.

## The data side

`session.Session`: `data` (the creator's data), `ui` (their UI, default `data/ui`), `exe`, `out` (the project).
The newest copy of every file is read first from `out/INSTALL_TO_data`, then from the data / UI folders, and written
into `out/INSTALL_TO_data`; files equal to the data folder's are pruned at the end. So the package is cumulative and
installs over the creator's install whether or not an earlier package was installed.

**Registry**: the executable's marker when the input is patched (the source of truth), else the project's
`sm4shclonetool_project.json`. A fighter record: `kind, name, cap, ui_id, ui_name, title, base` (native vanilla
base), `source` / `source_kind` / `source_ui` (what was copied: a vanilla fighter or a clone), `base_ui_id`,
`weapons` (article names), `customs`, `fanfare`, `sort`, `series`, `costumes`, `subtitle`. A stage record: `name,
cosmetic, kind, source, source_cosmetic, title, series, page`.

**Fighter** (`fighter.build`): `add_fighter.edit_params` / `edit_msbt` / `copy_portraits` / `copy_folder` with a
record built here, so the source can be a clone (`bkind` = its kind, its rows, its folder, its effect bank
`0x3KK`); `add_fighter.UI_NAMES` extended with the clones' ids; `used_texture_ids` over the package and both UI
folders. Then imported PNGs (`textures.put_png`: the set's file of the base, else another character's, as the
format; new texture ids from `0x28010000 + 0x100 (id - 59) + 0x80`), custom-move labels / icons
(`add_fighter_customs.py` on a one-record spec), the fanfare (`bgm_fighter.fbb` record = kind, the source's row) and
the KO voices (`commonsoundtable.csb` record `0x3E + kind - 0x41`, the source's record found by its Capitalised name in
the executable's table `0x10340F8C`). add_fighter's checks run on every file (without the new rows, the input
byte for byte; melee.msbt the same).

**Placement**: the CSS order is `+0x20` (the first sort key; `0x030A0874` returns it for the list sort
`0x028BE798`), DLC entries after (`0x028BF6AC`). "After X" = X's key + 1; entries at or above it move up by one
(`_renumber`: only that key changes; the post-build check takes those back out).

**Stage** (`stage.build`): `ui_stage_db.bin` (the source's entry at position = cosmetic id, kinds `0x80 + 2i` /
`+1`, page byte, order after every other), `ui_sound_db.bin`, melee.msbt (`MmelStageN_` / `MmelStageG_`), the icon
sets (`stage_13` keeps its shared texture id), `stage/melee|end/<name>/` with names renamed. Stage kind names come
from the executable's table `0x1011D95C` (vanilla names for kinds up to 0x7F).

## Previews

`preview.render_css`: the entries in CSS order; with `<ui>/lumen/chara/chara.lm` the faces' places of frame
`num_<count>` (`chara_layout.Lm.simulate()` and `faces()`), checked for missing / overlapping faces; else a 12-column
grid. Icons: the profile's `grid_icon` sets (`chr_10`, `chr_00`, `chr_13`). `render_sss`: pages 1 / 2 by order, 8
columns, `stage_10` (page 2 `stage_13`). A UI profile `sm4shclonetool_ui.json` in the UI folder overrides the layout
path, icon sets and icon size.

## Tests (`tests/`)

1.3: `run_all.py WORK VANILLA.rpx VPARAM VUI VFIGHTER SOUND_CONFIG [CUSTOM_CHR]` takes the game's v288 executable (the
stand-in below only when given a modded one); new: `extras_test.py PATCHED VANILLA` (the results call for every kind /
costume against the game's own function, the bank aliases, Kirby's copy hooks: unicorn), `media_test.py VUI_CHR WORK`
(the DSP-ADPCM encoder against the C one, IDSP / WAV, the plates against the game's, fonts), run_all's 1.3 checks (the
call's tones / labels, the fanfare BGM, win cameras, Kirby's copy files, a voice replaced from a WAV, every language's
labels), `rpx_valid` on every build, gui_test's extras / voices tabs. Fixtures added by `make_fixtures.py`: the narration
bank (SOUND_CONFIG's `snd_se_narration_characall.nus3bank` or `S4CT_CHARACALL`), `bgm_property.mpb`, a synthetic
fanfare bank, synthetic win cameras / Kirby copy hats and motions, a `data(us_fr)` region beside the data folder.

No untouched v288 cross_f.rpx was available. `make_vanilla_standin.py` makes a stand-in from a modded executable:
`.text` cut to `0x04B77E1C`, the text region restored, every generator-hooked word restored to the generators' stated
originals (read like `kind_expand_incremental.py`), the weapon switches' dispatch rebuilt in the game's form, the
relocations other caves moved onto a dummy put back (RELA entries stay sorted, so a moved entry's site is the matching
`lis` / D-form instruction in the gap between its neighbours, the LO paired with its HA's register), the stage-slot
sites' game instructions, and two other mods' hooks the tests run through (`0x02D1FDD8`, the save-record getter's
`0x02A53C68` / `6C`) restored from the game's sibling code. Other mods' hooks elsewhere stay (the stand-in is for
tests only).

`run_all.py WORK MODDED VPARAM VUI VFIGHTER SOUND_CONFIG [CUSTOM_CHR]` (fixtures by `make_fixtures.py`: vanilla param,
melee.msbt and Zero Suit Samus's portraits, partial vanilla Fox / Zero Suit Samus folders, a synthetic BattleField_f
folder and icons, sound config cut to the game's record counts, a custom UI = modded portraits + a synthetic
honeycomb `chara.lm`): three builds into one project (Fox -> foxclone with an own article, customs, PNG portraits,
placed after Fox, + BattleField_f -> CloneField; Zero Suit Samus -> zssclone on build 1's executable; foxclone ->
foxtwo on build 2's), then: incremental = all at once, idempotent, byte-for-byte rebuild; every changed word in the
code space or recorded; every changed relocation recorded; `kind_expand_test`, `weapon_expand_test`,
`base_effects_test`, `stage_slot_test`, `import_call_check` through `repo_test.py` (the generators pointed at the
tool's layout); the custom-move mapping in unicorn; every database rebuilt without the new rows; names, folders,
effect ids, portraits, icons; CSS / SSS placement on the vanilla and the custom UI. GUI: `tests/gui_test.py PYTHON_WITH_TK
DATA CUSTOM_UI EXE OUT SHOTS` (`gui.py --screenshot` under Xvfb: the window built, roster icons, the previews, the
remembered folders). Package: `make_package.py OUT.zip --check-exe EXE` unpacks the zip and runs its CLI with `python -I`.

`many_clones_test.py WORK STANDIN FIXTURES` (v1.1): 40 fighter clones (8 vanilla bases, own articles, two left out of
random) + 8 stage clones (page 2) at once and as 20 + 20 (same memory image; code space to `0x04BD1000`, 356 KB), the
research tests on it (kind_expand_test 1428 checks), `random_select_test.py` (the refill `0x02FFB610` run with its
database calls stubbed: the pool holds the game's fighters and the random clones below id 96, nothing written outside
its 12 bytes, the saved registers restored; the remove `0x02FFC5BC` for ids 0-0xFF), and a 40-clone data build:
refused with the game's 96-place layout, built with a custom layout to `num_112` and previewed. With 40 new kinds
kind_expand_test's check of the unpatched game reading past its own 58-name fanfare table finds two stray matches in
the data after it: a property of the unpatched executable, read as such.

`weapon_expand_test` has one Mario-specific expectation (weapon 0x185 = the fireball's module row); with Fox's
blaster as 0x185 it fails by design and `run_all.py` reads it as such. `base_customs_test` is written for this
repository's own mapping and isn't run; `run_all.py`'s customs check replaces it.

## Limits (v1.1)

Every cap on the number of clones found, and what the tool does about it:

| cap | where | old | now |
|---|---|---|---|
| character ids looked up by position | `ui_character_db` accessors `0x0309FB94`-`0x030A0C58` (ids `<= 0xC7`; `>= 200` searched) | - | stays: 141 clones (ids 59-199) |
| kind tables / per-kind arrays | kind_expand's capacity (names, sizes, sound class, switches, the parameter manager's arrays `0x25B0 + cap * 0x48`, the equipment object `0x320 + 4 cap`, the bounds) | 0x60 (31 kinds) | sized to the clones; kind_expand's own bound 0x13F |
| random select pool | see "Random pools (1.2)" | v1: 15 clones; 1.1 said "the first 37" but the pick (`0x028E21B4`) still scanned 0x51 bits: only clones with ids below 81 (the first 22) were ever picked | 1.2: a 224-bit pool (ids 0-223) in the tool's space, every access replaced: every clone |
| character select places | `chara.lm` arrangements `num_%03d` (`0x028BEE20`) and faces bound in order (`0x028BE920`); the list builder `0x028BF6AC` uses a growable list | 96 (the game's file: `num_013`-`num_096`) | the UI's highest `num_NNN` (`preview.css_capacity`); a plan past it is refused |
| stage select | `0x0298D068` fills `img_01`-`img_48` of each of the 2 pages (`lumen/stage/stage.lm`) | page 1: 48 (47 used) | 48 a page checked; 41 clones (1 + 40). More pages: not researched |
| stage-select ids | positional `<= 0xC7` | | stays: 144 |
| random stage pools | `+0xA4` / `+0xB4` (refill `0x02FFB76C`) and `+0xC4` / `+0xD4` (refill `0x02FFB8CC`), 128 bits each, bound 0x63 (`0x02FFC5C4`-style removes `0x02FFC604` / `0x02FFC6D0`), getters `0x02FFC5EC` / `0x02FFC6B8` | | stays: every stage clone is below 0x63 (at most 41: 0x38-0x60); 1.2 adds the per-clone choice (a mask on each refill's store) and clamps the stage helper `0x0301CCB4` (16-byte local, one bit per stage database entry) to 128 entries |
| weapon kinds | weapon_expand's capacity | 0x1C0 (59 articles) | sized to the articles |
| effect banks | the 8-slot bank table (`0x030C1278`), per match | | stays (a clone without its base uses 2 slots) |
| effect ids | `0x3KK....` (8-bit kind) | | kinds up to 0xFF: not reached (0xCD) |
| resource ids | `kind * 0x11 + n`, `kind * 9 + n` (map keys, `0x030C010C` ...) | | not a cap; collisions for high kinds not checked |
| custom moves | owned-move bits `0x02A51368` (51 ids) | | mapped to the base (base_customs_cave; the table covers every new id) |
| save records | `0x02A53C54` | | the new ids' records in the code space (RAM only), one per clone |
| code space | `0x04B78000`-`0x04BB8000` | v1 fixed 256 KB (kinds part 160 KB: ~27 fighters) | grows with the clones (text region raised), up to 3 MB |

## Random pools (1.2)

Every access to the character select's random-fighter pool found (static: every `bl` to the pool object's
functions, every `+0x98` / `+0x9C` / `+0xA0` access in the object's code and every reference to them as data; the
getter has one caller):

| address | what | 1.2 |
|---|---|---|
| `0x02FFB610` refill (from the set-up `0x02FFBB0C` and the count) | positions 0-0x50, available / not masked / not a Mii -> bit; random's id cleared; a 12-byte stack local copied to `+0x98` | replaced (`b`): the 224-bit pool of this object, positions 0 .. max(0x51, 59 + clones) - 1, the allow mask; `+0x98` gets ids 0-95 as a mirror |
| `0x02FFC4A8` count (from `0x03017BCC`, `0x03017E20`) | bits 0-0x50 of `+0x98`; under 8 -> refill; then the four stage pools | its loop (`0x02FFC4BC`) replaced: bits of the new pool |
| `0x02FFC5BC` remove (from `0x03017CFC`) | clears bit id (< 0x51) | replaced: the new pool and the mirror |
| `0x02FFC5B4` getter (from the pick only) | `+0x98` | kept (the mirror) |
| `0x028E21B4` pick (from `0x0290A454`, `0x0290A824`, `0x0290C5F0`) | copies the 12 bytes to the stack, counts 0x51 bits; for a player, a second copy without the other 7 players' ids (used with 7 or more left); xorshift (`0x105759D0`) % count, the n-th set bit -> id (a byte); none: `0x030A0F1C` (4) | replaced (a far jump: out of a `b`'s reach): the same with 7-word copies in a bigger frame, 224 bits |
| `0x0301CAE8` available-fighters helper (also `0x0290D960`, `0x029E6CE0`) | a bit per database entry in a 12-byte stack local: past 96 entries it writes over its frame (ids 128+ reach the saved registers: 1.1 with 70+ clones) | its count (`0x0301CB40`) clamped to 96 |

The new pool: 4 slots `{object, 7 words}` (an object not seen yet starts from its `+0x98` words), the allow mask
(7 words) and the stage allow mask (4 words), then the code, in the `random` part. Stage pools: the stores of the two
stage refills (`0x02FFB814`, `0x02FFB964`) ANDed with the stage mask.

`tests/random_select_test.py PATCHED [PICKS]` runs it in unicorn (database / availability / player calls stubbed):
the pool after a refill, a pick + remove cycle (every enabled id once), the count's refill, PICKS picks from the full
pool (every enabled id, none disabled, a chi-square test of uniformity), a player's pick without the other players' ids,
remove for ids 0-0xFF, the helper's loop with 200 entries, the stage refill with the mask; no write outside the pool,
its mirror, the random state, the lazy-init guard and the stack.

## Own sound banks and effects (1.2)

- Sound: `sm4shclonetool/sound.py`. The game loads a fighter's banks by file name with its Capitalised name (the
  clone's own: `snd_se_<Cap>.nus3bank` ...), each bank's id from its BINF; a sound id is `row << 16 | label` with
  the soundlabeltable row naming the bank id. The clone's banks get BINF names / ids of their own (the next free id
  in 2000-2999), rows of their own (the base's label lists, the last free row or a new one), and its ACMD sound ids
  (`sound.bin`: every int parameter; other scripts: SE / Sound commands) move to its rows. No executable change.
  MSC sound ids are not remapped.
- Effects: `"effects_base": false` in the generators' spec for a clone with its own effects: base_effects_cave then
  doesn't register the base's banks for it. Its effect ids are already its own (`0x3KK` / `0x4KK`, the folder copy).
- Results panel: `param/ui/result_param.bin` gets the clone's entry (the source's, by model name; vendor/result_param.py).
- Name plates (`chrn_*`): redrawn with the clone's title (`fighter.name_plates`), unless a PNG is imported for the set.
- Own articles default to all of the base's: its article list's entries before the special ones, named by the weapon
  name table (`exe.base_articles`, read through the descriptor switch's own jump table, which the kind expansion keeps).

## Not done / open

- Not done in 1.2 (asked for, not built): the clone's own CSS / results announcer call (a new label in the
  character-call narration bank: a TONE section append and a soundlabeltable label; the narration bank isn't in the
  test data), its own fanfare / results music track (new BGM entries and streams), Kirby copying clones with their own
  hats (copy_grant refuses kinds >= 0x3A; the copy tables, the ~22 copy-kind switches and the hat / motion loaders
  would need the new kinds: the research's Kirby copy work for added kinds is the reference), its own Final Smash
  cutscene / transformation kinds (camera/final and Fin<Cap> are copied by folder; the scene tables per kind and the
  transformation map 0x030BF9C0 / 0x030C1FDC were not extended), an own custom-move save bitfield, MSC sound-id
  remapping (needs an MSC reader), per-language msbt files, and a mode-by-mode emulated check (All-Star, Stadium,
  Smash Tour, Events, online, replays) with new kinds. Classic's save records, the random selects, the CPU AI files
  and amiibo rows are covered.

- In-game confirmation (nothing here ran in Cemu or on a console).
- Own sound banks (soundlabeltable rows), the announcer call, Kirby's copy: not offered (vanilla Kirby refuses new
  kinds).
- The game's character-select layout file is not read without a `chara.lm` in the UI folder; ties between equal sort
  keys are assumed to keep id order.
- Rewriting a custom `chara.lm` for a new count (only detected and reported).

## 1.3

### The game's own executable

1.3 was tested on the game's v288 `cross_f.rpx` (SHA-1 `a4cc56d89726c480637c20bea992a9afe8ee9ad9`, 37 of its 48
sections zlib-compressed; memory-image digest `57ea6573...`, `exe.V288_SHA1` / `V288_IMAGE`). Plainly decompressing it
does not give the research's `3b7e1b3f...` (that one's section layout differs), so that hash stays a "seen before" note.
The stand-in 1.1 / 1.2 were tested on (`tests/make_vanilla_standin.py`, from a modded executable) compared with it:
- memory: 1304 words differ in all, every one another mod's (hooks into the cut code space, data edits) that the
  stand-in left on purpose; none is a word the tool patches;
- the words the tool patches (445 for the run_all registry, every part): their recorded originals are identical except
  three: `0x030A926C` / `70` / `78`, the DLC unlock index (`0x030A9230`) that `stage_slot_cave` bounds. The game has
  `addic. r12, r28, -0x30` / `blt 0x030A92B0` / `addi r31, r12, 9` / `b 0x030A92B4` (no upper bound); the stand-in
  carried the research's bounded version (`cmplwi r12, 8` ...) as its "original". The patch written is the same; on
  the game's executable the marker now records the game's words (so un-patching restores the game exactly);
- relocations: the 124 the tool moves are identical; the stand-in still had 116 of other mods' relocations parked on
  the research's dummy word (none at a site the tool touches);
- the patched images from both are identical outside the code space except those 1304 words.
`run_all.py` takes the game's executable as its second argument (it makes a "modified" copy with one hooked word
changed for the refusal check); a modded executable still works the old way (stand-in). Every build is checked to be a
valid RPX (`rpx_valid`: each section's CRC, compressed sizes, the text region covering the code).

### Sounds (sound.py, clone_extras.py, voices.py)

- **Bank aliases.** A fighter's sound (row << 16 | label) plays only from that fighter's own bank handles: the finder
  `0x02C71898` matches the row's bank id with each handle's BINF id or the handle's alias (`+0x5C0` se, `+0x5C4` vc,
  `+0x5C8` cheer, `+0x580` the Final Smash's se_common), which the SoundModule set-up `0x02761C50` reads from
  `fightermodelbanktable.mtb` by the fighter's name (none for a new kind). With 1.2's own bank ids the base's ids the
  game plays from code (commonsoundtable.csb's KO / missfoot voices, the voice sequences, MSC scripts, the base's
  native code) found no bank for a clone. `clone_extras.py` gives a clone's handles its base's ids as aliases: hook
  SETUP `0x03127990` (`lwz r12, 0(r3)`, the sound manager's getter; acts only when called from `0x02761E44`, LR
  `0x02761E48`, after the MTB reads) and FS `0x03121FA8` (`lwz r3, 0(r3)`; from `0x02761598`, LR `0x0276159C`). The
  research's `sound_alias_cave.py` design, per clone kind (`rec["sound_alias"]`: the base's se / vc / cheer /
  se_common ids, from the banks' BINF before `own_banks` renumbers them). So **MSC sound ids** need no rewriting:
  they keep the base's ids and play from the clone's banks (item 12 of the 1.3 brief: documented instead of an MSC
  rewriter); the same for the soundseq `.sqb` and the csb records.
- **Kirby-copy voice bank** (`snd_se_vc_Kirby_copy_<Cap>`): Kirby's copy handles (`+0x5DC`, filled at `0x02761B00`
  from `0x02EFDE88`) have no alias, and Kirby plays it by the base's row: the clone's copy keeps the base's id (its own
  file / tones). nus3 loads one bank an id, so with the base and the clone in one match the later player's Kirby-copy
  bank is refused (only Kirby's copy voices of that player are affected).
- **Voices.** `voices.lines()` lists every tone of the clone's banks by category (the victory lines: the tones its
  `sound.bin` Win1 / Win2 / Win3 / ... scripts play through the soundlabeltable); `replace()` appends the WAV's
  DSP-ADPCM to PACK and points the tone at it (the TONE entry's group / volume kept). Replacing changes that line
  everywhere the game plays it for the clone (its own rows and, through the alias, the base's ids).
- **DSP-ADPCM**: `vendor/dspadpcm.py`, a port of jackoalan's grok.c (MIT); `media_test.py` checks it against the C
  encoder byte for byte (coefficients and frames).

### The announcer call (narration.py, clone_extras.py)

- Select: `0x0204CA14` -> `0x0294812C(the call database, character id, costume + 1)`, the only reader of
  `ui_sound_call_voice_db.bin` (searched by id; an id not in it would read entry -1: every clone has its row).
- Results ("... the winner is X") and three other callers: `0x02A65898(mode, kind, costume, flag)` (`play_result_characall_se`
  `0x030EECB4`, `0x02FE14A8`, `0x02FE1708`, `0x02FE1A28`): a switch on the kind (tables `0x100C870C`, `0x100C8640`,
  `0x100C8624`, the Koopalings' `0x02A65790` / `0x100C868C`, costume variants for Olimar / Alph, Wii Fit Trainer,
  Villager, Robin), kinds `0x3E`-`0x40` one call, **past 0x40 none** (a 1.2 clone was not called), then the region
  remap `0x02A657BC` (`0x10340CE4` pairs). `narration.results_calls` is the switch in Python (checked against the
  function for every kind and costume in `extras_test.py`).
- The hook: `0x02A65898`'s first four words become a far jump (the code space is out of a `b`'s reach); for a clone
  kind the function body runs with the base's kind and the result goes through the clone's `call_map` (base id ->
  its own label); other kinds replay the four words and jump back.
- Data: every base call id (16 select ids + results ids for costumes 0-15) gets a new tone in the main narration bank
  (a copy of the base's, from its DLC bank for a DLC base, or the creator's WAV) and a label appended to that bank's
  row (`sound.Table.set_row` rebuilds the label area; every other row keeps its list).

### The fanfare (music.py)

`bgm_fighter.fbb` record = kind (names `0x10340BBC`, kind order) -> BGM id -> `bgm_property.mpb` entry; the game's own
entries' names come from the executable's `(id, name)` table `0x100C7380` (593 pairs, filled at load by `0x02A640DC`
unless `0x02A7BA48` says the file's names stand), an added entry keeps its file name (`0x03116ECC`:
`%s/snd_bgm_%s.nus3bank`). A clone's own fanfare: the base's bank copied under `<name>_<Cap>` (BINF name / id 6400+
unused), a new entry (the lowest free id) copying the base's ints, the fbb record pointed at it. The results music after
the fanfare (`CRS24_VS_Result` ...) is per mode, not per fighter.

### Kirby (clone_extras.py, fighter.kirby_files)

Hooks (originals in the marker; the research's `kirby_copy_new_cave.py` design, generic): GRANT `0x02EFCDA4`
(`mr r28, r6`: a clone kind -> its base's: Kirby gets the base's ability, every copy table / switch the base's), RES
`0x030C46A8` / `0x030C5254` / `0x030C5BD0` (`mr r28|r16|r23, r4`: the copy resources' loader / helper / release; the
helper keeps the real kind), BODY `0x030C4710` (`lbz r10, 0(r7)`: motion folder `fighter/kirby/motion/<name>body`; not
`0x030C470C`, which carries a relocation) and HAT `0x030C4830` (`lwzx r7, r23, r21`: `fighter/kirby/model/<name>cap/cNN`)
for a clone with its own, VOICE `0x030C0FF8` (`cmplwi r29, 0x39`: the Kirby-copy voice bank loads for a clone that has
one). Kirby's copy ACMD is his own by motion name: the clone's copy motions run the base's copy scripts (own scripts
would need new motion names in Kirby's motion table: not built). Copy effects: Kirby's `effect.bin` calls the COPIED fighter's
bank (`0x3KK....`, KK = the copied kind: 54 / 56 / 41 ... for his copy scripts; read from a Kirby `effect.bin` of the
research repository's packages), not a sub-bank of his own; for a clone copied as its base those are the base's ids, so
they show only while the base's bank is loaded (the base in the match, or a clone without its own effect bank, whose
base banks load with it). Giving the copy the clone's own effects needs either Kirby scripts of its own (new motion
names) or an effect-id remap for Kirby while he holds a clone's copy: not built.

Kirby's copy sounds: his copy voices come from the copied player's Kirby-copy bank (the clone's own file, listed and
replaceable in the Voices tab); the copy's sound effects are labels of Kirby's own se bank played by his own copy
scripts (shared with the base's copy: separate labels would need separate scripts). The hat folder copy carries the
hat's own files (its model and material animations); the copy motions are the whole `<base>body` folder copied. No
Sm4shCommand names file is written: no new script slots exist (Kirby's scripts are shared). The window offers a hat
folder import; replacing single copy motions is done by putting .omo files in the clone's `motion/<name>body/`.

### Plates, fonts, languages

- `plates.py`: per set the text centre / width / line boxes / outline / shadow measured on the game's 66 plates;
  `media_test.py` compares 8 names a set (lines within 4 % of the height, centre within 4 %, width within 12 %).
- Fonts: bundled DFMincho-SU / DFGothic-SU (`fonts/`, FONTS_NOTICE.txt; package_clean_test allows exactly those two
  by name and SHA-256). The game's own fonts are Lumen `.brf` resources (`ui/font/resource/static/Gothic.brf`,
  `Folk.brf`, `ui/font/lumen/...`): bitmap fonts the tool does not draw with; "game" uses a TrueType font a UI mod put
  in `ui/font/`.
- Boxing Ring: `ui/info/aurora_punch_out/` (builder `0x026552B8`, from `0x02655434` / `0x02655F80`) reads
  `MmelCharaA_<costume>_<UI name>` through `0x030A02A4` (`0x0309FF74`: the db entry's per-costume label byte, by
  position for ids up to 0xC7): the clone's copies of its base's title-line labels.
- No other per-character text pictures are made by the tool: the Boxing Ring's title, the results screen's winner name
  (`ui/font/result_fgb/`) and the menus draw text with the game's fonts from `melee.msbt`.
- `languages.py`: `data(<region>)/ui/message/melee.msbt` beside the data folder, written to `INSTALL_TO_data(<region>)/`.

### Random stage switches

`0x02FFB76C` (the stage pool refill) keeps a stage when `0x0301BA8C(kind, 4)` (`0x0293FD40` on the type-1 checker,
vtable `0x100BAAFC`: +0x74 unlocked `0x026F2ED0`, +0x6C the switch `0x0293F298`, +0x4C) and the mask `0x02948858`
(an object never loaded in normal play: null -> allowed) pass. The switch: save `+0x38` (12 words, 5 bits a stage,
`0x02A517DC`, bounded) at the index `0x030A9230` returns (the switch screen's list `[0x102F7C38]`; DLC 0x30-0x37 ->
9-16): a stage clone has none (-1) -> always on, never written. No save layout change.

### Not built in 1.3 (researched; why)

- **Trophies**: `ui_figure_db.bin` (743 entries x 47 values), `ending_fig_get.bin` (Classic / All-Star awards), the
  trophy texts (not in the test data) and the save's trophy ownership (a bitfield sized to the game's 743 / 716 ids;
  not traced). Without the save's ownership layout traced, new ids can't be made safe; reusing unused ids was not
  researched far enough to name any. Not built.
- **Palutena's Guidance**: the conversation table is `ui_smashappeal_angeland.bin` (portraits `chr_14_<Name>_NN`,
  groups of 23 / 7 values), its voices and texts are not in the test data (no voice bank / msbt to copy), and the
  per-character lookup was not traced. Not built.
- **Smash Tour**: `param/worldsmash/*` (stat params, board data); its fighter pools / kind tables not traced. Not built.
- **amiibo**: `ui_nfp_db.bin` (66 entries x 5: the fighter's id ... amiibo character number, e.g. 58 -> 8453); writing a
  clone's id to a figure would put an id the unpatched game doesn't know on it: not built (no figure write traced, so
  none is done: the tool never touches figure data).
- **Final Smash**: transform kinds `0x3A`-`0x3D` map back to their base by `0x030BF9C0` / `0x030C1FDC` (fixed compares);
  a clone of Bowser / Wario / Little Mac / Lucario transforms into the base's transformed kind. Its own transformed kind
  (a kind cloned from 0x3A-0x3D, its resources by `kind * 9 + n`) and its own FS scene-table entries were not built.
- **Mode-by-mode emulation** (All-Star, Stadium, Trophy Rush, Events, Smash Tour, Records, replays, online): not done;
  the README's mode table says what was checked and how. `0x0290D960` (from the menus, `0x02178E24` -> `0x0290D708`)
  and `0x029E6CE0` (`0x029E6CC4`, from `0x029E7000` / `7118` / `76C8`) copy the 96-id available-fighters set (12 bytes)
  into structures at `+0x24` / `+0x30`; their readers were not traced (clones with ids 96+ are absent from them).
- **Base + clone in one match**: the per-kind state is per fighter; the shared things found are the kind's static
  specializer object (as for two players of one vanilla kind), the Kirby-copy voice bank id (above) and the Kirby
  loader's `res_kind` word (set at each helper call; the loader runs the match's fighters one after another).
