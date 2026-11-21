#!/usr/bin/env python3
"""Supamario's Ultra Instinct (fighters/supamario/README.md "Ultra Instinct v1"): the native part. Supamario (kind
0x41, extra_kinds.json "supamario") runs Mario's native code (specializer vtable 0x10139E60), which has no counter. For
kind 0x41 ONLY (the fighter's kind [fighter + 4]; Mario, kind 3, and every other kind run the game's words as before)
this adds:

v5 (exe_v46z_ui3): every "status 0x157" below is now status 0x155 with TIMER_4 (V_MODE) above MODE_FORM_ON (the
transformation / its counter: his MSC writes 7 every frame of it), and the dodge's 0x158 is 0x155 with TIMER_4 5; 0x155
without the transformation's mode keeps Secret Sensation's rules. Mario's F.L.U.D.D. statuses 0x157 / 0x158 are nothing
special here any more. The diag build adds S4U4 (the 8 frames after a dodge signal: his status, TIMER_1 / 2 / 4) and
S4UM's status.

ui4 (exe_v46z_ui4; README "Ultra Instinct v5", from the v4 diag log): slot 43 is event 0x12, the shield DAMAGE that
follows a shield hit, never a body hit (3. below is v1-v4's reading, kept for the 0x155 cases): the autododge is now a
hit on the counter shape his MSC keeps on in Wait / Walk / WalkBrake / Squat .. SquatRv while transformed, in slot 42
(s42_dg: TIMER_1 / TIMER_2 by the hitting object's side), slot 43 returning 0 there; the fighters' hit-record search is
gone. Objects of category 4 (items: the Killer Eye 0x4001000x) count as an opponent's in slot 42 / the owner chain.
Mesh_Visibility's name walk (mesh_vis_cave in the base) takes unaligned names (WALK_FIX). The diag build adds S4UF and
the effect runtime's messages.

v7 (exe_v46z_ui6; README "Ultra Instinct v7"): 0x155's modes are 9 the transformation, 7 the sway (the autododge), 5
its counter, 3 Secret Sensation; slot 42 in 0x155 in the sway family (TIMER_4 in (MODE_SWAY_ON, MODE_FORM_ON]) is the
autododge's (another sway: XV2's chain), slot 43 there returns 0; EscapeN (his spot dodge) is one of the autododge's
statuses (the counter's "attacked" mark). The PROJECTILE FILTER (ui_pf, on the collision pair pass's per-entry check
0x02C0F7F0): his counter shape doesn't meet anything that isn't a fighter's own attack (except in Secret Sensation), so a
projectile / item goes on to his body (see PF_HOOK). The diag build adds S4UP.

1. SETUP: Mario's specializer slot 0 (0x02F1A6F0 `li r5, 1`, then `b 0x02F1A598` his setup) branches here first: for
   kind 0x41 the counter shape, ShieldModule ([acc + 0x72F4], kind 2) group 1, built as Marth's setup builds his
   (0x0200C858(M, &desc, 1), desc {&shape, 1, bytes 0, 0, 0, 1}) and switched off (0x0200BD8C(M, 0, 0, 1)); then the
   replaced `li r5, 1` and on to 0x02F1A598. The shape: a capsule round his whole body on joint 0, (0, 2.5, 0) to
   (0, 9.5, 0), radius 6.5 (front and back: an attack from either side meets it). His MSC switches it on only in the
   transformation status (0x157): ShieldModule(0, 2, 0, 1, 1) / (0, 2, 0, 0, 1).
2. SLOT42 (0x02F1B218 `blr`, the shield-hit event's call): for kind 0x41, a hit on group 1 (message +0x14 == 1) in
   status 0x157 (the transformation) or 0x155 (Secret Sensation, the transformed grounded down special: his MSC has
   the shape on only in its window; Fake Death / Sledgehammer never switch it on) before any. The two counters' rules
   differ (the user's): the transformation's is XV2's (1510_GKS_MGT_PLAYER.bcm: its counter children's
   PrimaryActivatorConditions CounterMelee, not CounterProjectile): a FIGHTER's own attack only (record category 0);
   Secret Sensation's: anything an opponent owns (0 fighter, 1 weapon, 2 item), never a stage gimmick (3); (status flag 0x21000010 off), counterable (the attacker AttackModule's hit data
   vt +0x194(id, part): +0x54 == 0): status float 0x01000006 = the hit's damage (message +0xC), 0x01000007 = the side
   (+1.0 the attacker to his right: the facing that faces it), 0x01000008 / 0x01000009 = X / Y of the fighter to
   answer: the attacker itself (record +0x1C category 0), or for a weapon / item (1 / 2) its current owner (the
   object's owner module [acc + 0x6C] +0x34, a fighter id (id >> 28 == 0)); flags 0x21000010 on, 0x21000011 on for a
   non-fighter attacker, 0x21000012 on when the fighter to answer was found (else the side from the attacker object's
   place, or Marth's 0x02C22684 when that is gone too). No hitstop, no attacker freeze (his MSC answers at once). A stage gimmick's hit (category 3:
   owned by no opponent, the user's) is not countered: nothing recorded. Grabs never reach the shape (a catch box
   isn't a hitbox: the shield-hit event is the attack collision's).
3. SLOT43 (0x02F1B21C `li r3, 1`, the damage event's call; 0 skips the damage, knockback and reaction):
   - status 0x157 (the transformation and its counter strike): 0, the message's handled bit (+8 |= 1): fully
     invincible (his MSC also makes him intangible: no grab, nothing reaches the body);
   - the AUTODODGE: transformed (TIMER_0 0x0F000320 > 1500: his MSC writes 2000 every frame once transformed), in
     Wait / Walk / WalkBrake (0x0-0x2) or Squat .. SquatRv (0x11-0x15), and a FIGHTER's attack: another fighter
     (the fighter table, live entries) whose AttackModule hit records ([AM + 0x14] + part x 0x174: the list at +0x124 /
     +0x128, node +0x18 the object hit) hold him, and that hit counterable (vt +0x194(node +0x27, part) +0x54 == 0):
     0 (no damage / knockback / hitstun), the handled bit, and TIMER_1 0x0F000321 (the attacker to his right) or
     TIMER_2 0x0F000322 (to his left) = 4.0 (the other 0) through his WorkModule's set_float (vt +0x4C, the MSC's
     path: the user variables' hooks), which his MSC turns into the dodge status (0x158). Weapons / items / stage
     gimmicks (no fighter's records hold him), grabs (no damage event) and uncounterable hits fall through: 1.
   - status 0x155 with 0x21000010 on (Secret Sensation answering): 0 and the handled bit; without it: 1;
   - anything else: 1 (Mario's stub).
The damage event's message has no attacker fields that are known (only +8, the handled byte, is read by the game's
handler and by Marth's / Sephiroth's slot 43), so the attacker is found from the attackers' side: their hit records,
which are written at the collision (the "don't hit twice" log) before the hit is dealt.

Space: 0x04BE8000-0x04BE9000 (past the outline shell's 0x04BE5000-0x04BE8000; `textregion:0x2BE9000 grow:0x04BE9000`).
Calls go through ctr (game functions only: no import is called). Each hooked word is asserted.

  python3 tools/rpx_patch.py exe_v46z_outline4.rpx exe_v46z_ui.rpx $(python3 tools/supamario_ui_cave.py --rpx exe_v46z_outline4.rpx)
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

CAVE = 0x04BE8000
LIMIT = 0x04BEA000                # v4: 0x04BE8000-0x04BEA000 (v1-v3: to 0x04BE9000)
TEXT_REGION = LIMIT - 0x02000000
SPEC = os.path.join(HERE, 'extra_kinds.json')
NAME = 'supamario'

# Mario's specializer (vtable 0x10139E60: slot n's entry at +0xC + 8n)
MARIO_VT = 0x10139E60
SETUP_HOOK = 0x02F1A6F0          # slot 0 (entry 0x10139E6C): li r5, 1 (then b 0x02F1A598)
SETUP_BODY = 0x02F1A598          # his setup (r5 = 1)
SLOT42_HOOK = 0x02F1B218         # slot 42 (entry 0x10139FBC): blr
SLOT43_HOOK = 0x02F1B21C         # slot 43 (entry 0x10139FC4): li r3, 1
ORIGINAL = {SETUP_HOOK: 0x38A00001, SETUP_HOOK + 4: 0x4BFFFEA4, SLOT42_HOOK: 0x4E800020, SLOT43_HOOK: 0x38600001,
            SLOT43_HOOK + 4: 0x4E800020, 0x02C0F7F0: 0x4BFFFAF9}

# game functions (none is an import)
GROUP_INIT = 0x0200C858          # ShieldModule: (M, desc, group)
GROUP_STATE = 0x0200BD8C         # ShieldModule vt +0x6C: (M, shape, on, group)
SIDE = 0x02C22684                # Marth's side: (module [acc+0x7290], attacker AM, hit data, id, part, f1, f2) -> f1
HANDLE = 0x02BF2108              # (manager [0x102F6C30], &handle, object id, 0)
HANDLE_GONE = 0x02BEF50C         # (&handle) -> 0 while the object exists
HANDLE_POS = 0x02BEF640          # (&handle) -> its position (x +0, y +4)
OBJ_MANAGER = 0x102F6C30
SETVIS = 0x034232FC              # the game's mesh visibility setter (MI, mesh, value, which): which 0 = the set state
MV_APPLY = 0x04BE4294            # tools/mesh_vis_cave.py's mv_apply in exe_v46z_outline4 (its words asserted)
MV_APPLY_WORDS = (0x9421FFE0, 0x7C0802A6, 0x90010024, 0x90610010)
MV_ARR = 0x7DC                   # the instance's per-mesh visibility bytes: [[MI + 0x7DC] + 4] + mesh
# ui4: Mesh_Visibility's name walk (tools/mesh_vis_cave.py in exe_v46z_outline4) checked the name pointer the mesh's vt
# +0x2C gives like any heap pointer, 4-aligned too; the model loader copies the names into one buffer back to back
# (0x036DC8E8: strlen + 1 each), so a name at an unaligned address read as "no name": its mesh was never matched and
# was taken for a part of the match before it (the v4 log: Mario_Nohat hit meshes 5-8, Mario_Hair / the eye and full
# hair copies / 6 overlays never). The alignment test (andi. r0, r3, 3) becomes a nop; its bne then never branches
# (cr0 from the range test just passed). mesh_vis_cave.py's source has the same fix (chk_str)
WALK_FIX = 0x04BE4200
WALK_WORDS = {0x04BE41F0: 0x4E800421, 0x04BE41F4: 0x3C03F000, 0x04BE41F8: 0x54000001, 0x04BE41FC: 0x40820040,
              WALK_FIX: 0x70600003, 0x04BE4204: 0x40820038, 0x04BE4208: 0x88030000}
NOP = 0x60000000

# --diag (TEST ONLY): OSReport lines through the game's veneer (diag_crumbs_cave.py), no pauses (nothing here can crash
# the game in a way the lines would explain); the motion -> script lookup's two hooks
OSREPORT_VENEER = 0x0288B4D4
VENEER_WORDS = (0x9421FFF0, 0x93E1000C, None, None, 0x7FE903A6, 0x83E1000C, 0x38210010, 0x4E800420)
MHASH_HOOK = 0x02E42518          # the kind's motion -> script hash (table, kind, motion): `li r0, 0x10`
MHASH_FROM = 0x027607D0          # its call in the motion change 0x027606C0 (r30 the kind, r29 / r28 the sets)
BIND_HOOK = 0x02BEE580           # `bl 0x02BEE404` in the agent bind 0x02BEE560 (r5 the hash): r3 0 found / -1 not
BIND_FN = 0x02BEE404
BIND_FROM = 0x02760864           # 0x02BEE560's call in the motion change (r29 the set: 0 game 1 expression 2 sound
                                 # 3 effect, r30 the kind)
LATE_FN = 0x02760DB0             # v5: the script module's per-frame late update (r3 the module, [r3 + 4] its object)
LATE_HOOK = 0x02E4133C           # its one call (`bl 0x02760DB0`, the accessor's update: r3 = [acc + 0xC4]): S4U4 for
                                 # the fighter whose dodge slot 43 just signalled (0x02760DB0 itself is out of a b's reach)
EFT_PRINT = 0x04A58A8C           # ui4 diag: the effect runtime's message print ("Emitter is Empty.", "Particle is
                                 # Empty.", "Emitter Set is Empty.", ...: a no-op in the game's build): to OSReport
EFT_CAP = 300                    # its lines at most
EFF_MGR = 0x10353CA4             # ui4 diag S4UF: the effect manager (docs/efc-format.md): 0x032EFEA0(mgr, bank, 0) its
EFF_SLOT = 0x032EFEA0            # bank's slot index (< 0x7F), slot = mgr + 0xB8 + 0x80 index: +4 the .ptcl's resource,
UI_BANK = 0x341                  # +8 the .efc file (+8 its entry count: an effect id's index must be below it)
DIAG_ORIGINAL = {MHASH_HOOK: 0x38000010, BIND_HOOK: 0x4BFFFE85, LATE_HOOK: 0x4B91FA75, EFT_PRINT: 0x9421FF90}
DIAG_LATE_N = 8                  # S4U4 lines after a dodge signal (that many frames of his)
DIAG_CAP = 1500                  # lines of S4UM / S4UB at most (the UI motions' lines always)
DIAG_MOTIONS = (0x229, 0x231, 0x235, 0x239, 0x241, 0x245)   # S4UM always (Fake Death's / Sledgehammer's: controls)
DIAG_HASHES = ('speciallwlight', 'speciallwheavy', 'specialairlwlight', 'specialairlwheavy', 'speciallwstart',
               'specialairlwstart', 'entryl', 'entryr', 'wait1')
DIAG_FMTS = [
    ('f42', 'S4U2 st=%X grp=%d cat=%d obj=%08X flags=%08X x=%08X y=%08X\n'),
    ('f42c', 'S4U5 chain n=%d %08X %08X %08X %08X\n'),
    ('f43', 'S4U3 st=%X t0=%08X ret=%d\n'),
    ('fmv', 'S4UV mi=%08X mesh=%d val=%d before=%02X after=%02X\n'),
    ('fmh', 'S4UM kind=%X motion=%X hash=%08X n=%d st=%X\n'),
    ('fbd', 'S4UB hash=%08X found=%d set=%d kind=%X n=%d\n'),
    ('f44', 'S4U4 st=%X t1=%08X t2=%08X mode=%08X left=%d\n'),
    ('fef', 'S4UF bank=%X slot=%d entries=%d res=%d motion=%X\n'),
    ('fpf', 'S4UP obj=%08X him=%08X n=%d\n'),
    ('fws', 'S4UW on=%d owner=%08X mode=%d stage=%08X\n'),
]
DIAG_PF_CAP = 200                # v7: S4UP lines at most
FIGHTERS = 0x1035184C            # [[FIGHTERS] + 0]: +0 the entries, +8 their count (acmd_ext_cave.py)
FIGHTER_ENTRY = 0x76B0           # entry: +0 object id, +0xC accessor, byte +0x1E >= 4 live

# the fighter / its modules (the slot's r4 is the fighter's table entry: +0 its id, +4 its kind, +0x28 -> the
# module block whose +0x72xx are the modules, edge_counter_cave.py's)
ACC = 0x28
KIND_AT = 4
SHIELD = 0x72F4                  # kind-2 ShieldModule (guard = group 0)
STATUS_MOD = 0x7264              # StatusModule (+0x48 the status kind)
WORK = 0x726C                    # WorkModule ([+8] categories, [1] = status work; vt +0x44 get_float, +0x4C set)
POSTURE = 0x72E4                 # PostureModule (+0x10 x)
SIDE_MOD = 0x7290
BASE_POSTURE = 0x18              # a base accessor's PostureModule (vt +0x44 -> its position)
BASE_ATTACK = 0x50               # a base accessor's AttackModule
BASE_OWNER = 0x6C                # a base accessor's team / owner module (+0x34 the current owner's id: the reflector
                                 # after a reflect; docs/native-notes.md "Reflection", "Teams")
BASE_LINK = 0x68                 # a base accessor's LinkModule: vt +0x5C(0) has link 0, vt +0x6C(0, 1) its object id
                                 # (a weapon's owner: docs/native-notes.md "A weapon's owner")
OWNER_DEPTH = 4                  # v4: the owner chain's steps at most (a shot -> its item -> the item's thrower ...)
NO_OBJECT = 0x50000000

GROUP = 1
# v5 (exe_v46z_ui3): the transformation / its counter and the autododge are MODES of the down special's status 0x155
# (Fake Death's / Sledgehammer's / Secret Sensation's), told apart by TIMER_4 (V_MODE): v1-v4 used Mario's F.L.U.D.D.
# statuses 0x157 / 0x158, which his native code keeps for the pump (0x02F169D0 on leaving them, 0x02F11C0C, the pump's
# own code; docs/native-notes.md "Supamario's Ultra Instinct" v5)
ST_SS = 0x155                    # the down special: Secret Sensation while transformed (its MSC switches the shape)
ST_UI = ST_SS                    # the transformation / counter: 0x155 with TIMER_4 > MODE_FORM_ON
ST_DODGE = ST_SS                 # the dodge: 0x155 with TIMER_4 in (MODE_DODGE_ON, MODE_FORM_ON] (nothing here)
OLD_ST_UI, OLD_ST_DODGE = 0x157, 0x158   # v1-v4's (the tests: nothing special there any more)
DODGE_LO, DODGE_HI = 0x0, 0x2    # Wait, Walk, WalkBrake
SQUAT_LO, SQUAT_HI = 0x11, 0x15  # Squat, SquatWait, SquatF, SquatB, SquatRv
# v12 (exe_v46z_ui8; the user: "teetering on an edge also allows for the autododge"): Ottotto, OttottoWait (the teeter on
# a ledge's edge, reference/msc-note-sheet/Actions_Fighters.csv)
OTTOTTO_LO, OTTOTTO_HI = 0x7B, 0x7C
ST_OTTOTTO = OTTOTTO_LO
# status work: floats 6-9, flags word 0 bits 16-18
F_DAMAGE, F_SIDE, F_TX, F_TY = 6, 7, 8, 9
FLAG_HIT, FLAG_NOTFIGHTER, FLAG_FOUND = 0x21000010, 0x21000011, 0x21000012
# the user variables (docs/acmd-extra-commands.md: TIMER_0-15; unused by every earlier Supamario script and his MSC)
V_FORM = 0x0F000320              # TIMER_0: his MSC writes 0 / 1000 (transforming) / 2000 (transformed) every frame
V_DODGE_R = 0x0F000321           # TIMER_1: a dodge asked, the attacker to his right
V_DODGE_L = 0x0F000322           # TIMER_2: ... to his left
V_MODE = 0x0F000324              # TIMER_4: status 0x155's mode (his MSC: 7 the transformation, 5 the dodge, renewed every
                                 # frame; 3 Secret Sensation; 0 Fake Death / Sledgehammer)
# v7 (exe_v46z_ui6): four modes; TIMER_4 counts down by itself, so each mode is at least 1.5 from the next threshold
MODE_FORM = 9.0                  # the transformation / its counter
MODE_DODGE = 7.0                 # the autododge (XV2's sway)
MODE_COUNTER = 5.0               # v7: the sway's / spot dodge's counter (XV2's CMN.bac entry 706)
MODE_FORM_ON = 7.5               # 0x155 is the transformation (its counter included) above this
MODE_DODGE_ON = 5.5              # ... the autododge above this (and not above MODE_FORM_ON)
MODE_SWAY_ON = 3.5               # v7: the sway family (the autododge, its counter) above this; Secret Sensation (3) and
                                 # Fake Death / Sledgehammer (0) below
ST_ESCAPE_N = 0x1F               # v7: his spot dodge (EscapeN): the shape on while transformed (the counter's "attacked")
# v7: the projectile filter (README "Ultra Instinct v7"). The collision manager's pair pass 0x02C0F6F0 (A, B, flag) is
# run by 0x02C117F8 over the type pairs of the table 0x10351914 ({type A, type B, flag} x 11: (3, 0) reflector / attack,
# (4, 0) absorber, (0, 0) clank, (2, 0) SHIELD vs attack, (0, 1) attack vs hurtbox, ...), so a shield meets an attack
# before the hurtboxes do and its record keeps the attack off the body. The node masks (0x02D42C44: every 3-7 bit field
# of A.w0 & B.w1 and A.w1 & B.w0 non-zero) can't tell a fighter's attack from a projectile: the attack's object class
# (w0 bits 19-24, 1 << [AttackModule + 0x110]) is 0 for fighters (0x02E5402C) and for every weapon (their default block
# fill 0x032108D8, 0x0320E748 in ~400 weapon vtables), and a shield node's w1 is 0xFFFFFFFF (0x02C6FBB4). So the cave
# hooks the pass's per-entry check (`bl 0x02C0F2E8` at 0x02C0F7F0: A's entry r4, B's entry r5, A's container r3; the
# caller's r31 = B's container): when A is HIS counter shape (kind 0x41, his ShieldModule's container M + 0x18, its
# group 1's collision object) and B's object is not a fighter (container +0x1C = id >> 28 != 0), the pair doesn't meet
# (except in Secret Sensation, which answers anything an opponent owns): the projectile / item goes on to the attack /
# hurtbox pass and hits him as normal. Grabs never meet a shield (the catch pass is (6, 1)).
PF_HOOK = 0x02C0F7F0             # `bl 0x02C0F2E8` in the pair pass
PF_FN = 0x02C0F2E8               # the facing / position check (A container, A entry, B entry) -> 0 skip
PF_WORD = 0x4BFFFAF9
FORM_ON = 1500.0                 # transformed: TIMER_0 above this
DODGE_SIGNAL = 4.0               # the timers count down by themselves: a signal the MSC missed dies in 4 frames
MAX_FIGHTERS, MAX_PARTS, MAX_NODES = 16, 16, 32

# v10 (exe_v46z_ui7; README "Ultra Instinct v10"):
# 1. The shield-hit mark. A hit on a shield shape is event 0x10 (fighter.handler 0x02E35794: slot 42 first, then the
#    EffectModule's +0x90 = 0x0100001F, common effect 0x1F: PtcCommonGuardMark, the ring and flash of the user's v9
#    clip). The EffectModule listens to the same event (its init 0x02C28DD0 registers 0x02C2CD28 for event 0x10,
#    0x02C2CDC0 for 0x11): 0x02C2CD28 (r3 the EffectModule, r4 the message: +8 the attacker's AttackModule, +0x10 the
#    record, +0x14 the shape group) asks the hit's data (vt +0x194) and, when its +0x54 is 0, requests effect [EM +
#    0x90] at the record's place (vt +0x44). SX_HOOK: for HIS counter shape (group 1; the EffectModule the one of a live
#    kind-0x41 fighter: module block + EFFM = fighter + 0x74D8, the module the handler writes +0x90 into) nothing is
#    requested: no mark on a dodge (and on Secret Sensation / the transformation's counter, which have their own
#    effects now); his guard bubble (group 0) and every other shield keep it.
# 2. The WORLD STOP (Secret Sensation, DBFZ's): his MSC asks it with TIMER_6 (V_STOP > 0.5, renewed every frame).
#    STEP_HOOK (the fighter's step wrapper 0x02E40B90, r3 the fighter, r4 its module block; from the fighter update
#    0x02E40C4C and 0x02E2534C): for a kind-0x41 fighter asking it, the stop starts (ws_begin) or its lease is renewed
#    (WS_LEASE frames); while it runs, HIS step runs on a normal frame (the frame state's +8 cleared for its length:
#    every module of his runs). FILL_HOOK (the frame state fill 0x02BFB97C, once a battle step, before the objects): the
#    lease counted down; while it lasts the frame state is a slowed frame in the middle of its cycle (+8 1, +0 1, the
#    fill's answer 0), the one in which no object steps (0x02E40B90, the weapons' and items' wrappers: +8 0 or +0 2
#    steps; the game's own slow-motion frames between two steps); at 0 the world goes on (ws_end). ws_begin pauses
#    every effect instance that isn't his and isn't paused (the instance list [INST_LIST], +0x18 next: +0x19E = 1,
#    0x032F0F10's write, the Final Smashes' way through 0x0334CA30; the instance update 0x0334E080 then holds it:
#    +0x19F 0, its clock stopped), his own (+8 & PAUSE_MASK = his EffectModule's +0x10 | 0x8000: the EffectModule's own
#    pause key, 0x02C27E88) left running, and stops the stage (0x0316505C(stage manager, 1), the Final Smashes' call,
#    unless [[STAGE_FLAGS] + 0xB3] as they check); ws_end lets the instances it paused go and the stage on
INST_LIST = 0x10439088           # the effect manager's instance list (+0x18 next, +8 the owner key, +0x19E paused,
                                 # +0x1A4 kept out of a pause)
PAUSE_MASK = 0x0100BFFF          # an EffectModule's own pause: key = [EM + 0x10] | 0x8000 under this mask (0x02C27E88)
STAGE_MGR = 0x102F7020           # [STAGE_MGR]: the stage manager (0x0316505C(manager, on): +0xD0 the stop)
STAGE_FLAGS = 0x102F7024         # [STAGE_FLAGS] + 0xB3: the Final Smash code skips the stage stop when set (0x02772674)
STAGE_STOP = 0x0316505C
FRAME_STATE = 0x102F6C04         # [FRAME_STATE]: +0 the phase (2 a step), +4 1/N, +8 1 while slowed
FILL_HOOK = 0x02BFB97C           # the frame state fill: `mflr r0`
STEP_HOOK = 0x02E40B90           # the fighter's step wrapper: `mflr r0`
SX_HOOK = 0x02C2CD28             # the EffectModule's shield-hit listener: `mflr r0`
MFLR = 0x7C0802A6
EFFM = 0x72A8                    # the module block's EffectModule (fighter + 0x74D8; the block is fighter + 0x230)
V_STOP = 0x0F000326              # TIMER_6: the world stop asked (his MSC)
WS_LEASE = 2                     # frames the stop lasts after the last ask
WS_MAX = 100                     # instances paused at most (the effect manager's pool holds 100)
WS_STAGE_ONLY = 4.5              # v13: an ask (TIMER_6) above this stops the stage only (ws_stagef)
ORIGINAL.update({FILL_HOOK: MFLR, STEP_HOOK: MFLR, SX_HOOK: MFLR})

# the shape: x sideways, y up, z forward (joint 0's frame); a capsule round his body
SHAPE = {'bone': 0, 'p1': (0.0, 2.5, 0.0), 'p2': (0.0, 9.5, 0.0), 'radius': 8.0}   # v12: 6.5 -> 8 (OttottoWait's
# flailing hand reaches 7.73 from the axis; Wait 5.07, SquatWait 4.11)
SHAPE_TYPE = 2
DESC_BYTES = (0, 0, 0, 1)        # Marth's counter group (+0x28 0: not front only)


def kind(spec=SPEC, name=NAME):
    for k in json.load(open(spec))['kinds']:
        if k['name'] == name:
            assert k['base'] == 'mario', 'the cave hooks Mario\'s specializer: %s has base %s' % (name, k['base'])
            return int(k['kind'], 0)
    raise SystemExit('no kind %r in %s' % (name, spec))


def hilo(v):
    return v >> 16, v & 0xFFFF


def ha(v):
    return ((v + 0x8000) >> 16) & 0xFFFF


def slo(v):
    v &= 0xFFFF
    return v - 0x10000 if v >= 0x8000 else v


def call(name):
    return """
        lis r12, %(""" + name + """_hi)d
        ori r12, r12, %(""" + name + """_lo)d
        mtctr r12
        bctrl"""


def fmt_words(text):
    """.word lines of a NUL-ended string, padded to a word"""
    b = text.encode() + b'\0'
    b += b'\0' * (-len(b) % 4)
    return ''.join('\n        .word 0x%08X' % int.from_bytes(b[i:i + 4], 'big') for i in range(0, len(b), 4))


D43 = {'d43_zero': """
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        li r0, 0
        stw r0, 0(r11)
        stw r0, 4(r11)
        stw r0, 8(r11)
        li r0, -1
        stw r0, 0xC(r11)""",
       'd43_t0': """
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        stfs f1, 0(r11)""",
       'd43_found': """
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        lwz r0, 0(r24)
        stw r0, 4(r11)
        li r0, 1
        stw r0, 8(r11)""",
       'd43_sig': """
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        stw r26, 0x30(r11)
        stw r31, 0x28(r11)
        li r0, """ + str(DIAG_LATE_N) + """
        stw r0, 0x2C(r11)""",
       'd43_unc': """
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        stw r0, 0xC(r11)"""}

DPF = """
        bl ui_dpf"""                    # v7 diag: S4UP, a projectile / item let through his counter shape

OSR = """
        lis r12, %(osr_hi)d
        ori r12, r12, %(osr_lo)d
        mtctr r12
        .word 0x4CC63182                # crclr 6: no float arguments
        bctrl"""

RELEASE_TAIL = """
# the diag build's lines (TEST ONLY); this build: none
ui_dchain:
ui_dmv:
ui_dws:
        blr
"""

DIAG_TAIL = """
# v10: S4UW on owner n stage (r4 1 the world stopped / 0 going on, r5 his fighter, r6 the instances paused, r7 the
# stage manager): ws_begin / ws_end (the volatile registers go)
ui_dws: stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        lis r3, ui_fws@ha
        addi r3, r3, ui_fws@l""" + OSR + """
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# ---- TEST ONLY (--diag): the lines (docs/native-notes.md "Supamario's Ultra Instinct" v4) --------------------------
# ui_drec: +0 TIMER_0 as slot 43 read it, +4 the attacker found (its id), +8 found, +0xC the hit's uncounterable byte
# (-1 not read), +0x10 the slot-42 owner chain's ids (4), +0x20 their count, +0x24 S4UM / S4UB lines so far
# ui_dchain (slot 42, r26 the next owner): kept in the record. Leaf: r0, r11, r12
ui_dchain:
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        lwz r12, 0x20(r11)
        cmplwi r12, 4
        bgelr
        slwi r0, r12, 2
        add r0, r0, r11
        addi r12, r12, 1
        stw r12, 0x20(r11)
        mr r12, r0
        stw r26, 0x10(r12)
        blr

# slot 42 for kind 0x41 (the hook's target in this build): the slot, then S4U2 (and S4U5 when an owner chain ran)
ui_d42w:
        lwz r12, %(kind_at)d(r4)
        cmpwi r12, %(kind)d
        bne slot42
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stw r4, 0x10(r1)
        stw r5, 0x14(r1)
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        li r0, 0
        stw r0, 0x20(r11)
        stw r0, 0x30(r11)
        bl slot42
        lwz r5, 0x14(r1)
        lwz r12, 0x10(r5)               # the record
        lbz r6, 0x1C(r12)               # its category
        lwz r7, 0x18(r12)               # its object
        lwz r5, 0x14(r5)                # the group hit
        lwz r4, 0x10(r1)
        lwz r12, %(acc)d(r4)
        lwz r11, %(st)d(r12)
        lwz r4, 0x48(r11)               # the status
        lwz r11, %(work)d(r12)
        lwz r11, 8(r11)
        lwz r11, 4(r11)                 # status work
        lwz r8, 0x14(r11)
        lwz r8, 0(r8)                   # its flags word (0x21000010 = 0x00010000, 11 = 0x20000, 12 = 0x40000)
        lis r12, ui_drec@ha
        addi r12, r12, ui_drec@l
        lwz r0, 0x30(r12)               # ui4: | 0x321 / 0x322 when the autododge signalled TIMER_1 / TIMER_2
        or r8, r8, r0
        lwz r11, 4(r11)
        lwz r9, %(ftx)d(r11)            # the X / Y written (float bits)
        lwz r10, %(fty)d(r11)
        lis r3, ui_f42@ha
        addi r3, r3, ui_f42@l""" + OSR + """
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        lwz r4, 0x20(r11)
        cmpwi r4, 0
        beq d42_out
        lwz r5, 0x10(r11)
        lwz r6, 0x14(r11)
        lwz r7, 0x18(r11)
        lwz r8, 0x1C(r11)
        lis r3, ui_f42c@ha
        addi r3, r3, ui_f42c@l""" + OSR + """
d42_out:
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

# slot 43 for kind 0x41: the slot, then S4U3 (every damage event of his)
ui_d43w:
        lwz r12, %(kind_at)d(r4)
        cmpwi r12, %(kind)d
        bne slot43
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stw r4, 0x10(r1)
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        li r0, 0
        stw r0, 0(r11)
        stw r0, 4(r11)
        stw r0, 8(r11)
        li r0, -1
        stw r0, 0xC(r11)
        bl slot43
        stw r3, 0x18(r1)
        mr r9, r3
        lwz r4, 0x10(r1)
        lwz r12, %(acc)d(r4)
        lwz r11, %(st)d(r12)
        lwz r4, 0x48(r11)
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        lwz r5, 0(r11)
        mr r6, r9
        lis r3, ui_f43@ha
        addi r3, r3, ui_f43@l""" + OSR + """
        lwz r3, 0x18(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

# Persist 2's write (mvp2: r3 the mesh, r4 the byte before, r27 the instance, r30 the parameters): S4UV
ui_dmv:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        mr r5, r3
        lwz r12, %(va)d(r27)
        lwz r12, 4(r12)
        lbzx r8, r12, r3                # the byte after
        mr r7, r4
        lwz r6, 8(r30)
        mr r4, r27
        mr r5, r3
        lis r3, ui_fmv@ha
        addi r3, r3, ui_fmv@l""" + OSR + """
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# the motion -> script hash lookup (b from its first word): from the motion change for kind 0x41, S4UM
ui_dmh: mflr r0
        lis r12, %(mhf_hi)d
        ori r12, r12, %(mhf_lo)d
        cmplw r0, r12
        bne dmh_orig
        cmpwi r4, %(kind)d
        bne dmh_orig
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        stw r4, 0x10(r1)
        stw r5, 0x14(r1)
        bl dmh_orig
        stw r3, 0x18(r1)
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        lwz r8, 0x24(r11)
        lwz r5, 0x14(r1)
        bl ui_dmot                      # r3 1: a motion always logged
        cmpwi r3, 0
        bne dmh_log
        cmplwi r8, 20
        bge dmh_out
dmh_log:
        cmplwi r8, %(cap)d
        bge dmh_out
        addi r8, r8, 1
        stw r8, 0x24(r11)
        lwz r4, 0x10(r1)
        lwz r5, 0x14(r1)
        lwz r6, 0x18(r1)
        mr r7, r8
        lwz r12, 4(r27)                 # v5: the status (0x027606C0's r27 = the script module, + 4 its object)
        lwz r12, %(st)d(r12)
        lwz r8, 0x48(r12)
        lis r3, ui_fmh@ha
        addi r3, r3, ui_fmh@l""" + OSR + """
        lwz r8, 0x14(r1)                # ui4: the transformation's / Secret Sensation's motion: S4UF, his effect
        cmpwi r8, 0x%(mot_form)X        # bank's .efc entry count as the game holds it (an id 0x0341nnnn needs nnnn
        beq dmh_ef                      # below it)
        cmpwi r8, 0x%(mot_ss)X
        bne dmh_out
dmh_ef: lis r3, %(efm_hi)d
        ori r3, r3, %(efm_lo)d
        lwz r3, 0(r3)
        cmpwi r3, 0
        beq dmh_out
        stw r3, 0x1C(r1)
        li r4, %(bank)d
        li r5, 0
        lis r12, %(efs_hi)d
        ori r12, r12, %(efs_lo)d
        mtctr r12
        bctrl
        mr r5, r3
        li r6, -1
        li r7, -1
        cmplwi r3, 0x7F
        bge dmh_efp
        slwi r12, r3, 7
        lwz r11, 0x1C(r1)
        add r12, r12, r11
        addi r12, r12, 0xB8
        lwz r7, 4(r12)                  # the .ptcl's resource
        lwz r11, 8(r12)                 # the .efc
        cmpwi r11, 0
        beq dmh_efp
        lha r6, 8(r11)
dmh_efp:
        li r4, %(bank)d
        lwz r8, 0x14(r1)
        lis r3, ui_fef@ha
        addi r3, r3, ui_fef@l""" + OSR + """
dmh_out:
        lwz r3, 0x18(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
dmh_orig:
        li r0, 0x10                     # the replaced word
        b 0x%(mh_back)08X

# v5: the script module's late update (bl from its call 0x02E4133C; every object, every frame): S4U4 for the
# fighter slot 43 just wrote a dodge signal for (ui_drec +0x28 its module block, +0x2C frames left): his status,
# TIMER_1 / TIMER_2 / TIMER_4 (float bits), the lines left
ui_dlate:
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        lwz r12, 0x2C(r11)
        cmpwi r12, 0
        ble dl_orig
        lwz r0, 4(r3)
        lwz r12, 0x28(r11)
        cmpw r0, r12
        bne dl_orig
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stw r3, 0x10(r1)
        stw r30, 0x38(r1)
        stw r31, 0x3C(r1)
        lwz r12, 0x2C(r11)
        addi r12, r12, -1               # (not r0: addi's rA 0 is the literal 0)
        stw r12, 0x2C(r11)
        lwz r31, 0x28(r11)              # his module block
        lwz r30, %(work)d(r31)          # his WorkModule
        mr r3, r30
        lis r4, %(vform_hi)d
        ori r4, r4, %(vr_lo)d
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl
        stfs f1, 0x18(r1)
        mr r3, r30
        lis r4, %(vform_hi)d
        ori r4, r4, %(vl_lo)d
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl
        stfs f1, 0x1C(r1)
        mr r3, r30
        lis r4, %(vmode_hi)d
        ori r4, r4, %(vmode_lo)d
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl
        stfs f1, 0x20(r1)
        lwz r12, %(st)d(r31)
        lwz r4, 0x48(r12)
        lwz r5, 0x18(r1)
        lwz r6, 0x1C(r1)
        lwz r7, 0x20(r1)
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        lwz r8, 0x2C(r11)
        lis r3, ui_f44@ha
        addi r3, r3, ui_f44@l""" + OSR + """
        lwz r3, 0x10(r1)
        lwz r30, 0x38(r1)
        lwz r31, 0x3C(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
dl_orig:
        lis r12, %(late_hi)d             # on to 0x02760DB0 (LR: the call's return)
        ori r12, r12, %(late_lo)d
        mtctr r12
        bctr

# ui4: the effect runtime's message print (b from 0x04A58A8C, its first word): OSReport with the same arguments (r3 the
# format, r4-r10, cr1 as the caller set it), at most EFT_CAP lines; then the game's no-op as before
ui_deft:
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        lwz r12, 0x34(r11)
        cmplwi r12, %(eft_cap)d
        bge deft_orig
        addi r12, r12, 1
        stw r12, 0x34(r11)
        lis r12, %(osr_hi)d
        ori r12, r12, %(osr_lo)d
        mtctr r12
        bctr                            # OSReport returns to the print's caller
deft_orig:
        stwu r1, -0x70(r1)              # the replaced word
        b 0x%(eft_back)08X

# v7: S4UP (from ui_pf's drop: r29 A's container (his shape's), r31 B's (the attacker object's)): the object let
# through, his id, the count; at most DIAG_PF_CAP lines (ui_drec +0x38)
ui_dpf: stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        lwz r6, 0x38(r11)
        cmplwi r6, %(pf_cap)d
        bge dpf_out
        addi r6, r6, 1
        stw r6, 0x38(r11)
        lwz r4, 0x18(r31)
        lwz r5, 0x18(r29)
        lis r3, ui_fpf@ha
        addi r3, r3, ui_fpf@l""" + OSR + """
dpf_out:
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# ui_dmot(r5 a motion): r3 1 when it is one of DIAG_MOTIONS. Leaf: r0, r3, r12
ui_dmot:
        lis r12, ui_dmots@ha
        addi r12, r12, ui_dmots@l
dmo_l:  lwz r0, 0(r12)
        cmpwi r0, -1
        beq dmo_no
        addi r12, r12, 4
        cmpw r0, r5
        bne dmo_l
        li r3, 1
        blr
dmo_no: li r3, 0
        blr

# the agent bind's lookup (bl from 0x02BEE580): the lookup, then for the motion change of kind 0x41 and one of
# DIAG_HASHES, S4UB (found: the hash is in that set's files)
ui_dbind:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stw r5, 0x10(r1)""" + """
        lis r12, %(bind_hi)d
        ori r12, r12, %(bind_lo)d
        mtctr r12
        bctrl
        stw r3, 0x14(r1)
        lwz r0, 0x54(r1)                # 0x02BEE560's saved LR (its 0x10 frame above ours)
        lis r12, %(bdf_hi)d
        ori r12, r12, %(bdf_lo)d
        cmplw r0, r12
        bne dbd_out
        cmpwi r30, %(kind)d
        bne dbd_out
        lwz r5, 0x10(r1)
        lis r12, ui_dhash@ha
        addi r12, r12, ui_dhash@l
dbd_l:  lwz r0, 0(r12)
        cmpwi r0, 0
        beq dbd_out
        addi r12, r12, 4
        cmplw r0, r5
        bne dbd_l
        lis r11, ui_drec@ha
        addi r11, r11, ui_drec@l
        lwz r8, 0x24(r11)
        cmplwi r8, %(cap)d
        bge dbd_out
        addi r8, r8, 1
        stw r8, 0x24(r11)
        lwz r4, 0x10(r1)
        lwz r0, 0x14(r1)
        li r5, 1
        cmpwi r0, 0
        beq dbd_f
        li r5, 0
dbd_f:  mr r6, r29
        mr r7, r30
        lis r3, ui_fbd@ha
        addi r3, r3, ui_fbd@l""" + OSR + """
dbd_out:
        lwz r3, 0x14(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr
"""


def build(kind_id=None, diag=False):
    """(words, labels): the cave from CAVE (diag: TEST ONLY, the OSReport lines and their hooks)"""
    if kind_id is None:
        kind_id = kind()
    a = Asm(CAVE)
    calls = {}
    for n, v in (('init', GROUP_INIT), ('state', GROUP_STATE), ('side', SIDE), ('handle', HANDLE),
                 ('gone', HANDLE_GONE), ('pos', HANDLE_POS), ('setvis', SETVIS)):
        calls[n + '_hi'], calls[n + '_lo'] = hilo(v)
    p = dict(kind=kind_id, acc=ACC, kind_at=KIND_AT, shield=SHIELD, st=STATUS_MOD, work=WORK, posture=POSTURE,
             sidemod=SIDE_MOD, group=GROUP, st_ui=ST_UI, st_ss=ST_SS, back=SETUP_BODY, fdmg=4 * F_DAMAGE, fside=4 * F_SIDE,
             ftx=4 * F_TX, fty=4 * F_TY, mgr_ha=ha(OBJ_MANAGER), mgr_lo=slo(OBJ_MANAGER), fts_ha=ha(FIGHTERS),
             fts_lo=slo(FIGHTERS), entry=FIGHTER_ENTRY, bpost=BASE_POSTURE, batk=BASE_ATTACK, bown=BASE_OWNER, blink=BASE_LINK, depth=OWNER_DEPTH,
             noobj_hi=NO_OBJECT >> 16, dlo=DODGE_LO, dhi=DODGE_HI, sqlo=SQUAT_LO, sqhi=SQUAT_HI,
             otlo=OTTOTTO_LO, othi=OTTOTTO_HI,
             vform_hi=V_FORM >> 16, vform_lo=V_FORM & 0xFFFF, vmode_hi=V_MODE >> 16, vmode_lo=V_MODE & 0xFFFF, vr_lo=V_DODGE_R & 0xFFFF, vl_lo=V_DODGE_L & 0xFFFF,
             maxf=MAX_FIGHTERS, maxp=MAX_PARTS, maxn=MAX_NODES, mv_back=MV_APPLY + 4, va=MV_ARR,
             osr_hi=OSREPORT_VENEER >> 16, osr_lo=OSREPORT_VENEER & 0xFFFF, mhf_hi=MHASH_FROM >> 16,
             mhf_lo=MHASH_FROM & 0xFFFF, mh_back=MHASH_HOOK + 4, bind_hi=BIND_FN >> 16, bind_lo=BIND_FN & 0xFFFF,
             bdf_hi=BIND_FROM >> 16, bdf_lo=BIND_FROM & 0xFFFF, cap=DIAG_CAP, late_n=DIAG_LATE_N,
             late_hi=LATE_FN >> 16, late_lo=LATE_FN & 0xFFFF, efm_hi=EFF_MGR >> 16, efm_lo=EFF_MGR & 0xFFFF,
             efs_hi=EFF_SLOT >> 16, efs_lo=EFF_SLOT & 0xFFFF, bank=UI_BANK, eft_cap=EFT_CAP, eft_back=EFT_PRINT + 4,
             mot_form=0x231, mot_ss=0x245, escn=ST_ESCAPE_N, pf_cap=DIAG_PF_CAP, pff_hi=PF_FN >> 16, pff_lo=PF_FN & 0xFFFF,
             effm=EFFM, sx_back=SX_HOOK + 4, fill_back=FILL_HOOK + 4, step_back=STEP_HOOK + 4,
             vstop_hi=V_STOP >> 16, vstop_lo=V_STOP & 0xFFFF, lease=WS_LEASE, wsmax=WS_MAX, wsguard=4 * WS_MAX,
             inst_ha=ha(INST_LIST), inst_lo=slo(INST_LIST), mask_hi=PAUSE_MASK >> 16, mask_lo=PAUSE_MASK & 0xFFFF,
             stg_ha=ha(STAGE_MGR), stg_lo=slo(STAGE_MGR), stgf_ha=ha(STAGE_FLAGS), stgf_lo=slo(STAGE_FLAGS),
             fs_ha=ha(FRAME_STATE), fs_lo=slo(FRAME_STATE), stop_hi=STAGE_STOP >> 16, stop_lo=STAGE_STOP & 0xFFFF,
             **calls)
    p.update({k: (v if diag else '') for k, v in D43.items()})
    p['dpf'] = DPF if diag else ''
    a.asm(("""
# ---- 1. setup (r3 spec, r4 fighter, r5 = whatever: the replaced word sets 1)
setup:  lwz r12, %(kind_at)d(r4)
        cmpwi r12, %(kind)d
        bne setup_tail
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        stw r3, 0x8(r1)
        stw r4, 0xC(r1)
        lwz r12, %(acc)d(r4)
        lwz r31, %(shield)d(r12)        # M: the kind-2 ShieldModule
        cmpwi r31, 0
        beq setup_done
        mr r3, r31                      # 0x0200C858(M, &desc, 1)
        lis r4, ui_desc@ha
        addi r4, r4, ui_desc@l
        li r5, %(group)d""" + call('init') + """
        mr r3, r31                      # 0x0200BD8C(M, 0, 0, 1): the shape off
        li r4, 0
        li r5, 0
        li r6, %(group)d""" + call('state') + """
setup_done:
        lwz r3, 0x8(r1)
        lwz r4, 0xC(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
setup_tail:
        li r5, 1                        # the replaced word
        b 0x%(back)08X

# ---- 2. slot 42 (r3 spec, r4 fighter, r5 message): the counter
slot42: lwz r12, %(kind_at)d(r4)
        cmpwi r12, %(kind)d
        bnelr
        lwz r12, 0x14(r5)               # the shield group hit
        cmpwi r12, %(group)d
        bnelr
        lwz r12, %(acc)d(r4)
        lwz r11, %(st)d(r12)
        lwz r11, 0x48(r11)              # status kind: 0x155 (the transformation, Secret Sensation; v5)
        cmpwi r11, %(st_ss)d
        beq s42_ss
        cmpwi r11, %(escn)d             # v7: his spot dodge while transformed: the dodge's signal marks "attacked" (the
        beq s42_dg                      # counter from EscapeN, his MSC)
        cmplwi r11, %(dhi)d             # ui4: the autododge (the shape is on in Wait / Walk / WalkBrake / Squat ..
        ble s42_dg                      # SquatRv while transformed: his MSC's ui_tick)
        cmpwi r11, %(otlo)d             # v12: Ottotto / OttottoWait (the teeter)
        blt s42_sq
        cmpwi r11, %(othi)d
        ble s42_dg
        blr
s42_sq: cmpwi r11, %(sqlo)d
        bltlr
        cmpwi r11, %(sqhi)d
        bgtlr
        b s42_dg
s42_ss: stwu r1, -0x20(r1)              # v7: 0x155 in the sway family (the autododge / its counter: TIMER_4 in
        mflr r0                         # (MODE_SWAY_ON, MODE_FORM_ON]): a hit on the shape is another dodge (XV2's
        stw r0, 0x24(r1)                # sway chains), not Secret Sensation's record
        stw r4, 0x10(r1)
        stw r5, 0x14(r1)
        stw r12, 0x18(r1)
        lwz r3, %(work)d(r12)
        bl ui_mode4
        lwz r4, 0x10(r1)
        lwz r5, 0x14(r1)
        lwz r12, 0x18(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        cmpwi r3, 1
        beq s42_dg
        lwz r11, %(work)d(r12)
        lwz r11, 8(r11)
        lwz r11, 4(r11)                 # status work
        lwz r10, 0x14(r11)
        lwz r10, 0(r10)
        rlwinm. r10, r10, 0, 15, 15     # 0x21000010: answered already
        bnelr
        stwu r1, -0x60(r1)
        mflr r0
        stw r0, 0x64(r1)
        stmw r24, 0x40(r1)
        mr r31, r12                     # the module block
        mr r30, r5                      # message
        mr r29, r11                     # status work
        lwz r28, 0x10(r5)               # the collision record
        li r25, 0                       # flag bits to add
        lbz r0, 0x1C(r28)               # the attacker's category (id >> 28): 0 fighter, 1 weapon, 4 item (ui4: the
        cmplwi r0, 3                    # Killer Eye's 0x4001000x in the v4 log; 2 kept), 3 a gimmick: Secret
        beq out42                       # Sensation answers anything an opponent owns, never a gimmick
        cmplwi r0, 4
        bgt out42
        lwz r3, %(work)d(r31)           # the transformation (v5: 0x155 with TIMER_4 > MODE_FORM_ON): XV2's
        bl ui_isform                    # CounterMelee only (a fighter's own attack)
        cmpwi r3, 0
        beq s42_cat
        lbz r0, 0x1C(r28)
        cmplwi r0, 0
        bne out42
s42_cat:
        lwz r3, 8(r30)                  # the attacker's AttackModule: vt +0x194(id, part) = hit data
        lwz r12, 0(r3)
        lwz r12, 0x194(r12)
        lbz r4, 0x26(r28)
        lbz r5, 0x29(r28)
        mtctr r12
        bctrl
        mr. r27, r3
        beq out42
        lbz r0, 0x54(r27)               # can't be countered
        cmpwi r0, 0
        bne out42
        lwz r3, %(sidemod)d(r31)        # the side, Marth's (the fallback)
        lwz r4, 8(r30)
        mr r5, r27
        lbz r6, 0x26(r28)
        lbz r7, 0x29(r28)
        lfs f1, 0x18(r30)
        lfs f2, 0x1C(r30)""" + call('side') + """
        stfs f1, 0x10(r1)
        lwz r26, 0x18(r28)              # the attacker's object id
        lbz r24, 0x1C(r28)              # its category (id >> 28): 0 a fighter
        cmpwi r24, 0
        beq have_id
        oris r25, r25, 2                # 0x21000011: not a fighter
        lis r3, %(mgr_ha)d              # a weapon / item: its place for the side, its owner to answer
        lwz r3, %(mgr_lo)d(r3)
        addi r4, r1, 0x18
        mr r5, r26
        li r6, 0""" + call('handle') + """
        addi r3, r1, 0x18
        bl ui_side_of                   # the side from the attacker object (0x10(r1)), when it exists
        cmpwi r3, 0
        bne no_target
        li r24, %(depth)d               # v4: the owner CHAIN (a Killer Eye's shot -> the Killer Eye -> its thrower)
own_step:
        lwz r12, 0x18(r1)               # [handle] = the object's entry: +0xC its accessor
        lwz r12, 0xC(r12)
        cmpwi r12, 0
        beq no_target
        stw r12, 0x30(r1)
        li r0, -1
        stw r0, 0x34(r1)                # the next object (none yet)
        lwz r11, %(bown)d(r12)          # 1. the team / owner module's +0x34: the current owner (a reflector
        cmpwi r11, 0                    #    after a reflect, else the spawner)
        beq own_link
        lwz r0, 0x34(r11)
        stw r0, 0x34(r1)
        mr r3, r0
        bl ui_id_ok
        cmpwi r3, 0
        beq own_link
        lwz r3, 0x34(r1)
        cmpw r3, r26                    # itself: the link instead
        bne own_next
own_link:
        lwz r12, 0x30(r1)               # 2. LinkModule ([acc + 0x68]) link 0: vt +0x5C(0) has it, vt +0x6C(0, 1) its id
        lwz r3, %(blink)d(r12)
        cmpwi r3, 0
        beq own_none
        lwz r12, 0(r3)
        lwz r12, 0x5C(r12)
        li r4, 0
        mtctr r12
        bctrl
        cmpwi r3, 0
        beq own_none
        lwz r12, 0x30(r1)
        lwz r3, %(blink)d(r12)
        lwz r12, 0(r3)
        lwz r12, 0x6C(r12)
        li r4, 0
        li r5, 1
        mtctr r12
        bctrl
        stw r3, 0x34(r1)
        bl ui_id_ok
        cmpwi r3, 0
        beq own_none
own_next:
        lwz r3, 0x34(r1)
        cmpw r3, r26                    # the same object again: a loop
        beq own_none
        mr r26, r3
        bl ui_dchain                    # (diag: the chain's ids; else a blr)
        rlwinm. r0, r26, 4, 28, 31      # a fighter (id >> 28 == 0): the one to answer
        beq have_id
        addi r24, r24, -1               # a weapon / item: its own owner next (at most %(depth)d steps)
        cmpwi r24, 0
        beq own_none
        lis r3, %(mgr_ha)d
        lwz r3, %(mgr_lo)d(r3)
        addi r4, r1, 0x18
        mr r5, r26
        li r6, 0""" + call('handle') + """
        addi r3, r1, 0x18""" + call('gone') + """
        cmpwi r3, 0
        beq own_step
own_none:
        b no_target
have_id:
        lis r3, %(mgr_ha)d
        lwz r3, %(mgr_lo)d(r3)
        addi r4, r1, 0x20
        mr r5, r26
        li r6, 0""" + call('handle') + """
        addi r3, r1, 0x20
        bl ui_side_of
        cmpwi r3, 0
        bne no_target
        lwz r11, 4(r29)                 # status floats: X / Y of the fighter to answer
        lfs f0, 0x28(r1)
        stfs f0, %(ftx)d(r11)
        lfs f0, 0x2C(r1)
        stfs f0, %(fty)d(r11)
        oris r25, r25, 4                # 0x21000012: found
no_target:
        lwz r11, 4(r29)
        lfs f0, 0xC(r30)
        stfs f0, %(fdmg)d(r11)          # 0x01000006 = the damage
        lfs f0, 0x10(r1)
        stfs f0, %(fside)d(r11)         # 0x01000007 = the side
        lwz r11, 0x14(r29)
        lwz r0, 0(r11)
        oris r0, r0, 1                  # 0x21000010
        or r0, r0, r25
        stw r0, 0(r11)
out42:  lmw r24, 0x40(r1)
        lwz r0, 0x64(r1)
        mtlr r0
        addi r1, r1, 0x60
        blr

# ui4: the AUTODODGE (r4 fighter, r5 message, r12 his module block; Wait / Walk / WalkBrake / Squat .. SquatRv).
# v1-v4 waited for slot 43, taking it for the body's damage event: it is event 0x12, the shield DAMAGE that follows a
# shield hit (the v4 log: slot 43 ran only right after slot 42, never for DK's punches on his body; the body hit is
# events 0xB / 0xC, 0x02E2AFBC / 0x02E2B59C, no specializer veto). So his MSC keeps the counter shape on in these
# statuses while transformed, and a hit on it here is the dodge: transformed (TIMER_0 > FORM_ON through his
# WorkModule's get_float), any object's hit (the shape blocks whatever reaches it: nothing is absorbed without a
# dodge), the side from the hitting object's place (Marth's side function when it is gone): TIMER_1 (it is to his
# right) or TIMER_2 = DODGE_SIGNAL, the other 0, through set_float. Nothing in the status work (a normal status's)
s42_dg: stwu r1, -0x60(r1)
        mflr r0
        stw r0, 0x64(r1)
        stmw r24, 0x40(r1)
        mr r31, r12                     # the module block
        mr r30, r5                      # message
        lwz r29, %(work)d(r31)          # his WorkModule
        mr r3, r29                      # transformed: TIMER_0 > FORM_ON
        lis r4, %(vform_hi)d
        ori r4, r4, %(vform_lo)d
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl%(d43_t0)s
        lis r12, ui_form@ha
        lfs f0, ui_form@l(r12)
        fcmpu cr0, f1, f0
        ble dg_out
        lwz r28, 0x10(r30)              # the collision record: +0x18 the object that hit him
        lis r3, %(mgr_ha)d
        lwz r3, %(mgr_lo)d(r3)
        addi r4, r1, 0x18
        lwz r5, 0x18(r28)
        li r6, 0""" + call('handle') + """
        addi r3, r1, 0x18
        bl ui_side_of                   # 0x10(r1) = +1.0: the object to his right
        cmpwi r3, 0
        beq dg_sig
        lwz r3, 8(r30)                  # gone: Marth's side (the attacker's AttackModule's hit data)
        lwz r12, 0(r3)
        lwz r12, 0x194(r12)
        lbz r4, 0x26(r28)
        lbz r5, 0x29(r28)
        mtctr r12
        bctrl
        lis r12, ui_one@ha
        lfs f1, ui_one@l(r12)
        mr. r27, r3
        beq dg_one
        lwz r3, %(sidemod)d(r31)
        lwz r4, 8(r30)
        mr r5, r27
        lbz r6, 0x26(r28)
        lbz r7, 0x29(r28)
        lfs f1, 0x18(r30)
        lfs f2, 0x1C(r30)""" + call('side') + """
dg_one: stfs f1, 0x10(r1)
dg_sig: lfs f1, 0x10(r1)
        li r26, %(vr_lo)d               # to his right: TIMER_1
        li r27, %(vl_lo)d
        lis r12, ui_zero@ha
        lfs f0, ui_zero@l(r12)
        fcmpu cr0, f1, f0
        bgt dg_set
        li r26, %(vl_lo)d               # to his left: TIMER_2
        li r27, %(vr_lo)d
dg_set:%(d43_sig)s
        mr r3, r29                      # set_float(WM, 4.0, the side's timer)
        lis r4, %(vform_hi)d
        or r4, r4, r26
        lis r12, ui_sig@ha
        lfs f1, ui_sig@l(r12)
        lwz r12, 0(r3)
        lwz r12, 0x4C(r12)
        mtctr r12
        bctrl
        mr r3, r29                      # the other side's timer 0
        lis r4, %(vform_hi)d
        or r4, r4, r27
        lis r12, ui_zero@ha
        lfs f1, ui_zero@l(r12)
        lwz r12, 0(r3)
        lwz r12, 0x4C(r12)
        mtctr r12
        bctrl
dg_out: lmw r24, 0x40(r1)
        lwz r0, 0x64(r1)
        mtlr r0
        addi r1, r1, 0x60
        blr

# ui_side_of(r3 &handle; r31 his module block; caller's frame at r1): 0 and 0x10(caller r1) = +-1.0 (the object to
# his right: +1), 0x28 / 0x2C(caller r1) its X / Y, when the object exists; else non-zero, nothing written.
# (r24-r31 kept; a leaf frame of its own)
ui_side_of:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r3, 0x8(r1)""" + call('gone') + """
        cmpwi r3, 0
        bne uso_out
        lwz r3, 0x8(r1)""" + call('pos') + """
        lfs f0, 0(r3)                   # its X
        lfs f12, 4(r3)                  # its Y
        stfs f0, 0x48(r1)               # caller's 0x28 / 0x2C (its r1 = ours + 0x20)
        stfs f12, 0x4C(r1)
        lwz r12, %(posture)d(r31)
        lfs f13, 0x10(r12)              # his X
        lis r12, ui_one@ha
        lfs f1, ui_one@l(r12)
        fcmpu cr0, f13, f0
        blt uso_set                     # he is left of it: +1.0
        fneg f1, f1
uso_set:
        stfs f1, 0x30(r1)               # caller's 0x10
        li r3, 0
uso_out:
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# ui_id_ok(r3 an object id): r3 non-zero when it is an object of category 0, 1, 2 or 4 (fighter, weapon, ui4: item 4;
# 2 kept): not none (0x50000000), not -1, not a stage gimmick (3). Leaf: r0, r3
ui_id_ok:
        cmpwi r3, -1
        beq uio_no
        lis r0, %(noobj_hi)d
        cmpw r3, r0
        beq uio_no
        rlwinm r0, r3, 4, 28, 31
        cmplwi r0, 3
        beq uio_no
        cmplwi r0, 4
        bgt uio_no
        li r3, 1
        blr
uio_no: li r3, 0
        blr

# v4: Mesh_Visibility Persist 2 (tools/mesh_vis_cave.py's mv_apply entered here first: r3 the mesh index, r27 the
# instance, r28 the accessor, r30 the parameters; r22-r31 kept for its caller): the mesh's OWN set state written through
# the game's setter 0x034232FC(MI, mesh, Visible, 0) (0 hidden, 1 shown, 2 follow the motion's visibility animation):
# no override entry, it lasts until written again (motion changes, KOs, training resets keep it; a visibility group
# writes the same state). An override of that mesh (Persist 0 / 1) keeps it aside (mesh_vis_cave's mv_set) and gives
# it back when it ends. Persist 0 / 1: mv_apply as before.
mvp2:   lwz r0, 0xC(r30)
        cmpwi r0, 2
        beq mvp2_go
        stwu r1, -0x20(r1)              # mv_apply's first word
        b 0x%(mv_back)08X
mvp2_go:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r3, 0x10(r1)
        lwz r12, %(va)d(r27)            # the byte before (diag)
        lwz r12, 4(r12)
        lbzx r0, r12, r3
        stw r0, 0x14(r1)
        mr r4, r3
        mr r3, r27
        lwz r5, 8(r30)                  # Visible: 0 / 1 / 2
        cmplwi r5, 2
        ble mvp2_v
        li r5, 2
mvp2_v: li r6, 0""" + call('setvis') + """
        lwz r3, 0x10(r1)
        lwz r4, 0x14(r1)
        bl ui_dmv                       # (diag: S4UV; else a blr)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# ---- 3. slot 43 (r3 spec, r4 fighter, r5 message) -> 0: no damage / knockback / reaction
slot43: li r3, 1
        lwz r12, %(kind_at)d(r4)
        cmpwi r12, %(kind)d
        bnelr
        lwz r12, %(acc)d(r4)
        lwz r11, %(st)d(r12)
        lwz r11, 0x48(r11)
        cmpwi r11, %(st_ss)d
        bne s43_dodge
        lwz r11, %(work)d(r12)          # Secret Sensation answering (0x21000010): no damage
        lwz r11, 8(r11)
        lwz r11, 4(r11)
        lwz r11, 0x14(r11)
        lwz r11, 0(r11)
        rlwinm. r11, r11, 0, 15, 15
        bne handled
        stwu r1, -0x20(r1)              # v5: the transformation / its strike (TIMER_4 > MODE_FORM_ON): fully invincible
        mflr r0
        stw r0, 0x24(r1)
        stw r5, 0x10(r1)
        lwz r3, %(work)d(r12)
        bl ui_mode4                     # v7: the transformation (2) or the sway family (1: no shield damage) -> 0
        lwz r5, 0x10(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        cmpwi r3, 0
        bne handled
        li r3, 1
        blr
s43_dodge:                              # ui4: the autododge's statuses (the shape on while transformed): the shield
        cmpwi r11, %(escn)d             # (v7: and his spot dodge)
        beq s43_go
        cmplwi r11, %(dhi)d             # damage that follows the shape's hit skipped (no guard damage / stun)
        ble s43_go                      # Wait, Walk, WalkBrake
        cmpwi r11, %(otlo)d             # v12: Ottotto / OttottoWait
        blt s43_sq
        cmpwi r11, %(othi)d
        ble s43_go
        blr
s43_sq: cmpwi r11, %(sqlo)d
        bltlr
        cmpwi r11, %(sqhi)d
        bgtlr                           # Squat .. SquatRv
s43_go: stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r5, 0x10(r1)
        lwz r3, %(work)d(r12)           # transformed: TIMER_0 > FORM_ON
        lis r4, %(vform_hi)d
        ori r4, r4, %(vform_lo)d
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl%(d43_t0)s
        lwz r5, 0x10(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        lis r12, ui_form@ha
        lfs f0, ui_form@l(r12)
        li r3, 1
        fcmpu cr0, f1, f0
        bgt handled
        blr

handled:
        lbz r0, 8(r5)
        ori r0, r0, 1
        stb r0, 8(r5)
        li r3, 0
        blr

# ---- v10 (exe_v46z_ui7) 8. ui_sx: the shield-hit mark (SX_HOOK: the EffectModule's event-0x10 listener 0x02C2CD28,
# r3 the EffectModule, r4 the message): not for HIS counter shape (group 1, the EffectModule a live kind-0x41
# fighter's: the fighter table's entries, module block + EFFM). Leaf: r0, r10-r12
ui_sx:  lwz r0, 0x14(r4)
        cmpwi r0, %(group)d
        bne sx_go
        lis r12, %(fts_ha)d
        lwz r12, %(fts_lo)d(r12)
        cmpwi r12, 0
        beq sx_go
        lwz r12, 0(r12)
        cmpwi r12, 0
        beq sx_go
        lwz r11, 8(r12)                 # the count
        lwz r12, 0(r12)                 # the entries
        cmpwi r12, 0
        beq sx_go
        cmplwi r11, %(maxf)d
        bgt sx_go
sx_loop:
        cmpwi r11, 0
        beq sx_go
        lbz r0, 0x1E(r12)               # live
        cmplwi r0, 4
        blt sx_next
        lwz r0, %(kind_at)d(r12)
        cmpwi r0, %(kind)d
        bne sx_next
        lwz r10, %(acc)d(r12)
        cmpwi r10, 0
        beq sx_next
        lwz r10, %(effm)d(r10)          # his EffectModule
        cmpw r10, r3
        beqlr                           # his counter shape: no mark
sx_next:
        addi r12, r12, %(entry)d
        addi r11, r11, -1
        b sx_loop
sx_go:  mflr r0                         # the replaced word
        b 0x%(sx_back)08X

# ---- v10 9. the world stop. ws_data: +0 the lease (frames left), +4 its owner (his fighter), +8 the instances paused
# (v12: none), +0xC (v10-v11: the list of them) v13: the mode (0 the world stopped, 1 the stage only: an ask over 4.5)
# ws_fill (FILL_HOOK: the frame state fill, r3 the frame state): the game's fill, then while the lease lasts a slowed
# frame between two steps (+8 1, +0 1, answer 0): no object steps; the last frame of the lease ends the stop
ws_fill:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r30, 0x18(r1)
        stw r31, 0x1C(r1)
        mr r31, r3
        bl wsf_orig
        mr r30, r3
        lis r12, ws_data@ha
        addi r12, r12, ws_data@l
        lwz r11, 0(r12)
        cmpwi r11, 0
        beq wsf_out
        addi r11, r11, -1               # (addi from r0 would be li)
        stw r11, 0(r12)
        cmpwi r11, 0
        bne wsf_stop
        bl ws_end
        b wsf_out
wsf_stop:
        lwz r0, 0xC(r12)                # v13: the stage-only stop (ws_data + 0xC 1): the frame as the game made it
        cmpwi r0, 0
        bne wsf_out
        li r0, 1
        stb r0, 8(r31)
        stw r0, 0(r31)
        li r30, 0
wsf_out:
        mr r3, r30
        lwz r30, 0x18(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
wsf_orig:
        mflr r0                         # the replaced word
        b 0x%(fill_back)08X

# ws_step (STEP_HOOK: the fighter's step wrapper, r3 the fighter, r4 its module block): another kind as before; his
# ask (TIMER_6 > 0.5) starts the stop / renews its lease; while it is his stop, his step on a normal frame
ws_step:
        lwz r0, %(kind_at)d(r3)
        cmpwi r0, %(kind)d
        beq wss_him
wss_orig:
        mflr r0                         # the replaced word
        b 0x%(step_back)08X
wss_him:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stw r3, 0x10(r1)
        stw r4, 0x14(r1)
        stw r30, 0x28(r1)
        stw r31, 0x2C(r1)
        mr r31, r3
        lwz r12, %(acc)d(r3)
        lwz r3, %(work)d(r12)
        lis r4, %(vstop_hi)d
        ori r4, r4, %(vstop_lo)d
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl                           # get_float(TIMER_6)
        lis r30, ws_data@ha
        addi r30, r30, ws_data@l
        lis r12, ws_half@ha
        lfs f0, ws_half@l(r12)
        fcmpu cr0, f1, f0
        ble wss_go
        lwz r0, 0(r30)
        cmpwi r0, 0
        bne wss_lease
        lis r12, ws_stagef@ha           # v13: an ask above 4.5 (the transformation counter's) stops the stage only
        lfs f0, ws_stagef@l(r12)        # (the objects step: its hits land; his MSC freezes the others itself)
        li r0, 0
        fcmpu cr0, f1, f0
        ble wss_mode
        li r0, 1
wss_mode:
        stw r0, 0xC(r30)
        stw r31, 4(r30)
        mr r3, r31
        bl ws_begin
wss_lease:
        li r0, %(lease)d
        stw r0, 0(r30)
        stw r31, 4(r30)
wss_go: lwz r0, 0(r30)
        cmpwi r0, 0
        beq wss_plain
        lwz r0, 4(r30)
        cmpw r0, r31
        bne wss_plain
        lwz r0, 0xC(r30)                # v13: the stage-only stop: his step as any
        cmpwi r0, 0
        bne wss_plain
        lis r12, %(fs_ha)d
        lwz r30, %(fs_lo)d(r12)         # the frame state
        lbz r0, 8(r30)
        stw r0, 0x18(r1)
        lwz r0, 0(r30)
        stw r0, 0x1C(r1)
        li r0, 0
        stb r0, 8(r30)                  # his step: a normal frame
        lwz r3, 0x10(r1)
        lwz r4, 0x14(r1)
        bl wss_orig
        lwz r0, 0x18(r1)
        stb r0, 8(r30)
        lwz r0, 0x1C(r1)
        stw r0, 0(r30)
        b wss_out
wss_plain:
        lwz r3, 0x10(r1)
        lwz r4, 0x14(r1)
        bl wss_orig
        b wss_out
wss_out:
        lwz r30, 0x28(r1)
        lwz r31, 0x2C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# ws_begin(r3 his fighter): every effect instance not his, not paused and not kept out of pauses paused and noted; the
# stage stopped
ws_begin:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r29, 0x14(r1)
        stw r30, 0x18(r1)
        stw r31, 0x1C(r1)
        mr r29, r3
        lwz r12, %(acc)d(r3)
        lwz r12, %(effm)d(r12)          # his EffectModule's pause key
        li r31, -1
        cmpwi r12, 0
        beq wsb_key
        lwz r31, 0x10(r12)
        ori r31, r31, 0x8000
wsb_key:
        lis r30, ws_data@ha
        addi r30, r30, ws_data@l
        li r0, 0
        stw r0, 8(r30)
        b wsb_stage                     # v12: no effect instance paused (v10-v11's sweep paused every instance not
                                        # his, the stage's too: its emitter sets then ran at rate 0 (0x0334E238) and
                                        # the screen went white, the user's v11 clip b); the stage stop is the Final
                                        # Smashes' and handles the stage's own
wsb_stage:
        li r4, 1
        bl ws_stage
        li r4, 1
        mr r5, r29
        lwz r6, 0xC(r30)                # v13: the mode (diag: S4UW's third number)
        lis r7, %(stg_ha)d
        lwz r7, %(stg_lo)d(r7)
        bl ui_dws
        lwz r29, 0x14(r1)
        lwz r30, 0x18(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# ws_end: the instances ws_begin paused go on; the stage goes on; the stop's state cleared
ws_end: stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r30, 0x18(r1)
        stw r31, 0x1C(r1)
        lis r30, ws_data@ha
        addi r30, r30, ws_data@l
        lwz r11, 8(r30)
        cmplwi r11, %(wsmax)d
        ble wse_n
        li r11, %(wsmax)d
wse_n:  addi r12, r30, 0xC
        li r0, 0
wse_loop:
        cmpwi r11, 0
        beq wse_done
        lwz r10, 0(r12)
        stb r0, 0x19E(r10)
        addi r12, r12, 4
        addi r11, r11, -1
        b wse_loop
wse_done:
        lwz r31, 8(r30)
        lwz r5, 4(r30)
        li r0, 0
        stw r0, 0xC(r30)                # v13: the mode
        stw r0, 0(r30)
        stw r0, 4(r30)
        stw r0, 8(r30)
        stw r5, 0x10(r1)
        li r4, 0
        bl ws_stage
        li r4, 0
        lwz r5, 0x10(r1)
        mr r6, r31
        lis r7, %(stg_ha)d
        lwz r7, %(stg_lo)d(r7)
        bl ui_dws
        lwz r30, 0x18(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# ws_stage(r4 on): the stage stopped / on, as the Final Smashes do (0x0316505C(manager, on), skipped while [[STAGE_FLAGS]
# + 0xB3] or without a manager)
ws_stage:
        lis r3, %(stg_ha)d
        lwz r3, %(stg_lo)d(r3)
        cmpwi r3, 0
        beqlr
        lis r12, %(stgf_ha)d
        lwz r12, %(stgf_lo)d(r12)
        cmpwi r12, 0
        beq wst_go
        lbz r0, 0xB3(r12)
        cmpwi r0, 0
        bnelr
wst_go: lwz r0, 0(r3)                   # v13: a stage loaded: its update skipped (+0xD0) and nothing told (v10-v12 the
        cmpwi r0, 0                     # Final Smashes' full stop 0x0316505C, whose 0x031427D0 whites the screen out:
        beqlr                           # Stage_Freeze On 1 / 2 in game, docs/acmd-extra-commands.md)
        stb r4, 0xD0(r3)
        blr

# ui_isform(r3 his WorkModule): r3 1 when TIMER_4 (status 0x155's mode, his MSC's) > MODE_FORM_ON, the transformation /
# its counter; else 0. Its own frame (get_float vt +0x44: the volatile registers go)
ui_isform:
        stwu r1, -0x10(r1)
        mflr r0
        stw r0, 0x14(r1)
        lis r4, %(vmode_hi)d
        ori r4, r4, %(vmode_lo)d
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl
        lis r12, ui_modef@ha
        lfs f0, ui_modef@l(r12)
        li r3, 0
        fcmpu cr0, f1, f0
        ble isf_out
        li r3, 1
isf_out:
        lwz r0, 0x14(r1)
        mtlr r0
        addi r1, r1, 0x10
        blr

# v7: ui_mode4(r3 his WorkModule): r3 2 when TIMER_4 > MODE_FORM_ON (the transformation / its counter), 1 when >
# MODE_SWAY_ON (the autododge, its counter), else 0 (Secret Sensation 3, Fake Death / Sledgehammer 0). Its own frame
ui_mode4:
        stwu r1, -0x10(r1)
        mflr r0
        stw r0, 0x14(r1)
        lis r4, %(vmode_hi)d
        ori r4, r4, %(vmode_lo)d
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl
        li r3, 2
        lis r12, ui_modef@ha
        lfs f0, ui_modef@l(r12)
        fcmpu cr0, f1, f0
        bgt m4_out
        li r3, 1
        lis r12, ui_swayf@ha
        lfs f0, ui_swayf@l(r12)
        fcmpu cr0, f1, f0
        bgt m4_out
        li r3, 0
m4_out: lwz r0, 0x14(r1)
        mtlr r0
        addi r1, r1, 0x10
        blr

# v7: the projectile filter (bl from 0x02C0F7F0 in the collision pair pass 0x02C0F6F0, for every pair of entries the
# pass tests: r3 A's container, r4 A's entry, r5 B's entry, the pass's r31 B's container; the per-entry check
# 0x02C0F2E8 -> 0: they don't meet). After the game's check: A is HIS counter shape (A's object a fighter of kind 0x41,
# A his ShieldModule's container (M + 0x18), r4 its group 1's collision object ([M + 0x24] + [[M + 8] + 0x34] x 0x174))
# and B's object is not a fighter (B +0x1C, its id >> 28: a weapon 1, an item 4, a gimmick 3 ...) -> 0, except in status
# 0x155 below the sway family (Secret Sensation answers anything an opponent owns). A fighter's own attack (category
# 0), every other shield (his guard bubble, group 0; other fighters') and every other pair: the game's answer
ui_pf:  stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r27, 0x2C(r1)
        mr r29, r3                      # A's container
        mr r28, r4                      # A's entry
        lis r12, %(pff_hi)d
        ori r12, r12, %(pff_lo)d
        mtctr r12
        bctrl                           # the game's check
        mr. r27, r3
        beq pf_out
        lbz r0, 0x1C(r31)               # B's object category: a fighter's own attack goes on as before
        cmpwi r0, 0
        beq pf_out
        lwz r5, 0x18(r29)               # A's object: a fighter (category 0)
        rlwinm. r0, r5, 4, 28, 31
        bne pf_out
        lis r3, %(mgr_ha)d
        lwz r3, %(mgr_lo)d(r3)
        addi r4, r1, 0x10
        li r6, 0
        lis r12, %(handle_hi)d
        ori r12, r12, %(handle_lo)d
        mtctr r12
        bctrl
        addi r3, r1, 0x10
        lis r12, %(gone_hi)d
        ori r12, r12, %(gone_lo)d
        mtctr r12
        bctrl
        cmpwi r3, 0
        bne pf_out
        lwz r12, 0x10(r1)               # [handle]: the fighter's entry
        lwz r0, %(kind_at)d(r12)
        cmpwi r0, %(kind)d
        bne pf_out
        lwz r30, %(acc)d(r12)           # his module block
        lwz r11, %(shield)d(r30)        # his ShieldModule
        cmpwi r11, 0
        beq pf_out
        addi r0, r11, 0x18              # its container
        cmpw r0, r29
        bne pf_out
        lwz r10, 8(r11)                 # group 1 (+0x34): its first collision object's index (+0)
        lwz r10, 0x34(r10)
        mulli r10, r10, 0x174
        lwz r9, 0xC(r29)
        add r9, r9, r10
        cmpw r9, r28
        bne pf_out                      # his guard bubble (group 0): as before
        lwz r11, %(st)d(r30)
        lwz r11, 0x48(r11)
        cmpwi r11, %(st_ss)d
        bne pf_drop
        lwz r3, %(work)d(r30)
        bl ui_mode4
        cmpwi r3, 0
        beq pf_out                      # Secret Sensation (or Fake Death / Sledgehammer: the shape is off there)
pf_drop:
        li r27, 0%(dpf)s
pf_out: mr r3, r27
        lmw r27, 0x2C(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr
""" + (DIAG_TAIL if diag else RELEASE_TAIL)) % p)
    if diag:
        import zlib
        a.asm('ui_drec:' + '\n        .word 0' * 16)
        a.asm('ui_dmots:' + ''.join('\n        .word 0x%X' % m for m in DIAG_MOTIONS) + '\n        .word -1')
        a.asm('ui_dhash:' + ''.join('\n        .word 0x%08X' % (zlib.crc32(h.encode()) & 0xFFFFFFFF)
                                    for h in DIAG_HASHES) + '\n        .word 0')
        for lab, text in DIAG_FMTS:
            a.asm('ui_%s:' % lab + fmt_words(text))
    shape_at = a.pc + 4 * 4
    a.asm("""
ui_one: .float 1.0
ui_form: .float %(form)r
ui_sig: .float %(sig)r
ui_zero: .float 0.0
ui_shape:
        .float %(x1)r
        .float %(y1)r
        .float %(z1)r
        .float %(x2)r
        .float %(y2)r
        .float %(z2)r
        .float %(radius)r
        .word 0x%(bonetype)08X
ui_desc:
        .word 0x%(shape_at)08X
        .word 1
        .word 0x%(descbytes)08X
ui_modef: .float %(modef)r
ui_swayf: .float %(swayf)r
ws_half: .float 0.5
ws_stagef: .float %(stagef)r
ws_data:
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
""" % dict(form=FORM_ON, modef=MODE_FORM_ON, swayf=MODE_SWAY_ON, sig=DODGE_SIGNAL, stagef=WS_STAGE_ONLY, x1=SHAPE['p1'][0], y1=SHAPE['p1'][1], z1=SHAPE['p1'][2],
           x2=SHAPE['p2'][0], y2=SHAPE['p2'][1], z2=SHAPE['p2'][2], radius=SHAPE['radius'],
           bonetype=(SHAPE['bone'] << 16) | (SHAPE_TYPE << 8), shape_at=shape_at,
           descbytes=int.from_bytes(bytes(DESC_BYTES), 'big')))
    assert a.labels['ui_shape'] == shape_at
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, 'cave too long'
    return words, dict(a.labels)


def branch(src, dst):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0, (hex(src), hex(dst))
    return (18 << 26) | (off & 0x3FFFFFC)


def patches(kind_id=None, diag=False):
    """{address: word}: the cave and its hooks (Mario's slots 0 / 42 / 43, mesh_vis_cave's mv_apply; diag: the
    lookup / bind hooks, slots 42 / 43 through their line wrappers)"""
    words, labels = build(kind_id, diag)
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    hooks = [(SETUP_HOOK, 'setup'), (SLOT42_HOOK, 'ui_d42w' if diag else 'slot42'),
             (SLOT43_HOOK, 'ui_d43w' if diag else 'slot43'), (MV_APPLY, 'mvp2')]
    if diag:
        hooks.append((MHASH_HOOK, 'ui_dmh'))
    for hook, label in hooks:
        out[hook] = branch(hook, labels[label])
    if diag:
        out[BIND_HOOK] = branch(BIND_HOOK, labels['ui_dbind']) | 1
        out[LATE_HOOK] = branch(LATE_HOOK, labels['ui_dlate']) | 1
        out[EFT_PRINT] = branch(EFT_PRINT, labels['ui_deft'])
    out[WALK_FIX] = NOP                 # ui4: Mesh_Visibility's name walk takes unaligned names
    out[PF_HOOK] = branch(PF_HOOK, labels['ui_pf']) | 1      # v7: the projectile filter
    out[SX_HOOK] = branch(SX_HOOK, labels['ui_sx'])          # v10: no shield-hit mark on his counter shape
    out[FILL_HOOK] = branch(FILL_HOOK, labels['ws_fill'])    # v10: the world stop
    out[STEP_HOOK] = branch(STEP_HOOK, labels['ws_step'])
    return out


def word_or_0(img, a):
    try:
        return img.w(a)
    except KeyError:
        return 0


def check_base(rpx):
    """the hooks' words in the base are the game's (or this cave's own branches: re-applying); the space is free"""
    import kind_expand as K
    img = K.Image(rpx)
    p = patches(diag=True)
    want = dict(ORIGINAL)
    want.update(DIAG_ORIGINAL)
    want.update({MV_APPLY + 4 * i: w for i, w in enumerate(MV_APPLY_WORDS)})
    want.update(WALK_WORDS)
    bad = ['0x%08X: 0x%08X' % (a, img.w(a)) for a, w in want.items() if img.w(a) not in (w, p.get(a, w))]
    bad += ['veneer 0x%08X' % (OSREPORT_VENEER + 4 * i) for i, w in enumerate(VENEER_WORDS)
            if w is not None and img.w(OSREPORT_VENEER + 4 * i) != w]
    if bad:
        raise SystemExit('supamario_ui_cave: unexpected words in %s: %s' % (rpx, ', '.join(bad)))
    for s, hook in ((0, SETUP_HOOK), (42, SLOT42_HOOK), (43, SLOT43_HOOK)):
        if img.w(MARIO_VT + 0xC + 8 * s) != hook:
            raise SystemExit('supamario_ui_cave: Mario\'s vtable slot %d is not 0x%08X in %s' % (s, hook, rpx))
    used = [a for a in range(CAVE, LIMIT, 4) if word_or_0(img, a) not in (0, p.get(a, 0), patches().get(a, 0))]
    if used:
        raise SystemExit('supamario_ui_cave: the cave space is in use in %s (0x%08X)' % (rpx, used[0]))


def args(kind_id=None, diag=False):
    return ['textregion:0x%X' % TEXT_REGION, 'grow:0x%08X' % LIMIT] + \
        ['0x%08X=0x%08X' % (a, w) for a, w in sorted(patches(kind_id, diag).items())]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', help='check the hooks\' original words and the cave space in this base')
    ap.add_argument('--kinds', default=SPEC)
    ap.add_argument('--diag', action='store_true', help='TEST ONLY: the OSReport build (S4U2 / S4U5 / S4U3 / S4UV / '
                    'S4UM / S4UB lines)')
    a = ap.parse_args()
    if a.rpx:
        check_base(a.rpx)
    k = kind(a.kinds)
    words, labels = build(k, a.diag)
    print(' '.join(args(k, a.diag)))
    sys.stderr.write('supamario ui: kind 0x%X, cave 0x%08X-0x%08X (%d words), hooks 0x%08X / 0x%08X / 0x%08X\n'
                     % (k, CAVE, CAVE + 4 * len(words), len(words), SETUP_HOOK, SLOT42_HOOK, SLOT43_HOOK))


if __name__ == '__main__':
    main()
