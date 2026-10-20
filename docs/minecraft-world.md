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
  `stage + 0xCC`; other generic stages must be left alone).

So biome rotation can be: every biome's models in `dyr_` model folders whose animations show only
the current biome, every biome's collision rigged under its own subname, and a cave on that hook
counting frames (adding `f1`, as the animations do) that moves the inactive biomes' collision away
(`0x0315EF88`) and the active one into place.

## Moving-platform test (not tested in game yet)

`build/moving_platform_test.zip`: the full RPX (the standard build plus
`tools/stage_script_cave.py`) and `stage/melee/NewStage01` (the Plains build plus
`tools/moving_platform_test.py`'s platform). A 3-block hay bale platform circles over the middle of
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
