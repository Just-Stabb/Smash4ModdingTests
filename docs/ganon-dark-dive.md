# Ganondorf's up special (Dark Dive): statuses, the victim, the user's custom ending

Ganondorf's MSC (`ganon.mscsb`, decompiled; the universal mechanics build) registers his own
statuses in `func_2244`-`func_2250` (`sv_set_mem(0x1, slot, status, func)`):

| Status | Motion (mtable slot) | Pre / main | What |
|---|---|---|---|
| `0x154` | SpecialHi `0x239` / SpecialAirHi `0x23d` | `func_2289` / `func_2290` | the dive; the grab (`Grab_Collision2`, TargetStatus `0xB8`) |
| `0x15C` | SpecialHiCatch `0x241` | `func_2294` / `func_2295` | holding; to `0x15D` at the motion's end |
| `0x15D` | SpecialHiThrow `0x245` | `func_2298` / `func_2299` | the ending; to `0xE` (fall) at the motion's end |

The victim: status `0xB8` ("grabbed by Ganondorf up-b") while caught, then `0x44` (Thrown). Both
bind to the capturer the same way (their slot-3 functions: `LinkModule(0x2716, 0, 0x3)`).
`0x15D`'s slot-3 function (`func_2418`) calls `BattleObject(0x3e9, 0xb, -1)`, Ganondorf's wrapper
for the link event `0xb` that the common Throw status sends too (`func_1081`:
`LinkModule(0x271b, 0xb, ...)`): the victim goes to Thrown, held at the thrower's `ThrowN` until
`Throw_Applier` (ATK_HIT_ABS), as in every grab throw.

Vanilla SpecialHiThrow runs `Throw_Applier` on frame 0 (bone `0x1A`), so the victim is launched at
once. The user's custom SpecialHiThrow animation (`ganon_scriptsmotion.zip`) carries `ThrowN` from
67 up / 60 forward (held frames 0-16) down to the ground (0.5 at frame 36, -2.9 at 37): with
`Throw_Applier` at frame 0 the victim never followed it. `build/ganon_upb_throwN.zip`: `Throw_Applier`
at frame 36; the ending's explosion effects, sound and shake moved with it (frame 0 -> 36, shake
2 -> 38).

Invincibility (user: no trades once it connects): `Body_Collision(State=1)` (state 1 = invincible:
vanilla Ike's counter hit, Lucas' up smash; 2 = intangible: air dodges, ledge options) at frame 0 of
SpecialHiCatch (the user had it at frame 1), and in SpecialHiThrow from frame 0 to the launch, then
`State=0`. The frame the grab connects is still SpecialHi's, before any of it.

## v2 (`build/ganon_upb_v2.zip`): the drag during SpecialHiCatch

User (v1): no upward drag; Ganondorf "appears behind the opponent". While caught the victim is in
`0xB8`, held at a fixed point (vanilla: in front of his hand; vanilla SpecialHiCatch keeps `ThrowN`
at his feet, unused); only Thrown (`0x44`) follows `ThrowN`. The user's SpecialHiCatch carries
`ThrowN` 67 up / 60 ahead over frames 0-28 with his body still, so the victim stayed put, then
jumped there when SpecialHiThrow sent the thrown event.

- `func_2412` (status `0x15C` slot 3, empty in vanilla) now sends the thrown event,
  `func_2261(0xb, -1)` (= `BattleObject(0x3e9, 0xb, -1)`, what `0x15D`'s `func_2418` does): the
  victim is thrown from the catch's first frame. `0xB8`'s exit (`func_1593`) only releases the
  capture for a status other than `0x44`. `0x15D` still sends it (it is what sets the
  `Throw_Applier` target, `0x11000005-7`; not traced natively). Hitboxes hit a thrown victim
  (Pikachu ThrowF, Kirby ThrowLw, Bowser ThrowHi loop `Special_Hitbox`es), so the catch's
  multi-hits stay.
- `func_2299` / `func_2302`: vanilla's posture pop at the throw's start (-7 x LR, then +14 on frame
  1: vanilla's catch and throw animations' offset) removed; the user's two animations are continuous.
- The turn near the end is the user's animation (bust yaw 146 -> 27 degrees over SpecialHiThrow
  frames 28-40).
- `msc_fingerprint.py`: 2449 functions, only `func_2299`, `func_2302`, `func_2412` differ. If the
  event at the catch's init comes too early in game (before the capture link), the fallback is to
  send it on the catch's first main frame.

## v3 (`build/ganon_upb_v3.zip`): v2 crashed (user)

Ganondorf's `BattleObject` handler (`fighter_ganon.cpp`, `0x02EEC46C`: `cmplwi 0x3e8 / 0x3e9`): both
build a link-event record (event = arg 1, motion = arg 2, the rest -1) and send it through
`0x02C55B04(obj+0x7294, 0, &rec)`; `0x3e9` then reads the linked object (`0x02C55CB4`) and writes it
and the record's hit group / no into the current status's work ints `0x11000005-7` (what
`Throw_Applier` reads). v2 sent it at the catch's init (the victim still entering `0xB8`) and again
at the throw's init (the victim already Thrown); vanilla does neither. v3:

- `func_2412` (catch init): `global65 = 0`. `func_2296` (catch main, every frame): from motion
  frame 1, once, `func_2261(0xb, -1)`, then `global66-68` = `0x11000005-7`, `global65 = 1`.
- `func_2418` (throw init): if `global65`, `0x11000005-7` = `global66-68` (no second event); else
  vanilla's `func_2261(0xb, -1)`.
- `func_2299` / `func_2302`: posture pop removed (v2).
- Four globals added after `global64`; fingerprint: 5 functions differ (`func_2296`, `func_2299`,
  `func_2302`, `func_2412`, `func_2418`); `msc_stack_check.py` clean.

## v4 (`build/ganon_upb_v4.zip`): the victim T-posed and didn't move (user, v3)

The link event's motion (arg 2) is what Thrown (`0x44`) plays (`func_1130`: `func_22(0x11000002)`);
Ganondorf's `func_2261(0xb, -1)` sends none, never seen in vanilla (launched on frame 0). Every
thrown motion carries the victim's own `ThrowN` (0 for normal fighters, -10.7 in the `Dx` variants:
the victim's `ThrowN` is lined up with the thrower's, so the hanging body sits below it): with no
motion, no pose and no position. v4: `func_2261(0xb, 0x1be)` in the catch, `0x1be` = the Dark Dive
capture motion `0xB8` plays (`func_1584`; its Dx / Girl variants are picked by Thrown's slot-3
`MotionModule(0x29, ...)`). Generic alternatives: ThrownF / B / Hi / Lw `0x7c`-`0x7f`. The throw
init's vanilla fallback keeps -1 (only used if the catch didn't send it).
