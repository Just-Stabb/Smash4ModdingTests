# Sephiroth's specials (plan and progress)

User (after test 56): "Can you do Sephiroth's specials? (Please keep Zelda's articles and make new
ones)". Built on his Zelda slot (kind 0x42): Zelda's native code, status table and article list stay;
his moves are new MSC in her special statuses, Ultimate's animations in her special motion slots,
and four new article kinds after hers.

## Sources

- Ultimate scripts: `lua2cpp_edge/edge/Special*.txt` (body), `edge_fire/` (Flare: `SpecialN1-3`,
  `BurstS/M/L`), `edge_flare1/` (`Fly`, `Hit`, `End`), `edge_flare2/` (`Fly`, `Try`, `Exp`, `End`),
  `edge_flash/` (`Attack`).
- Ultimate's status code (`lua2cpp_edge.nro`): the user's `lua2cpp_decomp.zip` (ssbu-recomp output for every
  fighter, `gen_nro_eh_o2/lua2cpp_<name>/`; Drive), read with `tools/recomp_annotate.py` (imports named, the
  lua const table's reads as CONST[offset], hash40s named; `--status`: the status table) and
  `tools/recomp_hashes.py` (which function reads which param). The const table's values are filled at run
  time (not in the dump): constants are named by matching the compiled ACMD functions to the smashline
  sources. (Before: the moves' logic rebuilt from the scripts, the params and the videos.)
- Ultimate params: `param/vl.prc` read with `tools/prc.py` (labels: ultimate-research/param-labels
  `ParamLabels.csv`): `param_special_n / s / hi / lw`, `param_fire`, `param_flare1 / flare2`,
  `param_flaredummy`, `param_flash`, `special_lw_shield_data`, `map_collision_*`.
- Animations: his `motion/body/c00` (26 special `.nuanmb`). His articles have no models or
  animations (only `motion_list.bin`): effects only, like Zelda's `dein`.

## Zelda's side (vanilla `zelda.mscsb`, decompiled)

Her own statuses 0x152-0x15C (status table `sv_set_mem(0x1, slot, status, func)`), motions set by
`func_22(motion, frame, rate)` / `func_23(motion)`:

| status | Zelda | motions (ground / air) |
|---|---|---|
| 0x152 | Nayru's Love | 0x211 SpecialN / 0x215 SpecialAirN |
| 0x153 -> 0x157 -> 0x158 | Din's Fire start / loop / end (article 0) | 0x219 / 0x21D / 0x221, air 0x225 / 0x229 / 0x22D |
| 0x154 -> 0x159 -> 0x15A | Farore's Wind start / warp / end | 0x231 / -, 0x235; air 0x239 / 0x23D |
| 0x155, 0x15B, 0x15C | Phantom Slash (article 2) | 0x241-0x258 |
| 0x156 | Final Smash (articles 3 / 4) | 0x259 / 0x25A |

Every special motion has three custom-move variants (`_c2`, `_c3`, `_c4`: 0x212-0x214 ...) that
Sephiroth (no custom moves) can use for his extra animations: the kind record's `motions` map names
their animations (kind_expand's motion table copy, as jab 2 / 3).

Her articles: 0 `dein` (8 motion slots, no model), 1 `dein_s`, 2 `phantom`; kept. Since test 111 article 2 is his
own copy of the Phantom's kind, 0x19B (`extra_kinds.json` `"phantom": "0x19B"`): a weapon's files load by its kind's
owner, so with her kind his `script/msc/phantom/` (tests 106–110's tracking) was never read, only hers.

## Plan

- Articles (`tools/extra_kinds.json` `weapons`, all based on `dein`): `fire` 0x18C, `flare1` 0x18D,
  `flare2` 0x18E, `flash` 0x18F, article ids 5-8 (after Zelda's five normal entries: `weapon_expand.py`
  `article_layout`). Their files under `fighter/edge/` (`script/msc/<name>/`,
  `script/animcmd/weapon/<name>/`).
- Neutral (status 0x152): charge `SpecialNStart` (charge kind S at 20, M at 32, L at 100; Gigaflare
  fired at 120 by the start motion itself), release -> `SpecialN1` (Flare) / `SpecialN2`
  (Megaflare), shield -> `SpecialNCancel`. Motions 0x211 N1, 0x212 NStart, 0x213 N2, 0x214 NCancel
  (air 0x215-0x218). `fire`: fly (level S / M / L: `param_fire` speed, acceleration, life), then
  burst S / M / L.
- Side (0x153 start, 0x158 hold / fire): Shadow Flare, `flare1` (the orb) / `flare2`.
- Up (0x154 start, 0x159 Blade Dash / Octaslash, 0x15A ends): no article ("Up special" below).
- Down (0x155 stance, 0x15B hit, 0x15C end): Scintilla, `flash`.
- Final Smash (0x156): Zelda's for now.

## Executable

Re-applying `kind_expand.py` / `weapon_expand.py` outputs over the newest executable (Sephiroth test
42's) gives it back byte for byte; their new outputs go over it the same way.

## Build

```
python3 tools/edge_specials_build.py DUMP/lua2cpp_edge EDGE ZELDA ZELDA_UM fighter_param_vl_zelda.bin OUT/c00 PKG \
    --rpx TEST42/cross_f.rpx --bank FXDIR --motions MOTIONDIR
```
(`tools/edge_specials_build.py`: his body scripts with `specials_acmd.json`, `edge.mscsb`, the fire
article's and the flash article's MSC and scripts, Zelda's `dein` files as the not-yet-made articles'
placeholders (flare1 / flare2), the
executable.) The pieces it takes ready-made:
- FXDIR: the effect bank, `tools/vfxb_to_ptcl.py` over his `ef_edge.eff` with every `edge_*` name of
  `edge_effects.json` and the turned variants (`effect_variants.py scan` of the body effect.bin:
  the Flare's hand effects at (90, 0, 90) are 7 more); its ids.json goes back to `edge_effects.json`
  (the variants are numbered after the plain effects, so adding effects renumbers them: the build
  re-runs the effect translation with the new ids).
- MOTIONDIR: `ultimate_fighter.py motions ... --add C00Attack12,C00Attack13,D00SpecialNStart,
  D00SpecialN2,D00SpecialNCancel,D00SpecialAirNStart,D00SpecialAirN2,D00SpecialAirNCancel,
  D02SpecialHi1End,D02SpecialHi2,D02SpecialHi2End,D02SpecialAirHi1End,D02SpecialAirHi2End` (the 301
  motions of test 22 byte for byte, plus these 11).

Translator additions for the specials (`tools/ultimate_acmd.py`): `for _ in a..b { }` loops unrolled
(the charge's dust puffs; the loop swallowed the frames after it), `AttackModule::set_size` ->
`Change_Hitbox_Size` (Flare's growing hitbox), and a `--translate` slot with no script in the dump
(SpecialNCancel) gets empty scripts so the slot's custom-move variant of Zelda's doesn't run.

## Neutral special (test 57)

- `edge.c` (`edge_n_*`, status 0x152's main; its end / other slots empty): SpecialNStart from frame 0;
  charge level M at 32, L at 100. From frame 20 to 99: shield -> SpecialNCancel; special released
  (at any time before) -> SpecialN1 (level S) or SpecialN2 (M), which fire at their frame 13. Not
  released by 120: Gigaflare fired by SpecialNStart itself. Air: the same motions + 4, the fall
  slowed (gravity 0.0756, max 1.012: Ultimate's accel_y_mul 0.7 / max_speed_y_mul 0.55 of his)
  until frame 140 (charge) / 33 (Megaflare); landing / leaving the ground swaps the motion keeping
  its frame. Ends in wait / fall.
- The fire article (`weapons/fire.c`): level from the generate (his custom slot 0x10000048 ->
  its 0x10000005): S / M / L fly at 0.01 growing by 0.07 / 2.1 / 0.022 a frame to 1.5 / 2.1 / 1.0
  for 74 / 28 / 47 frames (`param_fire`), then burst (BurstS / M / L) for 10 / 24 / 50 frames; a
  wall or floor bursts it early, a hit too (`"on_hit": 1`). Its scripts are Ultimate's edge_fire
  ones; the bursts' effects outlive it (Terminate 0).

## Up special

Blade Dash / Octaslash, `edge.c` `edge_hi_*`, from Ultimate's status code (`lua2cpp_edge.nro`, read function
by function: the spec `edgenro/spec_up_special.md`; addresses below are `f_7203e<addr>`), `vl.prc`
`param_special_hi[0]` (written into the code: his vl file is Zelda's layout) and the ExeFS's rush hook.

- **Statuses:** Zelda's table ends at 0x15C (`global7` 0x15D), so Ultimate's five statuses go in her three
  up-special ones: 0x154 start (SPECIAL_HI: pre `09690`, main `09a70`, loops `17e40` / `19910`, exec `03650`,
  end `09dd0`), 0x159 the rush, Blade Dash and Octaslash in one (`0a500` / `175b0`, `0acc0` / `15c90`, exec
  `038b0` / `03930`, end `0a6c0` / `0ae80`; the charge flag picks the `charged_` params as Ultimate's do), 0x15A
  the ground end and the air end in one (`0b360` / `15510`, `0be60` / `14b30`, ends `0ba00` / `0c700`).
  Table slots: 0 pre, 1 main, 2 end, 3 init (none: set up in the mains; Zelda's 0x15A one took out), 4 exec,
  5 exec in hitlag (the pitch), 6 empty. Ultimate's status work kept across them (KEEP_ALL) is in globals.
  LandingFallSpecial 0x19's init is `edge_hi_landing_init` (Ultimate's hook `03d40`).
- **Motions** (MotionModule straight: func_22 adds Zelda's custom offset): 0x231 / 0x239 SpecialHiStart /
  SpecialAirHiStart, 0x235 SpecialHi1 in both situations (Ultimate has no air one; 0x23D's script is empty),
  0x237 SpecialHi2, 0x236 / 0x238 SpecialHi1End / SpecialHi2End, 0x23E / 0x23F SpecialAirHi1End /
  SpecialAirHi2End, 0x232 SpecialHi2Landing (`extra_kinds.json`: Ultimate's special_hi2_landing plays
  landing_fall_special's animation, so the slot names `FitZeldaBodyMainA04LandingFallSpecial`).
- **Scripts:** `specials_acmd.json` (all nine of Ultimate's). Their DECIDED_RUSH (start, frame 18) and
  ENABLE_CONTROL (air ends, frame 18) flags aren't translated: the MSC reads the motion frame. Their cliff
  check NONE isn't either: the MSC sets the ledge modes (below). Not in his effect bank yet (left out of the
  effect scripts): `edge_octaslash_sword_flare`, `_arc`, `_arc2`, `_charge`, `_speed_line`, and the aim's
  `edge_octaslash_direction`.
- **Start:** ground x speed x 0.4, brake 0.1, stopping at edges; air x x 0.4 (brake 0.02), y x 0.4, gravity
  0.06, fall capped at 0.1 of his, no drift (the common start setting); landing / leaving the ground swaps
  the motion keeping the frame and sets that again. Octaslash = special held without a release until frame
  18 (exec `03650`). Aim: the raw stick, |x| + |y| < 0.5 = straight up, analog (normalised). Decided at frame
  18 (Octaslash 30): faces the stick if |x| > 0.125; on the ground an aim at least K from the floor normal
  goes along the floor (`f_16f20`). Pitch target -sign(y) x angle(facing, dir), blended in over frames 18-23
  (30-35). Rush at frame 23 (Octaslash: the start motion's end, 35).
- **Rush:** the direction resolved again (`f_157d0`: ground -> situation ground, correct ground; air ->
  air), 13.5 a frame (6.2) on energy 3, no gravity or drift (kinetic 0xD, as Fox's Fire Fox). Each frame out of
  hitlag (ExeFS `0x9e5100`): on the ground along the floor's tangent keeping its size; from rush count 2 (6)
  braked by 1.72 (0.47) along the path. Ends at count 7 (15): ground -> ground end, air -> air end. Landing
  mid-rush within 25 degrees of straight down: x x 0.25, LandingFallSpecial; otherwise Blade Dash -> ground
  end ("landed": x x 0.25), Octaslash keeps sliding. From rush frame 1, `GroundModule(0x2713, 0)` =
  set_passable_check(false). The pitch follows the speed. No intangibility (Ultimate has none).
- **Rush fixes (test 101, the user: tap up special "doesn't go far enough when going upwards"; Octaslash "bounces"
  off diagonal stage geometry):** the stop energy's speed limit is lifted (`KineticModule(0x14, 3, -1, -1)`): Smash 4
  caps its y in the air unless a script lifts it, as Zelda's Farore's Wind does (`func_2291`: x limit kept, y -1).
  In the air the rush is kept on its own line each frame, and where it touches a ceiling or a wall
  (`GroundModule(0x2722, 1 / 2 / 4)`) the surface's normal is taken out of its direction, so it slides along slanted
  stage sides (Ultimate's hook only re-aims on the ground; this is the port's). Test 105 (the user's clip: it went
  on up and away along a stage's slanted underside past the corner): the slide is for the frames it touches only,
  the aim kept, so off the surface it goes on the way it was aimed.
- **Rush speed (test 106, the user: tap up special "still barely gives height" after test 101):** the speed each
  frame comes from Ultimate's schedule (13.5 / 6.2, less 1.72 / 0.47 a frame from count 2 / 6: `edge_hi_rush_m`), not
  read back; on the ground it's on the stop energy along the floor as before, in the air x on the stop energy and y
  on the gravity energy (gravity 0, fall cap 20: `edge_hi_rush_set`), whose speed Smash 4 is seen to move him by
  (held forward air's fall, Scintilla's break). The rush's y read anywhere is both energies' (`edge_hi_vy`).
- **The user's up special concept (test 113, stage 1 of 3):** "Tap up and hold up special both leave a purple line
  trail ... When multiple lines form a closed shape inside, a purple glow ... appears" (stages 2 / 3: the trail as
  articles, then the closed shapes' fill and hitbox, later tests); this test is the rest:
  - **Octaslash held:** while the special button stays held the rush turns toward the stick, 8 degrees a frame the
    shorter way round, the full 360 degrees (test 114, the user: "allow a full 360 degrees of movement"; test 113
    kept it to his front; he keeps his facing, so going back his pitch passes 90: a loop; neutral keeps the way),
    at 6.2 braking as normal down to 2.4 (test 126; 2.2 in test 116, 2.0 in 115) and kept there while held (`edge_hi_rush_m`, `edge_hi_cruise`; test 115, the
    user: "moves far too fast" at test 113's steady 6.2); on the ground, turned more than ~20 degrees up, he leaves
    it (`edge_hi_steer`). Past the rush's count 15, still held and with loop time left, SpecialHi2 is played again
    from frame 4 (`MotionModule(0x1, 0x237, 4, 1)`) the frame after it has been on frame 14, its last (Ultimate's
    d02specialhi2.nuanmb final frame 14; VAR_14 the one-frame wait, so frame 14's hit is out first): frames 4 - 14 are
    the 2nd hit to the 7th (the one before SpecialHi2End's), so the loop is those. Test 113 / 114 waited for frame 16,
    past the motion's end: it never looped and held the last pose (the user's clip). VAR_20 tells the script which pass it is (0 plain, 1
    the first held, 2 looped): SpecialHi2's 1st hit (frame 2) and start effects (frame 0) are skipped on a looped
    pass, its end flash (frame 15) plays on a plain pass only, and held (VAR_20 1 / 2) its multi-hits (frames 4 - 14)
    are 0.14% each (test 127, the user: "reduce held Octaslash's multihit damage to 0.14% per hit"; 0.5% in test 126)
    with no hitlag (test 126: "have no hitstop"; let go, Ultimate's 2.3%) (`edge_specials_build.py
    octaslash_loop_scripts`). VAR_20 3: a shape was made (below): the rush goes straight to the end, whose finisher
    is angle 366 (pulled toward the hitbox: "force Sephiroth to end Octaslash with the finisher hit angle that sends
    towards him, inside the shape"; SpecialHi2End / SpecialAirHi2End `_when` 3).
    **Blast zones (test 127, "make opponents hit by it unable to be KO'd by the blast zone during the duration of the
    entire attack, including the ending hit"):** a fighter in hitstun while he's charged in the rush (0x159) or its
    end (0x15A) is marked (his TIMER_0 - 7, one a player slot) and stays marked while its hitstun lasts and 40 frames
    after (the launch's speed left); marked, it's kept 20 inside the side / bottom blast zones and 30 under the top
    (StageData 0 - 3) by moving it there (`0x0F000020 + 4 x slot`, set slot X / Y; `edge_hi_keep_in` from func_82).
    Test 127 kept them in only while he was in 0x159 / 0x15A (the user: it "still allows for KOing in the blast
    zone": the finisher's launch carries them on after the end status) and 15 from the sides. Approximated: a marked
    fighter hit by someone else within those frames is kept in too.
    **On the ground (test 127, the user: "if Octaslash is held on the ground, or while going towards the ground,
    Sephiroth loses control and can only move forward until leaving the edge"):** held, the ground rush moves along the
    floor by the aim's part along it (back too), still if aimed straight into it, and keeps the aim, so steering up
    lifts him off (`edge_hi_rush_speed`); the landing rule (within 25 degrees of straight down) is for the tap only.
    Loop time 100 frames (test 126; 60 before: `edge_hi_loop_frames`; VAR_12), started again by every hit (SELF_HIT_NOW), and 180 frames
    of loop at most, hitlag included (VAR_15, `edge_hi_loop_max`; test 116, the user: it "loops indefinitely when an
    opponent is hit"); held = ControlModule's held special and SELF_SPECIAL both; let go or out
    of time -> the end (SpecialHi2End's final hit) and SpecialFall as before. Approximated: the restart assumes the
    script runs past frames 0 - 3 at once on a motion change with a start frame.
  - **The trail (tests 123 - 126, stage 2):** from the rush's start to the air end's first falling frame (the rush's
    y speed, `edge_hi_vy`, at 0 or below) or the ground end, his middle's path (feet + 9) is taken as points 4 apart
    (one a frame at most, `edge_tr_step`; what's left from 1 long when it ends: test 127 writes the end a frame after
    that last point, so the landing's piece is taken, "Blade Dash's lines should follow where Sephiroth landed"),
    numbered block x 1024 + n (Blade Dash blocks 1 - 14 in turn, held Octaslash's 15: `edge_tr_block`, his MSC's last
    global, 0x86). **Blade Dash's (test 128):** on while he still moves the slash's way (the user: "Blade Dash lines
    should only stop being made once Sephiroth stops moving in the direction the slash is in in the animation", "This
    line should reach all the way to Sephiroth's back"): through the rush, either end (the ground end's slide too)
    and into Fall (20 frames at most, his per-frame hook; any other status ends it: the snake sword shares these
    variables), ending once his move along the slash (rush direction x facing; his position last frame in VAR_11,
    0.25 units) is under 0.4 a frame, not in hitlag or a shape's steps (`edge_tr_bd_stop`, `edge_tr_running`, TIMER_8).
    Once he's been in the air in a trail, its points on the ground are at his feet + 1, not his middle (TIMER_9,
    `edge_tr_h`): a line he lands on reaches the floor (test 128: "Lines still don't cover all the way to the ground on
    landing"). The end is -1 (Blade Dash: it stays) or -2 (held Octaslash: its articles go once their fill is
    over; test 127, "only make Blade Dash lines persist after use, not held Octaslash's lines"); a new Blade Dash
    trail puts out the ones 6 or more blocks before it ("delete the oldest line if a new line has been made after the
    6th line"). `trail` articles (weapon kind 0x19C, a
    copy of Zelda's dein as the snake runs: `tools/extra_kinds.json`, his article 11, 24 at most since test 128: the
    kept Blade Dash lines held all 12, so held Octaslash's line and its shape's glow sometimes weren't made; 60 of 64
    instances in all) draw it: each a
    stretch of 16 points (15 pieces) from the one before's last point (`weapons/trail.c`, generated by
    `tools/edge_trail_msc.py`), still at its first point, moving its model's joints every frame relative to it
    (`ModelModule(0x7, 0x7D0 + bone, 0, dy, dx x lr)`, lr its facing as made: test 127 fixes a line drawn the wrong way
    when the move was turned after its start; setting the facing to +1 didn't turn its model); removed after
    360 frames ("persists for 6 seconds"), or once its pieces are all gone and its fill is over. Model
    (`tools/edge_snake_articles.py build_trail`, 49 bones): the line, piece k two ribbons 1.2 wide in the screen plane
    (width along world up and along world X) between its own joints A_k / B_k, so a piece can go alone (both on its
    start); the fill, wedges from a middle joint C to joints W_k / W_k+1 at the pieces' points. The light arrow's glow
    material (additive, blend 1 / 1) with purple textures made by the build (the line: a whiter middle; the fill:
    radial, bright at the line). Scripts empty (the snake articles' one motion, `Move`). Test 123 made an article per
    8-long piece, 40 at most: the game crashed loading him (64 article instances a fighter, docs/native-notes.md
    "Article instance cap"; `port_check` W8).
  - **Closed shapes (tests 125 / 126, stage 3: "think about this ... similarly to how art programs do fill buckets";
    test 126: "The lines should go away when forming a shape, and the old lines from the last uses of up special should
    be usable to create shapes. Also please make other shapes possible that aren't circles", "I'd like for the formed
    shape to mirror the lines that the closed shape was made of"):** his shared 4 - 6 (VAR_28 - VAR_30, free in up
    special: Shadow Flare's orbs read 0 - 3, the Phantom 7, the snake runs 0 - 6 only while the sword's out) carry 5 the
    newest point (packed (x + 512) x 2 x 2048 + (y + 512) x 2, half units), 6 its number (-1 once the trail's over), 4
    a crossing. Every trail article, its trail over or not, tests the newest piece against its own pieces still drawn
    (not the ones next to it in its own trail); one crossed, piece m, is reported as -m. A shape is the trail crossing
    an earlier piece of itself (a loop: its points m + 1 .. newest - 1; after a shape only a loop closing on a piece
    from its end counts, so each lap is its own), or crossing an old trail a second time (its points since the first
    crossing and the old trail's between the two pieces crossed: VAR_6 / VAR_7 keep the first), with 10 frames between
    shapes. Then, a step a frame from his per-frame hook (`edge_tr_tick`: they finish after the trail's over; the step
    in VAR_0 as -1 - -5, never a snake run's code), the trail paused: the shape's points marked (shared 6 = start x 512
    + count + 0.5, one or two ranges), their sums in 5 / 4 (x, y; x^2, y^2; x y: each point once), and the commit (5 the
    middle): every line goes (test 128, the user: "When a shape is formed, all lines aren't cleared for both Blade Dash
    and Octaslash": all of them, the trail being laid too, which goes on from its next point; tests 126 / 127 dropped
    the shape's pieces only) and the articles fill the shape with wedges from its middle to the pieces'
    points x 1.2 (so its outline is the lines that made it, 1.2 x: test 127, "The effect and hitbox should be at least
    1.2x the size of the shape"), grown in from frame 12 to 20, held to 40, shrunk away by 50. A
    `fill` article (kind 0x19D, article 12, 3 at most, 8 motions; `weapons/fill.c` from `tools/edge_fill_msc.py`) at
    the middle takes the ellipse fitted to the points (the long axis' angle and half axes 1.2 x sqrt(2 l1), sqrt(2 l2)
    from their spread, or 1.2 x the points' half extents along / across that axis if larger: test 127's EXTENT steps 7
    / 8, so a triangle's corners count; the middle is the extents' middle; packed in 4) and is the shape's hitbox:
    turned along the long axis (mirrored with his facing), its joints J0 - J4 from -(a - b) to a - b, a sphere on each
    from its frame 4 to 50, when the glow's gone (test 127, the user: "make the hitbox ... happen on frame 4, and linger
    until the effect fades"; tests 125 / 126: frames 20 - 23; one hit log: a fighter is hit once), size by b (up to 5 / 8
    / 12 / 17 / more: 6, 9.5, 14, 19.5, 26), damage / BKB / KBG by sqrt(a b) (up to 8 / 13 / 19 / 26 / more: 6 / 9 /
    12 / 15 / 18%, 40 - 60, 60 - 100), angle 80, from its VAR_0 / VAR_1 in its script. His VAR_0 - VAR_11 (the snake
    runs', free in up special) keep the steps.
    **Three or four lines (test 127, "make shapes enclosed by 3 or more lines work"):** a crossing of another trail's
    piece is kept by the crossed article as a junction (its piece, the crossing trail's number then; 4 at most). When
    the trail crosses old trail Y after old trail X, he asks the articles (JQ X Y: shared 6 = -(3000 + X x 16 + Y) -
    0.5) for a junction X - Y (a triangle), or X - Z then Z - Y for the last 6 Blade Dash trails Z (a four-sided
    shape), a step a frame (VAR_0 -11 / -12 / -13; `edge_tr_find*`); found, the path's ranges (this trail since X, X
    between, Z between, Y between) are marked and the shape is made as above; not, Y is kept as the first crossing.
    The crossing test counts a point on the other line on one side, so lines meeting at a shared point cross once
    (test 126's strict test missed them: the simulation's triangle met exactly at a corner).
    **Octaslash's shape** ends the move (VAR_20 3, above).
    **Not near the blast zones (test 128, the user: "make shapes not able to be formed off-screen near the bounds of
    the blast zone"):** a shape whose middle +- its long half axis comes within 50 of the side / bottom blast zones or
    60 of the top isn't made: CANCEL (shared 6 -1005.5) drops the articles' marks; no fill, no hitbox, the lines stay.
    Modelled in `tools/edge_trail_sim.py` (a held Octaslash circle: a shape a lap; a U closed by the next up special's
    line: middle (0, 32.5), half axes 36 / 19.1; a tilted ellipse a 40 b 15: 47.5 / 19.8 at 28.1 degrees; a triangle of
    three Blade Dashes (0, 50) (-26.7, 70) (26.7, 70): middle (0, 60), 30 / 12; a 60 x 40 rectangle of four: middle
    (0, 40), 39 / 29.2; a Blade Dash's landing point taken), both update orders. Approximated: the hitbox is a chain
    of 5 spheres along the ellipse; a shape of five or more different trails isn't found.
  - **Autolink:** each frame of Octaslash's rush, the last fighter hit (still in hitstun, within 30) is pulled 60%
    of the way to 10 along his rush direction, 3 higher (LASTHIT_OFFSET_X / _Y; `edge_hi_link`), so the multi-hits
    carry them along.
  - **Blade Dash (tap):** its aim stays the full circle; landing lag 22
    (Ultimate 27); the air end ends in a normal Fall (Octaslash: SpecialFall as before), at frame 15 (test 120, the user: 8
    frames earlier than test 116's 23, which was "right before the point where Sephiroth would begin falling in the
    animation": d02specialairhi1end's legs and Rot start into the fall at 24 of 48), its pitch back to 0 over 11 - 15.
  - **Once per air time:** up special (either) sets VAR_21 as its attack starts (the rush's main; test 116, the
    user: "only used after the attacking portion of either up special begins"; test 113: its start); in the air it can't start again until he
    is on the ground outside up special or grabs a ledge (statuses 0x72 - 0x74): `edge_hi_can` on the two air
    input checks, `edge_hi_air_tick` from func_82. Being hit doesn't give it back; dying / respawning does (test 127,
    the user: "make up special's air count reset on respawn": statuses 0xB1 Dead / 0xB2 Rebirth, and the Rebirth
    status' own start, func_228).
- **Ground end:** x x 0.6 (Octaslash 0.9; 0.25 if landed), brake 0.12 (0.06); actionable at the motion's
  cancel frame 27 (56); off an edge -> Fall; end -> Wait.
- **Air end:** x x 0.4 (0.9), brake 0.02, the rush's y x the same into gravity, gravity 0.12; from frame 18
  drift with max speed x 0.5; pitch back to 0 over frames 11-44 (18-53); landing -> LandingFallSpecial, end
  -> SpecialFall (Blade Dash: Fall since test 113).
- **Landing lag** (`f_147f0`): 27 (Octaslash 56; Blade Dash 22 since test 113) in the landing frame float 0 when the next status is
  SpecialFall / LandingFallSpecial (Smash 4 plays LandingFallSpecial over it). Straight out of Octaslash's
  rush, LandingFallSpecial plays SpecialHi2Landing (its landing hit) over the same frames.
- **Ledge** (func_100): Blade Dash rush frames 0-5 (mode 2, both sides), none from 6; Octaslash rush none;
  air ends mode 4 (Ultimate's pre: cliff kind 1728, ON_DROP_BOTH_SIDES inferred), Octaslash's none on frames
  1-5 and mode 2 from 6.
- **Pitch** (`edge_hi_pitch`, `f_02cf0`): Ultimate's set_joint_rotate("rot", (ROT, 0, 0)) is Smash 4's
  `ModelModule(0x1, 0x2, ROT, 0, 0, 1)` (joint 2 = RotN, his "rot"; mode 1 composes with the animation as
  vanilla's 0x10E tilt; mode 2 the one to try if it turns wrong), every frame and in hitlag. It stays until
  `ModelModule(0x2, 0x2)`: every way out removes it (the start unless into the rush, the rush unless into the
  air end, the ends).
- **Approximated / not done:** K (the ground-aim limit, NRO rodata `0x265620`, not in the dump) = 90 degrees
  (vanilla Fox's Fire Fox uses 90); the start's ground correction (cliff stop) and re-applying the start's
  multipliers on a situation change (the common routine isn't in the NRO); the air end's control accel x 0.5
  (no Smash 4 op found: max speed only) and its y speed (inferred); the rush end's floor check
  (ground_check_distance 0.01 + attach_ground: the situation alone here); the landing's 0.25 slide may be
  replaced by LandingFallSpecial's own kinetics; Blade Dash's jostle off (frames 2-6) and Octaslash's
  jostle area / victim pull (`FighterSpecializer_Edge`: angle 368 -> 366); shield_speed_mul (not traced); the
  aim effect (not in the bank: its place and roll are computed, `edge_hi_direction`). Not tested in game.

## Down special

Scintilla, `edge.c` `edge_lw_*` and the `flash` article (`weapons/flash.c`), from Ultimate's status code
(`lua2cpp_edge.nro`, function by function: the spec `edgenro/spec_down_special.md`; addresses below are
`f_7203e<addr>`), its ACMD (`SpecialLw*.txt`, `edge_flash/Attack.txt`), `vl.prc` `param_special_lw` /
`param_flash` (written into the code) and the ExeFS's native counter (FighterEdge: shield hit `0x9e02f0`,
per frame `0x9e05b0`, flash spawn `0x9e11f0`). The shield itself is native here too: the counter cave
(`tools/edge_counter_cave.py`, docs/native-notes.md "Sephiroth's counter shape").

- **Zelda's Phantom** (test 100, the user's: "make down special also charge Zelda's Phantom, and force it to activate
  if the counter is hit"; hold B to charge, as hers): her article 2 is made at the stance's start (none if one is
  still out), goes to its charging status at the stance's frame 7 (the counter on) and charges a frame each frame
  B is held, its full-charge look at 49 (7 levels of 7 frames, param `0x08000000`). It is sent (the level, frames / 7
  at most 7, in status float `0x1000006`, then `ArticleModule(0x271a, 2)`: her `func_2307`) when B is let go, 60
  frames after full charge (`0x18000001`), or at once when the counter is hit (the hit's damage is read first: the
  cave writes it in the same float). Since test 103 the charge runs in his per-frame hook (`func_82` ->
  `edge_lw_ph_tick`), whatever status he's in, so B can be held past the stance (slash, landing lag, hit...): the
  stance plays out as normal (tests 100–102 held it at frame 30). The level goes in his current status's float
  `0x1000006` for the call only (its value put back). The stance interrupted before frame 7: it goes (status 4); KO'd
  while it charges: it goes. Its state in his VAR_16–VAR_18 (`edge_lw_ph_*`).
  - **Test 104:** sent when down special is pressed again (B pressed with the stick at or below -0.5, read in any
    status and in hitlag too, so also while he isn't actionable; a down special that starts a new stance sends the
    charging one and makes none), or 120 frames past full charge (was B let go / 60). Hit while it's out (charging,
    or sent and still there: damage statuses 0x45–0x4B, 0x41, 0x57), it goes; a hit the counter takes isn't one.
  - **Test 105:** while it charges, the down special inputs (`func_43`, `func_58`, `func_675`, `func_1999`) don't
    start the counter (`edge_lw_can_counter`): the press only sends it. During the counter move a press sends it
    only from near its end (`edge_lw_ph_open`: not in the stance, from frame 42 of the slash, 32 of the break); a
    counter hit still sends it at once.
  - **Test 106:** the counter stays off while it's out at all (charging, or sent and still there): his per-frame
    hook runs before the status loop's input checks, so the press had already sent it when they looked. Tracking:
    as it's sent, if the last fighter he hit is in hitstun, its place goes in his VAR_31 (`edge_lw_ph_target`); the
    Phantom's own script (`weapons/phantom.c`, Zelda's decompiled with `ph_track`) takes it at the start of its
    attack (its main and its first frame) and stands 10 behind that fighter along its own facing (kept), at its
    height, so its slash (hitboxes 14 ahead) meets it.
  - **Test 107:** a fighter held on his snake sword (held forward air / up tilt) comes first: its place (packed with
    2^22) is kept up to date in VAR_31 every frame while the Phantom is out (`edge_lw_ph_held`); the Phantom is
    placed after its own ground set-up (test 106 placed it before, which kept it down), put in the air, and follows
    that fighter's height every frame of its attack (`ph_follow_frame`; x and facing kept) until it's let go.
    Forced out 240 frames after full charge (test 107; was 120).
  - **Test 108:** the hitstun tracking (not the held-on-the-sword one) only for a fighter within 10 of him (straight
    distance, `edge_lw_ph_near`), and only horizontally: the Phantom keeps its own height.
  - **Test 109:** that range is 15, and the Phantom also moves toward the fighter's height by at most 8
    (`ph_lift`).
  - **Test 110:** the Phantom checks every frame of its attack for a fighter held on the sword and starts following
    whenever one is (it only followed if one was held when it was sent); a fighter counts as held only while the
    sword is out (`edge_sn_out`: the per-slot places start at 0, which read as held). Release: while he can't act
    (`edge_lw_free` 0: not a free status, not past a cancel frame) any special press sends it, any or no direction;
    while he can act, down special only.
- **Statuses:** Zelda's Phantom Slash ones (her phantom article, 2, made again since test 100; see above):
  0x155 the stance (SPECIAL_LW: pre `0c790`, main `0cb70`, loop `143b0`, end `0cec0`), 0x15B the slash
  (SPECIAL_LW_HIT `0xe2b4`: `0d1f0` / `0d5f0` / `13fb0`), 0x15C the break (SPECIAL_LW_END `0xe2b8`: `0d770` /
  `0db70` / `11f00`). Slots 0 pre (0x15B / 0x15C: Zelda's `func_2303` / `func_2308`, kinetic and work kept:
  Ultimate's KEEP_ALL), 1 main, 2 end (`edge_lw_end`); no init / exec. Ultimate's work kept across them is in
  globals. All three run `f_123d0` (`edge_lw_frame`) every frame.
- **Motions** (MotionModule straight): 0x241 / 0x245 SpecialLw / SpecialAirLw, 0x249 / 0x24D SpecialLwHit /
  SpecialAirLwHit, 0x251 / 0x255 SpecialLwEnd / SpecialAirLwEnd: Zelda's SpecialLw / Loop / Attack slots, whose
  animations are already Ultimate's (`ultimate_fighter.py` MOTION_STANDINS: lwloop = lwhit, lwattack = lwend);
  no new slots. Ground and air swap keeping the frame when the situation changes.
- **Scripts:** `specials_acmd.json` (the six; the Hit / End slots renamed `speciallwhit` ... in motion.mtable).
  Their game scripts hold nothing Smash 4 runs: the MSC does by the motion frame what they do (the shield on,
  the flags, SET_SPEED_EX, WHOLE_HIT, the flash, FT_MOTION_RATE); `speciallwhit` / `specialairlwhit` are emptied
  by the build (`EMPTY_GAME`: game_speciallwhit's countered / whiff branches don't survive the dump's braces).
  SpecialLwInterrupt (an effect script, no motion) is played by the MSC (below). Not translated: FLASH /
  COL_NORMAL (the stance's body flash), jostle areas, sounds, expressions.
- **Stance:** the special start's kinetics (ground x x 0.6, brake 0.1; air x x 0.6, brake 0.009, y kept,
  gravity x 0.8, fall capped at x 0.25 of his, no drift). Frame 7: the shield group on (`ShieldModule(0, 2, 0,
  1, 1)`, Ike's call: the cave's group 1 = Ultimate's special_lw_shield_data capsule r 6, (0, 2, 8.3)-(0, 20,
  8.3)) until the stance ends. A hit on it (the cave: status float 0x01000006 = its damage d, flag 0x21000010,
  0x21000011 a projectile; damage and knockback cancelled): d kept in a global at once; d > shield_max 25 ->
  0x15C, else 0x15B (Ultimate: shield HP 25 - d, broken below 0; only the first hit counts). Motion end (no
  hit) -> 0x15B, the whiff.
- **Stance end** (`0cec0`): the shield group off; into the break: `edge_senkou_shield` stopped; any other exit
  (grabbed, hit from behind): killed, and `edge_senkou_shield_break2` at top (0, 13, 12) x 0.85
  (effect_speciallwinterrupt; `EffectModule(0x2710, ..., 1)`: the bone's frame, Z forward). Their ids:
  `edge_lw_fx_*`, written in from `edge_effects.json` by the build (0 = not in the bank: left out).
- **Hit / break:** the native per-frame's hitstop on him, `StopModule(2, n)` (hit_stop_frame 20,
  hit_stop_frame_shoot 10 for a projectile) and `ShakeModule(0, 0, n, 0, 0, 0.15)` (hit_shake_mul), in the
  0x15B / 0x15C main.
- **Slash (0x15B):** countered: speed 0, intangible frames 0-11 (`HitModule(0x2710, 2 / 0)`), control X at 26,
  fall speed at 28; in the air once (not yet at 28) the fall slowed to x 0.2 (speed, accel and cap:
  shield_speed_y_mul_air). Whiff: motion rate 0.5 on frames 1-5, 1 / 1.15 on 30-50, control at 15, fall at 20.
  Both: the flash at frame 7; actionable from 52 (func_39 / func_41); end -> Wait / Fall.
- **Break (0x15C):** speed (-1.4, 0) x facing on the ground, (-0.8, +0.8) in the air at frame 0; control and
  fall at 18; actionable from 42; end -> Wait / Fall.
- **Control X / fall speed** (`f_123d0`): in the air, the stop energy off and drift seeded with the x speed,
  max x 0.6 of his (control_max_speed_x_mul_air_flag_enable); his own gravity back. The rise capped at 1.35
  (air_invoke_speed_y_limit) every airborne frame.
- **The flash** (article 8, weapon kind 0x18F, `weapons/flash.c` + `flash_scripts()`): Smash 4's ACMD has no
  hitbox lerp, so it comes in tiers, one motion slot each (dein has 8): 0 `attacknohit` (the whiff's table,
  effects x 0.65), 1-5 `attack0`-`attack4` at p = 0, .25, .5, .75, 1 (p = clamp(d / shield_damage_charge_max
  18, 0, 1), nearest quarter): frame 0 / frame 15 hitboxes id 0 -> id 1 lerped by p (damage, KBG, FKB, BKB,
  size, hitlag, SDI, shield damage; sound level L from p .5), effects x 1.2 + 0.8 p (exec `31950` scales the
  latest effect each frame: all but the first puff). The tier goes through Zelda's side special custom slot
  (int 0x10000049 set around `ArticleModule(0x2710, 8)`; Din's Fire's creation callback 0x02F97C90 copies it,
  a signed byte, into the weapon's 0x10000005). Static, removed after 17 frames (Ultimate's notify at 16:
  one frame more so the frame-15 hitbox gets a frame whatever the order).
- **Flash placement:** the callback spawns a weapon at the owner's joint 0x13 (his head) + (lr x 9, -0.8)
  (vl 0x06000002 / 3, Zelda's special_s offsets, the same in every slot); Ultimate's is at his position +
  (lr x offset_x, 10.5), offset_x 16 + 3.5 d / 25 (14.5 on a whiff). The flash sets its position
  (`PostureModule(0x2714, x, y, z)`, Luma's set_pos) by the difference, his head being at (4.1 forward, 16.27
  up) on the slash's frame 7 (the converted SpecialLwHit / SpecialAirLwHit, `omo.world`; Ultimate's nuanmb
  gives the same).
- **Approximated / not done:** the flash's tier (p to the nearest quarter) and its x (the tier's middle d: at
  most ~0.6 off); the head's place taken at frame 7 (the pose the callback reads may be frame 6's: 1 unit
  back) at scale 1; the tier's int 1-5 also picks dein's param block (custom slots past Zelda's 3: flash.c
  reads no params); hitstop / shake through MSC on the next status's first frame (Ultimate's native code, in
  the stance's last frame); the attacker's freeze (hit_stop_slow_frame 25, mag 50: not done) and
  ShieldModule::set_hit_stop_slow; the drift's accel x 0.3; Ultimate's ground correction KEEP (Zelda's 9 here);
  the break2 effect's turned variant (MSC plays the plain one). Not in his effect bank yet (left out until
  added): `edge_senkou_start`, `_shield`, `_shield_break`, `_shield_break2`, `_shield_success`, `_success1`-`7`,
  `_success_end`, `_success_end1`-`6`, `_success_end_l`, `_success_end1_l`-`6_l`, `_hold`, `_hold_attack`,
  `_hold_end`. The shield call is Ike's (`ShieldModule(0, 2, 0, 1 / 0, 1)`): re-check against the cave's
  interface notes. Not tested in game.

## Side special: Shadow Flare

From Ultimate's status code (lua2cpp_edge, `spec_side_special` research: START 08940 / 1ac20, HOLD 08f00 / 035d0 /
1a4c0, SHOT 09510 / 1a060; flare1 25d10.., flaredummy 2e300.., flare2 272e0..), its ACMD (`SpecialS*.txt`,
`edge_flare1/`, `edge_flare2/`), `vl.prc` `param_special_s` / `param_flare1` / `param_flaredummy` / `param_flare2`
(written into the code) and the ExeFS's native parts (main.bin 0x9e1770 the generation, 0x33eccf0 / 0x33ecf80 flare1,
0x33f00e8 / 0x33f06xx the dummy, 0x33ee1c8 flare2).

- **Fighter** (`edge.c` `edge_s_*`, Zelda's Din's Fire statuses): 0x153 START (SpecialSStart 0x219 / air 0x225) ->
  motion end -> 0x157 HOLD (SpecialSLoop 0x21D / 0x229, Ultimate's special_s_hold; these slots loop, the hold
  doesn't wait for them) -> on the special button's release (after its first frame) or at hold_max 27 frames ->
  0x158 SHOT (SpecialSEnd 0x221 / 0x22D, Ultimate's special_s) -> actionable from its cancel frame 31 (test 73),
  motion end -> Wait / Fall (no special fall, no landing lag). Leaving the hold with the stick back (x . lr <= -0.2) turns him round. Kinetics:
  `param_special_s` start_*: ground x speed x 0.5, brake 0.1; air x 0.6, brake 0.008, y x 0.75, gravity and max fall
  x 0.85; re-applied with the motion swapped (frame kept) on a ground / air change.
- **The shot** (flare1, article 6, weapon 0x18D, `weapons/flare1.c`, `tools/extra_kinds.json` `"on_hit": 1`, max 4):
  made on SHOT's frame 8 with the hold's frames (and +32 in the air) through Zelda's side special custom slot
  (int 0x10000049 -> the weapon's 0x10000005). r = hold / 27; n = max(1, 3 r) orbs; speed 5.5 x (1 + 0.5 r) along
  his facing, 7 frames, power x (1 + 2 r) (`AttackModule(0x2728)`); placed at his position + (lr x 10, 10) (air 7)
  (from his own slot's position, the slot found by his kind 0x42: test 72 took his position from the creation
  callback's point, assumed his head, and in game that point is ~9 lower, so the shot flew along the floor). Scripts: Ultimate's Fly (4 hitboxes, the
  beam), Hit (beam left, beam_hit), End (beam left). A wall / the floor or its life's end: End, gone.
- **The orbs**: Ultimate's hit makes a flaredummy on the fighter hit (one per fighter), which keeps ceil(n) flare2
  orbs circling it. Smash 4's MSC has no way for a weapon to make or reach other weapons, so the shot itself turns
  into the dummy and plays the orbs: on its hit (status 1) it finds the fighter hit (in hitstop, nearest: the slot
  variables), then (status 2 ORBIT) sits at that fighter's centre with the orbs as effects moved by handle
  (EffectModule 0x3 / 0x17, `edge_shadowflare_bullet`) and its hitboxes 0-4 (`orbit` script: flare2 Fly's 7 damage,
  50 degrees, KBG 75, BKB 65, size 1.5, rehit 45; Part i % 2: a dein copy has only Parts 0-1, `docs/native-notes.md`
  "AttackModule sizes", and an orb that starts, strikes or explodes clears its Part's hit record first with
  `Hit_Log_Clear`, flagged by the MSC in VAR_20, in place of Ultimate's one object and record per orb) placed each frame
  (`AttackModule(0x1, id, x, y, z)`). Orbit: life 240, orbs appear from the centre over 5 frames (no hitbox then:
  flare2 PRE has none), evenly spaced, spinning 2 pi x lerp(0.4, 0.8, n / 5) degrees a frame. A second shot on the
  same fighter: n = min(n + its n, 5), life + min(30 + 150 r, what's left of 210) (Ultimate's forwarded event), via
  that fighter's `SLOTn_SHARED_k` variables (`tools/acmd_ext_cave.py`: 0 the controller's life, 1 its heartbeat, 2
  orbs to add, 3 frames to add). Life out (status 3 CONVE): the spin brakes (0.1 a frame to 0.3-0.4), orb i strikes
  8 i frames later: thrown out at 4-5.2 then in, + 0.45-0.85 a frame up to 7-14 (lerped by R = n / 5), TRY 6.5 damage
  53 degrees; at the centre EXP: one frame, size 3.5, `edge_shadowflare_bullet_hit` x 1.3; each strike with its hit
  records cleared. Test 112: a striking orb that reaches the centre while the target is still in hitstop (another
  orb's hit) waits there and explodes on the first frame after the hitstop. The fighter KO'd / respawning / gone:
  every orb ends (`edge_shadowflare_bullet_end`).
- **Orbit per fighter (test 71):** Ultimate's `edge_flare_radius` and its ring centre on `edge_flare_node` (`waist`
  for 92 of 94 fighters) + `edge_flare_offset_x/y/z` in that joint's axes, from `fighter_param.prc`, by the target's
  fighter kind (`SLOTn_KIND`, `docs/position-variables.md`): `fl_target_shape` in flare1.c, written by
  `tools/edge_flare_targets.py`. These keep the ring just outside the body, so the orbiting orbs (7 damage, rehit
  45) don't hit their own target. The centre follows the target's joint as it moves (test 72: the variable cave reads
  its `ModelModuleF(axis, bone)`, `0x0F000290 + 4 x target`), + the offsets turned by the joint's rest-pose axes
  (its live rotation isn't readable); the rest-pose centre stays as the fallback. The target's scale (size
  changes) is taken as 1.
- **Orbiting orbs hit no one (test 72):** in the user's Ultimate clip the orbs pass through Donkey Kong's hands
  with no damage: Ultimate's orbiting orbs (Fly, 7 damage, rehit 45) never hit the fighter they circle (how is
  native, not found). A Smash 4 hitbox can't leave one fighter out, so the orbiting orbs have none here: someone
  else walking into the ring isn't hit (Ultimate: 7 damage). Strikes (TRY) and explosions (EXP) are as before. Giga Bowser (Ultimate: radius 0,
  no joint) gets Bowser's row with the radius grown by his waist height (approximated).
- **Approximated / not done:** the orbs can't be hit (Ultimate: damage
  takes n down by 0.07 a point) and don't freeze in hitlag; TRY / EXP keep the orbit's BKB 65 (Ultimate's 50; no MSC
  op for BKB) and EXP stays fighters-only; reflection (Ultimate: n x 2, life 8) isn't handled beyond the game's own
  turn; the air drift (Ultimate: control x 0.1 accel, x 0.6 max) is off; the shot's set_base_offset (its hitbox
  stretched back over the last frame) and disable_tip are left out; sounds (none of his are converted).
