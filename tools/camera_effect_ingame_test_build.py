#!/usr/bin/env python3
"""TEST_ONLY scripts for Effect_Camera (camera_effects v1): Dr. Mario's up taunt (AppealHiR / AppealHiL) given camera
effects and a stage freeze, on the user's own Dr. Mario scripts (every other script kept as it is):

  python3 tools/camera_effect_ingame_test_build.py MARIOD_BODY_DIR OUT_DIR

MARIOD_BODY_DIR: fighter/mariod/script/animcmd/body (game.bin, effect.bin). OUT_DIR gets game.bin and effect.bin.
Vanilla Dr. Mario has no up-taunt game script and no AppealHiR effect script (its AppealHiL jumps to it): both are
added (new hashes bind like any other, docs/native-notes.md "Script binding on a motion change").

  game    frame 2: Stage_Freeze(On=1, Frames=120)
  effect  frame 2: Effect_Camera 0x10000E2 (the common Timer swirl: its alpha-blended flare / swirl, looping, following)
                   Mode 1 over the screen's centre, black at 85 % (a darkening swirl), Frames 120, unslowed;
                   Effect_Camera 0x1000042 (common white stars) Mode 1 pinned at the top-right (X 1.5, Y 0.75), Frames 120;
          frame 20: Effect_Camera 0x100003F (the common ice shock-wave smoke, a one-shot burst) Mode 0, 30 in front.
Both overlays outlast the taunt (a status change doesn't end them) and the freeze's end is the same frame as theirs.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd  # noqa: E402

TAUNTS = ('AppealHiR', 'AppealHiL')


def cmd(name, **kw):
    """an ACMD command by its Sm4shCommand name, its parameters by name (acmd_info.json's syntax, all given)"""
    hit = [(k, v) for k, v in acmd.INFO.items() if v['name'] == name]
    assert len(hit) == 1, name
    ident, info = hit[0]
    syn = info['syntax']
    assert sorted(syn) == sorted(kw), (name, syn, sorted(kw))
    return acmd.Command(ident, [kw[s] for s in syn])


def camfx(graphic, x, y, z, size, mode, frames, flags=1):
    return cmd('Effect_Camera', Graphic=graphic, X=x, Y=y, Z=z, XRot=0.0, YRot=0.0, ZRot=0.0, Size=size, Mode=mode,
               Frames=frames, Flags=flags)


def game_script():
    return [cmd('FRAME', Frames=2.0), cmd('Stage_Freeze', On=1, Frames=120), cmd('Script_End')]


def effect_script():
    return [cmd('FRAME', Frames=2.0),
            camfx(0x10000E2, 0.0, 0.0, 20.0, 0.12, 1, 120),
            cmd('LAST_EFFECT_SET_COLOR', Red=0.0, Green=0.0, Blue=0.0),
            cmd('LAST_EFFECT_SET_ALPHA', Alpha=85.0),
            camfx(0x1000042, 1.5, 0.75, 20.0, 0.08, 1, 120),
            cmd('FRAME', Frames=20.0),
            camfx(0x100003F, 0.0, 0.0, 30.0, 1.0, 0, 0),
            cmd('Script_End')]


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for fn, make in (('game.bin', game_script), ('effect.bin', effect_script)):
        f = acmd.ACMDFile.load(os.path.join(src, fn))
        n = len(f.scripts)
        for t in TAUNTS:
            f.scripts[acmd.crc(t)] = make()
        f.save(os.path.join(out, fn))
        back = acmd.ACMDFile.load(os.path.join(out, fn))
        assert len(back.scripts) == len(f.scripts)
        for t in TAUNTS:
            assert [str(c) for c in back.scripts[acmd.crc(t)]] == [str(c) for c in make()]
        print('%s: %d scripts (+%d), %s:' % (fn, len(back.scripts), len(back.scripts) - n, '/'.join(TAUNTS)))
        print(acmd.fmt_script(back.scripts[acmd.crc(TAUNTS[0])]))


if __name__ == '__main__':
    main()
