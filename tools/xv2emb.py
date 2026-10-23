#!/usr/bin/env python3
"""Dragon Ball Xenoverse 2 EMB containers (textures `.emb`, and the `.pbind.emb` / `.tbind.emb`
that hold an effect's EMP particle / ETR trace files).

  python3 tools/xv2emb.py list FILE.emb              entries (name, size, kind, DDS size / format)
  python3 tools/xv2emb.py extract FILE.emb OUTDIR    the entries as files; DDS also as PNG

Layout (little-endian; LazyBone152 XV2-Tools Xv2CoreLib/EMB_CLASS/EMB_File.cs):
  +0 "#EMB", +8 u16, +10 u16, +12 u32 entries, +24 u32 contents table, +28 u32 name table (0 = none)
  contents table: per entry (u32 offset relative to the entry's own position, u32 size)
  name table: per entry u32 absolute offset of a NUL-terminated name (no table: DATA<i>.dds)
"""
import io
import os
import struct
import sys

MAGIC = b'#EMB'


class Emb:
    def __init__(self, data):
        assert data[:4] == MAGIC, 'not an EMB'
        n, contents, names = struct.unpack_from('<I', data, 12)[0], *struct.unpack_from('<II', data, 24)
        self.entries = []
        for i in range(n):
            rel, size = struct.unpack_from('<II', data, contents + 8 * i)
            off = contents + 8 * i + rel
            if names:
                no = struct.unpack_from('<I', data, names + 4 * i)[0]
                name = data[no:data.index(b'\0', no)].decode('latin-1')
            else:
                name = 'DATA%d.dds' % i
            self.entries.append((name, bytes(data[off:off + size])))

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, i):
        return self.entries[i]


def dds_info(d):
    """(width, height, format) of a DDS, format the FourCC or 'DX10:<dxgi>' or 'RGBA<bits>'"""
    if d[:4] != b'DDS ':
        return None
    h, w = struct.unpack_from('<II', d, 12)
    flags, fourcc = struct.unpack_from('<I4s', d, 80)
    if flags & 4:
        if fourcc == b'DX10':
            return w, h, 'DX10:%d' % struct.unpack_from('<I', d, 128)[0]
        return w, h, fourcc.decode('latin-1')
    return w, h, 'RGBA%d' % struct.unpack_from('<I', d, 88)[0]


def dds_rgba(d):
    """a DDS's first image as an RGBA numpy array (Pillow's DDS decoder: DXT1/3/5, BC4/5/7,
    uncompressed)"""
    import numpy as np
    from PIL import Image
    return np.array(Image.open(io.BytesIO(d)).convert('RGBA'))


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ('list', 'extract'):
        sys.exit(__doc__)
    e = Emb(open(sys.argv[2], 'rb').read())
    for i, (name, d) in enumerate(e):
        info = dds_info(d)
        print('%2d  %-32s %7d  %s' % (i, name, len(d), '%dx%d %s' % info if info else d[:4]))
        if sys.argv[1] == 'extract':
            out = sys.argv[3]
            os.makedirs(out, exist_ok=True)
            open(os.path.join(out, name), 'wb').write(d)
            if info:
                from PIL import Image
                Image.fromarray(dds_rgba(d)).save(os.path.join(out, os.path.splitext(name)[0] + '.png'))


if __name__ == '__main__':
    main()
