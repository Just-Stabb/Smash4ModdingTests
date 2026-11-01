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
| gravity, world gravity, air resistance | data, exact | p += v, then v = v x air + g (vfx_trace, down smash's splash2: born at z -0.1, v -1.965; next frame z -2.065, v -1.965 x 0.96 with gravity in it, not yet in the position). Until the spray-height check fx_render had air first: every particle one air step short, its gravity a frame early |
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
| texture | exact (shaders) | Ultimate's own programs (above); `--ult-model`: the first flipbook cell only, no UV animation |
| combiner (colour / alpha process) | exact (shaders) | Ultimate's own pixel programs; `--ult-model`: colour 0 / colour x texture / c0 x tex + c1 x (1 - tex) |
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

## Ultimate's side drawn by Ultimate's shaders (default; `--ult-model` for the old model)

Since this step fx_render draws every Ultimate emitter with its own programs (tools/mx_exec.py): the
translated GLSL compiled as C++ behind a small GLSL layer (vec2 / vec4, half floats, carries, bitfields,
`texture()` a bilinear sampler with eft2's wrap modes), the vertex program run on each particle x mesh
vertex, the pixel program on every pixel the triangles cover, blended in primitive order in linear light
(the frame encoded for display at the end, as Ultimate does). So scale / colour / alpha curves, UV
scroll / scale / flipbooks, rotation, motion under gravity and air resistance, dissolves and combiners are
the engine's own code. What fx_render still supplies is the emission: the births (exact, vfx_trace) and
each particle's arrays as born.

Inputs, all by name from each program's reflection (BNSH program +0x78: per stage, _DIC tables of inputs,
outputs, samplers, constant buffers and a slot table; constant buffer slot k = the shader's c(3 + k)):
- attributes: sysPosAttr / sysTexCoordAttr (the mesh, or eft2's quad), sysLocalPosAttr (emitter-local
  position at birth, w life x (1 - life_random x U)), sysLocalVecAttr (velocity, w birth time),
  sysScaleAttr (scale x (1 - scale_random x U) on all axes x EASL), sysRandomAttr (4 uniforms),
  sysInitRotateAttr (rotate_init on is_rotate's axes; the random part is the program's), sysEmtMat0-2Attr
  (the emitter matrix at birth, rows). Every one of Squirtle's 164 emitters is calc type 0, the CPU's:
  eft2 moves the particle and rewrites its position / velocity arrays every frame (the trace's per-frame
  records move; the programs read no velocity xyz), so the program gets the particle's current place and
  velocity in its birth frame, life / birth time / scale / random / rotation / matrix as born (the engine's
  birth records, docs/vfx-trace.md). Fed the birth values, every particle stood where it was born: down
  smash's spray drew low.
- c9 sysEmitterStaticUniformBlock: the emitter data after eft2's load-time pass, run from main.bin itself
  (tools/eft2_resolve.py, unicorn: 0x8B480, then the first 0x750 bytes, as the memcpy at 0x8C204 copies
  them). The file alone is not it: e.g. every UV repeat is 0 in the file (1 after the pass, from the
  repeat byte's two tables), the key tables are padded, the shader flag words +0x50 / +0x54 set (0x8C660).
- c10 sysEmitterDynamicUniformBlock: colour 0 / 1 (info colours), time (8), step (11), alpha (12), scale
  (13-15: the call's size, the fighter's 0.94 with it: the birth matrices carry it but the program
  normalises them), the emitter matrix (16-27, rows) and its rotation (32-43).
- c8 sysViewUniformBlock: view 0-15 (to_screen()), projection 16-31, view-projection 32-47 (straight to
  canvas pixels), billboard matrix 48-59, eye vector 64, eye position 68, near / far 72.
- c13 sysCustomShaderReservedUniformBlockParam: the emitter's CSDP (the dissolve's edge); c16
  sysCustomShaderUniformBlock2: the game's per-effect block, neutral (colour / alpha x 1, no depth shift);
  c2: texture unit u at word 8 + 2u; c1: the program's immediates (NVN control section +0x6FC / +0x700).

Checked against Ultimate's own footage (Squirtle's native clip): the smash-charge ring is a crescent
(sys_smash_flash ring1's 5-cell flipbook, which the old model froze on its full first cell) and down
smash's dust is low translucent puffs; both as the shader-run side draws them. Not modelled: the game's
per-effect colour / alpha (c16, EFFECT_SET_COLOR...), depth / soft particles, refraction (shader_type 1,
left out), sort order (far particles first).

## Smash 4's side drawn by the converted parts' own vertex programs (default; `--s4-model` for the old placement)

`tools/latte_exec.py` turns a Latte vertex program (latte-dis text) into C++, one vertex at a time with the
program's own control flow (R600 predication as one lane: ALU_PUSH_BEFORE saves the active flag, PRED_SET
with UPDATE_EXEC_MASK sets it at the clause's end, JUMP / ELSE / POP and the POP_AFTER clauses restore it),
integer and float operations bit-exact (MUL / MULADD / DOT4 non-IEEE, SIN / COS in revolutions), KCACHE
banks, buffer fetches (b130 = CB2 at an integer index). All 171 programs of Squirtle's bank compile. The
pixel programs stay latte_pixel's, fed the vertex program's PARAMn by semantic (SPI_VS_OUT_ID).

Inputs:
- CB2 emitterStaticUniformBlock: built by Smash 4's own code (`tools/eft_static.py`: cross_f 0x04A5AA00 in
  unicorn, PowerPC; it clears 0x500 bytes, fills shtAnim0-2 (0x04A5A6AC), ptnAnm0-1 (0x04A5A858), uboFlag,
  rotBasis, the scale / alpha / colour animation tables, and swaps every word for the GPU).
- CB1 viewUniformBlock: vm, pm, vpm (world -> fx_render's screen), bm (billboards), ev, ep, vp, crossflg 0.
- CB3 emitterDynamicUniformBlock (cross_f 0x04A65A08 fills it each frame from the live instance): emc0 /
  emc1 1, emp0 = (the emitter's time, 1, 1, 1), emp1 1, emm / emmrt the emitter matrix. Not modelled: the
  set's and instance's colours, emp0.yz / emp1 (set values).
- the particle record (eft binds its streams by name, cross_f 0x04A59FC8: buffer 5, 0xB0 bytes a particle:
  WldPos, Scl, Vec, Random, Rot, EmtMat0-2, Color0, Color1, WldPosDf); the mesh in buffers 0-4 (Pos w 1,
  TexCoord, Normal, Color, Index), or eft's quad (cross_f 0x04A66B9C: corners -+0.5, w 0, indices 0-3).
  The GPU programs (those reading v_inVec: 93 of the bank's 171) take the particle as born and work out
  the rest themselves: v_inWldPos.w its birth (age = emp0.x - it), v_inRandom.w its life (their scale,
  alpha and colour sections are fractions of it), v_inScl only the random factor (the base scale and its
  curve are CB2's scaleAnim0-2): found by running smoke3's program, whose size follows its keys only so.
  The CPU's programs take its current values (v_inWldPos.w the age). A program reading the live emitter
  matrix (CB3 emm: sys_smash_flash's ring and lines, following) takes positions in the emitter's space;
  so does a GPU program reading v_inEmtMat0-2 (it applies the birth matrix, translation included, to the
  particle's birth position and velocity), and its v_inVec.w is a speed factor, 1 (0 stops the motion and
  the gravity). Fed world values, down smash's spray went up and forward (the call's offset and turn
  counted twice). Their motion, run on down smash's splash2 against the trace: the same places as eft2's
  steps (geometric sum: z to 0.001), the gravity a trapezoid (+ 0.5 g x the sum of air^i), so it falls
  0.02 more after a frame, 0.24 after 16, 0.31 after 24 (of about 8): eft has no constant world velocity
  to take it back with, and it is left.
  Still fx_render's: the CPU particles' motion and colour curves (eft's CPU calc), emission.

Checked (Squirtle's forward / down smash): the smash ring now plays its flipbook into the crescent, as
Ultimate's; the dust is translucent puffs on both sides; the flash lands where Ultimate's does once the
following programs get local positions (world positions put it 8 units off). Down smash's dust crown
(sys_whirlwind_l / r's impact meshes) was missing on the Smash 4 side because the bank had it as type 4 at
rest, which eft draws as a point (the vertex program run on it: every vertex at the particle): converted as
type 1 since test 15 it matches Ultimate's (its last frames a little wider: eft's three scale keys for
Ultimate's four). The Smash 4 sampler honours each slot's wrap mode (ptcl texture word 0x0C: u bits 24-27,
v 28-31; repeat everywhere before put a scrolled crown's base back over its top as a grey band). Down
smash's spray, a few units higher on the Smash 4 side, was the renderer's three times over, not the bank's:
the GPU programs fed world values (above), Ultimate's CPU particles drawn where they were born (calc type
0, above) and its steps in the wrong order (Particles). Now each splash emitter's particle centres agree
within noise (the highest 15.8 / 16.1 for splash1, 14.8 / 13.2 for splash2, 12.8 / 13.9 for splash3,
frames 16-36; the side of each square within about 10%: Ultimate's program emits the quad's corners in
another order, so measure it by its sides).

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
