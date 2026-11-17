# Byleth (`master`)

A port of Ultimate's Byleth (internal name `master`) to Smash 4, on **Zero Suit Samus's base** (`szerosuit`, kind
0x19). New fighter kind **`0x47`**, character id **65**, UI name `Byleth` (subtitle "A Heroic Legacy": Ultimate's own
string for him, `msg_menu.msbt` `mnu_standard_sub_master`; Ultimate has no other per-fighter subtitle), texture-id block `0x40C70000` (`reference/port_bases.json` `_texture_ids`). Trait: **Strike** (the user's
choice; `docs/character-traits.md`, `kirby_copy_trait()`). Roll-off: the default 2.2 / 1.0 with Hero's momentum
(ZSS's universal-mechanics body, below).

The port goes through the framework (`docs/ultimate-port-guide.md`): `fighters/master/port.json`,
`tools/ultimate_port.py` (init / plan / run), `reference/port_bases.json` `szerosuit` (her traps, new with this port).

## Status: rapid_setoff v1 (`scratchpad/rapid_setoff_v1.zip`, over v17: exe_v46y_hold, body game.bin, Sm4shCommand v1.7.5; in-game TEST)

User: "can you recreate the Ultimate setting for rapid jabs?" (v17 held the loop with angle 80.)

| point | finding (evidence) | change |
|---|---|---|
| what Ultimate's setoff is | ExeFS main.bin (docs/native-notes.md "Hitbox hold"): AttackData +0x62 `set_off_` (the store_l2c_table hash40 names), AttackModuleImpl vt +0x728 set_set_off, set_attack's collision word (0x22 / 0x23, Smash 4's Clang bit) and the clank resolution 0x3E0A50 (ON / THRU: the move cancelled, OFF / NO_STOP: goes on; NO_STOP: no clank hitlag): the CLANK kind, already Clang / Rebound in the port. It never touches the victim. What Ultimate does for a grounded 361 hit under 60 knockback: 0 degrees and the speed x0.8 (`damage_angle_ground_zero_speed_mul`, 0x403A20); Smash 4: 0 degrees, x1 | none needed for the field itself |
| the hold | Smash 4's victim handler 0x02C25318 stores the launch vector (knockback x 0.03 along the angle) into the damage event's +0xC / +0x10 at 0x02C25BF4, which the fighter's damage energy takes | new ACMD command **Hitbox_Hold(ID, Mode)** (`tools/hitbox_hold_cave.py`, region 0x04BD7000-0x04BD8000, exe_v46y_hold = exe_v46x_whipmot + it): Mode 1 a grounded victim the hit doesn't lift gets no travel (damage, hitstun incl. HitstunMul, hitlag, SDI, the flinch kept), Mode 2 every victim; the mark goes with the hitbox. `tools/hitbox_hold_test.py`: 54 checks (the game's code around each hook) |
| the rapid jab | v17's attack100: the 12 loop hits (IDs 0 / 1, frames 2 - 17) at HOLD_ANGLE 80 | back at Ultimate's **361**, each followed by `Hitbox_Hold(ID, 1)` (an airborne victim is carried at the Sakurai air angle as in Ultimate; the finisher launches). Only attack100 changed (12 angle words + 12 commands; `scratchpad/setoff/build_game.py` on v17's game.bin). attack100sub (Ultimate's Attack100Sub) has no Smash 4 script |
| the pipeline | `ultimate_acmd.holding` (setoff off + 361 + FKB 0 + KBG / BKB <= 30 + damage) | HOLD_MODE 'hold' by default (Ultimate's angle + Hitbox_Hold); v17's angle with `--hold-angle` / port.json `rapid_hold: "angle"`. **port_check S28** (ERROR: a holding hit from the dumps without Hitbox_Hold; WARN: v17's angle) and **X8 hold-exe** (ERROR: Hitbox_Hold without the cave in the install's exe) |

Checks: `tools/master_specials_test.py` 131 checks, 0 problems (+ the default mode, Attack100 translated with 12 holds).
port_check over v4 ... v17_fix, rapid_setoff_v1: 0 ERROR apart from R2 result-param (v17's result_param.bin, the
results-panels work's: with results_panels_v1 before this package, **0 ERROR**, 31 WARN). v17's install now: S28 WARN
(the old angle). Other ports: no Ultimate hit in their dumps matches the hold rule with damage (Hero's Final Smash start
7 % at 60, Incineroar's Cross Chop start 2.5 % at 5 / BKB 30, Squirtle's Final 0.5 % set knockback 20 at 30 / 330 are
setoff off but not 361 / low-knockback-growth holds: they launch or carry by design; pummels are set knockback on a
grabbed victim). Not done: Ultimate's x0.8 on other 361 grounded hits; ATK_SET_SHIELD_SETOFF_MUL (shield push, x9 on
the loop hits).

## Status: v17 (`scratchpad/byleth_v17_fix.zip`: a FIX package over v16 + sound_v1: body / whip game.bin, the whip's pac, master.mscsb, the face pacs of c00 - c07 / l00 - l07, fighter_param.bin, result_param.bin; exe unchanged (exe_v46x_whipmot); in-game TEST)

User, v16 test: (1) "the whip disappears when catching someone"; (2) "jab 3 is inaccessible"; (3) "the rapid jab's hits don't
connect properly"; (4) "the sword will appear twice in taunts"; (5) "reduce Byleth's travel time slightly during the catch";
(6) the mouth still missing in the victory poses (male and female winners) and Byleth not in the loser panels (an empty
grey panel; image 28: P1 Byleth winning, P2 Byleth's panel empty; image 29: DK's panel shows him clapping).

| point | cause (evidence) | fix |
|---|---|---|
| the whip vanishes at the catch | v15 / v16's SpecialAirHiHit script took the tether's whip (made in AirCatch at 0, in her shoot status 1 from 17: WhipShoot in hand space, her native chain) into status 0 (`Set_Remote_Article_Action(2, 0)`) and played the hit motion on it. In the executable (below, docs/native-notes.md "Article ops"): op 0x2713 is only a status request to the weapon (applied at its next shift), op 0x2715 only a change_motion (frame 0, rate 1): nothing re-links or re-shows the article. The whip MSC (`v15/whipmsc/whip.c`) has no removal and no visibility off anywhere (status 0: pre only, no main; status 7 turns visibility ON), and its scripts for the new slots are Visibility 1 (dumped from the install); the face keys of SpecialAirHiHit / the overtake hide only the body sword; master_whip_sweep keeps 0x15B; master_hi_air_end skips func_127 into 0x15B. So the scripts / MSC / sweeps don't hide it: what changed from v14 (sword shown through the stop, v14's clip) is the tether whip moved out of her native tether statuses into an anchored motion, which ZSS never does (her whips that play anchored motions are made in their own move; the generation callback 0x02F8172C sets the whip up from the owner's status at its making). NOT proven in game which native step drops it (the kind's native handlers not read) | the tether's whip removed at SpecialAirHiHit's 0 and a fresh one made at 1 (`master_build.hi_hit_script`: an article's removal may finish only at the frame's end, the whip has one instance), the hit motion on it from there: the HIT slots now start on the body's frame 1 (`master_whip.HIT_GEN`; Ultimate's bend kept on body frames 1 - 2); pull / overtake on the new whip as before. The floor / ceiling stop keeps her reverse. One frame (0) with no sword. **port_check S29 article-status-reuse** (ERROR on v16's install) |
| jab 3 inaccessible | fighter_param 86 (attack_100_input_count) 0, ZSS's (she has no rapid jab), with Byleth's rapid jab on (264 = 1): the common Attack status (`func_270`) goes into Attack100 when ENABLE_100 is on and the presses (0x11000003) >= 86: 0 >= 0 the moment jab 2's script turns ENABLE_100 on (6 - 10), pressed or not, before jab 3's combo input. Vanilla 3-jab + rapid fighters all have 4 - 6 (Captain Falcon, Bayonetta, Corrin, Pit, Greninja 5) | the user's fighter_param.bin (byleth_userdata_v2), kind 0x47's row only: **86 0 -> 5** (Ultimate's attack_100_enable_cnt 4 + 1, the vanilla rule), **81 / 82 (combo_input_frame_attack12 / 13) 30 -> 28** (Ultimate's combo_attack_12_end / 13_end); 262 (1: hit), 263 (3), 264 (1) were right. `ultimate_stats` maps 81 / 82 / 86 / 262 now. **port_check P3 rapid-count** |
| rapid jab doesn't connect | Ultimate's Attack100 hits: 0.4 %, angle 361, KBG 10, BKB 12 / 10, ATTACK_SETOFF_KIND_OFF (no setoff: the victim held), +3 hitstun. Smash 4 has no setoff field and its 361 sends a grounded victim under 32 knockback at 0 degrees: each hit slid it away (about 2 units a hit) out of the 3 - 24 reach. Rehit, hitlag (0.4), SDI (0.7), positions (top, Z 9 / 18) and the 2 / 5 / 8 / 11 / 14 / 17 loop are Ultimate's; the hit log is cleared as in vanilla rapid jabs (Part 0 re-made after Remove_All_Hitboxes); the +3 hitstun is there (HitstunMul -3) | the 12 loop hits at **angle 80** (`ultimate_acmd.hold_angle`: setoff off + 361 + small knockback; Smash 4's own rapid jabs hold at 50 - 90: Robin 80; APPROXIMATED: an airborne victim goes up a little); the finisher unchanged (54). Other ports: no Ultimate hit in their dumps with damage matches the rule (only 0-damage boxes: Steve's forge, Hero's Snooze). **port_check S28 rapid-slide** |
| the sword twice in taunts | ZSS's side taunt (appealsr; appealsl JUMPs to it) and Win1 kept her own game scripts: GENERATE_ARTICLE + her whip slot 40 / 48 (now his back / down throw's sword) while the body sword shows (Ultimate's AppealS / Win1 make no sword article). Also the up smash: slot 4 built from body frame 7 but played at FRAME 8: the whip hid a frame after the body sword came back (frame 59) | `master_whip.strip_base_whip` (the base's whip out of every script the whip plan doesn't write: appealsr, win1); slot 4 rebuilt from frame 8. **port_check S27 weapon-twice** (port.json `weapon_article`: every frame of a body script with the whip drawn and the body sword shown, and an article made where Ultimate makes none) |
| travel time | user | the reel **5.0 a frame** (Ultimate's 4.1; `MASTER_HI_REWIND`, `master_whip.REWIND`); the six pull motions rebuilt at 5.0 (the blade 64 -> 16.1 in 10 frames, 48 in 7, 24 in 2); the stop (19 / 12) and the overtake unchanged. Travel (blade length L, the reel ~L - 16.1): far L 64: 12 -> **10** frames; L 48: 8 -> **7**; near L 24: 2 -> **2** |
| no mouth in the result poses | v16's per-motion result entries (MouthN on in both face pacs) changed nothing in game, so the results scene draws the poses in another state: the face pac's `display.mta` (ZSS's, kept: Mouth_Result on, every other mouth slot off; Mouth_Result is his sword: no mouth, the face's mouth hole drawn black), the only entry of his that hides every mouth (default / default_temporarily show one) | `ultimate_fighter.display_entry` (result_faces runs it): display.mta with MouthN on, the other mouths off, the sword on (Ultimate's win poses hold it), added to face_lang.pac too, c00 - c07, l00 - l07. NOT confirmed in game that display.mta is the state used (the evidence is that it is the only one without a mouth). **port_check F4 display-face** |
| empty loser panel | `param/ui/result_param.bin` (the user's = vanilla) frames each fighter in the results by model name (61 entries; names reversed and XORed with "Smash"; fields from the scene's Xtal bindings at 0x030D37C4: win1 - 5, MVP / team, eye / to). "master" has none, so the panel uses "missing" (all 0): the loser camera on its target, nothing drawn | an entry for "master", a copy of ZSS's (eye (3, 15, 5), to (0, 17, 0): her lose-panel framing, APPROXIMATED for his height) with win1 - 3 125 / 169 / 156 (ZSS's 135 / 150 / 135 scaled by the motions' lengths, 131 / 181 / 181 against her 141 / 161 / 157: APPROXIMATED) (`tools/result_param.py`). His lose motion (J02Lose: Ultimate's clap, 111 frames) was already in bodyresult. Every other new-kind port (Hero, Sephiroth, Incineroar, Steve, Squirtle, Supamario) has no entry either: their loser panels are empty too (fixed by `results_panels_v1.zip`, which keeps his entry byte for byte; the pipeline's `result-param` step rebuilds his with the same win frames). **port_check R2 result-param** |

Checks: `tools/master_specials_test.py` **129 checks, 0 problems** (v16's 105 with the reel at REWIND and v15's hit-script
checks now v17's: the removal at 0, the new whip with the hit motion at 1, no status change; + v17: the reel / pull rates, the
slots' starts, the pulls' frames at 5.0, slot 4 from 8, the base's whip stripped only from the taunt / Win1, the holding
angle cases, the jab chain's stats from Ultimate's). port_check (v4 ... v16_fix, sound_v1, v17_fix): **0 ERROR**, 31 WARN
(`scratchpad/v17/pc_v17.log`; P2 stats-ultimate gone); on v16's install: F4, P3, R2, S27, S28, S29 ERROR (`pc_before.log`).
The whip pac: only slot 4 and the 12 up-special slots changed (entry by entry); blade lengths read back: pull 64: 64, 59,
54 ... 19, 16.1; hit 48 at its frame 0 (body 1): the 64 bend. fighter_param.bin: three values at 0x1EC8A / 0x1EC8F / 0x1ECA5
(kind 0x47's 81, 82, 86). Package `scratchpad/byleth/make_pkg_v17_fix.py` (`scratchpad/v17/bin/build.py`, `build2.py`),
INSTALL README `scratchpad/byleth/INSTALL_README_v17.txt`. Not done: the Hitbox Viewer pass (the rapid jab's angle only
changed; positions are v16's).

Other ports, from the new stats mapping against the user's fighter_param.bin (not changed): Sephiroth 81 30 -> 28, 262 1 -> 2;
Incineroar 81 30 -> 24, 82 0 -> 32 (and 263 2 where Ultimate has 3: his jab 3 may be unreachable too); Steve 81 / 82 27 -> 0,
86 5 -> 0, 262 2 -> 0; Hero 86 6 -> 0 (no rapid jab, harmless); Squirtle 81 / 82 24 -> 30.

## Status: v16 (`scratchpad/byleth_v16_fix.zip`: a FIX package over v15: body / arrow2 game.bin, master.mscsb, the face pacs of c00 - c07 / l00 - l07; exe unchanged (exe_v46x_whipmot); in-game TEST)

User, v15 test (clips `afdc9a1a-...191508681.mp4` (ours, Aymr with turns), `560378f7-...192510721.mp4` (ours, the ground
up special on DK twice), `72aa49f5-...193014493.mp4` (Ultimate, the same up special), `838dcda7-...193139500.mp4`
(Ultimate, Aymr with a turn); framed at 60 fps): Aymr has no hit sound; Aymr's turn only shows when the move ends; the
up special's catch -> hit too slow. Coordinator, from the user: the mouth is missing in the victory poses.

| point | cause (evidence) | fix |
|---|---|---|
| Aymr silent | Ultimate's axe ATTACK: `ATTACK_SOUND_LEVEL_L, COLLISION_SOUND_ATTR_MASTER_AXE` (Ultimate plays its own HitSE `se_master_hit_axe`; no PLAY_SE on hit in the scripts). `ultimate_acmd.SFX_TYPE.get(attr, 0)` had no MASTER_AXE: SFXType 0, Smash 4's "Nothing" (installed speciallwstart 0x6642CE2F / specialairlwstart: SFXLevel 2, SFXType 0). The same for _MASTER_ATTACK100END (the rapid jab's finisher) and _MASTER_ARROW_MAX (the max arrow), and Aymr's down smash / down air (MASTER_AXE): 13 body hitboxes, 720 in arrow2 | `ultimate_acmd.sfx_type`: every attribute the ports' dumps use mapped (the fighters' own -> 3 slash: Smash 4 has no per-fighter hit sound type for a new kind (Cloud's 0x3B - 0x3E are his), so `se_master_hit_axe` itself can't play: APPROXIMATED as the common heavy slash at level L; BOMB 0xB, WATER 9, FREEZE 0x1C, SLAP 0x12, ZENIGAME_SHELLHIT 2), an unlisted one warns, never 0. `tools/hit_sound_fix.py` (Ultimate's ATTACK / ATTACK_ABS matched by damage / KBG / BKB / size) fixed the installed files: only SFXType words changed. **port_check S25 hit-sound** (ERROR; v15's install: 5 body scripts, 8 arrow2). Other ports with the same silent hits (their dumps): Hero (AttackS4 / Hi4 / Lw4 critical, Kaboom / Kafrizz / Magic Burst (SpecialLw18 / 20), the explosions), Squirtle (Water Gun, Waterfall, AttackHi4, Final, its water), Incineroar (Attack11 slap, SpecialHiBound bomb), Steve (Final end): to fix with hit_sound_fix on their installs |
| Aymr's turn at the end | Ultimate: SpecialLwTurn is its own status (lua2cpp f_7208a21800 main: special_lw_turn by situation, the axe told `fighter_master_axe_turn`; f_7208a289f0 loop: MotionModule::is_end -> back to SpecialLw, whose main (f_7208a21060) resumes special_lw at the kept frame and restarts the axe); its script's REVERSE_LR at 8. The turn motion d03speciallwturn (12 frames) turns his hip -35 -> 122 degrees and ends on SpecialLw's pose (-58) turned 180: the model faces the new way from where SpecialLw resumes. Ours (v7): the same flow inside one status (0x155 phase 4, Reverse_Direction at 8), but Smash 4's Reverse_Direction (handler 0x02BD42E0 -> PostureModule vt+0x84) flips the facing only (`+0x60`); the model's turn (`+0x64`, update_rot_y_lr vt+0xC4) waits for a status change: SpecialLw resumed drawn the old way (hitting the new way) until the move ended (docs/native-notes.md "Facing and the model's turn"). Clips: Ultimate turns at 89 - 97 of clip 4 and swings to the new side (108 - 120) | master.c: PostureModule(0x2) where SpecialLw resumes after the turn motion (both situations). **port_check S26 turn-rot** (ERROR on v15's master.c) |
| up special too slow | measured (below): catch -> overtake hit 36 - 37 frames in our two attempts, 37 in Ultimate's; start -> hit 57 ours, 61 Ultimate's. Ultimate reels at param_special_hi rewind_speed x PostureModule::scale (f_7208a0a800: the sword's float = 4.1 x scale, a frame), as ours; its stop is hit_stop_frame_fighter 19 from the catch (measured 18), ours 19 - 20 | **not changed**: no difference from Ultimate found that would make it "much faster". Asked the user which part feels slow (the air version / a far catch are not in the clips) |
| no mouth in the victory poses | `ultimate_fighter.build_motions` writes face entries for motion/body only; the result poses' (bodyresult: J02Win1 - 3, waits, Lose) stayed the base's: ZSS's `material_anime_face_lang.pac` (the results scene's) Win1Wait / Win2Wait / Win3 / Win3Wait key MouthN and every mouth slot 0 and Mouth_Result 1 (her result smile; his Sword of the Creator), in every costume and low model; Win1 / Win2 / Lose had no entry (default.mta) | `ultimate_fighter.result_faces` (also run by build_motions now; `ultimate_fighter.py result-faces` on the installed folders): every result motion's entry from Ultimate's visibility (MASTER_MOUTHS drive: e.g. j02win1's master_Mouth_Result -> MouthN, the sword where master_sword shows) in face.pac AND face_lang.pac, male (c00 motions) and female (c01) groups, c00 - c07 and l00 - l07. **port_check F3 result-face** (ERROR: v15's install, all 16 folders) |

Up special, frames from the clips (60 fps; ours: Cemu at full speed, clip 1's timer 5:52.05 -> 5:47.05 over 300 frames;
Ultimate's: unique frames, 2 repeats in 55):

| | Ultimate (clip 72aa49f5) | ours, 1st (560378f7) | ours, 2nd |
|---|---|---|---|
| the catching hit (3 %) | 69 | 81 | 385 |
| stop: he starts to move | 87 (18) | 101 (20) | 404 (19) |
| travel: on the target | 93 (6) | 109 (8) | 412 (8) |
| the overtake's hit | 106 (13) | 118 (9) | 421 (9) |
| catch -> hit | **37** | **37** | **36** |

Aymr's turn (Ultimate clip 838dcda7): the stick back at ~89 (the turn motion, whirlwind), facing the new way by 97, the
swing to the new side 108 - 120; ours (afdc9a1a): the swing faced the old way and turned at the end (v15; v16 not
filmed).

Checks: `tools/master_specials_test.py` **105 checks, 0 problems** (v15's 98 + v16: the turn by situation, the model
facing the old way through the turn motion and turned as SpecialLw resumes at its frame, none with the stick forward;
on v15's master.mscsb the two model-turn checks fail); compiling v15's master.c reproduces the installed master.mscsb
byte for byte. port_check (v4 ... v15_fix, v16_fix): **0 ERROR**, 31 WARN (`scratchpad/byleth/pc_v16.log`, as v15);
on v15's install: S25 and F3 ERROR (`pc_v16_before.log`), S26 on v15's master.c. Package
`scratchpad/byleth/make_pkg_v16_fix.py` (35 fighter files, the TEST_ONLY diag master.mscsb for v15's TEST_ONLY exe),
INSTALL README `scratchpad/byleth/INSTALL_README_v16.txt`.

Not done / approximated: Ultimate's own hit sounds (se_master_hit_axe ...: the common slash instead); the result poses'
eyelid / eye keys (`material_anime_eyelid_lang.pac`, `eye_lang`) are still ZSS's blink timing (the eyes show); the up
special unchanged (above).

## Status: v15 (`scratchpad/byleth_v15_fix.zip`: a FIX package over v14: the whip's motion pac / scripts, body game.bin, master.mscsb; **exe_v46x_whipmot**; in-game TEST)

User, after v14: Ultimate's sideways bend of the sword on the hit, the sword's own overtake animation, and the
retraction tied to the pull's distance (v14's "Not done" below).

| point | source (Ultimate's files) | built |
|---|---|---|
| no whip slot free | the whip (weapon 0x1A0) motion info is a **static** table (hashes `crc32(.omo name, 0xFFFFFFFF)`: the v14 handover's raw `crc32(name)` search missed it), weapon_expand_append.py's copy at `0x04B9C438` (60 entries: her 15 x 4 custom moves) | `tools/master_whip_motion_cave.py` (exe_v46x_whipmot = exe_v46w_vars_line + it; region `0x04BD6000`-`0x04BD7000`, docs/native-notes.md "Whip motion table"): 112 entries, 13 new motions (`master_whip.NEW_NAMES`, slots 60 - 108, 4 each); the whip's motion.mtable 112 (`master_whip.new_scripts`: the visibility game scripts), main.pac + 13 (`master_whip.py up`); `tools/master_whip_motion_test.py` (unicorn, 20 checks) |
| the hit's bend | `motion/sword/c00/d02specialairhihit` (16 frames: frames 1 - 2 the tip 22 sideways (x), 65 long; still from 3 - 4) on his `d02specialairhihit` hand (HaveR) | HIT_SLOT(v): frames 0 - 4 exactly Ultimate's (renders: the same tip to 0.1), then the blade eased over 4 - 9 to PULL_LENGTHS[v] (its straight pose in d02specialhipull) and held (APPROXIMATED: Ultimate's status code aims the sword at what it holds, tip_angle_object, not read; ours keeps the hit pose's direction, his hand's 0.91 up / 0.40 forward, and the length) |
| the pull | `d02specialhipull` (101 frames: a straight blade 115 long at 0, 1.01 shorter a frame; the sword's rewind picks its frame from the length; param_special_hi rewind_speed 4.1) | PULL_SLOT(v): the blade at PULL_LENGTHS[v] - 4.1 t (the reel's speed: master.c reels 4.1 a frame) down to 16.1 (the overtake's first frame), then held; 6 starting lengths 64 / 56 / 48 / 40 / 32 / 24 |
| the length's pick | the catch's distance | master.c `master_hi_sword_len` (0x15B's main, before its motion): his hand in the hit pose (6.2 ahead, 18.5 up from where he is held) to the caught fighter's throw point / the wall point, the nearest length -> **VAR_16** = 10 x VAR_15 + v (-1: the floor / ceiling stop); diag: a second k4 line, 1000 x VAR_16 + the distance |
| the overtake | `d02specialairhiovertake` (12 frames, the folded sword swung over) on his `d02specialairhiovertake` | OVT_SLOT 60, played by specialairhiovertake's game script at 0 (`master_build.overtake_sword`) |
| playing them | Ultimate: the sword article's own statuses | SpecialAirHiHit's game script (`master_build.hi_hit_script`): VAR_16 >= 0: `Set_Remote_Article_Action(2, 0)` (the whip out of her tether status 1 / 2, whose MSC loop sets its motion rate, into status 0: no MSC main, as a generated whip) and `Set_Anchored_Article_Action(2, HIT_SLOT(v))` at 0; at 12 (wall) / 19 (fighter) `Set_Anchored_Article_Action(2, PULL_SLOT(v))` (replacing v9 - v14's `Set_Remote_Article_Action2(2, 3)`, her native reverse); the floor / ceiling stop keeps the reverse at 0 |

Kept: v14's freeze protection (the stop's own-frame count and MASTER_HI_STOP_CAP; the 60-frame hit motion). Not
proven in game: that ArticleModule 0x271B (the anchored action) restarts the motion at rate 1 after her status 2 (rate 0:
whip.mscsb func_54) - status 0 is entered first; if the sword stands still on the catch, that is the cause (then the
MSC sets the rate: the whip's MotionModule 0x4 through a link event, or status 4 / 6). Not reproduced: Ultimate's aim of
the sword at the target (tip_angle_object -15 / tip_angle_wall 70), the ground up special's hit (SpecialHiHit: our
ground up special has no catch).

Renders (`scratchpad/v15/render_up.py`, the v6 whip renderer: ours = his converted body + the whip's new slots from the
shipped pac / model, beside Ultimate's body + sword article at the same frames; `scratchpad/v15/renders/sheet_hit.png`,
`sheet_pull.png`, `sheet_overtake.png`): the hit's frames 0 - 4 match Ultimate's (the bend at 1 - 2 in the front view),
9 the 48 blade; the pull at 48 - 4.1 t against Ultimate's pull at the same length; the overtake frame for frame. The
blade lengths read back from the built .omo (HaveN -> AttachN): hit 64.6, 64.0, 64.0, 64.6, 64.6, (6) 58.7, (9) 48.0;
pull 48.0, 43.9, (3) 35.7, ... (8) 16.1. Hitbox Viewer (the whip as its own fighter root, Shot.exe:
`scratchpad/v15/view/whip_view.png`): the shipped pac / model play HIT 48 frames 2 / 9, PULL 48 frame 4, the overtake 4
(the viewer shows no articles on the body, as v12's views).

Checks: `tools/master_specials_test.py` **98 checks, 0 problems** (v14's 80 + the length pick for a fighter / a wall /
the stop, the hit script's commands for every mode x length, the overtake's, the slots); `tools/master_whip_motion_test.py`
20 / 20 on exe_v46x_whipmot vs exe_v46w_vars_line and on the diag pair; port_check (v4 ... v14_fix, v15_fix): **0 ERROR**,
31 WARN (`scratchpad/byleth/pc_v15.log`: as v14); new **X7 article-motion-slot** (ERROR: a body script's anchored article
slot past the install executable's motion info, or naming no animation in the article's pac): v15's data without its exe
-> X7 ERROR (the executable gives the whip 60 motions), without its pac -> X7 ERROR. A full `master_whip` motion build
reproduces the installed 15 whip motions byte for byte and the 13 new ones. Package `scratchpad/byleth/make_pkg_v15_fix.py`
(8 fighter files, the exe, the TEST_ONLY diag: v11's TEST_ONLY exe + the same cave (sha1 441117d7...), the v15 diag
master.mscsb), INSTALL README `scratchpad/byleth/INSTALL_README_v15.txt`. Sm4shCommand rebuilt with the whip's new
script names (ModAnimNames.txt).

## Status: v14 (`scratchpad/byleth_v14_fix.zip`: a FIX package over v13: master.mscsb, motion/body + body2 main.pac; exe unchanged (exe_v46w_vars_line); in-game TEST)

User, v13 test with the TEST_ONLY diag (log `0622cb9c-log.txt`, RPX 553479bb = v11's diag exe; clip
`6c3659c3-...182426865.mp4`, frames `scratchpad/byleth/v14/`): "Up special freezes Byleth, the whip and the opponent
forever now, with no movement after hitting an opponent."

| point | cause (evidence) | fix |
|---|---|---|
| the freeze | v13 ended SpecialAirHiHit's stop on its motion frame 19, but slot 0x23A plays D02SpecialAirHiHit, **15 frames** (Ultimate's special_air_hi_hit; Ultimate times its stop in status code): the motion stands on frame 14, 19 never comes. Log, first catch (k7 2: a soft catch, VAR_11 1, a ground target): k8 = 1000 x (19 - frame) + height: 19024, 18982, 18940 ... (frame + 0.042 a frame for 6 frames: his hitlag), then 18022 ... 6021 (1 a frame), then **5021 for 35 s** (frame 14 = 19 - 5). The k7 3 catches at 18:21:25 / :33 stand at k8 ~5031 the same; the wall attempt (stop 12 < 14) runs (k10 23 -> 0, k11 1). Clip (60 fps): two catches (DK 0 -> 3 % at frames 71 - 81 and 606 - 612, the catching hit's spark at 609), then nothing of Byleth / the sword / DK moves (621 - 883: Byleth below-left in the hit pose, the sword a straight line from his hand to DK, DK in its hit pose, held; only the stage's background and a slight camera drift change). The same cause had kept the game script's FRAME 19 (the sword back) from ever running in v9 - v12: the sword stayed full length through every reel | D02SpecialAirHiHit held on its last pose to 60 frames (`master_build.hi_hit_motion`, body and body2; `master_build.py hi DIR --fighter F`): its clock and script run through the stop and the reel (the sword goes back on 19 / 12 with the reel's start); the stop also ends after `hold` frames of his own out of his hitstop (SELF 0x0F000043) and at the latest hold + 30 frames (MASTER_HI_STOP_CAP), whatever the motion does; the floor / ceiling stop's Fall on frame 14 (MASTER_HI_HIT_LAST), not the motion's end. **port_check S23 frame-past-end** (ERROR: a declared MSC wait, port.json `frame_waits`, past its motion's end; WARN: script FRAMEs past it; v13's install: 0x23A waits for 19 of 15) |
| k14's 2 / 2.5 | SPEED_Y (0x0F000333) sums every energy, held ones too: v13 suspended the energies (he stayed put: k8's height part constant) but their speeds stayed, 2 - 2.5 up (the v12 drift's size). Which energy: not read yet | the energies' speeds zeroed when held (0, 2, 3; gravity was); diag k15 at the catch: 100 x energy + its y speed (KineticModuleF(1, e)) for 0 - 3, to name it |

Test model: `tools/master_specials_test.py` 80 checks, 0 problems, with a motion standing at 14 (v13's freeze: the stop
ends on loop 19, the reel and the overtake follow) and a 6-frame hitlag first (ends on loop 25). port_check (v4 ...
v13_fix, v14_fix): **0 ERROR**, 31 WARN (`scratchpad/byleth/pc_v14b.log`; the new one S23's script WARN: the overtake's
FRAME 12 on its 12-frame motion, attack100end's FRAME 85 on 52: their Remove_Article never run, the whip sweep removes
it); on v13's install S23 ERROR (0x23A waits for 19). The two pacs differ from the installed ones in that one motion only
(compared entry by entry). Package `scratchpad/byleth/make_pkg_v14_fix.py`, INSTALL README
`scratchpad/byleth/INSTALL_README_v14.txt`.

**Not done (handover, next agent; done in v15: "Status: v15"): the sword's own motions** (user: Ultimate's sideways bend on the hit, the sword's
overtake animation, the retraction tied to the reel's distance). Facts gathered:
- Ultimate's sword motions (`ult/master/motion/sword/c00`, read with `master_whip.Ult.sword_locals` / `.rel`):
  d02specialairhihit 16 frames (the tip (0, 65) at 0, swung to (22, 59, 11) at 2, back to (-1, 64) by 4, still after);
  d02specialhihit the same (67 long); d02specialairhiovertake 12 frames (short: tip (15, 6) at 0, (-12, 19) at 2, (0, 16)
  from 8); d02specialhipull 101 frames, a straight blade shrinking ~1 a frame (length 115 at 0 ... 18 at 96): the status
  code picks its frame from the length (the sword rewinds at rewind_speed 4.1 while he is reeled). SpecialHiHit's
  status code (lua2cpp f_7208a2b7d0) changes the sword's status and gives it tip_angle_object / rewind_speed; the
  overtake (f_7208a1f1d0) generates a new sword with `special_air_hi_overtake`.
- Our whip (article 2, ZSS's whip copy, weapon kind 0x1A0): 15 motion names, all used (`master_whip.SLOTS`); ACMD
  `Set_Anchored_Article_Action(2, slot)` plays a slot (index into the 60-entry motion info, 4 x custom move; only
  multiples of 4 are used) from frame 0 at rate 1 in fighter space. A raw CRC search of the exe for
  crc32('FitSZerosuitWhipMainC03AttackS4S') found nothing: the motion info for 0x1A0 is built at run time
  (`tools/weapon_expand.py`, "motions"; `docs/weapon-expansion-ram.md`), so the new slots need weapon_expand's motion
  table grown for 0x1A0, built as its own cave script over exe_v46w_vars_line (`scratchpad/vr/exe/exe_v46w_vars_line.rpx`)
  asserting the words it replaces, shipped under INSTALL_TO_code with a matching TEST_ONLY diag exe
  (`tools/diag_godfist_cave.py` over it).
- Then (master_whip.SLOTS + body_scripts): 60 = SpecialAirHiHit (the hit motion, its 65 length scaled to the whip's
  48 reach or the catch's distance: APPROXIMATE either way), 64 = the overtake, 68+ = the pull: Ultimate's
  d02specialhipull resampled to 4.1 a frame from 48, either one motion started when the length matches (a delay in the
  game script: the stop's frames + (48 - D) / 4.1 cannot be scripted per catch) or several pull slots by starting
  length (e.g. 48 / 40 / 32 / 24, MSC picks one into a VAR, the hit script branches on it); the hit script's
  Set_Remote_Article_Action2(2, 3) (the native reverse) replaced by those anchored actions at frame 19 / 12.

## Status: v13 (`scratchpad/byleth_v13_fix.zip`: a FIX package over v12, master.mscsb only; exe unchanged (exe_v46w_vars_line); in-game TEST)

User, v12 test with the TEST_ONLY diag (log `e50a37a0-log.txt`, clips `42cb0c57-...175946571.mp4`,
`f08f4b8b-...180404608.mp4`; frames in `scratchpad/byleth/v13/`): "Up special works now, but the pulling is jittery and
odd instead of the grab and pull being seamless and smooth. Also an effect persists through the move and never
disappears. The sword is also stiff during the pull." The follow-up now lands: k12 10 / 11 / 10 (on the target), k13
9.5 / 29 / 48.5 (its damage up by the throw's 6.5).

| point | cause (evidence) | fix |
|---|---|---|
| jittery pull | the log's stop: k8's height part constant for the first 6 frames (33: the catching hit's hitlag), then falling 2 - 2.5 a frame to -1 by the stop's end (all three catches): he drifted UP through the stop, past the reel's end point (the target's throw point - 14.2); the reel then went back against the drift (k10 9, 7, 5, 3: 2 a frame, not 4.1). Something still gave him a speed once the hitlag ended (only gravity (1) and energy 3 were held; not identified: energy 0 / 2 or a kept speed); v12 also measured each reel step from where he was | 0x15B holds every energy (KineticModule 0x2717 on 0 - 3; resumed by 0x2718 at the throw / its end; into the wall jump 0 / 2 / 3 resumed for the cling's root motion), writes his position each frame (`master_hi_place`): exactly where the stop began, then one straight path computed once when the stop ends (`master_hi_reel_begin` / `master_hi_reel`: n = ceil(distance / 4.1) equal steps), then the overtake's point. Diag k14 = SPEED_Y (0x0F000333) through the stop / reel |
| an effect never disappears | clip 42cb0c57 at 3.3 - 4.3 s (`v13/s.png`): a red wisp hangs in the air where the catch was, long after the move. master_wire_wind2 (efc 0x73, set PtcMasterMasterWireWind2): its 3 emitters' end frame is 0x7FFFFFFF (endless); v12 played it from MSC (non-following) and never ended it. In Ultimate it is an EFFECT_FOLLOW of the sword's hit motion, gone when the sword rewinds | stopped when the reel starts (EffectModule 0x2723, 0, 0: its particles fade), killed with its particles on any way out (0x15B's end, the status sweep leaving 0x15B). **port_check E15 msc-effect-leak** (ERROR: an endless own effect started from the MSC with no 0x2723 kill; v12's master.c: 0x3470073) |
| stiff sword during the pull | the sword goes back (her whip's status 3, WhipReverse: the extend backwards, a straight blade shortening, as Ultimate's d02specialhipull) by SpecialAirHiHit's game script at the motion's frame 19 (12 a wall); the stop was counted by the MSC loop, which ran through the catching hit's hitlag while the motion stood (log: 19 entries, the first 6 unmoved): the reel began ~6 frames before the sword pulled back, so he was pulled along a full-length rigid blade (inferred from the log's timing; Ultimate's pull shortens the blade with the distance) | the stop ends on the motion's frame (`MotionModuleF(1) < 19 / 12`): the reel and the sword's pull-back start together |

Not done: Ultimate's sword hit motion (d02specialairhihit: the blade whips 22 sideways over frames 0 - 4, then holds)
and its overtake motion: no whip motion slot is free (15, all used: master_whip.SLOTS) and Set_Anchored_Article_Action
starts a slot at frame 0; WhipShoot / WhipReverse are her native statuses' (status 5's frame-from-distance needs their
lengths). Needs the whip's motion info grown (weapon_expand "motions", an exe change). The reverse's speed is her native
rate (not tied to the reel's distance as Ultimate's length-indexed pull). If the overtake's start pops: the root moves
7.8 / 14.2 there by design (the pose compensates); a motion blend on 0x23B (vl byte 1) would show it.

Checks: `tools/master_specials_test.py` 78 checks, 0 problems (v13: held exactly through the stop's motion frames, one
straight path of equal steps <= 4.1 for a fighter and a wall, all energies held / resumed, wind2 stopped at the reel and
killed on a cut-short exit and by the sweep); port_check (v4 ... v12_fix, v13_fix): **0 ERROR**, 30 WARN
(`scratchpad/byleth/pc_v13.log`); E15 on v12's master.c: 0x3470073. Package `scratchpad/byleth/make_pkg_v13_fix.py`,
INSTALL README `scratchpad/byleth/INSTALL_README_v13.txt` (TEST_ONLY: the v13 diag master.mscsb with v11's diag exe).

## Status: v12 (`scratchpad/byleth_v12_fix.zip`: a FIX package over v11; exe unchanged (exe_v46w_vars_line); in-game TEST)

User, v11 test with the TEST_ONLY diag (log `a4361367-log.txt`, clips `bbed1d82-...170241085.mp4`,
`800871dd-...170250758.mp4`): "Up special pulls Byleth, but doesn't pull him above the opponent, so the follow-up never
hits. The effects for catching the opponent and off of the wall never play. The wall jump seems to work well now."

| point | cause (evidence) | fix |
|---|---|---|
| the follow-up never hits | (1) **the hit record**: v11's catching hit (SpecialAirHiHit's game script, frame 1, `Extended_Special_Hitbox` Part 0) and the overtake's soft hitbox (frame 11, Part 0) are in one status (0x15B plays 0x23A then 0x23B: `master_motion`); a Part's "already hit" record lasts the status (docs/acmd-extra-commands.md "Hit_Log_Clear"), so the overtake could never hit the fighter the catch had hit. (2) **the place**: the reel took his root to 8 behind the target's feet at their height (log: k8 33 -> 1, k10 34 -> 1: the reel works, it ends level with the feet) and the overtake's hitbox (9 around (8 fwd, 10 up)) swung beside the target; Ultimate's overtake (f_7208a1f1d0) sets his `top` constrained to the target's `throw` joint (LinkModule set_model_constraint_joint / _target_joint, then GroundModule set_shape_safe_pos at its centre), so he is ON the target: special_air_hi_overtake draws his hip 8.1 behind / 6.2 below the root on frame 0 and flips over it to stand on it by 10 (hip 9.5 up), the throw (ATK_HIT_ABS, no hitbox) at 11. The reel's end: the hit pose's hip is (-0.3 fwd, 8.0 up), the overtake's frame 0 (-8.1, -6.2): his root moves 7.8 forward / 14.2 up into the overtake, so the reel ends with the target's throw point 7.8 ahead / 14.2 above him (his raised hand; Ultimate's rewind is the sword article's, native) | the overtake's soft hitboxes on **Part 1**, centred on the target ((0, -3, 0), size 9: his root on its throw point; `master_build.overtake_part` / `hi_fix`; **port_check S22 status-hit-log**, port.json `status_scripts`); the reel to (target throw point - (7.8, 14.2)) (`master_hi_rewind`; a target on the ground: not under its feet), then his root on the throw point through the throw's frame 11 (`master_hi_ovt_place`, gravity held, the fall back at 12); the throw point = the target's waist joint (jtb 11, the joint position variables: its rest place) or its feet + 10 (MASTER_HI_OVT_Y, APPROXIMATED: its `throw` joint isn't readable). Real captures (0xBD) get the same placement |
| catch effects never show | v11 put master_wire_catch / master_wire_wind2 in SpecialAirHiHit's effect script as `Graphic_Effect`: that is the game's **FOOT_EFFECT** (Sm4sh_params ACMD events: 0xC84B610E FOOT_EFFECT; every vanilla use is ground dust). Its handler (0x02BE1444) first asks EffectModule vt +0x32C (0x02C31610: on only while the module's +0x9F / +0xA0 bytes are clear, the foot-effect switch) and plays nothing otherwise; he is in the air in 0x15B. The ids are right (efc 0x6E -> set 104 PtcMasterMasterWireCatch, 0x73 -> set 109 ...WireWind2 in the shipped bank, unchanged since v8); the script is bound (motion.mtable 0x23A = crc("specialairhihit")); the Hitbox Viewer draws foot effects regardless (`v12/view/v12_view.png`) | Ultimate's are the sword article's (SpecialHiHit: EFFECT_FOLLOW(_NO_STOP) on the tip, sword35, which holds the target): played from MSC at the target's throw point (`master_hi_fx_at`: EffectModule 0x2710, bone 0, flag 0); the effect script left empty. **port_check E14 foot-effect** (ERROR: own effects as FOOT_EFFECT in an air move) |
| wall effects never play | none were there: Ultimate's sword hit status plays the same catch / wind on a wall; its SpecialAirHiWallJump effect script turns REQ_EFFECT on at 6 and the status (f_7208a2ac80) plays `sys_cling` at a joint (EffectModule::req) | master_wire_catch / wind2 at the point the sword met (0x15B's main, a wall latch); at the cling's frame 6 a flash on that point: Smash 4 has no sys_cling, the common ledge-catch flash (sys_cliff_catch, 0x100001E) stands in (APPROXIMATED) |
| sounds | Ultimate's SpecialHiHit status plays se_master_special_h04 on every hit (after hit_disable_landing_frame / rewind_frame) | SpecialAirHiHit's sound script: se_master_special_h04 (0x1B00FB) at 0 when VAR_15 != 0 (a fighter or a wall), h03 at 2 as before |
| point-blank: no catch (clips) | clip 1 frames 140 - 184 and 300 - 360 (60 fps): Donkey Kong overlapping him, the tip's 0.01 % hit lands (training panel "Damage 0"), nothing caught, both fall to the floor. The tip pulls (master_vt_specialhi, 17 / 19) only took fighters 1 - 31 ahead of him; the soft catch measured the tip alone, far out by frame 20 | the tip pulls' box from 8 behind his front (-8 - 31); the soft catch measures the blade (four points from his hand to the tip) as well as the tip (Ultimate's sword stops on the first thing it meets); the catching hit's capsule from his hand ((0, 20, 6) - (0, 68, 24)) |

Checks: `tools/master_specials_test.py` 75 checks, 0 problems (v12: the reel's end and the overtake's place with and
without a waist read, a target on the ground, the catch / wall / cling effects and their places, point-blank catches,
the tip pull of an overlapping fighter, the hold through 11); port_check (v4 ... v9_fix, vars_reset_v1, v10_fix,
v11_fix, v12_fix): **0 ERROR**, 30 WARN (`scratchpad/byleth/pc_v12.log`); on v11's install the new rules give E14
(specialairhihit 0x347006E / 0x3470073) and S22 (0x15B Part 0). Hitbox Viewer (Shot.exe v1.7.2,
`scratchpad/byleth/v12/view/`): the catch effects' ids (a test copy of the effect script), the overtake on frames 1 / 4 /
11 (his body under the root, then over it; the hitbox under his feet, on the target). Built: the installed body scripts
= the port build's (compared), `python3 tools/master_build.py hi DIR` on them (idempotent; the specials step runs it
too), master.mscsb `master_build.compile_msc`. Package `scratchpad/byleth/make_pkg_v12_fix.py` (game.bin, effect.bin,
sound.bin, master.mscsb; TEST_ONLY: the diag master.mscsb only, with v11's TEST_ONLY exe: k12 his height over the
target's feet as the overtake starts, k13 its damage on the overtake's 11 - 13), INSTALL README
`scratchpad/byleth/INSTALL_README_v12.txt`. Not proven in game: the overtake's look with the target's own pose
(Ultimate's target is in a capture pose on his `throw`; here it is held in its hit pose), the waist joint read's
height per fighter, the cling flash's look; that the game shows no effect for a FOOT_EFFECT in the air is read from
the handler and the vanilla scripts (not traced who sets the +0x9F switch).

## Status: v11 (`scratchpad/byleth_v11_fix.zip`: a FIX package over v10; exe unchanged (exe_v46w_vars_line); in-game TEST)

User, v10 test with the TEST_ONLY diag (log `613f0faa-log.txt`, clip `6fac5f8c-...16164730639.mp4`, sheets
`scratchpad/byleth/v10/clips/d_o.png`, `d_w.png`): "the grab seems to catch but with no effect and doesn't pull Byleth;
the wall jump works better but is buggy".

| point | cause (evidence) | fix |
|---|---|---|
| catch: no pull, no effect | log attempts 2 / 3: k6 0.7 / 2.3 at frame 20, k7 3 / k4 3 at 21 (the MSC catch), k8 19033 -> 1033 (the 19-frame stop), then **k8 = 33 for the reel's 20 frames**: his height under the target never changes. The reel set kinetic energy 3's speed from the status loop every frame; it never moved him (v9's trim: he sank under it too), while speeds set in a status's main did (v9's wall jump flew off the top). After the 20-frame cap the overtake's hitbox swung 33 below the target. No catch effect: the catch had none (Ultimate's sword SpecialHiHit: master_wire_catch + master_wire_wind2 on the tip; the 3 % was added silently) | the reel moves him by his position (position_vars' self moves 0x0F000004 forward / 0x0F000005 up, 4.1 a frame; energy 3 kept 0); SpecialAirHiHit's effect script: master_wire_catch / master_wire_wind2 where the tip held the fighter (VAR_15 2); its game script: Ultimate's catching hit (3 %, no knockback) on the held fighter at frame 1 when there is no capture (VAR_11 > 0: its spark, sound, hitlag; MSC no longer adds the 3 % then). **port_check S21 loop-speed** (WARN: a loop moving the fighter by energy 3 speeds; v10's master.c: master_hi_hit_loop) |
| wall jump buggy | log attempt 4: k8 42 for 20 frames (the same reel), then k9 1001 - 1013 (the cling) and 1114 (the jump taken) to the motion's end; clip frames 529 - 676: after the cling he drops under the stage and is KO'd at the bottom: the jump's speeds, set from the loop, did nothing | the jump in 0x15C's main: the loop requests 0x15C again at the cling's end (master_hi_wj_jump), the main sets the fall kinetics, 2.6 up (gravity energy) and 0.9 away (air control), the motion kept at its frame, no extra wall jump counted (the loop also sets them, in case the game ignores a change to the status it is in); diag k10 the reel's distance left each frame, k11 the jump's re-entry |

Checks: `tools/master_specials_test.py` 67 checks, 0 problems (the model applies the self moves; the jump's re-entry);
port_check (v4 ... v9_fix, vars_reset_v1, v10_fix, v11_fix): **0 ERROR**, 30 WARN (`scratchpad/byleth/pc_v11.log`).
Package `scratchpad/byleth/make_pkg_v11_fix.py` (game.bin, effect.bin (the installed one + SpecialAirHiHit's), master.mscsb;
the TEST_ONLY diag as v10's with k10 / k11). Not proven: why loop-set speeds don't move him (the evidence is the two logs
and clips); that re-entering 0x15C from itself runs its main (if not, the loop's own speeds apply, as v10).

## Status: v10 (`scratchpad/byleth_v10_fix.zip`: a FIX package over v4 + byleth_userdata_v2 + v5_fix ... v9_fix + vars_reset_v1; exe unchanged (the user's **exe_v46w_vars_line**, sha1 bfd3b5b4...); in-game TEST)

User, v9 test (3 clips + a trim of clip 1, framed at 60 fps in `scratchpad/byleth/v10/clips/`; the TEST_ONLY diag log,
Cemu RPX hash 5838c778 = v9's exe_v46v_line_diag): up special still grabs nobody; its ledge box too large; the wall
cling broken; landing during the air down special near its hit still cancels it with no hit.

| point | cause (evidence) | fix |
|---|---|---|
| up special: nothing caught | **Log, attempt 1** (13:51:51, ground: frame-16 hit): the opponent goes 0 -> Damage (0x46) at the second line of frame 15 while Byleth's frame stays 15.0 - 15.21 for 7 lines (the hit's 7 hitlag frames: Ultimate's frame-16 1 % `top` hit, hitlag 1.4), then stays in 0x46 to frame 29; k5 (CatchModule 0x2712) 0 throughout. **Clip 2** (`v10/clips/c2a.png`, frames 52 - 62): the same hit (DK 0 -> 1 %) then DK leaves the top of the screen in 3 frames while the sword goes up empty. The cause: Ultimate's 368 + set_vec_target_pos (carry to (18, 44)) written as Smash 4's 366, which takes the hitbox's own per-frame motion; on bone 0 that is the body's (~0), its y raised to the common minimum (docs/native-notes.md "Special angles"): launched up, never in the tip's reach. **Clip 3** (`c3c.png`, frames 82 - 88): the ground up special under an airborne DK: the sword reaches his legs, nothing happens (no hitlag, no capture). **Log, attempt 2**: the tip met the stage at frame 18 (k2 31: kind 3, 6.3 from his hand, latched as a wall: k4 1) before the catch window: no catch test. The log "stopping" at n=98 is not a cap (`diag_godfist_cave.py` has none): v9's diag only logged in 0x154 / 0xF1, not in 0x15B. Exe side, read further: the catch is applied by the capturer's CatchModule vt +0x8C (`0x02C18DC8`) from a record inside the module (+0x1C: the victim's id at +0x34, the grab box index +0x43, built by the module's constructor `0x02C17F80`, 0x60 bytes) that the collision pass fills by a struct copy (no direct store found: the per-frame pass not traced); the victim's side: catchable = !(its status data & 0x800) every frame (`0x02E2528C`); Damage 0x46's pre (`func_788`: StatusModule(0x2713, 0, 0, 0, 0, ...)) leaves it catchable. So no exe reason was found to refuse; no capture ever came in game either (v8, v9) | (1) **the hits Ultimate writes at 368** take a plain angle toward their target (`master_build.pull_angles`: SpecialHi 16 -> 74, the tip's 0.01 % pulls -> 90; the up smash's 13 / 14 -> 110 / 67, the same bug class), the MSC pull carries them, now also in the air (0xF1, frames 17 / 19); **port_check S19 vec-pull-angle**. (2) **The catch without a capture** (`master_hi_soft`): Ultimate's catch is its tip hit (ENABLE_CATCH 20 - 25, the status code's set_catch); the grab box (0xBD) is tried first; a fighter whose body (feet + 4 to + 18) is within 10.5 of the tip (Ultimate's tip on his timeline, `master_tip_x / _y`) on two frames running (the grab box had the first), not intangible, not on a ledge, is caught by MSC: held where it is (position + collision 5 + a 3-frame hitstop rewritten each frame: it can't act), Ultimate's 3 %, SpecialAirHiHit (19 frames still, the rewind), the overtake's throw as a hitbox on it at frame 11 (Ultimate's ATTACK_ABS numbers: THROW 6.5 % 260 / 40 / 85 ground, CATCH 114 / 65 / 65 air, THROW_MEWTWO 260 / 110 / 14 air at 50 %+; VAR_11 1 / 2 / 3; the Throw_Applier branch only with a real capture). (3) The diag logs the catch's decision (k6 the tip's distance, k7 1 capture / 2 - 4 MSC catch) and 0x15B / 0x15C each frame (k8, k9) |
| up special: ledge box too large | the exe's ledge box (`0x02D62D74`, from GroundModule's use-box `0x02C36A34`): anchor = his position (the ground collision's +0x1D0) + (x along the facing, y); mode 0 front only [anchor, + w] x [y, y + h], mode 2 adds 0.6 w behind, mode 1 that alone; the mode is the status's cliff check kind (StatusModule(0x5) 4th value, `0x02C368B0`: kind 1 -> 0, 2 / 4 -> 2): AirCatch (func_123) checks in front only. Units: world units x the fighter's scale (ZSS's 1.0). ZSS's own (10, -10, 70, 60) = 10 - 80 in front, -10 - 50 up. v9's (0, 20, 44, 65) = 0 - 44 in front, 20 - 85 up: Ultimate's AIR_LASSO box (p1 (44, 85), p2 (-44, 20)) mapped like the normal box (only its front half), but **on all of 12 - 16**, while Ultimate's SpecialAirHi selects the AIR_LASSO box only at 15 (12 - 14: the normal box with HANG_IMMIDIATE: a ledge at his hands) | the box by frame in MSC (`master_hi_air_loop`): 12 - 14 vl entry 0 (Ultimate's cliff_hang_data[0], his normal ledge box), 15 - 16 entry 2; entry 2 = Ultimate's AIR_LASSO rectangle in world units for the front-only check: (-44, 20, 88, 65) (`ultimate_vl_shapes.tether_box`). Diagram: `scratchpad/byleth/v10/ledge/ledge_boxes_v9_v10.png` (five positions under / beside a ledge: A caught in both; C, the ledge 20 behind him, now caught on 15 - 16 as in Ultimate; B / D / E in neither). NOTE: Ultimate's box is wider than v9's (44 behind too); v10 matches it in world units and in time, the 3 extra frames of v9 gone |
| up special: wall cling broken | the user's trim (`v10/clips/t1d.png` .. `t1f.png`, 60 fps): 114 - 122 the start (facing left, the sword back-left), 123 turned right (TURN_CHECK); 126 - 127 the tip meets the underside of Battlefield's left overhang (log attempt 2: frame 18, kind 3, 6.3 from his hand, |ny| <= 0.934: latched); **128 the sword is gone** (the common AirCatch end func_127 removed the whip leaving 0xF1 for 0x15B); **128 - 159 he sinks** instead of being held and reeled up: kinetic type 0xA (AIR_STOP) keeps the gravity energy (1) running and the pull sets energy 3 only: the 12-frame stop drifts down, the 4.1 rewind loses to his fall speed until its 20-frame cap; **160 the wall jump from mid-air**, 30 frames late and far below the point, **not turned** (v9 asked the body's wall contact: none, so he kept facing the wall), its 2.6 up on energy 3, which nothing slows: clip 1 frames 380 - 390, off the top of the screen. Ultimate (f_7208a2b7d0 SpecialHiHit, f_7208a1fa60 / f_7208a1c840 / f_7208a2a8a0 / f_7208a2ac80 the wall jump): the sword stays on the point, 12 frames still, he is reeled at 4.1 until his hand is there; the wall jump turns him away (reverse_lr when the wall's angle is within wall_angle_min / max), clings 13 frames (wall_jump_stop_frame; its sounds: landing 5, jump 15), then jump_speed_x / _y 0.9 / 2.6 | the sword kept into 0x15B (`master_hi_air_end` skips func_127 there; **port_check S17 tether-latch**); no fall while held (gravity speed 0 + the energy suspended: KineticModule 0x2717 / 0x2718, Captain Falcon's own pair, kinetic_module_impl `0x02C52CEC` / `0x02C52F0C`; resumed at 0x15B's end, after the overtake's throw, the wall jump's jump; **port_check S18 pull-gravity**); the reel puts his hand (the line test's start, 5.5 / 20.5) on the point; the wall jump from a latch: reverse_lr, 13 frames' cling (his motion's root: 24 up, back to the wall), then 2.6 on the gravity energy and 0.9 on air control (both slow as a jump's do) |
| down special: landing near the hit | Ultimate's SpecialAirLw: INHERIT_LANDING_1 0 - 51, **KineticModule::add_speed (0, 1, 0) at 53** (a hop), FORBID_LANDING 60 - 65 (the axe hit 61 - 67 with him in the air), INHERIT_LANDING_2 65 - 117. The translator drops add_speed (no ACMD for it): no hop, so he landed inside 53 - 60 -> SpecialLwLanding2 (no hit); 60 - 65 went to the ground motion at its frame (a new script started there: whether it still gives the hit it starts past is not shown; the air one keeps it for sure) | the hop in MSC (gravity y + 1 at 53, once); landed from 53 to the hit's end (67): the air motion and its script go on (the hit comes out), the axe meets the floor at 64 -> SpecialLwHit as before; 51 - 53 Landing2, < 51 / 67 - 117 the ground motion, 117+ Landing1. **port_check S20 add-speed** (an Ultimate game script's own movement not done in MSC) |

Not proven offline: that the game's grab pass ever captures from his statuses (no capture in any test so far); the MSC
catch does the move without it. The MSC catch's reach (10.5 from the tip to the body line) is mine (Ultimate's catching
hit's 5.5 + about half a body). Ultimate's wall_offset (-0.6, -0.8) and tip_angle_wall 70 (the sword's pose on the wall)
and the sword's length (canned extend: on a short latch it keeps growing through the wall during the stop, then goes
back while he is reeled) not reproduced. The normal ledge box on 12 - 14 is checked in front only here (AirCatch's kind 1;
Ultimate's is both sides: 9.6 behind).

Built: `ultimate_port.py run master scripts specials variants shapes --out OUT` (`scratchpad/byleth/pipeline_v10.log`);
master.mscsb `master_build.compile_msc`; body effect.bin kept as installed (the run's variants step now folds the bone
rotations of Aymr's flares into variant ids 0x34700A4 - A6, which v9's shipped effect.bin doesn't: not in v10's scope,
`scratchpad/byleth/v10/effect_pipeline_v10.bin` kept to compare; the bank is unchanged). Package
`scratchpad/byleth/make_pkg_v10_fix.py` (game.bin, master.mscsb, the vl; TEST_ONLY exe_v46w_vars_line_diag
(diag_godfist_cave over the user's exe, sha1 719e23d1...) + the diag master.mscsb); INSTALL README
`scratchpad/byleth/INSTALL_README_v10.txt`. Checks: `tools/master_specials_test.py` 65 checks, 0 problems (v10: the
latch keeps the sword, the held fall, the reel to the hand, the wall jump's turn / 13-frame cling / jump, the catch
without a capture and its hold to frame 11, not a far / intangible / shielding fighter, the ledge box by frame, Aymr's
landings and hop); `tools/kinetic_suspend_test.py` (unicorn on exe_v46w_vars_line: 0x2717 / 0x2718 set / clear energy
1's +0x19); `tools/diag_godfist_test.py exe_v46w_vars_line.rpx exe_v46w_vars_line_diag.rpx` (0 failed); Hitbox Viewer
(Shot.exe v1.7.2, `scratchpad/byleth/v10/view/`): SpecialHi 16 the 1 % hit at 74 degrees (launch 1.2 a frame, 15 hitstun
frames: the pull's 7 frames hold it), the overtake's frame 11 hitbox (THROW_MEWTWO 260 / 110 / 14, 9 around his hand).
port_check (`byleth_v4 ... byleth_v9_fix, vars_reset_v1, byleth_v10_fix`): **0 ERROR**, 30 WARN (`scratchpad/byleth/pc_v10.log`);
on v9's install S19 (AttackHi4 13 / 14, SpecialHi 16); on v9's master.c S17, S18 (0x15B, 0x15C), S20 (SpecialAirLw).

## Status: v9 (`scratchpad/byleth_v9_fix.zip`: a FIX package over v4 + byleth_userdata_v2 + v5_fix ... v8_fix; exe **exe_v46v_line** (exe_v46v_threads + `tools/line_test_cave.py`); in-game TEST)

User, v8 test (3 clips, framed at 60 fps in `scratchpad/byleth/v9/clips/`): up special grabs nobody and doesn't pull him;
the ledge grab "very specific" (not Ultimate's wide area); no pull to walls, the whip passes through them; "check
Ultimate's code for how up special works"; no turn into the held direction, no B-reverse; down special's camera zoom
missing on a hit; the smash-charge orbs wrong.

| point | cause (evidence) | fix |
|---|---|---|
| up special: nothing caught | clip 1 (`v9/clips/c1_z1.png`, `c1_z2.png`, `c1_hud.png`: clip frames 86 - 117): the tip reaches DK at clip frame 90, DK's percent goes 120 -> 123 at 93 (one 3 % hit, `c1_hud.png`), the hit sparks 94 - 98 (hitlag) and DK is launched with the smoke trail; clip 2 (ground, `c2_sheet1.png`): DK 0 -> 1 -> 4 %, launched. v8's grab box (frames 20 - 25) shared frame 20 with Ultimate's 3 % hits on the tip (ID 0 / 1, HitBits 0x1F / 0x3F: they hit fighters): the hit took DK first and the grab box never caught it, also not through DK's 6 hitlag frames inside it. The exe side read: a catch goes through the capturer's CatchModule (vtable `0x10104410`, vt +0x8C `0x02C18DC8`: the victim's CaptureModule vt +0xBC gets the grab box's TargetStatus `+0x1E` and flag `+0x26`); the capturer's status isn't asked there (Falcon's / Ganondorf's dives catch from their 0x154, same status data as ours); the fighter's catch event (event 8, `0x02E31F68`) only moves Catch / CatchDash / CatchTurn to CatchPull. Not traced: the per-frame pass that orders hits and grabs (the hit-first reading is from the clips; the diag build logs it if it still fails) | `master_build.no_release`: the hits over the catch frames (20 - 25) keep NoGrabRelease and lose HitBits bit 0 (items / gimmicks only), so the grab box is the only thing touching fighters there; `master_hi_catch` adds Ultimate's catching hit's 3 % to the caught fighter (its damage variable); 0x15B now holds `hit_stop_frame_fighter` 19 frames before the rewind (Ultimate's ShakeModule stop), the sword going back at 19 (`hi_hit_script`, VAR_15). **port_check S14 grab-vs-hit** (ERROR: a grab box out with a fighter-hitting hitbox; v8's install: aircatch / specialhi frames 20 - 24) |
| up special: the ledge "very specific" | the box check (the common AirCatch's func_99 with flag 0x2100000D) ran on ZSS's zair frames 0 - 5 (aircatch: ON 0, OFF 5), before his sword is out (17): only the whip tip's native latch could take a ledge; the box was ZSS's tether box (vl group 7 entry 2: (10, -10, 70, 60)) | the flag on Ultimate's AIR_LASSO_FLAG_CHECK (12 - 17); the tether box Ultimate's cliff_hang_data[3] (FIGHTER_MASTER_CLIFF_HANG_DATA_AIR_LASSO, selected at SpecialAirHi frame 15: p1 (44, 85), p2 (-44, 20)) -> (0, 20, 44, 65) (port.json `tether_ledge_box`, `ultimate_vl_shapes.py --tether`; Smash 4 takes the reach behind as 0.6 x 44 = 26: APPROXIMATED against Ultimate's 44). **port_check S16 tether-window** (ERROR on v8's install: 0 - 5 vs the whip at 17) |
| up special: walls | no stage test from the sword (v8: "the wall check is still his body's") | **a line test in the executable** (`tools/line_test_cave.py`: the game's GroundModule ray_check `0x02C39FB4`, as a new ACMD command `Line_Test` and the MSC variables `LINE_*`, `docs/acmd-extra-commands.md` "Line_Test"); `master_hi_line`: frames 17 - 26 (EXTEND to BACK), from his hand (5.5 forward, 20.5 up) to the next frame's tip (Ultimate's sword tip on his timeline, `master_whip.py tips`: (7.5, 22.4) at 18 ... (22.6, 64.9) at 25), passable platforms left out. A wall (its normal within Ultimate's wall_angle_min / max, +-69 degrees) with wall hits left (wall_hit_max 3) -> 0x15B latched: the sword stays (hit_stop_frame_wall 12), then he is rewound at rewind_speed 4.1 until his hand is at the point, then the wall jump 0x15C (jump 0.9 / 2.6); a floor / ceiling (or no wall hits left) -> stopped: the sword goes back at once, Fall at the motion's end. The body-touching-a-wall jump is gone (Ultimate's only comes from the sword). Ground and air |
| max arrow through walls | the line hitbox and beam always 300 long (v8: "not cut at the first ground") | its game / effect scripts start with `Line_Test(0, 0, 0, 300, 0, Floors 1, VAR_0)`: the three capsules end at the distance (10-unit steps, `master_build.arrow2_buckets`), the beam's pieces only where the line goes, the head and end flash at the cut. **port_check S15 line-cut** (WARN: a long article line hitbox with no Line_Test), **X6 line-test-exe** (ERROR: Line_Test with no executable carrying it) |
| no turn / B-reverse | his loops had no turn code | Ultimate's (lua2cpp f_7208a2f5e0, read below): on TURN_CHECK (frame 8) once, the stick back past status_start_turn_stick_x 0.3 turns him (momentum kept); B-reverse (mine: frames 0 - 3, Ultimate's is the common special start's): the stick back turns him and flips his air momentum (energies 2 / 3), once. Ground and air (`master_hi_turn`) |
| down special: no zoom | not done (README v1: "Aymr's KO zoom") | `master_lw_crit` (every frame from func_82): Ultimate's param_special_lw critical_* (critical_frame 40, slow 4, 1-on-1 only), as Hero's critical hits: the move's first hit in a 1-on-1 with a KO-strength hit slows the game to 1/4 for 40 frames (SlowModule) and closes the camera in (ITEM variable 8, back with 9). The KO test APPROXIMATED: the hit's hitstun >= 56 (knockback 140); Ultimate's own is its cut-in's KO check (ExeFS, not read); its zoom rate 4.6 / offset (3, 1.5) / darkened background (bg_only_frame 30) not reproduced (Camera_Closeup's fixed call) |
| smash-charge orbs | the hold effect scripts were still ZSS's (the translator has no Charge -> Hold names): her flash (his bank's sys_smash_flash_s copy, 0x3470091) on RHaveN at (0, 1.5, 2), the same in all three smashes, size 1 random 4 | Ultimate's AttackS4Charge / AttackHi4Charge / AttackLw4Charge translated into attacks4hold / attackhi4hold / attacklw4hold (`master_build.smash_hold_fx`): sys_smash_flash_s on haver (RHaveN) at Areadbhar's head (0, 24, 0), the sword (0, 6, 1), Aymr's head (0, 16, 1), random 3, every 10 frames with the dust. Colour: the same emitter set as Ultimate's (his bank's copy of sys_smash_flash_s, no script colour in Ultimate's). Brightness: no halo added (the bloom clip of v8's cause 2 applies; xv2_smash_fx's HALO_ALPHA / HDR_CAP halos to tune in game: Handover). The orbs are non-following, short (no leak: E12 clean). **port_check E13 smash-hold** (ERROR: holds identical to the base's; v8's install: all three) |

### Ultimate's up special (status code: lua2cpp_master, read with `tools/recomp_annotate.py` / `recomp_hashes.py`)

- **Scripts** (SpecialHi / SpecialAirHi): rate 0.3 over 1 - 10; TURN_CHECK on at 8; (air) AIR_LASSO_FLAG_CHECK on 12 - 17,
  HANG_IMMIDIATE 12 - 15, the AIR_LASSO cliff box selected at 15; a search box at 15 (air fighters above-ahead,
  cleared at 16); the sword EXTEND at 17; hits on `throw` (the sword tip) 17 - 21: ID 0 0.01 % angle 368 to (16, 40)
  above him (the pull), ID 1 3 %; ENABLE_CATCH at 20 with ID 0 3 % (the catching hit); clear at 25; BACK at 27.
- **Main loop** (f_7208a2f5e0): the cancel / wait / fall checks, the cliff catch (GroundModule is_status_cliff /
  can_entry_cliff / hang_cliff_dir, set_rhombus_modify_air_lasso, select_cliff_hangdata, set_cliff_check), the turn:
  `if TURN_CHECK and not TURN_DONE: if stick_x x lr <= -common.status_start_turn_stick_x (0.3): reverse_lr,
  update_rot_y_lr; TURN_DONE on` (once), the start speeds (sub_exec_special_start_common_kinetic_setting
  param_special_hi: start_speed_x_mul_air 0.7, start_speed_y_air 1.4, start_brake_x_air 0.01, ...).
- **Init** (f_7208a1e220): start_speed_y_air_dec, the map collision point: map_coll_joint `hip` + map_coll_offset
  (0, 8, 8) into the ground shape (set_shape_data_rhombus_modify_node_offset), the air lasso's rhombus.
- **SpecialHiHit** (f_7208a2b7d0): a caught fighter: CatchModule::set_catch (Smash 4: the grab box's capture),
  the hit pose (special_(air_)hi_hit_pose), the stop (ShakeModule req_time_scale: hit_stop_frame_fighter 19 /
  _wall 12 / _item 12), the sword told rewind_speed (4.1) and the angle (tip_angle_object -15 / tip_angle_wall 70);
  a wall: GroundModule get_touch_normal, wall_offset (-0.6, -0.8); then the overtake (overtake_stop_frame 3, its
  throw by TARGET_AIR / TARGET_HI_DAMAGE: overtake_attack_damage 50) or the wall jump (f_7208a1fa60 / f_7208a1c840 /
  f_7208a2a8a0 / f_7208a2ac80: the wall within wall_angle_min / max -69 / 69, wall_jump_stop_frame 13, jump_speed_x /
  _y 0.9 / 2.6, wall_jump_speed_x_mul 0.9, sys_cling; wall_hit_max 3 an airtime). The wall / ground contact itself is
  the sword article's (its own statuses' map test from its tip, not read in detail): here the line test from his hand.
- **Not reproduced:** the sword's variable length (Smash 4 plays canned extend / back motions: it stops by the status
  change on the frame before the tip would cross the line), tip_angle_*, the search box's use, HANG_IMMIDIATE's box.

Built: `ultimate_port.py run master scripts specials variants shapes --out OUT` (`scratchpad/byleth/pipeline_v9.log`),
master.mscsb `master_build.compile_msc`. Exe: `python3 tools/rpx_patch.py exe_v46v_threads.rpx exe_v46v_line.rpx
$(python3 tools/line_test_cave.py --rpx exe_v46v_threads.rpx)` (sha1 in INSTALL README); with exe_v46w_vars
(tools/var_reset_cave.py) the order is var_reset first, then line_test (docs/native-notes.md "Stage line test").
Checks: `tools/master_specials_test.py` (42 checks, 0 problems: the catch's 3 %, the 19 / 12 stops, the line test's
latch / stop / nothing / facing left / ground, the turn rules, the B-reverse, Aymr's critical); `tools/line_test_test.py`
(unicorn on exe_v46v_threads 29 checks, on exe_v46w_vars 31, 0 failures); Sm4shCommand v1.7.3 (`new_var_test.cs`: 205
checks, Line_Test's 4 examples compile and round-trip). Diag: `TEST_ONLY_INSTALL_TO_code` exe_v46v_line_diag (+
`tools/diag_godfist_cave.py`: S4GF lines) with a diag master.mscsb (`compile_msc(..., diag=True)`, master.c
master_diag: k 0 frame, 1 a fighter near (slot x 1000 + status), 2 / 3 the line test, 4 the hit mode, 5 holding).
Package `scratchpad/byleth/make_pkg_v9_fix.py` (5 fighter files + the vl + the exe + the TEST_ONLY diag), INSTALL
README `scratchpad/byleth/INSTALL_README_v9.txt`. port_check (all seven packages): **0 ERROR**, 30 WARN
(`scratchpad/byleth/pc_v9.log`); on v8's install the new rules give S14 (aircatch / specialhi 20, 21, 25), S16
(0 - 5 vs 17), E13 (all three holds) and S15 (the max arrow's 300-unit capsules). Hitbox Viewer (v1.7.3, Shot.exe):
the smash holds' orbs before / after (`scratchpad/byleth/v9/view/`).

## Status: v8 (`scratchpad/byleth_v8_fix.zip`: a FIX package over v4 + byleth_userdata_v2 + v5_fix + v6_fix + v7_fix; exe unchanged (exe_v46v_threads); in-game TEST)

User, v7 test (3 clips + an effects comparison, framed at 60 fps in `scratchpad/byleth/v8/clips/`, `v8/fxcmp/`): the
fully charged neutral special "doesn't spawn its line and doesn't have a hitbox" (the uncharged arrow works); up special
should match Ultimate (the tip a real grab: opponents, ledges, walls); the charge effect "continues into other actions if
the special button is held"; the glows weaker / effects darker than Ultimate's (side special, up / forward / down smash).

| point | cause (evidence) | fix |
|---|---|---|
| max arrow: no line, no hit | clip 2 (`v8/clips/sb2.png`, `sb3.png`: frames 150 - 160): the body's shot flash (master_bow_arrow2_shot, its script) plays at the bow, nothing beyond it, DK (~70 units off) untouched. v7 changed only arrow2's effect.bin and the vl (charged speed 0x02000001 75, life 4); its game.bin / MSC were v6's. The shot is ZSS's Paralyzer bullet moved by her NATIVE specializer, which takes the charged speed only for her own charge flag (arrow2's MSC forces the charged branch of its status, not the native speed: v1's note "if the native shot fires the max arrow uncharged it flies 153 units"): 9 a frame for 4 frames = 36 units, then removed, its 1.2-radius hitbox and the bullet / beams (frames 0 - 3) inside the 30-unit shot flash. And at 75 a frame its hitbox would step 60 radii a frame: no reliable hit (`port_check` W15 on v7's install: ERROR, arrow1 and arrow2 both: the shot's speed block is shared) | `master_build.arrow2_line`: the arrow stands still (charged speed 0, life 10 = the beam set's) and its game script is Ultimate's three ATTACKs (29 %, 361, 56 / 53, 1.2, lateral -2 / 0 / 2) as capsules from it to param_arrow2 distance 300 along its facing, frames 0 - 1 (one line over the path, as set_search; the native shot is removed on its first hit: everyone in the line that frame is hit); its effect script: master_bow_arrow2 pieces every 10 (param_arrow2's 10: the set is 9.5 long, x effect_max_scale 1.055) from effect_max_offset_x 8 to 300, the bullet and end flash at 300 (non-following: they outlive the arrow). **Not cut at the first ground** (Ultimate's GroundModule line test: no MSC / ACMD line test found; APPROXIMATED), no master_bow_arrow2_hit on the victim (Ultimate's hit effect comes from its collision attribute: not mapped) |
| charge glow leaks | clip 3 (`v8/clips/sc2.png`, frames 209 - 266): after the shot the rings and cyan sparks stay on his hands into the wait. master_bow_hold2 (frame 49 of the draw: particles living 100 frames, arrowFlare / arrow / flare2_alpha) and master_bowflare2 (frame 0, 120) follow his hand; only the draw's frame 118 (hold2) and the shot's script (bowflare2) end them, emission only. Smash 4 ends a following effect neither at a motion change (Terminate=1) nor a status change; Ultimate removes the held arrow / bow articles that carry them (`v8/leakscan2.py`: the body scripts' following effects that outlive their move) | `master.c` `master_n_fx_off` (EffectModule(0x2723, id, 1, 1): particles too) at the shot / max shot / shield cancel, `master_n_end` (0x152's end), `master_fx_sweep` (from `master_whip_sweep`, every status change: leaving 0x152 Failnaught's, leaving 0x155 Aymr's flares / aura / hold, and always the sword flares, neutral air's and (but into the rapid jab) its lines: the endless ones a hit or a grab left on). **port_check E12 effect-leak** (v7's install with v7's master.c: ERROR master_bowflare2 / master_atk_100, WARN 10 more (hold2, the axe flares, the sword flare, neutral air's, the axe rocks); v8: none). Aymr's rocks (SpecialLwHit, detached at 60) killed when the move is left before 60 (`master_lw_end`) |
| up special: the catch | v7 held "the nearest fighter in hitstop" by writing its position: no capture | a real grab (Ultimate: ENABLE_CATCH from 20, clear at 25; the hit on `throw` catches, the overtake's ATK_HIT_ABS throws it): `master_build.tip_catch` puts an Extended_Grab_Collision where the hit ID 0 is (ThrowN on the sword's tip, its capsule and size: 4.5 air / 5.5 ground), frames 20 - 25, TargetStatus 0xBD (the Falcon Dive capture: the victim faces him, plays its capture pose and stays where it was caught while the capturer never calls CatchModule(0x2710), as Ganondorf's Dark Dive, docs/ganon-dark-dive.md); the hits over 20 - 25 get NoGrabRelease (`no_release`). The game changes the capturer's status only from Catch / CatchDash / CatchTurn (0x02E31F68: CatchPull / CatchDashPull; any other status is left alone), so `master_hi_catch` asks every frame of 20 - 26 (air 0xF1 and ground 0x154): a fighter in 0xBD within 125 -> 0x15B, Ultimate's TARGET_AIR (its situation) and TARGET_HI_DAMAGE (its damage >= overtake_attack_damage 50: APPROXIMATED, the flag's test is ExeFS code) into VAR_12 / VAR_13. 0x15B: pulled at rewind_speed 4.1 a frame (v8: the true distance, v7's |dx| + |dy| was slower on diagonals; the last step no longer zeroed on the same frame) until his hand (fighter_offset 8) is at it, then the overtake: the common Throw's thrown link event (0xB, ThrownF 0x7C) and work int 0x11000005 (`master_hi_throw`); its game script (`master_build.overtake_throw`): THROW (260, 40 / 85) and CATCH (114, 65 / 65) at frame 0, at 11 Throw_Applier by VAR_12 / 13, THROW_MEWTWO (260, 110 / 14) set in its branch (the translator had put it in the THROW slot for every case). Ends let go of a fighter still held (`master_hi_hit_end`, `master_hi_end`, `master_hi_air_end`). A hit before 20: just a hit (Ultimate: no SpecialAirHiHit) |
| up special: ledges | the common AirCatch ledge catch is back since v7 (func_99, in front of his body) and ZSS's native tether latch runs between the whip's HaveN and AttachN, AttachN on the sword's tip (v6), from WhipShoot (frame 17): the tip latches, her native AirCatchHit / hang pull him to the ledge. Ground up special: none (Ultimate's ground script has no AIR_LASSO flags) | unchanged (not testable offline) |
| up special: walls | the wall check is still his body's (GroundModule 0x2722 2 / 4); Ultimate's sword-tip wall hit (SpecialAirHiHit pose, wall_offset, hit_stop_frame_wall 12, then the wall jump) needs a line test from the hand to the tip: none reachable (GroundModule's MSC ops not mapped; the Wii U ray_check 0x02C39F18 has no MSC op found) | **not done** (Handover) |
| glows weaker | effects comparison (`v8/fxcmp/side_special_ours_vs_ult.png`: ours top, Ultimate bottom): Ultimate's side special lights Byleth red (frames 37 - 46), the bow's draw / max shot and Aymr's aura light him too; those are eft2 lights on emitters Ultimate doesn't draw (is_particle_draw 0: master_spear_aura pointlight1, master_bow_hold2 / bow_arrow2_shot pointLight, master_bow_flash flare2, master_axe_aura pointlight1, master_win_wire_flare2): `vfxb_to_ptcl` skipped them whole. Second cause, not fixed: Ultimate's bloom of HDR colours (master_smash_hi's emitters at colour scale 2 - 6: the up smash's blue glow ball, the spear's flares) where an own pixel program clamps to 1 | `vfxb_to_ptcl.py` LIGHTS_UNDRAWN: such an emitter kept as a black, added particle carrying the light (every port at its next effects build). The bloom: Handover (fake halos as `tools/xv2_smash_fx.py`'s, tuned in game) |

Built: `ultimate_port.py run master scripts specials variants shapes --out OUT` (`scratchpad/byleth/pipeline_v8b.log`).
Package `scratchpad/byleth/make_pkg_v8_fix.sh` (the install rebuilt as v7's + byleth_v7_fix.zip, every file of the build
that differs; the vl into data and data(us_en)); INSTALL README `scratchpad/byleth/INSTALL_README_v8.txt`.
Checks: `tools/master_specials_test.py` (the compiled MSC in rolloff_hold_test's interpreter: 20 checks, 0 problems);
Hitbox Viewer (Shot.exe, `scratchpad/byleth/v8/shots/`): the air up special's tip hitbox at game frame 14 (anim 21) ~50
above him; the viewer draws hitboxes, not grab boxes: the grab box is hitbox ID 0's bone / offsets / size by
construction (`tip_catch`). port_check `byleth_v4.zip byleth_userdata_v2.zip byleth_v5_fix.zip byleth_v6_fix.zip
byleth_v7_fix.zip byleth_v8_fix.zip`: **0 ERROR**, 29 WARN (v7's), `scratchpad/byleth/pc_v8.log`. The effect ids after
master_win_wire_flare2 moved up by one (its set, empty before, now holds its light): the bank, every effect script and
the whip's effect.bin ship together; master.c's literal ids follow master_effects.json (E8). Not tested in game: the
catch (that the game links a grab box's victim while the capturer stays in a non-catch status, as for Falcon's and
Ganondorf's dives; that 0xBD's pose suits), the light-only particles (drawn black and added: if a dark shape shows, the
universal program ignores the colour keys), the stationary max arrow's line (Ultimate's ground cut not done).

## Status: v7 (`scratchpad/byleth_v7_fix.zip`: a FIX package over v4 + byleth_userdata_v2 + v5_fix + v6_fix; exe_v46v_threads; in-game TEST)

User, v6 test (4 clips, 3 screenshots; framed at 60 fps in `scratchpad/byleth/v7/clips/`): colours / effects / trails too
dark; side special snaps back to where it started; up special grabs no ledge / wall / fighter, pulls him to the wrong
place, ends in special fall; grounded down special has no floor impact and acts as the air one, landing during the air
one near its hit frame cancels it; the charged arrow far too slow, most of its emitters and its beam missing, no hit
effect. Their Ultimate reference: `images/23.png` (training, idle) against `images/20.webp`.

| point | cause (evidence) | fix |
|---|---|---|
| side special snaps back | Ultimate's special_s_front / air: motion_list flags 0x84 (move), its Trans 11 (air 14) forward over frames 0 - 18 (d01specialsf.nuanmb); extra_kinds.json gave slots 0x22E / 0x232 flags 0x0 (ZSS's 0x22E had 0x4): Smash 4 drew the root's translation as an offset and dropped it at the end. Same in the wall jump 0x23C (Trans 25 up / 8 back, Ultimate 0x84) | flags 0x4 on 0x22E / 0x232 / 0x23C (exe_v46v). **port_check M12 root-motion** (ERROR; v6's install: 3) |
| up special: no ledge | his 0xF1 loop (master_hi_air_loop) replaced the common AirCatch loop (func_126) without its ledge catch (`func_99() == 1 && 0x2100000D -> 0xF2`) | the test back in his loop; **port_check S13 tether-ledge** (ERROR on v6's master.c) |
| up special: special fall | master.c sent every end to 0x10 (FallSpecial) and landings to 0x19 | Fall (0xE) and LandingHeavy (0x16) everywhere (ground, air, hit, overtake) |
| up special: the hit / pull | v6 pulled him toward where the tip was on the hit frame (a table), the fighter left to fly | `master_hi_find` (the other fighter in hitstop nearest him, within object_dist_max 55 + reach 70), `master_hi_rewind`: the caught fighter held where it was caught (position_vars, as the vec_target pulls), him pulled at Ultimate's rewind_speed 4.1 a frame until his hand (param_sword fighter_offset 8) is at it, then the overtake hit (cap 20 frames, mine) |
| down special on the ground | Ultimate's SpecialLw sets the axe's PIERCE_GROUND at 64 - 65: the axe meets the floor -> SpecialLwHit (the axe stuck, 4 ground shock hits 8 % at its frame 2, the ground's landing effect, master_axe_rock); v1 - v6 had no SpecialLwHit (no slot): the ground one played on as the air one | new slots 0x242 SpecialLwHit, 0x243 / 0x247 SpecialLwTurn / air (exe_v46v; Ultimate's scripts, the axe's merged); master.c: grounded at 64 -> 0x242; TURN_CHECK 12 - 42 with the stick back -> the turn, once |
| down special: landing near the hit | master.c sent landings at 51 - 65 to SpecialLwLanding2 (no hit); Ultimate's FORBID_LANDING (60 - 65) keeps the move going | 60 - 65: the ground motion at its frame (its hit, then the floor hit); 51 - 60 still Landing2 (Ultimate's INHERIT_LANDING_1 ends at 51) |
| charged arrow: speed | Ultimate's arrow2 doesn't fly: its Search status calls the ExeFS's `WeaponSpecializer_MasterArrow1::set_search` (main.bin 0x03443100: param_arrow2 distance 300 x scale, cut at the first ground by a GroundModule line test, one attack line over the whole path); v1 - v6 flew it at 10 a frame for 30 frames (mine) | 300 in 4 frames (75 a frame, `master_build.ARROW2_LIFE`) |
| charged arrow: beam / emitters / hit | master_bow_arrow2 (the beam), _bullet, _end, _end2, _abs, _hit and Aymr's master_axe_impact / _ground are requested by status / native code only (`recomp_hashes`: f_7208a04340 set_arrow_max_effect, f_7208a050e0, f_7208a052f0): init took the ACMD's sets, so none was in the bank | the 8 sets in port.json effects.own (bank rebuilt); the arrow's effect script: the bullet on it, the beam left at each frame's point (Ultimate stretches one beam: APPROXIMATED), the end flash. **port_check E11 status-effects** (WARN) |
| colours too dark (model) | `ultimate_fighter.templates` takes the base's first 0x9A011063 material: on ZSS that is Mouth_Ouch (fresnel 0, AO floor 0, specular exponent 1; her suit is a reflective 0x9801106b): every Byleth part drew with no rim, its AO down to black, one flat lobe; and the reflectance ignored PRM metalness (his armour, F0 ~ albedo, took 0.16 spec^2) | `rim_from_body`: rim / specular / AO floor / exponent from the base's main body material (ZSS's suit Gamemodel: rim 0.75, specular 1.5, AO floor 0.05, exponent 10), scaled by Ultimate's reflectance as before; `reflectance` takes metalness. Other ports: only a base whose 0x9A011063 template has no rim changes (Zelda's has rim 0.91: Sephiroth unchanged) |

Not done / approximated (v7): the effects' darkness in game (fx_render draws master_axe_slash bright; the dark streaks are
its `_sub` emitters, a subtractive layer in Ultimate too: to compare with an Ultimate clip of the move); the wall tether
(Ultimate's sword tip meeting a wall: the wall check is still his body's, no line test in MSC); the dash Areadbhar
(SpecialSFDash: no slot); SpecialLwCancel / SpecialAirLwHit (the air axe meeting the floor: no ray test); the hair's
skin-path material (CustomVector30) still lighter / greener than Ultimate's.

Executable **exe_v46v_threads** (`scratchpad/byleth/v7/exe/exe_v46v_threads.rpx`, sha1
ce5edb1df6c17a4da4c64d8bc1e285a991972575) = the user's exe_v46u_threads (sha1 c131ea41...) + 9 motion-table words
(`kind_expand_incremental.py build exe_v46u_threads.rpx EXTRA_KINDS_V6.json tools/extra_kinds.json ARGS --list
0x47=0x04B9C728`, ARGS without kirby_copy_pool_cave's 0x04BA9B24 / 0x04BA9BE4): flags 0x4 on 0x22E / 0x232 / 0x23C, anim
hashes FitSZerosuitBodyMainD03SpecialLwHit / SpecialLwTurn / SpecialAirLwTurn on 0x242 / 0x243 / 0x247 (flags 0).

Build: `ultimate_port.py run master model-c00 .. model-c07 motions motions-group2 low-models effects scripts specials
variants shapes --out OUT` (`scratchpad/byleth/pipeline_v7.log`). Package `scratchpad/byleth_v7_fix.zip`
(`scratchpad/byleth/make_pkg_v7_fix.sh`: the install rebuilt from the four zips, every file of the build that differs, a
changed model.nud with its model.nut (M5), the vl into data and data(us_en), cross_f.rpx; 61 fighter files + vl + exe),
INSTALL README `scratchpad/byleth/INSTALL_README_v7.txt`. port_check `byleth_v4.zip byleth_userdata_v2.zip
byleth_v5_fix.zip byleth_v6_fix.zip byleth_v7_fix.zip`: **0 ERROR**, 29 WARN (v6's), `scratchpad/byleth/pc_v7.log`; on
v6's install the new checks give M12 x3 (0x22E 11.0, 0x232 14.0, 0x23C 24.7) and S13 (v6's master.c). Hitbox Viewer
(Sm4shCommand v1.7.2 rebuilt with the new names, Shot.exe: `scratchpad/byleth/v7/shots/`): SpecialLw 62 the axe's 30 %,
SpecialLwHit 3 the floor shock hit (8 %, 88 degrees) with the axe flares, 56 master_axe_rock. Not run: the new MSC in
a unicorn / game test (compiles; C1 stack check passes); the material change was checked by its parameters only (no
Smash 4 shader render here).

## Status: v6 (`scratchpad/byleth_v6_fix.zip`: a FIX package over v4 + byleth_userdata_v2 + v5_fix; in-game TEST)

User, v4 / v5 tests: up special "not appearing / functioning" (twice), the whip moves without their blade, "etc".

| point | cause (evidence) | fix |
|---|---|---|
| up special hits nothing at the whip | Ultimate's SpecialHi / SpecialAirHi put every hitbox on `throw` (frame 17 (2, -1, -1), 19 - 21 capsules down the blade), a joint its status code keeps on the sword's tip: his body animations hold Throw at the origin (d02specialhi frames 0 - 27: (0, 0, 0)). Translated as they were, the hitboxes sat at his feet (the Hitbox Viewer and port_check S12 on v5: ERROR) | `master_whip.bake_throw`: D02SpecialHi / G04AirCatch (body and body2) get a ThrowN track on the sword's tip (sword_null) on Ultimate's timeline (special_hi(_air)_start from 1, EXTEND at 17, BACK at 27: his game scripts), its rotation kept: frame 17 (z 6.9, y 17.5), 21 (17.7, 52.5), 25 (22.5, 64.9). **port_check S12 throw-joint** (ERROR: hitboxes on ThrowN in a move whose animation keeps it at the root) |
| no whip anywhere (v1 - v5: ZSS's whip copy, model hidden) | the `sword` article was never built | **`tools/master_whip.py`** (below): Ultimate's sword article on his whip article (ZSS's copy, kind 0x1A0, article 2) |
| the air hit's pull | v1 - v5 pulled 1.15 / 2.85 a frame for 14 frames whatever the hit | `master.c` `master_hi_pull`: toward where the tip was on the hit's frame, from his hand, at Ultimate's `rewind_speed` 4.1 a frame (`object_dist_max` 55): `master_whip.py tips` |
| v5's stand-in (body sword shown with the whip moves) | `master_build.WEAPONS['SWORD']`, `ultimate_fighter.VIS_ALSO['master_sword']` | removed: his sword follows Ultimate's own `master_sword` track (hidden while the article is out); `master_build.SWORD_VIS` keeps it where the whip has no slot or another timeline (the air tether: shown 0 - 17 and from 35; Win3 and his Final Smash animations: shown, approximated) |
| a whip left out after an interrupted move | an article outlives its status (ZSS's own ends removed hers: func_2275 - 2277) | `master.c` `master_whip_sweep` (per frame): article 2 removed on entering any status but the whip moves' (0x2A, 0x26, 0x31 - 0x34, 0x18, 0x3E, 0x14D, 0x154, 0xF1 - 0xF5, 0x15B) |
| "etc" sweep: neutral air's landing hit missing | `LandingAirN` (1 %, 30 degrees, frame 2) not in the translator's list: the base's emptied slot | `ultimate_acmd.TRANSLATE` += LandingAirN / F / B / Hi (no vl bytes for landings) |
| "etc": no step dust (walks, dash 21, turn) | Ultimate's `FOOT_EFFECT("null", foot)` = the ground's own footstep effect, dropped as an effect without an id; Smash 4 writes it `Graphic_Effect(0, LFootJ ...)` (vanilla ZSS's walks) | `ultimate_acmd.EffectTranslator`: FOOT_EFFECT "null" -> effect 0 |
| "etc": sounds missing (dash attack swing, down smash's second swing, double jump, run brake / dash turn) | Ultimate tones that are containers with one `_ft` variant (se_master_dash_stop -> _dash_stop_ft, _jump02, _attackdash01, _dash_turn, _smash_L02): the "first variant" rule took numbered children only | `ultimate_sound.ult_tones`: a container with no numbered child maps to its `_ft` one (sound_ids.json only: the banks and the label table are byte-identical to the installed ones) |
| charged neutral special "late" (open) | no cause found in the scripts (FT_MOTION_RATE and Smash 4's Set_Frame_Duration are both frame-length multipliers: the Hitbox Viewer plays SpecialHi's 0.3 as fast, 72 frames in 65); the article / arrow MSC unchanged | still waiting for the user's clip |

### v6: the whip sword (`tools/master_whip.py`, called by `master_build.py build`)

What Smash 4's whip gives (ZSS's files and the executable): its descriptor (kind 0x38, copied for 0x1A0) links its joint
2000 (HaveN) to the owner's joint 0x19 (RHaveN = Ultimate's HaveR: his converted RHaveN equals it, 0.0 difference); its
motion info names 15 animations (x4 custom moves) by the material_anime-list CRC of `FitSZerosuitWhipMain<name>` (C03AttackS4S,
C04AttackHi4, ..., WhipShoot, WhipReverse): fixed in the executable, so his sword's motions go in under those names.
`Set_Anchored_Article_Action(2, motion)` (ZSS's up smash, grab, down taunt) plays one of them in the fighter's model
space from the frame it runs (her E00Catch whip's HaveN track IS her RHaveN's world matrix, 0.0002); her tether's
`Set_Remote_Article_Action(2, 1)` / `2(2, 3)` (statuses 1 shoot / 3 back: WhipShoot / WhipReverse at her params'
rate, the ledge check between joints 2000 - 2001, HaveN - AttachN) play in the hand's space (her HaveN track 0).

| slot (ZSS name) | his move | how |
|---|---|---|
| 0 C03AttackS4S | down tilt | anchored, Ultimate's attack_lw3 (frame = body frame), removed 59 |
| 4 C04AttackHi4 / 20 E00Catch | up smash | 20: frames 0 - 6 then the sword's charge loop (the body holds at 7 for the charge); 4 from body frame 7 (FRAME 8: after the charge, Ultimate's restart frame) |
| 8 C05AttackAirN / 12 D01SpecialS | up air / its landing | anchored; the landing changes it (Ultimate's IS_EXIST + change_motion) |
| 16 D01SpecialAirS | up special (ground) | anchored, Ultimate's timeline: special_hi start (1 - 16), extend (17 - 26), special_hi_end (27 on); the body's 0.3 rate (1 - 10) in its own script |
| 24 / 28 / 32 E00CatchDash / Turn / Pulled | rapid jab start / loop / finisher | anchored, the loop restarted each loop (its script's JUMP) |
| 36 E01ThrowF / 40 J01AppealS / 48 J02Win1 | forward / back / down throw | anchored |
| 44 J01AppealLw | down taunt (L and R: one animation, ZSS's) | anchored |
| 52 WhipShoot / 56 WhipReverse | up special (air: ZSS's tether) | hand space: `extend` at the frame whose tip is as far from the hand as her AttachN at that frame, capped at Ultimate's full reach 48 (AttachN = the tip: the ledge check, the hang's frame-from-distance and the blade agree); the back motion folds into the sword's wait pose under 18 |

Model: ZSS's 18 whip bones first (names, hashes, order: model.jtb / nhb kept; HaveN's bind the identity, Ultimate's
root), the sword's 57 after (sword01 under HaveN, Ultimate's binds, CRC32 hashes); her chain bones ride the sword's
(PlasmaWhip01H - 08H on sword05 / 10 / ... / 35 / 37, AttachN / PlasmaWhipEndN on sword_null): effects on joints
0x7D1 - 0x7D9 and the ledge check follow the blade. Meshes: Ultimate's sword / sword2 / stone in her
Whip_VIS_O_OBJ_NSC slot (Cylinder empty), his body's materials (`ultimate_fighter.templates` / `material_for`),
textures in his article block 0x40C74800 (`fighter_texture_ids` 'whip'). The whip's own scripts: game = visibility
(drawn while Ultimate's body sword is hidden: e.g. SpecialHi 2 - 51) and the up special's rate; effect = the sword
article's Extend (master_wire_flash on sword37 = joint 0x7D9, master_wire_wind on sword35 = 0x7D8) at 17 (ground) or on
WhipShoot where the tip is as far (air). Its MSC: ZSS's (the tether). W11: 75 bone-instances (1 instance).

Checked offline: `scratchpad/byleth/v6/bin/render_whip.py` (our body NUD / OMO / face pac + the whip NUD / VBN / OMO
against Ultimate's body + sword article on his timeline, side and front views): every slot at 3 - 7 frames
(`scratchpad/byleth/v6/r1/`, sheets `v6/sheet1-5.png`, `v6/sheet_final.png`) draws the same blade in the same place;
WhipShoot's AttachN = the tip at every frame (distance 4.5 -> 48, capped). Sm4shCommand's Hitbox Viewer (Shot.exe,
`scratchpad/byleth/v6/shots/`): SpecialHi / AirCatch's hitboxes at the whip's tip (game frame 14 = motion 21: the
capsule ~50 above him). port_check `byleth_v4.zip byleth_userdata_v2.zip byleth_v5_fix.zip byleth_v6_fix.zip`:
**0 ERROR**, 29 WARN (v5's); S12 on v5's install: ERROR (the bug), on v6's: INFO.

Not checked (in game only): that an anchored motion follows the owner's hitlag (the rapid jab's hits) and a mid-move
turn (back throw's Reverse_Direction at 25); that Set_Anchored_Article_Action on an article that's gone (the up air's
landing after its frame 65) does nothing; ZSS's native ledge check on the new joints. Approximated: the air up
special's start / back motions (the body sword shows until 17, the whip folds back in ZSS's 6-frame retract rather
than Ultimate's 46-frame special_air_hi_end); the female down taunt's whip on the male hand; Win3 and the Final
Smash keep the body sword (no slot left); the sword's physics frames (Ultimate's PHYSICS flag in the article's
scripts: the canned motion plays instead); its SpecialHiHit catch effect (wire_catch) not shown.

Package `scratchpad/byleth_v6_fix.zip` (`scratchpad/byleth/make_pkg_v6_fix.sh`: the fighter files that differ from
v4 + v5_fix as installed; 28 files: the whip model / motions / scripts, body / body2 main.pac, the 16 face pacs, body
game / effect / sound, master.mscsb), INSTALL README `scratchpad/byleth/INSTALL_README_v6.txt`. No exe.
Build: `master_build.py vis` (weapon_vis.json without the stand-in), then `ultimate_port.py run master motions
motions-group2 low-models sound scripts specials variants shapes --out OUT` (`scratchpad/byleth/pipeline_v6.log`,
`pipeline_v6b.log`).

## Status: v5 (`scratchpad/byleth_v5_fix.zip`: a FIX package over v4 + byleth_userdata_v2; in-game TEST)

User, v4 test: the select-screen icon too large and off its hexagon (screenshot), down tilt "not visible for most of
the move" (the weapon, user), the bow showing in moves where it shouldn't, up special doesn't appear / work, the
charged neutral special's effects and arrow "extremely late", "etc".

| point | cause (evidence) | fix |
|---|---|---|
| select icon | v3 / v4 shipped `ui/replace/chr` from the build made on the vanilla stand-in templates (`port/master/ui`), not the user-file build (byleth_userdata_v2): installed after userdata, its `chr_10_Byleth_01` (a rectangular close-up) and 8 `chr_00` replaced the hexagon ones (byte diff v4 vs userdata_v2: exactly those 9; the screenshot's icon is the rectangular art) | the fix package ships the user-template build's (= userdata_v2's) chr_00 / chr_10, for data and data(us_en). **port_check U1 portrait-replaced** (WARN: a later package's different portrait over an earlier one's) |
| stock icons | `ultimate_portraits.py --stock-icon` fitted Ultimate's chara_2 into the base icon's MATCHED head box, which on the user's ZSS icon (not a crop of her chr_90) was ~6 px: 42 of 4096 pixels drawn (9 chara_2 px a pixel) | fitted into the base icon's whole drawn box (1.07 px a pixel); **port_check U2 stock-icon** (ERROR: < 15 % drawn) |
| down tilt's weapon (and rapid jab, up smash, up air, throws, down taunt, up special) | Ultimate hides his body's sword (`master_sword` vis, down tilt 0-57) while the `sword` article (the whip form) is out, and v1-v4 followed that track with no whip built: nothing in hand | `master_build.py vis`: the sword article's generate / remove frames (`master_sword_article`) and `ultimate_fighter.VIS_ALSO` (the body sword shows with it): the body sword stands in for the whip. The sword article's Extend (from the up special's frame 17), SpecialHiHit and ThrowLw effects merged onto Sword1 (`ARTICLE_FX` collapsed: approximated) |
| bow in other moves | every motion's weapon keys checked against Ultimate's scripts (generate / remove / exist per game script, 13 scripts touch the bow, all with it) and the face pacs of every costume (only the 10 Failnaught / neutral-air motions key it on). Found: (a) same-frame keys were applied sorted ([f, 0] before [f, 1]: a script's "remove a leftover, then generate" or "exist then remove" order lost); (b) the bow hidden in SpecialNTurn although Ultimate's bow plays `d00specialnturn` (also Aymr's turn / cancel / landing 1) | (a) keys by frame in script order (`master_build` vis, `build_motions`); (b) an article's own motion of a body motion its script doesn't touch: out from the motion before (`ARTICLE_MOTIONS`). Still to find with the user's clip / move names if it persists |
| up special | the whip blade (`sword` article, 58 bones) is still not built | the body sword now shows through it, with its effects. **Not done**: Handover |
| charged neutral special late | not reproduced offline: the draw is Ultimate's (SpecialNStart 120 frames, rate 0.9 from 45 = Ultimate's FT_MOTION_RATE; CAN_SHOOT 45; max at the motion's end, ~112 frames; the arrow made on the shot's first frame as Ultimate's shoot_exist; the arrow's MSC moves it natively, no wait); the merged glows at Ultimate's frames (arrow Haved 23, Haved2 49 / 105) | asked the user for a clip (hold length, when the glow / arrow appear) |

Built: `master_build.py vis`, `ultimate_port.py run master motions motions-group2 low-models scripts specials variants
shapes`, `portraits` (to `scratchpad/byleth/port_ui5`, the user's templates); package `scratchpad/byleth/make_pkg_v5_fix.sh`
(the fighter files that differ from v4's: the 16 face pacs, effect.bin, the effect bank (the variants step's turned
copies for the new merges); + the 17 portraits), INSTALL README `scratchpad/byleth/INSTALL_README_v5.txt`. No exe.
Article effects merged: 17 (the sword's SpecialHiHit catch effect left out: its slot's scripts are empty; merges skip
slots he doesn't play, which put the Extend effects in ZSS's emptied D02SpecialAirHi slot on the first run (C1)).
port_check `byleth_v4.zip byleth_userdata_v2.zip byleth_v5_fix.zip`: **0 ERROR**, 29 WARN (v4's 21 + U1 x8: the
remade stock icons, expected). Suites: fighter_texture_ids_test ALL OK, brave_mark_test 0 failures. Not done: the
whip blade (up special), the charged-Failnaught timing (no cause found offline: needs the user's clip), the "etc"
pass over the rest of the moveset (only weapon visibility / article effects were gone through).

## Status: v4 (`scratchpad/byleth_v4.zip`: fixes from v3's first in-game test; complete fresh install; in-game TEST)

User, v3 test (two clips, male c00 only; a female clip still to come): "Many of female byleth's effects don't appear,
and both male and female byleth snap in their animations, weapons don't align correctly or appear at all, up special
doesn't appear, many effects in general aren't appearing (ex. neutral special), constantly holding the bow when not
doing neutral special"; then "Neutral special also never fires its projectile".

The clips framed (60 fps, every frame; `scratchpad/byleth/clips4/`): clip 1 (13.4 s) wait with the bow and no sword
(0.0-0.3 s, 1.5-2.1, 2.5-2.7, 12.0-13.4: Wait1, static from 1.55 to 2.08 s, entered with a one-frame swap of sword /
bow at 1.48 s), dash attack 0.4-0.9 (into a turn at its cancel frame 45: a one-frame pose change, no blend), Failnaught
2.75-3.9 and 4.25-5.4 (the draw: only foot dust; the shot: no arrow, nothing flies), forward smash 8.4-9.1 (Areadbhar
in hand but along the wrong axis), down smash 7.0-8.3 (Aymr: blades sideways), grab / throw 11.4-11.9; clip 2 (6.1 s)
aerials with Areadbhar (fair / bair 0.6-2.2: the spear pointing down / backwards out of the fist, its flame and hits
elsewhere), double jump, nair / Failnaught in the air (4.1-4.3), landing into the bow wait (5.6 s). Also seen (not in
the user's list): the win-pose `_lang` face entries are ZSS's (results only). Every cause below is proven offline
with renders (`scratchpad/byleth/bin/pose.py`: our NUD + VBN + OMO + face pac against Ultimate's numshb + nusktb +
nuanmb + articles; `scratchpad/byleth/renders/`).

| user's point | cause (evidence) | fix |
|---|---|---|
| bow always held / sword gone in the wait; weapons "appear at all" wrong | **the base's `material_anime.lst`** (in every face pac, kept since v1) sends 73 motions to ANOTHER motion's face entry: ZSS's Wait1, WaitItem, WalkFast, the five aerial landings, Passive*, ... -> `D00SpecialNStart` (her shared ones). Decoded: entries (CRC-32 with start 0 of the motion name, of the shared entry's name, u32), the hash from the executable's loop at 0x03357004. Vanilla lists only motions without an entry of their own (0 of its 74 have one); ours have, but the game takes the list: Wait1 played SpecialNStart's keys (bow on, sword off), the landings too | `ultimate_fighter.lst_without`: the list without the motions that have their own entry (1 entry left, an unknown motion -> TurnRunBrake). **port_check F2 face-lst** (ERROR: v3 fails it on all 16 costumes) |
| weapons don't align | the held articles' meshes were put on HaveR / HaveL in their raw coordinates: Areadbhar is bound to its `Spear` bone (turned from the article root) and Aymr is skinned in the article's model space (under its rotated root `HaveR`); Ultimate's link puts the article ROOT on the fighter's bone. Proof: Ultimate's hitboxes on `haver` run along its +Y (forward smash (0, 3) -> (0, 26.5)), the converted spear ran along the hand's Z | `ultimate_fighter.article_link_space`: a parent-bound mesh by inv(root bind) @ bone bind, a skinned one by inv(root bind) (the bow's root is identity: unchanged). Renders: spear (forward smash, forward air), axe (down smash) and bow match Ultimate's pose with the articles linked |
| neutral special never fires | **the arrows had no MSC**: ZSS's Paralyzer shot (their base) flies, picks its motion and times out in its own `script/msc/paralyzer_bullet/paralyzer_bullet.mscsb`; v1-v3 shipped none for `arrow1` / `arrow2`, so the arrows were made with no status: no motion, so no ACMD (hitbox, effect), no movement (article list checked: 6 / 7 are 0x19E / 0x19F, max 2 / 1, the shot's spawner) | `master_build.py weapons`: arrow1 = the shot's MSC; arrow2 = the shot's MSC with its charge test (`WorkModule(0x10, 0x21000000)`, ZSS's charge flag, which his Failnaught doesn't set) always true (motion 4, life 0x12000003 = 30), decompiled / recompiled (the shot's own round trip decompiles identically). **port_check W14 weapon-msc** (ERROR: v3 fails it) |
| effects missing (neutral special ...) | Ultimate draws Failnaught's glow (`master_bowflare2`), the drawn arrow's charge (`master_bow_hold1` / `hold2`, `master_bow_flash` at full charge: the held arrow1's Haved / Haved2), the shot (`master_bow_arrow1_shot`) and Aymr's blade flares (`master_axeflare1-3`) from the ARTICLES' effect scripts; the articles are baked into his body, so none played | `master_build.py article_effects`: those scripts merged into the body effect scripts of the slots that play their animations (bow -> SpecialNStart / SpecialN + air; arrow1 Haved / Haved2 -> SpecialNStart + air; axe -> down smash, down air, its landing, SpecialLw / air / hit / landing), their bones: the article root on the bone it is linked to (bow `have` -> havel; axe root -> haver; the held arrow's top -> haver: approximated), the others by the article's bind (Aymr's blades: an offset and turn along the blade, EffectTranslator's parents / locals). `merge_timed` keeps the body script's facing tests whole. 16 merges |
| snapping | the converted motions are Ultimate's exactly (world positions of hands / head / hip / feet / sword over every frame of AttackDash, Wait1, AttackAirF, Turn, Attack11: <= 0.07); frame counts equal; the vl blend bytes as Ultimate's motion_list (wait 6, run 3, ...; attacks 0 in both games); OMO hemisphere flips at vanilla's rate (0.18 % / 0.16 %). What snapped in the clips: the bow / sword swaps between Wait1 (SpecialNStart's keys) and every move (above), and Wait1 itself played in the wrong-weapon pose; cancels into another status (dash attack -> turn at 45) change pose in one frame as in Ultimate (blend 0 there too) | the face list (above). If a female clip still shows snaps: send it (her motions were checked the same way in v3) |
| up special doesn't appear | the move plays (ground 0x154 / air 0xF1 with SpecialAirHi, Ultimate's slash at 16 and flash at 17), but its visible part is the Sword of the Creator's whip (the `sword` article, 58 bones) and its own Extend effects (`master_wire_flash` / `_wind` at its tip): neither is built (v1's known gap: "the whip sword not shown") | **not done in v4**: Handover 1 |
| female effects | no female clip yet; her group shares every script, effect bank and joint table with the male (joint tables 0 / 1 identical, FaceN / Sword1), so the fixes above apply to her too | to check with a clip |

Package `scratchpad/byleth_v4.zip` (`scratchpad/byleth/make_pkg_v4.sh`, INSTALL README `scratchpad/byleth/INSTALL_README_v4.txt`):
the packaging convention's roots (`INSTALL_TO_data/`, `INSTALL_TO_code/`, `OPTIONAL_INSTALL_TO_data/` for Sephiroth's
flare1), exe **exe_v46t_threads** (= exe_v46s + `tools/ts_scene_sites_cave.py`, the time commands' scene fix: no Byleth
exe change in v4). The user's data files: `byleth_userdata_v2.zip`, unchanged; the param / ui files go into both `data`
and `data(us_en)` where the game reads regional copies. port_check: Install now maps `INSTALL_TO_code/` to `code/` and
skips `not_for_install/`.

Build: `python3 tools/ultimate_port.py run master model-c00 .. model-c07 motions motions-group2 low-models scripts
specials variants shapes --out OUT` (`scratchpad/byleth/pipeline_v4.log`, `pipeline_v4b.log`).
port_check: `port_check master scratchpad/byleth_v4.zip scratchpad/byleth_userdata_v2.zip` (the install as the user
has it): **0 ERROR**, 21 WARN (v3's B1 / E3 / E7 / M5); the new checks over v3: F2 x16 (every costume), W14 x2.
Suites: brave_mark_test, fighter_texture_ids_test 0 failures; ts_scene_sites_test on exe_v46t_threads 0 failures.
Offline renders kept: `scratchpad/byleth/renders/weapons_v4.png` (ours v4 vs Ultimate's with the articles linked:
forward smash 28, down smash 20, SpecialNStart 60, forward air 12), `cmp_wait1.png`, `dash.png`.

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

0000000000000000. **v17 fix** (sent: `scratchpad/byleth_v17_fix.zip`, no exe): test list in
   `scratchpad/byleth/INSTALL_README_v17.txt`. If the whip still vanishes at the catch: a clip of frames 0 - 2 of the catch
   (a one-frame gap is expected), then read the whip kind's native handlers (docs/native-notes.md "Article ops") or move
   the regeneration into master.c. If the loser panel shows him badly framed: result_param eye / to (`tools/result_param.py`).
   If the mouth is still missing: which state the results scene applies (a diag on MaterialAnime in the result scene).
   Open: the same result_param entry for Hero / Sephiroth / Incineroar / Steve / Squirtle / Supamario; the other ports'
   jab values (README "Status: v17").
000000000000000. **v16 fix** (sent: `scratchpad/byleth_v16_fix.zip`, no exe): test list in
   `scratchpad/byleth/INSTALL_README_v16.txt` (hit sounds on Aymr / down smash / down air / rapid jab end / max arrow,
   Aymr's turn during the move, mouths in every victory pose). Open: the user's "up special too slow" (v16 measured
   ours = Ultimate's from catch to hit: ask which part, a clip of the air / far case); the same silent-hit fix for Hero,
   Squirtle, Incineroar and Steve (`tools/hit_sound_fix.py` on their installs, port_check S25); the result eyelids.
00000000000000. **v15 fix** (sent: `scratchpad/byleth_v15_fix.zip`, exe_v46x_whipmot): test list in
   `scratchpad/byleth/INSTALL_README_v15.txt` (the hit's flick, the blade shortening with the pull, the overtake's
   sword, no freeze). If the sword stands still from the catch: the anchored action kept her status 2's rate 0 (README
   "Status: v15": set the rate from the whip's side). If the blade's length is off: the diag's second k4 (VAR_16, the
   distance); PULL_LENGTHS / MASTER_HI_HAND_X / _Y. Open: Ultimate's aim of the sword at the target (tip_angle_object).
0000000000000. **v14 fix** (sent: `scratchpad/byleth_v14_fix.zip`): test list in `scratchpad/byleth/INSTALL_README_v14.txt`
   (no freeze; the sword retracting through the pull; k15 names the energy that carried 2.5 up). **Next: the sword's
   own motions** (hit bend, overtake, distance-tied pull): the plan and the facts are under "Status: v14" ("Not done").
000000000000. **v13 fix** (sent: `scratchpad/byleth_v13_fix.zip`): test list in `scratchpad/byleth/INSTALL_README_v13.txt`.
   With the diag: k14 0 (nothing else moving him), k8 constant through the stop, k10 equal steps. Open: the sword's hit
   flex and overtake motions (a whip motion slot: weapon_expand "motions", exe), the reverse's rate vs the reel.
00000000000. **v12 fix** (sent: `scratchpad/byleth_v12_fix.zip`): test list in `scratchpad/byleth/INSTALL_README_v12.txt`.
   With the diag (v11's TEST_ONLY exe + v12's diag master.mscsb): k12 about 10 (on the target), k13 up by 6.5 at the
   overtake (its hit). If the hit lands but looks wrong: the target's pose (Ultimate holds it in a capture pose on his
   `throw`; a capture status of ours for the soft catch), MASTER_HI_OVT_Y per fighter. Then v11's / v10's open lists.
0000000000. **v11 fix** (sent: `scratchpad/byleth_v11_fix.zip`): test list in `scratchpad/byleth/INSTALL_README_v11.txt`.
   With the diag: k10 should fall about 4 a frame during the reel; k11 1 at the wall jump's jump (else the game didn't
   re-enter 0x15C: then the jump needs another route, e.g. the speeds from a slot-6 function as Captain Falcon's
   func_2288). Then v10's open list below.
000000000. **v10 fix** (sent: `scratchpad/byleth_v10_fix.zip`, no exe: the user's exe_v46w_vars_line): the user's test list in
   `scratchpad/byleth/INSTALL_README_v10.txt`. If the catch still fails: the TEST_ONLY diag (exe_v46w_vars_line_diag
   + the diag master.mscsb: k6 the tip's distance to the opponent each frame of 20 - 26, k7 which catch, k8 / k9 the
   hang and the wall jump): k6 never under 10.5 = the opponent isn't brought to the tip (the pulls); k7 2 - 4 but no
   hold in the clip = the hitstop / position writes (position_vars) don't hold it. Open: (1) the game's grab pass (who
   fills CatchModule `+0x1C`: README "Status: v10"); (2) the sword's length on a wall latch (canned motions: the tip
   grows through the wall during the 12-frame stop) and Ultimate's tip_angle_wall / wall_offset; (3) the ledge box's
   size against an Ultimate clip (v10 = Ultimate's data in world units on Ultimate's frames: wider than v9's, see the
   diagram `scratchpad/byleth/v10/ledge/ledge_boxes_v9_v10.png`); (4) v9's list below.
00000000. **v9 fix** (sent: `scratchpad/byleth_v9_fix.zip`, exe_v46v_line): the user's test list in
   `scratchpad/byleth/INSTALL_README_v9.txt`. If the catch still fails: the TEST_ONLY diag (exe_v46v_line_diag +
   the diag master.mscsb: S4GF lines k 1 = an opponent's status near him (189 caught), k 5 holding) settles whether
   the grab box catches at all (then trace the per-frame pass that applies grabs: the CatchModule vt +0x8C
   `0x02C18DC8` caller) or the MSC misses it. Open: (1) the exe for the other agent's variable resets: apply
   `tools/var_reset_cave.py` first, then `tools/line_test_cave.py` (`scratchpad/byleth/v9/exe/exe_v46w_vars_line.rpx`
   built that way: sha1 bfd3b5b4...); (2) Ultimate's "would KO" test for Aymr's critical (the ExeFS cut-in: main.bin
   reads critical_* in the common critical code at ~0x869F10 / 0xAD7xxx, not read) and its zoom rate / offset / the
   darkened background; (3) the smash orbs' and effects' bloom (halos as xv2_smash_fx.py's, an A/B in game:
   `scratchpad/byleth/v9/view/smash_holds_v8_left_v9_right.png` is the Hitbox Viewer's before / after of the orb
   placement); (4) the up special's sword length (canned motions: it stops by the status change, Ultimate's sword
   shortens to the point), HANG_IMMIDIATE's box, the search box at 15; (5) v8's list below.
0000000. **v8 fix** (sent: `scratchpad/byleth_v8_fix.zip`, no exe): the user's test list in
   `scratchpad/byleth/INSTALL_README_v8.txt` (the max arrow's line and hit, the charge glow gone with the move, the up
   special's catch / pull / throw on ground and air targets, the lights). Open, in order: (1) **the effects' bloom**:
   Ultimate's HDR emitters (master_smash_hi at colour scale 2 - 6, the spear / axe flares) bloom into wide soft glows
   that Smash 4's own pixel programs clamp away (`v8/fxcmp/side_special_ours_vs_ult.png`, the up smash in the user's
   clips `v8/fxcmp/s4.png` / `ult.png`): fake halos as `tools/xv2_smash_fx.py`'s (an additive soft copy of each
   emitter whose Ultimate peak is over ~2, HALO_ALPHA tuned in game; meshes need their own falloff), in
   `vfxb_to_ptcl.py` behind a port.json switch, then an A/B package; the `_sub` (subtractive) layers' strength against
   Ultimate's clip; (2) **the wall tether**: a line test from his hand to the sword's tip (an exe cave over the Wii U's
   GroundModule ray_check 0x02C39F18 as a position variable, as `smashrun_walker_cave.py`'s pk_ray calls it), then
   Ultimate's SpecialAirHiHit on a wall (wall_offset (-0.6, -0.8), tip_angle_wall 70, hit_stop_frame_wall 12) and the
   wall jump; the same test would cut the max arrow at the first ground (param_arrow2: "cut at the first ground");
   (3) if the caught fighter's capture pose (0xBD, Falcon Dive's) looks wrong, another capture status (0xB8 Dark Dive)
   or a custom thrown motion; TARGET_HI_DAMAGE's real test (ExeFS); (4) v7's list below.
000000. **v7 fix** (sent: `scratchpad/byleth_v7_fix.zip`, exe_v46v_threads): the user's test list in
   `scratchpad/byleth/INSTALL_README_v7.txt` (brightness vs `images/23.png`, side special end position, up-special ledge /
   catch / no special fall, Aymr's floor hit / landing / turn, the max arrow). If the side special now moves too far
   (Smash 4 adding the root's motion on top of the MSC's lunge speed), drop the MSC speed for 0x22E / 0x232 and keep the
   root's; if the model is still dark, the hair (skin path) and an in-game A/B of `rim_from_body`'s values. Open: the
   wall tether (the sword tip's wall test), SpecialSFDash, SpecialLwCancel / SpecialAirLwHit, the effects' in-game
   darkness (fx_render draws them bright: compare against an Ultimate clip move by move), master_swordaura.
00000. **v6 fix** (sent: `scratchpad/byleth_v6_fix.zip`, `scratchpad/byleth/INSTALL_README_v6.txt`): the user's test
   of the whip (up special on the ground / air, a ledge tether, the hit's pull; down tilt, rapid jab, up smash tap /
   charge, up air + landing, throws (back throw facing left), down taunt; no whip left after a hit). Then: if an
   anchored whip drifts from the hand (hitlag in the rapid jab, the back throw's turn), the anchored motions'
   frame / facing rule (a diag build or the clip). Still open: the charged Failnaught timing (a clip), Areadbhar's
   dash version (SpecialSFDash / AirSFDash: Ultimate's longer lunge, 11.5 / 17.25 %; no slot / status yet), Aymr's
   SpecialLwHit / Turn / Cancel, SpecialHiDispSword's effects, the sounds with no id left (se_common_sword_swing_s,
   se_common_ladderstep_m, other fighters' / raw hashes, the female-only se_master_win01_02 / 03 in the male bank's
   scripts), Win3's whip (a 16th whip motion needs the executable's motion info grown: weapon_expand "motions").
0000. **v6: the whip sword** (done in v6, "Status: v6" above; the plan below is what was found before it). Facts gathered for it:
   ZSS's whip article (his copy, kind 0x1A0, `model/whip/c00`, now hidden by `nud.hidden` in `master_build.weapons`)
   has 18 bones: HaveN, PlasmaWhip01H-08H (a straight chain in bind, ~4.99 apart along (-0.5, 0, 0.866) from
   (-1.35, 0, 2.46) to AttachN (-19.74, 0, 34.31) and PlasmaWhipEndN), and billboard copies 02H-08H; its meshes
   Whip_VIS_O_OBJ_NSC / Cylinder_VIS_O_OBJ_NSC (bind 4, rigged); motions `motion/whip/main.pac` (15: AttackS4S,
   Catch*, WhipShoot / WhipReverse ...). Ultimate's `sword` article: 58 bones (HaveR root, sword01-sword37 + _B
   helpers), motions in `motion/sword/c00` (extend, wait, c02attacklw3, c04attackhi4, c05attackairhi, e01throw*,
   d02special*hi*, c00attack100*, j01appeallw*). Plan: (1) the up special: the sword's mesh posed at `extend`'s last
   frame (scratchpad/byleth/bin/pose.py `ult` renders it with the root on haver), re-skinned to the 8 whip segments
   by distance from the hilt along the chain, written as the whip's model.nud (its own nut), `nud.hidden` and the
   aircatch script's `Article_Visibility(2, 0)` dropped; check the whip's native reach (ZSS's tether) against
   Ultimate's 70 and move the hitboxes to the whip's tip if its ACMD can carry them. (2) the other whip moves: a model
   article with a MotionModule (dein copy, catalogue W5 / W8) playing the sword's motions resampled to <= 16 bones, or
   the whip article generated with a motion of ours; then the stand-in (`master_build.WEAPONS['SWORD']` +
   `VIS_ALSO['master_sword']`) removed. Then the "etc" sweep (hitbox timing, effects, sounds per move vs Ultimate).
000. **v5 fix** (sent: `scratchpad/byleth_v5_fix.zip`): the user's test of the icons, the sword stand-in, the bow; their
   clip of the charged Failnaught timing and of any move still showing the bow. Then the whip sword (the plan below,
   item 1), which also replaces the stand-in in the down tilt / rapid jab / up smash / up air / throws / taunt.
00. **v4** (sent: `scratchpad/byleth_v4.zip`, `scratchpad/byleth/INSTALL_README_v4.txt`): the user's test of the face
   list fix (no bow in the wait, weapons per move), the held weapons' axes, the arrows (MSC), the article effects; a
   female clip (her missing effects: none found offline). Then, in order:
   1. **The Sword of the Creator's whip** (user: "up special doesn't appear"; also the rapid jab, up smash, down tilt, up
      air, throws, down taunt, Win3 show the hilt only). Plan: Ultimate's `sword` article (58 bones; `extend` /
      `special_hi_*` / per-move motions) on the whip article ZSS's tether already makes for the air up special (article
      2, kind 0x1A0, her 8-segment chain PlasmaWhip01H-08H driven by her native code; its model is hidden now): its
      mesh posed at `extend`'s last frame, re-skinned along the 8 segments by distance from the hilt, `nud.hidden`
      dropped and the `Article_Visibility(2, 0)` in aircatch removed; the sword article's Extend / SpecialHiHit
      effects (`master_wire_flash` / `_wind` / `_catch` on sword35 / 37) on the last segment. The ground up special and
      the normals need a whip of their own (a dein-copy model article with MotionModule playing the sword's motions,
      catalogue W5 / W8: 58 bones, resample to ~16) or a baked chain (no bone budget left: 132 / 136).
   2. If snaps remain (a clip): which move / transition; the converted motions are exact (README v4), so a status
      change without blend (the vl byte 1 of the target motion) or a frame jump in game (a diag on MotionModule frames).
   3. The held arrow's top is on his right hand (approximated) and `master_bow_hold1` isn't turned off when hold2
      starts (Ultimate's Haved / Haved2 split not read); the bow's string / body bones and Aymr's opening blades are
      still rigid (their article motions not baked: no bone budget).
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
  46215. The female cheer (`vc_master_c01_cheer`) is the male's audio (only 0.3 dB louder): one cheer bank (Sound v1).
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
- His announcer call was ZSS's (0x380017, "Zero Suit Samus") until the user sent their
  `sound/se/snd_se_narration_characall.nus3bank`: done in "Sound v1" below.

## Sound v1: announcer call and crowd cheer (`$S/byleth_sound_v1.zip`)

Install after v15 (and supamario_sledgehammer_v1, whose soundlabeltable it builds on).

**Announcer (character select).** `param/ui/ui_sound_call_voice_db.bin` gives character id 65 sixteen sound ids (one
per costume); the vanilla roster's and the ports' calls are labels of `sound/se/snd_se_narration_characall.nus3bank`
(BINF `snd_se_narration_characall` 6085, soundlabeltable row 0x38: ids `0x0038LLLL`; the DLC banks
`snd_se_narration_characall_<Name>` are named one by one in the executable, no `%s` form). The user's bank: vanilla's
86 calls + Squirtle (86, `_Pzenigame`) + Sephiroth (87, `_Edge`), row 0x38 88 labels. Byleth's call is Ultimate's
`vc_narration_characall_master` (one mono IDSP, 1.07 s, +3.0 dB like every other call) as tone 88
`snd_se_narration_characall_Master`; row 0x38 88 -> 89 labels; id 65's 16 ids 0x00380017 -> 0x00380058:
```
python3 tools/fighter_extras.py narration THEIR/sound/se/snd_se_narration_characall.nus3bank \
    SLEDGEHAMMER_V1/sound/config/soundlabeltable.bin USERDATA_V2/param OUT \
    --ult-bank ULT/sound/bank/narration/vc_narration_characall_master --ult-tone master --name Master --id 65
python3 tools/fighter_extras_test.py --narration THEIR_BANK THEIR_TABLE THEIR_PARAM ULT_BANK master 65
```
Checked (`fighter_extras_test.py --narration`, new): the bank's 88 tones byte for byte (TONE entries, audio at the same
PACK offsets, every other section), the new tone = Ultimate's audio and volume, only row 0x38 changed in the table
(+1 label; the table is supamario_sledgehammer_v1's: userdata_v2's + Supamario's 3 labels), only id 65's 16 bytes in
ui_sound_call_voice_db (userdata_v2's: no later package ships it). The same pipeline on vanilla's bank
(`sound-Smash4.zip` on the Drive: `sound/se/`, `sound/config/`) gives tone 86 / 0x00380056, all checks ok.

**Crowd cheer (in a match): already in since v4 / userdata_v2.** The parts, all in place:
- the bank: `fighter/master/sound/snd_vc_Master_ouen.nus3bank`, loaded by the kind's name (`0x030BB464` type 8:
  `fighter/%s/sound/snd_vc_%s_ouen.nus3bank`, Miis `snd_vc_Mii_ouen`), registered as the player's id kind x 0x11 + 9.
  ZSS's chant bank (52 tones; label 0 = tone 50 `_ouen_L`, the stereo chant; tone 51 `_R` is an 801-sample stub as in
  every vanilla chant bank) with tone 50 = Ultimate's `vc_master_cheer` (stereo, 1.48 s, -7.4 dB), own BINF id 46194
  (`ultimate_sound.py`; rebuilt now: byte-identical to v4's). Shipped in v1 / v3 / v4.
- the row: the exe's cheer alias for kind 0x47 = 6106 (ZSS's; `sound_alias_cave.py`, +0x5C8), so ZSS's row 0x8DD
  plays from his bank (checked in v15's cross_f.rpx).
- which label: `commonsoundtable.csb` record 0x44 (0x3E + kind - 0x41; named "Master" in v15's exe by kind_expand's
  table) = ZSS's: KO screams 0x24 / 0x25 / 0x1A of row 0x4E, chant (0, 0x8DD) (userdata_v2).
- the timing: `param/sound/audience_ouen_param.bin` row (0x47, 0) = ZSS's (3, 180, 58) (userdata_v2).
- **Per costume:** the loader takes `fighter/%s/sound/snd_vc_%s_c%02d_ouen.nus3bank` for a costume != 0 when it exists
  (`0x030C0E18`: type 8 with the se bank's costume, a new kind's costume number as is; else the main file). Ultimate's
  female cheer (`vc_master_c01_cheer`, `vc_master_cheer_c01/03/05/07`) is the male's recording byte for byte, only
  -7.1 dB instead of -7.4: one bank serves all 8 costumes (costume banks would need own ids outside
  `sound_bank_ids.own_id`'s slots, which have none for `ouen_cNN`, for a 0.3 dB difference). Not built.
- `port_check master` over v4, userdata_v2, v5-v9, vars_reset_v1, v10-v15 and this package: 0 errors (31 warnings,
  6 notes: the same as without it).
- Not tested in game.

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
# v4: the face list, the held weapons' link space, the arrows' MSC, the article effects; a complete package
python3 tools/ultimate_port.py run master model-c00 .. model-c07 motions motions-group2 low-models scripts specials \
    variants shapes --out OUT
bash scratchpad/byleth/make_pkg_v4.sh                                             # -> scratchpad/byleth_v4.zip (complete)
python3 tools/port_check.py master scratchpad/byleth_v4.zip scratchpad/byleth_userdata_v2.zip   # 0 ERROR, 21 WARN
# v6: the whip sword (tools/master_whip.py, run by the specials step), the throw joint on its tip, the "etc" sweep
python3 tools/master_build.py vis DUMP ULT fighters/master/weapon_vis.json
python3 tools/ultimate_port.py run master motions motions-group2 low-models sound scripts specials variants shapes --out OUT
python3 tools/master_whip.py tips ULT                                             # the air hit's pull table (master.c)
bash scratchpad/byleth/make_pkg_v6_fix.sh                                         # -> scratchpad/byleth_v6_fix.zip (fix)
python3 tools/port_check.py master byleth_v4.zip byleth_userdata_v2.zip byleth_v5_fix.zip byleth_v6_fix.zip   # 0 ERROR
# v16: hit sounds (ultimate_acmd.sfx_type; the install fixed by tools/hit_sound_fix.py), Aymr's turn (master.c), the result faces
python3 tools/hit_sound_fix.py DUMP/lua2cpp_master INST/.../body/game.bin INST/.../weapon/arrow2/game.bin --fix OUT
python3 tools/ultimate_fighter.py result-faces ULT/motion/body/c00 BASE INST/c00=OUT/c00 ...   # c01 for c01/03/05/07
python3 scratchpad/byleth/make_pkg_v16_fix.py
# v10: the catch / ledge box / wall cling / Aymr's landing (master.c, master_build.pull_angles / overtake_soft,
# ultimate_vl_shapes.tether_box), no exe; the TEST_ONLY diag exe on the user's exe_v46w_vars_line
python3 tools/ultimate_port.py run master scripts specials variants shapes --out OUT
python3 tools/rpx_patch.py exe_v46w_vars_line.rpx exe_v46w_vars_line_diag.rpx $(python3 tools/diag_godfist_cave.py --rpx exe_v46w_vars_line.rpx)
python3 -I tools/master_specials_test.py; python3 tools/kinetic_suspend_test.py exe_v46w_vars_line.rpx
python3 scratchpad/byleth/make_pkg_v10_fix.py
python3 tools/port_check.py master byleth_v4.zip byleth_userdata_v2.zip byleth_v5_fix.zip ... byleth_v9_fix.zip vars_reset_v1.zip byleth_v10_fix.zip
```
Body: `rolloff_acmd.py VANILLA/.../game.bin game.bin --plain --add 2.2 EscapeF EscapeB`; `mscdec.py -x tools/mscinfo.xml
szerosuit.mscsb` (round trip: 2 of 2393 functions differ, both equivalent: a folded negative constant, an empty else),
`universal_mechanics.py --air-mult 1.0`, `msclang.py`; packed as `build/universal_mechanics_all.zip`'s szerosuit entry
(local: the user's universal_mechanics_all wasn't at hand).
