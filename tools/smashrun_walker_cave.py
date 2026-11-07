#!/usr/bin/env python3
"""Smash Run step 2b: a generic "walker" behaviour (AI) for Smash Run enemies the Wii U has no behaviour for
(docs/smash-run-port.md, "Step 2b"). Prints rpx_patch.py args, or patches an RPX (after smashrun_menu.py's,
smashrun_field_cave.py's and smashrun_enemy_cave.py's patches; IN.rpx is read for BehaviorImpl's vtable):

  python3 tools/smashrun_walker_cave.py IN.rpx            the args
  python3 tools/smashrun_walker_cave.py IN.rpx OUT.rpx    IN with them (checks the hook words first)

The behaviour is a BehaviorImpl (the Wii U's own enemy framework, the 3DS one: damage, knock-back, down, capture,
death stay its own) with its own vtable and state table, written as the 3DS walkers' code does (Kuribo, Waddle Dee,
Shy Guy, Waddle Doo, Churine, read in enemy_fs.cro):
  1 FALL     kinetic 8, attach ground off, the kind's Fall loop; on the ground -> LANDING (WALK if none)
  2 LANDING  kinetic 0, ground on, Landing; at its end -> WALK
  3 WALK     the kind's walk kinetic (Kuribo 0xA, the others 1), ground on, its walk loop (Kuribo at 0.6);
             every frame move(input) = (lr, 0) (Behavior +0x10, the AI stick the kinetic module reads); off the
             ground -> FALL; every TARGET_INTERVAL frames get_nearest_target 0x026A7008 +
             check_turn_to_target 0x026A6984 (TURN_DIST) -> TURN; check_wall 0x026A68E4 -> TURN;
             check_cliff_lr 0x026A6D88 (posture lr) -> TURN
  4 TURN     kinetic 0, ground on, the kind's Turn (Kuribo: RunTurnL); at its end reverse_lr(1, 1) (slot 50)
             -> WALK (the 3DS Turn states flip after the animation)
  6 DEAD     (slot 67, the framework's death state) the kind's Damage pose at rate 0, bullet() 0x02DB5158 (the
             defeated enemy flies off); update = zima's 0x026D7A94 (kinetic flag 8 -> state 7)
  7 REMOVE   zima's 0x026D7B58 (EnemyManager remove_enemy_by_id) / 0x026D7B6C
Unknown ids (and 0, 5) go to FALL. Slots 64 / 65 / 66 / 67 (the states the framework returns to after damage on the
ground / in the air / by default, and the death state) are zima's 3 / 1 / 1 / 6.

- vtable VT: a copy of BehaviorImpl's 0x1008AEBC (GHS: {delta, fn}, slot k's fn at +0xC + 8k) plus slots 74 / 75;
  overrides: 12 zima's 0x026D6E18 (the gl entry's capture motion, generic), 38 w_noflip (0: no motion flip, fix v3
  below; --keep-flip: zima's 0x026D7C98, 1), 40 initialize (the kind's kinetic energy parameters, below), 41 start
  (set_rhombus 0x026A65BC, +0x10 = posture lr, face the nearest target, FALL), 45 set_attack_data (below),
  64-67, 72 / 73 change_state(id) / the interrupt one (the state table entry {enter, update, exit} PMFs to
  0x026A3A44 / 0x026A3AD4, BehaviorImpl's change_state_base / change_state_interrupt_base; 74 / 75 the same).
  Dtor (slot 0, delete only), update (3, the PMF at +0xE8 = common_state_func), damage / capture / death slots:
  BehaviorImpl's.
- create(acc, K, variation): operator new 0x03374578(OBJ_SIZE), Behavior ctor 0x02DB2DF0, then BehaviorImpl's
  inline init as zima's create 0x026D6680 (+0xE4..: 0, +0xE8 = common_state_func 0x102FDBCC, +0x120 = 1,
  +0x15C = -1), vptr VT, +0x168 = the kind's CFG, set_motion_label 0x02DB5B08 (+0xA8 = the kind's script hashsets
  or 0) and set_damage_motion_label 0x02DB5AD8 (the 3DS create's nine indices).
- set_attack_data(state) (slot 45; BehaviorImpl's reads [param slot]+0x30/+0x34, the aliased twin's list): clear_all
  0x02C08324 on the attack module (acc+0x30C8), and in WALK / TURN the kind's contact attack (a 3DS
  InnerEnemyAttackParam, 42 words): create_attack_data 0x02DB572C(this, entry), +0x84 / +0x88 = entry +4 / +8,
  AttackModule set_attack 0x02C086A8(module, id, part, this+0x1C). Kuribo and Shy Guy use their own bump attack
  (Kuribo's charge, damage 1, angle 100, fixed 80; Shy Guy's damage 1, angle 50, fixed 60); Waddle Dee, Waddle
  Doo and Churine have only their "bullet" attack on the 3DS (no contact damage while walking), so they get
  Shy Guy's bump (node 0).
- initialize (slot 40): the kind's kinetic energy parameters, as its 3DS initialize writes them (run in Unicorn on
  enemy_fs.cro with its fs vl, variation 0) at [[[acc+0x3130]+8]+0]+4 (+8 .. +0x44, the same offsets on the
  Wii U: mczakostalfos's writes match the 3DS stalfos's), then for Kuribo and Shy Guy the kinetic module's
  vt+0xFC(0x20000004) as theirs (3DS vt+0x7C).

Hooks (2a's three stay as they are):
- F2, the factory 0x02DB94CC after 2a's hook: 0x02DB951C `cmplwi r12, 0x10` -> for the walker kinds
  module+8 = create(module+4, K, variation) then the factory's epilogue 0x02DB96E0; else the instruction and
  0x02DB9520 (2a's kinds and the factory's own never reach it: 2a branches out before, 0x50-0x60 pass through).
- T2, battle load 0x02D9A46C `cmpwi r0, 1` (after 2a's table hook): on a Smash Run stage motion data set table
  0x10352610[K] = K's set (the article table stays the empty default: no weapons).
- S2, the battle's param load 0x02D9A618 `lwz r0, 0x5EC(r28)` (after 2a's slot hook): on a Smash Run stage
  param slot[K] = slot[0x5A] (mczakozima: the activation and accessor set-up read [slot]+0x70 / +0x5C unchecked;
  the walker reads no tuning from it, BehaviorImpl only its generic parts).

Motion data sets (the game's layout: +0 entries*, +4 count, +8..+0x14 0, the entries {hash, flags} from +0x18;
the mczako sets have nothing else, set_motion_label carries the script hashsets): K's 3DS motion_data_set_<name>
(enemy_fs.cro) in its own order, hash zlib.crc32(stem, 0xFFFFFFFF), flags the 3DS word >> 16 (1, 5, 0x40 as the
twins' Wii U sets). Script hashsets (Kuribo, Shy Guy, Churine have them on the 3DS): crc32(lower(name) + ".init"),
crc32(lower(name)), crc32(lower(name) + ".exit") per index (the 3DS tables are exactly these).

Fix v3 (every Smash Run kind < 0x50, 2a's twins included; in-game reports: enemies facing away / askew, defeated
enemies vanishing without an effect):
- slot 38 (does set_lr / reverse_lr / initialize_after flip the motion with lr): on the 3DS it returns 1 for the
  kinds whose model has a model.flp (mirror table: 33 of the 34 kinds with one return 1, 41 of the 43 without
  return 0); the converted models have none, so the Wii U mirrors their skeletons without it. The walker's slot 38 returns 0,
  and the twins' (vtable words 0x1008FFCC zima, 0x1008F1D4 plasmawisp, 0x1008EC68 darios, functions `li r3, 1`;
  stalfos's already returns 0) -> twin_flip: 1 for kinds >= 0x50 (the Fortress minions, unchanged), 0 below; their
  ADDR32 relocations moved to RELOC_DUMMY 0x037EE73C (kind_expand.py's dead word). `--keep-flip` builds without it.
- initialize_after 0x02DB4AC8 (every behaviour, after start), 0x02DB4B20 `lwz r10, 0(r31)` -> for kinds < 0x50
  set_lr(posture lr, 1, 1) (slot 49): the model's rotation (posture +0x64 = lr * 90) from the first frame. Only
  set_lr / reverse_lr write it, and the behaviours' starts only reverse when the target is behind.
- notify_on_remove 0x02DB40E4 (slot 27, called by the Enemy's removal 0x02D8BE78 with its type), `mflr r0` -> for
  kinds < 0x50 type 0 (the behaviour's remove state: remove_enemy_by_id 0x02D9C0E0) becomes 3, the defeat path
  0x02DB3AB0: effect 0x08000033 scaled by the common param +0x5C x the kind's gl entry +0x20 (its size), sound
  0x124, the dead item check (0x02DB3944, as notify_on_damage does at 0 HP). Type 0 only reaches 0x02DB3574, which
  in category sm shows the Fortress minions' vanish effect (kinds 0x57-0x5A with +0x9C set) and nothing else; no
  Wii U caller passes 3 / 4 (the manager passes 1 and 5).

Space: 0x04B86800-0x04B88000 (the rest of kind_expand.py's old space that smashrun_enemy_cave.py clears; nothing
refers to it).
"""
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm, ha, lo  # noqa: E402
import smashrun_field_cave as F  # noqa: E402

CAVE = 0x04B86800
LIMIT = 0x04B88000

# the framework (docs/smash-run-port.md, Step 2b)
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
CHECK_CLIFF_LR = 0x026A6D88          # check_cliff_lr(f1 lr)
CHG_BASE = 0x026A3A44                # change_state_base(id, &update, &enter, &exit) (deferred)
CHG_INT = 0x026A3AD4                 # change_state_interrupt_base (now)
COMMON_PMF = 0x102FDBCC              # BehaviorImpl::common_state_func
BI_VT = 0x1008AEBC
ZIMA_CAPTURE_MOTION = 0x026D6E18     # slot 12
ZIMA_ONE = 0x026D7C98                # li r3, 1
ZIMA_RET = {64: 0x026D7CA0, 65: 0x026D7CA8, 66: 0x026D7CB0, 67: 0x026D7CB8}   # 3, 1, 1, 6
ZIMA_DEAD_UPDATE = 0x026D7A94
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
# slot 38 of the twins' vtables (mczakozima 0x1008FE90, mczakoplasmawisp 0x1008F098, mczakodarios 0x1008EB2C;
# mczakostalfos's already returns 0): {vtable word, its function (li r3, 1)}; the words carry an ADDR32 relocation,
# moved to RELOC_DUMMY (kind_expand.py's dead word) so the loader keeps the patched value
TWIN_FLIP = ((0x1008FFCC, 0x026D7C98), (0x1008F1D4, 0x026D19F4), (0x1008EC68, 0x026CF200))
RELOC_DUMMY = 0x037EE73C
SET_LR_SLOT = 49
KEEP_FLIP = False    # True: the variant that keeps the motion flip (only the rotation and death fixes)

ST_FALL, ST_LANDING, ST_WALK, ST_TURN, ST_DEAD, ST_REMOVE = 1, 2, 3, 4, 6, 7
NSTATES = 8
OBJ_SIZE = 0x170                     # BehaviorImpl 0x168, +0x168 CFG*, +0x16C frame counter
TARGET_INTERVAL = 30                 # frames between target checks
TURN_DIST = 20.0                     # check_turn_to_target: turn when the target is this far behind

# CFG (per kind)
C_KIND, C_WALK, C_TURN, C_FALL, C_LAND, C_DEAD, C_WKIN, C_RATE = 0, 4, 8, 0xC, 0x10, 0x14, 0x18, 0x1C
C_HASH, C_ATK, C_EN, C_ENN, C_KICK, C_SET, C_DMG = 0x20, 0x24, 0x28, 0x2C, 0x30, 0x34, 0x38
CFG_SIZE = 0x60

# InnerEnemyAttackParam (fs vl, 42 values; create_attack_data: +0xC node, +0x10 power, +0x14 angle, +0x18 kbg,
# +0x1C fkb, +0x20 bkb, +0x24 size, +0x28.. offset)
KURIBO_BUMP = (5, 0, 0, 4, 1, 100, 100, 80, 0, 3, -1.0, 0.0, 0.0, 0, 0.0, 1.0, 1.0, 0, 0, 1, 0, 2, 3, 1, 2, 1, 0,
               9, 0, 1, 0, 0, 60, 0, 0, 1, 0, 0, 0, 0, 0, 0)
HEIHO_BUMP = (9, 0, 0, 0, 1, 50, 100, 60, 0, 4, 0.0, 8.0, 1.0, 0, 0.0, 1.0, 3.0, 0, 0, 1, 0, 1, 3, 1, 0, 1, 0,
              9, 0, 1, 0, 0, 4, 0, 0, 1, 0, 0, 0, 0, 0, 0)
DAMAGE_LABELS = ('DamageStart', 'DamageFly', 'DamageFall', 'DownBound', 'DownBound', 'DownLoop', 'DownBoundEnd',
                 'DownWait')
# kinds (index in the name table 0x1041A22C). motions: the 3DS motion_data_set_<name> order (name, Wii U flags).
# energy: {offset: value} of the kind's 3DS initialize; kick: it calls the kinetic module's vt (0x20000004).
WALKERS = (
    dict(name='kuribo', kind=0x01,
         motions=(('Collapses', 1), ('Damage', 1), ('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1),
                  ('DownBound', 1), ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1), ('Fall', 1),
                  ('Landing', 1), ('RunBrakeL', 1), ('RunHoldL', 1), ('RunL', 5), ('RunTurnL', 1), ('WalkL', 5)),
         walk='WalkL', turn='RunTurnL', fall='Fall', landing='Landing', dead='Damage', last='Fall',
         walk_kinetic=0xA, walk_rate=0.6, hashset=True, attack=KURIBO_BUMP, kick=True,
         energy={8: 2.0, 0xC: 1.5, 0x10: 0.02, 0x14: 0.001, 0x18: 0.01, 0x20: -0.4, 0x24: 1.6, 0x2C: 5.0,
                 0x40: 1.0, 0x44: 0.8}),
    dict(name='heiho', kind=0x0B,
         motions=(('Damage', 1), ('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1),
                  ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1), ('Fall', 1), ('Landing', 1), ('Run', 1),
                  ('RunBrake', 5), ('RunHold', 1), ('RunTurn', 1), ('Turn', 1), ('Wait', 1), ('Walk', 1)),
         walk='Walk', turn='Turn', fall='Fall', landing='Landing', dead='DamageStart', last='Fall',
         walk_kinetic=1, walk_rate=1.0, hashset=True, attack=HEIHO_BUMP, kick=True,
         energy={8: 0.3, 0xC: 10.0, 0x10: 0.3, 0x14: 0.0, 0x18: 0.0, 0x20: 0.5, 0x24: 2.5, 0x28: 0.5, 0x2C: 2.5,
                 0x40: 1.0}),
    dict(name='waddledee', kind=0x13,
         motions=(('Damage', 1), ('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1),
                  ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1), ('Fall', 1), ('Jump', 0x40),
                  ('Landing', 1), ('ParasolFall', 1), ('Turn', 1), ('Walk', 1)),
         walk='Walk', turn='Turn', fall='Fall', landing='Landing', dead='Damage', last='Jump',
         walk_kinetic=1, walk_rate=1.0, hashset=False, attack=HEIHO_BUMP, kick=False,
         energy={8: 0.2, 0x10: 0.2, 0x18: 0.0005, 0x20: 0.3, 0x24: 2.5, 0x28: 0.3, 0x2C: 2.5, 0x44: 1.0}),
    dict(name='waddledoo', kind=0x19,
         motions=(('BeamShot', 1), ('BeamShotHold', 1), ('Damage', 1), ('DamageFall', 1), ('DamageFly', 1),
                  ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1),
                  ('Fall', 1), ('Jump', 1), ('Landing', 1), ('Turn', 1), ('Walk', 1)),
         walk='Walk', turn='Turn', fall='Fall', landing='Landing', dead='Damage', last='Jump',
         walk_kinetic=1, walk_rate=1.0, hashset=False, attack=HEIHO_BUMP, kick=False,
         energy={8: 0.3, 0x10: 0.3, 0x20: 0.5, 0x24: 2.4, 0x28: 0.5, 0x2C: 2.4}),
    dict(name='churine', kind=0x1F,
         motions=(('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1),
                  ('DownLoop', 1), ('DownWait', 1), ('Jump', 1), ('Landing', 1), ('SleepPowder', 1), ('Turn', 1),
                  ('Walk', 1), ('Fall', 1)),
         walk='Walk', turn='Turn', fall='Fall', landing='Landing', dead='DamageStart', last='Fall',
         walk_kinetic=1, walk_rate=1.0, hashset=True, attack=HEIHO_BUMP, kick=False,
         energy={8: 0.7, 0x10: 0.1, 0x14: 0.05, 0x20: 0.2, 0x24: 2.5, 0x28: 0.2, 0x2C: 2.5}),
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


def fword(v):
    return struct.unpack('>I', struct.pack('>f', v))[0]


def sx(v):
    """signed 16-bit low half (for `addi` / `lwz` after `lis ha`)"""
    v = lo(v)
    return v - 0x10000 if v & 0x8000 else v


def branch(src, dst, link=False):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000
    return 0x48000000 | (off & 0x03FFFFFC) | (1 if link else 0)


def branch_target(src, word):
    off = word & 0x03FFFFFC
    return src + (off - 0x4000000 if off & 0x2000000 else off)


# ---------------------------------------------------------------- data
class Data:
    """the cave's data, laid out from BASE; .addr[label]"""

    def __init__(self, base, vt_words):
        self.base, self.words, self.addr = base, [], {}
        self.vt_words = vt_words

    def at(self, label):
        self.addr[label] = self.base + 4 * len(self.words)

    def align(self, n=0x10):
        while (self.base + 4 * len(self.words)) % n:
            self.words.append(0)

    def build(self, code_labels):
        """code_labels: the code's function addresses (pass 2); 0 in pass 1"""
        cl = lambda k: code_labels.get(k, 0)  # noqa: E731
        self.words, self.addr = [], {}
        self.at('fzero')
        self.words += [fword(0.0), fword(1.0), fword(TURN_DIST), 0]
        self.addr['fone'] = self.addr['fzero'] + 4
        self.addr['fturn'] = self.addr['fzero'] + 8
        # vtable
        self.align()
        self.at('vt')
        vt = list(self.vt_words) + [0, 0, 0, 0]          # 74 slots + 74 / 75
        over = {12: ZIMA_CAPTURE_MOTION, 38: ZIMA_ONE if KEEP_FLIP else cl('w_noflip'), 40: cl('w_init'),
                41: cl('w_start'), 45: cl('w_atk'),
                72: cl('w_chg'), 73: cl('w_chgi'), 74: cl('w_chg'), 75: cl('w_chgi')}
        over.update(ZIMA_RET)
        for k, fn in over.items():
            vt[(0xC + 8 * k) // 4] = fn
            vt[(0x8 + 8 * k) // 4] = 0
        self.words += vt
        # state table {enter, update, exit} PMFs {0x0000FFFF, fn}
        self.align()
        self.at('states')
        st = {ST_FALL: ('fall_enter', 'fall_update'), ST_LANDING: ('land_enter', 'land_update'),
              ST_WALK: ('walk_enter', 'walk_update'), ST_TURN: ('turn_enter', 'turn_update'),
              ST_DEAD: ('dead_enter', ZIMA_DEAD_UPDATE), ST_REMOVE: (ZIMA_REMOVE_ENTER, ZIMA_REMOVE_UPDATE)}
        for i in range(NSTATES):
            if i in st:
                en, up = (x if isinstance(x, int) else cl(x) for x in st[i])
                self.words += [0xFFFF, en, 0xFFFF, up, 0, 0]
            else:
                self.words += [0] * 6
        # kind table {kind, cfg*}, -1
        self.at('ktab')
        ktab_at = len(self.words)
        self.words += [0] * (2 * len(WALKERS) + 1)
        # attacks
        self.align()
        atk = {}
        for name, entry in (('kuribo_bump', KURIBO_BUMP), ('heiho_bump', HEIHO_BUMP)):
            self.at(name)
            atk[entry] = self.addr[name]
            for v in entry:
                self.words.append(fword(v) if isinstance(v, float) else v & 0xFFFFFFFF)
        # per kind
        for w in WALKERS:
            n = w['name']
            self.align()
            self.at('set_' + n)
            ms = w['motions']
            self.words += [self.addr['set_' + n] + 0x18, len(ms), 0, 0, 0, 0]
            for sfx, flags in ms:
                self.words += [motion_hash(stem(n, sfx)), flags]
            if w['hashset']:
                self.at('hs_' + n)
                for sfx, _f in ms:
                    s = sfx.lower()
                    self.words += [zlib.crc32((s + '.init').encode()), zlib.crc32(s.encode()),
                                   zlib.crc32((s + '.exit').encode())]
            self.at('en_' + n)
            for off, v in sorted(w['energy'].items()):
                self.words += [off, fword(v)]
            self.at('cfg_' + n)
            cfg = [w['kind'], index(w, w['walk']), index(w, w['turn']), index(w, w['fall']),
                   index(w, w['landing']), index(w, w['dead']), w['walk_kinetic'], fword(w['walk_rate']),
                   self.addr.get('hs_' + n, 0), atk[w['attack']], self.addr['en_' + n], len(w['energy']),
                   1 if w['kick'] else 0, self.addr['set_' + n]] + damage_labels(w)
            cfg = [v & 0xFFFFFFFF for v in cfg]
            self.words += cfg + [0] * (CFG_SIZE // 4 - len(cfg))
        for i, w in enumerate(WALKERS):
            self.words[ktab_at + 2 * i:ktab_at + 2 * i + 2] = [w['kind'], self.addr['cfg_' + w['name']]]
        self.words[ktab_at + 2 * len(WALKERS)] = 0xFFFFFFFF
        return self


# ---------------------------------------------------------------- code
def assemble(vt_words, data_base=None):
    """(Asm, code words, Data); two passes (the code's size does not depend on DATA's address)"""
    final = data_base is None
    if final:
        a, words, _d = assemble(vt_words, CAVE + 0x1000)
        data_base = (CAVE + 4 * len(words) + 0xF) & ~0xF
    d = Data(data_base, vt_words).build({})
    a = Asm(CAVE)
    D = d.addr

    def far(t):
        a.asm("lis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctrl" % (t >> 16, t & 0xFFFF))

    def near(t):
        a.asm("bl 0x%08X" % t)

    def lfs(fr, label):
        a.asm("lis r12, 0x%04X\nlfs %s, %d(r12)" % (ha(D[label]), fr, sx(D[label])))

    def la(r, label):
        a.asm("lis %s, 0x%04X\naddi %s, %s, %d" % (r, ha(D[label]), r, r, sx(D[label])))

    def vcall(off):
        a.asm("lwz r12, 0xE0(r3)\nlwz r12, 0x%X(r12)\nmtctr r12\nbctrl" % off)

    def chg(state):          # this->change_state(state) (slot 72)
        a.asm("mr r3, r31\nli r4, %d" % state)
        vcall(0xC + 8 * 72)

    def module(r, off):
        a.asm("lwz %s, 0(r31)\nlwz %s, 0x%X(%s)" % (r, r, off, r))

    def kinetic(n=None):
        module('r3', 0x30E8)
        a.asm("li r4, %d" % n if n is not None else "lwz r4, 0x%X(r30)" % C_WKIN)
        near(CHANGE_KINETIC)

    def attach(on):
        module('r3', 0x30DC)
        a.asm("li r4, %d" % on)
        near(SET_ATTACH_GROUND)

    def motion(field, rate, loop):   # change_motion_state(this, cfg.field, 0, rate, loop, 0)
        a.asm("mr r3, r31\nlwz r4, 0x%X(r30)" % field)
        lfs('f1', 'fzero')
        if rate == 'cfg':
            a.asm("lfs f2, 0x%X(r30)" % C_RATE)
        else:
            lfs('f2', rate)
        a.asm("fmr f3, f1\nli r5, %d" % loop)
        near(CHANGE_MOTION)

    def on_ground():
        module('r3', 0x30DC)
        a.asm("li r4, 8")
        near(IS_TOUCH)
        a.asm("cmpwi r3, 0")

    def motion_end():
        module('r3', 0x30F0)
        near(MOTION_IS_END)
        a.asm("cmpwi r3, 0")

    def enter(label):        # r31 this, r30 cfg, r29 the AI input (updates)
        a.asm("""
    %s:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stmw r29, 0x14(r1)
        mr r31, r3
        lwz r30, 0x168(r3)
        mr r29, r4
        """ % label)

    def leave(label):
        a.asm("""
    %s:
        lmw r29, 0x14(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
        """ % label)

    # ---- F2: the factory (r31 kind, r30 module, r29 variation, r12 = kind - 0x50)
    a.asm("cave_f:")
    la('r11', 'ktab')
    a.asm("""
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
    a.asm("""
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
    la('r11', 'ktab')
    a.asm("""
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
    la('r11', 'vt')
    a.asm("""
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
    """ % (ha(COMMON_PMF), sx(COMMON_PMF), sx(COMMON_PMF + 4), C_HASH, SET_MOTION_LABEL))
    for i, r in enumerate(('r4', 'r5', 'r6', 'r7', 'r8', 'r9', 'r10')):
        a.asm("lwz %s, 0x%X(r31)" % (r, C_DMG + 4 * i))
    a.asm("""
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
    """ % (C_DMG + 0x1C, C_DMG + 0x20, SET_DAMAGE_LABEL))
    # ---- slot 40 initialize: the kinetic energy parameters
    a.asm("""
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
    """ % (C_EN, C_ENN, C_KICK))
    # ---- slot 41 start
    enter('w_start')
    far(SET_RHOMBUS)
    a.asm("""
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x60(r12)
        stfs f0, 0x10(r31)
    """)
    lfs('f1', 'fzero')
    a.asm("""
        stfs f1, 0x14(r31)
        stfs f1, 0x18(r31)
        li r0, 0
        stw r0, 0x16C(r31)
        mr r3, r31
    """)
    far(NEAREST)
    a.asm("mr r4, r3\nmr r3, r31")
    lfs('f1', 'fzero')
    far(CHECK_TURN)
    a.asm("""
        cmpwi r3, 0
        beq s_state
        mr r3, r31
        li r4, 1
        li r5, 1
    """)
    vcall(0xC + 8 * 50)
    a.asm("s_state:")
    chg(ST_FALL)
    leave('s_out')
    # ---- slots 72 / 73 change_state(id)
    for label, target in (('w_chg', CHG_BASE), ('w_chgi', CHG_INT)):
        a.asm("""
    %s:
        cmplwi r4, %d
        blt %s_in
        li r4, %d
    %s_in:
        mulli r11, r4, 0x18
        """ % (label, NSTATES, label, ST_FALL, label))
        la('r12', 'states')
        a.asm("""
        add r6, r12, r11
        lwz r0, 0xC(r6)
        cmpwi r0, 0
        bne %s_ok
        li r4, %d
        addi r6, r12, %d
    %s_ok:
        addi r5, r6, 8
        addi r7, r6, 0x10
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        mtctr r12
        bctr
        """ % (label, ST_FALL, ST_FALL * 0x18, label, target >> 16, target & 0xFFFF))
    # ---- slot 45 set_attack_data(state): the contact attack in WALK / TURN
    enter('w_atk')
    a.asm("mr r29, r4")
    module('r3', 0x30C8)
    near(ATK_CLEAR)
    a.asm("""
        cmpwi r29, %d
        beq a_set
        cmpwi r29, %d
        bne a_out
    a_set:
        lwz r29, 0x%X(r30)
        cmpwi r29, 0
        beq a_out
        mr r3, r31
        mr r4, r29
        bl 0x%08X
        lwz r4, 4(r29)
        lwz r5, 8(r29)
        stw r4, 0x84(r31)
        stw r5, 0x88(r31)
    """ % (ST_WALK, ST_TURN, C_ATK, ATK_CREATE))
    module('r3', 0x30C8)
    a.asm("addi r6, r31, 0x1C")
    near(ATK_SET)
    leave('a_out')
    # ---- states
    enter('fall_enter')
    kinetic(8)
    attach(0)
    motion(C_FALL, 'fone', 1)
    leave('fe_out')
    enter('fall_update')
    on_ground()
    a.asm("beq fu_out\nlwz r0, 0x%X(r30)\ncmpwi r0, 0\nblt fu_walk" % C_LAND)
    chg(ST_LANDING)
    a.asm("b fu_out\nfu_walk:")
    chg(ST_WALK)
    leave('fu_out')
    enter('land_enter')
    kinetic(0)
    attach(1)
    motion(C_LAND, 'fone', 0)
    leave('le_out')
    enter('land_update')
    motion_end()
    a.asm("beq lu_out")
    chg(ST_WALK)
    leave('lu_out')
    enter('walk_enter')
    kinetic()
    attach(1)
    motion(C_WALK, 'cfg', 1)
    a.asm("li r0, 0\nstw r0, 0x16C(r31)")
    leave('we_out')
    enter('walk_update')
    lfs('f1', 'fzero')
    a.asm("""
        lfs f0, 0x10(r31)
        stfs f0, 0(r29)
        stfs f1, 4(r29)
    """)
    on_ground()
    a.asm("bne wu_ground")
    chg(ST_FALL)
    a.asm("""
        b wu_out
    wu_ground:
        lwz r11, 0x16C(r31)
        addi r11, r11, 1
        stw r11, 0x16C(r31)
        cmpwi r11, %d
        blt wu_wall
        li r11, 0
        stw r11, 0x16C(r31)
        mr r3, r31
    """ % TARGET_INTERVAL)
    far(NEAREST)
    a.asm("cmpwi r3, 0\nblt wu_wall\nmr r4, r3\nmr r3, r31")
    lfs('f1', 'fturn')
    far(CHECK_TURN)
    a.asm("cmpwi r3, 0\nbne wu_turn\nwu_wall:\nmr r3, r31")
    far(CHECK_WALL)
    a.asm("""
        cmpwi r3, 0
        bne wu_turn
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x60(r12)
        mr r3, r31
    """)
    far(CHECK_CLIFF_LR)
    a.asm("cmpwi r3, 0\nbeq wu_out\nwu_turn:")
    chg(ST_TURN)
    leave('wu_out')
    enter('turn_enter')
    kinetic(0)
    attach(1)
    a.asm("lwz r0, 0x%X(r30)\ncmpwi r0, 0\nblt te_out" % C_TURN)
    motion(C_TURN, 'fone', 0)
    leave('te_out')
    enter('turn_update')
    lfs('f1', 'fzero')
    a.asm("stfs f1, 0(r29)\nstfs f1, 4(r29)")
    on_ground()
    a.asm("bne tu_ground")
    chg(ST_FALL)
    a.asm("b tu_out\ntu_ground:\nlwz r0, 0x%X(r30)\ncmpwi r0, 0\nblt tu_done" % C_TURN)
    motion_end()
    a.asm("beq tu_out\ntu_done:\nmr r3, r31\nli r4, 1\nli r5, 1")
    vcall(0xC + 8 * 50)
    chg(ST_WALK)
    leave('tu_out')
    enter('dead_enter')
    motion(C_DEAD, 'fzero', 0)
    a.asm("mr r3, r31")
    near(BULLET)
    leave('de_out')
    # ---- fix v3 -----------------------------------------------------------------------------------------------
    # slot 38 (flip the motion with lr): the 3DS returns 1 exactly for the kinds with a model.flp (mirror table),
    # which the converted models lack; without it the flipped skeleton is wrong (the enemy faces away / askew).
    a.asm("""
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
    """)
    # initialize_after (every behaviour, after start): for the Smash Run kinds set_lr(posture lr, 1, 1), so the
    # model's rotation (posture +0x64 = lr * 90) is set from the first frame, not only after a turn
    a.asm("""
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
    """)
    vcall(0xC + 8 * SET_LR_SLOT)
    a.asm("""
    rot_done:
        lwz r10, 0(r31)
        b 0x%08X
    """ % (SITE_ROT + 4))
    # notify_on_remove(type): a Smash Run kind removed by its behaviour (type 0: its remove state, after its death
    # flight) gets type 3, the defeat path 0x02DB3AB0 (effect 0x08000033 scaled by the gl entry's +0x20, sound
    # 0x124); type 0 only shows the Fortress minions' vanish effect (0x02DB3574: kinds 0x57-0x5A, +0x9C set)
    a.asm("""
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
    """ % (SITE_DEATH + 4))
    # ---- T2: the motion data set table (r0 = category, r31 = mgr; r9-r12 free)
    a.asm("cave_t:")
    F.sr_check(a)
    a.asm("bgt t_done")
    for w in WALKERS:
        s, t = D['set_' + w['name']], MOTION_SETS + 4 * w['kind']
        a.asm("lis r11, 0x%04X\naddi r11, r11, %d\nlis r12, 0x%04X\nstw r11, %d(r12)" % (ha(s), sx(s), ha(t), sx(t)))
    a.asm("""
    t_done:
        cmpwi r0, 1
        b 0x%08X
    """ % (SITE_T + 4))
    # ---- S2: param slots (r28 = mgr, r3 the load's result: kept)
    a.asm("cave_s:")
    F.sr_check(a)
    a.asm("""
        bgt s2_done
        lis r12, 0x%04X
        lwz r12, %d(r12)
        cmpwi r12, 0
        beq s2_done
        lwz r11, 0x%X(r12)
    """ % (ha(PARAM_MGR), sx(PARAM_MGR), SLOTS + 4 * SLOT_DONOR))
    for k in KINDS:
        a.asm("stw r11, 0x%X(r12)" % (SLOTS + 4 * k))
    a.asm("""
    s2_done:
        lwz r0, 0x5EC(r28)
        b 0x%08X
    """ % (SITE_S + 4))
    words = a.words()
    assert CAVE + 4 * len(words) <= data_base, 'walker code overlaps its data'
    funcs = {k: a.addr(k) for k in ('w_init', 'w_start', 'w_atk', 'w_chg', 'w_chgi', 'w_noflip', 'fall_enter',
                                    'fall_update',
                                    'land_enter', 'land_update', 'walk_enter', 'walk_update', 'turn_enter',
                                    'turn_update', 'dead_enter')}
    d.build(funcs)
    assert not final or d.base + 4 * len(d.words) <= LIMIT, 'walker cave too big (0x%X)' % (d.base + 4 * len(d.words))
    return a, words, d


def read_vt(img):
    return [img.u32(BI_VT + 4 * i) for i in range((0xC + 8 * 74) // 4)]


def patches(img):
    a, words, d = assemble(read_vt(img))
    out = {}
    for addr in range(CAVE, LIMIT, 4):
        out[addr] = 0
    for i, w in enumerate(words):
        out[CAVE + 4 * i] = w
    for i, w in enumerate(d.words):
        out[d.base + 4 * i] = w
    out[SITE_F] = branch(SITE_F, a.addr('cave_f'))
    out[SITE_T] = branch(SITE_T, a.addr('cave_t'))
    out[SITE_S] = branch(SITE_S, a.addr('cave_s'))
    out[SITE_ROT] = branch(SITE_ROT, a.addr('cave_rot'))
    out[SITE_DEATH] = branch(SITE_DEATH, a.addr('cave_death'))
    for word, fn in TWIN_FLIP:
        out[word] = fn if KEEP_FLIP else a.addr('twin_flip')
    return out, a, d


def args(img):
    out, _a, _d = patches(img)
    res = ['grow:0x%08X' % LIMIT] + ['0x%08X=0x%08X' % (k, v) for k, v in sorted(out.items())]
    if not KEEP_FLIP:
        res += ['reloc:0x%08X-0x%08X=0x%08X' % (w, w + 4, RELOC_DUMMY) for w, _fn in TWIN_FLIP]
    return res


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
        assert got == want or (got >> 26 == 18 and CAVE <= branch_target(site, got) < LIMIT), \
            '0x%08X holds 0x%08X, expected 0x%08X' % (site, got, want)
    if img.u32(E.SITE_F) >> 26 != 18:
        print('warning: tools/smashrun_enemy_cave.py is not applied (it clears this space and aliases its kinds)',
              file=sys.stderr)
    sys.argv = ['rpx_patch.py', sys.argv[1], sys.argv[2]] + args(img)
    rpx_patch.main()


if __name__ == '__main__':
    main()
