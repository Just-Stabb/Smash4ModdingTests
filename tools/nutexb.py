#!/usr/bin/env python3
"""Smash Ultimate textures (.nutexb, Switch): the first mip of the first layer, as RGBA.

  python3 tools/nutexb.py info FILE.nutexb...
  python3 tools/nutexb.py png FILE.nutexb OUT.png

The footer (last 0x70 bytes, the mip sizes before it) and the Tegra X1 block-linear layout
follow ssbh's nutexb / tegra_swizzle (MIT): GOBs of 64 bytes x 8 rows, stacked block_height GOBs
high, the block height picked from the image's height. Formats: R8G8B8A8, B8G8R8A8, BC1-BC5
(unorm / srgb alike; the values are returned as stored).
"""
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nut  # noqa: E402

FORMATS = {  # format: (bytes per element, block size, name)
    0x0400: (4, 1, 'R8G8B8A8'), 0x0405: (4, 1, 'R8G8B8A8_SRGB'),
    0x0450: (4, 1, 'B8G8R8A8'), 0x0455: (4, 1, 'B8G8R8A8_SRGB'),
    0x0480: (8, 4, 'BC1'), 0x0485: (8, 4, 'BC1_SRGB'),
    0x0490: (16, 4, 'BC2'), 0x0495: (16, 4, 'BC2_SRGB'),
    0x04A0: (16, 4, 'BC3'), 0x04A5: (16, 4, 'BC3_SRGB'),
    0x0180: (8, 4, 'BC4'), 0x0280: (16, 4, 'BC5'),
}


class Nutexb:
    def __init__(self, path):
        d = open(path, 'rb').read()
        f = d[-0x70:]
        assert f[:4] == b' XNT', path
        self.data = d
        self.name = f[4:0x44].split(b'\0')[0].decode()
        self.w, self.h, self.depth, self.fmt = struct.unpack('<IIIH', f[0x44:0x52])
        self.mips, self.align, self.layers, self.size = struct.unpack('<4I', f[0x58:0x68])

    def info(self):
        return '%s %dx%d %s mips %d layers %d' % (self.name, self.w, self.h,
                                                 FORMATS.get(self.fmt, (0, 0, hex(self.fmt)))[2],
                                                 self.mips, self.layers)


def _block_height(height):
    """GOBs per block for mip 0 (height in elements)"""
    hh = height + height // 2
    for limit, bh in ((128, 16), (64, 8), (32, 4), (16, 2)):
        if hh >= limit:
            return bh
    return 1


def deswizzle(src, width_bytes, height, bh):
    """block-linear -> linear rows ([height, width_bytes] uint8)"""
    wg = (width_bytes + 63) // 64
    y = np.arange(height)[:, None]
    x = np.arange(width_bytes)[None, :]
    addr = ((y // (8 * bh)) * 512 * bh * wg + ((y % (8 * bh)) // 8) * 512 + (x // 64) * 512 * bh
            + ((x % 64) // 32) * 256 + ((y % 8) // 2) * 64 + ((x % 32) // 16) * 32 + (y % 2) * 16 + (x % 16))
    return src[addr]


def decode(t):
    """RGBA uint8 [h, w, 4] of mip 0, layer 0"""
    eb, bs, _ = FORMATS[t.fmt]
    ew, eh = (t.w + bs - 1) // bs, (t.h + bs - 1) // bs
    src = np.frombuffer(t.data, dtype=np.uint8)
    lin = deswizzle(src, ew * eb, eh, _block_height(eh)).reshape(eh * ew, eb)
    if bs == 1:
        img = lin.reshape(t.h, t.w, 4)
        return (img[..., [2, 1, 0, 3]] if t.fmt in (0x0450, 0x0455) else img).copy()
    kind = t.fmt & 0xFFF0
    if kind == 0x0480:
        px = nut._bc1_colors(lin, True)
    elif kind == 0x0490:
        px = nut._bc1_colors(lin[:, 8:], False)
        px[:, :, 3] = np.stack([(lin[:, j // 2] >> (4 * (j & 1))) & 15 for j in range(16)], 1) * 17
    elif kind == 0x04A0:
        px = nut._bc1_colors(lin[:, 8:], False)
        px[:, :, 3] = nut._bc4_values(lin[:, :8])
    elif kind == 0x0180:
        v = nut._bc4_values(lin)
        px = np.stack([v, v, v, np.full_like(v, 255)], 2)
    else:
        r, g = nut._bc4_values(lin[:, :8]), nut._bc4_values(lin[:, 8:])
        px = np.stack([r, g, np.zeros_like(r), np.full_like(r, 255)], 2)
    img = px.reshape(eh, ew, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(eh * 4, ew * 4, 4)
    return img[:t.h, :t.w].astype(np.uint8)


def main():
    if sys.argv[1] == 'info':
        for p in sys.argv[2:]:
            print(p, Nutexb(p).info())
    elif sys.argv[1] == 'png':
        from PIL import Image
        Image.fromarray(decode(Nutexb(sys.argv[2])), 'RGBA').save(sys.argv[3])


if __name__ == '__main__':
    main()
