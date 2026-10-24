#!/usr/bin/env python3
"""Trail shader 3: Ultimate's retracting sword trail in Smash 4, for trails converted from Ultimate.

  python3 tools/trail_shader.py nsh VANILLA/shader/effect_trail.nsh OUT/effect_trail.nsh
  python3 tools/rpx_patch.py IN.rpx OUT.rpx ... $(python3 tools/trail_shader.py rpx IN.rpx)
  python3 tools/trail_shader.py acmd IN/effect.bin OUT/effect.bin     (Sword_Glow Shader 1 -> 3)

Smash 4 and Ultimate keep a trail alike (docs/native-notes.md "The trail shaders"): a fade value
(+0x30) runs 1 -> 0 over `Terminate_Sword_Glow`'s frames. Smash 4 multiplies the vertex alpha by it
and slides the texture by 1 - fade; Ultimate's shader 101 instead samples the second texture (a
mask) at U = 1 - t / fade, t = the point's place along the trail (0 at the blade, 1 at the tail),
which cuts the trail back into the sword, and slides the first by half that.

- `nsh`: adds shader 0x4F000003 to effect_trail.nsh (a record after 0x4F000002, ids stay sorted;
  the header's low 24 bits are the record count). Its vertex program is shader 1's; its pixel
  program is tools/shaders/trail_retract.psh, assembled with tools/latte_dis/latte-asm
  (tools/latte_dis/build_asm.sh), with shader 1's pixel header (the same inputs, samplers and
  hdrRange block; the GPR count and program size from the new program).
- `rpx`: the textured trail's vertex writer (0x032F8050, the branch at 0x032F84D0) fills the
  vertex colour's rgb with 1.0, which no trail shader reads (1, 2, 1001 and 1002 use its alpha
  only). Two stores now put t (f30) in red and the fade (+0x30, f0) in green, so shader 3 has them.
- `acmd`: every `Sword_Glow` / `Sword_Glow2` of an effect.bin gets Shader 3 (a fighter converted
  before tools/ultimate_acmd.py wrote 3).
Shader 3's textures (tools/ultimate_trails.py --shader 3): Texture1 = Ultimate's colour texture
as is, Texture2 = its mask in alpha with the colour gain / 2 (AFTER_IMAGE4_ON's arg 28) in rgb.
"""
import os
import re
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

LATTE_ASM = os.path.join(HERE, 'latte_dis', 'latte-asm')
PSH = os.path.join(HERE, 'shaders', 'trail_retract.psh')
BASE_ID, NEW_ID, AFTER_ID = 0x4F000001, 0x4F000003, 0x4F000002
RECORD_ALIGN = 0x80
PS_HEADER, PS_PROGRAM, END = 6, 7, 1
HDR_RESOURCES, HDR_SIZE = 0, 41        # GX2PixelShader words: sq_pgm_resources_ps, program size
# vertex writer stores (0x032F8520 / 0x032F8538): (original, new)
VERTEX_PATCH = {
    0x032F8520: (0xD38100B0, 0xD3C100B0),   # stfs f28, 0xB0(r1) -> stfs f30, 0xB0(r1): red = t
    0x032F8538: (0xD38100B4, 0xD00100B4),   # stfs f28, 0xB4(r1) -> stfs f0, 0xB4(r1): green = fade
}
SHADER = 3


def records(d):
    """[(shader id, offset, size)] of an NSP3 file"""
    assert d[:4] == b'NSP3', d[:4]
    n = struct.unpack_from('>I', d, 8)[0] & 0xFFFFFF
    out, o = [], 0x20
    for _ in range(n):
        sid, k = struct.unpack_from('>II', d, o)
        size = struct.unpack_from('>I', d, o + 8 + 8 * k)[0]
        out.append((sid, o, size))
        o += size
    return out


def gsh_blocks(d, g):
    """[(block type, header offset, data offset, data size)] of the GX2 file at g"""
    assert d[g:g + 4] == b'Gfx2'
    o, out = g + struct.unpack_from('>I', d, g + 4)[0], []
    while d[o:o + 4] == b'BLK{':
        head, _major, _minor, typ, size = struct.unpack_from('>5I', d, o + 4)
        out.append((typ, o, o + head, size))
        if typ == END:
            break
        o += head + size
    return out


def programs(d, rec):
    """the record's program descriptors: [(descriptor offset, gsh offset, gsh size)]"""
    _sid, k = struct.unpack_from('>II', d, rec)
    offs = struct.unpack_from('>%dI' % (2 * k), d, rec + 8)
    out = []
    for off in offs[:k]:
        g, one, size, _ = struct.unpack_from('>4I', d, rec + off)
        assert one == 1, hex(one)
        out.append((rec + off, rec + g, size))
    return out


def assemble(psh=PSH):
    """(program bytes, GPR count) of a pixel shader source"""
    if not os.path.exists(LATTE_ASM):
        sys.exit('%s missing: run tools/latte_dis/build_asm.sh' % LATTE_ASM)
    gprs = int(re.search(r'\$SQ_PGM_RESOURCES_PS\.NUM_GPRS\s*=\s*(\d+)', open(psh).read()).group(1))
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, 'ps.gsh')
        r = subprocess.run([LATTE_ASM, 'assemble', '--psh', psh, out], capture_output=True, text=True)
        if r.returncode or not os.path.exists(out):
            sys.exit('latte-asm failed: %s%s' % (r.stdout, r.stderr))
        g = open(out, 'rb').read()
    prog = [g[o:o + s] for t, _h, o, s in gsh_blocks(g, 0) if t == PS_PROGRAM]
    assert len(prog) == 1
    return prog[0], gprs


def pixel_gsh(d, g, program, gprs):
    """the pixel GX2 file at g with its program replaced (header: GPR count and size updated)"""
    out = bytearray(d[g:g + struct.unpack_from('>I', d, g + 4)[0]])
    for typ, h, o, size in gsh_blocks(d, g):
        head = bytearray(d[h:o])
        data = bytearray(d[o:o + size])
        if typ == PS_HEADER:
            res = struct.unpack_from('>I', data, 4 * HDR_RESOURCES)[0]
            struct.pack_into('>I', data, 4 * HDR_RESOURCES, (res & ~0xFF) | gprs)
            assert struct.unpack_from('>I', data, 4 * HDR_SIZE)[0] == next(
                s for t, _h, _o, s in gsh_blocks(d, g) if t == PS_PROGRAM)
            struct.pack_into('>I', data, 4 * HDR_SIZE, len(program))
        elif typ == PS_PROGRAM:
            data = bytearray(program)
        struct.pack_into('>I', head, 0x14, len(data))
        out += head + data
    return bytes(out)


def build_nsh(vanilla, program, gprs):
    recs = records(vanilla)
    ids = [r[0] for r in recs]
    assert NEW_ID not in ids and BASE_ID in ids and AFTER_ID in ids, [hex(i) for i in ids]
    _sid, rec, size = recs[ids.index(BASE_ID)]
    progs = programs(vanilla, rec)
    pix = [p for p in progs if any(t == PS_HEADER for t, *_ in gsh_blocks(vanilla, p[1]))]
    assert len(progs) == 2 and len(pix) == 1, progs
    desc, g, gsize = pix[0]
    assert g + gsize <= rec + size and all(p[1] < g for p in progs if p != pix[0])
    new_ps = pixel_gsh(vanilla, g, program, gprs)
    # the record up to the pixel GX2 file (descriptors, the vertex one) as shader 1's, then the new one
    body = bytearray(vanilla[rec:g]) + new_ps
    body += b'\0' * (-len(body) % RECORD_ALIGN)
    struct.pack_into('>I', body, 0, NEW_ID)
    k = struct.unpack_from('>I', body, 4)[0]
    struct.pack_into('>I', body, 8 + 8 * k, len(body))
    struct.pack_into('>I', body, desc - rec + 8, len(new_ps))
    _a, at, asize = recs[ids.index(AFTER_ID)]
    out = bytearray(vanilla[:at + asize]) + body + vanilla[at + asize:]
    count = struct.unpack_from('>I', out, 8)[0]
    struct.pack_into('>I', out, 8, (count & ~0xFFFFFF) | (len(recs) + 1))
    struct.pack_into('>I', out, 4, len(out))
    return bytes(out)


def rpx_args(rpx):
    import rpx_patch
    d, _shoff, _ent, secs = rpx_patch.load(rpx)
    cache, out = {}, []
    for a, (old, new) in sorted(VERTEX_PATCH.items()):
        cur = rpx_patch.read_u32(d, secs, a, cache)
        assert cur in (old, new), '0x%08X: 0x%08X' % (a, cur)
        out.append('0x%08X=0x%08X' % (a, new))
    return out


def set_acmd_shader(src, dst, shader=SHADER):
    import acmd
    f = acmd.ACMDFile.load(src)
    ids = {acmd.BY_NAME[n] for n in ('sword_glow', 'sword_glow2') if n in acmd.BY_NAME}
    n = 0
    for script in f.scripts.values():
        for c in script:
            if c.ident in ids:
                c.params[-1] = shader
                n += 1
    f.save(dst)
    return n


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ('nsh', 'rpx', 'acmd'):
        sys.exit(__doc__)
    if sys.argv[1] == 'nsh':
        program, gprs = assemble()
        out = build_nsh(open(sys.argv[2], 'rb').read(), program, gprs)
        open(sys.argv[3], 'wb').write(out)
        sys.stderr.write('%s: shader 0x%08X added (%d GPRs, 0x%X-byte program), %d records\n' % (
            sys.argv[3], NEW_ID, gprs, len(program), len(records(out))))
    elif sys.argv[1] == 'rpx':
        print(' '.join(rpx_args(sys.argv[2])))
    else:
        n = set_acmd_shader(sys.argv[2], sys.argv[3])
        sys.stderr.write('%s: %d Sword_Glow -> Shader %d\n' % (sys.argv[3], n, SHADER))


if __name__ == '__main__':
    main()
