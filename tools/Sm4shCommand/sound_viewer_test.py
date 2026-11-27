#!/usr/bin/env python3
"""Sm4shCommand v1.7.32's Sound Effect Viewer and v1.7.33's Sound Adder, tested headlessly (Mono): sound_viewer_test.cs
(SvTest.exe) on real banks, then its decoded PCM checked here against this file's own DSP-ADPCM decoder (written from the
format, not from the C#) and, for Greninja's IceBoom, against the user's creeper_explosion.mp3 it was made from
(tools/gekkouga_sound.py --ice: trimmed / padded, -0.5 dBFS peak), by cross-correlation.

  python3 -I tools/Sm4shCommand/sound_viewer_test.py RUN_DIR FIGHTER_ROOT GAME_DATA PORT_ROOT OUT_DIR [--mp3 CREEPER.mp3] [--gui] [--adder]

RUN_DIR: the built SM4SHCommand.exe / SALT.dll / Events.cfg / Viewer (SvTest.exe is built there); the other arguments
are sound_viewer_test.cs's. --gui runs the form part under xvfb-run (pictures OUT_DIR/viewer_*.png, adder_*.png).
--adder (needs --mp3: the clips are made from it) tests the Sound Adder: ffmpeg makes the inputs (44.1 kHz WAVs mono /
stereo / 24-bit / float, a 22.05 kHz one, one padded with silence, an mp3, a flac, an ogg); the C# adds 3 tones to the
user's snd_se_Gekkouga and his soundlabeltable row, one to Master's se and its costume bank, ...; then here: the C#
encoder's frames against tools/dspadpcm's (dspenc, compiled here) byte for byte, its resampling against ffmpeg's, and
the written banks / table read with the repo's own tools (fighter_own_bank.py's Table / binf, minecraft_sound.py's TONE
reader, fighter_sound.py's tone count) and this file's decoder, the new tones against their source clips.
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile

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


# ---------------------------------------------------------------- v1.7.33: the Sound Adder

TOOLS = os.path.normpath(os.path.join(HERE, '..'))


def ff(*a):
    subprocess.run(['ffmpeg', '-v', 'error', '-y'] + list(a), check=True)


def ff_pcm(path, rate, ch):
    """ffmpeg's own decode + resample (swr), int16 [n, ch]: the independent reference"""
    b = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', str(ch), '-ar', str(rate), '-f', 's16le', '-'],
                       stdout=subprocess.PIPE, check=True).stdout
    return np.frombuffer(b, '<i2').reshape(-1, ch)


def make_inputs(mp3, d):
    os.makedirs(d, exist_ok=True)
    j = lambda f: os.path.join(d, f)
    ff('-i', mp3, '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le', j('mono44.wav'))
    ff('-i', mp3, '-ac', '2', '-ar', '44100', '-c:a', 'pcm_s16le', j('stereo44.wav'))
    ff('-i', j('mono44.wav'), '-c:a', 'pcm_s24le', j('mono44_s24.wav'))
    ff('-i', j('mono44.wav'), '-c:a', 'pcm_f32le', j('mono44_f32.wav'))
    ff('-i', j('mono44.wav'), '-c:a', 'flac', j('mono44.flac'))
    ff('-i', j('stereo44.wav'), '-c:a', 'libvorbis', '-q:a', '5', j('stereo44.ogg'))
    ff('-i', mp3, '-ac', '1', '-ar', '22050', '-c:a', 'pcm_s16le', j('mono22.wav'))
    ff('-i', mp3, '-t', '1.5', '-ac', '1', '-c:a', 'libmp3lame', '-b:a', '128k', j('ding.mp3'))
    # the clip trimmed (-45 dBFS peak, both ends), then 0.5 s of silence before it and 0.3 s after
    trim = 'silenceremove=start_periods=1:start_threshold=-45dB:detection=peak,areverse,' \
           'silenceremove=start_periods=1:start_threshold=-45dB:detection=peak,areverse'
    ff('-i', j('mono44.wav'), '-af', trim + ',adelay=delays=22050S:all=1,apad=pad_dur=0.3', '-c:a', 'pcm_s16le', j('padded.wav'))


def source_48k(path, ch, db=-45.0):
    """the Sound Adder's input path done by ffmpeg / numpy: decoded at its own rate (f32), silence trimmed (peak), resampled
    to 48 kHz; [n, ch] floats"""
    rate = int(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=sample_rate', '-of', 'csv=p=0', path],
                              stdout=subprocess.PIPE, check=True).stdout.decode().strip())
    b = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', str(ch), '-f', 'f32le', '-'], stdout=subprocess.PIPE, check=True).stdout
    x = np.frombuffer(b, '<f4').reshape(-1, ch)
    loud = np.nonzero((np.abs(x) >= 10 ** (db / 20)).any(1))[0]
    x = x[loud[0]:loud[-1] + 1]
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, 'x.f32')
        x.astype('<f4').tofile(raw)
        o = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(rate), '-ac', str(ch), '-i', raw, '-ar', '48000', '-f', 'f32le', '-'],
                           stdout=subprocess.PIPE, check=True).stdout
    return np.frombuffer(o, '<f4').reshape(-1, ch).astype(np.float64)


def be16s(b):
    return struct.unpack('>%dh' % (len(b) // 2), b)


def adder_checks(check, out, adder_in):
    sys.path.insert(0, TOOLS)
    import fighter_own_bank as FB
    import fighter_sound as FS
    import minecraft_music as mm
    import minecraft_sound as ms
    ad = os.path.join(out, 'adder')
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(ad, 'manifest.txt'))]
    exe = mm.dspenc()
    try:
        # the C# encoder against tools/dspadpcm (grok.c through dspenc.c), on the same 48 kHz PCM: coefficients, ps, frames
        for kind, f, ch, stem in [r for r in rows if r[0] == 'encode']:
            ch = int(ch)
            pcm = np.fromfile(stem + '.pcm48.s16', '<i2').reshape(-1, ch)
            idsp = open(stem + '.idsp', 'rb').read()
            per = struct.unpack('>I', idsp[0x2C:0x30])[0]
            doff = 0x40 + 0x60 * ch
            for c in range(ch):
                coefs, ps, _lps, _y1, _y2, adpcm = mm.encode(exe, pcm[:, c].copy(), 0)
                h = 0x40 + 0x60 * c
                check('%s ch %d: coefficients = dspenc\'s' % (f, c), idsp[h + 0x1C:h + 0x3C] == coefs)
                check('%s ch %d: ps = dspenc\'s' % (f, c), idsp[h + 0x3E:h + 0x40] == ps)
                if ch == 1:
                    mine = idsp[doff:doff + per]
                else:
                    blocks = np.frombuffer(idsp[doff:doff + per * ch], np.uint8).reshape(-1, ch, 0x10)
                    mine = blocks[:, c, :].tobytes()
                check('%s ch %d: ADPCM frames = dspenc\'s byte for byte (%d bytes)' % (f, c, len(adpcm)),
                      mine[:len(adpcm)] == adpcm and mine[len(adpcm):] == b'\0' * (len(mine) - len(adpcm)))
            # resampling against ffmpeg's (swr) and the decoded IDSP against it: both > 0.99
            ref = ff_pcm(os.path.join(adder_in, f), 48000, ch).astype(np.float64)
            dec = np.fromfile(stem + '.dec.s16', '<i2').reshape(-1, ch).astype(np.float64)
            k = min(len(ref), len(pcm))
            check('%s: 48 kHz length = ffmpeg\'s (%d vs %d)' % (f, len(pcm), len(ref)), abs(len(pcm) - len(ref)) <= 1)
            for c in range(ch):
                r1 = float(np.corrcoef(pcm[:k, c].astype(np.float64), ref[:k, c])[0, 1])
                r2 = float(np.corrcoef(dec[:k, c], ref[:k, c])[0, 1])
                check('%s ch %d: the C# resampling vs ffmpeg\'s, r %.5f > 0.999' % (f, c, r1), r1 > 0.999)
                check('%s ch %d: encoded + decoded vs ffmpeg\'s resampling, r %.5f > 0.99' % (f, c, r2), r2 > 0.99)
        for kind, f, ch, stem in [r for r in rows if r[0] == 'resample']:
            pcm = np.fromfile(stem + '.pcm48.s16', '<i2').astype(np.float64)
            ref = ff_pcm(os.path.join(adder_in, f), 48000, 1)[:, 0].astype(np.float64)
            k = min(len(ref), len(pcm))
            r = float(np.corrcoef(pcm[:k], ref[:k])[0, 1])
            check('%s: 22.05 -> 48 kHz vs ffmpeg\'s, r %.5f > 0.999' % (f, r), r > 0.999)

        # the written banks and table, read with the repo's own tools
        tab = [r for r in rows if r[0] == 'table'][0]
        old_t, new_t, row = FB.Table(open(tab[1], 'rb').read()), FB.Table(open(tab[2], 'rb').read()), int(tab[3])
        check('table (fighter_own_bank.Table): row %d = the old labels + 111, 112, 113' % row,
              new_t.tones(row) == old_t.tones(row) + [111, 112, 113])
        check('table: fighter_own_bank.Table writes it back byte for byte', new_t.data() == open(tab[2], 'rb').read())
        check('table: the other rows the same', all(a == b for i, (a, b) in enumerate(zip(old_t.rows, new_t.rows)) if i != row)
              and len(old_t.rows) == len(new_t.rows))
        check('table: row %d is still bank 2058\'s (fighter_own_bank.Table.row_of)' % row, new_t.row_of(2058) == row)
        srcs = {'snd_se_Gekkouga_AddMono': ('mono44.wav', 1), 'snd_se_Gekkouga_AddStereo': ('stereo44.wav', 2),
                'snd_se_Gekkouga_AddLoop': ('ding.mp3', 1), 'snd_se_Master_Added': ('stereo44.wav', 2)}
        for kind, path, idx, name, ch, loop, vol in [r for r in rows if r[0] == 'tone']:
            idx, ch = int(idx), int(ch)
            data = open(path, 'rb').read()
            secs = mm.sections(data)
            names = [n for n, _b in secs]
            check('%s: sections (minecraft_music.sections) in vanilla\'s order (%s)' % (os.path.basename(path), b' '.join(names).decode()),
                  names in ([b'PROP', b'BINF', b'GRP ', b'DTON', b'TONE', b'JUNK', b'PACK'],
                            [b'PROP', b'BINF', b'GRP ', b'DTON', b'TONE', b'MARK', b'JUNK', b'PACK']))
            bname, bid = FB.binf(data)
            check('%s: BINF (fighter_own_bank.binf) %s %d' % (os.path.basename(path), bname, bid), bname.startswith('snd_se_'))
            _s, tones = ms.tones_of(data)
            check('%s: tone count (fighter_sound.tone_count) = TONE\'s entries (minecraft_sound.tones_of)' % os.path.basename(path),
                  FS.tone_count(data) == len(tones) and len(tones) > idx)
            head, nm, rest = ms.parse_entry(tones[idx])
            check('tone %d (minecraft_sound.parse_entry): its name %s' % (idx, nm), nm == name)
            off, size, v = struct.unpack('<IIf', rest[4:16])
            tail = struct.unpack('<6I', rest[-0x20:-0x08])
            audio = tone_audio(path, idx)
            hd = struct.unpack('>4sI10I', audio[:48])
            n = hd[4]
            check('tone %d: TONE tail (rate, ch, samples, loop) = its IDSP\'s (fighter_own_bank / minecraft_sound set_data)' % idx,
                  tail == (48000, ch, n, 0, n - 1 if loop == '1' else 0, int(loop)) and hd[2] == ch and hd[3] == 48000)
            check('tone %d: volume %s dB' % (idx, vol), abs(v - float(vol)) < 1e-6)
            check('tone %d: PACK offset a multiple of 0x10, size = IDSP\'s' % idx,
                  off % 16 == 0 and size == len(audio) == hd[10] + ch * hd[11])
            pack_at = 24 + 8 * len(secs) + sum(8 + len(b) for _n, b in secs[:-1]) + 8
            check('%s: PACK\'s body at a multiple of 0x10 (0x%X)' % (os.path.basename(path), pack_at), pack_at % 16 == 0)
            y, _rate, _ls, _le = dsp_decode(audio)
            # against the source clip: decoded by ffmpeg at its own rate, trimmed by the same rule (the first / last frame
            # whose peak in any channel reaches -45 dBFS), resampled to 48 kHz by ffmpeg; the same length, lag 0
            src = source_48k(os.path.join(adder_in, srcs[name][0]), ch)
            check('tone %d %s: its length = the trimmed source\'s at 48 kHz (%d vs %d)' % (idx, name, len(y), len(src)), abs(len(y) - len(src)) <= 1)
            for c in range(ch):
                a, b = y[:, c].astype(np.float64), src[:, c]
                k = min(len(a), len(b))
                r = float(np.corrcoef(a[:k], b[:k])[0, 1])
                lags = {l: float(np.corrcoef(a[max(0, l):k + min(0, l)], b[max(0, -l):k - max(0, l)])[0, 1]) for l in (-2, -1, 0, 1, 2)}
                check('tone %d %s ch %d: this file\'s decoder vs the source (ffmpeg), r %.4f > 0.99 at lag 0 (the best)' % (idx, name, c, r),
                      r > 0.99 and max(lags, key=lags.get) == 0)
    finally:
        os.remove(exe)


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) < 5:
        sys.exit(__doc__)
    run, root, game, port, out = [os.path.abspath(x) for x in a[:5]]
    mp3 = sys.argv[sys.argv.index('--mp3') + 1] if '--mp3' in sys.argv else None
    gui = '--gui' in sys.argv
    adder_in = os.path.join(out, 'adder_in') if '--adder' in sys.argv else None
    if adder_in:
        assert mp3, '--adder needs --mp3 (the clips are made from it)'
        make_inputs(mp3, adder_in)
    exe = os.path.join(run, 'SvTest.exe')
    refs = ['-r:' + os.path.join(run, x) for x in ('SALT.dll', 'SM4SHCommand.exe', 'FastColoredTextBox.dll')] + \
           ['-r:%s/%s' % (MONO, x) for x in ('mscorlib.dll', 'System.dll', 'System.Core.dll', 'System.Windows.Forms.dll', 'System.Drawing.dll')]
    subprocess.run(['dotnet', CSC, '-nologo', '-nowarn:1701,1702', '-out:' + exe, '-nostdlib'] + refs +
                   [os.path.join(HERE, 'sound_viewer_test.cs')], check=True)
    cmd = ['mono', exe, os.path.join(run, 'Events.cfg'), root, game, port, out] + (['--gui'] if gui else []) + \
          (['--adder', adder_in] if adder_in else [])
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
    if adder_in:
        adder_checks(check, out, adder_in)
        shutil.rmtree(os.path.join(out, 'adder'), ignore_errors=True)      # the staged / written copies (rebuildable)
        shutil.rmtree(adder_in, ignore_errors=True)
    print('%d python checks; %d failures in all (the C# test\'s count included)' % (oks, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
