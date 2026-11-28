#!/usr/bin/env python3
"""The clone extras of a patched executable (clone_extras.py), run in unicorn on the game's own code around them.

  python3 tools/sm4shclonetool/tests/extras_test.py PATCHED.rpx VANILLA.rpx

Checks:
- the results screen's announcer call 0x02A65898 (the game's function, its region remap's region getter stubbed): for
  every vanilla kind 0-0x40 and costume 0-15 the patched executable gives what the vanilla one gives; for every clone
  and costume, the base's call mapped through the clone's own labels (its call_map), never -1; the Python port of
  the switch (narration.results_calls) agrees with the code;
- the sound aliases: the SoundModule set-up's getter 0x03127990 called from 0x02761E48 for a clone writes the base's
  se / vc / cheer ids into +0x5C0 / +0x5C4 / +0x5C8 and nothing else, for a vanilla kind or from another caller
  nothing; the Final Smash registration 0x03121FA8 from 0x0276159C: +0x580 and r5 = se_common's (when the base has one);
- Kirby: copy_grant's kind (0x02EFCDA4) is the base's for a clone, unchanged for 0-0x3F; the three resource functions'
  kinds likewise, the helper keeping the real kind; the motion folder / hat names (0x030C4710 / 0x030C4830) are the
  clone's own for its kind, the base's table entries for the base; the Kirby-copy voice bank's bound (0x030C0FF8) lets
  the clones with an own Kirby-copy bank through, 0x3A-0x40 and other kinds as the game does.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sm4shclonetool import clone_extras as CE  # noqa: E402
from sm4shclonetool import exe as X  # noqa: E402
from sm4shclonetool import narration as N  # noqa: E402
from sm4shclonetool import roster as R  # noqa: E402
from sm4shclonetool.rpx import Rpx  # noqa: E402
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_WRITE  # noqa: E402
from unicorn import ppc_const as P  # noqa: E402

RET, STACK, OBJ = 0x01000000, 0x7F00F000, 0x7E000000
FAILS = []


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)), flush=True)
    if not ok:
        FAILS.append(what)


def Rg(n):
    return getattr(P, 'UC_PPC_REG_%d' % n)


class M:
    def __init__(self, path):
        x = Rpx(path)
        self.x = x
        self.mu = mu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
        spans = [[a & ~0xFFF, (a + len(b) + 0xFFF) & ~0xFFF, a, b] for a, b in x.memory().items()]
        for s in x.secs:
            if s[1] == 8 and s[3]:
                spans.append([s[3] & ~0xFFF, (s[3] + s[5] + 0xFFF) & ~0xFFF, None, None])
        spans.sort()
        merged = []
        for lo, hi, _a, _b in spans:
            if merged and lo <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        for lo, hi in merged:
            mu.mem_map(lo, hi - lo)
        for _l, _h, a, b in spans:
            if b:
                mu.mem_write(a, b)
        mu.mem_map(RET, 0x1000)
        mu.mem_map(0x7E000000, 0x2000000)
        # the region getter of the call's remap: region 0 (no remap)
        mu.hook_add(UC_HOOK_CODE, lambda uc, a, s, u: self.ret(0), begin=0x02AC246C, end=0x02AC246C)
        self.writes = []
        mu.hook_add(UC_HOOK_MEM_WRITE, lambda uc, acc, a, size, v, u: self.writes.append((a, size)))

    def r(self, n):
        return self.mu.reg_read(Rg(n))

    def ret(self, v):
        self.mu.reg_write(Rg(3), v & 0xFFFFFFFF)
        self.mu.reg_write(P.UC_PPC_REG_PC, self.mu.reg_read(P.UC_PPC_REG_LR))

    def run(self, pc, until, regs, lr=RET, count=200000):
        for n, v in regs.items():
            self.mu.reg_write(Rg(n), v & 0xFFFFFFFF)
        self.mu.reg_write(Rg(1), STACK)
        self.mu.reg_write(P.UC_PPC_REG_LR, lr)
        self.writes = []
        self.mu.emu_start(pc, until, count=count)

    def w(self, a):
        return struct.unpack('>I', bytes(self.mu.mem_read(a, 4)))[0]

    def cstr(self, a):
        b = bytes(self.mu.mem_read(a, 64))
        return b[:b.index(0)].decode('latin1')


def signed(v):
    return v - (1 << 32) if v & 0x80000000 else v


def main():
    patched, vanilla = sys.argv[1:3]
    base, rec = X.find_marker(Rpx(patched))
    reg = rec['registry']
    fs = reg['fighters']
    m, v = M(patched), M(vanilla)
    kind_of = R.KINDS.index

    # ---------------------------------------------------------------- results call
    def call(mm, kind, costume):
        mm.run(0x02A65898, RET, {3: 1, 4: kind, 5: costume, 6: 0})
        return mm.r(3)
    diff = [(k, c) for k in range(0x41) for c in range(16) if call(m, k, c) != call(v, k, c)]
    check('results call 0x02A65898: kinds 0-0x40 x costumes 0-15 as the game gives them', diff[:5], [])
    port = [(k, c) for k in range(0x41) for c in range(16) if k not in (8,)
            and (N.results_calls(v.x.r32, k, c) & 0xFFFFFFFF) != call(v, k, c)]
    check('the switch\'s Python port (narration.results_calls) = the game\'s function for kinds 0-0x40', port[:5], [])
    bad, n = [], 0
    for f in fs:
        mp = dict(f.get('call_map') or [])
        for c in range(16):
            want = call(v, kind_of(f['base']), c)
            want = mp.get(want, want)
            got = call(m, f['kind'], c)
            n += 1
            if got != want or got == 0xFFFFFFFF:
                bad.append((f['name'], c, hex(got), hex(want)))
    check('results call for the %d clones x 16 costumes: the base\'s call through the clone\'s own labels (%d calls)'
          % (len(fs), n), bad[:5], [])
    own = [f for f in fs if f.get('call_map')]
    if own:
        f = own[0]
        check('%s: its results call is its own label (0x%08X), not the base\'s' % (f['name'], f['call_map'][0][1]),
              call(m, f['kind'], 0) in [b for _a, b in f['call_map']], True)
    check('a kind past the clones (0x%X) still has no call' % (0x41 + len(fs)),
          call(m, 0x41 + len(fs), 0), 0xFFFFFFFF)

    # ---------------------------------------------------------------- aliases
    for f in fs[:6]:
        al = (list(f.get('sound_alias') or []) + [0, 0, 0, 0])[:4]
        mod = OBJ + 0x1000
        m.mu.mem_write(mod, b'\0' * 0x600)
        m.mu.mem_write(mod + 8, struct.pack('>I', f['kind']))
        tab = OBJ + 0x3000
        m.mu.mem_write(tab, struct.pack('>I', tab + 0x100) + b'\0' * 0x400)
        m.run(CE.SETUP_HOOK, CE.SETUP_HOOK + 4, {3: tab, 30: mod}, lr=CE.SETUP_RET)
        got = [m.w(mod + o) for o in (0x5C0, 0x5C4, 0x5C8)]
        want = [a if a else 0 for a in al[:3]]
        stray = [a for a, s in m.writes if not (mod + 0x5C0 <= a < mod + 0x5CC) and not (STACK - 0x400 <= a < STACK + 8)]
        check('%s: the set-up gives its banks the base\'s ids as aliases (se, vc, cheer = %s), nothing else written'
              % (f['name'], want), (got, stray), (want, []))
        m.mu.mem_write(mod, b'\0' * 0x600)
        m.mu.mem_write(mod + 8, struct.pack('>I', f['kind']))
        m.run(CE.SETUP_HOOK, CE.SETUP_HOOK + 4, {3: tab, 30: mod}, lr=0x02761000)
        check('%s: the getter called from elsewhere: no alias written' % f['name'],
              [m.w(mod + o) for o in (0x5C0, 0x5C4, 0x5C8)], [0, 0, 0])
        m.mu.mem_write(mod + 8, struct.pack('>I', f['kind']))
        m.run(CE.FS_HOOK, CE.FS_HOOK + 4, {3: tab, 30: mod, 5: 0x1234}, lr=CE.FS_RET)
        check('%s: the Final Smash bank\'s alias (+0x580, r5) = %s' % (f['name'], al[3] or 'none (kept)'),
              (m.w(mod + 0x580), m.r(5)), (al[3], al[3]) if al[3] else (0, 0x1234))
    mod = OBJ + 0x1000
    m.mu.mem_write(mod, b'\0' * 0x600)
    m.mu.mem_write(mod + 8, struct.pack('>I', 0x19))
    m.run(CE.SETUP_HOOK, CE.SETUP_HOOK + 4, {3: OBJ + 0x3000, 30: mod}, lr=CE.SETUP_RET)
    check('a vanilla kind (0x19): no alias written', [m.w(mod + o) for o in (0x5C0, 0x5C4, 0x5C8)], [0, 0, 0])

    # ---------------------------------------------------------------- Kirby
    # a Kirby: fighter +0x726C -> WorkModule, [WM+8] -> groups, [group 0 + 0xC] -> his int array (int 0xA4 at +0x290)
    FTR, WM, GRP, INTS = OBJ + 0x8000, OBJ + 0x9000, OBJ + 0x9100, OBJ + 0xA000
    m.mu.mem_write(FTR + 0x726C, struct.pack('>I', WM))
    m.mu.mem_write(WM + 8, struct.pack('>I', GRP))
    m.mu.mem_write(GRP, struct.pack('>I', GRP + 0x40))
    m.mu.mem_write(GRP + 0x40 + 0xC, struct.pack('>I', INTS))

    def grant(k, ftr=FTR):
        m.run(CE.GRANT, CE.GRANT + 4, {6: k, 28: 0xDEAD, 4: ftr})
        return m.r(28)
    want = {f['kind']: kind_of(f['base']) for f in fs if f.get('kirby', True)}
    got = {k: grant(k) for k in range(0x100)}
    check('copy_grant: a clone is granted as its base\'s kind (%d clones), kinds without a clone unchanged'
          % len(want), [k for k in range(0x100) if got[k] != want.get(k, k)], [])
    for hook, rg, keep in CE.RES:
        res = {}
        for k in list(range(0x40)) + list(want):
            m.run(hook, hook + 4, {4: k, rg: 0xDEAD})
            res[k] = (m.r(rg), m.w(base + 0) if False else None)
        check('copy resources 0x%08X: r%d = the base\'s kind for a clone, the kind itself otherwise' % (hook, rg),
              [k for k in res if res[k][0] != want.get(k, k)], [])
    lab = None
    for f in fs:
        if not f.get('kirby', True):
            continue
        bk = kind_of(f['base'])
        m.run(CE.RES[0][0], CE.RES[0][0] + 4, {4: f['kind']})
        btab = m.w(0x1041A6D0 + 4 * bk)
        m.run(CE.BODY, CE.BODY + 4, {7: btab})
        body = m.cstr(m.r(7))
        m.run(CE.HAT, CE.HAT + 4, {23: 0x1041A7B8, 21: 4 * bk})
        hat = m.cstr(m.r(7)) if m.r(7) else None
        check('%s: Kirby\'s copy loads motion/%sbody and model/%s' % (f['name'], body, hat),
              (body, hat), (f.get('kirby_body') or m.cstr(btab),
                            f.get('kirby_hat') or (m.cstr(m.w(0x1041A7B8 + 4 * bk)) if m.w(0x1041A7B8 + 4 * bk) else None)))
        m.run(CE.RES[0][0], CE.RES[0][0] + 4, {4: bk})
        m.run(CE.BODY, CE.BODY + 4, {7: btab})
        b2 = m.cstr(m.r(7))
        m.run(CE.HAT, CE.HAT + 4, {23: 0x1041A7B8, 21: 4 * bk})
        h2 = m.cstr(m.r(7)) if m.r(7) else None
        check('%s\'s base (kind 0x%X): its own table entries (%s, %s)' % (f['name'], bk, b2, h2),
              (b2, h2), (m.cstr(btab), m.cstr(m.w(0x1041A7B8 + 4 * bk)) if m.w(0x1041A7B8 + 4 * bk) else None))
        lab = f
    vk = {f['kind'] for f in fs if f.get('kirby', True) and f.get('kirby_voice')}
    bad = []
    for k in range(0x100):
        m.run(CE.VOICE, CE.VOICE + 4, {29: k})
        cr = m.mu.reg_read(P.UC_PPC_REG_CR) if hasattr(P, 'UC_PPC_REG_CR') else None
        gt = (cr >> 30) & 1 if cr is not None else None
        want_gt = 0 if (k <= 0x39 or k in vk) else 1
        if gt is not None and gt != want_gt:
            bad.append(hex(k))
    check('the Kirby-copy voice bank bound: kinds 0-0x39 and the %d clones with their own copy voices pass, the rest '
          'not' % len(vk), bad[:6], [])
    kirby_scripts(m, v, fs, kind_of, grant, FTR, WM, INTS)
    print('\n%d failed' % len(FAILS))
    return 1 if FAILS else 0


def kirby_scripts(m, v, fs, kind_of, grant, FTR, WM, INTS):
    """(1.4) Kirby's own copy scripts (KMAP, GRANT's KTAB) and the clone's own Kirby-copy bank id (COPYID)"""
    labels = m_labels(m, v)
    ks = [f for f in fs if f.get('kirby', True) and f.get('kirby_slots')]
    print('     Kirby\'s own copy scripts: %d clone(s) with copy runs in the marker' % len(ks))
    if ks:
        ktab = labels['ktab']
        f = ks[0]
        bk = kind_of(f['base'])
        grant(f['kind'])
        check('%s: copy_grant keeps {Kirby\'s int array, the clone\'s kind} (KTAB)' % f['name'],
              (m.w(ktab), m.w(ktab + 4)), (INTS, f['kind']))
        # the per-kind script lookup: a manager with Kirby's entry (kind 8 -> his motion.mtable)
        MGR, MT, MOD, ACC = OBJ + 0xC000, OBJ + 0x10000, OBJ + 0xB000, OBJ + 0xB800
        n = max(nb + hi - lo for lo, hi, nb in f['kirby_slots']) + 1
        m.mu.mem_write(MGR, b'\0' * 0x400)
        m.mu.mem_write(MGR, struct.pack('>IIII', 8, 0, 1, MT))
        m.mu.mem_write(MT, b''.join(struct.pack('>I', 0x5000000 + i) for i in range(n)))
        m.mu.mem_write(MOD + 4, struct.pack('>I', ACC))
        m.mu.mem_write(ACC + 0x28, struct.pack('>I', WM))
        runs = f['kirby_slots']
        probe = sorted({x for lo, hi, _nb in runs for x in (lo, hi, (lo + hi) // 2, lo - 1, hi + 1)} | {0, 0x211, 0x300})

        def look(motion, kind=8, site=CE.KMAP_CALLERS[0][0], reg=27, copy=bk):
            m.mu.mem_write(INTS + 0x290, struct.pack('>I', copy))
            m.run(CE.KMAP, site + 4, {3: MGR, 4: kind, 5: motion, reg: MOD, 27 if reg != 27 else 29: 0}, lr=site + 4)
            return m.r(3)

        def want(motion):
            for lo, hi, nb in runs:
                if lo <= motion <= hi:
                    return 0x5000000 + nb + motion - lo
            return 0x5000000 + motion
        for site, reg in CE.KMAP_CALLERS:
            bad = [(hex(x), hex(look(x, site=site, reg=reg)), hex(want(x))) for x in probe
                   if look(x, site=site, reg=reg) != want(x)]
            check('%s: the script lookup from 0x%08X (module r%d) for Kirby holding its copy: the copy runs %s -> '
                  'its own entries, every other motion the game\'s' % (
                      f['name'], site, reg, ', '.join('0x%X-0x%X->0x%X' % tuple(r) for r in runs)), bad, [])
        check('%s: Kirby holding another copy (kind 0x%X): the game\'s scripts' % (f['name'], (bk + 1) % 0x3A),
              [x for x in probe if look(x, copy=(bk + 1) % 0x3A) != 0x5000000 + x], [])
        m.mu.mem_write(MGR, struct.pack('>I', 0x19))
        check('another fighter (kind 0x19) with the same motions: the game\'s scripts',
              [x for x in probe if look(x, kind=0x19) != 0x5000000 + x], [])
        m.mu.mem_write(MGR, struct.pack('>I', 8))
        m.mu.mem_write(INTS + 0x290, struct.pack('>I', bk))
        m.run(CE.KMAP, 0x02760004, {3: MGR, 4: 8, 5: runs[0][0], 27: MOD}, lr=0x02760004)
        check('the lookup called from elsewhere: the game\'s', m.r(3), 0x5000000 + runs[0][0])
        # the vanilla function, the same answers for every probe (the hook replays its first words)
        bad = []
        for x in probe:
            v.mu.mem_write(MGR, b'\0' * 0x400)
            v.mu.mem_write(MGR, struct.pack('>IIII', 8, 0, 1, MT))
            v.mu.mem_write(MT, b''.join(struct.pack('>I', 0x5000000 + i) for i in range(n)))
            v.run(CE.KMAP, 0x01000000, {3: MGR, 4: 8, 5: x})
            if v.r(3) != 0x5000000 + x:
                bad.append(hex(x))
        check('the game\'s lookup (vanilla) returns mtable[motion] for the probes', bad, [])
        grant(bk)
        check('%s: Kirby then granted the base\'s copy itself: KTAB updated, the game\'s scripts' % f['name'],
              (m.w(ktab + 4), [x for x in probe if look(x) != 0x5000000 + x]), (bk, []))
        # 20 Kirbys: KTAB stays in its 16 entries (round robin), nothing written outside it, knext, the stack
        writes = []
        for i in range(20):
            ftr = OBJ + 0x20000 + 0x10000 * i
            m.mu.mem_write(ftr + 0x726C, struct.pack('>I', WM))
            m.run(CE.GRANT, CE.GRANT + 4, {6: f['kind'], 28: 0, 4: ftr})
            writes += m.writes
        stray = [hex(a) for a, _s in writes if not (labels['knext'] <= a < ktab + 8 * CE.KTAB_N)
                 and not (STACK - 0x400 <= a < STACK + 8)]
        check('20 grants: KTAB written only in its own 16 entries / knext', stray, [])
        grant(8)
        grant(0x3A)
    kb = [f for f in fs if f.get('kirby_copy_bank')]
    print('     own Kirby-copy banks: %d clone(s) with an id of their own' % len(kb))
    for f in kb[:3]:
        own, base = f['kirby_copy_bank']

        def bid(handle_id, wanted, lr):
            def body(uc, a, sz, u):        # the getter's real body: the handle's BINF id, then its epilogue
                uc.reg_write(Rg(3), handle_id)
                uc.reg_write(Rg(1), uc.reg_read(Rg(1)) + 0x10)
                uc.reg_write(P.UC_PPC_REG_PC, uc.reg_read(Rg(0)))
            h = m.mu.hook_add(UC_HOOK_CODE, body, begin=CE.COPYID + 8, end=CE.COPYID + 8)
            m.run(CE.COPYID, lr, {28: wanted, 3: 0x7777}, lr=lr)
            m.mu.hook_del(h)
            return m.r(3)
        hit = CE.COPYID_CALLER + 4
        check('%s: Kirby\'s copy-handle finder (0x%08X): its own bank (%d) answers for the base\'s id %d, for its '
              'own, and another bank does not; called from elsewhere the id is the bank\'s' % (
                  f['name'], CE.COPYID_CALLER, own, base),
              (bid(own, base, hit), bid(own, own, hit), bid(own + 1, base, hit), bid(own, base, 0x02761004)),
              (base, own, own + 1, own))


def m_labels(m, v):
    """the extras part's labels (rebuilt from the marker's registry on the vanilla words: the same code)"""
    base, rec = X.find_marker(m.x)
    reg = rec['registry']
    lay = X.layout(base, reg)
    words, info = CE.build(v.w, reg['fighters'], R.KINDS.index, *lay['extras'])
    bad = [hex(a) for a, w in words.items() if info['labels']['alias'] <= a < lay['extras'][1] and m.w(a) != w]
    check('the extras part in the executable = the part rebuilt from its registry (past its RAM words)', bad[:4], [])
    return info['labels']


if __name__ == '__main__':
    sys.exit(main())
