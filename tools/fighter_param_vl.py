#!/usr/bin/env python3
"""Read, edit and create Smash 4 per-fighter param files (fighter_param_vl_<name>.bin).

The game parses each fighter's vl file into a C++ struct whose layout is compiled into the
executable, one layout per fighter kind (docs/params/fighter_param_vl.md). This tool walks the
file with that exact layout (reference/params/vl/vl_schema.json, recovered by running the game's
own parser), so every value gets a stable path, its WorkModule ID when MSC can read it, and the
labels from reference/params/vl/<Character>.csv.

Paths
  m<i>                 top-level member i (m0-m15 = groups 1-16, m16 = the "category 4" block at
                       +0x140, m17... = fighter-specific members)
  m<i>[e]              entry e of a vector member (for m12-m15 / weapon blocks: e = custom slot)
  m<i>[e].<f>          field f of that entry; m<i>.<f> for a field of a plain struct member
  ...[e].i<k>          item k of an entry made of several items (nested vectors), e.g. m17[0].i1[3]
  g<N>                 alias: the N-th group (0x20 marker) of the vanilla file, as the community
                       sheets number them (g13 = m12 for every fighter)
  0x0500000a           a WorkModule ID (category 4-8); with --slot e (default 0, or 'all')
  starmissile:0x0200000d   an ID of a weapon (article) param block (WorkModule category 2)

Commands
  dump FILE [--kind K] [--only PATH-PREFIX] [--no-labels]     list every value
  get  FILE PATH|ID [--slot S]
  set  FILE OUT PATH|ID|"label text"=VALUE ... [--slot S]      change values (type kept)
  new  OUT --base KIND [--from FILE] [--count PATH=N ...]       new file from a base fighter
  new  OUT --template KIND [--count PATH=N ...]                 same layout, values zeroed
  check FILE [--kind K]                                        validate against the layout
  test DIR                                                     parse + rebuild every vl file in DIR
  schema KIND                                                  print the layout of a kind

Type bytes (from the game's readers): 1 s8, 2 u8, 3 s16, 4 u16, 5 u32, 6 s32, 7 f32, 8 string,
0x20 group (u32 entry count). Header: FF FF 00 00 + u32 count of named tags (0 in vl files).
"""
import argparse
import csv
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, '..', 'reference', 'params', 'vl')
SCHEMA_PATH = os.path.join(REF, 'vl_schema.json')

FMT = {1: '>b', 2: '>B', 3: '>h', 4: '>H', 5: '>I', 6: '>i', 7: '>f'}
SIZE = {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4, 7: 4}
WIDTH_TYPES = {1: (1, 2), 2: (3, 4), 4: (5, 6, 7)}
TNAME = {1: 's8', 2: 'u8', 3: 's16', 4: 'u16', 5: 'u32', 6: 's32', 7: 'f32', 8: 'str'}
SCALAR = {'u8': 2, 's8': 1, 'u16': 4, 's32': 6, 'u32': 5, 'f32': 7, 'str': 8, 'str2': 8}
SPECIAL_CAT = {12: 5, 13: 6, 14: 7, 15: 8}      # member index -> WorkModule category


class VlError(Exception):
    pass


# ---------------------------------------------------------------- tokens
class Tok:
    """one typed value; raw bytes kept so unchanged values rebuild byte-exactly"""
    __slots__ = ('t', 'raw')

    def __init__(self, t, raw):
        self.t, self.raw = t, raw

    @property
    def value(self):
        if self.t == 8:
            return self.raw[4:]
        return struct.unpack(FMT[self.t], self.raw)[0]

    def set(self, v):
        if self.t == 8:
            b = v.encode('latin1') if isinstance(v, str) else bytes(v)
            self.raw = struct.pack('>I', len(b)) + b
            return
        if self.t == 7:
            self.raw = struct.pack('>f', float(v))
        else:
            v = int(v)
            if self.t in (2, 4, 5) and v < 0:
                v &= (1 << (8 * SIZE[self.t])) - 1
            self.raw = struct.pack(FMT[self.t], v)

    def text(self):
        v = self.value
        if self.t == 7:
            return '%g' % v
        if self.t == 8:
            return '"%s"' % v.decode('latin1').rstrip('\0')
        if self.t in (5, 6) and (v >= 0x01000000 or v < 0):
            return '0x%X' % (v & 0xFFFFFFFF)
        return str(v)


def tokenize(data):
    if data[:1] != b'\xff':
        raise VlError('no FF header (the game also accepts header-less files; not supported here)')
    ntag = struct.unpack('>I', data[4:8])[0]
    if ntag:
        raise VlError('header has %d named tags; vl files have none' % ntag)
    out, i = [], 8
    while i < len(data):
        t = data[i]
        i += 1
        if t == 0x20:
            out.append(('G', struct.unpack('>I', data[i:i + 4])[0]))
            i += 4
        elif t == 8:
            n = struct.unpack('>I', data[i:i + 4])[0]
            out.append(Tok(8, data[i:i + 4 + n]))
            i += 4 + n
        elif t in SIZE:
            out.append(Tok(t, data[i:i + SIZE[t]]))
            i += SIZE[t]
        else:
            raise VlError('unknown type byte 0x%02X at 0x%X' % (t, i - 1))
    return data[:8], out


# ---------------------------------------------------------------- schema
_SCHEMA = None


def schema():
    global _SCHEMA
    if _SCHEMA is None:
        with open(SCHEMA_PATH) as f:
            _SCHEMA = json.load(f)['kinds']
    return _SCHEMA


def kind_from_path(path):
    m = re.search(r'fighter_param_vl_([a-z]+)', os.path.basename(path).lower())
    if m and m.group(1) in schema():
        return m.group(1)
    return None


def resolve_kind(name):
    s = schema()
    if name in s:
        return name
    for k, v in s.items():
        if v['csv'].lower() == name.lower() or str(v['kind']) == str(name):
            return k
    raise VlError('unknown fighter kind %r (use the file name, e.g. kirby, or the CSV name)' % name)


# ---------------------------------------------------------------- tree
class Vec:
    def __init__(self, sch, entries, group):
        self.sch, self.entries, self.group = sch, entries, group   # entries: list of item lists


class Struct:
    def __init__(self, sch, toks):
        self.sch, self.toks = sch, toks


class Scalar:
    def __init__(self, sch, tok):
        self.sch, self.tok = sch, tok


class VlFile:
    def __init__(self, kind, header, members):
        self.kind, self.header, self.members = kind, header, members

    # ---- parse / build
    @classmethod
    def parse(cls, data, kind):
        header, toks = tokenize(data)
        pos = [0]
        group = [0]

        def take_tok(widths_ok, what):
            if pos[0] >= len(toks):
                raise VlError('file ends inside %s' % what)
            t = toks[pos[0]]
            if not isinstance(t, Tok) or t.t not in widths_ok:
                raise VlError('token %d: expected %s, got %s' % (pos[0], what, 'group' if not isinstance(t, Tok) else TNAME.get(t.t)))
            pos[0] += 1
            return t

        def items(sch_items):
            out = []
            for it in sch_items:
                if it['t'] == 'vec':
                    if pos[0] >= len(toks) or isinstance(toks[pos[0]], Tok):
                        raise VlError('token %d: expected a group (vector) marker' % pos[0])
                    n = toks[pos[0]][1]
                    pos[0] += 1
                    group[0] += 1
                    g = group[0]
                    out.append(Vec(it, [items(it['elem']) for _ in range(n)], g))
                elif it['t'] == 'struct':
                    out.append(Struct(it, [take_tok(WIDTH_TYPES[int(w)], 'a %s-byte value' % w) for w in it['w']]))
                else:
                    t = SCALAR[it['t']]
                    out.append(Scalar(it, take_tok((t,), it['t'])))
            return out

        members = items(schema()[kind]['members'])
        if pos[0] != len(toks):
            raise VlError('%d values left after the last member (wrong fighter kind?)' % (len(toks) - pos[0]))
        return cls(kind, header, members)

    def build(self):
        out = bytearray(self.header)

        def emit(nodes):
            for n in nodes:
                if isinstance(n, Vec):
                    out.append(0x20)
                    out.extend(struct.pack('>I', len(n.entries)))
                    for e in n.entries:
                        emit(e)
                elif isinstance(n, Struct):
                    for t in n.toks:
                        out.append(t.t)
                        out.extend(t.raw)
                else:
                    out.append(n.tok.t)
                    out.extend(n.tok.raw)
        emit(self.members)
        return bytes(out)

    # ---- leaves
    def leaves(self):
        """yield (path, tok, group, member_index, entry_or_None, field_index)"""
        def walk(nodes, prefix, top, entry, multi):
            for k, n in enumerate(nodes):
                p = prefix if not multi else '%s.i%d' % (prefix, k)
                if isinstance(n, Vec):
                    for e, ent in enumerate(n.entries):
                        yield from walk(ent, '%s[%d]' % (p, e), top, e if entry is None else entry, len(ent) > 1)
                elif isinstance(n, Struct):
                    for f, t in enumerate(n.toks):
                        yield ('%s.%d' % (p, f), t, top, entry, f)
                else:
                    yield (p, n.tok, top, entry, 0)
        for i, m in enumerate(self.members):
            yield from walk([m], 'm%d' % i, i, None, False)

    def groups(self):
        """group number -> member path prefix (vanilla numbering when counts are vanilla)"""
        res = {}

        def walk(nodes, prefix, multi):
            for k, n in enumerate(nodes):
                p = prefix if not multi else '%s.i%d' % (prefix, k)
                if isinstance(n, Vec):
                    res[n.group] = p
                    for e, ent in enumerate(n.entries):
                        walk(ent, '%s[%d]' % (p, e), len(ent) > 1)
        for i, m in enumerate(self.members):
            walk([m], 'm%d' % i, False)
        return res


# ---------------------------------------------------------------- IDs
def leaf_id(kind, path, tok):
    """WorkModule ID of a leaf, or None"""
    m = re.match(r'm(\d+)(?:\[(\d+)\])?(?:\.(\d+))?$', path)
    if not m:
        return None
    mi = int(m.group(1))
    entry, field = m.group(2), int(m.group(3) or 0)
    isint = 0x10000000 if tok.t in (5, 6) else 0
    role = schema()[kind]['members'][mi].get('role')
    if mi in SPECIAL_CAT and entry is not None:
        return isint | SPECIAL_CAT[mi] << 24 | field
    if role == 'cat4' and entry is None:
        return isint | 4 << 24 | field
    if role == 'weapon' and entry is not None:
        return isint | 2 << 24 | field
    return None


# ---------------------------------------------------------------- labels
def load_labels(kind):
    """path pattern ('m12[*].3') -> (label, description)"""
    name = schema()[kind]['csv']
    p = os.path.join(REF, name + '.csv')
    res = {}
    if not os.path.exists(p):
        return res
    with open(p, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            path = row.get('Path', '').strip()
            if not path:
                continue
            res[path] = (row.get('Move', '').strip(), row.get('Description', '').strip())
    return res


def label_for(labels, path):
    if path in labels:
        return labels[path]
    star = re.sub(r'\[\d+\]', '[*]', path, count=1)
    if star in labels:
        return labels[star]
    star_all = re.sub(r'\[\d+\]', '[*]', path)
    return labels.get(star_all, ('', ''))


# ---------------------------------------------------------------- lookup
def find(vf, key, slot='0', labels=None):
    """-> list of (path, tok)"""
    leaves = list(vf.leaves())
    gmap = vf.groups()
    key = key.strip()
    m = re.match(r'g(\d+)(.*)$', key)
    if m and int(m.group(1)) in gmap:
        key = gmap[int(m.group(1))] + m.group(2)
    weapon = None
    if ':' in key and re.match(r'[a-z_]+:0x', key):
        weapon, key = key.split(':', 1)
    if re.match(r'(0x)?[0-9a-fA-F]{7,8}$', key):
        want = int(key, 16)
        slots = None if slot == 'all' else {int(slot)}
        res = []
        for path, tok, top, entry, f in leaves:
            mem = schema()[vf.kind]['members'][top]
            if weapon and not any(w[1] == weapon for w in mem.get('weapons', [])):
                continue
            if not weapon and mem.get('role') == 'weapon':
                continue
            lid = leaf_id(vf.kind, path, tok)
            if lid is None or (lid & 0x0FFFFFFF) != (want & 0x0FFFFFFF):
                continue
            if entry is not None and slots is not None and entry not in slots:
                continue
            res.append((path, tok))
        return res
    if re.match(r'm\d+', key):
        return [(p, t) for p, t, *_ in leaves if p == key or p.startswith(key + '.') or p.startswith(key + '[')]
    if labels:
        hits = [(p, t) for p, t, *_ in leaves
                if key.lower() in ' '.join(label_for(labels, p)).lower()]
        if slot != 'all':
            hits = [(p, t) for p, t in hits if not re.search(r'\[(\d+)\]', p) or
                    re.search(r'\[(\d+)\]', p).group(1) == str(slot)]
        return hits
    return []


# ---------------------------------------------------------------- new files
def zero_tree(nodes):
    for n in nodes:
        if isinstance(n, Vec):
            for e in n.entries:
                zero_tree(e)
        elif isinstance(n, Struct):
            for t in n.toks:
                t.set(0)
        else:
            if n.tok.t == 8:
                n.tok.set(b'')
            else:
                n.tok.set(0)


def deep_copy_entry(ent):
    out = []
    for n in ent:
        if isinstance(n, Vec):
            out.append(Vec(n.sch, [deep_copy_entry(e) for e in n.entries], n.group))
        elif isinstance(n, Struct):
            out.append(Struct(n.sch, [Tok(t.t, t.raw) for t in n.toks]))
        else:
            out.append(Scalar(n.sch, Tok(n.tok.t, n.tok.raw)))
    return out


def set_count(vf, path, n):
    """resize the vector at path (e.g. m4 or g5) to n entries, copying the last entry"""
    gmap = vf.groups()
    m = re.match(r'g(\d+)$', path)
    if m:
        path = gmap[int(m.group(1))]
    node = None

    def walk(nodes, prefix, multi):
        nonlocal node
        for k, x in enumerate(nodes):
            p = prefix if not multi else '%s.i%d' % (prefix, k)
            if isinstance(x, Vec):
                if p == path:
                    node = x
                for e, ent in enumerate(x.entries):
                    walk(ent, '%s[%d]' % (p, e), len(ent) > 1)
    for i, mm in enumerate(vf.members):
        walk([mm], 'm%d' % i, False)
    if node is None:
        raise VlError('no vector at %s' % path)
    if not node.entries and n:
        raise VlError('%s is empty in the base file; cannot copy an entry' % path)
    while len(node.entries) > n:
        node.entries.pop()
    while len(node.entries) < n:
        node.entries.append(deep_copy_entry(node.entries[-1]))


# ---------------------------------------------------------------- CLI
def load(path, kind=None):
    kind = resolve_kind(kind) if kind else kind_from_path(path)
    if not kind:
        raise VlError('cannot tell the fighter kind from %s; pass --kind' % path)
    with open(path, 'rb') as f:
        data = f.read()
    vf = VlFile.parse(data, kind)
    if vf.build() != data:
        raise VlError('internal: round trip differs')
    return vf


def cmd_dump(a):
    vf = load(a.file, a.kind)
    labels = {} if a.no_labels else load_labels(vf.kind)
    gmap = {v: k for k, v in vf.groups().items()}
    last_top = None
    for path, tok, top, entry, f in vf.leaves():
        if a.only and not (path == a.only or path.startswith(a.only + '.') or path.startswith(a.only + '[')):
            continue
        if top != last_top:
            mem = schema()[vf.kind]['members'][top]
            g = gmap.get('m%d' % top)
            print('# m%d%s  +0x%X  %s%s' % (top, ' (g%d)' % g if g else '', mem['off'], mem.get('role', 'fighter'),
                                        ' ' + ','.join(w[1] for w in mem.get('weapons', [])) if mem.get('weapons') else ''))
            last_top = top
        lid = leaf_id(vf.kind, path, tok)
        mv, desc = label_for(labels, path)
        print('%-16s %-11s %-4s %-12s %s' % (path, '0x%08X' % lid if lid is not None else '', TNAME[tok.t], tok.text(),
                                             ' | '.join(x for x in (mv, desc) if x)))


def cmd_get(a):
    vf = load(a.file, a.kind)
    hits = find(vf, a.key, a.slot, load_labels(vf.kind))
    if not hits:
        raise VlError('nothing matches %r' % a.key)
    for p, t in hits:
        print(p, TNAME[t.t], t.text())


def cmd_set(a):
    vf = load(a.file, a.kind)
    labels = load_labels(vf.kind)
    for spec in a.assign:
        key, _, val = spec.rpartition('=')
        hits = find(vf, key, a.slot, labels)
        if not hits:
            raise VlError('nothing matches %r' % key)
        if len(hits) > 1 and not (re.match(r'(0x)?[0-9a-fA-F]{7,8}$', key.split(':')[-1]) and a.slot == 'all') \
                and not re.match(r'[mg]\d+$', key):
            raise VlError('%r matches %d values (%s...); be more specific' % (key, len(hits), ', '.join(p for p, _ in hits[:4])))
        for p, t in hits:
            v = val.strip()
            if t.t == 7:
                t.set(float(v))
            elif t.t == 8:
                t.set(v)
            else:
                t.set(int(v, 0))
            print('%s = %s' % (p, t.text()))
    with open(a.out, 'wb') as f:
        f.write(vf.build())


def cmd_new(a):
    if bool(a.base) == bool(a.template):
        raise VlError('give --base KIND or --template KIND')
    kind = resolve_kind(a.base or a.template)
    src = a.src
    if not src:
        raise VlError('give --from FILE: the base fighter\'s vanilla fighter_param_vl_<name>.bin '
                      '(it supplies the value types and the default values)')
    vf = load(src, kind)
    if a.template:
        zero_tree(vf.members)
    for spec in a.count or []:
        p, n = spec.split('=')
        set_count(vf, p.strip(), int(n, 0))
    data = vf.build()
    VlFile.parse(data, kind)
    with open(a.out, 'wb') as f:
        f.write(data)
    print('wrote %s (%d bytes, layout of %s)' % (a.out, len(data), kind))


def cmd_check(a):
    vf = load(a.file, a.kind)
    s = schema()[vf.kind]
    for mi, cat in SPECIAL_CAT.items():
        n = len(vf.members[mi].entries)
        if n < 4:
            print('warning: m%d (category %d) has %d entries; the game indexes it by custom slot 0-3' % (mi, cat, n))
    print('ok: %s layout, %d members, %d values' % (vf.kind, len(s['members']), sum(1 for _ in vf.leaves())))


def cmd_test(a):
    bad = 0
    for fn in sorted(os.listdir(a.dir)):
        k = kind_from_path(fn)
        if not k:
            continue
        p = os.path.join(a.dir, fn)
        data = open(p, 'rb').read()
        try:
            vf = VlFile.parse(data, k)
            ok = vf.build() == data
        except VlError as e:
            ok = False
            print(fn, e)
        bad += not ok
        print('%-34s %s' % (fn, 'ok' if ok else 'FAIL'))
    sys.exit(1 if bad else 0)


def cmd_schema(a):
    kind = resolve_kind(a.kind_name)
    s = schema()[kind]
    print('%s (kind %d, CSV %s): category bytes %s' % (kind, s['kind'], s['csv'], s['cat_bytes']))

    def show(items, ind):
        for it in items:
            if it['t'] == 'vec':
                print(' ' * ind + 'vector, entry %d bytes:' % it['esize'])
                show(it['elem'], ind + 4)
            elif it['t'] == 'struct':
                print(' ' * ind + 'struct %d fields (byte widths %s)' % (len(it['w']), it['w']))
            else:
                print(' ' * ind + it['t'])
    for i, m in enumerate(s['members']):
        print('m%-3d +0x%03X %-18s' % (i, m['off'], m.get('role', 'fighter') +
                                        (' ' + ','.join(w[1] for w in m.get('weapons', [])) if m.get('weapons') else '')))
        show([m], 8)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('dump')
    p.add_argument('file')
    p.add_argument('--kind')
    p.add_argument('--only')
    p.add_argument('--no-labels', action='store_true')
    p = sp.add_parser('get')
    p.add_argument('file')
    p.add_argument('key')
    p.add_argument('--kind')
    p.add_argument('--slot', default='0')
    p = sp.add_parser('set')
    p.add_argument('file')
    p.add_argument('out')
    p.add_argument('assign', nargs='+')
    p.add_argument('--kind')
    p.add_argument('--slot', default='0')
    p = sp.add_parser('new')
    p.add_argument('out')
    p.add_argument('--base')
    p.add_argument('--template')
    p.add_argument('--from', dest='src')
    p.add_argument('--count', action='append')
    p = sp.add_parser('check')
    p.add_argument('file')
    p.add_argument('--kind')
    p = sp.add_parser('test')
    p.add_argument('dir')
    p = sp.add_parser('schema')
    p.add_argument('kind_name')
    a = ap.parse_args(argv)
    try:
        {'dump': cmd_dump, 'get': cmd_get, 'set': cmd_set, 'new': cmd_new, 'check': cmd_check,
         'test': cmd_test, 'schema': cmd_schema}[a.cmd](a)
    except VlError as e:
        sys.exit('error: %s' % e)


if __name__ == '__main__':
    main()
