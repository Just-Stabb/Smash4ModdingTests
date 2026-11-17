#!/usr/bin/env python3
"""TEST_ONLY game script for Outline_Set and Mesh_Visibility (model_commands v1, exe_v46z_outline), built on the user's
own Dr. Mario (every other script kept as it is):

  python3 tools/model_commands_ingame_test_build.py MARIOD_DIR OUT_DIR

MARIOD_DIR: the fighter/mariod folder (script/animcmd/body/{game,effect}.bin). OUT_DIR gets script/animcmd/body/game.bin
(the taunts below) and the user's own effect.bin (an earlier test's effect.bin, if installed, goes back to his).

  AppealHiR / AppealHiL (up): a white edge glow, edge only (Tint 0), Alpha 510, faded in over 4 frames, held 120 frames
             (2 s), out over 10
  AppealSR (side; AppealSL jumps to it): a red pulsing outline (a pulse every 20 frames, a light red tint 48), held 150
             frames, out over 15; his own side-taunt lines (the cape article) kept
  AppealLwR (down, facing right): his stethoscope / head mirror (stethoscope_VIS_O_OBJ) hidden until the end of the
             taunt (Persist 0)
  AppealLwL (down, facing left): the same mesh hidden persistently (Persist 1): it stays hidden after the taunt, until
             the next down taunt facing right (whose own hide replaces it and ends with that taunt) or a KO / training
             reset
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd  # noqa: E402
import mesh_vis_cave as MV  # noqa: E402

MESH = 'stethoscope_VIS_O_OBJ'


def cmd(name, **kw):
    """an ACMD command by its Sm4shCommand name, its parameters by name (acmd_info.json's syntax, all given)"""
    hit = [(k, v) for k, v in acmd.INFO.items() if v['name'] == name]
    assert len(hit) == 1, name
    ident, info = hit[0]
    syn = info['syntax']
    assert sorted(syn) == sorted(kw), (name, syn, sorted(kw))
    return acmd.Command(ident, [kw[s] for s in syn])


def outline(rgb, alpha, tint=0.0, frames=0, fin=0, fout=0, flash=0, target=0):
    return cmd('Outline_Set', Target=target, Red=rgb[0], Green=rgb[1], Blue=rgb[2], Alpha=alpha, Tint=tint,
               Frames=frames, FadeIn=fin, FadeOut=fout, Flash=flash)


def meshvis(visible, persist, mesh=MESH, target=0):
    return cmd('Mesh_Visibility', Target=target, Mesh=MV.crc32(mesh) if isinstance(mesh, str) else mesh,
               Visible=visible, Persist=persist)


def scripts(old):
    """the taunts (old: the user's game.bin scripts by name, for the side taunt's own lines)"""
    wait = cmd('FRAME', Frames=2.0)
    end = cmd('Script_End')
    up = [wait, outline((255.0, 255.0, 255.0), 510.0, 0.0, 120, 4, 10), end]
    side = [outline((255.0, 30.0, 20.0), 450.0, 48.0, 150, 6, 15, 20)] + list(old['AppealSR'])
    down_r = [wait, meshvis(0, 0), end]
    down_l = [wait, meshvis(0, 1), end]
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
