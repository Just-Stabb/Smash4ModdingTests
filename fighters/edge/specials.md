# Sephiroth's specials (plan and progress)

User (after test 56): "Can you do Sephiroth's specials? (Please keep Zelda's articles and make new
ones)". Built on his Zelda slot (kind 0x42): Zelda's native code, status table and article list stay;
his moves are new MSC in her special statuses, Ultimate's animations in her special motion slots,
and four new article kinds after hers.

## Sources

- Ultimate scripts: `lua2cpp_edge/edge/Special*.txt` (body), `edge_fire/` (Flare: `SpecialN1-3`,
  `BurstS/M/L`), `edge_flare1/` (`Fly`, `Hit`, `End`), `edge_flare2/` (`Fly`, `Try`, `Exp`, `End`),
  `edge_flash/` (`Attack`). Their statuses are native code in Ultimate (not in the dump): the moves'
  logic is rebuilt from the scripts, the params and the videos.
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
- Up (0x154 start, 0x159 Blade Dash / Octaslash, 0x15A ends): no article.
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
