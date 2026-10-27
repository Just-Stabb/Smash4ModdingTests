#!/usr/bin/env python3
"""A new fighter's own sound-effect bank (a copy of its base's: same tones, its own bank id and
soundlabeltable row) plus extra sounds from audio files.

  python3 tools/fighter_own_bank.py FIGHTER_DIR SOUNDLABELTABLE OUT_DIR --name Supamario \\
      [--bank-id 2200] [--row N] [--sound LABEL=FILE[@VOLUME_DB] ...]

FIGHTER_DIR: fighter/<name>/ (its sound/snd_se_<Name>.nus3bank: the base's, renamed; its
script/animcmd and script/msc). SOUNDLABELTABLE: the current sound/config/soundlabeltable.bin.
Writes OUT_DIR/fighter/<name>/sound/snd_se_<Name>.nus3bank, the scripts it changed, and
OUT_DIR/sound/config/soundlabeltable.bin.

How the game binds them (cross_f.rpx): a fighter's bank is loaded by file name
(fighter/%s/sound/snd_se_%s.nus3bank, 0x030BB464), its id read from BINF. A sound id is
(row << 16) | label: soundlabeltable row `row` -> (bank id, labels, offset) (0x0311EC30 /
0x0311EC80), label -> tone index (0x0311EDC4 / 0x0311EEC4), and the bank id is matched against the
banks the player has loaded (by their BINF id, e.g. 0x03125C78 for a stage). So a renamed copy of
the base's bank with the base's id plays from the base's row, and with two banks of one id loaded
(base and clone in one match) which one answers is unknown; with its own id and row it is separate.

- BINF: name snd_se_<Name>, id --bank-id (default: the highest id in the table + 1 above 2143,
  the fighter se range 2000-2143).
- soundlabeltable: an empty row (bank id -1; --row, default the highest-index empty one, so the
  row count is unchanged) = the base's row's labels + one label per --sound.
- TONE / PACK: each --sound encoded as the game's one-shot se tones are (Namco IDSP, DSP-ADPCM,
  48000 Hz mono, no loop; the clip normalised to a -0.5 dBFS peak), the TONE entry a copy of the
  base's Special_L01 one-shot's (its group, flags) with its name snd_se_<Name>_<LABEL>, data and
  VOLUME (dB, default 0).
- Scripts: every sound id on the base's row becomes the same label on the new row: ACMD sound.bin
  (all commands' int params) and other ACMD files' SE / Sound commands; MSC pushInt values whose
  label maps to a tone (so flag constants like 0x20000, label 0 = none, are left alone).
"""
import argparse
import glob
import os
import struct
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'mscdec'))
import acmd  # noqa: E402
import minecraft_music as mm  # noqa: E402
import minecraft_sound as ms  # noqa: E402

RATE = 48000
PEAK_DB = -0.5
TEMPLATE_TONE = 'Special_L01'       # a one-shot (loop flag 0) of the base's bank


# ---------------------------------------------------------------- audio

def load_audio(path):
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, 'a.s16')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-ac', '1', '-ar', str(RATE), '-f', 's16le', raw],
                       check=True)
        x = np.fromfile(raw, '<i2').astype(np.float64) / 32768
    x *= 10 ** (PEAK_DB / 20) / max(np.abs(x).max(), 1e-9)
    return np.round(x * 32767).clip(-32768, 32767).astype(np.int16)


def idsp_oneshot(exe, pcm):
    """mono IDSP, no loop (as the game's se one-shots: header loop points 0, DSP loop flag 0)"""
    n = len(pcm)
    frames = (n + 13) // 14
    frames += frames & 1
    size = frames * 8
    coefs, ps, _lps, _y1, _y2, adpcm = mm.encode(exe, pcm, 0)
    h = struct.pack('>IIIHHIII', n, mm.nibble(n - 1) + 1, RATE, 0, 0, mm.nibble(0), mm.nibble(n - 1), 2)
    h += coefs + struct.pack('>H', 0) + ps + b'\0' * 8
    head = struct.pack('>4sI10I', b'IDSP', 0, 1, RATE, n, 0, 0, 0x10, 0x40, 0x60, 0xA0, size).ljust(0x40, b'\0')
    return head + h.ljust(0x60, b'\0') + adpcm.ljust(size, b'\0')


# ---------------------------------------------------------------- bank

def build_bank(data, name, bank_id, sounds):
    """(bank bytes, first new tone index); sounds: [(label, idsp, volume)]"""
    secs = mm.sections(data)
    _s, tones = ms.tones_of(data)
    template = None
    for e in tones:
        head, nm, rest = ms.parse_entry(e)
        if nm.endswith(TEMPLATE_TONE):
            template = (head, rest)
    assert template, 'no %s tone to copy' % TEMPLATE_TONE
    pack = bytearray(dict(secs)[b'PACK'])
    first = len(tones)
    entries = [bytes(e) for e in tones]
    for label, blob, vol in sounds:
        pack.extend(b'\0' * (-len(pack) % 0x20))
        off = len(pack)
        pack.extend(blob)
        n = struct.unpack('>I', blob[0x10:0x14])[0]
        rest = ms.set_data(template[1], off, len(blob), RATE, 1, n, False, vol)
        entries.append(bytes(ms.entry(template[0], 'snd_se_%s_%s' % (name, label), rest)))
    pack.extend(b'\0' * (-len(pack) % 0x20))
    table, body = b'', b''
    base = 4 + 8 * len(entries)
    for e in entries:
        table += struct.pack('<II', base + len(body), len(e))
        body += e
    for s in secs:
        if s[0] == b'TONE':
            s[1] = struct.pack('<I', len(entries)) + table + body
        elif s[0] == b'PACK':
            s[1] = bytes(pack)
        elif s[0] == b'BINF':
            nm = ('snd_se_' + name).encode() + b'\0'
            b = s[1][:8] + bytes([len(nm)]) + nm
            s[1] = b.ljust((len(b) + 3) & ~3, b'\0') + struct.pack('<I', bank_id)
    toc = b''.join(struct.pack('<4sI', nm, len(b)) for nm, b in secs)
    out = b'BANKTOC ' + struct.pack('<II', 4 + len(toc), len(secs)) + toc
    out += b''.join(nm + struct.pack('<I', len(b)) + b for nm, b in secs)
    return b'NUS3' + struct.pack('<I', len(out)) + out, first


def binf(data):
    b = dict(mm.sections(data))[b'BINF']
    n = b[8]
    return b[9:9 + n - 1].decode('latin1'), struct.unpack('<I', b[(9 + n + 3) & ~3:][:4])[0]


# ---------------------------------------------------------------- soundlabeltable

class Table:
    def __init__(self, d):
        assert d[:4] == b'STB\0'
        self.head = d[:8]
        n, size = struct.unpack('<II', d[8:16])
        assert size == 16 * n
        self.rows = [list(struct.unpack('<4I', d[16 + 16 * i:32 + 16 * i])) for i in range(n)]
        self.labels = bytearray(d[16 + size:])

    def data(self):
        n = len(self.rows)
        return self.head + struct.pack('<II', n, 16 * n) + b''.join(struct.pack('<4I', *r) for r in self.rows) + \
            bytes(self.labels)

    def row_of(self, bank_id):
        rows = [i for i, r in enumerate(self.rows) if r[0] == bank_id]
        assert len(rows) == 1, (bank_id, rows)
        return rows[0]

    def tones(self, row):
        _b, n, off, _z = self.rows[row]
        return list(struct.unpack('<%di' % n, self.labels[off:off + 4 * n]))

    def set_row(self, row, tones):
        """a row in use given a new label list (appended; the old list stays as unused bytes)"""
        assert self.rows[row][0] != 0xFFFFFFFF and len(self.labels) % 4 == 0
        off = len(self.labels)
        self.labels.extend(struct.pack('<%di' % len(tones), *tones))
        self.rows[row][1:3] = [len(tones), off]

    def add_row(self, row, bank_id, tones):
        assert self.rows[row][0] == 0xFFFFFFFF, 'row %d is in use' % row
        assert len(self.labels) % 4 == 0
        off = len(self.labels)
        self.labels.extend(struct.pack('<%di' % len(tones), *tones))
        self.rows[row] = [bank_id, len(tones), off, 0]


# ---------------------------------------------------------------- scripts

def acmd_rewrite(path, kind, old_row, count, new_row, log):
    """kind: the file's own name (sound.bin: every command's int params; others: SE / Sound commands)"""
    f = acmd.ACMDFile.load(path)
    n = 0
    for cmds in f.scripts.values():
        for c in cmds:
            words = c.name.lower().split('_')
            if kind != 'sound.bin' and 'se' not in words and not any('sound' in w for w in words):
                continue
            for i, v in enumerate(c.params):
                if c.kind(i) != 1 and isinstance(v, int) and v >> 16 == old_row and (v & 0xFFFF) < count:
                    c.params[i] = new_row << 16 | (v & 0xFFFF)
                    n += 1
    if n:
        f.save(path)
        log.append('%s: %d sound ids' % (kind if kind != 'sound.bin' else path, n))
    return n


def sound_arg(cmds, k):
    """pushInt k is a SoundModule call's sound id: right after its function selector (pushInt
    0x27xx, e.g. 0x2710 play) and, past any further pushed arguments, the call is sys 0x1E
    (fireball: sys_1E(0x2710, 0x20037)); flag words like sys_18(0x2713, ..., 0x20001, ...) are not"""
    prev = cmds[k - 1] if k else None
    # the selector pushed as an int (0xA, the game's own scripts) or a short (0xD, tools/mscdec's compiler)
    if not (prev and prev.command in (0xA, 0xD) and prev.parameters and 0x2700 <= prev.parameters[0] < 0x2800):
        return False
    for c in cmds[k + 1:]:
        if c.command in (0xA, 0xD):
            continue
        return c.command == 0x2D and c.parameters[1] == 0x1E
    return False


def msc_rewrite(path, old_row, tones, new_row, log):
    import msc as mscmod
    d = bytearray(open(path, 'rb').read())
    m = mscmod.MscFile()
    m.readFromBytes(bytes(d), '<')
    n = 0
    for s in m.scripts:
        for k, c in enumerate(s.cmds):
            if c.command == 0xA and c.parameters:
                v = c.parameters[0] & 0xFFFFFFFF
                lab = v & 0xFFFF
                if v >> 16 == old_row and lab < len(tones) and tones[lab] >= 0 and sound_arg(s.cmds, k):
                    p = c.commandPosition + 0x30
                    assert d[p] & 0x7F == 0xA and struct.unpack('>I', d[p + 1:p + 5])[0] == v, hex(p)
                    d[p + 1:p + 5] = struct.pack('>I', new_row << 16 | lab)
                    log.append('%s @0x%X: pushInt 0x%08X -> 0x%08X' % (path, p, v, new_row << 16 | lab))
                    n += 1
    if n:
        open(path, 'wb').write(d)
    return n


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('fighter')
    ap.add_argument('table')
    ap.add_argument('out')
    ap.add_argument('--name', required=True)
    ap.add_argument('--bank-id', type=lambda s: int(s, 0))
    ap.add_argument('--row', type=lambda s: int(s, 0))
    ap.add_argument('--sound', action='append', default=[])
    a = ap.parse_args()
    folder = os.path.basename(os.path.normpath(a.fighter))
    bank_path = os.path.join(a.fighter, 'sound', 'snd_se_%s.nus3bank' % a.name)
    data = open(bank_path, 'rb').read()
    old_name, old_id = binf(data)
    table = Table(open(a.table, 'rb').read())
    old_row = table.row_of(old_id)
    old_tones = table.tones(old_row)
    ids = {r[0] for r in table.rows}
    bank_id = a.bank_id if a.bank_id is not None else max(i for i in ids if 2000 <= i < 3000) + 1
    assert bank_id not in ids, 'bank id %d is in the table' % bank_id
    row = a.row if a.row is not None else max(i for i, r in enumerate(table.rows) if r[0] == 0xFFFFFFFF)

    exe = mm.dspenc()
    sounds = []
    for spec in a.sound:
        label, rest = spec.split('=', 1)
        path, vol = (rest.rsplit('@', 1) + ['0'])[:2] if '@' in rest else (rest, '0')
        pcm = load_audio(path)
        sounds.append((label, idsp_oneshot(exe, pcm), float(vol)))
    os.remove(exe)
    bank, first = build_bank(data, a.name, bank_id, sounds)
    new_tones = old_tones + [first + k for k in range(len(sounds))]
    table.add_row(row, bank_id, new_tones)

    out_fighter = os.path.join(a.out, 'fighter', folder)
    os.makedirs(os.path.join(out_fighter, 'sound'), exist_ok=True)
    open(os.path.join(out_fighter, 'sound', os.path.basename(bank_path)), 'wb').write(bank)
    os.makedirs(os.path.join(a.out, 'sound', 'config'), exist_ok=True)
    open(os.path.join(a.out, 'sound', 'config', 'soundlabeltable.bin'), 'wb').write(table.data())

    log = []
    for src in sorted(glob.glob(os.path.join(a.fighter, 'script', 'animcmd', '**', '*.bin'), recursive=True)):
        if os.path.basename(src) == 'motion.mtable':
            continue
        dst = os.path.join(out_fighter, os.path.relpath(src, a.fighter))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        tmp = dst + '.tmp'
        open(tmp, 'wb').write(open(src, 'rb').read())
        if acmd_rewrite(tmp, os.path.basename(src), old_row, len(old_tones), row, log):
            os.replace(tmp, dst)
        else:
            os.remove(tmp)
    for src in sorted(glob.glob(os.path.join(a.fighter, 'script', 'msc', '**', '*.mscsb'), recursive=True)):
        dst = os.path.join(out_fighter, os.path.relpath(src, a.fighter))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        tmp = dst + '.tmp'
        open(tmp, 'wb').write(open(src, 'rb').read())
        if msc_rewrite(tmp, old_row, old_tones, row, log):
            os.replace(tmp, dst)
        else:
            os.remove(tmp)

    print('%s: BINF %s id %d (row %d) -> snd_se_%s id %d, row %d (%d labels)' % (
        os.path.basename(bank_path), old_name, old_id, old_row, a.name, bank_id, row, len(new_tones)))
    for k, (label, blob, vol) in enumerate(sounds):
        lab = len(old_tones) + k
        print('  %-14s tone %d, label %d: sound id 0x%08X (%.2f s, volume %+.1f dB)' % (
            label, first + k, lab, row << 16 | lab, struct.unpack('>I', blob[0x10:0x14])[0] / RATE, vol))
    print('\n'.join(log))


if __name__ == '__main__':
    main()
