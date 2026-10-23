# New ACMD commands

These are new commands for game, effect, sound and expression scripts. They need the patched
`cross_f.rpx` (`tools/acmd_ext_cave.py`, part of the standard build). Without it, a script that uses
them won't load properly, so ship the executable with any script that uses them.

Sm4shCommand knows them, with tooltips for every parameter. View > Commands lists the Extra hitboxes
under Hitboxes and Track_Target under Traces & targeting.
`tools/acmd.py` reads and writes them too.

## Extra_Special_Hitbox / Extra_Extended_Special_Hitbox

- **Extra_Special_Hitbox** takes `Special_Hitbox`'s 41 parameters, then six more.
- **Extra_Extended_Special_Hitbox** takes `Extended_Special_Hitbox`'s 43 parameters (the capsule, with
  X2 / Y2 / Z2), then the same six.

The hitbox itself is made exactly as the original command makes it.

| Extra parameter | Type | Meaning |
|---|---|---|
| HitstunMul | float | Multiplies the hitstun this hit gives (knockback × 0.4). |
| HitstopMul | float | Multiplies the opponent's hitstop (hitlag), on top of the hitbox's own Hitlag multiplier. |
| HitstopFrames | int | The opponent's hitstop in frames, replacing the computed one. HitstopMul is then ignored. |
| SelfHitstopMul | float | Multiplies the attacker's own hitstop. |
| SelfHitstopFrames | int | The attacker's own hitstop in frames, replacing the computed one. |
| DIMul | float | Multiplies how far DI can turn this hit's launch angle: 0.5 is half the DI, 2 is double. |

- **Multipliers:** 0 or less means ×1 (unchanged), so a template with zeros behaves like
  `Special_Hitbox`. For no DI at all, use a tiny value such as 0.001.
- **Frames:** 0 means "computed". The frame values aren't capped at 30 like the computed hitstop is.
  For no hitstop, use the hitbox's DisableHitlag parameter.

Example: a 12% hit with half hitstun, a 20-frame freeze on the opponent, and no DI.

```
Extra_Special_Hitbox(ID=0, Part=0, Bone=0, Damage=12.0, Angle=361, KBG=100, FKB=0, BKB=40, Size=5.0,
    X=0.0, Y=8.0, Z=6.0, Effect=0, Trip=0.0, Hitlag=1.0, SDI=1.0, Clang=1, Rebound=1, ShieldDamage=0,
    SFXLevel=2, SFXType=1, Ground/Air=3, Direct/Indirect=1, Type=1, HitBits=63, Unk41=0, CollisionPart=15,
    NoScale=0, Shieldable=1, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0, HitAllStates=0,
    FacingRestrict=3, NoGrabRelease=0, TeamDamage=0, DisableHitlag=0, NoGFX=0, Flinchless=0, Shape=0,
    HitstunMul=0.5, HitstopMul=0.0, HitstopFrames=20, SelfHitstopMul=0.0, SelfHitstopFrames=0, DIMul=0.001)
```

(One line in a real script.)

### Notes

- **Stacking:** the extras stack with everything else: the per-move hitstun variable
  `0x0F000052`, Strike Kirby's hitstop, `Set_Frame_Duration` slowdowns and so on. Hitstop frame
  values are set after the game's slowdown rate, so they are exact.
- **Shared hitbox IDs:** a later plain hitbox command with the same ID replaces the hitbox and drops
  its extras, as you'd expect. `Change_Hitbox_Damage` / `Change_Hitbox_Size` keep them.
- **DI:** each fighter's own damage code reads the max DI angle (fighter_param `0x0200011A`), so
  DIMul scales that read for the fighter that was hit, until their next hit.
  - It doesn't touch LSI or SDI. SDI is already per hitbox: the SDI parameter.
  - **Not yet checked in game:** that every fighter's damage code reads the DI angle this way.
- **Projectiles and other articles** work too: their scripts use the same commands.

## Track_Target

`Track_Target(Frames, Speed, TurnRate, Range, Mode)` makes the object running the script home in on
the nearest other fighter. That object can be a fighter, or a projectile (in the projectile's own
script).

| Parameter | Type | Meaning |
|---|---|---|
| Frames | int | How long to track. -1 means until stopped: `Track_Target` with 0 frames, writing 0 to `TRACK_FRAMES`, or the object being reset. |
| Speed | float | Travel speed while tracking. 0 keeps the current speed and only turns it. |
| TurnRate | float | The most the direction can turn per frame, in degrees. 0 (or 180 and up) points straight at the target every frame. |
| Range | float | Only targets within this X/Y distance count. 0 means any distance. With no target in range, the object keeps going as it was. |
| Mode | int | Bit 1: horizontal only (height is ignored). Bit 2: fighters turn to face the target. Bit 4: no gravity while tracking (fighters). |
| TargetOwner | int | 1: a projectile may also target the fighter who fired it (normally skipped). |
| TargetTeammates | int | 1: teammates are targets too. Normally a fighter on the tracker's team is skipped when the game wouldn't let the tracker hit them. |

- **When it runs:** every frame the object moves (not during hitlag), right after its script for
  that frame.
- **Projectiles:**
  - Steers the projectile's own movement (its first kinetic energy, the one its MSC sets when it's
    fired). Gravity stays as it was, so give a falling projectile enough Speed.
  - Never targets the fighter who fired it.
  - **Reflected:** a reflected projectile goes back at the fighter who fired it, at any distance
    (Range doesn't apply). If that fighter isn't there (KO'd), it goes for the nearest fighter
    other than the one who reflected it. Reflected back again by its owner, it behaves normally.
- **Fighters:**
  - Sets their X and Y speed every frame (X through the same energy as `Add/Set_Momentum`, with no
    braking; Y through the gravity energy).
  - **Gravity** (user: Track_Target left Roy with no gravity after it): gravity keeps acting while
    tracking, so a slow track sags a little each frame. Mode bit 4 cancels it: each frame the
    vertical speed set gets back what gravity took since the last frame (at most 1; a landing or a
    status change that resets the speed isn't "put back"). The gravity energy's own acceleration and
    fall-speed limit are never changed, so nothing is left over when tracking ends. (Before this fix it
    zeroed the acceleration and set the limit to Speed, the way Kirby's side-B homing does, and
    never put them back: the fighter kept no gravity for the rest of the move.)
  - It works in the air. On the ground the fighter's status may move them its own way.
- **Teams:** a fighter is skipped when their "hurt team" equals the tracker's "attack team". That
  is the pair the game compares when deciding whether an attack can hit someone, so these are the
  teammates the tracker couldn't hit anyway.
  - A projectile's attack team is its owner's, or the reflector's after a reflect.
  - In free-for-all the teams are presumably all different or none, so nobody is skipped.
  - **Not confirmed in game:** that turning team attack on changes the hurt teams, so that
    teammates become targets automatically. The team-attack setting itself wasn't found in the
    game code.
  - The read-only variables `TEAM`, `HURT_TEAM` and `ATTACK_TEAM` (below) show the values.
    Comparing them in a team battle with team attack on and off settles it. If team attack doesn't
    change them, teammates stay skipped either way, and `TargetTeammates=1` includes them.
- **Untested in game:** projectiles whose movement isn't their first energy won't turn. Tell me
  which one and I'll look at it.

Example: a projectile that homes for 60 frames at speed 1.8, turning at most 4° a frame.

```
Track_Target(Frames=60, Speed=1.8, TurnRate=4.0, Range=0.0, Mode=0, TargetOwner=0, TargetTeammates=0)
```

## Thread_Start / Thread_Stop

`Thread_Start(ID, Flags){ ... }` runs the commands in its block on their own, frame by frame, while
the script goes on past the block.

- **What can stop it:** nothing about the script itself. The thread keeps running after the
  animation ends or switches, and while the character is KO'd.
- **When it ends:** at the end of its block, at `Thread_Stop(ID)`, or when the object is set up
  again. For a projectile, that means its next use.
- **Inside the block:** any command works, including `FRAME`, `WAIT`, `If` / `True` / `Else`, loops,
  hitboxes, effects, sounds and `CALL`. `FRAME` counts from the thread's start.
- **Timing:**
  - The thread's first frame is the frame after `Thread_Start`.
  - It runs 1 frame per game frame, whatever the animation's speed.
  - It pauses while the object is in hitlag, unless Flags bit 1 is set.

| Parameter | Meaning |
|---|---|
| Offset | Words to the end of the block. Sm4shCommand fills it in from the braces, like `True`'s. |
| ID | Any number. Running `Thread_Start` with an ID that's already running restarts that thread. `Thread_Stop(ID)` stops it; `Thread_Stop(-1)` stops all of this object's threads. |
| Flags | Bit 1: keep running during hitlag. |

Sm4shCommand ends the block with a `Script_End` when it compiles, and doesn't show it when it
decompiles. The script itself jumps over the block, so it never reaches that `Script_End`.

Example: a lingering explosion 30 frames after the move, whatever the fighter is doing by then.

```
Thread_Start(Offset=0, ID=1, Flags=0){
    FRAME(Frames=30)
    Graphic_Effect(...)
    Hitbox(ID=3, ...)
    WAIT(Frames=3)
    Remove_Hitbox(ID=3)
}
```

- **Capacity:** up to 32 threads at once, across all objects.
- **KO'd fighters:** thread hitboxes made while the fighter is in a KO status may be ignored by the
  game.
- **Kirby:** don't leave a thread running in a copy ability's script when Kirby can lose the copy.
  The script it runs may be unloaded with the copy, and the game would crash.
- **Untested in game:** whether a respawn counts as "set up again" and ends the threads.

## Variables, timers and the kinetic type

These are ordinary float variables in the same `0x0F000xxx` range as the position variables
(`docs/position-variables.md`). Use them with `SET_FLOAT`, `ADD_FLOAT`, `Float_Var_Compare` and
the other float variable commands, or with MSC's `WorkModuleF` / `WorkModule`.

- **Floats only.** `SET_INT` and the int compares don't work on them.
- **Each object has its own,** fighters and projectiles alike, up to 48 objects using them at
  once.
- **Lifetime:** the values stay until the object is set up again: a fighter's KO, or a projectile
  being reused for its next shot. They start at 0.
- **Names:** Sm4shCommand shows the names below, and the names compile too.

| ID | Name | Read | Write |
|---|---|---|---|
| `0x0F000300`–`31F` | `VAR_0`–`VAR_31` | the value | set it |
| `0x0F000320`–`32F` | `TIMER_0`–`TIMER_15` | frames left (0 = done) | set frames; it then counts down by 1 every frame the object moves (not in hitlag), stopping at 0 |
| `0x0F000330` | `KINETIC_TYPE` | the current kinetic type, the one `Set_Kinetic_Handler` sets | change it (projectiles too) |
| `0x0F000331` | `TRACK_FRAMES` | `Track_Target` frames left (-1 = until stopped) | set them; 0 stops tracking |
| `0x0F000332` / `333` | `SPEED_X` / `SPEED_Y` | the current speed (all the object's kinetic energies) | — |
| `0x0F000334` / `335` / `336` | `TEAM` / `HURT_TEAM` / `ATTACK_TEAM` | the object's team ids (-1 = none) | — |

Example: the move hits harder if it's used again within 2 seconds (120 frames) of its last use.
`Method=5` is "greater than" (0 `==`, 1 `!=`, 2 `<=`, 3 `>=`, 4 `<`, 5 `>`).

```
FRAME(Frames=10)
Hitbox(ID=0, Part=0, Bone=0, Damage=8.0, Angle=361, KBG=100, FKB=0, BKB=40, Size=5.0, X=0.0, Y=8.0, Z=8.0, Effect=0, Trip=0.0, Hitlag=1.0, SDI=1.0, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=1, SFXType=1, Ground/Air=3, Direct/Indirect=1, Type=1)
Float_Var_Compare(Variable=TIMER_0, Method=5, Value=0)
True(Offset=0){
    // the same ID again: replaces the 8% hitbox with a 12% one
    Hitbox(ID=0, Part=0, Bone=0, Damage=12.0, Angle=361, KBG=100, FKB=0, BKB=50, Size=5.0, X=0.0, Y=8.0, Z=8.0, Effect=0, Trip=0.0, Hitlag=1.0, SDI=1.0, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=2, SFXType=1, Ground/Air=3, Direct/Indirect=1, Type=1)
}
WAIT(Frames=3)
Remove_All_Hitboxes()
// at the end of the move: start (or restart) the 2-second window
SET_FLOAT(Value=120, Variable=TIMER_0)
```

Sm4shCommand works out `True`'s offset from the braces. The variables only hold numbers, so a
script can't stop a move from starting. MSC (`WorkModuleF(0, 0x0F000320)`) can read the same timer
to do that.

## How it works

`tools/acmd_ext_cave.py` (docstring and comments), tested in the emulator by `tools/acmd_ext_test.py`.

- **Loading:** when a script loads, the game swaps each command's CRC for an index and steps by the
  command's size. The cave adds indices 584 and up, each with its own CRC, size and handler.
- **The command:** an Extra command's handler runs the original hitbox handler, then records the six
  values for that hitbox's attack slot. It tags the slot's data (`+0x66`, a halfword the game
  doesn't use) with the record's number.
- **At hit time:** the hit carries a copy of the hitbox data. The tag and a few check words find the
  record. Hooks then scale the victim's hitstun, the victim's and attacker's hitstop, and the
  victim's DI angle read.
- **Per-object state:** the variables, timers and tracking live in a table keyed by the object's
  WorkModule, reached through the position variables' ID hook.
  - A hook after each object's per-frame ACMD run counts the timers down and steers.
  - The object set-up code clears an object's state when it's set up or reused.
- Addresses: `docs/native-notes.md`, "New ACMD commands".
