#!/usr/bin/env python3
"""Checks tools/fighter_texture_ids.py.

Unit (always): a made-up fighter folder (two costumes and their low models, an article in two costumes, the old shared
0x40EB ids, a metal.nud naming a texture its .nut lacks, a model.mta with a texture pattern) re-id'd: the scheme's
ranges, cNN / lNN / article sharing, every reference followed, pixels unchanged, the check clean after and not before.

Package (--package ZIP PKG...): a fix package against the install it fixes (PKG...: the packages in install order):
  - every rewritten .nut decodes to the original's pixels texture for texture, and differs from it only in the ids;
  - every rewritten .nud / metal.nud is the original with each texture id mapped as its folder's .nut was (the metal
    repair aside), nothing else changed;
  - over the whole install with the package on top: no id shared by two folders with different pictures (vanilla bases
    too, --vanilla), every drawn mesh's texture in its own folder's .nut, each port's ids in its range (check() clean).

  python3 tools/fighter_texture_ids_test.py [--package ZIP PKG [PKG...]] [--vanilla DIR ...]
"""
import argparse
import os
import struct
import sys
import tempfile
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fighter_texture_ids as tx  # noqa: E402
import nud  # noqa: E402
import nut  # noqa: E402

FAIL = []


def ok(cond, what):
    print('%s %s' % ('ok  ' if cond else 'FAIL', what))
    if not cond:
        FAIL.append(what)


def decode_all(data):
    """[(id, RGBA)] of every texture of a .nut (NTWU), in file order"""
    with tempfile.NamedTemporaryFile(suffix='.nut', delete=False) as f:
        f.write(data)
    try:
        d, texs = nut.load(f.name)
        return [(t.tex_id, nut.decode(d, t)) for t in texs]
    finally:
        os.unlink(f.name)


# ------------------------------------------------------------------ unit
def _img(seed, w=8, h=8):
    r = np.random.RandomState(seed)
    return r.randint(0, 256, (h, w, 4)).astype(np.uint8)


def _material(ids):
    m = nud.Material(flags=0x9A011063, src=0, dst=0)
    m.textures = [dict(hash=t, map_mode=0, wrap_s=1, wrap_t=1, min_f=3, mag_f=2, mip=6, unk=0, unk2=0) for t in ids]
    m.props = [('NU_materialHash', [0.0, 0, 0, 0])]
    return m


def _nud(ids_per_mesh):
    meshes = []
    for k, ids in enumerate(ids_per_mesh):
        p = nud.Polygon()
        p.pos = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], np.float64) + k
        p.nrm = np.tile([0.0, 0.0, 1.0], (4, 1))
        p.col = np.full((4, 4), 127)
        p.uvs = [np.array([[0, 0], [1, 0], [0, 1], [1, 1]], np.float64)]
        p.idx = np.array([0, 1, 2, 1, 3, 2])
        p.materials = [_material(ids)]
        meshes.append(nud.Mesh('mesh%d' % k, [p], bone=0, bind=0))
    return nud.write(meshes)


def _mta_with_pattern(default, keys):
    """a one-material MTA4 (tools/mta.py's writer) with a texture pattern appended (Smash Forge MTA.cs: default id,
    key count, key offset, frame count - 1, 0; keys (texture id, frame))"""
    import mta
    d = bytearray(mta.write(10, [dict(name='m', hash=0x1234, props=[dict(name='NU_finalColorGain',
                                                                       values=[[1, 1, 1, 1]] * 10)])]))
    e = struct.unpack_from('>I', d, 0x38)[0]
    po = len(d)
    d += struct.pack('>I', po + 4)
    ko = po + 4 + 20
    d += struct.pack('>iIIIi', default, len(keys), ko, 9, 0)
    for t, fr in keys:
        d += struct.pack('>ii', t, fr)
    d[e + 16] = 1
    struct.pack_into('>I', d, e + 20, po)
    return bytes(d)


def unit():
    tx_reg = tx.registry
    tx.registry = lambda: {'zz': dict(kind='0x50', base='0x40D00000', articles=['arrow'])}
    try:
        old = tx.OLD_PORT_BASE
        files = {}

        def put(rel, data):
            files[rel] = (lambda data=data: data)

        for c in (0, 1):
            imgs = [(old + k, 0x1A, _img(10 * c + k)) for k in range(3)]
            put('fighter/zz/model/body/c%02d/model.nut' % c, nut.write_ntwu(imgs))
            put('fighter/zz/model/body/c%02d/model.nud' % c, _nud([[old, old + 1], [old + 1, 0x10080000]]))
            # metal.nud: its metal texture (old + 2, unused by model.nud) named old + 3, as Sephiroth's tests 79 - 82
            put('fighter/zz/model/body/c%02d/metal.nud' % c, _nud([[old + 3, old + 1]]))
            put('fighter/zz/model/body/c%02d/model.mta' % c, _mta_with_pattern(old, [(old, 0), (old + 1, 5)]))
            # l00: a copy of c00; l01: an older .nut (other pictures)
            low = imgs if c == 0 else [(old + k, 0x1A, _img(99 + k)) for k in range(3)]
            put('fighter/zz/model/body/l%02d/model.nut' % c, nut.write_ntwu(low))
            put('fighter/zz/model/body/l%02d/model.nud' % c, _nud([[old, old + 1]]))
        for c in (0, 1):
            put('fighter/zz/model/arrow/c%02d/model.nut' % c, nut.write_ntwu([(old + 0xF000, 0x1A, _img(50))]))
            put('fighter/zz/model/arrow/c%02d/model.nud' % c, _nud([[old + 0xF000]]))
        # another port with the same old ids (different pictures), and a base copy (vanilla ids) left alone
        put('fighter/yy/model/body/c00/model.nut', nut.write_ntwu([(old, 0x1A, _img(77))]))
        put('fighter/zz/model/fireball/c00/model.nut', nut.write_ntwu([(0x40115801, 0x1A, _img(5))]))
        before = tx.check(files, ports={'zz'})
        ok(any(c == 'T1 texture-clash' for _s, c, _m in before), 'before: the shared ids clash')
        ok(any(c == 'T2 texture-ref' and 'metal.nud' in m for _s, c, m in before), 'before: metal.nud\'s texture missing')
        ok(any(c == 'T1 texture-range' for _s, c, _m in before), 'before: ids outside the range')
        out, maps = tx.reid('zz', files, log=lambda *a: None, add_articles=False)
        new = dict(files)
        for rel, data in out:
            new[rel] = (lambda data=data: data)
        new.pop('fighter/yy/model/body/c00/model.nut')
        m = {f.split('model/', 1)[1]: v for f, v in maps.items()}
        ok(m['body/c00'][old] == 0x40D00000 and m['body/c01'][old] == 0x40D00400, 'body cNN at base + 0x400 x NN')
        ok(m['body/l00'] == {k: v for k, v in m['body/c00'].items() if k != old + 3}, 'l00 (a copy of c00) shares its ids')
        ok(m['body/l01'][old] == 0x40D02400, 'l01 (other pictures) at base + 0x2000 + 0x400')
        ok(m['arrow/c00'][old + 0xF000] == 0x40D04800 and m['arrow/c01'] == m['arrow/c00'],
           'article at base + 0x4800, its costumes sharing one picture share ids')
        ok('fireball/c00' not in m, 'a base copy (vanilla ids, base pictures) keeps its ids')
        ok(m['body/c00'][old + 3] == m['body/c00'][old + 2], 'metal.nud\'s missing texture -> the unused one')
        for rel, data in out:
            if rel.endswith('.nut'):
                a, b = decode_all(files[rel]()), decode_all(data)
                ok(all(np.array_equal(x[1], y[1]) for x, y in zip(a, b)) and len(a) == len(b), rel + ' pixels')
        mta_new = dict(out)['fighter/zz/model/body/c01/model.mta']
        words = [w for _a, w in tx.anim_refs(mta_new)]
        ok(words[0] == 0x40D00400 and 0x40D00401 in words and 5 in words, 'model.mta texture pattern re-id\'d')
        after = tx.check(new, ports={'zz'})
        ok(not [x for x in after if x[0] == 'ERROR'], 'after: check clean %s' % [x for x in after if x[0] == 'ERROR'])
        # idempotent
        out2, _ = tx.reid('zz', new, log=lambda *a: None, add_articles=False)
        ok(not out2, 'a second rewrite changes nothing')
    finally:
        tx.registry = tx_reg


# ------------------------------------------------------------------ package
def package(zip_path, pkgs, vanilla_dirs):
    inst = tx.overlay(pkgs)
    z = zipfile.ZipFile(zip_path)
    import port_check
    rels = {port_check.Install._norm(n): n for n in z.namelist() if not n.endswith('/')}
    rels.pop(None, None)
    pkg = {r: (lambda n=n: z.read(n)) for r, n in rels.items()}
    maps = {}
    nuts = sorted(r for r in pkg if r.endswith('model.nut'))
    n_tex = 0
    bad = []
    for r in nuts:
        old, new = inst[r](), pkg[r]()
        a, b = decode_all(old), decode_all(new)
        n_tex += len(a)
        same = len(a) == len(b) and all(np.array_equal(x[1], y[1]) for x, y in zip(a, b))
        diff = [i for i in range(len(old)) if old[i] != new[i]]
        at = {t[1] + k for t in tx.nut_textures(new) for k in range(4)}
        if not same or len(old) != len(new) or not set(diff) <= at:
            bad.append(r)
        maps[r.rsplit('/', 1)[0]] = {x[0]: y[0] for x, y in zip(a, b)}
    ok(not bad, '%d rewritten .nut (%d textures): pixels identical, only the ids changed %s' % (len(nuts), n_tex,
                                                                                               bad[:3]))
    bad, metal = [], 0
    nuds = sorted(r for r in pkg if r.endswith('.nud'))
    for r in nuds:
        folder = r.rsplit('/', 1)[0]
        old, new = inst[r](), pkg[r]()
        ro, rn = tx.nud_refs(old), tx.nud_refs(new)
        mp = maps.get(folder, {})
        have = set(mp.values())
        for (a1, t1, _m1, _d1), (a2, t2, _m2, _d2) in zip(ro, rn):
            want = mp.get(t1, t1)
            if a1 != a2 or (t2 != want and not (r.endswith('metal.nud') and t1 not in mp and t2 in have)):
                bad.append('%s %08X -> %08X' % (r, t1, t2))
            elif t2 != want:
                metal += 1
        changed = [i for i in range(len(old)) if old[i] != new[i]]
        at = {a + k for a, _t, _m, _d in rn for k in range(4)}
        if len(old) != len(new) or not set(changed) <= at:
            bad.append(r + ' (bytes outside the texture ids)')
    ok(not bad, '%d rewritten .nud / metal.nud: every reference mapped as its .nut, nothing else changed (%d metal '
       'references repaired) %s' % (len(nuds), metal, bad[:3]))
    full = dict(inst)
    full.update(pkg)
    rep = tx.check(full, vanilla=tx.vanilla_digests(vanilla_dirs))
    errs = [x for x in rep if x[0] == 'ERROR']
    for x in errs[:10]:
        print('   ', x)
    fl = tx.folders(full)
    ids = sum(len(tx.nut_textures(fs['model.nut']())) for fs in fl.values() if 'model.nut' in fs)
    ok(not errs, 'install + package: %d model folders, %d textures: no clash, every drawn texture in its own .nut, '
       'ports in range' % (len(fl), ids))
    rep0 = tx.check(inst, vanilla=tx.vanilla_digests(vanilla_dirs))
    ok(any(x[1] == 'T1 texture-clash' for x in rep0), 'the install without the package: the clash is found (%d errors)'
       % sum(1 for x in rep0 if x[0] == 'ERROR'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--package', nargs='+', metavar='ZIP PKG')
    ap.add_argument('--vanilla', action='append', default=[])
    a = ap.parse_args()
    unit()
    if a.package:
        package(a.package[0], a.package[1:], a.vanilla)
    print('\n%s' % ('ALL OK' if not FAIL else '%d FAILED' % len(FAIL)))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
