#!/usr/bin/env python3
"""Offline effect renderer: a move's effects as Ultimate draws them (its .eff, its effect script) beside
the converted ones (the port's .ptcl / .efc, its translated effect.bin), frame by frame, so a port's
effects can be checked before a test in game (Squirtle v6: down smash splashing up, the dash's droplets
flying high, ripples standing upright).

  python3 tools/fx_render.py NAME MOVE [MOVE ...] --out DIR [--frames A-B] [--every N] [--scale PX]
  python3 tools/fx_render.py NAME --effect pzenigame_dash [--call x,y,z,rx,ry,rz,size] --out DIR

NAME: the port (fighters/NAME/port.json, port_sources.json: its Ultimate .eff and script dump);
--pkg DIR: the package's fighter folder (default: the plan's build dir, --build DIR). MOVE: the script
name (Ultimate's file / Smash 4's script: AttackLw4 / attacklw4). Writes DIR/<move>.png: a column per
game (Ultimate left, ours right), a row per frame shown.

Stage 1 (this): the particles' motion and shape on the CPU, each game's emitter data as that game
reads it (emission, the emitter's shape and transform, velocity, gravity, air resistance, life, scale /
alpha / colour over life, rotation, particle type, mesh), drawn with their own textures (the first
flipbook cell), a plain colour x texture combine, alpha or add blending, no bloom. A side view of the
fighter's "top" frame (forward = right, up = up), 5-unit grid, the ground at 0. The fighter doesn't
move and bones other than top are taken at top (noted). Stage 2: the converted particles through
their own vertex / pixel programs (tools/latte_interp.py).

What each game does here is what we know of it: Ultimate's side is the reference only as far as that
goes. Check it once against Ultimate footage (the user's recordings) when a rule is new; the converted
side reads the same fields the game does (docs/ptcl-format.md).
"""
import argparse
import json
import math
import os
import re
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import acmd  # noqa: E402
import efc  # noqa: E402
import ptcl  # noqa: E402
import vfxb  # noqa: E402

NONE64 = 0xFFFFFFFFFFFFFFFF
FOREVER = 0x7FFFFFFF
BG = np.array([0.62, 0.62, 0.64])


# ------------------------------------------------------------------ maths
def rot_xyz(r, order='zyx'):
    """'zyx': R = Rz Ry Rx (radians: eft's emitter matrix order, and the scripts' XRot / YRot / ZRot);
    'xyz': R = Rx Ry Rz (eft2's emitter rotation: vfxb_to_ptcl.eft_rotation)"""
    cx, cy, cz = np.cos(r)
    sx, sy, sz = np.sin(r)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rx @ ry @ rz if order == 'xyz' else rz @ ry @ rx


def anim_value(keys, loop, frame):
    """an emitter key animation [(frame, value)] at this emitter frame (linear; held past the ends)"""
    fr = [k[0] for k in keys]
    if loop and fr[-1] > 0:
        frame = frame % fr[-1]
    return float(np.interp(frame, fr, [k[1] for k in keys]))


def three(v0, v1, v2, s1, s2, t):
    """eft's 3-key ramp at t (0-1): v0 -> v1 at s1, held to s2, -> v2 at 1"""
    if t < s1:
        return v0 + (v1 - v0) * (t / s1 if s1 > 0 else 1)
    if t <= s2:
        return v1
    return v1 + (v2 - v1) * ((t - s2) / (1 - s2) if s2 < 1 else 0)


def shape_point(rng, vt, radius, sweep=None):
    """a point of an emitter volume (eft / eft2 share the numbers for these): 0 point, 1 circle,
    2 circle (even), 3 / 4 filled circle, 5 / 6 sphere, 7 / 8 filled sphere ... the rest as a sphere"""
    r = np.asarray(radius, float)
    if vt == 0:
        return np.zeros(3)
    if vt in (1, 2, 3, 4):           # circle in XZ
        a = rng.uniform(0, 2 * math.pi)
        k = 1.0 if vt in (1, 2) else math.sqrt(rng.uniform())
        return np.array([math.cos(a) * r[0] * k, 0.0, math.sin(a) * r[2] * k])
    d = rng.normal(size=3)
    d /= np.linalg.norm(d) or 1
    k = 1.0 if vt in (5, 6) else rng.uniform() ** (1 / 3)
    return d * r * k


def spread(rng, d, angle_deg):
    """direction d turned at random within angle_deg"""
    if not angle_deg:
        return d
    a = math.radians(angle_deg) * rng.uniform()
    b = rng.uniform(0, 2 * math.pi)
    u = np.cross(d, [0, 1, 0] if abs(d[1]) < 0.9 else [1, 0, 0])
    u /= np.linalg.norm(u)
    w = np.cross(d, u)
    return d * math.cos(a) + (u * math.cos(b) + w * math.sin(b)) * math.sin(a)


# ------------------------------------------------------------------ particles
class Emitter:
    """what both games' emitters come down to here; filled by ult_emitter / s4_emitter"""
    name = ''
    start = 0                 # frames after the call
    duration = 1              # emitting frames (FOREVER: while the effect lives)
    interval = 0
    rate = 1.0
    life = 10
    srt = ((1, 1, 1), (0, 0, 0), (0, 0, 0))     # emitter scale, rotation (radians), translation
    rot_order = 'zyx'
    anims = {}                # key-animation target (ptcl.KEYA_TARGETS) -> (keys [(frame, value)], loop)
    volume = (0, (0, 0, 0))
    all_dir = 0.0
    dir_speed = 0.0
    direction = np.array([0.0, 1.0, 0.0])
    dispersion = 0.0
    vel_random = 0.0
    gravity = np.zeros(3)
    world_gravity = False     # gravity straight down in top's frame, not turned with the emitter
    air = 1.0
    size = (1.0, 1.0)
    size_random = 0.0
    size_curve = None         # t -> (sx, sy) multipliers
    alpha_curve = None        # t -> alpha
    colour_curve = None       # t -> rgb
    colour1_curve = None
    combine = 1               # 0 colour, 1 colour x tex, 2 c0 x tex + c1 x (1 - tex)
    alpha_from_red = False
    rot_init = np.zeros(3)
    rot_rand = np.zeros(3)
    rot_add = np.zeros(3)
    ptype = 0                 # 0 billboard, 1 plate XY, 2 plate XZ, 3 directional, 4 directional polygon, 8 Y billboard
    mesh = None               # (pos [n, 3], uv [n, 2], idx [m])
    tex = None                # [h, w, 4] 0-1
    blend = 0                 # 0 alpha, 1 add
    follow = True
    notes = ()


def simulate(em, call, frames, seed=1):
    """{frame: [(pos, vel, age_t, size, rot, alpha, rgb)]} of one emitter played by a script call
    (call: (frame, matrix effect -> top, size))"""
    rng = np.random.default_rng(seed)
    f0, cm, csize = call
    out = {f: [] for f in frames}
    live = []
    carry = 0.0
    last = max(frames)
    for f in range(f0, last + 1):
        k = f - f0 - em.start
        m = cm @ emitter_matrix(em, f - f0)
        lin = m[:3, :3]
        a = lambda t, d, k=f - f0: anim_value(*em.anims[t], k) if t in em.anims else d    # noqa: E731
        if 0 <= k < em.duration and k % (em.interval + 1) == 0:
            carry += a(0, em.rate)
            while carry >= 1 - 1e-6:
                carry -= 1
                p = shape_point(rng, *em.volume)
                d = spread(rng, em.direction / (np.linalg.norm(em.direction) or 1), em.dispersion)
                outward = p / np.linalg.norm(p) if np.linalg.norm(p) > 1e-6 else spread(rng, np.array([0, 1.0, 0]), 180)
                v = outward * a(15, em.all_dir) + d * a(16, em.dir_speed)
                v = v * (1 - em.vel_random * rng.uniform())
                sr = 1 - em.size_random * rng.uniform()
                sa = (a(17, 1.0), a(18, 1.0))
                rot = em.rot_init + em.rot_rand * rng.uniform(-1, 1, 3)
                live.append({'p': (m @ np.append(p, 1))[:3], 'v': lin @ v, 'age': 0, 'sr': sr, 'rot': rot,
                             'sa': sa, 'lin': lin})
        keep = []
        for q in live:
            if q['age'] >= em.life:
                continue
            t = q['age'] / max(em.life, 1)
            if f in out:
                sx, sy = em.size_curve(t) if em.size_curve else (1, 1)
                rgb = em.colour_curve(t) if em.colour_curve else np.ones(3)
                rgb1 = em.colour1_curve(t) if em.colour1_curve else None
                out[f].append((q['p'].copy(), q['v'].copy(), t, (em.size[0] * sx * q['sr'] * q['sa'][0] * csize,
                                                                    em.size[1] * sy * q['sr'] * q['sa'][1] * csize),
                               q['rot'] + em.rot_add * q['age'], em.alpha_curve(t) if em.alpha_curve else 1.0,
                               rgb, rgb1))
            g = em.gravity if em.world_gravity else q['lin'] @ em.gravity / max(np.linalg.norm(q['lin'][:, 1]), 1e-6)
            q['v'] = q['v'] * em.air + g * csize
            q['p'] = q['p'] + q['v']
            q['age'] += 1
            keep.append(q)
        live = keep
    return out


def emitter_matrix(em, frame):
    """emitter -> effect at this frame of the effect (its SRT, key animations 2 - 10 over it)"""
    s, r, t = (list(v) for v in em.srt)
    for i in range(3):
        if 2 + i in em.anims:
            s[i] = anim_value(*em.anims[2 + i], frame)
        if 5 + i in em.anims:
            r[i] = anim_value(*em.anims[5 + i], frame)
        if 8 + i in em.anims:
            t[i] = anim_value(*em.anims[8 + i], frame)
    m = np.eye(4)
    m[:3, :3] = rot_xyz(np.array(r, float), em.rot_order) @ np.diag(s)
    m[:3, 3] = t
    return m


# ------------------------------------------------------------------ drawing
class Canvas:
    def __init__(self, x0, x1, y0, y1, ppu):
        self.x0, self.y1, self.ppu = x0, y1, ppu
        self.w, self.h = int((x1 - x0) * ppu), int((y1 - y0) * ppu)
        self.rgb = np.tile(BG, (self.h, self.w, 1))
        for gx in range(int(math.ceil(x0 / 5)) * 5, int(x1) + 1, 5):
            self.rgb[:, self.px(gx, 0)[0].clip(0, self.w - 1)] = BG * (0.8 if gx else 0.55)
        for gy in range(int(math.ceil(y0 / 5)) * 5, int(y1) + 1, 5):
            self.rgb[self.px(0, gy)[1].clip(0, self.h - 1), :] = BG * (0.8 if gy else 0.4)

    def px(self, x, y):
        return (np.asarray((np.asarray(x) - self.x0) * self.ppu).astype(int),
                np.asarray((self.y1 - np.asarray(y)) * self.ppu).astype(int))

    def tri(self, P, UV, tex, rgb, rgb1, alpha, combine, alpha_red, blend):
        """one triangle: P [3, 2] world (screen x = top's Z, y = Y), UV [3, 2]"""
        X = (P[:, 0] - self.x0) * self.ppu
        Y = (self.y1 - P[:, 1]) * self.ppu
        xa, xb = max(int(X.min()), 0), min(int(X.max()) + 1, self.w)
        ya, yb = max(int(Y.min()), 0), min(int(Y.max()) + 1, self.h)
        if xa >= xb or ya >= yb:
            return
        den = (Y[1] - Y[2]) * (X[0] - X[2]) + (X[2] - X[1]) * (Y[0] - Y[2])
        if abs(den) < 1e-9:
            return
        gx, gy = np.meshgrid(np.arange(xa, xb) + 0.5, np.arange(ya, yb) + 0.5)
        l0 = ((Y[1] - Y[2]) * (gx - X[2]) + (X[2] - X[1]) * (gy - Y[2])) / den
        l1 = ((Y[2] - Y[0]) * (gx - X[2]) + (X[0] - X[2]) * (gy - Y[2])) / den
        l2 = 1 - l0 - l1
        inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
        if not inside.any():
            return
        u = (l0 * UV[0, 0] + l1 * UV[1, 0] + l2 * UV[2, 0])[inside]
        v = (l0 * UV[0, 1] + l1 * UV[1, 1] + l2 * UV[2, 1])[inside]
        if tex is None:
            t = np.ones((len(u), 4))
        else:
            th, tw = tex.shape[:2]
            t = tex[((v % 1) * th).astype(int).clip(0, th - 1), ((u % 1) * tw).astype(int).clip(0, tw - 1)]
        if combine == 0:
            c = np.broadcast_to(rgb, (len(u), 3))
        elif combine == 2 and rgb1 is not None:
            c = rgb * t[:, :3] + rgb1 * (1 - t[:, :3])
        else:
            c = rgb * t[:, :3]
        a = alpha * (t[:, 0] if alpha_red else t[:, 3])
        a = np.clip(a, 0, 1)[:, None]
        c = np.clip(c, 0, 1)
        ys, xs = np.nonzero(inside)
        ys, xs = ys + ya, xs + xa
        dst = self.rgb[ys, xs]
        self.rgb[ys, xs] = dst + c * a if blend == 1 else dst * (1 - a) + c * a

    def image(self):
        return (np.clip(self.rgb, 0, 1) * 255 + 0.5).astype(np.uint8)


QUAD = (np.array([[-0.5, 0.5, 0], [0.5, 0.5, 0], [0.5, -0.5, 0], [-0.5, -0.5, 0]]),
        np.array([[0, 0], [1, 0], [1, 1], [0, 1.0]]), np.array([0, 1, 2, 0, 2, 3]))
# top's axes on screen: Z right, Y up; X away from the camera (depth)
TO_SCREEN = np.array([[0, 0, 1.0], [0, 1.0, 0], [-1.0, 0, 0]])


def basis(em, vel, cm):
    """the particle's frame (3x3, columns its X Y Z in top's frame) before its own rotation"""
    if em.ptype in (0, 7):            # facing the camera: its X right, Y up, Z toward the camera
        return np.array([[0, 0, -1.0], [0, 1.0, 0], [1.0, 0, 0]]).T
    if em.ptype == 8:                 # upright, turned to the camera about Y
        return np.array([[0, 0, -1.0], [0, 1.0, 0], [1.0, 0, 0]]).T
    frame = (cm @ emitter_matrix(em, 0))[:3, :3]
    frame = frame / np.maximum(np.linalg.norm(frame, axis=0), 1e-9)
    if em.ptype == 1:
        return frame
    if em.ptype == 2:                 # XZ plate: the quad's Y along the emitter's Z
        return frame @ np.array([[1, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])
    s = np.linalg.norm(vel)
    if em.ptype in (3, 4) and s > 1e-4:
        y = vel / s
        x = np.cross(y, frame[:, 2])
        if np.linalg.norm(x) < 1e-6:
            x = np.cross(y, [1.0, 0, 0])
        x /= np.linalg.norm(x)
        return np.stack([x, y, np.cross(x, y)], 1)
    return frame


def draw(canvas, em, parts, cm):
    pos, uv, idx = em.mesh if em.mesh is not None else QUAD
    items = []
    for p, v, t, (sx, sy), rot, alpha, rgb, rgb1 in parts:
        b = basis(em, v, cm) @ rot_xyz(rot)
        w = (b @ (pos * np.array([sx, sy, sx])).T).T + p
        items.append((-(w[:, 0].mean()), w, alpha, rgb, rgb1))
    for _d, w, alpha, rgb, rgb1 in sorted(items, key=lambda x: x[0]):
        s = w @ TO_SCREEN.T
        for k in range(0, len(idx) - 2, 3):
            tri = idx[k:k + 3]
            canvas.tri(s[tri, :2], uv[tri, :2], em.tex, rgb, rgb1, alpha, em.combine, em.alpha_from_red, em.blend)


# ------------------------------------------------------------------ Ultimate (eft2)
def ult_anims(e):
    """Ultimate's emitter animations (VFXB EA** sections: vfxb_to_ptcl.EMITTER_ANIMS) by eft target,
    in eft2's own terms (rotation in radians, eft2's order; EASL the particle scale over its base)"""
    import vfxb_to_ptcl as V
    out = {}
    for sec, targets in V.EMITTER_ANIMS.items():
        raw = bytes.fromhex(e['subsections'].get(sec, ''))
        if len(raw) < 12:
            continue
        on, loop, _pad, nk, _z = struct.unpack_from('<BBHII', raw, 0)
        keys = [struct.unpack_from('<4f', raw, 12 + 16 * k) for k in range(nk)]
        if not on or not keys:
            continue
        for i, t in enumerate(targets):
            vals = [k[i] for k in keys]
            if sec == 'EAER':
                vals = [math.radians(v) for v in vals]
            elif sec == 'EASL':
                b = e['scale']['scale'][i] or 1.0
                vals = [v / b for v in vals]
            elif sec in ('EAC0', 'EAC1', 'EAA0'):
                continue
            out[t] = ([(k[3], v) for k, v in zip(keys, vals)], loop)
    return out


def ult_emitters(eff, set_index, images, names, prims):
    import vfxb_to_ptcl as V
    out = []
    for e in eff.emitters(set_index):
        em = Emitter()
        em.name = e['name']
        notes = []
        if not e['info']['is_particle_draw']:
            continue
        ems, st, pt, vel, col = e['emission'], e['static'], e['particle'], e['velocity'], e['color']
        em.start, em.interval = int(ems['start']), int(ems['interval'])
        em.duration = max(1, int(ems['duration'])) if ems['one_time'] else FOREVER
        em.rate = float(ems['rate'])
        em.life = int(pt['life']) if not pt['infinite_life'] else 600
        info = e['info']
        em.srt = (tuple(info['scale']), tuple(info['rotate']), tuple(info['trans']))
        em.rot_order = 'xyz'
        em.anims = ult_anims(e)
        sh = e['shape']
        em.volume = (sh['volume_type'], np.array(sh['volume_radius']) * np.array(sh['volume_form_scale']))
        em.all_dir, em.dir_speed = float(vel['all_direction']), float(vel['designated_dir_scale'])
        em.direction = np.array(vel['designated_dir'], float)
        em.dispersion = float(vel['diffusion_dir_angle'])
        em.vel_random = float(vel['vel_random']) / 100
        em.gravity = np.array(ems['gravity_dir'], float) * float(ems['gravity_scale'])
        em.world_gravity = bool(ems['world_gravity'])
        em.air = float(st['air_res'])
        sc = e['scale']
        em.size = (float(sc['scale'][0]), float(sc['scale'][1]))
        em.size_random = min(1.0, float(sc['scale_random'][0]) / 100)
        curve = V.keys(st['scale_anim'], st['num_scale_keys'], 2)
        em.size_curve = lambda t, c=curve: c[int(round(t * 100))]
        c0, a0 = V.track(st, col, 0)
        c1, a1 = V.track(st, col, 1)
        cs = float(st['color_scale'] or 1.0)
        rgb0 = c0 * np.array(info['color0'][:3]) * cs
        rgb1 = c1 * np.array(info['color1'][:3]) * cs
        al = a0 * info['color0'][3] * (a1 * info['color1'][3] if e['combiner']['alpha_process'] == 4 else 1)
        em.colour_curve = lambda t, c=rgb0: c[int(round(t * 100))]
        em.colour1_curve = lambda t, c=rgb1: c[int(round(t * 100))]
        em.alpha_curve = lambda t, a=al: a[int(round(t * 100))]
        cp = e['combiner']['color_process']
        em.combine = 0 if cp == 0 else 2 if cp == 2 else 1
        em.alpha_from_red = e['combiner']['alpha_process'] in (2, 3)
        em.rot_init = np.array(st['rotate_init'][:3], float)
        em.rot_rand = np.array(st['rotate_init_rand'][:3], float)
        em.rot_add = np.array(st['rotate_add'][:3], float)
        em.ptype = {5: 3, 6: 3, 7: 0}.get(pt['billboard_type'], pt['billboard_type'])
        if pt['primitive_id'] != NONE64 and pt['primitive_id'] in prims:
            pos, _n, _c, uv, idx = V.mesh(prims[pt['primitive_id']], e['tex_anim'][0]['uv_channel'])
            em.mesh = (np.asarray(pos, float) * np.array(sc['scale']) / np.array([em.size[0], em.size[1], em.size[0]]),
                       np.asarray(uv, float)[:, :2], np.asarray(idx).ravel())
        ti, smp = V.main_texture(e, names)
        if smp and smp['texture_id'] in images:
            img = V.first_cell(images[smp['texture_id']], st['tex_scroll'][ti], V.shown_cell(e, ti))
            em.tex = np.asarray(img, float) / 255
        em.blend = 1 if e['render']['blend_type'] == 1 else 0
        if e['combiner']['shader_type'] == 1:
            em.alpha_curve = lambda t: 0.0
            notes.append('refraction (not drawn)')
        em.notes = notes
        out.append(em)
    return out


# ------------------------------------------------------------------ Smash 4 (eft)
def s4_emitters(p, set_index):
    out = []
    for e in p.sets[set_index]['emitters']:
        d = e['data']
        if d is None:
            continue
        f = lambda n, d=d: p.field(d, n)    # noqa: E731
        em = Emitter()
        em.name = p.emitter_name(d)
        em.start = f('start_frame') + f('emit_start')
        em.interval = f('emit_interval')
        em.duration = f('end_frame') if f('one_time') else FOREVER
        em.rate = f('emit_rate')
        em.life = f('ptcl_life') if f('ptcl_life') != FOREVER else 600
        em.srt = (tuple(f('emitter_scale')), tuple(f('emitter_rotation')), tuple(f('emitter_translation')))
        em.anims = {a['target']: (a['keys'], a['loop']) for a in p.key_anims(d) if a['target'] < 0x1C}
        em.volume = (f('volume_type'), np.array(f('volume_radius')))
        em.all_dir, em.dir_speed = f('figure_velocity'), f('emitter_velocity')
        em.direction = np.array(f('emit_direction'), float)
        em.dispersion = f('dispersion_angle')
        em.vel_random = f('init_velocity_random')
        em.gravity = np.array(f('gravity'), float)
        em.world_gravity = bool(f('world_gravity'))
        em.air = f('air_resistance')
        em.size = tuple(f('scale'))
        em.size_random = f('scale_random')[0]
        s0 = np.array(f('scale_init_ratio'))
        s1 = s0 + np.array(f('scale_diff21'))
        s2 = s1 + np.array(f('scale_diff32'))
        ss = [v / 100 for v in f('scale_sections')]
        em.size_curve = lambda t, a=(s0, s1, s2, ss): tuple(three(a[0][k], a[1][k], a[2][k], a[3][0], a[3][1], t)
                                                              for k in range(2))
        a0 = f('alpha_init')
        a1 = a0 + f('alpha_diff21')
        a2 = a1 + f('alpha_diff32')
        em.alpha_curve = lambda t, a=(a0, a1, a2, f('alpha_section1'), f('alpha_section2')): three(*a, t)
        cs = f('color_scale')

        def colour(track):
            keys = np.array(f('color%d_keys' % track)).reshape(8, 4)[:, :3] * cs
            if f('color%d_type' % track) != 2:
                return lambda t, k=keys: k[0]
            secs = [f('color_section%d' % n)[track] / 100 for n in (1, 2, 3)]
            return lambda t, k=keys, s=secs: (k[0] if t <= s[0] else k[2] if t >= s[2] else
                                              k[0] + (k[1] - k[0]) * min(1, (t - s[0]) / max(s[1] - s[0], 1e-6))
                                              + (k[2] - k[1]) * max(0, (t - s[1]) / max(s[2] - s[1], 1e-6)))
        em.colour_curve = colour(0)
        em.colour1_curve = colour(1)
        c1 = np.array(f('color1_keys')).reshape(8, 4)[0, :3]
        em.combine = 2 if c1.max() > 0.02 else 1
        em.rot_init = np.array(f('rotation_init'))
        em.rot_rand = np.array(f('rotation_random'))
        em.rot_add = np.array(f('rotation_velocity'))
        em.ptype = f('particle_type')
        if f('primitive_index') >= 0:
            pos, _n, _c, uv, idx = p.primitive(f('primitive_index'))
            em.mesh = (np.asarray(pos, float), np.asarray(uv, float)[:, :2], np.asarray(idx).ravel())
        try:
            em.tex = np.asarray(p.decode_texture(d, 0), float) / 255
        except Exception:                       # noqa: BLE001
            em.tex = None
        em.blend = 1 if f('blend_type') == 1 else 0
        sh = p.field(d, 'shader_index')
        if struct.unpack_from('>I', bytes(p.shader_entry(sh)), 0)[0] & 0xFF in (5, 6):
            em.alpha_curve = lambda t: 0.0
            em.notes = ['distortion pass (not drawn)']
        out.append(em)
    return out


# ------------------------------------------------------------------ the scripts
EFFECT_MACROS = ('EFFECT', 'EFFECT_FOLLOW', 'EFFECT_FLIP', 'EFFECT_FOLLOW_FLIP', 'EFFECT_FOLLOW_NO_STOP',
                 'EFFECT_FOLLOW_NO_SCALE', 'EFFECT_FOLLOW_ALPHA', 'EFFECT_ALPHA', 'LANDING_EFFECT', 'FOOT_EFFECT',
                 'EFFECT_FOLLOW_FLIP_ALPHA', 'EFFECT_FLIP_ALPHA', 'EFFECT_FOLLOW_RND', 'EFFECT_FOLLOW_WORK')


def ult_calls(path, move):
    """[(frame, effect name, bone, (x, y, z), (rx, ry, rz) degrees, size)] of Ultimate's effect_<move>"""
    if not os.path.exists(path):
        return []
    text = open(path, errors='replace').read()
    m = re.search(r'unsafe extern "C" fn effect_%s\b.*?\n\}' % re.escape(move.lower()), text, re.S | re.I)
    if not m:
        m = re.search(r'fn effect_\w*\(.*?\n\}', text, re.S)
    body = m.group(0) if m else text
    frame, out = 0, []
    for line in body.splitlines():
        fm = re.search(r'\bframe\(\s*[\w.]+\s*,\s*([\d.]+)\s*\)', line)
        if fm:
            frame = max(frame, int(float(fm.group(1))))
            continue
        wm = re.search(r'\bwait\(\s*[\w.]+\s*,\s*([\d.]+)\s*\)', line)
        if wm:
            frame += int(float(wm.group(1)))
            continue
        em = re.search(r'macros::(\w+)\(agent,\s*(.*)\);', line)
        if em and em.group(1) in EFFECT_MACROS:
            names = re.findall(r'Hash40::new\("([^"]+)"\)', em.group(2))
            rest = re.sub(r'Hash40::new\("[^"]+"\)\s*,?', '', em.group(2))
            nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', rest.split('true')[0].split('false')[0])]
            if 'FLIP' in em.group(1):
                names = [names[0]] + names[2:]
            if len(names) >= 2 and len(nums) >= 7:
                out.append((frame, names[0], names[1], tuple(nums[:3]), tuple(nums[3:6]), nums[6]))
            elif len(names) >= 2 and em.group(1) in ('LANDING_EFFECT', 'FOOT_EFFECT') and len(nums) >= 7:
                out.append((frame, names[0], names[1], tuple(nums[:3]), tuple(nums[3:6]), nums[6]))
    return out


def s4_calls(effect_bin, move):
    """the same from the translated effect.bin (Graphic, Bone, X..ZRot, Size; frames from FRAME / WAIT)"""
    f = acmd.ACMDFile.load(effect_bin)
    cmds = f.scripts.get(acmd.crc(move.lower()), [])
    frame, out = 0, []
    for c in cmds:
        info = acmd.INFO.get(c.ident) or {}
        name, syn = info.get('name', ''), info.get('syntax', [])
        if name == 'FRAME':
            frame = max(frame, int(c.params[0]))
        elif name == 'WAIT':
            frame += int(c.params[0])
        elif syn[:2] == ['Graphic', 'Bone'] and 'Size' in syn:
            g = dict(zip(syn, c.params))
            out.append((frame, g['Graphic'], g['Bone'], (g.get('X', 0), g.get('Y', 0), g.get('Z', 0)),
                        (g.get('XRot', 0), g.get('YRot', 0), g.get('ZRot', 0)), g['Size']))
    return out


def call_matrix(xyz, rot_deg, size):
    m = np.eye(4)
    m[:3, :3] = rot_xyz(np.radians(rot_deg)) * size
    m[:3, 3] = xyz
    return m


# ------------------------------------------------------------------ main
def render_move(args, move, ult, s4, out_png):
    ucalls = ult_calls(os.path.join(args.dump, move + '.txt'), move)
    scalls = s4_calls(args.effect_bin, move)
    frames = list(range(args.first, args.last + 1, args.every))
    cols = []
    log = []
    for side, calls in (('Ultimate', ucalls), ('Smash 4', scalls)):
        canvases = {fr: Canvas(*args.view, args.scale) for fr in frames}
        for fr0, name, bone, xyz, rot, size in calls:
            if side == 'Ultimate':
                ems = ult.get(name)
                if ems is None:
                    log.append('%s f%d %s: not in the .eff' % (side, fr0, name))
                    continue
                if bone != 'top':
                    log.append('%s f%d %s on %s: drawn at top' % (side, fr0, name, bone))
            else:
                ems = s4.get(name)
                if ems is None:
                    log.append('%s f%d 0x%X: not in the bank' % (side, fr0, name))
                    continue
                if bone not in (0,):
                    log.append('%s f%d 0x%X on bone %d: drawn at top' % (side, fr0, name, bone))
            cm = call_matrix(xyz, rot, size)
            for k, em in enumerate(ems):
                sim = simulate(em, (fr0, cm, size), frames, seed=k + 1)
                for fr in frames:
                    if sim[fr]:
                        draw(canvases[fr], em, sim[fr], cm)
        cols.append([canvases[fr].image() for fr in frames])
        log.append('%s: %d calls' % (side, len(calls)))
    from PIL import Image, ImageDraw
    h, w = cols[0][0].shape[:2]
    sheet = Image.new('RGB', (w * 2 + 50, (h + 4) * len(frames) + 20), (40, 40, 40))
    dr = ImageDraw.Draw(sheet)
    dr.text((50, 4), 'Ultimate', fill=(255, 255, 255))
    dr.text((50 + w, 4), 'converted (Smash 4)', fill=(255, 255, 255))
    for r, fr in enumerate(frames):
        y = 20 + r * (h + 4)
        dr.text((4, y + h // 2), 'f%d' % fr, fill=(255, 255, 255))
        for c in range(2):
            sheet.paste(Image.fromarray(cols[c][r]), (50 + c * w, y))
    sheet.save(out_png)
    return log


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('name')
    ap.add_argument('moves', nargs='*')
    ap.add_argument('--out', required=True)
    ap.add_argument('--build', help='the plan\'s build dir (ultimate_port.py --out): its package is drawn')
    ap.add_argument('--frames', default='0-40')
    ap.add_argument('--every', type=int, default=4)
    ap.add_argument('--scale', type=float, default=6.0, help='pixels a unit')
    ap.add_argument('--view', default='-25,25,-6,34', help='x0,x1,y0,y1 in units (x: forward)')
    a = ap.parse_args()
    import port_sources
    src = port_sources.load()
    cfg = json.load(open(os.path.join(ROOT, 'fighters', a.name, 'port.json')))
    ult_name = cfg['ult']
    a.first, a.last = (int(v) for v in a.frames.split('-'))
    a.view = tuple(float(v) for v in a.view.split(','))
    a.dump = os.path.join(src.dump(ult_name), ult_name)
    pkg = os.path.join(a.build, a.name, 'fighter', a.name)
    a.effect_bin = os.path.join(pkg, 'script/animcmd/body/effect.bin')
    # Ultimate: name -> emitters
    eff = vfxb.Eff(src.eff(ult_name))
    images = eff.images()
    names, _ = eff.textures()
    prims = eff.primitives()
    ids = json.load(open(os.path.join(ROOT, 'fighters', a.name, '%s_effects.json' % a.name)))
    ult = {}
    for nm, si in (eff.effects or {}).items():
        ult[nm] = ult_emitters(eff, si, images, names, prims)
    common = src.find('ult_effects', 'system/common/ef_common.eff') or src.get('ef_common')
    if common:
        import ultimate_port
        ce = vfxb.Eff(common)
        cimg, (cnames, _x), cprims = ce.images(), ce.textures(), ce.primitives()
        for nm, sname in ultimate_port.common_sets(cfg['effects'].get('common', []), common).items():
            if sname:
                ult[nm] = ult_emitters(ce, ce.sets.index(sname), cimg, cnames, cprims)
    # Smash 4: id -> emitters
    edir = os.path.join(pkg, 'effect', a.name)
    p = ptcl.Ptcl(open(os.path.join(edir, '%s.010d0000.ptcl' % a.name), 'rb').read())
    ef = efc.Efc(open(os.path.join(edir, '%s.010d0000.efc' % a.name), 'rb').read())
    s4 = {}
    for nm, v in ids.items():
        if nm.startswith('_'):
            continue
        i = int(v, 0) & 0xFFFF
        if i < len(ef.entries) and ef.entries[i][1]:
            s4[int(v, 0)] = s4_emitters(p, ef.entries[i][1] - 1)
    os.makedirs(a.out, exist_ok=True)
    for move in a.moves:
        out = os.path.join(a.out, '%s.png' % move.lower())
        for line in render_move(a, move, ult, s4, out):
            print('  ' + line)
        print(out)


if __name__ == '__main__':
    main()
