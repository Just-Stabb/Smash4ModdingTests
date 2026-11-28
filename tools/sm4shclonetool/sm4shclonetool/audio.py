"""Sounds: a nus3bank's tones (list, read, add, replace), Namco IDSP (Smash 4's DSP-ADPCM tone format: encode from a
WAV with the vendored pure-Python encoder vendor/dspadpcm.py, decode for a preview), WAV in / out and a preview player.

nus3bank (little-endian): 'NUS3', size, 'BANKTOC ', the sections (PROP, BINF, GRP, DTON, TONE, JUNK, PACK). TONE:
count, (offset, size) per entry, then the entries: 12 bytes, the name (length byte, text), padding, then a block
starting with the word 8: +4 the data's offset in PACK, +8 its size, +12 the volume (dB, float), ..., and 0x20 bytes
from its end: rate, channels, samples, loop start, loop end, loop flag. A tone's data is an IDSP: a 0x40-byte header
('IDSP', 0, channels, rate, samples, loop start, loop end, interleave 0x10, 0x40, 0x60 per channel, data offset, size
per channel), a 0x60-byte DSP header per channel (samples, nibbles, rate, loop flag, format, loop start / end nibble,
current nibble 2, the 16 coefficients, gain, ps, two history samples, loop ps / history), then the channels' ADPCM
interleaved by 0x10 bytes."""
import os
import struct
import subprocess
import sys
import tempfile
import wave

from . import _paths  # noqa: F401
import dspadpcm  # noqa: E402

RATE = 48000


# ---------------------------------------------------------------- nus3bank
def sections(d):
    assert d[:4] == b'NUS3' and d[8:16] == b'BANKTOC ', 'not a nus3bank'
    count = struct.unpack('<I', d[20:24])[0]
    q = 24 + count * 8
    out = []
    for i in range(count):
        name, size = struct.unpack('<4sI', d[24 + i * 8:32 + i * 8])
        out.append([name, bytes(d[q + 8:q + 8 + size])])
        q += 8 + size
    return out


def build(secs):
    toc = b''.join(struct.pack('<4sI', nm, len(b)) for nm, b in secs)
    out = b'BANKTOC ' + struct.pack('<II', 4 + len(toc), len(secs)) + toc
    out += b''.join(nm + struct.pack('<I', len(b)) + b for nm, b in secs)
    return b'NUS3' + struct.pack('<I', len(out)) + out


def _entries(secs):
    t = dict(secs)[b'TONE']
    n = struct.unpack('<I', t[:4])[0]
    return [bytes(t[o:o + s]) for o, s in (struct.unpack('<II', t[4 + 8 * i:12 + 8 * i]) for i in range(n))]


def _parse(e):
    """(head 12 bytes, name, block from the word 8) or None for an entry without data (a placeholder)"""
    if len(e) < 0x10:
        return None
    q = ((0x0D + e[0x0C] + 3) & ~3) + 4
    if q + 4 > len(e) or struct.unpack('<I', e[q:q + 4])[0] != 8:
        return None
    return e[:0x0C], e[0x0D:0x0D + e[0x0C] - 1].decode('latin1'), e[q:]


def _entry(head, name, block):
    nm = name.encode('latin1') + b'\0'
    e = head + bytes([len(nm)]) + nm
    return e.ljust((len(e) + 3) & ~3, b'\0') + b'\0' * 4 + block


class Bank:
    """a nus3bank in memory: .tones = [{'name', 'offset', 'size', 'volume', 'rate', 'channels', 'samples'} or None]"""

    def __init__(self, data):
        self.secs = sections(data)
        assert build(self.secs) == bytes(data), 'nus3bank: round trip differs'
        self.raw = _entries(self.secs)
        self.pack = bytearray(dict(self.secs)[b'PACK'])

    @property
    def tones(self):
        out = []
        for e in self.raw:
            p = _parse(e)
            if p is None:
                out.append(None)
                continue
            _h, name, b = p
            off, size = struct.unpack('<II', b[4:12])
            vol = struct.unpack('<f', b[12:16])[0]
            rate, ch, n = struct.unpack('<3I', b[-0x20:-0x14])
            out.append({'name': name, 'offset': off, 'size': size, 'volume': vol, 'rate': rate, 'channels': ch,
                        'samples': n})
        return out

    def binf(self):
        b = dict(self.secs)[b'BINF']
        n = b[8]
        return b[9:9 + n - 1].decode('latin1'), struct.unpack('<I', b[(9 + n + 3) & ~3:][:4])[0]

    def data_of(self, i):
        t = self.tones[i]
        return bytes(self.pack[t['offset']:t['offset'] + t['size']])

    def _put(self, blob):
        self.pack.extend(b'\0' * (-len(self.pack) % 0x20))
        off = len(self.pack)
        self.pack.extend(blob)
        self.pack.extend(b'\0' * (-len(self.pack) % 0x20))
        return off

    def _with_data(self, block, off, blob, volume=None):
        b = bytearray(block)
        b[4:12] = struct.pack('<II', off, len(blob))
        if volume is not None:
            b[12:16] = struct.pack('<f', volume)
        if blob[:4] == b'IDSP':
            ch, rate, n, ls, le = struct.unpack('>5I', blob[8:28])
            loop = struct.unpack('>H', blob[0x40 + 12:0x40 + 14])[0]
            b[-0x20:-0x08] = struct.pack('<6I', rate, ch, n, ls, le, 1 if loop else 0)
        return bytes(b)

    def add_copy(self, src, name, blob=None, volume=None):
        """a new tone: tone src's entry (group, flags, volume) under name, with its data copied (or blob); its index"""
        head, _n, block = _parse(self.raw[src])
        blob = blob if blob is not None else self.data_of(src)
        off = self._put(blob)
        self.raw.append(_entry(head, name, self._with_data(block, off, blob, volume)))
        return len(self.raw) - 1

    def replace(self, i, blob, volume=None):
        """tone i plays blob (appended to PACK; the old data stays where it is, unreferenced if no other tone uses it)"""
        head, name, block = _parse(self.raw[i])
        off = self._put(blob)
        self.raw[i] = _entry(head, name, self._with_data(block, off, blob, volume))

    def set_binf(self, name, bank_id):
        for s in self.secs:
            if s[0] == b'BINF':
                b = s[1]
                n = b[8]
                rest = b[(9 + n + 3) & ~3:]
                nm = name.encode('latin1') + b'\0'
                head = b[:8] + bytes([len(nm)]) + nm
                s[1] = head.ljust((len(head) + 3) & ~3, b'\0') + struct.pack('<I', bank_id) + rest[4:]

    def data(self):
        table, body = b'', b''
        base = 4 + 8 * len(self.raw)
        for e in self.raw:
            table += struct.pack('<II', base + len(body), len(e))
            body += e
        for s in self.secs:
            if s[0] == b'TONE':
                s[1] = struct.pack('<I', len(self.raw)) + table + body
            elif s[0] == b'PACK':
                s[1] = bytes(self.pack)
        return build(self.secs)


# ---------------------------------------------------------------- IDSP
def _nibbles(n):
    return n // 14 * 16 + (n % 14 + 2 if n % 14 else 0)


def idsp_encode(pcm, rate=RATE, loop=False):
    """an IDSP of int16 samples: a list (mono) or a list of channels (one-shot unless loop: the whole sound looped)"""
    chans = pcm if pcm and isinstance(pcm[0], (list, tuple)) else [pcm]
    n = len(chans[0])
    nfr = (n + 13) // 14
    nfr += nfr & 1                                  # whole 0x10-byte interleave blocks
    size = nfr * 8
    nib = _nibbles(n)
    heads, datas = b'', []
    for c in chans:
        coefs, frames, _dec = dspadpcm.encode(list(c))
        frames = frames.ljust(size, b'\0')
        h = struct.pack('>IIIHHIII', n, nib, rate, 1 if loop else 0, 0, 2, nib - 1, 2)
        h += struct.pack('>16h', *coefs) + struct.pack('>HHhh', 0, frames[0], 0, 0) + struct.pack('>Hhh', frames[0], 0, 0)
        heads += h.ljust(0x60, b'\0')
        datas.append(frames)
    start = 0x40 + 0x60 * len(chans)
    body = b''.join(b''.join(d[o:o + 0x10] for d in datas) for o in range(0, size, 0x10))
    head = struct.pack('>4sI10I', b'IDSP', 0, len(chans), rate, n, 0, n - 1 if loop else 0, 0x10, 0x40, 0x60, start,
                       size)
    return head.ljust(0x40, b'\0') + heads + body


def idsp_decode(blob):
    """(rate, [channel sample lists]) of an IDSP"""
    assert blob[:4] == b'IDSP', 'not an IDSP'
    ch, rate, n = struct.unpack('>3I', blob[8:20])
    inter, _h0, hsize, start, size = struct.unpack('>5I', blob[0x1C:0x30])
    out = []
    for c in range(ch):
        h = blob[0x40 + hsize * c:0x40 + hsize * (c + 1)]
        coefs = list(struct.unpack('>16h', h[0x1C:0x3C]))
        frames = bytearray()
        for o in range(0, size, inter):
            at = start + o * ch + inter * c
            frames += blob[at:at + inter]
        out.append(dspadpcm.decode(bytes(frames), coefs, n))
    return rate, out


# ---------------------------------------------------------------- WAV
def read_wav(path, rate=RATE, channels=1):
    """int16 samples of a WAV (PCM 8 / 16 / 24 / 32-bit or 32-bit float), resampled to rate: a list (channels=1, the
    channels mixed) or a list of `channels` channel lists (a mono WAV doubled)"""
    import numpy as np
    d = open(path, 'rb').read()
    if d[:4] != b'RIFF' or d[8:12] != b'WAVE':
        raise ValueError('%s: not a WAV file' % path)
    p, fmt, data = 12, None, None
    while p + 8 <= len(d):
        cid, size = struct.unpack('<4sI', d[p:p + 8])
        body = d[p + 8:p + 8 + size]
        if cid == b'fmt ':
            fmt = struct.unpack('<HHIIHH', body[:16])
        elif cid == b'data':
            data = body
        p += 8 + size + (size & 1)
    if fmt is None or data is None:
        raise ValueError('%s: no fmt / data chunk' % path)
    tag, ch, src_rate, _br, _al, bits = fmt
    if tag == 0xFFFE:
        tag = 3 if bits == 32 and b'\x03\x00\x00\x00\x00\x00\x10\x00' in d[:200] else 1
    if tag == 3 and bits == 32:
        x = np.frombuffer(data[:len(data) // 4 * 4], '<f4').astype(np.float64)
    elif bits == 8:
        x = (np.frombuffer(data, np.uint8).astype(np.float64) - 128) / 128
    elif bits == 16:
        x = np.frombuffer(data[:len(data) // 2 * 2], '<i2') / 32768.0
    elif bits == 24:
        b = np.frombuffer(data[:len(data) // 3 * 3], np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        x = np.where(v >= 1 << 23, v - (1 << 24), v) / float(1 << 23)
    elif bits == 32:
        x = np.frombuffer(data[:len(data) // 4 * 4], '<i4') / float(1 << 31)
    else:
        raise ValueError('%s: %d-bit samples not supported' % (path, bits))
    x = x[:len(x) // ch * ch].reshape(-1, ch)
    cols = [x.mean(1)] if channels == 1 else [x[:, min(c, ch - 1)] for c in range(channels)]
    out = []
    for y in cols:
        if src_rate != rate and len(y):
            if src_rate > rate:                                 # a simple low-pass before going down
                k = max(1, int(round(src_rate / rate)))
                if k > 1:
                    y = np.convolve(y, np.ones(k) / k, mode='same')
            t = np.arange(int(len(y) * rate / src_rate)) * (src_rate / rate)
            y = np.interp(t, np.arange(len(y)), y)
        out.append([int(v) for v in np.clip(np.round(y * 32767), -32768, 32767)])
    return out[0] if channels == 1 else out


def write_wav(path, samples, rate=RATE):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack('<%dh' % len(samples), *samples))


def wav_to_idsp(path):
    return idsp_encode(read_wav(path))


def idsp_to_wav(blob, path):
    rate, chans = idsp_decode(blob)
    write_wav(path, chans[0], rate)
    return path


def play(blob_or_wav):
    """plays an IDSP (bytes) or a WAV path: winsound on Windows, afplay / aplay / paplay elsewhere; False if none"""
    path = blob_or_wav
    if isinstance(blob_or_wav, (bytes, bytearray)):
        fd, path = tempfile.mkstemp(suffix='.wav', prefix='s4ct_')
        os.close(fd)
        idsp_to_wav(bytes(blob_or_wav), path)
    if sys.platform.startswith('win'):
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        return True
    for player in (['afplay'], ['aplay', '-q'], ['paplay']):
        try:
            subprocess.Popen(player + [path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except OSError:
            continue
    return False
