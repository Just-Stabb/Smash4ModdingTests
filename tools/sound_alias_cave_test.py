#!/usr/bin/env python3
"""Runs tools/sound_alias_cave.py (v2) natively (unicorn) on the patched executable, against the one it was built on,
and the game's own nus3 bank loader on real banks.

  python3 tools/sound_alias_cave_test.py PATCHED.rpx ORIGINAL.rpx [--pairs BASE.nus3bank PORT_OLD PORT_NEW ...]

- the words: both hooks `b`s to their entries, the cave as built, no other word changed (ORIGINAL may carry v1);
- the SoundModule set-up natively, for every new kind of reference/port_sound_ids.json and two vanilla kinds:
  0x02761E40 -> 0x02761E4C (the call the SETUP hook acts on, right after the MTB lookups): +0x5C0 / +0x5C4 / +0x5C8 =
  the kind's old se / vc / cheer ids (0xFFFF before, as the MTB leaves a new kind; vanilla kinds and the unpatched
  executable unchanged); then 0x027620A0 -> 0x027620D0: the voice player gets them as its se / vc slots' aliases;
  the Final Smash bank 0x02761580 -> 0x0276159C: +0x580 and the slot's alias = the old se_common id;
- the bank finder 0x02C71898 with every handle holding a bank of the kind's OWN id (sound_bank_ids.own_id): a sound
  of the old se / vc / se_common id is found in the se / vc / Final Smash handle (unpatched: none), another id not;
- with --pairs (triples): nus3's own load (0x03673A94, natively; each bank in its own buffer), in one session as in a
  match: BASE then PORT_OLD (the port as it was: the base's id) -> the second refused (0x80000021); BASE then
  PORT_NEW -> both load; and every BASE and PORT_NEW of the run loaded together -> all load.
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
MGR = KT.STRUCTS + 0x18000      # the sound manager object the set-up's getters read
FINDER = 0x02C71898             # (module, bank id) -> the handle (module + offset) holding it
BANK_ID = 0x033EC060
COMMON = 0x03127708
SND_MGR = 0x102F7288            # [..] -> [..] the sound manager


def emu(path):
    E = Emu(path)
    E.mu.reg_write(UC_PPC_REG_MSR, E.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    E.regs = []
    E.ids = {}
    E.stub(0x03121E94, lambda E: E.regs.append((E.r(4) - MOD, E.r(5), E.r(6), E.r(7))))
    E.stub(BANK_ID, lambda E: E.ids.get(E.r(3), 0xFFFFFFFF))
    E.stub(COMMON, lambda E: KT.STRUCTS + 0x7F00)
    E.stub(0x033EBB6C, lambda E: 1 if E.r(3) in E.ids else 0)
    E.setw(SND_MGR, MGR)
    E.setw(MGR, MGR + 0x100)
    return E


def module(E, kind, entry=1):
    E.mu.mem_write(MOD, b'\0' * 0x600)
    E.setw(MOD, 0x10093C64)                 # the fighter SoundModule's vtable (vt +0x344: the alias check)
    E.setw(MOD + 8, kind)
    E.setw(MOD + 0xC, entry)
    E.setw(MOD + 0x10, MOD + 0x400)
    for o in (0x5C0, 0x5C4, 0x5C8, 0x5CC, 0x580, 0x584):
        E.setw(MOD + o, 0xFFFF)


def run(E, start, until, regs=None):
    for n in range(32):
        E.mu.reg_write(REGS[n], 0x1000 + n)
    E.mu.reg_write(REGS[30], MOD)
    E.mu.reg_write(REGS[28], 0x102F0000)    # the set-up's lis r28, 0x102F (0x02761E40: lwz r3, 0x7288(r28))
    for n, v in (regs or {}).items():
        E.mu.reg_write(REGS[n], v)
    E.mu.reg_write(UC_PPC_REG_1, KT.STACK + 0xF0000)
    E.mu.reg_write(UC_PPC_REG_LR, 0x0BADC0DE)
    E.mu.emu_start(start, until, count=100000)
    return {n: E.mu.reg_read(REGS[n]) for n in range(13, 32)}


def setup(E, kind):
    """the SETUP hook's call, then the registrations; (aliases, registrations, r13-r31)"""
    module(E, kind)
    del E.regs[:]
    keep = run(E, 0x02761E40, 0x02761E4C)
    al = tuple(E.w(MOD + o) for o in (C.SE_ALIAS, C.VC_ALIAS, C.OUEN_ALIAS))
    run(E, 0x027620A0, 0x027620D0)
    return al, [(o, a) for o, a, _6, _7 in E.regs], keep


def final_smash(E, kind):
    module(E, kind)
    del E.regs[:]
    keep = run(E, 0x02761580, 0x0276159C, {3: 0xFFFF})
    return E.w(MOD + C.COMMON_ALIAS), [(o, a) for o, a, _6, _7 in E.regs], keep


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
    pairs = []
    if '--pairs' in argv:
        i = argv.index('--pairs')
        pairs = argv[i + 1:]
        del argv[i:]
    patched, original = argv[0], argv[1]
    P, O = K.Image(patched), K.Image(original)
    words, hooks, labels = C.build()
    aliases = C.load_aliases()
    print('# words')
    check('the hooks are b to their entries', sorted((hex(a), P.w(a)) for a in hooks),
          sorted([(hex(C.FS_HOOK), C.branch(C.FS_HOOK, labels['fs'])),
                  (hex(C.SETUP_HOOK), C.branch(C.SETUP_HOOK, labels['setup']))]))
    check('the cave holds the built words', [hex(C.CAVE + 4 * i) for i, w in enumerate(words)
                                             if P.w(C.CAVE + 4 * i) != w], [])
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

    print('# the set-up natively: aliases, the voice player\'s slots, the Final Smash bank')
    Ep, Eo = emu(patched), emu(original)
    kinds = sorted(aliases) + [0x2C, 0x01]
    for kind in kinds:
        al, regs, keep = setup(Ep, kind)
        al0, regs0, keep0 = setup(Eo, kind)
        fs, fregs, fkeep = final_smash(Ep, kind)
        fs0, fregs0, fkeep0 = final_smash(Eo, kind)
        if kind in aliases:
            se, vc, ou, com = aliases[kind]
            want = tuple(x or 0xFFFF for x in (se, vc, ou))
            check('kind 0x%02X: +0x5C0 / +0x5C4 / +0x5C8 = %s (the executable it was built on: %s)' % (
                kind, want, al0), al, want)
            check('  the voice player\'s se / vc slots get them', regs, [(0x18, want[0]), (0x24, want[1])])
            check('  Final Smash: +0x580 and the slot alias = %d' % (com or 0xFFFF), (fs, fregs),
                  (com or 0xFFFF, [(0x84, com or 0xFFFF)]))
        else:
            check('kind 0x%02X (vanilla): as the executable it was built on' % kind, (al, regs, fs, fregs),
                  (al0, regs0, fs0, fregs0))
        check('  r13-r31 as unpatched', (keep, fkeep), (keep0, fkeep0))

    print('# the bank finder 0x02C71898: banks of the kind\'s own ids, sounds of the old ids')
    v1 = O.w(C.FS_HOOK) == C.branch(C.FS_HOOK, C.CAVE)
    for kind in sorted(aliases):
        se, vc, ou, com = aliases[kind]
        res = {}
        for tag, E in (('patched', Ep), ('unpatched', Eo)):
            setup(E, kind)
            final_smash_mem = E.w(MOD + C.COMMON_ALIAS)
            if tag == 'patched':
                run(E, 0x02761580, 0x0276159C, {3: 0xFFFF})
            E.ids.clear()
            E.ids.update({MOD + 0x18: B.own_id(kind, 'se'), MOD + 0x24: B.own_id(kind, 'vc'),
                          MOD + 0x84: B.own_id(kind, 'se_common')})
            res[tag] = [E.call(FINDER, MOD, b) - MOD if b else None for b in (se, vc, com, 1234)]
            del final_smash_mem
        want = [0x18 if se else None, 0x24 if vc else None, 0x84 if com else None]
        got = res['patched'][:3]
        check('kind 0x%02X: old se %d / vc %d / se_common %s -> +0x18 / +0x24 / +0x84; another id none' % (
            kind, se, vc, com or '-'), got + [res['patched'][3] in (0x18, 0x24, 0x84)], want + [False])
        if v1 and kind in (0x42, 0x45):             # v1 (new kinds' sound fix v1) aliased these two's se / vc
            continue
        check('  unpatched: none found', [o in (0x18, 0x24, 0x84) for o in res['unpatched'][:3] if o is not None],
              [False] * len([b for b in (se, vc, com) if b]))

    if pairs:
        print('# nus3\'s bank load (0x03673A94), natively')
        trip = [pairs[i:i + 3] for i in range(0, len(pairs), 3)]
        allb = []
        for base, old, new in trip:
            b, o, n = [(os.path.basename(p), open(p, 'rb').read()) for p in (base, old, new)]
            check('%s: the renumbered bank differs from the old one only in its id (%d -> %d)' % (
                n[0], B.binf(o[1])[1], B.binf(n[1])[1]), B.with_id(o[1], B.binf(n[1])[1]) == n[1], True)
            r = nus3(original, [b, o])
            check('%s (id %d) then the old %s (id %d): the later refused' % (
                b[0], B.binf(b[1])[1], o[0], B.binf(o[1])[1]), [x[1] for x in r],
                [0, 0x80000021] if B.binf(b[1])[1] == B.binf(o[1])[1] else [0, 0])
            r = nus3(original, [b, n])
            check('%s then the new %s (id %d): both load' % (b[0], n[0], B.binf(n[1])[1]), [x[1] for x in r], [0, 0])
            allb += [b, n]
        seen, uniq = set(), []
        for x in allb:
            if x[0] not in seen:
                seen.add(x[0])
                uniq.append(x)
        r = nus3(original, uniq)
        check('all %d bases and ports in one session: every bank loads' % len(uniq),
              [x for x in r if x[1] != 0], [])
    print('FAILED %d' % KT.fails if KT.fails else 'all passed')
    sys.exit(1 if KT.fails else 0)


if __name__ == '__main__':
    main()
