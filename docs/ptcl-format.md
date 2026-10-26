# Smash 4 (Wii U) particle files: `.ptcl` (EFTF v0x42)

NintendoWare for Cafe "eft" particle resource, e.g.
`fighter/<name>/effect/<name>/<name>.010d0000.ptcl`. Big-endian except three little-endian
totals in the header. Reader / writer: `ptcl.py` (same folder).

Confidence tags used below:
- **verified**: holds on all 117 vanilla fighter files (byte-exact round trip) and/or the runtime
  code reads it that way (`cross_f.rpx`, resource constructor 0x04A6CD18–0x04A6D6EC).
- **corpus**: inferred from the values across the 8115 emitters of the corpus (`field_stats.txt`).
- **guess**: by analogy with NintendoWare eft; unconfirmed.

## File layout (verified)

```
0x00   header (0x48)
0x48   emitter set records (0x1C each, nsets)
       per set, in set order: its emitter table (0x10 x count), then its emitters' data
       zero padding to tex_pos
tex    texture table (GX2 surfaces, raw)
names  name table (NUL-terminated ASCII), zero padded so the shader table is 16-aligned
shader shader table
       zero gap (align16(end + 4) in vanilla)
keyanim key-animation table
       zero gap (same rule)
prim   primitive table
       zero gap (same rule)
sparam shader-parameter table
```

Vanilla `tex_pos` is 0x2000-aligned (the writer keeps the original position unless the emitter
area changed size, then re-aligns to 0x2000). The runtime only checks the resource buffer is
128-byte aligned ("resource memory must be 128 byte alignment").

Quirk (verified, 9 files: FinGameWatch, FinKoopa, FinLucina, lucina, FinMarth, marth,
metaknight, FinWario, FinWiifit): when the shader-param table is empty the file ends 4 bytes
before `sparam_pos` (the last gap is cut short). The writer reproduces this.

## Header (0x48, verified)

| off  | type | meaning |
|------|------|---------|
| 0x00 | char[4] | `EFTF` |
| 0x04 | u32 | version, 0x42 (runtime refuses others: "Binary Version Error") |
| 0x08 | u32 | number of emitter sets |
| 0x0C | u32 | file name, offset into the name table |
| 0x10 | u32 | name table pos (absolute) |
| 0x14 / 0x18 | u32 | texture table pos / size |
| 0x1C / 0x20 | u32 | shader table pos / size |
| 0x24 / 0x28 | u32 | key-animation table pos / size |
| 0x2C / 0x30 | u32 | primitive table pos / size |
| 0x34 / 0x38 | u32 | shader-parameter table pos / size |
| 0x3C | u32 **LE** | texture table size |
| 0x40 | u32 **LE** | total GFX2 shader binary bytes (shader size − binaries base − 0x78·count) |
| 0x44 | u32 **LE** | sum of all emitter data sizes |

(The LE totals look like build-tool statistics; the runtime constructor does not read them, but
the writer recomputes them.)

## Emitter set record (0x1C, verified)

| off | meaning |
|-----|---------|
| 0x00 | user data (u32) |
| 0x04 | "updated"/runtime word (u32, kept) |
| 0x08 | name, offset into the name table — this is the name the `.efc` / ACMD refers to |
| 0x0C | runtime pointer slot (stored as found) |
| 0x10 | emitter count |
| 0x14 | emitter table pos (absolute) |
| 0x18 | runtime pointer slot (stored as found) |

## Emitter table entry (0x10, verified)

`+0` emitter data pos (absolute, 0 = none), `+4..+0xC` runtime slots (kept).

## Emitter (verified sizes)

- `type` (u32 @0) = 0 simple: 0x8BC bytes (6421 in the corpus).
- `type` = 1 complex: 0x8BC base + complex header at 0x8BC; total size at **0x8D0** (1604 emitters,
  all match). Complex header 0x8BC = flags (bit 0: has child emitter → child block at 0x8D4, with
  its own TexRes at **0x920**; other bits: fields, fluctuation, stripe sub-blocks). Sub-blocks
  are kept opaque by the tool (copied with the emitter).
- 90 emitters are followed by zero padding which the tool keeps.

### Emitter fields (`FIELDS` in ptcl.py)

| off | type | name | conf |
|-----|------|------|------|
| 0x000 | u32 | type (0 simple, 1 complex) | verified |
| 0x004 | u32 | flags | corpus |
| 0x008 | u32 | random seed (0xFFFFFFFF random) | guess |
| 0x00C - 0x037 | | eft's user data, read by the game's user callback 0x034 (the eft runtime keeps the matching callback set at instance +0x170, 0x04A55B60). Callback 1 is an effect light shining on fighters (vanilla: every `pointlight*` and ~90 flares): 0x00C top half the flags (bit 0 set; 0x09 - 0x3D), 0x010 0 (0x10101010 with 0x00C's low half 0x1010 on some), 0x014 - 0x01C colour (0 the particle's), 0x020 radius x the particle's scale (FliesUp flare1: 0.5 x 30). Ultimate's custom action 1 (CADP: u32 flags, colour, radius, a factor) is the same light: the common effects both games have match (FliesUp 0x1B / 0.5 in both; SpecialSpeedUp 15 x 1.3 / 0.5 x 30), Smash 4 without the flag bits from 0x20 up; its factor has no slot here. Callback 2 (34 vanilla emitters, user data 0) is unknown | corpus |
| 0x038 | u32 | emitter name (name-table offset) | verified |
| 0x040 / 0x118 / 0x1F0 | TexRes x3 | texture slots 0–2 (below) | verified |
| 0x2CC / 0x2D0 | u32 | key-animation pos / size (into keyanim table) | verified |
| 0x2DC | s32 | primitive index (−1 none) | verified |
| 0x2EC / 0x2F0 | u32 | shader-param size / pos (into sparam table) | verified |
| 0x2F8–0x33C | u32s | small enums (blend, display, z-mode, etc.) — shader-keyed | corpus |
| 0x32C–0x33C | 5 u32 | per-particle hooks (0x04A627A0: function tables, 0 none); 2 = by key animation, only ever on key-animated emitters (it reads the key table: null once the table is dropped, a crash at 0x04A5E154); 1 everywhere else | verified (calls) / corpus |
| 0x324 | u32 | blend: 0 alpha (normal), 1 additive, 2 subtract. Not shader-keyed: 352 of 5366 (file, shader) pairs use more than one; emitters named `*_alpha` are 0 (273 of 280), `*add*` mostly 1 | corpus |
| 0x340 | u32 | volume type (0 point, 1 circle (XZ plane, radius x / z), 2 circle (same divide), 3 circle fill, 4 sphere, 7 sphere fill, 8-9 cylinder, 10-11 box, 12-13 line, 14 rectangle: names and radii in the corpus fit NintendoWare's order) | corpus |
| 0x348 | 3f | volume radius | corpus |
| 0x354 / 0x358 | f | volume sweep start / param | corpus |
| 0x3D8 | 12f | emitter matrix, 3 rows of 4: Rz·Ry·Rx(rotation)·diag(scale), translation in the 4th column (all 8115 vanilla emitters agree; `Ptcl.set_emitter_srt` writes it with the three below) | corpus |
| 0x408 / 0x414 / 0x420 | 3f each | emitter scale / rotation (radians) / translation | corpus |
| 0x444 | f | emit rate | corpus |
| 0x2FF | u8 | one-time: 1 = emits only until end frame, 0 = until killed. All 7982 vanilla emitters: 1 exactly when the end frame is finite. The particle buffer (128 bytes a particle, emitter +0x310, count +0x6C; 0x04A5BDCC) is sized ((end − emit start) / (interval + 1) + 1) × rate when set, else (life / (interval + 1)) × rate + rate: one-time with end 0x7FFFFFFF overflows it (Kamehameha test 4 crashed) | verified |
| 0x448 | s32 | start frame (after the set starts) | corpus |
| 0x44C | s32 | emit start: first emission, frames after the start frame | verified (0x04A6507C) |
| 0x450 | s32 | end frame: with one-time, emission stops this many frames after the start frame (a duration: 49 vanilla emitters have it below their start frame); 0x7FFFFFFF without | verified (0x04A64F70) |
| 0x454 / 0x458 | s32 | emit interval / random | corpus / guess |
| 0x45C | f | figure (omni) velocity | guess |
| 0x460 | f | emitter (directional) velocity | verified (read as float) |
| 0x464 | f | initial velocity random | guess |
| 0x468 | 3f | emit direction | corpus |
| 0x474 | f | dispersion angle (deg) | corpus |
| 0x478 | 3f | spread vector | guess |
| 0x484 | f | air resistance (velocity × this per frame) | corpus |
| 0x4A4 | 3f | gravity | corpus |
| 0x4B0 / 0x4B4 | s32 | particle life / random (frames) | verified |
| 0x4BC | u32 | particle type (billboard / polygon / directional / stripe…) — shader-keyed | corpus |
| 0x4D0 | f | camera offset: the static uniforms' vec4 36 .z (`rotBasis` is .xy; 0x04A5AB04), every vertex program then moves the clip-space z by -offset × (1 − z/w): positive draws the particle in front of what's near it. Vanilla: 5, 1.5, 3, 1, -3, -5, 10 ... (the same units as eft2's `offset`, Bounce's barrier 10) | verified (fill, programs) |
| 0x4D4 | 3 × 0x7C | per-slot UV params (scale at +0x34 for slot 0 → 0x508, flipbook / scroll; slot 0's below) | corpus |
| 0x4D5 / 0x4D7 / 0x4D8 / 0x4D9 | u8 | slot 0 flipbook: pattern table used / cells across / cells down / random start cells (a particle starts on a random cell below this, 0x04A54A88) | verified (0x04A5A6AC, 0x04A5A858: the emitter's uniforms) |
| 0x4DA / 0x4DB / 0x4DC | u8 | slot 0 flags (shader feature bits 0x400 / 0x800 / 0x10000 for slot 0) | verified (use) |
| 0x4E0 | 32 × u8 | slot 0 flipbook pattern table | verified |
| 0x500 | u32 | slot 0 flipbook mode: 0 none, 1 life fit, 4 clamp, 2 loop, 3 random (uboFlag bits 0x4 / 0x8 / 0x10 / 0x20 in that order, eft2's; 5 -> 0x10000000, explosions; 0x04A5A858). Read by the CPU; every vanilla vertex program that plays flipbooks tests all five bits, so any of them plays any mode (no group mixes on / off: a program with no flipbook can't play one) | verified (bits, programs) / corpus (names: 1 / 3 / 5 have no frame rate, 2 / 4 do) |
| 0x504 / 0x506 | s16 each | slot 0 flipbook frames a cell / cells (or table entries) | verified |
| 0x508 / 0x50C | 2f | slot 0 UV scale = repeat (1 / 2) / cells (2, 1/2, 1/3, 1/4 seen) | corpus |
| 0x510 | u32 | slot 0 UV animation mode, bits: 1 scroll, 2 scale, 4 rotate (each bit set exactly where its values below are non-neutral). Read by nothing: not the uniform fill (0x04A5A6AC), no vertex program; a program draws all of a slot's UV animation or none (`tools/eft_vertex.py`; 2900 vanilla slots run a full program under a narrower word) | verified |
| 0x514 / 0x51C / 0x524 | 2f each | slot 0 UV scroll a frame / initial / random | corpus |
| 0x52C / 0x534 / 0x53C | 2f each | slot 0 UV scale a frame / initial (1) / random | corpus |
| 0x544 / 0x548 / 0x54C | f each | slot 0 UV rotation a frame / initial / random (radians) | corpus |

Slot 0's UV transform (GPU particles): scale x (uv x 0x508 repeat / cells - 0.5), turned about the
texture's centre, - shift + 0.5, shift = frame x 0x514 + 0x51C +- 0x524 (random), the same on U and
V and the same as Ultimate's eft2, so `tools/vfxb_to_ptcl.py` copies eft2's values unchanged. Verified:
0x04A5A6AC copies 0x514-0x54C, 0x508 / 0x50C and the cells into the static uniforms' shtAnim0 (pm0
rate u v, initial u v; pm1 random, scale rate; pm2 scale initial, random; pm3 rotation; pm4 repeat,
cells) unchanged, and the vertex programs subtract the shift (shader 142's groups 37-47). An earlier
reading from the vanilla corpus (clamped, shifted meshes landing partly on their texture) had eft
adding it; the converter negated every shift up to Hero's fix 29. (A CPU-side UV path, 0x04A6C26C,
adds U's and subtracts V's rate; no converted emitter uses it.)
| 0x648 / 0x64C | u32 | color0 / color1 type (0 const, 1 random, 2 key anim) | corpus |
| 0x650 / 0x6D0 | 32f | color0 / color1 keys (8 × rgba-ish) | corpus |
| 0x750–0x768 | 2i each | color sections 1–3 (% of life), repeat | corpus |
| 0x778 | f | color scale (brightness; 1.2–1.5 on glows) | corpus |
| 0x784–0x794 | f | alpha init / diffs / sections | corpus / guess |
| 0x7C4 | 2i | scale sections (% of life) | corpus |
| 0x7CC / 0x7D4 / 0x7DC | 2f | scale random / base scale / init ratio | corpus |
| 0x7E4 / 0x7EC | 2f | scale diffs | guess |
| 0x314 | u32 | colour combiner (shader-keyed; read off the vanilla pixel shaders, one per value): 0 colour 0 (alpha = texture red), 1 colour 0 x texture rgb (alpha = texture **alpha**), 2 colour 1 + (colour 0 - colour 1) x texture rgb (alpha = texture red); Cafe eft's COLOR / TEXTURE / TEXTURE_INTERPOLATE (some variants differ: Koopa's `pointlight1`, mode 2 with a self-distortion, takes alpha from alpha). Vanilla BC4 textures select R R R 1 (TexRes +0x14 = 0x00000005), so a shader reading alpha draws alpha 1 over the whole quad with them: write converted shapes R R R R (0x00000000) | verified (disassembly) |
| 0x7F8 / 0x804 / 0x810 / 0x81C | 3f | rotation init / random / velocity / velocity random (rad). Drawn only by a shader whose vertex program has the `v_inRot` attribute (all 3165 vanilla emitters with a rotation have one; without it the particle is unturned). A mesh shader builds R = Rx·Rz·Ry from it (Y, then Z, then X; column vectors, after the particle scale), unlike the emitter's Rz·Ry·Rx | corpus / verified |
| 0x828 | f | rotation attenuation | corpus |
| 0x82C | f | fade rate: while the emitter set fades (turned off), the emitter instance's alpha (+0x58) drops by this x the frame step, the emitter (with its particles) ending at the threshold; otherwise it climbs back by it (1 / frames: 1/11, 1/4, 1/7...; set on vanilla's infinite-life emitters, the only way they end; 0 on 84% of the rest) | verified (0x04A64F00, 0x04A661D8) |
| 0x2F8 | u8 | read with the gravity vector (0x4A4) at 0x04A62620 | verified (use) |
| 0x2F9 | u8 | stop emitting while the set fades (eft2's is_fade_emit): the emitter calc 0x04A65034 skips emission when fading only if this is set; with it 0 and 0x82C 0 a turned-off emitter emits on for good | verified |
| 0x2FC / 0x2FD / 0x2FE | u8 | random rotation direction per axis X / Y / Z: at emission (0x04A5DBCC) a random roll negates that axis's initial rotation and rotation speed | verified |
| 0x310 | u32 | follow type (eft2's numbers): 0 the particle points at the emitter's live matrices (instance +0x84 / +0xB4: follows it), else they are copied at emission (0x04A5C89C, from the instance's +0x12C = this); 1 none, 2 position only. No vanilla shader group mixes values (5136 / 2822 / 157), but one vertex program serves all three (positions come in as `v_inWldPos`), save those reading the live emitter matrix (`emm`), whose emitters all follow (0; 2 with `v_inEmtMat` too) | verified |
| 0x830 | u32 | flags (shader-keyed). Byte 0x831 is the shader's mode, the same as the low byte of its key record's first word: 0 / 4 / 8 draw colour (CB9's colours); 5 and 6 write a screen offset (x 1/960, 1/540, from CB4) for the distortion pass, not a colour (mode 5's 7 vanilla emitters are all refraction parts, Bayonetta's `ciecle1_rif` and Shulk's `rifraction2`; mode 6's 3 Ryu's and Robin's Final Smash `rifraction1` / `buller1`); 7 Fox / Falco's Illusion. A pixel program of a mode-5 template replaced by a colour one still draws in that pass: the colour bends the picture behind it (Hero fix 33's lens) | corpus / verified (disassembly) |
| 0x844 | u32 | shader index (into shader table) | verified |

Everything not listed is copied verbatim.

### Complex emitters (header after the simple 0x8BC bytes)

`+0x8BC` u32 (0xC00050 on every vanilla complex emitter without a child), then u16s from `+0x8C0`:
field flags, fluctuation flags (bit 0 on; 0xE when off), stripe flags, pad, `+0x8C8` child data offset
(0x308 bytes), `+0x8CA` field blocks, `+0x8CC` fluctuation (0x20), `+0x8CE` stripe (0x34), `+0x8D0`
total size (`Ptcl.with_fields` rebuilds the 95 vanilla field-only emitters byte for byte).

The field blocks follow each other in flag-bit order (`ptcl.FIELD_BLOCKS`, big endian). cross_f 0x04A62E4C
runs them each frame on the CPU's particles (0x04A6E56C random, 0x04A6E6EC magnet, 0x04A6EB3C spin,
0x04A6EFC4 collision, 0x04A6F90C convergence, 0x04A6FD40 position add, 0x04A610AC curl noise);
0x04A5AF90 also copies them into the vertex programs' uniforms (`fieldRandomParam` vec4 67 ...
`fieldCurlNoise1` 75), but the only vanilla GPU programs (`v_inVec`) reading any read spin (72) and
magnet (71): fields need the CPU's particles.

| Bit | Field | Size | Layout |
|-----|-------|------|--------|
| 0 | random | 0x10 | s32 interval, vec3 velocity (every interval frames velocity += rand x it) |
| 1 | magnet | 0x18 | f power, vec3 position, u32 axes (x 1, y 2, z 4), u8 follows the emitter |
| 2 | spin | 0x0C | u32 rate (2^32 = 360 degrees a frame), u32 axis (0-2), f outward speed |
| 3 | collision | 0x14 | u8 type, u8 world, f plane, f bounce, s32 count (-1), f friction (read at 0x04A5BFF4) |
| 4 | convergence | 0x14 | u32 0 (to the position) / non-zero (to the emitter; vanilla 0x01000000), vec3 position, f ratio |
| 5 | position add | 0x10 | vec3, u8 world |
| 6 | curl noise | 0x24 | u8, u8, 2 pad, f, vec3, vec3, f (uniforms: vec4 74 = the first vec3 and f, 75 = the second and the last f) |

Fluctuation (`+0x8C2` flags, `+0x8CC` a 0x20-byte block; `ptcl.FLUCT_FMT`): cross_f 0x04A622C4 on the
CPU's particles, `flucX` / `flucY` (vec4 34 / 35) on the GPU's, which only the 128 vanilla emitters' GPU
programs reading them draw. Flags: bit 0 on, 1 alpha, 2 scale, 3 / 4 / 5 the wave (one of three
128-entry tables at 0x1046D830 ...), 6 scale y from the second channel (else the first's). Each
channel: f amplitude, f 128 / cycle (frames), u32 random phase (a random cycle's worth), f phase
(frames); the value 1 - table[(age + phase) x 128 / cycle & 127] x amplitude multiplies alpha / scale.
Ultimate's (emitter `fluc` flags, `static` amplitude / cycle / phase_rnd / phase_init for x and y) is the
same: its wave types are the same bits (8 / 16 / 32), and Bayonetta's flares and bats agree in both
games (`vfxb_to_ptcl.fluctuation`; Ultimate's phase is taken as degrees of the cycle, unverified).

Per-particle key animations (targets above 0x1B, see the key-animation section) animate them: 0x1C - 0x1E
the random velocity, 0x1F magnet power, 0x20 spin rate (keyed as an int, the block's units), 0x21 spin
outward speed, 0x22 convergence ratio, 0x23 - 0x25 position add.

Ultimate's fields are the same with their own sections (little endian; main 0x8CB00 reads the tags,
0x955F0 runs them on the CPU) and 37-word 8-key animations (on, loop, random, key count, period 100,
then 8 keys of x, y, z, time 0 - 1 of the life; 0x93C80): FRN1 = random (velocity, interval, its
animation at word 4), FMAG (bytes follow / x / y / z, power, position, animation at word 5), FSPN (rate in
radians, axis, outward; the rate's animation at word 3 in degrees and replacing it, the outward speed's at
word 40 x pi / 180 as Ultimate's code does), FCOV (type, position, ratio, animation at word 5), FCLN (the
curl noise's numbers reordered: eft's f = word 7, first vec3 = words 4 - 6, second = 1 - 3, last f =
word 8; flags bytes 0 / 1 the same). FRND (eft2's sine-noise random) and FCOL aren't mapped yet. The stripe block (eft's own ribbons, types 5 / 6:
90 / 31 vanilla) is 13 words: type, option, connect, texture coordinates, history length,
divisions, start / end alpha (f), UV scroll (2f), history step, history / direction interpolation (f).

## TexRes (0xD8; only the first 0x38 bytes are stored, the rest are runtime zeros) — verified

| off | meaning |
|-----|---------|
| 0x00 | u16 width, u16 height |
| 0x04 | GX2 tile mode (4 = 2D thin1 in vanilla) |
| 0x08 | swizzle (0) |
| 0x0C | sampler: U wrap in bits 24-27, V wrap in 28-31 (eft's codes, as eft2's: 0 mirror, 1 repeat, 2 clamp; every vanilla 2 x 2 repeat is 0x0, mirroring a quarter texture into a whole; the axes from the 374 vanilla emitters repeated along U only (0x508 = 2, 1): bits 24-27 always 0 there, 28-31 0 / 1 / 2), 0x100 filter (vanilla: 0x100, 0x22000100, 0x11000100...) |
| 0x10 | mip levels |
| 0x14 | component selector (one byte per output channel: 0 R 1 G 2 B 3 A 4 zero 5 one; BC4 = R,R,R,1; BC5 = R,R,R,G) |
| 0x18 | enable mip level (f) |
| 0x1C | mip bias (f) |
| 0x20 / 0x24 / 0x28 | original format / pos / size (source image, usually format 2 RGBA8, pos 0) |
| 0x2C / 0x30 / 0x34 | native format / size / pos (into the texture table) |

eft format → GX2: 2→0x1A RGBA8, 3→0x31 BC1, 5→0x32 BC2, 7→0x33 BC3, 9→0x34 BC4, 11→0x35 BC5
(even numbers 4/6/8/10/12 = sRGB/SNORM variants 0x431, 0x432, 0x433, 0x234, 0x235).
Surfaces: tile mode 4, pitch aligned to 32 elements, rows to 16; decoded with `tools/nut.py`'s
GX2 addressing. Native textures start 0x800–0x2000-aligned in the table (per format). Runtime
errors "Texture Binary is None" / "Child Texture Binary is None": slot 0 (and a child's slot 0)
must have a texture.

## Shader table (verified structure)

```
+0x00 u32 count
+0x04 u32 table size
+0x10 u32 binaries base (offset in the table)
+0x14 u32 entries offset (= base + binaries length)
base: GFX2 ("Gfx2") vertex+pixel shader binaries, 0x100-aligned
entries: count × 0x78 key records; +0x68 binary size, +0x6C binary offset (from base)
```

The runtime builds one 0x6E8-byte shader object per entry at load. Emitters choose one by
index (0x844); the key record encodes the emitter configuration the shader was generated for.

## Pixel programs (verified: disassembly of the corpus' 1336 distinct shaders)

Each shader binary is a GX2 file: vertex header (block 3) + program (5), pixel header (6) +
program (7). The pixel inputs are named by GX2 semantic (pixel header word 4 = count, words 5+ =
`SPI_PS_INPUT_CNTL`, semantic in the low byte), in register order R0, R1, ...:

| semantic | contents |
|---|---|
| 0 | colour 0: rgb the colour track 0, a the alpha track |
| 1 | colour 1 (rgb) |
| 6 | a mesh's vertex colour (rgb and a multiply in) |
| 9 / 10 | texture coordinates: slot 0 in .xy and slot 1 in .zw of one of them, slot 2 in the other's .xy (which is which varies with the vertex program: slot 0 reads 9 in 766 shaders, 10 in 450) |
| 3, 2 / 5, 11, 12 | view / depth (soft particles, fresnel), the flipbook cross-fade (FRACT of a cell index, texture arrays) |

The common programs (layout 0, 1, 9: 469 shaders; 0, 1, 6, 10: 271) are: sample slot 0, colour =
colour 1 + (colour 0 − colour 1) × texture rgb, alpha = colour 0 alpha × texture red (or alpha, by
template) clamped, × the vertex colour on a mesh, then rgb × `u_nwHdrRange` (CB9 [8]: × .x
+ .w; `userUniformBlock`, the game's: `u_nwColorHdrRange` is [9]). Robin's `fire1` (shader 95,
layout 0, 1, 3, 9, 10) is Ultimate's fire combiner: texture 0 offsets texture 1's UVs
(distortion, × CB2 [12].xy × semantic 3's .w), colour by texture 1 × 2's rgb, alpha by their red.

Premultiplied programs: a shader whose key record has bit 0x40 in its word +0x40 (the shader
object's +0x4BC; the 0x78 record is copied to +0x47C) is drawn by shader mode 4's draw callback
(the game's, cross_f 0x032F4814: per mode, registered at 0x032F4B8C) with blend ONE /
INV_SRC_ALPHA (alpha ZERO / INV_SRC_ALPHA), whatever the emitter's blend (0x324), and its program
premultiplies: rgb × hdr × 2 (`MULADD_M2`) × alpha. All 543 vanilla programs with the bit do, none
without it (all mode 4: 543 of its 774). A replacement program on such a template must
premultiply too: unmultiplied, its colour is added at full strength over the whole shape and only
the picture behind is scaled by alpha (Hero's glow discs, fix 33 - 42: flat orbs to the mesh's
rim, rgb saturated where alpha was 0.005). The emitter's blend 0 (alpha) / 1 (add) both draw
"over" there, as vanilla's do (`impact3`, blend 1).

Replacing only the pixel program (block 7; the header's GPR count and program size updated, its
inputs, samplers and uniform blocks kept) leaves the emitter's vertex program (particle type,
flipbook, UV animation) as the template's: `tools/eft_pixel.py` writes eft2's combiner this way for
every converted emitter (`tools/eft_pixel_test.py` checks each variant against the formula).

Two-texture templates (19 quad and 50 mesh vanilla pixel programs sample slot 0 and slot 1 each
straight from an input, semantic 9 on quads, 10 on meshes: slot 0 in `.xy`, slot 1 in `.zw`) work
out slot 1's coordinates in the vertex program from the same UVs (a mesh's one UV set) with slot 1's
own block (0x550 = 0x4D4 + 0x7C: repeat / cells at 0x584, UV mode 0x58C, scroll / scale / rotation
from 0x590; 0x04A5A6AC copies it into shtAnim1 as slot 0's into shtAnim0). The converter draws a
second Ultimate sampler there, live (`live_sampler`), when it moves apart from the main one.

## Vertex programs (`tools/eft_vertex.py`)

The GX2 vertex header names the uniform blocks (CB1 `viewUniformBlock`, CB2
`emitterStaticUniformBlock`, CB3 `emitterDynamicUniformBlock`), uniforms and attributes; its
`SQ_VTX_SEMANTIC` words map input GPRs (R1 on) to attribute locations (attributes are declared only
where read). CB2 vec4s: 0 `uboFlag`, 1-15 `shtAnim0-2.pm0-pm4` (the per-slot UV block below), 16 /
25 `ptnAnm0 / 1` (frames a cell, cells, random start cells; tables after), 36 `rotBasis`, 46-61
`col0 / col1` keys, 76-78 `u_shaderParam*`. The uniform fill (0x04A5A6AC, a slot at a time from the
emitter's 0x4D4 + 0x7C x slot): pm0 = scroll a frame, scroll initial; pm1 = scroll random, scale a
frame; pm2 = scale initial, scale random; pm3 = rotation a frame, initial, random, the slot (its
random channel); pm4 = repeat / cells (0x508), cells across / down; uboFlag 0x400 << 2 x slot /
0x800 << 2 x slot from the slot's inverse-random bytes (0x4DA / 0x4DB).

Vertex programs declaring `userUniformBlockParam` (CB4, 8 vec4s the game fills: a light's
direction and colour, ambient) light their particles: colour x max(normal . light, 0) x the light's
colour + ambient (Mario's fireball smoke, Dedede's swing smoke; 245 vanilla emitters, all shader mode
4, the other 798 of mode 4 unlit): flames on them burn dark away from the light.

What a template draws is read from its program, not its mode words: the UV animation of each slot
(all or none), whether it plays a flipbook (any mode), the follow types it draws right, `v_inRot` /
`v_inVec`, and whether it reads the shader parameters (162 of 675 vanilla programs: a template
with parameters its program doesn't read is plain once its pixel program is ours). No vertex
program reads the colour keys: colour animation is the CPU's (`v_inColor0` / `v_inColor1`).

### Grafts (`tools/eft_vertex.py` graft_uv1, graft_rot)

Code of our own goes into a vanilla vertex program as extra ALU clauses (assembled by latte-asm),
the program's own clauses untouched. The control flow (CF) words are little-endian pairs: an ALU
clause has word 1 bits 29:28 = 2 / 3, its code address (64-bit units) in word 0 bits 21:0; other
instructions a 7-bit opcode in word 1 bits 29:23 (1 / 2 / 3 TEX / VTX clauses, word 0 their code
address; 4 - 18 loops, jumps, else, pop, call, word 0 a CF index; 19 CALL_FS; 39 / 40 EXP /
EXP_DONE: word 0 bits 12:0 the array base (PARAMn: n), 14:13 the type (1 position, 2 parameter),
21:15 the GPR, word 1 bits 20:17 the burst count, bit 21 END_OF_PROGRAM). The CF list is padded
before the first clause (vanilla: 32+ slots); the GX2VertexShader header's SQ_PGM_RESOURCES_VS
(word 0, NUM_GPRS in bits 7:0) and program size (word 52) follow the program; SPI_VS_OUT_ID
(words 4 - 13) gives each parameter's semantic (PARAM 4n + k in byte k of word 4 + n).

What every vanilla program exports in the texture coordinates' parameter: slot 0's UV in .xy and
slot 1's in .zw, animated where the program has slot 1's UV animation, else still (x slot 1's
repeat, inverse-random flips done): a one-texture program computes it and nothing reads it. The
particle's age: `v_inWldPos.w` on the CPU's particles; on the GPU's (programs reading `v_inVec`)
`.w` is its birth and the age emitterDynamicUniformBlock vec4 2 .x less it (438 / 301 graftable
vanilla programs, no exception). eft's UV transform of a slot (fitted against vanilla clauses run
through an interpreter, `tools/eft_vertex_test.py`; r the random channel pm3.w picks): shift =
age x rate + initial + random x (1 - 2r), scale likewise, a = -(age x turn rate + initial +
random x (1 - 2r)); a mesh: u' / v' = the still UV - 0.5, U = scaleU (cos a u' - sin a v') -
shiftU + 0.5, V = scaleV (cos a v' + sin a u') - shiftV + 0.5; a quad (corner x, y = U / repeat
- 0.5, 0.5 - V / repeat; turned to Ru, Rv): U = Ru (repeat - 1 + scaleU) + repeat / 2 - shiftU,
V = Rv (1 - scaleV - repeat) + repeat / 2 - shiftV.

The slot-1 graft: after CALL_FS a clause saves the age and `v_inRandom` in GPRs past the program's
own (the inputs' GPRs are reused later); before the texture coordinates' EXP a clause works out
slot 1's animated UV from the still one in .zw into a fresh GPR, which the EXP then exports. With a
`textureSampler1` (2D, location 1) added to the pixel header (its relocation table: '}BLK' with
the data and text regions and the pointer patch list, 0 entries for null pointers, extended) and
the shader key's texture count set, the program draws a second texture: 739 vanilla one-texture
programs take the graft (all checked: their clauses unchanged, jumps moved, the export re-pointed,
the relocation table whole); the few that already animate slot 1 need only the sampler. The shader key
(0x78 record) is copied to the shader object at +0x47C (cross_f 0x04A5779C): key byte 0x29 = the
textures past the first (eft looks up textureSampler1 / 2, by name through the relocated
pointers, 0x04A59E54, only for them; 5397 vanilla keys all match their pixel samplers), 0x3B /
0x3C slot 0 / 1 a texture array (textureArraySampler).

The slot-2 graft (graft_uv1 with a second semantic): one-texture programs work out nothing of slot
2, so its still UV is slot 1's / slot 1's repeat x slot 2's (CB2 vec4 10 / 15; slot 1's
inverse-random flips kept), animated by a third clause on shtAnim2 (vec4 11 - 15) and exported in
.zw of a new parameter: an EXP (opcode 39, type 2, the next PARAM index, barrier) just before the
texture coordinates', SPI_VS_OUT_CONFIG's VS_EXPORT_COUNT (bits 5:1, the count - 1) and
NUM_SPI_VS_OUT_ID (words, 4 parameters each) raised, the semantic (0x0B on, one the program doesn't
use) in its SPI_VS_OUT_ID byte (unused bytes 0xFF). The pixel header takes it as a new input: the
input count (word 4) and SPI_PS_IN_CONTROL_0's NUM_INTERP (bits 5:0) raised, its SPI_PS_INPUT_CNTL
entry the texture coordinates' with the semantic swapped (0x100 | semantic). With
`textureSampler2` and key byte 0x29 = 2 it draws a third texture. eft2's texture blends
(tex1 / tex2): 0 multiply, 1 add, 2 subtract (t - texture n: Ultimate's own program for Hero's
ChantFinish light1, alpha = t0 x t1 - t2).

The rotation graft (graft_rot): eft's turning mesh programs work out R (S (pos + rotBasis)), S the
particle's scale (`v_inScl` x / y; z by x, or by y where uboFlag has 0x08000000), rotBasis CB2
vec4 36 .xy (z none), R = Rx·Rz·Ry from `v_inRot` (radians; fitted on Little Mac's Final program
through the interpreter, 1e-5); the programs without `v_inRot` work out S (pos + rotBasis) alike.
So a clause after CALL_FS rewrites the position in place, pos' = S⁻¹ R S (pos + rotBasis) -
rotBasis (a zero scale: RECIP_CLAMPED, which the program's own x 0 takes back to 0), and the
attribute comes in through the header: an entry ('v_inRot', type 11 float4, count 0, the next free
location) appended to the attribute array (copied past the data with the relocation table
extended, as for samplers: count / pointer at header word 0xD0 / 4 + 13 / 14), and an
SQ_VTX_SEMANTIC entry (word 16 the count, 17 on each input GPR's location: R1 on) mapping the
location to the GPR after the inputs. eft feeds a stream to every attribute a program's header
names (by name, cross_f 0x04A59FC8; vanilla programs reach 14 attributes). A program takes the
graft when its ALU clauses before the POS0 export (run through the interpreter, branches or not)
give the same POS0 for pos as for S (pos + rotBasis) - rotBasis at scale 1, random inputs, both z
scales: 49 of the 126 vanilla mesh programs without `v_inRot` (the rest scale otherwise, as by
x mirrored on a view-block flag, or lack `v_inScl`), each grafted one checked end to end against
R S (pos + rotBasis), within 2e-6.

Colour 1 is scaled like colour 0: the particle's colour 1 (+0x88) x the set's colour (+0x278) x
the colour scale (0x778) x the emitter instance's colour 1 (+0x238), cross_f 0x04A588CC (colour 0:
0x04A58830).

## Primitive table (meshes; authoring: `Ptcl.add_primitive`)

`+0` u32 count, `+4` u32 total size, `+8` u32 entry offset (0xC); then count entries of 0x50: five
attributes of (u32 float count, u32 components, u32 offset, u32 byte size): position (3), normal
(3), colour (4, RGBA 0-1), UV (4: two UV sets), index (1, u32, triangle list). Offsets are from the
data after the entries; values big endian. An absent attribute is four zeros (Zelda's quad has no
colour). Emitter 0x2DC indexes the table ("Primitive Index is Error" if out of range); vanilla
draws meshes with particle types 0 / 2 / 3 / 4 (the type orients the mesh as it would a quad).
eft's loader (cross_f 0x04A6CF74) reads each attribute at its own offset, so the storage order is
free; an attribute whose offset is 0 counts as absent there (a missing colour is filled with a
constant). `add_primitive` stores them in vanilla's order (position, normal, UV, colour, index,
contiguous: all 825 vanilla meshes) for likeness only. (Hero's fix 42 put the orbs down to the
order; they were the premultiplied blend, "Pixel programs".)

## Key-animation and shader-parameter tables

Emitters reference ranges by pos/size (0x2CC/0x2D0 key animations, 0x2F0/0x2EC shader parameters,
still opaque). Cloned emitters share their source's ranges.

A key-animation range is `b'KEYA'`, a u32 block count, then the blocks (`Ptcl.key_anims` /
`set_key_anims`):

| Offset | Type | Meaning |
|--------|------|---------|
| 0x00 | u32 | key count *n* |
| 0x04 | u32 | interpolation: 0 linear, 1 smoothstep |
| 0x08 | u32 | target (below) |
| 0x0C | u32 | loop: the frame is taken modulo the last key's |
| 0x10 | u32 | 100 (1 on 9 vanilla blocks); not read by the player |
| 0x14 | u32 | 0 (1 on 3 vanilla blocks); not read by the player |
| 0x18 | u32 | block size, 0x1C + 8*n* |
| 0x1C | f32 pairs | keys: frame, value |

Before the first key the value is the first key's; after the last (no loop) the last's (cross_f
0x04A6DA70). Targets above 0x1B are per particle: their blocks are kept at +0x1E8 + 4 x target and read
at frame 100 x age / life (0x04A5E148): the complex emitters' fields (above). The pointer is resolved at load (0x04A5A5A0, into emitter +0x2C8); each frame (0x04A64444)
targets below 0x1C are written into the emitter instance's float array (+0x1EC + 4 x target), over the
defaults 0x04A5C048 sets from the emitter's fields; targets 2, 5 and 8 also flag the emitter matrix for a
rebuild. Higher targets are per particle (the 0x32C hooks).

| Target | Animates | Default |
|--------|----------|---------|
| 0 | emission rate | 0x444 |
| 1 | particle life | 0x4B0 |
| 2-4 | emitter scale | 0x408 |
| 5-7 | emitter rotation (radians) | 0x414 |
| 8-10 | emitter translation | 0x420 |
| 11-13 | colour 0 | 0x384 |
| 14 | alpha | 0x3A4 |
| 15 | all-direction velocity | 0x45C |
| 16 | directional velocity | 0x464 |
| 17-18 | particle scale | 1 |
| 19-21 | colour 1 | 0x394 |
| 22-24 | shape scale | 0x378 |

The colour, alpha and shape-scale defaults (the twelve floats 0x378 - 0x3A7) act as multipliers: the
converter writes 1.0 over all of them (a template's own otherwise: Kaboom's flareBase had a shape scale
of 10) and keys Ultimate's colour / alpha values divided by the emitter's own colours.

Ultimate's emitter animations are the `EA**` subsections (little endian: u8 on, u8 loop, u16, u32 key
count, u32, then keys of x, y, z, frame): EATR 0, EAPL 1, EAES 2-4, EAER 5-7 (degrees), EAET 8-10, EAC0
11-13, EAA0 14, EAOV 15, EASL 17-18, EAC1 19-21, EASS 22-24. EAA1 and EADV have no eft target and stay
unconverted.

## Shaders: which fields are tied to the shader

Across 1484 (shader, file) groups, the bytes that vary in the corpus but never within a group are
listed in `shader_keyed.txt`. The meaningful ones: the enums 0x2F8–0x340, particle type 0x4BC,
the per-slot UV / texture-mode words 0x4D4–0x640 that select features (not the scale values),
flags 0x830, the texture slots' use and channel selection (format class / comp_sel), and
color/alpha *types* (constant vs animated). (Many listed bytes are coincidences from one-emitter
groups.) Free within a group: colors and keys, alpha values, scale, rotation values, velocity,
gravity, life, emission rate/frames, volume size, UV scale, texture image (same format class).

So: a new emitter cloned from a template keeps the template's shader index and works as long as
those keyed fields stay as in the template. For a different configuration, pick a template
whose configuration matches, or import a matching shader from another file
(`Ptcl.import_shader`, which copies the 0x78 key record + binary and re-points it).

## Runtime checks (resource constructor 0x04A6CD18 ff.)

Magic and version 0x42; 128-byte buffer alignment; names resolvable; texture slot 0 present
(and the child's); primitive index in range; shader objects built from every entry. `Ptcl.validate()`
mirrors these plus range checks for textures, key animations and shader params. Clean on all 117.

## Not covered / risks

- Nothing written by the tool has been tested in game yet.
- Field names marked corpus/guess may be wrong; the complex sub-blocks (child, fields,
  fluctuation, stripe) are opaque.
- New textures are single-mip; texture placement alignment assumed (0x2000 table, per-format
  surface alignment).
- Shader key records are not decoded field by field; binaries placed 0x100-aligned.
- A new emitter set only plays if the `.efc` lists it (separate research).
