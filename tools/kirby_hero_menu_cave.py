#!/usr/bin/env python3
"""Kirby's Hero copy, stage 2 (Stone = Hero's Command Selection): the damage panel draws Hero's menu window and MP
gauge for Kirby too, and the Robin copy (the Hero copy's granted kind) gets Hero's spell articles. Prints rpx_patch.py
arguments for exe_v45 = exe_v44 + this:

  python3 tools/rpx_patch.py EXE_V44.rpx EXE_V45.rpx $(python3 tools/kirby_hero_menu_cave.py)
  python3 tools/kirby_hero_menu_test.py EXE_V45.rpx EXE_V44.rpx

fighters/kirby/specials.md "Hero copy: Stone = Command Selection".
1. The panel (tools/trait_badge_cave.py build_menu, at 0x04B85000): it finds each panel's fighter object and draws
   the window / gauge from the ints 0x1000009C (gauge), 0x1000009E (window), 0x1000009F (rows) when the object's kind
   is Hero's (0x45). Kirby's own 0x9C-0x9F are taken (star copy, copy custom slot), so Kirby's MSC writes the same
   values to 0x1000008A (gauge), 0x1000008C (window), 0x1000008D (rows): the same spacing, 0x12 ints lower (in
   Kirby's copy range: copy_grant clears them; only the Palutena copy reads 0x8D, as a count, never with these
   values' magic bytes). Hooks: the kind compare (0x04B850C0 `cmpwi r0, 0x45`, then `bne`) -> a stub that keeps the
   kind and leaves cr0 "equal" for 0x45 or 8; the int array load (0x04B85138 `lwz r11, 0xC(r11)`) -> a stub that
   loads it and, for Kirby, takes 0x48 off (the cave reads +0x270 / +0x278 / +0x27C from it). The values carry their
   magic bytes (0x4D50 / 0x4845 / 0x48), so a Kirby without the Hero copy (they're 0) draws nothing.
2. Robin's copy record list (v44's, in kirby_copy_new_cave.py's cave) copied again with Hero's spell weapons after
   the fireball / fire: copy articles 8 flash (Sizz / Sizzle, weapon 0x193), 9 explosion (Bang / Kaboom, 0x194),
   10 deathball (Whack / Thwack, 0x195), 11 sleep (Snooze, 0x197), 12 crash (Magic Burst, 0x196); all copies of
   Robin's thunder with its spawner 0x02F643A4 (extra_kinds.json brave "weapons"), Hero's max counts. Kirby's
   reserve article entries 10-14 name them (their files load with Kirby's).
Space: after kirby_copy_new_cave.py's code (its cave ends at 0x04BD4218), below its LIMIT.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402
import kirby_copy_new_cave as V44  # noqa: E402

CAVE = 0x04BD4400
LIMIT = V44.LIMIT
HOOK_KIND = 0x04B850C0          # cmpwi r0, 0x45 (then bne rows)
HOOK_INTS = 0x04B85138          # lwz r11, 0xC(r11) (the WorkModule's int array)
KIRBY = 8
BRAVE = 0x45
SHIFT = (0x9C - 0x8A) * 4       # Kirby's gauge int 0x8A for Hero's 0x9C
KIRBY_INTS = (0x1000008A, 0x1000008C, 0x1000008D)   # gauge, window, rows
SPELL_RECORDS = ((0x193, 2, 0x02F643A4, 0), (0x194, 2, 0x02F643A4, 0), (0x195, 2, 0x02F643A4, 0),
                 (0x197, 2, 0x02F643A4, 0), (0x196, 1, 0x02F643A4, 0))
SPELL_ARTICLES = {'flash': 8, 'explosion': 9, 'deathball': 10, 'sleep': 11, 'crash': 12}
RESERVE = ((14, 0x193), (13, 0x194), (12, 0x195), (11, 0x197), (10, 0x196))


def records():
    return list(V44.ROBIN_RECORDS) + list(V44.NEW_RECORDS) + list(SPELL_RECORDS)


def build():
    src = ['panel_kind:', '.word 0', 'robin_list2:'] + ['.word 0x%08X' % w for r in records() for w in r]
    src += ['kind_stub:', 'lis r12, panel_kind@ha', 'stw r0, panel_kind@l(r12)',
            'cmpwi r0, %d' % BRAVE, 'beq ks_out', 'cmpwi r0, %d' % KIRBY, 'ks_out:', 'blr']
    src += ['ints_stub:', 'lwz r11, 0xC(r11)', 'lis r12, panel_kind@ha', 'lwz r12, panel_kind@l(r12)',
            'cmpwi r12, %d' % KIRBY, 'bne is_out', 'addi r11, r11, -%d' % SHIFT, 'is_out:', 'blr']
    a = Asm(CAVE)
    a.asm('\n'.join(src))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    out[HOOK_KIND] = V44.bl(HOOK_KIND, a.labels['kind_stub'])
    out[HOOK_INTS] = V44.bl(HOOK_INTS, a.labels['ints_stub'])
    out[V44.ROBIN_HDR] = a.labels['robin_list2']
    out[V44.ROBIN_HDR + 4] = len(records())
    for i, k in RESERVE:
        out[V44.KIRBY_RESERVE + 0x10 * i] = k
    return a, out


def main():
    a, out = build()
    print(' '.join('0x%08X=0x%08X' % kv for kv in sorted(out.items())))
    print('kirby hero menu cave: 0x%08X-0x%08X; Robin copy list 0x%08X (%d records)' % (
        CAVE, a.pc, a.labels['robin_list2'], len(records())), file=sys.stderr)


if __name__ == '__main__':
    main()
