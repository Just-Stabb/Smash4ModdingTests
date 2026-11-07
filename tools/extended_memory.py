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

The game: at boot 0x03374EC4 reads MEM2's allocatable size; above 1 GiB it allocates 1 GiB from the tail and
never uses it (0x03374EC8-0x03374EF0: a dev kit's extra RAM) -- skipped (CAP_SITE), else the pack would leave the
arena less than without it. Then 0x03374F38 calls the MEM_ARENA_2 total's getter 0x02010AE8 with r29 = MEM2's free bytes (the
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
# the pools that grow with the pack: (name, size getter, its call sites, size with the pack). Every call of a getter
# is hooked (each pool's block is taken from the arena with one call and the heap made with another: both must agree)
POOLS = (
    ('animation', P.ANIM_GETTER, (0x03326310, 0x03326320), 0x0A000000),    # 46 -> 160 MiB (~14,000 bone-instances)
    ('effect', P.EFFECT_GETTER, (0x033FA2E4, 0x033FA39C), 0x08000000),     # 60 -> 128 MiB (every effect bank's shaders)
    ('resource', P.RESOURCE_GETTER, (0x033FA278, 0x033FA284, 0x033FA330, 0x033FA33C),   # 444 -> 704 MiB (loaded
     0x2C000000),                                                          # files: models, textures, motions ...)
)
ANIM_EXT = POOLS[0][3]
CAVE, LIMIT = 0x04BAF000, 0x04BAF100
HOOK_TOTAL = 0x03374F38
# the game's own 1 GiB cap: when MEM2's allocatable size is > 0x40000000 it allocates 1 GiB from the heap's tail and
# never uses it (a dev kit's extra RAM), so the pack's 1.75 GiB left the arena 0x2EF99F84 (< its total: crash at boot,
# exe_v12 v1, the user's log). The `ble` past it -> `b`: the whole free size is kept.
CAP_SITE, CAP_WORD, CAP_SKIP = 0x03374ED0, 0x40810024, 0x48000024     # ble 0x03374EF4 -> b 0x03374EF4
HOOK_ANIM = POOLS[0][2]
TITLE_IDS = ('0005000010144F00', '0005000010145000', '0005000010110E00')   # US, EU, JP


def lis_value(word):
    assert word >> 16 == 0x3C60, hex(word)                  # lis r3, X
    return (word & 0xFFFF) << 16


def bl(src, dst):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0, (hex(src), hex(dst))
    return (18 << 26) | (off & 0x3FFFFFC) | 1


def ext_total(total, bases):
    """the arena's total with the pack: the base's + what every pool grows by"""
    return total + sum(ext - bases[name] for name, _g, _c, ext in POOLS)


def build(total, bases):
    """(words, labels): total = the arena total getter's value in the base (exe_v11's), bases = {pool: its size}"""
    grow = ext_total(total, bases) - total
    assert total & 0xFFFF == 0 and grow & 0xFFFF == 0 and grow < 0x80000000
    for name, _g, _c, ext in POOLS:
        assert ext >= bases[name] and ext & 0xFFFF == 0 and bases[name] & 0xFFFF == 0, name
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
    """ % dict(T=total >> 16, TH=THRESHOLD >> 16, X=grow >> 16))
    for name, _g, _c, ext in POOLS:
        a.asm("""
    ext_%(n)s:
        lis r12, flag@ha
        lwz r12, flag@l(r12)
        lis r3, 0x%(A)X
        cmpwi r12, 0
        beq %(n)s_out
        lis r3, 0x%(E)X
    %(n)s_out:
        blr
        """ % dict(n=name, A=bases[name] >> 16, E=ext >> 16))
    a.asm("flag:\n.word 0")
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT
    return words, dict(a.labels)


def base_sizes(img):
    return lis_value(img.w(P.ARENA_TOTAL)), {name: lis_value(img.w(g)) for name, g, _c, _e in POOLS}


def args(rpx):
    import kind_expand as K
    img = K.Image(rpx)
    used = [x for x in range(CAVE, LIMIT, 4) if img.w(x)]
    assert not used, 'extended_memory: cave space in use in %s (0x%08X)' % (rpx, used[0])
    total, bases = base_sizes(img)
    hooks = [(HOOK_TOTAL, P.ARENA_TOTAL, 'ext_total')] + [(x, g, 'ext_' + n) for n, g, calls, _e in POOLS for x in calls]
    for at, getter, _l in hooks:
        assert img.w(at) == bl(at, getter), 'extended_memory: 0x%08X is 0x%08X, not bl 0x%08X' % (at, img.w(at), getter)
    assert img.w(CAP_SITE) == CAP_WORD, 'extended_memory: 0x%08X is 0x%08X' % (CAP_SITE, img.w(CAP_SITE))
    words, labels = build(total, bases)
    out = ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out.append('0x%08X=0x%08X' % (CAP_SITE, CAP_SKIP))
    out += ['0x%08X=0x%08X' % (at, bl(at, labels[lab])) for at, _g, lab in hooks]
    return out


RULES = """[Definition]
titleIds = %(ids)s
name = Extended Memory
path = "Super Smash Bros. for Wii U/Mods/Extended Memory"
description = Gives the game %(gib)s GiB of emulated RAM instead of 1 GiB (MEM2 0x%(b)08X-0x%(e)08X).|Needs the modded executable (exe_v12 or later): with it, the extra RAM goes to the animation heap (more model-bearing articles: e.g. four Sephiroths), the effect heap, the file (resource) heap and the general heap.|Without this pack the executable keeps its normal sizes.
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
