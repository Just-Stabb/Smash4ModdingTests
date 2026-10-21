#!/usr/bin/env python3
"""Per-frame code for a new stage slot (StageBaseCafe), first use: a moving-platform test on
NewStage01. Prints rpx_patch.py args (added after the standard build's).

New stage slots get the game's generic stage class (StageBaseCafe), which loads rigged collision
(lvd flag2) into links but never moves them; stage classes with gimmicks do it themselves each
frame (docs/minecraft-world.md "Stage code"). This adds that for one stage kind:

- the generic update (0x02D1CF9C) calls the base update with `bl 0x031415C8` at 0x02D1CFDC; that
  call goes to UPDATE, which makes it and then, if the stage's kind (stage + 0, KIND_AT) is KIND, adds
  the frame rate (f1, as the stage's animations do) to a frame counter wrapping at PERIOD and moves
  the collision of the link LINK (0x03142954(stage, LINK): the link whose subname is
  "LINK__<anything>__") to (x, y) = (AX * tri(p), AY * tri(p + 1/4)), p = counter / PERIOD,
  tri(q) = 1 - 4 |q - 1/2| (0x0315EF88(grounds, &(x, y), rotation 0): an offset from where the lvd
  puts it);
- the generic setup (0x02D1C65C, once a stage load) starts at RESET, which zeroes the counter,
  so the counter starts with the stage's animations.

tools/moving_platform_test.py makes the matching stage files (the same motion in a model
animation, the platform's rigged collision).

Space: grown code 0x04B7E000-0x04B7F000 (after stage_slot_cave.py's; within bl range of both
hooks). The counter is a word in it (the code region is writable in Cemu, as the stage-select
debug table was).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

CAVE = 0x04B7E000
LIMIT = 0x04B7F000
UPDATE_HOOK = 0x02D1CFDC       # bl 0x031415C8 in StageBaseCafe's update 0x02D1CF9C
BASE_UPDATE = 0x031415C8
SETUP = 0x02D1C65C             # StageBaseCafe setup (vtable +0x1C); first word stwu r1, -0x298(r1)
SETUP_FIRST = 'stwu r1, -0x298(r1)'
LINK_GROUNDS = 0x03142954      # (stage, name) -> the link's ground list or 0
MOVE_GROUNDS = 0x0315EF88      # (grounds, &(x, y), f1 rotation)

KIND = 0x80                    # NewStage01, normal play
KIND_AT = 0x00                 # the stage's kind: init (vtable +0x14, 0x02D1A760) copies the stage
                               # manager's settings (kind first) to the stage's start; +0xCC is
                               # the manager's +0xF4 (0 / 1 / -1), which the first test read
LINK = 'mctest'
PERIOD = 240.0                 # frames (4 s)
AX, AY = 25.0, 12.0            # half the swing, x and y


def motion(t):
    """the offset at frame t, as the cave computes it"""
    p = (t % PERIOD) / PERIOD

    def tri(q):
        return 1.0 - 4.0 * abs(q % 1.0 - 0.5)
    return AX * tri(p), AY * tri(p + 0.25)


def build():
    name = LINK.encode() + b'\0'
    name += b'\0' * (-len(name) % 4)
    a = Asm(CAVE)
    a.asm("""
reset:
        lis r12, data@ha
        addi r12, r12, data@l
        li r11, 0
        stw r11, 0(r12)
        %(first)s
        b 0x%(setup1)08X
update:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stw r31, 0x3C(r1)
        stw r30, 0x38(r1)
        stfd f31, 0x30(r1)
        mr r31, r3
        fmr f31, f1
        bl 0x%(base)08X
        stw r3, 0x10(r1)
        lwz r0, %(kind_at)d(r31)
        cmpwi r0, %(kind)d
        bne done
        lis r30, data@ha
        addi r30, r30, data@l
        lfs f0, 0(r30)
        fadds f0, f0, f31
        lfs f13, 4(r30)
        fcmpu cr0, f0, f13
        blt keep
        fsubs f0, f0, f13
keep:
        stfs f0, 0(r30)
        fdivs f1, f0, f13
        lfs f2, 8(r30)
        lfs f3, 12(r30)
        lfs f4, 16(r30)
        fsubs f5, f1, f2
        fabs f5, f5
        fmuls f5, f5, f3
        fsubs f5, f4, f5
        lfs f6, 20(r30)
        fmuls f5, f5, f6
        stfs f5, 0x18(r1)
        lfs f7, 24(r30)
        fadds f1, f1, f7
        fcmpu cr0, f1, f4
        blt nowrap
        fsubs f1, f1, f4
nowrap:
        fsubs f5, f1, f2
        fabs f5, f5
        fmuls f5, f5, f3
        fsubs f5, f4, f5
        lfs f6, 28(r30)
        fmuls f5, f5, f6
        stfs f5, 0x1C(r1)
        mr r3, r31
        addi r4, r30, 36
        bl 0x%(lookup)08X
        cmpwi r3, 0
        beq done
        addi r4, r1, 0x18
        lfs f1, 32(r30)
        bl 0x%(move)08X
done:
        lwz r3, 0x10(r1)
        lfd f31, 0x30(r1)
        lwz r30, 0x38(r1)
        lwz r31, 0x3C(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr
data:
        .float 0
        .float %(period)r
        .float 0.5
        .float 4.0
        .float 1.0
        .float %(ax)r
        .float 0.25
        .float %(ay)r
        .float 0
""" % dict(first=SETUP_FIRST, setup1=SETUP + 4, base=BASE_UPDATE, kind=KIND, lookup=LINK_GROUNDS,
           move=MOVE_GROUNDS, period=PERIOD, ax=AX, ay=AY, kind_at=KIND_AT))
    for i in range(0, len(name), 4):
        a.asm('.word 0x%08X' % int.from_bytes(name[i:i + 4], 'big'))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT
    hooks = Asm(UPDATE_HOOK)
    hooks.asm('bl 0x%08X' % a.addr('update'))
    setup = Asm(SETUP)
    setup.asm('b 0x%08X' % a.addr('reset'))
    return a, words, [(UPDATE_HOOK, hooks.words()[0]), (SETUP, setup.words()[0])]


def main():
    a, words, hooks = build()
    out = ['grow:0x%08X' % LIMIT]
    out += ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % h for h in hooks]
    print(' '.join(out))
    sys.stderr.write('stage script: %d words, counter at 0x%08X\n' % (len(words), a.addr('data')))


if __name__ == '__main__':
    main()
