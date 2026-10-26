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

## Fix 20 (`build/hero_fix20.zip`): Woosh's whirlwinds, multi-hit placed articles

- Whirlwinds: their meshes are directional (velocity-aligned) with `rotate_init` X 180 but
  `is_rotate` 0 1 0; turned so they hung upside down under the stage. `tools/vfxb_to_ptcl.py` drops a
  directional mesh's rotation about the axes `is_rotate` disables (observed on these; billboards and
  the chant's type-4 rings keep theirs). 32 emitters change: the three Woosh sets, Acceleratle /
  Oomph's whirlwinds, the charge wind, the smash crown's Z wobble.
- Multi-hit: the placed articles' first hit asked for status 1 (`"on_hit": 1`), and the status change
  cleared their hitboxes: Swoosh / Kaswoosh (Ultimate's re-hit 7) hit once. `weapons/placed.c` goes
  to status 1 at once from status 0; status 1 places the article and plays its motion, and a hit then
  changes nothing.

## Fix 21 (`build/hero_fix21.zip`): effect brightness

The Frizz test (`hero_frizz_test`: each charge level's fireball with one group of Fire1Bullet's
emitters: glows, sparks, fire) showed the purple in all three, always at the brightest spot: Smash 4's
bloom / glare on colours far over 1 (Frizz's spark1 4.4 = colour x `color_scale` 4.0; 86 of Hero's 840
emitters over 2.5, vanilla's 99th percentile 2.0). `tools/vfxb_to_ptcl.py hdr_scale` compresses a
particle's peak over `HDR_START` 1.2 to a quarter (4.4 -> 2.0), hue kept, through `color_scale`: 387
emitters change.

## Fix 22 (`build/hero_fix22.zip`): Robin's Thunder orbs, Kafrizz's ball

- The purple crescent on every Frizz level (the Frizz test, then fix 21, kept it) is Robin's own
  Thunder orb: the fireball is a Thunder copy and the game's code plays the base bank's entries 1-3
  (Thunder / Elthunder / Gigathunder bullet) on it. `tools/vfxb_to_ptcl.py --empty 1,2,3,4,6,7,b`
  empties those entries (set, model, meshes 0, as 403 vanilla entries): Thunder bullets / hit,
  Thoron, the Levin Sword's sparkle and flare model.
- Kafrizz's solid yellow disc: `sphere1` has eft2's fresnel alpha (0.3 - 1.0). Ultimate's vertex
  program (the WindowSmash shader translator on `ef_brave.eff`) multiplies the alpha by
  smoothstep(near, far, |N . V|); on a billboard mesh (types 0 / 7) turning only about Z, V is the
  mesh's Z, so `fresnel_bake` puts it in the vertex alpha. 8 emitters (the ball, Bounce's barrier,
  Acceleratle / Oomph's flare3); the other ~90 fresnel emitters need a shader with the view vector.

## Fix 23 (`build/hero_fix23.zip`): whirlwinds upright, colours held near 1

The whirlwind test (each Woosh level one part: meshes red, particles red, meshes opaque): the meshes
drew as a flat red ring at his feet, the whirlwind end-on (eft's type 3 on a mesh); the particles
drew; the opaque pale-blue meshes glowed purple. So:
- `vfxb_to_ptcl.py`: a directional mesh whose velocity is only along the emitter's Y (no
  all-direction speed or spread) is type 4, the emitter's frame (48 emitters).
- `HDR_START, HDR_KNEE = 1.0, 0.05`: vanilla fire keeps its colour keys at 1.0 - 1.05 (the colour in
  its textures); colours over that glowed purple in the bloom.
- `fresnel_bake` takes the normals from the triangles (`face_normals`): Kafrizz's `sphere1` model has
  none, and the +Z default baked a flat 1.

## Fix 24 (`build/hero_fix24.zip`): Kaswoosh's two whirlwinds, no Thunder orb on Frizz

- Kaswoosh: Ultimate's two whirlwinds sit on the article's bones Tornado1 / Tornado2, which its
  `d02specialhi3` animation sends round each other (3 - 12 units out); with no model here both
  drew on bone 0, the same as Swoosh's one. `brave_build.py` puts them `KASWOOSH_SPREAD` (7) either
  side along Z with their hitboxes (IDs 0 / 2 / 4 and 1 / 3 / 5), and adds the launch Ultimate has
  under `if life <= 2` (dropped by the translator) at frame 50 of its 52.
- Frizz's purple-blue orb, every level, through fixes 21 - 23: Robin's own Thunder orb, played by
  the game's native Thunder code (0x031DBDF4: effect `0x032C0001` - `3` by charge level) from
  Robin's real bank, which `base_effects_cave.py` loads for Hero too; Hero's articles are copies of
  the Thunder, so they ran it. `tools/thunder_orb_cave.py` gives every other kind effect id 0 (as
  the code does itself for levels over 2).

## Fix 25 (`build/hero_fix25.zip`): own pixel programs for every effect part (test)

The fix 24 videos against Ultimate's: Frizzle's flames dark red blots (Ultimate's white-yellow to
orange), the whirlwinds faint. Ultimate's `ef_cmn_fire00` is a flipbook whose alpha is the flame and
whose rgb its hot core, coloured colour 1 -> colour 0 by it; Smash 4's stock pixel programs take a
texture's colour and alpha from one channel, so `combine()` folded every part into one shape and one
colour (the life mean: red). Now (`tools/eft_pixel.py`, docs/ptcl-format.md "Pixel programs"):
- every emitter keeps its template's vertex program and gets a pixel program of its own: eft2's
  colour modes 0-3 and alpha modes (erosion included) exactly, from an RGBA texture (BC5 R R R G
  when the colour input is grey) holding Ultimate's colour input in rgb and its alpha input in a,
  the other samplers combined in with eft2's own multiply / add (`exact_texture`);
- alphas past 1 (the whirlwind body's custom shader 8 at 2 - 4x) become the program's gain;
- templates: any slot-0 format (the program is ours), ranked first by whether ours can replace
  theirs, then by animated colour tracks where Ultimate's change (fire1's white flash at birth was
  lost to a constant template). All 563 of Hero's emitters take the new path (`--no-exact`: the old).

## Fix 26 (`build/hero_fix26.zip`): F-smash crash

Fix 25 crashed on F-smash's ground hit (Cemu log: PPC 0x04A5E154, a null read of the emitter
instance's +0x2A0, from 0x04A63A20). The runtime calls a per-particle hook for each of the emitter's
words 0x32C - 0x33C (0x04A62744 ff.); value 2 animates by the key-animation table, which
`Ptcl.import_emitter` doesn't copy. Fix 25's colour-track ranking picked seven such templates (the
ground flare among them); templates with key animation are now left out. Converted meshes also always
get normals (from their triangles) and a vertex colour: an absent attribute is an empty buffer, which
a template reading it hits ("GX2RSetAttributeBuffer(): Offset exceeds buffer size").

## Fix 27 (`build/hero_fix27.zip`): Ultimate's brightness, clamped in the pixel program

F-smash on fix 26 against Ultimate's: the ground spikes (`impact2_frontL`: colour mode 1, colour 0 x
`ef_donkey_line01`'s rgb, grey bands 0.2 - 0.8 under a solid spike alpha, colour scale 2.0) drew
dull grey with dark tips; in Ultimate the product runs past 1 and saturates yellow. `hdr_scale`
(fix 21 - 23) had squeezed the colour to ~1.05 before the texture multiplied it. With own pixel
programs the colour scale is now Ultimate's and the program clamps the drawn colour to 0 - 1 where
it's last written (nothing past 1 reaches Smash 4's bloom, the purple haze `hdr_scale` was for).
Template programs (`--no-exact`) still get `hdr_scale`.

## Fix 28 (`build/hero_fix28.zip`): hidden emitters, colour 1 on every template, mesh samplers

- F-smash's solid yellow zigzag was `impact2_frontL`, which has eft2's `is_particle_draw` 0: Ultimate
  never draws it (no child emitters either). Such emitters are skipped (4 in Hero's bank: Tornado3
  rock1, Flash1 / Flash2 flare2 too).
- Kafrizz's black ball: `sphere1` / `spherering1` / `flare1` (colour mode 2) got templates whose
  programs pass colour 0 only (inputs 0, 6, 10); `eft_pixel.source` fell back to colour 0 x texture,
  and sphere1's `ef_cmn_grade00` (alpha 1 everywhere, rgb a dark-ended gradient) at alpha 2 drew an
  opaque black ball. Templates are now ranked by passing colour 1 when the mode needs it, and a
  program on one that doesn't gets colour 1 as constants (its life mean x the colour scale).
- A mesh's other samplers (sphere1's `ef_brave_mask02`) come in as their mean (they read other UVs).

## Fix 29 (`build/hero_fix29.zip`): flipbooks shown as one cell fade by their cells' ink

F-smash on fix 28: the spike burst and ring still solid where Ultimate's are see-through. Their
flipbooks (`ef_cmn_impact00`, `ef_brave_ring00`: eft2 pattern 1 / 2) have no template with the mode,
so the first (thickest) cell showed all life. `flipbook_fade` scales the alpha track by each cell's
mean alpha as Ultimate plays the table (life-fit: spread over the life; clamp / loop: a cell each
`frequency` frames) against the shown cell's: 104 of Hero's emitters (impact1 ends at 0.14, the ring
at 0.17). The crown (`crown2_back`) is as opaque in Ultimate's data (texture red x vertex alpha x
alpha 1, emitter alpha cb10[48] = 1 with no LAST_EFFECT_SET_ALPHA in the script).

## Fix 30 (`build/hero_fix30.zip`): UV scrolls run Ultimate's way

F-smash on fix 29 (colour test: `crown2_back` green): the crown's band is a wide solid wave that stays
up all life; Ultimate's is a thin crown of spikes that sinks into the floor in its 8 frames. Its UVs
scroll V by 0.09 + 0.07 a frame with the scale growing 0.7 + 0.08 a frame (V clamped): in Ultimate,
scale (v - 0.5) - shift + 0.5 moves the texture's white band down the cone (v = 1 is its foot) and
under it, leaving the spikes. The converter wrote the shifts negated, so the band climbed the cone
and stayed. eft subtracts them as eft2 does: cross_f.rpx 0x04A5A6AC copies 0x514-0x54C into the
static uniforms (shtAnim0) unchanged, and every vanilla vertex program that scrolls (621) draws
s (uv x repeat - 0.5) - (frame x rate + initial +- random) + 0.5 on U and V. `set_uv_anim` now
writes eft2's values as they are: every scrolling part of every converted effect turns round (the
fire's flow, the whirlwinds, F-smash's crown). The earlier corpus reading (`docs/ptcl-format.md`) is
corrected; Sephiroth's bank still has the negated shifts until it is rebuilt.

## Fix 31 (`build/hero_fix31.zip`): whirlwinds move and show

Test 30 (Woosh / Swoosh / Kaswoosh against the Ultimate video): the whirlwinds thin, faint blue
arcs at the floor; Ultimate's thick white columns of rising streaks.
- **UV animation ranks before the colour tracks** (`Templates.get`). Woosh's `tornado1_*` (their
  streaks stretch over life: UV scale animation) took templates without it, picked for follow type 2
  (position only) and animated colour, and stood still. Position-only following now takes a
  fully-following template (no type-4 mesh template with follow 2 animates UVs), then the UV
  animation decides. Bakes frozen at their start: 145 -> 76 of Hero's emitters.
- **What a template can animate keeps animating.** A scroll-only template for a part wanting scroll
  and scale (Swoosh's `tornado2`) had the whole UV transform frozen into the mesh; now only the
  starting scale (or rotation) is, and the scroll runs (7 emitters).
- **Bakes about the texture's centre:** `uv_transform` scaled about the corner (uv x scale - shift);
  both games scale about the centre (the same reading as fix 30's), so every baked mesh with a UV
  scale was offset.
- **Alpha input 2 is "one":** Ultimate's shader for `tornado1_f2` (WindowSmash) never reads its second
  texture's alpha; taken as that alpha (mean 0.34), it dimmed the whirlwind to a third.
- **Same-UV samplers combine texel by texel** on meshes: Swoosh / Kaswoosh's columns multiply
  `ef_cmn_wind00` by itself through identical UVs (red x alpha), which had come in as its mean
  (x 0.39, flat). 14 emitters.
Still missing on the columns: the dissolve threshold (custom shader 8, `CSDP`).

## Fix 32 (`build/hero_fix32.zip`): second textures drawn live, the dissolve

Step 1 of "a template for every Ultimate effect": own pixel programs that read two textures, each
with its own coordinates and UV animation, and Ultimate's dissolve.
- **Two-texture templates** (`tools/eft_pixel.py`): a vanilla program sampling slots 0 and 1
  straight from its inputs is replaced by one that samples both and combines them as Ultimate does
  (texture 0 x or + texture 1, colour and alpha each by eft2's tex1 / tex2 blend), then the colour /
  alpha combiner. The vertex program is the template's: slot 1's UV block (0x550) gets the second
  sampler's repeat, scroll, scale and rotation (`set_uv_anim(..., slot=1)`).
- **Which sampler goes live** (`live_sampler`): one moving apart from the main one (its own UV
  animation, repeat or UV set; a mesh: the same UV set only). The two trade slots when the template
  animates them better that way round (texture 0 x texture 1 either way), 15 emitters. 81 of Hero's
  emitters now draw a second texture moving as Ultimate's does (fire's flow over its shape, the
  whirlwinds' second layer, the auras' noise) where it came in frozen at its start or as its mean.
  Still frozen / meaned: 27 whose mesh UVs are baked (the template can't animate slot 0's UVs; slot
  1 would read the baked ones), 34 with no two-texture template of their type, blend, follow and
  flipbook mode.
- **Templates with shader parameters** whose vertex program parameter-free emitters run too count
  as plain once their pixel program is ours (half the two-texture templates had parameters).
- **Dissolve** (Ultimate's custom shader 8, read from Woosh's / ring2's Maxwell code): a pixel goes
  where sampler 1's alpha is under colour 1's alpha (over life: the whirlwinds eat away from 7% to
  100%), alpha x (mask - threshold) / width over the edge (width: the `CSDP`'s first float, 0.05 /
  0.12). Our program reads the mask from texture 0's green (grey colour in red and blue; RGBA8,
  uncompressed) and the threshold from a colour track: colour 1's (colour 1 then a constant in the
  program), or colour 0's when its rgb is constant (6 emitters). Smash 4 scales colour tracks by the
  colour scale (cross_f 0x04A588CC): the threshold is written divided by it. 10 of the 14
  converted dissolve parts (fix 32's notes said 14 of 18, counting the undrawn ones twice); Woosh's
  `tornado2_f` (and the three Wind ones) don't: no template animates both its scroll and a colour
  track, and the scroll ranks first. (Fix 33: all 14.)

## Fix 33 (`build/hero_fix33.zip`): templates chosen by what their vertex programs draw

Step 2 was to be vertex programs of our own for meshes. Reading the vanilla ones first
(`tools/eft_vertex.py`, `docs/ptcl-format.md` "Vertex programs") showed most of the template limits
the converter worked around aren't in the programs at all:
- **UV animation:** the slot's mode word (0x510) is read by nothing (not the uniform fill, no
  vertex program); a program draws all of a slot's scroll, scale and rotation or none (13022
  vanilla emitters checked; 2900 slots run a full program under a narrower word). Templates were
  ranked by the word: "UV animation 7: template has 2" and its mesh bakes mostly weren't real.
- **Flipbooks:** the CPU turns the mode word (0x500) into flags every flipbook program tests, all
  five modes; any flipbook template plays any mode once the word is Ultimate's.
- **Follow types:** the CPU's (0x310); one program serves 0, 1 and 2 (only programs reading the live
  emitter matrix need 0). The converter now writes Ultimate's; it kept the template's before.
- **Blend:** the emitter's (0x324); a template whose pixel program is ours serves any blend.
- **Shader parameters** a template's vertex program doesn't read don't count against it once its
  pixel program is ours.
- **Key-animated templates** are usable: their per-particle hooks (0x32C - 0x33C) set to 2 (by key
  animation, which reads the dropped table: fix 25's crash) are written as 1, as on every other
  emitter. Pikachu's type-4 mesh is the only flipbook template of its kind.
- Ranking: a flipbook played before the UV animation, the main texture's UV animation before a
  second texture (missing on a mesh, it bakes slot 0's UVs and the second texture is lost too); the
  two textures trade slots only when both fit so.

Hero, fix 32 -> fix 33: follow mismatches 63 -> 0; UV animation a template lacked 97 -> 1; meshes
with UVs baked 62 -> 0; flipbooks frozen on one cell 147 -> 0; second textures drawn live 81 ->
122; samplers folded in as their mean 45 -> 22; dissolves 10 -> 14 of 14; spins lost 33 -> 6. Worse:
directional parts turned by their world motion (no `v_inVec`) 11 -> 17. Every mesh now has a vanilla
vertex program that draws what it needs, so no program of our own was written; what's left
(directional parts without `v_inVec`, 6 spins) is quads and directional types (step 3).

## Fix 34 (`build/hero_fix34.zip`): Frizz / Zap's see-through lens

Fix 33 showed a see-through, bending "lens" at Hero's hand while Frizz and Zap charged, lingering
after the shot. Their charge flare (`flare1`) had a refraction part's template (Bayonetta's
`ciecle1_rif`, Shulk's `rifraction2`): once a template's pixel program is ours its blend no longer
mattered (fix 33), and those two, drawn with another blend, became candidates. Their shader mode (byte 0x831,
the shader key's first word: `docs/ptcl-format.md` 0x830) is 5: the game draws them in the
distortion pass, whose output is a screen offset, so the flare's colour bent the picture instead of
showing. Fix 33 had 10 such parts: the charge flares of Frizz, Frizzle, Zap and Woosh, Zap's
release flare, Kafrizz's ball (`sphere1`, mode 6), Bounce's barrier, Snooze's flare and the
no-MP flare; fix 32 had 30 (the sword light, explosions, impacts), short or small enough to miss. Shaders of modes 5, 6 (distortion) and 7 (Fox / Falco's Illusion) are never
templates now (`PASS_MODES`); every Hero part uses a mode 0, 4 or 8 shader. Nothing else changes
from fix 33.

Ruled out on the way (round 1-6 tests): Robin's own refraction sets, the second textures, the
dissolve, the chant, the bank's size, follow types, and `light1`.

## Fix 35 (`build/hero_fix35.zip`): effect lights

Ultimate's "custom action 1" data (CADP), left out until now, is an effect light: the glow of a
spell lights up the fighters near it. Smash 4 has the same light, eft's user callback 1 and its user
data (`docs/ptcl-format.md` 0x00C), with the same flags and a radius that is likewise a multiple of
the particle's scale: the common effects both games share (FliesUp, SpecialSpeedUp, AssistOut)
match. 54 of Hero's parts now light their surroundings as in Ultimate (the Frizz / Zap / Woosh charge
flares, radius 20 x 0.5; Kaboom 800 x 0.1; Kamikazee, the explosions, the sword spells' glows...),
and 6 parts no longer carry a light their template had (Ultimate gives them none). Not converted:
CADP's last value (0.2 - 1.0; maybe the light's strength: Smash 4's light has no such slot) and the
flag bits 0x20 - 0x80 Smash 4 doesn't use.

## Fix 36 (`build/hero_fix36.zip`): step 3, spins and directional parts

- **Spins:** a mesh's spin ranked after everything else (from when its UV animation had to come
  first, which the UV term now covers): Kafrizz's burst rings (`ring1`, `ring2`) and Kaboom's
  warning `wind1` stood still for a template that animates colour 1. A spin now ranks before the colour tracks (a constant colour
  track is drawn as its mean; a lost spin is the whole motion); they turn again, colour 1 at its
  mean. Still unturned: `impact2` x 2 (no spinning stripe-mesh template plays a flipbook) and one
  quad, `splash1`.
- **Directional parts:** every vanilla vertex program that reads `v_inVec` moves its particles on
  the GPU (141 of 141: air resistance and gravity worked out from the velocity); the CPU's
  directional programs turn a particle by its world motion (`v_inWldPosDf`). That is its velocity
  unless the emitter follows (the bone's motion adds in), so the 5 unfollowing parts were never
  off. The 12 following ones (Zap's / Kazap's bolts, lines, flashes) keep their templates: a GPU
  one would cost them their second texture's motion or their colour animation, seen all the
  time, for a tilt seen only while Hero's hand moves.
- **Second textures not drawn live (20):** no vanilla two-texture program draws what these need:
  a flipbook (8: no two-texture mesh program plays one), the main texture's UV animation (9), or
  that quad type at all (3).

What's left (following directional parts, the 20 second textures, 3 spins) needs vertex programs
of our own: template choice has gone as far as the vanilla programs go.

## Fix 37 (`build/hero_fix37.zip`): vertex programs grafted

The first vertex program code of our own (`tools/eft_vertex.py` graft_uv1, `docs/ptcl-format.md`
"Grafts"): a one-texture template's program gets slot 1's UV animation (eft's own transform, fitted
against vanilla code run through an interpreter, `tools/eft_vertex_test.py`), its pixel header a
`textureSampler1`, its key a texture count of 1, and so draws a second texture. Every vanilla
one-texture template we can stand in for (739 programs, all checked: clauses unchanged, jumps
moved, the export re-pointed, relocation tables whole) can now be a two-texture one, a vanilla
two-texture template still taken over a grafted one drawing as much. The GPU templates that turn
particles by their velocity were all one-texture: grafted, they serve the directional parts too.

Hero, fix 36 -> fix 37: second textures not drawn live 20 -> 0 (drawn live 122 -> 142); UV
animation a template lacked 16 -> 3; samplers folded in as their mean 22 -> 11; directional parts
turned by world motion instead of velocity 12 -> 0. 84 parts use a grafted program. Left: 11 third
samplers (their mean: a slot-2 graft), 2 spins (`impact2`), `Light`'s quad UV animation.

## Fix 38 (`build/hero_fix38.zip`): no lit smoke templates; spell lights within 1

- **Dark flames:** Kafrizz's trail stayed black-red through tests A - F (its second texture off,
  its colour averaged) and orange only on fix 36's template: the grafted template was Mario's
  fireball smoke, whose vertex program lights its particles (colour x max(normal . light, 0) x the
  light colour + ambient, from the game's `userUniformBlockParam`, CB4). 245 vanilla emitters (all
  shader mode 4) have such programs; fixes 33 - 37 used them for 71 - 102 of Hero's parts (Frizz's
  and Frizzle's flames, the fire hits, the sword spells, the lightning flashes). They are never
  templates now (`LIT_BLOCK`), at no cost: every count of fix 37 holds.
- **Lights:** a light left to the particle's colour took its colour scale (2 on most of Ultimate's
  flares; vanilla lights stay within 1, 99% of 599): Kaboom's stacked lights were blinding. Each light
  now has its own colour, the particle's mean within 1, x CADP's last value (the light's strength).
- Kafrizz's core sphere keeps its grafted (GPU) template: test A's fireball, the best of A - D.

## Fix 39 (`build/hero_fix39.zip`): light reach capped

Kaboom stayed far too bright in fix 38. Vanilla lights with flag 0x10 (radius x the particle's
scale) reach at most 108 (median 20, 330 non-Final lights); Kaboom's `flareBase` reached 60 x 4.3 =
260 for 55 frames. Those lights are capped at 70 (Mii Gunner's Stealth Bomb): Kaboom 260 -> 70,
Magic Burst 220, Kamikazee 113, Bang 87, Kafrizz's burst 82 -> 70.

## Fix 40 (`build/hero_fix40.zip`): third textures drawn live

The slot-2 graft (`docs/ptcl-format.md` "Grafts"): a one-texture template's vertex program gets slots
1 and 2's UV animation, slot 2's in a parameter of its own (a new export, the vertex header's
counts and semantics, a pixel input for it), and `textureSampler1 / 2`; our pixel programs take a
third texture in eft2's order ((t0 . t1) . t2). Checked like slot 1's on all 739 graftable vanilla
programs (clauses, jumps, both exports, the header registers) and its clause against eft's formula.
eft2's texture blend 2 is subtract (Ultimate's own `light1` program: alpha = t0 x t1 - t2); the
converter folded it as multiply before.

Hero, fix 39 -> fix 40: samplers folded in as their mean 11 -> 3 (13 parts draw three textures:
the sword light, Kafrizz's / Frizzle's rings and flare lines, the chant's `light1` / `light2`,
Zap's discharge line, Magic Burst's impact, Bounce's parts). Left: Kaboom's / Kafrizz's wind rings
(`wind1`, `wind2`: their main texture is sampler 1, so eft2's order puts the folded one first).


## Fix 41 (`build/hero_fix41.zip`): spins grafted

The rotation graft (`docs/ptcl-format.md` "Grafts"): a mesh template without `v_inRot` gets the
attribute (a header entry at a new location, an input GPR) and a clause turning its position in
place, pos' = S⁻¹ R S (pos + rotBasis) - rotBasis, so its own S (pos' + rotBasis) is eft's
R S (pos + rotBasis) (R = Rx·Rz·Ry, fitted on Little Mac's Final program). A program takes it when
its clauses before the position export, run through the interpreter (`tools/latte_interp.py`),
work the position out so; 49 of 126 vanilla mesh programs without `v_inRot` do, each grafted one
checked end to end. The converter grafts the template it picked when a mesh's spin or random turn
would otherwise be lost.

Hero, fix 40 -> fix 41: Zap's / Zapple's `impact2` stripes (random 0 - 360 degrees about Z in
Ultimate, all one way on Pikachu's template before) turn. No spin is lost now.

## Fix 42 (`build/hero_fix42.zip`): the orbs

The flat discs on Frizz, Zap, Kazap, Zoom, Kacrackle / Flame Slash, Snooze and the rest were
Hero's glow parts on Ultimate's 16-sided flare disc (73 parts): in Ultimate a soft glow, its vertex
alpha fading the rim to nothing. Found by elimination in game (tests: lights off, glow alpha
cut, parts tinted, the disc's texture swapped for a checkerboard / a core / a solid fill): the
texture mapped right but the vertex alpha never did. Every vanilla mesh stores its data position,
normal, UV, colour; `Ptcl.add_primitive` stored colour before UV, and eft read our UVs as the
vertex colour. The primitive data now goes in vanilla's order (the same 147 meshes, byte for byte,
read by offset), which fixes the vertex colour of every converted mesh, not only the discs.
