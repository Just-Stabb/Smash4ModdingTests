#!/usr/bin/env python3
"""Kirby's Hero / Sephiroth copies (granted as the Robin copy): Robin's native "hold this tome" code left out, so it no
longer zeroes Kirby's ints 0x1000009F (the copy's custom slot: the spell's level) and 0x100000A0 (the Hero / Sephiroth
marker). Prints rpx_patch.py arguments (exe_v45h = exe_v45g + this, exe_v46f = exe_v46e + this):

  python3 tools/rpx_patch.py EXE_V45G.rpx EXE_V45H.rpx $(python3 tools/kirby_robin_book_cave.py)
  python3 tools/kirby_robin_book_test.py EXE_V45H.rpx EXE_V45G.rpx

fighters/kirby/specials.md "Hero copy fix v2". Traced (exe_v45g / exe_v46e, the same words in the base game):
- Robin's thunder spawner 0x02F643A4 (the Hero copy's fireball, article 6, and the Stone's spells, articles 8-12: the
  records' spawner, kirby_copy_new_cave.py / kirby_hero_menu_cave.py) calls 0x02F613B8(owner, 0) at 0x02F645BC, before
  its custom-number read at 0x02F64650 (copy_custom_cave.py's hook: Kirby with a copy reads his 0x1000009F there).
- 0x02F613B8(F, book): Robin's tome in hand: VisibilityModule (F+0x72B0) group 1, the module at F+0x727C op 7 with the
  book as a float, and the owner's ints 0x9F, 0xA0, 0xA1 (`stw r29, 0x27C / 0x280 / 0x284` at 0x02F61458-0x02F61460)
  and 0x90 (+0x240) = book, a flag cleared. Robin's ints; on Kirby with the Robin copy the same offsets are this mod's
  copy custom slot (0x9F) and copy marker (0xA0).
So every fireball / spell Kirby's Hero copy made zeroed 0x9F just before the spawner read it (the level always 0: Frizz
for Frizzle / Kafrizz, Whack for Thwack, Sizz for Sizzle, Bang for Kaboom: the user's fix v1 report) and zeroed the
marker 0xA0 (the Hero copy then counted as Robin's copy from the first Frizz on: crash fix v5's "only Frizz, the other
levels lock Kirby out" and fix v1's "marker lost", which fix v1's guess only papered over in a match with no Robin).
Sephiroth's fire uses Din's Fire's spawner (no call), so his marker and levels survived.

The patch: 0x02F613B8's first word (`mflr r0`, no relocation) -> `b book_stub`: a Kirby (the fighter kind at
[[F+0x726C]+0x18] = 8) whose marker int 0x100000A0 is 2 (Hero) or 3 (Sephiroth) returns at once (no tome on those
copies); anything else replays `mflr r0` and goes on at 0x02F613BC. Registers: r11 / r12 / cr0 (volatile at a call).
Space: 0x04BAF100-0x04BAF200, free (zero) code in kind_expand.py's region after extended_memory.py's 0x04BAF000-0x04BAF100
and before kirby_copy_new_cave.py's 0x04BAF400: the code region the standard build already runs (never the grown text
region: crash fix v1).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

CAVE = 0x04BAF100
LIMIT = 0x04BAF200
HOOK = 0x02F613B8               # Robin: hold tome `book` (r3 the fighter F, r4 book or -1); its first word mflr r0
HOOK_WORD = 0x7C0802A6
BACK = HOOK + 4
KIRBY = 8
MARKER = 0x100000A0             # kirby_copy_new_cave.py: 1 Supamario, 2 Hero, 3 Sephiroth
COPY_SLOT = 0x1000009F          # copy_custom_cave.py
THUNDER_SPAWNER = 0x02F643A4
SPAWNER_CALL = 0x02F645BC       # bl 0x02F613B8 (r3 = the owner, r4 = 0)
CUSTOM_READ = 0x02F64650        # copy_custom_cave.py's hook: the custom number (Kirby with a copy: 0x9F)
STORES = (0x02F61458, 0x02F6145C, 0x02F61460)   # stw r29, 0x27C / 0x280 / 0x284 (r10): ints 0x9F / 0xA0 / 0xA1

SOURCE = """
book_stub:                              # r3 = F (WorkModule at +0x726C), r4 = the book
        lwz r12, 0x726C(r3)
        lwz r11, 0x18(r12)              # the fighter kind
        cmpwi r11, %(kirby)d
        bne go
        lwz r12, 8(r12)                 # category table
        lwz r12, 0(r12)                 # category 0 (instance ints)
        lwz r12, 0xC(r12)               # ints
        lwz r11, %(marker)d(r12)        # int 0x100000A0
        cmpwi r11, 2
        blt go
        cmpwi r11, 3
        bgt go
        blr                             # Kirby's Hero / Sephiroth copy: no tome
go:
        mflr r0                         # the hooked word
        b 0x%(back)08X
""" % dict(kirby=KIRBY, marker=(MARKER & 0xFFFF) * 4, back=BACK)


def assemble():
    a = Asm(CAVE)
    a.asm(SOURCE)
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, 'robin book cave too big'
    return a, words


def args():
    a, words = assemble()
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    out[HOOK] = (18 << 26) | ((a.labels['book_stub'] - HOOK) & 0x03FFFFFC)
    return ['0x%08X=0x%08X' % (k, v) for k, v in sorted(out.items())]


def main():
    print(' '.join(args()))
    a, words = assemble()
    print('kirby robin book cave: 0x%08X-0x%08X (%d words)' % (CAVE, CAVE + 4 * len(words), len(words)),
          file=sys.stderr)


if __name__ == '__main__':
    main()
