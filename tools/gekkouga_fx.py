#!/usr/bin/env python3
"""Greninja's effect bank additions (fighters/gekkouga/README.md "Skeleton v1.2" on): flipbook emitter sets made from
the user's processed video effects (tools/fx_video_to_flipbook.py atlases + sidecars) appended to his
gekkouga.010d0000.ptcl / .efc (data/fighter/gekkouga/effect/gekkouga/).

  python3 -I tools/gekkouga_fx.py IN_EFFECT_DIR KIRBY_PTCL FX_PKG OUT_EFFECT_DIR
      IN_EFFECT_DIR   his vanilla effect folder (gekkouga.010d0000.ptcl / .efc)
      KIRBY_PTCL      vanilla kirby.010d0000.ptcl (the template emitter: PtcKirbyStoneEnd / stone)
      FX_PKG          the flipbooks: FX_PKG/<name>/<name>_atlas.png + <name>.json (the user's greninja_fire_effects_v1)
      OUT_EFFECT_DIR  gets the new .ptcl / .efc (nothing else of the folder changes)

Every new emitter is a copy of one vanilla template, Kirby's PtcKirbyStoneEnd/stone (cross-checked with
tools/eft_vertex.features over the 7128 emitters of the vanilla banks): a CPU particle (eft moves it: follow type 0
draws it on its emitter's live matrix, so a following call keeps it on the article), a camera billboard (particle type
0), a vertex program that plays slot 0's flipbook, colour combiner 1 (colour 0 x the texture's rgb, alpha = the
texture's alpha), one BC3 RGBA texture (its own texture: same format and channels as the template's), clamped UVs, no
lighting, not premultiplied. Its shader (55 in kirby's bank) is imported once. Blend (0x324, not shader-keyed) per set:
0 normal (the green-screen footage: dark smoke must darken) or 1 additive (fire on black, luma matte).

One particle per call (one emission, emitter +0x2FF one-time, end 1), no motion, no rotation, no random size, alpha 1,
white; its size the quad's (eft's quad is +- 0.5 x the particle scale, cross_f 0x04A66B9C); the flipbook from the
sidecar (loop: mode 2, life forever, fade 1.0 a frame: terminated, it goes at once; one-shot: mode 4 clamp, life =
cells x frames a cell, fade 0: a fade (its owner gone) doesn't cut it short). Placed by the emitter's translation so the
footage's anchor (the skeleton's feet, the explosion's base) sits at the call's point.

Facing: a billboard is not turned by its emitter, so the skeleton has two sets, right (the footage as shot) and left
(each cell mirrored in place); its MSC picks one by its way.
"""
import json
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import efc as EFC  # noqa: E402
import ptcl as P  # noqa: E402

BANK = 0x330                       # his effect bank (0x300 + kind 0x30): ids 0x0330nnnn
VANILLA_ENTRIES = 22               # his vanilla .efc: entries 0x00 - 0x15
TEMPLATE = ('PtcKirbyStoneEnd', 2)  # kirby.010d0000.ptcl: set, emitter (stone)
BC3 = 0x33
FOREVER = 0x7FFFFFFF

# ---- skeleton v1.2: the Running Skeleton's look (its MSC fighters/gekkouga/weapons/skeleton.c sk_fx_*)
SK_BODY_H = 28.0                   # the body (feet to head) this tall: the collision box's height (12 x 28)
SK_BODY_TOP_V = 0.141              # the body's top / bottom in a cell (alpha >= 0.5, median over the 55 cells of
SK_BODY_BOTTOM_V = 0.907           # skeleton_run_atlas.png; the sidecar's anchor: feet at 0.933 of the frame)
SK_BOOM_DIAMETER = 44.0            # the explosion's widest (its smoke column, cells 24 - 32: u 0.08 - 0.93) = the
SK_BOOM_WIDEST_U = 0.84            # hitbox's 22 radius x 2
SK_BOOM_BASE_V = 0.895             # its base (alpha >= 0.5's lowest row, every cell): on the ground
SK_HIT_W = 18.0                    # a hit's sparks: the quad 18 units across (centred on the hit)

# ---- burn v2: fire (the luma-matted footage, additive: fire on black). Heights of the quad; widths from the cell's shape
FIRE_BODY_H = 30.0                 # on a burning fighter (fire_small_4): its base on his feet (TransN), ~16 of flame, ~21 wide
FIRE_TIP_H = 15.0                  # at the outer ends of his water (fire_torch_012): centred on the call (x the call's size:
                                   # ~7 of flame at 1)
FIRE_TRAIL_H = 22.0                # the smashes' trails (fire_ground_10): its base on the call's point, ~14.5 of flame
FIRE_RING = dict(n=15, r0=5.0, v=0.9, air=0.8, life=14, seed=7)   # burn v2.2 / v2.3: neutral air's ring of flames: n
                                   # flames round a circle of radius r0, flying out at v a frame x air a frame (~9 by frame
                                   # 10: x the call's 1.45, 13, the water burst's bright edge in fx_render's render; its
                                   # faint mist reaches ~21), gone by 14 (the burst by ~13)
# v2.3 (the user: "varying fire effects, rotations and fire direction based on Greninja's position in the circle"): one
# emitter a flame, the assets in turn round the ring (quad height at size 1, each its own flipbook's first 31 cells),
# each turned so its own flame's tip (ring_tip_angle: measured on its atlas) points out from the centre, +- RING_JITTER
# degrees, sized x RING_SIZE_VAR
RING_ASSETS = (('fire_small_4', 6.5), ('fire_torch_012', 9.0), ('fire_small_5', 6.0), ('fire_ground_10', 8.0),
               ('fire_torch_026', 7.0))
RING_JITTER = 12.0
RING_POS_JITTER = 4.0              # degrees round the circle
RING_SIZE_VAR = (0.85, 1.15)
FIRE_FADE = 15                     # frames the body / trail fires take to go when ended with a fade (0x2723 (0, 0))


def cell_aspect(name):
    d = sidecar(name)
    return d['cell_size'][0] / d['cell_size'][1]


def _fire_sets():
    body = dict(atlas='fire_small_4', blend=1, size=(FIRE_BODY_H * cell_aspect('fire_small_4'), FIRE_BODY_H),
                fade=FIRE_FADE)
    body['offset'] = (0.0, (feet_cell_v('fire_small_4') - 0.5) * FIRE_BODY_H)
    tip = dict(atlas='fire_torch_012', blend=1, size=(FIRE_TIP_H * cell_aspect('fire_torch_012'), FIRE_TIP_H),
               offset=(0.0, 0.0))
    trail = dict(atlas='fire_ground_10', blend=1, size=(FIRE_TRAIL_H * cell_aspect('fire_ground_10'), FIRE_TRAIL_H),
                 fade=FIRE_FADE)
    trail['offset'] = (0.0, (feet_cell_v('fire_ground_10') - 0.5) * FIRE_TRAIL_H)
    ring = dict(ring=FIRE_RING, left=False)
    ring_l = dict(ring=FIRE_RING, left=True)
    return [('PtcGekkougaFireBody', body), ('PtcGekkougaFireTip', tip), ('PtcGekkougaFireTrail', trail),
            ('PtcGekkougaFireRing', ring), ('PtcGekkougaFireRingL', ring_l)]


def all_sets(burn2=True):
    """every set in entry order: skeleton v1.2's, then burn v2's"""
    return _sk_sets() + (_fire_sets() if burn2 else [])


def _sk_sets():
    h = SK_BODY_H / (SK_BODY_BOTTOM_V - SK_BODY_TOP_V)
    body = dict(atlas='skeleton_run', blend=0, size=(h * (2048 / 6) / (2048 / 10), h))
    feet_v = feet_cell_v('skeleton_run')
    body['offset'] = (0.0, (feet_v - 0.5) * h)
    bw = SK_BOOM_DIAMETER / SK_BOOM_WIDEST_U
    boom = dict(atlas='explosion_simple_24', blend=0, size=(bw, bw * (1024 / 6) / (1024 / 7)))
    boom['offset'] = (0.0, (SK_BOOM_BASE_V - 0.5) * boom['size'][1])
    hit = dict(atlas='impact_sparks', blend=0, size=(SK_HIT_W, SK_HIT_W), offset=(0.0, 0.0))
    return [('PtcGekkougaSkeletonR', dict(body, mirror=False)),
            ('PtcGekkougaSkeletonL', dict(body, mirror=True)),
            ('PtcGekkougaSkeletonHit', hit),
            ('PtcGekkougaSkeletonBoom', boom)]


FX_PKG = None


def sidecar(name):
    return json.load(open(os.path.join(FX_PKG, name, name + '.json')))


def atlas(name):
    from PIL import Image
    return np.asarray(Image.open(os.path.join(FX_PKG, name, name + '_atlas.png')).convert('RGBA'))


def feet_cell_v(name):
    """the sidecar's feet (anchor body_bottom_v, across the frame) in the cell: the frame is centred in its cell"""
    d = sidecar(name)
    ch, fh = d['cell_size'][1], d['frame_size_in_cell'][1]
    return ((ch - fh) // 2 + d['anchor']['body_bottom_v'] * fh) / ch


def mirror_cells(img, nx, ny):
    """each cell mirrored left-right in place (cells on i x W / nx, rounded to whole pixels: the frames are centred
    with a clear margin, so a pixel's rounding moves nothing out of its cell)"""
    out = img.copy()
    h, w = img.shape[:2]
    for i in range(nx):
        x0, x1 = int(round(i * w / nx)), int(round((i + 1) * w / nx))
        out[:, x0:x1] = img[:, x0:x1][:, ::-1]
    return out


def template(p, kirby):
    """Kirby's stone imported (its shader once), without its texture: the emitter bytes"""
    si = kirby.find_set(TEMPLATE[0])
    assert kirby.emitter_name(kirby.sets[si]['emitters'][TEMPLATE[1]]['data']) == 'stone'
    return p.import_emitter(kirby, si, TEMPLATE[1], skip_slots=(0,))


TABLE = 32                         # eft's pattern table: 32 entries (CB2 ptnAnm0's vec4 17 - 24, from emitter 0x4E0); every
                                   # vanilla flipbook program reads its cell from the table (no vanilla emitter has more
                                   # than 32 cells: 7128 checked)
MODE = 4                           # flipbook mode 4 (uboFlag 0x8, cross_f 0x04A5A858): the cell is table[(age / frames a
                                   # cell) mod count] (Kirby's stone program run in tools/latte_exec.py: mode 2 adds a random
                                   # start, mode 1 spreads the count over the life)


def chunks(n, size):
    """n cells cut into runs of at most size (as even as possible): [(first cell, count)]"""
    m = -(-n // size)
    out, at = [], 0
    for i in range(m):
        c = n // m + (1 if i < n % m else 0)
        out.append((at, c))
        at += c
    return out


def flip_plan(n, k, loop):
    """the emitters of one flipbook (n cells, k frames a cell): [{first, cells, table, start, life, period}]. Up to 32
    cells: one emitter (a loop lives for ever, its table wrapping; a one-shot lives n x k). More: one emitter a run of
    cells (the table holds 32), each born when its run is due (start frame = k x the cells before it), living its run's
    frames plus one, its table the run and its last cell again (that extra frame shows it: a birth a frame late leaves
    no gap, the hand-over frame shows two adjacent cells), a loop's runs born again every n x k frames; a one-shot's
    last run lives its frames only"""
    if n <= TABLE:
        return [dict(first=0, cells=n, table=list(range(n)), start=0, life=FOREVER if loop else n * k, period=0)]
    out = []
    runs = chunks(n, TABLE - 1)
    for i, (a, c) in enumerate(runs):
        held = loop or i < len(runs) - 1
        out.append(dict(first=a, cells=c, table=list(range(a, a + c)) + ([a + c - 1] if held else []), start=a * k,
                        life=c * k + (1 if held else 0), period=n * k if loop else 0))
    return out


def ring_tip_angle(name):
    """the direction its flames point in the footage (degrees, 90 = up, counter-clockwise): the median over its first
    31 cells of base -> tip, the alpha-weighted centres of the bottom and top 35 % of each cell's alpha"""
    d = sidecar(name)
    img = atlas(name).astype(np.float32) / 255
    h, w = img.shape[:2]
    nx, ny = d['columns'], d['rows']
    cw, ch = w / nx, h / ny
    out = []
    for k in range(min(d['frames'], TABLE - 1)):
        i, j = k % nx, k // nx
        c = img[int(round(j * ch)):int(round((j + 1) * ch)), int(round(i * cw)):int(round((i + 1) * cw)), 3]
        tot = c.sum()
        if tot < 1:
            continue
        ys, xs = np.mgrid[0:c.shape[0], 0:c.shape[1]]
        rows = c.sum(1)
        yb = c.shape[0] - 1 - int(np.searchsorted(np.cumsum(rows[::-1]) / tot, 0.35))
        yt = int(np.searchsorted(np.cumsum(rows) / tot, 0.35))
        lo, hi = c[yb:], c[:yt + 1]
        bx, by = (lo * xs[yb:]).sum() / lo.sum(), (lo * ys[yb:]).sum() / lo.sum()
        tx, ty = (hi * xs[:yt + 1]).sum() / hi.sum(), (hi * ys[:yt + 1]).sum() / hi.sum()
        out.append(math.degrees(math.atan2(by - ty, tx - bx)))
    return float(np.median(out))


def ring_flames(left):
    """burn v2.3: the ring's flames: [{atlas, height, phi (degrees round the circle: 0 forward along his facing, 90 up),
    rot (the billboard's turn, degrees counter-clockwise), size, start (its table's first cell)}]. Facing left the game
    mirrors the places (the call's matrix) but not a billboard's turn: the left set's turns are worked out from the
    places as seen (180 - phi), its flames otherwise the same"""
    rng = np.random.RandomState(FIRE_RING['seed'])
    n = FIRE_RING['n']
    tips = {a: ring_tip_angle(a) for a, _h in RING_ASSETS}
    out = []
    for i in range(n):
        atl, hgt = RING_ASSETS[i % len(RING_ASSETS)]
        phi = 360.0 * i / n + rng.uniform(-RING_POS_JITTER, RING_POS_JITTER)
        jit = rng.uniform(-RING_JITTER, RING_JITTER)
        size = rng.uniform(*RING_SIZE_VAR)
        start = int(rng.randint(0, TABLE - 1))
        seen = (180.0 - phi) if left else phi
        out.append(dict(atlas=atl, height=hgt, phi=phi, rot=(seen - tips[atl] + jit + 180.0) % 360.0 - 180.0, size=size,
                        start=start, tip=tips[atl], jitter=jit))
    return out


def ring_fields(p, em, ring, flame):
    """burn v2.2 / v2.3: one flame of the ring: one particle at radius r0 round the call's YZ plane (the burst's
    billboards' circle seen side-on) at its angle phi, flying out along it (directional speed v, air resistance air) as
    the burst's edge grows, turned so its tip points out (rotation Z: a billboard's turn on screen, counter-clockwise),
    fading in quickly, held, fading out over the last 55 % of its life, a little bigger after 30 %; played out when ended"""
    f = p.set_field
    ph = math.radians(flame['phi'])
    dy, dz = math.sin(ph), math.cos(ph)
    f(em, 'volume_type', 0)
    f(em, 'volume_radius', [0.0, 0.0, 0.0])
    f(em, 'emit_rate', 1.0)
    f(em, 'figure_velocity', 0.0)
    f(em, 'emit_direction', [0.0, dy, dz])
    f(em, 'emitter_velocity', ring['v'])
    f(em, 'air_resistance', ring['air'])
    f(em, 'rotation_init', [0.0, 0.0, math.radians(flame['rot'])])
    f(em, 'alpha_init', 0.6)
    f(em, 'alpha_diff21', 0.4)
    f(em, 'alpha_diff32', -1.0)
    f(em, 'alpha_section1', 0.12)
    f(em, 'alpha_section2', 0.45)
    f(em, 'scale_init_ratio', [0.6, 0.6])
    f(em, 'scale_diff21', [0.4, 0.4])
    f(em, 'scale_diff32', [0.0, 0.0])
    f(em, 'scale_sections', [30, 100])
    p.set_emitter_srt(em, translation=(0.0, ring['r0'] * dy, ring['r0'] * dz))
    struct.pack_into('>f', em, 0x82C, 0.0)


def ring_emitters(p, tmpl, name, spec):
    """the ring's set: one emitter a flame (ring_flames), each its asset's flipbook"""
    out = []
    for i, fl in enumerate(ring_flames(spec['left'])):
        sub = dict(atlas=fl['atlas'], blend=1, size=(fl['height'] * fl['size'] * cell_aspect(fl['atlas']),
                                                       fl['height'] * fl['size']),
                   offset=(0.0, 0.0), ring=dict(spec['ring'], flame=fl))
        out += flip_emitters(p, tmpl, name if i == 0 else '%s_%d' % (name, i + 1), sub)
    return out


def flip_emitters(p, tmpl, name, spec):
    """the emitters of one flipbook billboard (module docstring; flip_plan) from the template bytes"""
    import vfxb_to_ptcl as VP
    d = sidecar(spec['atlas'])
    nx, ny, n, k = d['columns'], d['rows'], d['frames'], d['frames_per_cell_at_60fps']
    loop = d['playback'] == 'loop'
    img = atlas(spec['atlas'])
    assert img.shape[:2] == tuple(d['atlas_size'][::-1])
    if spec.get('mirror'):
        img = mirror_cells(img, nx, ny)
    out = []
    plan = flip_plan(n, k, loop)
    ring = spec.get('ring')
    if ring:                                       # burn v2.3: one flame: the flipbook's first cells from its start
        n = min(n, TABLE - 1)                      # (out of step with the others: eft's random start, 0x4D9, is one UV
        st = ring['flame']['start'] % n            # shift per emitter, 0x04A54A88)
        plan = [dict(first=0, cells=n, table=[(c + st) % n for c in range(n)], start=0, life=ring['life'], period=0)]
    for j, run in enumerate(plan):
        em = bytearray(tmpl)
        struct.pack_into('>I', em, 0x38, p.add_name(name if j == 0 else '%s_%d' % (name, j + 1)))
        sampler = struct.unpack_from('>I', em, P.TEXRES + 0x0C)[0]
        p.set_texture(em, 0, img, BC3)             # the runs share one copy (ptcl.add_texture: the same image)
        assert struct.unpack_from('>I', em, P.TEXRES + 0x0C)[0] == sampler == 0x22000100   # clamped U / V
        f = p.set_field
        f(em, 'blend_type', spec['blend'])
        f(em, 'volume_type', 0)
        f(em, 'volume_radius', [0.0, 0.0, 0.0])
        f(em, 'start_frame', run['start'])
        f(em, 'emit_start', 0)
        if run['period']:                          # born again every period frames, for ever
            f(em, 'one_time', 0)
            f(em, 'end_frame', FOREVER)
            f(em, 'emit_interval', run['period'] - 1)
        else:                                      # once (the shadow's: one-time, end 1)
            f(em, 'one_time', 1)
            f(em, 'end_frame', 1)
            f(em, 'emit_interval', 10)
        f(em, 'emit_interval_random', 0)
        f(em, 'emit_rate', 1.0)
        f(em, 'ptcl_life', run['life'])
        f(em, 'ptcl_life_random', 0)
        f(em, 'figure_velocity', 0.0)
        f(em, 'init_velocity_random', 0.0)
        f(em, 'emitter_velocity', 0.0)
        f(em, 'dispersion_angle', 0.0)
        f(em, 'gravity', [0.0, 0.0, 0.0])
        f(em, 'air_resistance', 1.0)
        f(em, 'scale', list(spec['size']))
        f(em, 'scale_random', [0.0, 0.0])
        f(em, 'scale_init_ratio', [1.0, 1.0])
        f(em, 'scale_diff21', [0.0, 0.0])
        f(em, 'scale_diff32', [0.0, 0.0])
        for r in ('rotation_init', 'rotation_random', 'rotation_velocity', 'rotation_velocity_random'):
            f(em, r, [0.0, 0.0, 0.0])
        em[0x2FC:0x2FF] = b'\0\0\0'                    # no random rotation direction
        f(em, 'alpha_init', 1.0)
        f(em, 'alpha_diff21', 0.0)
        f(em, 'alpha_diff32', 0.0)
        f(em, 'color0_type', 0)
        f(em, 'color0_keys', [1.0] * 32)
        f(em, 'color_scale', spec.get('brightness', 1.0))
        f(em, 'camera_offset', 0.0)
        struct.pack_into('>I', em, 0x310, 0)           # follow type 0: on its emitter's live matrices
        # a loop goes at once when ended (or fades over spec fade frames); a one-shot plays out
        struct.pack_into('>f', em, 0x82C, (1.0 / spec['fade'] if spec.get('fade') else 1.0) if loop else 0.0)
        em[0x2F9] = 1                                  # no emission while ending
        p.set_emitter_srt(em, translation=(spec['offset'][0], spec['offset'][1], 0.0))
        t = run['table']
        VP.set_flipbook(em, MODE, {'uv_div': [nx, ny]},
                        {'num': len(t), 'num_random': 1, 'table': t + [0] * (TABLE - len(t)), 'frequency': k})
        if ring:
            ring_fields(p, em, ring, ring['flame'])
        VP.set_uv_anim(em, None)
        VP.set_inv_rand(em, 0, (False, False))
        out.append(em)
    return out


def build(in_dir, kirby_path, fx_pkg, out_dir, sets=None, burn2=True):
    """the new .ptcl / .efc in out_dir: {set name: effect id}"""
    global FX_PKG
    FX_PKG = fx_pkg
    p = P.Ptcl(open(os.path.join(in_dir, 'gekkouga.010d0000.ptcl'), 'rb').read())
    e = EFC.Efc(open(os.path.join(in_dir, 'gekkouga.010d0000.efc'), 'rb').read())
    assert len(e.entries) == VANILLA_ENTRIES and len(p.sets) == 20, 'his vanilla bank'
    kirby = P.Ptcl(open(kirby_path, 'rb').read())
    tmpl = template(p, kirby)
    ids = {}
    for name, spec in (sets if sets is not None else all_sets(burn2)):
        si = p.new_set(name, ring_emitters(p, tmpl, name, spec) if 'left' in spec else flip_emitters(p, tmpl, name, spec))
        ids[name] = (BANK << 16) | e.add(si + 1, None, 0x100)
    errs = p.validate()
    assert not errs, errs
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, 'gekkouga.010d0000.ptcl'), 'wb').write(p.build())
    open(os.path.join(out_dir, 'gekkouga.010d0000.efc'), 'wb').write(e.build())
    return ids


def ids_of(sets):
    """the ids build gives these sets (vanilla entries first, then one entry a set in order)"""
    return {name: (BANK << 16) | (VANILLA_ENTRIES + i) for i, (name, _s) in enumerate(sets)}


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) != 4:
        sys.exit(__doc__)
    for k, v in build(*a).items():
        print('0x%08X %s' % (v, k))
