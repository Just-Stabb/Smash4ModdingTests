#!/usr/bin/env python3
"""Smash Ultimate music (.nus3audio holding Namco "OPUS" + Switch Opus) to WAV, with its loop.

  python3 tools/nus3audio_opus.py FILE.nus3audio OUT.wav

nus3audio: 'NUS3', 'AUDIINDX', ..., 'ADOF' (the file's blobs: absolute offset, size), 'TNNM'
(names), 'PACK'. The blob: 'OPUS' (big-endian: version, sample count, channels, sample rate, loop
start, loop end, ?, the Switch Opus offset and size), then Switch Opus (little-endian 0x80000001
header: channels, frame size, sample rate, data offset, ..., pre-skip; at the data offset
0x80000004 + size, then packets: big-endian size, final range, the Opus packet). Decoded with the
system's libopus. Prints the sample rate, sample count and loop points (samples).
"""
import ctypes
import ctypes.util
import struct
import sys
import wave

import numpy as np


def blob(path):
    d = open(path, 'rb').read()
    i = d.index(b'ADOF')
    off, size = struct.unpack('<II', d[i + 8:i + 16])
    return d[off:off + size]


def decode(path):
    """(pcm int16 [n, channels], rate, loop start, loop end)"""
    a = blob(path)
    assert a[:4] == b'OPUS', a[:4]
    _v, count, ch, rate, ls, le, _f, off, _size = struct.unpack('>9I', a[4:40])
    sw = a[off:]
    sid, _hs, _ver, sch, _fs, srate, doff, _u, _ctx, preskip = struct.unpack('<IIBBHIIIII', sw[:32])
    assert sid == 0x80000001 and sch == ch and srate == rate, (hex(sid), sch, srate)
    did, dsize = struct.unpack('<II', sw[doff:doff + 8])
    assert did == 0x80000004
    lib = ctypes.CDLL(ctypes.util.find_library('opus') or 'libopus.so.0')
    lib.opus_decoder_create.restype = ctypes.c_void_p
    err = ctypes.c_int()
    dec = lib.opus_decoder_create(rate, ch, ctypes.byref(err))
    assert err.value == 0
    buf = (ctypes.c_int16 * (5760 * ch))()
    out = []
    o, end = doff + 8, doff + 8 + dsize
    while o + 8 <= end:
        n, _rng = struct.unpack('>II', sw[o:o + 8])
        pkt = sw[o + 8:o + 8 + n]
        got = lib.opus_decode(ctypes.c_void_p(dec), pkt, n, buf, 5760, 0)
        assert got > 0, got
        out.append(np.frombuffer(bytes(buf), np.int16, got * ch).copy())
        o += 8 + n
    pcm = np.concatenate(out).reshape(-1, ch)[preskip:preskip + count]
    return pcm, rate, ls, le


def main():
    pcm, rate, ls, le = decode(sys.argv[1])
    w = wave.open(sys.argv[2], 'wb')
    w.setnchannels(pcm.shape[1])
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(pcm.tobytes())
    w.close()
    print('%d Hz, %d samples (%.1f s), loop %d-%d' % (rate, len(pcm), len(pcm) / rate, ls, le))


if __name__ == '__main__':
    main()
