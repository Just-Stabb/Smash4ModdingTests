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

- Articles (`tools/extra_kinds.json` `weapons`, all based on `dein`): 3 `fire` 0x18C, 4 `flare1`
  0x18D, 5 `flare2` 0x18E, 6 `flash` 0x18F. Their files under `fighter/edge/` (`script/msc/<name>/`,
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
article's MSC and scripts, Zelda's `dein` files as the not-yet-made articles' placeholders, the
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
