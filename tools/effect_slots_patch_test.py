#!/usr/bin/env python3
"""Runs tools/effect_slots_patch.py's executable in unicorn against its base: the effect manager (0x032EE380) built by
its own constructor in both, then its slot and pool code driven the same way in both.

  python3 tools/effect_slots_patch_test.py PATCHED.rpx BASE.rpx

Checks:
- static: the base's manager code (0x032EE09C-0x032F2000) and facade (0x0334C3C8-0x0334CC40) hold exactly the patch's
  sites (every slot count / bound `0x29`, every tail offset: 0x1540, 0x1380, addis 1 + -0x3BC0 / -0x3BBC, ori
  0xC470; no other immediate in the tail's range), and the patched words are the tool's;
- the constructor: allocation 0xC490 + DELTA, the mutex initialised at its new place, the header and slots 0-40
  as the base's, slots 41-126 as freshly made slots, the whole tail (pool, count 100, mutex, camera block) the
  base's moved up by DELTA;
- registration (0x032F1388): fighters' / Final Smashes' / common / stage / other categories' banks get the same slots
  as on the base; 86 enemy banks all get slots (41-126), the 87th is refused cleanly (nothing written past the slot
  array); the base takes 10 (26-35);
- lookups after it: the slot finder, the request path 0x032F00A0 (the slot handed to the instance set-up, the pool
  entry, the handle), the efc-flag getters 0x032F1040 / 0x032F10E0 / 0x032F1180, the facade's entry count 0x0334C4D8,
  0x032EFF5C, find-by-bank 0x032F1344, unregister-by-bank 0x032F1CCC; for an enemy bank past the base's 10 too;
- the loops over all slots (per-frame release 0x032EE2DC, unload-all 0x032EEA44) reach slot 126; the loops over the
  pool (0x032EFC5C, 0x032EE7F8, 0x032EE908, 0x032F0310, 0x032F0454, 0x032F05BC, 0x032F0268, 0x032F03BC, 0x032F0508)
  find the same entries as on the base (the old pool place, now slots 41+, holds poison) and the pool count / camera
  block (0x032F1D00, 0x032EFAE4) are written at their new places;
- eft: the System is configured with 127 resources (0x032EF7D4's config +0x18).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import effect_slots_patch as P  # noqa: E402
from kind_expand_test import Emu  # noqa: E402
from diag_crumbs_test import import_relocs  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_MSR  # noqa: E402

STUBS = 0x01F00000                    # import stubs, reached with bla (absolute, 26 bits)
MGR = 0x60800000                      # the manager's allocation (fixed: the rest of the heap matches between runs)
CTOR, FINDER, REGISTER, REQUEST = 0x032EE380, 0x032EFEA0, 0x032F1388, 0x032F00A0
RANGES = [P.CODE_RANGE, P.FACADE_RANGE]
POISON = 0x7570000A                   # looks like a live handle / an enemy effect id
fails = 0


def check(what, ok, detail=''):
    global fails
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': ' + str(detail)))
    return ok


class G(Emu):
    """the RPX with every import call (REL24) sent to a recording stub, paired-single saves nopped, Python stubs for
    the allocators and the manager's outside callees"""

    def __init__(self, path, patched):
        super().__init__(path)
        self.patched = patched
        self.n = P.NEW_SLOTS if patched else P.OLD_SLOTS
        self.d = P.DELTA if patched else 0
        self.mu.mem_map(STUBS, 0x10000)
        self.mu.reg_write(UC_PPC_REG_MSR, self.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
        for lo, hi in RANGES + [(0x0334C000, 0x03351000)]:
            for at in range(lo, hi, 4):
                if self.w(at) >> 26 in (4, 56, 57, 60, 61):
                    self.setw(at, 0x60000000)
        self.log = []
        imp = {}
        for at, typ, _val, name in import_relocs(path):
            if typ != 10:
                continue
            if name not in imp:
                imp[name] = STUBS + 0x10 * len(imp)
                self.stub(imp[name], lambda e, n=name: e.rec(n))
            self.setw(at, 0x48000003 | imp[name])
        self.stub(0x03374578, self.new)
        self.stub(0x03376098, self.new)
        for a in (0x033746FC, 0x03334CA8, 0x032F8874, 0x032F8A64, 0x0334AF5C, 0x032F8FB8, 0x0334B250,
                  0x032EFA20, 0x03336298, 0x0335009C, 0x032F28F4, 0x032F2ACC, 0x032F3090, 0x04A49AA0):
            self.stub(a, lambda e, a=a: (e.rec(a), e.alloc(0x200, b'\0'))[1])
        self.stub(0x04A53F08, lambda e: (e.rec('eft', struct.unpack('>I', bytes(e.mu.mem_read(e.r(4) + 0x18, 4)))[0]),
                                         0)[1])
        for a in (0x0334D568, 0x0334F308, 0x0334E080, 0x032EE0D4, 0x032EE9A0, 0x032DAB00,   # 0x032DAB00: no files
                  0x032D3E3C, 0x032D69B8, 0x032D8B9C, 0x032D4200):          # the registration's path objects
            self.stub(a, lambda e, a=a: (e.rec(a), 0)[1])
        self.stub(0x0334D8D8, lambda e: (e.rec(0x0334D8D8), 1)[1])
        self.stub(0x03336E30, lambda e: e.alloc(0x10, b'\0'))          # the camera's position (3 floats)
        self.cam = self.alloc(0x2400, b'\0')
        self.setw(0x10423DCC, self.cam)
        self.mgr = self.call(CTOR, 0, 0x12345678, count=5000000)
        self.setw(0x10353CA4, self.mgr)

    def rec(self, name, *extra):
        self.log.append((name,) + (extra or tuple(self.r(i) for i in range(3, 8))))

    def new(self, e):
        n = self.r(3)
        self.log.append(('new', n))
        if n >= P.MGR_SIZE:
            self.mu.mem_write(MGR, b'\0' * n)
            return MGR
        return self.alloc(n, b'\0')

    def calls(self, name):
        return [x for x in self.log if x[0] == name]

    def slot(self, n):
        return self.mgr + P.SLOTS_AT + P.SLOT_SIZE * n

    def pool(self, i):
        return self.mgr + P.POOL + self.d + 0x1C0 * i

    def mem(self, a, n):
        return bytes(self.mu.mem_read(a, n))

    def run(self, fn, *args):
        self.log = []
        return self.call(fn, *args, count=5000000)


def static(base, new):
    """the sites, found again in the base's code: every immediate that is the slot count or points into the tail"""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
    found = {'count': [], 'pool': [], 'pre': [], 'cnt': [], 'mutex': [], 'cam': [], 'other': []}
    for lo, hi in RANGES:
        prev = []
        for at in range(lo, hi, 4):
            w = base.w(at)
            op, imm, ra = w >> 26, w & 0xFFFF, (w >> 16) & 31
            if op in (10, 11) and imm == 0x29 or op == 14 and ra == 0 and imm == 0x29:
                found['count'].append(at)
            elif op in [14] + list(range(32, 56)) and ra:
                s = imm - 0x10000 if imm & 0x8000 else imm
                base_lis = [p for p in prev if p >> 26 == 15 and (p >> 21) & 31 == ra]
                hi16 = (base_lis[-1] & 0xFFFF) if base_lis else None
                if s == 0x1540:
                    found['pool'].append(at)
                elif s == 0x1380:
                    found['pre'].append(at)
                elif s in (-0x3BC0, -0x3BBC):
                    found['cnt' if s == -0x3BC0 else 'mutex'].append(at)
                elif 0x1480 <= s < 0x8000 and not (hi16 is not None and 0x1000 <= hi16 < 0x1100) \
                        and not (hi16 is not None and 0x0200 <= hi16 < 0x0500):
                    found['other'].append((at, md.disasm(struct.pack('>I', w), at).__next__().op_str))
            elif op == 24 and P.MGR_SIZE - 0x40 <= imm < P.MGR_SIZE:
                found['cam'].append(at)
            prev = (prev + [w])[-24:]
    check('static: the slot count / bound sites (%d)' % len(found['count']), found['count'] == P.COUNT_SITES,
          found['count'])
    check('static: the pool sites 0x1540 (%d)' % len(found['pool']), found['pool'] == P.POOL_SITES, found['pool'])
    check('static: the pool loop bases 0x1380 (%d)' % len(found['pre']), found['pre'] == P.POOL_PRE_SITES, found['pre'])
    check('static: the pool count sites (%d)' % len(found['cnt']), found['cnt'] == P.COUNT_FIELD_SITES, found['cnt'])
    check('static: the mutex sites (%d)' % len(found['mutex']), found['mutex'] == P.MUTEX_SITES, found['mutex'])
    check('static: the camera block site', found['cam'] == P.CAMERA_SITES, found['cam'])
    # what's left in the tail's range: data / code addresses (lis 0x10xx / 0x03xx bases resolved above), and loads
    # from other objects' fields (checked by hand: 0x032EEFB4 / 0x032EFB84.. read [0x10423DCC]'s camera at +0x23E0 /
    # +0x2324, not the manager)
    known = {0x032EEFB4, 0x032EEFC0, 0x032EFB84, 0x032EFB98, 0x032EFB9C, 0x032EFBA0, 0x032EFBB4, 0x032EFBBC,
             0x032EFBC0}
    other = [x for x in found['other'] if x[0] not in known]
    check('static: no other immediate in the tail\'s range', other == [], ['0x%08X %s' % x for x in other])
    p = P.patches()
    bad = [hex(a) for a, w in p.items() if new.w(a) != w]
    check('the patched words are the tool\'s (%d)' % len(p), bad == [], bad)
    diff = [hex(a) for lo, hi in RANGES for a in range(lo, hi, 4)
            if base.w(a) != new.w(a) and a not in p]
    check('nothing else differs in the manager\'s code / facade (raw image)', diff == [], diff[:8])


def layout(b, n):
    d = P.DELTA
    check('constructor: the manager allocated with 0xC490 + DELTA (0x%X)' % (P.MGR_SIZE + d),
          [x[1] for x in n.log if x[0] == 'new' and x[1] >= P.MGR_SIZE] == [P.MGR_SIZE + d], n.log[:1])
    mi = [x[1] for x in n.log if x[0] == 'OSInitMutex']
    check('constructor: the mutex initialised at +0x%X' % (P.MUTEX + d), mi == [n.mgr + P.MUTEX + d], [hex(v) for v in mi])
    head = P.SLOTS_AT + P.OLD_SLOTS * P.SLOT_SIZE
    check('constructor: header and slots 0-40 as the base\'s', b.mem(b.mgr, head) == n.mem(n.mgr, head))
    fresh = n.mem(n.slot(0), P.SLOT_SIZE)
    check('constructor: slots 41-126 made like slot 0', all(n.mem(n.slot(k), P.SLOT_SIZE) == fresh
                                                           for k in range(P.OLD_SLOTS, P.NEW_SLOTS)))
    tb, tn = b.mem(b.mgr + head, P.MGR_SIZE - head), n.mem(n.mgr + head + d, P.MGR_SIZE - head)
    bad = []
    for o in range(0, len(tb), 4):
        wb, wn = struct.unpack_from('>I', tb, o)[0], struct.unpack_from('>I', tn, o)[0]
        if wb != wn and not (b.mgr + head <= wb < b.mgr + P.MGR_SIZE and wn == wb + d):
            bad.append(hex(head + o))
    check('constructor: the tail (pool, count, mutex, camera block) is the base\'s moved up by 0x%X' % d, bad == [],
          bad[:8])
    check('constructor: the pool count is 100 at +0x%X' % (P.POOL_COUNT + d), n.w(n.mgr + P.POOL_COUNT + d) == 100)


def register(e, bank, path=0x10190700):
    e.run(REGISTER, e.mgr, bank, path, 0, 0, 0, 0)
    s = e.run(FINDER, e.mgr, bank, 0)
    return s if s < e.n else -1


def main():
    new, old = sys.argv[1:3]
    bn, nn = G(old, False), G(new, True)
    static(bn, nn)
    layout(bn, nn)
    # registration: other categories interleaved with enemies, in both
    others = [0x100, 0x200, 0x303, 0x341, 0x30A, 0x403, 0x502, 0x504, 0x901, 0x905]
    enemies = [0x700 + k for k in range(0x00, 0x5A)][:P.ENEMY_COUNT + 1]
    got = {'b': {}, 'n': {}}
    order = []
    for i, bank in enumerate(enemies):
        order.append(bank)
        if i < len(others):
            order.append(others[i])
    for bank in order:
        got['b'][bank] = register(bn, bank)
        got['n'][bank] = register(nn, bank)
    same = [hex(k) for k in others if got['b'][k] != got['n'][k] or got['b'][k] < 0]
    check('registration: the other categories\' banks take the base\'s slots (%s)' %
          ' '.join('%X:%d' % (k, got['n'][k]) for k in others), same == [], same)
    en = [got['n'][k] for k in enemies]
    eb = [got['b'][k] for k in enemies]
    check('registration: base: 10 enemy banks in slots 26-35, the rest refused', eb[:10] == list(range(26, 36))
          and set(eb[10:]) == {-1}, eb[:12])
    check('registration: patched: %d enemy banks in slots 41-126, the %dth refused' % (P.ENEMY_COUNT,
          P.ENEMY_COUNT + 1), en[:-1] == list(range(41, 127)) and en[-1] == -1, en)
    check('registration: slots 26-35 left empty (patched)', all(nn.w(nn.slot(k)) == 0 for k in range(26, 36)))
    check('registration: slots 0-40 (but 26-35) hold the same banks', all(
        bn.w(bn.slot(k)) == nn.w(nn.slot(k)) for k in range(41) if not 26 <= k < 36))
    head = P.SLOTS_AT + P.NEW_SLOTS * P.SLOT_SIZE
    check('registration: the refused bank wrote nothing past the slot array (the pool\'s first entry unchanged)',
          nn.mem(nn.mgr + head, 0x1C0 * 2) == bn.mem(bn.mgr + P.SLOTS_AT + P.OLD_SLOTS * P.SLOT_SIZE, 0x1C0 * 2))
    # efc data for an enemy bank in both (base: slot 26's bank 0x700; patched: its slot 41, and the last, slot 126)
    efc = {}
    for e in (bn, nn):
        f = e.alloc(0x100, b'\0')
        ent = e.alloc(0x100, b'\0')
        e.mu.mem_write(f, b'EFCF' + struct.pack('>HHH', 0, 7, 4))
        for i in range(4):
            e.setw(ent + 16 * i, [1, 2, 4, 7][i])
            e.setw(ent + 16 * i + 4, 1)
        e.mu.mem_write(e.mgr + 0xB1, b'\0')                # ready (0x032EF7D4 clears it when eft is up)
        efc[e] = (f, ent)

    def give(e, bank):
        s = e.run(FINDER, e.mgr, bank, 0)
        e.setw(e.slot(s) + 8, efc[e][0])
        e.setw(e.slot(s) + 0xC, efc[e][1])
        return s
    lastb = enemies[P.ENEMY_COUNT - 1]
    sb, sn, sl = give(bn, 0x700), give(nn, 0x700), give(nn, lastb)
    # request: the slot handed to the instance set-up, the pool entry, the handle
    for e, bank, s in ((bn, 0x700, sb), (nn, 0x700, sn), (nn, lastb, sl)):
        h = e.run(REQUEST, e.mgr, (bank << 16) | 2, 0, 0, 0, 0, 0, 0)
        c = e.calls(0x0334D8D8)
        ok = h != 0 and len(c) == 1 and c[0][1] == e.pool(h >> 24) and c[0][3] == e.slot(s) \
            and e.w(c[0][3]) == bank and c[0][4] == (bank << 16) | 2
        check('request %s 0x%X0002: handle 0x%X, instance = pool entry %d, slot %d handed over' % (
              'patched' if e.patched else 'base', bank, h, h >> 24, s), ok, [hex(v) for v in (c[0] if c else ())])
        e.setw(e.pool(h >> 24), h)                         # the instance set-up's own first store (stubbed)
        e.setw(e.pool(h >> 24) + 4, (bank << 16) | 2)
    nn.setw(nn.pool(1), 0)                                 # the slot-126 request's entry freed again
    hb = bn.w(bn.pool(0)) | 0
    hn = nn.w(nn.pool(0))
    check('request: the same handle / pool entry on both (0x%X)' % hn, hb == hn)
    # flag getters, the facade's entry count, 0x032EFF5C (needs the eft System at +0x38)
    for fn, want in ((0x032F1040, 1), (0x032F10E0, 1), (0x032F1180, 1)):
        rb = bn.run(fn, bn.mgr, 0x7000003)
        rn = nn.run(fn, nn.mgr, 0x7000003)
        rl = nn.run(fn, nn.mgr, (lastb << 16) | 3)
        check('flag getter 0x%08X: base %d, patched %d, slot 126 %d' % (fn, rb, rn, rl), rb == rn == rl == want)
    rb, rn, rl = bn.run(0x0334C4D8, 0x700), nn.run(0x0334C4D8, 0x700), nn.run(0x0334C4D8, lastb)
    check('facade 0x0334C4D8 (entry count): %d / %d / slot 126 %d' % (rb, rn, rl), rb == rn == rl == 4)
    for e in (bn, nn):
        sysm = e.alloc(0x40, b'\0')
        arr = e.alloc(4 * (P.NEW_SLOTS + 32), b'\0')
        res = e.alloc(0x40, b'\0')
        inner = e.alloc(0x40, b'\0')
        e.setw(sysm + 8, arr)
        e.setw(e.mgr + 0x38, sysm)
        e.setw(res + 8, inner)
        e.setw(inner + 8, 10)
        sets = e.alloc(0x40, b'\0')
        e.setw(res + 0x14, sets)
        e.setw(sets + 0x20, 0x5E7DA7A)
        for s in range(e.n):
            e.setw(arr + 4 * s, res)
    rb, rn, rl = bn.run(0x032EFF5C, bn.mgr, 0x700, 1), nn.run(0x032EFF5C, nn.mgr, 0x700, 1), \
        nn.run(0x032EFF5C, nn.mgr, lastb, 1)
    check('0x032EFF5C (the eft resource\'s emitter set data): 0x%X / 0x%X / slot 126 0x%X' % (rb, rn, rl),
          rb == rn == rl == 0x5E7DA7A)
    for e in (bn, nn):
        e.setw(e.mgr + 0x38, 0)
    # find-by-bank, unregister-by-bank
    nn.setw(nn.slot(sl) + 0x78, 3)
    check('find-by-bank 0x032F1344 (slot 126, refcount 3)', nn.run(0x032F1344, nn.mgr, lastb) == 1)
    nn.run(0x032F1CCC, nn.mgr, lastb)
    c = nn.calls(0x032EE9A0)
    check('unregister-by-bank 0x032F1CCC reaches slot 126', len(c) == 1 and c[0][2] == nn.slot(sl), c)
    # per-frame release: slot 126 with refcount 1 and the temporary flag -> unloaded; slot 125 refcount 5 -> 4
    nn.setw(nn.slot(sl) + 0x78, 1)
    nn.mu.mem_write(nn.slot(sl) + 0x7C, b'\1')
    nn.setw(nn.slot(sl - 1) + 0x78, 5)
    nn.run(0x032EE2DC, nn.mgr)
    c = nn.calls(0x032EE0D4)
    check('per-frame release 0x032EE2DC: slot 126 unloaded, slot 125 counted down',
          [x[2] for x in c] == [nn.slot(sl)] and nn.w(nn.slot(sl - 1) + 0x78) == 4, c)
    nn.run(0x032EEA44, nn.mgr)
    c = [x[2] for x in nn.calls(0x032EE9A0)]
    want = [nn.slot(k) for k in range(P.NEW_SLOTS) if nn.w(nn.slot(k))]
    check('unload-all 0x032EEA44: every occupied slot, 41-126 included (%d)' % len(c), c == want and nn.slot(126) in c)
    # the pool loops: identical entries found on both; the old pool place (patched: slots 41+) poisoned
    pz = []
    for i in range(1, 8):                                # the base's pool entries 1-7 place (patched: slots 44-68)
        for o, v in ((0, POISON), (4, POISON), (8, 0x55)):
            a = nn.mgr + P.POOL + 0x1C0 * i + o
            pz.append((a, nn.w(a), v))
            nn.setw(a, v)
    for e in (bn, nn):
        e.setw(e.pool(7), 0x07000099)
        e.setw(e.pool(7) + 4, 0x7000001)
        e.setw(e.pool(7) + 8, 0x55)
    tests = [(0x032EFC5C, 'per-frame update 0x032EFC5C', (), 0x0334E080),
             (0x032EE908, 'kill-by-bank 0x032EE908', (0x700,), 0x0334D568),
             (0x032EE7F8, 'kill-all 0x032EE7F8', (), 0x0334D568),
             (0x032F0310, 'by-key 0x032F0310', (0x55, 0xFF, 0, 0, 0), 0x0334F308),
             (0x032F0454, 'by-key 0x032F0454', (0x55, 0xFF, 0, 0, 0), 0x0334F308),
             (0x032F05BC, 'restart-by-key 0x032F05BC', (0x55, 0xFF, 0, 0, 0), 0x0334D8D8),
             (0x032F0268, 'by-handle 0x032F0268', (0x07000099, 0, 0), 0x0334F308),
             (0x032F03BC, 'by-handle 0x032F03BC', (0x07000099, 0, 0, 0), 0x0334F308)]
    for fn, what, args, cb in tests:
        bn.run(fn, bn.mgr, *args)
        nn.run(fn, nn.mgr, *args)
        cb_b = [x[1] - bn.pool(0) for x in bn.calls(cb)]
        cb_n = [x[1] - nn.pool(0) for x in nn.calls(cb)]
        extra = ''
        if cb == 0x0334D8D8:
            sb_ = [x[3] for x in bn.calls(cb)]
            sn_ = [x[3] for x in nn.calls(cb)]
            extra = ' (slot %s)' % ['%d' % ((s - nn.slot(0)) // P.SLOT_SIZE) for s in sn_]
            ok = sb_ == [bn.slot(sb)] and sn_ == [nn.slot(sn)]
        else:
            ok = True
        check('%s: the same pool entries as the base %s%s' % (what, [v // 0x1C0 for v in cb_n], extra),
              ok and cb_b == cb_n and cb_n, (cb_b, cb_n))          # (void functions: r3 is left over)
    nn.run(0x032F0508, nn.mgr, 0x07000099, 0xAAAA, 0xBBBB, 0, 0, 0, 0)
    check('follow set-up 0x032F0508 writes the pool entry\'s +0x34 / +0x38',
          (nn.w(nn.pool(7) + 0x34), nn.w(nn.pool(7) + 0x38)) == (0xAAAA, 0xBBBB))
    check('the poisoned old pool place untouched by the pool code', all(nn.w(a) == v for a, _w, v in pz))
    for a, w, _v in pz:
        nn.setw(a, w)
    # the pool count, the camera block, the eft config
    for e in (bn, nn):
        e.run(0x032F1D00, e.mgr, 0, 50, 0, 0)
    check('pool count set at +0x%X (0x032F1D00)' % (P.POOL_COUNT + P.DELTA),
          nn.w(nn.mgr + P.POOL_COUNT + P.DELTA) == 50 and bn.w(bn.mgr + P.POOL_COUNT) == 50)
    for e in (bn, nn):
        e.setw(e.cam + 0x2324, 1)
        for i in range(6):
            e.mu.mem_write(e.cam + 0x2328 + 4 * i, struct.pack('>f', 1.5 + i))
        e.run(0x032EFAE4, e.mgr)
    blk = [nn.mem(nn.mgr + P.CAMERA + P.DELTA, 0x1C), bn.mem(bn.mgr + P.CAMERA, 0x1C)]
    check('camera block written at +0x%X (0x032EFAE4)' % (P.CAMERA + P.DELTA), blk[0] == blk[1] and blk[0][0] == 1,
          blk)
    for e in (bn, nn):
        e.run(0x032EF7D4, e.mgr, e.alloc(0x40, b'\0'))
    rb, rn = bn.calls('eft'), nn.calls('eft')
    check('eft System config: %s resources (base %s)' % (rn[0][1] if rn else '?', rb[0][1] if rb else '?'),
          rn and rb and rn[0][1] == P.NEW_SLOTS and rb[0][1] == P.OLD_SLOTS)
    print('%d failure(s)' % fails if fails else 'all ok')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
