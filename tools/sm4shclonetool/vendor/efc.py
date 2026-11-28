"""Effect control files (.efc, EFCF): the effect list of a bank (an ACMD effect id 0xBBBBnnnn is entry nnnn): read,
rebuild byte for byte, add entries.

Adapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; the tool
sets the code addresses itself, see its README "The executable")."""
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
            e = data.index(b'\x00', o)
            names.append(data[o:e].decode('ascii'))
            o = e + 1
        self.models, self.mesh_names = (names[:m], names[m:])
        self.tail = data[o:]

    def build(self):
        out = b'EFCF' + struct.pack('>HHHHHH', self.variant, self.version, len(self.entries), len(self.models), len(self.meshes), 0)
        out += b''.join((struct.pack('>IIIHH', *e) for e in self.entries))
        out += b''.join((struct.pack('>HH', *mm) for mm in self.meshes))
        if self.variant == 1:
            out += struct.pack('>%dH' % len(self.models), *self.model_u16)
        out += b''.join((s.encode('ascii') + b'\x00' for s in self.models + self.mesh_names))
        return out + self.tail

    def add(self, emitter_set, model=None, flags=256):
        mi = 0
        if model is not None:
            self.models.append(model)
            if self.variant == 1:
                self.model_u16.append(0)
            mi = self.models.index(model) + 1
        self.entries.append([flags, emitter_set, mi, 0, 0])
        self.tail = b''
        return len(self.entries) - 1

def ptcl_set_names(path):
    d = open(path, 'rb').read()
    _m, _v, n, _z, name_off, name_size = struct.unpack('>4sIIIII', d[:24])
    return (n, d[name_off:name_off + name_size])
