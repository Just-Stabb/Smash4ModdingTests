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
- Test 9 in game: brightness right; the beam "slightly slower" and "about double the length": 5
  units a frame to 240 / 320 / 400 units (`--speed 5 --length-rate 4`).

## The move: neutral special (test 10, `build/supamario_kame_test10.zip`)

The user's design: neutral special (the fireball article kept, no longer thrown); hold to charge,
release fires; head and body multi-hit, the beam stops on what it hits (as in XV2) and ends with a
launching hit; the same move in the air; each charge level a little faster. All built by
`tools/supamario_kame_build.py ... --rpx IN.rpx` (its docstring lists the files).

- **Charge** (`fighters/supamario/supamario.c`, status 0x152, `kame_n_*`): Mario's throw
  (0x211 / 0x215) frozen at frame 10 while special is held (`ControlModule(0x2712, 1)`); level 2
  after 42 charge frames, 3 after 78 (the XV2 charge effect's steps, `PtcSupamarioKmhCrg` /
  `CrgON` / `tsubu` at the hand, following, killed on release or when the status ends); fires by
  itself at 100. Released, the throw plays on and at frame 14 generates article 5 and sets its
  status to the level. In the air it stalls (kinetic 0xA, the cape's) until the beam is out.
  SpecialN / SpecialAirN ACMD: no GENERATE_ARTICLE, no fire / red flash; the release (Fire model,
  Ring) at the hand at 14; charge sound from the start, stopped for the fire sound at 13.
- **Projectile** (weapon kind 0x18B, `fighters/supamario/weapons/kamehameha.c`): statuses 0-2 fly
  (level 1-3: 5.0 / 5.5 / 6.0 units a frame for 48 / 58 / 67 frames: 240 / 320 / 400 units),
  3 hold (30 frames, still multi-hitting), 4 finish (12 frames). The hit -> hold switch is native:
  the fireball's hit method removes the weapon on any hit, so weapon_expand's `on_hit` gives the
  kind its own singleton whose hit method asks for status 3 instead (`docs/weapon-expansion.md`).
  `"motions": 6` gives it six motion slots (all the fireball's animation): fly1-3, finish1-3.
- **Body**: a trace can't stop where the head stops, so the projectile drops a body piece
  (`EffSupamarioKameSeg1` / `2` / `3`, `xv2_trace_to_nud.Segment`: the level's trace, 2 x speed
  long, behind its spawn point) every 2 frames at its head; they stay at full width for 125 frames
  and are killed (`EffectModule(0x2723)`) when the beam ends. Their textures' V repeats are
  -scroll x length / speed, so the scrolling texture continues from one piece to the next.
- **Hitboxes** (weapon game.bin): head ID 0 (4.5 / 5.5 / 6.5) and a body capsule ID 1 (3.5 /
  4.0 / 4.5, from the head back to the spawn point, regrown every 4 frames), 1.0 / 1.3 / 1.6%,
  angle 366, KBG 100, FKB 30, Rehit 5; the finish, Part 1 (its own hit log): 6 / 8 / 10%, 40
  degrees, KBG 85 / 90 / 95, BKB 50 / 55 / 60, size 7 / 8 / 9, frames 0-2.
- **Effects** (weapon effect.bin): the head per level from EEPK effects 3 / 4 / 5 (Bas 1.6 / 2.0
  / 2.5, Fireptcl, Wav, 4ptcl, Hand; LineAll at level 1), on bone 0x7D0 as the fireball's, turned
  180; the finish: Fire, Ring, Wav. The taunts are back to normal (`--taunts` for the old test).
- Unverified in game: the weapon's effect / hitbox frame (+Z forward assumed, as on fighters),
  how the kill looks on the body pieces, kinetic 0xA in the charge.

### Test 10 in game, and test 11 (`build/supamario_kame_test11.zip`)

Test 10: charge and release work, the charge effects at the hand. But:
- the head effects did not face the flight; they turned around the body's front end. They were on
  bone 0x7D0 as the fireball's flame, and the fireball's animation spins that bone. The body pieces
  (MSC, bone 0) faced right. Test 11: the head effects on bone 0 (`WEAPON_BONE`), still turned 180.
- the beam stopped on a hit but multi-hit for ever, never launched, and it and its effects never
  went away. So the MSC never finished the finish status (the removal, and the body pieces' kill,
  are there). Likely cause: the finish played motion slots 4-6 (`"motions": 6`), past the
  fireball's four, so its motion change failed and the fly motion's hitboxes stayed. Test 11: four
  motions (fly1-3, one `finish` for every level: 8%, 40 degrees, KBG 90, BKB 55, size 8), and
  `kame_phase` so hold / finish don't restart if their status is entered again. (The kill call is
  right: ACMD Terminate_Graphic_Effect's handler `0x02BE25AC` builds `EffectModule(0x2723, id, a,
  b)` and calls the same EffectModule MSC handler, accessor `+0xA0` vt `+0x2EC`.)
- the body capsule (angle 366) pulled targets to its middle. Test 11: angle 0, FKB 15 (where they
  are, pushed a little along the beam); the head keeps 366.
- the joins between body pieces showed. Test 11: each piece is half a spacing longer and its ends
  fade over that (`Segment` `overlap`, `SEG_OVERLAP` 0.5), so neighbours cross-fade.
- T-pose charging in the air: test 11 drops the air stall (kinetic 0xA, the cape's); he falls as
  with the fireball. The charge effects also end in the SpecialN effect script at frame 13.
- "the charge effect has a hitbox": not found (no hitbox in SpecialN's game script; the beam's
  head hitbox is at the hand when it spawns at frame 14). Asked the user.


### Test 11 in game, and test 12 (`build/supamario_kame_test12.zip`)

Test 11: the head faces the flight now. But:
- "the starting point of the beam is displaying at the end": the EEPK parts all sit on XV2's TRS bone,
  but only Bas and Wav have `PositionUpdate` (they move with the head); Hand (the ball at the hands),
  Fireptcl, 4ptcl and LineAll stay where they were spawned: the beam's start. Test 12: those are
  `Graphic_Effect`s (non-following) at the spawn point; Bas / Wav `External_Graphic` on the head.
- the start's colour ("lacking in color", the user's XV2 shot: a white core, a saturated cyan rim,
  deep blue streaks): Kmh_Hand's subtractive `hand` mesh was left out and the ball tinted pale blue.
  Test 12: `xv2_to_nud.py --subtract-as hand=0,0.3,1` (normal blend, the deep blue that subtracting
  its orange leaves) and `--rim cor=0,0.8,1.8,1.3` (MatCol3's rim colour baked into the vertex
  colours for the side camera: white in the middle, cyan at the edge).
- the multi-hits didn't carry targets into the head, and hit for ever (an opponent right behind
  him): the body capsule kept growing in the hold (the fly motion played on) past the spawn point.
  Test 12: the hold freezes the fly motion (`MotionModule(0x4, 0)`): no more body pieces, the capsule
  stays; the body's knockback pushes forward (angle 0, FKB 50) into the head (366 holds them).
  Safety: removed `KAME_MAX` (155) frames after firing whatever happens; the hold removes it if the
  finish doesn't start; a fly status asked for after the hit goes back to the hold / finish.
- "the beam effect sometimes disappears after hitting": probably the head's Terminate-1 effects
  ending with the hit's status change. Test 12: every beam effect has Terminate 0 and they all end
  together: the finish's ACMD (Terminate_Graphic_Effect for each) and `kame_fx_off()` in the MSC
  before any removal. The body pieces now come from the fly ACMD (frames 2, 4, ...), not the MSC.
- the body "should disappear nearly all together": as above, all at once.
- the charge effect should grow with the level (the user's XV2 shots): Crg x0.5 / 1.0 / 1.6 and
  CrgON x1.0 / 1.6 at levels 2 / 3, the previous level's replaced, spawned again every 40 frames.

### Test 13 (`build/supamario_kame_test13.zip`, test 12 + the user's notes before testing it)

- After firing, the throw is frozen at frame 16 (the firing pose) while the beam exists
  (`ArticleModule(0x2717, 5)`, the vanilla "article exists" check), at most 115 frames (the longest
  beam), then plays to its end.
- In the air: floats down while charging (his rise stopped; gravity energy 1: acceleration 0.02,
  max fall 0.6 a frame) and floats in place while the pose is held (speed, acceleration and max fall
  0), then the normal fall (kinetic type 0 set again). The calls are the cape's air code's
  (`func_2264`: `KineticModule(0x11 / 0xf / 0x14, 1, ...)`).

### Test 13 in game, and test 14 (`build/supamario_kame_test14.zip`)

1. "The beam's end is slightly too close to the body": the start parts 5 units further forward
   (`START_FORWARD`).
2. "When the beam finishes, it should turn bright and transparent leaving a white line behind":
   `Segment(dissolve=...)` pieces (`EffSupamarioKameDis1-3`, 31 frames): XV2's DefaultEnd thinning
   at 0.75 speed, RGB up to x2.5 over 4 frames, the tubes half as opaque and gone at 55 %, the core
   ribbon opaque, x1.6, with its texture's white kept: a white line. At the end (the finish, the
   range, a wall) the MSC puts one in each body piece's place (`kame_dissolve`: from the frames
   flown, `EffectModule(0x2710, id, 0, 0, 0, z)` behind the head) and ends the rest; the beam stays,
   without hitboxes (`AttackModule(0x2719)`, the vanilla status-end clear), until they're done.
3. The charge pose: SpecialAirN frame 6 (the user's shot; both hands at head height, one forward,
   one back: frames 4-8 by the bones' world positions, `omo.world`), SpecialN too.
4. The beam at a wall left its effects: the fly ends on `GroundModule(0x2722)` (the fireball MSC's
   touch check) as at its range (dissolve, then removed).
- "Fireball disappearing effects on the hand" fired against a wall: the fireball's specializer
  +0x44 sets its EffectModule's vt +0xD4 to 5 (likely the effect of a weapon removed early): the
  Kamehameha's vtable copy has it as a `blr` (weapon_expand `"nop"`).
- "The multihit isn't connecting into the final hit": the body capsule overlapped the head and its
  forward push (angle 0, FKB 50) knocked held opponents out. The capsule now starts behind the head
  (Z -(head + body size)), FKB 35; the launcher is a capsule over the head and 30 units of body.
- "Directly in front when he fires, it disappears at once": the hit method took only bits 0x3; the
  default removes the weapon for 0x13. It now takes 0x13 (`HIT_BITS`). Also the MSC's state is reset
  when status 0 is entered (weapons are pooled: a reused beam may still hold the last one's phase).
- The charge effects stayed where they were made as he floated down (`EffectModule(0x2711)`): now
  `EffectModule(0x2717, id, bone, ...)`, the vanilla following form.

### Test 14 in game, and test 15 (`build/supamario_kame_test15.zip`)

Test 14: the charge effects stay on the hand now. But the multi-hit still dropped, the beam's
effects stayed when it hit no one, Supamario's pose didn't hold until the beam ended, and the finish
(light shaft etc.) never played: the user's read, "the beam is being killed immediately after
hitting an opponent", was right. The fireball's **vtable 2** (`0x101791BC`, the weapon calls it
through the pointer the vtable +0x1C method stores, the base singleton's +4) has the fireball's own
per-frame logic: +0x1C counts its life (work int `0x10000004`, Mario's fireball life) down, +0x3C
removes it at life 0 and, touching ground (GroundModule vt +0x2E4), bounces it (message 0xA) or at a
wall plays Mario's puff (`0x3030002`, EffectModule vt +0x4C) and removes it. So the beam was removed
at the fireball's life, whatever its MSC did, and at walls with the fireball's puff.
Test 15: weapon_expand gives the Kamehameha's singleton its own vtable 2 copy with +0x1C / +0x3C as
`blr` (`"nop2"`), and its vtable's +0x1C a copy storing its own singleton's +4 (unicorn: the copy
stores `0x04B8F324` where the base's stores `0x1056AA04`). Its MSC does its range and walls. The
test-14 `"nop": ["0x44"]` is undone (+0x44 sets the EffectModule's vt +0xD4 to 5: the weapon's
effects end with it; without it they stayed).

### Test 15 in game, and test 16 (`build/supamario_kame_test16.zip`)

Test 15: "the beam is still removed early". The cause was in the weapon MSC: in the weapon
boilerplate `func_22` is `StatusModule(0x2, x)`, which sets the **situation**; a status change is
`StatusModule(0x3, status, flag)` (`func_18` / `func_19`; vanilla weapons: Samus's wave
`func_18(0x1)`). The hold's "go to the finish" used `func_22(4)`, so the hold never ended (tests 10 /
11: multi-hit for ever) and, from test 12, the hold's fallback removed the beam 10 frames later (no
finish, no light shaft). Test 16: `kame_status()` = `StatusModule(0x3, status, 0)`. The test-15
vtable 2 copy stays (the fireball's life / wall removal would cut the beam too).

### Test 16 in game, and test 17 (`build/supamario_kame_test17.zip`)

Test 16: the finish comes out. But:
- the multi-hit hit once: the hold froze the fly motion (rate 0) and the re-hit timer stopped with it.
  Test 17: the hold plays the fly motion on. The body pieces come from the MSC again (`EffectModule
  0x2710`, every 2 frames, only while flying), and the fly ACMD's body capsule stops growing at 40
  units (`BODY_MAX`), so the hold adds neither.
- the beam's effects never ended past a blast zone (the game removes it there without its MSC):
  the head / start / body effects now have Terminate 1 (test 11: Terminate-1 head effects lived
  through the hit's status change and ended with the beam).
- the light shaft (the Fire cone) went into the screen: following (`External_Graphic`) at the
  weapon's bone 0 its rotation isn't the beam's; the finish's effects are now `Graphic_Effect`s like
  the body pieces (which line up), the cone along the beam (the user's choice).
- the pose was never held: `ArticleModule(0x2717, 5)` (vanilla's "article exists", e.g. Samus's
  final smash) said no. Test 17: the pose holds for the level's flight + dissolve (81 / 91 / 100).
  ArticleModule's MSC handler: accessor `+0x4C` vt `+0x17C`; `0x2717` calls vt `+0xFC(id)`, which in
  the class at `0x10102B8C` returns 0 (the fighter's own class not found yet).

### Test 17 in game, and test 18 (`build/supamario_kame_test18.zip`)

Test 17: the blast-zone fix works for the head, but: the head vanished at the hit, the beam didn't
multi-hit, the start parts stayed after a blast zone, and the light shaft was still on the wrong axis.
What it shows about Terminate 1: a **following** effect ends at any status change of its owner (the
hit's status 3) and with it; a **non-following** one doesn't end with it.
- The head: following, Terminate 1 in the fly ACMD; at the hold the MSC puts its parts back, still
  (`kame_head_fx`, EffectModule 0x2710, terminate 1); the finish's ACMD ends them.
- The start parts (Hand ball, Fireptcl, 4ptcl, LineAll): now made by Supamario's MSC when he fires
  (`kame_n_start_fx`, at bone 0 `START_POS` (0, 6.7, 14) + their EEPK offsets, turned 180, the level's
  sizes) and ended with his pose or his status (`kame_n_start_off`).
- The multi-hit: the head is PK Fire's pillar kind of hitbox (vanilla `pkfire` game.bin: 68-80
  degrees, KBG 30, BKB 10, FacingRestrict 3, re-hit 11): 80 degrees, KBG 30, BKB 10, re-hit 6.
- The light shaft: Kmh_Fire's cone runs along +Z only through its TRS bone's constant X -90; in game
  it went into the screen. `xv2_to_nud.py --bake-rot TRS`: that rotation in the vertices, the bone
  unrotated with its scale axes swapped (R S R^T); posed vertices identical to before at every frame.
  (Kmh_Bas has animated bones under its TRS: not baked.)
