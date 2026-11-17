# Sm4shCommand (updated)

Sm4shCommand and the SALT library it builds on, copied from Sammi Husky's repositories and fixed here:

- `SM4SHCommand/` from https://github.com/Sammi-Husky/Sm4sh-Tools (commit `0173bd3`)
- `SALT/` from https://github.com/Sammi-Husky/SALT (commit `9ffff37`; Sm4sh-Tools pins an older
  submodule commit, `4753c93`)

Both are by Sammi Husky; see `SM4SHCommand/LICENSE.txt`, `SM4SHCommand/COPYING.txt` and
`SALT/LICENSE`. Sm4shCommand uses FastColoredTextBox (LGPLv3), included as `FastColoredTextBox.dll`.

**Version:** v1.7.6 (title bar and Help > About). v1.7.6: **Effect_Camera** (exe_v46z_camfx: `tools/camera_effect_cave.py`): `Effect_Camera(Graphic, X, Y, Z, XRot, YRot, ZRot, Size, Mode, Frames, Flags)` starts an effect (the fighter's bank or the common one) attached to the camera the game draws with, set every frame: offsets in camera space (X right, Y up, Z forward from the eye), facing it, following its moves and zooms; Mode 0 follow, 1 fixed to the screen (X / Y / Size in half screen heights, scaled with the FOV: full-screen overlays), 2 position only; Frames ends it (a fade), Flags 1 unslowed (Time_Scale's slow-motion). In a new subgroup, New Commands / **Effects** (its group help, the command's full help and five examples: a time-stop darkening, a glass-shatter burst, a charge vignette, a common effect pinned to a corner, Mode 2 falling particles); the command list now orders Time & stage and Effects before Variables. The Hitbox Viewer draws it in front of its own view (X / Y from the view's centre, Mode 1 in half the view's height) and ends it with its Frames. `new_var_test.cs`: 241 checks (631 commands, 47 with help, 11 group blocks; Effect_Camera's words, round trip, group; every example compiles and round-trips; the one failure is the effect.bin else-if count, as in v1.7.5's run on the same body); `hitbox_var_test.cs` 206 / 0; `viewer_scripts_test.cs` 39 / 0 (6 new: Effect_Camera's spawns, Frames, the view placement). v1.7.5: **Hitbox_Hold** (exe_v46y_hold: `tools/hitbox_hold_cave.py`): `Hitbox_Hold(ID, Mode)` after a hitbox command makes that hitbox's hits keep the victim in place (no knockback travel; damage, hitstun, hitlag, SDI and the reaction stay): Mode 1 a victim on the ground the hit doesn't lift (the rapid-jab setting the port pipeline now gives Ultimate's setoff-off rapid-jab hits, with Ultimate's own angle 361), Mode 2 every victim (drills), 0 off; ID -1 every hitbox of the object; it goes with the hitbox (a new hitbox in that ID drops it), plain and Extra hitboxes alike. In New Commands / Hitboxes & hits with its help and four examples (a rapid-jab loop hit, a holding drill, the same hit without it for comparison, every hitbox at once). `new_var_test.cs`: 232 checks (630 commands, Hitbox_Hold's words, its group, every example compiles and round-trips; the one failure is the effect.bin else-if count, which is Kirby's 5 and 0 on the ZSS body used here, as in v1.7.4's run); `hitbox_var_test.cs` 201 / 0. v1.7.4: **variable resets** (exe_v46w: `tools/var_reset_cave.py`): `New_Var` takes an optional **`Reset`** (1 KO, 2 landing, 4 ledge grab, 8 hit, or the names joined by `|`: `Reset=landing|ledge`), the events that put the variable back to its Initial; kept in bits 8-11 of the Scope word, shown only when not 0, so every old script compiles and shows as before; **`Var_Reset_Set(Variable, Reset, Value, Owner)`** gives any variable (`VAR_n`, `TIMER_n`, a New_Var name, the input / state variables) a reset on its owner (this object or a target); the variables `VAR_RESET_ID` / `VAR_RESET_VALUE` / `VAR_RESET_OWNER` / `VAR_RESET` (`0x0F0003CA`-`3CD`, MSC's way) have names. New_Var's help says what changed and has four new examples (a combo counter reset on landing, a once-per-airtime flag reset on landing / ledge, a buff cleared on KO, a charge cleared when hit); Var_Reset_Set has its help and five examples (in New Commands / Variables). `new_var_test.cs`: 226 checks, 0 failures (629 commands, every example compiles and round-trips, Line_Test's too; Reset's words, names, errors; Var_Reset_Set's words); `hitbox_var_test.cs` 197 / 0. v1.7.3: **Line_Test** (exe_v46v_line, `tools/line_test_cave.py`): `Line_Test(Space, X0, Y0, X1, Y1, Floors, Distance, HitX, HitY, Kind)` follows a segment against the stage (the game's own GroundModule ray check) and stores how far the first floor / wall / ceiling is, the point and its kind; Space 0 relative to the object along its facing, 1 world; Floors 1 leaves the passable platforms out; the same from the variables `LINE_X0` ... `LINE_NY` (`0x0F0003D0`-`3DA`, named) for MSC. In New Commands / Position & rotation with help and four examples (a beam cut at a wall, a floor check ahead, the variables, a world line); `new_var_test.cs`: 205 checks, every example compiles and round-trips. v1.7.2: **every script of a move runs in the Hitbox Viewer** (game, effect, sound and expression, together and each on its own frame cursor, as the game runs them: hitboxes, body states and effects from any of them), **effect models' parts placed in their bone's space** (a flame pillar drawn under the stage now stands on the fighter), **particles' UV animation** (the common flash's ring, Link's air up special: a ring, not four arcs), and **Add Script File / Remove Script File** (give a motion a script in one more of its four files, the file made if missing); see "Every script, effect models, UV animation, script files (v1.7.2)" below. v1.7.1: the Hitbox Viewer's **common effects checked against the game's own common bank** (vanilla, sent by the user): Dr. Mario's forward-air arc in front of him and orange-yellow (each fighter's colour for the common attack arcs / streaks, fighter_param 0x13C-0x147), Pac-Man's jab streak ahead of his fist and his neutral-air puffs without blocks, Link's air-grab beam (the Genesis beam) without its edge lines and with its head meshes the right way round; see "Common effects against the game's bank (v1.7.1)" below. v1.7.0: **Time_Scale / Target_Time_Scale / Stage_Freeze** (exe_v46n): the whole match slower (the game's own slow-motion, 1/2 ... 1/20) or faster (2-4 game steps a frame), one fighter slower (the Timer item's slow), the stage frozen (the stage manager's own stop), each for some frames or until ended, all ended with the match. In New Commands / Time & stage, with help (what each affects, how they stack with training's speed / the Timer / Final Smashes, offline only) and examples (a hit opponent at half speed for 60 frames, the stage frozen during a hold, a 2x speed-up for 120 frames); new_var_test.cs: 198 checks, every example compiles and round-trips. v1.6.4: **Thread_Start's help** says what exe_v46m changed (threads run in game: before it no thread of any object ever ran) and has an example of a fighter's thread (docs/acmd-extra-commands.md "Thread_Start"); nothing else changed. v1.6.3: the Hitbox Viewer's **Model parts** right-click menu (defaults saved per fighter in VisUser.txt), Pac-Man's visibility groups, part animations (hands, props), billboard sprites, stripes drawn as ribbons, emitter blocks fixed; see "Model parts menu, part animations, stripes, blocks (v1.6.3)" below. v1.6.2: the Hitbox Viewer gets a **Model parts** tab (every mesh, shown / hidden and why, your own choice per mesh), shows the fighter's meshes as the game's **visibility animations** say (faces, eyes, ... per motion), follows the scripts' **visibility commands** (Model_Changer & co., the expression script too), draws **effect colours / alphas as the game scales them** and the **body overlays / flashes**, has a **Hitboxes** toggle, and draws **swoosh / streak effects the right way round** (following particles follow their emitter's live turn; camera billboards were mirrored); see "Model parts, visibility, colours, arcs (v1.6.2)" below. v1.6.1: the Hitbox Viewer's **effects follow the same scripts as its hitboxes** (one rule for both: the selected tab's game and effect scripts, edits followed as you type, an effect.bin opened alone works), **common effects are drawn** (the game's data/effect/common, found above the fighter's folder or picked once with **Common effects..**), and **effect rates** (`LAST_EFFECT_SET_RATE`, a spawn's own Rate) speed up / slow down particles, models and lifetimes; see "Effects: scripts, common bank, rates (v1.6.1)" below. v1.6.0: **the Hitbox Viewer draws the effects** (Level 2: the .ptcl particles simulated, the effect models animated, the sword trails textured; approximate, see "Effects drawn" below; Level 1's markers are their own toggle). v1.5.0: **the Hitbox Viewer shows the effect script's effects** (Level 1: where each effect plays; see "Effects in the Hitbox Viewer" below). v1.4.13: **Buffer_Clear / Buffer_Set** (exe_v46l): `Buffer_Clear(Target, Inputs, Frames)` empties a fighter's input buffer (Inputs bits: 1 attacks, 2 specials, 4 jump, 8 shield / dodges, 16 grab, 32 taunts, 64 stick commands; 0 everything), now or for some frames; `Buffer_Set(Target, Input, Direction, Frames)` puts a press in it as if pressed (a stick direction, + 8 flicked), for the game's window or Frames. In New Commands / Inputs, with help (how the game's buffer works, the difference from Input_Set) and examples (Super God Fist's release, a buffered jump at the end of a move, ...); the variable `BUFFER_CLEAR` (`0x0F0003C9`, MSC's way) has a name. Tested by `new_var_test.cs` and `hitbox_var_test.cs`, 0 failures. v1.4.12: **Position_Place / Position_Offset_Get and Target 12** (exe_v46k): `Position_Place(Target, Relative, Fwd, Up, Depth, Axes, Frames, Collision)` puts a fighter (or this object) at a stage point, in front of / above this object, moved from where it is, or this object next to the target, some axes only, once or held every frame (Collision 1: through the stage while held); `Position_Offset_Get(Target, Axis, RelativeTo, Variable)` reads its stage position / facing, how far in front / above, behind its back, or the distance: the position variables' uses as commands (the variables keep working). Every command that takes a Target (the input commands too) takes **Target 12**, the fighter this attack hit (its newest hit only; nobody once the attack is over, unlike Target 2), and `Last_Hit_Get` Which 2; its variables are named `ATKHIT_...` (`0x0F0002C8`-`0x0F0002FF`). Help, examples (a Target 12 one for every changed command), tooltips. Tested by `new_var_test.cs` (176 checks: every example compiles and round-trips) and `hitbox_var_test.cs` (159 checks), 0 failures. v1.4.11: **variables in Extra hitboxes** (exe_v43): `Extra_Special_Hitbox` / `Extra_Extended_Special_Hitbox`'s Damage, Angle, KBG, FKB, BKB and Size take a variable (`Angle=STICK_ANGLE`, `Damage=VAR_0`, `Size=charge`, an ID such as `0x0F000300`) with flags after it: `|FOLLOW` (read again every frame while the hitbox is out), `|WORLD` (Angle: a screen angle, mirrored when facing left), `|NEG` (minus it); they compile to the ID in the parameter word (flags in bits 20-23) and show by name. New variable names `STICK_ANGLE` / `STICK_ANGLE_RAW` / `STICK_LEN`, the C-stick's, `ROT_X` / `ROT_Y` / `ROT_Z` (`0x0F0003C0`-`3C8`). Help and four new examples (a stick-aimed hit, one that follows the stick, the fighter's rotation as the angle, a hitbox growing with a charge; an Extended capsule aimed with the C-stick). The Hitbox Viewer draws a variable with the script's last `SET_FLOAT` of it (else a stand-in) and lists it in the Extras column. Tested by `hitbox_var_test.cs` (build it next to the built exe: `csc -out:HvTest.exe -r:SALT.dll -r:SM4SHCommand.exe` + mono's mscorlib / System / System.Core, `-nostdlib`; `mono HvTest.exe Events.cfg Aliases`: 122 checks, 0 failures). v1.4.10: **Gravity_Set** (exe_v42): `Gravity_Set(Accel=0.02, MaxFall=0.6, Mode=0)` sets a fighter's gravity and max fall speed for the rest of the move (Mode bits: 1 multipliers of its own, 2 cut a faster fall at once, 4 no fast fall; -1 keeps its own); it ends by itself at the next status, a hit that takes effect, a ledge grab or a KO. In New Commands / Fighter state with its help and examples; the variables `GRAVITY` / `MAX_FALL` (`0x0F000337` / `338`, read only) have names. v1.4.9: **New_Var** (exe_v40): `New_Var(Name=charge, Type=int, Initial=0, Scope=move)` declares a variable with your own name (int or float, a starting value, kept per object or reset per move; slots `0x0F000380`–`0x0F0003BF`, 64 per object). The name compiles in every variable parameter of every open script (and in int parameters that take a variable ID, such as `SUB_FLOAT_2`'s) and is shown wherever the variable is used; the command stores the name, so opening the file again brings the names back. `Slot` is optional (the name's slot, else the lowest free one) and shown when the script is shown again. View > Commands has it under New Commands / Variables with its help, examples and the names declared in the open scripts; hovering a name shows its slot, type and scope. Int parameters that hold a variable ID (named `...Var...`: `SUB_FLOAT_2`, `Float_Var_Compare_Var`, ...) now show the variable's name (`VAR_0`, a New_Var name) like variable parameters do. v1.4.8: `Leave_Ground_Cancel(Enabled)` (exe_v39: a grounded move goes on in the air instead of ending in Fall) in New Commands / Fighter state, with its help and examples. v1.4.7: View > Commands puts every command this mod adds (33 then) under one group, **New Commands** (first in the list), in subgroups (Hitboxes & hits, Fighter state, Inputs, Position & rotation, Animation, Targets & tracking, Threads); vanilla commands stay where they were. Each new command has in-depth help (how it works, each parameter's values, gotchas) and several complete examples, and clicking a group shows its overview (targets, compare methods, variables, what the commands need). Variable names (`VAR_0`, `SELF_HIT`, ...) compile in int parameters too (the new commands' `Variable` parameters and `SUB_FLOAT_2`'s were refused: "must be a whole number"), and the new commands' `Variable` parameters are variables, shown by name. v1.4.6: threads fixed (a script with a `Thread_Start` block was cut at the block when its file was opened again: everything after it was lost), and the Hitbox Viewer runs thread blocks on their own; new commands Hit_Check / Hit_Get (what an attack connected with: hurtbox, shield, ...), Rotation_Get / _Set, Position_Get / _Set, Motion_Get / _Set, Last_Hit_Get, Target_Slot_Get and the fighter-state commands (Status_, Hitstun_, Hitstop_Set, Damage_, Body_State_Set, Armor_Set, Item_State_Set, Stage_Collision_Set, Joint_Position_Get, Animation_Rate_Set) (`ACMD-new-commands.md`; they need the matching cross_f.rpx). v1.4.5: `ModAnimNames.txt` names Supamario's Kamehameha projectile scripts (fly1-3, finish1-3). v1.4.4: the Hitbox Viewer plays a mod's scripts with their own animations from other motion folders and draws the held model they show (Kirby's Marth-copy sword aerials: `marthbody` animations, `marthsword` on `LHaveN`), from `->` lines in `ModAnimNames.txt`. v1.4.3: `ModAnimNames.txt` names the scripts the mods add (Kirby's Marth-copy sword scripts); loaded with `AnimNames.txt`, which keeps your own labels. v1.4.2: kinetic types listed in Set_Kinetic_Handler's description; Track_Target Mode bit 4 (no gravity). v1.4.1: Hitbox Viewer fixes (Extra hitbox commands, fractional FRAME / WAIT timers, the selected tab's script) and a DI multiplier. v1.4.0: usage examples in View > Commands.

**Run:** needs .NET Framework 4 (built into Windows 10/11). Windows may warn that the exe is from an
unknown publisher ("More info" > "Run anyway"); if the zip was downloaded, right-click it > Properties >
Unblock before extracting. A file or fighter folder can be dragged onto the exe (or given on the command
line) to open it. If anything goes wrong, the error and its details are written to
`Sm4shCommand_errors.log` next to the exe.

**Build:** open `Sm4shCommand.sln` in Visual Studio (Windows, .NET Framework 4.0 or later) and build. On Linux
(v1.4.7's exe): mono's `xbuild` with Microsoft's C# compiler (Roslyn, from the .NET SDK, as for Sm4shExplorer:
`tools/sm4shexplorer/README.md`), on a copy of this folder with two case links the project files expect
(`ln -s Params SALT/SALT/PARAMS`, `ln -s Gui SM4SHCommand/GUI`):
`xbuild SM4SHCommand/SM4SHCommand.csproj /p:Configuration=Release /p:CscToolPath=$PWD/roslyn /p:CscToolExe=csc`.
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
| Undo emptied the script | Opening a script put its text in the undo history, so pressing Ctrl+Z past your own edits removed the whole script. Loading isn't an undo step any more. |
| EFFECT_FOLLOW_COLOR unlabeled, in hex floats | Its parameters are named and typed: `Graphic, Bone` (int), `X, Y, Z, XRot, YRot, ZRot, Size` (float), `Terminate` (int), `R, G, B` (float, 0-255), e.g. `EFFECT_FOLLOW_COLOR(Graphic=0x1000012, Bone=0x0, X=10.0, Y=0.0, Z=-50.0, XRot=0.0, YRot=90.0, ZRot=0.0, Size=5.5, Terminate=0x1, R=250.0, G=0.0, B=250.0)`. Float parameters also accept the hex float bits int parameters show (`0x437A0000` = 250.0; up to `0xFFFF` a hex value is that number), so older text still compiles (same bytes). |
| Colors | The name of a command with R, G, B parameters (`EFFECT_FOLLOW_COLOR`, `Color_Overlay`, ...: any command whose definition names three parameters R/G/B or Red/Green/Blue) is drawn in the color they make. Right-click the line > **Pick Color for ...** opens a color picker set to the current color and writes the chosen R, G, B (one undo step; 0-1 values stay 0-1). |
| Numbers only in hex | View > **Show Numbers as Decimal** (remembered in `Sm4shCommand.ini`): int parameters show as decimal (`Angle=361`, `KBG=100`). Int parameters that hold float bits show as floats (`unknown=0.6f`; View > **Show Float Values in Int Parameters as Floats**). Hashes, effect / sound IDs and bit fields stay hex: values above 0xFFFF, and parameters listed in View > **Parameters Always in Hex..** (default: Hash, Graphic, GFXLeft, GFXRight, SFX, HitBits, Flag, Variable1–3). Every form compiles in any int parameter (`0x169`, `361`, `1.5f`), with or without the setting. Checked on 3,443 scripts (Kirby's game/effect/sound/expression and weapons, Captain Falcon): the same bytes back as with hex. |
| Comments were lost on save | `// ...` (on its own line or after a command) and `/* ... */` comments are kept. The game's .bin has no room for them, so saving writes each commented script's text to `FILE.comments` next to the file (e.g. `game.bin.comments`; deleted again when no script has comments); the game never reads it. Opening a script shows that text again. If the .bin was changed by another tool since, the comments go back onto the lines that still match (compared by what they compile to, so `0x169` and `361` match). File and fighter mode (not project mode). A comment after a command used to be a compile error; comments inside `if` blocks are fine too. |
| Editing a parameter meant clicking or arrowing to it | View > **Jump Between Parameters** (off by default, remembered in `Sm4shCommand.ini`): **Tab** selects the next parameter's value on the line, so typing replaces it (in a `Hitbox`: ID, Part, Bone, then Damage, ...); **Shift+Tab** goes back; after the line's last parameter it goes on to the next line that has some (in `if(Bit_Variable_Test(...))` the inner call's values). View > **Parameter Jump Key..** picks another key. Off, Tab works as before. |
| Value tooltips | Hovering a number in a parameter explains it, from the text files in the `Tooltips` folder next to the exe. They're generated from the MSC Note Sheet, the fighter_param sheets and the article list, with `make_tooltips.py`. They cover variables (work variables, fighter_param stats, STrans / STransGroup IDs, the position variables `0x0F0000xx`), common effect IDs in `Graphic=`, the 361 angle, and each fighter's article IDs and special-move params (`0x05`–`0x09xxxxxx`, with default values). Per-fighter entries are used when the open path is `.../fighter/NAME/...`. **Right-click a number > Edit Tooltip..** adds or changes one in `Tooltips/custom.txt`. Tools > **Reload Tooltips** / **Open Tooltips Folder**. The file format (filters by fighter, command, parameter name, type or position) is described at the top of `SM4SHCommand/Classes/Tooltips.cs`. |
| Variable aliases | Names for variables, e.g. `SET_FLOAT(Value=1.5, Variable=LASTHIT_HITSTUN_MUL)` instead of `0x0F000052`. Loaded from the text files in the `Aliases` folder next to the exe (`NAME = 0x0F000052`, any variable form works; `custom.txt` for your own, it wins). `Aliases/variables.txt` (from `make_tooltips.py`) names the common variables of `tools/position_vars_cave.py`: `POS_SELF_X` … `POS_OPP_OFFSET_X` … `POS_SLOT1_X` …, the combat ones as `TARGET_QUANTITY` (`SELF`, `OPP`, `LASTHIT`, `SLOT1`–`SLOT8` × `HITSTUN`, `HITSTUN_DEALT`, `HITSTUN_MUL`, `HITSTOP_SHAKE`, `HITSTOP`, `OFFSET_X/Y/Z`) and `SELF_ANIM_RATE`. The input / state variables (`0x0F000100`–`0x0F00025F`) are `TARGET_QUANTITY` too: `SELF_ATTACK`, `OPP_JUMP_PRESSED`, `LASTHIT_INPUT_OFF`, `SELF_STICK_X`, `SLOT2_DAMAGE`, `SELF_INTANGIBLE`, ... (docs/position-variables.md "Inputs and state"). View > **Show Variable Aliases** (on by default) shows them by name; names always compile, case doesn't matter, and tooltips work on them. Tools > **Reload Variable Aliases** / **Open Aliases Folder**. |
| Tooltips stayed on screen | The editor's tooltip only went away on a mouse move over the editor, so after switching programs, moving the window or changing tabs it stayed over other tabs, sometimes for good. It's now hidden as soon as the pointer isn't over a visible editor in the active window (and a tooltip still waiting for its delay isn't shown then). |
| No list of what commands exist | View > **Commands..** (**F1**): every ACMD command in groups by what it does (Script flow, Variables, Hitboxes, Grabs & throws, Effects, Sound, Camera, Movement, Items, ...), with its description, each parameter's type and meaning, and a template line. Search filters by name, identifier, description or parameter ("knockback", "B738EABD"). **Insert into Script** (or double-click / Enter) adds the command below the caret in the open script with its first value selected; **Copy** copies it. The group is each command's `Category:` line in `Events.cfg`. **Examples:** 332 commands show a usage example under the template: a real use from the game's scripts (`// fighter, script (file)` and the line, with its block for True / False / Else / Set_Loop; `make_examples.py` picks them from the vanilla fighter folder into `vanilla_examples.json`), and, for the new commands, hand-written ones (`EXAMPLES` in `tools/acmd_ext_help.py`). **Insert Example** adds it below the caret (comments included, indented like the caret's line); **Copy Example** copies it. They're the `Example:` lines in `Events.cfg`. **New Commands** (v1.4.7): every command this mod adds is in this one group, at the top, in subgroups (`Category: New Commands / Inputs`: a group `A / B` is shown as B inside A); each has a **help** section after its parameters (`Help:` lines: how it works, the parameters' values, gotchas) and several examples, and picking a group shows its own help (`Group:` blocks: for New Commands, the targets, compare methods, variables and what the commands need). The help, groups and examples are written in `tools/acmd_ext_help.py` (`acmd_ext_cave.py --labels` puts them in `param_labels.json`, `make_events_cfg.py` in `Events.cfg`); search finds words in the help too. |
| Unknown parameters, wrong types | Every `unknown` parameter is labelled from the game's command handlers (`docs/acmd-params.md`; data in `param_labels.json`, applied by `apply_param_labels.py`). 85 commands' int/float types are fixed, 62 `unk_` commands are named (old `unk_XXXXXXXX` names still compile), and misnamed commands give their real name in the description. |
| Command definitions / descriptions | Tools > **Command Definitions..** edits names, parameter names and types, and descriptions, and adds new commands; Save writes `Events.cfg`. Hovering a command in the editor shows its description and parameters; hovering a parameter shows its name, type and description. A description can run over several lines (each further line in `Events.cfg` is a line break; Save keeps them), e.g. Set_Kinetic_Handler's kinetic types, one per line in groups (in the air, jumps, on the ground, moved by the animation, ledge, hit, ...). A long one is cut to its first 24 lines in the editor's tooltip (the command list shows it all), and hovering a parameter's value shows the description's line for that value (`Set_Kinetic_Handler(ID=0xA)`: "0x0A  AIR_STOP - in the air with no drift control"). |
| No way to see hitboxes | Tools > **Hitbox Viewer..** (Ctrl+Shift+H) on an open ACMD script shows its game script's hitboxes on the fighter's own model, posed by its animation, frame by frame: Play, `<` `>` and the slider step game frames (`Set_Frame_Duration` / `Frame_Speed_Multiplier` slow the animation as in game). Timers can be fractional: `FRAME(Frames=8.2)` comes out on the first game frame at or past 8.2 (frame 9 at normal speed), and `WAIT(Frames=0.2)` takes one frame (it isn't rounded down to none). The fighter folder must be laid out as in the game: `NAME\model\body\c00` (model.nud, model.vbn, model.jtb), `NAME\motion\body\main.pac` and `NAME\script\animcmd\body`; the animation is found from the script's name. There is one viewer: it shows the script of the tab selected in the main window and switches when you pick another script tab (Ctrl+Shift+H again brings it to the front). Picking another animation in the list shows that animation's game script (the saved one in game.bin; edits are followed for the open script), or no hitboxes when it has none. The models are textured (model.nut; **Textures** turns it off). Hitboxes are colored by ID, extended ones drawn as capsules (all the hitbox commands, including `Extra_Special_Hitbox` / `Extra_Extended_Special_Hitbox`, whose six extras are in the list's **Extras** column), with their launch angle (`S` for 361); intangible / invincible / super armor are shown. `True` / `Else` blocks: **If conditions true** picks the branch. Drag to rotate, right-drag to pan, wheel to zoom, double-click for the side view; **Bones** shows the skeleton, **Meshes..** the hidden expression meshes. The viewer follows the editor as you type (a script that doesn't compile shows the saved one, with the error). **Enemy**: Mario (the `mario` folder next to the fighter's, e.g. `fighter\mario`; **Enemy model..** picks another fighter folder, remembered) stands where the picked hitbox hits, takes the hit (hitlag), then flies along the calculated trajectory with his damage animation. The corner of the view says what state he's in (hitlag, hitstun and frames left, which cancels he could use, out of hitstun). **Play until the enemy can act** (remembered) makes the timeline run past the end of the animation (the attacker holds its last pose) to the frame he's out of hitstun. **Show hitlag freeze** (remembered) puts the frames both fighters stand still in hitlag (and any `SELF_HITSTOP` / enemy hitstop from the script) on the slider, so playback is in real game frames; the label shows the script frame and "(hitlag freeze)". **Floor** (on by default) keeps the enemy on the ground line; off, he follows the trajectory through it. Pick a hitbox in the list for the **knockback / hitstun calculator** (Sm4sh-Calculator's formulas): target fighter (all 58, from `Viewer\Fighters.txt`), target and attacker (rage) %, smash charge, staleness, crouch cancel, aerial target, launch rate, DI (**DI at** a stick angle; **DI x** multiplies how far DI turns the launch: 0.5 half, 2 double, 0 none). An Extra hitbox's own extras count too: HitstunMul, HitstopMul / HitstopFrames (enemy hitlag), SelfHitstopMul / SelfHitstopFrames (attacker hitlag) and DIMul (multiplied with **DI x**). **Hitstun x**, **Attacker hitstop x** and **Enemy hitstop x** multiply the hitstun and the two hitlags (before the script's own modifiers). It gives damage, knockback, launch angle and speed, hitstun and the first actionable frame, hitstun cancel frames (worked out again for the final hitstun, and later by any hitstop frozen during it), hitlag, shield stun and the distance travelled, and draws the trajectory (no stage) in the view. The script's own modifiers count: `SET_FLOAT` to the hitstun / hitstop variables (`LASTHIT_HITSTUN_MUL`, `OPP_HITSTUN_MUL`, `LASTHIT_HITSTUN`, `LASTHIT_HITSTOP` / `_HITSTOP_SHAKE`, `SELF_HITSTOP`, ... `0x0F000040`–`0x0F000057`) change the hitstun, hitlag and when the enemy flies, at the frame they run relative to the hit, and are listed under the results; the animation rate variable (`0x0F000098`) speeds up the timeline, and the hitbox's own Hitlag multiplier and electric effect are used. Any fighter whose folder has model, motion and script. |

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

## Effects in the Hitbox Viewer (v1.5.0, Level 1)

The viewer runs the effect script of the same name (effect.bin next to game.bin, or the open tab's effect editor,
followed as you type) on the game script's timeline: each game frame moves it by the same animation frames
(`Set_Frame_Duration` / `Frame_Speed_Multiplier` / the animation rate in the game script slow it as in game; the
effect script's own are ignored, the motion's rate is one), with the same `FRAME` / `WAIT` timers, loops,
`True` / `Else` (**If conditions true**) and threads.

- **What it reads.** Every effect command, by its name and its parameters' names (Events.cfg / the ACMD events
  sheet): `Graphic_Effect*`, `External_Graphic*`, the `EFFECT_*` family (`_FOLLOW*`, `_FLW*`, `_FLIP*` with their
  GFXRight / GFXLeft, `_COLOR`, `_ALPHA`, `_GLOBAL`, `EM_EFFECT_*` ...): the effect ID, bone, offset, rotation, size,
  its colour / alpha; `LAST_EFFECT_SET_COLOR` / `_ALPHA` / `_RATE` / `_SCALE` (and `LAST_PARTICLE_SET_COLOR`) on the
  last effect; `Terminate_Graphic_Effect` (by ID), `EFFECT_OFF` / `EFFECT_REMOVE_ATTR` (all), `EFFECT_OFF_HANDLE`
  (the last), `EFFECT_DETACH_KIND` (a following effect stays where it is); sword trails (`Sword_Glow`, `Sword_Glow2`,
  `Sword_Trace`, `AFTER_IMAGE*`: every command with Bone1 / Bone2) and `Terminate_Sword_Glow` (+ its FadeTime); screen
  and light effects (tints, flashes, lights, wind, `EFFECT_PAUSE` / `_RESUME`, the `_WORK` calls whose ID is in a
  variable) are listed, not drawn.
- **Following or one-shot.** The developers' `EFFECT_FOLLOW*` / `_FLW*` (`External_Graphic` = EFFECT_FOLLOW,
  `Graphic_Effect4` / `5` / `6` = `EFFECT_FOLLOW_NO_STOP` / `_RND` / `_ALPHA`) move with their bone until terminated
  or the script's end; the others are placed on their spawn frame and stay there, shown for their emitter set's
  lifetime (the .ptcl's one-time emitters: start + emission + particle life), a set that never stops by itself until
  terminated, an effect whose files aren't there (common effects) 20 frames.
- **Names.** An ID `0xBBBBnnnn` is entry nnnn of bank 0xBBBB (docs/efc-format.md): the fighter's
  `effect/NAME/NAME.010d0000.efc` names the `.ptcl`'s emitter set (and an effect model), shown as the effect's name
  (`PtcSupamarioGfCsg_Crg`, `model EffSupamarioGfCsgBas`); bank `0x300 + kind` is looked up by the fighter kind's
  folder (this fighter's, else the sibling `fighter/<kind>`: Kirby's copies use Hero's 0x345), a port's base fighter's
  number in its own folder (Hero's 0x32C, Robin's); common effects (`0x01000000 +`) from the tooltips (gfx.txt).
- **In the view.** Each effect is a sphere (radius 2 x Size) at its bone + offset, with its axes (X red, Y green,
  its forward Z blue) turned by its rotation (degrees, X then Y then Z), coloured by its set colour, dashed when
  one-shot, labelled with its ID and name (**Labels**); sword trails are the blade's line with a fading band over its
  last frames (**Trails**). **Markers** (v1.5.0's **Effects**) turns them off. The **Effects** tab next to the hitboxes lists the frame's
  effects (or **every effect of the script**): ID, name, bone, offset, rotation, size, colour / alpha / rate / scale,
  follow or one-shot, its frames (and why it ended), the facing check; trails and screen events below them.
- **Flip facing** turns the scene round as the game turns a fighter facing left (and shows a `_FLIP` call's
  GFXLeft). Effects turn with it rigidly here; in game an effect isn't simply turned: what the God Fist / Core Breaker
  ports learned (tools/xv2_smash_fx.py `facing_check`: on bone 0 only a height / forward offset and a Y turn of 0 or
  180, on any other bone no offset and no turn) is checked, and an effect that breaks it is marked `!` in the view and
  in the list, with why.
- **Approximate / not done (Level 1).** (v1.6.0 draws particles, models and trails: below.) The effect's own
  rotation order and the game's left-facing transform of effects aren't decoded (see Flip facing); `Random*` offsets
  are left out; an effect whose ID comes from a variable (`_WORK`) shows "(from variable ...)"; `EFFECT_FOLLOW_STR`'s
  bone (a name hash) isn't resolved; `Terminate` flags (end with the status) aren't modelled (the script's end is);
  one-shot lifetimes ignore a set's looping emitters' own life and `LAST_EFFECT_SET_RATE`. Tested headless by
  `effect_viewer_test.py` / `effect_viewer_test.cs` (Super God Fist, Mario's up smash / back throw, Hero, Kirby's
  BraveSword17, timeline cases: 32 checks).

## Effects drawn in the Hitbox Viewer (v1.6.0, Level 2)

On top of Level 1 (which effect plays where and when, above), the viewer draws what each effect is, from the
fighter's effect bank: the `.ptcl` emitter set's particles, the `.efc` entry's effect model and the sword trails'
textures, blended over the fighter and depth-tested against it. Toolbar: **Effects** (draw them), **HQ** (quality),
**Dark bg** (a dark background, on by default: additive effects show as on a stage), **Markers** (Level 1's spheres /
axes; **Labels** their names), **Trails**.

- **Particles** (`Classes/Viewer/Particles.cs`; a port of `tools/fx_render.py`'s Smash 4 simulation, the rules in
  docs/ptcl-format.md). Each emitter of the set is stepped one game frame at a time from the effect's start to the shown
  frame: emission (start frame + emit start, end frame for one-time emitters, interval + its random, the rate carried
  between frames, key-animated), the volume (point, circle random / even with its sweep, filled circle, sphere, filled
  sphere x the shape scale), velocity (all-direction + directional along the emit direction, spread, its random part),
  then each frame the move by the velocity it had, air resistance and gravity (world or the emitter's); life (+ its
  random), the scale / alpha / colour curves over the particle's life (eft's 3-key ramps, colour keys x colour scale x
  the emitter's colour / alpha multipliers 0x378-0x3A7), rotation (init + random, its speed), the emitter's key
  animations (rate, life, emitter scale / rotation / translation, colours, alpha, speeds, particle scale, shape scale)
  and its follow type (0: the particles move with the effect; 1: left where they were born; 2: by its position).
  Particle types: camera billboards (0, 7), Y billboards (8), XY / XZ plates in the emitter's frame (1, 2),
  directional along the velocity (3, 4); an emitter's primitive mesh is drawn instead of the quad. Texture slot 0 is
  decoded through the model textures' GX2 decoder (BC1-5, RGBA8; its channel selector), its first flipbook cell (UV
  scale); blend alpha / add / subtract (0x324); the colour combiner (0x314: colour, colour x texture, colour 1 to
  colour 0 by the texture). Distortion passes aren't drawn. The random numbers are a fixed-seed generator per effect
  and emitter: the same picture every time, scrubbing back gives the same particles.
- **Effect models** (an `.efc` entry's `model/<name>/`): model.nud / .nut / .vbn, posed by model.omo from the
  effect's spawn (looped while it follows, held on its last frame for a one-shot), its materials' `NU_effColorGain`
  (colour and alpha) and `NU_effTransUV` / `NU_effScaleUV` from model.mta (else the material's own), the vertex
  colours, blended by the material (dst 2 add, 3 subtract, else alpha), placed by the call's bone / offset / rotation
  x Size. A one-shot model-only entry lives as long as its animation.
- **Sword trails** (`Sword_Glow` / `AFTER_IMAGE*`): the blade's two points on this frame and the BlurLength frames
  before (4 steps between each two), as a ribbon with its two textures: the texture ids through the game's trail-name
  table (`TrailNames.cs`: ids 1-259 the game's, 260 on `tools/trail_table_cave.py`'s), `<name>.nut` (NTP3 or NTWU)
  from this fighter's or the other fighters' `effect/*/trail` folders, shaded as the trail shaders 1 / 2 / 3
  (docs/native-notes.md "The trail shaders"; 3 = Hero's retracting trail), faded over Terminate_Sword_Glow's frames.
  A trail whose texture isn't found keeps Level 1's band.
- **Responsiveness.** Particles a set's emitter keeps: 150 (HQ 600), quads drawn a frame: 2,500 (HQ 8,000); the
  status line says when a cap was hit. Without HQ the effects are drawn at half resolution and added back smoothed
  (an explosion's screen-filling glows: about 0.2 s a frame at worst, 60 ms typical, against 0.5 s), textures
  nearest-sampled unless blown up past twice their size; HQ draws at full resolution with bilinear textures. A
  simulation is kept per effect and stepped on as the frame moves on (a frame back starts it again).
- **Approximate (no game shaders, no bloom).** The emitters' own pixel / vertex programs aren't run: the combiner
  word decides the colour, and the alpha comes from the texture's own alpha channel when it has one, from its red
  when its alpha is constant (BC4's R R R 1; the converted effects' programs read it so); no HDR / glare / bloom,
  no refraction (distortion passes and trail shaders 1001 / 1002 left out, the latter drawn as 1); premultiplied
  (ONE / INV_SRC_ALPHA) trail blending assumed; no lighting on effect models (`NU_angleFadeParams`, `NU_effRotUV`,
  the efc's mesh-switch records not read); complex emitters' fields (random / magnet / spin / collision /
  convergence / curl noise), fluctuation and child emitters, stripes (types 5 / 6 drawn as quads in the emitter's
  frame), velocity stretch and texture slot 2 aren't simulated (slot 1 is a mask since v1.6.1); eft's random generator isn't reproduced (the
  sets' shapes and timings are, the exact scatter isn't); a
  following effect's particles vanish when it's terminated (the game lets live ones finish). (v1.6.1: rates and
  common effects are drawn: below.) The view's camera is orthographic: a
  flat ring on the ground (Fake Death's) is edge-on from the side; drag to look from above.
- **Tested** headless by `effect_viewer_test.py` / `.cs` (58 checks): the live particles on frames 0-29 of the God
  Fist's Csg_Crg and Csg_Circle, Core Breaker's Cor_Fire, Fake Death's ring and Mario's up special sets equal
  `tools/fx_render.py`'s simulation of them (every emitter with no random life / gap), a particle's path (velocity,
  air, gravity) equals it to 0.002, the fixed seeds (stepping on and back), the textures equal `tools/ptcl.py`'s
  decode, the God Fist aura and Core Breaker orb models' frames and colour gain equal `tools/mta.py`'s and they pose,
  the trail ids / names / Hero's textures, the blending; plus Level 1's 32. Screenshots (God Fist, Core Breaker,
  Fake Death, Kirby's BraveSword17, Mario's forward smash) under Xvfb.

## Effects: scripts, common bank, rates (v1.6.1)

- **Where the scripts come from: one rule for hitboxes and effects** (`HitboxViewer.PickCommands`,
  `Classes/Viewer/ViewerScripts.cs`). The viewer shows the selected tab's animation. While it is shown, each script
  (game for the hitboxes, effect for the effects) is that tab's editor text, compiled as you type; a compile error
  shows the saved script and says why. Another animation picked in the viewer's list shows that animation's saved game
  and effect scripts. The saved files are the ones open in the main window, else the game.bin / effect.bin next to
  them on disk (read again when they change on disk; read from a copy, so the main window can always save over them).
  - Fixed: picking another tab in the main window kept the first tab's effect editor (its edits drove the effects of
    every script shown after it); the effect.bin next to game.bin was read once when the viewer opened (later saves
    weren't seen); in single-file mode an effect.bin opened alone was refused ("No game.bin is open") or its script
    taken for the game script. Now an effect.bin (or sound / expression.bin) opened alone shows its effects with the
    game script's hitboxes from the game.bin next to it, and a game.bin opened alone finds its effect.bin.
- **Common effects** (ids `0x01000000 +`, bank 0x100: dust and landing clouds, hit sparks, fire puffs, ...). The game
  keeps them in `data/effect/common/common.010d0000.efc` / `.ptcl` (+ `model/`, `trail/`), next to `data/fighter`. The
  viewer looks for that folder above the fighter's folder (`fighter/NAME/../../effect/common`, any folder further
  up too: a dump's content/patch/data, a mod's data folder). If it isn't there, **Common effects..** (next to Enemy
  model..) picks it once: the folder itself, `data/effect` or `data` (remembered in Sm4shCommand.ini,
  `ViewerCommonEffects`). Common effects are then drawn as the fighter's (particles, models, one-shot life from their
  set) and named by their tooltip name with the set after it; without the folder they stay markers, and the status
  line says how to pick it. The common trail textures (`TexCommonHammerTrace`, ...) come from its `trail` folder.
- **Effect rates.** `LAST_EFFECT_SET_RATE(Rate)` sets the last effect's playback speed: the game multiplies the
  effect's emitter-set step by it (eft's frame step x the rate; docs/ultimate-fighter-port.md: Ultimate's command of
  the same name writes the set's rate, "as Smash 4's command of the same name"), so the viewer steps the effect's own
  time by the rate each game frame: rate 2 runs two of its frames a game frame (emission, motion, life), 0.5 one every
  other game frame, the particles drawn between their steps by the fraction; its model's animation (omo / mta) plays
  at the rate; a one-shot's life becomes life / rate game frames. `EFFECT_FLW_POS_STRENGTH`'s own `Rate` does the
  same. `LAST_EFFECT_SET_RATE_WORK` (the rate in a work variable) is listed, not applied (the value isn't known
  here). The game script's `Set_Frame_Duration` / `Frame_Speed_Multiplier` / the animation rate slow the effect
  script's timers (FRAME / WAIT, as in v1.5.0) but not the particles: an effect plays on game frames at its own rate
  (the system's step), as the trails do (docs/native-notes.md "Sword trails": the tick's step x the trail's rate);
  `LAST_EFFECT_SET_DISABLE_SYSTEM_SLOW` exists for the global slow-down, which the viewer has none of.
- **Texture slot 1** (new, approximate): an emitter's second texture (vanilla fire, e.g. Mario's: a shape flipbook
  over a noise texture) is drawn as a mask on the first (its first cell, its own UV scale): the fire puffs no longer
  show as squares.
- **Tested** (`effect_viewer_test.py` / `.cs`, 80 checks, 0 failures): rated lives (2, 0.5, 1.5, 1); three
  `LAST_EFFECT_SET_RATE`s in a script; `EFFECT_FLW_POS_STRENGTH`'s Rate; every particle of the God Fist's Csg_Circle at
  rate 2 on game frame 1 + t = at rate 1 on 1 + 2t, at 0.5 on 1 + 2t = at 1 on 1 + t, half a step drawn between; the
  aura model's frame at 0.5 / 2; the common bank found as the game lays it out and picked from data / data/effect /
  the folder (the game's own common files aren't in this repository: the test puts a stand-in there, Supamario's bank
  under the common name), its sets, model, names, life and particles; without it markers and tooltip names; the
  script rule (single-file effect.bin and game.bin, fighter mode's sub-tabs, the editor text compiled, an edit, a
  compile error falling back with the error, another animation's saved script, game.bin read from disk next to an
  effect.bin, a file changed on disk read again). The editors themselves (FastColoredTextBox) don't load on Mono:
  the rule picking a tab's editor is what's tested headless.

## Model parts, visibility, colours, arcs (v1.6.2)

- **Model parts tab** (next to Hitboxes / Effects; the toolbar's **Model parts..** opens it, replacing the v1.4 mesh
  dialog): every mesh of the fighter's model (and of the held model) with a **Show** box, what the frame shows without
  your choice (**Now**) and **Why** (your choice, a visibility group, the visibility animation, the default). Ticking a
  box overrides it; **Reset to script / default** drops your choices, **Show all** / **Hide all**. Choices are kept per
  fighter while Sm4shCommand runs. Below the list: the script's visibility commands so far and the groups' states.
- **Which meshes show by default (the Pac-Man ball bug).** Smash 4 decides it per motion from the model folder's own
  visibility animations: `material_anime_face.pac`, `_eye.pac`, `_eyelid.pac` (packs of MTA4 files named after each
  motion, `FitMarioBodyMainF00DamageHi1.mta`, whose visibility tracks switch the `_VIS_O_OBJ` meshes key by key: Mario's
  FaceN / Ouch / Blink / Nohat, Kirby's eyes and big body ...). The viewer now reads them (`Classes/Viewer/MeshVisibility.cs`
  MaterialVis): on each frame the motion's own tracks, and for a motion without a file the neutral state (Wait1's frame
  0). Meshes no track names keep the name rule (expression variants hidden). Not found in any data file: the model's
  `model.moi` lists the `_VIS_` objects (name, bone, index) but no default state; `model.xmb` / `model.nud` / the
  fighter's vl params have none either.
- **The scripts' visibility commands on the timeline.** `Model_Changer(ChangerID, ChangerState)`,
  `VIS_SET_DEFAULT(Group, State)`, `VIS_BACK_DEFAULT(Group)`, `VIS_RESET_DEFAULT(Group)` and `Visibility(State)` (the
  whole model) are run from the game, effect **and expression** scripts (the expression script now follows the same
  rule as the others: the tab's expression editor, else expression.bin), each group's state per frame, the scripts
  merged (the later change wins). `Visibility(State=0)` hides the model. A group's meshes are in the game's code (the
  VisibilityModule, accessor +0xA8: `Model_Changer`'s handler `0x02BD70E8` calls its vt +0xCC op 0x2711 -> vt +0x4C,
  which looks the group up in a per-fighter table of per-state part records at module +0xC and switches them through
  the ModelModule's vt +0x17C), not in the fighter's files, so they come from **`VisGroups.txt`** next to the exe
  (`fighter group state: mesh, ...` and `fighter group default: state`; shipped empty, documented in the file): a
  group listed there shows its current state's meshes and hides its others; without it, the group's changes are
  listed in the tab, not applied.
- **Effect colours and alphas as the game applies them.** The colour commands' values are 0-255 and divided by 255
  (`EFFECT_*_COLOR`, `LAST_EFFECT_SET_COLOR`: 510 = 2.0), the alphas percents divided by 100 (`LAST_EFFECT_SET_ALPHA`,
  `EFFECT_*_ALPHA`, `Graphic_Effect6` / `7`); `LAST_PARTICLE_SET_COLOR`'s multipliers (0-1.5) go on top; the light
  commands' colour (`EFFECT_LIGHT` / `_FOLLOW_LIGHT`) is the light's, not the effect's. The result multiplies every
  emitter's colour (x its own emitter colour 0x384 / alpha 0x3A4 x the particle's curves) and the effect model's colour
  gain. v1.6.0 / 1.6.1 took a colour over 5 as 0-255 and used the alpha as it was (50 meant 50 x).
  `EFFECT_COLOR_WORK` (from variables) stays as listed.
- **Body overlays / flashes** (`Color_Overlay`, `Change_Overlay` over its Transition frames, `Terminate_Overlays`,
  `FLASH_NO_STOP` / `FLASH_OFF`, `Flash_Light_Effect` / `Change_Flash_Light_Color` added as a light) tint the fighter
  (and its held model) on their frames (**Overlays**); approximate: the colour mixed in by its alpha, no shader.
- **Hitboxes** checkbox: hides the hitbox spheres / capsules and their angle arrows (the list, the calculator and the
  trajectory keep working); remembered in Sm4shCommand.ini.
- **Swooshes / streaks the right way round.** Two fixes:
  - Particles of a following emitter (0x310 = 0, "the particle points at the emitter's live matrices") are kept in the
    emitter's own space and placed by the call x the emitter matrix **of the frame shown**, its key-animated turn
    included. v1.6.0 froze the emitter's matrix at each particle's birth, so a swoosh whose emitter swings with the
    move (Mario's up smash `PtcMarioSmashHed`: its emitters turn about Y from -180 to -100 degrees over frames 2-10;
    the common forward-air arc is made the same way) stayed where the swing started.
  - Camera billboards (types 0, 7, 8) were mirrored: their X pointed to the screen's left (tools/fx_render.py's CPU
    basis), so the quad was seen from behind and every asymmetric sprite (a streak, an arc) pointed backwards. eft's
    own programs build them from the view block's billboard matrix, X along the screen's right (fx_render's
    `s4_view_block`), as the viewer now does.
  Facing left (Flip facing) the scene turns round, so effects attached to the fighter come out mirrored on screen
  while billboards still face the camera unmirrored.
- **Tested** (`effect_viewer_test.py` / `.cs`, 91 checks, 0 failures): Mario's DamageHi1 face meshes on frames 0 / 3 /
  11 against `tools/mta.py`'s reading of the three packs; the parts priority (your choice > a group > the visibility
  animation > the default) and a group switching with `Model_Changer`; the visibility commands on the timeline and
  two scripts merged; the colour / alpha scaling (`EFFECT_FOLLOW_FLIP_COLOR` 100 / 180 / 510, `LAST_EFFECT_SET_ALPHA` 50,
  `LAST_PARTICLE_SET_COLOR`, `Graphic_Effect6`'s Alpha, `EFFECT_LIGHT`); an overlay set, changed over 4 frames and
  ended; a following particle placed by the live emitter matrix (Mario's up smash swoosh), the swoosh in front of him
  facing right and mirrored facing left, billboards not mirrored in either facing. Not available here: Pac-Man's and
  Dr. Mario's files and the game's common effect bank (the forward-air arc and the attack streak are common effects),
  so the two reported cases weren't drawn; Mario's own swoosh (the same make) was.

## Model parts menu, part animations, stripes, blocks (v1.6.3)

Tested with the user's own Pac-Man, Dr. Mario and Link folders (game files: not in this repository).

- **Model parts right-click menu** (the selected rows, or the one clicked): **Show now** / **Hide now** (this session,
  as the Show box), **Hidden by default for this fighter** / **Visible by default** (saved in **`VisUser.txt`** next
  to the exe as `fighter hide: mesh` / `fighter show: mesh`, read on every start), **Follow the script / default**
  (takes your choice and your saved default away), **Isolate** (only these meshes now), **Show all**. A default is the
  fighter's neutral state: a script's visibility group still shows / hides the mesh on its frames. The order a mesh is
  decided in: your choice now; a group whose state doesn't list it (hidden); the motion's visibility animation; a group
  whose state lists it (shown); the fighter's defaults (yours over `VisGroups.txt`'s); the name rule. (v1.6.2 let a
  group's current state show a mesh over the visibility animation; now the animation decides those, so a group can
  list a body together with its face meshes.)
- **`VisGroups.txt` entries for Pac-Man**, read from his expression scripts (`Model_Changer` calls) and model:
  group 0, the 3D body / the 2D Pac-Man `PizaM` (state 1: neutral air, dash attack and others through subroutine
  `0x669E43CF`); group 1, the ghosts (forward smash 1: Blinky `Aaka`; up smash 2; down smash 3; down taunt 4; win 2: 5);
  group 2, the Final Smash power pellets `FinalpoweresaA` / `B` (the "ball", state 1 in `finalstart` only); group 3,
  the up taunt's 18 signs (`boardA`-`R`, one a state). Every group defaults to 0: in Wait only the body shows. Which
  ghost sprite the up / down smash and down taunt raise on bone `GhostA1N` (`Aaka`, `Aosuke`, `Guzuta`, `Ijike` and
  the signs all sit on it; `Pinkey` alone on `GhostB1N`) is inferred: correct the lines if the game shows another.
  The file also takes `fighter hide:` / `fighter show:` defaults now.
- **Part animations.** A fighter's `motion/body` holds more than `main.pac`: `lhand.pac` / `rhand.pac` (the hands'
  poses: fists, open hands), `NAMEpt1.pac`, `NAMEsw1.pac` ... (props, swords, Pac-Man's ghosts, signs and pellets),
  each with the same motions (`FitPacmanBodyPacmanpt1C03AttackS4S.omo` beside `FitPacmanBodyMainC03AttackS4S.omo`) on
  bones `main.pac` doesn't animate. The viewer played only `main.pac` (open hands everywhere, Pac-Man's ghosts never
  moved); it now layers the parts on the main motion.
- **Billboard bones.** A bone named `..._BILLBOARD_...` turns its meshes to the camera (`BILLBOARDY`: about the
  vertical only): Pac-Man's ghosts and signs are flat sprites on such bones, drawn edge-on (invisible) before.
- **The expression script ran late.** `SetExpression` (the main window passes the expression scripts after making the
  viewer) didn't run the scripts again, so their visibility commands waited for the first edit. It does now.
- **Emitter blocks (the translucent squares, Pac-Man's neutral air).** Two causes, both fixed:
  - A combiner that takes the alpha from the texture (0x314 = 1, or a selector naming its own alpha) on a texture that
    has none (every texel opaque: a one-channel BC4 whose selector names a missing alpha channel) covered its whole
    quad. Such a texture's shape is in its red channel: the viewer now reads the alpha from red there. Reproduced with
    Dr. Mario's real Cyclone (`PtcMariodCyclone` ring1 / impact2, `PtcMariodSmashAura`), squares before, ring after.
  - A texture with no native surface (TexRes native size 0) wasn't decoded, and its quad was drawn untextured, a
    solid block. Its original image (+0x20 format 2, RGBA8, row by row) is decoded now, with its component selector
    (Pac-Man's Final Smash eyes and scores: B G R A); an emitter whose texture still can't be read isn't drawn (the
    status line counts them). Pac-Man's neutral-air blocks come from common effects (0x1000072 / 0x1000052 /
    0x1000023): the same rules apply to them once the common bank is set.
- **Stripes** (particle types 5 / 6: eft's ribbons, the sword trails `kiseki*` and streak / beam emitters) are drawn as
  ribbons: type 5 through each particle's history of places (as many as the stripe block's history length, the
  divisions between each two smoothed), type 6 through the emitter's particles; width the particle's scale, across
  facing the camera (stripe type 0) or along the emitter's Y (1 / 2); alpha from the block's start to end alpha;
  texture U across, V along. v1.6.2 drew one quad per particle in the emitter's frame, a block or bar pointing
  wherever the emitter did. Link's up special (`PtcLinkKaitengiriSword` kiseki1) now trails the blade, both facings.
- **Effect models' UVs and colours** as the effect shader (`texas_cross.nsh` MC_EFFECT, docs/smash-run-port.md "UV
  transforms") works them out: turned by `NU_effRotUV`, `U = (u + t.x) s.x`, `V = 1 - s.y (1 - (v + t.y))` (v1.6.2:
  `u s + t`, another part of a scaled / scrolled texture); `NU_effCombinerColor0 / 1` (colour 1 + (colour 0 - colour 1)
  x the texture, by analogy with eft's interpolating combiner: the effect pixel program isn't read yet). The body
  shaders' `NU_colorSamplerUV` likewise as `s (uv + t)`.
- **Defaults**: Markers off, Labels off, HQ on. An `Sm4shCommand.ini` from an older version is reset to these three
  **once** (the `ViewerDefaults163` entry records it); what you choose after that is kept.
- **Arc / streak / beam colours and sides (open; found and fixed in v1.7.1, see "Common effects against the game's bank").** Dr. Mario's forward air plays one effect, the common arc
  `0x1000090` (`EFFECT_FOLLOW_FLIP` on bone 0, (-3, 5.5, 1), turned (-24, -11, -60), size 0.95), with no colour command
  and no trail command (`Sword_Glow` has no colour fields: a trail's colour is its two textures and shader), so its
  light yellow is the common bank's own (the arc's emitter colour keys / combiner, or its effect model's vertex
  colours, colour gain and combiner colours). Pac-Man's jab streak (`0x100008D`), Link's air grab beam (`0x10000A5`, at
  rate 4) are common effects too. The game's common bank (`data/effect/common`) wasn't among the files sent, so these
  three weren't drawn here; the viewer's billboards, polygons and directional particles were checked against Smash 4's
  own vertex programs run on real emitters (tools/latte_exec.py: the same corners, U toward the screen's right, V
  down / back along the velocity), and stripes, untextured blocks and missing-alpha blocks (the likely causes of the
  bars and blocks) are fixed above.
- **Tested** (`effect_viewer_test.py --pacman DIR --mariod DIR --link DIR`, the folders read where they are; 113
  checks, 0 failures; without the folders the 22 real-file checks are skipped): Pac-Man in Wait (body only), finalstart
  (pellets), forward smash frames 20 / 40 (Blinky on, then off), neutral air (the 2D Pac-Man through the CALLed
  subroutine, on the slowed timeline), the up taunt (one sign); the menu's defaults written to and read back from a
  VisUser.txt, a mesh hidden by default still shown by its group, and taken out again; forward smash's ghost bones
  animated by `pacmanpt1.pac` only; the ghost sprite facing the camera both facings; FinPacman's original-format
  textures (16 x 16, pupils blue); all 184 emitters of the three fighters' banks textured and none reading alpha from
  a texture without it; Dr. Mario's Cyclone ring and forward-air script; the effect UV formula; Link's up special
  stripes as ribbons both facings, mirrored. `new_var_test` 186 / 0 and `hitbox_var_test` 169 / 0 unchanged.

## Common effects against the game's bank (v1.7.1)

Checked with the game's own **vanilla** common bank (`data/effect/common`: `common.010d0000.efc` / `.ptcl`, `model/`,
`trail/`, sent by the user; game files, not in this repository) and the user's Pac-Man, Dr. Mario and Link folders.
**The viewer draws whatever common bank is in your game folder** (found above the fighter's folder, or the one picked
with **Common effects..**): if you have modded your common effects, the viewer shows yours, not the vanilla ones these
notes describe. Each fix below was read off Smash 4's own vertex programs (`tools/fx_render.py` `draw_s4`, the game's
`cross_f.rpx` shaders run on the real emitters) or its code:

- **Fighter colours for the common attack effects.** The common arcs and streaks are white in the bank; the game
  colours them per fighter. Every fighter's EffectModule holds a table (fighter_param_etc g14: common 0x8D, 0x92, 0x8E,
  0x90) with the fighter's own r, g, b for each (fighter_param words 0x13C-0x147, labelled "motion_blend" before), and a
  request for one of those ids gets it as the effect's colour (the call `LAST_EFFECT_SET_COLOR` makes; a colour command
  after it replaces it). Dr. Mario / Mario / Luigi / Sonic: 0x90 (3, 0.7, 0.25), Dr. Mario's forward-air arc's
  orange-yellow (white where it's brightest); Pac-Man 0x8D (2, 0.65, 0.55); Fox / Lucario blue, Samus / Ness green;
  Link, Marth and others white (docs/native-notes.md "Fighter colours for the common attack effects"). The viewer
  reads the game folder's `data/param/fighter/fighter_param.bin` when it finds one above the fighter's folder (your
  edited colours), else the vanilla values. A colour call's colour now multiplies colour 1 too (eft's own rule: the
  arcs' edges kept their colour 1 before).
- **Dr. Mario's forward-air arc in front of him** (both facings). The arc's sheets are directional polygons (particle
  type 4) given a tiny motion on purpose (1e-6 along the emitter's Y, 1e-8 along -Z); the game's program aims them by
  it however small, which turns them 180 degrees about Y. The viewer took them as at rest (under 1e-4) and drew the arc
  mirrored behind him.
- **rotBasis** (the emitter's 0x4C4): the game draws a particle's quad off its centre by this fraction of its size.
  Pac-Man's streak lines (`PtcCommonAttackLine`, 0x100008D) lie ahead of his fist, not centred on it.
- **Texture wraps** (each texture's sampler: mirror, repeat or clamp per axis). A 2 x 2 repeat in eft mirrors a
  quarter texture into a whole one; the viewer repeated it, so the streak's head glow (and others) came out as four
  bright corners, a square. Mirrored and clamped edges no longer blend with the texture's far edge (the Genesis beam's
  long quads drew a thin line along each edge).
- **Colour 1 with a texture's own alpha**: an emitter whose texture has its own alpha (combiner 2 with an RGBA texture)
  lost its colour 1 (black): the soccer-ball puffs (0x1000072) in Pac-Man's neutral air were sooty black, tan in the game.
- **XZ plates** (particle type 2): laid with their Y along the emitter's -Z, not +Z (the game's programs on the bomb
  rings and the Genesis beam's head meshes: they trail their particle along the beam).
- **Box volumes** (type 10): particles on the box's faces (`0x04A503C4`), not a sphere (Pac-Man's streak lines).
- Checked and left: hit sparks 0x1000001 / 0x1000002, landing smoke 0x1000006 / 0x1000007, dash smoke 0x1000009 and the
  fire puff 0x1000011 sit, move and grow as the game's programs draw them. The game lights its smoke (a stage light
  colour the programs read and the viewer doesn't have): the viewer's dust is the emitters' own cream / white.
  Stripes (types 5 / 6: the Genesis beam's lightning) aren't run through the game's programs here: unverified.
- **Tested** (`effect_viewer_test.py ... --common DIR`: the bank linked where the game keeps it, read in place; 131
  checks, 0 failures; without it, the stand-in bank as before, 113): the bank's entries (13 ids, against tools/efc.py +
  ptcl.py), the colour table (Dr. Mario, Pac-Man, Link; a fighter_param.bin in a game folder read instead), Dr. Mario's
  arc and Pac-Man's streak on the fighter's front in both facings, the wraps, rotBasis, the box volume, the beam's
  plates, and every emitter of the common bank textured with no blocks.

## Every script, effect models, UV animation, script files (v1.7.2)

- **Every script of the move runs.** The game runs all four ACMD scripts of a motion every frame (game, effect, sound,
  expression, in that order) and any command works in any of them; the viewer now does the same
  (`HitboxRunner.Others`): one timeline, each script with **its own frame cursor** (FRAME / WAIT timers, Set_Loop,
  True / Else blocks, CALL / JUMP into its own file, Thread_Start), all on the motion's rate (Set_Frame_Duration /
  Frame_Speed_Multiplier / the rate variable from whichever script sets it, from its next frame). Hitboxes, body states
  (intangible / invincible / armour), effects, trails, overlays and visibility commands from any script are the move's;
  the lists say which script a hitbox / effect came from when it isn't the usual one (`Hitbox (expression script)`).
  Up to v1.7.1 hitboxes came from the game script only and effects from the effect script only (a game script's effects
  were dropped when the move had an effect script; the sound script never ran). Vanilla cases: Pac-Man's 0xE8410CDF
  (FitPacmanBodyMainD03SpecialLwFailure) has its two hitboxes only in its expression script and 0x2BB1E8A1 its
  Special_Hitbox and its Set_Frame_Duration(7) in its effect script; Link's 0x1DDF4AA6 (EscapeAir) an effect in its game
  script. Sound commands (Sound_Effect, Stop_Sound_Effect, ...) aren't listed as effects. The sound script is followed as
  you type, like the other three (its tab's editor).
- **Effect models' single-bound parts in their bone's space.** An effect model's mesh bound to one bone (no weights)
  has its vertices in that bone's own space, placed by the bone's world matrix alone: EffCommonCrossBomb's fire meshes
  on a bone 250 units up have their vertices from -253 to -44 (the column from the ground to its flares' top at 206),
  Link's boomerang tornado's wind rings on bones 3-9 up sit at 0-12 in theirs. v1.7.1 skinned them as a fighter's
  (world x inverse bind: right for a fighter's face meshes, which are in model space), which takes the bone's bind
  transform off again: every such part was drawn that far off, a flame pillar under the stage (the user's Link up
  special) while its particles and hitboxes were in place. Rigged parts are skinned as before.
- **Particles' UV animation** (each texture slot's scroll / scale / turn, per frame, initial and random: the emitter's
  0x514-0x54C for slot 0, 0x590-0x5C8 for slot 1, the inverse-random flips 0x4DA / 0x4DB), worked out as the game's
  vertex programs do (`tools/eft_vertex.py` `uv1_lines`, fitted against them within 2e-5): a quad's corner turned about
  the texture's centre, scaled, minus the shift. The common flash (0x100001C, PtcCommonFlash; Link's air up special's
  start, many others) has a ring of a quarter texture mirrored 2 x 2 and shifted by one along V: v1.7.1 ignored the
  shift and drew four arcs bowing in round the star; it's a ring now, as the game's programs draw it (gold ring, white
  to blue star). The particles' randoms come from a generator of their own: their paths are unchanged. Approximated: the
  vertex programs aren't read, so a slot's animation is drawn whenever its values aren't the still ones; which random
  flips a particle's U / V (inverse random) is a guess.
- **Add Script File / Remove Script File** (fighter mode: a fighter's or an article's animcmd folder opened with File >
  Open > Fighter..). Right-click a motion in the tree, or the script tabs of its open tab: **Add Script File** lists the
  files that have no script for it (game, effect, sound, expression; "new KIND.bin" when the folder has no such file)
  and gives it an empty one (Script_End) under the motion's hash (the CRC32 of its lower-case name, as every script is
  keyed), opened in its own tab to edit at once; **Remove Script File** takes one out (asked first). Save writes it: an
  existing file keeps its other scripts byte for byte; a missing file is made, an ACMD file in the endianness of the
  folder's other files (big for Wii U, little for 3DS), that the game and Sm4shCommand read. The Hitbox Viewer plays the
  new script with the others (from the open files, before saving too). (Add Script.. still adds a new motion to all
  four files at once.) Saving works under Mono too now (SALT wrote through kernel32 and mapped a temp file past its end).
- **Tested** (Mono; build next to the exe, see each file's head):
  - `viewer_scripts_test.cs` (`xvfb-run mono VsTest.exe Events.cfg link pacman mariod --common DIR`): 45 checks, 0
    failures. Synthetic four-script moves (a hitbox and a body state in the effect / sound scripts, a Set_Loop in the
    sound script on its own WAIT cursor, an If / Else in the expression script both ways, a Set_Frame_Duration in the
    effect script slowing every script, no game script); every script of Link (380), Pac-Man (366) and Dr. Mario (325)
    run the v1.7.1 way and the v1.7.2 way: the game script's hitboxes / body states and the effect script's effects the
    same (no effect twice), apart from the 5 Pac-Man motions whose rate another script sets (their timeline is now the
    game's); Pac-Man's and Link's cross-script moves above; the UV formula; EffCommonCrossBomb's parts above ground.
  - `script_files_test.cs` (`mono SfTest.exe Events.cfg BODY_DIR WORK`, on Link's and Pac-Man's folders): 25 checks, 0
    failures. An effect script added to a motion with only a game script, edited, played by the viewer's scripts,
    saved: one more script, the others byte-identical, the other files untouched; reopened, removed, saved: effect.bin
    byte-identical to the original; sound.bin made from nothing (header, one script, size); an article folder with only
    a game.bin given the three others; a little-endian folder's new file little-endian.
  - Rendered (the user's Link, the vanilla common bank): Link's air up special frames 4-8 (the flash a ring), the
    CrossBomb fire column on his up special (v1.7.1 under the stage, v1.7.2 above it), Pac-Man's SpecialLwFailure
    (hitboxes from its expression script). `hitbox_var_test.cs` 184 / 0; `new_var_test.cs` 200 / 1, the one failure
    the same as v1.7.1's (its effect.bin else-if count is Kirby's).

## Events.cfg format

One block per command, blocks separated by a blank line; lines starting with `//` are comments:

```
B738EABD                     identifier (hex CRC32 of the command)
Hitbox                       name
0,0,0,1,...                  parameter types: 0 int, 1 float, 2 decimal, 3 variable (or NONE)
ID,Part,Bone,Damage,...      parameter names (or NONE)
Defines a hitbox ...         description, shown in tooltips (optional; NONE = none)
Category: Hitboxes           optional, the command's group in View > Commands
Param: KBG = Knockback growth   optional, one per parameter, shown when hovering that parameter
Example: Hitbox(ID=0, ...)   optional, one per line of a usage example (View > Commands);
                             the indentation after "Example: " is kept, "//" lines are comments
Help: text                   optional, one per line of help shown in View > Commands after the
                             parameters (not in tooltips); "Help:" alone is an empty line,
                             "Help: ## text" a heading, "Help: - text" a list line
```

A group's own help (shown when the group is picked in View > Commands) is a block of its own:

```
Group: New Commands / Inputs
Help: A fighter's controller: ...
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
- v1.4.10 (Mono, the same `new_var_test.cs`, counts updated): Events.cfg loads with no errors (620 commands, 36 with help); Gravity_Set's 4 examples (its `GRAVITY` alias included) compile and round-trip; everything below still passes (134 checks, 0 failures).
- v1.4.9 (Mono, `new_var_test.cs`): Events.cfg loads with no errors (619 commands, 9 group help blocks, 35 commands with
  help); New_Var's bytes, text and round trip; defaults, positional and numeric forms, a name used above its
  declaration and in another script, explicit / auto slots, all 64 slots, the errors (unknown name, an alias's or a
  command's name, too long, bad type / slot); aliases off (hex, compiles back); a preview compile (the Hitbox Viewer following the editor) leaves no half-typed names behind; names coming back from a saved file
  in a new session; Kirby's game / sound / expression scripts (1,651) still decompile and compile to the same bytes
  (effect.bin: the same 5 else-if chains as before); every new command's examples compile and round-trip. Under
  Xvfb (`new_var_gui_test.cs`, also referencing SM4SHCommand.exe and System.Windows.Forms / System.Drawing; `xvfb-run
  mono GuiTest.exe Events.cfg`): View > Commands' New_Var page (5 parameters, the declared names, the template) and
  the hover on a name. 130 + 9 checks, 0 failures. Build and run: `dotnet .../csc.dll -out:NvTest.exe -r:SALT.dll -r:/usr/lib/mono/4.5/mscorlib.dll
  -r:/usr/lib/mono/4.5/System.dll -r:/usr/lib/mono/4.5/System.Core.dll -nostdlib new_var_test.cs`, then
  `mono NvTest.exe Events.cfg Aliases FIGHTER/script/animcmd/body TMP_DIR` next to the built SALT.dll.
- v1.4.8 (Mono): Events.cfg loads with no errors (618 commands, 8 group help blocks, 34 commands with help); every
  new command's examples compile (names such as `VAR_0` / `SELF_DAMAGE` included) and come back the same after
  decompiling and compiling again; `SaveInfo` (Tools > Command Definitions' Save) writes the help, groups and
  examples back unchanged; View > Commands (Xvfb) shows New Commands first with its subgroups, the group
  overview and each command's help and examples.
- View > Commands (Mono under Xvfb): all 584 commands load in 20 groups, search and the parameter view
  work; Insert (Wine) adds the line under the caret with its indent, selects the first value, one undo.
- Tooltips (Wine): the old build left a tooltip over the next tab and over another window; now it's
  hidden on both, and still shown on hover.
- Hitbox Viewer textures: Mario's and Kirby's model.nut (BC1, BC3, RGBA8, GX2 2D-tiled) decode to their
  textures; LASTHIT_HITSTUN_MUL 1.5 typed into Kirby's AttackS4 gives 40 frames of hitstun instead of 27.
- Hitbox Viewer (Wine): Kirby's AttackS4 on his model and animation, hitboxes on frames 13-15 on the
  leg, following edits as typed; the calculator's result for it (16%, 361, KBG 102, BKB 30 on Mario at
  0%: 70.46 knockback, 27 hitstun) matches Sm4sh-Calculator.

Hitbox Viewer credits (MIT): the script timing, bone IDs and hitbox placement follow Smash Forge's
`ACMDScript.cs` and the model / texture reading (NUD materials, NUT, the GX2 deswizzle from `GTX.cs`, itself
from AboodXD's GTX Extractor) follow Smash Forge (https://github.com/jam1garner/Smash-Forge); the knockback / hitstun formulas and the
fighters' attributes (`Viewer/Fighters.txt`) are from Sm4sh-Calculator by rubendal
(https://github.com/rubendal/Sm4sh-Calculator).

`make_events_cfg.py` regenerates `Events.cfg` from SALT's table; `make_anim_names.py` regenerates
`AnimNames.txt` (this drops names added by Parse Animations / Set Name).
