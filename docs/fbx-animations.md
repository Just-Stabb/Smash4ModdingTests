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

## Bowser jabs v3 (`build/bowser_jabs_v3.zip`): weak pull-in, a tipper, Wario's fart

User: the nail's end a lower-priority 8% tipper that launches; the rest of the nail and the finger a
3% `Extra_Extended_Special_Hitbox` with 1.4x hitstun that pulls the opponent in through the finger
and nail until they're right in front of him; Jab 2 with Wario's fart.

- **Hitboxes** (frames 7-39, every frame from the pose, on LHandN): ID 0 finger, ID 1 nail from
  LIndex3N to `tip - 2r` (so it doesn't cover the tipper: a lower ID wins where they overlap), both
  3%, angle 180 (toward Bowser), KBG 100, FKB 50, `HitstunMul` 1.4; ID 2 `Special_Hitbox` sphere at
  the tip (radius = the nail's), 8%, angle 40, KBG 80, BKB 105.
- **The pull** (frames 7-68): `Float_Var_Compare(0x0F000050 > 0)` (the last fighter hit is in
  hitstun) and `0x0F000051 <= 37.5` (the hitstun it dealt: the weak FKB 50 hit gives about 27-35
  with x1.4 across weights; the tipper's BKB 105 at least 42), then: on the first such frame their
  Y offset is kept in `VAR_1` (`SET_FLOAT 0`, `SUB_FLOAT_2(VAR_1, 0x0F000056)`: -Y), each frame
  `SUB_FLOAT_2(0x0F000055, VAR_0)` with `VAR_0` = 3.5 (3.5 closer), clamped at 15 in front
  (`SET_FLOAT`), Y put back (`SET_FLOAT 0` then `SUB_FLOAT_2(0x0F000056, VAR_1)`), and while further
  than 15 their hitstun left set to 6. The nail is within 9 degrees of horizontal over frames 7-39
  (tip up to 138 in front), so the pull is horizontal. `ADD_FLOAT`'s handler is empty in this game
  (`0x02BE6E80`), hence `SUB_FLOAT_2` (WorkModule add, hooked by `position_vars_cave.py`).
- **The fart:** `Ptcl.import_set` (new: `import_emitter` per emitter plus the primitive mesh,
  `Ptcl.primitive` reading it) copied Wario's `PtcWarioPpeL` / `PtcWarioPpeL2` into Bowser's bank
  (sets 20 / 21, `.efc` entries 0x15 / 0x16 with Wario's 0x100 flags: `0x30F0015` / `0x30F0016`),
  validated. Scripted as Wario's big waft (`0x430A9E8F`: PpeL `EFFECT_COLOR` (0, -90, 0) on bone 0,
  common `0x1000008`, PpeL2 `EFFECT_FOLLOW_COLOR` on his HipN at (-90, -90, 0), his colours) at
  Jab 2 frame 20 / 21, at Bowser's TailNa (TransN (-0.5, 7.5, 4.5): he has turned his back to the
  front there, head at Z -4.4), turned 180 degrees about Y, size 1.8 (hip heights 10 / 4.2); PpeL2's
  angles are Wario's hip (SpecialLwLR frame 7) x the script's turn on TransN, turned: (-176.1, -55.5,
  149). No sound (user).

## Kirby's Donkey Kong copy: no special fall (`build/kirby_dk_copy_nofall.zip`)

Status `0x1BA` (the copy's Giant Punch, `fighters/kirby/kirby.c` `func_2649`): at its motion's end
in the air it went to `0x10` (SpecialFall); now `0xE` (Fall), as its cancel `0x1B9` already did.

## Kirby's R.O.B. copy: R.O.B.'s laser at Kirby's height (`build/kirby_robot_laser.zip`)

User: the copy's neutral special from R.O.B.'s (user-edited) SpecialN / SpecialAirN, hitbox lowered to
Kirby. Vanilla Kirby's game.bin has no `RobotSpecialN` / `RobotSpecialAirN` (motions `0x3A2` / `0x3A3`):
the copy's motion helpers (`func_3419` / `func_3420`) ran R.O.B.'s own game script
(`MotionAnimcmdModule(0, 0, 0x211 / 0x215, 0x1F)`), whose joint `0x42B` (R.O.B.'s table 1, his head)
is another bone on Kirby. Kirby's own effect script for it uses `0x13` (HeadN: table 0 id n = entry
n - 1, TransN ... HeadN 19 ... ThrowN 26 as in every vanilla jtb seen) with R.O.B.'s offsets and angles.

- `tools/kirby_robot_laser_acmd.py`: R.O.B.'s specialn / specialairn into Kirby's game.bin (added),
  effect.bin and expression.bin (replaced) as robotspecialn / robotspecialairn, joints `0x42B` /
  `0x42C` -> `0x13`, JUMPs to specialn -> robotspecialn. sound.bin kept (R.O.B. has no SpecialN
  sound script; Kirby's plays `0x7F0000`).
- Height (frame 24 of each one's animation): the hitbox line (1.5, 0, 0) -> (51.1, 290, 0) starts at
  6.9 on Kirby (R.O.B.'s Head1N / Head2N: 11.9 / 14.6) and ends at 37 (R.O.B. about 60), same angle.
- `func_3419` / `func_3420`: R.O.B.'s game script only for customs (`copy_custom_index != motion`).
- The user's effect script plays `0x250032` (R.O.B.'s FinalEnd sound, his se bank row `0x25`), which
  Kirby's banks don't hold (sound ids match the playing fighter's banks): likely silent on Kirby.
