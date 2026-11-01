# fx_render's Ultimate side vs eft2 (main.bin)

`tools/fx_render.py` draws a move's effects as Ultimate's engine (eft2, in exefs `main.bin`) would and
as the converted bank plays in Smash 4 (eft, `cross_f.rpx`). The aim is an Ultimate side that does
what eft2 does, stage by stage, read from the executable rather than guessed. This page lists every
stage: what has been checked against main.bin (with the address), and what is still an approximation.
Update it whenever a stage is checked or changed.

Status: **exact** = follows the code at the address given; **data** = reads the right fields but the
code that uses them hasn't been read; **approx** = a stand-in; **missing** = not modelled.

## Emitter

| stage | status | notes |
|---|---|---|
| emitter matrix (scale, rotation, translation) | exact, matches the engine | R = Rz Ry Rx, T R S; static 0x88320, animated 0x8D0A0 (EAER degrees x pi / 180), composed v . M 0x8D838 |
| emitter animations EAES / EAER / EAET / EASL / EATR ... | exact | parsed 0x8CB00 (EAES +0x290, EAER +0x298, EAET +0x2A0), applied 0x8DE1C, linear keys 0x933D0, matrix rebuilt every frame 0x8D770 |
| time emission: first emission, gaps | exact | the threshold starts at 0 (0x874D8): the first particles on the window's first frame; the next gap interval + 1 + (rand x interval_random) >> 32 (0x88750) |
| time emission: count | exact, matches the engine | carry += rate (animated, EATR; the data's own for volume types 5 / 6) + rate x rate_random / 100 x U (0x8D408); one particle a whole unit |
| distance emission | exact, matches the engine | 0x8D340, run every frame of the window instead of the rate: see below |
| the gate byte (emitter set +0x265) | assumed on | copied from the set's creation arguments (0x112C64); Squirtle's diagnostic 8 showed these emitters do emit in Ultimate |
| runtime emission scales (instance +0x60 / +0x64, set +0x50 / +0x54) | assumed 1 | set by the game |
| window (start, duration, one_time) | data | |
| effect turned off (EFFECT_OFF_KIND / Terminate) | approx | emission stops; is_fade_emit / alpha_fade_time not modelled |

Distance emission (0x8D340): the emitter's movement this frame is measured in its own frame (0x8E040 -
0x8E124: the current and previous positions through the inverse of its current matrix, so divided by
its scale and the effect's); under dist_marg it counts as 0. A movement of 0 becomes dist_min (emitting
where the emitter stands); otherwise it is clamped to dist_min .. dist_max. It is added to a carry,
and each whole dist_unit gives one particle: carry -= unit, then the particle comes from
cur + (prev - cur) x carry / movement, so the frame's particles are laid back along the path. The
previous position starts at the set's position and the movement at 0 (0x874E0); it is updated every
frame.

## Particles

| stage | status | notes |
|---|---|---|
| emission shapes: circles (types 1, 2) | exact | 0x90C40 / 0x90E20 (shape table 0x4F48C30): angle start + sweep x (i / n) - sweep / 2, point (sin a rx, 0, cos a rz); matches the engine's births |
| emission shapes: the others | approx | `shape_point`: point / sphere / box style spread; their routines are in the same table |
| position_random | missing | |
| velocity (all-direction, designated direction, diffusion, vel_random) | data, matches the engine's speeds | outward x all_direction + direction x scale, x (1 - vel_random x U): the engine's birth speeds fall in exactly that range |
| inherited velocity / scale (INHERIT) | missing | |
| life, life random | data / missing | life_random not modelled |
| gravity, world gravity, air resistance | data | integration order (v x air + g, then p += v) not checked |
| scale curve, scale random | data | only the X random |
| colour 0 / 1 and alpha over life | data | 8-key tracks read with `vfxb_to_ptcl.track`; evaluator not checked |
| rotation (init, random, add) | data | is_rotate axes zeroed per particle: exact (0x8B8A0); order taken as eft's Rx Rz Ry (--ult-prot-order) |
| following (follow_type) | approx | particles keep the emitter's frame from their birth (follow 1); 0 and 2 not told apart |
| fields (spin, collision, convergence, magnet, random) | missing | converted (vfxb_to_ptcl), not simulated here |
| child emitters, fluctuation | missing | |

## Drawing

| stage | status | notes |
|---|---|---|
| particle types (billboard, Y billboard, XY / XZ plates, directional, meshes) | data; type 3 meshes exact | eft2's type 3 is the XY polygon: a mesh's vertex program (variations 131 / 141, tools/ult_shader_glsl.py) is the birth emitter matrix (columns normalised) x rotation (X Z Y) x scale x (vertex + pivot), no velocity; 4 = XZ polygon (its vertex program flattens Y); 5 / 6 directional. The Smash 4 side's type 4 is drawn by its decoded program (Y along the world motion, X = emitter Y x motion) |
| texture | approx | the first flipbook cell only; no UV scroll / rotation / scale animation |
| combiner (colour / alpha process) | approx | colour 0 / colour x texture / c0 x tex + c1 x (1 - tex); alpha from red; alpha_process 4 erosion exact |
| second / third texture, custom shaders | missing | the converted side runs its own pixel programs (stage 2); Ultimate's Maxwell programs are not run |
| blending | approx | alpha or add; draw order by depth only |
| colour space | data | an alpha-blended part's colours (and its linear textures) shown display-encoded, as Ultimate's frame is (the converter's LINEAR_DISPLAY rule): before, the Ultimate side drew linear values, a deep blue where Ultimate shows pale cyan-white |
| camera | approx | orthographic side view; `--pitch` looks down (Cemu's training camera ~18 degrees, Ultimate's side view 0) |
| refraction, bloom, soft particles, depth | missing | |

## Checking against the engine itself

docs/vfx-trace.md: an OpenSmash-Ultimate mod records the engine's own emitters and particles (births,
every frame, its random state), and `tools/vfx_trace.py births` compares fx_render's births with them.
Each stage above moves to **exact** once it matches the trace, not only the code read.

## Ultimate's shaders as GLSL

`tools/ult_shader_glsl.py FILE.eff|PORT SET EMITTER [vs|ps]` turns an emitter's compiled program (its BNSH
variation) into GLSL with OpenSmash-Ultimate's Maxwell translator (ssbu-recomp `runtime/mx_translate.c`,
port_sources.json key `opensmash`; built once into build/mx_glsl). It is the code OpenSmash runs the game
with, register for register, so it settles what a stage computes without hand-decoding.

What its inputs are:
- **c9 is the emitter's data as stored in the effect file**: c9 byte k = EMTR binary byte k (vfxb.EMITTER;
  STATIC from 0x50). Squirtle's wave vertex program reads its scale curve at c9[384..391] = EMTR 0x600 =
  STATIC 0x5B0 `scale_anim` (key time in .w) and `rotate_regist` at c9[459] (EMTR 0x72C, as pow(regist, t)).
  So every emitter constant a program reads comes straight from the file.
- c10: per-emitter values set each frame (c10[8] the emitter's time); c8 the view block; c13 the custom
  shader's parameters (the dissolve's edge width c13[0]); c16 frame-level scales.
- vertex attributes = the particle arrays (docs/vfx-trace.md): 3 position (w life), 4 velocity (w birth),
  5 scale, 6 random, 8 / 9 / 10 the emitter matrix at birth (rows).

Checked with it:
- type 3 (XY polygon) meshes, variations 131 / 141: attributes 8 - 10's columns normalised (sqrt / rsqrt
  of each column), no velocity: the hand decode (vfxb_to_ptcl: eft type 1).
- the dissolve (custom shader 8), WaterSmash wave1's pixel program: colour = lerp(colour 1, colour 0,
  tex0.rgb x tex1.rgb); alpha = tex0.a x tex1.r x colour 0's alpha x ...; discard where tex1.a < colour 1's
  alpha (the threshold), alpha x (tex1.a - threshold) / c13[0] within the edge. eft_pixel's `mask1` matches
  (every dissolve's texture 1 is white in rgb, so writing it as white + the mask is exact).

Next: run these programs in fx_render (the GLSL is C-like: c9 from the file, the attributes from the
simulation or a vfx_trace record), so the Ultimate side draws with the engine's own vertex and pixel code.

## The first trace (Squirtle, user's run, 162 emitter runs)

Births a frame matched for every emitter of water_smash(_r), water_cutter(_r) and mouth_water, both facings
(only differences: where the move's script turned the effect off, which the bare emitter doesn't know).
water_smash / water_cutter's splashes are born at ONE point, (0, 0, -radius) (even circle, one division),
not spread round the circle as fx_render had them; eft has no division count we know of, so the
converted bank still spreads them (next: eft's circle routine in cross_f).

## Second check (matrices, positions, colour, camera)

The trace's emitter matrices against fx_render's (script call x emitter SRT and key animations, read at
the frame's own time): what is left is a pure facing turn and Squirtle's slide (tilt 0.01 degrees), for
forward and down smash, both facings: the call rotation order (Z Y X), the 0.94 fighter scale and the
key animations all as the engine has them. The wave particles' positions over their lives match within
about 6% (their speeds' random). Their scale and rotation arrays don't change on the CPU (the curves are
the GPU's). Down smash's wave stands about 5 units high with a level camera on both sides, as in the
native clip; with Cemu's camera (--pitch 18) the ring's far half stands up into the tall arc of the
Smash 4 footage: a camera difference, not the bank's.

## Next, in order

1. Velocity and emission shapes from main.bin (they decide where every particle goes).
2. Following types 0 / 2, position_random, life_random.
3. Texture animation (flipbook cells, UV scroll) and the second texture.
4. Fields and child emitters.
