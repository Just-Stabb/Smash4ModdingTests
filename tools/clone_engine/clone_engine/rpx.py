"""An RPX (Wii U executable, ELF with zlib sections) held in memory: read and write words by memory address,
resize the code section, move relocations, and save it again (sections recompressed, CRCs updated, the file packed).

Built on rpx_patch.py / rpx_compact.py (the same section handling); this keeps everything in memory so the engine
can make a "vanilla view" of an executable it patched before and apply a whole patch set in one pass.
"""
import hashlib
import struct
import zlib

from . import _paths  # noqa: F401
import rpx_compact  # noqa: E402
import rpx_patch  # noqa: E402

SHF_RPL_ZLIB = 0x08000000
SHT_RELA = 4
SHT_RPL_CRCS = 0x80000003
SHT_RPL_FILEINFO = 0x80000004
TEXT_BASE = 0x02000000


class Rpx:
    def __init__(self, path=None, data=None):
        raw = bytes(data) if data is not None else open(path, 'rb').read()
        if raw[:4] != b'\x7fELF':
            raise ValueError('not an ELF / RPX file')
        self.path = path
        self.d = bytearray(raw)
        self.shoff, = struct.unpack('>I', self.d[0x20:0x24])
        self.shentsize, shnum = struct.unpack('>HH', self.d[0x2E:0x32])
        self.secs = [list(struct.unpack('>10I', self.d[self.shoff + i * self.shentsize:
                                                       self.shoff + i * self.shentsize + 40])) for i in range(shnum)]
        self.cache = {}
        self.dirty = set()

    # ------------------------------------------------------------ sections
    def data(self, i):
        if i not in self.cache:
            self.cache[i] = rpx_patch.section_data(self.d, self.secs[i])
        return self.cache[i]

    def loadable(self):
        return [i for i, s in enumerate(self.secs) if s[1] == 1 and s[3] and s[5]]

    def locate(self, addr, n=4):
        for i in self.loadable():
            base = self.secs[i][3]
            dat = self.data(i)
            if base <= addr and addr + n <= base + len(dat):
                return i, addr - base
        raise KeyError('0x%08X is not in a loadable section' % addr)

    def has(self, addr, n=4):
        try:
            self.locate(addr, n)
            return True
        except KeyError:
            return False

    def blob(self, addr, n):
        i, o = self.locate(addr, n)
        return bytes(self.data(i)[o:o + n])

    def r32(self, addr):
        return struct.unpack('>I', self.blob(addr, 4))[0]

    def w32(self, addr, value):
        i, o = self.locate(addr)
        struct.pack_into('>I', self.data(i), o, value & 0xFFFFFFFF)
        self.dirty.add(i)

    def cstr(self, addr, limit=256):
        out = b''
        while len(out) < limit:
            c = self.blob(addr + len(out), 1)
            if c == b'\0':
                break
            out += c
        return out.decode('latin1')

    def text_index(self):
        """the code section (flags executable, at the start of the text region)"""
        cands = [i for i in self.loadable() if self.secs[i][2] & 4 and self.secs[i][3] >= TEXT_BASE
                 and self.secs[i][3] < 0x10000000]
        return max(cands, key=lambda i: len(self.data(i)))

    def text_end(self):
        i = self.text_index()
        return self.secs[i][3] + len(self.data(i))

    def set_text_end(self, end):
        """grow (zeros) or cut the code section to end at `end`"""
        i = self.text_index()
        dat = self.data(i)
        need = end - self.secs[i][3]
        if need > len(dat):
            dat += b'\0' * (need - len(dat))
        else:
            del dat[need:]
        self.dirty.add(i)

    def fileinfo_index(self):
        return next(i for i, s in enumerate(self.secs) if s[1] == SHT_RPL_FILEINFO)

    def text_region(self):
        return struct.unpack('>I', self.data(self.fileinfo_index())[4:8])[0]

    def set_text_region(self, size):
        i = self.fileinfo_index()
        struct.pack_into('>I', self.data(i), 4, size)
        self.dirty.add(i)

    # ------------------------------------------------------------ relocations
    def reloc_sections(self):
        return [i for i, s in enumerate(self.secs) if s[1] == SHT_RELA]

    def relocs_at(self, lo, hi):
        """[(section, entry offset, r_offset)] of relocations whose target is in [lo, hi)"""
        out = []
        for i in self.reloc_sections():
            dat = self.data(i)
            for o in range(0, len(dat), 12):
                off, = struct.unpack('>I', dat[o:o + 4])
                if lo <= off < hi:
                    out.append((i, o, off))
        return out

    def set_reloc_offset(self, sec, entry, value):
        struct.pack_into('>I', self.data(sec), entry, value)
        self.dirty.add(sec)

    def move_relocs(self, lo, hi, dummy):
        """rpx_patch.py's reloc:LO-HI=DUMMY; returns [(section, entry offset, old r_offset)] it changed"""
        moved = []
        for i, o, off in self.relocs_at(lo, hi):
            if off in (dummy, dummy + 2):
                continue
            self.set_reloc_offset(i, o, dummy + (off & 3))
            moved.append((i, o, off))
        return moved

    def reloc_clashes(self, words):
        """rpx_patch.py's check: patched words a relocation would still rewrite at load time"""
        by_section = {}
        for a, v in words.items():
            i, _o = self.locate(a)
            by_section.setdefault(i, (self.data(i), []))[1].append((a, v))
        for i in self.reloc_sections():
            by_section.setdefault(i, (self.data(i), []))
        # reloc_clashes compares the section's current word with the patch: give it the unpatched words
        return rpx_patch.reloc_clashes(self.d, self.secs, by_section)

    # ------------------------------------------------------------ whole image
    def memory(self):
        """{section address: bytes} of every loadable section (what the loader maps)"""
        return {self.secs[i][3]: bytes(self.data(i)) for i in self.loadable()}

    def image_digest(self):
        h = hashlib.sha1()
        for a, b in sorted(self.memory().items()):
            h.update(struct.pack('>II', a, len(b)))
            h.update(b)
        return h.hexdigest()

    def save(self, path=None):
        """the file's bytes (and written to path): dirty sections recompressed into their space or moved to the
        end of the file, CRCs updated, the file packed (rpx_compact)"""
        d = self.d
        crc_idx = next(i for i, s in enumerate(self.secs) if s[1] == SHT_RPL_CRCS)
        crc_off = self.secs[crc_idx][4]
        for idx in sorted(self.dirty):
            sec, dat = self.secs[idx], self.data(idx)
            flags, off, size = sec[2], sec[4], sec[5]
            if flags & SHF_RPL_ZLIB:
                nxt = [s[4] for s in self.secs if s[4] > off and s[5]] + ([self.shoff] if self.shoff > off else [])
                room = min(nxt) - off if nxt else size
                new = None
                for level in (6, 9):
                    comp = struct.pack('>I', len(dat)) + zlib.compress(bytes(dat), level)
                    if len(comp) <= room:
                        new = comp
                        break
                if new is None:
                    new = struct.pack('>I', len(dat)) + zlib.compress(bytes(dat), 9)
                    d[off:off + room] = b'\0' * room
                    off = (len(d) + 63) & ~63
                    d += b'\0' * (off - len(d)) + new
                    room = len(new)
                d[off:off + room] = new + b'\0' * (room - len(new))
                sec[4], sec[5] = off, len(new)
            else:
                if len(dat) != size:
                    raise ValueError('section %d is not compressed and changed size' % idx)
                d[off:off + size] = dat
            struct.pack_into('>10I', d, self.shoff + idx * self.shentsize, *sec)
            struct.pack_into('>I', d, crc_off + idx * 4, zlib.crc32(bytes(dat)) & 0xFFFFFFFF)
        self.dirty.clear()
        out = rpx_compact.compact(bytes(d))[0]
        self.d = bytearray(out)
        self.shoff, = struct.unpack('>I', self.d[0x20:0x24])
        self.secs = [list(struct.unpack('>10I', self.d[self.shoff + i * self.shentsize:
                                                       self.shoff + i * self.shentsize + 40]))
                     for i in range(len(self.secs))]
        if path:
            open(path, 'wb').write(self.d)
        return bytes(self.d)


def sha1_file(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()
