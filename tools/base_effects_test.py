#!/usr/bin/env python3
"""Runs tools/base_effects_cave.py's wrappers in a patched RPX in unicorn, entered at the game's own
call sites (PC = the site, stop at the next instruction), with the game's code around them where it is
self-contained and Python stubs for the resource / effect libraries.

  python3 tools/base_effects_test.py PATCHED.rpx ORIGINAL.rpx [KINDS.json] [--others ARGS_FILE ...]

Checks:
- each site is a bl to its wrapper (and was a bl to the original in ORIGINAL), no relocation left on
  it, no overlap with the other caves' words;
- every wrapper, for every game kind 0x00-0x40: exactly the original call, arguments unchanged;
  for each new kind: the original, then the same call for the base (fx_rem: the transformed base,
  fs_add: the base's Fin effect folder at id base*9 + 3, fs_rem: that id removed, fs_reg: bank
  0x400 + base, fs_rel: 0x400 + base); r14-r31 and r1 preserved, back at the site's next word;
- effect folders through the real 0x030C07A4 / 0x030C0828 call (holder add, transform map, names),
  refcounted by a model holder: Mario + Supamario, Supamario alone, two Supamarios; all removed at
  unload;
- banks through the real register / release (0x030C06E8 -> 0x030C0614, 0x030C1278, the 8-slot
  table): Supamario alone registers 0x341 and 0x303 and releases both; next to Mario they share 0x303
  (one register with data, then add-refs), and the slot table empties;
- Final Smash through the real 0x02E484D8: banks 0x441 and 0x403 registered from ids 0x24C / 0x1E.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import base_effects_cave as C  # noqa: E402
import kind_expand as K  # noqa: E402
from kind_expand_test import Emu, REGS, check  # noqa: E402
import kind_expand_test as KT  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_LR, UC_PPC_REG_PC  # noqa: E402

RES_MGR = 0x102F9028
OBJ = 0x68300000            # [RES_MGR]: +0x2C effect holder, +0x34 final holder
FX_HOLDER = 0x68301000
FS_HOLDER = 0x68302000
FRES = 0x68303000           # a fighter's resource struct (+0x3C-0x3F bytes)
FE = 0x68304000
MARK = 0x5A5A0000


def main():
    argv = sys.argv[1:]
    others = []
    while '--others' in argv:
        i = argv.index('--others')
        others.append(argv[i + 1])
        del argv[i:i + 2]
    patched, orig = argv[0], argv[1]
    spec = argv[2] if len(argv) > 2 else K.SPEC
    B = C.build(spec, orig)
    newk = [r['kind'] for r in B['kinds']]
    base = dict(zip(newk, B['base']))
    names = B['names']

    # ---- static
    pimg, oimg = K.Image(patched), K.Image(orig)
    for site, target, label, what in B['sites']:
        check('0x%08X (%s): bl %s' % (site, what, label),
              (pimg.w(site), oimg.w(site)),
              (K.b_word(site, B['labels'][label], True), K.b_word(site, target, True)))
    check('cave words as generated', all(pimg.w(a) == w for a, w in B['patch'].items()), True)
    check('no relocation left on a site', [hex(a) for a in B['inplace'] if a in pimg.relocs()], [])
    mine = set(B['patch'])
    for p in others:
        theirs = set()
        for t in open(p).read().split():
            if '=' in t and not t.startswith(('reloc:', 'grow:')):
                theirs.add(int(t.split('=')[0], 16))
        check('no overlap with %s' % os.path.basename(p), sorted(hex(a) for a in mine & theirs), [])

    # ---- wrappers, each original stubbed
    E = Emu(patched)
    E.setw(RES_MGR, OBJ)
    E.setw(OBJ + 0x2C, FX_HOLDER)
    E.setw(OBJ + 0x34, FS_HOLDER)
    E.setw(C.PATH_BUILDER, 0x68305000)
    calls = []

    def rec(name, n):
        return lambda E: calls.append((name,) + tuple(E.r(3 + i) for i in range(n)))
    E.stub(C.FX_ADD, rec('fx_add', 6))
    E.stub(C.FX_REG, rec('fx_reg', 2))
    E.stub(C.FX_UNREG, rec('fx_unreg', 2))
    E.stub(C.HOLDER_REMOVE, rec('remove', 2))
    E.stub(C.FS_ADD, rec('fs_add', 3))
    E.stub(C.FS_REMOVE, rec('fs_remove', 3))
    E.stub(C.BANK_RELEASE, rec('release', 1))

    def fs_reg(E):
        calls.append(('fs_reg', E.w(E.r(3) + 0x10)))
    E.stub(C.FS_REG, fs_reg)

    def fin_path(E):
        calls.append(('fin_path', E.r(3), E.r(5), E.r(6), E.r(7)))
        E.setw(E.r(4), MARK | E.r(5))
    E.stub(C.FIN_PATH, fin_path)

    def hadd(E):
        calls.append(('add', E.r(3), E.r(4), E.w(E.r(5))))
    E.stub(C.HOLDER_ADD, hadd)
    E.stub(C.STRING_FREE, rec('free', 2))

    def at_site(site, regs):
        """run from the call site to the next word; regs: {n: value}; r14-r31 seeded"""
        for i in range(14, 32):
            E.mu.reg_write(REGS[i], 0x1100 + i)
        for i in range(3, 13):
            E.mu.reg_write(REGS[i], 0)
        for n, v in regs.items():
            E.mu.reg_write(REGS[n], v & 0xFFFFFFFF)
        sp = KT.STACK + 0xF0000
        E.mu.reg_write(UC_PPC_REG_1, sp)
        E.mu.reg_write(UC_PPC_REG_LR, 0x12345678)
        del calls[:]
        E.mu.emu_start(site, site + 4, count=100000)
        ok = (E.mu.reg_read(UC_PPC_REG_PC) == site + 4 and E.mu.reg_read(UC_PPC_REG_1) == sp
              and all(E.r(i) == 0x1100 + i for i in range(14, 32)))
        return ok, list(calls)

    def xform(k):
        return {0x3B: 0x16, 0x3A: 0xF, 0x3C: 0x29, 0x3D: 0x1E}.get(k, k)

    def expect(label, k, a):
        """the calls a wrapper should make for kind k (a = the site's argument registers)"""
        b = base.get(k, 0xFF)
        if label == 'fx_add':
            out = [('fx_add',) + a]
            return out + ([('fx_add', a[0], b) + a[2:]] if b != 0xFF else [])
        if label in ('fx_reg', 'fx_unreg'):
            out = [(label,) + a]
            return out + ([(label, a[0], b)] if b != 0xFF else [])
        if label == 'fx_rem':
            return [('remove',) + a] + ([('remove', a[0], xform(b))] if b != 0xFF else [])
        if label == 'fs_add':
            out = [('fs_add',) + a]
            if b != 0xFF:
                out += [('fin_path', 0x68305000, b, 0, 0), ('add', a[0], b * 9 + 3, MARK | b),
                        ('free', KT.STACK + 0xF0000 - C.FRAME + 0x20, 2)]
            return out
        if label == 'fs_rem':
            return [('fs_remove',) + a] + ([('remove', a[0], b * 9 + 3)] if b != 0xFF else [])
        if label == 'fs_reg':
            return [('fs_reg', k)] + ([('fs_reg', b)] if b != 0xFF else [])
        if label == 'fs_rel':
            return [('release', 0x400 + k)] + ([('release', 0x400 + b)] if b != 0xFF else [])

    kinds = list(range(0x41)) + newk + [newk[-1] + 1, 0x5F, 0xFF]
    for site, _t, label, what in B['sites']:
        bad = []
        for k in kinds:
            if label == 'fx_add':
                a = (FX_HOLDER, k, 0x11, 0x22, 0x33, 0x44)
            elif label in ('fx_reg',):
                a = (FRES, k)
            elif label in ('fx_unreg', 'fx_rem'):
                a = (FX_HOLDER, k)
            elif label in ('fs_add', 'fs_rem'):
                a = (FS_HOLDER, k, 3)
            if label == 'fs_reg':
                E.setw(FE + 0x10, k)
                regs = {3: FE}
            elif label == 'fs_rel':
                regs = {3: 0x400 + k}
            else:
                regs = {3 + i: v for i, v in enumerate(a)}
            ok, got = at_site(site, regs)
            want = expect(label, k, a if label not in ('fs_reg', 'fs_rel') else None)
            if not ok or got != want:
                bad.append((hex(k), ok, got, want))
        check('0x%08X %s: game kinds unchanged, new kinds + base, registers kept' % (site, label), bad[:2], [])

    # ---- model holders + the real effect-folder add and bank register / release
    E2 = Emu(patched)
    E2.setw(RES_MGR, OBJ)
    E2.setw(OBJ + 0x2C, FX_HOLDER)
    E2.setw(OBJ + 0x34, FS_HOLDER)
    holders = {FX_HOLDER: {}, FS_HOLDER: {}}
    banks = []

    def path_builder(E):          # 0x030BB464(builder, string*, kind, type, x): marker = type, kind
        E.setw(E.r(4), (E.r(6) << 16) | E.r(5))
    E2.stub(0x030BB464, path_builder)
    E2.stub(C.FIN_PATH, lambda E: E.setw(E.r(4), (0xF << 16) | E.r(5)))

    def h_add(E):
        h = holders.setdefault(E.r(3), {})
        k = E.r(4)
        c, p = h.get(k, (0, E.w(E.r(5))))
        h[k] = (c + 1, p)
    E2.stub(C.HOLDER_ADD, h_add)

    def h_remove(E):
        h = holders.setdefault(E.r(3), {})
        k = E.r(4)
        if k in h:
            c, p = h[k]
            if c > 1:
                h[k] = (c - 1, p)
            else:
                del h[k]
    E2.stub(C.HOLDER_REMOVE, h_remove)

    def h_get(E):                 # 0x030BF0FC(holder, out, id): out = the file if present
        h = holders.get(E.r(3), {})
        E.setw(E.r(4), h[E.r(5)][1] if E.r(5) in h else 0)
    E2.stub(0x030BF0FC, h_get)
    E2.stub(0x032D9600, lambda E: 1 if E.w(E.r(3)) else 0)
    E2.stub(C.STRING_FREE, lambda E: None)
    E2.stub(0x0334CB20, lambda E: banks.append(('reg', E.r(3), E.w(E.r(4)) if E.r(4) else 0)))
    E2.stub(0x0334CB70, lambda E: banks.append(('reg', E.r(3), E.w(E.r(4)))))
    E2.stub(C.BANK_RELEASE, lambda E: banks.append(('release', E.r(3))))
    E2.stub(0x033FCC1C, lambda E: 1)        # not in a wait-for-idle context
    E2.stub(C.FS_ADD, lambda E: None)       # (its own ids: added by hand below)
    E2.stub(C.FS_REMOVE, lambda E: None)
    # the slot table, as 0x030C1370 initialises it: 8 x {kind -1, count 0} at +0x20
    for i in range(8):
        E2.setw(FX_HOLDER + 0x20 + 8 * i, 0xFFFFFFFF)
        E2.setw(FX_HOLDER + 0x24 + 8 * i, 0)
    E2.mu.mem_write(FRES + 0x3C, b'\0\0\0\0')

    def site2(site, regs):
        for n, v in regs.items():
            E2.mu.reg_write(REGS[n], v & 0xFFFFFFFF)
        E2.mu.reg_write(UC_PPC_REG_1, KT.STACK + 0xF0000)
        E2.mu.emu_start(site, site + 4, count=200000)

    def add(k):
        site2(0x030C09F8, {3: FX_HOLDER, 4: k, 5: 0, 6: 0, 7: 0, 8: 0})

    def rem(k):
        site2(0x030BFAE0, {3: FX_HOLDER, 4: xform(k)})

    def reg(k):
        site2(0x02E13170, {3: FRES, 4: k})

    def unreg(k):
        site2(0x02E147C0, {3: FX_HOLDER, 4: k})

    def slots():
        return sorted((E2.w(FX_HOLDER + 0x20 + 8 * i), E2.w(FX_HOLDER + 0x24 + 8 * i)) for i in range(8)
                      if E2.w(FX_HOLDER + 0x24 + 8 * i))

    S, M = newk[0], base[newk[0]]
    folder = lambda k: (2 << 16) | k  # noqa: E731
    add(S)
    check('Supamario alone: folders %s and %s (type 2), once each' % (hex(S), names[M]),
          holders[FX_HOLDER], {S: (1, folder(S)), M: (1, folder(M))})
    del banks[:]
    reg(S)
    check('  banks 0x%X and 0x%X registered with their files' % (0x300 + S, 0x300 + M),
          banks, [('reg', 0x300 + S, folder(S)), ('reg', 0x300 + M, folder(M))])
    check('  slots', slots(), sorted([(S, 1), (M, 1)]))
    del banks[:]
    unreg(S)
    rem(S)
    check('  teardown: both released, slots empty, holder empty',
          (banks, slots(), holders[FX_HOLDER]), ([('release', 0x300 + S), ('release', 0x300 + M)], [], {}))

    del banks[:]
    add(M)
    add(S)
    check('Mario + Supamario: Mario\'s folder refcount 2', holders[FX_HOLDER], {S: (1, folder(S)), M: (2, folder(M))})
    reg(M)
    reg(S)
    check('  0x%X registered once with its file, then an add-ref; 0x%X once' % (0x300 + M, 0x300 + S),
          banks, [('reg', 0x300 + M, folder(M)), ('reg', 0x300 + S, folder(S)), ('reg', 0x300 + M, 0)])
    check('  slots', slots(), sorted([(M, 2), (S, 1)]))
    del banks[:]
    unreg(S)
    rem(S)
    check('  Supamario leaves: Mario\'s bank and folder stay', (slots(), holders[FX_HOLDER]),
          ([(M, 1)], {M: (1, folder(M))}))
    unreg(M)
    rem(M)
    check('  Mario leaves: empty', (slots(), holders[FX_HOLDER]), ([], {}))

    add(S)
    add(S)
    reg(S)
    reg(S)
    check('two Supamarios: one folder each kind (refcount 2), slots count 2',
          (holders[FX_HOLDER], slots()), ({S: (2, folder(S)), M: (2, folder(M))}, sorted([(S, 2), (M, 2)])))
    for _ in range(2):
        unreg(S)
        rem(S)
    check('  both leave: empty', (slots(), holders[FX_HOLDER]), ([], {}))

    for k in (1, M, 0x3B):
        before = dict(holders[FX_HOLDER])
        add(k)
        added = {kk: v for kk, v in holders[FX_HOLDER].items() if kk not in before}
        rem(k)
        check('game kind 0x%X: its own folder only (id %s), removed' % (k, hex(xform(k))),
              (added, holders[FX_HOLDER]), ({xform(k): (1, folder(xform(k)))}, {}))

    # Final Smash: the real 0x02E484D8 (bank from the final holder's kind*9 + 3)
    del banks[:]
    site2(0x02E48434, {3: FS_HOLDER, 4: S, 5: 0})
    fin = holders[FS_HOLDER]
    check('Final Smash holder: the base\'s Fin effect folder at id 0x%X' % (M * 9 + 3),
          fin.get(M * 9 + 3), (1, (0xF << 16) | M))
    fin[S * 9 + 3] = (1, 0xF00000 | S)        # the stubbed 0x030C16B0 adds the own ids
    E2.setw(FE + 0x10, S)
    site2(0x02E1DDD0, {3: FE})
    check('  banks 0x%X and 0x%X registered with their Fin files' % (0x400 + S, 0x400 + M),
          banks, [('reg', 0x400 + S, 0xF00000 | S), ('reg', 0x400 + M, (0xF << 16) | M)])
    site2(0x02E48424, {3: FS_HOLDER, 4: S, 5: 0})
    check('  removed with the own ids', M * 9 + 3 in holders[FS_HOLDER], False)
    print('%d failed' % KT.fails)
    sys.exit(1 if KT.fails else 0)


def xform(k):
    return {0x3B: 0x16, 0x3A: 0xF, 0x3C: 0x29, 0x3D: 0x1E}.get(k, k)


if __name__ == '__main__':
    main()
