# vfx_trace: recording Ultimate's particle engine (OpenSmash-Ultimate)

[OpenSmash-Ultimate](https://github.com/OpenSmash-Ultimate/ssbu-recomp) runs Ultimate (13.0.4 / 13.0.5) as
a native Windows program. Its hook table lets a mod DLL wrap any function of the game's main executable.
`tools/opensmash/vfx_trace.cpp` wraps two functions of eft2 (nn::vfx) and writes what the engine computed
to `vfx_trace.bin`. `tools/vfx_trace.py` reads that file and checks `tools/fx_render.py` against it, so
the renderer's Ultimate side can be made to match the engine itself rather than footage.

## Running it (Windows, OpenSmash 13.0.4)

1. Put `vfx_trace.dll` in a folder of its own, e.g. `C:\vfxtrace`.
2. Start the game from a command prompt in the OpenSmash folder:
   ```
   set SSBU_MODS=C:\vfxtrace
   set VFX_TRACE_SETS=PZenigame
   "Play SSBU.bat"
   ```
   The log shows `[vfx_trace] hooks installed`, and the output path.
3. Play the moves (e.g. Training with Squirtle: forward smash and down smash, facing both ways), then
   close the game normally. The file is `C:\vfxtrace\vfx_trace.bin` unless `VFX_TRACE_OUT` names another.

Settings: `VFX_TRACE_SETS` (comma-separated, case-insensitive parts of effect-set names, e.g.
`PZenigame,Brave`; `*` everything), `VFX_TRACE_OUT` (file), `VFX_TRACE_MB` (stop at this size, default 400).
Only emitters of matching sets cost anything: other emitters are passed through untouched.

Building: on Linux, `tools/opensmash/build_vfx_trace.sh <ssbu-recomp checkout> <out folder>` (clang + lld,
no Windows SDK: it declares the few kernel32 functions it uses). On Windows, the port's own tool also
builds it: `python fighter_sdk\tools\build_mod.py vfx_trace.cpp C:\vfxtrace`.

## What is recorded

Hooked functions (offsets in main; the game at 0x7100000000):

| offset | function | record |
|---|---|---|
| 0x89BD0 | one emitter's frame (x0 system, x1 emitter instance): emission, then the particles' update | after it: `E` (the emitter), `P` (each live particle) |
| 0x8FBE0 | one particle's initialisation (x1 instance, x5 particle arrays, w6 slot, w7 number in this emission) | after it: `B` (the particle as born) |

Once: `S` (an emitter's set name, emitter name, calc type, follow type) and `T` (the engine's table of 512
random vectors, used by the emission shapes).

Emitter instance fields (from main.bin; the ones recorded):

| offset | |
|---|---|
| +0x1c | particles emitted so far (each particle's id) |
| +0x28 / +0x230 / +0x234 | slots in use / slots / next slot |
| +0x44, +0x48 | time |
| +0x50 - +0x6c | emission timers and scales (+0x54 timer, +0x5c threshold) |
| +0x78 | emitter set; +0xa0 emitter data (the VFXB EMTR binary: +0x10 name, +0x7f0 emission, ...) |
| +0xaa | random-vector index (u16, & 0x1ff) |
| +0xac | random state: x = x * 0x41C64E6D + 0x3039, a uniform number x / 2^32 |
| +0xb0 | particle records, 32 bytes: +0 id (0 free), +8 birth time, +0xc life |
| +0xc0 / +0x1d0 | particle arrays of a GPU / CPU emitter (calc_type, data +0x752) |
| +0x340 | world matrix, 4 columns (translation +0x370) |
| +0x3c0 / +0x3d0 | previous position / this frame's movement (distance emission) |
| +0x600 / +0x60c / +0x618 | EAES / EAER / EAET values |

Particle arrays (a pointer each, 16 bytes a particle): +0x00 position (w: life), +0x08 velocity (w: birth
time), +0x10 its copy, +0x18 scale, +0x20 four random numbers, +0x28 rotation, +0x30 / +0x38 colour 0 / 1
(may be absent), +0x40 / +0x48 / +0x50 the emitter matrix at birth (rows). A GPU emitter's arrays hold the
particles as born; the GPU works out the rest each frame, so `P` records only change for CPU emitters.

The set's name is found by scanning back from the emitter data to its ESET section (the section's size
covers its emitters; the name is at its binary + 16).

## Reading it

```
python3 tools/vfx_trace.py summary vfx_trace.bin
python3 tools/vfx_trace.py dump vfx_trace.bin splash1 --set WaterSmash --particles
python3 tools/vfx_trace.py births vfx_trace.bin pzenigame --set WaterSmash
python3 tools/vfx_trace.py json vfx_trace.bin out.json
```

`births` compares the particles born each frame with fx_render's Ultimate side for the same emitter.
Next: compare positions, velocities, sizes and rotations at birth (they depend on the random state, which
the trace records, so they can be matched exactly), then per-frame motion for CPU emitters.
