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

Reads with no such fighter (no opponent, empty slot, or called from a non-fighter such as an
article, for self IDs) give 0 and writes do nothing.

Native details (docs/native-notes.md "Position variables"):
  fighter table   [[0x1035184C] + 0]: +0 entries, +8 count; entry = entries + slot * 0x76B0,
                  live when byte +0x1E >= 4; +0xC module accessor
  accessor        +0x18 PostureModule, +0x28 WorkModule
  PostureModule   +0x10/+0x14/+0x18 position, +0x60 facing; vtable +0x4C set_pos(this, vec3*)
"""
import os
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
# frame: 0x08-0x13 vec3 for set_pos, 0x18 value, 0x1C-0x37 r25-r31
# r31 WorkModule, r30 index, r29 write, r28 self posture, r27 component, r26 loop, r25 target
# f12 self facing, f13 distance squared to the opponent
posvar:
        mflr r0
        stwu r1, -0x40(r1)
        stw r0, 0x44(r1)
        stmw r25, 0x1C(r1)
        stfs f1, 0x18(r1)
        mr r31, r3
        clrlwi r30, r4, 24
        mr r29, r5
        li r28, 0
        li r26, 0
self_loop:                              # self = the fighter whose WorkModule this is
        mr r3, r26
        bl slot
        cmpwi r3, 0
        beq self_next
        cmplw r4, r31
        bne self_next
        mr r28, r3
        b self_done
self_next:
        addi r26, r26, 1
        cmpwi r26, {SLOTS}
        blt self_loop
self_done:
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
        li r25, 0
        li r26, 0
opp_loop:                               # nearest other fighter by X/Y distance
        mr r3, r26
        bl slot
        cmpwi r3, 0
        beq opp_next
        cmplw r3, r28
        beq opp_next
        lfs f0, 0x10(r3)
        lfs f2, 0x10(r28)
        fsubs f0, f0, f2
        lfs f3, 0x14(r3)
        lfs f2, 0x14(r28)
        fsubs f3, f3, f2
        fmuls f0, f0, f0
        fmadds f0, f3, f3, f0
        cmpwi r25, 0
        beq opp_take
        fcmpu cr0, f0, f13
        bge opp_next
opp_take:
        mr r25, r3
        fmr f13, f0
opp_next:
        addi r26, r26, 1
        cmpwi r26, {SLOTS}
        blt opp_loop
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
        frsqrte f0, f13                 # y ~ 1/sqrt(d), refined: y *= 1.5 - 0.5*d*y*y
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
        lmw r25, 0x1C(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
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
        bl posvar
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
        bl posvar
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
                        GET_GO="blr" if DEBUG == "noop" else "b posvar",
                        SET_GO="blr" if DEBUG == "noop" else "b posvar",
                        SETPOS_CALL="nop" if DEBUG == "nowrite" else "bctrl", STAT_CAVE=STAT_CAVE, SET_RESUME=SET_RESUME, SLOTS=SLOTS,
                        ENTRY_SIZE=ENTRY_SIZE, FIGHTERS_HA=((FIGHTERS + 0x8000) >> 16) & 0xFFFF,
                        FIGHTERS_LO=FIGHTERS & 0xFFFF if FIGHTERS & 0x8000 == 0 else (FIGHTERS & 0xFFFF) - 0x10000)
    src2 = SOURCE2 + "".join(ARITH_STUB.format(n=n, first=first, resume=hook + 4)
                             for n, (hook, first) in enumerate(ARITH))
    parts = [(CAVE, LIMIT, src), (CAVE2, LIMIT2, src2)]
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
        for a, limit in zip(assemble(), (LIMIT, LIMIT2)):
            names = {v: k for k, v in a.labels.items()}
            code = b"".join(struct.pack(">I", x) for x in a.words())
            for ins in md.disasm(code, a.base):
                if ins.address in names:
                    print("%s:" % names[ins.address])
                print("  %08x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
            print("end 0x%08X (limit 0x%08X)" % (a.base + len(code), limit))
        return
    print(" ".join("0x%08X=0x%08X" % (a, v) for a, v in sorted(words().items())))


if __name__ == "__main__":
    main()
