#!/usr/bin/env python3
"""Runs the game's mark name lookup 0x0293DDD0(7, id) (what ui_mark_db.bin's loader calls for each row)
in a patched RPX and the original, in unicorn.

  python3 tools/series_test.py PATCHED.rpx ORIGINAL.rpx [--others ARGS_FILE ...]

Checks: the stub's three words and the cave are the generator's; no word overlaps another cave script
(--others); every id 0-0xFFFF gives the same name as unpatched (the same pointer, or none), but the
new ones: 0x2A -> "minecraft"; the stub's relocations moved (the loader won't rewrite it).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import series_cave as C  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_LR  # noqa: E402

fails = 0


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def words_of(path):
    out = {}
    for tok in open(path).read().split():
        if '=' in tok and not tok.startswith(('reloc:', 'grow:')):
            k, v = tok.split('=')
            out[int(k, 0)] = int(v, 0)
    return out


def main():
    a = sys.argv[1:]
    others = [a[i + 1] for i, x in enumerate(a) if x == '--others']
    patched, original = a[0], a[1]
    patches, n = C.build(original)
    pm, om = machine(patched), machine(original)

    def r32(mu, addr):
        return struct.unpack('>I', mu.mem_read(addr, 4))[0]
    check('patch words in place', all(r32(pm, k) == v for k, v in patches.items()), True)
    import rpx_patch as R
    d, _o, _e, secs = R.load(patched)
    left = []
    for s in secs:
        if s[1] == 4:
            data = R.section_data(d, s)
            left += [off for off, in (struct.unpack('>I', data[o:o + 4]) for o in range(0, len(data), 12))
                     if C.STUB + 4 <= off < C.STUB + 16]
    check('no relocation left on the stub', left, [])
    mine = set(patches)
    for o in others:
        check('no overlap with %s' % os.path.basename(o), sorted(hex(k) for k in mine & set(words_of(o))), [])

    def lookup(mu, i):
        mu.reg_write(UC_PPC_REG_3, 7)
        mu.reg_write(UC_PPC_REG_4, i)
        mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
        mu.reg_write(UC_PPC_REG_LR, RET)
        mu.emu_start(0x0293DDD0, RET, count=20000)
        return mu.reg_read(UC_PPC_REG_3)

    def cstr(mu, p):
        if not p:
            return None
        b = bytes(mu.mem_read(p, 64))
        return b[:b.index(b'\0')].decode('ascii', 'replace')
    diffs, new = [], {}
    for i in range(0x10000):
        p, o = lookup(pm, i), lookup(om, i)
        if p != o:
            if o == 0 or (o and r32(om, 0x10340610) == o):      # none (the fallback) before
                new[i] = cstr(pm, p)
            else:
                diffs.append(i)
    check('every game id: the same name', diffs, [])
    check('new ids', new, {0x2A: 'minecraft'})
    check('0x29 still bayonetta, 0 smashbros, 0x190 cs_all', [cstr(pm, lookup(pm, i)) for i in (0x29, 0, 0x190)],
          ['bayonetta', 'smashbros', 'cs_all'])
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
