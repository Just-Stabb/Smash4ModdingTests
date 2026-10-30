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
