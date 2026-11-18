#!/usr/bin/env python3
"""Supamario's Ultra Instinct (fighters/supamario/README.md "Ultra Instinct v1"): the native part. Supamario (kind
0x41, extra_kinds.json "supamario") runs Mario's native code (specializer vtable 0x10139E60), which has no counter. For
kind 0x41 ONLY (the fighter's kind [fighter + 4]; Mario, kind 3, and every other kind run the game's words as before)
this adds:

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
LIMIT = 0x04BE9000
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
            SLOT43_HOOK + 4: 0x4E800020}

# game functions (none is an import)
GROUP_INIT = 0x0200C858          # ShieldModule: (M, desc, group)
GROUP_STATE = 0x0200BD8C         # ShieldModule vt +0x6C: (M, shape, on, group)
SIDE = 0x02C22684                # Marth's side: (module [acc+0x7290], attacker AM, hit data, id, part, f1, f2) -> f1
HANDLE = 0x02BF2108              # (manager [0x102F6C30], &handle, object id, 0)
HANDLE_GONE = 0x02BEF50C         # (&handle) -> 0 while the object exists
HANDLE_POS = 0x02BEF640          # (&handle) -> its position (x +0, y +4)
OBJ_MANAGER = 0x102F6C30
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
BASE_OWNER = 0x6C                # a base accessor's owner module (+0x34 the current owner's id)
NO_OBJECT = 0x50000000

GROUP = 1
ST_UI = 0x157                    # the transformation / counter status (Mario's F.L.U.D.D. shoot, unreachable)
ST_DODGE = 0x158                 # the dodge status (MSC's own; nothing here)
ST_SS = 0x155                    # the down special: Secret Sensation while transformed (its MSC switches the shape)
DODGE_LO, DODGE_HI = 0x0, 0x2    # Wait, Walk, WalkBrake
SQUAT_LO, SQUAT_HI = 0x11, 0x15  # Squat, SquatWait, SquatF, SquatB, SquatRv
# status work: floats 6-9, flags word 0 bits 16-18
F_DAMAGE, F_SIDE, F_TX, F_TY = 6, 7, 8, 9
FLAG_HIT, FLAG_NOTFIGHTER, FLAG_FOUND = 0x21000010, 0x21000011, 0x21000012
# the user variables (docs/acmd-extra-commands.md: TIMER_0-15; unused by every earlier Supamario script and his MSC)
V_FORM = 0x0F000320              # TIMER_0: his MSC writes 0 / 1000 (transforming) / 2000 (transformed) every frame
V_DODGE_R = 0x0F000321           # TIMER_1: a dodge asked, the attacker to his right
V_DODGE_L = 0x0F000322           # TIMER_2: ... to his left
FORM_ON = 1500.0                 # transformed: TIMER_0 above this
DODGE_SIGNAL = 4.0               # the timers count down by themselves: a signal the MSC missed dies in 4 frames
MAX_FIGHTERS, MAX_PARTS, MAX_NODES = 16, 16, 32

# the shape: x sideways, y up, z forward (joint 0's frame); a capsule round his body
SHAPE = {'bone': 0, 'p1': (0.0, 2.5, 0.0), 'p2': (0.0, 9.5, 0.0), 'radius': 6.5}
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


def build(kind_id=None):
    """(words, labels): the cave from CAVE"""
    if kind_id is None:
        kind_id = kind()
    a = Asm(CAVE)
    calls = {}
    for n, v in (('init', GROUP_INIT), ('state', GROUP_STATE), ('side', SIDE), ('handle', HANDLE),
                 ('gone', HANDLE_GONE), ('pos', HANDLE_POS)):
        calls[n + '_hi'], calls[n + '_lo'] = hilo(v)
    p = dict(kind=kind_id, acc=ACC, kind_at=KIND_AT, shield=SHIELD, st=STATUS_MOD, work=WORK, posture=POSTURE,
             sidemod=SIDE_MOD, group=GROUP, st_ui=ST_UI, st_ss=ST_SS, back=SETUP_BODY, fdmg=4 * F_DAMAGE, fside=4 * F_SIDE,
             ftx=4 * F_TX, fty=4 * F_TY, mgr_ha=ha(OBJ_MANAGER), mgr_lo=slo(OBJ_MANAGER), fts_ha=ha(FIGHTERS),
             fts_lo=slo(FIGHTERS), entry=FIGHTER_ENTRY, bpost=BASE_POSTURE, batk=BASE_ATTACK, bown=BASE_OWNER,
             noobj_hi=NO_OBJECT >> 16, dlo=DODGE_LO, dhi=DODGE_HI, sqlo=SQUAT_LO, sqhi=SQUAT_HI,
             vform_hi=V_FORM >> 16, vform_lo=V_FORM & 0xFFFF, vr_lo=V_DODGE_R & 0xFFFF, vl_lo=V_DODGE_L & 0xFFFF,
             maxf=MAX_FIGHTERS, maxp=MAX_PARTS, maxn=MAX_NODES, **calls)
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
        lwz r11, 0x48(r11)              # status kind: the transformation or Secret Sensation (the down special)
        cmpwi r11, %(st_ui)d
        beq s42_st
        cmpwi r11, %(st_ss)d
        bnelr
s42_st: lwz r11, %(work)d(r12)
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
        lbz r0, 0x1C(r28)               # the attacker's category: 0 fighter, 1 weapon, 2 item, 3 gimmick
        cmplwi r0, 3                    # Secret Sensation: anything an opponent owns (0-2), never a gimmick
        bge out42
        lwz r12, %(st)d(r31)
        lwz r12, 0x48(r12)
        cmpwi r12, %(st_ui)d            # the transformation: XV2's CounterMelee only (a fighter's own attack)
        bne s42_cat
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
        lwz r12, 0x18(r1)               # [handle] = the object's entry: +0xC its accessor
        lwz r12, 0xC(r12)
        cmpwi r12, 0
        beq no_target
        lwz r12, %(bown)d(r12)          # the owner module
        cmpwi r12, 0
        beq no_target
        lwz r26, 0x34(r12)              # the current owner's id (a reflector after a reflect)
        rlwinm. r0, r26, 4, 28, 31      # a fighter: id >> 28 == 0
        bne no_target
        lis r0, %(noobj_hi)d
        cmpw r26, r0
        beq no_target
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

# ---- 3. slot 43 (r3 spec, r4 fighter, r5 message) -> 0: no damage / knockback / reaction
slot43: li r3, 1
        lwz r12, %(kind_at)d(r4)
        cmpwi r12, %(kind)d
        bnelr
        lwz r12, %(acc)d(r4)
        lwz r11, %(st)d(r12)
        lwz r11, 0x48(r11)
        cmpwi r11, %(st_ui)d
        beq handled                     # the transformation / its strike: fully invincible
        cmpwi r11, %(st_ss)d
        bne s43_dodge
        lwz r11, %(work)d(r12)          # Secret Sensation answering (0x21000010): no damage
        lwz r11, 8(r11)
        lwz r11, 4(r11)
        lwz r11, 0x14(r11)
        lwz r11, 0(r11)
        rlwinm. r11, r11, 0, 15, 15
        bne handled
        blr
s43_dodge:
        cmplwi r11, %(dhi)d
        ble s43_go                      # Wait, Walk, WalkBrake
        cmpwi r11, %(sqlo)d
        bltlr
        cmpwi r11, %(sqhi)d
        bgtlr                           # Squat .. SquatRv
s43_go: stwu r1, -0x70(r1)
        mflr r0
        stw r0, 0x74(r1)
        stmw r17, 0x2C(r1)
        mr r31, r12                     # the module block
        mr r30, r5                      # message
        lwz r29, %(work)d(r12)          # his WorkModule
        lwz r28, 0(r4)                  # his object id
        mr r3, r29                      # transformed: TIMER_0 > FORM_ON
        lis r4, %(vform_hi)d
        ori r4, r4, %(vform_lo)d
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl
        lis r12, ui_form@ha
        lfs f0, ui_form@l(r12)
        fcmpu cr0, f1, f0
        ble s43_no
        # a fighter whose hit records hold him
        lis r12, %(fts_ha)d
        lwz r12, %(fts_lo)d(r12)
        cmpwi r12, 0
        beq s43_no
        lwz r12, 0(r12)
        cmpwi r12, 0
        beq s43_no
        lwz r27, 0(r12)                 # entries
        lwz r26, 8(r12)                 # count
        cmpwi r27, 0
        beq s43_no
        cmplwi r26, %(maxf)d
        ble s43_cnt
        li r26, %(maxf)d
s43_cnt:
        li r25, 0                       # entry index
s43_floop:
        cmpw r25, r26
        bge s43_no
        mulli r24, r25, %(entry)d
        add r24, r27, r24               # the entry
        addi r25, r25, 1
        lbz r0, 0x1E(r24)
        cmplwi r0, 4
        blt s43_floop                   # not live
        lwz r0, 0(r24)
        cmpw r0, r28
        beq s43_floop                   # himself
        lwz r23, 0xC(r24)               # its accessor
        cmpwi r23, 0
        beq s43_floop
        lwz r22, %(batk)d(r23)          # its AttackModule
        cmpwi r22, 0
        beq s43_floop
        lwz r0, 0x4C(r22)               # records on
        cmpwi r0, 0
        beq s43_floop
        lwz r21, 0x18(r22)              # parts in use
        cmplwi r21, %(maxp)d
        ble s43_pn
        li r21, %(maxp)d
s43_pn: lwz r20, 0x14(r22)              # the per-part collision groups
        cmpwi r20, 0
        beq s43_floop
        li r19, 0                       # part
s43_ploop:
        cmpw r19, r21
        bge s43_floop
        mulli r18, r19, 0x174
        add r18, r20, r18
        addi r17, r18, 0x124            # the sentinel
        lwz r18, 0x128(r18)             # the first node
        li r0, %(maxn)d
        mtctr r0
s43_nloop:
        cmpwi r18, 0
        beq s43_pnext
        cmpw r18, r17
        beq s43_pnext
        lwz r0, 0x18(r18)               # the object it hit
        cmpw r0, r28
        beq s43_found
        lwz r18, 4(r18)
        bdnz s43_nloop
s43_pnext:
        addi r19, r19, 1
        b s43_ploop
s43_found:
        mr r3, r22                      # its hit data: vt +0x194(id, part)
        lwz r12, 0(r3)
        lwz r12, 0x194(r12)
        lbz r4, 0x27(r18)
        mr r5, r19
        mtctr r12
        bctrl
        cmpwi r3, 0
        beq s43_side
        lbz r0, 0x54(r3)
        cmpwi r0, 0
        bne s43_no                      # can't be countered: no dodge
s43_side:
        lwz r3, %(bpost)d(r23)          # its place: [acc + 0x18] vt +0x44 -> the position
        cmpwi r3, 0
        beq s43_no
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl
        lfs f0, 0(r3)                   # its X
        lwz r12, %(posture)d(r31)
        lfs f13, 0x10(r12)              # his X
        li r26, %(vr_lo)d               # to his right: TIMER_1
        li r27, %(vl_lo)d
        fcmpu cr0, f13, f0
        blt s43_sig
        li r26, %(vl_lo)d               # to his left: TIMER_2
        li r27, %(vr_lo)d
s43_sig:
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
        lbz r0, 8(r30)                  # the handled bit
        ori r0, r0, 1
        stb r0, 8(r30)
        li r3, 0
        b s43_out
s43_no: li r3, 1
s43_out:
        lmw r17, 0x2C(r1)
        lwz r0, 0x74(r1)
        mtlr r0
        addi r1, r1, 0x70
        blr

handled:
        lbz r0, 8(r5)
        ori r0, r0, 1
        stb r0, 8(r5)
        li r3, 0
        blr
""") % p)
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
""" % dict(form=FORM_ON, sig=DODGE_SIGNAL, x1=SHAPE['p1'][0], y1=SHAPE['p1'][1], z1=SHAPE['p1'][2],
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


def patches(kind_id=None):
    """{address: word}: the cave and the three hooks"""
    words, labels = build(kind_id)
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    for hook, label in ((SETUP_HOOK, 'setup'), (SLOT42_HOOK, 'slot42'), (SLOT43_HOOK, 'slot43')):
        out[hook] = branch(hook, labels[label])
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
    p = patches()
    bad = ['0x%08X: 0x%08X' % (a, img.w(a)) for a, w in ORIGINAL.items() if img.w(a) not in (w, p.get(a, w))]
    if bad:
        raise SystemExit('supamario_ui_cave: unexpected words in %s: %s' % (rpx, ', '.join(bad)))
    for s, hook in ((0, SETUP_HOOK), (42, SLOT42_HOOK), (43, SLOT43_HOOK)):
        if img.w(MARIO_VT + 0xC + 8 * s) != hook:
            raise SystemExit('supamario_ui_cave: Mario\'s vtable slot %d is not 0x%08X in %s' % (s, hook, rpx))
    used = [a for a in range(CAVE, LIMIT, 4) if word_or_0(img, a) not in (0, p.get(a, 0))]
    if used:
        raise SystemExit('supamario_ui_cave: the cave space is in use in %s (0x%08X)' % (rpx, used[0]))


def args(kind_id=None):
    return ['textregion:0x%X' % TEXT_REGION, 'grow:0x%08X' % LIMIT] + \
        ['0x%08X=0x%08X' % (a, w) for a, w in sorted(patches(kind_id).items())]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', help='check the hooks\' original words and the cave space in this base')
    ap.add_argument('--kinds', default=SPEC)
    a = ap.parse_args()
    if a.rpx:
        check_base(a.rpx)
    k = kind(a.kinds)
    words, labels = build(k)
    print(' '.join(args(k)))
    sys.stderr.write('supamario ui: kind 0x%X, cave 0x%08X-0x%08X (%d words), hooks 0x%08X / 0x%08X / 0x%08X\n'
                     % (k, CAVE, CAVE + 4 * len(words), len(words), SETUP_HOOK, SLOT42_HOOK, SLOT43_HOOK))


if __name__ == '__main__':
    main()
