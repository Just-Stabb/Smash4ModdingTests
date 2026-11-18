#!/usr/bin/env python3
"""TEST_ONLY game script for Outline_Shell and Mesh_Visibility v2 (model_commands v2, exe_v46z_outline2), built on the
user's own Dr. Mario (every other script kept as it is):

  python3 tools/outline_shell_ingame_test_build.py MARIOD_DIR OUT_DIR

MARIOD_DIR: the fighter/mariod folder (script/animcmd/body/{game,effect}.bin). OUT_DIR gets script/animcmd/body/game.bin
(the taunts below) and the user's own effect.bin (an earlier test's effect.bin, if installed, goes back to his).

  AppealHiR / AppealHiL (up): a white outline outside his silhouette, 1.5 pixels, added (a glow), grown in over 4
             frames, held 120 frames (2 s), shrinking over 10
  AppealSR (side; AppealSL jumps to it): a red pulsing outline, 3 pixels (a pulse every 20 frames), held 150 frames,
             shrinking over 15; his own side-taunt lines (the cape article) kept
  AppealLwR (down, facing right): the white outline (as up, 90 frames) and Screen_Invert's full negative for 60
             frames from frame 10 (how the band reads on the negative)
  AppealLwL (down, facing left): the same, and Mesh_Visibility v2 on his two two-part meshes (model.nud: the
             stethoscope / head mirror, stethoscope_VIS_O_OBJ, and his hair, MarioD_hair_O_OBJ, two polygons each):
             both hidden whole for the taunt (Persist 0), back after it
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd  # noqa: E402
import mesh_vis_cave as MV  # noqa: E402

TWO_PART = ('stethoscope_VIS_O_OBJ', 'MarioD_hair_O_OBJ')


def cmd(name, **kw):
    """an ACMD command by its Sm4shCommand name, its parameters by name (acmd_info.json's syntax, all given)"""
    hit = [(k, v) for k, v in acmd.INFO.items() if v['name'] == name]
    assert len(hit) == 1, name
    ident, info = hit[0]
    syn = info['syntax']
    assert sorted(syn) == sorted(kw), (name, syn, sorted(kw))
    return acmd.Command(ident, [kw[s] for s in syn])


def shell(rgb, alpha, width, frames=0, fin=0, fout=0, flash=0, blend=0, target=0):
    return cmd('Outline_Shell', Target=target, Red=rgb[0], Green=rgb[1], Blue=rgb[2], Alpha=alpha, Width=width,
               Frames=frames, FadeIn=fin, FadeOut=fout, Flash=flash, Blend=blend)


def invert(frames, fout):
    return cmd('Screen_Invert', Mode=1, Strength=1.0, Frames=frames, FadeIn=0, FadeOut=fout, Saturation=1.0,
               Brightness=1.0, Red=0.0, Green=0.0, Blue=0.0)


def meshvis(mesh, visible, persist, target=0):
    return cmd('Mesh_Visibility', Target=target, Mesh=MV.crc32(mesh), Visible=visible, Persist=persist)


def scripts(old):
    """the taunts (old: the user's game.bin scripts by name, for the side taunt's own lines)"""
    wait = cmd('FRAME', Frames=2.0)
    end = cmd('Script_End')
    white = (255.0, 255.0, 255.0)
    up = [wait, shell(white, 255.0, 1.5, 120, 4, 10, 0, 1), end]
    side = [shell((255.0, 30.0, 20.0), 255.0, 3.0, 150, 6, 15, 20, 1)] + list(old['AppealSR'])
    down_r = [wait, shell(white, 255.0, 1.5, 90, 4, 10, 0, 1), cmd('FRAME', Frames=10.0), invert(60, 10), end]
    down_l = [wait, shell(white, 255.0, 1.5, 90, 4, 10, 0, 1)] + [meshvis(m, 0, 0) for m in TWO_PART] + \
        [cmd('FRAME', Frames=10.0), invert(60, 10), end]
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
