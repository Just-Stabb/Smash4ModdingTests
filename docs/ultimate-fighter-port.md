# Porting an Ultimate fighter's model and animations to Smash 4

`tools/ultimate_fighter.py` (first used for Sephiroth, `fighters/edge/README.md`) turns Ultimate's
SSBH files into a Smash 4 fighter's model folders and motion pacs, on the fighter's own skeleton,
inside a new kind built on a base fighter (docs/kind-expansion.md).

```
python3 tools/ultimate_fighter.py model SRC/model/body/c0N BASE/model/body/c0N OUT/c0N --empty EMPTY_DIR
python3 tools/ultimate_fighter.py motions SRC/motion/body/c00 SRC/model/body/c0K BASE OUT
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

## Checked here

- The NUD read back (an independent reader of the written bytes) and rendered in bind pose and posed
  by frames of the written OMOs (Wait1, AttackS4S, Run, AttackAirB, AttackHi4; c00, c03, c06).
- The MTA visibility writer: the base's visibility entries round-trip.

## Not known yet (in game)

- Whether 172 bones skin right (vanilla fighters stop at 138); if not, fold the face and finger bones.
- Whether the empty `.sb` / `.nhb` and a model without `.sbwl` load.
