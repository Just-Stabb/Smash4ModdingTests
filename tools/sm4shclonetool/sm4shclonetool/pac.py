"""(2.0) KCAP packs (fighter/<name>/motion/<folder>/main.pac, lhand.pac ...): the motion files (.omo) of a fighter or an
article, by file name.

Layout (big-endian): 'KCAP', u32 0, u32 count, u32 0; count name offsets, count data offsets, count sizes; the names
(zero-terminated, in entry order), padding to 0x10, the data (each entry at a 0x10 boundary). The game's packs list
their entries sorted by name (ASCII order), and the pack loader (0x03326740) keys every .omo by
zlib.crc32(name without ".omo", 0xFFFFFFFF): a motion plays the animation whose name hashes to its entry in the
executable's motion table (motions.py).

read() / write() keep a pack byte for byte when nothing changed (checked on the game's packs: write(read(p)) == p).
"""
import struct
import zlib


def anim_hash(name):
    """the pack loader's key of an animation (its file name without .omo)"""
    if name.endswith('.omo'):
        name = name[:-4]
    return zlib.crc32(name.encode('latin1'), 0xFFFFFFFF) & 0xFFFFFFFF


class Pac:
    """entries: [[name, bytes]] in file order; tail: whatever followed the last entry (kept)"""

    def __init__(self, data=None):
        self.entries = []
        self.layout = None
        if data is None:
            return
        if data[:4] != b'KCAP':
            raise ValueError('not a KCAP pack')
        n = struct.unpack('>I', data[8:12])[0]
        names = struct.unpack('>%dI' % n, data[0x10:0x10 + 4 * n])
        offs = struct.unpack('>%dI' % n, data[0x10 + 4 * n:0x10 + 8 * n])
        sizes = struct.unpack('>%dI' % n, data[0x10 + 8 * n:0x10 + 12 * n])
        for no, o, s in zip(names, offs, sizes):
            self.entries.append([data[no:data.index(b'\0', no)].decode('latin1'), bytes(data[o:o + s])])
        self.raw = bytes(data)

    @classmethod
    def load(cls, path):
        return cls(open(path, 'rb').read())

    def names(self):
        return [n for n, _d in self.entries]

    def get(self, name):
        return next((d for n, d in self.entries if n == name), None)

    def put(self, name, data):
        """an entry added (in name order) or replaced"""
        for e in self.entries:
            if e[0] == name:
                e[1] = bytes(data)
                return
        self.entries.append([name, bytes(data)])
        self.entries.sort(key=lambda e: e[0].encode('latin1'))

    def build(self):
        n = len(self.entries)
        head = 0x10 + 12 * n
        names, noffs = b'', []
        for name, _d in self.entries:
            noffs.append(head + len(names))
            names += name.encode('latin1') + b'\0'
        pos = (head + len(names) + 0xF) & ~0xF
        body, doffs = bytearray(), []
        for i, (_n, data) in enumerate(self.entries):
            doffs.append(pos + len(body))
            body += data
            if i + 1 < n:
                body += bytes(-len(body) % 0x10)
        out = b'KCAP' + struct.pack('>III', 0, n, 0)
        out += struct.pack('>%dI' % n, *noffs) + struct.pack('>%dI' % n, *doffs)
        out += struct.pack('>%dI' % n, *[len(d) for _n, d in self.entries])
        out += names
        out += bytes(pos - len(out))
        out += bytes(body)
        raw = getattr(self, 'raw', None)
        if raw and len(raw) > len(out) and raw[:len(out)] == out:
            out = raw                                   # the game's own trailing padding, unchanged
        return out

    def save(self, path):
        open(path, 'wb').write(self.build())
