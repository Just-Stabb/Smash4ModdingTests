# Hold L at launch: straight to Training

`tools/boot_training_cave.py` (rpx_patch args, after the standard build's); test
`tools/boot_training_test.py PATCHED.rpx` (unicorn: 8 cases, 0 failed).

## How the game's modes start (cross_f.rpx)

- Scenes are registered by name with a factory: table `0x100CBD90` (`{factory, name}` pairs:
  `SystemBootSequenceScene`, `BootSequenceScene`, the `BootView*` save / SD / DLC checks,
  `TitleSequenceScene`, `TitleView{Title,Opening,Tutorial,NewsCheck,Info}Scene`, `MenuSequenceScene`,
  the `MenuView*` screens...). A scene is changed by name: a name object (`0x02020A28` / `0x033FD92C`)
  handed to the scene manager (`0x033B9F18`, also `0x033BA034` / `0x033BA394`).
- The root sequence controller: its set-up method `0x02C841E4` (vtable entry `0x1010E10C`) runs once
  after the boot scenes; it maps each mode's sequence scene to a menu state (`0x1010D938`...:
  `SingleTrainingSeqCtrlScene` -> 0x13, ...), builds its state tables at `+0xB4`, and starts
  `TitleSequenceScene` (`0x02C87650`-`0x02C87668`, through `0x033FD77C` with the name's id from
  `0x020FF398`).
- Its launcher `0x02C881D4` starts the mode the menu picked (state `+0x8C`, switch on state - 0x23,
  table of branches at `0x02C882DC`): state 0x5F is Training (`0x02C88F48`: menu mode 0xB through
  `0x02C840CC`, then `SingleTrainingSeqCtrlScene`), 0x60 Classic (`SingleSimpleSeqCtrlScene`, mode 4)...
- The title's end (`0x0224B42C`) changes to `MenuSequenceScene`.

## The patch

The two loads of the title's name in the set-up become `bl` into the cave (`0x04B84A00`; first `0x04B85000`, see below): with L held
on any controller (the pad slot array `0x1057581C`, as biome_select_cave.py reads it) it sets the menu
mode to 0xB and starts `SingleTrainingSeqCtrlScene` instead, as the menu's Training entry does.

Not known yet (in game): whether the controller's set-up runs only after the save data has loaded
(the boot scenes come first by name), and the way back from Training to the menu without the title
having run. Fallback if it misbehaves: hook the title's end (`0x0224B42C`) instead, so pressing
start on the title with L held goes to Training.

## In game: crash at boot (Sephiroth v3 executable, Cemu 2.6)

The first in-game run crashed at boot: Cemu asserted on an HLE call at `0x04B85170` (LR `0x02C87648`,
just before the first hook), i.e. execution reached stale words left from kind_expand.py's old space
(`0x04B850A8`-`0x04B877C4`: its old tables, words like `0x04B85000` that decode as Cemu HLE opcodes).
Nothing in the executable points there (no branch, pointer or lis/addi pair), the cave's own code is
as assembled and its unicorn test passes, so the path is not known yet. Sent: the same executable
without the shortcut (`build/sephiroth_v3_noboot.zip`; adding the shortcut back gives v3 byte for
byte) to confirm the shortcut is the trigger. Next: move the cave to clean space away from the old
kind_expand words (and clear those), keep the picked name in a data word instead of in the code.

The no-shortcut executable booted (user). Fixed version (`build/fighters_fix_test19.zip`): the cave
moved to `0x04B84A00`-`0x04B85000` (zeros after stage_omega_cave.py's), and the old kind_expand space
`0x04B85000`-`0x04B877C4` cleared to zeros. Not yet run in game.
