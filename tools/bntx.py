#!/usr/bin/env python3
"""Smash Ultimate textures (.bntx, Switch): a texture's first mip, as RGBA.

  python3 tools/bntx.py png FILE.bntx OUT.png     the first texture
  python3 tools/bntx.py all FILE OUTDIR           every texture (also a BNTX inside another file,
                                                  e.g. an effect .eff), as NAME.png

BNTX: an "NX  " block after the 0x20 header, a BRTI block per texture (format, size, block height,
the mip offsets); the data is Tegra block-linear (nutexb.deswizzle) with the BRTI's block height.
Formats: BC1-BC5 (nut.py's decoders), BC7 and RGBA8 (Pillow's DDS reader for BC7).
"""
import io
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nut  # noqa: E402
import nutexb  # noqa: E402

BLOCK_BYTES = {0x1A: 8, 0x1B: 16, 0x1C: 16, 0x1D: 8, 0x1E: 16, 0x20: 16, 0x0B: 4}


def read(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'BNTX', path
    return _brti(d, d.index(b'BRTI'))


def read_all(d):
    """{name: RGBA} of every texture of the first BNTX in d (offsets are from the BNTX's start)"""
    d = d[d.index(b'BNTX'):]
    out = {}
    i = d.find(b'BRTI')
    while i >= 0:
        name_ptr, = struct.unpack('<Q', d[i + 0x60:i + 0x68])
        n, = struct.unpack('<H', d[name_ptr:name_ptr + 2])
        out[d[name_ptr + 2:name_ptr + 2 + n].decode()] = _brti(d, i)
        i = d.find(b'BRTI', i + 4)
    return out


def _brti(d, i):
    mips, = struct.unpack('<H', d[i + 0x16:i + 0x18])
    fmt, = struct.unpack('<I', d[i + 0x1C:i + 0x20])
    w, h, _depth, _layers, layout = struct.unpack('<5I', d[i + 0x24:i + 0x38])
    size, = struct.unpack('<I', d[i + 0x50:i + 0x54])
    ptrs, = struct.unpack('<Q', d[i + 0x70:i + 0x78])
    data_off, = struct.unpack('<Q', d[ptrs:ptrs + 8])
    kind = fmt >> 8
    eb = BLOCK_BYTES[kind]
    bs = 1 if kind == 0x0B else 4
    ew, eh = (w + bs - 1) // bs, (h + bs - 1) // bs
    src = np.frombuffer(d, np.uint8, size, data_off)
    lin = nutexb.deswizzle(src, ew * eb, eh, 1 << (layout & 7)).reshape(eh * ew, eb)
    if kind == 0x0B:
        return lin.reshape(h, w, 4).copy()
    if kind == 0x20:
        from PIL import Image
        head = struct.pack('<4s7I44x', b'DDS ', 124, 0x1007, h, w, w * h, 0, 1)
        head += struct.pack('<2I4s5I', 32, 4, b'DX10', 0, 0, 0, 0, 0) + struct.pack('<5I', 0x1000, 0, 0, 0, 0)
        head += struct.pack('<5I', 98, 3, 0, 1, 0)                 # DXGI_FORMAT_BC7_UNORM, 2D
        return np.asarray(Image.open(io.BytesIO(head + lin.tobytes())).convert('RGBA'))
    if kind == 0x1A:
        px = nut._bc1_colors(lin, True)
    elif kind == 0x1C:
        px = nut._bc1_colors(lin[:, 8:], False)
        px[:, :, 3] = nut._bc4_values(lin[:, :8])
    elif kind == 0x1D:
        v = nut._bc4_values(lin)
        px = np.stack([v, v, v, np.full_like(v, 255)], 2)
    elif kind == 0x1E:                                          # BC5: red, green
        r, g = nut._bc4_values(lin[:, :8]), nut._bc4_values(lin[:, 8:])
        px = np.stack([r, g, np.zeros_like(r), np.full_like(r, 255)], 2)
    else:
        raise NotImplementedError('format 0x%X' % fmt)
    img = px.reshape(eh, ew, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(eh * 4, ew * 4, 4)
    return img[:h, :w].astype(np.uint8)


def main():
    from PIL import Image
    if sys.argv[1] == 'png':
        Image.fromarray(read(sys.argv[2]), 'RGBA').save(sys.argv[3])
    elif sys.argv[1] == 'all':
        os.makedirs(sys.argv[3], exist_ok=True)
        for name, img in read_all(open(sys.argv[2], 'rb').read()).items():
            Image.fromarray(img, 'RGBA').save('%s/%s.png' % (sys.argv[3], name))
            print(name, img.shape[1], img.shape[0])


if __name__ == '__main__':
    main()
