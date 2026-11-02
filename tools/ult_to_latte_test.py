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
import ult_to_latte  # noqa: E402
import vfxb  # noqa: E402

# Maxwell's FFMA rounds once, the Latte ALU's MULADD_IEEE twice (it has no fused multiply-add): the reference
# runs Ultimate's program unfused, the way the lowered one can. Fused, about 1 particle in 1000 of 4 programs
# differed by ~5e-4 relative, where the random view matrices cancel (z ~ 9e5); unfused they agree.
mx_exec.SHIM = mx_exec.SHIM.replace('return std::fmaf(a, b, c);', 'volatile float p = a * b; return p + c;')
assert 'volatile float p' in mx_exec.SHIM


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


def blocks(rng, e, time):
    c8 = rng.uniform(-1, 1, 80).astype(np.float32)
    c8[72:76] = (1.0, 10000.0, 10000.0, 9999.0)
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


def eft_inputs(prog, A, cbs, zratio):
    """eft's streams and blocks for the same particles (the inverse of ult_to_latte.EFT_ATTRIBUTES / eft_cb);
    Ultimate's side made consistent with what eft can carry (scale z = x x zratio, no plugin attributes)"""
    slot = prog.inputs
    time = float(cbs[10][8])
    g = lambda nm: A[:, slot[nm]] if nm in slot else np.zeros((len(A), 4), np.float32)
    for nm in slot:
        if nm.startswith('sysEmitterPlugin'):
            A[:, slot[nm]] = 0
    if 'sysScaleAttr' in slot:
        A[:, slot['sysScaleAttr'], 2] = A[:, slot['sysScaleAttr'], 0] * np.float32(zratio)
    pos, vec, rnd, scl = g('sysLocalPosAttr'), g('sysLocalVecAttr'), g('sysRandomAttr'), g('sysScaleAttr')
    st = {'v_inPos': g('sysPosAttr'), 'v_inTexCoord': g('sysTexCoordAttr'), 'v_inColor': g('sysVertexColor0Attr'),
          'v_inWldPos': np.c_[pos[:, :3], np.float32(time) - vec[:, 3]],
          'v_inVec': np.c_[vec[:, :3], rnd[:, 3]],
          'v_inRandom': np.c_[rnd[:, :3], pos[:, 3]],
          'v_inScl': np.c_[scl[:, :2], np.zeros(len(A)), scl[:, 3]],
          'v_inRot': g('sysInitRotateAttr'), 'v_inWldPosDf': g('sysLocalDiffAttr'),
          'v_inEmtMat0': g('sysEmtMat0Attr'), 'v_inEmtMat1': g('sysEmtMat1Attr'), 'v_inEmtMat2': g('sysEmtMat2Attr')}
    c8 = cbs[8].copy()
    c8[74], c8[75] = c8[72] * c8[73], c8[73] - c8[72]
    cbs[8] = c8
    cb1 = np.zeros(88, np.float32)
    cb1[:72] = c8[:72]
    cb1[80:82] = c8[72:74]
    return st, {1: cb1, 3: cbs[10]}


def test_program(prog, e, n, seed, keep=None, tag='', mode='identity'):
    rng = np.random.default_rng(seed)
    time = 30.0
    A = particles(rng, prog, n, time)
    cbs = blocks(rng, e, time)
    zratio = float(rng.uniform(0.5, 2))
    if mode == 'eft':
        streams, s4cbs = eft_inputs(prog, A, cbs, zratio)
    else:
        s4cbs = {1: cbs[8], 3: cbs[10]}
    consts = {k: [int(x) for x in np.asarray(v).view(np.uint32)] for k, v in cbs.items() if k not in (8, 10)}
    consts[1] = [int(x) for x in np.frombuffer(prog.cdata or b'\0\0\0\0', np.uint32)]
    names = {slot: name for name, slot in prog.inputs.items()}
    low = ult_to_latte.Lowering(prog.glsl, consts, names, mode, zratio).run()
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--only', default='')
    ap.add_argument('--n', type=int, default=256)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--keep', default='')
    ap.add_argument('--mode', default='identity', choices=('identity', 'eft'))
    a = ap.parse_args()
    import port_sources
    cfg = json.load(open(os.path.join(ROOT, 'fighters', a.name, 'port.json')))
    eff = vfxb.Eff(port_sources.load().eff(cfg['ult']))
    only = {int(x) for x in a.only.split(',') if x}
    seen, fails, sizes = {}, [], []
    for e in all_emitters(eff):
        idx = e['shader']['shader_index']
        if idx in seen or (only and idx not in only):
            continue
        seen[idx] = True
        try:
            prog = mx_exec.Program(eff.vfxb, idx, 'vs')
            bad, nops, _r, _low = test_program(prog, e, a.n, a.seed, a.keep or None, 'vs_%d' % idx, a.mode)
        except Exception as ex:  # noqa: BLE001
            bad, nops = ['error: %s' % str(ex).splitlines()[0][:200]], 0
        sizes.append(nops)
        if bad:
            fails.append(idx)
            print('vs %d %s: %s' % (idx, e['name'], ', '.join(bad)), flush=True)
    print('%d programs, %d pass, %d fail; Latte operations median %d, max %d'
          % (len(seen), len(seen) - len(fails), len(fails), int(np.median(sizes)) if sizes else 0, max(sizes or [0])))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
