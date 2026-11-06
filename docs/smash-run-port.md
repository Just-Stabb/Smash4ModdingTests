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
  textures (PICA200 commands: 0x82 size, 0x85 address, 0x8E format; tiled 8x8; the Goomba's is ETC1. The 3DS's V counts up
  from the bottom of the texture as stored: (u, v) samples row (1 - v) of the memory-order image, so the NUD gets
  V' = 1 - V on the unflipped texture. v1 also flipped the image, which put every lookup upside down: the
  Goomba's face, stem and feet took the wrong parts of its atlas (user, from the preview)), skeletal animations (transform segments: 9 slots, scale / rotation / translation, constant or key
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

## Every Smash Run enemy

`python3 tools/s3ds_enemy.py SRC_ROOT all OUT` converts the 80 Smash Run enemies (those with a
`param/enemy/fs/enemy_param_vl_*.bin`): 89 models (80 bodies plus bonkers' coconut, bokkuncannon's missile and shot,
hammerbros' hammer, octorock's rock, peahat's and shotzo's shots, popperam's gravel, waddledee's parasol), 961 OMOs
in 75 motion pacs, 17 `model.mta`, 3 `material_anime.pac` (25 MTAs), 45 ACMD folders, 79 sound banks (koshinigami
has none), 80 vl params. `tools/s3ds_enemy_test.py SRC_ROOT all`: 468 checks on all 80, every one passes (models,
skeletons, textures, every motion folder skinned against the 3DS keys, visibility, ACMD).
`tools/s3ds_preview.py SRC_ROOT OUT sheet.png [--motion NAME --frame N]` renders a contact sheet from the written
files.

What the other enemies needed beyond the Goomba:
- **MBN formats 5 and 6** (69 of the 105 files): every mesh's headers and description first, then from a 32-byte
  boundary each mesh's vertex buffer and its parts' indices, each block 32-aligned (0xFF padding). Format 4 pads
  each vertex buffer to 4 (the file may end unpadded).
- **Mesh order**: the .mbn keeps the meshes in the order the exporter wrote the objects' data, not the object
  table's (18 models differ: Dekakuribo's objects 0 1 3 2 4, Pokkuri's 1 0...). Matching by order put the eye
  material on the body; matched by the objects' part-record addresses, every object's bone lists equal its
  mesh's on all 105 models (asserted).
- **Materials** (H3D fragment-operation commands): blending (source alpha / one minus source alpha -> NUD 1 / 1;
  additive source alpha / one -> 1 / 2), alpha test (greater -> 516 with the 3DS reference), culling, wrap.
  Texture unit 0 is the colour; units 1 / 2 (reflection / specular maps of the 3DS shader) are left out, except
  `*alpha*` masks (mcanimal), folded into the colour's alpha.
- **UV transform**: see "UV transforms" below (`s3ds_model.nud_sampler_uv`: s = scale, t = (-tu, (1 - sv) / sv +
  tv)). The UV scroll animations (translate / scale of coordinator 0, about 70 tracks) become `NU_colorSamplerUV`
  frames in MTAs. A material whose UV rotates (devilcar's tire; mcanimal's and mcgiant's lights outside Smash Run)
  gets the skinned effect shader instead (no body shader rotates UVs), with NU_effRotUV / ScaleUV / TransUV tracks.
  The colour-constant (combiner) animations (25) and coordinators 1 / 2 (2) are not converted.
- **Sprite enemies** (cucco, shiroiobake, and the non-Smash-Run flyingman): flat sprite meshes whose flipbook is
  one long visibility timeline in the model itself (shiroiobake: 400 frames, emerge / jump / damage / tongue...):
  `model.mta`'s visibility.
- **Texture IDs**: 0x4E000000 + 0x1000 an enemy (its index among the 80, sorted) + 0x100 a model part.
- **Overlap with the Wii U**: cake, dogars, kamek, magnumkiller, metroid, ohganemochi, shinigami and tac are also
  Wii U enemy kinds (Smash Tour / the Master Fortress); writing them to `model/enemy/<kind>/` would replace the
  Wii U's own. The package keeps them in a separate folder.
- Particle effects: below.

## Enemy particle effects (3DS SPBD v0x33 -> Wii U EFTF v0x42)

`python3 tools/s3ds_effects.py SRC_ROOT all OUT VANILLA_DIR` writes `effect/enemy/KIND/KIND.010d0000.ptcl / .efc`
for the 52 Smash Run enemies with effects (238 emitters); `tools/s3ds_effects_test.py SRC_ROOT VANILLA_DIR`: every
file validates (ptcl.validate), has the 3DS sets / emitters in order, and every emitter's written fields read
back as the 3DS values (52 files, 238 emitters, 0 failures); `tools/s3ds_effects_preview.py FILE.ptcl sheet.png`
draws a converted file with fx_render's eft model. VANILLA_DIR: the vanilla Wii U fighter ptcl files (the
templates).

The 3DS file is the same NintendoWare eft as the Wii U's (a CTR port, little endian): the same header and
tables, set records, 8-byte emitter-table entries, emitters named at +0x38 with the fields in the same order, but
2 texture slots of 0x7C bytes, 3 colour keys a track and some settings packed into bytes; a simple emitter is
0x548 bytes. No layout for this version exists (Switch Toolbox reads only names, textures and colours), so it was
worked out here (`s3ds_effects.SPBD_FIELDS`, each with its evidence):
- statistics over the 2,112 emitters of the enemies' and fighters' 3DS files (`effect/fighter/` from the
  archive): which words are floats / ints / packed bytes, their ranges, the identity matrices, angles in radians;
- pairing with the Wii U: the fighter effects both games ship (the 117 vanilla Wii U files against the 3DS
  ones) matched by file, set and emitter name (313 pairs); 147 of them agree on the fields known first (life,
  rate, scale, speeds, alpha, gravity, volume...), so they are the same emitter, and every other 3DS word / byte
  was matched against the Wii U emitter's on those (e.g. follow type 0x190 = Wii U 0x310 in 95%, combiner 0x194
  = 0x314 90%, blend 0x244 = 0x324 99%, particle type 0x328 = 0x4BC 92%, emit start 0x2C8 = 0x44C 88%,
  interval random 0x2D4 = 0x458 90%);
- names: emitters named `*add*` are blend 1 (75 of 78), `*alpha*` blend 0 (57 of 59), `*line*` particle type 3.
Differences from the Wii U worth knowing: alpha sections are integer percent (Wii U: fractions); the UV
repeat mode is a separate word (0x364: 0 1x1, 1 2x1, 2 1x2, 3 2x2), already part of the UV scale; the texture
wrap byte (TexRes +0x10) uses the Wii U's codes (0 mirror, 1 repeat, 2 clamp; low nibble U), every 2x2 repeat
mirrored as on the Wii U; the 3DS's V runs up (V scroll and UV rotation negated); flipbooks are mostly a random
start cell (0x33D, as Wii U 0x4D9), animated ones flagged at 0x338 with frames a cell at 0x340; volume sweep
angles are u32s (2^32 a turn). Textures: PICA200 (ETC1 1,273, ETC1A4 653, L4, L8, RGB565...: Switch Toolbox's
SurfaceFormat numbers at TexRes +0x6C), decoded by `s3ds_model.decode_texture`.

Conversion: each emitter onto a vanilla template (vfxb_to_ptcl.Templates: particle type, blend, follow,
flipbook, UV animation, rotation; BC4-shape templates), the 3DS fields written over it, the texture folded into
a BC4 shape (alpha from the shape for ETC1 and the other formats without alpha) and its tint into the colour
keys. The `.efc` (3DS EFCC: the Wii U's layout little endian, a u32 version) keeps its entries.

Not converted yet:
- mesh particles (20 emitters: drawn as billboards), key animations (emitter curves), complex emitters' blocks
  (1: fields / child / stripe), colour 1 where the best template has no colour-1 combiner (11);
- the 3DS combiner 3 and 0x18C / 0x248 / 0x324 (copied where a Wii U field matches, otherwise left).
- 2 trail textures (`effect/trail/*.tex`).

## Enemy effect models (3DS H3D .bch -> Wii U effect model folders)

`tools/s3ds_effects.py SRC_ROOT all OUT VANILLA_DIR` also runs `tools/s3ds_effect_models.py` on every enemy:
each `effect/model/NAME/normal.bch` (+ `motion.bch`) becomes `effect/enemy/KIND/model/NAME/` (model.nud / nut /
vbn / omo / mta / xmb, the layout of the game's own effect models), and the `.efc` keeps every reference to a
model it converted (renumbered; one 3DS reference, `EfffsPokkuriBulletDelete`, names a folder the 3DS files
don't have either, and is dropped). 99 models in 62 enemy banks: 281 meshes, 540 materials, 230 textures. Six
enemies have models and no particles (keronpa, meganta, mettaur, monoeye, popperam, shinigami): their bank is an
`.efc` and model folders without a `.ptcl`, as the vanilla `miienemys` bank (four more have only an `.efc`). `tools/s3ds_effect_models_test.py
SRC_ROOT OUT` reads every written folder back (99 models, 0 failures); `tools/s3ds_effect_models_preview.py OUT
sheet.png` draws them from the written files.

What the conversion does:
- **Geometry**: the effect models keep their vertex data in the .bch itself (no .mbn). `s3ds_model.Bch._geometry`
  reads it the way the GPU does, from each object's PICA200 command list: the attribute layout and permutation
  (regs 0x201-0x205, 0x2BB / 0x2BC), the buffer address / stride / count, the per-attribute scales and the
  position offset from the vertex shader's float uniforms 6-8, and the index buffers (0x227 / 0x228; the
  relocation kind sets 16-bit indices). One NUD mesh a non-empty object part, bound to its bone (bind 8: the
  3DS's rigid skinning keeps the vertices in that bone's space); UV V' = 1 - V as the enemies.
- **Skeleton / motion**: the .bch bones under a TopN root (unless theirs is one), every bone at the origin in
  the VBN and its full local transform a frame in the OMO (the motion.bch sampled 0..end, or the bind pose).
  Several effects squash an axis to 0 or mirror it (negative scale); `s3ds_enemy.split_trs` keeps those exact
  (a zero axis takes its direction from the others, a negative determinant goes on the smallest axis); the
  enemy motions use it too.
- **Materials**: the effect shader 0xB0201100 as the XV2 effect models (`tools/xv2_to_nud.py`): blend from the
  fragment operations (source alpha / one minus source alpha -> alpha blend, source alpha / one -> additive),
  alpha test, culling, texture coordinator 0's scale / translate as NU_effScaleUV / NU_effTransUV.
- **The texture combiner, baked**: the 3DS draws these materials through its 6-stage texture combiner (TEV,
  regs 0xC0-0xFD in the material's fragment commands), which NUD has no equivalent of: most stages lerp the
  diffuse colour against a constant colour by the texture and take the alpha from one of the texture's channels
  (ETC1 has no alpha; drawn as is, those meshes were black squares). `s3ds_model.tev_combine` runs the combiner
  (every source, operand, the 10 combine modes, scales and the combiner buffer, as Citra's rasterizer) over the
  texture's texels and the result is the material's texture. Only texture 0 is ever read by these 540 materials,
  so the bake is exact for a static material (the vertex colour still multiplies after, in the NUD shader).
- **Colour animation**: a stage's constant is one of the material's 12 colours (found by value: e.g.
  StarmanBeam's stages use constant0, Popperam's exclamation mark the ambient slot), and the material
  animations target colours (property 9 diffuse, 8 ambient, 1 constant0; 19 / 21 coordinator 0 scale /
  translate, 20 its rotation). For an animated material the combiner runs every frame with the animated
  colours, the most visible frame is baked, and every frame's output (alpha-weighted colour, alpha) over the
  baked frame's is NU_effColorGain in the MTA. Exact when the output is proportional to the animated colour
  (fades, the usual case); an approximation for a lerp whose ends animate differently. Visibility animations go
  to the MTA by mesh name.
- UV scale / rotation / translation (static and animated) as "UV transforms" below.
- Not converted: the per-texel shape of a colour animation that isn't a scale.

## Stages (stage/field_smash -> the NewStage01 slot)

`python3 tools/s3ds_stage.py SRC_ROOT all BASE OUT --preview` builds every Smash Run area as a stage for the
new-stage slot (`docs/stage-expansion.md`): `OUT/AREA/stage/melee/NewStage01`, built on the slot's Battlefield copy
(BASE) the way Minecraft World is (`docs/minecraft-world.md`: only forms Battlefield's loaded models have, its
model folders hidden, its midday light held). `tools/s3ds_stage_test.py SRC_ROOT BASE OUT` reads every build back
(10 builds, 579 meshes, 0 failures). Areas: the rooms MiniRoom00 / 01 / 02 / 03 / 05 (arena sized, MiniRoom01 / 02
with their crystals), the final battles Race00 / Race01 (side-scrolling courses ~6000 units long) and Nobore (a
10000-unit climb), and MainField, the whole floating-island labyrinth (41 models, 302 meshes, 185 collisions).
`MiniRoomCommon` (doors, chests the mode places) and `stage/final/` (the Final Smash cut-in backdrops, not Smash
Run) aren't areas.

- **Formats**: the 3DS stage `.lvd` is the Wii U's format byte for byte (big-endian, same magic: `lvd.py` reads
  them; it now writes files with an enemy-generator section, which it keeps as bytes, back identically); the
  `*_stprm.bin` typed params are the Wii U's layout (one more value at the end); the models are the enemies' .bch +
  .mbn (a third UV set, MBN attribute 7, added to the reader).
- **Models**: each model folder (not the broken / cracked crystal pieces or the shadow volumes) is a static
  `stc_sr_NAME_set` folder: the objects shown by default, unbound, in Battlefield's unlit shader `0xA2001001`
  (opaque, alpha-tested, alpha or additive blending as the 3DS material), the texture combiner baked into the
  texture (as the effect models; textures 1 / 2, sphere environment maps and second UV sets on 180 of the 700
  materials, enter as their average colour), the 3DS fragment lighting baked into the vertex colours, UV scrolls in
  a `model.mta`. The gimmicks' animations (doors, chests, crystals breaking, moving floors, springs, barrels) need
  Smash Run's stage code and stay still; the material colour animations are left out.
- **Collision**: all the area's `.lvd` collisions (the Race's course pieces Test00-04 together) with their bone
  links dropped; Battlefield's spawn / respawn / camera / blast / item entries filled from the 3DS points (8 spawns:
  the 3DS ones and more on the floors near them; respawns in Battlefield's pattern; the 3DS camera bounds or the
  collision's; blast zones at least the camera bounds plus Battlefield's margins: the race's and climb's own are
  tuned for those modes). MiniRoom00 is walled in (a closed loop facing its inside: no KOs), so it also has a
  `MiniRoom00_open` build without it.
- **Camera**: the 3DS stage's stprm camera values (fov 30, distance 50, angles -5 / -22; MainField fov 15,
  distance 100).
- As versus stages: the rooms play as normal stages; the race / climb and the field are far larger than the
  camera's usual range (it frames everyone, so it will be zoomed far out when fighters spread).

## The stages in their own slots (no replacement)

`python3 tools/smashrun_slots.py SRC_ROOT BASE_STAGE PARAM_DIR SOUND_DB MSBT UI_DIR LOGO OUT --rpx IN.rpx` makes
every build above a stage of its own next to NewStage01 (Minecraft World): ten new slots
(`stage_slot_cave.py`, docs/stage-expansion.md), on page 2 with the DLC stages.

| folder | area | cosmetic | kinds | name |
|---|---|---|---|---|
| SR_Room00 | MiniRoom00 | 0x39 | 0x82 / 0x83 | Smash Run Room |
| SR_Room00Open | MiniRoom00, open | 0x3A | 0x84 / 0x85 | Open Room |
| SR_Room01 | MiniRoom01 | 0x3B | 0x86 / 0x87 | Crystal Room |
| SR_Room02 | MiniRoom02 | 0x3C | 0x88 / 0x89 | Crystal Cave |
| SR_Room03 | MiniRoom03 | 0x3D | 0x8A / 0x8B | Platform Room |
| SR_Room05 | MiniRoom05 | 0x3E | 0x8C / 0x8D | Long Room |
| SR_Race00 | Race00 | 0x3F | 0x8E / 0x8F | Run! Course 1 |
| SR_Race01 | Race01 | 0x40 | 0x90 / 0x91 | Run! Course 2 |
| SR_Climb | Nobore | 0x41 | 0x92 / 0x93 | Climb! |
| SR_Field | MainField | 0x42 | 0x94 / 0x95 | Smash Run Field |

("Run!" / "Climb!" are the 3DS's names for the final battles, `menu.msbt` MmenField_st_2_3 / 2_2.)
- Both forms are the Smash Run stage: `stage/melee/NAME` built on Battlefield's melee copy, `stage/end/NAME`
  (Omega) on its Omega copy; files renamed (`NAME00.lvd`, `Z_NAME_00.lvd`, `NAME_stprm.bin`). Battlefield's own
  model folders (hidden in NewStage01's builds) are left out: 10 of a stage's 12 MB, and nothing else in the
  folder refers to them (the generic stage loads a folder's files by pattern). Untested in game; their hidden
  copies are kept apart for a stage that wouldn't load without them.
- Database / songs / texts on the installed files (the user's `ui_stage_db.bin` with NewStage01 at 0x38, the
  Minecraft music `ui_sound_db.bin`, the newest `melee.msbt`): NewStage01's entry copied (Battlefield's, page 2),
  Battlefield's song list, `MmelStageN_` the name, `MmelStageG_` "Smash Run".
- Pictures rendered from the converted stage (its camera bounds, a 600 x 300 window over a long course's
  start) into the templates' formats: stage_11 preview, stage_10 / stage_12 / stage_30 / stage_13 crops (as
  Minecraft World's), stagen_10 the name banner, stagel_10 the unmodified Battlefield's "Super Smash Bros." logo.
- The executable: the last test's (Sephiroth test 147) + `stage_slot_cave.py` with NewStage01 and the ten
  (`stage_slot_test.py`: kinds 0x80-0x95, names / paths, cosmetic ids 0x38-0x42, no relocation left: 0 failures).
  Kinds past 0x81 are new ground: any table the game indexes by stage kind past the 128 it has, other than the
  ones the cave moves, is read past its end (as NewStage01's 0x80 / 0x81 already are, which play).

Placement found on the way (s3ds_stage.py, all builds): a rigidly skinned part (no weights) is in its bone's space
(the crystals' and the race hazards' bones carry their place: each now lands within 3 units of its collision); a
collision with `use_start` is translated by its start (the climb's tower: one segment's 31 lines five times,
1300 apart, so the tower pieces are drawn at each, the floor at the bottom; MainField's moving floors where a
collision of their width sits), and spawns / camera / floors use those placed lines. MainField's doors, barrels,
springs, chests and blocks (placed by the mode's code, at the origin in the files) and the swapped states of
Area_14 are left out.

## UI and mode params (3DS ui/, param/, field_smash/ -> Wii U files)

`python3 tools/s3ds_ui.py SRC WIIU_MESSAGES OUT [--melee MELEE.msbt]` converts what Smash Run shows and reads;
`tools/s3ds_ui_test.py SRC WIIU_MESSAGES OUT [--melee M] [--wiiu-lumen DIR]` reads it all back (0 failures: 201
Wii U .lm round trips, 16 .lm with 2475 actions, 15 .flx, 274 textures, 370 texts, 73 params / scripts). Nothing on
the Wii U loads these yet: the mode's code (FieldSmashManager, the menus' scenes) is the plan's step 2-4; these are
its files, ready in the Wii U's formats and places.

| 3DS | Wii U | how |
|---|---|---|
| `ui/info/fs_*`, `pause_field_down` (HUD movies, flx2) | `ui/info/NAME/` | byte order (tools/flx.py reads both), root scaled |
| `ui/lumen/field_*`, `result_field1_*` (menus, Lumen LMB) | `ui/lumen/NAME/` | field table below, root scaled |
| `texlist.lst` | same | byte order |
| `img-NNNNN.tex`, `ui/replace/field/*`, `mark_*_fs_item` | `.nut` | PICA decode, flipped, RGBA8, ids 0x2800A000 up |
| `ui/message/*.msbt` (LE) | `menu / melee / smash / figure / cleargetter.msbt` | the Smash Run labels added to the Wii U files |
| `field_smash/*.bin`, `param/item/*fs_*`, `param/ui/fs_info_param.bin` | same paths | copied: big-endian already |
| `ui/script/app/field_smash/*.xtal` | same | copied: the same xtal format |

- **Screen**: the 3DS movies are 400 x 240 (top) / 320 x 240 (bottom); the Wii U's 1920 x 1080. Each root
  placement gets x4.5 and the centring offset (+60 / +240), so everything keeps its proportions and the paths the
  game finds instances by (`root/num_1`) stay: an flx sprite's transform, an image's / text's rect (and the text's
  font size); a Lumen placement's matrix (a new row: rows are shared), a placement without one only when it places
  a new object. Checked by flx_render (the timer and the pause screen draw as on the 3DS).
- **Lumen byte order** (no 3DS / Wii U pair of the same file exists but prize2): each tag word of all 234 3DS
  .lm against all 201 Wii U ones: a word is one 32-bit value, two u16 (place mode / blend, depth, sprite frame
  counts, colours, graphic fill / vertex count, indices) or four bytes (text flags), whichever makes the 3DS
  values the Wii U's. Action bytecode (F005) is SWF's little-endian on both (same push types, doubles, branch
  offsets): only its counts swap. Tags: `s3ds_ui.FIXED / RECORDS`; the Wii U's own menus survive the table both
  ways byte for byte, and every converted field equals the 3DS's at its width.
- **Textures**: .tex = 0x80 header (u32 w, u32 h, u8 PICA format, u8 mips, name) + the PICA image, rows bottom
  first: flipped, the texture lists' UVs (from the top on both) then pick the same pixels (checked: the timer's
  digits). RGBA8, so no BC loss on the 3DS's small images.
- **Texts**: 370 labels (MmenField_*, Mmel_Fsi*, MmelField*, MmelPause_fieldsmash_*, Msma_Field*, MfigI_Fs*,
  MclgPrize_fsi*, ... and every label a movie shows that the Wii U lacks) added to the Wii U files (melee: on the
  stage-slot build's, which has the stage names); labels the Wii U already has keep its text. The 3DS's control
  codes (button icons, colours) are swapped like the text; any that differ between the two games show wrong.
- **Params**: 69 typed param files (FF FF header), 2 typed without a header (`camera_param.bin`, ...), 1 LVD
  (`fs_cp_path.bin`, the CPU paths): `--dump DIR` lists their values as JSON (outside OUT: everything in OUT has an
  extension the game's resource table has, so Sm4shExplorer adds the whole folder without skipping any).
- Open: flx frame actions are indices into a per-movie table compiled into the executable (docs/flx2-format.md):
  the fs_* movies' (the 3DS's) aren't in the Wii U's, so a scene playing them needs its own; Lumen scripts that
  set positions (`_x`, `_y`) still count in 3DS pixels.

## UV transforms (3DS coordinators -> Wii U shader UV props)

Both sides read from code, not guessed:
- **3DS**: H3D's texture coordinator transform, SPICA's `TextureTransform` (every Smash Run material is the Maya
  type): rotate about the texture's centre, subtract the translation, then scale: `s3ds_model.tex_transform`.
  The 3DS samples row (1 - v') of the texture, the NUD's V is 1 - V.
- **Wii U**: the vertex programs in the game's `shader/texas_cross.nsh` (disassembled with tools/latte_dis; the
  uniform blocks from the GX2 headers). The effect shader (MC_EFFECT: effScaleUV [1], effRotUV [2],
  effTransUV [3]): u_r = cos r (u - 1/2) + sin r (v - 1/2) + 1/2, v_r = -sin r (u - 1/2) + cos r (v - 1/2) + 1/2,
  U = (u_r + t.x) s.x, V = 1 - s.y (1 - (v_r + t.y)) (the angle in radians, as vanilla Ness PK Thunder's MTA
  animates it between 0 and pi). The body shaders' colorSamplerUV: U = s.x (u + t.x), V = s.y (V' + t.y), no
  rotation (some variants scroll t x uvScrollCounter instead).
- Solved (`s3ds_model.nud_eff_uv` / `nud_sampler_uv`, any transform type): effect r = the 3DS rotation, s = its
  scale, t = (-tu, tv) for Maya; body s = scale, t = (-tu, (1 - sv) / sv + tv). Checked numerically against SPICA's
  matrix for random transforms of all three types, and on the fighter effects both games ship (Cloud's
  Climhazzard slash U 0.4 -> -0.4, Dedede's jet hammer (0.042, 0.125) -> (-0.042, 0.125)); the tests run every
  written mesh's UVs through these shader formulas against the 3DS transform (and every MTA frame).
- What changed from before: the translation is scaled with the texture (the old mappings, from Ohana3DS's
  uv * scale - translate and Smash Forge's shader, were right only for scale 1), and rotation is converted.

Not yet: a running Goomba in game needs the enemy itself (Smash Run's `enemy.cro` BehaviorKuribo, the
EnemyManager side) — the code part of the plan below. Still to check with an enemy loaded: the Wii U's enemy
motion / visibility pac names (taken from the fighters'), the effect IDs.

## Plan (to refine once code.bin is in)

1. Data (names decoded): convert Smash Run's enemies, field, final-battle stages, UI, params. Done: enemies,
   their effects and effect models, the stages (also in their own slots), the UI and the mode's params (above).
2. Code: map the 3DS symbols onto the Wii U's leftover code (the same `app::` classes; names give the Wii U
   functions through string / structure matches); find what of FieldSmashManager / EnemyGenerator the Wii U
   still has.
3. Formats: 3DS models / motions / textures to Wii U (NUD / OMO / NUT), effects, sounds.
4. Mode: a menu entry, the character select and power setup, the 5-minute field, the final battle, results.
5. Split screen: the Wii U renders one camera; 4 viewports is engine work (cameras, HUD per player, culling).
