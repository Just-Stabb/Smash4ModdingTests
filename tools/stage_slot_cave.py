#!/usr/bin/env python3
"""New stage slots: stage kinds past the game's 128 and stage-select (cosmetic) ids past 0x37.
Prints rpx_patch.py args.

  python3 tools/stage_slot_cave.py [NAME[:COSMETIC] ...]      (default: NewStage01:0x38)

Each stage gets two kinds, 0x80 + 2i (normal, stage/melee/NAME) and 0x81 + 2i (Omega,
stage/end/NAME), and its cosmetic id (the stage select / ui_stage_db.bin index, default 0x38 + i).
tools/add_stage.py makes the matching files (ui_stage_db / ui_sound_db entries, texts, icons, the
stage folders). docs/stage-expansion.md has the research; Manifold (Fitz Null, zlib licence,
https://gitlab.com/fitz.lol/manifold) found several of these addresses first.

What it changes:
- the stage-kind table {name, variant} (0x1011D95C, 128 entries) is copied here with the new ones
  added; its three readers (name 0x02D1FD7C, path 0x02D1FDA0, variant 0x02D1FE10, the only code
  that reads it) point at the copy, the count (0x02D1FE24) and the name reader's bound are the
  new count;
- the match start (0x03014700) turned kinds >= 0x80 into 0 (Battlefield): its bound is the new
  count;
- the cosmetic id -> name table ({id, name}, 79 entries at 0x1033C100, searched linearly by
  0x0293DCE0) is copied with the new names added: the name picks the stage's icons
  (replace/stage/stage_10/stage_10_NAME.nut, ...) and texts (MmelStageN_NAME / MmelStageG_NAME).
The stage factory (0x03163B3C) already builds the generic stage (StageBaseCafe / StageBaseEnd)
for kinds past 0x7F, loading the stage folder's own models, collision (*.lvd) and params.

Space: new code space 0x04B7C000-0x04B7E000 (grow:, after position_vars_cave.py's 0x04B7C000).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpx_patch  # noqa: E402
from ppcasm import Asm, ha  # noqa: E402

RPX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build', 'cave_fix_s4', 'cross_f.rpx')
CAVE = 0x04B7C000
LIMIT = 0x04B7E000
KIND_TABLE, KIND_COUNT = 0x1011D95C, 0x80
COSMETIC_TABLE, COSMETIC_COUNT = 0x1033C100, 0x4F
DEFAULT = ['NewStage01:0x38']


def slo(v):
    """signed low half (for d(rA) and addi after lis @ha)"""
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def stages(args):
    out = []
    for i, a in enumerate(args or DEFAULT):
        name, _, cos = a.partition(':')
        out.append((name, int(cos, 0) if cos else 0x38 + i))
    return out


def build(new, rpx=RPX):
    d, _s, _e, secs = rpx_patch.load(rpx)
    cache = {}
    read = lambda a: rpx_patch.read_u32(d, secs, a, cache)  # noqa: E731
    kinds = [(read(KIND_TABLE + 8 * k), read(KIND_TABLE + 8 * k + 4)) for k in range(KIND_COUNT)]
    cosm = [(read(COSMETIC_TABLE + 8 * k), read(COSMETIC_TABLE + 8 * k + 4)) for k in range(COSMETIC_COUNT)]
    assert kinds[0][1] == 0 and kinds[47][1] == 1, 'unexpected stage-kind table'
    used = {c for c, _ in cosm}
    for name, cos in new:
        assert cos not in used, 'cosmetic id 0x%X is the game\'s' % cos
    count = KIND_COUNT + 2 * len(new)
    kt = CAVE
    ct = kt + 8 * count
    strings = ct + 8 * (COSMETIC_COUNT + len(new))
    blob = bytearray()
    ptr = {}
    for name, _ in new:
        ptr[name] = strings + len(blob)
        blob += name.encode('ascii') + b'\0'
    blob += b'\0' * (-len(blob) % 4)
    words = []
    for p, v in kinds:
        words += [p, v]
    for name, _ in new:
        words += [ptr[name], 0, ptr[name], 1]      # melee, end
    for c, p in cosm:
        words += [c, p]
    for name, cos in new:
        words += [cos, ptr[name]]
    words += list(struct.unpack('>%dI' % (len(blob) // 4), blob))
    assert CAVE + 4 * len(words) <= LIMIT, 'stage slot cave too big'

    def one(addr, text):
        a = Asm(addr)
        a.asm(text)
        return [(addr + 4 * i, w) for i, w in enumerate(a.words())]

    patches = []
    patches += one(0x02D1FE24, 'li r3, %d' % count)
    patches += one(0x02D1FD80, 'cmplwi r3, %d' % count)
    patches += one(0x02D1FD90, 'addis r12, r11, 0x%X' % ha(kt))
    patches += one(0x02D1FD94, 'lwz r0, %d(r12)' % slo(kt))
    patches += one(0x02D1FDA0, 'lis r10, 0x%X' % ha(kt))
    patches += one(0x02D1FDA8, 'addi r10, r10, %d' % slo(kt))
    patches += one(0x02D1FE10, 'lis r12, 0x%X' % ha(kt + 4))
    patches += one(0x02D1FE18, 'addi r12, r12, %d' % slo(kt + 4))
    patches += one(0x03014720, 'cmplwi r31, %d' % count)
    patches += one(0x0293DCE4, 'lis r3, 0x%X' % ha(ct))
    patches += one(0x0293DCE8, 'li r4, %d' % (COSMETIC_COUNT + len(new)))
    patches += one(0x0293DCEC, 'addi r3, r3, %d' % slo(ct))
    return words, patches, count


def main():
    new = stages(sys.argv[1:])
    words, patches, count = build(new)
    out = ['grow:0x%08X' % LIMIT]
    out += ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % (a, w) for a, w in patches]
    print(' '.join(out))
    for i, (name, cos) in enumerate(new):
        print('%s: kinds 0x%X (stage/melee) / 0x%X (stage/end), cosmetic 0x%X' %
              (name, KIND_COUNT + 2 * i, KIND_COUNT + 2 * i + 1, cos), file=sys.stderr)


if __name__ == '__main__':
    main()
