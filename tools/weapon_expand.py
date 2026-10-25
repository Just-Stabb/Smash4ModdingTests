#!/usr/bin/env python3
"""New weapon (article) kinds for new fighter kinds: copies of the base fighter's weapons, owned by the
new fighter (their files load from fighter/<new>/...), and the new fighter's article list pointing at
them. Prints rpx_patch.py arguments (after tools/kind_expand.py's, which this needs).

  python3 tools/rpx_patch.py build/cross_f.rpx OUT.rpx ... $(python3 tools/kind_expand.py) \\
      $(python3 tools/weapon_expand.py)
  python3 tools/weapon_expand.py [--kinds tools/extra_kinds.json] [--rpx build/cross_f.rpx] [--info]

extra_kinds.json: a record's "weapons": {"<article name>": "<new weapon kind>", ...} (the base fighter's
article of that name is copied; kinds consecutive from 0x185 over all records), and the top-level
"weapon_capacity" (default 0x1C0). A brand-new article: "<new name>": {"kind": "0x18B", "base":
"<base article>", "max": 1}: a copy of the base article's kind (its native code, descriptor, params)
under its own name and folder (fighter/<new>/model|motion/<name>/, script/.../<name>/), added to the
new fighter's article list after the base's articles (its article id = its place there), with that
max count. "on_hit": N (a brand-new article) gives it its own singleton (the base's, its first
vtable copied with the hit-result method +0xAC replaced): its attack connecting (result bits 0x13,
the ones the default method removes it for) asks for status N instead of removing it (left alone when
the status is N or more already); other results go to the base's method. Its singleton has its own
copy of the base's vtable 2 too: the base's methods that store the base singleton's +4 (its vtable 2
part: the fireball's +0x1C puts it in the weapon, which calls it) are copied with the new one's.
"nop": [...] / "nop2": [...] make those slots of the vtable / vtable 2 copies a `blr` (the
fireball's vtable 2 +0x1C counts its life down and +0x3C, every frame, removes it at life 0 and on
touching ground bounces it or, at a wall, plays Mario's puff 0x3030002 and removes it: test 14, the
beam removed early, at its life or a wall; its MSC does both). "motions": N (a brand-new article) gives its motion info N entries (the base's,
the last repeated: every one plays the base's animation; its motion.mtable names N scripts).

Research: docs/weapon-expansion*.md. Weapon kinds 0x000-0x184 (389); per kind:
- 4 name tables (root / owner / name / folder, 389 pointers, contiguous: can't grow) read by the path
  builders 0x030BC8E4 / 0x030BCB10 (13 HA/LO pairs), 3 static tables (u32 0x1018A1D4, u8 0x1018A7E8,
  u16 flags 0x1018A970; 14 pairs) and the bound 0x0320E5AC: all moved to the cave with C entries (the
  new kinds: owner = the new fighter, the rest the base's), their relocations moved to a dead word;
- 13 switches `cmplwi k, 0x184; bgt default; <k*4 + table into rT>; mtctr rT; bctr` (the descriptor
  getter 0x0320D934, the singleton getter 0x03210C30, 11 weapon methods 0x02B65000-0x02B84000, which are
  out of a branch's reach from the cave): the bound becomes C - 1, the dispatch words a far jump
  (`lis/addi rT, stub; mtctr rT; bctr`; rT is written by the original right there, so free) to a stub
  that dispatches kinds <= 0x184 exactly as before and a new kind as its base (k = base: the base's
  case, with the registers as the original leaves them) or, for the descriptor getter, to its own
  descriptor; unused kinds below C go to the default. 0x02B83B84 / 0x02B83C74 (bounds that jump into the
  last switch's dispatch) get the new bound;
- per new kind a writable descriptor copy (the base's bytes; +8 its own motion info copy, +0x14 its
  sub-article table with the kinds remapped, +0x18 / +0x24 the param getters copied to read the new
  fighter's vl slot (kind_expand's relocated array) instead of the base's, +0x1C the new kind);
- per new fighter its article list (the base's entries, kinds remapped), at the cave's start so
  kind_expand.py can point its descriptor copy's +8 at it (article_lists()).
- the module set-up 0x02BCB42C (an article's modules from its kind's row of 28 constructors, table
  0x103464A8, 0x70 a row, 389 rows, with no bound: the rows after it are another table's, so the first
  game test crashed on the fireball, kind 0x185, calling into them, user's Cemu log): `mulli r8, r30,
  0x70` at MODULE_ROW becomes a call to a stub that swaps a new kind (r30) for its base first.
"""
import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kind_expand as K  # noqa: E402
from ppcasm import Asm, ha  # noqa: E402

RPX = K.RPX
SPEC = K.SPEC
# grown code space after kind_expand.py's (its LIMIT); it was 0x04B8C000-0x04B92000, which ran into
# acmd_ext_cave.py's code (0x04B90000) once a third fighter's articles were added (Hero, from Steve /
# Hero v1): the old space is left as it is
CAVE = 0x04BB0000
LIMIT = 0x04BB8000
OLD_N = 0x185
DEFAULT_CAPACITY = 0x1C0
FIGHTER_VL = 0x111C            # FighterParamManager: vl slot of fighter kind k at +0x111C + 4 * k
NAME_TABLES = (('root', 0x104189DC), ('owner', 0x10418FF0), ('name', 0x10419604), ('folder', 0x10419C18))
STATIC_TABLES = (('u32', 0x1018A1D4, 4, 0), ('u8', 0x1018A7E8, 1, 6), ('u16', 0x1018A970, 2, 0))  # (.., invalid value)
BOUND = 0x0320E5AC             # addic r0, r4, -0x185 (kind < 0x185), the u32 / u8 accessors' check
DESC_SWITCH = 0x0320D934
SINGLETON_SWITCH = 0x03210C30  # per-kind specializer singleton (leaf, r4 = kind)
HIT_METHOD = 0xAC              # singleton vtable: hit result (r3 singleton, r4 weapon, r5 result bits)
# result bits the on_hit method takes as a hit: the ones the default method (0x0320EE2C) removes the
# weapon for (test 13: with only 0x3, a beam fired point-blank at an opponent vanished at once)
HIT_BITS = 0x13
SWITCHES = (0x0320D934, 0x03210C30, 0x02B651AC, 0x02B6894C, 0x02B6B7A8, 0x02B6FD44, 0x02B73AA4, 0x02B75A88,
            0x02B77FAC, 0x02B7A4DC, 0x02B7D378, 0x02B80CF4, 0x02B83D58)
INTO_LAST = ((0x02B83B84, 'r5'), (0x02B83C74, 'r5'))      # cmplwi r5, 0x184 jumping into 0x02B83D60
MODULE_ROW = 0x02BCB5C0        # mulli r8, r30, 0x70 (r30 = the kind) / addis r30, r8, 0x1034 / lwzu r10, 0x64A8(r30)
MODULE_TABLE = 0x103464A8      # 389 rows of 0x70 (28 module constructors)
DESC_COPY_MAX = 0x140          # bytes of a weapon descriptor copied (up to the next descriptor)
MINFO_SIZE = 0x20              # {entries, count, 0, 0, 0, 0, -90.0f, 90.0f}
ARTICLE = 0x10                 # article list entry {flags | kind, max count, callback, extra}


def load_weapons(path, img):
    """[(fighter record, [(new kind, base kind, article name)])], capacity; a brand-new article's
    record also gets r['new_articles'] = {new kind: (name, max count)}"""
    raw = json.load(open(path))
    cap = K.num(raw.get('weapon_capacity', DEFAULT_CAPACITY))
    _fcap, kinds = K.load_spec(path)
    rawk = {K.num(r['kind']): r for r in raw['kinds']}
    owner = [img.cstr(img.w(0x10418FF0 + 4 * k)) for k in range(OLD_N)]
    name = [img.cstr(img.w(0x10419604 + 4 * k)) for k in range(OLD_N)]
    out, nxt = [], OLD_N
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
                if 'on_hit' in spec:
                    r.setdefault('on_hit', {})[nk] = int(spec['on_hit'])
                    r.setdefault('nop', {})[nk] = [K.num(x) for x in spec.get('nop', [])]
                    r.setdefault('nop2', {})[nk] = [K.num(x) for x in spec.get('nop2', [])]
                art_base = spec['base']
            else:
                art_base = art
            base = [k for k in range(OLD_N) if owner[k] == r['base'] and name[k] == art_base]
            assert len(base) == 1, '%s has no article %s' % (r['base'], art_base)
            assert nk == nxt, 'weapon kinds must be consecutive from 0x185 (%s is 0x%X)' % (art, nk)
            nxt += 1
            lst.append((nk, base[0], art))
        if lst:
            out.append((r, lst))
    assert nxt <= cap, 'weapon capacity 0x%X too small' % cap
    assert cap <= 0x7FFF
    return out, cap


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
        self.words[addr] = word & 0xFFFFFFFF
        self.what[addr] = what
        if not CAVE <= addr < LIMIT:
            self.inplace.append(addr)

    def alloc(self, n, align=4):
        self.pc = (self.pc + align - 1) & ~(align - 1)
        a = self.pc
        self.pc += n
        assert self.pc <= LIMIT, 'cave full'
        return a


def rela(img):
    """{instruction address: (type, target)} of the 16-bit address relocations (ADDR16_LO 4 / HA 6)"""
    from rpx_patch import section_data
    out = {}
    for s in img.secs:
        if s[1] != 4:                    # SHT_RELA
            continue
        sym = section_data(img.d, img.secs[s[6]])
        data = section_data(img.d, s)
        for o in range(0, len(data), 12):
            off, info, add = struct.unpack('>IIi', data[o:o + 12])
            typ = info & 0xFF
            if typ in (4, 6):
                val = struct.unpack('>I', sym[16 * (info >> 8) + 4:16 * (info >> 8) + 8])[0]
                out[off & ~3] = (typ, (val + add) & 0xFFFFFFFF)
    return out


def parse_switch(img, a):
    """the dispatch at a: (kind reg, temp reg, bgt address, default, first word after the bgt, form,
    table, bctr address); form 'addis' (slwi k / addis t, k, hi / addi t, t, lo / mtctr t / bctr) or
    'r0' (lis r0, hi / slwi k / addic r0, r0, lo / add r0, k, r0 / mtctr r0 / bctr)"""
    w = img.w(a)
    assert w >> 26 == 10 and w & 0xFFFF == 0x184, 'no cmplwi 0x184 at 0x%08X' % a
    k = (w >> 16) & 0x1F
    b = a + 4
    if img.w(b) >> 26 != 16:              # one unrelated instruction between (0x02B651B0: clrlwi)
        b += 4
    assert img.w(b) >> 26 == 16, 'no bgt after 0x%08X' % a
    default = K.branch_target(b, img.w(b))
    x = b + 4
    words = [img.w(x + 4 * i) for i in range(6)]
    if words[0] >> 26 == 15 and (words[0] >> 21) & 31 == 0:          # lis r0
        hi = words[0] & 0xFFFF
        assert words[1] == K.one(x + 4, 'slwi r%d, r%d, 2' % (k, k))
        assert words[2] >> 26 == 12                                    # addic r0, r0, lo
        lo = K.sx16(words[2])
        assert words[3] == K.one(x + 12, 'add r0, r%d, r0' % k) and words[4] == K.one(x + 16, 'mtctr r0')
        assert words[5] == 0x4E800420
        t, form, bctr = 0, 'r0', x + 20
    else:
        assert words[0] == K.one(x, 'slwi r%d, r%d, 2' % (k, k))
        t = (words[1] >> 21) & 31
        assert words[1] >> 26 == 15 and (words[1] >> 16) & 31 == k     # addis t, k, hi
        hi = words[1] & 0xFFFF
        assert words[2] >> 26 == 14 and (words[2] >> 21) & 31 == t     # addi t, t, lo
        lo = K.sx16(words[2])
        assert words[3] == K.one(x + 12, 'mtctr r%d' % t) and words[4] == 0x4E800420
        form, bctr = 'addis', x + 16
    table = ((hi << 16) + lo) & 0xFFFFFFFF
    assert table == bctr + 4, 'table 0x%08X not after the bctr 0x%08X' % (table, bctr)
    return dict(at=a, k=k, t=t, bgt=b, default=default, x=x, form=form, table=table, bctr=bctr)


def case_target(img, table, kind):
    """the code a jump-table entry leads to (its b, and any b it lands on)"""
    e = table + 4 * kind
    while img.w(e) >> 26 == 18 and not img.w(e) & 3:
        e = K.branch_target(e, img.w(e))
    return e


def descriptor_of(img, kind):
    """the weapon descriptor 0x0320D934 returns for kind (its case: b getter; getter: lis/addi r3; blr)"""
    if not hasattr(img, '_desc_sw'):
        img._desc_sw = parse_switch(img, DESC_SWITCH)
    c = case_target(img, img._desc_sw['table'], kind)
    w1, w2, w3 = img.w(c), img.w(c + 4), img.w(c + 8)
    assert w1 >> 26 == 15 and (w1 >> 21) & 31 == 3 and w2 >> 26 == 14 and w3 == 0x4E800020, 'descriptor case 0x%08X' % c
    return (((w1 & 0xFFFF) << 16) + K.sx16(w2)) & 0xFFFFFFFF


def all_descriptors(img):
    out = set()
    for k in range(OLD_N):
        try:
            out.add(descriptor_of(img, k))
        except AssertionError:
            pass
    return sorted(out)


def copy_getter(img, src, base_fighter, new_vl_off):
    """a param getter (`lwz rX, 0x111C + 4 * base(rY)` ... blr) with the vl slot read moved; None if
    it isn't one"""
    words, a = [], src
    found = 0
    while True:
        w = img.w(a)
        if w >> 26 == 32 and (w & 0xFFFF) == FIGHTER_VL + 4 * base_fighter:    # lwz rX, slot(rY)
            w = (w & 0xFFFF0000) | new_vl_off
            found += 1
        words.append(w)
        if w == 0x4E800020:
            break
        assert w >> 26 not in (16, 18, 19) or w == 0x4E800020, 'branch in a getter at 0x%08X' % a
        a += 4
        assert len(words) < 32
    return words if found == 1 else None


def singleton_of(img, kind):
    """the base kind's singleton {vtable, vtable 2}: its case (lis / addi r3; blr) gives the address in
    .bss; the static initializer right after it (straight-line lis / addi / addic / stw) its words
    (vtable 2 None when the initializer doesn't set it)"""
    if not hasattr(img, '_single_sw'):
        img._single_sw = parse_switch(img, SINGLETON_SWITCH)
    c = case_target(img, img._single_sw['table'], kind)
    w1, w2, w3 = img.w(c), img.w(c + 4), img.w(c + 8)
    assert w1 >> 26 == 15 and (w1 >> 21) & 31 == 3 and w2 >> 26 == 14 and w3 == 0x4E800020, 'singleton case 0x%08X' % c
    at = (((w1 & 0xFFFF) << 16) + K.sx16(w2)) & 0xFFFFFFFF
    regs, stores, a = {}, {}, c + 12
    while img.w(a) != 0x4E800020:
        w = img.w(a)
        op, d, ra, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, K.sx16(w)
        if op == 15 and ra == 0:                                   # lis
            regs[d] = (w & 0xFFFF) << 16
        elif op in (12, 14) and ra in regs:                        # addic / addi
            regs[d] = (regs[ra] + imm) & 0xFFFFFFFF
        elif op == 36 and ra in regs and d in regs:                # stw
            stores[(regs[ra] + imm) & 0xFFFFFFFF] = regs[d]
        elif op not in (48, 52):                                   # lfs / stfs: the floats around it
            regs.pop(d, None)
        a += 4
        assert a - c < 0x80, 'no initializer after 0x%08X' % c
    # Zelda's dein stores its vtable only: its +4 (no vtable 2) stays 0 in .bss -> None
    assert at in stores, 'singleton 0x%08X not initialized after 0x%08X' % (at, c)
    return at, stores[at], stores.get(at + 4)


def sub_ref_copy(img, fn, old, new):
    """a short straight-line method (no branch but its blr, at most 16 words) that builds `old` with
    lis / addi or addic: its words with `new` instead; None otherwise"""
    if not 0x02000000 <= fn < 0x10000000:
        return None
    ws = []
    for i in range(16):
        w = img.w(fn + 4 * i)
        ws.append(w)
        if w == 0x4E800020:
            break
        if w >> 26 in (16, 18, 19):
            return None
    else:
        return None
    for i, w in enumerate(ws):
        if w >> 26 == 15 and (w >> 16) & 31 == 0:                 # lis rD, hi
            d = (w >> 21) & 31
            for j in range(i + 1, len(ws)):
                w2 = ws[j]
                if w2 >> 26 in (12, 14) and (w2 >> 16) & 31 == d:
                    if (((w & 0xFFFF) << 16) + K.sx16(w2)) & 0xFFFFFFFF == old:
                        ws[i] = (w & 0xFFFF0000) | ha(new)
                        ws[j] = (w2 & 0xFFFF0000) | (new & 0xFFFF)
                        return ws
                    break
    return None


def vtable_size(img, vt):
    """bytes of a vtable of {0, code address} pairs"""
    n = 8
    while img.w(vt + n) == 0 and 0x02000000 <= img.w(vt + n + 4) < 0x10000000:
        n += 8
    return n


def article_layout(img, recs):
    """per new fighter kind: (address of its article list, [entries]) at the cave's start"""
    out, at = {}, CAVE
    for r, lst in recs:
        fdesc = fighter_descriptor(img, r)
        alist = img.w(fdesc + 8)
        entries, count = img.w(alist), img.w(alist + 4)
        remap = {b: n for n, b, _a in lst if n not in r.get('new_articles', {})}   # brand-new: added below
        rows = []
        for i in range(count):
            e = [img.w(entries + ARTICLE * i + 4 * j) for j in range(4)]
            kind = e[0] & 0x3FFFFFFF
            if kind in remap:
                e[0] = (e[0] & 0xC0000000) | remap[kind]
            rows.append(e)
        for nk, (_name, mx) in sorted(r.get('new_articles', {}).items()):
            bk = [b for n, b, _a in lst if n == nk][0]
            found = [i for i in range(count) if (img.w(entries + ARTICLE * i) & 0x3FFFFFFF) == bk]
            assert found, 'the base fighter has no article of kind 0x%X' % bk
            i = found[0]
            e = [img.w(entries + ARTICLE * i + 4 * j) for j in range(4)]
            e[0] = (e[0] & 0xC0000000) | nk
            e[1] = mx
            rows.append(e)
        out[r['kind']] = (at, rows)
        at += 8 + ARTICLE * len(rows)
    return out, at


def fighter_descriptor(img, r):
    """the base fighter's descriptor (kind_expand's switch: case bl getter; getter lis/addi r3; blr)"""
    names = [img.cstr(img.w(K.TABLES['lower'][0] + 4 * k)) for k in range(K.OLD_N)]
    dk = K.kind_index(names, r['desc_from'])
    sw = K.switch_targets(img, 'descriptor')
    dsrc = sw[0][dk]
    g = K.branch_target(dsrc, img.w(dsrc))
    return ((img.w(g) & 0xFFFF) << 16) + K.sx16(img.w(g + 4))


def article_lists(spec_path=SPEC, rpx=RPX):
    """{new fighter kind: address of its article list} (for kind_expand.py's descriptor copies)"""
    img = K.Image(rpx)
    recs, _cap = load_weapons(spec_path, img)
    lay, _end = article_layout(img, recs)
    return {k: a for k, (a, _rows) in lay.items()}


def build(spec_path=SPEC, rpx=RPX):
    img = K.Image(rpx)
    B = Build(img)
    recs, cap = load_weapons(spec_path, img)
    fnames = [img.cstr(img.w(K.TABLES['lower'][0] + 4 * k)) for k in range(K.OLD_N)]
    fcap, _kinds = K.load_spec(spec_path)
    vl_new = K.mgr_layout(fcap)[0]['vl'][1]
    new = {}                                   # new weapon kind -> (base kind, fighter record, name)
    for r, lst in recs:
        r['bkind'] = K.kind_index(fnames, r['base'])
        for nk, bk, art in lst:
            new[nk] = (bk, r, art)
    info = {'capacity': cap, 'new': new}

    # ---- the new fighters' article lists (first: kind_expand.py points at them)
    lay, end = article_layout(img, recs)
    B.pc = end
    for fk, (at, rows) in lay.items():
        blob = struct.pack('>II', at + 8, len(rows)) + b''.join(struct.pack('>4I', *e) for e in rows)
        B.data(at, blob, 'article list 0x%X' % fk)
    info['article_lists'] = {k: a for k, (a, _r) in lay.items()}

    # ---- strings (the owners, and brand-new articles' names)
    sblob, sptr = bytearray(), {}
    for r, _lst in recs:
        sptr[r['name']] = len(sblob)
        sblob += r['name'].encode('ascii') + b'\0'
        for _nk, (aname, _mx) in sorted(r.get('new_articles', {}).items()):
            if aname not in sptr:
                sptr[aname] = len(sblob)
                sblob += aname.encode('ascii') + b'\0'
    s_at = B.alloc(len(sblob) + (-len(sblob) % 4))
    B.data(s_at, sblob, 'strings')
    sptr = {s: s_at + o for s, o in sptr.items()}

    # ---- tables (C entries)
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
                    vals.append(sptr[own_name[0]])     # a brand-new article: its own name / folder
                else:
                    vals.append(img.w(addr + 4 * bk))
            else:
                vals.append(img.w(addr))           # unused: kind 0's strings (never asked for)
        B.data(at, b''.join(struct.pack('>I', v) for v in vals), 'table ' + nm)
        tables[nm] = (addr, at)
    for nm, addr, es, invalid in STATIC_TABLES:
        size = es * cap
        at = B.alloc(size + (-size % 4))
        blob = bytearray()
        for k in range(cap):
            src = k if k < OLD_N else (new[k][0] if k in new else None)
            v = invalid if src is None else {1: img.b, 2: img.h, 4: img.w}[es](addr + es * src)
            blob += v.to_bytes(es, 'big')
        B.data(at, blob, 'table ' + nm)
        tables[nm] = (addr, at)
    info['tables'] = tables
    # every 16-bit relocation pointing at a table's start: the immediate moves with it
    rel = rela(img)
    starts = {old: new_ for old, new_ in tables.values()}
    sites = []
    for a, (typ, tgt) in sorted(rel.items()):
        if tgt in starts:
            v = starts[tgt]
            w = img.w(a)
            assert (w & 0xFFFF) == (ha(tgt) if typ == 6 else tgt & 0xFFFF), 'relocation at 0x%08X' % a
            B.put(a, (w & 0xFFFF0000) | ((ha(v) if typ == 6 else v) & 0xFFFF), ('table site', typ, tgt), w)
            sites.append(a)
    info['table_sites'] = sites
    assert len(sites) == 54, len(sites)          # 27 HA / LO pairs
    B.asm(BOUND, 'addic r0, r4, %d' % -cap, 'addic r0, r4, -0x185')

    # ---- per new kind: descriptor copy (+ motion info, sub-articles, param getters)
    descs = all_descriptors(img)
    dcase = {}
    getters = {}
    for nk in sorted(new):
        bk, r, art = new[nk]
        d = descriptor_of(img, bk)
        nxt = [x for x in descs if x > d]
        size = min(DESC_COPY_MAX, (nxt[0] - d) if nxt else DESC_COPY_MAX)
        assert size >= 0x28, 'descriptor of 0x%X too small' % bk
        blob = bytearray(img.blob(d, size))
        # +0x1C: an index of its own numbering, not the kind (Link's bow 0x8 at kind 7, Kirby's hammer
        # 0x72, 157 kinds 0xFFFFFFFF: Zelda's dein); Mario's 0-5 equal their kinds, and their copies
        # get the new kind there (as built for Supamario); any other value is kept
        if struct.unpack_from('>I', blob, 0x1C)[0] == bk:
            struct.pack_into('>I', blob, 0x1C, nk)
        mi = img.w(d + 8)
        if mi:
            ents, cnt = img.w(mi), img.w(mi + 4)
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
        sub = img.w(d + 0x14)
        if sub:
            ents, cnt = img.w(sub), img.w(sub + 4)
            remap = {b: n for n, (b, rr, _a) in new.items() if rr is r and n not in r.get('new_articles', {})}
            rows = []
            for i in range(cnt):
                e = [img.w(ents + ARTICLE * i + 4 * j) for j in range(4)]
                kk = e[0] & 0x3FFFFFFF
                if kk in remap:
                    e[0] = (e[0] & 0xC0000000) | remap[kk]
                rows.append(e)
            s_at2 = B.alloc(8 + ARTICLE * cnt)
            B.data(s_at2, struct.pack('>II', s_at2 + 8, cnt) + b''.join(struct.pack('>4I', *e) for e in rows),
                   'weapon 0x%X sub-articles' % nk)
            struct.pack_into('>I', blob, 0x14, s_at2)
        own = vl_new + 4 * r['kind']
        for off in (0x18, 0x24):
            src = struct.unpack_from('>I', blob, off)[0] if off + 4 <= size else 0
            if not src or not 0x02000000 <= src < 0x10000000:
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

    # ---- base kind of each kind 0x185 - C-1 (0xFFFF: none), a word each
    bt = B.alloc(4 * (cap - OLD_N))
    B.data(bt, b''.join(struct.pack('>I', new[k][0] if k in new else 0xFFFF) for k in range(OLD_N, cap)), 'base kinds')
    info['base_table'] = bt
    # descriptor targets of the new kinds (the getter's new path)
    dt = B.alloc(4 * (cap - OLD_N))
    B.data(dt, b''.join(struct.pack('>I', dcase.get(k, 0)) for k in range(OLD_N, cap)), 'descriptor cases')
    info['descriptor_cases'] = dt

    # ---- own singletons (on_hit): the vtable copy, the hit method, the singleton {vtable, vtable 2}
    scase = {}
    for nk in sorted(new):
        bk, r, _art = new[nk]
        status = r.get('on_hit', {}).get(nk)
        if status is None:
            continue
        _at, vt, vt2 = singleton_of(img, bk)
        size = vtable_size(img, vt)
        old_hit = img.w(vt + HIT_METHOD)          # the {0, fn} pair's fn word
        assert size > HIT_METHOD and 0x02000000 <= old_hit < 0x10000000
        fn = B.alloc(4 * 32)
        hit = B.code(fn, (
            'andi. r0, r5, %d\nbeq base\n'
            'mflr r0\nstwu r1, -0x18(r1)\nstw r0, 0x1C(r1)\nstw r31, 0x14(r1)\n'
            'lwz r12, 0x28(r4)\nlwz r31, 0x20(r12)\n'                    # StatusModule
            'lwz r12, 0(r31)\nlwz r12, 0x8C(r12)\nmtctr r12\nmr r3, r31\nbctrl\n'   # its status
            'cmpwi r3, %d\nbge done\n'
            'lwz r12, 0(r31)\nlwz r12, 0x2C(r12)\nmtctr r12\nmr r3, r31\nli r4, %d\nbctrl\n'  # change to N
            'done:\nlwz r0, 0x1C(r1)\nlwz r31, 0x14(r1)\nmtlr r0\naddi r1, r1, 0x18\nli r3, 0\nblr\n'
            'base:\nb 0x%X') % (HIT_BITS, status, status, old_hit))
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
        struct.pack_into(">I", vb, HIT_METHOD, fn)
        for off in nops:
            assert off % 8 == 4 and off < size and off != HIT_METHOD, 'vtable slot 0x%X' % off
            struct.pack_into(">I", vb, off, nop_at)
        # methods storing the base singleton's +4 (the vtable 2 part): copies with the new one's
        moved = []
        for off in range(4, size, 8):
            ws = sub_ref_copy(img, img.w(vt + off), _at + 4, o_at + 4)
            if ws is None:
                continue
            m_at = B.alloc(4 * len(ws))
            for i, w in enumerate(ws):
                B.put(m_at + 4 * i, w, ('singleton +4 method copy', off, i))
            struct.pack_into(">I", vb, off, m_at)
            moved.append((off, m_at))
        assert moved or not vt2, 'no method of 0x%08X stores the singleton +4: vtable 2 not reachable' % vt
        B.data(v_at, vb, 'weapon 0x%X vtable (copy of 0x%08X)' % (nk, vt))
        assert vt2 or not nops2, 'weapon 0x%X: nop2 but its base has no vtable 2' % nk
        if vt2:
            vb2 = bytearray(img.blob(vt2, size2))
            for off in nops2:
                assert off % 8 == 4 and off < size2, 'vtable 2 slot 0x%X' % off
                struct.pack_into(">I", vb2, off, nop_at)
            B.data(v2_at, vb2, 'weapon 0x%X vtable 2 (copy of 0x%08X)' % (nk, vt2))
        B.data(o_at, struct.pack('>II', v_at, v2_at), 'weapon 0x%X singleton' % nk)
        scase[nk] = o_at
        info.setdefault('singletons', {})[nk] = (o_at, v_at, fn, status)
        info.setdefault('nops', {})[nk] = (nops, nop_at)
        info.setdefault('vt2', {})[nk] = (v2_at, size2, nops2, moved)
    st = B.alloc(4 * (cap - OLD_N))
    B.data(st, b''.join(struct.pack('>I', scase.get(k, 0)) for k in range(OLD_N, cap)), 'singleton cases')

    # ---- the 13 switches
    info['switches'] = []
    for a in SWITCHES:
        sw = parse_switch(img, a)
        k, t = sw['k'], sw['t']
        tk = 'r%d' % t
        if t == 0:
            hi_lo = 'lis r0, 0x%X\naddic r0, r0, %d'
        else:
            hi_lo = 'lis ' + tk + ', 0x%X\naddi ' + tk + ', ' + tk + ', %d'
        stub = B.alloc(4 * 32)
        orig = ('slwi r{k}, r{k}, 2\n' + (hi_lo % (ha(sw['table']), K.slo(sw['table']))) + '\n' +
                ('add r0, r{k}, r0' if t == 0 else 'add {t}, {t}, r{k}') + '\nmtctr {t}\nbctr')
        dflt = (hi_lo % (ha(sw['default']), K.slo(sw['default']))) + '\nmtctr {t}\nbctr'
        if a == DESC_SWITCH:
            newpath = ('addi r{k}, r{k}, -0x185\nslwi r{k}, r{k}, 2\n' + (hi_lo % (ha(dt), K.slo(dt))) + '\n' +
                       ('lwzx r0, r{k}, r0' if t == 0 else 'lwzx {t}, {t}, r{k}') + '\n' +
                       ('cmpwi r0, 0' if t == 0 else 'cmpwi {t}, 0') + '\nbeq dflt\nmtctr {t}\nbctr')
        else:
            own = ''
            if a == SINGLETON_SWITCH:              # leaf: r12 free; an own singleton is returned in r3
                assert k != 12 and t != 12
                own = ('lis r12, 0x%X\naddi r12, r12, %d\nlwzx r12, r12, r{k}\ncmpwi r12, 0\nbeq bas\n'
                       'mr r3, r12\nblr\nbas:\n') % (ha(st), K.slo(st))
            newpath = ('addi r{k}, r{k}, -0x185\nslwi r{k}, r{k}, 2\n' + own + (hi_lo % (ha(bt), K.slo(bt))) + '\n' +
                       ('lwzx r{k}, r{k}, r0' if t == 0 else 'lwzx r{k}, {t}, r{k}') + '\n'
                       'cmplwi r{k}, 0x184\nble orig\nb dflt')
        src = ('cmplwi r{k}, 0x184\nbgt new\norig:\n' + orig + '\nnew:\n' + newpath + '\ndflt:\n' + dflt)
        assert len(B.code(stub, src.format(k=k, t=tk)).words()) <= 32
        # in place: the bound, and the far jump after the bgt
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

    # ---- the module set-up's row (r30 = kind -> r8 = row offset; a new kind uses its base's row).
    #      r10 is free (the next lwzu writes it); the function saved LR at its start.
    mr = B.alloc(4 * 12)
    B.code(mr, ('cmplwi r30, 0x184\nble old\naddi r8, r30, -0x185\ncmplwi r8, %d\nbge old\nslwi r8, r8, 2\n'
                'lis r10, 0x%X\naddi r10, r10, %d\nlwzx r8, r10, r8\ncmplwi r8, 0x184\nbgt old\nmr r30, r8\n'
                'old:\nmulli r8, r30, 0x70\nblr') % (cap - OLD_N, ha(bt), K.slo(bt)))
    assert B.pc - mr <= 4 * 14
    B.asm(MODULE_ROW, 'bl 0x%X' % mr, 'mulli r8, r30, 0x70')
    info['module_row'] = mr
    info['cave_end'] = B.pc
    return B, info


def args(B):
    out = ['grow:0x%08X' % ((B.pc + 0xFFF) & ~0xFFF)]
    out += ['0x%08X=0x%08X' % (a, w) for a, w in sorted(B.words.items())]
    out += ['reloc:0x%08X-0x%08X=0x%08X' % (a, a + 4, K.RELOC_DUMMY) for a in B.reloc_args()]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--kinds', default=SPEC)
    ap.add_argument('--rpx', default=RPX)
    ap.add_argument('--info', action='store_true')
    a = ap.parse_args()
    B, info = build(a.kinds, a.rpx)
    print(' '.join(args(B)))
    err = sys.stderr
    print('weapon expansion: capacity 0x%X, %d new weapon kind(s); %d words in place, %d relocations moved, '
          'cave 0x%08X-0x%08X' % (info['capacity'], len(info['new']), len(B.inplace), len(B.reloc_args()),
                                  CAVE, info['cave_end']), file=err)
    for fk, at in info['article_lists'].items():
        print('  fighter 0x%X: article list 0x%08X' % (fk, at), file=err)
    for nk, (bk, r, art) in sorted(info['new'].items()):
        d_at, d, size = info['descriptors'][nk]
        g = ', '.join('+0x%X %s' % (off, 'own params 0x%08X' % at if at else "base's (not a getter)")
                      for off, _s, at in info['getters'].get(nk, []))
        print('  0x%X %s (copy of 0x%X, owner %s): descriptor 0x%08X (0x%X bytes of 0x%08X)%s' % (
            nk, art, bk, r['name'], d_at, size, d, '; ' + g if g else ''), file=err)
        if nk in info.get('singletons', {}):
            o_at, v_at, fn, status = info['singletons'][nk]
            print('    own singleton 0x%08X (vtable 0x%08X, hit method 0x%08X: a hit -> status %d)' % (
                o_at, v_at, fn, status), file=err)
    if a.info:
        for nm, (old, new_) in info['tables'].items():
            print('  table %-6s 0x%08X -> 0x%08X' % (nm, old, new_), file=err)
        for sw in info['switches']:
            print('  switch 0x%08X (%s, k r%d, t r%d) table 0x%08X default 0x%08X stub 0x%08X' % (
                sw['at'], sw['form'], sw['k'], sw['t'], sw['table'], sw['default'], sw['stub']), file=err)


if __name__ == '__main__':
    main()
