#!/usr/bin/env python3
"""TEMPORARY diagnostic executable for Supamario's Core Breaker v10 (fighters/supamario/README.md "Core Breaker v10"):
every call of HitModule's three body-state setters prints one OSReport line, so Cemu's log shows who made a fighter
invincible / intangible, with what, and from where. Not for the normal chain build. Prints rpx_patch.py arguments
(to combine with tools/diag_godfist_cave.py's, whose cave it doesn't touch).

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/diag_hitstate_cave.py --rpx IN.rpx)

The setters (HitModule vtable 0x10107774, docs/native-notes.md "State"): +0x9C 0x02C42F00 the status's body state
(MSC HitModule(0, state)), +0xEC 0x02C43188 invincible frames (HitModule(1, frames, x): the INVINCIBLE variable's
write, ACMD Body_State_Set State 1), +0xD4 0x02C43108 intangible frames (HitModule(2, frames)). Each one's first word
(`mflr r0`) becomes a branch to its stub, which prints

  `S4HS op=<0 state / 1 invincible / 2 intangible> v=<r4> a=<r5> lr=<its caller> lr2=<the caller's caller> m=<the
  module> n=<serial>`

with every register saved, runs the `mflr r0` and goes back to the setter's second word. Zero values of op 0 (the
status body state reset at every status change) are not printed. Cemu: Debug > Logging > "Coreinit Logging" on;
the lines go to log.txt.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

CAVE = 0x04BAD000               # free grown .text (zero in exe_v46k: 0x04BAC000-0x04BAE000; diag_godfist_cave.py
LIMIT = 0x04BAE000              # uses 0x04BAC000-0x04BAD000)
OSREPORT_VENEER = 0x0288B4D4    # the game's OSReport veneer (diag_crumbs_cave.py)
VENEER_WORDS = (0x9421FFF0, 0x93E1000C, None, None, 0x7FE903A6, 0x83E1000C, 0x38210010, 0x4E800420)
SETTERS = ((0, 0x02C42F00), (1, 0x02C43188), (2, 0x02C43108))     # (op, address)
MFLR_R0 = 0x7C0802A6
CRCLR_CR1EQ = 0x4CC63182
FMT = b'S4HS op=%d v=%d a=%d lr=%08X lr2=%08X m=%08X n=%d\n\0'


def branch(src, dst):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0
    return (18 << 26) | (off & 0x3FFFFFC)


def stub(op, back):
    """the stub for one setter: r3 the module, r4 / r5 its arguments, LR its caller"""
    skip0 = '\n        cmpwi r4, 0\n        beq hs%d_out' % op if op == 0 else ''
    fsave = '\n'.join('        stfd f%d, 0x%X(r1)' % (n, 0xA0 + 8 * n) for n in range(14))
    frest = '\n'.join('        lfd f%d, 0x%X(r1)' % (n, 0xA0 + 8 * n) for n in range(14))
    return """
hs%(op)d:%(skip0)s
        stwu r1, -0x140(r1)
        stmw r3, 0x10(r1)               # r3-r31
        mflr r0
        stw r0, 0x144(r1)               # its caller (restored below)
        mfcr r0
        stw r0, 8(r1)
        .word 0x7C0902A6                # mfctr r0
        stw r0, 0x88(r1)
        .word 0x7C0102A6                # mfxer r0
        stw r0, 0x8C(r1)
%(fsave)s
        mr r9, r3                       # the module
        mr r6, r5
        mr r5, r4
        li r4, %(op)d
        lwz r7, 0x144(r1)               # lr: the setter's caller
        lwz r8, 0x140(r1)               # the caller's frame (back chain)
        lwz r8, 4(r8)                   # lr2: the caller's caller (its saved LR)
        lis r12, hs_serial@ha
        lwz r10, hs_serial@l(r12)
        addi r10, r10, 1
        stw r10, hs_serial@l(r12)
        lis r3, hs_fmt@ha
        addi r3, r3, hs_fmt@l
        lis r12, 0x%(vh)X
        ori r12, r12, 0x%(vl)X           # the game's OSReport veneer
        mtctr r12
        .word 0x%(crclr)08X
        bctrl
%(frest)s
        lwz r0, 0x8C(r1)
        .word 0x7C0103A6                # mtxer r0
        lwz r0, 0x88(r1)
        .word 0x7C0903A6                # mtctr r0
        lwz r0, 8(r1)
        mtcrf 0xFF, r0
        lwz r0, 0x144(r1)
        mtlr r0
        lmw r3, 0x10(r1)
        addi r1, r1, 0x140
hs%(op)d_out:
        mflr r0                         # the setter's first word
        b 0x%(back)08X
""" % dict(op=op, skip0=skip0, fsave=fsave, frest=frest, vh=OSREPORT_VENEER >> 16, vl=OSREPORT_VENEER & 0xFFFF,
           crclr=CRCLR_CR1EQ, back=back)


def build(orig):
    """{address: word}, labels for the executable whose words orig(address) gives"""
    for i, w in enumerate(VENEER_WORDS):
        if w is not None:
            assert orig(OSREPORT_VENEER + 4 * i) == w, 'veneer word %d' % i
    for _op, at in SETTERS:
        assert orig(at) == MFLR_R0, 'setter 0x%08X: 0x%08X is not mflr r0' % (at, orig(at))
    a = Asm(CAVE)
    a.asm(''.join(stub(op, at + 4) for op, at in SETTERS) + """
hs_serial:
        .word 0
hs_fmt:
""")
    words = a.words()
    blob = FMT + b'\0' * (-len(FMT) % 4)
    words += list(struct.unpack('>%dI' % (len(blob) // 4), blob))
    assert CAVE + 4 * len(words) <= LIMIT
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    for x in out:
        assert orig(x) == 0, 'cave word 0x%08X not free' % x
    for op, at in SETTERS:
        out[at] = branch(at, a.addr('hs%d' % op))
    return out, a.labels


def main():
    import kind_expand as K
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', required=True)
    args = p.parse_args()
    words, _labels = build(K.Image(args.rpx).w)
    print(' '.join('0x%08X=0x%08X' % (x, w) for x, w in sorted(words.items())))


if __name__ == '__main__':
    main()
