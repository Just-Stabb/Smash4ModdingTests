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
