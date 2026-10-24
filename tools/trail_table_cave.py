#!/usr/bin/env python3
"""Sword trail textures for new fighters: the trail-name table, copied into the grown code space
with new names after the game's 259. Prints rpx_patch.py arguments.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx ... $(python3 tools/trail_table_cave.py IN.rpx)

The game's table (`0x10423E60`, 259 pointers to names, docs/native-notes.md "Sword trails"): an ACMD
`Sword_Glow` / `Sword_Glow2` / `Sword_Trace` texture id N (1-based) is `table[N - 1]`; the trail
set-up (`0x032F515C`) formats `"%s.nut"` (`0x10192344`) from it and looks the texture up by that
name among the loaded trail textures (`effect/<fighter>/trail/*.nut`). It indexes the table with no
bound (`lwzx` from `0x10423E5C`, built at `0x032F53A4` / `0x032F53B0`, its only reference), and the
words after it are other variables, so the table can't grow in place: the copy gets the new names
(ids 260 on, NEW_TRAILS) and those two instructions point at it (their relocations moved to a dead
word, as the other caves do: the loader would otherwise rewrite them).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rpx_patch  # noqa: E402

CAVE = 0x04B9B000               # free grown space: smash_button_cave.py ends here, kind_expand.py starts at 0x04BA0000
LIMIT = 0x04BA0000
GROW = 0x04B9C000
TABLE = 0x10423E60
OLD_N = 259
LIS = 0x032F53A4                # lis r25, 0x1042
ADDI = 0x032F53B0               # addi r25, r25, 0x3E5C  (the table - 4: ids are 1-based)
RELOC_DUMMY = 0x037EE73C        # dead word for moved relocations (kind_expand.py, starcopy_cave.py)
# new trail textures, in id order (260, 261, ...): effect/<fighter>/trail/<name>.nut
NEW_TRAILS = ['TexEdgeSwordTrace', 'TexEdgeSwordTraceAdd', 'TexEdgeSwordTrace2', 'TexEdgeSwordTrace2Add']
FIRST_NEW = OLD_N + 1


def trail_id(name):
    return FIRST_NEW + NEW_TRAILS.index(name)


def build(rpx):
    d, _shoff, _ent, secs = rpx_patch.load(rpx)
    cache = {}
    assert rpx_patch.read_u32(d, secs, LIS, cache) == 0x3F201042, hex(rpx_patch.read_u32(d, secs, LIS, cache))
    assert rpx_patch.read_u32(d, secs, ADDI, cache) == 0x3B393E5C, hex(rpx_patch.read_u32(d, secs, ADDI, cache))
    old = [rpx_patch.read_u32(d, secs, TABLE + 4 * i, cache) for i in range(OLD_N)]
    assert all(old) and rpx_patch.read_u32(d, secs, TABLE + 4 * OLD_N, cache) == 0
    table = CAVE
    strings = table + 4 * (OLD_N + len(NEW_TRAILS))
    blob, ptrs = b'', []
    for n in NEW_TRAILS:
        ptrs.append(strings + len(blob))
        blob += n.encode() + b'\0'
    blob += b'\0' * (-len(blob) % 4)
    words = old + ptrs + list(struct.unpack('>%dI' % (len(blob) // 4), blob))
    assert CAVE + 4 * len(words) <= GROW <= LIMIT
    patches = {CAVE + 4 * i: w for i, w in enumerate(words)}
    base = table - 4
    ha, lo = (base + 0x8000) >> 16, base & 0xFFFF
    patches[LIS] = 0x3F200000 | ha                    # lis r25, ha
    patches[ADDI] = 0x3B390000 | lo                   # addi r25, r25, lo
    return patches


def args(patches):
    return (['grow:0x%08X' % GROW]
            + ['reloc:0x%08X-0x%08X=0x%08X' % (a + 2, a + 4, RELOC_DUMMY) for a in (LIS, ADDI)]
            + ['0x%08X=0x%08X' % kv for kv in sorted(patches.items())])


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(' '.join(args(build(sys.argv[1]))))
    sys.stderr.write('trail table: %d + %d names at 0x%08X (ids %d-%d: %s)\n' % (
        OLD_N, len(NEW_TRAILS), CAVE, FIRST_NEW, FIRST_NEW + len(NEW_TRAILS) - 1, ', '.join(NEW_TRAILS)))


if __name__ == '__main__':
    main()
