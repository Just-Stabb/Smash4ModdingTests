# Greninja special moves: how the MSC works

Every function from `func_2242` onward in `gekkouga.c` now has a one-line
`//` label. This page explains how each move fits together. The labels and
names come from the debug `printf` strings in the code (e.g.
`"Gekkouga status_SpecialNHold"`), the MSC Note Sheet, and reading the logic.
Where I'm guessing, it says so.

## How to read a status

Each action ("status") has up to 9 scripts, registered by `func_2243` and
`func_2244` with `sv_set_mem(0x1, key, actionId, func)`:

| Key | Role | What it usually does |
|---|---|---|
| 0 | **pre** | `StatusModule(0x5, ...)` and `StatusModule(0x2713, ...)`: situation, kinetic and ground rules, status attributes |
| 1 | **main** | Picks the animation (`func_22(acmd, frame, rate)`) and installs the per-frame loop with `func_78(loop)` |
| 2 | **end** | Cleanup when leaving the status (`global6` = the status being entered) |
| 3 | **init** | Sets up `KineticModule` speeds and gravity |
| 4 | **exec** | Extra per-frame logic |
| 5 | exec during hitlag | Usually just keeps a rotation applied |
| 6 | exit | More cleanup (e.g. turning off the counter shield, setting landing lag) |
| 7 / 8 | other per-frame hooks | Mostly the empty `func_2245` |

Patterns that repeat in every move:

- **`func_78(loop)`** refreshes the input globals, then installs `loop`
  through `callFunc3`. The loop runs every frame. It ends the status with
  `func_16(newStatus, 0); return 0x1;`.
- **`global16 = f`** adds a second per-frame function. Greninja uses it for
  frame counters, which are skipped during hitlag (`if (!StopModule(0x1))`).
- **IASA cancels:**
  `if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0)) return;`
  checks the interruptible frames. `func_39` and `func_41` try every ground
  and air action.
- **Ground/air swap:** `global19 == 0 && global18 == 0x2` means "was on the
  ground last frame, now in the air". Swap the motion (`func_23`/`func_24`
  keep the frame), the ground correction (`GroundModule(0x2710, ...)`) and the
  kinetic type (`KineticModule(0, 0x6 / 0xA)`).
- **Parameters:** `WorkModule(F)(…, 0x5……)` reads SpecialN params, `0x6……`
  SpecialS, `0x7……` SpecialHi, `0x8……` SpecialLw, `0x4……` Final. The high
  digit gives the type: `0x0…` float, `0x1…` int, so `0x17000004` is an int
  SpecialHi param and `0x07000003` is a float one. These come from
  `fighter_param_vl`, so changing a move's numbers usually means editing the
  param file, not the MSC.
- **Flags `0x21……`** are per-status flags that the ACMD scripts turn on at
  specific frames (e.g. "throw the shuriken now", "counter window open"). The
  MSC reacts to them.

## Neutral B: Water Shuriken (0x152, 0x157–0x15A)

```
SpecialN 0x152 --anim end--> SpecialNHold 0x157 --B released--> SpecialNShot 0x158
     |                               |
     | stored full charge            +--full charge--> SpecialNMaxShot 0x15A
     v                                                  (or store charge, see below)
SpecialNMaxStart 0x159 --anim end--> SpecialNMaxShot 0x15A
```

- **SpecialN (`func_2261`–`2264`)** is the windup. If a full charge is stored
  (instance float `0x2f` ≥ 1.0), it goes straight to MaxStart. When the
  windup animation ends it goes to Hold. Hold checks the button again itself,
  because `0x21……` flags reset on every status change.
- **SpecialNHold (`func_2266`/`2267`)** is the charge. The animation speed is
  set so it lasts `0x5000000` frames (max charge time, scaled by
  `0x5000008`). Each frame, `charge = animFrame / maxFrames` is written to
  `0x2f`.
  - Releasing B (`!ControlModule(0x2712, 1)`) goes to SpecialNShot.
  - At full charge, if SpecialN param `0x15000003` is set, it fires
    MaxShot. Otherwise it **stores** the charge (flag `0x20000078`) and drops
    to Wait/Fall, which looks like a custom-move variant.
- **Shot / MaxShot (`func_2270`/`2278`, loops `2271`/`2279`)** throw the
  article when ACMD sets `0x2100000d` (`ArticleModule(0x2719, 0)`). The end
  scripts reset the charge.
- **Aerial recoil (`func_2281`)**, the init for both shots: in the air,
  Greninja is pushed backward (`0x5000001`) and **up** (`0x5000002`). The
  upward push only happens on the first shot per airtime. Flag `0x2000007a`
  is set when a shot ends in the air and cleared on landing by `func_2259`.
- **Helpers:** `func_2282` picks the ground or air motion from
  `0x11000002`/`0x11000003` (each main stores both IDs). `func_2283` swaps
  between them mid-move.

**Easy edits:**
- Remove the once-per-airtime limit: delete the
  `WorkModule(0x2710, 0x2000007a);` line in `func_2272`/`func_2280`.
- Always auto-fire at max: make `func_2267` take the MaxShot branch
  unconditionally.

## Side B: Shadow Sneak (0x153, 0x15B, 0x15C)

```
SpecialS 0x153 --travel done--> SpecialSAttack 0x15B --anim end--> SpecialSEnd 0x15C
```

- **SpecialS (`func_2289`–`2291`):**
  1. The startup animation `0x239` is time-stretched to last `0x16000006`
     frames.
  2. After that, `func_2291` (installed in `global16`) makes Greninja
     **invisible, intangible and without hurtboxes**
     (`VisibilityModule`/`HitModule(0x2710, 2)`/`AreaModule`) for
     `0x16000007` frames.
  3. Then he reappears, is moved to `(0x31, 0x32)`, where the shadow
     travelled (the shadow itself is moved outside this file), and enters
     SpecialSAttack.
- **Direction (`func_2290`):** every frame it compares the stick with the
  facing direction against the deadzone `0x6000003`. Holding backward clears
  `0x2000007e`; forward or neutral sets it.
- **SpecialSAttack (`func_2294`):** with the flag set, Greninja does the
  normal attack (`0x23D` ground / `0x24D` air). Otherwise he does the
  turn-around attack (`0x241`/`0x251`), and **SpecialSEnd (`func_2298`)**
  flips his facing (`PostureModule(0x2710)`) at the end.

**Easy edits:**
- Change the vanish time with `0x16000007` (SpecialS params).
- Make him stay tangible by removing the `HitModule(0x2710, 0x2)` line in
  `func_2291`.

## Up B: Hydro Pump (0x154, 0x15D, 0x15F, 0x15E)

```
SpecialHi 0x154 --> SpecialHiJet 0x15D --timer / land--> SpecialHiEnd 0x15F --(2nd jet)--> SpecialHiJet 0x15D
                         |                                    |
                         +--steep wall--> WallDamage 0x15E      +--> SpecialFall 0x10 / LandingFallSpecial 0x19
```

- **Startup (`func_2302`, `2303`):**
  1. Marks up-B as used (`0x20000080`). The hook `func_2378` then blocks a
     second up-B until `func_2259` clears it on landing, ledge grab and so on.
  2. On frame `0x17000001`, it reads the stick, faces that way and saves the
     unit direction to `0x1000006`/`0x1000007`. A stick below the deadzone
     `0x7000002` means straight up.
  3. It then tilts the body bone (`ModelModule(0x1, 0x2, angle, …)`) toward
     that angle.
- **Jet (`func_2319` init, `func_2308` main, `func_2309` loop):**
  - Speed is `0x7000003`. The 2nd jet is multiplied by `0x7000007`.
  - The jet lasts `0x17000004` frames (counter `0x11000004`, decremented by
    `func_2321`, not during hitlag).
  - Aiming **into the floor** while touching it keeps the raw direction (a
    ground slide). Otherwise it uses the stored direction and **uses up your
    double jumps** (`0x10000001` = max jumps).
  - `func_2322` checks surfaces. Hitting the ceiling at a steep angle
    (> `0x17000005`+90°) ends the jet. Hitting a wall that way goes to
    **SpecialHiWallDamage**, a bonk that bounces off and falls into
    DamageFall (`func_2331`–`2333`).
- **Between and after jets (`func_2326`, `func_2327`, `func_2328`):**
  - Speed is damped (`0x7000008`/`9`) and the jet counter (`0x11000003`)
    goes up by one.
  - For about the first 10 frames, if fewer than 2 jets were used and the
    stick has turned at least `0x17000006` degrees from the last jet, a
    **2nd jet** starts.
  - Otherwise Greninja untilts and ends in **SpecialFall** (or
    LandingFallSpecial if he lands).
  - Key 6 (`func_2329`) sets the landing lag (`0x700000E`) and air speed
    (`0x700000B`), and enables recovery-move landing lag (`0x20000003`).

**Easy edits:**
- Three jets: change `if (var0 < 0x2)` in `func_2328` to `0x3`.
- No double-jump loss: remove the `WorkModule(0x7, …, 0x10000001)` line in
  `func_2319`.
- No helpless state: in `func_2315`, change `func_16(0x10, 0)` to
  `func_16(0xE, 0)` (Fall).

## Down B: Substitute (0x155, 0x160–0x164)

```
SpecialLw 0x155 --hit during window--> SpecialLwHit 0x160 --> SpecialLwAttack 0x161 --> SpecialLwEnd 0x162 --> SpecialLwLanding 0x163
                                                                        |
                                                                        +--steep surface--> SpecialLwBound 0x164
```

- **Counter stance (`func_2336`/`2337`, `func_2344`):**
  - While ACMD holds the window flag `0x2100000d`, a counter shield is on
    (`ShieldModule(0, 0x2, 0, 0x1, 0x1)`). Flag `0x2100000e` tracks whether
    it's on.
  - The animation runs at rate `0x8000026` during the window.
  - In the air, Greninja keeps his vertical speed only on the first use per
    airtime (`0x20000081`). After that, falling speed is `0x8000001`/`2`.
  - Getting hit while the shield is up enters SpecialLwHit. This switch
    isn't in this file; it's presumably the engine's counter handling.
- **SpecialLwHit (`func_2346`/`2347`):**
  1. Rolls `MathF(0x6)` (random 0–1) against `0x8000003 / 100`. Success sets
     `0x21000012`, which picks the **rare substitute** (`BattleObject(0x3F8)`)
     instead of the normal log (`0x3F7`). Both spawn when ACMD sets
     `0x21000013`. *(Which ID is which is inferred from the chance roll.)*
  2. After `0x8000004` frames, goes to SpecialLwAttack.
- **SpecialLwAttack (`func_2358` init, `func_2354` loop):**
  1. Reads the stick (`global48`, `global32`) and splits it into 8 sectors
     of 45°, grouped into 5 bands, each with its own speed, minimum speed and
     duration parameters:

     | Flag | Direction (best guess) | Speed param |
     |---|---|---|
     | `0x2100001F` | up | `0x8000013` |
     | `0x2100001E` | up-diagonal | `0x8000010` |
     | `0x2100001D` | sideways | `0x800000D` |
     | `0x2100001C` | down-diagonal | `0x800000A` |
     | `0x2100001B` | down | `0x8000007` |

     A neutral stick uses `0x8000006` and attacks back toward his original
     side.
  2. Warps to the start point `(0x1000008, 0x1000009, 0x100000A)`. That
     position is written outside this file, probably relative to the
     attacker.
  3. Rotates the model (`FighterUtil(0x6, angle)`) and rushes. The loop
     slides him along walls and floors and makes him visible again.
  4. When the band's duration runs out, goes to SpecialLwEnd. Hitting a
     surface steeply goes to **SpecialLwBound** (bounce: `0x800001F` back,
     `0x8000020` up).
- **SpecialLwEnd → SpecialLwLanding (`func_2362`–`2370`):** brakes along the
  rush direction (`0x800001B`/`C`) and rotates back upright over 10 frames.
  After `0x1800001D` frames on the ground, he lands.

**Easy edits:**
- Change the rare-substitute chance with param `0x8000003` (a percent).
- To force it in code, add `WorkModule(0x2710, 0x21000012);` at the end of
  the `func_2346` setup.

## Final Smash: Secret Ninja Attack (0x156, 0x165–0x168)

| Status | Scripts | What happens |
|---|---|---|
| Final 0x156 | `func_2388`–`2393` | Enters the Final Smash state (`BattleObject(0x25)`, per the sheet). Plays the windup `0x29B`. A hit (ACMD flags `0x2100000E` + `0x2100000F`) goes to 0x165. A whiff plays `0x295` and ends. |
| 0x165 | `func_2394`–`2398` | Caught; motion `0x295`. The switch to 0x166 isn't in this file (engine/ACMD). |
| 0x166 | `func_2399`–`2402` | Creates article 3 (likely the night/backdrop), motion `0x299`, fades the screen to black over `0x14000006` frames (`func_2412`). |
| 0x167 | `func_2403`–`2406` | Creates article 5, places the camera, motion `0x297`. At frame 170 the camera locks. The animation end goes to 0x168. |
| 0x168 | `func_2407`–`2411` | Motion `0x298`, fades back in (`func_2413`), then Wait/Fall. Removes article 3 and leaves the Final Smash state (`BattleObject(0x26)`). |

The state names for 0x165–0x168 are descriptive guesses; the code has no
debug strings for them.

## Non-special overrides

- **Dair bounce (`func_2382`/`2383`, `func_2384`/`2385`):** if the dair
  connects (`0x20000082`, matches the sheet's note), Greninja switches to
  JumpAerial after 3 frames and gets a bounce jump (`func_496(0x1E, 0)`).
  Specials, aerials and footstools stay blocked until the flag clears.
- **Up/down smash (`func_2386`/`2387`):** `ItemModule(0xF, 0)` before the
  common smash code.
- **Landing, ledge and similar (`func_2246`–`2258`):** all call `func_2259`,
  which refreshes the once-per-airtime shuriken boost and up-B.

## Not fully explained: `func_2379` (side-B hook)

`func_2377` and `func_2378` run `func_2379` at the start of the common
ground and air action checks (`func_43` / `func_58`), before the normal
side-B input check. As written, it:

1. Turns off the side-B transition (`WorkModule(0x17, 0x1E000063)`) every
   frame.
2. When side-B is pressed (`global24 & 0x2000`), sets `0x2000007C`, saves a
   direction (instance float `0x36`, flipped if the stick is held back) and
   speeds (`0x30`, `0x35`). From Dash/Run/TurnRun it goes to RunBrake; from
   Guard it goes to GuardOff.
3. While `0x2000007C` is set, turns off most other transitions (attacks,
   dodges, shield, specials, item pickups) and sets ACMD flags depending on
   the current status.

Nothing in this file clears `0x2000007C`, and with the side-B transition
switched off, the normal side-B check in `func_43` can't fire. Either the
engine or ACMD handles this flag, or this part of the file was edited. The
file has a few hand-written comments, so it may not be fully vanilla.
