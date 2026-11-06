#!/usr/bin/env python3
"""Checks tools/s3ds_ui.py's build (OUT) against the 3DS files (SRC), reading the written files back:

- Lumen byte order: every Wii U .lm under WIIU_LUMEN (optional) survives big -> little -> big endian byte for
  byte (the field table covers every tag the game's own menus use).
- every converted .lm: read big-endian, each field the 3DS's (read little-endian at the same place with its own
  width: u32 / float, u16, bytes), the action bytecode parses (SWF actions; push values), the u16 fields read as
  the Wii U's do (placement modes 1-3, depths under 0x1000), placement transforms in their tables; the root
  timeline's placements = the 3DS's x4.5 + the centring offset, every other placement unchanged; stage 1920x1080.
- every converted .flx: the 3DS's sprites / keyframes / labels; non-root placements unchanged, root placements'
  matrices (and image / text rects) = the 3DS's scaled; 1920x1080.
- texture lists: the 3DS's entries; textures: every .nut decodes to the 3DS image (flipped), ids unique.
- texts: each added label the 3DS's text, every Wii U label kept as it was; every message label the movies
  show is in the Wii U files.
- params and scripts: byte-identical copies.

  python3 tools/s3ds_ui_test.py SRC WIIU_MESSAGES OUT [--melee MELEE.msbt] [--wiiu-lumen DIR]
"""
import argparse
import glob
import os
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

FAILS = []
WIDTH = {'I': 'I', 'H': 'HH', 'B': '4B'}


def check(cond, what):
    if not cond:
        print('FAIL  ' + what)
        FAILS.append(what)
    return cond


def tags_raw(d, e):
    o, out = 0x40, []
    while o < len(d):
        t, n = struct.unpack_from(e + 'II', d, o)
        out.append((t, o + 8, n))
        o += 8 + 4 * n
        if t == 0xFF00:
            break
    return out


def codes(t, d, e, o, n):
    """the field code of each word of a tag body (as s3ds_ui.FIXED / RECORDS; None for byte data)"""
    if t in su.FIXED:
        return list(su.FIXED[t])
    if t in su.RECORDS:
        return ['I'] + list(su.RECORDS[t]) * struct.unpack_from(e + 'I', d, o)[0]
    if t == 0xF024:
        nv = struct.unpack_from(e + 'HH', d, o + 4)[1]
        ni = struct.unpack_from(e + 'I', d, o + 8)[0]
        return ['I', 'H', 'I'] + ['I'] * 4 * nv + ['H'] * ((ni + 1) // 2)
    return None


def walk_actions(a):
    """SWF action bytes -> number of actions; raises on a bad length or push type"""
    o = n = 0
    size = {0: 2, 1: 4, 2: 0, 3: 0, 4: 1, 5: 1, 6: 8, 7: 4, 8: 1, 9: 2}
    while o < len(a):
        op = a[o]
        o += 1
        if op >= 0x80:
            ln = struct.unpack_from('<H', a, o)[0]
            pl = a[o + 2:o + 2 + ln]
            if len(pl) != ln:
                raise ValueError('action 0x%X length' % op)
            if op == 0x96:
                q = 0
                while q < ln:
                    q += 1 + size[pl[q]]
                if q != ln:
                    raise ValueError('push')
            o += 2 + ln
        n += 1
    return n


def lm_checks(src_path, out_path):
    tag = os.path.basename(out_path)
    s, d = open(src_path, 'rb').read(), open(out_path, 'rb').read()
    lm = cl.Lm(d)
    src_tags, out_tags = tags_raw(s, '<'), tags_raw(d, '>')
    ci, a, b = su.lm_root(lm)
    root_places = {i for i in range(a + 1, b) if lm.tags[i][0] == cl.T_PLACE}
    check(len(src_tags) == len(out_tags), '%s: tag count' % tag)
    bad = 0
    acts = 0
    for k, ((t, so, n), (t2, oo, n2)) in enumerate(zip(src_tags, out_tags)):
        if (t, n) != (t2, n2) and t != 0xF003:
            bad += 1
            continue
        cs = codes(t, s, '<', so, n)
        if cs is None:
            continue
        for w, c in enumerate(cs):
            if (k in root_places and w == 7) or (t == 0xF00C and w in (8, 9)) or (t == 0xF003 and w == 0):
                continue
            if struct.unpack_from('<' + WIDTH[c], s, so + 4 * w) != struct.unpack_from('>' + WIDTH[c], d, oo + 4 * w):
                bad += 1
    check(bad == 0, '%s: %d fields differ from the 3DS' % (tag, bad))
    # symbols and actions
    sym = lm.sy
    check(all(isinstance(x, str) for x in sym), '%s: symbols' % tag)
    for t, body in lm.tags:
        if t == 0xF005:
            n, o = struct.unpack_from('>I', body)[0], 4
            for _ in range(n):
                ln = struct.unpack_from('>I', body, o)[0]
                try:
                    acts += walk_actions(bytes(body[o + 4:o + 4 + ln]))
                except (ValueError, KeyError, struct.error) as e:
                    check(False, '%s: action bytecode %s' % (tag, e))
                o += 4 + ((ln + 3) & ~3)
    # u16 fields read as the Wii U's, indices in their tables
    pos = cl.table(lm.tags[lm.ti[cl.T_POSITIONS]][1], 2)
    xf = cl.table(lm.tags[lm.ti[cl.T_TRANSFORMS]][1], 6)
    ok = True
    for t, body in lm.tags:
        if t == cl.T_PLACE:
            w = cl.words(body)
            ok &= (w[4] >> 16) in (1, 2, 3) and (w[5] >> 16) < 0x1000
            ok &= w[7] == cl.NONE or (w[7] & cl.POS_FLAG and (w[7] & 0xFFFF) < len(pos)) or w[7] < len(xf)
    check(ok, '%s: placement modes / depths / transforms' % tag)
    # root scaled, the rest as the 3DS's
    src_lm = cl.Lm(su.lm_swap(s, '<'))
    spos = cl.table(src_lm.tags[src_lm.ti[cl.T_POSITIONS]][1], 2)
    sxf = cl.table(src_lm.tags[src_lm.ti[cl.T_TRANSFORMS]][1], 6)
    cw = cl.words(src_lm.tags[ci][1])
    k, ox = su.fit(*struct.unpack('>2f', struct.pack('>2I', cw[8], cw[9])))
    worst = 0.0
    same = True
    for i, ((t, sb), (_t, ob)) in enumerate(zip(src_lm.tags, lm.tags)):
        if t != cl.T_PLACE:
            continue
        sw, ow = cl.words(sb), cl.words(ob)
        if i in root_places and not (sw[7] == cl.NONE and sw[4] >> 16 != 1):
            want = su.scale_matrix(su.lm_matrix(src_lm, sw[7], spos, sxf), k, ox)
            worst = max(worst, float(np.abs(np.subtract(su.lm_matrix(lm, ow[7], pos, xf), want)).max()))
        else:
            same &= sw == ow
    check(worst < 1e-3, '%s: root placements scaled (worst %.3g)' % (tag, worst))
    check(same, '%s: other placements unchanged' % tag)
    cw2 = cl.words(lm.tags[ci][1])
    check(struct.unpack('>2f', struct.pack('>2I', cw2[8], cw2[9])) == (1920.0, 1080.0), '%s: stage size' % tag)
    return acts


def flx_matrix(f, p):
    """an image / text placement's rect, or a sprite placement's matrix"""
    if p.kind in (flx.KIND_SPRITE, flx.KIND_NAMED_SPRITE):
        t = flx.Transform(0) if p.xform == flx.NONE16 else f.transforms[p.xform]
        return np.array(t.matrix())
    n = f.infos[p.info] if p.info != flx.NONE16 else flx.Info()
    return np.array([n.x, n.y, n.w, n.h])


def flx_checks(src_path, out_path):
    tag = os.path.basename(out_path)
    s = flx.read(open(src_path, 'rb').read())
    check(flx.E[0] == '<', '%s: the 3DS file is little-endian' % tag)
    o = flx.read(open(out_path, 'rb').read())
    check(flx.E[0] == '>' and (o.width, o.height) == (1920, 1080), '%s: big-endian 1920x1080' % tag)
    check(s.sprites == o.sprites and s.labels == o.labels and s.frames == o.frames and s.images == o.images and
          [k.action for k in s.keys] == [k.action for k in o.keys], '%s: sprites / keyframes / labels' % tag)
    k, ox = su.fit(s.width, s.height)
    root = s.sprites[0]
    worst, same = 0.0, True
    for ki, (sk, okey) in enumerate(zip(s.keys, o.keys)):
        is_root = root.key0 <= ki < root.key0 + root.nkeys
        for spi, opi in zip(sk.places, okey.places):
            sp, op = s.places[spi], o.places[opi]
            if not is_root:
                same &= spi == opi and sp == op
                continue
            a, b = flx_matrix(s, sp), flx_matrix(o, op)
            if sp.kind in (flx.KIND_SPRITE, flx.KIND_NAMED_SPRITE):
                want = np.array(su.scale_matrix(tuple(a), k, ox))
            else:
                want = np.array([ox + k * a[0], k * a[1], k * a[2], k * a[3]])
            worst = max(worst, float(np.abs(b - want).max()))
    check(worst < 1e-2, '%s: root placements scaled (worst %.3g)' % (tag, worst))
    check(same, '%s: other placements unchanged' % tag)


def texture_checks(src_dir, out_dir, ids, keep=lambda n: True):
    for p in sorted(glob.glob(os.path.join(src_dir, '*.tex'))):
        if not keep(os.path.basename(p)):
            continue
        q = os.path.join(out_dir, os.path.basename(p)[:-4] + '.nut')
        if not check(os.path.exists(q), '%s: written' % q):
            continue
        d, texs = nut.load(q)
        t = texs[0]
        ids.append(t.tex_id)
        check(t.fmt == 0x1A and np.array_equal(nut.decode(d, t), su.read_tex(open(p, 'rb').read())),
              '%s: the 3DS image' % os.path.relpath(q, out_dir))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('wiiu_msg')
    ap.add_argument('out')
    ap.add_argument('--melee')
    ap.add_argument('--wiiu-lumen')
    a = ap.parse_args()
    n_rt = 0
    if a.wiiu_lumen:
        for p in sorted(glob.glob(os.path.join(a.wiiu_lumen, '**', '*.lm'), recursive=True)):
            d = open(p, 'rb').read()
            check(su.lm_swap(su.lm_swap(d, '>'), '<') == d, '%s: Wii U round trip' % p)
            n_rt += 1
    ui, out_ui = os.path.join(a.src, 'ui'), os.path.join(a.out, 'ui')
    n_lm = n_flx = acts = 0
    ids = []
    for kind in ('info', 'lumen'):
        for d in sorted(glob.glob(os.path.join(ui, kind, '*'))):
            od = os.path.join(out_ui, kind, os.path.basename(d))
            for p in glob.glob(os.path.join(d, '*.lm')):
                acts += lm_checks(p, os.path.join(od, os.path.basename(p)))
                n_lm += 1
            for p in glob.glob(os.path.join(d, '*.flx')):
                flx_checks(p, os.path.join(od, os.path.basename(p)))
                n_flx += 1
            s, o = flx.Tlst(open(os.path.join(d, 'texlist.lst'), 'rb').read()), None
            o = flx.Tlst(open(os.path.join(od, 'texlist.lst'), 'rb').read())
            check(flx.E[0] == '>' and s.slots == o.slots and s.entries == o.entries, '%s: texture list' % od)
            texture_checks(d, od, ids)
    for d in sorted(glob.glob(os.path.join(ui, 'replace', '*', '*'))):
        od = os.path.join(out_ui, 'replace', os.path.relpath(d, os.path.join(ui, 'replace')))
        texture_checks(d, od, ids, (lambda n: '_fs_' in n) if '/mark/' in d else (lambda n: True))
    check(len(ids) == len(set(ids)) and min(ids) >= su.TEX_IDS, 'texture ids unique, from 0x%08X' % su.TEX_IDS)
    # texts
    used = su.movie_strings(a.out)
    added = 0
    all_wiiu = set()
    for f in su.TEXTS:
        base = a.melee if f == 'melee' and a.melee else os.path.join(a.wiiu_msg, f + '.msbt')
        b = msbt.Msbt(open(base, 'rb').read())
        s3 = msbt.Msbt(open(os.path.join(ui, 'message', f + '.msbt'), 'rb').read())
        o = msbt.Msbt(open(os.path.join(out_ui, 'message', f + '.msbt'), 'rb').read())
        check(o.endian == '>', '%s.msbt: big-endian' % f)
        check(all(o.text(lb) == b.text(lb) for lb in b.labels), '%s.msbt: Wii U texts kept' % f)
        new = [lb for lb in o.labels if lb not in b.labels]
        check(all(o.text(lb) == s3.text(lb) for lb in new), '%s.msbt: added texts the 3DS\'s' % f)
        added += len(new)
        all_wiiu |= set(o.labels)
    s3_all = set()
    for f in su.TEXTS:
        s3_all |= set(msbt.Msbt(open(os.path.join(ui, 'message', f + '.msbt'), 'rb').read()).labels)
    missing = sorted(lb for lb in used if lb in s3_all and lb not in all_wiiu)
    check(not missing, 'labels the movies show, missing: %s' % missing[:10])
    # params, scripts
    n_par = 0
    for p in glob.glob(os.path.join(a.out, 'field_smash', '*')) + glob.glob(os.path.join(a.out, 'param', '*', '*')) + \
            glob.glob(os.path.join(out_ui, 'script', 'app', 'field_smash', '*')):
        rel = os.path.relpath(p, a.out)
        check(open(p, 'rb').read() == open(os.path.join(a.src, rel), 'rb').read(), '%s: copy' % rel)
        n_par += 1
    print('%d Wii U .lm round trips, %d .lm (%d actions), %d .flx, %d textures, %d texts added, %d params / scripts, '
          '%d failures' % (n_rt, n_lm, acts, n_flx, len(ids), added, n_par, len(FAILS)))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
