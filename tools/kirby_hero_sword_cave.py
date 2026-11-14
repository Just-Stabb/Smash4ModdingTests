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
Fix v4 (Hero copy fix v4; the user: the sword STILL doesn't appear): the GEN stub was never reached. The copy model
function generates the hat (article 0x19, 0x02EFE268) first, and on success its own copy of the kind compare
(0x02EFE284 `cmplwi r27, 0x22`, then `bge 0x02EFE6A0` / `b 0x02EFE66C`: the compiler's tail duplication) jumps past
0x02EFE664, which only the hat's failure path (0x02EFE270 `beq`) and the -1 / 4 / 0x13 / 0x15 / 0x28 paths reach. The
Hero copy's hat is made, so for 0x2C the chain went 0x02EFE6A0 -> 0x02EFE7EC: no held article, nothing to show.
GEN2: 0x02EFE284 -> the same stub (cr0 as `cmplwi r27, 0x22` for every other kind; the Hero copy into 0x02EFE748).
Also the held model's two other reads of the held-item table, which still read Robin's (empty) name for a Hero
player's slot: ITEM2 0x030C49D8 `lwzx r7, r11, r24` (the c00 fallback path when model/<name>/cNN is missing) and ITEM3
0x030C4BE8 `lwzx r7, r12, r24` (the item's motion folder, fighter/kirby/motion/<name>: Robin's "" named the motion
root) -> the same name stub (r11 / r12 = r28 << 2 = r21 there, which the stub indexes with).
Space: 0x04BAF620-0x04BAF700, the end of kirby_copy_new_cave.py's space (its code ends at 0x04BAF610 since crash fix v3), in the code
region the standard build already runs (kind_expand.py's; never the grown text region: crash fix v1).
Fix v5 (Hero copy fix v5; the user, with fix v4: the sword still never appears). Two more things kept it from showing,
both in the held article's own native code (fighters/kirby/specials.md "Hero copy fix v5"):
- VIS: the article follows Kirby's visibility. Its VisibilityModule's is_visible (vt +0xA4 = 0x02C77004) is its own
  flag AND, when its LinkModule link 3 has attribute 7, the parent's is_visible (LinkModule vt +0xDC = 0x02C560C8). The
  update 0x02B02534 sets that attribute again every frame (0x02B02824 .. 0x02B02860) for every Kirby motion but the
  Sonic copy's spin ones (0x318-0x31A: SonicSpecialNSpin / Homing / HomingStart, where Kirby is hidden and the sphere
  shows; it clears it there, 0x02B02794). Kirby is invisible for the whole stone (his native stone code 0x02EED1FC:
  VisibilityModule whole 0 at 0x02EED290; the MSC's SpecialLwEnd main shows him again), so the stone show path's own
  flag (v6) was ANDed with Kirby's 0 every frame. The stone show path now goes to STONE_SHOW: the show path's own
  preamble (0x02BF0594 the owner's motion frame, the item's MotionModule vt +0x2F4), then the Sonic branch 0x02B02794
  with r7 = [r30+0x68] (the LinkModule), r10 = its vtable + 0x3C0, which clears link 3's attribute 7 and shows the
  item. The hide path is unchanged: its motion check sets the attribute again (0x02B02824). The stone check now also
  requires the article's copy kind (r31, its int 0x10000007) to be 0x2C: Kirby's int 0x1000008B is a copy int whose
  native users (e.g. 0x02F02208) store other things there, and with the parent's visibility out of the way a 1 there
  would have shown another copy's held model on the stone.
- JOINT: the article's init 0x02B02078 picks the joint and the link's constraint flags by the copy kind (its int
  0x10000007, Kirby's 0x100000A4): the Robin kind 0x2C (dead in vanilla: 0x2C never had a held article) goes to
  0x02B02248, joint 0x19 (Kirby's RHaveN: model.jtb table 0 entry 0x18) and flags 8. The sword model and the sword
  spells' hitboxes are on joint 0x18 (LHaveN), as Marth's sword. 0x02B02184 `beq 0x02B02248` -> `beq 0x02B022EC` (the
  Marth / Lucina / Roy path: joint 0x18, flags 0x108). Only the Hero copy reaches it (GEN: the held article is made
  for kind 0x2C only when granted for a Hero).
Space for STONE_SHOW: CAVE2 0x04BAF200-0x04BAF300 (free: kirby_robin_book_cave.py's space ends at 0x04BAF200,
kirby_copy_new_cave.py's starts at 0x04BAF400).
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
HOOK_GEN2 = 0x02EFE284          # fix v4: cmplwi r27, 0x22 (the hat's success path: bge 0x02EFE6A0 / b 0x02EFE66C)
HOOK_ITEM2 = 0x030C49D8         # fix v4: lwzx r7, r11, r24 (the c00 fallback's name)
HOOK_ITEM3 = 0x030C4BE8         # fix v4: lwzx r7, r12, r24 (the held item's motion folder name)
ORIGINAL = {HOOK_ITEM: 0x7CF8A82E, HOOK_GEN: 0x281B0022, HOOK_GEN2: 0x281B0022, HOOK_ITEM2: 0x7CEBC02E,
            HOOK_ITEM3: 0x7CECC02E}
GEN_ARTICLE = 0x02EFE748        # lwz r3, 0x7284(r24); li r5, 0; li r4, 0x1A; ... bl 0x02C03EA0 (generate)
HELD_BACK = 0x02B02734          # after the hide path's lwz r3, 0xA8(r30)
SWORD_INT = 0x1000008B          # Kirby: 1 while a sword spell is cast (kirby.c khm_sw_*; copy_grant clears it)
STONE = (0x155, 0x175, 0x176)
BRAVE = 0x45
ROBIN = 0x2C
ITEM_NAME = 'bravesword'
# fix v5
CAVE2 = 0x04BAF200
LIMIT2 = 0x04BAF300
HOOK_JOINT = 0x02B02184         # the held article's init: beq 0x02B02248 (kind 0x2C: joint 0x19, link flags 8)
JOINT_ORIGINAL = 0x418200C4
MARTH_LINK = 0x02B022EC         # lwz r4, 0x20(r30); li r6, 0; mr r3, r29; li r5, 0x18; bl 0x02B61FB8; flags r28 (0x108)
SHOW_SYNC = 0x02BF0594          # the show path's first call (0x02B026B8): the owner's motion frame (r3 = the handle)
SONIC_SHOW = 0x02B02794         # the show path's Sonic-spin branch: link 3 attribute 7 cleared, the item shown
ORIGINAL[HOOK_JOINT] = JOINT_ORIGINAL


def source(lab44, stone_show):
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
    # fix v5: the Hero copy's article only (r31 = its copy kind, int 0x10000007)
    src += ['held_stone:', 'cmplwi r31, 0x%X' % ROBIN, 'bne hs_hide',
            'lwz r3, 0x20(r27)', 'lwz r12, 0(r3)', 'lwz r12, 0x8C(r12)', 'mtctr r12', 'bctrl']
    for i, st in enumerate(STONE):
        src += ['cmplwi r3, 0x%X' % st, 'beq hs_chk']
    src += ['b hs_hide', 'hs_chk:', 'lwz r3, 0x28(r27)', 'lwz r12, 0(r3)', 'lwz r12, 0x84(r12)',
            'lis r4, 0x%04X' % (SWORD_INT >> 16), 'ori r4, r4, 0x%04X' % (SWORD_INT & 0xFFFF), 'mtctr r12', 'bctrl',
            'cmpwi r3, 1', 'bne hs_hide',
            # fix v5 (v6-v4 went to the show path 0x02B026B4, whose motion check set link 3's attribute 7 again: the
            # item then hidden with Kirby)
            'b 0x%08X' % stone_show,
            'hs_hide:', 'lwz r3, 0xA8(r30)',
            'lis r12, 0x%04X' % (HELD_BACK >> 16), 'ori r12, r12, 0x%04X' % (HELD_BACK & 0xFFFF), 'mtctr r12', 'bctr']
    return '\n'.join(src)


def source2():
    """fix v5: the stone's show path. In 0x02B02534's frame (reached by branches: its LR is saved there), r27 Kirby's
    module accessor, r30 the item's, r31 its copy kind, r1 + 0x68 the owner's handle"""
    return '\n'.join([
        'stone_show:',
        'addi r3, r1, 0x68',                                    # as 0x02B026B4: the owner's motion frame (f1) ...
        'lis r12, 0x%04X' % (SHOW_SYNC >> 16), 'ori r12, r12, 0x%04X' % (SHOW_SYNC & 0xFFFF), 'mtctr r12', 'bctrl',
        'lwz r3, 0x44(r30)', 'lwz r6, 0(r3)', 'lwz r7, 0x2F4(r6)', 'mtctr r7', 'bctrl',    # ... set on the item
        'lwz r7, 0x68(r30)', 'lwz r10, 0(r7)', 'addi r10, r10, 0x3C0',                     # the LinkModule (0x02B02718)
        'lis r12, 0x%04X' % (SONIC_SHOW >> 16), 'ori r12, r12, 0x%04X' % (SONIC_SHOW & 0xFFFF), 'mtctr r12', 'bctr',
    ])


def build():
    a44, _res = V44.args()
    a2 = Asm(CAVE2)
    a2.asm(source2())
    words2 = a2.words()
    assert CAVE2 + 4 * len(words2) <= LIMIT2, 'kirby hero sword cave 2 too big: %d words' % len(words2)
    a = Asm(CAVE)
    a.asm(source(a44.labels, a2.labels['stone_show']))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, 'kirby hero sword cave too big: %d words' % len(words)
    assert a44.pc <= CAVE, 'kirby_copy_new_cave.py reaches 0x%08X' % a44.pc
    a.labels.update(a2.labels)
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    out.update({x: 0 for x in range(a.pc, LIMIT, 4)})                  # fix v5: v6's longer show branch's tail
    out.update({CAVE2 + 4 * i: w for i, w in enumerate(words2)})
    out[HOOK_JOINT] = bc_to(HOOK_JOINT, MARTH_LINK)                   # fix v5
    out[HOOK_ITEM] = V44.bl(HOOK_ITEM, a.labels['name_item'])
    out[HOOK_GEN] = V44.bl(HOOK_GEN, a.labels['gen_stub'])
    out[HOOK_GEN2] = V44.bl(HOOK_GEN2, a.labels['gen_stub'])          # fix v4
    out[HOOK_ITEM2] = V44.bl(HOOK_ITEM2, a.labels['name_item'])       # fix v4
    out[HOOK_ITEM3] = V44.bl(HOOK_ITEM3, a.labels['name_item'])       # fix v4
    held, hook = HELD.build(HELD.MOTIONS, a.labels['held_stone'])
    for i, w in enumerate(held):
        out[HELD.CAVE + 4 * i] = w
    out[HELD.HOOK] = hook
    return a, out


def bc_to(at, target):
    """the `beq` at `at` (bc 12, 2) re-aimed at target"""
    off = target - at
    assert -0x8000 <= off < 0x8000 and not off & 3
    return 0x41820000 | (off & 0xFFFC)


def main():
    a, out = build()
    print(' '.join('0x%08X=0x%08X' % kv for kv in sorted(out.items())))
    print('kirby hero sword cave: 0x%08X-0x%08X (%d words)' % (CAVE, a.pc, (a.pc - CAVE) // 4), file=sys.stderr)


if __name__ == '__main__':
    main()
