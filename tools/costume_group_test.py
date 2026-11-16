#!/usr/bin/env python3
"""Unicorn test of tools/costume_group_cave.py on the real code paths.

  python3 tools/costume_group_test.py PATCHED.rpx ORIGINAL.rpx

1. the motion path builder 0x030BB18C(r3, out, kind, type, costume) for every type / costume of kind 0x47 (male
   costumes -> body/, bodyentry/, ..., female -> body2/, bodyentry2/ ...), Bayonetta (0x38) as vanilla, the other kinds
   untouched (the string calls stubbed: the format call's format / name / folder are what is checked);
2. the shared entry / result packs' ids at each patched site (run from the site to its call: r4 = kind x 9 + 1 +
   group) and the getter 0x030C20C4 (whole: its id to 0x030BF0FC), Bayonetta's own branches included;
3. the variables 0x0F000500-502 through a fighter WorkModule's get_float (0x02F1DBE4 -> position_vars' hook ->
   get_other -> ours) with a fake fighter table and player loaders, two Byleths (c00, c03) and a Bayonetta (c05);
   another ID and an unknown WorkModule go on / read 0;
4. the original executable gives the old answers (the patch is what changes them).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kind_expand_test import Emu, REGS, STACK  # noqa: E402
from stage_slot_test import RET  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_FPR1, UC_PPC_REG_1, UC_PPC_REG_LR, UC_PPC_REG_MSR  # noqa: E402
import costume_group_cave as C  # noqa: E402

fails = 0


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


FOLD = ['body', 'bodyentry', 'bodyresult', 'bodyroutemap']


def path_emu(path):
    e = Emu(path)
    e.fmt = []
    for a in (0x032D6F6C, 0x032D4200, 0x032D3E3C):
        e.stub(a, lambda e: None)

    def fmt(e):
        e.fmt.append((e.cstr(e.r(5)), e.cstr(e.r(6)), e.cstr(e.r(7))))
    e.stub(0x032D94F4, fmt)
    return e


def path_of(e, kind, typ, costume):
    e.fmt = []
    e.call(0x030BB18C, 0, e.alloc(0x40), kind, typ, costume)
    return e.fmt[-1] if e.fmt else None


def run_site(e, start, stop, regs):
    for r, v in regs.items():
        e.mu.reg_write(REGS[r], v & 0xFFFFFFFF)
    e.mu.reg_write(UC_PPC_REG_1, STACK + 0xF0000)
    e.mu.emu_start(start, stop, count=2000)
    return e.r(4), e.r(3)


ID_SITES = [  # name, start, stop (the call), kind reg, costume reg, preset
    ('entry load', 0x030C1A34, 0x030C1A44, 30, 31, {}),
    ('entry unload', 0x030C1B08, 0x030C1B14, 30, 31, {}),
    ('result load (release)', 0x030C1C1C, 0x030C1C28, 28, 29, {}),
    ('result load', 0x030C1CD8, 0x030C1CE4, 28, 29, {'r26': True}),
    ('result unload', 0x030C1ECC, 0x030C1ED8, 30, 31, {}),
]


def ids(e, patched):
    for name, start, stop, kr, cr, pre in ID_SITES:
        for kind, costume in ((0x47, 0), (0x47, 1), (0x47, 6), (0x47, 7), (0x45, 1), (0x19, 3)):
            regs = {kr: kind, cr: costume, 29 if kr != 29 and cr != 29 else 27: 0x1234}
            if pre.get('r26'):
                regs[26] = kind * 9
            r4, _r3 = run_site(e, start, stop, regs)
            group = 1 if patched and kind == 0x47 and costume & 1 else 0
            check('%s kind 0x%X c%02d: id' % (name, kind, costume), r4, kind * 9 + 1 + group)
    got = []
    e.stub(0x030BF0FC, lambda e: got.append(e.r(5)))
    for kind, costume, want in ((0x47, 0, 1), (0x47, 3, 2 if patched else 1), (0x47, 4, 1), (0x38, 0, 1),
                                (0x38, 5, 2), (0x38, 2, 1), (0x19, 1, 1), (0x46, 7, 1)):
        got.clear()
        e.call(0x030C20C4, 0, e.alloc(0x40), kind, costume)
        check('getter kind 0x%X c%02d: id' % (kind, costume), got[:1], [kind * 9 + want])


def fighters(e, entries):
    """the fighter table and the player loaders: entries [(kind, entry index, costume)] -> their WorkModules"""
    tab, holder, ents = e.alloc(0x10, b'\0'), e.alloc(0x10, b'\0'), e.alloc(0x76B0 * len(entries), b'\0')
    e.setw(C.FIGHTERS, tab)
    e.setw(tab, holder)
    e.setw(holder, ents)
    e.setw(holder + 8, len(entries))
    mgr = e.alloc(0x80, b'\0')
    e.setw(C.LOADERS, mgr)
    wms = []
    for i, (kind, idx, costume) in enumerate(entries):
        ent = ents + 0x76B0 * i
        acc, wm, ldr = e.alloc(0x40, b'\0'), e.alloc(0x40, b'\0'), e.alloc(0x40, b'\0')
        e.mu.mem_write(ent + 0x1E, b'\x04')
        e.setw(ent + 4, kind)
        e.setw(ent + 8, idx)
        e.setw(ent + 0xC, acc)
        e.setw(acc + 0x28, wm)
        e.setw(mgr + 0x58 + 4 * idx, ldr)
        e.setw(ldr + 0x28, costume)
        wms.append(wm)
    return wms


def getf(e, wm, var):
    e.mu.reg_write(UC_PPC_REG_MSR, e.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)      # the FPU on
    e.mu.reg_write(UC_PPC_REG_FPR1, struct.unpack('>Q', struct.pack('>d', -99.0))[0])
    e.mu.reg_write(REGS[3], wm)
    e.mu.reg_write(REGS[4], var)
    e.mu.reg_write(UC_PPC_REG_1, STACK + 0xF0000)
    e.mu.reg_write(UC_PPC_REG_LR, RET)
    e.mu.emu_start(0x02F1DBE4, RET, count=20000)
    return struct.unpack('>d', struct.pack('>Q', e.mu.reg_read(UC_PPC_REG_FPR1)))[0]


def variables(path):
    e = Emu(path)
    stat = []
    e.stub(C.STAT_CAVE, lambda e: stat.append(e.r(4)))       # every other ID: kirby_stat_cave's path, untouched
    wms = fighters(e, [(0x47, 0, 0), (0x47, 1, 3), (0x38, 2, 5), (0x19, 3, 6)])
    want = {0: (0, 0, 0), 1: (3, 1, 1), 2: (5, 1, 1), 3: (6, 0, 0)}
    for i, wm in enumerate(wms):
        for v in range(3):
            check('fighter %d %s' % (i, C.VAR_NAMES[v]), getf(e, wm, C.VAR + v), float(want[i][v]))
    check('an unknown WorkModule reads 0', getf(e, 0x7F000400, C.VAR), 0.0)
    stat.clear()
    getf(e, wms[0], C.VAR + 3)
    check('0x0F000503 goes on to the stat cave', stat, [C.VAR + 3])
    stat.clear()
    getf(e, wms[0], 0x0F000423)
    check('0x0F000423 goes on to the stat cave', stat, [0x0F000423])


def main():
    new, old = sys.argv[1], sys.argv[2]
    e = path_emu(new)
    for c in range(8):
        for t in range(4):
            got = path_of(e, 0x47, t, c)
            check('path kind 0x47 type %d c%02d' % (t, c), got,
                  ('fighter/%s/motion/%s/', 'master', FOLD[t] + ('2' if c & 1 else '')))
    for kind, c, name, folder in ((0x38, 0, 'bayonetta', 'body'), (0x38, 5, 'bayonetta', 'body2'),
                                  (0x38, 2, 'bayonetta', 'body'), (0x19, 1, 'szerosuit', 'body'),
                                  (0x45, 1, 'brave', 'body'), (0x46, 3, 'pzenigame', 'body')):
        check('path kind 0x%X c%02d' % (kind, c), path_of(e, kind, 0, c), ('fighter/%s/motion/%s/', name, folder))
    check('path kind 0x47 type 5 (not a motion folder) as before', path_of(e, 0x47, 5, 1), None)
    ids(e, True)
    variables(new)
    o = path_emu(old)
    check('original: kind 0x47 c01 plays body/', path_of(o, 0x47, 0, 1), ('fighter/%s/motion/%s/', 'master', 'body'))
    ids(o, False)
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
