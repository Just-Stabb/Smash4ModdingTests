#!/usr/bin/env python3
"""Smash Run button in Games & More (docs/games-and-more-menu.md), built on the user's own menu files:

  python3 tools/smashrun_menu.py OTHER_DIR MENU_MSBT BUTTON_SEQ IN.rpx OUT [--x 1460 --y 496]

OTHER_DIR: the installed ui/lumen/other (other.lm, texlist.lst, img-0000N.nut); MENU_MSBT: the installed
ui/message/menu.msbt; BUTTON_SEQ: param/ui/ui_button_sequence.bin; IN.rpx: the current executable. Writes
OUT/ui/lumen/other/*, OUT/ui/message/menu.msbt, OUT/param/ui/ui_button_sequence.bin, OUT/code/cross_f.rpx.

- Layout (the user's movie: a UI mod's Games & More with btn_01..07 as their own sprites and btn_08 an empty
  shape parked at x 5000): btn_08 becomes a copy of the Group button (btn_04, sprite 151) at (x, y) on the empty
  right side. Only the sprites on the paths to its icon and title are copied (anim, base, bg, icon, txt_mc,
  txt_sel_mc, btn_text_n); the frame / colour / selection-animation pieces stay shared. New shapes: the title
  "Smash Run" (atlas 3, BC5 luminance + alpha, drawn like the movie's titles: black, white outline and offset
  white shadow; Inter Black at the titles' cap height) and a star icon (Smash Run's icon on the 3DS menu; atlas 0,
  BC4) where the Group icon sits; both in atlas space no shape samples and no texel uses. New characters get ids after the old ones and the root sprite moves to the new
  last id (F00C words 3 / 5 keep naming it); F00D's shape / sprite counts follow. The hit shape 4xm_08 is moved
  over the button like the others' 4xm_NN.
- Native (cave at 0x04B7D000, stage_slot_cave.py's space after its code): the Games & More button list
  (0x02C8C280) gets an 8th entry through 0x029ABC68(this, button 8, enabled 1, result 7, shown 1, id 115) at its
  end (0x02C8C324), and result 7 (a spare case of page 16's switch, 0x0218BA0C) posts menu key 0x31 (Training)
  instead of 0x5B: the button starts Training's character select (step 1: Smash Run Field with no CPUs; the
  enemies come from tools/smashrun_field_cave.py).
- ui_button_sequence.bin: entry id 115 [115, 8, 3, 1, 0, 0, 8, -1, 0 x 6] (msbt MmenOther_8, button 8), and page
  16 (MmenOther_) lists 8 ids. menu.msbt: MmenOther_8 "Smash Run", MmenOther_8h its help line.
"""
import argparse
import os
import shutil
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chara_layout as cl  # noqa: E402
import flx  # noqa: E402
import msbt  # noqa: E402
import nut  # noqa: E402
import s3ds_ui as su  # noqa: E402
from ppcasm import Asm  # noqa: E402

GROUP_BTN = 151                 # btn_04 (Group) in the user's other.lm
TEXT_SHAPE, ICON_SHAPE = 145, 140
FONT = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
TITLE = 'Smash Run'
HELP = 'Battle the enemies of Smash Run on its own field!'
BUTTON_ID, MSBT_N, RESULT = 115, 8, 7
TITLE_AT = (420, 812)           # atlas 3 (1024x1024): no shape samples there, no texels
TITLE_SIZE = (537, 99)          # the Group title's region (main_txt_world)
STAR_AT, STAR_SIZE = (1612, 4), 120     # atlas 0 (2048x2048): no shape samples there, no texels
CAVE = 0x04B7D000
LIMIT = 0x04B7E000
LIST_END = 0x02C8C324           # lwz r0, 0x14(r1) (the button list's epilogue)
LIST_END_WORD = 0x80010014
SET_BUTTON = 0x029ABC68         # (this, button number, enabled, result, shown, id)
KEY_SITE = 0x0218BA10           # li r4, 0x5B (result 7's menu key)
KEY_WORD = 0x3880005B
TRAINING_KEY = 0x31


# ---------------------------------------------------------------- art
def title_image():
    """luminance, alpha [h, w] of TITLE in the movie's title style, laid out as the Group title's region"""
    from PIL import Image, ImageDraw, ImageFont
    w, h = TITLE_SIZE
    cap, x0, top, big = 53, 30, 5, 4
    fs = 10
    while True:
        bb = ImageFont.truetype(FONT, fs).getbbox('H')
        if bb[3] - bb[1] >= cap:
            break
        fs += 1
    f = ImageFont.truetype(FONT, fs * big)
    oy = f.getbbox('H')[1]

    def layer(sw, off):
        im = Image.new('L', (w * big, h * big), 0)
        ImageDraw.Draw(im).text(((x0 + off) * big, (top + off) * big - oy), TITLE, font=f, fill=255,
                                stroke_width=sw * big, stroke_fill=255)
        return np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255
    alpha = np.maximum(layer(4, 4), layer(5, 0))
    core = layer(1, 0)
    lum = 1 - core
    return (np.clip(lum, 0, 1) * 255).astype(np.uint8), (np.clip(alpha, 0, 1) * 255).astype(np.uint8)


def star_image(size=STAR_SIZE, points=5, inner=0.48, round_px=6):
    """alpha [size, size]: a rounded five-point star (the 3DS menu's Smash Run icon), drawn at 4x"""
    from PIL import Image, ImageDraw, ImageFilter
    big = 4
    s = size * big
    c, r = s / 2, s * 0.47
    pts = []
    for i in range(points * 2):
        a = -np.pi / 2 + i * np.pi / points
        rr = r if i % 2 == 0 else r * inner
        pts.append((c + rr * np.cos(a), c + rr * np.sin(a) + s * 0.03))
    im = Image.new('L', (s, s), 0)
    ImageDraw.Draw(im).polygon(pts, fill=255)
    # round the tips: blur and re-threshold
    im = im.filter(ImageFilter.GaussianBlur(round_px * big / 2)).point(lambda v: 255 if v > 128 else 0)
    return np.asarray(im.resize((size, size), Image.LANCZOS))


def put_bc5(path, at, lum, alpha):
    d, ts = nut.load(path)
    t = ts[0]
    img = nut.decode(d, t)
    x, y = at
    h, w = lum.shape
    img[y:y + h, x:x + w, 0] = lum
    img[y:y + h, x:x + w, 1] = alpha
    return nut.replace(d, t, img), (t.w, t.h)


def put_bc4(path, at, alpha):
    d, ts = nut.load(path)
    t = ts[0]
    img = nut.decode(d, t)
    x, y = at
    h, w = alpha.shape
    img[y:y + h, x:x + w, 0] = alpha
    return nut.replace(d, t, img), (t.w, t.h)


# ---------------------------------------------------------------- the movie
def sprite_range(lm, cid):
    T = lm.tags
    i = next(k for k, (t, b) in enumerate(T) if t == cl.T_SPRITE and cl.words(b)[0] == cid)
    j = i + 1
    while j < len(T) and T[j][0] not in (cl.T_SPRITE, cl.T_END, 0xF022, 0x25):
        j += 1
    return i, j


def shape_range(lm, cid):
    T = lm.tags
    i = next(k for k, (t, b) in enumerate(T) if t == 0xF022 and cl.words(b)[0] == cid)
    j = i + 1
    while j < len(T) and T[j][0] == 0xF024:
        j += 1
    return i, j


def children(lm, cid):
    i, j = sprite_range(lm, cid)
    out = []
    for t, b in lm.tags[i + 1:j]:
        if t == cl.T_PLACE:
            c = cl.words(b)[0]
            if c != cl.NONE and c not in out:
                out.append(c)
    return out


def paths_to(lm, root, targets):
    """sprites under root that contain (transitively) one of targets"""
    memo = {}

    def has(c):
        if c in memo:
            return memo[c]
        memo[c] = False
        try:
            kids = children(lm, c)
        except StopIteration:
            return False
        memo[c] = any(k in targets or has(k) for k in kids)
        return memo[c]
    out, todo = [], [root]
    while todo:
        c = todo.pop()
        if c not in out and has(c):
            out.append(c)
            todo += [k for k in children(lm, c) if k not in targets]
    return out


def graphic(atlas, fill, verts, idx):
    b = struct.pack('>IHHI', atlas, fill, len(verts), len(idx))
    b += b''.join(struct.pack('>4f', *v) for v in verts)
    b += struct.pack('>%dH' % len(idx), *idx)
    return bytearray(b + b'\0' * (-len(b) % 4))


def rect_graphic(atlas, fill, x0, y0, x1, y1, u0, v0, u1, v1):
    return graphic(atlas, fill, [(x0, y1, u0, v1), (x0, y0, u0, v0), (x1, y0, u1, v0), (x1, y1, u1, v1)],
                   [0, 1, 2, 0, 2, 3])


def edit_movie(lm, atlas_sizes, x, y, icon_box):
    T = lm.tags
    sy = lm.sy
    copy = paths_to(lm, GROUP_BTN, {TEXT_SHAPE, ICON_SHAPE})
    assert GROUP_BTN in copy
    ci, ra, rb = su.lm_root(lm)
    root = cl.words(T[ci][1])[3]
    ids = sorted({cl.words(b)[0] for t, b in T if t in (cl.T_SPRITE, 0xF022, 0x25)})
    nxt = max(ids) + 1
    remap = {}
    for c in copy + [TEXT_SHAPE, ICON_SHAPE]:
        remap[c] = nxt
        nxt += 1
    new_root = nxt
    new_tags = []
    # shapes: the title and the icon
    for old, (atlas, (gx0, gy0, gx1, gy1), (u0, v0, u1, v1)) in (
            (TEXT_SHAPE, title_geom(lm, atlas_sizes)), (ICON_SHAPE, icon_box)):
        i, j = shape_range(lm, old)
        w = cl.words(T[i][1])
        w[0], w[4] = remap[old], 1
        new_tags.append([0xF022, cl.pack(w)])
        new_tags.append([0xF024, rect_graphic(atlas, 0x41, gx0, gy0, gx1, gy1, u0, v0, u1, v1)])
    # sprites on the paths, children remapped
    for c in reversed(copy):            # children first
        i, j = sprite_range(lm, c)
        for k in range(i, j):
            t, b = T[k]
            b = bytearray(b)
            w = cl.words(b)
            if k == i:
                w[0] = remap[c]
                b = cl.pack(w)
            elif t == cl.T_PLACE and w[0] in remap:
                w[0] = remap[w[0]]
                b = cl.pack(w)
            new_tags.append([t, b])
    # btn_08: the copy, on the right; 4xm_08 over it
    btn8 = sy.index('btn_08')
    hit8 = sy.index('4xm_08')
    pos_tag = T[lm.ti[cl.T_POSITIONS]]
    pos_i = cl.append_rows(pos_tag, [(x, y)], 2)[0]
    xf_tag = T[lm.ti[cl.T_TRANSFORMS]]
    w_btn, h_btn = 870.0, 200.0
    xf_i = cl.append_rows(xf_tag, [(w_btn / 32, 0.0, 0.0, h_btn / 32, x, y)], 6)[0]
    n_btn = n_hit = 0
    for k in range(ra + 1, rb):
        t, b = T[k]
        if t != cl.T_PLACE:
            continue
        w = cl.words(b)
        if w[3] == btn8:
            w[0] = remap[GROUP_BTN]
            w[7] = cl.POS_FLAG | pos_i
            n_btn += 1
        elif w[3] == hit8:
            w[7] = xf_i
            n_hit += 1
        else:
            continue
        T[k][1] = cl.pack(w)
    assert n_btn and n_hit, (n_btn, n_hit)
    # the root keeps being the last character
    rw = cl.words(T[ra][1])
    rw[0] = new_root
    T[ra][1] = cl.pack(rw)
    cw = cl.words(T[ci][1])
    assert cw[3] == root and cw[5] == root, cw
    cw[3] = cw[5] = new_root
    T[ci][1] = cl.pack(cw)
    di = lm.ti[0xF00D]
    dw = cl.words(T[di][1])
    dw[0] += 2
    dw[2] += len(copy)
    T[di][1] = cl.pack(dw)
    # definitions before the root's
    lm.tags[ra:ra] = new_tags
    lm.ti = {t: i for i, (t, _) in reversed(list(enumerate(lm.tags)))}
    return remap, new_root, copy


def title_geom(lm, atlas_sizes):
    """the Group title shape's quad, its UVs moved to the new title's region (same size: same layout)"""
    i, j = shape_range(lm, TEXT_SHAPE)
    b = lm.tags[i + 1][1]
    atlas = struct.unpack('>I', b[:4])[0]
    nv = struct.unpack('>H', b[6:8])[0]
    v = np.array(struct.unpack('>%df' % (4 * nv), b[12:12 + 16 * nv])).reshape(nv, 4)
    aw, ah = atlas_sizes[atlas]
    u0, v0 = TITLE_AT[0] / aw, TITLE_AT[1] / ah
    u1, v1 = (TITLE_AT[0] + TITLE_SIZE[0]) / aw, (TITLE_AT[1] + TITLE_SIZE[1]) / ah
    return atlas, (v[:, 0].min(), v[:, 1].min(), v[:, 0].max(), v[:, 1].max()), (u0, v0, u1, v1)


def icon_geom(lm, other_dir, atlas_sizes):
    """where the Group icon is drawn (its opaque pixels inside shape 140's quad) -> a square of that height
    around its centre, mapped to the star"""
    i, j = shape_range(lm, ICON_SHAPE)
    b = lm.tags[i + 1][1]
    atlas = struct.unpack('>I', b[:4])[0]
    nv = struct.unpack('>H', b[6:8])[0]
    v = np.array(struct.unpack('>%df' % (4 * nv), b[12:12 + 16 * nv])).reshape(nv, 4)
    aw, ah = atlas_sizes[atlas]
    d, ts = nut.load(os.path.join(other_dir, 'img-%05d.nut' % atlas))
    a = nut.decode(d, ts[0])[..., 0]
    ux0, ux1 = int(v[:, 2].min() * aw), int(v[:, 2].max() * aw)
    uy0, uy1 = int(v[:, 3].min() * ah), int(v[:, 3].max() * ah)
    sub = a[uy0:uy1, ux0:ux1]
    ys, xs = np.nonzero(sub > 128)
    # quad x / y per atlas pixel
    sx = (v[:, 0].max() - v[:, 0].min()) / (ux1 - ux0)
    sy = (v[:, 1].max() - v[:, 1].min()) / (uy1 - uy0)
    gx0 = v[:, 0].min() + xs.min() * sx
    gx1 = v[:, 0].min() + (xs.max() + 1) * sx
    gy0 = v[:, 1].min() + ys.min() * sy
    gy1 = v[:, 1].min() + (ys.max() + 1) * sy
    cx, cy, hgt = (gx0 + gx1) / 2, (gy0 + gy1) / 2, (gy1 - gy0) * 1.05
    u0, v0 = STAR_AT[0] / aw, STAR_AT[1] / ah
    u1, v1 = (STAR_AT[0] + STAR_SIZE) / aw, (STAR_AT[1] + STAR_SIZE) / ah
    return atlas, (cx - hgt / 2, cy - hgt / 2, cx + hgt / 2, cy + hgt / 2), (u0, v0, u1, v1)


# ---------------------------------------------------------------- button table
def edit_button_sequence(data):
    """id 115 after id 114 in group 1 (14 typed values an entry, the types of entry 114's), page 16's list"""
    assert data[:4] == b'\xff\xff\x00\x00'
    vals = []                           # (offset, type, value, size)
    i = 8
    while i < len(data):
        t = data[i]
        if t == 0x20:
            vals.append((i, t, struct.unpack('>I', data[i + 1:i + 5])[0], 5))
            i += 5
        elif t == 8:
            n = struct.unpack('>I', data[i + 1:i + 5])[0]
            vals.append((i, t, data[i + 5:i + 5 + n], 5 + n))
            i += 5 + n
        else:
            n = {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4, 7: 4}[t]
            vals.append((i, t, data[i + 1:i + 1 + n], 1 + n))
            i += 1 + n
    groups = [k for k, v in enumerate(vals) if v[1] == 0x20]
    g1, g2, g3 = groups
    assert vals[g1][2] == 115 and (g2 - g1 - 1) == 115 * 14, 'button table not the vanilla one'
    last = vals[g2 - 14:g2]
    entry_vals = [BUTTON_ID, MSBT_N, 3, 1, 0, 0, 8, 0xFFFFFFFF, 0, 0, 0, 0, 0, 0]
    entry = bytearray()
    for (_o, t, _v, n), val in zip(last, entry_vals):
        size = n - 1
        entry += bytes([t]) + (val & ((1 << (8 * size)) - 1)).to_bytes(size, 'big')
    # page 16 in group 3: entries of 24 values: [index, prefix, 0, movie, ..., count, 11 ids]
    per = (len(vals) - g3 - 1) // vals[g3][2]
    p16 = g3 + 1 + 16 * per
    assert vals[p16 + 1][2].rstrip(b'\0') == b'MmenOther_', vals[p16 + 1]
    cnt_k = p16 + 12                    # u8 count, then 11 u32 ids
    assert vals[cnt_k][1] == 1 and vals[cnt_k][2] == b'\x07', vals[cnt_k]
    out = bytearray(data)
    out[vals[cnt_k][0] + 1] = 8
    o, t, v, n = vals[cnt_k + 8]
    assert struct.unpack('>I', v)[0] == 0xFFFFFFFF
    out[o + 1:o + 5] = struct.pack('>I', BUTTON_ID)
    o = vals[g1][0]
    out[o + 1:o + 5] = struct.pack('>I', 116)
    ins = vals[g2][0]
    return bytes(out[:ins] + entry + out[ins:])


# ---------------------------------------------------------------- executable
def cave_words():
    a = Asm(CAVE)
    a.asm("""
        mr r3, r31
        li r4, 8
        li r5, 1
        li r6, %d
        li r7, 1
        li r8, %d
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        mtctr r12
        bctrl                   # 0x029ABC68 is out of bl range (> 32 MB)
        lwz r0, 0x14(r1)
        b 0x%08X
    """ % (RESULT, BUTTON_ID, SET_BUTTON >> 16, SET_BUTTON & 0xFFFF, LIST_END + 4))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT
    return words


def rpx_args():
    words = cave_words()
    out = ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    b = 0x48000000 | ((CAVE - LIST_END) & 0x03FFFFFC)
    out.append('0x%08X=0x%08X' % (LIST_END, b))
    out.append('0x%08X=0x%08X' % (KEY_SITE, 0x38800000 | TRAINING_KEY))
    return out


def patch_rpx(src, dst):
    import rpx_patch
    d, _shoff, _ent, secs = rpx_patch.load(src)
    for addr, want in ((LIST_END, LIST_END_WORD), (KEY_SITE, KEY_WORD)):
        got = rpx_patch.read_u32(d, secs, addr)
        assert got in (want, ) or (addr == KEY_SITE and got == 0x38800000 | TRAINING_KEY) or \
            (addr == LIST_END and got >> 26 == 18), '0x%08X holds 0x%08X' % (addr, got)
    for addr in range(CAVE, LIMIT, 4):
        w = rpx_patch.read_u32(d, secs, addr)
        assert w == 0 or addr < CAVE + 4 * len(cave_words()), 'cave space 0x%08X not free' % addr
    sys.argv = ['rpx_patch.py', src, dst] + rpx_args()
    rpx_patch.main()


# ---------------------------------------------------------------- build
def build(other_dir, menu_msbt, button_seq, rpx, out, x, y):
    od = os.path.join(out, 'ui', 'lumen', 'other')
    os.makedirs(od, exist_ok=True)
    for f in os.listdir(other_dir):
        shutil.copy(os.path.join(other_dir, f), od)
    sizes = {}
    for f in sorted(os.listdir(other_dir)):
        if f.startswith('img-') and f.endswith('.nut'):
            _d, ts = nut.load(os.path.join(other_dir, f))
            sizes[int(f[4:9])] = (ts[0].w, ts[0].h)
    lum, alpha = title_image()
    data, _ = put_bc5(os.path.join(other_dir, 'img-00003.nut'), TITLE_AT, lum, alpha)
    open(os.path.join(od, 'img-00003.nut'), 'wb').write(data)
    data, _ = put_bc4(os.path.join(other_dir, 'img-00000.nut'), STAR_AT, star_image())
    open(os.path.join(od, 'img-00000.nut'), 'wb').write(data)
    lm = cl.Lm(open(os.path.join(other_dir, 'other.lm'), 'rb').read())
    icon = icon_geom(lm, other_dir, sizes)
    remap, root, copy = edit_movie(lm, sizes, x, y, icon)
    open(os.path.join(od, 'other.lm'), 'wb').write(lm.data())
    t = flx.Tlst(open(os.path.join(other_dir, 'texlist.lst'), 'rb').read())
    aw, ah = sizes[3]
    t.add('main_txt_smashrun', 3, TITLE_AT[0], TITLE_AT[1], TITLE_SIZE[0], TITLE_SIZE[1], aw, ah)
    aw, ah = sizes[0]
    t.add('main_btn_icon_smashrun', 0, STAR_AT[0], STAR_AT[1], STAR_SIZE, STAR_SIZE, aw, ah)
    flx.E[0] = '>'
    open(os.path.join(od, 'texlist.lst'), 'wb').write(t.build())
    m = msbt.Msbt(open(menu_msbt, 'rb').read())
    m.set('MmenOther_%d' % MSBT_N, TITLE)
    m.set('MmenOther_%dh' % MSBT_N, HELP)
    os.makedirs(os.path.join(out, 'ui', 'message'), exist_ok=True)
    open(os.path.join(out, 'ui', 'message', 'menu.msbt'), 'wb').write(m.build())
    os.makedirs(os.path.join(out, 'param', 'ui'), exist_ok=True)
    open(os.path.join(out, 'param', 'ui', 'ui_button_sequence.bin'), 'wb').write(
        edit_button_sequence(open(button_seq, 'rb').read()))
    os.makedirs(os.path.join(out, 'code'), exist_ok=True)
    patch_rpx(rpx, os.path.join(out, 'code', 'cross_f.rpx'))
    return remap, root, copy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('other_dir')
    ap.add_argument('menu_msbt')
    ap.add_argument('button_seq')
    ap.add_argument('rpx')
    ap.add_argument('out')
    ap.add_argument('--x', type=float, default=1460.0)
    ap.add_argument('--y', type=float, default=496.0)
    a = ap.parse_args()
    remap, root, copy = build(a.other_dir, a.menu_msbt, a.button_seq, a.rpx, a.out, a.x, a.y)
    print('copied %s -> %s; root %d' % (copy, {k: v for k, v in remap.items()}, root))


if __name__ == '__main__':
    main()
