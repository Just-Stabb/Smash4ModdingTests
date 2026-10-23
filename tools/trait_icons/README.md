# Kirby trait icons

Icon art for the trait badges in Kirby's damage panel (`tools/trait_badge_art.py`). One PNG per
trait, named after it:

| File | Trait |
|---|---|
| `barrage.png` | Barrage (the orange four-point star) |
| `strike.png` | Strike (the red burst): to add |
| `juggernaut.png` | Juggernaut (the yellow shield): to add |
| `normal.png`, `rush.png`, `shooter.png`, `technical.png` | the other traits (optional) |

Each file is used as it is: scaled to fit the icon's spot on the left of the badge, with its aspect
ratio kept. Any size works; square, with a transparent background, looks best. A trait without a
file keeps the drawn icon.
