#!/usr/bin/env python3
"""Ultimate sword trail textures (effect/fighter/<name>/trail/*.nutexb) -> Smash 4 trail textures
(effect/<name>/trail/<Name>.nut), named as tools/trail_table_cave.py's NEW_TRAILS.

  python3 tools/ultimate_trails.py [--shader 3 [--gain G]] TRAIL_DIR OUT_DIR MAIN.nutexb,MASK.nutexb=SmashName ...

Ultimate's AFTER_IMAGE4_ON takes two textures: a colour one (RGB + alpha: the swing's shape fading
toward the trail's end) and a white one whose RGB is a mask. A Smash 4 trail is a pair too
(`Sword_Glow` Texture1 / Texture2, e.g. Ike's TexIkeSwordTrace / TexIkeSwordTraceAdd): vanilla's
are NTP3 (untiled), one mip, 128 x 128, DXT5 for the trail and DXT1 for its "Add" (texture id 0).
So <SmashName>.nut = the colour texture with its alpha x the mask (DXT5), <SmashName>Add.nut its
colour x that alpha x ADD_GAIN (DXT1, no alpha). Both are oriented as vanilla's (the blade's edge
on the right, fading to the left), so no flip.

  --shader 3 [--gain G]: for trail shader 3 (tools/trail_shader.py: Ultimate's retracting trail),
  which samples the two apart as Ultimate's does: <SmashName>.nut = the colour texture as is (DXT5),
  <SmashName>Add.nut = the mask (red) in alpha and G / 2 in rgb (DXT5): the colour gain,
  AFTER_IMAGE4_ON's arg 28 (default 1.4, Sephiroth's).
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nut  # noqa: E402
import nutexb  # noqa: E402

SIZE = (128, 128)
ADD_GAIN = 0.5
GAIN = 1.4


def rgba(path):
    return nutexb.decode(nutexb.Nutexb(path)).astype(np.float32) / 255.0


def resize(img):
    from PIL import Image
    u8 = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
    return np.asarray(Image.fromarray(u8, 'RGBA').resize(SIZE, Image.LANCZOS)).astype(np.float32) / 255.0


def convert(main, mask, shader=1, gain=GAIN):
    c, m = resize(rgba(main)), resize(rgba(mask))
    u8 = lambda x: (np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8)  # noqa: E731
    if shader == 3:
        packed = np.dstack([np.full(m.shape[:2] + (3,), gain / 2), m[..., 0]])
        return (nut.write_ntp3([(0, nut.NTP3_FORMATS['dxt5'], [u8(c)])]),
                nut.write_ntp3([(0, nut.NTP3_FORMATS['dxt5'], [u8(packed)])]))
    a = c[..., 3] * m[..., 0]
    trail = np.dstack([c[..., :3], a])
    add = np.dstack([c[..., :3] * a[..., None] * ADD_GAIN, np.ones_like(a)])
    return (nut.write_ntp3([(0, nut.NTP3_FORMATS['dxt5'], [u8(trail)])]),
            nut.write_ntp3([(0, nut.NTP3_FORMATS['dxt1'], [u8(add)])]))


def main():
    argv, shader, gain = sys.argv[1:], 1, GAIN
    for opt in ('--shader', '--gain'):
        if opt in argv:
            i = argv.index(opt)
            if opt == '--shader':
                shader = int(argv[i + 1])
            else:
                gain = float(argv[i + 1])
            del argv[i:i + 2]
    if len(argv) < 3 or shader not in (1, 3):
        sys.exit(__doc__)
    src, out = argv[0], argv[1]
    os.makedirs(out, exist_ok=True)
    for spec in argv[2:]:
        files, name = spec.split('=')
        main_f, mask_f = files.split(',')
        trail, add = convert(os.path.join(src, main_f), os.path.join(src, mask_f), shader, gain)
        open(os.path.join(out, name + '.nut'), 'wb').write(trail)
        open(os.path.join(out, name + 'Add.nut'), 'wb').write(add)
        print('%s + %s -> %s.nut, %sAdd.nut' % (main_f, mask_f, name, name))


if __name__ == '__main__':
    main()
