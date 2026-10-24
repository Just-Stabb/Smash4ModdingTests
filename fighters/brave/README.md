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
