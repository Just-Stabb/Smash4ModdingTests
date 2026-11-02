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

Modelled since Squirtle's effects test 4: a non-following particle keeps the emitter's frame from its
birth (an emitter turned by its key animation lays each new sheet further round); Ultimate's
directional meshes turn only about their is_rotate axes; EFFECT_OFF_KIND / Terminate_Graphic_Effect stop
an effect's emission (its particles live on); the particle rotation order is eft's (Rx Rz Ry) on both
sides unless --ult-prot-order says otherwise. Since test 10 Ultimate's emission (time and distance) is
main.bin's (docs/fx-render-eft2.md: what is exact, what is still approximate; --ult-time-emit emits
distance emitters by their rate, as eft does). Test switches for open questions about eft2: --ult-rt
(emitter translation turned by its rotation), --ult-drop (key-animation targets left out), --only
(emitters by name).

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
    """R as the product of the axis rotations in the order named, left to right (radians): 'zyx'
    R = Rz Ry Rx (eft's emitter matrix order, and the scripts' XRot / YRot / ZRot); 'xyz' R = Rx Ry Rz; 'xzy' R = Rx Rz Ry (eft's particle rotation,
    vfxb_to_ptcl.rotation_matrix)"""
    cx, cy, cz = np.cos(r)
    sx, sy, sz = np.sin(r)
    m = {'x': np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]),
         'y': np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]),
         'z': np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])}
    return m[order[0]] @ m[order[1]] @ m[order[2]]


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


def shape_point(rng, vt, radius, sweep=None, sh=None, number=0, eft=None, count=1):
    """a point of an emitter volume (eft / eft2 share the numbers for these): 0 point, 1 circle,
    2 circle (even), 3 / 4 filled circle, 5 / 6 sphere, 7 / 8 filled sphere ... the rest as a sphere.
    sh: an Ultimate emitter's shape (its circles exact, main.bin: below); number: the particle's place in
    this emission"""
    r = np.asarray(radius, float)
    if vt == 0:
        return np.zeros(3)
    if sh is not None and vt in (1, 2):
        # eft2's circles (main.bin 0x90C40 random, 0x90E20 even; the table of shapes at 0x4F48C30): the
        # angle starts at sweep_start (2 pi x U with sweep_start_random) and runs over sweep_longitude
        # CENTRED on it (- sweep / 2); the point is (sin a x radius x, 0, cos a x radius z) and the particle
        # goes out along (sin a, 0, cos a). Even: n = num_divide_circle (less 0 .. n x random % at random:
        # prim_emit_type 0; one less when the sweep isn't a full turn), particle i of an emission at
        # sweep x (i mod n) / n (type 1: a random index; 2: a running count); + surface_pos_rand x U(-1, 1)
        # (Squirtle's water_smash / water_cutter splashes: one division, start 0 -> a = -pi, all born at
        # (0, 0, -r): the engine's own records, docs/vfx-trace.md)
        sweep = float(sh['sweep_longitude'])
        start = 2 * math.pi * rng.uniform() if sh['sweep_start_random'] else float(sh['sweep_start'])
        if vt == 1:
            a = start + sweep * rng.uniform() - sweep / 2
        else:
            n = max(1, int(sh['num_divide_circle']))
            mode = int(sh['prim_emit_type'])
            if mode == 0 and sh['num_divide_circle_random']:
                n -= int(rng.uniform() * sh['num_divide_circle_random'] / 100 * n)
            if abs(sweep - 2 * math.pi) > 1e-6 and n > 1:
                n -= 1
            i = int(rng.uniform() * n) if mode == 1 else number % n
            a = start + sweep / n * i - sweep / 2 + float(sh['surface_pos_rand']) * (rng.uniform() - 0.5) * 2
        return np.array([math.sin(a) * r[0], 0.0, math.cos(a) * r[2]])
    if eft is not None and vt in (1, 2):
        # eft's circles (ptcl.py volume_sweep_param): start + U x param, or particle i of an emission of n at
        # start + i x param / n (full turn; else / (n - 1)); + surface random degrees
        start, param, rnd, surf = eft
        if rnd:
            start = 2 * math.pi * rng.uniform()
        if vt == 1:
            a = start + rng.uniform() * param
        else:
            full = abs(param - 2 * math.pi) < 1e-4
            step = 0.0 if count <= 1 else param / (count if full else count - 1)
            a = start + number * step
        a += math.radians(surf) * (rng.uniform() * 2 - 1) if surf else 0.0
        return np.array([math.sin(a) * r[0], 0.0, math.cos(a) * r[2]])
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
    interval_random = 0       # extra frames a gap, 0 .. this - 1 at random (eft2 0x88750, eft 0x04A65350)
    rate = 1.0
    rate_random = 0.0         # eft2: rate x this x U(0, 1) more particles an emission (0x8D408)
    rate_from_data = False    # eft2: volume types 5 / 6 take the data's rate, not the animated one (0x8D44C)
    life = 10
    srt = ((1, 1, 1), (0, 0, 0), (0, 0, 0))     # emitter scale, rotation (radians), translation
    rot_order = 'zyx'
    rt = False
    prot_order = 'xzy'        # the particle's own rotation (eft: Rx Rz Ry)
    anims = {}                # key-animation target (ptcl.KEYA_TARGETS) -> (keys [(frame, value)], loop)
    volume = (0, (0, 0, 0))
    shape = None              # an Ultimate emitter's shape section (shape_point: its circles exactly)
    eft_shape = None          # a ptcl emitter's circle: sweep start, param, random start, surface random
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
    dissolve = None           # Ultimate's custom shader 8: (mask [h, w], edge width, threshold curve t -> value)
    alpha_erode = None        # Ultimate's alpha_process 4: sat(sat((tex.a - alpha 0) x 4) x this gain)
    rot_init = np.zeros(3)
    rot_rand = np.zeros(3)
    rot_add = np.zeros(3)
    ptype = 0                 # 0 billboard, 1 plate XY, 2 plate XZ, 3 directional, 4 directional polygon, 8 Y billboard
    mesh = None               # (pos [n, 3], uv [n, 2], idx [m])
    mesh_frame = False        # a directional mesh kept in the emitter's frame (eft2's: Ultimate's footage)
    program = None            # stage 2: its pixel program (latte_pixel.Program), sample, consts, blend_mode
    sample = None
    consts = None
    blend_mode = 'alpha'
    tex = None                # [h, w, 4] 0-1
    blend = 0                 # 0 alpha, 1 add
    follow = True
    dist = None               # eft2's distance emission (unit, min, max, margin): simulate()
    notes = ()
    ult = None                # Ultimate's own shaders (--ult-model off): {'e', 'vfxb', 'images', 'srgb', 'prim'}
    s4 = None                 # Smash 4's own vertex programs (--s4-model off): {'p', 'd', 'sh', 'texs'}
    life_random = 0.0         # eft2: a particle's life x (1 - this x U) (the engine's birth records)
    life_random_frames = 0    # eft: life - int(U x this) (cross_f 0x04A5C8BC: mulhwu of the u32 random)


def simulate(em, call, frames, seed=1, births_only=False):
    """{frame: [(pos, vel, age_t, size, rot, alpha, rgb)]} of one emitter played by a script call
    (call: (frame, matrix effect -> top, size)); births_only: {frame: particles born} (tools/vfx_trace.py)"""
    rng = np.random.default_rng(seed)
    f0, cm, csize, off = call
    out = {f: [] for f in frames}
    live = []
    carry = 0.0
    next_emit = 0
    last = max(frames)
    for f in range(f0, last + 1):
        k = f - f0 - em.start
        m = cm @ emitter_matrix(em, f - f0)
        lin = m[:3, :3]
        a = lambda t, d, k=f - f0: anim_value(*em.anims[t], k) if t in em.anims else d    # noqa: E731
        cur = m[:3, 3].copy()
        if f == f0:
            prev = cur
        births = []                 # emitter origins (top's frame) of this frame's new particles
        if 0 <= k < em.duration and (off is None or f < off):
            if em.dist is not None:
                # eft2's distance emission (main.bin 0x8D340, run every frame of the window instead of
                # the rate): the emitter's movement this frame in its own frame (0x8E040: both positions
                # through the inverse of its current matrix, so / its scale and the call's), 0 under the
                # margin; 0 -> min (emitting where it stands), else clamped to min - max; carried, one
                # particle per unit, each laid back along prev -> cur by what is left of the carry
                unit, dmin, dmax, marg = em.dist
                move = float(np.linalg.norm(np.linalg.solve(lin, cur - prev)))
                s9 = 0.0 if move < marg else move
                if s9 == 0:
                    s9 = dmin
                elif s9 < dmin:
                    s9 = dmin
                elif s9 > dmax:
                    s9 = dmax
                carry += s9
                if unit > 0:
                    for _ in range(int(carry / unit)):
                        carry -= unit
                        births.append((cur + (prev - cur) * (carry / s9 if s9 else 0.0), 0))   # one a call
            elif k >= next_emit:
                # emitted when the gap has run out (the first on the window's first frame: the threshold
                # starts at 0, main.bin 0x874D8), then every interval + 1 (+ random) frames
                next_emit = k + em.interval + 1 + (int(rng.uniform() * em.interval_random) if em.interval_random else 0)
                carry += (em.rate if em.rate_from_data else a(0, em.rate)) + em.rate * em.rate_random * rng.uniform()
                while carry >= 1 - 1e-6:
                    carry -= 1
                    births.append((cur, len(births)))     # numbered within the emission
        prev = cur
        if births_only:
            out[f] = len(births)
            continue
        for org, number in births:
            p = shape_point(rng, *em.volume, sh=em.shape, number=number, eft=em.eft_shape, count=len(births))
            d = spread(rng, em.direction / (np.linalg.norm(em.direction) or 1), em.dispersion)
            outward = p / np.linalg.norm(p) if np.linalg.norm(p) > 1e-6 else spread(rng, np.array([0, 1.0, 0]), 180)
            v = outward * a(15, em.all_dir) + d * a(16, em.dir_speed)
            v = v * (1 - em.vel_random * rng.uniform())
            sr = 1 - em.size_random * rng.uniform()
            sa = (a(17, 1.0), a(18, 1.0))
            # eft: init + U x random (cross_f 0x04A5DAB4, U 0 - 1); eft2: init + random x (U - 1/2) (its programs)
            rot = em.rot_init + em.rot_rand * (rng.uniform(0, 1, 3) if em.s4 is not None else rng.uniform(-0.5, 0.5, 3))
            # the particle's own life: eft takes whole frames off, eft2 a fraction (its curves, dissolves and
            # death run on it: Waterfall's spikes, life 7, erode by 61% at frame 3 of a 4.9-frame life)
            plife = (em.life - int(rng.uniform() * em.life_random_frames)) if em.s4 is not None else \
                em.life * (1 - em.life_random * rng.uniform())
            born = None
            if em.s4 is not None and S4_SHADERS:
                # what eft's particle record holds (cross_f 0x04A59FC8's streams: v_inWldPos, v_inScl, v_inVec,
                # v_inRandom, v_inRot, v_inEmtMat0-2, ...): the GPU programs (those reading v_inVec) get the
                # particle as born, world position and velocity, birth time in v_inVec.w
                mb = np.zeros((3, 4))
                mb[:, :3], mb[:, 3] = lin, org
                born = {'p': lin @ p + org, 'v': lin @ v, 'pl': p.copy(), 'vl': v.copy(), 'birth': float(f - f0),
                        'random': rng.uniform(size=3),
                        'scale': (sr * sa[0] * csize, sr * sa[1] * csize), 'm': mb, 'rot0': rot.copy(),
                        'life': float(max(plife, 1))}
            if em.ult is not None and ULT_SHADERS:
                # the particle arrays as eft2 fills them at birth (vfx_trace B records: a GPU emitter's
                # arrays hold the particle as born, its vertex program works out the rest each frame):
                # emitter-local position (w: life x (1 - life_random x U)) and velocity (w: birth time),
                # scale x (1 - scale_random x U) on every axis x the EASL value, four uniforms, rotate_init
                # (is_rotate's axes; the random part is the program's, from the uniforms), the emitter's
                # matrix at birth (rows, its translation where the particle came from)
                mb = np.zeros((3, 4))
                mb[:, :3], mb[:, 3] = lin, org
                # each axis its own (main.bin 0x90738: the emitter's 3-axis scale, EMTR +0x9C0, copied to the
                # instance at 0x87CF0, x (1 - random x U); one U for all three when the X and Y randoms are
                # equal, else one an axis with the axis's own random): Z is the scale's own (up smash's wave4,
                # scale 1 / 0.5 / 1.7, given X's stood 1.7 times too low)
                r3 = np.array([sr] * 3) if em.size_rand3[0] == em.size_rand3[1] else \
                    np.array([sr] + [1 - em.size_rand3[i] * rng.uniform() for i in (1, 2)])
                born = {'pos': np.append(p, plife),
                        'vec': np.append(v, float(f - f0)),
                        'scale': np.append(np.array(em.size3) * r3 * np.array([sa[0], sa[1], a('EASLz', 1.0)]), 1.0),
                        'random': rng.uniform(size=4), 'rot': np.append(em.rot_init, 0.0), 'm': mb}
            # a non-following particle keeps the emitter's frame at its birth (eft2 follow 1, eft's
            # copies made at emission): an emitter turned by its key animation (Squirtle's down-smash
            # waves, EAER Y 89 -> -120 over 6 frames) lays each new sheet further round
            # 'd': its last frame's movement (eft2's sysLocalDiffAttr, the trace's vec2: position now - a frame
            # ago; on its birth frame the slot holds a stale value, the birth velocity here)
            live.append({'p': lin @ p + org, 'v': lin @ v, 'age': 0, 'sr': sr, 'rot': rot,
                         'sa': sa, 'lin': lin, 'born': born, 'd': lin @ v, 'life': max(plife, 1)})
        keep = []
        for q in live:
            if q['age'] >= q['life']:
                continue
            t = q['age'] / max(q['life'], 1)
            if f in out:
                sx, sy = em.size_curve(t) if em.size_curve else (1, 1)
                rgb = em.colour_curve(t) if em.colour_curve else np.ones(3)
                rgb1 = em.colour1_curve(t) if em.colour1_curve else None
                out[f].append((q['p'].copy(), q['v'].copy(), t, (em.size[0] * sx * q['sr'] * q['sa'][0] * csize,
                                                                    em.size[1] * sy * q['sr'] * q['sa'][1] * csize),
                               q['rot'] + em.rot_add * q['age'], em.alpha_curve(t) if em.alpha_curve else 1.0,
                               rgb, rgb1, q['lin'], q['born'], q['d'].copy()))
            g = em.gravity if em.world_gravity else q['lin'] @ em.gravity / max(np.linalg.norm(q['lin'][:, 1]), 1e-6)
            # moved by the velocity it had, then air and gravity (vfx_trace of down smash's splash2: born at
            # z -0.1 with v -1.965, next frame at -2.065 with v -1.965 x 0.96, gravity in it but not yet in
            # the position); eft's GPU programs give the same places (geometric sum: down smash's splash2 run
            # through its program lands on the trace's z to 0.001). Air first, as this had it, every particle
            # fell short by one air step and took its gravity a frame early
            q['p'] = q['p'] + q['v']
            q['d'] = q['v']
            q['v'] = q['v'] * em.air + g * csize
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
    rm = rot_xyz(np.array(r, float), em.rot_order)
    m[:3, :3] = rm @ np.diag(s)
    # T R S, or with em.rt the translation turned by the rotation (R T S: --ult-rt, a test)
    m[:3, 3] = rm @ np.asarray(t, float) if em.rt else t
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

    def tri(self, P, UV, tex, rgb, rgb1, alpha, combine, alpha_red, blend, VC=None, erode=None, dissolve=None):
        """one triangle: P [3, 2] world (screen x = top's Z, y = Y), UV [3, 2], VC [3, 4] a mesh's vertex
        colours (x the colour and alpha, as both games' mesh programs do)"""
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
        if erode is not None:
            a = np.clip(np.clip((t[:, 3] - alpha) * 4, 0, 1) * erode, 0, 1)
        if dissolve is not None:
            # Ultimate's custom shader 8 (vfxb_to_ptcl.DISSOLVE_SHADER): sampler 1's alpha the mask, colour
            # 1's alpha the threshold, alpha x (mask - threshold) / width over the edge
            mask, width, thr = dissolve
            mh, mw = mask.shape
            m = mask[((v % 1) * mh).astype(int).clip(0, mh - 1), ((u % 1) * mw).astype(int).clip(0, mw - 1)]
            a = a * np.clip((m - thr) / max(width, 1e-4), 0, 1)
        if VC is not None:
            vc = np.stack([l0[inside], l1[inside], l2[inside]], 1) @ np.asarray(VC, float)
            c = c * vc[:, :3]
            a = a * vc[:, 3]
        a = np.clip(a, 0, 1)[:, None]
        c = np.clip(c, 0, 1)
        ys, xs = np.nonzero(inside)
        ys, xs = ys + ya, xs + xa
        dst = self.rgb[ys, xs]
        self.rgb[ys, xs] = dst + c * a if blend == 1 else dst * (1 - a) + c * a

    def tri_program(self, P, attrs, shade, blend):
        """one triangle drawn by a pixel program (stage 2): attrs {semantic: [3, 4]} per vertex,
        interpolated over its pixels; shade(inputs {semantic: [4, n]}) -> rgba [4, n]; blend: 'premult'
        (ONE / INV_SRC_ALPHA: the premultiplied templates), 'alpha', 'add' or 'sub' (the emitter's)"""
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
        b = np.stack([l0[inside], l1[inside], l2[inside]])            # [3, n]
        inputs = {sem: (np.asarray(v, float).T @ b) for sem, v in attrs.items()}
        out = shade(inputs)
        c = np.clip(out[:3].T, 0, None)
        a = np.clip(out[3], 0, 1)[:, None]
        ys, xs = np.nonzero(inside)
        ys, xs = ys + ya, xs + xa
        dst = self.rgb[ys, xs]
        if blend == 'premult':
            self.rgb[ys, xs] = c + dst * (1 - a)
        elif blend == 'add':
            self.rgb[ys, xs] = dst + c * a
        elif blend == 'sub':
            self.rgb[ys, xs] = dst - c * a
        else:
            self.rgb[ys, xs] = dst * (1 - a) + c * a

    def image(self):
        return (np.clip(self.rgb, 0, 1) * 255 + 0.5).astype(np.uint8)


QUAD = (np.array([[-0.5, 0.5, 0], [0.5, 0.5, 0], [0.5, -0.5, 0], [-0.5, -0.5, 0]]),
        np.array([[0, 0], [1, 0], [1, 1], [0, 1.0]]), np.array([0, 1, 2, 0, 2, 3]))
# top's axes on screen: Z right, Y up; X away from the camera (depth)
XZ_PLATE = np.array([[1, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])   # a plate's Y onto the emitter's Z
TO_SCREEN = np.array([[0, 0, 1.0], [0, 1.0, 0], [-1.0, 0, 0]])
PITCH = 0.0              # --pitch: degrees the camera looks down (Smash 4's training camera ~15-20; Ultimate's side view 0)


def to_screen():
    """top frame -> screen (x forward, y up, depth): +x is away from the camera, seen higher when looking down"""
    p = math.radians(PITCH)
    return np.array([[0, 0, 1.0], [math.sin(p), math.cos(p), 0], [-math.cos(p), math.sin(p), 0]])


def basis(em, vel, cm, lin=None):
    """the particle's frame (3x3, columns its X Y Z in top's frame) before its own rotation; lin: the
    emitter's frame (call x emitter matrix) when the particle was born, else the emitter's at frame 0"""
    if em.ptype in (0, 7):            # facing the camera: its X right, Y up, Z toward the camera
        return np.array([[0, 0, -1.0], [0, 1.0, 0], [1.0, 0, 0]]).T
    if em.ptype == 8:                 # upright, turned to the camera about Y
        return np.array([[0, 0, -1.0], [0, 1.0, 0], [1.0, 0, 0]]).T
    frame = (cm @ emitter_matrix(em, 0))[:3, :3] if lin is None else np.asarray(lin, float)
    frame = frame / np.maximum(np.linalg.norm(frame, axis=0), 1e-9)
    if em.ptype == 1:
        return frame
    if em.ptype == 2:                 # XZ plate: the quad's Y along the emitter's Z
        return frame @ XZ_PLATE
    s = np.linalg.norm(vel)
    if em.ptype == 4 and s > 1e-4:
        # eft's type 4 (directional polygon), from its vertex program (cross_f; Squirtle's shader 112 before
        # test 14): Y along the particle's world motion (v_inWldPosDf), X = normalize(emitter Y x motion),
        # Z = X x motion. Not the emitter's frame: a sheet lying along its own motion stands on end
        y = vel / s
        x = np.cross(frame[:, 1], y)
        if np.linalg.norm(x) < 1e-6:
            x = frame[:, 0].copy()        # motion along the emitter's Y: the program's X is undefined
        x /= np.linalg.norm(x)
        return np.stack([x, y, np.cross(x, y)], 1)
    if em.ptype == 4 or (em.ptype == 3 and em.mesh is not None and em.mesh_frame):
        # type 4 at rest: taken as the emitter's frame (Zelda's crystals looked right; the program's own
        # basis is zero then, so the CPU must feed it something: not read). eft2's type 3 (the XY
        # polygon, Squirtle's waves: its vertex programs, variations 131 / 141) is the emitter's frame
        return frame
    if em.ptype == 3 and s > 1e-4:
        # directional: Y along the motion, turned about it to face the camera (eft's type 3; eft2's
        # stripe types 5 / 6: Squirtle's up-smash columns, XY sheets drawn edge-on before)
        y = vel / s
        p = math.radians(PITCH)
        to_cam = np.array([-math.cos(p), math.sin(p), 0.0])
        x = np.cross(y, to_cam)
        if np.linalg.norm(x) < 1e-6:
            x = np.cross(y, frame[:, 2])
        x /= np.linalg.norm(x)
        return np.stack([x, y, np.cross(x, y)], 1)
    return frame


ULT_RT = False
ULT_DROP = ()            # --ult-drop: key-animation targets left out (tests)
ULT_TIME_EMIT = False    # --ult-time-emit: distance emitters emit by their rate instead (a comparison)
ULT_PROT_ORDER = 'xzy'     # eft2's particle rotation order (--ult-prot-order)
ONLY = ''                  # --only: emitter names containing this (both sides)
HDR_RANGE = (1.0, 0.0, 0.0, 0.0)    # u_nwHdrRange (CB9 [8]): rgb x .x + .w, the game's own at run time


def _wrap(t, mode):
    """eft / eft2 wrap codes: 0 mirror, 1 repeat, 2 clamp"""
    if mode == 2:
        return np.clip(t, 0, 1 - 1e-6)
    if mode == 0:
        t = np.mod(t, 2)
        return np.clip(np.where(t > 1, 2 - t, t), 0, 1 - 1e-6)
    return np.mod(t, 1)


def sampler(textures, scales, wraps=None):
    """sample(slot, u, v) for latte_pixel: nearest texel, the slot's UV repeat and wrap (default repeat)"""
    def sample(slot, u, v):
        tex = textures[slot] if slot < len(textures) else None
        if tex is None:
            return np.ones((4, len(u)))
        sx, sy = scales[slot] if slot < len(scales) else (1, 1)
        wu, wv = wraps[slot] if wraps and slot < len(wraps) else (1, 1)
        th, tw = tex.shape[:2]
        iu = (_wrap(np.asarray(u) * sx, wu) * tw).astype(int).clip(0, tw - 1)
        iv = (_wrap(np.asarray(v) * sy, wv) * th).astype(int).clip(0, th - 1)
        return tex[iv, iu].T
    return sample


def draw(canvas, em, parts, cm):
    pos, uv, idx = em.mesh[:3] if em.mesh is not None else QUAD
    vcol = em.mesh[3] if em.mesh is not None and len(em.mesh) > 3 and em.mesh[3] is not None else None
    items = []
    for p, v, t, (sx, sy), rot, alpha, rgb, rgb1, lin, *_born in parts:
        b = basis(em, v, cm, lin)
        if em.ptype == 2:
            # an XZ plate is laid flat first, then turned (its Y the plate's normal): Squirtle's up-smash
            # ripple ring1 (is_rotate 0 1 0, a random Y turn) spins about the vertical, flat
            b = b @ XZ_PLATE.T @ rot_xyz(rot, em.prot_order) @ XZ_PLATE
        else:
            b = b @ rot_xyz(rot, em.prot_order)
        w = (b @ (pos * np.array([sx, sy, sx])).T).T + p
        items.append((-(w[:, 0].mean()), w, alpha, rgb, rgb1, t))
    for _d, w, alpha, rgb, rgb1, age in sorted(items, key=lambda x: x[0]):
        s = w @ to_screen().T
        for k in range(0, len(idx) - 2, 3):
            tri = idx[k:k + 3]
            if em.program is not None:
                # stage 2: the part's own pixel program (tools/latte_pixel.py) on its inputs
                c0 = np.append(np.asarray(rgb, float), alpha)
                c1 = np.append(np.asarray(rgb1 if rgb1 is not None else (0, 0, 0), float), 1.0)
                uvs = np.concatenate([uv[tri, :2], uv[tri, :2]], 1)
                attrs = {0: np.tile(c0, (3, 1)), 1: np.tile(c1, (3, 1)), 9: uvs, 10: uvs,
                         6: vcol[tri] if vcol is not None else np.ones((3, 4))}
                canvas.tri_program(s[tri, :2], attrs, lambda inp: em.program.run(inp, em.consts, em.sample),
                                   em.blend_mode)
            else:
                canvas.tri(s[tri, :2], uv[tri, :2], em.tex, rgb, rgb1, alpha, em.combine, em.alpha_from_red,
                           em.blend, vcol[tri] if vcol is not None else None, em.alpha_erode,
                           (em.dissolve[0], em.dissolve[1], em.dissolve[2](age)) if em.dissolve else None)


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
    srgb = {t for t, f in eff.formats().items() if f & 0xFF == 6}     # textures stored sRGB
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
        em.interval_random = max(0, int(ems['interval_random']))
        em.rate_random = max(0, int(ems['rate_random'])) / 100
        em.rate_from_data = e['shape']['volume_type'] in (5, 6)
        if ems['emit_dist_enabled'] and not ULT_TIME_EMIT:
            em.dist = tuple(float(ems[k]) for k in ('dist_unit', 'dist_min', 'dist_max', 'dist_marg'))
        em.life = int(pt['life']) if not pt['infinite_life'] else 600
        info = e['info']
        em.srt = (tuple(info['scale']), tuple(info['rotate']), tuple(info['trans']))
        em.rot_order = 'zyx'          # eft2 turns an emitter X first too (vfxb_to_ptcl.eft_rotation)
        em.prot_order = ULT_PROT_ORDER
        em.rt = ULT_RT
        em.anims = {k: v for k, v in ult_anims(e).items() if k not in ULT_DROP}
        sh = e['shape']
        em.volume = (sh['volume_type'], np.array(sh['volume_radius']) * np.array(sh['volume_form_scale']))
        em.shape = sh
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
        em.size3 = tuple(float(v) for v in sc['scale'])
        em.size_rand3 = tuple(min(1.0, float(v) / 100) for v in sc['scale_random'])
        easl = em.anims.get(17)
        raw = bytes.fromhex(e['subsections'].get('EASL', ''))
        if easl is not None and len(raw) >= 12:
            # EASL's Z (vfxb_to_ptcl.EMITTER_ANIMS takes X / Y only, eft's particle scale has two axes)
            nk = struct.unpack_from('<I', raw, 4)[0]
            zb = em.size3[2] or 1.0
            em.anims['EASLz'] = ([(k[3], k[2] / zb) for k in (struct.unpack_from('<4f', raw, 12 + 16 * i)
                                                               for i in range(nk))], easl[1])
        curve = V.keys(st['scale_anim'], st['num_scale_keys'], 2)
        em.size_curve = lambda t, c=curve: c[int(round(t * 100))]
        c0, a0 = V.track(st, col, 0)
        c1, a1 = V.track(st, col, 1)
        cs = float(st['color_scale'] or 1.0)
        rgb0 = c0 * np.array(info['color0'][:3]) * cs
        rgb1 = c1 * np.array(info['color1'][:3]) * cs
        al = a0 * info['color0'][3]
        if e['combiner']['alpha_process'] == 4:
            em.alpha_erode = float(np.mean(a1 * info['color1'][3]))
        if V.display_space(e):
            # Ultimate draws an alpha-blended part in linear light and encodes the frame for the screen at
            # the end; drawn here on a display-space canvas, its colours are shown encoded (the converter's
            # LINEAR_DISPLAY rule, vfxb_to_ptcl.display): without it the water was a deep blue where
            # Ultimate's (native clips) is a pale cyan-white
            rgb0, rgb1 = V.display(np.clip(rgb0, 0, None)), V.display(np.clip(rgb1, 0, None))
        em.colour_curve = lambda t, c=rgb0: c[int(round(t * 100))]
        em.colour1_curve = lambda t, c=rgb1: c[int(round(t * 100))]
        em.alpha_curve = lambda t, a=al: a[int(round(t * 100))]
        cp = e['combiner']['color_process']
        em.combine = 0 if cp == 0 else 2 if cp == 2 else 1
        em.alpha_from_red = e['combiner']['alpha_process'] in (2, 3)
        em.rot_init = np.array(st['rotate_init'][:3], float)
        em.rot_rand = np.array(st['rotate_init_rand'][:3], float)
        em.rot_add = np.array(st['rotate_add'][:3], float)
        if not all(pt['is_rotate']):
            # a particle turns only about the axes its is_rotate enables (main.bin 0x8B8A0: vfxb_to_ptcl)
            on = np.array([float(bool(v)) for v in pt['is_rotate'][:3]])
            em.rot_init, em.rot_rand, em.rot_add = em.rot_init * on, em.rot_rand * on, em.rot_add * on
        em.ptype = {4: 2, 5: 3, 6: 3, 7: 0}.get(pt['billboard_type'], pt['billboard_type'])   # vfxb_to_ptcl.TYPES
        # a type-3 directional mesh keeps the emitter's frame (Squirtle's down-smash waves, footage); the
        # stripe types 5 / 6 face the camera about their motion
        em.mesh_frame = pt['billboard_type'] == 3
        if pt['primitive_id'] != NONE64 and pt['primitive_id'] in prims:
            pos, _n, col, uv, idx = V.mesh(prims[pt['primitive_id']], e['tex_anim'][0]['uv_channel'])
            em.mesh = (np.asarray(pos, float) * np.array(sc['scale']) / np.array([em.size[0], em.size[1], em.size[0]]),
                       np.asarray(uv, float)[:, :2], np.asarray(idx).ravel(),
                       None if col is None else np.asarray(col, float))
        ti, smp = V.main_texture(e, names)
        if smp and smp['texture_id'] in images:
            img = V.first_cell(images[smp['texture_id']], st['tex_scroll'][ti], V.shown_cell(e, ti))
            em.tex = np.asarray(img, float) / 255
            if V.display_space(e) and smp['texture_id'] not in srgb:
                em.tex[..., :3] = em.tex[..., :3] ** V.DISPLAY_GAMMA     # a linear (UNORM) texture as shown
        em.blend = 1 if e['render']['blend_type'] == 1 else 0
        if e['shader']['custom_shader_index'] == V.DISSOLVE_SHADER and 'CSDP' in e['subsections']:
            s1 = e['sampler'][1]
            if s1['texture_id'] in images:
                width = struct.unpack('<f', bytes.fromhex(e['subsections']['CSDP'][:8]))[0]
                thr = V.track(st, e['color'], 1)[1] * info['color1'][3]
                mask = np.asarray(V.first_cell(images[s1['texture_id']], st['tex_scroll'][1], V.shown_cell(e, 1)),
                                  float)[..., 3] / 255
                em.dissolve = (mask, width, lambda t, c=thr: float(c[int(round(t * 100))]))
        if e['combiner']['shader_type'] == 1:
            em.alpha_curve = lambda t: 0.0
            notes.append('refraction (not drawn)')
        em.life_random = max(0, int(pt['life_random'])) / 100
        if ULT_SHADERS and not e['combiner']['shader_type'] == 1:
            em.ult = {'e': e, 'vfxb': eff.vfxb, 'images': images, 'srgb': srgb,
                      'prim': prims.get(pt['primitive_id']) if pt['primitive_id'] != NONE64 else None}
        em.notes = notes
        out.append(em)
    return out


# ------------------------------------------------------------------ Ultimate's own shaders
ULT_SHADERS = True       # --ult-model: Ultimate's side drawn by fx_render's reimplementation instead
_programs = {}


def ult_programs(em):
    """(vertex, pixel) mx_exec.Program of an Ultimate emitter, or None when they can't be run"""
    import mx_exec
    idx = em.ult['e']['shader']['shader_index']
    key = (id(em.ult['vfxb']), idx)
    if key not in _programs:
        try:
            _programs[key] = (mx_exec.Program(em.ult['vfxb'], idx, 'vs'), mx_exec.Program(em.ult['vfxb'], idx, 'ps'))
        except Exception as ex:          # noqa: BLE001 (a program the translator or the shim can't take)
            print('  %s: shader variation %d not run (%s)' % (em.name, idx, str(ex).splitlines()[0][:120]))
            _programs[key] = None
    return _programs[key]


def srgb_to_linear(x):
    x = np.asarray(x, np.float32)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(np.float32)


def view_block(canvas):
    """eft2's sysViewUniformBlock (c8) for this canvas: viewMat 0-15, projMat 16-31, vpMat 32-47 (world ->
    canvas pixels: gl_Position.xy, w 1), bldMat 48-59 (view -> world: billboards face the camera), eyeVec
    64, eyePos 68, viewParam 72 (near, far). The view is to_screen(): x right, y up, z toward the eye"""
    S = to_screen()
    v = np.zeros(80, np.float32)
    view = np.eye(4)
    view[:3, :3] = S
    v[0:16] = view.ravel()
    v[16:32] = np.eye(4).ravel()
    vp = np.zeros((4, 4))
    vp[0, :3], vp[0, 3] = canvas.ppu * S[0], -canvas.x0 * canvas.ppu
    vp[1, :3], vp[1, 3] = -canvas.ppu * S[1], canvas.y1 * canvas.ppu
    vp[2, :3], vp[3, 3] = S[2], 1.0
    v[32:48] = vp.ravel()
    bld = np.zeros((3, 4))
    bld[:, :3] = S.T
    v[48:60] = bld.ravel()
    v[64:67] = S.T @ np.array([0, 0, 1.0])
    v[68:71] = S.T @ np.array([0, 0, 1000.0])
    v[72:76] = (1.0, 10000.0, 1.0 * 10000.0, 10000.0 - 1.0)
    return v


def draw_ult(canvas, em, parts, mnow, time, csize):
    """one Ultimate emitter's live particles drawn by its own vertex and pixel programs (tools/mx_exec.py),
    blended in linear light into the canvas (Ultimate encodes its finished frame for display)"""
    progs = ult_programs(em)
    if progs is None:
        return False
    vs, ps = progs
    e = em.ult['e']
    live = [q for q in parts if len(q) > 9 and q[9] is not None]
    born = [q[9] for q in live]
    if not born:
        return True
    if e['info']['calc_type'] == 0:
        # eft2's calc type 0 is the CPU's: it moves the particle and rewrites its position / velocity arrays
        # every frame (the trace's per-frame records move; the vertex programs, e.g. down smash's splash1,
        # read no velocity at all): the particle's current place and velocity in its birth frame, not the
        # birth values (fed those, every CPU particle stood where it was born: the spray stayed low)
        cur = []
        for q, b in zip(live, born):
            lin, org = b['m'][:, :3], b['m'][:, 3]
            c = dict(b)
            c['pos'] = np.append(np.linalg.solve(lin, q[0] - org), b['pos'][3])
            c['vec'] = np.append(np.linalg.solve(lin, q[1]), b['vec'][3])
            c['diff'] = np.append(np.linalg.solve(lin, q[10]), 0.0)
            cur.append(c)
        born = cur
    import vfxb_to_ptcl as V
    if em.ult['prim'] is not None:
        pos, _n, col, uv, idx = V.mesh(em.ult['prim'], 0)
        pos, uv, idx = np.asarray(pos, np.float32), np.asarray(uv, np.float32), np.asarray(idx).ravel()
        col = np.ones((len(pos), 4), np.float32) if col is None else np.asarray(col, np.float32)
    else:
        pos, uv2, idx = QUAD
        uv = np.concatenate([uv2, uv2], 1).astype(np.float32)
        col = np.ones((4, 4), np.float32)
    nv = len(pos)
    A = np.zeros((len(born), nv, 16, 4), np.float32)
    slot = vs.inputs
    if 'sysPosAttr' in slot:
        A[:, :, slot['sysPosAttr'], :3], A[:, :, slot['sysPosAttr'], 3] = pos, 1.0
    if 'sysTexCoordAttr' in slot:
        A[:, :, slot['sysTexCoordAttr'], :uv.shape[1]] = uv[:, :4]
    if 'sysVertexColor0Attr' in slot:
        A[:, :, slot['sysVertexColor0Attr']] = col
    for name, key in (('sysLocalPosAttr', 'pos'), ('sysLocalVecAttr', 'vec'), ('sysScaleAttr', 'scale'),
                      ('sysRandomAttr', 'random'), ('sysInitRotateAttr', 'rot'), ('sysLocalDiffAttr', 'diff')):
        # sysLocalDiffAttr: the directional types' (5 / 6) axis, the particle's last movement (left 0, up
        # smash's rising columns lay flat)
        if name in slot and all(key in b for b in born):
            A[:, :, slot[name]] = np.array([b[key] for b in born], np.float32)[:, None]
    for r, name in enumerate(('sysEmtMat0Attr', 'sysEmtMat1Attr', 'sysEmtMat2Attr')):
        if name in slot:
            A[:, :, slot[name]] = np.array([b['m'][r] for b in born], np.float32)[:, None]
    info = e['info']
    c10 = np.zeros(48, np.float32)
    c10[0:4], c10[4:8] = info['color0'], info['color1']
    # c10[8] the emitter's time after this frame's step (main.bin 0x8F244: instance +0x44, which the update
    # 0x8DC80 advances at its end, 0x8E44C, after emitting and moving the particles; drawing comes after):
    # time - birth is 1 on a particle's birth frame. c10[11] the step
    c10[8], c10[11], c10[12], c10[13:16] = time + 1.0, 1.0, 1.0, csize
    c10[16:28] = mnow[:3, :4].ravel()
    rt = mnow[:3, :4].copy()
    rt[:, :3] /= np.maximum(np.linalg.norm(rt[:, :3], axis=0), 1e-9)
    c10[32:44] = rt.ravel()
    c16 = np.zeros(32, np.float32)
    c16[[0, 4, 5, 6, 8, 10, 18]] = 1.0          # the game's own per-effect block: colour / alpha x 1, no depth shift
    csdp = bytes.fromhex(e['subsections'].get('CSDP', ''))
    import eft2_resolve
    cbs = {8: view_block(canvas), 9: np.frombuffer(eft2_resolve.static_block(e), np.uint32), 10: c10, 16: c16,
           13: np.frombuffer(csdp[:len(csdp) // 4 * 4], np.uint32) if csdp else np.zeros(4, np.uint32)}
    gp, out = vs.run(A.reshape(-1, 16, 4), cbs)
    gp, out = gp.reshape(len(born), nv, 4), out.reshape(len(born), nv, -1, 4)
    # far particles first (as fx_render's own drawing); a particle's triangles in index order
    order = np.argsort(gp[:, :, 2].mean(1))
    tri = idx[:len(idx) // 3 * 3].reshape(-1, 3)
    vpos = np.concatenate([gp[k][tri] for k in order])
    vout = np.concatenate([out[k][tri] for k in order])
    wrap = {0: 1, 1: 0, 2: 2}                     # eft2 0 mirror, 1 repeat, 2 clamp -> mx_exec's
    tex = {}
    for name, unit in ps.samplers.items():
        k = int(name[-1])
        smp = e['sampler'][k]
        img = em.ult['images'].get(smp['texture_id'])
        if img is None:
            continue
        rgba = np.asarray(img, np.float32) / 255
        if smp['texture_id'] in em.ult['srgb']:
            rgba[..., :3] = srgb_to_linear(rgba[..., :3])
        tex[unit] = (rgba, wrap.get(smp['wrap_u'], 0), wrap.get(smp['wrap_v'], 0))
    lin = (np.clip(canvas.rgb, 0, None) ** (1 / V.DISPLAY_GAMMA)).astype(np.float32)
    ps.draw(vpos, vout, cbs, tex, lin, {1: 1, 2: 2}.get(e['render']['blend_type'], 0))
    canvas.rgb = np.clip(lin, 0, None) ** V.DISPLAY_GAMMA
    return True


# ------------------------------------------------------------------ Smash 4's own vertex programs
S4_SHADERS = True        # --s4-model: Smash 4's side placed by fx_render's model of eft instead
_s4_programs, _s4_static = {}, {}
EFT_QUAD = np.array([[-0.5, 0.5, 0, 0], [-0.5, -0.5, 0, 0], [0.5, -0.5, 0, 0], [0.5, 0.5, 0, 0]], np.float32)  # cross_f 0x04A66B9C
EFT_QUAD_IDX = np.array([0, 1, 2, 0, 2, 3])


def s4_view_block():
    """eft's viewUniformBlock (CB1) for fx_render's camera: vm 0, pm 16, vpm 32 (world -> fx_render's screen x, y,
    depth, w 1), bm 48 (view -> world: billboards), ev 64, ep 68, vp 80, crossflg 84 (0)"""
    S = to_screen()
    v = np.zeros(88, np.float32)
    m = np.eye(4)
    m[:3, :3] = S
    v[0:16] = m.ravel()
    v[16:32] = np.eye(4).ravel()
    v[32:48] = m.ravel()
    bm = np.eye(4)
    bm[:3, :3] = S.T
    v[48:64] = bm.ravel()
    v[64:67] = S.T @ np.array([0, 0, 1.0])
    v[68:71] = S.T @ np.array([0, 0, 1000.0])
    v[80:84] = (1.0, 10000.0, 1.0, 1.0)
    return v


def s4_program(em):
    import latte_exec
    b = bytes(em.s4['p'].shader_binary(em.s4['sh']))
    if b not in _s4_programs:
        try:
            _s4_programs[b] = latte_exec.VertexProgram(b)
        except Exception as ex:          # noqa: BLE001
            print('  %s: vertex program not run (%s)' % (em.name, str(ex).splitlines()[0][:120]))
            _s4_programs[b] = None
    return _s4_programs[b]


def draw_s4(canvas, em, parts, mnow, time):
    """one converted emitter's live particles placed by its own vertex program (tools/latte_exec.py) on eft's
    uniform blocks (CB2 built by cross_f's own code: tools/eft_static.py) and drawn by its pixel program"""
    vs = s4_program(em)
    if vs is None or em.program is None:
        return False
    if 'distortion pass (not drawn)' in getattr(em, 'notes', ()):
        return True                         # it bends the picture behind it; drawn, its map came out black
    born = [q for q in parts if len(q) > 9 and q[9] is not None]
    if not born:
        return True
    d = em.s4['d']
    if id(d) not in _s4_static:
        import eft_static
        _s4_static[id(d)] = np.frombuffer(eft_static.build(d), np.float32).copy()
    cb2 = _s4_static[id(d)]
    gpu = 'v_inVec' in vs.attributes
    # a program reading the live emitter matrix (CB3 emm) takes its particles in the emitter's own space and turns
    # them by it each frame (the flash ring / lines of sys_smash_flash, following): fed world positions, the
    # emitter's offset counted twice
    local = any(cb == 3 and 4 <= v <= 7 for cb, v, _c in vs.reads)
    # a GPU program also turns its particle by the emitter matrix at birth (v_inEmtMat0-2, rows with the
    # translation): it takes the particle's birth position and velocity in the emitter's own space, and
    # v_inVec.w is a speed factor (1; 0 stops the motion and the gravity): run on down smash's splash1, an
    # emitter row translated to (0, 6, 7) put a particle at local 0 on (7, 6), a velocity along local Y under
    # rows turned 90 degrees about X moved it along Z. Fed world values, the call's offset and turn (10 / 180
    # degrees) counted twice and the spray went up and forward where Ultimate's goes back along the ground
    local = local or (gpu and 'v_inEmtMat0' in vs.attributes)
    mesh = em.s4['mesh']
    if mesh is not None:
        pos = np.concatenate([np.asarray(mesh[0], np.float32), np.ones((len(mesh[0]), 1), np.float32)], 1)
        nrm = np.zeros((len(pos), 4), np.float32) if mesh[1] is None else np.concatenate([mesh[1], np.zeros((len(pos), 1))], 1)
        col = np.ones((len(pos), 4), np.float32) if mesh[2] is None else np.asarray(mesh[2], np.float32)
        uv = np.zeros((len(pos), 4), np.float32) if mesh[3] is None else np.asarray(mesh[3], np.float32).reshape(len(pos), -1)
        if uv.shape[1] == 2:
            uv = np.concatenate([uv, uv], 1)
        idx = np.asarray(mesh[4]).ravel()
    else:
        pos, idx = EFT_QUAD, EFT_QUAD_IDX
        nrm = np.tile(np.array([0, 0, 1, 0], np.float32), (4, 1))
        col = np.ones((4, 4), np.float32)
        uv = np.zeros((4, 4), np.float32)
    nv = len(pos)
    follow_live = em.s4['follow'] == 0
    rows = np.asarray(mnow[:3, :4], np.float32)
    A = np.zeros((len(born), nv, len(vs.attributes), 4), np.float32)
    for k, name in enumerate(vs.attributes):
        for j, q in enumerate(born):
            pw, vw, t, (sx, sy), rot, alpha, rgb, rgb1, _lin, b = q[:10]
            age = t * b.get('life', em.life)
            m = rows if follow_live else b['m']
            # the GPU programs (reading v_inVec) take the particle as born and work out the rest: v_inWldPos.w its
            # birth time (age = emp0.x - it), v_inRandom.w its life (the scale / alpha / colour sections are
            # fractions of it), v_inScl only the random x EASL factor (x the base scale and its curve, CB2
            # scaleAnim0-2, in the program); the CPU's programs take its current values, v_inWldPos.w the age
            # (tools/latte_exec.py runs of smoke3: the sizes come out as its keys say only so)
            # a CPU particle's v_inWldPos.w is its age after this frame's step (cross_f 0x04A637E4 writes the
            # record after the update 0x04A624E4 & co. add the step, 0x04A65990 -> 0x04A659A4): 1 on its birth frame
            per = {'v_inWldPos': np.append(b['pl' if local else 'p'], b['birth']) if gpu else np.append(pw, age + 1.0),
                   'v_inVec': np.append(b['vl' if local else 'v'], 1.0),
                   'v_inScl': (b['scale'][0], b['scale'][1], b['scale'][0], 1) if gpu else (sx, sy, sx, 1),
                   'v_inRandom': np.append(b['random'], b.get('life', float(em.life))), 'v_inRot': np.append(b['rot0'] if gpu else rot, 0),
                   'v_inEmtMat0': m[0], 'v_inEmtMat1': m[1], 'v_inEmtMat2': m[2],
                   'v_inColor0': np.append(rgb, alpha), 'v_inColor1': np.append(rgb1 if rgb1 is not None else (0, 0, 0), 1.0),
                   'v_inWldPosDf': np.append(vw, 0)}
            if name in per:
                A[j, :, k] = per[name]
        if name == 'v_inPos':
            A[:, :, k] = pos
        elif name == 'v_inNormal':
            A[:, :, k] = nrm
        elif name == 'v_inColor':
            A[:, :, k] = col
        elif name == 'v_inTexCoord':
            A[:, :, k] = uv
        elif name == 'v_inIndex':
            A[:, :, k, 0] = np.arange(nv)
    cb3 = np.zeros(48, np.float32)
    cb3[0:8] = 1.0                           # emc0 / emc1: the set's and instance's colours (x 1 here)
    # emp0 (cross_f 0x04A65A08): x the emitter's time after this frame's step (instance +0x30, advanced at the
    # end of the update 0x04A64CE8 -> 0x04A65440, after emission and the particles), so time - birth is 1 on
    # a birth frame; w the step (instance +0x5C, the update's own step: 0x04A65984), which the GPU programs
    # take off for their curves (age 0 on the birth frame, as eft's CPU curves); y / z emitter data +0x264 / +0x268
    cb3[8:12] = (time + 1.0, 1.0, 1.0, 1.0)
    cb3[12:16] = 1.0
    full = np.eye(4)
    full[:3, :4] = mnow[:3, :4]
    cb3[16:32] = full.ravel()
    rt = full.copy()
    rt[:3, :3] /= np.maximum(np.linalg.norm(rt[:3, :3], axis=0), 1e-9)
    cb3[32:48] = rt.ravel()
    gp, par = vs.run(A.reshape(-1, len(vs.attributes), 4), {1: s4_view_block(), 2: cb2, 3: cb3},
                     np.tile(np.arange(nv), len(born)))
    gp, par = gp.reshape(len(born), nv, 4), par.reshape(len(born), nv, -1, 4)
    order = np.argsort(gp[:, :, 2].mean(1))           # far first (depth: toward the eye is +)
    tri = idx[:len(idx) // 3 * 3].reshape(-1, 3)
    for j in order:
        for t3 in tri:
            P = gp[j, t3, :2] / np.where(np.abs(gp[j, t3, 3:4]) > 1e-9, gp[j, t3, 3:4], 1.0)
            attrs = {sem: par[j, t3, k] for k, sem in vs.params.items()}
            canvas.tri_program(P, attrs, lambda inp: em.program.run(inp, em.consts, em.s4['sample']), em.blend_mode)
    return True


# ------------------------------------------------------------------ Smash 4 (eft)
def s4_emitters(p, set_index, program_cache=None):
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
        em.interval_random = max(0, f('emit_interval_random'))
        em.duration = f('end_frame') if f('one_time') else FOREVER
        em.rate = f('emit_rate')
        em.life = f('ptcl_life') if f('ptcl_life') != FOREVER else 600
        em.life_random_frames = max(0, f('ptcl_life_random')) if f('ptcl_life') != FOREVER else 0
        em.srt = (tuple(f('emitter_scale')), tuple(f('emitter_rotation')), tuple(f('emitter_translation')))
        em.anims = {a['target']: (a['keys'], a['loop']) for a in p.key_anims(d) if a['target'] < 0x1C}
        em.volume = (f('volume_type'), np.array(f('volume_radius')))
        em.eft_shape = (f('volume_sweep_start'), f('volume_sweep_param'), f('volume_sweep_start_random'), f('volume_surface_random'))
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
            pos, _n, col, uv, idx = p.primitive(f('primitive_index'))
            em.mesh = (np.asarray(pos, float), np.asarray(uv, float)[:, :2], np.asarray(idx).ravel(),
                       None if col is None else np.asarray(col, float))
        texs = []
        for slot in range(3):
            try:
                t = p.decode_texture(d, slot)
                texs.append(None if t is None else np.asarray(t, float) / 255)
            except Exception:                   # noqa: BLE001
                texs.append(None)
        em.tex = texs[0]
        em.blend = 1 if f('blend_type') == 1 else 0
        sh = p.field(d, 'shader_index')
        if program_cache is not None:
            import eft_pixel
            import latte_pixel
            key = bytes(p.shader_binary(sh))
            if key not in program_cache:
                try:
                    program_cache[key] = latte_pixel.Program(key)
                except NotImplementedError:
                    program_cache[key] = None
            em.program = program_cache[key]
            em.sample = sampler(texs, [tuple(f('tex0_uv_scale'))] + [(1, 1)] * 2)
            em.consts = {8: HDR_RANGE}
            em.blend_mode = 'premult' if eft_pixel.premultiplied(p, sh) else \
                {0: 'alpha', 1: 'add', 2: 'sub'}.get(f('blend_type'), 'alpha')
        if S4_SHADERS:
            em.s4 = {'p': p, 'd': bytes(d), 'sh': sh, 'follow': struct.unpack_from('>I', bytes(d), 0x310)[0],
                     'mesh': p.primitive(f('primitive_index')) if f('primitive_index') >= 0 else None,
                     # the vertex program works out the UVs (repeat, flipbook cells, scroll): sampled as they are
                     'sample': sampler(texs, [(1, 1)] * 3, [(
                         (struct.unpack_from('>I', bytes(d), ptcl.TEXRES + ptcl.TEXRES_SIZE * k + 0x0C)[0] >> 24) & 0xF,
                         (struct.unpack_from('>I', bytes(d), ptcl.TEXRES + ptcl.TEXRES_SIZE * k + 0x0C)[0] >> 28) & 0xF)
                         for k in range(3)])}
        if struct.unpack_from('>I', bytes(p.shader_entry(sh)), 0)[0] & 0xFF in (5, 6):
            em.alpha_curve = lambda t: 0.0
            em.notes = ['distortion pass (not drawn)']
        out.append(em)
    return out


# ------------------------------------------------------------------ the scripts
EFFECT_MACROS = ('EFFECT', 'EFFECT_FOLLOW', 'EFFECT_FLIP', 'EFFECT_FOLLOW_FLIP', 'EFFECT_FOLLOW_NO_STOP',
                 'EFFECT_FOLLOW_NO_SCALE', 'EFFECT_FOLLOW_ALPHA', 'EFFECT_ALPHA', 'LANDING_EFFECT', 'FOOT_EFFECT',
                 'EFFECT_FOLLOW_FLIP_ALPHA', 'EFFECT_FLIP_ALPHA', 'EFFECT_FOLLOW_RND', 'EFFECT_FOLLOW_WORK',
                 'EFFECT_FLW_POS', 'EFFECT_FLW_POS_NO_STOP', 'EFFECT_FLW_UNSYNC_VIS')


def ult_calls(path, move):
    """[(frame, effect name, bone, (x, y, z), (rx, ry, rz) degrees, size)] of Ultimate's effect_<move>"""
    if not os.path.exists(path):
        return []
    text = open(path, errors='replace').read()
    # up to the next function: the dumps' facing split leaves an else block whose closing brace is in
    # column 0, so stopping at the first one dropped what follows it (forward smash's EFFECT_OFF_KIND of
    # mouth_water at 23: its crowns lived on in the render; the vfx_trace showed them gone)
    m = re.search(r'unsafe extern "C" fn effect_%s\b.*?(?=\nunsafe extern|\Z)' % re.escape(move.lower()), text, re.S | re.I)
    if not m:
        m = re.search(r'fn effect_\w*\(.*?\n\}', text, re.S)
    body = m.group(0) if m else text
    frame, out, offs = 0, [], []
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
        if em and em.group(1) == 'EFFECT_OFF_KIND':
            offs += [(frame, n) for n in re.findall(r'Hash40::new\("([^"]+)"\)', em.group(2))[:1]]
            continue
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
    return with_offs(out, offs)


def with_offs(calls, offs):
    """each call with the frame its effect is turned off (EFFECT_OFF_KIND / Terminate_Graphic_Effect: its
    emitters stop emitting, the particles live on), else None"""
    return [c + (min((f for f, n in offs if n == c[1] and f >= c[0]), default=None),) for c in calls]


def s4_calls(effect_bin, move):
    """the same from the translated effect.bin (Graphic, Bone, X..ZRot, Size; frames from FRAME / WAIT)"""
    f = acmd.ACMDFile.load(effect_bin)
    cmds = f.scripts.get(acmd.crc(move.lower()), [])
    frame, out, offs = 0, [], []
    for c in cmds:
        info = acmd.INFO.get(c.ident) or {}
        name, syn = info.get('name', ''), info.get('syntax', [])
        if name == 'FRAME':
            frame = max(frame, int(c.params[0]))
        elif name == 'WAIT':
            frame += int(c.params[0])
        elif name == 'Terminate_Graphic_Effect':
            offs.append((frame, c.params[0]))
        elif syn[:2] == ['Graphic', 'Bone'] and 'Size' in syn:
            g = dict(zip(syn, c.params))
            out.append((frame, g['Graphic'], g['Bone'], (g.get('X', 0), g.get('Y', 0), g.get('Z', 0)),
                        (g.get('XRot', 0), g.get('YRot', 0), g.get('ZRot', 0)), g['Size']))
    return with_offs(out, offs)


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
        for fr0, name, bone, xyz, rot, size, off in calls:
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
                if ONLY and not any(o in em.name for o in ONLY.split(',')):
                    continue
                sim = simulate(em, (fr0, cm, size, off), frames, seed=k + 1)
                for fr in frames:
                    if sim[fr]:
                        if em.ult is not None and draw_ult(canvases[fr], em, sim[fr],
                                                           cm @ emitter_matrix(em, fr - fr0), float(fr - fr0), size):
                            continue
                        if em.s4 is not None and draw_s4(canvases[fr], em, sim[fr], cm @ emitter_matrix(em, fr - fr0),
                                                         float(fr - fr0)):
                            continue
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
    ap.add_argument('--stage', type=int, default=2, help='1: the converted parts drawn as colour x texture; '
                    '2 (default): by their own pixel programs (tools/latte_pixel.py)')
    ap.add_argument('--ult-prot-order', default='xzy', help="eft2's particle rotation order for Ultimate's side "
                    '(the product left to right, e.g. xzy = Rx Rz Ry)')
    ap.add_argument('--ult-rt', action='store_true', help="test: Ultimate's emitter translation turned by its "
                    'rotation (R T S, not T R S)')
    ap.add_argument('--ult-drop', default='', help='test: comma-separated key-animation targets left out on '
                    "Ultimate's side (5-7 EAER, 8-10 EAET, 17-18 EASL)")
    ap.add_argument('--ult-time-emit', action='store_true', help="comparison: Ultimate's distance emitters "
                    'emitted by their rate instead (what eft does)')
    ap.add_argument('--pitch', type=float, default=0.0, help='degrees the camera looks down (Cemu footage of '
                    "Smash 4's training stage: about 15 - 20; Ultimate's side view: 0)")
    ap.add_argument('--only', default='', help='comma-separated substrings: only emitters whose name has one')
    ap.add_argument('--ult-model', action='store_true', help="Ultimate's side drawn by fx_render's own model "
                    "of eft2 instead of Ultimate's shaders run through tools/mx_exec.py")
    ap.add_argument('--s4-model', action='store_true', help="Smash 4's side placed by fx_render's own model of eft "
                    "instead of the converted parts' vertex programs run through tools/latte_exec.py")
    a = ap.parse_args()
    global ULT_SHADERS, S4_SHADERS
    ULT_SHADERS = not a.ult_model
    S4_SHADERS = not a.s4_model
    global ULT_PROT_ORDER, ONLY, ULT_RT
    ULT_PROT_ORDER, ONLY, ULT_RT = a.ult_prot_order, a.only, a.ult_rt
    global ULT_DROP, ULT_TIME_EMIT, PITCH
    PITCH = a.pitch
    ULT_TIME_EMIT = a.ult_time_emit
    ULT_DROP = tuple(int(v) for v in a.ult_drop.split(',') if v)
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
    programs = {}
    for nm, v in ids.items():
        if nm.startswith('_'):
            continue
        i = int(v, 0) & 0xFFFF
        if i < len(ef.entries) and ef.entries[i][1]:
            s4[int(v, 0)] = s4_emitters(p, ef.entries[i][1] - 1, None if a.stage == 1 else programs)
    os.makedirs(a.out, exist_ok=True)
    for move in a.moves:
        out = os.path.join(a.out, '%s.png' % move.lower())
        for line in render_move(a, move, ult, s4, out):
            print('  ' + line)
        print(out)


if __name__ == '__main__':
    main()
