#!/usr/bin/env python3
"""TEMPORARY diagnostic executable for Supamario's Super God Fist (fighters/supamario/README.md "Super God Fist v4"):
a write to a diag variable 0x0F0003F0 + k (k 0-15, from ACMD SET_FLOAT / SUB_FLOAT_2 or MSC WorkModule) prints one
OSReport line, so Cemu's log shows what the move did in game. Not for the normal chain build. Prints rpx_patch.py
arguments.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/diag_godfist_cave.py --rpx IN.rpx)

Line: `S4GF k=<k> v=<value, whole> c=<value x 100> n=<serial>` (Cemu: Debug > Logging > "Coreinit Logging"
checked; the lines go to log.txt). The k numbers are tools/supamario_godfist_build.py's D_* (its --diag build writes
them; README "Diagnostics" lists them).

Where: the IDs 0x0F0003C9-0x0F0003FF are acmd_ext_cave.py's "reads 0, writes do nothing" (hv_var: index > 0x3C8 ->
hvv_zero -> `b ue_zero`; r1 = user_entry's frame, the written float at +0x18, r29 = 1 for a write, r30 = the index,
r27-r31 restored by ue_zero itself). The `b ue_zero` at hvv_zero (HVV_ZERO, found by its neighbours in the
executable) is aimed at `diag_stub`, which for a write of 0x3F0-0x3FF calls the game's OSReport veneer
(OSREPORT_VENEER, as tools/diag_crumbs_cave.py) with every volatile register saved, then goes on to ue_zero as
before. Reads and every other ID: unchanged (the stub only branches on).
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

CAVE = 0x04BAC000               # free grown .text (zero in exe_v45h / exe_v46g: 0x04BA97B4-0x04BAE000)
LIMIT = 0x04BAD000
OSREPORT_VENEER = 0x0288B4D4    # the game's OSReport veneer (diag_crumbs_cave.py)
VENEER_WORDS = (0x9421FFF0, 0x93E1000C, None, None, 0x7FE903A6, 0x83E1000C, 0x38210010, 0x4E800420)
HV_VAR_SIG = (0x281E03C0, None, 0x281E03C8, None)       # cmplwi r30, 0x3C0; blt; cmplwi r30, 0x3C8; bgt hvv_zero
DIAG_LO, DIAG_HI = 0x3F0, 0x3FF
CRCLR_CR1EQ = 0x4CC63182
FMT = b'S4GF k=%d v=%d c=%d n=%d\n\0'


def find_hv(orig, lo=0x04B90000, hi=0x04BA0000):
    """(hv_var, hvv_zero, ue_zero): hv_var by its first four words; hvv_zero = its `bgt` target, a `b ue_zero`"""
    for x in range(lo, hi, 4):
        if orig(x) == HV_VAR_SIG[0] and orig(x + 8) == HV_VAR_SIG[2]:
            bgt = orig(x + 12)
            assert bgt >> 26 == 16 and (bgt >> 21) & 31 == 12 and (bgt >> 16) & 31 == 1, hex(bgt)
            off = bgt & 0xFFFC
            off -= 0x10000 if off & 0x8000 else 0
            zero = x + 12 + off
            b = orig(zero)
            assert b >> 26 == 18 and not b & 3, 'hvv_zero 0x%08X: 0x%08X is not a b' % (zero, b)
            boff = b & 0x3FFFFFC
            boff -= 0x4000000 if boff & 0x2000000 else 0
            return x, zero, zero + boff
    raise ValueError('hv_var not found')


def branch(src, dst):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0
    return (18 << 26) | (off & 0x3FFFFFC)


def build(orig):
    """{address: word} for the executable whose words orig(address) gives"""
    for i, w in enumerate(VENEER_WORDS):
        if w is not None:
            assert orig(OSREPORT_VENEER + 4 * i) == w, 'veneer word %d' % i
    _hv, hvv_zero, ue_zero = find_hv(orig)
    a = Asm(CAVE)
    a.asm("""
diag_stub:
        cmpwi r29, 0
        beq ds_on
        cmplwi r30, %(lo)d
        blt ds_on
        cmplwi r30, %(hi)d
        bgt ds_on
        stwu r1, -0x140(r1)
        mflr r0
        stw r0, 0x144(r1)
        stmw r3, 0x10(r1)               # r3-r31 (0x10-0x83)
        mfcr r0
        stw r0, 8(r1)
        .word 0x7C0902A6                # mfctr r0
        stw r0, 0x88(r1)
        .word 0x7C0102A6                # mfxer r0
        stw r0, 0x8C(r1)
%(fsave)s
        lfs f1, 0x158(r1)               # the written value (user_entry's frame +0x18)
        fctiwz f2, f1
        stfd f2, 0x90(r1)
        lwz r5, 0x94(r1)
        lis r12, hundred@ha
        lfs f2, hundred@l(r12)
        fmuls f1, f1, f2
        fctiwz f2, f1
        stfd f2, 0x90(r1)
        lwz r6, 0x94(r1)
        addi r4, r30, -%(lo)d
        lis r12, serial@ha
        lwz r7, serial@l(r12)
        addi r7, r7, 1
        stw r7, serial@l(r12)
        lis r3, fmt@ha
        addi r3, r3, fmt@l
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
        lmw r3, 0x10(r1)
        lwz r0, 0x144(r1)
        mtlr r0
        addi r1, r1, 0x140
ds_on:
        b 0x%(ue)08X
hundred:
        .float 100.0
serial:
        .word 0
fmt:
""" % dict(lo=DIAG_LO, hi=DIAG_HI, vh=OSREPORT_VENEER >> 16, vl=OSREPORT_VENEER & 0xFFFF, crclr=CRCLR_CR1EQ,
           ue=ue_zero, fsave='\n'.join('        stfd f%d, 0x%X(r1)' % (n, 0xA0 + 8 * n) for n in range(14)),
           frest='\n'.join('        lfd f%d, 0x%X(r1)' % (n, 0xA0 + 8 * n) for n in range(14))))
    words = a.words()
    blob = FMT + b'\0' * (-len(FMT) % 4)
    words += list(struct.unpack('>%dI' % (len(blob) // 4), blob))
    assert CAVE + 4 * len(words) <= LIMIT
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    for x in out:
        assert orig(x) == 0, 'cave word 0x%08X not free' % x
    out[hvv_zero] = branch(hvv_zero, a.addr('diag_stub'))
    return out, a.labels, (hvv_zero, ue_zero)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', required=True, help='the executable to patch (exe_v45h / exe_v46g based)')
    args = p.parse_args()
    import kind_expand as K
    img = K.Image(args.rpx)
    words, _labels, _at = build(img.w)
    print(' '.join('0x%08X=0x%08X' % kv for kv in sorted(words.items())))


if __name__ == '__main__':
    main()
