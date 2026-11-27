"""A CRO / CRS loader that does what the 3DS RO service (and Citra's HLE copy of it, ro/cro_helper.cpp) does, into
any memory with write(addr, bytes) / read(addr, size): for the tests' fake Azahar.

load_crs: the file at its address; header offsets rebased (+ address); the CRS's segment table already holds
code.bin's absolute addresses (it is not rebased); the named export table's name offsets rebased.
load_cro: the file at `base`; header offsets rebased; the segment table rebased (text / rodata + base, .data -> the
data buffer, which gets the file's .data bytes, .bss -> the bss buffer, zeroed); the export / import tables' name and
patch offsets rebased; the internal relocations applied (type 2 R_ARM_ABS32, 3 R_ARM_REL32, 28 / 29 ARM call /
jump24); the named imports resolved against the loaded modules' exports and their patch batches written; the
module linked into the list (header +0x88 next, +0x8C previous; static.crs is the head).
"""
import struct

OFFSET_FIELDS = [0x84, 0xB0, 0xB8, 0xC0, 0xC8, 0xD0, 0xD8, 0xE0, 0xE8, 0xF0, 0xF8, 0x100, 0x108, 0x110, 0x118,
                 0x120, 0x128, 0x130]


def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


class Loaded:
    def __init__(s, name, base, segs, exports):
        s.name, s.base, s.segs, s.exports = name, base, segs, exports


def _exports(x, segs_rt):
    eo, en = u32(x, 0xD0), u32(x, 0xD4)
    out = {}
    for i in range(en):
        no, tag = struct.unpack_from('<II', x, eo + 8 * i)
        nm = x[no:x.index(b'\0', no)].decode('latin1')
        if (tag & 0xF) < len(segs_rt):
            out[nm] = segs_rt[tag & 0xF][0] + (tag >> 4)
    return out


def _rebase_header(img, base):
    for f in OFFSET_FIELDS:
        v = u32(img, f)
        struct.pack_into('<I', img, f, v + base)


def _rebase_named_table(img, x, at, n, stride, base, fields=(0,)):
    for i in range(n):
        for f in fields:
            o = at + stride * i + f
            struct.pack_into('<I', img, o, u32(x, o) + base)


def load_crs(mem, x, addr):
    img = bytearray(x)
    so, sn = u32(x, 0xC8), u32(x, 0xCC)
    segs = [list(struct.unpack_from('<III', x, so + 12 * i)) for i in range(sn)]
    exports = _exports(x, segs)
    eo, en = u32(x, 0xD0), u32(x, 0xD4)
    _rebase_named_table(img, x, eo, en, 8, addr)
    _rebase_header(img, addr)
    struct.pack_into('<II', img, 0x88, 0, 0)
    mem.write(addr, bytes(img))
    return Loaded(x[u32(x, 0xC0):u32(x, 0xC0) + u32(x, 0xC4)].split(b'\0')[0].decode(), addr, segs, exports)


def _apply(mem, target, typ, value):
    if typ == 2:
        mem.write(target, struct.pack('<I', value & 0xFFFFFFFF))
    elif typ == 3:
        mem.write(target, struct.pack('<I', (value - target) & 0xFFFFFFFF))
    elif typ in (28, 29):
        old = struct.unpack('<I', mem.read(target, 4))[0]
        off = ((value - target - 8) >> 2) & 0xFFFFFF
        mem.write(target, struct.pack('<I', (old & 0xFF000000) | off))
    elif typ == 0:
        pass
    else:
        raise ValueError('relocation type %d' % typ)


def load_cro(mem, x, base, data_addr, bss_addr, modules, unresolved=0):
    img = bytearray(x)
    so, sn = u32(x, 0xC8), u32(x, 0xCC)
    fsegs = [list(struct.unpack_from('<III', x, so + 12 * i)) for i in range(sn)]
    rt = []
    data = b''
    for off, size, typ in fsegs:
        if typ == 2 and size:
            rt.append([data_addr, size, typ])
            data = x[off:off + size]
        elif typ == 3 and size:
            rt.append([bss_addr, size, typ])
        elif off:
            rt.append([base + off, size, typ])
        else:
            rt.append([0, size, typ])
    for i, (a, n, t) in enumerate(rt):
        struct.pack_into('<III', img, so + 12 * i, a, n, t)
    # tables: named exports {name, tag}; import modules {name, indexed off, n, anon off, n}; named imports
    # {name, patch batch}; indexed imports {index, batch}; anonymous imports {tag, batch}
    _rebase_named_table(img, x, u32(x, 0xD0), u32(x, 0xD4), 8, base)
    _rebase_named_table(img, x, u32(x, 0xF0), u32(x, 0xF4), 20, base, (0, 4, 12))
    _rebase_named_table(img, x, u32(x, 0x100), u32(x, 0x104), 8, base, (0, 4))
    _rebase_named_table(img, x, u32(x, 0x108), u32(x, 0x10C), 8, base, (4,))
    _rebase_named_table(img, x, u32(x, 0x110), u32(x, 0x114), 8, base, (4,))
    _rebase_header(img, base)
    mem.write(base, bytes(img))
    if data:
        mem.write(data_addr, data)
    if bss_addr and rt and any(t == 3 for _a, _n, t in rt):
        mem.write(bss_addr, b'\0' * next(n for _a, n, t in rt if t == 3))
    seg_of = lambda tag: rt[tag & 0xF][0] + (tag >> 4)
    # internal relocations
    ro, rn = u32(x, 0x128), u32(x, 0x12C)
    for i in range(rn):
        tgt, typ, seg, _u1, _u2, add = struct.unpack_from('<IBBBBI', x, ro + 12 * i)
        _apply(mem, seg_of(tgt), typ, rt[seg][0] + add)
    # named imports
    exports = {}
    for m in modules:
        exports.update(m.exports)
    io, inn = u32(x, 0x100), u32(x, 0x104)
    missing = []
    for i in range(inn):
        no, bo = struct.unpack_from('<II', x, io + 8 * i)
        nm = x[no:x.index(b'\0', no)].decode('latin1')
        sym = exports.get(nm)
        if sym is None:
            missing.append(nm)
            sym = unresolved
        p = bo
        while True:
            tgt, typ, last, _u1, _u2, add = struct.unpack_from('<IBBBBI', x, p)
            _apply(mem, seg_of(tgt), typ, sym + add)
            if last:
                break
            p += 12
    me = Loaded(x[u32(x, 0xC0):u32(x, 0xC0) + u32(x, 0xC4)].split(b'\0')[0].decode(), base, rt, _exports(x, rt))
    me.missing = missing
    me.file_segs = fsegs
    return me


def link(mem, crs, cros):
    """static.crs -> first CRO -> ... (next words); previous words back to the CRS"""
    chain = [crs] + list(cros)
    for i, m in enumerate(chain):
        nxt = chain[i + 1].base if i + 1 < len(chain) else 0
        prv = chain[i - 1].base if i > 0 else (chain[-1].base if len(chain) > 1 else 0)
        mem.write(m.base + 0x88, struct.pack('<II', nxt, prv))
