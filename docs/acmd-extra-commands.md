# New ACMD commands

These are new commands for game, effect, sound and expression scripts. They need the patched
`cross_f.rpx` (`tools/acmd_ext_cave.py`, part of the standard build). Without it, a script that uses
them won't load properly, so ship the executable with any script that uses them.

Sm4shCommand knows them, with tooltips for every parameter. View > Commands lists the Extra hitboxes,
Hit_Reset / Hit_Log_Clear and Hit_Check / Hit_Get under Hitboxes, the Input commands under Variables & compares,
Track_Target, Last_Hit_Get and Target_Slot_Get under Traces & targeting, Rotation_ / Position_ under Movement &
physics, Motion_, Animation_Rate_Set and Joint_Position_Get under Animation, and the fighter-state commands
(Status_, Hitstun_, Hitstop_Set, Damage_, Body_State_Set, Armor_Set, Item_State_Set, Stage_Collision_Set) under
Hurtboxes & body. `tools/acmd.py` reads and writes them too.

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
| `0x0F000340`–`37F` | `SLOT1_SHARED_0`–`SLOT8_SHARED_7` | `VAR_24`–`VAR_31` of the fighter in that player slot (below) | set it |

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
- Addresses: `docs/native-notes.md`, "New ACMD commands".
