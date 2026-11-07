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
| `field_smash/*.bin` | `param/field_smash/` | copied: big-endian already; under param/: the Wii U has no path for them and Sm4shExplorer adds no folder at data's root |
| `param/item/*fs_*`, `param/ui/fs_info_param.bin` | same paths | copied |
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

## What the Wii U executable has of Smash Run (read for "make the mode playable")

- **Enemy kinds**: the full shared table, 97 kinds (names 0x1041A22C, killer = 0; resource folders 0x1041A3B0,
  capitalised 0x1041A534), all 90 Smash Run kinds included; `enemy_param.bin` and the path builder 0x030BC6BC
  (model / motion / animcmd / sound / effect) work for every kind.
- **Behaviours: none for Smash Run kinds.** Enemy object: vtable 0x10120038, ctor 0x02D88CE4 (0x34D8 bytes),
  activate 0x02D89CC8 (calls the factory; reads `[mgr+0x60+4*kind]+0x70` unchecked). Factory 0x02DB94CC (behaviour
  module vtable 0x10122340 +0x44): `kind - 0x50`, 17 cases: masterhand 0x02DD0438, crazyhand 0x02DC7414, mastercore
  0x026B7344, mcfinal 0x026C2E9C, mcblade 0x026BE944, mcanimal 0x026BB3E8, mcgiant 0x026C5F80, mczakoplasmawisp
  0x026CF4DC, mczakodarios 0x026CBA64, mczakostalfos 0x026D1DFC, mczakozima 0x026D6834, yellowdevil 0x02DDB82C,
  ridley 0x026E24EC, metalface 0x026D80A0, nabbit 0x026DB864 (subetenoyaminoou / flyingman: none). Base Behavior
  ctor 0x02DB2DF0 has 12 callers (= these 15). Kinds below 0x50 get no behaviour. The 3DS's 77 enemy_fs.cro
  behaviours were not linked; the Master Fortress minions (mczako*: Plasma Wisp, Darios, Stalfos, Zima) are the
  only Smash Run enemies with Wii U AI.
- **Params**: manager `*(0x102F6C00)` (0x02DC64F4); its set-up 0x02DC66D0(mode) makes the ml accessor (mode 0,
  ctor 0x026AE888) or sm (mode 2, 0x026B40B8); no fs accessor. They load `param/enemy/{ml,sm}/<kind>.bin` for
  kinds 0x50-0x60 only (switch 0x026AED18) into mgr+0x60+4*kind.
- **Leftovers**: 34 Smash Run enemy weapons in the weapon kind table (owners 0x10418968), and code clusters reading
  Smash Run kinds' param slots (0x03187000-0x031A1000, 0x02AD5000-0x02AE9000), probably their projectiles: dead
  (null slots). Smash Tour loads models / motions only (cake, dogars, kamek, metroid, tac, shinigami, ...).
- **Scene**: `FieldSmashScene` is only a name: the battle scene changer 0x03017010 picks it for mode 8, but no
  factory is registered (0x100CBD90, 0x02A6878C, 0x023A6EF0). No FieldSmashManager / EnemyGenerator.
- **Spawning** (stages do it): EnemyManager / EnemyResourcePool `*(0x102F98A0)` (ctor 0x02D998CC; 24 slots).
  Battle load 0x02FB6068 makes it and sets the category (0x02D99FD4: 1 ml, 2 sm, 0 fs); 0x02FB64E0 -> 0x02D9A454
  requests kinds per stage (0x1C yellowdevil, 8 ridley, 0x13 metalface, 3 nabbit) through 0x02D9A580 / the
  resource request 0x02DAE314(mgr+0x28, kind). Spawn: `id = 0x02D9BCFC(mgr, &EnemyCreateParam)` (-1 on failure),
  e.g. Pyrosphere 0x024B4248 (kind 0x5E). Data-driven stage spawner 0x02A8558C (kind, variation, int, x, y).
  EnemyCreateParam 0x3C bytes: +0 kind, +4 variation, +8 f 1.0, +0xC/+0x10/+0x14 position, +0x18 f -1.0, +0x1C u8,
  +0x20 s32 2, +0x24/+0x28/+0x30 f, +0x2C/+0x34 s32, +0x38-0x3B flags (+0x3A cost limit).

## Step 1: the button and enemies on the field

`tools/smashrun_menu.py` (Games & More button) and `tools/smashrun_field_cave.py` (enemies), tests
`tools/smashrun_menu_test.py` / `tools/smashrun_field_test.py` (0 failures each; Training 0 CPUs and the stage slots
still pass on the same executable). Not yet run in game.
- **Button** (docs/games-and-more-menu.md): on the user's own Games & More (a UI mod: btn_08 was an empty shape at
  x 5000) a copy of the Group button at (1460, 496), "Smash Run" in the titles' style and a star (the 3DS menu's
  Smash Run icon); the 8th button registered by a cave (0x029ABC68: button 8, result 7, id 115), result 7 posting
  Training's menu key (0x31) instead of the spare 0x5B. Pick a fighter, the Smash Run Field stage and 0 CPUs.
- **Enemies on every Smash Run stage** (0x82-0x95): the game's own enemy system as Classic's Master Fortress uses
  it, category sm, with the four Fortress minions (the Smash Run enemies the Wii U has AI for): Plasma Wisp,
  Darios, Stalfos, Zima, one every 150 frames beside the player in turn, at most 6 alive. Hooks: 0x02D9E2DC (make
  the EnemyManager), 0x02D99FF8 (category 2), 0x02D9A568 (request the kinds' resources), 0x02D9B6F8 (spawner,
  in the manager's per-frame update). Cave 0x04B7D100-0x04B7E000.
- Open: whether the minions' appear effect / sound load outside the Fortress (0x02DB3574; missing would only mean
  no effect); whether the manager's update runs during pause; memory on the large field; Classic's counter object
  0x10352470 (set up only by the Fortress round) left alone. Next: Smash Run's own enemies (generic AI on the
  converted models, motions and scripts), power-ups, the 5-minute timer and the final battle.

## Step 2a: Smash Run's own Stalfos, Zima, Plasma Wisp and Darios with their Fortress twins' AI

`tools/smashrun_enemy_cave.py IN.rpx [OUT.rpx]` (test `tools/smashrun_enemy_test.py PATCHED.rpx [ENEMY_ROOT]`), with
`tools/smashrun_field_cave.py` now spawning (and requesting) the Smash Run kinds instead of the minions (its
`ENEMY_SETS`; `--minions` builds step 1's set). Not yet run in game. Package smashrun_step2a_v1: the user's
executable (stage slots + Training 0 CPUs) + smashrun_menu.py's rpx part + the field cave + this, in one
rpx_patch.py call (each tool's hook words checked first; smashrun_menu.patch_rpx's free-space check reads the text
section once per word, minutes), and capitalised copies of the four sound banks. On it: smashrun_enemy_test.py
(with the installed enemies: every set entry an OMO of K's pac, every stalfos script in its set) 26 checks,
smashrun_field_test.py 12, training_cpu_test.py, smashrun_menu_test.py's rpx checks, stage_slot_test.py (NewStage01
+ the ten): 0 failures each.

The four Fortress minions are Smash Run enemies under another name, with the same (3DS) behaviours. The converted
3DS enemies keep their own kinds (index in the name table 0x1041A22C, checked): stalfos 0x30 (twin mczakostalfos
0x59), zima 0x0E (0x5A), plasmawisp 0x12 (0x57), darios 0x1D (0x58). Each K runs its twin's behaviour on K's own
files (model, main.pac, animcmd, sound, effects):
- **Factory** 0x02DB94CC (r30 module, r31 kind, r29 variation): hook 0x02DB9518 `addi r12, r31, -0x50` -> for the
  four K, `module+8 = twin_create(module+4, K, variation)` (creates 0x026D1DFC / 0x026D6834 / 0x026CF4DC /
  0x026CBA64, reached with `bctrl`: out of `bl` reach), then the factory's epilogue 0x02DB96E0; other kinds go on
  to its switch. create passes K to the Behavior ctor 0x02DB2DF0; behaviour code reads params both through the
  object's kind (`lwz r0, 8(rX)` then `[mgr+0x60+4*kind]`, e.g. 0x026D1E24) and from its twin's slot hard-coded
  (20 sites in mczakostalfos's code read `[mgr+0x60+4*0x59]`).
- **Tables** (battle load 0x02D9A454, before its accessor set-up and the field cave's requests): hook 0x02D9A468
  `lwz r0, 0x5EC(r31)` -> on a Smash Run stage, motion data set table 0x10352610[K] (get_motion_data_set
  0x02DC6D68, read by the enemy's accessor set-up 0x02DA2A3C at +0x58) -> K's own set, and article table
  0x10352794[K] (0x02DC6D88: the weapons the request 0x030BF400 loads at 0x030BF588, accessor +0x80) -> the twin's
  (only mczakoplasmawisp has articles: 4 weapons from 0x102FE844; the other three are the empty default). Both
  tables are initialised .data written at run time (nothing to relocate).
- **Param slots**: the sm accessor fills `[*(0x102F6C00) + 0x60 + 4*kind]` (kinds 0x50-0x5A) in 0x02DC67C0, called
  from the battle's param load 0x02D9A5EC (0x02D9A614), after the battle load's requests: hook 0x02D9A614 `bl
  0x02DC67C0` -> the call, then on a Smash Run stage slot[K] = slot[twin]. The activation (0x02D89CC8, +0x70) and
  the accessor set-up (0x02DA2B9C, +0x5C) read slot[K] unchecked. Sharing is the right layout as well as the right
  values: the Wii U sm vl files are longer than the 3DS fs ones (stalfos 1323 / 1293 bytes, zima 783 / 758,
  plasmawisp 2288 / 2248, darios 1128 / 1098), and the behaviours were built for the Wii U layout. The accessor
  frees its own block on teardown (0x026B43E0), never a slot, so the copied pointers are no double free.
- **Field cave** (smashrun_field_cave.py "smashrun" set): spawns 0x12, 0x1D (placement 2) and 0x30, 0x0E
  (placement 1) in turn from a (kind, placement) table, and requests 0x12 0x1D 0x30 0x0E plus 0x57
  (mczakoplasmawisp's own resources, in case its weapons / effects are looked up under the twin).

Motion data sets (K's built from the twin's, at 0x04B85C00): `{entries*, count, 4 zero words, count x 12-byte
hashsets, entries {hash, flags}}`. Entry hash = `zlib.crc32(stem, 0xFFFFFFFF)` of the OMO's file name in main.pac
without `.omo`, case kept: every entry of the Wii U mczako sets is `EnmMczako<name>BodyMain<X>`, and 572 entries of
the fighters' weapon sets in .data hash their pac stems the same way (none with `.omo` or lower case). The twin sets
are K's 3DS animations with "Mczako" inserted, in the Wii U's own order (stalfos: 38 entries, the 30 animations with
aliases at 5-10 = Attack1 / Attack2 and 31-32 = Jumpattack / Jumpattacklanding; zima: Damage dropped, Turn added
against the 3DS set; stalfos's index 26 is `FlinchEnd` on the Wii U, `Flinchend` in K's pac). K's set: the same
indices, K's stems' hashes, the twin's flags (1; 5 for stalfos FlinchStart; 0x40 for darios DamageStart) and
hashsets. Every one of the twins' entries has its animation in K's converted pac. Scripts: K's converted
`animcmd/enemy/stalfos/attack.bin` and `effect.bin` (13 scripts each) all hash into mczakostalfos's hashsets (the
3DS scripts use the Wii U's names); zima / plasmawisp / darios have no animcmd on the 3DS either (their attacks are
code and params). The enemy loads `effect.bin`, `sound.bin`, `attack.bin` (0x02DC6A98); missing ones are skipped.

Sound: the bank path uses the capitalised name table 0x1041A534 (`sound/se/snd_se_enemy_%s.nus3bank` -> Stalfos,
Zima, Plasmawisp, Darios), as every Wii U enemy bank is named (snd_se_enemy_Mczakostalfos...); the converted banks
were written lower case, so step 2a's package adds capitalised copies (the banks' own names are already
`snd_se_enemy_Stalfos`...). Their tones are in the twins' order (Stalfos: Attack, JumpAttack, Buckstep, Guard,
Shrink, Landing = Mczakostalfos's; Plasmawisp's five = Mczakoplasmawisp's; Darios's two = Mczakodarios's).

Params (enemy_param.bin, gl, read by the activation for every kind): the four K have entries of their own, with
Smash Run's values: HP (+0x14) stalfos 60 / zima 10 / plasmawisp 20 / darios 20 against the twins' 24 / 15 / 10 / 25,
model scale (+0x1C, the activation's set_scale) stalfos 2.4 against 1.6, darios 0.8 against 0.9, the others equal.

Not verified (no Wii U mczako model / motion / effect files here): whether the behaviours use bone indices (no bone
name strings, and no hash of any of K's bone names, in the behaviours' code or the vl params: the attack scripts'
bones are K's own, from the 3DS); whether their effect calls (by index into the kind's own effect file) match the
converted 3DS effect lists; what the gl entries' other differing fields do (+0x34 is 1 for every 3DS kind, 0 for
the Wii U ones; not read by the activation).

Space: 0x04B85800-0x04B86800 (code to 0x04B8597C, sets 0x04B85C00-0x04B86174), in kind_expand.py's old stale space
(0x04B85800-0x04B877C4; no branch, address or data pointer refers to it), cleared to zeros up to 0x04B88000
(base_effects_cave.py's). Still free: 0x04B86800-0x04B88000.

## Step 2b: a generic walker behaviour for Goomba, Shy Guy, Waddle Dee, Waddle Doo and Churine

`tools/smashrun_walker_cave.py IN.rpx [OUT.rpx]` (test `tools/smashrun_walker_test.py PATCHED.rpx [ENEMY_ROOT]`),
with `tools/smashrun_field_cave.py`'s new default set "walkers". Not yet run in game. Package smashrun_step2b_v1:
the user's executable (stage slots + Training 0 CPUs) + smashrun_menu.py's rpx part + the field cave + step 2a +
this, in one rpx_patch.py call (every tool's hook words checked first), and `smashrun_step2b_data` with every file
the five kinds use (models with jtb / sb / nhb / xmb, motions, animcmd, fs params, effects, sound banks lower case and
capitalised). On it: smashrun_walker_test.py (with the kinds' converted pacs / animcmd) 60 checks,
smashrun_enemy_test.py 26, smashrun_field_test.py 12, training_cpu_test.py, smashrun_menu_test.py's rpx checks,
stage_slot_test.py (NewStage01 + the ten): 0 failures each. The text section no longer recompresses into its slot
in the file, so rpx_patch moves it to the end of the file (73.7 MB instead of 56.5 MB; the section headers point
at it, as for any grown section).

What the 3DS walkers do (enemy_fs.cro, the shared framework read through code.bin's symbols): the AI writes the
move direction into the AI input (`Behavior::move(AiInput*)`, the Wii U 0x026A66D0: stick x = Behavior +0x10, the
direction set_lr 0x026A780C syncs with the posture lr); the enemy kinetic module (acc+0x30E8; change_kinetic
0x02DBE00C) turns the stick into speed with the energy parameters each behaviour's initialize writes at
`[[[acc+0x3130]+8]+0]+4` (+8..+0x44; mczakostalfos writes the same offsets as the 3DS stalfos). Walk: kinetic 1
(Kuribo 0xA), ground attach on (GroundModule acc+0x30DC: set_attach_ground 0x02C37C6C, is_touch 0x02C38A24, 8 =
on the ground, 2 / 4 = wall left / right), the walk loop; off the ground -> fall (kinetic 8); wall (check_wall
0x026A68E4) or ledge (check_cliff_lr 0x026A6D88 with the posture lr [acc+0x311C]+0x60) -> turn; the Turn motion,
then reverse_lr (slot 50 0x026A7A20) after it ends; every so often get_nearest_target 0x026A7008 +
check_turn_to_target 0x026A6984. Death: the framework's notify_on_damage calls change_state_interrupt(slot 67);
that state plays the Damage pose at rate 0 and calls bullet() 0x02DB5158 (the defeated enemy flies off), then
removes itself (EnemyManager remove_enemy_by_id). These Wii U addresses come from aligning the 3DS stalfos / zima
state functions with the Wii U mczako ones (call sequences, 20+ votes for each module call used).

BehaviorImpl, as the Wii U builds it (zima's create 0x026D65EC): Behavior ctor 0x02DB2DF0(this, acc, kind,
variation) fills up to +0xE0; then +0xE0 vptr, +0xE4 common state 0, +0xE8 PMF common_state_func (0x102FDBCC: {0,
-1, 0x0269FDFC}), +0xF0 / +0xF8 the state's update / exit PMFs, +0x100 / +0x108 / +0x110 pending update / enter /
exit, +0x120 1, +0x15C -1, size 0x168. A PMF is {s16 delta, s16 vindex (-1: fn direct, 0: none), fn}. The state
table rows are {enter, update, exit} (0x18 bytes). Slot 72 change_state(id) passes them to change_state_base
0x026A3A44 (pending: common_state_func calls the old exit and swaps at the end of the frame, the enter at the start
of the next), slot 73 to change_state_interrupt_base 0x026A3AD4 (exit, enter now); both reset +0xE8 to
common_state_func and call set_attack_data(id) (slot 45). Slots 64 / 65 / 66 / 67 give the states the framework
returns to after damage on the ground / in the air / by default, and the death state. set_motion_label 0x02DB5B08
only stores the script hashset table at +0xA8 (12 bytes per motion: crc32 of name.init / name / name.exit, lower
case; the 3DS tables are exactly these); change_motion_state 0x02DB420C(this, index, f1 start frame, f2 rate, r5
loop, f3) runs the hashset's scripts and MotionModule::change_motion. GHS vtables: slot k's fn at +0xC + 8k
(BehaviorImpl 0x1008AEBC: 74 slots, 72 / 73 pure).

The cave (0x04B86800-0x04B88000, the rest of the space smashrun_enemy_cave.py clears; code to 0x04B87178, data
0x04B87180-0x04B87E74):
- Factory: 0x02DB951C `cmplwi r12, 0x10` (after 2a's hook at 0x02DB9518, which branches out for its kinds) -> for
  the walker kinds module+8 = create(module+4, K, variation), then the factory's epilogue; any other kind runs the
  instruction and goes on. create: operator new 0x03374578(0x170), the Behavior ctor, BehaviorImpl's init as zima's,
  vptr VT, +0x168 the kind's CFG, set_motion_label, set_damage_motion_label 0x02DB5AD8 (the nine indices of the
  kind's 3DS create: DamageStart, DamageFly, DamageFall, DownBound, DownBound, DownLoop, DownBoundEnd, DownWait,
  Fall / Jump).
- VT: BehaviorImpl's 74 slots (dtor, update = the +0xE8 PMF, damage / capture / death kept) + 74 / 75; overrides 12
  (zima's 0x026D6E18: the gl entry's capture motion, generic), 38 (zima's: 1, flip the model with lr, as every 3DS
  behaviour), 40 initialize, 41 start, 45 set_attack_data, 64-67 (zima's: 3 / 1 / 1 / 6), 72-75 change_state.
- States: 1 FALL, 2 LANDING, 3 WALK, 4 TURN, 6 DEAD (update zima's 0x026D7A94), 7 REMOVE (zima's 0x026D7B58 /
  0x026D7B6C); other ids -> FALL. WALK: stick (lr, 0); off the ground FALL; every 30 frames turn when the nearest
  target is more than 20 units behind; wall / ledge ahead -> TURN. TURN: kinetic 0, the Turn motion (Goomba:
  RunTurnL), reverse_lr(1, 1) at its end, WALK.
- initialize: the kind's energy words (Unicorn runs of each kind's 3DS initialize on its fs vl, variation 0), and
  the kinetic module's vt+0xFC(0x20000004) for Goomba / Shy Guy as theirs. start: set_rhombus 0x026A65BC, +0x10 =
  posture lr, +0x14 / +0x18 = 0, face the nearest target, FALL.
- set_attack_data(state): clear_all 0x02C08324 (acc+0x30C8), then in WALK / TURN the kind's contact attack (a 3DS
  InnerEnemyAttackParam, 42 words: create_attack_data 0x02DB572C reads +0xC node (u16), +0x10 power, +0x14 angle,
  +0x18 kbg, +0x1C fkb, +0x20 bkb, +0x24 size, +0x28.. offset; set_attack 0x02C086A8(module, id, part,
  this+0x1C)). BehaviorImpl's own reads [param slot]+0x30 / +0x34, the aliased twin's list keyed by its state ids,
  so it is replaced. Goomba: its charge bump (power 1, angle 100, fixed 80, node 4); Shy Guy: its bump (power 1,
  angle 50, fixed 60, node 0); Waddle Dee / Waddle Doo / Churine have only their "bullet" attack on the 3DS (no
  contact damage while walking there), so they get Shy Guy's bump (node 0).
- Tables: 0x02D9A46C `cmpwi r0, 1` (after 2a's) -> on a Smash Run stage motion data set table 0x10352610[K] = K's
  set. Slots: 0x02D9A618 `lwz r0, 0x5EC(r28)` (after 2a's slot copy) -> on a Smash Run stage slot[K] = slot[0x5A]
  (mczakozima; the walker reads no tuning from it).
- Kinds (name table index): Goomba kuribo 0x01, Shy Guy heiho 0x0B, Waddle Dee 0x13, Waddle Doo 0x19, Churine 0x1F:
  plain ground walkers on the 3DS (walk / turn / fall / landing states with move, check_wall, check_cliff) with the
  full damage set. Togemet walks along walls (EnemyGroundLineTrace), Togezo has no damage motions: left out.

Motion data sets: the game's layout is {entries*, count, 4 zero words, entries {hash, flags}} (the mczako sets'
entries start at +0x18; there is no hashset block in the set: step 2a's sets carry 12 x count unused bytes there,
harmless). K's set is its 3DS motion_data_set_<name> in its own order, hash crc32(stem, 0xFFFFFFFF), flags the 3DS
word >> 16 (the twins' 0x10000 / 0x50000 / 0x400000 are 1 / 5 / 0x40 on the Wii U). Every entry is an OMO of the
kind's converted pac, and Goomba's / Shy Guy's / Churine's animcmd scripts (effect.bin, sound.bin, attack.bin) all
hash into their hashsets (checked).

Field cave set "walkers" (default; `--set smashrun` builds 2a's): Plasma Wisp, Goomba, Darios, Shy Guy, Stalfos,
Waddle Dee, Zima, Waddle Doo, Churine in turn (placement 1 for the walkers), one every 150 frames, at most 6 alive;
requests the nine + 0x57. The turn counter now wraps at the set's size.

Not verified (only Unicorn so far): the kinetic energy fields' meaning (copied from each kind's 3DS initialize,
not understood: walking speed could be off, or 0 if kinetic 1 / 0xA read other fields on the Wii U); whether the
turn animations (3DS: lr flipped after the Turn motion) look right with the Wii U model flip (slot 38 = 1 calls
MotionModule 0x02C6108C -> 0x0331910C, flags at model +0x10C and [[model+0x1C]+0xA0]+0xC; whether flipped poses
read the unconverted model.flp mirror table at model +0x48 / +0x4C was not traced); the contact attacks' node
indices (joint table indices, the converted model.jtb); the bullet death flight with the kinds' gl entries;
memory with ten kinds' resources on the field (the request loads model, motion, animcmd, sound, effect per kind);
that nothing else reads the aliased zima slot in a kind-specific way for these kinds.

## Fix v3: facing, mesh visibility, death effect (and Plasma Wisp's laser, open)

From the user's first Step 2b test (Cemu): the walkers spawn and walk; some enemies face the wrong way (Waddle Dee
seen from behind, a Goomba side-on / three-quarter), Waddle Dee shows three parasols, Waddle Doo every eye state at
once, defeated enemies vanish without an effect, and Plasma Wisp's laser no longer shows. Package smashrun_fix_v3:
the executable (the full chain: base + menu + field + 2a + 2b + these hooks) and per-motion visibility for every
converted enemy that switches meshes by code. Tests on it: smashrun_walker_test.py 63, s3ds_enemy_vis_test.py
(29 kinds), smashrun_enemy_test.py 26, smashrun_field_test.py 12, training_cpu_test.py, smashrun_menu_test.py's rpx
checks, stage_slot_test.py: 0 failures each; the `--keep-flip` variant's walker test too.

**Facing.** The model's rotation is posture +0x64 = lr x 90 (degrees), written only by set_lr 0x026A780C /
reverse_lr 0x026A7A20 (the same code on the 3DS, Behavior::set_lr 0x7B5778); posture +0x60 is the lr. Both also
flip the motion (MotionModule 0x02C6108C -> 0x0331910C: model +0x10C, anim +0xC; the bone getter 0x0331915C and the
joint remap 0x033117B4 then use the mirror data) when the behaviour's slot 38 returns 1. On the 3DS slot 38 returns
1 for the kinds whose model has a model.flp (FLIP v1, little-endian: u16 bone, pair, param, mode, lr flag, 0 per
entry; modes 3 TransN / RotN, 1 / 2 / 4 the hip, 7 the paired limbs): 33 of the 34 with one, 41 of the 43 without
return 0 (stalfos, heiho... do not flip). The converted models have no flp (the Wii U's FLIP is v1.1, big-endian,
another entry layout: Squirtle's lists only hip entries), so a flipped enemy's skeleton is mirrored without its
table: the hip's odd bind rotations (Goomba HipN x pi, z pi/2) come out turned. The bind poses and animations are
fine (the 3DS models face +Z like the Wii U fighters: arms at +-X, eyes at +Z; no root rotation in the walks; jtb
starts TransN, RotN). Fix: slot 38 = 0 for the Smash Run kinds (the walker's own; the twins' vtable words ->
twin_flip, 1 only for kinds >= 0x50), and initialize_after sets the rotation from the first frame (set_lr(lr, 1, 1)),
since nothing else writes it at spawn. Variant `--keep-flip` (code_keepflip/): only the rotation and death fixes, to
tell in game whether the flip is the cause. A converted Wii U FLIP (to keep the flips) is left for later.

**Visibility** (`tools/s3ds_enemy_vis.py`, test `tools/s3ds_enemy_vis_test.py`). 39 enemies list meshes in a
normal.vmt that their 3DS code switches (Behavior::set_mesh_visibility(vmt index, bool) -> the GsbDrawModel's vmt
table, 0x7FB018); none of these meshes has a 3DS visibility animation, and the Wii U (no .vmt) draws them all. The
tool writes motion/enemy/KIND/body/material_anime.pac, one MTA a motion plus default.mta (the Wii U's material
animation names: 0x104290E4 "default.*", 0x10429108 "material_anime.pac"; the converter's Goomba pac has the same
form), constant visibility: the model's own default bit mask, damage / blink / tear / closed-eye meshes hidden, one of
each alternative set (bonkers' hands, shinigami's faces, darknut's swords), the damage meshes shown and the normal
ones hidden in Damage* / Down* / Collapses; per the 3DS code: Waddle Dee both arms, no parasol, the normal face
(0x5D04C; the parasol variations' one parasol follows lr per frame: not done), Waddle Doo the open eyes, no blink, no
tear. 29 kinds (the Wii U's own kinds and the overlap ones, kamek / shinigami / tac, left out; koshinigami's vmt
names meshes its model lacks).

**Death effect.** Defeat: notify_on_damage 0x026A3564 -> change_state_interrupt(slot 67) (the death flight:
bullet()) -> the remove state -> remove_enemy_by_id 0x02D9C0E0 -> 0x02D9A1B0(type 0) -> the Enemy's removal
0x02D8BE78 -> notify_on_remove 0x02DB40E4(type): 0 / 2 -> 0x02DB3574 (category sm: only kinds 0x57-0x5A with
+0x9C set; the minions' appear / vanish effect 0x0752001E, sound 0x08EB001A), 3 / 4 -> 0x02DB3AB0, the defeat
effect 0x08000033 scaled by the common param +0x5C x the gl entry's +0x20 (the "scales with their size" effect),
sound 0x124, the dead-item check. No Wii U caller passes 3 or 4 (the manager's updates pass 1 and 5); the step 1
minions never died outside the Fortress (their sm HP). Fix: for kinds < 0x50 type 0 becomes 3.

**Plasma Wisp's laser (open).** The twin's code requests its effects from group 0x757 (0x700 + mczakoplasmawisp,
the Wii U's own effect file the field cave loads with kind 0x57) at joint 3 (the jtb: RHandN) through
request_follow_effect (0x026A9584 / 0x026A95F8); with sb / nhb the bone getter 0x0331915C walks the helper
object's list and falls back to the plain matrix, which looks right. What fix v2 changed for the model is sb / nhb
/ xmb; the decisive experiment: delete data/model/enemy/plasmawisp/body/c00/model.xmb (the body draws black) and see
whether the laser returns.

Not verified: that the Wii U plays material_anime.pac for enemies (the Goomba's damage face switching on a hit is
the same mechanism: check it); the defeat path's sound / item drop for the Smash Run kinds' gl entries.

## Fix v4: mesh visibility in the models (facing kept as in v3)

User test of fix v3 (Cemu): the defeat effect plays (star burst + debris); Stalfos faces sideways and animates;
code_keepflip looks wrong (so the no-flip build stays); the Goomba faces the camera, which a 3DS screenshot shows is
right for it; but the material_anime.pac files did nothing: Waddle Doo's eye pieces and the Goomba's two faces stayed
(and the Goomba's converted per-motion face pac never played either). The enemy resource request
(0x030BC6BC: model/enemy/%s/body/c00/, motion/enemy/%s/body/, effect/, animcmd/, sound) loads the motion folder, but
nothing shows enemies playing its material_anime.pac.

Package smashrun_fix_v4: the same executable as fix v3's main build (rebuilt, identical: sha1 efd12dab…; tests as
v3) and `smashrun_fix_v4_data`: model/enemy/KIND/body/c00/model.nud for 18 kinds with their default-hidden meshes
drawn as nothing (`tools/s3ds_enemy_vis.py S3DS_ENEMY_ROOT --nud CONVERTED_ROOT OUT`: those meshes' polygon indices
zeroed, nud.hidden's way; the meshes, materials and bones stay). Hidden: the vmt meshes model_states() hides (see
Fix v3; Waddle Dee's three parasols and damage face, Waddle Doo's blinks and tear, Darios's shoot, Pooka / Shandera /
Chappy / Ghos / Tikibuzz / Monoeye's damage or other eye states, bonkers' extra hands, darknut's second sword, jugem's
cloud / pipe / spare arm, bokkuncannon's beam / missile, dafune's shot) and, for the kinds whose converted
material_anime.pac has a default.mta (kuribo, dekakuribo, keronpa), the meshes it hides (their damage faces).
Test: `tools/s3ds_enemy_vis_test.py ... NUD_OUT` (same size, hidden meshes' indices all zero, every other mesh's
indices unchanged; 18 NUDs, 0 failures).

What this can't do: switch meshes by state (the damage faces, blinks, Waddle Dee's parasol, Darios's shot), and the
3DS material animations (the Goomba's face animation). Both need a Wii U path that plays mesh visibility / material
animation on an enemy: the motion module's material_anime.pac (not played for enemies, as it turned out), the
model's model.mta (loaded by the model loader 0x03303140 for every model; whether it plays for enemies is untested:
Shy Guy's converted model.mta, a UV scroll, would show it), or a mesh-visibility call from the behaviour (the
fighters' VisibilityModule is MSC module 39; the enemy accessor's modules have no such call found yet).

Facing: kept as in fix v3. The 3DS walkers (and twins) set their yaw only through reverse_lr(1, 1) in their turn and
start code (posture +0x64 = lr x 90); fix v3's initialize_after set_lr(lr, 1, 1) gives the same yaw from the first
frame. The Goomba's own model / walk then faces the camera, as on the 3DS. What still differs from the 3DS: the
kinds that flip on the 3DS (model.flp: kuribo, waddledee, waddledoo, zima, plasmawisp, darios, ...) don't mirror
when facing right; a converted Wii U FLIP (its parser not yet found: the bone getter 0x0331915C reads a per-bone mode
list {mode, flags, bone} and the joint remap 0x033117B4 a pair list from the model's helper object) would restore
that. The Goomba's walk plays WalkL at 0.6 (the 3DS walk enter writes 0.6 into the motion module's rate, 3DS +0x50:
MotionModuleImpl::change_motion stores the rate there).

## Fix v5: the five walkers' own 3DS behaviours (state tables per kind)

User report on fix v4: most 3DS walkers have no hitbox while walking, but the Goomba has one while it runs; asked for
each enemy as the 3DS has it. The generic walker (one walk / turn / fall machine, Shy Guy's bump on every kind while
walking or turning) is replaced by each kind's own state table, numbered as its 3DS table, each state written from the
3DS enter / update (enemy_fs.cro, the tables behind each Behavior's slot 72 / 73), with the same transitions,
conditions and vl values. `tools/smashrun_walker_cave.py` (docstring: every state per kind), test
`tools/smashrun_walker_test.py` (92 checks: the factory, vtable, slots 64-67 per kind, change_state per table,
initialize / start / set_attack_data, each kind's state sequences in a stubbed world). Package smashrun_fix_v5.

How the 3DS walkers work (what was read): every kind's state functions call the shared Behavior API (search_target,
check_cliff, check_wall, reverse_lr, change_motion_state, change_kinetic, set_kinetic_jump, random_range, ...); the
tuning comes from the kind's param struct in EnemyParamAccessor (slot [K]: +0xC the vl's first group, +0x20 the
search groups {type, interval, 5 floats}, +0x34 the attack list, from +0x48 the kind's own group inline). Contact
damage is Behavior::set_attack_data(state), called by change_state_base: it arms the vl attack entries whose first
value is the new state. The five vl files list: Kuribo 5 (run) and 9 (death), Shy Guy 9 (run) and 15 (death),
Waddle Dee 7, Waddle Doo 10, Churine 8 (their deaths). So on the 3DS only the Goomba's and the Shy Guy's runs hurt;
walking never does; every defeated body carries a "bullet" attack while it flies.

- Kuribo: walk (WalkL at 0.6, the walk animation's movement), every 100 frames a search box ahead ({2, 100, 40, 10,
  10}); found: face it, a startled hop back (E+0x20 = -0.4, kinetic 5, RunHoldL), 30 frames, then the run (RunL,
  hitbox on) for 110 frames with a search every 60 (a target behind: the run turn RunTurnL and back to the run),
  walls turn it, then RunBrakeL and back to walking. Walls reverse the walk at once (no Turn motion); variation 0
  walks off ledges (variation 1 turns).
- Shy Guy: walk (60-120 frames) and wait (Wait twice, 50 % turn) alternate, a search every 30 frames; found: face it,
  two hops in place (set_kinetic_jump(0, 2.0)), then the run (kinetic 3, hitbox on, 80 frames, the run turn when the
  target is behind), RunBrake, a settle (kinetic 21) and walk; a wall in the walk makes it hop (and turn if it lands at
  the same height), in the run it turns.
- Waddle Dee: walks (Walk at 1.2), every 100 frames a 50 % jump, walls 50 % jump / 50 % turn; variations 0 / 1 carry
  the parasol: they start in the parasol fall and fall back into it from a jump's apex or a ledge. Never chases.
- Waddle Doo: walks, turns to face a target found behind (search every 60 frames), hops at walls.
- Churine: walks, hops at walls (turns if it lands at the same height), turns at ledges.

Not ported: Waddle Doo's beam (states 7 / 8: it needs its beam article; no Wii U weapon kind exists for it), its
random hop and leave timer (their param offsets in its struct were not pinned down), Churine's sleep powder (6 / 7:
an attack with its own effect data); the Waddle Dee's parasol float (the 3DS embeds an EnemyAerialModule in the
behaviour: the parasol fall here is the normal fall kinetic with the ParasolFall motion, so it drops faster than on
the 3DS); sounds; per-state mesh visibility (no Wii U path; the fix v4 NUD baseline stands); ray_check in the hops
(check_wall stands in); check_cliff_distance_lr in the Kuribo's hop (it hops back even at a ledge); variations 1-3's
rows (the spawner always makes variation 0). Inferred from the vl order (not from code): Waddle Dee 100 / 50 / 50 /
1.2, Shy Guy's run-turn rate 0.7 and hop height 1.0; Waddle Doo's hop height is a guess (1.0). set_kinetic_jump's
second kick (the 3DS's vt+0x74 for its flag) uses the initialize kick (vt+0xFC = 3DS +0x7C).

Space: the code no longer fits 0x04B86800-0x04B88000, so it also uses 0x04B89000-0x04B8A000 (zero and unreferenced
between base_effects_cave.py and base_customs_cave.py) and 0x04BB8000-0x04BB8660 (grow:0x04BB8660, after
weapon_expand.py's 0x04BB8000, below the text region's end 0x04BB8670). Calls into 0x026Axxxx go through ctr (beyond a
branch's reach from the cave).

## Fix v6: the Goomba's stomp (stepped on -> Collapses)

User result of fix v5: the five walkers work as intended; but a Goomba can't be jumped on for its squash. On the 3DS
a fighter's footstool on an enemy reaches the behaviour's slot 21; BehaviorImpl's is a nop, Kuribo's (0x32944)
interrupts to state 8: kinetic 0, Collapses, ground on, `BehaviorImpl::notify_on_death` (death flag, hit off,
attacks cleared: the Goomba dies whatever its HP), play_se 0x28D0004; on state frame p+0x38 (1)
`create_dead_item(1, 10)` (kill count, item drop); at the motion's end state 10 (remove). The stomped enemy takes no
damage path and gives none; the fighter's bounce is the fighter's own footstool jump. The enemies' tread is an
AreaModule area (`Behavior::enable_tread` / `disable_tread`: area 0 on / off; Wii U 0x026A7614 / 0x026A75FC).

The Wii U keeps the receiving path: the Enemy ctor registers an event handler (0x02D8C450, at 0x02D89184); its event
6 (0x02D8C5D4) calls the behaviour module's 0x02DB98F4, which calls behaviour slot 20 (vt+0xAC), then writes a param
float (acc+0x315C vt+0x44 with 0x11) and a flag into the event for the sender. Slot 20 is the 3DS's slot 21: the
3DS (ARM) vtables have two destructors, so up to slot 28 the 3DS slot is the Wii U's + 1 (3DS 13 capture motion /
Wii U 12, 3DS 28 notify_on_remove / Wii U 27), and zima overrides exactly this slot with its own nop on both
(Wii U 0x026D7C8C, 3DS 0x14A0C). (The spec table's "Wii U k = 3DS k + 1" is the other way round.)

`tools/smashrun_walker_cave.py`: slot 20 -> w_tread (the kind's CFG TREAD state, interrupt; 0 = nothing), Kuribo's
state 8 as the 3DS's (notify_on_death 0x0269FD6C, slot 71); create_dead_item is left to the removal's defeat path
(fix v3: type 3 drops the items), play_se as all sounds not ported. The other four walkers keep the nop, as on the
3DS (Waddle Dee's slot 21 only sets its parasol timer, not ported). Later kinds with a slot-21 reaction: dekakuribo
(add_damage(p+0x3C), then 10 / 11 by its HP), patapata (variations 0 / 1 => 9, else 0x13), tikibuzz, waddledee.
Test: smashrun_walker_test.py 98 checks (slot 20 per kind, the stomp's state sequence). Not run in game; what isn't
known statically: whether the Wii U fighters send the footstool event to these enemies (the sender side and the
enemies' tread area, which comes from data, were not traced). The README's check decides it: a footstool on a Goomba
squashes it (works), bounces without a squash (the reaction is missing: would need debugging), or doesn't bounce
(no tread area / event: a replacement detection in the walker's update would be needed).

## Fix v7: the walkers' own tread areas (the stomp could never happen)

User result of fix v6: no bounce and no reaction, with a footstool or a plain landing. Cause (static): a fighter can
only stomp an enemy whose AreaModule area 0, the tread area (area kind 0xE), is on. The Enemy builds its two areas
from its param slot's table at +0x70 (2 entries {on, node, 4 floats}; 0x02D89860 -> add_area 0x02BFEA2C; entry
layout +1 kind byte 0xE / 9, +0xC node, +0x10.. floats) and turns area i off where entry i's word 0 is 0
(0x02D8A24C), 0x02D8FB98 setting area 0 again from entry 0 later. Nothing enables it in code: the 3DS's
Behavior::enable_tread / disable_tread (Wii U 0x026A7614 / 0x026A75FC) are called only by the few kinds that switch
it, not by Kuribo. The table is the vl's last group: 3DS Kuribo {1, 2, 14, 8, 0, 0} (on), Waddle Dee
{1, 0, 10, 2, 0, 12} (on), Shy Guy / Waddle Doo / Churine off. But step 2b's S2 hook gives the walkers mczakozima's
param slot, whose table has the tread area off ({0, 0, 12, 12, 0, 0}; Stalfos, Plasma Wisp and Darios too: no
Fortress minion is stompable on the Wii U, so none is a reference for the fighter side).

`tools/smashrun_walker_cave.py`: the three reads (0x02D89898 `lwz r10, 0x70(r5)`, 0x02D8A24C `lwz r26, 0x70(r12)`,
0x02D8FB98 `lwz r8, 0x70(r10)`) -> caves that return the walker kind's own table (both areas, its 3DS vl's values),
other kinds their slot's. With the tread area on, the footstool should reach fix v6's slot 20 -> Kuribo state 8.
Not verified statically: the fighter side (which code tests other objects' tread areas when a fighter jumps / lands,
and whether it includes enemies); if a footstool on a Goomba still does nothing, the fighter side ignores enemies on
the Wii U and the walker update has to detect the stomp itself (the design in the fix v7 report). Space: the hooks at
0x04BB8000 (region C); to fit, the state tables start at row 1 and P has five words. Test: smashrun_walker_test.py
109 checks (the three sites per kind, the tables, the game's own area set-up 0x02D89860 run for a Goomba: area 0
kind 0xE, node 2, 14 x 8; for zima's slot: node 0, 12 x 12, then off).

## Fix v8: the stomp detected by the Goomba itself

User result of fix v7: still no bounce and no reaction, from a footstool or a landing. With the walkers' own tread
areas the enemy side is the 3DS's (code.bin 0x756EE0 builds the same two areas: kinds 0xE / 9 from the table at
0xB71C04, entry +4 = 0.0 / 40960.0, as the Wii U's 0x02D89860 does), so the Wii U fighters don't tread on these
enemies; the fighter-side scan (who tests other objects' tread areas, and its object filter) was not found in a cheap
look and stays open. Its own detection instead (`tools/smashrun_walker_cave.py`, docstring "Stomp detection"):
slot 3 (update) -> w_upd before BehaviorImpl's update: for a kind with a TREAD state (Kuribo), each live fighter
(slots 0-3, the fighter table as tools/position_vars_cave.py reads it) whose feet (posture y) cross the Goomba's
tread box top this frame from above, within its half width -> collapses (state 8, fix v6) and the fighter's status
StepJump 0xB3 (the footstool jump; MSC StatusModule(3, 0xB3, 0) as position_vars_cave.py changes a status). The box
is the 3DS area 0 (node 2, 14 x 8) as half width 7, centre the posture y + 2.53 (node 2 in the bind pose), half height
4. Approximations: the box doesn't follow the animation or the model's scale; the fighter's feet are its posture
origin; any fall onto the Goomba stomps (no jump press needed, as a footstool would); StepJump is entered without the
footstool's own set-up (the stepped object's id): if it misbehaves, an upward speed is the fallback.

Space: the hook's frame and loop at 0x04B84900-0x04B84A00 (256 bytes: zero in the base, between stage_omega_cave.py's
LIMIT 0x04B84900 and boot_training_cave.py's CAVE 0x04B84A00, claimed by no tool, no branch, data word or lis / addi
pair in the executable points into it); the per-fighter test after the area hooks in region C. To fit: Waddle Doo's
and Churine's death / remove states renumbered 10 / 11 and 8 / 9 -> 6 / 7 (no empty table rows), the unused search
groups dropped (Waddle Dee, Churine), data placed largest first. The build (sr5/build.py) ends with
`tools/stage_omega_cave.py --revert` (the user's revert of the stage select's Auto Omega: the five game words,
checked against its ORIGINAL; its cave stays, unreferenced). Test: smashrun_walker_test.py 111 checks (the stomp:
a fall onto a walking Goomba -> 8 + StepJump, none beside it, rising, past its bottom, on the first frame, in 8 or
dying, not live, no fighters, above it short of its top, nor on the other four).

User result of fix v8: still no bounce and no reaction (the Phantom glow fix and stage_db_omega_swap.py's stage
select confirmed in the same round). The static path (w_upd's tests, the fighter table, the posture reads) matches
the installed words, so a run-time look: `tools/diag_stomp_cave.py` (temporary, on exe_v10, 0x04BAE000-0x04BAF000;
test `tools/diag_stomp_test.py`, differential against exe_v10 in unicorn) logs `S4STOMP upd` (every 90th w_upd past
its first test: this, state, CFG, TREAD, death state, the fighter table and its count), `S4STOMP near` (a fighter
within 14 of the enemy's x and -6..40 above its posture: fighter y / last y / x, enemy y / x, state; floats as bits)
and `S4STOMP hit` (the stomp taken). Shipped with diag_crumbs_cave.py v3 in one build, exe_diag_v3.

User result with exe_diag_v3b (exe_v10 + the logging, fix v8's stomp words unchanged): stomping on a Goomba works.
(The earlier "no reaction" report was before this build; the stomp diagnostics weren't needed. fix v8 stands.)

User results (after fix v8 / Extended Memory v3): Shy Guy's texture scroll and mirroring look right; Plasma Wisp's
(Lethinium's) laser is still invisible (open, below the next step).

## Step 2c: the White Bear and the Gordo (3DS state code), the fliers' groundwork, Plasma Wisp's laser

`tools/smashrun_walker_cave.py` (two more kinds in its state-table engine, code in a new region E), test
`tools/smashrun_walker_test.py` (147 checks), `tools/smashrun_field_cave.py` set "step2c" (the default: the walkers'
set with the two new kinds). Package smashrun_step2c_v1: exe_v13 = exe_v12 (Extended Memory v3) + only these
regions (word diff below) and `smashrun_step2c_data`. Not yet run in game. Each kind's reading, with the code
addresses read, is in `reference/smashrun_enemy_specs/hand_read.json` (and its .md "Reading").

**White Bear** (Ice Climber, kind 0x40; enemy_fs.cro 0x7E378-0x7F420). Walks (Move, kinetic 1, the initialize
energy +0x10 1.0 / +0x08 0.3 / +0x14 0); a wall or a ledge -> Turn; every random(60, 120) frames a SpecialTurn;
search group 1 (interval 60, box 180 x 140) -> QuakeHold (1.5x) -> the quake jump (QuakeUp: energy +0x24 / +0x2C
1.5, +0x3C 0.1 and the KineticEnergy kick vt+0x74 -> Wii U vt+0xEC, kinetic 5) -> QuakeFall (the current speed into
+0x20 / +0x24, +0x2C 3, +0x3C 1) -> on the ground QuakeLanding (a fall of 180 frames or more lands in the plain
Landing instead); at the landing's end 50 % (then 25 %) to jump again, at most 3 quakes, then a 60-frame search
cool-down. Contact damage: none while alive (its vl attack list has only state 10); the defeated body (state 10:
DamageStart at rate 0, bullet()) hits with P2 entry 0 (power 8, angle 361, kbg 100, bkb 50, size 5, node 2 HipN).
Its one attack on the 3DS, the landing quake, is **not ported**: `Behavior::set_attack_absolute_data(P6)` +
`hit_attack_absolute` (code.bin 0x7B50AC / 0x7B3D28 -> AttackModuleImpl set_absolute / hit_absolute 0x4CBC48) on
the first fighter-manager entry whose situation module reports the ground (power 10, angle 90, kbg 100, bkb 40), an
absolute hit with no range test. The Wii U route found: the enemy's AttackModule (acc+0x30C8) is AttackModuleImpl
(clear_all 0x02C08324, set_abs vtable +0x64 0x02C08A3C, MSC ops 0x2716 set_abs / 0x271D hit_absolute through its
vt+0x334, as the ACMD Throw_Specifier / Throw_Applier handlers 0x02BE6E88 / 0x02BE6FCC call them); not written,
because a wrong absolute hit could hang a fighter and nothing here can test it. Also not ported: the camera quake
(request_quake(7)), the landing effects 0x7400000 (scaled 2.5 x 1.7) / 0x7400001, set_weak_param(5, 2.0), and the
camera test is_in_view_area (CameraModule is_clip_in(true)) before the jump, taken as true. The fall state (1)
uses the walkers' generic one (it waits while the speed's y > 0; the bear's lands on the first ground contact).

**Gordo** (Kirby, kind 0x08; 0x19CB0-0x1A4A8), variation 0 (the spawner's): start = set_rhombus, set_correct(0)
(GroundModule 0x02C36458: the twins' calls with 0 / 5), set_lr(0.0, 1, 1) (lr 0: faces the camera, as the 3DS's),
no turn to a target; state 1 = kinetic -1 (no movement), ground off, Togetoge loop; 3 = remove. Contact damage: yes
in states 1 and 2 (always), P2 entries 0 / 1: power 10, angle 65, kbg 50, fkb 50, bkb 100, size 8, node 3 (Thorn1N).
Never defeated (death state 0, slots 64-66 0; its gl entry: HP 1 with the three flags other enemies set at 0); no
hashsets and no damage labels (its ctor calls neither; the walker's create now skips set_damage_motion_label when
the kind has none). Not ported: the per-frame write of energy 0 (helper 0x65D20: type 0x17, speed (home - position)
x 0.5: kinetic -1 already holds it in place), set_test_coll_stop(1), set_invincible_global(0), variations 1-3
(state 2: along a line / the layout path).

**Spawner**: set "step2c" spawns Gordo, White Bear, Plasma Wisp, Goomba, Darios, Shy Guy, Gordo, Stalfos, White Bear,
Waddle Dee, Zima, Waddle Doo, Churine in turn (Gordo placement 2, as given: it floats where it appears; the bear 1),
requests the twelve kinds + 0x57. Its code now ends below CODE_LIMIT 0x04B7D600.

**Space** (all zero and unreferenced in exe_v12: no branch, data word, lis / D-form pair or relocation into them;
scratch refcheck): region E 0x04B7D600-0x04B7DF00 (the field cave's tail before its DATA; code to 0x04B7D9E8, then
data), and data-only spans 0x04B85980-0x04B85C00 / 0x04B86220-0x04B86800 (smashrun_enemy_cave.py's gaps between its
code, sets and the walker's region A) and 0x04B77E20-0x04B78000 (the original .text end before
position_vars_cave.py's 0x04B78000). The engine's data blocks are placed largest first across all regions (two
spans are still empty). **exe_v13 vs exe_v12, word diff** (text; data / rodata sections and relocations equal):
0x02D9A618 (S2 hook), 0x02D9B6F8 (field hook D), 0x04B7D16C-0x04B7D480 (field cave code), 0x04B7D600-0x04B7DEF8
(E), 0x04B849C0-0x04B84A00 (D's tail: data), 0x04B85980-0x04B85BA4 (data), 0x04B86918-0x04B87FF4 (A),
0x04B89020-0x04B8A000 (B), 0x04BB8000-0x04BB8008 and 0x04BB8180-0x04BB8660 (C): 2954 words.

Tests on exe_v13: smashrun_walker_test.py 147 checks (the White Bear's 3DS state sequences: the search on the frame
its counter passes 60, the quake jump's energy and kick, the fall / landing / repeat chances over 40 and 60 seeded
runs, the cool-down, special turn, walls / ledges, the long fall; the Gordo's start, state 1 and attacks; every
existing check), smashrun_field_test.py 12, smashrun_enemy_test.py 26 (its space check leaves the walker's data
spans to the walker test), s3ds_enemy_test.py whitebear / gordo: 0 failures each.

**The fliers' groundwork** (ghos, tikibuzz, furiijio, propellerheiho: all fly with an EnemyAerialModuleImpl embedded
in the behaviour, 3DS object +0x168): the Wii U keeps a reduced EnemyAerialModuleImpl for mczakoplasmawisp (embedded
at +0x168 of its 0x210-byte object): ctor 0x02DB2C44(this, acc) (0x74 bytes; energies 0 / 1 from KineticModule
get_energy 0x02C4FE9C at +4 / +8), set_mode_homing (mode 2) 0x02DB28E4(f1-f6), set_mode_slip_homing (mode 3)
0x02DB2A48, a 4-float mode 6 0x02DB2A7C, set_max_speed 0x02DB2BB4, set_current_speed(Vector2&) 0x02DB2BC0,
set_target_point 0x02DB2BE4, get_distance 0x02DB2C08, update() 0x02DB28C8 -> update(0, 0, true) 0x02DB2524 (mode
word +0xC: modes 0-4 and 6; the 3DS's 5 is absent, -1 = none does nothing), the target from a fighter id +0x30 when
+0x2C is 0 (0x02DB1EFC = the 3DS's 0x5F593C: set_target(id, offset) is three stores). The energy layout differs
from the 3DS's by the vtable's place: 3DS offsets below 0x20 are 4 lower on the Wii U (enable byte +0x1C -> +0x18,
speed +4 -> +0), from 0x20 the same, the vtable at +0x1C (3DS vt+0xC -> Wii U vt+0x1C). GroundModule
set_passable_check is 0x02C367C4. Missing for parity: Ghos's damage path (slot 69 -> its stun state 2 with
hit_return_frame; the Wii U notify_on_damage 0x026A3564 does call slot 69 and skips its own reaction when it returns
non-zero), its common leave (init / update_common_leave), its bounce off walls (GroundCollisionObject
get_ground_normal) and its hitbox node 3, which its 3-entry jtb lacks; Tiki Buzz's homing_extend / uniform / braking
modes (not in the Wii U's update). Not ported in this step.

**Plasma Wisp's laser (static finding)**: the twin's article set-up callbacks (article table 0x102FE844: needle
0x026CF644, large needle 0x026CF7F8, laser 0x026CF9B0, hadoudan 0x026CFB08) place each weapon at a node of the
owner's model: ModelModule (acc+0x3118) node position 0x0200739C(module, node, &pos, 1) with node **5** for the
needles and the laser (node 3 for the hadoudan), then add the twin's param offsets (slot[0x57] +0xC0 x lr, +0xC4).
The 3DS code does the same (enemy_fs.cro 0x895A4: node_global_position(5)). The converted Plasma Wisp's model.jtb
(the 3DS file) has 5 nodes, 0-4 (bones 0, 1, 2, 4, 3): node 5 is past its end. The node -> bone step is the motion
module's callback at +0x20 with the jtb (model handle +0xC) (0x02C64588 -> 0x0331915C); for a bone index past the
skeleton the 3DS's MotionModuleImpl::get_world_matrix (0x501468) returns the identity matrix (the stage origin);
how the Wii U callback treats a node past the table (bounds check or the next bytes in memory) was not traced. So
the laser (and the needles) most likely spawn far from the wisp (at the origin or a garbage bone). The step 2c data
adds the check: `model/enemy/plasmawisp/body/c00/model.jtb` with a sixth node, 5 -> bone 2 (BodyN, the body's
centre). If the laser (and needles) then come out of the wisp, this was the cause; if not, the next suspects are the
weapons' own effect / model resources (the Wii U's mczakoplasmawisp weapons, loaded with kind 0x57).

## Plan (to refine once code.bin is in)

1. Data (names decoded): convert Smash Run's enemies, field, final-battle stages, UI, params. Done: enemies,
   their effects and effect models, the stages (also in their own slots), the UI and the mode's params (above).
2. Code: map the 3DS symbols onto the Wii U's leftover code (the same `app::` classes; names give the Wii U
   functions through string / structure matches); find what of FieldSmashManager / EnemyGenerator the Wii U
   still has.
3. Formats: 3DS models / motions / textures to Wii U (NUD / OMO / NUT), effects, sounds.
4. Mode: a menu entry, the character select and power setup, the 5-minute field, the final battle, results.
5. Split screen: the Wii U renders one camera; 4 viewports is engine work (cameras, HUD per player, culling).
