# Custom effects for new fighters

Fully custom effects (our own emitters, textures and effect models) in a new fighter's own effect
bank (`fighter/<name>/effect/<name>/`: `.efc` effect list, `.ptcl` particles (EFTF), `model/Eff*`
effect models; ACMD ids `0x3KKnnnnn`, Supamario `0x341`). Format research in progress: the `.ptcl`
(EFTF) reader / writer and the `.efc` + effect models.

## First: Supamario's Kamehameha

Look (user): **blue, like the original** (Dragon Ball's): a near-white core with a cyan to deep blue
glow around it.
- Charge: a blue energy orb between the hands, growing, with small sparks drawn inward and a soft
  blue glow; white-hot centre.
- Beam: an effect model (a cylinder / tapered beam with a scrolling energy texture: white core, cyan
  edge, blue falloff, additive) from the hands forward, with a wider glow sheath and particles
  streaming along it; a bulbous head at the front.
- Impact: a blue-white burst with a shockwave ring and scattered sparks.

Sounds (user's clips): `kame_charge` (6.2 s, the charge), `basicbeam_fire` (5.7 s, the beam firing),
`beamhead` (3.3 s, the beam head), added to Supamario's own sound-effect bank (its own bank id and
soundlabeltable row, instead of sharing Mario's) and played from the move's ACMD.

Plan: a small self-authored test effect first (prove the chain in game), then the three parts, then
the move (animations, ACMD hitboxes, MSC charge logic).

## Built so far

- Formats: `tools/ptcl.py` (docs/ptcl-format.md), `tools/efc.py` (docs/efc-format.md).
- XV2's own Kamehameha models (Kmh_Fire / Kmh_Bas / Kmh_Hand) converted to effect model folders
  `EffSupamarioKameFire / Bas / Hand`: `tools/xv2_to_nud.py` (docs/xv2-model-conversion.md).
- Supamario's own sound bank: `tools/fighter_own_bank.py` (docs/kind-expansion.md): BINF id 2144,
  soundlabeltable row 3249; Kamehameha sounds `0x0CB1008B` charge, `0x0CB1008C` fire,
  `0x0CB1008D` beam head.
- Chain test (Supamario v5): `PtcSupamarioKameCharge`, a new emitter set built from the fireball's
  8 emitters (blue colour keys, our own 64x64 orb texture, the templates' shaders), `.efc` entry
  `0x16` (effect id `0x03410016`), played from the up taunt (`External_Graphic` at bone 0x11,
  terminated with the animation) with the charge sound.
- v5 in game: a big square sheet over Supamario. The orb texture was BC3 with white colour and
  the shape only in alpha, but the game's fx textures (BC4 / BC5, component-selected R, R, R, 1)
  carry the shape in the colour, which the template shaders read; and it was put on every
  emitter, the refraction ones too (their texture is a distortion map, 128 grey = none).
  Rebuilt with `tools/supamario_kame_fx.py BASE.ptcl OUT.ptcl` (from v4's file): the fireball's
  sparks / ball / flash with their own textures, red and blue swapped in the colour keys; the
  shimmer unchanged; our glow texture as the template's quarter glow (drawn mirrored), BC4, the
  shape in R = G = B; no smoke. Rule for our own textures: match the template slot's format and
  channel layout.

## The Xenoverse 2 Kamehameha port (`000_GOK_KMH.vfxpackage`)

Readers: `tools/xv2vfx.py` (EEPK / EMP / ETR / EMM, docs/xv2-vfx-format.md), `tools/xv2emb.py`,
`tools/xv2model.py`. Converters:

- **Particles**: `tools/xv2_to_ptcl.py PKG BASE.ptcl OUT.ptcl` (the mapping is in its docstring).
  One emitter set per EMP (`PtcSupamarioKmh<Name>`, split at 16 emitters, the most any vanilla set
  has): each EMP emission node becomes an emitter cloned from a template in Mario's file whose
  shader fits the particle type: camera billboards (type 0) from `PtcMarioPumpMax/flare1` (additive)
  or `PtcMarioFireball/PtcMarioFireballSmoke_Copy2` (normal blend), streaks along their velocity
  (type 3, XV2 `AutoOriented_VisibleOnSpeed`) from `PtcMarioSupermant2/line1`, ShapeDraw rings
  (type 1, a polygon turned by the emitter transform, the ring drawn into the texture) from
  `PtcMarioFireballShoot/PtcMarioRireballShoot`. All four: one BC4 texture, no flipbook, colour
  key-animated. Blend (0x324) is set per emitter (it is not shader-keyed). Textures: the
  sampler's first sprite-sheet cell, BC4 with the shape in R, the texture's mean tint moved into
  the particle colour. Timing: the XV2 spawn tree (bursts, frequencies, loops, `MaxInstances`)
  is simulated and eft's start / end / interval / rate fitted to the spawn frames. Curves (colour,
  alpha, scale) are least-squares fits of eft's 3-key ramps. 8.5 Smash units per XV2 unit (as the
  models); XV2 velocities are per second. Not converted: ConeExtrude ribbons (2 in LineAll),
  Vortex / Translation modifiers, sprite-sheet animation, the secondary colour.
- **Models**: `tools/xv2_to_nud.py` (docs/xv2-model-conversion.md).
- **Emitter transform** (found for this): emitter +0x3D8 is a 3x4 matrix Rz·Ry·Rx·scale with the
  translation, from the scale / rotation / translation at +0x408 / +0x414 / +0x420
  (`Ptcl.set_emitter_srt`; all 8115 vanilla emitters agree).
- **Test build**: `tools/supamario_kame_build.py PKG V4 V5 OUT` (Supamario's v4 ptcl + v5 efc /
  scripts): sets `0x03410017`-`0x0341001F`, models `0x03410020` Fire, `0x03410021` Bas,
  `0x03410022` Hand. Up taunt: the charge at bone 0x11 (EEPK effects 0 / 15: Crg x0.4 + tsubu at
  0, x0.6 + CrgON x0.8 at 42, x1.0 + CrgON x1.2 at 78, Crg again at 118 / 158); side taunt: the
  release (Fire model + Ring x0.8); down taunt: the beam head at bone 0, 7 up and 14 in front
  (Bas x1.6, Fireptcl, Wav, 4ptcl, LineAll, Hand x0.45, at their EEPK offsets). Package
  `build/supamario_kame_test.zip`. Not yet seen in game: sizes, the beam head's direction (XV2 +Z
  forward, taken as bone 0's +Z) and the model entries are the things to check.
- Test 1 in game: particles and models show, blue, sized about right; the head model animates.
  The beam head did not point the way Supamario faces, and the second down taunt crashed. The
  Cemu log before the crash: `GX2RSetAttributeBuffer(): Offset exceeds buffer size` ~23 times a
  frame. Its only caller is `0x036F3CE4` (vertex streams of `NU::DeviceWiiU` draw calls, the NU
  model renderer: `NU::CommandBase` vtable `0x10207DCC`; eft draws with `GX2SetAttribBuffer`), so
  the models, not the particles: a vertex buffer whose size is smaller than the stream offsets, as
  when the NU buffer creator (`0x0372A468`, from the allocator at owner `+0x33C`) fails and leaves
  the size 0. NU skins / streams model vertices into per-frame dynamic buffers
  (`NU::DynamicVertexOffsetTable`, `CPUSkinningManager`, `GPUStreamOutSkinningManager`).
  Not pinned down further. Test 2 (`build/supamario_kame_test2.zip`): lighter models
  (`xv2_to_nud.py --plain 1`: cull none, no alpha test, no subtractive, as every vanilla effect
  model; `--skip hand`: Kmh_Hand without its dark subtractive mesh), the down taunt terminating
  its effects at frame 96, the beam head turned 180 degrees (`HEAD_YROT`).
- Test 2 in game: the beam head points the way Supamario faces (test 1's was reversed: the XV2
  TRS parts face their -Z, `HEAD_YROT` 180 is right). The game still crashes some time after a
  down taunt, even a single one; the side taunt (Fire model + Ring) never does. The head read too
  white without Kmh_Hand's dark layer: `--tint` (xv2_to_nud.py) now tints Hand `cor` and Bas
  `Cor` blue. Test 3 (`supamario_kame_build.py --diag`, `build/supamario_kame_test3.zip`): the
  down taunt's pieces one per taunt (up: Bas model, side: Hand model, down: its particles) to
  find the one that crashes.
- Test 3: only the down taunt (the beam head's particle sets: Fireptcl, Wav, 4ptcl, 4ptcl_2,
  LineAll) crashed; the Bas and Hand models alone did not. Values in those sets that no vanilla
  emitter has (7767 checked): life random above life (`wev01_short` 8 +/- 10: XV2's
  Lifetime_Variance exceeds Lifetime), negative emitter velocity (`ring_2`), and a 310-particle
  emitter (vanilla p99 66, max 520). `xv2_to_ptcl.sanitize` now clamps them. Test 4
  (`--diag2`, `build/supamario_kame_test4.zip`): the whole beam head on the down taunt, its sets
  in two halves on the up / side taunts.
- Test 4: the down taunt and both halves crashed (Fireptcl + Wav after longer). Cause: eft's
  `one_time` byte (emitter +0x2FF). With it set, the particle buffer (128 bytes a particle) is
  sized ((end frame - emit start) / (interval + 1) + 1) x rate (`0x04A5BDCC`); the templates had it
  set and the looping emitters an end frame of 0x7FFFFFFF: counts of 10^8-10^9, sizes that wrap
  to small or zero allocations (`count << 7`), then particles written past them, corrupting the
  heap (the NU renderer's buffers among it: the GX2R warnings). Every vanilla emitter has
  one_time set exactly when its end frame is finite. The end frame is also a duration after the
  start frame (`0x04A64F70`), not an absolute frame. `xv2_to_ptcl` now writes both (and checks
  the buffer count per emitter: at most 196 here). Test 5: `build/supamario_kame_test5.zip`, the
  normal taunt layout.
- Test 5 in game: no crash, all three taunts work. The beam-head models sit back to front
  against the particles (the white ball next to Supamario, the stream ahead): the user wants it
  that way, as the beam's end will be a separate effect from the head so it can travel with the
  beam body (for the move: head and end as separate effect ids).
- Orientation (from Mario's cape: `EffMarioSupermant1_L` is `EffMarioSupermant1` mirrored in Z):
  an effect at bone 0 is in the fighter's facing-turned frame, +Z forward, Z offsets in front
  (the cape at Z 9).
- **Beam body** (the ETR traces `Kmh_Beam*.etr`): `tools/xv2_trace_to_nud.py PKG OUT` (the
  mapping in its docstring). Each trace node is a mesh 1 unit long along +Z on its own bone: the
  shaped nodes (closed 25 / 13-point cross-sections) tubes of radius Scale, the flat
  auto-oriented core two crossed ribbons; the bone's Z scale grows at `--speed` (default 2 Smash
  units a frame: XV2's speed belongs to the skill, so the move's projectile should match) for
  ExtrudeDuration frames, then holds while the DefaultEnd Scale / alpha keyframes thin and fade it;
  ShapeStartToEnd alpha keyframes are the alpha along the length; textures BC3 with ScaleUV V
  animated with the length (texture aspect kept) and TransUV at the sampler's scroll speed.
  `EffSupamarioKameBeam` / `Beam2` / `Beam3` (79 / 103 / 125 frames, textures 0x15141A30 / 40 /
  50), entries `0x03410023`-`0x03410025`. Test 7 (`build/supamario_kame_test7.zip`): the side
  taunt adds the size-1 body from bone 0 (0, 7, 3) forward. The user wants the beam's end as a
  separate effect from the head, travelling with the body.
- Test 7 in game: the body shows and grows forward, but too white inside (the inner tube's
  T2_UV01 white cloud and the core ribbon, both opaque). Test 8 (`build/supamario_kame_test8.zip`):
  `xv2_trace_to_nud.py --alpha 0=0.3` (the core ribbon's alpha x 0.3) and `--white-fade 0.85`
  (texel alpha x (1 - 0.85 x its darkest channel): near-white mostly transparent);
  `TRACE_ALPHA` / `TRACE_WHITE_FADE` in the build.
- Test 8 in game: the white is fixed; brighten a bit, and the beam projectile should be much
  faster. Test 9 (`build/supamario_kame_test9.zip`): `--gain 1.3`, `--speed 6 --length-rate 2`
  (grows 6 units a frame to the same 120 / 160 / 200 units: 20 / 27 / 34 frames). The move's
  beam-head projectile should fly at `TRACE_SPEED` (6) to stay with the body.
- Still to do: the move itself (projectile, hitboxes, charge logic).
