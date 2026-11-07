#!/usr/bin/env python3
"""Extended Memory for Smash 4 on Cemu: a graphic pack that maps more emulated RAM (MEM2) and an executable patch
that, only when that RAM is there, gives it to the animation heap (the limit four Sephiroths hit).

  python3 tools/extended_memory.py --rpx BASE.rpx                 rpx_patch.py arguments (BASE: exe_v11 or later)
  python3 tools/extended_memory.py --pack OUT_DIR                 write the graphic pack folder (rules.txt)

The RAM: Cemu's graphic packs (version 6+) may move an MMU range's end with a [RAM] `mappingN = start-end` line
whose start is the range's base (Cemu src/Cafe/HW/MMU/MMU.cpp memory_mapForCurrentTitle; MEM2 is 0x10000000-
0x50000000, the next range the optional overlay arena at 0xA0000000). Cemu's OSGetMemBound(MEM2) is the range's end
minus what the loader took (coreinit_Memory.cpp: mmuRange_MEM2.getEnd() - currentRPLAllocatorOffset), so the game
sees the bigger MEM2 by itself. MEM2_END keeps every address below 0x80000000 (no pointer the game might compare
signed goes negative): MEM2 1 GiB -> 1.75 GiB.

The game: at boot 0x03374F38 calls the MEM_ARENA_2 total's getter 0x02010AE8 with r29 = MEM2's free bytes (the
`MEM_ARENA_2 ptr=.., freeBytes=..` OSReport just before); the arena is the top `total` bytes, the default heap the
rest (tools/effect_heap_patch.py). Later 0x03326310 / 0x03326320 call the animation heap's getter 0x02010B18 (its
block taken from the arena, the heap made over it). Hooks (each a `bl` re-aimed at the cave):
- 0x03374F38 -> ext_total: the getter's value (effect_heap_patch.py's, exe_v11: 0x36600000); when r29 >=
  THRESHOLD (the RAM is extended) + ANIM_EXT - the animation getter's value, and a flag set.
- 0x03326310, 0x03326320 -> ext_anim: the animation getter's value (exe_v11: 46 MiB), ANIM_EXT when the flag is set.
Without the pack (MEM2 free ~1007 MiB < THRESHOLD) both return exe_v11's values: the executable behaves as v11. The
getters themselves are unchanged (2 words each, no room for a far branch; nothing else calls them). With the pack
the default heap grows from ~138 MiB to ~776 MiB (MEM2 free ~1775 MiB minus the arena's ~999 MiB) and the
animation heap is ANIM_EXT.
Space: CAVE 0x04BAF000-0x04BAF100 (zero in exe_v11, after diag_stomp_cave.py's 0x04BAE000-0x04BAF000, in b reach of
the three hooks). Test: tools/extended_memory_test.py.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402
import effect_heap_patch as P  # noqa: E402

MEM2_BASE, MEM2_END = 0x10000000, 0x80000000
THRESHOLD = 0x50000000           # MEM2 free bytes from which the RAM counts as extended (1.25 GiB; normal ~1007 MiB)
ANIM_EXT = 0x0A000000            # the animation heap with the pack: 160 MiB (~14,000 bone-instances; 4 Sephiroths
                                 # ~5,100, 8 ~10,200)
CAVE, LIMIT = 0x04BAF000, 0x04BAF100
HOOK_TOTAL = 0x03374F38
HOOK_ANIM = (0x03326310, 0x03326320)
TITLE_IDS = ('0005000010144F00', '0005000010145000', '0005000010110E00')   # US, EU, JP


def lis_value(word):
    assert word >> 16 == 0x3C60, hex(word)                  # lis r3, X
    return (word & 0xFFFF) << 16


def bl(src, dst):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0, (hex(src), hex(dst))
    return (18 << 26) | (off & 0x3FFFFFC) | 1


def build(total, anim):
    """(words, labels): total / anim = the getters' values in the base (exe_v11's)"""
    assert ANIM_EXT > anim and (ANIM_EXT - anim) & 0xFFFF == 0 and total & 0xFFFF == 0
    a = Asm(CAVE)
    a.asm("""
    ext_total:
        lis r3, 0x%(T)X
        lis r12, 0x%(TH)X
        cmplw r29, r12
        blt t_out
        addis r3, r3, 0x%(X)X
        lis r12, flag@ha
        li r11, 1
        stw r11, flag@l(r12)
    t_out:
        blr
    ext_anim:
        lis r12, flag@ha
        lwz r12, flag@l(r12)
        lis r3, 0x%(A)X
        cmpwi r12, 0
        beq a_out
        lis r3, 0x%(E)X
    a_out:
        blr
    flag:
        .word 0
    """ % dict(T=total >> 16, TH=THRESHOLD >> 16, X=(ANIM_EXT - anim) >> 16, A=anim >> 16, E=ANIM_EXT >> 16))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT
    return words, dict(a.labels)


def args(rpx):
    import kind_expand as K
    img = K.Image(rpx)
    used = [x for x in range(CAVE, LIMIT, 4) if img.w(x)]
    assert not used, 'extended_memory: cave space in use in %s (0x%08X)' % (rpx, used[0])
    total, anim = lis_value(img.w(P.ARENA_TOTAL)), lis_value(img.w(P.ANIM_GETTER))
    for at, getter in [(HOOK_TOTAL, P.ARENA_TOTAL)] + [(x, P.ANIM_GETTER) for x in HOOK_ANIM]:
        assert img.w(at) == bl(at, getter), 'extended_memory: 0x%08X is 0x%08X, not bl 0x%08X' % (at, img.w(at), getter)
    words, labels = build(total, anim)
    out = ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out.append('0x%08X=0x%08X' % (HOOK_TOTAL, bl(HOOK_TOTAL, labels['ext_total'])))
    out += ['0x%08X=0x%08X' % (x, bl(x, labels['ext_anim'])) for x in HOOK_ANIM]
    return out


RULES = """[Definition]
titleIds = %(ids)s
name = Extended Memory
path = "Super Smash Bros. for Wii U/Mods/Extended Memory"
description = Gives the game %(gib)s GiB of emulated RAM instead of 1 GiB (MEM2 0x%(b)08X-0x%(e)08X).|Needs the modded executable (exe_v12 or later): with it, the extra RAM goes to the animation heap (more model-bearing articles: e.g. four Sephiroths) and the general heap.|Without this pack the executable keeps its normal sizes.
version = 6

[RAM]
mapping0 = 0x%(b)08X-0x%(e)08X # extend MEM2 (default range is 0x10000000-0x50000000); kept below 0x80000000
"""


def write_pack(out):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'rules.txt'), 'w') as f:
        f.write(RULES % dict(ids=','.join(TITLE_IDS), b=MEM2_BASE, e=MEM2_END,
                             gib=('%g' % ((MEM2_END - MEM2_BASE) / (1 << 30)))))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx')
    ap.add_argument('--pack')
    a = ap.parse_args()
    if a.pack:
        write_pack(a.pack)
    if a.rpx:
        print(' '.join(args(a.rpx)))


if __name__ == '__main__':
    main()
