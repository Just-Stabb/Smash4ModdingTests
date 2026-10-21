#!/usr/bin/env python3
"""Minecraft World's sounds: Ultimate's stage sound bank (se_stage_pickel_world) in NewStage01's.

  python3 tools/minecraft_sound.py ULT.nus3audio NEWSTAGE01_sound.nus3bank ONESHOT.nus3bank \\
      soundlabeltable.bin OUT_DIR

ULT.nus3audio: Ultimate's sound/bank/stage/se_stage_pickel_world.nus3audio (the user's
sound-ssbu.zip): 'NMOF' names, 'ADOF' (offset, size) a sound, the data Namco IDSP (DSP ADPCM,
big-endian header), as Smash 4's: copied as they are. 48 kHz mono.

NEWSTAGE01_sound.nus3bank: the slot's own bank (a copy of Battlefield's, BINF 3051: 7 tones,
waterfall01_loop with no data and amb01-06_loop, which its sound/sequence.bin plays through the
music player at frames 0 / 3120 / 5040 / 5760, as Battlefield's day turns): kept, its ambient
loops made silent (a short silent loop; the sequence file stays Battlefield's own, so it is
known to load), then SOUNDS after them, each variant a tone (TONE entries as a one-shot of
ONESHOT.nus3bank's, e.g. sound/se/snd_se_enemy_Metalface.nus3bank: loop flag 0; in the stage's
group as Battlefield's, volume VOLUME dB).

soundlabeltable.bin (sound/config, 'STB\\0': 3252 rows of (bank id, sounds, offset, 0), then the
rows' sounds' tone indices): a sound's ID is (row << 16) | its index in the row; NewStage01's bank
is row ROW (1147, bank 3051), grown from 7 sounds to all of the bank's tones.

Writes OUT_DIR/sound.nus3bank, OUT_DIR/soundlabeltable.bin; tools/monster_roll_cave.py plays the
sounds (tone index: tone_index()).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import minecraft_music as mm  # noqa: E402

ROW = 1147                      # soundlabeltable row of NewStage01's (Battlefield's) bank
BANK_ID = 3051
FIRST = 7                       # Battlefield's tones kept before ours
# (sound, variants): Ultimate's se_stage_pickel_world_<sound><n> (n from 1; one without a number:
# no variants); its block sounds are left out (the port's blocks don't break)
SOUNDS = [('cow_vo', 6), ('chicken_vo', 6), ('sheep_vo', 6), ('villager_vo', 6), ('spider_vo', 6),
          ('zombi_vo', 6), ('zombi_burn', 2), ('zombi_death', 0), ('bone_move', 4), ('enderman_portal', 3),
          ('door_open', 0), ('door_close', 0)]
VOLUME = 0.0                    # dB (Smash 4's one-shots: mostly 0)
STAGE_GROUP = 0x272             # Battlefield's tones' (the one-shot template's 0x271: an enemy's)
RATE = 48000
SILENT = 4800                   # samples of the silent loop


def tone_index(sound):
    """(first tone index, variants (1 if none)) of a SOUNDS sound"""
    i = FIRST
    for s, n in SOUNDS:
        if s == sound:
            return i, max(n, 1)
        i += max(n, 1)
    raise KeyError(sound)


def ultimate(path):
    """{name: IDSP bytes} of Ultimate's nus3audio"""
    d = open(path, 'rb').read()
    count = struct.unpack('<I', d[d.index(b'TNID') + 4:d.index(b'TNID') + 8])[0] // 4
    nmof, adof = d.index(b'NMOF') + 8, d.index(b'ADOF') + 8
    out = {}
    for i in range(count):
        o = struct.unpack('<I', d[nmof + 4 * i:nmof + 4 * i + 4])[0]
        name = d[o:d.index(b'\0', o)].decode()
        off, size = struct.unpack('<II', d[adof + 8 * i:adof + 8 * i + 8])
        if size:
            assert d[off:off + 4] == b'IDSP', name
            out[name] = d[off:off + size]
    return out


def silent_idsp(n):
    """a mono IDSP of n silent samples, looped whole (zero coefficients and frames)"""
    frames = (n + 13) // 14
    frames += frames & 1
    size = frames * 8
    h = struct.pack('>IIIHHIII', n, size * 2, RATE, 1, 0, mm.nibble(0), mm.nibble(n - 1), 2)
    h += b'\0' * 32 + b'\0' * 14
    head = struct.pack('>4sI10I', b'IDSP', 0, 1, RATE, n, 0, n - 1, 0x10, 0x40, 0x60, 0xA0, size).ljust(0x40, b'\0')
    return head + h.ljust(0x60, b'\0') + b'\0' * size


def idsp_info(b):
    ch, rate, n = struct.unpack('>III', b[8:20])
    return rate, ch, n


def entry(head, name, rest):
    """a TONE entry: head (12 bytes), name, then rest (from its 8-word: data offset, size, volume,
    ..., -1, rate, channels, samples, loop start, loop end, loop flag, 8 bytes)"""
    nm = name.encode() + b'\0'
    e = head + bytes([len(nm)]) + nm
    e = e.ljust((len(e) + 3) & ~3, b'\0') + b'\0' * 4
    return bytearray(e) + bytearray(rest)


def parse_entry(e):
    q = ((0x0D + e[0x0C] + 3) & ~3) + 4
    assert struct.unpack('<I', e[q:q + 4])[0] == 8, e[:0x40]
    return bytes(e[:0x0C]), e[0x0D:0x0D + e[0x0C] - 1].decode(), bytes(e[q:])


def set_data(rest, off, size, rate, ch, n, loop, volume=None):
    r = bytearray(rest)
    r[4:12] = struct.pack('<II', off, size)
    if volume is not None:
        r[12:16] = struct.pack('<f', volume)
    r[-0x20:-0x08] = struct.pack('<6I', rate, ch, n, 0, n - 1 if loop else 0, 1 if loop else 0)
    return bytes(r)


def tones_of(d):
    secs = mm.sections(d)
    t = dict(secs)[b'TONE']
    n = struct.unpack('<I', t[:4])[0]
    return secs, [t[o:o + s] for o, s in (struct.unpack('<II', t[4 + 8 * i:12 + 8 * i]) for i in range(n))]


def bank(ult, template, oneshot):
    secs, old = tones_of(template)
    _s, shots = tones_of(oneshot)
    shot_head, _n, shot_rest = parse_entry(shots[0])
    shot_rest = bytearray(shot_rest)
    k = shot_rest.index(struct.pack('<I', 0x271))
    shot_rest[k:k + 4] = struct.pack('<I', STAGE_GROUP)
    pack, where = bytearray(), {}

    def put(b):
        if b not in where:
            where[b] = len(pack)
            pack.extend(b)
            pack.extend(b'\0' * (-len(pack) % 0x20))
        return where[b]
    silent = silent_idsp(SILENT)
    entries = []
    for e in old[:FIRST]:                       # waterfall01_loop, amb05 / amb06: no data, kept as they are
        head, name, rest = parse_entry(e)
        if struct.unpack('<I', rest[8:12])[0]:
            e = entry(head, name, set_data(rest, put(silent), len(silent), RATE, 1, SILENT, True))
        entries.append(bytes(e))
    for sound, variants in SOUNDS:
        for v in range(1, variants + 1) if variants else [None]:
            name = 'se_stage_pickel_world_%s%s' % (sound, '' if v is None else v)
            b = ult[name]
            rate, ch, n = idsp_info(b)
            rest = set_data(shot_rest, put(b), len(b), rate, ch, n, False, VOLUME)
            entries.append(bytes(entry(shot_head, 'snd_se_stage_minecraft_%s%s' % (sound, '' if v is None else v), rest)))
    table, body = b'', b''
    first = 4 + 8 * len(entries)
    for e in entries:
        table += struct.pack('<II', first + len(body), len(e))
        body += e
    tone = struct.pack('<I', len(entries)) + table + body
    for s in secs:
        if s[0] == b'TONE':
            s[1] = tone
        elif s[0] == b'PACK':
            s[1] = bytes(pack)
    toc = b''.join(struct.pack('<4sI', nm, len(b)) for nm, b in secs)
    out = b'BANKTOC ' + struct.pack('<II', 4 + len(toc), len(secs)) + toc
    out += b''.join(nm + struct.pack('<I', len(b)) + b for nm, b in secs)
    return b'NUS3' + struct.pack('<I', len(out)) + out, len(entries)


def label_table(d, count):
    """soundlabeltable.bin with row ROW's sounds 0..count-1 (tone i)"""
    assert d[:4] == b'STB\0'
    rows_n, rows_size = struct.unpack('<II', d[8:16])
    assert rows_size == 16 * rows_n
    rows = [list(struct.unpack('<4I', d[16 + 16 * i:32 + 16 * i])) for i in range(rows_n)]
    base = 16 + rows_size
    labels = d[base:]
    bank_id, old, off, _z = rows[ROW]
    assert bank_id == BANK_ID and list(struct.unpack('<%dI' % old, labels[off:off + 4 * old])) == list(range(old))
    grow = 4 * (count - old)
    for r in rows:
        if r[0] != 0xFFFFFFFF and r[2] > off:
            r[2] += grow
    rows[ROW][1] = count
    labels = labels[:off] + struct.pack('<%dI' % count, *range(count)) + labels[off + 4 * old:]
    return d[:16] + b''.join(struct.pack('<4I', *r) for r in rows) + labels


def main():
    ult_path, template, oneshot, table, out = sys.argv[1:6]
    ult = ultimate(ult_path)
    data, count = bank(ult, open(template, 'rb').read(), open(oneshot, 'rb').read())
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'sound.nus3bank'), 'wb').write(data)
    open(os.path.join(out, 'soundlabeltable.bin'), 'wb').write(label_table(open(table, 'rb').read(), count))
    print('%d tones (%d of Ultimate\'s), bank %d bytes' % (count, count - FIRST, len(data)))
    for s, _n in SOUNDS:
        print('  %-16s tone %d x%d' % ((s,) + tone_index(s)))


if __name__ == '__main__':
    main()
