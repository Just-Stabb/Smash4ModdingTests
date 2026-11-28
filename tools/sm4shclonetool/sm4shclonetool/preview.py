"""Character select (CSS) and stage select (SSS) previews, drawn from the creator's files.

CSS: the entries in the game's order (roster.css_entries: first sort key, DLC after), placed where the layout puts
face_001 ... face_N for N entries: the UI folder's lumen/chara/chara.lm frame num_<N> (the game shows that frame,
0x028BEE20, and binds the faces in list order, 0x028BE920), read with tools/chara_layout.py. Without a chara.lm the
grid is approximated (rows of 12). Each face is the character's grid icon (chr_10 by default; a UI profile can name
another set), else a name tile.

SSS: page 1 / page 2 (the DLC page) in stage-select order (+0x20), 8 columns, the stage_10 icons (page 2: append
stage_13), else name tiles. The game's stage-select layout file is not read (approximated grid).

UI profile (optional): <UI folder>/sm4shclonetool_ui.json
  {"css_layout": "lumen/chara/chara.lm", "grid_icon": ["chr_10", "chr_00"], "icon_size": [124, 124],
   "portrait_sets": [...], "stage_icon": ["stage_10"]}
"""
import json
import math
import os

from . import _paths  # noqa: F401
from . import roster as R
from . import textures as T

W, H = 1280, 720
PROFILE = 'sm4shclonetool_ui.json'
DEFAULT_PROFILE = {'css_layout': 'lumen/chara/chara.lm', 'grid_icon': ['chr_10', 'chr_00', 'chr_13'],
                   'icon_size': [116, 116], 'stage_icon': ['stage_10', 'stage_00'], 'portrait_sets': None}


def profile(ui_dir):
    p = dict(DEFAULT_PROFILE)
    f = os.path.join(ui_dir or '', PROFILE)
    if ui_dir and os.path.exists(f):
        try:
            p.update(json.load(open(f)))
            p['_file'] = f
        except Exception as e:
            p['_error'] = '%s: %s' % (f, e)
    return p


def lm_layout(path, count):
    """{face number: (x, y, scale x, scale y)} of chara.lm's frame num_<count> (stage coordinates, origin at the
    centre), and a note; None when the file has no such frame"""
    import chara_layout as cl
    lm = cl.Lm(open(path, 'rb').read())
    frames, labels = lm.frames()
    want = 'num_%03d' % count
    fi = next((f for f, name in labels.items() if name == want), None)
    if fi is None:
        return None, 'chara.lm has no frame %s' % want
    states = lm.simulate()
    out = {}
    for n, (_d, e) in cl.faces(states[fi]).items():
        m = e['m'] or (1, 0, 0, 1, 0, 0)
        out[n] = (m[4], m[5], m[0], m[3])
    return out, 'chara.lm frame %s' % want


def check_layout(pos, count):
    """problems with a layout for `count` entries: missing faces, two faces on one place"""
    probs = []
    missing = [n for n in range(1, count + 1) if n not in pos]
    if missing:
        probs.append('no place for face_%03d' % missing[0] + (' (+%d more)' % (len(missing) - 1) if len(missing) > 1 else ''))
    seen = {}
    for n in range(1, count + 1):
        if n in pos:
            k = (round(pos[n][0]), round(pos[n][1]))
            if k in seen:
                probs.append('face_%03d and face_%03d overlap' % (seen[k], n))
                break
            seen[k] = n
    return probs


def grid_layout(count, cols=12):
    rows = math.ceil(count / cols)
    out = {}
    dx, dy = 130.0, 130.0
    for i in range(count):
        r, c = divmod(i, cols)
        n_in = min(cols, count - r * cols)
        x = (c - (n_in - 1) / 2.0) * dx
        y = (r - (rows - 1) / 2.0) * dy - 60
        out[i + 1] = (x, y, 1.0, 1.0)
    return out


def css_layout(ui_dir, count, prof=None):
    prof = prof or profile(ui_dir)
    p = os.path.join(ui_dir or '', prof['css_layout'])
    if ui_dir and os.path.exists(p):
        try:
            pos, note = lm_layout(p, count)
            if pos:
                return pos, note, check_layout(pos, count), True
            return grid_layout(count), note + '; approximated grid', [note], False
        except Exception as e:  # a layout the reader doesn't understand
            return grid_layout(count), 'chara.lm unreadable (%s); approximated grid' % e, [str(e)], False
    return grid_layout(count), 'no %s in the UI folder: approximated grid (the vanilla layout file is not ' \
                               'shipped with the tool)' % prof['css_layout'], [], False


def _font(size):
    from PIL import ImageFont
    for f in ('DejaVuSans-Bold.ttf', 'arialbd.ttf', 'Arial Bold.ttf', 'DejaVuSans.ttf', 'arial.ttf'):
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _tile(img, box, icon, label, highlight, colour):
    from PIL import ImageDraw
    x0, y0, x1, y1 = [int(v) for v in box]
    d = ImageDraw.Draw(img)
    w, h = max(4, x1 - x0), max(4, y1 - y0)
    if icon is not None:
        ic = icon.copy()
        ic.thumbnail((w, h))
        img.alpha_composite(ic, (x0 + (w - ic.width) // 2, y0 + (h - ic.height) // 2))
    else:
        d.rectangle(box, fill=colour, outline=(20, 20, 30, 255))
        f = _font(max(9, min(15, w // 7)))
        txt = label[:12]
        tw = d.textlength(txt, font=f)
        d.text((x0 + (w - tw) / 2, y0 + h / 2 - 7), txt, fill=(240, 240, 240, 255), font=f)
    if highlight:
        for k in range(4):
            d.rectangle((x0 - 3 - k, y0 - 3 - k, x1 + 3 + k, y1 + 3 + k), outline=(255, 200, 0, 255))


def render_css(param_dirs, ui_dirs, reg, highlight=(), out=None, prof=None, title=None):
    """the CSS preview as a PIL image (and saved to out); returns (image, info)"""
    from PIL import Image, ImageDraw
    ui_main = next((d for d in ui_dirs if d and os.path.isdir(d)), None)
    layout_dir = next((d for d in ui_dirs if d and os.path.exists(os.path.join(d, (prof or profile(d))['css_layout']))),
                      ui_main)
    prof = prof or profile(layout_dir)
    ents = R.css_entries(param_dirs, reg)
    n = len(ents)
    pos, note, probs, real = css_layout(layout_dir, n, prof)
    img = Image.new('RGBA', (W, H), (34, 40, 64, 255))
    d = ImageDraw.Draw(img)
    xs = [p[0] for p in pos.values()] or [0]
    ys = [p[1] for p in pos.values()] or [0]
    iw, ih = prof['icon_size']
    span_x = (max(xs) - min(xs)) + iw
    span_y = (max(ys) - min(ys)) + ih
    s = min((W - 40) / max(span_x, 1), (H - 120) / max(span_y, 1))
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    for i, e in enumerate(ents, 1):
        if i not in pos:
            continue
        x, y, sx, sy = pos[i]
        w, h = iw * abs(sx) * s, ih * abs(sy) * s
        px, py = W / 2 + (x - cx) * s, (H - 80) / 2 + 20 + (y - cy) * s
        icon = None
        p = T.find_icon(ui_dirs, prof['grid_icon'], e['ui_name'])
        if p:
            icon = T.decode(p)
        col = (200, 120, 40, 255) if e['clone'] else (70, 80, 110, 255)
        _tile(img, (px - w / 2, py - h / 2, px + w / 2, py + h / 2), icon, e['ui_name'],
              e['id'] in highlight, col)
    f = _font(18)
    d.text((16, H - 58), title or 'Character select preview: %d entries' % n, fill=(255, 255, 255, 255), font=f)
    d.text((16, H - 32), note + ('; ' + '; '.join(probs) if probs else ''), fill=(200, 210, 230, 255), font=_font(13))
    if out:
        img.convert('RGB').save(out)
    return img, {'count': n, 'note': note, 'problems': probs, 'real_layout': real,
                 'order': [e['id'] for e in ents], 'slot': {e['id']: i for i, e in enumerate(ents, 1)}}


def render_sss(param_dirs, ui_dirs, reg, highlight=(), out=None, prof=None, cols=8):
    from PIL import Image, ImageDraw
    prof = prof or profile(next((d for d in ui_dirs if d), None))
    pages = R.sss_pages(param_dirs, reg)
    img = Image.new('RGBA', (W, H), (30, 52, 44, 255))
    d = ImageDraw.Draw(img)
    pw = (W - 60) / 2
    tw = pw / cols - 6
    th = tw * 0.62
    for pi, p in enumerate((1, 2)):
        x0 = 20 + pi * (pw + 20)
        d.text((x0, 14), 'Page %d (%d stages)' % (p, len(pages[p])), fill=(255, 255, 255, 255), font=_font(18))
        for i, s in enumerate(pages[p]):
            r, c = divmod(i, cols)
            bx, by = x0 + c * (tw + 6), 48 + r * (th + 8)
            sets = prof['stage_icon'] if p == 1 else ['stage_13'] + prof['stage_icon']
            ip = T.find_icon(ui_dirs, sets, s['name'])
            icon = T.decode(ip) if ip else None
            col = (200, 120, 40, 255) if s['clone'] else (60, 90, 80, 255)
            _tile(img, (bx, by, bx + tw, by + th), icon, s['name'], s['id'] in highlight, col)
    d.text((16, H - 32), 'Stage select preview: approximated grid (8 columns), stage-select order', fill=(200, 230, 210, 255),
           font=_font(13))
    if out:
        img.convert('RGB').save(out)
    return img, {'pages': {p: [s['id'] for s in v] for p, v in pages.items()}}
