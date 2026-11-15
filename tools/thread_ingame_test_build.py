#!/usr/bin/env python3
"""In-game test of ACMD threads on a fighter (exe_v46m, docs/acmd-extra-commands.md "Thread_Start"): adds an up-taunt
game script (AppealHiR / AppealHiL, which vanilla Mario's game.bin, and so Supamario's, leaves empty) that starts a
thread. Run with the threads diag executable (tools/diag_threads_cave.py + tools/diag_godfist_cave.py) for the log;
with the plain exe_v46m the stars (6, every 10 frames, the last ones after the taunt) still show that the thread runs.

  python3 tools/thread_ingame_test_build.py IN_GAME.bin OUT_GAME.bin

The script (both taunts; printed by this tool, as Sm4shCommand shows it):

    SET_FLOAT(Value=1, Variable=0x0F0003F7)         // log k=7: the taunt started the thread (S4GF line)
    Thread_Start(ID=0x7E, Flags=0){                 // runs on its own from the next frame
        SET_FLOAT(Value=1, Variable=0x0F0003F8)     // log k=8 on each of its 60 frames
        Graphic_Effect(0x100000F, Bone=0, Y=18, Size=0.6)   // on frames 1, 11, 21, ...: a star over his head
        WAIT(Frames=1)
        ... (60 frames, written out: no loop)
        SET_FLOAT(Value=60, Variable=0x0F0003F9)    // log k=9 v=60: its last frame
    }

The writes to 0x0F0003F0 + k only print with the diag executable; elsewhere they do nothing (acmd_ext_cave.py: IDs
0x3C9-0x3FF read 0, writes ignored). The thread outlives the taunt (40 frames): its last stars come after it.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd  # noqa: E402

DIAG = 0x0F0003F0
TID = 0x7E
FRAMES = 60
STAR = 0x100000F                # common "Large star" (Tooltips gfx.txt)
TAUNTS = ('appealhir', 'appealhil')


def cmd(name, *params):
    return acmd.Command(acmd.BY_NAME[name.lower()], list(params))


def size(cmds):
    return sum(acmd.INFO[c.ident]['size'] for c in cmds)


def star():
    return cmd('graphic_effect', STAR, 0, 0.0, 18.0, 0.0, 0.0, 0.0, 0.0, 0.6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)


def test_script():
    body = []
    for k in range(FRAMES // 10):
        frame10 = [cmd('set_float', 1.0, DIAG + 8)]
        frame10 += [star()]
        frame10 += [cmd('wait', 1.0)]
        rest = [cmd('set_float', 1.0, DIAG + 8), cmd('wait', 1.0)]
        body += frame10 + rest * 9
    body += [cmd('set_float', float(FRAMES), DIAG + 9)]
    block = [cmd('thread_start', 4 + size(body) + 1, TID, 0)] + body + [acmd.Command(acmd.END)]
    return [cmd('set_float', 1.0, DIAG + 7)] + block + [acmd.Command(acmd.END)]


def main():
    a = sys.argv[1:]
    if len(a) != 2:
        sys.exit(__doc__)
    f = acmd.ACMDFile.load(a[0])
    for n in TAUNTS:
        assert f.script(n) is None, '%s already has a game script: refusing to replace it' % n
        f.scripts[acmd.crc(n)] = test_script()
    f.save(a[1])
    g = acmd.ACMDFile.load(a[1])
    for n in TAUNTS:
        assert [c.encode() for c in g.script(n)] == [c.encode() for c in test_script()], n
    print('wrote %s: %s (%d commands each)' % (a[1], ', '.join(TAUNTS), len(test_script())))
    print(acmd.fmt_script(test_script())[:1500])


if __name__ == '__main__':
    main()
