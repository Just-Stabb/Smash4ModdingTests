# Scope: one shader path for Ultimate effects on Smash 4 ("universal shader pair")

Status: scoping only, nothing built yet (Squirtle test 21 is the current state of the converter).

## The idea

Today `tools/vfxb_to_ptcl.py` turns each Ultimate emitter into an eft emitter. It picks one of Smash 4's own
compiled particle programs (a "template") that is close enough. Then it patches around the template's
limits:

- `eft_pixel.py` writes our own pixel programs.
- `eft_vertex.py` grafts slot 1 / 2 UVs, rotation and the Z scale curve into the vertex programs.
- Colour, alpha and threshold curves are refitted to eft's 3-key ramps.
- Mix-weight curves are baked into textures, sections clamped, flips moved between slots.

Most fixes in tests 16–21 were one more patch of that kind:

- Type-6 frame
- Z scale curve
- Dissolve masks
- UV switches
- Random flips
- Linear-light mix

Every new port will hit more of them.

The universal path stops imitating Ultimate's programs and **runs them**. Ultimate's compiled shader for each
emitter (its BNSH variation) is already decoded to GLSL by `tools/ult_shader_glsl.py`, and `fx_render` runs it
through `mx_exec`. The new step lowers that GLSL to Latte (the Wii U GPU's instruction set) and writes it into the
ptcl as the emitter's own vertex and pixel program. The per-emitter constants are baked in. The drawing is then
Ultimate's own, by construction; only eft's CPU side (emission, motion, life) still has to be converted.

"Pair" = one generator producing a vertex + pixel program for any emitter, not two hand-written programs.

## Measured scope (Squirtle, `ef_pzenigame.eff`)

| | |
|---|---|
| emitters | 165, each with its own compiled variation (165 variations) |
| particle calc | all CPU (`calc_type` 0): Ultimate's CPU moves the particles, the vertex program draws them |
| custom shaders | 114 none, 51 dissolve (custom 8) |
| vertex programs | 317 - 1056 operations (median 600); one jump dispatcher (`for (;;) switch (pc)`) each |
| pixel programs | 26 - 78 operations |
| per-emitter constants read (c9) | vertex median 62 words, max 128; pixel 1 - 3 |
| textures per pixel program | 1 (81), 2 (73), 3 (11): fits eft's 3 slots |
| operations used | fma, mul/add, compares + predicates, floor / trunc / f2i, int / uint casts, bitfield extract (~8.5k), sin / cos, exp2 / log2, sqrt / inversesqrt, min / max / clamp / abs, isnan, texture / textureLod / textureQueryLod, discard |

All have Latte equivalents in our assembler (decaf's table: MULADD, BFE_UINT / BFE_INT, SIN / COS in turns,
EXP_IEEE / LOG, SQRT_IEEE / RECIPSQRT, FLT_TO_INT, KILL*, SAMPLE / SAMPLE_L, GET_GRADIENTS).

## Architecture

### Lowering (new: `tools/ult_to_latte.py`)

The translated GLSL is register-level (Maxwell registers `rN` as `uint`, `F()` / `U()` bit casts, one operation a
statement), so lowering is statement by statement, not a general GLSL compiler:

- registers `rN` -> Latte GPRs (Maxwell uses about 30 to 40; Latte allows up to 128)
- one operation an ALU group to start (as `eft_vertex` grafts already are); packing into 5-wide groups later,
  only if speed needs it
- predicates `pN` -> conditional selects (CNDE / CNDGT) or predicated groups; the jump dispatcher -> Latte CF jumps
  (few blocks a program: a dead-particle exit, a branch or two)
- texture handles (`c2` pairs) -> slots t0 - t2; LOD queries -> gradients / SAMPLE_L

### Constants

| Ultimate block | contents | on Smash 4 |
|---|---|---|
| c9 static (emitter data) | curves, scale, UV animation, colours, ... | baked as literals (only the words read) |
| c13 custom params (CSDP), c16 per-effect, c1, c12 | dissolve edge, multipliers, driver values | baked (c12: 20 words, to identify) |
| c8 view | view / projection / billboard matrices, eye | a prologue rebuilding them from eft's CB1 (vm, pm, vpm, bm, eye) |
| c10 dynamic | time, step, emitter matrix, colour / alpha multipliers | prologue from eft's CB3 (emp0, emm, emc0 / 1) |

### Attributes

Ultimate's particle arrays come from eft's streams. The CPU binds them by name (cross_f 0x04A59FC8), so the
program's header just asks for them:

| Ultimate | eft stream |
|---|---|
| sysPosAttr / TexCoord / VertexColor0 | v_inPos / v_inTexCoord / v_inColor |
| sysLocalPosAttr (xyz, w life) | v_inWldPos.xyz (CPU particles: current place), life from v_inRandom.w or baked |
| sysLocalVecAttr (xyz, w birth) | v_inVec / v_inWldPosDf; birth = time - age (v_inWldPos.w is the age on CPU particles) |
| sysLocalDiffAttr (last movement) | v_inWldPosDf |
| sysScaleAttr (xyz) | v_inScl (x, y; z = x x the baked z / x ratio) |
| sysRandomAttr (4 uniforms) | v_inRandom.xyz + one derived (hash) |
| sysInitRotateAttr | v_inRot |
| sysEmtMat0-2 | v_inEmtMat0-2, or identity with world places |

### Output

Pixel output is display-encoded at the end (Smash 4's framebuffer isn't linear). Blend, depth and cull state stay
eft's emitter fields (already converted). The template chooses only the particle mode and the stream set; its
programs are replaced whole.

### What stays as the converter does it now

Everything on eft's CPU:

- emission (rate, interval, distance emission)
- volume shapes
- velocity, gravity and air resistance on CPU particles
- life and life random
- key animations (EA**)
- fields, children, fade

These are already matched against main.bin (docs/fx-render-eft2.md).

## Verification (already half built)

`fx_render` runs both sides: `mx_exec` runs Ultimate's GLSL, and `latte_exec` / `latte_pixel` run Latte programs.
The new path gets a per-emitter **differential test**: feed the same particle to Ultimate's program (inputs as
eft2 lays them out) and to the lowered program (the same values through eft's streams and blocks), and compare
`gl_Position`, every output and every pixel. Any lowering bug shows up as a named emitter and a first
differing register. `port_check` gets a check that every emitter's lowered program passed.

## Phase 0 results (settled; details in docs/fx-render-eft2.md, "Runtime timing")

- `emp0.w` is the frame step (1); eft's GPU-side programs subtract it so their curves start at age 0. The age
  a translated program needs is `v_inWldPos.w` (age after the step) = Ultimate's c10[8] - birth.
- CPU streams: `v_inRandom.w` = the particle's life (int), `v_inScl.z` = 0 (so the z / x ratio is baked),
  `v_inVec.w` a random value (not the birth: birth = time - age).
- c12 = the emitter-plugin block (EP0x), baked like c9.
- Still to measure in phase 1: whether a particle is moved on its birth frame in both games (the record
  shows the moved place in eft; Ultimate's order looks the same).

## Unknowns to settle first (phase 0, as scoped)

1. **eft's runtime values:**
   - `emp0.w` = instance +0x5C (cross_f 0x04A65B18). Test 21's open one-frame lag hinges on it.
   - `v_inRandom.w` and `v_inScl.z` on CPU particles.
   - `emp0.x` at draw time.

   To settle: cross_f in unicorn (as `eft_static.py` does for CB2), or a Cemu capture (RenderDoc, or a graphics
   pack dumping the particle uniforms).
2. **c12:** what Ultimate keeps there (20 words).
3. **Shader size:** about 600 one-op groups x 8 bytes + literals ≈ 6 - 8 KB an emitter, ≈ 1.2 MB for Squirtle
   (his bank is 8.7 MB now and loads). Dedupe identical programs.
4. **Speed:** 600 vertex ops a vertex is about 3x a template's. Squirtle's busiest frames are a few tens of
   thousands of vertices: fine on Cemu, to measure on hardware. Packing is the lever if needed.

## What still can't be 1:1

- **Linear-light blending and HDR / bloom:** Ultimate blends transparency in linear light and lets colours pass 1;
  Smash 4's framebuffer can't. The programs encode their output for display (as the converter does now); a
  half-transparent white still reads a little thinner.
- **Ultimate's CPU-side engine:** emission and motion run on eft's CPU, converted as now.

## Phases

| phase | work | done when |
|---|---|---|
| 0 | settle the unknowns above (emp0, CPU streams, c12) | values written into docs/fx-render-eft2.md |
| 1 | vertex lowering + prologues + header writer | Squirtle's 165 vertex programs pass the differential test |
| 2 | pixel lowering (textures, discard, LOD, encode) | all 165 pixel programs pass |
| 3 | converter integration: universal path by default, today's path as per-emitter fallback | Squirtle builds, port_check clean, renders match Ultimate in fx_render |
| 4 | in-game test (Squirtle), then Hero / Sephiroth rebuilt through it | your in-game check |

Rough size: phase 0 about 1 - 2 working sessions; phase 1 about 4 - 6; phase 2 about 2 - 3; phase 3 about 2 - 3;
phase 4 about 2. So about 11 - 16 sessions, with a working Squirtle (phases 0 - 3) part way through. The
differential test means a port's effects would mostly need no hand-fixing afterwards.

## Decisions for you

- **Hardware vs Cemu:** whether real Wii U hardware matters (it decides whether speed / packing work is needed).
- **First character:** Squirtle first (all CPU particles, his renders already set up), then the others.
- **Old path:** keep it as the fallback, or retire it once the universal path covers everything.
