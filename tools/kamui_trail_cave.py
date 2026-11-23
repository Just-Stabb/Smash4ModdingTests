#!/usr/bin/env python3
"""Corrin's (kamui) extra sword trail textures: trail texture ids past tools/trail_table_cave.py's (272 on). Prints
rpx_patch.py arguments, as trail_table_cave.py does.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/kamui_trail_cave.py IN.rpx)
  python3 tools/kamui_trail_cave.py --ids           the new names and their ids

How a trail texture is found (docs/native-notes.md "Sword trails", docs/acmd-params/effects.md "Trails"): a Sword_Glow /
AFTER_IMAGE* texture id N is entry N - 1 of the trail-name table; the trail set-up (0x032F515C, from the trail creator
0x032F9128 / 0x032F5158) formats "%s.nut" from that name and looks the texture up by name among the loaded trail
textures, which are every .nut in each loaded fighter's effect/<fighter>/trail/ folder. The game's table (0x10423E60)
has 259 names and can't grow in place; trail_table_cave.py copies it into the grown code space (0x04B9B000, the
pointers then the strings, below 0x04B9C000) and adds its NEW_TRAILS (ids 260 - 271: Sephiroth, Hero, Byleth).

This adds KAMUI_TRAILS after them: it is trail_table_cave.py's build with NEW_TRAILS + KAMUI_TRAILS (the table re-laid
out over the copy, which that build re-applies over an executable that has it). Names already in NEW_TRAILS are not
added twice, so folding KAMUI_TRAILS into trail_table_cave.NEW_TRAILS later changes nothing (same ids, same bytes).
Only words in [0x04B9B000, 0x04B9C000) and the two instructions trail_table_cave.py writes change.

In the release chain: tools/gekkouga_clone_cave.py's feature ktrail (RELEASE from exe_v46z_gkb21) adds these words
(the ones that differ from its base) to its own, so `rpx_patch.py exe_v46z_ui10.rpx OUT $(gekkouga_clone_cave.py
--rpx exe_v46z_ui10.rpx)` gives the release with them; over that release this script changes nothing.

The textures: fighter/kamui/effect/kamui/trail/<name>.nut (NTP3, 128 x 128, one mip, texture id 0, as her vanilla
TexKamuiSwordTrace / Add), made by tools/kamui_trail_build.py. Test: tools/kamui_trail_cave_test.py.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trail_table_cave as T  # noqa: E402

# new trail textures, in id order after trail_table_cave.NEW_TRAILS (272, 273, ...): effect/kamui/trail/<name>.nut
KAMUI_TRAILS = [
    # cyan v1: the user's cyan / light-blue trail (kamui_in/trail1/preview.png) and its glow (Texture1 / Texture2)
    'TexKamuiSwordTraceCyan', 'TexKamuiSwordTraceCyanAdd',
]


def names():
    """every new name after the game's 259, in id order"""
    return T.NEW_TRAILS + [n for n in KAMUI_TRAILS if n not in T.NEW_TRAILS]


def trail_id(name):
    return T.FIRST_NEW + names().index(name)


def build(rpx):
    """{address: word}: trail_table_cave.py's table with names() (its NEW_TRAILS + KAMUI_TRAILS)"""
    saved = T.NEW_TRAILS
    T.NEW_TRAILS = names()
    try:
        return T.build(rpx)
    finally:
        T.NEW_TRAILS = saved


def args(patches):
    return T.args(patches)


def main():
    if sys.argv[1:] == ['--ids']:
        for n in KAMUI_TRAILS:
            print(trail_id(n), n)
        return
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(' '.join(args(build(sys.argv[1]))))
    sys.stderr.write('trail table: %d + %d names (Corrin: %s)\n' % (
        T.OLD_N, len(names()), ', '.join('%d %s' % (trail_id(n), n) for n in KAMUI_TRAILS)))


if __name__ == '__main__':
    main()
