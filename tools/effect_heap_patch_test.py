#!/usr/bin/env python3
"""Runs tools/effect_heap_patch.py's executable in unicorn against its base: MEM_ARENA_2's size getters and its bump
allocator (0x03374558 set-up, 0x033746FC take: a block past the end is still handed out, overlapping what follows).

  python3 tools/effect_heap_patch_test.py PATCHED.rpx BASE.rpx

Checks, on the patched executable: the effect / resource / animation heap getters return the patch's sizes; the
arena's total grew by exactly what the animation heap did (so the default heap, MEM2 past the arena, gives it and
no other arena block shrinks); every getter-sized block (in the base's boot order and reversed) still fits in the
arena, with the same slack left as on the base (the arena's fixed-size blocks: 0x34E00000 minus the getters' sum);
and the bump allocator hands out the animation block in full, inside the arena (one past the end would still be
handed out, overlapping the default heap). And that the patched blocks would overflow the base's total (the total
has to grow with them).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import effect_heap_patch as P  # noqa: E402
from kind_expand_test import Emu  # noqa: E402

ARENA_SET, ARENA_TAKE = 0x03374558, 0x033746FC
ARENA_PTR, ARENA_LEFT = 0x104291E0, 0x104291E4
GETTERS = {'arena total': 0x02010AE8, 'small': 0x02010AF0, 'resource': 0x02010AF8, 'big': 0x02010B00,
           'effect': 0x02010B08, 'misc': 0x02010B10, 'animation': 0x02010B18, 'small-block': 0x02010B20}
BASE_ARENA = 0x10000000          # a stand-in arena address (only differences are checked)
fails = 0


def check(what, ok, detail=''):
    global fails
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': ' + detail))


def sizes(e):
    return {k: e.call(a) for k, a in GETTERS.items()}


def bump(e, total, blocks):
    """the arena set up with `total` bytes, then each block taken in turn: [(name, address or 0)]. A block past the
    end isn't refused: 0x033746FC returns the current pointer anyway and only then marks the arena spent (left -1,
    pointer 0), so such a block counts as 0 here (it would overlap whatever follows the arena)"""
    e.setw(ARENA_LEFT, 0)                     # 0x03374558 sets up only an unset arena
    e.call(ARENA_SET, BASE_ARENA, total)
    out = []
    for n, s in blocks:
        a = e.call(ARENA_TAKE, s)
        out.append((n, 0 if e.w(ARENA_LEFT) == 0xFFFFFFFF else a))
    return out


def main():
    new, old = sys.argv[1:3]
    en, eo = Emu(new), Emu(old)
    sn, so = sizes(en), sizes(eo)
    for k in sn:
        print('     %-12s base 0x%08X  patched 0x%08X' % (k, so[k], sn[k]))
    grow = P.ANIM_GROW_MIB << 20
    check('animation heap 22 -> %d MiB' % (22 + P.ANIM_GROW_MIB),
          so['animation'] == 0x01600000 and sn['animation'] == 0x01600000 + grow)
    check('arena total grows by the same', sn['arena total'] - so['arena total'] == grow)
    check('effect heap 60 MiB, resource heap 444 MiB',
          sn['effect'] == 0x03C00000 and sn['resource'] == 0x1BC00000)
    others = [k for k in GETTERS if k not in ('arena total', 'animation')]
    check('no other block changed', all(sn[k] == so[k] for k in others))
    blocks = [k for k in GETTERS if k != 'arena total']
    slack_old = so['arena total'] - sum(so[k] for k in blocks)
    slack_new = sn['arena total'] - sum(sn[k] for k in blocks)
    check('the arena\'s fixed-size room unchanged (0x%X)' % slack_new, slack_new == slack_old and slack_new >= 0,
          'base 0x%X' % slack_old)
    for order in (blocks, blocks[::-1]):
        got = bump(en, sn['arena total'], [(k, sn[k]) for k in order])
        check('every block taken (%s first)' % order[0], all(a for _n, a in got), str(got))
        addr = dict(got)
        check('animation block whole (0x%08X + 0x%X inside the arena)' % (addr['animation'], sn['animation']),
              addr['animation'] and addr['animation'] + sn['animation'] <= BASE_ARENA + sn['arena total'])
        left = en.w(ARENA_LEFT)
        check('left after the getters\' blocks = the fixed-size room (0x%X)' % left, left == slack_new)
    got = bump(eo, so['arena total'], [(k, sn[k]) for k in blocks])
    check('the patched blocks would NOT fit the base\'s total (the total has to grow with them)',
          not all(a for _n, a in got))
    print('\n%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
