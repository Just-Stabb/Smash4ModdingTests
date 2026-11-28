#!/usr/bin/env python3
"""(2.0) The importer's executable side, run in unicorn on the game's own code (the patched executable, and the patch
set relocated as the Aroma plugin and Cemu place it).

  python3 tools/sm4shclonetool/tests/import_exe_test.py PATCHED.rpx VANILLA.rpx [WORK]

Imported motions (motion_exe.py), for every fighter with some (vanilla and clone):
- the run-time motion table getter 0x02EA9064(manager, kind) (the game's: it calls the descriptor getter and, the
  first time, 0x02EA9008, which copies vl group 1 into the table) returns the grown table: the fighter's own motions
  exactly as the unpatched game gives them (hash, flags after vl group 1), then the imported ones (their animation's
  hash, the copied flags, byte +4 = their vl byte 1, flag 0x80 for vl byte 0), and writes nothing but the table and
  descriptor +0x1C;
- every vanilla kind without imports gets the unpatched game's table, entry for entry;
- the AI's motion count 0x0275BAB0(kind) = the grown count;
- each part table (the motion info's +8 list) the game's for the old motions, the imported part hash or 0 after.
Imported articles / article clones (articles.py, weapon_expand.py):
- the owner's descriptor (the game's getter) +8 = its article list: the unpatched list's entries with the new articles
  at their article ids (kind, max count, the source entry's spawner), the special entries after them;
- the weapon descriptor getter 0x0320D934 for each new kind: a copy of the source kind's descriptor (+8 its own motion
  info with the source's entries, +0x1C its kind where the source's held its own); every game kind unchanged;
- the path builder's lists 0x030BC8E4 for each new kind: its own name and folder; game kinds unchanged;
- the fighter_param_vl load / unload hooks (a cross-fighter source): for the owner's kind the game's function body
  runs for the source's kind and the owner's (the load: the source first, the owner's return value returned; the
  unload: the owner first), once each, with the caller's stack and callee-saved registers restored; for every other
  kind only its own.
With WORK: the same on the patch set (patchset.export) applied at the Aroma plugin's base and evaluated from the Cemu
graphic pack's patches.txt at a Cemu cave base (patchset_test's Overlay).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from sm4shclonetool import exe as X  # noqa: E402
from sm4shclonetool import motion_exe as ME  # noqa: E402
from sm4shclonetool import roster as R  # noqa: E402
from sm4shclonetool.rpx import Rpx  # noqa: E402
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_MEM_WRITE  # noqa: E402
from unicorn import ppc_const as P  # noqa: E402

RET, STACK = 0x01000000, 0x7F00F000
MGR, VL = 0x7E000000, 0x7E100000
FAILS, OKS = [], []


def check(what, got, want=True):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)), flush=True)
    (OKS if ok else FAILS).append(what)
    return ok


def Rg(n):
    return getattr(P, 'UC_PPC_REG_%d' % n)


class M:
    """an image (an Rpx, or patchset_test's Overlay: .memory() / .secs) mapped into unicorn"""

    def __init__(self, x):
        self.x = x
        self.mu = mu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
        mem = x.memory()
        spans = [[a & ~0xFFF, (a + len(b) + 0xFFF) & ~0xFFF] for a, b in mem.items()]
        for s in x.secs:
            if s[1] == 8 and s[3]:
                spans.append([s[3] & ~0xFFF, (s[3] + s[5] + 0xFFF) & ~0xFFF])
        spans.sort()
        merged = []
        for lo, hi in spans:
            if merged and lo <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        for lo, hi in merged:
            mu.mem_map(lo, hi - lo)
        for a, b in mem.items():
            mu.mem_write(a, b)
        mu.mem_map(RET, 0x1000)
        mu.mem_map(0x7E000000, 0x1000000)
        mu.mem_map(0x7F000000, 0x10000)
        self.writes = []
        mu.hook_add(UC_HOOK_MEM_WRITE, lambda uc, acc, a, size, v, u: self.writes.append((a, size)))

    def w(self, a):
        return struct.unpack('>I', bytes(self.mu.mem_read(a, 4)))[0]

    def put(self, a, data):
        self.mu.mem_write(a, bytes(data))

    def call(self, pc, *args):
        for i, v in enumerate(args):
            self.mu.reg_write(Rg(3 + i), v & 0xFFFFFFFF)
        self.mu.reg_write(Rg(1), STACK)
        self.mu.reg_write(P.UC_PPC_REG_LR, RET)
        self.writes = []
        self.mu.emu_start(pc, RET, count=2000000)
        return self.mu.reg_read(Rg(3))


def table_of(m, kind, group1, vl_off):
    """0x02EA9064(MGR, kind) with a fresh manager whose vl[kind] has group 1 = group1 (6 bytes a motion)"""
    m.put(MGR, bytes(0x8000))
    m.put(VL, bytes(0x40))
    data = VL + 0x100
    m.put(data, b''.join(bytes(e) for e in group1))
    m.put(VL + 0xC, struct.pack('>I', data))
    struct_at = MGR + vl_off + 4 * kind
    m.put(struct_at, struct.pack('>I', VL))
    d = m.call(0x02E4313C, 0x104D1631, kind)      # the table is built once a kind (descriptor +0x1C), in place (0x80
    m.put(d + 0x1C, bytes(4))                    # ORed in): start afresh from the file's table
    mi = m.w(d + 4)
    main, cnt = m.w(mi), m.w(mi + 4)
    m.put(main, b''.join(struct.pack('>I', m.x.r32(main + 4 * i)) for i in range(2 * cnt)))
    t = m.call(0x02EA9064, MGR, kind)
    return t, list(m.writes)


def entries(m, t, n):
    return [(m.w(t + 8 * i), m.w(t + 8 * i + 4)) for i in range(n)]


def run(m, v, reg, name):
    """the checks on image m (vanilla v for the reference)"""
    recs_all = ME.motion_records(reg)
    if not recs_all:
        print('     (no imported motions in the registry)')
        return
    kind_of = X._kind_of(reg)
    import random
    rnd = random.Random(7)
    for fname, recs in sorted(recs_all.items()):
        kind = kind_of(fname)
        bkind = kind if kind < 0x41 else R.KINDS.index(next(f['base'] for f in reg['fighters'] if f['name'] == fname))
        count = recs[0]['index']
        n = count + len(recs)
        g1 = [[rnd.randrange(2), rnd.choice((0, 0, 1, 2, 6)), rnd.randrange(60), 0, 0, 0] for _i in range(count)]
        g1 += [list(r['vl']) for r in recs]
        disp_p = m.w(0x02EA9028) & 0xFFFF            # (kind_expand moves it to its relocated array)
        t, wr = table_of(m, kind, g1, disp_p)
        tv, _w = table_of(v, bkind, g1[:count], v.w(0x02EA9028) & 0xFFFF)
        got, ref = entries(m, t, n), entries(v, tv, count)
        check('%s: %s (kind 0x%X): 0x02EA9064 gives the grown table (0x%08X), motions 0-0x%X as the unpatched game '
              'gives %s\'s' % (name, fname, kind, t, count - 1, R.KINDS[bkind]), got[:count], ref)
        want = []
        for i, r in enumerate(recs):
            cf = r.get('flags_from')
            low = (ref[cf][1] & 0x00FFFF7F) if cf is not None else 0
            fl = (low & 0x00FFFFFF) | (r['vl'][1] << 24) | (0x80 if r['vl'][0] else 0)
            want.append((r['hash'], fl))
        check('%s: %s: the %d imported motions 0x%X-0x%X: their animations\' hashes, the copied flags, vl group 1\'s '
              'byte +4 / flag 0x80' % (name, fname, len(recs), count, n - 1), got[count:], want)
        tw = [a for a, s in wr if not (t <= a < t + 8 * n or MGR <= a < MGR + 0x8000 or a >= 0x7F000000)]
        check('%s: %s: 0x02EA9064 writes only the table, its descriptor\'s +0x1C and the stack' % (name, fname),
              len(tw) <= 2, True)
        ai = m.call(0x0275BAB0, kind)
        check('%s: %s: the AI\'s motion count 0x0275BAB0 = 0x%X (the game: 0x%X)' % (name, fname, n, count),
              ai if kind < 0x41 else n, n)
        # the part tables: the motion info's +8 list
        desc_mi = _minfo(m, fname, kind)
        vmi = _minfo(v, R.KINDS[bkind], bkind)
        parts, np_ = m.w(desc_mi + 8), m.w(desc_mi + 12)
        vparts = v.w(vmi + 8)
        ok_parts = []
        for p in range(np_):
            tb, pid = m.w(parts + 8 * p), m.w(parts + 8 * p + 4)
            vt, vpid = v.w(vparts + 8 * p), v.w(vparts + 8 * p + 4)
            if not tb:
                ok_parts.append(vt == 0 and pid == vpid)
                continue
            old = [m.w(tb + 4 * i) for i in range(count)] == [v.w(vt + 4 * i) for i in range(count)]
            new = [m.w(tb + 4 * (count + i)) for i in range(len(recs))] == [
                next((h for tag, h in (r.get('part_hashes') or {}).items() if ME.part_id(tag) == pid), 0) for r in recs]
            ok_parts.append(old and new and pid == vpid)
        check('%s: %s: its %d part tables: the game\'s for the old motions, the imported part hashes (or 0) after'
              % (name, fname, np_), all(ok_parts), True)
    # every other vanilla kind: the game's table (the first 0x20 entries, every vanilla kind but the Miis)
    others = [k for k in range(3, 0x3A) if R.KINDS[k] not in recs_all]
    bad = []
    for k in others:
        g = [[0, 0, 0, 0, 0, 0]] * 0x800
        t, _w = table_of(m, k, g, m.w(0x02EA9028) & 0xFFFF)
        tv, _w = table_of(v, k, g, v.w(0x02EA9028) & 0xFFFF)
        if t != tv or entries(m, t, 0x20) != entries(v, tv, 0x20):
            bad.append(R.KINDS[k])
    check('%s: every other vanilla kind (%d) gets the game\'s own table from 0x02EA9064' % (name, len(others)), bad, [])


def run_articles(m, v, reg, name):
    from sm4shclonetool import articles as A
    recs = A.records(reg)
    if not recs:
        return
    import weapon_expand as W
    kind_of = X._kind_of(reg)
    wk = X.weapon_kinds(reg, imported=True)
    for owner in sorted({a['owner'] for a in recs}):
        k = kind_of(owner)
        bk = R.KINDS.index(A.native(reg, owner))
        d = m.call(0x02E4313C, 0x104D1631, k)
        dv = v.call(0x02E4313C, 0x104D1631, bk)
        al, alv = m.w(d + 8), v.w(dv + 8)
        rows = [[m.w(m.w(al) + 16 * i + 4 * j) for j in range(4)] for i in range(m.w(al + 4))]
        vrows = [[v.w(v.w(alv) + 16 * i + 4 * j) for j in range(4)] for i in range(v.w(alv + 4))]
        mine = [a for a in recs if a['owner'] == owner]
        want = [list(r) for r in vrows]
        if k >= 0x41:                         # a clone's own articles are its copies: kinds remapped as built
            want = [[(r[0] & 0xC0000000) | (rows[i][0] & 0x3FFFFFFF)] + r[1:] for i, r in enumerate(want)]
        special = next((i for i, r in enumerate(vrows) if r[0] & 0x80000000), len(vrows))
        names = [v.x.cstr(v.x.r32(0x10419604 + 4 * kk)) for kk in range(W.OLD_N)]
        owners_ = [v.x.cstr(v.x.r32(0x10418FF0 + 4 * kk)) for kk in range(W.OLD_N)]
        for j, a in enumerate(mine):
            sk = next(kk for kk in range(W.OLD_N) if owners_[kk] == A.native(reg, a['source_owner']) and names[kk] == a['source'])
            sd = v.call(0x02E4313C, 0x104D1631, R.KINDS.index(A.native(reg, a['source_owner'])))
            sl = v.w(sd + 8)
            se = next([v.w(v.w(sl) + 16 * i + 4 * q) for q in range(4)] for i in range(v.w(sl + 4))
                      if v.w(v.w(sl) + 16 * i) & 0x3FFFFFFF == sk)
            want.insert(special + j, [(se[0] & 0xC0000000) | wk[owner][a['name']], int(a.get('max') or 1), se[2], se[3]])
        check('%s: %s (kind 0x%X): its article list = the game\'s with %s at article id%s %s (the source\'s spawner, the '
              'max count given), its special entries after' % (
                  name, owner, k, ', '.join(a['name'] for a in mine), 's' if len(mine) > 1 else '',
                  ', '.join(str(a['article_id']) for a in mine)), (rows, [a['article_id'] for a in mine]),
              (want, [special + j for j in range(len(mine))]))
    bad = [kk for kk in list(range(0, W.OLD_N, 7)) + [W.OLD_N - 1] if m.call(W.DESC_SWITCH, 0, kk) != v.call(W.DESC_SWITCH, 0, kk)]
    check('%s: the weapon descriptor getter: game kinds unchanged' % name, bad, [])
    for a in recs:
        nk = wk[a['owner']][a['name']]
        names = [v.x.cstr(v.x.r32(0x10419604 + 4 * kk)) for kk in range(W.OLD_N)]
        owners_ = [v.x.cstr(v.x.r32(0x10418FF0 + 4 * kk)) for kk in range(W.OLD_N)]
        sk = next(kk for kk in range(W.OLD_N) if owners_[kk] == A.native(reg, a['source_owner']) and names[kk] == a['source'])
        d1, d0 = m.call(W.DESC_SWITCH, 0, nk), v.call(W.DESC_SWITCH, 0, sk)
        size = 0x28
        diff = [o for o in range(0, size, 4) if m.w(d1 + o) != v.w(d0 + o)]
        allowed = {8, 0x14, 0x18, 0x1C, 0x24}
        mi1, mi0 = m.w(d1 + 8), v.w(d0 + 8)
        same_m = (not mi0) or [m.w(m.w(mi1) + 4 * i) for i in range(2 * m.w(mi1 + 4))] == \
            [v.w(v.w(mi0) + 4 * i) for i in range(2 * v.w(mi0 + 4))]
        check('%s: %s/%s weapon kind 0x%X: its descriptor 0x%08X is a copy of %s\'s %s (0x%X): differs only in %s, the '
              'same motion entries' % (name, a['owner'], a['name'], nk, d1, a['source_owner'], a['source'], sk,
                                       sorted(set(diff) & allowed)), (set(diff) <= allowed, same_m), (True, True))

        def lists(mm, kk):
            o = 0x7E800000
            mm.put(o, bytes(0x20))
            mm.call(0x030BC8E4, 0, kk, 0, o, o + 4, o + 8)
            n = mm.w(o + 8)
            return [(_cstr(mm, mm.w(mm.w(o) + 4 * i)), _cstr(mm, mm.w(mm.w(o + 4) + 4 * i))) for i in range(n)]
        check('%s: %s/%s: the file names list 0x030BC8E4 gives its own name / folder %s' % (
            name, a['owner'], a['name'], lists(m, nk)), lists(m, nk), [(a['name'], a['name'])])
    bad = [kk for kk in range(0, W.OLD_N, 11) if lists(m, kk) != lists(v, kk)]
    check('%s: 0x030BC8E4: game kinds unchanged' % name, bad, [])
    # the vl hooks
    pairs = A.cross_sources(reg)
    if not pairs:
        return
    for entry, frame, what in ((A.VL_LOAD, 0x90, 'load'), (A.VL_UNLOAD, 0x28, 'unload')):
        calls = []

        def body(uc, addr, size, user):
            sp = uc.reg_read(Rg(1))
            calls.append((uc.reg_read(Rg(3)), uc.reg_read(Rg(4))))
            uc.reg_write(Rg(3), 0x1000 + uc.reg_read(Rg(4)))        # its "return value"
            uc.reg_write(Rg(1), sp + frame)                         # the replayed stwu's frame popped
            uc.reg_write(P.UC_PPC_REG_PC, uc.reg_read(P.UC_PPC_REG_LR))
        from unicorn import UC_HOOK_CODE
        h = m.mu.hook_add(UC_HOOK_CODE, body, begin=entry + 4, end=entry + 4)
        res = []
        for kk in sorted({o for o, _s in pairs} | {3, 0x19}):
            del calls[:]
            for r_ in range(14, 32):
                m.mu.reg_write(Rg(r_), 0xA0000000 + r_)
            ret = m.call(entry, MGR, kk)
            regs_ok = all(m.mu.reg_read(Rg(r_)) == 0xA0000000 + r_ for r_ in range(14, 32)) and \
                m.mu.reg_read(Rg(1)) == STACK
            srcs = [s_ for o, s_ in pairs if o == kk]
            want = ([(MGR, s_) for s_ in srcs] + [(MGR, kk)]) if what == 'load' else ([(MGR, kk)] + [(MGR, s_) for s_ in srcs])
            res.append((calls == want, ret == 0x1000 + kk, regs_ok))
        m.mu.hook_del(h)
        check('%s: the fighter_param_vl %s hook: the owners %s also %s their sources\' params (%s), every other kind only '
              'its own; the owner\'s return value, the stack and r14-r31 kept' % (
                  name, what, ', '.join('0x%X' % o for o, _s in pairs), what, ', '.join('0x%X' % s_ for _o, s_ in pairs)),
              all(all(x) for x in res), True)


def _cstr(m, a):
    b = bytes(m.mu.mem_read(a, 64))
    return b[:b.index(0)].decode('latin1')


def _minfo(m, fname, kind):
    """the motion info the fighter's descriptor names (the game's getter through the patched switch)"""
    d = m.call(0x02E4313C, 0x104D1631, kind)
    return m.w(d + 4)


def main():
    patched, vanilla = sys.argv[1:3]
    work = sys.argv[3] if len(sys.argv) > 3 else None
    _base, rec = X.find_marker(Rpx(patched))
    reg = rec['registry']
    v = M(Rpx(vanilla))
    from sm4shclonetool import articles as A
    mp = M(Rpx(patched))
    run(mp, v, reg, 'patched rpx')
    run_articles(mp, v, reg, 'patched rpx')
    if work and (ME.motion_records(reg) or A.records(reg)):
        os.makedirs(work, exist_ok=True)
        from sm4shclonetool import patchset as PS
        import patchset_test as PT
        ps = PS.export(vanilla, reg, log=lambda s: None, work=work)
        words, cave = PT.plugin_image(ps, vanilla, PT.PLUGIN_BASE)
        ma = M(PT.Overlay(vanilla, words, PT.PLUGIN_BASE, cave, reg))
        run(ma, v, reg, 'Aroma (0x%08X)' % PT.PLUGIN_BASE)
        run_articles(ma, v, reg, 'Aroma (0x%08X)' % PT.PLUGIN_BASE)
        text, _multi = PS.cemu_patches(ps, [PS.V288_CEMU_HASH])
        secs = [(a, a + len(b)) for a, b in Rpx(vanilla).memory().items()]
        _g, _mm, cw, csize = PT.cemu_parse(text, PT.CEMU_BASE, secs)
        cwords = {a: w for a, w in cw.items() if not PT.CEMU_BASE <= a < PT.CEMU_BASE + csize}
        cblob = bytearray(ps.size)
        for a, w in cw.items():
            if PT.CEMU_BASE <= a < PT.CEMU_BASE + csize:
                struct.pack_into('>I', cblob, a - PT.CEMU_BASE, w)
        mc = M(PT.Overlay(vanilla, cwords, PT.CEMU_BASE, bytes(cblob), reg))
        run(mc, v, reg, 'Cemu (0x%08X)' % PT.CEMU_BASE)
        run_articles(mc, v, reg, 'Cemu (0x%08X)' % PT.CEMU_BASE)
    print('\n%d ok, %d failed' % (len(OKS), len(FAILS)))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
