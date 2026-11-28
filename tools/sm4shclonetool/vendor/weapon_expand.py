"""New weapon (article) kinds for new fighter kinds: copies of the base fighter's articles owned by the new fighter
(their files load from its folder): the weapon tables, the 13 weapon-kind switches, descriptors, the module
rows, kind compares, and the new fighter's article list.

Adapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; the tool
sets the code addresses itself, see its README "The executable")."""
import argparse
import json
import os
import struct
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kind_expand as K
from ppcasm import Asm, ha
RPX = K.RPX
SPEC = K.SPEC
CAVE = 79331328
LIMIT = 79396864
OLD_N = 389
DEFAULT_CAPACITY = 448
FIGHTER_VL = 4380
NAME_TABLES = (('root', 272730588), ('owner', 272732144), ('name', 272733700), ('folder', 272735256))
STATIC_TABLES = (('u32', 270049748, 4, 0), ('u8', 270051304, 1, 6), ('u16', 270051696, 2, 0))
BOUND = 52487596
DESC_SWITCH = 52484404
SINGLETON_SWITCH = 52497456
HIT_METHOD = 172
HIT_BITS = 19
SWITCHES = (52484404, 52497456, 45502892, 45517132, 45529000, 45546820, 45562532, 45570696, 45580204, 45589724, 45601656, 45616372, 45628760)
INTO_LAST = ((45628292, 'r5'), (45628532, 'r5'))
MODULE_ROW = 45921728
MODULE_TABLE = 271869096
DESC_COPY_MAX = 320
MINFO_SIZE = 32
ARTICLE = 16

def load_weapons(path, img):
    raw = json.load(open(path))
    cap = K.num(raw.get('weapon_capacity', DEFAULT_CAPACITY))
    _fcap, kinds = K.load_spec(path) if raw.get('kinds') else (None, [])
    rawk = {K.num(r['kind']): r for r in raw.get('kinds', [])}
    owner = [img.cstr(img.w(272732144 + 4 * k)) for k in range(OLD_N)]
    name = [img.cstr(img.w(272733700 + 4 * k)) for k in range(OLD_N)]
    if raw.get('owners'):
        fnames = [img.cstr(img.w(K.TABLES['lower'][0] + 4 * k)) for k in range(K.OLD_N)]
        for o in raw['owners']:
            k = K.kind_index(fnames, o['name'])
            assert k not in rawk, 'owner %s twice' % o['name']
            assert all((isinstance(v, dict) for v in (o.get('weapons') or {}).values())), 'a vanilla owner\'s weapons are brand-new articles ({"kind", "base", "max"})'
            kinds.append({'kind': k, 'name': o['name'], 'base': o['name'], 'desc_from': o['name'], 'vanilla_owner': True})
            rawk[k] = o
    out, nxt = ([], OLD_N)
    for r in kinds:
        ws = rawk[r['kind']].get('weapons') or {}
        lst = []
        r['new_articles'] = {}

        def kind_of(v):
            return K.num(v['kind'] if isinstance(v, dict) else v)
        for art, nk in sorted(ws.items(), key=lambda kv: kind_of(kv[1])):
            spec = nk if isinstance(nk, dict) else None
            nk = kind_of(nk)
            if spec:
                r['new_articles'][nk] = (art, int(spec.get('max', 1)))
                if 'motions' in spec:
                    r.setdefault('motions', {})[nk] = int(spec['motions'])
                if 'modules' in spec:
                    r.setdefault('modules', {})[nk] = (spec['modules']['from'], [int(s) for s in spec['modules']['slots']])
                if 'spawn_from' in spec:
                    r.setdefault('spawn_from', {})[nk] = spec['spawn_from']
                if 'flags_set' in spec:
                    r.setdefault('flags_set', {})[nk] = K.num(spec['flags_set'])
                if 'on_hit' in spec:
                    r.setdefault('on_hit', {})[nk] = int(spec['on_hit'])
                    r.setdefault('on_hit_bits', {})[nk] = K.num(spec.get('on_hit_bits', HIT_BITS))
                    r.setdefault('nop', {})[nk] = [K.num(x) for x in spec.get('nop', [])]
                    r.setdefault('nop2', {})[nk] = [K.num(x) for x in spec.get('nop2', [])]
                art_base = spec['base']
            else:
                art_base = art
            src_owner, sep, src_name = art_base.partition('/')
            if not sep:
                src_owner, src_name = (r['base'], art_base)
            elif spec:
                r.setdefault('src_owner', {})[nk] = src_owner
            base = [k for k in range(OLD_N) if owner[k] == src_owner and name[k] == src_name]
            assert len(base) == 1, '%s has no article %s' % (src_owner, src_name)
            lst.append((nk, base[0], art))
        for key in ('modules', 'spawn_from'):
            for nk, v in list(r.get(key, {}).items()):
                nm = v[0] if key == 'modules' else v
                kk = [k for k in range(OLD_N) if owner[k] == r['base'] and name[k] == nm]
                assert len(kk) == 1, '%s has no article %s' % (r['base'], nm)
                r[key][nk] = (kk[0], v[1]) if key == 'modules' else kk[0]
        if lst:
            out.append((r, lst))
    allk = sorted((nk for _r, lst in out for nk, _b, _a in lst))
    assert allk == list(range(OLD_N, OLD_N + len(allk))), 'weapon kinds must be consecutive from 0x185: %s' % ', '.join(('0x%X' % k for k in allk))
    nxt = OLD_N + len(allk)
    assert nxt <= cap, 'weapon capacity 0x%X too small' % cap
    assert cap <= 32767
    return (out, cap)

class Build(K.Build):

    def __init__(self, img):
        super().__init__(img)
        self.pc = CAVE

    def put(self, addr, word, what, orig=None):
        assert addr not in self.words, 'patched twice: 0x%08X' % addr
        if orig is not None:
            want = K.one(addr, orig) if isinstance(orig, str) else orig
            got = self.img.w(addr)
            assert got == want, '0x%08X is 0x%08X, expected 0x%08X (%s)' % (addr, got, want, orig)
        self.words[addr] = word & 4294967295
        self.what[addr] = what
        if not CAVE <= addr < LIMIT:
            self.inplace.append(addr)

    def alloc(self, n, align=4):
        self.pc = self.pc + align - 1 & ~(align - 1)
        a = self.pc
        self.pc += n
        assert self.pc <= LIMIT, 'cave full'
        return a

def rela(img):
    from rpx_patch import section_data
    out = {}
    for s in img.secs:
        if s[1] != 4:
            continue
        sym = section_data(img.d, img.secs[s[6]])
        data = section_data(img.d, s)
        for o in range(0, len(data), 12):
            off, info, add = struct.unpack('>IIi', data[o:o + 12])
            typ = info & 255
            if typ in (4, 6):
                val = struct.unpack('>I', sym[16 * (info >> 8) + 4:16 * (info >> 8) + 8])[0]
                out[off & ~3] = (typ, val + add & 4294967295)
    return out

def parse_switch(img, a):
    w = img.w(a)
    assert w >> 26 == 10 and w & 65535 == 388, 'no cmplwi 0x184 at 0x%08X' % a
    k = w >> 16 & 31
    b = a + 4
    if img.w(b) >> 26 != 16:
        b += 4
    assert img.w(b) >> 26 == 16, 'no bgt after 0x%08X' % a
    default = K.branch_target(b, img.w(b))
    x = b + 4
    words = [img.w(x + 4 * i) for i in range(6)]
    if words[0] >> 26 == 15 and words[0] >> 21 & 31 == 0:
        hi = words[0] & 65535
        assert words[1] == K.one(x + 4, 'slwi r%d, r%d, 2' % (k, k))
        assert words[2] >> 26 == 12
        lo = K.sx16(words[2])
        assert words[3] == K.one(x + 12, 'add r0, r%d, r0' % k) and words[4] == K.one(x + 16, 'mtctr r0')
        assert words[5] == 1317012512
        t, form, bctr = (0, 'r0', x + 20)
    else:
        assert words[0] == K.one(x, 'slwi r%d, r%d, 2' % (k, k))
        t = words[1] >> 21 & 31
        assert words[1] >> 26 == 15 and words[1] >> 16 & 31 == k
        hi = words[1] & 65535
        assert words[2] >> 26 == 14 and words[2] >> 21 & 31 == t
        lo = K.sx16(words[2])
        assert words[3] == K.one(x + 12, 'mtctr r%d' % t) and words[4] == 1317012512
        form, bctr = ('addis', x + 16)
    table = (hi << 16) + lo & 4294967295
    assert table == bctr + 4, 'table 0x%08X not after the bctr 0x%08X' % (table, bctr)
    return dict(at=a, k=k, t=t, bgt=b, default=default, x=x, form=form, table=table, bctr=bctr)

def case_target(img, table, kind):
    e = table + 4 * kind
    while img.w(e) >> 26 == 18 and (not img.w(e) & 3):
        e = K.branch_target(e, img.w(e))
    return e

def descriptor_of(img, kind):
    if not hasattr(img, '_desc_sw'):
        img._desc_sw = parse_switch(img, DESC_SWITCH)
    c = case_target(img, img._desc_sw['table'], kind)
    w1, w2, w3 = (img.w(c), img.w(c + 4), img.w(c + 8))
    assert w1 >> 26 == 15 and w1 >> 21 & 31 == 3 and (w2 >> 26 == 14) and (w3 == 1317011488), 'descriptor case 0x%08X' % c
    return ((w1 & 65535) << 16) + K.sx16(w2) & 4294967295

def all_descriptors(img):
    out = set()
    for k in range(OLD_N):
        try:
            out.add(descriptor_of(img, k))
        except AssertionError:
            pass
    return sorted(out)

def copy_getter(img, src, base_fighter, new_vl_off, clamp=None):
    words, a = ([], src)
    found = 0
    while True:
        w = img.w(a)
        if w >> 26 == 32 and w & 65535 == FIGHTER_VL + 4 * base_fighter:
            w = w & 4294901760 | new_vl_off
            found += 1
        words.append(w)
        if w == 1317011488:
            break
        assert w >> 26 not in (16, 18, 19) or w == 1317011488, 'branch in a getter at 0x%08X' % a
        a += 4
        assert len(words) < 32
    if found != 1:
        return None
    if CUSTOM_CLAMP if clamp is None else clamp:
        words = clamp_custom(words, new_vl_off)
    return words
CUSTOM_CLAMP = True
VECTOR_COUNT = -4
CLAMP_SIGNATURE = 2080659520

def clamp_custom(words, slot_off):

    def is_slot(w):
        return w >> 26 == 32 and w & 65535 == slot_off
    i_slot = next((i for i, w in enumerate(words) if is_slot(w)))
    rv = words[i_slot] >> 21 & 31
    data = [w for w in words[i_slot + 1:] if w >> 26 == 32 and w >> 16 & 31 == rv]
    if not data:
        return words

    def reads_r4(w):
        op = w >> 26
        return op == 7 and w >> 16 & 31 == 4 or (op == 21 and w >> 21 & 31 == 4)
    if not any((reads_r4(w) for w in words)):
        return words
    off = data[0] & 65535
    assert off >= 4 and (not any((w >> 21 & 31 in (4, 11) for w in words if w >> 26 not in (36, 38) and (not reads_r4(w)) and (w != 1317011488)))), 'getter writes r4 / r11'
    from ppcasm import Asm
    a = Asm(0)
    a.asm('\n        lwz r11, %d(r%d)\n        cmplw r4, r11\n        blt ok\n        clrlwi r4, r4, 30\n        cmplw r4, r11\n        blt ok\n        li r4, 0\nok:\n' % (off + VECTOR_COUNT, rv))
    clamp = a.words()
    early = [w for w in words[:i_slot] if reads_r4(w)]
    head = [w for w in words[:i_slot] if not reads_r4(w)]
    return head + [words[i_slot]] + clamp + early + words[i_slot + 1:]

def singleton_of(img, kind):
    if not hasattr(img, '_single_sw'):
        img._single_sw = parse_switch(img, SINGLETON_SWITCH)
    c = case_target(img, img._single_sw['table'], kind)
    w1, w2, w3 = (img.w(c), img.w(c + 4), img.w(c + 8))
    assert w1 >> 26 == 15 and w1 >> 21 & 31 == 3 and (w2 >> 26 == 14) and (w3 == 1317011488), 'singleton case 0x%08X' % c
    at = ((w1 & 65535) << 16) + K.sx16(w2) & 4294967295
    regs, stores, a = ({}, {}, c + 12)
    while img.w(a) != 1317011488:
        w = img.w(a)
        op, d, ra, imm = (w >> 26, w >> 21 & 31, w >> 16 & 31, K.sx16(w))
        if op == 15 and ra == 0:
            regs[d] = (w & 65535) << 16
        elif op in (12, 14) and ra in regs:
            regs[d] = regs[ra] + imm & 4294967295
        elif op == 36 and ra in regs and (d in regs):
            stores[regs[ra] + imm & 4294967295] = regs[d]
        elif op not in (48, 52):
            regs.pop(d, None)
        a += 4
        assert a - c < 128, 'no initializer after 0x%08X' % c
    assert at in stores, 'singleton 0x%08X not initialized after 0x%08X' % (at, c)
    return (at, stores[at], stores.get(at + 4))

def sub_ref_copy(img, fn, old, new):
    if not 33554432 <= fn < 268435456:
        return None
    ws = []
    for i in range(16):
        w = img.w(fn + 4 * i)
        ws.append(w)
        if w == 1317011488:
            break
        if w >> 26 in (16, 18, 19):
            return None
    else:
        return None
    for i, w in enumerate(ws):
        if w >> 26 == 15 and w >> 16 & 31 == 0:
            d = w >> 21 & 31
            for j in range(i + 1, len(ws)):
                w2 = ws[j]
                if w2 >> 26 in (12, 14) and w2 >> 16 & 31 == d:
                    if ((w & 65535) << 16) + K.sx16(w2) & 4294967295 == old:
                        ws[i] = w & 4294901760 | ha(new)
                        ws[j] = w2 & 4294901760 | new & 65535
                        return ws
                    break
    return None

def vtable_size(img, vt):
    n = 8
    while img.w(vt + n) == 0 and 33554432 <= img.w(vt + n + 4) < 268435456:
        n += 8
    return n

def article_layout(img, recs):
    out, at = ({}, CAVE)
    for r, lst in recs:
        fdesc = fighter_descriptor(img, r)
        alist = img.w(fdesc + 8)
        entries, count = (img.w(alist), img.w(alist + 4))
        remap = {b: n for n, b, _a in lst if n not in r.get('new_articles', {})}
        rows = []
        for i in range(count):
            e = [img.w(entries + ARTICLE * i + 4 * j) for j in range(4)]
            kind = e[0] & 1073741823
            if kind in remap:
                e[0] = e[0] & 3221225472 | remap[kind]
            rows.append(e)
        special = next((i for i, e in enumerate(rows) if e[0] & 2147483648), len(rows))
        added = []
        for nk, (_name, mx) in sorted(r.get('new_articles', {}).items()):
            bk = [b for n, b, _a in lst if n == nk][0]
            sents, scount = (entries, count)
            if nk in r.get('src_owner', {}):
                sl = img.w(fighter_descriptor(img, {'desc_from': r['src_owner'][nk]}) + 8)
                sents, scount = (img.w(sl), img.w(sl + 4))
            found = [i for i in range(scount) if img.w(sents + ARTICLE * i) & 1073741823 == bk]
            assert found, 'the base fighter has no article of kind 0x%X' % bk
            i = found[0]
            e = [img.w(sents + ARTICLE * i + 4 * j) for j in range(4)]
            e[0] = e[0] & 3221225472 | nk
            e[1] = mx
            sk = r.get('spawn_from', {}).get(nk)
            if sk is not None:
                si = [i for i in range(count) if img.w(entries + ARTICLE * i) & 1073741823 == sk]
                assert si, 'the base fighter has no article of kind 0x%X' % sk
                e[2] = img.w(entries + ARTICLE * si[0] + 8)
                e[3] = img.w(entries + ARTICLE * si[0] + 12)
            added.append(e)
        rows[special:special] = added
        out[r['kind']] = (at, rows)
        at += 8 + ARTICLE * len(rows)
    return (out, at)

def fighter_descriptor(img, r):
    names = [img.cstr(img.w(K.TABLES['lower'][0] + 4 * k)) for k in range(K.OLD_N)]
    dk = K.kind_index(names, r['desc_from'])
    sw = K.switch_targets(img, 'descriptor')
    dsrc = sw[0][dk]
    g = K.branch_target(dsrc, img.w(dsrc))
    return ((img.w(g) & 65535) << 16) + K.sx16(img.w(g + 4))

def article_lists(spec_path=SPEC, rpx=RPX):
    img = K.Image(rpx)
    recs, _cap = load_weapons(spec_path, img)
    lay, _end = article_layout(img, recs)
    return {k: a for k, (a, _rows) in lay.items()}

def build(spec_path=SPEC, rpx=RPX):
    img = K.Image(rpx)
    B = Build(img)
    recs, cap = load_weapons(spec_path, img)
    fnames = [img.cstr(img.w(K.TABLES['lower'][0] + 4 * k)) for k in range(K.OLD_N)]
    fcap = K.load_spec(spec_path)[0] if json.load(open(spec_path)).get('kinds') else K.DEFAULT_CAPACITY
    vl_new = K.mgr_layout(fcap)[0]['vl'][1]
    new = {}
    for r, lst in recs:
        r['bkind'] = K.kind_index(fnames, r['base'])
        for nk, bk, art in lst:
            new[nk] = (bk, r, art)
    info = {'capacity': cap, 'new': new}
    lay, end = article_layout(img, recs)
    B.pc = end
    for fk, (at, rows) in lay.items():
        blob = struct.pack('>II', at + 8, len(rows)) + b''.join((struct.pack('>4I', *e) for e in rows))
        B.data(at, blob, 'article list 0x%X' % fk)
    info['article_lists'] = {k: a for k, (a, _r) in lay.items()}
    B.extra_relocs = []
    for r, _lst in recs:
        if r.get('vanilla_owner'):
            fdesc = fighter_descriptor(img, r)
            old = img.w(fdesc + 8)
            B.put(fdesc + 8, lay[r['kind']][0], 'article list of %s' % r['name'], old)
            if fdesc + 8 in img.relocs():
                assert old + 4 not in img.relocs()
                B.inplace.remove(fdesc + 8)
                B.extra_relocs.append((fdesc + 8, old + 4))
    sblob, sptr = (bytearray(), {})
    for r, _lst in recs:
        sptr[r['name']] = len(sblob)
        sblob += r['name'].encode('ascii') + b'\x00'
        for _nk, (aname, _mx) in sorted(r.get('new_articles', {}).items()):
            if aname not in sptr:
                sptr[aname] = len(sblob)
                sblob += aname.encode('ascii') + b'\x00'
    s_at = B.alloc(len(sblob) + -len(sblob) % 4)
    B.data(s_at, sblob, 'strings')
    sptr = {s: s_at + o for s, o in sptr.items()}
    tables = {}
    for nm, addr in NAME_TABLES:
        at = B.alloc(4 * cap)
        vals = []
        for k in range(cap):
            if k < OLD_N:
                vals.append(img.w(addr + 4 * k))
            elif k in new:
                bk, r, _a = new[k]
                own_name = r.get('new_articles', {}).get(k)
                if nm == 'owner':
                    vals.append(sptr[r['name']])
                elif own_name and nm in ('name', 'folder'):
                    vals.append(sptr[own_name[0]])
                else:
                    vals.append(img.w(addr + 4 * bk))
            else:
                vals.append(img.w(addr))
        B.data(at, b''.join((struct.pack('>I', v) for v in vals)), 'table ' + nm)
        tables[nm] = (addr, at)
    for nm, addr, es, invalid in STATIC_TABLES:
        size = es * cap
        at = B.alloc(size + -size % 4)
        blob = bytearray()
        for k in range(cap):
            src = k if k < OLD_N else new[k][0] if k in new else None
            v = invalid if src is None else {1: img.b, 2: img.h, 4: img.w}[es](addr + es * src)
            if nm == 'u16' and k in new:
                v |= new[k][1].get('flags_set', {}).get(k, 0)
            blob += v.to_bytes(es, 'big')
        B.data(at, blob, 'table ' + nm)
        tables[nm] = (addr, at)
    info['tables'] = tables
    rel = rela(img)
    starts = {old: new_ for old, new_ in tables.values()}
    sites = []
    for a, (typ, tgt) in sorted(rel.items()):
        if tgt in starts:
            v = starts[tgt]
            w = img.w(a)
            assert w & 65535 == (ha(tgt) if typ == 6 else tgt & 65535), 'relocation at 0x%08X' % a
            B.put(a, w & 4294901760 | (ha(v) if typ == 6 else v) & 65535, ('table site', typ, tgt), w)
            sites.append(a)
    info['table_sites'] = sites
    assert len(sites) == 54, len(sites)
    B.asm(BOUND, 'addic r0, r4, %d' % -cap, 'addic r0, r4, -0x185')
    descs = all_descriptors(img)
    dcase = {}
    getters = {}
    for nk in sorted(new):
        bk, r, art = new[nk]
        d = descriptor_of(img, bk)
        nxt = [x for x in descs if x > d]
        size = min(DESC_COPY_MAX, nxt[0] - d if nxt else DESC_COPY_MAX)
        assert size >= 40, 'descriptor of 0x%X too small' % bk
        blob = bytearray(img.blob(d, size))
        if struct.unpack_from('>I', blob, 28)[0] == bk:
            struct.pack_into('>I', blob, 28, nk)
        mi = img.w(d + 8)
        if mi:
            ents, cnt = (img.w(mi), img.w(mi + 4))
            n = r.get('motions', {}).get(nk, cnt)
            assert cnt and n >= cnt or n == cnt, 'weapon 0x%X: %d motions (the base has %d)' % (nk, n, cnt)
            m_at = B.alloc(MINFO_SIZE, 8)
            e_at = B.alloc(8 * n, 8) if n else 0
            mib = bytearray(img.blob(mi, MINFO_SIZE))
            struct.pack_into('>II', mib, 0, e_at if n else ents, n)
            B.data(m_at, mib, 'weapon 0x%X motion info' % nk)
            if n:
                blob_m = img.blob(ents, 8 * cnt)
                B.data(e_at, blob_m + blob_m[-8:] * (n - cnt), 'weapon 0x%X motions' % nk)
            struct.pack_into('>I', blob, 8, m_at)
        sub = img.w(d + 20)
        if sub:
            ents, cnt = (img.w(sub), img.w(sub + 4))
            remap = {b: n for n, (b, rr, _a) in new.items() if rr is r and n not in r.get('new_articles', {})}
            rows = []
            for i in range(cnt):
                e = [img.w(ents + ARTICLE * i + 4 * j) for j in range(4)]
                kk = e[0] & 1073741823
                if kk in remap:
                    e[0] = e[0] & 3221225472 | remap[kk]
                rows.append(e)
            s_at2 = B.alloc(8 + ARTICLE * cnt)
            B.data(s_at2, struct.pack('>II', s_at2 + 8, cnt) + b''.join((struct.pack('>4I', *e) for e in rows)), 'weapon 0x%X sub-articles' % nk)
            struct.pack_into('>I', blob, 20, s_at2)
        own = vl_new + 4 * r['kind']
        for off in (24, 36) if not r.get('vanilla_owner') else ():
            src = struct.unpack_from('>I', blob, off)[0] if off + 4 <= size else 0
            if not src or not 33554432 <= src < 268435456:
                continue
            ws = copy_getter(img, src, r['bkind'], own)
            if ws is None:
                getters.setdefault(nk, []).append((off, src, None))
                continue
            g_at = B.alloc(4 * len(ws))
            for i, w in enumerate(ws):
                B.put(g_at + 4 * i, w, ('getter copy', src, i))
            struct.pack_into('>I', blob, off, g_at)
            getters.setdefault(nk, []).append((off, src, g_at))
        d_at = B.alloc(len(blob), 8)
        B.data(d_at, blob, 'weapon 0x%X descriptor (copy of 0x%X)' % (nk, bk))
        c_at = B.alloc(12)
        B.code(c_at, 'lis r3, 0x%X\naddi r3, r3, %d\nblr' % (ha(d_at), K.slo(d_at)))
        dcase[nk] = c_at
        new[nk] = (bk, r, art)
        info.setdefault('descriptors', {})[nk] = (d_at, d, size)
    info['getters'] = getters
    bt = B.alloc(4 * (cap - OLD_N))
    B.data(bt, b''.join((struct.pack('>I', new[k][0] if k in new else 65535) for k in range(OLD_N, cap))), 'base kinds')
    info['base_table'] = bt
    dt = B.alloc(4 * (cap - OLD_N))
    B.data(dt, b''.join((struct.pack('>I', dcase.get(k, 0)) for k in range(OLD_N, cap))), 'descriptor cases')
    info['descriptor_cases'] = dt
    scase = {}
    for nk in sorted(new):
        bk, r, _art = new[nk]
        status = r.get('on_hit', {}).get(nk)
        if status is None:
            continue
        _at, vt, vt2 = singleton_of(img, bk)
        size = vtable_size(img, vt)
        old_hit = img.w(vt + HIT_METHOD)
        assert size > HIT_METHOD and 33554432 <= old_hit < 268435456
        fn = B.alloc(4 * 32)
        hit = B.code(fn, 'andi. r0, r5, %d\nbeq base\nmflr r0\nstwu r1, -0x18(r1)\nstw r0, 0x1C(r1)\nstw r31, 0x14(r1)\nlwz r12, 0x28(r4)\nlwz r31, 0x20(r12)\nlwz r12, 0(r31)\nlwz r12, 0x8C(r12)\nmtctr r12\nmr r3, r31\nbctrl\ncmpwi r3, %d\nbge done\nlwz r12, 0(r31)\nlwz r12, 0x2C(r12)\nmtctr r12\nmr r3, r31\nli r4, %d\nbctrl\ndone:\nlwz r0, 0x1C(r1)\nlwz r31, 0x14(r1)\nmtlr r0\naddi r1, r1, 0x18\nli r3, 0\nblr\nbase:\nb 0x%X' % (r.get('on_hit_bits', {}).get(nk, HIT_BITS), status, status, old_hit))
        assert len(hit.words()) <= 32
        nops = r.get('nop', {}).get(nk, [])
        nops2 = r.get('nop2', {}).get(nk, [])
        nop_at = B.alloc(4)
        B.code(nop_at, 'blr')
        o_at = B.alloc(8, 8)
        v_at = B.alloc(size, 8)
        size2 = vtable_size(img, vt2) if vt2 else 0
        v2_at = B.alloc(size2, 8) if vt2 else 0
        vb = bytearray(img.blob(vt, size))
        struct.pack_into('>I', vb, HIT_METHOD, fn)
        for off in nops:
            assert off % 8 == 4 and off < size and (off != HIT_METHOD), 'vtable slot 0x%X' % off
            struct.pack_into('>I', vb, off, nop_at)
        moved = []
        for off in range(4, size, 8):
            ws = sub_ref_copy(img, img.w(vt + off), _at + 4, o_at + 4)
            if ws is None:
                continue
            m_at = B.alloc(4 * len(ws))
            for i, w in enumerate(ws):
                B.put(m_at + 4 * i, w, ('singleton +4 method copy', off, i))
            struct.pack_into('>I', vb, off, m_at)
            moved.append((off, m_at))
        assert moved or not vt2, 'no method of 0x%08X stores the singleton +4: vtable 2 not reachable' % vt
        B.data(v_at, vb, 'weapon 0x%X vtable (copy of 0x%08X)' % (nk, vt))
        assert vt2 or not nops2, 'weapon 0x%X: nop2 but its base has no vtable 2' % nk
        if vt2:
            vb2 = bytearray(img.blob(vt2, size2))
            for off in nops2:
                assert off % 8 == 4 and off < size2, 'vtable 2 slot 0x%X' % off
                struct.pack_into('>I', vb2, off, nop_at)
            B.data(v2_at, vb2, 'weapon 0x%X vtable 2 (copy of 0x%08X)' % (nk, vt2))
        B.data(o_at, struct.pack('>II', v_at, v2_at), 'weapon 0x%X singleton' % nk)
        scase[nk] = o_at
        info.setdefault('singletons', {})[nk] = (o_at, v_at, fn, status)
        info.setdefault('nops', {})[nk] = (nops, nop_at)
        info.setdefault('vt2', {})[nk] = (v2_at, size2, nops2, moved)
    st = B.alloc(4 * (cap - OLD_N))
    B.data(st, b''.join((struct.pack('>I', scase.get(k, 0)) for k in range(OLD_N, cap))), 'singleton cases')
    info['switches'] = []
    for a in SWITCHES:
        sw = parse_switch(img, a)
        k, t = (sw['k'], sw['t'])
        tk = 'r%d' % t
        if t == 0:
            hi_lo = 'lis r0, 0x%X\naddic r0, r0, %d'
        else:
            hi_lo = 'lis ' + tk + ', 0x%X\naddi ' + tk + ', ' + tk + ', %d'
        stub = B.alloc(4 * 32)
        orig = 'slwi r{k}, r{k}, 2\n' + hi_lo % (ha(sw['table']), K.slo(sw['table'])) + '\n' + ('add r0, r{k}, r0' if t == 0 else 'add {t}, {t}, r{k}') + '\nmtctr {t}\nbctr'
        dflt = hi_lo % (ha(sw['default']), K.slo(sw['default'])) + '\nmtctr {t}\nbctr'
        if a == DESC_SWITCH:
            newpath = 'addi r{k}, r{k}, -0x185\nslwi r{k}, r{k}, 2\n' + hi_lo % (ha(dt), K.slo(dt)) + '\n' + ('lwzx r0, r{k}, r0' if t == 0 else 'lwzx {t}, {t}, r{k}') + '\n' + ('cmpwi r0, 0' if t == 0 else 'cmpwi {t}, 0') + '\nbeq dflt\nmtctr {t}\nbctr'
        else:
            own = ''
            if a == SINGLETON_SWITCH:
                assert k != 12 and t != 12
                own = 'lis r12, 0x%X\naddi r12, r12, %d\nlwzx r12, r12, r{k}\ncmpwi r12, 0\nbeq bas\nmr r3, r12\nblr\nbas:\n' % (ha(st), K.slo(st))
            newpath = 'addi r{k}, r{k}, -0x185\nslwi r{k}, r{k}, 2\n' + own + hi_lo % (ha(bt), K.slo(bt)) + '\n' + ('lwzx r{k}, r{k}, r0' if t == 0 else 'lwzx r{k}, {t}, r{k}') + '\ncmplwi r{k}, 0x184\nble orig\nb dflt'
        src = 'cmplwi r{k}, 0x184\nbgt new\norig:\n' + orig + '\nnew:\n' + newpath + '\ndflt:\n' + dflt
        assert len(B.code(stub, src.format(k=k, t=tk)).words()) <= 32
        B.asm(a, 'cmplwi r%d, %d' % (k, cap - 1), 'cmplwi r%d, 0x184' % k)
        x = sw['x']
        if t == 0:
            jump = ['lis r0, 0x%X' % ha(stub), 'addic r0, r0, %d' % K.slo(stub), 'mtctr r0', 'bctr']
        else:
            jump = ['lis %s, 0x%X' % (tk, ha(stub)), 'addi %s, %s, %d' % (tk, tk, K.slo(stub)), 'mtctr ' + tk, 'bctr']
        for i, line in enumerate(jump):
            B.put(x + 4 * i, K.one(x + 4 * i, line), line, img.w(x + 4 * i))
        info['switches'].append(dict(sw, stub=stub))
    for a, reg in INTO_LAST:
        B.asm(a, 'cmplwi %s, %d' % (reg, cap - 1), 'cmplwi %s, 0x184' % reg)
    rows, rt_words = ({}, [])
    for k in range(OLD_N, cap):
        if k in new and k in new[k][1].get('modules', {}):
            src, slots = new[k][1]['modules'][k]
            base_row = [img.w(MODULE_TABLE + 112 * new[k][0] + 4 * j) for j in range(28)]
            for s in slots:
                base_row[s] = img.w(MODULE_TABLE + 112 * src + 4 * s)
            at = B.alloc(112, 8)
            B.data(at, b''.join((struct.pack('>I', w) for w in base_row)), 'module row 0x%X' % k)
            rows[k] = (at, base_row)
            rt_words.append(at - MODULE_TABLE & 4294967295)
        else:
            rt_words.append(0)
    rt = B.alloc(4 * len(rt_words))
    B.data(rt, b''.join((struct.pack('>I', w) for w in rt_words)), 'own module rows')
    info['module_rows'] = rows
    mr = B.alloc(4 * 24)
    B.code(mr, 'cmplwi r30, 0x184\nble old\naddi r8, r30, -0x185\ncmplwi r8, %d\nbge old\nslwi r8, r8, 2\nlis r10, 0x%X\naddi r10, r10, %d\nlwzx r10, r10, r8\ncmpwi r10, 0\nbeq base\nmr r8, r10\nblr\nbase:\nlis r10, 0x%X\naddi r10, r10, %d\nlwzx r8, r10, r8\ncmplwi r8, 0x184\nbgt old\nmr r30, r8\nold:\nmulli r8, r30, 0x70\nblr' % (cap - OLD_N, ha(rt), K.slo(rt), ha(bt), K.slo(bt)))
    assert B.pc - mr <= 4 * 24
    B.asm(MODULE_ROW, 'bl 0x%X' % mr, 'mulli r8, r30, 0x70')
    info['module_row'] = mr
    kind_compares(B, img, new, info)
    info['cave_end'] = B.pc
    return (B, info)
OBJ_CATEGORY, OBJ_KIND = (46069236, 46069252)
KIND_COMPARE_LIMIT = 67108864

def _bl_target(a, w):
    if w >> 26 != 18 or w & 3 != 1:
        return None
    off = w & 67108860
    if off & 33554432:
        off -= 67108864
    return a + off

def kind_compare_sites(img, bases):
    out = []
    for base, data in img.mem:
        if base >= KIND_COMPARE_LIMIT:
            continue
        n = len(data) // 4
        W = struct.unpack('>%dI' % n, data[:4 * n])
        for i in range(n):
            if _bl_target(base + 4 * i, W[i]) != OBJ_KIND:
                continue
            for j in range(1, 4):
                if i + j + 1 >= n:
                    break
                w = W[i + j]
                if w >> 26 in (10, 11) and w >> 21 & 7 == 0 and (w >> 16 & 31 == 3):
                    k = w & 65535
                    nxt = W[i + j + 1]
                    if k in bases and nxt >> 26 == 16 and (nxt >> 18 & 7 == 0) and any((_bl_target(base + 4 * x, W[x]) == OBJ_CATEGORY and any((W[y] >> 26 in (10, 11) and W[y] >> 16 & 31 == 3 and (W[y] & 65535 == 1) for y in range(x + 1, min(x + 4, i)))) for x in range(max(0, i - 12), i))):
                        out.append((base + 4 * (i + j), w, k))
                    break
    return out

def kind_compares(B, img, new, info):
    copies = {}
    for nk, (bk, _r, _art) in sorted(new.items()):
        copies.setdefault(bk, []).append(nk)
    info['kind_compares'] = []
    for at, w, k in kind_compare_sites(img, set(copies)):
        op = 'cmplwi' if w >> 26 == 10 else 'cmpwi'
        lines = ['%s r3, 0x%X' % (op, k)]
        for c in copies[k]:
            lines += ['beq.far 0x%X' % (at + 4), '%s r3, 0x%X' % (op, c)]
        lines.append('b 0x%X' % (at + 4))
        st = B.alloc(4 * (len(lines) + len(copies[k])))
        B.code(st, '\n'.join(lines))
        B.put(at, 18 << 26 | st - at & 67108860, 'kind compare 0x%X -> stub (copies %s)' % (k, ', '.join(('0x%X' % c for c in copies[k]))), orig=w)
        info['kind_compares'].append((at, k, st, copies[k]))

def args(B):
    out = ['grow:0x%08X' % (B.pc + 4095 & ~4095)]
    out += ['0x%08X=0x%08X' % (a, w) for a, w in sorted(B.words.items())]
    out += ['reloc:0x%08X-0x%08X=0x%08X' % (a, a + 4, K.RELOC_DUMMY) for a in B.reloc_args()]
    out += ['reloc:0x%08X-0x%08X=0x%08X' % (a, a + 4, d) for a, d in getattr(B, 'extra_relocs', [])]
    return out
