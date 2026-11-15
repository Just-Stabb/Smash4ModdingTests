#!/usr/bin/env python3
"""In-game test of Time_Scale / Target_Time_Scale / Stage_Freeze (exe_v46n, docs/acmd-extra-commands.md "Time and the
stage"): adds Supamario taunt game scripts (vanilla Mario's game.bin, and so Supamario's, has none):

  up taunt    Time_Scale(Rate=2, Frames=120)                  everything twice as fast for 2 seconds
  side taunt  Time_Scale(Rate=0.5, Frames=120)                everything at half speed for 2 seconds
  down taunt  Stage_Freeze(On=1, Frames=180)                  the stage stands still for 3 seconds, and
              Target_Time_Scale(Target=1, Rate=0.5, Frames=180)   the nearest opponent at half speed for 3 seconds

  python3 tools/time_stage_ingame_test_build.py IN_GAME.bin OUT_GAME.bin

Each runs on the taunt's first frame (the right and left versions alike). Refuses to replace a taunt script the file
already has.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd  # noqa: E402

UP = ('appealhir', 'appealhil')
SIDE = ('appealsr', 'appealsl')
DOWN = ('appeallwr', 'appeallwl')


def cmd(name, *params):
    return acmd.Command(acmd.BY_NAME[name.lower()], list(params))


def scripts():
    end = acmd.Command(acmd.END)
    return {
        UP: [cmd('time_scale', 2.0, 120), end],
        SIDE: [cmd('time_scale', 0.5, 120), end],
        DOWN: [cmd('stage_freeze', 1, 180), cmd('target_time_scale', 1, 0.5, 180), end],
    }


def main():
    a = sys.argv[1:]
    if len(a) != 2:
        sys.exit(__doc__)
    f = acmd.ACMDFile.load(a[0])
    for names, body in scripts().items():
        for n in names:
            assert f.script(n) is None, '%s already has a game script: refusing to replace it' % n
            f.scripts[acmd.crc(n)] = body
    f.save(a[1])
    g = acmd.ACMDFile.load(a[1])
    for names, body in scripts().items():
        for n in names:
            assert [c.encode() for c in g.script(n)] == [c.encode() for c in body], n
        print('%s: %s' % ('/'.join(names), '; '.join(str(c) for c in body[:-1])))
    # the parameter words as the game reads them (Rate a float)
    w = scripts()[UP][0].encode()
    assert struct.unpack('>f', w[4:8])[0] == 2.0 and struct.unpack('>I', w[8:12])[0] == 120
    print('wrote', a[1])


if __name__ == '__main__':
    main()
