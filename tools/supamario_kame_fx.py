#!/usr/bin/env python3
"""Supamario's Kamehameha charge orb (PtcSupamarioKameCharge), the custom-effect chain test.

  python3 tools/supamario_kame_fx.py BASE.ptcl OUT.ptcl

BASE: Supamario's supamario.010d0000.ptcl without the set (v4: 19 sets); the set is appended as
set 19 (the .efc entry 0x16, effect id 0x03410016, names set 20, 1-based).

Built from Mario's fireball (PtcMarioFireball) emitters, recoloured blue, keeping the textures the
emitters were made for:
- spark1 (sparks), PtcMarioFireball (the ball: flame flipbook over a disc), FireballShootFlash
  (the flash): their own textures; every recoloured emitter's colour keys (both tracks) get red
  and blue swapped;
- flare1_alpha (the glow): our own texture, a quarter of a round glow (the template's texture is a
  quarter, drawn mirrored), in the template's format: BC4, the shape in the colour (R = G = B, the
  game's fx textures carry the shape there, alpha 1). v5's orb was BC3 with the shape only in alpha
  and white colour, so every emitter drew a solid square;
- refraction1 / refraction1_Copy1 (the heat shimmer): unchanged (their texture is a distortion
  map, 128 grey = none: v5's white orb there shifted the screen behind a square);
- the two smoke emitters: left out.
"""
import sys

import numpy as np

import ptcl

SET = 'PtcSupamarioKameCharge'
TEMPLATE = 'PtcMarioFireball'
# (template emitter, new name, recolour, own glow texture)
EMITTERS = (('spark1', 'KameSpark', True, False),
            ('refraction1', 'KameShimmer', False, False),
            ('refraction1_Copy1', 'KameShimmer2', False, False),
            ('flare1_alpha', 'KameGlow', True, True),
            ('FireballShootFlash', 'KameFlash', True, False),
            ('PtcMarioFireball', 'KameOrb', True, False))


def blue(r, g, b, a):
    """red <-> blue: the fireball's yellow / orange / red over a particle's life become pale cyan /
    blue / deep blue (and a subtracted colour, as flare1_alpha's cyan, takes away the other way)"""
    return (b, g, r, a)


def glow_quarter(n=64):
    """the bright corner at the bottom right, as the template's quarter glow"""
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.hypot(n - 0.5 - xx, n - 0.5 - yy) / n
    v = (np.clip(1 - r, 0, 1) ** 2 * 255).astype(np.uint8)
    img = np.zeros((n, n, 4), np.uint8)
    img[..., 0] = img[..., 1] = img[..., 2] = v
    img[..., 3] = 255
    return img


def build(base):
    p = ptcl.Ptcl(base)
    assert SET not in [p.set_name(i) for i in range(len(p.sets))], 'BASE already has ' + SET
    t = p.find_set(TEMPLATE)
    names = [p.emitter_name(e['data']) for e in p.sets[t]['emitters']]
    ems = [p.emitter_bytes(t, names.index(src)) for src, _n, _c, _g in EMITTERS]
    si = p.new_set(SET, ems, [n for _s, n, _c, _g in EMITTERS])
    for e, (_src, _n, recolour, glow) in zip(p.sets[si]['emitters'], EMITTERS):
        d = e['data']
        if recolour:
            for track in (0, 1):
                keys = p.color_keys(d, track)
                p.set_color_keys(d, track, [blue(*k) for k in keys])
        if glow:
            p.set_texture(d, 0, glow_quarter())         # template format (BC4)
    return p, si


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    base = open(sys.argv[1], 'rb').read()
    p, si = build(base)
    out = p.build()
    q = ptcl.Ptcl(out)
    assert q.validate() == [], q.validate()
    assert q.set_name(si) == SET and si == len(q.sets) - 1
    open(sys.argv[2], 'wb').write(out)
    print('%s: set %d (efc 1-based %d), %d emitters; %d -> %d bytes'
          % (sys.argv[2], si, si + 1, len(q.sets[si]['emitters']), len(base), len(out)))


if __name__ == '__main__':
    main()
