# Minecraft World (Smash Ultimate) on NewStage01

Status: **built, not tested in game yet.** The whole normal-play stage (not the Battlefield form)
is converted from Ultimate's files (`stage/pickel_world`, from the user's Drive) into the
`NewStage01` slot (`docs/stage-expansion.md`), with collision made from the models, for both
normal play and Omega.

Build: `python3 tools/minecraft_world.py SRC BASE OUT [--biome plains]`. SRC is the extracted
`stage/pickel_world` folder, BASE holds the slot's current `melee/NewStage01` and `end/NewStage01`
(the Battlefield copy), and OUT gets `stage/melee/NewStage01` and `stage/end/NewStage01`.
Deliverables (git-ignored `build/`):
- `minecraft_world.zip`: both stage folders, built with the Plains biome, plus the stage-select
  pictures (`ui/...`: a preview rendered from the port, the page-2 tile and a "Minecraft World"
  name banner; same files, texture IDs and formats as `new_stage_pictures.zip`, which this replaces).
- `minecraft_world_biomes.zip`: the other five biomes (Birch Forest, Savanna, Taiga, Snowy Tundra,
  Stone Shore). Each is the three model folders plus `NewStage0100.lvd` that differ from Plains;
  copy one over `stage/melee/NewStage01` to switch biomes.

## What Ultimate's files have (and don't)

- `normal/model`: per biome a `ring_<biome>_set` (the island: terrain, village, trees, under-side,
  10-unit Minecraft blocks), `far_<biome>_set` (the panorama: a 3200x1600 texture on a ~8800-unit
  bowl), `platform_<biome>_set` (the orange-trimmed pass-through plates; Plains and Taiga have
  none), doors, Plains' farm, mobs (rigged and animated; not ported), `ink_*` (Splatoon-ink
  decals), `lightboard_*` (a lighting duplicate of the ring), and one model per block kind
  (`bg_b_<kind>_01_set`: a 10-unit cube). `far_common_set`: sky dome, clouds, sun, moon and stars.
- `battle/model`: the Battlefield form (`ring_endbattle_set`, `floating_plate_set`) and the flat
  form `ring_end_l_set`, used here for Omega.
- No `param` folder, so no collision (`.lvd`) and no stage parameters, and no stage code. Which
  breakable blocks a biome has, where they are, the biome rotation, day / night and the mobs are
  all run by Ultimate's stage code.

The blocks' places come from `ink_<biome>block_set`: one ink-able top face per breakable block
(named by column / row, 10-unit cells, with its depth). The kind of block isn't in the files, so
it's grass-type on top and dirt under (Stone Shore: stone; Snowy Tundra: the snowy grass block).

Scale is 1:1. Ultimate's Battlefield form sits where Smash 4's Battlefield does (plates at
x ±59, top 47 against Battlefield's 59 / 47.3; ledges ±78 in both), so no rescaling.

## Formats (new tools)

- `tools/nutexb.py`: Ultimate textures. Tegra X1 block-linear deswizzle (64-byte x 8-row GOBs, block
  height from the image height) and RGBA8 / BC1-BC5 decode (reusing `nut.py`'s BC decoders).
- `tools/nut.py ntp3`: new NTP3 textures (untiled, so any size; the game's own Battlefield has
  NTP3 `model.nut`s, and the header matches them). Formats 0 DXT1, 2 DXT5, 14 RGBA8 (stored
  A, R, G, B), full mip chains.
- `tools/nud.py`: NUD read / write. Checked by rewriting every static Battlefield model with it:
  byte-identical except the bounding spheres it recomputes (and one unused vertex field).
- `tools/lvd.py`: LVD read / write (collisions with ledges and surface kinds, spawns, respawns,
  camera, blast zones, item areas, general points; Battlefield's melee and Omega files round-trip
  byte-identical).

## The conversion

- **Models**: every Ultimate mesh becomes a NUD mesh: positions, normals (half float), vertex
  colors from `colorSet1` (Ultimate 0.5 = 1.0 maps to Battlefield's 127 = 1.0; the other color
  sets are shader inputs, e.g. the backdrops' `colorSet5` is a constant 0.33), the first UV set
  (same orientation in both games, checked by rendering Battlefield's own models), triangle lists.
  Meshes under a bone (doors) are moved by the skeleton. Each block kind is merged into one mesh.
- **Materials** are Battlefield's: `0xA4001041` (its ground: lit, vertex colors, shadows) for the
  island, blocks, plates, doors and farm, with an alpha test (`>= 128`) for the block atlas'
  cut-outs (leaves, grass, flowers) and nearest filtering (pixel art). `0xA2000001` (its background
  plane) for the panorama (alpha-tested sky cut-out) and the sky. Cull mode from Ultimate's.
- **Textures**: the block atlas (512x512) is RGBA8 with 5 mips, one copy for the island and the
  blocks (Ultimate's `_for_programBlock` copy has the same layout, slightly different tones). The
  panorama is resized to 2048x1024 DXT5.
- **Sky**: Ultimate colors the sky dome in its shader (its vertex colors are only shading), so the
  dome gets a fixed day gradient. Clouds at 70% opacity (from under the layer they'd hide most of
  the sky). Sun kept; moon, stars and fog layers not.
- **Model folders**: Battlefield's names are kept (whether the generic stage enumerates the folder
  isn't known). `stc_c_Ring_set`: everything on the block atlas; `stc_k_BG_most_far2`: the panorama;
  `stc_o_BG_clouds_set`: the sky. Every other folder gets an empty model (one zero-size triangle,
  a transparent 4x4 texture). Melee's `stc_a_surinuke_set` isn't empty in Battlefield (it holds
  Battlefield's pass-through platforms), so it's emptied too. The replaced folders' `model.mta`
  (material animations) are removed.
- Melee folder: 13 MB (Battlefield's: 32 MB).

## Collision

The fighting plane is z = 0 (the block grid is centered on it). Solid cells (10x10) there come
from the ring's block meshes (parity of the x-facing faces each row crosses) plus the block
cells; their outlines (clockwise, holes dropped, collinear points merged) become the collisions,
normals pointing out as in Battlefield. Ledges at the main outline's outer top corners, on 5-unit
floor lines (`0x40` left / `0x80` right, as Battlefield). Platforms: the up-facing faces of the
platform set crossing z = 0, as drop-through lines. Surface sounds: soil (snow on Snowy Tundra,
rock on Stone Shore, wood on platforms).

| | island | ledges | blocks |
|---|---|---|---|
| Plains | x ±100, top y 0 | ±100 | mound x -70..-40 (to y 20), arch x 20..60 (to y 30) |
| Omega (end_l) | x ±120 | ±120 | none |

Spawns: players 1 / 2 a mirrored pair on the ground nearest 35% of the half-width (Plains ±80),
the rest spread over flat floor. Respawns 50 / 78 above the highest floor. Camera: island ±90,
top 130 or more. Blast zones: island ±165 (Plains ±265, Omega ±285), top 192 or more, bottom -140.
Item drops along a line 60 above the highest floor. These numbers are this port's (Ultimate's
lvd isn't in the files).

`tools/minecraft_world.py` was checked by rendering every biome's built NUDs from the front with
the collision drawn on top (it follows the blocks in all six biomes and the Omega form).

## Not ported (no stage code to drive it)

Biome rotation (one biome per build; `minecraft_world_biomes.zip` has the others), breakable /
placeable blocks (they're solid scenery), mobs, day / night (the sky is day; the lighting is still
Battlefield's, which may darken over the match), the ink decals, Ultimate's particle effects
(Battlefield's effect files are still in the folder). The `melee.msbt` texts for the slot still
say whatever `add_stage.py` wrote; the stage select shows the name picture.

## To check in game

1. The stage loads and looks like the preview (models, textures, sky; no Battlefield pieces).
2. Standing on the ground, the blocks, the ledges at ±100, the Plains arch and mound.
3. Omega.
4. Lighting / day-night: if it turns dark or odd, `animation/light.bin` / `render/` are still
   Battlefield's.
