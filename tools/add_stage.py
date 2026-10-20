#!/usr/bin/env python3
"""The files for a new stage slot (tools/stage_slot_cave.py makes the RPX side), copied from an
existing stage: its folders, icons, stage-select database entry, song list (My Music) and names.

  python3 tools/add_stage.py --param PARAM_DIR --ui UI_DIR --stage STAGE_DIR --out OUT_DIR
          [--name NewStage01] [--cosmetic 0x38] [--kind 0x80] [--from BattleField_f [--from-cosmetic ID]]
          [--title "New Stage"] [--series TEXT] [--page 1|2]

PARAM_DIR   data/param (ui/ui_stage_db.bin, ui/ui_sound_db.bin)
UI_DIR      data/ui (message/melee.msbt, replace/stage/<set>/<set>_<Name>.nut)
STAGE_DIR   data/stage (melee/<Name>, end/<Name>)
OUT_DIR     gets param/ui/{ui_stage_db,ui_sound_db}.bin, ui/message/melee.msbt (data/... in the game),
            ui/replace/stage/*/<set>_<name>.nut, stage/{melee,end}/<name>

--kind is the new stage's normal kind (Omega is kind + 1): stage_slot_cave.py gives the i-th new
stage 0x80 + 2i. --page 1 puts it on the stage select's first page, which has one free slot (48
slots, 47 stages); --page 2 with the DLC stages (the entry's DLC byte, +0x0C, as theirs).

ui_stage_db.bin (one entry a stage, 25 values; ids below 0xC8 are looked up by position, so the
new entry goes at position COSMETIC): [0] cosmetic id, [1] on the stage select, [2] series,
[3] DLC page, [4] (set with [3]), [5], [6] / [7] stage kind (and alternate), [8] / [9] Omega kind
(and alternate), [10] stage-select order (byte +0x20, the sort key), [11] / [12] max fighters
(normal / Omega), ..., [20] (a running number), ... The new entry is the source stage's with its
own id, kinds, order (after every other) and page.
"""
import argparse
import copy
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msbt  # noqa: E402
import s4param  # noqa: E402


def group(items):
    return next(it for it in items if isinstance(it, list) and it[0] == 'group')


def entry_of(g, ident):
    return next(e for e in g[2] if e[0][1] == ident)


def setv(e, i, v):
    e[i] = (e[i][0], v)


def insert(g, pos, e):
    ids = [x[0][1] for x in g[2]]
    assert e[0][1] not in ids, 'id 0x%X is already in the database' % e[0][1]
    assert all(ids[k] == k for k in range(pos)), 'positions before %d aren\'t ids 0..%d' % (pos, pos - 1)
    g[2].insert(pos, e)
    g[1] = len(g[2])


def stage_db(path, src, cos, kind, page):
    data = open(path, 'rb').read()
    items = s4param.parse(data)
    g = group(items)
    e = copy.deepcopy(entry_of(g, src))
    order = max(x[10][1] for x in g[2] if x[0][1] < 0xC8) + 1
    run = max(x[20][1] for x in g[2]) + 1
    setv(e, 0, cos)
    setv(e, 1, 1)
    setv(e, 3, 1 if page == 2 else 0)
    setv(e, 4, 1 if page == 2 else 0)
    for i in (6, 7):
        setv(e, i, kind)
    for i in (8, 9):
        setv(e, i, kind + 1)
    setv(e, 10, order)
    setv(e, 20, run)
    insert(g, cos, e)
    return s4param.build(items, data[:8]), e


def sound_db(path, src, cos):
    data = open(path, 'rb').read()
    items = s4param.parse(data)
    g = group(items)
    e = copy.deepcopy(entry_of(g, src))
    setv(e, 0, cos)
    insert(g, cos, e)
    return s4param.build(items, data[:8]), e


def copy_stage(src_dir, dst_dir, src, name):
    """the folder with the source's name in file names replaced"""
    for root, _dirs, files in os.walk(src_dir):
        rel = os.path.relpath(root, src_dir)
        os.makedirs(os.path.join(dst_dir, rel), exist_ok=True)
        for f in files:
            shutil.copyfile(os.path.join(root, f), os.path.join(dst_dir, rel, f.replace(src, name)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--param', required=True)
    ap.add_argument('--ui', required=True)
    ap.add_argument('--stage', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--name', default='NewStage01')
    ap.add_argument('--cosmetic', default='0x38')
    ap.add_argument('--kind', default='0x80')
    ap.add_argument('--from', dest='src', default='BattleField_f')
    ap.add_argument('--from-cosmetic', default=None, help='the source stage\'s cosmetic id (DLC stages)')
    ap.add_argument('--title', default='New Stage')
    ap.add_argument('--series', default=None)
    ap.add_argument('--page', type=int, default=1, choices=(1, 2))
    a = ap.parse_args()
    cos, kind = int(a.cosmetic, 0), int(a.kind, 0)
    out = a.out

    # the source's cosmetic id: its stage-kind name (melee) -> ui_stage_db entry with that kind
    items = s4param.parse(open(os.path.join(a.param, 'ui', 'ui_stage_db.bin'), 'rb').read())
    if a.from_cosmetic:
        src_cos = int(a.from_cosmetic, 0)
    else:
        src_kind = MELEE_KINDS.index(a.src)
        src_cos = next(e[0][1] for e in group(items)[2] if e[6][1] == src_kind and e[0][1] != 0)  # 0: random

    os.makedirs(os.path.join(out, 'param', 'ui'), exist_ok=True)
    db, e = stage_db(os.path.join(a.param, 'ui', 'ui_stage_db.bin'), src_cos, cos, kind, a.page)
    open(os.path.join(out, 'param', 'ui', 'ui_stage_db.bin'), 'wb').write(db)
    sdb, se = sound_db(os.path.join(a.param, 'ui', 'ui_sound_db.bin'), src_cos, cos)
    open(os.path.join(out, 'param', 'ui', 'ui_sound_db.bin'), 'wb').write(sdb)

    m = msbt.Msbt(open(os.path.join(a.ui, 'message', 'melee.msbt'), 'rb').read())
    m.set('MmelStageN_' + a.name, a.title)
    m.set('MmelStageG_' + a.name, a.series if a.series is not None else m.text('MmelStageG_' + a.src))
    os.makedirs(os.path.join(out, 'ui', 'message'), exist_ok=True)
    open(os.path.join(out, 'ui', 'message', 'melee.msbt'), 'wb').write(m.build())

    icons = []
    rs = os.path.join(a.ui, 'replace', 'stage')
    for st in sorted(os.listdir(rs)):
        f = os.path.join(rs, st, '%s_%s.nut' % (st, a.src))
        if os.path.exists(f):
            os.makedirs(os.path.join(out, 'ui', 'replace', 'stage', st), exist_ok=True)
            shutil.copyfile(f, os.path.join(out, 'ui', 'replace', 'stage', st, '%s_%s.nut' % (st, a.name)))
            icons.append(st)

    for v in ('melee', 'end'):
        copy_stage(os.path.join(a.stage, v, a.src), os.path.join(out, 'stage', v, a.name), a.src, a.name)

    print('%s (from %s, cosmetic 0x%X): cosmetic 0x%X, kinds 0x%X / 0x%X, page %d, order %d' %
          (a.name, a.src, src_cos, cos, kind, kind + 1, a.page, e[10][1]))
    print('  ui_stage_db entry:', ' '.join(str(v) for _, v in e))
    print('  ui_sound_db songs:', ' '.join(str(v) for _, v in se[:se[1][1] + 2]))
    print('  icons:', ', '.join(icons))


# stage kinds 0x00-0x2E (stage/melee), the order of the game's stage-kind table (0x1011D95C)
MELEE_KINDS = ['BattleField_f', 'End_f', 'Galaxy', 'MarioU', 'MarioKart', 'Kalos', 'Skyward', 'DKReturns',
               'Metroid', 'YoshiU', 'Cave', 'Village2', 'Assault', 'Colloseum_f', 'PikminU', 'Angeland',
               'Gamer', 'DuckHunt', 'Wrecking', 'XenoBlade', 'PunchOut', 'PunchOut2', 'Wufu', 'Miiverse',
               'WiiFit', 'Pilotwings', 'Windyhill', 'Pacland', 'Wily', 'Gw3', 'XDolpic', 'XKart', 'XStadium',
               'XOldin', '64Jungle', 'XNorfair', 'DxYorster', 'XHalberd', 'XVillage', 'XStarfox', 'XEmblem',
               'XPalutena', 'XFzero', 'DxOnett', 'XDonkey', 'DxShrine', 'XMansion']

if __name__ == '__main__':
    main()
