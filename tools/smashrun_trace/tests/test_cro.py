#!/usr/bin/env python3
"""The CRO address mapping against the dump's real modules: enemy_fs.cro loaded (tests/croload.py, as the RO service
loads it) at two arbitrary bases with its .data elsewhere, then found and read back with the tracer's own code
(srtrace/cro.py) through a memory reader, as the tracer reads Azahar's RAM.

  python3 tools/smashrun_trace/tests/test_cro.py [DUMP_DIR]      (static.crs, cro/enemy_fs.cro; default $S3DS_DUMP)
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import croload                       # noqa: E402
from srtrace import cro              # noqa: E402

FAILS = []
N = [0]


def check(c, msg):
    N[0] += 1
    if not c:
        FAILS.append(msg)
        print('FAIL:', msg)


class Mem:
    """sparse page memory with the Target-like read / try_read the tracer uses"""
    def __init__(s):
        s.pages = {}

    def write(s, a, b):
        for i in range(0, len(b)):
            p = (a + i) >> 12
            pg = s.pages.get(p)
            if pg is None:
                pg = s.pages[p] = bytearray(0x1000)
            pg[(a + i) & 0xFFF] = b[i]

    def read(s, a, n):
        out = bytearray()
        for i in range(n):
            pg = s.pages.get((a + i) >> 12)
            if pg is None:
                raise IOError('unmapped 0x%08X' % (a + i))
            out.append(pg[(a + i) & 0xFFF])
        return bytes(out)

    def try_read(s, a, n):
        try:
            return s.read(a, n)
        except IOError:
            return None


def fast_write(mem, a, b):
    # page-wise copy for the big module images
    i = 0
    while i < len(b):
        p = (a + i) >> 12
        off = (a + i) & 0xFFF
        n = min(0x1000 - off, len(b) - i)
        pg = mem.pages.get(p)
        if pg is None:
            pg = mem.pages[p] = bytearray(0x1000)
        pg[off:off + n] = b[i:i + n]
        i += n


def main():
    dump = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('S3DS_DUMP')
    if not dump or not os.path.exists(os.path.join(dump, 'cro', 'enemy_fs.cro')):
        print('SKIP: no dump')
        return 0
    crs_x = open(os.path.join(dump, 'static.crs'), 'rb').read()
    ef_x = open(os.path.join(dump, 'cro', 'enemy_fs.cro'), 'rb').read()
    mp = json.load(open(os.path.join(os.path.dirname(HERE), 'srtrace', 'maps', 'enemy_fs_base.json')))
    fsegs = mp['file_segments']
    import s3ds_enemy_spec as S
    c = S.Cro(os.path.join(dump, 'cro', 'enemy_fs.cro'))
    for base, data, bss in ((0x0A3C1000, 0x0A600000, 0x0A640000), (0x00D8F000, 0x01F00000, 0x01F40000)):
        tag = '[0x%08X] ' % base
        mem = Mem()
        mem.write = lambda a, b, mem=mem: fast_write(mem, a, b)
        crs = croload.load_crs(mem, crs_x, 0x08400000)
        ef = croload.load_cro(mem, ef_x, base, data, bss, [crs])
        croload.link(mem, crs, [ef])
        check(not ef.missing, tag + 'every import resolved against static.crs (%d missing)' % len(ef.missing))
        mods = cro.by_name(cro.scan(mem, [(0x00D00000, 0x00E00000), (0x08000000, 0x08500000),
                                          (0x0A300000, 0x0A400000)]))
        check(set(mods) >= {'|static|', 'enemy_fs'}, tag + 'scan + chain found %s' % sorted(mods))
        m = mods.get('enemy_fs')
        if not m:
            continue
        check(m.base == base and m.loaded, tag + 'base / rebased header')
        check(m.segments[0][0] == base + fsegs[0][0] and m.segments[2][0] == data and m.segments[3][0] == bss,
              tag + 'segment table: text in place, .data / .bss in their buffers')
        ex = cro.read_exports(mem, m)
        k = mp['kinds']['kuribo']
        a = cro.export_addr(m, k['create_mangled'])
        check(a == base + k['create'], tag + 'the Goomba create export -> base + file offset')
        tg = ex.get(k['create_mangled'])
        check(tg and fsegs[tg[0]][0] + tg[1] == k['create'], tag + 'the export tag gives the file offset back')
        # every kind's create resolves and matches the map
        bad = [kd for kd, v in mp['kinds'].items() if cro.export_addr(m, v['create_mangled']) != base + v['create']]
        check(not bad, tag + 'every kind\'s create at base + map offset (%d bad)' % len(bad))
        # relocations: the Goomba vtable (rodata, in place) holds the run-time function addresses
        vt = k['vtable']
        rv = m.to_runtime(vt, fsegs)
        okslots = 0
        for slot, off in k['slots'].items():
            if not isinstance(off, int):
                continue
            idx = {'update': 4, 'tread': 21, 'initialize': 40, 'start': 41, 'every_frame': 55, 'capture': 13,
                   'death_state': 67, 'on_change_state': 63, 'slot69': 69}.get(slot)
            if idx is None:
                continue
            w = struct.unpack('<I', mem.read(rv + 4 * idx, 4))[0]
            check(w == base + off, tag + 'vtable slot %s -> 0x%08X (base + 0x%X)' % (slot, w, off))
            okslots += 1
        check(okslots >= 5, tag + 'vtable slots checked: %d' % okslots)
        # the state table (in .data, moved): each entry's enter / update -> base + map offset
        st = m.to_runtime(k['state_table'], fsegs)
        check(data <= st < data + fsegs[2][1], tag + 'the state table maps into the .data buffer')
        for sid, fns in k['states'].items():
            w = struct.unpack('<III', mem.read(st + 24 * int(sid), 12))
            check(w[0] == (base + fns['enter'] if fns['enter'] else 0) and
                  (w[2] == (base + fns['update'] if fns['update'] else 0)), tag + 'state %s enter / update words' % sid)
        check(m.to_file(st, fsegs) == k['state_table'], tag + 'to_file inverts to_runtime')
        # an import veneer: ldr pc, [pc, #-4] + the CRS export address
        pse = [x for x, nm in c.stubs.items() if nm == 'app::Behavior::play_se(unsigned int, bool)']
        check(pse, tag + 'the play_se veneer exists')
        if pse:
            w = struct.unpack('<II', mem.read(base + pse[0], 8))
            want = crs.exports['_ZN3app8Behavior7play_seEjb']
            check(w[0] == 0xE51FF004 and w[1] == want, tag + 'play_se veneer word = code.bin 0x%08X (got 0x%08X)'
                  % (want, w[1]))
    print('cro: %d checks, %d failed' % (N[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), '..'))
    sys.exit(main())
