#!/usr/bin/env python3
"""Tests tools/kirby_copy_pool_cave.py's patch (crash fixes v4 / v5) in unicorn, with the patched RPX's own code.

  python3 tools/kirby_copy_pool_test.py PATCHED.rpx ORIGINAL.rpx       (exe_v45f, exe_v45d)

- the original at the hooks: the pool builder's `lwz r19, 4(r11)` after its `rlwinm.` (cr0 live across the hook),
  r11 / r12 rewritten before read; the granted-kind load / unload cases as kind_expand.py builds them; the cave free;
- the patch: every word in place, the hooks branch to the stubs, no word the build changed is rewritten by a
  relocation, the cave in the code region;
- the pool stub, every weapon kind 0 to the last (with and without the record's flag bits), owner loaded or not:
  r19 = the count, 0 when the owner's vl reference count is 0; cr0-cr6 and every register but r11 / r12 kept;
- the vl load / unload chain of each granted kind (Sephiroth): its load case loads the granted kind (Robin) and then
  its base; its unload releases the base and then the granted kind, the stack and saved registers as they were;
- the matches (fighters loaded = the opponent's load chain, run as above, and Kirby's): Kirby vs Mario / Supamario /
  Robin / Hero / Sephiroth, each with Mario's and Robin's copy lists: every record the stub pools has its param getters
  (descriptor +0x18 / +0x24, found with the real descriptor getter 0x0320D934) run with loaded fighters' vl slots
  valid and the others garbage (0x9F16CDAC, unmapped, as in the user's v5 log): no fault, and the records the copies
  use are pooled (the copied fighter's own, and Hero's fireball / Sephiroth's fire for their copies).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kind_expand as K  # noqa: E402
import kirby_copy_pool_cave as C  # noqa: E402
from kirby_copy_new_test import Img, reloc_clashes, bl_target  # noqa: E402
from unicorn import Uc, UcError, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_0, UC_PPC_REG_LR, UC_PPC_REG_CR  # noqa: E402

FAIL = []
MGR = 0x7E000000                # fake FighterParamManager (0x4000)
VL = 0x7E100000                 # a valid fake vl struct: every word points at ZERO
ZERO = 0x7E200000
GARBAGE = 0x9F16CDAC            # the user's log: an unloaded fighter's slot
RET = 0x7F00FFF0
STACK = 0x7F008000
COPY_TABLE = 0x1038281C         # per copied kind: {records, count}
MARIO, KIRBY, ZELDA, ROBIN = 3, 8, 0x10, 0x2C


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        FAIL.append(what)


def reg(mu, r):
    return mu.reg_read(UC_PPC_REG_0 + r)


def setr(mu, r, v):
    mu.reg_write(UC_PPC_REG_0 + r, v & 0xFFFFFFFF)


def emu(img):
    mu = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
    spans = [(b, b + len(d)) for b, d in img.segs] + [(s[3], s[3] + s[5]) for s in img.secs if s[1] == 8 and s[3]]
    pages = []                                  # the sections' pages (.bss as zeros), merged
    for lo, hi in sorted((lo & ~0xFFF, (hi + 0xFFF) & ~0xFFF) for lo, hi in spans):
        if pages and lo <= pages[-1][1]:
            pages[-1][1] = max(pages[-1][1], hi)
        else:
            pages.append([lo, hi])
    for lo, hi in pages:
        mu.mem_map(lo, hi - lo)
    for base, data in img.segs:
        mu.mem_write(base, data)
    mu.mem_map(MGR, 0x4000)
    mu.mem_map(VL, 0x1000)
    mu.mem_map(ZERO, 0x10000)
    mu.mem_map(0x7F000000, 0x10000)
    mu.mem_write(VL, struct.pack('>I', ZERO) * 0x400)
    mu.mem_write(C.PARAM_MGR, struct.pack('>I', MGR))
    return mu


def call(mu, at, regs, until=RET, count=400):
    for r, v in regs.items():
        setr(mu, r, v)
    setr(mu, 1, STACK)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.emu_start(at, until, count=count)


def set_loaded(mu, loaded, vl_new, refcnt):
    mu.mem_write(MGR, b'\0' * 0x4000)
    for k in range(0x60):
        on = k in loaded
        mu.mem_write(MGR + refcnt + 4 * k, struct.pack('>I', 1 if on else 0))
        mu.mem_write(MGR + vl_new + 4 * k, struct.pack('>I', VL if on else GARBAGE))
        if k < C.OLD_FIGHTERS:
            mu.mem_write(MGR + C.VL_OLD + 4 * k, struct.pack('>I', VL if on else GARBAGE))


def main():
    new, old = Img(sys.argv[1]), Img(sys.argv[2])
    oimg = K.Image(sys.argv[2])
    vl_new, refcnt = C.layout()
    check('FighterParamManager layout: vl 0x25B0, refcnt 0x2730', (vl_new, refcnt), (0x25B0, 0x2730))
    check('original 0x%08X lwz r19, 4(r11)' % C.HOOK, old.w(C.HOOK), C.HOOK_WORD)
    check('original 0x02EFDC70 rlwinm. r10, r17, 0, 0, 0 / 0x02EFDC78 bne (cr0 live across the hook)',
          (old.w(0x02EFDC70), old.w(0x02EFDC78) >> 16), (0x562A0001, 0x4082))
    check('original r12 / r11 rewritten before read (0x02EFDCA4 lwz r12, 0x24(r3); 0x02EFDCCC lwz r11, 0xC(r1))',
          (old.w(0x02EFDCA4), old.w(0x02EFDCCC)), (0x81830024, 0x8161000C))
    check('the vl load / unload count references at mgr + 0x2730 (0x02EA6BDC / 0x02EA5D80 addi r28, rX, 0x2730)',
          (old.w(0x02EA6BDC) & 0xFFFF, old.w(0x02EA5D80) & 0xFFFF), (refcnt, refcnt))
    for a in range(C.CAVE, C.LIMIT, 4):
        if old.w(a):
            check('cave 0x%08X free in the original' % a, old.w(a), 0)
    a, out, own, grants = C.build(oimg)
    lab = a.labels
    check('granted kinds whose params need loading: Sephiroth (base Zelda) -> Robin', [(k, b, g) for k, b, g, _l, _u in grants],
          [(0x42, ZELDA, ROBIN)])
    check('Robin\'s copy weapons owned by Robin (thunder by its getter, book by name)',
          {k: own[k] for k in (0xB4, 0xB6)}, {0xB4: (ROBIN, 'name'), 0xB6: (ROBIN, 'getter')})
    check('every patched word in place', [hex(k) for k, v in sorted(out.items()) if new.w(k) != v], [])
    check('0x%08X bl pool_max' % C.HOOK, bl_target(C.HOOK, new.w(C.HOOK)), lab['pool_max'])
    for k, _b, _g, ld, ub in grants:
        check('0x%08X (kind 0x%X load case) bl load_%x' % (ld, k, k), bl_target(ld, new.w(ld)), lab['load_%x' % k])
        check('0x%08X (its unload\'s last word) b unload_%x' % (ub, k), (new.w(ub) & 3, bl_target(ub, new.w(ub) | 1)),
              (0, lab['unload_%x' % k]))
    check('no word the build changed is rewritten by a relocation', reloc_clashes(new, old), [])
    check('cave inside the proven code region', C.CAVE >= 0x04B00000 and a.pc <= C.LIMIT <= 0x04BD4000, True)

    mu = emu(new)
    # ---- the pool stub alone
    last = max(own)
    keep = [r for r in range(32) if r not in (1, 11, 12, 19)]
    bad = []
    for kind in range(last + 2):
        o = own.get(kind, (None, ''))[0]
        for flags in (0, 0x40000000):
            for present in (False, True):
                set_loaded(mu, set(range(0x60)) - ({o} if not present else set()), vl_new, refcnt)
                rec = 0x7F000100
                regs = {r: 0x1000 + r for r in range(32)}
                regs.update({11: rec, 17: kind | flags, 19: 0xDEAD})
                mu.mem_write(rec, struct.pack('>II', kind | flags, 5))
                cr = 0x20000004 | 0x80
                mu.reg_write(UC_PPC_REG_CR, cr)
                call(mu, lab['pool_max'], regs)
                want = 0 if (o is not None and not present) else 5
                if reg(mu, 19) != want or [reg(mu, r) for r in keep] != [regs[r] for r in keep] or \
                        (mu.reg_read(UC_PPC_REG_CR) ^ cr) & 0xFFFFFFF0:
                    bad.append((hex(kind | flags), present, reg(mu, 19), want))
    check('pool stub: count kept, 0 when the weapon\'s owner has no vl loaded; cr0-cr6 and registers kept',
          bad[:8], [])

    # ---- the vl load / unload chains (VL_LOAD / VL_UNLOAD replaced by a blr that records the kind)
    calls = []
    saved = {a2: bytes(mu.mem_read(a2, 4)) for a2 in (C.VL_LOAD, C.VL_UNLOAD)}
    for a2 in saved:
        mu.mem_write(a2, struct.pack('>I', 0x4E800020))
    h = mu.hook_add(UC_HOOK_CODE, lambda m, addr, size, u: calls.append((addr, reg(m, 4), reg(m, 3))),
                    begin=C.VL_LOAD, end=C.VL_LOAD)
    h2 = mu.hook_add(UC_HOOK_CODE, lambda m, addr, size, u: calls.append((addr, reg(m, 4), reg(m, 3))),
                     begin=C.VL_UNLOAD, end=C.VL_UNLOAD)
    chain = {}
    for k, b, g, ld, ub in grants:
        calls.clear()
        call(mu, ld, {29: MGR, 30: 0x3030, 31: k}, until=ld + 12)
        got = [(x[0], x[1], x[2]) for x in calls]
        check('kind 0x%X load case: loads 0x%X then its base 0x%X (r3 = the manager), stack kept' % (k, g, b),
              (got, reg(mu, 1), reg(mu, 29)), ([(C.VL_LOAD, g, MGR), (C.VL_LOAD, b, MGR)], STACK, MGR))
        chain[k] = [x[1] for x in calls]
        calls.clear()
        call(mu, ub - 12, {30: MGR, 29: 0x2929, 31: k}, until=C.VL_UNLOAD_TAIL)
        check('kind 0x%X unload case: releases its base 0x%X then 0x%X, into the common tail' % (k, b, g),
              ([(x[0], x[1], x[2]) for x in calls], reg(mu, 1), reg(mu, 30)),
              ([(C.VL_UNLOAD, b, MGR), (C.VL_UNLOAD, g, MGR)], STACK, MGR))
    mu.hook_del(h)
    mu.hook_del(h2)
    for a2, w in saved.items():
        mu.mem_write(a2, w)

    # ---- the matches
    _f, kinds = K.load_spec(K.SPEC)
    fnames = [oimg.cstr(oimg.w(C.FIGHTER_NAME + 4 * i)) for i in range(C.OLD_FIGHTERS)]
    base = {r['kind']: fnames.index(r['base']) for r in kinds}

    def loads(k):
        return {k} | set(chain.get(k, [])) | ({base[k]} if k in base else set())
    lists = {name: (new.w(new.w(COPY_TABLE + 4 * ck)), new.w(new.w(COPY_TABLE + 4 * ck) + 4)) for name, ck in
             (('Mario', MARIO), ('Robin', ROBIN))}
    scen = [('Mario', MARIO, 'Mario', [0]), ('Supamario', 0x41, 'Mario', [0, 5]), ('Robin', ROBIN, 'Robin', [0, 2]),
            ('Hero', 0x45, 'Robin', [6]), ('Sephiroth', 0x42, 'Robin', [7])]
    pools = {}
    for opp, ok_, lst, need in scen:
        loaded = loads(KIRBY) | loads(ok_)
        recs, n = lists[lst]
        faults, pooled = [], []
        for i in range(n):
            kind_w, mx = new.w(recs + 16 * i), new.w(recs + 16 * i + 4)
            if kind_w & 0x80000000 or not mx:
                continue
            set_loaded(mu, loaded, vl_new, refcnt)
            mu.mem_write(0x7F000100, struct.pack('>II', kind_w, mx))
            call(mu, lab['pool_max'], {11: 0x7F000100, 17: kind_w, 19: 0})
            if not reg(mu, 19):
                continue
            pooled.append(i)
            kind = kind_w & 0x3FFFFFFF
            try:
                call(mu, 0x0320D934, {3: 0, 4: kind}, count=2000)
                d = reg(mu, 3)
                for off in (0x18, 0x24):
                    g = new.w(d + off)
                    if 0x02000000 <= g < 0x10000000:
                        call(mu, g, {3: 0x7F000200, 4: 0}, count=2000)
            except UcError as e:
                faults.append((hex(kind), str(e)))
        check('Kirby vs %s (loaded %s), %s copy list: every pooled record\'s getters run without a fault' % (
            opp, sorted(hex(x) for x in loaded), lst), faults, [])
        check('Kirby vs %s: the records its copy uses are pooled (%s)' % (opp, need),
              [i for i in need if i not in pooled], [])
        pools[opp] = pooled
    # the weapons left out: Supamario's Kamehameha (5) without Supamario, Robin's own without Robin, Hero's / Sephiroth's
    # without them
    check('pooled records per match (Mario list: 0 fireball, 5 Kamehameha; Robin list: 0-5 Robin\'s, 6 Hero\'s fireball, '
          '7 Sephiroth\'s fire, 8-12 Hero\'s spells)', pools,
          {'Mario': [0], 'Supamario': [0, 5], 'Robin': [0, 2], 'Hero': [0, 2, 6, 8, 9, 10, 11, 12],
           'Sephiroth': [0, 2, 7]})
    print('%d failures' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
