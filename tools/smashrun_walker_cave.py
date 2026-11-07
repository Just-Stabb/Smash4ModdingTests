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
  the same height or a wall ahead => 4, else => 3), 10 dead, 11 remove; 3 / 1 / 1 / 10. No contact attack.
Churine 0x1F: 1 fall, 2 landing (end: unless it came from a hop, the nearest target behind -> 5; else 3), 3 walk
  (initialize again, Walk, kinetic 1; a wall -> 4; a ledge -> 5), 4 jump (initialize, kinetic 5, Jump; landed on
  the same height (row +0x18: 20) or a wall ahead => 5, else => 2), 5 turn (=> 3), 8 dead, 9 remove; 3 / 1 / 1 /
  8. No contact attack.

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
weapon_expand.py, up to the text region's end 0x04BB8670; grow:0x04BB8660). Code in the first two, data after it.
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
REGIONS = ((CAVE, LIMIT), (CAVE_B, LIMIT_B), (CAVE_C, LIMIT_C))
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
NOTIFY_DEATH = 0x0269FD6C            # BehaviorImpl::notify_on_death (slot 71: death flag, hit off, attacks cleared)
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

OBJ_SIZE = 0x1A0                     # BehaviorImpl 0x168, +0x168 CFG*, +0x16C V0..V8, +0x190 Y0


def V(i):
    return 0x16C + 4 * i


Y0 = 0x190
SLOT = {50: 0xC + 8 * 50, 72: 0xC + 8 * 72, 73: 0xC + 8 * 73}     # reverse_lr, change_state, interrupt

# CFG (per kind)
CF = {}
for _i, _n in enumerate(('KIND NST TAB START START01 R64 R65 R66 R67 REMOVE DEADMOT HASH EN ENN KICK SET ATK SRCH '
                         'FALLMOT LANDST LANDMOT TURNMOT TURNST WALKST HOPTHR HOPLAND HOPFLAG HOPMOT HOPLOOP ZERO TREAD').split()):
    CF[_n] = 4 * _i
CF['DMG'] = 4 * len(CF)              # 9 words
CF['P'] = CF['DMG'] + 4 * 9          # the kind's own values P0..P7
CFG_SIZE = CF['P'] + 4 * 8


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
ATTACKS = {'kuribo_bump': KURIBO_BUMP, 'heiho_bump': HEIHO_BUMP, 'bullet': BULLET_ATK, 'heiho_bullet': HEIHO_BULLET,
           'churine_bullet': CHURINE_BULLET}
DAMAGE_LABELS = ('DamageStart', 'DamageFly', 'DamageFall', 'DownBound', 'DownBound', 'DownLoop', 'DownBoundEnd',
                 'DownWait')

# kinds (index in the name table 0x1041A22C). motions: the 3DS motion_data_set_<name> order (name, Wii U flags).
# energy: {offset: value} of the kind's 3DS initialize (variation 0); kick: it calls the kinetic module's vt
# (0x20000004). states: {3DS id: (enter, update)} (labels of this file, or game addresses). search: the vl search
# groups {type, interval, 5 floats}. attacks: (state, attack). P: the kind's own values (P0..).
WALKERS = (
    dict(name='kuribo', kind=0x01,
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
    dict(name='heiho', kind=0x0B,
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
    dict(name='waddledee', kind=0x13,
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
         search=((2, 30, 300.0, 100.0, 0.0, 10.0, 0.0),),
         attacks=((7, 'bullet'),),
         P=(1.2, 100, 50, 50)),       # walk rate (+0x84), jump interval / chance %, wall jump chance % (+0x78..)
    dict(name='waddledoo', kind=0x19,
         motions=(('BeamShot', 1), ('BeamShotHold', 1), ('Damage', 1), ('DamageFall', 1), ('DamageFly', 1),
                  ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1),
                  ('Fall', 1), ('Jump', 1), ('Landing', 1), ('Turn', 1), ('Walk', 1)),
         dead='Damage', last='Jump', hashset=False, kick=False,
         energy={8: 0.3, 0x10: 0.3, 0x20: 0.5, 0x24: 2.4, 0x28: 0.5, 0x2C: 2.4},
         states={1: ('g_fall_en', 'g_fall_up'), 2: ('g_land_en', 'g_landt_up'), 3: ('o_walk_en', 'o_walk_up'),
                 4: ('g_turn_en', 'g_turn_up'), 5: ('g_hop_en', 'g_hop_up'), 10: ('g_dead_en', 'g_dead_up'),
                 11: 'remove'},
         start=(1, 1), rets=(3, 1, 1, 10), remove=11, fall=('Fall', 2), landing='Landing', turn='Turn', turnst=4,
         walkst=3, hop=(1.0, 3, 0), hop_motion=('Jump', 0),
         search=((2, 60, 200.0, 200.0, 0.0, 0.0, 0.0), (2, 20, 60.0, 70.0, 30.0, 20.0, 0.0)),
         attacks=((10, 'bullet'),),
         P=()),
    dict(name='churine', kind=0x1F,
         motions=(('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1),
                  ('DownLoop', 1), ('DownWait', 1), ('Jump', 1), ('Landing', 1), ('SleepPowder', 1), ('Turn', 1),
                  ('Walk', 1), ('Fall', 1)),
         dead='DamageStart', last='Fall', hashset=True, kick=False,
         energy={8: 0.7, 0x10: 0.1, 0x14: 0.05, 0x20: 0.2, 0x24: 2.5, 0x28: 0.2, 0x2C: 2.5},
         states={1: ('g_fall_en', 'g_fall_up'), 2: ('g_land_en', 'g_landt_up'), 3: ('c_walk_en', 'c_walk_up'),
                 4: ('c_jump_en', 'g_hop_up'), 5: ('g_turn_en', 'g_turn_up'), 8: ('g_dead_en', 'g_dead_up'),
                 9: 'remove'},
         start=(1, 1), rets=(3, 1, 1, 8), remove=9, fall=('Fall', 2), landing='Landing', turn='Turn', turnst=5,
         walkst=3, hop=(20.0, 2, 1),
         search=((2, 3, 100.0, 35.0, 5.0, 5.0, 0.0),),
         attacks=((8, 'churine_bullet'),),
         P=()),
)
KINDS = tuple(w['kind'] for w in WALKERS)


def stem(name, sfx):
    return 'Enm%sBodyMain%s' % (name.capitalize(), sfx)


def motion_hash(s):
    return zlib.crc32(s.encode(), 0xFFFFFFFF)


def index(w, sfx):
    return [m for m, _f in w['motions']].index(sfx) if sfx else -1


def damage_labels(w):
    return [index(w, s) for s in DAMAGE_LABELS] + [index(w, w['last'])]


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


def cfg_values(w, D):
    """the kind's CFG words (D: data labels)"""
    n = w['name']
    lm = lambda s: index(w, s) if s else 0  # noqa: E731
    c = dict(KIND=w['kind'], NST=nstates(w), TAB=D['st_' + n], START=w['start'][0], START01=w['start'][1],
             R64=w['rets'][0], R65=w['rets'][1], R66=w['rets'][2], R67=w['rets'][3], REMOVE=w['remove'],
             DEADMOT=lm(w['dead']), HASH=D.get('hs_' + n, 0), EN=D['en_' + n], ENN=len(w['energy']),
             KICK=1 if w['kick'] else 0, SET=D['set_' + n], ATK=D['atk_' + n], SRCH=D['sr_' + n],
             FALLMOT=lm(w['fall'][0]), LANDST=w['fall'][1], LANDMOT=lm(w['landing']), TURNMOT=lm(w['turn']),
             TURNST=w['turnst'], WALKST=w['walkst'], HOPTHR=fword(w['hop'][0]), HOPLAND=w['hop'][1],
             HOPFLAG=w['hop'][2], HOPMOT=lm(w.get('hop_motion', (None, 0))[0]),
             HOPLOOP=w.get('hop_motion', (None, 0))[1], ZERO=0, TREAD=w.get('tread', 0))
    words = [0] * (CFG_SIZE // 4)
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
        vt = list(self.vt_words) + [0, 0, 0, 0]          # 74 slots + 74 / 75
        over = {12: ZIMA_CAPTURE_MOTION, 38: ZIMA_ONE if KEEP_FLIP else fn('w_noflip'), 40: fn('w_init'),
                41: fn('w_start'), 45: fn('w_atk'), TREAD_SLOT: fn('w_tread'), 64: fn('w_r64'), 65: fn('w_r65'), 66: fn('w_r66'),
                67: fn('w_r67'), 72: fn('w_chg'), 73: fn('w_chgi'), 74: fn('w_chg'), 75: fn('w_chgi')}
        for k, f in over.items():
            vt[(0xC + 8 * k) // 4] = f
            vt[(0x8 + 8 * k) // 4] = 0
        b.append(('vt', vt, 0x10))
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
            for i in range(nstates(w)):
                s = w['states'].get(i)
                if s == 'remove':
                    s = (ZIMA_REMOVE_ENTER, ZIMA_REMOVE_UPDATE)
                st += [0xFFFF, fn(s[0]), 0xFFFF, fn(s[1]), 0, 0] if s else [0] * 6
            b.append(('st_' + n, st, 4))
            need = ('st_', 'en_', 'set_', 'atk_', 'sr_') + (('hs_',) if w['hashset'] else ())
            b.append(('cfg_' + n, cfg_values(w, {p + n: g(p + n) for p in need}), 4))
        return self

    def place(self, spans):
        """first fit into spans [(lo, hi)]; sets .addr, .chunks [(base, words)]"""
        spans = [list(s) for s in spans]
        self.addr, self.chunks = {}, []
        for label, words, al in self.blocks:
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
        mr r3, r27
    """ % (ha(COMMON_PMF), sx(COMMON_PMF), sx(COMMON_PMF + 4), CF['HASH'], SET_MOTION_LABEL))
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
    A.asm("""
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
    """ % ((OBJ_SIZE - 0x16C) // 4, CF['START'], CF['START01']))
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
        blt c2_in
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
    st(A, 'g_dead_en', "lwz r4, 0x%X(r30)\nli r5, 0\nbl h_mot0\nmr r3, r31\nbl 0x%08X" % (CF['DEADMOT'], BULLET))
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
    en(A, 'k_col_en', 0, 1, 0, 0, extra="mr r3, r31\nlis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctrl"
       % (NOTIFY_DEATH >> 16, NOTIFY_DEATH & 0xFFFF))
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
        b go""")
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
        li r4, 3
    death_go:
        mflr r0
        b 0x%08X
    """ % (0xC + 8 * SET_LR_SLOT, SITE_ROT + 4, SITE_DEATH + 4))
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
    return A, B


def assemble(vt_words):
    """(A, B, Data): the code in regions A and B, the data after it (two passes: the code's size does not depend
    on the data's addresses)"""
    d = Data(vt_words)
    D = {}
    for _pass in range(3):
        dd = {k: D.get(k, CAVE) for k in ('consts', 'vt', 'ktab') + tuple(
            p + w['name'] for w in WALKERS for p in ('set_', 'hs_', 'en_', 'sr_', 'atk_', 'st_', 'cfg_')) +
            tuple('row_heiho_' + r for r in ('walk', 'run', 'jump')) + tuple(ATTACKS)}
        A, B = code(dd)
        labels = dict(A.labels)
        labels.update(B.labels)
        A.labels.update(B.labels)
        B.labels.update(labels)
        ea, eb = A.pc, B.pc
        assert ea <= LIMIT and eb <= LIMIT_B, 'walker code too big (0x%X, 0x%X)' % (ea, eb)
        d.build(labels, D)
        d.place([((ea + 0xF) & ~0xF, LIMIT), ((eb + 0xF) & ~0xF, LIMIT_B), (CAVE_C, LIMIT_C)])
        if d.addr == D:
            break
        D = dict(d.addr)
    d.build(labels, D)
    d.place([((ea + 0xF) & ~0xF, LIMIT), ((eb + 0xF) & ~0xF, LIMIT_B), (CAVE_C, LIMIT_C)])
    assert d.addr == D
    return A, B, d


def read_vt(img):
    return [img.u32(BI_VT + 4 * i) for i in range((0xC + 8 * 74) // 4)]


def patches(img):
    A, B, d = assemble(read_vt(img))
    out = {}
    for lo_, hi_ in REGIONS:
        for addr in range(lo_, hi_, 4):
            out[addr] = 0
    for a in (A, B):
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
                       (SITE_DEATH, WORD_DEATH)):
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
