# Byleth (`master`)

A port of Ultimate's Byleth (internal name `master`) to Smash 4, on **Zero Suit Samus's base** (`szerosuit`, kind
0x19). New fighter kind **`0x47`**, character id **65**, UI name `Byleth` (subtitle "A Heroic Legacy": Ultimate's own
string for him, `msg_menu.msbt` `mnu_standard_sub_master`; Ultimate has no other per-fighter subtitle), texture-id block `0x40C70000` (`reference/port_bases.json` `_texture_ids`). Trait: **Strike** (the user's
choice; `docs/character-traits.md`, `kirby_copy_trait()`). Roll-off: the default 2.2 / 1.0 with Hero's momentum
(ZSS's universal-mechanics body, below).

The port goes through the framework (`docs/ultimate-port-guide.md`): `fighters/master/port.json`,
`tools/ultimate_port.py` (init / plan / run), `reference/port_bases.json` `szerosuit` (her traps, new with this port).

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
  `effects.kept_out`; their stale ids dropped from `master_effects.json`). Colours compared with Ultimate's
  (`fx_render.py`, now through the port's translate map: Aymr, Areadbhar's lunge, Failnaught's draw, the air Sword of
  the Creator): the same reds / whites / gold; one stray magenta line on the converted side of Aymr's and Areadbhar's
  slashes (a refraction / distortion emitter drawn without its pass: check in game). The normals' colours not compared
  in this session.
- **Package** `scratchpad/byleth_v1.zip` (`scratchpad/byleth/make_pkg.sh`): the build (`ultimate_port.py run master
  effects model-c00 .. c07 motions low-models scripts specials variants shapes portraits --out $B/port`), the kind
  folder's AI / Kirby-copy bank / FinMaster, his sound banks, exe_v46q, the install README; `not_for_install/` the
  files made on vanilla stand-ins (soundlabeltable, commonsoundtable / bgm_fighter from `fighter_extras.py common` /
  `fanfare --set 0x47=0x12`, fighter_param with his stats, the ui / ai param databases, melee.msbt). Sm4shCommand rebuilt with his script names: `scratchpad/sm4shcommand_v1.7.1_byleth.zip`.

`port_check master scratchpad/byleth_v1.zip`: 0 ERROR (21 WARN). WARN: B1 effect / sound / expression (her common dust, common tones, slopes and
damage rumbles on common motions Ultimate's scripts have nothing for; her own tones taken out of 16 of them), E3
(one Smash 4 common effect), E7 (FLASH / BURN_COLOR macros), M5 (two empty ZSS slots).

## Handover: next steps (in order)

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
5. The whip sword's segments (the rapid jab, up smash, down tilt, up air, throws, the tether: a model on her whip
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

When their files arrive (port_sources.json: `fighter_param`, `soundlabeltable`, `s4_chr`, `templates.master`, and
add_fighter's `--param` / `--ui` on theirs):
```
python3 tools/add_fighter.py --param THEIRS/param --param VANILLA/param --ui THEIRS/ui --kinds tools/extra_kinds.json --only master --out DATA
python3 tools/ultimate_port.py run master sound scripts specials variants stats portraits --out OUT
python3 tools/fighter_extras.py common THEIRS/sound/config/commonsoundtable.csb OUT
python3 tools/fighter_extras.py fanfare THEIRS/sound/config/bgm_fighter.fbb OUT --set 0x47=0x12
```
(scripts / specials / variants again after sound: the scripts take the sound ids.)
Until then the outputs on vanilla files (`port/master/sound/config/soundlabeltable.bin`, `param/fighter/fighter_param.bin`,
the add_fighter data) are **not for install**: they would overwrite the user's own rows.

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
```
Body: `rolloff_acmd.py VANILLA/.../game.bin game.bin --plain --add 2.2 EscapeF EscapeB`; `mscdec.py -x tools/mscinfo.xml
szerosuit.mscsb` (round trip: 2 of 2393 functions differ, both equivalent: a folded negative constant, an empty else),
`universal_mechanics.py --air-mult 1.0`, `msclang.py`; packed as `build/universal_mechanics_all.zip`'s szerosuit entry
(local: the user's universal_mechanics_all wasn't at hand).
