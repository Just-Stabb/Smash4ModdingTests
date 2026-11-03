#!/usr/bin/env python3
"""Checks option_button_ui.py's output against the originals.

  python3 tools/option_button_ui_test.py UI_DIR MENU_MSBT

- xtal: every original instruction outside the replaced tables is in the new code (decoded again
  from the written file) with the same fields, its jumps to the relocated targets; the tables read
  back as wanted; the new identifiers and constants;
- layout: the label sprites' new frame per row (`sub_11`: the text named MmenOption_button_85$0, its
  own text object; the character counts and max id), the btn_group row sub_11 at depth 8 wherever
  sub_3 is (with O.ROW_LAYOUT: every toggle row at its scale and y, under the TRY button);
- msbt: the new labels, every other text unchanged.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xtal  # noqa: E402
import chara_layout as LM  # noqa: E402
import option_button_ui as O  # noqa: E402
from msbt import Msbt  # noqa: E402

fails = 0


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def main():
    ui, menu = sys.argv[1:3]
    orig_data = open(os.path.join(ui, O.XTAL), 'rb').read()
    patched = O.patch_xtal(orig_data)
    target, instr = patched.relocate
    new = xtal.Code(patched.data())               # decoded again from the bytes
    orig = xtal.Code(orig_data)
    check('the written file parses back the same', new.data(), patched.data())
    replaced = [(s, e) for s, e, _n in patched.edits if e > s]
    newins = {pc: (op, f) for pc, op, f, _ in new.instructions()}
    bad = 0
    kept = 0
    for pc, op, f, _ in orig.instructions():
        if any(s <= pc < e for s, e in replaced):
            continue
        kept += 1
        got = newins.get(instr(pc))
        if got is None or got[0] != op:
            bad += 1
            continue
        for t, name in xtal.INSTS[op][1]:
            if t == 'address16':
                if instr(pc) + got[1][name] != target(pc + f[name]):
                    bad += 1
            elif got[1][name] != f[name]:
                bad += 1
    check('%d original instructions kept, fields and jump targets' % kept, bad, 0)
    check('code size', len(new.code), len(orig.code) + sum(n - (e - s) for s, e, n in patched.edits))

    def tab(start):
        s = target(start)
        if start == O.NAMES_AT:                    # the op -> text map's OP_NONE entry is put before it
            s = next(pc for pc, op, f, _ in new.instructions() if pc >= s and xtal.INSTS[op][0] == 'MakeMap')
        return xtal.read_table(new, s, O.table_end(new, s))[1]
    names = tab(O.NAMES_AT)
    keys = [r[0] for r in O.ROWS]
    for p in O.ROW_PADS:
        check('%s names: %s after SMASH' % (p, keys), names[p][names[p].index('SMASH') + 1:][:len(keys)], keys)
    check('FREE_STYLE / REMOTE names unchanged', (names['FREE_STYLE'], names['REMOTE']),
          tuple(xtal.read_table(orig, O.NAMES_AT, O.table_end(orig, O.NAMES_AT))[1][p] for p in ('FREE_STYLE', 'REMOTE')))
    ids, cur, clips = tab(O.IDS_AT), tab(O.CURSOR_AT), tab(O.CLIPS_AT)
    for p in O.ROW_PADS:
        n = names[p]
        check('%s ids / cursor / clips aligned with names' % p, (len(ids[p]), len(cur[p]), len(clips[p])), (len(n),) * 3)
        chain = ['SMASH'] + keys
        at = [n.index(x) for x in chain]
        check('%s cursor: %s up / down in order' % (p, ' <-> '.join(chain)),
              [(cur[p][at[q]][1], cur[p][at[q + 1]][0]) for q in range(len(keys))],
              [(chain[q + 1], chain[q]) for q in range(len(keys))])
        below = cur[p][at[-1]][1]
        ocur = xtal.read_table(orig, O.CURSOR_AT, O.table_end(orig, O.CURSOR_AT))[1][p]
        onames = xtal.read_table(orig, O.NAMES_AT, O.table_end(orig, O.NAMES_AT))[1][p]
        check('%s cursor: %s down = what was below SMASH (%s)' % (p, keys[-1], below), below,
              ocur[onames.index('SMASH')][1])
        if below is not None:
            check('%s cursor: the key below %s goes up to it' % (p, keys[-1]), cur[p][n.index(below)][0], keys[-1])
        check('%s clips' % p, [clips[p][q] for q in at[1:]], [('call', 4, r[1]) for r in O.ROWS])
        check('%s ids: null' % p, [ids[p][q] for q in at[1:]], [None] * len(keys))
    equip = tab(O.EQUIP_AT)
    oequip = xtal.read_table(orig, O.EQUIP_AT, O.table_end(orig, O.EQUIP_AT))[1]
    missing = [(p, k) for p, keys in equip.items() for k, (w, ops) in keys.items() if O.OP_SMASH not in ops]
    check('keys without Smash (windows with no bigger one)', missing, [('FREE_STYLE', 'UP'), ('FREE_STYLE', 'LR'),
                                                                       ('FREE_STYLE', 'DOWN'), ('REMOTE', 'UP')])
    ckeys = [k[0] for k in O.CLICKS]
    for p, keys in equip.items():
        for k, (w, ops) in keys.items():
            if k in ckeys:
                continue
            ow, oops = oequip[p][k]
            if ops != oops:
                assert ops == oops + [O.OP_SMASH] and w == ow + 10, (p, k)
    print('     e.g. GC A %s (was %s), GC UP %s (was %s)' % (equip['GC']['A'], oequip['GC']['A'], equip['GC']['UP'], oequip['GC']['UP']))
    # stick clicks
    onames = xtal.read_table(orig, O.NAMES_AT, O.table_end(orig, O.NAMES_AT))[1]
    oids = xtal.read_table(orig, O.IDS_AT, O.table_end(orig, O.IDS_AT))[1]
    ocur = xtal.read_table(orig, O.CURSOR_AT, O.table_end(orig, O.CURSOR_AT))[1]
    for p in O.CLICK_PADS:
        n = names[p]
        at = n.index('R_STICK')
        check('%s: %s after R_STICK, ids %s, clips key_14 / key_15' % (p, ckeys, [k[1] for k in O.CLICKS]),
              (n[at + 1:at + 3], ids[p][at + 1:at + 3], clips[p][at + 1:at + 3]),
              (ckeys, [k[1] for k in O.CLICKS], [('call', 5, k[1]) for k in O.CLICKS]))
        check('%s: equip %s' % (p, O.CLICK_OPS), [equip[p][k] for k in ckeys], [[O.CLICK_WINDOW, O.CLICK_OPS]] * 2)
        others = [x for x in n if x not in ckeys and ids[p][n.index(x)] is not None]     # the other keys
        changed = {x: (ocur[p][onames[p].index(x)], cur[p][n.index(x)]) for x in others
                   if ocur[p][onames[p].index(x)] != cur[p][n.index(x)]}
        if p in O.CLICK_SHOWN:
            c = {x: cur[p][n.index(x)] for x in ckeys}
            check('%s cursor: L_PUSH / R_PUSH rows' % p, c, {'L_PUSH': ['L', 'UP', None, 'R_STICK'],
                                                            'R_PUSH': ['R_STICK', 'X', 'L_PUSH', 'TRY']})
            check('%s cursor: L down / UP up / R_STICK down, left / X up to them' % p,
                  {x: v[1] for x, v in changed.items()},
                  {'L': ['ZL', 'L_PUSH', None, 'R'], 'UP': ['L_PUSH', 'LR', None, 'X'],
                   'R_STICK': ['R', 'R_PUSH', 'L_PUSH', 'TRY'], 'X': ['R_PUSH', 'Y', 'UP', 'TRY']})
            # up / down to and from the new keys come back; L_PUSH <-> R_STICK across (R_PUSH's left is one-way)
            back = {0: 1, 1: 0, 2: 3, 3: 2}
            oneway = [(x, d, v[d]) for x in ckeys + list(changed) for v in [cur[p][n.index(x)]] for d in range(4)
                      if v[d] in ckeys + list(changed) and cur[p][n.index(v[d])][back[d]] != x]
            check('%s cursor: the moves to / from the new keys come back (but R_PUSH left)' % p, oneway,
                  [('R_PUSH', 2, 'L_PUSH')])
        else:
            check('%s cursor: the new keys unreachable, no other key changed' % p,
                  ([cur[p][n.index(x)] for x in ckeys], changed, [x for x in n for v in [cur[p][n.index(x)]] if set(v) & set(ckeys)]),
                  ([[None] * 4] * 2, {}, []))
    opmap = [new.fmt(pc, op, f) for pc, op, f, _ in new.instructions() if target(O.NAMES_AT) <= pc < target(O.NAMES_AT) + 7]
    check('op -> text map: OP_NONE -> txt_%d: %s' % (O.OP_NONE, opmap[:3]), [x.split()[0] for x in opmap[:3]],
          ['LoadInt1Byte', 'LoadInt1Byte', 'MapInsert'])
    for name in [x for k in O.CLICKS for x in k[3:5]]:
        check('identifier %s' % name, name in [new.resolve(v) for v in new.idents], True)
    check('rows map', tab(O.ROWS_MAP_AT), dict({'RUMBLE': 1, 'FLICK': 2, 'SMASH': 10, 'SHAKE': 3},
                                               **{r[0]: r[1] for r in O.ROWS}))
    for name in [x for r in O.ROWS for x in r[2:4]]:
        check('identifier %s' % name, name in [new.resolve(v) for v in new.idents], True)
    sub = [new.fmt(pc, op, f) for pc, op, f, _ in new.instructions()
           if target(O.IS_SUB_END) <= pc < instr(O.IS_SUB_END) and xtal.INSTS[op][0] == 'LoadConstant']
    check('is_sub: the new rows are right-hand items', [r[0] for r in O.ROWS if any("'%s'" % r[0] in x for x in sub)],
          [r[0] for r in O.ROWS])
    for s, e, n in patched.edits:
        if s == e:
            print('---- inserted at %d (new %d):' % (s, target(s)))
            for pc, op, f, _ in new.instructions():
                if target(s) <= pc < target(s) + n:
                    print('  %5d  %s' % (pc, new.fmt(pc, op, f)))

    # layout
    lm = LM.Lm(O.patch_lm(open(os.path.join(ui, O.LMB), 'rb').read()))
    T, sy = lm.tags, lm.sy
    for cid in (166, 171):
        i, j = O.sprite_range(lm, cid)
        labels = {sy[LM.words(b)[0]]: LM.words(b)[1] for t, b in T[i:j] if t == LM.T_LABEL}
        frames = [k for k in range(i, j) if T[k][0] == LM.T_FRAME]
        for r in O.ROWS:
            f = labels.get('sub_%d' % r[1])
            names_in = [sy[LM.words(T[k][1])[3]] for k in range(frames[f] + 1, frames[f] + 1 + LM.words(T[frames[f]][1])[1])
                        if T[k][0] == LM.T_PLACE] if f is not None else []
            check('sprite %d: frame sub_%d shows the new text' % (cid, r[1]), names_in, [r[4] + '$0'])
        hdr = LM.words(T[i][1])
        check('sprite %d: header counts' % cid, (hdr[3], hdr[4], hdr[5]),
              (len(labels), len(frames), sum(1 for t, b in T[i:j] if t == LM.T_KEYFRAME)))
    rowsprites = {}
    cur = None
    for t, b in T:
        if t == LM.T_SPRITE:
            cur = LM.words(b)[0]
        elif t == LM.T_LABEL and sy[LM.words(b)[0]].startswith('sub_'):
            rowsprites.setdefault(cur, set()).add(sy[LM.words(b)[0]])
    for cid, labs in sorted(rowsprites.items()):
        check('sprite %d (a frame per row name): has every new row' % cid,
              sorted({'sub_%d' % r[1] for r in O.ROWS} - labs), [])
    i, j = O.sprite_range(lm, O.ICON_SPRITE)
    labels = {sy[LM.words(b)[0]]: LM.words(b)[1] for t, b in T[i:j] if t == LM.T_LABEL}
    keys = {LM.words(b)[0]: k for k, (t, b) in enumerate(T[i:j], i) if t == LM.T_KEYFRAME}

    def key_chars(f):
        k = keys[f]
        return [LM.words(b)[0] for t, b in T[k + 1:k + 1 + LM.words(T[k][1])[1]] if t == LM.T_PLACE]
    for r in O.ROWS:
        check('icon sprite: sub_%d shows the %s icon %s' % (r[1], O.ICON_FROM, key_chars(labels[O.ICON_FROM])),
              key_chars(labels['sub_%d' % r[1]]), key_chars(labels[O.ICON_FROM]))
    hdr = LM.words(T[i][1])
    check('icon sprite: header counts', (hdr[3], hdr[4], hdr[5]),
          (len(labels), sum(1 for t, b in T[i:j] if t == LM.T_FRAME), len(keys)))
    i, j = O.sprite_range(lm, 420)
    xf = LM.table(T[lm.ti[LM.T_TRANSFORMS]][1], 6)
    olm = LM.Lm(open(os.path.join(ui, O.LMB), 'rb').read())
    oi, oj = O.sprite_range(olm, 420)
    opos = LM.table(olm.tags[olm.ti[LM.T_POSITIONS]][1], 2)

    def places(tags, depth):
        return [LM.words(b) for t, b in tags if t == LM.T_PLACE and LM.words(b)[5] >> 16 == depth]
    ox = [opos[w[7] & 0xFFFF][0] for w in places(olm.tags[oi:oj], 3)]
    if O.ROW_LAYOUT is None:
        for d in (3, 4, 5, 6):
            check('btn_group: depth %d as the game has it' % d, [w[7] for w in places(T[i:j], d)],
                  [w[7] for w in places(olm.tags[oi:oj], d)])
        for n, r in enumerate(O.ROWS):
            check('btn_group: depth %d at the SHAKE row\'s places' % (8 + n), [w[7] for w in places(T[i:j], 8 + n)],
                  [w[7] for w in places(olm.tags[oi:oj], 3)])
    else:
        scale, row_ys = O.ROW_LAYOUT
        for d, y in sorted(row_ys.items()):
            got = [tuple(round(v, 4) for v in xf[w[7]]) for w in places(T[i:j], d)]
            want = [tuple(round(v, 4) for v in (scale, 0.0, 0.0, scale, x, y)) for x in ox]
            check('btn_group: depth %d at scale %.2f, y %.1f, x as the SHAKE row (%d placements)' % (d, scale, y, len(got)),
                  got, want)
        half = 52 * scale                          # the row's background: -52..52
        ys = sorted(set(row_ys.values()))
        check('rows apart (%.1f) and under the old top edge' % (ys[1] - ys[0]),
              (all(b - a > 2 * half for a, b in zip(ys, ys[1:])), ys[0] - half >= -429 - 52), (True, True))
        check('last row above the TRY button (top 130 - 78)', ys[-1] + half < 130 - 78, True)
    for n, r in enumerate(O.ROWS):
        named = [sy[w[3]] for w in places(T[i:j], 8 + n) if w[0]]
        check('btn_group: depth %d is the row sub_%d' % (8 + n, r[1]), set(named), {'sub_%d' % r[1]})
    k = i + 1
    ok = True
    while k < j:                                   # frame child counts
        t, b = T[k]
        if t in (LM.T_FRAME, LM.T_KEYFRAME):
            n = LM.words(b)[1]
            ok &= all(T[x][0] not in (LM.T_FRAME, LM.T_KEYFRAME, LM.T_LABEL) for x in range(k + 1, k + 1 + n))
            k += 1 + n
        else:
            k += 1
    check('btn_group: frame child counts', ok, True)
    for cid in sorted({LM.words(b)[0] for t, b in T if t == LM.T_SPRITE}):
        si, sj = O.sprite_range(lm, cid)
        depths = [LM.words(b)[5] >> 16 for t, b in T[si:sj] if t == LM.T_PLACE]
        if depths and max(depths) >= LM.words(T[si][1])[6] >> 16:
            check('sprite %d: header depth count %d covers depth %d' % (cid, LM.words(T[si][1])[6] >> 16, max(depths)),
                  False, True)
    check('btn_group: header depth count', LM.words(T[i][1])[6] >> 16, 8 + len(O.ROWS))
    texts = {LM.words(b)[0] for t, b in T if t == 0x25}
    names = {}
    for t, b in T:
        w = LM.words(b) if t == LM.T_PLACE else None
        if w and w[0] in texts and w[3]:
            names.setdefault(w[0], set()).add(sy[w[3]])
    check('every text object placed under one name (as every game layout)',
          sorted(c for c, n in names.items() if len(n) > 1), [])
    for r in O.ROWS:
        check('%s$0: its own text object' % r[4], sum(1 for n in names.values() if n == {r[4] + '$0'}), 2)
    ids = [LM.words(b)[0] for t, b in T if t in (LM.T_SPRITE, 0x25, 0xF022)]
    sprites = [LM.words(b)[0] for t, b in T if t == LM.T_SPRITE]
    props, counts = LM.words(T[lm.ti[0xF00C]][1]), LM.words(T[lm.ti[0xF00D]][1])
    check('ids unique, root sprite last and highest (F00C max id / root)',
          (len(ids) == len(set(ids)), props[3], props[5]), (True, max(ids), sprites[-1]))
    check('F00D counts: shapes, sprites, texts', (counts[0], counts[2], counts[4]),
          (sum(1 for t, b in T if t == 0xF022), len(sprites), len(texts)))
    check('layout parses back', LM.Lm(lm.data()).data() == lm.data(), True)

    def frame_places(cid, label):
        si, sj = O.sprite_range(lm, cid)
        labs = {sy[LM.words(b)[0]]: LM.words(b)[1] for t, b in T[si:sj] if t == LM.T_LABEL}
        if label not in labs:
            return None
        out = {}
        for kind in (LM.T_FRAME, LM.T_KEYFRAME):
            k = next(k for k in range(si, sj) if T[k][0] == kind and LM.words(T[k][1])[0] == labs[label])
            out[kind] = [LM.words(b) for t, b in T[k + 1:k + 1 + LM.words(T[k][1])[1]] if t == LM.T_PLACE]
        return out
    xf = LM.table(T[lm.ti[LM.T_TRANSFORMS]][1], 6)
    pos = LM.table(T[lm.ti[LM.T_POSITIONS]][1], 2)

    def where(m):
        return tuple(pos[m & 0xFFFF]) if m & LM.POS_FLAG else tuple(round(v, 3) for v in xf[m])
    f = frame_places(O.TXT_SPRITE, 'txt_%d' % O.OP_NONE)
    check('txt_mc: txt_14 shows %s$3' % O.NOT_SET, f and [sy[w[3]] for w in f[LM.T_KEYFRAME]], [O.NOT_SET + '$3'])
    for k in O.CLICKS:
        f = frame_places(O.KEY_MC, 'btn_%d' % k[2])
        check('key_mc: btn_%d shows %s$0' % (k[2], k[5]), f and [sy[w[3]] for w in f[LM.T_KEYFRAME]], [k[5] + '$0'])
    for pad, cid in O.PICTURES.items():
        for k in O.CLICKS:
            f = frame_places(cid, 'key_%d' % k[1])
            check('picture %s (%d): key_%d' % (pad, cid, k[1]), f is not None and len(f[LM.T_KEYFRAME]) ==
                  len(frame_places(cid, 'key_9' if pad in O.CLICK_SHOWN else 'off')[LM.T_KEYFRAME]), True)
        if pad in O.CLICK_SHOWN:
            base, line, mark = frame_places(cid, 'key_9')[LM.T_KEYFRAME]
            lb, ll, lmk = frame_places(cid, 'key_14')[LM.T_KEYFRAME]
            rb, rl, rmk = frame_places(cid, 'key_15')[LM.T_KEYFRAME]
            a = xf[line[7]]
            check('picture %s: L line / mark mirror the R stick\'s' % pad,
                  (tuple(round(v, 3) for v in xf[ll[7]]), where(lmk[7])),
                  (tuple(round(v, 3) for v in (-a[0], a[1], -a[2], a[3], -a[4], a[5])),
                   (-1.0, 0.0, 0.0, 1.0, -where(mark[7])[0], where(mark[7])[1])))
            r = xf[rl[7]]
            h = ((where(mark[7])[0] - a[4]) ** 2 + (where(mark[7])[1] - a[5]) ** 2) ** 0.5 / (a[2] ** 2 + a[3] ** 2) ** 0.5
            end = (r[4] + r[2] * h, r[5] + r[3] * h)
            check('picture %s: R line from 100 lower to the R stick %s (%.1f, %.1f)' % (pad, where(mark[7]), end[0], end[1]),
                  (round(r[5] - a[5], 3), abs(end[0] - where(mark[7])[0]) < 0.01, abs(end[1] - where(mark[7])[1]) < 0.01,
                   round((r[0] ** 2 + r[1] ** 2) ** 0.5, 4), round(r[0] * r[2] + r[1] * r[3], 6)),
                  (100.0, True, True, round((a[0] ** 2 + a[1] ** 2) ** 0.5, 4), 0.0))
    ki, kj = O.sprite_range(lm, O.KEY_GROUP)
    check('key_group: header depth count 17', LM.words(T[ki][1])[6] >> 16, O.TOP_DEPTH + 3)
    kframes = {}
    for k in range(ki, kj):
        t, b = T[k]
        if t in (LM.T_FRAME, LM.T_KEYFRAME):
            kframes[(t, LM.words(b)[0])] = [LM.words(x) for tt, x in T[k + 1:k + 1 + LM.words(b)[1]] if tt == LM.T_PLACE]
    bad = []
    for (t, n), ps in sorted(kframes.items()):
        full = t == LM.T_KEYFRAME or n == 0
        by = {w[5] >> 16: w for w in ps}
        if full and (by.get(O.TOP_DEPTH + 2) is None or sy[by[O.TOP_DEPTH + 2][3]] != 'top_mc'):
            bad.append((t, n, 'top_mc'))
        for q, k in enumerate(O.CLICKS):
            w = by.get(O.TOP_DEPTH + q)
            shown = n in O.CLICK_SHOWN.values()
            want_pos = O.CLICK_POS[q] if shown else (0.0, 0.0)
            if w is None or where(w[7]) != want_pos or w[8:10] != ([55, 1] if shown else [120, 1]) or \
                    (full and (sy[w[3]] != 'key_%02d' % k[1] or w[0] != 320)):
                bad.append((t, n, k[0], w))
    check('key_group: key_14 / key_15 at depths 14 / 15 in every frame (shown on typ_1 / typ_2), top_mc at 16', bad, [])
    lab = {sy[LM.words(b)[0]]: LM.words(b)[1] for t, b in T[ki:kj] if t == LM.T_LABEL}
    check('key_group: typ_1 / typ_2 are frames 0 / 1', (lab['typ_1'], lab['typ_2']), (0, 1))

    # msbt
    md = open(menu, 'rb').read()
    m, m0 = Msbt(O.patch_msbt(md)), Msbt(md)
    for r in O.ROWS:
        check('msbt: new label %s' % r[4], m.text(r[4]), r[5])
    for k in O.CLICKS:
        check('msbt: icon label %s' % k[5], m.text(k[5]), k[6])
    check('msbt: other labels unchanged', all(m.text(k) == m0.text(k) for k in m0.labels), True)
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
