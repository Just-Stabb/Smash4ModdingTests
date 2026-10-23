#!/usr/bin/env python3
"""Stage select: the form switch starts on Omega; new stages (cosmetic ids from FIRST_NEW, e.g.
Minecraft World 0x38) are picked in their normal form unless the switch was flipped by hand.
Prints rpx_patch.py arguments.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx ... $(python3 tools/stage_omega_cave.py)

The switch (StageSelectScene +0x160, docs/stage-expansion.md "Normal / Omega"): state +8 is 0 normal,
1 Omega ("terminate"), 2 My Music; 0x0298C948 is the state shown, 0x0298C984(switch, state, sound)
sets it. The scene's setup (0x022421F4) starts it from the player's remembered form (the rule's
per-player block, +0x74 + player * 0x80, byte 2: 1 normal, 0 Omega): 0x02242ABC .. 0x02242AE0.
0x0298CA84, the switch's input handler, calls 0x0298C984 every frame with the state it wants
(changed by the button), and so does a touch path (0x022466B8). The confirm (0x02245B18(scene,
stage, ..)) takes the form from the switch, `form = !isOmega(scene)` (0x022453D8, at 0x02245BB0;
r29 = the stage), into the block it passes to the match setup (0x030197FC / 0x02FFC604).

Patches:
- 0x02242AC8 `beq` -> `b`: the normal-play start always takes the Omega branch (state 1);
  0x02242AD8 `li r4, 1` -> `bl entry` (r4 = 1, and clears `flipped`).
- 0x0298CBEC / 0x022466B8 `bl 0x0298C984` -> `bl toggle`: sets `flipped` when the state asked for
  differs from the current one, then goes on to 0x0298C984.
- 0x02245BB0 `bl 0x022453D8` -> `bl confirm`: isOmega, but 0 (normal) for a stage id in
  FIRST_NEW..0xC7 while `flipped` is clear.
The code is in the grown space; the patched calls go through `b` trampolines at TRAMPOLINES, and the
code reaches the game's functions with mtctr / bctr (also out of reach from there).
Modes 3 / 4 (Omega-only / normal-only rule sets, scene +0x1A4) keep the game's start state.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

CAVE = 0x04B84800               # free: trait_badge_cave.py ends at 0x04B84800, then free up to 0x04B88000 (kind_expand.py's old space)
TRAMPOLINES = 0x037EE3F4        # 3 words (position_vars_cave.py's CAVE2 stops here): the grown space is out of
                                # bl reach (32 MB) of the stage select code, the Havok cave is within it of both
LIMIT = 0x04B84900
GROW = 0x04B84900
FIRST_NEW = 0x38                # stage_slot_cave.py's new cosmetic ids start here (0xC8+ are menus)

START_BRANCH = 0x02242AC8       # beq 0x02242AD8 (remembered form 0 -> Omega)
START_OMEGA = 0x02242AD8        # li r4, 1
TOGGLE_CALLS = (0x0298CBEC, 0x022466B8)
CONFIRM_CALL = 0x02245BB0
SET_STATE = 0x0298C984
IS_OMEGA = 0x022453D8

ORIGINAL = {
    START_BRANCH: 0x41820010,
    START_OMEGA: 0x38800001,
    CONFIRM_CALL: 0x4BFFF829,
    0x0298CBEC: 0x4BFFFD99,
    0x022466B8: 0x487462CD,
}


def build():
    a = Asm(CAVE)
    a.asm('''
    entry:                          # the switch's start state: Omega; nothing flipped yet
            li r4, 1
            lis r12, flipped@ha
            li r11, 0
            stb r11, flipped@l(r12)
            blr
    toggle:                         # r3 switch, r4 the state asked for, r5 sound
            lwz r12, 8(r3)
            cmplw r12, r4
            beq same
            lis r12, flipped@ha
            li r11, 1
            stb r11, flipped@l(r12)
    same:   lis r12, %(set_state_hi)d
            ori r12, r12, %(set_state_lo)d
            mtctr r12
            bctr
    confirm:                        # isOmega(r3 scene); r29 = the stage being confirmed
            mflr r0
            stwu r1, -16(r1)
            stw r0, 20(r1)
            lis r12, %(is_omega_hi)d
            ori r12, r12, %(is_omega_lo)d
            mtctr r12
            bctrl
            cmplwi r29, %(first)d
            blt done
            cmplwi r29, 0xC8
            bge done
            lis r12, flipped@ha
            lbz r12, flipped@l(r12)
            cmpwi r12, 0
            bne done
            li r3, 0                # a new stage: its normal form unless the switch was flipped
    done:   lwz r0, 20(r1)
            mtlr r0
            addi r1, r1, 16
            blr
    flipped: .word 0
    ''' % dict(set_state_hi=SET_STATE >> 16, set_state_lo=SET_STATE & 0xFFFF,
           is_omega_hi=IS_OMEGA >> 16, is_omega_lo=IS_OMEGA & 0xFFFF, first=FIRST_NEW))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT
    patches = {CAVE + 4 * i: w for i, w in enumerate(words)}

    def branch(at, to, link):
        off = to - at
        assert -0x2000000 <= off < 0x2000000, (hex(at), hex(to))
        return 0x48000000 | (off & 0x3FFFFFC) | link
    tramp = {}
    for i, name in enumerate(('entry', 'toggle', 'confirm')):
        tramp[name] = TRAMPOLINES + 4 * i
        patches[tramp[name]] = branch(tramp[name], a.addr(name), 0)
    patches[START_BRANCH] = 0x48000010                      # b 0x02242AD8
    patches[START_OMEGA] = branch(START_OMEGA, tramp['entry'], 1)
    for at in TOGGLE_CALLS:
        patches[at] = branch(at, tramp['toggle'], 1)
    patches[CONFIRM_CALL] = branch(CONFIRM_CALL, tramp['confirm'], 1)
    return a, patches


def args(patches):
    return ['grow:0x%08X' % GROW] + ['0x%08X=0x%08X' % kv for kv in sorted(patches.items())]


def main():
    _a, patches = build()
    print(' '.join(args(patches)))
    sys.stderr.write('stage select: Omega by default, new stages (0x%X+) normal unless flipped; cave 0x%08X\n'
                     % (FIRST_NEW, CAVE))


if __name__ == '__main__':
    main()
