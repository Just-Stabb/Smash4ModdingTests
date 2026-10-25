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
| 0x038 | u32 | emitter name (name-table offset) | verified |
| 0x040 / 0x118 / 0x1F0 | TexRes x3 | texture slots 0–2 (below) | verified |
| 0x2CC / 0x2D0 | u32 | key-animation pos / size (into keyanim table) | verified |
| 0x2DC | s32 | primitive index (−1 none) | verified |
| 0x2EC / 0x2F0 | u32 | shader-param size / pos (into sparam table) | verified |
| 0x2F8–0x33C | u32s | small enums (blend, display, z-mode, etc.) — shader-keyed | corpus |
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
| 0x4D4 | 3 × 0x7C | per-slot UV params (scale at +0x34 for slot 0 → 0x508, flipbook / scroll; slot 0's below) | corpus |
| 0x4D5 / 0x4D7 / 0x4D8 / 0x4D9 | u8 | slot 0 flipbook: pattern table used / cells across / cells down / random start cells (a particle starts on a random cell below this, 0x04A54A88) | verified (0x04A5A6AC, 0x04A5A858: the emitter's uniforms) |
| 0x4DA / 0x4DB / 0x4DC | u8 | slot 0 flags (shader feature bits 0x400 / 0x800 / 0x10000 for slot 0) | verified (use) |
| 0x4E0 | 32 × u8 | slot 0 flipbook pattern table | verified |
| 0x500 | u32 | slot 0 flipbook mode: 0 none, 1 life fit, 4 clamp, 2 loop, 3 random (shader bits 0x4 / 0x8 / 0x10 / 0x20 in that order, eft2's; 5 -> 0x10000000, explosions); shader-keyed (no group mixes on / off) | verified (bits) / corpus (names: 1 / 3 / 5 have no frame rate, 2 / 4 do) |
| 0x504 / 0x506 | s16 each | slot 0 flipbook frames a cell / cells (or table entries) | verified |
| 0x508 / 0x50C | 2f | slot 0 UV scale = repeat (1 / 2) / cells (2, 1/2, 1/3, 1/4 seen) | corpus |
| 0x510 | u32 | slot 0 UV animation mode, bits: 1 scroll, 2 scale, 4 rotate (each bit set exactly where its values below are non-neutral; shader-keyed: 8 of 4291 shader groups mix values) | corpus |
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
| 0x310 | u32 | follow type (eft2's numbers): 0 the particle points at the emitter's live matrices (instance +0x84 / +0xB4: follows it), else they are copied at emission (0x04A5C89C, from the instance's +0x12C = this); 1 none, 2 position only. Shader-keyed: no vanilla shader group mixes values (5136 / 2822 / 157) | verified |
| 0x830 | u32 | flags (shader-keyed) | corpus |
| 0x844 | u32 | shader index (into shader table) | verified |

Everything not listed is copied verbatim.

### Complex emitters (header after the simple 0x8BC bytes)

u16s from `+0x8C0`: field flags (bits 0-2 add 0x10 / 0x18 / 0xC-byte field blocks, read at 0x04A5BFF4),
`+0x8C8` child data offset (0x308 bytes), `+0x8CA` field blocks, `+0x8CC` fluctuation (0x20),
`+0x8CE` stripe (0x34), `+0x8D0` total size. The stripe block (eft's own ribbons, types 5 / 6:
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
template) clamped, × the vertex colour on a mesh, then rgb × `u_nwColorHdrRange` (CB9 [8]: × .x
+ .w). Robin's `fire1` (shader 95, layout 0, 1, 3, 9, 10) is Ultimate's fire combiner: texture 0
offsets texture 1's UVs (distortion, × CB2 [12].xy × semantic 3's .w), colour by texture 1 × 2's
rgb, alpha by their red.

Replacing only the pixel program (block 7; the header's GPR count and program size updated, its
inputs, samplers and uniform blocks kept) leaves the emitter's vertex program (particle type,
flipbook, UV animation) as the template's: `tools/eft_pixel.py` writes eft2's combiner this way for
every converted emitter (`tools/eft_pixel_test.py` checks each variant against the formula).

## Primitive table (meshes; authoring: `Ptcl.add_primitive`)

`+0` u32 count, `+4` u32 total size, `+8` u32 entry offset (0xC); then count entries of 0x50: five
attributes of (u32 float count, u32 components, u32 offset, u32 byte size): position (3), normal
(3), colour (4, RGBA 0-1), UV (4: two UV sets), index (1, u32, triangle list). Offsets are from the
data after the entries; values big endian. An absent attribute is four zeros (Zelda's quad has no
colour). Emitter 0x2DC indexes the table ("Primitive Index is Error" if out of range); vanilla
draws meshes with particle types 0 / 2 / 3 / 4 (the type orients the mesh as it would a quad).

## Key-animation and shader-parameter tables

Opaque blobs; emitters reference ranges by pos/size (0x2CC/0x2D0, 0x2F0/0x2EC). Cloned
emitters share their source's ranges.

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
