#!/usr/bin/env python3
"""Ultimate's own effect shaders, run on the CPU: the GLSL OpenSmash-Ultimate's translator makes of an
emitter's BNSH program (tools/ult_shader_glsl.py) compiled as C++ and called from numpy.

  prog = Program(path_or_eff_bytes, variation, 'vs' | 'ps')
  prog.inputs        {name: slot} from the program's reflection (sysPosAttr, sysLocalPosAttr, ...)
  prog.blocks        {name: constant buffer} (sysViewUniformBlock -> c8, sysEmitterStaticUniformBlock -> c9, ...)
  vs.run(attrs, cbs)                          -> gl_Position [n, 4], outputs [n, 8, 4]
  ps.draw(tris, outs, cbs, textures, canvas)  rasterises triangles into a linear canvas, the pixel program
                                              on every covered pixel, blended in primitive order

The translated code is register-level (r0.., predicates, F() / U() bit casts) and already C-like: it is
wrapped in a namespace with a small GLSL layer (vec2 / vec4, half floats, carries, bitfields, texture()
-> a bilinear sampler over the arrays given). Each program is compiled once into build/mx_exec/.

The reflection (BNSH, per program and stage): the program's +0x78 (its 16th word) points at a table of
stage reflections (vertex +0x00, pixel +0x20); a stage's: _DIC offsets of its inputs, outputs, samplers,
constant buffers, storage buffers, then the indices where each kind starts in its slot table (int32 x 4)
and the slot table's offset. A constant buffer slot k is the shader's c(3 + k)."""
import ctypes
import hashlib
import os
import re
import struct
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ult_shader_glsl  # noqa: E402

CACHE = os.path.join(ROOT, 'build', 'mx_exec')
NCB = 20                 # constant buffers c0 .. c19
NATTR = 16
NOUT = 8
CB_WORDS = 4096          # every buffer padded to this many words (a read past the data gives 0)

SHIM = r'''
#include <cstdint>
#include <cstring>
#include <cmath>
namespace glsl {
typedef uint32_t uint;
struct vec2 { float x, y; vec2() : x(0), y(0) {} explicit vec2(float a) : x(a), y(a) {} vec2(float a, float b) : x(a), y(b) {}
  float &operator[](int i) { return (&x)[i]; } float operator[](int i) const { return (&x)[i]; } };
struct vec4 { float x, y, z, w; vec4() : x(0), y(0), z(0), w(0) {} vec4(float a, float b, float c, float d) : x(a), y(b), z(c), w(d) {}
  float &operator[](int i) { return (&x)[i]; } float operator[](int i) const { return (&x)[i]; } };
struct uvec2 { uint x, y; uvec2() : x(0), y(0) {} uvec2(uint a, uint b) : x(a), y(b) {} uint &operator[](int i) { return (&x)[i]; } };
static inline float uintBitsToFloat(uint u) { float f; memcpy(&f, &u, 4); return f; }
static inline uint floatBitsToUint(float f) { uint u; memcpy(&u, &f, 4); return u; }
static inline float fma(float a, float b, float c) { return std::fmaf(a, b, c); }
static inline float sqrt(float a) { return std::sqrt(a); }
static inline float inversesqrt(float a) { return 1.0f / std::sqrt(a); }
static inline float floor(float a) { return std::floor(a); }
static inline float trunc(float a) { return std::trunc(a); }
static inline float sin(float a) { return std::sin(a); }
static inline float cos(float a) { return std::cos(a); }
static inline float log2(float a) { return std::log2(a); }
static inline float exp2(float a) { return std::exp2(a); }
static inline bool isnan(float a) { return std::isnan(a); }
static inline float abs(float a) { return std::fabs(a); }
static inline int abs(int a) { return a < 0 ? -a : a; }
static inline float min(float a, float b) { return a < b ? a : b; }
static inline float max(float a, float b) { return a > b ? a : b; }
static inline double min(double a, double b) { return a < b ? a : b; }
static inline double max(double a, double b) { return a > b ? a : b; }
static inline int min(int a, int b) { return a < b ? a : b; }
static inline int max(int a, int b) { return a > b ? a : b; }
static inline uint min(uint a, uint b) { return a < b ? a : b; }
static inline uint max(uint a, uint b) { return a > b ? a : b; }
static inline float clamp(float x, float a, float b) { return x < a ? a : x > b ? b : x; }
static inline uint uaddCarry(uint a, uint b, uint &c) { uint r = a + b; c = r < a; return r; }
static inline int bitfieldExtract(int v, int off, int bits) { if (bits == 0) return 0; return (int)((uint)v << (32 - off - bits)) >> (32 - bits); }
static inline uint bitfieldExtract(uint v, int off, int bits) { if (bits == 0) return 0; return (v >> off) & (bits >= 32 ? 0xffffffffu : ((1u << bits) - 1)); }
static inline uint bitfieldInsert(uint b, uint ins, int off, int bits) { uint m = (bits >= 32 ? 0xffffffffu : ((1u << bits) - 1)) << off; return (b & ~m) | ((ins << off) & m); }
static inline float half2f(uint h) { uint s = (h >> 15) & 1, e = (h >> 10) & 31, m = h & 1023; float v;
  if (e == 0) v = std::ldexp((float)m, -24); else if (e == 31) v = m ? NAN : INFINITY; else v = std::ldexp((float)(m | 1024), (int)e - 25);
  return s ? -v : v; }
static inline uint f2half(float f) { uint u = floatBitsToUint(f), s = (u >> 16) & 0x8000; float a = std::fabs(f);
  if (std::isnan(f)) return s | 0x7e00; if (a >= 65520.0f) return s | 0x7c00; if (a < 6.103515625e-05f) return s | (uint)std::lrint(a * 16777216.0f);
  int e; float m = std::frexp(a, &e); uint mm = (uint)std::lrint((m * 2 - 1) * 1024); if (mm == 1024) { mm = 0; e++; } return s | ((uint)(e + 14) << 10) | mm; }
static inline vec2 unpackHalf2x16(uint r) { return vec2(half2f(r & 0xffff), half2f(r >> 16)); }
static inline uint packHalf2x16(vec2 v) { return f2half(v.x) | (f2half(v.y) << 16); }
struct Tex { int w, h; const float *rgba; int wrap_u, wrap_v; };
static Tex g_tex[16];
struct sampler2D { int unit; sampler2D(uvec2 h) : unit((int)h.x) {} };
static inline int wrapi(int i, int n, int mode) {
  if (mode == 1) { int p = 2 * n; i = ((i % p) + p) % p; return i < n ? i : p - 1 - i; }      /* mirror */
  if (mode == 2) return i < 0 ? 0 : i >= n ? n - 1 : i;                                      /* clamp */
  return ((i % n) + n) % n; }                                                                 /* repeat */
static inline vec4 texture(sampler2D s, vec2 uv) {
  if (s.unit < 0 || s.unit >= 16 || !g_tex[s.unit].rgba) return vec4(1, 1, 1, 1);
  const Tex &t = g_tex[s.unit];
  float x = uv.x * t.w - 0.5f, y = uv.y * t.h - 0.5f; int x0 = (int)std::floor(x), y0 = (int)std::floor(y);
  float fx = x - x0, fy = y - y0; vec4 o;
  for (int k = 0; k < 4; k++) {
    int xi = wrapi(x0 + (k & 1), t.w, t.wrap_u), yi = wrapi(y0 + (k >> 1), t.h, t.wrap_v);
    float wgt = ((k & 1) ? fx : 1 - fx) * ((k >> 1) ? fy : 1 - fy);
    const float *p = t.rgba + 4 * (yi * t.w + xi);
    for (int c = 0; c < 4; c++) o[c] += wgt * p[c]; }
  return o; }
static inline vec4 textureLod(sampler2D s, vec2 uv, float) { return texture(s, uv); }
static inline vec2 textureQueryLod(sampler2D, vec2) { return vec2(0.0f, 0.0f); }
static bool mx_discarded;
static int gl_VertexID;
static vec4 gl_FragCoord;
'''


def _cpp(glsl, stage):
    """the translated GLSL as C++ in namespace glsl, plus run / draw entry points"""
    body = []
    cbs, ins, outs = set(), set(), set()
    for line in glsl.splitlines():
        s = line.strip()
        if s.startswith('#version') or s.startswith('#extension') or s.startswith('#define F(') or \
                s.startswith('#define U('):
            continue
        m = re.match(r'layout\(std430, binding = (\d+)\) readonly buffer CB\d+ \{ uint (c\d+)\[\]; \};', s)
        if m:
            cbs.add(int(m.group(2)[1:]))
            body.append('static const uint *%s;' % m.group(2))
            continue
        m = re.match(r'layout\(location = (\d+)\) (in|out) vec4 (\w+);', s)
        if m:
            (ins if m.group(2) == 'in' else outs).add((int(m.group(1)), m.group(3)))
            body.append('static vec4 %s;' % m.group(3))
            continue
        if s.startswith('out gl_PerVertex'):
            body.append('static vec4 gl_Position; static float gl_PointSize;')
            continue
        if s.startswith('layout(location = 0) uniform uvec2 mx_alpha'):
            body.append('static uvec2 mx_alpha(0u, 0u);')
            continue
        if s.startswith('layout('):
            raise ValueError('unhandled declaration: ' + s)
        line = line.replace('v.xx', 'vec2(v.x, v.x)').replace('v.yy', 'vec2(v.y, v.y)').replace('frag0.a', 'frag0.w')
        line = re.sub(r'\bdiscard\b', '{ mx_discarded = true; return; }', line)
        line = line.replace('void main()', 'static void shader_main()')
        body.append(line)
    src = [SHIM, '#define F(x) uintBitsToFloat(x)', '#define U(x) floatBitsToUint(x)'] + body + ['}  // namespace glsl']
    setcb = '\n'.join('  c%d = cb[%d];' % (k, k) for k in sorted(cbs))
    setin = '\n'.join('  %s = vec4(a[%d], a[%d], a[%d], a[%d]);' % (n, 4 * l, 4 * l + 1, 4 * l + 2, 4 * l + 3)
                      for l, n in sorted(ins))
    if stage == 'vs':
        getout = '\n'.join('  for (int c = 0; c < 4; c++) o[%d + c] = %s[c];' % (4 * l, n) for l, n in sorted(outs))
        src.append(r'''
extern "C" void vs_run(int n, const float *attr, const glsl::uint *const *cb, float *pos, float *out) {
  using namespace glsl;
%s
  for (int i = 0; i < n; i++) {
    const float *a = attr + (size_t)i * %d * 4; float *o = out + (size_t)i * %d * 4;
%s
    gl_VertexID = i; gl_Position = vec4(); mx_discarded = false;
    shader_main();
    for (int c = 0; c < 4; c++) pos[4 * i + c] = gl_Position[c];
%s
  }
}''' % (setcb, NATTR, NOUT, setin, getout))
    else:
        src.append(r'''
extern "C" int ps_draw(int ntri, const float *vpos, const float *vout, const glsl::uint *const *cb,
                       const float *const *tex, const int *texinfo, float *canvas, int w, int h, int blend,
                       float *alpha_out) {
  using namespace glsl;
%s
  for (int u = 0; u < 16; u++) { g_tex[u].rgba = tex[u]; g_tex[u].w = texinfo[4 * u]; g_tex[u].h = texinfo[4 * u + 1];
    g_tex[u].wrap_u = texinfo[4 * u + 2]; g_tex[u].wrap_v = texinfo[4 * u + 3]; }
  int drawn = 0;
  float a[%d * 4];
  for (int t = 0; t < ntri; t++) {
    const float *P = vpos + (size_t)t * 12, *O = vout + (size_t)t * 3 * %d * 4;
    float x0 = P[0], y0 = P[1], x1 = P[4], y1 = P[5], x2 = P[8], y2 = P[9];
    float area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0);
    if (std::fabs(area) < 1e-12f) continue;
    int bx0 = (int)std::floor(std::fmin(x0, std::fmin(x1, x2))), bx1 = (int)std::ceil(std::fmax(x0, std::fmax(x1, x2)));
    int by0 = (int)std::floor(std::fmin(y0, std::fmin(y1, y2))), by1 = (int)std::ceil(std::fmax(y0, std::fmax(y1, y2)));
    if (bx0 < 0) bx0 = 0; if (by0 < 0) by0 = 0; if (bx1 > w) bx1 = w; if (by1 > h) by1 = h;
    for (int py = by0; py < by1; py++) for (int px = bx0; px < bx1; px++) {
      float sx = px + 0.5f, sy = py + 0.5f;
      float l1 = ((sx - x0) * (y2 - y0) - (x2 - x0) * (sy - y0)) / area;
      float l2 = ((x1 - x0) * (sy - y0) - (sx - x0) * (y1 - y0)) / area;
      float l0 = 1 - l1 - l2;
      if (l0 < 0 || l1 < 0 || l2 < 0) continue;
      for (int k = 0; k < %d * 4; k++) a[k] = l0 * O[k] + l1 * O[%d * 4 + k] + l2 * O[2 * %d * 4 + k];
%s
      gl_FragCoord = vec4(sx, sy, l0 * P[2] + l1 * P[6] + l2 * P[10], 1.0f);
      mx_discarded = false; frag0 = vec4();
      shader_main();
      if (mx_discarded) continue;
      float *d = canvas + 3 * ((size_t)py * w + px), al = frag0.w;
      if (!(al == al)) continue;
      for (int c = 0; c < 3; c++) {
        float s = frag0[c];
        if (blend == 1) d[c] += s * al;                    /* add */
        else if (blend == 2) d[c] -= s * al;               /* subtract */
        else if (blend == 3) d[c] = s + d[c] * (1 - al);   /* premultiplied */
        else d[c] = s * al + d[c] * (1 - al);              /* alpha */
      }
      if (alpha_out) { float *q = alpha_out + (size_t)py * w + px; *q = al + *q * (1 - al); }
      drawn++;
    }
  }
  return drawn;
}
extern "C" int ps_eval(int n, const float *ins, const glsl::uint *const *cb, const float *const *tex,
                       const int *texinfo, float *out) {
  using namespace glsl;
%s
  for (int u = 0; u < 16; u++) { g_tex[u].rgba = tex[u]; g_tex[u].w = texinfo[4 * u]; g_tex[u].h = texinfo[4 * u + 1];
    g_tex[u].wrap_u = texinfo[4 * u + 2]; g_tex[u].wrap_v = texinfo[4 * u + 3]; }
  int kept = 0;
  for (int i = 0; i < n; i++) {
    const float *a = ins + (size_t)i * %d * 4;
%s
    gl_FragCoord = vec4(0.5f, 0.5f, 0.0f, 1.0f); mx_discarded = false; frag0 = vec4();
    shader_main();
    for (int c = 0; c < 4; c++) out[5 * i + c] = frag0[c];
    out[5 * i + 4] = mx_discarded ? 0.0f : 1.0f; kept += !mx_discarded;
  }
  return kept;
}''' % (setcb, NOUT, NOUT, NOUT, NOUT, NOUT, setin, setcb, NOUT, setin))
    return '\n'.join(src)


def compile_glsl(glsl, stage):
    """the shared library for this program (cached by its text)"""
    src = _cpp(glsl, stage)
    key = hashlib.sha1(src.encode()).hexdigest()[:20]
    so = os.path.join(CACHE, '%s_%s.so' % (stage, key))
    if not os.path.exists(so):
        os.makedirs(CACHE, exist_ok=True)
        cpp = so[:-3] + '.cpp'
        open(cpp, 'w').write(src)
        r = subprocess.run(['g++', '-O1', '-w', '-shared', '-fPIC', '-o', so, cpp], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError('compiling %s: %s' % (cpp, r.stderr[:2000]))
        os.unlink(cpp)
    return ctypes.CDLL(so)


# ------------------------------------------------------------------ reflection
def _name(d, b, o):
    n = struct.unpack_from('<H', d, b + o)[0]
    return d[b + o + 2:b + o + 2 + n].decode('latin1')


def _dic(d, b, o):
    if not o:
        return []
    assert d[b + o:b + o + 4] == b'_DIC', hex(o)
    n = struct.unpack_from('<I', d, b + o + 4)[0]
    return [_name(d, b, struct.unpack_from('<Q', d, b + o + 8 + 16 * (i + 1) + 8)[0]) for i in range(n)]


def reflection(d, index, stage):
    """{'inputs', 'outputs', 'samplers', 'blocks'}: {name: slot} of BNSH variation index's stage"""
    b = d.find(b'BNSH')
    prog = b + struct.unpack_from('<Q', d, b + 0xC0 + 0x40 * index + 0x10)[0]
    tab = struct.unpack_from('<Q', d, prog + 0x78)[0]
    st = struct.unpack_from('<Q', d, b + tab + 8 * (0 if stage == 'vs' else 4))[0]
    if not st:
        return {'inputs': {}, 'outputs': {}, 'samplers': {}, 'blocks': {}}
    w = struct.unpack_from('<5Q4iQ', d, b + st)
    dicts = [_dic(d, b, p) for p in w[:5]]
    oi, si, ci, ui = w[5:9]
    slots = struct.unpack_from('<%di' % (ui + len(dicts[4])), d, b + w[9])
    return {'inputs': dict(zip(dicts[0], slots[0:oi])), 'outputs': dict(zip(dicts[1], slots[oi:si])),
            'samplers': dict(zip(dicts[2], slots[si:ci])),
            'blocks': {n: 3 + s for n, s in zip(dicts[3], slots[ci:ui])}}


class Program:
    def __init__(self, d, index, stage):
        self.stage = stage
        code, self.cdata = ult_shader_glsl.program(d, index, stage)
        self.glsl, self.summary = ult_shader_glsl.translate(code, self.cdata, stage)
        self.lib = compile_glsl(self.glsl, stage)
        r = reflection(d, index, stage)
        self.inputs, self.outputs, self.samplers, self.blocks = r['inputs'], r['outputs'], r['samplers'], r['blocks']

    def _cbs(self, cbs):
        """[NCB] pointers; cbs {buffer number: words (np.uint32)}, c1 the program's own immediates"""
        keep = []
        arr = (ctypes.POINTER(ctypes.c_uint32) * NCB)()
        full = dict(cbs)
        full[1] = np.frombuffer(self.cdata, np.uint32) if self.cdata else np.zeros(1, np.uint32)
        if 2 not in full:
            # the texture handle table: words 8 + 2u = texture unit u (the shim's sampler2D takes it as is)
            c2 = np.zeros(128, np.uint32)
            c2[8:40:2] = np.arange(16)
            full[2] = c2
        for k in range(NCB):
            a = np.zeros(CB_WORDS, np.uint32)
            if k in full:
                v = np.asarray(full[k]).view(np.uint32).ravel()
                a[:min(len(v), CB_WORDS)] = v[:CB_WORDS]
            keep.append(a)
            arr[k] = a.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
        return arr, keep

    def run(self, attrs, cbs):
        """vertex stage: attrs [n, 16, 4] float32 by slot -> (gl_Position [n, 4], outputs [n, 8, 4])"""
        attrs = np.ascontiguousarray(attrs, np.float32)
        n = len(attrs)
        pos = np.zeros((n, 4), np.float32)
        out = np.zeros((n, NOUT, 4), np.float32)
        arr, _keep = self._cbs(cbs)
        f = self.lib.vs_run
        f.restype = None
        f(ctypes.c_int(n), attrs.ctypes.data_as(ctypes.c_void_p), arr, pos.ctypes.data_as(ctypes.c_void_p),
          out.ctypes.data_as(ctypes.c_void_p))
        return pos, out

    def _tex(self, textures):
        texp = (ctypes.c_void_p * 16)()
        info = np.zeros(64, np.int32)
        hold = []
        for u, (img, wu, wv) in textures.items():
            img = np.ascontiguousarray(img, np.float32)
            hold.append(img)
            texp[u] = img.ctypes.data
            info[4 * u:4 * u + 4] = (img.shape[1], img.shape[0], wu, wv)
        return texp, info, hold

    def eval(self, ins, cbs, textures):
        """pixel stage on given inputs [n, 8, 4] -> [n, 5] (frag0 rgba, 1 kept / 0 discarded)"""
        ins = np.ascontiguousarray(ins, np.float32)
        out = np.zeros((len(ins), 5), np.float32)
        arr, _keep = self._cbs(cbs)
        texp, info, _hold = self._tex(textures)
        f = self.lib.ps_eval
        f.restype = ctypes.c_int
        f(ctypes.c_int(len(ins)), ins.ctypes.data_as(ctypes.c_void_p), arr, texp, info.ctypes.data_as(ctypes.c_void_p),
          out.ctypes.data_as(ctypes.c_void_p))
        return out

    def draw(self, vpos, vout, cbs, textures, canvas, blend, alpha=None):
        """pixel stage: triangles vpos [t, 3, 4] (x, y in canvas pixels, z, w), their vertices' outputs
        [t, 3, 8, 4], into canvas [h, w, 3] float32 (linear); textures {unit: (rgba [h, w, 4] float32,
        wrap_u, wrap_v)} (0 repeat, 1 mirror, 2 clamp); blend 0 alpha, 1 add, 2 subtract, 3 premultiplied"""
        vpos = np.ascontiguousarray(vpos, np.float32)
        vout = np.ascontiguousarray(vout, np.float32)
        arr, _keep = self._cbs(cbs)
        texp, info, _hold = self._tex(textures)
        assert canvas.dtype == np.float32 and canvas.flags['C_CONTIGUOUS']
        f = self.lib.ps_draw
        f.restype = ctypes.c_int
        return f(ctypes.c_int(len(vpos)), vpos.ctypes.data_as(ctypes.c_void_p), vout.ctypes.data_as(ctypes.c_void_p),
                 arr, texp, info.ctypes.data_as(ctypes.c_void_p), canvas.ctypes.data_as(ctypes.c_void_p),
                 ctypes.c_int(canvas.shape[1]), ctypes.c_int(canvas.shape[0]), ctypes.c_int(blend),
                 None if alpha is None else alpha.ctypes.data_as(ctypes.c_void_p))
