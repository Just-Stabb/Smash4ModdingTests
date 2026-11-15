#!/usr/bin/env python3
"""TEMPORARY diagnostic for ACMD threads on fighters (exe_v46m, docs/acmd-extra-commands.md "Thread_Start"): the
fighter step call 0x02E40BF0 (`bl 0x02E408B8` in 0x02E40B90, r4 = the stack slot holding the accessor) goes through
a stub that prints, for the first LOG_N fighter steps of the session, one OSReport line:

  `S4TH step n=<n> r4=<hex> r1=<hex> acc=<hex> old=<1 / 0>`

old = whether exe_v46l's check on r4 (a heap pointer, 0x10000000-0x8FFFFFFF) would have let the thread runner in
(0: every fighter's threads were skipped, the bug exe_v46m fixes). Then it goes on to 0x02E408B8 as before. Use it
with tools/diag_godfist_cave.py's stub (the S4GF lines a thread's SET_FLOAT to 0x0F0003F0 + k prints):

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/diag_godfist_cave.py --rpx IN.rpx) \\
      $(python3 tools/diag_threads_cave.py --rpx IN.rpx)

Cemu: Debug > Logging > "Coreinit Logging" checked; the lines go to log.txt. Not for the normal chain build.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402
import diag_godfist_cave as G  # noqa: E402

CAVE = 0x04BAD000               # free grown .text after diag_godfist_cave.py's stub (0x04BAC000-0x04BAD000)
LIMIT = 0x04BAD400
CALL = 0x02E40BF0               # 0x02E40B90: bl 0x02E408B8 (the fighter's step: its threads, motion, ACMD)
STEP = 0x02E408B8
LOG_N = 6
FMT = b'S4TH step n=%d r4=%08X r1=%08X acc=%08X old=%d\n\0'


def bl(src, dst):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0
    return (18 << 26) | (off & 0x3FFFFFC) | 1


def build(orig):
    for i, w in enumerate(G.VENEER_WORDS):
        if w is not None:
            assert orig(G.OSREPORT_VENEER + 4 * i) == w, 'veneer word %d' % i
    assert orig(CALL) == bl(CALL, STEP), 'the fighter step call 0x%08X: 0x%08X' % (CALL, orig(CALL))
    a = Asm(CAVE)
    a.asm("""
dt_stub:                                # bl from 0x02E40BF0: r3 object, r4 -> accessor, r5; LR = 0x02E40BF4
        stwu r1, -0xA0(r1)
        mflr r0
        stw r0, 0xA4(r1)
        stmw r3, 0x10(r1)               # r3-r31 (0x10-0x83)
        mfcr r0
        stw r0, 8(r1)
        lis r12, dt_count@ha
        lwz r7, dt_count@l(r12)
        cmplwi r7, %(n)d
        bge dt_out
        addi r7, r7, 1
        stw r7, dt_count@l(r12)
        mr r5, r4                       # r4 (the slot holding the accessor)
        li r8, 1                        # old: exe_v46l's check (a heap pointer 0x10000000-0x8FFFFFFF)?
        addis r0, r5, -0x1000
        rlwinm. r0, r0, 0, 0, 0
        beq dt_heap
        li r8, 0
dt_heap:
        lwz r9, 0(r5)                   # the accessor
        mr r4, r7                       # n
        addi r6, r1, 0xA0               # the caller's r1
        mr r7, r9
        lis r3, dt_fmt@ha
        addi r3, r3, dt_fmt@l
        lis r12, 0x%(vh)X
        ori r12, r12, 0x%(vl)X           # the game's OSReport veneer
        mtctr r12
        .word 0x%(crclr)08X
        bctrl
dt_out:
        lwz r0, 8(r1)
        mtcrf 0xFF, r0
        lmw r3, 0x10(r1)
        lwz r0, 0xA4(r1)
        mtlr r0
        addi r1, r1, 0xA0
        b 0x%(step)08X
dt_count:
        .word 0
dt_fmt:
""" % dict(n=LOG_N, vh=G.OSREPORT_VENEER >> 16, vl=G.OSREPORT_VENEER & 0xFFFF, crclr=G.CRCLR_CR1EQ, step=STEP))
    words = a.words()
    blob = FMT + b'\0' * (-len(FMT) % 4)
    words += list(struct.unpack('>%dI' % (len(blob) // 4), blob))
    assert CAVE + 4 * len(words) <= LIMIT
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    for x in out:
        assert orig(x) == 0, 'cave word 0x%08X not free' % x
    out[CALL] = bl(CALL, a.addr('dt_stub'))
    return out, a.labels


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', required=True, help='the executable to patch (exe_v46m based)')
    args = p.parse_args()
    import kind_expand as K
    img = K.Image(args.rpx)
    words, _labels = build(img.w)
    print(' '.join('0x%08X=0x%08X' % kv for kv in sorted(words.items())))


if __name__ == '__main__':
    main()
