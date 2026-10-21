# Minecraft World (Smash Ultimate) on NewStage01

Status: **loads in game (v5, v6: user), normal play and Omega**; stage code moves rigged
collision (moving-platform test, user). v7 in game (user): camera and the island's front good;
sky white, backdrop low-res, houses / trees / back blocks dark. v8 and v9 (below) not tested yet.
v1-v4 froze while loading their models (see "Freeze"); v5 uses only forms Battlefield's own loaded
models have. The whole normal-play stage (not the Battlefield form) converted
from Ultimate's `stage/pickel_world` (the user's dump, with its `param` folders) into the
`NewStage01` slot (`docs/stage-expansion.md`), normal play and Omega, with Ultimate's own collision,
spawns, camera, blast zones, item areas and breakable-block layouts.

Build:

    python3 tools/minecraft_world.py SRC BASE OUT [--biome plains] [--hazards on|off] \
        --yamlvd PATH/yamlvd --labels PATH/ParamLabels.csv

SRC is the dumped `stage/pickel_world` folder (`normal/` and `battle/`, each with `model/`,
`param/`, ...), BASE holds the slot's current `melee/NewStage01` and `end/NewStage01` (the Battlefield
copy), OUT gets `stage/melee/NewStage01` and `stage/end/NewStage01`. Ultimate's `.lvd` is read with
lvd-rs' `yamlvd` (github.com/ultimate-research/lvd-rs, `cargo build --release`), its `.stdat`
params with pyprc (`pip install pyprc`) and ultimate-research/param-labels' `ParamLabels.csv`.

Deliverables (git-ignored `build/`):
- `minecraft_world.zip`: both stage folders (Plains, hazards on) and the stage-select pictures
  (`ui/...`, same files / texture IDs / formats as `new_stage_pictures.zip`): Ultimate's own preview
  (`stage_2_pickel_world`) in the preview, tiles and icons, the "MINECRAFT" logo in the series logo
  (`stagel_10`: red = the logo's fill, green = its silhouette, as the Smash Bros. logo there) and a
  "Minecraft World" name banner.
- `minecraft_world_biomes.zip`: every other biome / hazards combination (`<biome>_hazards_on|off`):
  the three model folders and `NewStage0100.lvd` that differ; copy one over `stage/melee/NewStage01`.
- `moving_platform_test.zip`: the moving-platform test (below) on v6, with its RPX.
- `minecraft_world_tests.zip` (v5): the first moving-platform test and the freeze bisect
  (`1_battlefield_hidden`: Battlefield's NewStage01 with every model hidden; `2_ring_only` /
  `3_backdrop_only` / `4_sky_only`: one v5 folder each), not needed since v5 loaded.

## Ultimate's files

- `normal/model`: per biome a `ring_<biome>_set` (the island: terrain, village, trees, under-side),
  `far_<biome>_set` (the panorama: a 3200x1600 texture on a ~8800-unit bowl), `platform_<biome>_set`
  (the pass-through plates), doors, Plains' farm, mobs (rigged and animated; not ported), `ink_*`
  (Splatoon-ink decals), `lightboard_*` (a lighting duplicate of the ring), and a model per block
  kind (`bg_b_<model>_set`, a 10-unit cube). `far_common_set`: sky dome, clouds, sun, moon, stars.
  `pickel_world_visual.stdat` lists each biome's models (biome order: 0 Plains, 1 Birch Forest,
  2 Savanna, 3 Taiga, 4 Snowy Tundra, 5 Stone Shore).
- `normal/param`: `pickel_world_NN.lvd` (biome NN) and `pickel_world_NN_gimmick_off.lvd` (hazards off:
  no breakable blocks, spawns on the ground); `pickel_world_breakable_NN.stdat` (the biome's blocks:
  kind, x, y, z in 10-unit cells, flags); `pickel_world.stdat` (biome odds / limit, day / night /
  monster frames, mob odds, the block table: life and material a kind).
- `battle/`: the Battlefield form (`ring_endbattle_set` + `floating_plate_set`, `pickel_world_battle_00
  .lvd`) and Omega (`ring_endbattle_set`, `pickel_world_end_00.lvd`: +-80, Battlefield-Omega-like;
  `end_l` is a larger +-120 variant, not used).
- No stage code: the biome rotation, breaking / placing blocks, day / night and the mobs are
  Ultimate's executable's.

Ultimate's collision: the ground is one open line (x +-100, top y 0, down to -160) with a material a
10-unit segment and ledges at (+-100, 0); the pass-through floors are separate 10-unit pieces. All
are "dynamic" (`basic_floor_<biome>`, `hidden_floor_*`: moved by the stage code); the port makes
them static. Blast zones +-260 / 180 / -120, camera +-190 / 130 / -60 in every biome.

Breakable blocks: on the fighting plane (z 0) they're solid (the spawns stand on them: Plains on the
hay pile and the house, Birch Forest / Taiga on the leaves), except those with flag 1 (the branch
logs under each pass-through floor). Kinds -> models (`KIND_MODEL`; the files don't name them):
worked out from where each kind sits (trunks / branches / leaves, the Plains house, the Stone Shore
ores, the Snowy Tundra igloo), the block table's materials and lives, and the models: 0 dirt, 1 oak
log (`wood_01`), 2 stone, 3 iron ore, 5 grass block, 9 hay bale, 10 snow (the igloo), 11 cobblestone,
12 mossy cobblestone, 18 oak planks, 21-23 birch log / branch / leaves, 24-26 acacia, 27-29 pine,
35 furnace; 7 (six "soil" blocks in Taiga: dirt) and 33 (two "snow" blocks at the igloo's ends:
blue ice) are guesses. Ultimate's own preview of Plains shows the same hay pile and house.

Scale is 1:1 (Ultimate's Battlefield form sits where Smash 4's Battlefield does: plates x +-59,
top 47 against 59 / 47.3; ledges +-78 / +-80).

## Formats (new tools)

- `tools/nutexb.py`: Ultimate textures. Tegra X1 block-linear deswizzle (64-byte x 8-row GOBs, block
  height from the image height) and RGBA8 / BC1-BC5 decode (reusing `nut.py`'s BC decoders).
- `tools/bntx.py`: Ultimate UI textures (BNTX: BRTI format / size / block height; BC1-BC5, BC7
  through Pillow's DDS reader, RGBA8).
- `tools/nut.py`: `write_ntwu` writes new NTWU textures (GX2 tile mode 4, one mip) as
  Battlefield's: its pitch / size / alignment rule holds for all 626 of Battlefield's textures, and
  rebuilding `stc_moon__set/model.nut` gives the same headers and GX2 surfaces byte for byte.
  `ntp3` (NTP3, untiled) is still there, but the game's loaded models don't use it (below).
- `tools/nud.py`: NUD read / write. Checked by rewriting every static Battlefield model with it:
  byte-identical except the bounding spheres it recomputes (and one unused vertex field).
  `hidden(path)`: the model with its indices zeroed (nothing drawn, everything else unchanged).
- `tools/lvd.py`: Smash 4 LVD read / write (Battlefield's melee and Omega files round-trip
  byte-identical).

## The conversion

- **Models**: every Ultimate mesh becomes a NUD mesh: positions, normals (half float), vertex
  colors from `colorSet1` (Ultimate 0.5 = 1.0 maps to Battlefield's 127 = 1.0; the other color
  sets are shader inputs, e.g. the backdrops' `colorSet5` is a constant 0.33), the first UV set
  (same orientation in both games, checked by rendering Battlefield's own models), triangle lists.
  Meshes under a bone (doors) are moved by the skeleton. The blocks are placed from the breakable
  file (every block, every depth) and merged into one mesh a material.
- **Materials**: the flags (which pick the shader) only as Battlefield's melee models have them,
  with their vertex layout: `0xA4001041` (its ring; lit by the stage's lights), `0xA4011001` (its
  rubble; lit, alpha test >= 128: the block atlas) and `0xA2001001` (its platforms; unlit: texture x
  vertex color). The island is lit (`OPAQUE`, `CUTOUT`, `BLEND`); the panorama, sky dome, clouds
  and sun are unlit (`UNLIT`, `UNLIT_CUTOUT`, `UNLIT_BLEND`), as Ultimate's (their lighting is in the
  texture): v5 lit the panorama and clouds and doubled the sky's vertex colors, and the user saw
  the background "extremely bright". Blending (`1 / 1`: alpha, one minus alpha) and the alpha test
  are GPU states, not shaders, so v6 adds them to `0xA2001001`. Faces Ultimate draws from both
  sides are doubled (reversed copies) except with the alpha test (Battlefield's has culling 0).
  Linear filtering, as all of Battlefield's.
- **Fog** (v7): v6 in game (user's screenshot): the sky white, the backdrop washed out with
  distance, the island greyed. Battlefield's far materials carry their own fog (`NU_fogParams`
  start, end, strength at start / end, e.g. `[36000, 42300, 0.17, 0.44]`, and `NU_fogColor`); ours
  had none, so (read from the result) the stage's default fog, white and full by a few thousand
  units. Now every material has its own: none on the island and the sky, a light blue haze on the
  far backdrop (Ultimate's distant hills).
- **Light**: Battlefield's `animation/light.bin` is its day / night cycle (2401 frames: night at
  0, dawn, midday around 945, sunset around 1400, night again; light colors, directions, fog), which
  the user saw as wrong lighting. `still_light` sets every frame to frame 945 (the most neutral
  white, light from above): same file layout ('LIGH', version 5, frame count, ?, the per-frame
  records' offset; five RGB tracks of 3 bytes a frame; one 1988-byte record a frame). A record: a
  116-byte block for the characters, then one per light set (`model.xmb`'s light set number), each
  4 lights of 28 bytes (enabled, direction of travel, hue, saturation, value; the 4th off, without
  a direction: likely the set's ambient) and 4 bytes; then 16 bytes (a moving position, likely the
  sun). Battlefield's midday set 4 (the island's): a warm main light (V 1.3), a weak blue one and
  a strong blue one from below-front, which tinted the island. v7 sets it from Ultimate's
  `render/light/light00_set.nuanmb` (9000 frames, day at 0): its stage light is white and comes from
  (0.20, 0.90, 0.38) (Battlefield's midday sun is (0.17, 0.90, 0.39), same convention), plus a
  sky light from above, a fill from the camera and a neutral ambient for Ultimate's ambient
  (spherical harmonics, `render/stage_01plains.shpcanim`, not decoded). Its fog, bloom and color
  settings (`render_param.prc`, the light file's `sceneAttributesForShaderFX`) aren't mapped.
- **Camera** (v7): `NAME_stprm.bin` value 6-10 are Battlefield's normal camera (fov 30, distance
  83 / 1000, vertical angle -5, look-down angle -15); Ultimate's `stageparam_pickel_world.stprm` has
  30, 83 / 1000, -5, -22, which v7 uses. The camera area (lvd) is already Ultimate's.
- **Textures**: NTWU, one mip, BC1 (opaque) or BC3, powers of two from 64 to 2048, IDs
  `0x2000F001`... (Battlefield's are `0x2000xxxx` below that). The block atlas (512x512) is 4x larger
  with nearest pixels (2048x2048 BC3): each source pixel is one 4x4 block, exact in BC, and sharp
  under linear filtering. The panorama 2048x1024 BC3.
- **Sky (v8)**: v5-v7's sky folder had the clouds' `model.xmb` (draw range 4); Battlefield uses
  range 4 only for things within ~27000 units (its clouds, grass, neon ring), its sky dome (to
  85000) and backdrops have range 2, so the 47000-unit dome was most likely clipped (the user saw
  white, no clouds). v8 keeps the folder's own xmb (range 2) and puts the gradient in a texture
  (`sky_gradient`, 64x256 RGBA8, by elevation) with the vertex colors at 1.0, in case the unlit
  shader doesn't use vertex colors.
- **Clouds (v8)**: Ultimate moves the three cloud layers (`far_common_set` bones `cloud_model0-2`,
  10.8 units a frame, jumping back; all repeat after 4500 frames). Each layer is in a Battlefield
  `dyr_` folder with one bone at the origin, draw range 2 and no `.mta` (`dyr_i`, `dyr_j`, `dyr_l`),
  bound to it (bind 8, bone 0), with that bone's animation = Ultimate's frames 0-4500 as offsets from
  the rest pose (as the moving platform, which the stage plays). `moving_platform_test.py` uses
  `dyr_j` too (it replaces the middle cloud layer). The unlit shader on a bone-bound mesh isn't in
  Battlefield (its bound meshes are lit); binding should only change the transform.
- **Shaders (v9)**: from Ultimate's `render/shader/nuc2effectlibrary.nufxlb` (the user's
  `render-ssbu.zip`; dumped with ssbh_lib, every program's vertex attributes and material
  parameters): every shader the stage uses reads `colorSet1`. The `SFX_PBS_...4100` / `...4000`
  family has an emission texture (`Texture5`): color = texture x `CustomVector3` x `CustomVector8` x
  `colorSet1` x 2, unlit (the sky, clouds, sun, fog layers, the island's `EmissiveSFX` glowing
  blocks); v9 makes those unlit and takes Ultimate's colors (day: the animation's frame 0) into the
  vertex colors (linear -> gamma 2.2). The sky dome: (0.25, 0.43, 1.0) x its shading, by elevation
  into `sky_gradient`; clouds (0.61, 0.61, 0.62), opaque as Ultimate's (not 70%); the sun x 2.
  `SFX_PBS_52.../53...` (doors, crops, the block models): toon shading (`Texture11` =
  `ToonGradationMap`, material `PointLight_block`), where `colorSet1` drives the lighting.
  Ultimate's own haze replaces v7's material fog: `sky_fog_model`'s `fog_near` ring and the
  panorama's fog layer (`far_fog_<x>_low_col`, white with an alpha ramp, (0.38, 0.62, 1.0)). That
  layer's ramp as read would hide the near hills and clear the horizon, the opposite of Ultimate's
  look, so it's read the other way up, at 80% (`FAR_FOG_ALPHA`); 1% nearer than the panorama, so it
  draws over it.
- **Torches (v9)**: Ultimate's `effect/stage/pickel_world/ef_pickel_world.eff` (the user's
  `effect-ssbu-partial.zip`: EFFN with a VFXB, emitter sets `P_PickelWorldFire` (fire1 + smoke1),
  the mobs', a block-break set per block kind; textures in a BNTX: `tools/bntx.py all`) can't be
  converted (Switch VFXB vs Wii U EFTF, compiled shaders). Its positions are in
  `pickel_world_visual.stdat`'s `torch_info_table` (row = biome, row 6 = the battle / Omega island;
  up to 8, `count`). `--effect PATH` adds, in `dyr_change_160_2_O_OBJ_O_HIR_set` (draw range 0, no
  `.mta`): a quad a flame (`ef_pickelworld_fire00`) and two smoke puffs (`smoke00`'s first frame)
  per torch, each mesh on its own bone (bind 8, bone n) of a made skeleton (`omo.vbn_write`:
  Battlefield's layout, rebuilds its 1-bone file byte for byte; every bone at the origin), animated
  (240 frames: the flame flickering in scale, the smoke rising 7 units and shrinking over 60 frames,
  out of step; a scale about the sprite's centre is a translation c (1 - s) with it).
- **Not animated**: the sun / moon / stars and the day-night cycle (the stage is held at midday).
- **Backdrop resolution (v8)**: the 3200x1600 panorama is two 2048x2048 textures (its halves,
  overlapping by its widest triangle, 6.25% of the width; each triangle on the half its centre is
  in) instead of one 2048x1024.
- **Vertex colors (v8)**: Ultimate's `colorSet1` is Minecraft's corner shading (0.5 = none) on the
  ring and blocks; at full strength the houses, trees and back blocks were too dark (user), so it's
  kept at half (`AO_KEEP`); the `SFX_PBS_52...` shaders (doors, crops) have values near 0 there that
  can't be color (they look lit in Ultimate): 0.5. The island's ambient up to 0.45, sun 0.75.
- **Sky gradient**: Ultimate colors the sky dome in its shader (its vertex colors are only shading), so the
  dome gets a fixed day gradient (Minecraft's day sky, `(0.47, 0.65, 1.0)` at the top, as vertex
  colors at 127 = 1.0). Clouds at 70% opacity (from under the layer they'd hide most of
  the sky). Sun kept; moon, stars and fog layers not.
- **Model folders**: only Battlefield folders without a material animation (`model.mta`) get new
  models: `stc_c_Ring_set` (everything on the block atlas), `stc_k_BG_most_far2` (the panorama),
  `stc_BG_most_far2_1_set` (the sky, with `stc_o_BG_clouds_set`'s `model.xmb`: light set 14, draw
  range 4, order 12). Every other folder keeps all of Battlefield's files with the model hidden
  (`nud.hidden`), so its `.mta` and skeleton still match its model (installing over an old build
  can't remove files, so dropping the `.mta`s as v1-v4 did may leave them beside other models).
- **Omega**: `battle/model/ring_endbattle_set` (the ring the Battlefield form and Omega share) with
  `pickel_world_end_00.lvd`, Plains' panorama and the sky.

## Collision

- Hazards off, and Omega: Ultimate's lines one for one (vertices, normals, a surface kind a line
  from its material name, ledge flags `0x40` / `0x80` from `hang_l` / `hang_r`, the cliffs).
- Hazards on (normal play): the ground's cells (inside its line, closed along its ends) and the
  solid blocks' cells on the plane become one outline per solid region (clockwise, holes dropped,
  a line where the direction or the material changes: the ground's from its own lines, a block's
  from the block table), ledges at the island's outer top corners on 5-unit floor lines as
  Battlefield's. Pass-through floors: Ultimate's pieces joined into lines, left to right.
- Spawns, respawns, camera, blast zones, item areas (every path) and Kirby's points: Ultimate's,
  into Battlefield's entries.

`tools/minecraft_world.py`'s output was checked by rendering every biome from the front with the
collision and spawns drawn on top (all spawns on a floor, blocks and outlines matching), and the
lvds for zero-length lines, unit normals and ledges on their lines.

## Not ported (no stage code to drive it)

Biome rotation (one biome a build; `minecraft_world_biomes.zip` has the others), breaking / placing
blocks (solid scenery), mobs, day / night (the sky is day; the lighting is still Battlefield's, which
may darken over the match), the ink decals, Ultimate's particle effects (Battlefield's effect files
are still in the folder). The `melee.msbt` texts for the slot still say whatever `add_stage.py`
wrote; the stage select shows the name picture.

## To check in game

1. The stage loads and looks like the preview (models, textures, sky; no Battlefield pieces).
2. Standing on the ground and the blocks, the ledges at +-100, the pass-through floors.
3. Omega.
4. Lighting / day-night: if it turns dark or odd, `animation/light.bin` / `render/` are still
   Battlefield's.

## Stage code: what moves stage collision (research, cross_f.rpx)

Ultimate's stage code (biomes, blocks, mobs) is in Ultimate's executable, not in the stage files, so
it would have to be rewritten for Smash 4. What Smash 4 offers for it:

- Collisions are made in `0x03142CC8` (stage base) from each loaded `.lvd`. A collision with the
  **rig flag** (`flag2`, byte 2 of the four flag bytes; runtime word `+0xE8` bit 16) isn't static:
  `0x03142BA4` files it in a **link** named by its **subname** (one link a subname, made by
  `0x0315CF34` in the stage's link manager at `stage + 0x1C8`; the link keeps the start position
  `+0x94`, a joint index `+0xA0` (lvd `unk3`, -1 = none) and a bone name `+0xA4`), then
  `0x0315C7DC` adds the ground to the link's list (`link + 0xEC`). Battlefield's own Omega floor is
  rigged (subname `Ring`) and stays put.
- Links are looked up by model name: `0x03142954(stage, name)` returns the link's ground list
  (a name starting with `dyr_` is retried without it); `0x03142A48` the link's `+0x178` object.
- Moving them is up to the stage's own class: each frame, stage classes call
  `0x0315EF88(grounds, &(x, y), rotation)` (every ground of the link: `0x02D59E40(ground, &pos,
  rot, scale x, scale y)`: position `+4/+8`, rotation `+0x1C`, scale `+0x28/+0x2C`, dirty flag
  `+0x164`), or `0x0315F500` / `0x0315F548` (set / clear a flag on all of them, e.g. on / off).
- The generic stage class new slots get (`StageBaseCafe`, vtable `0x1011D27C`; Omega
  `StageBaseEnd`) never calls these, so rigged collision on NewStage01 stays where the lvd puts it.
  Its update, `0x02D1CF9C(stage, f1 = frame rate)`, calls the base update at `0x02D1CFDC`
  (`bl 0x031415C8`): a hook there can run NewStage01's own code every frame (the stage kind is at
  `stage + 0`: `app::StageManager` (`0x031653F4`) makes the stage, then calls its init, vtable
  (`stage + 0x111C`) `+0x14` = `0x02D1A760`, which copies the manager's settings (`+8`, the kind
  first) to the stage's start and the manager's `+0xF4` (0 / 1 / -1, not the kind) to `+0xCC`;
  other generic stages must be left alone).

So biome rotation can be: every biome's models in `dyr_` model folders whose animations show only
the current biome, every biome's collision rigged under its own subname, and a cave on that hook
counting frames (adding `f1`, as the animations do) that moves the inactive biomes' collision away
(`0x0315EF88`) and the active one into place.

## Moving-platform test

First try (user, `minecraft_world_tests.zip`'s `5_moving_platform`): the hay bales move, their
collision stays a drop-through platform where the lvd puts it. So the stage plays a `dyr_` model's
animation, and the cave didn't move the link: it checked the kind at `stage + 0xCC`, which isn't
the kind (above), so it never ran. Every other step was checked again in the game's code: the
entry's `unk1` (runtime `+0xD4`) is 0, so the collision is filed in the link manager at `+0x1C8`
that the lookup searches (non-zero: `+0x1CC`'s, with `unk2` copied to the link); the short name is
`mctest`; the lookup returns the link's ground list when it isn't empty; `0x02D59E40` sets the
position and the dirty flag. Second try: `build/moving_platform_test.zip`, the kind read at
`stage + 0` (the RPX differs from the first one's in that word only): **works** (user): the
collision follows the bales, you can stand on it as it moves.

`build/moving_platform_test.zip`: the full RPX (the standard build plus
`tools/stage_script_cave.py`) and the files `tools/moving_platform_test.py` adds to the v6 Plains
build (its platform model, animation and lvd). A 3-block hay bale platform circles over the middle of
the island (x -35 to 15, y 38 to 62, a 4-second loop): its model by animation, its drop-through
collision by the cave.

- `tools/stage_script_cave.py`: hooks StageBaseCafe's update (0x02D1CFDC) and setup (0x02D1C65C) as
  above; for kind 0x80 only. `tools/stage_script_test.py PATCHED.rpx` runs it in unicorn with
  stubs (counter reset, base update kept, link looked up by name and moved to `motion(t)` every
  frame, slow motion, other kinds untouched): all ok. The built RPX differs from `full_rpx.zip`'s in
  the two hook words and the new code only.
- The link name: `0x03142954` doesn't compare names with the subname but with a short name taken
  from subnames shaped `NAME__TAG__` (link `+0x48`, made in `0x0315C3EC`; at most 15 characters),
  so the platform's subname is `mctest__move__`.
- The platform is in `dyr_j_BG_most_far0_set` (Battlefield's: one bone, hash `0x181C1749`, an
  animation the stage loops; 1201 frames for a 1200-frame loop), its mesh bound to the bone (bind 8,
  bone 0), its animation 241 frames. The folder's `model.xmb` is the ring's: the xmb's numbers are
  light set, draw range and drawing order (dyr_j: 3 / 2 / 0, the far background; the ring: 4 / 0 /
  15; the backdrop folder `stc_k_BG_most_far2`: 13 / 2 / 0; the sky folder: 14 / 4 / 12).

What the result tells:
- platform moves and you ride it: animations play and the cave moves collision, so biome rotation
  can be built this way;
- platform moves, collision stays (you fall through it / stand on air where it started): the cave
  isn't running or the link isn't found;
- collision moves (you ride something invisible), the platform doesn't: the stage doesn't play the
  animation (the cave would have to move the models too);
- they drift apart over the match: the frame counts differ (loop length or slow motion).

## Music

Ultimate's Minecraft World playlist (`ui_bgm_db.prc`'s `bgmpickel`, the user's `ui-SSBU.zip`): 7
tracks, `stream:/sound/bgm/bgm_mc01_mc_glide` ... `bgm_mc07_mc_danceoftheblocks` (`.nus3audio`,
the user's `stream-ssbu.zip`). `tools/nus3audio_opus.py` decodes them (Namco OPUS header + Switch
Opus, libopus; 48 kHz stereo, loop points from the header). `tools/minecraft_music.py` adds them to
Smash 4 the way Sm4shMusic adds songs (nothing replaced; `build/minecraft_music.zip`):

- **Banks** `sound/bgm/snd_bgm_MC0n_<Title>.nus3bank`: a copy of Battlefield's
  (`snd_bgm_CRS02_Senjyou`; the writer rebuilds it byte for byte) with the name in BINF / TONE, a
  new BINF id (unique per bank: the game's 730 go up to 6136; ours 6200+), TONE's pack size, volume
  (Battlefield's 4.6: the tracks are as loud, -14 dB RMS) and stream info (rate, channels, samples,
  loop start / end, loop flag at its end), and an IDSP in PACK: big-endian, `IDSP`, 0, channels,
  rate, samples, loop start, loop end, interleave 0x10, header 0x40, header size 0x60, data 0x100,
  data size per channel; a standard 0x60-byte DSP header per channel (loop context = the decoded
  samples before the loop); the channels' DSP-ADPCM interleaved every 0x10 bytes. Every Smash 4 BGM
  is 47999 Hz (0xBB7F); so are ours (48000 Hz sources, 0.002% slower). Encoder: `tools/dspadpcm`
  (jackoalan's gc-dspadpcm-encode, MIT); 36-40 dB SNR against the decoded Opus.
- **`sound/config/bgm_property.mpb`** (`MPB\0`, 6, count 1983, offsets or -1, 0x74-byte entries:
  name 0x3C, 4 ints, 4 menu check points, loop start / end ms, loop start / end samples, total ms /
  samples, all at 47999 Hz): BGM ids 1-7 (Sm4shMusic's choice: the lowest free ones; the game's
  start at 17), each naming its file. The game's own entries leave the name empty and use its table.
- **`param/ui/ui_sound_db.bin`**: sounds 600-606 (copies of Battlefield's, label `SOUND<id + 1>`,
  Sound Test order 999 like Sm4shMusic, mix 3 = new remix, 0 for Clockwork Crafter which Ultimate
  credits as Mojang's own), and NewStage01's (0x38) song list set to them in Ultimate's order.
- **`ui/message/sound.msbt`**: the unmodified one + `MsndN_` / `MsndN2_` (title), `MsndS_`
  (source game), `MsndW_` (staff) and `MsndO_` (copyright) for each, Ultimate's texts
  (`msg_bgm.msbt`). The user's modified copy had been re-saved by Sm4shMusic, which relabels every
  song in base 36 (`SOUND1A`), not matching the vanilla ui_sound_db's labels.
- **My Music** (which song plays in a match, with what odds): `sound/config/bgm_mymusic.mmb`
  (`MMB\0`, 4, count 94, offsets, then per group a 0x20-byte name, a count and 0x3C-byte entries:
  BGM id, index, -1, rarity, -1, ...). The game finds a stage's group by its stage-kind name
  (`BattleField_f`, `Galaxy`, ...; Omega shares it; NewStage01's is `NewStage01`), but names the
  groups from its own 94-name table (`0x1041CE18`, loader `0x0311CD6C`), unless `0x02A7BA48` (a
  stub returning 0) says to take the name fields in the file, which are blank in vanilla. RPX patch
  `0x0311CE50=0x38600001` (that call -> `li r3, 1`) does that; the tool names all 94 groups and adds
  a 95th, `NewStage01`, with Ultimate's odds: incidence 10000 / 5000 / 2500 -> rarity 100
  (Halland / Dalarna) / 50 (Earth) / 25. Sm4shMusic re-saving the file would blank the names again.

In game (user): the Sound Test and the stage's music work, other stages keep theirs. The My
Music chances for NewStage01 showed 0: the menu shows the save's values, not the file's. The
save keeps them as bytes, 99 rows of 20 (0x7BC; writer `0x2A4ECA4`: row x 0x14 + song), each
stage's rows in `ui_stage_db.bin` (value 20: songs 1-20, value 21: 21-40, -1 none; read by
`0x030A93EC`). The game uses rows 0-55 and 98; `add_stage.py` gives a new stage the next free one
(NewStage01: 56), which a save made before it has at 0. The menu's Reset (`reset_sound_rate`,
`0x0223F33C`) sets the stage's songs to their `bgm_mymusic.mmb` rarity, finding the group from
the cosmetic id -> kind -> name, so it gives 100 / 50 / 25 here.

Still to check: My Music's other effects; NewStage01 playing them (and Omega); My Music's
NewStage01 page if there is one; nothing else losing its music; save data with a 95th group.

    python3 -I tools/minecraft_music.py AUDIO sound/bgm/snd_bgm_CRS02_Senjyou.nus3bank \
      sound/config param "ui/message/sound.msbt" OUT

## v10: v9 froze (user)

v9 (and v8, never tested) froze loading; v7 loaded. Compared with v7 and with Battlefield:
- **Memory**: v9's models are 35.9 MB, Battlefield's 26.3 (v8's two 2048x2048 panorama halves,
  +6.7 MB). Every hidden Battlefield folder still carried its full textures (14.5 MB, e.g. the sky
  dome's 6 MB). v10 cuts them to 64x64 with the same IDs (`tiny_nut`; not the cube map file or
  Omega's NTP3 ones): 24.0 MB (normal), 27.1 (Omega).
- **Torches** (v9): the only folder with a skeleton of its own (16 / 22 bones instead of
  Battlefield's 1) and a scale animation. `--torches still` keeps Battlefield's skeleton (the
  flames on its bone, its animation made still); `--torches off` leaves the folder hidden.
- **Unlit on a bone** (v8 clouds, v9 torches): `0xA2001001` on a bone-bound mesh, the one flag /
  layout / binding combination Battlefield doesn't have. `--clouds still` leaves them unbound.

`build/minecraft_world_v10_tests.zip`: test 1 animated torches, 2 still torches, 3 no torches,
4 no torches and still clouds (no combination outside Battlefield's); all with the small textures.

Results (user): test 3 loaded, 1 and 2 froze, so the torch folder, with or without its own
skeleton. `dyr_change_160_2_O_OBJ_O_HIR_set` is Battlefield's 160-mesh building (meshes
`mix_000_w002_O_OBJ`...; its windows light up at night, most likely the stage code switching them
by mesh number) and the torch model had 8 meshes. The torches now go in `dyr_d_mid_front01_set`
(a one-mesh, one-bone object, draw range 1, order 12) or, `--torches still`, into the island's
model unbound (nothing test 3 doesn't load).

Also in test 3 (user): the sky sometimes drawn over the background, depending on where the camera
is. The sky folder and the panorama both had drawing order 0, so the blended ones (the sun, the
haze ring, the panorama) were drawn by distance, and the haze ring's bounding sphere (centred at
the origin, radius 11600) and the panorama halves' trade places as the camera moves. Now the
panorama is order 2 and its haze layer (Ultimate's `sfx_far_A_long_fog`) is in its own folder,
`stc_b_shadow_gareki_set`, order 3, draw range 2 (`tools/xmb.py` edits `model.xmb`: Battlefield's
88 files rebuild byte for byte). The background's resolution: Ultimate's own panorama is
3200x1600 (`far_a_day_low_col`) around the whole stage, used at full resolution since v8 (two
2048x2048 halves); `lightboard_<biome>_set` is the blocks' additive glow, not a background.

`build/minecraft_world_v10_tests2.zip`: test 5 animated torches (dyr_d), 6 still torches (island
model), 7 none; all with the draw order fix.

Results (user): test 5 froze, test 6 loaded. So animated torches freeze in a plain one-bone folder
too: what tests 1 and 5 share, and test 6 doesn't, is the made 16-bone skeleton with its scale
animation and unlit alpha-tested / blended meshes on bones (`0xA2001001` with an alpha test or
blending, bone-bound: not in Battlefield; the clouds, which load, are the same shader bone-bound
but opaque). The torches stay still (`--torches still`, the default).

## v11

Test 6 (still torches in the island's model) loaded (user, with a screenshot); its notes:
- **The sky still drawn over the background when the camera moves a lot, and the clouds seen
  through it.** Ultimate draws the panorama premultiplied (`One, OneMinusSourceAlpha`; its texture's
  color is already times alpha) and its distant band (rows 200-400 of 1600) has alpha ~230. Blended
  with alpha / one minus alpha that band got more transparent, and as a blended model it was
  still sorted against the sky's blended parts. v11 draws it alpha-tested (`UNLIT_CUTOUT`), with
  the solid models: it hides what's behind it. Its color is un-premultiplied first
  (`PREMULTIPLIED`; resizing works on premultiplied colors for every texture with alpha).
- **The grass's white outline.** Ultimate's textures have white (about 222) in their fully
  transparent texels, which linear filtering mixes in at the alpha-tested edges; `bleed` fills
  them with their visible neighbors' color.
- **Block colors lacking saturation.** Sampled from the screenshot: hay's top (229, 210, 102),
  its blue channel ~100 where the texture has almost none, grey stone beige: the island's lit
  shader (`0xA4001041`, no fog parameters of its own) gets the stage's light and haze on top.
  v11 draws the island unlit (`0xA2001001`, as everything else of ours) with Minecraft-style face
  shading baked into the vertex colors (`BAKE_SUN_DIR`, `BAKE_AMBIENT` 0.6 + `BAKE_SUN` 0.42 x the
  face's share of Ultimate's sun: top 0.98, front 0.76, sides 0.69 / 0.6, bottom 0.6) times
  Ultimate's corner shading. Characters are still lit by the stage's lights.

No setup outside what test 6 loaded (checked on every biome); `build/minecraft_world.zip` (plains,
hazards on, with Omega and the ui files) and `build/minecraft_world_biomes.zip`.

## v12

v11 in game (user, screenshot; it matches the offline render within a few percent, so the
renderer predicts the game's unlit colors): no more sky over the background; "a bit too dark",
the hay's and the background's colors off next to Ultimate (user's screenshot), a lighter band of
sky over the hills; the grass fixed; no fighter shadows (none before either: the island's
materials don't take them).
- The panorama shows its texture's own color in game (sampled: (129, 153, 95) vs the texture's
  (127, 152, 95)), so Ultimate's livelier look is its post-processing: the stage's color grading LUT
  (`lut/color_grading_lut.nutexb`, a 16^3 R8G8B8A8 3D texture: `nutexb.lut3d`, blocks one GOB high
  and the full depth deep; near the identity, it adds ~0.07 saturation) and its lighting. v12 puts
  every texture through the LUT and `GRADE_SATURATION` 1.1, and the island's baked shading x1.25.
- The lighter band: Ultimate's haze ring (`fog_near`), now behind a solid panorama: left out.
- Animated torches (test A): the sprites' materials are now exact copies of Battlefield's
  bone-bound ones (`BF_FLAME`: dyr_g's 0xA3C01081, additive; `BF_SMOKE`: dyr_f's 0xA4011001,
  premultiplied, the texture written premultiplied; their property lists as Battlefield's).
  Test B: the same on Battlefield's one bone (whether the made skeleton matters); C: still.

`build/minecraft_world_v12_tests.zip`.

Results (user): A froze, B loaded: Battlefield's bone materials are fine, the made skeleton
isn't. The cause found: NUD header 0x0E is the highest bone index the meshes use (Mario's body
83 of 84 bones, the pump 16 of 17, Battlefield's one-bone stage models 0; all 59 of the game's
files we have agree), and `nud.write` always wrote 0, so the game's bone data for the model was
one bone long while the meshes used bones 1-15 (v9's torches too). `nud.write` now writes it;
the torch animation also gets a still track for the root bone, as the game's files have one a
bone. `build/minecraft_world_v12_testA2.zip`: test A with that.

A2 in game (user): loads, the torches animate. Animated torches are the default
(`--torches animated`); `build/minecraft_world.zip` / `minecraft_world_biomes.zip` are v12 with
them. The same pieces (a made skeleton, NUD header 0x0E, Battlefield's bone-bound materials, an
animation track a bone) are what the mobs and villagers need: Ultimate's `ch_pickel_*_set`
models are 12-16 bones, each part rigid on one bone, with idle motions (`motion/ch_pickel_*`).

## v13: mobs and villagers

Ultimate's `ch_pickel_*_set` models are rigid (every vertex fully on one bone) and their motions
(`motion/ch_pickel_*_set/pickel_<biome>_<kind>_<motion>.nuanmb`) carry the stage paths in stage
coordinates on the Hip bone (Trans and Rot still), so the models stay at the origin: the plains
sheep wander the pen (x -84..-54, z -99..-70), the farmer and the butcher walk between their spots
and the houses. The parameters only have odds (`pickel_world.stdat`: sheep / chicken / cow 30 / 30
/ 30, one, two or three villagers 20 / 60 / 20; guest origins 0). Omega's (`battle/motion`) are the
same files.

- `mob_parts`: each mesh split by bone; each part a NUD mesh on its own bone of a made skeleton
  (bind 8), unlit opaque `0xA2001001` (the clouds' bone-bound setup), shading baked in the bind
  pose. `mob_motion`: a part's motion is A_f x B^-1 (its animated world matrix times its bind
  pose's inverse, column vectors as `omo.trs`), decomposed into position / rotation / scale tracks.
- Villagers (plains, snowy tundra): their day loop `VILLAGER_LOOP` (free1, work, free2, free3,
  work, free4; each 1200 frames from and back to the villager's spot: 7200, Battlefield's
  animation length) in `TORCH_SET` with the torches (240 divides it): one skeleton (26 bones; 32 on
  Omega), one animation. Meeting / return / sleep (to the meeting spot, home, indoors at night) and
  the night's monsters left out (the stage is held at day).
- Animals: two (`--animal sheep|cow|chicken|none`, default sheep as in the user's Ultimate
  screenshot), wait1 and wait2 (4200 frames each, start = end), in `ANIMAL_SET`
  (`dyr_e_mid_left01_set`, no .mta).
- `omo.set_node` writes a rotation / scale that doesn't change as a constant track (types 7 /
  0x201, as Battlefield's; flags `0x7087201` like most of its animations): the torch + villager
  animation 2.6 MB (was 3.3). The stage's models and animations: 33.6 MB (Omega 37.2), Battlefield's
  31.6.
- Checked offline (`view_rig.py`: the meshes posed from the written .omo through `omo.world`, as
  the game reads it): sheep whole and in the pen, villagers whole and on the path.

v13 in game (user, screenshots): loads; the sheep's and villagers' faces and the villagers'
clothes smeared. Their skins are 128-pixel pixel art (`pickel_guestg_col` 128x128,
`pickel_plains_col` 128x64) with faces a few pixels wide: BC1's 4x4 blocks (4 colors on a line)
mixed the eyes (16 pixels off by up to 122 / 255) and linear filtering blurred the rest. v13b draws
them 4x larger with nearest pixels as the block atlas (`pixel_art`): each source pixel one BC block,
within 5 / 255 of the source.

v13b in game (user): the breakable blocks a little lighter than the island's; the skyline's cutout
edge showing stray green pixels and an odd resolution; every torch on the same timing.
- Blocks: the island mesh has Minecraft's corner shading in colorSet1 (mean 0.39), the breakable
  blocks next to none (0.49): Ultimate shades them at run time (`ao_depth_table`). `block_ao` gives
  them Minecraft's smooth-lighting levels from the solid cells around each face corner (the
  island's cells from its axis-aligned faces, `solid_cells`, and the blocks'), at the island mesh's
  own values a level (its vertices' colorSet1 by level, computed the same way: 0.5 / 0.31 / 0.18
  / 0.15, `AO_LEVELS`).
- Skyline: the panorama slices (1800 x 1600 source pixels) were scaled to 2048 x 2048 (Lanczos),
  which rang at the cutout edge (stray bright pixels over the trees); now they're kept pixel for
  pixel in the slice texture's corner (`SLICE`, UVs scaled to it; the edges repeated outwards so
  filtering there stays solid).
- Torches: each its own flicker periods and amplitudes and its own smoke life and height
  (`FLICKER_PERIODS`, `FLICKER2_PERIODS`, `SMOKE_LIVES`: divisors of `TORCH_LOOP`).
- Pixel art (`pixel_art`) now goes straight to the power of two at or above 4x with nearest pixels
  (the crops' 164 x 72 went 4x to 656 and then down to 512, dropping columns).

`build/minecraft_world_v13_test.zip` (v13c).

## v14: day and night

Ultimate's cycle (its far_common_set / far_<biome>_set / render/light/light00_set animations,
9000 frames: day, sunset ~4500, night ~6000, dawn ~8250) at its full length (`CYCLE`; the user asked
for it rather than Battlefield's 7200).
- **Material animations**: `tools/mta.py` reads / writes MTA4 (a folder's model.mta; Battlefield's
  16 without texture patterns rebuild byte for byte; blocks 32-byte aligned, a material's pattern
  offset its own block's end). Entries find materials by their `NU_materialHash` (its float's bits:
  all 21 of Battlefield's match), and Battlefield animates `NU_finalColorGain` on its lit, unlit and
  additive shaders (its grass, sky, moon, clouds). `write_set` gives each mesh's materials its kind's
  hash (`gain_hash`: one a kind, `GAIN_KINDS`) and writes the folder's model.mta.
- **Curves** (`daynight_curves`, per frame): island and mobs: Ultimate's stage light (LightStg0:
  intensity 2.4 -> 0.3, colour white / orange at sunset / blue at night), gamma-encoded, at least
  0.3; sky, clouds, sun, haze: their CustomVector8 over its day value (gamma-encoded, our vertex
  colours are); stars: sun_stars' .w as alpha; the panorama: the night texture over the day one
  (per channel) by CustomVector20.w, warmed at sunset, towards its haze colour by
  CustomVector19.w (late night near black). Whether our unlit 0xA2001001 takes NU_finalColorGain
  is untested: `--gain-shader a3c` puts the curves on Battlefield's 0xA3C01081 instead (a test).
- **Sun, moon, stars** (`sky_rig`, `SKY_RIG` = dyr_m_SKY_DOME_set, Battlefield's sky dome folder:
  draw range 2, order 0; its own .mta replaced): far_common_set's meshes on their bones
  (sunmoon_rotateAxis turns once a cycle, stars_RotateAxis), BF_FLAME (additive). Ultimate's haze
  ring stays out.
- **Clouds**: Ultimate's motion over the whole cycle (two of its 4500-frame loops).
- **Villagers**: `VILLAGER_CYCLE`: free1, work, free2 (day), meeting (dusk, 600), return (home,
  1200), sleep (3600: indoors, out to their spot at dawn) = 9000. **Animals**: wait1 until
  Ultimate's frame_of_monster (4200), then scaled to nothing until the end of the night.
  **Torches**: `TORCH_LOOP` 300 (divides 9000).
- **Fighters' light** (`cycle_light`): light.bin's header has a record every 3 frames (Battlefield
  2401 records = 7200 frames); 3001 records over the cycle, each Battlefield's own record for the
  same time of day (`LIGHT_PHASES`), its colour tracks likewise.
- Offline (`view_cycle.py`: the curves and rigs applied as the game should): day, a soft orange
  sunset with the sun low over the hills, a dark island under stars at night, the moon late at
  night. Size: 39.5 MB normal, 42.9 Omega (v13c 33.6).

`build/minecraft_world_v14_tests.zip`: test A (curves on our unlit shader), B (on 0xA3C01081).
User: A's island didn't darken (the fighters' light did), B worked: 0xA2001001 ignores
NU_finalColorGain, so `--gain-shader a3c` is the default.

## v15: doors, Omega's village, sun and moon, torch light

From the user's v14 notes:
- **Doors** ("they just walk through the door"): `door_rig`. Each house's door (door_*_set: one
  bone; Ultimate's open / close motions swing it 90 degrees in 4 frames) on the villagers'
  skeleton in TORCH_SET, open while a villager's Hip is within `DOOR_REACH` (8) of it, from
  `DOOR_EARLY` (12) frames before to after, swinging over `DOOR_SWING` (4). Plains: the farmer
  through the firmer door at ~4462 and ~8348, the butcher through his at ~4482 and ~8613 (checked
  offline). The doors' texels: the block atlas's rows they use (`atlas_rows`, 352 KB instead of
  a second 4 MB atlas in that folder).
- **Omega** (a floating villager, no door on the middle house): battle/model's motions are the
  normal form's, but ring_endbattle_set is narrower and has only the butcher's house. The farmer's
  spot is a block above its ground and his house isn't there, so Omega has the butcher only
  (`END_VILLAGERS`) and his door; the animals' pen walked off its edge, so they're moved by
  `END_ANIMAL_SHIFT` (10, 0, 20): the least block shift that keeps every frame of all three
  animals' paths on its ground (checked against its up-facing triangles).
- **Sun at sunset** ("extremely bright ... the square sun appear round"): the sun was added
  (BF_FLAME) over the bright sky, white past 1 and rounded by the game's bloom. Ultimate draws it
  with one / one minus source alpha and colour x alpha in its shader, i.e. alpha blending. Smash
  Forge's NudEnums: source 1 and 5 are both source alpha, so Battlefield's 5 / 1 is plain alpha
  blending (and the smoke's 5 / 1 isn't premultiplied, as the code had said). The sun, its core and
  the moon now use `BF_GLOW` (0xA3C01081, 5 / 1); its glow fades with its colour once set, its core
  stays white (Ultimate's doesn't change) and fades with it (`sun_core`).
- **Moon** ("seems to not glow at all"): Ultimate's halo is a dim grey-blue its bloom lifts;
  Smash 4's doesn't reach it, so the moon's half of the texture gets a paler, stronger halo
  (`MOON_GLOW`, `MOON_GLOW_ALPHA`).
- **Torch light** ("the torches also don't light the surrounding area"): Ultimate's are point
  lights; our island is unlit. `torch_light`: the island's faces within `TORCH_LIGHT_RANGE` (45)
  of a torch drawn again, added (Battlefield's unbound 0xA3C01081 5 / 2), lifted 0.05 along their
  normals, their texture times a warm light per corner (a quarter from everywhere, the rest by
  how much the face looks at the torch, falling off with distance squared), faded in as the
  island darkens (`torchlight`). The doors get it too, on their bones (user).
- **Backdrop lights** (user: its torches and lava, weaker): Ultimate's night panorama has torch-lit
  patches and lava our darkened day one lacks. `pano_glow`: the night texture's excess over the
  darkened day one, at 1024 x 512, added over the panorama triangles it reaches, faded in by
  Ultimate's own day / night blend (CustomVector20.w).
- **Night floor**: `NIGHT_FLOOR` 0.5 (was 0.3; Ultimate's light ratio gave 0.39): the user's
  comparison shows Ultimate's island much brighter at night (its ambient light stays).
- **Other biomes**: `daynight_curves` read plains' panorama material node (sfx_far_A_long) on
  every biome; now each far set's own (sfx_far_E_long, sfx_far_C, ...). All six build.

v15 in game (user): loaded; the doors open, the torches light up. Then (v15b):
- **The door far too bright**: its corners are next to its two torches, at the cap (1.6); doors
  now at most `DOOR_LIGHT_MAX` (0.5).
- **A growing semi-transparent square with each flame**: the flame (and smoke) quads wrote depth
  over their whole area, so the torch light drawn after them was hidden behind it (the unlit wall
  showed through, as big as the flame). All our blended materials now alpha-test (greater than
  0, as every blended material of Battlefield's); the sprites' alpha is 0 or over 239.
- **The moon gives no light**: drawn past white (`MOON_BRIGHT` 1.8) for Smash 4's bloom to glow
  around it, as it does around the sun.
- **No stars**: their vertex colours (0.34, alpha 0.49) left them at 0.17 at most, invisible in
  Smash 4's night sky (Ultimate lifts them by its CustomVector8 1.5 and its HDR bloom). Now 1.5,
  alpha 1 (`STARS_BRIGHT`).
- **Fighters' light** (with Ultimate's for comparison): `cycle_light` used Battlefield's own
  fighter light for the time of day, a strong blue one at night. Ultimate's `LightChr` (light00_set)
  goes from 4.6 by day to 1.8 at night, white, slightly warm at night (1, 0.97, 0.88). `chr_light`:
  each record's fighter block is Battlefield's midday one (`DAY_FRAME`) with that colour and the
  intensity's ratio (gamma-encoded: 0.65 at night); the five colour tracks are midday's likewise.

v15b in game (user): loaded; the flame squares gone, stars shown. Then (v15c):
- **Stars as long streaks**: BF_FLAME's sampler clamps (wrap 3), the stars' UVs run 0-4 / -3-1,
  so their edge texels were stretched across the sky. `BF_STARS`: the same, repeating (wrap 1).
- **Doors still far too bright**: their overlay wasn't doubled (checked) and was at 0.5. The
  door's own material (on a bone) had the night curve's hash but no `NU_finalColorGain`, which
  every material Battlefield animates on a bone has; the unbound island darkens without it, the
  door looked to stay at day brightness. `write_set` now gives every curve material the property;
  `DOOR_LIGHT_MAX` 0.35.
- **Omega's lamp post extremely bright** (four torches on it): `TORCH_LIGHT_MAX` 1.6 -> 0.8 (the
  walls a few blocks away were at about 0.9).
- **No fighter shadows**: Smash 4 draws them on materials with flag 0x40 (Smash Forge's
  `TextureFlag.Shadow`); our 0xA3C01081 has none (0x81: glow, diffuse). Battlefield's own platform
  (stc_c_Ring_set) is 0xA4001041 (and 0xA6101045 with a reflection), lit. `--island-shader shadow`
  (`ISLAND_FLAGS`) puts the island on it: a test, as a lit shader once washed the colours out.

`build/minecraft_world_v15c_tests.zip`: test A (the island unlit, no shadows), B (on 0xA4001041).

User: B has shadows, but the island's lighting is wrong (Battlefield's island lights, as when it
was lit before). v15d:
- **Shadow catcher** (`--island-shader catcher`, `shadow_catcher`): the island stays unlit (A),
  and its upward faces are drawn again on 0xA4001041 (shadows) with a white texture, multiplied
  over it (blend 8 / 0: destination colour, zero, per Smash Forge's NudEnums; no Battlefield
  material uses it). Its light set (the island's, 4, every frame: `SHADOW_LIGHTS`) brings a
  sunlit top face to 1 (main light 0.55 at 0.90 of it, ambient 0.5), so only the shadows darken;
  the island's own curves still darken it at night. 0.02 in front of the island, behind its torch
  light (0.05): it writes depth, and if drawn first it would hide that light.
- **Stage-select pictures** ("less compressed", user): ours were Ultimate's 512 x 256 preview
  enlarged slightly and BC3-compressed. Now rendered from the port (offline renderer, day, camera
  (-15, 38, 220) to (5, 22, -110), fov 27) at 2048 x 1024, contrast 1.12 and saturation 1.25
  towards Ultimate's preview, cropped as before (the crops found by matching the old pictures
  against Ultimate's: stage_13 x 60-450 of 512, stage_10 64-450, stage_12 32-478 into 210 x 120
  of 256 x 128, stage_30 128-382) and scaled down; stage_10 / 12 / 13 / 30 uncompressed RGBA8
  (0x1A, which the game's own UI uses, e.g. lumen/popup2), stage_11 (1024 x 512) BC3. Same
  texture IDs.

`build/minecraft_world_v15d_tests.zip`: test A (v15c A, new pictures), C (the shadow catcher).

User: C loads with shadows, but the catcher is drawn opaque white (8 / 0 isn't a multiply in
Smash 4; no model of the game's we have uses it, or any multiply: the blends found are 0/0, 0/1,
1/1, 1/2, 3/1, 4/0, 5/1, 5/2). The catcher is removed. And the stars "look 3d and incorrect".
v15e:
- **Stars**: each is a 3 x 3 texel square, which without mips and at 1.5 came out as big bright
  blocks (on Ultimate's planes at different depths, so moving apart: "3d"). Ultimate samples them
  with mips, dim (colorSet 0.03 x 1.5): pinpricks. Now each star's brightest texel only, at 1.0.
- **Shadows, test D** (`--island-shader shadow`): the island on 0xA4001041 as in B, but lit by its
  own light set (`ISLAND_LIT`, written into every light.bin record by `cycle_light`) instead of
  Battlefield's: the sun 0.35, a sky light from above 0.15, a fill from the camera 0.15, the
  ambient 0.7, for the baked shading's top 1.21, front 0.97, sides 0.77, bottom 0.7 (the bake:
  1.22, 0.95, 0.86 / 0.75, 0.75), scaled and tinted each frame by the island's curve; the vertex
  colours its corner shading only (`to_nud(..., bake=False)`), and no gain curve on it.

`build/minecraft_world_v15e_tests.zip`: test A (unlit), D (shadows, own lights).

User: D loads with shadows and looks good, torch light still there; the shadows go at the darkest
point of the night; the stars look good but show over the moon. v15f (D the default:
`--island-shader shadow`):
- **Shadows at night**: a light.bin record ends with 16 bytes: a word, then a position ~55000 out
  following Battlefield's sun (midday (53100, 14294, -2112), at night below the horizon): the
  shadows' light. `cycle_light` copied Battlefield's for the time of day; now `SHADOW_SUN` (Ultimate's
  sun, ISLAND_LIT's main light, x 55000) every frame.
- **Stars over the moon**: Ultimate's stars are at 27000-41700 from the sky's turning point
  (0, 250, 0), in front of the moon (45000); Ultimate draws the moon over them, Smash 4 by depth.
  The stars (`STARS_PUSH` 1.75: 46900-72800) and the sky dome (`DOME_PUSH` 1.76: 78900-83700,
  Battlefield's own reaches 85000) are pushed out from that point: the same directions and sizes
  on screen, the sun and the moon in front.
- With `--daynight off` and the shadow island, `still_light` writes ISLAND_LIT at midday.

`build/minecraft_world_v15f_test.zip`.

## v16: monsters, all the animals

User: v15f loads, shadows stay at night, the moon shows over the stars; add the rest of the mobs
and the other animals.
- **Monsters** (`MONSTERS`, `mob_kinds`): `pickel_world.stdat` has frame_of_monster 4200 and odds
  zombie 40 / skeleton 35 / spider 20 / enderman 5 (Ultimate rolls them, several a night: the user's
  Ultimate screenshots show more than one). No stage code here to roll, so all four, each playing
  its biome's path (`pickel_<biome>_<monster>`: zombie 4180 frames, rising out of the ground;
  skeleton 4000; spider and enderman 3600) once from `MONSTER_FRAME` (4200), scaled to nothing
  before and after, gone by dawn. In Battlefield's dyr_h_BG_more_far0_set (`MONSTER_SET`, draw
  range 2), a rig of their own. Their animations' Visibility tracks are fixed per biome (the
  enderman's carried block: grass in plains, dirt / tundra / savanna grass elsewhere):
  `hidden_meshes` drops what starts hidden. The block meshes have no weights, only a parent bone:
  `mob_parts` puts them on it.
- **Fitting paths to ground** (`Ground`, `fit_shift`): the up-facing faces' heights on a 2.5-unit
  grid; a path frame fits where it stands on one (within 2) with nothing within 30 above;
  `fit_shift` finds the least shift (blocks of 10) for a path's sampled frames. Replaces v15's
  hand-found `END_ANIMAL_SHIFT`.
- **Omega monsters**: Ultimate's own paths fit the normal form's ground 0.79-0.90 of the time
  (rising out of it, coming in from off the island; the enderman's path is 3 below its feet, found
  per monster). On Omega each is moved to where it fits at least `END_MONSTER_FIT` (0.9) of that:
  the zombie, skeleton and enderman; the spider (0.71 at best, 0.77 needed) is left out.
- **Animals** (`ANIMALS`, `--animal all`, the default): Ultimate picks one kind a match, all three
  walking the same pen; all three here, the first (sheep) in the pen, the others moved by
  `fit_shift` to ground behind the fighters (z <= `ANIMAL_BACK` -45), `ANIMAL_APART` (15) from the
  others. `--animal sheep|cow|chicken` keeps one kind in the pen.
- Size: 54 MB normal / 48 MB Omega (v15f 44): the six animals' animation is 6.5 MB, the monsters'
  4.8 MB.

`build/minecraft_world_v16_tests.zip`: test A (all the mobs), B (the monsters, the sheep only).

User: A loads. The zombie should burn in daylight and the enderman teleport, neither shows
(Ultimate's are stage code playing ef_pickel_world.eff emitters, `P_PickelWorldEnemyFired` /
`P_PickelWorldEnderman`). v16b:
- **Burning** (`burn_fx`, `BURNING`): the zombie's path stops in the sun at ~8120 and falls over
  ~8280-8360. From `BURN_FROM` (8100) to its end, four flame sprites (the torches'
  ef_pickelworld_fire00; the eff's fire01 is a streak, not a frame sheet) on a bone copying its
  hip's track, scaled to nothing outside and flickering (scaled about the feet) inside.
- **Teleports** (`teleport_fx`): the enderman's path dashes in 6-10 frames at 8-15 units a frame
  (its walk at most 10.6 over 2 frames): its bones scaled to nothing over each dash, and at both
  ends a burst of `TELEPORT_PARTS` (12) purple particle sprites (a made 8 x 8 `pickel_portal`)
  rising and shrinking over `TELEPORT_FX` (40) frames. Plains: 7 teleports a night.

`build/minecraft_world_v16b_test.zip`.

## v17: the biome picked at load, the monsters rolled (executable patches)

User: random biome per match as Ultimate, a biome chosen by buttons (as Boxing Ring's): L+A plains
(Grassland), L+R+A birch forest (Forest), L+stick up+A savanna, L+right+A taiga, L+down+A snowy
tundra, L+left+A stone shore; monsters random per match. Both need code: research (two agents,
notes in the scratchpad's `re_input/` and `re_stage/`):
- **Controllers** (all static, polled every frame, also while loading): the pad manager's slot
  array `0x1057581C` (26 wrappers; slot 0 the GamePad, 1 a dummy, 2-8 Wii Remotes / Pro, 9-16 the
  GameCube adapter, 17-24 3DS / network); wrapper `+8` the status: `+0` held buttons in the game's
  own layout (A `0x10`, L `0x1000`, R `0x2000`, ZL `0x4000`, ZR `0x8000`, d-pad left / right / down
  / up `1` / `2` / `4` / `8`, the left stick as buttons left `0x80000` / right `0x100000` / down
  `0x200000` / up `0x400000` past half way), `+8` / `+0xC` stick X / Y floats, `+0x68` pressed,
  `+0x7C` pad type, `+0x87` valid this frame. GameCube L / R are their analog values past 48 / 255
  (a light press), Wii Remotes have no L / R.
- **Stage folder**: the path function `0x02D1FDA0` is called when a match's stage setting is built
  (`0x0315800C`, return `0x03158060`; the setting caches the path, the loader uses that copy), for
  an optional prefetch (return `0x02AB83A4`) and for StageEdit only. Nothing else builds
  `stage/melee/%s`; the kind's name also names the music group, so only the path changes.
- **RNG**: the game's xorshift128 x4 at `0x105759C0`: instance 0 the battle's (seeded per match,
  replays / online), instance 1 seeded from the clock: `0x024F6BE8(n)` = x % n on it.
- **Stage models**: `0x03141D2C(stage, folder)` -> StageModel; flags `+0x118` (`0x80000` visible,
  `0x40000` stage-wide visible, both for drawn); the game's per-model show / hide in setAllVisible
  `0x03159750` (scene add `0x03158994`, remove `0x031589E0`, render `0x032FF668` / `0x032FF68C` on
  `+0xDC`); OMO frame `0x0315871C(m, f1, 1)`.

Built:
- `tools/biome_select_cave.py` (test: `tools/biome_select_test.py`, unicorn, 22 checks): kind 0x80's
  folder: `NewStage01` (plains), `NewStage01_forest`, `_savanna`, `_taiga`, `_tundra`, `_shore`:
  every controller's held word ORed; L held: R or a stick / d-pad direction picks (`BUTTONS`), L
  alone plains; no L: random (the time base). Only the setting build picks, kept within ~5 s of
  setting builds (several a match); other callers get the last pick. Omega (0x81) stays plains.
- `tools/monster_roll_cave.py` (test: `tools/monster_roll_test.py`, unicorn, 14 checks): replaces
  `stage_script_cave.py` (the moving-platform test) on the generic stage's update / setup hooks; for
  kind 0x80 counts frames (f1) over the 9000-frame cycle and on the first update and each cycle's
  end rolls 3 spawns at Ultimate's odds (40 / 35 / 20 / 5) on the clock RNG, showing the monsters
  rolled (zombie ~78% of nights, skeleton 73%, spider 49%, enderman 14%). The stage builder puts
  each monster in its own Battlefield folder (`MONSTER_SETS`: dyr_h / dyr_f / dyr_g / dyr_n1).
  Omega's generic stage is another class (StageBaseEnd), not hooked: all its monsters every night.
- The RPX: the user's current one (`minecraft_music.zip`'s, = `build/cross_f.rpx`) plus both:
  `rpx_patch.py build/cross_f.rpx OUT $(biome_select_cave.py) $(monster_roll_cave.py)`.
- `ppcasm.py`: `mftb` / `mftbu`, `divwu`.

Open (Cemu): the prefetch's order to the setting build; L / direction held through the confirm
(A) and the load; the show / hide on our folders; online / replays (a clock pick isn't synced).

User (v17): loads, the biomes switch with the buttons. Then (v17b):
- **Pale see-through boxes** in the other biomes' backgrounds: their fog layer's v runs 0-7
  (plains' 0-1; Ultimate's sampler clamps); read the other way up and repeated, the ramp tiled into
  bands over the backdrop's big quads. v is clamped to 0-1 before the flip (`far_parts`).
- **Grass flickering near torches**: the torch light overlay 0.05 off the faces fought them for
  depth at the camera's distance: `TORCH_LIGHT_LIFT` 0.25.
- **Taiga's lamp gives no light**: `lamp_points`: the island's emissive mesh's connected pieces
  (pieces within 8 of each other as one) that aren't torches light like them (taiga's lantern at
  (-5, 37, -180); snowy tundra's two at (55 / 75, 27, -120)).
- **Spawns as Ultimate's** (user): pickel_world.stdat has, besides the monsters' odds, sheep /
  chicken / cow 30 / 30 / 30 (one kind a match, else none) and guest single / double / triple
  20 / 60 / 20 (read as how many monsters a night; their kinds then picked without repeats,
  weighted 40 / 35 / 20 / 5). The animals are all built in Ultimate's pen, each kind sharing a
  folder with a monster (`ANIMAL_SETS`: sheep + zombie in dyr_h, cow + skeleton dyr_f, chicken +
  spider dyr_g; the enderman dyr_n1): each is scaled to nothing outside its time by its own
  animation, so `monster_roll_cave.py` shows a folder by day for its animal and by night for its
  monster: the animals' kind at the match's start (setup), the night's monsters at frame 4200,
  the animals again at the cycle's end. Omega's update calls StageBaseCafe's (0x0264D1C0 /
  0x0264D228) and its setup Cafe's (0x0264CB2C), so the patch takes kind 0x81 too. The folders
  the port doesn't fill are hidden (`hide_folder`). `monster_roll_test.py`: 6000 rolls as the
  rules in Python; nights with zombie / skeleton / spider / enderman ~0.71 / 0.67 / 0.49 / 0.13.
  (`biome_odds` 85 and `biome_limit_count` 3 aren't used: their meaning is unknown.)

## v17c: burning mobs, animals day and night, sounds

User (v17b): the doors still too bright; the burning zombie / skeleton didn't flash, its fire
looked wrong, no poof (Ultimate screenshots: a tall animated fire sheet over the mob, the mob
tinted red, white puffs); the fog boxes still there on every biome but plains; the animals gone
at night (Ultimate keeps them) and several kinds at once, inside each other on the same path;
asked for the mobs' sounds (Ultimate's bank: the user's `sound-ssbu.zip`).

- **Doors**: `DOOR_LIGHT_MAX` 0.18.
- **Burning** (`burn_fx`, from `BURN_FROM` 8100 to the mob's last frame): Ultimate's
  `ef_pickelworld_fire01` (16x512: 32 Minecraft fire frames side by side) on two quads over the
  mob on a bone copying its hip, a frame every `FIRE_STEP` 3 by an MTA `NU_colorSamplerUV` curve
  (`write_set` takes {property: values} curves); the mob's own materials on curve
  `hurt_<kind>` = the island's times `HURT_TINT` (1, 0.4, 0.4) for `HURT_FRAMES` 30 of every
  `HURT_PERIOD` 60 and the last `HURT_DEATH` 90; at its end a bone at its last place shows 7
  puffs of `ef_pickelworld_smoke00` (7 frames, made white) for 21 frames.
- **Fog boxes**: the other biomes' haze v runs 0-7; past 1 it's clear, but those cards sat on the
  ramp's top edge, where the repeating sampler and the mips mixed in its opaque bottom rows. Their
  fully-clear triangles (all corners v >= 1: ~400 a biome) are left out and the rest clamp
  (`FOG_WRAP` 3).
- **Animals** (day and night, one kind a match): each kind in a folder of the port's own
  (`ANIMAL_SETS`: dyr_p sheep, dyr_q cow, dyr_r chicken, copies of dyr_h's files): the stage
  makes a model of every folder it finds (Battlefield's folder names aren't in the executable;
  its lookup `0x031429B4` only strips a `dyr_` prefix). Their animation: wait1 or wait2 twice,
  then still on its first frame (= its last) to the cycle's end. `monster_roll_cave.py` applies
  its mask every update: v17b set the folders once, at the first update, and the game showing
  every stage model as the match starts brought all three kinds back (the same pen paths: inside
  each other). The night's mask is its monsters and the animals.
- **Sounds**: below.

### Sounds

Smash 4's stage sounds (cross_f.rpx):
- The stage loader `0x031434B8` loads `*/sound/sound.nus3bank`, `*/sound/sequence.bin` and
  `*/sound/sound_add.nus3bank` from the stage's folder into `X = **(stage + 0xFF0)`. The bank's
  load `0x03124D54` calls `0x03122E08(X, name = stage + 0x10, form)`, which makes the stage's
  sound object `S = X + 0x390` by the stage's name (a list per form: `BattleField_f` ->
  `0x023A8EAC` (0x1004 bytes) / `0x023B17E0`, Galaxy, MarioU, ... Wufu ...); no match, no object.
  NewStage01 matches nothing, so its bank (a copy of Battlefield's) never played.
- A sound's ID is `(row << 16) | index` in `sound/config/soundlabeltable.bin` ('STB\0': 3252
  rows of (bank id, sounds, offset, 0), then each row's tone indices); `0x0311EC80` checks the row
  and `0x0311EDBC` the index against its count. Battlefield's (= NewStage01's) bank 3051 is row
  1147, 7 sounds.
- `sequence.bin` ('SQB\0'): 16-byte entries (sound ID, 1, frame, 0...), -2 = loop: Battlefield's
  plays its ambient loops amb01-04 at 0 / 3120 / 5040 / 5760 (its day turning), loop 7200, through
  the music player (`S + 0xFC8`, `0x03121D78`).
- Stage code plays a sound with `0x03125D80(S, handle, id)` (the handle 0x30 bytes, the caller's;
  then `0x033EFD88(handle, 2)`): Wuhu Island's code (301 calls, e.g. `0x023A8878`).

Built:
- `tools/minecraft_sound.py`: Ultimate's `se_stage_pickel_world.nus3audio` holds Namco IDSP (DSP
  ADPCM, 48 kHz mono) as Smash 4's banks do: copied as they are into NewStage01's bank as tones
  7-54 (`SOUNDS`: cow / chicken / sheep / villager / spider / zombie voices x6, zombi_burn x2,
  zombi_death, bone_move x4, enderman_portal x3, door_open, door_close; the block sounds left
  out), entries as a Smash 4 one-shot's (`snd_se_enemy_Metalface`'s: loop flag 0) in
  Battlefield's group 0x272, `VOLUME` 0 dB. Battlefield's amb loops are made a silent loop, so
  its sequence.bin (kept, known to load) plays nothing. soundlabeltable.bin's row 1147 grown to
  55 (the other rows' offsets moved).
- `tools/minecraft_world.py --sound-bank / --sound-events`: the bank in both forms' sound folders
  (Omega's vanilla bank is an empty file); the build lists its sounds: the doors as they start to
  open / close (`door_rig`), voices at random frames `SOUND_EVERY` apart while the mob is out
  (fixed a build), a burning mob's hurt on each red flash and its death at the poof, the
  enderman's portal as it leaves and lands. Ultimate's own timing is in its stage code, not
  available. `tools/minecraft_sound_events.json`: all biomes' and Omega's.
- `tools/monster_roll_cave.py`: hooks `0x03122E08` so a name starting `NewStage01` is matched as
  `BattleField_f` (Battlefield's sound object: its methods only start / stop the sequence); each
  update plays the events (8 bytes: frame, tone, mob folder bit or always, variants) of the
  biome's table (the biome cave's pick mod 6; Omega its own) up to the cycle's frame, those
  whose mob is shown, a variant at random (the clock RNG), with `0x03125D80`. 24 unicorn checks.
- Install: also `sound/config/soundlabeltable.bin`.
- Space: the mob cave's tables (~6 KB) grow the code section to 0x04B84000.

Packaging (user): the hazards-off folders only once the hazards are finished. Until then
`biome_select_cave.HAZARDS_OFF` is False: ZL / Z ignored, only the six biome folders listed
(`--hazards-off` lists the twelve); `biome_select_test.py` checks both. v17c ships the six.

## v17d

User (v17c): loads, the sounds play. Animals sometimes missing; the fog still visible at the top
of every biome but plains by day; villagers going to sleep where there's no house; the fire on the
burning mobs not Minecraft's and not animating, nor the puff.

- **Fire / puff**: Battlefield's MTA UV curves all have the property's u2 = 1 (its colour gains
  0); ours had 0 (`write_set` now writes 1 on UV properties). The flames' shader (0xA3C01081) has no
  UV curve of Battlefield's, so the fire and the puff are now flipbooks instead: a mesh a frame of
  the strip (`sprites`: several quads in one mesh), each on a bone shown (scale 1) only for its
  frame (`FIRE_STEP` 3 frames each, 32 frames; the puff 7 frames of `POOF_STEP` 3).
- **Fog**: the layer is a bowl, its rim high in the sky (v 0), the horizon at v ~0.87, under it to
  the ground below the island; its texture white, alpha 0 at the top rows to 1 at the bottom along a
  ragged edge that follows the farthest hills (it hazes the far hill line). v11-v17c read it the
  other way up (to keep the near ground clear), which put the haze at the top of the sky (with
  v17c's clamped sampler: pale shapes at the top of the screen). Now read as it is above
  `FOG_HORIZON_Y` (0) and clear (v 0) below: the far hills hazy, the sky and the near ground clear.
- **Fog (v17e)**: in game (user) v17d's fog, still 1% in front of the panorama as since v9, laid a
  white band over the far hills with a hard lower edge (the texture's alpha runs out within a few
  rows of the horizon). Ultimate's bowl is a little *behind* the panorama (rim 8825, panorama
  8804): now there too (`FOG_SCALE` 1.01), read as it is: the hills hide it, only their edges
  catch a little haze (rendered offline for plains, taiga, savanna).
- **Animals**: Ultimate's 30 / 30 / 30 read as weights: a kind every match (v17c: none 10%).
- **Villagers**: one is built only where its house's door is (`door_<villager>_set`, the farmer's
  named "firmer"): snowy tundra has no farmer's house (Ultimate's model has only the butcher's
  door), so its farmer is left out (as Omega's).

## Freeze (user) and tests

The moving-platform test build froze while loading the stage, and so did v4. Not the cause
(checked): the link manager rigged collision needs exists on every stage (made in the base
constructor, `0x03140B78`); a cave keeping data next to its code (strike_cave.py's counters already
do). `build/freeze_tests.zip` (v4) split it; the user's results:
- 1 (Minecraft World, normal and Omega): froze;
- 3 (Minecraft models, Battlefield's collision): froze;
- 4 (Battlefield's models, Minecraft collision): loaded, with the Minecraft collision. Omega froze,
  but that folder still had test 1's Minecraft models (user).

So the models, not the collision. Compared with Battlefield's own loaded models, v4's had:
- **NTP3 textures**: all 43 `model.nut` / `render` textures Battlefield's melee and Omega folders
  load are NTWU (GX2 tiled); its only NTP3 files are in three Omega-only folders (`stc_BG_set`,
  `stc_ring_set`, `stc_surinuke_set`) that melee doesn't have, likely never loaded;
- material setups Battlefield doesn't have: `0xA2000001` with normals (its one use, an Omega-only
  folder, has none), `0xA4001041` with an alpha test, nearest filtering, a texture ID `0x2001EFFF`;
- `model.mta` removed from folders whose model it no longer matched (or left over on install);
- 4x4 / 8x8 textures (Battlefield's smallest: 32x32).

v5 changes all four (above); `tools/minecraft_world.py`'s output is checked (scratch
`check_v5.py`) for: every material setup and sampler in Battlefield's melee models, every texture
by the NTWU rule, every other file Battlefield's or its model hidden, no file missing or extra.

## Ultimate files (user)

`param-SSBU.zip` is Ultimate's top-level `param/` (game, spirits, sound settings). `pickel_world.zip`
is the stage's dump with its `param` folders (used above). `ui-SSBU.zip` has the stage pictures
(`ui/replace_patch/stage/stage_0`-`stage_4/stage_N_pickel_world.bntx`: the "MINECRAFT" logo, a small
icon, the normal / Omega / Battlefield-form previews) and the series symbol
(`ui/replace_patch/series/series_0|1/series_N_minecraft.bntx`, a cube).
