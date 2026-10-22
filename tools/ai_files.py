#!/usr/bin/env python3
"""A fighter's CPU files, fighter/<name>/script/ai/ (docs/params/fighter_files.md "AI").

  python3 tools/ai_files.py attack_data.bin [--mtable MTABLE]      the attack ranges (ATKD)
  python3 tools/ai_files.py attack_data.bin --json OUT.json
  python3 tools/ai_files.py --atkd IN.json OUT.bin                  write attack_data.bin
  python3 tools/ai_files.py script.bin                              routines and their commands
  python3 tools/ai_files.py param.bin                               AIPD header and section table
  python3 tools/ai_files.py --selftest AI_DIR...                    byte-exact round trips

attack_data.bin ('ATKD', big-endian): u32 entry count, u32 first own motion kind (0x211, the
common motion count), u32 own motion count (the fighter's motion count - 0x211); then 0x18-byte
entries: u16 motion kind, u16 0, u16 first / last frame the move hits, f32 x min, x max, y min,
y max (the area the hitboxes cover, fighter facing right, from its position). The CPU only
knows the attacks listed here (read at 0x02DFC824: entries go in a table by motion kind,
< 0x611).

script.bin (big-endian): u32 0, u32 routine count, u32 0, u32 0, u32 offset per routine; a
routine: u32 id (e.g. 0x1130, 0x4010, 0x6039: they replace the common script's routine of the
same id, fighter/common/script/ai/script.bin), u32 code offset (0x10), u32 constants offset,
u32 flags?; code = commands (u8 op, u8 arg count, u16 size, u32 args), the constants (floats)
after it. Arguments 0x1000+n look like variables, 0x2000+n constants n. Ops are not named.

param.bin / param_nfp.bin ('AIPD', version 15, checked by 0x02DFB4D8; nfp = the amiibo version):
0x10-byte header, 0x158 bytes of per-action flags (read by direct offsets, e.g. +0x108 + n),
72 u32 section offsets at 0x168, then the sections. Either file missing or invalid -> the game
uses fighter/common/script/ai/param.bin. Kept byte for byte here (no editor).
"""
import json
import struct
import sys
import zlib

ATKD_KEYS = ('motion', 'unk', 'start', 'end', 'x_min', 'x_max', 'y_min', 'y_max')


# ---------------------------------------------------------------- ATKD

def atkd_read(d):
    assert d[:4] == b'ATKD', 'not an attack_data.bin'
    n, first, own = struct.unpack('>3I', d[4:16])
    rows = [dict(zip(ATKD_KEYS, struct.unpack('>4H4f', d[16 + 24 * i:40 + 24 * i]))) for i in range(n)]
    assert len(d) == 16 + 24 * n, 'trailing data'
    return {'first_own_motion': first, 'own_motions': own, 'attacks': rows}


def atkd_write(a):
    out = b'ATKD' + struct.pack('>3I', len(a['attacks']), a['first_own_motion'], a['own_motions'])
    for r in a['attacks']:
        out += struct.pack('>4H4f', *(int(r[k]) for k in ATKD_KEYS[:4]), *(float(r[k]) for k in ATKD_KEYS[4:]))
    return out


# ---------------------------------------------------------------- script.bin

def script_read(d):
    z0, n, z1, z2 = struct.unpack('>4I', d[:16])
    offs = list(struct.unpack('>%dI' % n, d[16:16 + 4 * n]))
    routines = []
    for k, o in enumerate(offs):
        end = offs[k + 1] if k + 1 < n else len(d)
        rid, code, consts, flags = struct.unpack('>4I', d[o:o + 16])
        cmds = []
        p = o + code
        while p < o + consts:
            op, argc, size = struct.unpack('>BBH', d[p:p + 4])
            assert size >= 4 and (size - 4) % 4 == 0 and (size - 4) // 4 == argc, 'bad command at 0x%X' % p
            cmds.append((op, list(struct.unpack('>%dI' % argc, d[p + 4:p + size]))))
            p += size
        assert p == o + consts, 'code runs past the constants'
        routines.append({'id': rid, 'code': code, 'flags': flags, 'commands': cmds,
                         'constants': d[o + consts:end]})
    return {'head': (z0, z1, z2), 'pad': d[16 + 4 * n:offs[0]] if offs else b'', 'routines': routines}


def script_write(s):
    z0, z1, z2 = s['head']
    rs = s['routines']
    body = b''
    offs = []
    base = 16 + 4 * len(rs) + len(s['pad'])
    for r in rs:
        code = b''.join(struct.pack('>BBH', op, len(args), 4 + 4 * len(args)) + struct.pack('>%dI' % len(args), *args)
                        for op, args in r['commands'])
        offs.append(base + len(body))
        body += struct.pack('>4I', r['id'], r['code'], r['code'] + len(code), r['flags']) + \
            b'\0' * (r['code'] - 16) + code + r['constants']
    return struct.pack('>4I', z0, len(rs), z1, z2) + struct.pack('>%dI' % len(rs), *offs) + s['pad'] + body


def floats(b):
    n = len(b) // 4
    return [round(x, 4) for x in struct.unpack('>%df' % n, b[:4 * n])]


# ---------------------------------------------------------------- AIPD

def aipd_info(d):
    assert d[:4] == b'AIPD', 'not an AIPD file'
    ver = struct.unpack('>I', d[4:8])[0]
    offs = struct.unpack('>72I', d[0x168:0x168 + 72 * 4])
    return ver, offs


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == '--atkd':
        open(a[2], 'wb').write(atkd_write(json.load(open(a[1]))))
        print('wrote', a[2])
        return
    if a[0] == '--selftest':
        import os
        n = 0
        for folder in a[1:]:
            p = os.path.join(folder, 'attack_data.bin')
            d = open(p, 'rb').read()
            assert atkd_write(json.loads(json.dumps(atkd_read(d)))) == d, p
            p = os.path.join(folder, 'script.bin')
            d = open(p, 'rb').read()
            assert script_write(script_read(d)) == d, p
            for f in ('param.bin', 'param_nfp.bin'):
                ver, offs = aipd_info(open(os.path.join(folder, f), 'rb').read())
                assert ver == 15, f
            n += 1
        print('%d AI folders round-trip byte for byte' % n)
        return
    d = open(a[0], 'rb').read()
    if d[:4] == b'ATKD':
        at = atkd_read(d)
        if '--json' in a:
            json.dump(at, open(a[a.index('--json') + 1], 'w'), indent=1)
            print('wrote', a[a.index('--json') + 1])
            return
        names = {}
        if '--mtable' in a:
            mt = open(a[a.index('--mtable') + 1], 'rb').read()
            hashes = struct.unpack('>%dI' % (len(mt) // 4), mt)
            try:
                import mtable
                voc, _ = mtable.vocabulary()
            except ImportError:
                voc = {}
            names = {i: voc.get(h, '%08X' % h) for i, h in enumerate(hashes)}
        print('ATKD: %d attacks, own motions 0x%X + %d' % (len(at['attacks']), at['first_own_motion'], at['own_motions']))
        for r in at['attacks']:
            print('  0x%03X %-22s frames %3d-%-3d  x %6.1f .. %-6.1f y %6.1f .. %-6.1f%s' % (
                r['motion'], names.get(r['motion'], ''), r['start'], r['end'], r['x_min'], r['x_max'],
                r['y_min'], r['y_max'], ('  unk %d' % r['unk']) if r['unk'] else ''))
    elif d[:4] == b'AIPD':
        ver, offs = aipd_info(d)
        print('AIPD version %d, %d bytes, crc %08X' % (ver, len(d), zlib.crc32(d) & 0xFFFFFFFF))
        print('flags 0x10-0x168:', d[0x10:0x168].hex())
        ends = list(offs[1:]) + [len(d)]
        for k, (o, e) in enumerate(zip(offs, ends)):
            print('  section %2d at 0x%04X, 0x%X bytes' % (k, o, e - o))
    else:
        s = script_read(d)
        print('AI script: %d routines' % len(s['routines']))
        for r in s['routines']:
            print('routine 0x%04X (flags 0x%X): %d commands, constants %s' % (
                r['id'], r['flags'], len(r['commands']), floats(r['constants'])))
            for op, args in r['commands']:
                print('    %02X %s' % (op, ' '.join('0x%X' % x for x in args)))


if __name__ == '__main__':
    import os  # noqa: E402
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
