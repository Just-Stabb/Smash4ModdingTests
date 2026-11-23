#!/usr/bin/env python3
"""Corrin's extra sword trail textures (tools/kamui_trail_cave.py KAMUI_TRAILS) from a picture: the trail texture
(<Name>.nut) and its glow (<Name>Add.nut), as her vanilla TexKamuiSwordTrace / TexKamuiSwordTraceAdd: NTP3, 128 x 128,
one mip, texture id 0, DXT5 for the trail and DXT1 for the Add.

  python3 -I tools/kamui_trail_build.py IMAGE OUT_DIR [--name TexKamuiSwordTraceCyan] [--add-gain 0.3]

IMAGE is laid out as a vanilla trail texture: U (left to right) along the trail, the newest part (the blade) on the
right fading toward the tail on the left; V (top to bottom) across the blade. Any size: it is scaled to 128 x 128
(bicubic, in premultiplied alpha, so fully transparent pixels' colour doesn't bleed into their neighbours).

The two textures are drawn by trail shader 1 (Sword_Glow Shader=1, docs/native-notes.md "The trail shaders"):
rgb = (t0.rgb x t0.a + t1.rgb x t1.a) x the vertex alpha, a = t0.a x the vertex alpha. So the trail texture's alpha is
the trail's shape, and the Add's rgb (DXT1, alpha 1) is light added on top: here the picture's own colour x its alpha x
ADD_GAIN, a soft glow of the same colour as vanilla's Add is of hers (TexKamuiSwordTraceAdd: a dim copy of her trail's
orange). Add gain 0 = a black Add: the trail drawn exactly as the picture.
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nut  # noqa: E402

SIZE = 128
ADD_GAIN = 0.3


def load(path):
    """the picture as float RGBA 0-1, scaled to SIZE x SIZE in premultiplied alpha"""
    from PIL import Image
    im = np.asarray(Image.open(path).convert('RGBA')).astype(np.float32) / 255.0
    a = im[..., 3:]
    pre = np.concatenate([im[..., :3] * a, a], 2)
    chans = [np.asarray(Image.fromarray(pre[..., c], 'F').resize((SIZE, SIZE), Image.BICUBIC)) for c in range(4)]
    out = np.clip(np.stack(chans, 2), 0, 1)
    a = out[..., 3:]
    rgb = np.where(a > 1e-4, out[..., :3] / np.maximum(a, 1e-4), 0)
    return np.concatenate([np.clip(rgb, 0, 1), a], 2)


def textures(img, add_gain=ADD_GAIN):
    """(trail .nut bytes, Add .nut bytes) from float RGBA SIZE x SIZE"""
    def u8(x):
        return np.clip(np.round(x * 255), 0, 255).astype(np.uint8)
    add = np.concatenate([img[..., :3] * img[..., 3:] * add_gain, np.ones_like(img[..., 3:])], 2)
    return (nut.write_ntp3([(0, nut.NTP3_FORMATS['dxt5'], [u8(img)])]),
            nut.write_ntp3([(0, nut.NTP3_FORMATS['dxt1'], [u8(add)])]))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('image')
    p.add_argument('out_dir')
    p.add_argument('--name', default='TexKamuiSwordTraceCyan')
    p.add_argument('--add-gain', type=float, default=ADD_GAIN)
    a = p.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    trail, add = textures(load(a.image), a.add_gain)
    for name, data in ((a.name, trail), (a.name + 'Add', add)):
        path = os.path.join(a.out_dir, name + '.nut')
        open(path, 'wb').write(data)
        print('%s: %d bytes' % (path, len(data)))


if __name__ == '__main__':
    main()
