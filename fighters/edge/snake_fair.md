# Sephiroth: held forward air (the extending sword)

**Status: off since test 80.** Test 79 (below) crashed the game as he loaded: posing 15 joints of his model from MSC
overruns the model's joint-override list (fighters/edge/README.md test 80, `port_check` C6). The runs have to be
drawn another way (articles or effects); the design and the MSC / ACMD below stay for that.

The user's design (not Ultimate's): forward air is unchanged when tapped. Held 6 frames or longer, the sword
"extends" like the game Snake. Its base stays in his hand, its body grows from the base, and its point stays at the
end.

- **Steering:** the tip moves in the cardinal direction held on the stick: forward, up, down or back,
  relative to his facing.
  - It can turn at most every 8 frames, never straight back on itself, and never across its own body.
  - It can't go back until the tip is 24 units past the sword's normal reach.
  - With no direction held, it stops.
- **Release:** letting go of attack sends the sword back along its path to where it started.
- **Catching:** whoever the tip hits stays stuck where they were hit, relative to the sword. They ride back
  along the path with it, then take a second hit.
- **Trail:** the sword trail follows the moving tip.

The user's numbers:
- 3 units a frame, 300 at most.
- Slightly lower gravity while extending.
- Normal landing lag; landing drops anyone caught.
- Only the tip catches.
- The catch does 5%. The end hit does 11% at fair's angle, with much less knockback growth so it combos.

## Pieces

| Part | Where | What |
|---|---|---|
| Model | `tools/snake_sword.py`, `ultimate_fighter.py model --snake` | See "Model" below |
| MSC | `tools/edge_snake_msc.py` writes the `SNAKE FAIR` block of `fighters/edge/edge.c` | See "MSC" below |
| ACMD | `tools/edge_specials_build.py` `snake_fair_scripts` | See "ACMD" below |

**Model.** The bones are added to every costume:
- **EdgeBladeL** (joint 1005), at SwordL1: the real blade, which is folded away while the extended one is out.
- **EdgeSnake01–13** (joints 1006–1018), under TransN: one straight run each. Each carries a ring-to-ring
  slice of the blade, one unit long along +X.
- **EdgeSnakeTip** (joint 1019): the point, also one unit long.

The pieces are drawn twice, crossed, so a run looks the same width turned any way. Every new bone's bind is the
identity, so the joint ops mean the same whether they replace or add.

To make room in the 136-bone budget, 15 bones were folded: 5 finger tips, the upper-lip bones and the centre of
the lower lip. The skirt bones are protected. `--materials-from` keeps test 58's materials on every existing
polygon.

**MSC.** The block hooks into four places:
- **Aerial status main (`func_315`), `edge_sn_init`:** starts the hold check if this is fair with attack held.
- **Aerial status loop (`func_319`), `edge_sn_loop`:**
  - The hold check, then the freeze at frame 13.
  - Steering, then retracting.
  - Catching and holding fighters.
  - Posing the bones every frame.
  - 0.7x gravity.
- **Aerial status end (slot 2, was the empty `func_334`), `edge_sn_end`:** landing or any interruption drops
  the caught fighters and puts the sword back.
- **Per-frame line (`func_74`), `edge_sn_frame`:** keeps the snake's pieces hidden outside the move.

The runs live in this object's `VAR_0`–`VAR_12` (direction × 1000 + length), because the MSC's globals must stay
under 0x86 (`port_check` C5). The caught fighters are kept per player slot.

**ACMD.** `VAR_23` is the flag: 0 for the normal move, 1 held, 2 for the end hit.
- The tapped move's hitboxes (frames 13 and 15) and effects (frame 13) only run at 0.
- Held, frame 13 brings out the tip catch: 5%, BKB 20, KBG 0, on joint 1019.
- The 11% end hit is on the sword (joint 24, fair's three blade capsules, each 2 bigger), with fair's 361
  angle and KBG 40 (fair's: 86). It runs on frames 14–18, after `Hit_Log_Clear(-1)`. Frame 14 only comes once
  the motion runs again, after the retract.
- The trail is his own sword trail (textures 0x104 / 0x105). Its two points sit across the tip, so the ribbon
  sweeps along the tip's path.

## The move, frame by frame

1. **Frames 0–6:** forward air starts with attack held. Released before frame 6, it's the normal fair (C-stick
   fairs always are).
2. **Frames 6–13:** held. `VAR_23` is 1, which turns off the normal hits and effects.
3. **Frame 13:** the sword points straight ahead (Ultimate's `c05attackairf` frame 13: swordl1's +X =
   (0, -0.027, 1)). The motion freezes (`MotionModule(4, 0)`) and the real blade folds away.
   - The path starts as one forward run from the blade's start, (−0.51, 13.35, 11.06) in model space. Its
     length is the blade's body (21.98); the point (3.48) follows it.
4. **Extending, while attack is held.** The tip moves 3 a frame in the held direction:
   - A turn starts a new run, if it's been 8 frames since the last one and it isn't straight back.
   - Back needs the tip 24 units past the normal reach.
   - The tip and its point never come within 3 units of an earlier run.
   - The path stops growing at 300.
   - A fighter hit by the tip whose feet are within 22 of it is caught: its place along the path and its
     offset from the tip are kept.
   - Each frame, caught fighters are put back there, with hitstop 2 and hitstun 20 refreshed, so they hang
     frozen.
5. **Retracting, once attack is let go.** The path shortens from the tip end by 6 a frame. Caught fighters move
   back along it by the same amount, gathering on the normal blade (at least 60% of its body out).
6. **Back to normal length.** The motion runs again and `VAR_23` becomes 2: the end hit on frames 14–18, then the
   rest of fair as normal.
7. **Landing at any point:** the status ends with fair's normal landing lag. Caught fighters drop (hitstun 0) and
   the sword returns to normal.

## Not proven in game

- **The joint ops.** That ModelModule ops 0 / 1 / 7 (scale / rotate / translate) take table-1 joint IDs (1005+).
  They have been seen on table-0 joints (up special's pitch on joint 2).
- **Op 7.** That op 7 is the joint translation, in the parent's (TransN's) frame.
- **Turn signs.** The turn signs: forward is Ry −90, back Ry +90, up Rz +90, down Rz −90 (the bone's +X onto the
  direction). If a direction comes out mirrored, swap the sign in `edge_sn_piece`.
- **Following moved bones.** That hitboxes and the trail follow bones the MSC moves. The game reads joint
  matrices for both, so they should.
- **Folded bones.** That motions still carrying tracks for the folded bones (lips, finger tips) skip them. Bones
  are matched by name hash, and the shipped motions weren't rebuilt.
