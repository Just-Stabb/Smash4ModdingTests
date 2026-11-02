#!/usr/bin/env python3
"""A converted emitter's own shader: Ultimate's vertex and pixel programs for it (BNSH variation, translated
by tools/ult_shader_glsl.py), lowered to Latte in eft mode (tools/ult_to_latte.py) and put together as one
GX2 vertex + pixel file, as a ptcl shader entry holds them. The universal shader path's phase 3
(docs/eft-universal-shader-scope.md).

  binary, info = build(vfxb, e, quad, zratio, encode, premultiply)

The baked blocks are the emitter's own: c9 its static block (eft2_resolve.static_block), c13 its CSDP, c12
the plugin block (zeros: none of Squirtle's emitters has a plugin), c16 Ultimate's per-effect block at its
defaults (fx_render's), c1 each program's immediates. info: {'samplers' [eft slots the pixel program
samples], 'kills', 'mat', 'vs_ops', 'ps_ops'}."""
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eft2_resolve  # noqa: E402
import mx_exec  # noqa: E402
import ult_shader_glsl  # noqa: E402
import ult_to_latte  # noqa: E402

C16 = np.zeros(32, np.float32)
C16[[0, 4, 5, 6, 8, 10, 18]] = 1.0          # colour / alpha x 1, no depth shift (fx_render's)
GFX2_HEAD = 0x20


def consts(e, cdata):
    csdp = bytes.fromhex(e['subsections'].get('CSDP', ''))
    words = lambda a: [int(x) for x in np.asarray(a).view(np.uint32).ravel()]
    return {9: words(np.frombuffer(eft2_resolve.static_block(e), np.uint32)),
            13: words(np.frombuffer(csdp[:len(csdp) // 4 * 4], np.uint32)) if csdp else [0] * 4,
            16: words(C16), 12: [0] * 32,
            1: words(np.frombuffer(cdata or b'\0\0\0\0', np.uint32))}


_mat = {}


def probe_matrix(vfxb, idx, e):
    """which matrix Ultimate's vertex program takes its particles out of the emitter's space with: run it on
    a live particle with sysEmtMat0-2's translation moved, then c10's emitter matrix's: 'attr', 'c10' or None
    (neither moves it: its positions are the world's)"""
    key = (id(vfxb), idx)
    if key in _mat:
        return _mat[key]
    vs = mx_exec.Program(vfxb, idx, 'vs')
    slot = vs.inputs
    rng = np.random.default_rng(7)
    n = 32
    A = rng.uniform(-1, 1, (n, 16, 4)).astype(np.float32)          # nothing degenerate (a zero vector normalised)
    time = 20.0

    def put(name, v):
        if name in slot:
            A[:, slot[name]] = v
    put('sysPosAttr', np.c_[rng.choice([-0.5, 0.5], (n, 2)), np.zeros(n), np.ones(n)])
    put('sysTexCoordAttr', rng.uniform(0, 1, (n, 4)))
    put('sysVertexColor0Attr', np.ones((n, 4)))
    put('sysLocalPosAttr', np.c_[rng.uniform(-3, 3, (n, 3)), np.full(n, 40.0)])          # w life
    put('sysLocalVecAttr', np.c_[rng.uniform(-1, 1, (n, 3)), time - rng.uniform(1, 10, n)])  # w birth
    put('sysScaleAttr', rng.uniform(0.5, 2, (n, 4)))
    put('sysRandomAttr', rng.uniform(0, 1, (n, 4)))
    put('sysInitRotateAttr', rng.uniform(-3, 3, (n, 4)))
    c8 = np.zeros(80, np.float32)
    for o in (0, 16, 32):
        c8[o:o + 16] = np.eye(4).ravel()
    c8[48:60] = np.eye(4)[:3].ravel()
    c8[64:72] = (0, 0, 1, 0, 0, 0, 100, 1)
    c8[72:76] = (1.0, 10000.0, 10000.0, 9999.0)
    c10 = np.zeros(48, np.float32)
    c10[0:8] = 1.0
    c10[8:16] = (time, 0, 0, 1, 1, 1, 1, 1)
    c10[16:28] = c10[32:44] = np.eye(4)[:3].ravel()
    cbs = {k: np.asarray(v, np.uint32) for k, v in consts(e, vs.cdata).items() if k != 1}
    cbs[8] = c8

    def run(dm, dc):
        for r in range(3):
            put('sysEmtMat%dAttr' % r, np.eye(4)[r] + (np.array([0, 0, 0, dm]) if r == 0 else 0))
        c = c10.copy()
        c[19] += dc
        cbs[10] = c
        return vs.run(A, cbs)[0]
    base = run(0, 0)
    live = np.isfinite(base).all(1) & (np.abs(base[:, 2]) < 1e4)       # (the dead path parks it at z 5e4)
    if not live.any():
        out = 'auto'                                                    # no answer: ult_to_latte's guess
    elif np.abs(run(5.0, 0) - base)[live].max() > 1e-3:
        out = 'attr'
    elif np.abs(run(0, 5.0) - base)[live].max() > 1e-3:
        out = 'c10'
    else:
        out = None
    _mat[key] = out
    return out


def combine(vs_gsh, ps_gsh):
    """one GX2 file: the GFX2 header, the vertex program's header and program blocks, the pixel program's, the
    end block (as the ptcl's vanilla binaries; block ids zeroed as theirs)"""
    def blocks(g):
        out, o = [], struct.unpack_from('>I', g, 4)[0]
        while o + 32 <= len(g) and g[o:o + 4] == b'BLK{':
            hs, typ, size = struct.unpack_from('>I', g, o + 4)[0], struct.unpack_from('>I', g, o + 16)[0], \
                struct.unpack_from('>I', g, o + 20)[0]
            head = bytearray(g[o:o + hs])
            struct.pack_into('>II', head, 0x18, 0, 0)
            out.append((typ, bytes(head) + g[o + hs:o + hs + size]))
            o += hs + size
        return out
    vb, pb = blocks(vs_gsh), blocks(ps_gsh)
    body = [b for t, b in vb if t in (3, 5)] + [b for t, b in pb if t in (6, 7)] + [b for t, b in vb if t == 1]
    return vs_gsh[:GFX2_HEAD] + b''.join(body)


def sampler_map(samplers):
    """{texture unit: eft slot} of a pixel program's samplers ({name: unit}): sysTextureSampler0-2 -> slots 0-2;
    sysDepthBufferTexture (soft particles' fade near the scene) 'far': eft's pixel stage has no depth texture, so
    it reads as the far plane (no fade); sysFrameBufferTexture (refraction) not lowered"""
    out = {}
    for name, unit in samplers.items():
        if name.startswith('sysTextureSampler'):
            out[unit] = int(name[len('sysTextureSampler'):])
        elif name == 'sysDepthBufferTexture':
            out[unit] = 'far'
        else:
            raise NotImplementedError('sampler ' + name)
    return out


def build(vfxb, e, quad, zratio=1.0, encode='display', premultiply=False):
    idx = e['shader']['shader_index']
    vcode, vdata = ult_shader_glsl.program(vfxb, idx, 'vs')
    vglsl, _ = ult_shader_glsl.translate(vcode, vdata, 'vs')
    pcode, pdata = ult_shader_glsl.program(vfxb, idx, 'ps')
    pglsl, _ = ult_shader_glsl.translate(pcode, pdata, 'ps')
    vref, pref = mx_exec.reflection(vfxb, idx, 'vs'), mx_exec.reflection(vfxb, idx, 'ps')
    names = {slot: name for name, slot in vref['inputs'].items()}
    info = e['info']
    colours = [float(v) for v in list(info['color0'])[:4] + list(info['color1'])[:4]]
    mat = probe_matrix(vfxb, idx, e)
    vlow = ult_to_latte.Lowering(vglsl, consts(e, vdata), names, 'eft', zratio, quad=quad, mat=mat,
                                 colours=colours).run()
    samplers = sampler_map(pref['samplers'])
    plow = ult_to_latte.Lowering(pglsl, consts(e, pdata), mode='eft', samplers=samplers, encode=encode,
                                 premultiply=premultiply, colours=colours).run()
    vs = ult_to_latte.assemble(vlow.text(), 'vs')
    ps = ult_to_latte.assemble(plow.text(), 'ps')
    missing = set(ult_to_latte.ps_header(ps)['inputs']) - set(ult_to_latte.vs_semantics(vs))
    if missing:
        raise RuntimeError('pixel inputs %s without a vertex output' % sorted(missing))
    used = sorted({srcs[0] for op, _d, srcs in plow.code if op in ult_to_latte.TEX_OPS})
    return combine(vs, ps), {'samplers': used, 'kills': plow.kills, 'mat': vlow.mat,
                             'depth': 'far' in samplers.values(), 'vs_ops': len(vlow.code),
                             'ps_ops': len(plow.code), 'attributes': vlow.hw_attrs}
