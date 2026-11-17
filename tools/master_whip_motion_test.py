#!/usr/bin/env python3
"""Tests tools/master_whip_motion_cave.py (exe_v46x_whipmot: Byleth's whip, weapon kind 0x1A0, with motion slots past
ZSS's 15) in the patched RPX against the executable it was built on (unicorn for the game's own code).

  python3 tools/master_whip_motion_test.py PATCHED.rpx BASE.rpx [WHIP_MAIN.pac]

- the words: PATCHED differs from BASE only in the claimed region (WM_CAVE - WM_LIMIT) and the motion info's two words;
  the region was zero in BASE; the cave's arguments on PATCHED are the same words (idempotent);
- the game's descriptor getter (0x0320D934, the switch weapon_expand.py hooked, run in unicorn) for every weapon kind
  0 - 0x1BF on both: the same descriptor, and the same motion info (pointer, count, every entry) for every kind but
  0x1A0; 0x1A0's: master_whip.MOTION_COUNT entries, her 60 as before, then 4 per new motion, each the pack loader's
  hash of its .omo name (tools/mtable.py anim_hash);
- with WHIP_MAIN.pac (the whip's motion/whip/main.pac to install): every one of 0x1A0's entries names an animation in
  it (so each slot the scripts play has its animation).
Not run here: the weapon MotionModule's own change of motion (it takes the motion info from the article's set-up,
0x02BCBB20 -> init +0x58, and indexes it by the motion number; Sephiroth's Scintilla flash plays slots past dein's 8
the same way: fighters/edge/README.md test 67).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kind_expand as K  # noqa: E402
import master_whip_motion_cave as C  # noqa: E402
from stage_slot_test import machine, call  # noqa: E402

DESC_GETTER = 0x0320D934
fails = 0


def check(what, ok, detail=''):
    global fails
    print('%s  %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ' (%s)' % detail))
    if not ok:
        fails += 1


def motion_info(mu, kind):
    d = call(mu, DESC_GETTER, 0, kind)
    if not d:
        return d, None
    mi = struct.unpack('>I', bytes(mu.mem_read(d + 8, 4)))[0]
    if not mi:
        return d, (0, 0, b'')
    ents, cnt = struct.unpack('>II', bytes(mu.mem_read(mi, 8)))
    return d, (ents, cnt, bytes(mu.mem_read(ents, 8 * cnt)) if ents and cnt else b'')


def main():
    patched, base = sys.argv[1], sys.argv[2]
    pac = sys.argv[3] if len(sys.argv) > 3 else None
    import master_whip as MW
    P, B = K.Image(patched), K.Image(base)
    diffs = []
    for (pb, pd), (bb, bd) in zip(P.mem, B.mem):
        assert pb == bb
        n = min(len(pd), len(bd))
        for i in range(0, n, 4):
            if pd[i:i + 4] != bd[i:i + 4]:
                diffs.append(pb + i)
        if len(pd) != len(bd):
            diffs.append(('size', pb, len(bd), len(pd)))
    outside = [a for a in diffs if not (isinstance(a, int) and (C.WM_CAVE <= a < C.WM_LIMIT or a in (C.MINFO, C.MINFO + 4)))]
    check('the words: only the region 0x%08X-0x%08X and the motion info 0x%08X / +4 changed (%d words)' % (
        C.WM_CAVE, C.WM_LIMIT, C.MINFO, len(diffs)), not outside, str([hex(a) if isinstance(a, int) else a
                                                                         for a in outside[:8]]))
    check('the region was free (zero) in the base', not any(B.blob(C.WM_CAVE, C.WM_LIMIT - C.WM_CAVE)))
    again = C.build(patched)
    check('the cave on its own result: the same words (asserts pass: idempotent)',
          all(P.w(a) == w for a, w in again.items()))
    mu, mb = machine(patched), machine(base)
    same, bad = 0, []
    for k in range(0x1C0):
        dp, ip = motion_info(mu, k)
        db, ib = motion_info(mb, k)
        if k == C.KIND:
            continue
        if dp != db or ip != ib:
            bad.append(hex(k))
        else:
            same += 1
    check('the descriptor getter: every other kind (0 - 0x1BF) the same descriptor and motion info (%d kinds)' % same,
          not bad and same == 0x1BF, str(bad[:10]))
    dp, (ents, cnt, blob) = motion_info(mu, C.KIND)
    db, (ents0, cnt0, blob0) = motion_info(mb, C.KIND)
    check('0x1A0: the same descriptor (0x%08X), its motion info now {0x%08X, %d} (was {0x%08X, %d})' % (
        dp, ents, cnt, ents0, cnt0), dp == db and ents == C.WM_CAVE and cnt == MW.MOTION_COUNT and cnt0 == 60)
    check('0x1A0: her 60 entries unchanged (C03AttackS4S ... WhipReverse, 4 each)', blob[:480] == blob0)
    hs = struct.unpack('>%dI' % (2 * cnt), blob)
    want = []
    for slot in sorted(MW.NEW_NAMES):
        want += [C.anim_hash(C.PREFIX + MW.NEW_NAMES[slot]), 0] * 4
    check('0x1A0: entries 60 - %d = the new motions\' hashes, 4 each (%s ... %s)' % (
        cnt - 1, MW.NEW_NAMES[60], MW.NEW_NAMES[max(MW.NEW_NAMES)]), list(hs[120:]) == want)
    for slot in (MW.OVT_SLOT, MW.HIT_SLOT(0), MW.PULL_SLOT(5)):
        for c in range(4):
            i = slot + c
            check('0x1A0 slot %d (+ custom %d) -> %s' % (slot, c, MW.NEW_NAMES[slot]),
                  hs[2 * i] == C.anim_hash(C.PREFIX + MW.NEW_NAMES[slot]))
    if pac:
        import omo
        names = {C.anim_hash(n[:-4]) for n, _d in omo.pac_read(pac)}
        miss = sorted({hs[2 * i] for i in range(cnt)} - names)
        check('%s: every motion-info entry of 0x1A0 has its animation (%d names)' % (os.path.basename(pac), len(names)),
              not miss, ', '.join('0x%08X' % h for h in miss))
    print('\n%d failure(s)' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
