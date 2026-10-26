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

  t   = texture 0 (rgba: Ultimate's colour input in rgb, its alpha input in a, tools/vfxb_to_ptcl.py);
        on a two-texture template (texture 1's coordinates passed beside texture 0's, each slot with
        its own UV animation in the vertex program) t = texture 0 x or + texture 1, colour and alpha
        each as Ultimate's tex1 colour / alpha blend (0 multiply, 1 add)
  rgb = colour mode 0: c0; 1: c0 x t.rgb; 2: c1 + (c0 - c1) x t.rgb; 3: c0 x t.rgb + c1
  a   = alpha mode 0: c0.a x t.a; 1: t.a + c0.a - 1 (erosion: the texture eaten away by the fading
        alpha); x ALPHA_GAIN (Ultimate's alphas go past 1: its whirlwinds' at 2 - 4), clamped
  (a mesh layout: rgb x v.rgb, a x v.a), rgb clamped to 0 - 1 (the colours keep Ultimate's
  brightness past 1: what Ultimate's tone mapping shows saturated, not Smash 4's bloom), then
  rgb x hdr.x + hdr.w.
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
    template's own slot-0 SAMPLE reads them straight from an input, its only sample; or, a
    two-texture template, its slot-0 and slot-1 SAMPLEs each straight from an input, and 'uv1' for
    slot 1's"""
    q = header_words(binary, PS_HEADER)
    if q is None:
        return None
    sems = [q[INPUT_CNTL + k] & 0xFF for k in range(q[NUM_INPUTS])]
    text = disassemble(binary)
    samples = re.findall(r'SAMPLE\w*\s+R\d+\.\S+,\s+R(\d+)\.(\w\w)\w\w,\s+t(\d+),\s+s(\d+)', text)
    if 'DENORM' in text or sorted(t for _r, _c, t, _s in samples) not in (['0'], ['0', '1']) \
            or any(t != sm for _r, _c, t, sm in samples):
        return None
    uvs = {}
    for reg, comps, t, _s in samples:
        reg = int(reg)
        if comps not in ('xy', 'zw') or reg >= len(sems) or sems[reg] not in UV_SEMS:
            return None
        uvs[int(t)] = (reg, comps)
    used = {sems[r] for r, _c in uvs.values()}
    if SEM_COLOR0 not in sems or set(sems) - {SEM_COLOR0, SEM_COLOR1, SEM_VCOLOR} - used:
        return None
    out = {'regs': len(sems), 'c0': sems.index(SEM_COLOR0),
           'c1': sems.index(SEM_COLOR1) if SEM_COLOR1 in sems else None,
           'vc': sems.index(SEM_VCOLOR) if SEM_VCOLOR in sems else None,
           'uv': uvs[0], 'sems': sems}
    if 1 in uvs:
        out['uv1'] = uvs[1]
    return out


def lit(v):
    """an ALU literal operand"""
    if v == 0:
        return '0.0f'
    if v in (1.0, 0.5, -1.0, -0.5):
        return '%sf' % ('%.1f' % v)
    return '(0x%08X, %r)' % (struct.unpack('>I', struct.pack('>f', v))[0], float(v))


def source(lay, color_mode, alpha_mode, alpha_gain=1.0, c1_const=None, tex_blend=(0, 0), dissolve=None,
           c0_const=None):
    """the program's latte-asm source. c1_const (rgb): colour 1 as constants, for a layout without
    it (colour modes 2 / 3 on a template that passes colour 0 only: Kafrizz's sphere1 drew colour 0 x
    texture, an opaque black ball where its gradient texture is dark). tex_blend (colour, alpha):
    how a two-texture layout's texture 1 comes in, 0 multiply, 1 add. dissolve (edge width): Ultimate's
    custom shader 8 on a one-texture layout: texture 0 grey (colour in .x and .z), its mask in .y;
    the threshold colour 1's red (the converter's colour-1 track: Ultimate's colour 1 alpha over
    life), colour 1 itself c1_const; or, c0_const given (colour 0's rgb; its alpha stays the
    track's), colour 0's red; alpha x clamp((mask - threshold) / width)"""
    n = lay['regs']
    two = 'uv1' in lay
    c0, c1, vc = 'R%d' % lay['c0'], ('R%d' % lay['c1']) if lay['c1'] is not None else None, lay['vc']
    uvr, uvc = lay['uv']
    t, d = 'R%d' % n, 'R%d' % (n + 1)          # the texel, the colour's work register
    thr = None
    if dissolve is not None and not two:
        if c0_const is not None and (c1 is not None or c1_const is None or color_mode not in (2, 3)):
            thr = c0
        elif c0_const is None and c1 is not None:
            thr, c1 = c1, None
        ramp = 'R%d' % (n + 2)
    if thr != c0:
        c0_const = None

    def c0op(ch):
        return lit(c0_const['xyz'.index(ch)]) if c0_const is not None else '%s.%s' % (c0, ch)
    tc = (lambda ch: 'x' if ch == 'y' else ch) if thr else (lambda ch: ch)     # the texel's colour channels
    if color_mode in (2, 3) and c1 is None and c1_const is None:
        color_mode = 1

    def c1op(ch, neg=False):
        if c1 is not None:
            return '%s%s.%s' % ('-' if neg else '', c1, ch)
        return lit(-c1_const['xyz'.index(ch)] if neg else c1_const['xyz'.index(ch)])
    head = ['; eft pixel program (tools/eft_pixel.py): colour mode %d, alpha mode %d, alpha x %g%s%s'
            % (color_mode, alpha_mode, alpha_gain, ', texture 1 %s / %s' % tuple(
                ('x', '+')[b] for b in tex_blend) if two else '',
               ', dissolve %g by colour %d' % (dissolve, thr != c0) if thr else ''),
            '; $MODE = "UniformBlock"',
            '; $SQ_PGM_RESOURCES_PS.NUM_GPRS = %d' % (n + 3 if two or thr else n + 2),
            '; $SQ_PGM_EXPORTS_PS.EXPORT_MODE = 2',
            '; $SPI_PS_IN_CONTROL_0.NUM_INTERP = %d' % n,
            '; $NUM_SPI_PS_INPUT_CNTL = %d' % n]
    head += ['; $SPI_PS_INPUT_CNTL[%d].SEMANTIC = %d' % (k, s) for k, s in enumerate(lay['sems'])]
    body = ['00 TEX: VALID_PIX',
            '  0      SAMPLE          %s.xyzw, R%d.%s0%s, t0, s0' % (t, uvr, uvc, uvc[0])]
    groups = []
    if two:
        t1 = 'R%d' % (n + 2)
        r1, c1c = lay['uv1']
        body.append('  1      SAMPLE          %s.xyzw, R%d.%s0%s, t1, s1' % (t1, r1, c1c, c1c[0]))
        # texture 1 into the texel first: t = t0 x / + t1 (colour, alpha)
        groups.append(['%s: %-15s %s.%s, %s.%s, %s.%s' % (ch, ('MUL', 'ADD')[tex_blend[ch == 'w']], t, ch, t, ch, t1, ch)
                       for ch in 'xyzw'])
    if thr:
        # the dissolve's ramp from the untouched mask
        groups.append(['x: ADD             %s.x, %s.y, -%s.x' % (ramp, t, thr)])
        groups.append(['x: MUL             %s.x, %s.x, %s CLAMP' % (ramp, ramp, lit(1.0 / max(dissolve, 1e-3)))])
    body.append('01 ALU: KCACHE0(CB9:0-15)')
    # group 1: the colour's first step, the alpha's first step
    g = []
    for i, ch in enumerate('xyz'):
        if color_mode == 0:
            g.append('%s: MOV             %s.%s, %s' % (ch, d, ch, c0op(ch)))
        elif color_mode == 1:
            g.append('%s: MUL             %s.%s, %s, %s.%s' % (ch, d, ch, c0op(ch), t, tc(ch)))
        elif color_mode == 2:
            g.append('%s: ADD             %s.%s, %s, %s' % (ch, d, ch, c0op(ch), c1op(ch, True)))
        else:
            g.append('%s: MULADD          %s.%s, %s, %s.%s, %s' % (ch, d, ch, c0op(ch), t, tc(ch), c1op(ch)))
    if alpha_mode in (1, 3):
        g.append('w: ADD             %s.w, %s.w, %s.w' % (d, c0, t))
    else:
        g.append('w: MUL             %s.w, %s.w, %s.w' % (d, c0, t))
    groups.append(g)
    # group 2: the lerp; the erosion's -1 / the gain
    g = []
    if color_mode == 2:
        for ch in 'xyz':
            g.append('%s: MULADD          %s.%s, %s.%s, %s.%s, %s' % (ch, d, ch, d, ch, t, tc(ch), c1op(ch)))
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
    if thr:
        # after the clamp, as Ultimate's: saturate(alpha) x the ramp
        groups.append(['w: MUL             %s.w, %s.w, %s.x' % (d, d, ramp)])
    if vc is not None:
        groups.append(['%s: MUL             %s.%s, %s.%s, R%d.%s' % (ch, d, ch, d, ch, vc, ch) for ch in 'xyz'])
    # the colour clamped to 0 - 1 where it's last written (Ultimate's colours run past 1 for its tone
    # mapping: kept so, a bright yellow over a grey band texture saturates to yellow as in Ultimate,
    # where scaled down to 1 first it drew a dull grey band; past 1 Smash 4's bloom turns it into a
    # purple haze, fix 21)
    last = max(i for i, g in enumerate(groups) if any(ln[0] in 'xyz' for ln in g))
    groups[last] = [ln + ' CLAMP' if ln[0] in 'xyz' and not ln.endswith('CLAMP') else ln for ln in groups[last]]
    # out: rgb x hdr.x + hdr.w, alpha
    groups.append(['%s: MULADD          R0.%s, %s.%s, KC0[8].x, KC0[8].w' % (ch, ch, d, ch) for ch in 'xyz']
                  + ['w: MOV             R0.w, %s.w' % d])
    k = 2 if two else 1                 # instruction slots count on from the samples
    for g in groups:
        for j, ln in enumerate(g):
            body.append(('  %-3d ' % k if j == 0 else '      ') + ln)
        k += 1
    body += ['02 EXP_DONE: PIX0, R0.xyzw', 'END_OF_PROGRAM', '']
    return '\n'.join(head + [''] + body)


_programs = {}


def program(lay, color_mode, alpha_mode, alpha_gain=1.0, c1_const=None, tex_blend=(0, 0), dissolve=None,
            c0_const=None):
    """(program bytes, GPR count), assembled once per variant"""
    src = source(lay, color_mode, alpha_mode, alpha_gain, c1_const, tex_blend, dissolve, c0_const)
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


def own_shader(p, si, color_mode, alpha_mode, alpha_gain=1.0, c1_const=None, tex_blend=(0, 0), dissolve=None,
               c0_const=None):
    """the index of shader si of Ptcl p with one of these pixel programs (added once per variant),
    or None when its pixel program isn't one this module can stand in for. c1_const: colour 1 (rgb,
    x the colour scale) for a template that doesn't pass it, or that passes the dissolve's
    threshold in it (dissolve: its edge width; on a one-texture layout with colour 1 only); c0_const:
    colour 0's rgb, the dissolve's threshold in colour 0's track instead (a layout without colour 1
    then only in colour modes 0 / 1)"""
    b = bytes(p.shader_binary(si))
    lay = layout(b)
    if lay is None:
        return None
    if dissolve is None or 'uv1' in lay or (c0_const is None and lay['c1'] is None) or (
            c0_const is not None and lay['c1'] is None and color_mode in (2, 3)):
        dissolve = c0_const = None
    if dissolve is not None:
        dissolve = round(float(dissolve), 4)
    if c0_const is not None:
        c0_const = tuple(round(float(v), 3) for v in c0_const)
    if (lay['c1'] is not None and (dissolve is None or c0_const is not None)) or color_mode not in (2, 3):
        c1_const = None
    elif c1_const is not None:
        c1_const = tuple(round(float(v), 3) for v in c1_const)
    if 'uv1' not in lay:
        tex_blend = (0, 0)
    key = (id(p), hashlib.md5(b).hexdigest(), color_mode, alpha_mode, round(alpha_gain, 4), c1_const, tuple(tex_blend),
           dissolve, c0_const)
    if key not in _shaders or _shaders[key][0] is not p:
        prog, gprs = program(lay, color_mode, alpha_mode, alpha_gain, c1_const, tex_blend, dissolve, c0_const)
        _shaders[key] = (p, p.add_shader(p.shader_entry(si), with_program(b, prog, gprs)))
    return _shaders[key][1]


if __name__ == '__main__':
    # print a variant's source: eft_pixel.py COLOR_MODE ALPHA_MODE [GAIN] [mesh]
    lay = {'regs': 3, 'c0': 0, 'c1': 1, 'vc': None, 'uv': (2, 'xy'), 'sems': [0, 1, 9]}
    if 'mesh' in sys.argv:
        lay = {'regs': 4, 'c0': 0, 'c1': 1, 'vc': 2, 'uv': (3, 'xy'), 'sems': [0, 1, 6, 10]}
    args = [a for a in sys.argv[1:] if a != 'mesh']
    print(source(lay, int(args[0]), int(args[1]), float(args[2]) if len(args) > 2 else 1.0))
