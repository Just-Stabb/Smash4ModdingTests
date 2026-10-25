#!/usr/bin/env python3
"""Pixel programs of our own for converted eft emitters: eft2's (Ultimate's) colour / alpha combiner
on a vanilla template's vertex program.

Smash 4's eft pixel programs are small and alike (docs/ptcl-format.md "Pixel programs"): inputs by
GX2 semantic, 0 = colour 0 (rgba: the colour and alpha tracks), 1 = colour 1, 6 = a mesh's vertex
colour (rgb and alpha multiply in), the texture coordinates on another (9 or 10, slot 0 in .xy);
then colour 1 + (colour 0 - colour 1) x texture rgb, alpha = colour 0 alpha x the texture's red or
alpha (template by template), x u_nwColorHdrRange (CB9 [8]: rgb x .x + .w). They can't take a
texture's colour from one channel and its alpha from another unless the template happens to read
alpha (Frizz's fire: Ultimate's ef_cmn_fire00 is a flipbook whose alpha is the flame and whose rgb
its hot core, coloured colour 1 -> colour 0 by it; through a red-alpha template every flame was one
flat colour). So a converted emitter keeps its template's vertex program (particle type, flipbook,
UV animation, follow) and pixel header (inputs, sampler, uniform blocks), and gets a pixel program
written here:

  t   = texture 0 (rgba: Ultimate's colour input in rgb, its alpha input in a, tools/vfxb_to_ptcl.py)
  rgb = colour mode 0: c0; 1: c0 x t.rgb; 2: c1 + (c0 - c1) x t.rgb; 3: c0 x t.rgb + c1
  a   = alpha mode 0: c0.a x t.a; 1: t.a + c0.a - 1 (erosion: the texture eaten away by the fading
        alpha); x ALPHA_GAIN (Ultimate's alphas go past 1: its whirlwinds' at 2 - 4), clamped
  (a mesh layout: rgb x v.rgb, a x v.a), then rgb x hdr.x + hdr.w.
"""
import hashlib
import os
import re
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from trail_shader import assemble, gsh_blocks, pixel_gsh  # noqa: E402

PS_HEADER, PS_PROGRAM = 6, 7
SEM_COLOR0, SEM_COLOR1, SEM_VCOLOR = 0, 1, 6
UV_SEMS = (9, 10)
# GX2PixelShader words: input count, then the input controls (semantic in the low byte)
NUM_INPUTS, INPUT_CNTL = 4, 5


def header_words(b, typ):
    for t, _h, o, s in gsh_blocks(b, 0):
        if t == typ:
            return [struct.unpack_from('>I', b, o + 4 * i)[0] for i in range(s // 4)]
    return None


def disassemble(b):
    import subprocess
    dis = os.path.join(HERE, 'latte_dis', 'latte-dis')
    for t, _h, o, s in gsh_blocks(b, 0):
        if t == PS_PROGRAM:
            with tempfile.NamedTemporaryFile(suffix='.gsh', delete=False) as f:
                f.write(b)
            try:
                return subprocess.run([dis, f.name, str(o), str(s)], capture_output=True, text=True).stdout
            finally:
                os.unlink(f.name)
    return ''


_layouts = {}


def layout(binary):
    """layout_of, cached by the binary's hash"""
    key = hashlib.md5(binary).hexdigest()
    if key not in _layouts:
        _layouts[key] = layout_of(binary)
    return _layouts[key]


def layout_of(binary):
    """the template pixel program's inputs, or None when it isn't one this module can stand in for:
    {'regs': number of input registers, 'c0', 'c1' (None without colour 1), 'vc' (None, or the
    vertex colour's register), 'uv': (register, 'xy' / 'zw')} -- the texture coordinates as the
    template's own slot-0 SAMPLE reads them straight from an input, its only sample"""
    q = header_words(binary, PS_HEADER)
    if q is None:
        return None
    sems = [q[INPUT_CNTL + k] & 0xFF for k in range(q[NUM_INPUTS])]
    text = disassemble(binary)
    samples = re.findall(r'SAMPLE\w*\s+R\d+\.\S+,\s+R(\d+)\.(\w\w)\w\w,\s+t(\d+)', text)
    if len(samples) != 1 or samples[0][2] != '0' or 'DENORM' in text:
        return None
    reg, comps = int(samples[0][0]), samples[0][1]
    if comps not in ('xy', 'zw') or reg >= len(sems) or sems[reg] not in UV_SEMS:
        return None
    if SEM_COLOR0 not in sems or set(sems) - {SEM_COLOR0, SEM_COLOR1, SEM_VCOLOR, sems[reg]}:
        return None
    return {'regs': len(sems), 'c0': sems.index(SEM_COLOR0),
            'c1': sems.index(SEM_COLOR1) if SEM_COLOR1 in sems else None,
            'vc': sems.index(SEM_VCOLOR) if SEM_VCOLOR in sems else None,
            'uv': (reg, comps), 'sems': sems}


def lit(v):
    """an ALU literal operand"""
    if v in (0.0, 1.0, 0.5, -1.0, -0.5):
        return '%sf' % ('%.1f' % v)
    return '(0x%08X, %r)' % (struct.unpack('>I', struct.pack('>f', v))[0], float(v))


def source(lay, color_mode, alpha_mode, alpha_gain=1.0):
    """the program's latte-asm source"""
    n = lay['regs']
    c0, c1, vc = 'R%d' % lay['c0'], ('R%d' % lay['c1']) if lay['c1'] is not None else None, lay['vc']
    uvr, uvc = lay['uv']
    t, d = 'R%d' % n, 'R%d' % (n + 1)          # the texel, the colour's work register
    if color_mode in (2, 3) and c1 is None:
        color_mode = 1
    head = ['; eft pixel program (tools/eft_pixel.py): colour mode %d, alpha mode %d, alpha x %g'
            % (color_mode, alpha_mode, alpha_gain),
            '; $MODE = "UniformBlock"',
            '; $SQ_PGM_RESOURCES_PS.NUM_GPRS = %d' % (n + 2),
            '; $SQ_PGM_EXPORTS_PS.EXPORT_MODE = 2',
            '; $SPI_PS_IN_CONTROL_0.NUM_INTERP = %d' % n,
            '; $NUM_SPI_PS_INPUT_CNTL = %d' % n]
    head += ['; $SPI_PS_INPUT_CNTL[%d].SEMANTIC = %d' % (k, s) for k, s in enumerate(lay['sems'])]
    body = ['00 TEX: VALID_PIX',
            '  0      SAMPLE          %s.xyzw, R%d.%s0%s, t0, s0' % (t, uvr, uvc, uvc[0]),
            '01 ALU: KCACHE0(CB9:0-15)']
    groups = []
    # group 1: the colour's first step, the alpha's first step
    g = []
    for i, ch in enumerate('xyz'):
        if color_mode == 0:
            g.append('%s: MOV             %s.%s, %s.%s' % (ch, d, ch, c0, ch))
        elif color_mode == 1:
            g.append('%s: MUL             %s.%s, %s.%s, %s.%s' % (ch, d, ch, c0, ch, t, ch))
        elif color_mode == 2:
            g.append('%s: ADD             %s.%s, %s.%s, -%s.%s' % (ch, d, ch, c0, ch, c1, ch))
        else:
            g.append('%s: MULADD          %s.%s, %s.%s, %s.%s, %s.%s' % (ch, d, ch, c0, ch, t, ch, c1, ch))
    if alpha_mode in (1, 3):
        g.append('w: ADD             %s.w, %s.w, %s.w' % (d, c0, t))
    else:
        g.append('w: MUL             %s.w, %s.w, %s.w' % (d, c0, t))
    groups.append(g)
    # group 2: the lerp; the erosion's -1 / the gain
    g = []
    if color_mode == 2:
        for ch in 'xyz':
            g.append('%s: MULADD          %s.%s, %s.%s, %s.%s, %s.%s' % (ch, d, ch, d, ch, t, ch, c1, ch))
    a_ops = []
    if alpha_mode in (1, 3):
        a_ops.append(('ADD', lit(-1.0)))
    if alpha_gain != 1.0:
        a_ops.append(('MUL', lit(alpha_gain)))
    if vc is not None:
        a_ops.append(('MUL', 'R%d.w' % vc))
    if a_ops:
        op, arg = a_ops.pop(0)
        g.append('w: %-15s %s.w, %s.w, %s%s' % (op, d, d, arg, '' if a_ops else ' CLAMP'))
    else:
        g.append('w: MOV             %s.w, %s.w CLAMP' % (d, d))
    groups.append(g)
    while a_ops:
        op, arg = a_ops.pop(0)
        groups.append(['w: %-15s %s.w, %s.w, %s%s' % (op, d, d, arg, '' if a_ops else ' CLAMP')])
    if vc is not None:
        groups.append(['%s: MUL             %s.%s, %s.%s, R%d.%s' % (ch, d, ch, d, ch, vc, ch) for ch in 'xyz'])
    # out: rgb x hdr.x + hdr.w, alpha
    groups.append(['%s: MULADD          R0.%s, %s.%s, KC0[8].x, KC0[8].w' % (ch, ch, d, ch) for ch in 'xyz']
                  + ['w: MOV             R0.w, %s.w' % d])
    k = 1
    for g in groups:
        for j, ln in enumerate(g):
            body.append(('  %-3d ' % k if j == 0 else '      ') + ln)
        k += 1
    body += ['02 EXP_DONE: PIX0, R0.xyzw', 'END_OF_PROGRAM', '']
    return '\n'.join(head + [''] + body)


_programs = {}


def program(lay, color_mode, alpha_mode, alpha_gain=1.0):
    """(program bytes, GPR count), assembled once per variant"""
    src = source(lay, color_mode, alpha_mode, alpha_gain)
    if src not in _programs:
        with tempfile.NamedTemporaryFile('w', suffix='.psh', delete=False) as f:
            f.write(src)
        try:
            _programs[src] = assemble(f.name)
        finally:
            os.unlink(f.name)
    return _programs[src]


def with_program(binary, prog, gprs):
    """a shader binary (vertex + pixel GX2 file) with its pixel program replaced"""
    return pixel_gsh(bytes(binary), 0, prog, gprs)


_shaders = {}


def own_shader(p, si, color_mode, alpha_mode, alpha_gain=1.0):
    """the index of shader si of Ptcl p with one of these pixel programs (added once per variant),
    or None when its pixel program isn't one this module can stand in for"""
    b = bytes(p.shader_binary(si))
    lay = layout(b)
    if lay is None:
        return None
    key = (id(p), hashlib.md5(b).hexdigest(), color_mode, alpha_mode, round(alpha_gain, 4))
    if key not in _shaders or _shaders[key][0] is not p:
        prog, gprs = program(lay, color_mode, alpha_mode, alpha_gain)
        _shaders[key] = (p, p.add_shader(p.shader_entry(si), with_program(b, prog, gprs)))
    return _shaders[key][1]


if __name__ == '__main__':
    # print a variant's source: eft_pixel.py COLOR_MODE ALPHA_MODE [GAIN] [mesh]
    lay = {'regs': 3, 'c0': 0, 'c1': 1, 'vc': None, 'uv': (2, 'xy'), 'sems': [0, 1, 9]}
    if 'mesh' in sys.argv:
        lay = {'regs': 4, 'c0': 0, 'c1': 1, 'vc': 2, 'uv': (3, 'xy'), 'sems': [0, 1, 6, 10]}
    args = [a for a in sys.argv[1:] if a != 'mesh']
    print(source(lay, int(args[0]), int(args[1]), float(args[2]) if len(args) > 2 else 1.0))
