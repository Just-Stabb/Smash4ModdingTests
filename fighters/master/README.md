# Byleth (`master`)

A port of Ultimate's Byleth (internal name `master`) to Smash 4, on **Zero Suit Samus's base** (`szerosuit`, kind
0x19). New fighter kind **`0x47`**, character id **65**, UI name `Byleth` (subtitle "A Heroic Legacy": Ultimate's own
string for him, `msg_menu.msbt` `mnu_standard_sub_master`; Ultimate has no other per-fighter subtitle), texture-id block `0x40C70000` (`reference/port_bases.json` `_texture_ids`). Trait: **Strike** (the user's
choice; `docs/character-traits.md`, `kirby_copy_trait()`). Roll-off: the default 2.2 / 1.0 with Hero's momentum
(ZSS's universal-mechanics body, below).

The port goes through the framework (`docs/ultimate-port-guide.md`): `fighters/master/port.json`,
`tools/ultimate_port.py` (init / plan / run), `reference/port_bases.json` `szerosuit` (her traps, new with this port).

## Status: v3 (`scratchpad/byleth_v3.zip`, over v2: the female animations, the win cameras, exe_v46s; in-game TEST)

User (v2 handover): "build the per-costume motion selection in the exe ... then her side" and "keep looking for a way
to play Ultimate's converted win cameras", both approved as in-game test builds.

| part | state |
|---|---|
| female animations (c01 / c03 / c05 / c07) | **built, tested offline**: exe costume groups (exe_v46s), `motion/body2` + entry / result / route map, her face / eyelid pacs, low models; not tested in game |
| costume tests in the scripts | `INT_COLOR % 2` and the `GET_VOICE_VARIATION` chains -> Float_Var_Compare on COSTUME_PARITY (new variable); the taunt / win sound scripts, empty in v1 / v2, play |
| win cameras | **the result scene does play camera motions** (its script loads `motion/camera/result/<name>/<n>/`): his three shipped there, no exe change; format to confirm in game |
| exe | **exe_v46s** = exe_v46r + `tools/costume_group_cave.py` |
| package | **a complete fresh install** (the user installed neither v1 nor v2): `scratchpad/byleth/make_pkg_v3.sh` -> `scratchpad/byleth_v3.zip` (457 files): exe_v46s, the whole fighter/master (+ the kind folder's AI / Kirby-copy bank / FinMaster, his sound banks), `motion/camera/result/master`, his vl file, his portraits, `shader/effect_trail.nsh` (vanilla + trail shader 3, `trail_shader.py nsh`), Kirby's kirby.mscsb (his trait), `optional_sephiroth/` flare1.mscsb (0x47's orbit row), Sm4shCommand data; the user's own data files come from `byleth_userdata_v1.zip` (another build), `not_for_install/` the vanilla stand-ins. INSTALL / TEST README: `scratchpad/byleth/INSTALL_README_v3.txt` |
| port_check | `port_check master scratchpad/byleth_v3.zip`: **0 ERROR**, 21 WARN (v1's B1 / E3 / E7 / M5); R1 now ERROR when missing, new M11 motion-groups (v1 + v2: 5 ERROR, as expected); `motion/` is now an install root |
| translator | also: the win sound scripts' `GET_VOICE_REGION == VOICE_US_EN` wrapper taken (English), as `first_voice_region` |

### v3: female animations (the executable side)

Traced in exe_v46r (`tools/costume_group_cave.py`'s docstring has the addresses):
- **In battle** every player has its own resource loader (`[[0x102F9028] + 0x58 + 4 entry]`, 0x030C3368; per-costume
  models prove it: the model id kind x 0x11 + 0 holds each player's own cNN). The loader (0x030C0828) registers the body
  motion folder as id kind x 0x11 + 3 with the path from 0x030BB18C(kind, type 0, costume), and the fighter's
  construction (0x02E130E4) reads its own player's id + 3 (0x030BF0FC) and binds the MotionModule to that path
  (0x02C5BFB8 -> 0x03306AC0: a motion resource by path). So the only per-costume piece in battle is the path: two
  Byleths of both groups load both packs. The v2 handover's "open piece" (the player record's byte +0x23, picking
  kind x 0x11 + 0 / + 1 in mode 3) is the **model** pack (mode 3 loads c00 and c01 models) and Kirby's copy resources'
  category (`+0x23 << 28`, 0x030C5240): not a motion selector. Its writers (0x028190F8 from a settings copy,
  0x029C7558 / 0x029C75F4) were left alone.
- **Entry / result packs** live in shared loaders under kind x 9 + 1; Bayonetta's second group uses kind x 9 + 2 (no
  other kind uses + 2: every `mulli rX, kind, 9` checked).
- **The patch**: the path builder's Bayonetta test (0x030BB1AC) -> a cave: kind 0x47 (any kind with a mask byte) and a
  masked costume builds `fighter/master/motion/body2/` (`bodyentry2/`, `bodyresult2/`, `bodyroutemap2/`: vanilla's own
  strings) with the game's own string calls; the default paths of the entry load / unload, result load (two words) /
  unload and the getter (0x030C1A40, 0x030C1B10, 0x030C1C24, 0x030C1CDC, 0x030C1ECC, 0x030C20E8) take kind x 9 + 1 +
  group. Masks from `tools/extra_kinds.json` "motion_group2" (Byleth `[1, 3, 5, 7]` = 0xAA). Plus three read-only
  variables (get_float, chained on position_vars' get_other `b` at 0x037EDC94): COSTUME 0x0F000500, COSTUME_PARITY
  0x0F000501, MOTION_GROUP 0x0F000502 (the fighter found as position_vars finds self; its player loader's +0x28).
- **Tests** (`tools/costume_group_test.py exe_v46s exe_v46r`, unicorn, real code): 131 ok, 0 failed: the path builder for
  every type / costume of 0x47 (c00 `body`, c01 `body2`, ... `bodyroutemap2`), Bayonetta c00 / c05 / c02 as vanilla,
  ZSS / Hero / Squirtle untouched; every id site run from its word to its call (kind x 9 + 1 / + 2); the getter whole;
  the variables through a fighter WorkModule's get_float with a fake fighter table and loaders (two Byleths c00 / c03,
  Bayonetta c05, ZSS c06), an unknown WorkModule 0, other IDs passed on; the original exe_v46r gives the old answers.

### v3: female animations (her side)

- `port.json` motions.group2 (`c01 c03 c05 c07`, source `c01`: Ultimate's c01 / c03 / c05 / c07 motion folders are
  byte-identical; 348 of 368 files differ from c00's): `ultimate_port.py run master motions motions-group2 low-models`.
  The male step now writes c00 / c02 / c04 / c06's face pacs only (its main.pac / pacs byte-identical to v2's); the new
  `motions-group2` step converts c01's motions on her skeleton (130 bones: her hair S_Hair*, KnifeholderF1,
  S_StringF1, H_Armtwist animated; Wait1 361 frames) into `motion/body2` (322), `bodyentry2` (2), `bodyresult2` (7),
  `bodyroutemap2` (4) (+ lhand / rhand) and her costumes' material_anime face / eyelid pacs from her motions' mouth /
  eye / weapon visibility (weapon_vis.json as the male's: the same scripts). Stand-ins as the male's (7 on Wait1).
- Her models: rebuilding c01 with her motions' animated bones gives the same 129 + joint skeleton as v1's (no bone was
  merged: under budget), so cNN / lNN models are unchanged; lNN take the new face pacs.
- Her skirt bones (S_Skirt*) have no tracks in Ultimate's motions either (physics there): they hold their bind pose.
- Scripts: `ultimate_acmd.py` turns `FIGHTER_INSTANCE_WORK_ID_INT_COLOR % 2` into Float_Var_Compare(COSTUME_PARITY)
  True / Else (AppealHiL / R's flash on 10 (female) / 19 (male), Win3's flashes, smoke, slash, aura) and folds the sound
  scripts' `GET_VOICE_VARIATION == 0 ... 7` chains (even / odd identical) into the same test (`fold_voice_variation`):
  those sound scripts (taunts, wins) were empty in v1 / v2.
- Not verified: the result scene's fighters in the fighter table the costume variables search (if they aren't, a
  female winner's Win3 flashes / win sounds take the male branch; her result poses come from bodyresult2 either way).
- Not done: her win cameras (the result scene's camera path has no costume: hers play his); the female cheer bank;
  Sm4shCommand's data files (Events.cfg / Aliases / Tooltips, regenerated) ship in the package, the program itself
  is unchanged (no rebuild needed: no code changed).

### v3: win cameras

**Smash 4's result screen does play per-fighter camera motions.** The result scene is an Xtal script,
`data/script/xscene_result.xtal` (script-smash4-vanilla.zip, compiled; its strings read): it loads
`motion/camera/result/%s/%d/` (else prints "NOT FOUND CAMERA!" and loads `motion/camera/result/default/1/`; teams
`motion/camera/result/team/%d/`, no contest `nocontest/%d/`) and calls its camera's `start_motion` (binding 0x0310861C:
the camera's motion player at +0x38, 0x02D38734, the player stage and Final Smash cameras use; modes 0 look-at, 1 spline,
2 motion at +0x470). The bindings it uses are in the executable's registration code (0x030D....: `load_motion`
0x03111AC8 (a motion folder resource: its .omo / .pac files), `create_camera`, `set_projection_param`, `look_at`,
`get_fighter_model_name_from_fighter_kind` 0x030ED508 -> 0x0275DB24, kind_expand's name table: `master`).
v2's reading ("plays no camera motion", result_param.bin only) missed the script. So no executable hook: the `camera`
step writes `motion/camera/result/master/1-3/camera_motion.omo` + `.vbn` (the Final Smash camera form: Corrin's one
`gya_camera` bone, frames 131 / 171 / 181). To confirm in game (INSTALL README test 4): the vanilla folders' own file
names / node form (not in any archive here: the user's `data/motion/camera/result/`), that `%d` is the win pose, the
units / origin and the field of view (Ultimate's 0.28-0.68 rad is not in the motion). Not decoded: the Xtal bytecode
(Smash 4's serializer differs from xtal-language's public one: u8 string lengths).

### v3: executable exe_v46s

`scratchpad/byleth/exe/exe_v46s.rpx` (sha1 7fd810c03a8b66a2420a402af4c2503504e49bef) = exe_v46r +
`python3 tools/costume_group_cave.py --rpx exe_v46r.rpx` (cave 0x04BAD800-0x04BADCD0, 8 hooks; checks every replaced
word). Suites (exe_v46p as the original, as for exe_v46r): the same results as exe_v46r's: kind_expand_test 21, the same
lines; weapon_expand_append test 3; sound_alias_cave_test 6 (its "no other word changed" lists the new hooks too);
acmd_ext_test 18; kirby_copy_new_test 123; kirby_copy_pool_test 151 (stage_q); position_vars_test 0; vec_target_test 0;
costume_group_test 0 failed (131 ok).

## Status: v2 (`scratchpad/byleth_v2.zip`, over v1: the rapid jab, the angled forward smashes, Ultimate's low models, exe_v46r)

v2 (user: "Add the rapid jab and angled forward smashes to Byleth, as well as port over their Ultimate camera angles
(for victory animations) and ensure all future ports also port their camera and LOD models"; then "please add the
female animations"):

| part | state |
|---|---|
| rapid jab, angled forward smashes | **done** ("v2: the rapid jab and the angled forward smashes" below) |
| low models (magnifier, 8-player Smash) | **done**: Ultimate's own low model (lod.xmb) in l00-l07 |
| win cameras | **converted, not shown**: Smash 4's result screen plays no camera motion ("v2: win cameras") |
| female animations per costume | **not done**: the executable side is mapped, not built ("v2: female animations") |
| framework | `low-models` builds Ultimate's LOD, new `camera` step, `--slot-moves`; port_check M10 / R1 / S11 |
| exe | **exe_v46r** = exe_v46q + his 5 new motion slots |
| port_check | `port_check master byleth_v1.zip byleth_v2.zip`: 0 ERROR, 22 WARN (v1's B1 / E3 / E7 / M5 + R1: the win cameras aren't shipped) |
| translator fixes (all ports) | Ultimate's endless `loop {}` scripts were dropped whole: now translated (his run / walk dust, dizzy / swim / ladder sounds now play as Ultimate's), random sound containers -> their first tone (forward throw's frame-11 swing) |

### v2: the rapid jab and the angled forward smashes

ZSS's motion table has no animation in the common slots 0x53 - 0x55 (rapid jab start / loop / end) and 0x5E / 0x61
(forward smash up / down), so v1 had no rapid jab and one forward smash. Now:
- **slots**: `tools/extra_kinds.json` "motions" 0x53 `FitSZerosuitBodyMainC00Attack100Start` (flags 0), 0x54
  `...C00Attack100` (0x2: Ultimate's loop flag), 0x55 `...C00Attack100End` (0), 0x5E `...C03AttackS4Hi` / 0x61
  `...C03AttackS4Lw` (0x4, the move flag: Ultimate's motion_list 0x84); `port.json` motions.add; Ultimate's
  `c00attack100start` / `c00attack100` / `c00attackend` (attack_100_end) / `c03attacks4hi` / `lw` in main.pac (322
  motions); the held Areadbhar shows in the angled smashes as in the straight one (`weapon_vis.json` had them).
- **scripts** (`ultimate_acmd.py --slot-moves`, passed by `ultimate_port.py` from motions.add): Ultimate's game /
  effect / sound / expression scripts. The loop is Ultimate's: hits at 2 / 5 / 8 / 11 / 14 / 17 of an 18-frame loop
  (0.4 %, angle 361 (Ultimate's: not 367), 6.0 hitboxes at 9 / 18 forward, +3 hitstun frames), the continue check
  (`100_CONTINUE_CHECK` -> 0x21000016) after each, `WAIT_LOOP_CLR` + `JUMP(attack100)` (vanilla Kirby's form);
  the finisher 3.5 % at 54 degrees, 162 / 60, on frame 6 (cancel 51); jab 2 turns ENABLE_100 (0x21000011) on 6 - 10
  and jab 1 ENABLE_RESTART (0x2100000E) at 16 (both dropped before: the translator didn't know them). The angled
  smashes: Ultimate's hits (13 / 19.5 % up, 11.5 / 17.25 % down: the tipper on Sword1), charge flag at 14, cancel 66.
  Effects `master_atk_100` / `_finish` (in the bank since v1) with Ultimate's calls; the foot smoke loop unrolled;
  the rapid jab's sound `se_master_attack100` (a random container) -> its first tone `_01`.
- **MSC**: none needed: ZSS's MSC holds the common statuses. The jab (0x25) goes to Attack100 (0x26) when ENABLE_100
  is on and A is mashed (the mash count against the common param) or held after a hit at the last jab; the loop
  (`func_337` / `func_338`) continues while A is pressed or held at each check, then plays 0x55; the forward smash
  status picks 0x5E / 0x61 from the stick's angle once the motions exist (`MotionModule(0xc, k)`). Ultimate's rapid
  jab has the same structure (ENABLE_100 on jab 2, the continue check per hit, the finisher).
- **vl**: group 1 bytes from Ultimate's motion_list: 0x53 / 0x54 cancel 0 (byte 0 = 0 on the loop), 0x55 cancel 51,
  0x5E / 0x61 cancel 66.
- Not done: Ultimate's `ATK_SET_SHIELD_SETOFF_MUL` (x9 shield push on the loop hits: no Smash 4 hitbox field), the
  whip sword's model (the loop shows the hilt only, as v1's up smash).

### v2: low models (`model/body/l00`-`l07`)

v1's were copies of c00-c07. Ultimate has its own low model in every costume (`model/body/cNN/lod.xmb`: c00 / c02 /
c04 / c06 `body_low` (7701 triangles) for `body_high` (11641); the female costumes also `hair_low`, `coatG_low`,
`skirtG_low`). `ultimate_port.py run master low-models` now builds them (`ultimate_fighter.py model --lod-low`): the
same 34 mesh slots, skeleton (model.vbn / jtb byte-identical to cNN's), `model.nut` and face / eyelid packs as cNN
(the low build's textures named by cNN's ids: every picture is in cNN's .nut), model.nud ~7 % (male) / ~10 %
(female) smaller. The magnifier and 8-player Smash load lNN (Squirtle v6: no lNN = invisible there).

### v2: win cameras (superseded: "v3: win cameras")

Ultimate: `camera/fighter/master/c00/j02win1-3.nuanmb` (camera-SSBU.zip; c01's differ for the female poses): one
`gya_camera` node animated 131 / 171 / 181 frames, field of view 0.28 - 0.68 rad. Converted (`tools/ultimate_camera.py`,
the pipeline's `camera` step) into Smash 4 camera motions in Corrin's final-camera form: `fighter/master/camera/
result/win1-3/camera_motion.omo` (+ `.vbn`, `camera.json` with the field of view), round trip within 0.0002.
**Not shown in game, not shipped**: Smash 4's result screen plays no camera motion. What is known:
- vanilla fighters have no result camera files (their `camera/` folders are Final Smash cameras only, `camera/final/N`:
  eye + aim locators (Captain Falcon) or one `gya_camera` (Corrin));
- the result framing is in `param/ui/result_param.bin`: a 61-record group (a `default` record, then the 58 vanilla
  fighters + 2 in the per-win table's order; names stored as type-0x0A encoded strings) whose fields the executable
  binds by name (`0x030D37C4`: `name`, `win1`-`win5`, `eyex/y/z`, `tox/y/z`, `team_motion*`, `mvp_motion*`,
  `mvp_camera_x/y/z`, `rot`, `x_rot`, `offset_x/y/z`), and a 153-row table (name, win 1-3, two floats; plain
  names) whose two floats don't follow Ultimate's framing (correlation < 0.25 over all 153 rows with every vanilla
  fighter's Ultimate camera: they are not a zoom / height of the camera);
- the names reach the result logic through script bindings (`0x030ED508` / `0x030ED5C0` return a kind's lower / cap
  name to a script VM), so the record lookup is in a script, not found yet.
Next step: find where the result scene sets its camera (eye / to) per frame and hook it to play
`camera/result/winN` for a kind that has them (kind_expand's name, the win number), as the Final Smash camera player
does (`fighter/%s/camera/final/` 0x10158C08). port_check R1 warns until then.

### v2: female animations (costumes c01 / c03 / c05 / c07; built in v3)

Not built in v2: the executable change needs every per-costume resource site, and none of it can be tested offline.
What vanilla does for Bayonetta (0x38), her Bayonetta 2 costumes (4 - 7 but 2) using `body2` / `bodyentry2` /
`bodyresult2`, is the model to copy (10 sites, every one a `cmpwi rK, 0x38` with the costume test):
- path builder `0x030BAE08` (types 0 body, 1 entry, 2 result, 3 routemap: `0x030BAE90`, `0x030BAF54`, `0x030BB028`,
  `0x030BB0F8`), reached from `0x030BB18C` for kind 0x38;
- entry / result packs: separate resource ids per costume group in the kind x 9 space (`0x1F9` = 0x38 x 9 + 1,
  `0x1FA` = + 2): load `0x030C199C` (entry), `0x030C1BE0` / `0x030C1C30` (result), unload `0x030C1ADC`, `0x030C1E90`,
  getter `0x030C20C4` (+2 for the second group, +5 / +6 alike);
- the in-battle body pack (kind x 0x11 + 0 / + 1): the fighter's construction `0x02E130E4` takes +1 when the
  player's record byte `+0x23` is 1 (mode 3), else +0: where that byte is set (the costume group) is the open
  piece; the registration side of +0 / +1 not found yet.
So two Bayonettas of both groups already coexist in one match for entry / result packs; for 0x47 the same stubs
(kind 0x47 and costume & 1 -> the second group, folder `bodyf` ...), then `ultimate_fighter.py motions` from
Ultimate's `motion/body/c01` into `motion/bodyf/` (+ entry / result), the face pacs per costume, the effect scripts'
costume-parity branches (v1 takes the male branch), and the female's win cameras (camera c01). Memory: one more
main.pac (10.4 MB for 322 motions) only while a female Byleth is in the match.

## Status: v1 (`scratchpad/byleth_v1.zip`: playable, first in-game test)

v1 is the first package: his model, animations, normals, grabs, throws and specials, his sounds, his effects (the Final
Smash's kept out), his held weapons, sword trails, arrows, the ZSS leftovers audit, and executable **exe_v46q**. Not in
v1 (next steps, "Handover" below): the female costumes' own animations (they play the male's), Kirby's Failnaught copy,
Aymr's KO zoom, the whip-sword models (the tether and the whip moves show the hilt only), the effect-colour check of
every move (done for the specials only).

| part | state |
|---|---|
| specials | `fighters/master/master.c` (his statuses at its end), `specials_acmd.json`, `tools/master_build.py` (the plan's `specials` step) |
| exe | **exe_v46q** = exe_v46p + his 9 motion slots + his weapon kinds 0x19E / 0x19F / 0x1A0 (`tools/weapon_expand_append.py`) + trail ids 270 / 271 |
| held weapons | Areadbhar / Aymr / Failnaught: Ultimate's article meshes rigid on his hands, in three of ZSS's mouth slots, shown by the moves that hold them (`weapon_vis.json`) |
| effects | 78 sets of his own + ZSS's, the Final Smash's 13 kept out (`port.json` `effects.kept_out`: port_check E5) |
| port_check | 0 ERROR over v1 as installed (WARNs below) |

## v1: his specials (`fighters/master/master.c`, `tools/master_build.py`)

Ultimate's order (user): neutral Failnaught, side Areadbhar, up Sword of the Creator, down Aymr. Every value from
Ultimate's `vl.prc` (`param_special_*`, ParamLabels' names) or his scripts' frames (`master_build.py CONSTS`: each
one's source is beside it); "mine" marks the few with no Ultimate value.

| status | move | motions (slot) | what |
|---|---|---|---|
| 0x152 | Failnaught | SpecialNStart 0x211 / air 0x21D, SpecialNTurn 0x212 / 0x21E, SpecialNCancel 0x229 / 0x22A, SpecialN 0x215 / 0x221, SpecialNMax 0x219 / 0x225 | the draw charges the whole motion (119 frames); let go once CAN_SHOOT (45; earlier: it fires at 45) -> the arrow (article 6); the draw's end -> the max arrow (article 7); stick back during ENABLE_TURN (28 - 44; threshold 0.5, mine) -> the turn, once; shield during cancel_start - cancel_end (20 - 65) -> the cancel |
| 0x153 | Areadbhar | SpecialSStart 0x22D / 0x231, SpecialSF 0x22E / 0x232, SpecialSLanding 0x22F | the lunge 3.0 (air x0.6) from its frame 2, braking 0.34 (air 0.22) a frame, from frame 14 0.07 (air 0.008); an air lunge landing: x0.9, braking 0.03 |
| 0x154 | Sword of the Creator (ground) | SpecialHi 0x239 | Ultimate's hits (the pull to the point above him: angle 368 -> 366) |
| 0xF1 | Sword of the Creator (air) | AirCatch 0x091 = his SpecialAirHi | ZSS's tether status (user): her whip (article 2, his hidden copy 0x1A0) goes out at the sword's frame 17, back at 27; a ledge in reach -> her native 0xF5 / 0xF3 / 0xF4 (his AirCatchHit / Hang animations); start speed up 1.4 |
| 0x15B | its hit | SpecialAirHiHit 0x23A, SpecialAirHiOvertake 0x23B | a hit on frames 16 - 25: pulled toward the sword's tip (1.15 / 2.85 a frame for 14 frames: Ultimate's target point 16 / 40, mine), then the overtake's hit (Ultimate's CATCH numbers 6.5, 114 degrees, 65 / 65 as a hitbox: nothing is caught), special fall |
| 0x15C | its wall jump | SpecialAirHiWallJump 0x23C | a wall touched while the sword is out (16 - 27), up to 3 a time in the air (wall_hit_max): 0.9 off it, 2.6 up |
| 0x155 | Aymr | SpecialLw 0x241 / 0x245, SpecialLwLanding1 0x255, SpecialLwLanding2 0x259 | super armor below 30 % damage (DamageModule 0xB type 3; super_armor_damage_max) from frame 34 to 64; the axe's hitbox (Ultimate's `master_axe` 30 %, on his haver) merged into his script; landing before 51 or within 65 - 117 goes on as the ground one at its frame, 51 - 65 SpecialLwLanding2, after 117 SpecialLwLanding1 |
| 0x156 / 0x161 / 0x162 | ZSS's Final Smash (Gunship) | her slots and scripts | kept (user); her final scripts restored by `master_build.py` (port.json `base_scripts_kept`) |

**Position-setting hits** (Ultimate's `set_vec_target_pos`, `tools/vec_target.py`, port.json `vec_target`, port_check
S10): the up smash (frames 13 / 14, (3, 27) over 8 frames) and the ground Sword of the Creator (frame 16 (18, 44) over 7,
17 / 19 (16, 40) / (16, 41) over 4 / 2) pull the fighters they hit to the point in MSC (`master_vt_attackhi4` /
`master_vt_specialhi`, generated, called from the per-frame hook; VAR_14 0x0F00030E); the air one is his status 0x15B's
pull. Not tested in game.

**The arrows** (Failnaught): his copies of ZSS's Paralyzer shot (`paralyzer_bullet`: native, straight, removed on a
hit), brand-new articles `arrow1` (6) / `arrow2` (7), files in `fighter/master/script/animcmd/weapon/arrow1|2`. Every
one of the shot's eight motions plays Ultimate's `master_arrow1` Fly (12 %, 35 degrees) / `master_arrow2` Search (29 %,
361, piercing not done) with their effects. Speed / life in his vl (the shot's block, both copies read it): uncharged
9 / 17 frames (Ultimate's `param_arrow1`), charged 10 / 30 (the max arrow's distance 300 at speed 10, mine; if the
native shot fires the max arrow uncharged it flies 153 units). Approximated: the arrow's damage doesn't grow with the
charge (Ultimate's status code scales it), no arrow model (the effect draws it), its spawn point is the shot's.

**Not done in v1**: Failnaught's air jump cancel (SpecialAirNJumpCancel), Aymr's turn (SpecialLwTurn) and SpecialLwHit
(the axe stuck in the ground), the air physics multipliers of the specials' starts (start_speed_*_mul_air: ZSS's
kinetic types 0x6 / 0xA as hers), Sword of the Creator's SpecialHiFailure / wall failure, the KO zoom (Aymr's
critical_zoom in 1-on-1: needs a native KO test, Smash 4 zooms only on a match's last KO).

## v1: ZSS leftovers ("ZSS's statuses / leftovers must not override Byleth's")

Audit (all fixed in v1; port_check B1 / C1 / V1 pass):
- **Status table** (`master.c` func_2245 - func_2248): only his functions for his statuses. Gone: her 0x157 - 0x15A
  (Paralyzer shot / charged / landing), 0x15D - 0x15F (Flip Jump's flip / kick landing), her LandingHeavy pre (0x16: to
  0x19 after a Flip Jump), her CatchPull / CatchDashPull mains (0x36 / 0x38: her whip's pull) and her ends of 0x2D /
  0x33 / 0x34 / 0x39 (removing her whip after the smashes, aerials, pivot grab): the common ones again. Kept on purpose:
  her tether 0xF2 - 0xF5 (the base the user chose for Sword of the Creator), her Final Smash 0x156 / 0x161 / 0x162.
- **Transitions into her specials**: her zair (func_61 / func_378: air grab -> 0xF1) off (`master_zair()`); her
  Flip Jump once-per-air hook (global35 = func_2242: down special off in the air) replaced by his (the wall jump
  count); her own special mains (which made her whip, Paralyzer, Boost Kick) are no longer registered; the plain grab:
  his Ultimate Catch scripts (no GENERATE_ARTICLE), the common CatchPull.
- **vl motion bytes** (group 1, `master_build.py vl_fix`): ZSS's Flip Jump intangible window 3 - 13 (2 - 7) on all
  eight of 0x241 - 0x248 (his Aymr slots: Supamario Core Breaker v11's bug class), her Boost Kick's byte 5 (0x239 -
  0x240), her Paralyzer / whip / Flip Jump cancel frames on the custom-move slots (0x216 - 0x258): 42 bytes; every slot
  he plays has Ultimate's cancel / window, every other fighter-specific slot 0. New check **port_check V1
  vl-leftovers** (ERROR): bytes 3 - 5 of every own slot (0x211 on) the port plays = Ultimate's window, bytes 2 - 5 of one
  it doesn't = 0.
- **Scripts**: 116 of her scripts left in special slots he doesn't play (her custom moves, her Boost Kick's air copy,
  ...) emptied (`body_fix`), her SpecialLwLanding (Reverse_Direction) in his Landing1 slot (Ultimate's has no game
  script). B1: 0 game, 0 effect / sound / expression besides her kept Final Smash.
- **Per-kind native code on 0x47**: her tether vector (x152C, exe_v46p `tail_vector`); her whip's kind compare in her
  specializer (0x02F81010, `cmplwi r3, 0x38`: the whip) also takes his copy 0x1A0 (weapon_expand_append's kind compare
  stub); her article list kept in order (0 paralyzer, 1 shot, 2 whip, 3 cockpit, 4 gunship, 5 laser: her Final Smash's
  ids), his arrows after it. Has Tether stays 1 (fighter_param 0x1300011F): her native whip needs it; zair is off in his
  MSC. Not checked yet: her native per-kind code in the Paralyzer / Gunship paths (only her Final Smash reaches them).
- **Model**: her Paralyzer slot (her code shows it) empty; her face skin slot (her eyelid pac keys it) empty (F1).

## Executable: exe_v46r (v2)

exe_v46r (`scratchpad/byleth/exe/exe_v46r.rpx`, sha1 59025fa1a0931ed4cf4b2b6250fd60ef33b4a570) = exe_v46q + his 5
motion-table entries (0x53 / 0x54 / 0x55 / 0x5E / 0x61: 8 words in his table at 0x04BA8738, `extra_kinds.json` "motions"):
```
python3 tools/kind_expand_incremental.py build EXE_V46Q KINDS_V46Q.json tools/extra_kinds.json KE_ARGS --list 0x47=0x04B9C728
    (KINDS_V46Q.json: extra_kinds.json as committed for v1; drop 0x04BA9B24 / 0x04BA9BE4, kirby_copy_pool_cave.py's hooks:
     the cases didn't move, its hooks stay)
python3 tools/rpx_patch.py EXE_V46Q EXE_V46R $(cat KE_ARGS)
```
Tests (exe_v46p as the original, as for exe_v46q): the same results as exe_v46q's: kind_expand_test 21 (the
original's expanded layout), weapon_expand_append test 3 (by design), sound_alias_cave_test 6, acmd_ext_test 18,
kirby_copy_new_test 123, kirby_copy_pool_test 151 (with stage_q as the original), position_vars_test 0,
vec_target_test 0.

## Executable: exe_v46q

exe_v46q (`scratchpad/byleth/exe/exe_v46q.rpx`, sha1 39d77b31cbe821ffc4dbd8ad9b2270158d3f673a) = exe_v46p (the kind, tether vector, sound aliases) +:
- **his motion slots** (`extra_kinds.json` "motions": 9 of ZSS's custom-move slots get his extra phases' animations,
  FitSZerosuitBodyMainD00SpecialNTurn ...): `kind_expand_incremental.py build EXE_V46P OLD NEW ARGS --list
  0x47=0x04B9C728` (15 motion-table words + his descriptor's +8; its two kirby_copy_pool hooks left as they are);
- **his weapon kinds** (`extra_kinds.json` "weapons": arrow1 0x19E / arrow2 0x19F (brand-new, copies of her Paralyzer
  shot), whip 0x1A0 (her whip, his own files)): new tool **`tools/weapon_expand_append.py`**: weapon_expand.py's cave
  is full (exe_v46p: 0x04BB7EB8 of 0x04BB8000) and can't be rebuilt from an un-grown base (none kept), and a new
  fighter's article list at its start would move every word other caves call into; so the new kinds go into what's there:
  their entries in the 7 per-kind tables (found by their first 0x185 entries), descriptor copies, cases and getter copies,
  the base-kinds table, the whip's kind-compare stub, his article list (8 entries) and kind_expand's descriptor +8, all
  in 0x04B9C000-0x04B9C7B0 (trail_table_cave.py's space past its GROW, below 0x04BD4000). 516 words;
- **trail ids** 270 / 271 (`trail_table_cave.py` NEW_TRAILS TexMasterSwordTrace / Add; his trails on trail shader 3 as
  Sephiroth's).

```
python3 tools/weapon_expand_append.py EXE_V46P KINDS_V46P.json tools/extra_kinds.json WE_ARGS
python3 tools/kind_expand_incremental.py build EXE_V46P KINDS_V46P.json tools/extra_kinds.json KE_ARGS --list 0x47=0x04B9C728
    (drop 0x04BA9B24 / 0x04BA9BE4 from KE_ARGS: kirby_copy_pool_cave.py's hooks)
python3 tools/trail_table_cave.py EXE_V46P > TRAIL_ARGS
python3 tools/rpx_patch.py EXE_V46P EXE_V46Q $(cat WE_ARGS KE_ARGS) $(cat TRAIL_ARGS)
```
KINDS_V46P.json: extra_kinds.json without his "motions" / "weapons". Tests (exe_v46p as the original): `weapon_expand_append.py
test` (weapon_expand_test.py over every weapon kind 0-0x1C0: switches, descriptors, getters reading his vl slot,
accessors, path builders `fighter/master/.../arrow1`, module rows, article lists, kind compares): 321 ok, 3 fail by design
(the motion-info copies' "inside 0x04BB0000-0x04BB8000" check); kind_expand_test (incremental): his new checks ok, the
+8 check expects weapon_expand's own layout (by design); sound_alias / acmd_ext / kirby_copy_new / kirby_hero_sword /
kirby_copy_pool: the same failures as exe_v46p over exe_v46n (the originals already have the caves); position_vars_test 0
failed.

## v1: weapons, trails, effects, package

- **Held weapons**: Ultimate's `spear` (6 meshes), `axe`, `bow` article models (c00-c07 their own costume folders)
  rigid on HaveR / HaveR / HaveL (`ultimate_fighter.py` SZEROSUIT_SLOTS: ZSS's Mouth_Escape / Mouth_HeavyOuch /
  Moutn_Furafura slots; their mouths go to VoiceA / Ouch / Down: MASTER_MOUTHS), shown by `material_anime_face.pac`
  from the frames his scripts generate / remove them (`master_build.py vis` -> `weapon_vis.json`, port.json
  `motions.extra_vis` -> `ultimate_fighter.py motions --extra-vis`: 33 motions). Approximated: rigid (the bow's string
  doesn't draw, the axe's blades don't open), the whip sword (`sword`, 58 bones) not shown: the rapid jab, up smash,
  down tilt, up air, throws and the tether show the Sword of the Creator's hilt only (Ultimate hides it and shows the
  article: its track is followed, so the hilt is hidden where Ultimate hides it).
- **Sword trails**: `tex_master_sword1` / `2` -> `effect/master/trail/TexMasterSwordTrace(Add).nut`
  (`ultimate_trails.py --shader 3`, run by `master_build.py`), ids 270 / 271 in `master_effects.json`; trail shader 3
  as Sephiroth's (needs its `effect_trail.nsh`, already installed with Sephiroth).
- **Effects**: 78 of his + 26 of Ultimate's common sets (104 ids), his Final Smash's 13 kept out (`port.json`
  `effects.kept_out`; their stale ids dropped from `master_effects.json`).
- **Effect colours, every move** (`fx_render.py` over the taunts, jabs, tilts, smashes, aerials and landings, dash
  attack, pummel, throws, ledge / get-up / trip attacks, wins and the specials, every 3rd frame to 90; an automatic
  pass (`scratchpad/byleth/bin/fxcmp.py`: each frame's effect pixels, Ultimate's column against ours, mean colour and
  coverage) and the flagged frames looked at). Fixed (v1b):
  - **the magenta line over Areadbhar's and Aymr's slashes**: their lightning meshes (`master_spear_slash` /
    `master_axe_slash` lightning1-3, lightning2_bk and 18 more emitters of 11 sets) have a fresnel alpha whose mean over
    the mesh from the side is 0 (Ultimate draws them edge-on: nothing); through the universal path the lowered program's
    view-angle term came out whole. `vfxb_to_ptcl.py`: such an emitter (fresnel mean x 0.00) takes the converted shader,
    which keeps it at 0;
  - **taunt / win effects missing**: the translator only gave a slot an effect script when the base's effect file had
    one (ZSS has none on her taunts); now also when the motion table names it (`translate_effects(motions=)`, as sound).
    And Ultimate's costume-parity branches (`FIGHTER_INSTANCE_WORK_ID_INT_COLOR % 2`: male / female timings, the up taunt's
    and Win3's flashes and smoke) were both dropped: the male branch is taken (every costume plays the male animations);
  - `fx_render.py`: the port's translate map for a move's Smash 4 script, a sampler that isn't the emitter's skipped, an
    emitter with no particle alive skipped (it crashed).

  Left (Handover 6): the forward / back air's Areadbhar flame (`master_spearflare` spearflare3_fresnel, fresnel 0.90 -
  0.00) draws as a rim on our side where fx_render's Ultimate column draws the whole mesh at its mean (0.69): our
  per-pixel rim may well be Ultimate's own look (check against footage); up air's arcs (`master_atk_air_hi_l / _r`)
  show more yellow and fewer red sheets (their XZ meshes turned about Y and Z: "eft's order differs (approximate)");
  `sys_smash_flash_s` (Ultimate's common set, the side taunt's sword flash) violet where Ultimate's core is white; Aymr's
  hold aura a little darker. Call-count differences in the comparison are the facing branches (Ultimate's column draws
  both) and Failnaught's smoke loop (ours unrolled), not missing effects. **Missing moves**: the rapid jab (Attack100 /
  End: ZSS's motion table has no rapid-jab slots, neither did v1's) and the angled forward smashes (AttackS4Hi / Lw)
  need slots of their own (extra_kinds.json "motions" on the common slots 0x53-0x55 / 0x5E / 0x61, motions.add,
  exe_v46q's kind_expand words): Handover 5.
- **Package** `scratchpad/byleth_v1.zip` (`scratchpad/byleth/make_pkg.sh`): the build (`ultimate_port.py run master
  effects model-c00 .. c07 motions low-models scripts specials variants shapes portraits --out $B/port`), the kind
  folder's AI / Kirby-copy bank / FinMaster, his sound banks, exe_v46q, the install README; `not_for_install/` the
  files made on vanilla stand-ins (soundlabeltable, commonsoundtable / bgm_fighter from `fighter_extras.py common` /
  `fanfare --set 0x47=0x12`, fighter_param with his stats, the ui / ai param databases, melee.msbt). Sm4shCommand rebuilt with his script names: `scratchpad/sm4shcommand_v1.7.1_byleth.zip`.

`port_check master scratchpad/byleth_v1.zip` (v1b: the colour fixes, the position-setting hits): 0 ERROR (21 WARN; S10 INFO). WARN: B1 effect / sound / expression (her common dust, common tones, slopes and
damage rumbles on common motions Ultimate's scripts have nothing for; her own tones taken out of 16 of them), E3
(one Smash 4 common effect), E7 (FLASH / BURN_COLOR macros), M5 (two empty ZSS slots).

## Handover: next steps (in order)

0. **v3** (sent: `scratchpad/byleth_v3.zip`, `scratchpad/byleth/INSTALL_README_v3.txt`): the user's in-game test of the
   female animations (a male and female Byleth in one match, entry / result poses) and the win cameras (do they
   move as Ultimate's; the vanilla `data/motion/camera/result/<fighter>/<n>/` file names from the user's dump). If the
   cameras show nothing / wrong: fix the format from the vanilla files (`ultimate_camera.py camera_omo`: node form,
   units, maybe a field-of-view track), keep the path. If the female motions fail: a diag build logging
   0x030BB18C's paths per player (tools/diag_sound_cave.py's OSReport veneer pattern). Then: her win cameras (needs a
   costume in the result scene's camera path: the scene's `winner_color` / a name variant; not found), v2's list below.
   (v2's list: done in v3; its "+0x23" piece turned out to be the model pack, "v3: female animations (the executable
   side)".)
1. **In-game test of v1** (the tether ledge grab for kind 0x47, the arrows' spawn / speed, Aymr's armor, the Final
   Smash).
2. **Female animations per costume** (user: approved executable change). Found so far: the motion path builder
   `0x030BB18C(r3, buf, kind, type, costume)` (type 0 body, 1 entry, 2 result, 3 routemap) already sends Bayonetta
   (0x38) to `0x030BAE08`, which takes another sub-folder (`0x101587A4`, "body2"-style) for costumes >= 4 but 2: the
   hook point for 0x47's odd costumes (a cave: kind 0x47 and costume & 1 -> `bodyf`, `bodyentryf`, ...). Open: the
   fighter loader (`0x030C0880`-`0x030C09D0`) registers the packs under `kind * 0x11 + n` without the costume, so a
   male and a female Byleth in one match would share one pack: find how two Bayonettas of both sets coexist (the
   resource ids), and give 0x47 the same. Then `ultimate_fighter.py motions` from Ultimate's `motion/body/c01` into
   `motion/bodyf/` (+ entry / result), the face pacs per costume.
3. **Kirby's Failnaught copy** (decision 7): `kirby-ssbu-partial.zip` (Drive id 10D7B1Za9lW7cFEtkopIfapMF-em5yIoY) ->
   `kirby/model/copy_master_cap`, `kirby/motion/masterbody`; `kirby_copy_new_cave.py` MAP 0x47 (as Hero / Sephiroth:
   Robin's copy 0x2C, marker 4) + his arrow 0x19E as the copy's article; `kirby.c` (the marker's Failnaught: the Robin
   copy's N slots); `kirby_copy_hats.py`, `kirby_copy_motions.py`, `kirby_copy_sound.py` (vc_kirby_copy_master).
4. **Aymr's KO zoom** (decision 8): a native hook on the finish camera (Smash 4 zooms on a match's last KO only).
5. ~~The rapid jab and the angled forward smashes~~ (v2). The whip sword's segments (the rapid jab, up smash, down tilt, up air, throws, the tether: a model on her whip
   chain, 8 segments), Failnaught's damage by charge and the max arrow's piercing, SpecialAirNJumpCancel,
   SpecialLwTurn / SpecialLwHit, the item swings retimed (BatSwing4 kept as hers: `base_scripts_kept`).
6. The normals' effect colours (fx_render over every move), then the user's own files (below).

## Phase 1 (inputs, slot, plan)

Nothing has been packaged or sent: the port isn't playable yet (ZSS's moves under his animations, no scripts, no
specials) and `port_check` has an ERROR (E5, the Final Smash ripple: "Effects"). Done so far:

| part | state |
|---|---|
| inputs | downloaded / extracted (Sources); `port_sources.json` (repository root, not committed) points at them |
| `init` / `plan` | `port.json` written (8 costumes, joint `Sword1` to table 1, 91 own effects, 28 common); the plan's missing inputs are the user's current install files (Open questions 1) |
| kind / slot | `tools/extra_kinds.json` record 0x47 / id 65; executable **exe_v46o** (below); the kind folder (`add_fighter.py --only master --folder`, from vanilla ZSS) |
| Kirby | `kirby_copy_trait()`: 0x47 -> `trait_strike()`; `kirby.mscsb` rebuilt (globals 118 of 128, 0 stack problems, roll-off as Hero's) |
| body | ZSS's universal-mechanics body rebuilt from vanilla (roll-off ACMD 2.2, `universal_mechanics.py` on her decompiled MSC: 0 stack problems, `rolloff_hold_test` as Hero's) |
| stats | `ultimate_stats.py` on Ultimate's fighter_param.prc (below), on a vanilla-based fighter_param (the real one is the user's current file) |
| model | c00-c07 converted (`ultimate_fighter.py` profile `szerosuit` / `szerosuit_nomark`, new): 132 bones (male) / 130 (female) |
| motions | `main.pac` (body 308, entry 2, result 7, route map 4) + face / eyelid pacs; low models l00-l07 |
| effects | his bank: 117 sets (91 of his own, 26 of Ultimate's common ones; `sys_screw` has no set: stays Smash 4's) after ZSS's, ids in `fighters/master/master_effects.json` (below) |
| Shadow Flare row | `fighters/edge/weapons/flare1.c`: 0x47's orbit row (`edge_flare_targets.py --vbn master=...`, his converted model.vbn); `flare1.mscsb` rebuilt (ships with the next Sephiroth package) |
| not started | sound, scripts (ACMD translation), specials (MSC / articles), variants, shapes, portraits, AI, Final Smash |

`port_check master` on the phase-1 build: E7 effect-macros (`EFFECT_FLW_UNSYNC_VIS` x4 in his side special's dash,
`EFFECT_GLOBAL` x3 in the Final Smash screens) is fixed in `tools/ultimate_acmd.py`: Smash 4 has both commands under
those names (`EFFECT_FLW_UNSYNC_VIS` names its id field `Effect`, which same_name_syntax now takes; `EFFECT_GLOBAL` has
no bone and Ultimate's trailing bool is dropped). M5 warnings (two empty ZSS mesh slots keep her texture ids
0x40280015 / 16: harmless). The effect checks (E4 / E5 / E9) are in "Effects" below.

## Sources (all Ultimate data from the user's Drive)

| what | file (Drive) | used |
|---|---|---|
| model, motions, `vl.prc`, `expression_vl.prc`, AI, article models / motions | `SSBU Characters(10_27_26)/master.zip` (whole) | model c00-c07, motion body c00 (male) / c01 (female), vl.prc (specials, articles), motion_list (cancel frames, later) |
| ACMD (game / effect / sound / expression) | GitHub `WuBoytH/SSBU-Dumped-Scripts` `smashline/master` (8 folders: `master`, `master_arrow1`, `_arrow2`, `_axe`, `_bow`, `_sword`, `_sword2`, `_swordflare`) | init's effects / joints; the scripts step |
| status code (recomp) | `lua2cpp_decomp.zip`: `gen_nro_eh_o2/lua2cpp_master/` only (63 files) | specials' behaviour (not read yet) |
| `fighter/common/param` | `fighter-common-SSBU.zip` (`common/param/*.prc`) | stats, effect tints |
| effects | `effect-fighter-SSBU.zip` (`fighter/master/`: `ef_master.eff`, trail textures), `effect-system-SSBU.zip` (`system/common/ef_common.eff`) | his bank, the sys_* sets |
| sound | `sound-full-ssbu.zip` (the master files only: `se_master*`, `vc_master*`, `vc_master_cheer*`, `vc_kirby_copy_master`, `vc_narration_characall_master`). **The `sound-ssbu.zip` link has only stage banks and the config**: Byleth's banks aren't in it | sound step (not run) |
| UI | the UI SSBU link: `ui/replace/chara/chara_*/chara_*_{master,szerosuit}_*` (101 files), `ui/message/msg_name.msbt` (his name: "Byleth", sound names "Byleth (Male)" / "(Female)") | portraits (not run) |
| ExeFS | `exefs-SSBU.zip` (`exefs/main`: an LZ4-compressed NSO; decompressed to a flat `main.bin` (text 0, rodata 0x39C8000, data 0x4F16000) for `eft2_resolve.py`: with the NSO itself all 665 universal-shader emitters failed to lower) | the effect converter's eft2 pass; behaviour the data doesn't hold (later) |
| ParamLabels.csv | GitHub `ultimate-research/param-labels` | names of vl.prc / fighter_param.prc values |
| OpenSmash-Ultimate | GitHub `OpenSmash-Ultimate/ssbu-recomp` (sparse: `runtime/`) | the effect converter's shader translator |
| vanilla Smash 4 | `fighter-smash4-vanilla.zip` (`fighter/szerosuit/`, every fighter's `effect/*/*.ptcl/.efc` (templates) and `model/body/c00/model.vbn`, Cloud's model.sb / Kirby's model.nhb (empty)), `param-smash4-vanilla.zip` (whole), `ui - unmodified.zip` (melee.msbt, ZSS's portraits, every chrn_ name plate) | base files, templates |

Executable: the user's B `exe_v46n` (`time_stage_commands_v1.zip`).

## Executable: exe_v46o (kind 0x47 only; exe_v46p, exe_v46q above)

exe_v46o = exe_v46n + the new kind (built, not shipped: it goes with the first playable package). The kind caves are
generated for an un-grown base, so they were run **incrementally** on exe_v46n: each generator's reads of exe_v46n see
the words it hooked as the originals it states (the switch bounds, kind_expand_ram.json's sites, its stated originals,
base_effects / base_customs' hook sites). Run with the six-kind spec, each generator reproduces exe_v46n exactly
(kind_expand: all 9965 words but the two kirby_copy_pool_cave re-hooked; base_effects 210 / 210; base_customs 52 / 52);
with the seven-kind spec its differing words are the patch:

- `kind_expand.py`: 8604 words (27 in place, 8577 cave; the cave grows 0x04BA97B4 -> 0x04BAAC58, below
  extended_memory's 0x04BAF000; Byleth: descriptor 0x04BA86E8, motion table 0x04BA8738 (607, ZSS's), vl load 0x04BA9F70,
  unload 0x04BA9FF8; every later kind's code moved, so Sephiroth's load / unload cases with it);
- `base_effects_cave.py`: 2 words (count 7, his base byte 0x19); `base_customs_cave.py`: 3 words (count 7, base id 0x1A);
- `kirby_copy_pool_cave.py` re-run on the result: its cave the same, its two hooks on Sephiroth's moved cases
  (0x04BA9B24 / 0x04BA9BE4).
- No other cave refers into kind_expand's region (every branch / pointer / lis-addi pair scanned); `weapon_expand.py`
  (Byleth has no weapons yet) and `sound_alias_cave.py` (no banks of his yet) unchanged.

Tests (exe_v46n as the original, through the same virtual base): `base_effects_test` 0 failed; `kind_expand_test` every
0x47 check ok (switches, descriptor, names, sizes, character id 65 -> 'Byleth', loader, vl load / unload of
ZSS's params, motion table, sound names, save records 59-65), 20 failures all from the original being an expanded exe
(its manager size, its six kinds' loads / names / records) or kirby_copy_pool_cave's own Sephiroth load; `base_customs_test`
1 (the original's id 59 already mapped); `kirby_copy_pool_test` every functional check ok (its "original" failures:
the stage-1 exe already holds its cave). Tool: `tools/kind_expand_incremental.py` (`build` / `test`), which
reproduces these words exactly.

```
python3 tools/kind_expand_incremental.py build EXE_V46N.rpx KINDS_WITHOUT_MASTER.json tools/extra_kinds.json ARGS
python3 tools/rpx_patch.py EXE_V46N.rpx STAGE1.rpx $(cat ARGS)
python3 tools/rpx_patch.py STAGE1.rpx EXE_V46O.rpx $(python3 tools/kirby_copy_pool_cave.py STAGE1.rpx)
python3 tools/kind_expand_incremental.py test kind_expand_test EXE_V46O.rpx EXE_V46N.rpx    (and base_effects_test,
    base_customs_test); python3 tools/kirby_copy_pool_test.py EXE_V46O.rpx STAGE1.rpx
```
exe_v46o sha1 bd818233d2c55b8b16fe7a104bd030fc95dbe587.

exe_v46p added the tether vector and his sound aliases, exe_v46q his motion slots, weapon kinds and trail ids
("Executable: exe_v46q" above). Still to come: the female per-costume motion folders, Kirby's copy grant, the KO zoom
(Handover).

## Phase 2 (exe_v46p, sound, scripts)

- **exe_v46p** (`scratchpad/byleth/exe/exe_v46p.rpx`, sha1 e4fe65797487e5aa7f859cb5c9c0c2107ee3a1c5) = exe_v46n + the
  kind (as exe_v46o) + **his tether set** + **his sound aliases**:
  - `kind_expand.py`: a record's `"tail_vector": true` runs its base's vl-tail block for the new kind in hook A (ZSS's:
    count +0x198 / vector +0x19C of the kind's parsed vl struct -> x152C[kind]; registers r3-r6, written before the
    tail reads them). `kind_expand_test` checks it: `x152C[0x47]` = his own struct's +0x19C (unicorn), the other new
    kinds unchanged (Steve keeps no Pit x1324 vector: off unless asked). Risk 1 is closed for the vl data; his tether
    statuses still need an in-game test.
  - `sound_alias_cave.py`: kind 0x47's aliases (se 2028, vc 6023, cheer 6106) from `reference/port_sound_ids.json`;
    `sound_alias_cave_test`: kind 0x47 ok (4 "unpatched" failures: the original is already aliased for the others).
- **Sound** (`ultimate_sound.py`, on the vanilla soundlabeltable): se 154 + 130 Ultimate tones, voice 44 + 55 (the
  base's game-played voices given his), cheer, 14 sequences; **the female costumes' own banks**
  (`snd_se_Master_c01/03/05/07`, `snd_vc_Master_c01/03/05/07`, Ultimate's `se_ / vc_master_c01`): the game already
  loads `_cNN` banks by costume for a new kind, so the female voice needs no executable change. Own bank ids 46192-
  46215. The female cheer (`vc_master_c01_cheer`) isn't used yet (one cheer bank).
- **Scripts** (`ultimate_acmd.py`): 30 game scripts (normals, grabs, throws, ledge / get-up attacks, the dash) with
  Ultimate's cancel / intangible frames into the vl file, 75 effect, 159 sound, 191 expression scripts. Every normal's
  hitboxes are in his body scripts (on `haver` / `top`): the weapon articles carry none, so the normals hit as
  Ultimate's without the article models. Left out: the sword trails (done in v1), 9 sounds without an id (containers / other fighters' / raw hashes), rumble kinds with no Smash 4 match.

## Re-run on the user's files

Done on the user's own files (2026-11-16: their fighter_param, soundlabeltable, melee.msbt, ui/replace/chr, then their
whole param folder and sound/config): **`scratchpad/byleth_userdata_v2.zip`** (replaces userdata_v1; install after v3;
the v1 / v3 `not_for_install/` stand-ins are no longer needed). port_sources.json: `fighter_param` (theirs + his row),
`soundlabeltable`, `s4_chr`, `templates.master`, `user_param`, `user_sound_config`, `user_ui`. Again on newer files:
```
python3 tools/add_fighter.py --param THEIRS/param --param VANILLA/param --ui THEIRS/ui --kinds tools/extra_kinds.json --only master --out DATA
python3 tools/ultimate_port.py run master sound stats portraits --out OUT
python3 tools/fighter_extras.py common THEIRS/sound/config/commonsoundtable.csb OUT --only master
python3 tools/fighter_extras.py fanfare THEIRS/sound/config/bgm_fighter.fbb OUT --set 0x47=0x12
```
(`fighter_extras.py common` with the exe that has kind_expand's tables (`kind_expand.RPX`, exe_v46s); scripts /
specials / variants again only if `sound_ids.json` changes: on the user's table it didn't, ZSS's rows 27 / 78 are
vanilla there.) Every output was checked: with his entries taken out, each file is the user's byte for byte
(`ui_character_db` id 65, `ui_layout_db` / `ui_skill_db` / `ui_sound_call_voice_db` id 65, the ai / amiibo / Classic /
cheer params kind 0x47, fighter_param kind 0x47 (Ultimate's stats), soundlabeltable rows 27 / 78 grown (lists appended),
commonsoundtable record 0x44 (ZSS's), bgm_fighter entry 0x47 (Marth's), melee.msbt his 4 labels, 47 portraits with ids
0x28010600-0x2801062E). His series is Fire Emblem (11, extra_kinds.json `ui.series`); chr_10 on the user's hexagon art
needs port.json `portraits.set_fits` (their chr_10 is their chr_00's art, not a crop of chr_90).

- `fighter_extras.py common` used to rewrite every extra kind's record from its base: on the user's file it would have
  replaced Squirtle's own KO-voice record (0x43) with Mario's. It now only adds missing records (an existing one is
  kept), `--only` limits it to kinds, `--replace` (with `--only`) rewrites (`tools/fighter_extras_test.py --rpx`).
- Open: his announcer call is ZSS's (0x380017, "Zero Suit Samus") until the user sends
  `sound/se/snd_se_narration_characall.nus3bank` (Sephiroth's / Squirtle's calls are in it, soundlabeltable row 0x38):
  then `fighter_extras.py narration ... --ult-tone master --name Master --id 65`.

## Model and motions

```
python3 tools/ultimate_port.py run master body model-c00 ... model-c07 motions low-models --out OUT
```

- **Profile `szerosuit`** (`tools/ultimate_fighter.py`, `SZEROSUIT_SLOTS`; c06 / c07 `szerosuit_nomark`: ZSS's 6 / 7
  have no back mark, 33 meshes): body, face (c01's `faceShape`), knife, coat / skirt -> `Gamemodel` (ZSS's eyelid pac
  keys her face skin `Face_Main`: port_check F1); hair -> `OMOTE` (sorted, never keyed); eyes -> the ZSS eye slot of the
  same expression (EyeN = his open eyeballs, shown with Openblink; an expression's own eyes ride with its lids); mouths
  -> driven per frame from Ultimate's visibility (`MASTER_MOUTHS`, fallback MouthN); the Sword of the Creator
  (`master_sword`, hidden while a weapon article is out) -> `Mouth_Result` (only results motions key it), driven by
  Ultimate's track. Empty: Face_Main, Eye_VIS, Eye_Result, Paralyzer (her code toggles it), base, Tail, Mark_back1.
  Left out: low meshes, `hair_final`, mouths with no slot (shown as the nearest: `MASTER_MOUTHS`).
- **Skeleton:** 132 bones (male c00/02/04/06) / 130 (female c01/03/05/07) of Ultimate's 147, under the 136 budget;
  `Sword1` -> table 1 (his hitboxes use it: 11); FaceN a bone of its own (ZSS's table 1).
- **Motions:** Ultimate's c00 (male) on every costume (one main.pac per fighter in Smash 4). Male and female share
  the body's bind pose exactly (every standard bone), and their attacks' tracks are identical (forward smash, forward
  air: 0 difference); idles / taunts / wins differ (wait1: up to 0.37 on the right arm). Female-only bones (hair
  S_Hair*, KnifeholderF*, skirt) have no tracks yet (they hold their bind pose). Stand-ins: ZSS's angled forward
  tilts -> his one forward tilt, Wait3 -> Wait2, face-down spot dodge -> face-up; 7 motions on Wait1 (crawls, small /
  big item, the Genesis start, magic pot).
- **Specials' animations** in ZSS's slots for now (`SZEROSUIT_MOTIONS`): Paralyzer -> Failnaught (start, shot, max
  shot), Plasma Whip -> Areadbhar's start, Boost Kick -> Sword of the Creator, Flip Jump -> Aymr; the other phases
  need slots of their own (Plan).

## Effects

`ultimate_port.py run master effects` (`vfxb_to_ptcl.py`): 117 sets after ZSS's own (her articles keep theirs), 664
emitters on Ultimate's own programs (the universal path, lowered with OpenSmash-Ultimate's translator and the flat
main.bin), one kept on a converted shader (texture 0 not decoded); 278 unused shaders and 6.9 MB of unused textures
dropped; the bank file 25.4 MB, ~12.4 MiB of the 44 MiB effect heap (`port_check` E9: a WARN; Sephiroth needed
`effect_heap_patch.py` past ~13.3 MiB). Variants (turned effects on bones) come after the scripts step. Effect colours
(the scripts' `LAST_EFFECT_SET_COLOR` etc., his `common_effect_0` tint) are applied by the scripts / variants steps:
not compared with Ultimate's yet (CLAUDE.md: before any package).

`port_check`: E4 clear; E5 was 1 ERROR (`PtcMasterMasterFinalGround/ripple1_rif`, the Final Smash's ground ripple, a
refraction mesh: eft2 type 6 moving along its emitter's Y, converted as type 4, whose X is then zero): v1 keeps his Final
Smash's 13 effects out of the bank (the Final Smash is ZSS's for now: port.json `effects.kept_out`), E5 clear. E5 looks
at the port's converted sets only (ZSS's vanilla `PtcSzerosuitSmashArc` emitters were flagged: eft art the game draws as
it is). To do with his own Final Smash: convert eft2 type 6 refraction meshes.

## Stats (Ultimate's `fighter_param.prc`, `tools/ultimate_stats.py`)

walk 0.1 / 0.07 / 0.78, ground friction 0.05625 (x0.45), dash 1.8, run 0.13 / 0.02 / 1.43, jump squat 3, jump x 0.8 /
0.8 / 1.0 / 1.0, jumps 26.5 / 14.0 / 28.5 (x1, the default), air 0.043 / 0.01 / 0.89 / 0.008, gravity 0.089, fall 1.6 /
air brake y 0.004 / fast fall 2.56, landing lag n 13 / f 11 / b 13 / hi 14 / lw 28, weight 97, 2 jumps, jab count 3,
rapid jab 1 (264), jump type normal (268). Kept as ZSS's (base): landing frames, scale (Ultimate 1.02), shield radius.
On a vanilla-based fighter_param (the real file: the user's current one, Open questions 1).

## Plan

### What ZSS's base gives, what fights it

Gives: a 3-hit jab and the common moves' slots; her **tether machinery** (her grab is a whip tether, her zair hangs on
ledges: the lasso statuses 0xF3 / 0xF4 are in her MSC); her **Paralyzer charge** (a charged neutral special with a
projectile article: start / hold / shoot / max-shoot slots, air and ground); a whip article with a native chain (8
segments, `PlasmaWhip01H`-`08H`); 16 special statuses (0x152-0x162); her Flip Jump (an air / ground two-phase special).

Fights it: her grab and zair are tethers (Byleth's grab is a plain grab and he has no zair); her Paralyzer stuns; her
Boost Kick / Flip Jump physics; her eyelid pac keys her face skin; her holstered Paralyzer slot; her kind's x152C
vector (Risks 1); her motion table has no rapid jab and no angled forward smash; her articles load from
`fighter/szerosuit/` (a port-own kind for every one we change, W7).

### Moveset (Ultimate's scripts / params; the specials' slots)

Note: in Ultimate **side special is Areadbhar (the lance, `spear`) and down special is Aymr (the axe)** (his scripts:
`SpecialSF` generates the spear, `master_axe` holds the `SpecialLw*` scripts; vl.prc `param_special_s` / `_lw`).

| move | Ultimate | on ZSS |
|---|---|---|
| normals, grabs, throws | 2-hit jab + rapid jab (`Attack100Start` / `Attack100` / `AttackEnd`, the sword whip), one forward tilt, angled forward smash with Areadbhar (`AttackS4Hi` / `S` / `Lw`), up smash / down tilt / up air / throws with the whip sword, down smash / down air with Aymr, forward / back air with Areadbhar, neutral air with Failnaught | translator into her slots; added slots for the rapid jab (3) and f-smash Hi / Lw (2); her grab statuses replaced by a plain grab (no whip), zair off |
| neutral special: Failnaught | `SpecialNStart` -> hold (charge) -> `SpecialN` / `SpecialNMax`; `SpecialNCancel`, `SpecialNTurn`, `SpecialAirNJumpCancel`; arrow1 (`param_arrow1`: speed 9, life 17), max arrow2 (`param_arrow2`: distance 300, piercing); `param_special_n` (offsets, air speeds, cancel 20-65) | her Paralyzer statuses (0x152-...: charge / shoot) with an MSC of his; the arrows as new weapon kinds (a copy of her laser / bullet, or a model-bearing dein copy: W5) with Failnaught's ACMD; the bow a held model (below) |
| side special: Areadbhar | `SpecialSStart` -> `SpecialSF` (the lunge: speed 3.0, brakes), `SpecialSLanding`, air versions; tipper on the lance | her Plasma Whip status, MSC of his (speeds from `param_special_s`); the start + lunge + landing in added slots |
| up special: Sword of the Creator | `SpecialHi` (the sword extends up-forward, 70 max reach): `SpecialHiHit` (latched on a fighter, pulled in; `Overtake` follow-up), `SpecialAirHiWallJump` (a wall: jump off it, 3 max), ledge: the lasso hang (`AirCatchHang` / `AirCatchPose` scripts in his dump), `SpecialHiFailure` | **her tether**: the up special puts him in her lasso / hang statuses (0xF3 / 0xF4: the native ledge reach and hang come free) with the sword-whip model on her whip chain, his own hit / pull / overtake / wall jump in MSC; needs the x152C vector (Risks 1) |
| down special: Aymr | `SpecialLw` (heavy overhead, super armor up to 30 damage), `SpecialLwHit`, `SpecialLwCancel`, landings, `SpecialLwTurn`; `param_special_lw` critical zoom 1-on-1 | her Flip Jump statuses replaced (MSC); armor by damage threshold; the critical zoom as Strike's camera cave (strike_cave) if wanted |
| Final Smash | Progenitor God Kindled (cinematic `VisualScene01-03`, sword2 / background articles) | Open questions 5 |

### Weapons / held models

- **Held weapons baked into the body** (as Hero's sword / shields and Sephiroth's swords): Areadbhar (`spear`, 2
  bones), Aymr (`axe`, 5), Failnaught (`bow`, 12) as meshes on bones of their own under HaveR / HaveL, their animation
  from the article's motion of the same move (Ultimate plays the article motion named as the body's), shown by
  visibility slots driven from when Ultimate's scripts generate / remove them (the tool needs: driving slots keyed by
  the eyelid pac, and article tracks merged into the body's). Bone budget: ~19 more bones; coat swing bones merged to
  stay under 136. Their hitboxes go on those bones (table-1 joints, as `Sword1`).
- **The whip sword** (`sword`, 58 bones; 28 segments): its moves (rapid jab, up smash, down tilt, up air, throws, down
  taunt) play canned article motions with hitboxes on the segments: either a model article of his own (dein copy with
  MotionModule: W5, its own ACMD) or baked like the others (58 bones: too many with the coat; resampled to fewer).
  For the up special's tether: her whip article (copied as his kind, his sword's model on its 8 segments).
- **Arrows** (`arrow1`, `arrow2`): projectile weapons of his own (nop2 / on_hit per the guide's catalogue).
- `swordflare` (the sword's flame) / `sword2` / `background` / `baton`: Final Smash and entry only.

### Sound and UI

- Sound: `ultimate_sound.py` on `se_master` / `vc_master` / `vc_master_cheer` (+ costume banks: `se_master_c01` and
  `vc_master_c01` are the female's) with his own bank ids (46000 + 6 x 32 + slot = 46192...), the aliases in
  `reference/port_sound_ids.json` and `sound_alias_cave.py` (exe), `soundlabeltable` grown (the user's current one).
- UI: `ultimate_portraits.py` from `chara_*_master_*` framed as ZSS's (templates made by add_fighter), name plates
  BYLETH from the vanilla plates' letters, stock icons from Ultimate's chara_2; the 5-row select is already there
  (Squirtle); `add_fighter_customs.py` (ZSS's custom-move labels).

### Kirby

Trait Strike is in. Kirby can't copy a new kind unless the executable grants it (copy_grant refuses kinds >= 0x3A;
`kirby_copy_new_cave.py` MAP has Supamario, Hero, Sephiroth; Incineroar / Steve / Squirtle aren't copyable either). For
Failnaught on Kirby: map 0x47 -> a granted kind (Pit's copy 0x18: a bow, charge and arrows; or Robin's 0x2C as Hero /
Sephiroth), its marker, his hat (`kirby/model/copy_master_cap` from Ultimate's Kirby folder: not downloaded yet;
`kirby_copy_hats.py`), his motions (`kirby/motion/masterbody`, `kirby_copy_motions.py`), the arrows in the copy's
article list (Ultimate's `param_special_n` has `arrow_offset_*_kirby`), the copy voice (`vc_kirby_copy_master`,
downloaded). The Drive's `kirby-ssbu-partial.zip` has both: `kirby/model/copy_master_cap/c00-c07` (Byleth's hair as a
hat: male / female textures) and `kirby/motion/masterbody/c00` (12 motions: Failnaught on Kirby); not downloaded yet.

### Risks

1. **x152C (her tether vector).** ZSS (0x19) is a `TAIL_EXTRA_KINDS` base: the vl load tail stores its x152C vector
   for her own kind only, and the kinds with one are exactly the tether fighters (Link, Samus, ZSS, Toon Link,
   Lucas). Kind 0x47 gets 0 there. Any of her native tether code the port reaches (grab whip, zair, lasso hang) may
   read a null vector (crash). Before the first in-game test: copy the base's x152C entry for the new kind in its vl
   load case (kind_expand.py), or keep him off every tether path. The up-special plan above needs the first.
2. Her native code on his moves: her grab spawns the whip, zair is on (Has Tether 1), her specials' physics; every
   one replaced or switched off in his MSC / params.
3. Articles: the whip sword's 58-bone article is costly (W8 / W11: instances x bones in the animation heap); the
   held-weapon baking needs ultimate_fighter.py work (eyelid-pac driven slots, article tracks).
4. Effects: 91 own sets + 28 common (heap: E9 checks it; Sephiroth needed effect_heap_patch).
5. The effect bank's size (E9: ~12.4 MiB, under Sephiroth's crash point; more with variants) and the FS ripple (E5).
6. Female costumes: male motions (exact for attacks), female hair / skirt / knife static until their tracks are
   merged in; female idles / taunts / wins are the male's; female voice needs per-costume voice support.

## Decisions (user)

1. Their install files (fighter_param with the other ports' stats, the param / ui databases, melee.msbt, ui/replace/chr,
   soundlabeltable) come later: everything that depends on them re-runs on theirs with one command ("Re-run on the
   user's files"); vanilla stand-ins until then, shipped as not_for_install.
2. Ultimate's specials order: side Areadbhar, down Aymr, neutral Failnaught, up Sword of the Creator.
3. Up special on ZSS's native tether / ledge hang with his own Sword of the Creator on top.
4. Female costumes: her own animations and voice per costume (voice done: her banks load by costume; animations: the
   executable change is approved, Handover 2).
5. Final Smash: ZSS's for now, no crash; his Final Smash effects kept out of the bank (E5).
6. Subtitle "A Heroic Legacy".
7. Kirby's Failnaught copy with his hat (Handover 3); Kirby's trait for him: Strike.
8. Aymr's KO zoom in 1-on-1: yes (Handover 4).
9. ZSS's statuses / leftovers must not override his (v1 audit above).

## Commands

```
python3 tools/ultimate_port.py init master --base szerosuit --kind 0x47 --ui-name "Byleth" --trait strike
python3 tools/ultimate_port.py plan master --out OUT
python3 tools/ultimate_port.py run master body model-c00 model-c01 model-c02 model-c03 model-c04 model-c05 model-c06 \
    model-c07 motions low-models effects --out OUT
python3 tools/ultimate_port.py stats master FIGHTER_PARAM_BIN OUT/master/param/fighter/fighter_param.bin
python3 tools/add_fighter.py --kinds tools/extra_kinds.json --only master --folder VANILLA/fighter/szerosuit KINDDIR
python3 tools/port_check.py master OUT/master
# v1: the specials, held weapons, trails and the package
python3 tools/master_build.py vis DUMP ULT fighters/master/weapon_vis.json        # before the motions step
python3 tools/ultimate_port.py run master effects model-c00 .. model-c07 motions low-models scripts specials variants \
    shapes portraits --out OUT                                                    # specials = master_build.py build
bash scratchpad/byleth/make_pkg.sh                                                # -> scratchpad/byleth_v1.zip
# v2: the new slots' animations and scripts, Ultimate's low models, the win cameras (built, not shipped), the package
python3 tools/ultimate_port.py run master motions low-models camera scripts specials variants shapes --out OUT
bash scratchpad/byleth/make_pkg_v2.sh                                             # -> scratchpad/byleth_v2.zip (files changed since v1)
python3 tools/port_check.py master scratchpad/byleth_v1.zip scratchpad/byleth_v2.zip
# v3: the costume groups (exe_v46s), the female motions, the costume tests, the win cameras; a complete package
python3 tools/rpx_patch.py exe_v46r.rpx exe_v46s.rpx $(python3 tools/costume_group_cave.py --rpx exe_v46r.rpx)
python3 tools/costume_group_test.py exe_v46s.rpx exe_v46r.rpx
python3 tools/ultimate_port.py run master motions motions-group2 low-models camera scripts specials variants shapes --out OUT
bash scratchpad/byleth/make_pkg_v3.sh                                             # -> scratchpad/byleth_v3.zip (complete)
python3 tools/port_check.py master scratchpad/byleth_v3.zip
```
Body: `rolloff_acmd.py VANILLA/.../game.bin game.bin --plain --add 2.2 EscapeF EscapeB`; `mscdec.py -x tools/mscinfo.xml
szerosuit.mscsb` (round trip: 2 of 2393 functions differ, both equivalent: a folded negative constant, an empty else),
`universal_mechanics.py --air-mult 1.0`, `msclang.py`; packed as `build/universal_mechanics_all.zip`'s szerosuit entry
(local: the user's universal_mechanics_all wasn't at hand).
