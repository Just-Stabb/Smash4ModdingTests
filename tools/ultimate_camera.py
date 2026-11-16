#!/usr/bin/env python3
"""Ultimate's victory cameras -> Smash 4 camera motions (docs/ultimate-port-guide.md "Win cameras").

Ultimate keeps a fighter's result-screen cameras in camera/fighter/<name>/cNN/j02win1-3.nuanmb (camera-SSBU.zip):
one animated `gya_camera` node (translation + rotation a frame, looking down its -Z) and a Camera group with its
FieldOfView (radians), NearClip, FarClip. Smash 4's result scene plays camera motions too: its script
(data/script/xscene_result.xtal, script-smash4-vanilla.zip) loads `motion/camera/result/<model name>/<n>/` for the
winner (the model name from get_fighter_model_name_from_fighter_kind, 0x030ED508: the kind's folder name, "master" for
kind 0x47 through kind_expand.py's name table; "NOT FOUND CAMERA!" -> `motion/camera/result/default/1/`) and starts it
on its scene camera (`start_motion`, 0x0310861C: the camera's motion player at +0x38, 0x02D38734, the same player stage
and Final Smash cameras use). A motion folder resource loads its .omo / .pac files (as fighter/<name>/camera/final/N/,
the Final Smash cameras: camera_motion.omo + camera_motion.vbn, Corrin's one `gya_camera` bone, the game's hash
0x1AC0648C, animated the same way). This writes each win's camera in that form, at the data root:

  motion/camera/result/<name>/<n>/camera_motion.omo   gya_camera: position (interpolated), rotation (type 5)
  motion/camera/result/<name>/<n>/camera_motion.vbn   the template's one bone (Corrin's)
  motion/camera/result/<name>/camera.json             per win: frames, field of view a frame, near / far clip (not
                                                      read by the game: the field of view isn't in the motion)

Not confirmed in game yet (Byleth v3's test): the vanilla folders' own file names / node form (the user's
data/motion/camera/result/), what <n> counts (the win pose 1-3 is assumed) and the field of view the scene uses.

  python3 tools/ultimate_camera.py convert NAME --out OUT [--costume c00]      (the pipeline's `camera` step)
  python3 tools/ultimate_camera.py convert-dir ULT_CAM_DIR OUT_ROOT NAME --template VBN   (OUT_ROOT: the data root)
  python3 tools/ultimate_camera.py info NUANMB...                               eye / target / field of view
Sources (port_sources.json): "ult_camera" (folders holding camera/fighter/<name>/), "camera_template" (a
gya_camera camera_motion.vbn: vanilla fighter/kamui/camera/final/2/camera_motion.vbn).
"""
import argparse
import json
import math
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import omo  # noqa: E402

GYA_CAMERA = 0x1AC0648C        # the game's hash of 'gya_camera' (Corrin's final camera_motion.vbn)
WINS = (1, 2, 3)


def _qmat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def read_camera(path):
    """{'pos': [F x 3], 'rot': [F x 4 xyzw], 'fov': [F], 'near', 'far', 'frames'} of an Ultimate camera .nuanmb"""
    import ssbh_data_py as s
    a = s.anim_data.read_anim(path)
    tr, cam = None, {}
    for g in a.groups:
        for n in g.nodes:
            for t in n.tracks:
                if g.group_type.name == 'Transform' and tr is None:
                    tr = t.values
                elif g.group_type.name == 'Camera':
                    cam[t.name] = t.values
    if tr is None:
        raise SystemExit('%s: no camera transform track' % path)
    frames = int(round(a.final_frame_index)) + 1
    idx = np.minimum(np.arange(frames), len(tr) - 1)
    pos = np.array([tr[i].translation for i in idx], dtype=np.float64)
    rot = np.array([tr[i].rotation for i in idx], dtype=np.float64)
    fov = cam.get('FieldOfView', [0.5])
    fov = [float(fov[min(i, len(fov) - 1)]) for i in range(frames)]
    return dict(pos=pos, rot=rot, fov=fov, frames=frames, near=float(cam.get('NearClip', [1.0])[0]),
                far=float(cam.get('FarClip', [100000.0])[0]))


def framing(c, fr):
    """eye, the point it looks at nearest the fighter's vertical axis, its distance, the view height there"""
    p, fwd = c['pos'][fr], -_qmat(c['rot'][fr])[:, 2]
    d2 = fwd[[0, 2]]
    t = -float(np.dot(p[[0, 2]], d2)) / max(float(np.dot(d2, d2)), 1e-9)
    return p, p + t * fwd, t, 2 * t * math.tan(c['fov'][fr] / 2)


def camera_omo(c):
    o = omo.Omo.__new__(omo.Omo)
    o.head = b'\x00\x01\x00\x03\x0b\x13\x16\x0d\x00\x01'       # Corrin's final camera 2's header words
    o.frames = c['frames']
    o.nodes = []
    rot = [tuple(q) for q in c['rot']]
    omo.set_node(o, GYA_CAMERA, [tuple(p) for p in c['pos']], rot, [(1.0, 1.0, 1.0)] * c['frames'])
    return o.encode()


def result_dir(out_root, name):
    """the result scene's camera folder of a fighter (xscene_result.xtal: motion/camera/result/<model name>/<n>/)"""
    return os.path.join(out_root, 'motion', 'camera', 'result', name)


def convert_dir(cam_dir, out_root, name, template):
    """cam_dir: Ultimate's camera/fighter/<name>/cNN; out_root: the package's data root (OUT/NAME); name: the kind's
    folder name"""
    out = result_dir(out_root, name)
    info = {}
    for w in WINS:
        src = os.path.join(cam_dir, 'j02win%d.nuanmb' % w)
        if not os.path.exists(src):
            continue
        c = read_camera(src)
        d = os.path.join(out, '%d' % w)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'camera_motion.omo'), 'wb').write(camera_omo(c))
        shutil.copy(template, os.path.join(d, 'camera_motion.vbn'))
        e0, t0, _d0, h0 = framing(c, 0)
        e1, t1, _d1, h1 = framing(c, c['frames'] - 1)
        info['%d' % w] = dict(frames=c['frames'], fov=[round(x, 5) for x in c['fov']], near=c['near'], far=c['far'],
                                 first=dict(eye=[round(x, 2) for x in e0], target=[round(x, 2) for x in t0],
                                            view_height=round(h0, 2)),
                                 last=dict(eye=[round(x, 2) for x in e1], target=[round(x, 2) for x in t1],
                                           view_height=round(h1, 2)))
    os.makedirs(out, exist_ok=True)
    json.dump(dict(_comment='Ultimate\'s win cameras (tools/ultimate_camera.py); Smash 4 plays camera_motion.omo '
                   'without a field of view: it is here', source=cam_dir, wins=info),
              open(os.path.join(out, 'camera.json'), 'w'), indent=1)
    return sorted(info)


def cam_source(src, ult, costume='c00'):
    for root in src.roots('ult_camera'):
        for rel in ('camera/fighter/%s/%s' % (ult, costume), 'fighter/%s/%s' % (ult, costume), '%s/%s' % (ult, costume)):
            if os.path.isdir(os.path.join(root, rel)):
                return os.path.join(root, rel)
    return None


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('convert')
    p.add_argument('name')
    p.add_argument('--out', required=True, help='the pipeline\'s OUT (OUT/NAME: the data root)')
    p.add_argument('--costume', default='c00', help='Ultimate\'s cameras are the same in every costume (Byleth c00 / '
                   'c01 differ: the female poses; the male\'s until per-costume result motions)')
    p = sub.add_parser('convert-dir')
    p.add_argument('cam_dir')
    p.add_argument('out_root')
    p.add_argument('name')
    p.add_argument('--template', required=True)
    p = sub.add_parser('info')
    p.add_argument('files', nargs='+')
    a = ap.parse_args()
    if a.cmd == 'info':
        for f in a.files:
            c = read_camera(f)
            for fr in (0, c['frames'] - 1):
                e, t, d, h = framing(c, fr)
                print('%s frame %d: eye (%.1f, %.1f, %.1f) target (%.1f, %.1f, %.1f) distance %.1f, fov %.2f, view '
                      'height %.1f' % (os.path.basename(f), fr, *e, *t, d, c['fov'][fr], h))
        return
    if a.cmd == 'convert-dir':
        print('win cameras: %s' % ', '.join(convert_dir(a.cam_dir, a.out_root, a.name, a.template)))
        return
    import port_sources
    src = port_sources.load()
    sys.path.insert(0, HERE)
    import ultimate_port
    cfg = ultimate_port.load_cfg(a.name)
    cam = cam_source(src, cfg['ult'], a.costume)
    tmpl = src.get('camera_template')
    if not cam or not tmpl:
        sys.exit('camera: no %s (port_sources "ult_camera": camera-SSBU.zip\'s folder) or no "camera_template" '
                 '(vanilla fighter/kamui/camera/final/2/camera_motion.vbn)' % ('camera/fighter/%s/%s' % (cfg['ult'], a.costume)
                                                                               if not cam else 'template'))
    done = convert_dir(cam, os.path.join(a.out, a.name), a.name, tmpl)
    print('win cameras (%s): %s' % (cam, ', '.join(done) or 'none'))


if __name__ == '__main__':
    main()
