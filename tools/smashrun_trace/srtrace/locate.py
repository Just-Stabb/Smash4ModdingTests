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
# fallback scan order (user's v1.0.1 log: code.bin 0x00100000-0x01100000 has no CRO, the heap 0x08000000-0x08600000
# none either; the linear heaps were never reached): linear heaps first
SCAN_REGIONS = [(0x14000000, 0x1C000000), (0x30000000, 0x38000000), (0x08000000, 0x10000000),
                (0x01100000, 0x04000000), (0x00100000, 0x01100000)]


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
        s.use_threads = True
        s.stop_thread = None
        s.osdata_text = None

    # ------------------------------------------------------------------------------------------------ latency
    def _time(s, n=10, addr=CODE_LO):
        ts = []
        for _ in range(n):
            t0 = time.time()
            s.t.try_read(addr, 4)
            ts.append(time.time() - t0)
        ts.sort()
        return ts[len(ts) // 2]

    def measure(s, stop_state_running=False):
        """10 reads in the state the stub was in at connect (Azahar: halted, '?' -> T00), 10 in the other one, then
        stay in the faster state for the bulk reads. Returns 'halted' / 'running'."""
        s.steps.start('latency')
        first = s._time()
        if stop_state_running:
            st = s.t.halt(3.0)
            other = s._time() if st is not None else None
            run_ms, halt_ms = first, other
        else:
            s.t.resume_nowait()
            other = s._time()
            st = s.t.halt(3.0)
            run_ms, halt_ms = other, first
            if st is None:                      # no answer to the interrupt: it stays running
                halt_ms = None
        s.latency = {'halted_ms': round(halt_ms * 1000, 2) if halt_ms is not None else None,
                     'running_ms': round(run_ms * 1000, 2) if run_ms is not None else None,
                     'at_connect': 'running' if stop_state_running else 'halted'}
        if halt_ms is not None and (run_ms is None or halt_ms <= run_ms * 1.25):
            s.mode = 'halted'
        else:
            s.mode = 'running'
            s.t.resume_nowait()
        s.latency['mode'] = s.mode
        s.steps.end('%s ms halted, %s ms running -> bulk reads %s' % (
            s.latency['halted_ms'], s.latency['running_ms'], s.mode))
        return s.mode

    def ensure_halted(s):
        if s.t.running:
            return s.t.halt(3.0) is not None
        return True

    def back_to_mode(s):
        if s.mode == 'running' and not s.t.running:
            s.t.resume_nowait()

    def block(s):
        """the bulk read size: the largest multiple of a page the stub answers in one packet"""
        return max(0x1000, ((s.t.max_read or 0x1000) // 0x1000) * 0x1000)

    # ------------------------------------------------------------------------------------------------ modules
    def from_cache(s):
        mods = {}
        for base, h in s.cache.d.get('last_bases', []):
            info = s.cache.d['modules'].get(h, {})
            if not info.get('name'):
                continue
            # one read: the header holds the hash block; the segment table read only for the hooked modules
            m = s._module_known(base, info.get('name'), expect_hash=h)
            if m:
                mods[m.name] = m
        return mods

    def _module_known(s, base, name=None, expect_hash=None):
        """the module at base: header + segment table (+ the name unless known)"""
        try:
            hdr = s.t.read(base, cro.HEADER_SIZE)
        except rsp.RSPError:
            return None
        if hdr[cro.HDR:cro.HDR + 4] != cro.MAGIC:
            return None
        if expect_hash and hdr[:0x80].hex() != expect_hash:
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

    def thread_regs(s):
        """(thread id, registers) of every thread the stub lists (one Hg + one g each), the stop thread first"""
        out = []
        tids = s.t.threads() if s.use_threads else []
        if not tids:
            return [(None, s.t.read_regs())]
        for tid in tids:
            if s.t.set_thread(tid):
                try:
                    out.append((tid, s.t.read_regs()))
                except rsp.RSPError:
                    pass
        if s.stop_thread and s.stop_thread in tids:
            s.t.set_thread(s.stop_thread)
        return out or [(None, s.t.read_regs())]

    def stack_words(s, sp):
        """the words above sp: one bulk read (shorter if it would run off the mapped stack)"""
        if not sp:
            return []
        b = s.t.try_read(sp & ~3, s.block())
        if not b:
            b = s.t.try_read(sp & ~3, 0x1000 - (sp & 0xFFC))
        return [struct.unpack_from('<I', b, i)[0] for i in range(0, len(b) - 3, 4)] if b else []

    def sample_candidates(s, mods, max_cands=24):
        cands = []
        for tid, regs in s.thread_regs():
            for v in (regs.get('r15', 0), regs.get('r14', 0)):
                a = v & ~1
                if 0x00100000 <= a < 0x40000000 and not s.in_known(a, mods) and a not in cands:
                    cands.append(a)
            for w in s.stack_words(regs.get('r13', 0)):
                a = w & ~1
                if len(cands) >= max_cands:
                    break
                if not (0x00100000 <= a < 0x40000000) or s.in_known(a, mods) or a in cands or (w & 3) not in (0, 1):
                    continue
                prev = s.t.try_read(a - 4, 4)
                if prev and is_call_return(struct.unpack('<I', prev)[0]):
                    cands.append(a)
        # outside code.bin's possible range first (the update's code.bin may reach 0x01100000)
        cands.sort(key=lambda a: CODE_LO <= a < 0x01100000)
        return cands

    def walk_back(s, a, limit_pages=1536):
        """the CRO0 header at or below a: bulk reads downwards, each page's +0x80 checked locally"""
        B = s.block()
        top = a & ~0xFFF
        pages = 0
        while pages < limit_pages and top >= 0x00100000:
            start = max(0x00100000, top - B + 0x1000)
            b = s.t.try_read(start, top - start + 0x84)
            if not b:
                # the block's start is unmapped: page by page down from top until unmapped
                for p in range(top, start - 1, -0x1000):
                    w = s.t.try_read(p + cro.HDR, 4)
                    if w is None:
                        return None
                    if w == cro.MAGIC:
                        return p
                return None
            for p in range(top, start - 1, -0x1000):
                if b[p - start + cro.HDR:p - start + cro.HDR + 4] == cro.MAGIC:
                    return p
            pages += (top - start) // 0x1000 + 1
            top = start - 0x1000
        return None

    def osdata(s):
        """what qXfer:osdata:read offers (logged once; Azahar lists it, its content is unknown)"""
        if not s.t.c.features.get('qXfer:osdata:read'):
            return None
        x = s.t.xfer('osdata', '', limit=0x2000)
        s.osdata_text = (x or '')[:4000]
        return x

    def find(s, samples=20):
        mods = {}
        s.steps.start('modules: cache')
        mods = s.from_cache()
        s.steps.end('%d cached modules still loaded' % len(mods))
        if '|static|' in mods:
            s.how['modules'] = 'cache'
            if 'enemy_fs' not in mods or 'main_field' not in mods:
                s.steps.start('modules: chain (enemy_fs / main_field not cached)')
                s.chain(mods['|static|'], mods)
                s.steps.end('%d modules' % len(mods))
            return mods
        s.osdata()
        s.steps.start('modules: thread / stack samples')
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
            # let the game run ~100 ms so the threads are somewhere else next time
            s.t.resume_nowait()
            time.sleep(0.1)
        s.steps.end('%d candidates walked back, %d modules' % (tried, len(mods)))
        if '|static|' in mods:
            s.how['modules'] = 'samples'
            return mods
        s.steps.start('modules: bulk scan (fallback)')
        s.ensure_halted()
        found = s.scan(mods)
        s.steps.end('%d modules' % len(found))
        s.how['modules'] = 'scan'
        return found

    def first_mapped(s, lo, hi):
        """the first mapped page in (lo, hi] when lo is unmapped and hi mapped (binary search on page starts)"""
        while hi - lo > 0x1000:
            mid = ((lo + hi) // 2) & ~0xFFF
            if mid <= lo:
                break
            if s.t.try_read(mid, 4) is None:
                lo = mid
            else:
                hi = mid
        return hi

    def scan(s, mods):
        """bulk reads (one packet a block of pages, the +0x80 words checked locally); unmapped stretches skipped
        with growing steps (4 KB .. 256 KB), and the start of the next mapped stretch found by binary search, so a
        block that is only partly mapped is still read from its first mapped page"""
        regions = s.regions or SCAN_REGIONS
        B = s.block()
        total = sum(hi - lo for lo, hi in regions)
        done, t0, last = 0, time.time(), time.time()
        for lo, hi in regions:
            a = lo
            step = 0x1000
            while a < hi:
                b = s.t.try_read(a, min(B, hi - a))
                if b:
                    for p in range(0, len(b) - 0x83, 0x1000):
                        if b[p + cro.HDR:p + cro.HDR + 4] == cro.MAGIC:
                            m = s._module_known(a + p)
                            if m:
                                if m.name:
                                    mods[m.name] = m
                                s.chain(m, mods)
                                if '|static|' in mods:
                                    return mods
                    a += len(b) & ~0xFFF or 0x1000
                    done += len(b)
                    step = 0x1000
                else:
                    nxt = min(hi, a + step)
                    if nxt < hi and s.t.try_read(nxt, 4) is not None:
                        a = s.first_mapped(a, nxt)
                    else:
                        done += nxt - a
                        a = nxt
                        step = min(step * 2, 0x40000)
                if time.time() - last > 5:
                    last = time.time()
                    rate = done / max(1e-3, last - t0)
                    s.say('[probe] scan: 0x%08X, %d%% of the regions, at most about %.0f s left (%d packets so far)'
                          % (a, 100 * done // max(1, total), (total - done) / max(rate, 1), s.t.c.n_packets))
        return mods

    def remember(s, mods):
        s.cache.d['last_bases'] = [[m.base, getattr(m, 'hash80', None) or hash80(s.t, m.base)] for m in mods.values()
                                   if m.name in NEEDED]
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
