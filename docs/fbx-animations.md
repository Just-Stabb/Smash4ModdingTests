# FBX animations from Blender -> Smash 4 motions

```
python3 tools/fbx_anim.py ANIM.fbx MODEL.vbn PACDIR MOTION OUTDIR [--check] [--all]
```

For animations made in Blender on a Smash 4 armature (the fighter's model imported, its motion
edited, exported with Blender's FBX exporter). `tools/fbx_bin.py` reads the binary FBX (7.x);
`tools/fbx_anim.py` evaluates every bone's channels (Lcl Translation / Rotation Euler XYZ degrees /
Scaling, linear keys, 60 fps; the stack's LocalStop + 1 frames), converts them to the game's bone
space and writes MOTION's omo into each pac of PACDIR that has it (`OUTDIR/<pac>.pac`, the rest of
each pac kept; the omos also in `OUTDIR/omo/`).

- **Axes:** Blender's exporter turns each bone's local axes 90 degrees about Z (game `(x, y, z)` =
  FBX `(y, -x, z)`): a bone's game local = `C^-1 L C`; the root TransN also carries the scene's
  axis change, its rest transform (identity in game): `(L_rest C)^-1 L C`. Checked on Bowser's
  Attack11 (user's BUNDYA11): frames 0-5, unedited, match vanilla's to 0.003.
- **Bones per pac:** each pac's motion keeps its vanilla bone list and order (main = the joint
  table's 26 in vbn order: see docs/ganon-dark-dive.md v5). Blender's `*_end` leaf bones are skipped.
- **Untouched part pacs:** Blender imports only main.pac's motion, so bones the user never animated
  sit at the model's rest pose in the FBX (checked: 0.000 from model.vbn). A part pac (not main)
  whose bones stay at rest for the whole FBX keeps its current motion (Bowser's fists, toes, mouth);
  `--all` writes them anyway.
- `--check` prints each motion's largest difference from the current one on the frames both have.

## Bowser's jabs (user, `build/bowser_jab_anims.zip`)

BUNDYA11 -> Attack11 (69 frames, vanilla 31): main + lhand from the FBX, rhand / koopapt1 /
koopapt2 kept. BundyA12 -> Attack12 (62 frames, vanilla 33): main + lhand + koopapt1 (tail), rhand
/ koopapt2 kept. Built on vanilla Bowser's pacs. game.bin still vanilla-timed (Attack11 hitboxes
frame 7, Attack12 frame 9); the new strikes reach furthest at frame 13 (Jab 1, LHandN) and 6
(Jab 2, RHandN).

## Bowser jabs v2 (`build/bowser_jabs_v2.zip`): hitboxes on a bone that isn't a joint, a fart

User: hitboxes matching LIndex3N, from the finger to the nail Jab 1 stretches out (LIndex3N's X scale
1 -> 28.5 -> 1 over frames 7-39), and a fart on Jab 2.

- **The nail's size:** the FBX's skin clusters (Blender writes each cluster's `Transform` as the
  mesh -> that bone's space, so no `TransformLink` needed): the 85 vertices weighted > 0.5 to
  LIndex3N run 0 -> 2.895 along its X (game axes: `C^-1`), radius 1.19; LIndex1N / LIndex2N's 1.18.
- **The hitboxes:** LIndex3N isn't in the joint table (Bowser's 26 + table 1's 16), so both are
  `Extended_Special_Hitbox` capsules on LHandN (ACMD joint 0x11), set every frame 7-39 from that
  frame's pose (`inv(W_LHandN) @ W_bone @ p`): ID 0 LIndex1N -> LIndex3N (1.18), ID 1 LIndex3N ->
  (2.895, 0, 0) in LIndex3N's stretched space (radius x its Y / Z scale): 5.1 long at frame 7, 82.5
  at 17-29. Damage / knockback: vanilla Attack11's ID 1; vanilla's arm intangibility kept; Attack12
  allowed from 40 (vanilla 11). Same IDs re-set each frame, no removal in between (expected to keep
  the hit list; not tested).
- **The fart:** `EFFECT_COLOR` common smoke puff `0x1000021` at TailNa (table-1 joint 1006) at
  frames 20 (size 1.6) and 24 (1.1), tint (150, 200, 40), as Jab 2's tail lifts (tip 1.6 -> 11
  up over frames 6-20).
