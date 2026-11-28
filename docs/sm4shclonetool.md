# Sm4shCloneTool: internals

The tool for other creators (`tools/sm4shclonetool/`, user guide in its `README.md`): clones fighters and stages into
new slots on a **vanilla** game, BrawlEx-Clone-Engine style, and (2.0) imports animations, effects, sounds and articles
into any fighter (article cloning included: "2.0" at the end). It is built on the research generators in `tools/`
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
    kirby_copy.py                (1.4) Kirby's own copy scripts for a clone (motion.mtable entries, script copies, names file)
    patchset.py, ppcflow.py      (1.5) the patch as data: relocatable export, the Aroma patch file, the Cemu graphic pack
    importer.py, pac.py          (2.0) the importer's data side: motions (KCAP packs, motion.mtable, scripts, vl group 1),
                                 effects (emitter sets, .efc entries), sounds (the Sound Adder's rules), names / aliases
    motion_exe.py                (2.0) the grown motion tables (the executable side of imported motions)
    articles.py                  (2.0) new articles / article clones: the files, the weapon_expand spec, the vl hooks
    session.py                   folders, registry, plan (Check), build (the package), post-build checks
  aroma/                         (1.5) the Aroma plugin: source, Makefile, the built sm4shclonetool.wps
  tests/                         repository-only: fixtures, the vanilla stand-in, run_all.py, repo_test.py
  make_vendor.py                 regenerates vendor/ (the tool's adapted copies of the research modules)
  make_package.py                the standalone zip
```

`vendor/` holds the tool's own copies of the research modules it runs on, made by `make_vendor.py` from `tools/`:
`rpx_patch`, `rpx_compact`, `ppcasm`, `kind_expand` (+ `kind_expand_ram.json`), `weapon_expand`, `base_effects_cave`,
`base_customs_cave`, `stage_slot_cave`, `s4param`, `msbt`, `add_fighter`, `add_stage`, `add_fighter_customs`, `acmd`
(+ `acmd_info.json`), `nut`, `chara_layout`, and (2.0) `ptcl`, `efc`. Adapted, not verbatim: comments and docstrings taken out (they described
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

## 1.4

### Kirby's own copy scripts, effects and voice bank (kirby_copy.py, clone_extras.py)

How a Kirby copy motion finds its scripts (traced): the MotionAnimcmdModule binds (`0x027606C0` sets 0-3, `0x027608DC`
the second layer, `0x02760CE8` the MSC rebind, vt +0x6C) ask `0x02E42518(mgr [0x102FF68C], kind, motion)` for the
script hash: the kind's entry (16 of 0x40 bytes) `+0xC` = its `motion.mtable` data, `lwzx` by motion, unbounded; the
hash is then looked up in game / effect / sound / expression.bin (`0x02E424D8`, `0x02BEE560`). Those three binds are
its only callers. The animation is the motion's own (Kirby's static table, descriptor `0x103829BC`: 1222 motions, the
copy packs `motion/<copy>body/` by file-name CRC). A copy's motions are the Kirby motions whose animations are in its
copy folder: e.g. Fox `0x31F-0x324`, Zero Suit Samus `0x3F9-0x3FF`; Dr. Mario / Lucina / Dark Pit copies share
Mario's / Marth's / Pit's folders with extra slots elsewhere (several runs). Kirby's copy effect scripts call the
copied kind's bank (`0x3KK....`, e.g. ZSS `0x3190005`), his copy sound scripts the copied fighter's se row (ZSS row 27,
bank 2028) and Kirby-copy row (132, bank 2098); some scripts `JUMP` to another copy script by hash.

The tool (data, `kirby_copy.own_scripts`): finds the base's copy runs (its copy folder's packs against Kirby's motion
table read from the executable), appends one `motion.mtable` entry per motion of the runs (the clone's own script
names: `<clone><tail of the animation name>` when Kirby's script name is `<copy><tail>`, else
`<clone>_kirbycopy_<motion>`), copies each script under the new hash with the base's effect ids moved to the clone's
kind (KK), the base's sound rows to the clone's own rows (sound.own_banks' map, the Kirby-copy row included) and
`JUMP` / `CALL` targets inside the runs to their copies; `rec["kirby_slots"] = [[lo, hi, newbase]]`. A rebuild finds
its entries again (same names, same place). `<out>/Sm4shCommand_names.txt` lists the names (one section per clone).

The executable (clone_extras.py, part "extras"):
- GRANT (1.3's hook, `0x02EFCDA4`) also records {Kirby's int array `[[[[fighter+0x726C]+8]+0]+0xC]`, the kind he was
  granted (the clone's own)} in KTAB (16 entries, round robin, RAM in the code space like the random pool), for the
  copies copy_grant accepts (not 8, below 0x3A after the clone -> base map). r8-r12 only (r0 holds copy_grant's LR
  until `0x02EFCDA8`);
- KMAP `0x02E42518` (`li r0, 0x10` / `li r12, 0` replayed, back at `+8` through ctr): kind 8 called from one of the
  three binds (return address `0x027607D0` / `0x027609F0` module r27, `0x02760D38` module r29), the module's
  accessor `+4` -> WorkModule `+0x28` -> the int array; its KTAB kind a clone whose base is the current copy (int
  0x100000A4, `+0x290`): a motion in one of the clone's runs becomes newbase + (motion - lo). Everything else: the
  game's lookup;
- COPYID `0x033EC060` (a bank handle's BINF id; `mflr r0` / `stwu` replayed): called from `0x027623F0` (the Kirby-copy
  handle finder vt +0x2EC `0x027623B4`, which compares with r28), a clone's own Kirby-copy bank id answers for the base's
  id. sound.own_banks now gives the clone's `snd_se_vc_Kirby_copy_<Cap>` its own BINF id and row
  (`rec["kirby_copy_bank"] = [own, base]`): nus3 loads one bank an id, so 1.3's shared id lost the later player's copy
  voices; now both load, Kirby's copy scripts of the clone play its own row, the base's ids it plays from code find it.

Tests: `extras_test.py` runs GRANT / KMAP (with the game's lookup after it) / COPYID in unicorn: KTAB contents, the runs
remapped for all three callers, other copies / kinds / callers untouched, the vanilla lookup's answers, 20 grants
writing only KTAB; the copy-handle finder answering for the base's id. `run_all.py`: Kirby's grown `motion.mtable`
(his 1222 entries unchanged), each new script = the base's copy script with only the clone's effect ids / sound rows /
own jump targets changed, the names file naming them all, the copy bank's own id. Kirby's vanilla ACMD and copy packs
come from the fighter dump (`VFIGHTER/kirby/script`, `motion/foxbody`, `motion/szerosuitbody`).

Not covered: a Kirby who swallows a Kirby holding the clone's copy gets the base's copy (copy_grant is given the base
kind: KTAB records the base); a clone of a clone copies its source's scripts with the vanilla base's rows (its rows
answer through the alias).

### The plates' weight and tone (plates.py)

Measured on 14 of the game's plates a set (`style_metrics`, numpy only): fill coverage, stroke thickness (twice the
mean distance to the edge), median stem run, rim coverage, raw channel values of the fill / rim cores, anti-aliased
edge pixels per edge pixel, top / bottom gradient. The game's plates: no gradient; chrn_11 / 40 fill R=G=255 and rim
R~29 G=255 B=0; chrn_12 fill 254.6, rim ~27 (block-compressed: 16-32), alpha 255. The rim is the fill dilated by a disc
(best fit of the game's own rim on its own fill, IoU 0.97 / 0.97 / 0.99: radius 3.5 / 5.5 / 9, shadow (3, 5) / (5, 9) /
(8, 15) for chrn_12 / 11 / 40). 1.3: square dilation 4.5 % of the cap height (fill +21-34 %, strokes +12-18 %), Lanczos
down-sampling (soft edges +0.15-0.19). 1.4: per set `bold` 0.4 / 0.4 / 0.35 % (a round dilation, fractional radii
blended), `crisp` (edge contrast) 1.0 / 1.1 / 1.1, box down-sampling; fill coverage x1.000-1.019, strokes x0.997-1.003 over the
names; the outline value the mean of the base plate's outline core. Other fonts: `font_weight` (stroke / cap height of
"HAMBURGEFONSTIV": DFMincho-SU 0.116, DFGothic-SU 0.153) and `WEIGHT_GAIN` 1.8 take them to the same weight (eroded
when heavier). `media_test.py` checks the metrics with tolerances (TOL) and draws 1.2 / 1.3 / 1.4 / game, raw and as
coloured on screen (`in_game`: an approximation of the screen's colouring of the channel plates).

### Online: the 96-id sets (random_select.py)

`0x0301CAE8` (a bit per available database entry, 96 at most since 1.1) is now called only from `0x0290D960`
(`0x0290D708`, from the menus `0x02178E24`) and `0x029E6CE0` (`0x029E6CC4`): both copy its 12 bytes to `+0x30` of the
object `0x029E2B84` returns (`[0x102F711C] + 0x2E00`: the 0x029E.... module, the online session's, whose code names
`ChainMapperLinkInfo`, match / disconnection counters...: the fighters this console announces to its peers). No
reader of those 12 bytes was found statically next to the 44 calls of `0x029E2B84` (the record is copied / sent
whole). 1.4 sets no clone's bit there (hook `0x0301CB78`, the bit set, skipping ids 59 .. 59 + clones - 1): a vanilla
peer is never told of a fighter id it doesn't have, for every clone id (1.3 announced ids 59-95). Not seen online.

### Researched in 1.4, not built (what was traced; what each still needs)

- **Trophies.** `ui_figure_db.bin` parsed to 0xB0-byte entries at `[db+0xC]` (count `+8`, `0x030A5C2C`); entry `+0x8B`
  the character id: `get_figure_id_from_chara_id` (xtal, `0x030ED814`) -> `0x030A5788(db, id, type 0, -1)`, a linear
  search over a category range (`0x030A135C`), -1 when none (a clone has no trophy: -1). Texts: labels `MmenFigN_%s`,
  `MfigI_%s`, `MfigD_%s`, `MfigR_%s` (`0x030A18B8` / `0x030A1934`) in `ui/message/figure.msbt`; models
  `model/figure/%s/body/c00/`. Ownership: the box screen's `box_data_%d_figure_get_state_%d` (xtal); the save's own
  storage was not found: no accessor bounded by 743 / 716 in the save accessors (`0x02A4F000-0x02A58000`, whose bounds
  are 0x60 / 0x63 / 0x3F / 0x139 / 0x264 / 0x270F), so neither the size of the ownership area nor an unused id that is
  never read or written can be named. New trophy ids are therefore not made (writing an id past the save's area would
  corrupt the save); reusing vanilla ids needs the ownership area traced (a write breakpoint on the save when a trophy
  is won, in Cemu).
- **Palutena's Guidance.** `ui_smashappeal_angeland.bin` = 120 groups: 60 pairs {lines: per line {number, 60, flag,
  3 speakers x 6 portrait names `chr_14_<Name>_NN`, 15, 0}, sequences of 7 ints}. The texts are
  `MmelAppeal_Angeland_<a>_<b>_<line>` (`0x0267DE68`: a = `[obj+0xB8]` + 1, b = `[obj+0x10C]` + 1), the voices
  `snd_vc_smashappeal_Angeland_<JP|EU|US>_%02d.nus3bank` (`0x0267DC10`, region by `+0xAC` 0xC / 0xF / 0x27, the number
  `[obj+0xB4]`), the param loaded by `0x026865D4`. Which index the character id selects was not found (`+0xB8` comes
  from a resource lookup in `0x02686970`, `+0xB4` from `0x0267CF40` / `0x0267D32C` / `0x026815A4`): the voice banks
  and `ui/message` for these texts are not in the test data either. Not built.
- **Smash Tour.** `param/worldsmash/*` (stat / event / item params), `WorldSmashManager` states (`0x10048DD8`...), the
  fighter models `worldsmash/model/fighter1-3`, `worldsmash/ui/lumen/ws_select_fighter`; its fighter pool reads the
  character database through the same accessors (positional ids up to 0xC7). Not traced further; no data written.
- **amiibo.** `ui_nfp_db.bin` (66 x 5) maps a fighter id to an amiibo character number; the figure writes go through
  `nn::nfp::WriteApplicationArea` (`NfpViewComWriteFigureScene`, `menu_nfp_begin_write_chara`). What is written for a
  kind / id was not traced, so no clone row is added and no amiibo can be assigned (the tool never touches figure data).
- **Final Smash.** `0x030BF9C0` / `0x030C1FDC` map the transformed kinds 0x3A-0x3D to their bases (Bowser 0xF, Wario
  0x16, Lucario 0x1E, Little Mac 0x29) for the Final Smash holder's resources (`0x030C2238`: `kind * 9 + 4 / + 6`);
  their callers are `0x030BFA90`, `0x030C0618`, `0x030C07A8`, `0x030C0C34`, `0x030C127C`, `0x030C2020`, `0x030C20F4`,
  `0x030C2238` (two). No table maps a base to its transformed kind (searched as words and bytes): the base's native
  Final Smash code names the transformed kind itself, so a clone of Bowser presumably becomes the vanilla Giga Bowser
  (0x3A). Open question (not run in game): if the holder's kind (`+0x20`) is the transformed kind when `0x030C2238`
  releases, it releases the base's ids (0xF * 9 + n), not the clone's own; when it is the clone's kind, its own.
  Not changed. New transformed kinds (cloned from 0x3A-0x3D) and a mapping in the tool's space need the
  transform's spawn traced. Not built.
- **Mode emulation.** Done for the online sets above, the random pools (1.2) and the results call (1.3); the other
  modes' set-up code was not emulated.
- **Base and clone in one match.** Per-kind arrays are per kind (kind_expand sizes them); a clone runs its base's
  specializer, whose statics are shared exactly as between two players of the base (a vanilla ditto). The tool's own
  globals: `res_kind` (the Kirby loader's, set per helper call, the loader runs players one after another), KTAB (per
  Kirby, by int array). None found that changes behaviour; not seen in game.

## 1.5: the executable patch as data (Aroma plugin, Cemu graphic pack)

The patched rpx ("route 1") needs the creator's players to install a modified `cross_f.rpx`. 1.5 adds two outputs that
patch the game's own executable in memory instead (`Session(exe_output=...)`, `cli.py --exe-output rpx|aroma|cemu|all`,
the window's "Executable output"): an Aroma plugin with a per-project patch file, and a Cemu graphic pack. The patched
rpx itself is unchanged (the same generators, byte for byte; only the marker's `tool` field says 1.5).

### Files

```
sm4shclonetool/patchset.py   export (relocation classification, veneers), apply (the plugin's algorithm in Python),
                             the plugin file (plugin_bytes / read_plugin), Cemu (cemu_patches / cemu_rules / cemu_hash)
sm4shclonetool/ppcflow.py    PowerPC register reads / writes (decode) and a forward liveness check (dead_at)
aroma/                       the plugin: src/patch_core.c (parse / check / apply, no Wii U calls), src/main.c (WUPS
                             hooks, MCP, KernelCopyData, notifications), src/cave.S (the cave buffer in .text),
                             Makefile, README.md (install, the file format, what is confirmed), sm4shclonetool.wps
exe.generate(view, base, reg) the generators run at any base (exe.build = generate + the rpx writing, unchanged)
tests/patchset_test.py, tests/plugin_host.c   the checks below
```

### What the patched rpx changes beyond code words, and what the in-memory loaders do instead

| the patched rpx | why | Aroma plugin | Cemu graphic pack |
|---|---|---|---|
| `.text` grown from `0x04B77E1C` to the code space's end (at least `0x04BB8000`; the section's zlib size prefix and its compressed size) | room for the cave after the game's code | nothing can grow a loaded section: the cave goes into the plugin's own memory (a 1 MB + 64 KB block of its `.text`, `cave.S`), relocated | the cave goes into a Cemu code cave (Cemu allocates it, `codeCaveSize`), relocated |
| the RPL file info's `textSize` (+4) raised past `0x2BB8670` when the cave passes `0x04BB8670` (about 30+ fighters) | the loader maps the text region the file asks for | not needed (no part of the patch is in the game's region past its code); the limit is the plugin's buffer (`CAVE_KB`, 1024 KB: 40 fighters + 8 stages need 381 KB) | not needed; Cemu's cave area is 4 MB for every pack |
| relocations at patched words moved to a dummy word in the marker block (`r_offset`; 124 for run_all's registry: HA16 / LO16 against the game's own sections) | so the loader does not write the original back over a patched word | not needed: the plugin writes after the loader. Its "original" check reads the loaded words; every relocation at a patched word resolves to the file's own word (the main executable loads at its link addresses; checked for all 124: `R_PPC_ADDR16_HA` / `LO` against `.text` / `.data` / `.rodata` symbols, the result = the file's word), so the file's originals are the loaded ones | the same: Cemu applies graphic packs after the module is loaded and relocated |
| the marker block at `0x04B78000` (registry, originals, moved relocations, zlib JSON) | incremental, idempotent re-patching | the patch file carries the originals (and a JSON summary: tool version, clones, the source's SHA-1); nothing in memory | the originals are not needed (Cemu matches the module checksum) |
| the CRC section, recompressed sections, the file's layout (`rpx_compact`) | a valid RPX | file only | file only |
| the cave's run-time data (the random pools, KTAB / knext / res_kind, the new characters' records) in the code region | (Cemu does not protect code) | in the plugin's memory, which the game can write (assumed, see below) | in Cemu's code cave (writable in Cemu) |

No data section, `.bss` size or import changes: every game word the patch writes is in `.text` (`0x021E6E30`-`0x033EC060`
for run_all's registry).

**The patched rpx on a console** therefore has two problems the tests can't show (they run in unicorn, which maps
everything writable, as Cemu does): the cave's run-time data sits in the code region, which Cafe OS maps read-only for
the game (the first write, e.g. the random pick's pool, would fault); and, past about 30 fighters, the raised text
region. Neither was tried on a console. The plugin avoids both.

### Making the patch relocatable (`patchset.export`)

The generators (`kind_expand`, `weapon_expand`, `base_effects_cave`, `base_customs_cave`, `stage_slot_cave`,
`clone_extras`, `random_select`) all take their part's address from `exe.configure(base)`. `export` runs them at the
tool's base `L = 0x04B78000` and at `L + 0x10000`, `L + 0x2000` and `L + 0x20000` (4 generations, about 35 s), on the
input's vanilla view, and requires the same set of written addresses (game words by address, cave words by offset).
Every word that differs between the builds is classified by how it differs:

| kind | +0x10000 | +0x2000 | where |
|---|---|---|---|
| ADDR32 | +0x10000 | +0x2000 | cave data (251 words for run_all's registry); none in the game |
| HA16 / HI16 | +1 in the low half | +0 / +1 | `lis` / `addis` (67 in the cave, 67 in the game) |
| LO16 | 0 | +0x2000 in the low half | `addi` / `addic` / `ori` / a load's displacement (68 / 67) |
| REL24 game -> cave | the branch +0x10000 | +0x2000 | the hooks (39) |
| REL24 cave -> game | the branch -0x10000 | -0x2000 | calls / jumps back into the game (72) |

Anything else fails the export (a word that would need another kind of fix-up). Then the table is checked against the
generators: applied with delta +0x20000 it must give the `L + 0x20000` build word for word, and the full targets
(below) must give the `L + 0x2000` build; every unclassified word must be equal in all four builds. Data words that
look like branches (strings, hashes with opcode 18) are left alone because they don't change.

**Full targets** (for Cemu, which places the cave at any 256-aligned address): every HA16 is paired with the LO16
words that use its register before it is redefined (`ppcflow.decode`), giving the address it builds; a LO16 without a
high half here is known modulo 0x10000, all it needs. A high half shared by low halves in different 256-byte blocks
would break at some Cemu address; none occurs (checked, `multi`).

**Veneers.** From the plugin's memory (under `0x02000000`) or Cemu's (`0x01800000` up) the game's code past
`0x03800000` is out of a branch's reach, so every cave -> game branch is replaced by a branch to a veneer appended to
the cave: `lis rN, t@h / ori rN, rN, t@l / mtctr rN / bctr`. It clobbers rN and ctr, so `ppcflow.dead_at` proves both
dead at the target: every path from there (followed through branches, into the cave's own hooks, with calls ending
the volatile registers and returns ending r0 / r5-r12 / ctr) writes them before reading them, on the patched image.
For a call (`bl`), the registers a callee leaves undefined anyway (r0 / r11 / r12, ctr) must be dead after the call
in the cave. r12 is preferred, r11 next (`0x03127994`, the SETUP hook's return, and `0x02EA8D50` / `0x02EA8D54` read
r12). An address without a free register fails the export. The 41 veneers of run_all's registry (63 for 40 + 8
clones) all found one. `ppcflow.decode` was checked against capstone's operands on 46,000 of the game's instructions
(paired-single opcodes left out: capstone decodes them as VSX).

**Game -> cave branches** become absolute (`ba` / `bla`): the plugin's and Cemu's caves are below `0x02000000`, which
an absolute branch reaches from anywhere. HA16 hooks (`lis` / `addic` pairs, the jump tables' bases) move with the
cave.

### The plugin's placement and file

The plugin puts the cave at `base = L (mod 0x10000)` in its buffer: then delta is a multiple of 0x10000, LO16 words
don't change, ADDR32 += delta, HA16 += delta >> 16, REL24 hooks become absolute. The file (format 1, `aroma/README.md`)
holds the game words (address, original, new at `L`, kind), the cave relocations (offset | kind << 28), the cave as at
`L` with its veneers, the title ids (`0005000010144F00`, `0005000010145000`, `0005000010110E00`), the game version (288)
and a CRC-32. The tool writes one file under each title id's name (`INSTALL_TO_sd/wiiu/sm4shclonetool/`).

The plugin (`ON_APPLICATION_START`, Smash 4 only): reads the file, checks it and the update's version
(`MCP_GetTitleInfo(0005000E-...)`), checks every original word, computes every new word (a hook that can't reach the
cave stops it), zeroes and fills the cave, relocates it, flushes it (DC flush / IC invalidate), then writes the game's
words with `KernelCopyData` (physical addresses from `OSEffectiveToPhysical`; the game's code is read-only to
applications) and flushes each. Nothing of the game is written before every check passes.

Where the cave lives: the plugin's own `.text` (`cave.S`, zeros, 1 MB + 64 KB: the 64 KB to place it at `L` mod
0x10000). `.text` because that memory is certainly executable (the plugin's own code runs from it); it must also be
writable (the game writes the cave's run-time data) and below `0x02000000` (the absolute branches). Aroma loads WUMS
modules and plugins into its module area under `0x01000000` (as far as known), mapped readable / writable / executable;
the plugin checks the address at run time and refuses past `0x02000000`, but cannot test the permissions without
risking a fault. If the plugin's `.text` turns out not to be writable from the game, the cave's data part has to move
to a writable block (the relocation table already tells data from code: ADDR32 / HA16 targets; not built).

### Cemu (`cemu_patches`, `cemu_rules`)

`patches.txt` in the Cemuhook format, which Cemu's `ParseCemuhookPatchesTxtInternal` reads (Cemu prefers `patch_*.asm`
files when a pack has any; this pack has none): one group `[Sm4shCloneTool_v288]`, `moduleMatches`, `codeCaveSize`
(informational: Cemu takes the cave's size from its highest cave-relative address), `_cave = 0x00000000`, then one
`0xADDR = .int EXPR` line per word: cave words at their cave-relative offsets (an address up to 8 MB is relative to the
cave in Cemu's `_relocateAddress`), game words at their addresses (inside the module's sections). Expressions use only
`+`, numbers, `_cave` and the functions `ha()` / `lo()` (Cemu's `ExpressionParser` with the patch resolver's function
callback; not the `@ha` suffixes, whose meaning changed in Cemu 2.7). Every word a generator wrote is written (zeros
too: Cemu's cave memory may hold an earlier session's data), padding is not. `rules.txt`: `[Definition]`, the three
title ids, `path = "Super Smash Bros. for Wii U/Mods/Sm4shCloneTool_Clones"`, version 6.

`moduleMatches` is Cemu's module checksum (`RPLModule::patchCRC`, `RPLLoader_BeginCemuhookCRC` in Cemu's rpl.cpp):
CRC-32 over `\x7FRPX`, the section count and the symtab / strtab / shstrtab indices (little-endian ints), then per
section its name offset, type, flags, address, decompressed size and alignment (little-endian words) and its
decompressed data. For the v288 file as Nintendo ships it: `0x63FAA900` (`patchset.V288_CEMU_HASH`); a vanilla input
with another checksum (e.g. a decompressed copy) is listed too.

Cemu's format can express everything the patch needs: words at fixed module addresses, a relocated cave, symbolic
32-bit values and high / low halves of cave addresses. What it can't do is grow the module's sections or keep the cave
at `0x04B78000` (a fixed address outside the module's sections is refused), hence the relocation.

### Tests (`tests/patchset_test.py`, in run_all; `many_clones_test.py`)

- the patch set from the vanilla rpx = the one from the patched rpx (its vanilla view); its game words = the marker's;
- applied at `L` without veneers: the patched rpx's memory image byte for byte (every section, but the marker block);
  the same for 40 fighters + 8 stages (`many_clones_test.py`);
- the plugin file reads back; a damaged one is refused; its cave with the veneered branches made direct = the rpx's;
  every veneer is lis / ori / mtctr / bctr to its target;
- relocated as the plugin places it (`0x00908000`) and as Cemu would (`0x01800100`, evaluated from patches.txt): every
  hook branch absolute to the same offset, and `extras_test.py` (37 checks) and `random_select_test.py` (14) run on the
  relocated image through an overlay (`X.find_marker` / `Rpx` monkeypatched; the extras labels shifted), plus the
  custom-move map `0x02A4D40C` for ids 0-63, all as on the patched rpx;
- the plugin's `patch_core.c` compiled for the PC (`plugin_host.c`, `-Wall -Wextra -Werror`): the same game words (in
  order) and cave bytes as `patchset.apply` for two buffers; it refuses a changed word (rc 6), a damaged file (1),
  another title (3), update v272 (4), a buffer past `0x02000000` (5), writing nothing;
- patches.txt / rules.txt through a strict parser written from Cemu's (`cemu_parse`: groups, `moduleMatches`, symbol
  lines relocated as Cemu does, `.int` with one expression, cave-relative or in-section addresses, no word written
  twice); evaluated at `0x00908000` it equals the plugin's image;
- `ppcflow.decode` against capstone (above).
- run_all: a build with `--exe-output all` (the rpx = build 3's image, three identical patch files that read back, the
  plugin, the Cemu files, the README's three install paths), then `aroma` only (the other outputs removed).

Not covered: the research tests (`kind_expand_test`, `weapon_expand_test`, `base_effects_test`, `stage_slot_test`) on
a relocated image (they read the patched rpx's file; their parts are relocated by the same checked table), and of
course the console and Cemu themselves.

## 2.0: the importer, article cloning

The importer adds animations (motion kinds), effects, sounds and articles to a fighter, vanilla or a clone; article
cloning is the article part with any owner. Everything is data in the package plus (motions, articles) the executable
patch, through the same generate / patchset path as the clones (rpx, Aroma, Cemu). The registry gets
`imports = {motions: {fighter: [..]}, effects: {fighter: [..]}, sounds: {fighter: [..]}, articles: [..]}` (in the
project and the marker): a rebuild finds every item by name (same motion number, effect id, sound id, article id) and
`exe.generate` makes the tables from it. Without imports the layout and every generator's output are 1.5's.

### Files

```
sm4shclonetool/importer.py   Target (a vanilla fighter or a clone: folder, Cap name, kind), import_motions, copy_set /
                             import_effects, import_sounds (Sm4shCommand's SoundAdder ported: _template, make_entry,
                             bank_build), write_names (Sm4shCommand_names.txt sections), write_aliases, plan / preview /
                             run (the session's entry points)
sm4shclonetool/pac.py        KCAP packs: read / build (the game's packs byte for byte), anim_hash
sm4shclonetool/motion_exe.py the grown motion tables (part "imports")
sm4shclonetool/articles.py   the article records -> weapon_expand spec entries, the files, the vl load / unload hooks
                             (part "article_hooks")
vendor/ptcl.py, vendor/efc.py  (make_vendor.py) the research's ptcl / efc readers and writers
tools/weapon_expand.py       (and its vendored copy) two generic options: a brand-new article's "base" as
                             "<fighter>/<article>" (another fighter's), and the spec's "owners" (vanilla fighters with
                             brand-new articles); without them its output is unchanged
tests/import_test.py, import_exe_test.py, sm4shcommand_test.cs   (below)
```

### Motions: what bounds a motion number (traced on v288)

- Per kind a static descriptor (switch `0x02E43148`, getter `0x02E4313C`) `+4` -> motion info `{main table, count,
  part list, part count, ...}` (Fox `0x1037083C`: 0x2A9 motions, 5 parts; Zero Suit Samus `0x103FDFA4`: 0x25F, 6). The
  main table: `{animation hash, flags}` a motion (hash = `zlib.crc32(.omo name, 0xFFFFFFFF)`, the pack loader's key);
  a part table: a hash a motion (3 rhand, 4 lhand, 5 face, 6 `<name>pt1`, 7 `<name>sw1` / `pt2`; 0 = none).
- **The count is read twice**: `0x02EA9008` (from `0x02EA9064`, the run-time table getter, called once per kind from
  `0x02E12C74` at fighter creation) stores the table at descriptor `+0x1C` and copies vl group 1 (6 bytes a motion:
  byte 1 -> the entry's byte `+4`, byte 0 -> flag `0x80` in `+6`) into the table **in place** for `count` motions; and
  `0x0275BAB0` (the AI's attack_data check, `0x02DFC8C4`) returns it. Those are the only readers of descriptor `+4`
  among the getter's 16 callers.
- **Nothing bounds the number where it is used**: the 28 MotionModule accesses in `0x02C5B000-0x02C66000` read
  `[module + 0x1C] + 8 x motion` and check only `motion == -1` (then a static default entry `0x1049314C`); the script
  lookup `0x02E42518` reads `motion.mtable[motion]` unbounded; MSC / ACMD pass any int. The AI's attack index
  (`0x02DFC8CC`) has 0x611 slots. So a fighter can't play a new motion without the executable: a number past the count
  reads the `.data` after its table (Fox's main table is followed by his first part table). With no executable change
  the only option is to replace an existing motion's animation (its `.omo` under the same name) or its scripts.
- **The patch** (`motion_exe.build`): per fighter with imported motions, in part "imports" (after "extras", sized
  from the registry: 0 without imports): the main table copied (the game's entries; for a clone the base's, as
  kind_expand copies them) plus one entry per motion `{hash, flags}` (flags: the copied motion's static low 24 bits
  without 0x80, else 0: the high byte and 0x80 come from vl group 1 at run time), the part list and each part table
  copied and extended (the imported part's hash or 0), and the motion info's `+0` / `+4` / `+8` changed: in place for a
  vanilla fighter (`.data`; its ADDR32 relocations at `+0` / `+8` moved to dead `.data` words: the old main table's
  first hash and the old part list's first part id, which nothing reads once the motion info moves; an ADDR32 of
  `.rela.data` can't name a word of `.text` like the code-space dummy, the same rule weapon_expand's Kirby header
  follows), in kind_expand's own motion info copy for a clone (`exe.generate`'s `add(..., override=...)`: those three
  words only). The tables are written at run time (`0x02EA9008`, in place): the cave must be writable (as for the
  clones' own tables). In the patchset these are ADDR32 game sites (the plugin and Cemu handle them as the cave's).
- **The files** (`import_motions`): the `.omo` into `main.pac` (sorted by name as the game's packs; `pac.Pac`
  rebuilds the game's 26 packs of the test data byte for byte), part animations into their packs (`<prefix><Tag><code>
  <Name>.omo`, the tag read from the pack's own names), `motion.mtable` + the four scripts (empty or a deep copy of a
  motion's), vl group 1 grown (the vl file's first vector, `0x20` + count + 6 x `{type, byte}` a motion: the rest of the
  file untouched); `index = count + i`, checked against `motion.mtable` on a rebuild.

### Effects

`copy_set` (not ptcl.py's `import_set`, which drops key animations and leaves a child's shaders / textures pointing
into the source file): every emitter with all its shader slots (`Ptcl.shader_slots`: its own and its child's, each
source shader imported once), its shader-parameter range, its key animations (`key_anims` -> `set_key_anims`), its
texture slots and its child's (`CHILD_TEXRES`; each source texture copied once, at its format's alignment), its
primitive mesh; then `new_set`. The `.efc` entry copies the source's flags, model (its folder `model/<name>/` copied
when the target has none) and mesh-switch records. Id = `3 << 24 | kind << 16 | entry`. `Ptcl.validate()` must pass
before writing. A rebuild finds an item by (source file, entry).

### Sounds

`import_sounds` ports SoundAdder.cs: row = the bank's BINF id's soundlabeltable row (none: refused); labels =
row count + k, tone index = the largest tone count of the bank and its costume banks on the row (`snd_<se|vc>_<Cap>
[_common|_ouen]_cNN`) + k, padded with the bank's 12-byte stub; the TONE entry from `_template` (IDSP one-shots, the
tail's loop flag 0; `_Special_L01` first; stereo for stereo) through `make_entry` (MakeEntry: head, name, the 4 bytes
before the block, PACK offset / size, volume, the tail); PACK appended at 0x10; `bank_build` sizes JUNK as
Nus3Bank.Build(alignPack). Audio: `audio.read_wav` (resampled to 48 kHz), trimmed at -45 dBFS, peak -0.5 dBFS,
`audio.idsp_encode` (vendor/dspadpcm.py); an IDSP file as it is. A rebuild re-uses a tone (by bank and name) and leaves
it untouched when its audio, volume and loop flag are the same. Aliases: Sm4shCommand's `Aliases/sounds/<fighter>.txt`
(its WriteFile header, `0x%08X = name`), merged.

### Articles: weapon kinds and their limits (vanilla v288)

- **Weapon kinds**: 0x185 (389, `0x000`-`0x184`): four 389-pointer name tables (root `0x104189DC`, owner `0x10418FF0`,
  name `0x10419604`, folder `0x10419C18`, contiguous, so they move), three static tables (u32 `0x1018A1D4`, u8
  `0x1018A7E8`, u16 flags `0x1018A970`), the u32 / u8 accessors' bound `0x0320E5AC` (`addic r0, r4, -0x185`), 13
  switches `cmplwi k, 0x184` (descriptor getter `0x0320D934`, singleton getter `0x03210C30`, 11 weapon methods), the
  module rows (`0x103464A8`, 0x70 a row, 389 rows, read unbounded at `0x02BCB5C0`). weapon_expand moves / bounds all of
  them to its capacity (`max(0x1C0, 0x185 + every own / imported article, rounded to 0x10)`, at most 0x7FFF).
- **A fighter's article list** (its descriptor `+8` -> `{entries, count}`, 16 bytes an entry `{kind | bit 31 special,
  max count, spawner callback, extra}`): the article id is the position. The ArticleModule (`0x02C02614`) counts the
  entries before the first special one into its holder's `+0x110` and stores one pointer per instance (their max
  counts) from `+0x10` with no bound: **64 instances a fighter** (more overwrite `+0x110` / `+0x114`: a crash at the next
  lookup by id, native-notes "Article instance cap"). The game's lists: at most 34 entries (Kirby), 28 instances
  (Villager); Fox 5 entries / 10 instances, Zero Suit Samus 6 / 7. The tool refuses an import past 64.
- **An imported article** = a brand-new article of weapon_expand (`{"kind", "base", "max"}`): a copy of the source kind
  (descriptor copy: its motion info with the source's entries, `+0x14` sub-articles, `+0x1C`; every switch sends it to
  the source kind's case; its module row is the source's), its own name / folder strings, owner = the owner fighter,
  its list entry = the source's entry (spawner) with its own max. Numbered after every clone's own articles in registry
  order (`articles.spec_entries`): a kind may change when a clone with articles is added later; the article id does not
  (ids are positions, the imported ones after the owner's normal entries in registry order).
  - Owner a clone: in its record's `weapons` (weapon_expand builds its list, kind_expand points its descriptor copy at
    it). Source = an article of the clone's base: the param getters (`+0x18` / `+0x24`) are copied to read the clone's
    own vl slot (kind_expand's array): own params. Source of another fighter: `"base": "<fighter>/<article>"`; its getters
    are not copied (they read that fighter's slot).
  - Owner a vanilla fighter: the spec's `owners` (weapon_expand: a record of the fighter's own kind, `vanilla_owner`);
    its list copied to the cave with the new entries and its descriptor `+8` (`.data`) pointed at it, the ADDR32
    relocation moved to the old list's count; its getters are the source's (the owner's own vl when it is the source).
  - **The vl hooks** (`articles.build_exe`, part "article_hooks", only for an article of another fighter): the first
    word of `fighter_param_vl` load `0x02EA6BC4` (`stwu r1, -0x90(r1)`, only caller `0x02E11C8C`, fighter creation) and
    unload `0x02EA5D64` (`stwu r1, -0x28(r1)`, callers `0x02E1482C`, `0x02EA6B98`) become branches to wrappers that look
    the kind up in a `{owner kind, source kind}` table: load runs the function body (the replayed `stwu`, then the
    function from its second word) for each source, then for the owner (its return value returned); unload for the owner
    first (its value kept), then the sources. The game's reference count (`mgr + 0x1220`) keeps each file loaded once.
    kind_expand's clone load case calls `vl_load(mgr, base)` through the same entry, so a clone owner works the same.
- **The files** (`import_articles`): `model/`, `motion/`, `script/animcmd/weapon/`, `script/msc/` folders of the source
  (each from the package if it has it, else the data folder) copied under the new name (`<name>.mscsb` renamed); the
  scripts' effect ids moved: same bank -> nothing; the owner's bank a copy of the source's (a clone of it with its own
  effects) -> KK only; else `import_effects` of the referenced entries and their new ids. Sound ids: rows the same ->
  nothing; the owner's bank of that kind on rows with the same labels (a clone's copy) -> the row; else the tones
  (`bank.data_of`) copied into the owner's se bank with `import_sounds` (`<tone>_<Cap>_<article>`) and the new ids. An
  owner without an se bank in your files keeps the source's sound ids (logged).
- Sub-articles: an article that makes another (a weapon descriptor's `+0x14` list) keeps the source's kinds for those.
  In the vanilla lists, a fighter's projectiles are their own list entries made by the fighter's code (Zero Suit
  Samus's paralyzer and paralyzer_bullet are articles 0 and 1; no weapon of hers has a `+0x14` list), so copy each one
  you need.

### Sm4shCommand

How it opens a fighter (read for this): File > Open fighter = a folder, normally `fighter/<name>/script/animcmd/body`:
every `.bin` in it is an ACMD file (SALT `ACMDFile`) and `motion.mtable` beside them (SALT `MTable`), one tree node per
mtable entry then the unlisted scripts (`MainForm.OpenFighter` / `PopulateFighterScripts`); names from `ModAnimNames.txt`
then `AnimNames.txt` next to the exe (`Runtime.LoadAnimNameFile`: a name a line, `0xHASH = label`, `Name ->
folder/File.omo [+ held@Bone]`); the Hitbox Viewer (`FighterAssets.Load`) finds the fighter folder above the scripts,
`model/body/c00` and `motion/body/*.pac`, and maps a script to an animation by the file name's tail after
`[A-Z]NN` (and by the names files' viewer lines); the Sound Effect Viewer (`FighterSounds.Load`) lists the fighter's
banks through `sound/config/soundlabeltable.bin` above it; the effect library (`EffectLibrary`) reads
`effect/<folder>/<folder>.010d0000.efc / .ptcl` (a bank number past its kind list falls back to the fighter's own
folder, as for a clone). The importer's names: the tail of an imported animation's file name is its script name, so the
viewer plays it even without the names file.

### Tests

- `import_exe_test.py PATCHED VANILLA [WORK]` (unicorn, the game's own functions; with WORK also on the patch set applied
  at the Aroma plugin's base and evaluated from the Cemu patches.txt at a Cemu cave base): `0x02EA9064` builds the grown
  table (the old motions as the unpatched game gives them with the same vl group 1, the new ones' hashes / flags / vl
  bytes; only the table, `+0x1C` and the stack written), every other vanilla kind the game's table, `0x0275BAB0`'s count,
  the part tables; each owner's article list (the game's with the new entries at their ids and the source's spawners),
  the weapon descriptor getter (a copy of the source's; game kinds unchanged), the file-name lists `0x030BC8E4` (its own
  name / folder; game kinds unchanged), the vl hooks (the body run for the source(s) and the owner in order, once each,
  the return value, the stack and r14-r31 kept; other kinds only their own).
- `import_test.py WORK PROJECT DATA PATCHED VANILLA [SM4SHCOMMAND_RUN]` (run_all runs it on its project after the other
  checks): a fourth build with 12 imports (motions into vanilla Zero Suit Samus with a hand part animation and into
  zssclone, effects into vanilla Fox and foxclone, a mono WAV, a stereo WAV and an IDSP, articles for vanilla Fox (another
  fighter's: the vl hooks, its effects imported), zssclone (its base's) and vanilla Zero Suit Samus (her own)); the plan
  and its refusals; every round trip and old entry; the new data against the inputs (the .omo bytes, the copied scripts,
  key animations / textures / shaders / names, the decoded audio > 25 dB SNR, the IDSP as given); ids unique; nothing
  else in the package changed; a rebuild changes no byte; the executable valid, `import_exe_test` (patched rpx, Aroma,
  Cemu) and `weapon_expand_test` (repo_test); Sm4shCommand's loaders (`sm4shcommand_test.cs`, compiled against its built
  `SM4SHCommand.exe` / `SALT.dll` with the .NET SDK's csc, run with mono under xvfb-run because its Runtime makes the
  main window) on an installed view (data + package) of each fighter: SALT opens the four files (every script: the
  tool's count) and motion.mtable; each imported motion's mtable entry, scripts, its label and viewer line
  from the names file through `Runtime.LoadAnimNameFile`, the animation `FighterAssets` plays for it and its OMO;
  each imported sound in the Sound Effect Viewer's list by its id, decoded (`Idsp.Decode`) with its samples / channels;
  the aliases file; each imported effect through `EffectLibrary.AssetsFor` (its set name and emitter count). run_all
  finds a built Sm4shCommand in `$SM4SHCOMMAND_RUN` or `WORK/../../sm/run`; without one that part is reported skipped.
- `gui_test.py`: the import tab (a fighter's effect bank listed, the imported items shown).

Not covered: the game itself (nothing here ran in Cemu or on a console), a cross-fighter article's native behaviour for
its new owner, the effect memory of a match with imported effects, imported sounds through the game's sound engine.
