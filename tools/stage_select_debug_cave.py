#!/usr/bin/env python3
"""DEBUG ONLY: why a stage isn't on the stage select. Prints rpx_patch.py args, added after the
standard build's (after tools/stage_slot_cave.py, whose grow: this extends).

The stage select's list builder (0x0298FAC8) loops over every ui_stage_db.bin entry (index =
cosmetic id), skips Random, asks 0x0301BA8C(id, mode) whether the stage is available (mode 4, or 1
for a DLC-marked entry) and files it on page 1 or page 2. The hook on that call (0x0298FBCC) runs
it as before and also records, for every id, the result and each check of the stage database
wrapper (static object 0x1054F408, vtable 0x100BAAFC) in a table, one byte an id:

  +0x000 calls (word)          +0x004 stage database count (word)
  +0x008 ui_sound_db count     +0x00C the list builder's database ([0x102F7188] + 4)
  +0x100 + id: available (0x10 | result: 0x11 yes, 0x10 no; 0 = never asked)
  +0x200 + id: mode
  +0x300 + id: exists (+0x1C: shown on the select, song list, DLC owned)
  +0x400 + id: DLC-marked (+0x24, byte +0x0C)
  +0x500 + id: +0x4C (DLC content record)   +0x600 + id: unlocked (+0x6C)   +0x700 + id: +0x74
(each check byte is 0x10 | result; v5 records +0x500 only)
v5 (NAMES), for id 0x38: +0x10 name list built (byte), +0x14 its records, +0x18 its count,
+0x1C the empty name, +0x20 / +0x24 / +0x28 record 0x38 (name, ?, hash), +0x40 what the name
lookup 0x0293DCE0 returns for 0x38, +0x50 its first 12 characters.
and, with ENTRIES (v2; no room for it next to all the checks), the database entry at that index (0x54 bytes from [[ [0x102F7188] + 4 ] + 0xC]):
  +0x800 + id: its id (low byte)   +0x900: +0x04 shown   +0xA00: +0x0C page 2 / DLC   +0xB00: +0x0D
  +0xC00: its stage kind (low byte)

v1 result (user): while the stage select ran, the database had 0x86 entries (the file: 0x4F) and
the entry at 0x38 wasn't the file's 0x38 (not DLC-marked, not shown). v2 (user, the file installed):
79 entries, the file's, 0x38 the new stage, exists / page 2 / unlocked passed and it was still
dropped: the +0x4C DLC content record (stage_slot_cave.py patches it now). v3 records all checks.

The table is at TABLE (in Cemu: Debug > Memory, go to the address). Compare id 0x38 (the new
stage) with 0x37 (Umbra, page 2) and 0x01 (Battlefield). The code sits in the Havok cave's free
words (the hook is too far from the grown code space for a branch); the table in the grown code
space after stage_slot_cave.py's.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

CAVE = 0x037EE430           # free: 0x037EE428-0x037EE5A0 (copy_held_cave.py from 0x037EE5A0); copy_custom_cave.py's
                            # SPAWNERS caves now use 0x037EE428-0x037EE4DC: a debug build only, not with the standard one
LIMIT = 0x037EE5A0
TABLE = 0x04B7E000          # grown code space after stage_slot_cave.py's (ends at 0x04B7E000)
GROW_END = 0x04B7F000
HOOK = 0x0298FBCC           # bl 0x0301BA8C (r3 id, r4 mode)
AVAILABLE = 0x0301BA8C
WRAPPER = 0x1054F408
CHECKS = [(0x500, 0x0293F280)]
NAMES = True                # v5: the database's name list and the name lookup, for id 0x38
ENTRIES = False             # v2's entry dump (+0x800-+0xCFF); no room next to all the checks


def build():
    src = """
ssdbg:                                  # called instead of 0x0301BA8C(r3 id, r4 mode)
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        andi. r3, r3, 0xFF
        stw r3, 8(r1)
        stw r4, 0xC(r1)
        bl 0x%(AVAILABLE)08X
        stw r3, 0x10(r1)                # result, returned at the end
        lis r11, 0x%(THI)04X
        ori r11, r11, 0x%(TLO)04X
        lwz r12, 0(r11)
        addi r12, r12, 1
        stw r12, 0(r11)
        lwz r12, 8(r1)
        add r10, r11, r12
        stw r10, 0x14(r1)               # table + id
        lwz r9, 0x10(r1)
        ori r9, r9, 0x10
        stb r9, 0x100(r10)
        lwz r9, 0xC(r1)
        stb r9, 0x200(r10)
""" % dict(AVAILABLE=AVAILABLE, THI=TABLE >> 16, TLO=TABLE & 0xFFFF)
    for off, fn in CHECKS:
        src += """
        lis r3, 0x%(WHI)04X
        ori r3, r3, 0x%(WLO)04X
        lwz r4, 8(r1)
        bl 0x%(FN)08X
        andi. r3, r3, 1
        ori r3, r3, 0x10
        lwz r10, 0x14(r1)
        stb r3, 0x%(OFF)X(r10)
""" % dict(WHI=WRAPPER >> 16, WLO=WRAPPER & 0xFFFF, FN=fn, THI=TABLE >> 16, TLO=TABLE & 0xFFFF, OFF=off)
    src += """
""" + ("""
        lis r12, 0x102F
        lwz r12, 0x7188(r12)
        lwz r12, 4(r12)                 # the database
        lwz r9, 0xC(r12)                # its entries
        lwz r4, 8(r1)
        mulli r4, r4, 0x54
        add r9, r9, r4
        lwz r10, 0x14(r1)
        lwz r4, 0(r9)
        stb r4, 0x800(r10)
        lbz r4, 4(r9)
        stb r4, 0x900(r10)
        lbz r4, 0xC(r9)
        stb r4, 0xA00(r10)
        lbz r4, 0xD(r9)
        stb r4, 0xB00(r10)
        lbz r4, 0x13(r9)
        stb r4, 0xC00(r10)

""" if ENTRIES else "") + ("""
        lwz r4, 8(r1)
        cmplwi r4, 0x38
        bne names_out
        lis r11, 0x%(THI)04X
        ori r11, r11, 0x%(TLO)04X
        lis r12, 0x1034
        lwz r9, 0x610(r12)              # the empty name
        stw r9, 0x1C(r11)
        lis r12, 0x102F
        lwz r12, 0x7188(r12)
        lwz r12, 4(r12)                 # the database
        lbz r9, 0x38(r12)               # its name list: built, records, count
        stw r9, 0x10(r11)
        lwz r9, 0x3C(r12)
        stw r9, 0x14(r11)
        lwz r10, 0x40(r12)
        stw r10, 0x18(r11)
        cmplw r4, r10
        bge names_call
        mulli r4, r4, 0xC
        add r9, r9, r4
        lwz r4, 0(r9)                   # record 0x38: name, +4, hash
        stw r4, 0x20(r11)
        lwz r4, 4(r9)
        stw r4, 0x24(r11)
        lwz r4, 8(r9)
        stw r4, 0x28(r11)
names_call:
        li r3, 0x38
        bl 0x0293DCE0                   # the name lookup (stage_slot_cave.py's table)
        lis r11, 0x%(THI)04X
        ori r11, r11, 0x%(TLO)04X
        stw r3, 0x40(r11)
        cmpwi r3, 0
        beq names_out
        lwz r4, 0(r3)
        stw r4, 0x50(r11)
        lwz r4, 4(r3)
        stw r4, 0x54(r11)
        lwz r4, 8(r3)
        stw r4, 0x58(r11)
names_out:
""" % dict(THI=TABLE >> 16, TLO=TABLE & 0xFFFF) if NAMES else "") + """
        lis r11, 0x%(THI)04X
        ori r11, r11, 0x%(TLO)04X
        lis r12, 0x102F
        lwz r12, 0x7188(r12)
        addi r3, r12, 4
        stw r3, 0xC(r11)
        bl 0x030A89C0                   # stage database count
        lis r11, 0x%(THI)04X
        ori r11, r11, 0x%(TLO)04X
        stw r3, 4(r11)
        lis r12, 0x1034
        lwz r12, 0x69C(r12)             # ui_sound_db: [ [0x1034069C] + 4 ] + 8
        lwz r12, 4(r12)
        cmpwi r12, 0
        beq ssdbg_out
        lwz r12, 8(r12)
        stw r12, 8(r11)
ssdbg_out:
        lwz r3, 0x10(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
""" % dict(THI=TABLE >> 16, TLO=TABLE & 0xFFFF)
    a = Asm(CAVE)
    a.asm(src)
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, 'stage select debug cave too big: %d words' % len(words)
    hook = Asm(HOOK)
    hook.asm('bl 0x%08X' % CAVE)
    return words, hook.words()[0]


def main():
    words, hook = build()
    out = ['grow:0x%08X' % GROW_END]
    out += ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % (TABLE + 4 * i, 0) for i in range(0xD00 // 4)]
    out.append('0x%08X=0x%08X' % (HOOK, hook))
    print(' '.join(out))
    sys.stderr.write('table at 0x%08X (%d code words)\n' % (TABLE, len(words)))


if __name__ == '__main__':
    main()
