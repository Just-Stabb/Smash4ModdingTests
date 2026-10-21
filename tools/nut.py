#!/usr/bin/env python3
"""Smash 4 Wii U textures (.nut, NTWU): read a texture to RGBA and write one back in the same format.

  python3 tools/nut.py info FILE.nut
  python3 tools/nut.py png FILE.nut OUT.png            first texture's first mip, as a PNG
  python3 tools/nut.py replace FILE.nut IMAGE OUT.nut  IMAGE (any size; resized) into the texture,
                                                       same format / size / ID, mips rebuilt
  python3 tools/nut.py ntp3 OUT.nut ID:FORMAT:IMAGE...  new NTP3 .nut (FORMAT dxt1, dxt5 or rgba)

Header layout and the GX2 (de)swizzle follow Smash Forge's NUT.cs / GTX.cs (MIT; GTX.cs ports
AboodXD's GTX Extractor), as tools/Sm4shCommand's Viewer/Textures.cs does. Formats: 0x1A RGBA8,
0x31 BC1, 0x32 BC2, 0x33 BC3, 0x34 BC4, 0x35 BC5. BC encoding is a simple fit (BC1:
endpoints = the block's extremes along its main color axis; BC4: min / max), good enough for UI
pictures. Only single-mip textures are written (the stage-select icons all are).

NTP3 (write_ntp3): the untiled .nut the game also loads (some of Battlefield's own model.nut are
NTP3), so new textures of any size need no GX2 tiling. Layout as Smash Forge's NUT.Rebuild
(version 0x0200): formats 0 DXT1, 2 DXT5, 14 RGBA8 (stored A, R, G, B), full mip chains.
"""
import struct
import sys
import zlib

import numpy as np


# ---------------------------------------------------------------- container
def be32(d, o):
    return struct.unpack('>i', d[o:o + 4])[0]


def be16(d, o):
    return struct.unpack('>H', d[o:o + 2])[0]


class Tex:
    """one texture of a .nut: where its header / GX2 surface / data are"""
    def __init__(self, d, hp):
        self.hp = hp
        self.header_size = be16(d, hp + 12)
        self.data_off = be32(d, hp + 32) + hp
        self.mip_off = be32(d, hp + 36) + hp
        self.gtx = be32(d, hp + 40) + hp
        g = self.gtx
        self.dim, self.w, self.h, self.depth, self.levels, self.fmt, self.aa, self.use, self.image_size, \
            self.image_ptr, self.mip_size, self.mip_ptr, self.tile_mode, self.swizzle, self.alignment, \
            self.pitch = struct.unpack('>16i', d[g:g + 64])
        self.mip_offsets = list(struct.unpack('>13i', d[g + 64:g + 64 + 52]))
        self.gidx = d.find(b'GIDX', hp, hp + self.header_size)
        self.tex_id = be32(d, self.gidx + 8) if self.gidx >= 0 else None


def load(path):
    d = open(path, 'rb').read()
    if d[:2] == b'\x78\x9c':
        d = zlib.decompress(d)
    assert d[:4] == b'NTWU', d[:4]
    count = be16(d, 6)
    texs = []
    hp = 0x10
    for _ in range(count):
        t = Tex(d, hp)
        texs.append(t)
        hp += t.header_size
    return d, texs


# ---------------------------------------------------------------- GX2 addressing
def _bpp(fmt):
    f = fmt & 0x3F
    return {0x1A: 32, 0x08: 16, 0x0A: 16, 0x0B: 16, 0x31: 64, 0x34: 64, 0x32: 128, 0x33: 128, 0x35: 128}[f]


def _is_bc(fmt):
    return 0x31 <= (fmt & 0x3F) <= 0x35


def _pixel_index(x, y, bpp):
    bits = ((x & 4) << 1) | ((y & 2) << 3) | ((y & 4) << 3)
    if bpp in (32, 96, 16):
        bits |= (x & 1) | (x & 2) | ((y & 1) << 2)
    elif bpp == 64:
        bits |= (x & 1) | ((y & 1) << 1) | ((x & 2) << 1)
    elif bpp == 128:
        bits |= (y & 1) | ((x & 1) << 1) | ((x & 2) << 1)
    return bits


def _macro_tiled(x, y, bpp, pitch, swz):
    pi = _pixel_index(x, y, bpp)
    elem = (bpp * pi) >> 3
    pipe = ((y ^ x) >> 3) & 1
    bank = (((y >> 5) ^ (x >> 3)) & 1) | ((((y >> 4) ^ (x >> 4)) & 1) << 1)
    bank_pipe = ((pipe + 2 * bank) ^ swz) % 9
    pipe = bank_pipe % 2
    bank = bank_pipe // 2
    macro_bytes = (bpp * 512 + 7) >> 3
    macro_off = (x // 32 + pitch // 32 * (y // 16)) * macro_bytes
    u1 = elem + (macro_off >> 3)
    u2 = u1 & ~0xFF
    return (u2 << 3) | (0xFF & u1) | (pipe << 8) | (bank << 9)


def element_offsets(ew, eh, bpp, tile_mode, swizzle, pitch):
    """byte offset in the surface of each element (pixel / 4x4 block), [eh, ew]"""
    eb = bpp // 8
    swz = ((swizzle >> 8) & 1) + (((swizzle >> 9) & 3) << 1)
    y, x = np.mgrid[0:eh, 0:ew].astype(np.int64)
    if tile_mode in (0, 1):
        return (y * pitch + x) * eb
    if tile_mode in (2, 3):
        return ((y // 8) * (pitch // 8) + x // 8) * 64 * eb + ((_pixel_index(x, y, bpp) * bpp) >> 3)
    return _macro_tiled(x, y, bpp, pitch, swz)


# ---------------------------------------------------------------- BC decode
def _rgb565(v):
    return np.stack([((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31], -1)


def _bc1_colors(blocks, punch):
    c0 = blocks[:, 0].astype(np.int32) | (blocks[:, 1].astype(np.int32) << 8)
    c1 = blocks[:, 2].astype(np.int32) | (blocks[:, 3].astype(np.int32) << 8)
    a, b = _rgb565(c0), _rgb565(c1)
    pal = np.zeros((len(blocks), 4, 4), dtype=np.int32)
    pal[:, 0, :3], pal[:, 1, :3] = a, b
    pal[:, :2, 3] = 255
    four = (c0 > c1) | (not punch)
    pal[:, 2, :3] = np.where(four[:, None], (2 * a + b) // 3, (a + b) // 2)
    pal[:, 3, :3] = np.where(four[:, None], (a + 2 * b) // 3, 0)
    pal[:, 2, 3] = 255
    pal[:, 3, 3] = np.where(four, 255, 0)
    bits = blocks[:, 4].astype(np.uint32) | (blocks[:, 5].astype(np.uint32) << 8) | \
        (blocks[:, 6].astype(np.uint32) << 16) | (blocks[:, 7].astype(np.uint32) << 24)
    idx = (bits[:, None] >> (2 * np.arange(16))) & 3
    return np.take_along_axis(pal, idx[:, :, None].astype(np.int64).repeat(4, 2), 1)


def _bc4_values(blocks):
    a0, a1 = blocks[:, 0].astype(np.int32), blocks[:, 1].astype(np.int32)
    pal = np.zeros((len(blocks), 8), dtype=np.int32)
    pal[:, 0], pal[:, 1] = a0, a1
    six = a0 > a1
    for i in range(1, 7):
        pal[:, i + 1] = np.where(six, ((7 - i) * a0 + i * a1) // 7, 0)
    for i in range(1, 5):
        pal[:, i + 1] = np.where(six, pal[:, i + 1], ((5 - i) * a0 + i * a1) // 5)
    pal[:, 6] = np.where(six, pal[:, 6], 0)
    pal[:, 7] = np.where(six, pal[:, 7], 255)
    bits = np.zeros(len(blocks), dtype=np.uint64)
    for i in range(6):
        bits |= blocks[:, 2 + i].astype(np.uint64) << np.uint64(8 * i)
    idx = (bits[:, None] >> (np.uint64(3) * np.arange(16, dtype=np.uint64))) & np.uint64(7)
    return np.take_along_axis(pal, idx.astype(np.int64), 1)


def decode(d, t, level=0):
    """RGBA uint8 [h, w, 4] of the texture's first mip"""
    f = t.fmt & 0x3F
    bpp = _bpp(f)
    bc = _is_bc(f)
    w, h = t.w, t.h
    ew, eh = ((w + 3) // 4, (h + 3) // 4) if bc else (w, h)
    eb = bpp // 8
    src = np.frombuffer(d[t.data_off:t.data_off + t.image_size], dtype=np.uint8)
    offs = element_offsets(ew, eh, bpp, t.tile_mode, t.swizzle, t.pitch)
    lin = src[(offs[..., None] + np.arange(eb)).reshape(-1, eb)].reshape(eh * ew, eb)
    if not bc:
        img = lin.reshape(h, w, 4) if f == 0x1A else None
        if img is None:
            raise NotImplementedError('format 0x%X' % f)
        return img.copy()
    if f == 0x31:
        px = _bc1_colors(lin, True)
    elif f == 0x32:
        px = _bc1_colors(lin[:, 8:], False)
        a = np.stack([(lin[:, j // 2] >> (4 * (j & 1))) & 15 for j in range(16)], 1).astype(np.int32) * 17
        px[:, :, 3] = a
    elif f == 0x33:
        px = _bc1_colors(lin[:, 8:], False)
        px[:, :, 3] = _bc4_values(lin[:, :8])
    elif f == 0x34:
        v = _bc4_values(lin)
        px = np.stack([v, v, v, np.full_like(v, 255)], 2)
    else:  # 0x35 BC5: red, green
        r, g = _bc4_values(lin[:, :8]), _bc4_values(lin[:, 8:])
        px = np.stack([r, g, np.zeros_like(r), np.full_like(r, 255)], 2)
    img = px.reshape(eh, ew, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(eh * 4, ew * 4, 4)
    return img[:h, :w].astype(np.uint8)


# ---------------------------------------------------------------- BC encode
def _blocks(img):
    """[h, w, 4] -> [n, 16, 4] 4x4 blocks in row order (edges repeated)"""
    h, w = img.shape[:2]
    H, W = (h + 3) // 4 * 4, (w + 3) // 4 * 4
    pad = np.pad(img, ((0, H - h), (0, W - w), (0, 0)), mode='edge').astype(np.int32)
    return pad.reshape(H // 4, 4, W // 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 4), W // 4, H // 4


def _enc_bc4(v):
    """v [n, 16] 0-255 -> [n, 8] (8-value mode: a0 = max > a1 = min)"""
    a0, a1 = v.max(1), v.min(1)
    a1 = np.where(a0 == a1, np.maximum(a0 - 1, 0), a1)
    a0 = np.where(a0 == a1, a1 + 1, a0)
    pal = np.stack([a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)], 1)
    idx = np.abs(v[:, :, None] - pal[:, None, :]).argmin(2).astype(np.uint64)
    bits = np.zeros(len(v), dtype=np.uint64)
    for j in range(16):
        bits |= idx[:, j] << np.uint64(3 * j)
    out = np.zeros((len(v), 8), dtype=np.uint8)
    out[:, 0], out[:, 1] = a0, a1
    for i in range(6):
        out[:, 2 + i] = ((bits >> np.uint64(8 * i)) & np.uint64(0xFF)).astype(np.uint8)
    return out


def _to565(c):
    return ((c[..., 0] * 31 + 127) // 255 << 11) | ((c[..., 1] * 63 + 127) // 255 << 5) | ((c[..., 2] * 31 + 127) // 255)


def _enc_bc1(rgb):
    """rgb [n, 16, 3] -> [n, 8] (4-color mode; endpoints = the block's extremes along its main axis)"""
    mean = rgb.mean(1, keepdims=True)
    d = rgb - mean
    cov = np.einsum('nki,nkj->nij', d, d)
    axis = np.ones((len(rgb), 3))
    for _ in range(4):
        axis = np.einsum('nij,nj->ni', cov, axis)
        axis /= np.linalg.norm(axis, axis=1, keepdims=True) + 1e-9
    proj = np.einsum('nki,ni->nk', d, axis)
    lo = rgb[np.arange(len(rgb)), proj.argmin(1)]
    hi = rgb[np.arange(len(rgb)), proj.argmax(1)]
    c0, c1 = _to565(hi), _to565(lo)
    swap = c0 < c1
    c0, c1 = np.where(swap, c1, c0), np.where(swap, c0, c1)
    same = c0 == c1
    c1 = np.where(same & (c1 > 0), c1 - 1, c1)
    c0 = np.where(same & (c0 == 0), 1, c0)
    a, b = _rgb565(c0), _rgb565(c1)
    pal = np.stack([a, b, (2 * a + b) // 3, (a + 2 * b) // 3], 1)
    idx = ((rgb[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(3).argmin(2).astype(np.uint32)
    bits = np.zeros(len(rgb), dtype=np.uint32)
    for j in range(16):
        bits |= idx[:, j] << np.uint32(2 * j)
    out = np.zeros((len(rgb), 8), dtype=np.uint8)
    out[:, 0], out[:, 1], out[:, 2], out[:, 3] = c0 & 0xFF, c0 >> 8, c1 & 0xFF, c1 >> 8
    for i in range(4):
        out[:, 4 + i] = (bits >> np.uint32(8 * i)) & 0xFF
    return out


def encode(img, t):
    """RGBA [t.h, t.w, 4] -> the texture's image data (t's format, tiling, swizzle, pitch)"""
    f = t.fmt & 0x3F
    bpp = _bpp(f)
    eb = bpp // 8
    blocks, ew, eh = _blocks(img)
    if f == 0x31:
        lin = _enc_bc1(blocks[:, :, :3])
    elif f == 0x33:
        lin = np.concatenate([_enc_bc4(blocks[:, :, 3]), _enc_bc1(blocks[:, :, :3])], 1)
    elif f == 0x34:
        lin = _enc_bc4(blocks[:, :, 0])
    elif f == 0x35:
        lin = np.concatenate([_enc_bc4(blocks[:, :, 0]), _enc_bc4(blocks[:, :, 1])], 1)
    elif f == 0x1A:
        lin = np.ascontiguousarray(img).reshape(-1, 4)
        ew, eh = img.shape[1], img.shape[0]
    else:
        raise NotImplementedError('format 0x%X' % f)
    out = np.zeros(t.image_size, dtype=np.uint8)
    offs = element_offsets(ew, eh, bpp, t.tile_mode, t.swizzle, t.pitch).reshape(-1)
    for k in range(eb):
        out[offs + k] = lin[:, k]
    return out.tobytes()


def replace(d, t, img):
    """the .nut data d with texture t's first mip replaced by img (RGBA [t.h, t.w, 4])"""
    assert t.levels <= 1, 'mipmapped textures not supported'
    data = encode(img, t)
    return d[:t.data_off] + data + d[t.data_off + len(data):]


# ---------------------------------------------------------------- NTP3
NTP3_FORMATS = {'dxt1': 0, 'dxt5': 2, 'rgba': 14}


def ntp3_mip(img, fmt):
    """RGBA [h, w, 4] -> NTP3 data of format fmt (0 / 2 / 14)"""
    if fmt == 14:
        return np.ascontiguousarray(img[..., [3, 0, 1, 2]]).tobytes()
    blocks, _, _ = _blocks(img)
    if fmt == 0:
        return _enc_bc1(blocks[:, :, :3]).tobytes()
    return np.concatenate([_enc_bc4(blocks[:, :, 3]), _enc_bc1(blocks[:, :, :3])], 1).tobytes()


def mip_chain(img, smallest=4):
    """RGBA [h, w, 4] and its halvings down to `smallest` (box filter)"""
    from PIL import Image
    out = [img]
    while min(out[-1].shape[:2]) > smallest:
        h, w = out[-1].shape[:2]
        out.append(np.asarray(Image.fromarray(out[-1], 'RGBA').resize((max(1, w // 2), max(1, h // 2)), Image.BOX)))
    return out


def write_ntp3(textures):
    """textures: [(tex_id, fmt, [mip RGBA arrays])] -> .nut bytes"""
    heads, datas = [], []
    for tex_id, fmt, mips in textures:
        data = [ntp3_mip(m, fmt) for m in mips]
        data = [x + b'\0' * (-len(x) % 0x10) for x in data]
        hs = 0x50 + (4 * len(mips) if len(mips) > 1 else 0)
        hs += -hs % 0x10
        heads.append((tex_id, fmt, mips, data, hs))
        datas.append(b''.join(data))
    out = bytearray(b'NTP3' + struct.pack('>HHII', 0x0200, len(textures), 0, 0))
    remaining = sum(h[4] for h in heads)
    data_before = 0
    for (tex_id, fmt, mips, data, hs), blob in zip(heads, datas):
        h, w = mips[0].shape[:2]
        head = struct.pack('>IIIHHBBBBHHII', len(blob) + hs, 0, len(blob), hs, 0, 0, len(mips), 0, fmt, w, h, 0, 0)
        head += struct.pack('>IIII', remaining + data_before, 0, 0, 0)
        if len(mips) > 1:
            head += b''.join(struct.pack('>I', len(x)) for x in data)
        head += b'\0' * (-len(head) % 0x10)
        head += b'eXt\0' + struct.pack('>III', 0x20, 0x10, 0)
        head += b'GIDX' + struct.pack('>III', 0x10, tex_id, 0)
        assert len(head) == hs
        out += head
        remaining -= hs
        data_before += len(blob)
    for blob in datas:
        out += blob
    return bytes(out)


# ---------------------------------------------------------------- NTWU (write)
NTWU_CODE = {0x31: 0, 0x33: 2, 0x1A: 14}          # GX2 format -> the .nut header's format byte
NTWU_ALIGN = {0x31: 0x1000, 0x33: 0x2000, 0x1A: 0x800}


class Surface:
    """a single-mip 2D texture as the game's own: tile mode 4, pitch (elements) a multiple of 32,
    rows to a multiple of 16 (checked against all 626 of Battlefield's textures)"""
    def __init__(self, fmt, w, h, swizzle=0xD0000):
        self.fmt, self.w, self.h, self.swizzle = fmt, w, h, swizzle
        bc = _is_bc(fmt)
        ew, eh = ((w + 3) // 4, (h + 3) // 4) if bc else (w, h)
        self.tile_mode, self.alignment = 4, NTWU_ALIGN[fmt]
        self.pitch = -(-ew // 32) * 32
        self.image_size = self.pitch * (-(-eh // 16) * 16) * (_bpp(fmt) // 8)

    def gx2(self):
        return struct.pack('>16i13i12x', 1, self.w, self.h, 1, 1, self.fmt, 0, 1, self.image_size, 0, 0, 0,
                           self.tile_mode, self.swizzle, self.alignment, self.pitch, *[0] * 13)


def write_ntwu(textures):
    """textures: [(tex_id, GX2 format 0x31 BC1 / 0x33 BC3 / 0x1A RGBA8, RGBA [h, w, 4])] -> .nut bytes:
    one mip each, laid out as Battlefield's single-mip .nut (the headers, the data from 0x1000 each
    at its alignment, the GX2 surfaces at the end)"""
    hs = 0x50
    surfs = [Surface(fmt, img.shape[1], img.shape[0]) for _, fmt, img in textures]
    out = bytearray(b'NTWU' + struct.pack('>HH8x', 0x020E, len(textures)))
    pos = 0x10 + hs * len(textures)
    offs = []
    for s in surfs:
        pos = -(-max(pos, 0x1000) // s.alignment) * s.alignment
        offs.append(pos)
        pos += s.image_size
    gtx = pos
    for i, ((tex_id, fmt, img), s) in enumerate(zip(textures, surfs)):
        hp = 0x10 + hs * i
        out += struct.pack('>IIIHHBBBBHHII', s.image_size + hs, 0, s.image_size, hs, 0, 0, 1, 0, NTWU_CODE[fmt],
                           s.w, s.h, 1, 0)
        out += struct.pack('>IIII', offs[i] - hp, 0, gtx + 0x80 * i - hp, 0)
        out += b'eXt\0' + struct.pack('>III', 0x20, 0x10, 0)
        out += b'GIDX' + struct.pack('>III', 0x10, tex_id, 0)
    for (tex_id, fmt, img), s, o in zip(textures, surfs, offs):
        out += b'\0' * (o - len(out))
        out += encode(img, s)
    for s in surfs:
        out += s.gx2()
    return bytes(out)


def main():
    cmd = sys.argv[1]
    if cmd == 'info':
        d, texs = load(sys.argv[2])
        for t in texs:
            print('id 0x%08X %dx%d fmt 0x%X tile %d swizzle 0x%X pitch %d levels %d image 0x%X mips 0x%X' %
                  (t.tex_id or 0, t.w, t.h, t.fmt, t.tile_mode, t.swizzle, t.pitch, t.levels, t.image_size, t.mip_size))
    elif cmd == 'png':
        from PIL import Image
        d, texs = load(sys.argv[2])
        Image.fromarray(decode(d, texs[0]), 'RGBA').save(sys.argv[3])
    elif cmd == 'replace':
        from PIL import Image
        d, texs = load(sys.argv[2])
        t = texs[0]
        img = np.asarray(Image.open(sys.argv[3]).convert('RGBA').resize((t.w, t.h), Image.LANCZOS))
        open(sys.argv[4], 'wb').write(replace(d, t, img))
    elif cmd == 'ntp3':
        from PIL import Image
        texs = []
        for arg in sys.argv[3:]:
            tid, fmt, path = arg.split(':', 2)
            img = np.asarray(Image.open(path).convert('RGBA'))
            texs.append((int(tid, 0), NTP3_FORMATS[fmt], mip_chain(img)))
        open(sys.argv[2], 'wb').write(write_ntp3(texs))


if __name__ == '__main__':
    main()
