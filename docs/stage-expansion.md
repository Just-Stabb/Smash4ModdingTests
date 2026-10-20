# Adding a new stage slot (research)

Status: **works in game (v6, user)**: the new stage (a Battlefield copy, `NewStage01`, cosmetic `0x38`, kinds `0x80` / `0x81`) is on the stage select's page 2 with its name and icon, and loads. Open: the user's modded layout's page 1 since the stage was added (see "v2 result and v3").
`NewStage01`, not tested in game yet. Addresses are this repo's `cross_f.rpx` (the version
the other caves target). Several of them were first found by **Manifold** (Fitz Null, zlib
licence, https://gitlab.com/fitz.lol/manifold, `src/cross/stage.cpp` / `stage.hpp` / `ui.hpp`), a
runtime patching framework (Aroma / WUMS function patcher) that loaded a custom stage, `XMadein`.
Every address below was checked against this RPX; the plan uses static RPX patches and code
caves, as the rest of this repo does, so it also works on Cemu.

## Two numbers per stage

- **Stage kind** (`STAGE_KIND`): which stage files and which `Stage*` class to load. 128 vanilla
  kinds, `0x00`-`0x7F`: one per stage for normal play ("melee", `stage/melee/<Name>`) and another
  for Omega ("end", `stage/end/<Name>`), the Smash Run / Home-Run / other modes, the DLC pairs
  (`0x6E`-`0x7F`).
- **Cosmetic id**: the stage-select / UI id, the index into `ui_stage_db.bin`. `0x00` random,
  `0x01`-`0x37` the stages (DLC `0x30`-`0x37`), `0xC8`+ menu / mode backgrounds (`MenuMusic`,
  `Homerun_f`, `sh_all`, `page`, ...). A new stage takes the next free id, `0x38`.

## Stage kinds: one table, four small functions

| what | address | vanilla |
|---|---|---|
| table `{const char *name; u32 variant}` x 128 (variant 0 melee, 1 end, 3/4 other) | `0x1011D95C` | `BattleField_f`/0 ... `Umbra_f`/1 |
| count | `0x02D1FE24` | `li r3, 0x80; blr` |
| name of a kind (`""` past the end) | `0x02D1FD7C` | `cmplwi r3, 0x80` + table read |
| path of a kind (`stage/melee/%s`, `stage/end/%s`, `stage/other/%s`) | `0x02D1FDA0` | table read |
| variant of a kind | `0x02D1FE10` | table read |

Those three are the only code that reads the table (every `lis/addi` of `0x1011D95C` in
`.text` checked), so the table can move to a code cave with room for more entries: point the
three functions at the copy and make the count `0x80 + n`.

Other limits on kinds:

- `0x03014720`: `cmplwi r31, 0x80; blt; li r25, 1; li r31, 0`. The function that starts a match on
  a kind turns a kind `>= 0x80` into kind 0 (Battlefield). Manifold nops these four instructions.
- The stage factory, `app::StageManager` `0x03163B3C`: a jump table over the vanilla kinds
  (`cmplwi r12, 0x7F; bgt 0x031647CC`) builds each stage's own class (its gimmicks). **Kinds past
  `0x7F` fall through to the generic stage**: `StageBaseEnd` (0x11B0 bytes, `0x0264C88C`) for
  variant 1, else `StageBaseCafe` (0x1140 bytes, `0x02D1A660`). So a new stage with no scripted
  gimmicks (platforms, collision, blast zones and camera come from its files) needs no factory
  change. A stage with gimmicks needs its own class, as Manifold's `StageXMadein` (a ladder, a
  spring and a breakable pillar on `StageBaseCafe`).
- Name -> kind lookups (`struct_03157edc` `0x031580EC`) loop over the count, so they follow it.

## The stage-select screen is built from `ui_stage_db.bin`

`data/param/ui/ui_stage_db.bin` (the string is at `0x101564CD`), loaded into a database of
`0x54`-byte entries indexed by cosmetic id (ids `>= 0xC8` are searched for instead). Manifold's
layout (`StageParamEntry`): `+0x00` cosmetic id, `+0x04` shown on the stage select, `+0x08`
series, `+0x0C` (DLC page), `+0x10` stage kind, `+0x14` alternate kind, `+0x18` Omega kind,
`+0x1C` alternate Omega kind, `+0x24` / `+0x28` max fighters (normal / Omega), ...

The icons are not fixed in the layout: `0x0298FAC8` loops over every database entry, keeps the
ones that are available (`0x0301BA8C` -> the database's own checks, `0x0293FD40`: usable, DLC,
unlocked in the save), puts them in one of two lists (page 1, or page 2 when byte `+0x0C` is set,
as the DLC stages), and sorts each by a key from the entry (`0x030A92CC`). `0x0298D068` then fills
the layout's slots `img_01`..`img_48` of each page (`lumen/stage/stage.lm`, 48 per page) from those
lists, with the icon textures by name (`stage_img_rep_%02d` / `stage_img_l_rep_%02d` and the
`stage_10_<Name>.nut` family). Page 2 has the DLC stages and plenty of room, so **a new database
entry should show up as a new icon without editing the layout**.

Names: cosmetic id -> name, `0x0293DCE0`: a 79-entry `{id, name}` table at `0x1033C100`
(`0x4F` in the function). Extend it the same way (cave copy + count) so id `0x38` gets a name,
which picks its icons (`replace/stage/stage_10/stage_10_<Name>.nut`, `stage_11`, `stage_12`,
`stage_30`, `stagen_10`, `stagel_10`) and its text (`message/melee.msbt` labels
`MmelStageN_<Name>` (name) and `MmelStageG_<Name>` (series)).

## Built

- `tools/stage_slot_cave.py [NAME[:COSMETIC] ...]`: the RPX side (default `NewStage01:0x38`, kinds
  `0x80` / `0x81`). Added at the end of the standard RPX command: `$(python3
  tools/stage_slot_cave.py)`. `tools/stage_slot_test.py PATCHED.rpx ORIGINAL.rpx` runs the patched
  functions in unicorn: count 130, the new kinds' names / variants / paths (`stage/melee/NewStage01`,
  `stage/end/NewStage01`), cosmetic `0x38` -> `NewStage01`, every game kind and cosmetic name
  unchanged.
- `tools/add_stage.py`: the files, copied from an existing stage (`--from BattleField_f`): the
  `ui_stage_db.bin` entry (position / id `0x38`, kinds `0x80` / `0x81`, order 56, page 1 by
  default: page 1 has 48 slots and 47 stages), the `ui_sound_db.bin` song list (the source's),
  `MmelStageN_` / `MmelStageG_` texts in `melee.msbt`, the six icon sets, `stage/melee` and
  `stage/end` folders (file names renamed). `tools/s4param.py` / `tools/msbt.py` read and write the
  param / MSBT files (byte-identical round trips).
- `rpx_patch.py`: several `grow:` arguments (one per cave script) now grow the section once, to the
  largest (it used to keep the first, smaller copy for the patches).

The generic stage loads the folder's files by pattern (`*/param/*_stprm`, `*.lvd` / `*%02u.lvd`,
`*/sound/sound.nus3bank`), so renamed copies load. Battlefield's own class (day / night, `_stdat`)
isn't used: the copy is a generic stage, so its background may not animate as Battlefield's does.

## v2 result and v3 (page 2)

**v2 (user): no new stage** on the select screen, with the user's modded stage layout and stages. The
layout picks page 1's arrangement by stage count: `num_%02d`, or `type2_num_%02d` when there are two
pages (`0x0298D068`; Random is the separate `img_99`). The user's modded `lumen/stage/stage.lm`
renames `type2_num_44`-`type2_num_48` to `type2_num_74`-`78` and moves the icons, so its page 1 has
room for the 47 stages it already has and the 48th (the new one, sorted last) has no slot.

The game's availability checks (`0x0293FD40` through the stage database wrapper, vtable
`0x100BAAFC`) pass for `0x38`: it's in `ui_stage_db.bin` and shown (`0x030A8DD0`), it has a
`ui_sound_db.bin` entry with songs (`0x02948808`), and it isn't in the unlock list (`0x030A9230`).

**v3 (`build/new_stage_test_v3.zip`): the stage on page 2**, with the DLC stages (their arrangement
`type2_num_09` is in the modded layout). Page 2 is byte `+0x0C`, which also marks a stage as DLC:
- unlock (`0x030A9230`): a DLC id's save unlock bit index is `id - 0x30 + 9`; `0x38` would read
  index 17, which belongs to no stage;
- DLC content (`0x030A8D78`, in the availability check `0x026F2ED0`): a DLC id with byte `+0x0E`
  clear must be in the DLC content list.

`stage_slot_cave.py` now treats only `0x30`-`0x37` as DLC in both (other ids: the normal unlock
list, no DLC content); `stage_slot_test.py` checks the content one in unicorn. Database:
`add_stage.py --page 2`.

**v3 result (user): still not shown.** `tools/stage_select_debug_cave.py` (records the stage
select's availability checks per id in the grown code space, `0x04B7E000`, read in Cemu's memory
view) showed, with the v3 files: 79 database entries, the new stage at 0x38, and its "exists",
page-2 and unlock checks passing, yet not available. The one check left: a page-2 (DLC-marked)
stage also needs a DLC content record at its index (`0x030A8E58`, the database's `+0x38` list,
12 bytes a stage; only the DLC stages have one). **v4** (`build/new_stage_test_v4.zip`, the v3
files + an RPX with the debug recorder): ids `0x38`-`0xC7` pass it too.

**v4 result (user): the stage is on the select, with no name or icon; selecting it, everyone
falls in a black void.** Debug v5 (name list, `0x0293DCE0` called in game): the lookup returned
nothing for 0x38 although it returns "NewStage01" in unicorn. Cause: **relocations**. The patched
table pointers (`lis` / `addi` / `lwz` at `0x02D1FD90`/`94`, `0x02D1FDA0`/`A8`, `0x02D1FE10`/`18`,
`0x0293DCE4`/`EC`) carry ADDR16_HA / LO relocations to the game's tables, and the loader applies
them after the file is loaded, putting the old table addresses back (unicorn doesn't apply
relocations): the new kind read past the old kind table (no folder name: the void) and the new
cosmetic id wasn't in the old name table (no name list entry: no name, no icon, and the DLC
content check failed). `stage_slot_cave.py` now moves those relocations to a dead word
(`reloc:`, starcopy_cave.py's `0x037EE73C`), `stage_slot_test.py` checks the built RPX has none
left there, and `rpx_patch.py` keeps every `reloc:` argument's moves (each used to start again from
the file's data, so only the first one, starcopy's, was kept). The same check found
`position_vars_cave.py`'s five WorkModule div_float hooks over `lis` instructions with relocations
(the loader would have broken those branches): moved too. **v6**: `build/new_stage_test_v6.zip`. **v6 result (user): the stage loads, with its name and icon.** (`build/new_stage_v6_release.zip`: the same RPX without the debug recorder.)
But its stage-select grid icon was blank: the copied icons kept Battlefield's texture IDs (GIDX in
the .nut; each stage's `stage_10_*` icon has its own). `add_stage.py` now gives copied icons unused
IDs from `0x2800FF00` (`build/new_stage_icons_v7.zip`). Ω form shows a mix of the game's and the
pack's Battlefield (the copy came from the unmodified stage folders); fine, the user is replacing
the stage.

 with a different entry at 0x38: the stage select had
been opened with another setup installed; the user's pack itself has the 78-entry database.)

## The user's page 1 (solved: unlocked stages)

The user's page 1 showed one icon from the first build of their pack on. Bisect RPXs (none of the stage
patches, then the RPX from before the stage work) and the user's original databases didn't
bring it back, and the rebuilt packages check out (`ui/replace/stage`, `ui/lumen/stage`, `param`,
`ui/message`: every resource-table entry matches its package's data). Cause: the layout (4xM-based
`stage.lm`) has two-page arrangements `type2_num_01`-`43` only (44-48 renamed `type2_num_74`-`78`);
`unlock_condition_of_stages.bin` makes 6 stages unlockable (0x0A, 0x16, 0x1E, 0x27, 0x2A, 0x2C). With
them locked page 1 has 41 stages; the save had them all unlocked by then (debug v1: all "unlocked"),
47, no arrangement. Fix: the layout with the five labels renamed back (`build/stage_lm_fix.zip`, 5
bytes changed).



1. RPX caves (a `stage_slot_cave.py` like the others): a bigger stage-kind table (vanilla 128 +
   new melee / end pairs) and cosmetic-name table, the three table functions and the name lookup
   pointed at them, the count, the `0x03014720` check. Configurable list of new stages
   (name, cosmetic id).
2. `ui_stage_db.bin`: a tool that appends an entry (copy of an existing stage's, with the new
   cosmetic id, kinds `0x80` / `0x81`, page 2, shown on the stage select).
3. Files: `stage/melee/<Name>` and `stage/end/<Name>` (first test: a copy of Battlefield's, so only
   the slot is being tested), the six icon / preview textures (copies first), the two msbt labels.
4. Test in game: the icon, selecting it, the match loading it, Omega, random select, records /
   save (see below).

## Not known yet (to find while testing)

- **Save data / records** indexed by cosmetic id (stage play counts, unlock bits) may be fixed
  size for `0x00`-`0x37`; an id past it could write out of bounds. To check before release.
- **Music**: the stage's song list (My Music) is per stage, by name (the sound config groups,
  Manifold's `s_musicGroupNames` at `0x1041CE18`). A new name may need its own group or to be
  pointed at an existing stage's.
- **Online / replays** store stage ids; a modded stage there is untested.
- Other `0x80` / `0x38` bounds checks on kinds or cosmetic ids that only show up in game.
