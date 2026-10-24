# Porting an Ultimate fighter's model and animations to Smash 4

`tools/ultimate_fighter.py` (first used for Sephiroth, `fighters/edge/README.md`) turns Ultimate's
SSBH files into a Smash 4 fighter's model folders and motion pacs, on the fighter's own skeleton,
inside a new kind built on a base fighter (docs/kind-expansion.md).

```
python3 tools/ultimate_fighter.py model SRC/model/body/c0N BASE/model/body/c0N OUT/c0N --empty EMPTY_DIR [--joints SwordL1,SwordR1] \
    --max-bones 136 --motions SRC/motion/body/c00 --anim-cache CACHE.json
python3 tools/ultimate_fighter.py motions SRC/motion/body/c00 SRC/model/body/c0K BASE OUT [--add C00Attack12,...] \
    [--joints ...] --max-bones 136 --anim-cache CACHE.json
```

`EMPTY_DIR`: Cloud's `model.sb` (12 bytes, no swing bones) and Kirby's `model.nhb` (64 bytes, no
helper bones). `c0K` for the motions: the costume whose skeleton has every bone (Sephiroth: c06).

## What the game ties to the skeleton (Zelda's model folder)

| file | keyed by | done |
|---|---|---|
| `model.vbn` (LE `' NBV'`, counts by bone type 0/1/2/3) | bone hashes: the same for a name in every fighter (not CRC32, not a known function), so the standard bones copy the base's | ours: the base's 26 standard bones first, then Ultimate's (CRC32 hashes), all type 0 |
| `model.jtb` | ACMD / effect joint ids -> bone index (table 0: id n = entry n - 1) | the base's, each index moved to our bone of the same name (armor bones -> stand-ins) |
| `model.ik` (`CRIK`) | bone indices 3-6, 7-10 (the legs) | kept: our first 26 are the base's |
| `model.nhb` (`' BHN'`, LE) | helper (HLP) bones by hash | empty (Kirby's) |
| `model.sb` (`' BWS'`, LE) | swing (SWG) bones by hash, physics | empty (Cloud's); `model.sbwl` left out |
| `model.moi` | mesh name prefixes (a hash we can't compute), a VIS flag, a bone, the mesh index | kept, so the NUD keeps the base's 32 mesh names in order |
| `material_anime_eyelid / face.pac` (MTA per motion) | visibility by **mesh name** (`Zelda_Openblink_Eye_VIS_O_OBJ`...), material UV animations by material hash | rebuilt per motion: the base's eye / mouth keys, plus the swords' (from Ultimate's visibility tracks) and the wing (hidden) |
| `motion/*/main.pac` | OMO nodes by bone hash; entries by name (`FitZeldaBodyMain<Motion>.omo`) | the base's entry list, each Ultimate motion of the same name (stand-ins in `MOTION_STANDINS`) |
| `motion/*/lhand / rhand.pac` | the base's hand poses (they turn `LHandN` / `LHaveN`) | every entry one constant node on a bone we don't have |
| `zeldapt1 / sw1 / sw2.pac` | the base's own bones (swing, parts) | kept (none of our bones) |

## Skeleton

The 26 bones the game, the IK and the joint table know (`TransN` ... `ThrowN`) come first, in the
base's order, from Ultimate's `Trans` ... `Throw` (`STANDARD`). Ultimate puts `LegC` between `Hip`
and the legs and `ClavicleC` between `Bust` and the clavicles; Smash 4 hangs legs and shoulders from
`HipN` / `BustN`, so those two are folded into their children (bind and every frame: parent's local
x child's local), and stay as extra bones for the vertices weighted to them. Then Ultimate's other
bones, parents first, leaving out bones nothing is skinned to (end markers, unused helpers): vanilla
fighters have at most 138 bones (Dr. Mario), Sephiroth 172 (124 in his second outfit).

**Bone budget** (`--max-bones 136`, Zelda's count): past it, leaf bones are merged into their parents
(their vertices re-weighted there), the ones no motion moves first (`--motions`: the Ultimate motions
read once, cached in `--anim-cache`), then those with the fewest vertices; never the standard bones,
the folded ones or `--joints`. The motions use every costume's kept bones (Sephiroth: 154 animated
nodes; a costume ignores the ones it lacks, as Bowser Jr's motions do for the Koopalings).

**NUD header 0x0C / 0x0E** (`nud.write`): the first and last bone index the vertices use. Every vanilla
fighter: 2 to N (Zelda 2-135, Bowser 2-78), no vertex on TransN / RotN. Ours were 0 to bone count - 1:
Incineroar (0-142) drew as a stretched red pillar, Sephiroth (0-171) crashed on loading. Now: vertices
on bone 0 / 1 go to HipN (including the empty meshes that fill unused slots), and the header holds
the range the vertices really use (Sephiroth 2-131 / 2-109, Incineroar 2-135).

Packaging: leave out `model.sbwl`; keep the base's other motion pacs (`zeldasw1 / sw2 / pt1.pac`,
`koopapt1-3.pac`) next to the new `main.pac` / `lhand` / `rhand`.

VBN bind: position, Euler angles with R = Rz Ry Rx (Sm4shCommand's `EulerToQuat`), scale.

## Meshes and materials

Every polygon rigged as the base's body (vertex type `0x47`: byte colors and half UVs in the vertex
section; position, half normal / bitangent / tangent with w 1, four bone bytes and four byte weights
summing to 255 in the "vertex add" section; mesh bind 4), positions in bind space (a mesh Ultimate
binds to one bone: weighted 1.0 to it). `tools/nud.py` writes these (`Polygon.bones`).

Mesh slots (`MESH_SLOTS`): each Ultimate mesh goes into the base mesh that plays its part (eyes open,
half blinks, blink, mouth shapes; body; hair; left sword in Zelda's `skirt_VIS_O_OBJ16`, right sword
in `polySurface5817_VIS_O_OBJ`, the wing in `Zelda_DamageFlyFront_VIS_O_OBJ`); an unused slot gets an
empty triangle.

Materials: the base's skinned body material (`0x9A011063`: color, normal, ramp `0x10080000`), opaque
or alpha-blended (src / dst 1). Textures (`0x40EB0000` up, power-of-two, one mip):
- color: Ultimate's col x ambient occlusion (prm blue) brightened by emission; cut-out texels get
  their neighbours' color (BC7 leaves noise there);
- normal: Ultimate's XY, Z rebuilt, alpha = smoothness (prm green inverted);
- eyes: the iris (second UV set) drawn onto the white.

`tools/nutexb.py` decodes BC7 now (Pillow's BCn decoder).

## Motions

Per motion, per frame: Ultimate's animated locals (bind where a bone has no track), the folded chains
multiplied, helper bones (`model.nuhlpb` orient constraints: a share, axis by axis, of the source
bone's turn from its bind in the parent bone's frame) -> OMO (constant tracks stored constant,
others interpolated 16-bit). Aim constraints are not done (H_Collarbone in the second outfit).

## Moves (`tools/ultimate_acmd.py`)

Ultimate's hitboxes are in its ACMD, decompiled to smashline Rust (WuBoytH/SSBU-Dumped-Scripts,
`smashline/lua2cpp_<fighter>/<fighter>/<Motion>.txt`); `ultimate_acmd.py` turns the normals, grabs,
throws and get-up / ledge attacks into the base's `game.bin` scripts (`TRANSLATE`):

```
python3 tools/ultimate_acmd.py DUMP/edge BASE/script/animcmd/body/game.bin OUT/game.bin OUT_MODEL/c00 \
    --others BASE/script/animcmd/body OUT --motion-list SRC/motion/body/c00/motion_list.bin \
    --mtable BASE/.../motion.mtable OUT/motion.mtable --vl VL_IN VL_OUT --base-rpx RPX --base-kind 0x10
```

- `ATTACK` -> `Extended_Special_Hitbox` on the joint id of the same bone (`model.jtb`; the sword bones
  are added to the joint table with `model --joints SwordL1,SwordR1`), `CATCH` -> `Extended_Grab_Collision`,
  `ATTACK_ABS` / `ATK_HIT_ABS` -> `Throw_Specifier` / `Throw_Applier`, status flags -> the Smash 4
  variables vanilla scripts set for the same thing. Frame numbers carry over as they are: both games
  number the first active frame the same way (Mario's jab: `FRAME 2`, active on frame 2).
- Smash 4 has one script name per side tilt / smash (`attacks3`, `attacks4`; `attacks3hi` / `lw`
  are the angled tilts), not `attacks3s`.
- Cancel frames: Ultimate's `motion_list.bin` extra bytes {intangible start, end, cancel frame} are
  `fighter_param_vl` group 1 bytes 3 / 4 / 2 (Cloud's DownAttackU: 46 / 1 / 26 in both), so the
  moves end when Ultimate's do without cutting the animations.
- The base's effect / sound scripts of the translated motions are emptied (they'd play the base's).
- A motion the base has no slot for (Attack12 / 13 on a one-jab base): `motions --add C00Attack12`
  adds the animation to `body/main.pac`, the kind's `extra_kinds.json` "motions" points its motion
  table entry at it, the translator adds its `motion.mtable` entry; the jab count is fighter_param
  `attack_1_count` (read by the common MSC every fighter's `.mscsb` carries).

## Checked here

- The NUD read back (an independent reader of the written bytes) and rendered in bind pose and posed
  by frames of the written OMOs (Wait1, AttackS4S, Run, AttackAirB, AttackHi4; c00, c03, c06).
- The MTA visibility writer: the base's visibility entries round-trip.

## Not known yet (in game)

- Test 19 (`build/fighters_fix_test19.zip`): whether the 2-N header and the 136-bone budget fix the
  pillar / crash.
- Whether the empty `.sb` / `.nhb` and a model without `.sbwl` load.
