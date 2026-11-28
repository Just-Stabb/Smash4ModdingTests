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
    _paths.py                    imports: ./vendor (the standalone package) else tools/ (this repository)
    rpx.py                       an RPX in memory: words by address, resize .text, relocations, save (rpx_patch / rpx_compact)
    exe.py                       detection, the marker, the vanilla view, running the generators, the patch
    roster.py                    fighters / stages from the databases, the CSS order, the project file
    fighter.py                   a fighter clone's data (add_fighter.py's functions), customs, sound config
    stage.py                     a stage clone's data (add_stage.py's helpers)
    textures.py                  .nut decode (nut.py), PNG -> portrait in a set's format, new NTWU icons
    preview.py                   CSS (chara.lm via chara_layout.py, or a grid) and SSS previews
    session.py                   folders, registry, plan (Check), build (the package), post-build checks
  tests/                         repository-only: fixtures, the vanilla stand-in, run_all.py, repo_test.py
  make_package.py                the standalone zip (vendor/ = the tools/ modules below, unchanged)
```

Vendored (copied unchanged by `make_package.py`): `rpx_patch`, `rpx_compact`, `ppcasm`, `kind_expand` (+
`kind_expand_ram.json`), `weapon_expand`, `base_effects_cave`, `base_customs_cave`, `stage_slot_cave`, `s4param`,
`msbt`, `add_fighter`, `add_stage`, `add_fighter_customs`, `fighter_extras`, `fighter_param`, `acmd` (+ `acmd_info.json`
with only the game's commands: `acmd_ext_cave.NEW_CMDS` filtered out), `nut`, `chara_layout`. Dependencies: Python 3,
numpy (nut.py), Pillow, Tkinter.

## The executable

### Code space

The game's `.text` ends at `0x04B77E1C`; its text region (RPL file info `textRegionSize` 0x2BB8670) reaches
`0x04BB8670`. The tool takes `0x04B78000`-`0x04BB8000` (`exe.PARTS`, offsets from the base):

| part | offset | generator (module globals set by `exe.configure(base)`) |
|---|---|---|
| marker | 0x0000-0x4000 | the registry and the originals; its last 8 bytes = the relocation dummy (`DUMMY_OFF`) |
| stage | 0x4000-0x5000 | `stage_slot_cave` `CAVE` / `LIMIT` / `RELOC_DUMMY` |
| customs | 0x5000-0x6000 | `base_customs_cave` |
| effects | 0x6000-0x8000 | `base_effects_cave` |
| kinds | 0x8000-0x30000 | `kind_expand` `CAVE` / `LIMIT` / `RELOC_DUMMY` |
| weapons | 0x30000-0x40000 | `weapon_expand` |

Moved relocations go to the tool's own dummy word (in the marker block), not to a game function. The research's
dummy `0x037EE73C` is not used.

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

Per new kind (kind_expand's cave, ~6 KB a kind with a 600-motion table), the 160 KB kinds part holds the 15 kinds the
random select allows (`RANDOM_SELECT` 0x51 + new ids <= 96).

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

`weapon_expand_test` has one Mario-specific expectation (weapon 0x185 = the fireball's module row); with Fox's
blaster as 0x185 it fails by design and `run_all.py` reads it as such. `base_customs_test` is written for this
repository's own mapping and isn't run; `run_all.py`'s customs check replaces it.

## Not done / open

- In-game confirmation (nothing here ran in Cemu or on a console).
- Own sound banks (soundlabeltable rows), the announcer call, Kirby's copy: not offered (vanilla Kirby refuses new
  kinds).
- The game's character-select layout file is not read without a `chara.lm` in the UI folder; ties between equal sort
  keys are assumed to keep id order.
- Rewriting a custom `chara.lm` for a new count (only detected and reported).
