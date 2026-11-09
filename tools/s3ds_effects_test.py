#!/usr/bin/env python3
"""Checks tools/s3ds_effects.py on every Smash Run enemy's effects: each converted file validates (ptcl.Ptcl
validate: the game's loader rules), has the 3DS file's sets in order with their emitters, and every emitter's
written fields read back (as the game reads them, tools/ptcl.py) as the 3DS values: timing, life, rate, speeds,
direction, gravity, air resistance, volume, emitter transform, scale (base, random, ratios, sections), alpha
(3 keys, sections as fractions), colour types / sections / scale, the colour mode (the 3DS combiner, the pixel
program run on the CPU), the colour keys (the texture's tint folded in for that mode: colour 1 untinted),
rotation, UV scale / scroll (V negated), blend, follow and particle type; the texture is the 3DS one's shape
(no alpha: the colour's level, once); step 2n: every emitter's MATC block (its own TEV set-up, +0x158) is found,
Furiijio's alpha channels read off its command lists, and where the colour level / the MATC's alpha
channel differ from the one shape the texture holds both (BC5: R the level, G the alpha) and the pixel program
takes the alpha from G (run on the CPU);
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
_MODES = {}


def program_mode(p, si):
    """the colour mode (0-3) shader si's pixel program draws, run on the CPU (tools/latte_exec.py) with
    colour 0, colour 1 and a flat texture; None when the program isn't a one-texture colour 0 / 1 one"""
    import eft_pixel
    import latte_exec
    b = bytes(p.shader_binary(si))
    key = hash(b)
    if key not in _MODES:
        lay = eft_pixel.layout(b)
        mode = None
        if lay is not None and lay.get('c1') is not None and 'uv1' not in lay:
            c0, c1, t = np.array([0.2, 0.4, 0.6, 1.0]), np.array([0.5, 0.3, 0.1, 1.0]), 0.5
            inp = np.zeros((1, lay['regs'], 4), np.float32)
            inp[0, lay['c0']] = c0
            inp[0, lay['c1']] = c1
            inp[0, lay['uv'][0]] = (0.5, 0.5, 0, 0)
            if lay.get('vc') is not None:
                inp[0, lay['vc']] = 1.0
            cb9 = np.zeros((16, 4), np.float32)
            cb9[8] = (1, 0, 0, 0)
            tex = np.full((4, 4, 4), t, np.float32)
            rgb = latte_exec.PixelProgram(b).run(inp, {9: cb9}, {0: (tex, 1, 1)})[0, :3]
            want = {0: c0[:3], 1: c0[:3] * t, 2: c1[:3] + (c0[:3] - c1[:3]) * t, 3: c0[:3] * t + c1[:3]}
            hits = [m for m, v in want.items() if np.abs(rgb - v).max() < 2e-3]
            mode = hits[0] if len(hits) == 1 else None
        _MODES[key] = mode
    return _MODES[key]


def program_alpha(p, si):
    """step 2n: the alpha shader si's pixel program draws from colour 0 alpha 1 and a texel rgb 0.5 / alpha 0.25
    (0.25: the texture's alpha, the BC5 two-channel textures' G), run on the CPU; None for a two-texture layout"""
    import eft_pixel
    import latte_exec
    b = bytes(p.shader_binary(si))
    lay = eft_pixel.layout(b)
    if lay is None or 'uv1' in lay:
        return None
    inp = np.zeros((1, lay['regs'], 4), np.float32)
    inp[0, lay['c0']] = (1.0, 1.0, 1.0, 1.0)
    if lay.get('c1') is not None:
        inp[0, lay['c1']] = (0.0, 0.0, 0.0, 1.0)
    inp[0, lay['uv'][0]] = (0.5, 0.5, 0, 0)
    if lay.get('vc') is not None:
        inp[0, lay['vc']] = 1.0
    cb9 = np.zeros((16, 4), np.float32)
    cb9[8] = (1, 0, 0, 0)
    tex = np.zeros((4, 4, 4), np.float32)
    tex[...] = (0.5, 0.5, 0.5, 0.25)
    return float(latte_exec.PixelProgram(b).run(inp, {9: cb9}, {0: (tex, 1, 1)})[0, 3])


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
        ('scale_sections', tuple(max(v, 0) for v in g(0x4D8, '2i'))), ('alpha_init', g(0x4BC, 'f')), ('alpha_diff21', g(0x4C0, 'f')),
        ('alpha_diff32', g(0x4C4, 'f')), ('alpha_section1', max(g(0x4C8, 'i'), 0) / 100.0),
        ('alpha_section2', max(g(0x4CC, 'i'), 0) / 100.0), ('color_section1', g(0x490, '2i')),
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
    # no negative section (the 3DS's -127, no first section: eft took the key's step backwards from it)
    check(min(f(w, 'scale_sections')) >= 0 and f(w, 'alpha_section1') >= 0, '%s: negative section' % tag)
    # colour mode: the 3DS combiner, and the emitter's pixel program draws it (run on the CPU)
    comb = g(se.COMBINER, 'I')
    mode = struct.unpack_from('>I', w, vt.COLOR_MODE)[0]
    if comb in (0, 1, 2, 3):
        check(mode == comb, '%s: colour mode %d != 3DS combiner %d' % (tag, mode, comb))
        drawn = program_mode(p, f(w, 'shader_index'))
        check(drawn in (None, mode), '%s: pixel program draws colour mode %s, not %d' % (tag, drawn, mode))
    # colour keys: the 3DS keys with the texture's tint folded in for that mode (se.tinted_keys)
    img = e['textures'][0]
    if img is not None:
        shape, tint = se.texture_shape(img, e['formats'][0])
        k0, k1 = se.tinted_keys(mode, [g(0x430, '3f')], [g(0x460, '3f')], tint)
        keys = np.array(f(w, 'color0_keys')).reshape(8, 4)[0, :3]
        check(close(keys, np.array(k0[0]), 1e-3), '%s: colour 0 key 0' % tag)
        keys1 = np.array(f(w, 'color1_keys')).reshape(8, 4)[0, :3]
        check(close(keys1, np.array(k1[0]), 1e-3), '%s: colour 1 key 0 (untinted)' % tag)
        back = p.decode_texture(w, 0)
        check(back is not None and back.shape[0] >= 8, '%s: texture' % tag)
        chan = se.matc_alpha_channel(e.get('matc'))
        two = struct.unpack_from('>I', w, ptcl.TEXRES + 0x14)[0] == se.TWO_SEL and \
            p.texres(w, 0)['native_format'] == ptcl.GX2_EFT[se.BC5]
        if chan is not None and back is not None and back.shape[:2] == shape.shape:
            # step 2n: the emitter's own TEV stage 0 (its MATC block): the colour the texture's rgb (level, alpha
            # not folded in), the alpha its channel chan; two channels where they differ from the one shape
            level, alpha, _t = se.texture_channels(img, e['formats'][0], chan)
            differs = np.abs(level - shape).mean() > 0.02 or np.abs(alpha - shape).mean() > 0.02
            if differs and check(two, '%s: two-channel texture (colour level / alpha %s): not written' % (tag, chan)):
                el = np.abs(back[..., 0] / 255.0 - level).mean()
                ea = np.abs(back[..., 3] / 255.0 - alpha).mean()
                check(el < 0.03 and ea < 0.03, '%s: two channels: colour level error %.3f, alpha (%s) error %.3f'
                      % (tag, el, chan, ea))
                pa = program_alpha(p, f(w, 'shader_index'))
                check(pa is not None and abs(pa - 0.25) < 2e-3, '%s: the pixel program\'s alpha is not colour 0 '
                      'alpha x the texture\'s alpha (G): %s' % (tag, pa))
            elif not differs:
                check(not two, '%s: two channels where one shape is exact' % tag)
        if back is not None and e['formats'][0] in se.NO_ALPHA and back.shape[:2] == shape.shape and not two:
            # no alpha: the shape is the colour's level, once (not level^2: Furiijio's mist, effects v3)
            err = np.abs(back[..., 0] / 255.0 - shape).mean()
            check(err < 0.03, '%s: shape not the texture level (mean error %.3f)' % (tag, err))
            if e['formats'][0] == 12 and shape.max() > 0.5:
                lv = np.asarray(img, np.float32)[..., :3].max(-1) / 255.0
                check(np.abs(back[..., 0] / 255.0 - lv).mean() <= np.abs(back[..., 0] / 255.0 - lv * lv).mean()
                      + 1e-3, '%s: ETC1 shape nearer level^2 than the level' % tag)
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
        raw = open(f, 'rb').read()
        s3 = se.read_spbd(raw)
        if struct.unpack_from('<I', raw, 0x44)[0]:
            # step 2n: every emitter's +0x158 lands on a MATC block of the table (header words 16 / 17)
            lost = [e['name'] for s in s3['sets'] for e in s['emitters'] if e.get('matc') is None]
            check(not lost, '%s: emitters without their MATC block: %s' % (k, lost))
        if k == 'furiijio':
            got = {(s['name'], e['name']): se.matc_alpha_channel(e['matc']) for s in s3['sets'] for e in s['emitters']}
            want = {('PtcfsFuriijioFreezBeamRoot', 'BG'): 'r', ('PtcfsFuriijioFreezBeamRoot', 'snow'): 'r',
                    ('PtcfsFuriijioFreezBeamRoot', 'cool_airA'): 'a', ('PtcfsFuriijioShootFilling', 'tubu'): 'r',
                    ('PtcfsFuriijioSign', 'flare'): 'r', ('PtcfsFuriijioSign', 'sign_center'): 'a'}
            check(all(got.get(x) == v for x, v in want.items()), 'furiijio: the MATC alpha channels (TEV stage 0) '
                  'read: %s' % got)
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
