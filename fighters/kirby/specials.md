# Kirby special moves: how the MSC works

Every Kirby-specific function in `kirby.c` (from `func_2242` to the end,
about 1,880 functions) now has a one-line `//` label. The labels are comments
only, so the compiled file is byte-for-byte the same.

There are three kinds of label:

- **Kirby's own moves** (`func_2242`–`func_2477`): written by hand from
  reading the code, like Greninja's. They look like
  `[SpecialSHoldWalk 0x16A] loop: ...`.
- **Copy abilities** (`func_2478` onward): generated, with `[Copy: <fighter>
  <action>] <role>`.
  - The fighter comes from Kirby's own neutral-B table (`func_2351`, below).
  - The role (pre/main/end/init/exec/exit/loop) comes from how the function
    is registered.
  - Helpers are labelled with the fighter whose scripts call them. If the
    function has a debug `printf`, its text is appended.
- **`[unused]`**: 229 copy-ability functions that nothing reachable
  references. They're leftovers of the original fighters' scripts and never
  run.

Status keys work the same as for Greninja (see
`fighters/gekkouga/specials.md`): 0 pre, 1 main, 2 end, 3 init, 4 exec,
5 exec during hitlag, 6 exit.

## Neutral B: Inhale (0x152, 0x157–0x168)

```
SpecialN 0x152 -> SpecialNLoop 0x157 --B released--> SpecialNEnd 0x158
                         | caught someone
                         v
        SpecialNCapture 0x159 -> SpecialNEat 0x15A -> EatWait 0x15B (mouthful)
                                                        |-- A / B -> Spit 0x168 (star)
                                                        |-- B / down -> Swallow 0x167 (copy)
                                                        +-- walk 0x15E, jump 0x15F/0x160, fall 0x161,
                                                            turn 0x164/0x165, land 0x163, drop through 0x162
```

- **Copy abilities start here.** `func_2351` (SpecialN pre) checks
  `0x2000009A` (Kirby has a copy ability). If set, it jumps straight to that
  fighter's neutral-B status using the copy kind in `0x100000A4`, e.g. kind
  `0x30` (Greninja) → status `0x22D`. Otherwise Kirby inhales.
- **Inhale (`func_2356`–`2358`):** the inhale lasts at least `0x15000000`
  frames. After that, releasing B goes to SpecialNEnd.
- **The catch** (when Kirby grabs someone with the inhale) is started from
  outside MSC. `0x159`'s loop only handles ground/air swaps, which is why its
  label says "guess".
- **Mouthful (`func_2266`):** A, or B while flag `0x21000018` is set, spits.
  B or holding down below `0x5000011` swallows.
- **Not fully sure:** `0x15C`, `0x15D` and `0x166` are mouthful states whose
  exact role isn't clear from the code; their labels say "guess".

## Side B: Hammer Flip (0x153, 0x169–0x171)

```
SpecialS 0x153 --hold--> HoldWait 0x169 <-> HoldWalk 0x16A / HoldTurn 0x16B
                            |-> HoldJumpSquat 0x16C -> HoldJump 0x16D -> HoldFall 0x16F -> HoldLanding 0x170
                            +-> HoldPass 0x16E (drop through platform)
release B from any of them --> SpecialSSwing 0x171
```

- **Charge (`func_2474`):** each frame, `0x11000003 += 0x16000008` until it
  reaches `0x6000004`. Then the full-charge flag `0x21000010` is set and a
  sound plays.
- **Full charge hurts (`func_2476`):** while fully charged, Kirby takes 1%
  every `0x6000006` frames, as long as Kirby's damage is below `0x6000007`.
- **Swing (`func_2468`, `func_2475`):** the motion depends on charge.
  - Full charge: `0x2C5`/`0x2C9`.
  - Under ¼ charge: `0x2B5`/`0x2B9`.
  - Otherwise: `0x2BD`/`0x2C1`.
  - Damage is multiplied by `charge × 0x6000005`
    (`AttackModule(0x272D, …)`).

### Your edits in `func_2430` (SpecialS loop)

I left your code exactly as it is. Three things in it probably don't do what
you want:

1. **`KineticModuleF(0x0, facing * 1.2f);` doesn't set speed.** `KineticModuleF`
   is `sys_11`, the float *getter*. `KineticModuleF(0, 1)` reads the current
   X speed, and the return value is thrown away here. The same goes for the
   `KineticModuleF(0x1, 1.2f)` line. To set speed, use the pattern from
   Kirby's other moves:
   ```c
   KineticModule(0xe, 0x3, 0x6, 0, 0, 0, 0, 0);    // reset horizontal energy
   KineticModule(0x11, 0x3, facing * 1.2f, 0);     // set X speed (world units, so multiply by facing)
   KineticModule(0xb, 0x3);                        // enable it
   KineticModule(0xe, 0x1, 0, 0, 0, 0, 0, 0);      // reset vertical energy
   KineticModule(0x11, 0x1, 1.2f);                 // set Y speed
   KineticModule(0xb, 0x1);
   ```
   Also, `KineticModule(0, 0x6)` sets the kinetic type to GROUND_STOP every
   frame on the ground, and that cancels horizontal movement. Use a moving
   type, or set the speed after it.
2. **`func_22(0x290, 0, 1.0f)` after `func_16(0x171, 0x1)` gets
   overwritten.** The Swing status's main (`func_2466` → `func_2468`) picks
   its own motion as soon as it starts. To use animation `0x290`, change it
   inside `func_2468`.
3. **The hit check is correct.** `AttackModule(0x2727, 0x2)` is "hitbox has
   connected with a hurtbox" (sheet: Complex CMDs). It stays true for the
   rest of the status.

## Up B: Final Cutter (0x154, 0x172–0x174)

```
SpecialHi 0x154 (rise) -> SpecialHiFall 0x172 -> SpecialHiFall2 0x173 -> SpecialHiLanding 0x174 (shockwave)
                                 +-- ACMD flag 0x2100000F -> SpecialFall
```

- **Rise:** speed comes from gravity `0x3000014 × 0x7000001` (`func_2305`).
  Starting on the ground scales the upward speed by
  `0x7000000 × 0x7000006` (`func_2309`).
- **Landing slash:** sets landing lag `0x7000005` (`func_2304`).

## Down B: Stone (0x155, 0x175, 0x176)

- **Start (`func_2318`, `func_2331`):** creates the stone article `0x18` and
  picks a random stone form (`0x100000A3`). The form is never the same as
  the previous one.
- **Hold (`func_2322`/`2323`):** pressing B after at least `0x18000001`
  frames reverts. On the ground it reverts automatically after
  `0x18000000` frames.
- **Armor:** the effect is toggled from ACMD flag `0x21000010`
  (`func_2333`).
- **End (`func_2328`):** removes the stone and makes Kirby visible again.

## Final Smash: Ultra Sword (0x156, 0x179)

`0x156` swings the sword. If a hit is confirmed (`0x2100000D`) by frame 80,
it goes to `0x179`, the sword combo. The end scripts remove the sword
articles (`0x1C`, `0x1D`) and leave the Final Smash state.

## Hooks and overrides

| Function | Where it runs | What it does |
|---|---|---|
| `func_2348` | `global23/57/59` (before action checks) | Copy-ability input limits for Pit/Dark Pit, Rosalina (Luma timer `0x100000A9`), Villager, Shulk |
| `func_2349` | `global28` (neutral-B allowed?) | Blocks neutral B for Rosalina/Pit copies at certain times |
| `func_2350` | `global35` (air checks) | Sonic copy: one neutral B per airtime (`0x20000079`) |
| `func_2280`–`2286` | Landing, ledge grab, death | Link/Toon Link copy arrow landing lag; reset Sonic's flag |
| `func_2269`–`2279` | CatchWait/CatchAttack | Kirby's pummel and throw inputs |

## Copy ability → status table (from `func_2351`)

| Kind | Fighter | Status | | Kind | Fighter | Status |
|---|---|---|---|---|---|---|
| 0x0 | Mii Brawler | 0x17C | | 0x1D | Ike | 0x1BC |
| 0x1 | Mii Swordfighter | 0x181 | | 0x1E | Lucario | 0x1EB |
| 0x2 | Mii Gunner | 0x186/0x18A (via `func_2524`) | | 0x1F | R.O.B. | 0x1D2 |
| 0x3 | Mario | 0x19A | | 0x20 | Toon Link | 0x1EA |
| 0x4 | Donkey Kong | 0x1B7 | | 0x21 | Charizard | 0x19D |
| 0x5 | Link | 0x1E9 | | 0x22 | Sonic | 0x192 |
| 0x6 | Samus | 0x1F0/0x1F4 (via `func_2680`) | | 0x23 | Jigglypuff | 0x1C5 |
| 0x7 | Yoshi | 0x1AB | | 0x24 | Dr. Mario | 0x201 |
| 0x9 | Fox | 0x19B | | 0x25 | Lucina | 0x202 |
| 0xA | Pikachu | 0x18E | | 0x26 | Dark Pit | 0x206 |
| 0xB | Luigi | 0x1BB | | 0x27 | Rosalina | 0x20B |
| 0xC | Captain Falcon | 0x18C | | 0x28 | Wii Fit Trainer | 0x20F |
| 0xD | Ness | 0x1B3 | | 0x29 | Little Mac | 0x212 |
| 0xE | Peach | 0x1A9 | | 0x2A | Villager | 0x21A |
| 0xF | Bowser | 0x1F6 | | 0x2B | Palutena | 0x21F |
| 0x10 | Zelda | 0x1AE | | 0x2C | Robin | 0x222 |
| 0x11 | Sheik | 0x1AF | | 0x2D | Duck Hunt | 0x228 |
| 0x12 | Marth | 0x1C1 | | 0x2E | Bowser Jr. | 0x229 |
| 0x13 | Mr. Game & Watch | 0x1FC | | 0x2F | Shulk | 0x22C |
| 0x14 | Ganondorf | 0x1E7 | | 0x30 | Greninja | 0x22D |
| 0x15 | Falco | 0x19C | | 0x31 | Pac-Man | 0x232 |
| 0x16 | Wario | 0x19E | | 0x32 | Mega Man | 0x236 |
| 0x17 | Meta Knight | 0x18F | | 0x33 | Mewtwo | 0x237 |
| 0x18 | Pit | 0x1F7 | | 0x34 | Ryu | 0x23B |
| 0x19 | Zero Suit Samus | 0x1FD | | 0x35 | Lucas | 0x23E |
| 0x1A | Olimar | 0x1E6 | | 0x36 | Roy | 0x242 |
| 0x1B | Diddy Kong | 0x1CD | | 0x37 | Cloud | 0x248 |
| 0x1C | King Dedede | 0x1D3 | | 0x38 | Bayonetta | 0x249 |
| | | | | 0x39 | Corrin | 0x24D |

Kind `0x7` (Yoshi, `0x1AB`) isn't in the sheet's Kirby tab; it comes from
this table. Any unknown kind falls back to SpecialFall (`0x10`).
