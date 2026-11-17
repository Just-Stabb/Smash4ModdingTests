#!/usr/bin/env python3
"""Unicorn test of tools/hitbox_hold_cave.py (Hitbox_Hold) on an executable with acmd_ext_cave.py's patches
(exe_v46x_whipmot):

  python3 tools/hitbox_hold_test.py EXE.rpx

The cave's words are written into the emulated image (the file isn't patched). Run with the game's own code around
the hooks: the command tables (the game's CRC search, both script loaders, the handler fetch) for Hitbox_Hold and the
earlier caves' commands; Hitbox_Hold's handler on a fighter-like AttackModule (plain hitboxes, an Extra hitbox tagged by
acmd_ext's own ext_record, ID -1, mode 0 / bad modes / bad IDs, not executing, the script stepped over); set_attack's
slot hook (0x02C0874C -> hh_slotset -> acmd_ext's slot_set -> back into set_attack); and the victim handler's launch
vector store (0x02C25BF0 - 0x02C25C04 of 0x02C25318, the game's instructions around the hook) for each mode and
situation: what the damage event's +0xC / +0x10 (the speed the victim's damage energy gets) holds, against the
unpatched executable running the same instructions.
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_cave as C  # noqa: E402
import hitbox_hold_cave as H  # noqa: E402
import kind_expand as K  # noqa: E402
import acmd_ext_test  # noqa: E402
from acmd_ext_test import check, r32, w32, run, RET, CRC_TABLE, COUNT, SIZES, HANDLERS, BUF  # noqa: E402
from stage_slot_test import machine  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_0, UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5,  # noqa: E402
                               UC_PPC_REG_6, UC_PPC_REG_7, UC_PPC_REG_12, UC_PPC_REG_19, UC_PPC_REG_26, UC_PPC_REG_28,
                               UC_PPC_REG_29, UC_PPC_REG_30, UC_PPC_REG_FPR27)

REG = lambda n: UC_PPC_REG_0 + n          # noqa: E731
ACC, AM, SLOTS, STATE, FLAG, PARAMS = 0x10370000, 0x10371000, 0x10372000, 0x10373000, 0x10374000, 0x10375000
HI, REC, STACK, EXTRAS = 0x10376000, 0x10377000, 0x7F00E000, 0x10378000
NSLOT = 10


def f2bits(v):
    return struct.unpack('>Q', struct.pack('>d', v))[0]


def fbits(v):
    return struct.unpack('>I', struct.pack('>f', v))[0]


def main():
    exe = sys.argv[1]
    img = K.Image(exe)
    words, lab, s = H.build(img.w)
    om, pm = machine(exe), machine(exe)
    for at, w in words.items():
        w32(pm, at, w)
    a, _cw, _hooks = C.build()
    check('acmd_ext\'s cave as acmd_ext_cave.py builds it (ext_record / find_copy addresses)',
          [r32(om, a.addr(k)) for k in ('ext_record', 'find_copy', 'slot_set')],
          [img.w(a.addr(k)) for k in ('ext_record', 'find_copy', 'slot_set')])
    check('slot set hook went to acmd_ext\'s slot_set', s['slotset_to'], a.addr('slot_set'))
    check('present() on the patched words', H.present(lambda x: words.get(x, img.w(x))), True)
    check('present() on the unpatched exe', H.present(img.w), False)
    try:
        H.build(lambda x: words.get(x, img.w(x)))
        check('building over itself refused', False, True)
    except AssertionError:
        check('building over itself refused', True, True)

    # ---- command tables
    pairs = [(r32(om, CRC_TABLE + 8 * i), r32(om, CRC_TABLE + 8 * i + 4)) for i in range(COUNT)]
    check('Hitbox_Hold CRC not a game command', H.CMD_CRC in dict(pairs), False)
    check('Hitbox_Hold CRC not an acmd_ext command', H.CMD_CRC in [C.crc(c[0]) for c in C.COMMANDS], False)

    def lookup(mu, crc):
        run(mu, 0x02BEE154, RET, {UC_PPC_REG_3: crc})
        return mu.reg_read(UC_PPC_REG_3)
    check('vanilla CRCs keep their index', [hex(c) for c, i in pairs[::17] if lookup(pm, c) != i], [])
    check('acmd_ext CRCs keep theirs', [lookup(pm, C.crc(c[0])) for c in C.COMMANDS],
          [C.NEW_BASE + k for k in range(len(C.COMMANDS))])
    others = {n: zlib.crc32(n.encode()) & 0xFFFFFFFF for n in ('Line_Test', 'Var_Reset_Set')}
    check('earlier caves\' commands (Line_Test, Var_Reset_Set) keep their index',
          [lookup(pm, c) for c in others.values()], [lookup(om, c) for c in others.values()])
    check('... which the unpatched exe has', [lookup(om, c) != 0xFFFFFFFF for c in others.values()], [True, True])
    check('Hitbox_Hold -> its index', lookup(pm, H.CMD_CRC), H.HH_INDEX)
    check('unknown CRC -> -1', lookup(pm, 0x12345678), 0xFFFFFFFF)
    idx = dict(pairs)
    size = {i: r32(om, SIZES + 4 * i) for _, i in pairs}
    lt = lookup(om, others['Line_Test'])
    script = [0xB738EABD, H.CMD_CRC, 0x42ACFE7D, others['Line_Test']]
    want_idx = [idx[0xB738EABD], H.HH_INDEX, idx[0x42ACFE7D], lt]
    want_size = [size[want_idx[0]], 3, size[want_idx[2]], 11]
    for loop, (start, stop, regs) in enumerate([
            (0x02BEE2B4, 0x02BEE2D8, {UC_PPC_REG_28: BUF, UC_PPC_REG_29: 0, UC_PPC_REG_30: len(script),
                                      UC_PPC_REG_4: SIZES}),
            (0x02BEE3B4, 0x02BEE3D8, {UC_PPC_REG_28: BUF, UC_PPC_REG_4: 0, UC_PPC_REG_29: len(script),
                                      UC_PPC_REG_30: SIZES})]):
        pm.mem_write(BUF, b'\0' * 0x1000)
        o, offs = 0, []
        for c, sz in zip(script, want_size):
            w32(pm, BUF + 4 * o, c)
            offs.append(o)
            o += sz
        run(pm, start, stop, regs)
        check('loader %d: indices (Hitbox, Hitbox_Hold, FRAME, Line_Test)' % (loop + 1),
              [r32(pm, BUF + 4 * x) for x in offs], want_idx)
        check('loader %d: words stepped' % (loop + 1), pm.reg_read(UC_PPC_REG_29 if loop == 0 else UC_PPC_REG_4),
              sum(want_size))

    def fetch(mu, i):
        run(mu, 0x02BEE84C, 0x02BEE854, {UC_PPC_REG_7: i, UC_PPC_REG_29: HANDLERS, UC_PPC_REG_12: 0x55})
        return mu.reg_read(UC_PPC_REG_0)
    check('vanilla handlers unchanged', [i for _, i in pairs[::23] if fetch(pm, i) != r32(om, HANDLERS + 4 * i)], [])
    check('Line_Test / Var_Reset_Set handlers kept', [fetch(pm, lookup(om, c)) for c in others.values()],
          [fetch(om, lookup(om, c)) for c in others.values()])
    check('Hitbox_Hold handler', fetch(pm, H.HH_INDEX), lab['h_hold'])

    # ---- an object: accessor +0x50 AttackModule (+0x3C 10 slots, +0x40 slots of 0x84)
    for mu in (pm, om):
        w32(mu, ACC + 0x50, AM)
        w32(mu, AM + 0x3C, NSLOT)
        w32(mu, AM + 0x40, SLOTS)
    slot = lambda i: SLOTS + 0x84 * i       # noqa: E731

    def put_hitbox(mu, i, angle=361, kbg=10, fkb=0, bkb=12, bone=0):
        mu.mem_write(slot(i), b'\0' * 0x84)
        mu.mem_write(slot(i) + 0x18, struct.pack('>ff', 0.4, 6.0))
        mu.mem_write(slot(i) + 0x20, struct.pack('>4i', angle, kbg, fkb, bkb))
        w32(mu, slot(i) + 0x3C, bone)
    for i in range(NSLOT):
        put_hitbox(pm, i)
        put_hitbox(om, i)
    tag = lambda i: struct.unpack('>H', pm.mem_read(slot(i) + C.TAG_OFF, 2))[0]    # noqa: E731

    def hold(hid, mode, execute=1):
        w32(pm, STATE + 4, 0x1000)
        w32(pm, STATE + 8, 0xFFFFFFFF)
        pm.mem_write(FLAG + 8, bytes([execute]))
        pm.mem_write(PARAMS, struct.pack('>ii', hid, mode))
        for r in range(14, 32):
            pm.reg_write(REG(r), 0x1000 + r)
        run(pm, lab['h_hold'], RET, {UC_PPC_REG_3: ACC, UC_PPC_REG_5: STATE, UC_PPC_REG_6: FLAG, UC_PPC_REG_7: PARAMS})
        kept = [r for r in range(14, 32) if r != 1 and pm.reg_read(REG(r)) != 0x1000 + r]
        return pm.reg_read(UC_PPC_REG_3), r32(pm, STATE + 4) - 0x1000, kept
    check('Hitbox_Hold(2, 1): returns 2, steps 3 words, callee-saved kept', hold(2, 1), (2, 12, []))
    check('... plain hitbox 2 tagged 0xED01, the others not', [hex(tag(i)) for i in range(4)],
          ['0x0', '0x0', '0xed01', '0x0'])
    hold(2, 2)
    check('Hitbox_Hold(2, 2): 0xED02', tag(2), 0xED02)
    hold(2, 0)
    check('Hitbox_Hold(2, 0): mark off', tag(2), 0)
    hold(2, 7)
    check('Mode 7: as 0 (off)', tag(2), 0)
    hold(10, 1)
    hold(-2, 1)
    check('ID 10 (past the 10 slots) / -2: nothing marked', [tag(i) for i in range(NSLOT)], [0] * NSLOT)
    r = hold(1, 1, execute=0)
    check('not executing: nothing marked, still stepped', (tag(1), r[1]), (0, 12))
    hold(-1, 2)
    check('ID -1: every slot 0xED02', [tag(i) for i in range(NSLOT)], [0xED02] * NSLOT)
    hold(-1, 0)
    check('ID -1, Mode 0: every mark off', [tag(i) for i in range(NSLOT)], [0] * NSLOT)
    w32(pm, ACC + 0x50, 0)
    hold(0, 1)
    check('no AttackModule: nothing (no crash)', tag(0), 0)
    w32(pm, ACC + 0x50, AM)

    # ---- an Extra hitbox in slot 3: acmd_ext's own ext_record tags it (0xEC00 | n)
    def ext_record(i, mu=pm):
        mu.mem_write(PARAMS + 0x100, struct.pack('>i', i))
        mu.mem_write(EXTRAS, struct.pack('>ffifif', -3.0, 0.0, 0, 0.0, 0, 0.0))
        run(mu, a.addr('ext_record'), RET, {UC_PPC_REG_3: ACC, UC_PPC_REG_4: PARAMS + 0x100, UC_PPC_REG_5: EXTRAS})
        return struct.unpack('>H', mu.mem_read(slot(i) + C.TAG_OFF, 2))[0]
    t3 = ext_record(3)
    ext_record(3, om)
    check('ext_record tagged slot 3 (0xEC00 | n)', t3 >> 8, 0xEC)
    n3 = t3 & 0xFF
    hold(3, 1)
    ext = lab['hh_ext']
    check('Hitbox_Hold on the Extra hitbox: tag kept, HH_EXT[n] = {slot 3, 1}',
          (tag(3), r32(pm, ext + 8 * n3), r32(pm, ext + 8 * n3 + 4)), (t3, slot(3), 1))
    hold(4, 1)                               # a plain one next to it

    # ---- the victim: the game's instructions 0x02C25BF0 - 0x02C25C04 (stfs f27, 0(r30); the vector's loads and
    #      stores) with r28 the hit info (its data copy at +0x44), r19 the situation, r1 the handler's frame
    def victim(mu, i, x, y, situation=0, data=None):
        mu.mem_write(HI + 0x44, data if data is not None else bytes(mu.mem_read(slot(i), 0x68)))
        mu.mem_write(STACK + 0xC, struct.pack('>ff', x, y))
        mu.mem_write(REC, b'\xAA' * 0x20)
        mu.reg_write(UC_PPC_REG_FPR27, f2bits(13.8))
        run(mu, 0x02C25BF0, 0x02C25C04, {UC_PPC_REG_1: STACK, UC_PPC_REG_28: HI, UC_PPC_REG_19: situation,
                                         UC_PPC_REG_30: REC})
        mu.reg_write(UC_PPC_REG_1, STACK)
        got = tuple(round(v, 4) for v in struct.unpack('>ff', mu.mem_read(REC + 0xC, 8)))
        return got, (round(struct.unpack('>f', mu.mem_read(REC, 4))[0], 2), bytes(mu.mem_read(REC + 4, 8)),
                     bytes(mu.mem_read(REC + 0x14, 0xC)), mu.reg_read(UC_PPC_REG_28), mu.reg_read(UC_PPC_REG_19))
    v = (0.414, 0.0)
    rest = (13.8, b'\xAA' * 8, b'\xAA' * 0xC, HI, 0)
    check('unpatched exe: the vector stored as it is', victim(om, 2, *v), (v, rest))
    check('no mark (slot 0): the same in the patched exe', victim(pm, 0, *v), (v, rest))
    hold(2, 1)
    check('Mode 1, victim on the ground, 361 at 0 degrees: held (0, 0); the event\'s other words as before',
          victim(pm, 2, *v), ((0.0, 0.0), rest))
    check('Mode 1, ground, facing the other way (-x)', victim(pm, 2, -0.414, 0.0)[0], (0.0, 0.0))
    check('Mode 1, ground, y = -0.0', victim(pm, 2, 0.414, -0.0)[0], (0.0, 0.0))
    check('Mode 1, ground, downward (spike): held', victim(pm, 2, 0.2, -0.5)[0], (0.0, 0.0))
    check('Mode 1, ground, launched upward (361 at 60+ knockback): as the game', victim(pm, 2, 1.8, 1.2)[0],
          (1.8, 1.2))
    check('Mode 1, victim in the air (situation 2): as the game', victim(pm, 2, 0.29, 0.29, situation=2)[0],
          (0.29, 0.29))
    hold(2, 2)
    check('Mode 2: in the air too, held', victim(pm, 2, 0.29, 0.29, situation=2)[0], (0.0, 0.0))
    check('Mode 2: a big launch held', victim(pm, 2, 3.0, 2.5)[0], (0.0, 0.0))
    hold(2, 0)
    check('Mode 0 again: as the game', victim(pm, 2, *v)[0], v)
    check('Extra hitbox marked (slot 3), ground: held', victim(pm, 3, *v)[0], (0.0, 0.0))
    check('... its HitstunMul extras still found by acmd_ext\'s find_copy', find_copy(pm, a, slot(3)) != 0, True)
    check('plain marked hitbox (0xED01): acmd_ext sees no Extra tag', find_copy(pm, a, slot(4)), 0)
    other = bytearray(pm.mem_read(slot(3), 0x68))
    other[0x28:0x2C] = struct.pack('>i', 5)
    check('an Extra-tagged copy that is not that hitbox (FKB differs): as the game',
          victim(pm, 3, *v, data=bytes(other))[0], v)
    check('Extra hitbox in another slot with its own entry, unmarked: as the game',
          (ext_record(5), victim(pm, 5, *v)[0])[1], v)

    # ---- set_attack's slot hook: new data in slot 3 drops its marks (0x02C0874C -> hh_slotset -> slot_set -> back)
    w32(pm, AM + 0x14, 0x5150)
    run(pm, H.SLOTSET_AT, H.SLOTSET_AT + 4, {UC_PPC_REG_26: slot(3), UC_PPC_REG_28: AM})
    check('slot hook: back in set_attack with acmd_ext\'s r10 (lwz r10, 0x14(r28))',
          (pm.reg_read(REG(10)), tag(3)), (0x5150, 0))
    check('... HH_EXT[n] of slot 3 cleared, slot 4\'s plain mark untouched by it',
          (r32(pm, ext + 8 * n3), tag(4)), (0, 0xED01))
    hold(3, 1)
    check('a plain hitbox in slot 3 now, unmarked until Hitbox_Hold: then 0xED01', tag(3), 0xED01)
    run(pm, H.SLOTSET_AT, H.SLOTSET_AT + 4, {UC_PPC_REG_26: slot(3), UC_PPC_REG_28: AM})
    t3b = ext_record(3)
    check('a new Extra hitbox in slot 3 (new entry), no Hitbox_Hold: as the game', (t3b != t3, victim(pm, 3, *v)[0]),
          (True, v))
    # a stale HH_EXT entry for an entry index reused by another slot: the slot check refuses it
    w32(pm, ext + 8 * (t3b & 0xFF), slot(6))
    w32(pm, ext + 8 * (t3b & 0xFF) + 4, 2)
    check('HH_EXT naming another slot: as the game', victim(pm, 3, *v)[0], v)
    check('debug counters: commands run, hits held', (r32(pm, lab['hh_dbg']) > 0, r32(pm, lab['hh_held'])),
          (True, 7))
    sys.exit(1 if acmd_ext_test.fails else 0)


def find_copy(pm, a, s):
    pm.mem_write(HI + 0x44, bytes(pm.mem_read(s, 0x68)))
    run(pm, a.addr('find_copy'), RET, {UC_PPC_REG_5: HI + 0x44})
    return pm.reg_read(UC_PPC_REG_5)


if __name__ == '__main__':
    main()
