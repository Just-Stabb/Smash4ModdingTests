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
- **No catching, no pull (added):** `tools/kirby_inhale_acmd.py` removes the
  `Grab_Collision2` boxes and the `Special_Hitbox` pull windbox (0 damage,
  flinchless, 160°) from the `SpecialNStart` / `SpecialNLoop` ACMD (the air
  versions JUMP to them), so the inhale neither catches nor pulls in
  opponents. The search box and the `Throw_Specifier` stay.
- **Less end lag (added):** SpecialNEnd's loop (`func_2362`) sets the motion
  rate to `inhale_end_speed()` (3×) every frame, including after a ground/air
  motion swap.
- **game.bin build:** `python3 tools/kirby_throwb_acmd.py build/acmd_in/game.bin g1;
  python3 tools/kirby_throwlw_acmd.py g1 g2; python3 tools/kirby_inhale_acmd.py g2 g3;
  python3 tools/kirby_sideb_reflect_acmd.py g3 g4;
  python3 tools/rolloff_acmd.py g4 g5 --plain --add 2.1 EscapeF EscapeB` (roll-off, see
  `docs/universal-mechanics.md`); `python3 tools/kirby_fair_autolink_acmd.py g5 g6`;
  `python3 tools/kirby_sideb_link_acmd.py g6 g7` (ground side B link);
  `python3 tools/kirby_rapid_air_acmd.py g7 g8` (air rapid jab: loop 60% damage, finisher 65% knockback);
  `python3 tools/kirby_jump_articles_acmd.py g8 build/game.bin` (no test articles in the air jumps).
  The current `build/game.bin` also had `kirby_throwb_acmd.py IN OUT --retune` run on it (bury
  slam size 18, SDI 0); a fresh `kirby_throwb_acmd.py` run already uses those values
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

- **Jump while turning (added):** HoldTurn (`0x16B`, loop `func_2443`) can jump into
  HoldJumpSquat (`0x16C`) the same way HoldWait / HoldWalk do (`func_2470`: jump button, or tap
  jump with the stick flicked up): `sideb_hold_turn_jump()`, after the air check.

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

### Added: ground swing → air side B cancel, and a better link

- **Cancel (`sideb_ground_cancel_update()`, end of `kirby.c`, called from the swing loop
  `func_2467`):** in the ground swing (`0x171` on the ground), once the strong hit (from frame
  `sideb_cancel_hit_frame()` = 11) has hit a hurtbox or shield (`AttackModule(0x2727, 0x6)`),
  a side-special input (`global24 & 0x2000`) puts Kirby in the air and starts air side B
  (`0x153`). It goes through the air side-B limit (`func_72(global25)`) and counts as one air
  side B. The side-B main `func_2429` then applies a hop (`sideb_cancel_hop()`:
  `sideb_cancel_hop_x()` 0.8 forward, `sideb_cancel_hop_y()` 1.5 up, Kirby's gravity) after it
  sets the air kinetic type, so the speeds aren't wiped. `global74` marks the pending hop.
- **Link (`tools/kirby_sideb_link_acmd.py`):** the weak start hit (`specialsstart`, frame 3)
  launched at 58° (KBG 30, BKB 30), which carried opponents out of the swing's frame-11 strong
  hit. It now uses autolink angle 366 with KBG 30 / BKB 28 (forward air's linking values), so
  opponents travel with Kirby's slide. The ground swing (`specials`, also used by the
  low-charge `0x2B5` swing) gets a third strong hitbox (ID 2, copy of ID 0) at Z 17, size 4.5,
  for opponents who still drift a little. This extra reach applies to every non-max-charge
  ground swing.
- **Windbox:** the same tool adds a weak windbox to the ground swing (`specials`) on frames
  1–10: `Special_Hitbox` ID 3, hit group Part 1 (so it can't use up the strong hit's hit log),
  0 damage, angle 0 (forward, FacingRestrict 3), fixed knockback 20, rehit every 2 frames,
  flinchless / no hitlag / no effect, size 8 at Y 8 / Z 1 (over and around Kirby).
  `Remove_Hitbox(3)` on frame 11, right before the strong hit. It keeps opponents that are too
  close from crossing over Kirby. Bowser's windboxes are the template (they use 40 / angle 10).

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
`python3 tools/rpx_patch.py cross_f.rpx build/cross_f.rpx 0x10136C58=9` (current build: 9).
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
     flies in the **direction the stick is held** at `sideb_homing_speed()`
     (any angle; he turns around if it's held backwards), with no gravity.
     The direction is read every frame of the window, so the stick at frame 5
     sets the final direction. Stick inside `sideb_stick_deadzone()` (0.3):
     he flies **straight forward** with no vertical speed. If a target turns
     up within the window, he steers at it from then on.
   - `sideb_bounce_update()`, also called from `func_2467` (before the
     steering): the first time the air swing hits a hurtbox or a shield
     (`AttackModule(0x2727, 0x6)`: `0x2` hurtbox | `0x4` shield), Kirby gets `sideb_bounce_back()` (0.8)
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
   - `sideb_gravity_update()`: after flying (homing or straight) and without
     a bounce, Kirby's gravity and max fall speed come back at swing frame
     `sideb_gravity_frame()` (29).
   - `sideb_slow_update()`: if Kirby flew and didn't bounce, from swing frame
     `sideb_slow_frame()` (35) his **horizontal** speed is multiplied by
     `sideb_slow_factor()` (0.9) every frame (read with `KineticModuleF(0,
     0x1)`, set on energy 3). Gravity handles the vertical.
   - Side-B state lives in `global17` bits: `0x1` flew, `0x2` bounced, `0x4`
     gravity back (reset at the start of each swing).

### Air side-B limit (2 per airtime)

`global25` is the fighter's side-B condition script: every side-B check calls
`func_72(global25)` and only starts side B if it returns non-zero (Corrin uses
the same hook). Kirby's init `func_2242` now sets it to `sideb_air_condition()`:

- On the ground: always allowed (and the count resets).
- In the air: blocked once `sideb_air_max()` (2) air side Bs were used.

The count is bits `0x100` / `0x200` of `global17`. An air side B only uses one up once it's past
frame `sideb_count_frame()` (5) (`sideb_count_update()` in the side-B loop `func_2430` and the
swing loop `func_2467`; `global80` frame count, `global81` counted). Being KO'd (Dead main
`func_2286`) also resets the count. It resets in Kirby's landing mains
(`func_2281`–`func_2284`, statuses `0x16`–`0x19`), the ledge-catch main
(`func_2285`, `0x73`), and in `func_2247` (every frame of every special
status) whenever Kirby is on the ground. That covers side B landing inside
its own statuses.

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
  0x10136C58=9 \
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

## Added: stick drift in forward and up throw

Kirby's forward, back and up throws are status `0xDC`; the throw kind is int
`0x11000002` (`0x78` forward, `0x79` back, `0x7A` up; down throw is the
common `0x3E`). The throws move by animation (kinetic `0xF`, then `0x12` once
the ACMD flag `0x2100000D` lifts Kirby off the ground, in `func_1138`).

`throw_drift_update()` (end of `kirby.c`), called at the top of the throw loop
`func_1137`: while airborne in a forward or up throw, it sets energy 3's X
speed to stick X (`global48`) × the drift speed, with no braking, on top of
the animation's movement. The held opponent moves with Kirby.

Settings: `throw_drift_speed_f()` (0.8) for forward throw and
`throw_drift_speed_hi()` (0.4, half) for up throw.

Untested: if the throw's motion kinetic type ignores energy 3, the drift will
do nothing before the drop phase below. The fallback is moving Kirby's
position directly each frame.

### Forward/up throw: falling below the start height

The throw animations bring Kirby back to his starting height. The landing
impact effect plays at frame 36 (forward) / 46 (up), and the opponent is
released at 45 / 51. `throw_drop_update()` (throw loop `func_1137`): if Kirby
is still airborne and not touching the floor (`GroundModule(0x2722, 0x8)`) at
frame `throw_drop_frame_f()` (35) / `throw_drop_frame_hi()` (45), it:

1. pauses the animation there (`MotionModule(0x2713, frame)`,
   `MotionModule(0x4, 0)`);
2. switches to kinetic AIR_STOP (`0xA`);
3. makes Kirby fall at `throw_drop_speed()` (3.0) with the opponent still
   held. Stick drift still works.

When he touches the floor, the animation resumes, and the slam and the
release play there. Off stage, he carries the opponent to the bottom blast
zone. State bits in `global17`: `0x1000` falling, `0x2000` done (reset in
the throw main `func_1136`).

Fix: when the drop reaches the floor, the throw's motion kinetic type
(`0x12`) is restored. Otherwise the animation's bounce after the slam
doesn't move Kirby. This also happened on stage, because the drop check
fires one frame before the floor.

### Forward/up throw: attack/special finisher

While airborne in forward or up throw, pressing attack or special releases
the opponent right away:
- forward throw: at **60°**;
- up throw: as a **spike** (270°).

Damage and knockback are the same as the normal throw.

- **ACMD** (`build/acmd/game.bin`; `throwf` / `throwhi`): before the release
  (`Throw_Applier` at frame 45 / 51), `IS_FLAG(0x21000012)` → `True` →
  re-specify throw 0 with the new angle. Without the flag the throw is
  unchanged. ACMD branch offsets count words from the branch command
  itself; `True(o)` runs the next `o-2` words only when the condition holds.
- **MSC** `throw_finish_update()` (top of the throw loop `func_1137`): on
  `ControlModule(0x2710, 0/1)` it sets `0x21000012`, stops a drop if one is
  running, and jumps the animation to one frame before the release. Once
  `CatchModule(0x2712)` reports the opponent is gone, it ends the throw:
  Fall (`0xE`) in the air, Wait (`0`) on the ground.
- Only **before landing**: the throw status counts as "air" the whole time,
  so the check uses the animation instead. It's allowed after lift-off
  (frame 9 / 6) and before the landing frame (35 / 45), or while dragging
  the opponent down, but not after the drag has landed.
- Before skipping frames it switches to kinetic AIR_STOP (`0xA`) with the
  speeds zeroed. With the throw's motion kinetic, skipping animation frames
  also applies the animation's movement, so the up throw snapped back down to
  its start height. It also marks the drag as done (`global17` `0x2000`) so
  `throw_drop_update()` doesn't pause the animation again.
- If the ACMD doesn't follow the frame jump, the throw just plays on to its
  normal release frame and still uses the finisher angle.

### Throw loop points and finisher window (update)

- The loop (pause + fall) frames are now **32** for forward throw
  (`throw_drop_frame_f()`) and **30** for up throw
  (`throw_drop_frame_hi()`).
- The attack/special finisher only works **inside the loop**: while Kirby is
  paused at the loop frame and falling (`global17` `0x1000`). It doesn't work
  before the loop or after landing.
- `throw_eat_inputs()` clears the buffered press when the finisher triggers
  and again when the throw ends. It uses the same calls Kirby's item pickup
  uses to consume an A press: `ControlModule(0x271B)`,
  `ControlModule(0x271F)`, and zeroing `global24/31/29/45/38`. This stops the
  press from also starting an aerial or special in the following Fall.

### Throw drop acceleration and up-throw spike momentum

- While dropping in the loop, Kirby's fall speed grows by
  `throw_drop_accel()` (0.3) each frame, starting at `throw_drop_speed()`
  (3.0) and capped at `throw_drop_max()` (12). The max fall speed limit is
  raised to match while dropping.
- Up throw finisher (spike): once the opponent is released, Kirby gets
  `throw_finish_down_hi()` (7.0) downward speed, with normal gravity and a
  raised max fall speed, then goes into Fall. If Fall clamps it back to his
  normal max fall speed, the effect is weaker than intended. Report it and
  it can be held for a few frames instead.

### Forward throw loop timer

- When the forward throw's loop starts (frame 32, dropping), a timer starts.
  After `throw_loop_time_f()` (10) loop frames without landing or a
  finisher, the throw ends normally where Kirby is: the drop stops, the
  throw's motion kinetic comes back and the animation resumes, so the
  opponent is released by the normal forward throw (frame 45). Afterwards
  Kirby goes into Fall (animation end in the air).
- The count is kept in bits `0xFF0000` of `global17`. It's cleared when the
  throw starts and when the loop starts. Up throw has no timer.
- A forward throw marks the air grab as used (`0x8000`, set in
  `throw_drop_reset()`), so Kirby can't air grab again until he lands or
  grabs a ledge. `airgrab_update()` doesn't clear `0x8000` during a forward
  throw, which is grounded until its lift-off. Otherwise a ground forward
  throw (after an air grab had landed) gave the air grab back and could loop
  into itself.
- Forward throw lock (`global17` `0x80`): it's set when a forward throw
  starts, and `airgrab_check()` refuses while it's set. The landing that
  clears it (`sideb_air_reset()`) only counts once Kirby has been airborne in
  something other than the throw or Fall (`0x8`, set by `fthrow_lock_update()`
  in `func_74`). So the throw's own landing, or the Fall straight out of it,
  doesn't give the air grab back. Kirby needs a real airtime and landing.

### Back throw: drift, drop, height damage, bury

Back throw is status `0xDC` with kind `0x79`. Code is at the end of `kirby.c`
(`throwb_*`) plus additions to `throw_drift_update` and `throw_drop_update`.

- **Drift and drop**: like forward throw. The drift speed is
  `throw_drift_scale_b()` (0.8) × the forward throw's (0.8), backwards only
  (stick input towards where Kirby faces is ignored). The loop frame is
  `throw_drop_frame_b()` (29), and the fall speed, acceleration and cap are the
  same. Right after lift-off (frame 13), energy 3 gets an extra upward
  speed of `throwb_lift_speed()` (2.0), fading to 0 by `throwb_lift_end()`
  (frame 25), so he goes about 13 units higher. That extra rise is added to the
  recorded start height, so it counts towards the damage (about +0.26×, i.e. 1.3× on the ground). There's no loop timer and no finisher, so off stage Kirby carries the
  opponent down to the blast zone.
- **Landing** (`throwb_land`, on the first floor contact at or after the
  loop frame): Kirby is put on the ground (`func_20(0)`, ground correction,
  kinetic `0xF`). All his speeds are zeroed, and they stay zeroed every frame
  until the throw ends. The animation then resumes to the release at frame 41.
  At the animation's end he goes to Wait instead of Fall.
- **Height damage**: `throwb_start()` (throw main) stores Kirby's Y in int
  `0x10000094` (tenths + 100000), and the extra lift is added to it. On
  landing, the drop (start Y − landing Y) gives a multiplier from 1.0× (no
  drop) to `throwb_mult_max()` (3.0×) at `throwb_height_max()` (115 units).
  The multiplier is rounded to 0.1 steps, and the tier (0–20) goes in int
  `0x10000095`.
- **ACMD** (`tools/kirby_throwb_acmd.py IN OUT`, run on an unedited throwb).
  There's one block per tier (`Int_Var_Compare(0x10000095, 0, t)` → `True`
  → command), and damage is 8 × (1 + t/10):
  - **Below 2.5×** (tiers 0–14): the normal back throw release, throw 0 at
    frame 41. It keeps the original angle 130° and BKB 30, with knockback
    growth at 60% (120 → 72) and no bury. Tiers above 10 use hitlag 3.0.
  - **2.5× and up** (tiers 15–20): a weak release (0 damage, 270°, fixed
    knockback 10) so the opponent stays on the ground. Then at frame 42 a
    `Special_Hitbox` slams them for 2 frames. It's copied from Kirby's Stone
    and uses bury (`0xB`), 270°, the original knockback (KBG 120, BKB 30),
    size 18 (was 12) with SDI 0 on bone 0, ground and air, and hitlag 3.0. This buries (tested at size 12; enlarged so it reaches opponents still slightly airborne).
- **2.5× and up** (tier ≥ `throwb_zoom_tier()` = 15):
  - **Zoom**: the Final Smash zoom `CameraModule(0x2714, 10, 0, 2.0)`
    starts as soon as the drop so far is worth 2.5×, already during the fall
    (`throwb_tier()` from the current height). It stays on until
    `throwb_zoom_time()` (20) frames after the release. Kirby int
    `0x10000093` counts down and is refreshed while the opponent is held.
    `throwb_camera_update()` in `func_74` then resets it with
    `CameraModule(0x2718)`, so it also resets if the throw is cancelled or
    Kirby is KO'd.
  - **Shake**: `CameraModule(0x2710, throwb_quake_kind())` (4; Kirby's own
    moves use 2 and 3) once the opponent is released and the animation
    reaches the slam (`throwb_hit_frame()` 42).
- **Above 2.0×** (tier > `throwb_big_tier()` = 10): 3× hitstop (ACMD), and
  from `throwb_cancel_frame()` (44, after the slam, because cancelling
    stops the ACMD), every frame runs `func_38()` (enable the ground groups)
    + `func_39()` (ground transitions), so any ground action cancels the
    throw.
- The slam hitbox buries (tested). Quake kind 4: if it crashes or does
  nothing, use 3.

### Down throw slide

- Down throw is the common Throw status `0x3E` with kind `0x7B`.
  `throwlw_slide_update()`, called at the top of its loop `func_1084`, sets
  energy 3's X speed to stick X (`global48`) × `throwlw_slide_speed()` (4.0)
  every frame while Kirby is on the ground, with no braking. The opponent
  stays attached, so they slide with him. The status's ground correction
  stops him at ledges.
- From `throwlw_final_frame()` (56, the final hit in the `throwlw` ACMD;
  the release is frame 58) the speed is set to 0 every frame, so Kirby stops
  dead on the final hit.
- **Air down throw landing loop** (`throwlw_land_*`, end of `kirby.c`): if
  Kirby lands during a down throw started from an air grab, the animation
  runs at `throwlw_land_speed()` (2×) its rate (`0x1000006`). It jumps from
  `throwlw_loop_end()` (43) back to `throwlw_loop_start()` (6)
  `throwlw_land_loops()` (9) times. Each jump back is a motion change
  at frame 6 (`throwlw_restart`, `MotionModule(0x1, motion, frame, rate)`),
  which restarts the ACMD too, so the stomps play again. Just setting the
  frame (`MotionModule(0x2713)`) doesn't rewind the ACMD: its final hit and
  release then came while the animation looped without the opponent.
  From the landing, `throwlw_land_hold()` keeps Kirby in place each frame
  while looping: kinetic GROUND_STOP (`0x6`, no movement and no animation
  movement), speeds zeroed, and he's put back on the ground (`func_20(0)`)
  if anything lifts him. The stick slide is off for the rest of the throw.
  Ground detection starts on frame `throwlw_land_check()` (4), so being on the
  ground during frames 0–3 doesn't start the loop yet.
  The loop is only armed when the throw starts off the floor
  (`!GroundModule(0x2722, 0x8)` in `throwlw_land_init`): an air grab or
  pummel can still have situation air while Kirby stands on the floor.
  Loop damage: Kirby int `0x10000099` = 1 while looping (0 normal, 2 done).
  The `throwlw` ACMD (`tools/kirby_throwlw_acmd.py IN OUT`) then uses a
  0.27-damage stomp instead of 0.8. That's 9 stomps per pass × 9 passes plus
  the partial first pass, about 22–24 total.
- **No staling**: the 7th value of the Throw status setup
  (`StatusModule(0x2713, ...)` in `func_1080`) is the stale-move negation
  bitfield, per `set_fighter_status_data` in
  `reference/msc-note-sheet/Complex_CMDs.csv`. It's normally `0x40001`.
  `throwlw_stale_bits()` makes it 0 for the down throw (kind `0x7B`), so the
  down throw, its stomps, the landing loop and the final hit don't stale. Then the rest plays at the normal rate. In the air the animation plays
  normally. The loop only starts if he lands before the final hit
  (`throwlw_final_frame()`, 56). Landing at or after it plays the throw out
  as usual. State is in Kirby int
  `0x10000098`: -1 = off, 0 = air and not landed yet, n = landed with n − 1
  jumps left. It's set in the down throw main `func_1082` and run from its
  loop `func_1084`.
- **Landing loop zoom**: when the loop starts, a slight zoom on Kirby
  (`CameraModule(0x2714, throwlw_zoom_in() 10, 0, throwlw_zoom_amount()
  4.0)`). The value works backwards: higher is farther. The back throw's
  big hit uses 2.0, and 1.4 was much closer than that. `throwlw_zoom_update()` keeps
  the shared countdown (Kirby int `0x10000093`) at `throwlw_zoom_after()`
  (12) until the final hit (frame 56). Then `throwb_camera_update()` resets
  the camera 12 frames later, or 12 frames after the throw ends early.

## Added: forward throw finisher explosion

When the forward throw finisher (attack or special while falling in the loop,
`throw_finish_update()`) is used, `throw_finish_effect_f()` spawns common
graphic `0x17` "Bomb Explosion" (`EffectModule(0x3, 0x1000017, ...)`)
`throw_finish_gfx_x()` (10) units in front of Kirby and `throw_finish_gfx_y()`
(6) above his position, size `throw_finish_gfx_size()` (1.0), with sound
`throw_finish_sfx_f()` (common `0x5E`, the sound of Kirby's forward throw landing impact). IDs come from the
global GFX list (`0x1000000` + list index; e.g. `0x39` small explosion, `0x91`
X Bomb explosion).

## Added: air grab

Pressing grab in the air starts Kirby's normal grab (Catch `0x35`) as an air
status. Code is at the end of `kirby.c` (`airgrab_check`, `airgrab_on`,
`airgrab_update`). State bits in `global17`: `0x4000` = air grab active,
`0x8000` = used this airtime.

- **Trigger**: `airgrab_check()` in the air transition checks `func_41`,
  right after the item-throw check `func_59`. It runs when the grab command
  (`global24 & 0x20000000`) is pressed and all of these hold: Kirby is
  airborne, the air grab is unused this airtime, he isn't holding an item
  (grab still throws items), and the aerial transition `0x1E000061` is
  enabled.
- **Air setup**: the setup functions of Catch `func_1032`, CatchPull
  `func_1037`, CatchWait `func_1059`, CatchAttack `func_1066`, Throw `0x3E`
  `func_1080` and throws `0xDC` `func_1135` use situation air, ground
  correction `0x5` and kinetic `0x13` (motion + gravity, like the aerials)
  while `airgrab_on()`. The `0xDC` throws use `0x12` instead, the same air
  kinetic they switch to on their own after lifting off. Kirby has his normal
  gravity while grabbing, holding and pummelling.
- **No forced breakaway**: the loops that normally send an airborne grabber
  to Fall or CatchCut (`0x3D`) skip that while `airgrab_on()`. Those loops
  are `func_1035`, `func_1040`, `func_1063`, `func_2273`, `func_2277` and
  `func_1084`. The pummel/throw selectors `func_2269` and `func_1062` also
  accept the air, so pummel and all four throws work in the air.
- **Missed grab**: when the grab animation ends in the air, Kirby goes into
  Fall.
- **Slower grab**: from frame `airgrab_slow_frame()` (14) the air grab's
  animation (and so its ACMD) runs `airgrab_slow()` (1.4×) slower
  (`airgrab_slow_update()` in the Catch loop `func_1035`, rate 1/1.4), also
  after landing. Kirby int `0x1000009A` = 1 when the grab started in the air
  (set by `airgrab_check()`); a grab that starts on the ground clears it,
  because `0x4000` can still be left over from an earlier air grab that
  landed.
- **CatchPull in the air**: CatchPull (`0x36`) normally lasts one frame and
  then becomes CatchWait. Its loop (`func_1041`) only did that on the ground,
  and its other exit waits for the end of a looping animation. So in the air
  Kirby stayed in CatchPull, where pummel and throw inputs aren't read. It
  now also changes over while `airgrab_on()`.
- **Air throws**: the throw loop `func_1137` sends an airborne throw to Fall
  while transition `0x1E000093` is on. That transition stays on until the
  throw lifts off (`func_1138`). An air throw is airborne from its first
  frame, so it was cancelled at once. The check is skipped while
  `airgrab_on()`. Down throw is status `0x3E`, which has no such check.
- **Landing breakaway**: landing during the hold, a pummel or down throw
  used to free the opponent. `airgrab_update()` cleared `0x4000` on the
  first ground frame. If the situation flickered back to air for a frame,
  the grab loops' own "airborne and not an air grab → Fall / CatchCut"
  checks ran and let go. `0x4000` now stays set after landing and is only
  cleared by `sideb_air_reset()` or the next air grab (`airgrab_on()` also
  needs the air, so it's off on the ground anyway). Bit `0x400` of
  `global17` means "already landed", so kinetic `0xF` is set once. Down
  throw (`0x3E`) lands like the others again.
- **Hold timer**: opponents can't escape an air grab normally. After
  `airgrab_hold_time()` (68) frames of CatchPull, CatchWait or CatchAttack
  in the air, Kirby goes into Fall, and the grab statuses' end scripts
  release the opponent. The count is kept in bits `0xFF0000` of `global17`
  (shared with the forward throw timer, which resets it when a throw
  starts).
- **Landing mid-grab**: on touching the floor, `airgrab_update()` switches
  Kirby to the ground with kinetic `0xF` and the grab carries on as a normal
  ground grab. `0xDC` throws keep their own landing code.
- **Once per airtime**: `sideb_air_reset()` (landing statuses and ledge
  grab) clears both bits. The side-B init keeps them.
- **Untested risk**: the grabbed opponent's own capture statuses are in
  their fighter's MSC. If their side forces them out when the grabber is
  airborne, that needs a different fix.
- **Air down throw**: a down throw (`0x3E`, kind `0x7B`) from an air grab
  falls during the animation with `throwlw_air_gravity()` (0.4) × Kirby's
  gravity (`0x3000018`) and max fall speed (`0x3000019`). This is set every
  frame by `throwlw_air_update()` in `func_1084` and put back by
  `throwlw_air_end()` in the status end `func_1085` (bit `0x40` of
  `global17`). If he lands during it, the down throw carries on on the
  ground (with the stick slide).

### Side-B bounce: neutral B cancel

After the on-hit bounce (animation jumps to `sideb_bounce_frame()` = 40),
neutral B can cancel it from `sideb_bounce_nb_cancel()` (1) frame later. It
must be a neutral special press: `global24 & 0x1000` with none of the
side/up/down special bits (`0xE000`). Everything else still waits for
`sideb_bounce_cancel()` (6). Code: `sideb_bounce_cancel_update()`.

## Added: crouch jump (superjump)

Jumping while crouching or crawling (Squat `0x11`–`0x14` → JumpSquat `0xA` → Jump `0xB`;
standing back up, SquatRv `0x15`, doesn't count), or buffering the jump out of an aerial's
landing, running (Dash / Run / RunBrake / TurnRun / TurnRunBrake), a tilt or a smash attack
(`crouchjump_bufferable()`) while holding down on any jump squat frame (stick Y ≤
`crouchjump_buffer_stick()`, −0.5), is a superjump, `crouchjump_update()` (end of the main
loop `func_74`):

- **Height:** `crouchjump_height_mult()` (2.4) × the full hop's height. Height goes with the
  square of the takeoff speed, so the upward speed (gravity energy `0x1`) is set to the full
  hop's takeoff speed × `crouchjump_speed_mult()` (√2.4 ≈ 1.549). The full hop speed is the
  one the game's jump uses (native jump init `0x02E79940`): attribute `0x300015F` × work float
  `0x1000006` (`0x3000160` is the short hop's).
- **No short hop superjump:** status flag `0x21000005` (short hop; it also picks the JumpMini
  motions `0x1A`/`0x1C`) → a normal short hop.
- **Keeps the vertical speed:** for `crouchjump_hold()` (3) frames after takeoff the boosted
  speed (minus gravity `0x3000018` per frame) is set again if the jump lowered it.
- **Momentum:** Kirby's ground speed during the jump squat (X change per frame) ×
  `crouchjump_momentum()` (0.8) is added to his horizontal air speed (energy `0x3`).
- **Trail:** while airborne and still rising, common GFX `0x10` ("Small star (fastfall)",
  `crouchjump_gfx()`) spawns at his position every `crouchjump_gfx_every()` (3) frames, size
  `crouchjump_gfx_size()` (1.0). (The first version used `0x94`, the white knockback streak.) Smash 4 has no body-afterimage effect; the
  `AFTER_IMAGE*` ACMD commands are sword trails. Other IDs to try: `0x1000010` small star,
  `0x100002F` aura particle, `0x100008C` transparent dash.
- State (new globals): `global62` previous status, `global63` state / frame count, `global64`
  jump-squat ground speed, `global65` last X position, `global67` boosted takeoff speed
  (`global66` unused).

## Added: air side B reflector

`tools/kirby_sideb_reflect_acmd.py` adds a reflector to the air swings (status `0x171`):
`SpecialAirS` (motion `0x2C1`, hitboxes frames 11–29; the low-charge `0x2B9` JUMPs to it) and
the max-charge air swing (`0x2C9`, hash `0xFFBD29D0`, hitboxes frames 11–13). At frame 9
(2 frames before the hitboxes) `REFLECTOR` + `SHIELD_ON(3, 0, 3)`; right after the first
`Remove_All_Hitboxes`, `Shield_Off2(3, 0, 3)`. Kind 3 = reflector, ID 0, group 3, the same as
Kirby's Zelda copy (Nayru's Love, `ShieldModule(0, 0x3, 0, on/off, 0x3)` in `func_2887`).
Box: capsule on bone 0 from (0, 5, −3) to (0, 5, 12), size 8; reflected projectiles ×1.5
damage, ×1.2 speed, up to 999 damage, ×1.2 lifetime. If the swing status ends early,
`sideb_reflect_off()` (main loop) turns it off.

## Added: jab, rapid jab, neutral air, forward air

- **Jab 1 → rapid jab:** Attack11 (`0x25`, main `func_263`) goes straight to Attack100 (`0x26`)
  (`jab_to_rapid()`).
- **Rapid jab hold:** it loops while the attack button is held; releasing it after at least one
  full loop (`rapidjab_loop()`) plays the finisher (`rapidjab_cancel()` keeps flag `0x21000015`
  on for the first loop and turns it off on release after that).
- **Rapid jab cancel:** after one full loop (`global71` frames in the loop ≥ the loop motion's
  length) and before the final hit (finisher motion `0x55`, its hitbox at frame
  `rapidjab_final_frame()` = 5), `rapidjab_cancel()` (top of the loop `func_337`) goes into any
  attack from the command bits in `global24`: tilts `0x2`/`0x4`/`0x8` → `0x28`/`0x29`/`0x2A`,
  smashes `0x10`/`0x20`/`0x40` → `0x2B`/`0x31`/`0x2E`, specials `0x2000`/`0x4000`/`0x8000`/`0x1000`
  → `0x153`/`0x154`/`0x155`/`0x152`, grab `0x20000000` → Catch `0x35` (checked first).
  Plain jab isn't included (mashing A keeps it going). Not from the finisher's hit frame
  (`rapidjab_final_frame()`, 5) on, except with **Overdrive** (`global83`): then the finisher can be
  cancelled too, during and after its hit (that was the whole Rush trait's before; user).
- **Neutral air = rapid jab:** `func_310` plays rapid jab's loop motion `0x54` (animation and its
  ACMD, which calls the hit `0xDCD907DA` every 4 frames and loops) instead of AttackAirN `0x68`.
  It loops while attack is held; letting go after at least one loop plays the finisher `0x55`
  (`nair_rapid_update()` in `func_317`), then Fall.
  `0x11000002` keeps `0x68` (neutral air's landing lag), and flag `0x2100000D` (landing lag)
  stays on for the whole move. Before the finisher's hit (frame `rapidjab_final_frame()` = 5)
  landing has neutral air's full lag; from that frame on, `global75` = 1 and LandingAir's init
  (`func_586`) calls `nair_rapid_landing()`, which plays the landing at
  `nair_rapid_landing_mult()` (0.5) times the lag.
  Landing goes straight to LandingAir (`0x18`) from `nair_rapid_update()` whenever Kirby touches
  the ground in the loop or finisher, instead of relying on flag `0x2100000D` (with only the
  flag, it landed with almost no lag in-game).
- **Air rapid jab cancel (`nair_rapid_cancel()`):** after one loop and before the final hit:
  grab → Kirby's air grab (`airgrab_try()`, same once-per-airtime / item / after-forward-throw
  limits as `airgrab_check()`, without the aerial-transition check), specials → `func_58`
  (air specials enabled with `0x1F00000A`), attack with a direction (command bits `0x2`–`0x40`)
  → `func_63` (aerials enabled with `0x1F00000E`). Plain attack doesn't cancel; it would only
  restart neutral air. The finisher can't be cancelled from its hit's frame
  (`rapidjab_final_frame()`, 5) on, except with **Overdrive** (`global83`), where it can be
  cancelled during and after its hit (that was the whole Rush trait's before; user).
- **Air hitboxes (loop 60% damage, finisher 65% knockback):** neutral air sets status flag
  `0x21000024` (`nair_rapid_air_flag()`) when it starts. `tools/kirby_rapid_air_acmd.py` turns
  each hitbox of the loop hit `0xDCD907DA` and the finisher `attack100end` into
  `IS_FLAG(0x21000024)` True → air version, False → the original. Air loop hits: Damage × 0.6
  (1 → 0.6). Air finisher: KBG/BKB/WBKB × 0.65 (120/80 → 78/52). Ground rapid jab never sets
  the flag.
- **Air drift 70%:** every frame of the air loop and finisher, `nair_rapid_drift()` sets the
  control energy's (energy 2, stick drift) max speed to Kirby's air speed (`0x3000016`) ×
  `nair_rapid_drift_mult()` (0.7): `KineticModule(0x15, 0x2, x, 100)`, as the Ryu copy and Final
  Cutter's fall do. Air acceleration is unchanged.
- **Air jumps:** `tools/kirby_jump_articles_acmd.py` removes the test `GENERATE_ARTICLE`s from
  `jumpaerialf3`–`f5` (six each).
- **Forward air autolink:** `tools/kirby_fair_autolink_acmd.py` gives the first hit's hitboxes
  (frame 10) the second hit's Angle 366 / KBG 30 / WBKB 0 / BKB 28.

## Added: copy ability traits

See `docs/character-traits.md`. While Kirby has a copy, `kirby_trait_update()` (main loop
`func_74`) looks up the copied fighter's trait (`kirby_copy_trait()`), keeps it in `global76`, and
writes `0x4B490000 + profile` to int `0x1000008E` for the executable's stat scaling
(`tools/kirby_stat_cave.py`; needs the current `build/cross_f.rpx`).

- **Rush** (Captain Falcon, Sonic, Corrin, Little Mac): ×1.25 movement stats (not jump height); neutral air is
  the air rapid jab (`kirby_rapid_nair()` in `func_310`).
- **Strike** (Bowser, Marth, Donkey Kong): neutral air is jab 2 (`attack12`, motion `0x51`) in the air
  (`kirby_strike_nair()` / `strike_nair_start()` in `func_310`, `strike_nair_update()` in the loop
  `func_317`). `strike_nair_start()` sets status flag `0x21000025` (`strike_nair_flag()`), plays
  `0x51`, and turns landing lag on (`0x2100000D`; `0x11000002` keeps `0x68`, neutral air's lag).
  `tools/kirby_strike_nair_acmd.py` edits `attack12` in `game.bin`: with the flag, frame duration
  1.6 from the start and 1.4 from frame 7, and the air hitbox (user's: Damage 6, Angle 43, KBG 32,
  BKB 60, Size 3, Z 17.5 → Z2 7, Ground/Air 3) plus `SET_FLOAT(1.2, 0x0F000052)` (1.2× hitstun on
  whoever it hits); without the flag (grounded jab 2) the original hitbox. From frame
  `strike_nair_grab_frame()` (4), grab (`global24 & 0x20000000`) cancels it into an air grab
  (`airgrab_try()`). From frame `strike_nair_special_frame()` (1 = any time), any special
  (`global24 & 0xF000`) cancels it: air specials are allowed (`0x1f00000A`) and `func_58()` picks
  the special with its usual conditions (e.g. up B once per airtime). Touching the ground:
  LandingAir (`0x18`). Confirmed in game (user).
- Without a copy, or with a non-Rush / non-Strike copy, neutral air is Kirby's normal neutral air
  (`kirby_rapid_nair_without_copy()` = 1 brings the rapid jab back for plain Kirby).

## Added: up B once per airtime, neutral-special cancel with a copy

- **Once per airtime:** up B sets `global77` when it starts (`upb_start()` in the main `func_2290`);
  `upb_air_condition()` (hooked as `global26`, the up-B condition script) blocks up B in the air while
  it's set. It clears on the ground (any grounded status except up B itself), when hit (Damage
  statuses `0x45`–`0x4C`, CaptureDamage `0x41`, DownDamage `0x57`), on ledge grab (`func_2285`) and
  when KO'd (`func_2286`) (`upb_air_update()` in the main loop `func_74`). A ground up B counts too:
  Kirby can't up B again until one of those happens.
- **Cancel:** with a copy ability (flag `0x2000009A`), from frame `upb_cancel_frame()` (31) of
  up B (counted from its start, across the rise and fall statuses), neutral special (B with no
  direction: command bits `0x1000` without `0xE000`) cancels up B into the copy's neutral special
  (`upb_cancel_update()` at the top of the rise `func_2291` and fall loops `func_2295` /
  `func_2299`). Before the neutral special, `upb_cancel_stop()` zeroes kinetic energies 0, 2 and
  3 (after up B hit someone, the cancel flung Kirby very high and fast) and keeps Kirby's total
  vertical speed (`KineticModuleF(0, 1)`), capped at `upb_cancel_rise_cap()` (2.5) going up, in
  the gravity energy (1). The neutral special's start resets the gravity energy (the rise was
  lost at once, user), so `upb_cancel_carry()` (main loop `func_74`) sets it again on the first
  `upb_cancel_carry_frames()` (2) frames in the air after the cancel, only raising it
  (`global87` frames left, `global88` the speed).
  `global78` = up-B frames. In the rise (`0x154`) the animation must also be at that
  frame (`MotionModuleF(0x1)` + 1 ≥ 31, the ACMD's frame count), so a game frame counter that runs
  ahead of the animation can't open it early (user: it was cancellable before frame 20).
  (Before: 3, then 6 frames after the first hitbox, 14, 20;
  `global79` still records the frame the first hitbox appeared.)
- Note: Kirby's ground up-B rise script (`specialhi`) isn't in this `game.bin` (air up B `JUMP`s to it),
  so the first hitbox may be the fall's (`0x2D1`, frame 1 of `0x172`). The cancel goes by whatever
  hitbox actually comes out first.

## Added: Luigi / Sonic copies: momentum and Luigi's wavedash

- **Momentum conservation (Sonic or Luigi copy, `kirby_momentum_copy()`):** a jump (Jump pre
  `func_472`) and a roll-off (roll ends `func_381` / `func_382`) take the air speed cap off (flag
  `0x20000044`) until Kirby is on the ground / a ledge (`global93`, `kirby_momentum_update()` in the
  main loop `func_74`; Fall's end `func_535` no longer puts the cap back then). Air friction still
  slows him. With **Luigi's** copy the carried speed only goes down (`momentum_decay_only()`,
  `global94`: energy 3's X speed can't go above both the max air speed and the carried amount); with
  **Sonic's** it's only the cap removal, so the speed can go up (user).
- **Luigi's Melee air dodge / wavedash (Luigi copy, `kirby_melee_dodge()`):** the same code as
  Luigi's (`fighters/luigi/README.md`): directional dodge (3.1, 10% decay to frame 30, helpless
  after, ledge grab), wavedash on landing, buffered wavedash out of jumpsquat with the 89° perfect
  wavedash, no shield from the dodge's own press, no walk / turn until the stick is neutral. Hooked
  into Kirby's common scripts (`func_62`, `func_365` / `func_375` / `func_378` / `func_379`,
  `func_478` / `func_479`, `func_487` / `func_488`, `func_502`, `func_509`, `func_977`, `func_50` /
  `func_52`, …); globals `global89`–`global92`. ACMD (`tools/kirby_luigi_airdodge_acmd.py`):
  EscapeAir's `Set_Kinetic_Handler(0)` at frame 19 only without status flag `0x2100001F` (the Luigi
  dodge's), so Kirby's own dodge is unchanged.
  **Not ported:** Luigi's 2.5 ground collision drop (`GroundModule(0x1A, x, y − 2.5)`, in the
  jumpsquat wavedash and the stick-neutral air dodge). Kirby's collision is small, so it ended up under
  the stage and a buffered wavedash fell through it (user).

## Removed: Marth copy forward smash

With Marth's copy Kirby's F-smash became Marth's (Roy-copy Flare Blade retimed, then Marth's own
`AttackS4S` retargeted onto Kirby, `kirby_marth_sword.py --marth`; commits 917294e..e362d2c). Removed
at the user's request (they'll animate their own); in game only the sword's trace showed, not the
sword. `kirby.c` is back as it was before (F-smash statuses `func_286` / `func_288` / `func_292`,
air Shield Breaker in `func_2919` / `marth_full_charge_fx()`), slots `0x381` / `0x383` play the game's
own animations again, and scripts `0x304` / `0x305` are gone from `motion.mtable` (`game.bin` back to
the user's). `tools/omo.py` still reads rotation type 10 (compressed quaternions, Smash Forge's
`OMOOld.cs`).

## Added: Marth copy sword in Strike neutral air, back air and up air

**History.** v1 (named motion slots `0x301`–`0x303` + animations in `marthbody`) T-posed: a motion's
animation isn't found by its name. A nested call in the MSC (`func_22(marth_sword_motion(var0), …)`)
then broke every aerial until removed (`docs/MSC-C_Guide.md`). A test animation named
`…SpecialNEndMax` didn't change the full-charge Shield Breaker end. Traced with
`tools/motion_debug_cave.py` (Cemu memory reads, user):

**How Kirby's motions pick animations.** The RPX's data has Kirby's static motion tables, 1222
entries each, of animation **file-name hashes** (CRC32 from 0, i.e. `zlib.crc32(name, 0xFFFFFFFF)`,
of the full name without `.omo`, case kept; the pack loader `0x03326740` keys files the same way):
- `0x103850A4`: main body, 8 bytes a motion (hash, flags word: e.g. `0x4`; the game ORs `0x80`
  in at runtime). It's `[MotionModule+0x18]`'s first field (count 1222 after it) and what
  `0x02C5D4EC` reads (`[this+0x1C]`).
- `0x10382A0C` / `0x10383D24`: Kirbypt1 / Kirbypt2 (part bits 6 / 7), 4 bytes a motion
  (`[MotionModule+0x18]` + 8: part entries; parts 1 and 3 have no array).
- Marth's `0x380` (EndMax) has the same hashes as `0x37F` (End): the full charge reuses the End
  animation, which is why the EndMax test changed nothing. Motions above `0x30A` are copy
  motions (the copy-change code `0x02EFE138` checks the current motion against `0x30A`).

**v2 (slots `0x301`–`0x303` with patched tables): the aerials animated, without the sword** (user).
So the sword shows only in the Marth copy's own motions, `0x37D`–`0x384` (the only check against
`0x30A` in the code is the copy-change one; Shield Breaker's charge loop `0x37E` shows the sword
with no sword-trace effect).

**What shows the sword (tested):** with the v3 RPX, Strike nair keeping the slot's own effect
script (the full-charge end's) showed the sword; bair / up air with their own effects didn't. So the
Marth copy's **effect script** switches it on: `Sword_Trace` on `LHaveN` (from frame 3 in
`MarthSpecialNEndMax`) to `Terminate_Sword_Glow`. (The v3 "no sword" test had the old RPX.)

**v4 (now):** v3's slots, plus effect / sound scripts for the three aerials: their own scripts with
Marth's `Sword_Trace` added at the appear frame − 1 and `Terminate_Sword_Glow` at the gone frame − 1,
named `MarthSwordAttack12` / `MarthSwordAttackAirB` / `MarthSwordAttackAirHi` in the empty slots
`0x301`–`0x303` (`motion.mtable`); `marth_sword_play()` binds them as the effect / sound set (`0x10`)
and the move's own game script. The slots' expression scripts (`MarthSpecialNEndMax`,
`MarthSpecialAirNEndMax`, `MarthSpecialAirNLoop`; the MSC can't rebind expressions) are the aerials'
own: up air had the air charge loop's endless rumble. Nair's blade points straight forward (model
+Z) from the hand (user: it was rotated oddly).

**v5 (user):** the sword is **twice the size** (`SIZE`), bair's blade points **straight back** (model
−Z, grip still between the knees). The bone's local transform is now solved so the blade's world
direction and length are exact even where Kirby's body squashes unevenly (the parent matrix
isn't a plain rotation × scale there): local axes = the parent-space images of the wanted ones,
each scaled to the wanted world length (`local_for()`); only the blade's cross-section can skew.

**v3 result (user): no sword either**, with Marth's own slots and Shield Breaker unchanged in look,
so it isn't the motion slot. Not in the animations' own data either (OMO header field `0x08` is a
per-pack date stamp; the body's `material_anime_face` / `_eyelid` MTAs for the Marth animations only
have face meshes; `marthsword`'s `model.mta` is empty). Next test: whether the copy's effect script
(`Sword_Trace` on bone `0x18` in the End scripts) is what shows it.

**Now (v3):** three of Marth's slots carry the sword animations: `0x380` (was the full-charge
ground end) → Strike nair, `0x384` (full-charge air end) → back air, `0x382` (air charge loop) →
up air. Shield Breaker's animation slots come from `func_2919` (MSC): the full-charge ends now
play `0x37F` / `0x383` (they had the same animations already) and the air charge plays the ground
charge `0x37E` (the legs are bent as on the ground; up to ~2 units off). Its hitboxes don't depend
on the slot: `func_2920` / `func_2921` bind Marth's scripts by special number
(`copy_custom_motion(arg0, 0x12)`), and `marth_full_charge_fx()` binds the full-charge ends' own
effects and sounds (Kirby's scripts for `0x380` / `0x384`, set `0x10`, `tools/copy_fx_cave.py`).
The RPX tables get the sword animations' hashes and the original moves' flags in those slots,
`fighter_param_vl_kirby` group 1 the original moves' values, and `marth_sword_play()` (end of
`kirby.c`) plays the slot with the Marth copy, then binds the original move's game script
(`MotionAnimcmdModule(0, 0, motion, 8)`) and effects / sounds (set `0x10`). No `motion.mtable` or
ACMD changes.

Build: `python3 tools/kirby_marth_sword.py <kirby folder> <script/animcmd/body>
<fighter_param_vl_kirby.bin> build/cave_fix_s4/cross_f.rpx build/marthsword`, then the standard RPX command with
`$(cat build/marthsword/rpx_args.txt)` added at the end.

With Marth's copy (kind `0x12`), Kirby holds Marth's sword (user): **Strike neutral air** (air jab 2)
in the left hand from frame 3, shrinking from frame 7 to nothing at 15; **back air** between the legs
from frame 7 (grip between the knees, blade toward the feet), shrinking 17 → 27; **up air** on the
left leg from frame 4 (grip at the knee, blade along the leg), shrinking 16 → 28.

How the copy's sword shows (traced): it's its own model (`model/marthsword`, bones `HaveN` →
`SwordN`, meshes `WeaponbladeM_VIS_O_OBJ` / `WeapongripM_VIS_O_OBJ`; the RPX's held-model table at
`0x1041A8A0` + kind × 4 names it) on Kirby's `LHaveN`. No MSC / ACMD shows it and the animations have
no track for it: it shows while Kirby plays an animation from the copy's motion folder
(`motion/marthbody`). Tested in game: Strike nair playing motion `0x383` (MarthSpecialAirNEnd)
showed it.

Motion names: a `motion.mtable` entry is the CRC32 of the motion's name (ACMD scripts are found by
it; e.g. `MarthSpecialNStart` for `0x37D`). Animations aren't found by it (see above). Slots
`0x301`–`0x30A` are empty (between Final `0x300` and `CaptainSpecialN` `0x30B`) and unused by the MSC.

- **Motions (v3):** `0x380` (Strike nair), `0x384` (back air), `0x382` (up air).
  MSC `marth_sword_motion()` picks them with the Marth copy in
  `strike_nair_start()` / `strike_nair_update()` and the AttackAir main (`func_310`); int
  `0x11000002` still holds the vanilla aerial kind (landing lag etc.).
- **Animations / ACMD:** `tools/kirby_marth_sword.py` (command above) copies Kirby's `Attack12` / `AttackAirB` / `AttackAirHi`
  (main, `kirbypt1`, `kirbypt2`) into the `marthbody` packs as `...MarthBody...D00<Name>.omo`; in the
  main animation `LHaveN` gets a per-frame position / rotation / scale track (the blade is
  `LHaveN` +Y; its X faces the camera, model X; "nothing" is scale 0.001). The bone math
  (`tools/omo.py`, forward kinematics from the animation) matches the game's hitboxes (jab 2's fist
  at Z ~18, its hitbox at Z 17.5). Kirby's arms stretch unevenly, so on a few frames the sword can
  look up to ~30% longer.
- **Files:** `build/marthsword/motion/marthbody/{main,kirbypt1,kirbypt2}.pac` →
  `fighter/kirby/motion/marthbody/`; `build/marthsword/fighter_param_vl_kirby.bin`; the RPX
  with `rpx_args.txt`.
- **Format notes** (`tools/omo.py` docstring): OMO tracks per bone, position / rotation / scale,
  constant, interpolated (min + range × u16 / 65535) or raw per frame; KCAP packs name-sorted. All
  of Kirby's 188 packs and the 2185 animations with known track types read and write back byte
  for byte.
