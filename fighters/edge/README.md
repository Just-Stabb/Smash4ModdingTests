# Sephiroth (`edge`)

A port of Ultimate's Sephiroth (the user's files: `edge.zip` in their Drive: `model/body/c00-c07`,
`motion/body` 367 nuanmb, `param/vl.prc`, AI params). New fighter kind `0x42`, character id 60,
UI name `Sephiroth`, base Zelda (`tools/extra_kinds.json`; docs/kind-expansion.md). Trait:
**Technical** (docs/character-traits.md, `kirby_copy_trait()`). Roll-off: the default 2.2 / 1.0.

## v1 (`build/sephiroth_v1_test.zip`): the slot

A copy of Zelda in the new slot, with Zelda's universal-mechanics scripts (roll-off, reverse tilts,
tilts / down smash / shield out of run). Its executable is Supamario test 18's plus kind 0x42.

## Next

1. Model: Ultimate's body (and Masamune) to NUD on Zelda's skeleton names where they match, all
   eight colours (tools/ssbh_to_nud.py).
2. Animations: nuanmb -> omo, mapped onto Zelda's motion list (Sephiroth has no counterpart for
   some of Zelda's motions, and vice versa).
3. Moves: ACMD / MSC from Ultimate's frame data (Ultimate's hitboxes are compiled code, not in the
   files), his own specials and articles.
4. Effects, sounds, portraits from the Ultimate zips.
