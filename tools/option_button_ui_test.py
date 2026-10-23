#!/usr/bin/env python3
"""Checks option_button_ui.py's output against the originals.

  python3 tools/option_button_ui_test.py UI_DIR MENU_MSBT

- xtal: every original instruction outside the replaced tables is in the new code (decoded again
  from the written file) with the same fields, its jumps to the relocated targets; the tables read
  back as wanted; the new identifiers and constants;
- layout: the label sprites' new `sub_11` frame (text named MmenOption_button_85$0), the btn_group
  row sub_11 at depth 8 wherever sub_3 is;
- msbt: the new label, every other text unchanged.
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
        return xtal.read_table(new, s, O.table_end(new, s))[1]
    names = tab(O.NAMES_AT)
    for p in O.ROW_PADS:
        check('%s names: STICK after SMASH' % p, names[p][names[p].index('SMASH') + 1], 'STICK')
    check('FREE_STYLE / REMOTE names unchanged', (names['FREE_STYLE'], names['REMOTE']),
          tuple(xtal.read_table(orig, O.NAMES_AT, O.table_end(orig, O.NAMES_AT))[1][p] for p in ('FREE_STYLE', 'REMOTE')))
    ids, cur, clips = tab(O.IDS_AT), tab(O.CURSOR_AT), tab(O.CLIPS_AT)
    for p in O.ROW_PADS:
        n = names[p]
        check('%s ids / cursor / clips aligned with names' % p, (len(ids[p]), len(cur[p]), len(clips[p])), (len(n),) * 3)
        s, k = n.index('SMASH'), n.index('STICK')
        check('%s cursor: SMASH down STICK, STICK up SMASH' % p, (cur[p][s][1], cur[p][k][0]), ('STICK', 'SMASH'))
        below = cur[p][k][1]
        check('%s cursor: the key below STICK goes up to it' % p, cur[p][n.index(below)][0], 'STICK')
        check('%s clip: sub_11' % p, clips[p][k], ('call', 4, 11))
        check('%s id: null' % p, ids[p][k], None)
    equip = tab(O.EQUIP_AT)
    oequip = xtal.read_table(orig, O.EQUIP_AT, O.table_end(orig, O.EQUIP_AT))[1]
    missing = [(p, k) for p, keys in equip.items() for k, (w, ops) in keys.items() if O.OP_SMASH not in ops]
    check('keys without Smash (windows with no bigger one)', missing, [('FREE_STYLE', 'UP'), ('FREE_STYLE', 'LR'),
                                                                       ('FREE_STYLE', 'DOWN'), ('REMOTE', 'UP')])
    for p, keys in equip.items():
        for k, (w, ops) in keys.items():
            ow, oops = oequip[p][k]
            if ops != oops:
                assert ops == oops + [O.OP_SMASH] and w == ow + 10, (p, k)
    print('     e.g. GC A %s (was %s), GC UP %s (was %s)' % (equip['GC']['A'], oequip['GC']['A'], equip['GC']['UP'], oequip['GC']['UP']))
    check('rows map', tab(O.ROWS_MAP_AT), {'RUMBLE': 1, 'FLICK': 2, 'SMASH': 10, 'SHAKE': 3, 'STICK': 11})
    for name in ('stick_smash', 'set_stick_smash'):
        check('identifier %s' % name, name in [new.resolve(v) for v in new.idents], True)
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
        f = labels.get('sub_11')
        names_in = [sy[LM.words(T[k][1])[3]] for k in range(frames[f] + 1, frames[f] + 1 + LM.words(T[frames[f]][1])[1])
                    if T[k][0] == LM.T_PLACE] if f is not None else []
        check('sprite %d: frame sub_11 shows the new text' % cid, names_in, [O.LABEL + '$0'])
        hdr = LM.words(T[i][1])
        check('sprite %d: header counts' % cid, (hdr[3], hdr[4], hdr[5]),
              (len(labels), len(frames), sum(1 for t, b in T[i:j] if t == LM.T_KEYFRAME)))
    i, j = O.sprite_range(lm, 420)
    rows = [(LM.words(b)[5] >> 16, LM.words(b)[7]) for t, b in T[i:j] if t == LM.T_PLACE and LM.words(b)[5] >> 16 in (3, 8)]
    d3 = [x[1] for x in rows if x[0] == 3]
    d8 = [x[1] for x in rows if x[0] == 8]
    check('btn_group: depth 8 follows depth 3 (%d placements)' % len(d3), d8, d3)
    named = [sy[LM.words(b)[3]] for t, b in T[i:j] if t == LM.T_PLACE and LM.words(b)[5] >> 16 == 8 and LM.words(b)[0]]
    check('btn_group: depth 8 is the row sub_11', set(named), {'sub_11'})
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
    check('layout parses back', LM.Lm(lm.data()).data() == lm.data(), True)

    # msbt
    md = open(menu, 'rb').read()
    m, m0 = Msbt(O.patch_msbt(md)), Msbt(md)
    check('msbt: new label', m.text(O.LABEL), O.TEXT)
    check('msbt: other labels unchanged', all(m.text(k) == m0.text(k) for k in m0.labels), True)
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
