"""The clone's own victory fanfare.

How the game picks it (cross_f.rpx): sound/config/bgm_fighter.fbb holds a record per fighter kind ('FBB\\0', 1, count,
then 0x14-byte records: a 16-byte name the game ignores, the BGM id), named by the executable's Capitalised-name table
in kind order (the parser 0x02A63954; kind_expand grows the table with the clones: a clone's record is its kind); the
lookup 0x02A63C50 (kind -> BGM id) feeds the results screen. A BGM id is an entry of sound/config/bgm_property.mpb
('MPB\\0', 6, count, offsets or -1, 0x74-byte entries: a 0x3C-byte name, then 14 ints: ..., loop start / end, total
length in ms and samples); its file is sound/bgm/snd_bgm_<name>.nus3bank (0x03116ECC, "%s/snd_bgm_%s.nus3bank"). The
game's own entries leave the name empty: at load 0x02A640DC fills the 593 names from the executable's (id, name) table
0x100C7380 (fanfares Z01_F_Mario ...); an entry outside that table keeps the name in the file (how added songs load).

The results screen's music after the fanfare (CRS24_VS_Result, ...) is the mode's, the same for every fighter: there is
no per-fighter results track to give a clone.

A clone's own fanfare ("own", the default): a copy of its base's fanfare bank under a name of its own
(snd_bgm_<base name>_<Cap>.nus3bank, BINF name / id of its own), a new bgm_property.mpb entry (the lowest free BGM id, a
copy of the base's entry naming the file) and its bgm_fighter.fbb record pointing at it. "wav": the same from the
creator's WAV (stereo DSP-ADPCM at the BGM rate). "share": the base's BGM id.
"""
import os
import struct

from . import _paths  # noqa: F401
from . import audio as AU
from . import roster as R

NAMES_TABLE, NAMES_COUNT = 0x100C7380, 0x251        # (BGM id, name) pairs the game fills empty entries from
BGM_RATE = 47999
FIRST_BINF = 6400                                     # new BGM bank ids: past the game's (up to 6136)


def mpb_entries(d):
    assert d[:4] == b'MPB\0', 'not a bgm_property.mpb'
    count = struct.unpack('<I', d[8:12])[0]
    offs = struct.unpack('<%dI' % count, d[12:12 + 4 * count])
    base = 12 + 4 * count
    return {i: d[base + o:base + o + 0x74] for i, o in enumerate(offs) if o != 0xFFFFFFFF}


def mpb_build(head, entries):
    count = max(max(entries) + 1, struct.unpack('<I', head[8:12])[0])
    table, body = [], b''
    for i in range(count):
        if i in entries:
            table.append(len(body))
            body += entries[i]
        else:
            table.append(0xFFFFFFFF)
    return head[:8] + struct.pack('<I%dI' % count, count, *table) + body


def bgm_name(read, entries, bgm):
    nm = entries[bgm][:0x3C].rstrip(b'\0').decode('latin1') if bgm in entries else ''
    if nm or read is None:
        return nm
    from .fighter import _rstr
    for i in range(NAMES_COUNT):
        if read(NAMES_TABLE + 8 * i) == bgm:
            return _rstr(read, read(NAMES_TABLE + 8 * i + 4))
    return ''


def own_fanfare(rec, data_dir, out_data, read=None, mode='own', wav=None, log=print):
    """gives the clone its own fanfare (see above); rec['fanfare_bgm'] = its BGM id"""
    if mode == 'share' or not rec.get('fanfare', True):
        return []
    dirs = [out_data, data_dir]
    fp, mp = R.first(dirs, 'sound/config/bgm_fighter.fbb'), R.first(dirs, 'sound/config/bgm_property.mpb')
    if not fp or not mp:
        log('fanfare: no sound/config/%s: the clone keeps its base\'s fanfare' % (
            'bgm_fighter.fbb' if not fp else 'bgm_property.mpb'))
        return []
    fbb = bytearray(open(fp, 'rb').read())
    n = struct.unpack_from('<I', fbb, 8)[0]
    if rec['kind'] >= n:
        log('fanfare: bgm_fighter.fbb has no record 0x%X' % rec['kind'])
        return []
    at = 0xC + 0x14 * rec['kind'] + 0x10
    bgm = struct.unpack_from('<I', fbb, at)[0]
    mpd = open(mp, 'rb').read()
    entries = mpb_entries(mpd)
    if rec.get('fanfare_bgm') and rec['fanfare_bgm'] in entries and bgm == rec['fanfare_bgm']:
        log('fanfare: already its own (BGM %d)' % bgm)
        return []
    name = bgm_name(read, entries, bgm)
    src = R.first(dirs, 'sound/bgm/snd_bgm_%s.nus3bank' % name) if name else None
    if bgm not in entries or (not src and mode != 'wav'):
        log('fanfare: BGM 0x%X (%s): %s; the clone keeps its base\'s fanfare' % (
            bgm, name or '?', 'no bgm_property entry' if bgm not in entries else
            'no sound/bgm/snd_bgm_%s.nus3bank in the data folder' % name))
        return []
    new_name = ('%s_%s' % (name or 'Fanfare', rec['cap']))[:0x3B]
    used = set()
    for d in dirs:
        bd = os.path.join(d, 'sound', 'bgm')
        if os.path.isdir(bd):
            for f in os.listdir(bd):
                if f.endswith('.nus3bank'):
                    try:
                        with open(os.path.join(bd, f), 'rb') as fh:
                            head = fh.read(4096)
                        if b'BINF' in head:
                            used.add(AU.Bank(open(os.path.join(bd, f), 'rb').read()).binf()[1])
                    except Exception:
                        pass
    bid = FIRST_BINF
    while bid in used:
        bid += 1
    template = src or R.first(dirs, 'sound/bgm/snd_bgm_%s.nus3bank' % 'Z01_F_Mario')
    if not template:
        log('fanfare: no BGM bank to copy the layout from; the clone keeps its base\'s fanfare')
        return []
    bank = AU.Bank(open(template, 'rb').read())
    ent = bytearray(entries[bgm])
    if mode == 'wav' and wav:
        ch = bank.tones[0]['channels'] if bank.tones and bank.tones[0] else 2
        pcm = AU.read_wav(wav, BGM_RATE, channels=max(1, ch))
        blob = AU.idsp_encode(pcm, BGM_RATE)
        bank.replace(0, blob)
        ns = len(pcm[0]) if ch > 1 else len(pcm)
        vals = list(struct.unpack('<14i', ent[0x3C:]))
        vals[12], vals[13] = int(ns * 1000 / BGM_RATE), ns
        ent[0x3C:] = struct.pack('<14i', *vals)
    # names: BINF and the tone(s) named after the base's BGM
    bank.set_binf('snd_bgm_' + new_name, bid)
    for i, t in enumerate(bank.tones):
        if t and name and t['name'] == name:
            from .audio import _parse, _entry
            h, _n, b = _parse(bank.raw[i])
            bank.raw[i] = _entry(h, new_name, b)
    free = next(i for i in range(1, 0x10000) if i not in entries)
    ent[:0x3C] = new_name.encode('latin1').ljust(0x3C, b'\0')
    entries[free] = bytes(ent)
    struct.pack_into('<I', fbb, at, free)
    out = []
    for rel, data in (('sound/bgm/snd_bgm_%s.nus3bank' % new_name, bank.data()),
                      ('sound/config/bgm_property.mpb', mpb_build(mpd, entries)),
                      ('sound/config/bgm_fighter.fbb', bytes(fbb))):
        p = os.path.join(out_data, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(data)
        out.append(p)
    rec['fanfare_bgm'] = free
    log('fanfare: its own BGM %d (%s, BINF %d), %s; bgm_fighter.fbb record 0x%X -> %d' % (
        free, new_name, bid, 'from %s' % os.path.basename(wav) if mode == 'wav' and wav else
        'a copy of %s (BGM 0x%X)' % (name, bgm), rec['kind'], free))
    return out
