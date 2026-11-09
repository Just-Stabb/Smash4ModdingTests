# Step 2h readings: Big Goomba, Spiny, Paratroopa, Pooka (3DS code)

These readings come from the 3DS `enemy_fs.cro` (update) ARM and `code.bin` (the framework, with symbols). They cover
the next batch to port: **dekakuribo** (Big Goomba, 0x23), **togezo** (Spiny, 0x4E), **patapata** (Paratroopa, 0x03)
and **pooka** (Pooka, 0x20). They are machine-readable in
`reference/smashrun_enemy_specs/step2h_readings.json`, which uses hand_read.json's entry structure so it can be merged
into it later. That file has every state's text. This page has the conclusions, the porting notes and what is still
open. The generated specs (`<kind>.json` / `.md`) were used only as a map: every state function, helper and vtable
override named here was read in the disassembly. The few points taken from the map without a full re-read are flagged.

Conventions (as in README.md):
- Addresses are enemy_fs.cro offsets unless marked code.bin or Wii U.
- **W** is the enemy work struct `[[[acc+0x30B0]+8]+0]+4` (Wii U `acc+0x3130`). Its fields:
  - **+0 is the HP** (float) and **+4 the max HP**. `BehaviorImpl::notify_on_damage` (code.bin 0x3DA8BC) compares
    W+0 to 0, and Pooka's helpers 0x65020 / 0x65040 read the two fields.
  - +0x08..+0x44 are the movement parameters that the specs call "KineticEnergy".
  - The flags word is `[[[acc+0x30B0]+8]+0]+0x14`: bit 2 dead, 8 bullet done, 0x20 start, 0x80 stun.
- A node N is model.jtb entry N−1 (node 0 = bone 0). ACMD `Special_Hitbox` bones use the same converter: the Big
  Goomba's stomp boxes on nodes 6 / 5 land on RFootJ / LFootJ, which confirms it.
- `random_range(int a, int b)` is inclusive.

## Fighter bounce on Koopas: the Green Shell (user request)

**Bounce to use for the Paratroopa / Koopa (and the stomp in general):** the fighter's StepJump (status 0xB3) with
the tread multiplier at its default of 1.0. This is the fighter's own footstool jump (fighter_param 0x15F
`step_jump_speed_y`, or 0x160 `step_mini_jump_speed_y`). Fix v8's stomp already does this (`StatusModule(3, 0xB3,
0)`, no extra speed write).

How it was found:

- **The 3DS Paratroopa sets no bounce.** Its slot 21 (0x726BC) only changes state: variation 0 / 1 → 9 (wings lost),
  2 / 3 → 19 (shell).
- **The bounce value comes from the tread link event, not from the behaviour.** The fighter's tread status (in MSC)
  sends **LinkEvent kind 6** through LinkModule:
  - 3DS: `LinkModuleImpl::notify_event_msc_cmd` 0x4794E0. The event is built at code.bin 0x479834-0x479868.
  - Wii U: the LinkModule MSC handler is 0x02C58578, op 3 at 0x02C588C4. The event is built at
    0x02C58AE8-0x02C58B6C and sent with LinkModule vt+0x8C.
  - The fighter sets event+0x20 to **1.0** (Wii U constant 0x1010980C) and +0x2C..+0x2E to 0.
  - After the send, it copies +0x20 / +0x24 / +0x28 (floats), +0x2C..+0x2E (bytes) and +0x1C into script
    variables, and returns byte +0x18.
- **An enemy answers the event.** The handler writes a per-kind multiplier, its param 0x11, into +0x20, and sets
  +0x2E = 1:
  - 3DS: code.bin 0x757A14, module `[enemy+0xDC]` vt+0x20(0x11) → `vstr s0, [sl, #0x20]` / `strb [sl, #0x2E]`.
  - Wii U: event switch 0x02D8C450, case 6 at 0x02D8C5D4. It calls behaviour slot 20 through 0x02DB98F4, then
    `acc+0x315C` vt+0x44(0x11) → +0x20 (0x02D8C5F8) and +0x2E = 1 (0x02D8C600).
- **The Green Shell does not answer.** It is item kind **0x46 `greenshell`** in the Wii U item table 0x104157A0
  (0x24-byte entries, name at +0x18); the 3DS table 0xC2EB28 is the same.
  - A scan of the whole Wii U text finds no other writer of the event's +0x20 / +0x2E than the enemy handler, and the
    same holds for the 3DS code.bin.
  - The only item link-event switch found (Wii U 0x0303CC40) handles kinds 2 / 8 and has no case 6.
  - So a fighter that treads a Green Shell keeps the default multiplier of 1.0.

**Not verified:**
- That the fighter's tread MSC multiplies `step_jump_speed_y` by this float. This is inferred from the 1.0 default;
  the Wii U fighter tread status script was not read.
- The Green Shell's own tread path: its tread area, and whether stepping on it goes through event 6 at all.
- Each enemy's param 0x11 (the gl entry; the 3DS gl file is not in the dump).

## Big Goomba (dekakuribo, 0x23)

The Big Goomba walks and charges. It has two attacks, an angry stomp dance and a charge, and all its hitboxes come
from ACMD. Stepping on it costs it 25 HP. **It does not split**: it has no articles and no spawn or create calls.

- **States.** These are the 3DS ids. The state functions are in the JSON (`read`).
  - **1 Fall → 2 Landing.** Landing plays `request_quake(3)` and se 0x2910009.
  - **3 Walk**: WalkL, MotionModule +0x50 = 0.3, kinetic 10.
    - Every 60 state frames it calls `check_target` with P1[0] (type 2, range 150 × 40, offset (10, 10)) and faces
      the fighter it finds.
    - A fighter within **28** (3D distance, P0 f18) → **4**; farther away → **6**.
    - A wall ahead, or a ledge for variation 1, sets a turn flag: `clear_speed_all` until the walk motion loops, then
      `reverse_lr` and restart 3. There is no turn motion.
  - **4**: W+0x24 / +0x2C = 0, kinetic 5. It is a zero-height "jump" counted 3 times, so it stands about 3 frames in
    the Fall pose, then goes to **5**.
  - **5 Angry**: AngryL, kinetic 0, for 200 state frames (P0 f19), then back to 3.
  - **6 Run start**: a hop back. W+0x24 = 3, +0x2C = 3.5, and W+0x20 = −0.5, or 0 if
    `check_cliff_distance_lr(3/g + 2, −lr)` finds a ledge behind it. Kinetic 5, AttackRunStart at 0.6. After 30
    frames → **7**.
  - **7 Run**: RunL, rate 0.6, kinetic 10.
    - Every 100 run frames it searches with P1[1] (200 × 100); a fighter behind → **9** RunTurnL (0.6), then back
      to 7.
    - A wall, or a ledge for variation 1 → 9; off the ground → 1.
    - After **200 run frames in all** (the turns do not reset the counter) → **8** RunBrakeL (se 0x2910008) → 3.
  - **10 / 11** are the stomp results below; **12** is death; **13** removes it.
- **Contact damage: ACMD only.**
  - `set_attack_data` (slot 45 0x869F4) is an empty function, so the P2 entry (state 0) is never armed. Slots 47 / 48
    (0x86C88 / 14) arm nothing either: no P2 entry has state 14.
  - **AngryL** (state 5), in each 100-frame loop: id 1 at node 6 RFootJ on frames 28-36, id 2 at node 5 LFootJ from
    frame 78. Both are **4 %, angle −30 (330), kbg 100, fixed 80**, size 5, offset (2, −3, 0), hitlag 2, shield
    damage 2, rehit 60. Each stomp also plays QUAKE(3) and effect 0x1000026.
  - **RunL** (state 7): **6 %, angle 30, kbg 100, bkb 80**, size 5, node 4 HeadN, offset (−5, 5, 0), facing
    restriction 3, rehit 60, QUAKE(3) every 10 frames.
  - **WalkL / Landing**: a 0-damage flinchless push box (node 4 HeadN, size 3, kbg 60, fkb 1).
  - **Death** (motion 18 Damage, state 12): **12 %, 361, kbg 100, bkb 50**, size 10, RotN.
- **Stomp (slot 21 0x85FE0).** It calls `add_damage(25, 0)` (P0 f15), then takes 25 from HP (W+0):
  - HP still above 0 → **10 Stepped**: 24 frames, se 0x291000C, then walk.
  - Otherwise HP = 0 → **11 Collapses**: `notify_on_death`, se 0x291000B; at the motion's end
    `create_dead_item(1, 20)` → remove.
  - Tread area (P5[0]): on, node 0, 14 × 3, offset (0, 6).
- **Damage and death.** Slots 64-66 = 3 / 1 / 1, death 67 = 12. It has no leave. Slot 38 = 1 (the model flips).
- **Slot 3 (every frame)**: the eyes follow fighter 0. The angle from RotN to the fighter sets
  `set_frame_material(frame 1..59)`.
- **Porting notes.** It fits the walker state-table engine (kinetic 10 as Kuribo's) with the fix-v8 stomp detection
  (TREAD state → a slot-21 handler that branches on HP).
  - **New: ACMD-armed hitboxes.** The walker engine arms P2 entries; here the hitboxes come from the motions' ACMD,
    which `change_motion_state` already runs on the Wii U, if the converted animcmd has them.
  - **New: the HP write.** The HP is W+0 (Wii U `[[[acc+0x3130]+8]+0]+4` +0); `add_damage` (code.bin 0x4D2FE4) is
    not mapped on the Wii U.
  - **New:** `MotionModule is_looped` (0x5048D0), `get_sum_speed3f` (0x96EBFC), and `check_cliff_distance_lr`
    (0x9EAED4; the cave's CHECK_CLIFF_LR 0x026A6D88 may be this one).
  - The quake is the White Bear's REQ_QUAKE. The eye material animation is optional.

## Spiny (togezo, 0x4E)

The Spiny's body hurts all the time and it cannot be stomped. Its variation 0 is the egg (Paipo).

- **Variation 0 (egg).** It starts in **1**, spinning: node 2 is rotated by a speed-derived step in slots 55 / 5.
  Then **2** bounces (kinetic 4). A landing with |speed| < 0.5 hatches it: `L622F4` makes the variation 1,
  re-runs initialize, swaps the meshes and re-arms the attack → **5 Change** (se 0x6D90000) → walk or turn.
- **Variation 1.**
  - **8 Walk**: kinetic 1, `move()`. A wall → **9 Turn**.
  - For its first **150** walk frames, every **20** frames (P1[0]: 100 × 60, offset (0, 10)) it turns toward a
    fighter behind it.
  - After **200** walk frames → **10 Leave**: `init_common_leave(P6 {120, 0.1, 5, …})`.
  - **6 / 7** are fall and landing.
- **Contact: always on.**
  - At start and at the hatch, `L62440` arms id 0 from P2[0] (egg: angle 361) or P2[1] (Spiny: angle 70). Both are
    **power 1, kbg 100, bkb 70, size 2, node 2 RotN**.
  - Its `set_attack_data` (0x37568) clears only ids ≥ 1, then arms the P2 entries from index 2 whose state matches:
    entry 2 for state 4, entry 3 for state 12. These are the dead bodies, power 5, angle 361, bkb 50, id 0.
- **Stomp: impossible.** Its tread area is off (P5[0].on = 0), slot 21 is BehaviorImpl's nop, and nothing calls
  `enable_tread`. A fighter that lands on it only touches the spike box.
- **Damage.** Slots 64 / 65 = 0 (it has no damage motions or labels).
  - Slot 69 (0x37EAC) ends a running leave (`finalize_common_leave` + `set_correct(5)`), then → **3** egg stun or
    **11** stun (`hit_return_frame` frames, flag 0x80), and returns 1.
  - Slot 66 = var 1 ? 6 : 1; death 67 = var 1 ? 12 : 4 (bullet).
- **Facing.** At start it does not turn to a target. The hatch and the landing face the nearest fighter. Slot 38 = 1.
- **Porting notes.** Use the walker engine (kinetic 1 walk, turn, fall / landing) with the flier framework's
  `hit_return_frame` and common leave. The always-on attack is set once in start (as Gordo's), and set_attack_data
  must keep id 0.
  - **New:** the stomp detection must skip it (its TREAD area is off).
  - **New for the egg:** the kinetic 4 bounce (W+0x40 = 0.8, the restitution, inferred), the hatch with its in-place
    variation change and mesh swap, and the spin (visual).
  - **New:** `AttackModule clear(id)` (0x4CE5AC; not mapped, so re-arm id 0 instead).
- **Open.** Who calls slot 60 (it hatches the egg); the common spin factor (EnemyParamAccessor +0x198 +0x90 / +0xA0).

## Paratroopa / Koopa Troopa (patapata, 0x03)

The Paratroopa hops and dive-bites until it loses its wings; then it walks as a Koopa, and a Koopa ends as a shell
item.

- **Winged (variations 0 / 1).**
  - **2 Hop**: kinetic 5, with W+0x08 / +0x20 / +0x28 = 0.6, +0x0C / +0x24 / +0x2C = 2.5 and +0x40 = 1. The first
    falling frame sets energy 0's +0x38 = 0.6 and +0x3C = 2.5.
  - Every 10 frames, outside the bite cool-down (+0x1E8, 30 frames), it calls `search_target(var)` (42.5 × 50,
    offset (5, 5)). A fighter found → face it → **5**.
  - **5 Bite wind-up**: the aerial module's `set_mode_normal(0, 0, 0, 0, 10, 10)` with speed (0, −0.5), Bite at 1.5,
    for 15 frames → **6 Bite**: P2 entry 0 armed, 9 frames → **7** → **1 Fall** → 2.
  - Variation 1, on each landing, has a **60 %** chance (`random_range(1, 100) ≤ 60`) to search group 2 (80 × 80) and
    turn (**3** TurnPatapata) if the fighter is behind. A wall → 3.
- **Wings lost (state 9).** Slot 21 (stomp), slot 69 (a hit that does not kill) and slot 13 (capture) make it:
  - variation += 2;
  - hide the wing mesh;
  - play `EffectModule req(0x7030000)` once at the posture;
  - load the walk parameters (L5D968);
  - play NokonokoMode → 10 Fall → 11 Landing → **12 Walk**.
- **Walking (variations 2 / 3).**
  - **12 Walk**: kinetic 1. Every 30 frames it calls `search_target(var + 1)` (70 × 30, offset (10, 10)); a
    fighter found → **14 JumpHold** → **15**.
  - **15**: `set_kinetic_shoot(3, 1, 0.075)`, JumpAttack at 3.
  - **16**: P2 entry 1 armed for 20 frames.
  - **17 Slide** (`set_kinetic_brake_ground(0.04)`) / **18** LandingJumpAttack (`brake_ground(0.1)`, 1.5) → 12.
  - A wall, or a ledge for variation 3 → **13 TurnNokonoko**.
- **Shell (stomped as a Koopa, state 19).**
  - On entry: ShellMode, `disable_hit`, `disable_tread`, `set_current_damage(0)`; the first time also
    `create_dead_item` and `set_already_dead_flag`.
  - At the motion's end, on the ground: `create_item_and_throw(0x94, var 0 / 2 ? 1 : 0, position + (0, 3 − vy, 0),
    current speed, 0, true, −1, −1)`.
  - Item **0x94 `patapata`** (the shell, 2 variations) is in both item tables. The enemy then hides itself and is
    removed (23).
- **Killed as a Koopa (state 20).** The same with kinetic 16, ShellMode at rate 10, and the spinning-shell hitbox
  (P2 entry 2) until it lands.
- **Killed winged (state 8).** BulletMode, `bullet()`, P2 entry 3.
- **States 21 / 22** (riding the shell item, then ShellReturn) are reached by no code read.
- **Contact damage (P2, armed per state):**
  - **6 Bite**: **4 %, angle −50, kbg 100, bkb 40**, size 9, HeadN, offset (7, 0, 0).
  - **16 Leap**: **2 %, 361, kbg 100, bkb 40**, size 5, HeadN, offset (3, 2, 0).
  - **20 Shell**: **17 %, 361, kbg 70, bkb 50**, size 3, bone 0, offset (0, 3, 0).
  - **8 Dead body**: 2 %, 361, bkb 50, size 3, RotN.
  - Hopping and walking never hurt.
- **Damage and death.** `notify_on_damage` calls slot 67 (death) before slot 69 (reaction):
  - A lethal hit goes to 8 (winged) or 20 (Koopa).
  - Slot 69 returns 0, so the normal damage reaction runs and comes back to slots 64 / 65 / 66, which are read
    *after* the variation change: 2 / 1 / 1 winged, 12 / 10 / 10 walking.
  - Slot 71: variations 0 / 1 call `notify_on_death`. Variations 2 / 3 instead push a request into the module at
    acc+0x30A0 (not mapped); both set +0x1FC = 0.
  - Slot 38 = 0 (no model flip). There is no leave.
  - The material frame is 10 for variations 0 / 2 and 0 for 1 / 3 (the shell colour, not checked).
- **Porting notes.**
  - The walking Koopa is a walker-engine kind: walk, turn, fall, landing, a timed leap with inline kinetic writes
    (`set_kinetic_shoot` = W+0x20 / +0x24 / +0x28 −1 / +0x2C 10 / +0x1C, kick, kinetic 5;
    `set_kinetic_brake_ground` = W+0x14, kinetic 2).
  - The winged hop is walker-like (kinetic 5 hops on the ground), but the bite needs the flier's aerial module (mode
    0 `set_mode_normal` is not in the Wii U's reduced module; uniform-speed handling as Tiki Buzz's `f_amode` would
    do).
  - **Stomp:** the fix-v8 detection with a per-variation TREAD handler (9 or 19). The bounce is StepJump with
    multiplier 1.0 (above).
  - **New:** `disable_hit` / `enable_hit` (Wii U **0x026A75C0 / 0x026A75D4**, HitModule acc+0x30E0 `set_whole`
    0x02C42F00 (3 / 0, 0)), `disable_tread` / `enable_tread` (0x026A75FC / 0x026A7614), `set_current_damage`
    (INIT_DAMAGE 0x02C212F0 + the HP write), `create_item_and_throw` (Wii U 0x026A8F10) with item 0x94 (check that
    the Wii U has its code and files), the wing-loss variation change, and the mesh hide (no Wii U mesh path).

## Pooka (pooka, 0x20)

The Pooka walks, lunges, can go ghost through walls, and is defeated by inflating it until it pops.

- **Walk (3).** Kinetic 1 (W+0x10 = 0.04, +0x08 = 0.15, +0x14 = 0.01), Move.
  - Every `random_range(30, 90)` frames it turns toward the nearest fighter.
  - Every 15 frames (P1[0]: 45 × 40, offset (25, 10)) a fighter found → **5**.
  - A wall or a ledge → **4 Turn**.
  - A fighter within 200 whose ground ray is blocked → **8 Ghost** or **9** jump over. This choice comes from the
    generated map and was not fully re-read.
- **Attack.**
  - **5**: backs off (stick reversed), Attackhold at 1.5, 40 frames, se 0x6B10006.
  - **6 Lunge**: W+0x20 = 2, +0x24 = 1, kinetic 5, Attack at 0.1, se 0x6B10007; **P2 entry 0 armed**.
  - Slot 7 (0x23670) stores the id of the object it hits. In 6, a hit (or a wall) bounces it away (×0.5) and
    `clear_all` ends the hitbox.
  - Landing → **7** slide → 3.
- **Ghost (8).** No ground collision (`set_correct(0)`), `disable_hit`, only the goggles shown, follow effect
  0x7200000 on node 1.
  - Every 30 frames it flies toward the nearest fighter within 200.
  - Once the rays are clear: `set_correct(5)`, `enable_hit`, the meshes back, the effect removed → 1.
  - It can also start in 8 (start 0x21064).
- **Inflate / pop (the defeat).** The threshold +0x180 is **85 %** of max HP (P0 f23).
  - **A hit:** slot 11 (0x22900) runs before BehaviorImpl's `notify_on_damage`: HP ≤ threshold → link / hit-stop
    handling and se 0x6B10004. Slot 69 (0x23A48): HP ≤ threshold → **10**, returning 1 (no knockback reaction);
    otherwise it returns 0 (a normal reaction).
  - **State 10 (Damageballoon, also the death state 67):** a small launch. While it inflates, the balloon frame
    tracks (threshold − HP) / threshold.
  - **Pop:** 15 frames (P0 f24) later, if dead (HP 0, flags bit 2) → **11 Pop**.
  - **Deflate:** if not dead, after 100 more frames (f25) it deflates. Each frame the balloon frame drops by 0.3 and
    `set_current_damage` makes the HP rise with it. At frame 0 the HP is set to **90 %** (f29) → 1.
  - **11 Pop**: the **burst hitbox** (P2 entry 1), effect 0x7200001 at node 3 ×3 and se 0x6B10005. After 1 frame
    `create_dead_item` and `request_quake(3)`; when the sound ends → remove.
  - Slots 56 / 60 / 70 / 17 / 13 keep the balloon consistent in the framework's damage and capture states; their
    callers are inferred.
- **Contact damage:**
  - **6 Lunge**: **2 %, angle 20, kbg 100, bkb 50**, size 5, node 4 BodyN, until the first hit or wall.
  - **11 Pop**: **6 %, angle 70, kbg 100, fixed 60**, size **30** around BodyN.
  - Nothing else: no bullet death, no ACMD hitboxes.
- **Stomp: impossible.** Its tread area is off (P5[0] = {0, 0, 12, 12, 0, 0}) and slot 21 is the default nop.
- **Meshes.** Slot 51 (`sync_lr_and_direction`) and L65084 choose body_normal_L / _R by lr, plus the damage / normal
  sets and the ghost's goggles only. Slot 38 = 1. It has no leave.
- **Porting notes.** The walk, turn, fall and landing fit the walker engine. Most of the rest is new:
  - the balloon state machine: HP-driven motion frame, `set_current_damage`, deflation and pop;
  - a slot-69 damage reaction (the flier framework's hook);
  - the ghost: `set_correct(0)` / `(5)`, a follow effect, a fly-to (kinetic 26 with energy 0's speed written, as the
    fliers);
  - the bounce on hit (slot 7 = the Wii U's 6, the hit notification);
  - `MotionModule set_frame` (0x504928) / `end_frame` (0x953F98), `ray_check` (Wii U 0x02C39F18),
    `reset_gravity` (inline: W+0x3C = gl+0x120, W+0x40 = 1), `update_weaken` (0x7B0FE8), `SoundModule is_playing`
    (a timer would do), and `disable_hit` / `enable_hit` (Wii U 0x026A75C0 / 0x026A75D4).
  - It is the largest of the four.

## Framework calls these kinds use that the port has not mapped

Each line gives the 3DS code.bin address, then the Wii U address where one was found (Wii U HitModule = acc+0x30E0):

- `Behavior::disable_hit` 0x7B0864 / `enable_hit` 0x42FB14: Wii U **0x026A75C0 / 0x026A75D4**. `HitModule
  set_whole` is 0x02C42F00. In the same block: 0x026A75B4 `delete_hit` and 0x026A828C `set_death_flag`, both read
  from `notify_on_death` 0x0269FD6C.
- `Behavior::set_current_damage` 0x7B3688: `init_damage(f)` (Wii U 0x02C212F0), then HP = max − damage.
- `DamageModuleImpl::add_damage` 0x4D2FE4: not found on the Wii U (the Big Goomba's stomp; the HP write suffices for
  the states).
- `Behavior::update_weaken` 0x7B0FE8.
- `Behavior::reset_gravity` 0x7B0F64: inline.
- `set_kinetic_shoot` 0x7B24E0: inline.
- `set_kinetic_brake_ground` 0x7B51F4: inline.
- `is_falling` 0x9EA500: `get_sum_speed3f(1)`.y < 0.
- `EnemyKineticModuleImpl::get_sum_speed3f` 0x96EBFC.
- `MotionModuleImpl::is_looped` 0x5048D0, `set_frame` 0x504928, `end_frame` 0x953F98, `set_frame_material` 0x7FB7FC,
  `set_rate_material` 0x5015AC.
- `check_cliff_distance_lr` 0x9EAED4 (compare with the cave's 0x026A6D88).
- `ray_check_from_pos` 0x7B2E34.
- `calc_angle` 0x7B01D8.
- `Behavior::set_current_speed` 0x7B24B4.
- `get_current_speed_all` 0x9EAD88.
- `is_generate_shoot` 0x9EAA2C.
- `AttackModuleImpl::clear(int, bool)` 0x4CE5AC.
- `EnemyManager::set_already_dead_flag` 0x3E5C84.
- `ItemManager::remove_item` 0x3C94C8.
- `SoundModuleImpl::is_playing` 0x4C27BC.
- `LinkModuleImpl::to_link_stop` 0x478B34.
- `create_item_and_throw` 0x7B4488: Wii U 0x026A8F10.
- The aerial module's `set_mode_normal` 0x5F5A9C: mode 0, not in the Wii U's reduced module's setters.

Already mapped and reused: the walker engine (change_state tables, walk / turn / fall), the stomp detection and
StepJump (fix v8), the quake (REQ_QUAKE), the common leave, `hit_return_frame`, the aerial module, `get_ground_normal`,
`set_correct`, `ray_check`, `enable_tread` / `disable_tread`, the effects (REQ_EFFECT / REQ_FOLLOW / REMOVE_EFFECT)
and `create_item_and_throw`.

## Still open

- The HP of each kind (its gl entry, not in the 3DS dump), and each enemy's param 0x11 (the tread multiplier).
- Big Goomba: the meaning of slots 47 / 48.
- Spiny: who calls slot 60.
- Paratroopa: how states 21 / 22 are entered; the acc+0x30A0 request; is_generate_shoot at start; whether the Wii U
  has item 0x94's code and files; the colour per material frame.
- Pooka: the ghost / jump choice in 3 and the ghost's flight speed were not fully re-read; the callers of slots
  56 / 60 / 70.
  Resolved in step 2j (hand_read.json pooka `port_step2j`): the choice (two ray_checks, the passable floors in or
  out, and a 30-degree "below" test for the drop), the flight (0.5 a frame toward the fighter, every 30 frames), the
  slot callers (56 every frame of the common damage states, 60 when they end, 70 from notify_on_damage without a
  reaction). Correction: the ghost hides the whole model; the goggles are the follow effect 0x7200000.
- Green Shell: the fighter-side multiply and the item's tread path (above).

## Resolved in step 2h (docs/smash-run-port.md, "Step 2h")

- **Param 0x11** is the enemy's work float 0x11 (W+0x44), not a gl word: the event's `acc+0x315C` is a WorkModule
  (vt+0x44 get_float) that the Enemy ctor fills (HP, +0x3C = gl+0x120, +0x40 / +0x44 = 1.0). The 3DS initialize writes
  it: Goomba 0.8, Tiki Buzz 0.98, Big Goomba 0.9, Paratroopa 0.7.
- **The fighter-side multiply** is confirmed: StepJump speed y = step_jump_speed_y x status float 0x1000006 (Wii U
  0x02E79938 = 3DS 0x97E080, kinetic 1 mode 1).
- **HP** (Wii U enemy_param.bin gl group 3, entry kind + 1, +0x14): Big Goomba 40, Spiny 30, Paratroopa 20, Pooka 10.
- **add_damage / set_current_damage**: Wii U Behavior::set_current_damage is 0x026A7E58 (init_damage, then HP = max -
  get_damage(0) 0x02C22ECC).
- **Item 0x94** is in the Wii U item table; its code and files are still unverified.
