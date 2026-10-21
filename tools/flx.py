#!/usr/bin/env python3
"""Smash 4 Wii U HUD movies (data/ui/info/<name>/<name>.flx, magic 'flx2') and their texture lists
(texlist.lst, 'TLST'): read, edit and write them back (byte-exact for every unmodified file).
Format: docs/flx2-format.md.

  python3 tools/flx.py info FILE.flx [-v] [SPRITE...]  header, tables and the sprites' timelines
                                                   (-v: whole display list at every keyframe)
  python3 tools/flx.py tlst texlist.lst            the texture list's images
  python3 tools/flx.py check DIR...                round trip every .flx / texlist.lst under DIR

A movie is Flash-like: sprites (movie clips; sprite 0 is the root) with frames, frame labels and
keyframes; each keyframe is the full display list of that frame: placements of images, sprites
or text fields, with a transform and a colour transform. The game finds instances by name
(e.g. root/dmg_1/ko_mc) and drives their frames by label. All tables are global and referenced by
index; this module keeps them that way (Flx.sprites, .keys, .places, ...) and has helpers to append
new images, sprites and instances (add_*, insert_place).
"""
import math
import os
import struct
import sys
from dataclasses import dataclass, field

NONE16 = 0xFFFF
NONE32 = 0xFFFFFFFF
KIND_IMAGE, KIND_SPRITE, KIND_NAMED_SPRITE, KIND_TEXT = 0, 1, 2, 4
KIND_NAMES = {0: 'image', 1: 'sprite', 2: 'sprite', 4: 'text'}


def _pad4(b):
    return b + b'\0' * (-len(b) % 4)


def _enc(s):
    return s.encode('cp932', 'surrogateescape')


def _dec(b):
    return b.decode('cp932', 'surrogateescape')


# ---------------------------------------------------------------- records
@dataclass
class Transform:
    """flags: 1 x, 2 y, 4 scale x (also y without 8), 8 scale y, 0x10 angle rot, 0x20 angle rot2
    (u16, 0x10000 = 360 degrees, clockwise on screen). Alone, rot is a rotation; with 0x20 they are
    Flash's skewX (rot: the y axis's angle) and skewY (rot2: the x axis's angle), e.g. rot2 = 180
    degrees mirrors horizontally, rot = 180 vertically"""
    flags: int = 3
    x: float = 0.0
    y: float = 0.0
    sx: float = 1.0
    sy: float = 1.0
    rot: int = 0
    rot2: int = 0

    @staticmethod
    def make(x=0.0, y=0.0, sx=1.0, sy=None, deg=0.0):
        """x / y position, scale (sy defaults to sx), rotation in degrees (clockwise on screen)"""
        f = 3
        if sx != 1.0 or (sy is not None and sy != sx):
            f |= 4
        if sy is not None and sy != sx:
            f |= 8
        r = int(round(deg / 360.0 * 0x10000)) & 0xFFFF
        if r:
            f |= 0x10
        return Transform(f, x, y, sx, sy if sy is not None else sx, r, r)

    def matrix(self):
        """(a, b, c, d, tx, ty): x' = a x + c y + tx, y' = b x + d y + ty"""
        f = self.flags
        sx = self.sx if f & 4 else 1.0
        sy = self.sy if f & 8 else sx
        ry = self.rot * math.pi / 0x8000 if f & 0x10 else 0.0
        rx = self.rot2 * math.pi / 0x8000 if f & 0x20 else ry
        return (sx * math.cos(rx), sx * math.sin(rx), -sy * math.sin(ry), sy * math.cos(ry),
                self.x if f & 1 else 0.0, self.y if f & 2 else 0.0)

    def encode(self):
        f = self.flags
        out = bytes([f])
        for bit, v in ((1, self.x), (2, self.y), (4, self.sx), (8, self.sy)):
            if f & bit:
                out += struct.pack('>f', v)
        for bit, v in ((0x10, self.rot), (0x20, self.rot2)):
            if f & bit:
                out += struct.pack('>H', v)
        return out

    @staticmethod
    def decode(b, o):
        f = b[o]
        t = Transform(f)
        o += 1
        for bit, k in ((1, 'x'), (2, 'y'), (4, 'sx'), (8, 'sy')):
            if f & bit:
                setattr(t, k, struct.unpack('>f', b[o:o + 4])[0])
                o += 4
        if not f & 8:
            t.sy = t.sx
        for bit, k in ((0x10, 'rot'), (0x20, 'rot2')):
            if f & bit:
                setattr(t, k, struct.unpack('>H', b[o:o + 2])[0])
                o += 2
        if not f & 0x20:
            t.rot2 = t.rot
        assert not f & 0xC0, 'transform flags 0x%X' % f
        return t, o

    def __str__(self):
        f = self.flags
        s = '(%g, %g)' % (self.x, self.y)
        if f & 4:
            s += ' scale %g' % self.sx + (' x %g' % self.sy if f & 8 else '')
        if f & 0x10:
            s += ' rot %.1f' % (self.rot * 360.0 / 0x10000)
        if f & 0x20:
            s += '/%.1f' % (self.rot2 * 360.0 / 0x10000)
        return s


@dataclass
class Color:
    """colour transform, channels A R G B: out = in * mul / 100 + add (add in 0-255 units)"""
    mul: tuple = (100, 100, 100, 100)
    add: tuple = (0, 0, 0, 0)

    def __str__(self):
        s = 'mul %s' % '/'.join(map(str, self.mul))
        return s + (' add %s' % '/'.join(map(str, self.add)) if any(self.add) else '')


@dataclass
class Sprite:
    """a movie clip: frames [frame0, +nframes) of Flx.frames, keyframes [key0, +nkeys) of Flx.keys,
    labels [label0, +nlabels) of Flx.labels; nslots = how many child slots (Place.slot) it uses"""
    name: int = 0          # string index ('undefined' in every sample)
    nframes: int = 0
    nkeys: int = 0
    nlabels: int = 0
    nslots: int = 0
    frame0: int = 0
    key0: int = 0
    label0: int = 0


@dataclass
class Key:
    """keyframe: the whole display list (Flx.places indices, highest depth first) and a frame
    action (NONE16 = none): an index into the game's native per-sprite function table (compiled
    ActionScript: stop(), gotoAndPlay(...)), not in the file. New sprites past the end of that
    table (dmg: 0x5F entries) must not have actions."""
    action: int = NONE16
    places: list = field(default_factory=list)


@dataclass
class Place:
    """one display-list entry. kind 0: image (char = Flx.images index, info = its quad);
    1: sprite instance (char = sprite index); 2: named sprite instance (info = Info whose name is
    the instance name); 4: text field (char = Flx.texts index, info = its box). Images and texts
    have no transform / colour (NONE16): they sit at their Info rect in their own sprite."""
    kind: int = KIND_SPRITE
    slot: int = 0          # child slot in the parent sprite: same slot and char = same instance
    char: int = 0
    depth: int = 0         # stacking order (higher is in front; display lists are sorted by it)
    blend: int = 0         # 0 normal, 9 on glow effects (drawn additive by flx_render)
    xform: int = NONE16    # Flx.transforms index
    color: int = NONE16    # Flx.colors index
    info: int = NONE16     # Flx.infos index


@dataclass
class Info:
    """an instance name and / or a rectangle (image quad, text box); name None = no name"""
    name: object = None    # string index
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0


@dataclass
class Text:
    """dynamic text field: name = its message / variable (e.g. 'STR201$66'), box size, format"""
    name: int = 0
    width: int = 0
    height: int = 0
    unk: int = 1
    fmt: int = 0           # Flx.formats index


@dataclass
class Format:
    """text format: text = string index of the authoring text (often the replacement image's name),
    color = 0xRRGGBB, size = font size, align 0 left / 1 centre / 2 right (guess), b1-b3 unknown"""
    text: int = 0
    color: int = 0xFFFFFF
    size: int = 0
    align: int = 0
    b1: int = 0
    b2: int = 2
    b3: int = 0


@dataclass
class Label:
    frame: int = 0         # frame within the sprite
    name: int = 0          # string index


# ---------------------------------------------------------------- movie
class Flx:
    def __init__(self):
        self.bg_color = 0
        self.fps = 60
        self.width, self.height = 1920, 1080
        self.unk_counts = [0] * 6   # header 0x28-0x33: not read by the loader; kept as they are
        self.sprites = []
        self.transforms = []
        self.colors = []
        self.infos = []
        self.texts = []
        self.formats = []
        self.keys = []
        self.places = []
        self.labels = []
        self.frames = []            # per sprite frame: index of its keyframe within the sprite
        self.images = []            # image symbol names (texlist.lst entries)
        self.strings = []

    # ---- lookups
    def string(self, i):
        return '-' if i is None or i == NONE32 else self.strings[i]

    def sprite_keys(self, s):
        sp = self.sprites[s]
        return self.keys[sp.key0:sp.key0 + sp.nkeys]

    def sprite_labels(self, s):
        sp = self.sprites[s]
        return {self.strings[lb.name]: lb.frame for lb in self.labels[sp.label0:sp.label0 + sp.nlabels]}

    def frame_key(self, s, frame):
        """the Key shown at a frame (number or label) of sprite s"""
        sp = self.sprites[s]
        if isinstance(frame, str):
            frame = self.sprite_labels(s)[frame]
        return self.keys[sp.key0 + self.frames[sp.frame0 + min(frame, sp.nframes - 1)]]

    def instance_name(self, p):
        if p.kind == KIND_NAMED_SPRITE and p.info != NONE16:
            return self.string(self.infos[p.info].name)
        return None

    def parents(self, s):
        """[(parent sprite, Place index)] of every placement of sprite s"""
        out = []
        for si, sp in enumerate(self.sprites):
            seen = set()
            for k in self.keys[sp.key0:sp.key0 + sp.nkeys]:
                for pi in k.places:
                    p = self.places[pi]
                    if p.kind in (KIND_SPRITE, KIND_NAMED_SPRITE) and p.char == s and pi not in seen:
                        seen.add(pi)
                        out.append((si, pi))
        return out

    # ---- building
    def add_string(self, s):
        if s in self.strings:
            return self.strings.index(s)
        self.strings.append(s)
        return len(self.strings) - 1

    def add_image(self, name):
        """image symbol (needs a texlist.lst entry of the same name: Tlst.add)"""
        if name in self.images:
            return self.images.index(name)
        self.images.append(name)
        return len(self.images) - 1

    def add_info(self, name=None, x=0.0, y=0.0, w=0.0, h=0.0):
        inf = Info(None if name is None else self.add_string(name), x, y, w, h)
        if inf in self.infos:
            return self.infos.index(inf)
        self.infos.append(inf)
        return len(self.infos) - 1

    def add_transform(self, t):
        if t in self.transforms:
            return self.transforms.index(t)
        self.transforms.append(t)
        return len(self.transforms) - 1

    def add_color(self, mul=(100, 100, 100, 100), add=(0, 0, 0, 0)):
        c = Color(tuple(mul), tuple(add))
        if c in self.colors:
            return self.colors.index(c)
        self.colors.append(c)
        return len(self.colors) - 1

    def add_place(self, p):
        self.places.append(p)
        return len(self.places) - 1

    def image_place(self, image, w, h, cx=0.5, cy=0.5, slot=0, depth=0):
        """Place of an image (name or index) drawn w x h with its (cx, cy) fraction at the origin"""
        if isinstance(image, str):
            image = self.add_image(image)
        return Place(KIND_IMAGE, slot, image, depth, info=self.add_info(None, -w * cx, -h * cy, w, h))

    def sprite_place(self, sprite, name=None, transform=None, color=None, slot=0, depth=0, blend=0):
        """Place of a sprite instance (named if name), transform a Transform, color a Color"""
        xf = self.add_transform(transform or Transform.make())
        col = self.add_color(*((color.mul, color.add) if color else ()))
        if name is None:
            return Place(KIND_SPRITE, slot, sprite, depth, blend, xf, col, NONE16)
        return Place(KIND_NAMED_SPRITE, slot, sprite, depth, blend, xf, col, self.add_info(name))

    def add_sprite(self, frames, labels=None, actions=None):
        """append a sprite. frames: one display list a frame, each a list of Place (or Flx.places
        indices), bottom first; equal consecutive lists share a keyframe. labels: {name: frame};
        actions: {frame: action number}. Returns the sprite index."""
        labels, actions = labels or {}, actions or {}
        sp = Sprite(0, len(frames), 0, len(labels), 0, len(self.frames), len(self.keys), len(self.labels))
        prev = None
        for fi, lst in enumerate(frames):
            idx = [p if isinstance(p, int) else self.add_place(p) for p in lst]
            ps = [self.places[i] for i in idx]
            sp.nslots = max([sp.nslots] + [p.slot + 1 for p in ps])
            act = actions.get(fi, NONE16)
            if idx != prev or act != NONE16 or fi in labels.values():
                self.keys.append(Key(act, sorted(idx, key=lambda i: -self.places[i].depth)
                                     if any(p.depth for p in ps) else idx[::-1]))
                sp.nkeys += 1
                prev = idx
            self.frames.append(sp.nkeys - 1)
        for name, fr in sorted(labels.items(), key=lambda kv: kv[1]):
            self.labels.append(Label(fr, self.add_string(name)))
        self.sprites.append(sp)
        return len(self.sprites) - 1

    def insert_place(self, sprite, place, keys=None):
        """add a Place (or index) to keyframes (local indices; default all) of an existing sprite,
        at its depth; slot 0 / depth 0 (defaults) become a new slot on top of everything"""
        pi = place if isinstance(place, int) else self.add_place(place)
        p = self.places[pi]
        sp = self.sprites[sprite]
        ks = self.keys[sp.key0:sp.key0 + sp.nkeys]
        if not isinstance(place, int) and p.slot == 0 and p.depth == 0:
            p.slot = sp.nslots
            p.depth = 1 + max([self.places[i].depth for k in ks for i in k.places] + [-1])
        sp.nslots = max(sp.nslots, p.slot + 1)
        for j in range(sp.nkeys) if keys is None else keys:
            lst = ks[j].places
            at = 0
            while at < len(lst) and self.places[lst[at]].depth > p.depth:
                at += 1
            lst.insert(at, pi)
        return pi


# ---------------------------------------------------------------- read / write
def read(data):
    """parse .flx bytes into a Flx"""
    assert data[:4] == b'flx2', data[:4]
    f = Flx()
    f.bg_color, f.fps, f.width, f.height = struct.unpack('>I3H', data[4:14])
    counts = struct.unpack('>13H', data[14:40])
    f.unk_counts = list(struct.unpack('>6H', data[40:52]))
    assert data[52:104] == bytes(52), 'pointer slots not zero'
    o = 104

    def section(n):
        nonlocal o
        if not n:
            return b''
        size = struct.unpack('>I', data[o:o + 4])[0]
        b = data[o + 4:o + 4 + size]
        o += 4 + size
        return b

    def blobs(n):
        nonlocal o
        if not n:
            return []
        table = section(n)            # n pointers, filled in by the loader
        assert table == bytes(4 * n), 'pointer table not zero'
        out = []
        for _ in range(n):
            size = struct.unpack('>I', data[o:o + 4])[0]
            out.append(data[o + 4:o + 4 + size])
            o += 4 + size
        return out

    (n_spr, n_xf, n_col, n_inf, n_txt, n_fmt, n_key, n_pl, n_lst, n_lab, n_fr, n_img, n_str) = counts
    b = section(n_spr)
    f.sprites = [Sprite(*struct.unpack('>I4H3I', b[24 * i:24 * i + 24])) for i in range(n_spr)]
    b = section(n_xf)
    offs = {}
    p = 0
    for i in range(n_xf):
        offs[p] = i
        t, p = Transform.decode(b, p)
        f.transforms.append(t)
    assert b[p:] == bytes(len(b) - p) and len(b) == (p + 3) & ~3, 'transform padding'
    b = section(n_col)
    for i in range(n_col):
        v = struct.unpack('>4B4h', b[12 * i:12 * i + 12])
        f.colors.append(Color(v[:4], v[4:]))
    b = section(n_inf)
    for i in range(n_inf):
        v = struct.unpack('>I4f', b[20 * i:20 * i + 20])
        f.infos.append(Info(None if v[0] == NONE32 else v[0], *v[1:]))
    b = section(n_txt)
    f.texts = [Text(*struct.unpack('>I2H2I', b[16 * i:16 * i + 16])) for i in range(n_txt)]
    b = section(n_fmt)
    for i in range(n_fmt):
        t, c, a, b1, b2, b3 = struct.unpack('>2I4B', b[12 * i:12 * i + 12])
        f.formats.append(Format(t, c >> 8, c & 0xFF, a, b1, b2, b3))
    b = section(n_key)
    keys = [struct.unpack('>2HI', b[8 * i:8 * i + 8]) for i in range(n_key)]
    b = section(n_pl)
    for i in range(n_pl):
        kind, slot, char, depth, blend, xf, col, inf = struct.unpack('>8H', b[16 * i:16 * i + 16])
        f.places.append(Place(kind, slot, char, depth, blend, NONE16 if xf == NONE16 else offs[xf], col, inf))
    lists = blobs(n_lst)
    for i, (act, n, li) in enumerate(keys):
        lst = lists[li]
        assert li == i and len(lst) == (2 * n + 3) & ~3, 'keyframe list'
        f.keys.append(Key(act, list(struct.unpack('>%dH' % n, lst[:2 * n]))))
    b = section(n_lab)
    f.labels = [Label(*struct.unpack('>2I', b[8 * i:8 * i + 8])) for i in range(n_lab)]
    b = section(n_fr)
    f.frames = list(struct.unpack('>%dH' % n_fr, b[:2 * n_fr]))
    f.images = [_dec(s.rstrip(b'\0')) for s in blobs(n_img)]
    f.strings = [_dec(s.rstrip(b'\0')) for s in blobs(n_str)]
    assert o == len(data), 'trailing data at 0x%X' % o
    return f


def write(f):
    """Flx -> .flx bytes"""
    xf_offs, xf = [], b''
    for t in f.transforms:
        xf_offs.append(len(xf))
        xf += t.encode()
    assert len(xf) < NONE16, 'transform table too big for 16-bit offsets'
    counts = [len(f.sprites), len(f.transforms), len(f.colors), len(f.infos), len(f.texts),
              len(f.formats), len(f.keys), len(f.places), len(f.keys), len(f.labels), len(f.frames),
              len(f.images), len(f.strings)]
    out = bytearray(b'flx2' + struct.pack('>I3H', f.bg_color, f.fps, f.width, f.height))
    out += struct.pack('>13H', *counts) + struct.pack('>6H', *f.unk_counts) + bytes(52)

    def section(n, body):
        if n:
            out.extend(struct.pack('>I', len(body)) + body)

    def blobs(items):
        if items:
            section(len(items), bytes(4 * len(items)))
            for b in items:
                out.extend(struct.pack('>I', len(b)) + b)

    section(counts[0], b''.join(struct.pack('>I4H3I', s.name, s.nframes, s.nkeys, s.nlabels, s.nslots,
                                            s.frame0, s.key0, s.label0) for s in f.sprites))
    section(counts[1], _pad4(xf))
    section(counts[2], b''.join(struct.pack('>4B4h', *(tuple(c.mul) + tuple(c.add))) for c in f.colors))
    section(counts[3], b''.join(struct.pack('>I4f', NONE32 if i.name is None else i.name, i.x, i.y, i.w, i.h)
                                for i in f.infos))
    section(counts[4], b''.join(struct.pack('>I2H2I', t.name, t.width, t.height, t.unk, t.fmt) for t in f.texts))
    section(counts[5], b''.join(struct.pack('>2I4B', m.text, m.color << 8 | m.size, m.align, m.b1, m.b2, m.b3)
                                for m in f.formats))
    section(counts[6], b''.join(struct.pack('>2HI', k.action, len(k.places), i) for i, k in enumerate(f.keys)))
    section(counts[7], b''.join(struct.pack('>8H', p.kind, p.slot, p.char, p.depth, p.blend,
                                            NONE16 if p.xform == NONE16 else xf_offs[p.xform], p.color, p.info)
                                for p in f.places))
    blobs([_pad4(struct.pack('>%dH' % len(k.places), *k.places)) for k in f.keys])
    section(counts[9], b''.join(struct.pack('>2I', lb.frame, lb.name) for lb in f.labels))
    section(counts[10], _pad4(struct.pack('>%dH' % len(f.frames), *f.frames)))
    blobs([_pad4(_enc(s) + b'\0') for s in f.images])
    blobs([_pad4(_enc(s) + b'\0') for s in f.strings])
    return bytes(out)


# ---------------------------------------------------------------- texlist.lst
@dataclass
class TlstEntry:
    """an image: rectangle (u0, v0)-(u1, v1) of texture slot tex (0-1, origin top left), size in pixels"""
    name: str
    u0: float
    v0: float
    u1: float
    v1: float
    w: int
    h: int
    tex: int
    unk: int = 0
    name2: str = None      # second name offset (always the same name)


class Tlst:
    """texlist.lst: texture slots (flag 0: img-NNNNN.nut in the folder, NNNNN = slot; 0x01000000:
    supplied at run time, e.g. fighter icons / rendered text) and the images on them"""
    def __init__(self, data=None):
        self.version = 0
        self.slots = []
        self.entries = []
        self.tail = b''
        if data is not None:
            self._read(data)

    def _read(self, d):
        assert d[:4] == b'TLST', d[:4]
        ntex, n, toff, eoff, soff = struct.unpack('>I4H', d[4:16])
        assert toff == 16 and eoff == toff + 4 * ntex and soff == eoff + 32 * n
        self.slots = list(struct.unpack('>%dI' % ntex, d[toff:eoff]))

        def name(o):
            return d[soff + o:d.index(b'\0', soff + o)].decode('ascii')
        end = soff
        for i in range(n):
            o1, o2, u0, v0, u1, v1, w, h, tex, unk = struct.unpack('>2I4f4H', d[eoff + 32 * i:eoff + 32 * i + 32])
            self.entries.append(TlstEntry(name(o1), u0, v0, u1, v1, w, h, tex, unk, name(o2)))
            end = max(end, d.index(b'\0', soff + o1) + 1)
        self.tail = d[end:]

    def find(self, name):
        for e in self.entries:
            if e.name == name:
                return e
        return None

    def add(self, name, slot, x, y, w, h, tex_w, tex_h):
        """an image at pixel rect (x, y, w, h) of texture slot `slot` (tex_w x tex_h pixels)"""
        e = TlstEntry(name, x / tex_w, y / tex_h, (x + w) / tex_w, (y + h) / tex_h, w, h, slot, 0, name)
        self.entries.append(e)
        return e

    def build(self):
        names = bytearray()
        offs = {}
        for e in self.entries:
            for nm in (e.name, e.name2 or e.name):
                if nm not in offs:
                    offs[nm] = len(names)
                    names += nm.encode('ascii') + b'\0'
        n, ntex = len(self.entries), len(self.slots)
        eoff = 16 + 4 * ntex
        out = bytearray(b'TLST' + struct.pack('>I4H', ntex, n, 16, eoff, eoff + 32 * n))
        out += struct.pack('>%dI' % ntex, *self.slots)
        for e in self.entries:
            out += struct.pack('>2I4f4H', offs[e.name], offs[e.name2 or e.name], e.u0, e.v0, e.u1, e.v1,
                               e.w, e.h, e.tex, e.unk)
        return bytes(out + names + (self.tail if self.tail is not None else b'\0' * (-len(names) % 4)))


# ---------------------------------------------------------------- dump
def describe_place(f, i):
    p = f.places[i]
    if p.kind == KIND_IMAGE:
        r = f.infos[p.info]
        s = 'image %d %s  quad (%g, %g) %gx%g' % (p.char, f.images[p.char], r.x, r.y, r.w, r.h)
    elif p.kind == KIND_TEXT:
        t, r = f.texts[p.char], f.infos[p.info]
        s = 'text %d %s  box (%g, %g) %gx%g' % (p.char, f.strings[t.name], r.x, r.y, r.w, r.h)
    else:
        nm = f.instance_name(p)
        s = 'sprite %d%s  %s' % (p.char, ' "%s"' % nm if nm else '',
                                 f.transforms[p.xform] if p.xform != NONE16 else '-')
        if p.color != NONE16 and f.colors[p.color] != Color():
            s += '  ' + str(f.colors[p.color])
    if p.blend:
        s += '  blend %d' % p.blend
    return 'pl %d slot %d depth %d: %s' % (i, p.slot, p.depth, s)


def dump(f, only=None, full=False, out=sys.stdout):
    """readable dump; a keyframe lists its display list (top first) when full or first, else the
    slots that changed (+ new / ~ changed / - removed)"""
    w = out.write
    w('flx2 %dx%d %d fps, background #%06X, unk counts %s\n' % (f.width, f.height, f.fps, f.bg_color,
                                                                 f.unk_counts))
    w('%d sprites, %d keyframes, %d frames, %d placements, %d transforms, %d colours, %d infos, '
      '%d texts, %d images, %d strings\n' % (len(f.sprites), len(f.keys), len(f.frames), len(f.places),
                                            len(f.transforms), len(f.colors), len(f.infos), len(f.texts),
                                            len(f.images), len(f.strings)))
    if only is None:
        w('images: %s\n' % ' '.join('%d:%s' % kv for kv in enumerate(f.images)))
        for i, t in enumerate(f.texts):
            m = f.formats[t.fmt]
            w('text %d: %s %dx%d unk %d, format %d: "%s" #%06X size %d align %d %d %d %d\n' % (
                i, f.strings[t.name], t.width, t.height, t.unk, t.fmt, f.strings[m.text], m.color, m.size,
                m.align, m.b1, m.b2, m.b3))
    users = {}
    for si, sp in enumerate(f.sprites):
        for k in f.keys[sp.key0:sp.key0 + sp.nkeys]:
            for pi in k.places:
                p = f.places[pi]
                if p.kind in (KIND_SPRITE, KIND_NAMED_SPRITE):
                    users.setdefault(p.char, {}).setdefault(si, set()).add(f.instance_name(p) or '')
    for si, sp in enumerate(f.sprites):
        if only is not None and si not in only:
            continue
        labels = {lb.frame: f.strings[lb.name] for lb in f.labels[sp.label0:sp.label0 + sp.nlabels]}
        w('\nsprite %d%s: %d frames, %d keyframes, %d slots%s\n' % (
            si, ' (root)' if si == 0 else '', sp.nframes, sp.nkeys, sp.nslots,
            ', name %s' % f.strings[sp.name] if sp.name else ''))
        if si in users:
            w('  placed in: %s\n' % ', '.join('%d %s' % (ps, ' '.join('"%s"' % n if n else '(unnamed)'
                                                                     for n in sorted(names)))
                                            for ps, names in sorted(users[si].items())))
        prev, shown = None, {}
        for fr in range(sp.nframes):
            k = f.frames[sp.frame0 + fr]
            lab = labels.get(fr)
            if k == prev and lab is None:
                continue
            key = f.keys[sp.key0 + k]
            w('  frame %d%s: key %d%s\n' % (fr, ' [%s]' % lab if lab else '', k,
                                           ' action %d' % key.action if key.action != NONE16 else ''))
            if k != prev:
                cur = {f.places[pi].slot: pi for pi in key.places}
                for pi in reversed(key.places):
                    sl = f.places[pi].slot
                    if full or prev is None:
                        w('    %s\n' % describe_place(f, pi))
                    elif shown.get(sl) != pi:
                        w('   %s %s\n' % ('~' if sl in shown else '+', describe_place(f, pi)))
                for sl in sorted(set(shown) - set(cur)):
                    w('   - slot %d\n' % sl)
                shown = cur
            prev = k


def check(paths):
    """byte-exact round trip of every .flx / texlist.lst under paths"""
    n = bad = 0
    for top in paths:
        for root, _, files in os.walk(top):
            for fn in sorted(files):
                p = os.path.join(root, fn)
                if fn.endswith('.flx'):
                    d = open(p, 'rb').read()
                    ok = write(read(d)) == d
                elif fn == 'texlist.lst':
                    d = open(p, 'rb').read()
                    ok = Tlst(d).build() == d
                else:
                    continue
                n += 1
                if not ok:
                    bad += 1
                    print('MISMATCH', p)
    print('%d files, %d mismatches' % (n, bad))
    return bad == 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'info':
        f = read(open(sys.argv[2], 'rb').read())
        args = [a for a in sys.argv[3:] if a != '-v']
        dump(f, [int(x) for x in args] or None, '-v' in sys.argv[3:])
    elif cmd == 'tlst':
        t = Tlst(open(sys.argv[2], 'rb').read())
        print('%d texture slots: %s' % (len(t.slots), ' '.join('%d%s' % (i, '' if s == 0 else '*')
                                                            for i, s in enumerate(t.slots))))
        print('(* = supplied at run time; others are img-NNNNN.nut, NNNNN = slot)')
        for i, e in enumerate(t.entries):
            print('%3d %-28s slot %3d  %4dx%-4d uv (%.4f %.4f)-(%.4f %.4f)%s' % (
                i, e.name, e.tex, e.w, e.h, e.u0, e.v0, e.u1, e.v1, '' if e.name2 == e.name else ' ' + e.name2))
    elif cmd == 'check':
        sys.exit(0 if check(sys.argv[2:]) else 1)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
