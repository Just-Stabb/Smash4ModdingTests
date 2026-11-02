# Squirtle (`pzenigame`)

A port of Ultimate's Squirtle (the user's `pokemon-trainer-SSBU` zip, folder `pzenigame`:
model/body c00-c07, the `water` / `waterfall` article models, motion/body/c00, `vl.prc`,
`expression_vl.prc`, AI). New fighter kind `0x46`, character id 64, UI name `Squirtle` (subtitle
"Tiny Turtle Pokémon"), base Mario. Trait: **Shooter** (`docs/character-traits.md`,
`kirby_copy_trait()`). Roll-off: the default 2.2 / 1.0 (Mario's universal-mechanics scripts).
Down special (the user's call): Pokémon Change stays as an animation with no swap.

## v1 (`build/squirtle_v1.zip`)

Slot, model, animations, portraits and the 5-row character select, on Mario's moves:

- executable: Hero fix 64's plus every cave generator again (`kind_expand.py` with 6 kinds, base
  effects / customs, weapons, Kirby copy customs); `kind_expand_test`, `base_effects_test`,
  `base_customs_test`, `copy_custom_cave_test`: 0 failed; `weapon_expand_test`: the one failure Hero
  fix 64's executable has too (fighter 0x45's article-list order).
- data: `add_fighter.py --only pzenigame` on `fighters_latest`'s param / ui with Steve fix 10's
  `fighter_param.bin`; the folder from Mario with his universal-mechanics `game.bin` /
  `mario.mscsb`.
- model: `tools/ultimate_fighter.py model` with the new `mario` profile (`MARIO_SLOTS`): Mario's
  34 mesh slots. The open face rides in `FaceN`, the pupils in `Eye`, each blink / expression face
  in one of Mario's (Halfblink1-3 = Ultimate's Harfblink, Blink / Down = Down_Blink, Ouch, Talk,
  Attack, Capture, Heavyouch, Furafura, Cliff, Final = Hot_Blink...), the mouths in Mario's mouth
  slots; the hat / hair slots are empty. So Mario's `material_anime_eyelid / face.pac` keys (by mesh
  name) blink Squirtle and change his face. 43 bones, all 8 colours.
- eyes: Ultimate draws the iris (`eye_pzenigame_b_col`) over the white through the second UV set;
  `Textures.eye()` bakes it into the white. Squirtle's white UVs run V -1.85..-1.15 (the texture
  repeats), so each triangle is now drawn in its [0, 1) tile (before: no iris, blank white eyes).
- motions: `ultimate_fighter.py motions` (base Mario): 293 body motions (4 item / run-fall ones
  fall back to Wait1), entry, result, route map. Specials (`MARIO_MOTIONS`): neutral = Water Gun's
  shot, side = Withdraw's start, up = Waterfall, down = Pokémon Change's out / in, taunts = the
  right-facing ones.
- portraits: `tools/ultimate_portraits.py --ult pzenigame --ult-base mario --ui-name Squirtle --s4-base
  Mario --cross 3.71,790.8,24.6 --stock-whole` from Ultimate's UI (`ui-SSBU.zip`), framed as Mario's,
  toned as Smash 4's renders (Hero fix 75's curve). `--cross`: Mario's Ultimate face frame in his Smash 4
  chr_90 set by hand (least squares on the eyes, nose and cap emblem, residual up to 33 px): his two
  arts' poses differ too much to match (the search gave scale 1.02 at score 0.50, Squirtle off frame).
  `--stock-whole`: Squirtle's chara_4 is his upper body, turned (it fits chara_3 at 0.74 only), so
  stock_90 is chara_4 whole in Mario's head box. Name plates: no Smash 4 name has a Q; it is the O with
  a tail (`glyph_q`). Mario's `_09` / `_10` and `chr_40` files stay Mario's (Squirtle has 8 colours).
- custom-move labels and icons: `add_fighter_customs.py --only pzenigame` (Mario's).
- character select: `tools/chara_layout.py --style user5 --first 63 --last 72`: from 63 entries the
  icons shrink to 0.75 and the grid takes a 5th row in the 4 rows' height (rows of 13 / 12, centred;
  more columns up to 19, 93 entries, before they shrink again). 58-62 keep the 4-row layout.
- `fighter/kirby/script/msc/kirby.mscsb`: Kirby's copy of Squirtle gets the Shooter trait (only
  `kirby_copy_trait()` differs from Kirby copy customs v1's).

Sources: model, motions, UI art from Ultimate's files as above. Still Mario's: moves, hitboxes,
timings, params (`fighter_param_vl_pzenigame.bin` is Mario's), effects, sounds and voice.

Known / next: Mario's specials run (fireball, cape, Super Jump Punch, FLUDD) under Squirtle's
animations; his own moveset (ACMD from Ultimate's scripts, Water Gun / Withdraw / Waterfall,
Pokémon Change with no swap), params, effects and sounds come next.

## v2 (`build/squirtle_v2.zip`): colours, his moves, stats, effects, specials

User (v1, in game): "Squirtle's colors seem a bit washed out. Can you add Squirtle's hitboxes, stats,
timings, code and effects?"

```
python3 tools/ultimate_fighter.py model ULT/model/body/c0N MARIO/model/body/c0N OUT/c0N --empty EMPTY --max-bones 136 \
    --motions ULT/motion/body/c00 --anim-cache CACHE.json --joints Tail1,Tail2
python3 tools/ultimate_fighter.py motions ULT/motion/body/c00 ULT/model/body/c00 MARIO OUT --max-bones 136 --anim-cache CACHE.json \
    --joints Tail1,Tail2 --add D00SpecialNHold,D00SpecialNShot,D00SpecialAirNHold,D00SpecialAirNShot,D01SpecialSLoop,D01SpecialSEnd,\
D01SpecialAirSHit,D01SpecialAirSLoop,D01SpecialAirSEnd
python3 tools/vfxb_to_ptcl.py ef_pzenigame.eff FOLDER/effect/pzenigame FXDIR 0x46 fighters/pzenigame/pzenigame_effects.json \
    <the 26 pzenigame_* effects his scripts use> --prefix PtcPzenigame --templates VANILLA/fighter/*/effect/*/*.ptcl
python3 tools/pzenigame_build.py DUMP/lua2cpp_pzenigame ULT FOLDER/script/animcmd/body fighter_param_vl_pzenigame.bin OUT/c00 \
    MARIO PKG --param fighter_param.bin --bank FXDIR
```

- **Colours** (`ultimate_fighter.py` `material_for` / `skin_ramp`): his whole body is Ultimate skin
  (subsurface: CustomVector30 / 11), so it took Mario's skin material: a human one, rim (0.96, 0.57,
  0.57) x 1.5, specular (1, 0.67, 0.55), AO floor (0.58, 0.32, 0.18) and a ramp going red into the
  shadow. Its tints are now Ultimate's own at the base's brightness: the subsurface colour
  (CustomVector11: body blue (0.007, 0.175, 0.279), shell brown (0.233, 0.141, 0.088)) for the AO floor
  and the ramp (one ramp per colour: the base ramp's luminance, its tint turned to that colour at the
  same strength), the rim colour (CustomVector14: 0.75 grey body, 1 shell) for the rim, a neutral
  specular. Hero's / Sephiroth's skin (faces) gets the same on their next rebuild.
- **Normals, grabs, throws** (`tools/ultimate_acmd.py`): 30 scripts, Ultimate's frames, damage, angles,
  knockback and sizes, on his own bones (the tail: `--joints Tail1,Tail2`, joint ids of their own: 27 / 28 up to v4, 1002 / 1003 from v5);
  cancel / intangible frames into the vl file; effect scripts (102 with the specials': his own 26 and
  the common ones, `reference/ultimate_sys_effects.json`). Their sound scripts are emptied (Mario's
  would play); his own sounds aren't in yet.
- **Stats** (fighter_param kind 0x46: `tools/pzenigame_build.py` STATS): Ultimate's `fighter_param.prc`,
  Hero's / Steve's mapping: walk 0.1575 / 0.1575 / 1.281, ground friction 0.088 x 0.45, dash 1.936, run
  0.088 / 0.044 / 1.76, jump squat 3, jump x 0.95 / 0.9 / 1.3 / 1, jumps 35.35 x 0.82 / 17.03 x 0.9 /
  35.35, air 0.095 / 0.01 / 1.01 / 0.018, gravity 0.128, fall 1.35 / fast fall 2.16, landing lag n 8 /
  f 6 / b 18 / hi 6 / lw 16, weight 75, 2 jumps.
- **Effects**: 26 of `ef_pzenigame.eff`'s sets (every pzenigame_* effect his and the water's scripts
  name) after Mario's sets in `effect/pzenigame/pzenigame.010d0000` (3.4 MB); ids in
  `fighters/pzenigame/pzenigame_effects.json`.
- **Specials** (`fighters/pzenigame/pzenigame.c`: Mario's decompiled MSC + `universal_mechanics.py`, the
  same bytes as v1's, then his specials in Mario's special statuses; `specials_acmd.json`: Ultimate's
  scripts in Mario's special slots, the extra animations in his custom-move slots, extra_kinds.json
  "motions"):
  - Water Gun (0x152): SpecialNStart, SpecialNHold while special is held (up to Ultimate's
    charge_frame 45), SpecialNShot: six waters at its frames 7, 11 ... 27 (Ultimate's script), each
    told the charge through the custom slot (as the Kamehameha's level). The water: new article 5,
    weapon kind 0x198 on Mario's fireball (`extra_kinds.json` "weapons", on hit -> status 1: gone),
    `weapons/water.c`: Ultimate's param_water (speed 2.0 + 2.2 x charge / 45, 20 frames, falling 0.01 a
    frame up to 1.2), its ACMD Ultimate's pzenigame_water push (0%, 45 degrees, KBG 100) with fixed
    knockback 40 + reaction_add 75 x the charge (40 / 78 / 115 by thirds) and size x 0.8 - 1.5 (the
    effect too); model: Mario's fireball's, hidden (`nud.hidden`); motion: the fireball's.
  - Withdraw (0x153): SpecialSStart in place, the slide (SpecialS, Ultimate's 8% hitbox) 40 frames
    speeding up 1.2 -> 2.4 over 10, then SpecialSEnd slowing (x 0.9 a frame); a hit bounces him back
    (1.0, SpecialAirSHit's animation), then the end. **Approximations**: Ultimate's speeds are in its
    status code (`param_special_s` is empty), not its data. Speed: kinetic energy 3, along the facing
    (as Mario's func_137 sets it from his params). No turn-around (SpecialSOverturn) yet.
  - Waterfall (0x154, Mario's Super Jump Punch status): Ultimate's script; its rise is the animation's
    (TransN: 50 up, 25 forward, motion-driven like Mario's); Ultimate's FIGHTER_STATUS_SUPER_JUMP_PUNCH
    flags REVERSE_LR / MOVE_TRANS -> Mario's 0x2100000F / 0x2100000D (his script sets them at the same
    frames, 4 and 6), the ledge-check notify -> Allow/Disallow_Ledgegrab 1 / 2 (`ultimate_acmd.py`).
  - Pokemon Change (0x155): SpecialLwOut then SpecialLwIn, no swap (the user's call); FLUDD's pump
    isn't made, its statuses 0x157 / 0x158 aren't entered.
  Mario's fireball / cape scripts in the slots whose Ultimate motion has no game script
  (SpecialNStart, SpecialSStart) are emptied; the special slots' sounds too (`special_slots`).
- **Executable**: rpx64 + every cave again with the water (`weapon_expand.py`: his article list =
  Mario's 5 + the water; `kind_expand.py`: 10 motion slots from the record). Tests: kind_expand 0
  failed, base_effects / base_customs 0, copy_custom 0, weapon_expand only Hero's article-order check
  (the same as before).

Sources: as v1, plus Ultimate's `lua2cpp_pzenigame` scripts (body and pzenigame_water),
`fighter_param.prc` (`fighter-common-SSBU.zip`), `vl.prc` (param_special_n, param_water),
`ef_pzenigame.eff` (`effect-fighter-SSBU.zip`). Approximated: Withdraw's speeds, the water's spawn
point (the fireball's, at his hand; Ultimate's from his mouth), Water Gun's aim (Ultimate's angle
range not done).

## v3 (`build/squirtle_v3.zip`): Water Gun from his mouth, aimable; his sounds

User: "Can you fix Water Gun, make it aimable, and add sounds?"

```
python3 tools/ultimate_sound.py ULT_SOUND FOLDER SOUNDLABELTABLE SND --name Pzenigame --ult-name pzenigame \
    --dump DUMP/lua2cpp_pzenigame        (SOUNDLABELTABLE: Hero fix 71's; vc_pzenigame_cheer = Ultimate's _c00)
python3 tools/pzenigame_build.py ... --sound SND
```

- **Where the water starts**: the article's native generate (`0x02F1AC88`, Mario's fireball's) puts it
  at the thrower's joint `0x11` (`0x02F1ACEC`: `li r4, 0x11` into the model's joint position call):
  LHandN in Mario's table and so in Squirtle's. Remapping the joint would move everything else on it,
  so `water.c` moves itself on its first frame: `WATER_MOUTH_FWD` 1.5 forward, `WATER_MOUTH_UP` 2.8 up
  (his SpecialNShot pose, frames 7 - 27, through `ultimate_fighter.py`'s own pose code: mouth (jaw) ~
  forward 9.5 / up 5, left hand ~ 8.0 / 2.2).
- **Aim**: Ultimate's `FIGHTER_PZENIGAME_STATUS_SPECIAL_N_FLAG_SHOOT_ANGLE_ENABLE` window (SpecialNShot frames
  5 - 40) and `param_special_n` angle_up 40 / angle_down 25 / angle_speed 2: the stick's Y (past a 0.2
  dead zone, mine) sets the target, the aim turns 2 degrees a frame toward it (`pz_n_aim_update`). Each
  water gets it with the charge (custom slot: charge + 0x40 x (aim + 0x40)); it flies along it (speed x
  cos / sin) and is turned to it (`PostureModule(0x4, -aim, 0, 0)`). Not done: `param_special_n`
  angle 12 / offset_y / speed_add (their use not known), his body tilting with the aim.
- **Sounds** (`tools/ultimate_sound.py`, base rows kept: no ids move): se 60 tones, voice 29 (23 of
  Mario's labelled voice tones the game plays itself take Squirtle's), the cheer, 5 voice sequences;
  `soundlabeltable.bin` built on Hero fix 71's. Sound scripts (160) and expression scripts (217)
  translated from Ultimate's, the specials' too; the special slots' leftover Mario sounds emptied
  (only where the script is still Mario's: v3's first build also emptied the new Water Gun slots'
  translated ones). Left out: three common sounds with no Smash 4 id, the water's take-out sound.

## v4 (`build/squirtle_v4.zip`): the water's launch sound, the last common sounds

- **Common sounds** matched in `reference/ultimate_sound_map.json` `common_se` (Ultimate's
  `se_common.nus3bank` against Smash 4's `snd_se_joucyu`):

  | Ultimate | Smash 4 index | Smash 4 tone | Match |
  |---|---|---|---|
  | `se_common_slip_01` | 163 | `snd_se_common_058` | same sample count (3467), next to slip_02 = 164 (`_059`) |
  | `se_common_falldown_01` | 159 | `snd_se_common_054` | same sample count (25584), next to falldown_02 = 160 (`_055`) |
  | `se_common_down_soil_ss` | 95 | `snd_se_common_down_Soil_ss` | name (Ultimate's re-recorded) |
  | `se_common_c_water_m` | 354 | `snd_se_common_C_Water_m` | name |

  They are used by DownBound/DownDamage/DownSpot/Slip/SlipDown; every sound in his scripts has an id now.
- **Water's sound script**: Ultimate's `pzenigame_water` `sound_regular` (`SET_TAKEOUT_SE
  se_common_c_water_m`), translated by `ultimate_acmd.SoundTranslator` into all three water motions
  (`SET_TAKEOUT_SE(Se=0x162)`, the command Mario's fireball / pump water use).


## v5 (`build/squirtle_v5.zip`): the tail

User (v3, in game, screenshot): his tail stretched out across the stage, "breaking a lot of his
hitboxes". v2 put `Tail1` / `Tail2` in Mario's joint table 0 as joints 27 / 28 (`--joints`), past the
26 every vanilla fighter has, already known to break (Sephiroth's swords, test 20: hitboxes over the
whole stage): the tail drew stretched to the stage's origin and its 18 hitboxes (Attack13, the
AttackS3s, AttackAirB...: Ultimate's `tail1` / `tail2`) were off. `ultimate_fighter.py --joints` now
appends to table 1 (Mario's HatN 1000, FaceN 1001; the tail 1002 / 1003; table 1's length differs
per fighter and Robin's vanilla hitboxes use its SwordN, 1000). Rebuilt: every costume's
`model.jtb` (nothing else in the model changes), the game script (`ultimate_acmd.joint_ids` reads
both tables). Untested in game.

## Port framework check (docs/ultimate-port-guide.md): v1-v5 as installed

`tools/port_check.py pzenigame build/squirtle_v1.zip ... squirtle_v5.zip`, against the user's bug list:
- F1 face: 58 motions where Mario's mouth keys hide every mouth slot (Mario's expression meshes carry his
  mouth; Squirtle's mouths are his lower face): the hole / black face. Fix: drive the slots from Ultimate's
  visibility tracks (needs his Ultimate motions again).
- S4: Waterfall's angle 367 (Ultimate-only): it let go. Translator now writes 366.
- S5: ThrowF / ThrowHi / ThrowLw hitboxes freed the held opponent (NoGrabRelease 0). Translator now sets it.
- C4: Withdraw (`pz_s_move`) set energy 3's X to a positive speed whatever his facing: the right-side bias.
- E1: 13 effect scripts turn his own effects on a bone (dash attack among them): no variants were made.
- E3: 29 Smash 4 common effects stand in for Ultimate's in 113 scripts; 31 of his 32 `sys_*` map to
  ef_common.eff sets (`ultimate_port.py effects pzenigame`).
- S7: Mario's LandingAirLw landing hitbox and special slot 0x223 still Mario's.
- Not found by a check: the water showing Mario's fireball (the fireball's native code: reference/port_bases.json
  "mario"), the stock icon (portraits `--stock-icon`).
- `fighters/pzenigame/port.json`: his settings for `tools/ultimate_port.py`. To rebuild: his Ultimate
  `fighter/pzenigame` (model, motion, param) again (deleted for disk space).

## v6 (`build/squirtle_v6.zip`): rebuilt through the framework

User: the list above (effects turning / bleak, hidden face, side-B bias, Water Gun "Mario's fireball
with a windbox at close range", Smash 4 common effects, Waterfall multi-hit, throws, stock icon); his
fighter file again (Drive); "use Ultimate's real jump heights for new ports" (Squirtle keeps 0.82 /
0.9: port.json); the icons have no eyes in Ultimate's files.

Built with `tools/ultimate_port.py run pzenigame body model-c00..c07 motions effects sound specials
variants shapes stats portraits --out DIR` (port.json, port_sources.json), executable as below.
`port_check.py` over v1-v6 as installed: 0 errors (E3: 5 Smash 4 effects with no Ultimate set left in
Mario's custom-move / item scripts; S7: `specialhi_c3`, a custom-move slot).

- **Face** (F1 0): the motions step drives Mario's mouth slots (material_anime_face.pac) per frame from
  Ultimate's visibility tracks (`ultimate_fighter.py` profile `drive`, `MARIO_MOUTHS`), after the model
  step (whose pacs would overwrite it).
- **Water Gun**: the water (a copy of Mario's fireball) ran the fireball's native vtable 2 code: its life
  counter (no param for the new kind: removed at once), the ground bounce, the wall puff. `extra_kinds.json`
  `"nop2": ["0x1C", "0x3C"]` as the Kamehameha (test 15); water.c moves it. Executable: v3's (= v2's)
  + `weapon_expand.py` again: 2 words differ (the water's vtable 2 +0x1C / +0x3C -> blr);
  `weapon_expand_test.py`: the water's checks pass, the one known failure (Hero's article order) as before.
- **Withdraw**: the facing (C4), and Ultimate's `param_special_s` (vl.prc; ParamLabels names it now):
  speed_x 2.8 / air 2.3, accel_x 0.02 / air 0.01 up to stable_speed_x 3.5, limit_frame_min 20 / max 40
  (held special), end_stick_x -0.5 (pulled back: ends after the minimum), hit_speed_x 0.6 back /
  hit_speed_y 2.0 up in the air, end_x_speed_mul 0.8 / 0.7 and end_x_brake 0.07 / 0.015 a frame.
  ssbu-recomp (the user's `lua2cpp_pzenigame`, `tools/recomp_hashes.py`): the NRO's status code reads
  limit_frame_min / max with end_stick_x (f_720cc09070), attack_speed_mul, and rot / mot speeds for the
  animation (f_720cc04480); speed_x / accel / hit speeds are not in the NRO (read in the executable's
  native code), so their use above is by name. Approximated: no smash_speed_x (a flicked start), no
  slope speeds (slant_*), the over-turn (turn-around) status not made.
- **Effects**: his 26 + 31 of Ultimate's 32 common effects (`sys_screw` has no ef_common set) in his
  bank (`--extra-eff`), turned variants after the scripts (`variants` step, `--variants-last`: 10
  variants, `sys_piyo` included, no id moves); the base scripts he keeps (ledge quick options, sleep,
  ...) remapped to his Ultimate ones (43 commands, `ultimate_acmd.common_to_own`). An Ultimate
  `sys_piyo` emitter with rate 0.4 once (a buffer of 0) emits one particle. Still: Ultimate's
  refraction emitters (the water's screen warp) are skipped, and the dissolve (CSDP) of some parts.
- **Scripts**: Waterfall 367 -> 366, throws NoGrabRelease (translator), LandingAirLw emptied (no
  Ultimate script: `EMPTY_IF_ABSENT`).
- **Hurtboxes**: 12 (Ultimate's vl.prc), the tail's two on table-1 joints 1003 (vanilla Charizard /
  Bowser / Falco use table-1 hurtbox bones too).
- **Stock icons**: Ultimate's chara_2 (`--stock-icon`, `portraits.sets` stock_90 only).
- Stats: Ultimate's (`ultimate_stats.py`), jumps x 0.82 / 0.9 as before.

## v6 refraction test (`build/squirtle_v6_refraction_test.zip`, the effect bank only)

User: can Smash 4 draw Ultimate's screen-warp layer? Smash 4 has a distortion pass (shader modes 5 / 6:
Bayonetta's `ciecle1_rif` / `ring_rif1_f`, Shulk's `rifraction1` / `2`, Ryu's and Robin's Final Smash),
whose vanilla pixel program writes `(colour 1 + (colour 0 - colour 1) x texture - 0.5) x alpha x
CB4[0].x / (960, 540)` as the screen offset. Ultimate's refraction (combiner `shader_type` 1) offsets its
screen read by `(d x 50 - 25) x coefficient` (d the texture's alpha, the static block's `coefficient`:
c9 +0x100 / +0x104 in its pixel shader, tools/eft_shader_dis.py). The converter (`Templates.refraction`,
`refraction_map`) now draws them on a vanilla mode-5 template with its own program: colour 0 white,
colour 1 black, the map 0.5 + (d - 0.5) x coefficient / REFRACT_FULL (0.3) per axis, Ultimate's alpha
fade, sampler 0 (Waterfall's `ef_cmn_indirect03`). Converted: the 7 mesh parts (dash, up smash, Waterfall
start / rise, water attack, ripple; 0.15 -> map x 0.5, Waterfall 0.5 / 0.7 -> x 2.33); the 2 quads (run,
Withdraw's line) still skipped (every vanilla distortion emitter is a mesh). CB4[0].x (the pass's scale)
is the game's: strength to tune in game. Ids unchanged from v6 (`--variants-last`), so the bank ships alone.

## In-game comparison (user's videos, v6 vs Ultimate): open

- Smash attacks: up smash a wide low burst with blue haze (Ultimate: a narrow tall column); down smash
  splashes upward (Ultimate: flat along the ground to both sides); forward smash bigger and more vertical;
  a blue ring / glow on all three that Ultimate doesn't show.
- Dash / run: white droplets (`splash1` / `parts1`) fly high above him (Ultimate: low, behind his feet);
  pale water sheets stand upright (`ripple1`, `waterline*`, directional meshes with a -50 degree Z turn
  the converter drops: "rotation about disabled axes dropped", a rule from Hero's Woosh); a flat white
  quad at the dash's start (`waterline3`, a stripe quad).

## v6 effects test (`build/squirtle_v6_effects_test.zip`, the effect bank only)

Found with tools/fx_render.py against the user's Ultimate clips: down smash's water emitters turn while
they emit (EAER), and the converter turned eft2's angles into eft's at the keys only, so between keys
(eft blending eft's angles) the emitter took another path (up to 0.41 off at frame 4); and the emitters'
world gravity (eft2 emission `world_gravity`, eft byte 0x2F8) wasn't set, so gravity turned with them.
Both fixed in vfxb_to_ptcl.py (rotation keys every frame, angles unwrapped; `world_gravity` written).
Includes the refraction test. Open: the dash's droplets (both columns agree, Ultimate's footage is lower).

## v6 effects test 2 (`build/squirtle_v6_effects_test2.zip`)

User's clip of test 1: down smash's water to both sides, but two tall curtains (Ultimate: one low wide
wave). The waves are flat sheets (Y 0, 8.2 units along -Z) sent along -Z; Ultimate keeps directional
meshes in the emitter's frame, eft's type 3 turns the mesh's Y onto the motion and faces the camera.
vfxb_to_ptcl.py: a directional mesh sent along any fixed emitter direction (no spread, the all-direction
part the lesser) is type 4 (the emitter's frame), beside the old moving-along-Y rule (Woosh). 26 of
Squirtle's parts (74 converted emitters with the variants and both sides); Hero's bank has 5 such parts,
changed only when it is rebuilt.

## v6 effects test 3 (`build/squirtle_v6_effects_test3.zip`)

User's clip of test 2: the smash charge flash showed a strong rainbow band (Ultimate: a white flash, the
rainbow lost in it). sys_smash_flash's rainbow1 / rainbow2 are additive in Ultimate; the converter's
template was premultiplied (ONE / INV_SRC_ALPHA, the shader key's bit), so they covered the flash. Our
pixel program now writes alpha 0 for an additive part on such a template, so the blend adds (8 emitters:
the flash's rainbows, additive parts of landing / jump / run smoke, attack arcs, piyo, sleep, the win pose).
tools/eft_pixel_test.py covers it. Renderer stage 2 (tools/latte_pixel.py) shows the flash matching.

## v6 effects test 4 (`build/squirtle_v6_effects_test4.zip`)

User's clips of test 3 against native Ultimate: Ultimate's down smash is a low opaque sheet that is gone
quickly, with tiny droplets; ours left big white flecks lingering (the dash too). Ultimate's
alpha_process 4 (read from the vfxb shader binaries' combiner) is an erosion, not a transparency:
alpha = sat(sat((tex.a - alpha0) x 4) x alpha1) x fade, where alpha0 (the alpha-0 colour track) is a
threshold that rises over the particle's life and alpha1 a gain. The converter read it as tex.a x a0 x a1.
eft_pixel's own programs now have alpha mode 4 (ADD t.w, -c0.w; x4 clamp; x gain clamp; x vertex alpha),
vfxb_to_ptcl.py sends the alpha-0 track as the threshold and the alpha-1 mean as the gain. 89 converted
emitters (down smash sheet and droplets, dash / run splashes, Water Gun spray, landings); ids unchanged.
491 emitters across 20 Ultimate fighters use it. tools/eft_pixel_test.py covers it; fx_render shows both
columns dissolving alike (down smash, dash). Still open: the charge flash's ring, washed out by Ultimate's
screen bloom, which Smash 4 lacks.

## v6 effects test 5 (`build/squirtle_v6_effects_test5.zip`)

User's clip of test 4 against native Ultimate: down smash "separate textures blended together" where
Ultimate shows one wave splashing round in rotation; forward smash's wave curling up. The down-smash
water is one flat sheet mesh per frame (follow type 1: each keeps the emitter's frame from its birth)
from emitters swept by EAER (water_smash: Y 89 -> -120 while Z tilts 0 -> 70; water_cutter: Y -130 ->
-440), and the script turns water_smash off at frame 19. Ultimate's emitter matrices, read from
exefs main.bin (static 0x88320, animated 0x8D0A0, composed v . M at 0x8D838), turn X first (R = Rz Ry
Rx), as eft does; vfxb_to_ptcl's eft_rotation had re-expressed the angles as Z first (Sephiroth test
44's inference), standing the swept sheets up. It keeps the angles now. tools/fx_render.py also gained
birth-frame emitter frames, is_rotate axes and effect off-switches; its down / forward smash renders
put the sheets low and forward, both columns alike. Effect ids unchanged.

## v6 effects test 6 (`build/squirtle_v6_effects_test6.zip`)

User's clip of test 5 against native Ultimate: down smash better (both sides, lower) but still higher
than Ultimate's band; forward smash's wave rising in front instead of running along the ground; up
smash a V of splayed columns (Ultimate: two straight columns) inside a big blue haze. From main.bin:
the emitter setup (0x8B8A0 - 0x8B910) zeroes rotate_init / random / add / random on every particle's
disabled is_rotate axes, not only directional meshes' (the converter's old rule): the up-smash waves
(type 5 meshes, is_rotate 000, X 15 and -10 a frame) rise straight now (30 emitters cut, 14 before).
Ultimate's particle type 4 lays the particle flat (an XZ polygon: its vertex program negates the mesh's
Y, type 3's doesn't; type-4 meshes are authored in XY, 141 of 147 flat ones) and maps to eft's type 2,
not 4: the ripple's flare1, a 30-unit XY glow disc, stood up as the haze. Smash 4's own emitter matrix
rebuild (cross_f 0x04A644E0) is X first too (R = Rz Ry Rx), so test 5's angle change stands.
Open: whether eft's type 2 with a grafted rotation turns ring1 (a random Y turn) before laying it flat
(it would tilt); the forward / down smash waves higher than in Ultimate (Ultimate's EAET translation
and key evaluation (0x933D0) read as ours); fx_render doesn't draw the up-smash wave meshes.

## Scale check and diagnostics 7a / 7b

User's clip of test 6: up smash right (two straight columns, rings flat; the flare now a pale patch on
the floor from Cemu's raised camera); forward / down smash water still about twice Squirtle's height
(Ultimate: about his height). Scale ruled out: Ultimate's fighter_param.prc has Squirtle scale 0.94 and
effect_scale 0.85; the port keeps Mario's (Smash 4 fighter_param 44 scale 1.0, 49 effect_scale 0.95, the
latter the common effects' size: landing / water splash, KO, burial), 6 / 10 percent, not 2x. Ultimate's
height for him is 10 units, and fx_render puts the forward-smash wave tops at about 10 on both columns, so
the excess is Smash 4 playing the converted bank bigger or higher than modelled. Diagnostics (not fixes,
each test 6 plus one change): 7a drops water_smash's translation keys (targets 8-10), 7b the
particle-scale keys (17-18) of water_smash / water_cutter.

Diagnostics 7a / 7b (user's clips): without water_smash's translation keys (7a) the forward / down smash
water stays at Squirtle's height, curling round him; without the scale keys (7b) it still rises in
high crescents. So the lift is the emitter translation (EAET). In Ultimate water_smash's wave and splash
emitters (all but splash3) emit by distance (emit_dist_enabled, dist_unit 1-3.5, max 10), which the
converter doesn't convert (it emits by time). main.bin: distance emission (0x8D340) counts the emitter's
own movement this frame (+0x3D0, the current and previous positions through the inverted matrix,
0x8E040 - 0x8E124; the animated translation included), places the particles along the path (+0x3C0 to
+0x370), and runs only when a byte on the emitter set (+0x265) is set; otherwise those emitters emit
nothing. That byte is written from a list lookup (0xF70BC / 0xFEE78) not yet placed. Diagnostic 8: the
ten distance emitters of water_smash / water_smash_r silenced (emit_rate 0).


## v6 effects test 9 (`build/squirtle_v6_effects_test9.zip`)

Diagnostic 8 (user's clip): with water_smash's distance emitters silenced forward smash lost nearly
all its water, so they do emit in Ultimate. Side by side with native (Squirtle facing left there,
right in ours) our forward-smash water stood up over him where Ultimate's runs low and forward. Ultimate
picks water_smash / water_cutter facing left and their mirrored _r copies (with mirrored angles)
facing right, and turns top's effects with the facing without mirroring anything; the translator always
took the facing-left branch. ultimate_acmd.fix_lr_split + LR_FACING: the split is laid out and decided
in game (Float_Var_Compare(0x0F000003 < 0)), 12 compares in his effect.bin. Package: the bank (test 6's
plus nothing new) and script/animcmd/body/effect.bin.

Test 9 (user's clip, down and forward smash facing right and left): both attacks now mirror with
his facing. Down smash splashes in front first and then the wave runs round behind him; forward smash
puts the water in front and the dust cloud behind, both ways.

## v6 effects test 10 (`build/squirtle_v6_effects_test10.zip`)

Distance emission. In Ultimate, water_smash's splash1, wave1, wave2, wave3 and splash2 (and their _r
copies) emit one particle for every dist_unit (1, 2, 3, 3.5, 2) of the emitter's own movement, and the
emitter moves along its EAET path ((-3, 1, -10) -> (3, 7, -9) -> (0, 9, 3) over 6 frames). main.bin
0x8D340, run every frame of the emission window instead of the rate:
- The movement is measured in the emitter's own frame (0x8E040: through the inverse of its matrix).
- dist_min / dist_max / dist_marg (0 / 10 / 0 here) clamp it.
- A carry gives one particle per unit, each placed back along the path.
- The previous position starts at the set's (0x874E0), so the first frame emits nothing.

Converted by time, these emitters had given about half the particles (splash1 a fifth: 3 rather than 14).
vfxb_to_ptcl's `dist_emission` works out the per-frame counts along the path (splash1 0, 4, 4, 3, 3; wave1
and splash2 0, 2, 2, 1, 2; wave2 and wave3 1 a frame) and writes them as rate keys, one per frame,
with interval 0. eft can't lay a frame's particles back along the path, so they all start where the
emitter is at that frame. fx_render's Ultimate side now runs the exact routine; `--ult-time-emit`
shows the old way.

Also from main.bin (all fighters):
- The first time-based emission comes on the window's first frame (the threshold starts at 0, 0x874D8).
- Each next gap is interval + 1 + a random 0 .. interval_random - 1 (0x88750). eft does the same
  (cross_f 0x04A65350), so the converter now writes ptcl `emit_interval_random` (0x458), which before
  kept the template's value.
- Each emission adds rate x rate_random % x a random 0 - 1 (0x8D408).
- vfxb.py read rate_random and interval_random as floats; they are ints.

The byte on the emitter set that gates distance emission is copied from the set's creation arguments
(0x112C64). Diagnostic 8 showed these emitters do emit in Ultimate, so it is on for them.
docs/fx-render-eft2.md lists what fx_render's Ultimate side does exactly and what it still approximates.
Package: the bank and script/animcmd/body/effect.bin (test 9's).

## v6 effects test 11 (`build/squirtle_v6_effects_test11.zip`)

First run of the OpenSmash trace mod (docs/vfx-trace.md, the user's run: forward / down smash both
facings, 162 emitter runs). Births per frame matched fx_render for every water_smash(_r), water_cutter(_r)
and mouth_water emitter: distance emission (test 10) is what the engine does. Down smash's water_smash
emits for one frame only (its script turns it off at 19, two frames after it starts: 4 splash1 particles,
forward smash 14).

The births also showed water_smash / water_cutter's splashes all born at ONE point, (0, 0, -radius):
volume type 2 (even circle) with one division. main.bin 0x90E20: angle = start + sweep x i / n - sweep / 2,
the point (sin a rx, 0, cos a rz). eft (cross_f 0x04A4BF18) has no division count: it starts at the sweep
start and spreads an emission's own particles over the sweep. The converter had kept a template's
sweep, so each frame's splashes (up to 4) spread round a 9 - 15 unit circle: the water in separate
pieces. It now writes the sweep (start - sweep / 2; 0 for one division: exact). fx_render does both
engines' circles exactly now; its down-smash render shows the converted water as one body.
Still different in the render: Ultimate's wave stands taller at frames 24 - 28, its colour denser.

Test 11 (user's clip: forward, down, up smash): down smash is one wave sweeping round him now (no
separate pieces), up smash two straight columns over the ripple, forward smash a fan of water in front.
fx_render's "blue splash lingering at the impact point" (frames 28 - 40, test 10's note) was the
renderer's: it read Ultimate's effect function only up to the first column-0 brace, which the dumps'
facing split puts mid-function, so forward smash's EFFECT_OFF_KIND of mouth_water (frame 23) was lost
(the vfx_trace showed its crowns living 10 frames). Fixed; the forward-smash renders now differ in the
water's colour only (Ultimate a deeper blue, ours paler): next.

Colour and wave height (after test 11, no new package): the trace's emitter matrices match fx_render's
exactly (the left-over transform a pure facing turn, 0.01 degrees), the wave particles' positions within
about 6%. The native Ultimate clip's water is a pale cyan-white and its down-smash wave about 5 units
high, with a level side camera. The port's colours already were Ultimate's as displayed (the converter
display-encodes them); fx_render's Ultimate side had drawn the linear values (deep blue) and now encodes
them too. The wave: both renders stand about 5 units high with a level camera; drawn with Cemu's
downward-looking camera (fx_render --pitch 18) the ring round Squirtle (13 units out) stands up into the
tall arc of the Smash 4 footage. Its height in game is the camera's, not the bank's.

## v6 effects test 12 (`build/squirtle_v6_effects_test12.zip`)

Dissolves. Ultimate's custom shader 8 eats a part away by a mask (sampler 1's alpha) against a threshold
rising in colour 1's alpha (CSDP: the edge width). 18 more of Squirtle's parts dissolve now (24 -> 42):
- the dissolve wanted texture 0's colour grey; his water lines are BC-compressed linear textures whose
  channels sit 5 - 10 / 255 apart once display-encoded (the 2.5 / 255 test failed them): 12 / 255 now;
- the smash waves, Waterfall's water and Water Gun's crowns scroll the colour texture over a still mask
  (their own UV animations): the mask was packed into texture 0's green and had to share its UVs, so the
  dissolve was dropped. eft_pixel's `mask1` programs read the mask from texture 1 (sampler 1's alpha,
  its own UVs and animation, set_slot1(mask=True)) and keep texture 0's colour.
fx_render: Ultimate's dissolve drawn (mask x threshold over life); eft2's stripe meshes (types 5 / 6:
up smash's columns) face the camera about their motion, where they had been drawn edge-on (invisible).
Still not modelled in fx_render: eft's type 4 meshes' orientation (the converted up-smash columns render
edge-on; in game they face the camera, test 11's clip). Left: EAA1 (colour 1's alpha animated, 1.5 -> 1
over 4 frames) on 23 emitters, most of them distortion parts.

## v6 effects test 13 (`build/squirtle_v6_effects_test13.zip`)

Test 12 (user's clip): forward, down and up smash's water now breaks up with crisp edges; Water Gun's
charge shows a few droplets at the mouth (as Ultimate's mizuteppo_hold: fx_render both sides), but its
shot was a faint thin line. mizuteppo_shoot's four crowns (type 4 meshes) multiply their alpha by
sampler 2's red (ef_cmn_grade00, a gradient down V, x 2.7) on UVs of their own; a mesh's other samplers
came in as their mean (0.21): the burst a fifth as opaque. vfxb_to_ptcl.one_axis: a sampler that varies
along one axis only, which the main sampler neither scrolls nor scales, is multiplied in row by row
(exact). fx_render also reads EFFECT_FLW_POS (Water Gun's hold / shot calls had been missing on
Ultimate's side). The renders of the shot match.

Still open: forward / down smash look more separated in game than Ultimate's single mass of water. The
native clip (level camera) shows Ultimate's water as a low band, its streaks along the sweep; the Cemu
camera looks down ~18 degrees, which opens the ring of sheets (fx_render --pitch 18 shows the same on
both sides). The renders put our bank and Ultimate's close in either view, so what remains is in eft's
drawing of these parts that fx_render doesn't model; footage of both games from comparable cameras
(a level stage in Smash 4) is the next check.

## v6 effects test 14 (`build/squirtle_v6_effects_test14.zip`)

Test 13 (user's clip on Final Destination, level camera): forward / down smash's waves still stood up
as separate fanned curtains; Ultimate's (native clip) lie in one low band. fx_render had both sides
close, so the difference was in a stage it modelled on an assumption. Read from the shaders themselves:
- Ultimate (ef_pzenigame.eff, WaterSmash / WaterCutter wave1, BNSH variations 131 / 141, tools/eft_shader_dis.py): world =
  the emitter's matrix at birth (columns normalised) x the particle's rotation (X Z Y) x scale x
  (vertex + pivot) + position. No velocity input (type 5 directional programs load three more vec3s).
  So eft2's billboard type 3 is the XY polygon (4 the XZ one, already mapped to eft's XZ plate).
- Smash 4 (the converted bank's shader 112, type 4, tools/eft_vertex.py disassembly): Y = the particle's
  world motion normalised (v_inWldPosDf), X = normalize(emitter Y x motion), Z = X x motion; world =
  [X Y Z] x rotation x scale x (vertex + rotBasis) + v_inWldPos. Not the emitter's frame: each sheet,
  8 units long along -Z and sent along -Z, had its length turned up (Z -> -emitter Y), and each one
  fanned by its own velocity spread and gravity.
- eft's type 1 programs (135 vanilla mesh emitters) are v_inEmtMat x the turned, scaled vertex +
  v_inWldPos: Ultimate's formula. The converter now sends every eft2 type-3 mesh that moves to eft type 1
  (61 emitters: the smash waves, run / dash waves and smoke, Water Gun's crowns, Waterfall, Withdraw,
  common smokes); their templates (shaders 111 / 112 now) read v_inRot, so the rotations stay live.
- fx_render's Smash 4 side draws eft type 4 by the decoded program. With it, test 13's bank renders as
  the curtains seen in game (the check that the decode is right); test 14's renders as Ultimate's band.
  Types 4 at rest (crossed ribbons, Zelda's crystals) are left as they were: the program's basis is zero
  then, so the CPU must feed v_inWldPosDf something there (not read).
port_check: 0 errors. Asked: forward / down smash both ways on Final Destination, run, dash attack,
Water Gun, Waterfall.

Test 14 (user's clips): forward / down smash's water now one low connected sweep in game, as Ultimate's;
run's splashes low at his feet, Water Gun's shot a thin cone of streaks. fx_render now draws Ultimate's side
with Ultimate's own shaders (docs/fx-render-eft2.md); against the native clip it shows the smash-charge ring
as a crescent and the dust as translucent puffs, as Ultimate does. The converted ring plays the same 7-cell
table (mode 4, a cell a frame); the dust impacts (2-cell flipbook + scroll) are set too: footage decides.

## v6 effects test 15 (`build/squirtle_v6_effects_test15.zip`)

fx_render now runs both games' own vertex programs (docs/fx-render-eft2.md). Down smash's dust crown
(sys_whirlwind_l / r: impact1 / impact2 / circle1 meshes, eft2 type 3, still) was missing on the Smash 4
side: the converter sent eft2 type-3 meshes at rest to eft type 4, and eft's type-4 program aims a mesh's Y
along the particle's motion, so a still one put every vertex on the particle (latte_exec run: extent 0).
They now go to type 1 like the moving ones since test 14 (the emitter's frame, Ultimate's formula), 54
emitters in all: the crown, his ripples (up smash, dash, Waterfall start, Withdraw / run waterlines),
landing smoke, attack arcs, the dizzy crown. The crown now matches Ultimate's (a little wider at its end:
the three eft scale keys fitted to Ultimate's four). port_check E4 catches still type-4 meshes (test 14:
1 error, 49 warnings; test 15: none). 0 errors.
Note for other ports: the same branch built Sephiroth's (edge) still sword arcs as type 4 crossed ribbons;
their next build takes type 1 and needs an in-game look.

### Down smash spray height (no new package)

The Smash 4 spray rose a few units higher than Ultimate's in fx_render. That came from the renderer, not
the bank. Ultimate's side drew its CPU particles (eft2 calc type 0, all of Squirtle's) where they were
born. It also stepped them air-first, while Ultimate moves a particle by its velocity first; the
vfx_trace of the forward smash's splash2 shows it. Separately, the converted GPU programs had been fed
world values. With all three fixed, the splash emitters' heights agree (docs/fx-render-eft2.md). The
bank's GPU motion, run on that splash2, lands on Ultimate's traced positions; its gravity integrates
as a trapezoid, so a particle sits up to 0.3 units lower by the end of its life. eft has no constant
world velocity that could offset this, so it is left.

## v6 effects test 16 (`build/squirtle_v6_effects_test16.zip`)

Every water move was compared in fx_render with both games' own shaders. Each converter change below was
derived by running Ultimate's vertex programs (tools/mx_exec.py) and eft's (tools/latte_exec.py) on the
same inputs:
- eft2 type 5 is a directional billboard. Y follows the last movement (`sysLocalDiffAttr`) and
  X = movement × eye, which is eft's type-3 mesh frame. As eft type 4 (X = emitter Y × motion), the
  up-smash columns, the crown and the double-jump ring rose along the emitter's Y with zero width.
  Flat type-5 meshes are now type 3, and port_check E5 catches the case.
- eft2 type-3 quads are XY polygons, like its type-3 meshes (the common smokes' smoke1 / smoke2 draw
  the same square whatever their motion). They were eft's directional type 3 and drew edge-on; they
  are now type 1.
- eft's speed stretch (ptcl 0x7F4, CB2 gravityParam.w) was left as each template had it. It now
  takes eft2's add_vel_to_scale under add_scale_y, else 0. One template's stretch of 1 had made the
  13-unit columns 40 tall.
- XZ polygons turn after they are laid flat in Ultimate, but before it in eft. Rotation axes are now
  mapped (x, y, z) -> (x, -z, y), which is exact while one of y / z is 0. The up-smash and ripple
  rings had stood off the floor.
- EADV (the animated directional speed) becomes eft key target 16: the columns' 3 -> 2.2.

Still different in the renders:
- Up smash: its base band (wave4, eft2 type 6) is wider, and its side spikes are larger.
- Waterfall: dark streaks and more upright spikes, where Ultimate's sheet is flat and dense.
- Forward smash: the impact wedges cover about half of Ultimate's area.
- Splashes: whites cap at 1 (Ultimate's go past it into its bloom).

## v6 effects test 17 (`build/squirtle_v6_effects_test17.zip`)

Waterfall, compared emitter by emitter in fx_render:
- waveline1_1 / 1_2 (eft2 type-5 meshes, slightly curved: 1.8 deep in 13.6) stayed eft type 4. They move
  along the emitter's -Z under the call's -50 degree turn, so type 4's X (emitter Y x motion) pointed
  into the screen: edge-on streaks. Every type-5 mesh is now type 3. eft's type-3 mesh programs scale Z
  by a template constant, but Z points toward the eye, so the silhouette is unchanged.
- rifraction1 (the refraction along the column, about 80 units) has no type-3 distortion template in
  the corpus. On the billboard one it stood upright. It is now skipped.
- Random rotation: eft2 turns init + random x (U - 1/2) (wave1's program run with U 0 / 0.5 / 1:
  -0.61 / 0 / +0.61 rad). eft turns init + U x random (cross_f 0x04A5DAB4, U a u32 x 2^-32). eft's init
  is now init - random / 2. eft2's rot_rev_rand goes to ptcl 0x2FC - 0x2FE.
- fx_render's Smash 4 side now gives particles eft's random life (life - int(U x 0x4B4), cross_f
  0x04A5C8BC) and eft's rotation range. Distortion passes are no longer drawn there; they were drawn
  black.

Still different: the start spikes (wave1) look about 1.7x fuller than Ultimate's. The geometry is no
bigger (Ultimate's reaches 34 units, ours 20), but Ultimate's dissolve eats more of it. Threshold, edge,
mask UVs and formula all match, so that cause is still open.

## v6 effects test 18 (`build/squirtle_v6_effects_test18.zip`)

Waterfall's spikes (TakinoboriStart wave1). With their spin forced to zero, both sides matched within 5%
at every age, which put the difference in the random parts. Ultimate's programs take sampler 0's scroll
random from the particle's random x, and sampler 1's (the dissolve mask's) from its y, which also drives
the Y spin. eft's programs do the same per slot (both swept in mx_exec / latte_exec).
- same_uv took two samplers with equal UV settings as one UV set. It no longer does when either has a
  random scroll, scale or turn. The mask is now drawn live as texture 1 (23 emitters). The texel-by-texel
  combine had laid the mask's empty parts over the texture's own, so it cut nothing.
- exact_texture no longer combines a dissolve's mask into colour / alpha.
- Random life: Ultimate's curves run on floor(life x (1 - r U)) (thresholds identical for lives
  6.0 - 6.7). eft's life is now ceil(life) - 1, with random frames chosen for the same mean.
- Result: wave1 covers 38.9k px against Ultimate's 40.5k (three seeds; it was 53.5k).

## v6 effects test 19 (`build/squirtle_v6_effects_test19.zip`)

Up smash's base band (AttackHi4 wave4) and the dash / run-brake ripples (Brake wave1); both are eft2 type-6 meshes.
- Frame: eft2's type 6 is Y = motion, X = motion x Y, Z = X x motion (its program, run with set inputs). eft's
  type 4 is the same turned 180 degrees about the motion. The mesh is now turned 180 degrees about its Y
  (x, z negated). The band hung under the floor, and the test-18 ripples sank under the stage during dash / run.
- Scale: Ultimate gives a particle all three scale axes (main.bin 0x87CF0 copies EMTR +0x9C0's xyz to the
  instance; 0x90738 writes each axis x (1 - random x U)). fx_render's Ultimate side had used X for Z, which
  drew Ultimate's band 1.7x too low; it now feeds xyz. With that, both peak at 5.9 high.
- Scale curve: wave4's curve has its own Z (0.2 -> 0.96 at 30% -> 0.3) while X / Y grow 0.77 -> 1.3 (the
  ptcl's curve has two axes, and its type-4 programs scale Z by X, or by Y under uboFlag 0x08000000). The
  converter grafts Z(t) / X(t) onto v_inPos.z (eft_vertex.graft_zcurve). t = age / the mean eft life (an
  approximation for each particle's own life). The particles fan out in every horizontal direction, so
  putting Z's curve on X (tried first) narrowed the pieces heading toward the camera.
- Result: wave4 covers 18.1k / 18.2k px against Ultimate's 19.4k / 19.1k (two seeds; 28.7k before). Height
  2.3 / 5.4 at ages 4 / 8 against 2.3 / 5.9. Whole moves: AttackHi4 229k vs 199k, AttackLw4 203k vs 179k,
  AttackS4 137k vs 151k, Dash 32.1k vs 30.1k, RunBrakeL 14.4k vs 14.7k, SpecialHi 288k vs 264k.
- Also grafted: down smash's wave2 / wave3 (type 1, the same Z-curve difference). Waterfall's cylinder1 and
  light1 templates can't take the graft (their Z follows X, as before).

## v6 effects test 20 (`build/squirtle_v6_effects_test20.zip`)

Waterfall's whiter, wispy look (test 18's zoomed clip). The renderer showed it too: one piece, waveline1_2,
drew as a soft white haze over the column.
- waveline1_2's Ultimate pixel program (shader 32, run with mx_exec) works as follows:
  - Sampler 0 is a distortion map that bends sampler 1.
  - Sampler 1 is the dissolve mask; its colour is pure white.
  - Sampler 2 is the picture: alpha = its alpha, colour = colour 1 + (colour 0 - colour 1) x sampler 2 x sampler 1.
  - Samplers 1 and 2 take different random scrolls: random z and x (vertex program run with each random
    component changed in turn).
- main_texture had taken sampler 1 and averaged sampler 2 in, losing the shape (the blob). A dissolve
  whose sampler 1 is white now takes sampler 2, with the mask live as texture 1.
- Colour mode 2 mixes colour 0 / 1 by the texture. Ultimate mixes by the linear value in linear light.
  Ours mixes display-encoded keys, by a display-encoded (UNORM) or stored-sRGB weight, which pulls
  towards white. The converter now bakes a weight curve per emitter (mix_weight_curve): least squares
  against Ultimate's mix over the colour tracks' life, one curve for all channels.
- A dissolve's threshold now takes colour 0's track when colour 0 is constant and colour 1 animates
  (about 25 parts). waveline1_2's colour 1 runs dark blue -> pale over its life; it had been held at its mean.
- Result for waveline1_2's drawn colours (R; renderer, frames 10-30):

  | | Ultimate | Before | Now |
  |---|---|---|---|
  | Median | 0.64 | 0.71 (blob) | 0.62 |
  | Darkest 10% | 0.45 | 0.59 | 0.34 |

  The darkest are darker than Ultimate's because Smash 4 blends alpha in display space, Ultimate in
  linear light. Coverage per move is unchanged from test 19.
- Still open: Waterfall's water1 splash sheets (alpha mode 4, threshold erosion) are fainter / smaller
  than Ultimate's white sheets.

## v6 effects test 21 (`build/squirtle_v6_effects_test21.zip`)

Waterfall's water1 splash sheets (TakinoboriStart, eft2 type 3, dissolve, life 8). Over six seeds the
sheets covered 78k px on ours against Ultimate's 117k. The scale curve, rotation ranges, bounding boxes,
threshold keys and alpha fade all matched; by particle age they agreed at ages 0-2 and fell to half by age 4.
- tex_anim switches: water1's samplers have scroll / scale / rotate switched off, yet store a scroll of
  +0.05 a frame and a V random of 1. Ultimate's vertex program (run with each random component changed in
  turn) leaves their UVs alone apart from the random flip. Ours animated them: the mask slid off the water.
  The converter now treats a switched-off component as identity (gate_uv_anim). Across the moves checked
  (up / down / side smash, dash, Waterfall) every program's UV behaviour agrees with its switches.
- Random flips: sampler 0 flips U on random x, sampler 1 on random z (independent). eft's 0x4DA / 0x4DB
  were never written. Now written; where both slots flip, slot 1's is left to slot 0 (eft flips both on
  one random), so the mask lies mirrored over the water on half the particles (measured 6161 of 11355).
- fit_texture now judges each channel at its own level (the mask had shrunk to 32 x 32). Alpha
  sections are at least 1% (the two-texture template drew nothing on a particle's first frame).
- Result: the sheets now cover about 141k against Ultimate's 117k (ages 0-2 within a few percent; ages
  3-5 above). The rest is a one-frame lag in eft's GPU-side programs: this template computes its colour
  / alpha / threshold at (age - emp0.w) / life, emp0.w being the instance's +0x5C (cross_f 0x04A65B18). The
  renderer takes it as 1, unverified; if it is the frame step in game too, every GPU-side template's
  curves run a frame late, and compensating belongs in the converter for all of them.
- Still open: Waterfall's water1 life-20 streaks (alpha mode 4, directional) cover about 5x Ultimate's.
- Renderer note: renders run in parallel right after a rebuild race on the shader cache; one of them
  drew nothing on half the seeds. Warm the cache with one render first.


## v6 effects test 22 (`build/squirtle_v6_effects_test22.zip`): Ultimate's own shaders

The first build of the universal shader path (docs/eft-universal-shader-scope.md, phases 0-3).
- **Shaders.** 308 of the bank's emitters (255 shaders) are drawn by Ultimate's own vertex and pixel programs:
  each emitter's BNSH variation translated (tools/ult_shader_glsl.py), lowered to Latte (tools/ult_to_latte.py),
  and assembled under the converted template's key record (tools/ult_shader.py,
  vfxb_to_ptcl.universal_shader).
- **eft's CPU side** is set to give the programs Ultimate's particle: base scale with a flat eft curve, the
  initial rotation only, the raw mesh, Ultimate's textures (sRGB ones as eft's sRGB BC3).
- **Fallback.** Refraction parts, child emitters, and any program that doesn't lower keep test 21's
  conversion. None failed in this build.

Sources and checks:
- The programs, their constants (c9 from the emitter, c13 CSDP, c1 immediates) and the matrix each applies
  (probed by running it) come from ef_pzenigame.eff / ef_common.eff.
- Every vertex and pixel program passes the differential test against the translated original:
  - Squirtle's 156 non-refraction programs and the 166 common ones his scripts call;
  - every stage, in both identity and eft mode, with the vertex / pixel pairs linked.
- In fx_render, up smash, down smash and Waterfall draw like Ultimate's. Up smash's emitters are within a few %
  of Ultimate's drawn pixels; what is left is the two sides' own random draws.

Still approximated:
- The call's colour, alpha and scale (c16, c10[12 - 15]) at their defaults.
- No soft-particle fade: eft has no depth texture.
- Display-space blending.

Bank: 11.5 MB (test 21: 8.6 MB), after dropping the 3.7 MB of converted textures the universal emitters no
longer use (Ptcl.drop_unused_textures).

## v6 effects test 23 (`build/squirtle_v6_effects_test23.zip`): test 22's frozen parts

In game, test 22 left many parts frozen, many at the stage's origin (the user's clip).
- **Cause.** 145 universal emitters had kept their GPU template's GPU-calc flags: the emitter's byte 5 bit 0x80
  and the key's byte 4 bit 0x02, which split vanilla's GPU emitters / programs from the CPU's exactly. With them
  on, eft moves nothing on the CPU and the particle records hold birth values. Ultimate's programs, written for
  particles already moved, drew them as they stood.
- **Fix.** `vfxb_to_ptcl.universal_shader` clears both. The streams eft's CPU writes follow the program's own
  attributes (cross_f 0x04A57DA4: the shader object's attribute locations +0x578.. set its stream flags +0x5A0),
  so nothing else changes.
- **Why the checks missed it.** fx_render took GPU from the program's `v_inVec`, which every universal program
  reads. It now follows the emitter's flag; on test 22's bank it draws up smash's converted side empty.
- **Now caught.** port_check E6 universal-gpu is an ERROR: on v6 + test 22 it reports 145 emitters and 109 keys.
  On v6 + test 23: 0 errors (the 9 warnings are test 22's).
- **Unchanged.** The scripts (effect.bin) and the .efc are byte for byte test 22's. In fx_render, up smash,
  down smash, Waterfall and dash draw as before and like Ultimate's.

## v6 effects test 24 (`build/squirtle_v6_effects_test24.zip`): test 23's vertical white lines

The user's report on test 23: effects move and look good, apart from occasional thin vertical white lines in
different moves. In the clip, textured water streaks run from Squirtle up off the top of the screen for a frame
or so, at the start of moves.
- **Cause.** Ultimate's programs read the particle's last movement (sysLocalDiffAttr -> `v_inWldPosDf`) on any
  particle type. eft works that stream out only under the emitter's +0x308 bit 0x10 (cross_f 0x04A62888 /
  0x04A62F4C), which vanilla sets on its directional types 3 / 4 and no other (6,108 vanilla CPU emitters). With
  the bit off, nothing writes the stream, so it holds the particle slot's last occupant's value, and the
  programs stretched the part along it.
- **Affected:** 20 emitters on non-directional templates. The common attack / dash / run / turn smokes, up
  smash's splash1_2, the dash's parts1, Water Gun's water / splashes, Waterfall's end.
- **Fix.** `universal_shader` sets the bit when the program reads the stream. The bank differs from test 23 in
  exactly those 20 bytes; effect.bin and the .efc are unchanged.
- **Checks.**
  - port_check E6 universal-diff is an ERROR (20 on test 23; 0 errors on v6 + test 24).
  - fx_render, which fed the velocity and so drew these right, now warns: on test 23 for up smash's splash1_2
    and the dash's parts1, on test 24 for none.

## v6 effects test 25 (`build/squirtle_v6_effects_test25.zip`): tilts, jabs and aerials

The user's report on test 24: up tilt missing its speed line; forward tilt wrong facing left and without its
colour; jab 1 / 2 / 3 and up air without their colours; down / back air without their twisting effects.
- **Colours** (CLAUDE.md now: effect colours must match Ultimate's).
  - Ultimate's engine tints `sys_attack_line` / `_b` and `sys_attack_arc` / `_b` / `_c` / `_d` with the
    fighter's `common_effect_0` (fighter_param.prc; his (0.32, 1.6, 0.4) green). The pipeline never passed
    it: port.json `tint_for` was empty. `tools/ultimate_tints.py` now passes it by default, multiplied into
    the universal programs' c10 colours (linear) as eft2 does.
  - Up tilt's speed line takes `LAST_PARTICLE_SET_COLOR(0.4, 1, 0.5)` after every call: baked into the bank.
- **Script translation.** Effect macros now map to Smash 4's command of the same name (the ACMD ids are crc32
  of the names), flips with their type:
  - the up-tilt speed line (`EFFECT_FOLLOW_FLIP_ALPHA`) and the aerials' winds (`EFFECT_FOLLOW_RND`,
    `_FLIP_ALPHA`) had been dropped;
  - forward tilt's arc (0, -30, 195) is now `EFFECT_FOLLOW_FLIP` (mirrored facing left);
  - its whirlwind is `FOOT_EFFECT_FLIP` with its r / l pair.
- **Colour scale.** 224 universal emitters had eft's colour scale (+0x778) on top of the program's own
  (c9 word 236), x 1.04 to 3, in tests 22-24. It is now 1.
- **Checks.**
  - `port_check`: E6 universal-colour-scale and E7 effect-macros are new. Over v6 + test 25: 0 errors; the
    warnings are test 24's plus E7's known gaps (FLASH x21, FLASH_FRM x15).
  - fx_render: the Ultimate side applies the engine colours; the Smash 4 side reads flip commands and
    follows facing checks.
  - In fx_render, jab 1's green line, up tilt's speed line and down / back air's winds match Ultimate.
    Forward tilt's arc isn't drawn on fx_render's Ultimate side (a renderer gap), so it is unchecked there.

## Status after effects test 25

- Effects: confirmed correct by the user in game (test 25 on v6): the universal shader path, colours and
  script translation are done for Squirtle.
- Functionality (his specials especially): not finished. Left for later, since the user plans to change
  Squirtle heavily.

## v6 extras 1 (`build/squirtle_v6_extras1.zip`): magnifier, up smash's rumble

- **Magnifier (user: not shown):** the off-screen magnifier and 8-player Smash draw `model/body/l00`-`l07`, which
  no Squirtle package had. They are copies of v6's `c00`-`c07` (the pipeline's new `low-models` step).
- **Up smash's rumble (user: too hard, lingers for seconds):** Ultimate starts `rbkind_loopattack` (looping) at
  frame 19 and erases it at 34. It was translated as a plain `Rumble(8)`; Smash 4's kind 8 loops for good
  (param/pad_rumble) and there is no stop command. Now `Rumble_Loop(8)`, which stops with the status. It is the
  only change to expression.bin.
- `port_check` over v6 + test 25 + extras 1: 0 errors (new: M6 low-models, S8 rumble-endless).

## v6 extras 2 (`build/squirtle_v6_extras2.zip`): announcer, victory theme

The user, on extras 1: his own victory poses play; the announcer says "Mario"; no crowd chant.
- **Announcer:** Ultimate has no "Squirtle" call (`vc_narration_characall`: 112 calls, the Pokémon Trainer's
  Pokémon none of their own), so his call is Ultimate's `poketrainer`, appended to Smash 4's
  `snd_se_narration_characall.nus3bank` as label 86 (row 0x38 grown to 87). His 16 ids in
  `ui_sound_call_voice_db.bin` (id 64, Mario's 0x380000 before) are 0x380056. `tools/fighter_extras.py narration`.
- **Victory theme:** `bgm_fighter.fbb` extended from 58 to 71 kinds: 0x46 Squirtle and 0x43 Incineroar Pikachu's,
  0x42 Sephiroth Cloud's, 0x41 Supamario Mario's, 0x44 Steve Pit's, 0x45 Hero Robin's (`fighter_extras.py fanfare`).
  A test: whether the reader takes the file's count is not known yet.
- **Chant:** his cheer bank is set up as Mario's (same bank id and row, timing row for kind 0x46); why it doesn't
  play is still open (docs/new-fighter-slot.md "Announcer and fanfare").
- `port_check` over v6 + test 25 + extras 1 + extras 2: 0 errors.

## v6 extras 3 (`build/squirtle_v6_extras3.zip`): KO screams, crowd chant, victory theme

The user: "KO sounds are also missing" (and no chant, from extras 1).
- **Cause:** the executable reads `commonsoundtable.csb` (KO screams + the chant bank's row) and
  `bgm_fighter.fbb` (victory theme) into records it names itself, by index, from tables of the vanilla roster
  (62 / 58 names), then finds a fighter's record by its name. A new kind's record never had a name, so
  extras 2's fanfare entries were never found, and the csb had no record for Squirtle at all. His voice bank's
  KO tones are fine (MissFoot01 / 02 and Damage_hoshikie hold his Ultimate `missfoot01` / `02` and
  `damage_twinkle`); nothing asked for them.
- **Executable:** `tools/kind_expand.py` grows both name tables with the new kinds' names (`SOUND_NAME_TABLES`:
  6 instructions and two cave tables); built on `aerial_buffer_fix.zip`'s `cross_f.rpx` (the newest), nothing
  else changed (195 words). `kind_expand_test.py` runs both parsers and the fanfare lookup on files with a
  record per kind: the new kinds' records are found (unpatched: none), the vanilla ones as before. 0 failed.
- **commonsoundtable.csb:** records 62-67 for the new kinds, each its base's (Squirtle record 67 = Mario's:
  labels 0x12 / 0x13 / 0x0B on row 0x5E, chant row 0x89F; his banks keep Mario's ids). Hero, Sephiroth,
  Incineroar, Steve and Supamario get their bases' records too (`tools/fighter_extras.py common`).
- `port_check` (new checks A2 sound-names, A3 common-voices, A4 fanfare): v6 + test 25 + extras 1 + extras 2 +
  the aerial buffer fix had the 3 errors; with extras 3, 0 errors.
