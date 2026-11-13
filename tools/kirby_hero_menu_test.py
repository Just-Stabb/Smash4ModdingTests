#!/usr/bin/env python3
"""Tests tools/kirby_hero_menu_cave.py's patch (exe_v45) in unicorn and against its data.

  python3 tools/kirby_hero_menu_test.py PATCHED.rpx ORIGINAL.rpx

- the original has `cmpwi r0, 0x45` / `bne` and `lwz r11, 0xC(r11)` at the panel cave's hooks, v44's Robin copy list
  (8 records) behind the header and reserve entries 10-14 free;
- the kind stub: cr0 "equal" for 0x45 and 8 only (every kind 0-0x50), the kind kept;
- the int stub: the int array pointer as loaded, 0x48 lower for Kirby only;
- the hooks are bl to the stubs; the Robin copy header -> 13 records (v44's 8 + Hero's 5 spell weapons, the thunder's
  spawner); reserve entries 10-14 name 0x196, 0x197, 0x195, 0x194, 0x193.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kirby_copy_new_test as T  # noqa: E402
import kirby_hero_menu_cave as C  # noqa: E402
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_0, UC_PPC_REG_LR, UC_PPC_REG_CR  # noqa: E402

check = T.check


def live_after(img, at, limit=400):
    """registers read before written along the code from `at` (straight line, following unconditional branches and
    both ways of conditional ones, up to `limit` instructions; calls end a path: r3-r12 are then dead)"""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
    live, seen, todo = set(), set(), [(at, frozenset())]
    while todo and len(seen) < limit:
        a, written = todo.pop()
        while (a, written) not in seen and len(seen) < limit:
            seen.add((a, written))
            ins = next(md.disasm(img.read(a, 4), a))
            regs = [int(x) for x in re.findall(r'\br(\d+)\b', ins.op_str)]
            m = ins.mnemonic
            if m.startswith(('st', 'cmp', 'mt', 'tw')) or m.startswith('b'):
                rd, wr = set(regs), set()
            elif regs:
                rd, wr = set(regs[1:]), {regs[0]}
            else:
                rd, wr = set(), set()
            live |= rd - written
            written = written | wr
            m = ins.mnemonic
            if m in ('blr', 'bctr', 'bctrl') or m == 'bl':
                break
            if m == 'b':
                a = int(ins.op_str.split()[-1], 0)
                continue
            if m.startswith('b') and not m.endswith('lr') and not m.endswith('ctr'):
                todo.append((int(ins.op_str.split()[-1], 0), written))
            a += 4
    return live


def main():
    new, old = T.Img(sys.argv[1]), T.Img(sys.argv[2])
    check('original 0x%08X cmpwi r0, 0x45' % C.HOOK_KIND, old.w(C.HOOK_KIND), 0x2C000045)
    check('original next: bne', old.w(C.HOOK_KIND + 4) >> 26, 16)
    check('original 0x%08X lwz r11, 0xC(r11)' % C.HOOK_INTS, old.w(C.HOOK_INTS), 0x816B000C)
    hdr = C.V44.ROBIN_HDR
    recs, n = old.w(hdr), old.w(hdr + 4)
    check('original Robin copy list: v44\'s 8 records',
          [tuple(old.w(recs + 16 * i + 4 * j) for j in range(4)) for i in range(n)],
          list(C.V44.ROBIN_RECORDS) + list(C.V44.NEW_RECORDS))
    for i, _k in C.RESERVE:
        e = C.V44.KIRBY_RESERVE + 0x10 * i
        check('original reserve entry %d free' % i, [old.w(e + 4 * j) for j in range(4)], [0x10, 0, 0, 0])
    check('cave inside the proven code region (crash fix v1)', C.CAVE >= 0x04B00000 and C.LIMIT <= 0x04BD4000, True)
    for a in range(C.CAVE, C.CAVE + 0x200, 4):
        if old.w(a):
            check('cave 0x%08X free in the original' % a, old.w(a), 0)
    a, _out = C.build()
    lab = a.labels
    for hook, name in ((C.HOOK_KIND, 'kind_stub'), (C.HOOK_INTS, 'ints_stub')):
        w = new.w(hook)
        check('0x%08X bl %s' % (hook, name), (w >> 26, w & 3, T.bl_target(hook, w)), (18, 1, lab[name]))
    mu = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
    mu.mem_map(C.CAVE & ~0xFFF, 0x2000)
    mu.mem_write(C.CAVE & ~0xFFF, new.read(C.CAVE & ~0xFFF, 0x2000))
    mu.mem_map(0x7F000000, 0x10000)
    bad = []
    for k in range(0x51):
        mu.reg_write(UC_PPC_REG_0, k)
        mu.reg_write(UC_PPC_REG_CR, 0)
        mu.reg_write(UC_PPC_REG_LR, 0x7F00FFF0)
        mu.emu_start(lab['kind_stub'], 0x7F00FFF0, count=50)
        eq = bool(mu.reg_read(UC_PPC_REG_CR) >> 29 & 1)
        kept = struct.unpack('>I', bytes(mu.mem_read(lab['panel_kind'], 4)))[0]
        if eq != (k in (C.BRAVE, C.KIRBY)) or kept != k:
            bad.append(hex(k))
        mu.mem_write(0x7F000100, struct.pack('>I', 0x12345678))
        mu.reg_write(UC_PPC_REG_0 + 11, 0x7F000100 - 0xC)
        mu.reg_write(UC_PPC_REG_LR, 0x7F00FFF0)
        mu.emu_start(lab['ints_stub'], 0x7F00FFF0, count=50)
        r11 = mu.reg_read(UC_PPC_REG_0 + 11)
        if r11 != (0x12345678 - (C.SHIFT if k == C.KIRBY else 0)):
            bad.append('ints %x' % k)
    check('kind stub: equal for Hero and Kirby only; int array 0x48 lower for Kirby only', bad, [])
    # crash fix v2: a stub may change only the registers the panel cave doesn't read before writing them after the
    # hook (exe_v45b's kind stub clobbered r12, the fighter object the cave reads next: `lwz r12, 0xC(r12)`)
    for hook, name, own in ((C.HOOK_KIND, 'kind_stub', set()), (C.HOOK_INTS, 'ints_stub', {11})):
        live = live_after(new, hook + 4)
        for r in range(32):
            mu.reg_write(UC_PPC_REG_0 + r, 0x7F000100 - 0xC if r == 11 else 0x1000 + r)
        mu.reg_write(UC_PPC_REG_LR, 0x7F00FFF0)
        mu.emu_start(lab[name], 0x7F00FFF0, count=50)
        changed = {r for r in range(32) if r not in (1,) and mu.reg_read(UC_PPC_REG_0 + r) != (
            0x7F000100 - 0xC if r == 11 else 0x1000 + r)} - own
        check('%s: changes no register the panel cave reads after 0x%08X (live: %s)' % (name, hook, sorted(live)),
              sorted(changed & live), [])
    check('Kirby\'s ints land on the cave\'s gauge / window / rows reads',
          [0x10000000 | (i * 4 + C.SHIFT) // 4 for i in (0x8A, 0x8C, 0x8D)], [0x1000009C, 0x1000009E, 0x1000009F])
    recs, n = new.w(hdr), new.w(hdr + 4)
    check('Robin copy header -> 13 records', (recs, n), (lab['robin_list2'], 13))
    check('Robin copy records', [tuple(new.w(recs + 16 * i + 4 * j) for j in range(4)) for i in range(n)], C.records())
    for i, k in C.RESERVE:
        e = C.V44.KIRBY_RESERVE + 0x10 * i
        check('reserve entry %d names 0x%X' % (i, k), [new.w(e + 4 * j) for j in range(4)], [k, 0, 0, 0])
    print('%d failures' % len(T.FAIL))
    sys.exit(1 if T.FAIL else 0)


if __name__ == '__main__':
    main()
