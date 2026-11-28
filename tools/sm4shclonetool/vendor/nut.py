"""Smash 4 Wii U textures (.nut, NTWU / NTP3): read a texture to RGBA and write one back. Header layout and the GX2
(de)swizzle follow Smash Forge's NUT.cs / GTX.cs (MIT; GTX.cs ports AboodXD's GTX Extractor).

Adapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; the tool
sets the code addresses itself, see its README "The executable")."""
import struct
import sys
import zlib
import numpy as np

def be32(d, o):
    return struct.unpack('>i', d[o:o + 4])[0]

def be16(d, o):
    return struct.unpack('>H', d[o:o + 2])[0]

class Tex:

    def __init__(self, d, hp):
        self.hp = hp
        self.header_size = be16(d, hp + 12)
        self.data_off = be32(d, hp + 32) + hp
        self.mip_off = be32(d, hp + 36) + hp
        self.gtx = be32(d, hp + 40) + hp
        g = self.gtx
        self.dim, self.w, self.h, self.depth, self.levels, self.fmt, self.aa, self.use, self.image_size, self.image_ptr, self.mip_size, self.mip_ptr, self.tile_mode, self.swizzle, self.alignment, self.pitch = struct.unpack('>16i', d[g:g + 64])
        self.mip_offsets = list(struct.unpack('>13i', d[g + 64:g + 64 + 52]))
        self.gidx = d.find(b'GIDX', hp, hp + self.header_size)
        self.tex_id = be32(d, self.gidx + 8) if self.gidx >= 0 else None

def load(path):
    return load_bytes(open(path, 'rb').read())

def load_bytes(d):
    if d[:2] == b'x\x9c':
        d = zlib.decompress(d)
    assert d[:4] == b'NTWU', d[:4]
    count = be16(d, 6)
    texs = []
    hp = 16
    for _ in range(count):
        t = Tex(d, hp)
        texs.append(t)
        hp += t.header_size
    return (d, texs)

def _bpp(fmt):
    f = fmt & 63
    return {26: 32, 8: 16, 10: 16, 11: 16, 49: 64, 52: 64, 50: 128, 51: 128, 53: 128}[f]

def _is_bc(fmt):
    return 49 <= fmt & 63 <= 53

def _pixel_index(x, y, bpp):
    bits = (x & 4) << 1 | (y & 2) << 3 | (y & 4) << 3
    if bpp in (32, 96, 16):
        bits |= x & 1 | x & 2 | (y & 1) << 2
    elif bpp == 64:
        bits |= x & 1 | (y & 1) << 1 | (x & 2) << 1
    elif bpp == 128:
        bits |= y & 1 | (x & 1) << 1 | (x & 2) << 1
    return bits

def _macro_tiled(x, y, bpp, pitch, swz):
    pi = _pixel_index(x, y, bpp)
    elem = bpp * pi >> 3
    pipe = (y ^ x) >> 3 & 1
    bank = (y >> 5 ^ x >> 3) & 1 | ((y >> 4 ^ x >> 4) & 1) << 1
    bank_pipe = (pipe + 2 * bank ^ swz) % 9
    pipe = bank_pipe % 2
    bank = bank_pipe // 2
    macro_bytes = bpp * 512 + 7 >> 3
    macro_off = (x // 32 + pitch // 32 * (y // 16)) * macro_bytes
    u1 = elem + (macro_off >> 3)
    u2 = u1 & ~255
    return u2 << 3 | 255 & u1 | pipe << 8 | bank << 9

def element_offsets(ew, eh, bpp, tile_mode, swizzle, pitch):
    eb = bpp // 8
    swz = (swizzle >> 8 & 1) + ((swizzle >> 9 & 3) << 1)
    y, x = np.mgrid[0:eh, 0:ew].astype(np.int64)
    if tile_mode in (0, 1):
        return (y * pitch + x) * eb
    if tile_mode in (2, 3):
        return (y // 8 * (pitch // 8) + x // 8) * 64 * eb + (_pixel_index(x, y, bpp) * bpp >> 3)
    return _macro_tiled(x, y, bpp, pitch, swz)

def _rgb565(v):
    return np.stack([(v >> 11 & 31) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v & 31) * 255 // 31], -1)

def _bc1_colors(blocks, punch):
    c0 = blocks[:, 0].astype(np.int32) | blocks[:, 1].astype(np.int32) << 8
    c1 = blocks[:, 2].astype(np.int32) | blocks[:, 3].astype(np.int32) << 8
    a, b = (_rgb565(c0), _rgb565(c1))
    pal = np.zeros((len(blocks), 4, 4), dtype=np.int32)
    pal[:, 0, :3], pal[:, 1, :3] = (a, b)
    pal[:, :2, 3] = 255
    four = (c0 > c1) | (not punch)
    pal[:, 2, :3] = np.where(four[:, None], (2 * a + b) // 3, (a + b) // 2)
    pal[:, 3, :3] = np.where(four[:, None], (a + 2 * b) // 3, 0)
    pal[:, 2, 3] = 255
    pal[:, 3, 3] = np.where(four, 255, 0)
    bits = blocks[:, 4].astype(np.uint32) | blocks[:, 5].astype(np.uint32) << 8 | blocks[:, 6].astype(np.uint32) << 16 | blocks[:, 7].astype(np.uint32) << 24
    idx = bits[:, None] >> 2 * np.arange(16) & 3
    return np.take_along_axis(pal, idx[:, :, None].astype(np.int64).repeat(4, 2), 1)

def _bc4_values(blocks):
    a0, a1 = (blocks[:, 0].astype(np.int32), blocks[:, 1].astype(np.int32))
    pal = np.zeros((len(blocks), 8), dtype=np.int32)
    pal[:, 0], pal[:, 1] = (a0, a1)
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
    idx = bits[:, None] >> np.uint64(3) * np.arange(16, dtype=np.uint64) & np.uint64(7)
    return np.take_along_axis(pal, idx.astype(np.int64), 1)

def decode(d, t, level=0):
    f = t.fmt & 63
    bpp = _bpp(f)
    bc = _is_bc(f)
    w, h = (t.w, t.h)
    ew, eh = ((w + 3) // 4, (h + 3) // 4) if bc else (w, h)
    eb = bpp // 8
    src = np.frombuffer(d[t.data_off:t.data_off + t.image_size], dtype=np.uint8)
    offs = element_offsets(ew, eh, bpp, t.tile_mode, t.swizzle, t.pitch)
    lin = src[(offs[..., None] + np.arange(eb)).reshape(-1, eb)].reshape(eh * ew, eb)
    if not bc:
        img = lin.reshape(h, w, 4) if f == 26 else None
        if img is None:
            raise NotImplementedError('format 0x%X' % f)
        return img.copy()
    if f == 49:
        px = _bc1_colors(lin, True)
    elif f == 50:
        px = _bc1_colors(lin[:, 8:], False)
        a = np.stack([lin[:, j // 2] >> 4 * (j & 1) & 15 for j in range(16)], 1).astype(np.int32) * 17
        px[:, :, 3] = a
    elif f == 51:
        px = _bc1_colors(lin[:, 8:], False)
        px[:, :, 3] = _bc4_values(lin[:, :8])
    elif f == 52:
        v = _bc4_values(lin)
        px = np.stack([v, v, v, np.full_like(v, 255)], 2)
    else:
        r, g = (_bc4_values(lin[:, :8]), _bc4_values(lin[:, 8:]))
        px = np.stack([r, g, np.zeros_like(r), np.full_like(r, 255)], 2)
    img = px.reshape(eh, ew, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(eh * 4, ew * 4, 4)
    return img[:h, :w].astype(np.uint8)

def _blocks(img):
    h, w = img.shape[:2]
    H, W = ((h + 3) // 4 * 4, (w + 3) // 4 * 4)
    pad = np.pad(img, ((0, H - h), (0, W - w), (0, 0)), mode='symmetric').astype(np.int32)
    return (pad.reshape(H // 4, 4, W // 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 4), W // 4, H // 4)

def _enc_bc4(v):
    a0, a1 = (v.max(1), v.min(1))
    a1 = np.where(a0 == a1, np.maximum(a0 - 1, 0), a1)
    a0 = np.where(a0 == a1, a1 + 1, a0)
    pal = np.stack([a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)], 1)
    idx = np.abs(v[:, :, None] - pal[:, None, :]).argmin(2).astype(np.uint64)
    bits = np.zeros(len(v), dtype=np.uint64)
    for j in range(16):
        bits |= idx[:, j] << np.uint64(3 * j)
    out = np.zeros((len(v), 8), dtype=np.uint8)
    out[:, 0], out[:, 1] = (a0, a1)
    for i in range(6):
        out[:, 2 + i] = (bits >> np.uint64(8 * i) & np.uint64(255)).astype(np.uint8)
    return out

def _to565(c):
    return (c[..., 0] * 31 + 127) // 255 << 11 | (c[..., 1] * 63 + 127) // 255 << 5 | (c[..., 2] * 31 + 127) // 255

def _enc_bc1(rgb):
    mean = rgb.mean(1, keepdims=True)
    d = rgb - mean
    cov = np.einsum('nki,nkj->nij', d, d)
    axis = np.ones((len(rgb), 3))
    for _ in range(4):
        axis = np.einsum('nij,nj->ni', cov, axis)
        axis /= np.linalg.norm(axis, axis=1, keepdims=True) + 1e-09
    proj = np.einsum('nki,ni->nk', d, axis)
    lo = rgb[np.arange(len(rgb)), proj.argmin(1)]
    hi = rgb[np.arange(len(rgb)), proj.argmax(1)]
    c0, c1 = (_to565(hi), _to565(lo))
    swap = c0 < c1
    c0, c1 = (np.where(swap, c1, c0), np.where(swap, c0, c1))
    same = c0 == c1
    c1 = np.where(same & (c1 > 0), c1 - 1, c1)
    c0 = np.where(same & (c0 == 0), 1, c0)
    a, b = (_rgb565(c0), _rgb565(c1))
    pal = np.stack([a, b, (2 * a + b) // 3, (a + 2 * b) // 3], 1)
    idx = ((rgb[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(3).argmin(2).astype(np.uint32)
    bits = np.zeros(len(rgb), dtype=np.uint32)
    for j in range(16):
        bits |= idx[:, j] << np.uint32(2 * j)
    out = np.zeros((len(rgb), 8), dtype=np.uint8)
    out[:, 0], out[:, 1], out[:, 2], out[:, 3] = (c0 & 255, c0 >> 8, c1 & 255, c1 >> 8)
    for i in range(4):
        out[:, 4 + i] = bits >> np.uint32(8 * i) & 255
    return out

def encode(img, t):
    f = t.fmt & 63
    bpp = _bpp(f)
    eb = bpp // 8
    blocks, ew, eh = _blocks(img)
    if f == 49:
        lin = _enc_bc1(blocks[:, :, :3])
    elif f == 51:
        lin = np.concatenate([_enc_bc4(blocks[:, :, 3]), _enc_bc1(blocks[:, :, :3])], 1)
    elif f == 52:
        lin = _enc_bc4(blocks[:, :, 0])
    elif f == 53:
        lin = np.concatenate([_enc_bc4(blocks[:, :, 0]), _enc_bc4(blocks[:, :, 1])], 1)
    elif f == 26:
        lin = np.ascontiguousarray(img).reshape(-1, 4)
        ew, eh = (img.shape[1], img.shape[0])
    else:
        raise NotImplementedError('format 0x%X' % f)
    out = np.zeros(t.image_size, dtype=np.uint8)
    offs = element_offsets(ew, eh, bpp, t.tile_mode, t.swizzle, t.pitch).reshape(-1)
    for k in range(eb):
        out[offs + k] = lin[:, k]
    return out.tobytes()

def encode_blocks(img, fmt):
    f = fmt & 63
    if f == 26:
        return np.ascontiguousarray(img).reshape(-1, 4).astype(np.uint8)
    blocks, _ew, _eh = _blocks(img)
    if f == 49:
        return _enc_bc1(blocks[:, :, :3])
    if f == 51:
        return np.concatenate([_enc_bc4(blocks[:, :, 3]), _enc_bc1(blocks[:, :, :3])], 1)
    if f == 52:
        return _enc_bc4(blocks[:, :, 0])
    if f == 53:
        return np.concatenate([_enc_bc4(blocks[:, :, 0]), _enc_bc4(blocks[:, :, 1])], 1)
    raise NotImplementedError('format 0x%X' % f)

def replace_region(d, t, x, y, sub):
    assert t.levels <= 1, 'mipmapped textures not supported'
    img = decode(d, t)
    h, w = sub.shape[:2]
    img[y:y + h, x:x + w] = sub
    bs = 4 if _is_bc(t.fmt & 63) else 1
    x0, y0 = (x // bs * bs, y // bs * bs)
    x1, y1 = (-(-(x + w) // bs) * bs, -(-(y + h) // bs) * bs)
    lin = encode_blocks(img[y0:y1, x0:x1], t.fmt)
    bpp = _bpp(t.fmt & 63)
    ew, eh = ((t.w + bs - 1) // bs, (t.h + bs - 1) // bs)
    offs = element_offsets(ew, eh, bpp, t.tile_mode, t.swizzle, t.pitch)
    offs = offs[y0 // bs:y1 // bs, x0 // bs:x1 // bs].reshape(-1)
    out = bytearray(d)
    eb = bpp // 8
    for k in range(eb):
        for o, v in zip(offs, lin[:, k]):
            out[t.data_off + int(o) + k] = int(v)
    return bytes(out)

def replace(d, t, img):
    assert t.levels <= 1, 'mipmapped textures not supported'
    data = encode(img, t)
    return d[:t.data_off] + data + d[t.data_off + len(data):]
NTP3_FORMATS = {'dxt1': 0, 'dxt5': 2, 'rgba': 14}

def ntp3_mip(img, fmt):
    if fmt == 14:
        return np.ascontiguousarray(img[..., [3, 0, 1, 2]]).tobytes()
    blocks, _, _ = _blocks(img)
    if fmt == 0:
        return _enc_bc1(blocks[:, :, :3]).tobytes()
    return np.concatenate([_enc_bc4(blocks[:, :, 3]), _enc_bc1(blocks[:, :, :3])], 1).tobytes()

def mip_chain(img, smallest=4):
    from PIL import Image
    out = [img]
    while min(out[-1].shape[:2]) > smallest:
        h, w = out[-1].shape[:2]
        out.append(np.asarray(Image.fromarray(out[-1], 'RGBA').resize((max(1, w // 2), max(1, h // 2)), Image.BOX)))
    return out

def read_ntp3(d):
    if d[:2] == b'x\x9c':
        d = zlib.decompress(d)
    assert d[:4] == b'NTP3', d[:4]
    count = be16(d, 6)
    hp, out, data = (16, [], 16)
    heads = []
    for _ in range(count):
        hs = be16(d, hp + 12)
        heads.append(hp)
        data += hs
        hp += hs
    for hp in heads:
        size, hs = (be32(d, hp + 8), be16(d, hp + 12))
        fmt, w, h = (d[hp + 19], be16(d, hp + 20), be16(d, hp + 22))
        g = d.find(b'GIDX', hp, hp + hs)
        tex_id = be32(d, g + 8) if g >= 0 else None
        mip0 = d[data:data + size]
        data += size
        if fmt == 14:
            img = np.frombuffer(mip0[:w * h * 4], np.uint8).reshape(h, w, 4)[..., [1, 2, 3, 0]].copy()
        elif fmt in (0, 1, 2):
            ew, eh = ((w + 3) // 4, (h + 3) // 4)
            eb = 8 if fmt == 0 else 16
            lin = np.frombuffer(mip0[:ew * eh * eb], np.uint8).reshape(ew * eh, eb)
            if fmt == 0:
                px = _bc1_colors(lin, True)
            elif fmt == 1:
                px = _bc1_colors(lin[:, 8:], False)
                px[:, :, 3] = np.stack([lin[:, j // 2] >> 4 * (j & 1) & 15 for j in range(16)], 1) * 17
            else:
                px = _bc1_colors(lin[:, 8:], False)
                px[:, :, 3] = _bc4_values(lin[:, :8])
            img = px.reshape(eh, ew, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(eh * 4, ew * 4, 4)[:h, :w]
            img = img.astype(np.uint8)
        else:
            raise NotImplementedError('NTP3 format %d' % fmt)
        out.append((tex_id, fmt, img))
    return out

def write_ntp3(textures):
    heads, datas = ([], [])
    for tex_id, fmt, mips in textures:
        data = [ntp3_mip(m, fmt) for m in mips]
        data = [x + b'\x00' * (-len(x) % 16) for x in data]
        hs = 80 + (4 * len(mips) if len(mips) > 1 else 0)
        hs += -hs % 16
        heads.append((tex_id, fmt, mips, data, hs))
        datas.append(b''.join(data))
    out = bytearray(b'NTP3' + struct.pack('>HHII', 512, len(textures), 0, 0))
    remaining = sum((h[4] for h in heads))
    data_before = 0
    for (tex_id, fmt, mips, data, hs), blob in zip(heads, datas):
        h, w = mips[0].shape[:2]
        head = struct.pack('>IIIHHBBBBHHII', len(blob) + hs, 0, len(blob), hs, 0, 0, len(mips), 0, fmt, w, h, 0, 0)
        head += struct.pack('>IIII', remaining + data_before, 0, 0, 0)
        if len(mips) > 1:
            head += b''.join((struct.pack('>I', len(x)) for x in data))
        head += b'\x00' * (-len(head) % 16)
        head += b'eXt\x00' + struct.pack('>III', 32, 16, 0)
        head += b'GIDX' + struct.pack('>III', 16, tex_id, 0)
        assert len(head) == hs
        out += head
        remaining -= hs
        data_before += len(blob)
    for blob in datas:
        out += blob
    return bytes(out)
NTWU_CODE = {49: 0, 51: 2, 26: 14}
NTWU_ALIGN = {49: 4096, 51: 8192, 26: 2048}

class Surface:

    def __init__(self, fmt, w, h, swizzle=851968):
        self.fmt, self.w, self.h, self.swizzle = (fmt, w, h, swizzle)
        bc = _is_bc(fmt)
        ew, eh = ((w + 3) // 4, (h + 3) // 4) if bc else (w, h)
        self.tile_mode, self.alignment = (4, NTWU_ALIGN[fmt])
        self.pitch = -(-ew // 32) * 32
        self.image_size = self.pitch * (-(-eh // 16) * 16) * (_bpp(fmt) // 8)

    def gx2(self):
        return struct.pack('>16i13i12x', 1, self.w, self.h, 1, 1, self.fmt, 0, 1, self.image_size, 0, 0, 0, self.tile_mode, self.swizzle, self.alignment, self.pitch, *[0] * 13)

def write_ntwu(textures):
    hs = 80
    surfs = [Surface(fmt, img.shape[1], img.shape[0]) for _, fmt, img in textures]
    out = bytearray(b'NTWU' + struct.pack('>HH8x', 526, len(textures)))
    pos = 16 + hs * len(textures)
    offs = []
    for s in surfs:
        pos = -(-max(pos, 4096) // s.alignment) * s.alignment
        offs.append(pos)
        pos += s.image_size
    gtx = pos
    for i, ((tex_id, fmt, img), s) in enumerate(zip(textures, surfs)):
        hp = 16 + hs * i
        out += struct.pack('>IIIHHBBBBHHII', s.image_size + hs, 0, s.image_size, hs, 0, 0, 1, 0, NTWU_CODE[fmt], s.w, s.h, 1, 0)
        out += struct.pack('>IIII', offs[i] - hp, 0, gtx + 128 * i - hp, 0)
        out += b'eXt\x00' + struct.pack('>III', 32, 16, 0)
        out += b'GIDX' + struct.pack('>III', 16, tex_id, 0)
    for (tex_id, fmt, img), s, o in zip(textures, surfs, offs):
        out += b'\x00' * (o - len(out))
        out += encode(img, s)
    for s in surfs:
        out += s.gx2()
    return bytes(out)

def append_ntwu(data, textures):
    d = data
    packed = d[:2] == b'x\x9c'
    if packed:
        d = zlib.decompress(d)
    d, texs = load_bytes(d)
    hs_new = 80
    surfs = [Surface(fmt, img.shape[1], img.shape[0]) for _, fmt, img in textures]
    heads = [bytearray(d[t.hp:t.hp + t.header_size]) for t in texs]
    hp, hps = (16, [])
    for h in heads:
        hps.append(hp)
        hp += len(h)
    new_hps = [hp + hs_new * i for i in range(len(textures))]
    pos = hp + hs_new * len(textures)
    blobs = []
    for t in texs:
        img = d[t.data_off:t.data_off + t.image_size]
        mip = d[t.mip_off:t.mip_off + t.mip_size] if t.levels > 1 else b''
        al = max(t.alignment, 256)
        pos = -(-max(pos, 4096) // al) * al
        blobs.append((pos, img + (b'\x00' * (t.mip_off - t.data_off - t.image_size) if mip else b'') + mip))
        pos += len(blobs[-1][1])
    for (tex_id, fmt, img), s in zip(textures, surfs):
        pos = -(-max(pos, 4096) // s.alignment) * s.alignment
        blobs.append((pos, encode(img, s)))
        pos += len(blobs[-1][1])
    gtx = -(-pos // 128) * 128
    for i, (t, h) in enumerate(zip(texs, heads)):
        o = blobs[i][0]
        struct.pack_into('>i', h, 32, o - hps[i])
        if t.levels > 1:
            struct.pack_into('>i', h, 36, o + (t.mip_off - t.data_off) - hps[i])
        struct.pack_into('>i', h, 40, gtx + 128 * i - hps[i])
    out = bytearray(d[:16])
    struct.pack_into('>H', out, 6, len(texs) + len(textures))
    for h in heads:
        out += h
    for k, ((tex_id, fmt, img), s) in enumerate(zip(textures, surfs)):
        i = len(texs) + k
        out += struct.pack('>IIIHHBBBBHHII', s.image_size + hs_new, 0, s.image_size, hs_new, 0, 0, 1, 0, NTWU_CODE[fmt], s.w, s.h, 1, 0)
        out += struct.pack('>IIII', blobs[i][0] - new_hps[k], 0, gtx + 128 * i - new_hps[k], 0)
        out += b'eXt\x00' + struct.pack('>III', 32, 16, 0)
        out += b'GIDX' + struct.pack('>III', 16, tex_id, 0)
    for o, b in blobs:
        out += b'\x00' * (o - len(out))
        out += b
    out += b'\x00' * (gtx - len(out))
    for t in texs:
        out += d[t.gtx:t.gtx + 128]
    for s in surfs:
        out += s.gx2()
    return zlib.compress(bytes(out)) if packed else bytes(out)

def _is_ntp3(path):
    d = open(path, 'rb').read(65536)
    return d[:4] == b'NTP3' or (d[:2] == b'x\x9c' and zlib.decompressobj().decompress(d)[:4] == b'NTP3')
