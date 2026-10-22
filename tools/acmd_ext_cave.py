#!/usr/bin/env python3
"""New ACMD commands (native): prints rpx_patch.py arguments.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx ... $(python3 tools/acmd_ext_cave.py)

How the game runs ACMD (docs/native-notes.md "ACMD commands: dispatch"): when a script is loaded,
0x02BEE1CC / 0x02BEE2F8 replace each command's CRC (the first word of each command) by its index,
from the binary search 0x02BEE154 over the sorted {crc, index} table 0x100FAAB8 (584 pairs), and
step to the next command with the size table 0x100FA198 (words, header included: CMD_SIZES). The
interpreter 0x02BEE63C then calls handler[index] (table 0x10350ED8, at 0x02BEE84C) as
handler(r3 module accessor, r4, r5 script state, r6 (+8: execute flag), r7 the parameters); a handler
moves the script on itself (state +4 += its size in bytes, when state +8 is -1) and returns 2.

New commands get indices NEW_BASE.. (584 + k):
- LOOKUP (0x02BEE1BC, the binary search's not-found `li r3, -1`): look the CRC up in our table.
- SIZE1 / SIZE2 (0x02BEE2C0 / 0x02BEE3C0, the two loaders' size reads): an index >= NEW_BASE reads
  our size table.
- FETCH (0x02BEE84C, the interpreter's handler read): an index >= NEW_BASE reads our handler table.

Commands (CRC = zlib.crc32 of the name as written, like the game's own):
- Extra_Special_Hitbox: Special_Hitbox's 41 parameters, then EXTRA (below).
- Extra_Extended_Special_Hitbox: Extended_Special_Hitbox's 43, then EXTRA.
  The handler calls the original handler (which makes the hitbox and steps over its own size), steps
  over the extra words too, and when the command runs (execute flag) records the extras for the
  hitbox's AttackModule slot ([accessor +0x50] +0x40 + ID * 0x84): an entry of the extras table
  (ENTRIES, round robin, reused for the same slot), with the slot's data +0x20..+0x2C (angle,
  KBG, FKB, BKB) and +0x3C (bone) as a check, and the entry's number tagged into the slot's data
  +0x66 (a halfword no hitbox builder writes: TAG | n). ext_find(data) gives the entry back at hit
  time only if the tag, the slot and the check words all still match (a later plain hitbox in that
  slot has different data / tag).
EXTRA = HitstunMul, HitstopMul, HitstopFrames, SelfHitstopMul, SelfHitstopFrames, DIMul: multipliers
<= 0 mean 1 (unchanged), frames 0 mean "computed" (> 0 replaces the hitstop).
The hit-time hooks that use them are in this file too (HIT_* below), see docs/acmd-extra-commands.md.
"""
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

CAVE = 0x04B90000
LIMIT = 0x04B94000
TABLE = 0x04B92000               # extras entries (zero at load)
ENTRIES = 128
ENTRY = 0x30
TAG = 0xEC00
TAG_OFF = 0x66

LOOKUP = 0x02BEE1BC              # li r3, -1 (then blr)
SIZE1 = 0x02BEE2C0               # slwi r10, r3, 2 / stwx r3, r28, r5 / lwzx r0, r10, r4 -> 0x02BEE2CC
SIZE2 = 0x02BEE3C0               # slwi r11, r3, 2 / stwx r3, r28, r5 / lwzx r12, r11, r30 -> 0x02BEE3CC
FETCH = 0x02BEE84C               # slwi r6, r7, 2 / lwzx r0, r6, r29 -> 0x02BEE854 (r12 is live)
NEW_BASE = 584

SPECIAL_HITBOX = 0x02BDBB20      # handler, size 42
EXT_SPECIAL_HITBOX = 0x02BDD46C  # handler, size 44
N_EXTRA = 6

COMMANDS = [                     # name, size (words, header included), handler label, base handler
    ('Extra_Special_Hitbox', 42 + N_EXTRA, 'h_extra', SPECIAL_HITBOX),
    ('Extra_Extended_Special_Hitbox', 44 + N_EXTRA, 'h_extra_ext', EXT_SPECIAL_HITBOX),
]


def crc(name):
    return zlib.crc32(name.encode()) & 0xFFFFFFFF


def build():
    a = Asm(CAVE)
    n = len(COMMANDS)
    # --- dispatch -----------------------------------------------------------------------------
    a.asm("""
lookup:                                 # r3 = CRC not in the game's table
        lis r12, cmd_crcs@ha
        addi r12, r12, cmd_crcs@l
        li r11, 0
lk_loop:
        cmpwi r11, %(n)d
        bge lk_none
        slwi r0, r11, 2
        lwzx r0, r12, r0
        cmplw r0, r3
        beq lk_found
        addi r11, r11, 1
        b lk_loop
lk_found:
        addi r3, r11, %(base)d
        blr
lk_none:
        li r3, -1
        blr

size1:
        slwi r10, r3, 2
        stwx r3, r28, r5
        addi r0, r3, -%(base)d
        cmplwi r0, %(n)d
        bge s1_orig
        slwi r10, r0, 2
        addis r10, r10, cmd_sizes@ha     # (addis rD, r0, ... would read r0 as 0)
        lwz r0, cmd_sizes@l(r10)
        slwi r10, r3, 2
        b 0x%(s1back)08X
s1_orig:
        lwzx r0, r10, r4
        b 0x%(s1back)08X

size2:
        slwi r11, r3, 2
        stwx r3, r28, r5
        addi r12, r3, -%(base)d
        cmplwi r12, %(n)d
        bge s2_orig
        slwi r12, r12, 2
        addis r12, r12, cmd_sizes@ha
        lwz r12, cmd_sizes@l(r12)
        b 0x%(s2back)08X
s2_orig:
        lwzx r12, r11, r30
        b 0x%(s2back)08X

fetch:
        addi r6, r7, -%(base)d
        cmplwi r6, %(n)d
        bge f_orig
        slwi r6, r6, 2
        addis r6, r6, cmd_handlers@ha
        lwz r0, cmd_handlers@l(r6)
        b 0x%(fback)08X
f_orig:
        slwi r6, r7, 2
        lwzx r0, r6, r29
        b 0x%(fback)08X
""" % dict(n=n, base=NEW_BASE, s1back=SIZE1 + 12, s2back=SIZE2 + 12, fback=FETCH + 8))

    # --- Extra hitbox handlers ----------------------------------------------------------------
    for _name, size, label, base in COMMANDS[:2]:
        a.asm("""
%(label)s:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r27, 0x1C(r1)
        mr r31, r3                      # accessor
        mr r30, r5                      # script state
        mr r29, r6
        mr r28, r7                      # parameters
        bl 0x%(base)08X                 # the hitbox itself; steps over its own words
        mr r27, r3
        lbz r0, 8(r29)                  # executed (not skipped)?
        cmpwi r0, 0
        beq %(label)s_step
        mr r3, r31
        mr r4, r28
        addi r5, r28, %(extra)d         # the extra parameters
        bl ext_record
%(label)s_step:
        lwz r0, 8(r30)
        cmpwi r0, -1
        bne %(label)s_out
        lwz r11, 4(r30)
        addi r11, r11, %(extra_bytes)d
        stw r11, 4(r30)
%(label)s_out:
        mr r3, r27
        lmw r27, 0x1C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
""" % dict(label=label, base=base, extra=4 * (size - N_EXTRA - 1), extra_bytes=4 * N_EXTRA))

    # ext_record(r3 accessor, r4 params (ID first), r5 extras): find the slot, take an entry, copy.
    a.asm(("""
ext_record:
""" + chk('r3', 'er_out') + """
        lwz r6, 0x50(r3)                # AttackModule
""" + chk('r6', 'er_out') + """
        lwz r7, 0(r4)                   # ID
        cmplwi r7, 7
        bgt er_out
        lwz r8, 0x40(r6)                # slots
""" + chk('r8', 'er_out') + """
        mulli r7, r7, 0x84
        add r8, r8, r7                  # slot (its data)
        lis r9, table@ha
        addi r9, r9, table@l
        lhz r10, %(tag)d(r8)            # an entry this slot had: reuse it
        rlwinm r0, r10, 0, 16, 23
        cmplwi r0, %(TAG)d
        bne er_new
        rlwinm r10, r10, 0, 24, 31
        cmplwi r10, %(entries)d
        bge er_new
        mulli r11, r10, %(entry)d
        add r11, r9, r11
        lwz r0, 0(r11)
        cmplw r0, r8
        beq er_have
er_new:
        lis r12, next_entry@ha
        lwz r10, next_entry@l(r12)
        addi r0, r10, 1
        cmplwi r0, %(entries)d
        blt er_wrap
        li r0, 0
er_wrap:
        stw r0, next_entry@l(r12)
        mulli r11, r10, %(entry)d
        add r11, r9, r11
er_have:                                # r10 = entry number, r11 = entry, r8 = slot
        stw r8, 0(r11)
        lwz r0, 0x20(r8)
        stw r0, 4(r11)
        lwz r0, 0x24(r8)
        stw r0, 8(r11)
        lwz r0, 0x28(r8)
        stw r0, 0xC(r11)
        lwz r0, 0x2C(r8)
        stw r0, 0x10(r11)
        lwz r0, 0x3C(r8)
        stw r0, 0x2C(r11)
        lis r12, one@ha
        lfs f0, one@l(r12)              # 1.0
        lfs f2, zero@l(r12)             # 0.0 (next to it)
""" + mul('0', '0x14', 'hs') + mul('4', '0x18', 'hp') + """
        lwz r0, 8(r5)                   # hitstop frames
        stw r0, 0x1C(r11)
""" + mul('0xC', '0x20', 'sp') + """
        lwz r0, 0x10(r5)                # self hitstop frames
        stw r0, 0x24(r11)
""" + mul('0x14', '0x28', 'di') + """
        ori r0, r10, %(TAG)d
        sth r0, %(tag)d(r8)
er_out:
        blr
""") % dict(tag=TAG_OFF, TAG=TAG, entries=ENTRIES, entry=ENTRY))
    # ext_find(r3 data) -> r3 entry or 0. Leaf: r0, r11, r12.
    a.asm("""
ext_find:
        andi. r0, r3, 3
        bne ef_none
        addis r0, r3, -0x1000
        rlwinm. r0, r0, 0, 0, 0
        bne ef_none
        lhz r11, %(tag)d(r3)
        rlwinm r0, r11, 0, 16, 23
        cmplwi r0, %(TAG)d
        bne ef_none
        rlwinm r11, r11, 0, 24, 31
        cmplwi r11, %(entries)d
        bge ef_none
        mulli r11, r11, %(entry)d
        lis r12, table@ha
        addi r12, r12, table@l
        add r11, r12, r11
        lwz r0, 0(r11)
        cmplw r0, r3
        bne ef_none
        lwz r0, 0x20(r3)
        lwz r12, 4(r11)
        cmplw r0, r12
        bne ef_none
        lwz r0, 0x24(r3)
        lwz r12, 8(r11)
        cmplw r0, r12
        bne ef_none
        lwz r0, 0x28(r3)
        lwz r12, 0xC(r11)
        cmplw r0, r12
        bne ef_none
        lwz r0, 0x2C(r3)
        lwz r12, 0x10(r11)
        cmplw r0, r12
        bne ef_none
        lwz r0, 0x3C(r3)
        lwz r12, 0x2C(r11)
        cmplw r0, r12
        bne ef_none
        mr r3, r11
        blr
ef_none:
        li r3, 0
        blr
one:
        .float 1.0
zero:
        .float 0.0
next_entry:
        .word 0
""" % dict(tag=TAG_OFF, TAG=TAG, entries=ENTRIES, entry=ENTRY))

    a.asm('cmd_crcs:\n' + ''.join('        .word 0x%08X\n' % crc(c[0]) for c in COMMANDS))
    a.asm('cmd_sizes:\n' + ''.join('        .word %d\n' % c[1] for c in COMMANDS))
    a.asm('cmd_handlers:\n' + ''.join('        .word 0x%08X\n' % a.addr(c[2]) for c in COMMANDS))
    a.labels['table'] = TABLE
    words = a.words()
    assert CAVE + 4 * len(words) <= TABLE, hex(CAVE + 4 * len(words))
    hooks = {LOOKUP: b(LOOKUP, a.addr('lookup')), SIZE1: b(SIZE1, a.addr('size1')),
             SIZE2: b(SIZE2, a.addr('size2')), FETCH: b(FETCH, a.addr('fetch'))}
    return a, words, hooks


def mul(src, dst, k):
    """copy the float multiplier at src(r5) to dst(r11); <= 0 or NaN -> 1.0 (f0 = 1.0, f2 = 0.0)"""
    return """
        lfs f1, %s(r5)
        fcmpu cr1, f1, f2
        bgt cr1, er_%s
        fmr f1, f0
er_%s:
        stfs f1, %s(r11)""" % (src, k, k, dst)


def chk(reg, fail):
    """branch to fail unless reg is a word-aligned pointer in 0x10000000-0x8FFFFFFF"""
    return """
        addis r0, %s, -0x1000
        rlwinm. r0, r0, 0, 0, 0
        bne %s
        andi. r0, %s, 3
        bne %s""" % (reg, fail, reg, fail)


def b(at, to):
    off = to - at
    assert -0x2000000 <= off < 0x2000000, (hex(at), hex(to))
    return 0x48000000 | (off & 0x3FFFFFC)


def main():
    a, words, hooks = build()
    out = ['grow:0x%08X' % LIMIT]
    out += ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % kv for kv in sorted(hooks.items())]
    print(' '.join(out))
    sys.stderr.write('acmd ext: %d words, %s\n' % (len(words), ', '.join(
        '%s 0x%08X index %d' % (c[0], crc(c[0]), NEW_BASE + i) for i, c in enumerate(COMMANDS))))


if __name__ == '__main__':
    main()
