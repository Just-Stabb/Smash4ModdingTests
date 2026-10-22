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
LIMIT = 0x04B9A000
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

# per-object state (user variables, timers, tracking), keyed by the object's WorkModule
OBJS = 0x04B94000                # OBJ_N entries of OBJ_SIZE (zero at load)
OBJ_N = 48
OBJ_SIZE = 0x100                 # +0 WorkModule, +4 accessor (last seen), +8 tracking frames left (int, < 0 = until
                                 # stopped), +0xC speed, +0x10 cos(turn) (< -1.5: turn at once), +0x14 sin(turn),
                                 # +0x18 range squared (0 = any), +0x1C mode, +0x20 timers[16], +0x60 vars[32]
ACC_CACHE = 0x04B97000           # 64 x {WorkModule, accessor}, filled by the per-frame hook for every object
THREADS = 0x04B98000             # THREAD_N slots of THREAD_SIZE: +0 accessor (0 = free), +4 script table (the
THREAD_N = 32                    # handler's r4), +8 ID, +0xC flags (0x80000000 = stop after this frame),
THREAD_SIZE = 0x48               # +0x10 the thread's own interpreter state (0x38 bytes)
STEP_HOOKS = [0x02E408B8, 0x02BAD64C, 0x03048064]   # object step entries (fighters, weapons, items?): every
                                 # unpaused frame, hitlag and KO included; stwu r1, -0x38(r1), r4 -> accessor
INTERP = 0x02BEE950              # (r3 script table, r4 accessor, r5 state, r6 exec, f1 frames, f2 target)
STATE_RESET = 0x02BEE9B8         # (r3 state): clear it, free a nested CALL state
THREAD_STOP_BIT = 0x80000000
GROW = 0x04B9A000
FRAME_HOOK = 0x02C5F430          # every object's motion step, right after its ACMD ran (not in hitlag): li r0, 1
WM_RESET = 0x02BF5864            # object set-up (every class, 0x02BF57B0): lwz r3, 0x28(r31) before WorkModule
                                 # vt +0x24 (reset): an object is set up / reused. r0 r10 ctr are free there
VAR_ENTRY = 0x04B79000           # position_vars_cave.py's var_entry (0x0F000xxx IDs): rlwinm r12, r4, 0, 22, 31
USER_BASE = 0x300                # IDs 0x0F000300+ come here (docs/acmd-extra-commands.md)
FIGHTERS = 0x1035184C            # [[FIGHTERS] + 0] = fighter table: +0 entries, +8 count
FIGHTER_ENTRY = 0x76B0           # entry: +0 object ID, +0xC accessor, byte +0x1E >= 4 = live
KINETIC_W = 0x030B29D8           # MSC module wrappers: wrapper(ctx (+4 = accessor), {words, count})
POSTURE_W = 0x030B2AB8
OBJ_ORIG = {FRAME_HOOK: 0x38000001, WM_RESET: 0x807F0028, VAR_ENTRY: 0x548C05BE}
OBJ_ORIG.update({h: 0x9421FFC8 for h in STEP_HOOKS})

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
SM4SHCOMMAND_DESC['Track_Target'] = (
    'Makes this object (a fighter, or a projectile in its own script) home in on the nearest other fighter for Frames frames: '
    'its direction turns toward the target by up to TurnRate degrees a frame, at Speed. Projectiles skip their owner; '
    'a reflected one goes back at its original owner instead (any distance). '
    'Read / stop it with variable 0x0F000331. New command: needs the patched cross_f.rpx (docs/acmd-extra-commands.md).')
SM4SHCOMMAND_DESC['Thread_Start'] = (
    'Thread_Start(ID, Flags){ ... }: the commands in the block run on their own, frame by frame, from the next frame on, '
    'while the script goes on past the block. The thread keeps running after the animation ends or changes and while the '
    'character is KO\'d, until the block ends, Thread_Stop(ID), or the object is set up again. FRAME inside counts from '
    'the thread\'s start. New command: needs the patched cross_f.rpx (docs/acmd-extra-commands.md).')
SM4SHCOMMAND_DESC['Thread_Stop'] = 'Stops this object\'s thread ID (-1 = all of them). New command: needs the patched cross_f.rpx.'
BASE_CRC = {'Extra_Special_Hitbox': 0x14FCC7E4, 'Extra_Extended_Special_Hitbox': 0x7075DC5A}

COMMANDS = [                     # name, size (words, header included), handler label, base handler
    ('Extra_Special_Hitbox', 42 + N_EXTRA, 'h_extra', SPECIAL_HITBOX),
    ('Extra_Extended_Special_Hitbox', 44 + N_EXTRA, 'h_extra_ext', EXT_SPECIAL_HITBOX),
    ('Track_Target', 8, 'h_track', None),
    ('Thread_Start', 4, 'h_thread', None),
    ('Thread_Stop', 2, 'h_thread_stop', None),
]
THREAD_PARAMS = [
    ('Offset', 0, 'Words to the end of the block (Sm4shCommand works it out from the braces, like True).'),
    ('ID', 0, 'This thread\'s number (any). Starting it again restarts it; Thread_Stop(ID) stops it.'),
    ('Flags', 0, 'Bits: 1 = keep running during hitlag (normally the thread pauses with the object).'),
]
THREAD_STOP_PARAMS = [
    ('ID', 0, 'The thread to stop (Thread_Start\'s ID); -1 = every thread of this object.'),
]
TRACK_PARAMS = [
    ('Frames', 0, 'Frames to track for (counted while the object moves: not in hitlag). -1 = until a Track_Target with 0 frames (or the object is reset).'),
    ('Speed', 1, 'Travel speed while tracking. 0 = keep the current speed (and turn it).'),
    ('TurnRate', 1, 'Most the direction can turn per frame, in degrees. 0 (or 180+) = point straight at the target every frame.'),
    ('Range', 1, 'Only targets within this distance (X/Y). 0 = any distance.'),
    ('Mode', 0, 'Bits: 1 = horizontal only (ignore height; fighters keep gravity), 2 = turn to face the target (fighters).'),
    ('TargetOwner', 0, '1 = a projectile may also target the fighter who fired it (normally skipped). Fighters: no effect.'),
    ('TargetTeammates', 0, '1 = may target teammates even when team attack is off (normally skipped then; with team attack on they are always targets).'),
]


def ha(v):
    return ((v + 0x8000) >> 16) & 0xFFFF


def lo(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


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
    obj_code(a)
    thread_code(a)
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
    a.labels['objs'] = OBJS
    a.labels['acc_cache'] = ACC_CACHE
    a.labels['threads'] = THREADS
    assert TABLE + ENTRIES * ENTRY + 8 * DI_SLOTS <= OBJS
    assert a.addr('scratch') % 8 == 0, hex(a.addr('scratch'))
    words = a.words()
    assert CAVE + 4 * len(words) <= TABLE, hex(CAVE + 4 * len(words))
    assert ACC_CACHE + 64 * 8 <= THREADS and THREADS + THREAD_N * THREAD_SIZE <= GROW <= LIMIT
    hooks = {LOOKUP: b(LOOKUP, a.addr('lookup')), SIZE1: b(SIZE1, a.addr('size1')),
             SIZE2: b(SIZE2, a.addr('size2')), FETCH: b(FETCH, a.addr('fetch')),
             HIT_STUN: b(HIT_STUN, a.addr('hk_stun')), HIT_VSTOP: b(HIT_VSTOP, a.addr('hk_vstop')),
             HIT_AMUL: b(HIT_AMUL, a.addr('hk_amul')), HIT_AFIX: b(HIT_AFIX, a.addr('hk_afix')),
             DI_STAT: b(DI_STAT, a.addr('di_check')),   # was bnelr: di_check tests cr0
             FRAME_HOOK: b(FRAME_HOOK, a.addr('hk_frame')), WM_RESET: b(WM_RESET, a.addr('hk_wmreset')),
             VAR_ENTRY: b(VAR_ENTRY, a.addr('user_gate'))}
    for k, h in enumerate(STEP_HOOKS):
        hooks[h] = b(h, a.addr('hk_step%d' % k))
    return a, words, hooks


def vcall(off):
    """call vt +off of the object in r3 (r12 / ctr clobbered)"""
    return """
        lwz r12, 0(r3)
        lwz r12, %d(r12)
        mtctr r12
        bctrl""" % off


def kcall(wrapper, words):
    """MSC module op through its wrapper: ctx at 0x40(r1) (+4 = accessor in r30), args {0x30(r1), n} at
    0x28(r1); words: ints, or ('f', stack offset) for a float kept at that offset of the frame"""
    out = ["        stw r30, 0x44(r1)"]
    for i, w in enumerate(words):
        if isinstance(w, tuple):
            out.append("        lwz r0, %d(r1)" % w[1])
        else:
            out.append("        li r0, %d" % w)
        out.append("        stw r0, %d(r1)" % (0x30 + 4 * i))
    out += ["        addi r0, r1, 0x30", "        stw r0, 0x28(r1)", "        li r0, %d" % len(words),
            "        stw r0, 0x2C(r1)", "        addi r3, r1, 0x40", "        addi r4, r1, 0x28",
            "        bl 0x%08X" % wrapper]
    return "\n" + "\n".join(out)


def obj_code(a):
    """per-object state: user variables / timers / kinetic type / tracking"""
    U = dict(ubase=USER_BASE, u20=USER_BASE + 0x20, u30=USER_BASE + 0x30, u31=USER_BASE + 0x31,
             u32=USER_BASE + 0x32, u33=USER_BASE + 0x33)
    fl = lambda reg, fail: chk_t(reg, 'r0', fail)     # noqa: E731
    a.asm("""
# --- obj_find(r3 WorkModule, r4 create) -> r3 entry or 0; leaf: r0 r10 r11 r12 -----------------
obj_find:
        lis r12, objs@ha
        addi r12, r12, objs@l
        li r11, %(n)d
of_loop:
        lwz r0, 0(r12)
        cmplw r0, r3
        beq of_hit
        addi r12, r12, %(size)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne of_loop
        cmpwi r4, 0
        beq of_none
        lis r12, objs@ha
        addi r12, r12, objs@l
        li r11, %(n)d
of_free:
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq of_take
        addi r12, r12, %(size)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne of_free
        lis r10, obj_next@ha            # all taken: the oldest one goes
        lwz r11, obj_next@l(r10)
        addi r0, r11, 1
        cmplwi r0, %(n)d
        blt of_wrap
        li r0, 0
of_wrap:
        stw r0, obj_next@l(r10)
        mulli r11, r11, %(size)d
        lis r12, objs@ha
        addi r12, r12, objs@l
        add r12, r12, r11
of_take:
        li r0, 0
        li r11, %(last)d
of_zero:
        stwx r0, r12, r11
        addi r11, r11, -4
        cmpwi r11, 0
        bge of_zero
        stw r3, 0(r12)
of_hit:
        mr r3, r12
        blr
of_none:
        li r3, 0
        blr

# --- acc_of(r3 WorkModule) -> r3 accessor or 0 (the per-frame cache); leaf: r0 r11 r12 -----------
acc_of:
        rlwinm r12, r3, 31, 23, 28      # ((wm >> 4) & 63) * 8
        lis r11, acc_cache@ha
        addi r11, r11, acc_cache@l
        add r11, r11, r12
        lwz r0, 0(r11)
        cmplw r0, r3
        bne ao_none
        lwz r3, 4(r11)
        blr
ao_none:
        li r3, 0
        blr

# --- i2f(r3) -> f1 (float); f2i(f1) -> r3 (truncated). r0 r12 f0 f12 ------------------------------
i2f:
        lis r12, scratch@ha
        addi r12, r12, scratch@l
        xoris r0, r3, 0x8000
        stw r0, 4(r12)
        lis r0, 0x4330
        stw r0, 0(r12)
        lfd f0, 0(r12)
        lfd f12, 8(r12)
        fsub f1, f0, f12
        frsp f1, f1
        blr
f2i:
        lis r12, scratch@ha
        addi r12, r12, scratch@l
        fctiwz f0, f1
        stfd f0, 0(r12)
        lwz r3, 4(r12)
        blr

# --- fsqrt(f1) -> f1; f0 f12 f13 (0 for <= 0) -----------------------------------------------------
fsqrt:
        lis r12, zero@ha
        lfs f0, zero@l(r12)
        fcmpu cr0, f1, f0
        bgt fs_go
        fmr f1, f0
        blr
fs_go:
        frsqrte f12, f1
        lfs f13, half@l(r12)
        lfs f0, onehalf@l(r12)
        fmul f13, f1, f13               # x / 2
        fmul f2, f12, f12
        fmul f2, f2, f13
        fsub f2, f0, f2
        fmul f12, f12, f2               # y (1.5 - x/2 y^2), twice
        fmul f2, f12, f12
        fmul f2, f2, f13
        fsub f2, f0, f2
        fmul f12, f12, f2
        fmul f1, f1, f12
        frsp f1, f1
        blr

# --- var_entry gate: IDs 0x0F000300+ -> user_entry ---------------------------------------------------
user_gate:
        rlwinm r12, r4, 0, 22, 31
        cmplwi r12, %(ubase)d
        blt ug_back
        b user_entry
ug_back:
        b 0x%(var_back)08X

# --- user_entry(r3 WorkModule, r4 ID, r5 write, f1 value) -> f1 ----------------------------------------
# 0x300+i (i < 32) user variable i; 0x320+i (i < 16) timer i (counts down to 0 each frame);
# 0x330 kinetic type (write: change it); 0x331 tracking frames left (write: set, 0 stops);
# 0x332 / 0x333 speed X / Y (read only, all energies). Any other: reads 0.
user_entry:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r27, 0x1C(r1)
        stfs f1, 0x18(r1)
        mr r31, r3
        rlwinm r30, r4, 0, 22, 31
        mr r29, r5""" % dict(n=OBJ_N, size=OBJ_SIZE, last=OBJ_SIZE - 4, ubase=USER_BASE, var_back=VAR_ENTRY + 4)
        + fl('r31', 'ue_zero') + """
        cmplwi r30, %(u20)d
        blt ue_var
        cmplwi r30, %(u30)d
        blt ue_timer
        beq ue_kin
        cmplwi r30, %(u31)d
        beq ue_track
        cmplwi r30, %(u33)d
        bgt ue_zero
        b ue_speed
ue_var:
        addi r28, r30, -%(ubase)d
        slwi r28, r28, 2
        addi r28, r28, 0x60
        b ue_slot
ue_timer:
        addi r28, r30, -%(u20)d
        slwi r28, r28, 2
        addi r28, r28, 0x20
ue_slot:
        mr r3, r31
        mr r4, r29                      # writing creates the object's entry
        bl obj_find
        cmpwi r3, 0
        beq ue_zero
        cmpwi r29, 0
        bne ue_slot_w
        lfsx f1, r3, r28
        b ue_out
ue_slot_w:
        lfs f1, 0x18(r1)
        stfsx f1, r3, r28
        b ue_out
ue_track:
        mr r3, r31
        mr r4, r29
        bl obj_find
        mr. r28, r3
        beq ue_zero
        cmpwi r29, 0
        bne ue_track_w
        lwz r3, 8(r28)
        bl i2f
        b ue_out
ue_track_w:
        lfs f1, 0x18(r1)
        bl f2i
        stw r3, 8(r28)
        b ue_out
ue_kin:
        mr r3, r31
        bl acc_of""" % U + fl('r3', 'ue_zero') + """
        lwz r3, 0x34(r3)                # KineticModule""" + fl('r3', 'ue_zero') + """
        mr r28, r3
        cmpwi r29, 0
        bne ue_kin_w
        lwz r3, 0x11C(r28)              # current kinetic type
        bl i2f
        b ue_out
ue_kin_w:
        lfs f1, 0x18(r1)
        bl f2i
        mr r4, r3
        mr r3, r28""" + vcall(0xEC) + """   # set the kinetic type (as Set_Kinetic_Handler: op 0)
        b ue_out
ue_speed:
        cmpwi r29, 0
        bne ue_out
        mr r3, r31
        bl acc_of""" + fl('r3', 'ue_zero') + """
        lwz r3, 0x34(r3)""" + fl('r3', 'ue_zero') + """
        li r4, -1""" + vcall(0xA4) + """   # sum of the enabled energies' speed: r3 x, r4 y (float bits)
        stw r3, 0x10(r1)
        stw r4, 0x14(r1)
        cmplwi r30, 0x332
        bne ue_sp_y
        lfs f1, 0x10(r1)
        b ue_out
ue_sp_y:
        lfs f1, 0x14(r1)
        b ue_out
ue_zero:
        lis r12, zero@ha
        lfs f1, zero@l(r12)
ue_out:
        cmpwi r29, 0
        beq ue_ret
        lfs f1, 0x18(r1)
ue_ret:
        lmw r27, 0x1C(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

# --- WorkModule set up / reused: forget its entry --------------------------------------------------
hk_wmreset:
        lwz r3, 0x28(r31)               # the WorkModule about to be reset
        lis r10, objs@ha
        addi r10, r10, objs@l
        li r0, %(n)d
        mtctr r0
wr_loop:
        lwz r0, 0(r10)
        cmplw r0, r3
        bne wr_next
        li r0, 0
        stw r0, 0(r10)
        stw r0, 8(r10)                  # no tracking
wr_next:
        addi r10, r10, %(size)d
        bdnz wr_loop
        stwu r1, -0x90(r1)              # and its threads (STATE_RESET frees a CALL state: save all)
        mflr r0
        stw r0, 0x94(r1)
        stmw r3, 0x10(r1)
        mfcr r0
        stw r0, 0x88(r1)
        mr r3, r31
        li r4, -1
        li r5, 0
        bl thread_drop
        lwz r0, 0x88(r1)
        mtcrf 0xFF, r0
        lmw r3, 0x10(r1)
        lwz r0, 0x94(r1)
        mtlr r0
        addi r1, r1, 0x90
        b 0x%(wm_back)08X

# --- every object, every frame it moves (after its ACMD): timers, tracking --------------------------
hk_frame:
        stwu r1, -0x60(r1)
        stmw r26, 0x28(r1)
        lwz r29, 4(r31)                 # accessor (r31 = MotionModule)""" % dict(U, n=OBJ_N, size=OBJ_SIZE, wm_back=WM_RESET + 4)
        + fl('r29', 'hf_out') + """
        lwz r28, 0x28(r29)              # WorkModule""" + fl('r28', 'hf_out') + """
        rlwinm r12, r28, 31, 23, 28
        lis r11, acc_cache@ha
        addi r11, r11, acc_cache@l
        add r11, r11, r12
        stw r28, 0(r11)
        stw r29, 4(r11)
        mr r3, r28
        li r4, 0
        bl obj_find
        mr. r30, r3
        beq hf_out
        stw r29, 4(r30)
        lis r12, one@ha
        lfs f2, one@l(r12)
        lfs f3, zero@l(r12)
        li r11, 0x20
hf_timer:
        lfsx f1, r30, r11
        fcmpu cr0, f1, f3
        ble hf_tnext
        fsubs f1, f1, f2
        fcmpu cr0, f1, f3
        bge hf_tset
        fmr f1, f3
hf_tset:
        stfsx f1, r30, r11
hf_tnext:
        addi r11, r11, 4
        cmpwi r11, 0x60
        blt hf_timer
        lwz r12, 8(r30)
        cmpwi r12, 0
        beq hf_out
        blt hf_go                       # < 0: until stopped
        addi r12, r12, -1               # (not r0: addi rD, r0, n is li)
        stw r12, 8(r30)
hf_go:
        mr r3, r30
        mr r4, r29
        bl track_step
hf_out:
        lmw r26, 0x28(r1)
        addi r1, r1, 0x60
        li r0, 1
        b 0x%(frame_back)08X
""" % dict(frame_back=FRAME_HOOK + 4))
    track_code(a)


def track_code(a):
    fl = lambda reg, fail: chk_t(reg, 'r0', fail)     # noqa: E731
    # frame: 0x10/0x14 current v, 0x18/0x1C target delta, 0x20/0x24 new v, 0x28 args, 0x30 words,
    # 0x40 ctx (+4 accessor), 0x48 best d2; r31 entry, r30 accessor, r29 KineticModule, r28 posture,
    # r27 owner ID, r26 self is a fighter, r25 count, r24 entries, r23 energy 0 (weapons), r22 found
    a.asm("""
# --- Track_Target command: (Frames, Speed, TurnRate, Range, Mode) ------------------------------------
h_track:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r28, 0x1C(r1)
        mr r31, r5
        mr r30, r7
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq ht_step""" + fl('r3', 'ht_step') + """
        lwz r3, 0x28(r3)""" + fl('r3', 'ht_step') + """
        li r4, 1
        bl obj_find
        mr. r29, r3
        beq ht_step
        lwz r0, 0(r30)
        stw r0, 8(r29)                  # frames
        lfs f1, 4(r30)
        stfs f1, 0xC(r29)               # speed
        lfs f1, 0xC(r30)                # range -> squared
        fmuls f1, f1, f1
        stfs f1, 0x18(r29)
        lwz r0, 0x10(r30)
        lwz r11, 0x14(r30)              # TargetOwner -> mode bit 0x100
        cmpwi r11, 0
        beq ht_noown
        ori r0, r0, 0x100
ht_noown:
        lwz r11, 0x18(r30)              # TargetTeammates -> mode bit 0x200
        cmpwi r11, 0
        beq ht_notm
        ori r0, r0, 0x200
ht_notm:
        stw r0, 0x1C(r29)               # mode
        lfs f1, 8(r30)                  # turn rate (degrees)
        lis r12, zero@ha
        lfs f0, zero@l(r12)
        lfs f2, snap@l(r12)
        stfs f2, 0x10(r29)              # cos < -1.5: turn at once
        fcmpu cr0, f1, f0
        ble ht_step
        lfs f3, deg180@l(r12)
        fcmpu cr0, f1, f3
        bge ht_step
        lfs f3, deg2rad@l(r12)
        fmuls f1, f1, f3                # x (radians)
        fmuls f2, f1, f1                # x^2
        lfs f4, one@l(r12)
""" + horner('f5', 'f2', [72, 42, 20, 6]) + """
        fmuls f5, f5, f1                # sin x = x (1 - x2/6 (1 - x2/20 (...)))
        stfs f5, 0x14(r29)
""" + horner('f5', 'f2', [56, 30, 12, 2]) + """
        stfs f5, 0x10(r29)              # cos x
ht_step:
        lwz r0, 8(r31)
        cmpwi r0, -1
        bne ht_out
        lwz r11, 4(r31)
        addi r11, r11, 32               # 8 words
        stw r11, 4(r31)
ht_out:
        li r3, 2
        lmw r28, 0x1C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- track_step(r3 entry, r4 accessor): steer toward the nearest other fighter ------------------------
track_step:
        stwu r1, -0x90(r1)
        mflr r0
        stw r0, 0x94(r1)
        stmw r20, 0x58(r1)
        mr r31, r3
        mr r30, r4
        li r21, -1                      # reflected: the original owner (the only target, if live)
        lwz r29, 0x34(r30)""" + fl('r29', 'ts_out') + """
        lwz r28, 0x18(r30)""" + fl('r28', 'ts_out') + """
        li r27, -1
        li r26, 0
        lis r12, %(fh)d
        lwz r12, %(fl)d(r12)""" % dict(fh=ha(FIGHTERS), fl=lo(FIGHTERS)) + fl('r12', 'ts_out') + """
        lwz r12, 0(r12)""" + fl('r12', 'ts_out') + """
        lwz r25, 8(r12)
        lwz r24, 0(r12)""" + fl('r24', 'ts_out') + """
        cmplwi r25, 16
        bgt ts_out
        li r11, 0
ts_self:
        cmpw r11, r25
        bge ts_self_done
        mulli r12, r11, %(fe)d
        add r12, r24, r12
        lwz r0, 0xC(r12)
        cmplw r0, r30
        bne ts_self_next
        li r26, 1
ts_self_next:
        addi r11, r11, 1
        b ts_self
ts_self_done:
        cmpwi r26, 0
        bne ts_vel
        lwz r3, 0x68(r30)               # a weapon: its owner (LinkModule link 0's object ID)""" % dict(fe=FIGHTER_ENTRY)
        + fl('r3', 'ts_vel') + """
        mr r22, r3
        li r4, 0""" + vcall(0x5C) + """
        cmpwi r3, 0
        beq ts_vel
        mr r3, r22
        li r4, 0
        li r5, 1""" + vcall(0x6C) + """
        mr r27, r3
        lwz r3, 0x6C(r30)               # reflected? the current owner (+0x34: the reflector, after a
                                        # reflect) differs from link 0's (the original owner)""" + fl('r3', 'ts_vel') + """
        lwz r3, 0x34(r3)
        cmpw r3, r27
        beq ts_ownbit
        lis r0, 0x5000                  # (no object)
        cmpw r3, r0
        beq ts_ownbit
        mr r21, r27                     # go for the original owner; skip the reflector
        mr r27, r3
        b ts_vel
ts_ownbit:
        lwz r0, 0x1C(r31)               # TargetOwner: the owner is a target like any other
        andi. r0, r0, 0x100
        beq ts_vel
        li r27, -1
ts_vel:
        cmpwi r26, 0
        beq ts_vel_w
        mr r3, r29
        li r4, -1""" + vcall(0xA4) + """   # fighter: speed of all energies
        stw r3, 0x10(r1)
        stw r4, 0x14(r1)
        b ts_find
ts_vel_w:
        mr r3, r29
        li r4, 0""" + vcall(0x54) + """   # weapon: energy 0 (its own movement)""" + fl('r3', 'ts_out') + """
        mr r23, r3
        lwz r0, 0(r23)
        stw r0, 0x10(r1)
        lwz r0, 4(r23)
        stw r0, 0x14(r1)
ts_find:
        li r22, 0
        li r11, 0
        li r20, 0                       # r20 = 1: first pass, the original owner only (any distance)
        cmpwi r21, -1
        beq ts_floop
        li r20, 1
ts_floop:
        cmpw r11, r25
        bge ts_fdone
        mulli r12, r11, %(fe)d
        add r12, r24, r12
        addi r11, r11, 1
        lbz r0, 0x1E(r12)
        cmplwi r0, 4
        blt ts_floop
        lwz r0, 0(r12)
        cmpwi r20, 0
        beq ts_any
        cmpw r0, r21
        bne ts_floop
        b ts_id_ok
ts_any:
        cmpw r0, r27
        beq ts_floop
ts_id_ok:
        lwz r10, 0xC(r12)
        cmplw r10, r30
        beq ts_floop""" % dict(fe=FIGHTER_ENTRY) + fl('r10', 'ts_floop') + """
        lwz r10, 0x18(r10)""" + fl('r10', 'ts_floop') + """
        lfs f1, 0x10(r10)
        lfs f2, 0x10(r28)
        fsubs f1, f1, f2                # dx
        lfs f2, 0x14(r10)
        lfs f3, 0x14(r28)
        fsubs f2, f2, f3                # dy
        lwz r0, 0x1C(r31)
        andi. r0, r0, 1
        beq ts_d2
        lis r12, zero@ha
        lfs f2, zero@l(r12)
ts_d2:
        fmuls f3, f1, f1
        fmadds f3, f2, f2, f3           # d2
        cmpwi r20, 0
        bne ts_take                     # the original owner: whatever the range
        lfs f4, 0x18(r31)               # range squared (0 = any)
        lis r12, zero@ha
        lfs f5, zero@l(r12)
        fcmpu cr0, f4, f5
        ble ts_inrange
        fcmpu cr0, f3, f4
        bgt ts_floop
ts_inrange:
        cmpwi r22, 0
        beq ts_take
        lfs f4, 0x48(r1)
        fcmpu cr0, f3, f4
        bge ts_floop
ts_take:
        li r22, 1
        stfs f3, 0x48(r1)
        stfs f1, 0x18(r1)
        stfs f2, 0x1C(r1)
        b ts_floop
ts_fdone:
        cmpwi r22, 0
        bne ts_found
        cmpwi r20, 0
        beq ts_out
        li r20, 0                       # the original owner isn't there: the nearest other than the reflector
        li r11, 0
        b ts_floop
ts_found:
        lfs f1, 0x48(r1)                # d^ = d / |d|
        bl fsqrt
        lis r12, tiny@ha
        lfs f0, tiny@l(r12)
        fcmpu cr0, f1, f0
        blt ts_out
        lfs f2, 0x18(r1)
        lfs f3, 0x1C(r1)
        fdivs f6, f2, f1                # f6, f7 = d^
        fdivs f7, f3, f1
        stfs f6, 0x20(r1)
        stfs f7, 0x24(r1)
        lfs f2, 0x10(r1)                # |v|
        lfs f3, 0x14(r1)
        fmuls f1, f2, f2
        fmadds f1, f3, f3, f1
        bl fsqrt
        stfs f1, 0x4C(r1)
        lfs f6, 0x20(r1)
        lfs f7, 0x24(r1)
        lfs f8, 0xC(r31)                # speed (0 = keep |v|)
        lis r12, zero@ha
        lfs f0, zero@l(r12)
        fcmpu cr0, f8, f0
        bgt ts_spd
        fmr f8, f1
ts_spd:
        lis r12, tiny@ha
        lfs f0, tiny@l(r12)
        fcmpu cr0, f1, f0
        blt ts_dir_d                    # not moving: straight at the target
        lfs f2, 0x10(r1)
        lfs f3, 0x14(r1)
        fdivs f2, f2, f1                # f2, f3 = v^
        fdivs f3, f3, f1
        lfs f4, 0x10(r31)               # cos(turn)
        lfs f5, snap@l(r12)
        fcmpu cr0, f4, f5
        blt ts_dir_d
        fmuls f9, f2, f6                # dot
        fmadds f9, f3, f7, f9
        fcmpu cr0, f9, f4
        bge ts_dir_d
        lfs f5, 0x14(r31)               # sin(turn), signed by cross
        fmuls f10, f2, f7               # cross = vx dy - vy dx
        fmuls f11, f3, f6
        fsubs f10, f10, f11
        lis r12, zero@ha
        lfs f0, zero@l(r12)
        fcmpu cr0, f10, f0
        bge ts_rot
        fneg f5, f5
ts_rot:
        fmuls f6, f2, f4                # (vx c - vy s, vx s + vy c)
        fmuls f11, f3, f5
        fsubs f6, f6, f11
        fmuls f7, f2, f5
        fmadds f7, f3, f4, f7
ts_dir_d:
        fmuls f6, f6, f8
        fmuls f7, f7, f8
        stfs f6, 0x20(r1)
        stfs f7, 0x24(r1)
        stfs f8, 0x4C(r1)
        cmpwi r26, 0
        bne ts_fighter
        stfs f6, 0(r23)                 # weapon: its own movement energy
        lwz r0, 0x1C(r31)
        andi. r0, r0, 1
        bne ts_out
        stfs f7, 4(r23)
        b ts_out
ts_fighter:""" + kcall(KINETIC_W, [0x11, 3, ('f', 0x20), 0]) + kcall(KINETIC_W, [0x10, 3, 0, 0])
        + kcall(KINETIC_W, [0xB, 3]) + """
        lwz r0, 0x1C(r31)
        andi. r0, r0, 1
        bne ts_face""" + kcall(KINETIC_W, [0x11, 1, ('f', 0x24)]) + kcall(KINETIC_W, [0xF, 1, 0])
        + kcall(KINETIC_W, [0x14, 1, ('f', 0x4C)]) + kcall(KINETIC_W, [0xB, 1]) + """
ts_face:
        lwz r0, 0x1C(r31)
        andi. r0, r0, 2
        beq ts_out
        lfs f1, 0x18(r1)
        lfs f2, 0x60(r28)               # facing
        fmuls f1, f1, f2
        lis r12, zero@ha
        lfs f0, zero@l(r12)
        fcmpu cr0, f1, f0
        bge ts_out""" + kcall(POSTURE_W, [0x2710]) + kcall(POSTURE_W, [0x2]) + """
ts_out:
        lmw r20, 0x58(r1)
        lwz r0, 0x94(r1)
        mtlr r0
        addi r1, r1, 0x90
        blr
half:
        .float 0.5
onehalf:
        .float 1.5
tiny:
        .float 0.0001
snap:
        .float -2.0
deg180:
        .float 180.0
deg2rad:
        .float 0.017453292
obj_next:
        .word 0
""" + ''.join("k_%d:\n        .float %r\n" % (d, 1.0 / d) for d in (72, 42, 20, 6, 56, 30, 12, 2)))


def horner(fd, fx2, ds):
    """fd = 1 - x2/d0 (1 - x2/d1 (... (1 - x2/dn))) for ds = [dn ... d0] (innermost first); f4 = 1.0;
    the constants 1/d are inline-loaded from k_<d> labels (made by consts_for)"""
    out = ["        fmr %s, f4" % fd]
    for d in ds:
        out += ["        lfs f6, k_%d@l(r12)" % d, "        fmuls f6, f6, %s" % fx2, "        fmuls f6, f6, %s" % fd,
                "        fsubs %s, f4, f6" % fd]
    return "\n".join(out)


def thread_code(a):
    """Thread_Start / Thread_Stop handlers, the per-object thread runner (step entries), thread_drop"""
    fl = lambda reg, fail: chk_t(reg, 'r0', fail)     # noqa: E731
    D = dict(n=THREAD_N, size=THREAD_SIZE, reset=STATE_RESET, interp=INTERP, stop=THREAD_STOP_BIT >> 16)
    a.asm("""
# --- thread_drop(r3 accessor, r4 ID (-1 = all), r5 running state or 0): stop matching threads;
#     the one whose state is r5 (it's running this command) is only marked to stop after this frame
thread_drop:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stmw r28, 0x10(r1)
        mr r31, r3
        mr r30, r4
        mr r29, r5
        lis r28, threads@ha
        addi r28, r28, threads@l
        li r0, %(n)d
        stw r0, 8(r1)
td_loop:
        lwz r0, 0(r28)
        cmplw r0, r31
        bne td_next
        cmpwi r30, -1
        beq td_hit
        lwz r0, 8(r28)
        cmpw r0, r30
        bne td_next
td_hit:
        addi r3, r28, 0x10
        cmplw r3, r29
        bne td_free
        lwz r0, 0xC(r28)
        oris r0, r0, %(stop)d
        stw r0, 0xC(r28)
        b td_next
td_free:
        bl 0x%(reset)08X
        li r0, 0
        stw r0, 0(r28)
td_next:
        addi r28, r28, %(size)d
        lwz r12, 8(r1)
        addi r12, r12, -1               # (not r0: addi rD, r0, n is li)
        stw r12, 8(r1)
        cmpwi r12, 0
        bne td_loop
        lmw r28, 0x10(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# --- Thread_Start(Offset, ID, Flags){ block ... Script_End }: r3 accessor, r4 table, r5 state, r6 ctx, r7 params
h_thread:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r26, 0x18(r1)
        mr r31, r3
        mr r30, r4
        mr r29, r5
        mr r28, r7
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq th_step""" % D + fl('r31', 'th_step') + """
        lwz r27, 4(r28)                 # ID
        lis r26, threads@ha
        addi r26, r26, threads@l
        li r11, %(n)d
th_find:                                # this object's thread with this ID: restart it
        lwz r0, 0(r26)
        cmplw r0, r31
        bne th_fnext
        lwz r0, 8(r26)
        cmpw r0, r27
        bne th_fnext
        addi r3, r26, 0x10
        cmplw r3, r29                   # (not from inside itself)
        beq th_step
        bl 0x%(reset)08X
        b th_take
th_fnext:
        addi r26, r26, %(size)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne th_find
        lis r26, threads@ha
        addi r26, r26, threads@l
        li r11, %(n)d
th_free:
        lwz r0, 0(r26)
        cmpwi r0, 0
        beq th_take
        addi r26, r26, %(size)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne th_free
        b th_step                       # all taken: not started
th_take:
        stw r31, 0(r26)
        stw r30, 4(r26)
        stw r27, 8(r26)
        lwz r0, 8(r28)
        rlwinm r0, r0, 0, 1, 31
        stw r0, 0xC(r26)
        li r0, 0
        li r11, 0x34
th_zero:
        addi r12, r26, 0x10
        stwx r0, r12, r11
        addi r11, r11, -4
        cmpwi r11, 0
        bge th_zero
        li r0, -1
        stw r0, 0x18(r26)               # state +8: running
        lwz r3, 4(r29)
        addi r3, r3, 16                 # the block's first command (after Thread_Start's 4 words)
        stw r3, 0x10(r26)
        stw r3, 0x14(r26)
th_step:
        lwz r3, 8(r29)
        cmpwi r3, -1
        bne th_ret
        lwz r0, 0(r28)                  # jump over the block (as True)
        slwi r0, r0, 2
        lwz r11, 4(r29)
        add r11, r11, r0
        stw r11, 4(r29)
        li r3, 2
th_ret:
        lmw r26, 0x18(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- Thread_Stop(ID)
h_thread_stop:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        mr r31, r5
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq ts2_step
        lwz r4, 0(r7)
        mr r5, r31
        bl thread_drop
ts2_step:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne ts2_ret
        lwz r11, 4(r31)
        addi r11, r11, 8
        stw r11, 4(r31)
        li r3, 2
ts2_ret:
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# --- thread_run(r3 accessor): one frame of each of its threads ---------------------------------------
thread_run:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r27, 0x1C(r1)
        mr r31, r3
        li r30, 0                       # in hitlag?
        lwz r3, 0x48(r31)               # StopModule""" % D + fl('r3', 'tr_go') + """
        lbz r30, 0x10(r3)
tr_go:
        lis r29, threads@ha
        addi r29, r29, threads@l
        li r28, %(n)d
tr_loop:
        lwz r0, 0(r29)
        cmplw r0, r31
        bne tr_next
        lwz r0, 0xC(r29)
        andi. r0, r0, 1                 # Flags 1: also in hitlag
        bne tr_run
        cmpwi r30, 0
        bne tr_next
tr_run:
        lwz r3, 4(r29)
        mr r4, r31
        addi r5, r29, 0x10
        li r6, 1
        lis r12, one@ha
        lfs f1, one@l(r12)
        lfs f2, zero@l(r12)
        bl 0x%(interp)08X
        lwz r0, 0x14(r29)               # state +4 = 0: ended (Script_End)
        cmpwi r0, 0
        beq tr_end
        cmpwi r3, 0
        beq tr_end
        lwz r0, 0xC(r29)
        rlwinm. r0, r0, 0, 0, 0         # stop bit (Thread_Stop from inside itself)
        beq tr_next
tr_end:
        addi r3, r29, 0x10
        bl 0x%(reset)08X
        li r0, 0
        stw r0, 0(r29)
tr_next:
        addi r29, r29, %(size)d
        addi r28, r28, -1
        cmpwi r28, 0
        bne tr_loop
        lmw r27, 0x1C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
""" % D)
    for k, h in enumerate(STEP_HOOKS):
        a.asm("""
hk_step%(k)d:                            # object step entry: r4 -> accessor; save everything, run its threads
        stwu r1, -0xA0(r1)
        mflr r0
        stw r0, 0xA4(r1)
        stmw r3, 0x10(r1)
        mfcr r0
        stw r0, 0x88(r1)
        stfd f1, 0x90(r1)
        stfd f2, 0x98(r1)""" % dict(k=k) + fl('r4', 'hs%d_out' % k) + """
        lwz r3, 0(r4)""" + fl('r3', 'hs%d_out' % k) + """
        bl thread_run
hs%(k)d_out:
        lfd f1, 0x90(r1)
        lfd f2, 0x98(r1)
        lwz r0, 0x88(r1)
        mtcrf 0xFF, r0
        lmw r3, 0x10(r1)
        lwz r0, 0xA4(r1)
        mtlr r0
        addi r1, r1, 0xA0
        stwu r1, -0x38(r1)
        b 0x%(back)08X
""" % dict(k=k, back=h + 4))


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
        own = {'Track_Target': TRACK_PARAMS, 'Thread_Start': THREAD_PARAMS, 'Thread_Stop': THREAD_STOP_PARAMS}
        if name in own:
            e = {'_command': name, '_new': True, '_name': name, '_size': size, '_desc': SM4SHCOMMAND_DESC[name],
                 '_format': [t for _n, t, _d in own[name]]}
            assert len(own[name]) == size - 1
            for k, (pname, _t, desc) in enumerate(own[name]):
                e[str(k)] = {'name': pname, 'desc': desc, 'confidence': 'high'}
            d['%08X' % crc(name)] = e
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
