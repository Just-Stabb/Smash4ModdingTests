#!/usr/bin/env python3
"""Runs base_customs_cave.py's patches in unicorn against the unpatched game.

  python3 tools/base_customs_test.py PATCHED.rpx ORIGINAL.rpx [--others ARGS_FILE ...]

Checks: the two in-place jumps are the generator's and carry no relocation; no word overlaps another
cave script (--others); 0x02A4D40C(id) for ids 0-0xC7; the bitfield index 0x02A51368(id, slot,
variant) for every id / slot / variant 0-4; 0x02946468(db, skill id) for every skill id 0-0xFFF:
unpatched for every id but 59, 59 = Mario's (4).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import base_customs_cave as C  # noqa: E402
import rpx_patch as R  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_LR  # noqa: E402

fails = 0


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def call(mu, fn, *args):
    for r, v in zip((UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5), args):
        mu.reg_write(r, v & 0xFFFFFFFF)
    mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.emu_start(fn, RET, count=10000)
    v = mu.reg_read(UC_PPC_REG_3)
    return v - (1 << 32) if v & 0x80000000 else v


def main():
    argv = sys.argv[1:]
    others = []
    while '--others' in argv:
        i = argv.index('--others')
        others.append(argv[i + 1])
        del argv[i:i + 2]
    patched, orig = argv[:2]
    patches, labels, m = C.build(rpx=orig)
    p, o = machine(patched), machine(orig)

    def w(mu, a):
        return struct.unpack('>I', mu.mem_read(a, 4))[0]
    check('every generated word is in the patched RPX', [a for a, v in patches.items() if w(p, a) != v], [])

    d, _o, _e, secs = R.load(patched)
    rel = set()
    for s in secs:
        if s[1] == 4:
            data = R.section_data(d, s)
            rel.update(struct.unpack('>I', data[i:i + 4])[0] & ~3 for i in range(0, len(data), 12))
    check('no relocation on a patched word', sorted(hex(a) for a in patches if a in rel), [])
    mine = set(patches)
    for path in others:
        theirs = set()
        for t in open(path).read().split():
            if '=' in t and not t.startswith(('reloc:', 'grow:')):
                theirs.add(int(t.split('=')[0], 0) & ~3)
            if t.startswith('reloc:'):
                lo, hi = t[6:].split('=')[0].split('-')
                theirs.update(range(int(lo, 0) & ~3, int(hi, 0), 4))
        check('no overlap with %s' % os.path.basename(path), sorted(hex(a) for a in mine & theirs), [])

    want_map = {i: m.get(i, i) for i in range(0x101)}
    got = [call(p, C.OWN_INDEX, i) for i in range(0xC8)]
    ref = [call(o, C.OWN_INDEX, want_map[i]) for i in range(0xC8)]
    check('0x02A4D40C(id): unpatched for every id, 59 -> Mario (3)', (got, got[59]), (ref, 3))

    bad = []
    for cid in range(0x53):
        for slot in range(5):
            for var in range(5):
                g = call(p, 0x02A51368, cid, slot, var)
                r = call(o, 0x02A51368, want_map[cid], slot, var)
                if g != r:
                    bad.append((cid, slot, var, g, r))
    check('0x02A51368(id, slot, variant): ids 0-0x52 x slots 0-4 x variants 0-4 as unpatched (59 as 4)', bad, [])
    check('  id 59 slot 0 variant 1 = Mario\'s index 36, id 58 (Bayonetta... DLC) still -1',
          (call(p, 0x02A51368, 59, 0, 1), call(p, 0x02A51368, 58, 0, 1), call(o, 0x02A51368, 59, 0, 1)), (36, -1, -1))

    bad = []
    for sk in range(0x1000):
        cf = (sk >> 4) & 0xFF
        rs = (((want_map[cf + 1] - 1) & 0xFF) << 4) | (sk & 0xF)
        g = call(p, C.LINEAR, 0x7F000100, sk)
        r = call(o, C.LINEAR, 0x7F000100, rs)
        if g != r:
            bad.append((hex(sk), g, r))
    check('0x02946468(db, skill id): every skill id 0-0xFFF as unpatched (char field 58 as 3)', bad, [])
    check('  Supamario Nt variant 1 (0x3A1) = Mario\'s (0x31) = 36; variant 0 = -1',
          (call(p, C.LINEAR, 0, 0x3A1), call(o, C.LINEAR, 0, 0x31), call(p, C.LINEAR, 0, 0x3A0)), (36, 36, -1))
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
