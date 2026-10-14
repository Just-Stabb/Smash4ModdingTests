# Charizard (`lizardon`) MSC

- `lizardon.c`: Charizard's decompiled fighter MSC (as provided).
- `breath.mscsb`: the Flamethrower flame article's compiled MSC (as provided); `breath.c` is it decompiled with `tools/mscdec`.

## How Flamethrower aims (used as the model for Kirby's aimable inhale)

- **`func_2262` (SpecialN loop, while the flame is out, `0x11000004 == 1`):**
  - If |stick Y| > 0.5: `angle += 0x5000003 * stickY`, clamped to
    `[-0x5000002, 0x5000001]` with `func_15`, stored in status float
    `0x1000006`.
  - It also derives three angles (`0x1000007`–`0x1000009`) from
    `angle * 0x5000004`. Nothing in this MSC applies them to bones, so
    Charizard's neck rotation is done by the game's native code.
- **`breath.c` (the flame article) doesn't aim itself.** It counts down its
  hitbox time (`0x2000002`) and lifetime (`0x2000001`), and grows its scale
  (`PostureModule(0x2713, scale)`). It follows the mouth bone it's attached
  to.
- **Kirby's Bowser copy (Fire Breath, `kirby.c` `func_2874`/`func_2875`)**
  uses the same angle logic, then rotates Kirby's bone `0x13` itself:
  `ModelModule(0x1, 0x13, 0, 0, -angle * scale - 45)`. That's the pattern the
  aimable inhale copies.
