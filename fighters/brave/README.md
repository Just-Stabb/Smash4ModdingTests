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
  tome empty. 110-120 bones (Robin's count).
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

Not yet: the side tilt's second hit (`AttackS3S2`, a second press), the critical hits, his sword
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
  SpecialNHold while special is held; Frizzle from 18 frames held, Kafrizz from 81. Released (a tap
  too) -> SpecialN1 / N2 / N3, the fireball out at frame 10 / 11 / 16; shield while holding ->
  SpecialNCancel, the charge kept for the next one (lost if he's hit while charging, or loses a
  stock). Actionable from Ultimate's cancel frames (44 / 52 / 68, cancel 6) through Robin's
  `func_2246`; the air motions are swapped in by Robin's `func_2245`. Air: the fall slowed while
  charging and through Frizz (x0.8). Motions: Robin's 0x21F start, 0x223 hold, 0x227 N1, the shoot's
  custom-move variants 0x228 / 0x229 N2 / N3, Thoron's start 0x22F cancel (air + 0x1C; extra_kinds.json
  "motions", `specials_acmd.json`).
- Fireball (weapon kind 0x190, a copy of Robin's thunder, article 7; `weapons/fireball.c`): the level
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
  hits, Zap's lightning lands on that fighter: the spark article (weapon kind 0x191, article 8) at its
  player slot, once a fighter per cast. The slot is found from the last fighter hit's offset and the slot
  positions (docs/position-variables.md); the spark waits 3 frames (activate_wait_frame) and hits for 8.
  Motions: start 0x258 / 0x25C, hold 0x259 / 0x25D, Zap 0x257 / 0x25B, Zapple 0x25A / 0x25E, Kazap
  0x230 + 0x231 / 0x24C + 0x24D (Thoron's slots).
- Up special (status 0x154, Robin's Elwind; `brave_hi_*`): SpecialHiStart, SpecialHiHold (Swoosh from 10,
  Kaswoosh at 28, by itself), then SpecialHi1 / 2 / 3: the tornado article (0x192, article 9) at his own
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
