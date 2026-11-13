#!/usr/bin/env python3
"""Kirby's Hero copy, v6: Hero's sword as the copy's held model, shown on the stone while a sword spell is cast.
Prints rpx_patch.py arguments for exe_v46 = exe_v45c (crash fix v2) + this:

  python3 tools/rpx_patch.py EXE_V45C.rpx EXE_V46.rpx $(python3 tools/kirby_hero_sword_cave.py)
  python3 tools/kirby_hero_sword_test.py EXE_V46.rpx EXE_V45C.rpx

fighters/kirby/specials.md "v6". Traced (exe_v45b, the same in v45c):
- Kirby's copy held model (marthsword, ikesword, ...) is his article 26, "simple" (weapon kind 0x11, spawner
  0x02EFC3D0, the same generic spawner as the hat, article 25 / kind 0xC). The copy model function 0x02EFE138 (called
  by copy_grant at 0x02EFD0A0 with the granted kind; with -1 at a copy's loss from 0x02EF5DE4 / 0x02EF6074) generates
  it (ArticleModule generate 0x02C03EA0, r4 = 0x1A, at 0x02EFE748) only for the kinds with a held model (1, 0x12,
  0x13, 0x17, 0x1D, 0x22, 0x25, 0x27, 0x2B, 0x2E, 0x2F, 0x36, 0x37; Bayonetta 0x38: articles 0x20 / 0x21), from the
  compare chain at 0x02EFE664; Robin (0x2C, the Hero copy's granted kind) gets none, and a -1 removes it (0x02C05594).
- Its model is the copied player's slot resource of type 0x11 (the copy-resource loader 0x030C4694 runs per match
  entry for types 0xC, 0x11, 0x164, 0x165 = Kirby's article weapon kinds hat, simple, simple2r / simple2l, 0x030C4D88
  ...), named from the held-item table 0x1041A8A0 (read at 0x030C487C, `lwzx r7, r24, r21`), empty for Robin.
- Its per-frame update 0x02B02534 (r27 = the owner Kirby's module accessor, r30 = the article's own) shows / hides
  it by Kirby's status (tools/copy_held_cave.py).
The patch:
1. ITEM: the held-item name read 0x030C487C -> a stub: "bravesword" for a Hero player's slot (the loader's kept kind,
   kirby_copy_new_cave.py res_kind, 0x45), else the table's own name (model/bravesword/cNN, Kirby's costume NN).
2. GEN: the kind compare 0x02EFE664 (`cmplwi r27, 0x22`) -> a stub: for the Robin kind (0x2C) granted for a Hero
   (kirby_copy_new_cave.py grant_kind 0x45) it returns into 0x02EFE748 (the article 0x1A generate, then the Robin
   path's own code: 0x02EFE7EC on), else does the compare and returns.
3. STONE: copy_held_cave.py --stone: its hide path comes here: in the stone statuses (0x155 / 0x175 / 0x176) with
   Kirby's int 0x1000008B == 1 (kirby.c khm_sw_*: a sword spell being cast) it takes the show path (0x02B026B4), else
   the hook's own `lwz r3, 0xA8(r30)` and back to 0x02B02734 (both through ctr: 0x02Bxxxxx is out of `b` reach).
Space: 0x04BAF620-0x04BAF700, the end of kirby_copy_new_cave.py's space (its code ends at 0x04BAF610 since crash fix v3), in the code
region the standard build already runs (kind_expand.py's; never the grown text region: crash fix v1).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402
import kirby_copy_new_cave as V44  # noqa: E402
import copy_held_cave as HELD  # noqa: E402

CAVE = 0x04BAF620
LIMIT = 0x04BAF700
HOOK_ITEM = 0x030C487C          # lwzx r7, r24, r21 (r24 = 0x1041A8A0, the held-item table)
HOOK_GEN = 0x02EFE664           # cmplwi r27, 0x22
GEN_ARTICLE = 0x02EFE748        # lwz r3, 0x7284(r24); li r5, 0; li r4, 0x1A; ... bl 0x02C03EA0 (generate)
HELD_BACK = 0x02B02734          # after the hide path's lwz r3, 0xA8(r30)
SWORD_INT = 0x1000008B          # Kirby: 1 while a sword spell is cast (kirby.c khm_sw_*; copy_grant clears it)
STONE = (0x155, 0x175, 0x176)
BRAVE = 0x45
ROBIN = 0x2C
ITEM_NAME = 'bravesword'


def source(lab44):
    gk, rk = lab44['grant_kind'], lab44['res_kind']
    src = ['s_item:'] + V44.words_of(ITEM_NAME)
    # 1. the held-item name
    src += ['name_item:', 'lis r12, 0x%04X' % ((rk + 0x8000) >> 16), 'lwz r12, %d(r12)' % (((rk & 0xFFFF) ^ 0x8000) - 0x8000),
            'cmplwi r12, 0x%X' % BRAVE, 'bne ni_own', 'lis r7, s_item@ha', 'addi r7, r7, s_item@l', 'blr',
            'ni_own:', 'lwzx r7, r24, r21', 'blr']
    # 2. the held article for the Hero copy
    src += ['gen_stub:', 'lis r12, 0x%04X' % ((gk + 0x8000) >> 16), 'lwz r12, %d(r12)' % (((gk & 0xFFFF) ^ 0x8000) - 0x8000),
            'cmplwi r12, 0x%X' % BRAVE, 'bne gs_cmp', 'cmplwi r27, 0x%X' % ROBIN, 'bne gs_cmp',
            'lis r12, 0x%04X' % (GEN_ARTICLE >> 16), 'ori r12, r12, 0x%04X' % (GEN_ARTICLE & 0xFFFF), 'mtlr r12', 'blr',
            'gs_cmp:', 'cmplwi r27, 0x22', 'blr']
    # 3. the stone statuses (r27 = Kirby's module accessor, r30 = the held article's)
    src += ['held_stone:', 'lwz r3, 0x20(r27)', 'lwz r12, 0(r3)', 'lwz r12, 0x8C(r12)', 'mtctr r12', 'bctrl']
    for i, st in enumerate(STONE):
        src += ['cmplwi r3, 0x%X' % st, 'beq hs_chk']
    src += ['b hs_hide', 'hs_chk:', 'lwz r3, 0x28(r27)', 'lwz r12, 0(r3)', 'lwz r12, 0x84(r12)',
            'lis r4, 0x%04X' % (SWORD_INT >> 16), 'ori r4, r4, 0x%04X' % (SWORD_INT & 0xFFFF), 'mtctr r12', 'bctrl',
            'cmpwi r3, 1', 'bne hs_hide',
            'lis r12, 0x%04X' % (HELD.SHOW >> 16), 'ori r12, r12, 0x%04X' % (HELD.SHOW & 0xFFFF), 'mtctr r12', 'bctr',
            'hs_hide:', 'lwz r3, 0xA8(r30)',
            'lis r12, 0x%04X' % (HELD_BACK >> 16), 'ori r12, r12, 0x%04X' % (HELD_BACK & 0xFFFF), 'mtctr r12', 'bctr']
    return '\n'.join(src)


def build():
    a44, _res = V44.args()
    a = Asm(CAVE)
    a.asm(source(a44.labels))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, 'kirby hero sword cave too big: %d words' % len(words)
    assert a44.pc <= CAVE, 'kirby_copy_new_cave.py reaches 0x%08X' % a44.pc
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    out[HOOK_ITEM] = V44.bl(HOOK_ITEM, a.labels['name_item'])
    out[HOOK_GEN] = V44.bl(HOOK_GEN, a.labels['gen_stub'])
    held, hook = HELD.build(HELD.MOTIONS, a.labels['held_stone'])
    for i, w in enumerate(held):
        out[HELD.CAVE + 4 * i] = w
    out[HELD.HOOK] = hook
    return a, out


def main():
    a, out = build()
    print(' '.join('0x%08X=0x%08X' % kv for kv in sorted(out.items())))
    print('kirby hero sword cave: 0x%08X-0x%08X (%d words)' % (CAVE, a.pc, (a.pc - CAVE) // 4), file=sys.stderr)


if __name__ == '__main__':
    main()
