#!/usr/bin/env python3
"""Smash 4 stage collision / level data (.lvd): read, edit, write.

  python3 tools/lvd.py info FILE.lvd

Layout as Smash Forge's LVD.cs (MIT): a list of sections, each "01" + count + entries; every
entry starts with a 12-byte magic and the common header (name, subname, start position, ...,
bone name). Sections: 1 collisions, 2 spawns, 3 respawns, 4 camera bounds, 5 blast zones,
6 enemy generators, 7-11 (empty in the stages read here), 12 damage shapes, 13 item spawners,
14 general shapes, 15 general points, then the rest (kept as read).

Collision: vertices (x, y), a normal per line (pointing out of the solid, e.g. (0, 1) for a
floor), ledges ("cliffs": the grab point, -1 left / 1 right, the line index) and a material per
line (byte 3: the surface kind, byte 10 flags: 0x40 left ledge, 0x80 right ledge, 0x10 no wall
jump). flag4 is drop-through (soft platforms).
"""
import struct
import sys

MAGIC_COL = bytes.fromhex('030401017735BB7500000002')
MAGIC_2 = bytes.fromhex('020401017735BB7500000002')
MAGIC_1 = bytes.fromhex('010401017735BB7500000002')


class R:
    def __init__(self, d, o=0):
        self.d, self.o = d, o

    def take(self, n):
        b = self.d[self.o:self.o + n]
        self.o += n
        return b

    def u8(self):
        return self.take(1)[0]

    def i32(self):
        return struct.unpack('>i', self.take(4))[0]

    def f32(self, n=1):
        v = struct.unpack('>%df' % n, self.take(4 * n))
        return v[0] if n == 1 else list(v)


class Entry:
    def __init__(self, name='', subname='', magic=MAGIC_2):
        self.magic = magic
        self.name, self.subname, self.bone = name, subname, ''
        self.start = [0.0, 0.0, 0.0]
        self.use_start = 0
        self.unk1 = 0
        self.unk2 = [0.0, 0.0, 0.0]
        self.unk3 = -1

    def read_head(self, r):
        self.magic = r.take(12)
        r.u8()
        self.raw_name = r.take(0x38)
        self.name = self.raw_name.split(b'\0')[0].decode()
        r.u8()
        self.raw_subname = r.take(0x40)
        self.subname = self.raw_subname.split(b'\0')[0].decode()
        r.u8()
        self.start = r.f32(3)
        self.use_start = r.u8()
        r.u8()
        self.unk1 = r.i32()
        r.u8()
        self.unk2 = r.f32(3)
        self.unk3 = r.i32()
        r.u8()
        self.raw_bone = r.take(0x40)
        self.bone = self.raw_bone.split(b'\0')[0].decode()

    def _str(self, attr, size):
        """the field as read (bytes after the terminator kept) unless it was changed"""
        raw = getattr(self, 'raw_' + attr, None)
        text = getattr(self, attr)
        if raw is not None and raw.split(b'\0')[0].decode() == text:
            return raw
        return text.encode().ljust(size, b'\0')

    def head(self):
        return (self.magic + b'\1' + self._str('name', 0x38) + b'\1' + self._str('subname', 0x40) + b'\1' +
                struct.pack('>3fB', *self.start, self.use_start) + b'\1' + struct.pack('>i', self.unk1) + b'\1' +
                struct.pack('>3fi', *self.unk2, self.unk3) + b'\1' + self._str('bone', 0x40))


class Cliff(Entry):
    def read(self, r):
        self.read_head(r)
        r.u8()
        self.x, self.y, self.angle = r.f32(3)
        self.line = r.i32()

    def write(self):
        return self.head() + b'\1' + struct.pack('>3fi', self.x, self.y, self.angle, self.line)


class Collision(Entry):
    def __init__(self, name='', subname=''):
        super().__init__(name, subname, MAGIC_COL)
        self.flags = [0, 0, 0, 0]
        self.verts, self.normals, self.cliffs, self.mats = [], [], [], []

    def read(self, r):
        self.read_head(r)
        self.flags = list(r.take(4))
        r.u8()
        self.verts = []
        for _ in range(r.i32()):
            r.u8()
            self.verts.append(r.f32(2))
        r.u8()
        self.normals = []
        for _ in range(r.i32()):
            r.u8()
            self.normals.append(r.f32(2))
        r.u8()
        self.cliffs = []
        for _ in range(r.i32()):
            c = Cliff()
            c.read(r)
            self.cliffs.append(c)
        r.u8()
        self.mats = []
        for _ in range(r.i32()):
            r.u8()
            self.mats.append(bytearray(r.take(12)))

    def write(self):
        b = self.head() + bytes(self.flags) + b'\1' + struct.pack('>i', len(self.verts))
        for v in self.verts:
            b += b'\1' + struct.pack('>2f', *v)
        b += b'\1' + struct.pack('>i', len(self.normals))
        for n in self.normals:
            b += b'\1' + struct.pack('>2f', *n)
        b += b'\1' + struct.pack('>i', len(self.cliffs))
        for c in self.cliffs:
            b += c.write()
        b += b'\1' + struct.pack('>i', len(self.mats))
        for m in self.mats:
            b += b'\1' + bytes(m)
        return b


class Point(Entry):
    def read(self, r):
        self.read_head(r)
        r.u8()
        self.x, self.y = r.f32(2)

    def write(self):
        return self.head() + b'\1' + struct.pack('>2f', self.x, self.y)


class Bounds(Entry):
    def read(self, r):
        self.read_head(r)
        r.u8()
        self.left, self.right, self.top, self.bottom = r.f32(4)

    def write(self):
        return self.head() + b'\1' + struct.pack('>4f', self.left, self.right, self.top, self.bottom)


class Shape:
    def read(self, r):
        r.u8()
        self.type = r.i32()
        self.v = r.f32(4)
        r.u8()
        r.u8()
        self.points = []
        for _ in range(r.i32()):
            r.u8()
            self.points.append(r.f32(2))

    def write(self):
        b = b'\3' + struct.pack('>i4f', self.type, *self.v) + b'\1\1' + struct.pack('>i', len(self.points))
        for p in self.points:
            b += b'\1' + struct.pack('>2f', *p)
        return b


class ItemSpawner(Entry):
    def read(self, r):
        self.read_head(r)
        r.u8()
        self.id = r.i32()
        r.u8()
        r.u8()
        self.sections = []
        for _ in range(r.i32()):
            r.u8()
            s = Shape()
            s.read(r)
            self.sections.append(s)

    def write(self):
        b = self.head() + b'\1' + struct.pack('>i', self.id) + b'\1\1' + struct.pack('>i', len(self.sections))
        for s in self.sections:
            b += b'\1' + s.write()
        return b


class GeneralShape(Entry):
    def read(self, r):
        self.read_head(r)
        r.u8()
        self.id = r.i32()
        self.shape = Shape()
        self.shape.read(r)

    def write(self):
        return self.head() + b'\1' + struct.pack('>i', self.id) + self.shape.write()


class GeneralPoint(Entry):
    def read(self, r):
        self.read_head(r)
        r.u8()
        self.id = r.i32()
        r.u8()
        self.type = r.i32()
        self.x, self.y, self.z = r.f32(3)
        self.pad = r.take(0x10)

    def write(self):
        return self.head() + b'\1' + struct.pack('>i', self.id) + b'\1' + struct.pack('>i3f', self.type, self.x, self.y, self.z) + self.pad


class DamageShape(Entry):
    """a damage collision (Luigi's Mansion's pillars: capsules "DamageeCapsule_00_LD_Pillar", subname
    "00_LD_Pillar", which the stage finds by subname): type (3 capsule), start x / y / z, direction
    dx / dy / dz, radius, a float (0), a byte (0)"""
    def __init__(self, name='', subname='', magic=MAGIC_1):
        super().__init__(name, subname, magic)
        self.type, self.v, self.tail_byte = 3, [0.0] * 8, 0

    def read(self, r):
        self.read_head(r)
        r.u8()
        self.type = r.i32()
        self.v = list(r.f32(8))
        self.tail_byte = r.u8()

    def write(self):
        return self.head() + b'\1' + struct.pack('>i8f', self.type, *self.v) + bytes([self.tail_byte])


def capsule(name, subname, start, direction, radius):
    """a DamageShape capsule from start (x, y, z) along direction (dx, dy, dz)"""
    d = DamageShape(name, subname)
    d.v = [*map(float, start), *map(float, direction), float(radius), 0.0]
    return d


class Raw(Entry):
    """an entry kept as its bytes (damage shapes: their length depends on the type)"""


SECTIONS = [('collisions', Collision), ('spawns', Point), ('respawns', Point), ('camera', Bounds),
            ('blast', Bounds), ('enemy', None), ('s7', None), ('s8', None), ('s9', None), ('s10', None),
            ('s11', None), ('damage', DamageShape), ('items', ItemSpawner), ('shapes', GeneralShape),
            ('points', GeneralPoint)]


class LVD:
    def __init__(self, path=None):
        self.head = bytes.fromhex('000000010A014C564431')
        for name, _ in SECTIONS:
            setattr(self, name, [])
        self.tail = b''
        if path:
            self.read(open(path, 'rb').read())

    def read(self, d):
        r = R(d)
        self.head = r.take(10)
        for name, cls in SECTIONS:
            start = r.o
            r.u8()
            n = r.i32()
            if n and cls is None:
                r.o = start
                break
            items = []
            for _ in range(n):
                e = cls()
                e.read(r)
                items.append(e)
            setattr(self, name, items)
        self.tail = d[r.o:]

    def write(self):
        b = bytearray(self.head)
        for name, cls in SECTIONS:
            items = getattr(self, name)
            if cls is None:
                assert not items
            b += b'\1' + struct.pack('>i', len(items))
            for e in items:
                b += e.write()
        return bytes(b) + self.tail


def collision(name, verts, normals, mats, cliffs=(), drop_through=False):
    """a Collision from lists (normals / mats: one per line; cliffs: [(x, y, -1|1, line)])"""
    c = Collision(name)
    c.flags = [0, 0, 0, 1 if drop_through else 0]
    c.verts = [list(map(float, v)) for v in verts]
    c.normals = [list(map(float, n)) for n in normals]
    c.mats = [bytearray(m) for m in mats]
    for x, y, ang, line in cliffs:
        cl = Cliff('', '', MAGIC_COL)
        cl.x, cl.y, cl.angle, cl.line = float(x), float(y), float(ang), line
        c.cliffs.append(cl)
    return c


def main():
    if sys.argv[1] == 'info':
        lv = LVD(sys.argv[2])
        for c in lv.collisions:
            print('collision %r %r flags %s bone %r start %s use %d' % (c.name, c.subname, c.flags, c.bone, c.start, c.use_start))
            for i, v in enumerate(c.verts):
                extra = ''
                if i < len(c.normals):
                    extra = ' normal (%.2f, %.2f) mat %s' % (c.normals[i][0], c.normals[i][1], c.mats[i].hex() if i < len(c.mats) else '-')
                print('   (%.2f, %.2f)%s' % (v[0], v[1], extra))
            for cl in c.cliffs:
                print('   cliff %r (%.2f, %.2f) %.0f line %d' % (cl.name, cl.x, cl.y, cl.angle, cl.line))
        for s in lv.spawns:
            print('spawn %r (%.2f, %.2f)' % (s.name, s.x, s.y))
        for s in lv.respawns:
            print('respawn %r (%.2f, %.2f)' % (s.name, s.x, s.y))
        for b in lv.camera:
            print('camera %r l %.1f r %.1f t %.1f b %.1f' % (b.name, b.left, b.right, b.top, b.bottom))
        for b in lv.blast:
            print('blast %r l %.1f r %.1f t %.1f b %.1f' % (b.name, b.left, b.right, b.top, b.bottom))
        for it in lv.items:
            print('items %r id 0x%X' % (it.name, it.id), [(s.type, [round(x, 1) for x in s.v], s.points) for s in it.sections])
        for g in lv.shapes:
            print('shape %r id %d type %d %s %s' % (g.name, g.id, g.shape.type, [round(x, 1) for x in g.shape.v], g.shape.points))
        for p in lv.points:
            print('point %r id %d type %d (%.1f, %.1f, %.1f)' % (p.name, p.id, p.type, p.x, p.y, p.z))
        print('tail %d bytes' % len(lv.tail))
        assert lv.write() == open(sys.argv[2], 'rb').read(), 'round trip differs'
        print('round trip ok')


if __name__ == '__main__':
    main()
