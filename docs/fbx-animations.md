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
