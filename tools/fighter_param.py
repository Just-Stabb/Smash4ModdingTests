#!/usr/bin/env python3
"""Read / edit the shared fighter attribute tables of Smash 4 (Wii U) by name.

Files (data/param/fighter/): fighter_param.bin, fighter_param_common.bin, fighter_param_etc.bin,
fighter_param_power_up.bin, fighter_param_equipment_ability.bin.  Format: generic param file
(FF FF 00 00 + 4 bytes, then typed values; 0x20 = group with an entry count).  The game binds each
file to a fixed C++ layout (see docs/params/fighter_param.md); this tool uses the same layouts, so
nested groups (etc, equipment_ability) are split exactly as the game splits them.

Labels come from reference/params/<file>.csv (column `name`).

  python3 tools/fighter_param.py dump FILE [FIGHTER]          labelled dump (fighter_param: one fighter,
                                                               or a one-line-per-attribute table of all)
  python3 tools/fighter_param.py get FILE FIGHTER NAME...      print values
  python3 tools/fighter_param.py set FILE OUT FIGHTER NAME=VALUE ...
  python3 tools/fighter_param.py add FILE OUT BASE KIND        append an entry for fighter kind KIND (copy of BASE)
  python3 tools/fighter_param.py set-common FILE OUT NAME=VALUE ...   (fighter_param_common.bin)
  python3 tools/fighter_param.py check FILE...                 parse + rebuild, must be byte-identical

FIGHTER = kind number (0-64) or internal name (mario, kirby, koopag, ...).  NAME = attribute name
from the CSV, an index (e.g. 0x21 or 33) or an ID (0x03000021 / 0x13000022).

Notes for new fighters: fighter_param entries are matched by word 0 (= fighter kind), not by
position; the vanilla executable only maps kinds 0..64 (0x41 slots) and copies exactly 354 words
per fighter, so an added kind > 64 is ignored unless the executable is extended.
"""
import csv
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, '..', 'reference', 'params')

SIZES = {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4, 7: 4}
FMT = {1: '>B', 2: '>b', 3: '>H', 4: '>h', 5: '>I', 6: '>i', 7: '>f'}
TYPE_NAMES = {1: 'u8', 2: 's8', 3: 'u16', 4: 's16', 5: 'u32', 6: 's32', 7: 'float', 8: 'string'}

KINDS = ['miifighter', 'miiswordsman', 'miigunner', 'mario', 'donkey', 'link', 'samus', 'yoshi', 'kirby', 'fox',
         'pikachu', 'luigi', 'captain', 'ness', 'peach', 'koopa', 'zelda', 'sheik', 'marth', 'gamewatch', 'ganon',
         'falco', 'wario', 'metaknight', 'pit', 'szerosuit', 'pikmin', 'diddy', 'dedede', 'ike', 'lucario', 'robot',
         'toonlink', 'lizardon', 'sonic', 'purin', 'mariod', 'lucina', 'pitb', 'rosetta', 'wiifit', 'littlemac',
         'murabito', 'palutena', 'reflet', 'duckhunt', 'koopajr', 'shulk', 'gekkouga', 'pacman', 'rockman',
         'mewtwo', 'ryu', 'lucas', 'roy', 'cloud', 'bayonetta', 'kamui', 'koopag', 'warioman', 'littlemacg',
         'lucariom', 'miienemyf', 'miienemys', 'miienemyg']

# ---------------------------------------------------------------------------------------------
# Layouts, decoded from the executable's binders (constructor + bind function per file):
#   ('vec', name, [fields])  = a 0x20 group, each entry made of `fields`
#   ('n', name, count)       = `count` loose values (any 1/2/4-byte type the binder accepts)
# fighter_param:   ctor 0x02E8F81C, entry schema 0x1012D724 (354 u32)
# common:          ctor 0x02E8F910, schema 0x1012D754 (849 u32)
# etc:             ctor 0x02E8F9D4, bind 0x02E89E88
# power_up:        ctor 0x02E8FF78, bind 0x02E8A048
# equipment_ab.:   ctor 0x02E901E4, bind 0x02E8A0A8
LAYOUTS = {
    'fighter_param': [('vec', 'fighters', [('n', 'w', 354)])],
    'fighter_param_common': [('n', 'w', 849)],
    'fighter_param_etc': [
        ('vec', 'g00', [('n', 'w', 3)]),           # +0x000
        ('vec', 'g01', [('n', 'w', 5)]),           # +0x014
        ('n', 'g02', 6),                           # +0x028
        ('n', 'g03', 18),                          # +0x040
        ('vec', 'g04', [('n', 'w', 1)]),           # +0x088 floats
        ('vec', 'g05', [('n', 'w', 4)]),           # +0x09C
        ('vec', 'g06', [('n', 'w', 4)]),           # +0x0B0 4 x u8
        ('vec', 'g07', [('n', 'w', 4)]),           # +0x0C4 4 x u8
        ('vec', 'g08', [('vec', 'sub', [('n', 'w', 1)])]),                 # +0x0D8
        ('vec', 'g09', [('vec', 'sub', [('n', 'w', 2)]), ('n', 'w', 2)]),  # +0x0EC
        ('vec', 'g10', [('n', 'w', 2)]),           # +0x100
        ('n', 'g11', 2),                           # +0x114
        ('n', 'g12', 2),                           # +0x11C
        ('n', 'g13', 1),                           # +0x124 float
        ('vec', 'g14', [('n', 'w', 1)]),           # +0x128 u32
        ('vec', 'g15', [('n', 'w', 3)]),           # +0x13C
        ('vec', 'g16', [('n', 'w', 4)]),           # +0x150 3 words + u8
        ('vec', 'g17', [('n', 'w', 3)]),           # +0x164
        ('vec', 'g18', [('n', 'w', 1)]),           # +0x178 floats
        ('vec', 'g19', [('n', 'w', 3)]),           # +0x18C 3 x u8
        ('vec', 'g20', [('n', 'w', 11)]),          # +0x1A0
        ('vec', 'g21', [('n', 'w', 11)]),          # +0x1B4
        ('vec', 'g22', [('n', 'w', 9)]),           # +0x1C8
        ('vec', 'g23', [('n', 'w', 2)]),           # +0x1DC
        ('n', 'g24', 4),                           # +0x1F0
        ('vec', 'g25', [('n', 'w', 2)]),           # +0x200
        ('vec', 'g26', [('n', 'w', 2)]),           # +0x214
        ('vec', 'g27', [('n', 'w', 3)]),           # +0x228 u16 + 2 x u8
        ('vec', 'g28', [('n', 'w', 2)]),           # +0x23C
        ('vec', 'g29', [('n', 'w', 1)]),           # +0x250 floats
        ('vec', 'g30', [('n', 'w', 3)]),           # +0x264
        ('vec', 'g31', [('n', 'w', 2)]),           # +0x278
        ('n', 'g32', 3),                           # +0x28C 2 x u8, u32
    ],
    'fighter_param_power_up': [
        ('vec', 'g0', [('n', 'w', 6)]), ('vec', 'g1', [('n', 'w', 6)]), ('vec', 'g2', [('n', 'w', 6)]),
        ('vec', 'g3', [('n', 'w', 6)]), ('vec', 'g4', [('n', 'w', 6)]), ('vec', 'g5', [('n', 'w', 6)]),
        ('vec', 'g6', [('n', 'w', 2)]), ('vec', 'g7', [('n', 'w', 6)]),
    ],
    'fighter_param_equipment_ability': [
        ('n', 'g0', 186),
        ('vec', 'g1', [('vec', 'sub', [('n', 'w', 4)]), ('n', 'w', 1)]),
    ],
}
# struct offset of each top-level node (for cross-referencing code), etc only
ETC_OFFSETS = [0x0, 0x14, 0x28, 0x40, 0x88, 0x9C, 0xB0, 0xC4, 0xD8, 0xEC, 0x100, 0x114, 0x11C, 0x124, 0x128,
               0x13C, 0x150, 0x164, 0x178, 0x18C, 0x1A0, 0x1B4, 0x1C8, 0x1DC, 0x1F0, 0x200, 0x214, 0x228, 0x23C,
               0x250, 0x264, 0x278, 0x28C]


class Val:
    """One typed value; keeps its raw bytes so unchanged values are written back byte-exact."""
    __slots__ = ('t', 'raw')

    def __init__(self, t, raw):
        self.t, self.raw = t, raw

    @property
    def v(self):
        if self.t == 8:
            return self.raw[4:]
        return struct.unpack(FMT[self.t], self.raw)[0]

    @v.setter
    def v(self, x):
        if self.t == 7:
            self.raw = struct.pack('>f', float(x))
        elif self.t == 8:
            self.raw = struct.pack('>I', len(x)) + x
        else:
            self.raw = struct.pack(FMT[self.t], int(x))

    def __repr__(self):
        return fmt(self)


def fmt(val):
    v = val.v
    if val.t == 7:
        return '%.9g' % v
    if val.t == 5 and v >= 0x80000000:
        return '0x%X' % v
    return str(v)


def tokens(data):
    assert data[:4] == b'\xff\xff\x00\x00', 'not a param file'
    i = 8
    out = []
    while i < len(data):
        t = data[i]
        i += 1
        if t == 0x20:
            out.append(('G', struct.unpack('>I', data[i:i + 4])[0]))
            i += 4
        elif t == 8:
            ln = struct.unpack('>I', data[i:i + 4])[0]
            out.append(Val(8, data[i:i + 4 + ln]))
            i += 4 + ln
        else:
            out.append(Val(t, data[i:i + SIZES[t]]))
            i += SIZES[t]
    return out


def parse_fields(fields, toks, pos):
    """returns (dict name -> value list / list of entries, new pos)"""
    res = []
    for f in fields:
        if f[0] == 'n':
            vals = toks[pos:pos + f[2]]
            assert len(vals) == f[2] and all(isinstance(x, Val) for x in vals), 'layout mismatch at %s' % f[1]
            res.append((f[1], vals))
            pos += f[2]
        else:
            g = toks[pos]
            assert isinstance(g, tuple) and g[0] == 'G', 'expected group for %s' % f[1]
            pos += 1
            ents = []
            for _ in range(g[1]):
                e, pos = parse_fields(f[2], toks, pos)
                ents.append(e)
            res.append((f[1], ents))
    return res, pos


def emit_fields(fields, node, out):
    for f, (name, val) in zip(fields, node):
        if f[0] == 'n':
            for x in val:
                out.append(bytes([x.t]) + x.raw)
        else:
            out.append(b'\x20' + struct.pack('>I', len(val)))
            for e in val:
                emit_fields(f[2], e, out)


class ParamFile:
    def __init__(self, path, kind=None):
        self.path = path
        self.data = open(path, 'rb').read()
        base = os.path.basename(path)
        self.kind = kind or os.path.splitext(base)[0]
        if self.kind not in LAYOUTS:
            raise SystemExit('unknown file kind %s (expected one of %s)' % (self.kind, ', '.join(LAYOUTS)))
        self.layout = LAYOUTS[self.kind]
        self.header = self.data[:8]
        toks = tokens(self.data)
        self.root, pos = parse_fields(self.layout, toks, 0)
        assert pos == len(toks), 'trailing values after layout (%d of %d)' % (pos, len(toks))

    def build(self):
        out = [self.header]
        emit_fields(self.layout, self.root, out)
        return b''.join(out)

    def save(self, path):
        open(path, 'wb').write(self.build())

    # --- fighter_param helpers
    def entries(self):
        return [e[0][1] for e in self.root[0][1]]

    def entry(self, fighter):
        k = kind_of(fighter)
        for e in self.entries():
            if e[0].v == k:
                return e
        raise SystemExit('no entry with kind %d' % k)


def kind_of(f):
    f = str(f).lower()
    if f in KINDS:
        return KINDS.index(f)
    return int(f, 0)


def load_labels(kind):
    """fighter_param / common: {index: row}; others: {path: row}"""
    p = os.path.join(REF, kind + '.csv')
    rows = {}
    if not os.path.exists(p):
        return rows
    for r in csv.DictReader(open(p, newline='')):
        key = r.get('index') or r.get('path')
        try:
            key = int(key, 0)
        except (TypeError, ValueError):
            pass
        rows[key] = r
    return rows


def resolve(name, labels):
    s = str(name)
    try:
        v = int(s, 0)
        return v & 0xFFFFFF if v > 0xFFFFFF else v
    except ValueError:
        pass
    for k, r in labels.items():
        if r.get('name') == s:
            return k
    raise SystemExit('unknown attribute %s' % s)


def parse_value(val, text):
    if val.t == 7:
        return float(text)
    return int(text, 0)


def walk(fields, node, prefix=''):
    """yield (path, Val) for every value"""
    for f, (name, val) in zip(fields, node):
        p = prefix + name
        if f[0] == 'n':
            for i, x in enumerate(val):
                yield '%s.%d' % (p, i), x
        else:
            for j, e in enumerate(val):
                for q in walk(f[2], e, '%s[%d].' % (p, j)):
                    yield q


def cmd_dump(args):
    pf = ParamFile(args[0])
    labels = load_labels(pf.kind)
    if pf.kind == 'fighter_param':
        if len(args) > 1:
            e = pf.entry(args[1])
            for i, x in enumerate(e):
                r = labels.get(i, {})
                print('%3d 0x%03X %-6s %-34s %s' % (i, i, TYPE_NAMES[x.t], r.get('name', ''), fmt(x)))
        else:
            ents = pf.entries()
            names = [KINDS[e[0].v] if e[0].v < len(KINDS) else str(e[0].v) for e in ents]
            print('idx  name' + ''.join(' %s' % n for n in names))
            for i in range(354):
                r = labels.get(i, {})
                print('%3d %s %s' % (i, r.get('name', ''), ' '.join(fmt(e[i]) for e in ents)))
    elif pf.kind == 'fighter_param_common':
        for i, x in enumerate(pf.root[0][1]):
            r = labels.get(i, {})
            print('%3d 0x%s %-6s %-40s %s' % (i, '%X' % ((0x12 if x.t == 5 else 0x02) << 24 | i), TYPE_NAMES[x.t],
                                              r.get('name', ''), fmt(x)))
    else:
        for path, x in walk(pf.layout, pf.root):
            r = labels.get(path) or labels.get(generic_path(path), {})
            print('%-24s %-6s %-40s %s' % (path, TYPE_NAMES[x.t], r.get('name', ''), fmt(x)))


def generic_path(path):
    """g01[3].w.2 -> g01[*].w.2"""
    import re
    return re.sub(r'\[\d+\]', '[*]', path)


def cmd_get(args):
    pf = ParamFile(args[0])
    labels = load_labels(pf.kind)
    e = pf.entry(args[1])
    for n in args[2:]:
        i = resolve(n, labels)
        print('%s = %s' % (n, fmt(e[i])))


def cmd_set(args):
    pf = ParamFile(args[0])
    labels = load_labels(pf.kind)
    e = pf.entry(args[2])
    for a in args[3:]:
        n, v = a.split('=', 1)
        i = resolve(n, labels)
        if i == 0:
            raise SystemExit('word 0 is the fighter kind; use add to make a new entry')
        e[i].v = parse_value(e[i], v)
    pf.save(args[1])


def cmd_set_common(args):
    pf = ParamFile(args[0])
    labels = load_labels(pf.kind)
    vals = pf.root[0][1]
    for a in args[2:]:
        n, v = a.split('=', 1)
        i = resolve(n, labels)
        vals[i].v = parse_value(vals[i], v)
    pf.save(args[1])


def cmd_add(args):
    pf = ParamFile(args[0])
    base = pf.entry(args[2])
    k = kind_of(args[3])
    if any(e[0].v == k for e in pf.entries()):
        raise SystemExit('kind %d already has an entry' % k)
    new = [Val(x.t, x.raw) for x in base]
    new[0].v = k
    pf.root[0][1].append([('w', new)])
    pf.save(args[1])
    if k > 64:
        print('note: the vanilla executable only maps kinds 0-64; kind %d needs an extended exe' % k)


def cmd_check(args):
    ok = True
    for p in args:
        pf = ParamFile(p)
        same = pf.build() == pf.data
        ok &= same
        print('%s: %s' % (p, 'round trip OK' if same else 'DIFFERS'))
    if not ok:
        sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    fn = {'dump': cmd_dump, 'get': cmd_get, 'set': cmd_set, 'add': cmd_add, 'check': cmd_check,
          'set-common': cmd_set_common}.get(cmd)
    if not fn:
        raise SystemExit('unknown command %s' % cmd)
    fn(sys.argv[2:])


if __name__ == '__main__':
    main()
