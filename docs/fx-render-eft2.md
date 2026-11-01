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
| emitter matrix (scale, rotation, translation) | exact | R = Rz Ry Rx, T R S; static 0x88320, animated 0x8D0A0 (EAER degrees x pi / 180), composed v . M 0x8D838 |
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
| particle types (billboard, Y billboard, XY / XZ plates, directional, meshes) | data | type 4 = XZ polygon (its vertex program flattens Y); type 5 / 6 directional meshes |
| texture | approx | the first flipbook cell only; no UV scroll / rotation / scale animation |
| combiner (colour / alpha process) | approx | colour 0 / colour x texture / c0 x tex + c1 x (1 - tex); alpha from red; alpha_process 4 erosion exact |
| second / third texture, custom shaders | missing | the converted side runs its own pixel programs (stage 2); Ultimate's Maxwell programs are not run |
| blending | approx | alpha or add; draw order by depth only |
| refraction, bloom, soft particles, depth | missing | |

## Checking against the engine itself

docs/vfx-trace.md: an OpenSmash-Ultimate mod records the engine's own emitters and particles (births,
every frame, its random state), and `tools/vfx_trace.py births` compares fx_render's births with them.
Each stage above moves to **exact** once it matches the trace, not only the code read.

## The first trace (Squirtle, user's run, 162 emitter runs)

Births a frame matched for every emitter of water_smash(_r), water_cutter(_r) and mouth_water, both facings
(only differences: where the move's script turned the effect off, which the bare emitter doesn't know).
water_smash / water_cutter's splashes are born at ONE point, (0, 0, -radius) (even circle, one division),
not spread round the circle as fx_render had them; eft has no division count we know of, so the
converted bank still spreads them (next: eft's circle routine in cross_f).

## Next, in order

1. Velocity and emission shapes from main.bin (they decide where every particle goes).
2. Following types 0 / 2, position_random, life_random.
3. Texture animation (flipbook cells, UV scroll) and the second texture.
4. Fields and child emitters.
