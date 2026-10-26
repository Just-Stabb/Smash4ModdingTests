#!/usr/bin/env python3
"""What an eft vertex program does, read from the program itself rather than the emitter's mode words.

  python3 tools/eft_vertex.py PTCL SHADER_INDEX      (its inputs, uniform reads, UV capabilities)

The GX2 vertex header (block 3: GX2VertexShader) names the program's uniform blocks, uniforms and
attributes; its register words map each input GPR to an attribute location (SQ_VTX_SEMANTIC).
eft's blocks: viewUniformBlock (CB1: vm, pm, vpm, bm, eye, ...), emitterStaticUniformBlock (CB2:
uboFlag, then shtAnim0-2.pm0-pm4 at vec4 1-15, the flipbook tables, rotation / scale / alpha
animation, col0 / col1 keys at 46-61, ...), emitterDynamicUniformBlock (CB3: emitter colours and
matrices). The per-slot UV block (cross_f.rpx 0x04A5A6AC; the emitter's 0x4D4 + 0x7C x slot):
pm0 = scroll a frame (u, v), scroll initial; pm1 = scroll random, scale a frame; pm2 = scale initial,
scale random; pm3 = rotation a frame, initial, random, the slot (which random channel); pm4 =
repeat / cells (0x508), cells across / down. uboFlag 0x400 << 2 x slot / 0x800 << 2 x slot: the
slot's inverse-random U / V bytes (0x4DA / 0x4DB).

Neither the uniform fill nor any vanilla vertex program reads the slot's UV mode word (0x510 +
0x7C x slot): a program is compiled with no UV animation for a slot or with all of it (scroll,
scale, rotation; 13022 vanilla emitters, none with mode bits its program doesn't read, 2900 slots
running a full program under a narrower mode word). So what a template can animate is what its
program reads (uv_caps). Colour animation is the CPU's (v_inColor0 / v_inColor1: no vertex program
reads the col0 / col1 keys).

Flipbooks likewise: the CPU turns the slot's flipbook mode (0x500 + 0x7C x slot) into uboFlag bits
(0x04A5A858: slot 0's modes 1-5 -> 0x4, 0x10, 0x20, 0x8, 0x10000000; slot 1's 0x40, 0x100, 0x200,
0x80, 0x20000000; the table in use 0x1 / 0x2) and fills ptnAnmN (frames a cell, cells, random
start cells, the table); every vanilla program that reads ptnAnm0 tests all five slot-0 mode bits
(1211 emitters; none of the other 5300 has a flipbook), so a flipbook program plays any mode.
Follow types (0x310) are the CPU's too (0x04A5C89C: the live emitter matrices or copies made at
emission; the positions come in as v_inWldPos): one program serves 0, 1 and 2, except those
reading the live emitter matrix (emitterDynamicUniformBlock emm, vec4 4-7), all of whose emitters
follow (0; 2 with v_inEmtMat as well).
"""
import hashlib
import os
import re
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from trail_shader import gsh_blocks  # noqa: E402

VS_HEADER, VS_PROGRAM = 3, 5
CB_VIEW, CB_STATIC, CB_DYNAMIC = 1, 2, 3
# GX2VertexShader register words: [16] SQ_VTX_SEMANTIC count, [17-48] the semantics (input GPR R1 on)
NUM_SEMANTIC, SEMANTIC = 16, 17


def _ptr(o, v):
    """a GSH header pointer (0xD06xxxxx: an offset into the block's data)"""
    return o + (v & 0xFFFFF) if v else None


def _cstr(d, o):
    return d[o:d.index(b'\0', o)].decode('latin1')


def vertex_header(b):
    """the GX2VertexShader header of a shader binary: {'regs', 'blocks' [(name, CB, size)],
    'uniforms' [(name, type, count, offset in floats, block)], 'attribs' [(name, type, count,
    location)]}"""
    for t, _h, o, _s in gsh_blocks(b, 0):
        if t != VS_HEADER:
            continue
        regs = struct.unpack_from('>52I', b, o)
        w = struct.unpack_from('>15I', b, o + 0xD0)
        nub, pub, nuv, puv, nav, pav = w[3], w[4], w[5], w[6], w[13], w[14]
        out = {'regs': regs, 'blocks': [], 'uniforms': [], 'attribs': []}
        for i in range(nub):
            n, cb, size = struct.unpack_from('>3I', b, _ptr(o, pub) + 12 * i)
            out['blocks'].append((_cstr(b, _ptr(o, n)), cb, size))
        for i in range(nuv):
            n, typ, cnt, off, blk = struct.unpack_from('>5I', b, _ptr(o, puv) + 20 * i)
            out['uniforms'].append((_cstr(b, _ptr(o, n)), typ, cnt, off, blk if blk != 0xFFFFFFFF else -1))
        for i in range(nav):
            n, typ, cnt, loc = struct.unpack_from('>4I', b, _ptr(o, pav) + 16 * i)
            out['attribs'].append((_cstr(b, _ptr(o, n)), typ, cnt, loc))
        return out
    return None


def used_attributes(b):
    """the attribute names the program reads, in input-GPR order (R1, R2, ...)"""
    h = vertex_header(b)
    if h is None:
        return []
    loc = {a[3]: a[0] for a in h['attribs']}
    return [loc.get(s, s) for s in h['regs'][SEMANTIC:SEMANTIC + h['regs'][NUM_SEMANTIC]]]


def disassemble(b):
    dis = os.path.join(HERE, 'latte_dis', 'latte-dis')
    for t, _h, o, s in gsh_blocks(b, 0):
        if t == VS_PROGRAM:
            with tempfile.NamedTemporaryFile(suffix='.gsh', delete=False) as f:
                f.write(b)
            try:
                return subprocess.run([dis, f.name, str(o), str(s)], capture_output=True, text=True).stdout
            finally:
                os.unlink(f.name)
    return ''


def uniform_reads(text):
    """{(CB, vec4 index, component)} the program's ALU clauses read through their constant caches"""
    out, kc = set(), {}
    for line in text.splitlines():
        if 'ALU' in line and ': ADDR' in line:
            kc = {int(m.group(1)): (int(m.group(2)), int(m.group(3)))
                  for m in re.finditer(r'KCACHE(\d)\(CB(\d+):(\d+)-\d+\)', line)}
            continue
        for m in re.finditer(r'KC(\d)\[(\d+)\]\.([xyzw])', line):
            cb, base = kc[int(m.group(1))]
            out.add((cb, base + int(m.group(2)), m.group(3)))
    return out


_caps = {}


def program_key(b):
    return hashlib.md5(b''.join(b[o:o + s] for t, _h, o, s in gsh_blocks(b, 0) if t == VS_PROGRAM)).hexdigest()


def uv_caps(b):
    """[slot 0, 1, 2] the UV animation the vertex program draws (1 scroll: shtAnim pm0; 2 scale: pm2's
    initial scale; 4 rotation: pm3's rate / initial), cached by program"""
    key = program_key(b)
    if key not in _caps:
        r = uniform_reads(disassemble(b))
        out = []
        for k in range(3):
            v = 1 + 5 * k          # shtAnim k's pm0
            out.append((1 if any((CB_STATIC, v, c) in r for c in 'xyzw') else 0)
                       | (2 if (CB_STATIC, v + 2, 'x') in r or (CB_STATIC, v + 2, 'y') in r else 0)
                       | (4 if (CB_STATIC, v + 3, 'x') in r or (CB_STATIC, v + 3, 'y') in r else 0))
        _caps[key] = out
    return _caps[key]


_features = {}


def features(b):
    """{'uv': uv_caps, 'flipbook': (slot 0, slot 1) read ptnAnm0 / ptnAnm1, 'follow': the follow types
    it draws right, 'rot': reads v_inRot, 'vec': reads v_inVec, 'shader_param': reads u_shaderParam /
    u_shaderParamAnim0 / 1 (vec4 76-78; 162 of 675 vanilla programs)}, cached by program"""
    key = program_key(b)
    if key not in _features:
        r = uniform_reads(disassemble(b))
        used = used_attributes(b)
        emm = any(cb == CB_DYNAMIC and 4 <= v < 8 for cb, v, _c in r)
        _features[key] = {
            'uv': uv_caps(b),
            'flipbook': tuple(any(cb == CB_STATIC and v == base for cb, v, _c in r) for base in (16, 25)),
            'follow': frozenset((0, 2) if 'v_inEmtMat0' in used else (0,)) if emm else frozenset((0, 1, 2)),
            'rot': 'v_inRot' in used, 'vec': 'v_inVec' in used,
            'shader_param': any(cb == CB_STATIC and 76 <= v <= 78 for cb, v, _c in r)}
    return _features[key]


if __name__ == '__main__':
    import ptcl
    p = ptcl.Ptcl(open(sys.argv[1], 'rb').read())
    b = bytes(p.shader_binary(int(sys.argv[2])))
    h = vertex_header(b)
    print('blocks', h['blocks'])
    print('inputs', used_attributes(b))
    print('features', features(b))
    print('reads', sorted(uniform_reads(disassemble(b))))
