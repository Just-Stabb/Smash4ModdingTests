# MSC-C Guide (Smash 4 Wii U)

How to read and write character MSC code as C, using Jam1Garner's tools:

- **mscdec** (decompiler, `.mscsb` -> `.c`): https://github.com/jam1garner/mscdec
- **msclang** (compiler, `.c` -> `.mscsb`): https://github.com/jam1garner/msclang

The IDs and meanings below come from the community MSC Note Sheet, copied into
[`reference/msc-note-sheet/`](../reference/msc-note-sheet/). The sheet writes
everything in assembly form (`pushInt` / `sys` / `callFunc`). This guide shows
how to write the same thing in MSC-C.

## 1. Workflow

```sh
./tools/setup_toolchain.sh                         # once: clones mscdec + msclang, installs pycparser
python3 tools/mscdec/mscdec.py -x tools/mscinfo.xml fighter.mscsb -o fighter.c
# ...edit fighter.c...
python3 tools/msclang/msclang.py -x tools/mscinfo.xml fighter.c -o fighter.mscsb
```

`tools/mscinfo.xml` gives syscalls readable names (`WorkModule(...)` instead of
`sys_16(...)`). Pass `-x tools/mscinfo.xml` to **both** tools. Without it, the
compiler rejects a file that uses the names ("function StatusModule does not
exist"). Syscalls with no name stay as `sys_XX`.

Rules for editing decompiled files:

- **Add new functions at the end of the file.** Scripts are numbered by their
  position (`func_0`, `func_1`, ...). Putting a function in the middle shifts
  the numbers of every script after it.
- **Add new globals after the last existing `globalN` declaration.** A global's
  ID is its position in the declarations, so never reorder or delete them.
- Globals can't have a starting value. Set them inside a function.
- Don't use `-a` (autocast) on decompiled files. It's for code you wrote yourself.

## 2. The language in brief

- Types: `int`, `float`, `bool` (stored as an int). There are no structs,
  arrays or memory pointers.
- String literals can only be passed to `printf`.
- Function pointers live in an `int`: `int f = func_12; (*f)();`
- Control flow: `if`/`else`, `for`, `while`, `do`/`while`, `?:`. A `switch`
  has to test a plain variable.
- Built-ins:
  - `printf(fmt, ...)`
  - `set_main(funcPtr, args...)` replaces the main loop
  - `callFunc3(funcPtr, args...)`
  - `sys_XX(args...)`, where XX is the syscall number in hex
- Constants: `true`, `false`, `NULL`, `NULL_FUNC_PTR` (0xFFFFFFFF),
  `M_PI`, `M_PI_2`, `M_SQRT2`, ...
- **Write floats as float literals (`1.0f`, `-0.5f`).** The sheet shows floats
  as raw bits, e.g. `pushInt. 0x3f800000` is `1.0f` and `0xbf800000` is `-1.0f`.
  An int literal is passed as an int, not converted.
- **Don't pass a call to a function that itself calls functions as an argument of another
  script function** (`func_22(f(x), 0, 1.0f)` where `f` calls other functions). It compiled to
  normal-looking bytecode but broke Kirby's aerials in game (user); store the result in a local
  first. One-line `return` functions (`func_22(strike_nair_motion(), …)`) and syscall arguments
  are fine.
## 3. Translating the sheet's assembly into MSC-C

Arguments are pushed in order, then `sys N, M` calls syscall `M` with `N` args:

```
pushInt. 0x7
pushInt. 0x1
pushInt. 0x10000001
sys 0x3, 0x16
```
```c
sys_16(0x7, 0x1, 0x10000001);   // WorkModule: set int var 0x10000001 (jumps used) = 1
```

A function call is `pushInt. script_N` followed by `callFunc <argc>`:

```
pushInt. 0x10
pushInt. 0x0
pushInt. script_16
callFunc 0x2
```
```c
func_16(0x10, 0);               // change action to SpecialFall
```

**Naming differences** between the sheet and mscdec:

| Sheet / pymsc | mscdec / MSC-C |
|---|---|
| `script_16` | `func_16` (same index, decimal) |
| `GlobalVar26` / `pushVar. 0x1, 0x26` (hex) | `global38` (decimal) |
| `pushVar. 0x0, 0x3` (local variable) | `var3` / `argN` |

### Syscall names (`tools/mscinfo.xml`)

| Name | sys | Name | sys | Name | sys |
|---|---|---|---|---|---|
| `sv_get_mem` | 2 | `StatusModule` | 18 | `StopModule` | 30 |
| `sv_set_mem` | 3 | `GroundModule` / `F` | 1A / 1B | `BattleObjectParamFloat` | 34 |
| `randi` | 9 | `EffectModule` / `F` | 1C / 1D | `ShieldModule` | 36 |
| `MathF` | A | `SoundModule` | 1E | `TurnModule` | 37 |
| `FighterUtil` | C | `ArticleModule` | 20 | `VisibilityModule` | 39 |
| `CameraModule` | D | `BattleObject` | 21 | `CatchModule` | 3B |
| `ControlModule` / `F` | E / F | `CancelModule` | 23 | `CaptureModule` / `F` | 3C / 3D |
| `KineticModule` / `F` | 10 / 11 | `DamageModule` / `F` | 24 / 25 | `ItemModule` / `F` | 3E / 3F |
| `MotionModule` / `F` | 12 / 13 | `ComboModule` | 26 | `ColorBlendModule` | 42 |
| `PostureModule` / `F` | 14 / 15 | `ModelModule` / `F` | 27 / 28 | `PhysicsModule` | 44 |
| `WorkModule` | 16 | `AreaModule` | 29 | `BattleObjectF` | 45 |
| `WorkModuleF` | 17 | `LinkModule` / `F` | 2A / 2B | `AudienceManager` | 46 |
| | | `StageData` | 2C | `JostleModule` | 47 |
| `SlopeModule` | 19 | `HitModule` | 2D | `ShakeModule` | 48 |
| | | `AttackModule` / `F` | 2E / 2F | `SlowModule` / `F` | 49 / 4C |
| `SearchModule` | 31 | | | `ShadowModule` | 4A |
| | | | | `MotionAnimcmdModule` | 4B |

The `F` versions return floats. Everything in this guide written as `sys_XX`
works with either spelling. For example, `sys_16(0x7, 1, v)` is the same call as
`WorkModule(0x7, 1, v)`, and `sv_set_mem(0x1, key, action, func)` is
`sys_3(...)`.

## 4. Fighter globals (GlobalVars tab)

| Hex | MSC-C | Meaning |
|---|---|---|
| 0x1 | `global1` | Character ID |
| 0x4 | `global4` | Current action |
| 0x5 | `global5` | Previous action |
| 0x6 | `global6` | Next action (useful in Key 2 scripts) |
| 0x9 | `global9` | Action timer (float) |
| 0x10 | `global16` | Extra per-frame script (function pointer, 0 = none) |
| 0x12 | `global18` | Situation: 0 ground, 1 cliff, 2 air, 3 water, 5 dead, 6 ladder |
| 0x13 | `global19` | Situation on the previous frame |
| 0x14 | `global20` | Animation frame (float) |
| 0x18 | `global24` | Command inputs, category 1 (bitfield, see below) |
| 0x1F | `global31` | Command inputs, category 2 |
| 0x1D | `global29` | Command inputs, category 3 (item throws) |
| 0x20 | `global32` | Stick Y (float) |
| 0x26 | `global38` | Button triggers/releases (bitfield) |
| 0x2D | `global45` | Command inputs, category 4 (Ryu commands) |
| 0x30 | `global48` | Stick X (float) |
| 0x32 | `global50` | Fastfall frames (float) |

Input bitmasks (Inputs2 tab):

```c
// global38 (0x26)
// 0x1 A pressed       0x2 A released
// 0x4 B pressed       0x8 B released
// 0x10 jump pressed   0x20 jump released
// 0x40 shield pressed 0x80 shield released
if (global38 & 0x4) { /* B was just pressed */ }

// global24 (0x18), CAT1
// 0x1 jab   0x2 ftilt   0x4 utilt   0x8 dtilt
// 0x10 fsmash   0x20 usmash   0x40 dsmash
// 0x80 nair   0x100 fair   0x200 bair   0x400 uair   0x800 dair
// 0x1000 neutral-B   0x2000 side-B   0x4000 up-B   0x8000 down-B
// 0x100000 jump (stick)   0x200000 jump (button)   0x400000 air dodge
// 0x1000000 spot dodge    0x20000000 grab
if (global24 & 0x4000) { /* up-B input */ }
```

## 5. Work variables (`sys_16` / `sys_17`)

Variable IDs have the form `0xXYZZZZZZ`:

- **X (type):** 0 float, 1 int, 2 flag
- **Y (group):**
  - 0 instance work (stays set across actions)
  - 1 status work (resets on action change)
  - 2 `fighter_param_common`
  - 3 `fighter_param`
  - 5–8 `fighter_param_vl` special-move params

See `Variables.csv` for the known IDs.

| Operation | MSC-C |
|---|---|
| Get int / flag value | `sys_16(0x6, var)` |
| Get float | `sys_17(0x0, var)` |
| Set float | `sys_16(0x0, 1.5f, var)` |
| Random float in [min, max] | `sys_16(0x1, min, max, var)` |
| Add / sub / mul / div float | `sys_16(0x2 / 0x3 / 0x4 / 0x5, value, var)` |
| Set int | `sys_16(0x7, value, var)` |
| Random int in [a, b) | `sys_16(0x8, a, b, var)` |
| Increment / decrement int | `sys_16(0x9, var)` / `sys_16(0xA, var)` |
| Add / sub / mul / div int | `sys_16(0xB / 0xC / 0xD / 0xE, value, var)` |
| Is flag set? | `sys_16(0x10, var)` |
| Flag on / off | `sys_16(0x11, var)` / `sys_16(0x12, var)` |
| Set flag to bool | `sys_16(0x13, b, var)` |
| Test then clear flag | `sys_16(0x14, var)` |
| Is status transition on? | `sys_16(0x15, 0x1E......)` |
| Status transition on / off | `sys_16(0x16, id)` / `sys_16(0x17, id)` |
| Status transition group on / off | `sys_16(0x19, 0x1F......)` / `sys_16(0x1A, id)` |

Examples:

```c
int jumps = sys_16(0x6, 0x10000001);       // jumps used
sys_16(0x7, 0x0, 0x10000001);              // refresh jumps
float f = sys_17(0x0, 0x01000006);        // read a float var
if (sys_16(0x10, 0x21000001)) { }          // fastfall flag set?
sys_16(0x11, 0x20000003);                  // turn on RCO landing lag
```

## 6. Common scripts (Cmn Scripts tab)

| Call | Effect |
|---|---|
| `func_16(actionId, 0)` | Change action (`func_17` skips checks) |
| `func_20(state)` | Set situation: 0 ground, 1 ledge, 2 air |
| `func_22(acmdId, startFrame, speed)` | Change subaction (animation + ACMD), e.g. `func_22(0x105, 0.0f, 1.0f)` |
| `func_23(acmdId)` | Change subaction and keep the current animation frame |
| `func_30(n)` | Returns 1 with a 1-in-n chance |
| `func_33()` | Reverse direction |
| `func_100(mode)` | Ledge grab: 0 none, 1 snap while facing, 2 snap, 3 falling + facing, 4 falling |
| `func_550()` | Allow fastfall |
| `func_12(x)` / `func_13(x)` / `func_14(x)` | abs int / abs float / sign of a float |

Useful action IDs (Actions tab):

| ID | Action |
|---|---|
| 0x0 | Wait |
| 0xA | Jumpsquat |
| 0xB | JumpF/JumpB |
| 0xC | JumpAerial |
| 0xE | Fall |
| 0x10 | SpecialFall |
| 0x16 | LandingHeavy |
| 0x17 | LandingLight |
| 0x22 | EscapeAir |

## 7. Syscalls by module (Syscalls + Complex CMDs tabs)

The first argument is usually the module's sub-command (opcode).

| Syscall | Module | Handy calls |
|---|---|---|
| `sys_9(a, b)` | Random | Random int in [a, b) |
| `sys_A` | Math (float) | `sys_A(0x0, x)` sqrt, `sys_A(0x1, y, x)` atan2, `sys_A(0x4, x)` cos, `sys_A(0x5, x)` sin, `sys_A(0x6)` random 0–1 |
| `sys_C` | FighterUtil | `sys_C(0x1E)` jab subaction, `sys_C(0x1F)` ftilt subaction |
| `sys_D` | Camera | `sys_D(0x3, intensity)` quake, `sys_D(0x2, 0/1)` focus |
| `sys_E` | Control | `sys_E(0x2710, btn)` pressed, `sys_E(0x2712, btn)` held, `sys_E(0x2713, btn)` not held |
| `sys_F` | Control (float) | `sys_F(0x0)` stick X, `sys_F(0x1)` stick Y, `sys_F(0x4)` stick angle |
| `sys_10` | Kinetic | see below |
| `sys_11` | Kinetic (float) | Get speed |
| `sys_12` | Motion | `sys_12(0x4, speed)` anim speed, `sys_12(0x2712)` anim ended?, `sys_12(0x2713, frame)` set frame |
| `sys_13` | Motion (float) | `sys_13(0x1)` current anim frame, `sys_13(0x9)` frame speed |
| `sys_14` | Posture | `sys_14(0x0, 1.0f / -1.0f)` set facing direction |
| `sys_16` / `sys_17` | Work | see section 5 |
| `sys_18` | Status | `sys_18(0x0)` status kind, `sys_18(0x1)` situation |
| `sys_33(0x0, id)` / `sys_34(0x0, id)` | battle_object params | int / float |

Button IDs for `sys_E`: 0 attack, 1 special, 2 jump, 3 shield, 4 smash
(A+B / C-stick), 9 grab (Z).

Kinetic (`sys_10`):

```c
sys_10(0x0, 0xA);           // set kinetic type: AIR_STOP (Kinetic Types tab)
sys_10(0xf, 0x1, 0.0f);     // set gravity (0.0f disables it)
sys_10(0x11, 0x1, 2.5f);    // set vertical air velocity
sys_10(0x11, 0x2, 1.0f);    // set horizontal air velocity
sys_10(0x14, 0x1, 3.0f);    // set max fall speed
sys_10(0xd, h, v);          // set launch speed
```

## 8. How action scripts run (Other tab)

Each action registers scripts under "keys" (`sys_3(0x1, key, actionId, funcPtr)`):

- **0 -> 3 -> 1:** run once when the action starts
- **4 / 7:** every frame, outside hitlag
- **5:** every frame, during hitlag
- **8:** every frame, both
- **2 / 6:** when the action changes or ends

`global16` (0x10) holds an extra per-frame function pointer. Action scripts
often set it to a small function that checks for cancels.

## 9. Pattern: allow up-B to cancel an action on frame 10+

```c
void myCancelCheck()
{
    if (global20 >= 10.0f && (global24 & 0x4000))   // anim frame >= 10, up-B input
    {
        func_16(SPECIAL_HI_ACTION, 0);               // change action
    }
}

// inside the action's key-0/key-1 setup script:
global16 = myCancelCheck;
```

`SPECIAL_HI_ACTION` is a placeholder: replace it with the fighter's SpecialHi
action ID, from the decompiled file or the Actions tab.
