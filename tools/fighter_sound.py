#!/usr/bin/env python3
"""How a fighter's sounds are bound (docs/params/fighter_files.md "Sound"): read-only report.

  python3 tools/fighter_sound.py SOUND_DIR SOUNDLABELTABLE [--model DIR]
  python3 tools/fighter_sound.py --csb sound/config/commonsoundtable.csb SOUNDLABELTABLE

SOUND_DIR = fighter/<name>/sound; SOUNDLABELTABLE = sound/config/soundlabeltable.bin; DIR = a
model folder (model/body/c00) whose material_anime_face.pac names the voice mouth animations.

- *.nus3bank (little-endian 'NUS3', sections PROP BINF GRP DTON TONE JUNK PACK): BINF holds the
  bank's name and id. soundlabeltable.bin ('STB\\0', 16-byte rows: bank id, label count, offset,
  0; then each row's tone indices) gives the bank's row; a sound's ID is (row << 16) | label, as
  ACMD sound commands use it (Marth: snd_se_Marth = bank 2020 = row 0x16, IDs 0x0016xxxx;
  snd_vc_Marth = 6016 = row 0x49).
- soundseq_<Name>.sqb ('SQB\\0', little-endian): u16 version 4, u16 set id, u32 count, u32 count*4,
  u32 offset per sequence (-1 = none, from the end of the table); a sequence: u16 2, u16 n,
  u16 0, u16 ?, then n 16-byte choices (u32 sound ID or -1 = silence, u16 1, u16 weight %,
  u32 0, u16 0, u16 volume?). ACMD plays one as 0x8000 | set id << 16 | index
  (Low_Voice_Clip / PLAY_FLY_VOICE 0x80280004: Marth's set 0x28, sequence 4).
- voiceanim_<Name>.vat ('VAT\\0', little-endian): u32 2, u32 n, u32 0, then per voice label the
  hash (zlib.crc32(name, 0xFFFFFFFF)) of the mouth animation in material_anime_face.pac
  (FitMarthBodyMainVoiceS0 / S1 / S2 / L0), -1 = none.
- commonsoundtable.csb ('CSB\\0'): per fighter (in voice-bank order: Mario first) three voice
  sound IDs (label, row) and the crowd-cheer (ouen) bank's row.
"""
import os
import struct
import sys
import zlib


def sections(d):
    assert d[:4] == b'NUS3' and d[8:16] == b'BANKTOC ', 'not a nus3bank'
    count = struct.unpack('<I', d[20:24])[0]
    q = 24 + count * 8
    out = {}
    for i in range(count):
        name, size = struct.unpack('<4sI', d[24 + i * 8:32 + i * 8])
        out[name.decode()] = d[q + 8:q + 8 + size]
        q += 8 + size
    return out


def binf(d):
    b = sections(d)['BINF']
    n = b[8]
    name = b[9:9 + n - 1].decode('latin1')
    o = (9 + n + 3) & ~3
    return name, struct.unpack('<I', b[o:o + 4])[0]


def tone_count(d):
    t = sections(d).get('TONE')
    return struct.unpack('<I', t[:4])[0] if t else None


def stb_rows(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'STB\0', 'not a soundlabeltable.bin'
    n = struct.unpack('<I', d[8:12])[0]
    return [struct.unpack('<4I', d[16 + 16 * i:32 + 16 * i]) for i in range(n)]


def sqb(d):
    assert d[:4] == b'SQB\0', 'not an .sqb'
    ver, sid, cnt, tsz = struct.unpack('<HHII', d[4:16])
    offs = struct.unpack('<%di' % cnt, d[16:16 + 4 * cnt])
    base = 16 + tsz
    seqs = []
    for o in offs:
        if o < 0:
            seqs.append(None)
            continue
        p = base + o
        typ, n, _z, unk = struct.unpack('<4H', d[p:p + 8])
        seqs.append((typ, unk, [struct.unpack('<IHHIHH', d[p + 8 + 16 * i:p + 24 + 16 * i]) for i in range(n)]))
    return ver, sid, seqs


def pac_names(path):
    b = open(path, 'rb').read()
    n = struct.unpack('>I', b[8:12])[0]
    offs = struct.unpack('>%dI' % n, b[0x10:0x10 + 4 * n])
    return [b[o:b.index(b'\0', o)].decode('latin1') for o in offs]


def sid(v):
    return '-' if v == 0xFFFFFFFF else 'row %d label %d (0x%08X)' % (v >> 16, v & 0xFFFF, v)


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == '--csb':
        d = open(a[1], 'rb').read()
        rows = stb_rows(a[2])
        n = struct.unpack('<H', d[0xA:0xC])[0]
        for i in range(n):
            v = struct.unpack('<8H', d[0x1C + 0x20 * i:0x2C + 0x20 * i])
            bank = lambda r: rows[r][0] if r < len(rows) else None  # noqa: E731
            print('%2d: voices %s  ouen row %d (bank %s)' % (
                i, ', '.join('%d@row %d' % (v[k], v[k + 1]) if v[k] != 0xFFFF else '-' for k in (0, 2, 4)),
                v[7], bank(v[7])))
        return
    folder, rows = a[0], stb_rows(a[1])
    rowof = {r[0]: i for i, r in enumerate(rows)}
    faces = {}
    if '--model' in a:
        p = os.path.join(a[a.index('--model') + 1], 'material_anime_face.pac')
        if os.path.exists(p):
            for n in pac_names(p):
                b = n.rsplit('.', 1)[0]
                faces[zlib.crc32(b.encode(), 0xFFFFFFFF) & 0xFFFFFFFF] = b
    for fn in sorted(os.listdir(folder)):
        p = os.path.join(folder, fn)
        d = open(p, 'rb').read()
        if fn.endswith('.nus3bank'):
            name, bid = binf(d)
            r = rowof.get(bid)
            print('%s: BINF %s id %d, %s tones; STB %s' % (
                fn, name, bid, tone_count(d),
                ('row %d (0x%X): %d labels -> sound IDs 0x%04X0000+' % (r, r, rows[r][1], r)) if r is not None
                else 'NO ROW (the game cannot play it)'))
        elif fn.endswith('.sqb'):
            ver, setid, seqs = sqb(d)
            print('%s: version %d, set 0x%X (ACMD 0x%04X00nn), %d sequences' % (fn, ver, setid, 0x8000 | setid, len(seqs)))
            for k, s in enumerate(seqs):
                if s:
                    print('  0x%04X%04X: %s' % (0x8000 | setid, k, '; '.join('%s %d%%' % (sid(e[0]), e[2]) for e in s[2])))
        elif fn.endswith('.vat'):
            n = struct.unpack('<I', d[8:12])[0]
            hs = struct.unpack('<%dI' % n, d[16:16 + 4 * n])
            print('%s: %d voice labels' % (fn, n))
            for k, h in enumerate(hs):
                print('  label %2d: %s' % (k, '-' if h == 0xFFFFFFFF else faces.get(h, '%08X' % h)))


if __name__ == '__main__':
    main()
