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
| weapons | 0xA000- (past the file's import-call targets, which end at 0x04B811D0), 0x10000 + 0x1800 per own article | `weapon_expand` |
| kinds | after the weapons, up to `MAX_SPACE` (3 MB) | `kind_expand` (about 5-6 KB a fighter: descriptor, motion table, vl cases) |

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
| random select pool | refill `0x02FFB610` (scan `li r23` at `0x02FFB644`), count of picks left `0x02FFC4A8` (`li r11, 0x51` at `0x02FFC4BC`), remove `0x02FFC5BC` (`cmplwi r4, 0x51` at `0x02FFC5C4`); the set is 12 bytes at `+0x98` of the pool object, `+0xA4` / `+0xB4` are the stage pools | v1: 15 clones (`n_sel <= 96` asserted); the count / remove bounds stayed 0x51 (clones with ids 0x51-0x5F, past v1's cap, would never have been removed) | scan `min(96, 0x51 + n)`, both other bounds the same; a stub on the refill's store (`0x02FFB6C4`) masks out clones with `"random": false`; ids >= 96 are never scanned (out of the random select). Not enlarged: the set is inside the object (the stage pools follow it) and the getter `0x02FFC5B4` hands its address to callers not traced |
| character select places | `chara.lm` arrangements `num_%03d` (`0x028BEE20`) and faces bound in order (`0x028BE920`); the list builder `0x028BF6AC` uses a growable list | 96 (the game's file: `num_013`-`num_096`) | the UI's highest `num_NNN` (`preview.css_capacity`); a plan past it is refused |
| stage select | `0x0298D068` fills `img_01`-`img_48` of each of the 2 pages (`lumen/stage/stage.lm`) | page 1: 48 (47 used) | 48 a page checked; 41 clones (1 + 40). More pages: not researched |
| stage-select ids | positional `<= 0xC7` | | stays: 144 |
| random stage pools | `+0xA4` / `+0xB4` (16 bytes each), bound `cmplwi r4, 0x63` at `0x02FFC620` | | stays: the first 43 stage clones (ids < 0x63) |
| weapon kinds | weapon_expand's capacity | 0x1C0 (59 articles) | sized to the articles |
| effect banks | the 8-slot bank table (`0x030C1278`), per match | | stays (a clone without its base uses 2 slots) |
| effect ids | `0x3KK....` (8-bit kind) | | kinds up to 0xFF: not reached (0xCD) |
| resource ids | `kind * 0x11 + n`, `kind * 9 + n` (map keys, `0x030C010C` ...) | | not a cap; collisions for high kinds not checked |
| custom moves | owned-move bits `0x02A51368` (51 ids) | | mapped to the base (base_customs_cave; the table covers every new id) |
| save records | `0x02A53C54` | | the new ids' records in the code space (RAM only), one per clone |
| code space | `0x04B78000`-`0x04BB8000` | v1 fixed 256 KB (kinds part 160 KB: ~27 fighters) | grows with the clones (text region raised), up to 3 MB |

## Not done / open

- In-game confirmation (nothing here ran in Cemu or on a console).
- Own sound banks (soundlabeltable rows), the announcer call, Kirby's copy: not offered (vanilla Kirby refuses new
  kinds).
- The game's character-select layout file is not read without a `chara.lm` in the UI folder; ties between equal sort
  keys are assumed to keep id order.
- Rewriting a custom `chara.lm` for a new count (only detected and reported).
