#!/usr/bin/env python3
"""Kirby's copy of a custom special: effect and sound scripts too. Prints rpx_patch.py args.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx ... $(python3 tools/position_vars_cave.py) \\
      $(python3 tools/strike_cave.py) $(python3 tools/copy_fx_cave.py)

(after position_vars_cave.py, whose grow:0x04B79000 makes the code space this uses; it sits after
strike_cave.py's, which ends before 0x04B78E80. The hook is too far from there for a branch, so it
goes through TRAMP, 4 free words at the end of copy_custom_cave.py's CAVE_C space in the Havok cave.)

MotionAnimcmdModule (FighterMotionAnimcmdModuleImpl, vtable 0x10093B80) runs a motion's scripts on
four agents (at +0x50, 0x38 bytes each), one per script set: 0 game (ACMD), 1 expression, 2 sound,
3 effect (the order the loader 0x02E421C0 stores game.bin / expression.bin / sound.bin / effect.bin
at the kind's entry +0x10 + 8 set). A motion change (0x027608B0) binds sets 0-1 at once and leaves
the motion at +0x1C; the module's late update (0x02760DB0, every frame) then binds sets 2-3 to the
default kind for it (0x027606C0(this, 2, 3)) and sets +0x1C = -2. MSC MotionAnimcmdModule(0, set,
motion, kind) calls vtable +0x6C (0x02760CE4), which stores the kind for that set but only rebinds
set 0: copy_custom_motion() in fighters/kirby/kirby.c used it to run the copied fighter's custom
ACMD, while the effects and sounds stayed Kirby's own (default) ones.

The hook at +0x6C's first instruction adds set BIND_ALL (0x10, never used by the game): it binds
sets 2 and 3 (sound, effect) to `kind`'s scripts for `motion` the way 0x027606C0 does
  script = 0x02E42518([0x102FF68C], kind, motion)       (0 = the kind has no such motion: nothing done)
  table  = 0x02E424D8([0x102FF68C], kind, set)
  0x02BEE560(table, [this+4], this + 0x50 + 0x38 set, script)
  0x02BEE950(table, [this+4], agent, [this+0x24], [this+0x20], ![this+0x2C])   (unless [this+0x2D])
stores the kind at +8 + 4 set, and sets +0x1C = -2 so the late update doesn't rebind them to
Kirby's own scripts (the first version bound sets 1-2 and was overwritten there; set 1 is
expression). Any other set goes on to the original function. copy_custom_motion() calls it for a
custom slot only, after the motion change.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm, ha, lo  # noqa: E402

CAVE = 0x04B78E80
LIMIT = 0x04B79000
TRAMP = 0x037EE5F0          # -0x037EE600 (transform_grab_cave.py starts there)
HOOK = 0x02760CE4           # MotionAnimcmdModule vtable +0x6C: mflr r0
BIND_ALL = 0x10
SCRIPT_OF = 0x02E42518
SET_TABLE = 0x02E424D8
BIND = 0x02BEE560
FSYNC = 0x02BEE950

SOURCE = """
copy_fx:                                # r3 this, r4 set, r5 motion, r6 kind (-1 = own)
        lis r11, dbg@ha                 # debug: every +0x6C call (r11 / r12 are free here)
        addi r11, r11, dbg@l
        lwz r12, 0(r11)
        addi r12, r12, 1
        stw r12, 0(r11)
        cmpwi r4, %(BIND_ALL)d
        beq fx_all
        mflr r0                         # +0x6C's own instruction
        lis r12, %(BACK_HI)s            # back (too far for b; r12 is free at a function's start)
        addi r12, r12, %(BACK_LO)s
        mtctr r12
        bctr
fx_all:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r24, 0x10(r1)
        mr r31, r3
        mr r30, r5
        mr r29, r6
        cmpwi r29, -1
        bne fx_kind
        lwz r29, 0x18(r31)              # own kind
fx_kind:
        lis r26, dbg@ha
        addi r26, r26, dbg@l
        lwz r12, 4(r26)                 # debug: bind-all calls, motion, kind
        addi r12, r12, 1
        stw r12, 4(r26)
        stw r30, 8(r26)
        stw r29, 0xC(r26)
        li r0, 0
        stw r0, 0x14(r26)
        stw r0, 0x18(r26)
        lis r3, 0x1030
        lwz r3, -0x974(r3)              # [0x102FF68C] script manager
        mr r4, r29
        mr r5, r30
        bl %(SCRIPT_OF)s
        mr. r28, r3
        stw r28, 0x10(r26)              # debug: the motion's script (0 = none)
        beq fx_done
        li r27, 2
fx_loop:
        slwi r0, r27, 2
        add r12, r31, r0
        stw r29, 8(r12)                 # the set's kind
        lis r3, 0x1030
        lwz r3, -0x974(r3)
        mr r4, r29
        mr r5, r27
        bl %(SET_TABLE)s
        slwi r0, r27, 2
        add r12, r26, r0
        stw r3, 0xC(r12)                # debug: set 2 / 3 table (0x14 / 0x18)
        mr. r25, r3
        beq fx_next
        mulli r24, r27, 0x38
        addi r24, r24, 0x50
        add r24, r31, r24               # the set's agent
        lwz r4, 4(r31)
        mr r5, r24
        mr r6, r28
        bl %(BIND)s
        lbz r0, 0x2D(r31)               # frame sync, as 0x027606C0 does
        cmpwi r0, 0
        bne fx_next
        lbz r6, 0x2C(r31)
        xori r6, r6, 1
        mr r3, r25
        lwz r4, 4(r31)
        mr r5, r24
        lfs f1, 0x24(r31)
        lfs f2, 0x20(r31)
        bl %(FSYNC)s
fx_next:
        addi r27, r27, 1
        cmpwi r27, 3
        ble fx_loop
        li r0, -2                       # the late update's own "bound" mark: it won't rebind 2-3
        stw r0, 0x1C(r31)
fx_done:
        lmw r24, 0x10(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
dbg:                                    # debug words (docs/native-notes.md): +0x6C calls, bind-all
        .word 0                         # calls, last motion, last kind, last script, set 2 / 3 tables
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
"""


def assemble():
    a = Asm(CAVE)
    back = HOOK + 4
    a.asm(SOURCE % dict(BIND_ALL=BIND_ALL, BACK_HI=hex(ha(back)), BACK_LO=hex(lo(back)), SCRIPT_OF="0x%08X" % SCRIPT_OF,
                        SET_TABLE="0x%08X" % SET_TABLE, BIND="0x%08X" % BIND, FSYNC="0x%08X" % FSYNC))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, "copy fx cave too big: %d words" % len(words)
    return a, words


def trampoline(target):
    t = Asm(TRAMP)
    t.asm("""
        lis r12, %s
        addi r12, r12, %s
        mtctr r12
        bctr""" % (hex(ha(target)), hex(lo(target))))
    return t.words()


def main():
    a, words = assemble()
    out = ["0x%08X=0x%08X" % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ["0x%08X=0x%08X" % (TRAMP + 4 * i, w) for i, w in enumerate(trampoline(a.labels["copy_fx"]))]
    off = TRAMP - HOOK
    out.append("0x%08X=0x%08X" % (HOOK, (18 << 26) | (off & 0x3FFFFFC)))
    print(" ".join(out))


if __name__ == "__main__":
    main()
