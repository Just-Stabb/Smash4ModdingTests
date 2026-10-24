# Porting an Ultimate fighter's model and animations to Smash 4

`tools/ultimate_fighter.py` (first used for Sephiroth, `fighters/edge/README.md`) turns Ultimate's
SSBH files into a Smash 4 fighter's model folders and motion pacs, on the fighter's own skeleton,
inside a new kind built on a base fighter (docs/kind-expansion.md).

```
python3 tools/ultimate_fighter.py model SRC/model/body/c0N BASE/model/body/c0N OUT/c0N --empty EMPTY_DIR [--joints SwordL1,SwordR1] \
    --max-bones 136 --motions SRC/motion/body/c00 --anim-cache CACHE.json
python3 tools/ultimate_fighter.py motions SRC/motion/body/c00 SRC/model/body/c0K BASE OUT [--add C00Attack12,...] \
    [--joints ...] --max-bones 136 --anim-cache CACHE.json
```

`EMPTY_DIR`: Cloud's `model.sb` (12 bytes, no swing bones) and Kirby's `model.nhb` (64 bytes, no
helper bones). `c0K` for the motions: the costume whose skeleton has every bone (Sephiroth: c06).

## What the game ties to the skeleton (Zelda's model folder)

| file | keyed by | done |
|---|---|---|
| `model.vbn` (LE `' NBV'`, counts by bone type 0/1/2/3) | bone hashes: the same for a name in every fighter (not CRC32, not a known function), so the standard bones copy the base's | ours: the base's 26 standard bones first, then Ultimate's (CRC32 hashes), all type 0 |
| `model.jtb` | ACMD / effect joint ids -> bone index (table 0: id n = entry n - 1) | the base's, each index moved to our bone of the same name (armor bones -> stand-ins) |
| `model.ik` (`CRIK`) | bone indices 3-6, 7-10 (the legs) | kept: our first 26 are the base's |
| `model.nhb` (`' BHN'`, LE) | helper (HLP) bones by hash | empty (Kirby's) |
| `model.sb` (`' BWS'`, LE) | swing (SWG) bones by hash, physics | empty (Cloud's); `model.sbwl` left out |
| `model.moi` | mesh name prefixes (a hash we can't compute), a VIS flag, a bone, the mesh index | kept, so the NUD keeps the base's 32 mesh names in order |
| `material_anime_eyelid / face.pac` (MTA per motion) | visibility by **mesh name** (`Zelda_Openblink_Eye_VIS_O_OBJ`...), material UV animations by material hash | rebuilt per motion: the base's eye / mouth keys, plus the swords' (from Ultimate's visibility tracks) and the wing (hidden) |
| `motion/*/main.pac` | OMO nodes by bone hash; entries by name (`FitZeldaBodyMain<Motion>.omo`) | the base's entry list, each Ultimate motion of the same name (stand-ins in `MOTION_STANDINS`) |
| `motion/*/lhand / rhand.pac` | the base's hand poses (they turn `LHandN` / `LHaveN`) | every entry one constant node on a bone we don't have |
| `zeldapt1 / sw1 / sw2.pac` | the base's own bones (swing, parts) | kept (none of our bones) |

## Skeleton

The 26 bones the game, the IK and the joint table know (`TransN` ... `ThrowN`) come first, in the
base's order, from Ultimate's `Trans` ... `Throw` (`STANDARD`). Ultimate puts `LegC` between `Hip`
and the legs and `ClavicleC` between `Bust` and the clavicles; Smash 4 hangs legs and shoulders from
`HipN` / `BustN`, so those two are folded into their children (bind and every frame: parent's local
x child's local), and stay as extra bones for the vertices weighted to them. Then Ultimate's other
bones, parents first, leaving out bones nothing is skinned to (end markers, unused helpers): vanilla
fighters have at most 138 bones (Dr. Mario), Sephiroth 172 (124 in his second outfit).

**Bone budget** (`--max-bones 136`, Zelda's count): past it, leaf bones are merged into their parents
(their vertices re-weighted there), the ones no motion moves first (`--motions`: the Ultimate motions
read once, cached in `--anim-cache`), then those with the fewest vertices; never the standard bones,
the folded ones or `--joints`. The motions use every costume's kept bones (Sephiroth: 154 animated
nodes; a costume ignores the ones it lacks, as Bowser Jr's motions do for the Koopalings).

**NUD header 0x0C / 0x0E** (`nud.write`): the first and last bone index the vertices use. Every vanilla
fighter: 2 to N (Zelda 2-135, Bowser 2-78), no vertex on TransN / RotN. Ours were 0 to bone count - 1:
Incineroar (0-142) drew as a stretched red pillar, Sephiroth (0-171) crashed on loading. Now: vertices
on bone 0 / 1 go to HipN (including the empty meshes that fill unused slots), and the header holds
the range the vertices really use (Sephiroth 2-131 / 2-109, Incineroar 2-135).

**Polygon flags** (+0x22 of each polygon entry): 0x40 << 8, low byte **4 on every rigged polygon**
(all 288 in the vanilla fighters; 0 on all 640 single-bound ones). Ours had 0 up to test 19, and the
game drew them unskinned: Incineroar a stretched pillar, Sephiroth invisible (with the 2-N header
too). `nud.write` sets it from test 20.

**Joint table: 26 entries, never more** (every vanilla fighter's). Test 20 appended Sephiroth's
swords as joints 27 / 28 (`--joints`): his hitboxes hit the whole stage. `--have LEFT,RIGHT` (both
tools) makes those Ultimate bones play `LHaveN` / `RHaveN` instead of `HaveL` / `HaveR` (Sephiroth's
`SwordL1` / `SwordR1` hang from the same hand bones), so the sword hitboxes use joints 24 / 25 and
follow the sword exactly; a held item takes the sword's angle. `ultimate_acmd.py` also writes
spheres as `Special_Hitbox` / `Grab_Collision` (vanilla has zero-length extended ones too, so that
wasn't the cause).

**Effects** (`ultimate_acmd.py --effects IDS_JSON NUSKTB`, with `--others`): every `effect_*`
function becomes the effect script of the same Smash 4 name (`TRANSLATE`'s for the translated
moves), replacing the base's; not specials / Final Smash (still the base's moves). Macros:
`EFFECT_MACROS` (EFFECT -> Graphic_Effect2, EFFECT_FOLLOW -> External_Graphic, FOOT_EFFECT ->
Graphic_Effect, LANDING_EFFECT -> Graphic_Effect3, ..., EFFECT_OFF_KIND -> Terminate_Graphic_Effect;
alpha x 100, colour x 255), matched on 10 fighters both games have. `sys_*` names -> Smash 4 common
ids: `reference/ultimate_sys_effects.json` (`tools/ultimate_sys_effect_map.py`: the same moves'
scripts aligned by frame, 47 names). Since Sephiroth test 30 a name matching a common
emitter set or model by name takes that entry (`--common EFC PTCL`: `sys_bomb_a`, `sys_sp_flash`,
`sys_sliding_smoke`, `sys_spin_wind_s` had another effect's id). Bones without a joint id use their
nearest jointed ancestor (Ultimate skeleton), the offset carried through the bind pose
(`skeleton_locals`). The facing-left branch is taken (the dumps nest the right-facing one inside it);
looping motions get `Loop_Rest` + `JUMP` to themselves when the base's script loops.

**Sword trails**: `AFTER_IMAGE4_ON(_arg29)` -> `Sword_Glow` (texture pair, blur length, the two
blade points, the effect bone, size; blend mode / shader 11 / 1 as Ike's, Marth's and Link's),
`AFTER_IMAGE_OFF` -> `Terminate_Sword_Glow`. Trail textures are numbered: an id is a 1-based index
into the executable's table of 259 names (`0x10423E60`, docs/native-notes.md "Sword trails");
`tools/trail_table_cave.py` copies it into the grown code space with new names (Sephiroth's 260-263),
`tools/ultimate_trails.py` makes the `.nut` pairs (`effect/<name>/trail/`) from Ultimate's nutexb
pairs, and the ids file maps Ultimate's texture names to them (`fighters/edge/edge_effects.json`,
merged with the sys map: `--effects A.json,B.json NUSKTB`).

**The fighter's own effects** (`tools/vfxb_to_ptcl.py`): Ultimate's `ef_<name>.eff` (EFFN header:
effect names -> 1-based emitter set index; a VFXB, Switch eft2 version 22: `tools/vfxb.py`, the
emitter layout ported from KillzXGaming's EffectLibrary) -> new sets in the fighter's bank (the
base's ptcl / efc, whose sets stay for the base's specials), one efc entry each (ids `0x3KKnnnn`),
the ids merged into the fighter's ids file for `--effects`. Per emitter, from a template emitter of
the same particle type, blend and mesh-ness (the base's own, else one from any vanilla ptcl with its
shader, shader parameters and textures imported: `Ptcl.import_emitter`; plain shaders first, i.e. no
shader parameters (Ike's FS cloud shader tinted Sephiroth's meshes orange, test 32), then the UV
animation the emitter needs (mode word 0x510) and the follow byte 0x2F9): its texture (BNTX with the
channel selection applied: Ultimate's BC5 textures are luminance + alpha) as a BC4 shape with the
colour moved into the particle's, colour / alpha / scale keys fitted to eft's 3-key ramps, life,
emission, velocity, gravity, volume, rotation, the emitter transform. Meshes (a primitive id) come
from the VFXB's BFRES (`tools/bfres_switch.py`) into the ptcl's primitive table
(`Ptcl.add_primitive`). Identical textures are shared (Sephiroth's bank: 4.1 MB; Bayonetta's
vanilla one is 4.6 MB). Not converted: stripes (ribbon trails: the speed lines), flipbook
animation (the first cell), the second colour track and multi-texture combiners, end fades,
emitter animations, child emitters. A directional (type 3) mesh at rest becomes type 4: Smash 4's
type 3 turns a mesh by its velocity, and with none his sword glows and slash arcs pointed the wrong
way (test 32); type 4 keeps the emitter's frame at rest (Zelda's Nayru's Love crystals).
UV shift / scale / rotation (initial, random, per frame) go to slot 0's UV block (0x510-0x54C;
a mesh whose template can't animate UVs gets the starting transform baked into its UVs): Ultimate's
slash arcs are full discs that the scrolling texture cuts into a swing, neutral air's burst a circle
whose tiled line texture makes the spikes. Templates never use a shader that reads the frame / depth buffer (refraction: they drew glows
see-through, test 36) or texture arrays, and are ranked on the follow type (0x310, shader-keyed)
and the flipbook mode (0x500, shader-keyed: eft2's life fit / clamp / loop / random -> 1 / 4 / 2 / 3)
before the UV animation; with a matching flipbook template the whole sheet, cells, table and frame
rate go over (docs/ptcl-format.md). The fade (0x82C) and "stop emitting when turned off" (0x2F9)
come from eft2's alpha fade / is_fade_emit. eft2's types 5 / 6 carry no ribbon settings (its
ribbons are emitter plugins): directional quads along their motion. Smash 4 adds the UV shift (uv x scale + shift), Ultimate
subtracts it; both turn about the texture's centre (found from each game's own effects: the shifts
are written negated). The fade when turned off (0x82C = 1 / eft2's alpha fade
time) ends infinite-life glows; the sampler's wrap is per axis (eft's codes are eft2's) and eft2's
texture repeat (2 x 1 / 1 x 2 / 2 x 2) goes to 0x508 / 0x50C: with mirror, a quarter texture makes a
whole star (his X flashes). Flipbooks show the cell Ultimate's pattern table plays first.

**Effect angles** are the same in both games: R = Rz Ry Rx (X turned first; his sword glows lie along
the blade, his up-air arc faces the camera only so, and the moves both games share keep their angles
in this order better than in the others). An effect on a bone without a joint id goes to the nearest
ancestor that has one, the offset and the angles carried through the bind pose (`EffectTranslator.place`).

**Last-effect settings**: `LAST_EFFECT_SET_RATE` / `_ALPHA` / `_COLOR` -> Smash 4's commands of the
same name (rate as is, alpha x 100, colour x 255), left out with the effect they follow when that one
wasn't converted (they would land on the one before). `EFFECT_DETACH_KIND` -> `EFFECT_DETACH_KIND`
(neutral air's burst detaches and plays out after the move). Read from Ultimate's executable below.
Not yet in the scripts: FLASH / BURN_COLOR, `EffectModule::set_disable_render_offset_last` /
`enable_sync_init_pos_last`.

### Ultimate's effect commands (ExeFS `main`, version used: the NSO's dynsym names them)

`app::sv_animcmd::*` read their lua arguments and call EffectModule (accessor +0x140) virtuals
(FighterEffectModule's vtable 0x4F6BCB8 in the decompressed image; `.rela.dyn` holds the pointers):
- `LAST_EFFECT_SET_RATE` (0x22A49A0) -> vt+0x338 = `set_rate(last handle (module +0x24), rate)`
  (vt+0x330): the rate goes to the effect record's +0x264 (records of 0x300 bytes, handle >> 24 =
  index): the set's playback speed, as Smash 4's command of the same name. `LAST_EFFECT_SET_ALPHA` ->
  vt+0x348, alpha as is (0-1; Smash 4 takes a percent).
- `EFFECT_OFF_KIND(name, a, b)` -> vt+0xE0 `kill_kind(name, a, b)`, the flags in the order of Smash 4's
  `Terminate_Graphic_Effect(Graphic, KillParticles, KillImmediately)`. `EFFECT_DETACH_KIND(name, n)` ->
  vt+0x100 `(name, n, 0)`.
- `AFTER_IMAGE4_ON_arg29` (0x22A76D0, the parser 0x22A6420) fills a 0xB0-byte request and calls
  vt+0x120: tex1 +0x10, tex2 +0x18, blur frames +0x20, bone1 +0x00 / offset +0x30, bone2 +0x08 /
  offset +0x40, terminate +0x50 (ORed with 0x10000 into the trail flags), effect +0x58 ("null" -> none),
  bone3 +0x60, offset +0x70, rotation +0x80 (degrees -> radians), size +0x90, mode +0x94, axis +0x95
  (0 X, 1 Y, else Z: unit vectors), arg 24 +0x98, blend +0x9C, shader +0xA0, cull +0xA4, then two
  floats +0xA8 / +0xAC (defaults 1 / 0). The trail (0x2B0 bytes, built at 0x35670E0) keeps a history
  of blur x 16 + 1 points as Smash 4's, and the arguments are Smash 4's `Sword_Glow` ones in the same
  order (texture pair .. size, TrailMode, Axis, Unused, BlendMode, Shader); Ultimate added the cull
  and the two floats. The shader number: >= 1000 subtracts 1000 and loads a second shader (as Smash
  4's); then >= 100 subtracts 100 and sets trail +0x64 = 2 (else 1), which only stops the update
  (0x355B540) writing the fade (+0x44) into the vertices. Every Ultimate trail in the dumps passes
  axis X, `TRAIL_BLEND_ALPHA`, 101, `TRAIL_CULL_NONE`: the converted ones keep Marth's / Ike's / Link's
  Smash 4 blend 11 and shader 1. The two floats (1.4 / 0.1 for Sephiroth; 1.2-2 / -0.1-0.7 across the
  dumps) go only into the trail shader's constant block (with the fade and a global time, update
  0x355BF9C): Ultimate's trail shader, not in the ExeFS, so they have no Smash 4 counterpart. Not in
`render/shader` either (nufxlb / nushdb: model and post-effect programs only), nor `effect/system`
(ef_common / ef_item, the item trail textures), `common/shader/sfxpbs` (default textures) or
`fighter/common` (params: `effect.prc` holds colours and effect ids, no trail or lighting values).
Smash 4's own trail shader is `shader/effect_trail.nsh` (GX2 microcode).

**Ultimate's trail shaders, found and decoded.** The executable names them as Smash 4 does
(`"0x4f%06x"` + `VS` / `PS`); the programs are in `render/shader/bin/nusampleshaderlist.N.nushdb`
(`0x4f000000PS` .3, `0x4f000001VS` .2 (the vertex program for all but the 1000s), `0x4f000001PS` .4,
`0x4f000002PS` .5, **`0x4f000065PS` (101, every Ultimate trail) .6**, `0x4f0003e9VS` / `PS` .7 / .8).
`tools/nush_dis.py NAME FILES` disassembles one (Maxwell, envytools' `envydis -m gm107`:
`tools/maxwell_dis/build.sh`). The trail's constant buffer c4 is the update's block (0x355BF9C):
c4[0x0] = `AFTER_IMAGE4_ON` arg 29 (0.1), c4[0x4] = arg 28 (1.4), c4[0x8] = the trail's +0x44, then
a global time and +0x2A0; c13[0x0] the frame's HDR range.
- **101 PS**: colour = A(u - c4[0x8], v).rgb x **c4[0x4]** x c13[0x0]; alpha = A.a x **B(u2, v).r**
  (A = the first trail texture, sampler 8; B = the second, sampler 0xA, sampled at its own U: the
  vertex's attribute 9, not the texture coordinate). The vertex colour isn't used. So arg 28 is a
  plain **colour gain** (Sephiroth 1.4), and the mask is B's red channel.
- **1 VS**: world z -= **c4[0x0]** before the view-projection: arg 29 is a **depth offset** (0.1: a
  little behind the fighter; negative values in the dumps pull trails in front).
- **Turning it off**: `AFTER_IMAGE_OFF(agent, n)` -> EffectModule vt+0x138 (0x4511D0): the trail
  (0x2B0 bytes) gets +0x38 = n / 60 (seconds left), +0x3C = 1 / n, its delay +0x34 = 0 and the fading
  flag +0x2A8. A trail starts (0x3569600) with +0x40 = 1, +0x44 = 0.
- **The calc** (0x1356124, a walk of the global trail list, once a frame; step = game speed (global
  +0x148) x the trail's rate +0x4C): a +0x34 above 0 counts down (step / 60) and sets the fading flag
  at 0 (a delayed off). While fading, +0x38 counts down the same way (at 0 the trail goes to the
  dying list, state 5) and each frame **+0x40 -= step / n** (1 -> 0 over the n frames) and **+0x44 +=
  step / n x 0.5** (0 -> 0.5). It also keeps the history: one 64-byte entry a frame the blade moved
  (+0x00 / +0x10 the two blade points, +0x30 how many points the segment is split into: 1, 2, 4 ..
  from how far it swung (thresholds 1/8, 1/4, 1/2), +0x34 its time in frames x rate; a frame whose
  step is under 1/16 (all but frozen) adds its time to the last entry instead).
- **Attribute 9 (B's U)**: the update (0x355C344, the 101 / mode-2 path) walks the history from the
  newest point with t = the time so far / the trail's whole time (each entry's +0x34 / its point
  count / the sum of +0x34) and writes **U = 1 - t / +0x40** (1 if +0x40 is 0). A's U is 1 - p with
  p = the time so far / (blur - 1) frames, clamped at 1. So with the history full (a swing longer
  than the blur) the two run together, 1 at the blade to 0 at the tail, and A x B is the same
  picture as one texture; on a shorter trail A shows only its blade end while B still spans the
  whole of it (B's tail is 0: the short trail still fades out at its end). The vertex colour (alpha
  (1 - t) x +0x40) is written but unused by 101.
- **The ending**, put together: over AFTER_IMAGE_OFF's n frames +0x40 shrinks, so B's U reaches 0 at
  t = +0x40 and goes below it past there: the mask (0 at U = 0: Sephiroth's tex_edge_sword2 / 4) **cuts the trail back from its tail to the blade**, while A slides
  by +0x44 (c4[0x8]: up to half the texture) toward the blade. An Ultimate trail **retracts into the
  sword** as it ends; a Smash 4 one fades out in place (vertex alpha).
For the conversion (`tools/ultimate_trails.py`): alpha = A.a x B.r in A's UV space is what Ultimate
draws while the swing is longer than the blur (B's U = A's U then); its "Add" texture (x0.5) gives
Smash 4's shader 1 about 1.5x the colour, close to the 1.4 gain. Not carried over (Smash 4's shader
1 has no second U nor a fade constant): the depth offset, B spanning a short trail on its own (a short
Ultimate trail still fades out at its tail; the converted one ends wherever A's U stops), and the
retracting ending (Smash 4 fades).

**Shader 3: the retracting trail in Smash 4** (test 42). Smash 4's trail keeps the same fade value
(+0x30, 1 -> 0 over `Terminate_Sword_Glow`'s frames) and the same t; it only lacked a way to hand
them to the shader (docs/native-notes.md "The trail shaders"). `tools/trail_shader.py` adds trail
shader 3 to `shader/effect_trail.nsh` (Ultimate's 101: mask at U = 1 - t / fade, colour slid by
(1 - fade) / 2, colour x gain, the alpha the colour's alpha x the mask) and patches two stores of the
executable's vertex writer so the vertex colour (whose rgb no vanilla trail shader reads) carries t
and the fade. Converted trails use it: `tools/ultimate_acmd.py` writes Shader 3, and
`tools/ultimate_trails.py --shader 3` keeps A as is and packs B's mask (alpha) with the gain / 2
(rgb, arg 28) into the second texture, so the mask follows the trail's length as in Ultimate (the
short-trail case too). Still not carried over: the depth offset (arg 29).

**Swapped meshes**: Ultimate swaps Sephiroth's sword for a bright copy during swings (`VIS_ALSO`:
the slot shows while the sword or its bright / dark copy does); with the plain sword's track alone it
vanished in attacks (test 22).

**Material animation pacs**: keep the base's `default.mta`, `default_temporarily.mta`, `display.mta`
and `material_anime.lst` (a hash of the base's motion names, not CRC32); the face defaults get the
swords' keys. Test 20 left them out and the sword didn't show in attacks.

Packaging: leave out `model.sbwl`; keep the base's other motion pacs (`zeldasw1 / sw2 / pt1.pac`,
`koopapt1-3.pac`) next to the new `main.pac` / `lhand` / `rhand`.

VBN bind: position, Euler angles with R = Rz Ry Rx (Sm4shCommand's `EulerToQuat`), scale.

## Meshes and materials

Every polygon rigged as the base's body (vertex type `0x47`: byte colors and half UVs in the vertex
section; position, half normal / bitangent / tangent with w 1, four bone bytes and four byte weights
summing to 255 in the "vertex add" section; mesh bind 4), positions in bind space (a mesh Ultimate
binds to one bone: weighted 1.0 to it). `tools/nud.py` writes these (`Polygon.bones`).

Mesh slots (`MESH_SLOTS`): each Ultimate mesh goes into the base mesh that plays its part (eyes open,
half blinks, blink, mouth shapes; body; hair; left sword in Zelda's `skirt_VIS_O_OBJ16`, right sword
in `polySurface5817_VIS_O_OBJ`, the wing in `Zelda_DamageFlyFront_VIS_O_OBJ`); an unused slot gets an
empty triangle.

Materials: the base's skinned body material (`0x9A011063`: color, normal, ramp `0x10080000`), opaque
or alpha-blended (src / dst 1); Ultimate's skin (the materials with subsurface settings,
`CustomVector30` / `11`, eyes aside) the base's skin material when it has one (Zelda's `0x9A211067`:
color, normal, her 32 x 256 skin ramp copied in as the last texture, the ramp; warm rim, specular
and AO floor). Textures (`0x40EB0000` up, power-of-two, one mip):
- color: Ultimate's col x `CustomVector8` x `CustomVector13` (colour / diffuse gain: his
  `def_edge_005` 0.588), brightened by emission; cut-out texels get their neighbours' color (BC7
  leaves noise there). No AO in it (only without a normal map);
- normal: Ultimate's XY, Z rebuilt, alpha = Ultimate's AO (prm blue) ^ (1 / 2.2). Smash 4 reads the
  normal map's alpha as AO: diffuse x (aoMinGain + (1 - aoMinGain) x alpha^2.2), specular and rim x
  (alpha^2.2 + aoMinGain.w) (Smash Forge's SmashShader.frag, from Link's face shader in Cemu; Zelda's
  alpha is AO with a shine mask: mid-grey cloth, dark folds, bright trims). Tests up to 40 put the
  smoothness there (prm green inverted) and the AO in the color as well: his rough coat came out at
  about a quarter of its diffuse (alpha ~0.13), the whole model ~4x darker than now in diffuse
  (colours 5 / 6: ~20x);
- eyes: the iris (second UV set) drawn onto the white.

`tools/nutexb.py` decodes BC7 now (Pillow's BCn decoder).

## Motions

Per motion, per frame: Ultimate's animated locals (bind where a bone has no track), the folded chains
multiplied, helper bones (`model.nuhlpb` orient constraints: a share, axis by axis, of the source
bone's turn from its bind in the parent bone's frame) -> OMO (constant tracks stored constant,
others interpolated 16-bit). Aim constraints are not done (H_Collarbone in the second outfit).

## Moves (`tools/ultimate_acmd.py`)

Ultimate's hitboxes are in its ACMD, decompiled to smashline Rust (WuBoytH/SSBU-Dumped-Scripts,
`smashline/lua2cpp_<fighter>/<fighter>/<Motion>.txt`); `ultimate_acmd.py` turns the normals, grabs,
throws and get-up / ledge attacks into the base's `game.bin` scripts (`TRANSLATE`):

```
python3 tools/ultimate_acmd.py DUMP/edge BASE/script/animcmd/body/game.bin OUT/game.bin OUT_MODEL/c00 \
    --others BASE/script/animcmd/body OUT --motion-list SRC/motion/body/c00/motion_list.bin \
    --mtable BASE/.../motion.mtable OUT/motion.mtable --vl VL_IN VL_OUT --base-rpx RPX --base-kind 0x10
```

- `ATTACK` -> `Extended_Special_Hitbox` on the joint id of the same bone (`model.jtb`; the sword bones
  are added to the joint table with `model --joints SwordL1,SwordR1`), `CATCH` -> `Extended_Grab_Collision`,
  `ATTACK_ABS` / `ATK_HIT_ABS` -> `Throw_Specifier` / `Throw_Applier`, status flags -> the Smash 4
  variables vanilla scripts set for the same thing. Frame numbers carry over as they are: both games
  number the first active frame the same way (Mario's jab: `FRAME 2`, active on frame 2).
- Smash 4 has one script name per side tilt / smash (`attacks3`, `attacks4`; `attacks3hi` / `lw`
  are the angled tilts), not `attacks3s`.
- Cancel frames: Ultimate's `motion_list.bin` extra bytes {intangible start, end, cancel frame} are
  `fighter_param_vl` group 1 bytes 3 / 4 / 2 (Cloud's DownAttackU: 46 / 1 / 26 in both), so the
  moves end when Ultimate's do without cutting the animations.
- The base's effect / sound scripts of the translated motions are emptied (they'd play the base's).
- A motion the base has no slot for (Attack12 / 13 on a one-jab base): `motions --add C00Attack12`
  adds the animation to `body/main.pac`, the kind's `extra_kinds.json` "motions" points its motion
  table entry at it, the translator adds its `motion.mtable` entry; the jab count is fighter_param
  `attack_1_count` (read by the common MSC every fighter's `.mscsb` carries).

## Checked here

- The NUD read back (an independent reader of the written bytes) and rendered in bind pose and posed
  by frames of the written OMOs (Wait1, AttackS4S, Run, AttackAirB, AttackHi4; c00, c03, c06).
- The MTA visibility writer: the base's visibility entries round-trip.

## Not known yet (in game)

- Confirmed in game: the rigged-polygon flag (test 20: both load and draw), the 26-joint table with
  `--have` (test 22: hitboxes right), the sword's swapped copies (test 23: the sword shows).
- Whether the empty `.sb` / `.nhb` and a model without `.sbwl` load.
