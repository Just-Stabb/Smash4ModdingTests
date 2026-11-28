#!/usr/bin/env python3
"""Sounds and name plates (1.3), headless.

  python3 tools/sm4shclonetool/tests/media_test.py VUI_CHR WORK

VUI_CHR: the game's ui/replace/chr (its chrn_11 / chrn_12 / chrn_40 name plates). WORK: scratch + preview pictures.

- the vendored DSP-ADPCM encoder (vendor/dspadpcm.py) gives the same coefficients and frames as the C encoder it was
  ported from (tools/dspadpcm/grok.c, compiled here when a C compiler is found), and decodes to what it encoded;
- IDSP encode / decode (mono and stereo), WAV in (8 / 16 / 24-bit PCM, 32-bit float, stereo mixed down, resampled);
- name plates: for 8 of the game's plates (one-line and two-line names) in each set, the tool's plate of the same
  name (the bundled DFMincho-SU) has the same line count, its lines within 4 % of the plate height of the game's, its
  text centred within 4 % and as wide within 12 % of the plate's width; the outline / shadow in the plate's channels;
  previews old (1.2) / new / the game's side by side in WORK;
- fonts: the default is the bundled DFMincho-SU; a picked font file wins; "game" finds a TrueType font in the data's
  ui/font/ (a UI mod's) and falls back to the bundled one without.
"""
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
from sm4shclonetool import audio as AU  # noqa: E402
from sm4shclonetool import plates as PL  # noqa: E402
from sm4shclonetool import textures as T  # noqa: E402
import dspadpcm  # noqa: E402
import numpy as np  # noqa: E402

FAILS = []
NAMES = [('Mario', 'Mario'), ('Link', 'Link'), ('Kirby', 'Kirby'), ('Duckhunt', 'Duck Hunt'), ('Pacman', 'Pac-Man'),
         ('Szerosuit', 'Zero suit Samus'), ('Captain', 'Captain Falcon'), ('Gamewatch', 'Mr. Game & Watch')]


def check(what, got, want=True):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)), flush=True)
    if not ok:
        FAILS.append(what)


def snr(a, b):
    a, b = np.array(a, float), np.array(b[:len(a)], float)
    return 10 * np.log10((a ** 2).sum() / max(1e-9, ((a - b) ** 2).sum()))


def audio_tests(work):
    random.seed(3)
    pcm = [int(11000 * math.sin(i * 0.031) * math.sin(i * 0.0009) + random.randint(-600, 600)) for i in range(30000)]
    coefs, frames, dec = dspadpcm.encode(pcm)
    src = os.path.join(os.path.dirname(os.path.dirname(TOOL)), 'tools', 'dspadpcm')
    cc = shutil.which('cc') or shutil.which('gcc')
    if cc and os.path.isdir(src):
        tmp = tempfile.mkdtemp(prefix='s4ct_dsp_')
        exe = os.path.join(tmp, 'dspenc')
        subprocess.run([cc, '-O2', '-o', exe, os.path.join(src, 'dspenc.c'), os.path.join(src, 'grok.c'), '-lm'],
                       check=True)
        open(os.path.join(tmp, 'in'), 'wb').write(struct.pack('<%dh' % len(pcm), *pcm))
        subprocess.run([exe, os.path.join(tmp, 'in'), os.path.join(tmp, 'out'), '0'], check=True)
        d = open(os.path.join(tmp, 'out'), 'rb').read()
        check('DSP-ADPCM: the pure-Python encoder = the C encoder (coefficients and %d frames byte for byte)'
              % (len(frames) // 8), (list(struct.unpack('>16h', d[:32])) == coefs, d[40:] == frames), (True, True))
        shutil.rmtree(tmp)
    else:
        print('skip the C encoder comparison (no C compiler / tools/dspadpcm)')
    check('DSP-ADPCM: decode = the encoder\'s own decoded samples; %.1f dB SNR' % snr(pcm, dec),
          (dspadpcm.decode(frames, coefs, len(pcm)) == dec, snr(pcm, dec) > 30), (True, True))
    st = [pcm, [-v for v in pcm]]
    blob = AU.idsp_encode(st, 47999)
    rate, ch = AU.idsp_decode(blob)
    check('IDSP stereo: 2 channels at 47999 Hz decode back (%.1f / %.1f dB)' % (snr(pcm, ch[0]), snr(st[1], ch[1])),
          (rate, len(ch), snr(pcm, ch[0]) > 30, snr(st[1], ch[1]) > 30), (47999, 2, True, True))
    # WAV in: formats
    base = [math.sin(i * 2 * math.pi * 440 / 44100) * 0.5 for i in range(44100)]
    ok = []
    for bits, tag in ((8, 1), (16, 1), (24, 1), (32, 3)):
        p = os.path.join(work, 'w%d.wav' % bits)
        if bits == 8:
            body = bytes(int(128 + v * 127) for v in base for _c in range(2))
        elif bits == 16:
            body = b''.join(struct.pack('<hh', int(v * 32767), int(v * 32767)) for v in base)
        elif bits == 24:
            body = b''.join(int(v * 8388607).to_bytes(3, 'little', signed=True) * 2 for v in base)
        else:
            body = b''.join(struct.pack('<ff', v, v) for v in base)
        fmt = struct.pack('<HHIIHH', tag, 2, 44100, 44100 * 2 * bits // 8, 2 * bits // 8, bits)
        open(p, 'wb').write(b'RIFF' + struct.pack('<I', 4 + 8 + len(fmt) + 8 + len(body)) + b'WAVE' + b'fmt ' +
                            struct.pack('<I', len(fmt)) + fmt + b'data' + struct.pack('<I', len(body)) + body)
        x = AU.read_wav(p)
        want = [math.sin(i * 2 * math.pi * 440 / 48000) * 0.5 * 32767 for i in range(len(x))]
        ok.append((bits, len(x), round(snr(want[100:-100], x[100:-100]))))
    check('WAV in: 8 / 16 / 24-bit and float stereo 44.1 kHz -> mono 48 kHz (samples, SNR dB): %s' % ok,
          all(n == 48000 and s > 25 for _b, n, s in ok), True)


def plate_tests(vchr, work):
    from PIL import Image, ImageDraw, ImageFont
    font = PL.resolve_font(None, 'plate')
    check('fonts: the default plate font is the bundled DFMincho-SU', os.path.basename(font or ''), 'DF_Mincho_SU.ttf')
    other = PL.bundled_font('gothic')
    check('fonts: a picked font file wins', PL.resolve_font(other, 'plate'), other)
    d = tempfile.mkdtemp(prefix='s4ct_font_')
    check('fonts: "game" without a font in the data folder: the bundled one',
          os.path.basename(PL.resolve_font('game', 'plate', [d])), 'DF_Mincho_SU.ttf')
    os.makedirs(os.path.join(d, 'ui', 'font'))
    shutil.copyfile(other, os.path.join(d, 'ui', 'font', 'mod_font.ttf'))
    check('fonts: "game" finds a TrueType font in the data\'s ui/font/', os.path.basename(PL.resolve_font('game', 'plate', [d])),
          'mod_font.ttf')
    shutil.rmtree(d)
    for st in ('chrn_11', 'chrn_12', 'chrn_40'):
        rows, bad = [], []
        for n, title in NAMES:
            p = os.path.join(vchr, st, '%s_%s_01.nut' % (st, n))
            if not os.path.exists(p):
                continue
            van = T.decode(p)
            w, h = van.size
            mine, lines = PL.render(title, st, font, van.size, PL.plate_style(van))
            mv, mm = PL.metrics(van), PL.metrics(mine)
            ok = len(mv['lines']) == len(mm['lines']) and all(
                abs(a[0] - b[0]) <= 0.04 * h and abs(a[1] - b[1]) <= 0.04 * h for a, b in zip(mv['lines'], mm['lines']))
            ok &= abs(mv['centre'] - mm['centre']) <= 0.04 * w
            ok &= abs((mv['fill'][1] - mv['fill'][0]) - (mm['fill'][1] - mm['fill'][0])) <= 0.12 * w
            a = np.asarray(mine.convert('RGBA')).astype(int)
            if (a[:, :, 3] > 250).mean() > 0.98:
                edge = ((a[:, :, 1] > 160) & (a[:, :, 0] < 90)).sum()
            else:
                edge = ((a[:, :, 3] > 200) & (a[:, :, :3].sum(2) < 200)).sum()
            ok &= edge > 0
            if not ok:
                bad.append((n, mv['lines'], mm['lines'], mv['fill'][:2], mm['fill'][:2]))
            rows.append((van, mine, _old_plate(title, van)))
        check('%s: the tool\'s plates match the game\'s %d (lines, height, centre, width, outline)' % (st, len(rows)),
              bad, [])
        if rows:
            W, H = rows[0][0].size
            out = Image.new('RGBA', (3 * W + 16, len(rows) * (H + 4) + 20), (70, 70, 70, 255))
            dr = ImageDraw.Draw(out)
            for i, lab in enumerate(('1.2 (generic sans)', '1.3 (this tool)', 'the game')):
                dr.text((i * (W + 8) + 4, 4), lab, fill=(255, 255, 255, 255))
            for k, (van, mine, old) in enumerate(rows):
                for i, im in enumerate((old, mine, van)):
                    out.paste(im, (i * (W + 8), 20 + k * (H + 4)), im)
            out.save(os.path.join(work, 'plates_%s.png' % st))


def _old_plate(title, van):
    """1.2's plate, for the before / after picture"""
    from PIL import Image, ImageDraw, ImageFont
    w, h = van.size
    text = title.upper()
    pic = Image.new('RGBA', (w, h), (0, 0, 0, 255 if (np.asarray(van)[:, :, 3] > 250).mean() > 0.98 else 0))
    dr = ImageDraw.Draw(pic)
    size, font = max(8, int(h * 0.7)), None
    while size >= 8:
        for name in ('DejaVuSans-Bold.ttf', 'arialbd.ttf'):
            try:
                font = ImageFont.truetype(name, size)
                break
            except Exception:
                font = None
        font = font or ImageFont.load_default()
        box = dr.textbbox((0, 0), text, font=font, stroke_width=max(1, size // 12))
        if box[2] - box[0] <= w * 0.94 and box[3] - box[1] <= h * 0.9:
            break
        size -= 2
    box = dr.textbbox((0, 0), text, font=font, stroke_width=max(1, size // 12))
    dr.text(((w - (box[2] - box[0])) / 2 - box[0], (h - (box[3] - box[1])) / 2 - box[1]), text, font=font,
            fill=(255, 255, 0, 255), stroke_width=max(2, size // 10), stroke_fill=(0, 255, 0, 255))
    return pic


def main():
    vchr, work = sys.argv[1:3]
    os.makedirs(work, exist_ok=True)
    audio_tests(work)
    plate_tests(vchr, work)
    print('\n%d failed' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
