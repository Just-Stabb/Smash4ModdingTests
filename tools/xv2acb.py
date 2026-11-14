#!/usr/bin/env python3
"""Dragon Ball Xenoverse 2 sound banks: CRI ACB (cue sheet, @UTF tables) + AWB (AFS2 archives): cues, their
waveforms, and the HCA files to decode.

  python3 -I tools/xv2acb.py list BANK.acb                      every cue: index, id, name, its waveforms
  python3 -I tools/xv2acb.py extract BANK.acb [BANK.awb] OUT_DIR CUE...
      each cue's waveforms as OUT_DIR/<cue name>[_<n>].hca (CUE: an index or a name)
  node tools/xv2acb_decode.mjs HCA_JS_DIR IN_DIR OUT_DIR   (HCA -> 16-bit WAV through hca.js: `npm i hca.js`;
      XV2's CMN HCAs carry a `ciph` chunk of type 0: no key)

Reading (CRI's layout, as vgmstream / VGAudio / LazyBone152's XV2-Tools read it):
- @UTF table: big-endian; "@UTF", u32 size, then u16 version, u16 rows offset, u32 strings / data offsets,
  u32 name offset, u16 columns, u16 row length, u32 rows; a column: u8 flags (0x10 name, 0x30 constant, 0x50 per
  row) | type (0-7 ints, 8 float, 0xA string, 0xB data: u32 offset, u32 size), u32 name.
- Header row: CueTable, CueNameTable, WaveformTable, SynthTable, SequenceTable, TrackTable, TrackEventTable
  (or CommandTable), AwbFile (the in-memory AFS2).
- A cue: ReferenceType 1 a waveform, 2 a synth, 3 a sequence (its TrackIndex, u16s) -> each track's
  EventIndex -> its Command blob (u16 code, u8 size, args): code 0x07D0 (noteOn) u16 type, u16 index (2 a
  synth, 1 a waveform); a synth's ReferenceItems: u16 pairs (1 a waveform, 3 a synth).
- A waveform: Streaming 0 -> MemoryAwbId in AwbFile; else StreamAwbId in the separate .awb. EncodeType 2 = HCA.
- AFS2: "AFS2", u8 version, u8 offset size, u8 id size, u8 0, u32 count, u16 alignment, u16 subkey, ids, count
  + 1 offsets (each file starts at its offset rounded up to the alignment).
"""
import os
import struct
import sys


def utf(d, o=0):
    """the rows of the @UTF table at d[o:] (column name -> value; data columns: (absolute offset, size))"""
    if d[o:o + 4] != b'@UTF':
        raise ValueError('not an @UTF table at 0x%X' % o)
    b = o + 8
    _ver, rows_off, str_off, data_off, _name, ncols, rowlen, nrows = struct.unpack_from('>HHIIIHHI', d, b)
    strs, datab = b + str_off, b + data_off

    def s(off):
        e = d.index(b'\0', strs + off)
        return d[strs + off:e].decode('utf8', 'replace')

    def val(p, ty):
        fmt = {0: '>B', 1: '>b', 2: '>H', 3: '>h', 4: '>I', 5: '>i', 6: '>Q', 7: '>q', 8: '>f'}
        if ty in fmt:
            return struct.unpack_from(fmt[ty], d, p)[0], p + struct.calcsize(fmt[ty])
        if ty == 0xA:
            return s(struct.unpack_from('>I', d, p)[0]), p + 4
        if ty == 0xB:
            off, n = struct.unpack_from('>II', d, p)
            return (datab + off, n), p + 8
        raise ValueError('column type %d' % ty)

    cols, p = [], b + 24
    for _ in range(ncols):
        fl = d[p]
        nm = struct.unpack_from('>I', d, p + 1)[0]
        p += 5
        const = None
        if fl & 0xF0 == 0x30:
            const, p = val(p, fl & 0x0F)
        cols.append((s(nm), fl & 0xF0, fl & 0x0F, const))
    rows = []
    for r in range(nrows):
        q = b + rows_off + r * rowlen
        row = {}
        for nm, st, ty, const in cols:
            if st == 0x50:
                row[nm], q = val(q, ty)
            else:
                row[nm] = const
        rows.append(row)
    return rows


def afs2(d):
    """{id: bytes} of an AFS2 (AWB) archive"""
    if d[:4] != b'AFS2':
        raise ValueError('not an AFS2 archive')
    off_size, id_size = d[5], d[6]
    n, align = struct.unpack_from('<IH', d, 8)
    p = 16
    ids = [struct.unpack_from('<H' if id_size == 2 else '<I', d, p + i * id_size)[0] for i in range(n)]
    p += n * id_size
    fmt = '<I' if off_size == 4 else '<H'
    offs = [struct.unpack_from(fmt, d, p + i * off_size)[0] for i in range(n + 1)]
    return {ids[i]: d[(offs[i] + align - 1) // align * align:offs[i + 1]] for i in range(n)}


class Acb:
    def __init__(self, data, awb=None):
        self.d = data
        self.h = utf(data)[0]

        def table(name):
            v = self.h.get(name)
            return utf(data, v[0]) if isinstance(v, tuple) and v[1] else []
        self.cues, self.wav, self.syn = table('CueTable'), table('WaveformTable'), table('SynthTable')
        self.seq, self.trk = table('SequenceTable'), table('TrackTable')
        self.tev = table('TrackEventTable') or table('CommandTable')
        self.name = {r['CueIndex']: r['CueName'] for r in table('CueNameTable')}
        mem = self.h.get('AwbFile')
        self.mem = afs2(self.blob(mem)) if isinstance(mem, tuple) and mem[1] else {}
        self.stream = afs2(awb) if awb else {}

    def blob(self, v):
        return self.d[v[0]:v[0] + v[1]]

    def u16s(self, v):
        b = self.blob(v)
        return list(struct.unpack('>%dH' % (len(b) // 2), b))

    def commands(self, v):
        b, p, out = self.blob(v), 0, []
        while p + 3 <= len(b):
            code, size = struct.unpack_from('>HB', b, p)
            out.append((code, b[p + 3:p + 3 + size]))
            p += 3 + size
        return out

    def synth_waves(self, s):
        items = self.u16s(self.syn[s]['ReferenceItems'])
        out = []
        for k in range(0, len(items) - 1, 2):
            if items[k] == 1:
                out.append(items[k + 1])
            elif items[k] == 3:
                out += self.synth_waves(items[k + 1])
        return out

    def cue_waves(self, i):
        """the waveform indices cue i plays"""
        c = self.cues[i]
        if c['ReferenceType'] == 1:
            return [c['ReferenceIndex']]
        if c['ReferenceType'] == 2:
            return self.synth_waves(c['ReferenceIndex'])
        if c['ReferenceType'] != 3:
            return []
        sq = self.seq[c['ReferenceIndex']]
        out = []
        for t in self.u16s(sq['TrackIndex'])[:sq['NumTracks']]:
            for code, arg in self.commands(self.tev[self.trk[t]['EventIndex']]['Command']):
                if code == 0x07D0 and len(arg) >= 4:
                    typ, idx = struct.unpack('>HH', arg[:4])
                    out += self.synth_waves(idx) if typ == 2 else [idx] if typ == 1 else []
        return out

    def wave_data(self, w):
        r = self.wav[w]
        return (self.stream if r['Streaming'] else self.mem).get(r['StreamAwbId'] if r['Streaming'] else
                                                                 r['MemoryAwbId'])

    def cue_index(self, key):
        if str(key).isdigit():
            return int(key)
        hit = [i for i, n in self.name.items() if n == key]
        if not hit:
            raise KeyError(key)
        return hit[0]


def main():
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == 'list':
        acb = Acb(open(a[1], 'rb').read())
        for i in range(len(acb.cues)):
            print(i, acb.cues[i]['CueId'], acb.name.get(i), [(w, acb.wav[w]['SamplingRate'], acb.wav[w]['NumSamples'])
                                                          for w in acb.cue_waves(i)])
    elif len(a) >= 4 and a[0] == 'extract':
        awb = open(a[2], 'rb').read() if a[2].lower().endswith('.awb') else None
        rest = a[3:] if awb else a[2:]
        out, cues = rest[0], rest[1:]
        acb = Acb(open(a[1], 'rb').read(), awb)
        os.makedirs(out, exist_ok=True)
        for c in cues:
            i = acb.cue_index(c)
            for n, w in enumerate(acb.cue_waves(i)):
                data = acb.wave_data(w)
                if not data or data[:3] != b'HCA':
                    print('cue %d %s: waveform %d not HCA / not there' % (i, acb.name.get(i), w))
                    continue
                fn = os.path.join(out, '%s%s.hca' % (acb.name.get(i), '' if n == 0 else '_%d' % n))
                open(fn, 'wb').write(data)
                print('cue %d %s -> %s (%d Hz, %d samples)' % (i, acb.name.get(i), fn, acb.wav[w]['SamplingRate'],
                                                               acb.wav[w]['NumSamples']))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
