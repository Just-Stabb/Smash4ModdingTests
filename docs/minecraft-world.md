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
