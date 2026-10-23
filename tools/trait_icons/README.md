# Kirby trait icons

Icon art for the trait badges in Kirby's damage panel (`tools/trait_badge_art.py`). One PNG per
trait, named after it:

| File | Trait |
|---|---|
| `rush.png` | Rush: blue, recoloured from `source/rush.png` |
| `shooter.png` | Shooter: purple and black crosshair, recoloured from `source/shooter.png` |
| `strike.png` | Strike: the red burst |
| `juggernaut.png` | Juggernaut: the yellow shield |
| `technical.png` | Technical: black, recoloured from `source/technical.png` |
| `barrage.png` | Barrage: the orange four-point star |
| `normal.png` | Normal: not yet, so it keeps the drawn star |

The recoloured ones are made by `recolor.py` from the originals in `source/`, with a white outline
like Strike's and Juggernaut's; run it again after changing a source or a colour.

The badges in use set the names in TT Travels ExtraBold (white), a trial font (TypeType's trial license:
testing and evaluation only, not to be passed on), so it isn't in the repository:
`python3 tools/trait_badge_art.py OUT_DIR --font "TT Travels Trial ExtraBold.otf"`.

Each file is used as it is: scaled to fit the icon's spot on the left of the badge, with its aspect
ratio kept. Any size works; square, with a transparent background, looks best. A trait without a
file keeps the drawn icon.
