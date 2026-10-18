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

## Examples

ACMD: grab-style "pull the opponent in front of me" on frame 10:

    Synchronous_Timer(Frames=10)
    SET_FLOAT(Value=12, Variable=0x0F00000C)
    SET_FLOAT(Value=0, Variable=0x0F00000D)

ACMD: only do something when the opponent is within 20 units. The method numbers are assumed to
follow Int_Var_Compare's description: 0 `==`, 1 `!=`, 2 `<=`, 3 `>=`, 4 `<`, 5 `>`. That order is
unconfirmed, so check it in game:

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
