#!/usr/bin/env python3
"""Common position variables for every fighter: prints rpx_patch.py args (ADDR=VALUE words).

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/starcopy_cave.py) ... \\
      $(python3 tools/kirby_stat_cave.py) $(python3 tools/position_vars_cave.py)

(after kirby_stat_cave.py: both hook WorkModuleImpl::get_float, and this one passes other IDs on to
the stat cave; after starcopy_cave.py, which clears the dead Havok function the caves live in.)

WorkModule float IDs 0x0F0000xx (category F, unused for floats by the game) are handled here
instead of the WorkModule tables, by hooks on get / set / add / sub / mul / div float of
WorkModuleImpl and all four of its subclasses (fighters use their own copies at 0x02F1DBE4..., see
CLASSES; hooking only the base class left fighters writing these IDs into a table that doesn't
exist, which crashed). MSC (WorkModuleF / WorkModule) and ACMD (SET_FLOAT, Float_Var_Compare) go
through these functions, so the IDs work from both, on any fighter. Other IDs are untouched.

"Self" is the fighter that owns the WorkModule being read. "Opponent" is the nearest other fighter
(by X/Y distance; teams are not considered). Slots are the game's fighter table entries 0-7, in
player order. Positions are the fighter's PostureModule position (the same X/Y as MSC's
PostureModuleF(1)/(2)); writes go through the fighter's own set_pos, like MSC's PostureModule(3).

"Fwd" means X measured along this fighter's facing: positive = in front of where self faces.

  ID          read                                write
  0x0F000000  self X                              set self X
  0x0F000001  self Y                              set self Y
  0x0F000002  self Z                              set self Z
  0x0F000003  self facing (1 right, -1 left)      -
  0x0F000004  0                                   move self forward by value (fwd)
  0x0F000005  0                                   move self up by value
  0x0F000006  0                                   move self along Z by value
  0x0F000008  opponent X                          set opponent X
  0x0F000009  opponent Y                          set opponent Y
  0x0F00000A  opponent Z                          set opponent Z
  0x0F00000B  distance to opponent (X/Y)          -
  0x0F00000C  opponent X - self X (fwd)           put opponent at self + value (fwd)
  0x0F00000D  opponent Y - self Y                 put opponent at self Y + value
  0x0F00000E  opponent Z - self Z                 put opponent at self Z + value
  0x0F000010  self X - opponent X (fwd)           put self at opponent + value (fwd)
  0x0F000011  self Y - opponent Y                 put self at opponent Y + value
  0x0F000012  self Z - opponent Z                 put self at opponent Z + value
  0x0F000020 + 4*slot + n   slot X/Y/Z/facing (n = 0..3), slot 0-7   set slot X/Y/Z
                            (0x0F000020-0x0F00003F)

  0x0F000040-0x0F000097      hitstun / hitstop / offsets for self, the nearest opponent, the last
                            fighter hit and each slot (see "Combat variables" below and
                            docs/position-variables.md)

Reads with no such fighter (no opponent, empty slot, or called from a non-fighter such as an
article, for self IDs) give 0 and writes do nothing.

Native details (docs/native-notes.md "Position variables"):
  fighter table   [[0x1035184C] + 0]: +0 entries, +8 count; entry = entries + slot * 0x76B0,
                  live when byte +0x1E >= 4; +0xC module accessor
  accessor        +0x18 PostureModule, +0x28 WorkModule
  PostureModule   +0x10/+0x14/+0x18 position, +0x60 facing; vtable +0x4C set_pos(this, vec3*)
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

# WorkModuleImpl and its four subclasses each have their own (identical) copy of get / set / add /
# sub / mul / div float: vtables 0x10003224 (base), 0x100F93CC, 0x1012132C, 0x1013A1C0 / 0x1013AFFC
# (fighters), 0x10153184. Every copy's first instruction branches to the same stubs; IDs that
# aren't ours continue in the base copy (same code), so one set of stubs covers them all.
# (get, set, add, sub, mul, div) per class:
CLASSES = [
    (0x0200F628, 0x0200F648, 0x0200F73C, 0x0200F764, 0x0200F78C, 0x0200F7B4),  # base
    (0x02BCD8A0, 0x02BCD8C0, 0x02BCD9B4, 0x02BCD9DC, 0x02BCDA04, 0x02BCDA2C),
    (0x02DA6020, 0x02DA6040, 0x02DA6134, 0x02DA615C, 0x02DA6184, 0x02DA61AC),
    (0x02F1DBE4, 0x02F1DC04, 0x02F1DCF8, 0x02F1DD20, 0x02F1DD48, 0x02F1DD70),  # fighters
    (0x03060880, 0x030608A0, 0x03060994, 0x030609BC, 0x030609E4, 0x03060A0C),
]
GET_HOOK = 0x0200F628      # WorkModuleImpl::get_float (vtable 0x10003224 +0x44)
SET_HOOK = 0x0200F648      # WorkModuleImpl::set_float (+0x4C)
SET_RESUME = 0x0200F64C    # set_float after its first instruction
STAT_CAVE = 0x037EE160     # kirby_stat_cave.py: the get_float path for every other ID
CAVE = 0x037EDC78          # free: 0x037EDC78-0x037EE098 (between the star cave's two parts)
LIMIT = 0x037EE098
CAVE2 = 0x037EE280         # free: after the stat cave's table, up to copy_custom_cave.py's CAVE_C
LIMIT2 = 0x037EE400
# WorkModuleImpl add/sub/mul/div float (vtable +0x64/+0x6C/+0x74/+0x7C) work on the tables
# directly; for these IDs they are turned into a read and a write. (hook, first instruction)
ARITH = [(0x0200F73C, "rlwinm r12, r4, 8, 28, 31"), (0x0200F764, "rlwinm r12, r4, 8, 28, 31"),
         (0x0200F78C, "rlwinm r12, r4, 8, 28, 31"), (0x0200F7B4, "lis r12, 0x1000")]
FIGHTERS = 0x1035184C      # object manager tables: [+0] = fighter table
ENTRY_SIZE = 0x76B0
SLOTS = 8

SOURCE = """
# --- hooks -------------------------------------------------------------------------------
get_hook:
        rlwinm r11, r4, 8, 28, 31       # category
        cmpwi r11, 15
        bne get_other
        rlwinm. r12, r4, 0, 8, 23       # index must be < 0x100
        bne get_other
        li r5, 0
        {GET_GO}
get_other:
        b {STAT_CAVE}

set_hook:
        rlwinm r11, r4, 8, 28, 31       # set_float's own first instruction
        cmpwi r11, 15
        bne set_other
        rlwinm. r12, r4, 0, 8, 23
        bne set_other
        li r5, 1
        {SET_GO}
set_other:
        b {SET_RESUME}

# --- slot(r3 = slot) -> r3 = PostureModule or 0, r4 = WorkModule. Uses r11, r12 only. ------
slot:
        lis r12, {FIGHTERS_HA}
        lwz r12, {FIGHTERS_LO}(r12)
{DATA_r12_slot_none}
        lwz r12, 0(r12)
{DATA_r12_slot_none}
        lwz r11, 8(r12)                 # entry count
        cmplw r3, r11
        bge slot_none
        lwz r12, 0(r12)                 # entries
{DATA_r12_slot_none}
        mulli r11, r3, {ENTRY_SIZE}
        add r12, r12, r11
        lbz r11, 0x1E(r12)              # live when >= 4 (as 0x02BEF61C checks)
        cmplwi r11, 4
        blt slot_none
        lwz r12, 0xC(r12)               # module accessor
{DATA_r12_slot_none}
        lwz r4, 0x28(r12)
        lwz r3, 0x18(r12)
{DATA_r4_slot_none}
{DATA_r3_slot_none}
        blr
slot_none:
        li r3, 0
        blr


# --- posvar(r3 = WorkModule, r4 = ID, r5 = 1 to write, f1 = value) -> f1 ---------------------
# frame: 0x08-0x13 vec3 for set_pos, 0x18 value, 0x1C-0x43 r22-r31
# r31 WorkModule, r30 index, r29 write, r28 self posture, r27 component, r26 loop, r25 target
# f12 self facing, f13 distance squared to the opponent
posvar:
        mflr r0
        stwu r1, -0x48(r1)
        stw r0, 0x4C(r1)
        stmw r22, 0x1C(r1)
        stfs f1, 0x18(r1)
        mr r31, r3
        clrlwi r30, r4, 24
        mr r29, r5
        bl find_self                    # r28 self posture (0 = none), r27 accessor, r26 slot
        cmplwi r30, 0x20
        blt not_slot
        cmplwi r30, 0x40
        bge ret_zero
        addi r3, r30, -0x20             # slot IDs
        srwi r3, r3, 2
        bl slot
        mr r25, r3
        cmpwi r25, 0
        beq ret_zero
        clrlwi r27, r30, 30
        b abs_comp
not_slot:
        cmpwi r28, 0
        beq ret_zero
        cmplwi r30, 4
        bge not_self
        mr r25, r28
        mr r27, r30
abs_comp:                               # r25 posture, r27 component 0-3: read or set
        cmpwi r27, 3
        bne abs_pos
        cmpwi r29, 0
        bne ret_zero
        lfs f1, 0x60(r25)
        b ret
abs_pos:
        cmpwi r29, 0
        bne abs_write
        slwi r12, r27, 2
        add r12, r12, r25
        lfs f1, 0x10(r12)
        b ret
abs_write:
        lfs f1, 0x18(r1)
        b set_comp

not_self:
        lfs f12, 0x60(r28)              # self facing
        cmplwi r30, 7
        bge need_opp
        cmpwi r29, 0                    # 4-6: move self by value
        beq ret_zero
        addi r27, r30, -4
        mr r25, r28
        lfs f1, 0x18(r1)
        cmpwi r27, 0
        bne move_add
        fmuls f1, f1, f12
move_add:
        slwi r12, r27, 2
        add r12, r12, r25
        lfs f0, 0x10(r12)
        fadds f1, f1, f0
        b set_comp

need_opp:
        cmplwi r30, 8
        blt ret_zero
        bl find_opp                     # r25 nearest opponent's posture, f13 distance squared
        cmpwi r25, 0
        beq ret_zero

        cmplwi r30, 0xB
        bge not_opp_abs
        addi r27, r30, -8               # 8-A: opponent position
        b abs_pos
not_opp_abs:
        bne not_dist
        cmpwi r29, 0                    # B: distance
        bne ret_zero
        lis r12, consts@ha
        addi r12, r12, consts@l
        lfs f1, 0(r12)                  # 0.0
        fcmpu cr0, f13, f1
        ble ret
        lfs f3, 4(r12)                  # 0.5
        lfs f4, 8(r12)                  # 1.5
        frsqrte f0, f13                 # y ~ 1/sqrt(d), refined twice: y *= 1.5 - 0.5*d*y*y
        fmul f5, f0, f0
        fmul f5, f5, f13
        fmul f5, f5, f3
        fsub f5, f4, f5
        fmul f0, f0, f5
        fmul f5, f0, f0
        fmul f5, f5, f13
        fmul f5, f5, f3
        fsub f5, f4, f5
        fmul f0, f0, f5
        fmul f1, f13, f0
        frsp f1, f1
        b ret
not_dist:
        cmplwi r30, 0xF
        bge not_opp_rel
        addi r27, r30, -0xC             # C-E: opponent relative to self
        mr r3, r25
        mr r4, r28
        b rel
not_opp_rel:
        cmplwi r30, 0x10
        blt ret_zero
        cmplwi r30, 0x13
        bge ret_zero
        addi r27, r30, -0x10            # 10-12: self relative to opponent
        mr r3, r28
        mr r4, r25
rel:                                    # r3 moved, r4 reference, r27 component
        mr r25, r3
        slwi r12, r27, 2
        add r11, r12, r3
        add r12, r12, r4
        lfs f2, 0x10(r12)
        cmpwi r29, 0
        bne rel_write
        lfs f1, 0x10(r11)
        fsubs f1, f1, f2
        cmpwi r27, 0
        bne ret
        fmuls f1, f1, f12
        b ret
rel_write:
        lfs f1, 0x18(r1)
        cmpwi r27, 0
        bne rel_add
        fmuls f1, f1, f12
rel_add:
        fadds f1, f1, f2

set_comp:                               # posture r25, component r27 = f1, via its own set_pos
        lfs f0, 0x10(r25)
        stfs f0, 0x8(r1)
        lfs f0, 0x14(r25)
        stfs f0, 0xC(r1)
        lfs f0, 0x18(r25)
        stfs f0, 0x10(r1)
        slwi r12, r27, 2
        add r12, r12, r1
        stfs f1, 0x8(r12)
        lwz r12, 0(r25)                 # its vtable and set_pos must look like real ones
{DATA_r12_ret_zero}
        lwz r12, 0x4C(r12)
{CODE_r12_ret_zero}
        mr r3, r25
        addi r4, r1, 8
        mtctr r12
        {SETPOS_CALL}
ret_zero:
        lis r12, consts@ha
        lfs f1, consts@l(r12)
ret:
        lmw r22, 0x1C(r1)
        lwz r0, 0x4C(r1)
        mtlr r0
        addi r1, r1, 0x48
        blr
consts:
        .float 0.0
        .float 0.5
        .float 1.5
"""

ARITH_STUB = """
arith_hook{n}:
        rlwinm r11, r4, 8, 28, 31
        cmpwi r11, 15
        bne arith_other{n}
        rlwinm. r12, r4, 0, 8, 23
        bne arith_other{n}
        li r6, {n}
        b arith
arith_other{n}:
        {first}
        b {resume}
"""

SOURCE2 = """
# --- arith(r3 = WorkModule, r4 = ID, f1 = operand, r6 = 0 add, 1 sub, 2 mul, 3 div) ---------
arith:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        stw r30, 0x18(r1)
        stw r29, 0x14(r1)
        stfs f1, 0x10(r1)
        mr r31, r3
        mr r30, r4
        mr r29, r6
        li r5, 0
        bl var_entry
        lfs f2, 0x10(r1)
        cmpwi r29, 1
        blt arith_add
        beq arith_sub
        cmpwi r29, 2
        beq arith_mul
        lis r12, consts@ha              # div: by 0 does nothing, as in the game
        lfs f0, consts@l(r12)
        fcmpu cr0, f2, f0
        beq arith_done
        fdivs f1, f1, f2
        b arith_set
arith_add:
        fadds f1, f1, f2
        b arith_set
arith_sub:
        fsubs f1, f1, f2
        b arith_set
arith_mul:
        fmuls f1, f1, f2
arith_set:
        mr r3, r31
        mr r4, r30
        li r5, 1
        bl var_entry
arith_done:
        lwz r29, 0x14(r1)
        lwz r30, 0x18(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
"""


def check_data(reg, fail):
    """Branch to fail unless reg is a word-aligned pointer in 0x10000000-0x4FFFFFFF (data / heap)."""
    return ("        addis r0, %s, -0x1000\n"
            "        rlwinm. r0, r0, 0, 0, 1\n"
            "        bne %s\n"
            "        andi. r0, %s, 3\n"
            "        bne %s" % (reg, fail, reg, fail))


def check_code(reg, fail):
    """Branch to fail unless reg is a word-aligned address in 0x02000000-0x09FFFFFF (code)."""
    return ("        addis r0, %s, -0x200\n"
            "        rlwinm. r0, r0, 0, 0, 4\n"
            "        bne %s\n"
            "        andi. r0, %s, 3\n"
            "        bne %s" % (reg, fail, reg, fail))


# --- Combat variables: IDs 0x0F000040-0x0F000097 (hitstun / hitstop / offsets per target) -------
# index = 0x40 + 8 * target + quantity
#   target  0 self, 1 nearest opponent, 2 last fighter self hit, 3-10 player slots 1-8
#   quantity
#     0 hitstun frames left (int 0x1000003E)       read / set
#     1 hitstun of the last hit taken (DamageModuleF(1))   read
#     2 hitstun x value                              write (reads 0)
#     3 in hitstop: 1 / 0 (StopModule(1))           read; write: hitstop N frames + shake
#     4 hitstop of the last hit taken (DamageModule(8))     read; write: hitstop N frames, no shake
#     5 / 6 / 7 offset X (along self's facing) / Y / Z from self   read; write: put the target there
# The game's own MSC module commands do the work: the cave calls the MSC wrappers (WorkModule,
# DamageModule(F), StopModule, ShakeModule) with a fake MSC context whose +4 is the target's module
# accessor, the way ACMD's SET_FLOAT calls the WorkModule handler.
# "Last fighter hit": the newest hit record of self's attack (AttackModule +0x50: +0x4C records on,
# +0x18 hitbox count, +0x14 hitboxes (0x174 each), list +0x124 / first node +0x128, node +0x18 =
# object ID; fighter ID: category (id >> 28) 0, slot (id >> 16) & 0xFFF). When the records are gone
# (the attack ended), the fighter whose last attacker (int 0x10000065, a player number) is self's
# slot, preferring one still in hitstun.
EXT_REGIONS = [               # (start, end) free code for the combat variables
    (0x04AE6258, 0x04AE648C),  # unreferenced function (no calls, relocations or exports)
    (0x04AD2164, 0x04AD22F8),  # unreferenced function
    (0x037EE858, 0x037EE97C),  # unreferenced function after the Havok one
    (0x037EE3B0, 0x037EE400),  # after the arith stubs, before copy_custom_cave.py's CAVE_C
    (0x037EE240, 0x037EE280),  # after the stat cave's table (8 entries, kirby_stat_cave.py)
]
RELOC_REGIONS = EXT_REGIONS[:3]  # their old relocations must not patch the new code
RELOC_DUMMY = 0x037EE73C   # dead word starcopy_cave.py already points moved relocations at
MSC_WORK = 0x030B2B28      # MSC syscall wrappers (ctx, args): 0x16 WorkModule
MSC_DAMAGE = 0x030B2F8C    # 0x24 DamageModule
MSC_DAMAGE_F = 0x030B2FC4  # 0x25 DamageModuleF
MSC_STOP = 0x030B5160      # 0x30 StopModule
MSC_SHAKE = 0x030B5C50     # 0x48 ShakeModule
HITSTUN = 0x1000003E
LAST_ATTACKER = 0x10000065


def msc(wrapper, *args):
    """Call an MSC module command on the target (accessor in r24) through ext_msc. args: ints or
    register names, stored as the command's words at 0x20(r1)... Result in r3 (float bits for F)."""
    out = []
    for v in sorted(set(a for a in args if not isinstance(a, str)), key=str):
        if -0x8000 <= v < 0x8000:
            out.append("li r0, %d" % v)
        else:
            out.append("lis r0, 0x%X" % ((v >> 16) & 0xFFFF))
            if v & 0xFFFF:
                out.append("ori r0, r0, 0x%X" % (v & 0xFFFF))
        out += ["stw r0, 0x%X(r1)" % (0x20 + 4 * i) for i, a in enumerate(args) if a == v and not isinstance(a, str)]
    out += ["stw %s, 0x%X(r1)" % (a, 0x20 + 4 * i) for i, a in enumerate(args) if isinstance(a, str)]
    out += ["li r4, %d" % len(args), "lis r5, 0x%X" % (wrapper >> 16),
            "ori r5, r5, 0x%X" % (wrapper & 0xFFFF), "bl ext_msc"]
    return "\n".join("        " + x for x in out)


def chk(reg, fail):
    """bne fail unless reg is a word-aligned data pointer (ext_chk)."""
    return "        mr r9, %s\n        bl ext_chk\n        bne %s" % (reg, fail)


# Blocks in order: (text, falls through into the next block). pack() spreads them over EXT_REGIONS.
def ext_blocks(SLOTS, SETPOS_CALL):
    F = True
    return [
("""
var_entry:                              # every hook / arith call: r3 WM, r4 ID, r5 write, f1
        rlwinm r12, r4, 0, 24, 31
        cmplwi r12, 0x40
        blt posvar
ext:
        mflr r0
        stwu r1, -0x80(r1)
        stw r0, 0x84(r1)
        stmw r22, 0x50(r1)
        stfs f1, 0x10(r1)
        mr r31, r3
        clrlwi r30, r4, 24
        mr r29, r5
        bl find_self
        cmplwi r30, 0x98
        bge ext_zero
        addi r3, r30, -0x40
        clrlwi r0, r3, 29
        stw r0, 0x14(r1)                # quantity
        srwi r22, r3, 3                 # target
        cmpwi r22, 3
        bge ext_t_slot
        cmpwi r22, 1
        blt ext_t_self
        beq ext_t_opp
        b ext_t_last
""", False),
("""
ext_t_self:
        cmpwi r28, 0
        beq ext_zero
        mr r25, r28
        mr r24, r27
        mr r23, r31
        b ext_have
ext_t_slot:
        addi r3, r22, -3
        bl slot
        cmpwi r3, 0
        beq ext_zero
        mr r25, r3
        mr r24, r12
        mr r23, r4
        b ext_have
""", False),
("""
ext_t_opp:                              # nearest other fighter by X/Y distance
        cmpwi r28, 0
        beq ext_zero
        bl find_opp
        cmpwi r25, 0
        beq ext_zero
""", F),
("""
ext_have:                               # r25 posture, r24 accessor, r23 WorkModule of the target
        lwz r22, 0x14(r1)
        cmpwi r22, 5
        bge ext_q_offset
        cmpwi r22, 1
        blt ext_q_hitstun
        beq ext_q_dealt
        cmpwi r22, 3
        blt ext_q_mul
        beq ext_q_stop_shake
        b ext_q_stop
""", False),
("""
ext_q_hitstun:
        cmpwi r29, 0
        bne ext_hitstun_set
        bl ext_get_hitstun
        b ext_ret_int
ext_hitstun_set:
        bl ext_value_int
        mr r5, r3
        bl ext_set_hitstun
        b ext_zero
ext_q_dealt:
        cmpwi r29, 0
        bne ext_zero
%(DEALT)s
        stw r3, 0x8(r1)
        lfs f1, 0x8(r1)
        b ext_ret
""", False),
("""
ext_q_mul:
        cmpwi r29, 0
        beq ext_zero
        bl ext_get_hitstun
        bl ext_i2f
        lfs f0, 0x10(r1)
        fmul f1, f1, f0
        fctiwz f0, f1
        stfd f0, 0x8(r1)
        lwz r5, 0xC(r1)
        bl ext_set_hitstun
        b ext_zero
""", False),
("""
ext_q_stop_shake:
        cmpwi r29, 0
        bne ext_stop_write_shake
%(IN_STOP)s
        b ext_ret_int
ext_stop_write_shake:
        bl ext_value_int
        mr r22, r3                      # frames
%(SHAKE)s
        b ext_stop_set
""", False),
("""
ext_q_stop:
        cmpwi r29, 0
        bne ext_stop_write
%(STOP_DEALT)s
        b ext_ret_int
ext_stop_write:
        bl ext_value_int
        mr r22, r3
ext_stop_set:
%(SET_STOP)s
        b ext_zero
""", False),
("""
ext_q_offset:                           # quantity 5-7: target - self, X along self's facing
        cmpwi r28, 0
        beq ext_zero
        addi r22, r22, -5
        lfs f12, 0x60(r28)
        slwi r12, r22, 2
        add r11, r12, r25
        add r12, r12, r28
        lfs f2, 0x10(r12)               # self
        cmpwi r29, 0
        bne ext_off_write
        lfs f1, 0x10(r11)
        fsubs f1, f1, f2
        cmpwi r22, 0
        bne ext_ret
        fmuls f1, f1, f12
        b ext_ret
""", False),
("""
ext_off_write:
        lfs f1, 0x10(r1)
        cmpwi r22, 0
        bne ext_off_add
        fmuls f1, f1, f12
ext_off_add:
        fadds f1, f1, f2
        lfs f0, 0x10(r25)               # target position with component r22 replaced
        stfs f0, 0x40(r1)
        lfs f0, 0x14(r25)
        stfs f0, 0x44(r1)
        lfs f0, 0x18(r25)
        stfs f0, 0x48(r1)
        slwi r12, r22, 2
        add r12, r12, r1
        stfs f1, 0x40(r12)
        lwz r12, 0(r25)
%(CHK_VT)s
        lwz r12, 0x4C(r12)
        mr r3, r25
        addi r4, r1, 0x40
        mtctr r12
        %(SETPOS)s
        b ext_zero
""", False),
("""
ext_t_last:                             # newest hit record of self's attack
        cmpwi r27, 0
        beq ext_zero
        lwz r6, 0x50(r27)
%(CHK_R6)s
        lwz r4, 0x4C(r6)
        cmpwi r4, 0
        beq ext_last_fb
        lwz r5, 0x18(r6)
        cmpwi r5, 0
        ble ext_last_fb
        lwz r6, 0x14(r6)
%(CHK_R6)s
""", F),
("""
ext_last_loop:
        lwz r7, 0x128(r6)
        addi r8, r6, 0x124
        cmplw r7, r8
        beq ext_last_next
%(CHK_R7)s
        lwz r8, 0x18(r7)
        srwi. r0, r8, 28
        bne ext_last_next
        rlwinm r3, r8, 16, 20, 31
        cmplw r3, r26
        beq ext_last_next
        cmplwi r3, %(S)d
        bge ext_last_next
        bl slot
        cmpwi r3, 0
        beq ext_last_next
        mr r25, r3
        mr r24, r12
        mr r23, r4
        b ext_have
ext_last_next:
        addi r6, r6, 0x174
        addi r5, r5, -1
        cmpwi r5, 0
        bgt ext_last_loop
""", F),
("""
ext_last_fb:                            # attack over: a fighter whose last attacker is self's slot
        li r22, 0
ext_fb_loop:
        mr r3, r22
        bl slot
        cmpwi r3, 0
        beq ext_fb_next
        cmplw r3, r28
        beq ext_fb_next
        mr r25, r3
        mr r24, r12
        mr r23, r4
%(LAST_ATTACKER)s
        cmpw r3, r26
        beq ext_have
ext_fb_next:
        addi r22, r22, 1
        cmpwi r22, %(S)d
        blt ext_fb_loop
        b ext_zero
""", False),
("""
# --- find_self (r31 = WorkModule) -> r28 posture (0 = not a fighter), r27 accessor, r26 slot (-1)
# find_opp (r28 = self posture) -> r25 nearest other fighter's posture (0 = none), r24 accessor,
# r23 WorkModule, f13 X/Y distance squared. Both use r22 (callers save r22-r31).
find_self:
        mflr r0
        stwu r1, -0x10(r1)
        stw r0, 0x14(r1)
        li r28, 0
        li r27, 0
        li r26, -1
        li r22, 0
find_self_loop:
        mr r3, r22
        bl slot
        cmpwi r3, 0
        beq find_self_next
        cmplw r4, r31
        bne find_self_next
        mr r28, r3
        mr r27, r12
        mr r26, r22
        b find_done
find_self_next:
        addi r22, r22, 1
        cmpwi r22, %(S)d
        blt find_self_loop
        b find_done
find_opp:
        mflr r0
        stwu r1, -0x10(r1)
        stw r0, 0x14(r1)
        li r25, 0
        li r22, 0
find_opp_loop:
        mr r3, r22
        bl slot
        cmpwi r3, 0
        beq find_opp_next
        cmplw r3, r28
        beq find_opp_next
        lfs f0, 0x10(r3)
        lfs f2, 0x10(r28)
        fsubs f0, f0, f2
        lfs f3, 0x14(r3)
        lfs f2, 0x14(r28)
        fsubs f3, f3, f2
        fmuls f0, f0, f0
        fmadds f0, f3, f3, f0
        cmpwi r25, 0
        beq find_opp_take
        fcmpu cr0, f0, f13
        bge find_opp_next
find_opp_take:
        mr r25, r3
        mr r24, r12
        mr r23, r4
        fmr f13, f0
find_opp_next:
        addi r22, r22, 1
        cmpwi r22, %(S)d
        blt find_opp_loop
find_done:
        lwz r0, 0x14(r1)
        mtlr r0
        addi r1, r1, 0x10
        blr
""", False),
("""
ext_ret_int:                            # f1 = (float) r3
        bl ext_i2f
        b ext_ret
ext_zero:
        lis r12, consts@ha
        lfs f1, consts@l(r12)
ext_ret:
        lmw r22, 0x50(r1)
        lwz r0, 0x84(r1)
        mtlr r0
        addi r1, r1, 0x80
        blr
""", False),
("""
ext_msc:                                # MSC command r5 (wrapper) with r4 args at the caller's
        mflr r0                         # 0x20(r1), on the fighter whose accessor is r24 -> r3
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        li r0, 0
        stw r0, 0x8(r1)                 # fake MSC context: +4 = module accessor
        stw r24, 0xC(r1)
        addi r6, r1, 0x40               # the caller's 0x20(r1)
        stw r6, 0x10(r1)
        stw r4, 0x14(r1)
        addi r3, r1, 0x8
        addi r4, r1, 0x10
        mtctr r5
        bctrl
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
""", False),
("""
ext_get_hitstun:                        # r3 = target's hitstun frames left
        li r0, 6
        stw r0, 0x20(r1)
        lis r0, %(HS_HI)s
        ori r0, r0, %(HS_LO)s
        stw r0, 0x24(r1)
        li r4, 2
        b ext_msc_work
ext_set_hitstun:                        # target's hitstun frames left = r5
        stw r5, 0x24(r1)
        li r0, 7
        stw r0, 0x20(r1)
        lis r0, %(HS_HI)s
        ori r0, r0, %(HS_LO)s
        stw r0, 0x28(r1)
        li r4, 3
ext_msc_work:
        lis r5, %(WK_HI)s
        ori r5, r5, %(WK_LO)s
        b ext_msc
""", False),
("""
ext_value_int:                          # r3 = (int) the value being written
        lfs f1, 0x10(r1)
        fctiwz f0, f1
        stfd f0, 0x8(r1)
        lwz r3, 0xC(r1)
        blr
ext_chk:                                # cr0 eq when r9 is a word-aligned data pointer
        addis r0, r9, -0x1000
        rlwinm. r0, r0, 0, 0, 1
        bnelr
        andi. r0, r9, 3
        blr
""", False),
("""
ext_i2f:                                # f1 = (float) r3
        stwu r1, -0x10(r1)
        xoris r0, r3, 0x8000
        stw r0, 0xC(r1)
        lis r0, 0x4330
        stw r0, 0x8(r1)
        lfd f1, 0x8(r1)
        lis r12, ext_magic@ha
        lfd f0, ext_magic@l(r12)
        fsub f1, f1, f0
        frsp f1, f1
        addi r1, r1, 0x10
        blr
ext_magic:
        .word 0x43300000
        .word 0x80000000
""", False),
    ], dict(
        S=SLOTS, SETPOS=SETPOS_CALL,
        DEALT=msc(MSC_DAMAGE_F, 1),
        IN_STOP=msc(MSC_STOP, 1),
        STOP_DEALT=msc(MSC_DAMAGE, 8),
        SET_STOP=msc(MSC_STOP, 2, "r22"),
        SHAKE=msc(MSC_SHAKE, 0, 0, "r22", 0, 0, 0x3F800000),
        LAST_ATTACKER=msc(MSC_WORK, 6, LAST_ATTACKER),
        CHK_VT=chk("r12", "ext_zero"), CHK_R6=chk("r6", "ext_last_fb"), CHK_R7=chk("r7", "ext_last_next"),
        HS_HI=hex(HITSTUN >> 16), HS_LO=hex(HITSTUN & 0xFFFF),
        WK_HI=hex(MSC_WORK >> 16), WK_LO=hex(MSC_WORK & 0xFFFF))


def count(text):
    n = 0
    for l in text.splitlines():
        l = re.split(r"[#;]", l, maxsplit=1)[0].strip()
        if l and not l.endswith(":"):
            n += 2 if ".far " in l else 1
    return n


def far_branches(text):
    """Conditional branches to labels outside this block become .far (they may land in another
    region, megabytes away)."""
    own = set(re.findall(r"^(\w+):", text, re.M))
    def fix(m):
        return m.group(0) if m.group(3) in own else "%sb%s.far %s" % (m.group(1), m.group(2), m.group(3))
    return re.sub(r"^([ \t]+)b(eq|ne|lt|ge|le|gt) (\w+)[ \t]*$", fix, text, flags=re.M)


def pack(extra=()):
    """Spread the blocks over EXT_REGIONS (largest first, best fit). Within a region blocks keep
    their order; a block that falls through into one placed elsewhere gets a branch to it."""
    blocks, fmt = ext_blocks(SLOTS, "nop" if DEBUG == "nowrite" else "bctrl")
    blocks = [(far_branches(t % fmt), f) for t, f in blocks]
    size = [count(t) * 4 + (4 if f else 0) + (8 if "ext_magic:" in t else 0) for t, f in blocks]  # + branch / align
    regions = list(EXT_REGIONS) + list(extra)
    free = [e - s for s, e in regions]
    where = {}
    for k in sorted(range(len(blocks)), key=lambda k: -size[k]):
        fits = [ri for ri in range(len(free)) if free[ri] >= size[k]]
        if not fits:
            raise AssertionError("combat variables don't fit (block %d)" % k)
        ri = min(fits, key=lambda ri: free[ri])
        free[ri] -= size[k]
        where[k] = ri
    first_label = [re.search(r"^(\w+):", t, re.M).group(1) for t, _ in blocks]
    out = []
    for ri, (s, e) in enumerate(regions):
        ks = sorted(k for k in where if where[k] == ri)
        text = ""
        n = 0
        for i, k in enumerate(ks):
            t, falls = blocks[k]
            if "ext_magic:" in t and (n + count(t) - 2) % 2:
                t = t.replace("ext_magic:", "        .word 0\next_magic:")     # 8-align the double
            text += t
            n += count(t)
            if falls and not (i + 1 < len(ks) and ks[i + 1] == k + 1):
                text += "        b %s\n" % first_label[k + 1]
                n += 1
        out.append((s, e, text))
    return out


CHECKS = {
    "DATA_r12_slot_none": check_data("r12", "slot_none"),
    "DATA_r4_slot_none": check_data("r4", "slot_none"),
    "DATA_r3_slot_none": check_data("r3", "slot_none"),
    "DATA_r12_ret_zero": check_data("r12", "ret_zero"),
    "CODE_r12_ret_zero": check_code("r12", "ret_zero"),

}


# Diagnostic builds (python3 tools/position_vars_cave.py --debug-noop / --debug-nowrite): noop = the
# IDs are recognised but nothing else runs (reads give whatever f1 held, writes do nothing);
# nowrite = everything runs except the final set_pos call.
DEBUG = "noop" if "--debug-noop" in sys.argv else "nowrite" if "--debug-nowrite" in sys.argv else None


def assemble():
    src = SOURCE.format(**CHECKS,
                        GET_GO="blr" if DEBUG == "noop" else "b var_entry",
                        SET_GO="blr" if DEBUG == "noop" else "b var_entry",
                        SETPOS_CALL="nop" if DEBUG == "nowrite" else "bctrl", STAT_CAVE=STAT_CAVE, SET_RESUME=SET_RESUME, SLOTS=SLOTS,
                        ENTRY_SIZE=ENTRY_SIZE, FIGHTERS_HA=((FIGHTERS + 0x8000) >> 16) & 0xFFFF,
                        FIGHTERS_LO=FIGHTERS & 0xFFFF if FIGHTERS & 0x8000 == 0 else (FIGHTERS & 0xFFFF) - 0x10000)
    src2 = SOURCE2 + "".join(ARITH_STUB.format(n=n, first=first, resume=hook + 4)
                             for n, (hook, first) in enumerate(ARITH))
    a = Asm(CAVE)
    a.asm(src)
    tail = (a.pc + 7) & ~7          # the rest of the first cave is free for the combat variables
    parts = [(CAVE, LIMIT, src), (CAVE2, LIMIT2, src2)] + pack([(tail, LIMIT)] if tail < LIMIT else [])
    labels = {}
    for base, _, text in parts:     # first pass: every label of both parts
        a = Asm(base)
        a.asm(text)
        labels.update(a.labels)
    out = []
    for base, limit, text in parts:
        a = Asm(base)
        a.labels = labels
        a.asm(text)
        assert a.pc <= limit, "cave at 0x%08X too long" % base
        out.append(a)
    return out


def words():
    parts = assemble()
    out = {}
    for a in parts:
        out.update({a.base + 4 * i: v for i, v in enumerate(a.words())})
    labels = parts[0].labels
    for get, set_, *arith in CLASSES:
        out[get] = branch(get, labels["get_hook"])
        out[set_] = branch(set_, labels["set_hook"])
        for n, hook in enumerate(arith):
            out[hook] = branch(hook, labels["arith_hook%d" % n])
    return out


def branch(src, dst):
    return (18 << 26) | ((dst - src) & 0x3FFFFFC)


def main():
    if "--check" in sys.argv:
        from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN
        md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
        for a in assemble():
            names = {v: k for k, v in a.labels.items()}
            code = b"".join(struct.pack(">I", x) for x in a.words())
            for ins in md.disasm(code, a.base):
                if ins.address in names:
                    print("%s:" % names[ins.address])
                print("  %08x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
            print("end 0x%08X" % (a.base + len(code)))
        return
    out = ["reloc:0x%08X-0x%08X=0x%08X" % (lo, hi, RELOC_DUMMY) for lo, hi in RELOC_REGIONS]
    out += ["0x%08X=0x%08X" % (a, v) for a, v in sorted(words().items())]
    print(" ".join(out))


if __name__ == "__main__":
    main()
