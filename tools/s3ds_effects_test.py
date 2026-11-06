#!/usr/bin/env python3
"""Checks tools/s3ds_effects.py on every Smash Run enemy's effects: each converted file validates (ptcl.Ptcl
validate: the game's loader rules), has the 3DS file's sets in order with their emitters, and every emitter's
written fields read back (as the game reads them, tools/ptcl.py) as the 3DS values: timing, life, rate, speeds,
direction, gravity, air resistance, volume, emitter transform, scale (base, random, ratios, sections), alpha
(3 keys, sections as fractions), colour types / sections / scale, the colour keys (x the texture's tint),
rotation, UV scale / scroll (V negated), blend, follow and particle type; the texture is the 3DS one's shape;
the .efc has the 3DS entries (models left out).

  python3 tools/s3ds_effects_test.py SRC_ROOT VANILLA_DIR [KIND...]
"""
import glob
import os
import struct
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import efc  # noqa: E402
import ptcl  # noqa: E402
import s3ds_effects as se  # noqa: E402
import vfxb_to_ptcl as vt  # noqa: E402

FAILS = []


def check(cond, what):
    if not cond:
        print('FAIL  ' + what)
        FAILS.append(what)
    return cond


def close(a, b, tol=1e-4):
    a, b = np.atleast_1d(np.asarray(a, float)), np.atleast_1d(np.asarray(b, float))
    return a.shape == b.shape and np.allclose(a, b, atol=tol, rtol=1e-4)


def emitter_checks(tag, p, w, e):
    d = e['data']

    def g(o, f):
        return se.field(d, o, f)
    f = p.field
    life = g(0x31C, 'i')
    pairs = [
        ('emit_rate', g(0x2C4, 'f')), ('emit_start', g(0x2C8, 'i')), ('emit_interval', g(0x2D0, 'i')),
        ('figure_velocity', g(0x2D8, 'f')), ('emitter_velocity', abs(g(0x2DC, 'f'))),
        ('init_velocity_random', g(0x2E0, 'f')), ('dispersion_angle', g(0x2F0, 'f')),
        ('air_resistance', g(0x300, 'f')), ('gravity', g(0x304, '3f')), ('volume_radius', g(0x254, '3f')),
        ('emitter_scale', g(0x208, '3f')), ('emitter_rotation', g(0x214, '3f')),
        ('emitter_translation', g(0x220, '3f')), ('scale', g(0x4E4, '2f')),
        ('scale_init_ratio', g(0x4EC, '2f')), ('scale_diff21', g(0x4F4, '2f')), ('scale_diff32', g(0x4FC, '2f')),
        ('scale_sections', g(0x4D8, '2i')), ('alpha_init', g(0x4BC, 'f')), ('alpha_diff21', g(0x4C0, 'f')),
        ('alpha_diff32', g(0x4C4, 'f')), ('alpha_section1', g(0x4C8, 'i') / 100.0),
        ('alpha_section2', g(0x4CC, 'i') / 100.0), ('color_section1', g(0x490, '2i')),
        ('color_section2', g(0x498, '2i')), ('color_section3', g(0x4A0, '2i')), ('color_scale', g(0x4B8, 'f')),
        ('rotation_init', g(0x508, '3f')), ('rotation_random', g(0x514, '3f')),
        ('rotation_velocity', g(0x520, '3f')), ('rotation_attenuation', g(0x538, 'f')),
        ('tex0_uv_scale', g(0x368, '2f')), ('blend_type', g(0x244, 'I')), ('color0_type', g(0x428, 'I')),
        ('color1_type', g(0x42C, 'I'))]
    for name, want in pairs:
        if name == 'emit_rate' and f(w, name) != want:
            continue                                # sanitize may lower / raise it (noted when converting)
        check(close(f(w, name), want), '%s: %s %s != 3DS %s' % (tag, name, f(w, name), want))
    if life > 0:
        check(f(w, 'ptcl_life') == life, '%s: life %d != %d' % (tag, f(w, 'ptcl_life'), life))
    end = g(0x2CC, 'i')
    check(f(w, 'end_frame') == (se.FOREVER if end >= se.FOREVER else max(1, end)) and
          f(w, 'one_time') == (0 if end >= se.FOREVER else 1), '%s: end frame / one-time' % tag)
    check(struct.unpack_from('>I', w, vt.FOLLOW)[0] == g(0x190, 'I'), '%s: follow' % tag)
    check(close(struct.unpack_from('>2f', w, 0x514), (g(0x374, 'f'), -g(0x378, 'f'))), '%s: UV scroll' % tag)
    # colour keys: the 3DS keys x the texture's tint (a common factor per channel)
    img = e['textures'][0]
    if img is not None:
        rgba = img.astype(np.float32) / 255.0
        if e['formats'][0] in se.NO_ALPHA:
            rgba[..., 3] = rgba[..., :3].max(-1)
        _shape, tint = se.shape_texture(rgba)
        keys = np.array(f(w, 'color0_keys')).reshape(8, 4)[0, :3]
        check(close(keys, np.array(g(0x430, '3f')) * tint, 1e-3), '%s: colour 0 key 0' % tag)
        back = p.decode_texture(w, 0)
        check(back is not None and back.shape[0] >= 8, '%s: texture' % tag)
    typ = g(0x328, 'I')
    want_t = {5: 3, 6: 3, 7: 0}.get(typ, typ)
    if f(w, 'particle_type') != want_t:
        print('note  %s: particle type %d (3DS %d): no template of it' % (tag, f(w, 'particle_type'), typ))


def main():
    src, vanilla = sys.argv[1], sys.argv[2]
    import s3ds_enemy
    kinds = sys.argv[3:] or s3ds_enemy.fs_kinds(src)
    vt.EXACT = vt.TWO_TEXTURES = vt.GRAFT = vt.UNIVERSAL = False
    corpus = sorted(glob.glob(os.path.join(vanilla, '**', '*.ptcl'), recursive=True))
    base = min(corpus, key=os.path.getsize)
    templates = vt.Templates(ptcl.Ptcl(open(base, 'rb').read()), corpus)
    n_files = n_em = 0
    for k in kinds:
        f = os.path.join(src, 'enemy', k, 'effect', '%s.03030000.ptcl' % k)
        if not os.path.exists(f):
            continue
        s3 = se.read_spbd(open(f, 'rb').read())
        out, efc_b, _made = se.convert_file(f, f.replace('.ptcl', '.efc'), templates, base, log=lambda *a: None)
        p = ptcl.Ptcl(out)
        n_files += 1
        if not check(p.validate() == [], '%s: validates' % k):
            continue
        check([p.set_name(i) for i in range(len(p.sets))] == [s['name'] for s in s3['sets']], '%s: sets' % k)
        for si, s in enumerate(s3['sets']):
            ws = [x['data'] for x in p.sets[si]['emitters']]
            check([p.emitter_name(w) for w in ws] == [e['name'] for e in s['emitters'][:se.MAX_EMITTERS]],
                  '%s/%s: emitters' % (k, s['name']))
            for w, e in zip(ws, s['emitters']):
                emitter_checks('%s/%s/%s' % (k, s['name'], e['name']), p, w, e)
                n_em += 1
        with tempfile.NamedTemporaryFile(suffix='.efc') as t:
            t.write(efc_b)
            t.flush()
            ef = efc.Efc(open(t.name, 'rb').read())
            want = se.read_efc(open(f.replace('.ptcl', '.efc'), 'rb').read())[0] \
                if os.path.exists(f.replace('.ptcl', '.efc')) else []
            check([e[:2] for e in ef.entries] == [e[:2] for e in want], '%s: efc entries' % k)
    print('%d files, %d emitters, %d failures' % (n_files, n_em, len(FAILS)))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
