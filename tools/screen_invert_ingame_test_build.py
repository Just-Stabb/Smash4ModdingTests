#!/usr/bin/env python3
"""TEST_ONLY game script for Screen_Invert (screen_invert v1, exe_v46z_inv), built on the user's own Dr. Mario (every
other script kept as it is):

  python3 tools/screen_invert_ingame_test_build.py MARIOD_DIR OUT_DIR

MARIOD_DIR: the fighter/mariod folder (script/animcmd/body/{game,effect}.bin). OUT_DIR gets script/animcmd/body/game.bin
(the taunts below) and the user's own effect.bin (camera_effects' test effect.bin, if installed, goes back to his).

  AppealHiR / AppealHiL (up, both directions): a full negative at once for 120 frames (2 s), off at once
  AppealSR (side; AppealSL jumps to it): Strength 0.5, FadeIn 20, held 60, FadeOut 20, from frame 0: the 3D picture
             greys out (half a negative is an even grey) and comes back; his own side-taunt lines (the cape article) kept
  AppealLwR (down, facing right): Stage_Freeze(1, 120) and a full negative for the same 120 frames
  AppealLwL (down, facing left): Stage_Freeze(1, 120) with XV2's time-stop look (negative, grey, x 0.8, + (19, 37, 60))
             for 90 frames, then XV2's white negative (Saturation 0.15, Brightness 0.6, + (102, 104, 110)) replacing it,
             held 30 frames and faded out over 20
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd  # noqa: E402


def cmd(name, **kw):
    """an ACMD command by its Sm4shCommand name, its parameters by name (acmd_info.json's syntax, all given)"""
    hit = [(k, v) for k, v in acmd.INFO.items() if v['name'] == name]
    assert len(hit) == 1, name
    ident, info = hit[0]
    syn = info['syntax']
    assert sorted(syn) == sorted(kw), (name, syn, sorted(kw))
    return acmd.Command(ident, [kw[s] for s in syn])


def inv(mode, strength=1.0, frames=0, fin=0, fout=0, sat=1.0, bri=1.0, rgb=(0.0, 0.0, 0.0)):
    return cmd('Screen_Invert', Mode=mode, Strength=strength, Frames=frames, FadeIn=fin, FadeOut=fout, Saturation=sat,
               Brightness=bri, Red=rgb[0], Green=rgb[1], Blue=rgb[2])


XV2_STOP = dict(strength=1.0, sat=0.0, bri=0.8, rgb=(19.0, 37.0, 60.0))
XV2_WHITE = dict(strength=1.0, sat=0.15, bri=0.6, rgb=(102.0, 104.0, 110.0))


def scripts(old):
    """the taunts (old: the user's game.bin scripts by name, for the side taunt's own lines)"""
    wait = cmd('FRAME', Frames=2.0)
    end = cmd('Script_End')
    up = [wait, inv(1, 1.0, 120, 0, 0), end]
    side = [inv(1, 0.5, 60, 20, 20)] + list(old['AppealSR'])     # his own lines' timing kept (frame 0 on)
    down_r = [wait, cmd('Stage_Freeze', On=1, Frames=120), inv(1, 1.0, 120, 0, 0), end]
    down_l = [wait, cmd('Stage_Freeze', On=1, Frames=120), inv(1, frames=0, **XV2_STOP),
              cmd('FRAME', Frames=92.0), inv(1, frames=30, fout=20, **XV2_WHITE), end]
    return {'AppealHiR': up, 'AppealHiL': up, 'AppealSR': side, 'AppealLwR': down_r, 'AppealLwL': down_l}


def main():
    mdir, out = sys.argv[1:3]
    body = os.path.join(mdir, 'script/animcmd/body')
    f = acmd.ACMDFile.load(os.path.join(body, 'game.bin'))
    old = {n: f.scripts[acmd.crc(n)] for n in ('AppealSR',)}
    add = scripts(old)
    n = len(f.scripts)
    for name, sc in add.items():
        f.scripts[acmd.crc(name)] = sc
    od = os.path.join(out, 'script/animcmd/body')
    os.makedirs(od, exist_ok=True)
    f.save(os.path.join(od, 'game.bin'))
    shutil.copyfile(os.path.join(body, 'effect.bin'), os.path.join(od, 'effect.bin'))
    b = acmd.ACMDFile.load(os.path.join(od, 'game.bin'))
    for name, sc in add.items():
        assert [str(c) for c in b.scripts[acmd.crc(name)]] == [str(c) for c in sc]
    orig = acmd.ACMDFile.load(os.path.join(body, 'game.bin'))
    for k, sc in orig.scripts.items():         # every other script as it was
        if k not in [acmd.crc(x) for x in add]:
            assert [str(c) for c in b.scripts[k]] == [str(c) for c in sc]
    print('game.bin: %d scripts (+%d new), set: %s; effect.bin: the user\'s own' % (len(b.scripts),
                                                                                   len(b.scripts) - n, ', '.join(add)))
    for name in sorted(add):
        print('  %s:\n%s' % (name, acmd.fmt_script(b.scripts[acmd.crc(name)], '    ')))


if __name__ == '__main__':
    main()
