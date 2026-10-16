# Bowser (koopa)

Decompiled from the user's upload: `koopa.c` (`script/msc/koopa.mscsb`) and `breath.c`
(`script/msc/breath/breath.mscsb`, the Fire Breath weapon).

## Neutral B customs (for Kirby's copy ability)

- Body ACMD (`game.bin`) has no SpecialN scripts: the hitboxes are on the `breath` weapon.
  Body motions: SpecialNStart `0x211`, SpecialN `0x215`, SpecialNEnd `0x219`, air `0x21D` /
  `0x221` / `0x225`; each has 4 slots (default + customs) that only matter for effect.bin
  (game.bin has none of them).
- `breath` weapon: `func_40` = motion + weapon custom ID (`0x10000005`). Its `motion.mtable`:
  index 0 `0xEF3E3778` (1.2 / 1.2 damage, default Fire Breath), 1 `0x15225DE3` (6 / 5
  damage, BKB 70/50, ends at frame 20), 2 `0x62256D75` (2.7 / 1.8 damage), 3 `0xFC41F8D6`
  (no script).
- The body MSC barely branches on the custom ID (`0x10000048` only picks a sound in the
  SpecialN exec, `func_2345`). The differences come from the custom's params (the
  `0x15xxxxxx` / `0x5xxxxxx` param groups are selected by the custom slot) and the weapon
  script above.
- Kirby's Bowser copy (`kirby.c`, statuses `0x1F6`, exec at "se id:") is the same code and
  reads Kirby's own `0x10000048` the same way.
