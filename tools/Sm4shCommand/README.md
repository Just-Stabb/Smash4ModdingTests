# Sm4shCommand (updated)

Sm4shCommand and the SALT library it builds on, copied from Sammi Husky's repositories and fixed here:

- `SM4SHCommand/` from https://github.com/Sammi-Husky/Sm4sh-Tools (commit `0173bd3`)
- `SALT/` from https://github.com/Sammi-Husky/SALT (commit `9ffff37`; Sm4sh-Tools pins an older
  submodule commit, `4753c93`)

Both are by Sammi Husky; see `SM4SHCommand/LICENSE.txt`, `SM4SHCommand/COPYING.txt` and
`SALT/LICENSE`. Sm4shCommand uses FastColoredTextBox (LGPLv3), included as `FastColoredTextBox.dll`.

**Run:** needs .NET Framework 4 (built into Windows 10/11). Windows may warn that the exe is from an
unknown publisher ("More info" > "Run anyway"); if the zip was downloaded, right-click it > Properties >
Unblock before extracting. A file or fighter folder can be dragged onto the exe (or given on the command
line) to open it. If anything goes wrong, the error and its details are written to
`Sm4shCommand_errors.log` next to the exe.

**Build:** open `Sm4shCommand.sln` in Visual Studio (Windows, .NET Framework 4.0 or later) and build.
`Events.cfg`, `AnimNames.txt` and the `Tooltips` and `Aliases` folders are copied next to the exe (regenerate the tooltips with `python3 make_tooltips.py`). (The FastColoredTextBox reference used to
point at the original author's desktop; it now uses the bundled DLL.)

## What changed

| Problem | Fix |
|---|---|
| Variables showed as `LA-Int[1]` | Shown as their raw value, `0x2100000D` (like FITX and the game's code). Both forms, and FITX's `var 0x...`, compile. View > "Show variables as LA-Int[1] style" brings the old form back. |
| Hidden scripts weren't listed | In fighter (folder) and project mode, scripts that aren't in `motion.mtable` (subroutines reached through JUMP/CALL, unused scripts) are listed after the motion table entries as `[unlisted] name`, in grey. |
| Save did nothing while scripts were open | Open tabs are compiled before saving (they used to be compiled only when their tab closed). The toolbar Save/Open buttons had no click handlers. In fighter mode, files were written to the working directory instead of where they were opened from. |
| Hitbox fields were missing / wrong | The bundled `Events.cfg`, loaded on top of SALT's definitions at startup, was older than SALT and replaced its hitbox definitions (Special_Hitbox's fields as `Unknown`, X/Z swapped, Rebound/SFXLevel missing). It's now generated from SALT's table (`make_events_cfg.py`). |
| Scripts named by hash | `AnimNames.txt` (next to the exe) lists standard animation names (about half of a fighter's `game.bin` scripts on Kirby, Captain Falcon and Bowser). Tools > Parse Animations now saves the names it finds there, and right-click > **Set Name** names a script (or labels a hash whose real name isn't known), so names only need finding once. Names show in file, fighter and project mode. |
| Parsing animations by hand every time | Tools > **Auto-Parse Animations on Open** (on by default, remembered in `Sm4shCommand.ini` next to the exe): opening a file, fighter folder or project parses that fighter's `motion` folder automatically, found next to the opened folder or one of its parents (`fighter/NAME/motion` for `fighter/NAME/script/animcmd/body`). Each folder is parsed once per session; turning the setting on re-parses the current one. The names are saved to `AnimNames.txt` as with Parse Animations. The "LA-Int[1] style" view option is remembered too. |
| JUMP/CALL targets couldn't be opened | The hash in `JUMP(Hash=0x...)` / `CALL(Hash=0x...)` is underlined; **Ctrl+click** it to open that script. Hovering it shows the script's name. |
| Couldn't add scripts | Right-click > **Add Script..**: an animation name or `0xHASH`. In a fighter folder it's added to game/effect/sound/expression, and you choose whether it also goes into `motion.mtable` (a new motion) or stays unlisted (a JUMP/CALL target). |
| No animation IDs | View > **Show Animation IDs** (on by default, remembered in `Sm4shCommand.ini`) lists each script with its animation (motion) ID: its index in `motion.mtable`, the number the game's code uses for the motion (`MotionModule` / `func_22(0x5f, ...)` in MSC), e.g. `0x5F - AttackS4`. The script's tooltip and its tab show it too, and the filter box matches it (`0x5F`). Fighter and project mode, and single-file mode when `motion.mtable` is next to the opened .bin (scripts are then listed in ID order, then the unlisted ones). Tools > **Go to Animation ID..** (Ctrl+Shift+G; Ctrl+G is the editor's Go to line) opens a script by its ID (hex, `0x383` or `383`). |
| Numbers only in hex | View > **Show Numbers as Decimal** (remembered in `Sm4shCommand.ini`): int parameters show as decimal (`Angle=361`, `KBG=100`). Int parameters that hold float bits show as floats (`unknown=0.6f`; View > **Show Float Values in Int Parameters as Floats**). Hashes, effect / sound IDs and bit fields stay hex: values above 0xFFFF, and parameters listed in View > **Parameters Always in Hex..** (default: Hash, Graphic, GFXLeft, GFXRight, SFX, HitBits, Flag, Variable1–3). Every form compiles in any int parameter (`0x169`, `361`, `1.5f`), with or without the setting. Checked on 3,443 scripts (Kirby's game/effect/sound/expression and weapons, Captain Falcon): the same bytes back as with hex. |
| Comments were lost on save | `// ...` (on its own line or after a command) and `/* ... */` comments are kept. The game's .bin has no room for them, so saving writes each commented script's text to `FILE.comments` next to the file (e.g. `game.bin.comments`; deleted again when no script has comments); the game never reads it. Opening a script shows that text again. If the .bin was changed by another tool since, the comments go back onto the lines that still match (compared by what they compile to, so `0x169` and `361` match). File and fighter mode (not project mode). A comment after a command used to be a compile error; comments inside `if` blocks are fine too. |
| Value tooltips | Hovering a number in a parameter explains it, from the text files in the `Tooltips` folder next to the exe. They're generated from the MSC Note Sheet, the fighter_param sheets and the article list, with `make_tooltips.py`. They cover variables (work variables, fighter_param stats, STrans / STransGroup IDs, the position variables `0x0F0000xx`), common effect IDs in `Graphic=`, the 361 angle, and each fighter's article IDs and special-move params (`0x05`–`0x09xxxxxx`, with default values). Per-fighter entries are used when the open path is `.../fighter/NAME/...`. **Right-click a number > Edit Tooltip..** adds or changes one in `Tooltips/custom.txt`. Tools > **Reload Tooltips** / **Open Tooltips Folder**. The file format (filters by fighter, command, parameter name, type or position) is described at the top of `SM4SHCommand/Classes/Tooltips.cs`. |
| Variable aliases | Names for variables, e.g. `SET_FLOAT(Value=1.5, Variable=LASTHIT_HITSTUN_MUL)` instead of `0x0F000052`. Loaded from the text files in the `Aliases` folder next to the exe (`NAME = 0x0F000052`, any variable form works; `custom.txt` for your own, it wins). `Aliases/variables.txt` (from `make_tooltips.py`) names the common variables of `tools/position_vars_cave.py`: `POS_SELF_X` … `POS_OPP_OFFSET_X` … `POS_SLOT1_X` …, the combat ones as `TARGET_QUANTITY` (`SELF`, `OPP`, `LASTHIT`, `SLOT1`–`SLOT8` × `HITSTUN`, `HITSTUN_DEALT`, `HITSTUN_MUL`, `HITSTOP_SHAKE`, `HITSTOP`, `OFFSET_X/Y/Z`) and `SELF_ANIM_RATE`. View > **Show Variable Aliases** (on by default) shows them by name; names always compile, case doesn't matter, and tooltips work on them. Tools > **Reload Variable Aliases** / **Open Aliases Folder**. |
| Command definitions / descriptions | Tools > **Command Definitions..** edits names, parameter names and types, and descriptions, and adds new commands; Save writes `Events.cfg`. Hovering a command in the editor shows its description and parameters; hovering a parameter shows its name, type and description. |

Also:

- **Compile errors instead of crashes or silent damage.** A line that doesn't compile (unknown
  command, wrong number of parameters, a value that isn't a number, an unclosed `{`) stops the save,
  shows the tab and selects the line with the reason. Before, a missing parameter was silently left
  out or the app threw. Closing a tab with an error asks before discarding the changes.
- **Script_End** is added back if it's deleted (the game reads past the end of a script without it).
- **Numbers** are written in a culture-independent, exact form (floats round-trip bit for bit; a
  Windows decimal-comma locale no longer breaks parameter lists).
- **Name lookup:** `Else` and `ELSE` are different commands; exact-case names win.
- **Intensity_Special_Hitbox** listed 46 parameters for a 48-word command, so saving zeroed its last
  word; it now has 47.
- The tree filter box no longer throws when narrowing the list.
- Empty motion.mtable slots show as `(empty)` (with their animation ID).
- The toolbar/window images are embedded as plain PNG/ICO files (`SM4SHCommand/Resources/`) and loaded
  by `Images.cs`, instead of being serialized into the forms' .resx; a startup failure is logged and shown
  instead of the program silently not opening.
- The folder picker falls back to the standard folder dialog if the Vista-style one can't be created.

## Events.cfg format

One block per command, blocks separated by a blank line; lines starting with `//` are comments:

```
B738EABD                     identifier (hex CRC32 of the command)
Hitbox                       name
0,0,0,1,...                  parameter types: 0 int, 1 float, 2 decimal, 3 variable (or NONE)
ID,Part,Bone,Damage,...      parameter names (or NONE)
Defines a hitbox ...         description, shown in tooltips (optional; NONE = none)
Param: KBG = Knockback growth   optional, one per parameter, shown when hovering that parameter
```

A block with a problem is skipped and reported in the log at startup.

## Checked

- Run under Wine (wine-mono): opens a fighter folder, names and unlisted scripts in the tree, filter,
  editor with tooltips, Ctrl+click on CALL, edit + Ctrl+S saving in place (only the edited script
  changes), the compile-error dialog, Command Definitions (edit + save), Add Script (all four files +
  motion.mtable). Not run on Windows itself.
- SALT: every script of Kirby's game/sound/expression.bin and Captain Falcon's game.bin
  (2,000+ scripts) prints to text and compiles back to identical bytes. In effect.bin, 470 of 475 do; the
  other 5 are else-if chains that SALT writes as nested Else blocks (same behaviour, different offsets;
  unchanged from upstream).
- Events.cfg written by Tools > Command Definitions reads back with no errors.

`make_events_cfg.py` regenerates `Events.cfg` from SALT's table; `make_anim_names.py` regenerates
`AnimNames.txt` (this drops names added by Parse Animations / Set Name).
