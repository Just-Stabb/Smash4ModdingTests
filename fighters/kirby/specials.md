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
  length) and until the frame before the final hit (finisher motion `0x55`, its hitbox at frame
  `rapidjab_final_frame()` = 5), `rapidjab_cancel()` (top of the loop `func_337`) goes into any
  attack from the command bits in `global24`: tilts `0x2`/`0x4`/`0x8` → `0x28`/`0x29`/`0x2A`,
  smashes `0x10`/`0x20`/`0x40` → `0x2B`/`0x31`/`0x2E`, specials `0x2000`/`0x4000`/`0x8000`/`0x1000`
  → `0x153`/`0x154`/`0x155`/`0x152`, grab `0x20000000` → Catch `0x35` (checked first).
  Plain jab isn't included (mashing A keeps it going). Not from the frame before the finisher's hit
  (`rapidjab_cancel_end_frame()`, 4) on (user), except with **Overdrive** (`global83`): then the finisher can be
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
- **Air rapid jab cancel (`nair_rapid_cancel()`):** after one loop and until the frame before the final hit:
  grab → Kirby's air grab (`airgrab_try()`, same once-per-airtime / item / after-forward-throw
  limits as `airgrab_check()`, without the aerial-transition check), specials → `func_58`
  (air specials enabled with `0x1F00000A`), attack with a direction (command bits `0x2`–`0x40`)
  → `func_63` (aerials enabled with `0x1F00000E`). Plain attack doesn't cancel; it would only
  restart neutral air. The finisher can't be cancelled from the frame before its hit
  (`rapidjab_cancel_end_frame()`, 4) on (user), except with **Overdrive** (`global83`), where it can be
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

- **Roll-off momentum (Kirby and every copy):** Hero's roll-off momentum (`fighters_rolloff_hero_v1`, docs/universal-mechanics.md "Roll-off" 6): the cap stays off while the stick holds the
  way he moves (`rolloff_hold_update()` from `func_82`, `rolloff_cap`); the Sonic / Luigi copy's
  roll-off no longer sets `global93` (was: until grounded).
- **Momentum conservation (Sonic or Luigi copy, `kirby_momentum_copy()`):** a jump (Jump pre
  `func_472`) (and, before `fighters_rolloff_hero_v1`, a roll-off) take the air speed cap off (flag
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

## Added: easier buffered wavedash (Luigi copy) and the Overdrive roll

- **Wavedash** (user: the input was very tight): the same as Luigi's (`fighters/luigi/README.md`,
  "Easier buffered wavedash"): a shield press up to 3 frames before the jumpsquat counts
  (`global96`), and an air dodge within 8 frames of a ground jump, at most 20 above the floor the jump
  left (`global95`), stick down or straight left / right, puts Kirby 0.1 above that floor so it lands
  at once (`wavedash_snap()`, in `melee_airdodge_entry()`).
- **Backward wavedash** (Luigi copy, user): the same as Luigi's: a jump press in a roll's first 3
  frames gives the buffered wavedash instead of the roll (`wavedash_roll_jump()`, `global97`), and the
  dodge's held shield press doesn't shield / roll anywhere on the ground until it's let go.
- **Overdrive roll** (Corrin copy, user): roll-off speed 2.8 instead of 2.1, x1.05 into the air
  (`overdrive_rolloff_air_mult()`). `rolloff_update()` sets status flag `0x2100001F` on every roll
  frame while Overdrive is on; the rolls' ACMD adds 2.8 when it's set, else 2.1
  (`tools/kirby_overdrive_roll_acmd.py`, after `rolloff_acmd.py --clear-first`).

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

**v6 (works in game, user: the sword shows in the aerials): what shows the sword, found.** Kirby's per-frame copy update (`0x02B02534`) shows the
copy's held model (`[fighter+0x28]+0xA8`: `marthsword`, `ikesword`, `gamewatchpan`, ...) only while
Kirby's **status kind** is in a fixed list (`0x181`, `0x18F`-`0x191`, `0x1BC`-`0x1C4` (Shield Breaker
is `0x1C1`-`0x1C4`), `0x1FC`, `0x202`-`0x205`, `0x20B`-`0x20E`, `0x21F`-`0x221`, `0x229`-`0x22B`,
`0x242`-`0x248`), and hides it in any other status. The aerials run in the aerial status, so
no script, motion slot or animation could show it; what the earlier tests took for the sword was
the `Sword_Trace` effect. `tools/copy_held_cave.py` hooks the hide path (`0x02B02730`) to take the
show path too while the motion kind is `0x380` / `0x382` / `0x384` (only the sword aerials play
those now). Added to the standard RPX command: `$(python3 tools/copy_held_cave.py)`. Test build
`build/marthsword_v6.zip` (v5's files, new RPX).

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

### Sword hitboxes (Marth copy aerials)

User: hitboxes along the sword in Strike nair, back air and up air, tipper style (the tipper hitting
the other way from the rest), with their Marth's aerials as the comparison and Kirby's own hitboxes
keeping priority. `tools/kirby_marth_sword_hitboxes.py KIRBY_GAME.bin MARTH_GAME.bin OUT.bin` adds
game scripts `MarthSwordAttack12` / `MarthSwordAttackAirB` / `MarthSwordAttackAirHi` (the sword
slots `0x301`-`0x303`' names): Kirby's move script plus three spheres on `LHaveN` (script bone
`0x18`) at Y 5 / 11.5 / 18. The sword's blade is along the bone's +Y (the held model's `HaveN` bind
rotation (90, 0, -90) turns its +Z blade onto +Y) at twice Marth's size: 3.6-21.4 from the grip; hitbox
offsets are taken without the bone's scale (as Smash Forge draws them). Base and middle copy their
Marth's blade hitbox of the same aerial, the tip his tipper (nair 6% at 0 / 7.7% at 150, bair 9% at
361 / 12.5% at 180, uair 9.5% at 80 / 13% at 270). Same part as Kirby's, higher IDs. Bair: Marth turns
around and hits in front (FacingRestrict 3); Kirby hits behind (4), which the sword's take. Timing:
nair and uair with Kirby's hitboxes; bair from frame 7 (the sword appears) for Marth's 5 frames.
`marth_sword_play()` binds the slot's game script instead of Kirby's (MSC: only that function differs,
`msc_fingerprint.py`). Not checked in game: the offsets (if the game scales them with the bone's
scale, the spheres land twice as far out).

## Added: Supamario copy (the Kamehameha; Supamario fix 90)

User: "make it so Kirby can take Supamario's copy ability". Copies come from the 12th star missile hit
(`starcopy_cave.py`), which hands over any fighter kind; `copy_grant` refuses kinds `>= 0x3A`, and every copy
table (hat, params, motions, weapon pools, `0x02F1B8B0`'s special params, about 22 switches on the copy kind)
has 0x3A rows, so Supamario (`0x41`) is copied as Mario:

- **MSC** (`kirby.c`, "Supamario copy" at the end): `starcopy_update` → `supa_copy_pending()` turns a
  pending `0x42` (kind + 1) into `4` (Mario) and sets int `0x100000A0` (copy_grant clears `0x83`-`0x9E` only);
  any other copy clears it. Mario's copy neutral B (`0x19A`) with it is Supamario's Kamehameha (`skame_*`, his
  `kame_n_*`): no Mario game script (`func_2585` / `func_2586`: its fireball), no staling (`func_2587`), the
  beam generated as article 5. Kirby's hand is his ACMD bone `0x10` (Mario's `0x11`), effects on it turned
  (0, 0, 139.8) (Mario's flash (140, 90, 180) on `0x11` = Kirby's (-179.8, 90, 0) on `0x10`, calls turn Z Y X);
  the start effects 2.92 lower, 0.67 further forward (the throws' frame 16, `LHaveN`).
- **ACMD** (`tools/kirby_supa_copy_acmd.py`): MarioSpecialN / MarioSpecialAirN effect and sound commands run
  only while `0x100000A0` is 0 (`Int_Var_Compare` / `True`); while 1, Supamario's release effects at frame 14.
- **Copy articles (native, traced for this):** Kirby's reserve article entries 0-20 (kind `0x10`, count 0) are
  never filled. A copy's weapons come from a per-copied-kind header table `0x1038281C` (58 pointers →
  `{records, count}`, records `{kind, max, spawner, extra}` like an article list; Mario's `0x101355A4` →
  `0x10135C8C`, 5 records: fireball (max 5, spawner `0x02F1AC88`), mantle, pump, hugeflame, dokan with max 0).
  `copy_grant` → `0x02EFDB88` builds the copy's pools once per copied kind per match (Kirby's copy object, int
  array `+0x2B4`: 7 kinds, 16 records each), `0x02EFE138` makes it current (`obj+0xB9CC`); with a copy, an
  article id below 16 is the record's index (`0x02C03EA0`) and the spawner is read from the record at every
  generate (`0x02EFE98C`). `weapon_expand.py` `"kirby_copy": 3` on the kamehameha: Mario's list copied to the
  cave plus `{0x18B, 1, 0x02F1AC88, 0}` (id 5, as in Supamario's own list), the header pointed at it (its
  ADDR32 `.data` relocation moved to the old list's first record's last word, `0x10135C98`), count 6. Weapon
  files load per fighter in the match for every kind its article list names (`0x030C3E7C`, count 0 too), and
  Kirby's copies load none of their own (only Game & Watch / Corrin's): reserve entries 19 / 20 now name
  `0x18B` and `0` (the fireball, whose 5 instances the Mario copy's pool makes), so they're there in a match
  without Mario.
- Mario's hat and params; the copy's trait is Mario's (Normal, as Supamario's).
- **Hat and motions (fix 91, user: Kirby T-posed in the Kamehameha and had no hat):** Kirby's copy resources
  (`fighter/kirby/model/...` hats, `motion/mariobody` ...) load per fighter in the match, by that fighter's kind
  (`0x030C5240`, called for the 8 match entries from `0x030C077C`; its helper `0x030C4694`; the release
  `0x030C5BBC`), and each returns at once for a kind `>= 0x3A`: a match with Supamario and no Mario loaded no Mario
  copy hat or motions, so the copy's motion `0x331` played nothing. `weapon_expand.py` `kirby_copy` now also maps
  the copied fighter's kind (`0x41`) to the copy's (`3`) in all three (their `mr rK, r4` -> `bl` a stub;
  `weapon_expand_test.py` runs the stubs on every kind). Supamario's body model is Mario's, so Mario's hat is his.

## Changed: Samus copy's Charge Shot keeps its charge on a hit

As Samus's (`fighters/samus/README.md`): the hold's exit (`func_2720`, status `0x1F1`) keeps the charge
(`0x10000084`) when the next status is a damage status (`0x45`-`0x4C`), the same way as a shield / dodge out;
the starts' exits (`func_2722` `0x1F0`, `func_2725` `0x1F4`) keep a stored charge on a hit and only remove the
shot article. Before, a hit cleared it. Mii Gunner's Charge Blast copy (`func_2577`) is unchanged.
Package `link_samus_v1`.

## Added: Hero / Sephiroth copies (hats, motions, Frizz / Flare) — `kirby_hero_sephiroth_copy_v1`

User: "Please give Kirby his hats for Hero and Sephiroth and add their copy abilities." Traits: Hero Shooter,
Sephiroth Technical (already in `kirby_copy_trait`; `kirby_trait_update` now asks it with the copied fighter's own kind,
`newcopy_real_kind()`).

### Ultimate data used (the user's `kirby-ssbu-partial.zip`, `lua2cpp_decomp.zip`)

- `kirby/model/copy_brave_cap/c00-c07` (3 meshes: `kirby_brave_001`, `met_brave11_001/002`; **no skeleton**: it sits on
  Kirby's `Headdress` joint, (0, 9.752, 0), unrotated (wrong: its vertices are offsets from Body's place, 5.17:
  "Visual fix v1"); the 8 colours have the same textures) and
  `kirby/model/copy_edge_cap/c00-c07` (3 meshes skinned to `Body` / `Puff` / `S_HairB1`, an alpha-sorted hair layer, and a
  `model.nuanmb` for the hair). `kirby/motion/copy_edge_cap/c00` (the hair's own d00specialn* motions, `motion_list.bin`,
  swing prc) is **not used** (the hat is rigid here).
- `kirby/motion/bravebody/c00` (12 `braved00special(air)n{start,hold,1,2,3,cancel}`) and `edgebody/c00` (8:
  start, 1, 2, cancel, ground / air). No motion_list in those folders: Kirby's `motion/body/c00/motion_list.bin` lists
  them with **no game scripts** (only expression / sound / effect: the copies' logic is status code) and the cancel
  frames (vl byte 2): Hero start 12, N1 44, N2 52, N3 68, cancel 6; Sephiroth start 172, N1 56, N2 70, cancel 8.
- `kirby/param/vl.prc`: no Hero / Sephiroth params of Kirby's own: the copies read the copied fighter's
  `param_special_n` (lua2cpp_kirby's Hero copy status reads `param_special_n` `sp_special_n1/2/3` and calls
  **`FighterSpecializer_Brave::add_sp` on Kirby**: Kirby's Hero copy has its own MP, paid from it as Hero's).
- Kirby's copy effect scripts, read from the recomp dump with `tools/recomp_acmd.py` (new):
  `reference/kirby_copy_ultimate_acmd.txt`. Hero: hold = `brave_chant` on top (0, 5, 0) turned (0, -60, 0) +
  `brave_fire1_hold` / `brave_fire2_hold` on `arml` (2, 0, 0); N1 / N2 `brave_fire1_flame` on `arml` (2, 0, 0) to
  12 / 11; N3 the flame on `throw`, `brave_fire3_appearance` on `throw` at 3, the flame on `handl` (1, 2, 0) 24-42.
  Sephiroth: start = `edge_fire1_hold` on `havel`; 31 `edge_fire2_hold` + `_flash`; 68 `edge_fire2_hold_aura` on both
  arms, `head` (3, 0, 0) and both toes; 100 `edge_fire3_hold_flash`; 102 the aura again + `edge_fire3_trigger`; 118
  `_aura_end`; N1 / N2 `edge_fire1_trigger` / `edge_fire2_trigger` on `havel`. Floats loaded from the NRO's
  .rodata aren't in the dump (`?f`): the head aura's size (taken as 1.0). No sound scripts were found in those
  ranges (the copies' sounds: not done yet).
- Not in the zip: Kirby's Ultimate effect / sound folders (none needed: the effects are Hero's and Sephiroth's own,
  in their banks).

### Design

**Granted as Robin's copy.** Kirby's copy tables have rows for kinds 0-0x39 only (copy_grant refuses more), so both
are granted as Kirby's **Robin copy (0x2C)**, the copy with the most neutral-special motion slots (14), no held model
and no copy set-up; the int **`0x100000A0`** says which (2 Hero, 3 Sephiroth; 1 Supamario, 0 other). exe_v44
(`tools/kirby_copy_new_cave.py`, tested by `tools/kirby_copy_new_test.py`) does it in copy_grant itself (swallow and
the star copy both), so `supa_copy_pending()` is empty now (the executable maps Supamario too).

**Hats and motions per copied player.** The copy resources load per player slot of the copied fighter (traced:
`0x030C4D30` runs the helper `0x030C4694` for each match entry, resource ids `0x20C + slot`, Kirby's costume in the
top bits = the hat's `cNN`), so a Hero player's slot loads `model/bravecap/cNN` and `motion/bravebody` in place of
`refletcap` / `refletbody` (two name reads swapped for kinds 0x45 / 0x42 only), and a Robin in the same match keeps
his. The hats: `tools/kirby_copy_hats.py` (one bone, TopN, in Kirby's head frame: the placement worked out from
Ultimate's and Smash 4's Robin hats, which agree to ~0.7: docstring; texture ids 0x40C5F000 / 0x40C2F000 + 0x80 x
costume; the hat bone is BodyBN at 5.17, not HeadN: "Visual fix v1"). The motions: `tools/kirby_copy_motions.py`
(since "Visual fix v1" re-parented through Ultimate's FK, with Ultimate's own face packs; stage 1 copied
Ultimate's tracks as they are, which put the legs 2.392 low: the bind poses agree but the parents don't), stored under
the Robin copy
slots' animation names (a slot finds its animation by the CRC32 of the name):

| Robin slot (ground / air) | Hero | Sephiroth |
|---|---|---|
| 0x446 / 0x44D SpecialNStart | SpecialNStart | SpecialNStart (the charge, Gigaflare) |
| 0x447 / 0x44E SpecialNHold (loops) | SpecialNCancel (and the misfire) | - |
| 0x448 / 0x44F SpecialNShoot | SpecialN1 | SpecialN1 |
| 0x44A / 0x451 SpecialNTronStart | SpecialN2 | SpecialN2 |
| 0x44B / 0x452 SpecialNTronHold (loops) | SpecialNHold | - |
| 0x44C / 0x453 SpecialNTronEnd | SpecialN3 | SpecialNCancel |

`kirbypt1` / `kirbypt2` (the body sphere and the face) were the Robin copy's own packs (Robin's timing); since "Visual
fix v1" they are Ultimate's Body / mouth tracks.

**Articles.** Robin's copy record list gets Hero's fireball (0x190, max 3, the thunder's spawner) and Sephiroth's fire
(0x18C, max 3, Din's Fire's spawner) as copy articles 6 / 7, and Kirby's reserve article entries 15-18 name the Robin
copy's book / thunder and these two (so their files load and the copy's weapon pools can be made in a match without
Robin, as Supamario's fix 90).

**MSC** (`kirby.c`, "Hero / Sephiroth copies", hooked into the Robin copy's 0x222 pre / main / end): the moves as this
mod's Hero and Sephiroth do them (`brave_n_*`, `edge_n_*`: the mod's changes kept: Hero's second-press fire, the
stored charge, Kafrizz stored at 81, the misfire with too little MP; Sephiroth's up / down 45-degree Flare, the roll
out of the charge, the buffered roll 6 frames after the fire, Flare playing out on shields (the article's own
`on_hit_bits`)). Motions through MotionModule with Kirby's own effect / sound scripts for the slots rebound to an
empty one (copy_fx_cave's set 0x10); no Robin game script; IASA by Ultimate's frames (func_39 / func_41).
**MP:** Kirby's own (Ultimate's add_sp on Kirby): full (100) when he gets the Hero copy, 1 back a second while he
isn't charging, Frizz / Frizzle / Kafrizz 6 / 16 / 36. (Ultimate's starting amount and refills for Kirby weren't read
from its ExeFS: full on copying is assumed.) **No gauge is drawn on Kirby yet** (the damage-panel cave draws Hero's
from Hero's ints 0x1000009C-9F, which Kirby uses for the star copy): part of the Stone / Command Selection stage.

### Approximations / not done

- Hats rigid (Sephiroth's hair doesn't swing; Ultimate's `copy_edge_cap` motions unused).
- Copy sounds (none read: Ultimate's sound scripts for the copies weren't found in the dump's ranges) and the
  `?f` floats; Hero's hold-level flashes `0x16500259b5` / `0x16cba715da` (not in Hero's bank) left out.
- Swallowing a Kirby who has the Hero / Sephiroth copy gives Robin's copy (the swallow code passes that Kirby's
  copy kind, 0x2C, without the marker).
- Din's Fire's spawner places the fire for Zelda; on Kirby where it appears is unchecked.
- Effect rotations as brave.c's (radians); bone effects not turned (Kirby's bones match Ultimate's).

### Build

```
python3 tools/kirby_copy_hats.py ULT/kirby/model S4/fighter/kirby/model OUT/fighter/kirby/model [--check]
python3 tools/kirby_copy_motions.py ULT/kirby S4/fighter/kirby OUT/fighter/kirby/motion [--check]
python3 tools/rpx_patch.py EXE_V43.rpx EXE_V44.rpx $(python3 tools/kirby_copy_new_cave.py)
python3 tools/kirby_copy_new_test.py EXE_V44.rpx EXE_V43.rpx
python3 tools/msclang/msclang.py -x tools/mscinfo.xml fighters/kirby/kirby.c -o kirby.mscsb
python3 tools/msc_stack_check.py kirby.mscsb fighters/kirby/kirby.c; python3 tools/rolloff_hold_test.py kirby.mscsb
```
(S4 = Smash 4's `fighter/kirby` with `model/refletcap`, `model/mariocap`, `model/body/c00/model.vbn`,
`motion/refletbody`: the user's `kirby - Copy.zip`.)

## Planned (next stage): Hero copy + Stone = Command Selection

User decision (2026-11-13): **sword spells (Metal Slash and the other sword spells) show Hero's sword on the
stone while they are cast** (the sword model attached to the stone at Hero's hand offset for the spell's frames,
hitboxes on it as on Hero), rather than hitting at the sword's position with nothing shown.

User (via the coordinator): with Hero's copy, Kirby's Stone (down special) opens Hero's Command Selection menu with all
of Hero's spells, Kirby's stone animation unchanged, the spells' hitboxes / articles / effects / sounds / status effects
as Hero's, at Hero's offsets. Plan (not built yet):
- **Menu and MP gauge on Kirby:** `tools/trait_badge_cave.py`'s panel draws Hero's window / gauge from Hero's ints
  `0x1000009C` (gauge), `0x1000009E` (window), `0x1000009F` (rows) for kind 0x45. Kirby's own ints there are taken
  (0x9C debug hop, 0x9D / 0x9E star copy count / pending kind, 0x9F the copy's custom slot), so the cave reads Kirby's
  three from free Kirby ints (0x93-0x9A, cleared by copy_grant: rewritten every frame) when kind 8 and 0x100000A0 is 2.
- **The menu logic** (`brave.c` "Hero's MP", `brave_lw_*`: the 4 random spells, costs, the cursor, the 8-second limit)
  copied into kirby.c on Kirby's Stone statuses (down special `0x155` / `0x175` / `0x176`): opening the stone
  (status 0x155 start) opens the menu; choosing casts the spell from the stone pose; Kirby's motion stays the stone's.
- **Spells:** the article spells (Sizz / Sizzle, Bang / Kaboom, Whack / Thwack, Snooze, Magic Burst / Kamikazee's
  crash, Zoom 2 U's homing) need Hero's weapon kinds 0x193-0x197 (+ the placed / crash articles) in the Robin copy's
  list (as fireball / fire: 8 more records, more reserve entries: 2 are left, so the reserve list or a per-copy
  file-load hook must grow), their spawners, and each weapon's MSC reading its owner's Hero-only work (checked per
  article). Offsets: Hero's are on his bones (`haver`, `top`, ...); Kirby's same-named bones (bind identical to
  Ultimate's) take them, from the stone's pose (no animation of their own). Buffs (Oomph, Psyche Up, Acceleratle,
  Bounce, Kaclang, Hocus Pocus) run through the same executable caves Hero uses (kirby_stat_cave profile 3 needs
  Kirby's marker 0x1000008E free of the trait bits; strike_cave's bit; brave_reflect_cave's reflector group 3 is set
  up only in Robin's set-up: Kirby's own reflector set-up exists, group to be checked); Zoom moves Kirby (status code);
  Kaclang's metal is the Metal Box item function (any fighter); Metal Slash / Hatchet Man / Kacrackle Slash are sword
  slashes: on the stone they'd be hitboxes at Hero's sword offsets without a sword (to be agreed with the user).
- **Needed from the user for it:** Hero's current package (`fighter/brave` script/msc/brave.mscsb + weapons' msc, his
  body / weapon ACMD folders and `motion.mtable`s) — or confirmation that `fighters/brave/*.c` in the repo is current —
  and Kirby's current body ACMD (`fighter/kirby/script/animcmd/body`: the Drive's copy is from Oct 23, before Supamario
  fix 90).

## Added: Hero copy, Stone = Command Selection (stage 2, `kirby_hero_sephiroth_copy_v2`)

With the Hero copy, Kirby's stone (down special: the hold, status 0x175) opens Hero's Command Selection
(`kirby.c` "Hero copy, stage 2", `khm_*`, a port of `brave.c` `brave_lw_*` / `brave_panel_update`): four spells drawn
with Ultimate's weights, unaffordable ones greyed and put last, the stick moves the cursor (12-frame repeat), attack or
special (once let go) casts, shield / jump / 480 frames shut it (the 2-seconds-left sound at 360). While it's open the
stone's own "special ends it" check (`func_2323`) is held off and his MP doesn't come back. The stone's motion, fall,
armour and timer are untouched: the spell plays out from the stone, its frames counted by `khm_update` (main loop).
**The menu and gauge on his damage panel:** exe_v45 (`tools/kirby_hero_menu_cave.py`, tested by
`tools/kirby_hero_menu_test.py`): the panel cave draws for kind 8 too, from Kirby's ints `0x1000008A` (gauge),
`0x1000008C` (window), `0x1000008D` (rows) (Hero's values, shifted: his own 0x9C-0x9F are the star copy's); the gauge
shows whenever he has the Hero copy.

| spell | on Kirby (v2) |
|---|---|
| Heal (7 MP) | 11% off his damage at frame 6, Hero's sound, the heal effect on his hip |
| Sizz / Sizzle | Hero's flash article (copy article 8) at frame 6, level 0 / 1 |
| Bang / Kaboom | Hero's explosion (article 9) |
| Whack / Thwack | Hero's deathball (article 10) |
| Snooze | Hero's sleep (article 11) |
| Magic Burst | all his MP; Hero's crash (article 12) at frame 20, its strength in fifths of the MP spent, on his slot (no hover: the stone falls) |
| Acceleratle / Oomph / Psyche Up / Acceleration | Hero's marker bits on Kirby's marker 0x1000008E: profile 3 (x2 speeds, 600 frames), 0x80 + 0x20 (720), 0x40 (to his next hit), 0x1000 (600; no Overdrive glow); the glows on his hip |
| Kamikazee, Kaclang, Bounce, Hocus Pocus, Zoom, Zoom 2 U, Flame / Kacrackle / Metal Slash, Hatchet Man | **not yet** (weight 0: never drawn) |

The articles come out of his hand as the Hero copy's fireball (Robin's thunder spawner); `fighters/brave/weapons/shot.c`
(Hero's flash / explosion / deathball / sleep) now takes the nearest Hero **or Kirby** as the caster (it searched for
kind 0x45 only, so a Kirby's Whack would have counted the opposing Hero as its owner: his damage for the KO chance,
and immune). Rebuilt with `brave_build.compile_msc` (thunder_base.c + shot.c + the article).

Not yet / approximated: the 12 spells above (Zoom moves the fighter through Hero's own statuses; Kaclang / Bounce /
Hocus Pocus use Hero-side state (Robin's reflector group, his metal and item hooks) to check on Kirby; the sword spells
need Hero's sword as a Kirby held model (the item-model table row for the Hero copy, as the hat) shown in the stone
statuses (`copy_held_cave.py` shows held models by status) and their hitboxes from Hero's scripts on Kirby's bones);
Hero's MP from damage dealt (0.8x) isn't on Kirby; the cast's own effects (Hero's spell motions' effect scripts) aren't
played (the articles' and buffs' are).

**Copy sounds found** (stage 1 follow-up): Kirby's Ultimate copy sound scripts are in the recomp dump
(`reference/kirby_copy_ultimate_acmd.txt`, end): Hero hold `se_brave_special_n01` (status loop) + `vc_kirby_copy_brave_01`
at 2, `se_brave_special_n04` at 97; N1 `n02` at 8, N2 `n03` at 11, N3 `n07` at 1 / `n05` at 17; Sephiroth charge
`se_edge_special_n01` (loop) at 1, `vc_kirby_copy_edge_01` at 2, `se_edge_special_n04_01` at 119; Flare `n02_01` at 2,
Megaflare `n03_01` at 2. Not played yet: their Smash 4 ids are positions in Hero's / Sephiroth's built sound banks
(`tools/ultimate_sound.py`, from the label lists), which aren't in the repo; and `vc_kirby_copy_*` is Kirby's
Ultimate voice, not in any Smash 4 bank.

### v3 (`kirby_hero_sephiroth_copy_v3`): Kamikazee, Kaclang, Bounce, Hocus Pocus, Zoom, MP from damage dealt

`kirby.c` "v3" (`khm_kamikazee` / `khm_kaclang` / `khm_zoom` / `khm_hocus_pocus` / `khm_v3_timers`), Hero's code
(`brave.c`) with Ultimate's frames (brave.zip `motion/body/c00`: SpecialLw9 = spell7 50 frames, SpecialLw10Start 21,
SpecialLw16's start = spell9start 30), all while Kirby stays the stone (its motion untouched):
- **Kamikazee:** the crash article's blast (level 1 + 8 x his slot) at 20; KO'd at 49 (the motion's end) with the
  instance flag "causes KO" 0x20000043 (a common flag: Whack's KO uses it on any fighter).
- **Kaclang:** from 20, invincible (0x0F00011C renewed each frame) and the Metal Box's metal (SELF_ITEM 1) for 300
  frames, falling fast in the air (Hero's accel 0.2 / max 3); then the metal off (SELF_ITEM 2). Over early if he leaves
  the stone (as Hero's at his status's end). The stone keeps its own armour as well.
- **Bounce:** 720 frames of Kirby's reflector group 3 with Hero's shape (ShieldModule 0x2717: 15 across, 12 up, x1.5
  damage, x1.2 speed), renewed every frame (Kirby's own set-up gives group 3 a shape; Hero's needed a cave for it), the
  barrier glow on his hip.
- **Hocus Pocus:** Ultimate's outcomes and odds (brave_hp_weight): giant, Starman, full MP, timer, no MP, poison,
  sleep (the game's sleep status: ends the stone), small, flower, invisible (600 frames), or another spell cast from the
  stone; the sword spells and Zoom 2 U weigh 0 (not on Kirby yet).
- **Zoom:** from 29 the stone goes up at 9 a frame for 40 frames, intangible, is put 120 above a random fighter on
  the ground and comes down at 7 a frame (intangible) until it lands (150 frames at most); the stone's own landing
  follows.
- **MP from damage dealt:** 0.8 x the damage the other fighters took while his attack has hit (position variables'
  DAMAGE, his HIT), not from his specials (statuses 0x152-0x155, copy specials 0x17C-0x250), at most 100.
- **Still not on Kirby:** Zoom 2 U and the four sword spells (Flame Slash, Kacrackle Slash, Metal Slash, Hatchet Man).
  The sword spells need (1) Hero's sword as a Kirby held model (Hero's sword mesh from Ultimate's model, converted as
  the hats, loaded for a Hero player's slot through the copy item-model table's name read, as the hat), shown during the
  stone statuses only while a sword spell is cast (`copy_held_cave.py` shows held models by status / motion: a Kirby int
  condition added), and (2) their hitboxes: Hero's SpecialLw17-20 game scripts (his built `game.bin`, translated from
  the smashline dumps the repo doesn't have) moved onto Kirby's bones.

### v4 (`kirby_hero_sephiroth_copy_v4`): Zoom 2 U

`kirby.c` "v4" (`khm_zoom2u`, `khm_z2_*`), brave.c's `brave_zoom2u` / `brave_z2_*`: the target is the nearest other
fighter at the cast; launched at frame 29 (it starts as Zoom: Hero's slot 0x23A = Ultimate's spell9start, 30 frames),
lifted 6 off the ground first; then 9 a frame at the target's feet + 6, re-aimed every frame, intangible, through
platforms (GroundModule 0x2715), turned to face the target; over within 15 of it, after 40 frames, or on meeting the
ground; then the vertical speed clamped to the air maximum (0x3000019) and the stone falls. The stone's status keeps
its own kinetics, so the flight moves Kirby through his position variables (as Zoom's placement does) with gravity held
at 0, instead of Hero's kinetic type 0xA / energy 3. Not ported: Hero's after-flight homing (up to 15 frames of tracking
into an aerial: the stone has no aerials). Drawn with Zoom's weight and cost (8 MP); not in Hocus Pocus (it isn't
Ultimate's).

**Sword spells, what was found for the held sword (not built):** the copy item-model table `0x1041A8A0` (marthsword ...)
is read only by the copy-resource loader (`0x030C46F4` `addi r25`, the read `0x030C48C8` `lwzx r7, r25, r21`, type
0x164), so the sword would load for a Hero player's slot the same way as the hat (a third name read swapped in
`kirby_copy_new_cave.py`, "bravesword"); whether Kirby's copy then creates the held-model object for the Robin copy
(whose row is empty) is not traced (the object is `[fighter+0x28]+0xA8`, shown / hidden by `0x02B02534`'s status list,
`copy_held_cave.py`). Still to do: trace that creation, convert Hero's sword mesh (Ultimate `brave/model/body/cNN`,
skinned to `sword1` / `haver`) as a held model (HaveN -> SwordN, as `marthsword`), show it in the stone statuses only
while a sword spell is cast (a Kirby int read in `copy_held_cave.py`'s hook), then the hitboxes from Hero's built
`game.bin` (SpecialLw17-20) on Kirby's bones.

### Crash fix v1 (`kirby_copy_crashfix_v1`): exe_v44b / exe_v45b

User: v1 crashed while loading (Cemu: IP 0 / LR 0 inside `PPCRecompiler_getJumpTableBase`; r23-r26 = the copy-resource
loader's four tables, r8 = 0x10420010, i.e. in the loader `0x030C4694` for a copied player's slot). Two faults in
`tools/kirby_copy_new_cave.py`, both fixed:
1. **The cave was outside the code Cemu runs:** exe_v44 put its code at 0x04BD4000-0x04BD6000, growing the text region
   past acmd_ext_cave.py's end (0x04BD4000) for it; the first call into it (the loader's hooks) jumped nowhere. Both
   caves now sit in free code inside kind_expand.py's region: 0x04BAF400-0x04BAF700 (kirby_copy_new_cave.py) and
   0x04BAF700-0x04BAFA00 (kirby_hero_menu_cave.py); no grow / textregion.
2. **The hat swap hooked the wrong read:** `0x030C487C` reads the held-item table (r24 = 0x1041A8A0, resource type 0x11:
   marthsword ...), so a Hero / Sephiroth player's slot loaded `bravecap` / `edgecap` as Kirby's held item (and Robin's
   hood as the hat). The hat is read at `0x030C4830` (`lwzx r7, r23, r21`, r23 = 0x1041A7B8 from `0x030C46E8`).
Tests that would have caught them (`tools/kirby_copy_new_test.py`, `kirby_hero_menu_test.py`): the hooked read's base
register must be the one the loader fills with the hat table (decoded from the loader's own `addi`s), and every cave
must lie in the code region the standard build already executes (below 0x04BD4000). exe_v44 fails both.

### v5 (`kirby_hero_sephiroth_copy_v5`): the Hero copy's sounds

`kirby.c` `ncp_hero_sounds`: Kirby's Ultimate Hero-copy sound scripts with Hero's Smash 4 ids, resolved from the
user's `sound/config/soundlabeltable.bin` (snd_se_Brave = bank 2051 = row 1892) and Hero's `snd_se_Brave.nus3bank`
(tone `snd_se_Brave_special_N01` = tone 225 = label 0xAA -> 0x76400AA; checked: `special_L01` comes out 0x76400C0, the
id brave.c uses, and Hero's own SpecialN sound scripts play the same ids at the same frames): the hold's charge n01
(0x76400AA) from its frame 2, stopped at the fire / cancel / status end; n04 (0x76400AF) when the charge is full; Frizz
n02 (0x76400AB) at 8, Frizzle n03 (0x76400AD) at 11, Kafrizz n07 (0x76400B3) at 1 (stopping n04) and n05 (0x76400B0)
at 17. Kirby's copy voices (`vc_kirby_copy_brave_01` ...) have no equivalent in his Smash 4 banks: left out.
Sephiroth's copy sounds need `snd_se_Edge.nus3bank` (his tone names): the soundlabeltable only maps labels to tone
indices.

### Crash fix v2 (`kirby_copy_crashfix_v2`): exe_v45c, Kirby's MSC globals

User: exe_v45b (crash fix v1) boots, but loading a match with Kirby (against anyone) fails; the Cemu log has no crash
report (it ends at boot): a hang or a silent exit.
- **The likely cause: Kirby's MSC had more globals than the game keeps.** The MSC script context (allocated at
  `0x0337B230`, 0x43C bytes) holds a file's globals at +4 for 0x80 words (cleared with `li r4, 0x80`, `0x0337B26C` /
  `0x0337B320`); pushVar / setVar index them unchecked (`0x0337BA38`), so global 128 on writes over the context's own
  fields (+0x204 a 7-word sub-object, +0x220 the file's +0x14, +0x224 ...). Kirby had 106 globals in link_samus_v2,
  116 in copy v1; the Hero menu's 37 `khm_*` took v2-v5 to 138-149, and none of them had run in game (v1's exe crashed
  first). Hero / Sephiroth have 135 (their 128-134 land in the 7-word sub-object; no trouble seen).
  Fix: the `khm_*` state lives in Kirby's **New_Var slots** `0x0F00039B`-`0x0F0003BF` (the top of the 64, exe_v40;
  MSC `WorkModule(0x6 / 0x7)` as ints, `WorkModuleF(0)` / `WorkModule(0)` as floats; the table is in kirby.c above
  `khm_bit`): Kirby is at 117 globals. `tools/msc_stack_check.py` now fails on a global index >= 128.
- **exe_v45c:** exe_v45b's panel stub (`kirby_hero_menu_cave.py` kind_stub) kept the kind through r12, the fighter
  object the panel cave reads right after the hook (`lwz r12, 0xC(r12)`): every Hero / Kirby menu check read
  0x04BB000C (5) and gave up (no window or gauge; no crash). It uses r11 now (dead there);
  `kirby_hero_menu_test.py` checks each stub against the registers the cave reads after it (v45b fails, v45c passes).
- Ruled out (unicorn / static): 0x04BAF400-0x04BAFA00 is referenced by no code, data word, relocation or lis pair;
  Kirby's article-file collector (`0x030C37AC`, a 48-entry buffer, no bound) gathers 34 kinds as before (the new
  reserve kinds have no sub-articles); the loader stubs keep the registers the loader uses; the Robin header's
  relocation is moved.
- The package: exe_v45c and v5's kirby.mscsb with the slots.

### v6 (`kirby_hero_sephiroth_copy_v6`): the sword spells, Hero's sword on the stone (exe_v46)

User decision: during a sword spell Hero's sword is shown on the stone (attached at Hero's hand offset), its hitboxes on
it as on Hero. Flame Slash (17), Kacrackle Slash (18), Metal Slash (19) and Hatchet Man (20) are in the menu now, with
Hero's weights (0x12 / 0x12 / 0x7 / 0x12), costs (12 / 11 / 6 / 15 MP) and Hocus Pocus weight (244 each).

**1. Who makes the held model (traced in exe_v45b).** Kirby's copy held model (marthsword, ikesword, ...) is his
**article 26, "simple"** (weapon kind 0x11; its spawner 0x02EFC3D0 is the hat's (article 25, kind 0xC) generic one).
The copy model function `0x02EFE138` (copy_grant calls it at `0x02EFD0A0` with the granted kind; a copy's loss calls
it with -1 from `0x02EF5DE4` / `0x02EF6074`) generates it (ArticleModule generate `0x02C03EA0`, r4 = 0x1A, at
`0x02EFE748`) only for the kinds with a held model, from the compare chain at `0x02EFE664` (1, 0x12, 0x13, 0x17,
0x1D, 0x22, 0x25, 0x27, 0x2B, 0x2E, 0x2F, 0x36, 0x37; Bayonetta 0x38 gets articles 0x20 / 0x21), and removes it
(`0x02C05594`) on a -1. **So the Robin copy (the Hero copy's granted kind 0x2C) never had one**: fixed in the exe (2).
Its model is the copied player's slot resource of **type 0x11**: the copy-resource loader `0x030C4694` runs per match
entry for the types 0xC, 0x11, 0x164, 0x165 (`0x030C4D88` ...: Kirby's article weapon kinds hat, simple,
simple2r / simple2l), the name from the held-item table `0x1041A8A0` (read at `0x030C487C`). The per-frame show / hide
`0x02B02534` is that article's own update (r27 = its owner Kirby's module accessor, r30 = the article's;
`copy_held_cave.py`).

**2. exe_v46** = exe_v45c + `tools/kirby_hero_sword_cave.py` (tested by `tools/kirby_hero_sword_test.py`, unicorn), in
0x04BAF620-0x04BAF6F8 (the end of `kirby_copy_new_cave.py`'s space, whose LIMIT is now 0x04BAF620; the standard
code region, nothing grown, checked):
- the third name swap: `0x030C487C` (`lwzx r7, r24, r21`, r24 = the held-item table: the test decodes it from the
  loader's own `addi`s) -> "bravesword" for a Hero player's slot (kirby_copy_new_cave's res_kind 0x45), every other
  kind the table's own name -> `model/bravesword/cNN` (Kirby's costume);
- the held article for the Hero copy: `0x02EFE664` (`cmplwi r27, 0x22`) -> a stub that, for kind 0x2C granted for a
  Hero (grant_kind 0x45), returns into the generate at `0x02EFE748` (the Robin path's own code follows it), else does
  the compare;
- `copy_held_cave.py --stone`: its hide path goes on to a check: in the stone statuses 0x155 / 0x175 / 0x176 with
  Kirby's int **0x1000008B** == 1 the show path, else the hook's own instruction and back (both through ctr).

**3. The sword model** (`tools/kirby_copy_sword.py`, from Ultimate's brave.zip `model/body/c00`): the mesh
`brave_sword_VIS_O_OBJShape` (material met_brave11_001, single-bound to Sword1, blade along +X) in Kirby's LHaveN
frame as Hero holds it in HaveR (Sword1 -> HaveR from the nusktb: x' = 0.2023 - y, y' = x: the blade along +Y, as
Marth's on Kirby), one bone `HaveN` (unrotated), Hero's size; the template hat (v1's `bravecap/c00`) gives the
material, metal material / texture and the one-bone side files. Texture ids 0x40C5E000 + 0x80 x NN (Hero's block,
below the hats' 0x40C5F000). Every Kirby costume gets Eleven's (c00) sword (the folder is picked by Kirby's costume).

**4. MSC** (`kirby.c` "v6": `khm_sword`, `khm_sw_*`). The cast plays Hero's scripts as MSC calls at their frames:
`khm_sw_game` / `khm_sw_fx` / `khm_sw_end` / `khm_sw_cancel` / `khm_sw_window` are generated by
`tools/kirby_hero_sword_msc.py` from `reference/brave_sword_spells_acmd.txt`:
- timing: Hero's Set_Frame_Duration (FT_MOTION_RATE) applied (Flame / Kacrackle Slash 0.5 on 1-7, 0.8 / 0.7 on 12-40):
  their hitboxes at cast frames 6-8, Metal Slash 11, Hatchet Man 37; the motions' ends (sword shown until) 53 / 50 /
  61 / 107 and cancel frames 39 / 36 / 40 / 88 (Ultimate's motion_list: skill3 61 frames, cancel 47; skill1 61, 40;
  skill2 107, 88);
- hitboxes: AttackModule op 0x272C (Extended_Special_Hitbox's own path) with Hero's values, the capsule's end 0.01
  along Y from the centre (a sphere), IDs + 5 and Part 1 beside the stone's own; Hero's RHaveN (0x19) offsets on
  Kirby's LHaveN (0x18) as above, his RArmJ (0x16) on Kirby's LArmJ (0x10), bone 0 as is; removed by ID;
- effects: EFFECT_FOLLOW -> EffectModule 0x2712 (on the sword: turned 90 about Z), EFFECT / LANDING_EFFECT -> 0x2710,
  Terminate_Graphic_Effect -> 0x2723; sounds: Hero's ids (0x76400C2 ..., v5's bank mapping), the common swings;
- functions: Flame Slash's fire / Kacrackle Slash's freeze are their hitboxes' effects (5 / 4); Metal Slash (a
  hurtbox hit in its hitbox frames, AttackModule 0x2726 kinds 2): the fighter hit turns metal (ITEM 0x0F000278), one
  already metal is KO'd (0x0F00015F), nothing on a shield (as brave_metal_slash); Hatchet Man is always critical, the
  others 1 in 8 (rolled at the cast): the show on the hit (SlowModule(0, 4, 40), ITEM 8 then 9 after 40 frames, Hero's
  se_brave_criticalhit 0x7640112) and for 17-19 the marker's x2 bit 0x10 (hero_buff_cave.py) while cast; Hatchet
  Man's shield damage 10 as Hero's script. Oomph / Psyche Up don't boost (or spend on) a sword spell (Hero's specials
  don't); special can't end the stone before the cancel frame (khm_blocking); the stone ending or the copy lost stops
  the cast (hitboxes, effects, Hatchet Man's charge sound, the sword).

Tests: `kirby_hero_sword_test.py exe_v46 exe_v45c` (the originals at the hooks, the item name for kinds 0-0x50, the
generate stub for every grant / kind pair, the held model's visibility through the whole chain from 0x02B02730 with
stub modules), `kirby_copy_new_test.py` / `kirby_hero_menu_test.py` on exe_v46, `kirby_newcopy_test.py` v6 (each spell ground / air: every
hitbox / effect / sound call at its frame equals the generator's events from the reference; removals; the sword int;
MP; weights; Hocus Pocus; Hatchet Man's show and camera; Metal Slash metal / KO / shield; the crit bit; Oomph; the stone
ending mid-cast), `msc_stack_check.py`, `rolloff_hold_test.py`.

**Approximations / to check in game:** where LHaveN is in the stone pose (the sword sits there; the stone's animation
isn't changed) and its edge's side; whether LHaveN's frame is as Ultimate's HaveL; the effects' 90-degree turn;
Sword_Glow trails left out (the stone doesn't swing it); Metal Slash's Extra hitbox extras (6 frames more hitstun:
no MSC op); LANDING_EFFECT played as a plain EFFECT; the casts' frames counted from the frame after the choice (as
stage 2's spells).

Build:
```
python3 tools/rpx_patch.py EXE_V45C.rpx EXE_V46.rpx $(python3 tools/kirby_hero_sword_cave.py)
python3 tools/kirby_hero_sword_test.py EXE_V46.rpx EXE_V45C.rpx
python3 tools/kirby_copy_sword.py BRAVE_ZIP/brave/model/body V1/fighter/kirby/model/bravecap/c00 OUT/fighter/kirby/model
python3 tools/kirby_hero_sword_msc.py > /tmp/sw.c     # the GENERATED block in kirby.c (paste between its markers)
python3 tools/msclang/msclang.py -x tools/mscinfo.xml fighters/kirby/kirby.c -o kirby.mscsb
python3 tools/msc_stack_check.py kirby.mscsb fighters/kirby/kirby.c; python3 tools/rolloff_hold_test.py kirby.mscsb
python3 tools/kirby_newcopy_test.py kirby.mscsb
```

### Crash fix v3 (`kirby_bisect_v3`): exe_v45d / exe_v46b, the motion-folder hook's relocation

User (bisect v2, Kirby's old MSC from link_samus_v2): exe_v43 + only the copy-resource loader's hooks
(`kirby_copy_new_cave.py`) hangs on loading any Kirby match. The other pieces load fine (reserve entries, Robin copy
list, panel stub, copy_grant).

**Cause:** the motion-folder hook `0x030C470C` (`lwz r7, -0x5930(r8)`) sits on a word that carries an
**`R_PPC_ADDR16_LO` relocation** (`.rela.text`, offset `0x030C470E`, symbol `.data` `0x10000000` + `0x41A6D0`). The
loader applies relocations when the game starts, so it wrote `0xA6D0` into the low half of the `bl` put there:
`0x49AEAE9D` (`bl 0x04BAF5A8`) became `0x49AEA6D0`, i.e. **`b 0x04BAEDDC`**. That is a plain branch with no link,
into zeroed code space. It is reached for the hat entry (type 0xC) of every match entry whose kind is below 0x3A
and not Kirby, so the hang happens in any Kirby match against another fighter. A Kirby ditto never gets there.
It was in every build since exe_v44: v1's exe_v44 became `b 0x04BCEDDC` (also zeros). The registers in v1's crash
log (r8 = 0x10420010, set by the `addis` just before `0x030C470C`; r23-r26 = the loader's tables) put that crash at
this hook too. So crash fix v1's "cave outside the code region" was not what crashed.
- Evidence: across bisect v2's exes, `1_loader_hooks` is the only one with a patched word that a relocation still
  targets. In the whole of v6's exe_v46, `0x030C470E` is the only relocation that disagrees with its word (apart
  from rpx_patch's `reloc:` dummies and three vanilla entry-point words).
- Ruled out for the others: `0x030C46A8` / `0x030C5254` / `0x030C5BD0` replace weapon_expand's own `bl` (no
  relocation). `0x030C4830` is `lwzx` (none). It is also a `beq` target, which is harmless. The stubs touch only
  r12 / cr0 / LR, all dead at those points. Without a Hero or Sephiroth in the match they compute exactly what the
  originals did. The panel stub (which loads fine) stores to and runs from the same page (0x04BAF7xx).

**Fix:** the motion-folder hook moves to the read's use, `0x030C4710` `lbz r10, 0(r7)` (no relocation). The stub
swaps r7 for "brave" / "edge" when res_kind is 0x45 / 0x42, then replays the `lbz`. `0x030C470C` is left as it
was. The hat hook is unchanged, and the code now ends at 0x04BAF610 (kirby_hero_sword_cave.py still starts at
0x04BAF620).
- `tools/rpx_patch.py` now refuses a patch to a word that a relocation (after `reloc:` moves) would rewrite to
  something else (ADDR32 / ADDR16_LO / HI / HA / REL24 / REL14 modelled; any other type, or an import, is refused).
- `tools/kirby_copy_new_test.py`: every relocation whose word the build changed must write what is there; the
  original's `0x030C470C` stays; the body stub is run with r7 already read and checks the replayed r10.
  exe_v45c fails these, and exe_v45d / exe_v46b pass (with kirby_hero_menu_test / kirby_hero_sword_test).
- exe_v45d = exe_v45c with the cave regenerated, the five hooks re-pointed and `0x030C470C` restored. exe_v46b is
  v6's exe_v46 with the same words. The bisect package has exe_v43 + each old hook alone (2 = the relocated one,
  expected to hang), + all five fixed, and the two full exes.

### Crash fix v4 (`kirby_crashfix_v4`): exe_v45e / exe_v46c, copy pools with weapons whose owner is absent

User (bisect v3): exe_v43 + the hat hook (test 3), and exe_v43 + all five fixed loader hooks (test 6), load but
crash when Kirby gains a copy (Kirby vs Mario). Test 6's Cemu log: PPC IP `0x04BB3350` `lwz r11, 0x160(r8)`,
r8 = 0, r12 = FighterParamManager. Stack: copy_grant `0x02EFCEB0` -> the copy's pool builder `0x02EFDB88`
(`0x02EFDCA4`) -> weapon create `0x02BF42E8` -> ... -> the module set-up's +0x18 param getter call (`0x02BCB9F4`).

**Cause (not the loader hooks):** `0x04BB3340` is weapon_expand.py's copy of the Kamehameha's (weapon 0x18B) param
getter. It reads Supamario's vl slot `[mgr + 0x26B4]` (0x25B0 + 4 x 0x41), which is set only while Supamario is in
the match. The manager's constructor loops clear the relocated arrays for the whole capacity, so the empty slot is
deterministic. Mario's copy list (fix 90) has the Kamehameha with max 1, so the pool builder makes an instance, and
Kirby vs Mario crashes as soon as Kirby gains Mario's copy. exe_v43 should do the same (the package's check 1). The
same goes for the Robin copy list (Hero's 0x190 / 0x193-0x197 and Sephiroth's 0x18C): copying Robin, Hero without a
Sephiroth, or Sephiroth without a Hero. A vanilla copy pool only holds the copied fighter's own weapons, and that
fighter is always in the match. Bisect v3's test 1 reportedly gained a copy without crashing: not explained by the
code (the hat stub without hook 1 just replays the `lwzx`), so the copy gained there was probably not Mario's.

**Fix** (`tools/kirby_copy_pool_cave.py`, tested by `tools/kirby_copy_pool_test.py`, 0x04BAFA00-0x04BAFA78):
- The pool builder reads a record's instance count at `0x02EFDC74` (`lwz r19, 4(r11)`, no relocation). That read
  now goes through a stub. For a new weapon kind (0x185 on) whose owner fighter's vl slot is empty (the slot its
  getter reads; owners from extra_kinds.json), the count becomes 0. That is the path a vanilla max-0 record takes:
  no instances and not registered.
- Such a weapon is never generated, because its copy path needs the owner in the match.
- The stub uses r11 / r12 (dead there) and cr7, and keeps cr0 (the `rlwinm.` before the hook is tested after it).
- `tools/ppcasm.py`: `bltlr cr7` (a conditional blr with only a cr field) silently used cr0. It now takes the
  field. No other tool used that form.

exe_v45e = exe_v45d + this cave, and exe_v46c = exe_v46b + this cave. The package also has exe_v43 + only this
cave, to confirm the cause.
Tests: kirby_copy_pool_test (v45e, v46c, v43 + cave), kirby_copy_new_test, kirby_hero_menu_test,
kirby_hero_sword_test.
```
python3 tools/rpx_patch.py EXE_V45D.rpx EXE_V45E.rpx $(python3 tools/kirby_copy_pool_cave.py)
python3 tools/kirby_copy_pool_test.py EXE_V45E.rpx EXE_V45D.rpx
```

### Crash fix v5 (`kirby_crashfix_v5`): exe_v45f / exe_v46d, the granted kind's params

User (exe_v45e): copying Sephiroth crashes (Kirby vs Sephiroth). Cemu: PPC IP `0x031DD364` `lwz r7, 0x1B0(r8)`,
r8 = 0x9F16CDAC, r17 = 0xB6, the same stack as v4 (copy_grant -> pool builder -> weapon create -> +0x18 getter).

**Cause.** Robin's own thunder (0xB6, vanilla, max 5) is in the Robin copy's pool. Its getter `0x031DD350` reads
Robin's `[mgr + 0x11CC]` (0x111C + 4 × 0x2C), and no Robin is in the match.
- The vl pointers are never cleared. The manager's constructor clears the reference counts (mgr + 0x2730 + 4k, all
  0x60 kinds, kind_expand.py's array), not the vl arrays, so an unloaded fighter's slot holds heap garbage. v4
  looked at the slot and didn't cover vanilla kinds.
- Why only Sephiroth: a new kind's vl load case loads its base's vl first (kind_expand.py `copy_load_case`).
  Hero's base is Robin, so Robin's params are always there with Hero. Sephiroth's base is Zelda, so they aren't.
- Pooling is not the only thing that needs them. Copy kind 0x2C runs the Robin copy's native code, including the
  special-param loader `0x02F1B8B0` (reads `[mgr + 0x111C + 4 × copy]`).

**Fix** (`tools/kirby_copy_pool_cave.py BASE.rpx`, now reading the base executable; 0x04BAFA00-0x04BAFC2C,
139 words):
1. **Sephiroth's vl load also loads Robin's.** The rule covers any kind in kirby_copy_new_cave.py MAP whose base
   isn't its granted kind; today that is only 0x42.
   - Its load case's first word (`0x04BA875C` `mr r3, r29`) becomes a `bl` to a stub. The stub saves LR and calls
     `0x02EA6BC4(mgr, 0x2C)`, then replays the `mr`.
   - Its unload case's final `b 0x02EA6AF4` (`0x04BA881C`) becomes a branch to a stub that releases 0x2C after
     Zelda.
   - Both are refcounted like the base load.
2. **The pool stub now covers every weapon kind.** If the weapon's owner has vl reference count 0, it gets 0
   instances. Owners come from:
   - the fighter slot the weapon's +0x18 / +0x24 getters read (208 vanilla kinds; e.g. 0x13, owned by "kirby",
     reads Rosalina's);
   - else the owner name (0x10418FF0) as a fighter name;
   - else the new kinds from extra_kinds.json (360 owners in all).

`tools/kirby_copy_pool_test.py` runs the patched executable's own code in unicorn, all sections mapped:
- the pool stub for every kind;
- Sephiroth's load / unload chain (with VL_LOAD / VL_UNLOAD recorded): 0x2C then 0x10, and 0x10 then 0x2C;
- Kirby vs Mario / Supamario / Robin / Hero / Sephiroth, with the loaded sets from those chains and Mario's /
  Robin's copy lists. Every pooled record's real getters run (found with the real descriptor getter 0x0320D934),
  with the unloaded fighters' slots set to 0x9F16CDAC, and none faults.
- Pooled records per match:

  | Match | Pooled records |
  |---|---|
  | Kirby vs Mario | 0 |
  | Kirby vs Supamario | 0, 5 |
  | Kirby vs Robin | 0, 2 |
  | Kirby vs Hero | 0, 2, 6, 8-12 |
  | Kirby vs Sephiroth | 0, 2, 7 |

- Negative control on exe_v45e (v4's stub, Sephiroth only): 0xB6 is pooled, and its getter faults at 0x031DD364
  with r8 = 0x9F16CDAC, as in the user's log.

exe_v45f = exe_v45d + this cave, and exe_v46d = exe_v46b + this cave. It replaces v4's cave, whose words it rewrites.
```
python3 tools/rpx_patch.py EXE_V45D.rpx EXE_V45F.rpx $(python3 tools/kirby_copy_pool_cave.py EXE_V45D.rpx)
python3 tools/kirby_copy_pool_test.py EXE_V45F.rpx EXE_V45D.rpx
```

### Visual fix v1 (`kirby_copy_visuals_v1`): hat placement, the copy motions' legs and body

User (with crash fix v5, Kirby copying Sephiroth in game; clip 2026-11-13): "Sephiroth's hair/hat seem positioned
slightly wrong and the animations stretch Kirby oddly." Only Kirby's copy hats and copy motions change; no exe or MSC
change.

**Inputs.** Ultimate: the user's `kirby-ssbu-partial.zip`. Smash 4: `kirby - Copy.zip` (Drive), plus the user's
`kirby_smash4_model.zip` / `kirby_smash4_motion.zip`, which are the same vanilla files plus the installed copies.
Kirby's vl: `param-smash4-vanilla.zip`. Clip frames: ffmpeg. Checks: forward kinematics of both skeletons, and
renders of Kirby's Smash 4 meshes posed by each pack (a numpy rasterizer, not in the repo).

**Scale (the user's hint): no difference.** Both Kirby skeletons have the same bind pose, world position and turn,
to 0.0000 on all 42 shared bones. The body meshes' vertex boxes are equal to 0.01. Ultimate's copy tracks carry no
compensate-scale flag, so children inherit scale as in Smash 4. Vanilla motions both games share (A01Turn,
A01WalkFast) have the same scale values bone for bone (e.g. Waist 0.78-1.08). So translations need no ratio, and
Ultimate's own squash (Bust 0.73 in Gigaflare's charge, Body 0.83-1.19 in Hero's moves) is kept as it is.

**Motions: what stretched Kirby.** `tools/kirby_copy_motions.py --check` now runs every frame of the built packs
against Ultimate's FK. Stage 1 was 2.39 off on every frame; now the largest error is 0.04, from 16-bit rounding at
the toes.
- **Different parents.** Ultimate hangs both legs on LegC (Hip + 2.392 along Hip's X, i.e. up) and both clavicles on
  ClavicleC (Bust + 0.05). Smash 4 has LLegJ / RLegJ straight on HipN and L/RShoulderN on BustN. Stage 1 copied the
  local tracks as they were, so the legs, knees, feet and toes were 2.392 too low on every frame. The feet were in
  the floor, which is why they don't show in the clip's Flare / Megaflare frames.
  - The new converter gives each Smash 4 bone the transform from its Smash 4 parent's counterpart to its own
    counterpart in Ultimate's posed skeleton (`s4_locals`). LegC / ClavicleC never scale, so the decomposition is
    exact (shear asserted < 1e-3).
- **Body and mouth from the wrong pack.** In Smash 4 the whole body mesh, the eyes and the face meshes are bound to
  BodyBN. Vanilla main.pac motions never animate BodyBN or the mouth bones: kirbypt1 plays BodyBN, and kirbypt2 plays
  MouthN, the lips, MouthShitaN/Nb, CheekN and HukumiN. Every vanilla part entry has its main motion's frame count.
  - Stage 1 shipped the Robin copy's part packs. That put Robin's body lean on BodyBN (up to ~37 degrees, timed for
    Robin's 8-76 frame motions) under Ultimate's motions, and Body / Mouth1 / Cheek / Puff in main.pac too.
  - Now Ultimate's Body goes to kirbypt1, and Mouth1, MouthLa1-Le / Ra1-Re, MouthD1/D2, Cheek and Puff go to kirbypt2
    (`FACE_BONES`, mapped by name and bind: identical). Both have the main motion's frame count. main.pac has the
    other 26 bones, as vanilla.
  - The Robin part entries for slots a copy doesn't play (Sephiroth's two holds) stay, so the part packs keep stage
    1's entry set.
- HeadN keeps Ultimate's Head track. Ultimate's Head yaws freely (up to 179 degrees in Gigaflare's charge, 153 in
  its run), but nothing is skinned to it on Kirby and the hats aren't on it (below).

**Hats: the anchor.** Smash 4's copy hats sit on **BodyBN** (y 5.17 in the bind pose; NeckN is at the same place),
not on HeadN (6.37) as stage 1 assumed. A hat's one bone (TopN) has the head-frame turn as its bind, so its vertices
are Y-up offsets from the anchor. The evidence:
- Kirby's joint table 1 starts with BodyBN (joint ID 1000). His vl group 9 attach points are four on ID 1000 and two
  on HipN, where Marth's are BustN, HeadN x3 and HipN x2.
- Vanilla hats sit on the head only from 5.17. Peach's crown has its nearest vertex 0.10 inside the body sphere at
  5.17 and 0.92 above it at 6.37. Koopa's cap and Fox's ears behave the same way. Mario's and Luigi's caps, which
  just touch at 6.37, sink 0.2-0.6 at 5.17, as a cap does. `kirby_copy_hats.py --check` prints the table.
- The clip: the hair sat 1.2 low (bare pink head top behind the fringe, side locks down to the floor). It also kept
  to the body and face while the installed motions yawed HeadN by ~100 degrees.

So:
- **edgecap:** Ultimate's model-space vertices (skinned to Body at 5.17) minus (0, 5.17, 0). That is 1.2 higher
  than stage 1.
- **bravecap:** Ultimate's vertices as they are (offset 0). copy_brave_cap has no skeleton, and its coordinates are
  already offsets from that point: its circlet hugs the body sphere at 5.17 (nearest +0.05, median +0.23, none
  inside; the best fit scanning heights is 5.1-5.2), with the gem in front and the sword and shield on the back.
  Stage 1 put it on Headdress (9.752, + 3.382), which in game left the circlet ~1.5-2.9 above the head and the sword
  and shield 3.4 high: now 3.382 lower.

Renders of Ultimate's pose against both builds: the package's `preview/compare.png`. The new build matches
Ultimate's; stage 1 shows the sunk feet, the leaning body and the low hair the clip shows.

Still approximated: the hats are rigid (copy_edge_cap's S_HairB1 swing and its Puff weights; Ultimate's
`kirby/motion/copy_edge_cap` hair motions unused).

```
python3 tools/kirby_copy_hats.py ULT/kirby/model S4/fighter/kirby/model OUT/fighter/kirby/model --check
python3 tools/kirby_copy_motions.py ULT/kirby S4/fighter/kirby OUT/fighter/kirby/motion --check
```

### Visual fix v2 (`kirby_copy_visuals_v2`): Sephiroth's hair swings

User: "make Sephiroth's hair swing like in Ultimate." Only `model/edgecap/c00-c07` changes. No exe or MSC change.

**What Smash 4 supports.**
- **Swing bones on hats: yes, with no code.** 22 of Kirby's vanilla copy models have them. Examples: `marthcap`
  (3 hair bones), `linkcap` (the cap's tail, a chain of 3), `ikecap` (the bandana, 2 x 3), `szerosuithair` (the
  ponytail, 5); also `palutenacap`, `zeldacap`, `pikachucap`, `soniccap` and others. How they are built:
  - A swing bone is a `model.vbn` bone of type 3, named `SWG_<name>__swing` and parented on the root.
  - The hat's vertices are skinned to it.
  - The hat's `model.sb` (` BWS` 5.1, little-endian, a u32 count, 140-byte entries as Smash Forge's `SB.SBEntry`)
    gives each swing bone, by hash:
    - physics words (800, 5, 3, 100, 0, 1 for Marth's / Zero Suit Samus's hair);
    - rx / ry / rz limits in degrees (rz is the swing about the bone's Z, + away from the head on these hair bones);
    - 8 collision bone hashes (0xCD94A505 = none);
    - the bone's length at word 30 (Ike's 1.515 / 2.157 are his chain's bone-to-bone distances).
  - The swing bones' axes are Ultimate's convention: X along the strand, Z across.
- **Hat animations: not for this copy.** Kirby's copy resource tables are the body motions `0x1041A6D0`, the hats
  `0x1041A7B8` and three held-item tables (`0x1041A8A0` and two more with only Bayonetta's guns). None of them is a
  hat-motion table.
  - `motion/yoshicap` (the Yoshi copy's N1 / N2) and `motion/ultraswordhat` (the Final Smash) exist, but are
    presumably loaded and played by their own code; not traced.
  - So keyframed hair for the Robin-slot copies would need an exe stage: load `motion/edgecap` and play its entry for
    Kirby's motion on the hat.

**Ultimate's hair.** `copy_edge_cap` swings one bone, `S_HairB1`:
- It sits at Body + (2.1, -4.2, 0) local, i.e. the back of the head, pointing down to `S_HairB2_null` 5 below.
- It moves 1343 back-hair vertices, the strand below y ~6.9, blended into Body.
- `swing.prc` `hairb`: z -20..50, y -20..20, gravity 1, inertial mass 5, goal strength 10, air resistance 100,
  friction 0.5, no collision.
- `swingblend.prc` swing is on (blend 1) by default and off (0) in the 8 neutral-special motions. There,
  `motion/copy_edge_cap/d00special*.nuanmb` key `S_HairB1` up to ~83 degrees off its bind (hair flips).
- The front locks, the arcs and the Puff weights don't swing.

**Done** (`tools/kirby_copy_hats.py`, edgecap only):
- **Skeleton:** `model.vbn` = refletcap's `TopN` + `SWG_HairB1N__swing`.
  - Type 3, parent `TopN`, at `S_HairB1`'s bind in the hat frame (local (2.1, -4.2, 0), axes kept), hash
    crc32(name).
  - The header counts types (1, 0, 0, 1).
- **Skinning:** each vertex's `S_HairB1` weight goes to bone 1 and the rest to `TopN`, in `model.nud` and
  `metal.nud`. Positions are v1's exactly. The nud bone range is 0-1.
- **Physics:** `model.sb` takes one entry from Zero Suit Samus's `SWG_Pony01N__swing` (read from
  `szerosuithair/c00` at build time).
  - It is a strand hanging from the back of the head, with the same bone axes; its physics words are Marth's hair's.
  - With Ultimate's limits: ry (-20, 20), rz (-20, 50).
  - Length 5.0 (`SWING`).
- `--check` (with OUT) asserts the c00-c07 layout as the vanilla swing hats': the types, the parent, the sb hash and
  header, the nud bone range.

**Offline test.** In the package's `preview/`:
- **Skinning:** `swing_range.png` renders the bone at each limit; the strand bends smoothly with no tearing.
- **Motion:** `sim_dash.png` / `.gif` (a dash and stop) and `sim_charge.png` (Gigaflare's charge). They are a damped
  pendulum within the sb limits, an illustration only. The game's swing solver couldn't be run offline, so how much
  it swings is checked in game.

**Approximated / not done:**
- The physics words are Zero Suit Samus's, not a conversion of Ultimate's swing params (whose units don't map).
- Ultimate's keyframed hair in the neutral special: physics runs there instead.
- No collision with the body; the limits keep the hair off it, as in Ultimate.

### Hero copy fix v1 (`kirby_hero_copy_fix_v1`): exe_v45g / exe_v46e, the copy slots' scripts, copy voices / sounds

User (crash fix v5 A: exe_v45f + crash fix v2's MSC), Kirby's Hero copy: (1) most of Robin's sounds and effects play,
and Robin's neutral-special expression script too; (2) only Frizz comes out, the other charge levels lock Kirby out
of the move; (3) no MP gauge; (4) the Stone doesn't open Command Selection. Sephiroth's copy: no Kirby voice, no
Sephiroth sounds (none were played: not converted yet).

**Not the cause: New_Var slots without a declaration.** The hypothesis was that the cave keeps values only for slots a
New_Var declared, so the `khm_*` state (crash fix v2) was lost. `nv_code`'s `ue_nv` (every slot read / write, also
through the WorkModule int ops `nvi_*`) never tests the declared mask; only `h_newvar` uses it (to set Initial once).
Run with the game's own code (`tools/kirby_hero_copy_fix_test.py`, exe_v45f too): the MSC WorkModule handler
`0x0200E898` ops 7 / 6 / 0 and get_float on all 37 slots `0x0F00039B`-`0x0F0003BF`, no New_Var: unset slots read 0,
every write reads back, ints and floats, another object's slots apart (`new_var_test.py` passes on exe_v45f / v45g
too). The interpreter test's stub was not the real model though (ints and floats in two maps): it now mirrors the
cave (one float per category-F id 0x300-0x3BF, int ops cut toward 0, 0x3C0+ read 0 and drop writes).

**Cause found: the copy slots' scripts were only half silenced.** Kirby's scripts for the Robin copy slots (his
vanilla files, the Drive's `fighter-modded-scripts-only.zip`, hashes from `motion.mtable` = crc32 of
`refletspecialn*`): no game scripts; expression: 0x447 (Hold) `Rumble_Loop(0x22)`, 0x448 (Shoot) / 0x44C (TronEnd)
`Rumble(0xD)`, 0x44B (TronHold, the Hero copy's hold) `QUAKE(5)` (a screen shake) + `Rumble_Loop(2)`; sound: 0x447
`0x7640028` at 1 (Robin's bank id 2051, Hero's bank in Kirby vs Hero), 0x44A (TronStart, Frizzle / Megaflare)
`0x8B50003` at 15; effect: 0x447 an endless `0x1000019` spark loop. `ncp_silence` (set 0x10) rebound only the sound /
effect sets, to slot 0x446's (none), on motion changes; a motion change binds the game / expression sets itself, so
the expression scripts always ran. Fix: `copy_fx_cave.py` set **0x11 SILENCE** clears all four agents (game,
expression, sound, effect) with the game's clear `0x02BEE9B8` and cancels the late bind (`+0x1C` = -2); the copies'
MSC calls it after every motion change and every frame of the status (`MotionAnimcmdModule(0, 0x11, 0, 8)`).

**Symptoms 2-4 and Robin's sounds: the MSC taking the Robin copy's path.** All four match `newcopy_marker()` = 0 for the
Hero copy (the copy kind 0x2C without marker 2 in int `0x100000A0`): Robin's own neutral special runs (Thunder /
Elthunder / Arcthunder with the tome, which runs out: "locks Kirby out"; Robin's sounds and effects), `khm_panel`
writes no gauge, `khm_update` opens no menu. The Hero copy's own path does all four right in the interpreter, and the
Sephiroth copy's path ran in game (the visual fix clip shows its MSC-played charge effects), so the marker worked for
Sephiroth. Statically copy_grant's map / marker for 0x45 is right (kirby_copy_new_test runs the stubs; the swallow
path `0x02796680` passes the swallowed fighter's kind `0x02BEF604`; the star copy passes kind + 1 - 1; nothing else
writes int 0xA0: scanned). Not found why Hero's marker would be lost; one known way: a Kirby who has the Hero copy
swallowed by another Kirby passes only the Robin copy (stage 1 limitation). **Guard:** a Robin copy with no marker in
a match with no Robin is the Hero copy when a Hero is in the match and no Sephiroth, Sephiroth's when he is and no
Hero (`newcopy_guess`, the position variables' slot kinds `0x0F0000BD + 8 s`, once a frame into `ncp_guess`; also
`newcopy_real_kind` for the trait). The README's check 2b (a Robin in the match turns the guard off) tells whether
the marker itself arrives.

**Voices and Sephiroth's sounds** (`tools/kirby_copy_sound.py`, new): into **Kirby's own banks** (a sound id is matched
against the playing fighter's banks; Sephiroth's id 2018 needn't be among Kirby's while he has the Robin copy):
- `snd_vc_Kirby` (id 6006, row 63, 47 -> 55 labels): Ultimate's `vc_kirby_copy_brave_01-04` / `vc_kirby_copy_edge_01-04`
  (the user's `kirby_fighter_voice_ssbu`, IDSP and TONE volumes as they are) = `0x3F002F`-`0x3F0032` / `0x3F0033`-
  `0x3F0036`. The recomp dump's unnamed hashes in Kirby's copy sound scripts are these names (hash40: length + crc32):
  Hero hold _01 at 2 (PLAY_STATUS: stopped at the fire / cancel / end), Frizz _02 at 8, Frizzle _03 at 11, Kafrizz
  _04 at 17 (the non-Japanese side of an is_flag pick: the other is `vc_kirby_copy_brave_rnd_special_n0x_jp`);
  Sephiroth charge _01 at 2, Gigaflare _04 at 119, Flare _02 at 12, Megaflare _03 at 12.
- `snd_se_Kirby` (id 2009, row 10, 213 -> 217 labels): Sephiroth's `se_edge_special_n01` (charge, at 1, stopped at the
  fire / cancel / end), `n02_01` (Flare, 2), `n03_01` (Megaflare, 2), `n04_01` (Gigaflare, 119), from his Smash 4 bank
  (the user's `snd_se_Edge`) = `0xA00D5`-`0xA00D8`. Unresolved in the dump: `0xd6a6d0d29` (13 characters, played at
  the Hero fires' 10-17): left out.
- Base banks: the user's `kirby_smash4_sound` (= the vanilla ones in `fighter-smash4-vanilla.zip`, same sha1); the
  soundlabeltable: the user's upload (rows 10 and 63 changed only, `--check`). `voiceanim_Kirby.vat` (46 labels)
  isn't grown: Kirby's own label 46 is already past it (no mouth animation for those).

**A / B builds:** `tools/kirby_hero_copy_build.sh OUT`: B = kirby.c as it is (exe_v46e + v6's sword models); A = the
same with `khm_sword_on()` 0 (exe_v45g has no held sword: the four sword spells are never drawn, as before v6).
Globals 118 of 128.

Tests: `kirby_hero_copy_fix_test.py exe_v45g exe_v45f` / `exe_v46e exe_v46d` (the cave alone differs; SILENCE through
the real chain; the slots from MSC; exe_v45f fails the SILENCE checks), `copy_fx_test.py` (SILENCE with stubs),
`kirby_newcopy_test.py` A and B (the cave's WorkModule model; silence every frame and after every change; voices
and Sephiroth's sounds at their frames; the guess; the A build's sword spells; v1-v6's checks; the old B MSC fails
9), `msc_stack_check.py`, `rolloff_hold_test.py`, `new_var_test.py`, `kirby_copy_new_test.py`, `kirby_hero_menu_test.py`
(its base must be exe_v44: with exe_v43 the "original Robin list" check fails for exe_v45f as for v45g),
`kirby_hero_sword_test.py` (v46e), `kirby_copy_pool_test.py` (v45g / v46e).
```
python3 tools/rpx_patch.py EXE_V45F.rpx EXE_V45G.rpx $(python3 tools/copy_fx_cave.py)
python3 tools/rpx_patch.py EXE_V46D.rpx EXE_V46E.rpx $(python3 tools/copy_fx_cave.py)
python3 tools/kirby_copy_sound.py ULT_VOICE KIRBY_SOUND SND_SE_EDGE SOUNDLABELTABLE OUT [--check]
sh tools/kirby_hero_copy_build.sh OUT
```

### Hero copy fix v2 (`kirby_hero_copy_fix_v2`): exe_v45h / exe_v46f, the spell's level and the marker

User (fix v1 A / B), Kirby's Hero copy: (1) the charge holds (the hold pose, shield-store works) but the projectile is
always Frizz; (2) Thwack spawns Whack; (3) the Stone's Whack can't hit an enemy Hero, and Sizz / Bang don't hit
enemies either (Frizz does); (4) the buff spells don't work; (5) the B build's sword isn't shown in the sword spells
(with v6's `bravesword` folders installed); Sephiroth's copy doesn't store a Flare charge (correct: Sephiroth doesn't).

**Cause of (1) / (2), found: Robin's native "hold this tome" code zeroes Kirby's ints.** Every Hero-copy projectile
(the fireball, article 6, and the Stone's spells, articles 8-12) is made by Robin's thunder spawner `0x02F643A4` (the
records' spawner). The spawner first calls `0x02F613B8(owner, 0)` (at `0x02F645BC`: Robin takes the Thunder tome:
VisibilityModule group 1, the module at `F+0x727C` op 7, ints `0x9F` / `0xA0` / `0xA1` / `0x90` = the book, a flag
cleared: `stw r29, 0x27C / 0x280 / 0x284` at `0x02F61458`-`0x02F61460`), and only then reads the custom number at
`0x02F64650`, where copy_custom_cave.py's hook gives Kirby with a copy his `0x1000009F`. On Kirby those offsets are
this mod's copy custom slot (`0x9F`) and the Hero / Sephiroth marker (`0xA0`): the level the MSC had just written was
zeroed before it was read (always level 0), and the marker was lost at the first Frizz. That is also crash fix v5's
"only Frizz, the other levels lock Kirby out" (the Robin copy's path from the second cast on) and fix v1's "why would
Hero's marker be lost" (Sephiroth's fire uses Din's Fire's spawner: no tome call, his marker and levels survived);
fix v1's guess only papered over it in a match without a Robin. The interpreter tests never saw it: their ArticleModule
stub read the slots as the MSC left them.

**Fix:** `tools/kirby_robin_book_cave.py` (exe_v45h = exe_v45g + it, exe_v46f = exe_v46e + it): `0x02F613B8`'s first
word (`mflr r0`, no relocation) -> a stub that returns at once for a Kirby (fighter kind at `[[F+0x726C]+0x18]` = 8)
whose marker `0x100000A0` is 2 or 3 (no tome on those copies); anything else (Robin, Hero himself, Sephiroth, Kirby's
real Robin copy, Supamario's marker 1) replays `mflr r0` and runs the game's code. 15 words at `0x04BAF100`-`0x04BAF13C`
(free code in kind_expand.py's region, before kirby_copy_new_cave.py's `0x04BAF400`: the standard code region).
`tools/kirby_robin_book_test.py` (unicorn): the spawner's order and the stores (the evidence), the base's
`0x02F613B8` on a Kirby with the Hero copy zeroes `0x9F` / `0xA0` / `0xA1` / `0x90` (the bug), the patched one leaves a
Hero / Sephiroth copy's ints alone and still runs the game's code (both module calls, the stores) for everyone else;
only the cave and the hook differ from the base.

**(3) Whack's caster:** shot.c found the caster as "the Hero or Kirby nearest to the article", so a Kirby-cast Whack
with an enemy Hero nearer to it took that Hero as the caster (left out of its targets and rolls, his damage in the KO
chance). Now the custom number carries it (it reaches the article with the fix above): `khm_generate` passes level
+ 4 x (Kirby's player slot + 1) for articles 8-11 (flash / explosion / deathball / sleep), shot.c reads the caster from
it (a number below 4, Hero's own `brave_generate`, still searches). The native param getters keep the custom within
their 4 entries (`custom & 3` = the level: weapon_expand.py `CUSTOM_CLAMP`, checked in exe_v45h's getters for
0x190 / 0x193-0x197). Hero files rebuilt: `fighter/brave/script/msc/{flash,explosion,deathball,sleep}`
(`tools/brave_shot_owner_test.py`: Kirby's coding in any slot, Hero's own search unchanged, Whack's first target the
opponent; the old coding with the opponent Hero nearer picked him as the caster).

**Not found (statically) / open:** Sizz / Bang not hitting from the Stone while Frizz hits: the records 8-12 are the
same as 6 (spawner, pool counts, Kirby's reserve entries name them), the articles' MSC has no owner logic besides
Whack's, and nothing in the spawner depends on the cast's status; the casts happen from the stone status (Frizz from
the neutral special). The buffs: the MSC sets the marker bits / profile 3 (interpreter: Acceleratle 0x4B490303, Oomph
0x...A0, Psyche Up 0x...40, Acceleration 0x...1300, their glows played) and exe_v45h runs the stat cave's profile 3 /
Acceleration words (checked against `kirby_stat_cave.py --table --accel`) and the buff caves for any fighter's marker;
not reproduced. The sword (B): the name stub (`0x030C487C`), the held-article generate (`0x02EFE664` -> `0x02EFE748`,
article 0x1A for grant kind 0x45), the stone show path (int `0x1000008B`, statuses 0x155 / 0x175 / 0x176) and the
`bravesword/c0N` folders (path `fighter/kirby/model/` + name + `/c0` + costume) check out statically; the old
executable's tome call also hid Kirby's VisibilityModule group 1 and cleared int `0xA1` (the stone's own start-motion
int) at every spell, which exe_v45h / v46f no longer do on the Hero copy: re-test all three with fix v2 before going
further (the user's observations then decide: e.g. whether the spells appear at all, whether they pass through the
enemy).

Build:
```
python3 tools/rpx_patch.py EXE_V45G.rpx EXE_V45H.rpx $(python3 tools/kirby_robin_book_cave.py)
python3 tools/rpx_patch.py EXE_V46E.rpx EXE_V46F.rpx $(python3 tools/kirby_robin_book_cave.py)
python3 tools/kirby_robin_book_test.py EXE_V45H.rpx EXE_V45G.rpx; python3 tools/kirby_robin_book_test.py EXE_V46F.rpx EXE_V46E.rpx
sh tools/kirby_hero_copy_build.sh OUT        # kirby_A / kirby_B.mscsb (globals 118 of 128)
python3 tools/kirby_newcopy_test.py OUT/kirby_B.mscsb; python3 tools/kirby_newcopy_test.py OUT/kirby_A.mscsb OUT/kirby_A.c
python3 tools/brave_shot_owner_test.py OUT/shot   # + flash / explosion / deathball / sleep.mscsb (brave_build.compile_msc)
```
`kirby_newcopy_test.py` models the spawner now (`Game.spawn`: records 2 / 6 / 8-12 run the tome code before the
read unless `book_fix` and the marker is 2 / 3; record 7 reads 0x49): with the old executable modelled, Frizzle's
fireball gets custom 0 and the marker is lost (the in-game report); with fix v2, Frizz / Frizzle / the stored Kafrizz
0 / 1 / 2, the marker kept, the Stone's projectiles level + 4 x (slot + 1) (fix v1's MSC fails those).

### Hero copy fix v3 (`kirby_hero_copy_fix_v3`): visible spells, Acceleration, the sword, the Stone's menu and drop

User (fix v2): Frizzle / Kafrizz work. Every Command Selection projectile (Sizz, Bang, Whack, Snooze, Magic Burst ...)
is invisible except its burst; Acceleration does nothing and shows no glow; the B build's sword still isn't shown
(the `bravesword` folders installed). New: in the air, with the menu shut, down special drops him as a normal Stone;
a cancelled menu opens again at once.

**Invisible projectiles: fix v2's custom numbers past 3.** Between fix v1 (projectiles drawn: the user saw Whack for
Thwack) and fix v2 only the custom number changed for them (fix v2's exe change ran for Frizz too, which draws): fix v2
sent level + 4 x (slot + 1) (4-13) to articles 8-11 and Magic Burst's level + 8 x slot reached the crash. That is
port_check W10 ("past 3 it reads the base weapon's per-custom data past its 4 entries"), the bug catalogue's P2
Whack / Thwack that never appeared: the getter clamp (checked in exe_v45h) is not the only per-custom read (the other
one not found). Fix: `khm_generate` sends the level alone again (0 / 1) and Magic Burst 0 (61-100 MP spent: full) or
3 (1-60 MP: the x0.2 tier; 40 / 60 / 80 aren't below 4), Kamikazee 1. The caster is found in the article:
`shot.c` `sh_stone_kirby` / `placed.c` `pl_stone_kirby` (crash only): a Kirby (kind 8) in his stone (statuses
0x155 / 0x175 / 0x176, position variables) within 30 of the article, nearest first, before Hero's search (the nearest
Hero or Kirby, which took an opponent Hero nearer to the article). Hero's own casts are unchanged (no stone Kirby near
his hand; his crash keeps its slot in the number). Rebuilt Hero files: flash, explosion, deathball, sleep (shot.c),
crash, spark, tornado (placed.c).

**Acceleration: Hero's is Kirby's Overdrive.** brave.c's `brave_accel_on` (fix 79) sets the animation rate 1.2
(`0x0F000098`) and the common blue glow `0x10000C7` on four joints, made again every frame, besides the marker bit
0x1000; Kirby's v2 port set only the bit. `khm_accel` now does both for its 600 frames (Kirby's Overdrive joints
HeadN / LArmJ / RArmJ / LLegJ, `overdrive_gfx_on`), and puts the rate back at its end, a KO or the copy's loss.
Acceleratle / Oomph / Psyche Up already had their glows and bits (interpreter: the marker 0x...303 / 0xA0 / 0x40).

**The sword: a wrong bone hash in the converted model.** A model.vbn bone's third word is the game's hash of its name,
not crc32: Smash 4's held swords' root `HaveN` is 0x2D6C2084 and `SwordN` 0x7B4475A3 (marthsword, ikesword); Kirby's
body `RHaveN` 0x47F11BB8 is ikesword's root's; the copy hats kept their template's `TopN` 0x4A2AE7BC and show.
`tools/kirby_copy_sword.py` (v6) wrote crc32("HaveN") = 0xF4A99364 and one bone. The engine finds joints by name (an
item's `HaveN`: `0x0302C320` -> `0x030832C8`, ModelModule vt `+0x1CC` with the string), which no bone of ours
matched. Now the vanilla held swords' layout: HaveN (0x2D6C2084, the root, unrotated: the vertices are already in
LHaveN's frame) and its child SwordN (0x7B4475A3), model.jtb `00 02 00 00 00 01`; `--fix-skeletons MODEL_DIR` rewrites
an existing `bravesword` tree (fix v3's B package: the 8 folders' model.vbn / model.jtb). Not checked in game before
this package (no emulator here).

**The Stone (user):**
- The menu cancelled (shield / jump) opens again at once with the same four spells (`khm_reopen`: the window from
  its start, the opening sound, the 8 seconds from 0, the cursor on the first row). The 8 seconds running out still
  shuts it (Hero's limit), as before.
- Down special (B + down: command bit 0x8000) in the AIR with the menu shut (no menu open, no spell being cast,
  `khm_sub` idle: after a spell or the 8 seconds) drops him as a normal Stone: the stone article removed and the down
  special started over (status 0x155: Kirby's own transformation, its fast fall and the falling hitbox, then the
  stone's hold), with no menu for the rest of that stone (`khm_plain`, New_Var slot `0x0F00039A`, cleared when he
  leaves the stone statuses). `khm_stone_drop`, called first in the stone's hold loop `func_2323`. On the ground, or
  with the menu open (special casts there; a held-down special in the menu casts too) or during a cast, nothing new.

Tests: `kirby_newcopy_test.py` (fix v3: the spells' custom = the level, Magic Burst 0 / 3 from any slot, Kamikazee 1,
Acceleration's rate 1.2 / glow every frame / bit / its end, the menu reopened by shield and jump with the same spells,
the 8 seconds still shut it, the drop and its six non-cases), `brave_shot_owner_test.py` (the stone Kirby as caster
for every shot article, an opponent Hero nearer to it; Hero's own: a stone Kirby 40 away or a Kirby not in the stone
not taken; placed.c: crash on the stone Kirby, Hero's crash / Zap's spark by the number), `msc_stack_check.py`
(globals 118), `rolloff_hold_test.py`, `port_check brave` (0 errors; W10 / C4 as before: Hero's own brave.c).
No executable change: A stays exe_v45h, B exe_v46f.
```
python3 tools/kirby_copy_sword.py --fix-skeletons OUT/fighter/kirby/model      # v6's bravesword tree
sh tools/kirby_hero_copy_build.sh OUT; python3 tools/brave_shot_owner_test.py OUT/shot
```

### Hero copy fix v4 (`kirby_hero_copy_fix_v4`): exe_v46g (B), the held sword made; spells on Kirby's plane; Zoom; turning

User (fix v3 A / B): (1) the B build's sword still never shows in the sword spells (`bravesword` installed with v3's
skeletons); (2) the Stone's projectiles show now but Sizz / Sizzle / Bang / Kaboom ... don't hit; the user's
clarification: they hit every other opponent and fail **only against Hero**; (3) the menu cancelled and reopened should
draw new spells; (4) Zoom offstage can KO Kirby twice: no leaving the stone during Zoom / Zoom 2 U; (5) cast to the
stick held left / right, as Hero (left / right only: no angles; neutral keeps the facing). Also, for Hero himself: (6)
"Magic Burst as Hero on a slot other than player 1 doesn't spawn anything".

**(1) The sword: the held article was never generated (found statically, certain).** The copy model function
`0x02EFE138` makes the hat first (article 0x19, `0x02EFE254`-`0x02EFE268`). On success the compiler's tail duplication
gives that path its own copy of the held-model kind chain's first compare: `0x02EFE284 cmplwi r27, 0x22; bge
0x02EFE6A0; b 0x02EFE66C`, which skips `0x02EFE664`, where v6's GEN stub sat. `0x02EFE664` is reached only when the
hat's generate fails (`0x02EFE270 beq`) or from the -1 / 4 / 0x13 / 0x15 / 0x28 paths. The Hero copy's hat is made, so
kind 0x2C went `0x02EFE6A0` -> `0x02EFE7EC`: no article 0x1A, nothing for the stone check to show. v6's unicorn test ran
the stub from `0x02EFE664` itself and never the function's path to it. Fix (`tools/kirby_hero_sword_cave.py`, exe_v46g =
exe_v46f + three words): `0x02EFE284` -> the same GEN stub (cr0 as the `cmplwi` for every other kind). Also the two
other reads of the held-item table for a Hero player's slot, which still gave Robin's empty name: `0x030C49D8` (the
`c00` fallback when `model/<name>/cNN` is missing) and `0x030C4BE8` (the held item's motion folder,
`fighter/kirby/motion/<name>`: Robin's "" named the motion root) -> the name stub (`r11` / `r12` = `r28 << 2` = `r21`
there). Only those three words differ from exe_v46f (checked word by word); none has a relocation (rpx_patch).
`tools/kirby_hero_sword_test.py exe_v46g exe_v45h exe_v46f`: the function run in unicorn from the hat's generate
(its calls stubbed) for hat made / not made: the Hero copy reaches `0x02EFE748` both ways, Robin's / Sephiroth's
copies never, Marth-style kinds as before; exe_v46f reproduces it (`0x02EFE7EC` with the hat made, `0x02EFE748`
only when it fails); the new name reads give "bravesword".

**(2) Hits on Hero only fail: the projectile is 5 off Kirby's plane, and Hero's hurtboxes are thin.** Robin's thunder
spawner places the weapon at the owner's hand joint in 3D (`0x020073FC`: the joint's world position, z included;
joint 0x10 LHandN for a Kirby). Kirby's stone end pose (SpecialLw1 / SpecialAirLw1 last frames, held through the stone)
has LHandN at model (-5.0, 10.7, 4.0): the first axis is the game's depth, so the spell flies 5.0 off his plane (the
Frizz cast pose: 0.9). Smash 4's hit test is 3D, so a hitbox of radius r 5 deep reaches only hurtboxes of radius > 5 - r.
Hero's are Ultimate's (`brave/param/vl.prc` hit_data: hip / waist 2.0, head 1.55, legs 1.3, arms 0.95), the thinnest of
any fighter; vanilla widest are Robin 2.4, Link 2.6, Mario 3.1, Kirby 5.0. Sizz / Sizzle (3.0) reach every vanilla body
and miss Hero, which is the user's report. Nothing in the MSC, ACMD or native spawn excludes Hero: the spawner passes
Kirby's id and Kirby's team (`0x02F64424`-`0x02F64438`, the weapon set-up `0x02B64740` takes them; `0x02B64074` walks
to the root owner); Hero's MSC has no self-immunity. Fix: `fighters/brave/weapons/shot.c` `sh_plane`: a projectile
whose caster is a stone Kirby (`sh_stone_kirby`) is put on his plane at its start (PostureModule(3, its x, its y, his
position-variable Z)); Hero's own casts untouched. `tools/brave_shot_owner_test.py` checks the placement (every shot,
both levels, the three stone statuses; none for Hero's own) and reproduces the miss from those shapes.

**(3)** `khm_reopen` draws four spells anew (`khm_draw`), as Hero's menu opened again (brave.c `brave_lw_main`).

**(4) The double KO, found:** `khm_update` ran the cast every frame whatever his status and Zoom / Zoom 2 U never
looked at it (Kaclang did). KO'd during the cast (e.g. the stone falling past the bottom blast line in Zoom's 29 frames
before the launch, offstage), the spell went on through the KO / respawn statuses: at 29 it set him airborne
(`func_20(2)`) with a 9-a-frame rise for 40 frames, then put him 120 above a fighter (his position variables) and
pushed him down at 7 a frame for up to 150 frames: off the respawn platform and through the bottom line again. Zoom 2 U
moved him through his position too, and Kamikazee's KO flag (frame 49) could land after the respawn. Fix:
`khm_cast_guard` stops any cast at a KO (status 0xB1 Dead / 0xB2 Rebirth: nothing touches him after) and Kamikazee /
Zoom / Zoom 2 U when he is no longer the stone (the fall put back if mid-flight). `khm_zooming` (the choice to the
flight's end) holds the stone's ends off: special and the ground timer in its hold loop `func_2323`, the air drop
`khm_stone_drop`; he is invincible (`0x0F00011C`) until the launch (intangible in the flight, as before), so no hit ends
the stone either. The game's own KO still happens, once.

**(5)** `khm_turn` at the choice: Hero's rule (brave.c `brave_lw_loop`, fix 68): the stick held back past half (stick x
x facing < -0.5) turns him round (PostureModule(0, -lr), then 2); every spell then goes his facing's way (the projectiles
take it at the spawn, the sword hitboxes, Zoom 2 U aims itself). The stone's motion is untouched (the stone turns with
him).

**(6) Hero's Magic Burst / Kamikazee / Woosh / Zap from any slot** (Hero files; fighters/brave/README.md): his MSC sent
`tier + 8 x slot` (Magic Burst), `1 + 8 x slot` (Kamikazee), `level + 4 x slot` (Woosh, Zap's target): past 3 for every
slot but P1 and for P1's 21-80 MP tiers (port_check W10, the rule of fix v3's invisible spells). Now the level alone
(0-3) and a marker on Hero (`brave_mark`: his ARMOR_THRESHOLD = 9000 + the tier / target slot for 3 frames, then his
own back) that `placed.c` `pl_marked_hero` reads off the position variables. `tools/brave_mark_test.py`; port_check W10
is an ERROR now (docs/ultimate-port-guide.md catalogue). Shipping `brave.mscsb` again brought up an older ERROR
(port_check C1 / msc_stack_check): `brave.c` used globals up to index 134, past the game's 128 (crash fix v2: 128-134
wrote over the script context's 7-word sub-object at +0x204). The last seven (`brave_lw_released` ... `brave_lw_burst`)
now live in his New_Var slots 0x0F0003B6-BC (the marker's in 0x0F0003BD-BF): 128 globals (0-127). `brave_mark_test.py`
runs Command Selection for 16 spells with them as globals (the substitution reversed) and as slots: the same calls.

**Diagnostic executable** (`tools/diag_kirby_hero_cave.py`, tested by `tools/diag_kirby_hero_test.py`; exe_v46g_diag =
exe_v46g + 12 hooks in 0x04BAC000-0x04BAF000): OSReport lines `S4KH cpy / gen / res / stn / swd / spawn / hit` (the copy
model function's kinds, the held article's handle, the model path test, the held article's update in the stone, the
sword int and visibility, the thunder spawner's positions for Kirby / Hero, the spells' hit methods), each tag capped.
Shipped beside B in case the sword still doesn't show or a spell still misses Hero.

Tests: `kirby_newcopy_test.py` A and B (fix v4: the reopen draws anew; Zoom / Zoom 2 U: zooming, the special / ground
timer / drop held off, invincible before the launch, KO'd mid-cast then nothing through KO / respawn, out of the stone
mid-flight stopped; Kamikazee no KO after a KO; the turn for stick back / forward / neutral, both facings; fix v3's MSC
fails these 16 checks), `kirby_hero_sword_test.py`, `diag_kirby_hero_test.py`, `brave_shot_owner_test.py`,
`brave_mark_test.py`, `msc_stack_check.py` (Kirby 118 globals), `rolloff_hold_test.py`, `port_check brave` (0 errors).
```
python3 tools/rpx_patch.py EXE_V46F.rpx EXE_V46G.rpx $(python3 tools/kirby_hero_sword_cave.py)
python3 tools/kirby_hero_sword_test.py EXE_V46G.rpx EXE_V45H.rpx EXE_V46F.rpx
python3 tools/rpx_patch.py EXE_V46G.rpx EXE_V46G_DIAG.rpx $(python3 tools/diag_kirby_hero_cave.py --rpx EXE_V46G.rpx)
python3 tools/diag_kirby_hero_test.py EXE_V46G_DIAG.rpx EXE_V46G.rpx
sh tools/kirby_hero_copy_build.sh OUT; python3 tools/kirby_newcopy_test.py OUT/kirby_B.mscsb
python3 tools/brave_mark_test.py HERO_OUT; python3 tools/brave_shot_owner_test.py HERO_OUT    # brave + 7 articles
```

### Hero copy fix v5 (`kirby_hero_copy_fix_v5`): exe_v46h (B), the held sword drawn on the stone

User (fix v4 B, in game): "the sword still doesn't appear for Kirby's Stone Menu copy". Re-traced from the start, with
the held article's own code run in unicorn (fix v4's test ran single functions with stubbed calls).

**The chain, checked again:**
- Made: the copy model function's hat-success path reaches the GEN stub (fix v4, `0x02EFE284`); article 0x1A is the
  only generate of Kirby's "simple" article (`0x02EFE750` is the only `li r4, 0x1A` before `bl 0x02C03EA0`).
- Model: the loader (`0x030C4694`, called for types 0xC / 0x11 / 0x164 / 0x165 for every match entry from
  `0x030C4D28`) builds `fighter/kirby/model/` + name + `/c0` + costume (format `%s%s%s%d`, `0x10159A24`), falls back to
  `c00` (`0x030C49D8`), loads it as resource `type x 0x29 + entry` (costume in the top bits), and the motion folder
  `fighter/kirby/motion/` + name (`0x030C4BE8`). Vanilla held items (marthsword, ikesword, ...) have no motion folder
  (only cloudsword does): none is needed. The installed tree (v6 + fix v3) has all eight folders, each with the nine
  files of vanilla `marthsword/c00` (`model.xmb` / `nhb` / `sb` / `jtb` byte-identical to it), the NUT ids the NUDs
  use (0x40C5E000 + 0x80 NN, + 1, + 2; 0x10080000 / 0x10102000 shared), fix v3's two bones, the mesh rigged to bone 0
  as the working copy hats are; `kirby_copy_sword.py --fix-skeletons` on v6's tree reproduces it byte for byte.
- Init (`0x02B02078`, the article's vtable entry at `0x100E0984`): reads Kirby's copy kind (`0x100000A4`) into the
  article's int `0x10000007`, then links it to a Kirby joint (`0x02B61FB8`) and sets the LinkModule constraint flags
  (vt +0x314 = `0x02C5B164`, +0xAC) by kind: < 0x12 joint 0x19; 0x12 / 0x13 / 0x25 / 0x27 / 0x36 / 0x37 joint 0x18
  (`0x02B022EC`); 0x22 joint 1000 (BodyBN); 0x2E / 0x2F joint 0x1A; the rest 0x19; flags 0x108 except 0x37 (0x103),
  0x2E (8) and **0x2C (Robin's case, `0x02B02248`): joint 0x19, flags 8**. Kirby's jtb table 0 (joint n = entry n - 1): 0x18 LHaveN,
  0x19 RHaveN. So the Hero copy's sword hung on RHaveN; the model and the spells' hitboxes (`khm_sw_*`, bone 0x18) are
  built for LHaveN.
- Update (`0x02B02534`, vtable entry `0x100E09CC`): copy_held_cave's hook, the sword cave's stone check, then the
  show path (`0x02B026B4`) sets the article's own visibility; then by Kirby's motion kind it sets link 3's attribute 7
  (`0x02B02824`-`0x02B02860`) for every motion but 0x318-0x31A (`SonicSpecialNSpin` / `Homing` / `HomingStart`, crc32
  of the names), where it clears it (`0x02B02794`).
- **Attribute 7 = draw only while the parent is visible.** The weapon VisibilityModule (vtable `0x1010C55C`; fighters
  `0x1010C724`) is_visible, vt +0xA4 = `0x02C77004`: its own flag (+8) AND the LinkModule's vt +0xDC (`0x02C560C8`):
  when the module's mask (+0x84) has bit 7, the parent link's owner's VisibilityModule is_visible. set_attribute
  `0x02C5847C` (link `[+0xC] + 0x38 n`, +0x30 bits), is_attribute `0x02C5852C`. The Sonic exception is the game's own
  case of a held model (the sphere) shown while Kirby is hidden.
- **Kirby is invisible for the whole stone**: his MSC's `func_2337(1)` (stone article shown, `VisibilityModule(0x2710,
  0)`: handler `0x02C77060` -> vt +0x94, +8 = 0) in the transform's blink (`func_2336`, 0x155) and at the hold's init
  (`func_2339`, 0x175); only SpecialLwEnd's main shows him again.

**Cause (certain: read, and reproduced by running the game's code):** every frame of a sword spell, v6's stone path
set the sword's own flag, and the same update then set attribute 7 again (the stone's motions aren't Sonic's), so the
game's is_visible was `1 AND Kirby (0)`: never drawn, in v6, fix v3 and fix v4 alike. Second, smaller: the RHaveN
link (wrong hand for the model and the hitboxes).

**Fix** (`tools/kirby_hero_sword_cave.py`, exe_v46h = ported_sound_ids_v1's B exe (exe_v46g + sound_alias_cave.py v2) +
these words; only the cave's words differ from it, checked word by word):
- STONE_SHOW (CAVE2 `0x04BAF200`-`0x04BAF244`, free between kirby_robin_book_cave.py's and kirby_copy_new_cave.py's
  spaces): the stone check's show case now does the show path's preamble (`0x02BF0594(r1 + 0x68)`, the item
  MotionModule vt +0x2F4, as `0x02B026B4`-`0x02B026CC`) and goes to the Sonic branch `0x02B02794` with r7 = `[r30 +
  0x68]`, r10 = its vtable + 0x3C0 (as `0x02B02718`-`0x02B02724`): link 3's attribute 7 cleared, the item shown. The
  hide path is the game's: its motion check sets the attribute back (`0x02B02824`), so after the spell the sword
  follows Kirby again.
- The stone check now first requires the article's copy kind (r31, its int `0x10000007`) to be 0x2C: Kirby's int
  `0x1000008B` is a copy int whose native users store other things (`0x02F02208` writes an object id there), and with
  the parent visibility bypassed a stray 1 would otherwise show another copy's held model on the stone.
- JOINT: `0x02B02184` `beq 0x02B02248` -> `beq 0x02B022EC`: kind 0x2C takes Marth's path (joint 0x18, flags 0x108).
  0x2C's case is otherwise dead (no vanilla held article for 0x2C; GEN makes one only when granted for a Hero).
- v6's cave shrank by the old show branch; its tail words are zeroed. No word with a relocation (rpx_patch.py).

**Tests:**
- `tools/kirby_hero_sword_vis_test.py exe_v46h exe_v46g` (new; the exes run in unicorn with every section mapped):
  the real update `0x02B02534` frame by frame through the hooks and caves, with the game's own VisibilityModule /
  LinkModule code and a link 3 from the article to Kirby; Kirby's status / motion / work modules, the object lookup
  `0x02BF2108` and the link call stubbed; opcode-4 (paired-single) saves nopped in the emulated copy. The stone with a
  40-frame sword spell, before / after it, the stone's end, Wait: drawn (is_visible `0x02C77004`) on exactly the spell's
  frames, attribute 7 back on after. exe_v46g: never drawn, and on a spell frame own flag 1 / attribute 1 (the in-game
  report reproduced). Both: Marth's sword in 0x380 / 0x382 / 0x384 and Shield Breaker 0x1C1, hidden in Wait; Sonic's
  sphere in 0x318-0x31A with Kirby hidden, hidden in 0x316; Marth's held model never on the stone. The real init
  `0x02B02078`: kind 0x2C on joint 0x18 / flags 0x108 (exe_v46g 0x19 / 8); 0x12 / 0x25 / 0x1D / 0x22 / 0x2F as before.
- `tools/kirby_hero_sword_test.py exe_v46h exe_v45h exe_v46f`: as fix v4, the stone check per kind (0x2C to
  stone_show, 0x12 never), stone_show's words and the original show path / Sonic branch it relies on, the JOINT word,
  CAVE2 free in both bases.
- `tools/diag_kirby_hero_test.py exe_v46h_diag exe_v46h`; `kirby_copy_new_test.py` (base exe_v43),
  `kirby_hero_menu_test.py` (exe_v44), `kirby_copy_pool_test.py` (exe_v45d) on exe_v46h; `sound_alias_cave_test.py`
  (only its "no other word changed" check differs, by these words).

**Diagnostic executable** (`tools/diag_kirby_hero_cave.py`, now on exe_v46h, space `0x04BAA000`-`0x04BAE000`: fix
v4's `0x04BAC000`-`0x04BAF000` overlaps sound_alias_cave.py's `0x04BAE000` in the B chain since ported_sound_ids_v1).
Lines in chain order: `cpy`, `res` (model path found), `gen` (handle), `lnk` (new: the init's joint), `stn` (now at
the stone check's entry: status and the article's kind), `swd` (the sword int every frame it is 1 and the frame after,
with the article's own flag, Kirby's, the attribute mask), `vis` (new: the update's end for kind 0x2C, every spell
frame and the frame after: int, own, Kirby, mask, drawn = is_visible), `spawn`, `hit`. The two hooks in `0x02Bxxxxx`
are out of branch reach of the cave and go through trampolines at `0x037EE578`-`0x037EE588` (the Havok cave's zero
tail; diagnostic only).

**Not checked in game / approximated:** where LHaveN is in the stone (the hold motions 0x2ED / 0x2F1 have no
animation; fix v4 took SpecialLw1 / SpecialAirLw1's last frame as the held pose: LHaveN at about (-2.8, 11.2, 3.6),
the blade from (-2.7, 11.8, 5.6) to (-3.7, 8.1, -8.1), above most stone models' 8-unit top); what the link flags'
0x100 bit does (Marth's value is kept); the README asks for a clip.
```
python3 tools/rpx_patch.py B_EXE_V46G_IDS.rpx EXE_V46H.rpx $(python3 tools/kirby_hero_sword_cave.py)   # ported_sound_ids_v1 B
python3 tools/kirby_hero_sword_vis_test.py EXE_V46H.rpx EXE_V46G.rpx
python3 tools/kirby_hero_sword_test.py EXE_V46H.rpx EXE_V45H.rpx EXE_V46F.rpx
python3 tools/rpx_patch.py EXE_V46H.rpx EXE_V46H_DIAG.rpx $(python3 tools/diag_kirby_hero_cave.py --rpx EXE_V46H.rpx)
python3 tools/diag_kirby_hero_test.py EXE_V46H_DIAG.rpx EXE_V46H.rpx
```

### Hero copy fix v6 (`kirby_hero_copy_fix_v6`): exe_v46i (B), Hero's sword swung on the stone

User (fix v5 B): "The sword appears now, but doesn't animate." The held sword hangs on Kirby's LHaveN (fix v5), and
Kirby, invisible in the stone, holds a pose: his hold motions 0x2ED / 0x2F1 have no animation (Kirby's motion table:
hash 0).

**How the sword is moved (chosen and why).** Three ways were looked at:
- The article's own motion: Kirby's "simple" article loads `motion/<name>` (its set-up `0x02B01ED8`: model
  `0x030C5EE0`, motion pack `0x030C6054`, MotionModule vt +0x44), and the stone show path only sets its frame from
  Kirby's (`0x02BF0594` -> vt +0x2F4). Nothing found picks its motion: the simple article has no `motion.mtable`
  (no `animcmd/weapon/simple`), no ACMD of Kirby's changes article 0x1A's motion, and cloudsword's
  `FitKirbyCloudSwordMainD00SpecialN` is played by code not traced. Its hitboxes would also have stayed on LHaveN.
- Joint overrides (MSC ModelModule 1 / 7 on LHaveN): no motion change, but LHaveN's world still depends on the hidden
  pose of the arm above it, and the per-frame data (four spells, up to 108 frames) would be hundreds of calls.
- **Chosen: Kirby's own LHaveN moved by a Kirby motion played during the spell.** This is the same mechanism the Marth
  copy's sword aerials use (LHaveN tracks in Kirby animations moved `marthsword`, confirmed in game). The animation
  fixes the whole hidden skeleton, LHaveN included, and the bone-0x18 hitboxes and effects follow the blade with no
  extra work.

**Data (Ultimate's files, `tools/kirby_hero_sword_anim.py`):**
- Spells -> animations, from the motion_list: special_lw17 / 18 `d03speciallwskill3`, 19 `skill1`, 20 `skill2` (21
  Psyche Up is `skill4`, no sword). Cancel frames 47 / 47 / 40 / 88.
- The blade's frame on Hero is Sword1 @ inv(S2H): the model is given in HaveR's frame as Sword1 sits in it in the bind
  pose (`kirby_copy_sword.sword_to_have`: (0.2023 - y, x, z)). Sword1 has its own tracks in these spells, up to ~50
  degrees off its bind relation to HaveR. A first build driven by HaveR put the sword hitboxes 4-6 off Hero's (the
  swing test caught it).
- Clock: cast frame g shows Hero's motion frame mf(g), with the reference scripts' Set_Frame_Duration rates (the same
  clock as the hitboxes, `kirby_hero_sword_msc.timing`). Animation index mf - 1 (ACMD frames are 1-based),
  interpolated (position lerp, rotation nlerp). One key per cast frame, 0 to `khm_sw_end` (54 / 51 / 62 / 108 frames).
- Placement: Hero's model space = Kirby's (Y up, +Z facing). The path's scale about the feet is 1 by default: Hero's
  own arc, the sword at Hero's size, as v6's decision (Hero's sword "attached at Hero's hand offset", its hitboxes as on
  Hero; the bone-0 hitboxes are Hero's positions too). `--scale kirby` (the stone's top 8.02 / Hero's 19.34 = 0.415,
  with `kirby_copy_sword.py --rescale` for the model) was rendered for comparison: that sword is inside the 8-tall
  stone for most of each spell. A Hero-size blade on the scaled path went under the floor. Previews in the package.
- The animation: every bone of Kirby's main pack at `FitKirbyBodyMainD03SpecialLw1`'s last frame (the stone pose; the
  part bones are not in the main pack), constant; LHaveN per frame = inv(LHandN's stone-pose world) @ the wanted
  model-space matrix (no shear). Encoded and re-posed within 0.005.
- Arm hitbox (Hero's bone 0x16, his forearm ArmR, ID 2 in each spell): the stone has no arm, so it goes on LHaveN at
  ArmR's origin in the blade frame at its frame (`reference/kirby_hero_sword_path.json` "arm"). Before, it was on
  Kirby's still LArmJ.

**Files:**
- Kirby's `motion/body/main.pac`: his own pack (vanilla, byte for byte) plus `FitKirbyBodyMainD03SpecialLwBraveSword17`
  - `20`.
- exe_v46i = exe_v46h + Kirby's motion table (`0x103850A4`, 8 bytes a motion) slots 0x304-0x307 = the four animations'
  hashes (`zlib.crc32(name, 0xFFFFFFFF)`, as `kirby_marth_sword.py`) and SpecialLw's flags (0x4). These slots were
  empty: hash and flags 0, `motion.mtable` hash 0, so a change to them runs no ACMD. Marth's aerials use 0x301-0x303.
  The change motion `0x02C5D7xx` reads the entry's flags halfword (+6).
- `kirby.c` (B): `khm_sw_motion(n, f)`, called from `khm_sword` every cast frame:
  - Kirby's motion becomes `khm_sw_slot(n)` = 0x304 + n - 0x11 (`MotionModule(0x1, slot, f, 1.0)`) if it isn't already;
  - its frame is set to the cast frame (`MotionModule(0x2713, f)`).
  - Two exceptions:
    - Right after a landing (motion 0x2ED / 0x2F1 at frames 0-2, set by the hold loop's `func_2262`), it waits: the
      hold motion's own script (the landing hitbox) runs.
    - After the spell he stays in the slot. A change back to the hold motion would rerun its script (the hitbox).
  - The generated block (`tools/kirby_hero_sword_msc.py`, now reading `reference/kirby_hero_sword_path.json`): the arm
    hitbox on LHaveN at its offset. With a path scale other than 1, the sword offsets and the sword effects' sizes are
    scaled.
  - Globals 118.
- Diagnostic: `diag_kirby_hero_cave.py`'s vis line also gives Kirby's motion kind (`mot=304`-`307` while swinging).
- `ModAnimNames.txt`: `BraveSword17`-`20` with `-> body/FitKirbyBodyMainD03SpecialLwBraveSword1N.omo +
  bravesword@LHaveN` lines (Sm4shCommand rebuilt).

**Tests:**
- `tools/kirby_hero_sword_swing_test.py exe_v46i exe_v46h MAIN.pac KIRBY_MAIN.pac KIRBY_VBN ULT_BRAVE` (new):
  - the table words (empty in exe_v46h, no other word changed);
  - the pack (Kirby's entries byte for byte, plus the four);
  - each animation decoded and posed against Hero's blade frame recomputed from the Ultimate files and the scripts
    (within 0.05 on every frame), all other bones constant;
  - every sword hitbox the MSC makes, at its frame, at Hero's own hitbox point on his blade and inside the blade's
    reach; every arm hitbox at ArmR;
  - natively (`kirby_hero_sword_vis_test.World`): the held sword's update with Kirby in 0x304-0x307 draws it while
    the int is 1 and hides it after.
- `kirby_newcopy_test.py` fix v6 (the MSC in its interpreter):
  - each spell, ground and air: the motion changed once, its frame = the cast frame on every frame 0-end, none after;
  - a landing mid-cast: 0x2ED kept on its frames 0-2, then the spell's motion at the cast frame;
  - the arm hitbox on 0x18 at the path's offset;
  - all earlier checks pass.
- Also run: `kirby_hero_sword_vis_test.py`, `kirby_hero_sword_test.py`, `diag_kirby_hero_test.py` on exe_v46i(_diag);
  `msc_stack_check.py`, `rolloff_hold_test.py`.

**Not checked in game / approximated:**
- Whether Kirby's hidden TransN offset (SpecialLw1 ends with TransN at (0, 9, 0)) is drawn. The path is solved through
  it, as the game poses the bones. If the game drops it, everything is 9 lower.
- The ground animations serve air casts too.
- Sword_Glow trails are still left out. They would need ACMD scripts for the slots, so a `motion.mtable` name.
- The spells' bone-0 hitboxes and effects stay where v6 put them (Hero's positions).
```
python3 tools/kirby_hero_sword_anim.py ULT/brave KIRBY OUT --rpx EXE_V46H.rpx --preview PREVIEW   # OUT: main.pac, rpx_args, path.json
cp OUT/path.json reference/kirby_hero_sword_path.json
python3 tools/kirby_hero_sword_msc.py > /tmp/sw.c       # the GENERATED block in kirby.c
sh tools/kirby_hero_copy_build.sh MSC_OUT               # kirby_B.mscsb
python3 tools/rpx_patch.py EXE_V46H.rpx EXE_V46I.rpx $(cat OUT/rpx_args.txt)
python3 tools/rpx_patch.py EXE_V46I.rpx EXE_V46I_DIAG.rpx $(python3 tools/diag_kirby_hero_cave.py --rpx EXE_V46I.rpx)
python3 tools/kirby_hero_sword_swing_test.py EXE_V46I.rpx EXE_V46H.rpx OUT/motion/body/main.pac KIRBY/motion/body/main.pac \
    KIRBY/model/body/c00/model.vbn ULT/brave
python3 tools/kirby_newcopy_test.py MSC_OUT/kirby_B.mscsb
```

### Hero copy fix v7 (`kirby_hero_copy_fix_v7`): the swing where the game draws it, the stone kept, Hero's trails

User (fix v6, clip `MedalTVCemuWiiUEmulator20261114124342677`): "The sword swings now, but it's too low and doesn't
rotate correctly. Also now when the stone ends during sword moves, Kirby is visible in the animation rather than Kirby
staying in the stone state until it finishes. After fixing that, please begin on the sword trails." No executable
change: exe_v46i stays (the motion table words are the same).

**How the game draws the swing: measured on the clip (`tools/kirby_hero_sword_clip.py`).**
- The clip shows the first five frames of a Flame Slash from the 100t stone, side on. The pommel and the blade's end
  were read on 2x crops in stone units: 24 px a unit, the stone 11.6 wide and 8.1 tall.
- Fix v6's animation drawn the way fix v6 assumed misses all five frames: the pommel 6.5-9.6 too high, the blade
  117-173 degrees off.
- Two engine rules make the same animation match: pommel within 0.3-0.9, blade within 4-19 degrees (yellow over the
  clip's sword in `preview/clip_v6_vs_model.png`).
  - **TransN's translation is not drawn** (`TRANS_DRAWN = False`). It is the root's motion: SpecialLw1 ends with
    TransN at (0, 9, 0), the 9 the sword was low by.
  - **A held item is drawn turned -90 about the joint's Z** (`ITEM_TO_HAVE`): item point v at joint @ K @ v, so the
    item's +Y (bravesword's blade) lies along LHaveN's +X.
    - A free fit of the blade's axis in LHaveN's frame over the five frames gives (0.99, -0.14, 0.03), error 0.004.
      The +Y fix v6 assumed scores 8.6.
    - The vanilla Marth copy agrees. marthsword's blade is +Z under its HaveN bind (90, 0, -90), and with K it comes
      out along LHaveN's +Y. That is forward at Shield Breaker's thrust (`FitKirbyMarthBodyMainD00SpecialNEnd` frame
      15, LHaveN's +Y = (-0.03, -0.01, 0.96)).
  - One frame offset: the sword's first visible frame shows cast frame 1.
- So `tools/kirby_hero_sword_anim.py` now solves LHaveN as D @ inv(K) through the stone pose without the root's
  translation, where D is the wanted item frame (Hero's Sword1 @ inv(S2H), as fix v6).
  - S2H also turns by +90 about Z, so LHaveN's frame is now exactly Hero's Sword1 frame, 0.2023 apart along -Y.
  - In `tools/kirby_hero_sword_msc.py`, Hero's Sword1 offsets (x, y, z) become (x, y - 0.2023, z) on LHaveN; fix v6
    used (0.2023 - y, x, z). His sword effects keep their rotations (fix v6 added 90 about Z).
  - The arm hitbox offsets are recomputed in the new frame.
  - The slot names, the RPX table words and the animation names are unchanged.

**The stone ending mid-spell (cause found, certain):**
- `khm_blocking` held special off only to the spell's cancel frame, and the hold loop's ground timer not at all. Either
  took him to SpecialLwEnd 0x176, whose main shows him again (`VisibilityModule(0x2710, 1)`) and sets the revert
  motion.
- `khm_stone()` counts 0x176 as the stone, so the cast went on there, and `khm_sw_motion` put him back in the swing
  motion, visible.
- Now:
  - `khm_sw_busy()` (a sword spell cast, 0x0F0003A2) holds off both ends to the spell's end (special in
    `khm_blocking`, the timer in `func_2323`). The stone then ends normally.
  - `khm_sword` stops the spell in any status but the hold 0x175 (`khm_sw_stop`, no motion forced).
  - `khm_sw_motion` sets the motion's frame only when it has drifted half a frame from the cast's, since a set jumps
    the slot's new trail script.

**Trails (`tools/kirby_hero_sword_acmd.py`):**
- The swing slots 0x304-0x307 get motion.mtable names `BraveSword17`-`20`.
- Their effect scripts hold Hero's built Sword_Glow / Terminate_Sword_Glow (`reference/brave_sword_spells_acmd.txt`,
  Ultimate's AFTER_IMAGE4_ON / OFF as his port converted them):
  - Hero's textures (trail ids 264-269) and shader 3, so they draw exactly as Hero's own trails. Hero is in the match
    whenever Kirby has his copy.
  - Bones: 0x19 -> LHaveN 0x18, offsets as above.
  - Frames: Hero's motion frames -> cast frames (the swing motion's frames).

  | Spell | Trail on | Trail off | Textures | Blur |
  |---|---|---|---|---|
  | Flame Slash | 3 | 8 (fade 4) | 0x10A / 0x109 | 7 |
  | Kacrackle Slash | 4 | 8 (6) | 0x108 / 0x109 | 8 |
  | Metal Slash | 9 | 16 (2) | 0x10D / 0x109 | 6 |
  | Hatchet Man | 34 | 42 (3) | 0x10A / 0x109 | 6 |

- Built on the Drive's Kirby animcmd (`fighter-modded-scripts-only`: effect.bin sha1 3cdf26b9, motion.mtable 0c2aa945).
  Every other script is unchanged.
- `ModAnimNames.txt` updated, Sm4shCommand rebuilt.

**Tests:**
- `kirby_hero_sword_clip.py V6_MAIN V7_MAIN KIRBY_VBN [--frames CLIP_FRAMES --out DIR --ult ULT_BRAVE]` (new):
  - fix v6 as assumed misses the clip;
  - fix v6 under the two rules matches it;
  - the fitted axis is +X;
  - renders: the clip overlay, and per spell Hero's blade from the Ultimate files vs fix v6 and fix v7 as drawn
    (`hero_v6_v7_17-20.png`: green on white).
- `kirby_hero_sword_swing_test.py ... EFFECT.bin MTABLE`:
  - every animation drawn as the game does = Hero's blade frame (within 0.005);
  - sword and arm hitboxes on Hero's points;
  - the four trail scripts: names, frames, textures / shader, both trail points on Hero's blade.
  - fix v6's animation now fails it.
- `kirby_newcopy_test.py` (fix v6/v7):
  - the swing motion changed once, with no frame sets while it plays in step and one after a 4-frame drift;
  - the landing guard;
  - for each spell, special and the ground timer held off through the spell and taken the frame after;
  - 0x176 or a hit mid-spell stops it with no motion forced;
  - fix v6's MSC fails all of these, the user's report reproduced: special at the cancel frame, the timer at cast 1,
    the swing forced in 0x176.
- Also run: `msc_stack_check.py` (globals 118), `rolloff_hold_test.py`.

**Not checked in game / approximated:**
- The roll of the item turn: rotating about the blade axis, only the blade's line was measurable. -90 about Z is the
  plain choice and matches Marth's sword.
- The trail's look on Kirby is Hero's (his textures and shader), not compared with an Ultimate clip of Kirby.
- That gameplay joint positions (hitboxes) leave out TransN's translation as the drawn pose does.
```
python3 tools/kirby_hero_sword_anim.py ULT/brave KIRBY OUT --rpx EXE_V46I.rpx --preview PREVIEW
cp OUT/path.json reference/kirby_hero_sword_path.json
python3 tools/kirby_hero_sword_msc.py > /tmp/sw.c       # the GENERATED block in kirby.c
sh tools/kirby_hero_copy_build.sh MSC_OUT
python3 tools/kirby_hero_sword_acmd.py KIRBY/script/animcmd/body ACMD_OUT
python3 tools/kirby_hero_sword_clip.py V6_OUT/motion/body/main.pac OUT/motion/body/main.pac KIRBY/model/body/c00/model.vbn \
    --frames CLIP_FRAMES --out PREVIEW --ult ULT/brave
python3 tools/kirby_hero_sword_swing_test.py EXE_V46I.rpx EXE_V46H.rpx OUT/motion/body/main.pac KIRBY/motion/body/main.pac \
    KIRBY/model/body/c00/model.vbn ULT/brave ACMD_OUT/effect.bin ACMD_OUT/motion.mtable
python3 tools/kirby_newcopy_test.py MSC_OUT/kirby_B.mscsb
```
