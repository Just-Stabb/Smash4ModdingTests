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

Her articles: 0 `dein` (8 motion slots, no model), 1 `dein_s`, 2 `phantom`; kept.

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
  stage sides (Ultimate's hook only re-aims on the ground; this is the port's).
- **Ground end:** x x 0.6 (Octaslash 0.9; 0.25 if landed), brake 0.12 (0.06); actionable at the motion's
  cancel frame 27 (56); off an edge -> Fall; end -> Wait.
- **Air end:** x x 0.4 (0.9), brake 0.02, the rush's y x the same into gravity, gravity 0.12; from frame 18
  drift with max speed x 0.5; pitch back to 0 over frames 11-44 (18-53); landing -> LandingFallSpecial, end
  -> SpecialFall.
- **Landing lag** (`f_147f0`): 27 (Octaslash 56) in the landing frame float 0 when the next status is
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
  records cleared. The fighter KO'd / respawning / gone: every orb ends (`edge_shadowflare_bullet_end`).
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
