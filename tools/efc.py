#!/usr/bin/env python3
"""Smash 4 (Wii U) effect control file: <name>.010d0000.efc (magic EFCF), next to the bank's .ptcl.

  python3 tools/efc.py dump FILE.efc [PTCL]          entries (with emitter-set names from the .ptcl)
  python3 tools/efc.py check DIR...                  byte-exact round trip of every .efc under DIR
  python3 tools/efc.py add IN.efc OUT.efc --set N [--model NAME] [--flags 0x100]
                                               append an entry (prints its index = the ACMD id's low 16 bits)

Layout (big endian; read by the bank loader 0x032F1388, used by the effect spawn 0x0334D8D8):
  +0x00 'EFCF'
  +0x04 u16 variant (0 in every vanilla file; 1: a u16 per model follows the mesh list)
  +0x06 u16 version (7)
  +0x08 u16 n_entries     (an ACMD effect id 0xBBBBnnnn: bank 0xBBBB, entry nnnn < n_entries)
  +0x0A u16 n_models      (model name strings)
  +0x0C u16 n_meshes      (mesh-switch records)
  +0x0E u16 0
  +0x10 entries, 16 bytes each:
        +0 u32 flags   (0x100, 0x200, 0x10, 0x20, 0x1-0x5, 0x80000, 0x400000 seen; see efc-format.md)
        +4 u32 emitter set in the .ptcl, 1-based (0 = none)
        +8 u32 model, 1-based index into the model list (0 = none)
        +C u16 first mesh-switch record (1-based), +E u16 count (0 = none)
  then n_meshes x 4 bytes: u16, u16 (a frame / a flag pair: 0x30 / 0x31 seen)
  [variant 1: n_models x u16]
  then n_models zero-terminated model folder names (model/<name>/ next to the .efc), then
  n_meshes zero-terminated mesh (polygon) names, then padding to the file's end.
The model list has one name per entry with a model, in entry order (duplicates included); an
entry's model index points at the first occurrence of its name.
"""
import struct
import sys


class Efc:
    def __init__(self, data):
        assert data[:4] == b'EFCF', data[:4]
        self.variant, self.version, n, m, x, z = struct.unpack('>HHHHHH', data[4:16])
        assert z == 0
        self.entries = [list(struct.unpack('>IIIHH', data[16 + 16 * i:32 + 16 * i])) for i in range(n)]
        o = 16 + 16 * n
        self.meshes = [list(struct.unpack('>HH', data[o + 4 * i:o + 4 * i + 4])) for i in range(x)]
        o += 4 * x
        self.model_u16 = []
        if self.variant == 1:
            self.model_u16 = list(struct.unpack('>%dH' % m, data[o:o + 2 * m]))
            o += 2 * m
        names = []
        for _ in range(m + x):
            e = data.index(b'\0', o)
            names.append(data[o:e].decode('ascii'))
            o = e + 1
        self.models, self.mesh_names = names[:m], names[m:]
        self.tail = data[o:]

    def build(self):
        out = b'EFCF' + struct.pack('>HHHHHH', self.variant, self.version, len(self.entries), len(self.models),
                                    len(self.meshes), 0)
        out += b''.join(struct.pack('>IIIHH', *e) for e in self.entries)
        out += b''.join(struct.pack('>HH', *mm) for mm in self.meshes)
        if self.variant == 1:
            out += struct.pack('>%dH' % len(self.models), *self.model_u16)
        out += b''.join(s.encode('ascii') + b'\0' for s in self.models + self.mesh_names)
        return out + self.tail

    def add(self, emitter_set, model=None, flags=0x100):
        """a new entry: emitter set (1-based, 0 none), a model folder name or None; its index"""
        mi = 0
        if model is not None:
            self.models.append(model)
            if self.variant == 1:
                self.model_u16.append(0)
            mi = self.models.index(model) + 1
        self.entries.append([flags, emitter_set, mi, 0, 0])
        self.tail = b''         # the tail is padding: rebuilt files end after the names
        return len(self.entries) - 1


def ptcl_set_names(path):
    """the .ptcl's emitter-set names in order (EFTF v0x42: header counts at +8, set table at the
    name block's start: the first string is the bank's name, then sets / emitters in file order)"""
    d = open(path, 'rb').read()
    _m, _v, n, _z, name_off, name_size = struct.unpack('>4sIIIII', d[:24])
    return n, d[name_off:name_off + name_size]


def main():
    a = sys.argv[1:]
    if a[0] == 'dump':
        e = Efc(open(a[1], 'rb').read())
        print('variant %d version %d entries %d models %d meshes %d tail %d' % (
            e.variant, e.version, len(e.entries), len(e.models), len(e.meshes), len(e.tail)))
        for i, (fl, st, md, ms, mc) in enumerate(e.entries):
            print('  %04X flags 0x%06X set %3d model %s%s' % (
                i, fl, st, '%d %s' % (md, e.models[md - 1]) if md else '-',
                '  meshes %s' % [(e.meshes[k][0], e.meshes[k][1], e.mesh_names[k]) for k in range(ms - 1, ms - 1 + mc)]
                if mc else ''))
    elif a[0] == 'check':
        import glob
        import os
        ok = bad = 0
        for d in a[1:]:
            for p in sorted(glob.glob(os.path.join(d, '**', '*.efc'), recursive=True)):
                data = open(p, 'rb').read()
                if Efc(data).build() == data:
                    ok += 1
                else:
                    bad += 1
                    print('DIFF', p)
        print('%d round trip byte for byte, %d differ' % (ok, bad))
        sys.exit(1 if bad else 0)
    elif a[0] == 'add':
        e = Efc(open(a[1], 'rb').read())
        model = a[a.index('--model') + 1] if '--model' in a else None
        flags = int(a[a.index('--flags') + 1], 0) if '--flags' in a else 0x100
        i = e.add(int(a[a.index('--set') + 1], 0), model, flags)
        open(a[2], 'wb').write(e.build())
        print('entry 0x%04X' % i)


if __name__ == '__main__':
    main()
