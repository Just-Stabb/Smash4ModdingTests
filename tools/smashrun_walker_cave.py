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
  overrides: 12 zima's 0x026D6E18 (capture motion), 20 w_tread (stepped on, below), 38 w_noflip (0, fix v3; --keep-flip: zima's `li r3, 1`),
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
REGIONS = ((CAVE, LIMIT), (CAVE_B, LIMIT_B), (CAVE_C, LIMIT_C), (CAVE_D, LIMIT_D), (CAVE_E, LIMIT_E)) + DATA_F
GROW = LIMIT_C

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
REQ_FOLLOW = 0x026A9584              # request_follow_effect(id, node, &offset, &rot, scale) -> handle (3DS 0x7B4AEC)
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
TWIN_FLIP = ((0x1008FFCC, 0x026D7C98), (0x1008F1D4, 0x026D19F4), (0x1008EC68, 0x026CF200))
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
SLOT = {50: 0xC + 8 * 50, 72: 0xC + 8 * 72, 73: 0xC + 8 * 73}     # reverse_lr, change_state, interrupt

# CFG (per kind)
CF = {}
for _i, _n in enumerate(('KIND NST TAB START START01 R64 R65 R66 R67 REMOVE DEADMOT HASH EN ENN KICK SET ATK SRCH '
                         'FALLMOT LANDST LANDMOT TURNMOT TURNST WALKST HOPTHR HOPLAND HOPFLAG HOPMOT HOPLOOP ZERO TREAD AREA '
                         'SMODE LEAVE').split()):
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
ATTACKS = {'kuribo_bump': KURIBO_BUMP, 'heiho_bump': HEIHO_BUMP, 'bullet': BULLET_ATK, 'heiho_bullet': HEIHO_BULLET,
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
    return [index(w, s) for s in DAMAGE_LABELS] + [index(w, w['last'])]


def cfg_values(w, D):
    """the kind's CFG words (D: data labels)"""
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
             SMODE=w.get('smode', 0), LEAVE=w.get('leave', 0))
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
        vt = list(self.vt_words) + [0, 0, 0, 0]          # 74 slots + 74 / 75
        over = {12: ZIMA_CAPTURE_MOTION, 38: ZIMA_ONE if KEEP_FLIP else fn('w_noflip'), 40: fn('w_init'),
                3: fn('w_upd'), 41: fn('w_start'), 45: fn('w_atk'), TREAD_SLOT: fn('w_tread'), 64: fn('w_r64'), 65: fn('w_r65'), 66: fn('w_r66'),
                67: fn('w_r67'), 72: fn('w_chg'), 73: fn('w_chgi'), 74: fn('w_chg'), 75: fn('w_chgi')}
        for k, f in over.items():
            vt[(0xC + 8 * k) // 4] = f
            vt[(0x8 + 8 * k) // 4] = 0
        b.append(('vt', vt, 4))
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
                st += [0xFFFF, fn(s[0]), 0xFFFF, fn(s[1]), 0, 0] if s else [0] * 6
            b.append(('st_' + n, st, 4))
            b.append(('ar_' + n, [word(v) for e in w['areas'] for v in e], 4))
            need = ('st_', 'en_', 'set_', 'atk_', 'sr_', 'ar_') + (('hs_',) if w['hashset'] else ())
            b.append(('cfg_' + n, cfg_values(w, {p + n: g(p + n) for p in need}), 4))
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
        li r3, 0x%X
        bl 0x%08X
        mr. r27, r3
        beq c_out
        mr r4, r28
        mr r5, r29
        mr r6, r30
        bl 0x%08X
        li r0, 0
        addi r11, r27, 0xE0
        li r12, %d
        mtctr r12
    c_zero:
        stwu r0, 4(r11)
        bdnz c_zero
        li r0, 1
        stb r0, 0x120(r27)
        li r0, -1
        stw r0, 0x15C(r27)
    """ % (OBJ_SIZE, OPNEW, BEH_CTOR, (OBJ_SIZE - 0xE4) // 4))
    la(A, 'r11', 'vt')
    A.asm("""
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
    """ % (ha(COMMON_PMF), sx(COMMON_PMF), sx(COMMON_PMF + 4), CF['HASH'], SET_MOTION_LABEL, CF['DMG']))
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
        li r3, 0
        blr
    twin_flip:
        lwz r0, 8(r3)
        li r3, 1
        cmplwi r0, 0x50
        bgelr
        li r3, 0
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
    """ % (0xC + 8 * SET_LR_SLOT, SITE_ROT + 4, ha(D['vt']), sx(D['vt']), DEFEATED, SITE_DEATH + 4))
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
    return A, B, code_e(D, en, st, far, lfs)


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
        li r4, 7
        b go""" % dict(V5=V(5), V6=V(6), RMH=REMOVE_EFFECT >> 16, RML=REMOVE_EFFECT & 0xFFFF))
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


def assemble(vt_words):
    """(A, B, Data): the code in regions A, B and E (A.area / A.stomp / A.e: the units of C, D, E), the data after
    it (passes until the data's addresses settle: the code's size does not depend on them)"""
    d = Data(vt_words)
    D = {}
    keys = [lab for lab, _w, _a in Data(vt_words).build({}).blocks]
    for _pass in range(4):
        dd = {k: D.get(k, CAVE) for k in keys}
        A, B, Ee = code(dd)
        C = area_code(dd)
        Dd = stomp_code()
        labels = dict(A.labels)
        for a in (B, C, Dd, Ee):
            labels.update(a.labels)
        for a in (A, B, C, Dd, Ee):
            a.labels.update(labels)
        ea, eb, ec, ed, ee = A.pc, B.pc, C.pc, Dd.pc, Ee.pc
        assert ed <= LIMIT_D, 'stomp code too big (0x%X)' % ed
        assert ea <= LIMIT and eb <= LIMIT_B and ee <= LIMIT_E, 'walker code too big (0x%X, 0x%X, 0x%X)' % (ea, eb, ee)
        spans = [((ea + 0xF) & ~0xF, LIMIT), ((eb + 0xF) & ~0xF, LIMIT_B), ((ec + 0xF) & ~0xF, LIMIT_C),
                 ((ed + 3) & ~3, LIMIT_D), ((ee + 0xF) & ~0xF, LIMIT_E)] + list(DATA_F)
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
    return A, B, d


def stomp_code():
    """fix v8: slot 3 (update) -> w_upd: for a kind with a TREAD state, not in it nor dying / removed, each live
    fighter (slots 0-3) whose feet (posture y) went from at / above the tread box's top last frame to at / below it
    now, not below its bottom, within its half width -> change_state_interrupt(TREAD) and the fighter's
    StatusModule(3, STEP_JUMP, 0) (MSC's change status, as position_vars_cave.py does it); then BehaviorImpl's update"""
    Dd = Asm(CAVE_D)
    Dd.asm("""
    w_upd:
        stwu r1, -0x50(r1)
        mflr r0
        stw r0, 0x54(r1)
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
        lwz r12, 0(r31)
        lwz r28, 0x311C(r12)
        lis r27, tbox@ha
        addi r27, r27, tbox@l
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
        lwz r0, 0x54(r1)
        mtlr r0
        addi r1, r1, 0x50
        lis r12, 0x%(BH)04X
        ori r12, r12, 0x%(BL)04X
        mtctr r12
        bctr
    tbox:
        .float %(HW)r
        .float %(CY)r
        .float %(HH)r
    """ % dict(TREAD=CF['TREAD'], R67=CF['R67'], FH=ha(FIGHTERS), FL=sx(FIGHTERS), BH=BI_UPDATE >> 16,
               BL=BI_UPDATE & 0xFFFF, HW=TREAD_BOX[0], CY=TREAD_BOX[1], HH=TREAD_BOX[2]))
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
        slwi r10, r25, 2
        add r10, r10, r31
        lwz r0, 0x%(PREV)X(r10)
        lfs f2, 0x%(PREV)X(r10)
        stfs f1, 0x%(PREV)X(r10)
        cmpwi r0, 0
        beq b_next
        lfs f3, 0x14(r28)
        lfs f4, 4(r27)
        fadds f3, f3, f4
        lfs f5, 8(r27)
        fadds f4, f3, f5
        fcmpu cr0, f2, f4
        blt b_next
        fcmpu cr0, f1, f4
        bgt b_next
        fsubs f6, f3, f5
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
               ML=MSC_STATUS & 0xFFFF))


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
    for a in (A, B, A.area, A.stomp, A.e):
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
    return out, (A, B), d


def args(img):
    out, _a, _d = patches(img)
    res = ['grow:0x%08X' % GROW] + ['0x%08X=0x%08X' % (k, v) for k, v in sorted(out.items())]
    if not KEEP_FLIP:
        res += ['reloc:0x%08X-0x%08X=0x%08X' % (w, w + 4, RELOC_DUMMY) for w, _fn in TWIN_FLIP]
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
