"""Finding the modules and the hooked names with as few packets as possible.

Why: a Citra-style stub (Azahar's) answers about one packet per pass of the emulator's run loop while the game runs
(each pass emulates a slice of a frame), so every packet costs the game a frame; v1.0's probe scanned every 4 KB page
for a module header (tens of thousands of packets) and read static.crs's whole symbol table, and the game crawled frame
by frame for as long as it lasted (user report on v1.0.1). Halted, the stub may answer much faster: that is measured.

The steps, cheapest first:
1. latency: 10 four-byte reads as connected, then interrupt and 10 more halted; the faster state is used for the
   bulk reads (the probe prints both);
2. the cache (smashrun_trace_cache.json next to the logs): the modules last seen, each identified by the 0x80-byte
   hash block at its base (one read checks it is still there and the same file), their names, and the names the
   catalogue / maps need, resolved, per static.crs / CRO hash;
3. no cache hit: sample the halted CPU (PC, LR, a stack window: return addresses that follow a BL) for pointers into
   a CRO's code, walk back page by page (+0x80, 4 bytes a page) to its "CRO0" header, then follow the RO chain
   (next / previous) to every loaded module: about 2 packets a module;
4. still nothing after ~20 samples: the page scan of v1.0, with progress and an estimated time;
5. names: static.crs's whole named export table and strings in the largest reads the stub takes, unless the loaded
   static.crs is the one the catalogue was built from (its hash block matches: the catalogue's own addresses are used,
   no reads) or the cache has it.
"""
import json
import os
import struct
import time

from . import cro, rsp

CODE_LO = 0x00100000
CODE_HI_GUESS = 0x00D00000          # code.bin's text + rodata + data + bss end below this (base 0xC6Axxx, update ~0xCxxxxx)
NEEDED = ('|static|', 'enemy_fs', 'main_field', 'menu')
CACHE_NAME = 'smashrun_trace_cache.json'


class Steps:
    """packet / time accounting per step, for the progress lines and the probe summary"""
    def __init__(s, client, say):
        s.c = client
        s.say = say
        s.rows = []
        s.cur = None

    def start(s, name):
        s.cur = (name, s.c.n_packets, time.time())
        s.say('[probe] %s ...' % name)

    def end(s, note=''):
        if not s.cur:
            return
        name, p0, t0 = s.cur
        row = {'step': name, 'packets': s.c.n_packets - p0, 'seconds': round(time.time() - t0, 3), 'note': note}
        s.rows.append(row)
        s.say('[probe] %s: %d packets, %.1f s%s' % (name, row['packets'], row['seconds'], (' (' + note + ')') if note
                                                    else ''))
        s.cur = None
        return row


class Cache:
    def __init__(s, path):
        s.path = path
        s.d = {'version': 1, 'modules': {}, 'last_bases': [], 'symbols': {}, 'exports': {}}
        try:
            d = json.load(open(path))
            if d.get('version') == 1:
                s.d.update(d)
        except (OSError, ValueError):
            pass

    def save(s):
        try:
            json.dump(s.d, open(s.path, 'w'), indent=0, sort_keys=True)
        except OSError:
            pass


def hash80(t, base):
    b = t.try_read(base, 0x80)
    return b.hex() if b else None


def is_call_return(w):
    """the instruction before a return address: ARM BL / BLX imm (cond 1011 / 1111 101x), BLX reg, or Thumb BL"""
    if w is None:
        return False
    if (w >> 25) & 7 == 5 and (w >> 24) & 1 == 1:            # B with link (any condition) incl. BLX imm
        return True
    if w & 0x0FFFFFF0 == 0x012FFF30:                          # BLX rm
        return True
    if w & 0x0FFFF000 == 0x051F0000:                          # ldr pc via literal (veneers are reached by BL)
        return False
    hi = w >> 16
    if (hi & 0xF800) in (0xF800, 0xE800) and (w & 0xF800) == 0xF000:      # Thumb BL / BLX pair (little-endian)
        return True
    return False


class Locator:
    def __init__(s, t, say, cache_path, catalog=None, maps=None, regions=None):
        s.t = t
        s.say = say
        s.steps = Steps(t.c, say)
        s.cache = Cache(cache_path)
        s.catalog = catalog or {}
        s.maps = maps or {}
        s.regions = regions
        s.latency = {}
        s.mode = None
        s.code_hi = CODE_HI_GUESS
        s.how = {}

    # ------------------------------------------------------------------------------------------------ latency
    def _time(s, n=10, addr=CODE_LO):
        ts = []
        for _ in range(n):
            t0 = time.time()
            s.t.try_read(addr, 4)
            ts.append(time.time() - t0)
        ts.sort()
        return ts[len(ts) // 2]

    def measure(s, stop_state_running):
        """time reads as connected, then halted; stay in the faster state. Returns 'halted' / 'running'."""
        s.steps.start('latency')
        as_conn = s._time()
        st = s.t.halt(3.0)
        halted = s._time() if st is not None else None
        s.latency = {'as_connected_ms': round(as_conn * 1000, 2),
                     'halted_ms': round(halted * 1000, 2) if halted is not None else None,
                     'connected_state': 'running' if stop_state_running else 'unknown'}
        if halted is None:
            s.mode = 'running'                  # the stub didn't answer the interrupt: keep going as connected
        elif halted <= as_conn * 1.25:
            s.mode = 'halted'
        else:
            s.mode = 'running'
            s.t.resume_nowait()
        s.latency['mode'] = s.mode
        s.steps.end('%.1f ms a packet as connected, %s halted -> bulk reads %s' % (
            as_conn * 1000, ('%.1f ms' % (halted * 1000)) if halted is not None else 'no answer', s.mode))
        return s.mode

    def ensure_halted(s):
        if s.t.running:
            return s.t.halt(3.0) is not None
        return True

    def back_to_mode(s):
        if s.mode == 'running' and not s.t.running:
            s.t.resume_nowait()

    # ------------------------------------------------------------------------------------------------ modules
    def from_cache(s):
        mods = {}
        for base, h in s.cache.d.get('last_bases', []):
            if hash80(s.t, base) != h:
                continue
            info = s.cache.d['modules'].get(h, {})
            m = s._module_known(base, info.get('name'))
            if m:
                mods[m.name] = m
        return mods

    def _module_known(s, base, name=None):
        """the module at base: header + segment table (+ the name unless known)"""
        try:
            hdr = s.t.read(base, cro.HEADER_SIZE)
        except rsp.RSPError:
            return None
        if hdr[cro.HDR:cro.HDR + 4] != cro.MAGIC:
            return None
        m = cro.Module(base, hdr)
        m.hash80 = hdr[:0x80].hex()
        m.name = name
        if name is None:
            info = s.cache.d['modules'].get(m.hash80) or s.known_hash_names().get(m.hash80)
            if info:
                m.name = info if isinstance(info, str) else info.get('name')
        if m.name is None:
            na, nn = m.ptr(0xC0), m.w(0xC4)
            if 0 < nn < 0x100:
                b = s.t.try_read(na, nn)
                if b:
                    m.name = b.split(b'\0')[0].decode('latin1')
        so, sn = m.ptr(0xC8), m.w(0xCC)
        if 0 < sn <= 16 and (m.name in NEEDED or m.name is None):
            raw = s.t.try_read(so, 12 * sn)
            if raw:
                for i in range(sn):
                    a, n, ty = struct.unpack_from('<III', raw, 12 * i)
                    if not m.loaded and ty in (0, 1) and a:
                        a += base
                    m.segments.append([a, n, ty])
        if not m.segments:
            m.segments = [[base + 0x180, max(m.file_size - 0x180, 0), 0]]      # placeholder for range checks
            m.partial = True
        return m

    def known_hash_names(s):
        out = {}
        src = s.catalog.get('source', {})
        for name, h in (src.get('module_hash80') or {}).items():
            out[h] = name
        for mp in s.maps.values():
            if mp.get('hash80'):
                out[mp['hash80']] = mp['module']
        return out

    def chain(s, first, mods):
        """every module chained to `first` (2-3 packets each), stopping early once the needed ones are all known"""
        seen = {first.base: first}
        todo = [first.next, first.prev]
        while todo:
            a = todo.pop()
            if not a or a in seen or a & 0xFFF:
                continue
            m = s._module_known(a)
            if m is None:
                continue
            seen[a] = m
            if m.name:
                mods.setdefault(m.name, m)
            todo += [m.next, m.prev]
        for m in seen.values():
            if m.name:
                mods.setdefault(m.name, m)
        return mods

    def in_known(s, a, mods):
        if CODE_LO <= a < s.code_hi:
            return True
        for m in mods.values():
            lo, hi = m.range()
            if lo <= a < hi:
                return True
        return False

    def sample_candidates(s, mods, max_cands=12):
        regs = s.t.read_regs()
        pc, lr, sp = regs.get('r15', 0), regs.get('r14', 0), regs.get('r13', 0)
        cands = []
        for v in (pc, lr):
            if 0x00100000 <= v < 0x40000000 and not s.in_known(v & ~1, mods):
                cands.append(v & ~1)
        stk = s.t.try_read(sp & ~3, 0x400) if sp else None
        if stk:
            words = [struct.unpack_from('<I', stk, i)[0] for i in range(0, len(stk), 4)]
            for w in words:
                a = w & ~1
                if len(cands) >= max_cands:
                    break
                if not (0x00100000 <= a < 0x40000000) or s.in_known(a, mods) or a in cands or (w & 3) not in (0, 1):
                    continue
                prev = s.t.try_read(a - 4, 4)
                if prev and is_call_return(struct.unpack('<I', prev)[0]):
                    cands.append(a)
        return cands

    def walk_back(s, a, limit=1500):
        p = a & ~0xFFF
        for _ in range(limit):
            if p < 0x00100000:
                return None
            w = s.t.try_read(p + cro.HDR, 4)
            if w == cro.MAGIC:
                return p
            if w is None:
                return None
            p -= 0x1000
        return None

    def find(s, samples=20):
        mods = {}
        s.steps.start('modules: cache')
        mods = s.from_cache()
        s.steps.end('%d cached modules still loaded' % len(mods))
        if '|static|' in mods and all(n in mods for n in NEEDED if n != 'enemy_fs' and n != 'menu'):
            s.how['modules'] = 'cache'
            # enemy_fs may have been loaded since: check the chain cheaply only if it is missing
            if 'enemy_fs' not in mods:
                s.steps.start('modules: chain (enemy_fs not cached)')
                s.chain(mods['|static|'], mods)
                s.steps.end('%d modules' % len(mods))
            return mods
        s.steps.start('modules: CPU samples')
        tried = 0
        for i in range(samples):
            if not s.ensure_halted():
                break
            for a in s.sample_candidates(mods):
                tried += 1
                base = s.walk_back(a)
                if base:
                    m = s._module_known(base)
                    if m:
                        if m.name:
                            mods[m.name] = m
                        s.chain(m, mods)
                        break
            if '|static|' in mods:
                break
            # let the game run ~100 ms so the CPU is somewhere else next time
            s.t.resume_nowait()
            time.sleep(0.1)
        s.steps.end('%d candidates walked, %d modules' % (tried, len(mods)))
        if '|static|' in mods:
            s.how['modules'] = 'samples'
            return mods
        s.steps.start('modules: page scan (fallback)')
        s.ensure_halted()
        found = s.scan(mods)
        s.steps.end('%d modules' % len(found))
        s.how['modules'] = 'scan'
        return found

    def scan(s, mods):
        regions = s.regions or cro.DEFAULT_REGIONS
        total = sum((hi - lo) // 0x1000 for lo, hi in regions)
        done, t0, last = 0, time.time(), 0
        for lo, hi in regions:
            blk = lo
            while blk < hi:
                if s.t.try_read(blk, 4) is None and s.t.try_read(blk + 0x80000, 4) is None:
                    blk += 0x100000
                    done += 0x100
                    continue
                for a in range(blk, min(blk + 0x100000, hi), 0x1000):
                    done += 1
                    if s.t.try_read(a + cro.HDR, 4) == cro.MAGIC:
                        m = s._module_known(a)
                        if m:
                            if m.name:
                                mods[m.name] = m
                            s.chain(m, mods)
                            if '|static|' in mods:
                                return mods
                    if time.time() - last > 5:
                        last = time.time()
                        rate = done / max(1e-3, last - t0)
                        s.say('[probe] scan: %d / %d pages, about %.0f s left' % (done, total, (total - done) / rate))
                blk += 0x100000
        return mods

    def remember(s, mods):
        s.cache.d['last_bases'] = [[m.base, getattr(m, 'hash80', None) or hash80(s.t, m.base)] for m in mods.values()]
        for m in mods.values():
            h = getattr(m, 'hash80', None)
            if h and m.name:
                s.cache.d['modules'][h] = {'name': m.name, 'file_size': m.file_size}
        st = mods.get('|static|')
        if st and st.segments:
            ends = [a + n for a, n, t in st.segments if a and a < 0x04000000]
            if ends:
                s.code_hi = max(ends)
        s.cache.save()

    # ------------------------------------------------------------------------------------------------ names
    def export_tags(s, m, names, kind):
        """{mangled: (segment index, offset)} for the wanted names exported by module m"""
        h = getattr(m, 'hash80', None)
        box = s.cache.d['symbols' if kind == 'static' else 'exports']
        if h and h in box and all(n in box[h] for n in names if n):
            s.how[m.name] = 'cache'
            return {n: tuple(box[h][n]) for n in names if box[h].get(n)}
        s.steps.start('names: %s export table' % m.name)
        ex = s.read_exports_bulk(m)
        got = {n: ex[n] for n in names if n in ex}
        if h:
            box.setdefault(h, {}).update({n: list(ex[n]) if n in ex else None for n in names})
            s.cache.save()
        s.steps.end('%d of %d names found' % (len(got), len(names)))
        s.how[m.name] = 'read'
        return got

    def read_exports_bulk(s, m):
        if m.exports is not None:
            return m.exports
        return cro.read_exports(s.t, m)
