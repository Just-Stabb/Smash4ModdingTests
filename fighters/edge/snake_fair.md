# Sephiroth: held forward air (the extending sword)

**Status: test 107** (held up tilt since test 98; forward air's end hit removed in test 103). Test 79 posed 15 joints of his own model from MSC and crashed the game as he loaded (the
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
  - With no direction held, it keeps going the way it was (the first run is forward; user, test 92).
- **Release:** letting go of attack sends the sword back along its path to where it started. After 5 seconds out
  (300 frames from the hold, his `VAR_22`) it goes back by itself, held or not (test 99, both moves).
- **Catching:** whoever the tip hits stays stuck where they were hit, relative to the sword. They ride back
  along the path with it, then take a second hit.
- **Trail:** the sword trail follows the moving tip.

The user's numbers:
- 3 units a frame, 300 at most.
- From the hold until the end hit is over (frame 19), no gravity and a steady fall of 0.1 a frame (`edge_sn_fall`, test 100: the user's "not accelerate downwards over time", "extremely low" fall speed; tests 93–99: gravity x 0.4, then x 0.1), no fast fall.
- Normal landing lag; landing drops anyone caught.
- Only the tip catches.
- **Side special cancel** (test 107): if the move hit anyone (his own hits or the point's catch: VAR_19), side special
  cancels it (`edge_sn_cancel`, first in both loops) once the sword is back at the hilt (state 5: set in the loop
  after the check, so the frame after it gets there). Test 128 opened it from the return (state 4); test 129 put it
  back (the user: "The side B cancel should wait until the frame it hits the hilt") and made side special's startup
  faster instead (`specials.md` "Side special").
- **Grab cancel** (test 128, the user: "allow snakesword's hilt return to be cancelled into grab if on the ground"): on
  the ground, the grab input (no item held) goes into a standing grab (0x35 Catch; tests 128 / 129 used 0x37, the dash
  grab: test 130) on side special's terms (test 129, the user:
  "The same rules that apply to side special's cancel should apply to grab"): the sword back at the hilt and the move
  hit (test 128: from the return, hit or not).
- The catch does 5%. Only up tilt has an end hit (test 103, the user's): 11%, angle 42, knockback growth 40, each hitbox 6 bigger than up tilt's, frames 21–24 (test 105; the caught are taken out of their hold hitstop as they're let go). Forward air's caught fighters drop once at the hilt (tests 79–102: an 11% end hit at fair's angle).

## Held up tilt (test 98)

User, test 97: "please make held Up tilt work the same way that held forward air does", "for up tilt, make the
default direction up". Everything above applies, with up tilt's own numbers (`edge_sn_move` 1):
- **Hooks:** up tilt's status (0x29) main `func_278` (`edge_sn_init_hi3`: the hold check starts if attack is held),
  its loop `func_279` (`edge_sn_loop`, first), and its end slot (was the empty `func_323`; `edge_sn_end`).
- **Frames** (Ultimate's `c02attackhi3`, the port's ACMD): the pull hit at 17, the clean hit 20–22, the late hit
  23–32. The hold window opens at 23 (after the clean hit) and the hold is confirmed at 29 (6 frames, as fair's).
  The motion goes back to frame 20, where the sword points straight up (swordl1's +X = (0, 1, 0) from frame 20 on),
  and freezes there.
- **The path** starts at the blade's start in that pose: the hilt 1.14 forward, 26.36 up, the blade 0.82 above it, so
  (1.14, 27.18). The first run goes up, and with nothing held it keeps the way it goes. Down (against the first run)
  needs the tip 16 forward or back of the sword's start (`edge_sn_down_side`; test 99, the user's; test 98 had
  fair's rule, 24 past the reach upward).
- **The articles** tell which move it is from his status (hit / status variable q 2 of his slot: 0x29 is up tilt) and
  take up tilt's base then (`HI3_H` / `HI3_V`, `tools/edge_snake_articles_msc.py`).
- **No gravity change** (he is on the ground): `edge_sn_gravity` does nothing for up tilt. Fast fall doesn't apply.
- **ACMD** (`snake_hi3_scripts`): frames 17, 20 (hits and head intangibility) and 23 (late hits, intangibility off)
  and the frame 16 / 20 effects only at `VAR_23` 0. The end hit at a new frame 21 once the sword is back (`VAR_23` 2):
  `Hit_Log_Clear(-1)`, then frame 20's four hitboxes up the sword at 11%, up tilt's angles (90 / 91), KBG 40, each 2
  bigger; removed at 23.

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
- **snaketip** (the point): the blade's point on BaseN, its real length (3.48) along +Z, drawn once (its crossed copy
  drew a dark X across the curved tip; the turn is a pitch about the depth axis, so the blade's face stays to the camera).
- Both are drawn twice, the second copy turned 90 degrees about the blade, so they look the same width turned any
  way. Their material is the sword's own; its two textures are copied into the article's `model.nut` under ids
  his article blocks (`tools/fighter_texture_ids.py`: snake 0x40C24800 + k, snaketip 0x40C25000 + k; 0x40EBF000 + k
  before fighters_texid_fix_v1). `model.sb / .nhb / .mta / .xmb` are the light arrow's.

**His MSC.** The block hooks into three places:
- **Aerial status main (`func_315`), `edge_sn_init`:** starts the hold check if this is fair with attack held.
- **Aerial status loop (`func_319`), `edge_sn_loop`:**
  - The hold check (attack held from the start through frame 21: the tapped move's hits come out first), then the
    motion back to frame 13, held there: the blade hidden, the path published, the 12 runs and the point generated
    (ArticleModule 0x2710, articles 9 and 10).
  - Steering, then retracting.
  - Catching (a fighter in hitstun whose feet are within 22 of the tip) and holding the caught fighters. A caught
    fighter is put on the sword, its middle (7 above its feet) at the point's middle, not left where the point found
    it (test 95: off the sword, the end hit missed it on the way back).
  - Publishing the path every frame.
  - No gravity and the fall speed set to 0.1 every frame (`edge_sn_float`: the gravity energy's accel 0, its speed through `KineticModule(0x11, 1, -0.1)` as `func_81` sets it), kept after the sword is back, through the end hit, to motion frame 19 (`edge_sn_grav_end`).
  - No fast fall from the hold to the move's end (`edge_sn_free()` 0): its start (`func_553`, through `func_550` in
    the aerial's `func_316`, and `func_555` in `func_319`) is skipped, its flag `0x21000001` kept off, and one begun
    before the hold undone (fall speed back to the max fall speed, as `func_81` does). Tests 93–96 cleared
    `0x21000007` and skipped only `func_555`, which left fast fall working (test 97).
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
  facing), turns along the run (0x2717, (−pitch, 0, 0): its facing, his, already turns it his way, lr × 90 about Y;
  tests 84–88's Pit's-arrow 90 on top made 180, a forward run seen end-on) and stretches EndN to the run's drawn part
  (0 when that run isn't drawn).
- Both take his facing (`PostureModule(0, lr)`): a fighter the point hits takes it (none: facing the camera, test 83).
- Both are placed before their motion starts, so the point's trail begins where the point is.
- **The point** sits at the path's drawn end, turned along the last drawn run.
- Both remove themselves when VAR_30 goes below 0, when he's gone, or after 900 frames (a safety net).
- **The point's flash:** while the sword grows, fair's tip flash (`edge_sword_flash2`) every 6 frames at the point's
  end, the newest moved with it (`EffectModule` 0x3 / 0x17).

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
5. **Retracting, once attack is let go.** The path shortens from the tip end by 6 a frame. A caught fighter stays
   where it was caught until the shortening end gets back to it, then goes back with the end along the path,
   on to the hilt: once the sword is back at its own length, the retract goes on pulling the caught fighters in at
   the same speed until all are at the hilt, then the end hit comes (test 102; tests 79–101 left them 60% of the way
   out the blade, where the end hit missed). (Tests 79–93 moved them back by the retracted length at once, sliding
   along sword still out past them.)
   - **No blast-zone KO while caught** (test 102): a caught fighter's place is kept 15 inside the side and bottom
     blast zones and 30 under the top one (`StageData` 0–3, the bounds the Dead status clamps its KO place to). While it's dragged back it has no stage collision (hit / status
   variable q 6, `GroundModule(0x2710, 0)` on it every frame; 5, air, when it's let go): it goes through the stage and
   floors with the sword (test 96).
6. **Back to normal length.** The motion runs again and `VAR_23` becomes 2: the end hit on frames 14–18, then the
   rest of fair as normal. His slow fall stays until frame 19, then his own gravity takes over.
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

- **Test 148, shields** (the user: "Make the tip of snakesword not disappear when being shielded, if it is shielded,
  make it unable to hit the same character as it hit previously until the snakesword is being pulled back to where it
  came from"): the point's hit method takes the shield result too (`extra_kinds.json` snaketip `"on_hit_bits": "0x17"`;
  Din's Fire's method removed it), so a shield leaves it in its status. A hit on a shield is in its hit record, so the
  shielding fighter isn't hit again; as the sword starts back (VAR_30 shorter than last frame) a point that was shielded
  (`AttackModule(0x2726, 0x4)`) plays its motion 1, `snaketipclear` (frame 0: `Hit_Log_Clear(-1)`, the catch and the
  trail again: a dein copy has no animation, its scripts only run frame 0), so from then on it can hit them
  (`sn_shield_check`, `tools/edge_snake_articles_msc.py`). Unconfirmed in game: that the shield hit is recorded, and
  the trail across the motion change.
- **Test 119:** "attack held" is SELF_ATTACK or attack's raw input bit (MSC button 14, `ControlModule(0x2712, 0xe)`):
  with the A+B smash setting on, B pressed during the hold made the game clear attack's bit (smash latch), ending it.

