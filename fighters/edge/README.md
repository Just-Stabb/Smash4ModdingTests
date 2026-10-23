# Sephiroth (`edge`)

A port of Ultimate's Sephiroth (the user's files: `edge.zip` in their Drive: `model/body/c00-c07`,
`motion/body` 367 nuanmb, `param/vl.prc`, AI params). New fighter kind `0x42`, character id 60,
UI name `Sephiroth`, base Zelda (`tools/extra_kinds.json`; docs/kind-expansion.md). Trait:
**Technical** (docs/character-traits.md, `kirby_copy_trait()`). Roll-off: the default 2.2 / 1.0.

## v1 (`build/sephiroth_v1_test.zip`): the slot

A copy of Zelda in the new slot, with Zelda's universal-mechanics scripts (roll-off, reverse tilts,
tilts / down smash / shield out of run). Its executable is Supamario test 18's plus kind 0x42.

## v2 (`build/sephiroth_v2_test.zip`): his model and animations

`tools/ultimate_fighter.py` (docs/ultimate-fighter-port.md): Ultimate's model for all 8 colours on
his own skeleton (172 bones; the second outfit c06 / c07 124), all 299 battle motions plus entry /
result / route-map ones, the swords' visibility per motion. Zelda's moves still. Built with:

```
python3 tools/ultimate_fighter.py model edge/model/body/c0N zelda/model/body/c0N OUT/c0N --empty EMPTY
python3 tools/ultimate_fighter.py motions edge/motion/body/c00 edge/model/body/c06 zelda OUT
```
(each `c0N` also copied to `l0N`, the low-detail slot).

## Next

1. Moves: ACMD / MSC from Ultimate's frame data (Ultimate's hitboxes are compiled code, not in the
   files), his own specials and articles.
4. Effects, sounds, portraits from the Ultimate zips.
