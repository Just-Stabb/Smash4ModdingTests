# New ACMD commands

These are new commands for game, effect, sound and expression scripts. They need the patched
`cross_f.rpx` (`tools/acmd_ext_cave.py`, part of the standard build). Without it, a script that uses
them won't load properly, so ship the executable with any script that uses them.

Sm4shCommand knows them, with tooltips for every parameter. View > Commands (v1.4.7; Leave_Ground_Cancel from v1.4.8, New_Var from v1.4.9, Gravity_Set from v1.4.10, variables in Extra hitboxes from v1.4.11, Position_Place / Position_Offset_Get and Target 12 from v1.4.12, Buffer_Clear / Buffer_Set from v1.4.13, Time_Scale / Target_Time_Scale / Stage_Freeze from v1.7.0 (Stage_Freeze's On 2 / 3 and the flash-free On 1 from v1.7.8), Var_Reset_Set and New_Var's Reset from v1.7.4, Hitbox_Hold from v1.7.5, Effect_Camera from v1.7.6, its v5 squash fix from v1.7.10, Screen_Invert from v1.7.12) lists all of them in one
group, **New Commands**, at the top of the list (vanilla commands stay in their own groups), in subgroups:

| Subgroup | Commands |
|---|---|
| Hitboxes & hits | Extra_Special_Hitbox, Extra_Extended_Special_Hitbox, Hit_Check, Hit_Get, Hit_Reset, Hit_Log_Clear, Hitbox_Hold |
| Fighter state | Status_Get / _Set, Hitstun_Get / _Set, Hitstop_Set, Damage_Get / _Set, Body_State_Set, Armor_Set, Item_State_Set, Stage_Collision_Set, Leave_Ground_Cancel, Gravity_Set |
| Inputs | Input_Compare, Input_Get, Input_Set, Buffer_Clear, Buffer_Set |
| Position & rotation | Position_Get / _Set, Position_Place, Position_Offset_Get, Rotation_Get / _Set, Joint_Position_Get, Line_Test |
| Animation | Motion_Get / _Set, Animation_Rate_Set |
| Targets & tracking | Track_Target, Last_Hit_Get, Target_Slot_Get |
| Threads | Thread_Start, Thread_Stop |
| Time & stage | Time_Scale, Target_Time_Scale, Stage_Freeze |
| Effects | Effect_Camera, Screen_Invert |
| Variables | New_Var, Var_Reset_Set |

Each command there has in-depth help after its parameters (how it works, the values, gotchas) and several complete
examples (Insert Example / Copy Example), and clicking New Commands shows an overview (targets, compare methods,
variables). That text is written in `tools/acmd_ext_help.py` (a new command gets its group, help and examples
there; `python3 tools/acmd_ext_cave.py --labels tools/Sm4shCommand/param_labels.json`, then
`python3 tools/Sm4shCommand/apply_param_labels.py`, which regenerates Events.cfg). `tools/acmd.py` reads and writes
them too.

| Command | Does |
|---|---|
| `Extra_Special_Hitbox` / `Extra_Extended_Special_Hitbox` | hitboxes with hitstun / hitstop / DI extras; Damage / Angle / KBG / FKB / BKB / Size from variables (exe_v43, Sm4shCommand v1.4.11: below) |
| `Hitbox_Hold` | a hitbox whose hits keep the victim in place (no knockback travel; damage, hitstun, hitlag kept): the rapid-jab setting the port pipeline gives Ultimate's setoff-off rapid-jab hits (exe_v46y_hold, Sm4shCommand v1.7.5: "Hitbox_Hold" below) |
| `Track_Target` | homing on the nearest fighter |
| `Thread_Start` / `Thread_Stop` | a block that runs on its own |
| `Input_Compare` / `Input_Get` / `Input_Set` | a fighter's buttons and sticks |
| `Buffer_Clear` / `Buffer_Set` | a fighter's input buffer: empty it (all or some inputs, once or for some frames), or put an input in it as if pressed (exe_v46l, Sm4shCommand v1.4.13: below) |
| `Hit_Reset` / `Hit_Log_Clear` | the "has hit" flag / who a hitbox has hit |
| `Hit_Check` / `Hit_Get` | whether an attack connected, and with what (hurtbox, shield, ...) |
| `Rotation_Get` / `Rotation_Set`, `Position_Get` / `Position_Set` | a fighter's or article's rotation / position |
| `Position_Place` / `Position_Offset_Get` | the position variables' uses as commands, for every target: put a fighter in front of / above this one, at a stage point, move it, put this fighter next to it, some axes only, once or held every frame (through the stage if wanted); read where it is relative to this one (exe_v46k, Sm4shCommand v1.4.12: below) |
| `Motion_Get` / `Motion_Set`, `Animation_Rate_Set` | the animation playing, its frame and rate |
| `Last_Hit_Get`, `Target_Slot_Get` | the last fighter hit / the last attacker, any target's player slot |
| `Status_*`, `Hitstun_*`, `Hitstop_Set`, `Damage_*`, `Body_State_Set`, `Armor_Set`, `Item_State_Set`, `Stage_Collision_Set`, `Joint_Position_Get` | the variable-based features (docs/position-variables.md) as commands with parameters |
| `Leave_Ground_Cancel` | whether a grounded move is cut into Fall when the fighter leaves the ground (exe_v41; exe_v39 / v40's didn't work: below) |
| `Gravity_Set` | a fighter's gravity and max fall speed for the rest of the move (exe_v42, Sm4shCommand v1.4.10) |
| `Time_Scale` / `Target_Time_Scale` / `Stage_Freeze` | the whole match slower (the game's slow-motion) or faster (extra game steps a frame); one fighter slower (the Timer's slow); the stage frozen (exe_v46n, Sm4shCommand v1.7.0: below) |
| `Line_Test` | the stage between two points: where a segment first meets a floor / wall / ceiling, how far, which kind (the game's own GroundModule ray check); also from the `LINE_*` variables for MSC (exe_v46v_line: `tools/line_test_cave.py`, below) |
| `New_Var` | declares a variable with your own name (int or float, a starting value, per object or per move): 64 more per object, usable in every variable parameter (exe_v40, Sm4shCommand v1.4.9); `Reset`: back to its starting value on a KO / landing / ledge grab / hit (exe_v46w, Sm4shCommand v1.7.4: "Variable resets" below) |
| `Var_Reset_Set` | any variable (`VAR_n`, `TIMER_n`, a New_Var name, the input / state variables) put back to a value when its owner is KO'd, lands, grabs a ledge or is hit (exe_v46w, Sm4shCommand v1.7.4: "Variable resets" below) |
| `Effect_Camera` | an effect attached to the camera: in front of it, facing it, following its moves and zooms every frame (full-screen overlays, bursts in front of the camera, vignettes); Mode 1 keeps it on the same part of the screen (exe_v46z_camfx, Sm4shCommand v1.7.6: "Effect_Camera" below) |
| `Screen_Invert` | the 3D picture (not the HUD) as a photo-negative at any strength, then greyed / darkened / lifted toward a colour, faded in and out; the game's own colour-correction pass (exe_v46z_inv, Sm4shCommand v1.7.12: "Screen_Invert" below) |

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

### Variables in Extra hitboxes (exe_v43, Sm4shCommand v1.4.11)

The Extra hitboxes' **Damage, Angle, KBG, FKB, BKB and Size** (both commands) can each be a variable instead of a
number: `Damage=VAR_0`, `Angle=STICK_ANGLE`, `Size=charge` (a `New_Var`), or an ID (`0x0F000300`). The variable is
read when the command runs and the hitbox is made from its value through the game's own hitbox code, exactly as from
a number. Fields written as numbers work as before; a command with no variable does what it did in exe_v42.

- **Which variables:** any variable ID from `0x01000000` to `0x1FFFFFFF`: `VAR_0`–`VAR_31`, `New_Var` names (int or
  float), the mod's other variables (`STICK_ANGLE`, `ROT_X`, `POS_...`, `SELF_DAMAGE`, ...), the game's own floats
  (`0x0xxxxxxx`: work floats, fighter_param) and ints (`0x1xxxxxxx`, read as ints). Not flags (`0x2xxxxxxx`).
- **Encoding (why it doesn't break old scripts):** the variable's ID goes in the parameter word as it is (a float
  parameter holds the ID's bits). No real hitbox has such a word: as an int it is 16 million or more, as a float
  2.4·10⁻³⁸ to 10⁻¹⁹. Bits 20–23 (`0x00F00000`, never part of an ID the game or the mod uses) hold the flags. So
  the command, its size and every other parameter are unchanged, and an old script reads exactly as before.
- **The value:**
  - Damage, Size: as they are; below 0 is 0.
  - KBG, FKB, BKB: rounded to a whole number (halves away from 0); below 0 is 0.
  - Angle: rounded, then wrapped into 0–359 (−30 → 330, 725 → 5, 360 → 0, −0.5 → 359), except 361–368, kept as
    they are (361 = the Sakurai angle).
- **Facing:** a hitbox's angle is along the fighter's facing, as for every hitbox (0 forward, 90 up, 180 backward,
  270 down); the game mirrors it for a fighter facing left. Variables measured along the facing (`STICK_ANGLE`) go in
  as they are. An angle measured on screen (0 right, 90 up, 180 left, e.g. `STICK_ANGLE_RAW`) needs `|WORLD`: facing
  left it becomes 180 − value (screen 135°, up-left, is 45° forward-up for a fighter facing left).
- **Flags** (after the variable, with `|`, any case and order):
  - `|FOLLOW`: the field is read again every frame while the hitbox is out (a stick-aimed hitbox that follows the
    stick, damage that grows with a charge). It runs every frame the object moves, after its script, so not in
    hitlag. It ends when another hitbox is made with the same ID (Extra or plain), when the object is reset (KO, a
    projectile's next use), or after 16 more FOLLOW hitboxes (the oldest goes). Damage and Size change through the
    same calls `Change_Hitbox_Damage` / `Change_Hitbox_Size` make, so the hitbox really resizes; they keep the ratio
    the game's code gave the first value (Strike Kirby's ×1.15, ...).
  - `|WORLD` (Angle): the value is a screen angle (above).
  - `|NEG`: minus the value (`Angle=ROT_X|NEG`).
- **Needs exe_v43.** An older executable reads the ID as a number (a hitbox of size ~0 with an angle in the
  millions).

Variables for it (read only, this object's own; exe_v43):

| ID | Name | Read |
|---|---|---|
| `0x0F0003C0` | `STICK_ANGLE` | the control stick's angle in degrees, 0–360, along the facing (0 forward, 90 up, 180 back, 270 down): a hitbox angle as it is. 0 in neutral |
| `0x0F0003C1` | `STICK_ANGLE_RAW` | the same on screen (0 right, 90 up), whichever way the fighter faces (`|WORLD` in a hitbox) |
| `0x0F0003C2` | `STICK_LEN` | how far the stick is pushed: √(x² + y²), 0 (neutral) to 1 (a little over on diagonals) |
| `0x0F0003C3`–`3C5` | `CSTICK_ANGLE`, `CSTICK_ANGLE_RAW`, `CSTICK_LEN` | the C-stick's |
| `0x0F0003C6`–`3C8` | `ROT_X`, `ROT_Y`, `ROT_Z` | the object's rotation about X / Y / Z in degrees (`PostureModuleF(4–6)`, what `Rotation_Get` stores; a fighter's forward tilt is X) |

They come from the input variables (`STICK_X` / `STICK_Y` along the facing, `STICK_X_RAW` on screen;
docs/position-variables.md), forced sticks (`Input_Set`) included; an object without a controller reads 0.

Example 1, a hit launched the way the control stick points (on frame 8):

```
FRAME(Frames=8)
Extra_Special_Hitbox(ID=0, Part=0, Bone=0, Damage=10, Angle=STICK_ANGLE, KBG=80, FKB=0, BKB=50, Size=6, X=0, Y=8, Z=8, Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=2, SFXType=1, Ground/Air=3, Direct/Indirect=1, Type=1, HitBits=0x3F, Unk41=0, CollisionPart=0xF, NoScale=0, Shieldable=1, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0, HitAllStates=0, FacingRestrict=3, NoGrabRelease=0, TeamDamage=0, DisableHitlag=0, NoGFX=0, Flinchless=0, Shape=0, HitstunMul=0, HitstopMul=0, HitstopFrames=0, SelfHitstopMul=0, SelfHitstopFrames=0, DIMul=0)
WAIT(Frames=4)
Remove_All_Hitboxes()
```

`Angle=STICK_ANGLE|FOLLOW` makes it follow the stick every frame while it is out; `Angle=STICK_ANGLE_RAW|WORLD` is
the same angle from the on-screen one.

Example 2, the fighter's current rotation, stored, as the hitbox's angle:

```
FRAME(Frames=6)
Rotation_Get(Target=0, Axis=0, Variable=VAR_1)
Extra_Special_Hitbox(ID=0, Part=0, Bone=0, Damage=9, Angle=VAR_1, KBG=90, FKB=0, BKB=40, Size=5, X=0, Y=8, Z=7, Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=2, SFXType=1, Ground/Air=3, Direct/Indirect=1, Type=1, HitBits=0x3F, Unk41=0, CollisionPart=0xF, NoScale=0, Shieldable=1, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0, HitAllStates=0, FacingRestrict=3, NoGrabRelease=0, TeamDamage=0, DisableHitlag=0, NoGFX=0, Flinchless=0, Shape=0, HitstunMul=0, HitstopMul=0, HitstopFrames=0, SelfHitstopMul=0, SelfHitstopFrames=0, DIMul=0)
WAIT(Frames=3)
Remove_All_Hitboxes()
```

`Rotation_Get` stores degrees; Axis 0 (about X) is a fighter's forward tilt, the way `Rotation_Set`'s X turns it.
`Angle=ROT_X` does the same without the variable (and `|FOLLOW` follows it); `Angle=ROT_X|NEG` takes minus it, so a
fighter tilted 30° forward (nose down) launches 30° downward (330). Which axis and sign match a given move's
rotation depends on how its MSC / ACMD rotates the model: check in game.

More examples (FOLLOW with a neutral-stick fallback, a hitbox growing with a charge, an Extended capsule aimed with
the C-stick) are in Sm4shCommand's View > Commands. The Hitbox Viewer draws a variable with the script's last
`SET_FLOAT` of it, else a stand-in (Damage 10, Angle 0, KBG 100, FKB 0, BKB 40, Size 4), and lists it in the
Extras column.

How it works (`tools/acmd_ext_cave.py` `hv_code`; docs/native-notes.md "Hitbox variables"): the two commands'
handler table entries point at `hv_extra`, which reads each variable field, writes the value into the command's own
parameter word, calls the unchanged Extra handler (the game's hitbox handler, then the extras), and puts the words
back. A FOLLOW hitbox gets an entry in a 16-entry table keyed by its AttackModule slot; the per-frame hook sets
Damage and Size through the same AttackModule calls the vanilla `Change_Hitbox_Damage` / `Change_Hitbox_Size` make
(so a size change resizes the hitbox as that command does), and writes Angle / KBG / FKB / BKB into the slot's data
(`+0x20`-`+0x2C`) with the extras record's check words. Tested in `tools/hitbox_var_test.py` (unicorn) and
`tools/Sm4shCommand/hitbox_var_test.cs` (the compiler).

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

**Fixed in exe_v46m: threads now run in game** (user: "Can you fix Threads?"). Before exe_v46m no thread ever ran in
game. The God Fist's watchdog thread never logged once, and each God Fist left a registered, never-running thread.
`Thread_Start` registered the thread, but the per-frame runner never reached it:

- **The cause.** The runner sits at the entry of each object's step:
  - fighters `0x02E408B8`, called from `0x02E40B90`;
  - weapons `0x02BAD64C`;
  - items `0x03048064`.
  Its caller hands it r4, a slot on the caller's stack that holds the accessor (`addi r4, r1, 0xC; stw r31, 0xC(r1)`).
  The runner first checked r4 as a heap pointer (`0x10000000`-`0x8FFFFFFF`). The game's update thread runs on a stack
  outside that range (Cemu keeps the default threads' stacks in its own area below MEM2), so the check failed on
  every frame for every object.
- **Why the tests passed.** Unicorn had its stack at `0x7F00F000` and passed a heap holder, so the tests never saw it.
- **The fix.** exe_v46m takes a slot just above the runner's own frame (the caller's stack), else a heap pointer as
  before.

`acmd_ext_test.py`'s `fighter_thread_tests` runs the game's own fighter step (`0x02E40B90` -> `0x02E408B8` -> the
motion step -> the agent runner `0x02C2986C` -> the interpreter) with the stack where Cemu has it. On exe_v46l the
thread is registered and never runs (the in-game symptom). On exe_v46m it runs once a frame.

**The fighter's frame, as the game runs it.** The fighter update `0x02E24270` calls `0x02E40B90` once per frame:

- It is gated by the global at `[0x102F6C04]`. With its byte `+8` set and its mode `+0` not 2, the whole fighter
  frame is skipped, and `0x02E40B24` runs only the status agent. A thread waits on those frames, as the script does.
- Otherwise `0x02E408B8` runs, and the thread runner comes first, at its entry. Then, in order:
  1. if not in hitlag (StopModule `+0x10`), the motion modules;
  2. the queued status changes (StatusModule vt `+0x16C`);
  3. the game script, through the motion step `[acc +0x44]` -> `0x02E87428` -> `0x02C5F3BC`;
  4. the second agent `[acc +0xA0]` -> `0x02C2986C`;
  5. the MSC status agent.
- A second entry, `0x02E40C4C` (a vtable slot, `r4 = [r3 +0x28]`, a heap holder), reaches the same step.

So a thread runs exactly when the script's frame comes round:
- once per fighter update, before that frame's status change and script;
- during hitlag only with Flags 1;
- not on skipped frames.

Its documented behaviour is unchanged.

**In-game check** (`threads_fix_v1`):
- `tools/thread_ingame_test_build.py` adds an up-taunt game script to Supamario. A thread logs every frame for 60
  frames and puts a star over his head every 10 frames.
- The diag executable (`tools/diag_godfist_cave.py` + `tools/diag_threads_cave.py`, built on exe_v46m) prints the
  thread's `S4GF k=8` lines. It also prints the first fighter steps' `S4TH ... r1=... old=0` lines, which show the
  stack and that exe_v46l's check would have skipped them.

## Input_Compare / Input_Get / Input_Set

Commands for a fighter's controller: check an input, copy it into a variable, or force it.

| Command | Does |
|---|---|
| `Input_Compare(Target, Input, Method, Value)` | Compares the input with Value. `True` / `Else` after it run on the result, like `Float_Var_Compare`. |
| `Input_Get(Target, Input, Variable)` | Stores the input in a float variable, e.g. `VAR_0` (`0x0F000300`). |
| `Input_Set(Target, Input, Value)` | Forces the input, as if the controller did it. |

**Target:** 0 self, 1 the nearest opponent, 2 the last fighter hit, 3–10 player slots 1–8, 12 the fighter this
attack hit (exe_v46k: nobody once the attack is over; "Targets" below). 11 isn't supported here.

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

## Buffer_Clear / Buffer_Set (exe_v46l, Sm4shCommand v1.4.13)

The game doesn't act on a press only on its frame: each press becomes commands (attack, forward tilt, up special,
jump, roll, ...: from the button and the stick that frame) that stay buffered 10 frames, and a fighter that can act
takes the first one still there. These two commands work on that buffer (docs/native-notes.md "The input buffer").

| Command | Does |
|---|---|
| `Buffer_Clear(Target, Inputs, Frames)` | empties the target's buffer. Inputs, bits: 1 attacks, 2 specials, 4 jump (button and tap), 8 shield / air dodge / spot dodge / rolls, 16 grab, 32 taunts, 64 stick commands (dash, turn) and flicks; 0 (or 128) everything, as the game's own clear at a status change (also this frame's presses and the per-button counters). Frames 0 / 1 now; N: now and after each of its next N - 1 input reads |
| `Buffer_Set(Target, Input, Direction, Frames)` | puts a press in the target's buffer, as if pressed at its next input read: Input 0 attack, 1 special, 2 jump, 3 shield, 4 grab, 5-7 taunts up / side / down; Direction 0 its own stick, 1 neutral, 2 forward, 3 back, 4 up, 5 down, + 8 flicked (a smash input, a tap jump, a roll); Frames 0 the game's window (10), 1-255 that long |

- Every target (12 included). Fighters only.
- **vs Input_Set:** Input_Set forces the controller (the status sees the press, a forced stick stays until stopped,
  Input 21 ignores the controller); Buffer_Set only fills the buffer (the press and stick are put in for the game's
  command builder that frame, then put back), and its Frames can keep the command longer than the window.
  Buffer_Clear empties the buffer but doesn't stop new presses (Input_Set 21 does); a held button isn't a new press.
- **From MSC:** `BUFFER_CLEAR` (`0x0F0003C9`): `WorkModule(0, slot, 0x0F0003C9)` clears player slot 1-8's buffer
  (0: this fighter), everything; slot + 16 x Inputs for some inputs.
- Unconfirmed: whether the buffer counts down while a fighter is frozen in hitstop (if not, a press made before a
  long freeze is still there at its end: clear it on release).

```
// a grab-like move lets go of the fighter it hit with nothing buffered, and eats its mashing for 5 frames
Buffer_Clear(Target=2, Inputs=0, Frames=5)
// buffer a jump for this fighter near the end of a move (kept 20 frames)
Buffer_Set(Target=0, Input=2, Direction=0, Frames=20)
// the fighter this attack hit down-smashes as soon as it can
Buffer_Set(Target=12, Input=0, Direction=13, Frames=40)
```

Code: `tools/acmd_ext_cave.py` `buf_code` (APC_CODE, after the position commands), `buf_handlers` (CODE2), the tables
at `0x04BD3B00` and the requests at `0x04BD3D00` (12 x 0x14); the control update's builder call `0x02E72B9C` ->
`buf_build`. Tested in unicorn (`tools/acmd_ext_test.py` `buf_tests`). Super God Fist clears its victim's buffer at
the catch and the hand-off (fighters/supamario/README.md).

## Time_Scale / Target_Time_Scale / Stage_Freeze (exe_v46n, Sm4shCommand v1.7.0)

**exe_v46u_threads (in game, training):** exe_v46n counted Frames, ran a speed-up's extra steps and cleaned up only
on one battle screen's frame (scene C, `0x0309BE54`), which training doesn't use: in training Time_Scale(0.5, 120)
never ended and Stage_Freeze(1, 180) never let go, not even after a training reset (threads / time tests v2). Now the
Frames are counted in the battle object world's first phase (`0x02BF2544`, run by every battle step), a speed-up also
repeats the battle sequence's frame (`0x02FF4DF8`), and the game's own "clear every slow-motion" (training reset,
restart, match start / end) ends Time_Scale and Stage_Freeze. docs/native-notes.md "Script binding on a motion change"
has the paths; tests `tools/ts_tick_test.py`, `tools/acmd_ext_test.py` ts_tests.

User: "a command to start and stop stage bg / objects like training mode's pause menu, a time manipulation command to
speed up time for all characters / stage / bg, and one more to specify time manipulation to a specific / hit
opponent". Each uses the game's own mechanism; docs/native-notes.md "Time: global slow, per-object slow, stage stop"
has the addresses.

| Command | Parameters | Does |
|---|---|---|
| `Time_Scale(Rate, Frames)` | Rate float; Frames int | Below 1: the game's global slow-motion at 1/N (Rate rounded to 1/N, N 2-20). 2-4: that many game steps a frame. 1 (or 0): normal. Frames: 0 until changed / the match ends, else that many screen frames. |
| `Target_Time_Scale(Target, Rate, Frames)` | Target int; Rate float; Frames int | One fighter (or this article) at 1/N speed, the Timer item's own slow (SlowModule slot 3); 1 or more: normal. Frames: its own frames, counted by the game; 0 until changed or it's set up again (a respawn). |
| `Stage_Freeze(On, Frames)` | On int; Frames int | 1: the stage stopped, no flash (camera_effects v3: the stage manager's update flag only); 2: the game's full stop (the stage told too: the screen goes white while it lasts; v2's On 1); 3: the Final Smash stop (2 + the effects the Final Smashes hide and pause); 0: it goes on. Frames: 0 until resumed / the match ends, else that many screen frames. |

**How the game does it (and what each one therefore affects):**

- **Global slow-motion** (`Time_Scale` below 1). The global slow manager `[0x102F7004]` holds 16 requests {active,
  rate} (`0x02FB35AC` makes one, `0x02FB3600` frees it). Its per-frame update (`0x02FB34C0`, in the battle step) gives
  the slowest to the speed controller (`0x02FFA140`: an integer rate 1-100). Each battle frame `0x02BFB97C` then fills
  the frame state at `[0x102F6C04]`:
  - `+8` set while the rate isn't 1;
  - `+4` 1/N;
  - `+0` a phase 0 / 1 / 2.

  Every object's step entry (fighters `0x02E40B90`, weapons, items, ...) runs only when `+8` is clear or the phase
  is 2, so fighters, items and projectiles move one frame in N. The stage's step is multiplied by 1/N (`0x03022994`
  in the stage manager's update `0x03164B80`), so the stage runs smoothly at 1/N. The game's own users are Final
  Smashes and SlowModule's "slow everything" (MSC SlowModule op 0); training's speed probably too.
  - The game's speed controller has no rate above 1 (`0x02FFA140` clamps it to 1-100).
- **Speed-up** (`Time_Scale` 2-4). The battle scene's update (`0x0309BE34`) runs the battle step `0x029108D0` once a
  frame, and its next callback (`0x0309BEF4`) runs the step's second half `0x0291100C` when `0x0334CCE8` says so.
  exe_v46n's hook on that call (`0x0309BE54`) runs (step, second half) Rate - 1 extra times first, then the frame's
  own step. That is everything at Rate times the speed, the match timer included.
  - Not while the match is paused or ending (battle state `+0x88` / `+0x8C` / `+0x8D`), nor when the scene's check
    says no.
- **Per-fighter slow** (`Target_Time_Scale`). Every object has a SlowModule (`[accessor +0xB8]`, vtable `0x101211D4`):
  - slots of `0x14` bytes at `+0x24`, each {frames, integer rate, 1/rate, owner, byte}, set by `0x0200CC14` (vt
    `+0x44`) and cleared by vt `+0x6C`;
  - its tick `0x0200CFC8` counts the frames and works out the object's rate `+8` (1/N, read by its motion step
    `0x02C5F3BC`: the animation and the scripts' frames) and a skip flag `+0xC` (its status, movement and the rest
    skip that frame).

  The Timer item uses slot 3 (`0x02E16A14(fighter, on, rate 2, 450 frames, owner)`); the game itself uses 0-3.
  The module's own reset (vt `+0x24`, from the object set-up `0x02BF57B0`) clears every slot, so a respawn ends
  it. The module has no rate above 1: one fighter can't be sped up. Animation_Rate_Set speeds up only the
  animation and scripts.
- **The white screen (camera_effects v3).** v2's Dr. Mario test (clip 1f7de3cf): Stage_Freeze(1, 120) on the up
  taunt's frame 2 turned the whole 3D picture white (the HUD intact) from clip frame 20 to 139, exactly its 120
  frames, and the picture came back in one frame when it let go; the black overlay started with it (killed at the
  same frame) was a small dark blob fading out over frames 140-144, so the white wasn't the overlay. The first white
  frame shows the stage washed out with the fighters still drawn, then everything. The earlier threads / time test v2
  (Stage_Freeze(1, 180) in training, where the freeze then never ended) had "a flash that didn't disappear";
  Supamario's Time Skip shows it too. What v2's Stage_Freeze did was the game's full stop `0x0316505C(manager, 1)`:
  `+0xD0` set **and** the stage told, `0x031427D0(stage, 0)`: for each stage object (stage vt `+0x284`'s list) its
  `+0x118` bit `0x40000` cleared, its model / effect handle (`+0xDC`) paused through the render managers
  (`0x03158994` -> `0x033534A4`) and its visibility set off (`0x032FF68C`), then stage vt `+0x214`. The game uses
  that stop for the Final Smashes (`0x02772658` and its copies: the stop, then `0x0334CA64(0x01080000, 0xFF080000,
  0, 0)` hiding and `0x0334CA30(..., 1)` pausing the effects of that key class) and the pause (`0x029C6C54` with
  stage vt `+0x28C` / `+0x294`), where a white stage never shows. **v3** (`tools/camera_effect_cave.py`, hooks on
  h_sfreeze's `bl 0x0316505C` at `0x04BD4334` and ts_stage_off's at `0x04BD4268`): On 1 sets `+0xD0` only (the
  update skipped, nothing told; resumed by the game's own call, whose `0x031427D0` sees the stage still active and
  does nothing but clear `+0xD0`); On 2 is the full stop; On 3 the full stop plus the Final Smashes' two effect calls
  (undone on resume). Which part of the full stop whites the screen out (the stage's objects paused / hidden, or
  something the stage does in vt `+0x214`) is what the v3 test's three freeze taunts tell apart.
  **Confirmed in game (v3's test, log a5622166):** On 1 freezes with no flash, On 2 and On 3 flash; the S4SF lines show
  each stop and resume (`+0xD0` 1 then 0) for all three modes.
- **Stage stop** (`Stage_Freeze`). The stage manager `[0x102F7020]` skips the stage's update (vtable `+0x2C` /
  `+0x4C`, and `+0x34` in its second half `0x03164EA4`) while its byte `+0xD0` is set. `0x0316505C(manager, on)`
  sets it, and tells the stage (`0x031427D0`). The game's own callers are some Final Smashes' code (`0x02772694`,
  `0x027C4ECC`, ...) and `0x029C6BE0` / `0x029C6790`. Objects a stage spawns (its enemies, items) are objects of their
  own: they keep moving.

**exe_v46n.** The handlers and `ts_scene` are in the text region grown again (`0x04BD4000`-`0x04BD6000`), with
`ts_data` (`0x04BD5F00`) holding:
- our slow request and the manager it's in;
- the speed-up's extra steps;
- the stage frozen and its manager;
- each one's Frames left.

`ts_scene` replaces the scene's `bl 0x029108D0`. Each frame it:
1. ends everything when the battle (`[0x102F732C]`) changed (a new match) or isn't running (`+0x88` 0);
2. runs the extra steps;
3. after the frame's step, counts the Frames down.

Time_Scale frees only its own request, so a Final Smash's slow-motion is untouched. Stage_Freeze resumes only the stage
manager it froze.

**Tested** (`acmd_ext_test.py` `ts_tests`, unicorn on exe_v46n). The handlers run as the interpreter calls them, on the
game's own functions:
- **The slow manager's request / free.** Requests of rate 2 / 3 / 20 for 0.5 / 0.3 / 0.01; the game's own request
  kept when ours is freed.
- **The scene's call** (step and second half stubbed, counting calls): 1 step a frame normally, 2 / 4 with Rate 2 /
  3.6, none extra while paused, back to 1 after Frames.
- **Frames and match changes.** The slow freed after its Frames, when the match isn't running, and at a new match.
- **The stage manager's stop.** Set; let go after Frames, at `Stage_Freeze(0)` and at a new match.
- **A SlowModule on the game's own vtable.** Slot 3 = {61 frames, rate 2, 0.5, no owner}. The game's tick then gives
  rate 0.5, skips 1 frame in 2 and counts down. Rate 1 or 2 clears it; Rate 0.25 with Frames 0 has no count.

Not provable offline, in the in-game test (`time_stage_commands_v1`):
- what the global slow / speed-up does to effects and sounds;
- how training's speed setting interacts;
- the stage look while stopped.

Examples:

```
// everything at double speed for 2 seconds
Time_Scale(Rate=2, Frames=120)
// the fighter this attack hits at half speed for 60 of its frames (while the hitbox is out)
Target_Time_Scale(Target=12, Rate=0.5, Frames=60)
// a cinematic hold: the stage stands still from the catch to the release
FRAME(Frames=46)
Stage_Freeze(On=1, Frames=0)
FRAME(Frames=94)
Stage_Freeze(On=0, Frames=0)
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
by the hitboxes with that Part number. It stays while the Part's hitboxes stay (a hitbox command on an ID that is
still out, same Part, keeps it), and the game's set_attack clears it when a hitbox ID that is not out is set again on
that Part (`0x02C08848`; in unicorn on exe_v46y_hold, with the per-ID set-up `0x02C108C4` stubbed: `Remove_All_Hitboxes`
then the same IDs -> the record gone; not confirmed in game, and Sm4shCommand's help still says it stays). A hitbox that stays out (a sweeping orb, a lingering box) needs this command to hit again; a loop that
re-makes its hitboxes each wave gets it anyway, and uses it to be sure (the port pipeline's holding multi-hits, Byleth
v18).

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
| 12 | the fighter this attack hit (exe_v46k): the current attack's newest hit record only, **no fallback**: before the attack hits and once it is over it is nobody |

1, 2, 11 and 12 are worked out from a fighter's own script (from an article's, they find nobody: the command does
nothing / reads 0). A target that isn't there: nothing happens, reads give 0.

**Target 12 vs 2.** Target 2 falls back, once the attack's hit records are gone, to a fighter whose last attacker
(int `0x10000065`) is this one. That int is also the game's KO credit, so it can't be cleared, and target 2 goes on
meaning that fighter for the rest of the match. Target 12 is the same record walk without the fallback (exe_v46k):
use it when acting on a fighter this attack didn't hit would be wrong (a follow-up that should only happen on a hit).
Both read the attack's records, which the hit makes after the script runs: on the hitbox's own frame nobody is hit
yet. Target 12 works in every command that takes a Target (and the input commands, and `Last_Hit_Get` Which 2), and
has its own variables, `ATKHIT_...` (`0x0F0002C8`-`0x0F0002FF`, docs/position-variables.md). Targets 0-11 and their
variables are unchanged.

```
FRAME(Frames=7)
Status_Set(Target=12, Status=0x5D)                         // dizzy, only if this attack hit someone
Hitstop_Set(Target=2, Frames=8, Shake=1)                   // the last fighter hit: someone even when this attack missed
```

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
- Motion numbers are per fighter (Sm4shCommand's View > Show Animation IDs, in hex; a plain number in a script is
  decimal, so `Motion=42` is `0x2A`). Kinds 0x000-0x210 are common to every fighter (0x24 Fall, 0x2A FallSpecial,
  0x2D LandingFallSpecial, ...; `tools/mtable.py`). The status keeps running and may play its own motion again, or
  end when the new motion ends (Link's AirCatch goes to Fall then).
- **`Motion_Set` on the fighter itself ends the script it is in.** The game binds the new motion's game /
  expression scripts the moment the motion changes (its rule for every motion change, MSC's too:
  0x027608B0 -> 0x02BEE560), so nothing after the `Motion_Set` runs; the new motion's game script starts from its
  beginning on the next frame. Put what must still happen before it (a `Rate` in the `Motion_Set` itself instead
  of a `Set_Frame_Duration` after it). exe_v46j: if the motion change ran the new script at once (its frame sync,
  0x02760EB0), exe_v40-v46i's handler stepped 5 words into the *new* script and the interpreter went on reading it
  from there; now the old script stops cleanly and the new one is left as the game set it.
- To be in another *state* (helpless special fall, a landing, ...), change the status (`Status_Set`), not the
  animation: the status plays its own motion and lands, acts and ends as that state does.
- A grounded fighter moved up may snap back or fall, as with MSC's `PostureModule(3, ...)`.

```
Rotation_Set(Target=0, X=0, Y=0, Z=45)                     // this projectile, tilted 45 degrees
Motion_Set(Target=0, Motion=0x5F, Frame=10, Rate=0.5)      // motion 0x5F from frame 10, half speed
Position_Get(Target=1, Axis=1, Variable=VAR_0)             // VAR_0 = the nearest opponent's Y
```

Fox, any move's game script: from frame 20 play FallSpecial (0x2A, common) at half speed. Nothing after the
`Motion_Set` runs (FallSpecial's own script takes over), and the move's status still decides when it ends:

```
FRAME(Frames=20)
Motion_Set(Target=0, Motion=0x2A, Frame=0, Rate=0.5)
```

Link's AirCatch (Zair), helpless from frame 11: that is the SpecialFall *status* (0x10), which plays FallSpecial
itself, can't act until it lands, lands with LandingFallSpecial (status 0x19), and on leaving AirCatch the hookshot
is put away:

```
FRAME(Frames=11)
Remove_All_Hitboxes()
Status_Set(Target=0, Status=0x10)
```

### Position_Place / Position_Offset_Get (exe_v46k, Sm4shCommand v1.4.12)

What the position variables (`POS_...`, `..._OFFSET_X`, docs/position-variables.md) do, as commands, for every target
(12 included). The variables and `Position_Get` / `Position_Set` keep working as before.

`Position_Place(Target, Relative, Fwd, Up, Depth, Axes, Frames, Collision)` puts a fighter (or this object)
somewhere:

| Parameter | Values |
|---|---|
| Relative | 0 the stage: Fwd / Up / Depth are the world X / Y / Z. 1 this object: the target goes to this object + Fwd along this object's facing (in front +), Up, Depth (the `..._OFFSET_` writes). 2 the target itself: it moves by Fwd along its own facing, Up, Depth (`POS_SELF_MOVE_`, `Position_Set` Mode 1). 3 this object goes to the target + Fwd along this object's facing, Up, Depth (`POS_SELF_OFFSET_`; Fwd 15 when facing it = behind it) |
| Axes | bits 1 X, 2 Y, 4 Z; 0 = all three. The others keep the placed one's value (1: sideways only, keeps its height) |
| Frames | 0 / 1 once, now. N >= 2: now and again every frame after this object's script (its frame step, not in its hitlag), N frames in all, worked out again each time (it follows this object). -1: every frame until this object's status changes |
| Collision | 0 the placed one's stage collision as it is. 1 off while held (`GroundModule(0x2710, 0)` every frame: through floors and walls, as a grabbed fighter), back to air (5) when the hold ends; with Frames 0 / 1 it stays off. 2 off and left off |

A hold ends early when this object's status changes (the move ends, it's hit), or this object or the placed one is set
up again (a KO); a new `Position_Place` of the same target from this object replaces it. 16 holds at a time in all
(more: placed once). The placement is `PostureModule(3, x, y, z)` on the placed one, as `Position_Set`.

`Position_Offset_Get(Target, Axis, RelativeTo, Variable)` reads where it is:

| RelativeTo | Axis 0 / 1 / 2 | Axis 3 |
|---|---|---|
| 0 the stage | its world X / Y / Z (`Position_Get`) | its facing (1 right, -1 left) |
| 1 target - this object | X along this object's facing (+ = it is in front), Y (+ = above), Z (the `..._OFFSET_` reads) | the X/Y distance (`POS_OPP_DIST`) |
| 2 this object - target | X along this object's facing, Y, Z (`POS_SELF_OFFSET_`) | the distance |
| 3 this object - target, X along the target's facing | + = this object is in front of the target, - = behind its back; Y, Z | the distance |

No such target: the variable gets 0. Gotchas: it's a teleport (no collision on the way); a grounded fighter moved up
may be snapped back or put in a fall by its status on the next frame (hold it, or put it in the air); the placed
fighter's own speed still moves it on its own frame between placements; Relative 1 / 3 use this object's facing,
2 the target's.

```
// a grab-like hit: once it has hit, hold the fighter this attack hit 12 in front and 5 up for 10 frames
FRAME(Frames=7)
Position_Place(Target=12, Relative=1, Fwd=12, Up=5, Depth=0, Axes=0, Frames=10, Collision=1)
// pull the nearest opponent to 8 in front, sideways only
Position_Place(Target=1, Relative=1, Fwd=8, Up=0, Depth=0, Axes=1, Frames=0, Collision=0)
// player 2 (Target 4): 3 up from where it is
Position_Place(Target=4, Relative=2, Fwd=0, Up=3, Depth=0, Axes=0, Frames=0, Collision=0)
// a backstab check: VAR_1 < 0 when this fighter is behind the opponent's back
Position_Offset_Get(Target=1, Axis=0, RelativeTo=3, Variable=VAR_1)
```

Code: `tools/acmd_ext_cave.py` `apc_code` (APC_CODE `0x04B7B000`-`0x04B7C000`, position_vars_cave.py's grown text:
its EXT_REGIONS stop at `0x04B7AE00`): the handlers, `apc_apply`, the holds `apc_tab` (16 x 0x30) re-applied from
the frame hook (`FRAME_HOOK` -> `apc_fhook` -> `hv_fhook`) and dropped on an object's set-up (`WM_RESET` ->
`apc_wmreset` -> `hv_wmreset`). Tested in unicorn (`tools/acmd_ext_test.py` `apc_tests`).

## Last_Hit_Get / Target_Slot_Get

| Command | Does |
|---|---|
| `Last_Hit_Get(Which, Variable)` | Which 0: the player slot (1-8) of the last fighter this one hit; 1: of the last fighter that hit this one; 2 (exe_v46k): of the fighter this attack hit (0 before the hit and once the attack is over). 0 = none |
| `Target_Slot_Get(Target, Variable)` | the player slot (1-8) of any target (the nearest opponent, ...); 0 = none |

The same fighters are Target 2, 11 and 12 of the other commands, so a move can act on them directly:

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
| `Reset` | optional (exe_v46w, Sm4shCommand v1.7.4): the events that put the variable back to `Initial`, bits: 1 KO, 2 landing, 4 ledge grab, 8 hit (a number 0–15, or names joined by `\|`: `Reset=landing\|ledge`). Left out or 0: New_Var exactly as before. Kept in bits 8–11 of the Scope word; shown only when not 0. "Variable resets" below. |

- **Storage:** each object (fighter or article) has 64 of them, apart from its `VAR_0`–`VAR_31` / `TIMER_0`–`TIMER_15`
  (which work as before) and from every other object's. They live with the object's `VAR_n` (the same 48-object
  table), read 0 until set, and are cleared with them.
- **Int and float both work.** The value is kept as a float: the int commands and ops (`SET_INT`, `ADD_INT`,
  `INC_INT`, `Int_Var_Compare`, MSC's `WorkModule` int ops) read it cut to a whole number and write a whole number,
  the float ones read and write the float. (`VAR_n` stays float-only.) Whole numbers are exact up to 16,777,216.
- **MSC:** `WorkModuleF(0, 0x0F000380 + slot)` reads one, `WorkModule(6, 0x0F000380 + slot)` as an int;
  `WorkModule(0 / 7, value, ID)` write it. Give the variable a fixed `Slot` for this. MSC needs no `New_Var`: an
  undeclared slot reads 0 until written and keeps what is written (Kirby's Hero copy keeps its state in slots
  0x39B-0x3BF this way); `New_Var` only sets the starting value and the int type.
- **IDs:** `0x0F000380`–`0x0F0003BF`. `0x0F0003C0`–`0x0F0003C8` are the stick angles and rotation (exe_v43, "Variables in Extra hitboxes"); `0x0F0003C9` `BUFFER_CLEAR` (exe_v46l); `0x0F0003CA`–`3CD` the resets' MSC selection (exe_v46w, "Variable resets"); `0x0F0003D0`–`3DA` Line_Test's (exe_v46v_line); the rest still read 0.

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

## Variable resets (exe_v46w_vars, Sm4shCommand v1.7.4)

A variable can go back to a value by itself when something happens to the object that owns it: `New_Var`'s `Reset`
(back to its `Initial`) and `Var_Reset_Set(Variable, Reset, Value, Owner)` (any variable, any value). The game does it
where it handles the event, whatever status or move the fighter is in, so a script doesn't have to watch for it.
(`tools/var_reset_cave.py`; `New_Var(... Reset=0)` and every old script compile to the same words as before and do the
same in game.)

| Bit | Event | When (the game's own place, docs/native-notes.md "Variable resets") |
|---|---|---|
| 1 | KO | its Dead status starts (any KO: blast zone, star, stamina); if that never came, the respawn's set-up. Once per KO: the reset keeps its other bits |
| 2 | landing | its situation goes from air to ground (every landing: a normal one, a landing in hitstun, a tech, the special-fall landing) |
| 4 | ledge grab | it enters CliffCatchMove / CliffCatch, or a tether's AirCatchHit / AirCatchHang (once per grab) |
| 8 | hit | a hit takes effect on it: a reaction (flinch, hitstun, launch). Not a shielded hit, not one its armor (super / heavy armor, knockback under its threshold) absorbs, not one while it's invincible / intangible, not a counter: the damage reaction decision Gravity_Set already uses ("no reaction" = not a hit here) |

- **Owner:** the events are a fighter's. An article's (projectile's) resets are kept but never fire.
- **The reset** is a write of the value through the owner's WorkModule: exactly `SET_FLOAT(Value, Variable)` in the
  owner's script at that moment (an int New_Var gets a whole number; an input / state variable acts on its target).
- **`Var_Reset_Set(Variable, Reset, Value, Owner)`:** Owner 0 this object, or a target as the other commands' (1 the
  nearest opponent, 2 the last fighter hit, 3–10 player slots 1–8, 11 the last attacker, 12 the fighter this attack
  hit): the reset goes on that fighter, its Variable as that fighter sees it (Owner 4 + `VAR_24`: player 2's own
  `VAR_24`; Owner 12 + `SELF_INPUT_OFF`: the hit fighter's controller). `Reset=0` removes it.
- **New_Var:** every run sets (or with Reset 0 removes) its variable's reset, Scope object or move: put it at the top of
  a script that runs.
- **Lifetime:** a reset stays until changed / removed, or until the owner is set up again (a respawn, a projectile's
  next shot), as the variables themselves. 31 per object, 48 objects (round robin past that).
- **MSC:** `WorkModule(0, index, 0x0F0003CA)` (`VAR_RESET_ID`: the variable `0x0F000000 + index`, e.g. `0x300` for
  `VAR_0`, `0x115` `SELF_INPUT_OFF`: an index keeps the float exact), `0x0F0003CB` (`VAR_RESET_VALUE`), `0x0F0003CC`
  (`VAR_RESET_OWNER`, a target), then `WorkModule(0, mask, 0x0F0003CD)` (`VAR_RESET`) sets it; reading `VAR_RESET` gives
  the picked variable's mask. On an older exe these read 0 and writes do nothing.
- **Needs** exe_v46w (exe_v46w_vars, or exe_v46w_vars_line with Byleth v9's Line_Test). An older exe can't load a
  script with `Var_Reset_Set`; it reads a New_Var with `Reset` as Scope object (no resets).

Examples (Sm4shCommand's View > Commands has them, every one compiled and round-tripped):

```
// a combo counter back to 0 whenever the fighter lands
New_Var(Name=combo, Type=int, Initial=0, Scope=object, Reset=landing)
// a once-per-airtime move: the flag back to 0 on landing or a ledge grab
New_Var(Name=air_used, Type=int, Initial=0, Scope=object, Reset=landing|ledge)
// a power-up for the stock, gone with a KO
New_Var(Name=buff, Type=float, Initial=1, Scope=object, Reset=KO)
// a stored charge lost when hit
New_Var(Name=stored, Type=int, Initial=0, Scope=object, Reset=hit)
// any variable: VAR_0 back to 0 on landing; the hit fighter's controller back on when it is hit or KO'd, and when
// this fighter is KO'd (its own reset on the hit fighter's input-off as it sees it)
Var_Reset_Set(Variable=VAR_0, Reset=2, Value=0, Owner=0)
Var_Reset_Set(Variable=SELF_INPUT_OFF, Reset=9, Value=0, Owner=12)
Var_Reset_Set(Variable=LASTHIT_INPUT_OFF, Reset=1, Value=0, Owner=0)
```

Supamario's Sledgehammer / Super God Fist lockouts use these from MSC (fighters/supamario/README.md "Sledgehammer v5").

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
| `0x0F0003C0`–`3C5` | `STICK_ANGLE`, `STICK_ANGLE_RAW`, `STICK_LEN`, `CSTICK_ANGLE`, `CSTICK_ANGLE_RAW`, `CSTICK_LEN` | the sticks' angle in degrees (along the facing / on screen) and how far they're pushed (exe_v43; "Variables in Extra hitboxes" above) | — |
| `0x0F0003C6`–`3C8` | `ROT_X`, `ROT_Y`, `ROT_Z` | the object's rotation in degrees (as `Rotation_Get`; exe_v43) | — |
| `0x0F000340`–`37F` | `SLOT1_SHARED_0`–`SLOT8_SHARED_7` | `VAR_24`–`VAR_31` of the fighter in that player slot (below) | set it |
| `0x0F000380`–`3BF` | your `New_Var` names (slots 0–63; exe_v40) | the value (int or float commands) | set it (an int one keeps whole numbers) |
| `0x0F0003CA`–`3CD` | `VAR_RESET_ID`, `VAR_RESET_VALUE`, `VAR_RESET_OWNER`, `VAR_RESET` (exe_v46w) | the selection; `VAR_RESET`: the picked variable's reset mask | pick a variable (its index), its value, its owner; `VAR_RESET` sets its reset ("Variable resets") |

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

## Line_Test (exe_v46v_line: `tools/line_test_cave.py`)

`Line_Test(Space, X0, Y0, X1, Y1, Floors, Distance, HitX, HitY, Kind)` follows the segment (X0, Y0) -> (X1, Y1) and
stores what it first meets of the stage: `Distance` (from the start; the whole length when nothing), `HitX` / `HitY`
(the point; the end when nothing), `Kind` (0 nothing, 1 floor: the line's normal Y >= 0.6, 3 ceiling: <= -0.6, 2 a
wall: anything between). `Space` 0: relative to this object (X forward along its facing, Y up, from its position; the
results the same way), 1: world. `Floors` 1 leaves the passable (drop-through) platforms out. A variable parameter of 0
stores nothing. Any object: a fighter, an article, a projectile.

The game's own test: GroundModule (accessor `+0x2C`) ray_check with a normal, `0x02C39FB4(GM, from, dir, out, normal,
all)` (the first line the segment meets: `0x02D4CD68` over every line, `0x02D4E724` with mask `0x102000` for `all` 0),
the one its ledge / ground checks use (six GroundModule vtables).

**MSC (and scripts with points from variables):** `LINE_X0` / `LINE_Y0` / `LINE_X1` / `LINE_Y1` (`0x0F0003D0`-`3D3`,
write), then `LINE_TEST` (`0x0F0003D4`) = Space + 2 x Floors runs it; read `LINE_TEST` (1 met / 0), `LINE_DIST`
(`3D5`), `LINE_HIT_X` / `_Y` (`3D6` / `3D7`), `LINE_KIND` (`3D8`), `LINE_NX` / `LINE_NY` (`3D9` / `3DA`: the line's
normal, X along the facing in Space 0). Per object (32 objects at a time), kept until its next test.

```
// MSC: from the hand to a point 60 up, 20 ahead, platforms left out
WorkModule(0, 5.5f, 0x0f0003d0); WorkModule(0, 20.5f, 0x0f0003d1);
WorkModule(0, 25.0f, 0x0f0003d2); WorkModule(0, 80.0f, 0x0f0003d3);
WorkModule(0, 2.0f, 0x0f0003d4);
if (WorkModuleF(0, 0x0f0003d4) != 0.0f && WorkModuleF(0, 0x0f0003d8) == 2.0f) { /* a wall at LINE_HIT_X / _Y */ }
```

Used by Byleth's up special (the sword's tip stops at the first wall / ground and latches on a wall) and his max arrow
(its line hitbox and beam cut at the first ground: `Line_Test(0, 0, 0, 300, 0, 1, VAR_0, 0, 0, 0)` then the hitbox /
beam in 10-unit steps by VAR_0). Tested by `tools/line_test_test.py` (unicorn: the command tables, both loaders, the
handler, the variables through the game's WorkModule; the ray check stubbed with a wall and a floor). Not in the Hitbox
Viewer (the stage isn't there). The game script's command and its variables need the executable: a script with it
doesn't load on an older one (port_check X6).

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
- **Variable resets (exe_v46w):** `tools/var_reset_cave.py`, its own region (`0x04BD8000`-`0x04BE0000`): per-owner
  lists keyed by the WorkModule; hooks on the status change (KO, ledge), the fighters' set_situation (landing), the
  damage reaction decision (hit), the object set-up, New_Var's handler and the command tables' fallbacks. Details:
  `docs/native-notes.md`, "Variable resets".
- **Gravity_Set:** a 16-entry table keyed by the fighter's module accessor (`0x04BD3E00`, its code from
  `0x04BD3600`, in New_Var's grown region) and three hooks: the gravity energy's update (entry: its values swapped
  in; exit: the energy's own put back), the damage reaction decision (a hit that takes effect ends it) and, through
  Leave_Ground_Cancel's status change hook, the status change. Details: `docs/native-notes.md`, "Gravity_Set".
- Addresses: `docs/native-notes.md`, "New ACMD commands".

## Hitbox_Hold (exe_v46y_hold, Sm4shCommand v1.7.5)

`Hitbox_Hold(ID, Mode)`, after a hitbox command (same frame), makes that hitbox's hits keep the victim where it is: the
launch speed the hit gives (knockback x 0.03 along the angle) is 0. Damage, hitstun (an Extra hitbox's HitstunMul
too), hitlag, SDI, the reaction animation, the sound and effect are the hit's own.

| Mode | |
|---|---|
| 0 | off (the game's knockback travel) |
| 1 | ground hold: a victim on the ground that the hit doesn't launch upward (361 under 60 knockback: 0 degrees; 0 / 180; downward) stays; upward launches and victims in the air go as normal. The rapid-jab setting. |
| 2 | always: no victim moves, ground or air (gravity still acts; a big hit still tumbles in place) |

- **ID**: the hitbox's ID (Smash 4 keeps one hitbox per ID; Part doesn't pick one). -1: every hitbox ID of the object.
- **Lifetime**: it belongs to the hitbox. The next hitbox command with that ID starts without it; removing the hitboxes
  takes it away. A loop that remakes its hitboxes gives Hitbox_Hold again after each. Change_Hitbox_Damage / _Size keep it.
- **Not held**: the victim's own movement, SDI, slopes, pushing; shield pushback (a shielded hit is unchanged).
- **The port pipeline** (`tools/ultimate_acmd.py`, the default since rapid_setoff v1): every Ultimate hit with
  `ATTACK_SETOFF_KIND_OFF`, angle 361, no set knockback, KBG and BKB 30 or less and damage (a rapid-jab loop) keeps 361
  and gets `Hitbox_Hold(ID, 1)`. Since Byleth v18 (HOLD_WAVE_CLEAR) each such wave also starts with
  `Hit_Log_Clear(Part)` and its hits are Extra hitboxes with Ultimate's hitlag as fixed frames for both sides
  (HitstopFrames / SelfHitstopFrames = `ultimate_acmd.ult_hitlag`; `port_check` S30). v17's angle-80 workaround only with `--hold-angle` (port.json `"rapid_hold": "angle"`),
  for an executable without the cave. `port_check` S28 / X8.
- **What Ultimate's setoff is** (read from its ExeFS, docs/native-notes.md "Hitbox hold"): the clank kind (ON clanks
  and rebounds, OFF clanks without being cancelled, THRU never clanks, NO_STOP clanks with no clank hitlag), which
  Smash 4's Clang / Rebound already carry. It doesn't move or hold the victim; this command is the Smash 4 setting that
  keeps a rapid jab's victim in reach.

```
FRAME(Frames=2)
Extra_Special_Hitbox(ID=0, ..., Damage=0.4, Angle=361, KBG=10, FKB=0, BKB=12, ..., HitstunMul=-3, ...)
Hitbox_Hold(ID=0, Mode=1)
WAIT(Frames=1)
Remove_All_Hitboxes()
```

Sm4shCommand has four complete examples (a rapid-jab loop hit, a holding drill, the same hit without it, every hitbox
at once). How it works in the executable: docs/native-notes.md "Hitbox hold"; test `tools/hitbox_hold_test.py`.

## Effect_Camera (exe_v46z_camfx, Sm4shCommand v1.7.6)

`Effect_Camera(Graphic, X, Y, Z, XRot, YRot, ZRot, Size, Mode, Frames, Flags)` starts an effect (the fighter's bank or
the common one, by the EFFECT commands' ID) attached to the camera: every frame, just before the effects go to the
particle system, its matrix is set from the camera the game is drawing with (eye, target, up, FOV; the camera shake
included). Xenoverse 2's camera-attached screen effects (BTL_CMN 108 HIT_DmgGrs2, the time-stop darkening with glass
shattering) need it; Smash 4 had no way to place an effect on the screen.

| Parameter | |
|---|---|
| Graphic | the effect's ID (0x1000000 + n common, 0x3KK0000 + n the fighter's bank) |
| X, Y | from the screen's centre, right / up. Mode 0 / 2: units; Mode 1: half the screen's height (Y 1 the top edge, X 1.78 the right edge of a 16:9 screen) |
| Z | distance in front of the eye (units). At least near + 1 (3; closer is put there). Mode 1: 0 or less is 20 |
| XRot, YRot, ZRot | its turn in degrees, Rz Ry Rx as the EFFECT commands, in camera space (Mode 2: world space). At 0 its X is the screen's right, its Y up, its Z toward the viewer: a flat XY effect faces the camera |
| Size | its scale; Mode 1: one effect unit = Size half screen heights (a quad 2 units across, -1 to 1, at Size 1 covers the screen's height, at 1.78 its width). A bank particle of scale W (its full width) is W x Size / 2 screen heights wide in Mode 1, W x Size units in Mode 0 / 2 (the screen is ~0.75 x Z units tall). Bank effects are 10-40 units wide: Mode 1 sizes 0.02-0.2 |
| Mode | 0 follow the camera (place and turn); 1 fixed to the screen (as 0, and X / Y / Size scaled with the distance x tan(FOV / 2): the same part of the screen when the camera zooms or moves); 2 position only (moves with the camera, keeps the world's turn). Other values: 0 |
| Frames | 0: until it ends by itself or Terminate_Graphic_Effect; N > 0: faded out after N frames (it stays attached while it fades) |
| Flags | 1: unslowed (Time_Scale's slow-motion and the owner's hitlag / Target_Time_Scale don't slow its animation); other bits reserved |

- **It is the object's own effect** (requested through its EffectModule, as MSC's world-placed effects are):
  `Terminate_Graphic_Effect(Graphic=...)` ends it, `LAST_EFFECT_SET_COLOR` / `_ALPHA` / `_RATE` right after it apply to
  it, it hides with its owner's model. A status change doesn't end it: give a looping effect Frames or a Terminate.
- **Time:** it keeps drawing and following the camera through Stage_Freeze, Time_Scale and Target_Time_Scale (its matrix
  is set in the effects' own frame pass, every displayed frame; Stage_Freeze stops only the stage). Its animation plays at
  the match's slow-motion rate unless Flags=1. Frames counts displayed frames.
- **Draw order / depth:** a 3D effect: under the HUD (damage panels, timer). At 10-30 units it is in front of the
  fighters and the stage (80-300 away); other effects drawn after it, or closer to the camera, can show over it.
- **Darkening:** an alpha-blended effect (ptcl blend 0) coloured black with an alpha. An additive one can't darken.
- **Colour (camera_effects v6, Sm4shCommand v1.7.11):** `LAST_EFFECT_SET_COLOR`'s Red / Green / Blue are 0-255 (its
  handler divides by 255, vt `+0x27C`; vanilla scripts pass 20-255, some over 255 to brighten) and multiply the
  effect's own colours; `LAST_EFFECT_SET_ALPHA` is in percent. v5's test quad is white (colour 0 keys 1.0, a white
  texture, combiner colour 0 x texture), so it shows the colour as given; v5's test passed (0, 0.35, 1) for blue,
  i.e. under 1/255, black: the user's "the squares aren't blue". Black darkenings work at any scale (0 is 0). v6
  passes (0, 90, 255); the command and the executable are unchanged (exe_v46z_camfx5).
- **Sizes (camera_effects v2, Sm4shCommand v1.7.7's help):** v1's in-game test blew the screen out to white: it used
  common 0x1000042 as "stars" (the tooltip's label), which is PtcCommonThunder, additive flashes up to 40 units wide,
  looping, at Mode 1 Size 0.08 = 1.6 screen heights. The command's maths was right; bank effects are simply big. Check an
  ID's emitters (blend, scale) and size it with W x Size / 2 screen heights (Mode 1). Nothing in the command changed.
- **Emitters that don't follow** (ptcl 0x310 = 1 / 2) leave their particles in the world where they were emitted: they
  stay behind when the camera moves. Overlays want follow type 0 (`tools/ptcl.py` sets it).
- **Several views:** it follows the TV view's camera (the effect camera table's first entry). A GamePad / second Cemu
  view of the battle draws it at the same place in the world.
- **Limits:** 16 camera effects at once (a 17th fades the oldest out); nothing outside a match (no camera).

```
// a time stop: the stage freezes for 90 frames, the screen darkens (the fighter's darkening quad, -1 to 1, fixed
// to the screen at Size 1.9: a 16:9 screen is 1.78 half heights wide), black at 55 %, unslowed
FRAME(Frames=12)
Stage_Freeze(On=1, Frames=90)
Effect_Camera(Graphic=0x3410012, X=0, Y=0, Z=20, XRot=0, YRot=0, ZRot=0, Size=1.9, Mode=1, Frames=90, Flags=1)
LAST_EFFECT_SET_COLOR(Red=0, Green=0, Blue=0)
LAST_EFFECT_SET_ALPHA(Alpha=55)
// glass shattering in front of the camera as it ends (a one-shot burst, Mode 0, 25 in front)
FRAME(Frames=100)
Effect_Camera(Graphic=0x3410013, X=0, Y=0, Z=25, XRot=0, YRot=0, ZRot=15, Size=1.2, Mode=0, Frames=0, Flags=1)
```

- **camera_effects v3 (exe_v46z_camfx3, Sm4shCommand v1.7.8).** v2's in-game test (clip 1f7de3cf, Dr. Mario): the
  corner stars (Mode 1, X 1.4, Y 0.7) appeared 8-14 px each, up and right of the fighter, fixed in the world at about
  the stage's depth (they moved with the stage's platforms when the camera panned, about 30 px over 80 frames, where
  a screen-fixed effect moves 0), nothing at the corner; the black overlay showed only after the white freeze, as a
  small dark blob left of the centre fading out (frames 140-144); the ice smoke (Mode 0, Z 30) was centred and about
  0.75 screen heights across, as wanted. So the camera matrix wasn't what eft drew in Mode 1. v3 makes it win: eft is
  given the instance's matrix again right after the game's update of it (the calc pass's `bl 0x0334E0C8` at
  `0x032EFD7C` -> cf_upd, then `0x032FF744(inst + 0x20, inst + 0x50)`), the instance's position (`+0xC8`) and scale
  (`+0xB0`) hold the same place, and the camera manager's own snapshot is used when the effect camera table has no
  camera. The battle camera's near / far clips are fitted to the stage every frame (`0x02D27D74`, from the camera
  update `0x02D28B74`): a Z inside the near clip goes to near + 1 (Mode 1 keeps its screen place and size). The
  test-only diag executable logs, for each camera effect each frame (its first 30, then every 30th), the camera read
  (S4CC / S4CV / S4CN), the instance (S4CF: handle, flags, key, follow target, its bytes), its matrix (S4CM) and eft's
  emitter set's (S4CE: `+0x350`): docs/native-notes.md "Camera effects". Parameters unchanged; example 6 is the case
  v2 got wrong (a time stop's darkening staying on the screen while the camera pans).
- **camera_effects v4 (exe_v46z_camfx4, Sm4shCommand v1.7.9): the real cause.** v3's diag log had camera lines
  only, not one per-effect line: v3's re-give went to `inst + 0x20`, the effect's *model* (efc entries with a model:
  `0x0334DDA4`), which particle-only effects don't have (`0x032FF640` false). The particles' emitter set
  (`inst + 0x12C`) gets a matrix from the game only through `0x0334EEB0`: `cmpwi r26, 0` -> eft's `SetMtx`
  `0x04A4AFB8`, and r26 is set only when the update rebuilt the matrix from position / turn / scale (`0x0334E284`),
  turned it (billboard flags) or moved it (`+0x150`); the cave's flag `0x8000` skips the rebuild, so from v1 on the
  particles kept the matrix they were created with (the request's place, turn 0): fixed in the world, the centred
  ones looking right until the camera moved (v3's clips: the "square", a circle as its flash texture is round, stays
  in the world while the camera pans). v4: cf_upd gives `inst + 0x50` to the emitter set (`+0x12C`, alive: `+0x19A`,
  `+0x1D0` = `+0x130`, `+0x1DC` > 0) and its extra sets (`+0x158`, three at most) with eft's `SetMtx` before the game's
  update (the frame's emission) and after it, then to the model if there is one. The diag prints every Effect_Camera
  (S4CS: id, handle, instance, started or not, X / Y / Z) and each camera effect's first 30 frames then every 30th
  (S4CF / S4CM / S4CE: the emitter set's own matrix, `+0x1E4`), whatever its model.
- **camera_effects v5 (exe_v46z_camfx5, Sm4shCommand v1.7.10): the game's 2.5D depth squash.** v4's test (clips
  9a9b6ead / 200b18be, log bb4113b4): the squares (centre, full screen, the Mode 0 one at X 6, Y 3), the smoke followed
  the camera; the four corner stars (Mode 1, X +-1.4, Y +-0.7, Size 0.08) showed as two clusters of 8-14 px stars in a
  line about 0.25 half heights above the centre, about 100 px apart (where the corners are 1020 px apart and the stars,
  at 20 units, would be about 110 px each), staying put while the camera was still and drifting with the stage (a
  third of its motion) when it panned; the top-right-only stars likewise near the centre. Yet the log shows the stars'
  emitter sets holding the right corner matrices (S4CE's translation = S4CM's) and S4CF's last byte (`+0x1A3`) 1. The
  cause, in the game's code: the world request (and so Effect_Camera) sets the instance's byte `+0x1A3`, Smash's 2.5D
  mode, and the game's eft particle callback (`0x033508C0`, registered in the system's `+0xA68` table, run by eft's CPU
  particle calc `0x04A65480` on every CPU particle after it is placed) then moves each **CPU particle's** world Z to the
  plane `+0x11C` (0) + (Z - plane) x 0.07: harmless near the stage, but a particle 185 units out (20 in front of a camera
  at 205) lands at 13, on the stage, near the screen's centre and ten times smaller. The dizzy stars' emitters are CPU
  ones (complex emitters, flags without `0x00800000`); the square and the smoke are GPU emitters (flag `0x00800000`,
  moved by their vertex programs), which never run the callback: that is why only the stars were wrong. The same flag
  gives the emitter set emp1.z 0.07 (`+0x2CC`, `0x0334DC70`: the vertex programs skip the billboard matrix below 1) and
  squashes an effect model's depth (`0x0334EAAC`). v5 turns the squash off for camera effects: the instance's `+0x1A3`
  is cleared at the request and every frame, and each emitter set's emp1.z is eft's own 1.0 (billboards face the
  camera). **Every emitter type now works** (CPU and GPU particles, complex emitters, models); what still matters is
  the follow type (below) and the size. Unicorn: the game's callback run on a particle with and without `+0x1A3`, and on
  an Effect_Camera effect after the cave (`tools/camera_effect_test.py`, 92 checks). The diag's S4CE now prints the set's
  emp1.z and its translation from the right words (the SetMtx copy is at `+0x1E8`; v4 read one word early, which put
  m02 / m12 / m22 under "t"). Parameters unchanged; example 7 is the case v4 got wrong (CPU-particle stars in a corner).
- **Which effects work (v5):** any bank effect, CPU or GPU particles, with emitters that follow their set (ptcl `0x310` =
  0; `tools/ptcl.py` prints it). Follow types 1 / 2 still leave particles where they were emitted (a trail behind the
  camera's moves; fine for one-frame bursts). Size it for the screen: a particle of scale W is W x Size / 2 screen
  heights in Mode 1 (the common dizzy stars, scale 2.4-4, ring 8.6 units: Size 0.05 for stars 0.1 screen heights).
- Sm4shCommand (New Commands / Effects) has seven complete examples (the time-stop darkening, the glass-shatter burst, a
charge vignette, the common dizzy stars pinned to a corner (v1.7.7: was 0x1000042, the thunder), Mode 2 falling particles,
v1.7.10's four corners with CPU-particle stars, blue as 0-255 since v1.7.11) and the full help. The Hitbox Viewer
draws it in front of its own view (X / Y from the view's centre, Mode 1 in half the view's height; it has no game camera,
so Z changes nothing there) and lists it with the effects; Frames ends it there too. `port_check` X9 (ERROR): a script
using it with no executable carrying the cave. How it works: docs/native-notes.md "Camera effects"; tests
`tools/camera_effect_test.py` (unicorn), `tools/Sm4shCommand/new_var_test.cs`, `viewer_scripts_test.cs`.

## Screen_Invert (exe_v46z_inv, Sm4shCommand v1.7.12)

`Screen_Invert(Mode, Strength, Frames, FadeIn, FadeOut, Saturation, Brightness, Red, Green, Blue)` turns the 3D picture
into a photo-negative (Xenoverse 2's BPE 78 "Invert World Colors", Hit's Time Skip), then greys, darkens / brightens and
lifts it toward a colour, faded in and out. User: "Can you make a way for Smash 4 to invert the colors?"

| Parameter | |
|---|---|
| Mode | int: 1 start (or replace the one showing: one filter for the whole screen); 0 end it, over this command's FadeOut (0 at once) |
| Strength | float: the negative. 1 full (out = 1 - in), 0 none, between a blend: **0.5 is an even mid-grey** (0.3 / 0.7 a low-contrast picture / negative) |
| Frames | int: held this many frames once faded in, then out over FadeOut; 0 until Mode 0 / the match ends |
| FadeIn / FadeOut | int: frames (0 at once). A filter already showing fades from where it is |
| Saturation | float, after the negative: 1 kept, 0 grey (luma 0.299 / 0.587 / 0.114), above 1 stronger |
| Brightness | float, then a multiply: 1 kept |
| Red, Green, Blue | float, 0-255, then added (negative takes away). Brightness 1 - a with RGB = a x C mixes toward C by a |

Per channel (0-1): f(x) = Brightness x Sat(Strength x (1 - x) + (1 - Strength) x x) + RGB / 255; shown as
(1 - w) x + w f(x) while it fades (w 0 -> 1 over FadeIn, 1 -> 0 over FadeOut).

- **How:** Smash 4 copies its finished 3D picture through a 3x4 colour matrix every frame (shader/copy_color.nsh's
  colour-correct programs, uniform block `PostEffectSettings` / `correct_param[3]`), built each frame by the post-effect
  object from the parameters Screen_Tint sets. The patched executable composes the filter after that matrix just
  before it goes to the GPU, so nothing is drawn and a Screen_Tint showing at the same time is inverted with the rest
  (docs/native-notes.md "Screen colour").
- **Timing:** counted in the effects' frame, as Screen_Tint's own fades (runs through hitlag, Stage_Freeze, Time_Scale;
  stops while paused). Ends with the match, a restart and a training reset (the clear-all Time_Scale / Stage_Freeze use).
- **Whole picture:** the fighters are inverted too (XV2's stop keeps theirs: it inverts the world before drawing the
  characters; Smash draws both into one picture). The HUD isn't touched (drawn after the colour pass). Effects in the 3D
  picture, Effect_Camera overlays included, are inverted with it.
- **XV2's looks** (values fit to the user's clip b66e8a38, the background before / during the stop): the dark blue-grey
  stop = Strength 1, Saturation 0, Brightness 0.8, + (19, 37, 60) (the clip's sky (210, 228, 207) -> (47, 67, 91),
  floor (189, 195, 203) -> (67, 87, 110), the top (169, 211, 185) -> (69, 80, 105): 0.8 x the negative's luma +
  (19, 37, 60) gives each within 5 / 255); XV2's own shader
  (`NegaposiFilter_PS`, adam_shader's shader_default_ps.emz) is a plain `1 - rgb`, alpha kept, so the grey / blue part
  comes from what XV2 draws over and after it (the glass HIT_DmgGrs2, its fog / glare), which this folds into one
  filter. The white negative after the punch: Strength 1, Saturation 0.15, Brightness 0.6, + (102, 104, 110).
- **Not in the Hitbox Viewer.** `port_check` X10 (ERROR): a script using it with no executable carrying the cave.

```
// XV2's time stop: the stage freezes and the picture turns into a dark blue-grey negative until the punch
FRAME(Frames=12)
Stage_Freeze(On=1, Frames=0)
Screen_Invert(Mode=1, Strength=1, Frames=0, FadeIn=0, FadeOut=0, Saturation=0, Brightness=0.8, Red=19, Green=37, Blue=60)
FRAME(Frames=28)
Screen_Invert(Mode=0, Strength=0, Frames=0, FadeIn=0, FadeOut=0, Saturation=1, Brightness=1, Red=0, Green=0, Blue=0)
Stage_Freeze(On=0, Frames=0)
// a negative flash on a strong hit: 4 frames, out over 6
Screen_Invert(Mode=1, Strength=1, Frames=4, FadeIn=0, FadeOut=6, Saturation=1, Brightness=1, Red=0, Green=0, Blue=0)
// half strength faded in / out (the picture greys out and comes back)
Screen_Invert(Mode=1, Strength=0.5, Frames=60, FadeIn=20, FadeOut=20, Saturation=1, Brightness=1, Red=0, Green=0, Blue=0)
```

Tests: `tools/screen_invert_test.py` (unicorn: the command tables with every earlier cave's commands, the handler, the
tick through the game's screen-effect update, the lock with the matrix the game's lock sees, the clear; the builder's
paired-single matrix code run in a Python interpreter of its own words; the diag's lines), `new_var_test.cs` (the
command's words, round trip, group, every example). In game: `tools/screen_invert_ingame_test_build.py` (Dr. Mario's
taunts).

## Outline_Set (model_commands v1, exe_v46z_outline)

`Outline_Set(Target, Red, Green, Blue, Alpha, Tint, Frames, FadeIn, FadeOut, Flash)` puts a coloured glow on an object's
silhouette edges (a rim / fresnel light): Xenoverse 2's "Flashing White Body Outline" (BPE 85), a power-up's edge, a
mark on a fighter. Index 2400, 11 words, needs exe_v46z_outline (`tools/outline_cave.py`).

| Parameter | |
|---|---|
| Target | int: 0 this object, 1 nearest opponent, 2 last fighter hit, 3-10 slots 1-8, 11 last attacker, 12 the fighter this attack hit. One outline per object (a new one replaces it, fading from where it is) |
| Red, Green, Blue | float, 0-255: the colour |
| Alpha | float: strength, 255 = the colour at full at the very edge, up to 1020 (4x); **0 ends it** (over this command's FadeOut) |
| Tint | float, 0-255: the body tinted toward the colour too (the overlay's mix); **0 = edge only** |
| Frames | int: held once faded in, then out over FadeOut; 0 until Alpha 0, a KO, the match end or a training reset |
| FadeIn / FadeOut | int: frames (0 at once) |
| Flash | int: a pulse, one cycle every Flash frames (full, off, full; smooth); 0 steady |

- **How:** the fighter shaders' rim term is `(1 - N.V)^(fresnelParams.x + 1) x (material rim + g_fresnelOffset)`;
  g_fresnelOffset is in the model's own FB1 uniform block, which the game rebuilds for every model every frame. The
  executable adds the outline's colour x strength x fade there (and mixes the overlay colour, blinkColor, for Tint) just
  before the block goes to the GPU. No new draw (docs/native-notes.md "Outline").
- **Sharpness** is the material's (its NU_fresnelParams, exponents 2-4 on the fighters): there is no per-command power.
- Meshes whose shader has no g_fresnelOffset (the 0x...3063 / 0x...5061 rim family, unlit materials) don't glow; Dr.
  Mario's materials all do.
- Counted in the effects' frame (as Screen_Invert's): through hitlag and Stage_Freeze, not while paused.
- The Hitbox Viewer draws it on the model (Target 0: a rim on the edges seen edge-on, the tint) and lists it.
  `port_check` X11 (ERROR): a script using it with no executable carrying the cave.
- **v1.7.14 (exe_v46z_outline2):** unchanged, but it is a rim light: in game it stays inside the silhouette and reads as
  lighting. For a band of colour **outside** the silhouette use **Outline_Shell** (below); both can run on one object
  (the band round the body, the rim lighting its edges).

```
// a white edge glow for a time-stop move: 2 seconds, faded in over 4 frames, out over 10
Outline_Set(Target=0, Red=255, Green=255, Blue=255, Alpha=510, Tint=0, Frames=120, FadeIn=4, FadeOut=10, Flash=0)
// a red pulsing outline for a power-up (3 pulses a second, a light red tint), until ended
Outline_Set(Target=0, Red=255, Green=40, Blue=20, Alpha=400, Tint=40, Frames=0, FadeIn=6, FadeOut=0, Flash=20)
// ending it over 12 frames
Outline_Set(Target=0, Red=0, Green=0, Blue=0, Alpha=0, Tint=0, Frames=0, FadeIn=0, FadeOut=12, Flash=0)
// (v1.7.14) with Outline_Shell: XV2's white outline in full, the band outside and the rim inside, 2 seconds
Outline_Shell(Target=0, Red=255, Green=255, Blue=255, Alpha=255, Width=2.5, Frames=120, FadeIn=4, FadeOut=10, Flash=0, Blend=1)
Outline_Set(Target=0, Red=255, Green=255, Blue=255, Alpha=400, Tint=0, Frames=120, FadeIn=4, FadeOut=10, Flash=0)
```

## Mesh_Visibility (model_commands v1, exe_v46z_outline)

`Mesh_Visibility(Target, Mesh, Visible, Persist)` hides or shows one of an object's meshes by name, over the motion's
visibility animation and the visibility groups (Model_Changer). Index 2500, 5 words, needs exe_v46z_outline
(`tools/mesh_vis_cave.py`).

| Parameter | |
|---|---|
| Target | int: whose model (as Outline_Set's) |
| Mesh | int: the mesh's name in quotes, `Mesh="stethoscope_VIS_O_OBJ"` (Sm4shCommand stores its CRC32, exact case), or 0-255 an index (the game's mesh order: model.nud's meshes, each with all its polygons); **-1 ends every override of this object** |
| Visible | int: 0 hide, 1 show, 2 end this mesh's override |
| Persist | int: 0 until the motion (kind) changes, as vanilla visibility; 1 until changed, a KO, the match end or a training reset; **2 (exe_v46z_ui2): the mesh's own set state** (Visible 0 hidden, 1 shown, 2 follow the animation) written through the game's setter: no override entry, kept until written again |

- **How:** each mesh's visibility byte (set state: hidden / shown / follow the animation; the animation's bit) is forced
  while the override lasts; the game's own changes to the set state (visibility groups) are kept aside and come back when
  it ends (docs/native-notes.md "Mesh visibility").
- Sm4shCommand (v1.7.13) compiles any int parameter written as a quoted name to the name's CRC32; the script shows the
  hex number afterwards, which compiles the same.
- The Hitbox Viewer follows it (the Model parts tab: "hidden / shown by Mesh_Visibility"). `port_check` X12 (ERROR): a
  script using it with no executable carrying the cave.
- **v1.7.14 (exe_v46z_outline2, mesh visibility v2): meshes with several parts** (Smash Forge's Polygon_0, Polygon_1 ...
  under a mesh: HammerM2_O_OBJ, Dr. Mario's stethoscope and hair) change whole: every entry with the name, and every
  entry right after it that has no name of its own (a part of it), for the hide / show and the restore. By the game's
  code a mesh's entry already covers all its polygons (docs/native-notes.md "Mesh visibility", v2), so if a part still
  shows, the mesh may be in another model (an article's or a held item's: Target 0 in that article's script); the
  diag build's S4MH lines list every entry a command changed. Same words, v1 scripts unchanged.

- **Persist 2 (exe_v46z_ui2, `tools/supamario_ui_cave.py` hooks mesh_vis_cave's mv_apply):** the mesh's own set state
  (what a visibility group writes), written with the game's setter `0x034232FC(MI, mesh, Visible, 0)`: no entry in the
  32-entry override table, nothing ends it (motion changes, KOs, training resets keep it) until another Persist 2 (or a
  group) writes that mesh. For a look that lasts a stock (Supamario's Ultra Instinct: the cap off, the silver copies
  following their own visibility tracks); write the state back in Entry / Wait1. An older executable takes 2 as 1.

```
// a weapon hidden for one animation (back when the move ends)
Mesh_Visibility(Target=0, Mesh="sword_VIS_O_OBJ", Visible=0, Persist=0)
// hidden until shown again, then given back
Mesh_Visibility(Target=0, Mesh="sword_VIS_O_OBJ", Visible=0, Persist=1)
Mesh_Visibility(Target=0, Mesh="sword_VIS_O_OBJ", Visible=2, Persist=0)
// a hidden prop shown for this animation
Mesh_Visibility(Target=0, Mesh="Mario_Result_VIS_O_OBJ", Visible=1, Persist=0)
// (exe_v46z_ui2) the cap hidden for the rest of the stock, no override entry; given back on Entry
Mesh_Visibility(Target=0, Mesh="Mario_Hathead_VIS_O_OBJ", Visible=0, Persist=2)
Mesh_Visibility(Target=0, Mesh="Mario_Hathead_VIS_O_OBJ", Visible=2, Persist=2)
```

Tests: `tools/outline_test.py` / `tools/mesh_vis_test.py` (unicorn: the command tables with every earlier cave's
commands, the handlers, the ticks, the FB1 unlocks / the game's mesh setter, by-name setter and per-frame visibility,
the clear chain, the diag lines), `new_var_test.cs` (words, round trips, groups, every example), `hitbox_var_test.cs` (the
viewer's outline and mesh overrides). In game: `tools/model_commands_ingame_test_build.py` (Dr. Mario's taunts).

## Outline_Shell (model_commands v2, exe_v46z_outline2)

`Outline_Shell(Target, Red, Green, Blue, Alpha, Width, Frames, FadeIn, FadeOut, Flash, Blend)` draws a band of colour
**round an object's silhouette, outside it**: a real outline (Xenoverse 2's "Flashing White Body Outline", a power-up's
aura edge, a cel-shaded ink line). Index 2600, 12 words, needs exe_v46z_outline2 (`tools/outline_shell_cave.py`).

| Parameter | |
|---|---|
| Target | int: whose model (as Outline_Set's). One shell per object (a new one replaces it, growing from where it is) |
| Red, Green, Blue | float, 0-255: the band's colour |
| Alpha | float, 0-255: how solid (255 solid; with Blend 1 the colour added x Alpha / 255); **0 ends it** (over this command's FadeOut) |
| Width | float: the band's width. **> 0 pixels** of the 1280 x 720 picture (constant on screen: 1.5 thin, 3 a clear band, 6 thick); **< 0 game units** round the model (-0.3 to -1 on a fighter; grows with the zoom). Up to 64. The fades and the pulse scale it |
| Frames | int: held once grown in, then shrinks over FadeOut; 0 until Alpha 0, a KO, the match end or a training reset |
| FadeIn / FadeOut | int: frames (0 at once) |
| Flash | int: a pulse, one cycle every Flash frames (full width, none, full; smooth); 0 steady |
| Blend | int: 0 the colour over what is behind it; 1 added to it (a glow) |

- **How (an inverted hull):** each of the model's meshes is drawn a second time right after the game draws it, with the
  executable's own vertex / pixel programs: pushed out along its normals by Width, its front faces culled (only the back
  faces of the fattened copy show, round the edges), in the colour, depth-tested behind the body; the game's states are
  put back after each mesh. Which models: the model instance's own FB1 block carries the colour and width (the outline
  cave's FB1 hook) - docs/native-notes.md "Outline shell".
- An inverted hull also outlines a part in front of another (an arm across the body). It fades by width (growing /
  shrinking), not by transparency: the band is written to the depth buffer, so a see-through band (Alpha below 255)
  mixes with what was drawn before the fighter; use Alpha 255, Blend 1 for a glow, Blend 0 for a solid / black line.
- Only the meshes whose pixel program is a material one (the lit fighter shaders; every Dr. Mario mesh) get it;
  two-sided thin parts get it on the side facing away; Screen_Invert inverts it with the picture.
- Counted in the effects' frame (as Outline_Set): through hitlag and Stage_Freeze, not while paused.
- The Hitbox Viewer draws the band round the model's silhouette (outer edge only) and lists it. `port_check` X13
  (ERROR): a script using it with no executable carrying the cave.

```
// XV2's white outline for a time-stop move: 1.5 pixels, added, grown in over 4 frames, held 2 seconds, out over 10
Outline_Shell(Target=0, Red=255, Green=255, Blue=255, Alpha=255, Width=1.5, Frames=120, FadeIn=4, FadeOut=10, Flash=0, Blend=1)
// a red pulsing outline for a power-up (3 pulses a second), until ended
Outline_Shell(Target=0, Red=255, Green=30, Blue=20, Alpha=255, Width=3, Frames=0, FadeIn=6, FadeOut=0, Flash=20, Blend=1)
// ending it over 12 frames
Outline_Shell(Target=0, Red=0, Green=0, Blue=0, Alpha=0, Width=0, Frames=0, FadeIn=0, FadeOut=12, Flash=0, Blend=0)
// a black ink line in game units (thickens as the camera zooms in)
Outline_Shell(Target=0, Red=0, Green=0, Blue=0, Alpha=255, Width=-0.4, Frames=0, FadeIn=0, FadeOut=0, Flash=0, Blend=0)
```

Tests: `tools/outline_shell_test.py` (unicorn: the command tables with every earlier cave's commands; the handler and
tick; the FB1 hook chained on the outline's; CommandDrawModel's two draw calls on a fake device context with the game's
draw and every GX2 call recorded: no shell / a shell (programs, states, the draw again, every state back), the refusals;
the programs re-assembled and run in tools/latte_exec.py against `shell_ref` (the band Width pixels wide on screen);
the clear; the diag lines), `tools/mesh_vis_test.py` (v2's multi-part meshes), `new_var_test.cs`, `hitbox_var_test.cs`
(the viewer's band). In game: `tools/outline_shell_ingame_test_build.py` (Dr. Mario's taunts).
