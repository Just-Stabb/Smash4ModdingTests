#!/usr/bin/env python3
"""Robin's Thunder orb only on Robin's Thunder: prints rpx_patch.py args.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx ... $(python3 tools/thunder_orb_cave.py)

(after brave_reflect_cave.py: its cave ends at 0x04B856E8; this one is after its LIMIT.)

Robin's Thunder article (weapon kind 0xB6) plays its orb natively: 0x031DBDF4 (its only caller
0x031DC0FC, which keeps the weapon in r30) loads the effect id from the table at 0x101807D0,
{0x032C0001, 0x032C0002, 0x032C0003} by the charge level (r26), at 0x031DC020 (lwzx r4, r10, r0),
and plays it (EffectModule vt +0x64). The id names Robin's own bank (0x300 + his kind 0x2C), which
base_effects_cave.py loads for Hero too, so Hero's articles (copies of the Thunder: kinds 0x190 -
0x197, tools/extra_kinds.json) carried Robin's purple-blue orb on Frizz's fireball, every level (the
Frizz tests; emptying Hero's own bank's entries 1 - 3 changed nothing). The table read branches here:
the caller's r30 (its r4: the Thunder's object, whose +0x28 is the module accessor, +0x28 of that
WorkModule read with the 0x0200000x weapon params) is saved by 0x031DBDF4's stmw r24, 0x20(r1) at
0x38(r1); the kind is [[accessor] + 4], as 0x02BEF604 reads it (accessor +0 the BattleObject: +0 id,
+4 kind). Any kind but the Thunder's gets id 0, as the code itself plays for levels over 2 (li r4, 0).
CAVE is in kind_expand.py's old space (0x04B85000 - 0x04B88000, unused since it moved; an rpx built
over an older one still holds its stale tables there).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

HOOK = 0x031DC020               # lwzx r4, r10, r0: the orb's effect id by level
HOOK_WORD = 0x7C8A002E
CAVE = 0x04B85780               # brave_reflect_cave.py's LIMIT
LIMIT = 0x04B85800
THUNDER = 0xB6                  # Robin's Thunder weapon kind
SAVED_R30 = 0x38                # 0x031DBDF4's frame: stmw r24, 0x20(r1) -> r30 at 0x20 + 6 * 4


def build():
    a = Asm(CAVE)
    a.asm("""
        lwzx r4, r10, r0            # the replaced instruction
        lwz r11, %(saved)d(r1)      # the Thunder's object
        lwz r11, 0x28(r11)          # its module accessor
        lwz r11, 0(r11)             # the BattleObject
        lwz r11, 4(r11)             # its kind
        cmplwi r11, %(thunder)d
        beq ok
        li r4, 0                    # not Robin's Thunder: no orb
ok:     b 0x%(back)08X
""" % dict(saved=SAVED_R30, thunder=THUNDER, back=HOOK + 4))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, 'cave too long'
    return words


def main():
    words = build()
    out = ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out.append('0x%08X=0x%08X' % (HOOK, (18 << 26) | ((CAVE - HOOK) & 0x3FFFFFC)))
    print(' '.join(out))
    sys.stderr.write('thunder orb: %d words\n' % len(words))


if __name__ == '__main__':
    main()
