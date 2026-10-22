#!/usr/bin/env python3
"""Tests tools/acmd_ext_cave.py in a patched RPX (unicorn): the game's own ACMD loader / interpreter
code with the new commands.

  python3 tools/acmd_ext_test.py PATCHED.rpx ORIGINAL.rpx

- the hook sites held the expected instructions in the original;
- the CRC lookup 0x02BEE154: every vanilla command gives its old index, the new ones NEW_BASE + k,
  an unknown CRC -1;
- both loader loops (0x02BEE2B4, 0x02BEE3B4) over a script mixing vanilla and new commands: every
  CRC replaced by its index and the step over each command = its size;
- the interpreter's handler read (0x02BEE84C): vanilla indices give the old handlers (r12 kept), new
  ones the cave's;
- the Extra handlers (base handler stubbed: steps over its own size like the real ones): the script
  moves over base + extra words, the extras are recorded for the slot (multipliers <= 0 -> 1.0),
  ext_find finds them from the slot's data, not after the slot is rewritten, not when skipped.
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_cave as C  # noqa: E402
import rpx_patch as R  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_6,  # noqa: E402
                               UC_PPC_REG_7, UC_PPC_REG_0, UC_PPC_REG_12, UC_PPC_REG_28, UC_PPC_REG_29,
                               UC_PPC_REG_30, UC_PPC_REG_LR, UC_PPC_REG_MSR)

fails = 0
CRC_TABLE, COUNT, SIZES, HANDLERS = 0x100FAAB8, 584, 0x100FA198, 0x10350ED8
BUF = 0x7F004000


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def r32(mu, a):
    return struct.unpack('>I', mu.mem_read(a, 4))[0]


def w32(mu, a, v):
    mu.mem_write(a, struct.pack('>I', v & 0xFFFFFFFF))


def run(mu, start, stop, regs, count=200000):
    for r, v in regs.items():
        mu.reg_write(r, v & 0xFFFFFFFF)
    mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)     # FP on
    mu.emu_start(start, stop, count=count)


def main():
    patched, original = sys.argv[1:3]
    a, words, hooks = C.build()
    om, pm = machine(original), machine(patched)
    want = {C.LOOKUP: [0x3860FFFF], C.SIZE1: [0x546A103A, 0x7C7C292E, 0x7C0A202E],
            C.SIZE2: [0x546B103A, 0x7C7C292E, 0x7D8BF02E], C.FETCH: [0x54E6103A, 0x7C06E82E]}
    for at, ws in want.items():
        check('original words at 0x%08X' % at, [r32(om, at + 4 * i) for i in range(len(ws))], ws)
    check('cave words in place', all(r32(pm, C.CAVE + 4 * i) == w for i, w in enumerate(words)), True)
    check('hooks in place', all(r32(pm, k) == v for k, v in hooks.items()), True)

    pairs = [(r32(om, CRC_TABLE + 8 * i), r32(om, CRC_TABLE + 8 * i + 4)) for i in range(COUNT)]
    new = [(zlib.crc32(c[0].encode()) & 0xFFFFFFFF, C.NEW_BASE + k) for k, c in enumerate(C.COMMANDS)]
    check('new CRCs not in the game table', [c for c, _ in new if c in dict(pairs)], [])

    def lookup(mu, crc):
        run(mu, 0x02BEE154, RET, {UC_PPC_REG_3: crc})
        return mu.reg_read(UC_PPC_REG_3)
    bad = [hex(c) for c, i in pairs if lookup(pm, c) != i]
    check('vanilla CRCs keep their index (%d)' % COUNT, bad, [])
    check('new CRCs', [lookup(pm, c) for c, _ in new], [i for _, i in new])
    check('unknown CRC', lookup(pm, 0x12345678), 0xFFFFFFFF)
    check('unknown CRC (original)', lookup(om, 0x12345678), 0xFFFFFFFF)

    # a script: Hitbox (25), new 0, FRAME, new 1, Special_Hitbox (42)
    idx = dict(pairs)
    size = {i: r32(om, SIZES + 4 * i) for _, i in pairs}
    script = [0xB738EABD, new[0][0], 0x42ACFE7D, new[1][0], 0x14FCC7E4]
    want_idx = [idx[0xB738EABD], new[0][1], idx[0x42ACFE7D], new[1][1], idx[0x14FCC7E4]]
    want_size = [size[want_idx[0]], C.COMMANDS[0][1], size[want_idx[2]], C.COMMANDS[1][1], size[want_idx[4]]]
    for loop, (start, stop, regs) in enumerate([
            (0x02BEE2B4, 0x02BEE2D8, {UC_PPC_REG_28: BUF, UC_PPC_REG_29: 0, UC_PPC_REG_30: len(script), UC_PPC_REG_4: SIZES}),
            (0x02BEE3B4, 0x02BEE3D8, {UC_PPC_REG_28: BUF, UC_PPC_REG_4: 0, UC_PPC_REG_29: len(script), UC_PPC_REG_30: SIZES})]):
        pm.mem_write(BUF, b'\0' * 0x1000)
        o, offs = 0, []
        for c, s in zip(script, want_size):
            w32(pm, BUF + 4 * o, c)
            offs.append(o)
            o += s
        run(pm, start, stop, regs)
        got = [r32(pm, BUF + 4 * x) for x in offs]
        check('loader %d: indices' % (loop + 1), got, want_idx)
        total = pm.reg_read(UC_PPC_REG_29 if loop == 0 else UC_PPC_REG_4)
        check('loader %d: words stepped' % (loop + 1), total, sum(want_size))

    def fetch(mu, i):
        run(mu, 0x02BEE84C, 0x02BEE854, {UC_PPC_REG_7: i, UC_PPC_REG_29: HANDLERS, UC_PPC_REG_12: 0x55})
        return mu.reg_read(UC_PPC_REG_0), mu.reg_read(UC_PPC_REG_12)
    bad = [i for _, i in pairs if fetch(pm, i)[0] != r32(om, HANDLERS + 4 * i)]
    check('vanilla handlers unchanged', bad, [])
    check('r12 kept', fetch(pm, 50)[1], 0x55)
    check('new handlers', [fetch(pm, i)[0] for _, i in new], [a.addr(c[2]) for c in C.COMMANDS])

    # handlers, base handler stubbed (steps over its own size when state +8 == -1, returns 2)
    acc, am, slots, state, flag, params = 0x10370000, 0x10371000, 0x10372000, 0x10373000, 0x10374000, 0x10375000
    for k, (name, csize, label, base) in enumerate(C.COMMANDS):
        nbase = csize - C.N_EXTRA
        stub = [0x8005_0008, 0x2C00FFFF, 0x40820010, 0x8165_0004, 0x396B0000 | (4 * nbase), 0x91650004,
                0x38600002, 0x4E800020]          # lwz r0,8(r5); cmpwi r0,-1; bne +16; lwz r11,4(r5);
        for i, wd in enumerate(stub):           # addi r11,r11,size; stw r11,4(r5); li r3,2; blr
            w32(pm, base + 4 * i, wd)
        w32(pm, acc + 0x50, am)
        w32(pm, am + 0x40, slots)
        pm.mem_write(slots, bytes(range(256)) * 4 + b'\0' * 0x100)
        sid = 3
        slot = slots + sid * 0x84
        ext = params + 4 * (nbase - 1)

        def go(exe, extras, jump=False):
            w32(pm, params, sid)
            for i, v in enumerate(extras):
                pm.mem_write(ext + 4 * i, struct.pack('>f' if i in (0, 1, 3, 5) else '>i', v))
            w32(pm, state + 4, 0x1000)
            w32(pm, state + 8, 5 if jump else -1)
            pm.mem_write(flag + 8, bytes([exe]))
            run(pm, a.addr(label), RET, {UC_PPC_REG_3: acc, UC_PPC_REG_4: 0, UC_PPC_REG_5: state,
                                         UC_PPC_REG_6: flag, UC_PPC_REG_7: params})
            return pm.reg_read(UC_PPC_REG_3), r32(pm, state + 4) - 0x1000

        def find(data):
            run(pm, a.addr('ext_find'), RET, {UC_PPC_REG_3: data})
            return pm.reg_read(UC_PPC_REG_3)
        ret, step = go(1, [1.5, 0.0, 12, -2.0, 0, 0.5])
        check('%s: returns 2, steps over %d words' % (name, csize), (ret, step), (2, 4 * csize))
        e = find(slot)
        check('%s: found from the slot data' % name, e != 0 and (e - C.TABLE) % C.ENTRY == 0, True)
        if e:
            vals = struct.unpack('>ffiifif', bytes(pm.mem_read(e + 0x14, 0x1C)))[:6]
            got = struct.unpack('>ffifif', bytes(pm.mem_read(e + 0x14, 0x18)))
            check('%s: extras (x <= 0 -> 1)' % name, got, (1.5, 1.0, 12, 1.0, 0, 0.5))
            check('%s: tag' % name, struct.unpack('>H', pm.mem_read(slot + C.TAG_OFF, 2))[0], C.TAG | ((e - C.TABLE) // C.ENTRY))
        e2 = find(slot)
        go(1, [2.0, 3.0, 0, 1.0, 4, 1.0])
        check('%s: same slot reuses its entry' % name, find(slot), e2)
        check('%s: other slot not found' % name, find(slots + 2 * 0x84), 0)
        w32(pm, slot + 0x24, r32(pm, slot + 0x24) ^ 1)              # a plain hitbox rewrote the slot
        check('%s: not found after the slot changed' % name, find(slot), 0)
        w32(pm, slot + 0x24, r32(pm, slot + 0x24) ^ 1)
        pm.mem_write(slot + C.TAG_OFF, b'\0\0')
        ret, step = go(0, [2.0, 3.0, 0, 1.0, 4, 1.0])
        check('%s: skipped: steps, records nothing' % name, (step, find(slot)), (4 * csize, 0))
        ret, step = go(1, [2.0, 3.0, 0, 1.0, 4, 1.0], jump=True)
        check('%s: jump pending: no step' % name, step, 0)
        check('%s: bad pointer: no crash, nothing' % name, find(0x00001234), 0)

    print('%d failures' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
