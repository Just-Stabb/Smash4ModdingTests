#!/usr/bin/env python3
"""Runs tools/sound_alias_cave.py natively (unicorn) on the patched executable, against the unpatched one, and the
game's own nus3 bank loader on real banks.

  python3 tools/sound_alias_cave_test.py PATCHED.rpx ORIGINAL.rpx [--banks MAIN.nus3bank OLD_C01 NEW_C01 OTHER]

- the words: the hook a `b` to the cave, the cave as built, it was zero, no other word changed;
- the SoundModule set-up's tail run natively from 0x027620A0 through both bank registrations (0x03121FA8 called at
  0x027620B4 and 0x027620CC; the voice player 0x03121E94 stubbed to record what it gets): for Hero 0x45 / Sephiroth
  0x42 the aliases +0x5C0 / +0x5C4 become ALIASES' ids and the player gets them as the slots' aliases; for a vanilla
  kind (Robin 0x2C, Mario 0x01) and a new kind without an entry (0x41) everything as unpatched; registers as the
  unpatched run leaves them;
- the bank finder 0x02C71898, natively, with the module's handles holding costume banks of their own ids (the
  costume ids of tools/sound_bank_ids.py): a sound of the main se id / vc id is found in the se / vc handle once the
  set-up ran on the patched executable (unpatched: not found), a sound of another id not;
- with --banks: nus3's own load (0x03673A94, natively, each bank in its own buffer, the lib's bank lists set up as
  its init does): MAIN then OLD_C01 (the same BINF id) -> 0x80000021 (refused: the second player's bank), MAIN then
  NEW_C01 (its own id) -> 0, OTHER twice -> 0x80000021 (a vanilla bank loaded twice: the same rule).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kind_expand as K  # noqa: E402
import sound_alias_cave as C  # noqa: E402
import sound_bank_ids as B  # noqa: E402
from kind_expand_test import Emu, REGS, check  # noqa: E402
import kind_expand_test as KT  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_LR, UC_PPC_REG_MSR  # noqa: E402

MOD = KT.STRUCTS + 0x10000      # a fighter SoundModule (0x600 bytes)
FINDER = 0x02C71898             # (module, bank id) -> the handle (module + offset) holding it
BANK_ID = 0x033EC060
COMMON = 0x03127708


def emu(path):
    E = Emu(path)
    E.mu.reg_write(UC_PPC_REG_MSR, E.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    E.regs = []
    E.ids = {}
    E.stub(0x03121E94, lambda E: E.regs.append((E.r(4) - MOD, E.r(5), E.r(6), E.r(7))))
    E.stub(BANK_ID, lambda E: E.ids.get(E.r(3), 0xFFFFFFFF))
    E.stub(COMMON, lambda E: KT.STRUCTS + 0x7F00)
    E.stub(0x033EBB6C, lambda E: 1 if E.r(3) in E.ids else 0)
    return E


def module(E, kind, entry=1):
    E.mu.mem_write(MOD, b'\0' * 0x600)
    E.setw(MOD, 0x10093C64)                 # the fighter SoundModule's vtable (vt +0x344: the alias check)
    E.setw(MOD + 8, kind)
    E.setw(MOD + 0xC, entry)
    E.setw(MOD + 0x10, MOD + 0x400)
    for o in (0x5C0, 0x5C4, 0x5C8, 0x5CC, 0x580, 0x584):
        E.setw(MOD + o, 0xFFFF)


def setup_tail(E, kind):
    """0x027620A0 -> 0x027620D0: the common... se and vc registrations of the set-up"""
    module(E, kind)
    del E.regs[:]
    for n in range(32):
        E.mu.reg_write(REGS[n], 0x1000 + n)
    E.mu.reg_write(REGS[30], MOD)
    E.mu.reg_write(UC_PPC_REG_1, KT.STACK + 0xF0000)
    E.mu.reg_write(UC_PPC_REG_LR, 0x0BADC0DE)
    E.mu.emu_start(0x027620A0, 0x027620D0, count=100000)
    keep = {n: E.mu.reg_read(REGS[n]) for n in range(13, 32)}
    return E.w(MOD + 0x5C0), E.w(MOD + 0x5C4), list(E.regs), keep


def nus3(path, banks):
    """the game's nus3 bank load (0x03673A94) of each (name, data) in turn: [(name, result)]"""
    from unicorn import UcError
    E = Emu(path)
    mu = E.mu
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    data_at, pool = 0x40000000, [0x48000000]
    mu.mem_map(data_at, 0x08000000)
    mu.mem_map(pool[0], 0x04000000)

    def alloc_raw(n):
        a = (pool[0] + 0x3F) & ~0x3F
        pool[0] = a + n
        mu.mem_write(a, b'\0' * n)
        return a
    E.stub(0x03674C00, lambda E: alloc_raw(E.r(3)))             # the lib's allocator (its heap)
    for f in (0x03697858, 0x03697888, 0x036978A0):              # mutex init / lock / unlock
        E.stub(f, lambda E: 0)

    def memcpy(E):
        if E.r(5):
            E.mu.mem_write(E.r(3), bytes(E.mu.mem_read(E.r(4), E.r(5))))
        return E.r(3)

    def memset(E):
        if E.r(5):
            E.mu.mem_write(E.r(3), bytes([E.r(4) & 0xFF]) * E.r(5))
        return E.r(3)
    E.stub(0x04B811C0, memcpy)
    E.stub(0x04B811D0, memset)
    mu.mem_write(0x10446604, b'\x01\x00')                       # initialised, not shutting down
    for i in range(17):                                         # the lib's object lists (its init, 0x03676420)
        o = alloc_raw(0x30)
        E.call(0x0367411C, o)
        E.setw(0x1057B784 + 4 * i, o)
    o = alloc_raw(0x30)
    E.call(0x0367411C, o)
    E.setw(0x1057B4C4, o)
    out, at = [], data_at
    for name, d in banks:
        mu.mem_write(at, d)
        ret = alloc_raw(0x40)
        E.setw(ret + 8, 0x876500)                               # the result object's type word (0x03673440)
        try:
            r = E.call(0x03673A94, at, len(d), ret, count=50000000)
        except UcError as e:
            r = 'crash %s' % e
        out.append((name, r))
        at = (at + len(d) + 0xFFFF) & ~0xFFFF
    return out


def main():
    argv = sys.argv[1:]
    banks = None
    if '--banks' in argv:
        i = argv.index('--banks')
        banks = argv[i + 1:i + 5]
        del argv[i:i + 5]
    patched, original = argv[0], argv[1]
    P, O = K.Image(patched), K.Image(original)
    words, hooks = C.build()
    print('# words')
    check('the hook is a b to the cave', [(hex(a), P.w(a)) for a in hooks], [(hex(C.HOOK), C.branch(C.HOOK, C.CAVE))])
    check('the cave holds the built words', [hex(C.CAVE + 4 * i) for i, w in enumerate(words)
                                             if P.w(C.CAVE + 4 * i) != w], [])
    check('the cave was zero', [hex(x) for x in range(C.CAVE, C.CAVE + 4 * len(words), 4) if O.w(x)], [])
    import diag_sound_cave as DG
    diag = {st[1] for st in DG.STEPS}               # diag_sound_cave.py's hooks, when it is applied as well
    diff = []
    for base, data in O.mem:
        pd = P.blob(base, len(data))
        for o in range(0, len(data) - 3, 4):
            a = base + o
            if data[o:o + 4] != pd[o:o + 4] and not (C.CAVE <= a < C.LIMIT) and a not in hooks \
                    and not (DG.CAVE <= a < DG.LIMIT) and a not in diag:
                diff.append(hex(a))
    check('no other word changed', diff[:5], [])

    print('# the set-up\'s registrations, natively (0x027620A0 -> 0x027620D0)')
    Ep, Eo = emu(patched), emu(original)
    for kind, name in ((0x45, 'Hero'), (0x42, 'Sephiroth'), (0x41, 'Supamario (no entry)'), (0x2C, 'Robin'),
                       (0x01, 'Mario')):
        se, vc, regs, keep = setup_tail(Ep, kind)
        se0, vc0, regs0, keep0 = setup_tail(Eo, kind)
        if kind in C.ALIASES:
            a_se, a_vc = C.ALIASES[kind]
            check('%s: +0x5C0 / +0x5C4 = %d / %d (unpatched 0xFFFF)' % (name, a_se, a_vc), (se, vc, se0, vc0),
                  (a_se, a_vc, 0xFFFF, 0xFFFF))
            check('  the voice player gets them as the se / vc slots\' aliases',
                  [(o, al) for o, al, _6, _7 in regs], [(0x18, a_se), (0x24, a_vc)])
        else:
            check('%s: as unpatched' % name, (se, vc, regs), (se0, vc0, regs0))
        check('  r13-r31 as unpatched', keep, keep0)

    print('# the bank finder 0x02C71898 with costume banks of their own ids')
    for kind in sorted(C.ALIASES):
        a_se, a_vc = C.ALIASES[kind]
        c_se, c_vc = B.costume_id(a_se, 1), B.costume_id(a_vc, 1)
        res = {}
        for tag, E in (('patched', Ep), ('unpatched', Eo)):
            setup_tail(E, kind)
            E.ids.clear()
            E.ids.update({MOD + 0x18: c_se, MOD + 0x24: c_vc})
            res[tag] = [E.call(FINDER, MOD, b) - MOD for b in (a_se, a_vc, 1234)]
        check('kind 0x%02X, costume banks %d / %d: sounds of %d / %d -> se / vc handle; another id none' % (
            kind, c_se, c_vc, a_se, a_vc), res['patched'][:2] + [res['patched'][2] in (0x18, 0x24)],
            [0x18, 0x24, False])
        check('  unpatched: neither found (the costume player was silent)', [o in (0x18, 0x24) for o in res['unpatched'][:2]],
              [False, False])

    if banks:
        print('# nus3\'s bank load (0x03673A94), natively')
        main_, old, new, other = [(os.path.basename(p), open(p, 'rb').read()) for p in banks]
        check('the costume bank built from the old one: only its id differs', (B.binf(new[1])[1],
              B.with_id(old[1], B.binf(new[1])[1]) == new[1], B.binf(old[1])[1] == B.binf(main_[1])[1]),
              (B.binf(new[1])[1], True, True))
        r = nus3(original, [main_, old])
        check('%s then %s (same id %d): the second refused' % (main_[0], old[0], B.binf(old[1])[1]),
              [x[1] for x in r], [0, 0x80000021])
        r = nus3(original, [main_, new])
        check('%s then the renumbered %s (id %d): both load' % (main_[0], new[0], B.binf(new[1])[1]),
              [x[1] for x in r], [0, 0])
        r = nus3(original, [other, other])
        check('%s twice: the second refused (the same rule for vanilla banks)' % other[0], [x[1] for x in r],
              [0, 0x80000021])
    print('FAILED %d' % KT.fails if KT.fails else 'all passed')
    sys.exit(1 if KT.fails else 0)


if __name__ == '__main__':
    main()
