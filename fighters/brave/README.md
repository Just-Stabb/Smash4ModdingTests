# Hero (`brave`)

A port of Ultimate's Hero (the user's `brave.zip`: model/body c00-c07, motions, params, AI, the
articles). New fighter kind `0x45`, character id 63, UI name `Hero` (subtitle "The Luminary"),
base Robin. Trait: **Shooter** (no preference given; docs/character-traits.md,
`kirby_copy_trait()`). Roll-off: the default 2.2 / 1.0 (Robin's universal-mechanics scripts).

## v1 (`build/steve_hero_v1.zip`, with Steve)

Built as Steve's (fighters/pickel/README.md), from Robin:
- `tools/ultimate_fighter.py` profiles `reflet` (male Robin, costumes 0 / 2 / 4 / 6) and `reflet_f`
  (female Robin, 1 / 3 / 5 / 7: her own mesh names): Hero's body, hand, sword, shield and scabbard
  (and the other outfits' capes, headdress, bandana, slime, rings) in Robin's always-shown
  `fullhands`; his hair in her hair slot; his face meshes in hers by expression; her swords and
  tome empty. (Fix 16: the shield left `fullhands` for her Final / Result mouths.) 110-120 bones (Robin's count).
- motions: 316, 3 item ones on Wait1; Robin's specials on Hero's (Thunder -> Frizz, Arcfire ->
  Zap, Elwind -> Woosh, Nosferatu -> the command menu's first skill).
- melee.msbt: the sound-test names copied from Robin's ("Robin (Male)" / "(Female)") renamed
  "Hero" / "Hero (alt)".

Not yet: his own moves, spells (articles), stats, sounds, effects, portraits. Robin's tome article
shows in her specials.

## v2 (`build/hero_v2.zip`): his attacks

```
python3 tools/ultimate_fighter.py model HERO/model/body/c0N REFLET/model/body/c0N OUT/c0N --empty EMPTY --max-bones 120 \
    --have Shield,Sword1 --motions HERO/motion/body/c00 --anim-cache CACHE.json
python3 tools/ultimate_fighter.py motions HERO/motion/body/c00 HERO/model/body/c00 REFLET OUT --max-bones 120 --have Shield,Sword1 ...
python3 tools/ultimate_acmd.py DUMP/lua2cpp_brave/brave BRAVE_BODY/game.bin OUT/game.bin OUT/c00 --have Shield,Sword1 \
    --others BRAVE_BODY OUT --motion-list HERO/motion/body/c00/motion_list.bin --mtable BRAVE_BODY/motion.mtable OUT/motion.mtable \
    --vl fighter_param_vl_brave.bin OUT/fighter_param_vl_brave.bin --vl-kind reflet --effects reference/ultimate_sys_effects.json NUSKTB
python3 tools/fighter_param.py set fighter_param.bin OUT 69 264=0
```
- His hitboxes are on `sword1` (36) and `shield` (2): `--have Shield,Sword1` makes those bones play
  LHaveN / RHaveN (both hang from the hands, as HaveL / HaveR), as Sephiroth's swords.
- 27 scripts: jab 3 / 3 / 4, dash attack, tilts, smashes (forward 18 / 16, up 14 / 16, down 11 / 13
  in front at 9 then behind at 20), aerials, grabs, pummel, throws, get-up / ledge / trip attacks.
- Smash attacks: `lot_critical` / `is_flag(CRITICAL_HIT)` taken as false (the normal hits). Down
  smash's dump splits its critical branch (`if crit { A } B; operatorbool(); D`):
  `ultimate_acmd.fix_split_flag_branch` puts B back in the branch and D in its else.
- Jab: 3 hits, no rapid jab (fighter_param 264 = 0; Robin has one).

Not yet: the side tilt's second hit (`AttackS3S2`, a second press: fix 16), the critical hits, his sword
trails (`tex_brave_sword1 / 2`: trail textures to add, as Sephiroth's) and effects, sounds, specials.

## v3 (`build/hero_v3.zip`): effects, sword trails, neutral special

```
python3 tools/ultimate_trails.py --shader 3 HERO_FX/trail TRAILS tex_brave_sword1.nutexb,tex_brave_sword2.nutexb=TexBraveSwordTrace \
    tex_brave_firesword1.nutexb,tex_brave_sword2.nutexb=TexBraveFireSwordTrace ...   (the other three the same; only TexBraveSwordTraceAdd kept)
python3 tools/vfxb_to_ptcl.py HERO_FX/ef_brave.eff REFLET/effect/reflet FXDIR 0x45 IDS.json EFFECTS --prefix PtcBrave \
    --templates VANILLA/fighter/*/effect/*/*.ptcl [--variants VARIANTS.json]
python3 tools/ultimate_fighter.py motions HERO/motion/body/c00 HERO/model/body/c00 REFLET MOTIONDIR --have Shield,Sword1 --max-bones 120 \
    --add D00SpecialN2,D00SpecialN3,D00SpecialNCancel,D00SpecialAirN2,D00SpecialAirN3,D00SpecialAirNCancel --anim-cache CACHE.json
python3 tools/brave_build.py DUMP/lua2cpp_brave HERO BRAVE_BODY fighter_param_vl_reflet.bin OUT/c00 PKG \
    --rpx TEST42/cross_f.rpx --bank FXDIR --trails TRAILS --motions MOTIONDIR
```
- Effects: 17 of `ef_brave.eff`'s 103 (the ones his moves so far use: shield bash / impact, smash
  ground, sword light, the chant and Frizz's hand / shot / bullet / hit / burst effects) after Robin's
  38 sets (`effect/brave/brave.010d0000`, 4.9 MB; all 103 were 12.4 MB). Two are on his hand turned
  (-90, 0, -90): `effect_variants.py` copies (`brave_effects.json`). Left out (no move uses them yet):
  `brave_tension`, `brave_flying`, `brave_entry`, `sys_misfire` (the MP-failed puff).
- Sword trails: Ultimate's `AFTER_IMAGE4_ON` -> `Sword_Glow` shader 3 (Sephiroth's retracting trail,
  `shader/effect_trail.nsh` + the executable patch) with his textures, trail ids 264-269
  (`trail_table_cave.py` NEW_TRAILS; it now also re-applies over an executable that has the table).
- Neutral special (status 0x152, Robin's Thunder; `brave.c` `brave_n_*`): SpecialNStart, then
  SpecialNHold while special is held; Frizzle from 18 frames held, Kafrizz from 81 (held as long as special is, stored by shielding). Released (a tap
  too) -> SpecialN1 / N2 / N3, the fireball out at frame 10 / 11 / 16; shield while holding ->
  SpecialNCancel, the charge kept for the next one (lost if he's hit while charging, or loses a
  stock). Actionable from Ultimate's cancel frames (44 / 52 / 68, cancel 6) through Robin's
  `func_2246`; the air motions are swapped in by Robin's `func_2245`. Air: the fall slowed while
  charging and through Frizz (x0.8). Motions: Robin's 0x21F start, 0x223 hold, 0x227 N1, the shoot's
  custom-move variants 0x228 / 0x229 N2 / N3, Thoron's start 0x22F cancel (air + 0x1C; extra_kinds.json
  "motions", `specials_acmd.json`).
- Fireball (weapon kind 0x190, a copy of Robin's thunder, article 6; `weapons/fireball.c`): the level
  from the custom N slot; Frizz 1.6 (slowing from frame 30), Frizzle 2.4, Kafrizz 0.3 + 0.1 a frame
  up to 4.0; life 56 / 46 / 58 (`param_fireball`); bursts on a hit, a wall / the floor or at its
  life's end (BurstS / M: the hit effect; BurstL: the explosion's hits at 1 and 19). Its scripts are
  Ultimate's `brave_fireball` ones on its bone 0 (Frizzle's two balls in one place).

Not yet: MP (every spell works; Ultimate's MP checks taken as passed), Zap / Woosh / Command
Selection, the stored-charge glow on his hand (`brave_fire2_hold_flash` / `fire3_hold_flash`, status
code in Ultimate), Frizz's damage drop at frame 30 (`ATK_POWER` 9 -> 6), the air shoot hop, his sounds
(Robin's charge sound plays in the hold).

## v4 (`build/hero_v4.zip`): Zap and Woosh

Built as v3 (`tools/brave_build.py`, the effect bank with 18 more effects: 35 of his 103, 6.4 MB, five
turned variants; motions `--add` the side / up special animations too, extra_kinds.json "motions").
- Side special (status 0x153, Robin's Arcfire; `brave.c` `brave_s_*`): SpecialSStart, SpecialSHold while
  held (Zapple from 9 frames, Kazap at 26, which goes off by itself), released -> SpecialS1 (Zap) /
  S2 (Zapple); Kazap: SpecialS3 (the sword raised) then SpecialS32 at its frame 19 (the strike; Ultimate's
  lightning starts 85 above at frame 10 and falls 10 a frame). The bolts are his own hitboxes. When one
  hits, Zap's lightning lands on that fighter: the spark article (weapon kind 0x191, article 7) at its
  player slot, once a fighter per cast. The slot is found from the last fighter hit's offset and the slot
  positions (docs/position-variables.md); the spark waits 3 frames (activate_wait_frame) and hits for 8.
  Motions: start 0x258 / 0x25C, hold 0x259 / 0x25D, Zap 0x257 / 0x25B, Zapple 0x25A / 0x25E, Kazap
  0x230 + 0x231 / 0x24C + 0x24D (Thoron's slots).
- Up special (status 0x154, Robin's Elwind; `brave_hi_*`): SpecialHiStart, SpecialHiHold (Swoosh from 10,
  Kaswoosh at 28, by itself), then SpecialHi1 / 2 / 3: the tornado article (0x192, article 8) at his own
  slot's position at frame 4 / 6 / 8 (24 / 33 / 52 frames, param_tornado), the rise from frame 5 / 12 / 11.
  Ultimate's rise is jump_distance 42 / 64 / 99 at jump_accel_y 0.145 / 0.16 / 0.1. Here it starts at
  sqrt(2 x distance x accel) and slows by that accel to 0. Then the slowed fall (end_accel_y x0.96,
  end_max_speed_y) runs to the motion's end -> SpecialFall; landing -> LandingFallSpecial. Ledges from
  frame 11 / 20 / 18 (Robin's `func_56`); the charge's air fall held to 0.45. Motions: start 0x260 / 0x26C,
  hold 0x261 / 0x26D, Woosh 0x25F / 0x26B, Swoosh 0x262 / 0x26E, Kaswoosh 0x263 / 0x26F.
- Articles: `weapons/thunder_base.c` (Robin's thunder MSC up to `func_40`) + `fireball.c`, or + `placed.c`
  + `spark.c` / `tornado.c`. Placed articles read level + 4 x slot from their custom number and move to
  that slot's fighter (the position variables). A hit keeps them on ("on_hit": 1, instead of thunder's
  removal). Their scripts are Ultimate's `brave_spark` / `brave_tornado`.

Not yet: Command Selection (down special: still Robin's Nosferatu), MP, Kazap's armour (15 damage), the
air hop when Zap hits, Woosh's sideways speed params (his normal air control), the special-fall landing
lag per level (12 / 22 / 29), sounds.

### v4b: the executable fixed (`build/hero_v4b.zip`)

From v1 on, the new fighters' articles made `weapon_expand.py`'s cave (0x04B8C000, its LIMIT
0x04B92000) run past 0x04B90000 into `acmd_ext_cave.py`'s code (the ACMD extra commands): 893 of its
1627 words overwritten in v4's executable (`tools/acmd_ext_test.py` crashes on it; the kind / weapon
tests didn't see it: they compare the caves' outputs with `--others`, and acmd_ext's wasn't passed).
weapon_expand.py's cave is now 0x04BB0000-0x04BB8000 (kind_expand.py's ends at 0x04BB0000). Test with
`--others` for every cave in the executable (acmd_ext, series, smash_button too) and run
`acmd_ext_test.py PATCHED build/cross_f.rpx`.

## v5 (`build/hero_v5.zip`): Command Selection, with its menu in the damage panel

```
python3 tools/brave_build.py ... --menu TRAIT_DMG_DIR       (v4's command + the damage panel with the trait badge)
```
- Down special (status 0x155, Robin's Nosferatu; `brave.c` `brave_lw_*`): SpecialLwStart, then
  SpecialLwSelect with the menu open. Four spells are drawn at random, weighted by Ultimate's
  `param_special_lw_command_data` lot_prob, among the spells made so far (`brave_lw_weight`). The stick
  moves the cursor (up / down past 0.5, again every 12 frames while held). Attack, or special once it
  has been let go, casts; the cast spell's row stays up 30 frames. Shield or 480 frames
  (command_select_time_limit) -> SpecialLwCancel. The air fall is held to 0.45 while choosing. Spells so
  far: 17 Flame Slash, 18 Kacrackle Slash, 19 Metal Slash, 20 Hatchet Man (Ultimate's SpecialLw17-20 /
  SpecialAirLw17-20, their sword hitboxes and effects).
- The menu: Ultimate draws it next to Hero; here it is four rows above his damage panel
  (`ui/info/dmg`): `tools/brave_menu_art.py` draws a plate for each of the 21 spells, plain and highlighted
  (name, MP cost); `tools/dmg_brave_menu.py` adds a row sprite (frame n = spell n, 21 + n highlighted)
  placed four times (`spell0_mc`-`spell3_mc`) in each panel layout, on texture slot 134
  (`img-00134.nut`, BC3 512x1024). `tools/trait_badge_cave.py`'s menu routine (0x04B85000, run for every
  panel slot after the trait badge) shows them for a Hero (the fighter object's kind 0x45) from his
  work ints 0x1000009E (0x4845xxxx: bit 2 open, bits 0-1 the cursor's row) and 0x1000009F (0x48xxxxxx:
  the rows' spells, 5 bits each), and hides them everywhere else. `tools/trait_badge_test.py` covers it.
- Motions: start 0x277 / 0x283, select 0x278 / 0x284, cancel 0x279 / 0x285, spells 17-20 0x27A-0x27D /
  0x286-0x289 (Robin's Nosferatu slots; Ultimate's spell animations are shared: Flame and Kacrackle
  Slash both play `skill3`).

Not yet: the other 17 spells (Heal, Sizz / Sizzle, Bang / Kaboom, Whack / Thwack, Magic Burst,
Kamikazee, Kaclang, Acceleratle, Oomph, Bounce, Snooze, Hocus Pocus, Zoom, Psyche Up), MP (the costs
are on the plates; nothing is spent or greyed out yet), Metal Slash's metal KO, the menu blinking near
its time limit.

## v6 (`build/hero_v6.zip`): the window drawn like Ultimate's

Ultimate's window, from SmashWiki's screenshots (`Hero_MP_Comparison.png`: the international version;
the Japanese one has a white frame): one translucent black window with rounded corners and a dark brown
frame over the left two thirds of the panel, the four names in white (no costs on the lines), Dragon
Quest's gold pointer (two knobs and a tapered blade) over the window's left edge by the chosen line, and
a small window "MP nn" with the chosen spell's cost at its bottom right. `tools/brave_menu_art.py` draws
them to Ultimate's proportions (`LAYOUT`, in the 1-4 player panel's units) at 1.25x, in the Wii U's
shared font (FOT-Rodin: `--menu-font` Cemu's `resources/sharedFonts/CafeStd.ttf`; not in the repository,
Inter Medium stands in without it). `tools/dmg_brave_menu.py` puts them on one 1024x1024 texture (slot
134) and places `cmdwin_mc`, `spell0_mc`-`spell3_mc` (names, + 21 greyed for MP), `cmdcur0_mc`-
`cmdcur3_mc` and `cmdmp_mc` in each panel layout (the 5-8 player and small panels at 0.8, moved as the
trait badge is). `tools/trait_badge_cave.py`'s menu routine goes through the ten elements (window: open;
names: the row's spell, greyed by int 0x1000009F bit 20 + row; pointer: the cursor's row if it has a
spell; MP window: the cursor's spell). Shield or jump shuts the menu (SmashWiki); the chosen spell's
window stays up 70 frames (decided_command_window_close_frame).

Not yet: the MP bar above the panel (Ultimate's blue "MP 100" bar) and MP itself; the window's
opening / closing animation.

## v7 (`build/hero_v7.zip`): MP, the other 17 spells, Ultimate's menu

**MP** (`brave.c` "Hero's MP", `brave_frame` in place of the per-frame `func_82`): 100 at most, full at the
match's start (Entry) and after each stock (Rebirth, `func_235` → `brave_rebirth`); 1 back a second
(`sp_recover_frame` 60), not while a special charges or the menu is open; 0.8x the damage his other
moves deal (the other fighters' damage, through the position variables' slot `DAMAGE`, taken while his
attack has hit; his specials don't count). Costs (Ultimate's `sp`): Frizz / Frizzle / Kafrizz 6 / 16 /
36, Zap / Zapple / Kazap 8 / 18 / 42, Woosh / Swoosh / Kaswoosh 5 / 9 / 18; a charge pays for the highest
level his MP covers (Kazap / Kaswoosh wait for the release instead of going off by themselves); with
none, the spell fizzles: `SpecialLwFail` (N, S) or `SpecialHiEmpty` (a hop, no whirlwind). The menu
greys out the spells he can't pay for and puts them last; choosing one: `SpecialLwFail`.

**The gauge and the menu, from Ultimate's files**: `tools/brave_menu_art.py` reads Ultimate's battle
HUD (`ui/layout/info/info_melee/info_melee/layout.arc`, `--menu-layout`; `tools/sarc.py`,
`tools/bntx.py`): the part `p4_info_melee_lct_brave` gives the window, the one-row window of a cast spell,
the cost window, the 16-frame spinning pointer, the gauge's pill and its blue / green fills, and their
places (its panes) and behaviour (its animations: the pointer's spin, 2 frames a texture; names greyed
x 107/255; the window greyed when the spell at the cursor is too dear; the fills stretched 1-159 px for
0-100 MP; the cast spell's row window). The text (names, "MP", numbers) is the Wii U's FOT-Rodin, at
Ultimate's sizes. The MSC writes three ints the panel cave reads (`tools/trait_badge_cave.py`):
`0x1000009C` the gauge (MP, and what's left after the cost in view: green), `0x1000009E` the window
(shown, cursor, opening / closing frame, cast, blinking in the last 2 seconds of the 8-second limit,
the pointer's frame) and `0x1000009F` the rows' spells and which are greyed. The window opens and closes
with a short vertical stretch (5 + 4 frames).

**The spells** (`brave_lw_cast`; Ultimate's scripts for the motions, extra_kinds.json "motions" in
Robin's free slots `0x220`-`0x26A`):
- Heal: 11% healed. Sizz / Sizzle, Bang / Kaboom, Whack / Thwack, Snooze: articles 9 / 10 / 11 / 13
  (`weapons/shot.c` + `flash.c` / `explosion.c` / `deathball.c` / `sleep.c`, weapon kinds 0x193-0x195,
  0x197): a flame that bursts into a pillar on a hit, a bomb that explodes at its range's end or on a
  hit, a curse that KOs a fighter it touches with Ultimate's chance (sent below the blast line), a gust
  whose hitboxes put fighters to sleep (Effect 9).
- Magic Burst (all his MP) / Kamikazee: the crash article (12, `placed.c` + `crash.c`) on him; Magic
  Burst holds him in the air to frame 136; Kamikazee KOs him at its end (v8: flag 0x20000043).
- Kaclang: invincible steel for 300 frames. Acceleratle: 600 frames of x2 speeds (`kirby_stat_cave.py`
  profile 3 through the marker int `0x1000008E`, which Robin's Levin Sword code no longer touches).
  Oomph: 720 frames of x1.15 damage; Psyche Up: x1.15 until his next hit lands (`strike_cave.py`'s
  bit). Bounce: 720 frames of a reflector (x1.5 damage, x1.2 speed). Hocus Pocus: one of full MP, no
  MP, 600 frames invincible or invisible, Oomph, Acceleratle, Psyche Up, a Kaboom, a Sizzle. Zoom: up
  off the screen (intangible), then down above a fighter on the ground.

**Bounce's reflector** (`tools/brave_reflect_cave.py`, tested by `tools/brave_reflect_test.py`): every
fighter has room for reflector groups, but only a kind's own setup gives one a shape (Kirby's and
Zelda's do, Robin's doesn't, so a reflector on Robin's kind wrote into an unused slot and nothing
reflected). The first instruction of Robin's setup (`0x02F60194`) now goes through a cave that sets up
reflector group 3 with one shape as Kirby's setup does (`REFL_GROUP_INIT` `0x02C6F5FC`, then
`0x0200BD8C`); the MSC (`brave_reflect`) gives it its shape (`ShieldModule(0x2717, 3, ...)`) and turns
it on / off. Robin gets the (unused) group too.

Smaller: `tools/ultimate_acmd.py` maps `collision_attr_ice` to Smash 4's freezing (4, Lucas's PK
Freeze: Kacrackle Slash freezes), `sleep_ex` to sleep, `virtualcenter` to the hip; Ultimate's `f32::NAN`
shield damage is 0; `sys_misfire` (a spell failing) is the attack smoke. The effect bank has the spells'
effects (75 sets; 10.9 MB, Robin's 2.5 MB included).

Not checked in game: everything above (the executable caves are emulator-tested, the MSC isn't).
Approximations: Oomph / Psyche Up are x1.15 damage (Ultimate: x1.2 and x1.1 knockback), Acceleratle one x2
on every speed, Whack's chance formula is used for Thwack.

## v8 (`build/hero_v8.zip`): Magic Burst scales, on-the-spot KOs

- **Magic Burst** scales with the MP it takes: the crash article has four weaker copies of Crash1 (each
  hit x 0.2 / 0.4 / 0.6 / 0.8: `tools/brave_build.py` `CRASH_TIERS`), Hero picks one from the MP spent
  rounded up to the next 20 (`brave_burst_motion`; over 80: the full 44.6%). `placed.c` now takes each
  article's level count and lives from it (`pl_levels`, `placed_life`).
- **Whack / Thwack** KO with the game's own instant KO: a successful roll puts the curse on that fighter
  for 3 frames playing `deathballko`, its hitbox with effect 0x10 (Death: "instantly KO fighters", Smash
  Run's Orne; the hitbox effects sheet in `docs/resources.md`), its own hit group, unblockable, fighters
  only; then it goes back on its way (`deathball.c` `sh_tick`).
- **Kamikazee** KOs Hero at its end with instance flag `0x20000043` ("causes KO": he explodes as if KO'd,
  as in Stamina mode; `reference/msc-note-sheet/Variables.csv`), as the user's Captain Falcon's 1-in-100
  jab does (`ON_FLAG 0x20000043`).

## Fix 9 (`build/hero_steve_fix9.zip`, with Steve's): his head, his stats

- Head: Robin's `model.jtb` table 1 (`SwordN`, `FaceN`: bones Robin's own code drives) had been pointed
  at RHaveN / HeadN, and in game his head came off his neck. Each is now a bone of its own
  (`ultimate_fighter.py` `Skeleton.add_joint_bones`, as Steve's; fighters/pickel/README.md); his
  `--max-bones 120` now counts them, so the costumes at the cap merge two more skirt tips
  (`S_SkirtRB3` / `RB4`; c00 / c03 / c04 / c07 change their NUDs).
- Stats (fighter_param kind 0x45; they were Robin's), Ultimate's, as Steve's:
```
python3 tools/fighter_param.py set fighter_param.bin OUT 69 1=0.16 2=0.08 3=0.98 7=0.05 8=1.88 9=0.08 10=0.03 11=1.84 13=0.95 \
    14=0.8 15=1.2 16=1 17=23.8 18=13.95 19=31 20=0.045 21=0.01 22=1.01 23=0.008 24=0.094 25=1.57 27=2.512 28=10 29=12 30=14 \
    31=8 32=18 33=101 34=2
```
- Fix 10 (`build/steve_fix10.zip`): jump squat 3 frames (Ultimate's; Robin's 6): fighter_param 12.

## Fix 11 (`build/hero_seph_fix11.zip`): the compiler bug behind his specials

msclang compiled a call whose value is used and whose arguments call functions too (`f(g(x))`) with
the push bit on the inner call's `try` instead of its own (`addArg` took the nearest `try` back), so
`f`'s value never reached the stack. His MP checks are all `brave_can_pay(brave_*_cost(level))`: every
frame of neutral / side / up special and the menu (`brave_*_hold_level`, `brave_*_loop`, `brave_lw_grey`
/ `_draw` / `_loop`) left the VM stack a value off (no spells, wrong motions, no menu). Fixed in
`tools/msclang_nested_call.patch` (applied by `tools/setup_toolchain.sh`); `tools/msc_stack_check.py`
(the stack depth along every path of every script) found these 9 and nothing else in any fighter
but Sephiroth's two (`edge_n_change` / `edge_n_loop`).

## Fix 15 (`build/hero_fix15.zip`): his spells appear

- None of his articles past Robin's were ever made: the ArticleModule makes instances only for the
  article-list entries before the first special one (bit 31; Robin's id 6, kind `0x80`), and his 8 were
  added after it (docs/weapon-expansion-code.md section 2). `weapon_expand.py` now puts a fighter's new
  articles before its base's first special entry, so his are ids 6-13 (fireball 6, spark 7, tornado 8,
  flash 9, explosion 10, deathball 11, crash 12, sleep 13) and Robin's special one is 14; `brave.c`'s
  `brave_generate` ids follow. Only his list changes (Supamario's and Sephiroth's have no special entry
  before their new ones).
- Neutral special: fully charged (81 frames: Kafrizz) it went off by itself; undone after (Ultimate's
  holds it, and shielding stores it).

## Fix 16 (`build/hero_fix16.zip`): the side tilt's second hit, his shield on his back

- Side tilt 2 (fix 16 tried the game's own side-tilt combo, status 0x28 `func_276`: a second press once
  the script sets `0x2100000D`, Ultimate's `ENABLE_COMBO` at frame 16, plays motion 0x59 up to
  fighter_param 265 `attack_s3_count`, set to 2; in game the first hit only repeated. Fix 17: Hero's
  own loop, `brave_s3_*`, and 265 back to 1). Motion 0x59 (empty in Robin's table) plays
  Ultimate's `c01attacks32` (extra_kinds.json "motions", `--add C01AttackS32`); its script from
  Ultimate's `AttackS3S2` (specials_acmd.json, slot 0x59; the vl's cancel frame 48 for it).
- Shield: Ultimate hides `brave_shield` and shows `brave_shieldb` (on his back) in 180 motions (smash
  charges, specials, Command Selection). Robin's Final / Result mouths are never shown in battle (her
  face material animations never key them on), so they now hold the shield in hand / on his back
  (`ultimate_fighter.py` `REFLET_VIS` / `REFLET_F_VIS`), driven per motion by those two tracks (the hand
  one shown where a motion has none); the motion step reads each costume's own slot names (male and
  female Robin's differ). Her two mouth meshes (`brave_Mouth_Final`, `PatternA`) are left out.
- Built as before, with BRAVE_BODY = Robin's vanilla `script/animcmd/body` with the universal-mechanics
  `game.bin` (the roll-off scripts): a body folder whose effect.bin already has Robin's effects moved to
  kind 0x45 (`0x445....`) would point her leftover effects at Hero's bank instead of hers.

## Fix 17 (`build/hero_fix17.zip`): his textures, side tilt 2, the held Kafrizz

- Fix 16 shipped the rebuilt models without their `model.nut`: the shields' new slots change the
  texture list's order (same size, other ids), so every costume drew the old textures in the wrong
  places. Ship a costume's `model.nut` whenever its `model.nud` is rebuilt.
- Side tilt: status 0x28's main is Hero's `brave_s3_main` (Robin's `func_275` with its own loop):
  an attack press from the status's third frame on is kept, and from motion frame 16 the loop plays
  motion 0x59 (`AttackS3S2`) once, then hands on to Robin's `func_277`.
- Neutral special: at 81 frames (Kafrizz) the flash (`brave_chant_finish`, `EffectModule(0x2717, ...)`;
  Ultimate's `SpecialNHoldMax` also has `brave_fire3_hold_flash`, not in his bank yet) and the charge is
  stored as a shield cancel's (`brave_n_change(3)`); a stored Kafrizz is cast at once (fix 15's
  auto-release undone).
- Mouth: fix 16 gave every motion a face entry (for the shields), and an entry replaces `default.mta`,
  so the motions Robin has none for lost the default mouth. `ultimate_fighter.py` now starts those
  entries from the default's keys (Steve's tools, the same mechanism, get it too on his next rebuild).

## Fix 18 (`build/hero_fix18.zip`): his hurtboxes, ECB and ledge-grab boxes

`tools/ultimate_vl_shapes.py VL_IN VL_OUT HERO/param/vl.prc MODEL/c00` (over the vl with Ultimate's
blends, `ports_dash_fix`): Ultimate's 11 hurtboxes (Robin's 7) and their hit points (group 10), its ECB
points (head -0.5 x, shoulders, knees, hip; Robin's had the forearms) and ledge box (0, 10.5, 16.5,
16; Robin's (0, 8, 16, 16)), the tumbling box (0, 4, 9.9, 9.6).


## Fix 19 (`build/hero_fix19.zip`): no tomes or Levin Sword thrown away

Robin's code still counted her tome and Levin Sword uses down (her jab, smashes, aerials and the
special statuses Hero's moves sit on): a spent one set a bit in `0x10000091` (`BattleObject 0x3ec`) and
the status check `func_2254` sent him into her discard status `0x8c`, the tome or sword thrown, then
her pick-up status. `brave_keep_items()` (in `brave_frame`) keeps the five counters full every frame
(Thunder `0x10000083`, Elwind float `0x2f`, Arcfire `0x1000008a`, Nosferatu `0x10000086`, the Levin
Sword `0x1000008c`) and clears the bits; `func_2254` never changes status. Only `brave.mscsb` changes.
