# Minecraft World (Smash Ultimate) on NewStage01

Status: **built, not tested in game yet** (the first in-game try, the moving-platform test, froze
while loading; see "Freeze"). The whole normal-play stage (not the Battlefield form) converted
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
- `tools/nut.py ntp3`: new NTP3 textures (untiled; the game's own Battlefield has NTP3
  `model.nut`s, and the header matches them).
- `tools/nud.py`: NUD read / write. Checked by rewriting every static Battlefield model with it:
  byte-identical except the bounding spheres it recomputes (and one unused vertex field).
- `tools/lvd.py`: Smash 4 LVD read / write (Battlefield's melee and Omega files round-trip
  byte-identical).

## The conversion

- **Models**: every Ultimate mesh becomes a NUD mesh: positions, normals (half float), vertex
  colors from `colorSet1` (Ultimate 0.5 = 1.0 maps to Battlefield's 127 = 1.0; the other color
  sets are shader inputs, e.g. the backdrops' `colorSet5` is a constant 0.33), the first UV set
  (same orientation in both games, checked by rendering Battlefield's own models), triangle lists.
  Meshes under a bone (doors) are moved by the skeleton. The blocks are placed from the breakable
  file (every block, every depth) and merged into one mesh a material.
- **Materials** are Battlefield's: `0xA4001041` (its ground: lit, vertex colors, shadows) for the
  island, blocks, plates, doors and farm, with an alpha test (`>= 128`) for the block atlas'
  cut-outs (leaves, grass, flowers) and nearest filtering (pixel art). `0xA2000001` (its background
  plane) for the panorama (alpha-tested sky cut-out) and the sky. Cull mode from Ultimate's.
- **Textures**: only the NTP3 forms the game's own files use (Battlefield's models, the UI): RGBA8
  and DXT5 with one mip, DXT1 with a full mip chain, power-of-two sizes. The block atlas (512x512)
  is RGBA8, one copy for the island and the blocks (Ultimate's `_for_programBlock` copy has the same
  layout, slightly different tones); the panorama 2048x1024 DXT5. Texture IDs `0x2000F001`... (the
  game's are `0x2000xxxx`). v1 used RGBA8 / DXT5 with mips, a 36x36 texture and IDs `0x204Dxxxx`:
  the moving-platform test froze while loading the stage (user), which is the first suspect.
- **Sky**: Ultimate colors the sky dome in its shader (its vertex colors are only shading), so the
  dome gets a fixed day gradient. Clouds at 70% opacity (from under the layer they'd hide most of
  the sky). Sun kept; moon, stars and fog layers not.
- **Model folders**: Battlefield's names are kept (whether the generic stage enumerates the folder
  isn't known). `stc_c_Ring_set`: everything on the block atlas; `stc_k_BG_most_far2`: the panorama;
  `stc_o_BG_clouds_set`: the sky. Every other folder gets an empty model (one zero-size triangle,
  a transparent 4x4 texture). Melee's `stc_a_surinuke_set` isn't empty in Battlefield (it holds
  Battlefield's pass-through platforms), so it's emptied too. The replaced folders' `model.mta`
  (material animations) are removed.
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

## Freeze (user) and tests

The moving-platform test build froze while loading the stage. Not the cause (checked): the link
manager rigged collision needs exists on every stage (made in the base constructor,
`0x03140B78`); the generated lvd has Battlefield's layout (no zero-length lines, unit normals,
ledges on their lines); a cave keeping data next to its code (strike_cave.py's counters already do).
Fixed on suspicion: the texture forms and IDs (above). `build/freeze_tests.zip` splits it:
1 Minecraft World alone (current RPX), 2 the moving-platform test, 3 Minecraft models with
Battlefield's collision, 4 Battlefield's models with Minecraft collision, 5 the new RPX with the plain
Battlefield copy.

## Ultimate files (user)

`param-SSBU.zip` is Ultimate's top-level `param/` (game, spirits, sound settings). `pickel_world.zip`
is the stage's dump with its `param` folders (used above). `ui-SSBU.zip` has the stage pictures
(`ui/replace_patch/stage/stage_0`-`stage_4/stage_N_pickel_world.bntx`: the "MINECRAFT" logo, a small
icon, the normal / Omega / Battlefield-form previews) and the series symbol
(`ui/replace_patch/series/series_0|1/series_N_minecraft.bntx`, a cube).
