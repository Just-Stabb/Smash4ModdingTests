"""Finding the loaded CRO / CRS modules in the 3DS's RAM and resolving names and file offsets to run-time addresses.

A CRO (and static.crs, code.bin's symbol module) starts with 0x80 bytes of hashes, then the "CRO0" header. The RO
service (Citra's HLE ro module, as the real one) loads a module in place: it maps the file's buffer at the address the
game chose, then "rebases" the header: every offset field (module name, segment table, export / import tables and
their strings ...) becomes an absolute address (offset + module address), the segment table gets each segment's run-time
address (text / rodata stay in place: address = module + file offset; .data and .bss go to the buffers the game passed),
the internal relocations are applied and the imports patched. Loaded modules are chained through the header's
next / previous words (+0x88 / +0x8C), with static.crs as the list's head.

The named export table keeps its segment tags ({segment index | offset << 4}, not rebased), so a module's exports give
the run-time address of every exported name (segment's run-time address + offset) AND the file offset it had in the
dump (the dump's segment file offset + offset), which identifies the module's version exactly.

Header fields used (3dbrew "CRO0"): 0x80 magic, 0x84 name, 0x88 next, 0x8C previous, 0x90 file size, 0xB0 / 0xB4
code, 0xC0 / 0xC4 module name, 0xC8 / 0xCC segment table {offset, size, type 0 text / 1 rodata / 2 data / 3 bss},
0xD0 / 0xD4 named exports {name, tag}, 0xE0 / 0xE4 export strings.
"""
import struct

HDR = 0x80
MAGIC = b'CRO0'
HEADER_SIZE = 0x138
# where the game's modules can live: the code region after code.bin, the heap, the linear heap (old / new 3DS)
# (after code.bin's data first: the RO service maps a CRO where the game asks, usually after the main module)
DEFAULT_REGIONS = [(0x00B00000, 0x04000000), (0x08000000, 0x10000000), (0x00100000, 0x00B00000),
                   (0x14000000, 0x1C000000), (0x30000000, 0x38000000)]


class Module:
    def __init__(s, base, hdr):
        s.base = base
        s.hdr = hdr
        w = lambda o: struct.unpack_from('<I', hdr, o)[0]
        s.w = w
        s.file_size = w(0x90)
        s.loaded = w(0xC0) >= base          # rebased header (absolute pointers)
        s.name = None
        s.segments = []                     # run-time [addr, size, type]
        s.exports = None                    # name -> (seg index, offset)
        s.next, s.prev = w(0x88), w(0x8C)

    def ptr(s, field):
        v = s.w(field)
        return v if s.loaded else s.base + v

    def seg_addr(s, idx, off):
        return s.segments[idx][0] + off

    def range(s):
        return s.base, s.base + max(s.file_size, 0x1000)

    def text_range(s):
        for a, n, t in s.segments:
            if t == 0 and n:
                return a, a + n
        return s.range()

    def contains(s, addr):
        for a, n, _t in s.segments:
            if a <= addr < a + n:
                return True
        return False

    def to_runtime(s, file_off, file_segments):
        """a file offset of the dump's module -> run-time address (file_segments: [[off, size, type], ...])"""
        for i, (fo, fn, _t) in enumerate(file_segments):
            if fn and fo <= file_off < fo + fn and i < len(s.segments):
                return s.segments[i][0] + (file_off - fo)
        return s.base + file_off

    def to_file(s, addr, file_segments):
        for i, (a, n, _t) in enumerate(s.segments):
            if n and a <= addr < a + n and i < len(file_segments):
                return file_segments[i][0] + (addr - a)
        return None

    def __repr__(s):
        return 'Module(%s @ 0x%08X)' % (s.name, s.base)


def read_module(t, base):
    """the module whose file starts at `base`, or None (t: rsp.Target or anything with read(addr, size))"""
    try:
        hdr = t.read(base, HEADER_SIZE)
    except Exception:
        return None
    if hdr[HDR:HDR + 4] != MAGIC:
        return None
    m = Module(base, hdr)
    try:
        na, nn = m.ptr(0xC0), m.w(0xC4)
        if 0 < nn < 0x100:
            m.name = t.read(na, nn).split(b'\0')[0].decode('latin1')
        so, sn = m.ptr(0xC8), m.w(0xCC)
        if 0 < sn <= 16:
            raw = t.read(so, 12 * sn)
            for i in range(sn):
                a, n, ty = struct.unpack_from('<III', raw, 12 * i)
                if not m.loaded and ty in (0, 1) and a:
                    a += base
                m.segments.append([a, n, ty])
    except Exception:
        return m
    return m


def read_exports(t, m):
    """{mangled name: (segment index, offset)} of the module's named exports"""
    if m.exports is not None:
        return m.exports
    m.exports = {}
    eo, en = m.ptr(0xD0), m.w(0xD4)
    so, sn = m.ptr(0xE0), m.w(0xE4)
    if not (0 < en < 0x10000 and 0 < sn < 0x400000):
        return m.exports
    tab = t.read(eo, 8 * en)
    strs = t.read(so, sn)
    for i in range(en):
        no, tag = struct.unpack_from('<II', tab, 8 * i)
        o = no - so if m.loaded else no - (so - m.base)
        if not (0 <= o < len(strs)):
            continue
        e = strs.find(b'\0', o)
        name = strs[o:e if e >= 0 else len(strs)].decode('latin1')
        m.exports[name] = (tag & 0xF, tag >> 4)
    return m.exports


def export_addr(m, name):
    e = (m.exports or {}).get(name)
    if e is None or e[0] >= len(m.segments):
        return None
    return m.segments[e[0]][0] + e[1]


def walk(t, m, limit=512):
    """every module chained to m (next / previous words)"""
    seen = {m.base: m}
    todo = [m.next, m.prev]
    while todo and len(seen) < limit:
        a = todo.pop()
        if not a or a in seen or a & 0xFFF:
            continue
        n = read_module(t, a)
        if n is None:
            continue
        seen[a] = n
        todo += [n.next, n.prev]
    return list(seen.values())


def scan(t, regions=None, log=None, hint=()):
    """find the modules: try the hinted bases first, else probe each page's +0x80 for "CRO0" (skipping unmapped
    1 MB blocks), then follow the chain from the first one found"""
    found = {}
    for a in hint:
        m = read_module(t, a)
        if m:
            for n in walk(t, m):
                found[n.base] = n
    if found:
        return sorted(found.values(), key=lambda m: m.base)
    for lo, hi in (regions or DEFAULT_REGIONS):
        blk = lo
        while blk < hi:
            if t.try_read(blk, 4) is None and t.try_read(blk + 0x80000, 4) is None:
                blk += 0x100000
                continue
            for a in range(blk, min(blk + 0x100000, hi), 0x1000):
                if a in found:
                    continue
                w = t.try_read(a + HDR, 4)
                if w == MAGIC:
                    m = read_module(t, a)
                    if m:
                        for n in walk(t, m):
                            found[n.base] = n
                        if log:
                            log('[cro] %s at 0x%08X (+%d chained)' % (m.name, a, len(found) - 1))
                        if len(found) > 3:
                            return sorted(found.values(), key=lambda m: m.base)
            blk += 0x100000
    return sorted(found.values(), key=lambda m: m.base)


def by_name(mods):
    out = {}
    for m in mods:
        if m.name:
            out[m.name] = m
    return out
