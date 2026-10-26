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


# ---------------------------------------------------------------- grafts: code of our own in a template's program
# A graft adds ALU clauses to a vanilla program rather than rebuilding it (its branches, flipbook
# fetch clauses and scheduling stay the compiler's). Control flow (CF) words, little-endian pairs:
# an ALU clause has word 1 bits 29:28 = 2 / 3 and its code address (64-bit units) in word 0 bits
# 21:0; other instructions a 7-bit opcode at word 1 bits 29:23 (1 / 2 / 3 TEX / VTX clauses, word 0
# their code address; 4 - 18 loops, jumps, else, pop, call: word 0 a CF index; 19 CALL_FS; 39 / 40
# EXP / EXP_DONE: word 0 bits 12:0 the array base (PARAMn: n), 14:13 the type (2 param), 21:15 the
# GPR, word 1 bits 20:17 the burst count, bit 21 END_OF_PROGRAM).
CF_TEX, CF_VTX, CF_VTX_TC, CF_CALL_FS, CF_EXP, CF_EXP_DONE = 1, 2, 3, 19, 39, 40
CF_TARGETS = range(4, 19)
VS_REGS, VS_SIZE = 52, 52           # GX2VertexShader: 52 register words, then the program size
PS_SIZE, PS_NSAMPLER, PS_SAMPLERS = 41, 52, 53
SPI_VS_OUT_ID = 4                   # 10 words, 4 semantic bytes each (PARAM 4n + k in byte k)
# the shtAnim block of slot 1 (CB2 vec4 6-10: pm0-pm4) and uboFlag's inverse-random bits for it
SLOT1_PM = 6


def _cf(prog):
    out = []
    for i in range(0, len(prog), 8):
        w0, w1 = struct.unpack_from('<II', prog, i)
        out.append([w0, w1])
        if not (w1 >> 28) & 2 and (w1 >> 21) & 1:
            break
    return out


def _is_alu(w1):
    return (w1 >> 28) & 3 in (2, 3)


def _op(w1):
    return (w1 >> 23) & 0x7F


def _alu(lines, kcache=None):
    """(CF words, code) of an ALU clause written in latte-asm's syntax (assembled in a throwaway
    pixel program: ALU code is the same in both stages)"""
    from trail_shader import LATTE_ASM
    regs = [int(r) for r in re.findall(r'R(\d+)\.', '\n'.join(lines))]
    src = ['; $MODE = "UniformBlock"', '; $SQ_PGM_RESOURCES_PS.NUM_GPRS = %d' % (max(regs) + 1),
           '; $SQ_PGM_EXPORTS_PS.EXPORT_MODE = 2', '; $SPI_PS_IN_CONTROL_0.NUM_INTERP = 1',
           '; $NUM_SPI_PS_INPUT_CNTL = 1', '; $SPI_PS_INPUT_CNTL[0].SEMANTIC = 0', '',
           '00 ALU:' + (' KCACHE0(CB%d:%d-%d)' % kcache if kcache else '')]
    src += ['  %d   %s' % (i, l) for i, l in enumerate(lines)]
    src += ['01 EXP_DONE: PIX0, R0.xyzw', 'END_OF_PROGRAM']
    with tempfile.TemporaryDirectory() as tmp:
        ps, gsh = os.path.join(tmp, 'a.psh'), os.path.join(tmp, 'a.gsh')
        open(ps, 'w').write('\n'.join(src) + '\n')
        r = subprocess.run([LATTE_ASM, 'assemble', '--psh', ps, gsh], capture_output=True, text=True)
        if r.returncode or not os.path.exists(gsh):
            raise RuntimeError('latte-asm: %s%s' % (r.stdout, r.stderr))
        g = open(gsh, 'rb').read()
    prog = [g[o:o + s] for t, _h, o, s in gsh_blocks(g, 0) if t == 7][0]
    w0, w1 = struct.unpack_from('<II', prog, 0)
    addr, count = w0 & 0x3FFFFF, ((w1 >> 18) & 0x7F) + 1
    return [w0 & ~0x3FFFFF, w1], prog[8 * addr:8 * (addr + count)]


def uv1_lines(t, rnd, e, o, a, b, c, mesh=True, slot=1):
    """slot 1's UV animation, eft's own slot-0 code over again (fitted against it: Bayonetta's ring1
    mesh program and Bunner's smoke quad program, within 2e-5, repeats included; tools/
    eft_vertex_test.py): shift = frame x rate + initial + random x (1 - 2r), scale likewise, the turn
    a = -(frame x rate + initial + random x (1 - 2r)), r the random channel pm3.w picks. On a mesh,
    u' / v' = the still UV (e.zw: x repeat, inverse-random flips done) - 0.5:
        U = scaleU (cos a u' - sin a v') - shiftU + 0.5,  V = scaleV (cos a v' + sin a u') - shiftV + 0.5
    a quad's corner (x, y) = (e.z / repeat - 0.5, 0.5 - e.w / repeat), turned to (Ru, Rv):
        U = Ru (repeat - 1 + scaleU) + repeat / 2 - shiftU,  V = Rv (1 - scaleV - repeat) + repeat / 2 - shiftV
    One operation a group; out o = (e.xy, U, V). t: the frame (in .x), rnd: v_inRandom; a, b, c
    scratch GPRs; KC0 = CB2 0-15; slot: whose block (shtAnim1 / 2, CB2 vec4 6-10 / 11-15)"""
    pm = lambda k, ch: 'KC0[%d].%s' % (SLOT1_PM + 5 * (slot - 1) + k, ch)
    T, D, E, O, A, B, C = ('R%d' % r for r in (t, rnd, e, o, a, b, c))
    two, rev = '(0xC0000000, -2)', '(0xBE22F983, -0.15915494)'
    L = ['t: FLT_TO_INT      %s.x, %s' % (B, pm(3, 'w')),
         'y: SETE_INT        %s.y, %s.x, (0x00000001, 0)' % (B, B),     # (a bare 1 is 1.0f)
         'z: SETE_INT        %s.z, %s.x, (0x00000002, 0)' % (B, B)]
    # the random channel each value takes: chan 0 / 1 / 2 (scroll u, v; scale u, v; turn)
    for dst, (c0, c1, c2) in (('%s.x' % C, 'xyz'), ('%s.y' % C, 'yzx'), ('%s.z' % C, 'xyx'),
                              ('%s.w' % C, 'yzy'), ('%s.w' % B, 'zxy')):
        s = dst[-1]
        L += ['%s: CNDE_INT        %s, %s.y, %s.%s, %s.%s' % (s, dst, B, D, c0, D, c1),
              '%s: CNDE_INT        %s, %s.z, %s, %s.%s' % (s, dst, B, dst, D, c2),
              '%s: MULADD          %s, %s, %s, 1.0f' % (s, dst, dst, two)]
    # shift (A.xy), scale (A.zw), the turn (B.x), its sine / cosine (B.y / B.z)
    L += ['x: MULADD          %s.x, %s.x, %s, %s' % (A, T, pm(0, 'x'), pm(0, 'z')),
          'x: MULADD          %s.x, %s, %s.x, %s.x' % (A, pm(1, 'x'), C, A),
          'y: MULADD          %s.y, %s.x, %s, %s' % (A, T, pm(0, 'y'), pm(0, 'w')),
          'y: MULADD          %s.y, %s, %s.y, %s.y' % (A, pm(1, 'y'), C, A),
          'z: MULADD          %s.z, %s.x, %s, %s' % (A, T, pm(1, 'z'), pm(2, 'x')),
          'z: MULADD          %s.z, %s, %s.z, %s.z' % (A, pm(2, 'z'), C, A),
          'w: MULADD          %s.w, %s.x, %s, %s' % (A, T, pm(1, 'w'), pm(2, 'y')),
          'w: MULADD          %s.w, %s, %s.w, %s.w' % (A, pm(2, 'w'), C, A),
          'x: MULADD          %s.x, %s.x, %s, %s' % (B, T, pm(3, 'x'), pm(3, 'y')),
          'x: MULADD          %s.x, %s, %s.w, %s.x' % (B, pm(3, 'z'), B, B),
          # -turn in revolutions, wrapped to [-0.5, 0.5) (SIN / COS take revolutions)
          'x: MULADD          %s.x, %s.x, %s, 0.5f' % (B, B, rev),
          'x: FRACT           %s.x, %s.x' % (B, B),
          'x: ADD             %s.x, %s.x, -0.5f' % (B, B),
          't: SIN             %s.y, %s.x' % (B, B),
          't: COS             %s.z, %s.x' % (B, B)]
    if mesh:
        L += ['x: ADD             %s.x, %s.z, -0.5f' % (C, E),
              'y: ADD             %s.y, %s.w, -0.5f' % (C, E)]
    else:
        L += ['t: RECIP_IEEE      %s.z, %s' % (C, pm(4, 'x')),
              't: RECIP_IEEE      %s.w, %s' % (C, pm(4, 'y')),
              'x: MULADD          %s.x, %s.z, %s.z, -0.5f' % (C, E, C),
              'y: MULADD          %s.y, -%s.w, %s.w, 0.5f' % (C, E, C)]
    # turned: C.z = cos u - sin v, C.w = cos v + sin u
    L += ['z: MUL             %s.z, %s.z, %s.x' % (C, B, C),
          'z: MULADD          %s.z, -%s.y, %s.y, %s.z' % (C, B, C, C),
          'w: MUL             %s.w, %s.z, %s.y' % (C, B, C),
          'w: MULADD          %s.w, %s.y, %s.x, %s.w' % (C, B, C, C)]
    if mesh:
        L += ['z: MULADD          %s.z, %s.z, %s.z, -%s.x' % (O, A, C, A),
              'z: ADD             %s.z, %s.z, 0.5f' % (O, O),
              'w: MULADD          %s.w, %s.w, %s.w, -%s.y' % (O, A, C, A),
              'w: ADD             %s.w, %s.w, 0.5f' % (O, O)]
    else:
        L += ['z: ADD             %s.z, %s, -1.0f' % (O, pm(4, 'x')),
              'z: ADD             %s.z, %s.z, %s.z' % (O, O, A),
              'z: MUL             %s.z, %s.z, %s.z' % (O, C, O),
              'z: MULADD          %s.z, %s, 0.5f, %s.z' % (O, pm(4, 'x'), O),
              'z: ADD             %s.z, %s.z, -%s.x' % (O, O, A),
              'w: ADD             %s.w, -%s.w, 1.0f' % (O, A),
              'w: ADD             %s.w, %s.w, -%s' % (O, O, pm(4, 'y')),
              'w: MUL             %s.w, %s.w, %s.w' % (O, C, O),
              'w: MULADD          %s.w, %s, 0.5f, %s.w' % (O, pm(4, 'y'), O),
              'w: ADD             %s.w, %s.w, -%s.y' % (O, O, A)]
    L += ['x: MOV             %s.x, %s.x' % (O, E),
          'y: MOV             %s.y, %s.y' % (O, E)]
    return L


def uv2_lines(t, rnd, e, o, a, b, c, e2, mesh=True):
    """slot 2's UV animation into o.zw (uv1_lines on shtAnim2), its still UV made from slot 1's in
    e.zw: / slot 1's repeat x slot 2's (the base UV with slot 1's inverse-random flips: slot 2's own
    flags aren't drawn); e2: a GPR for it"""
    E, E2 = 'R%d' % e, 'R%d' % e2
    rep1, rep2 = 'KC0[%d]' % (SLOT1_PM + 4), 'KC0[%d]' % (SLOT1_PM + 9)
    return ['t: RECIP_IEEE      %s.x, %s.x' % (E2, rep1),
            't: RECIP_IEEE      %s.y, %s.y' % (E2, rep1),
            'z: MUL             %s.z, %s.z, %s.x' % (E2, E, E2),
            'z: MUL             %s.z, %s.z, %s.x' % (E2, E2, rep2),
            'w: MUL             %s.w, %s.w, %s.y' % (E2, E, E2),
            'w: MUL             %s.w, %s.w, %s.y' % (E2, E2, rep2)] + \
        uv1_lines(t, rnd, e2, o, a, b, c, mesh, slot=2)


def _param_semantic(regs, p):
    return (regs[SPI_VS_OUT_ID + p // 4] >> (8 * (p % 4))) & 0xFF


_points = {}


def uv1_graft_point(b, uv_sem):
    """uv1_graft_point_of, cached by program and semantic"""
    key = (program_key(b), hashlib.md5(b).hexdigest(), uv_sem)
    if key not in _points:
        _points[key] = uv1_graft_point_of(b, uv_sem)
    return _points[key]


def uv1_graft_point_of(b, uv_sem):
    """(the CF index of the EXP writing the texture coordinates, its GPR) when this program can take
    the slot-1 graft: it exports slot 1's still UV in .zw of the texcoord parameter (reads shtAnim1's
    pm4, animates none of slot 1), reads v_inWldPos (the frame in .w) and v_inRandom, starts with
    CALL_FS and exports that parameter alone; else None"""
    h = vertex_header(b)
    used = used_attributes(b)
    if h is None or 'v_inWldPos' not in used or 'v_inRandom' not in used or uv_caps(b)[1]:
        return None
    r = uniform_reads(disassemble(b))
    if (CB_STATIC, SLOT1_PM + 4, 'x') not in r or (CB_STATIC, SLOT1_PM + 4, 'y') not in r:
        return None
    params = [p for p in range(40) if _param_semantic(h['regs'], p) == uv_sem]
    prog = [b[o:o + s] for t, _h, o, s in gsh_blocks(b, 0) if t == VS_PROGRAM][0]
    cf = _cf(prog)
    if len(params) != 1 or _is_alu(cf[0][1]) or _op(cf[0][1]) != CF_CALL_FS:
        return None
    for i, (w0, w1) in enumerate(cf):
        if not _is_alu(w1) and _op(w1) in (CF_EXP, CF_EXP_DONE) and (w0 >> 13) & 3 == 2:
            base, burst = w0 & 0x1FFF, (w1 >> 17) & 0xF
            if base <= params[0] <= base + burst:
                return (i, (w0 >> 15) & 0x7F) if burst == 0 else None
    return None


def graft_uv1(b, uv_sem, uv2_sem=None):
    """the shader binary b (vertex + pixel GX2 file) with slot 1's UV animation grafted into its
    vertex program (uv1_lines, written into the texcoord parameter's .zw), or None (uv1_graft_point).
    Two clauses go in: after CALL_FS, saving the frame and v_inRandom in GPRs past the program's own
    (the inputs' GPRs are reused later); before the parameter's EXP, the animation into a fresh GPR,
    which the EXP then exports. Jumps past either point move with them; the clause code moves down
    when the CF list outgrows the space before it. uv2_sem: slot 2 as well (uv2_lines, a clause of
    its own), exported in .zw of a new parameter of that semantic (SPI_VS_OUT_CONFIG's count and
    SPI_VS_OUT_ID's byte for it), its EXP just before the texture coordinates'"""
    point = uv1_graft_point(b, uv_sem)
    if point is None:
        return None
    at, e = point
    h = vertex_header(b)
    used = used_attributes(b)
    n = h['regs'][0] & 0xFF
    extra = 8 if uv2_sem is not None else 6
    if n + extra > 120:
        return None
    t, rnd, o, a, bb, c = range(n, n + 6)
    e2, o2 = n + 6, n + 7
    w_t, w_r = used.index('v_inWldPos') + 1, used.index('v_inRandom') + 1
    # the particle's age: v_inWldPos.w on the CPU's particles; on the GPU's (programs reading
    # v_inVec: all 438 graftable vanilla ones) .w is its birth, the age the emitter's time
    # (emitterDynamicUniformBlock vec4 2 .x) less it, as their own code works it out
    if 'v_inVec' in used:
        save = _alu(['x: ADD             R%d.x, -R%d.w, KC0[2].x' % (t, w_t)] +
                    ['%s: MOV             R%d.%s, R%d.%s' % (ch, rnd, ch, w_r, ch) for ch in 'xyzw'], (CB_DYNAMIC, 0, 15))
    else:
        save = _alu(['x: MOV             R%d.x, R%d.w' % (t, w_t)] +
                    ['%s: MOV             R%d.%s, R%d.%s' % (ch, rnd, ch, w_r, ch) for ch in 'xyzw'])
    anim = _alu(uv1_lines(t, rnd, e, o, a, bb, c, 'v_inTexCoord' in used), (CB_STATIC, 0, 15))
    anim2 = _alu(uv2_lines(t, rnd, e, o2, a, bb, c, e2, 'v_inTexCoord' in used), (CB_STATIC, 0, 15)) \
        if uv2_sem is not None else None
    params = 1 + ((h['regs'][2] >> 1) & 0x1F)
    if uv2_sem is not None and params >= 32:
        return None
    prog = [b[o_:o_ + s] for t_, _h, o_, s in gsh_blocks(b, 0) if t_ == VS_PROGRAM][0]
    cf = _cf(prog)
    code_at = min(w0 & (0x3FFFFF if _is_alu(w1) else 0xFFFFFFFF) for w0, w1 in cf
                  if _is_alu(w1) or _op(w1) in (CF_TEX, CF_VTX, CF_VTX_TC))
    added = 2 + (2 if anim2 else 0)             # (save, anim; anim2 and its EXP)
    shift = max(0, len(cf) + added - code_at)
    shift += shift & 1                          # TEX / VTX clauses stay 16-byte aligned
    new_index = lambda i: i + (i >= 1) + (i >= at) * (added - 1)
    out = []
    for i, (w0, w1) in enumerate(cf):
        if _is_alu(w1):
            w0 = (w0 & ~0x3FFFFF) | ((w0 & 0x3FFFFF) + shift)
        elif _op(w1) in (CF_TEX, CF_VTX, CF_VTX_TC):
            w0 += shift
        elif _op(w1) in CF_TARGETS and w0 >= 1:
            w0 = new_index(w0) - (added - 1 if w0 == at else 0)     # (a jump to the EXP runs the graft first)
        if i == at:
            w0 = (w0 & ~(0x7F << 15)) | (o << 15)
        out.append([w0, w1])
    code = bytearray(prog[8 * code_at:])
    base = code_at + shift
    end = base + len(code) // 8
    end += end & 1
    inserts = []
    for cfw, alu in [save, anim] + ([anim2] if anim2 else []):
        inserts.append([cfw[0] | end, cfw[1]])
        code += bytes(8 * (end - base) - len(code)) + alu
        end += len(alu) // 8
        end += end & 1
    out.insert(1, inserts[0])
    before_exp = inserts[1:]
    if anim2:
        # its parameter: EXP (39), type 2, the GPR, xyzw, barrier
        before_exp.append([params | (2 << 13) | (o2 << 15), 0x93800688])
    for k, w in enumerate(before_exp):
        out.insert(at + 1 + k, w)
    head = b''.join(struct.pack('<II', *w) for w in out)
    prog2 = head + bytes(8 * base - len(head)) + bytes(code)
    prog2 += bytes(-len(prog2) % 256)
    return _replace_vertex_program(b, prog2, n + extra, (params, uv2_sem) if anim2 else None)


def _replace_vertex_program(b, prog, gprs, new_param=None):
    out = bytearray()
    for typ, hdr, o, size in gsh_blocks(b, 0):
        head, data = bytearray(b[hdr:o]), bytearray(b[o:o + size])
        if typ == VS_HEADER:
            res = struct.unpack_from('>I', data, 0)[0]
            struct.pack_into('>I', data, 0, (res & ~0xFF) | gprs)
            struct.pack_into('>I', data, 4 * VS_SIZE, len(prog))
            if new_param:
                p, sem = new_param
                cfg = struct.unpack_from('>I', data, 8)[0]
                struct.pack_into('>I', data, 8, (cfg & ~(0x1F << 1)) | (p << 1))     # count - 1
                struct.pack_into('>I', data, 12, p // 4 + 1)
                w = SPI_VS_OUT_ID + p // 4
                ids = struct.unpack_from('>I', data, 4 * w)[0]
                ids = (ids & ~(0xFF << (8 * (p % 4)))) | (sem << (8 * (p % 4)))
                struct.pack_into('>I', data, 4 * w, ids)
        elif typ == VS_PROGRAM:
            data = bytearray(prog)
        struct.pack_into('>I', head, 0x14, len(data))
        out += head + data
    first = next(h for _t, h, _o, _s in gsh_blocks(b, 0))
    return bytes(b[:first]) + bytes(out)


PS_IN_CONTROL_0, PS_NUM_INPUTS, PS_INPUT_CNTL = 2, 4, 5


def add_pixel_input(b, like_sem, sem):
    """the shader binary b with an input of semantic sem added to its pixel header (interpolated as
    its input of semantic like_sem): the new input's register is the old input count"""
    out = bytearray()
    for typ, hdr, o, size in gsh_blocks(b, 0):
        head, data = bytearray(b[hdr:o]), bytearray(b[o:o + size])
        if typ == 6:
            n = struct.unpack_from('>I', data, 4 * PS_NUM_INPUTS)[0]
            cntl = [struct.unpack_from('>I', data, 4 * (PS_INPUT_CNTL + k))[0] for k in range(n)]
            like = next(c for c in cntl if c & 0xFF == like_sem)
            struct.pack_into('>I', data, 4 * (PS_INPUT_CNTL + n), (like & ~0xFF) | sem)
            struct.pack_into('>I', data, 4 * PS_NUM_INPUTS, n + 1)
            c0 = struct.unpack_from('>I', data, 4 * PS_IN_CONTROL_0)[0]
            struct.pack_into('>I', data, 4 * PS_IN_CONTROL_0, (c0 & ~0x3F) | ((c0 & 0x3F) + 1))
        struct.pack_into('>I', head, 0x14, len(data))
        out += head + data
    first = next(h for _t, h, _o, _s in gsh_blocks(b, 0))
    return bytes(b[:first]) + bytes(out)


def add_pixel_sampler(b, name, location):
    """the shader binary b with a pixel sampler variable (2D) added to its pixel header, its
    relocation table ('}BLK': data / text regions, the pointer patch list) kept whole: eft finds a
    slot's sampler by name (cross_f 0x04A59E54, through the relocated pointers) and binds the slot's
    texture only where it does"""
    out = bytearray()
    for typ, hdr, o, size in gsh_blocks(b, 0):
        head, data = bytearray(b[hdr:o]), bytearray(b[o:o + size])
        if typ == 6:
            rel = data.rindex(b'}BLK')
            (_m, _sz, _z, dsize, doff, tsize, toff, pbase, pcount, poff) = struct.unpack_from('>10I', data, rel)
            patches = data[poff & 0xFFFFF:(poff & 0xFFFFF) + 4 * pcount]
            body = data[:dsize]
            n, ptr = struct.unpack_from('>II', body, 4 * PS_NSAMPLER)
            entries = body[ptr & 0xFFFFF:(ptr & 0xFFFFF) + 12 * n]
            arr = len(body)
            name_at = arr + 12 * (n + 1)
            body += entries + struct.pack('>3I', 0xCA700000 | name_at, 1, location)
            body += name.encode() + b'\0'
            body += bytes(-len(body) % 8)
            struct.pack_into('>II', body, 4 * PS_NSAMPLER, n + 1, 0xD0600000 | arr)
            new_patches = patches + b''.join(struct.pack('>I', 0xD0600000 | (arr + 12 * k)) for k in range(n + 1))
            poff2 = len(body)
            tail = new_patches + bytes(-len(new_patches) % 8)
            rel_hdr = struct.pack('>10I', 0x7D424C4B, 0x28, 0, len(body), doff, len(body) - (toff & 0xFFFFF),
                                  toff, pbase, pcount + n + 1, 0xD0600000 | poff2)
            data = body + tail + rel_hdr
        struct.pack_into('>I', head, 0x14, len(data))
        out += head + data
    first = next(h for _t, h, _o, _s in gsh_blocks(b, 0))
    return bytes(b[:first]) + bytes(out)


if __name__ == '__main__':
    import ptcl
    p = ptcl.Ptcl(open(sys.argv[1], 'rb').read())
    b = bytes(p.shader_binary(int(sys.argv[2])))
    h = vertex_header(b)
    print('blocks', h['blocks'])
    print('inputs', used_attributes(b))
    print('features', features(b))
    print('reads', sorted(uniform_reads(disassemble(b))))
