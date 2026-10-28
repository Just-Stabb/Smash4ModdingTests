#!/usr/bin/env python3
"""Put each animation's bone tracks in the model's bone order (model.vbn), as vanilla's are.

  python3 tools/omo_sort.py IN.pac MODEL.vbn OUT.pac

Vanilla body motions list their tracks in vbn order, the joint table's 26 bones first (TransN ...
ThrowN). The game draws the model by bone hash, so an animation exported in another order (the
user's Ganondorf: 101 tracks in hierarchy order, ThrowN last) looks right, but its gameplay
joints don't follow it: thrown / captured opponents stayed off ThrowN and hitboxes on those bones
sat elsewhere (docs/ganon-dark-dive.md, v5). Only the order changes: every track samples the same
on every frame (checked). Animations already in order are copied as they are.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omo as O  # noqa: E402


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    src, vbn, dst = sys.argv[1:]
    byh = {h: i for i, (_n, _p, h) in enumerate(O.vbn_read(vbn))}
    out = []
    for name, data in O.pac_read(src):
        o = O.Omo(data)
        order = [byh.get(n[1], len(byh)) for n in o.nodes]
        if order != sorted(order):
            before = {n[1]: [o.sample(n[1], f) for f in range(o.frames)] for n in o.nodes}
            o.nodes.sort(key=lambda n: byh.get(n[1], len(byh)))
            data = o.encode()
            o2 = O.Omo(data)
            assert all(o2.sample(h, f) == v for h, vs in before.items() for f, v in enumerate(vs)), name
            print('%s: reordered (%d tracks)' % (name, len(o.nodes)))
        out.append((name, data))
    O.pac_write(dst, out)


if __name__ == '__main__':
    main()
