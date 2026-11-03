#!/usr/bin/env python3
"""Differential test of tools/ult_to_latte.py: every vertex program of a fighter's Ultimate effects run two
ways on the same random particles: Ultimate's own (the translated GLSL in tools/mx_exec.py) and the lowered
Latte program (assembled by latte-asm, run by tools/latte_exec.py), comparing gl_Position and every output.

  python3 tools/ult_to_latte_test.py pzenigame [--only N,..] [--n 256] [--keep DIR]

The baked buffers are the emitter's own (c9 its static block, c13 its CSDP, c16 / c12 as fx_render feeds
them); c8 (view) and c10 (dynamic) are random and given to the Latte program as constant buffers 1 / 3 in
the same word layout (identity mode), or as eft's own blocks and streams (eft mode). Particles: birth and life spread
around the time so both the live and the dead-particle paths run; the other attributes random."""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import eft2_resolve  # noqa: E402
import latte_exec  # noqa: E402
import mx_exec  # noqa: E402
import ult_shader  # noqa: E402
import ult_to_latte  # noqa: E402
import vfxb  # noqa: E402

# Maxwell's FFMA rounds once, the Latte ALU's MULADD_IEEE twice (it has no fused multiply-add): the reference
# runs Ultimate's program unfused, the way the lowered one can. Fused, about 1 particle in 1000 of 4 programs
# differed by ~5e-4 relative, where the random view matrices cancel (z ~ 9e5); unfused they agree.
mx_exec.SHIM = mx_exec.SHIM.replace('return std::fmaf(a, b, c);', 'volatile float p = a * b; return p + c;')
assert 'volatile float p' in mx_exec.SHIM


def all_emitters_of(eff, si):
    def walk(es):
        for e in es:
            yield e
            yield from walk(e.get('children', []))
    yield from walk(eff.emitters(si))


def all_emitters(eff):
    def walk(es):
        for e in es:
            yield e
            yield from walk(e.get('children', []))
    for si in range(len(eff.sets)):
        yield from walk(eff.emitters(si))


def particles(rng, prog, n, time):
    A = rng.uniform(-1, 1, (n, 16, 4)).astype(np.float32)
    slot = prog.inputs
    if 'sysPosAttr' in slot:
        A[:, slot['sysPosAttr'], :2] = rng.choice([-0.5, 0.5], (n, 2))
        A[:, slot['sysPosAttr'], 2:] = (0, 1)
    for nm in ('sysTexCoordAttr', 'sysVertexColor0Attr', 'sysRandomAttr'):
        if nm in slot:
            A[:, slot[nm]] = rng.uniform(0, 1, (n, 4))
    if 'sysScaleAttr' in slot:
        A[:, slot['sysScaleAttr']] = rng.uniform(0.2, 2, (n, 4))
    if 'sysLocalPosAttr' in slot:
        A[:, slot['sysLocalPosAttr'], :3] = rng.uniform(-10, 10, (n, 3))
        A[:, slot['sysLocalPosAttr'], 3] = rng.integers(1, 40, n)            # life
    if 'sysLocalVecAttr' in slot:
        A[:, slot['sysLocalVecAttr'], 3] = time - rng.uniform(0, 45, n)       # birth
    if 'sysInitRotateAttr' in slot:
        A[:, slot['sysInitRotateAttr']] = rng.uniform(-3.2, 3.2, (n, 4))
    return A


def camera(rng):
    """c8 as a camera makes it: an orthonormal view (turn + translation), a perspective projection, their
    product, the billboard rows (the view's turn transposed), the eye; random 4 x 4s (phase 1's first runs)
    are near singular and blow rounding up"""
    c8 = np.zeros(80, np.float32)
    q, _r = np.linalg.qr(rng.normal(size=(3, 3)))
    view = np.eye(4)
    view[:3, :3], view[:3, 3] = q, rng.uniform(-5, 5, 3) + (0, 0, -60)
    f, near, far = 1 / np.tan(np.radians(rng.uniform(20, 40))), 1.0, 10000.0
    proj = np.array([[f, 0, 0, 0], [0, f * 1.7, 0, 0], [0, 0, -(far + near) / (far - near), -2 * far * near / (far - near)],
                     [0, 0, -1, 0]])
    c8[0:16], c8[16:32], c8[32:48] = view.ravel(), proj.ravel(), (proj @ view).ravel()
    c8[48:60] = np.c_[q.T, np.zeros(3)].ravel()
    eye = -q.T @ view[:3, 3]
    c8[64:67], c8[68:71] = q[2], eye
    c8[72:76] = (near, far, near * far, far - near)
    return c8


def blocks(rng, e, time):
    c8 = camera(rng)
    c10 = rng.uniform(-1, 1, 48).astype(np.float32)
    c10[0:8] = rng.uniform(0, 1, 8)
    c10[8:12] = (time, 0, 0, 1.0)
    c10[12] = rng.uniform(0.5, 1)
    c10[13:16] = rng.uniform(0.5, 2, 3)
    c16 = np.zeros(32, np.float32)
    c16[[0, 4, 5, 6, 8, 10, 18]] = 1.0
    csdp = bytes.fromhex(e['subsections'].get('CSDP', ''))
    c13 = np.frombuffer(csdp[:len(csdp) // 4 * 4], np.uint32) if csdp else np.zeros(4, np.uint32)
    c9 = np.frombuffer(eft2_resolve.static_block(e), np.uint32)
    return {8: c8, 9: c9, 10: c10, 16: c16, 13: c13, 12: np.zeros(32, np.uint32)}


def close(a, b):
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    both_nan = np.isnan(a) & np.isnan(b)
    ok = np.abs(a - b) <= 1e-4 + 2e-4 * np.maximum(np.abs(a), np.abs(b))
    ok |= both_nan | ((a == b) & np.isinf(a))
    return ok


QUAD = np.array([[-0.5, 0.5], [0.5, 0.5], [0.5, -0.5], [-0.5, -0.5]], np.float32)   # Ultimate's, vertex ids 0 - 3


def frame(rng, n=None):
    """3 x 4 rows (a turn x a scale 0.5 - 2, a translation): emitter matrices that invert well"""
    shape = (n,) if n else ()
    q, _r = np.linalg.qr(rng.normal(size=shape + (3, 3)))
    m = q * rng.uniform(0.5, 2, shape + (1, 3))
    return np.concatenate([m, rng.uniform(-10, 10, shape + (3, 1))], -1).astype(np.float32)


def eft_inputs(prog, A, cbs, zratio, low, quad):
    """eft's streams and blocks for the same particles (the inverse of ult_to_latte.EFT_ATTRIBUTES / eft_cb):
    world places / velocities = the program's matrix (sysEmtMat or c10's) x local (+ translation); a quad's
    corners as eft's (w 0) with Ultimate's texture coordinates and vertex ids from them. Ultimate's side made
    consistent with what eft can carry (scale z = x x zratio, no plugin attributes)"""
    slot = prog.inputs
    n = len(A)
    time = float(cbs[10][8])
    g = lambda nm: A[:, slot[nm]] if nm in slot else np.zeros((n, 4), np.float32)
    for nm in slot:
        if nm.startswith('sysEmitterPlugin'):
            A[:, slot[nm]] = 0
    if 'sysScaleAttr' in slot:
        A[:, slot['sysScaleAttr'], 2] = A[:, slot['sysScaleAttr'], 0] * np.float32(zratio)
    corner = QUAD[np.arange(n) % 4]
    if quad:
        if 'sysNormalAttr' in slot:
            A[:, slot['sysNormalAttr']] = (0, 0, 1, 0)
        if 'sysPosAttr' in slot:
            A[:, slot['sysPosAttr']] = np.c_[corner, np.zeros(n), np.ones(n)]
        if 'sysTexCoordAttr' in slot:
            uv = np.c_[corner[:, 0] + 0.5, 0.5 - corner[:, 1]]
            A[:, slot['sysTexCoordAttr']] = np.c_[uv, uv]
    elif 'sysPosAttr' in slot:
        A[:, slot['sysPosAttr'], 3] = 1.0
    if low.mat == 'attr':
        M = np.stack([g('sysEmtMat%dAttr' % r) for r in range(3)], 1)                   # [n, 3, 4]
    elif low.mat == 'c10':
        M = np.broadcast_to(cbs[10][16:28].reshape(3, 4), (n, 3, 4))
    else:
        M = np.broadcast_to(np.c_[np.eye(3), np.zeros(3)].astype(np.float32), (n, 3, 4))
    world = lambda v, t: np.einsum('nij,nj->ni', M[:, :, :3], v[:, :3]) + (M[:, :, 3] if t else 0)
    pos, vec, rnd, scl = g('sysLocalPosAttr'), g('sysLocalVecAttr'), g('sysRandomAttr'), g('sysScaleAttr')
    diff = g('sysLocalDiffAttr')
    st = {'v_inPos': np.c_[corner, np.zeros((n, 2))] if quad else g('sysPosAttr'),
          'v_inTexCoord': g('sysTexCoordAttr'), 'v_inColor': g('sysVertexColor0Attr'),
          'v_inNormal': g('sysNormalAttr'),
          'v_inColor0': g('sysColor0Attr'), 'v_inColor1': g('sysColor1Attr'),
          'v_inWldPos': np.c_[world(pos, True), np.float32(time) - vec[:, 3]],
          'v_inVec': np.c_[world(vec, False), rnd[:, 3]],
          'v_inRandom': np.c_[rnd[:, :3], pos[:, 3]],
          'v_inScl': np.c_[scl[:, :2], np.zeros(n), scl[:, 3]],
          'v_inRot': g('sysInitRotateAttr'), 'v_inWldPosDf': np.c_[world(diff, False), diff[:, 3]],
          'v_inEmtMat0': g('sysEmtMat0Attr'), 'v_inEmtMat1': g('sysEmtMat1Attr'), 'v_inEmtMat2': g('sysEmtMat2Attr')}
    c8 = cbs[8].copy()
    c8[74], c8[75] = c8[72] * c8[73], c8[73] - c8[72]
    cbs[8] = c8
    cb1 = np.zeros(88, np.float32)
    cb1[:72] = c8[:72]
    cb1[80:82] = c8[72:74]
    return {k: v.astype(np.float32) for k, v in st.items()}, {1: cb1, 3: cbs[10]}


def is_mesh(e):
    return e['particle']['primitive_id'] != 0xFFFFFFFFFFFFFFFF


def test_program(prog, e, n, seed, keep=None, tag='', mode='identity'):
    rng = np.random.default_rng(seed)
    time = 30.0
    A = particles(rng, prog, n, time)
    cbs = blocks(rng, e, time)
    if 'sysEmtMat0Attr' in prog.inputs:
        F = frame(rng, n)
        for r in range(3):
            A[:, prog.inputs['sysEmtMat%dAttr' % r]] = F[:, r]
    cbs[10][16:28] = frame(rng).ravel()
    zratio = float(rng.uniform(0.5, 2))
    quad = mode == 'eft' and not is_mesh(e)
    consts = {k: [int(x) for x in np.asarray(v).view(np.uint32)] for k, v in cbs.items() if k not in (8, 10)}
    consts[1] = [int(x) for x in np.frombuffer(prog.cdata or b'\0\0\0\0', np.uint32)]
    names = {slot: name for name, slot in prog.inputs.items()}
    low = ult_to_latte.Lowering(prog.glsl, consts, names, mode, zratio, quad=quad).run()
    if mode == 'eft':
        streams, s4cbs = eft_inputs(prog, A, cbs, zratio, low, quad)
    else:
        s4cbs = {1: cbs[8], 3: cbs[10]}
    text = low.text()
    if keep:
        open(os.path.join(keep, '%s.vsh' % tag), 'w').write(text)
    gsh = ult_to_latte.assemble(text)
    vs = latte_exec.VertexProgram(gsh)
    if mode == 'eft':
        cols = [streams[nm] for nm in vs.attributes]
    else:
        loc = {name: slot for slot, name in names.items()}
        cols = [A[:, loc[nm]] for nm in vs.attributes]
    A2 = np.stack(cols, 1).astype(np.float32) if cols else np.zeros((n, 0, 4), np.float32)
    p_l, o_l = vs.run(A2, s4cbs)
    p_u, o_u = prog.run(A, cbs)
    bad = []
    if not close(p_u, p_l).all():
        bad.append('gl_Position')
    for k, l in enumerate(sorted(low.outs)):
        if not close(o_u[:, l], o_l[:, k]).all():
            bad.append('out_attr%d' % l)
    nops = len(low.code)
    return bad, nops, (p_u, p_l, o_u, o_l), low


def test_pixel(prog, e, n, seed, keep=None, tag='', mode='identity'):
    """a pixel program both ways: random inputs (UV-like ranges), random 16 x 16 textures on every unit it
    samples (each wrap mode in turn), the emitter's baked buffers; equal when both keep or discard a pixel
    and the kept ones' rgba agree"""
    rng = np.random.default_rng(seed)
    cbs = blocks(rng, e, 30.0)
    if mode == 'eft':
        # c10 as a converted emitter's (ult_to_latte eft_cb with colours: alpha / call scale 1, the unmapped words 0)
        c10 = cbs[10].copy()
        c10[9:11], c10[12:16], c10[28:32], c10[44:] = 0, 1, 0, 0
        cbs[10] = c10
    consts = {k: [int(x) for x in np.asarray(v).view(np.uint32)] for k, v in cbs.items() if k not in (8, 10)}
    consts[1] = [int(x) for x in np.frombuffer(prog.cdata or b'\0\0\0\0', np.uint32)]
    eft = mode == 'eft'
    # eft mode: frag0 clamped, display-encoded, premultiplied, x a random u_nwHdrRange (CB9 floats 32 - 35)
    smap = ult_shader.sampler_map(prog.samplers)
    low = ult_to_latte.Lowering(prog.glsl, consts, mode=mode, encode='display' if eft else None, premultiply=eft,
                                samplers=smap, colours=[1.0] * 8 if eft else None).run()
    text = low.text()
    if keep:
        open(os.path.join(keep, '%s.psh' % tag), 'w').write(text)
    cb9 = np.zeros(64, np.float32)
    cb9[32:36] = rng.uniform(0.5, 2, 4)
    gsh = ult_to_latte.assemble(text, 'ps')
    ps = latte_exec.PixelProgram(gsh)
    h = ult_to_latte.ps_header(gsh)
    want_smp = sorted({srcs[0] for op, _d, srcs in low.code if op in ult_to_latte.TEX_OPS})
    locs = sorted(low.ins)
    ins = np.zeros((n, 8, 4), np.float32)
    ins[:, locs] = rng.uniform(-0.5, 1.5, (n, len(locs), 4))
    tex = {}
    for k, unit in enumerate(sorted(prog.samplers.values())):
        if smap.get(unit) == 'far':
            tex[unit] = (np.ones((1, 1, 4), np.float32), 0, 0)        # the depth texture as the lowering reads it
        else:
            tex[unit] = (rng.uniform(0, 1, (16, 16, 4)).astype(np.float32), k % 3, (k + 1) % 3)
    o_u = prog.eval(ins, cbs, tex)
    if eft:
        rgb = np.clip(o_u[:, :3], 0, 1) ** np.float32(1 / 2.2) * o_u[:, 3:4]
        o_u[:, :3] = rgb * cb9[32] + cb9[35]
    tex_l = {smap[u]: t for u, t in tex.items() if smap.get(u) != 'far'}
    cb1 = cbs[8]
    if eft:
        cb1 = np.zeros(88, np.float32)               # eft's view block: vp (near, far) at 80 (eft_cb)
        cb1[:72], cb1[80:82] = cbs[8][:72], cbs[8][72:74]
    o_l = ps.run(ins[:, locs], {1: cb1, 3: cbs[10], 9: cb9}, tex_l)
    bad = []
    if h['inputs'] != sorted(low.ins):
        bad.append('header inputs %s' % h['inputs'])
    if [(nm, loc) for nm, _t, loc in h['samplers']] != [(ult_to_latte.SAMPLER_NAMES.get(t, 'textureSampler%d' % t), t)
                                                         for t in want_smp]:
        bad.append('header samplers %s' % h['samplers'])
    if bool(h['db_shader_control'] & 0x40) != low.kills:
        bad.append('header KILL_ENABLE')
    if eft and ('userUniformBlock', 9, 256) not in h['blocks']:
        bad.append('header blocks %s' % h['blocks'])
    if not (o_u[:, 4] == o_l[:, 4]).all():
        bad.append('discard (%d pixels)' % int((o_u[:, 4] != o_l[:, 4]).sum()))
    kept = (o_u[:, 4] == 1) & (o_l[:, 4] == 1)
    if not close(o_u[kept, :4], o_l[kept, :4]).all():
        bad.append('frag0')
    return bad, len(low.code), (o_u, o_l), low


def test_pair(eff, e, idx):
    """the vertex and pixel programs of one emitter as eft will get them: every pixel input has a vertex output of
    its semantic"""
    rng = np.random.default_rng(0)
    cbs = blocks(rng, e, 30.0)
    consts = {k: [int(x) for x in np.asarray(v).view(np.uint32)] for k, v in cbs.items() if k not in (8, 10)}
    vp, pp = mx_exec.Program(eff.vfxb, idx, 'vs'), mx_exec.Program(eff.vfxb, idx, 'ps')
    names = {slot: name for name, slot in vp.inputs.items()}
    cv, cp = dict(consts), dict(consts)
    cv[1] = [int(x) for x in np.frombuffer(vp.cdata or b'\0\0\0\0', np.uint32)]
    cp[1] = [int(x) for x in np.frombuffer(pp.cdata or b'\0\0\0\0', np.uint32)]
    vs = ult_to_latte.assemble(ult_to_latte.lower(vp.glsl, cv, names, 'eft'), 'vs')
    ps = ult_to_latte.assemble(ult_to_latte.lower(pp.glsl, cp, encode='display',
                                                  samplers=ult_shader.sampler_map(pp.samplers)), 'ps')
    missing = set(ult_to_latte.ps_header(ps)['inputs']) - set(ult_to_latte.vs_semantics(vs))
    return ['pixel inputs without a vertex output: %s' % sorted(missing)] if missing else [], len(vs) + len(ps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--only', default='')
    ap.add_argument('--n', type=int, default=256)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--keep', default='')
    ap.add_argument('--mode', default='identity', choices=('identity', 'eft'))
    ap.add_argument('--stage', default='vs', choices=('vs', 'ps', 'pair'))
    ap.add_argument('--common', action='store_true', help="the common sets (ef_common.eff) his scripts use instead")
    a = ap.parse_args()
    import port_sources
    cfg = json.load(open(os.path.join(ROOT, 'fighters', a.name, 'port.json')))
    src = port_sources.load()
    eff = vfxb.Eff(src.eff(cfg['ult']))
    only = {int(x) for x in a.only.split(',') if x}
    emitters = list(all_emitters(eff))
    if a.common:
        # the common sets his scripts call (ef_common.eff): their programs instead
        import ultimate_port
        path = src.find('ult_effects', 'system/common/ef_common.eff') or src.get('ef_common')
        eff = vfxb.Eff(path)
        wanted = {v for v in ultimate_port.common_sets(cfg['effects'].get('common', []), path).values() if v}
        emitters = [e for si, nm in enumerate(eff.sets) if nm in wanted for e in all_emitters_of(eff, si)]
    seen, fails, sizes = {}, [], []
    for e in emitters:
        idx = e['shader']['shader_index']
        if idx in seen or (only and idx not in only):
            continue
        if e['combiner']['shader_type'] == 1:
            continue                    # refraction: the converter keeps its own (Smash 4's distortion pass)
        seen[idx] = True
        try:
            if a.stage == 'pair':
                bad, nops = test_pair(eff, e, idx)
                sizes.append(nops)
                if bad:
                    fails.append(idx)
                    print('pair %d %s: %s' % (idx, e['name'], ', '.join(bad)), flush=True)
                continue
            prog = mx_exec.Program(eff.vfxb, idx, a.stage)
            if a.stage == 'ps':
                bad, nops, _r, _low = test_pixel(prog, e, a.n, a.seed, a.keep or None, 'ps_%d' % idx, a.mode)
            else:
                bad, nops, _r, _low = test_program(prog, e, a.n, a.seed, a.keep or None, 'vs_%d' % idx, a.mode)
        except Exception as ex:  # noqa: BLE001
            bad, nops = ['error: %s' % str(ex).splitlines()[0][:200]], 0
        sizes.append(nops)
        if bad:
            fails.append(idx)
            print('%s %d %s: %s' % (a.stage, idx, e['name'], ', '.join(bad)), flush=True)
    print('%d programs, %d pass, %d fail; Latte operations median %d, max %d'
          % (len(seen), len(seen) - len(fails), len(fails), int(np.median(sizes)) if sizes else 0, max(sizes or [0])))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
