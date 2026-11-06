# Smash Run (3DS) port: scoping notes

Side project (user, worked on occasionally): Smash 3DS's Smash Run ("Field Smash" in the code, `fs`) as a
selectable mode on Wii U, up to 4 players in split screen.

## The 3DS dump (user's Google Drive, "Smash 4 3DS Dump.zip", title 00040000000EDF00)

RomFS only (no ExeFS):
- `dt` / `ls` (+ `patch/dt` / `patch/ls`, the update's): the data archive, **decoded** (`tools/s3ds_unpack.py list /
  extract`): 38,158 files, every one found in the dump (400 sampled: all decompress to their size).
  - `ls`: u32 version (0x1666F), u32 count, {u32 key, u32 dt offset, u32 size}. A `dt` chunk: 0xCC padding, zlib
    streams. The update's `patch/ls` (user's second upload) is version 0x2666F with 16-byte entries (a fourth word,
    0) and its RF has 48 extensions; `s3ds_unpack.py` reads both and looks in `patch/` first: 43,655 files.
  - Keys: CRC-32 with a zero start register (`zlib.crc32(s, 0xFFFFFFFF)`) of `data<region>/<folder>/packed` for a
    packaged folder or `data<region>/<file>` for a file packaged on its own (region "" or e.g. "(us_en)"); the
    string is built by code.bin 0x1A2A60 (`%sdata%s/%s/packed`). All 4123 packages of the base table map.
  - The file tree: the "RF" resource (version 5), the chunk that starts with "RF". As the Wii U's (24-byte
    entries), but names may be shortened: name field bit 0x800000, then control byte b0 (length - 4 in bits 0-4,
    distance bits 8-9 in bits 6-7) and b1 (distance bits 0-7): copy that much from that far back in the name
    table, then the string's own rest (`\x01\x07g/` after `koopa/` = `koopag/`). Extensions: a table at the end of
    the names (u32 count 47, offsets: .bin, .mtable, .fontdef, .tex, .efc, .ptcl, .bch, .jtb, .mbn, ...).
- What Smash Run has: `reference/s3ds_smash_run_files.txt` (2,429 files):
  - `field_smash/`: the mode's params (game, events, challenges, crystal, final battles, powerup bias, the start
    selection's areas / doors / enemies / treasure boxes, difficulty, camera, `fs_cp_path.bin`).
  - `stage/field_smash/`: MainField, MiniRoom00-05, Race00 / Race01, Nobore (models, params, `.lvd` collisions),
    and `stage/final/`.
  - `enemy/<kind>/` (98 kinds: kuribo, octorock, stalfos, ..., plus the bosses), `param/enemy/fs/enemy_param_vl_*`,
    the `fs_*` items, the UI.
  - Formats: models `.mbn` (meshes) + `.bch` (H3D: textures, skeleton, material animations), motions
    `motion/body/main.bch` (H3D), `.jtb`, `.flp`, sounds `.nus3bank`, ACMD `animcmd/*.bin`.
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
- It is the **update's** (v1.1.x: the DLC fighters' code). The RomFS dump's `static.crs` / `cro.sarc` are the base
  game's and don't fit it (only 75 of 5496 exported functions on a function start). The user then sent the
  update's `static.crs` and `cro.sarc` (189 modules: the base 174 + the DLC fighters and stages): they fit
  (text 0x100000 + 0xA6110C, rodata 0xB62000, data 0xC13000; `EnemyManager::create_request` at 0x3E3E14,
  `EnemyGenerator::get_next_enemy_kind` 0x466F14, `FieldSmashManager::get_treasurebox_ejection_data` 0x528BA0,
  `FsItemAutoSet::lot_all_item` 0x42A144 all start as functions). 6654 named addresses, 212 of them Smash Run /
  enemy code.
- `tools/s3ds_unpack.py`: `code` (decompress), `cros` (cro.sarc -> modules), `symbols` (static.crs -> demangled
  "ADDRESS name" lines; code.bin offset = address - 0x100000), `imports` (a module's names).

## Wii U leftovers (cross_f.rpx)

- Strings: `FieldSmashScene`, `param/enemy/fs`, `is_ready_fs_result`, `finalenemy`, `create_enemy`.
- A full enemy system already runs on Wii U (Master Fortress, Master / Crazy Hand, Smash Tour):
  `model/enemy/*`, `motion/enemy/*`, `animcmd/enemy/*`, `enemy_param.bin`, `param/enemy/{fs,gl,ml}`; kinds cake,
  crazyhand, dogars, flyingman, kamek, magnumkiller, masterhand, metalface, metroid, nabbit, ohganemochi, ridley,
  shinigami, tac, yellowdevil. Smash Run's own enemies (the 3DS's `enemy.cro` behaviours) would be new kinds in it.

## Enemies: the Goomba (`kuribo`), converted end to end

`tools/s3ds_model.py` reads the 3DS formats, `tools/s3ds_enemy.py SRC_ROOT KIND OUT` writes the Wii U files,
`tools/s3ds_enemy_test.py SRC_ROOT [KIND]` checks them against the 3DS files (12 checks, all pass on the Goomba).

| 3DS (`enemy/kuribo/`) | Wii U (the paths cross_f.rpx builds for enemies) | How |
|---|---|---|
| `model/body/c00/normal.mbn` + `normal.bch` | `model/enemy/kuribo/body/c00/model.nud / .nut / .vbn` | meshes rigged to the .bch skeleton, as below |
| `motion/body/main.bch` (16 skeletal animations) | `motion/enemy/kuribo/body/main.pac` (16 OMOs, `EnmKuriboBodyMain*.omo`) | sampled every frame 0..end |
| `model/body/c00/material_anime/body/main/*.bch` (10) | `motion/enemy/kuribo/body/material_anime.pac` (10 MTAs) | visibility animations: which face shows |
| `animcmd/effect.bin` | `animcmd/enemy/kuribo/effect.bin` | byte-swapped to big-endian |
| `snd_se_enemy_kuribo.nus3bank` | `sound/se/snd_se_enemy_kuribo.nus3bank` | as is (already the Wii U's layout) |
| `param/enemy/fs/enemy_param_vl_kuribo.bin` | `param/enemy/fs/enemy_param_vl_kuribo.bin` | as is (same typed big-endian format) |

Formats (details in the tools' docstrings):
- **MBN** (format 4): per mesh, parts {bone list (skeleton indices), u16 triangle list}, then a vertex description
  {kind, type (f32 / u8 / s8 / s16), scale} and the vertex buffer (attributes aligned to 2). The meshes are the
  .bch model's objects in order. Positions are model space; bone indices index the part's list.
- **H3D (.bch)**, backward compatibility 0x21: section-relative pointers fixed up by the relocation table; models
  (skeleton with Euler bind pose and inverse matrices, materials with texture names / wrap / colours, objects),
  textures (PICA200 commands: 0x82 size, 0x85 address, 0x8E format; tiled 8x8, rows bottom up; the Goomba's is
  ETC1), skeletal animations (transform segments: 9 slots, scale / rotation / translation, constant or key
  groups), visibility animations (one bit a frame per object name), material animations.
  In Smash 3DS's key groups the field Ohana3DS reads as the frame offset is 1 / the end frame (every one of the
  Goomba's 576): keys sit on whole frames without it.
- **Sound**: the 3DS bank is NUS3 with the same chunks (PROP, BINF, GRP, DTON, TONE, JUNK, PACK), little-endian
  TONE entries and IDSP audio, as the Wii U's (only the sample rate differs: 20 kHz).
- **Params**: the vl file is the typed big-endian param format the Wii U's `param/enemy/*` files use.
- **ACMD**: the 3DS's is little-endian; every field is a word, so a byte swap gives the Wii U file (Goto offsets
  are in words). The Goomba's `effect.bin`: `RunL` (dust effect 0x1000026 on start, 0x1000019 every 10 frames)
  and one more script (Terminate_Overlays). The effect IDs are the 3DS's common effects: to map onto the Wii
  U's when the enemy runs.

The Goomba (6 bones: TransN, RotN, HipN, HeadN, LFootJ, RFootJ; 2 meshes, `normal_mh` / `damage_mh`, the damage
face shown by the Damage* / Down* / Collapses visibility animations, `default` shows the normal one):
- NUD: Smash 4's skinned fighter body material (0x9A011063, as Zelda's): its 128x128 ETC1 texture (BC1 now, mean
  error 2 / 255), a flat normal map, the game's shared ramp; mirrored wrap as the 3DS material's. 3DS vertex
  colours (R / G about 0.3-0.5, B 1, A 0: a 3DS shader input, not a tint) are left out: white.
- Rigid binding kept (one bone a vertex). Bind pose = the 3DS's (both games R = Rz Ry Rx).
- OMOs: rotation type 5 rebuilds w from 16-bit x y z, so bones turned ~180 degrees (the feet) lose a little: the
  mesh skinned with the written OMOs is within 0.064 units of the 3DS keys (12.4-unit-tall model), most frames
  under 0.01. Re-orienting those bones would remove it but moves the bone axes the scripts' offsets use.
- Frame counts: keys run 0..end (end 20 -> 21 OMO frames), both ends kept (RunTurnL's turn lands on its last
  frame).

Not yet: a running Goomba in game needs the enemy itself (Smash Run's `enemy.cro` BehaviorKuribo, the
EnemyManager side) — the code part of the plan below. Still to check with an enemy loaded: the Wii U's enemy
motion / visibility pac names (taken from the fighters'), the effect IDs.

## Plan (to refine once code.bin is in)

1. Data (names decoded): convert Smash Run's enemies, field, final-battle stages, UI, params.
2. Code: map the 3DS symbols onto the Wii U's leftover code (the same `app::` classes; names give the Wii U
   functions through string / structure matches); find what of FieldSmashManager / EnemyGenerator the Wii U
   still has.
3. Formats: 3DS models / motions / textures to Wii U (NUD / OMO / NUT), effects, sounds.
4. Mode: a menu entry, the character select and power setup, the 5-minute field, the final battle, results.
5. Split screen: the Wii U renders one camera; 4 viewports is engine work (cameras, HUD per player, culling).
