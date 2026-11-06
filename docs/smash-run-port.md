# Smash Run (3DS) port: scoping notes

Side project (user, worked on occasionally): Smash 3DS's Smash Run ("Field Smash" in the code, `fs`) as a
selectable mode on Wii U, up to 4 players in split screen.

## The 3DS dump (user's Google Drive, "Smash 4 3DS Dump.zip", title 00040000000EDF00)

RomFS only (no ExeFS):
- `dt` / `ls` (+ `patch/dt` / `patch/ls`): the data archive. `ls`: u32 version (0x1666F), u32 count (4513), then
  {crc32, offset, size} chunks of `dt`; a chunk is 0x60 bytes of 0xCC, then zlib streams (files), padded with
  0xCC. The name index is an "RF" resource table (version 5) in `dt` itself, one per region (crc32s 0x264CD480,
  0xF9FE97F3, 0x1DCF74F7, 0x351477EE; the patch has its own). Entries are the Wii U's 24 bytes (offset, name |
  ext << 24, compressed, decompressed, timestamp, flags); the names are shortened with back-references (a
  control byte and an offset into earlier names, then a suffix: `\x03\x92_param_vl` = a fighter folder's
  `<name>_param_vl`), which `tools/rf_check.py` (Wii U, plain names) doesn't read yet. Next: decode those and list
  the Smash Run files (enemies, field parts, stat boosts, powers).
- `cro.sarc`: the code modules. Not Nintendo's SARC: "SARC", u32 count (174), "CRC\0", then {hash, offset,
  decompressed size, compressed size} and zlib-compressed CROs (module name at CRO header +0xC0).
- `static.crs`: the symbol tables of the main executable (code.bin), 6152 exported names, **no code** (its code
  size is 0).
- `sound/bgm/*.nus3bank`, `sound/smashappeal/`, `movie/howtoplay.moflex` (left out of the scratch copy to save
  space; refetch for Smash Run's music).

## Where Smash Run's code is

CROs (in the dump, with their symbol names):
- `main_field.cro`: `StageFieldSmash` (the Smash Run field) and `StageFsMiniroom`.
- `menu.cro`: the mode's scenes: `MenuViewFieldSmashScene`, `CharacterSelectFieldSmashScene`,
  `FsPreparationSequenceScene`, `FsViewItemSetScene` (powers / stat items), `FsViewFinalInfoScene`,
  `FsViewResult1Scene`, `FsViewSoundSelectScene`, `FsViewTutorialScene`.
- `enemy.cro` (Behavior* for each enemy), `enemy_fs.cro` (`EnemyParamAccessorInstanceFieldSmash`).
- The final battles' stages: `race.cro` (`StageFsRace`), `nobore.cro` (climb, `StageFsNobore`), and the rest
  of the `StageFs*` / `*_c` modules.

The main executable (code.bin, **not in the dump**): the managers the CROs import, e.g. `FieldSmashManager`,
`EnemyManager`, `EnemyGenerator`, `FsItemAutoSet`, `StageBaseFs`, `StageEnemyLayout`, the enemy modules
(`EnemyAerialModuleImpl`, `EnemyAiModuleImpl`, ...), records (`RecFieldSmash*`). Needed: the decrypted ExeFS
(`code.bin`; GodMode9 / a decrypted CIA's `exefs`).

## code.bin (user's dump, 6,478,036 bytes)

- Compressed with the 3DS's bottom-up LZ (footer: buffer top/bottom 0x0962D887, extra 0x54172C):
  decompresses exactly to 11,988,992 bytes (0x100000-based: text, rodata, data). CTR-SDK 1.2.7.
- **Not the build of the RomFS dump's `static.crs`:** the CRS's segments (text 0x100000 + 0x982FE4, rodata
  0xA83000, data 0xB25000) don't fit it (its code runs past 0xA83000), and only 75 of 5496 exported ARM functions
  land on a function start, with no common shift. So the code.bin is the update's (bigger: the DLC fighters' code)
  and the RomFS dump's `static.crs` / `cro.sarc` the base game's (or the other way round). Needed: a matching pair,
  either the base title's code.bin (00040000000EDF00 ExeFS) or the update title's (0004000E000EDF00) RomFS
  `static.crs` + `cro.sarc`.

## Wii U leftovers (cross_f.rpx)

- Strings: `FieldSmashScene`, `param/enemy/fs`, `is_ready_fs_result`, `finalenemy`, `create_enemy`.
- A full enemy system already runs on Wii U (Master Fortress, Master / Crazy Hand, Smash Tour):
  `model/enemy/*`, `motion/enemy/*`, `animcmd/enemy/*`, `enemy_param.bin`, `param/enemy/{fs,gl,ml}`; kinds cake,
  crazyhand, dogars, flyingman, kamek, magnumkiller, masterhand, metalface, metroid, nabbit, ohganemochi, ridley,
  shinigami, tac, yellowdevil. Smash Run's own enemies (the 3DS's `enemy.cro` behaviours) would be new kinds in it.

## Plan (to refine once code.bin is in)

1. Data: decode the 3DS RF names; extract Smash Run's enemies, field, final-battle stages, UI, params.
2. Code: map the 3DS symbols onto the Wii U's leftover code (the same `app::` classes; names give the Wii U
   functions through string / structure matches); find what of FieldSmashManager / EnemyGenerator the Wii U
   still has.
3. Formats: 3DS models / motions / textures to Wii U (NUD / OMO / NUT), effects, sounds.
4. Mode: a menu entry, the character select and power setup, the 5-minute field, the final battle, results.
5. Split screen: the Wii U renders one camera; 4 viewports is engine work (cameras, HUD per player, culling).
