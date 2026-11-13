# New ACMD commands

These are new commands for game, effect, sound and expression scripts. They need the patched
`cross_f.rpx` (`tools/acmd_ext_cave.py`, part of the standard build). Without it, a script that uses
them won't load properly, so ship the executable with any script that uses them.

Sm4shCommand knows them, with tooltips for every parameter. View > Commands (v1.4.7; Leave_Ground_Cancel from v1.4.8, New_Var from v1.4.9, Gravity_Set from v1.4.10) lists all of them in one
group, **New Commands**, at the top of the list (vanilla commands stay in their own groups), in subgroups:

| Subgroup | Commands |
|---|---|
| Hitboxes & hits | Extra_Special_Hitbox, Extra_Extended_Special_Hitbox, Hit_Check, Hit_Get, Hit_Reset, Hit_Log_Clear |
| Fighter state | Status_Get / _Set, Hitstun_Get / _Set, Hitstop_Set, Damage_Get / _Set, Body_State_Set, Armor_Set, Item_State_Set, Stage_Collision_Set, Leave_Ground_Cancel, Gravity_Set |
| Inputs | Input_Compare, Input_Get, Input_Set |
| Position & rotation | Position_Get / _Set, Rotation_Get / _Set, Joint_Position_Get |
| Animation | Motion_Get / _Set, Animation_Rate_Set |
| Targets & tracking | Track_Target, Last_Hit_Get, Target_Slot_Get |
| Threads | Thread_Start, Thread_Stop |
| Variables | New_Var |

Each command there has in-depth help after its parameters (how it works, the values, gotchas) and several complete
examples (Insert Example / Copy Example), and clicking New Commands shows an overview (targets, compare methods,
variables). That text is written in `tools/acmd_ext_help.py` (a new command gets its group, help and examples
there; `python3 tools/acmd_ext_cave.py --labels tools/Sm4shCommand/param_labels.json`, then
`python3 tools/Sm4shCommand/apply_param_labels.py`, which regenerates Events.cfg). `tools/acmd.py` reads and writes
them too.

| Command | Does |
|---|---|
| `Extra_Special_Hitbox` / `Extra_Extended_Special_Hitbox` | hitboxes with hitstun / hitstop / DI extras |
| `Track_Target` | homing on the nearest fighter |
| `Thread_Start` / `Thread_Stop` | a block that runs on its own |
| `Input_Compare` / `Input_Get` / `Input_Set` | a fighter's buttons and sticks |
| `Hit_Reset` / `Hit_Log_Clear` | the "has hit" flag / who a hitbox has hit |
| `Hit_Check` / `Hit_Get` | whether an attack connected, and with what (hurtbox, shield, ...) |
| `Rotation_Get` / `Rotation_Set`, `Position_Get` / `Position_Set` | a fighter's or article's rotation / position |
| `Motion_Get` / `Motion_Set`, `Animation_Rate_Set` | the animation playing, its frame and rate |
| `Last_Hit_Get`, `Target_Slot_Get` | the last fighter hit / the last attacker, any target's player slot |
| `Status_*`, `Hitstun_*`, `Hitstop_Set`, `Damage_*`, `Body_State_Set`, `Armor_Set`, `Item_State_Set`, `Stage_Collision_Set`, `Joint_Position_Get` | the variable-based features (docs/position-variables.md) as commands with parameters |
| `Leave_Ground_Cancel` | whether a grounded move is cut into Fall when the fighter leaves the ground (exe_v41; exe_v39 / v40's didn't work: below) |
| `Gravity_Set` | a fighter's gravity and max fall speed for the rest of the move (exe_v42, Sm4shCommand v1.4.10) |
| `New_Var` | declares a variable with your own name (int or float, a starting value, per object or per move): 64 more per object, usable in every variable parameter (exe_v40, Sm4shCommand v1.4.9) |

## Extra_Special_Hitbox / Extra_Extended_Special_Hitbox

- **Extra_Special_Hitbox** takes `Special_Hitbox`'s 41 parameters, then six more.
- **Extra_Extended_Special_Hitbox** takes `Extended_Special_Hitbox`'s 43 parameters (the capsule, with
  X2 / Y2 / Z2), then the same six.

The hitbox itself is made exactly as the original command makes it.

| Extra parameter | Type | Meaning |
|---|---|---|
| HitstunMul | float | Multiplies the hitstun this hit gives (knockback × 0.4). A negative value adds that many frames instead: −2 gives 2 frames more (Ultimate's `set_add_reaction_frame`). |
| HitstopMul | float | Multiplies the opponent's hitstop (hitlag), on top of the hitbox's own Hitlag multiplier. |
| HitstopFrames | int | The opponent's hitstop in frames, replacing the computed one. HitstopMul is then ignored. |
| SelfHitstopMul | float | Multiplies the attacker's own hitstop. |
| SelfHitstopFrames | int | The attacker's own hitstop in frames, replacing the computed one. |
| DIMul | float | Multiplies how far DI can turn this hit's launch angle: 0.5 is half the DI, 2 is double. |

- **Multipliers:** 0 or less means ×1 (unchanged; HitstunMul's negative values add frames, above), so a template with zeros behaves like
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
- **Each command is its own hitbox's** (fix, Sm4shCommand v1.4.6's executable): an Extra command now always takes a
  new extras record. Before, the same hitbox ID reused its record, so a hit that was still being handled when the
  script re-issued that ID (the next frame's hitbox, a multi-hit's next wave) read the new hitbox's extras: the
  hitstun of one hitbox showed up on the hit before or after it. And a plain hitbox command now clears the slot's
  tag (`0x02C0874C`, in AttackModule's set-hitbox), so it never keeps an earlier Extra hitbox's extras when its
  angle and knockback match. Extra hitboxes with IDs 8 and 9 (fighters have 10) get their extras too (only 0-7
  did).

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

**Fixed in Sm4shCommand v1.4.6** (user: "Threads haven't worked at all"): opening a file read each script only up
to its first `Script_End`, so a script with a thread came back cut at the thread's block: everything after the
block was gone (and was then saved that way). It now reads past the `Script_End`s inside thread blocks, to the
script's own (checked: a script with a thread, saved and reopened, comes back the same, and the next script too).
The Hitbox Viewer runs threads too: the block starts the frame after `Thread_Start` and runs one frame per game
frame (its `FRAME` counted from 0), alongside the script, with `Thread_Stop`; it used to run the block inline, so
a `FRAME` in it held up the whole move.
`tools/acmd.py` reads each script up to the next one's start, so a block at the very end of a script
(the thread's `Script_End`, then the script's) keeps both: it used to stop at the first, dropping the
script's own end, so the jump past the block landed in the next script (the user's Marth,
`SpecialHi_C2`, through `rolloff_acmd.py`; caught before delivery).

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

## Input_Compare / Input_Get / Input_Set

Commands for a fighter's controller: check an input, copy it into a variable, or force it.

| Command | Does |
|---|---|
| `Input_Compare(Target, Input, Method, Value)` | Compares the input with Value. `True` / `Else` after it run on the result, like `Float_Var_Compare`. |
| `Input_Get(Target, Input, Variable)` | Stores the input in a float variable, e.g. `VAR_0` (`0x0F000300`). |
| `Input_Set(Target, Input, Value)` | Forces the input, as if the controller did it. |

**Target:** 0 self, 1 the nearest opponent, 2 the last fighter hit, 3–10 player slots 1–8.

**Input:**

| Input | What | Read | `Input_Set` Value |
|---|---|---|---|
| 0–7 | attack, special, jump, shield, grab, taunt up, taunt side, taunt down: **held** | 1 / 0 | 1 hold it until 0 is set, 2 press it for one frame, 0 stop forcing it |
| 8–15 | the same buttons, **pressed** this frame | 1 / 0 | as above |
| 16 / 17 | stick X (along the fighter's facing: + = forward) / Y | −1 to 1 | force the stick to the value until input 20 is set |
| 18 / 19 | C-stick X (forward +) / Y | −1 to 1 | force the C-stick |
| 20 | a stick is forced | 1 / 0 | any value: stop forcing both sticks |
| 21 | the fighter's own inputs are ignored | 1 / 0 | 1 ignore its controller (forced inputs still work), 0 back on |
| 22–31 | the state quantities of the input variables (22 situation, 23 damage, 24 / 25 jumps used / max, 26 shield HP, 27 intangible, 28 invincible, 29 / 30 armor and threshold) | as there | as there |
| 32 / 33 | stick / C-stick X **on screen** (+ = right) | −1 to 1 | force it |

**Method** (`Input_Compare`): 0 `==`, 1 `!=`, 2 `<=`, 3 `>=`, 4 `<`, 5 `>` (input Method Value).

- **Reading:** the fighter's own buttons (Target 0, inputs 0–15) are read with the game's own
  `ControlModule(0x2712 held / 0x2710 pressed, button)`, as fighter MSC reads them. Everything else
  is read through the input variables (`docs/position-variables.md`, "Inputs and state").
- **Forcing** goes in where the game reads the controller, so a forced press counts as a real press
  next frame (the inputs for this frame were read before the script ran). Forced inputs last until
  changed, and are cleared when the fighter is KO'd. Details: `docs/position-variables.md`.
- `Input_Compare` stores 0 for an unknown Method, and compares 0 for an unknown Target or Input.
  `Input_Get` / `Input_Set` do nothing in a skipped block.

Examples:

```
// on frame 12: a stronger hit if special is still held
FRAME(Frames=12)
Input_Compare(Target=0, Input=1, Method=0, Value=1)
True(Offset=0){
    Hitbox(ID=0, Part=0, Bone=0, Damage=14.0, ...)
}

// the stick held forward past halfway
Input_Compare(Target=0, Input=16, Method=5, Value=0.5)

// make the fighter just hit jump and ignore its controller for 30 frames
Input_Set(Target=2, Input=21, Value=1)
Input_Set(Target=2, Input=2, Value=2)
WAIT(Frames=30)
Input_Set(Target=2, Input=21, Value=0)
```

## Hit_Reset

`Hit_Reset()` sets this object's "attack has hit" flag back to 0: the `SELF_HIT` variable
(`0x0F0000A0`), which otherwise stays 1 from the first connecting hitbox until the move ends. Use it
between hitboxes to check whether a later one connects on its own. Writing any value to `SELF_HIT`
does the same (`SET_FLOAT(Value=0, Variable=SELF_HIT)`).

It is the game's own `AttackModule(0x2724)`. Only the flag is cleared: the game's "already hit this
fighter" record (which stops one hitbox ID hitting the same fighter twice) isn't changed.

```
FRAME(Frames=5)
Hitbox(ID=0, ...)                       // first hit
WAIT(Frames=3)
Remove_All_Hitboxes()
Hit_Reset()
FRAME(Frames=20)
Hitbox(ID=0, ...)                       // second hit
WAIT(Frames=3)
Float_Var_Compare(Variable=SELF_HIT, Method=0, Value=1)
True(Offset=0){
    // only if the second hitbox connected
}
```

## Hit_Log_Clear

`Hit_Log_Clear(Part)` makes this object forget which fighters its hitboxes of that `Part` have hit, so
the same hitboxes can hit them again, as a new attack would. `Part=-1` clears every part. Unlike
`Hit_Reset`, this is the game's "already hit this fighter" record itself: each Part has one, shared
by the hitboxes with that Part number, and it stays through `Remove_All_Hitboxes` and new hitboxes
until the move (status) ends.

A Part the object doesn't have does nothing. **Fighters have hitbox IDs 0-9 and Parts 0-19; Zelda's
Din's Fire and the new articles copied from it (`tools/extra_kinds.json` `"base": "dein"`) only IDs
0-6 and Parts 0-1.** The game doesn't check a hitbox's ID or Part against these: a hitbox past them
writes over other memory when it connects, and the game crashes (`tools/port_check.py` W4).

```
FRAME(Frames=5)
Special_Hitbox(ID=0, Part=0, ...)       // a multi-hit's first wave
FRAME(Frames=20)
Hit_Log_Clear(Part=0)                   // the second wave can hit the same fighters again
```

It runs the game's own clear (`0x02C10660` on the Part's hit-record lists, as `0x02C0ECDC` does for
every Part: AttackModule vtable `+0x34`, used when an object is set up). Sephiroth's Shadow Flare orbs
(`fighters/edge/specials.md`) use it to give each orb strike a new record.

## Hit_Check / Hit_Get

What an attack has connected with, as MSC's `AttackModule(0x2727 / 0x2726, kinds)` (Ryu's specials cancel on
`0x6`, "hit or shield"; Kirby's star missile checks `0x2`, "hit").

| Command | Does |
|---|---|
| `Hit_Check(Target, When, Kinds)` | `True` / `Else` after it run when the attack connected with any of `Kinds` |
| `Hit_Get(Target, When, Variable)` | the float variable gets the kinds connected with, as bits (0 = none) |

- **Target:** the targets below ("Targets").
- **When:** 0 since the move started (or the last `Hit_Reset`), 1 this frame only.
- **Kinds** (bits; add them): **2** a hurtbox (it hit something), **4** a shield, **6** either. **0** = anything (0x7F,
  MSC's default). The other bits follow Ultimate's collision kinds and are **not confirmed**: 1 another attack
  (clank), 8 a reflector, 16 an absorber, 32 a search box, 64 other.
- The bits are the game's own (`AttackModule +0xC4` this frame, `+0xC8` since the start: `1 << ` each hit record's
  kind, `0x02C09C0C`), read through the module's own getters (vt `+0x2BC` / `+0x2C4`, what the MSC ops call).

```
// cancel into a jump on hit or on shield, from frame 20
FRAME(Frames=0x14)
Hit_Check(Target=0, When=0, Kinds=6)
True(Offset=0){
    Input_Set(Target=0, Input=2, Value=2)
}
```

## Targets

The commands below (and `Hit_Check` / `Hit_Get`) take a **Target**:

| Target | Who |
|---|---|
| 0 | this object: the fighter, or the article (projectile) whose script it is |
| 1 | the nearest opponent |
| 2 | the last fighter this one hit (its current attack's newest hit; once the attack is over, a fighter whose last attacker is this one) |
| 3-10 | player slots 1-8 |
| 11 | the last fighter that hit this one (the game's own record, int `0x10000065`, its projectiles included) |

1, 2 and 11 are worked out from a fighter's own script (from an article's, they find nobody: the command does
nothing / reads 0). A target that isn't there: nothing happens, reads give 0.

## Rotation, position, motion

| Command | Does |
|---|---|
| `Rotation_Get(Target, Axis, Variable)` | Axis 0 / 1 / 2: rotation about X / Y / Z in degrees (`PostureModuleF(4 / 5 / 6)`) |
| `Rotation_Set(Target, X, Y, Z)` | sets it (`PostureModule(4, x, y, z)`, degrees, relative to the facing: +X tilts it forward) |
| `Position_Get(Target, Axis, Variable)` | Axis 0 / 1 / 2: world X / Y / Z; 3: facing (1 right, -1 left) |
| `Position_Set(Target, X, Y, Z, Mode)` | Mode 0: put it at (X, Y, Z); 1: move it by X (forward, along its facing), Y, Z (`PostureModule(3, ...)`) |
| `Motion_Get(Target, What, Variable)` | What 0: the motion (animation) kind playing (`MotionModule(7)`), 1: its frame, 2: its rate |
| `Motion_Set(Target, Motion, Frame, Rate)` | play `Motion` from `Frame` at `Rate` (rate 0 = 1) (`MotionModule(1, ...)`); Motion -1: keep the animation, jump to `Frame` (if it isn't negative) and set `Rate` (if it is above 0) (`MotionModule(0x2713 / 4)`) |
| `Animation_Rate_Set(Rate)` | this fighter's animation rate multiplier (`SELF_ANIM_RATE`, docs/position-variables.md) |

- They run the same module ops MSC does, on the target, so articles work too (an article's rotation is kept until
  changed; a fighter's status may set its own every frame).
- Motion numbers are per fighter (Sm4shCommand's View > Show Animation IDs). The status keeps running and may play
  its own motion again.
- A grounded fighter moved up may snap back or fall, as with MSC's `PostureModule(3, ...)`.

```
Rotation_Set(Target=0, X=0, Y=0, Z=45)                     // this projectile, tilted 45 degrees
Motion_Set(Target=0, Motion=0x5F, Frame=10, Rate=0.5)      // motion 0x5F from frame 10, half speed
Position_Get(Target=1, Axis=1, Variable=VAR_0)             // VAR_0 = the nearest opponent's Y
```

## Last_Hit_Get / Target_Slot_Get

| Command | Does |
|---|---|
| `Last_Hit_Get(Which, Variable)` | Which 0: the player slot (1-8) of the last fighter this one hit; 1: of the last fighter that hit this one. 0 = none |
| `Target_Slot_Get(Target, Variable)` | the player slot (1-8) of any target (the nearest opponent, ...); 0 = none |

The same fighters are Target 2 and 11 of the other commands, so a move can act on them directly:

```
Last_Hit_Get(Which=1, Variable=VAR_0)                      // VAR_0 = who hit me last (player 1-8)
Damage_Set(Target=11, Percent=0)                           // ... and heal them
```

- "Hit last" is the game's own record for each fighter (the player number it keeps for the hit effects' colour,
  so projectiles count). **Unconfirmed:** what it holds before the fighter's first hit (slot 1 or none).

## Fighter-state commands

The features that were variables only (docs/position-variables.md) as commands with parameters. Each is the
variable's own code (the same rules), for any target above.

| Command | The variable it uses |
|---|---|
| `Status_Get(Target, Variable)` / `Status_Set(Target, Status)` | `STATUS` (`StatusModule`; the change takes effect on its next frame) |
| `Hitstun_Get(Target, What, Variable)` | What 0: `HITSTUN` (frames left), 1: `HITSTUN_DEALT` (the last hit's) |
| `Hitstun_Set(Target, Frames)` | `HITSTUN` |
| `Hitstop_Set(Target, Frames, Shake)` | `HITSTOP_SHAKE` (Shake 1) / `HITSTOP` (0) |
| `Damage_Get(Target, Variable)` / `Damage_Set(Target, Percent)` | `DAMAGE` |
| `Body_State_Set(Target, State, Frames)` | State 0: `INTANGIBLE`, 1: `INVINCIBLE` |
| `Armor_Set(Target, Type, Threshold)` | `ARMOR_THRESHOLD`, then `ARMOR` (0 none, 1 super armor, 2 knockback-, 3 damage-based) |
| `Item_State_Set(Target, Code)` | `ITEM` (1 metal on, 2 off, 3 giant, 4 small, 5 Super Star, 6 flower, 7 Timer, 8 / 9 camera) |
| `Stage_Collision_Set(Target, Mode)` | `GROUND` (0 none, 5 air, 1 / 2 ground) |
| `Joint_Position_Get(Target, Joint, VariableX, VariableY, VariableZ)` | `JOINT`: the joint, then its world X / Y / Z |

```
Status_Set(Target=2, Status=0x59)                          // the last fighter hit: shield break
Hitstop_Set(Target=2, Frames=8, Shake=1)
Body_State_Set(Target=0, State=0, Frames=0xA)              // intangible for 10 frames
```

## Leave_Ground_Cancel

`Leave_Ground_Cancel(Enabled)` (exe_v41 and later) decides whether this grounded move is cut short when the
fighter leaves the ground: walks or slides off an edge, or is moved up off it. Normally (on) the move ends there
and the fighter goes to Fall. Off, the move goes on in the air: its animation, hitboxes, effects and the rest of
its scripts, with air physics.

| Enabled | Meaning |
|---|---|
| 1 | on: the normal game (the move ends in Fall when the fighter leaves the ground) |
| 0 | off: the move goes on in the air, and a move that stops at edges can slide off them |
| 2 | off, but the move still stops at edges: it leaves the ground only by moving up |

- **Edges:** in Smash 4 most ground moves stop at edges (their ground correction is 2, "cliff stop": every dash
  attack, from the common `StatusModule(0x5, 0, 0xF, 0x2, ...)`), so they never leave the ground sideways. With
  `Enabled=0` such a move gets correction 1 (slides off, as a walk does) while it's on the ground, so a dash
  attack runs off the stage. `Enabled=2` keeps the stop. A move that already slides off (correction 1) is left as
  it is.
- **In the air:** the frame the fighter is in the air, it gets the air kinetics and stage collision the game's own
  ground / air moves switch to (`KineticModule(0, 0)` + `GroundModule(0x2710, 5)`, `func_102` in every fighter's
  MSC; kinetic 0 = FALL: gravity, air drift and air friction, the speed it had carried on). The animation keeps
  playing (the status doesn't change).
- **Ending:** the move ends in Fall at its interrupt frame (its cancel window opening: `CancelModule(0x2713)`, the
  move's cancel frame from the vl file, or `ENABLE_CANCEL`) or at the end of its animation, whichever comes first;
  in Fall it can act again (aerials, jump, specials).
- **Landing during it:** the move goes on, grounded (no landing, no landing lag), back on the kinetic type it had
  and its own ground correction (correction 1 for an edge-stopping move while the command is still off, so it can
  run off the next edge too), until it ends as it normally would.
- **Reset:** back on by itself at the next status change (the next move, Fall, a hit, ...), so it never carries
  into another move. Turning it back on in the air (`Enabled=1`) ends the move in Fall on the next frame. It stays
  through a motion change inside one status (e.g. a smash attack's charge and swing, when they are one status).
- **Fighters only** (Kirby's copies too). In an article's script it does nothing.
- **Only the leave-ground Fall is held back.** A move's own MSC loop asks for Fall every frame it's in the air
  (`if (global18 == 2) { func_16(0xE, 0); return; }`) and returns there, so the rest of that loop doesn't run in
  the air: a move that ends through its own MSC (a smash charge's hold, a rapid jab's loop, a move that changes its
  motion from MSC) won't end in the air until it reaches its interrupt frame, its animation's end, or the ground.
  Use it on moves that end by their animation (dash attacks, tilts, jabs, smashes' swings, ...), or turn it back
  on at a frame in the script.
- **Ledges:** no ledge grab during the move (the move isn't Fall).
- **Fixed in exe_v41** (user: "forces into edge slide if the move slides off of an edge, rather than continuing the
  move"): exe_v39 / v40 read the fighter's module accessor from the wrong place (StatusModule `+4`, which isn't it),
  so the in-air part never ran: `Enabled=0` made the move slide off the edge, and the move then ended in Fall as
  usual. exe_v41 keeps the accessor from the command itself. (docs/native-notes.md, "Leave_Ground_Cancel".)
- **Not tested in game yet**, only in the emulator (`tools/leave_ground_test.py`): the momentum the move carries
  into the air, and which kinetic type feels right, are to be checked in game.

Example: Diddy Kong's dash attack (`attackdash`, game script) keeps cartwheeling off the stage.

```
Leave_Ground_Cancel(Enabled=0)
FRAME(Frames=9)
Hitbox(ID=1, Part=0, Bone=0, Damage=2, Angle=0x28, KBG=0x64, FKB=0x37, BKB=0, Size=3.5, X=0, Y=7, Z=8.5, Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=1, SFXType=1, Ground/Air=0x80000003, Direct/Indirect=1, Type=6)
WAIT(Frames=1)
Remove_All_Hitboxes()
FRAME(Frames=18)
Hitbox(ID=0, Part=0, Bone=0, Damage=2, Angle=0x16E, KBG=0x64, FKB=0x3E, BKB=0, Size=3.5, X=0, Y=7, Z=8.5, Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=1, SFXType=1, Ground/Air=3, Direct/Indirect=1, Type=6)
WAIT(Frames=1)
Remove_All_Hitboxes()
FRAME(Frames=24)
Hitbox(ID=0, Part=0, Bone=0, Damage=3, Angle=0x4E, KBG=0x5A, FKB=0, BKB=0x50, Size=4.5, X=0, Y=6, Z=8.5, Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=2, SFXType=1, Ground/Air=3, Direct/Indirect=1, Type=6)
WAIT(Frames=1)
Remove_All_Hitboxes()
```

`tools/acmd.py` reads and writes it (`Command(acmd.BY_NAME['leave_ground_cancel'], [0])`).

## Gravity_Set

`Gravity_Set(Accel, MaxFall, Mode)` (exe_v42 and later, Sm4shCommand v1.4.10) sets this fighter's gravity and max fall
speed for the rest of the move: an aerial, a special, a grounded move that went on in the air with
`Leave_Ground_Cancel(Enabled=0)`, ... The game's own gravity code still does the falling, with these two numbers.

| Parameter | Type | Meaning |
|---|---|---|
| Accel | float | Gravity: how much the vertical speed drops each frame, on the scale of the fighter_param "Gravity" (`0x03000018`; Diddy Kong 0.105). 0: no gravity (the vertical speed stays as it is: a rise keeps rising). Below 0 (-1): the fighter's own. |
| MaxFall | float | Max fall speed, on the scale of "Maximum Fall Speed" (`0x03000019`; Diddy 1.75). Falling faster than it, the fighter slows to it gradually, by its "V acceleration" (`0x0300001A`, Diddy 0.016) a frame, as after a fast fall (Mode 2: at once). 0: it stops falling. Below 0 (-1): the fighter's own. |
| Mode | int | Bits: 1 Accel and MaxFall are multipliers of the fighter's own (0.5 = half; -1 still keeps its own); 2 a fall faster than MaxFall is cut to it at once (every frame); 4 no fast fall while it holds (the fast-fall flag `0x21000001` is turned off every frame). |

- **Off:** `Accel` and `MaxFall` both below 0 with Mode 0 or 1 turns it off at that frame.
- **When it ends by itself** (the fighter's own values from the next frame, so it never leaks):
  - at the next status change (the next move, Fall, landing, a jump, a grab / throw, a KO, a respawn, ...);
  - the moment a hit takes effect (the fighter will flinch or be launched), in the hit itself, before the damage
    status starts. A hit with no reaction (armor, or knockback under the fighter's threshold) leaves it: the move
    goes on (user's choice: armor keeps it);
  - on a ledge grab, whichever path it takes: the fighter's situation on the ledge, a cliff status (`0x72`–`0x7A`,
    CliffCatchMove … CliffJumpQuick2) or a tether hang (`0xF3` / `0xF4`) as the current or the pending status, even
    before the status change happens. (A Leave_Ground_Cancel move can't grab ledges anyway; aerials and specials
    can.)
  - It stays through a motion change inside one status.
- **Wins over the move's own gravity:** every frame the gravity energy is computed with these values, whatever the
  move's MSC set (`KineticModule(0xF / 0x14 / 0x15, 1, ...)`) and whatever kinetic type change reset the energy in
  between. The energy itself keeps the fighter's own values outside its update, so nothing has to be restored.
- **Only while the fighter falls with gravity:** a move whose own kinetics turn gravity off (moved by its
  animation, a move's own hover) has no gravity to change.
- **Fast fall:** without Mode 4, a fast fall (down during an aerial) still falls at the fighter's own fast-fall
  speed.
- **Reading it:** `GRAVITY` (`0x0F000337`) and `MAX_FALL` (`0x0F000338`) give the values in effect (positive numbers,
  as the params), e.g. for `Float_Var_Compare`. Read only.
- **Fighters only** (Kirby's copies too). In an article's script it does nothing (an article's gravity is another
  energy class, not done).
- **Not tested in game yet**, only in the emulator with the game's own gravity code (`tools/gravity_set_test.py`):
  the curve frame by frame, the restore, a reset in between, the hit / armor / ledge / status-change ends.

Example: Diddy Kong's dash attack runs off the stage and floats down (gravity 0.02 instead of 0.105, falling at most
0.6 instead of 1.75). The rest of the script is the vanilla one (Leave_Ground_Cancel's example above).

```
Leave_Ground_Cancel(Enabled=0)
Gravity_Set(Accel=0.02, MaxFall=0.6, Mode=0)
FRAME(Frames=9)
...
```

A floaty aerial (half the fighter's own gravity and max fall from frame 6, its own again at 30):

```
FRAME(Frames=6)
Gravity_Set(Accel=0.5, MaxFall=0.5, Mode=1)
FRAME(Frames=30)
Gravity_Set(Accel=-1, MaxFall=-1, Mode=0)
```

A hover (a rise slows to a stop, the fall stops at once, no fast fall), then a heavy drop:

```
Gravity_Set(Accel=0.03, MaxFall=0, Mode=6)
FRAME(Frames=40)
Gravity_Set(Accel=0.2, MaxFall=3, Mode=0)
```

How it works: docs/native-notes.md "Gravity_Set".

## New_Var

`New_Var(Name=charge, Type=int, Initial=0, Scope=move)` (exe_v40 and later, Sm4shCommand v1.4.9) declares a variable
with a name of your own. The name then works in every variable parameter of every open script, like `VAR_0`:
`SET_FLOAT`, `SET_INT`, `ADD_INT`, `INC_INT`, `SUB_FLOAT_2`, `Float_Var_Compare`, `Int_Var_Compare`,
`INT_VAR_COMPARE_VAR`, and the new commands' `Variable=` (`Hit_Get`, `Position_Get`, `Input_Get`, ...).

| Parameter | Values |
|---|---|
| `Name` | letters, digits and `_`, not starting with a digit, up to 24 characters; case doesn't matter. Not an alias (`VAR_0`, `SELF_HIT`, ...) or a command's name. |
| `Type` | `float` (default, or 0) or `int` (or 1). An int variable keeps whole numbers: a float written to it is cut toward 0 (2.7 → 2, −2.7 → −2). |
| `Initial` | the starting value (default 0). |
| `Scope` | `object` (default, or 0): `Initial` is set the first time a New_Var for it runs for this object; later New_Vars leave it alone, and the value stays (between moves) until the object is set up again (a fighter's KO, a projectile's next shot), as `VAR_n`'s. `move` (or 1): `Initial` is set every time this New_Var runs, so at the top of a move's script it starts fresh at every use of the move. |
| `Slot` | optional, 0–63: the variable is `0x0F000380 + Slot`. Left out (or `auto`): the slot the name already has in the open scripts, else the lowest free one. Sm4shCommand writes it back (`Slot=0`) when it shows the script again. |

- **Storage:** each object (fighter or article) has 64 of them, apart from its `VAR_0`–`VAR_31` / `TIMER_0`–`TIMER_15`
  (which work as before) and from every other object's. They live with the object's `VAR_n` (the same 48-object
  table), read 0 until set, and are cleared with them.
- **Int and float both work.** The value is kept as a float: the int commands and ops (`SET_INT`, `ADD_INT`,
  `INC_INT`, `Int_Var_Compare`, MSC's `WorkModule` int ops) read it cut to a whole number and write a whole number,
  the float ones read and write the float. (`VAR_n` stays float-only.) Whole numbers are exact up to 16,777,216.
- **MSC:** `WorkModuleF(0, 0x0F000380 + slot)` reads one, `WorkModule(6, 0x0F000380 + slot)` as an int;
  `WorkModule(0 / 7, value, ID)` write it. Give the variable a fixed `Slot` for this.
- **IDs:** `0x0F000380`–`0x0F0003BF`. `0x0F0003C0`–`0x0F0003FF` still read 0.

### Names in Sm4shCommand

The command keeps the name in itself (6 words of ASCII after its four parameters), so the name comes back when
the file is opened again: Sm4shCommand reads every `New_Var` in the opened file / fighter / project and shows the
name wherever that variable is used, in every script (`INC_INT(Variable=charge)`). Opening another fighter
forgets them.

- A name is known once a script declaring it compiles, or a file with its `New_Var` is opened. Within a script
  the name works above its `New_Var` too. Another script may use the name without declaring it, once the
  declaring one has compiled (saved) or was in the opened file; or declare it there too (with `Scope=object` a
  second `New_Var` doesn't reset it).
- An unknown name is a compile error ("unknown variable ... needs New_Var(Name=...)").
- View > Commands, `New_Var`: its parameters, help and examples, and the names declared in the open scripts.
  Hovering a name in a script shows its slot, type and scope.
- With View > Show Variable Aliases off, the uses show as `0x0F000380` + slot (which compiles too); `New_Var`
  itself always shows its name.
- `tools/acmd.py` shows them too (`python3 tools/acmd.py vars game.bin`; `acmd.new_var(name, slot, type,
  initial, scope)` makes one).

Example: a charge counter, fresh at every use of the move.

```
New_Var(Name=charge, Type=int, Initial=0, Scope=move)
FRAME(Frames=5)
Set_Loop(Iterations=30){
    Input_Compare(Target=0, Input=1, Method=0, Value=1)
    True(Offset=0){
        INC_INT(Variable=charge)
    }
    WAIT(Frames=1)
    Goto(Offset=0)
}
Int_Var_Compare(Variable=charge, Method=3, Value=20)
True(Offset=0){
    // held 20 frames or more: the strong hitbox
    Hitbox(ID=0, Part=0, Bone=0, Damage=18, Angle=361, KBG=100, FKB=0, BKB=60, Size=7, X=0, Y=8, Z=9, Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=2, SFXType=1, Ground/Air=3, Direct/Indirect=1, Type=1)
}
Else(Offset=0){
    Hitbox(ID=0, Part=0, Bone=0, Damage=10, Angle=361, KBG=100, FKB=0, BKB=40, Size=5, X=0, Y=8, Z=8, Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=2, SFXType=1, Ground/Air=3, Direct/Indirect=1, Type=1)
}
WAIT(Frames=3)
Remove_All_Hitboxes()
```

Example: every third use of the move is stronger (`Scope=object`: the count is kept between uses, until a KO).

```
New_Var(Name=uses, Type=int, Initial=0, Scope=object)
INC_INT(Variable=uses)
FRAME(Frames=10)
Int_Var_Compare(Variable=uses, Method=3, Value=3)
True(Offset=0){
    Hitbox(ID=0, Part=0, Bone=0, Damage=16, Angle=361, KBG=100, FKB=0, BKB=60, Size=6, X=0, Y=8, Z=8, Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=2, SFXType=1, Ground/Air=3, Direct/Indirect=1, Type=1)
    SET_INT(Value=0, Variable=uses)
}
Else(Offset=0){
    Hitbox(ID=0, Part=0, Bone=0, Damage=8, Angle=361, KBG=100, FKB=0, BKB=40, Size=5, X=0, Y=8, Z=8, Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=2, SFXType=1, Ground/Air=3, Direct/Indirect=1, Type=1)
}
WAIT(Frames=3)
Remove_All_Hitboxes()
```

More examples (float variables with the target commands, a counter shared by two scripts, a fixed slot for MSC)
are in Sm4shCommand's View > Commands.

## Debug counters

Words at `0x04B93900` (Cemu: Debug > Memory, go to the address), all 0 at boot, counting up across
the whole session. They show where an Extra hitbox's hitstop extras stop working.

| Offset | Word |
|---|---|
| `+0x00` | Extra hitboxes recorded (their slot tagged) |
| `+0x04` / `+0x08` | victim hitstop hook: runs / an Extra hit found |
| `+0x0C` / `+0x10` | last victim hitstop: before / after the extras (frames) |
| `+0x14` / `+0x18` | attacker hitstop hook (before the slowdown rate): runs / found |
| `+0x1C` / `+0x20` | last attacker hitstop there: before / after |
| `+0x24` / `+0x28` | attacker hitstop hook (after the rate): runs / found |
| `+0x2C` / `+0x30` | last attacker hitstop there: before / after |
| `+0x34` / `+0x38` | hitstun hook: runs / found |
| `+0x3C` | Extra hitbox commands run |
| `+0x40` | the last one's ID |

## Variables, timers and the kinetic type

These are ordinary float variables in the same `0x0F000xxx` range as the position variables
(`docs/position-variables.md`). Use them with `SET_FLOAT`, `SUB_FLOAT_2`, `Float_Var_Compare` and
the other float variable commands, or with MSC's `WorkModuleF` / `WorkModule`. (`ADD_FLOAT` does
nothing in this game: its handler is empty. Add by `SUB_FLOAT_2` of a variable holding a negative value.)

- **Floats only.** `SET_INT` and the int compares don't work on them (New_Var's variables, below, do).
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
| `0x0F000337` / `338` | `GRAVITY` / `MAX_FALL` | a fighter's gravity and max fall speed in effect (`Gravity_Set`'s, else its own: the gravity energy's; exe_v42); other objects read 0 | — |
| `0x0F000340`–`37F` | `SLOT1_SHARED_0`–`SLOT8_SHARED_7` | `VAR_24`–`VAR_31` of the fighter in that player slot (below) | set it |
| `0x0F000380`–`3BF` | your `New_Var` names (slots 0–63; exe_v40) | the value (int or float commands) | set it (an int one keeps whole numbers) |

### Shared variables (another fighter's)

`SLOTn_SHARED_k` (`0x0F000340 + 8 × (n − 1) + k`, n = 1–8, k = 0–7) is `VAR_(24 + k)` of the fighter
in player slot n: the very same float that fighter reads and writes as its own `VAR_24`–`VAR_31`
(`0x0F000318`–`31F`). Any object can use them, fighters and projectiles alike, from ACMD or MSC
(`WorkModuleF(0, 0x0F000340 + ...)`), so a projectile can keep state on the fighter it hit, and that
fighter's own scripts see it as its `VAR_24`–`VAR_31`.

- Slots are the fighter table entries, as in the position variables (`docs/position-variables.md`):
  player slot 1 = `SLOT1_SHARED_*`. Each ID names a fixed slot: which one to use (say, the fighter
  just hit) is up to the script, nothing here gives a fighter's slot number.
- An empty slot, or a fighter that isn't live (not loaded in yet), reads 0 and a write there does
  nothing.
- A write is what the fighter itself would do with its `VAR_(24 + k)`: it counts as one of the 48
  objects using variables if that fighter had none yet. The values go when that fighter is set up
  again (its KO), not when the projectile that wrote them goes.
- `VAR_24`–`VAR_31` are therefore the variables other objects can see and change: keep a fighter's
  private state in `VAR_0`–`VAR_23`.

Example: the projectile, on hit, counts the hits on the fighter in slot 2; that fighter's own
scripts read the count as `VAR_24`.

```
// in the projectile's script (SUB_FLOAT_2 by VAR_0 = -1 adds 1)
SET_FLOAT(Value=-1, Variable=VAR_0)
SUB_FLOAT_2(Variable=SLOT2_SHARED_0, SourceVariable=VAR_0)
```

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
  - The shared variables find the slot's fighter in the fighter table and use that fighter's entry
    in the same table.
- **The new commands' targets:** `position_vars_cave.py`'s variable `0x0F0002BC + target` (read only) gives the
  target's module accessor; the commands then run the module's MSC op through its wrapper with that accessor, as
  the position variables do (`nc_msc`). Their code is the cave's second part (`0x04B98900`).
- **New_Var:** the slots' values are a second 48 × 0x100-byte table beside the variables' (`0x04BD0000`, in 16 KB
  the executable's code region was grown by, with its code at `0x04BD3000`); the object's entry keeps which slots
  were declared and which are int. The WorkModule's int functions are redirected in the six WorkModule vtables for
  these IDs. Details: `docs/native-notes.md`, "New_Var".
- **Leave_Ground_Cancel:** a 16-entry table keyed by the fighter's StatusModule (`0x04B93A00`, its code from
  `0x04B93B10`) and three hooks on the game's StatusModule: the MSC situation read, the MSC status request and the
  status change. Details: `docs/native-notes.md`, "Leave_Ground_Cancel".
- **Gravity_Set:** a 16-entry table keyed by the fighter's module accessor (`0x04BD3E00`, its code from
  `0x04BD3600`, in New_Var's grown region) and three hooks: the gravity energy's update (entry: its values swapped
  in; exit: the energy's own put back), the damage reaction decision (a hit that takes effect ends it) and, through
  Leave_Ground_Cancel's status change hook, the status change. Details: `docs/native-notes.md`, "Gravity_Set".
- Addresses: `docs/native-notes.md`, "New ACMD commands".
