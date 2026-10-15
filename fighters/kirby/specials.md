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

What your code does: Kirby slides forward on the ground, hops into the air
on frame 10, and goes straight to the swing (`0x171`) when the hammer hits
someone (`AttackModule(0x2727, 0x2)`, "hitbox connected with a hurtbox").

**Momentum fix:** the original used `KineticModuleF(...)` to set speeds, but
`KineticModuleF` (`sys_11`) only *reads* speeds, so it did nothing. Now:

- **Ground:** every frame, `KineticModule(0x11, 0x3, facing * 1.2f, 0)` sets
  the X speed, with braking set to 0 and the energy enabled. I removed the
  per-frame `KineticModule(0, 0x6)`; the move already sets that kinetic type
  when it starts.
- **Hop (frame 10):**
  1. Sets the kinetic type to AIR_STOP first, because changing the type
     resets speeds.
  2. Sets X speed `facing * 0.8f` and Y speed `1.2f`.
  3. Applies Kirby's own gravity (`0x3000018`) and max fall speed
     (`0x3000019`).
  4. Ends the frame early (`return`). Otherwise the ground/air swap at the
     bottom of the loop (`func_2431`) would set the kinetic type again on
     the same frame and wipe those speeds.

The numbers (1.2, 0.8, 1.2) are yours. Tune them in the file.

**Still there:** `func_22(0x290, 0, 1.0f)` after `func_16(0x171, 0x1)` is
overwritten when the Swing status starts (`func_2466` → `func_2468` picks its
own motion). To use animation `0x290`, change it inside `func_2468`.

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

## Added: aimable inhale (stick rotates the aim)

During the inhale loop (status `0x157`), holding up or down rotates bones,
modelled on Charizard's Flamethrower and Kirby's own Fire Breath copy (see
`fighters/lizardon/README.md`). The new functions are at the end of
`kirby.c` (`inhale_aim_*`, compiled as `func_4123`–`func_4135`), hooked
into:

- `func_2356` (0x157 main): `inhale_aim_init()` sets the angle to 0
  (straight ahead).
- `func_2357` (0x157 loop): `inhale_aim_update()` runs every frame. When
  |stick Y| is above the deadzone, `angle += speed × stickY`, clamped to
  `[-max_down, max_up]` and stored in status float `0x1000006`. Then
  `ModelModule(0x1, shoulder, 0, sign × angle + offset, 0)` swings both
  arms up or down.
- `func_2359` (0x157 end): `inhale_aim_reset()` puts the bones back to 0.

**Settings** (the small functions under `// [Inhale aim] SETTINGS`):

| Setting | Default | What it does |
|---|---|---|
| `inhale_aim_max_up` / `_max_down` | 40 / 40 | Angle limits in degrees |
| `inhale_aim_speed` | 2.0 | Degrees per frame at full stick |
| `inhale_aim_deadzone` | 0.2 | Stick Y needed to move (Charizard uses 0.5) |
| `inhale_aim_bone1` | `0xE` | `LShoulderJ`, left arm (the arm and hand follow) |
| `inhale_aim_bone2` | `0x12` | `RShoulderJ`, right arm |
| `inhale_aim_sign1` / `_sign2` | 1 / -1 | The shoulders are mirrored, so the right one needs the opposite sign. Flip one if that arm goes the wrong way |
| `inhale_aim_offset1` / `2` | 0 | Fixed extra rotation in degrees |

**Why these bones and this axis:** the bone number is the bone's position in
Kirby's `model.vbn` (list: `fighters/kirby/model/bones.md`). The game's own
code confirms this: Greninja's Hydro Pump tilts bone `0x2` = `HipN`.

At rest, each shoulder's local X runs along the arm, local Z is vertical and
local Y points forward. Rotating around local **Y** therefore swings the arm
up and down. That still holds after the inhale animation turns the arm
forward, as long as the turn is around the vertical axis.

`inhale_aim_apply` passes the angle as the Y argument of
`ModelModule(0x1, bone, x, y, z)`. If an arm moves sideways or twists
instead, the animation posed it differently: try the angle as Z.

Correction to my earlier note: bone `0x13`, which Kirby's Fire Breath copy
rotates, is `RArmJ` (the right forearm), not a head or body bone.

**Making it a ranged attack:** the hitboxes and inhale grab box come from
Kirby's ACMD, not MSC. Attach them to the hand bones (or a child of the
rotated bone) so they follow the aim.

**Not tested in-game.** It compiles, and decompiling the result shows only
the three hook calls and the new functions changed; all other scripts keep
their numbers and code.

## Added: Ryu copy commands only with the special button

Kirby's Ryu copy (kind `0x34`) gets its command specials from `func_3938`,
which the `global37` hook `func_2287` calls. The commands are Hadoken
(`global45 & 0x1` → `0x23C`) and Shakunetsu (`& 0x2` → `0x23D`). As with
Ryu (`fighters/ryu/README.md`), they're now ignored unless Special was
pressed more recently than Attack (`ControlModule(0x2722, 0x1) <
ControlModule(0x2722, 0)`).

## Added: star missiles from alternating hands during the inhale

During the inhale loop (status `0x157`), a star missile (article `0x17`)
fires on frame 0, 12, 24, …, alternating left hand, right hand, left hand…
The code is at the end of `kirby.c` (`starmissile_*`), called from
`func_2358`, the inhale loop's per-frame function, so it pauses during
hitlag.

1. A frame counter in status int `0x11000005` picks the hand:
   `(frame / 12) % 2`.
2. `ArticleModule(0x1, 0x17)` counts the star missiles currently out (the
   same call Ryu uses for his Hadoken). If `starmissile_max()` are already
   out, the shot is skipped.
3. `ArticleModule(0x2718, 0x17)` creates a new star. That's the generate
   call Charizard's Flamethrower uses to spawn many flames (breath, max 6).
4. The star is moved to the hand bone's world position (from
   `ModelModuleF(0/1/2, bone)`) with `ArticleModule(0x272B, 0x17, x, y, z)`.

| Setting | Default | |
|---|---|---|
| `starmissile_interval` | 12 | Frames between shots |
| `starmissile_max` | 5 | Keep equal to the count patched into `cross_f.rpx` |
| `starmissile_article` | `0x17` | starmissile (`reference/FighterArticles.xml`) |
| `starmissile_bone_left` / `_right` | `0x18` / `0x17` | `LHaveN` / `RHaveN`, the hand hold points (`LHandN` 0x10 / `RHandN` 0x14 also work) |
| `starmissile_generate_cmd` | `0x2718` | Generate command; `0x2710` is the other generate |
| `starmissile_move_to_hand` | 1 | 0 = leave the star where the game spawns it |
| `starmissile_fly_status` | 1 | After spawning, switch the star to this status with `ArticleModule(0x2713, 0x17, status)`. Status 1 is flying, the one with the lifetime (`fighters/kirby/weapons/`). -1 = don't switch |
| `starmissile_shoot` | 0 | 1 = also call ArticleModule "shoot" (`0x2719`) if the star stays attached to Kirby |

**Max count:** the game's limit for `starmissile` is 1 (`Count="1"` in the
article list) unless the executable is patched. `tools/rpx_patch.py`
raises it:
`python3 tools/rpx_patch.py cross_f.rpx build/cross_f.rpx 0x10136C58=5` (current build: 5).
The spit star uses the same article, so it shares the limit.

**Uncertain:** the move and shoot commands take the article ID, not a
specific star. With several stars out, it's untested whether they affect
the newest star or all of them. If older stars jump back to Kirby's hands,
set `starmissile_move_to_hand` to 0.

**Direction:** the star missile's flight is controlled by its own script
(Kirby's `starmissile` weapon MSC/ACMD), not by Kirby. It will fly the way
it normally does when spat out.

## Added: side-B tracking (needs the patched RPX)

**Tested in-game: works.** Kirby homes in on the opponent during the air
swing, and inhale is unaffected. Debug is off (`sideb_homing_debug()` = 0).

How the game does it (traced in `cross_f.rpx`, details in
`docs/native-notes.md`):

- A search box hit on Kirby goes to Kirby's specializer, which hands it to
  the current copy ability's code. For the Sonic copy it reaches Sonic's
  search-hit code (`0x02F7E4D8`). That code only acts for Sonic in `0x152`,
  or for Kirby in `0x192`. It stores the opponent's position in status floats
  `0x1000006` (X) / `0x1000007` (Y), sets `0x2100000D`, and keeps the
  nearest hit.
- Kinetic type `0x68` (Sonic-copy homing) flies at that point, but only while
  the copy ability is Sonic. That's why the earlier `0x68` tests did nothing.

What this mod does:

1. **RPX patch** (in `build/cross_f.rpx`, together with the star missile
   count) sends search hits to that Sonic search code for Kirby with no copy
   (or a copy without its own search code). It also lets Kirby's air side-B
   swing status `0x171` capture targets, as well as `0x192`. Sonic and Kirby's
   real Sonic copy behave as before.
2. **ACMD:** the search box is in the air swing animation `specialairs`
   (motion `0x2C1`, played by `func_2468` in status `0x171`) at frame 0. It's
   an exact copy of Sonic's `specialnsearch` box:
   `Search_Collision(0, 0, 0, size 75, 0, 10, 10, 2, 3, 3, 0, 9, 1, 0, 1, 0, 0)`.
   No ACMD change is needed.

   **Use search ID 0 only.** Three boxes with IDs 0, 1, 2 made the game
   crash as soon as side B started, even with no opponent. Every vanilla
   search box (Sonic's homing, Kirby's inhale) uses only ID 0, so Kirby most
   likely has room for one search box. To cover several areas, swap one ID-0
   box between shapes on alternate frames:
   frames 0-5 cycle `size 28 @ (10, 10, 21)` → `size 15 @ (-2, 40, 12)` →
   `size 15 @ (-2, -20, 12)` (`WAIT(1)` between them), then
   `SEARCH_CLR_ALL()` (homing only reads the target in frames 1-5). Re-issuing
   `Search_Collision` with the same ID replaces the box.
3. **MSC** (end of `kirby.c`):
   - `sideb_homing_init()`, called at the top of the swing main `func_2466`
     (before the motion and search box start), sets the target to a far-away
     point (99999). The search code keeps whichever hit is nearer, so the
     first real hit replaces it. Side B uses `0x2100000D` as "motion
     started", so that flag can't mean "target found".
   - `sideb_homing_update()`, called from the swing loop `func_2467`, runs in
     the air from frame `sideb_homing_frame()` (1) to
     `sideb_homing_end_frame()` (5, so 5 frames of steering; gravity stays
     off afterwards, so Kirby keeps flying in that direction). If a target is
     stored (X < 90000), it turns Kirby to face it and sets his speed toward it
     (atan2 → cos/sin × `sideb_homing_speed()`, 2.0), with no gravity.

   - With no opponent found (no target stored), during the same frames Kirby
     flies **straight forward** at `sideb_homing_speed()`, with no vertical
     speed and no gravity. If a target turns up within the window, he steers
     at it from then on.
   - `sideb_bounce_update()`, also called from `func_2467` (before the
     steering): the first time the air swing hits a hurtbox
     (`AttackModule(0x2727, 0x2)`), Kirby gets `sideb_bounce_back()` (0.8)
     speed backwards (away from where he faces) and `sideb_bounce_up()` (1.5)
     upwards. Steering stops for the rest of the swing (flag `0x21000021`).
     With `sideb_bounce_gravity()` = 1, his gravity and max fall speed come
     back on the bounce so it arcs. Set it to 0 to keep gravity off.
     The bounce also jumps the animation (and its ACMD) to frame
     `sideb_bounce_frame()` (40) with `MotionModule(0x2713, frame)`.
   - `sideb_bounce_cancel_update()`: from `sideb_bounce_cancel()` (6) frames
     after the bounce (frame 46), it enables the air-special and aerial
     transition groups (`0x1F00000A`, `0x1F00000E`) and checks the aerial
     (`func_63`) and air-special (`func_58`) inputs, so any attack cancels the
     swing.
   - `sideb_slow_update()`: if Kirby homed and didn't bounce, from swing frame
     `sideb_slow_frame()` (35) his speed is multiplied by
     `sideb_slow_factor()` (0.9) every frame (read with `KineticModuleF(0/1,
     0x1)`, set on energies 3/1).

Earlier versions used the start status `0x153`. That was wrong: the search
box isn't in the start animation (`specialairsstart`, `0x28D`), so nothing
was ever captured.

Debug modes (`sideb_homing_debug()`) use only speed calls (proven by the
side-B hop). The earlier camera-shake signal was never real.

- `1`: during the steering frames, Kirby **freezes** in the air while no
  target is stored. Freezes = the code runs but nothing was captured.
  Flies at an opponent = everything works. Neither = the code isn't reached.
- `2`: **fake target**, 40 units ahead and 20 up from where the swing
  started. Tests the steering alone.

Known limits:
- Copy abilities with their own search code (kinds `0x16`, `0x1C`, `0x2A`,
  `0x2B`) still use theirs, so side B won't capture with those copies.
- With the patch, inhale's own search boxes (motions `0x211`–`0x217`) now
  also reach the Sonic code in status `0x152`, which Sonic's code accepts for
  anyone. There it writes `0x1000006`/`7` and sets `0x2100000D`. Inhale's
  scripts use `0x2100000D` only as "motion started" and set it on the first
  frame anyway, so this should be harmless.

To read or check ACMD: `python3 tools/acmd.py dump game.bin specialairs`, or
`python3 tools/acmd.py find game.bin Search_Collision`.

### RPX patch (apply to the original `cross_f.rpx`)

```
python3 tools/rpx_patch.py cross_f.rpx build/cross_f.rpx \
  0x10136C58=5 \
  0x2EFB518=0x60000000 0x2F00194=0x38800022 0x2F00198=0x48000034 0x2F001C8=0x4082FFCC \
  0x2F7E550=0x38000001 0x2F7E560=0x3808FE8F 0x2F7E564=0x3908FE6E 0x2F7E568=0x7C0041D6 \
  0x2F7E574=0x60000000 0x2F7E590=0x408201EC
```

| Address | Was | Now | Why |
|---|---|---|---|
| `0x02EFB518` | `beq` (skip when int `0x100000AD` is 0) | `nop` | always hand the hit to the copy dispatcher |
| `0x02F00194` | `lmw` (return, unhandled copy) | `li r4, 0x22` | treat it as Sonic… |
| `0x02F00198` | `lfs` | `b 0x02F001CC` | …and call Sonic's search-hit code |
| `0x02F001C8` | `bne 0x02F00430` | `bne 0x02F00194` | unhandled copies above `0x22` too |
| `0x02F7E550` | `li r0, 0` | `li r0, 1` | r0 = 0 now means "status matches" |
| `0x02F7E560` | `cmpwi r8, 0x192` | `addi r0, r8, -0x171` | |
| `0x02F7E564` | `bne` | `addi r8, r8, -0x192` | |
| `0x02F7E568` | `li r0, 1` | `mullw r0, r0, r8` | r0 = (status-0x171)·(status-0x192) |
| `0x02F7E574` | `clrlwi r0, r0, 24` | `nop` | test the whole product |
| `0x02F7E590` | `beq` | `bne` | skip unless the product is 0 |

To use a different status than `0x171`, change the `-0x171` in
`0x2F7E560` (`0x3808` followed by the 16-bit negative status).
