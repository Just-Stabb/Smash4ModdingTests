#!/usr/bin/env python3
"""Kirby's copy of a custom special: effect and sound scripts too. Prints rpx_patch.py args.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx ... $(python3 tools/position_vars_cave.py) \\
      $(python3 tools/strike_cave.py) $(python3 tools/copy_fx_cave.py)

(after position_vars_cave.py, whose grow:0x04B7C000 makes the code space this uses; it sits after
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

The hook at +0x6C's first instruction adds set BIND_ALL (0x10, never used by the game). It doesn't
bind anything itself: it points the late update at the copied fighter's custom, through the late
bind's own "other kind" override (0x027606C0: with +0x2E set it uses kind +0x28 instead of the
default +0x18), and sets the pending motion +0x1C to `motion`:
  [this+0x28] = kind; [this+0x2E] = 1; [this+0x1C] = motion
when the kind has a script for it (0x02E42518([0x102FF68C], kind, motion) != 0). The late update
then binds sets 2-3 to that kind's scripts and syncs them with the frame / "continue" flag
(+0x20 / +0x2C) the MSC's frame set (op 1) has stored by then. A motion change resets +0x2E / +0x28
/ +0x1C, so it lasts for this motion only. copy_custom_motion() calls it for a custom slot only,
after the motion change.

History: v1 bound sets 1-2 at once (set 1 is expression; the late update rebound 2-3 to Kirby's).
v2 bound 2-3 at once, synced them and set +0x1C = -2: it worked, but it ran before the MSC's
frame set, so when the motion restarted mid-move (landing: the copy helpers' ground / air swap
continue at the current frame, op 1 with flag 1 = +0x2C) the effects and sounds replayed from the
start (user).
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
        stmw r26, 0x18(r1)
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
        lis r3, 0x1030
        lwz r3, -0x974(r3)              # [0x102FF68C] script manager
        mr r4, r29
        mr r5, r30
        bl %(SCRIPT_OF)s
        mr. r28, r3
        stw r28, 0x10(r26)              # debug: the motion's script (0 = none)
        beq fx_done
        stw r29, 0x28(r31)              # the late bind's override kind
        li r0, 1
        stb r0, 0x2E(r31)               # use it
        stw r30, 0x1C(r31)              # and this motion (pending: the late update binds 2-3)
fx_done:
        lmw r26, 0x18(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
dbg:                                    # debug words (docs/native-notes.md): +0x6C calls, bind-all
        .word 0                         # calls, last motion, last kind, last script
        .word 0
        .word 0
        .word 0
        .word 0
"""


def assemble():
    a = Asm(CAVE)
    back = HOOK + 4
    a.asm(SOURCE % dict(BIND_ALL=BIND_ALL, BACK_HI=hex(ha(back)), BACK_LO=hex(lo(back)), SCRIPT_OF="0x%08X" % SCRIPT_OF))
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
