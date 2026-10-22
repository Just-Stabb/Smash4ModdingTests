#!/usr/bin/env python3
"""Fighter collision shapes in param/fighter/fighter_param_vl_<name>.bin: hurtboxes, the ground
box (ECB) bones and the ledge-grab boxes (docs/params/fighter_files.md "Shapes").

  python3 tools/vl_shapes.py VL.bin [--model DIR]             print them
  python3 tools/vl_shapes.py VL.bin --json OUT.json [--model DIR]
  python3 tools/vl_shapes.py VL.bin --apply IN.json OUT.bin    write the JSON's shapes (counts may change)
  python3 tools/vl_shapes.py --selftest PARAM_FIGHTER_DIR     byte-exact round trip of every vl file

DIR = a model folder (model/body/c00) with model.vbn and model.jtb: bone IDs are shown by name.
Bone IDs (as in ACMD): 0 = TransN, n = model.jtb table 0 entry n-1, 1000+n = table 1 entry n.

Groups, counted from 1 as the community sheet and docs/params do (the file's first group is 1):
  4  ECB bones: u32 bone, f32 x y z (offset in the bone's space). The game's ground box is the
     bounding box of these points (GroundModule, 0x02C39C40), at least 4.0 x 4.0 (x scale).
  5  hurtboxes: f32 x1 y1 z1 x2 y2 z2 (capsule ends in the bone's space; equal ends = sphere),
     f32 radius, u32 bone, part, height, unk, pool. part (0 body/head, 1 arm, 2 other, 3 leg) and
     height (0 low, 1 mid, 2 high) are inferred from the bones they sit on; pool is always 2 (the
     collision pool the shape is allocated from, 0x02C118E4). HitModule set-up: 0x02C42D7C.
  7  ledge-grab boxes: f32 x y w h (the sheet's X, Y, X2, Y2); entry 0 = normal, 1 = while
     tumbling (some fighters have more, e.g. tether boxes). GroundModule 0x02C36A34 scales them by
     the fighter's size.
The other groups are kept byte for byte. The file is the generic param format (FF FF 00 00 +
4 bytes, then typed values; 0x20 = a group: u32 entry count, the values up to the next group).
"""
import json
import os
import struct
import sys

SIZES = {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4, 7: 4}
FMT = {1: '>B', 2: '>b', 3: '>H', 4: '>h', 5: '>I', 6: '>i', 7: '>f'}
ECB, HURT, LEDGE = 4, 5, 7      # group numbers counted from 1 (groups[0] = values before group 1)
HURT_KEYS = ('x1', 'y1', 'z1', 'x2', 'y2', 'z2', 'radius', 'bone', 'part', 'height', 'unk', 'pool')
ECB_KEYS = ('bone', 'x', 'y', 'z')
LEDGE_KEYS = ('x', 'y', 'w', 'h')


def parse(data):
    """(header, [[count, [(type, value), ...]], ...]); values before the first group go in a
    pseudo-group with count None"""
    assert data[:4] == b'\xff\xff\x00\x00', 'not a param file'
    groups = [[None, []]]
    i = 8
    while i < len(data):
        t = data[i]
        i += 1
        if t == 0x20:
            groups.append([struct.unpack('>I', data[i:i + 4])[0], []])
            i += 4
            continue
        if t == 8:
            n = struct.unpack('>I', data[i:i + 4])[0]
            v = data[i + 4:i + 4 + n]
            i += 4 + n
        else:
            v = struct.unpack(FMT[t], data[i:i + SIZES[t]])[0]
            i += SIZES[t]
        groups[-1][1].append((t, v))
    return data[:8], groups


def build(header, groups):
    out = bytearray(header)
    for count, vals in groups:
        if count is not None:
            out += b'\x20' + struct.pack('>I', count)
        for t, v in vals:
            out.append(t)
            out += struct.pack('>I', len(v)) + v if t == 8 else struct.pack(FMT[t], v)
    return bytes(out)


def entries(group):
    count, vals = group
    if not count or len(vals) % count:
        return None
    k = len(vals) // count
    return [vals[j * k:(j + 1) * k] for j in range(count)]


def set_entries(group, new, keys, template):
    """replace the group's entries with dicts `new`, value types from `template` (an old entry)"""
    vals = []
    for e in new:
        vals += [(t, int(e[k]) if t != 7 else float(e[k])) for (t, _v), k in zip(template, keys)]
    group[0], group[1] = len(new), vals


# ---------------------------------------------------------------- bones

def load_bones(model_dir):
    vbn = open(os.path.join(model_dir, 'model.vbn'), 'rb').read()
    e = '<' if vbn[:4] == b' NBV' else '>'
    n = struct.unpack(e + 'I', vbn[8:12])[0]
    names = [vbn[28 + 76 * k:28 + 76 * k + 64].split(b'\0')[0].decode('latin1') for k in range(n)]
    tables = []
    jp = os.path.join(model_dir, 'model.jtb')
    if os.path.exists(jp):
        j = open(jp, 'rb').read()
        o = 4
        for cnt in struct.unpack('>HH', j[:4]):
            tables.append(list(struct.unpack('>%dh' % cnt, j[o:o + 2 * cnt])))
            o += 2 * cnt
    return names, tables


def bone_name(bid, bones):
    if not bones:
        return None
    names, tables = bones
    if bid >= 1000:
        t, k = divmod(bid, 1000)
        tab = tables[min(t, len(tables) - 1)] if tables else []
        idx = tab[k] if k < len(tab) else None
    elif bid == 0:
        return 'TransN'
    else:
        idx = (tables[0][bid - 1] if tables and bid - 1 < len(tables[0]) else
               (bid if not tables else None))
    return names[idx] if idx is not None and 0 <= idx < len(names) else '?'


# ---------------------------------------------------------------- shapes <-> dicts

def shapes(groups, bones=None):
    out = {}
    for gi, keys, name in ((HURT, HURT_KEYS, 'hurtboxes'), (ECB, ECB_KEYS, 'ecb_bones'),
                           (LEDGE, LEDGE_KEYS, 'ledge_boxes')):
        rows = []
        for e in entries(groups[gi]) or []:
            d = {k: v for k, (_t, v) in zip(keys, e)}
            if 'bone' in d and bones:
                d['bone_name'] = bone_name(d['bone'], bones)
            rows.append(d)
        out[name] = rows
    return out


def apply(groups, sh):
    for gi, keys, name in ((HURT, HURT_KEYS, 'hurtboxes'), (ECB, ECB_KEYS, 'ecb_bones'),
                           (LEDGE, LEDGE_KEYS, 'ledge_boxes')):
        if name in sh:
            g = groups[gi]
            old = entries(g)
            assert old, 'group %d has no entries to take the value types from' % gi
            set_entries(g, sh[name], keys, old[0])


def show(sh):
    f = lambda v: ('%g' % v) if isinstance(v, float) else str(v)  # noqa: E731
    print('hurtboxes (group 5): x1 y1 z1 x2 y2 z2 radius | bone part height unk pool')
    for k, d in enumerate(sh['hurtboxes']):
        print('  %2d: %s | %s%s' % (k, ' '.join(f(d[x]) for x in HURT_KEYS[:7]),
                                    ' '.join(f(d[x]) for x in HURT_KEYS[7:]),
                                    ('  (%s)' % d['bone_name']) if 'bone_name' in d else ''))
    print('ECB bones (group 4): bone x y z')
    for k, d in enumerate(sh['ecb_bones']):
        print('  %2d: %s%s' % (k, ' '.join(f(d[x]) for x in ECB_KEYS),
                               ('  (%s)' % d['bone_name']) if 'bone_name' in d else ''))
    print('ledge-grab boxes (group 7): x y w h')
    for k, d in enumerate(sh['ledge_boxes']):
        print('  %2d: %s' % (k, ' '.join(f(d[x]) for x in LEDGE_KEYS)))


def selftest(folder):
    n = 0
    for fn in sorted(os.listdir(folder)):
        if fn.startswith('fighter_param_vl_') and fn.endswith('.bin'):
            data = open(os.path.join(folder, fn), 'rb').read()
            h, g = parse(data)
            assert build(h, g) == data, fn
            sh = json.loads(json.dumps(shapes(g)))
            apply(g, sh)
            assert build(h, g) == data, fn + ' (through JSON)'
            n += 1
    print('%d files round-trip byte for byte' % n)


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == '--selftest':
        return selftest(a[1])
    data = open(a[0], 'rb').read()
    header, groups = parse(data)
    assert build(header, groups) == data, 'round trip differs'
    bones = load_bones(a[a.index('--model') + 1]) if '--model' in a else None
    if '--apply' in a:
        sh = json.load(open(a[a.index('--apply') + 1]))
        apply(groups, sh)
        out = a[a.index('--apply') + 2]
        open(out, 'wb').write(build(header, groups))
        print('wrote', out)
        return
    sh = shapes(groups, bones)
    if '--json' in a:
        json.dump(sh, open(a[a.index('--json') + 1], 'w'), indent=1)
        print('wrote', a[a.index('--json') + 1])
    else:
        show(sh)


if __name__ == '__main__':
    main()
