#!/usr/bin/env python3
"""Stage select: start stages on their Omega form by swapping each stage's normal and Omega kinds in
param/ui/ui_stage_db.bin (data only; no code).

  python3 tools/stage_db_omega_swap.py IN_ui_stage_db.bin OUT_ui_stage_db.bin [--ids 1,4,5,...] [--from-4xm 4XM_DB]
          [--except 30,29,...]

User: "I think my original, older modified UI had some way of changing what the default Omega variant for
a stage was"; the stage pack they used is based on 4xM, whose ui_stage_db.bin sets 53 stages' normal kind
([6] / [7]) to the stage's Omega kind ([8] / [9]), so a stage is always picked as its Omega (the Omega
switch then picks the Omega too: the normal form can't be reached). Here the two are swapped instead: the
switch's normal state gives the Omega stage, its Omega state the original, and the max-fighter counts
([11] normal / [12] Omega) go with their stages. Entry layout: tools/add_stage.py's docstring.

--ids: the cosmetic ids to swap (default: the 53 4xM makes Omega (Battlefield 1, Mario U 4 ... DLC 48-55;
4xM's other two changes, Galaxy 2 -> kind 69 and Divide 252, are not Omega swaps and are left out) minus
--except (default USER_KEEP_NORMAL, the user's list of stages that stay normal; --except '' for none).
--from-4xm: derive the ids from a 4xM ui_stage_db.bin instead (entries whose normal kind is the vanilla
db's Omega kind need IN to be vanilla-kinded). Stages already swapped (normal kind != the db's own
normal) are not swapped back: run it once on a db with the game's pairing.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s4param  # noqa: E402

FOURXM_IDS = (1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
              30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55)
# user: stages that keep their normal form as the default (and every modded stage, ids 0x38+, which aren't
# in FOURXM_IDS): Smashville 30, Town and City 29, Duck Hunt 39, Big Battlefield 47, Mushroom Kingdom U 4,
# Delfino Plaza 7, Mario Circuit 5, Mario Circuit (Brawl) 8, Yoshi's Island 16, Skyloft 11, Bridge of Eldin 12,
# Pyrosphere 13, Garden of Hope 24, PAC-LAND 44, Boxing Ring 36, Wrecking Crew 40, Miiverse 46,
# Peach's Castle (64) 50, Super Mario Maker 52, Umbra Clock Tower 55
USER_KEEP_NORMAL = (30, 29, 39, 47, 4, 7, 5, 8, 16, 11, 12, 13, 24, 44, 36, 40, 46, 50, 52, 55)
PAIRS = ((6, 8), (7, 9), (11, 12))      # normal kind / Omega kind, alternates, max fighters


def entries(items):
    g = items[0]
    assert g[0] == 'group', g[:2]
    return g[2]


def swap(data, ids):
    """-> (new bytes, [(id, normal kind before, Omega kind before)])"""
    items = s4param.parse(data)
    done = []
    for row in entries(items):
        cid = row[0][1]
        if cid not in ids:
            continue
        n, o = row[6][1], row[8][1]
        if n == o:              # no Omega form of its own (e.g. a stage whose two kinds are the same)
            continue
        for a, b in PAIRS:
            row[a], row[b] = (row[a][0], row[b][1]), (row[b][0], row[a][1])
        done.append((cid, n, o))
    return s4param.build(items), done


def ids_from_4xm(vanilla, fourxm):
    v = {r[0][1]: r for r in entries(s4param.parse(vanilla))}
    return sorted(r[0][1] for r in entries(s4param.parse(fourxm))
                  if r[0][1] in v and r[6][1] != v[r[0][1]][6][1] and r[6][1] == v[r[0][1]][8][1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp')
    ap.add_argument('out')
    ap.add_argument('--ids')
    ap.add_argument('--from-4xm')
    ap.add_argument('--except', dest='keep', default=','.join(map(str, USER_KEEP_NORMAL)))
    a = ap.parse_args()
    data = open(a.inp, 'rb').read()
    if a.ids:
        ids = {int(x, 0) for x in a.ids.split(',')}
    elif a.from_4xm:
        ids = set(ids_from_4xm(data, open(a.from_4xm, 'rb').read()))
    else:
        ids = set(FOURXM_IDS)
    if not a.ids:
        ids -= {int(x, 0) for x in a.keep.split(',') if x.strip()}
    out, done = swap(data, ids)
    open(a.out, 'wb').write(out)
    print('swapped %d stages: %s' % (len(done), ' '.join('%d(%d<->%d)' % d for d in done)))


if __name__ == '__main__':
    main()
