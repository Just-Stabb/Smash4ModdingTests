#!/usr/bin/env python3
"""Switch BFRES (version 9) models: vertex attributes and triangle lists, enough for Ultimate's
effect primitives (the VFXB's G3PR section, tools/vfxb.py).

  python3 tools/bfres_switch.py FILE.bfres          models, their attributes and triangle counts

Layout from KillzXGaming's BfresLibrary (MIT; Switch/ResFileParser.cs, Model/ModelParser.cs,
VertexBufferParser.cs, ShapeParser.cs, Shared/Models/Shape/Mesh.cs), little endian, offsets u64
from the file's start, strings as u16 length + bytes:
- FRES: +0x28 model array, +0x30 model dict, +0xB0 BufferInfo (+8 u64: the buffer data's offset);
  the model count is u16 at +0xDC (version 9).
- FMDL (0x78 bytes): +8 name, +0x20 vertex buffer array, +0x28 shape array, +0x68 u16 vertex buffer
  count, +0x6A u16 shape count.
- FVTX (0x58): +8 attribute array (0x10 each: name, u16 big-endian format code, 2 pad, u16 offset,
  u16 buffer), +0x30 buffer size array (0x10 each: u32 size), +0x38 stride array (0x10 each: u32),
  +0x48 u32 data offset (in the buffer data), +0x4C u8 attributes, +0x4D u8 buffers, +0x50 u32
  vertex count.
- FSHP (0x60): +8 name, +0x18 mesh array, +0x56 u16 vertex buffer index, +0x5B u8 mesh count.
- Mesh (0x38): +0x20 u32 index data offset (in the buffer data), +0x24 u32 primitive type (3
  triangles), +0x28 u32 index format (0 u8, 1 u16, 2 u32), +0x2C u32 index count, +0x30 first vertex.
"""
import struct
import sys

import numpy as np

# Switch attribute format code -> (numpy element type, components, normalise divisor or None)
FORMATS = {0x518: ('<f4', 3, None), 0x519: ('<f4', 4, None), 0x517: ('<f4', 2, None), 0x516: ('<f4', 1, None),
           0x515: ('<f2', 4, None), 0x512: ('<f2', 2, None),
           0x10B: ('u1', 4, 255.0), 0x20B: ('i1', 4, 127.0), 0x109: ('u1', 2, 255.0), 0x209: ('i1', 2, 127.0),
           0x112: ('<u2', 2, 65535.0), 0x212: ('<i2', 2, 32767.0), 0x115: ('<u2', 4, 65535.0),
           0x215: ('<i2', 4, 32767.0)}


class Bfres:
    def __init__(self, data):
        self.d = d = data
        assert d[:4] == b'FRES', d[:4]
        assert struct.unpack_from('<I', d, 8)[0] >> 16 == 9, 'version'
        self.buffer = self.u64(self.u64(0xB0) + 8)
        n = struct.unpack_from('<H', d, 0xDC)[0]
        arr = self.u64(0x28)
        self.models = [self.model(arr + 0x78 * i) for i in range(n)]

    def u64(self, o):
        return struct.unpack_from('<Q', self.d, o)[0]

    def string(self, o):
        n = struct.unpack_from('<H', self.d, o)[0]
        return self.d[o + 2:o + 2 + n].decode('latin1')

    def model(self, m):
        d = self.d
        assert d[m:m + 4] == b'FMDL'
        nvb, nsh = struct.unpack_from('<HH', d, m + 0x68)
        vbs = [self.vertex_buffer(self.u64(m + 0x20) + 0x58 * i) for i in range(nvb)]
        shapes = [self.shape(self.u64(m + 0x28) + 0x60 * i) for i in range(nsh)]
        return {'name': self.string(self.u64(m + 8)), 'vertex_buffers': vbs, 'shapes': shapes}

    def vertex_buffer(self, v):
        d = self.d
        assert d[v:v + 4] == b'FVTX'
        off = struct.unpack_from('<I', d, v + 0x48)[0]
        na, nb = d[v + 0x4C], d[v + 0x4D]
        count = struct.unpack_from('<I', d, v + 0x50)[0]
        sizes = [struct.unpack_from('<I', d, self.u64(v + 0x30) + 0x10 * i)[0] for i in range(nb)]
        strides = [struct.unpack_from('<I', d, self.u64(v + 0x38) + 0x10 * i)[0] for i in range(nb)]
        starts, o = [], self.buffer + off
        for s in sizes:
            starts.append(o)
            o += s
            o += -o % 8
        attrs = {}
        for i in range(na):
            a = self.u64(v + 8) + 0x10 * i
            name = self.string(self.u64(a))
            fmt = struct.unpack_from('>H', d, a + 8)[0]
            aoff, buf = struct.unpack_from('<HH', d, a + 0xC)
            if fmt not in FORMATS:
                continue
            dt, comps, div = FORMATS[fmt]
            item = np.dtype(dt).itemsize * comps
            raw = np.frombuffer(d, np.uint8, strides[buf] * count, starts[buf])
            vals = np.stack([np.frombuffer(raw.reshape(count, strides[buf])[:, aoff:aoff + item].tobytes(), dt)
                             .reshape(count, comps)], 0)[0].astype(np.float32)
            attrs[name] = vals / div if div else vals
        return {'count': count, 'attrs': attrs}

    def shape(self, s):
        d = self.d
        assert d[s:s + 4] == b'FSHP'
        vb = struct.unpack_from('<H', d, s + 0x56)[0]
        nmesh = d[s + 0x5B]
        meshes = []
        for i in range(nmesh):
            m = self.u64(s + 0x18) + 0x38 * i
            ioff, prim, ifmt, icount, first = struct.unpack_from('<5I', d, m + 0x20)
            dt = {0: 'u1', 1: '<u2', 2: '<u4'}[ifmt]
            idx = np.frombuffer(d, dt, icount, self.buffer + ioff).astype(np.int64) + first
            meshes.append({'primitive': prim, 'indices': idx})
        return {'name': self.string(self.u64(s + 8)), 'vertex_buffer': vb, 'meshes': meshes}


def main():
    b = Bfres(open(sys.argv[1], 'rb').read())
    for m in b.models:
        vb = m['vertex_buffers'][0] if m['vertex_buffers'] else {'count': 0, 'attrs': {}}
        tris = sum(len(me['indices']) // 3 for s in m['shapes'] for me in s['meshes'][:1])
        print('%-40s verts %5d tris %5d %s' % (m['name'], vb['count'], tris,
                                               {k: v.shape[1] for k, v in vb['attrs'].items()}))


if __name__ == '__main__':
    main()
