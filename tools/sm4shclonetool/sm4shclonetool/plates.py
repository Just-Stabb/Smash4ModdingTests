"""Name plates (chrn_11, chrn_12, chrn_40, chrn_41: the character's name drawn as a picture) in the game's own style.

Measured on the game's plates (66 characters' chrn_11 / chrn_12 / chrn_40; tests/plates_test.py compares):
- the name in small capitals: a capital letter at the full cap height, a lowercase letter as a capital about 0.68 as
  tall, on one baseline ("Zero suit Samus": Z, S big; ero, suit, amus small), heavy wide serif capitals (the
  DFMincho-SU full-width Latin forms, thickened), letters almost touching;
- one line, or two when the name has a space and would not fit one line without squeezing it past about 85 %
  ("Captain / Falcon", "Zero suit / Samus", "Mr. Game / & Watch"; "Duck Hunt", "Pac-Man" one line), each line squeezed
  horizontally to the plate's text width when wider, centred on the plate's text centre;
- an outline around the letters and a drop shadow down-right in the outline's colour;
- the colours / channels the plate already has: chrn_11 / chrn_40 opaque black with yellow letters (red + green) and a
  green outline / shadow (the screen colours them by channel); chrn_12 transparent with white letters and a near-black
  outline / shadow. The clone's plate takes its colours from its base's plate.
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(os.path.dirname(HERE), 'fonts')
BUNDLED = {'mincho': 'DF_Mincho_SU.ttf', 'gothic': 'DF_Gothic_SU.ttf'}
TEXT_TYPES = ('plate', 'title', 'other')        # the GUI's per-text-type font choice
DEFAULT_FONT = {'plate': 'mincho', 'title': 'mincho', 'other': 'gothic'}

# per plate set, in pixels of the game's plate size (w, h): text centre x, text width, one line (top, bottom of the
# capitals), two lines ((top, bottom), (top, bottom)), outline, shadow offset (x, y). Measured from the game's plates.
GEOMETRY = {
    'chrn_11': {'size': (512, 128), 'cx': 151, 'width': 286, 'one': (46, 97), 'two': ((22, 65), (68, 111)),
                'outline': 5, 'shadow': (6, 9), 'small_caps': False},
    'chrn_12': {'size': (256, 128), 'cx': 127, 'width': 220, 'one': (39, 81), 'two': ((22, 59), (62, 99)),
                'outline': 3, 'shadow': (3, 5)},
    'chrn_40': {'size': (1024, 512), 'cx': 318, 'width': 612, 'one': (111, 231), 'two': ((62, 170), (176, 281)),
                'outline': 9, 'shadow': (8, 14)},
}
NARROW = '-'                # signs drawn with the narrow form (the wide hyphen is a long dash)
SMALL_SIGNS = '&'           # signs drawn at the small capitals' height (the game's '& Watch')
SMALL_CAPS = 0.68           # a small capital's height / a capital's
GAP = 0.035                 # space between letters / cap height
SPACE = 0.30                # a word space / cap height
TWO_LINES_FROM = 12         # a name with a space and this many characters or more goes on two lines (the game's
                            # plates: "Captain Falcon", "Zero Suit Samus", "Mr. Game & Watch" two; "Master Hand", "Meta
                            # Knight", "Little Mac" one; "Donkey Kong" two is the one exception); a "\n" in the title forces it
BOLD = 0.045                # extra weight (dilation) / cap height: the game's letters are heavier than the font's


def bundled_font(kind='mincho'):
    p = os.path.join(FONTS_DIR, BUNDLED.get(kind, kind))
    return p if os.path.exists(p) else None


def game_fonts(data_dirs):
    """TrueType / OpenType fonts in the creator's data (a UI mod may ship one under ui/font/). The game's own fonts are
    Lumen .brf resources (ui/font/resource/static/Gothic.brf, Folk.brf: bitmap fonts the tool can't draw with)"""
    out = []
    for d in data_dirs:
        f = os.path.join(d or '', 'ui', 'font')
        if os.path.isdir(f):
            for root, _ds, fs in os.walk(f):
                out += [os.path.join(root, x) for x in sorted(fs) if x.lower().endswith(('.ttf', '.otf', '.ttc'))]
    return out


def resolve_font(choice=None, kind='plate', data_dirs=()):
    """the font file for a text type: choice = a path (the creator's pick), 'game' (a font in the data folder),
    'mincho' / 'gothic' (bundled) or None (the type's default). Falls back bundled -> any system bold font."""
    if choice and choice not in ('game', 'mincho', 'gothic') and os.path.exists(choice):
        return choice
    if choice == 'game':
        g = game_fonts(data_dirs)
        if g:
            return g[0]
    p = bundled_font(choice if choice in BUNDLED else DEFAULT_FONT.get(kind, 'mincho'))
    if p:
        return p
    for name in ('DejaVuSerif-Bold.ttf', 'timesbd.ttf', 'DejaVuSans-Bold.ttf', 'arialbd.ttf'):
        try:
            ImageFont.truetype(name, 10)
            return name
        except Exception:
            pass
    return None


def _wide(ch):
    """the full-width form of an ASCII letter / sign (the Japanese fonts' wide Latin, the game's letter shapes)"""
    o = ord(ch)
    if ch in NARROW:
        return ch
    return chr(o - 0x21 + 0xFF01) if 0x21 <= o <= 0x7E else ch


def _glyph(font_path, ch, cap):
    """(mask, ink box height) of one character drawn so its capital height is cap pixels"""
    probe = ImageFont.truetype(font_path, 200)
    box = probe.getbbox(_wide('H'))
    hh = box[3] - box[1]
    size = max(4, int(round(200 * cap / max(1, hh))))
    f = ImageFont.truetype(font_path, size)
    g = _wide(ch) if f.getbbox(_wide(ch)) != f.getbbox('￿') else ch
    bb = f.getbbox(g)
    im = Image.new('L', (bb[2] - bb[0] + 4, size * 2), 0)
    ImageDraw.Draw(im).text((2 - bb[0], 0), g, font=f, fill=255)
    hb = f.getbbox(_wide('H'))
    return im, hb[3]                      # the baseline: the capital H's bottom in the drawn image


def line_mask(text, font_path, cap, scale=4, small_caps=True):
    """one line in small capitals at cap height (drawn scale x larger): (mask, baseline y)"""
    big = cap * scale
    parts = []
    for ch in text:
        if ch == ' ':
            parts.append(None)
            continue
        small = (ch.islower() or ch in SMALL_SIGNS) and small_caps
        h = big * SMALL_CAPS if small else big
        im, base = _glyph(font_path, ch.upper(), h)
        a = np.array(im)
        xs = np.nonzero(a.max(0) > 0)[0]
        if len(xs):
            a = a[:, xs.min():xs.max() + 1]
        parts.append((a, base))
    above = max([b for p in parts if p for _a, b in [p]] + [1])
    below = max([a.shape[0] - b for p in parts if p for a, b in [p]] + [1])
    gap, space = int(GAP * big), int(SPACE * big)
    width = sum(space if p is None else p[0].shape[1] + gap for p in parts)
    out = np.zeros((above + below, max(1, width)), np.uint8)
    x = 0
    for p in parts:
        if p is None:
            x += space
            continue
        a, b = p
        y = above - b
        out[y:y + a.shape[0], x:x + a.shape[1]] = np.maximum(out[y:y + a.shape[0], x:x + a.shape[1]], a)
        x += a.shape[1] + gap
    ys = np.nonzero(out.max(1) > 0)[0]
    xs = np.nonzero(out.max(0) > 0)[0]
    out = out[:, xs.min():xs.max() + 1] if len(xs) else out
    return out, above, (ys.min() if len(ys) else 0)


def split_lines(text, lines=None):
    """[lines]: the title's own line break, else two lines from TWO_LINES_FROM characters with a space (lines=1 / 2
    forces one or two)"""
    if '\n' in text:
        return [t.strip() for t in text.split('\n', 1)]
    words = text.split()
    if len(words) < 2 or lines == 1 or (lines != 2 and len(text) < TWO_LINES_FROM):
        return [text]
    best = None
    for i in range(1, len(words)):
        a, b = ' '.join(words[:i]), ' '.join(words[i:])
        d = abs(len(a) - len(b))
        if best is None or d < best[0]:
            best = (d, [a, b])
    return best[1]


def text_mask(text, font_path, set_name, size=None, lines=None):
    """the letters' coverage (float 0-1) on the plate, the game's layout for that set"""
    geo = dict(GEOMETRY.get(set_name) or GEOMETRY['chrn_40'])
    gw, gh = geo['size']
    w, h = size or (gw, gh)
    sx, sy = w / gw, h / gh
    scale = 4
    lines = split_lines(text, lines)
    boxes = [geo['one']] if len(lines) == 1 else list(geo['two'])
    canvas = Image.new('L', (w * scale, h * scale), 0)
    bold = int(round(BOLD * (geo['one'][1] - geo['one'][0]) * sy * scale)) | 1
    pad = (min(bold, 15) - 1) / 2                      # the dilation grows each letter by this (drawn pixels)
    for line, (top, bot) in zip(lines, boxes):
        hh = (bot - top + 1) * sy * scale - 2 * pad
        m, base, _t = line_mask(line, font_path, hh / scale, scale, geo.get('small_caps', True))
        ys = np.nonzero(m.max(1) > 0)[0]
        m = m[ys.min():ys.max() + 1]
        lw = min(m.shape[1] * hh / max(1, m.shape[0]), geo['width'] * sx * scale - 2 * pad)
        im = Image.fromarray(m).resize((max(1, int(lw)), max(1, int(round(hh)))), Image.LANCZOS)
        x = int(geo['cx'] * sx * scale - im.size[0] / 2)
        canvas.paste(im, (x, int(top * sy * scale + pad)), im)
    if bold > 1:
        canvas = canvas.filter(ImageFilter.MaxFilter(min(bold, 15)))
    canvas = canvas.resize((w, h), Image.LANCZOS)
    return np.asarray(canvas, np.float32) / 255.0, geo, (sx, sy), lines


def _dilate(m, r):
    if r <= 0:
        return m
    im = Image.fromarray((m * 255).astype(np.uint8))
    k = 2 * int(r) + 1
    while k > 1:                         # MaxFilter takes odd sizes; big outlines in steps
        step = min(k, 9)
        step -= 1 - step % 2
        im = im.filter(ImageFilter.MaxFilter(step))
        k -= step - 1
    return np.asarray(im, np.float32) / 255.0


def _shift(m, dx, dy):
    out = np.zeros_like(m)
    h, w = m.shape
    out[max(0, dy):h, max(0, dx):w] = m[0:h - max(0, dy), 0:w - max(0, dx)]
    return out


def plate_style(img):
    """the base plate's colours: (background RGBA, fill RGB, outline RGB, outline alpha)"""
    a = np.asarray(img.convert('RGBA')).astype(int)
    opaque = (a[:, :, 3] > 250).mean() > 0.98
    if opaque:
        bright = a[:, :, :3].sum(2)
        fill = a[(a[:, :, 0] > 160) & (a[:, :, 1] > 160)]
        out = a[(a[:, :, 1] > 160) & (a[:, :, 0] < 90)]
        bg = (0, 0, 0, 255)
        f = tuple(int(v) for v in np.median(fill[:, :3], 0)) if len(fill) else (255, 255, 0)
        o = tuple(int(v) for v in np.median(out[:, :3], 0)) if len(out) else (0, 255, 0)
        if not len(fill) and bright.max() < 30:
            f, o = (255, 255, 0), (0, 255, 0)
        return bg, f, o, 255
    vis = a[a[:, :, 3] > 200]
    f = tuple(int(v) for v in np.median(vis[vis[:, :3].sum(1) > 600][:, :3], 0)) if (vis[:, :3].sum(1) > 600).any() \
        else (255, 255, 255)
    dark = vis[vis[:, :3].sum(1) < 200]
    o = tuple(int(v) for v in np.median(dark[:, :3], 0)) if len(dark) else (24, 24, 24)
    return (0, 0, 0, 0), f, o, 255


def render(text, set_name, font_path, size=None, style=None, lines=None):
    """the plate picture (RGBA) of text for a plate set; style = plate_style(base plate) (else the set's usual)"""
    m, geo, (sx, sy), lines = text_mask(text, font_path, set_name, size, lines)
    h, w = m.shape
    if style is None:
        style = ((0, 0, 0, 0), (255, 255, 255), (24, 24, 24), 255) if set_name == 'chrn_12' else \
            ((0, 0, 0, 255), (255, 255, 0), (0, 255, 0), 255)
    bg, fill, outc, oa = style
    k = (sx + sy) / 2
    o = _dilate(m, geo['outline'] * k)
    sh = _shift(o, int(round(geo['shadow'][0] * sx)), int(round(geo['shadow'][1] * sy)))
    edge = np.maximum(o, sh)
    out = np.zeros((h, w, 4), np.float32)
    out[:] = bg
    for cov, col, alpha in ((edge, outc, oa), (m, fill, 255)):
        c = cov[:, :, None]
        out[:, :, :3] = out[:, :, :3] * (1 - c) + np.array(col, np.float32) * c
        out[:, :, 3] = out[:, :, 3] * (1 - cov) + alpha * cov
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8), 'RGBA'), lines


def metrics(img, set_name=None):
    """layout of a plate picture: {'lines': [(top, bottom)], 'fill': (x0, x1, y0, y1), 'centre': x} of its letters"""
    a = np.asarray(img.convert('RGBA')).astype(int)
    if (a[:, :, 3] > 250).mean() > 0.98:
        fill = (a[:, :, 0] > 128) & (a[:, :, 1] > 128)
    else:
        fill = (a[:, :, 0] > 128) & (a[:, :, 3] > 128)
    ys, xs = np.nonzero(fill)
    if not len(xs):
        return None
    rows = fill.any(1)
    lines, y = [], 0
    while y < len(rows):
        if rows[y]:
            s = y
            while y < len(rows) and rows[y]:
                y += 1
            if y - s > 3:
                lines.append((s, y - 1))
        y += 1
    return {'lines': lines, 'fill': (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())),
            'centre': (xs.min() + xs.max()) / 2}
