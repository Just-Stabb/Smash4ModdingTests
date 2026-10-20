#!/usr/bin/env python3
"""Stage files for tools/stage_script_cave.py's moving-platform test, added to a built
NewStage01 (tools/minecraft_world.py's output).

  python3 tools/moving_platform_test.py SRC STAGE_DIR

SRC is Ultimate's stage/pickel_world (for the hay bale block), STAGE_DIR the built
stage/melee/NewStage01. Adds:
- a 3-block hay bale platform (bright, to tell it from the planks of the houses behind) in the model folder dyr_j_BG_most_far0_set (Battlefield's: one bone,
  an animation the stage plays; the folder's model was emptied by minecraft_world.py): the mesh is
  bound to the bone (bind 8, bone 0, vertices around it, as Battlefield's own), the bone's
  animation (animation/dyr_j_BG_most_far0_set/*.omo, PERIOD + 1 frames, the last = the first, as
  Battlefield's loops) moves it along stage_script_cave.motion around (CX, CY);
- the folder's model.xmb is replaced by stc_c_Ring_set's (Battlefield's dyr_j is draw range 2 / light
  set 3, the far background; the ring's is draw range 0, light set 4, as the island it sits by);
- its collision: a drop-through line on its top, rigged (lvd flag2) under the subname
  "<LINK>__move__" so the cave finds it by LINK, placed for the motion's zero offset (the cave moves
  it by motion(t)).

If the stage plays the animation and the cave runs, the platform and its collision move together;
if only one moves, that half doesn't work (see docs/minecraft-world.md).
"""
import os
import shutil
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lvd  # noqa: E402
import minecraft_world as M  # noqa: E402
import nud  # noqa: E402
import omo  # noqa: E402
import stage_script_cave as C  # noqa: E402

SET = 'dyr_j_BG_most_far0_set'
BONE_HASH = 0x181C1749          # its one bone (Floating_island02_O_OBJ_O_HIR)
CX, CY = -10.0, 50.0            # the platform's center at offset 0 (Plains: clear of the blocks)
WIDTH = 3                       # blocks


def build(src, stage):
    model = '%s/model/%s' % (stage, SET)
    cube = M.load_parts('%s/normal/model/bg_b_hay_bale_01_set' % src)
    parts = []
    for i in range(WIDTH):
        parts += M.translated(cube, np.array([(i - (WIDTH - 1) / 2) * 10.0, 0.0, 0.0]))
    tex = M.Textures(src)
    meshes = M.to_nud(M.merged(parts, 'mctest_platform'), tex, 'lit')
    for m in meshes:
        m.bind, m.bone = 8, 0
    open(model + '/model.nud', 'wb').write(nud.write(meshes))
    open(model + '/model.nut', 'wb').write(tex.nut([M.ATLAS]))
    shutil.copy('%s/model/%s/model.xmb' % (stage, M.RING_SET), model + '/model.xmb')

    path = '%s/animation/%s/%s.omo' % (stage, SET, SET)
    o = omo.Omo(open(path, 'rb').read())
    frames = int(C.PERIOD) + 1
    o.frames = frames
    o.nodes = []
    pos = [(CX + C.motion(t)[0], CY + C.motion(t)[1], 0.0) for t in range(frames)]
    omo.set_node(o, BONE_HASH, pos, [(0.0, 0.0, 0.0, 1.0)] * frames, [(1.0, 1.0, 1.0)] * frames)
    open(path, 'wb').write(o.encode())

    half = WIDTH * 5.0
    for f in os.listdir(stage + '/param'):
        if not f.endswith('.lvd'):
            continue
        lv = lvd.LVD(stage + '/param/' + f)
        c = lvd.collision('COL_00_%s' % C.LINK, [(CX - half, CY + 5), (CX + half, CY + 5)], [(0, 1)],
                          [M.mat_bytes(4)], drop_through=True)
        c.subname = '%s__move__' % C.LINK
        c.flags[1] = 1                      # rigged: filed in the link, moved by the cave
        c.use_start = 1
        lv.collisions = [x for x in lv.collisions if x.subname != c.subname] + [c]
        open(stage + '/param/' + f, 'wb').write(lv.write())
    return pos


def main():
    pos = build(sys.argv[1], sys.argv[2])
    print('platform: %d frames, x %.1f-%.1f, y %.1f-%.1f' % (len(pos), min(p[0] for p in pos), max(p[0] for p in pos),
                                                          min(p[1] for p in pos), max(p[1] for p in pos)))


if __name__ == '__main__':
    main()
