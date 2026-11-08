#!/usr/bin/env python3
"""Smash Run: the 3DS behaviours (AI) of five walking enemies the Wii U has none for, ported per kind from
enemy_fs.cro (docs/smash-run-port.md, "Step 2b" and "Fix v5"). Prints rpx_patch.py args, or patches an RPX (after
smashrun_menu.py's, smashrun_field_cave.py's and smashrun_enemy_cave.py's patches; IN.rpx is read for
BehaviorImpl's vtable):

  python3 tools/smashrun_walker_cave.py IN.rpx            the args
  python3 tools/smashrun_walker_cave.py IN.rpx OUT.rpx    IN with them (checks the hook words first)

Each kind is a BehaviorImpl (the Wii U's own enemy framework, the 3DS one: damage, knock-back, down, capture, death
stay its own) with its own state table, numbered as its 3DS table, each state's enter / update written from the
3DS functions (state id: enter / update in enemy_fs.cro). Calls are the Wii U's equivalents of the 3DS ones
(Behavior at the 3DS offset -4, the accessor's modules at the 3DS offset +0x80); "->" is a deferred change_state
(slot 72), "=>" the immediate one (slot 73); input = the AI stick (Behavior::move).

Kuribo (Goomba) 0x01, table 0x10F... (vtable 0xCD308):
  1 fall      kinetic 8, ground off, Fall loop; on the ground => 2
  2 landing   kinetic 0, ground on, Landing; at its end -> 3
  3 walk      WalkL at p+0x14 (0.6), kinetic 0xA (the walk animation's own movement), ground on; input (lr, 0);
              every interval frames (search 0: 100) search_target(search 0) -> if found: face it, => 4; off the
              ground -> 1; a ledge (variation 1 only; variation 0 walks off) or a wall ahead -> reverse_lr, -> 3
  4 notice    the startled hop: E+0x20 = p+0x1C (-0.4: back), kinetic 5, ground off, RunHoldL loop; on landing
              ground on; p+0x2C (30) frames after entering -> 5, the run counter 0
  5 run       RunL at p+0x28 (1.0), kinetic 0xA, ground on; the only state with the contact attack (vl attack
              list: state 5, KURIBO_BUMP); every 60 run frames search_target(search 1): a target behind -> 7;
              a wall ahead (or a ledge, variation 1: clear_speed_all) -> 7; off the ground -> 1; after p+0x30 (110)
              run frames -> 6
  6 brake     RunBrakeL, kinetic 2, ground on; at its end -> 3
  7 run turn  RunTurnL, kinetic 2, ground on; at a ledge clear_speed_all; at its end reverse_lr, => 5
  8 collapses stepped on (slot 21 on the 3DS, 20 here: below) => 8: kinetic 0, Collapses, ground on,
              notify_on_death (death flag, hit off, attacks cleared); at its end -> 10 (the 3DS's
              create_dead_item(1, 10) on frame p+0x38 (1) is the removal's defeat path here, fix v3)
  9 dead      Damage at rate 0, bullet() (the defeated enemy flies off) and the vl "bullet" attack (state 9: a
              flying body hits); kinetic flag 8 => 10
  10 remove   zima's 0x026D7B58 / 0x026D7B6C (EnemyManager remove_enemy_by_id)
  after damage on the ground 3, in the air / default 1, death 9 (slots 64-67)
Heiho (Shy Guy) 0x0B (vtable 0xCD978-ish, BehaviorHeiho): 1 fall (rising: wait), 2 landing (end: target behind ->
  5, else 4), 3 wait (Wait twice, then 50 %% reverse_lr, -> 4; the search below), 4 walk (the walk energy row,
  kinetic 1, Walk loop, random(60, 120) frames -> 3; a wall -> 6; a ledge (variations 1 / 2) -> 5; every 30
  frames search_target(search 0): face the target, -> 7), 5 turn (end: reverse_lr, => 9 while the run timer
  runs, else => 4), 6 wall hop (kinetic 5, Walk; landed on the same height (p+0x90) or a wall still ahead => 5,
  else => 2), 7 notice (set_kinetic_jump(0, 2.0, 0): two hops in place, RunHold; => 8), 8 hold (row 1 +0x10 frames
  (0), then face the target, -> 9), 9 run (the run energy row, kinetic 3, Run loop, 80 frames -> 12; the contact
  attack (state 9, HEIHO_BUMP); a wall -> 10; a ledge (variations 1 / 2) -> 10; every 30 frames search 1: a
  target behind -> 13), 10 wall run turn (RunTurn, end: reverse_lr => 9), 12 brake (RunBrake, kinetic 2; at its
  end and stopped -> 14), 13 run turn (RunTurn at p+0x78, kinetic 2; end: reverse_lr => 9), 14 settle (kinetic 21,
  Fall; kinetic flag 1 -> 4), 15 dead (DamageStart, bullet, state 15's bullet attack), 16 remove; 4 / 1 / 1 / 15.
Waddle Dee 0x13: 1 fall, 2 parasol fall (variations 0 / 1: start here and after a jump or a ledge), 3 landing
  (-> 4), 4 walk (Walk at p+0x84 (1.2), kinetic 1; every p+0x78 (100) frames p+0x7C %% (50) -> 6 jump; a wall:
  p+0x80 %% (50) -> 6, else -> 5; a ledge (variations 1 / 3) -> 5; off the ground -> 2 (variations 0 / 1) / 1),
  5 turn (end: reverse_lr => 4), 6 jump (kinetic 5, Jump; from the apex -> 2 / 1), 7 dead, 8 remove; 4 / 1 / 1 /
  7. No contact attack: its vl list has only the bullet (state 7).
Waddle Doo 0x19: 1 fall, 2 landing (end: the nearest target behind -> 4, else 3), 3 walk (Walk, kinetic 1; a wall
  -> 5; every 60 frames search_target(search 0) behind -> 4), 4 turn (=> 3), 5 jump (kinetic 5, Jump; landed on
  the same height or a wall ahead => 4, else => 3), 6 dead, 7 remove (the 3DS's 10 / 11: renumbered in fix v8 to
  save the empty rows); 3 / 1 / 1 / 6. No contact attack.
Churine 0x1F: 1 fall, 2 landing (end: unless it came from a hop, the nearest target behind -> 5; else 3), 3 walk
  (initialize again, Walk, kinetic 1; a wall -> 4; a ledge -> 5), 4 jump (initialize, kinetic 5, Jump; landed on
  the same height (row +0x18: 20) or a wall ahead => 5, else => 2), 5 turn (=> 3), 6 dead, 7 remove (the 3DS's
  8 / 9); 3 / 1 / 1 / 6. No contact attack.

Step 2c (docs/smash-run-port.md, "Step 2c"; code in region E):
White Bear 0x40 (create 0x7F420, table 0x111E8C): 1 fall (Fall loop; on the ground => 2), 2 landing (end: the nearest
  target behind -> 5, else 3), 3 walk (kinetic 1, Move loop; V1 = random(60, 120); stick (lr, 0); off the ground
  -> 1; a wall or ledge -> 5; the search counter V0++; a cool-down V2 > 0 counts down and skips the search; when V0
  passes search 1's interval (60): V0 = 0, search_target(group 1) found -> 6; V1 runs out -> 4), 4 special turn
  (SpecialTurn; end: reverse_lr => 3), 5 turn (Turn; same), 6 quake hold (QuakeHold at 1.5, V4 = 0; end -> 7: the
  3DS's is_in_view_area test (CameraModule is_clip_in) is taken as true), 7 quake jump (E+0x20 0, +0x24 / +0x2C
  1.5, +0x28 0, +0x3C 0.1, the kick vt+0xEC (the 3DS's KineticEnergy vt+0x74), kinetic 5, QuakeUp; V5 frames; speed
  y <= 0 -> 8), 8 quake fall (E+0x20 / +0x24 the current speed, +0x28 0, +0x2C 3, +0x3C 1, the kick, kinetic 5,
  QuakeFall; on the ground: V5 < 180 => 9, else => 2), 9 quake landing (kinetic 0, QuakeLanding at 1.0, 0.5 after
  the first; V4++; end: V4 < 3 and a 50 >> (V4 - 1) %% chance -> 7, else V2 = 60 -> 3), 10 dead (DamageStart,
  bullet, P2's bullet attack), 11 remove; 3 / 1 / 1 / 10. Not ported: the landing's camera quake, its absolute
  hit on the first grounded fighter (the bear's only attack: Behavior::hit_attack_absolute with P6, power 10,
  angle 90, bkb 40), its effects 0x7400000 / 0x7400001, set_weak_param(5, 2.0).
Gordo 0x08 (create 0x1A470, table 0x10F55C), variation 0: start (SMODE 1: set_rhombus, set_correct(0), set_lr(0, 1,
  1), no turn to a target), 1 spin (kinetic -1, ground off, Togetoge loop; the contact attack P2 entry 0: power 10,
  angle 65, kbg 50, fkb 50, bkb 100, size 8, node 3), 3 remove; slots 64-67 0 (never defeated: death state 0).
  Not ported: the per-frame energy-0 write steering it back to its spawn point (it holds it with kinetic -1),
  set_test_coll_stop(1), set_invincible_global(0), variations 1-3 (state 2: moving along a line or path).

Step 2c v2: the White Bear's landing (state 9 enter) also does request_quake(6) (0x026A9648), the 3DS's absolute
  hit on the first fighter on the ground (b_quake: MSC StatusModule(1) == 0, then the enemy's AttackModule MSC
  entry vt+0x334 with ops 0x2716 set_abs (ABS_WORDS) and 0x271D hit_absolute(the fighter's object id)) and its two
  effects (request_effect 0x026A951C / 0x026A94CC); Waddle Doo's leave (start: V7 = CFG LEAVE 600; the walk counts it
  down -> state 8: Fall at rate 0, the common leave (energy +0x30 / +0x34, kinetic 15, ground off, set_correct(0),
  effect 0x8000005 following node 0) for 300 frames -> remove); the death / collapse enters set DEFEATED (+0x19C)
  and the notify_on_remove hook gives the defeat path only to those (a leave is removed plainly).

Step 2e (docs/smash-run-port.md, "Step 2e"; region G, code_f): the fliers (FLIERS) Ghos 0x11 and Tiki Buzz 0x0F,
  walker-engine kinds with their own CFG VT / SIZE (0x230: the aerial module at AER 0x1B0) / tread box / handlers:
  VTF = VT but slots 10 / 27 / 41 / 69 (the kind's FDMG / F27 / FSTART / F69, else BehaviorImpl's). Ghos: 1 fly
  (slip homing on the nearest fighter, the wall bounce, 1200-frame leave timer), 2 stun (hit_return_frame), 3 leave,
  4 dead, 5 remove; contact P2 entry 1 in 1. Tiki Buzz: 1 fall, 2 dead, 3 fly (homing extend on fighter 0 + 35,
  search every 30 frames, 900-frame leave), 4 hold, 5 dive (uniform (0, -6); the only hitbox, P2 entry 0), 6 brake,
  7 landed (quake 3), 8 ready, 9 leave, 10 stomped (slot 20 and the stomp test, box (6, 11.72, 1.5)), 11 gone, 12
  remove. Region G is new code space past the old text region (textregion:0x2BC0000, grow:0x04BC0000).

Step 2f (docs/smash-run-port.md, "Step 2f"; region G): Furiijio 0x1A, a flier with its own object size (FU_SIZE) and
  vtable (`vtover`: slots 4 update_on_skip, 61 / 62 kinetic 26) and exit PMFs (a state's third entry): 1 fly (homing
  on the nearest fighter + 25, search every 50 frames after a 150-frame cool-down, 900-frame leave), 2 / 5 charge,
  3 / 6 aim (BeamN turned with set_node_rotate / placed with set_node_translate), 4 / 7 the ice beam (its own hitbox,
  P2 entry 0 / 1, freezing, slid out with AttackModule set_offset; three follow effects scaled / moved; 7 sweeps 180
  degrees), 8 leave, 9 dead, 10 remove. REQ_FOLLOW corrected to 0x026A95F8 (0x026A9584 is REQ_NODE), and the fliers'
  starts call set_rhombus with the Behavior.

Step 2g (docs/smash-run-port.md, "Step 2g"; region G, code_ph): Propeller Heiho 0x47 (PH_SIZE, `vtover` slots 55 /
  59, `dmg_labels`): 4 height, 5 patrol (cosine bob), 6 brake, 1 turn, 2 fly away, 7 stun, 3 dead, 8 remove, with the
  3DS's set_mode_normal / set_max_speed / get_height_from_ground / get_lr_to_nearest_target written over the Wii U's
  aerial module and GroundModule ray_check; it carries an item: the Wii U's Behavior::create_item 0x026A8D78 + the
  item's have(0x50000000) (create_item_and_have), held by Item::warp each frame (slot 59), swapped / dropped
  (Item::fall) in slot 55 and on damage (slot 10), removed with it (slot 27).
Step 2g v4: Ghos's immunity to direct hits (the 3DS's slot 31 0x113F0 / slot 11 0x11094): vt_ghos slot 31 f_g31 (the
  hit's AttackData byte +0x4C -> GH_IMM), slot 10 f_ghos_dmg (immune: DamageModuleImpl::init_damage(GH_DMG) 0x02C212F0,
  no reaction; else GH_DMG = the damage and BehaviorImpl's); Ghos's object GH_SIZE (two more words).

Not ported (the README lists them): the Waddle Doo's beam (states 7 / 8: an article the Wii U has no weapon kind
for) and its leave timer (9) and random hop (6); the Churine's sleep powder (6 / 7: an effect and attack the Wii U
has no data for); the Waddle Dee's parasol float (EnemyAerialModule embedded in the 3DS object: the parasol fall is
a normal fall with the ParasolFall motion); sounds (play_se: the 3DS sound ids); per-state mesh visibility (no
Wii U path: the NUD baseline of fix v4 stands); the Kuribo notice hop's ledge check (check_cliff_distance_lr
with the kind's gl gravity); ray_check (Shy Guy / Doo / Churine hops: check_wall stands in); the variation-indexed
rows of variations 1-3 (the spawner makes variation 0). Values the 3DS reads from a kind's param struct
(EnemyParamAccessor slot [K]) at fixed offsets: the vl groups (+0xC group 0, +0x20 the search groups, +0x34 the
attacks) and an inline part from +0x48 (the kind's own group: Waddle Dee +0x78..+0x84 = 100 / 50 / 50 / 1.2, Shy
Guy +0x78 = 0.7, +0x90 = 1.0 -- inferred from the vl files' order; the Waddle Doo's hop height is a guess, 1.0).

The framework:
- vtable VT: a copy of BehaviorImpl's 0x1008AEBC (GHS: {delta, fn}, slot k's fn at +0xC + 8k) plus 74 / 75;
  overrides: 12 zima's 0x026D6E18 (capture motion), 20 w_tread (stepped on, below), 38 w_noflip (0, fix v3; step 2g v6: 1 for FLIP_TABLE kinds; --keep-flip: zima's `li r3, 1`),
  40 initialize (the kind's 3DS kinetic energy words), 41 start (set_rhombus, +0x10 = posture lr, face the
  nearest target, the kind's first state), 45 set_attack_data (below), 64-67 the kind's states (CFG), 72 / 73
  change_state(id) / the interrupt one (the kind's state table {enter, update, exit} PMFs to 0x026A3A44 /
  0x026A3AD4; unknown ids -> 1); dtor, update, damage / capture / death slots: BehaviorImpl's.
- create(acc, K, variation): operator new 0x03374578(OBJ_SIZE), Behavior ctor 0x02DB2DF0, BehaviorImpl's inline
  init as zima's create 0x026D6680 (+0xE4..: 0, +0xE8 common_state_func 0x102FDBCC, +0x120 = 1, +0x15C = -1), vptr
  VT, +0x168 = the kind's CFG, set_motion_label 0x02DB5B08 (+0xA8 = its script hashsets or 0),
  set_damage_motion_label 0x02DB5AD8 (the 3DS create's nine indices). +0x16C.. the kind's counters (V0-V8, Y0).
- set_attack_data(state) (slot 45; the 3DS kinds use Behavior::set_attack_data, the vl attack list by state):
  AttackModule clear_all 0x02C08324, then each of the kind's {state, InnerEnemyAttackParam} with this state:
  create_attack_data 0x02DB572C(this, entry), +0x84 / +0x88 = entry +4 / +8, set_attack 0x02C086A8(module, id,
  part, this+0x1C). So the contact hitbox is on only in the Kuribo's run (5) and the Shy Guy's run (9), and every
  kind's defeated body carries its bullet attack (as the Wii U's own minions' lists do).
- search_target(group): the 3DS reads the kind's vl search group {type, interval, 5 floats}; the Wii U's
  search_target(int) 0x026A70FC reads the param slot (mczakozima's here), so the cave passes the kind's own group
  to 0x026A70A4 (Behavior::search_target(type, this+0x10, f1..f5) -> EnemyAiModule check_target 0x02DB9F24).
  Others: get_nearest_target 0x026A7008, check_turn_to_target 0x026A6984, get_fighter_pos 0x026A690C,
  check_wall 0x026A68E4, check_cliff 0x026A6E24, clear_speed_all 0x026A67E8, is_current_stopped 0x026A679C,
  get_current_speed 0x026A678C, random_range (an xorshift in the cave).

Stomp (fix v6): a fighter's footstool on an enemy reaches it as Enemy event 6 (the handler the Enemy ctor registers,
0x02D8C450 -> 0x02D8C5D4): behaviour module 0x02DB98F4 -> behaviour slot 20 (fn at vt+0xAC), then the event gets a
param float (acc+0x315C vt+0x44, 0x11) back for the fighter's bounce. Slot 20 is the 3DS's slot 21 (the 3DS vtables
have two destructors: 3DS k = Wii U k + 1 up to slot 28 -- 13 capture motion / 12, 28 notify_on_remove / 27, and
zima overrides exactly this slot with a nop on both). BehaviorImpl's is a nop; the 3DS overrides it in kuribo
(=> 8 collapses), dekakuribo (add_damage(p+0x3C), => 10 / 11), patapata (variations 0 / 1 => 9, else 0x13),
tikibuzz, waddledee (parasol variations: p+0x8C into its parasol timer) and zima (a nop). w_tread => the kind's
CFG TREAD state (Kuribo 8; the other four 0: nothing, as on the 3DS but Waddle Dee's parasol timer, not ported).

Tread area (fix v7): a fighter can only stomp an enemy whose AreaModule area 0 (the tread area, kind 0xE) is on. The
Enemy builds its two areas from its param slot's +0x70 table (2 x {on, node, 4 floats}: 0x02D89860, add_area
0x02BFEA2C) and turns area i off where entry i's word 0 is 0 (0x02D8A24C; 0x02D8FB98 sets area 0 again from entry 0);
no code enables it (Behavior::enable_tread / disable_tread, 0x026A7614 / 0x026A75FC, are only for the few kinds that
switch it). S2 gives the walkers mczakozima's slot, whose table has the tread area off (as all four Fortress
minions'), so nothing could stomp them. The three reads -> area_N: a walker kind gets its own table, its 3DS vl's
last group (Kuribo {1, 2, 14, 8, 0, 0} on, Waddle Dee {1, 0, 10, 2, 0, 12} on; Shy Guy, Waddle Doo, Churine off, as
on the 3DS; area 1 (kind 9) theirs too); other kinds read their slot's as before.

Stomp detection (fix v8; in game the footstool never reached the Goomba even with its tread area on, so the fighter
side doesn't tread on these enemies -- the area set-up itself is the 3DS's, code.bin 0x756EE0: same kinds 0xE / 9,
same flags 0 / 40960.0): slot 3 (update) -> w_upd, then BehaviorImpl's update 0x026A4880. For a kind with a TREAD
state, not in it nor in its death state: each live fighter of slots 0-3 (the fighter table [[0x1035184C]]: entries
0x76B0 apart, +0x1E live >= 4, +0xC accessor, its PostureModule +0x18: x +0x10, y +0x14) whose y went from at / above
the tread box's top last frame (this +0x1A0 + 4 * slot; 0 = no last frame yet) to at / below it now, and not below
its bottom, within its half width -> change_state_interrupt(TREAD) and the fighter's MSC StatusModule(3, 0xB3, 0)
(change status to StepJump, the footstool jump: tools/position_vars_cave.py's way, ctx {0, accessor}). The box: the
Goomba's 3DS area 0 (node 2, 14 x 8, offset 0) as half width 7 around the posture x, centre the posture y + 2.53
(node 2 HipN in the bind pose), half height 4. Approximated: the box is not moved with the animation or the model's
scale, and the fighter's feet are its posture origin (not its ECB); no jump input is needed (a fall onto it does).
Step 2g v3: the test is relative to the enemy (PREV keeps the fighter's y minus the box top, so a rising / sinking
flier is handled) and swept (a crossing of the box top this frame counts down to the box's height + STOMP_SWEEP 4 below
it: a fast fall stepped over Tiki Buzz's 3-unit box); a defeated enemy (+0x19C) is skipped (Tiki Buzz's 11 / 12).

Hooks (2a's three stay as they are):
- F2, the factory 0x02DB94CC after 2a's hook: 0x02DB951C `cmplwi r12, 0x10` -> for the walker kinds
  module+8 = create(module+4, K, variation) then the factory's epilogue 0x02DB96E0; else the instruction and
  0x02DB9520.
- T2, battle load 0x02D9A46C `cmpwi r0, 1` (after 2a's table hook): on a Smash Run stage motion data set table
  0x10352610[K] = K's set.
- S2, the battle's param load 0x02D9A618 `lwz r0, 0x5EC(r28)` (after 2a's slot hook): on a Smash Run stage
  param slot[K] = slot[0x5A] (mczakozima: the activation and accessor set-up read [slot]+0x70 / +0x5C unchecked).

Motion data sets (+0 entries*, +4 count, +8..+0x14 0, the entries {hash, flags} from +0x18): K's 3DS
motion_data_set_<name> in its own order (so the 3DS motion indices hold), hash zlib.crc32(stem, 0xFFFFFFFF), flags
the 3DS word >> 16. Script hashsets (Kuribo, Shy Guy, Churine): crc32(lower(name) + ".init" / "" / ".exit").

Fix v3 (every Smash Run kind < 0x50, 2a's twins included):
- slot 38: the walker's returns 0, and the twins' (vtable words 0x1008FFCC zima, 0x1008F1D4 plasmawisp,
  0x1008EC68 darios) -> twin_flip: 1 for kinds >= 0x50, 0 below; their ADDR32 relocations moved to RELOC_DUMMY
  0x037EE73C. `--keep-flip` builds without it.
- initialize_after 0x02DB4AC8, 0x02DB4B20 `lwz r10, 0(r31)` -> for kinds < 0x50 set_lr(posture lr, 1, 1).
- notify_on_remove 0x02DB40E4 `mflr r0` -> for kinds < 0x50 type 0 becomes 3 (the defeat effect path 0x02DB3AB0).
- step 2g v3: slots 49 / 50 (set_lr / reverse_lr) -> w_slr / w_rlr (the game's, then w_yaw) in the cave's vtables and
  the twins' (TWIN_LR, relocations moved to RELOC_DUMMY): the 3DS-flip kinds (YAW_FLIP; from step 2g v6 only YAW_HOLD,
  the ones without a model.flp: the others flip for real, slot 38 = 1) keep yaw -90 at lr 1, their
  camera-facing lr -1 view, which the 3DS mirrors for lr 1 (lr 1 showed their backs: the "sometimes facing away" spawns).

Space: 0x04B86800-0x04B88000 (kind_expand.py's old space after smashrun_enemy_cave.py), 0x04B89000-0x04B8A000
(free between base_effects_cave.py and base_customs_cave.py) and 0x04BB8000-0x04BB8660 (the grown text after
weapon_expand.py, up to the text region's end 0x04BB8670; grow:0x04BB8660). Code in the first two and the area hooks
at the start of the third (with the stomp test's body), the stomp hook's frame in the fourth (fix v8: 0x04B84900-
0x04B84A00, zero and unclaimed between stage_omega_cave.py's LIMIT and boot_training_cave.py's CAVE, no branch, word
or lis / addi pair in the executable pointing into it), data after them (largest blocks first). To fit fix v7, state tables start at row 1 (id 0 -> 1 in change_state) and
P has five words.
"""
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm, ha, lo  # noqa: E402
import smashrun_field_cave as F  # noqa: E402

CAVE, LIMIT = 0x04B86800, 0x04B88000
CAVE_B, LIMIT_B = 0x04B89000, 0x04B8A000
CAVE_C, LIMIT_C = 0x04BB8000, 0x04BB8660
CAVE_D, LIMIT_D = 0x04B84900, 0x04B84A00    # fix v8: free between stage_omega_cave.py and boot_training_cave.py
# step 2c: Smash Run's own unused space (zero and unreferenced in exe_v12, checked): the field cave's tail before its
# DATA (its code ends 0x04B7D430; F.CODE_LIMIT keeps it below CAVE_E), smashrun_enemy_cave.py's gaps (code to
# 0x04B8597C, sets to 0x04B8621C) and the old .text end before position_vars_cave.py's 0x04B78000
CAVE_E, LIMIT_E = 0x04B7D600, 0x04B7DF00    # code, then data
DATA_F = ((0x04B85980, 0x04B85C00), (0x04B86220, 0x04B86800), (0x04B77E20, 0x04B78000))     # data only
# step 2e: the fliers' code and data, in new code space after the text region's old end 0x04BB8670 (the RPL file
# info's textRegionSize raised to TEXT_REGION, the text section grown to LIMIT_G: nothing there in exe_v15)
CAVE_G, LIMIT_G = 0x04BB8680, 0x04BC0000
TEXT_REGION = LIMIT_G - 0x02000000
REGIONS = ((CAVE, LIMIT), (CAVE_B, LIMIT_B), (CAVE_C, LIMIT_C), (CAVE_D, LIMIT_D), (CAVE_E, LIMIT_E),
           (CAVE_G, LIMIT_G)) + DATA_F
GROW = LIMIT_G

# the framework (docs/smash-run-port.md, Step 2b / Fix v5)
OPNEW = 0x03374578
BEH_CTOR = 0x02DB2DF0
SET_MOTION_LABEL = 0x02DB5B08
SET_DAMAGE_LABEL = 0x02DB5AD8
CHANGE_MOTION = 0x02DB420C
BULLET = 0x02DB5158
CHANGE_KINETIC = 0x02DBE00C          # EnemyKineticModule (acc+0x30E8)
SET_ATTACH_GROUND = 0x02C37C6C       # GroundModule (acc+0x30DC)
IS_TOUCH = 0x02C38A24                # GroundModule; 8 = on the ground, 2 / 4 = wall left / right
MOTION_IS_END = 0x02C5F114           # MotionModule (acc+0x30F0)
ATK_CLEAR = 0x02C08324               # AttackModule (acc+0x30C8) clear_all
ATK_CREATE = 0x02DB572C              # Behavior::create_attack_data(InnerEnemyAttackParam const&)
ATK_SET = 0x02C086A8                 # AttackModule set_attack(id, part, AttackData&)
SET_RHOMBUS = 0x026A65BC
NEAREST = 0x026A7008                 # get_nearest_target() -> id / -1
CHECK_TURN = 0x026A6984              # check_turn_to_target(id, f1 distance)
CHECK_WALL = 0x026A68E4              # check_wall()
CHECK_CLIFF_LR = 0x026A6D88          # check_cliff with lr f1 (check_cliff_distance_lr by the speed)
CHECK_CLIFF = 0x026A6E24             # check_cliff(): the posture lr -> CHECK_CLIFF_LR
SEARCH = 0x026A70A4                  # search_target(type r4, &vec r5, f1..f5) -> check_target 0x02DB9F24
GET_TARGET_POS = 0x026A690C          # (out, this, id): get_fighter_pos (own position for id < 0)
GET_SPEED = 0x026A678C               # get_current_speed (out, this): get_sum_speed3f(1)
IS_STOPPED = 0x026A679C              # is_current_stopped(): |speed x| < 0.05
CLEAR_SPEED = 0x026A67E8             # clear_speed_all()
CHG_BASE = 0x026A3A44                # change_state_base(id, &update, &enter, &exit) (deferred)
CHG_INT = 0x026A3AD4                 # change_state_interrupt_base (now)
SET_CORRECT = 0x02C36458             # GroundModule set_correct(kind) (the twins' calls with 0 / 5)
# v2: Behavior helpers found on the Wii U (each the 3DS function's twin: the same module calls)
REQ_QUAKE = 0x026A9648               # request_quake(kind): CameraModule (acc+0x30CC) vt+0x1CC (3DS 0x7B0F0C)
REQ_EFFECT = 0x026A951C              # request_effect(id, &pos, &rot (degrees), scale) (3DS 0x7B12E0)
REQ_EFFECT0 = 0x026A94CC             # request_effect(id, &pos, scale) (3DS 0x7B1338)
REQ_FOLLOW = 0x026A95F8              # request_follow_effect(id, node, &offset, &rot, scale) -> handle (3DS 0x7B4AEC:
#                                      EffectModule req_follow 0x02C2AF98, the 3DS's 14-argument shape; step 2f)
REQ_NODE = 0x026A9584                # request_effect(id, node, &offset, &rot, scale) (3DS 0x7B1384: EffectModule req
#                                      on a node, the vtable slot after req(pos), as on the 3DS; not a follow: steps
#                                      2c-2e called this one as REQ_FOLLOW)
REMOVE_EFFECT = 0x026A95E4           # remove_effect(handle) (3DS 0x7B0EF0)
QUAKE_KIND = 6                       # the 3DS bear's request_quake(7); 6 is the largest any Wii U enemy asks for
NOTIFY_DEATH = 0x0269FD6C            # BehaviorImpl::notify_on_death (slot 71: death flag, hit off, attacks cleared)
# fix v7: the sites reading [param slot]+0x70 (the area table): (site, word, dst, base, the kind's register, kind * 4)
AREA_SITES = ((0x02D89898, 0x81450070, 10, 5, 0, True),       # the Enemy's area set-up: add_area(2 areas)
              (0x02D8A24C, 0x834C0070, 26, 12, 0, False),     # activation: area i off where entry i's word 0 == 0
              (0x02D8FB98, 0x810A0070, 8, 10, 0, True))       # area 0 (tread) on / off again by entry 0
TREAD_SLOT = 20                      # the 3DS's slot 21 (stepped on): Enemy event 6 -> module 0x02DB98F4 -> it
COMMON_PMF = 0x102FDBCC              # BehaviorImpl::common_state_func
BI_VT = 0x1008AEBC
ZIMA_CAPTURE_MOTION = 0x026D6E18     # slot 12
ZIMA_ONE = 0x026D7C98                # li r3, 1
ZIMA_REMOVE_ENTER = 0x026D7B58
ZIMA_REMOVE_UPDATE = 0x026D7B6C
SLOT_DONOR = 0x5A                    # mczakozima

MOTION_SETS = 0x10352610
PARAM_MGR = 0x102F6C00
SLOTS = 0x60

SITE_F, WORD_F = 0x02DB951C, 0x280C0010      # cmplwi r12, 0x10
FACTORY_NEXT, FACTORY_END = 0x02DB9520, 0x02DB96E0
SITE_T, WORD_T = 0x02D9A46C, 0x2C000001      # cmpwi r0, 1
SITE_S, WORD_S = 0x02D9A618, 0x801C05EC      # lwz r0, 0x5EC(r28)
# fix v3 (enemy-wide, for the Smash Run kinds < 0x50: 2a's four and the walkers)
SITE_ROT, WORD_ROT = 0x02DB4B20, 0x815F0000  # initialize_after: lwz r10, 0(r31)
SITE_DEATH, WORD_DEATH = 0x02DB40E4, 0x7C0802A6   # notify_on_remove: mflr r0
# ---- step 2e: the fliers (the Wii U's EnemyAerialModuleImpl, as mczakoplasmawisp embeds it; 3DS names / addresses)
AER = 0x1B0                          # the aerial module in a flier (0x74 bytes; the 3DS behaviours' +0x168)
FL_SIZE = 0x230                      # a flier object: the walker's 0x1B0, the aerial module, 3 words
AER_CTOR = 0x02DB2C44                # EnemyAerialModuleImpl(acc) (3DS 0x5F6BAC): +0 acc, +4 / +8 energies, mode -1
AER_UPDATE = 0x02DB28C8              # update() -> update(1.0, 1.0, true) 0x02DB2524 (3DS 0x5F6B80 / 0x5F66AC)
AER_SLIP_HOMING = 0x02DB28E4         # set_mode_slip_homing(f1-f6) (3DS 0x5F5F58: mode 2, params +0x10..+0x24)
AER_SLIP_HOMING_EXT = 0x02DB2A48     # set_mode_slip_homing_extend (3DS 0x5F64FC: slip homing, then mode 3)
AER_SET_SPEED = 0x02DB2BC0           # set_current_speed(Vector2&) (3DS 0x5F5C58): energy 0's speed x / y
GROUND_NORMAL = 0x02D64ABC           # GroundCollisionObject::get_ground_normal(mask) -> (r3, r4) = (x, y) bits
#                                      (3DS 0x96A538; the GroundModule's +0x18, as is_touch 0x02C38A24 reads it)
SET_PASSABLE = 0x02C367C4            # GroundModule set_passable_check(bool) (3DS 0x4E1B84)
SQRTF = 0x04ADEAB8                   # sqrtf (get_distance 0x02DB2C08 tail-calls it)
HIT_FACTOR = 0x02DB4ED4              # the 3DS's 0x9EB4C0 (hit_return_frame's factor: gl +0x158..+0x164, the
#                                      DamageModule (acc+0x30D4) float +0x6C through 0x026A81F8)
BI_NOTIFY_DMG = 0x026A3564           # BehaviorImpl::notify_on_damage (slot 10; the 3DS's slot 11)
# step 2g v4: Ghos's immunity (3DS slot 31 0x113F0 / slot 11 0x11094). The Wii U's slot 31 is the 3DS's: BehaviorImpl's
# 0x026A48EC (BI_VT +0x104) reads the hit record exactly as the 3DS's 0x3DD654 (r4 the hit: +0x14 AttackData, its
# byte +0x4C -> this +0x160; +0x20 the attacker record, byte +0x27 -> +0x15C); the EnemyBehaviorModule (acc+0x30EC,
# vtable 0x10122340) calls it through its +0xF4 entry 0x02DB9988 (Behavior +0xE0 vtable +0x104)
INIT_DAMAGE = 0x02C212F0             # DamageModuleImpl::init_damage(float) (3DS 0x4D30BC: every entry (Wii U 0xE4
#                                      bytes at [+0xC], [+8] of them; 3DS 0xE0) +0 = f, +4 / +8 / +0xC4 = 0, +0xD4 0)
GH_IMM, GH_DMG = FL_SIZE, FL_SIZE + 4    # Ghos's 3DS +0x1F4 (immune this hit) / +0x1F8 (the damage to restore)
GH_SIZE = FL_SIZE + 8
# step 2f (Furiijio; docs/smash-run-port.md "Step 2f")
CENTER_POS = 0x026A7104              # Behavior::center_pos (out, this): ModelModule node_global_position(center_node)
SET_NODE_ROT = 0x02C64188            # MotionModule set_node_rotate(node, &rad, compose) (3DS 0x501328) -> changed
SET_NODE_TRANS = 0x02C642C8          # MotionModule set_node_translate(node, &v, global, b) (3DS 0x501954)
MODEL_NODE_DIRTY = 0xC4              # the ModelModule (acc+0x3118) vt slot both callers make after a change (3DS +0x60)
ATK_SET_OFFSET = 0x02C09150          # AttackModule set_offset(id, &v) (3DS 0x4CB8B8; entries 0x84, +0x6C on)
EFF_SET_POS = 0x02C2C0C0             # EffectModule set_pos(handle, &v) (3DS 0x4DAF8C; EffectSystem 0x032F0978)
EFF_SET_SCALE = 0x02C2C120           # EffectModule set_scale(handle, &v) (3DS 0x4DB438; EffectSystem 0x032F0A48)
SINF, COSF, ACOSF = 0x04ADEB48, 0x04ADF434, 0x04ADF800      # libm (identified by running them; acosf: calc_angle's)
FU = 0x230                           # Furiijio's own fields after the flier's (object FU_SIZE)
FU_C, FU_ROT, FU_E = FU, FU + 0xC, FU + 0x18                 # center offset (3DS +0x218), node angles (+0x224), effects
FU_SIZE = FU + 0x28
# step 2g (Propeller Heiho; docs/smash-run-port.md "Step 2g"): the Wii U's item calls and the helpers it was missing
CREATE_ITEM = 0x026A8D78             # Behavior::create_item(kind, var, &pos, &rot, bool) -> Item* (3DS 0x7B214C: init_normal
#                                      0x030519B4 + ItemManager::create_item 0x0305542C); create_item_and_have 0x7B4104
#                                      itself is gone on the Wii U (no caller): the cave does its two item calls
ITEM_MGR = 0x102F9B30                # [ITEM_MGR] = the ItemManager (lib::Singleton<app::ItemManager>::instance_)
FIND_ITEM = 0x030563AC               # ItemManager::find_item(id) -> Item* / 0 (3DS 0x3CD464; Item +0 id, +4 kind)
ITEM_WARP = 0x0303207C               # Item::warp(Vector3 const&) (3DS 0x74E174)
ITEM_FALL = 0x03032D78               # Item::fall(float, Vector3 const&) (3DS 0x74D6E4; ItemModule drop / throw call it)
IT_VT, IT_REMOVE, IT_ID, IT_HAVE = 0x24, 0x28C, 0x29C, 0x2FC   # the Item's vtable (+0x24; entries 8 bytes) slots 81
#                                      (remove(bool): +0x3B6E = 1), 83 (id), 95 (have(owner, ...)): the 3DS's
#                                      vt+0x144 / +0x14C / +0x17C (the same slot numbers)
NODE_GPOS = 0x0200739C               # ModelModule node_global_position(node, &v, bool) (acc+0x3118; 3DS 0x4A8xxx via
#                                      acc+0x3098, as center_pos 0x026A7104 calls it)
RAY_CHECK = 0x02C39F18               # GroundModule ray_check(V2 const& from, V2 const& dir, V2& out, bool) (3DS 0x9535F4)
IN_VIEW = 0x026A96BC                 # Behavior::is_in_view_area() (3DS 0x9EA804: CameraModule (acc+0x30CC) is_clip_in(1)
#                                      0x02C15EB8, the 3DS's 0x950DDC)
SUCCESS_PCT = 0x026A8618             # Behavior::success_by_percent(f1) (3DS 0x7B3BC4: the game's Randomizer < f1 x 0.01)
DAMAGE_TURN = 0x02DB4E84             # Behavior::damage_turn() (3DS 0x7B0814: DamageModule +0x98 lr != posture lr -> turn)
AER_UPDATE_XY = 0x02DB2524           # EnemyAerialModuleImpl::update(f1 x, f2 y, r4 brake) (3DS 0x5F66AC)
PH = 0x230                           # Propeller Heiho's own fields after the flier's (3DS +0x1DC..+0x20C)
PH_D, PH_B, PH_Y, PH_F, PH_T, PH_A, PH_R, PH_S, PH_DT, PH_I, PH_X = (PH + 4 * i for i in range(11))
PH_SIZE = PH + 0x2C
ITEM_NONE = 0x50000000
PH_FOOD, PH_GOLDBAG, PH_CUSTOM = 0x0E, 0x1D, 0x21  # tabemono (29 variations), goldbag, customizeitem (both games' tables)
PH_SWAP_FX = 0x100001C               # the item swap's effect (3DS: the item's EffectModule req, common effect 0x1C)
GL_INDEX, GL_BASE = 0x1E4, 0x34      # gl entry = [[PARAM_MGR] + 0x34] + 0x228 * [[PARAM_MGR] + 0x1E4 + 4 * (8K + var)]
VT_WORDS = [None]                    # BehaviorImpl's vtable words (read from the input), for code_f
TWIN_FLIP = ((0x1008FFCC, 0x026D7C98), (0x1008F1D4, 0x026D19F4), (0x1008EC68, 0x026CF200))
# step 2g v3: the kinds whose 3DS behaviour flips the model (slot 38 = is_flip_model returns 1: MotionModuleImpl::set_flip(lr
# == 1) in Behavior::set_lr 0x7B5778 / reverse_lr 0x7B034C; reference/smashrun_enemy_specs: kuribo, waddledee, waddledoo,
# churine, zima, plasmawisp, darios, tikibuzz, furiijio, propellerheiho; not heiho, stalfos, whitebear, gordo, ghos).
# Their models face the camera at lr -1 (yaw -90) and the 3DS shows lr +1 as that view mirrored; without the mirror
# (no Wii U flip table: fix v3) lr +1's yaw +90 showed their backs. w_yaw keeps yaw -90 for lr +1 (the mirror's front).
YAW_FLIP = (0x01, 0x13, 0x19, 0x1F, 0x0E, 0x12, 0x1D, 0x0F, 0x1A, 0x47)
# step 2g v6: the real flip. The converted models now carry the 3DS model.flp as the Wii U's (tools/s3ds_enemy.py
# flp_bytes), so slot 38 returns 1 for the YAW_FLIP kinds that have one (FLIP_TABLE: the game's own set_lr 0x026A780C /
# reverse_lr 0x026A7A20 then call MotionModule 0x02C6108C(lr == 1, 1), the 3DS's set_flip(lr == 1, 1), and the anim
# mirror 0x036C48B0 mirrors the skeleton) and they keep lr x 90 (no yaw hold). Churine and Propeller Heiho flip on the
# 3DS but have no model.flp in either game (nothing to mirror): they keep the step 2g v3 yaw hold (YAW_HOLD).
FLIP_TABLE = (0x01, 0x13, 0x19, 0x0E, 0x12, 0x1D, 0x0F, 0x1A)
YAW_HOLD = tuple(k for k in YAW_FLIP if k not in FLIP_TABLE)
SET_LR, REVERSE_LR = 0x026A780C, 0x026A7A20
# the twins' vtables (2a's zima / plasmawisp / darios use them): slots 49 / 50 -> w_slr / w_rlr (kinds >= 0x50 unchanged)
TWIN_LR = tuple((w - 0x13C + 0xC + 8 * k, orig, lab) for w, _f in TWIN_FLIP
                for k, orig, lab in ((49, SET_LR, 'w_slr'), (50, REVERSE_LR, 'w_rlr')))


def yaw_mask(kinds=None):
    m = [0, 0, 0]
    for k in YAW_HOLD if kinds is None else kinds:
        m[k >> 5] |= 1 << (k & 31)
    return m
RELOC_DUMMY = 0x037EE73C
SET_LR_SLOT = 49
KEEP_FLIP = False    # True: the variant that keeps the motion flip (only the rotation and death fixes)

OBJ_SIZE = 0x1B0                     # BehaviorImpl 0x168, +0x168 CFG*, +0x16C V0..V8, +0x190 Y0, +0x1A0 PREV


def V(i):
    return 0x16C + 4 * i


Y0 = 0x190
DEFEATED = 0x19C                     # v2: set by the death / collapse enters: the removal plays the defeat path
PREV = 0x1A0                         # fix v8: each fighter slot's (0-3) y last frame (0 = none yet)
FIGHTERS = 0x1035184C                # [[FIGHTERS]]: +0 entries, +8 count; entry 0x76B0: +0x1E live >= 4, +0xC acc
FIGHTER_ENTRY = 0x76B0
MSC_STATUS = 0x030B2B98              # MSC StatusModule wrapper (ctx {0, accessor}, args {words*, count})
STEP_JUMP = 0xB3                     # fighter status StepJump (the footstool jump off an opponent)
BI_UPDATE = 0x026A4880               # BehaviorImpl::update (slot 3): the state's update PMF
# the Goomba's tread area (its 3DS area 0: node 2, 14 x 8, offset 0): half width, centre above the posture
# (node 2 HipN 2.53 in its bind pose), half height
TREAD_BOX = (7.0, 2.53, 4.0)
# step 2g v3: the stomp test is relative to the enemy (PREV keeps the fighter's y minus the box top) and swept: a
# crossing of the box top this frame counts down to the box's height + STOMP_SWEEP below it (a fast fall, 3.4 a
# frame at most, plus a rising flier, did step over Tiki Buzz's 3-unit box); dying / defeated enemies (+0x19C) skip
STOMP_SWEEP = 4.0
SLOT = {50: 0xC + 8 * 50, 72: 0xC + 8 * 72, 73: 0xC + 8 * 73}     # reverse_lr, change_state, interrupt

# CFG (per kind)
CF = {}
for _i, _n in enumerate(('KIND NST TAB START START01 R64 R65 R66 R67 REMOVE DEADMOT HASH EN ENN KICK SET ATK SRCH '
                         'FALLMOT LANDST LANDMOT TURNMOT TURNST WALKST HOPTHR HOPLAND HOPFLAG HOPMOT HOPLOOP ZERO TREAD AREA '
                         'SMODE LEAVE VT SIZE TB0 TB1 TB2 FSTART FDMG F69 F27 LVP TNODE').split()):
    CF[_n] = 4 * _i
CF['DMG'] = 4 * len(CF)              # 9 words
CF['P'] = CF['DMG'] + 4 * 9          # the kind's own values P0.. (at least five words)
CFG_SIZE = CF['P'] + 4 * 5          # the walkers' (step 2c kinds have more P words: cfg_size())


def P(i):
    return CF['P'] + 4 * i


# InnerEnemyAttackParam (fs vl, 42 values; create_attack_data: +0xC node, +0x10 power, +0x14 angle, +0x18 kbg,
# +0x1C fkb, +0x20 bkb, +0x24 size, +0x28.. offset): the 3DS vl attack lists
KURIBO_BUMP = (5, 0, 0, 4, 1, 100, 100, 80, 0, 3, -1.0, 0.0, 0.0, 0, 0.0, 1.0, 1.0, 0, 0, 1, 0, 2, 3, 1, 2, 1, 0,
               9, 0, 1, 0, 0, 60, 0, 0, 1, 0, 0, 0, 0, 0, 0)
HEIHO_BUMP = (9, 0, 0, 0, 1, 50, 100, 60, 0, 4, 0.0, 8.0, 1.0, 0, 0.0, 1.0, 3.0, 0, 0, 1, 0, 1, 3, 1, 0, 1, 0,
              9, 0, 1, 0, 0, 4, 0, 0, 1, 0, 0, 0, 0, 0, 0)
# the defeated body's attack (Kuribo's; Waddle Dee's and Waddle Doo's are the same but for the state word, which
# create_attack_data does not read: the list holds the state)
BULLET_ATK = (9, 0, 0, 2, 2, 361, 100, 0, 50, 3, 0.0, 0.0, 0.0, 0, 0.0, 2.0, 1.0, 0, 0, 0, 2, 1, 3, 0, 2, 2, 0, 9,
              0, 0, 0, 0, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0)
HEIHO_BULLET = (15, 0, 0, 2, 2, 361, 100, 0, 50, 2, 0.0, 0.0, 0.0, 0, 0.0, 2.0, 1.0, 0, 0, 0, 2, 1, 3, 0, 0, 2, 0,
                9, 0, 0, 0, 0, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0)
CHURINE_BULLET = (8, 0, 0, 2, 1, 361, 100, 0, 50, 3, 0.0, 0.0, 0.0, 0, 0.0, 2.0, 1.0, 0, 0, 0, 2, 1, 3, 0, 2, 2, 0,
                  9, 0, 0, 0, 0, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0)
# step 2c (the vl files' P2 entries, typed as in the files): Gordo's spikes (states 1 and 2: the same entry but for
# the state word), the White Bear's defeated body (state 10)
GORDO_SPIKE = (1, 0, 0, 3, 10, 65, 50, 50, 100, 8, 0.0, 0.0, 0.0, 2, 0.0, 2.0, 1.0, 0, 0, 0, 2, 3, 7, 1, 2, 3, 0, 9,
               0, 0, 0, 0, 60, 0, 0, 0, 0, 1, 0, 0, 0, 0)
WHITEBEAR_BULLET = (10, 0, 0, 2, 8, 361, 100, 0, 50, 5, 0.0, 0.0, 0.0, 0, 0.0, 2.0, 1.0, 0, 0, 0, 2, 1, 3, 0, 0, 2, 0,
                    9, 0, 0, 0, 0, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0)
# v2: the White Bear's landing quake as an absolute attack: the AttackModule MSC op 0x2716 (set_abs) words in
# Throw_Specifier's order (kind, part, damage, angle, kbg, wbkb, bkb, effect, trip, hitlag, sdi, sfx level, sfx type,
# facing, disable hitlag, no reaction, type) from its vl P6 (InnerEnemyAttackAbsoluteParam {state 9, id 0, part 0,
# power 10, angle 90, kbg 100, fkb 0, bkb 40, 0, 1.0, 1.0, 1.0, 2, 1, 0, 0, 1, 0}; the 3DS struct's bytes / the
# three floats mapped by their order: effect 0, hitlag 1.0, sdi 1.0, sound level 2, sound type 1, facing 3 (the
# Wii U throws' default), no reaction 0, type 0)
ABS_WORDS = (0x2716, 0, 0, 10.0, 90, 100, 0, 40, 0, 0.0, 1.0, 1.0, 2, 1, 3, 0, 0, 0)
SPECS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reference', 'smashrun_enemy_specs')


def vl_group(kind, index):
    """the kind's fs vl group `index` (its entries, typed as in the file: floats stay floats), from the generated
    spec (reference/smashrun_enemy_specs/<kind>.json, read from the 3DS param files)"""
    import json
    with open(os.path.join(SPECS, kind + '.json')) as f:
        members = json.load(f)['params']['members']
    if index == 'struct':
        return [m for m in members if m['type'] == 'struct'][0]['values'][0]
    return [m for m in members if m.get('index') == index][0]['values']


# step 2e: the fliers' vl P2 entries (the 3DS files' words)
GHOS_BODY = tuple(vl_group('ghos', 2)[1])          # state 1 (fly): power 3, angle 361, kbg 50, bkb 50, size 8, node 3
GHOS_BULLET = tuple(vl_group('ghos', 2)[0])        # state 4 (dead): power 3, angle 361, kbg 100, bkb 50, size 8
TIKI_DIVE = tuple(vl_group('tikibuzz', 2)[0])      # state 5 (dive): power 2, angle 60, kbg 120, fkb 50, size 4, y -1
TIKI_BULLET = tuple(vl_group('tikibuzz', 2)[1])    # state 2 (dead): power 2, angle 361, kbg 100, bkb 50, size 3
FU_BEAM0 = tuple(vl_group('furiijio', 2)[0])     # state 4 (beam): power 4, angle 361, kbg 100, fkb 100, size 2, node 3
FU_BEAM1 = tuple(vl_group('furiijio', 2)[1])     # state 7 (sweep beam): the same but +0x7C 140 (60 in entry 0)
FU_BULLET = tuple(vl_group('furiijio', 2)[2])    # state 9 (dead): power 3, angle 361, kbg 100, bkb 50, size 3, node 2
PH_BULLET = tuple(vl_group('propellerheiho', 2)[0])  # state 3 (dead): power 2, angle 361, kbg 100, bkb 50, size 2, node 2
ATTACKS = {'ph_bullet': PH_BULLET, 'fu_beam0': FU_BEAM0, 'fu_beam1': FU_BEAM1, 'fu_bullet': FU_BULLET, 'ghos_body': GHOS_BODY, 'ghos_bullet': GHOS_BULLET, 'tiki_dive': TIKI_DIVE, 'tiki_bullet': TIKI_BULLET, 'kuribo_bump': KURIBO_BUMP, 'heiho_bump': HEIHO_BUMP, 'bullet': BULLET_ATK, 'heiho_bullet': HEIHO_BULLET,
           'churine_bullet': CHURINE_BULLET, 'gordo_spike': GORDO_SPIKE, 'whitebear_bullet': WHITEBEAR_BULLET}
DAMAGE_LABELS = ('DamageStart', 'DamageFly', 'DamageFall', 'DownBound', 'DownBound', 'DownLoop', 'DownBoundEnd',
                 'DownWait')

# kinds (index in the name table 0x1041A22C). motions: the 3DS motion_data_set_<name> order (name, Wii U flags).
# energy: {offset: value} of the kind's 3DS initialize (variation 0); kick: it calls the kinetic module's vt
# (0x20000004). states: {3DS id: (enter, update)} (labels of this file, or game addresses). search: the vl search
# groups {type, interval, 5 floats}. attacks: (state, attack). P: the kind's own values (P0..).
WALKERS = (
    dict(name='kuribo', areas=((1, 2, 14.0, 8.0, 0.0, 0.0), (1, 2, 10.0, 12.0, 0.0, 0.0)), kind=0x01,
         motions=(('Collapses', 1), ('Damage', 1), ('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1),
                  ('DownBound', 1), ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1), ('Fall', 1),
                  ('Landing', 1), ('RunBrakeL', 1), ('RunHoldL', 1), ('RunL', 5), ('RunTurnL', 1), ('WalkL', 5)),
         dead='Damage', last='Fall', hashset=True, kick=True,
         energy={8: 2.0, 0xC: 1.5, 0x10: 0.02, 0x14: 0.001, 0x18: 0.01, 0x20: -0.4, 0x24: 1.6, 0x2C: 5.0,
                 0x40: 1.0, 0x44: 0.8},
         states={1: ('g_fall_en', 'g_fall_up'), 2: ('g_land_en', 'g_land_up'), 3: ('k_walk_en', 'k_walk_up'),
                 4: ('k_ntc_en', 'k_ntc_up'), 5: ('k_run_en', 'k_run_up'), 6: ('k_brk_en', 'k_brk_up'),
                 7: ('k_rt_en', 'k_rt_up'), 8: ('k_col_en', 'k_col_up'), 9: ('g_dead_en', 'g_dead_up'),
                 10: 'remove'},
         tread=8,
         start=(1, 1), rets=(3, 1, 1, 9), remove=10, fall=('Fall', 2), landing='Landing', turn=None, turnst=0,
         walkst=3, hop=(0.0, 0, 0),
         search=((2, 100, 100.0, 40.0, 10.0, 10.0, 0.0), (2, 60, 150.0, 60.0, 0.0, 10.0, 0.0)),
         attacks=((5, 'kuribo_bump'), (9, 'bullet')),
         P=(0.6, -0.4, 1.0, 30, 110)),      # walk rate, hop x, run rate, notice frames, run frames
    dict(name='heiho', areas=((0, 0, 1.0, 1.0, 0.0, 0.0), (1, 2, 6.0, 10.0, 0.0, 0.0)), kind=0x0B,
         motions=(('Damage', 1), ('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1),
                  ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1), ('Fall', 1), ('Landing', 1), ('Run', 1),
                  ('RunBrake', 5), ('RunHold', 1), ('RunTurn', 1), ('Turn', 1), ('Wait', 1), ('Walk', 1)),
         dead='DamageStart', last='Fall', hashset=True, kick=True,
         energy={8: 0.3, 0xC: 10.0, 0x10: 0.3, 0x14: 0.0, 0x18: 0.0, 0x20: 0.5, 0x24: 2.5, 0x28: 0.5, 0x2C: 2.5,
                 0x40: 1.0},
         states={1: ('g_fall_en', 'g_fall_up'), 2: ('g_land_en', 'g_landt_up'), 3: ('h_wait_en', 'h_wait_up'),
                 4: ('h_walk_en', 'h_walk_up'), 5: ('g_turn_en', 'h_turn_up'), 6: ('g_hop_en', 'g_hop_up'),
                 7: ('h_ntc_en', 'h_ntc_up'), 8: ('h_hold_en', 'h_hold_up'), 9: ('h_run_en', 'h_run_up'),
                 10: ('h_wrt_en', 'h_wrt_up'), 12: ('h_brk_en', 'h_brk_up'), 13: ('h_rt_en', 'h_rt_up'),
                 14: ('h_set_en', 'h_set_up'), 15: ('g_dead_en', 'g_dead_up'), 16: 'remove'},
         start=(1, 1), rets=(4, 1, 1, 15), remove=16, fall=('Fall', 2), landing='Landing', turn='Turn', turnst=5,
         walkst=4, hop=(1.0, 2, 0), hop_motion=('Walk', 1),
         search=((2, 30, 120.0, 40.0, 10.0, 10.0, 0.0), (2, 30, 150.0, 36.0, 0.0, 12.0, 0.0)),
         attacks=((9, 'heiho_bump'), (15, 'heiho_bullet')),
         # walk frames min / max, hold frames (row 1 +0x10), run frames (row 2 +0x10), run turn rate (+0x78)
         P=(60, 120, 0, 80, 0.7),
         rows={'walk': {0x10: 0.3, 8: 0.3, 0x14: 0.0, 0x20: 0.5, 0x24: 2.5, 0x28: 0.5, 0x2C: 2.5},
               'run': {0x10: 0.8, 8: 0.8, 0x14: 0.0075, 0x20: 0.5, 0x24: 2.5, 0x28: 0.5, 0x2C: 2.5},
               'jump': {0x20: 0.0, 0x28: 0.0, 0x24: 2.0, 0x2C: 2.0, 0x1C: 0.0}}),
    dict(name='waddledee', areas=((1, 0, 10.0, 2.0, 0.0, 12.0), (1, 2, 10.0, 10.0, 0.0, 0.0)), kind=0x13,
         motions=(('Damage', 1), ('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1),
                  ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1), ('Fall', 1), ('Jump', 0x40),
                  ('Landing', 1), ('ParasolFall', 1), ('Turn', 1), ('Walk', 1)),
         dead='Damage', last='Jump', hashset=False, kick=False,
         energy={8: 0.2, 0x10: 0.2, 0x18: 0.0005, 0x20: 0.3, 0x24: 2.5, 0x28: 0.3, 0x2C: 2.5, 0x44: 1.0},
         states={1: ('g_fall_en', 'g_fall_up'), 2: ('d_para_en', 'g_fall_up'), 3: ('g_land_en', 'g_land_up'),
                 4: ('d_walk_en', 'd_walk_up'), 5: ('g_turn_en', 'g_turn_up'), 6: ('d_jump_en', 'd_jump_up'),
                 7: ('g_dead_en', 'g_dead_up'), 8: 'remove'},
         start=(1, 2), rets=(4, 1, 1, 7), remove=8, fall=('Fall', 3), landing='Landing', turn='Turn', turnst=5,
         walkst=4, hop=(0.0, 0, 0),
         search=(),                   # 3DS {2, 30, 300, 100, 0, 10, 0}: never searches
         attacks=((7, 'bullet'),),
         P=(1.2, 100, 50, 50)),       # walk rate (+0x84), jump interval / chance %, wall jump chance % (+0x78..)
    dict(name='waddledoo', areas=((0, 2, 1.0, 1.0, 0.0, 0.0), (1, 2, 8.0, 10.0, 0.0, 0.0)), kind=0x19,
         motions=(('BeamShot', 1), ('BeamShotHold', 1), ('Damage', 1), ('DamageFall', 1), ('DamageFly', 1),
                  ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1),
                  ('Fall', 1), ('Jump', 1), ('Landing', 1), ('Turn', 1), ('Walk', 1)),
         dead='Damage', last='Jump', hashset=False, kick=False,
         energy={8: 0.3, 0x10: 0.3, 0x20: 0.5, 0x24: 2.4, 0x28: 0.5, 0x2C: 2.4},
         states={1: ('g_fall_en', 'g_fall_up'), 2: ('g_land_en', 'g_landt_up'), 3: ('o_walk_en', 'o_walk_up'),
                 4: ('g_turn_en', 'g_turn_up'), 5: ('g_hop_en', 'g_hop_up'), 6: ('g_dead_en', 'g_dead_up'),
                 7: 'remove', 8: ('o_leave_en', 'o_leave_up')},
         # the 3DS's 10 / 11 / 9 (dead / remove / leave; 6 hop and 7 / 8 beam not ported)
         start=(1, 1), rets=(3, 1, 1, 6), remove=7, leave=600,   # start: +0x184 = PS8c f0 600
         fall=('Fall', 2), landing='Landing', turn='Turn', turnst=4,
         walkst=3, hop=(1.0, 3, 0), hop_motion=('Jump', 0),
         search=((2, 60, 200.0, 200.0, 0.0, 0.0, 0.0), (2, 20, 60.0, 70.0, 30.0, 20.0, 0.0)),
         attacks=((6, 'bullet'),),
         # the leave (state 9, init_common_leave(P6 {300, 0.02, 30, -1, 0, 0, 3, 0, 0.85})): frames, the
         # energy's +0x30 (-0.02) / +0x34 (30), the leave effect's offset y and scale
         P=(300, -0.02, 30.0, 3.0, 0.85)),
    dict(name='churine', areas=((0, 0, 12.0, 12.0, 0.0, 0.0), (1, 3, 5.0, 10.0, 0.0, 4.0)), kind=0x1F,
         motions=(('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1),
                  ('DownLoop', 1), ('DownWait', 1), ('Jump', 1), ('Landing', 1), ('SleepPowder', 1), ('Turn', 1),
                  ('Walk', 1), ('Fall', 1)),
         dead='DamageStart', last='Fall', hashset=True, kick=False,
         energy={8: 0.7, 0x10: 0.1, 0x14: 0.05, 0x20: 0.2, 0x24: 2.5, 0x28: 0.2, 0x2C: 2.5},
         states={1: ('g_fall_en', 'g_fall_up'), 2: ('g_land_en', 'g_landt_up'), 3: ('c_walk_en', 'c_walk_up'),
                 4: ('c_jump_en', 'g_hop_up'), 5: ('g_turn_en', 'g_turn_up'), 6: ('g_dead_en', 'g_dead_up'),
                 7: 'remove'},                # the 3DS's 8 / 9 (6 / 7 not ported: no empty rows)
         start=(1, 1), rets=(3, 1, 1, 6), remove=7, fall=('Fall', 2), landing='Landing', turn='Turn', turnst=5,
         walkst=3, hop=(20.0, 2, 1),
         search=(),                   # 3DS {2, 3, 100, 35, 5, 5, 0}: only for the powder (not ported)
         attacks=((6, 'churine_bullet'),),
         P=()),
    # ---- step 2c
    # White Bear (Ice Climber) 0x40, BehaviorWhitebear (enemy_fs.cro create 0x7F420, table 0x111E8C)
    dict(name='whitebear', areas=((0, 2, 1.0, 1.0, 0.0, 0.0), (1, 3, 12.0, 26.0, 0.0, 5.0)), kind=0x40,
         motions=(('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1),
                  ('DownLoop', 1), ('DownWait', 1), ('Fall', 1), ('Landing', 1), ('Move', 1), ('QuakeFall', 1),
                  ('QuakeHold', 1), ('QuakeLanding', 1), ('QuakeUp', 1), ('SpecialTurn', 1), ('Turn', 1)),
         dead='DamageStart', last='Fall', hashset=True, kick=False,
         energy={0x10: 1.0, 8: 0.3, 0x14: 0.0},                 # initialize 0x7E738: P0 f1 / f2 / f3
         states={1: ('g_fall_en', 'g_fall_up'), 2: ('g_land_en', 'g_landt_up'), 3: ('b_walk_en', 'b_walk_up'),
                 4: ('b_sturn_en', 'g_turn_up'), 5: ('g_turn_en', 'g_turn_up'), 6: ('b_hold_en', 'b_hold_up'),
                 7: ('b_up_en', 'b_up_up'), 8: ('b_fall_en', 'b_fall_up'), 9: ('b_land_en', 'b_land_up'),
                 10: ('g_dead_en', 'g_dead_up'), 11: 'remove'},
         start=(1, 1), rets=(3, 1, 1, 10), remove=11, fall=('Fall', 2), landing='Landing', turn='Turn', turnst=5,
         walkst=3, hop=(0.0, 0, 0),
         search=((2, 30, 300.0, 100.0, 0.0, 10.0, 0.0), (2, 60, 180.0, 140.0, 0.0, 10.0, 0.0)),
         attacks=((10, 'whitebear_bullet'),),
         # P0 (0x5C a row): walk frames f7 / f8, QuakeHold rate f9, jump f10, fall E+0x3C f11 / E+0x2C f12, landing
         # rate f13, long-fall frames f14, repeat chance f15 (%%, halved per landing), repeat landing rate f16, quakes
         # f17, search cool-down f18; 0.1 the jump's E+0x3C (a literal)
         P=(60, 120, 1.5, 1.5, 1.0, 3.0, 1.0, 180, 50, 0.5, 3, 60, 0.1,
            2.5, 8.0)),       # v2: the landing effects' scales (0x7400000: the 3DS's (2.5, 1.7, 1) as 2.5; 0x7400001 8)
    # Gordo (Kirby) 0x08, BehaviorGordo (create 0x1A470, table 0x10F55C): variation 0 (the one the spawner makes)
    dict(name='gordo', areas=((0, 0, 12.0, 12.0, 0.0, 0.0), (0, 0, 14.0, 14.0, 0.0, 0.0)), kind=0x08,
         motions=(('Togetoge', 1),), no_damage_labels=True,       # its ctor 0x1A4A8: no hashsets, no damage labels
         dead=None, last=None, hashset=False, kick=True,
         energy={0x10: 0.0, 8: 0.0, 0x14: 0.0, 0x20: 0.0, 0x24: 0.0, 0x28: 0.0, 0x2C: 0.0, 0x40: 1.0, 0x18: 0.0,
                 0xC: 100.0},                                   # initialize 0x1A1D8 (variation 0's row: zeros)
         states={1: ('o_spin_en', 'o_nop'), 3: 'remove'},     # 2: variations 1-3 (moving on a path): not ported
         start=(1, 1), rets=(0, 0, 0, 0), remove=3, fall=(None, 0), landing=None, turn=None, turnst=0,
         walkst=0, hop=(0.0, 0, 0), smode=1,
         search=(),                   # 3DS {2, 30, 300, 100, 0, 10, 0}: never searches
         attacks=((1, 'gordo_spike'), (2, 'gordo_spike')),
         P=()),
)
_GS = vl_group('ghos', 'struct')     # P@0x8C: 20, 40, 96.0, 0.6, 0.8, 1200, 30.0
_GP7 = vl_group('ghos', 7)           # the two slip-homing sets
_GP6 = vl_group('ghos', 6)[0]        # the leave: {100, 0.02, 30, -1, 0, 0, 3, 0, 0.85}
_TP0 = vl_group('tikibuzz', 0)[0]    # Tiki Buzz's P0 row (variation 0)
_FS = vl_group('furiijio', 'struct')   # P@0x8C: 900, 2.5, 2, 1, 0.0, 1.0, 1.5, 25, 150, 20.0, 22, 4.5, 60, 34, 1, 1, 4.5, 140
_FP0 = vl_group('furiijio', 0)[0]      # P0 row, variation 0: set_mode_homing's six floats
_FP6 = vl_group('furiijio', 6)[0]      # the leave: {200, 0.01, 10, -1, 0, 0, 5, 0, 1}
DEG2RAD = struct.unpack('>f', bytes.fromhex('3C8EFA35'))[0]   # the 3DS literal (0.0174533)
# calc_angle's literals (3DS 0x7B01D8: pi / 2, 180, +-1 / pi), the clamp's -1 and the 2D rotation's small-angle
# test (0x67364: 1e-5)
FU_CALC = tuple(struct.unpack('>f', bytes.fromhex(h))[0] for h in ('3FC90FDB', '43340000', '3EA2F983', 'BEA2F983',
                                                                   'BF800000', '3727C5AC'))
FU_PD4 = 15.0                          # P@0xD4 (the beam hitbox's base offset; the spec's float after the struct)
_PP0 = vl_group('propellerheiho', 0)[0]    # P0 row (variation 0, 33 words: P(0)..P(32) = the 3DS P0 +0x00..+0x80)
_F = lambda h: struct.unpack('>f', bytes.fromhex(h))[0]  # noqa: E731
# Propeller Heiho's literals after its P0 row (the 3DS code's own constants; 0x3B360B61 = 1 / 360, 0x3C23D70A = 0.01)
PHK = dict(c01=33, c10=34, c50=35, c5=36, c1=37, cm1=38, c0=39, c360=40, deg=41, i360=42, half=43, stop=44, cm5=45)
PH_LIT = (_F('3DCCCCCD'), 10.0, 50.0, 5.0, 1.0, -1.0, 0.0, 360.0, DEG2RAD, _F('3B360B61'), 0.5, _F('3C23D70A'), -5.0)
FLIERS = (
    # Ghos (Kid Icarus) 0x11, BehaviorGhos (create 0x11560, table 0x10D350; docs/smash-run-port.md "Step 2e")
    dict(name='ghos', kind=0x11, flier=True, size=GH_SIZE, areas=tuple(tuple(e) for e in vl_group('ghos', 5)),
         motions=(('DamageStart', 1), ('FlyHoming', 1)), no_damage_labels=True,    # its ctor: no damage labels,
         dead='DamageStart', last=None, hashset=False, kick=False,                   # no hashsets
         energy={},                                      # initialize 0x10F74: bx lr
         states={1: ('f_g1_en', 'f_g1_up'), 2: ('f_g2_en', 'f_g2_up'), 3: ('f_leave_en', 'o_leave_up'),
                 4: ('g_dead_en', 'g_dead_up'), 5: 'remove'},
         start=(1, 1), rets=(1, 1, 1, 4), remove=5, fall=(None, 0), landing=None, turn=None, turnst=0, walkst=0,
         hop=(0.0, 0, 0), search=((0, 120, 300.0, 0.0, 0.0, 0.0, 0.0),),           # P1 (never searched)
         attacks=((1, 'ghos_body'), (4, 'ghos_bullet')),
         fstart='f_ghos_start', fdmg='f_ghos_dmg', f69='f_ghos_69', f27='f_ghos_rm', lvp=19,
         vtover={55: 'f_g55', 31: 'f_g31'},              # step 2g v3: the 3DS's slot 55 0x10BA0 (the turn); v4: 31
         P=(_GS[0], _GS[1], int(_GS[2]), _GS[3], _GS[4], _GS[5], 0.1) + tuple(_GP7[0]) + tuple(_GP7[1]) +
           (_GP6[0], -_GP6[1], _GP6[2], _GP6[6], _GP6[8], 1.0, 0.0) + (_GS[6], DEG2RAD)),   # P26 P@0xA4 30, P27
    # Tiki Buzz (Kirby) 0x0F, BehaviorTikibuzz (create 0x78630, table 0x10E134)
    dict(name='tikibuzz', kind=0x0F, flier=True, size=FL_SIZE, areas=tuple(tuple(e) for e in vl_group('tikibuzz', 5)),
         motions=(('Attack', 1), ('AttackBrake', 1), ('AttackHold', 4), ('AttackUnguard', 1), ('DamageFall', 1),
                  ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1), ('DownLoop', 1),
                  ('DownWait', 1), ('Fly', 1), ('FlyReady', 1), ('Step', 1)),
         dead='DamageStart', last='Fly', hashset=False, kick=False,
         energy={0x44: _TP0[18]},                       # initialize 0x77DC8: energy +0x44 = P0 f18 (0.98)
         states={1: ('t_fall_en', 't_fall_up'), 2: ('g_dead_en', 'g_dead_up'), 3: ('t_fly_en', 't_fly_up'),
                 4: ('t_hold_en', 't_hold_up'), 5: ('t_dive_en', 't_dive_up'), 6: ('t_brk_en', 't_brk_up'),
                 7: ('t_land_en', 't_land_up'), 8: ('t_rdy_en', 't_rdy_up'), 9: ('t_lv_en', 't_lv_up'),
                 10: ('t_stomp_en', 't_stomp_up'), 11: ('t_gone_en', 't_gone_up'), 12: 'remove'},
         tread=10, tbox=(6.0, 0.0, 1.5), tnode=3,      # area 0 (node 3 = HipN, 12 x 3): step 2g v5 centred on the
                                                       # live node (node_global_position), as the 3DS area is
         start=(3, 3), rets=(3, 3, 3, 2), remove=12, fall=(None, 0), landing=None, turn=None, turnst=0, walkst=0,
         hop=(0.0, 0, 0), search=tuple(tuple(g) for g in vl_group('tikibuzz', 1)),
         attacks=((5, 'tiki_dive'), (2, 'tiki_bullet')), fstart='f_tiki_start',
         P=tuple(_TP0[:14]) + (int(_TP0[14]),) + tuple(_TP0[15:19]) + (float(_TP0[19]), _TP0[20]) +
           (vl_group('tikibuzz', 'struct')[0], _TP0[3], _TP0[4], _TP0[7], _TP0[8], _TP0[5], _TP0[6], 0.0)),
    # Furiijio (Kid Icarus) 0x1A, BehaviorFuriijio (create 0x6DC6C, table 0x10D168; docs/smash-run-port.md "Step 2f")
    dict(name='furiijio', kind=0x1A, flier=True, size=FU_SIZE, areas=tuple(tuple(e) for e in vl_group('furiijio', 5)),
         motions=(('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1),
                  ('DownLoop', 1), ('DownWait', 1), ('IceBeamShot', 1), ('IceBeamShotHold', 1), ('Move', 1)),
         dead='DamageStart', last='Move', hashset=False, kick=False,
         energy={},                                      # initialize 0x6C404: bx lr
         states={1: ('fu1_en', 'fu1_up'), 2: ('fu2_en', 'fu2_up'), 3: ('fu3_en', 'fu3_up'),
                 4: ('fu4_en', 'fu4_up', 'fu_bexit'), 5: ('fu5_en', 'fu5_up'), 6: ('fu6_en', 'fu6_up'),
                 7: ('fu7_en', 'fu7_up', 'fu_bexit'), 8: ('fu8_en', 'o_leave_up'), 9: ('fu9_en', 'g_dead_up'),
                 10: 'remove'},
         start=(1, 1), rets=(1, 1, 1, 9), remove=10, fall=(None, 0), landing=None, turn=None, turnst=0, walkst=0,
         hop=(0.0, 0, 0), search=tuple(tuple(g) for g in vl_group('furiijio', 1)),
         attacks=((4, 'fu_beam0'), (7, 'fu_beam1'), (9, 'fu_bullet')),
         fstart='f_fu_start', fdmg='f_fu_dmg', lvp=31,
         vtover={4: 'f_fu_skip', 61: 'f_fu_kin', 62: 'f_fu_kin'},
         P=tuple(_FP0[1:7]) + (_FS[0], _FS[1] * 10, _FS[2], _FS[3], _FS[4] * 10, _FS[5] * 10, _FS[6], _FS[7], _FS[8],
                               _FS[9] * 10, _FS[10], _FS[11], _FS[12], _FS[13], _FS[14], _FS[15], _FS[17],
                               180.0 / (_FS[17] or 1), FU_PD4, 1.5, 0.05, DEG2RAD, 90.0, 1.0, 0.0) +
           (_FP6[0], -_FP6[1], _FP6[2], _FP6[6], _FP6[8]) + FU_CALC),
    # Propeller Heiho (Mario) 0x47, BehaviorPropellerheiho (create 0x9AA38, table 0x111278; docs/smash-run-port.md
    # "Step 2g"): its ctor's damage labels (Damage x 8, Vertical); slot 69 always => 7, so they are never played
    dict(name='propellerheiho', kind=0x47, flier=True, size=PH_SIZE,
         areas=tuple(tuple(e) for e in vl_group('propellerheiho', 5)),
         motions=(('Damage', 1), ('Move', 1), ('TurnAir', 1), ('Vertical', 1)),
         dmg_labels=('Damage',) * 8 + ('Vertical',),
         dead='Damage', last='Vertical', hashset=False, kick=False,
         energy={},                                      # no initialize override
         states={1: ('ph1_en', 'ph1_up'), 2: ('ph2_en', 'ph2_up'), 3: ('ph3_en', 'ph3_up'), 4: ('ph4_en', 'ph4_up'),
                 5: ('ph5_en', 'ph5_up'), 6: ('ph6_en', 'ph6_up'), 7: ('ph7_en', 'ph7_up'), 8: 'remove'},
         start=(4, 4), rets=(4, 4, 4, 3), remove=8, fall=(None, 0), landing=None, turn=None, turnst=0, walkst=0,
         hop=(0.0, 0, 0), search=tuple(tuple(g) for g in vl_group('propellerheiho', 1)),
         attacks=((3, 'ph_bullet'),),
         fstart='f_ph_start', fdmg='f_ph_dmg', f69='f_ph_69', f27='f_ph_rm',
         vtover={55: 'f_ph_55', 59: 'f_ph_59'},
         P=tuple(_PP0) + PH_LIT),
)
WALKERS = WALKERS + FLIERS
KINDS = tuple(w['kind'] for w in WALKERS)


def stem(name, sfx):
    return 'Enm%sBodyMain%s' % (name.capitalize(), sfx)


def motion_hash(s):
    return zlib.crc32(s.encode(), 0xFFFFFFFF)


def index(w, sfx):
    return [m for m, _f in w['motions']].index(sfx) if sfx else -1


def nstates(w):
    return max(k for k in w['states']) + 1


def fword(v):
    return struct.unpack('>I', struct.pack('>f', v))[0]


def word(v):
    return fword(v) if isinstance(v, float) else v & 0xFFFFFFFF


def sx(v):
    """signed 16-bit low half (for `addi` / `lwz` after `lis ha`)"""
    v = lo(v)
    return v - 0x10000 if v & 0x8000 else v


def branch(src, dst, link=False):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000
    return 0x48000000 | (off & 0x03FFFFFC) | (1 if link else 0)


def branch_target(src, word_):
    off = word_ & 0x03FFFFFC
    return src + (off - 0x4000000 if off & 0x2000000 else off)


def cfg_size(w):
    return CF['P'] + 4 * max(5, len(w['P']))


def damage_labels(w):
    """the nine set_damage_motion_label indices (all -1 for a kind whose 3DS create doesn't call it: then the call
    is skipped)"""
    if w.get('no_damage_labels'):
        return [-1] * 9
    if w.get('dmg_labels'):                     # step 2g: the 3DS create's own nine (motion names)
        return [index(w, s) for s in w['dmg_labels']]
    return [index(w, s) for s in DAMAGE_LABELS] + [index(w, w['last'])]


def cfg_values(w, D, fn=lambda x: 0):
    """the kind's CFG words (D: data labels, fn: code label -> address)"""
    n = w['name']
    lm = lambda s: index(w, s) if s else 0  # noqa: E731
    c = dict(KIND=w['kind'], NST=nstates(w), TAB=D['st_' + n] - 0x18, START=w['start'][0], START01=w['start'][1],
             R64=w['rets'][0], R65=w['rets'][1], R66=w['rets'][2], R67=w['rets'][3], REMOVE=w['remove'],
             DEADMOT=lm(w['dead']), HASH=D.get('hs_' + n, 0), EN=D['en_' + n], ENN=len(w['energy']),
             KICK=1 if w['kick'] else 0, SET=D['set_' + n], ATK=D['atk_' + n], SRCH=D['sr_' + n],
             FALLMOT=lm(w['fall'][0]), LANDST=w['fall'][1], LANDMOT=lm(w['landing']), TURNMOT=lm(w['turn']),
             TURNST=w['turnst'], WALKST=w['walkst'], HOPTHR=fword(w['hop'][0]), HOPLAND=w['hop'][1],
             HOPFLAG=w['hop'][2], HOPMOT=lm(w.get('hop_motion', (None, 0))[0]),
             HOPLOOP=w.get('hop_motion', (None, 0))[1], ZERO=0, TREAD=w.get('tread', 0), AREA=D['ar_' + n],
             SMODE=w.get('smode', 0), LEAVE=w.get('leave', 0),
             VT=D['vt_' + n] if w.get('vtover') else D['vtf' if w.get('flier') else 'vt'], SIZE=w.get('size', OBJ_SIZE),
             TB0=fword(w.get('tbox', TREAD_BOX)[0]), TB1=fword(w.get('tbox', TREAD_BOX)[1]),
             TB2=fword(w.get('tbox', TREAD_BOX)[2]), FSTART=fn(w.get('fstart', 0)), FDMG=fn(w.get('fdmg', 0)),
             F69=fn(w.get('f69', 0)), F27=fn(w.get('f27', 0)), LVP=P(w['lvp']) if 'lvp' in w else 0,
             TNODE=w.get('tnode', 0))
    words = [0] * (cfg_size(w) // 4)
    for k, v in c.items():
        words[CF[k] // 4] = v & 0xFFFFFFFF
    for i, v in enumerate(damage_labels(w)):
        words[CF['DMG'] // 4 + i] = v & 0xFFFFFFFF
    for i, v in enumerate(w['P']):
        words[P(i) // 4] = word(v)
    return words


# ---------------------------------------------------------------- data
class Data:
    """the cave's data blocks: [(label, words, align)], placed by place()"""

    def __init__(self, vt_words):
        self.vt_words = vt_words
        self.addr, self.blocks = {}, []

    def build(self, cl, D=None):
        """cl: the code's labels; D: the data addresses of the previous pass (0s in the first)"""
        D = D or {}
        g = lambda k: D.get(k, 0)  # noqa: E731
        fn = lambda x: x if isinstance(x, int) else cl.get(x, 0)  # noqa: E731
        b = self.blocks = []
        b.append(('consts', [fword(0.0), fword(1.0), 0x2545F491, 0], 0x10))     # 0.0, 1.0, the xorshift state
        b.append(('abs_words', [word(v) for v in ABS_WORDS], 4))
        b.append(('fconsts', [0x43300000, 0x80000000], 8))      # the int -> double bias (f_hitret)
        # step 2g v3: w_yaw (+0xC: the YAW_HOLD mask); step 2g v6: +0x18 the FLIP_TABLE mask (w_noflip / twin_flip)
        b.append(('yawk', [fword(1.0), fword(90.0), fword(-90.0)] + yaw_mask() + yaw_mask(FLIP_TABLE), 4))
        vt = list(self.vt_words) + [0, 0, 0, 0]          # 74 slots + 74 / 75
        over = {12: ZIMA_CAPTURE_MOTION, 38: ZIMA_ONE if KEEP_FLIP else fn('w_noflip'), 40: fn('w_init'),
                3: fn('w_upd'), 41: fn('w_start'), 45: fn('w_atk'), TREAD_SLOT: fn('w_tread'), 64: fn('w_r64'), 65: fn('w_r65'), 66: fn('w_r66'),
                67: fn('w_r67'), 72: fn('w_chg'), 73: fn('w_chgi'), 74: fn('w_chg'), 75: fn('w_chgi'),
                SET_LR_SLOT: fn('w_slr'), 50: fn('w_rlr')}       # step 2g v3: the 3DS flip's facing (YAW_FLIP)
        for k, f in over.items():
            vt[(0xC + 8 * k) // 4] = f
            vt[(0x8 + 8 * k) // 4] = 0
        b.append(('vt', vt, 4))
        vtf = list(vt)
        for k in (10, 27, 41, 69):
            vtf[(0xC + 8 * k) // 4] = fn('f_v%d' % k)
            vtf[(0x8 + 8 * k) // 4] = 0
        b.append(('vtf', vtf, 4))
        for w in WALKERS:                # step 2f: a kind's own vtable (VTF plus its overrides `vtover`)
            if w.get('vtover'):
                vk = list(vtf)
                for k, f in w['vtover'].items():
                    vk[(0xC + 8 * k) // 4] = fn(f)
                    vk[(0x8 + 8 * k) // 4] = 0
                b.append(('vt_' + w['name'], vk, 4))
        ktab = []
        for w in WALKERS:
            ktab += [w['kind'], g('cfg_' + w['name'])]
        b.append(('ktab', ktab + [0xFFFFFFFF], 4))
        for name, entry in ATTACKS.items():
            b.append((name, [word(v) for v in entry], 4))
        for w in WALKERS:
            n = w['name']
            ms = w['motions']
            b.append(('set_' + n, [g('set_' + n) + 0x18, len(ms), 0, 0, 0, 0] +
                      [x for sfx, flags in ms for x in (motion_hash(stem(n, sfx)), flags)], 4))
            if w['hashset']:
                b.append(('hs_' + n, [zlib.crc32((sfx.lower() + x).encode()) for sfx, _f in ms
                                      for x in ('.init', '', '.exit')], 4))
            b.append(('en_' + n, [x for off, v in sorted(w['energy'].items()) for x in (off, fword(v))], 4))
            for row, en in sorted(w.get('rows', {}).items()):
                b.append(('row_%s_%s' % (n, row), [x for off, v in sorted(en.items()) for x in (off, fword(v))] +
                          [0xFFFFFFFF], 4))
            b.append(('sr_' + n, [word(v) for grp in w['search'] for v in grp], 4))
            b.append(('atk_' + n, [x for st, a in w['attacks'] for x in (st, g(a))] + [0xFFFFFFFF], 4))
            st = []
            for i in range(1, nstates(w)):         # row 0 is never used (id 0 -> 1)
                s = w['states'].get(i)
                if s == 'remove':
                    s = (ZIMA_REMOVE_ENTER, ZIMA_REMOVE_UPDATE)
                st += ([0xFFFF, fn(s[0]), 0xFFFF, fn(s[1])] + ([0xFFFF, fn(s[2])] if len(s) > 2 else [0, 0])
                       if s else [0] * 6)            # {enter, update, exit} PMFs (step 2f: an exit)
            b.append(('st_' + n, st, 4))
            b.append(('ar_' + n, [word(v) for e in w['areas'] for v in e], 4))
            need = ('st_', 'en_', 'set_', 'atk_', 'sr_', 'ar_') + (('hs_',) if w['hashset'] else ())
            dd = {p + n: g(p + n) for p in need}
            dd.update(vt=g('vt'), vtf=g('vtf'))
            if w.get('vtover'):
                dd['vt_' + n] = g('vt_' + n)
            b.append(('cfg_' + n, cfg_values(w, dd, fn), 4))
        return self

    def place(self, spans):
        """first fit into spans [(lo, hi)]; sets .addr, .chunks [(base, words)]"""
        spans = [list(s) for s in spans]
        self.addr, self.chunks = {}, []
        for label, words, al in sorted(self.blocks, key=lambda x: -len(x[1])):     # largest first
            for s in spans:
                a = (s[0] + al - 1) & ~(al - 1)
                if a + 4 * len(words) <= s[1]:
                    self.addr[label] = a
                    self.chunks.append((a, words))
                    s[0] = a + 4 * len(words)
                    break
            else:
                raise AssertionError('walker data does not fit (%s)' % label)
        self.free = [tuple(s) for s in spans]
        return self


# ---------------------------------------------------------------- code
def code(D):
    """two Asm units (regions A and B) from the data addresses D; returns (a, b)"""
    A, B = Asm(CAVE), Asm(CAVE_B)

    def far(a, t):
        a.asm("lis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctrl" % (t >> 16, t & 0xFFFF))

    def la(a, r, label):
        a.asm("lis %s, 0x%04X\naddi %s, %s, %d" % (r, ha(D[label]), r, r, sx(D[label])))

    def la4(label):
        return "lis r4, 0x%04X\naddi r4, r4, %d" % (ha(D[label]), sx(D[label]))

    def tail(a, t):
        a.asm("lis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctr" % (t >> 16, t & 0xFFFF))

    def lfs(a, fr, label, off=0):
        a.asm("lis r12, 0x%04X\nlfs %s, %d(r12)" % (ha(D[label] + off), fr, sx(D[label] + off)))

    # ---- the shared prologue / epilogue and helpers (r31 this, r30 CFG, r29 the AI input; helpers keep r28-r31)
    A.asm("""
    pro:
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        stmw r28, 0x20(r1)
        mr r31, r3
        lwz r30, 0x168(r3)
        mr r29, r4
        blr
    go:
        bl h_chg
    epi:
        lmw r28, 0x20(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    goi:
        bl h_chgi
        b epi
    h_chg:
        mr r3, r31
        lwz r12, 0xE0(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctr
    h_chgi:
        mr r3, r31
        lwz r12, 0xE0(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctr
    h_rev:
        mr r3, r31
        li r4, 1
        li r5, 1
        lwz r12, 0xE0(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctr
    h_kin:
        lwz r3, 0(r31)
        lwz r3, 0x30E8(r3)
        b 0x%08X
    h_att:
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        b 0x%08X
    h_gnd:
        li r4, 8
    h_touch:
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        b 0x%08X
    h_end:
        lwz r3, 0(r31)
        lwz r3, 0x30F0(r3)
        b 0x%08X
    """ % (SLOT[72], SLOT[73], SLOT[50], CHANGE_KINETIC, SET_ATTACH_GROUND, IS_TOUCH, MOTION_IS_END))
    # the Behavior helpers at 0x026Axxxx are beyond a `b` from the cave: through ctr
    for lab, t in (('h_wall', CHECK_WALL), ('h_cliff', CHECK_CLIFF), ('h_clear', CLEAR_SPEED),
                   ('h_stop', IS_STOPPED), ('h_near', NEAREST)):
        A.asm("%s:\nmr r3, r31" % lab)
        tail(A, t)
    A.asm("h_mot1:")
    lfs(A, 'f2', 'consts', 4)
    A.asm("h_mot:")
    lfs(A, 'f1', 'consts')
    A.asm("fmr f3, f1\nmr r3, r31\nb 0x%08X" % CHANGE_MOTION)
    A.asm("h_tchk:")                      # check_turn_to_target(r4 id, 0)
    lfs(A, 'f1', 'consts')
    A.asm("mr r3, r31")
    tail(A, CHECK_TURN)
    # h_vy0: f1 = the current speed's y, cr0 = f1 ? 0
    A.asm("""
    h_vy0:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        addi r3, r1, 8
        mr r4, r31
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        mtctr r12
        bctrl
        lfs f1, 0xC(r1)
        lis r12, 0x%04X
        lfs f0, %d(r12)
        fcmpu cr0, f1, f0
        b h_ret20
    """ % (GET_SPEED >> 16, GET_SPEED & 0xFFFF, ha(D['consts']), sx(D['consts'])))
    A.asm("""
    h_ret20:
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    h_dx:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        mr r5, r4
        addi r3, r1, 8
        mr r4, r31
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        mtctr r12
        bctrl
        lfs f1, 8(r1)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x10(r12)
        fsubs f1, f1, f0
        lfs f0, 0x10(r31)
        fmuls f1, f1, f0
        b h_ret20
    h_grp:
        lwz r12, %d(r30)
        mulli r0, r4, 0x1C
        add r12, r12, r0
        lwz r3, 4(r12)
        blr
    h_srch:
        lwz r12, %d(r30)
        mulli r0, r4, 0x1C
        add r12, r12, r0
        lwz r4, 0(r12)
        lfs f1, 0x10(r12)
        lfs f2, 0x14(r12)
        lfs f3, 8(r12)
        lfs f4, 0xC(r12)
        lfs f5, 0x18(r12)
        addi r5, r31, 0x10
        mr r3, r31
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        mtctr r12
        bctr
    h_mv:
        lwz r0, 0x10(r31)
        stw r0, 0(r29)
        lwz r0, 0x14(r31)
        stw r0, 4(r29)
        blr
    h_mv0:
        li r0, 0
        stw r0, 0(r29)
        stw r0, 4(r29)
        blr
    h_flag:
        lwz r12, 0(r31)
        lwz r12, 0x3130(r12)
        lwz r12, 8(r12)
        lwz r12, 0(r12)
        lwz r12, 0x14(r12)
        lwz r3, 0(r12)
        and. r3, r3, r4
        blr
    h_ebase:
        lwz r12, 0(r31)
        lwz r12, 0x3130(r12)
        lwz r10, 8(r12)
        lwz r10, 0(r10)
        lwz r10, 4(r10)
        blr
    h_en:
        mflr r9
        bl h_ebase
        mtlr r9
    en_loop:
        lwz r7, 0(r4)
        cmpwi r7, -1
        beqlr
        lwz r6, 4(r4)
        stwx r6, r10, r7
        addi r4, r4, 8
        b en_loop
    h_kick:
        lwz r12, 0(r31)
        lwz r3, 0x3130(r12)
        lwz r12, 0(r3)
        lwz r12, 0xFC(r12)
        mtctr r12
        lis r4, 0x2000
        ori r4, r4, 4
        bctr
    h_dy:
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        lfs f0, 0x%X(r31)
        fsubs f1, f1, f0
        fabs f1, f1
        blr
    h_sety:
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        stfs f1, 0x%X(r31)
        blr
    """ % (GET_TARGET_POS >> 16, GET_TARGET_POS & 0xFFFF, CF['SRCH'], CF['SRCH'], SEARCH >> 16,
           SEARCH & 0xFFFF, Y0, Y0))
    # h_rand(r3 lo, r4 hi) -> r3 in [lo, hi] (xorshift32 in consts+8)
    A.asm("h_rand:")
    la(A, 'r12', 'consts')
    A.asm("""
        lwz r0, 8(r12)
        slwi r11, r0, 13
        xor r0, r0, r11
        srwi r11, r0, 17
        xor r0, r0, r11
        slwi r11, r0, 5
        xor r0, r0, r11
        stw r0, 8(r12)
        subf r4, r3, r4
        addi r4, r4, 1
        divwu r11, r0, r4
        mullw r11, r11, r4
        subf r0, r11, r0
        add r3, r3, r0
        blr
    """)

    # ---- F2: the factory (r31 kind, r30 module, r29 variation, r12 = kind - 0x50)
    A.asm("cave_f:")
    la(A, 'r11', 'ktab')
    A.asm("""
    f_loop:
        lwz r10, 0(r11)
        cmpwi r10, -1
        beq f_other
        cmpw r10, r31
        beq f_mine
        addi r11, r11, 8
        b f_loop
    f_other:
        cmplwi r12, 0x10
        b 0x%08X
    f_mine:
        lwz r3, 4(r30)
        mr r4, r31
        mr r5, r29
        bl w_create
        stw r3, 8(r30)
        b 0x%08X
    """ % (FACTORY_NEXT, FACTORY_END))
    # ---- create(acc, kind, variation) -> the behaviour (0 for another kind / no memory)
    A.asm("""
    w_create:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r27, 0x1C(r1)
        mr r28, r3
        mr r29, r4
        mr r30, r5
        li r27, 0
    """)
    la(A, 'r11', 'ktab')
    A.asm("""
    c_loop:
        lwz r10, 0(r11)
        cmpwi r10, -1
        beq c_out
        cmpw r10, r29
        beq c_found
        addi r11, r11, 8
        b c_loop
    c_found:
        lwz r31, 4(r11)
        lwz r3, 0x%X(r31)
        bl 0x%08X
        mr. r27, r3
        beq c_out
        mr r4, r28
        mr r5, r29
        mr r6, r30
        bl 0x%08X
        li r0, 0
        addi r11, r27, 0xE0
        lwz r12, 0x%X(r31)
        addi r12, r12, -0xE4
        srwi r12, r12, 2
        mtctr r12
    c_zero:
        stwu r0, 4(r11)
        bdnz c_zero
        li r0, 1
        stb r0, 0x120(r27)
        li r0, -1
        stw r0, 0x15C(r27)
    """ % (CF['SIZE'], OPNEW, BEH_CTOR, CF['SIZE']))
    A.asm("""
        lwz r11, 0x%X(r31)
        stw r11, 0xE0(r27)
        lis r11, 0x%04X
        lwz r12, %d(r11)
        stw r12, 0xE8(r27)
        lwz r12, %d(r11)
        stw r12, 0xEC(r27)
        stw r31, 0x168(r27)
        mr r3, r27
        li r4, 0
        lwz r5, 0x%X(r31)
        bl 0x%08X
        lwz r4, 0x%X(r31)
        cmpwi r4, -1
        beq c_out
        mr r3, r27
    """ % (CF['VT'], ha(COMMON_PMF), sx(COMMON_PMF), sx(COMMON_PMF + 4), CF['HASH'], SET_MOTION_LABEL, CF['DMG']))
    for i, r in enumerate(('r4', 'r5', 'r6', 'r7', 'r8', 'r9', 'r10')):
        A.asm("lwz %s, 0x%X(r31)" % (r, CF['DMG'] + 4 * i))
    A.asm("""
        lwz r0, 0x%X(r31)
        stw r0, 8(r1)
        lwz r0, 0x%X(r31)
        stw r0, 0xC(r1)
        bl 0x%08X
    c_out:
        mr r3, r27
        lmw r27, 0x1C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    """ % (CF['DMG'] + 0x1C, CF['DMG'] + 0x20, SET_DAMAGE_LABEL))
    # ---- slot 40 initialize: the kinetic energy words (a leaf; the Churine's walk / hop call it too)
    A.asm("""
    w_init:
        lwz r11, 0x168(r3)
        lwz r12, 0(r3)
        lwz r12, 0x3130(r12)
        lwz r10, 8(r12)
        lwz r10, 0(r10)
        lwz r10, 4(r10)
        lwz r9, 0x%X(r11)
        lwz r8, 0x%X(r11)
        cmpwi r8, 0
        beq i_kick
        mtctr r8
    i_loop:
        lwz r7, 0(r9)
        lwz r6, 4(r9)
        stwx r6, r10, r7
        addi r9, r9, 8
        bdnz i_loop
    i_kick:
        lwz r0, 0x%X(r11)
        cmpwi r0, 0
        beqlr
        mr r3, r12
        lwz r12, 0(r3)
        lwz r12, 0xFC(r12)
        mtctr r12
        lis r4, 0x2000
        ori r4, r4, 4
        bctr
    """ % (CF['EN'], CF['ENN'], CF['KICK']))
    # ---- slot 41 start: set_rhombus, +0x10 = posture lr, face the nearest target, the first state
    A.asm("w_start:\nmflr r0\nbl pro")
    far(A, SET_RHOMBUS)
    A.asm("lwz r0, 0x%X(r30)\ncmpwi r0, 0\nbeq s_lr\nbl h_smode" % CF['SMODE'])
    A.asm("""
    s_lr:
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x60(r12)
        stw r0, 0x10(r31)
        li r0, 0
        stw r0, 0x14(r31)
        stw r0, 0x18(r31)
        addi r11, r31, 0x168
        li r12, %d
        mtctr r12
    s_zero:
        stwu r0, 4(r11)
        bdnz s_zero
        lwz r0, 0x%X(r30)
        stw r0, 0x%X(r31)
        lwz r0, 0x%X(r30)
        cmpwi r0, 0
        bne s_state
        bl h_near
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        beq s_state
        bl h_rev
    s_state:
        lwz r4, 0x%X(r30)
        lwz r0, 0xC(r31)
        cmplwi r0, 1
        bgt s_go
        lwz r4, 0x%X(r30)
    s_go:
        b go
    """ % ((OBJ_SIZE - 0x16C) // 4, CF['LEAVE'], V(7), CF['SMODE'], CF['START'], CF['START01']))
    # ---- slot 20 (3DS 21): stepped on by a fighter (a footstool); the kind's state (CFG TREAD) => now, 0: nothing
    A.asm("""
    w_tread:
        lwz r12, 0x168(r3)
        lwz r4, 0x%X(r12)
        cmpwi r4, 0
        beqlr
        lwz r12, 0xE0(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctr
    """ % (CF['TREAD'], SLOT[73]))
    # ---- slots 64-67: the kind's states after damage on the ground / in the air / default, death
    for i, k in enumerate((64, 65, 66, 67)):
        A.asm("w_r%d:\nlwz r12, 0x168(r3)\nlwz r3, 0x%X(r12)\nblr" % (k, CF['R64'] + 4 * i))
    # ---- slots 72 / 73 change_state(id): the kind's table; unknown ids -> 1
    A.asm("""
    w_chg:
        lis r11, 0x%04X
        ori r11, r11, 0x%04X
        b w_chg2
    w_chgi:
        lis r11, 0x%04X
        ori r11, r11, 0x%04X
    w_chg2:
        lwz r12, 0x168(r3)
        lwz r0, 0x%X(r12)
        lwz r12, 0x%X(r12)
        cmplw r4, r0
        bge c2_one
        cmpwi r4, 0
        bne c2_in
    c2_one:
        li r4, 1
    c2_in:
        mulli r10, r4, 0x18
        add r6, r12, r10
        lwz r0, 0xC(r6)
        cmpwi r0, 0
        bne c2_ok
        li r4, 1
        addi r6, r12, 0x18
    c2_ok:
        addi r5, r6, 8
        addi r7, r6, 0x10
        mtctr r11
        bctr
    """ % (CHG_BASE >> 16, CHG_BASE & 0xFFFF, CHG_INT >> 16, CHG_INT & 0xFFFF, CF['NST'], CF['TAB']))
    # ---- slot 45 set_attack_data(state): clear_all, then the kind's attacks listed for this state
    A.asm("""
    w_atk:
        mflr r0
        bl pro
        mr r28, r4
        lwz r3, 0(r31)
        lwz r3, 0x30C8(r3)
        bl 0x%08X
        lwz r29, 0x%X(r30)
    a_loop:
        lwz r0, 0(r29)
        cmpwi r0, -1
        beq epi
        cmpw r0, r28
        bne a_next
        mr r3, r31
        lwz r4, 4(r29)
        bl 0x%08X
        lwz r12, 4(r29)
        lwz r4, 4(r12)
        lwz r5, 8(r12)
        stw r4, 0x84(r31)
        stw r5, 0x88(r31)
        lwz r3, 0(r31)
        lwz r3, 0x30C8(r3)
        addi r6, r31, 0x1C
        bl 0x%08X
    a_next:
        addi r29, r29, 8
        b a_loop
    """ % (ATK_CLEAR, CF['ATK'], ATK_CREATE, ATK_SET))

    # ---- states: f(a, label, body): a function with the shared prologue, `b epi` appended
    def st(a, label, body):
        a.asm("%s:\nmflr r0\nbl pro\n%s\nb epi" % (label, body))

    def en(a, label, kin, att, mot, loop, rate=None, extra='', pre=''):
        """an enter: [pre] kinetic, ground, motion (index / 'CFG field'), [extra]"""
        m = "lwz r4, 0x%X(r30)" % CF[mot] if isinstance(mot, str) else "li r4, %d" % mot
        r = "bl h_mot1" if rate is None else "lfs f2, 0x%X(r30)\nbl h_mot" % rate
        st(a, label, "%s\nli r4, %d\nbl h_kin\nli r4, %d\nbl h_att\n%s\nli r5, %d\n%s\n%s"
           % (pre, kin, att, m, loop, r, extra))

    # generic: fall (vy > 0: wait; on the ground => LANDST), landing, turn (end: reverse_lr => WALKST), dead
    en(A, 'g_fall_en', 8, 0, 'FALLMOT', 1)
    st(A, 'g_fall_up', "bl h_vy0\nbgt epi\nbl h_gnd\ncmpwi r3, 0\nbeq epi\nlwz r4, 0x%X(r30)\nb goi" % CF['LANDST'])
    en(A, 'g_land_en', 0, 1, 'LANDMOT', 0)
    st(A, 'g_land_up', "bl h_end\ncmpwi r3, 0\nbeq epi\nlwz r4, 0x%X(r30)\nb go" % CF['WALKST'])
    # landing that looks back (Shy Guy, Waddle Doo, Churine): unless V8 (a hop's landing), the nearest target
    # behind -> TURNST, else WALKST; V8 = 0
    st(A, 'g_landt_up', """
        bl h_end
        cmpwi r3, 0
        beq epi
        lwz r28, 0x%X(r30)
        lwz r0, 0x%X(r31)
        cmpwi r0, 0
        bne lt_go
        bl h_near
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        beq lt_go
        lwz r28, 0x%X(r30)
    lt_go:
        li r0, 0
        stw r0, 0x%X(r31)
        mr r4, r28
        b go""" % (CF['WALKST'], V(8), CF['TURNST'], V(8)))
    en(A, 'g_turn_en', 0, 1, 'TURNMOT', 0)
    st(A, 'g_turn_up', "bl h_end\ncmpwi r3, 0\nbeq epi\nbl h_rev\nlwz r4, 0x%X(r30)\nb goi" % CF['WALKST'])
    st(A, 'g_dead_en', "li r0, 1\nstw r0, 0x%X(r31)\nlwz r4, 0x%X(r30)\nli r5, 0\nbl h_mot0\nmr r3, r31\nbl 0x%08X"
       % (DEFEATED, CF['DEADMOT'], BULLET))
    A.asm("h_mot0:")                  # a motion at rate 0
    lfs(A, 'f2', 'consts')
    A.asm("b h_mot")
    st(A, 'g_dead_up', "li r4, 8\nbl h_flag\nbeq epi\nlwz r4, 0x%X(r30)\nb goi" % CF['REMOVE'])
    # a hop (Shy Guy 6, Waddle Doo 5, Churine 4): kinetic 5, ground off, Y0 = posture y; on landing: on the same
    # height (|dy| <= HOPTHR) or a wall still ahead (3DS ray_check(lr, 5)) => TURNST; else [HOPFLAG: V8 = 1] =>
    # HOPLAND
    st(A, 'g_hop_up', """
        bl h_vy0
        bgt epi
        bl h_gnd
        cmpwi r3, 0
        beq epi
        bl h_dy
        lfs f0, 0x%X(r30)
        fcmpu cr0, f1, f0
        ble hp_turn
        bl h_wall
        cmpwi r3, 0
        bne hp_turn
        lwz r0, 0x%X(r30)
        stw r0, 0x%X(r31)
        lwz r4, 0x%X(r30)
        b goi
    hp_turn:
        lwz r4, 0x%X(r30)
        b goi""" % (CF['HOPTHR'], CF['HOPFLAG'], V(8), CF['HOPLAND'], CF['TURNST']))
    # the hop enter of the Shy Guy (Walk loop) and the Waddle Doo (Jump): P-less, the motion from the kind's hop
    st(A, 'g_hop_en', "li r4, 5\nbl h_kin\nli r4, 0\nbl h_att\nlwz r4, 0x%X(r30)\nlwz r5, 0x%X(r30)\nbl h_mot1\n"
                      "bl h_sety" % (CF['HOPMOT'], CF['HOPLOOP']))

    # ---- Kuribo
    # walk: V0 frames, V3 target
    en(A, 'k_walk_en', 0xA, 1, 15, 1, rate=P(0), pre="li r0, 0\nstw r0, 0x%X(r31)" % V(0))
    st(A, 'k_walk_up', """
        li r4, 0
        bl h_grp
        lwz r0, 0x%X(r31)
        divwu r11, r0, r3
        mullw r11, r11, r3
        subf. r0, r11, r0
        bne kw_gnd
        li r4, 0
        bl h_srch
        stw r3, 0x%X(r31)
        cmpwi r3, 0
        blt kw_gnd
        mr r4, r3
        bl h_dx
        lfs f0, 0x%X(r30)
        fcmpu cr0, f1, f0
        bge kw_face
        bl h_rev
    kw_face:
        li r4, 4
        b goi
    kw_gnd:
        bl h_gnd
        cmpwi r3, 0
        bne kw_on
        li r4, 1
        bl h_chg
        b kw_in
    kw_on:
        bl h_cliff
        cmpwi r3, 0
        beq kw_wall
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        beq kw_rev
    kw_wall:
        bl k_wallt
        cmpwi r3, 0
        beq kw_in
    kw_rev:
        bl h_rev
        li r4, 3
        bl h_chg
    kw_in:
        bl h_mv
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)""" % (V(0), V(3), CF['ZERO'], V(0), V(0)))
    # k_wallt: is_touch(wall ahead: lr > 0 -> 4, else 2), cr0
    A.asm("k_wallt:\nlwz r0, 0x10(r31)\nli r4, 2\ncmpwi r0, 0\nble h_touch\nli r4, 4\nb h_touch")
    # notice: the startled hop (E+0x20 = P1, kinetic 5); V2 airborne; P3 frames after entering -> run (V1 = 0)
    en(A, 'k_ntc_en', 5, 0, 12, 1, pre="li r0, 0\nstw r0, 0x%X(r31)\nbl h_ebase\nlwz r0, 0x%X(r30)\nstw r0, 0x20(r10)"
       % (V(0), P(1)), extra="li r0, 1\nstw r0, 0x%X(r31)" % V(2))
    st(A, 'k_ntc_up', """
        lwz r0, 0x%X(r31)
        cmpwi r0, 1
        bne kn_wait
        bl h_vy0
        bgt kn_out
        bl h_gnd
        cmpwi r3, 0
        beq kn_out
        li r0, 0
        stw r0, 0x%X(r31)
        li r4, 1
        bl h_att
        b kn_out
    kn_wait:
        lwz r3, 0x%X(r31)
        lwz r0, 0x%X(r30)
        cmpw r3, r0
        ble kn_out
        li r4, 5
        bl h_chg
        li r0, 0
        stw r0, 0x%X(r31)
    kn_out:
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)""" % (V(2), V(2), V(0), P(3), V(1), V(0), V(0)))
    # run: V1 run frames; every search-1 interval a target behind -> 7; a wall / ledge (var 1) -> 7; off the
    # ground -> 1; after P4 frames -> 6
    en(A, 'k_run_en', 0xA, 1, 13, 1, rate=P(2))
    st(A, 'k_run_up', """
        li r4, 1
        bl h_grp
        lwz r0, 0x%X(r31)
        divwu r11, r0, r3
        mullw r11, r11, r3
        subf. r0, r11, r0
        bne kr_gnd
        li r4, 1
        bl h_srch
        stw r3, 0x%X(r31)
        cmpwi r3, 0
        blt kr_gnd
        mr r4, r3
        bl h_dx
        lfs f0, 0x%X(r30)
        fcmpu cr0, f1, f0
        bge kr_gnd
        li r4, 7
        bl h_chg
    kr_gnd:
        bl h_gnd
        cmpwi r3, 0
        bne kr_on
        li r4, 1
        bl h_chg
        b kr_time
    kr_on:
        bl h_cliff
        cmpwi r3, 0
        beq kr_wall
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        bne kr_wall
        bl h_clear
        b kr_turn
    kr_wall:
        bl k_wallt
        cmpwi r3, 0
        beq kr_time
    kr_turn:
        li r4, 7
        bl h_chg
    kr_time:
        lwz r3, 0x%X(r31)
        lwz r0, 0x%X(r30)
        cmpw r3, r0
        ble kr_in
        li r4, 6
        bl h_chg
    kr_in:
        bl h_mv
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)""" % (V(1), V(3), CF['ZERO'], V(1), P(4), V(1), V(1)))
    # brake: at a ledge (var 1) clear_speed_all, else off the ground -> 1; at its end -> 3; input (lr, 0)
    en(A, 'k_brk_en', 2, 1, 11, 0)
    st(A, 'k_brk_up', """
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        bne kb_g
        bl h_cliff
        cmpwi r3, 0
        beq kb_end
        bl h_clear
        b kb_end
    kb_g:
        bl h_gnd
        cmpwi r3, 0
        bne kb_end
        li r4, 1
        bl h_chg
    kb_end:
        bl h_end
        cmpwi r3, 0
        beq kb_in
        li r4, 3
        bl h_chg
    kb_in:
        bl h_mv
        li r0, 0
        stw r0, 4(r29)""")
    # run turn: at a ledge clear_speed_all; at its end reverse_lr => 5 (it came from the run)
    en(A, 'k_rt_en', 2, 1, 14, 0)
    st(A, 'k_rt_up', """
        bl h_cliff
        cmpwi r3, 0
        beq kt_end
        bl h_clear
    kt_end:
        bl h_end
        cmpwi r3, 0
        beq kt_in
        bl h_rev
        li r4, 5
        bl h_chgi
    kt_in:
        bl h_mv
        li r0, 0
        stw r0, 4(r29)""")

    # collapses (stepped on): kinetic 0, Collapses, ground on, notify_on_death; at its end -> 10 (the 3DS's
    # create_dead_item on frame 1 is left to the removal's defeat path, fix v3, which drops the items)
    en(A, 'k_col_en', 0, 1, 0, 0, extra="mr r3, r31\nlis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctrl\n"
       "li r0, 1\nstw r0, 0x%X(r31)" % (NOTIFY_DEATH >> 16, NOTIFY_DEATH & 0xFFFF, DEFEATED))
    st(A, 'k_col_up', "bl h_end\ncmpwi r3, 0\nbeq epi\nli r4, 10\nb go")

    # ---- Shy Guy (V0 search frames, V1 walk / hold frames, V2 run frames, V3 target, V4 hops / Wait loops,
    # V5 settle frames)
    def look(a, pfx, grp, then):
        """every interval frames (V0) search_target(grp) -> V3; found: `then` (asm, the id in r3)"""
        a.asm("""
        %s_look:
            li r4, %d
            bl h_grp
            lwz r11, 0x%X(r31)
            addi r11, r11, 1
            stw r11, 0x%X(r31)
            cmpw r11, r3
            ble epi
            li r0, 0
            stw r0, 0x%X(r31)
            li r4, %d
            bl h_srch
            stw r3, 0x%X(r31)
            cmpwi r3, -1
            beq epi
            mr r4, r3
            bl h_tchk
            cmpwi r3, 0
            %s""" % (pfx, grp, V(0), V(0), V(0), grp, V(3), then))

    en(A, 'h_wait_en', 2, 1, 15, 0, extra="li r0, 0\nstw r0, 0x%X(r31)" % V(4))
    st(A, 'h_wait_up', """
        bl h_gnd
        cmpwi r3, 0
        bne hw_on
        li r4, 1
        b go
    hw_on:
        bl h_end
        cmpwi r3, 0
        beq hh_look
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)
        cmpwi r3, 2
        blt hw_again
        li r3, 1
        li r4, 100
        bl h_rand
        cmpwi r3, 50
        bgt hw_walk
        bl h_rev
    hw_walk:
        li r4, 4
        b go
    hw_again:
        li r4, 15
        li r5, 0
        bl h_mot1
        b hh_look""" % (V(4), V(4)))
    look(A, 'hh', 0, "beq hl_n\nbl h_rev\nhl_n:\nli r4, 7\nb go")
    en(A, 'h_walk_en', 1, 1, 16, 1, pre=la4("row_heiho_walk") + "\nbl h_en\nbl h_kick",
       extra="lwz r3, 0x%X(r30)\nlwz r4, 0x%X(r30)\nbl h_rand\nstw r3, 0x%X(r31)" % (P(0), P(1), V(1)))
    st(A, 'h_walk_up', """
        bl h_mv
        bl h_gnd
        cmpwi r3, 0
        bne hk_on
        li r4, 1
        b go
    hk_on:
        bl h_wall
        cmpwi r3, 0
        beq hk_cl
        li r4, 6
        b go
    hk_cl:
        lwz r11, 0xC(r31)
        addi r11, r11, -1
        cmplwi r11, 1
        bgt hk_tm
        bl h_cliff
        cmpwi r3, 0
        beq hk_tm
        bl h_mv0
        li r4, 5
        b go
    hk_tm:
        lwz r3, 0x%X(r31)
        addi r3, r3, -1
        stw r3, 0x%X(r31)
        cmpwi r3, 0
        bgt hh_look
        li r4, 3
        b go""" % (V(1), V(1)))
    st(A, 'h_turn_up', """
        bl h_gnd
        cmpwi r3, 0
        bne ht_on
        li r4, 1
        b go
    ht_on:
        bl h_end
        cmpwi r3, 0
        beq epi
        bl h_rev
        lwz r0, 0x%X(r31)
        cmpwi r0, 0
        li r4, 4
        ble ht_g
        li r4, 9
    ht_g:
        b goi""" % V(2))
    en(A, 'h_ntc_en', 5, 0, 12, 1, pre=la4("row_heiho_jump") + "\nbl h_en\nbl h_kick",
       extra="li r0, 1\nstw r0, 0x%X(r31)" % V(4))
    st(A, 'h_ntc_up', """
        bl h_vy0
        bgt epi
        bl h_gnd
        cmpwi r3, 0
        beq epi
        lwz r3, 0x%X(r31)
        cmpwi r3, 2
        blt hn_hop
        li r4, 8
        b goi
    hn_hop:
        addi r3, r3, 1
        stw r3, 0x%X(r31)
        li r4, 5
        bl h_kin""" % (V(4), V(4)))
    en(A, 'h_hold_en', 0, 1, 12, 1, extra="lwz r0, 0x%X(r30)\nstw r0, 0x%X(r31)" % (P(2), V(1)))
    st(A, 'h_hold_up', """
        bl h_gnd
        cmpwi r3, 0
        bne hd_on
        li r4, 1
        b go
    hd_on:
        lwz r3, 0x%X(r31)
        addi r3, r3, -1
        stw r3, 0x%X(r31)
        cmpwi r3, 0
        bgt epi
        lwz r4, 0x%X(r31)
        bl h_tchk
        cmpwi r3, 0
        beq hd_run
        bl h_rev
    hd_run:
        li r4, 9
        b go""" % (V(1), V(1), V(3)))
    en(A, 'h_run_en', 3, 1, 10, 1, pre=la4("row_heiho_run") + "\nbl h_en\nbl h_kick",
       extra="lwz r0, 0x%X(r31)\ncmpwi r0, 0\nbgt hr_e\nlwz r0, 0x%X(r30)\nstw r0, 0x%X(r31)\nhr_e:"
       % (V(2), P(3), V(2)))
    st(A, 'h_run_up', """
        bl h_mv
        bl h_gnd
        cmpwi r3, 0
        bne hr_on
        li r0, 0
        stw r0, 0x%X(r31)
        li r4, 1
        b go
    hr_on:
        lwz r3, 0x%X(r31)
        addi r3, r3, -1
        stw r3, 0x%X(r31)
        cmpwi r3, 0
        bgt hr_w
        li r4, 12
        b go
    hr_w:
        bl h_wall
        cmpwi r3, 0
        bne hr_t
        lwz r11, 0xC(r31)
        addi r11, r11, -1
        cmplwi r11, 1
        bgt hr_look
        bl h_cliff
        cmpwi r3, 0
        beq hr_look
        bl h_mv0
    hr_t:
        li r4, 10
        b go""" % (V(2), V(2), V(2)))
    look(A, 'hr', 1, "beq epi\nli r4, 13\nb go")
    en(A, 'h_wrt_en', 0, 1, 13, 0)
    st(A, 'h_rt_up', "bl h_mv\nb h10_body")
    st(A, 'h_wrt_up', """
    h10_body:
        bl h_gnd
        cmpwi r3, 0
        bne h10_on
        li r4, 1
        b go
    h10_on:
        bl h_cliff
        cmpwi r3, 0
        beq h10_end
        bl h_clear
    h10_end:
        bl h_end
        cmpwi r3, 0
        beq epi
        bl h_rev
        li r4, 9
        b goi""")
    en(A, 'h_brk_en', 2, 1, 11, 0)
    st(A, 'h_brk_up', """
        bl h_mv
        bl h_cliff
        cmpwi r3, 0
        beq hb_g
        bl h_clear
    hb_g:
        bl h_gnd
        cmpwi r3, 0
        bne hb_on
        li r4, 1
        b go
    hb_on:
        bl h_end
        cmpwi r3, 0
        beq epi
        bl h_stop
        cmpwi r3, 0
        beq epi
        li r4, 14
        b go""")
    en(B, 'h_rt_en', 2, 1, 13, 0, rate=P(4))
    # settle after the brake: kinetic 21, ground off, Fall; kinetic flag 1 -> 4 (a 120-frame guard: the Wii U's
    # kinetic 21 is unverified)
    en(B, 'h_set_en', 21, 0, 8, 1, extra="li r0, 0\nstw r0, 0x%X(r31)" % V(5))
    st(B, 'h_set_up', """
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)
        cmpwi r3, 120
        bge hs_walk
        li r4, 1
        bl h_flag
        beq epi
    hs_walk:
        li r4, 4
        b go""" % (V(5), V(5)))

    # ---- Waddle Dee (V0 jump frames)
    en(B, 'd_para_en', 8, 0, 11, 1)
    en(B, 'd_walk_en', 1, 1, 13, 1, rate=P(0))
    st(B, 'd_walk_up', """
        bl h_mv
        bl h_gnd
        cmpwi r3, 0
        bne dw_on
    d_fall:
        lwz r0, 0xC(r31)
        li r4, 2
        cmplwi r0, 1
        ble dw_f
        li r4, 1
    dw_f:
        b go
    dw_on:
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)
        lwz r0, 0x%X(r30)
        cmpw r3, r0
        ble dw_wall
        li r0, 0
        stw r0, 0x%X(r31)
        li r3, 1
        li r4, 100
        bl h_rand
        lwz r0, 0x%X(r30)
        cmpw r3, r0
        ble dw_jump
    dw_wall:
        bl h_wall
        cmpwi r3, 0
        beq dw_cl
        li r3, 1
        li r4, 100
        bl h_rand
        lwz r0, 0x%X(r30)
        cmpw r3, r0
        bgt dw_turn
    dw_jump:
        li r4, 6
        b go
    dw_cl:
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        beq dw_c2
        cmpwi r0, 3
        bne epi
    dw_c2:
        bl h_cliff
        cmpwi r3, 0
        beq epi
    dw_turn:
        li r4, 5
        b go""" % (V(0), V(0), P(1), V(0), P(2), P(3)))
    en(B, 'd_jump_en', 5, 0, 9, 0)
    st(B, 'd_jump_up', "bl h_vy0\nbgt epi\nb d_fall")

    # ---- Waddle Doo: walk (a wall -> 5; every search-0 interval a target behind -> 4)
    en(B, 'o_walk_en', 1, 1, 14, 1)
    st(B, 'o_walk_up', """
        bl h_mv
        lwz r3, 0x%(V7)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V7)X(r31)
        cmpwi r3, 0
        bgt ow_g
        li r4, 8
        b go
    ow_g:
        bl h_gnd
        cmpwi r3, 0
        bne ow_on
        li r4, 1
        b go
    ow_on:
        bl h_wall
        cmpwi r3, 0
        beq ow_look
        li r4, 5
        b go""" % dict(V7=V(7)))
    look(B, 'ow', 0, "beq epi\nli r4, 4\nb go")

    # ---- Churine: walk / jump (initialize first, as the 3DS's vt+0xA0)
    en(B, 'c_walk_en', 1, 1, 11, 1, pre="mr r3, r31\nbl w_init")
    st(B, 'c_walk_up', """
        bl h_mv
        bl h_gnd
        cmpwi r3, 0
        bne cw_on
        li r4, 1
        b go
    cw_on:
        bl h_wall
        cmpwi r3, 0
        beq cw_cl
        li r4, 4
        b go
    cw_cl:
        bl h_cliff
        cmpwi r3, 0
        beq epi
        li r4, 5
        b go""")
    en(B, 'c_jump_en', 5, 0, 7, 1, pre="mr r3, r31\nbl w_init", extra="bl h_sety")

    # ---- fix v3 -----------------------------------------------------------------------------------------------
    B.asm("""
    w_noflip:
        lwz r12, 8(r3)
        li r3, 0
        cmplwi r12, 0x60
        bgelr
        lis r10, 0x%04X
        addi r10, r10, %d
        srwi r11, r12, 5
        slwi r11, r11, 2
        addi r11, r11, 0x18
        lwzx r11, r10, r11
        clrlwi r12, r12, 27
        srw r11, r11, r12
        clrlwi r3, r11, 31
        blr
    twin_flip:
        lwz r0, 8(r3)
        cmplwi r0, 0x50
        blt w_noflip
        li r3, 1
        blr
    cave_rot:
        lwz r0, 8(r31)
        cmplwi r0, 0x50
        bge rot_done
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x60(r12)
        mr r3, r31
        li r4, 1
        li r5, 1
        lwz r12, 0xE0(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctrl
    rot_done:
        lwz r10, 0(r31)
        b 0x%08X
    cave_death:
        lwz r12, 8(r3)
        cmplwi r12, 0x50
        bge death_go
        cmpwi r4, 0
        bne death_go
        lwz r12, 0xE0(r3)
        lis r11, 0x%04X
        addi r11, r11, %d
        cmpw r12, r11
        bne death_conv
        lwz r12, 0x%X(r3)
        cmpwi r12, 0
        beq death_go
    death_conv:
        li r4, 3
    death_go:
        mflr r0
        b 0x%08X
    """ % (ha(D['yawk']), sx(D['yawk']), 0xC + 8 * SET_LR_SLOT, SITE_ROT + 4, ha(D['vt']), sx(D['vt']), DEFEATED,
           SITE_DEATH + 4))
    # ---- T2: the motion data set table (r0 = category, r31 = mgr; r9-r12 free)
    B.asm("cave_t:")
    F.sr_check(B)
    B.asm("bgt t_done")
    for w in WALKERS:
        s, t = D['set_' + w['name']], MOTION_SETS + 4 * w['kind']
        B.asm("lis r11, 0x%04X\naddi r11, r11, %d\nlis r12, 0x%04X\nstw r11, %d(r12)" % (ha(s), sx(s), ha(t), sx(t)))
    B.asm("""
    t_done:
        cmpwi r0, 1
        b 0x%08X
    """ % (SITE_T + 4))
    # ---- S2: param slots (r28 = mgr, r3 the load's result: kept)
    B.asm("cave_s:")
    F.sr_check(B)
    B.asm("""
        bgt s2_done
        lis r12, 0x%04X
        lwz r12, %d(r12)
        cmpwi r12, 0
        beq s2_done
        lwz r11, 0x%X(r12)
    """ % (ha(PARAM_MGR), sx(PARAM_MGR), SLOTS + 4 * SLOT_DONOR))
    for k in KINDS:
        B.asm("stw r11, 0x%X(r12)" % (SLOTS + 4 * k))
    B.asm("""
    s2_done:
        lwz r0, 0x5EC(r28)
        b 0x%08X
    """ % (SITE_S + 4))
    return A, B, code_e(D, en, st, far, lfs), code_f(D, VT_WORDS[0])


def code_e(D, en, st, far, lfs):
    """step 2c (region E): the White Bear's and the Gordo's own states (3DS enemy_fs.cro, addresses in the
    docstring of each), the start variant (SMODE) and helpers"""
    import re

    class Near(Asm):
        """conditional branches to the shared exits (epi / go / goi, in region A: beyond a bc's reach) go
        through local copies"""
        def asm(self, text):
            Asm.asm(self, re.sub(r'\b(b(?:eq|ne|gt|lt|ge|le))(\s+)(epi|go|goi)\b', r'\1\2e_\3', text))
    Ee = Near(CAVE_E)
    Ee.asm("e_epi:\nb epi\ne_go:\nb go\ne_goi:\nb goi")
    # ---- helpers: the start variant 1 (Gordo, start 0x19CB0): set_correct(0), set_lr(0.0, 1, 1) (lr 0: faces the
    # camera); the kinetic energy's second kick (3DS KineticEnergy vt+0x74 -> Wii U vt+0xEC: Behavior::
    # set_kinetic_jump's at 0x026A84A4); the current speed into r1+8 (x, y, z)
    Ee.asm("h_smode:\nmflr r28\nlwz r3, 0(r31)\nlwz r3, 0x30DC(r3)\nli r4, 0")
    far(Ee, SET_CORRECT)
    lfs(Ee, 'f1', 'consts')
    Ee.asm("""
        mr r3, r31
        li r4, 1
        li r5, 1
        lwz r12, 0xE0(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctrl
        mtlr r28
        blr
    h_kick2:
        lwz r12, 0(r31)
        lwz r3, 0x3130(r12)
        lwz r12, 0(r3)
        lwz r12, 0xEC(r12)
        mtctr r12
        lis r4, 0x2000
        ori r4, r4, 4
        bctr
    o_nop:
        blr
    """ % (0xC + 8 * SET_LR_SLOT))

    # ---- Gordo: 1 spin (enter 0x1A180: kinetic -1, ground off, Togetoge loop; the contact attack, P2 entry 0);
    # update 0x1A3FC -> 0x65D20 (writes energy 0 every frame: a speed of (home - position) x 0.5: not ported, see
    # the docs); 3 remove (death state 0: the Gordo is not defeated by damage)
    en(Ee, 'o_spin_en', -1, 0, 0, 1)

    # ---- White Bear (V0 search counter +0x16C, V1 walk timer +0x168, V2 search cool-down +0x178, V4 quakes +0x174,
    # V5 jump frames +0x170)
    # 3 walk (enter 0x7E678, update 0x7E950): kinetic 1, Move loop, V1 = random(P0 60, P1 120), V0 = 0
    en(Ee, 'b_walk_en', 1, 1, 9, 1, extra="lwz r3, 0x%X(r30)\nlwz r4, 0x%X(r30)\nbl h_rand\nstw r3, 0x%X(r31)\n"
       "li r0, 0\nstw r0, 0x%X(r31)" % (P(0), P(1), V(1), V(0)))
    st(Ee, 'b_walk_up', """
        bl h_mv
        bl h_gnd
        cmpwi r3, 0
        bne bw_on
        li r4, 1
        b go
    bw_on:
        bl h_wall
        cmpwi r3, 0
        bne bw_turn
        bl h_cliff
        cmpwi r3, 0
        beq bw_cnt
    bw_turn:
        li r4, 5
        b go
    bw_cnt:
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(V0)X(r31)
        lwz r3, 0x%(V2)X(r31)
        cmpwi r3, 0
        ble bw_srch
        addi r3, r3, -1
        stw r3, 0x%(V2)X(r31)
        cmpwi r3, 0
        bgt bw_tm
    bw_srch:
        li r4, 1
        bl h_grp
        lwz r0, 0x%(V0)X(r31)
        cmpw r3, r0
        bge bw_tm
        li r0, 0
        stw r0, 0x%(V0)X(r31)
        li r4, 1
        bl h_srch
        cmpwi r3, 0
        blt bw_tm
        li r4, 6
        b go
    bw_tm:
        lwz r3, 0x%(V1)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V1)X(r31)
        cmpwi r3, 0
        bgt epi
        li r4, 4
        b go""" % dict(V0=V(0), V1=V(1), V2=V(2)))
    # 4 special turn (enter 0x7E5C8: kinetic 0, SpecialTurn; update 0x7E8A8 = 5's: at its end reverse_lr => 3)
    en(Ee, 'b_sturn_en', 0, 1, 14, 0)
    # 6 quake hold (enter 0x7EB34: kinetic 0, QuakeHold at P0 f9 1.5, V4 = 0; update 0x7F10C: at its end
    # is_in_view_area -> 7, else -> 3; the camera test is not ported: in view)
    en(Ee, 'b_hold_en', 0, 1, 11, 0, rate=P(2), extra="li r0, 0\nstw r0, 0x%X(r31)" % V(4))
    st(Ee, 'b_hold_up', "bl h_end\ncmpwi r3, 0\nbeq epi\nli r4, 7\nb go")
    # 7 quake jump (enter 0x7ED14: E+0x20 0, +0x24 f10, +0x28 0, +0x2C f10, +0x3C 0.1, the kick, kinetic 5, ground
    # off, QuakeUp, V5 = 0; update 0x7F1F8: V5++, the speed's y <= 0 -> 8)
    en(Ee, 'b_up_en', 5, 0, 13, 0, pre="""bl h_ebase
        li r0, 0
        stw r0, 0x20(r10)
        stw r0, 0x28(r10)
        lwz r0, 0x%X(r30)
        stw r0, 0x24(r10)
        stw r0, 0x2C(r10)
        lwz r0, 0x%X(r30)
        stw r0, 0x3C(r10)
        bl h_kick2""" % (P(3), P(12)), extra="li r0, 0\nstw r0, 0x%X(r31)" % V(5))
    st(Ee, 'b_up_up', """
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)
        bl h_vy0
        bgt epi
        li r4, 8
        b go""" % (V(5), V(5)))
    # 8 quake fall (enter 0x7EBB4: E+0x20 / +0x24 = the current speed, +0x28 0, +0x2C f12 3, +0x3C f11 1, the kick,
    # kinetic 5, ground off, QuakeFall; update 0x7F168: V5++; on the ground: V5 < f14 (180) => 9, else => 2)
    pre8 = "addi r3, r1, 8\nmr r4, r31\nlis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctrl\n" \
           % (GET_SPEED >> 16, GET_SPEED & 0xFFFF)
    en(Ee, 'b_fall_en', 5, 0, 10, 0, pre=pre8 + """bl h_ebase
        lwz r0, 8(r1)
        stw r0, 0x20(r10)
        lwz r0, 0xC(r1)
        stw r0, 0x24(r10)
        li r0, 0
        stw r0, 0x28(r10)
        lwz r0, 0x%X(r30)
        stw r0, 0x2C(r10)
        lwz r0, 0x%X(r30)
        stw r0, 0x3C(r10)
        bl h_kick2""" % (P(5), P(4)))
    st(Ee, 'b_fall_up', """
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)
        mr r28, r3
        bl h_gnd
        cmpwi r3, 0
        beq epi
        lwz r0, 0x%X(r30)
        li r4, 9
        cmpw r0, r28
        bgt bf_go
        li r4, 2
    bf_go:
        b goi""" % (V(5), V(5), P(7)))
    # 9 quake landing (enter 0x7EE74: kinetic 0, ground on, QuakeLanding at f13 (1.0), f16 (0.5) after the first,
    # request_quake(7), the absolute quake hit, effects 0x7400000 / 0x7400001: not ported; V4++; update 0x7F244: at
    # its end, V4 < f17 (3) and success_by_percent(f15 / 2^(V4 - 1)) -> 7 (jump again), else V2 = f18 (60), -> 3;
    # the percentage as an integer: 50 >> (V4 - 1) is exact for V4 1 / 2, the only ones it is tested with)
    st(Ee, 'b_land_en', """
        li r4, 0
        bl h_kin
        li r4, 1
        bl h_att
        lfs f2, 0x%(P6)X(r30)
        lwz r0, 0x%(V4)X(r31)
        cmpwi r0, 0
        ble bl_rate
        lfs f2, 0x%(P9)X(r30)
    bl_rate:
        li r4, 12
        li r5, 0
        bl h_mot
        mr r3, r31
        li r4, %(QK)d
        lis r12, 0x%(RQH)04X
        ori r12, r12, 0x%(RQL)04X
        mtctr r12
        bctrl
        bl b_quake
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lwz r12, 0(r31)
        lwz r5, 0x311C(r12)
        addi r5, r5, 0x10
        mr r3, r31
        lis r4, 0x740
        addi r6, r1, 8
        lfs f1, 0x%(P13)X(r30)
        lis r12, 0x%(REH)04X
        ori r12, r12, 0x%(REL)04X
        mtctr r12
        bctrl
        mr r3, r31
        lis r4, 0x740
        ori r4, r4, 1
        addi r5, r1, 8
        lfs f1, 0x%(P14)X(r30)
        lis r12, 0x%(RZH)04X
        ori r12, r12, 0x%(RZL)04X
        mtctr r12
        bctrl
        lwz r3, 0x%(V4)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(V4)X(r31)""" % dict(P6=P(6), P9=P(9), V4=V(4), QK=QUAKE_KIND, RQH=REQ_QUAKE >> 16,
                                        RQL=REQ_QUAKE & 0xFFFF, REH=REQ_EFFECT >> 16, REL=REQ_EFFECT & 0xFFFF,
                                        RZH=REQ_EFFECT0 >> 16, RZL=REQ_EFFECT0 & 0xFFFF, P13=P(13), P14=P(14)))
    # ---- Waddle Doo's leave (v2; the 3DS state 9: enter 0x7CEC0 = Fall at rate 0, init_common_leave(P6) code.bin
    # 0x7B23B4: the leave time, energy +0x30 = -p1 / +0x34 = p2 and kinetic 15 (0x7B4E84), ground off,
    # set_correct(0), disable_jostle (not ported), the common leave effect 0x8000005 following node 0 at (0, 3, 0)
    # scale 0.85 (EnemyManager +0x5F8 clear); update 0x7D444 / update_common_leave 0x7B40B0: the time counts
    # down, at 0 the effect is removed and -> remove (no defeat: DEFEATED stays 0)); V6 the time, V5 the effect
    st(Ee, 'o_leave_en', """
        li r4, 10
        li r5, 0
        bl h_mot0
        lwz r0, 0x%(P0)X(r30)
        stw r0, 0x%(V6)X(r31)
        bl h_ebase
        lwz r0, 0x%(P1)X(r30)
        stw r0, 0x30(r10)
        lwz r0, 0x%(P2)X(r30)
        stw r0, 0x34(r10)
        li r4, 15
        bl h_kin
        li r4, 0
        bl h_att
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0
        lis r12, 0x%(SCH)04X
        ori r12, r12, 0x%(SCL)04X
        mtctr r12
        bctrl
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0x10(r1)
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        stw r0, 0x1C(r1)
        lwz r0, 0x%(P3)X(r30)
        stw r0, 0xC(r1)
        mr r3, r31
        lis r4, 0x800
        ori r4, r4, 5
        li r5, 0
        addi r6, r1, 8
        addi r7, r1, 0x14
        lfs f1, 0x%(P4)X(r30)
        lis r12, 0x%(RFH)04X
        ori r12, r12, 0x%(RFL)04X
        mtctr r12
        bctrl
        stw r3, 0x%(V5)X(r31)""" % dict(P0=P(0), P1=P(1), P2=P(2), P3=P(3), P4=P(4), V5=V(5), V6=V(6),
                                        SCH=SET_CORRECT >> 16, SCL=SET_CORRECT & 0xFFFF, RFH=REQ_FOLLOW >> 16,
                                        RFL=REQ_FOLLOW & 0xFFFF))
    st(Ee, 'o_leave_up', """
        lwz r3, 0x%(V6)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V6)X(r31)
        cmpwi r3, 0
        bgt epi
        mr r3, r31
        lwz r4, 0x%(V5)X(r31)
        lis r12, 0x%(RMH)04X
        ori r12, r12, 0x%(RML)04X
        mtctr r12
        bctrl
        li r0, 0
        stw r0, 0x%(V5)X(r31)
        lwz r4, 0x%(RM)X(r30)
        b go""" % dict(V5=V(5), V6=V(6), RMH=REMOVE_EFFECT >> 16, RML=REMOVE_EFFECT & 0xFFFF, RM=CF['REMOVE']))
    # the landing's absolute hit (v2; the 3DS 0x7EF04-0x7F01C: set_attack_absolute_data(P6), then for the fighter
    # entries in order the first on the ground gets hit_attack_absolute(P6 id 0, entry), once): the fighter table
    # (slots 0-3, live) as the stomp test reads it; on the ground = MSC StatusModule(1) (the situation) == 0; the
    # enemy's AttackModule (acc+0x30C8, AttackModuleImpl) through its MSC entry vt+0x334 as the ACMD
    # Throw_Specifier / Throw_Applier handlers (0x02BE6E88 / 0x02BE6FCC) do: op 0x2716 set_abs(kind 0, part 0, the
    # P6 values: 10.0, 90, 100, 0, 40, ...: ABS_WORDS), then op 0x271D (0x02C0B8E4 -> vt+0x74 hit_absolute(kind 0,
    # node 0, the fighter's object id = [its accessor + 0], hit group 0, 0))
    Ee.asm("""
    b_quake:
        mflr r0
        stwu r1, -0xA0(r1)
        stw r0, 0xA4(r1)
        stmw r26, 0x88(r1)
        lis r12, 0x%(FH)04X
        lwz r12, %(FL)d(r12)
        cmpwi r12, 0
        beq q_out
        lwz r26, 0(r12)
        cmpwi r26, 0
        beq q_out
        lwz r27, 8(r26)
        li r28, 0
    q_loop:
        cmpw r28, r27
        bge q_out
        cmpwi r28, 4
        bge q_out
        lwz r12, 0(r26)
        mulli r11, r28, 0x%(ENT)X
        add r12, r12, r11
        lbz r11, 0x1E(r12)
        cmplwi r11, 4
        blt q_next
        lwz r29, 0xC(r12)
        cmpwi r29, 0
        beq q_next
        li r0, 0
        stw r0, 8(r1)
        stw r29, 0xC(r1)
        li r0, 1
        stw r0, 0x10(r1)
        stw r0, 0x1C(r1)
        addi r0, r1, 0x10
        stw r0, 0x18(r1)
        addi r3, r1, 8
        addi r4, r1, 0x18
        lis r12, 0x%(MH)04X
        ori r12, r12, 0x%(ML)04X
        mtctr r12
        bctrl
        cmpwi r3, 0
        beq q_hit
    q_next:
        addi r28, r28, 1
        b q_loop
    q_hit:
        lwz r30, 0(r31)
        lwz r30, 0x30C8(r30)
        cmpwi r30, 0
        beq q_out
        lis r11, 0x%(AH)04X
        addi r11, r11, %(AL)d
        addi r12, r1, 0x1C
        li r0, %(NW)d
        mtctr r0
    q_copy:
        lwz r0, 0(r11)
        stwu r0, 4(r12)
        addi r11, r11, 4
        bdnz q_copy
        li r0, %(NW)d
        bl q_msc
        li r0, 0x271D
        stw r0, 0x20(r1)
        li r0, 0
        stw r0, 0x24(r1)
        stw r0, 0x28(r1)
        stw r0, 0x30(r1)
        stw r0, 0x34(r1)
        lwz r0, 0(r29)
        stw r0, 0x2C(r1)
        li r0, 6
        bl q_msc
    q_out:
        lmw r26, 0x88(r1)
        lwz r0, 0xA4(r1)
        mtlr r0
        addi r1, r1, 0xA0
        blr
    q_msc:
        stw r0, 0x1C(r1)
        addi r0, r1, 0x20
        stw r0, 0x18(r1)
        mr r3, r30
        addi r4, r1, 0x18
        lwz r12, 0(r30)
        lwz r12, 0x334(r12)
        mtctr r12
        bctr
    """ % dict(FH=ha(FIGHTERS), FL=sx(FIGHTERS), ENT=FIGHTER_ENTRY, MH=MSC_STATUS >> 16, ML=MSC_STATUS & 0xFFFF,
               NW=len(ABS_WORDS), AH=ha(D['abs_words']), AL=sx(D['abs_words'])))
    st(Ee, 'b_land_up', """
        bl h_end
        cmpwi r3, 0
        beq epi
        lwz r3, 0x%(V4)X(r31)
        lwz r0, 0x%(P10)X(r30)
        cmpw r0, r3
        ble bl_done
        addi r5, r3, -1
        lwz r28, 0x%(P8)X(r30)
        srw r28, r28, r5
        li r3, 0
        li r4, 99
        bl h_rand
        cmpw r3, r28
        bge bl_done
        li r4, 7
        b go
    bl_done:
        lwz r0, 0x%(P11)X(r30)
        stw r0, 0x%(V2)X(r31)
        li r4, 3
        b go""" % dict(V4=V(4), P10=P(10), P8=P(8), P11=P(11), V2=V(2)))
    return Ee


def code_f(D, vtw):
    """step 2e (region G): the fliers' framework (the vtable's dispatching slots 10 / 27 / 41 / 69, the leave) and
    each flier's own states (3DS enemy_fs.cro addresses in the comments). Conditional branches to the shared exits
    (region A) use .far."""
    G = Asm(CAVE_G)

    def far(t):
        G.asm("lis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctrl" % (t >> 16, t & 0xFFFF))

    def st(label, body):
        G.asm("%s:\nmflr r0\nbl pro\n%s\nb epi" % (label, body))

    def lfs(fr, label, off=0):
        G.asm("lis r12, 0x%04X\nlfs %s, %d(r12)" % (ha(D[label] + off), fr, sx(D[label] + off)))

    orig = lambda k: vtw[(0xC + 8 * k) // 4]  # noqa: E731
    # ---- the vtable's dispatching slots: the kind's CFG handler (FSTART / FDMG / F27 / F69), else BehaviorImpl's
    G.asm("""
    f_v41:
        lwz r12, 0x168(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctr
    """ % CF['FSTART'])
    for k, f in ((10, 'FDMG'), (27, 'F27'), (69, 'F69')):
        G.asm("""
        f_v%d:
            lwz r12, 0x168(r3)
            lwz r12, 0x%X(r12)
            cmpwi r12, 0
            bne f_v%d_go
            lis r12, 0x%04X
            ori r12, r12, 0x%04X
        f_v%d_go:
            mtctr r12
            bctr
        """ % (k, CF[f], k, orig(k) >> 16, orig(k) & 0xFFFF, k))
    # ---- shared helpers
    # f_aer: r3 = the aerial module; f_pass1: set_passable_check(1); f_gl: r3 = the kind's gl entry (Behavior +8
    # kind, +0xC variation; the Wii U's own lookup, e.g. 0x02DB4EF0)
    G.asm("""
    f_pass1:
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 1
        b 0x%08X
    f_gl:
        lis r12, 0x%04X
        lwz r12, %d(r12)
        lwz r9, 8(r31)
        lwz r10, 0xC(r31)
        slwi r9, r9, 3
        add r9, r9, r10
        slwi r9, r9, 2
        add r9, r9, r12
        lwz r9, 0x%X(r9)
        mulli r9, r9, 0x228
        lwz r3, 0x%X(r12)
        add r3, r3, r9
        blr
    f_kflag:
        lwz r12, 0(r31)
        lwz r12, 0x3130(r12)
        lwz r12, 8(r12)
        lwz r12, 0(r12)
        lwz r12, 0x14(r12)
        blr
    """ % (SET_PASSABLE, ha(PARAM_MGR), sx(PARAM_MGR), GL_INDEX, GL_BASE))
    # f_hitret: r3 = hit_return_frame() (3DS 0x9EA9B0): int(float(int gl[+0x154]) * factor), factor = HIT_FACTOR
    # (the 3DS 0x9EB4C0's Wii U copy); uses r1+8..+0x17 of the caller's frame
    G.asm("""
    f_hitret:
        mflr r0
        stw r0, 0x1C(r1)
        bl f_gl
        lwz r0, 0x154(r3)
        xoris r0, r0, 0x8000
        stw r0, 0xC(r1)
        lis r0, 0x4330
        stw r0, 8(r1)
        lfd f1, 8(r1)
    """)
    G.asm("lis r12, 0x%04X\nlfd f0, %d(r12)" % (ha(D['fconsts']), sx(D['fconsts'])))
    G.asm("""
        fsub f1, f1, f0
        frsp f1, f1
        stfs f1, 0x10(r1)
        mr r3, r31
        bl 0x%08X
        lfs f0, 0x10(r1)
        fmuls f1, f0, f1
        fctiwz f1, f1
        stfd f1, 8(r1)
        lwz r3, 0xC(r1)
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """ % HIT_FACTOR)
    # the common leave (3DS Behavior::init_common_leave 0x7B23B4 with the kind's InnerEnemyLeaveParam at CFG LVP:
    # frames, the energy's +0x30 (-speed), +0x34, the leave effect 0x8000005's offset y and scale): V6 = frames,
    # kinetic 15, ground off, set_correct(0), the effect following node 0 -> V5; update: o_leave_up (step 2c v2)
    st('f_leave_en', """
        lwz r28, 0x%(LVP)X(r30)
        add r28, r28, r30
        lwz r0, 0(r28)
        stw r0, 0x%(V6)X(r31)
        bl h_ebase
        lwz r0, 4(r28)
        stw r0, 0x30(r10)
        lwz r0, 8(r28)
        stw r0, 0x34(r10)
        li r4, 15
        bl h_kin
        li r4, 0
        bl h_att
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0
        bl 0x%(SC)08X
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0x10(r1)
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        stw r0, 0x1C(r1)
        lwz r0, 0xC(r28)
        stw r0, 0xC(r1)
        mr r3, r31
        lis r4, 0x800
        ori r4, r4, 5
        li r5, 0
        addi r6, r1, 8
        addi r7, r1, 0x14
        lfs f1, 0x10(r28)
        lis r12, 0x%(RFH)04X
        ori r12, r12, 0x%(RFL)04X
        mtctr r12
        bctrl
        stw r3, 0x%(V5)X(r31)""" % dict(LVP=CF['LVP'], V6=V(6), V5=V(5), SC=SET_CORRECT, RFH=REQ_FOLLOW >> 16,
                                       RFL=REQ_FOLLOW & 0xFFFF))
    # f_unleave: finalize_common_leave (3DS 0x7B475C: the leave effect removed, the count 0) when a leave runs, then
    # set_correct(5) (as Ghos's / Furiijio's slot 69 do after it)
    G.asm("""
    f_unleave:
        lwz r0, 0x%(V6)X(r31)
        cmpwi r0, 0
        blelr
        mflr r0
        stw r0, 0x1C(r1)
        mr r3, r31
        lwz r4, 0x%(V5)X(r31)
        lis r12, 0x%(RMH)04X
        ori r12, r12, 0x%(RML)04X
        mtctr r12
        bctrl
        li r0, 0
        stw r0, 0x%(V5)X(r31)
        stw r0, 0x%(V6)X(r31)
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 5
        lwz r0, 0x1C(r1)
        mtlr r0
        b 0x%(SC)08X
    """ % dict(V5=V(5), V6=V(6), RMH=REMOVE_EFFECT >> 16, RML=REMOVE_EFFECT & 0xFFFF, SC=SET_CORRECT))

    # ---- Ghos (kind 0x11; enemy_fs.cro create 0x11560, table 0x10D350). V0 the slip-homing timer (+0x1EC), V1
    # the leave timer (+0x1E8), V2 the stun frames (+0x1E4), V3 the target (+0x1F0), V4 the follow effect (+0x1FC),
    # V5 / V6 the common leave's effect / frames. P: 0 / 1 timer range (20, 40), 2 choice % (96), 3 bounce speed
    # (0.6), 4 max speed (0.8), 5 leave frames (1200), 6 0.1 (a literal), 7-12 / 13-18 the two P7 slip-homing sets,
    # 19-23 the leave param (P6: 100, -0.02, 30, 3, 0.85)
    # start 0x109C0: the aerial module (its ctor: the 3DS ctor 0x11598's), set_rhombus, set_lr(0, 1, 1) (lr 0: faces
    # the camera), V3 = the nearest fighter, +0x10 = posture lr, +0x14 / +0x18 = 0, V1 = 1200, -> 1, the body effect
    # 0x7110000 following node 0 -> V4 (set_node_visibility(1, 1) / (0, 0) and play_se(0x8A60000) not ported)
    G.asm("f_ghos_start:\nmflr r0\nbl pro\naddi r3, r31, 0x%X\nlwz r4, 0(r31)\nbl 0x%08X\nmr r3, r31" % (AER, AER_CTOR))   # step 2f: set_rhombus(this) (r3 was the aerial module)
    far(SET_RHOMBUS)
    lfs('f1', 'consts')
    G.asm("""
        mr r3, r31
        li r4, 1
        li r5, 1
        lwz r12, 0xE0(r3)
        lwz r12, 0x%(LR)X(r12)
        mtctr r12
        bctrl
        bl h_near
        stw r3, 0x%(V3)X(r31)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x60(r12)
        stw r0, 0x10(r31)
        li r0, 0
        stw r0, 0x14(r31)
        stw r0, 0x18(r31)
        stw r0, 0x%(GI)X(r31)
        stw r0, 0x%(GD)X(r31)
        lwz r0, 0x%(P5)X(r30)
        stw r0, 0x%(V1)X(r31)
        li r4, 1
        bl h_chg
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        stw r0, 0x1C(r1)
        mr r3, r31
        lis r4, 0x711
        li r5, 0
        addi r6, r1, 8
        addi r7, r1, 0x14
    """ % dict(LR=0xC + 8 * SET_LR_SLOT, V3=V(3), P5=P(5), V1=V(1), GI=GH_IMM, GD=GH_DMG))
    lfs('f1', 'consts', 4)
    far(REQ_FOLLOW)
    G.asm("stw r3, 0x%X(r31)\nb epi" % V(4))
    # L66BA4: V0 = random(P0, P1); random_choice(100 - P2, P2, 0, 0) (3DS 0x7B0DC4: weights -> index: 4 % index 0,
    # 96 % index 1) -> set_mode_slip_homing(P7 set [index]: s0 +0, s1 +0xC, s2 +8, s3 +0x14, s4 +4, s5 +0x10); called
    # from a state (its frame's +0x1C keeps the return, +0x10 / +0x14 the speed). Step 2g v3: index 1 (96 %) is the
    # SECOND set (+0x18: P13-18, max 1.5 a frame: the homing that charges at the target), index 0 (4 %) the slow
    # drift (P7-12, max 0.052 / 0.15); steps 2e-2g v2 had them swapped (Ghos drifted 96 % of the time).
    # Step 2g v2: the Wii U's 0x02DB28E4 is set_mode_HOMING (energy 0's init with speed 0); the 3DS's slip homing
    # 0x5F5F58 inits it with the current speed (energy +4 / +8), so the speed is kept: saved before, set back with
    # set_current_speed 0x02DB2BC0 after (else every re-pick, each 20-40 frames, stopped Ghos dead)
    G.asm("""
    f_gpick:
        mflr r0
        stw r0, 0x1C(r1)
        lwz r3, 0x%(P0)X(r30)
        lwz r4, 0x%(P1)X(r30)
        bl h_rand
        stw r3, 0x%(V0)X(r31)
        li r3, 0
        li r4, 99
        bl h_rand
        lwz r0, 0x%(P2)X(r30)
        addi r12, r30, 0x%(P13)X
        cmpw r3, r0
        blt gp_set
        addi r12, r30, 0x%(P7)X
    gp_set:
        lfs f1, 0(r12)
        lfs f2, 0xC(r12)
        lfs f3, 8(r12)
        lfs f4, 0x14(r12)
        lfs f5, 4(r12)
        lfs f6, 0x10(r12)
        lwz r12, 0x%(E0)X(r31)
        lfs f0, 0(r12)
        stfs f0, 0x10(r1)
        lfs f0, 4(r12)
        stfs f0, 0x14(r1)
        addi r3, r31, 0x%(AER)X
        bl 0x%(SH)08X
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 0x10
        bl 0x%(SS)08X
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """ % dict(P0=P(0), P1=P(1), V0=V(0), P2=P(2), P7=P(7), P13=P(13), AER=AER, SH=AER_SLIP_HOMING, E0=AER + 4,
               SS=AER_SET_SPEED))
    # step 2g v3, slot 55 (0x10BA0, every frame after the state update; vtable 0xCB840 + 55 x 4 = 0xCB91C): in states
    # other than 0 / 2 / 4 / 5 with a target (V3, 3DS +0x1F0): d = target - posture, normalised by its length (x, y);
    # rx = -dy x P26 (P@0xA4 30.0), ry = dx x P26 (degrees); set_rotation_order_xyz (not mapped: the Wii U's default
    # order assumed); node 2 (RotN) set_node_rotate((rx, ry, -ry) x 0.0174533, 0) (+ ModelModule vt+0xC4 on a
    # change); the posture's rotation (count +0x54 > 1: [+0x58] + 0x38, the Wii U's layout as 0x02DC3CC4 writes it;
    # 3DS +0x3C) = (rx, ry, 0), on a change ModelModule +0x20 = 0 and MotionModule +0xFC 1 -> 2 (as 0x02DC3D28)
    G.asm("""
    f_g55:
        mflr r0
        bl pro
        lwz r0, 4(r31)
        cmplwi r0, 5
        bgt g55_go
        cmpwi r0, 1
        beq g55_go
        cmpwi r0, 3
        bne g55_out
    g55_go:
        lwz r5, 0x%(V3)X(r31)
        cmpwi r5, -1
        beq g55_out
        addi r3, r1, 8
        mr r4, r31
    """ % dict(V3=V(3)))
    far(GET_TARGET_POS)
    G.asm("""
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f3, 8(r1)
        lfs f0, 0x10(r12)
        fsubs f3, f3, f0
        lfs f4, 0xC(r1)
        lfs f0, 0x14(r12)
        fsubs f4, f4, f0
        lfs f5, 0x10(r1)
        lfs f0, 0x18(r12)
        fsubs f5, f5, f0
        fmuls f2, f3, f3
        fmadds f2, f4, f4, f2
        fmadds f2, f5, f5, f2
        lis r12, 0x%(KH)04X
        lfs f0, %(KL)d(r12)
        fcmpu cr0, f2, f0
        beq g55_n
        stfs f3, 0x14(r1)
        stfs f4, 0x18(r1)
        fmr f1, f2
        bl 0x%(SQ)08X
        lis r12, 0x%(KH)04X
        lfs f0, %(KL4)d(r12)
        fdivs f0, f0, f1
        lfs f3, 0x14(r1)
        fmuls f3, f3, f0
        lfs f4, 0x18(r1)
        fmuls f4, f4, f0
    g55_n:
        lfs f0, 0x%(P26)X(r30)
        fmuls f6, f4, f0
        fneg f6, f6
        fmuls f7, f3, f0
        stfs f6, 0x14(r1)
        stfs f7, 0x18(r1)
        lfs f0, 0x%(P27)X(r30)
        fmuls f1, f6, f0
        stfs f1, 8(r1)
        fmuls f1, f7, f0
        stfs f1, 0xC(r1)
        fneg f1, f1
        stfs f1, 0x10(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30F0(r3)
        li r4, 2
        addi r5, r1, 8
        li r6, 0
        bl 0x%(SNR)08X
        cmpwi r3, 0
        beq g55_p
        bl fu_dirty
    g55_p:
        lwz r9, 0(r31)
        lwz r10, 0x311C(r9)
        lwz r0, 0x54(r10)
        cmplwi r0, 1
        ble g55_out
        lwz r11, 0x58(r10)
        addi r11, r11, 0x38
        lfs f6, 0x14(r1)
        lfs f7, 0x18(r1)
        lis r12, 0x%(KH)04X
        lfs f8, %(KL)d(r12)
        li r8, 1
        lfs f0, 0(r11)
        fcmpu cr0, f0, f6
        bne g55_s
        lfs f0, 4(r11)
        fcmpu cr0, f0, f7
        bne g55_s
        lfs f0, 8(r11)
        fcmpu cr0, f0, f8
        bne g55_s
        li r8, 0
    g55_s:
        stfs f6, 0(r11)
        stfs f7, 4(r11)
        stfs f8, 8(r11)
        cmpwi r8, 0
        beq g55_out
        lwz r11, 0x3118(r9)
        li r0, 0
        stw r0, 0x20(r11)
        lwz r11, 0x30F0(r9)
        lwz r0, 0xFC(r11)
        cmpwi r0, 1
        bne g55_out
        li r0, 2
        stw r0, 0xFC(r11)
    g55_out:
        b epi
    """ % dict(KH=ha(D['consts']), KL=sx(D['consts']), KL4=sx(D['consts'] + 4), SQ=SQRTF, P26=P(26), P27=P(27),
               SNR=SET_NODE_ROT))
    # step 2g v3: set_lr / reverse_lr (vtable slots 49 / 50) -> the game's, then w_yaw: for a YAW_FLIP kind (< 0x50)
    # whose posture lr is 1 and rotation (+0x64) the 90 set_lr / reverse_lr just wrote: -90 (the lr -1 view, which the
    # 3DS mirrors for lr 1), ModelModule +0x20 = 0 and MotionModule +0xFC 1 -> 2 (set_lr's own marks, 0x026A7930)
    G.asm("""
    w_slr:
        lis r12, 0x%(SH)04X
        ori r12, r12, 0x%(SL)04X
        b w_lrw
    w_rlr:
        lis r12, 0x%(RH)04X
        ori r12, r12, 0x%(RL)04X
    w_lrw:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        mr r31, r3
        mtctr r12
        bctrl
        mr r3, r31
        bl w_yaw
        lwz r0, 0x24(r1)
        mtlr r0
        lwz r31, 0x1C(r1)
        addi r1, r1, 0x20
        blr
    w_yaw:
        lwz r12, 8(r3)
        cmplwi r12, 0x60
        bgelr
        lis r10, 0x%(YH)04X
        addi r10, r10, %(YL)d
        srwi r11, r12, 5
        slwi r11, r11, 2
        addi r11, r11, 0xC
        lwzx r11, r10, r11
        clrlwi r12, r12, 27
        srw r11, r11, r12
        andi. r11, r11, 1
        beqlr
        lwz r9, 0(r3)
        lwz r8, 0x311C(r9)
        lfs f0, 0x60(r8)
        lfs f2, 0(r10)
        fcmpu cr0, f0, f2
        bnelr
        lfs f0, 0x64(r8)
        lfs f2, 4(r10)
        fcmpu cr0, f0, f2
        bnelr
        lfs f2, 8(r10)
        stfs f2, 0x64(r8)
        lwz r11, 0x3118(r9)
        li r0, 0
        stw r0, 0x20(r11)
        lwz r11, 0x30F0(r9)
        lwz r0, 0xFC(r11)
        cmpwi r0, 1
        bnelr
        li r0, 2
        stw r0, 0xFC(r11)
        blr
    """ % dict(SH=SET_LR >> 16, SL=SET_LR & 0xFFFF, RH=REVERSE_LR >> 16, RL=REVERSE_LR & 0xFFFF,
               YH=ha(D['yawk']), YL=sx(D['yawk'])))
    # L1120C, the wall bounce: on any contact (is_touch(0xFF)) v = energy 0's speed, n = get_ground_normal(0xFF);
    # r = |v|^2 / (P4 * P4); r < 0.1 (and r <= 1): nothing; else v reflected on n (v - 2 (n.v) n), normalised,
    # times P3 * min(r, 1) -> set_current_speed
    G.asm("""
    f_gbounce:
        mflr r0
        stw r0, 0x1C(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0xFF
        bl 0x%(TOUCH)08X
        cmpwi r3, 0
        beq gb_out
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        lwz r3, 0x18(r3)
        li r4, 0xFF
        bl 0x%(GN)08X
        stw r3, 8(r1)
        stw r4, 0xC(r1)
        lwz r12, 0x%(E0)X(r31)
        lfs f1, 0(r12)
        lfs f2, 4(r12)
        fmuls f5, f1, f1
        fmadds f5, f2, f2, f5
        lfs f6, 0x%(P4)X(r30)
        fmuls f6, f6, f6
        fdivs f5, f5, f6
        lfs f6, 0x%(ONE)X(r30)
        fcmpu cr0, f5, f6
        bgt gb_clamp
        lfs f7, 0x%(P6)X(r30)
        fcmpu cr0, f5, f7
        blt gb_out
        b gb_refl
    gb_clamp:
        fmr f5, f6
    gb_refl:
        lfs f3, 8(r1)
        lfs f4, 0xC(r1)
        fmuls f8, f3, f1
        fmadds f8, f4, f2, f8
        fadds f8, f8, f8
        fnmsubs f1, f3, f8, f1
        fnmsubs f2, f4, f8, f2
        lfs f0, 0x%(P3)X(r30)
        fmuls f5, f5, f0
        stfs f1, 8(r1)
        stfs f2, 0xC(r1)
        stfs f5, 0x10(r1)
        fmuls f1, f1, f1
        fmadds f1, f2, f2, f1
        lfs f0, 0x%(ZERO)X(r30)
        fcmpu cr0, f1, f0
        beq gb_set
        bl 0x%(SQ)08X
        lfs f5, 0x10(r1)
        fdivs f5, f5, f1
        lfs f1, 8(r1)
        lfs f2, 0xC(r1)
        fmuls f1, f1, f5
        fmuls f2, f2, f5
        stfs f1, 8(r1)
        stfs f2, 0xC(r1)
    gb_set:
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 8
        bl 0x%(SS)08X
    gb_out:
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """ % dict(TOUCH=IS_TOUCH, GN=GROUND_NORMAL, E0=AER + 4, P4=P(4), ONE=P(24), P6=P(6), P3=P(3), ZERO=P(25),
               SQ=SQRTF, AER=AER, SS=AER_SET_SPEED))
    # 1 fly (enter 0x1091C, update 0x10E24): kinetic 26, f_gpick, ground off, passable on, FlyHoming (loop), the
    # aerial target = V3 (set_target: +0x30 id, +0x40 offset 0, +0x2C 0). Update: the aerial update, V0 runs out ->
    # f_gpick, the bounce, V1 runs out -> 3 (leave). Contact attack: P2 entry 1 (set_attack_data(1))
    st('f_g1_en', """
        li r4, 26
        bl h_kin
        bl f_gpick
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 1
        li r5, 1
        bl h_mot1
        lwz r0, 0x%(V3)X(r31)
        stw r0, 0x%(T)X(r31)
        li r0, 0
        stw r0, 0x%(O)X(r31)
        stw r0, 0x%(O4)X(r31)
        stw r0, 0x%(O8)X(r31)
        stb r0, 0x%(F)X(r31)""" % dict(V3=V(3), T=AER + 0x30, O=AER + 0x40, O4=AER + 0x44, O8=AER + 0x48,
                                      F=AER + 0x2C))
    st('f_g1_up', """
        addi r3, r31, 0x%(AER)X
        bl 0x%(UPD)08X
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V0)X(r31)
        cmpwi r3, 0
        bgt g1_b
        bl f_gpick
    g1_b:
        bl f_gbounce
        lwz r3, 0x%(V1)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V1)X(r31)
        cmpwi r3, 0
        bgt.far epi
        li r4, 3
        b go""" % dict(AER=AER, UPD=AER_UPDATE, V0=V(0), V1=V(1)))
    # 2 stun (enter 0x10AD0, update 0x10EE4): kinetic 16, ground off, passable on, DamageStart (once), V2 =
    # hit_return_frame(), the kinetic flag 0x80 set (set_node_visibility(1, 0) / (0, 1): not ported); V2 runs out ->
    # flag 0x80 cleared, -> 1
    st('f_g2_en', """
        li r4, 16
        bl h_kin
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 0
        li r5, 0
        bl h_mot1
        bl f_hitret
        stw r3, 0x%(V2)X(r31)
        bl f_kflag
        lwz r0, 0(r12)
        ori r0, r0, 0x80
        stw r0, 0(r12)""" % dict(V2=V(2)))
    st('f_g2_up', """
        lwz r3, 0x%(V2)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V2)X(r31)
        cmpwi r3, 0
        bgt.far epi
        bl f_kflag
        lwz r0, 0(r12)
        rlwinm r0, r0, 0, 25, 23
        stw r0, 0(r12)
        li r4, 1
        b go""" % dict(V2=V(2)))
    # slot 31 (0x113F0; the Wii U calls its slot 31 with the hit record before notify_on_damage, as the 3DS): immune
    # (GH_IMM = 1) when the hit is direct. The 3DS: category 1 (a weapon) immune when is_weapon_as_fighter(kind)
    # (3DS weapon kinds 0x179 / 0x17A / 0x180-0x182), category 4 (an item) when held and not kind 0x12 / 0x24, any
    # other (a fighter's own attack) when the AttackData's byte +0x4C is set. Approximated: every category by that
    # byte (the Wii U's twins of is_weapon_as_fighter / Item::is_haved are not found; projectiles and thrown items
    # are indirect hitboxes); not ported: the module acc+0x3074 byte +0x5A2 = 0 / 1 and play_se(15)
    G.asm("""
    f_g31:
        lwz r11, 0x14(r4)
        li r0, 0
        cmpwi r11, 0
        beq g31_s
        lbz r0, 0x4C(r11)
        cmpwi r0, 0
        beq g31_s
        li r0, 1
    g31_s:
        stb r0, 0x%X(r3)
        blr
    """ % GH_IMM)
    # slot 10 notify_on_damage (0x11094): immune (GH_IMM) -> DamageModuleImpl::init_damage(GH_DMG) (the HP before
    # the hit) and no reaction; else GH_DMG = damage(0) (entry 0's +0, as 3DS DamageModuleImpl::damage(int)
    # 0x9512CC) and BehaviorImpl's; then V1 = P5 (1200: the leave timer restarts). stop_se not ported
    G.asm("f_ghos_dmg:\nmflr r0\nbl pro\nlwz r3, 0(r31)\nlwz r3, 0x30D4(r3)\nlbz r0, 0x%X(r31)\ncmpwi r0, 0\n"
          "beq gd_n\nlfs f1, 0x%X(r31)" % (GH_IMM, GH_DMG))
    far(INIT_DAMAGE)
    G.asm("b gd_t\ngd_n:\nlwz r3, 0xC(r3)\nlfs f0, 0(r3)\nstfs f0, 0x%X(r31)\nmr r3, r31" % GH_DMG)
    far(BI_NOTIFY_DMG)
    G.asm("gd_t:\nlwz r0, 0x%X(r30)\nstw r0, 0x%X(r31)\nb epi" % (P(5), V(1)))
    # slot 69 (0x113A4; the Wii U notify_on_damage calls it as the 3DS's does): a leave running -> finalised and
    # set_correct(5); => 2 (stun); returns 1 (the framework's own reaction skipped)
    st('f_ghos_69', "bl f_unleave\nli r4, 2\nbl h_chgi\nli r3, 1")
    # slot 27 notify_on_remove (the 3DS's 28, 0x11140): the body effect V4 removed, then BehaviorImpl's
    G.asm("""
    f_ghos_rm:
        mflr r0
        bl pro
        lwz r4, 0x%X(r31)
        cmpwi r4, 0
        beq gr_out
        mr r3, r31
        li r0, 0
        stw r0, 0x%X(r31)
    """ % (V(4), V(4)))
    far(REMOVE_EFFECT)
    G.asm("gr_out:\nmr r3, r31\nlmw r28, 0x20(r1)\nlwz r0, 0x34(r1)\nmtlr r0\naddi r1, r1, 0x30")
    G.asm("lis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctr" % (orig(27) >> 16, orig(27) & 0xFFFF))
    # ---- the aerial modes the Wii U has no setter for (3DS EnemyAerialModuleImpl: every setter is the mode word,
    # energy 0's init vt+0x1C(0x17, &speed, &zero3, acc) (3DS vt+0xC), energy 0 on (+0x18 = 1), energy 1 off):
    # f_amode(r4 mode; the speed at the caller's r1+8): set_mode_none 0x5F58C8 (-1, speed 0), set_mode_uniform
    # 0x5F5BD4 (5, the given speed: the update does nothing in mode 5, on both), set_mode_braking 0x5F5B48 (4, the
    # current speed; +0x18 / +0x1C the two params); set_mode_homing_extend 0x5F60F0 = set_mode_homing (the slip
    # variant with speed 0: f_ahome zeroes energy 0's speed, then the Wii U's slip_homing_extend 0x02DB2A48)
    G.asm("""
    f_anone:
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        li r4, -1
    f_amode:
        mflr r0
        stw r0, 0x1C(r1)
        stw r4, 0x%(M)X(r31)
        li r0, 0
        stw r0, 0x10(r1)
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        lwz r3, 0x%(E0)X(r31)
        lwz r12, 0x1C(r3)
        lwz r12, 0x1C(r12)
        mtctr r12
        li r4, 0x17
        addi r5, r1, 8
        addi r6, r1, 0x10
        lwz r7, 0x%(AER)X(r31)
        bctrl
        li r0, 1
        lwz r12, 0x%(E0)X(r31)
        stb r0, 0x18(r12)
        li r0, 0
        lwz r12, 0x%(E1)X(r31)
        stb r0, 0x18(r12)
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    f_ahome:
        mflr r0
        stw r0, 0x1C(r1)
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stfs f1, 0x10(r1)
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 8
        bl 0x%(SS)08X
        lfs f1, 0x10(r1)
        lfs f2, 4(r28)
        lfs f3, 8(r28)
        lfs f4, 0xC(r28)
        lfs f5, 0x10(r28)
        lfs f6, 0x14(r28)
        addi r3, r31, 0x%(AER)X
        lwz r0, 0x1C(r1)
        mtlr r0
        b 0x%(SHE)08X
    f_aupd:
        addi r3, r31, 0x%(AER)X
        b 0x%(UPD)08X
    """ % dict(M=AER + 0xC, E0=AER + 4, E1=AER + 8, AER=AER, SS=AER_SET_SPEED, SHE=AER_SLIP_HOMING_EXT,
               UPD=AER_UPDATE))

    # ---- Tikibuzz (kind 0x0F; create 0x78630, table 0x10E134). V0 the search counter (+0x1DC), V1 the search
    # cool-down (+0x1E0), V2 the dive frames (+0x1E4), V3 the stomp frames (+0x1E8), V4 the landing frames
    # (+0x1EC), V5 the leave frames (+0x1F4), V6 the target's y (+0x1FC), Y0 the last y (+0x1F8). P0-P20: its P0
    # row (variation 0), P21 the leave frames (P@0x78 f0: 200)
    def tp(i):
        return P(i)
    G.asm("f_tiki_start:\nmflr r0\nbl pro\naddi r3, r31, 0x%X\nlwz r4, 0(r31)\nbl 0x%08X\nmr r3, r31" % (AER, AER_CTOR))   # step 2f: set_rhombus(this) (r3 was the aerial module)
    far(SET_RHOMBUS)
    G.asm("""
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x60(r12)
        stw r0, 0x10(r31)
        li r0, 0
        stw r0, 0x14(r31)
        stw r0, 0x18(r31)
        bl h_near
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        beq ts_go
        bl h_rev
    ts_go:
        li r4, 3
        b go
    """)
    # 1 fall (0x77BD8 / 0x77E10): kinetic 8, ground off, Fly (loop); on the ground -> 3
    st('t_fall_en', "li r4, 8\nbl h_kin\nli r4, 0\nbl h_att\nli r4, 11\nli r5, 1\nbl h_mot1")
    st('t_fall_up', "bl h_gnd\ncmpwi r3, 0\nbeq.far epi\nli r4, 3\nb go")
    # 3 fly (0x78668 / 0x77A2C): ground off, passable, Y0 = y, Fly (loop), set_mode_homing_extend(f3, f4, f7, f8,
    # f5, f6), the swing fields (+0x54 = 1, +0x5C = 0, +0x58 = -1), the target fighter 0 at (0, f1 (35), 0), V0 = 0
    # (the meshes' visibility: not ported). Update: the aerial update, Y0 = y (the flap rate MotionModule +0x50 =
    # f9 / f10 rising / not: not ported); V1 > 0 counts down, else every search-0 interval (30) frames of V0
    # search_target(0) (15 x 60 below it) -> 4, V1 = int(f17) (152); V0 < f2 (900): V0++, else -> 9 (leave)
    st('t_fly_en', """
        li r4, 0
        bl h_att
        bl f_pass1
        bl h_sety
        li r4, 11
        li r5, 1
        bl h_mot1
        addi r28, r30, 0x%(PH)X
        lfs f1, 0(r28)
        bl f_ahome
        li r0, 1
        stb r0, 0x%(S54)X(r31)
        li r0, 0
        stw r0, 0x%(S5C)X(r31)
        stw r0, 0x%(V0)X(r31)
        stw r0, 0x%(T)X(r31)
        stw r0, 0x%(O)X(r31)
        stw r0, 0x%(O8)X(r31)
        stb r0, 0x%(F)X(r31)
        lis r0, 0xBF80
        stw r0, 0x%(S58)X(r31)
        lfs f1, 0x%(P1)X(r30)
        stfs f1, 0x%(O4)X(r31)""" % dict(PH=P(22), S54=AER + 0x54, S5C=AER + 0x5C, S58=AER + 0x58, V0=V(0),
                                         T=AER + 0x30, O=AER + 0x40, O4=AER + 0x44, O8=AER + 0x48, F=AER + 0x2C,
                                         P1=tp(1)))
    st('t_fly_up', """
        bl f_aupd
        bl h_sety
        lwz r3, 0x%(V1)X(r31)
        cmpwi r3, 0
        ble tf_srch
        addi r3, r3, -1
        stw r3, 0x%(V1)X(r31)
        b tf_cnt
    tf_srch:
        li r4, 0
        bl h_grp
        lwz r0, 0x%(V0)X(r31)
        divw r12, r0, r3
        mullw r12, r12, r3
        cmpw r12, r0
        bne tf_cnt
        li r4, 0
        bl h_srch
        cmpwi r3, -1
        beq tf_cnt
        li r4, 4
        bl h_chg
        lfs f1, 0x%(P17)X(r30)
        fctiwz f1, f1
        stfd f1, 8(r1)
        lwz r0, 0xC(r1)
        stw r0, 0x%(V1)X(r31)
        b epi
    tf_cnt:
        lwz r3, 0x%(V0)X(r31)
        lwz r0, 0x%(P2)X(r30)
        cmpw r0, r3
        ble tf_leave
        addi r3, r3, 1
        stw r3, 0x%(V0)X(r31)
        b epi
    tf_leave:
        li r4, 9
        b go""" % dict(V0=V(0), V1=V(1), P17=tp(17), P2=tp(2)))
    # 4 hold (0x780A4 / 0x78410): ground off, passable, AttackHold at f11 (0.75), set_mode_none, kinetic 11, V6 =
    # fighter 0's y (get_fighter_pos(0)); the aerial update, at the motion's end -> 5
    st('t_hold_en', """
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 2
        li r5, 0
        lfs f2, 0x%(P11)X(r30)
        bl h_mot
        bl f_anone
        li r4, 11
        bl h_kin
        addi r3, r1, 8
        mr r4, r31
        li r5, 0
        lis r12, 0x%(GH)04X
        ori r12, r12, 0x%(GL)04X
        mtctr r12
        bctrl
        lwz r0, 0xC(r1)
        stw r0, 0x%(V6)X(r31)""" % dict(P11=tp(11), GH=GET_TARGET_POS >> 16, GL=GET_TARGET_POS & 0xFFFF, V6=V(6)))
    st('t_hold_up', "bl f_aupd\nbl h_end\ncmpwi r3, 0\nbeq.far epi\nli r4, 5\nb go")
    # 5 dive (0x77964 / 0x77CB0; the contact attack, P2 entry 0): ground off, passable, Attack (loop),
    # set_mode_uniform((0, -f12)) (-6 a frame), V2 = 0; the aerial update; at / below V6 passable off; on the
    # ground => 7; V2 < f13 (9): V2++, else -> 6
    st('t_dive_en', """
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 0
        li r5, 1
        bl h_mot1
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0x%(V2)X(r31)
        lfs f1, 0x%(P12)X(r30)
        fneg f1, f1
        stfs f1, 0xC(r1)
        li r4, 5
        bl f_amode""" % dict(V2=V(2), P12=tp(12)))
    st('t_dive_up', """
        bl f_aupd
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        lfs f0, 0x%(V6)X(r31)
        fcmpu cr0, f1, f0
        bgt td_t
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0
        bl 0x%(SP)08X
    td_t:
        bl h_gnd
        cmpwi r3, 0
        beq td_c
        li r4, 7
        b goi
    td_c:
        lwz r3, 0x%(V2)X(r31)
        lwz r0, 0x%(P13)X(r30)
        cmpw r0, r3
        ble td_brk
        addi r3, r3, 1
        stw r3, 0x%(V2)X(r31)
        b epi
    td_brk:
        li r4, 6
        b go""" % dict(V6=V(6), SP=SET_PASSABLE, V2=V(2), P13=tp(13)))
    # 6 brake (0x78240 / 0x784B4): ground off, passable, AttackBrake at f16 (0.7), set_mode_braking(0, f15);
    # the aerial update; on the ground: speed 0, set_mode_none, at the motion's end -> 3; in the air: rising or
    # still (speed y >= 0) -> 3
    st('t_brk_en', """
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 1
        li r5, 0
        lfs f2, 0x%(P16)X(r30)
        bl h_mot
        lwz r12, 0x%(E0)X(r31)
        lwz r0, 0(r12)
        stw r0, 8(r1)
        lwz r0, 4(r12)
        stw r0, 0xC(r1)
        li r4, 4
        bl f_amode
        li r0, 0
        stw r0, 0x%(B0)X(r31)
        lwz r0, 0x%(P15)X(r30)
        stw r0, 0x%(B1)X(r31)""" % dict(P16=tp(16), E0=AER + 4, B0=AER + 0x18, B1=AER + 0x1C, P15=tp(15)))
    st('t_brk_up', """
        bl f_aupd
        bl h_vy0
        stfs f1, 0x18(r1)
        bl h_gnd
        cmpwi r3, 0
        beq tb_air
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 8
        bl 0x%(SS)08X
        bl f_anone
        bl h_end
        cmpwi r3, 0
        beq.far epi
        b tb_go
    tb_air:
        lfs f1, 0x18(r1)
        lfs f0, 0x%(Z)X(r30)
        fcmpu cr0, f1, f0
        blt.far epi
    tb_go:
        li r4, 3
        b go""" % dict(AER=AER, SS=AER_SET_SPEED, Z=P(28)))
    # 7 landed (0x78454 / 0x78554): ground on, AttackUnguard, set_mode_none, V4 = 0, request_quake(3); the aerial
    # update; V4 < f14 (45): V4++, else -> 8. 8 ready (0x77D7C / 0x78204): ground off, FlyReady, set_mode_none; at
    # its end -> 3
    st('t_land_en', """
        li r4, 1
        bl h_att
        li r4, 3
        li r5, 0
        bl h_mot1
        bl f_anone
        li r0, 0
        stw r0, 0x%(V4)X(r31)
        mr r3, r31
        li r4, 3
        lis r12, 0x%(QH)04X
        ori r12, r12, 0x%(QL)04X
        mtctr r12
        bctrl""" % dict(V4=V(4), QH=REQ_QUAKE >> 16, QL=REQ_QUAKE & 0xFFFF))
    st('t_land_up', """
        bl f_aupd
        lwz r3, 0x%(V4)X(r31)
        lwz r0, 0x%(P14)X(r30)
        cmpw r0, r3
        ble tl_go
        addi r3, r3, 1
        stw r3, 0x%(V4)X(r31)
        b epi
    tl_go:
        li r4, 8
        b go""" % dict(V4=V(4), P14=tp(14)))
    st('t_rdy_en', "li r4, 0\nbl h_att\nli r4, 12\nli r5, 0\nbl h_mot1\nbl f_anone")
    st('t_rdy_up', "bl h_end\ncmpwi r3, 0\nbeq.far epi\nli r4, 3\nb go")
    # 9 leave (0x7781C / 0x77C40): ground off, passable, Fly (loop), set_correct(0), set_mode_none, V5 = 200; the
    # aerial update; V5 runs out -> 12 (removed)
    st('t_lv_en', """
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 11
        li r5, 1
        bl h_mot1
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0
        bl 0x%(SC)08X
        bl f_anone
        lwz r0, 0x%(P21)X(r30)
        stw r0, 0x%(V5)X(r31)""" % dict(SC=SET_CORRECT, P21=tp(21), V5=V(5)))
    st('t_lv_up', """
        bl f_aupd
        lwz r3, 0x%(V5)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V5)X(r31)
        cmpwi r3, 0
        bgt.far epi
        lwz r4, 0x%(RM)X(r30)
        b go""" % dict(V5=V(5), RM=CF['REMOVE']))
    # 10 stomped (slot 21 -> 10; 0x77F04 / 0x78388): ground off, passable, Step, create_dead_item(1, 10) (the
    # removal's defeat path here: DEFEATED), disable_hit (notify_on_death: hit off, attacks cleared, as the Goomba's
    # collapse), V3 = 0, set_mode_uniform((0, -f19)) (-3), effect 0x70F0000 at the body (the meshes, play_se: not
    # ported); the aerial update; V3 < f20 (60) and not on the ground: V3++, else -> 11
    st('t_stomp_en', """
        li r0, 1
        stw r0, 0x%(DF)X(r31)
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 13
        li r5, 0
        bl h_mot1
        mr r3, r31
        lis r12, 0x%(NDH)04X
        ori r12, r12, 0x%(NDL)04X
        mtctr r12
        bctrl
        li r0, 0
        stw r0, 0x%(V3)X(r31)
        stw r0, 8(r1)
        lfs f1, 0x%(P19)X(r30)
        fneg f1, f1
        stfs f1, 0xC(r1)
        li r4, 5
        bl f_amode
        lis r4, 0x70F
        bl t_fx""" % dict(DF=DEFEATED, NDH=NOTIFY_DEATH >> 16, NDL=NOTIFY_DEATH & 0xFFFF, V3=V(3),
                                               P19=tp(19)))
    st('t_stomp_up', """
        bl f_aupd
        lwz r3, 0x%(V3)X(r31)
        lwz r0, 0x%(P20)X(r30)
        cmpw r0, r3
        ble ts_gone
        bl h_gnd
        cmpwi r3, 0
        bne ts_gone
        lwz r3, 0x%(V3)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(V3)X(r31)
        b epi
    ts_gone:
        li r4, 11
        b go""" % dict(V3=V(3), P20=tp(20)))
    # 11 gone (0x77E50 / 0x78378): kinetic 26, ground on, passable, effect 0x70F0001 at the body (set_visibility(0),
    # play_se: not ported); -> 12
    st('t_gone_en', "li r4, 26\nbl h_kin\nli r4, 1\nbl h_att\nbl f_pass1\nlis r4, 0x70F\nori r4, r4, 1\nbl t_fx")
    st('t_gone_up', "lwz r4, 0x%X(r30)\nb go" % CF['REMOVE'])
    # t_fx(r4 id): request_effect(id, the posture position, rotation 0, 1.0) (3DS EffectModuleImpl::req(id,
    # posture +0x14, ZERO, 1, ...))
    G.asm("""
    t_fx:
        mflr r0
        stw r0, 0x1C(r1)
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lwz r5, 0(r31)
        lwz r5, 0x311C(r5)
        addi r5, r5, 0x10
        addi r6, r1, 8
        mr r3, r31
    """)
    lfs('f1', 'consts', 4)
    G.asm("""
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        mtctr r12
        bctrl
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """ % (REQ_EFFECT >> 16, REQ_EFFECT & 0xFFFF))
    # ---- Furiijio (kind 0x1A; enemy_fs.cro create 0x6DC6C, table 0x10D168; docs/smash-run-port.md "Step 2f").
    # V0 the search counter (3DS +0x1DC), V1 the search cool-down (+0x1E4), V2 the leave timer (+0x1E8), V3 the target
    # (+0x1EC), V4 the state frames (+0x1E0), V5 / V6 the common leave, V7 the sweep step (+0x1F0), V8 the beam length
    # (+0x248); FU_C the centre offset (+0x218), FU_ROT BeamN's angles in degrees (+0x224), FU_E the beam's three
    # follow effects (+0x254 / +0x258 / +0x25C). The 3DS's node offset +0x230 is (P@0x9C x 10 = 0) rotated: zero.
    # P0-5 set_mode_homing (P0 row, variation 0), 6 leave frames 900, 7 target offset y 25 (2.5 x 10), 8 / 9 the
    # beam choice (random(0, 2) < 1: sweep), 10 0 (the node offset), 11 10 (the aim effect's offset), 12 1.5 (its
    # scale), 13 aim frames 25, 14 cool-down 150, 15 beam length cap 200, 16 charge frames 22, 17 growth 4.5, 18 beam
    # frames 60, 19 sweep charge 34, 20 / 21 the sweep side (random(0, 1) < 1), 22 sweep frames 140, 23 180 / 140,
    # 24 P@0xD4 15, 25 1.5, 26 0.05, 27 deg -> rad, 28 90, 29 1, 30 0, 31-35 the leave (P6), 36-41 FU_CALC
    fp = lambda i: P(i)  # noqa: E731
    d = dict(AER=AER, V0=V(0), V1=V(1), V2=V(2), V3=V(3), V4=V(4), V7=V(7), V8=V(8), C=FU_C, C4=FU_C + 4,
             C8=FU_C + 8, R=FU_ROT, R4=FU_ROT + 4, R8=FU_ROT + 8, E=FU_E, E4=FU_E + 4, E8=FU_E + 8,
             SNR=SET_NODE_ROT, SNT=SET_NODE_TRANS, DIRTY=MODEL_NODE_DIRTY, OFS=ATK_SET_OFFSET, EPOS=EFF_SET_POS,
             ESC=EFF_SET_SCALE, SQ=SQRTF, SIN=SINF, COS=COSF, ACOS=ACOSF, SS=AER_SET_SPEED, SH=AER_SLIP_HOMING,
             CK=CHANGE_KINETIC, BUL=BULLET, DEF=DEFEATED, DM=CF['DEADMOT'],
             **{'P%d' % i: fp(i) for i in range(42)})
    # fu_node: BeamN (node 3) turned to FU_ROT (set_node_rotate(3, rad, 0); a change -> the ModelModule's vt+0xC4, as
    # the Wii U's own callers do) and placed at the posture + FU_C (+ the zero offset) in global space
    # (set_node_translate(3, &v, 1, 0) + vt+0xC4: the 3DS's Behavior::set_node_global_position 0x7B5224). Step 2g v5:
    # FU_ROT is (90, a lr, 90), the 3DS's (0, a lr, 90) turned 90 about the beam (x; step 2g v6: x 90 x -lr, so at lr 1,
    # now yaw +90 with the real flip, the planes' front still faces the camera): the 3DS beam models' bones are
    # Y-axial billboards (H3D billboard mode 6 in BeamBG / BeamBG2 / BeamBody's flags), which turn their planes to
    # the camera about the beam; the converted NUDs have no billboard, so the turn is in the angles (both games build
    # the node matrix as Rz Ry Rx: 3DS Matrix34::set_rotate_xyz 0x87D298, Wii U 0x033730A0). The 3DS's
    # set_rotation_order_zxy (ModelModule +0x21 = 1) is the model root's order (3DS 0xA6DBF8: the posture rotation
    # through set_rotate_zxy 0x87D3B4), the same as xyz for a yaw-only posture: nothing to port
    G.asm("""
    fu_node:
        mflr r0
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        lfs f0, 0x%(P27)X(r30)
        lfs f1, 0x%(R)X(r31)
        fmuls f1, f1, f0
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f2, 0x60(r12)
        fneg f2, f2
        fmuls f1, f1, f2
        stfs f1, 8(r1)
        lfs f1, 0x%(R4)X(r31)
        fmuls f1, f1, f0
        stfs f1, 0xC(r1)
        lfs f1, 0x%(R8)X(r31)
        fmuls f1, f1, f0
        stfs f1, 0x10(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30F0(r3)
        li r4, 3
        addi r5, r1, 8
        li r6, 0
        bl 0x%(SNR)08X
        cmpwi r3, 0
        beq fu_n1
        bl fu_dirty
    fu_n1:
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x10(r12)
        lfs f0, 0x%(C)X(r31)
        fadds f1, f1, f0
        stfs f1, 8(r1)
        lfs f1, 0x14(r12)
        lfs f0, 0x%(C4)X(r31)
        fadds f1, f1, f0
        stfs f1, 0xC(r1)
        lfs f1, 0x18(r12)
        lfs f0, 0x%(C8)X(r31)
        fadds f1, f1, f0
        stfs f1, 0x10(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30F0(r3)
        li r4, 3
        addi r5, r1, 8
        li r6, 1
        li r7, 0
        bl 0x%(SNT)08X
        cmpwi r3, 0
        beq fu_n2
        bl fu_dirty
    fu_n2:
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    fu_dirty:
        lwz r3, 0(r31)
        lwz r3, 0x3118(r3)
        lwz r12, 0(r3)
        lwz r12, 0x%(DIRTY)X(r12)
        mtctr r12
        bctr
    fu_grow:
        lfs f1, 0x%(V8)X(r31)
        lfs f0, 0x%(P17)X(r30)
        fadds f1, f1, f0
        stfs f1, 0x%(V8)X(r31)
        lfs f0, 0x%(P15)X(r30)
        fcmpu cr0, f0, f1
        bgelr
        stfs f0, 0x%(V8)X(r31)
        blr
    fu_beam:
        mflr r0
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        lfs f1, 0x%(V8)X(r31)
        lfs f0, 0x%(P25)X(r30)
        fmuls f1, f1, f0
        lfs f0, 0x%(P24)X(r30)
        fadds f1, f1, f0
        stfs f1, 8(r1)
        li r0, 0
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30C8(r3)
        li r4, 0
        addi r5, r1, 8
        bl 0x%(OFS)08X
        lfs f1, 0x%(V8)X(r31)
        lfs f0, 0x%(P26)X(r30)
        fmuls f1, f1, f0
        stfs f1, 8(r1)
        lfs f0, 0x%(P29)X(r30)
        stfs f0, 0xC(r1)
        stfs f0, 0x10(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30D8(r3)
        lwz r4, 0x%(E4)X(r31)
        addi r5, r1, 8
        bl 0x%(ESC)08X
        lwz r0, 0x%(V8)X(r31)
        stw r0, 8(r1)
        li r0, 0
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30D8(r3)
        lwz r4, 0x%(E8)X(r31)
        addi r5, r1, 8
        bl 0x%(EPOS)08X
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    fu_clamp:
        lfs f0, 0x%(P40)X(r30)
        fcmpu cr0, f1, f0
        bge fu_cl1
        fmr f1, f0
        blr
    fu_cl1:
        lfs f0, 0x%(P29)X(r30)
        fcmpu cr0, f1, f0
        blelr
        fmr f1, f0
        blr
    fu_calc:
        mflr r0
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        stfs f1, 8(r1)
        stfs f2, 0xC(r1)
        fmuls f0, f1, f1
        fmuls f3, f2, f2
        fadds f1, f0, f3
        lfs f0, 0x%(P30)X(r30)
        fcmpu cr0, f1, f0
        beq fu_c1
        bl 0x%(SQ)08X
        lfs f0, 0x%(P29)X(r30)
        fdivs f0, f0, f1
        lfs f1, 8(r1)
        fmuls f1, f1, f0
        stfs f1, 8(r1)
        lfs f1, 0xC(r1)
        fmuls f1, f1, f0
        stfs f1, 0xC(r1)
    fu_c1:
        lfs f1, 0xC(r1)
        bl fu_clamp
        bl 0x%(ACOS)08X
        stfs f1, 0x10(r1)
        lfs f1, 8(r1)
        bl fu_clamp
        bl 0x%(ACOS)08X
        lfs f0, 0x%(P36)X(r30)
        lfs f2, 0x%(P38)X(r30)
        fcmpu cr0, f1, f0
        bge fu_c2
        lfs f2, 0x%(P39)X(r30)
    fu_c2:
        lfs f1, 0x10(r1)
        lfs f0, 0x%(P37)X(r30)
        fmuls f1, f1, f0
        fmuls f1, f1, f2
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    fu_angle:
        mflr r0
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        addi r3, r1, 8
        mr r4, r31
        lwz r5, 0x%(V3)X(r31)
    """ % d)
    far(GET_TARGET_POS)
    G.asm("""
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x10(r12)
        lfs f2, 0x%(C)X(r31)
        fadds f0, f0, f2
        lfs f1, 8(r1)
        fsubs f1, f1, f0
        lfs f0, 0x14(r12)
        lfs f3, 0x%(C4)X(r31)
        fadds f0, f0, f3
        lfs f2, 0xC(r1)
        fsubs f2, f2, f0
        bl fu_calc
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    fu_tgt:
        lwz r0, 0x%(V3)X(r31)
        stw r0, 0x%(T)X(r31)
        li r0, 0
        stw r0, 0x%(O)X(r31)
        stw r0, 0x%(O8)X(r31)
        stb r0, 0x%(F)X(r31)
        lwz r0, 0x%(P7)X(r30)
        stw r0, 0x%(O4)X(r31)
        blr
    fu_follow:
        mflr r0
        stw r0, 0x1C(r1)
        mr r3, r31
        addi r6, r1, 8
        addi r7, r1, 8
        lfs f1, 0x%(P29)X(r30)
        lis r12, 0x%(RFH)04X
        ori r12, r12, 0x%(RFL)04X
        mtctr r12
        bctrl
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """ % dict(d, T=AER + 0x30, O=AER + 0x40, O4=AER + 0x44, O8=AER + 0x48, F=AER + 0x2C, RFH=REQ_FOLLOW >> 16,
               RFL=REQ_FOLLOW & 0xFFFF))
    # start 0x6BE88: the aerial module (the 3DS ctor's), set_rhombus, +0x10 = posture lr, +0x14 / +0x18 = 0, its
    # fields zero, V2 = 900, V3 = the nearest fighter (turned to it: check_turn_to_target -> reverse_lr(1, 1)), the
    # aerial target V3 at (0, 25, 0), -> 1
    G.asm("f_fu_start:\nmflr r0\nbl pro\naddi r3, r31, 0x%X\nlwz r4, 0(r31)\nbl 0x%08X\nmr r3, r31" % (AER, AER_CTOR))
    far(SET_RHOMBUS)
    G.asm("""
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x60(r12)
        stw r0, 0x10(r31)
        li r0, 0
        stw r0, 0x14(r31)
        stw r0, 0x18(r31)
        stw r0, 0x%(V1)X(r31)
        stw r0, 0x%(V4)X(r31)
        stw r0, 0x%(V7)X(r31)
        stw r0, 0x%(V8)X(r31)
        li r12, 10
        mtctr r12
        addi r12, r31, 0x%(Cm4)X
    fs_z:
        stwu r0, 4(r12)
        bdnz fs_z
        lwz r0, 0x%(P6)X(r30)
        stw r0, 0x%(V2)X(r31)
        bl h_near
        stw r3, 0x%(V3)X(r31)
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        beq fs_t
        bl h_rev
    fs_t:
        bl fu_tgt
        li r4, 1
        b go
    """ % dict(d, Cm4=FU_C - 4))
    # 1 fly (0x6BF78 / 0x6C0E8): set_mode_homing(P0-5) (energy 0's speed 0, then the slip homing setter: mode 2),
    # passable, ground off, Move (loop), V0 = search_interval(0) (50). Update: no target -> the nearest (none: the
    # frame ends) and the aerial target at it; the aerial update; V0 / V1 count down; both below 0: V0 = 50,
    # search_target(0) found -> V3 = it, V2 = 900, random(0, 2) < 1 -> 5 (sweep), else -> 2; otherwise V2 counts down
    # -> 8 (leave) at 0
    st('fu1_en', """
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 8
        bl 0x%(SS)08X
        lfs f1, 0x%(P0)X(r30)
        lfs f2, 0x%(P1)X(r30)
        lfs f3, 0x%(P2)X(r30)
        lfs f4, 0x%(P3)X(r30)
        lfs f5, 0x%(P4)X(r30)
        lfs f6, 0x%(P5)X(r30)
        addi r3, r31, 0x%(AER)X
        bl 0x%(SH)08X
        bl f_pass1
        li r4, 0
        bl h_att
        li r4, 9
        li r5, 1
        bl h_mot1
        li r4, 0
        bl h_grp
        stw r3, 0x%(V0)X(r31)""" % d)
    st('fu1_up', """
        lwz r3, 0x%(V3)X(r31)
        cmpwi r3, -1
        bne fu1_a
        bl h_near
        stw r3, 0x%(V3)X(r31)
        cmpwi r3, -1
        beq.far epi
        bl fu_tgt
    fu1_a:
        bl f_aupd
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V0)X(r31)
        lwz r4, 0x%(V1)X(r31)
        addi r4, r4, -1
        stw r4, 0x%(V1)X(r31)
        cmpwi r3, 0
        bge fu1_l
        cmpwi r4, 0
        bge fu1_l
        li r4, 0
        bl h_grp
        stw r3, 0x%(V0)X(r31)
        li r4, 0
        bl h_srch
        cmpwi r3, -1
        beq fu1_l
        stw r3, 0x%(V3)X(r31)
        lwz r0, 0x%(P6)X(r30)
        stw r0, 0x%(V2)X(r31)
        li r3, 0
        lwz r4, 0x%(P8)X(r30)
        lwz r0, 0x%(P9)X(r30)
        add r4, r4, r0
        addi r4, r4, -1
        bl h_rand
        lwz r0, 0x%(P9)X(r30)
        cmpw r3, r0
        li r4, 5
        blt fu1_go
        li r4, 2
    fu1_go:
        b go
    fu1_l:
        lwz r3, 0x%(V2)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V2)X(r31)
        cmpwi r3, 0
        bgt.far epi
        li r4, 8
        b go""" % d)
    # 2 / 5 charge (0x6D0F0 / 0x6D4F0): set_current_speed(0, 0), passable, ground off, IceBeamShotHold (loop),
    # FU_C = center_pos() - the posture, request_effect(0x71A0000 / 0x71A0001, the posture + FU_C, 1); V4 = 22 / 34
    # (play_se 0x6A90001 not ported). Update (0x6D924 / 0x6DA4C): V4 below 0 -> 3 / 6
    G.asm("fu2_en:\nmflr r0\nbl pro\nlis r28, 0x71A\nlwz r0, 0x%(P16)X(r30)\nb fu_chg" % d)
    G.asm("fu5_en:\nmflr r0\nbl pro\nlis r28, 0x71A\nori r28, r28, 1\nlwz r0, 0x%(P19)X(r30)" % d)
    G.asm("""
    fu_chg:
        stw r0, 0x%(V4)X(r31)
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 8
        bl 0x%(SS)08X
        bl f_pass1
        li r4, 0
        bl h_att
        li r4, 8
        li r5, 1
        bl h_mot1
        addi r3, r1, 8
        mr r4, r31
    """ % d)
    far(CENTER_POS)
    G.asm("""
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 8(r1)
        lfs f0, 0x10(r12)
        fsubs f1, f1, f0
        stfs f1, 0x%(C)X(r31)
        fadds f1, f0, f1
        stfs f1, 8(r1)
        lfs f1, 0xC(r1)
        lfs f0, 0x14(r12)
        fsubs f1, f1, f0
        stfs f1, 0x%(C4)X(r31)
        fadds f1, f0, f1
        stfs f1, 0xC(r1)
        lfs f1, 0x10(r1)
        lfs f0, 0x18(r12)
        fsubs f1, f1, f0
        stfs f1, 0x%(C8)X(r31)
        fadds f1, f0, f1
        stfs f1, 0x10(r1)
        mr r3, r31
        mr r4, r28
        addi r5, r1, 8
        lfs f1, 0x%(P29)X(r30)
    """ % d)
    far(REQ_EFFECT0)
    G.asm("b epi")
    for k, nxt in ((2, 3), (5, 6)):
        st('fu%d_up' % k, """
            lwz r3, 0x%(V4)X(r31)
            addi r3, r3, -1
            stw r3, 0x%(V4)X(r31)
            cmpwi r3, 0
            bge.far epi
            li r4, %(N)d
            b go""" % dict(d, N=nxt))
    # 3 / 6 aim (0x6D224 / 0x6D624): V8 = 0, a = calc_angle(the target - (the posture + FU_C)) (3DS 0x7B01D8:
    # normalised, acos(y) x 180 / pi, negated when acos(x) < pi / 2); 3: FU_ROT = (0, a lr, 90); 6: the step V7 =
    # 180 / 140 x lr, random(0, 1) < 1: V7 negated and FU_ROT y = a lr + 90 lr, else a lr - 90 lr; then fu_node and
    # request_effect(0x71A0005, node 2, offset (10 sin b, 10 cos b, 0) (b = -FU_ROT y in radians: (10, 0) turned by
    # 0x67364, its x / y swapped), rot (0, 0, lr FU_ROT y), 1.5); V4 = 25. Update (0x6D948 / 0x6DA70): fu_node; V4
    # below 0 -> V1 = 150 (the cool-down), -> 4 / 7
    G.asm("""
    fu_aimfin:
        bl fu_node
        lfs f1, 0x%(R4)X(r31)
        lfs f0, 0x%(P27)X(r30)
        fneg f0, f0
        fmuls f1, f1, f0
        stfs f1, 0x14(r1)
        fabs f2, f1
        lfs f0, 0x%(P41)X(r30)
        fcmpu cr0, f2, f0
        bge fu_af1
        lwz r0, 0x%(P11)X(r30)
        stw r0, 0xC(r1)
        li r0, 0
        stw r0, 8(r1)
        b fu_af2
    fu_af1:
        bl 0x%(COS)08X
        lfs f0, 0x%(P11)X(r30)
        fmuls f1, f0, f1
        stfs f1, 0xC(r1)
        lfs f1, 0x14(r1)
        bl 0x%(SIN)08X
        lfs f0, 0x%(P11)X(r30)
        fmuls f1, f0, f1
        stfs f1, 8(r1)
    fu_af2:
        li r0, 0
        stw r0, 0x10(r1)
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x60(r12)
        lfs f1, 0x%(R4)X(r31)
        fmuls f1, f0, f1
        stfs f1, 0x1C(r1)
        mr r3, r31
        lis r4, 0x71A
        ori r4, r4, 5
        li r5, 2
        addi r6, r1, 8
        addi r7, r1, 0x14
        lfs f1, 0x%(P12)X(r30)
    """ % d)
    far(REQ_NODE)
    G.asm("lwz r0, 0x%(P13)X(r30)\nstw r0, 0x%(V4)X(r31)\nb epi" % d)
    st('fu3_en', """
        li r0, 0
        stw r0, 0x%(V8)X(r31)
        bl fu_angle
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x60(r12)
        fmuls f1, f1, f0
        stfs f1, 0x%(R4)X(r31)
        lwz r0, 0x%(P28)X(r30)
        stw r0, 0x%(R)X(r31)
        stw r0, 0x%(R8)X(r31)
        b fu_aimfin""" % d)
    st('fu6_en', """
        li r0, 0
        stw r0, 0x%(V8)X(r31)
        bl fu_angle
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x60(r12)
        fmuls f1, f1, f0
        stfs f1, 8(r1)
        stfs f0, 0xC(r1)
        li r3, 0
        lwz r4, 0x%(P20)X(r30)
        lwz r0, 0x%(P21)X(r30)
        add r4, r4, r0
        addi r4, r4, -1
        bl h_rand
        lfs f0, 0xC(r1)
        lfs f2, 0x%(P23)X(r30)
        fmuls f2, f2, f0
        lfs f3, 0x%(P28)X(r30)
        fmuls f3, f0, f3
        lfs f1, 8(r1)
        lwz r0, 0x%(P21)X(r30)
        cmpw r3, r0
        bge fu6_b
        fneg f2, f2
        fadds f1, f1, f3
        b fu6_c
    fu6_b:
        fsubs f1, f1, f3
    fu6_c:
        stfs f2, 0x%(V7)X(r31)
        stfs f1, 0x%(R4)X(r31)
        lwz r0, 0x%(P28)X(r30)
        stw r0, 0x%(R)X(r31)
        stw r0, 0x%(R8)X(r31)
        b fu_aimfin""" % d)
    for k, nxt in ((3, 4), (6, 7)):
        st('fu%d_up' % k, """
            bl fu_node
            lwz r3, 0x%(V4)X(r31)
            addi r3, r3, -1
            stw r3, 0x%(V4)X(r31)
            cmpwi r3, 0
            bge.far epi
            lwz r0, 0x%(P14)X(r30)
            stw r0, 0x%(V1)X(r31)
            li r4, %(N)d
            b go""" % dict(d, N=nxt))
    # 4 / 7 the beam (enter 0x6C258 / 0x6C980): IceBeamShot (loop), V4 = 60 / 140, fu_node, follow effects
    # 0x71A0002 on node 2, 0x71A0004 / 0x71A0003 on node 3 (BeamN) -> FU_E (play_se 0x6A90002 not ported); the
    # contact attack P2 entry 0 / 1 (set_attack_data). Update (0x6CB80 / 0x6CE24): [4: fu_node] V4 below 0 -> 1;
    # else V8 += 4.5 (at most 200), the hitbox offset (V8 x 1.5 + 15, 0, 0) (AttackModule set_offset(0)), FU_E[1]
    # scaled (V8 x 0.05, 1, 1), FU_E[2] at (V8, 0, 0); [7: FU_ROT y += V7, fu_node]. Exit (0x6D094 / 0x6D494): the
    # three effects removed (stop_se not ported)
    G.asm("fu4_en:\nmflr r0\nbl pro\nlwz r0, 0x%(P18)X(r30)\nb fu_bst\nfu7_en:\nmflr r0\nbl pro\n"
          "lwz r0, 0x%(P22)X(r30)" % d)
    G.asm("""
    fu_bst:
        stw r0, 0x%(V4)X(r31)
        li r4, 7
        li r5, 1
        bl h_mot1
        bl fu_node
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lis r4, 0x71A
        ori r4, r4, 2
        li r5, 2
        bl fu_follow
        stw r3, 0x%(E)X(r31)
        lis r4, 0x71A
        ori r4, r4, 4
        li r5, 3
        bl fu_follow
        stw r3, 0x%(E4)X(r31)
        lis r4, 0x71A
        ori r4, r4, 3
        li r5, 3
        bl fu_follow
        stw r3, 0x%(E8)X(r31)
        b epi
    """ % d)
    st('fu4_up', """
        bl fu_node
        lwz r3, 0x%(V4)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V4)X(r31)
        cmpwi r3, 0
        bge fu4_b
        li r4, 1
        b go
    fu4_b:
        bl fu_grow
        bl fu_beam""" % d)
    st('fu7_up', """
        lwz r3, 0x%(V4)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V4)X(r31)
        cmpwi r3, 0
        bge fu7_b
        li r4, 1
        b go
    fu7_b:
        bl fu_grow
        bl fu_beam
        lfs f1, 0x%(R4)X(r31)
        lfs f0, 0x%(V7)X(r31)
        fadds f1, f1, f0
        stfs f1, 0x%(R4)X(r31)
        bl fu_node""" % d)
    G.asm("fu_bexit:\nmflr r0\nbl pro\naddi r28, r31, 0x%(E)X\nli r29, 3\nfu_bx:\nmr r3, r31\nlwz r4, 0(r28)" % d)
    far(REMOVE_EFFECT)
    G.asm("li r0, 0\nstw r0, 0(r28)\naddi r28, r28, 4\naddi r29, r29, -1\ncmpwi r29, 0\nbne fu_bx\nb epi")
    # 8 leave (0x6C058 / 0x6C408): IceBeamShot at rate 0, init_common_leave(P6: 200 frames, -0.01, 10, effect
    # 0x8000005 at (0, 5, 0) x 1) -> f_leave_en; the common leave's end -> 10 (o_leave_up)
    G.asm("""
    fu8_en:
        mflr r0
        bl pro
        li r4, 7
        li r5, 0
        bl h_mot0
        mr r3, r31
        mr r4, r29
        lmw r28, 0x20(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        b f_leave_en
    """)
    # 9 dead (0x6C0AC / 0x6CB2C): set_mode_none, DamageStart at rate 0, bullet() (P2 entry 2), defeated; the
    # kinetic flag 8 -> 10 (g_dead_up)
    st('fu9_en', """
        bl f_anone
        li r0, 1
        stw r0, 0x%(DEF)X(r31)
        lwz r4, 0x%(DM)X(r30)
        li r5, 0
        bl h_mot0
        mr r3, r31
        bl 0x%(BUL)08X""" % d)
    # slot 10 notify_on_damage (the 3DS's 11, 0x6CB64): V2 = 900, then BehaviorImpl's
    G.asm("""
    f_fu_dmg:
        lwz r12, 0x168(r3)
        lwz r0, 0x%(P6)X(r12)
        stw r0, 0x%(V2)X(r3)
        lis r12, 0x%(BH)04X
        ori r12, r12, 0x%(BL)04X
        mtctr r12
        bctr
    f_fu_kin:
        lwz r3, 0(r3)
        lwz r3, 0x30E8(r3)
        li r4, 26
        b 0x%(CK)08X
    """ % dict(d, BH=BI_NOTIFY_DMG >> 16, BL=BI_NOTIFY_DMG & 0xFFFF))
    # slot 4 update_on_skip (the 3DS's 5, 0x6C438): BehaviorImpl's, then the per-frame node / beam set-up again
    # (3 / 6: fu_node; 4: fu_node, fu_beam; 7: fu_beam, fu_node), without the timers or the growth
    G.asm("f_fu_skip:\nmflr r0\nbl pro\nmr r3, r31")
    far(orig(4))
    G.asm("""
        lwz r0, 4(r31)
        cmpwi r0, 3
        beq fsk_n
        cmpwi r0, 6
        beq fsk_n
        cmpwi r0, 4
        beq fsk_4
        cmpwi r0, 7
        bne.far epi
        bl fu_beam
    fsk_n:
        bl fu_node
        b epi
    fsk_4:
        bl fu_node
        bl fu_beam
        b epi
    """)
    code_ph(G, D, far, st, orig)
    return G


def code_ph(G, D, far, st, orig):
    """step 2g: Propeller Heiho (kind 0x47; enemy_fs.cro create 0x9AA38, state table 0x111278; docs/smash-run-port.md
    "Step 2g"), in region G after the other fliers. Its fields PH_* are the 3DS's +0x1DC..+0x20C: PH_D the vertical
    direction (+0x1DC), PH_B the aerial update's brake flag (+0x1E0), PH_Y a height reference (+0x1E4, written only),
    PH_F the fly-away frames (+0x1F0), PH_T the state timer (+0x1F4), PH_A the bob angle in degrees (int, +0x1F8),
    PH_R turned (+0x1FC), PH_S the item swap timer (+0x200), PH_DT the drop timer (+0x204), PH_I the held item's id
    (+0x208, 0x50000000 none), PH_X dropped (+0x20C). P0-32: its P0 row (P@0x00..0x80), then the literals PHK."""
    d = dict(AER=AER, AM=AER + 0xC, A10=AER + 0x10, A14=AER + 0x14, A18=AER + 0x18, A1C=AER + 0x1C, A20=AER + 0x20,
             A24=AER + 0x24, E0=AER + 4, E1=AER + 8, PD=PH_D, PB=PH_B, PY=PH_Y, PF=PH_F, PT=PH_T, PA=PH_A, PR=PH_R,
             PS=PH_S, PDT=PH_DT, PI=PH_I, PX=PH_X, PHm4=PH - 4, DEF=DEFEATED, MGRH=ha(ITEM_MGR), MGRL=sx(ITEM_MGR),
             FCH=ha(D['fconsts']), FCL=sx(D['fconsts']), SS=AER_SET_SPEED, UXY=AER_UPDATE_XY, SC=SET_CORRECT,
             SP=SET_PASSABLE, BUL=BULLET, CTOR=AER_CTOR, VT=IT_VT, RM=IT_REMOVE, ID=IT_ID, HAVE=IT_HAVE,
             FXH=PH_SWAP_FX >> 16, FXL=PH_SWAP_FX & 0xFFFF, FOOD=PH_FOOD, GOLD=PH_GOLDBAG, CUST=PH_CUSTOM,
             **{'P%d' % i: P(i) for i in range(33)}, **{k.upper(): P(i) for k, i in PHK.items()})

    def call(t):
        return "lis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctrl" % (t >> 16, t & 0xFFFF)

    d.update(FIND=call(FIND_ITEM), SUCC=call(SUCCESS_PCT), CREATE=call(CREATE_ITEM), FALL=call(ITEM_FALL),
             WARP=call(ITEM_WARP), NGP=call(NODE_GPOS), RAY=call(RAY_CHECK), VIEW=call(IN_VIEW), TPOS=call(GET_TARGET_POS),
             GSPD=call(GET_SPEED), COS=call(COSF), DTURN=call(DAMAGE_TURN), RHOMB=call(SET_RHOMBUS),
             BIDMG=call(BI_NOTIFY_DMG), REQ=call(REQ_EFFECT))
    a = lambda text: G.asm(text % d)  # noqa: E731
    # ---- helpers (r31 this, r30 CFG; own frames)
    # ph_find: r3 = ItemManager::find_item(PH_I) (0 for none / removed)
    a("""
    ph_find:
        lwz r4, 0x%(PI)X(r31)
        lis r3, 0x%(MGRH)04X
        lwz r3, %(MGRL)d(r3)
        lis r12, 0x%(FIH)04X
        ori r12, r12, 0x%(FIL)04X
        mtctr r12
        bctr
    """.replace('%(FIH)04X', '%04X' % (FIND_ITEM >> 16)).replace('%(FIL)04X', '%04X' % (FIND_ITEM & 0xFFFF)))
    # ph_anormal(f1-f6): EnemyAerialModuleImpl::set_mode_normal (3DS 0x5F5A9C; no Wii U copy): mode 0, energy 0's
    # init(0x17, &zero2, &zero3, acc), energy 0 on, energy 1 off, energy 0 +0x38 / +0x3C and the module +0x20 / +0x24
    # = (f5, f6) (the max speed), +0x10..+0x1C = f1..f4 (the update's accel x / y, brake x / y)
    a("""
    ph_anormal:
        mflr r0
        stwu r1, -0x40(r1)
        stw r0, 0x44(r1)
        stfs f1, 0x20(r1)
        stfs f2, 0x24(r1)
        stfs f3, 0x28(r1)
        stfs f4, 0x2C(r1)
        stfs f5, 0x30(r1)
        stfs f6, 0x34(r1)
        li r0, 0
        stw r0, 0x%(AM)X(r31)
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        lwz r3, 0x%(E0)X(r31)
        lwz r12, 0x1C(r3)
        lwz r12, 0x1C(r12)
        mtctr r12
        li r4, 0x17
        addi r5, r1, 8
        addi r6, r1, 0x10
        lwz r7, 0x%(AER)X(r31)
        bctrl
        li r0, 1
        lwz r12, 0x%(E0)X(r31)
        stb r0, 0x18(r12)
        li r0, 0
        lwz r11, 0x%(E1)X(r31)
        stb r0, 0x18(r11)
        lfs f5, 0x30(r1)
        lfs f6, 0x34(r1)
        stfs f5, 0x38(r12)
        stfs f6, 0x3C(r12)
        stfs f5, 0x%(A20)X(r31)
        stfs f6, 0x%(A24)X(r31)
        lfs f1, 0x20(r1)
        stfs f1, 0x%(A10)X(r31)
        lfs f1, 0x24(r1)
        stfs f1, 0x%(A14)X(r31)
        lfs f1, 0x28(r1)
        stfs f1, 0x%(A18)X(r31)
        lfs f1, 0x2C(r1)
        stfs f1, 0x%(A1C)X(r31)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr
    # ph_maxspd(f1, f2): set_max_speed (3DS 0x5F58A0): the module +0x20 / +0x24; in mode 0 / 1 also energy 0's
    ph_maxspd:
        stfs f1, 0x%(A20)X(r31)
        stfs f2, 0x%(A24)X(r31)
        lwz r0, 0x%(AM)X(r31)
        cmplwi r0, 1
        bgt ms_out
        lwz r12, 0x%(E0)X(r31)
        stfs f1, 0x38(r12)
        stfs f2, 0x3C(r12)
    ms_out:
        blr
    # ph_setspd(f1, f2): set_current_speed(x, y) (3DS 0x5F5C7C -> the Vector2 setter, Wii U 0x02DB2BC0)
    ph_setspd:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        stfs f1, 8(r1)
        stfs f2, 0xC(r1)
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 8
        bl 0x%(SS)08X
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    # ph_upd(f1, f2, r4): EnemyAerialModuleImpl::update(x, y, brake) (3DS 0x5F66AC = Wii U 0x02DB2524)
    ph_upd:
        addi r3, r31, 0x%(AER)X
        b 0x%(UXY)08X
    # ph_i2f(r3) -> f1, ph_f2i(f1) -> r3 (truncating, as vcvt.s32.f32)
    ph_i2f:
        stwu r1, -0x20(r1)
        xoris r3, r3, 0x8000
        stw r3, 0xC(r1)
        lis r0, 0x4330
        stw r0, 8(r1)
        lfd f1, 8(r1)
        lis r12, 0x%(FCH)04X
        lfd f0, %(FCL)d(r12)
        fsub f1, f1, f0
        frsp f1, f1
        addi r1, r1, 0x20
        blr
    ph_f2i:
        stwu r1, -0x20(r1)
        fctiwz f1, f1
        stfd f1, 8(r1)
        lwz r3, 0xC(r1)
        addi r1, r1, 0x20
        blr
    # ph_hgt(r7 bool) -> f1: Behavior::get_height_from_ground(posture, 50, bool) (3DS 0x7B4C68: GroundModule
    # ray_check(pos, (0 x 50, -1 x 50), out, bool); hit -> pos y - out y, else 50)
    ph_hgt:
        mflr r0
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x10(r12)
        stfs f1, 8(r1)
        lfs f1, 0x14(r12)
        stfs f1, 0xC(r1)
        stfs f1, 0x20(r1)
        lfs f2, 0x%(C50)X(r30)
        lfs f0, 0x%(C0)X(r30)
        fmuls f3, f0, f2
        stfs f3, 0x10(r1)
        lfs f0, 0x%(CM1)X(r30)
        fmuls f3, f0, f2
        stfs f3, 0x14(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        addi r4, r1, 8
        addi r5, r1, 0x10
        addi r6, r1, 0x18
        %(RAY)s
        lfs f1, 0x%(C50)X(r30)
        cmpwi r3, 0
        beq hg_out
        lfs f1, 0x20(r1)
        lfs f0, 0x1C(r1)
        fsubs f1, f1, f0
    hg_out:
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    # ph_lrcmp: f1 = get_lr_to_nearest_target(posture lr) (3DS 0x9EB178: the nearest fighter's x vs the posture's:
    # 1 / -1, else the given lr), then cr0 = f1 ? posture lr
    ph_lrcmp:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        bl h_near
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x60(r12)
        cmpwi r3, 0
        blt lr_cmp
        mr r5, r3
        addi r3, r1, 8
        mr r4, r31
        %(TPOS)s
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f2, 0x10(r12)
        lfs f3, 8(r1)
        lfs f1, 0x%(C1)X(r30)
        fcmpu cr0, f2, f3
        blt lr_cmp
        lfs f1, 0x%(CM1)X(r30)
        bgt lr_cmp
        lfs f1, 0x60(r12)
    lr_cmp:
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x60(r12)
        fcmpu cr0, f1, f0
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    # ph_hpos(r5 out): where the item hangs (3DS slot 59 0x9A224): node 3 (HipN)'s global position (ModelModule
    # node_global_position(3, &v, 1)) + (0, P7 -10, 0), z = 0
    ph_hpos:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        stw r5, 0x1C(r1)
        li r0, 0
        stw r0, 0(r5)
        stw r0, 4(r5)
        stw r0, 8(r5)
        lwz r3, 0(r31)
        lwz r3, 0x3118(r3)
        li r4, 3
        li r6, 1
        %(NGP)s
        lwz r5, 0x1C(r1)
        lfs f0, 0x%(C0)X(r30)
        lfs f1, 0(r5)
        fadds f1, f1, f0
        stfs f1, 0(r5)
        lfs f1, 4(r5)
        lfs f2, 0x%(P7)X(r30)
        fadds f1, f1, f2
        stfs f1, 4(r5)
        stfs f0, 8(r5)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    # ph_drop: the held item falls (3DS slots 11 / 55: Item::fall(tabemono ? 0 : 1, ZERO)); none held, dropped
    ph_drop:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        bl ph_find
        cmpwi r3, 0
        beq dr_none
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lfs f1, 0x%(C0)X(r30)
        lwz r0, 4(r3)
        cmpwi r0, 0x%(FOOD)X
        beq dr_go
        lfs f1, 0x%(C1)X(r30)
    dr_go:
        addi r4, r1, 8
        %(FALL)s
    dr_none:
        lis r0, 0x5000
        stw r0, 0x%(PI)X(r31)
        li r0, 1
        stw r0, 0x%(PX)X(r31)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    # ph_pick (3DS 0x5A6F0): a held item is removed (Item vt slot 81 remove(0)); then success_by_percent(P9 10):
    # customizeitem 0x21, else (P10 20) goldbag 0x1D, else tabemono 0x0E variation random(0, 28); created and held:
    # Behavior::create_item(kind, var, posture, zero, 1) and the item's have(0x50000000, 0, -1, 0, 0) (slot 95) =
    # the 3DS's create_item_and_have 0x7B4104; PH_I = its id (slot 83), or none
    ph_pick:
        mflr r0
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        stw r28, 0x28(r1)
        lwz r0, 0x%(PI)X(r31)
        lis r12, 0x5000
        cmplw r0, r12
        beq pk_new
        bl ph_find
        cmpwi r3, 0
        beq pk_none
        lwz r12, 0x%(VT)X(r3)
        lwz r12, 0x%(RM)X(r12)
        mtctr r12
        li r4, 0
        bctrl
    pk_none:
        lis r0, 0x5000
        stw r0, 0x%(PI)X(r31)
    pk_new:
        lfs f1, 0x%(P9)X(r30)
        %(SUCC)s
        li r4, 0x%(CUST)X
        li r5, 0
        cmpwi r3, 0
        bne pk_make
        lfs f1, 0x%(P10)X(r30)
        %(SUCC)s
        li r4, 0x%(GOLD)X
        li r5, 0
        cmpwi r3, 0
        bne pk_make
        li r3, 0
        li r4, 28
        bl h_rand
        andi. r5, r3, 0x1FFF
        li r4, 0x%(FOOD)X
    pk_make:
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lwz r6, 0(r31)
        lwz r6, 0x311C(r6)
        addi r6, r6, 0x10
        addi r7, r1, 8
        li r8, 1
        mr r3, r31
        %(CREATE)s
        lis r0, 0x5000
        mr r28, r3
        cmpwi r28, 0
        beq pk_store
        lwz r12, 0x%(VT)X(r28)
        lwz r12, 0x%(HAVE)X(r12)
        mtctr r12
        mr r3, r28
        lis r4, 0x5000
        li r5, 0
        li r6, -1
        li r7, 0
        li r8, 0
        bctrl
        mr r3, r28
        lwz r12, 0x%(VT)X(r3)
        lwz r12, 0x%(ID)X(r12)
        mtctr r12
        bctrl
        mr r0, r3
    pk_store:
        stw r0, 0x%(PI)X(r31)
        lwz r28, 0x28(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    """)
    # ---- start 0x99010: the aerial module, set_rhombus, the fields (the ctor's: PH_I none), +0x10 = posture lr,
    # +0x14 / +0x18 = 0, turned to the nearest fighter (check_turn_to_target -> reverse_lr(1, 1)), the item picked,
    # PH_S = P8 60, PH_DT = P26 100, -> 4. Not ported: set_frame_material / set_rate_material(0) (the prop's material
    # animation stopped), play_se(0x6D20000) (the propeller loop, counted per kind)
    a("""
    f_ph_start:
        mflr r0
        bl pro
        addi r3, r31, 0x%(AER)X
        lwz r4, 0(r31)
        bl 0x%(CTOR)08X
        mr r3, r31
        %(RHOMB)s
        li r0, 0
        li r12, 11
        mtctr r12
        addi r12, r31, 0x%(PHm4)X
    ps_z:
        stwu r0, 4(r12)
        bdnz ps_z
        lis r0, 0x5000
        stw r0, 0x%(PI)X(r31)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x60(r12)
        stw r0, 0x10(r31)
        li r0, 0
        stw r0, 0x14(r31)
        stw r0, 0x18(r31)
        bl h_near
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        beq ps_t
        bl h_rev
    ps_t:
        bl ph_pick
        lwz r0, 0x%(P8)X(r30)
        stw r0, 0x%(PS)X(r31)
        lwz r0, 0x%(P26)X(r30)
        stw r0, 0x%(PDT)X(r31)
        li r4, 4
        b go
    """)
    # slot 59 (0x9A224, every frame): the held item warped to ph_hpos (Item::warp)
    a("""
    f_ph_59:
        mflr r0
        bl pro
        lwz r0, 0x%(PX)X(r31)
        cmpwi r0, 0
        bne.far epi
        bl ph_find
        mr r28, r3
        cmpwi r28, 0
        beq.far epi
        addi r5, r1, 8
        bl ph_hpos
        mr r3, r28
        addi r4, r1, 8
        %(WARP)s
        b epi
    """)
    # slot 55 (0x99E24, after the state's update): in states 4 / 5 with the item still held: PH_S counts down; at 0
    # a new item (ph_pick), PH_S = P8 60, the swap effect 0x100001C at the item ((-5, 5, 0), tabemono (0, 5, 5));
    # else PH_DT counts down; at 0 success_by_percent(P25 10) drops it (ph_drop; not in 5: -> 5, in 5: PH_T = P32
    # 60), or PH_DT = P24 180. Not ported: the body's tilt (posture rot z toward -vx / P15 x P20 in 5, else 0, 1
    # degree a frame; the posture rotation is not mapped) and play_se(0x6D20001) at the swap
    a("""
    f_ph_55:
        mflr r0
        bl pro
        lwz r0, 4(r31)
        cmpwi r0, 5
        beq p55_a
        cmpwi r0, 4
        bne.far epi
    p55_a:
        lwz r0, 0x%(PX)X(r31)
        cmpwi r0, 0
        bne.far epi
        lwz r3, 0x%(PS)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(PS)X(r31)
        cmpwi r3, 0
        bgt p55_drop
        bl ph_pick
        lwz r0, 0x%(P8)X(r30)
        stw r0, 0x%(PS)X(r31)
        bl ph_find
        mr r28, r3
        cmpwi r28, 0
        beq.far epi
        addi r5, r1, 8
        bl ph_hpos
        lfs f2, 0x%(CM5)X(r30)
        lfs f3, 0x%(C5)X(r30)
        lfs f4, 0x%(C0)X(r30)
        lwz r0, 4(r28)
        cmpwi r0, 0x%(FOOD)X
        bne p55_o
        fmr f2, f4
        fmr f4, f3
    p55_o:
        lfs f1, 8(r1)
        fadds f1, f1, f2
        stfs f1, 8(r1)
        lfs f1, 0xC(r1)
        fadds f1, f1, f3
        stfs f1, 0xC(r1)
        lfs f1, 0x10(r1)
        fadds f1, f1, f4
        stfs f1, 0x10(r1)
        li r0, 0
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        stw r0, 0x1C(r1)
        mr r3, r31
        lis r4, 0x%(FXH)04X
        ori r4, r4, 0x%(FXL)04X
        addi r5, r1, 8
        addi r6, r1, 0x14
        lfs f1, 0x%(C1)X(r30)
        %(REQ)s
        b epi
    p55_drop:
        lwz r3, 0x%(PDT)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(PDT)X(r31)
        cmpwi r3, 0
        bgt.far epi
        lfs f1, 0x%(P25)X(r30)
        %(SUCC)s
        cmpwi r3, 0
        beq p55_fail
        bl ph_drop
        lwz r0, 4(r31)
        cmpwi r0, 5
        beq p55_in5
        li r4, 5
        b go
    p55_in5:
        lwz r0, 0x%(P32)X(r30)
        stw r0, 0x%(PT)X(r31)
        b epi
    p55_fail:
        lwz r0, 0x%(P24)X(r30)
        stw r0, 0x%(PDT)X(r31)
        b epi
    """)
    # slot 10 notify_on_damage (the 3DS's 11, 0x9A330): BehaviorImpl's, then a held item falls (ph_drop)
    a("""
    f_ph_dmg:
        mflr r0
        bl pro
        mr r3, r31
        %(BIDMG)s
        lwz r0, 0x%(PX)X(r31)
        cmpwi r0, 0
        bne.far epi
        lwz r0, 0x%(PI)X(r31)
        lis r12, 0x5000
        cmplw r0, r12
        beq.far epi
        bl ph_drop
        b epi
    """)
    # slot 69 (0x9AA1C): => 7 (stun), returns 1 (the framework's damage reaction skipped)
    st('f_ph_69', "li r4, 7\nbl h_chgi\nli r3, 1")
    # slot 27 notify_on_remove (the 3DS's dtors 0x9AC10 / 0x9AC74 remove a held item: vt slot 81 remove(0)), then
    # BehaviorImpl's (r4 kept)
    a("""
    f_ph_rm:
        mflr r0
        bl pro
        bl ph_find
        cmpwi r3, 0
        beq pr_go
        lwz r12, 0x%(VT)X(r3)
        lwz r12, 0x%(RM)X(r12)
        mtctr r12
        li r4, 0
        bctrl
    pr_go:
        lis r0, 0x5000
        stw r0, 0x%(PI)X(r31)
        mr r3, r31
        mr r4, r29
        lmw r28, 0x20(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        lis r12, 0x%(O27H)04X
        ori r12, r12, 0x%(O27L)04X
        mtctr r12
        bctr
    """.replace('%(O27H)04X', '%04X' % (orig(27) >> 16)).replace('%(O27L)04X', '%04X' % (orig(27) & 0xFFFF)))
    zero6 = "lfs f1, 0x%(C0)X(r30)\nfmr f2, f1\nfmr f3, f1\nfmr f4, f1\nlfs f5, 0x%(C10)X(r30)\nfmr f6, f5\nbl ph_anormal"
    tpos = "mr r5, r3\naddi r3, r1, 8\nmr r4, r31\n%(TPOS)s"
    # 1 turn (0x99598 / 0x99D64): set_mode_normal(0, 0, 0.1, 0.1, 10, 10), ground off, passable, TurnAir once; at
    # its end reverse_lr(1, 1), PH_R = 1, => 4; else the aerial update(0, 0, 0)
    st('ph1_en', ("""
        lfs f1, 0x%(C0)X(r30)
        fmr f2, f1
        lfs f3, 0x%(C01)X(r30)
        fmr f4, f3
        lfs f5, 0x%(C10)X(r30)
        fmr f6, f5
        bl ph_anormal
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 2
        li r5, 0
        bl h_mot1""") % d)
    st('ph1_up', ("""
        bl h_end
        cmpwi r3, 0
        beq p1_u
        bl h_rev
        li r0, 1
        stw r0, 0x%(PR)X(r31)
        li r4, 4
        b goi
    p1_u:
        lfs f1, 0x%(C0)X(r30)
        fmr f2, f1
        li r4, 0
        bl ph_upd""") % d)
    # 2 fly away (0x99440 / 0x99CC4): set_mode_normal(0, P28 0.05, 0, 0, 10, 10), set_max_speed(0, P29 4), PH_D = 1,
    # PH_B = 0, speed (0, P27 0), ground off, passable, set_correct(0), Vertical loop at P31 2, PH_F = P30 300; each
    # frame while PH_F > 0 and is_in_view_area: update(0, PH_D, PH_B); else => 8 (removed: a held item goes with it)
    st('ph2_en', ("""
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(P28)X(r30)
        fmr f3, f1
        fmr f4, f1
        lfs f5, 0x%(C10)X(r30)
        fmr f6, f5
        bl ph_anormal
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(P29)X(r30)
        bl ph_maxspd
        lfs f0, 0x%(C1)X(r30)
        stfs f0, 0x%(PD)X(r31)
        li r0, 0
        stw r0, 0x%(PB)X(r31)
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(P27)X(r30)
        lfs f0, 0x%(C1)X(r30)
        fmuls f2, f2, f0
        bl ph_setspd
        li r4, 0
        bl h_att
        bl f_pass1
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0
        bl 0x%(SC)08X
        lfs f2, 0x%(P31)X(r30)
        li r4, 3
        li r5, 1
        bl h_mot
        lwz r0, 0x%(P30)X(r30)
        stw r0, 0x%(PF)X(r31)""") % d)
    st('ph2_up', ("""
        lwz r3, 0x%(PF)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(PF)X(r31)
        cmpwi r3, 0
        ble p2_out
        mr r3, r31
        %(VIEW)s
        cmpwi r3, 0
        beq p2_out
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(PD)X(r30)
        lwz r4, 0x%(PB)X(r31)
        bl ph_upd
        b epi
    p2_out:
        li r4, 8
        b go""").replace('0x%(PD)X(r30)', '0x%(PD)X(r31)') % d)
    # 3 dead (0x99624 / 0x9A2F8): kinetic 23, ground off, passable off, bullet() (P2 entry 0), defeated; the kinetic
    # flag 8 -> 8
    st('ph3_en', ("""
        li r0, 1
        stw r0, 0x%(DEF)X(r31)
        li r4, 23
        bl h_kin
        li r4, 0
        bl h_att
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0
        bl 0x%(SP)08X
        mr r3, r31
        bl 0x%(BUL)08X""") % d)
    st('ph3_up', "li r4, 8\nbl h_flag\nbeq.far epi\nli r4, 8\nb go")
    # 4 height (0x9A578 / 0x9A6F8): set_mode_normal(0, 0, 0, 0, 10, 10), PH_B = 0, ground off, passable, Vertical
    # loop, PH_T = P13 120, PH_D = the nearest fighter's side in y (-1 below / 1), |dy| < P14 3 => 5, speed (0, P12 1
    # x PH_D). Update: going down, low = height_from_ground(1) < 5 - P7 (15); PH_T counts down; at 0, on the ground,
    # low or a ceiling: PH_D = -1 (ceiling), 1 (ground / low), => 5 (PH_T > 0 or PH_R) or to the nearest's side (lr
    # differs => 1 turn, else 5); else at the target's height (within P14) the same choice; else update(0, PH_D, PH_B)
    st('ph4_en', (zero6 + """
        li r0, 0
        stw r0, 0x%(PB)X(r31)
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 3
        li r5, 1
        bl h_mot1
        lwz r0, 0x%(P13)X(r30)
        stw r0, 0x%(PT)X(r31)
        lfs f0, 0x%(C0)X(r30)
        stfs f0, 0x%(PD)X(r31)
        bl h_near
        cmpwi r3, 0
        blt p4e_s
        """ + tpos + """
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        lfs f2, 0xC(r1)
        lfs f0, 0x%(C1)X(r30)
        fcmpu cr0, f1, f2
        ble p4e_d
        lfs f0, 0x%(CM1)X(r30)
    p4e_d:
        stfs f0, 0x%(PD)X(r31)
        fsubs f3, f2, f1
        fabs f3, f3
        lfs f0, 0x%(P14)X(r30)
        fcmpu cr0, f3, f0
        bge p4e_s
        li r4, 5
        b go
    p4e_s:
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(P12)X(r30)
        lfs f0, 0x%(PD)X(r31)
        fmuls f2, f2, f0
        bl ph_setspd""") % d)
    st('ph4_up', ("""
        li r28, 0
        lfs f1, 0x%(PD)X(r31)
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f1, f0
        bge p4_a0
        li r7, 1
        bl ph_hgt
        lfs f0, 0x%(C5)X(r30)
        lfs f2, 0x%(P7)X(r30)
        fsubs f0, f0, f2
        fcmpu cr0, f0, f1
        ble p4_a0
        li r28, 1
    p4_a0:
        lwz r3, 0x%(PT)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(PT)X(r31)
        cmpwi r3, 0
        ble p4_b
        li r4, 8
        bl h_touch
        cmpwi r3, 0
        bne p4_b
        cmpwi r28, 0
        bne p4_b
        li r4, 1
        bl h_touch
        cmpwi r3, 0
        beq p4_a
    p4_b:
        li r4, 1
        bl h_touch
        cmpwi r3, 0
        beq p4_b1
        lfs f0, 0x%(CM1)X(r30)
        stfs f0, 0x%(PD)X(r31)
    p4_b1:
        li r4, 8
        bl h_touch
        or r3, r3, r28
        cmpwi r3, 0
        beq p4_b2
        lfs f0, 0x%(C1)X(r30)
        stfs f0, 0x%(PD)X(r31)
    p4_b2:
        lwz r0, 0x%(PT)X(r31)
        cmpwi r0, 0
        bgt p4_5
    p4_d:
        lwz r0, 0x%(PR)X(r31)
        cmpwi r0, 0
        bne p4_5
        bl ph_lrcmp
        beq p4_5
        li r4, 1
        b go
    p4_5:
        li r4, 5
        b go
    p4_a:
        bl h_near
        cmpwi r3, 0
        blt p4_c
        """ + tpos + """
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        lfs f2, 0xC(r1)
        lfs f4, 0x%(PD)X(r31)
        lfs f0, 0x%(C0)X(r30)
        lfs f5, 0x%(P14)X(r30)
        fcmpu cr0, f4, f0
        ble p4_a2
        fsubs f3, f2, f5
        fcmpu cr0, f1, f3
        bgt p4_d
    p4_a2:
        fcmpu cr0, f4, f0
        bge p4_c
        fadds f3, f2, f5
        fcmpu cr0, f1, f3
        blt p4_d
    p4_c:
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(PD)X(r31)
        lwz r4, 0x%(PB)X(r31)
        bl ph_upd""") % d)
    # 5 patrol (0x991D4 / 0x99848): set_mode_normal(0 x 4, 10, 10), PH_A = 0, PH_B = 1, PH_Y = y, ground off,
    # passable, Move loop at P23 0.5, PH_T = dropped ? P32 60 : random(P18 150, P19 450), PH_DT = P24 180. Update:
    # PH_T at 0: dropped => 2 (fly away); the nearest fighter more than P11 60 away in y => 4 (PH_R = 0); else PH_T =
    # random(150, 450) => 6 (brake). A wall => 1. Else the bob: PH_A += 360 / P17 (int, wrapped at 360), vy =
    # cos(PH_A) x P16 x (360 / P17) / 360; PH_D = the current vy's sign; (going down and below 15 above the ground
    # (height_from_ground(0)), or on the ground) and vy < 0: PH_A = 270, PH_D = 1, PH_Y = y - P16 / 2; else a
    # ceiling and vy > 0: PH_A = 90, PH_D = -1, PH_Y = y + P16 / 2; speed (P15 0.5 x move x, vy); PH_D = vy >= 0;
    # update(move x, PH_D, 0)
    st('ph5_en', (zero6 + """
        li r0, 0
        stw r0, 0x%(PA)X(r31)
        li r0, 1
        stw r0, 0x%(PB)X(r31)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x14(r12)
        stw r0, 0x%(PY)X(r31)
        li r4, 0
        bl h_att
        bl f_pass1
        lfs f2, 0x%(P23)X(r30)
        li r4, 1
        li r5, 1
        bl h_mot
        lwz r0, 0x%(PX)X(r31)
        cmpwi r0, 0
        lwz r3, 0x%(P32)X(r30)
        bne p5e_t
        lwz r3, 0x%(P18)X(r30)
        lwz r4, 0x%(P19)X(r30)
        bl h_rand
    p5e_t:
        stw r3, 0x%(PT)X(r31)
        lwz r0, 0x%(P24)X(r30)
        stw r0, 0x%(PDT)X(r31)""") % d)
    st('ph5_up', ("""
        lwz r3, 0x%(PT)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(PT)X(r31)
        cmpwi r3, 0
        bgt p5_go
        lwz r0, 0x%(PX)X(r31)
        cmpwi r0, 0
        beq p5_n
        li r4, 2
        b go
    p5_n:
        bl h_near
        cmpwi r3, 0
        blt p5_r
        """ + tpos + """
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        lfs f2, 0xC(r1)
        fsubs f3, f2, f1
        fabs f3, f3
        lfs f0, 0x%(P11)X(r30)
        fcmpu cr0, f3, f0
        ble p5_r
        li r4, 4
        bl h_chg
        li r0, 0
        stw r0, 0x%(PR)X(r31)
        b epi
    p5_r:
        lwz r3, 0x%(P18)X(r30)
        lwz r4, 0x%(P19)X(r30)
        bl h_rand
        stw r3, 0x%(PT)X(r31)
        li r4, 6
        b go
    p5_go:
        bl h_wall
        cmpwi r3, 0
        beq p5_w
        li r4, 1
        b go
    p5_w:
        lwz r3, 0x%(PA)X(r31)
        bl ph_i2f
        lfs f0, 0x%(C360)X(r30)
        lfs f2, 0x%(P17)X(r30)
        fdivs f2, f0, f2
        stfs f2, 0x18(r1)
        fadds f1, f1, f2
        bl ph_f2i
        stw r3, 0x%(PA)X(r31)
        cmpwi r3, 360
        blt p5_ang
        bl ph_i2f
        lfs f0, 0x%(C360)X(r30)
        fsubs f1, f1, f0
        bl ph_f2i
        stw r3, 0x%(PA)X(r31)
    p5_ang:
        li r4, 8
        bl h_touch
        mr r28, r3
        li r4, 1
        bl h_touch
        stw r3, 0x14(r1)
        lwz r3, 0x%(PA)X(r31)
        bl ph_i2f
        lfs f0, 0x%(DEG)X(r30)
        fmuls f1, f1, f0
        %(COS)s
        lfs f2, 0x%(P16)X(r30)
        lfs f0, 0x18(r1)
        fmuls f2, f2, f0
        lfs f0, 0x%(I360)X(r30)
        fmuls f2, f2, f0
        fmuls f1, f1, f2
        stfs f1, 0x1C(r1)
        lwz r12, 0x%(E0)X(r31)
        lfs f1, 4(r12)
        lfs f0, 0x%(C0)X(r30)
        lfs f2, 0x%(C1)X(r30)
        fcmpu cr0, f1, f0
        bge p5_dr
        lfs f2, 0x%(CM1)X(r30)
    p5_dr:
        stfs f2, 0x%(PD)X(r31)
        lwz r0, 0x%(PX)X(r31)
        cmpwi r0, 0
        bne p5_g
        lfs f1, 0x%(PD)X(r31)
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f1, f0
        bge p5_g
        li r7, 0
        bl ph_hgt
        lfs f0, 0x%(C5)X(r30)
        lfs f2, 0x%(P7)X(r30)
        fsubs f0, f0, f2
        fcmpu cr0, f0, f1
        bgt p5_l
    p5_g:
        cmpwi r28, 0
        beq p5_m
    p5_l:
        lfs f1, 0x1C(r1)
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f0, f1
        ble p5_m
        li r0, 270
        stw r0, 0x%(PA)X(r31)
        lfs f0, 0x%(C1)X(r30)
        stfs f0, 0x%(PD)X(r31)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        lfs f2, 0x%(P16)X(r30)
        lfs f3, 0x%(HALF)X(r30)
        fmuls f2, f2, f3
        fsubs f1, f1, f2
        b p5_y
    p5_m:
        lwz r0, 0x14(r1)
        cmpwi r0, 0
        beq p5_n2
        lfs f1, 0x1C(r1)
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f1, f0
        ble p5_n2
        li r0, 90
        stw r0, 0x%(PA)X(r31)
        lfs f0, 0x%(CM1)X(r30)
        stfs f0, 0x%(PD)X(r31)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        lfs f2, 0x%(P16)X(r30)
        lfs f3, 0x%(HALF)X(r30)
        fmuls f2, f2, f3
        fadds f1, f1, f2
    p5_y:
        stfs f1, 0x%(PY)X(r31)
    p5_n2:
        lfs f1, 0x%(P15)X(r30)
        lfs f0, 0x10(r31)
        fmuls f1, f1, f0
        lfs f2, 0x1C(r1)
        bl ph_setspd
        lfs f0, 0x1C(r1)
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(C1)X(r30)
        fcmpu cr0, f0, f1
        bge p5_pd
        fmr f2, f1
    p5_pd:
        stfs f2, 0x%(PD)X(r31)
        lfs f1, 0x10(r31)
        li r4, 0
        bl ph_upd""") % d)
    # 6 brake (0x9934C / 0x99BD0): v = the current speed, set_mode_normal(0, 0, P21 0.05 x |vx| / max(|vy|, 0.1),
    # P21, 10, 10), speed v, PH_B = 1, ground off, passable, Move loop. Update: |v|^2 < 0.01: success_by_percent(P22
    # 100) => 2 (fly away); else the nearest's side differs => 1, else => 4 (PH_R = 0); moving: update(move x, PH_D,
    # PH_B)
    st('ph6_en', ("""
        addi r3, r1, 8
        mr r4, r31
        %(GSPD)s
        lfs f1, 8(r1)
        fabs f1, f1
        lfs f2, 0xC(r1)
        fabs f2, f2
        lfs f0, 0x%(C01)X(r30)
        fcmpu cr0, f2, f0
        bge p6_a
        fmr f2, f0
    p6_a:
        lfs f4, 0x%(P21)X(r30)
        fmuls f3, f4, f1
        fdivs f3, f3, f2
        lfs f1, 0x%(C0)X(r30)
        fmr f2, f1
        lfs f5, 0x%(C10)X(r30)
        fmr f6, f5
        bl ph_anormal
        lfs f1, 8(r1)
        lfs f2, 0xC(r1)
        bl ph_setspd
        li r0, 1
        stw r0, 0x%(PB)X(r31)
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 1
        li r5, 1
        bl h_mot1""") % d)
    st('ph6_up', ("""
        addi r3, r1, 8
        mr r4, r31
        %(GSPD)s
        lfs f1, 8(r1)
        fmuls f0, f1, f1
        lfs f1, 0xC(r1)
        fmuls f1, f1, f1
        fadds f0, f0, f1
        lfs f1, 0x10(r1)
        fmuls f1, f1, f1
        fadds f0, f0, f1
        lfs f1, 0x%(STOP)X(r30)
        fcmpu cr0, f0, f1
        bge p6_mv
        lfs f1, 0x%(P22)X(r30)
        %(SUCC)s
        cmpwi r3, 0
        beq p6_lr
        li r4, 2
        b go
    p6_lr:
        bl ph_lrcmp
        beq p6_4
        li r4, 1
        b go
    p6_4:
        li r4, 4
        bl h_chg
        li r0, 0
        stw r0, 0x%(PR)X(r31)
        b epi
    p6_mv:
        lfs f1, 0x10(r31)
        lfs f2, 0x%(PD)X(r31)
        lwz r4, 0x%(PB)X(r31)
        bl ph_upd""") % d)
    # 7 stun (0x99148 / 0x99674): Damage once, kinetic 16, ground off, damage_turn(), PH_T = hit_return_frame(), the
    # kinetic flag 0x80; update: on the ground clear_speed_all; PH_T below 0: flag 0x80 off, => 4; else move(ai).
    # Not ported: the posture's z rotation back to 0 (5 degrees a frame)
    st('ph7_en', ("""
        li r4, 0
        li r5, 0
        bl h_mot1
        li r4, 16
        bl h_kin
        li r4, 0
        bl h_att
        mr r3, r31
        %(DTURN)s
        bl f_hitret
        stw r3, 0x%(PT)X(r31)
        bl f_kflag
        lwz r0, 0(r12)
        ori r0, r0, 0x80
        stw r0, 0(r12)""") % d)
    st('ph7_up', ("""
        bl h_gnd
        cmpwi r3, 0
        beq p7_a
        bl h_clear
    p7_a:
        lwz r3, 0x%(PT)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(PT)X(r31)
        cmpwi r3, 0
        bge p7_mv
        bl f_kflag
        lwz r0, 0(r12)
        rlwinm r0, r0, 0, 25, 23
        stw r0, 0(r12)
        li r4, 4
        b goi
    p7_mv:
        bl h_mv""") % d)


def assemble(vt_words):
    """(A, B, Data): the code in regions A, B and E (A.area / A.stomp / A.e: the units of C, D, E), the data after
    it (passes until the data's addresses settle: the code's size does not depend on them)"""
    d = Data(vt_words)
    VT_WORDS[0] = vt_words
    D = {}
    keys = [lab for lab, _w, _a in Data(vt_words).build({}).blocks]
    for _pass in range(4):
        dd = {k: D.get(k, CAVE) for k in keys}
        A, B, Ee, Gg = code(dd)
        C = area_code(dd)
        Dd = stomp_code()
        labels = dict(A.labels)
        for a in (B, C, Dd, Ee, Gg):
            labels.update(a.labels)
        for a in (A, B, C, Dd, Ee, Gg):
            a.labels.update(labels)
        ea, eb, ec, ed, ee, eg = A.pc, B.pc, C.pc, Dd.pc, Ee.pc, Gg.pc
        assert eg <= LIMIT_G, 'flier code too big (0x%X)' % eg
        assert ed <= LIMIT_D, 'stomp code too big (0x%X)' % ed
        assert ea <= LIMIT and eb <= LIMIT_B and ee <= LIMIT_E, 'walker code too big (0x%X, 0x%X, 0x%X)' % (ea, eb, ee)
        spans = [((ea + 0xF) & ~0xF, LIMIT), ((eb + 0xF) & ~0xF, LIMIT_B), ((ec + 0xF) & ~0xF, LIMIT_C),
                 ((ed + 3) & ~3, LIMIT_D), ((ee + 0xF) & ~0xF, LIMIT_E), ((eg + 0xF) & ~0xF, LIMIT_G)] + list(DATA_F)
        d.build(labels, D)
        d.place(spans)
        if d.addr == D:
            break
        D = dict(d.addr)
    d.build(labels, D)
    d.place(spans)
    assert d.addr == D
    A.area = C
    A.stomp = Dd
    A.e = Ee
    A.g = Gg
    return A, B, d


def stomp_code():
    """fix v8: slot 3 (update) -> w_upd: for a kind with a TREAD state, not in it nor dying / removed, each live
    fighter (slots 0-3) whose feet (posture y) went from at / above the tread box's top last frame to at / below it
    now, not below its bottom, within its half width -> change_state_interrupt(TREAD) and the fighter's
    StatusModule(3, STEP_JUMP, 0) (MSC's change status, as position_vars_cave.py does it); then BehaviorImpl's update"""
    Dd = Asm(CAVE_D)
    Dd.asm("""
    w_upd:
        stwu r1, -0x60(r1)
        mflr r0
        stw r0, 0x64(r1)
        stmw r24, 0x20(r1)
        stw r4, 0x40(r1)
        mr r31, r3
        lwz r30, 0x168(r3)
        lwz r29, 0x%(TREAD)X(r30)
        cmpwi r29, 0
        beq u_out
        lwz r0, 4(r31)
        cmpw r0, r29
        beq u_out
        lwz r12, 0x%(R67)X(r30)
        cmpw r0, r12
        beq u_out
        lwz r12, 0x%(DF)X(r31)
        cmpwi r12, 0
        bne u_out
        lwz r12, 0(r31)
        lwz r28, 0x311C(r12)
        addi r27, r30, 0x%(TB)X
        lwz r4, 0x%(TN)X(r30)
        cmpwi r4, 0
        beq u_post
        lwz r3, 0x3118(r12)
        addi r5, r1, 0x50
        li r6, 1
        lis r12, 0x%(NGH)04X
        ori r12, r12, 0x%(NGL)04X
        mtctr r12
        bctrl
        addi r28, r1, 0x40
    u_post:
        lis r12, 0x%(FH)04X
        lwz r12, %(FL)d(r12)
        cmpwi r12, 0
        beq u_out
        lwz r26, 0(r12)
        cmpwi r26, 0
        beq u_out
        li r25, -1
    u_next:
        addi r25, r25, 1
        lwz r0, 8(r26)
        cmpw r25, r0
        bge u_out
        cmplwi r25, 4
        bge u_out
        b u_body
    u_out:
        mr r3, r31
        lwz r4, 0x40(r1)
        lmw r24, 0x20(r1)
        lwz r0, 0x64(r1)
        mtlr r0
        addi r1, r1, 0x60
        lis r12, 0x%(BH)04X
        ori r12, r12, 0x%(BL)04X
        mtctr r12
        bctr
    """ % dict(TREAD=CF['TREAD'], R67=CF['R67'], FH=ha(FIGHTERS), FL=sx(FIGHTERS), BH=BI_UPDATE >> 16,
               BL=BI_UPDATE & 0xFFFF, TB=CF['TB0'], DF=DEFEATED, TN=CF['TNODE'], NGH=NODE_GPOS >> 16,
               NGL=NODE_GPOS & 0xFFFF))
    return Dd


def stomp_body(C):
    """the per-fighter test (in region C, after the area hooks; r25 slot, r26 the fighter table, r27 tbox, r28 the
    enemy's posture, r29 its TREAD state, r31 this)"""
    C.asm("""
    u_body:
        lwz r12, 0(r26)
        mulli r11, r25, 0x%(ENT)X
        add r12, r12, r11
        lbz r11, 0x1E(r12)
        cmplwi r11, 4
        blt b_next
        lwz r24, 0xC(r12)
        lwz r11, 0x18(r24)
        lfs f1, 0x14(r11)
        lfs f3, 0x14(r28)
        lfs f4, 4(r27)
        fadds f3, f3, f4
        lfs f5, 8(r27)
        fadds f4, f3, f5
        fsubs f1, f1, f4
        slwi r10, r25, 2
        add r10, r10, r31
        lwz r0, 0x%(PREV)X(r10)
        lfs f2, 0x%(PREV)X(r10)
        stfs f1, 0x%(PREV)X(r10)
        cmpwi r0, 0
        beq b_next
        fsubs f0, f1, f1
        fcmpu cr0, f2, f0
        blt b_next
        fcmpu cr0, f1, f0
        bgt b_next
        fadds f6, f5, f5
        lis r0, 0x%(SWH)04X
        stw r0, 0x1C(r1)
        lfs f7, 0x1C(r1)
        fadds f6, f6, f7
        fneg f6, f6
        fcmpu cr0, f1, f6
        blt b_next
        lfs f6, 0x10(r11)
        lfs f7, 0x10(r28)
        fsubs f6, f6, f7
        fabs f6, f6
        lfs f7, 0(r27)
        fcmpu cr0, f6, f7
        bgt b_next
        mr r3, r31
        mr r4, r29
        lwz r12, 0xE0(r3)
        lwz r12, 0x%(S73)X(r12)
        mtctr r12
        bctrl
        li r0, 3
        stw r0, 0x10(r1)
        stw r0, 0x4C(r1)
        li r0, 0x%(STEP)X
        stw r0, 0x14(r1)
        li r0, 0
        stw r0, 0x18(r1)
        stw r0, 8(r1)
        stw r24, 0xC(r1)
        addi r0, r1, 0x10
        stw r0, 0x48(r1)
        addi r3, r1, 8
        addi r4, r1, 0x48
        lis r12, 0x%(MH)04X
        ori r12, r12, 0x%(ML)04X
        mtctr r12
        bctrl
        b u_out
    b_next:
        b u_next
    """ % dict(ENT=FIGHTER_ENTRY, PREV=PREV, S73=SLOT[73], STEP=STEP_JUMP, MH=MSC_STATUS >> 16,
               ML=MSC_STATUS & 0xFFFF, SWH=struct.unpack('>I', struct.pack('>f', STOMP_SWEEP))[0] >> 16))


def area_code(D):
    """fix v7: the three game sites that read a kind's area table [param slot]+0x70 (2 x {on, node, 4 floats}:
    area 0 the tread area, kind 0xE; area 1 kind 9) -> the walker kind's own table (its 3DS vl's), else the slot's
    (r9 / r0 / r12 free at each site; the functions keep LR on the stack)"""
    C = Asm(CAVE_C)
    C.asm("""
    area_tab:
        lis r12, 0x%04X
        addi r12, r12, %d
    at_loop:
        lwz r0, 0(r12)
        cmpwi r0, -1
        beq at_none
        cmpw r0, r9
        beq at_found
        addi r12, r12, 8
        b at_loop
    at_found:
        lwz r12, 4(r12)
        lwz r9, 0x%X(r12)
        blr
    at_none:
        li r9, 0
        blr
    """ % (ha(D['ktab']), sx(D['ktab']), CF['AREA']))
    for i, (site, word_, dst, base, kind_reg, shifted) in enumerate(AREA_SITES):
        C.asm("""
    area_%d:
        lwz r%d, 0x70(r%d)
        %s
        bl area_tab
        cmpwi r9, 0
        beq ar%d_out
        mr r%d, r9
    ar%d_out:
        b 0x%08X
        """ % (i, dst, base, ('srwi r9, r%d, 2' if shifted else 'mr r9, r%d') % kind_reg, i, dst, i, site + 4))
    stomp_body(C)
    return C


def read_vt(img):
    return [img.u32(BI_VT + 4 * i) for i in range((0xC + 8 * 74) // 4)]


def patches(img):
    A, B, d = assemble(read_vt(img))
    out = {}
    for lo_, hi_ in REGIONS:
        for addr in range(lo_, hi_, 4):
            out[addr] = 0
    for a in (A, B, A.area, A.stomp, A.e, A.g):
        for i, w in enumerate(a.words()):
            out[a.base + 4 * i] = w
    for base, words in d.chunks:
        for i, w in enumerate(words):
            out[base + 4 * i] = w
    out[SITE_F] = branch(SITE_F, A.addr('cave_f'))
    out[SITE_T] = branch(SITE_T, A.addr('cave_t'))
    out[SITE_S] = branch(SITE_S, A.addr('cave_s'))
    out[SITE_ROT] = branch(SITE_ROT, A.addr('cave_rot'))
    out[SITE_DEATH] = branch(SITE_DEATH, A.addr('cave_death'))
    for i, (site, _w, _d, _b, _k, _s) in enumerate(AREA_SITES):
        out[site] = branch(site, A.addr('area_%d' % i))
    for w, fn in TWIN_FLIP:
        out[w] = fn if KEEP_FLIP else A.addr('twin_flip')
    for w, orig, lab in TWIN_LR:
        # the game's word, or an earlier build's w_slr / w_rlr (anywhere in region G: later code moves them)
        assert img.u32(w) == orig or A.g.base <= img.u32(w) < A.g.base + 0x8000, hex(w)
        out[w] = A.g.addr(lab)
    return out, (A, B), d


def args(img):
    out, _a, _d = patches(img)
    res = ['textregion:0x%X' % TEXT_REGION, 'grow:0x%08X' % GROW] + ['0x%08X=0x%08X' % (k, v) for k, v in sorted(out.items())]
    if not KEEP_FLIP:
        res += ['reloc:0x%08X-0x%08X=0x%08X' % (w, w + 4, RELOC_DUMMY) for w, _fn in TWIN_FLIP]
    res += ['reloc:0x%08X-0x%08X=0x%08X' % (w, w + 4, RELOC_DUMMY) for w, _o, _l in TWIN_LR]
    return res


def in_cave(addr):
    return any(lo_ <= addr < hi_ for lo_, hi_ in REGIONS)


def main():
    global KEEP_FLIP
    if '--keep-flip' in sys.argv:
        sys.argv.remove('--keep-flip')
        KEEP_FLIP = True
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    import smashrun_enemy_cave as E
    img = E.Image(sys.argv[1])
    if len(sys.argv) == 2:
        print(' '.join(args(img)))
        return
    import rpx_patch
    for site, want in ((SITE_F, WORD_F), (SITE_T, WORD_T), (SITE_S, WORD_S), (SITE_ROT, WORD_ROT),
                       (SITE_DEATH, WORD_DEATH)) + tuple((s, w) for s, w, _d, _b, _k, _x in AREA_SITES):
        got = img.u32(site)
        assert got == want or (got >> 26 == 18 and in_cave(branch_target(site, got))), \
            '0x%08X holds 0x%08X, expected 0x%08X' % (site, got, want)
    if img.u32(E.SITE_F) >> 26 != 18:
        print('warning: tools/smashrun_enemy_cave.py is not applied (it clears this space and aliases its kinds)',
              file=sys.stderr)
    sys.argv = ['rpx_patch.py', sys.argv[1], sys.argv[2]] + args(img)
    rpx_patch.main()


if __name__ == '__main__':
    main()
