# Sephiroth: held forward air (the extending sword)

**Status: test 87.** Test 79 posed 15 joints of his own model from MSC and crashed the game as he loaded (the
model's joint-override list overran: fighters/edge/README.md test 80, `port_check` C6). Since test 82 the extended
sword is 13 articles, each posing itself; his own model only hides its real blade (one joint, at the start and end
of the move). Test 82's articles had no MotionModule (their base, Zelda's light arrow, has none), so the point's
hitbox and trail never ran; since test 83 they have one (README test 83). Test 84: the trail across the point in
the screen plane, the articles facing his way (README test 84). Test 85: the pieces' base off HaveN (drawn at his
feet), the real blade hidden through joint 0x7EA (README test 85; wrong). Test 86: the pieces rebased on dein with a model
(the light arrow's native code drew them at his feet), the blade on joint 1003 (README test 86).

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
| His model | `tools/snake_sword.py`, `ultimate_fighter.py model --have SwordL1,SwordR1 --snake` | **EdgeBladeL** (bone 26 in every costume) under SwordL1, holding the real blade so it can be hidden |
| His MSC | `tools/edge_snake_msc.py` writes the `SNAKE FAIR` block of `fighters/edge/edge.c` | Hold check, steering, retract, catching, the articles |
| His ACMD | `tools/edge_specials_build.py` `snake_fair_scripts` | The tapped move's hits gated, the 11% end hit |
| Article kinds | `tools/extra_kinds.json`: `snake` 0x199 (up to 12), `snaketip` 0x19A (one, kept on hit) | Copies of Zelda's dein (as fire / flare / flash, which place themselves) given a model (`"flags_set": "0x40"`); his articles 9 and 10 |
| Article models | `tools/edge_snake_articles.py` → `model/snake`, `model/snaketip` | A run, and the point |
| Article MSC | `tools/edge_snake_articles_msc.py` → `fighters/edge/weapons/snake.c`, `snaketip.c` | Each places itself on the path every frame |
| Article ACMD | `tools/edge_specials_build.py` `snake_article_scripts` | The point's 5% catch and the sword trail |

**His model.** EdgeBladeL is added at bone 26 (right after the 26 standard bones), so its number is the same in
every costume. The blade's mesh hangs from it; the hilt stays on SwordL1. The MSC hides the blade with ModelModule
scale on joint 1003 (his joint table 1's 4th entry, bone 26, in every costume: the overrides are the MotionModule's,
by joint ID as ACMD's) when the sword extends, and scales it back to 1 when it's back (ModelModule 2, the "clear",
left it hidden: test 86). If a move ends with it hidden, the next aerial shows it (`edge_sn_hid`). That's one joint; vanilla scripts
pose one or two. `--materials-from` keeps test 58's materials. To keep 136 bones, one bone is folded (UplipL1);
test 79's 15-bone fold is gone with `segments: 0`.

**Article models.** Four bones each: TopN (the root), HaveN, EndN and BaseN, all children of TopN with identity
binds. Nothing is on HaveN: the light arrow's kind (flag 0x10, a held weapon) draws HaveN on its owner, so test 84's
pieces had their base at his feet.
- **snake** (a run): one ring-to-ring slice of the blade, along +Z. Its near ring is on BaseN and its far ring on
  EndN, both at z = 0 in the bind, so it draws nothing until its MSC moves EndN out to the run's length (ModelModule
  7 on joint 0x7D2: weapons name their joints 0x7D0 + bone, as Mario's pump).
- **snaketip** (the point): the blade's point on BaseN, its real length (3.48) along +Z.
- Both are drawn twice, the second copy turned 90 degrees about the blade, so they look the same width turned any
  way. Their material is the sword's own; its two textures are copied into the article's `model.nut` under ids
  0x40EBF000 + k. `model.sb / .nhb / .mta / .xmb` are the light arrow's.

**His MSC.** The block hooks into three places:
- **Aerial status main (`func_315`), `edge_sn_init`:** starts the hold check if this is fair with attack held.
- **Aerial status loop (`func_319`), `edge_sn_loop`:**
  - The hold check (attack held from the start through frame 21: the tapped move's hits come out first), then the
    motion back to frame 13, held there: the blade hidden, the path published, the 12 runs and the point generated
    (ArticleModule 0x2710, articles 9 and 10).
  - Steering, then retracting.
  - Catching (a fighter in hitstun whose feet are within 22 of the tip) and holding the caught fighters.
  - Publishing the path every frame.
  - 0.7x gravity.
- **Aerial status end (slot 2, was the empty `func_334`), `edge_sn_end`:** landing or any interruption drops the
  caught fighters, shows the blade, and tells the articles to go.

The runs live in his private `VAR_0`–`VAR_11` (direction × 1000 + length), because the MSC's globals must stay
under 0x86 (`port_check` C5). The articles read his path from his slot-shared variables (`VAR_24`–`VAR_31`, which
any object reads as `SLOTn_SHARED_k`):
- **VAR_24–VAR_29:** the runs, two to a variable: run 2i+1 in the low 12 bits, run 2i+2 in the next 12. A run's
  code is direction × 1024 + length × 2 (0 forward, 1 up, 2 back, 3 down, relative to his facing).
- **VAR_30:** the length drawn (the path retracts from its end). Below 0: the move is over and the articles go.
- **VAR_31:** a counter. Each run article, made, takes the next number: run k draws the path's k-th run.

**Article MSC.** Status 0 of the light arrow is replaced (its motion offset, `func_40`, isn't installed). Each
article finds its owner (the nearest Sephiroth), then every frame:
- **A run** walks the path to its own run's start, places itself there (PostureModule 0x2714 from his position and
  facing), turns along the run (0x2717, (−angle, 90, 0), as Pit's arrow: the world's angle, so 180 − pitch facing
  left) and stretches EndN to the run's drawn part (0 when that run isn't drawn).
- Both take his facing (`PostureModule(0, lr)`): a fighter the point hits takes it (none: facing the camera, test 83).
- Both are placed before their motion starts, so the point's trail begins where the point is.
- **The point** sits at the path's drawn end, turned along the last drawn run.
- Both remove themselves when VAR_30 goes below 0, when he's gone, or after 900 frames (a safety net).

**ACMD.** `VAR_23` (his) is the flag: 0 for the normal move, 1 held, 2 for the end hit.
- The tapped move's hitboxes (frames 13 and 15) and effects (frame 13) only run at 0.
- The 11% end hit is on the sword (joint 24, fair's three blade capsules, each 2 bigger), with fair's 361 angle and
  KBG 40 (fair's: 86). It runs on frames 14–18, after `Hit_Log_Clear(-1)`. Frame 14 only comes once the motion runs
  again, after the retract.
- **The point's game script:** the catch, 5%, angle 361, BKB 20, KBG 0, size 4.5, on its root at the point's middle.
  After a hit, the point clears its hit log (AttackModule 0x2726 / 0x2724), so it can catch the next one.
- **The point's effect script:** his own sword trail (textures 0x104 / 0x105), its two points 1.5 either side of the
  point along its local Y (across the blade in the screen plane, whichever way it runs), so the ribbon sweeps along
  the tip's path. Test 83's were across X and Y both: X is depth once turned, a wide diagonal wedge.
- The run's scripts are empty. Both articles' one motion is the light arrow's (`Move`, 0xEF3E3778).

## The move, frame by frame

1. **Frames 0–21: the tapped move.** Forward air plays as normal, its clean hit (frames 13–14) and late hit (15–18)
   included, whatever the button does (the user, after test 82: the hold window starts after the tapped move's
   initial hitbox). Let go of attack before frame 21 (or a C-stick fair), and it stays the normal fair.
2. **Frame 21, attack held since the start (frames 15–21 the hold window, 6 frames after the clean hit):**
   `VAR_23` becomes 1, which turns off the normal hits and effects from here on.
3. **Back to frame 13:** the motion restarts at frame 13 (`func_22`: the aerial's motion, int `0x11000002`), where
   the sword points straight ahead (Ultimate's `c05attackairf` frame 13: swordl1's +X = (0, -0.027, 1)), and freezes
   there (`MotionModule(4, 0)`); the real blade folds away.
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

- **Op 7 on a weapon.** That ModelModule op 7 (translate) moves a weapon's joint 0x7D2 (EndN) in TopN's frame. If
  the runs never show, or show one unit long, this is it.
- **The copies' modules.** That the light arrow's copies, given dein's MotionModule (slot 7) and slot 5, draw their
  own model and run their ACMD (the earlier copies, fire / flare / flash, are dein's and have no models).
- **The rewind.** That restarting the motion at frame 13 leaves the script with nothing to replay (its frame-13 and
  15 hits are off at `VAR_23` 1) and runs frame 14's end hit when the motion runs again.
- **12 at once.** That a kind takes 12 instances (`extra_kinds` `max: 12`).
- **Turn signs.** The rotation (−pitch, 90, 0): up is pitch 90, down −90, back 180. If a direction comes out
  mirrored, swap the sign in `sn_pitch` (`tools/edge_snake_articles_msc.py`).
- **Joint 1003.** That the override takes his table-1 IDs (test 79's 1005+ were taken: 15 of them overran the list).
- **A model on a dein copy.** That flag 0x40 alone loads and draws it (both its readers are generic code).
- **The trail on a weapon.** That the sword trail (`Sword_Glow`) draws from a weapon's script.
