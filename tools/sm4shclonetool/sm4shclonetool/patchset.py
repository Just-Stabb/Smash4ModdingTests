"""The executable patch as data (1.5): the words the tool writes, the code cave and how to move it, for loaders that
patch the game in memory instead of a modified cross_f.rpx: the Aroma plugin (a .patch file on the SD card) and
Cemu (a graphic pack).

How the patch is made relocatable. The generators are parameterised by the code space's base (exe.generate), so the
same registry is generated at the tool's base 0x04B78000 and at probe bases (+0x10000, +0x2000, +0x20000). Every word
that differs between them depends on the base, and how it differs says how:
  +0x10000 / +0x2000 (the probe's own delta)    ADDR32: an address in the cave (data)
  +1 in the low half at +0x10000                HA16 / HI16: the high half of a cave address (lis / addis; HI16 when
                                                its low halves are ori)
  +0x2000 in the low half at +0x2000 only       LO16: the low half (addi / ori / a load's displacement)
  a branch (opcode 18) by +- the delta          REL24: a game -> cave branch (+) or a cave -> game branch (-)
Anything else fails the export. The table is then checked: applied to the base build it must give the +0x20000
build word for word, and the full addresses (each high half paired with its low halves) the +0x2000 build.

Where the cave goes:
- Aroma: in the plugin's own memory (the module area under 0x02000000, writable: the cave holds data the game writes
  at run time: the random pools, Kirby's copy table, the new characters' records). The plugin places it so that its
  base = 0x04B78000 (mod 0x10000): then only ADDR32 and HA16 words change (LO16 stay), game -> cave branches become
  absolute (`ba` / `bla`, reachable below 0x02000000 from anywhere), and each cave -> game branch goes through a
  veneer (lis / ori / mtctr / bctr, appended to the cave) whose scratch register is dead at its target
  (ppcflow.dead_at, checked on the game's code).
- Cemu: in a code cave at an address Cemu chooses (256-aligned, 0x01800000 up): every base-dependent word is written
  as an expression of the cave's symbol (_cave + offset, ha() / lo() of it), HA16 paired with its LO16 to know the
  full address.
"""
import json
import os
import struct
import zlib

from . import _paths  # noqa: F401
from . import exe as X
from . import ppcflow as F
from .rpx import Rpx, sha1_file

LINK = X.DEFAULT_BASE
ALIGN = 0x10000
PROBE_HI, PROBE_LO, PROBE_CHECK = 0x10000, 0x2000, 0x20000
MAGIC = b'S4CTPTCH'
FORMAT = 1
GAME_VERSION = 288
# Super Smash Bros. for Wii U: USA, EUR, JPN (the base titles; the code runs from the v288 update)
TITLE_IDS = (0x0005000010144F00, 0x0005000010145000, 0x0005000010110E00)
# Cemu's module checksum (RPLModule::patchCRC) of the game's v288 cross_f.rpx as Nintendo ships it
V288_CEMU_HASH = 0x63FAA900
VENEER = 16
# kinds (the plugin file's numbers)
K_ABS, K_HA16, K_ADDR32, K_REL24 = 0, 1, 2, 3
KIND_NAMES = {K_ABS: 'abs', K_HA16: 'ha16', K_ADDR32: 'addr32', K_REL24: 'rel24'}
# veneer scratch registers, in order of preference
SCRATCH = ['r12', 'r11', 'r0', 'r10', 'r9', 'r8', 'r7', 'r6', 'r5']


class PatchError(Exception):
    pass


def _bt(addr, w):
    off = w & 0x3FFFFFC
    if off & 0x2000000:
        off -= 0x4000000
    return (off if w & 2 else addr + off) & 0xFFFFFFFF


def _b(src, dst, link):
    off = (dst - src) & 0xFFFFFFFF
    if off & 0x80000000:
        off -= 1 << 32
    if not -0x2000000 <= off < 0x2000000:
        raise PatchError('branch 0x%08X -> 0x%08X out of reach' % (src, dst))
    return 0x48000000 | (off & 0x3FFFFFC) | int(link)


def _sx(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def _ha(v):
    return ((v >> 16) + ((v >> 15) & 1)) & 0xFFFF


class PatchSet:
    """sites: [{'addr', 'orig', 'new', 'kind', 'target'}] (target: the cave offset an ha16 / lo16 / addr32 / rel24 site
    points at); cave: bytes at the link base (blob_link: as the patched rpx; blob: with the veneers);
    cave_relocs: [(offset, kind)] for a base = LINK (mod ALIGN); cave_syms: {offset: (kind, target offset)} for any
    base (Cemu); veneers: [(offset, target, register)]."""

    def __init__(self):
        self.sites = []
        self.cave_relocs = []
        self.cave_syms = {}
        self.veneers = []
        self.blob = b''
        self.blob_link = b''
        self.registry = None
        self.notes = []
        self.meta = {}

    @property
    def size(self):
        return len(self.blob)


# ---------------------------------------------------------------- export
def export(in_path, reg, log=print, work=None):
    """the PatchSet of registry reg on the executable in_path (vanilla, or patched by this tool: its vanilla view)"""
    x, base, _old, notes = X.vanilla_view(in_path, force=False)
    if base != LINK:
        raise PatchError('the code space is not at 0x%08X' % LINK)
    work = work or os.path.dirname(os.path.abspath(in_path))
    view = os.path.join(work, '.ce_patchset_view.rpx')
    x.save(view)
    try:
        gens = {}
        for d in (0, PROBE_HI, PROBE_LO, PROBE_CHECK):
            gens[d] = X.generate(view, LINK + d, reg)
        vx = Rpx(view)
        ps = _classify(gens, vx)
    finally:
        if os.path.exists(view):
            os.unlink(view)
    ps.registry = reg
    ps.notes = notes
    ps.meta = {'tool': _version(), 'fighters': [f['name'] for f in reg['fighters']],
               'stages': [s['name'] for s in reg['stages']], 'source_sha1': sha1_file(in_path),
               'image': x.image_digest()}
    log('patch set: %d words in the game (%s), cave %d bytes (%d relocated words, %d veneers)'
        % (len(ps.sites), ', '.join('%s %d' % (KIND_NAMES[k], sum(1 for s in ps.sites if s['kind'] == k))
                                    for k in sorted(KIND_NAMES)), ps.size, len(ps.cave_relocs), len(ps.veneers)))
    return ps


def _version():
    from . import VERSION
    return VERSION


def _norm(g):
    b = g['base']
    cave, sites = {}, {}
    for a, w in g['words'].items():
        if b <= a < b + X.MAX_SPACE:
            cave[a - b] = w
        else:
            sites[a] = w
    return cave, sites, g['end'] - b


def _classify(gens, vx):
    c0, s0, size0 = _norm(gens[0])
    ch, sh, sizeh = _norm(gens[PROBE_HI])
    cl, sl, sizel = _norm(gens[PROBE_LO])
    cc, sc, sizec = _norm(gens[PROBE_CHECK])
    for name, c, s in (('+0x10000', ch, sh), ('+0x2000', cl, sl), ('+0x20000', cc, sc)):
        if set(c) != set(c0) or set(s) != set(s0):
            raise PatchError('the generators write other words at base %s: the patch is not relocatable' % name)
    if min(c0, default=0x4000) < 0x4000:
        raise PatchError('a generator writes the marker block')

    def kind_of(where, k, w0, wh, wl):
        dh, dl = (wh - w0) & 0xFFFFFFFF, (wl - w0) & 0xFFFFFFFF
        op = w0 >> 26
        if w0 == wh == wl:
            return None
        if op == 18 and where == 's' and dh == PROBE_HI and dl == PROBE_LO:
            return 'rel24_to_cave'
        if op == 18 and where == 'c' and dh == (-PROBE_HI) & 0xFFFFFFFF and dl == (-PROBE_LO) & 0xFFFFFFFF:
            return 'rel24_to_game'
        if dh == PROBE_HI and dl == PROBE_LO:
            return 'addr32'
        if dh == 1 and (w0 ^ wl) >> 16 == 0 and ((wl - w0) & 0xFFFF) in (0, 1):
            return 'ha16'
        if dh == 0 and (w0 ^ wl) >> 16 == 0 and ((wl - w0) & 0xFFFF) == PROBE_LO:
            return 'lo16'
        raise PatchError('%s word 0x%X: 0x%08X / 0x%08X / 0x%08X at the probe bases: not a known relocation'
                         % ('cave' if where == 'c' else 'game', k, w0, wh, wl))
    kinds = {}
    for k in c0:
        t = kind_of('c', k, c0[k], ch[k], cl[k])
        if t:
            kinds[('c', k)] = t
    for k in s0:
        t = kind_of('s', k, s0[k], sh[k], sl[k])
        if t:
            kinds[('s', k)] = t
    # the cave: up to its last written word (the rest of the patched rpx's code space is never read)
    size = (max(c0) + 4 + 0xF) & ~0xF if c0 else 0
    # the link image of the cave (zeros where nothing is written), and of the sites
    cave = bytearray(size)
    for off, w in c0.items():
        struct.pack_into('>I', cave, off, w)

    def word(key):
        where, k = key
        if where == 'c':
            return struct.unpack_from('>I', cave, k)[0] if 0 <= k < size else None
        if k in s0:
            return s0[k]
        try:
            return vx.r32(k)
        except KeyError:
            return None
    # full targets: pair every ha16 with the lo16 words that use its register
    targets = {}
    for key, t in sorted(list(kinds.items())):
        if t != 'ha16':
            continue
        w = word(key)
        rd = (w >> 21) & 31
        hi = w & 0xFFFF
        found, unsigned = [], []
        for i in range(1, 24):
            q = (key[0], key[1] + 4 * i)
            wq = word(q)
            if wq is None:
                break
            ins = F.decode(wq, q[1])
            if kinds.get(q) == 'lo16' and _src(wq) == rd:
                lo = wq & 0xFFFF
                tgt = ((hi << 16) + (lo if wq >> 26 in (24, 25) else _sx(lo))) & 0xFFFFFFFF
                found.append(tgt)
                unsigned.append(wq >> 26 in (24, 25))
                targets.setdefault(q, tgt)
            if 'r%d' % rd in ins[2] or ins[0] not in ('op',):
                break
        if not found:
            raise PatchError('the high half at %s 0x%X has no low half after it' % key)
        targets[key] = found[0]
        if all(unsigned):                       # lis / ori: the plain high half
            kinds[key] = 'hi16'
        elif any(unsigned):
            raise PatchError('the high half at %s 0x%X has both signed and unsigned low halves' % key)
        if len({t_ >> 8 for t_ in found}) > 1:
            targets[key + ('multi',)] = found
    for key, t in kinds.items():
        if t == 'lo16' and key not in targets:
            # a low half without its high half here: its offset is known modulo 0x10000, all a low half needs
            targets[key] = LINK + ((word(key) - LINK) & 0xFFFF)
        elif t == 'addr32':
            targets[key] = word(key)
        elif t in ('rel24_to_cave', 'rel24_to_game'):
            targets[key] = _bt(key[1] + (LINK if key[0] == 'c' else 0), word(key))
    ps = PatchSet()
    # the check: the relocation table predicts the +0x20000 build
    bad = []
    for key, t in kinds.items():
        where, k = key
        w0 = word(key)
        want = cc[k] if where == 'c' else sc[k]
        got = _relocate(w0, t, PROBE_CHECK, k + (LINK if where == 'c' else 0), PROBE_CHECK if where == 'c' else 0)
        if got != want:
            bad.append('%s 0x%X: 0x%08X predicted, 0x%08X built' % (where, k, got, want))
        # the full targets (Cemu's expressions) predict the +0x2000 build
        wl = cl[k] if where == 'c' else sl[k]
        tg = targets[key] + PROBE_LO
        if t == 'ha16':
            lo_want = (w0 & 0xFFFF0000) | _ha(tg)
        elif t == 'hi16':
            lo_want = (w0 & 0xFFFF0000) | ((tg >> 16) & 0xFFFF)
        elif t == 'lo16':
            lo_want = (w0 & 0xFFFF0000) | (tg & 0xFFFF)
        elif t == 'addr32':
            lo_want = tg & 0xFFFFFFFF
        else:
            lo_want = wl
        if lo_want != wl:
            bad.append('%s 0x%X: 0x%08X from its target, 0x%08X built at +0x%X' % (where, k, lo_want, wl, PROBE_LO))
    for name, c, s in (('+0x10000', ch, sh), ('+0x2000', cl, sl), ('+0x20000', cc, sc)):
        bad += ['%s 0x%X changes at %s' % (w, k, name) for w, tag, d0, d in (('cave', 'c', c0, c), ('game', 's', s0, s))
                for k in d0 if (tag, k) not in kinds and d0[k] != d[k]]
    if bad:
        raise PatchError('the relocation table does not predict the generators: ' + '; '.join(bad[:5]))
    ps.written = sorted(c0)
    ps.end_link = LINK + size0
    ps.blob_link = bytes(cave)
    # veneers for the cave -> game branches (appended at the end of the cave, 16-byte aligned)
    vstart = (size + 0xF) & ~0xF
    blob = bytearray(cave) + bytes(vstart - size)
    vby = {}
    def lread(a):                      # the patched image at the link base: what runs, but for the veneers
        if LINK <= a < LINK + size:
            return struct.unpack_from('>I', cave, a - LINK)[0]
        return s0[a] if a in s0 else vx.r32(a)

    def into_cave(t):
        return LINK <= t < LINK + size
    for key in sorted(k for k, t in kinds.items() if t == 'rel24_to_game'):
        off = key[1]
        w = word(key)
        tgt = targets[key]
        link = w & 1
        if link:
            # a call: the veneer runs before the callee, which leaves r0 / r11 / r12 / ctr undefined anyway; what the
            # cave code does after the call must not need them (it can't, by the ABI; checked)
            regs = [r for r in SCRATCH if r in F.CALL_CLOBBERS]
            dead = F.dead_at(lread, LINK + off + 4, regs + ['ctr'], follow=into_cave)
        else:
            regs = SCRATCH
            dead = F.dead_at(lread, tgt, regs + ['ctr'], follow=into_cave)
        use = next((r for r in regs if r in dead), None)
        if use is None or 'ctr' not in dead:
            raise PatchError('no free register for the far %s from cave 0x%X to 0x%08X (dead: %s)'
                             % ('call' if link else 'jump', off, tgt, ', '.join(dead) or 'none'))
        vk = (tgt, use)
        if vk not in vby:
            n = int(use[1:])
            at = len(blob)
            for v in (0x3C000000 | (n << 21) | (tgt >> 16),                     # lis rN, tgt@h
                      0x60000000 | (n << 21) | (n << 16) | (tgt & 0xFFFF),      # ori rN, rN, tgt@l
                      0x7C0903A6 | (n << 21),                                   # mtctr rN
                      0x4E800420):                                              # bctr
                blob += struct.pack('>I', v)
            vby[vk] = at
            ps.veneers.append((at, tgt, use))
        struct.pack_into('>I', blob, off, _b(off, vby[vk], link))
    ps.blob = bytes(blob)
    # relocations of the cave (plugin: base = LINK mod ALIGN) and its symbolic words (Cemu: any base)
    for key, t in sorted(kinds.items()):
        where, k = key
        if where != 'c' or t == 'rel24_to_game':
            continue
        if t in ('ha16', 'hi16'):
            ps.cave_relocs.append((k, K_HA16))
        elif t == 'addr32':
            ps.cave_relocs.append((k, K_ADDR32))
        ps.cave_syms[k] = (t, (targets[key] - LINK) & 0xFFFFFFFF, key + ('multi',) in targets)
    for a in sorted(s0):
        t = kinds.get(('s', a))
        rec = {'addr': a, 'orig': vx.r32(a), 'new': s0[a],
               'kind': {None: K_ABS, 'lo16': K_ABS, 'ha16': K_HA16, 'hi16': K_HA16, 'addr32': K_ADDR32,
                        'rel24_to_cave': K_REL24}[t],
               'sym': t}
        if t:
            rec['target'] = (targets[('s', a)] - LINK) & 0xFFFFFFFF
            rec['multi'] = ('s', a, 'multi') in targets
        ps.sites.append(rec)
    ps.written = ps.written + [o for at, _t, _r in ps.veneers for o in range(at, at + VENEER, 4)]
    return ps


def _src(w):
    """the register a low half is added to: rS for ori / oris, rA otherwise"""
    return (w >> 21) & 31 if w >> 26 in (24, 25) else (w >> 16) & 31


def _relocate(w, t, delta, addr, addr_delta):
    """word w of kind t at addr, the cave moved by delta (the word itself by addr_delta), as relative branches stay"""
    if t == 'addr32':
        return (w + delta) & 0xFFFFFFFF
    if t in ('ha16', 'hi16'):
        return (w & 0xFFFF0000) | ((w + (delta >> 16)) & 0xFFFF) if delta % ALIGN == 0 else None
    if t == 'lo16':
        return (w & 0xFFFF0000) | ((w + delta) & 0xFFFF)
    if t in ('rel24_to_cave', 'rel24_to_game'):
        tgt = _bt(addr, w) + (delta if t == 'rel24_to_cave' else 0)
        return _b(addr + addr_delta, tgt & 0xFFFFFFFF, w & 1)
    raise ValueError(t)


# ---------------------------------------------------------------- applying (the plugin's algorithm, in Python)
def apply(ps, read, write, base):
    """apply ps into memory through read(addr) -> word / write(addr, word) with the cave at base (= LINK mod ALIGN),
    as the Aroma plugin does: verify every original, copy the cave, relocate it, write the hooks. Returns the words
    written outside the cave {addr: word}. Raises PatchError (nothing written) on a mismatch."""
    if (base - LINK) % ALIGN:
        raise PatchError('the cave base 0x%08X is not 0x%04X modulo 0x%X' % (base, LINK % ALIGN, ALIGN))
    delta = (base - LINK) & 0xFFFFFFFF
    bad = [s for s in ps.sites if read(s['addr']) != s['orig']]
    if bad:
        raise PatchError('%d word(s) are not the game\'s (first 0x%08X: 0x%08X, expected 0x%08X)'
                         % (len(bad), bad[0]['addr'], read(bad[0]['addr']), bad[0]['orig']))
    blob = bytearray(ps.blob)
    for off, k in ps.cave_relocs:
        w = struct.unpack_from('>I', blob, off)[0]
        struct.pack_into('>I', blob, off, site_word(w, k, delta, base + off))
    for i in range(0, len(blob), 4):
        write(base + i, struct.unpack_from('>I', blob, i)[0])
    out = {}
    for s in ps.sites:
        out[s['addr']] = site_word(s['new'], s['kind'], delta, s['addr'])
    for a, w in out.items():
        write(a, w)
    return out


def site_word(w, kind, delta, addr):
    """the plugin's relocation of one word (kinds K_*); delta = base - LINK (a multiple of ALIGN)"""
    if kind == K_ABS:
        return w
    if kind == K_HA16:
        return (w & 0xFFFF0000) | ((w + (delta >> 16)) & 0xFFFF)
    if kind == K_ADDR32:
        return (w + delta) & 0xFFFFFFFF
    if kind == K_REL24:
        tgt = (_bt(addr, w) + delta) & 0xFFFFFFFF
        if tgt < 0x02000000:
            return (w & 0xFC000001) | 2 | tgt                   # ba / bla: absolute, reachable from anywhere
        return _b(addr, tgt, w & 1)
    raise ValueError(kind)


# ---------------------------------------------------------------- the plugin's file
def plugin_bytes(ps):
    """the .patch file the Aroma plugin reads (big-endian; layout in aroma/README.md)"""
    meta = zlib.compress(json.dumps(ps.meta, sort_keys=True).encode(), 9)
    head = MAGIC + struct.pack('>IIIIIIIII', FORMAT, GAME_VERSION, LINK, ALIGN, ps.size, len(ps.sites),
                               len(ps.cave_relocs), len(TITLE_IDS), len(meta))
    out = bytearray(head)
    for t in TITLE_IDS:
        out += struct.pack('>Q', t)
    out += meta + bytes(-len(meta) % 4)
    for s in ps.sites:
        out += struct.pack('>IIII', s['addr'], s['orig'], s['new'], s['kind'])
    for off, k in ps.cave_relocs:
        out += struct.pack('>I', off | (k << 28))
    out += ps.blob
    out += struct.pack('>I', zlib.crc32(bytes(out)) & 0xFFFFFFFF)
    return bytes(out)


def read_plugin(data):
    """parse a .patch file back into a PatchSet (the plugin's parser, in Python)"""
    if data[:8] != MAGIC:
        raise PatchError('not a Sm4shCloneTool patch file')
    crc, = struct.unpack('>I', data[-4:])
    if zlib.crc32(data[:-4]) & 0xFFFFFFFF != crc:
        raise PatchError('the patch file is damaged (CRC)')
    fmt, ver, link, align, size, nsites, nrel, ntitles, nmeta = struct.unpack_from('>9I', data, 8)
    if fmt != FORMAT or link != LINK or align != ALIGN:
        raise PatchError('unsupported patch file (format %d)' % fmt)
    o = 8 + 36
    titles = struct.unpack_from('>%dQ' % ntitles, data, o)
    o += 8 * ntitles
    ps = PatchSet()
    ps.meta = json.loads(zlib.decompress(data[o:o + nmeta]).decode())
    o += nmeta + (-nmeta % 4)
    for i in range(nsites):
        a, orig, new, k = struct.unpack_from('>4I', data, o + 16 * i)
        ps.sites.append({'addr': a, 'orig': orig, 'new': new, 'kind': k})
    o += 16 * nsites
    for i in range(nrel):
        v, = struct.unpack_from('>I', data, o + 4 * i)
        ps.cave_relocs.append((v & 0x0FFFFFFF, v >> 28))
    o += 4 * nrel
    ps.blob = data[o:o + size]
    if len(ps.blob) != size or o + size + 4 != len(data):
        raise PatchError('the patch file is truncated')
    ps.titles, ps.version = titles, ver
    return ps


# ---------------------------------------------------------------- Cemu
def cemu_hash(path):
    """Cemu's module checksum of an RPX (RPLModule::patchCRC, Cemu's RPLLoader_BeginCemuhookCRC; what a graphic
    pack's moduleMatches lists): CRC-32 over
    the header indices, then per section its name offset, type, flags, address, size (decompressed), alignment
    (little-endian words) and its decompressed data"""
    x = Rpx(path)
    d = x.d
    shstrndx, = struct.unpack('>H', d[0x32:0x34])
    sym = next((i for i, s in enumerate(x.secs) if s[1] == 2), -1)
    stra = next((i for i, s in enumerate(x.secs) if s[1] == 3 and i != shstrndx), -1)
    c = zlib.crc32(b'\x7fRPX')
    c = zlib.crc32(struct.pack('<iiii', len(x.secs), sym, stra, shstrndx), c)
    for s in x.secs:
        name, typ, flags, addr, off, size = s[:6]
        align = s[8]
        if typ == 8:
            raw, n = None, size
        elif flags & 0x08000000:
            n, = struct.unpack('>I', d[off:off + 4])
            raw = zlib.decompress(bytes(d[off + 4:off + size]))
        else:
            raw, n = bytes(d[off:off + size]), size
        c = zlib.crc32(struct.pack('<6I', name, typ, flags, addr, n, align), c)
        if raw:
            c = zlib.crc32(raw, c)
    return c & 0xFFFFFFFF


def cemu_expr(w, sym, target):
    """the expression of a base-dependent word (sym: its kind; target: the cave offset it points at)"""
    if sym == 'addr32':
        return '_cave + 0x%X' % target
    if sym == 'ha16':
        return '0x%08X + ha(_cave + 0x%X)' % (w & 0xFFFF0000, target)
    if sym == 'hi16':
        return '0x%08X + hi(_cave + 0x%X)' % (w & 0xFFFF0000, target)
    if sym == 'lo16':
        return '0x%08X + lo(_cave + 0x%X)' % (w & 0xFFFF0000, target)
    if sym == 'rel24_to_cave':
        return '0x%08X + _cave + 0x%X' % ((w & 0xFC000001) | 2, target)      # ba / bla
    raise ValueError(sym)


def cemu_patches(ps, hashes, group='Sm4shCloneTool_v288'):
    """patches.txt (Cemuhook format, which Cemu reads): the cave at cave-relative addresses, the game's words at theirs.
    Cemu places the cave (256-aligned) and resolves _cave; the veneers make the cave -> game branches absolute."""
    if any(m for _t, _o, m in ps.cave_syms.values()) or any(s.get('multi') for s in ps.sites):
        multi = True
    else:
        multi = False
    lines = ['; Sm4shCloneTool %s: the clone patch for Super Smash Bros. for Wii U v288 (cross_f.rpx),' % ps.meta['tool'],
             '; as a Cemu graphic pack patch. Clones: %s; stages: %s.' % (', '.join(ps.meta['fighters']) or '-',
                                                                       ', '.join(ps.meta['stages']) or '-'),
             '; The code cave is the tool\'s code space (0x%08X in its patched executable), placed by Cemu;' % LINK,
             '; every word that depends on where it is uses _cave. Do not edit by hand: rebuild with the tool.',
             '', '[%s]' % group, 'moduleMatches = ' + ', '.join('0x%08X' % h for h in hashes),
             'codeCaveSize = 0x%X' % ps.size, '_cave = 0x00000000', '']
    blob = ps.blob
    for off in ps.written:                    # every word a generator wrote (zeros too: Cemu's cave memory may
        w = struct.unpack_from('>I', blob, off)[0]     # hold an earlier game's data); padding is never read
        s = ps.cave_syms.get(off)
        if s:
            lines.append('0x%08X = .int %s' % (off, cemu_expr(w, s[0], s[1])))
        else:
            lines.append('0x%08X = .int 0x%08X' % (off, w))
    lines.append('')
    for s in ps.sites:
        if s.get('sym'):
            lines.append('0x%08X = .int %s' % (s['addr'], cemu_expr(s['new'], s['sym'], s['target'])))
        else:
            lines.append('0x%08X = .int 0x%08X' % (s['addr'], s['new']))
    return '\n'.join(lines) + '\n', multi


def cemu_rules(ps, name):
    desc = ('Sm4shCloneTool %s: new fighter / stage slots (%s) without a modified cross_f.rpx. Needs the game\'s '
            'v288 update and the clones\' data files.' % (ps.meta['tool'], ', '.join(ps.meta['fighters'] +
                                                                                   ps.meta['stages'])))
    return '\n'.join(['[Definition]', 'titleIds = ' + ','.join('%016X' % t for t in TITLE_IDS),
                      'name = %s' % name, 'path = "Super Smash Bros. for Wii U/Mods/%s"' % name,
                      'description = %s' % desc.replace('\n', ' '), 'version = 6', '']) + '\n'


# ---------------------------------------------------------------- the patch file in an emulated image
class Image:
    """a sparse memory image (words) over an Rpx's sections, for apply() in the tests"""

    def __init__(self, x):
        self.x = x
        self.extra = {}

    def read(self, a):
        if a in self.extra:
            return self.extra[a]
        return self.x.r32(a)

    def write(self, a, w):
        self.extra[a] = w & 0xFFFFFFFF
