# Scope: one shader path for Ultimate effects on Smash 4 ("universal shader pair")

Status: phases 0 and 1 done (vertex programs lowered and tested); phase 2 (pixel programs) next. Squirtle test 21
is still the converter's state in game: nothing from this path is in a package yet.

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

## Phase 1 results (vertex lowering)

`tools/ult_to_latte.py` lowers a translated vertex program to latte-asm source and assembles it.
`tools/ult_to_latte_test.py NAME [--mode identity|eft]` is the differential test.

**Squirtle: all 165 vertex programs pass.** This holds in both modes, on several seeds, with 256 to 1024 random
particles each, and both the live and the dead-particle paths run. The test compares `gl_Position` and every
output against `mx_exec` on the same particles, to 1e-4 + 2e-4 relative. Changing one baked word makes it fail,
so it is not passing trivially.

The reference runs Ultimate's program with an unfused multiply-add. Maxwell's FFMA rounds once; the Latte ALU
has no fused multiply-add (MULADD_IEEE rounds twice). With the fused reference, 4 programs differed on about 1
particle in 1000 by ~5e-4 relative. That only happened where the random view matrices cancel (z ~ 9e5); with
the unfused reference they agree, two of them bit for bit. A real camera doesn't cancel like that, so the game
shows no difference.

Size: median 727 one-operation groups, max 1541. Most of the gain over the Maxwell statement count comes from
branches on baked data being decided at build time, and their dead sides never emitted.

How it lowers:

- **Parsing.** The GLSL is parsed into statements (149 distinct shapes over the 165 programs) and expressions
  are typed (float / int / uint / bool). Every Latte operation on literals is folded with the ALU's own
  semantics, and a few identities are folded too (x & ~0, x | 0, a select on a literal).
- **Registers.** One GPR component per Maxwell register, predicate, flag, active mask and output component.
  Temporaries are per statement. Attributes go in R1.. and the vertex id in R0.x.
- **Control flow (if-conversion).** A block's active mask is the OR of its incoming jumps. A region opened by a
  jump closes back to the mask it began with when no lane returned inside it, so the usual if / else diamond
  costs nothing after the merge. Registers are guarded (CNDE_INT) only inside a region a pending jump skips.
  Outputs are guarded only once some lane may have left (a return).
- **Constants.** c9, c1, c12, c13 and c16 are baked. c9's one dynamic read is a select chain over 8 entries:
  `c9[(X + 0x120 / 0x128) >> 2]`, 16-byte entries, in 27 programs.
- **Instructions.**
  - Float operations use the IEEE kinds.
  - sin / cos are range-reduced into turns.
  - `~x` is XOR with ~0, because latte-asm's grammar gives NOT_INT two sources.
  - Clauses hold at most 120 slots, each locking CB1 / CB3 0-31.
- **Header.** Attribute and block names, outputs as PARAMn with their semantics. latte-asm needed a fix:
  the grammar's comment token drops the `;` that the header regexes expect, so before the fix it wrote no
  names at all. `build_asm.sh` now patches that. Attribute type `vec4` gives 11, as vanilla does; block sizes
  are eft's own (view 352, dynamic 192).

eft mode (`mode='eft'`), the mapping the converter will use:

| Ultimate | eft |
|---|---|
| c8 0-71 (view, projection, view-projection, billboard, eye) | CB1 the same words (row-major, as fx_render's validated blocks) |
| c8 72-75 (near, far, near x far, far - near) | CB1 vp 80 / 81, the products computed once |
| c10 (colours, time, step, emitter matrices) | CB3 the same words |
| sysLocalPosAttr xyz / w (life) | v_inWldPos.xyz / v_inRandom.w |
| sysLocalVecAttr xyz / w (birth) | v_inVec.xyz / emp0.x - v_inWldPos.w (computed once) |
| sysScaleAttr x y / z | v_inScl.xy / v_inScl.x x the emitter's z / x ratio (baked) |
| sysRandomAttr xyz / w | v_inRandom.xyz / v_inVec.w (eft's own per-particle random) |
| sysPosAttr, TexCoord, VertexColor0, InitRotate, LocalDiff, EmtMat0-2 | v_inPos, v_inTexCoord, v_inColor, v_inRot, v_inWldPosDf, v_inEmtMat0-2 |
| sysEmitterPluginAttr0-4 (6 programs) | none yet (0) |

The eft-mode test builds eft's streams from the same particle by this table's inverse. So it checks the
mechanism (the prologue code and its header), not the table's truth. Phase 3 checks the truth by rendering
against Ultimate in fx_render.

Still open, for phase 3:

- c10[12-15] (alpha, scale) against eft's emp1 (set values, cross_f 0x04A65A08).
- Ultimate's local positions against eft's world `v_inWldPos` for emitters that follow (EmtMat / c10 matrices).
- The z / x scale ratio per emitter.
- Which eft colour stream sysVertexColor0Attr is (eft has v_inColor0 / 1).
- The plugin attributes.

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
