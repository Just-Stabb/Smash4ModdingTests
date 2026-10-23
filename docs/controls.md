# Controls: Smash Attack button and Stick Smash

Two additions to the Controls menu (Options > Controls > a name):

- **Smash Attack on any button.** Every button's popup now also lists *Smash Attack* (it was only
  on the C-stick / right stick). A button set to it works like the C-stick's smash attack, with
  the control stick as the direction:
  - on the ground: no direction = forward smash, sideways = side smash (that way), up / down =
    up / down smash;
  - in the air: the aerial for the stick's direction (no direction = neutral air), as the C-stick;
  - holding the button charges the smash attack (attack stays held while the button is).
  The 3DS, GameCube, Pro / GamePad / Classic and Wii Remote + Nunchuk layouts all get it (the
  Nunchuk layout's d-pad keys excepted: their popups are already the biggest the menu has). The
  sideways Wii Remote's buttons list it too, but there it is the game's own smash input (as its
  1+2 default): the air behaviour above isn't added for that layout.
- **Stick Smash: ON / OFF** (a new row under *Smash Attack*, for the 3DS, GameCube and Pro /
  GamePad / Classic layouts). OFF: attack with a flicked control stick no longer makes a smash
  attack (side, up or down, including the dash forward smash) - it makes the tilt (or the aerial
  in the air) instead. Smash attacks then come from the Smash Attack button, the C-stick, or A+B
  (*Smash Attack* row). Default ON (the game as it was). The Wii Remote layouts keep their Shake to
  Smash row in that place and don't have the option.

Both are saved with the name's controls, like Tap Jump.

## How Stick Smash OFF works

On the frame attack is pressed (not held from before) without a smash input, the control stick
for that frame is limited to 0.79 sideways / 0.63 up-down (the game's smash thresholds are 0.83 /
0.66, the tilt ones 0.25), so the press can only be a tilt or an aerial. Only that one frame is
limited, and the stick stays past 0.25, so walking, dashing, jumping and fast falls aren't
affected. The setting is applied to the inputs themselves (where the game applies Tap Jump and
A+B), so replays play back as played.

## Files

| file | made by |
|---|---|
| `code/cross_f.rpx` | `tools/smash_button_cave.py` (with the rest of the build: `rpx_patch.py`) |
| `ui/script/app/option/option_view_button.xtal` | `tools/option_button_ui.py` (the Controls screen's script) |
| `ui/lumen/option_button/option_button.lm` | `tools/option_button_ui.py` (the new row) |
| `ui/message/menu.msbt` | `tools/option_button_ui.py` (`MmenOption_button_85` = "Stick Smash") |

```
python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/smash_button_cave.py)
python3 tools/option_button_ui.py UI_DIR MENU_MSBT OUT_DIR
python3 tools/smash_button_test.py OUT.rpx ORIGINAL.rpx      # the RPX side, in unicorn
python3 tools/option_button_ui_test.py UI_DIR MENU_MSBT     # the menu files
```

The menu.msbt in the package is the one from the earlier packages (Minecraft World / Supamario)
with the one label added; if yours has other changes, run `option_button_ui.py` on it (or add
`MmenOption_button_85` with `tools/msbt.py`).

Notes: `docs/native-notes.md` "Controls settings and input frames". The Controls script is Xtal
bytecode; `tools/xtal.py` reads, disassembles and rewrites these (`dis` / `check`), with jump
relocation for inserted code.
