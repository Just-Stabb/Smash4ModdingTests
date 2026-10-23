#!/usr/bin/env python3
"""Runs the game code tools/weapon_expand.py patches, in unicorn, on the patched and the unpatched RPX.

  python3 tools/weapon_expand_test.py PATCHED.rpx ORIGINAL.rpx [KINDS.json] [--others ARGS_FILE ...]

PATCHED = ORIGINAL + kind_expand + weapon_expand (and any other caves). Checks:
- the words: no overlap with the other caves (--others), no relocation left on a patched in-place word;
- the 13 switches' dispatch from their bound check, for every weapon kind 0x000-C (and past it): kinds
  0x000-0x184 reach the same jump-table entry with the same registers as unpatched; a new kind reaches
  its base's entry with the registers the base gets (the descriptor getter: its own case); unused kinds
  and kinds >= C the default;
- the descriptor getter for every kind: the game's descriptors as before; a new kind's copy is the base's
  bytes but +8 (its own motion info: the base's, entries copied), +0x14 (sub-articles, kinds remapped),
  +0x18 / +0x24 (the param getter copies), +0x1C (its kind);
- the param getter copies read the new fighter's vl slot (kind_expand's array) where the base's read the
  base fighter's, same fields and sizes;
- the static accessors (u32 / u8 with the bound, the 12 flag bits): as before for 0x000-0x184, the base's
  values for a new kind, the invalid values for unused kinds;
- the path builders 0x030BC8E4 (name / folder lists) and 0x030BCB10 (every path type: the owner / name /
  folder strings it formats with): the base's with owner = the new fighter;
- the new fighter's descriptor (kind_expand's copy) +8 = its article list: the base's entries, kinds
  remapped;
- an own singleton (on_hit): the singleton getter returns it for its kind; it is {the vtable copy, the
  base's vtable 2}; the copy is the base's vtable but +0xAC; the hit method asks a fake StatusModule
  for status N on result bits 0x13 (W.HIT_BITS) below N (none at N or more), returns 0, and leaves
  other results to the base's method.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import weapon_expand as W  # noqa: E402
import kind_expand as K  # noqa: E402
from kind_expand_test import Emu, REGS  # noqa: E402
from stage_slot_test import RET  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_LR, UC_PPC_REG_PC  # noqa: E402

fails = 0


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))
    return ok


def read_args(path):
    out = {}
    for tok in open(path).read().split():
        if '=' in tok and not tok.startswith(('reloc:', 'grow:')):
            a, v = tok.split('=')
            out[int(a, 0)] = int(v, 0)
    return out


class Run(Emu):
    def dispatch(self, sw, k, stops, regs):
        """run from the switch's bound check with kind k until a stop address: (stop, regs)"""
        for i in range(3, 32):
            self.mu.reg_write(REGS[i], 0x5A5A0000 + i)
        self.mu.reg_write(REGS[0], 0x5A5A0000)
        self.mu.reg_write(REGS[sw['k']], k)
        self.mu.reg_write(UC_PPC_REG_LR, RET)
        hit = []

        def cb(mu, a, size, ud):
            if a in stops:
                hit.append(a)
                mu.emu_stop()
        h = self.mu.hook_add(UC_HOOK_CODE, cb)
        try:
            self.mu.emu_start(sw['at'], 0xFFFFFFFC, count=80)
        finally:
            self.mu.hook_del(h)
        return (hit[0] if hit else None), tuple(self.r(i) for i in regs)


def main():
    a = sys.argv[1:]
    others = [a[i + 1] for i, x in enumerate(a) if x == '--others']
    pos = [x for i, x in enumerate(a) if x != '--others' and (i == 0 or a[i - 1] != '--others')]
    patched, original = pos[0], pos[1]
    spec = pos[2] if len(pos) > 2 else W.SPEC
    B, info = W.build(spec, original)
    KB, kinfo = K.build(spec, original)
    cap = info['capacity']
    new = info['new']
    img = K.Image(original)
    pimg = K.Image(patched)

    # ---- words
    mine = set(B.words)
    for p in others:
        theirs = set(read_args(p))
        check('no overlap with %s' % os.path.basename(p), sorted(mine & theirs)[:4], [])
    check('the patched RPX has every word', [hex(x) for x in sorted(mine) if pimg.w(x) != B.words[x]][:4], [])
    check('no relocation left on a patched in-place word', [hex(x) for x in B.inplace if x in pimg.relocs()][:4], [])
    check('cave within 0x%08X-0x%08X' % (W.CAVE, W.LIMIT), W.CAVE <= min(x for x in mine if x >= W.CAVE) and
          info['cave_end'] <= W.LIMIT, True)

    E0, E1 = Run(original), Run(patched)

    # ---- the switches
    dcases = {}
    for nk in new:
        d_at = info['descriptors'][nk][0]
        dcases[nk] = None
    for sw in info['switches']:
        stops = set([sw['default']] + [sw['table'] + 4 * k for k in range(W.OLD_N)])
        if sw['at'] == W.DESC_SWITCH:
            # the new kinds' cases: lis/addi r3 / blr in the cave (find them: the descriptor targets)
            for nk in new:
                c = E1.w(info['descriptor_cases'] + 4 * (nk - W.OLD_N))
                dcases[nk] = c
                stops.add(c)
        regs = (sw['k'], sw['t'])
        bad = []
        own = info.get('singletons', {}) if sw['at'] == W.SINGLETON_SWITCH else {}
        for k in list(range(0, cap)) + [cap, cap + 1, 0x7FFF]:
            if k in own:
                got = E1.dispatch(sw, k, stops | {RET}, (3,))
                if got != (RET, (own[k][0],)):
                    bad.append((hex(k), 'own singleton', [hex(x) for x in (got[0] or 0, got[1][0])]))
                continue
            got = E1.dispatch(sw, k, stops, regs)
            if k < W.OLD_N:
                want = E0.dispatch(sw, k, stops, regs)
            elif k in new:
                if sw['at'] == W.DESC_SWITCH:
                    want = (dcases[k], got[1])
                else:
                    want = E0.dispatch(sw, new[k][0], stops, regs)
            else:
                want = (sw['default'], got[1])
            if got[0] != want[0] or (k < W.OLD_N or (k in new and sw['at'] != W.DESC_SWITCH)) and got[1] != want[1]:
                bad.append((hex(k), [hex(x) if x is not None else None for x in (got[0], want[0])]))
        check('switch 0x%08X: every kind 0x0-0x%X (+ past C)' % (sw['at'], cap), bad[:3], [])

    # ---- own singletons and their hit method
    for nk, (o_at, v_at, fn, status) in sorted(info.get('singletons', {}).items()):
        art = new[nk][2]
        at0, vt, vt2 = W.singleton_of(img, new[nk][0])
        check('0x%X %s: singleton {vtable copy, base vtable 2}' % (nk, art), (E1.w(o_at), E1.w(o_at + 4)), (v_at, vt2))
        size = W.vtable_size(img, vt)
        diff = [o for o in range(0, size, 4) if E1.w(v_at + o) != img.w(vt + o)]
        nops, nop_at = info.get('nops', {}).get(nk, ([], 0))
        check('0x%X %s: vtable copy = the base\'s but +0x%X%s' % (nk, art, W.HIT_METHOD, ''.join(
            ', +0x%X' % o for o in nops)), diff, sorted([W.HIT_METHOD] + list(nops)))
        if nops:
            check('0x%X %s: the nop slots lead to a blr' % (nk, art),
                  [E1.w(E1.w(v_at + o)) for o in nops], [0x4E800020] * len(nops))
        check('0x%X %s: +0x%X = the hit method' % (nk, art, W.HIT_METHOD), E1.w(v_at + W.HIT_METHOD), fn)
        old_hit = img.w(vt + W.HIT_METHOD)
        E = Run(patched)
        calls = []
        cur = [0]
        f_status, f_change = E.alloc(8), E.alloc(8)
        E.stub(f_status, lambda e: cur[0])
        E.stub(f_change, lambda e: calls.append(('status', e.r(4))))
        E.stub(old_hit, lambda e: calls.append(('base', e.r(3), e.r(4), e.r(5))) or 0x77)
        weapon, acc, sm, svt = E.alloc(0x100), E.alloc(0x100), E.alloc(0x10), E.alloc(0x100)
        E.setw(weapon + 0x28, acc)
        E.setw(acc + 0x20, sm)
        E.setw(sm, svt)
        E.setw(svt + 0x8C, f_status)
        E.setw(svt + 0x2C, f_change)
        res = []
        for st, bits in ((0, 1), (2, 2), (0, 3), (status - 1, 0x11), (status, 1), (status + 1, 2), (0, 0x10), (0, 8),
                         (status, 4)):
            cur[0] = st
            del calls[:]
            ret = E.call(fn, o_at, weapon, bits)
            res.append((st, bits, ret, list(calls)))
        want = []
        for st, bits in ((0, 1), (2, 2), (0, 3), (status - 1, 0x11), (status, 1), (status + 1, 2), (0, 0x10), (0, 8),
                         (status, 4)):
            if bits & W.HIT_BITS:
                want.append((st, bits, 0, [('status', status)] if st < status else []))
            else:
                want.append((st, bits, 0x77, [('base', o_at, weapon, bits)]))
        check('0x%X %s: hit method (status, bits -> return, calls)' % (nk, art), res, want)

    # ---- the descriptor getter
    bad = []
    for k in range(W.OLD_N):
        if E0.call(W.DESC_SWITCH, 0, k) != E1.call(W.DESC_SWITCH, 0, k):
            bad.append(hex(k))
    check('descriptor getter: the game kinds unchanged', bad[:4], [])
    vl_new = K.mgr_layout(K.load_spec(spec)[0])[0]['vl'][1]
    for nk, (bk, r, art) in sorted(new.items()):
        d1 = E1.call(W.DESC_SWITCH, 0, nk)
        d0 = E0.call(W.DESC_SWITCH, 0, bk)
        size = info['descriptors'][nk][2]
        b0, b1 = bytes(E0.mu.mem_read(d0, size)), bytes(E1.mu.mem_read(d1, size))
        diff = [o for o in range(0, size, 4) if b0[o:o + 4] != b1[o:o + 4]]
        expect = [0x1C] + ([8] if E0.w(d0 + 8) else []) + ([0x14] if E0.w(d0 + 0x14) else []) + \
            [off for off, _s, at in info['getters'].get(nk, []) if at]
        check('0x%X %s: descriptor 0x%08X differs from the base\'s in %s' % (nk, art, d1, sorted(expect)),
              diff, sorted(expect))
        check('0x%X %s: +0x1C = its kind' % (nk, art), E1.w(d1 + 0x1C), nk)
        m0, m1 = E0.w(d0 + 8), E1.w(d1 + 8)
        if m0:
            n = E0.w(m0 + 4)
            n1 = new[nk][1].get('motions', {}).get(nk, n)
            same = bytes(E0.mu.mem_read(m0 + 8, 0x18)) == bytes(E1.mu.mem_read(m1 + 8, 0x18)) and E1.w(m1 + 4) == n1
            e0 = bytes(E0.mu.mem_read(E0.w(m0), 8 * n))
            ents = bytes(E1.mu.mem_read(E1.w(m1), 8 * n1)) == e0 + e0[-8:] * (n1 - n)
            check('0x%X %s: motion info copy (%d motions: the base\'s %d, the last repeated), its own (0x%08X)' % (
                nk, art, n1, n, m1), (same, ents, m1 != m0 and W.CAVE <= m1 < W.LIMIT), (True, True, True))
        s0, s1 = E0.w(d0 + 0x14), E1.w(d1 + 0x14)
        if s0:
            n = E0.w(s0 + 4)
            rows0 = [[E0.w(E0.w(s0) + 16 * i + 4 * j) for j in range(4)] for i in range(n)]
            rows1 = [[E1.w(E1.w(s1) + 16 * i + 4 * j) for j in range(4)] for i in range(n)]
            remap = {b: n2 for n2, (b, rr, _a) in new.items() if rr is r and n2 not in rr.get('new_articles', {})}
            want = [[(e[0] & 0xC0000000) | remap.get(e[0] & 0x3FFFFFFF, e[0] & 0x3FFFFFFF)] + e[1:] for e in rows0]
            check('0x%X %s: sub-articles %s -> %s' % (nk, art, [hex(e[0]) for e in rows0], [hex(e[0]) for e in rows1]),
                  (E1.w(s1 + 4), rows1), (n, want))
        # param getters: the copy reads the new fighter's slot
        for off, src, at in info['getters'].get(nk, []):
            if not at:
                continue
            for E, fn, slot in ((E0, src, 0x111C + 4 * r['bkind']), (E1, at, vl_new + 4 * r['kind'])):
                mgr = E.alloc(0x4000, b'\0')
                E.setw(0x102FF448, mgr)
                vl = E.alloc(0x400, b'\0')
                for o in range(0, 0x400, 4):
                    E.setw(vl + o, 0x77000000 + o)
                E.setw(mgr + slot, vl)
                out = E.alloc(0x20, b'\0')
                ret = E.call(fn, out, 2)
                res = (ret if off == 0x24 else None, E.w(out), E.w(out + 4))
                if E is E0:
                    base_res = res
            check('0x%X %s: +0x%X getter copy reads the new fighter\'s vl slot (+0x%X), as the base\'s reads +0x%X'
                  % (nk, art, off, vl_new + 4 * r['kind'], 0x111C + 4 * r['bkind']), res, base_res)

    # ---- static accessors
    acc = [(0x0320E5BC, 'u32'), (0x0320E5FC, 'u8')] + [(0x0320E634 + 0x14 * i, 'bit%d' % i) for i in range(12)]
    for fn, nm in acc:
        bad = []
        for k in list(range(0, cap)) + ([cap, 0x7FFF] if nm in ('u32', 'u8') else []):   # the flags: no bound
            got = E1.call(fn, 0, k)
            if k < W.OLD_N:
                want = E0.call(fn, 0, k)
            elif k in new:
                want = E0.call(fn, 0, new[k][0])
            elif nm == 'u32':
                want = 0
            elif nm == 'u8':
                want = 6
            else:
                continue                    # the flags had no bound: past 0x184 unused kinds read 0 now
            if got != want:
                bad.append((hex(k), got, want))
        check('accessor 0x%08X (%s): 0x0-0x%X' % (fn, nm, cap), bad[:3], [])

    # ---- path builders
    def lists(E, k, variant=0):
        o = E.alloc(0x20, b'\0')
        E.call(0x030BC8E4, 0, k, variant, o, o + 4, o + 8)
        n = E.w(o + 8)
        return [(E.cstr(E.w(E.w(o) + 4 * i)), E.cstr(E.w(E.w(o + 4) + 4 * i))) for i in range(n)]
    bad = []
    for k in range(W.OLD_N):
        if lists(E0, k) != lists(E1, k):
            bad.append(hex(k))
    check('0x030BC8E4: every game kind unchanged', bad[:4], [])
    for nk, (bk, r, art) in sorted(new.items()):
        own = r.get('new_articles', {}).get(nk)
        want = [(own[0], own[0])] if own else lists(E0, bk)
        check('0x030BC8E4 0x%X: %s name / folder %s' % (nk, 'its own' if own else 'the base\'s', lists(E1, nk)),
              lists(E1, nk), want)

    def paths(E, k):
        rec = []
        if not hasattr(E, 'stubbed'):
            E.stubbed = True
            E.rec = None
            E.stub(0x032D6F6C, lambda e: None)
            E.stub(0x032D4200, lambda e: None)
            E.stub(0x032D3E3C, lambda e: None)

            def fmt(e):
                if e.rec is not None:
                    e.rec.append(tuple(e.cstr(e.r(i)) if 0x02000000 <= e.r(i) < 0x80000000 else e.r(i)
                                       for i in (5, 6, 7, 8)))
            E.stub(0x032D94F4, fmt)
        for variant in range(5):
            E.rec = []
            out = E.alloc(0x100, b'\0')
            E.call(0x030BCB10, out, out + 0x80, k, variant, 0, 0)
            rec.append(E.rec)
        E.rec = None
        return rec
    bad = []
    for k in list(range(0, 0x20)) + [0x100, 0x184]:
        if paths(E0, k) != paths(E1, k):
            bad.append(hex(k))
    check('0x030BCB10: game kinds unchanged (0x0-0x1F, 0x100, 0x184)', bad, [])
    for nk, (bk, r, art) in sorted(new.items()):
        p1, p0 = paths(E1, nk), paths(E0, bk)
        base_owner = img.cstr(img.w(0x10418FF0 + 4 * bk))
        base_name = img.cstr(img.w(0x10419604 + 4 * bk))
        own = r.get('new_articles', {}).get(nk)
        want = [[tuple(r['name'] if x == base_owner else (own[0] if own and x == base_name else x) for x in call)
                 for call in v] for v in p0]
        check('0x030BCB10 0x%X %s: the base\'s paths with owner %s%s (%s)' % (
            nk, art, r['name'], ', its own name' if own else '', p1[0][:1]), p1, want)

    # ---- the new fighter's article list
    for r in kinfo['kinds']:
        al = info['article_lists'].get(r['kind'])
        if al is None:
            continue
        fd1 = E1.w(r['desc'] + 8)
        check('fighter 0x%X: descriptor copy +8 = its article list 0x%08X' % (r['kind'], al), fd1, al)
        base_list = E0.w(W.fighter_descriptor(img, r) + 8)
        n = E0.w(base_list + 4)
        rows0 = [[E0.w(E0.w(base_list) + 16 * i + 4 * j) for j in range(4)] for i in range(n)]
        rows1 = [[E1.w(E1.w(al) + 16 * i + 4 * j) for j in range(4)] for i in range(E1.w(al + 4))]
        own = {}
        for _n2, (_b, rr, _a) in new.items():
            if rr['kind'] == r['kind']:
                own = rr.get('new_articles', {})
        remap = {b: n2 for n2, (b, rr, _a) in new.items() if rr['kind'] == r['kind'] and n2 not in own}
        want = [[(e[0] & 0xC0000000) | remap.get(e[0] & 0x3FFFFFFF, e[0] & 0x3FFFFFFF)] + e[1:] for e in rows0]
        for n2, (_aname, mx) in sorted(own.items()):          # brand-new articles: the base's row, own kind / max
            b = new[n2][0]
            src = [e for e in rows0 if e[0] & 0x3FFFFFFF == b][0]
            want.append([(src[0] & 0xC0000000) | n2, mx] + src[2:])
        check('fighter 0x%X: articles %s' % (r['kind'], [hex(e[0]) for e in rows1]), rows1, want)
    # ---- the module set-up's row (0x02BCB5C0 .. the lwzu): r30 = kind -> r30 = its row, r10 = its first
    #      constructor; game kinds as unpatched, new kinds their base's row, unused kinds as unpatched
    def row(E, k):
        E.mu.reg_write(REGS[30], k)
        E.mu.reg_write(REGS[1], 0x7F00F000)
        E.mu.reg_write(REGS[8], 0x5A5A0008)
        E.mu.reg_write(REGS[10], 0x5A5A000A)
        E.mu.emu_start(W.MODULE_ROW, W.MODULE_ROW + 12, count=40)
        return E.r(30), E.r(10)
    bad = []
    for k in list(range(0, cap)) + [cap, 0x7FFF]:
        want = row(E0, new[k][0] if k in new else k)
        if row(E1, k) != want:
            bad.append(hex(k))
    check('module rows (0x%08X): every kind 0x0-0x%X, a new kind its base\'s' % (W.MODULE_ROW, cap), bad[:4], [])
    check('module row of 0x185 = the fireball\'s (0x%08X), not past the table' % W.MODULE_TABLE, row(E1, 0x185)[0],
          W.MODULE_TABLE)
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
