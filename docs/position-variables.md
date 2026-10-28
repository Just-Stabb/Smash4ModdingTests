# Common position variables

Every fighter can read and move its own position, the nearest opponent's, and any player slot's,
through ordinary WorkModule float variables. They work from ACMD (`SET_FLOAT`, `Float_Var_Compare`)
and MSC (`WorkModuleF(0, id)` to read, `WorkModule(op, value, id)` to write). Nothing is stored:
each read looks the position up, and each write moves the fighter through the game's own
`set_pos`.

Needs the executable patch `tools/position_vars_cave.py` (in the standard `build/cross_f.rpx`).
Sm4shCommand shows each ID's name and description when you hover it (`Tooltips/position_variables.txt`).

Terms used below:

- **Self** is the fighter running the script.
- **Opponent** is the nearest other fighter, by X/Y distance. Teams aren't considered.
- **Fwd** means X measured along self's facing, so positive is in front of self. This lets one
  script work facing either way.
- **Slots** are player slots 1–8, which are the game's fighter table entries 0–7.

| ID | Read | Write |
|---|---|---|
| `0x0F000000` | self X | set self X |
| `0x0F000001` | self Y | set self Y |
| `0x0F000002` | self Z | set self Z |
| `0x0F000003` | self facing (1 right, -1 left) | ignored |
| `0x0F000004` | 0 | move self forward by value (fwd) |
| `0x0F000005` | 0 | move self up by value |
| `0x0F000006` | 0 | move self along Z by value |
| `0x0F000008` | opponent X | set opponent X |
| `0x0F000009` | opponent Y | set opponent Y |
| `0x0F00000A` | opponent Z | set opponent Z |
| `0x0F00000B` | distance to opponent (X/Y) | ignored |
| `0x0F00000C` | opponent X − self X (fwd): positive = opponent in front | put the opponent `value` in front of self |
| `0x0F00000D` | opponent Y − self Y | put the opponent at self Y + value |
| `0x0F00000E` | opponent Z − self Z | put the opponent at self Z + value |
| `0x0F000010` | self X − opponent X (fwd) | put self at opponent X + value (fwd) |
| `0x0F000011` | self Y − opponent Y | put self at opponent Y + value |
| `0x0F000012` | self Z − opponent Z | put self at opponent Z + value |
| `0x0F000020 + 4×(slot−1) + n` | slot X / Y / Z / facing (n = 0–3) | set slot X / Y / Z |

Slot IDs:

- Slot 1: `0x0F000020`–`23`
- Slot 2: `24`–`27`
- …
- Slot 8: `3C`–`3F`

When the fighter doesn't exist (no opponent, an empty slot, or a non-fighter such as a projectile
using a "self" ID), reads give 0 and writes do nothing.

Adding to one of these works as you'd expect: it is a read, the change, then a write. In MSC that's
`WorkModule(2, value, id)`, and ops 3, 4 and 5 subtract, multiply and divide. For example,
`WorkModule(2, 5.0f, 0x0F000005)` moves up 5, and `WorkModule(2, 1.0f, 0x0F00000C)` moves the
opponent 1 unit further forward.

## Hitstun, hitstop and the last fighter hit

`0x0F000040 + 8 × target + quantity`, same rules (SET_FLOAT / Float_Var_Compare, MSC).

| target | IDs | |
|---|---|---|
| 0 self | `0x0F000040`–`47` | |
| 1 nearest opponent | `0x0F000048`–`4F` | |
| 2 last fighter hit | `0x0F000050`–`57` | the newest hit of self's current attack; once the attack is over, the fighter whose last attacker was self |
| 3–10 player slot 1–8 | `0x0F000058`–`97` | slot 1 `58`–`5F`, slot 2 `60`–`67`, … slot 8 `90`–`97` |

| quantity | read | write |
|---|---|---|
| +0 hitstun left | frames of hitstun left | set them (only matters while in a hit status) |
| +1 hitstun dealt | hitstun frames of the last hit taken | ignored |
| +2 hitstun × | 0 | multiply the hitstun left by the value. For the **last fighter hit** (`0x0F000052`) it is also remembered for the rest of the move: every hit of the move that lands afterwards gets that much hitstun (so it can go before the hit, e.g. right after the `Hitbox` lines); it's forgotten when the move ends |
| +3 hitstop (shake) | 1 while in hitstop, else 0 | hitstop for N frames, shaking like a hit |
| +4 hitstop (no shake) | hitstop frames of the last hit taken | hitstop for N frames, no shake |
| +5 offset X (fwd) | target X − self X, along self's facing | put the target that far in front of self |
| +6 offset Y | target Y − self Y | put the target at self Y + value |
| +7 offset Z | target Z − self Z | put the target at self Z + value |

Examples:

    SET_FLOAT(Value=8, Variable=0x0F000053)    // last fighter hit: 8 frames of hitstop, shaking
    SET_FLOAT(Value=0, Variable=0x0F000050)    // last fighter hit: end their hitstun now
    SET_FLOAT(Value=1.5, Variable=0x0F000052)  // this move's hits: 1.5x hitstun (before or after the hit)
    SET_FLOAT(Value=6, Variable=0x0F000044)    // self: 6 frames of hitstop, no shake
    SET_FLOAT(Value=12, Variable=0x0F000055)   // put the last fighter hit 12 in front of self

The work is done by the game's own MSC commands, run on the target: `WorkModule` int
`0x1000003E` (hitstun left), `DamageModuleF(1)` / `DamageModule(8)` (hitstun / hitstop of the
last hit), `StopModule(1)` / `StopModule(2, frames)` (in hitstop / set hitstop) and
`ShakeModule(0, 0, frames, 0, 0, 1.0)` (the shake). Player slot numbers and "last attacker" are
assumed to be the same numbering (player 1 = slot 1).

## Hit detection, status and motion

`0x0F0000A0 + 8 × target + quantity`, same targets as above (0 self, 1 nearest opponent, 2 last
fighter hit, 3–10 player slots 1–8), so `0x0F0000A0`–`0x0F0000F7`.

| quantity | read | write |
|---|---|---|
| +0 hit | 1 once its current attack has connected (stays 1 until the move ends or it's reset), else 0 | any value: back to 0 (`AttackModule(0x2724)`, as ACMD `Hit_Reset`), so a later hitbox can be checked on its own |
| +1 hit now | 1 only on the frame its attack connects | ignored |
| +2 status | its status kind | change its status (`StatusModule(3, status, 0)`), e.g. `0x59` shield break, `0x5D` dizzy |
| +3 motion | its motion kind | play that motion from frame 0 at rate 1 (`MotionModule(1, ...)`; motion numbers are per fighter) |
| +4 motion frame | its motion's current frame | ignored |
| +5 to +7 | 0 | ignored |

Use **`Float_Var_Compare`** to test them in ACMD (`Int_Var_Compare` reads ints, which these aren't):
`Method=0` is "equal". Example, Donkey Kong's side special: if it has hit someone by frame 20, a
second hitbox comes out and the fighter it hit goes into shield break (status `0x59` = 89):

    FRAME(Frames=20)
    Float_Var_Compare(Variable=SELF_HIT, Method=0, Value=1)
    True(Offset=0){
        Hitbox(ID=0, Part=0, Bone=0, Damage=8, Angle=361, KBG=100, WBKB=0, BKB=40, Size=5, X=0, Y=8, Z=8, Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=1, SFXType=1, Ground/Air=3, Direct/Indirect=1, Type=1)
        SET_FLOAT(Value=89, Variable=LASTHIT_STATUS)
    }
    WAIT(Frames=2)
    Remove_All_Hitboxes()

(Sm4shCommand works out `True`'s offset from the braces.) `SELF_HIT` = `0x0F0000A0`,
`LASTHIT_STATUS` = `0x0F0000B2`. Status numbers: `reference/msc-note-sheet/Actions_Fighters.csv`
(shield break: `0x59` launch, `0x5A` tumble, `0x5B` landing, `0x5C`–`0x5E` dizzy). A status
change takes effect on the fighter's next frame.

## Inputs and state

(ACMD also has commands for these: `Input_Compare`, `Input_Get`, `Input_Set`,
`docs/acmd-extra-commands.md`.)

`0x0F000100 + 0x20 × target + quantity`, same targets as above (0 self, 1 nearest opponent, 2 last
fighter hit, 3–10 player slots 1–8), so `0x0F000100`–`0x0F00025F`. Sm4shCommand names them
`TARGET_QUANTITY`, e.g. `SELF_ATTACK`, `OPP_INPUT_OFF`, `SLOT2_DAMAGE`. Test them with
**`Float_Var_Compare`** and set them with **`SET_FLOAT`**. To add, use **`SUB_FLOAT_2(Variable, SourceVariable)`** (Variable -= SourceVariable, through WorkModule's add: hooked) with a variable holding the negative step, e.g. `SET_FLOAT(-2, VAR_0)` then `SUB_FLOAT_2(0x0F000055, VAR_0)`. **`ADD_FLOAT` does nothing in this game:** its handler (`0x02BE6E80`) is `li r3, 0; blr`.

| quantity | read | write |
|---|---|---|
| +0 `ATTACK`, +1 `SPECIAL`, +2 `JUMP`, +3 `SHIELD`, +4 `GRAB`, +5 `TAUNT_UP`, +6 `TAUNT_SIDE`, +7 `TAUNT_DOWN` | 1 while that button is held | **1** hold it until **0** is written, **2** press it for one frame, **0** stop forcing it |
| +8 to +0xF: the same buttons `_PRESSED` | 1 only on the frame it's pressed | as above |
| +0x10 `STICK_X`, +0x11 `STICK_Y` | control stick, −1 to 1; X along the fighter's facing (positive = forward) | force the stick to the value until `STICK_FORCED` is written |
| +0x12 `CSTICK_X`, +0x13 `CSTICK_Y` | C-stick, the same way | force the C-stick |
| +0x14 `STICK_FORCED` | 1 while a stick is forced | any value: stop forcing both sticks |
| +0x15 `INPUT_OFF` | 1 while its own inputs are ignored | **1** ignore its buttons and sticks (forced ones still work), **0** back on |
| +0x16 `SITUATION` | 0 ground, 1 ledge, 2 air | set it (`StatusModule(2, value)`; the status itself doesn't change) |
| +0x17 `DAMAGE` | damage % | set it (the counter updates) |
| +0x18 `JUMPS_USED`, +0x19 `JUMPS_MAX` | jumps used / in all (ints `0x10000001` / `0x10000002`) | set them (`JUMPS_USED` 0 gives every jump back) |
| +0x1A `SHIELD_HP` | shield health (float `0x3`) | set it |
| +0x1B `INTANGIBLE` | body state: 0 normal, 1 invincible, 2–4 intangible (the stronger of the status's own and the timed one) | intangible for N frames (`HitModule(2, N)`) |
| +0x1C `INVINCIBLE` | 1 while invincible | invincible for N frames (`HitModule(1, N, 0)`) |
| +0x1D `ARMOR` | 0 none, 1 super armor, 2 knockback-based, 3 damage-based | set it (`DamageModule(0xB, type, threshold)`, threshold from `ARMOR_THRESHOLD`) |
| +0x1E `ARMOR_THRESHOLD` | the threshold (knockback for 2, damage for 3) | set it; write it before `ARMOR` |
| +0x1F `KO` | 0 | any value but 0: KO it at once (its work flag `0x20000043`, "Causes KO": it explodes as if KO'd; Hero's Whack / Thwack) |

Raw stick X, on screen whichever way the fighter faces (positive = right): `0x0F000260 + 2 × target`
(`STICK_X_RAW`) and `+1` (`CSTICK_X_RAW`), e.g. `SELF_STICK_X_RAW` = `0x0F000260`,
`OPP_CSTICK_X_RAW` = `0x0F000263`. The values are the game's own, −1 to 1 after its dead zone
(Y has no facing, so `STICK_Y` / `CSTICK_Y` are already raw). Writing one forces the stick like
`STICK_X` (the value is turned into "forward" with the fighter's facing at the time).

**Forced inputs** go in where the game reads the controller, so they act exactly like pressing the
button or tilting the stick: a forced press is "pressed this frame" on its first frame, a stick
forced from neutral to 1.0 counts as a smash input, and so on. They work on CPUs too. They last
until changed, and are all cleared when the fighter is KO'd, respawns, or is in the match's
entrance or results (so nothing carries into the next stock or match). Example: a move that makes
the fighter it hit jump and drop its shield, and can't be mashed out of for 30 frames:

    Float_Var_Compare(Variable=SELF_HIT_NOW, Method=0, Value=1)
    True(Offset=0){
        SET_FLOAT(Value=1, Variable=LASTHIT_INPUT_OFF)
        SET_FLOAT(Value=2, Variable=LASTHIT_JUMP)
    }
    WAIT(Frames=30)
    SET_FLOAT(Value=0, Variable=LASTHIT_INPUT_OFF)

Checking an input: `Float_Var_Compare(Variable=SELF_SPECIAL_PRESSED, Method=0, Value=1)`;
`Float_Var_Compare(Variable=SELF_STICK_Y, Method=5, Value=0.5)` for the stick up past halfway
(Methods: 0 `==`, 1 `!=`, 2 `<=`, 3 `>=`, 4 `<`, 5 `>`; the game's table at `0x10351804`).

## Animation rate

`0x0F000098`, self only.

| read | write |
|---|---|
| this fighter's animation rate multiplier (1.0 normally) | set it: every animation, and the ACMD timed to it, runs that many times faster until it's set back to 1.0 |

It's MotionModule's second rate (`+0xF4`), multiplied with each move's own rate
(`Set_Frame_Speed` / `Set_Frame_Duration` / MSC `MotionModule(0x4, …)`), so moves keep their own
speed changes on top. Mii Fighters' ACMD `MII_ENABLE_RATE` / `MII_UNABLE_RATE` set the same value.
Used by Kirby's Overdrive (`fighters/kirby/kirby.c`).

    SET_FLOAT(Value=1.2, Variable=0x0F000098)  // everything 1.2x faster
    SET_FLOAT(Value=1, Variable=0x0F000098)    // back to normal

## Item states

`0x0F000099` (`SELF_ITEM`), self only. Reads 0; writing a code puts one of the items' own states on
this fighter through the game's function for it (the one the item's pickup calls), with the item's
own durations:

| code | state | game function |
|---|---|---|
| 1 | metal on (Metal Box: the metal look, its physics and knockback resistance, flag `0x20000012`) | `0x02E15DE4(F, -1.0, 1, -1)` |
| 2 | metal off | `0x02E15DE4(F, -1.0, 0, -1)` |
| 3 | giant (Super Mushroom: its grow status `0xDD`) | `0x02E1E148(F, 1, 0)` |
| 4 | small (Poison Mushroom: `0xDE`) | `0x02E1E148(F, 1, 1)` |
| 5 | Super Star (invincible, flashing) | `0x02E16F4C(F, 1, -1, 0)` |
| 6 | Lip's Stick flower on its head | `0x02E1FB78(F, 1, 0, 0, 0.0, 0.0)` |
| 7 | the Timer's slow on every other fighter (half speed, 450 frames) | `0x02E16A14(F, 1, 2, 450, none)` each |
| 8 | the camera closes in on this fighter (ACMD `Camera_Closeup(3, 0, 2.0, 0, 0)`'s call) | CameraModule vt `+0xE4` |
| 9 | the camera back to normal (ACMD `Normal_Camera`'s call) | CameraModule vt `+0xEC(0)` |

F is the fighter object (its module accessor − 0x230). The mushroom refuses while flag `0x20000025`,
`0x20000037` or `0x2000001B` is set. Used by Hero's Kaclang (metal), Hocus Pocus and critical hits (8 / 9)
(`fighters/brave/brave.c`). Research: docs/native-notes.md "Item states".

    SET_FLOAT(Value=1, Variable=0x0F000099)    // metal

## Examples

ACMD: grab-style "pull the opponent in front of me" on frame 10:

    Synchronous_Timer(Frames=10)
    SET_FLOAT(Value=12, Variable=0x0F00000C)
    SET_FLOAT(Value=0, Variable=0x0F00000D)

ACMD: only do something when the opponent is within 20 units. The methods are 0 `==`, 1 `!=`,
2 `<=`, 3 `>=`, 4 `<`, 5 `>` (confirmed: the compare functions' table at `0x10351804`):

    if(Float_Var_Compare(Variable=0x0F00000B, Method=0x4, Value=20)){
        ...
    }

MSC: teleport 15 units behind the opponent, measured along self's facing:

    WorkModule(0, -15.0f, 0x0F000010);

MSC: read positions:

    var dx = WorkModuleF(0, 0x0F00000C);   // > 0: opponent in front
    var p2y = WorkModuleF(0, 0x0F000025);  // player 2's Y

## Notes

- A grounded fighter moved upward is still in a grounded status. The game's ground checks may snap
  it back or switch it to a fall on the next frame, the same as MSC's `PostureModule(3, ...)`.
- Native details: `docs/native-notes.md`, "Position variables".

## Names in Sm4shCommand

Sm4shCommand shows and accepts names for all of these (`tools/Sm4shCommand/SM4SHCommand/Aliases/variables.txt`):
`POS_SELF_X`, `POS_OPP_OFFSET_X`, `POS_SLOT3_Y`, ...; the combat and hit / status / motion
variables as `TARGET_QUANTITY` (`SELF` / `OPP` / `LASTHIT` / `SLOT1`-`SLOT8` + `HITSTUN`,
`HITSTUN_DEALT`, `HITSTUN_MUL`, `HITSTOP_SHAKE`, `HITSTOP`, `OFFSET_X`, `OFFSET_Y`, `OFFSET_Z`,
`HIT`, `HIT_NOW`, `STATUS`, `MOTION`, `MOTION_FRAME`), e.g. `LASTHIT_HITSTUN_MUL` = `0x0F000052`,
`OPP_STATUS` = `0x0F0000AA`; `SELF_ANIM_RATE` = `0x0F000098`; and `SELF_ITEM` = `0x0F000099`.

    SET_FLOAT(Value=1.5, Variable=LASTHIT_HITSTUN_MUL)
    SET_FLOAT(Value=12, Variable=POS_OPP_OFFSET_X)

