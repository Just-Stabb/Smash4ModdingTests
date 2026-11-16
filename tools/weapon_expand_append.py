#!/usr/bin/env python3
"""New weapon kinds on an executable that already has weapon_expand.py's cave (exe_v46p -> exe_v46q: Byleth's arrows
and whip), without moving anything already there. Prints / writes rpx_patch.py arguments.

  python3 tools/weapon_expand_append.py EXE OLD_KINDS.json NEW_KINDS.json ARGS_OUT [--info]
  python3 tools/weapon_expand_append.py test PATCHED EXE OLD_KINDS.json NEW_KINDS.json
      tools/weapon_expand_test.py on PATCHED with EXE as its original: every weapon kind (the old new ones too) through
      the 13 switches, the descriptors, getters, accessors, path builders, module rows and the new fighter's article
      list (the old new kinds are compared with their bases on EXE, as the appended ones). Its "cave within
      0x04BB0000-0x04BB8000" check fails by design (APPEND).

weapon_expand.py builds its whole cave in one pass from an un-grown base RPX: the fighters' article lists first, then
the strings, the 7 per-kind tables (C = weapon_capacity entries), the descriptor copies, ... and hooks 13 switches, 54
table sites, the module set-up, Kirby's copy resources and the inline kind compares in place. The user's executable has
had it since exe_v40 and no un-grown base of it is kept (docs/kind-expansion.md), and a new fighter's article list at the
cave's start would move every later word of it, which other caves call into (kirby_copy_new_cave.py re-hooks its copy
stubs). So this one adds the NEW spec's new weapon kinds (every kind of NEW's records that OLD doesn't have; they must
come after OLD's, as weapon_expand.py numbers them) the way weapon_expand.py's build makes them, into what is there:
- their entries in the cave's 7 tables (each found by its first 0x185 entries, the game's own table's), as
  weapon_expand.py fills them (owner = the new fighter, a brand-new article's own name / folder, the base's rest);
- their descriptor copies (+8 own motion info, +0x14 remapped sub-articles, +0x18 / +0x24 the param getters reading
  the new fighter's vl slot, +0x1C), descriptor cases and the descriptor-cases table entries; the base-kinds table
  entries (the 11 method switches, the singleton getter and the module set-up send a new kind to its base's case);
- the inline kind compares of their bases (weapon_expand.kind_compares: a base with no copies before, its sites still
  the game's), a stub each;
- the new fighter's article list (its base's, the copied kinds remapped, brand-new articles before the first special
  entry) and kind_expand.py's descriptor copy +8 pointing at it;
all in APPEND (weapon_expand.py's own cave is full), after its last used word. Not supported (asserted): on_hit / nop / modules /
kirby_copy / spawn_from articles, a fighter whose list already exists, bases with copies already.

The switch parsers read the patched form: the descriptor getter's original jump table is still in place after the far
jump weapon_expand.py wrote (its last 1 - 2 words are the game's: bctr, or mtctr r0 / bctr). Tests:
tools/weapon_expand_test.py on the result (the new kinds' checks).
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kind_expand as K  # noqa: E402
import weapon_expand as W  # noqa: E402
from ppcasm import ha  # noqa: E402

BCTR = 0x4E800420
# where the appended kinds go: trail_table_cave.py's space past its GROW (its table stays below 0x04B9C000) up to
# edge_counter_cave.py (0x04B9D000), inside the code region the executable has run since exe_v40 (below 0x04BD4000)
APPEND, APPEND_LIMIT = 0x04B9C000, 0x04B9D000
WCAVE_END = W.LIMIT


def parse_patched_switch(img, a):
    """weapon_expand.parse_switch on a switch weapon_expand.py has hooked: the bound C - 1, a far jump after the bgt"""
    w = img.w(a)
    assert w >> 26 == 10, 'no cmplwi at 0x%08X' % a
    k = (w >> 16) & 0x1F
    b = a + 4
    if img.w(b) >> 26 != 16:
        b += 4
    assert img.w(b) >> 26 == 16, 'no bgt after 0x%08X' % a
    x = b + 4
    j = [img.w(x + 4 * i) for i in range(4)]
    assert j[0] >> 26 == 15 and j[2] >> 26 == 31 and j[3] == BCTR, 'no far jump at 0x%08X' % x
    stub = ((j[0] & 0xFFFF) << 16) + K.sx16(j[1])
    if img.w(x + 16) == BCTR:
        form, bctr = 'addis', x + 16
    else:
        assert img.w(x + 20) == BCTR, 'switch 0x%08X: no bctr left after the far jump' % a
        form, bctr = 'r0', x + 20
    return dict(at=a, k=k, bgt=b, default=K.branch_target(b, img.w(b)), x=x, form=form, table=bctr + 4, bctr=bctr,
                stub=stub & 0xFFFFFFFF)


def lis_addi_pairs(img, at, n):
    """the 32-bit constants built by lis rX / addi rX (or addic) pairs in n words from at, in order"""
    out = []
    for i in range(n - 1):
        w, w2 = img.w(at + 4 * i), img.w(at + 4 * i + 4)
        if w >> 26 == 15 and (w >> 16) & 31 == 0 and w2 >> 26 in (12, 14) and (w2 >> 16) & 31 == (w >> 21) & 31:
            out.append((((w & 0xFFFF) << 16) + K.sx16(w2)) & 0xFFFFFFFF)
    return out


class Img(K.Image):
    pass


def find_table(img, addr, es, cap):
    """the cave copy of the game's table at addr (es bytes an entry): its first OLD_N entries"""
    want = img.blob(addr, es * W.OLD_N)
    cave = img.blob(W.CAVE, WCAVE_END - W.CAVE)
    at = cave.find(want)
    while at >= 0 and at % 4:
        at = cave.find(want, at + 1)
    assert at >= 0, 'no cave copy of the table 0x%08X' % addr
    assert cave.find(want, at + 1) < 0 or es == 1, 'two cave copies of the table 0x%08X' % addr
    return W.CAVE + at


def build(exe, old_spec, new_spec):
    import kind_expand_incremental as KI
    KI._install(exe)                      # kind_expand's own switches read as the originals (fighter descriptors)
    img = K.Image(exe)
    W.parse_switch = parse_patched_switch
    old_recs, cap = W.load_weapons(old_spec, img)
    new_recs, cap2 = W.load_weapons(new_spec, img)
    assert cap == cap2
    old_kinds = {nk for _r, lst in old_recs for nk, _b, _a in lst}
    old_fighters = {K.num(r['kind']) for r, _l in old_recs}
    new = {}
    recs = []
    for r, lst in new_recs:
        add = [(nk, bk, art) for nk, bk, art in lst if nk not in old_kinds]
        if not add:
            continue
        assert K.num(r['kind']) not in old_fighters, 'fighter 0x%X has an article list already' % K.num(r['kind'])
        assert len(add) == len(lst)
        for key in ('on_hit', 'modules', 'kirby_copy', 'spawn_from', 'motions'):
            # ("motions" also holds the fighter's own body-motion changes, keyed by motion: only weapon kinds count)
            assert not any(nk in (r.get(key) or {}) for nk, _b, _a in lst), \
                'weapon_expand_append: "%s" not supported' % key
        r['bkind'] = K.kind_index([img.cstr(img.w(K.TABLES['lower'][0] + 4 * k)) for k in range(K.OLD_N)], r['base'])
        recs.append((r, lst))
        for nk, bk, art in lst:
            new[nk] = (bk, r, art)
    assert new and min(new) > max(old_kinds), 'the new kinds must come after the old ones'
    B = W.Build(img)
    # weapon_expand.py's cave is full (exe_v46p: 0x04BB7EB8 of 0x04BB8000): the appended kinds go to APPEND
    blob = img.blob(APPEND, APPEND_LIMIT - APPEND)
    used = len(blob.rstrip(b'\0'))
    B.pc = APPEND + ((used + 0xF) & ~0xF)
    W.LIMIT = APPEND_LIMIT
    info = {'start': B.pc}
    # ---- strings: the owners, brand-new names
    sblob, sptr = bytearray(), {}
    for r, _lst in recs:
        sptr[r['name']] = len(sblob)
        sblob += r['name'].encode() + b'\0'
        for _nk, (aname, _mx) in sorted(r.get('new_articles', {}).items()):
            if aname not in sptr:
                sptr[aname] = len(sblob)
                sblob += aname.encode() + b'\0'
    s_at = B.alloc(len(sblob) + (-len(sblob) % 4))
    B.data(s_at, bytes(sblob), 'strings')
    sptr = {s: s_at + o for s, o in sptr.items()}
    # ---- the tables' entries
    info['tables'] = {}
    for nm, addr in W.NAME_TABLES:
        at = find_table(img, addr, 4, cap)
        info['tables'][nm] = at
        for k in sorted(new):
            bk, r, _a = new[k]
            own_name = r.get('new_articles', {}).get(k)
            if nm == 'owner':
                v = sptr[r['name']]
            elif own_name and nm in ('name', 'folder'):
                v = sptr[own_name[0]]
            else:
                v = img.w(addr + 4 * bk)
            assert img.w(at + 4 * k) == img.w(addr), 'table %s: kind 0x%X is in use' % (nm, k)
            B.put(at + 4 * k, v, 'table %s 0x%X' % (nm, k))
    for nm, addr, es, invalid in W.STATIC_TABLES:
        at = find_table(img, addr, es, cap)
        info['tables'][nm] = at
        rd = {1: img.b, 2: img.h, 4: img.w}[es]
        for k in sorted(new):
            bk, r, _a = new[k]
            v = rd(addr + es * bk)
            if nm == 'u16':
                v |= r.get('flags_set', {}).get(k, 0)
            assert rd(at + es * k) == invalid, 'table %s: kind 0x%X is in use' % (nm, k)
            wa = (at + es * k) & ~3
            word = img.w(wa) if wa not in B.words else B.words[wa]
            sh = 8 * (4 - es - (at + es * k - wa))
            mask = ((1 << (8 * es)) - 1) << sh
            word = (word & ~mask) | (v << sh)
            B.words.pop(wa, None)
            B.put(wa, word, 'table %s 0x%X' % (nm, k))
    # ---- the descriptor getter's / singleton getter's / module set-up's tables
    dsw = parse_patched_switch(img, W.DESC_SWITCH)
    dpairs = lis_addi_pairs(img, dsw['stub'], 32)
    dt = dpairs[1]                       # orig: the jump table; new: the descriptor cases
    assert dpairs[0] == dsw['table'], 'descriptor stub 0x%08X' % dsw['stub']
    ssw = parse_patched_switch(img, W.SINGLETON_SWITCH)
    spairs = lis_addi_pairs(img, ssw['stub'], 32)
    st, bt = spairs[1], spairs[2]        # orig table, singleton cases, base kinds
    mr = K.branch_target(W.MODULE_ROW, img.w(W.MODULE_ROW))
    mpairs = lis_addi_pairs(img, mr, 24)
    assert mpairs[1] == bt, 'module-row stub 0x%08X: base table 0x%08X, not 0x%08X' % (mr, mpairs[1], bt)
    info.update(dt=dt, st=st, bt=bt, rt=mpairs[0])
    for k in sorted(new):
        assert img.w(bt + 4 * (k - W.OLD_N)) == 0xFFFF and img.w(dt + 4 * (k - W.OLD_N)) == 0, 'kind 0x%X in use' % k
        assert img.w(st + 4 * (k - W.OLD_N)) == 0 and img.w(mpairs[0] + 4 * (k - W.OLD_N)) == 0
    # ---- per new kind: its descriptor copy (weapon_expand.build's loop) and its case
    fcap, _kinds = K.load_spec(new_spec)
    vl_new = K.mgr_layout(fcap)[0]['vl'][1]
    descs = W.all_descriptors(img)
    info['descriptors'] = {}
    for nk in sorted(new):
        bk, r, art = new[nk]
        d = W.descriptor_of(img, bk)
        nxt = [x for x in descs if x > d]
        size = min(W.DESC_COPY_MAX, (nxt[0] - d) if nxt else W.DESC_COPY_MAX)
        blob = bytearray(img.blob(d, size))
        if struct.unpack_from('>I', blob, 0x1C)[0] == bk:
            struct.pack_into('>I', blob, 0x1C, nk)
        mi = img.w(d + 8)
        if mi:
            ents, cnt = img.w(mi), img.w(mi + 4)
            m_at = B.alloc(W.MINFO_SIZE, 8)
            e_at = B.alloc(8 * cnt, 8) if cnt else 0
            mib = bytearray(img.blob(mi, W.MINFO_SIZE))
            struct.pack_into('>II', mib, 0, e_at if cnt else ents, cnt)
            B.data(m_at, bytes(mib), 'weapon 0x%X motion info' % nk)
            if cnt:
                B.data(e_at, img.blob(ents, 8 * cnt), 'weapon 0x%X motions' % nk)
            struct.pack_into('>I', blob, 8, m_at)
        sub = img.w(d + 0x14)
        if sub:
            ents, cnt = img.w(sub), img.w(sub + 4)
            remap = {b: n for n, (b, rr, _a) in new.items() if rr is r and n not in r.get('new_articles', {})}
            rows = []
            for i in range(cnt):
                e = [img.w(ents + W.ARTICLE * i + 4 * j) for j in range(4)]
                if (e[0] & 0x3FFFFFFF) in remap:
                    e[0] = (e[0] & 0xC0000000) | remap[e[0] & 0x3FFFFFFF]
                rows.append(e)
            s_at2 = B.alloc(8 + W.ARTICLE * cnt)
            B.data(s_at2, struct.pack('>II', s_at2 + 8, cnt) + b''.join(struct.pack('>4I', *e) for e in rows),
                   'weapon 0x%X sub-articles' % nk)
            struct.pack_into('>I', blob, 0x14, s_at2)
        own = vl_new + 4 * K.num(r['kind'])
        getters = []
        for off in (0x18, 0x24):
            src = struct.unpack_from('>I', blob, off)[0] if off + 4 <= size else 0
            if not src or not 0x02000000 <= src < 0x10000000:
                continue
            ws = W.copy_getter(img, src, r['bkind'], own)
            if ws is None:
                getters.append((off, src, None))
                continue
            g_at = B.alloc(4 * len(ws))
            for i, w in enumerate(ws):
                B.put(g_at + 4 * i, w, ('getter copy', src, i))
            struct.pack_into('>I', blob, off, g_at)
            getters.append((off, src, g_at))
        d_at = B.alloc(len(blob), 8)
        B.data(d_at, bytes(blob), 'weapon 0x%X descriptor (copy of 0x%X)' % (nk, bk))
        c_at = B.alloc(12)
        B.code(c_at, 'lis r3, 0x%X\naddi r3, r3, %d\nblr' % (ha(d_at), K.slo(d_at)))
        B.put(dt + 4 * (nk - W.OLD_N), c_at, 'descriptor case 0x%X' % nk)
        B.put(bt + 4 * (nk - W.OLD_N), bk, 'base kind 0x%X' % nk)
        info['descriptors'][nk] = (d_at, d, size, getters)
    # ---- inline kind compares of the bases (none hooked before: asserted by the site's word)
    W.kind_compares(B, img, new, info)
    # ---- the fighters' article lists, kind_expand's descriptor copies +8
    info['lists'] = {}
    for r, lst in recs:
        fdesc = W.fighter_descriptor(img, r)
        alist = img.w(fdesc + 8)
        entries, count = img.w(alist), img.w(alist + 4)
        remap = {b: n for n, b, _a in lst if n not in r.get('new_articles', {})}
        rows = []
        for i in range(count):
            e = [img.w(entries + W.ARTICLE * i + 4 * j) for j in range(4)]
            if (e[0] & 0x3FFFFFFF) in remap:
                e[0] = (e[0] & 0xC0000000) | remap[e[0] & 0x3FFFFFFF]
            rows.append(e)
        special = next((i for i, e in enumerate(rows) if e[0] & 0x80000000), len(rows))
        added = []
        for nk, (_name, mx) in sorted(r.get('new_articles', {}).items()):
            bk = [b for n, b, _a in lst if n == nk][0]
            found = [i for i in range(count) if (img.w(entries + W.ARTICLE * i) & 0x3FFFFFFF) == bk]
            e = [img.w(entries + W.ARTICLE * found[0] + 4 * j) for j in range(4)]
            e[0] = (e[0] & 0xC0000000) | nk
            e[1] = mx
            added.append(e)
        rows[special:special] = added
        at = B.alloc(8 + W.ARTICLE * len(rows), 8)
        B.data(at, struct.pack('>II', at + 8, len(rows)) + b''.join(struct.pack('>4I', *e) for e in rows),
               'article list 0x%X' % K.num(r['kind']))
        own_desc = new_fighter_descriptor(img, K.num(r['kind']), alist)
        assert img.w(own_desc) == K.num(r['kind']) and img.w(own_desc + 8) == alist
        B.put(own_desc + 8, at, 'fighter 0x%X descriptor +8: its article list' % K.num(r['kind']))
        info['lists'][K.num(r['kind'])] = (at, rows, own_desc)
    assert B.pc <= APPEND_LIMIT, 'append space full'
    info['end'] = B.pc
    return B, info, new


def new_fighter_descriptor(img, kind, alist):
    """kind_expand.py's descriptor copy for a new fighter kind (its cave, from kind_expand.CAVE): {kind, its motion info
    (in the cave), its article list (still its base's)}"""
    found = []
    for a in range(K.CAVE, W.CAVE, 8):
        if img.w(a) == kind and img.w(a + 8) == alist and K.CAVE <= img.w(a + 4) < W.CAVE:
            found.append(a)
    assert len(found) == 1, 'descriptor of fighter 0x%X: %s' % (kind, ['0x%08X' % x for x in found])
    return found[0]


def args(B, img_end):
    out = ['grow:0x%08X' % ((B.pc + 0xFFF) & ~0xFFF)] if B.pc > img_end else []
    return out + ['0x%08X=0x%08X' % (a, w) for a, w in sorted(B.words.items())]


def cmd_test(patched, exe, old, new_spec):
    """weapon_expand_test.main with W.build / K.build answering from the patched layout"""
    import kind_expand_incremental as KI
    import weapon_expand_test as T
    B, info, _new = build(exe, old, new_spec)
    img = K.Image(exe)
    pimg = K.Image(patched)
    recs, cap = W.load_weapons(new_spec, img)
    allnew = {}
    for r, lst in recs:
        r['bkind'] = K.kind_index([img.cstr(img.w(K.TABLES['lower'][0] + 4 * k)) for k in range(K.OLD_N)], r['base'])
        r['kind'] = K.num(r['kind'])
        for nk, bk, art in lst:
            allnew[nk] = (bk, r, art)
    descs = W.all_descriptors(img)
    winfo = dict(capacity=cap, new=allnew, descriptor_cases=info['dt'], descriptors={}, getters={}, switches=[],
                 article_lists={}, kind_compares=info.get('kind_compares', []), cave_end=info['end'])
    for nk, (bk, r, art) in allnew.items():
        d = W.descriptor_of(img, bk)
        nxt = [x for x in descs if x > d]
        size = min(W.DESC_COPY_MAX, (nxt[0] - d) if nxt else W.DESC_COPY_MAX)
        c = pimg.w(info['dt'] + 4 * (nk - W.OLD_N))
        d1 = ((pimg.w(c) & 0xFFFF) << 16) + K.sx16(pimg.w(c + 4))
        winfo['descriptors'][nk] = (d1 & 0xFFFFFFFF, d, size)
        g = []
        for off in (0x18, 0x24):
            src = img.w(d + off) if off + 4 <= size else 0
            if src and 0x02000000 <= src < 0x10000000:
                at = pimg.w(d1 + off)
                g.append((off, src, at if at != src else None))
        winfo['getters'][nk] = g
    for a in W.SWITCHES:
        sw = parse_patched_switch(img, a)
        j0 = img.w(sw['x'])
        sw['t'] = (j0 >> 21) & 31
        winfo['switches'].append(sw)
    W.LIMIT = WCAVE_END
    KI._install(exe)
    _kb, kinfo = K.build(new_spec, exe)
    for r in kinfo['kinds']:
        if any(rr['kind'] == r['kind'] for rr, _l in recs):
            winfo['article_lists'][r['kind']] = pimg.w(r['desc'] + 8)
    # the old new kinds' own singletons (on_hit), as weapon_expand.build records them
    st = info['st']
    winfo['singletons'], winfo['vt2'], winfo['nops'] = {}, {}, {}
    for nk, (bk, r, art) in allnew.items():
        o_at = pimg.w(st + 4 * (nk - W.OLD_N))
        if not o_at:
            continue
        v_at, v2_at = pimg.w(o_at), pimg.w(o_at + 4)
        _at, vt, vt2 = W.singleton_of(img, bk)
        size = W.vtable_size(img, vt)
        fn = pimg.w(v_at + W.HIT_METHOD)
        winfo['singletons'][nk] = (o_at, v_at, fn, r['on_hit'][nk])
        nops = r.get('nop', {}).get(nk, [])
        nop_at = pimg.w(v_at + nops[0]) if nops else 0
        winfo['nops'][nk] = (nops, nop_at)
        moved = [(off, pimg.w(v_at + off)) for off in range(4, size, 8)
                 if off != W.HIT_METHOD and off not in nops and pimg.w(v_at + off) != img.w(vt + off)]
        winfo['vt2'][nk] = (v2_at, W.vtable_size(img, vt2) if vt2 else 0, r.get('nop2', {}).get(nk, []), moved)
    W.build = lambda spec, rpx: (B, winfo)
    K.build = lambda spec, rpx: (_kb, kinfo)
    sys.argv = ['weapon_expand_test.py', patched, exe, new_spec]
    T.main()


def new_fighter_descriptor_any(img, kind):
    for a in range(K.CAVE, W.CAVE, 8):
        if img.w(a) == kind and K.CAVE <= img.w(a + 4) < W.CAVE:
            return a
    raise AssertionError('no descriptor of 0x%X' % kind)


def main():
    if sys.argv[1:2] == ['test']:
        cmd_test(*sys.argv[2:6])
        return
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('exe')
    ap.add_argument('old')
    ap.add_argument('new')
    ap.add_argument('out')
    ap.add_argument('--info', action='store_true')
    a = ap.parse_args()
    B, info, new = build(a.exe, a.old, a.new)
    img = K.Image(a.exe)
    text_end = img.text_end() if hasattr(img, 'text_end') else W.LIMIT
    open(a.out, 'w').write(' '.join(args(B, text_end)))
    print('weapon_expand_append: %d new weapon kind(s) from 0x%08X to 0x%08X, %d words -> %s' % (
        len(new), info['start'], info['end'], len(B.words), a.out))
    print('  tables: %s; descriptor cases 0x%08X, singleton cases 0x%08X, base kinds 0x%08X, module rows 0x%08X' % (
        ', '.join('%s 0x%08X' % kv for kv in info['tables'].items()), info['dt'], info['st'], info['bt'], info['rt']))
    for nk, (d_at, d, size, g) in sorted(info['descriptors'].items()):
        bk, r, art = new[nk]
        print('  0x%X %s (copy of 0x%X, owner %s): descriptor 0x%08X (0x%X bytes of 0x%08X); getters %s' % (
            nk, art, bk, r['name'], d_at, size, d, ', '.join('+0x%X %s' % (o, '0x%08X' % x if x else "base's")
                                                              for o, _s, x in g)))
    for at, k, stb, cs in info.get('kind_compares', []):
        print('  kind compare 0x%08X (0x%X) -> 0x%08X: also %s' % (at, k, stb, ', '.join('0x%X' % c for c in cs)))
    for fk, (at, rows, d) in info['lists'].items():
        print('  fighter 0x%X: article list 0x%08X (%s), its descriptor 0x%08X +8' % (
            fk, at, ', '.join('0x%X' % (e[0] & 0x3FFFFFFF) for e in rows), d))


if __name__ == '__main__':
    main()
