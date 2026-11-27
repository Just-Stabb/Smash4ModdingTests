#!/usr/bin/env python3
"""Sm4shCommand v1.7.32's Sound Effect Viewer, tested headlessly (Mono): sound_viewer_test.cs (SvTest.exe) on real
banks, then its decoded PCM checked here against this file's own DSP-ADPCM decoder (written from the format, not from
the C#) and, for Greninja's IceBoom, against the user's creeper_explosion.mp3 it was made from (tools/gekkouga_sound.py
--ice: trimmed / padded, -0.5 dBFS peak), by cross-correlation.

  python3 -I tools/Sm4shCommand/sound_viewer_test.py RUN_DIR FIGHTER_ROOT GAME_DATA PORT_ROOT OUT_DIR [--mp3 CREEPER.mp3] [--gui]

RUN_DIR: the built SM4SHCommand.exe / SALT.dll / Events.cfg / Viewer (SvTest.exe is built there); the other arguments
are sound_viewer_test.cs's. --gui runs the form part under xvfb-run (pictures OUT_DIR/viewer_*.png).
"""
import os
import struct
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CSC = '/usr/lib/dotnet/sdk/8.0.134/Roslyn/bincore/csc.dll'
MONO = '/usr/lib/mono/4.5'


def sections(d):
    assert d[:4] == b'NUS3' and d[8:16] == b'BANKTOC '
    n = struct.unpack('<I', d[20:24])[0]
    q, out = 24 + 8 * n, {}
    for i in range(n):
        nm, size = struct.unpack('<4sI', d[24 + 8 * i:32 + 8 * i])
        out[nm] = d[q + 8:q + 8 + size]
        q += 8 + size
    return out


def tone_audio(bank_path, index):
    """the tone's IDSP bytes (TONE entry's data block: u32 8, PACK offset, size)"""
    s = sections(open(bank_path, 'rb').read())
    t = s[b'TONE']
    o, size = struct.unpack('<II', t[4 + 8 * index:12 + 8 * index])
    e = t[o:o + size]
    q = ((0x0D + e[0x0C] + 3) & ~3) + 4
    assert struct.unpack('<I', e[q:q + 4])[0] == 8
    off, n = struct.unpack('<II', e[q + 4:q + 12])
    return s[b'PACK'][off:off + n]


def dsp_decode(b):
    """IDSP -> int16 [samples, channels]: DSP-ADPCM, frames of a header byte (predictor, scale) + 14 nibbles"""
    assert b[:4] == b'IDSP'
    ch, rate, n, ls, le, il, hs, chs, doff, dsize = struct.unpack('>9I', b[8:44]) + (struct.unpack('>I', b[44:48])[0],)
    out = np.zeros((n, ch), np.int16)
    frames = (n + 13) // 14
    for c in range(ch):
        h = hs + chs * c
        coef = struct.unpack('>16h', b[h + 0x1C:h + 0x3C])
        h1, h2 = struct.unpack('>hh', b[h + 0x40:h + 0x44])
        col = []
        for f in range(frames):
            p = f * 8
            at = doff + (p if ch == 1 else (p // il) * il * ch + c * il + p % il)
            ps = b[at]
            c1, c2 = coef[(ps >> 4) * 2], coef[(ps >> 4) * 2 + 1]
            sc = 1 << (ps & 15)
            for k in range(14):
                if f * 14 + k >= n:
                    break
                nib = (b[at + 1 + k // 2] >> (4 if k % 2 == 0 else 0)) & 15
                if nib >= 8:
                    nib -= 16
                v = ((nib * sc) << 11) + 1024 + c1 * h1 + c2 * h2
                v >>= 11
                v = max(-32768, min(32767, v))
                h2, h1 = h1, v
                col.append(v)
        out[:, c] = col
    return out, rate, ls, le


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) < 5:
        sys.exit(__doc__)
    run, root, game, port, out = [os.path.abspath(x) for x in a[:5]]
    mp3 = sys.argv[sys.argv.index('--mp3') + 1] if '--mp3' in sys.argv else None
    gui = '--gui' in sys.argv
    exe = os.path.join(run, 'SvTest.exe')
    refs = ['-r:' + os.path.join(run, x) for x in ('SALT.dll', 'SM4SHCommand.exe', 'FastColoredTextBox.dll')] + \
           ['-r:%s/%s' % (MONO, x) for x in ('mscorlib.dll', 'System.dll', 'System.Core.dll', 'System.Windows.Forms.dll', 'System.Drawing.dll')]
    subprocess.run(['dotnet', CSC, '-nologo', '-nowarn:1701,1702', '-out:' + exe, '-nostdlib'] + refs +
                   [os.path.join(HERE, 'sound_viewer_test.cs')], check=True)
    cmd = ['mono', exe, os.path.join(run, 'Events.cfg'), root, game, port, out] + (['--gui'] if gui else [])
    if gui:
        cmd = ['xvfb-run', '-a', '-s', '-screen 0 1400x900x24'] + cmd
    r = subprocess.run(cmd, cwd=run)
    fails = r.returncode
    oks = 0

    def check(what, ok, detail=''):
        nonlocal fails, oks
        print(('ok   ' if ok else 'FAIL ') + what + ('' if ok else ': ' + detail))
        if ok:
            oks += 1
        else:
            fails += 1

    for line in open(os.path.join(out, 'manifest.txt')):
        name, src, ch, rate, n, loops, ls, le = line.rstrip('\n').split('\t')
        path, idx = src.rsplit('#', 1)
        ref, rr, rls, rle = dsp_decode(tone_audio(path, int(idx)))
        got = np.fromfile(os.path.join(out, name + '.s16'), '<i2').reshape(-1, int(ch))
        check('%s (%s tone %s): C# decode = this decoder, sample for sample (%d x %s, %s Hz)' % (
            name, os.path.basename(path), idx, len(got), ch, rate), got.shape == ref.shape and np.array_equal(got, ref),
            'shape %s vs %s, %d samples differ' % (got.shape, ref.shape, int((got != ref).sum()) if got.shape == ref.shape else -1))
        check('%s: rate / loop points' % name, (int(rate), int(ls), int(le)) == (rr, rls, min(rle, len(ref) - 1)),
              '%s vs %s' % ((rate, ls, le), (rr, rls, rle)))
        peak = int(np.abs(ref.astype(np.int32)).max())
        check('%s: not silent (peak %d)' % (name, peak), peak > 1000)

    if mp3:
        # IceBoom against its source: the clip decoded at 48 kHz mono, best lag by FFT cross-correlation
        src = subprocess.run(['ffmpeg', '-v', 'error', '-i', mp3, '-ac', '1', '-ar', '48000', '-f', 's16le', '-'],
                             stdout=subprocess.PIPE, check=True).stdout
        x = np.frombuffer(src, '<i2').astype(np.float64)
        y = np.fromfile(os.path.join(out, 'iceboom.s16'), '<i2').astype(np.float64)
        m = 1 << int(np.ceil(np.log2(len(x) + len(y))))
        cc = np.fft.irfft(np.fft.rfft(y, m) * np.conj(np.fft.rfft(x, m)), m)
        lag = int(np.argmax(cc))
        lag = lag if lag < m // 2 else lag - m           # y[t] ~ x[t - lag]
        if lag >= 0:
            yy, xx = y[lag:], x
        else:
            yy, xx = y, x[-lag:]
        k = min(len(yy), len(xx))
        r_ = float(np.corrcoef(yy[:k], xx[:k])[0, 1])
        print('     IceBoom vs creeper_explosion.mp3: lag %d samples (%.3f s of silence in front), correlation %.4f' % (lag, lag / 48000, r_))
        check('IceBoom correlates with the user\'s mp3 (r %.4f > 0.98)' % r_, r_ > 0.98)
        check('IceBoom: the padding in front (gekkouga_sound.py ice_cut: 0.149 s)', abs(lag / 48000 - 0.149) < 0.005, '%.4f s' % (lag / 48000))
    print('%d python checks; %d failures in all (the C# test\'s count included)' % (oks, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
