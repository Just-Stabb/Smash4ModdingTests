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

# hit time (docs/acmd-extra-commands.md): the hit info's +0x44 is a copy of the hitbox data, so the
# tag is at hit info +0x44 +0x66; find_copy checks the tag and the check words (not the slot).
HIT_STUN = 0x02C25C88            # victim: stfs f28, 0x30(r30) (hitstun = knockback x 0.4 -> DamageModuleF(1));
                                 #   r27 victim accessor, r28 hit info; free r5 r8 r9 r10 r12 f9-f13
HIT_VSTOP = 0x02C25A78           # victim: cmpwi r19, 2, r20 = final hitstop frames; free r0 r3-r12 f0 f12 f13
HIT_AMUL = 0x02C2645C            # attacker: or. r27, r3, r3 (r3 = hitstop before the rate); r30 hit info
HIT_AFIX = 0x02C264C4            # attacker: lwz r27, 0x10(r1) (after the rate); r3 / ctr live
DI_STAT = 0x037EE180             # kirby_stat_cave.py's get_float path: bnelr after cmpwi r11, 3 (not a fighter stat)
DI_ID = 0x11A                    # fighter_param 0x0200011A: max DI angle (read by every fighter's MSC damage code)
DI_SLOTS = 16
HIT_ORIG = {HIT_STUN: 0xD39E0030, HIT_VSTOP: 0x2C130002, HIT_AMUL: 0x7C7B1B79, HIT_AFIX: 0x83610010,
            DI_STAT: 0x4C820020}

SPECIAL_HITBOX = 0x02BDBB20      # handler, size 42
EXT_SPECIAL_HITBOX = 0x02BDD46C  # handler, size 44
N_EXTRA = 6

# the extra parameters of the Extra hitbox commands: name, type (0 int, 1 float), description
EXTRA_PARAMS = [
    ('HitstunMul', 1, 'Multiplies the hitstun this hit gives the opponent (the game\'s own: knockback x 0.4). 0 or less = x1 (normal).'),
    ('HitstopMul', 1, 'Multiplies the opponent\'s hitstop (hitlag) from this hit, on top of the Hitlag parameter. 0 or less = x1.'),
    ('HitstopFrames', 0, 'The opponent\'s hitstop in frames, replacing the computed one (HitstopMul is then ignored). 0 = computed.'),
    ('SelfHitstopMul', 1, 'Multiplies the attacker\'s own hitstop from this hit. 0 or less = x1.'),
    ('SelfHitstopFrames', 0, 'The attacker\'s own hitstop in frames, replacing the computed one. 0 = computed.'),
    ('DIMul', 1, 'Multiplies how far DI can turn this hit\'s launch angle (0.5 = half, 2 = double). 0 or less = x1; for no DI use a tiny value (0.001).'),
]
SM4SHCOMMAND_DESC = {
    'Extra_Special_Hitbox': 'Special_Hitbox with 6 more parameters at the end: hitstun multiplier, hitstop / self hitstop multiplier '
                            'and frames, DI multiplier. New command: needs the patched cross_f.rpx (docs/acmd-extra-commands.md).',
    'Extra_Extended_Special_Hitbox': 'Extended_Special_Hitbox (capsule: X2/Y2/Z2) with 6 more parameters at the end: hitstun multiplier, '
                                     'hitstop / self hitstop multiplier and frames, DI multiplier. New command: needs the patched '
                                     'cross_f.rpx (docs/acmd-extra-commands.md).',
}
BASE_CRC = {'Extra_Special_Hitbox': 0x14FCC7E4, 'Extra_Extended_Special_Hitbox': 0x7075DC5A}

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

    hit_code(a)
    if a.pc % 8:
        a.asm('.word 0')
    a.asm("""
scratch:                                # scale_int: a double, then 2^52 + 2^31
        .word 0
        .word 0
        .word 0x43300000
        .word 0x80000000
""")
    a.asm('cmd_crcs:\n' + ''.join('        .word 0x%08X\n' % crc(c[0]) for c in COMMANDS))
    a.asm('cmd_sizes:\n' + ''.join('        .word %d\n' % c[1] for c in COMMANDS))
    a.asm('cmd_handlers:\n' + ''.join('        .word 0x%08X\n' % a.addr(c[2]) for c in COMMANDS))
    a.labels['table'] = TABLE
    a.labels['di_tab'] = TABLE + ENTRIES * ENTRY
    assert a.addr('scratch') % 8 == 0, hex(a.addr('scratch'))
    words = a.words()
    assert CAVE + 4 * len(words) <= TABLE, hex(CAVE + 4 * len(words))
    hooks = {LOOKUP: b(LOOKUP, a.addr('lookup')), SIZE1: b(SIZE1, a.addr('size1')),
             SIZE2: b(SIZE2, a.addr('size2')), FETCH: b(FETCH, a.addr('fetch')),
             HIT_STUN: b(HIT_STUN, a.addr('hk_stun')), HIT_VSTOP: b(HIT_VSTOP, a.addr('hk_vstop')),
             HIT_AMUL: b(HIT_AMUL, a.addr('hk_amul')), HIT_AFIX: b(HIT_AFIX, a.addr('hk_afix')),
             DI_STAT: b(DI_STAT, a.addr('di_check'))}   # was bnelr: di_check tests cr0
    return a, words, hooks


def hit_code(a):
    """find_copy, the four hit-time hooks, the DI table and the DI stat read"""
    sig = ''.join("""
        lwz r12, %d(r10)
        lwz r8, %d(r5)
        cmplw r8, r12
        bne fc_none""" % (e, d) for e, d in ((4, 0x20), (8, 0x24), (0xC, 0x28), (0x10, 0x2C), (0x2C, 0x3C)))
    a.asm("""
find_copy:                              # r5 = hitbox data (a copy) -> r5 = its extras or 0; uses r8 r10 r12 cr0
        andi. r10, r5, 3
        bne fc_none
        addis r10, r5, -0x1000
        rlwinm. r10, r10, 0, 0, 0
        bne fc_none
        lhz r10, %(tag)d(r5)
        rlwinm r12, r10, 0, 16, 23
        cmplwi r12, %(TAG)d
        bne fc_none
        rlwinm r10, r10, 0, 24, 31
        cmplwi r10, %(entries)d
        bge fc_none
        mulli r10, r10, %(entry)d
        lis r12, table@ha
        addi r12, r12, table@l
        add r10, r12, r10
        lwz r12, 0(r10)
        cmpwi r12, 0
        beq fc_none""" % dict(tag=TAG_OFF, TAG=TAG, entries=ENTRIES, entry=ENTRY) + sig + """
        mr r5, r10
        blr
fc_none:
        li r5, 0
        blr

scale_int:                              # r3 = floor(r3 x f13) (r3 >= 0); uses r0 r12 f0 f12
        lis r12, scratch@ha
        addi r12, r12, scratch@l
        xoris r0, r3, 0x8000
        stw r0, 4(r12)
        lis r0, 0x4330
        stw r0, 0(r12)
        lfd f0, 0(r12)
        lfd f12, 8(r12)                 # 2^52 + 2^31
        fsub f0, f0, f12
        fmul f0, f0, f13
        fctiwz f0, f0
        stfd f0, 0(r12)
        lwz r3, 4(r12)
        blr

hk_stun:                                # victim's hitstun (f28) x HitstunMul; this hit's DI x for the victim
        mfcr r9
        addi r5, r28, 0x44
        bl find_copy
        lis r12, one@ha
        lfs f9, one@l(r12)              # DI x (1 for any other hit)
        cmpwi r5, 0
        beq st_di
        lfs f10, 0x14(r5)
        fmuls f28, f28, f10
        lfs f9, 0x28(r5)
st_di:""" + chk_t('r27', 'r12', 'st_out') + """
        lwz r8, 0x28(r27)               # the victim's WorkModule""" + chk_t('r8', 'r12', 'st_out') + """
        bl di_store
st_out:
        mtcrf 0xFF, r9
        stfs f28, 0x30(r30)
        b 0x%(stun_back)08X

di_store:                               # r8 = WorkModule, f9 = DI x; uses r5 r10 r12 f10
        lis r10, di_tab@ha
        addi r10, r10, di_tab@l
        li r5, 0
ds_loop:
        lwz r12, 0(r10)
        cmplw r12, r8
        beq ds_set
        addi r10, r10, 8
        addi r5, r5, 1
        cmpwi r5, %(slots)d
        blt ds_loop
        lis r12, one@ha
        lfs f10, one@l(r12)
        fcmpu cr0, f9, f10
        beqlr                           # x1 and no entry: nothing to keep
        lis r12, di_next@ha
        lwz r5, di_next@l(r12)
        addi r10, r5, 1
        cmpwi r10, %(slots)d
        blt ds_wrap
        li r10, 0
ds_wrap:
        stw r10, di_next@l(r12)
        lis r10, di_tab@ha
        addi r10, r10, di_tab@l
        slwi r5, r5, 3
        add r10, r10, r5
        stw r8, 0(r10)
ds_set:
        stfs f9, 4(r10)
        blr

di_check:                               # from get_float after cmpwi r11, 3 (a b replaces its bnelr): r3 this, r4 id, f1
        bne dc_go
        b 0x%(stat_back)08X                # a fighter stat (category 3): on as before
dc_go:
        cmpwi r11, 2
        bnelr
        rlwinm r12, r4, 0, 8, 31
        cmplwi r12, %(di_id)d
        bnelr
        lis r10, di_tab@ha
        addi r10, r10, di_tab@l
        li r12, %(slots)d
dc_loop:
        lwz r0, 0(r10)
        cmplw r0, r3
        beq dc_found
        addi r10, r10, 8
        addi r12, r12, -1
        cmpwi r12, 0
        bne dc_loop
        blr
dc_found:
        lfs f0, 4(r10)
        fmuls f1, f1, f0
        blr

hk_vstop:                               # victim's hitstop (r20): HitstopFrames, else x HitstopMul
        addi r5, r28, 0x44
        bl find_copy
        cmpwi r5, 0
        beq vs_out
        lwz r0, 0x1C(r5)
        cmpwi r0, 0
        ble vs_mul
        mr r20, r0
        b vs_out
vs_mul:
        lfs f13, 0x18(r5)
        mr r3, r20
        bl scale_int
        mr r20, r3
vs_out:
        cmpwi r19, 2
        b 0x%(vstop_back)08X

hk_amul:                                # attacker's hitstop before the rate (r3): x SelfHitstopMul
        mfcr r9
        mr r27, r3
        addi r5, r30, 0x44
        bl find_copy
        cmpwi r5, 0
        beq am_out
        mr r8, r5
        lfs f13, 0x20(r8)
        mr r3, r27
        bl scale_int
        mr r27, r3
        lwz r0, 0x24(r8)                # fixed frames: make sure the hitstop path runs (set at HIT_AFIX)
        cmpwi r0, 0
        ble am_out
        cmpwi r27, 0
        bgt am_out
        li r27, 1
am_out:
        mtcrf 0xFF, r9
        mr r3, r27
        or. r27, r27, r27
        b 0x%(amul_back)08X

hk_afix:                                # attacker's hitstop after the rate: SelfHitstopFrames
        lwz r27, 0x10(r1)
        mfcr r9
        addi r5, r30, 0x44
        bl find_copy
        cmpwi r5, 0
        beq af_out
        lwz r0, 0x24(r5)
        cmpwi r0, 0
        ble af_out
        mr r27, r0
af_out:
        mtcrf 0xFF, r9
        b 0x%(afix_back)08X

di_next:
        .word 0
""" % dict(stun_back=HIT_STUN + 4, vstop_back=HIT_VSTOP + 4, amul_back=HIT_AMUL + 4, afix_back=HIT_AFIX + 4,
           slots=DI_SLOTS, di_id=DI_ID, stat_back=DI_STAT + 4))


def chk_t(reg, tmp, fail):
    """branch to fail unless reg is a word-aligned pointer in 0x10000000-0x8FFFFFFF (temp register tmp)"""
    return """
        addis %(t)s, %(r)s, -0x1000
        rlwinm. %(t)s, %(t)s, 0, 0, 0
        bne %(f)s
        andi. %(t)s, %(r)s, 3
        bne %(f)s""" % dict(t=tmp, r=reg, f=fail)


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


def labels(path):
    """add / update the new commands in tools/Sm4shCommand/param_labels.json (apply_param_labels.py then
    puts them in Sm4shCommand's table, tools/acmd_info.json and Events.cfg)"""
    import json
    d = json.load(open(path))
    info = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'acmd_info.json')))['commands']
    for name, size, _label, _base in COMMANDS:
        if name not in BASE_CRC:
            continue
        base = '%08X' % BASE_CRC[name]
        bi, bl = info[base], d.get(base, {})
        e = {'_command': name, '_new': True, '_name': name, '_size': size, '_desc': SM4SHCOMMAND_DESC[name],
             '_format': bi['format'] + [t for _n, t, _d in EXTRA_PARAMS]}
        for k, pname in enumerate(bi['syntax']):
            e[str(k)] = dict(bl.get(str(k), {}), name=pname)
        for k, (pname, _t, desc) in enumerate(EXTRA_PARAMS):
            e[str(len(bi['syntax']) + k)] = {'name': pname, 'desc': desc, 'confidence': 'high'}
        assert len(e['_format']) == size - 1
        d['%08X' % crc(name)] = e
    json.dump(dict(sorted(d.items())), open(path, 'w'), indent=1)


def main():
    if '--labels' in sys.argv:
        labels(sys.argv[sys.argv.index('--labels') + 1])
        return
    a, words, hooks = build()
    out = ['grow:0x%08X' % LIMIT]
    out += ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % kv for kv in sorted(hooks.items())]
    print(' '.join(out))
    sys.stderr.write('acmd ext: %d words, %s\n' % (len(words), ', '.join(
        '%s 0x%08X index %d' % (c[0], crc(c[0]), NEW_BASE + i) for i, c in enumerate(COMMANDS))))


if __name__ == '__main__':
    main()
