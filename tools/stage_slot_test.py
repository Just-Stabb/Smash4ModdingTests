#!/usr/bin/env python3
"""Runs the patched stage-kind / cosmetic-name functions of an RPX in unicorn (tools/stage_slot_cave.py).

  python3 tools/stage_slot_test.py PATCHED.rpx ORIGINAL.rpx [NAME:COSMETIC ...]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpx_patch as R  # noqa: E402
import stage_slot_cave as C  # noqa: E402
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_3, UC_PPC_REG_1, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_LR  # noqa: E402

RET = 0x01000000


def machine(path):
    d, _s, _e, secs = R.load(path)
    mu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    blocks, ranges = [], []
    for s in secs:
        if s[1] == 1 and s[3] and s[5]:
            data = bytes(R.section_data(d, s))
            if s[3] < 0x10000000 and s[2] & 4:   # code: the grown end too
                data += b'\0' * 0x4000
            blocks.append((s[3], data))
            ranges.append([s[3] & ~0xFFF, (s[3] + len(data) + 0xFFF) & ~0xFFF])
    ranges.sort()
    merged = [ranges[0]]
    for lo, hi in ranges[1:]:
        if lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    for lo, hi in merged:
        mu.mem_map(lo, hi - lo)
    for addr, data in blocks:
        mu.mem_write(addr, data)
    mu.mem_map(RET, 0x1000)
    mu.mem_write(RET, struct.pack('>I', 0x48000000))    # b . (stop here)
    mu.mem_map(0x7F000000, 0x10000)
    return mu


def call(mu, fn, *args):
    for r, v in zip((UC_PPC_REG_3, UC_PPC_REG_4), args):
        mu.reg_write(r, v)
    mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.emu_start(fn, RET, count=10000)
    return mu.reg_read(UC_PPC_REG_3)


def cstr(mu, a):
    if not a:
        return None
    b = bytes(mu.mem_read(a, 64))
    return b[:b.index(b'\0')].decode()


def main():
    new = C.stages(sys.argv[3:])
    mu, orig = machine(sys.argv[1]), machine(sys.argv[2])
    fails = 0

    def check(what, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print('%s %s: %r%s' % ('ok  ' if ok else 'FAIL', what, got, '' if ok else ' (want %r)' % (want,)))

    count = 0x80 + 2 * len(new)
    check('kind count', call(mu, 0x02D1FE24), count)
    same = all(cstr(mu, call(mu, 0x02D1FD7C, k)) == cstr(orig, call(orig, 0x02D1FD7C, k)) and
               call(mu, 0x02D1FE10, k) == call(orig, 0x02D1FE10, k) for k in range(0x80))
    check('the 128 game kinds unchanged (name, variant)', same, True)
    for i, (name, cos) in enumerate(new):
        check('kind 0x%X name' % (0x80 + 2 * i), cstr(mu, call(mu, 0x02D1FD7C, 0x80 + 2 * i)), name)
        check('kind 0x%X name' % (0x81 + 2 * i), cstr(mu, call(mu, 0x02D1FD7C, 0x81 + 2 * i)), name)
        check('kind 0x%X variant (melee)' % (0x80 + 2 * i), call(mu, 0x02D1FE10, 0x80 + 2 * i), 0)
        check('kind 0x%X variant (end)' % (0x81 + 2 * i), call(mu, 0x02D1FE10, 0x81 + 2 * i), 1)
        check('cosmetic 0x%X name' % cos, cstr(mu, call(mu, 0x0293DCE0, cos)), name)
    for i, (name, _cos) in enumerate(new):
        for k, want in ((0x80 + 2 * i, 'stage/melee/%s'), (0x81 + 2 * i, 'stage/end/%s')):
            # the path function ends in sprintf(out, format, name) (0x04ADA3F4): stop there
            mu.reg_write(UC_PPC_REG_3, 0x7F000100)
            mu.reg_write(UC_PPC_REG_4, k)
            mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
            mu.reg_write(UC_PPC_REG_LR, RET)
            mu.emu_start(0x02D1FDA0, 0x04ADA3F4, count=1000)
            got = cstr(mu, mu.reg_read(UC_PPC_REG_4)) % cstr(mu, mu.reg_read(UC_PPC_REG_5))
            check('kind 0x%X path' % k, got, want % name)
    check('kind past the end -> ""', cstr(mu, call(mu, 0x02D1FD7C, count)), '')
    game = [c for c in list(range(0x38)) + list(range(0xC8, 0xDA)) + [0xFB, 0xFC, 0xFD, 0xFE]]
    same = all(cstr(mu, call(mu, 0x0293DCE0, c)) == cstr(orig, call(orig, 0x0293DCE0, c)) for c in game)
    check('the game\'s cosmetic names unchanged', same, True)
    check('unknown cosmetic -> null', call(mu, 0x0293DCE0, 0x99), 0)
    # needs DLC content (0x030A8D78) on a stage database of 0x60 entries, 0x30-0x38 marked DLC
    # (+0x0C, the page-2 byte), +0x0E clear: the game's DLC ids still need it, 0x38 doesn't
    for m in (mu, orig):
        db, ents = 0x7F008000, 0x7F001000
        m.mem_write(ents, b'\0' * 0x54 * 0x60)
        for i in range(0x60):
            m.mem_write(ents + 0x54 * i, struct.pack('>I', i))
            if 0x30 <= i <= 0x38:
                m.mem_write(ents + 0x54 * i + 0x0C, b'\1')
        m.mem_write(db, struct.pack('>IIII', 0, 0, 0x60, ents))
        m.mem_write(db + 0x20, struct.pack('>I', db))
    check('DLC 0x31 needs DLC content', call(mu, 0x030A8D78, 0x7F008020, 0x31), 1)
    check('page-2 0x38 needs no DLC content (game: 1)', (call(mu, 0x030A8D78, 0x7F008020, 0x38),
          call(orig, 0x030A8D78, 0x7F008020, 0x38)), (0, 1))
    check('non-DLC 0x01', call(mu, 0x030A8D78, 0x7F008020, 0x01), 0)
    # DLC content record (0x030A8E58): new ids pass without reading the record list
    check('page-2 0x38 has its DLC content record', call(mu, 0x030A8E58, 0x7F008020, 0x38), 1)
    # the loader applies relocations (unicorn doesn't): none may be left on a patched table pointer
    d, _s, _e, secs = R.load(sys.argv[1])
    left = []
    for sec in secs:
        if sec[1] == 4:  # SHT_RELA
            data = R.section_data(d, sec)
            for o in range(0, len(data), 12):
                off = struct.unpack('>I', data[o:o + 4])[0]
                if any(a <= off < a + 4 for a in C.TABLE_SITES):
                    left.append(hex(off))
    check('no relocation on the patched table pointers', left, [])
    print('FAILS', fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
