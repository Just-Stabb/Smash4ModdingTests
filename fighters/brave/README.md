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
