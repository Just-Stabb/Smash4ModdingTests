#!/usr/bin/env python3
"""Smash 3DS's Smash Run UI and mode params -> Wii U files (docs/smash-run-port.md, "UI and mode params").

  python3 tools/s3ds_ui.py SRC WIIU_MESSAGES OUT [--melee MELEE.msbt]

SRC: the 3DS files extracted with tools/s3ds_unpack.py (ui/info/fs_*, ui/info/pause_field_down, ui/lumen/field_*,
ui/lumen/result_field1_*, ui/replace/field, ui/replace/mark, ui/message, ui/script/app/field_smash, param/item,
param/ui/fs_info_param.bin, field_smash). WIIU_MESSAGES: the game's ui/message folder (the texts are added to its
menu / melee / smash / figure / cleargetter.msbt); --melee: a melee.msbt to add to instead (the stage-slot build's,
which already has the Smash Run stage names). OUT gets:

- ui/info/NAME/ (HUD movies, 'flx2') and ui/lumen/NAME/ (menus, Lumen 'LMB'): the movie big-endian, scaled from the
  3DS screen (400x240 top, 320x240 bottom) to the Wii U's 1920x1080 (x4.5, centred: the root's placements get the
  scale, everything inside them is unchanged); texlist.lst big-endian; img-NNNNN.tex -> img-NNNNN.nut.
- ui/replace/field/..., ui/replace/mark/mark_*/mark_*_fs_item: the replace pictures as .nut.
- ui/message/*.msbt: the Wii U files with the Smash Run texts added (labels the 3DS has and the Wii U doesn't:
  MmenField_*, Mmel_Fsi*, MmelPause_fieldsmash_*, Msma_Field*, ... and every label the movies show).
- field_smash/, param/item/, param/ui/fs_info_param.bin: the mode params (big-endian already: typed params,
  LVD paths), copied; _dump/*.json: their values, readable.
- ui/script/app/field_smash/*.xtal: the menu scripts (the same xtal format on both).

Textures are written RGBA8 (0x1A; the 3DS images are small, so no BC loss), one mip, flipped (the 3DS stores rows
bottom first; the texture lists' UVs count from the top on both), ids from TEX_IDS up.
"""
import argparse
import dataclasses
import glob
import json
import os
import re
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
import s3ds_model as sm  # noqa: E402
import s4param  # noqa: E402

W, H = 1920, 1080
TEX_IDS = 0x2800A000            # the game's UI uses 0x28000000-0x28006395, add_stage.py 0x2800FF00 up
TEXTS = ['menu', 'melee', 'smash', 'figure', 'cleargetter']
SR_LABEL = re.compile(r'field|Field|_fs|fs_|Fs')
NOT_SR = re.compile(r'^MmelStage')


# ---------------------------------------------------------------- textures
def read_tex(data):
    """3DS UI texture (.tex: 0x80 header u32 w, u32 h, u8 PICA format, u8 mips, name at 0x0C) -> RGBA [h, w, 4],
    first row the top"""
    w, h, fmt = struct.unpack('<IIB', data[:9])
    return np.ascontiguousarray(sm.decode_texture(data[0x80:], w, h, fmt)[::-1])


def tex_to_nut(data, tex_id):
    return nut.write_ntwu([(tex_id, 0x1A, read_tex(data))])


# ---------------------------------------------------------------- screen fit
def fit(w, h):
    """(scale, x offset) putting a w x h 3DS screen on the Wii U's 1920x1080, centred"""
    k = H / float(h)
    return k, (W - k * w) / 2.0


def scale_matrix(m, k, ox):
    a, b, c, d, tx, ty = m
    return (a * k, b * k, c * k, d * k, ox + k * tx, k * ty)


# ---------------------------------------------------------------- flx (HUD movies)
def scale_flx(f, k, ox):
    """scale the root sprite's placements (sprite 0): sprites by their transform, images / texts (which sit at
    their Info rect) by a scaled copy of it (texts also a scaled copy of their format's font size)"""
    root = f.sprites[0]
    elsewhere = {pi for si, s in enumerate(f.sprites) if si for key in f.keys[s.key0:s.key0 + s.nkeys]
                 for pi in key.places}
    memo_x, memo_i, memo_t, done = {}, {}, {}, {}

    def xform(i):
        if i not in memo_x:
            t = flx.Transform(0) if i == flx.NONE16 else f.transforms[i]
            sx = t.sx if t.flags & 4 else 1.0
            sy = t.sy if t.flags & 8 else sx
            x = t.x if t.flags & 1 else 0.0
            y = t.y if t.flags & 2 else 0.0
            f.transforms.append(flx.Transform(t.flags | 15, ox + k * x, k * y, k * sx, k * sy, t.rot, t.rot2))
            memo_x[i] = len(f.transforms) - 1
        return memo_x[i]

    def info(i):
        if i not in memo_i:
            n = f.infos[i]
            f.infos.append(flx.Info(n.name, ox + k * n.x, k * n.y, k * n.w, k * n.h))
            memo_i[i] = len(f.infos) - 1
        return memo_i[i]

    def text(i):
        if i not in memo_t:
            t = f.texts[i]
            fm = f.formats[t.fmt]
            f.formats.append(dataclasses.replace(fm, size=min(255, int(round(fm.size * k)))))
            f.texts.append(dataclasses.replace(t, width=int(round(t.width * k)), height=int(round(t.height * k)),
                                               fmt=len(f.formats) - 1))
            memo_t[i] = len(f.texts) - 1
        return memo_t[i]

    for key in f.keys[root.key0:root.key0 + root.nkeys]:
        for j, pi in enumerate(key.places):
            if pi not in done:
                p = dataclasses.replace(f.places[pi])
                if p.kind in (flx.KIND_SPRITE, flx.KIND_NAMED_SPRITE):
                    p.xform = xform(p.xform)
                else:
                    if p.info != flx.NONE16:
                        p.info = info(p.info)
                    if p.kind == flx.KIND_TEXT:
                        p.char = text(p.char)
                if pi in elsewhere:
                    f.places.append(p)
                    done[pi] = len(f.places) - 1
                else:
                    f.places[pi] = p
                    done[pi] = pi
            key.places[j] = done[pi]
    f.width, f.height = W, H


def convert_flx(data):
    f = flx.read(data)
    k, ox = fit(f.width, f.height)
    scale_flx(f, k, ox)
    flx.E[0] = '>'
    return flx.write(f), (k, ox)


# ---------------------------------------------------------------- Lumen (LMB) byte order
# per tag, each 32-bit word: I = one 32-bit value (u32 / float), H = two u16, B = four bytes (kept). Found by
# comparing every tag word of the 3DS's 234 .lm with the Wii U's 201 (tools/s3ds_ui_test.py checks the Wii U's
# round trip); the action bytecode (F005) is SWF's little-endian on both.
FIXED = {0x0001: 'II', 0x0004: 'IIIIHHHIIIII', 0x0005: 'IH', 0x000C: 'II', 0x0025: 'IIIIIIIIHBBIIIII',
         0x0027: 'IIIIIIH', 0x002B: 'III', 0xF008: 'I', 0xF009: 'I', 0xF00A: 'I', 0xF00B: 'I',
         0xF00C: 'IIIIIIHIIIII', 0xF00D: 'IIIIIIII', 0xF014: 'II', 0xF022: 'IIIII', 0xF037: 'I' * 20,
         0xF105: 'II', 0xFF00: ''}
RECORDS = {0x000A: 'IIIII', 0xF002: 'HH', 0xF003: 'IIIIII', 0xF004: 'IIII', 0xF007: 'IIII', 0xF103: 'II'}
SWAP = {'I': (3, 2, 1, 0), 'H': (1, 0, 3, 2), 'B': (0, 1, 2, 3)}


def _swap(b, o, codes):
    out = bytearray()
    for c in codes:
        w = b[o:o + 4]
        out += bytes(w[i] for i in SWAP[c])
        o += 4
    return out


def lm_swap(data, src):
    """a .lm with every field byte-swapped: src '<' (3DS) -> big-endian, '>' -> little-endian"""
    u32 = lambda b, o: struct.unpack_from(src + 'I', b, o)[0]   # noqa: E731
    out = bytearray(_swap(data, 0, 'I' * 16))
    o = 0x40
    while o < len(data):
        t, n = u32(data, o), u32(data, o + 4)
        b = data[o + 8:o + 8 + 4 * n]
        out += _swap(data, o, 'II')
        if t in FIXED:
            assert len(FIXED[t]) == n, 'tag 0x%X: %d words' % (t, n)
            body = _swap(b, 0, FIXED[t])
        elif t in RECORDS:
            cnt, r = u32(b, 0), RECORDS[t]
            assert 4 + 4 * len(r) * cnt == len(b), 'tag 0x%X size' % t
            body = _swap(b, 0, 'I' + r * cnt)
        elif t in (0xF001, 0xF005):         # strings / action bytecode: u32 count, (u32 length, bytes, padding)
            body, q = _swap(b, 0, 'I'), 4
            for _ in range(u32(b, 0)):
                ln = u32(b, q)
                end = q + 4 + ((ln + 4) & ~3 if t == 0xF001 else (ln + 3) & ~3)
                body += _swap(b, q, 'I') + b[q + 4:end]
                q = end
            assert q == len(b), 'tag 0x%X size' % t
        elif t == 0xF024:                   # graphic: atlas, (fill, vertex count), index count, x y u v, u16 indices
            body = _swap(b, 0, 'IHI')
            nv = struct.unpack_from(src + 'HH', b, 4)[1]
            ni = u32(b, 8)
            body += _swap(b, 12, 'I' * 4 * nv)
            body += _swap(b, 12 + 16 * nv, 'H' * ((ni + 1) // 2))
            assert len(body) == len(b), 'tag 0xF024 size'
        else:
            raise ValueError('unknown Lumen tag 0x%X' % t)
        out += body
        o += 8 + 4 * n
        if t == 0xFF00:
            break
    assert o == len(data)
    return bytes(out)


def lm_root(lm):
    """(F00C tag index, root sprite's tag range [a, b))"""
    ci = lm.ti[0xF00C]
    root = cl.words(lm.tags[ci][1])[3]
    a = next(i for i, (t, b) in enumerate(lm.tags) if t == cl.T_SPRITE and cl.words(b)[0] == root)
    b = a + 1
    while b < len(lm.tags) and lm.tags[b][0] not in (cl.T_SPRITE, cl.T_END, 0x0025, 0xF022, 0x0007):
        b += 1
    return ci, a, b


def lm_matrix(lm, i, pos, xf):
    if i == cl.NONE:
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    if i & cl.POS_FLAG:
        x, y = pos[i & 0xFFFF]
        return (1.0, 0.0, 0.0, 1.0, x, y)
    return xf[i]


def scale_lm(lm):
    """the root timeline's placements scaled (transforms appended); stage size 1920x1080. A placement without a
    transform keeps the one before it unless it places a new object (mode 1)"""
    ci, a, b = lm_root(lm)
    cw = cl.words(lm.tags[ci][1])
    w, h = struct.unpack('>2f', struct.pack('>2I', cw[8], cw[9]))
    k, ox = fit(w, h)
    pos = cl.table(lm.tags[lm.ti[cl.T_POSITIONS]][1], 2)
    xft = lm.tags[lm.ti[cl.T_TRANSFORMS]]
    xf = cl.table(xft[1], 6)
    memo = {}
    for i in range(a + 1, b):
        t, body = lm.tags[i]
        if t != cl.T_PLACE:
            continue
        pw = cl.words(body)
        if pw[7] == cl.NONE and pw[4] >> 16 != 1:
            continue
        if pw[7] not in memo:
            memo[pw[7]] = cl.append_rows(xft, [scale_matrix(lm_matrix(lm, pw[7], pos, xf), k, ox)], 6)[0]
        pw[7] = memo[pw[7]]
        lm.tags[i][1] = cl.pack(pw)
    cw[8], cw[9] = struct.unpack('>2I', struct.pack('>2f', W, H))
    lm.tags[ci][1] = cl.pack(cw)
    return k, ox


def convert_lm(data):
    lm = cl.Lm(lm_swap(data, '<'))
    k, ox = scale_lm(lm)
    return lm.data(), (k, ox)


# ---------------------------------------------------------------- folders
class Ids:
    def __init__(self, first=TEX_IDS):
        self.next = first

    def take(self):
        self.next += 1
        return self.next - 1


def convert_movie_dir(src, dst, ids, log):
    os.makedirs(dst, exist_ok=True)
    for name in sorted(os.listdir(src)):
        p = os.path.join(src, name)
        data = open(p, 'rb').read()
        if name.endswith('.flx'):
            out, (k, ox) = convert_flx(data)
            log.append('%s: x%.2f +%.0f' % (os.path.relpath(p, src), k, ox))
        elif name.endswith('.lm'):
            out, (k, ox) = convert_lm(data)
            log.append('%s: x%.2f +%.0f' % (os.path.relpath(p, src), k, ox))
        elif name == 'texlist.lst':
            t = flx.Tlst(data)
            flx.E[0] = '>'
            out = t.build()
        elif name.endswith('.tex'):
            out, name = tex_to_nut(data, ids.take()), name[:-4] + '.nut'
        else:
            raise ValueError('unexpected file ' + p)
        open(os.path.join(dst, name), 'wb').write(out)


def convert_replace(src, dst, ids, keep=lambda n: True):
    n = 0
    for p in sorted(glob.glob(os.path.join(src, '*', '*.tex'))):
        if not keep(os.path.basename(p)):
            continue
        d = os.path.join(dst, os.path.basename(os.path.dirname(p)))
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, os.path.basename(p)[:-4] + '.nut'), 'wb').write(tex_to_nut(open(p, 'rb').read(),
                                                                                         ids.take()))
        n += 1
    return n


# ---------------------------------------------------------------- texts
def movie_strings(out):
    """every string the converted movies hold (flx strings, Lumen symbols): message labels among them"""
    s = set()
    for p in glob.glob(os.path.join(out, 'ui', '*', '*', '*.flx')):
        s.update(flx.read(open(p, 'rb').read()).strings)
    for p in glob.glob(os.path.join(out, 'ui', '*', '*', '*.lm')):
        s.update(cl.Lm(open(p, 'rb').read()).sy)
    return {x.split('$')[0] for x in s}


def merge_texts(src_msg, wiiu_msg, out, melee=None):
    used = movie_strings(out)
    s3 = {f: msbt.Msbt(open(os.path.join(src_msg, f + '.msbt'), 'rb').read()) for f in TEXTS}
    added = {}
    os.makedirs(os.path.join(out, 'ui', 'message'), exist_ok=True)
    for f in TEXTS:
        base = melee if f == 'melee' and melee else os.path.join(wiiu_msg, f + '.msbt')
        m = msbt.Msbt(open(base, 'rb').read())
        assert m.atr is None or struct.unpack('>I', m.atr[4:8])[0] == 0, '%s: per-text attributes' % f
        added[f] = []
        for label in s3[f].labels:
            if label in m.labels or NOT_SR.match(label):
                continue
            if SR_LABEL.search(label) or label in used:
                m.set(label, s3[f].text(label))
                added[f].append(label)
        flx.E[0] = '>'
        open(os.path.join(out, 'ui', 'message', f + '.msbt'), 'wb').write(m.build())
    return added


# ---------------------------------------------------------------- params
def flat_values(data):
    """typed values (s4param's types) in file order; a group (0x20) as {'group': entry count}: the entries'
    values follow it (not split: nested groups don't split evenly)"""
    out, i = [], 0
    while i < len(data):
        t = data[i]
        i += 1
        if t == 0x20:
            out.append({'group': struct.unpack('>I', data[i:i + 4])[0]})
            i += 4
        elif t == 8:
            n = struct.unpack('>I', data[i:i + 4])[0]
            out.append(data[i + 4:i + 4 + n].rstrip(b'\0').decode('ascii', 'replace'))
            i += 4 + n
        elif t in s4param.SIZES:
            n = s4param.SIZES[t]
            v = struct.unpack(s4param.UNPACK[t], data[i:i + n])[0]
            out.append(round(v, 6) if t == 7 else v)
            i += n
        else:
            raise ValueError('type 0x%X at 0x%X' % (t, i - 1))
    return out


def param_kind(data):
    """'params' (FF FF 00 00 header, typed values), 'values' (typed values, no header), 'lvd' or 'raw'"""
    if data[:4] == b'\xff\xff\x00\x00':
        flat_values(data[8:])
        return 'params'
    if data[4:9] == b'\x0a\x01LVD':
        return 'lvd'
    try:
        flat_values(data)
        return 'values'
    except (ValueError, struct.error, IndexError):
        return 'raw'


def copy_params(src, out):
    kinds = {}
    files = sorted(glob.glob(os.path.join(src, 'field_smash', '*.bin')) +
                   glob.glob(os.path.join(src, 'param', 'item', '*fs_*.bin')) +
                   glob.glob(os.path.join(src, 'param', 'ui', 'fs_*.bin')))
    for p in files:
        rel = os.path.relpath(p, src)
        data = open(p, 'rb').read()
        os.makedirs(os.path.dirname(os.path.join(out, rel)), exist_ok=True)
        shutil.copyfile(p, os.path.join(out, rel))
        k = kinds[rel] = param_kind(data)
        if k in ('params', 'values'):
            dump = os.path.join(out, '_dump', rel[:-4] + '.json')
            os.makedirs(os.path.dirname(dump), exist_ok=True)
            json.dump(flat_values(data[8:] if k == 'params' else data), open(dump, 'w'), indent=0)
    return kinds


# ---------------------------------------------------------------- build
def build(src, wiiu_msg, out, melee=None):
    ids, log = Ids(), []
    ui = os.path.join(src, 'ui')
    for kind in ('info', 'lumen'):
        for d in sorted(glob.glob(os.path.join(ui, kind, '*'))):
            convert_movie_dir(d, os.path.join(out, 'ui', kind, os.path.basename(d)), ids, log)
    n = convert_replace(os.path.join(ui, 'replace', 'field'), os.path.join(out, 'ui', 'replace', 'field'), ids)
    n += convert_replace(os.path.join(ui, 'replace', 'mark'), os.path.join(out, 'ui', 'replace', 'mark'), ids,
                         lambda name: '_fs_' in name)
    log.append('%d replace pictures' % n)
    added = merge_texts(os.path.join(ui, 'message'), wiiu_msg, out, melee)
    log += ['%s.msbt: %d texts added' % (f, len(v)) for f, v in added.items()]
    kinds = copy_params(src, out)
    log.append('%d param files (%s)' % (len(kinds), ', '.join('%d %s' % (list(kinds.values()).count(k), k)
                                                             for k in sorted(set(kinds.values())))))
    sd = os.path.join(ui, 'script', 'app', 'field_smash')
    for p in sorted(glob.glob(os.path.join(sd, '*.xtal'))):
        d = os.path.join(out, 'ui', 'script', 'app', 'field_smash')
        os.makedirs(d, exist_ok=True)
        shutil.copyfile(p, os.path.join(d, os.path.basename(p)))
    log.append('textures 0x%08X-0x%08X' % (TEX_IDS, ids.next - 1))
    return log, added, kinds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('wiiu_msg')
    ap.add_argument('out')
    ap.add_argument('--melee')
    a = ap.parse_args()
    log, _added, _kinds = build(a.src, a.wiiu_msg, a.out, a.melee)
    print('\n'.join(log))


if __name__ == '__main__':
    main()
