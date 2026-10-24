#!/usr/bin/env python3
"""Tests tools/trail_shader.py:

  python3 tools/trail_shader_test.py VANILLA/shader/effect_trail.nsh [CROSS_F.rpx]

- The nsh: shader 0x4F000003 between 2 and 1001, the other records byte for byte, the header's
  count and size, shader 3's vertex GX2 file = shader 1's, its pixel header = shader 1's but for the
  GPR count and program size.
- The vanilla pixel programs never read the vertex colour's rgb (R0.xyz) before writing it, so the
  vertex patch changes nothing for them.
- Shader 3's pixel program, run on a small Latte ALU interpreter (its disassembly), against
  Ultimate's shader 101 on the same trail (the mask at U = 1 - t / fade, the colour slid by
  (1 - fade) / 2), from Smash 4's vertex values (U = 1 - min(p + 1 - fade, 1), colour (t, fade, 1,
  (1 - t) fade)) across t, fade and V.
- With an RPX: the two vertex-writer stores run in Unicorn (patched) put t and the trail's +0x30 in
  the colour's red and green, unpatched they put 1.0 there.
"""
import os
import re
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trail_shader as T  # noqa: E402

LATTE_DIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'latte_dis', 'latte-dis')
FAILS = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        FAILS.append(what)


def disasm(path, off, size):
    r = subprocess.run([LATTE_DIS, path, hex(off), hex(size)], capture_output=True, text=True)
    return [l for l in r.stdout.splitlines() if l.strip()]


def pixel_program(d, rec):
    for _desc, g, _size in T.programs(d, rec):
        blocks = T.gsh_blocks(d, g)
        if any(t == T.PS_HEADER for t, *_ in blocks):
            hdr = [(h, o, s) for t, h, o, s in blocks if t == T.PS_HEADER][0]
            prog = [(h, o, s) for t, h, o, s in blocks if t == T.PS_PROGRAM][0]
            return g, hdr, prog


# ---- a Latte interpreter for the instructions shader 3 uses ----
def lit(tok):
    m = re.fullmatch(r'\((0x[0-9A-Fa-f]+),\s*[-0-9.e]+\)', tok)
    if m:
        return struct.unpack('>f', struct.pack('>I', int(m.group(1), 16)))[0]
    m = re.fullmatch(r'(-?[0-9.]+)f?', tok)
    return float(m.group(1)) if m else None


def run(lines, regs, kc0, samplers):
    """runs a disassembled pixel program: regs {'R0': [x, y, z, w], ...}; samplers {n: f(u, v) -> rgba}"""
    import math
    get = lambda r: regs.setdefault(r, [0.0] * 4)  # noqa: E731
    ch = 'xyzw'

    def src(tok):
        neg = tok.startswith('-')
        tok = tok[1:] if neg else tok
        v = lit(tok)
        if v is None:
            m = re.fullmatch(r'(R\d+|KC0\[(\d+)\])\.([xyzw])', tok)
            assert m, tok
            v = kc0[int(m.group(2))][ch.index(m.group(3))] if m.group(2) else get(m.group(1))[ch.index(m.group(3))]
        return -v if neg else v
    out = None
    for line in lines:
        m = re.match(r'\s*(?:\d+\s+)?([xyzwt]):\s+(\w+)\s+(.*)', line)
        if m:
            op, args = m.group(2), [a.strip() for a in re.split(r',\s*(?![^()]*\))', m.group(3))]
            args[-1] = args[-1].split(' ')[0] if not args[-1].startswith('(') else args[-1]
            args = [re.sub(r'\s+(SCL|VEC)_\d+$', '', a) for a in args]
            dst, s = args[0], [src(a) for a in args[1:]]
            v = {'MOV': lambda: s[0], 'MUL': lambda: s[0] * s[1], 'ADD': lambda: s[0] + s[1],
                 'MULADD': lambda: s[0] * s[1] + s[2], 'CNDGT': lambda: s[1] if s[0] > 0 else s[2],
                 'SETGE': lambda: 1.0 if s[0] >= s[1] else 0.0,
                 'RECIP_IEEE': lambda: 1.0 / s[0] if s[0] else math.inf}[op]()
            r, c = dst.split('.')
            get(r)[ch.index(c)] = v
            continue
        m = re.match(r'\s*\d+\s+SAMPLE\s+(R\d+)\.xyzw,\s+(R\d+)\.xy0x,\s+t(\d+),\s+s\d+', line)
        if m:
            u, v = get(m.group(2))[:2]
            regs[m.group(1)] = list(samplers[int(m.group(3))](u, v))
            continue
        m = re.match(r'\s*\d+\s+EXP_DONE: PIX0, (R\d+)\.xyzw', line)
        if m:
            out = list(get(m.group(1)))
    return out


def clamp01(x):
    return min(max(x, 0.0), 1.0)


def tex_a(u, v):   # colour texture: rgb and alpha varying along U and V
    u, v = clamp01(u), clamp01(v)
    return (0.2 + 0.6 * u, 0.5 * v, 0.9 - 0.3 * u, u * (1 - abs(v - 0.5)))


def tex_b(u, v, gain=1.4):   # mask in alpha (0 at U = 0), gain / 2 in rgb
    u, v = clamp01(u), clamp01(v)
    return (gain / 2, gain / 2, gain / 2, u ** 0.7 * (0.4 + 0.6 * v))


def ultimate(t, p, fade, v, hdr, gain=1.4):
    """Ultimate's 101 on its own vertex values: A at (1 - p - c4[8], v), c4[8] = (1 - fade) / 2; B at
    (1 - t / fade, v); premultiplied for Smash 4's blend (as shader 1)"""
    mu = 1 - t / fade if fade > 0 else 1.0
    a_ = tex_a(1 - p - (1 - fade) / 2, v)
    alpha = a_[3] * (tex_b(mu, v)[3] if mu >= 0 else 0.0)
    return [c * gain * hdr * alpha for c in a_[:3]] + [alpha]


def test_shader(lines):
    hdr = 1.25
    worst = 0.0
    n = 0
    for fade in (1.0, 0.8, 0.5, 0.2, 0.05):
        for i in range(11):
            t = i / 10
            p = t                                         # a full history: A's U and B's run together
            for v in (0.0, 1 / 3, 2 / 3, 1.0):
                regs = {'R0': [t, fade, 1.0, (1 - t) * fade], 'R1': [1 - min(p + 1 - fade, 1.0), v, 0, 0]}
                got = run(lines, regs, {0: [hdr, 0, 0, 0]}, {0: tex_a, 1: tex_b})
                want = ultimate(t, p, fade, v, hdr)
                worst = max(worst, max(abs(a - b) for a, b in zip(got, want)))
                n += 1
    check(worst < 1e-6, 'shader 3 = Ultimate 101 on %d samples (t, fade, V): max error %.2g' % (n, worst))
    # the tail past the fade point is cut, the part before it shows
    regs = {'R0': [0.6, 0.5, 1, 0.2], 'R1': [0.0, 0.5, 0, 0]}
    check(run(lines, regs, {0: [1, 0, 0, 0]}, {0: tex_a, 1: tex_b})[3] == 0.0, 'past the retract point: alpha 0')
    regs = {'R0': [0.2, 0.5, 1, 0.4], 'R1': [0.3, 0.5, 0, 0]}
    check(run(lines, regs, {0: [1, 0, 0, 0]}, {0: tex_a, 1: tex_b})[3] > 0.0, 'before it: alpha > 0')
    # no fade yet (1): the mask runs 1 -> 0 along the trail, A unslid
    regs = {'R0': [0.0, 1.0, 1, 1.0], 'R1': [1.0, 0.5, 0, 0]}
    got = run(lines, regs, {0: [1, 0, 0, 0]}, {0: tex_a, 1: tex_b})
    check(abs(got[3] - tex_a(1, 0.5)[3] * tex_b(1, 0.5)[3]) < 1e-9, 'at the blade, no fade: A.a x B.a')


def reads_rgb_first(lines):
    """does a program read R0.x / y / z before writing it?"""
    written = set()
    for line in lines:
        m = re.match(r'\s*(?:\d+\s+)?(?:[xyzwt]:\s+\w+(?:\*\d|/\d)?|SAMPLE)\s+(.*)', line)
        if not m:
            m = re.match(r'\s*\d+\s+EXP(?:_DONE)?: \w+, (.*)', line)
            if m:
                comps = re.match(r'R0\.([xyzw01_]+)', m.group(1))
                if comps and set(comps.group(1)) & ({'x', 'y', 'z'} - written):
                    return True
            continue
        parts = [p.strip() for p in re.split(r',\s*(?![^()]*\))', m.group(1))]
        for p in parts[1:]:
            for c in re.findall(r'R0\.([xyzw])', p):
                if c in 'xyz' and c not in written:
                    return True
        dm = re.match(r'R0\.([xyzw_]+)', parts[0])
        if dm:
            written |= set(dm.group(1)) - {'_'}
    return False


def test_rpx(rpx):
    from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN
    from unicorn import ppc_const as P
    import rpx_patch
    args = T.rpx_args(rpx)
    check(args == ['0x032F8520=0xD3C100B0', '0x032F8538=0xD00100B4'], 'rpx patch args: %s' % ' '.join(args))
    d, _shoff, _ent, secs = rpx_patch.load(rpx)
    cache = {}
    start, end = 0x032F851C, 0x032F855C           # fmr f28, f31 .. the alpha store
    code = b''.join(struct.pack('>I', rpx_patch.read_u32(d, secs, a, cache)) for a in range(start, end + 4, 4))
    for patched in (False, True):
        c = bytearray(code)
        for a, (old, new) in T.VERTEX_PATCH.items():
            struct.pack_into('>I', c, a - start, new if patched else old)
        mu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
        mu.mem_map(0x03200000, 0x200000)
        mu.mem_map(0x20000000, 0x10000)
        mu.mem_write(start, bytes(c))
        mu.reg_write(P.UC_PPC_REG_MSR, mu.reg_read(P.UC_PPC_REG_MSR) | 0x2000)     # FP on
        trail, sp = 0x20000000, 0x20008000
        mu.mem_write(trail + 0x30, struct.pack('>f', 0.375))             # the fade
        mu.mem_write(trail + 0xB8, struct.pack('>I', 0x20004000))         # history
        mu.reg_write(P.UC_PPC_REG_27, trail)
        mu.reg_write(P.UC_PPC_REG_1, sp)
        mu.reg_write(P.UC_PPC_REG_21, 0x20006000)
        mu.reg_write(P.UC_PPC_REG_24, 0)
        fpr = lambda n, x: mu.reg_write(getattr(P, 'UC_PPC_REG_FPR%d' % n), struct.unpack('>Q', struct.pack('>d', x))[0])  # noqa: E731
        fpr(31, 1.0)
        fpr(30, 0.25)                                                       # t
        fpr(24, 0.1)
        mu.emu_start(start, end + 4)
        col = struct.unpack('>4f', bytes(mu.mem_read(sp + 0xB0, 16)))
        want = (0.25, 0.375, 1.0, 0.75 * 0.375) if patched else (1.0, 1.0, 1.0, 0.75 * 0.375)
        check(all(abs(a - b) < 1e-6 for a, b in zip(col, want)),
              '%s vertex colour %s' % ('patched' if patched else 'vanilla', ', '.join('%.4g' % x for x in col)))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    vanilla = open(sys.argv[1], 'rb').read()
    program, gprs = T.assemble()
    new = T.build_nsh(vanilla, program, gprs)
    vrecs, nrecs = T.records(vanilla), T.records(new)
    check([r[0] for r in nrecs] == [0x4F000001, 0x4F000002, 0x4F000003, 0x4F0003E9, 0x4F0003EA],
          'record ids %s' % ' '.join('%X' % r[0] for r in nrecs))
    check(struct.unpack_from('>I', new, 4)[0] == len(new) and len(new) % T.RECORD_ALIGN == 0, 'header size')
    check(struct.unpack_from('>I', new, 8)[0] == 0x02000005, 'header count word 0x%08X' % struct.unpack_from('>I', new, 8)[0])
    by = {r[0]: r for r in nrecs}
    for sid, o, s in vrecs:
        _sid, no, ns = by[sid]
        check(new[no:no + ns] == vanilla[o:o + s], 'record %X unchanged' % sid)
    _s, r1, _ = by[0x4F000001]
    _s, r3, s3 = by[0x4F000003]
    check(r3 % T.RECORD_ALIGN == 0 and s3 % T.RECORD_ALIGN == 0, 'record 3 at 0x%X, 0x%X bytes' % (r3, s3))
    vs1, vs3 = T.programs(new, r1)[0], T.programs(new, r3)[0]
    check(new[vs1[1]:vs1[1] + vs1[2]] == new[vs3[1]:vs3[1] + vs3[2]], 'vertex GX2 file = shader 1\'s')
    p1, p3 = pixel_program(new, r1), pixel_program(new, r3)
    h1 = struct.unpack('>%dI' % (p1[1][2] // 4), new[p1[1][1]:p1[1][1] + p1[1][2]])
    h3 = struct.unpack('>%dI' % (p3[1][2] // 4), new[p3[1][1]:p3[1][1] + p3[1][2]])
    diff = [i for i in range(len(h1)) if h1[i] != h3[i]]
    check(diff == [T.HDR_RESOURCES, T.HDR_SIZE] and h3[0] & 0xFF == gprs and h3[T.HDR_SIZE] == len(program),
          'pixel header: words %s differ (GPRs %d, size 0x%X)' % (diff, h3[0] & 0xFF, h3[T.HDR_SIZE]))
    check(new[p3[2][1]:p3[2][1] + p3[2][2]] == program, 'pixel program in place')
    # the vanilla pixel programs leave the vertex rgb alone
    tmp = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), '.trail_shader_test.nsh')
    open(tmp, 'wb').write(new)
    try:
        for sid, o, _s in vrecs:
            _g, _h, (_ph, po, ps) = pixel_program(vanilla, o)
            lines = disasm(sys.argv[1], po, ps)
            check(not reads_rgb_first(lines), 'shader %X reads only the vertex alpha' % sid)
        lines = disasm(tmp, p3[2][1], p3[2][2])
    finally:
        os.remove(tmp)
    check(reads_rgb_first(lines), 'shader 3 reads the vertex colour (the reader check works)')
    test_shader(lines)
    if len(sys.argv) > 2:
        test_rpx(sys.argv[2])
    print('%d failed' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
