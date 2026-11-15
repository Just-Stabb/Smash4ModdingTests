#!/usr/bin/env python3
"""Supamario's fake-glow halo test (both XV2 moves: the Super God Fist and Core Breaker share his effect bank): the
current combined build's effect files with tools/xv2_smash_fx.py's halos added, at several strengths.

  python3 -I tools/supamario_halo_test.py BUILD_OUT OUT_DIR --cor 2070_FIT_COR_DIR --csg 002_GOK_CSG_DIR
          --cmn VFX_CMN_DIR [--alpha 0.25,0.45,0.7] [--size 2.5]

BUILD_OUT: tools/supamario_corebreaker_build.py's OUT_DIR (God Fist v17 + Core Breaker). Writes
OUT_DIR/halo_<alpha>/fighter/supamario/effect/supamario/supamario.010d0000.{ptcl,efc} and
script/animcmd/body/effect.bin (the attackdash / specialhi / specialairhi calls also call the halo sets that didn't
fit in their own set, and the model halos), and OUT_DIR/halo_report.json.

Glowing: an emitter whose XV2 material has its Glare flag on (not a refraction material, not hidden); the models
`EffSupamarioCbCrg` (the charge orb), `EffSupamarioCbFire` (the fist's flame, looping) and `EffSupamarioGfCsgBas`
(the God Fist's aura) each get a soft particle at their centre, MODEL_COLOURS (their materials' hue).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import xv2_smash_fx as FX  # noqa: E402

BASE = 'supamario.010d0000'
# model -> (halo colour, looping, its glowing core's radius in model units or None: the whole model's). The fire
# cone (11 long) and the God Fist's aura (its wind swirls reach 27) glow at their bulb / orb (~3 / ~2.5), not over
# their whole length
MODEL_COLOURS = {'EffSupamarioCbCrg': ((0.3, 0.9, 1.0), False, None),
                 'EffSupamarioCbFire': ((0.2, 0.6, 1.0), True, 3.0),
                 'EffSupamarioGfCsgBas': ((1.0, 0.55, 0.15), False, 2.5)}
SCRIPTS = ('attackdash', 'specialhi', 'specialairhi')


def model_radius(folder):
    import numpy as np
    import xv2_to_nud as N
    meshes, _tex, _o, _b, _a = N._load_folder(folder)
    return float(max(np.linalg.norm(p.pos, axis=1).max() for m in meshes for p in m.polygons))


def glowing_sets(p, packages):
    """{set index: [glowing emitter indices]} for the sets converted from each package ({set name prefix: dir})"""
    import xv2vfx
    out = {}
    tables = {}
    import tempfile
    for pre, d in packages.items():
        mats = {}
        eepks = [f for f in os.listdir(d) if f.lower().endswith('.eepk')]
        with tempfile.TemporaryDirectory() as tmp:
            if len(eepks) > 1:                      # vfx/cmn: BTL_CMN.eepk alone, as the God Fist build reads it
                for fn in os.listdir(d):
                    if not fn.lower().endswith('.eepk') or fn == 'BTL_CMN.eepk':
                        os.symlink(os.path.abspath(os.path.join(d, fn)), os.path.join(tmp, fn))
                d = tmp
            table = FX.material_table(xv2vfx.load_package(d, strict=False))
        for _emp, t in table.items():
            for en, m in t.items():
                mats.setdefault(en, m)
        tables[pre] = mats
    for si in range(len(p.sets)):
        name = p.set_name(si)
        pre = next((k for k in tables if name.startswith(k)), None)
        if pre is None:
            continue
        ks = []
        for k, em in enumerate(p.sets[si]['emitters']):
            d = em['data']
            if d is None or p.field(d, 'alpha_init') <= 0:
                continue
            m = tables[pre].get(p.emitter_name(d))
            if m and m[2].get('Glare') and not FX.is_refraction(m[1], m[0]):
                ks.append(k)
        if ks:
            out[si] = ks
    return out


def build(build_out, out_dir, packages, alpha):
    import efc
    import ptcl
    fdir = os.path.join(build_out, 'fighter', 'supamario')
    fx = os.path.join(fdir, 'effect', 'supamario')
    p = ptcl.Ptcl(open(os.path.join(fx, BASE + '.ptcl'), 'rb').read())
    e = efc.Efc(open(os.path.join(fx, BASE + '.efc'), 'rb').read())
    glow = glowing_sets(p, packages)
    cache = {}
    template = None
    for si, ks in glow.items():
        for k in ks:
            d = p.sets[si]['emitters'][k]['data']
            if template is None and p.field(d, 'particle_type') == 0:
                template = bytes(d)
    comp = FX.add_halos(p, e, glow, alpha, cache)
    mapping = {0x03410000 | i: [0x03410000 | j for j in js] for i, js in comp.items()}
    models = {}
    for name, (rgb, loop, core) in MODEL_COLOURS.items():
        mi = e.models.index(name) + 1
        ent = next(i for i, x in enumerate(e.entries) if x[2] == mi)
        folder = os.path.join(fx, 'model', name)
        import omo
        frames = omo.Omo(open(os.path.join(folder, 'model.omo'), 'rb').read()).frames
        r = core if core is not None else model_radius(folder)
        em = FX.model_halo_emitter(p, template, r, rgb, frames, loop, alpha, cache)
        hs = p.new_set('PtcSupamarioHalo' + name[len('EffSupamario'):], [em])
        hid = e.add(hs + 1)
        mapping.setdefault(0x03410000 | ent, []).append(0x03410000 | hid)
        models[name] = {'radius': round(r, 2), 'frames': frames, 'loop': loop, 'halo_id': '0x%08X' % (0x03410000 | hid)}
    data = p.build()
    assert ptcl.Ptcl(data).validate() == []
    od = os.path.join(out_dir, 'fighter', 'supamario', 'effect', 'supamario')
    os.makedirs(od, exist_ok=True)
    open(os.path.join(od, BASE + '.ptcl'), 'wb').write(data)
    open(os.path.join(od, BASE + '.efc'), 'wb').write(e.build())
    f = acmd.ACMDFile.load(os.path.join(fdir, 'script', 'animcmd', 'body', 'effect.bin'))
    calls = {}
    for n in SCRIPTS:
        s = f.script(n)
        new = FX.add_halo_calls(s, mapping)
        calls[n] = len(new) - len(s)
        f.scripts[acmd.crc(n)] = new
    sd = os.path.join(out_dir, 'fighter', 'supamario', 'script', 'animcmd', 'body')
    os.makedirs(sd, exist_ok=True)
    f.save(os.path.join(sd, 'effect.bin'))
    return {'alpha': alpha, 'size': FX.HALO_SIZE, 'glowing_emitters': sum(len(v) for v in glow.values()),
            'companion_sets': len(comp), 'models': models, 'calls_added': calls, 'ptcl_bytes': len(data)}, p, glow


def main():
    a = sys.argv[1:]
    opts = {}
    for k in ('--cor', '--csg', '--cmn', '--alpha', '--size'):
        if k in a:
            i = a.index(k)
            opts[k] = a[i + 1]
            del a[i:i + 2]
    if len(a) != 2:
        sys.exit(__doc__)
    if '--size' in opts:
        FX.HALO_SIZE = float(opts['--size'])
    packages = {'PtcSupamarioCb': opts['--cor'], 'PtcSupamarioGfCsg_': opts['--csg'], 'PtcSupamarioGfBtl_': opts['--cmn']}
    rep = []
    for al in [float(x) for x in opts.get('--alpha', '0.25,0.45,0.7').split(',')]:
        r, _p, _g = build(a[0], os.path.join(a[1], 'halo_%g' % al), packages, al)
        rep.append(r)
        print(json.dumps(r))
    with open(os.path.join(a[1], 'halo_report.json'), 'w') as fh:
        json.dump(rep, fh, indent=1)


if __name__ == '__main__':
    main()
