#!/usr/bin/env python3
"""Checks tools/smashrun_menu.py's build against the files it was built from:

  python3 tools/smashrun_menu_test.py OTHER_DIR MENU_MSBT BUTTON_SEQ IN.rpx OUT

- other.lm: parses; the root is still the last character and F00C names it; F00D's shape / sprite / text counts
  are the tags'; every placement's character exists; btn_08 is the copied Group button (a sprite with 'in' /
  'out', its frames placing the same shared pieces as Group's) at the right side, 4xm_08 over it; the copy's
  title / icon shapes sample the new atlas regions, the Group button still samples its own; every other
  placement unchanged.
- textures: the new regions hold the title / star; everything else of each atlas is as before (BC re-encode of
  untouched blocks gives the same decoded pixels).
- menu.msbt: MmenOther_8 / 8h added, every old text kept. ui_button_sequence.bin: entry 115 (msbt 8, button 8),
  page 16 lists 8 ids (59 55 56 57 58 60 61 115), everything else as before.
- cross_f.rpx (unicorn): the Games & More button list (0x02C8C280) with a fake view: 8 buttons, the 8th
  button number 8, enabled, result 7, shown, id 115; the 7 vanilla ones as before (0x029ABC98 run for real up to
  its data lookups, which are stubbed); result 7's case posts key 0x31.
"""
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chara_layout as cl  # noqa: E402
import lm_render  # noqa: E402
import msbt  # noqa: E402
import nut  # noqa: E402
import rpx_patch  # noqa: E402
import s3ds_ui as su  # noqa: E402
import smashrun_menu as M  # noqa: E402

FAILS = []


def check(cond, what):
    print(('ok    ' if cond else 'FAIL  ') + what)
    if not cond:
        FAILS.append(what)


def movie_checks(src_dir, out_dir):
    old = cl.Lm(open(os.path.join(src_dir, 'other.lm'), 'rb').read())
    new = cl.Lm(open(os.path.join(out_dir, 'other.lm'), 'rb').read())
    T = new.tags
    ids = {}
    for t, b in T:
        if t in (cl.T_SPRITE, 0xF022, 0x25):
            ids[cl.words(b)[0]] = t
    ci, ra, rb = su.lm_root(new)
    cw = cl.words(T[ci][1])
    root = cl.words(T[ra][1])[0]
    check(root == max(ids) == cw[3] == cw[5], 'root sprite %d = last character = F00C words 3/5' % root)
    dw = cl.words(T[new.ti[0xF00D]][1])
    counts = [sum(1 for t, _ in T if t == k) for k in (0xF022, cl.T_SPRITE, 0x25)]
    check([dw[0], dw[2], dw[4]] == counts, 'F00D counts %s = tags %s' % ([dw[0], dw[2], dw[4]], counts))
    missing = sorted({cl.words(b)[0] for t, b in T if t == cl.T_PLACE} - set(ids) - {cl.NONE, 0})
    check(not missing, 'every placed character exists %s' % missing[:5])
    mv = lm_render.Movie(out_dir)
    sy = new.sy
    btn = [cl.words(b) for t, b in T[ra:rb] if t == cl.T_PLACE and cl.words(b)[3] == sy.index('btn_08')]
    hit = [cl.words(b) for t, b in T[ra:rb] if t == cl.T_PLACE and cl.words(b)[3] == sy.index('4xm_08')]
    cid = btn[0][0]
    check(all(w[0] == cid for w in btn) and ids.get(cid) == cl.T_SPRITE and
          {'in', 'out'} <= set(mv.sprites[cid][1]), 'btn_08 = a sprite with in / out (%d)' % cid)
    m = mv.matrix(btn[0][7])
    check(1000 < m[4] < 1920 and 0 < m[5] < 1080, 'btn_08 on the right (%.0f, %.0f)' % (m[4], m[5]))
    h = mv.matrix(hit[0][7])
    check(abs(h[4] - m[4]) < 1 and abs(h[5] - m[5]) < 1, '4xm_08 over it')
    # the copy's shapes vs the Group button's
    copy_shapes = set()

    def walk(c, out):
        if c in mv.shapes:
            out.add(c)
        elif c in mv.sprites:
            for f in mv.sprites[c][0]:
                for t, b in f:
                    if t == cl.T_PLACE:
                        k = cl.words(b)[0]
                        if k not in out:
                            out.add(k)
                            walk(k, out)
    walk(cid, copy_shapes)
    group_shapes = set()
    walk(M.GROUP_BTN, group_shapes)
    new_shapes = sorted(c for c in copy_shapes - group_shapes if c in mv.shapes)
    check(len(new_shapes) == 2 and M.TEXT_SHAPE in group_shapes and M.ICON_SHAPE in group_shapes and
          M.TEXT_SHAPE not in copy_shapes and M.ICON_SHAPE not in copy_shapes,
          'the copy has its own title / icon shapes %s, the rest shared' % new_shapes)
    regions = []
    for c in new_shapes:
        (atlas, _f, v, _i), = mv.shapes[c]
        th, tw = mv.tex[atlas].shape[:2]
        regions.append((atlas, int(round(v[:, 2].min() * tw)), int(round(v[:, 3].min() * th))))
    check(sorted(regions) == sorted([(0, M.STAR_AT[0], M.STAR_AT[1]), (3, M.TITLE_AT[0], M.TITLE_AT[1])]),
          'they sample the star / title regions %s' % regions)
    # other placements unchanged: compare the old root's placements except btn_08 / 4xm_08
    oc, oa, ob = su.lm_root(old)
    keep = lambda lm, a, b: [cl.words(x) for t, x in lm.tags[a:b] if t == cl.T_PLACE and  # noqa: E731
                             cl.words(x)[3] not in (lm.sy.index('btn_08'), lm.sy.index('4xm_08'))]
    check(keep(old, oa, ob) == keep(new, ra, rb), 'every other root placement unchanged')
    # texture regions
    for atlas, at, size in ((3, M.TITLE_AT, M.TITLE_SIZE), (0, M.STAR_AT, (M.STAR_SIZE, M.STAR_SIZE))):
        d0, t0 = nut.load(os.path.join(src_dir, 'img-%05d.nut' % atlas))
        d1, t1 = nut.load(os.path.join(out_dir, 'img-%05d.nut' % atlas))
        a0, a1 = nut.decode(d0, t0[0]).astype(int), nut.decode(d1, t1[0]).astype(int)
        x, y = at
        w, hh = size
        mask = np.ones(a0.shape[:2], bool)
        mask[y:y + hh, x:x + w] = False
        # blocks touching the region may differ in the re-encode: compare away from it by one block
        mask[max(0, y - 4):y + hh + 4, max(0, x - 4):x + w + 4] = False
        ch = 2 if atlas == 3 else 1
        diff = np.abs(a0[mask][:, :ch] - a1[mask][:, :ch]).max()
        check(diff <= 0, 'atlas %d unchanged outside the new region (max diff %d)' % (atlas, diff))
        reg = a1[y:y + hh, x:x + w, :ch]
        check(reg[..., -1].max() > 200, 'atlas %d region has the new art' % atlas)


def text_checks(src_msbt, out_msbt, src_seq, out_seq):
    a = msbt.Msbt(open(src_msbt, 'rb').read())
    b = msbt.Msbt(open(out_msbt, 'rb').read())
    check(all(b.text(k) == a.text(k) for k in a.labels), 'menu.msbt: old texts kept')
    check(b.text('MmenOther_8') == M.TITLE and b.text('MmenOther_8h') == M.HELP, 'MmenOther_8 / 8h')
    import s3ds_ui
    va = s3ds_ui.flat_values(open(src_seq, 'rb').read()[8:])
    vb = s3ds_ui.flat_values(open(out_seq, 'rb').read()[8:])
    g = [i for i, v in enumerate(vb) if isinstance(v, dict)]
    check(vb[0] == {'group': 116}, 'group 1: 116 entries')
    e115 = vb[g[1] - 14:g[1]]
    check(e115[:8] == [115, 8, 3, 1, 0, 0, 8, 0xFFFFFFFF], 'entry 115 %s' % e115[:8])
    per = 24
    p16 = g[2] + 1 + 16 * per
    check(vb[p16 + 1] == 'MmenOther_' and vb[p16 + 12] == 8 and vb[p16 + 13:p16 + 21] ==
          [59, 55, 56, 57, 58, 60, 61, 115], 'page 16: 8 ids %s' % vb[p16 + 13:p16 + 21])
    # everything but the inserted entry, the group-1 count and page 16's count / slot
    ga = [i for i, v in enumerate(va) if isinstance(v, dict)]
    flat_a = va[1:ga[1]] + va[ga[1]:]
    flat_b = vb[1:g[1] - 14] + vb[g[1]:]
    diffs = [i for i, (x, y) in enumerate(zip(flat_a, flat_b)) if x != y]
    check(len(flat_a) == len(flat_b) and len(diffs) == 2, 'nothing else changed (%d other differences)' % (len(diffs) - 2))


def rpx_checks(path):
    from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
    R = {n: getattr(__import__('unicorn.ppc_const', fromlist=['x']), 'UC_PPC_REG_%d' % n) for n in range(32)}
    from unicorn.ppc_const import UC_PPC_REG_LR
    d, _shoff, _ent, secs = rpx_patch.load(path)
    uc = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    uc.mem_map(0x02000000, 0x03000000)
    for s in secs:
        if s[1] == 1 and s[3] and 0x02000000 <= s[3] < 0x05000000:
            uc.mem_write(s[3], bytes(rpx_patch.section_data(d, s)))
    VIEW, STACK = 0x30000000, 0x31000000
    uc.mem_map(VIEW, 0x10000)
    uc.mem_map(STACK - 0x10000, 0x20000)
    BLR = 0x4E800020
    calls = []

    from unicorn.ppc_const import UC_PPC_REG_PC

    def ret(u):
        u.reg_write(UC_PPC_REG_PC, u.reg_read(UC_PPC_REG_LR))

    def hook(u, addr, size, _):
        if addr == 0x029ABAA4:              # the list's set-up (clears the arrays): skipped
            ret(u)
        elif addr == 0x029ABC98:            # the stock adder: recorded, skipped (its data lookups need the db)
            calls.append(('stock', u.reg_read(R[4]), u.reg_read(R[5])))
            ret(u)
        elif addr == M.SET_BUTTON:          # the direct adder: recorded, then run for real
            calls.append(('set', u.reg_read(R[4]), u.reg_read(R[5]), u.reg_read(R[6]), u.reg_read(R[7]),
                          u.reg_read(R[8])))
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.reg_write(R[3], VIEW)
    uc.reg_write(R[1], STACK)
    uc.reg_write(UC_PPC_REG_LR, 0x02000000)
    uc.mem_write(0x02000000, struct.pack('>I', BLR))
    uc.emu_start(0x02C8C280, 0x02000000, count=2000)
    stock = [c for c in calls if c[0] == 'stock']
    check([(c[1], c[2]) for c in stock] == [(0x3B, 8), (0x37, 3), (0x38, 4), (0x39, 5), (0x3A, 6), (0x3C, 9),
                                            (0x3D, 10)], 'the 7 vanilla buttons as before')
    sets = [c for c in calls if c[0] == 'set']
    check(sets == [('set', 8, 1, M.RESULT, 1, M.BUTTON_ID)], 'then button 8: enabled, result 7, shown, id 115 %s' % sets)
    n = struct.unpack('>I', uc.mem_read(VIEW + 0x144, 4))[0]
    row = (struct.unpack('>I', uc.mem_read(VIEW + 0x188, 4))[0], uc.mem_read(VIEW + 0x1C8, 1)[0],
           struct.unpack('>I', uc.mem_read(VIEW + 0x148, 4))[0], uc.mem_read(VIEW + 0x1D8, 1)[0],
           struct.unpack('>I', uc.mem_read(VIEW + 0x1E8, 4))[0])
    check(n == 1 and row == (8, 1, 7, 1, 115), 'the arrays: count %d, row %s (stock adders stubbed)' % (n, row))
    key = rpx_patch.read_u32(d, secs, M.KEY_SITE)
    check(key == 0x38800000 | M.TRAINING_KEY, 'result 7 posts key 0x%X' % (key & 0xFFFF))


def main():
    src_dir, src_msbt, src_seq, _rpx, out = sys.argv[1:6]
    movie_checks(src_dir, os.path.join(out, 'ui', 'lumen', 'other'))
    text_checks(src_msbt, os.path.join(out, 'ui', 'message', 'menu.msbt'), src_seq,
                os.path.join(out, 'param', 'ui', 'ui_button_sequence.bin'))
    rpx_checks(os.path.join(out, 'code', 'cross_f.rpx'))
    print('%d failures' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
