# Sephiroth (`edge`)

A port of Ultimate's Sephiroth (the user's files: `edge.zip` in their Drive: `model/body/c00-c07`,
`motion/body` 367 nuanmb, `param/vl.prc`, AI params). New fighter kind `0x42`, character id 60,
UI name `Sephiroth`, base Zelda (`tools/extra_kinds.json`; docs/kind-expansion.md). Trait:
**Technical** (docs/character-traits.md, `kirby_copy_trait()`). Roll-off: the default 2.2 / 1.0.

## v1 (`build/sephiroth_v1_test.zip`): the slot

A copy of Zelda in the new slot, with Zelda's universal-mechanics scripts (roll-off, reverse tilts,
tilts / down smash / shield out of run). Its executable is Supamario test 18's plus kind 0x42.

## v2 (`build/sephiroth_v2_test.zip`): his model and animations

`tools/ultimate_fighter.py` (docs/ultimate-fighter-port.md): Ultimate's model for all 8 colours on
his own skeleton (172 bones; the second outfit c06 / c07 124), all 299 battle motions plus entry /
result / route-map ones, the swords' visibility per motion. Zelda's moves still. Built with:

```
python3 tools/ultimate_fighter.py model edge/model/body/c0N zelda/model/body/c0N OUT/c0N --empty EMPTY
python3 tools/ultimate_fighter.py motions edge/motion/body/c00 edge/model/body/c06 zelda OUT
```
(each `c0N` also copied to `l0N`, the low-detail slot).

## v3 (`build/sephiroth_v3_test.zip`): his normals, grabs and throws, his stats

Ultimate's game scripts translated by `tools/ultimate_acmd.py` (docs/ultimate-fighter-port.md,
"Moves"): jab 1-2-3, dash attack, tilts (angled forward tilt), smashes, aerials, grab / dash grab /
pivot grab, pummel, the four throws, get-up attacks, ledge attack, trip attack: hitboxes on his
own bones (the sword: `SwordL1`, joint 27), Ultimate's frames, damage, angles and knockback.
Cancel frames and intangible frames from Ultimate's `motion_list.bin` in his vl file.

- 3-hit jab: motion slots 0x51 / 0x52 (`extra_kinds.json` "motions", `main.pac`
  `FitZeldaBodyMainC00Attack12 / 13`, `motion.mtable`), fighter_param jab type 1, 3 jabs, no rapid
  jab, jab 2 / 3 input windows 30 (Cloud's).
- Move flag (the root moves him) as Ultimate's for down smash and back air (Zelda's are off).
- Stats (fighter_param kind 0x42), Ultimate's: walk 0.9, initial dash 1.92, run 1.86, air speed
  0.95, air acceleration 0.01 + 0.07, gravity 0.108, fall 1.84 / fast fall 2.944, weight 79, jumps
  25 / 9 / 25 (heights that give Ultimate's 45 / 27 frames of air time with his gravity), landing
  lag n 9, f 14, b 16, up 21, down 26.
- Zelda's effect / sound scripts of those moves emptied (his own effects and sounds are next).
- Model: every colour with the sword joints; `model.sb` / `model.nhb` empty (v2 shipped Zelda's).
- Executable: Incineroar v1's + the boot-to-Training shortcut + the 5 motion table words.

```
python3 tools/ultimate_fighter.py model edge/model/body/c0N zelda/model/body/c0N OUT/c0N --empty EMPTY --have SwordL1,SwordR1 \
    --max-bones 136 --motions edge/motion/body/c00 --anim-cache CACHE.json
python3 tools/ultimate_fighter.py motions edge/motion/body/c00 edge/model/body/c06 zelda OUT --add C00Attack12,C00Attack13 \
    --have SwordL1,SwordR1 --max-bones 136 --anim-cache CACHE.json
python3 tools/ultimate_acmd.py DUMP/lua2cpp_edge/edge ZELDA_UM/game.bin OUT/game.bin OUT/c00 --have SwordL1,SwordR1 --others ZELDA_BODY OUT \
    --motion-list edge/motion/body/c00/motion_list.bin --mtable ZELDA_UM/motion.mtable OUT/motion.mtable \
    --vl fighter_param_vl_edge.bin OUT/fighter_param_vl_edge.bin --base-rpx cross_f.rpx --base-kind 0x10
python3 tools/fighter_param.py set fighter_param.bin OUT 66 3=0.9 8=1.92 11=1.86 17=25 18=9 19=25 20=0.07 \
    21=0.01 22=0.95 24=0.108 25=1.84 27=2.944 28=9 29=14 30=16 31=21 32=26 33=79 81=30 82=30 262=1 263=3 264=0
```
(`ZELDA_UM` = Zelda's universal-mechanics `script/animcmd/body`.) Checked: `kind_expand_test.py`
(0 failed; the record's 4 entries kept after the run-time build), `boot_training_test.py`;
hitbox world positions on the posed skeleton (forward smash's sword hitboxes in a line 16-38 units
ahead at frame 26).

Left out of the scripts (counted by `--list`): Ultimate-only module calls (jostle areas, reaction
frames, throw camera zoom, finish camera), the down smash ground check, forward air's
platform pierce flag.

## Test 30 (`build/sephiroth_test30.zip`): sword trails, universal effects

- Sword trails: Ultimate's `AFTER_IMAGE4_ON` in forward / up / down tilt, forward / up smash, back /
  up air -> `Sword_Glow` with his own trail textures (`effect/edge/trail/TexEdgeSwordTrace*.nut`,
  ids 260-263 through the executable's trail table, `tools/trail_table_cave.py`).
- Universal effects: the sys map now matches names (slide attack's smoke was the dash's).

```
python3 tools/ultimate_trails.py ULT/effect/fighter/edge/trail OUT/fighter/edge/effect/edge/trail \
    tex_edge_sword1.nutexb,tex_edge_sword2.nutexb=TexEdgeSwordTrace tex_edge_sword3.nutexb,tex_edge_sword4.nutexb=TexEdgeSwordTrace2
python3 tools/ultimate_sys_effect_map.py DUMPS VANILLA reference/ultimate_sys_effects.json \
    --common effect/common/common.010d0000.efc effect/common/common.010d0000.ptcl
python3 tools/ultimate_acmd.py ... --effects reference/ultimate_sys_effects.json,fighters/edge/edge_effects.json edge/model/body/c00/model.nusktb
python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/trail_table_cave.py IN.rpx)
```

## Test 31 (`build/sephiroth_test31.zip`): his own effects

Ultimate's `ef_edge.eff` converted (`tools/vfxb_to_ptcl.py`): 43 of the 46 effects his translated
scripts use (sword flares and glows on the blade, slash arcs and lights, the grab's hand aura,
throw bursts, entry / victory effects), particles and meshes; the three speed-line effects are
stripes only (not converted). Bank: Zelda's sets + his (entries 0x27-0x51, ids 0x3420027-0x3420051,
`fighters/edge/edge_effects.json`).

```
python3 tools/vfxb_to_ptcl.py ULT/effect/fighter/edge/ef_edge.eff ZELDA/effect/zelda OUT 0x42 \
    fighters/edge/edge_effects.json EFFECT... --templates VANILLA/fighter/*/effect/*/*.ptcl
# OUT/zelda.010d0000.{ptcl,efc} -> fighter/edge/effect/edge/edge.010d0000.{ptcl,efc}
```

## Test 32 (`build/sephiroth_test32.zip`): effect colours and mesh proportions

User, test 31 (shots): effects displaced and discoloured (white / grey where Ultimate's are blue,
purple and black; arcs out of place). `vfxb_to_ptcl.py`:
- eft2's combiner: most of his emitters draw colour 0 x texture + colour 1 x (1 - texture), so the
  hue was mostly colour 1 (blue / purple) and test 31 used colour 0 alone (often white). Now each
  pixel's colour per mode is folded into the BC4 shape (its brightness) and one particle colour
  (the alpha-weighted mean); alpha from the channel the alpha mode reads (`combine`).
- meshes: Ultimate scales them in 3D (the arcs 30 x 0.1 x 30, 30 x 65 x 30), eft's scale has two
  axes: an uneven scale is built into the mesh (scale 1), an even one stays the particle's.
- missing mesh normals filled (every vanilla primitive has them), all-white vertex colours dropped,
  textures at most 128 px: the bank is 4.9 MB.
(The orange burst in the first shot was neutral air's own effect: see test 33.)

## Test 33 (`build/sephiroth_test33.zip`): plain shaders, sword glows and arcs turned

User, test 32: "Effects are still distorted and displaced. Sword attacks seem to have weird
displaced trailing"; "Neutral air isn't hitting an opponent, it's just incorrectly orange."
- Orange: `edge_light_impact2`'s blend-0 meshes (rings, circles, the dark flare) took
  `PtcFinIkeCloud`'s `FNSmoke` as their template, a shader with 32 bytes of parameters (Ike's
  Final Smash cloud) that tints them. Templates now prefer plain shaders (no parameters). (Test 33
  also required word 0x340 to be 0, read then as a shader setting: it is the volume shape; dropped
  in test 34.)
- Sword glows (`edge_sword_flare` / `_light*` / `_smash_flash`) and slash arcs (`edge_slash_light`)
  are Ultimate type 3 (directional) meshes at rest: Smash 4's type 3 turned them by their zero
  velocity (the glow below the sword, the up-air arc lying flat). Now type 4 (32 emitters), which
  keeps the emitter's frame at rest (as Zelda's Nayru's Love crystals).
- `ultimate_acmd.py`: an effect on a bone without a joint id now turns with that bone's bind frame
  too (`place`; the grab's `edge_catch_handaura` on `haver`, 90 degrees off his hand). His sword
  bones play LHaveN / RHaveN (joints 24 / 25, the same frames), so the sword effects' angles were
  already right; both games use R = Rz Ry Rx.
Package: the ptcl / efc and effect.bin (6 scripts changed); game / sound / expression unchanged.

## Test 34 (`build/sephiroth_test34.zip`): UV animation, fade on turn-off, wrap

User, test 33 (shots, with Ultimate's neutral air for comparison): the back-air arc a huge flat
white disc, the up-smash arc a solid white crescent, white L-shaped corners, neutral air a purple
haze instead of Ultimate's spiky burst, and its burst too short; "sword glows forever during back
air, even after the animation, same thing with up air and up smash". `vfxb_to_ptcl.py`:
- UV animation (eft2's per-sampler shift / scale / rotation: initial, random, a frame) wasn't
  converted. His slash arcs are full discs (`p_edgeslasharc_slash1`) that the scrolling texture
  cuts into a swing, neutral air's burst is a circle whose line texture tiled 4 x 0.5 makes the
  spikes (offline render: `edge_light_impact2` circle1 with and without). Now slot 0's eft UV block
  (corpus: 0x510 mode, bits 1 scroll / 2 scale / 4 rotate, each set exactly where its values are;
  0x514-0x54C the values, the same order as eft2's) is written, and templates are picked for the
  mode bits needed; meshes whose template can't animate UVs get the starting transform baked into
  their UVs (9 emitters).
- The fade when turned off: 0x82C (1 / frames) is set on all vanilla infinite-life emitters, 0 on
  most others. Converted emitters kept their template's: 0 on the sword flare's infinite-life glow
  (never ended), 1 on some of neutral air's (cut the frame it was turned off). Now 1 / eft2's
  alpha fade time where eft2 fades (and on infinite life), else 0.
- The follow byte 0x2F9 (0 on 86% of vanilla's infinite-life glows, 1 on 88% of the rest, taken
  as particles following the emitter) is matched to eft2's follow type in the template choice.
- Sampler wrap per axis (U bits 28-31, V 24-27); test 33 only clamped when both axes clamped.
  (Test 34 translated the codes to GX2's, swapping mirror and repeat: eft's are eft2's; test 35.)
- Alpha erosion: the fade follows the texture's remaining ink (texture - (1 - alpha)).
Package: the ptcl / efc (effect.bin as test 33's).

## Test 35 (`build/sephiroth_test35.zip`): texture repeat, mirror, flipbook cells

User, test 34 (shots, Ultimate's forward air for comparison): forward / down air draw a box at
the blade tip where Ultimate draws an X flash; neutral air still big flat shards; sword trails
slightly behind the sword (forward smash, up / back air). Checked against an offline side-by-side
of each Ultimate emitter and the converted one (scratch renderer: same UV maths both sides).
- The X flash (`edge_sword_flash2` flash3 / flash3_b, `ef_cmn_flash04`) is a quarter texture that
  eft2 repeats 2 x 2 (tex_anim repeat 3) with mirror wrap: one quarter made the box. eft2's repeat
  now goes to 0x508 / 0x50C (vanilla: 2.0 on 16% of emitters, all with mirror wrap 0x0), and the
  wrap codes are copied as they are (eft's are eft2's: test 34 had mirror and repeat swapped).
- Flipbook cells: neutral air's impact rings (`burst_ring2`, `ring2`: cmn impact00 / ring04, 4
  cells) start at cell 1 in Ultimate's pattern table; cell 0, the full solid shape, was shown. Now
  the table's first cell (flipbooks themselves aren't converted: on / off is shader-keyed).
- Meshes take the UV set eft2's uv_channel names.
Trails: positions come from the sword joint itself (LHaveN plays swordl1, the same frame and the
blade's X); a frame's lag would be the engine's sampling (to compare with Cloud's trail).
Package: the ptcl / efc (effect.bin as test 33's).

## Test 36 (`build/sephiroth_test36.zip`): UV shift direction

User, test 35 (shots): forward air's X flash right; back air's arc still a whole flat ring (Ultimate:
a crescent sweeping round); neutral air still wrong. The UV transform's form, tested on each game's
own effects (how many clamped, shifted meshes land partly on their texture over their life):
- Smash 4 (117 vanilla files): uv x scale + shift (373 of 375 axes; centred or subtracted forms
  262-282), turned about the texture's centre (20 of 20 clamped turned ones).
- Ultimate (31 fighters' VFXBs from the effect zip): uv x scale - shift (1652 of 1700; the others
  1183-1277), turned about the centre (223 of 224).
Test 34 / 35 wrote the shifts with eft2's sign (back air's arc then sat off the texture's clamped
edge: the whole ring) and baked meshes with a centred form. Now the shifts are negated and bakes use
eft2's form. Offline, frame by frame over the particle's life, the converted back-air arc
(`edge_slash_arc` line_white1, light1) sweeps exactly as Ultimate's.
Not yet: LAST_EFFECT_SET_RATE (back air's arc plays at 1.7x in Ultimate; rates differ per use, so
it needs a set per rate), flipbook animation, stripes.
Package: the ptcl / efc (effect.bin as test 33's).

## Test 37 (`build/sephiroth_test37.zip`): no screen-reading templates, stripes as directional quads

User, test 36 (shots): forward air only the X flash (no blade glow, no wind lines); back / up air
nearly right (trail off / too sharp); neutral air see-through, refracting the stage behind; down air
jagged, the glow not covering the sword.
- 33 converted emitters (all blend-0 meshes: his blade glows `edge_sword_light3`, the slash arcs,
  neutral air's burst ring, the throws' bursts...) had templates whose shader reads the frame
  buffer (`frameBufferTexture_CROSS` in the GX2 binary: refraction / distortion, 56 of 1797
  vanilla shaders): drawn as see-through distortion. Shaders reading the frame / depth buffer or
  texture arrays are no longer templates (none left in the bank).
- Stripes (eft2 types 5 / 6: his speed lines, the forward-air wind) -> directional quads (type 3,
  eft2's 2.5 x 36 scale, along their motion): `edge_attack_speedline`, `edge_gokumon_wind`,
  `edge_smashlw_speedline` now convert (46 of 46 effects); ids from 0x342002E on shift, so the
  effect scripts are rebuilt (game / sound / expression unchanged).
Bank 6.0 MB (meshes 1.9, textures 2.3; vanilla's largest, Bayonetta's, 4.6; tests 34-36's 5.2
loaded). Trails unchanged (Sword_Glow from the sword joint, as Corrin's / Kirby's).
Package: the ptcl / efc and effect.bin.

## Test 38 (`build/sephiroth_test38.zip`): stripes out again; 0x82C / 0x2F9 read from the code

User, test 37 (shots): forward-air glow shows a little; the speed lines are solid bars that never
go away (and a white bar on dash attack); neutral air round, not a burst; back / down air's sword
effects out of step, down air's flash high up and white; up air / up smash nearly right.
- Stripes are skipped again (the directional-quad stand-ins drew solid bars). eft has stripes as
  complex emitters only (types 5 / 6: 90 / 31 vanilla, Bayonetta's Witch Twist lines, Ness's PK
  Thunder): converting them needs the complex emitter's stripe block, next.
- From cross_f.rpx (0x04A64F00, 0x04A661D8): while an emitter set fades, each particle's alpha
  (+0x58) drops by 0x82C x the frame step and the particle dies at the threshold; otherwise it
  climbs back by the same rate. 0x2F9 is read right there (whether it is 0), so it belongs to the
  fade, not to following the emitter as test 34 assumed: the template choice no longer looks at
  it. 0x2F8 is read with the gravity vector (0x4A4).
- vfxb_to_ptcl: an effect that converts to nothing loses its id in the ids file (test 37's
  speed-line ids would otherwise name other effects' sets now).
Package: the ptcl / efc and effect.bin (test 33's again).

## Test 39 (`build/sephiroth_test39.zip`): Smash 4's effect runtime mapped (cross_f.rpx)

User, test 37 (shots, before test 38): forward-air glow faint, speed lines never ending, neutral
air round, back / down air's sword effects out of step, down air's flash high up, a white line on
dash attack. Read from the executable (docs/native-notes.md, docs/ptcl-format.md):
- Follow type is 0x310 (0 follow the emitter, 1 not, 2 position only; eft2's numbers), set at
  emission (0x04A5C89C), shader-keyed. 71 of his emitters had a template of another follow type;
  now ranked on it (17 position-only ones follow fully: vanilla has few).
- 0x2F9 = stop emitting when the set is turned off (eft2's is_fade_emit; test 37's speed lines kept
  emitting: 0 there, with no fade); 0x82C is the emitter's fade (the emitter ends at 0).
- Flipbooks: the block at 0x4D4 decoded (cells, table, frames a cell, random start, mode -> shader
  bit); 67 of his flipbook emitters now animate (18 without a matching template show one cell).
- eft2's "stripe" types carry no ribbon data (its ribbons are emitter plugins): directional quads
  again (test 37's never ended because of 0x2F9).
- `EFFECT_FLW_POS`: Smash 4 adds the offset to the bone's position unturned (0x0334E4B0), Ultimate
  turns it with the bone; with an offset it now follows fully (down / forward air's flash).
- Textures: BC4 aligned 0x1000 as vanilla's (not 0x2000), smooth ones halved when that changes them
  under 1%; flipbook sheets with 4+ cells a side up to 256 px. Bank 6.3 MB (test 37: 6.0 loaded).
Trails: no change found (swordl2 isn't animated; the joint is right).
Package: the ptcl / efc and effect.bin.

## Test 40 (`build/sephiroth_test40.zip`): Ultimate's effect commands read from its ExeFS

Read from Ultimate's `main` (docs/ultimate-fighter-port.md "Ultimate's effect commands"):
- `LAST_EFFECT_SET_RATE` is the set's playback speed (effect record +0x264), as Smash 4's command of
  the same name; `LAST_EFFECT_SET_ALPHA` the set's alpha (0-1; Smash 4: percent). Both were left
  out: now 44 rates and 18 alphas in his scripts (only after an effect that was converted).
- `EFFECT_DETACH_KIND` -> `EFFECT_DETACH_KIND` (6 new): neutral air's finger-snap light, up air's
  slash light, forward / down air's sword flash, back air's arc and down smash's speed lines detach
  and play out instead of being cut with the move.
- `EFFECT_OFF_KIND`'s flags are Smash 4's `Terminate_Graphic_Effect` ones in the same order (as was).
- Trails: `AFTER_IMAGE4_ON_arg29`'s arguments are Smash 4's `Sword_Glow` ones in the same order, the
  history the same (frames x 16 + 1); Ultimate's last two numbers (1.4 / 0.1) only feed its own trail
  shader, so nothing to carry over; the trail's look and lag aren't from the arguments.
Package: effect.bin (the bank is test 39's).

## Test 41 (`build/sephiroth_test41.zip`): materials closer to Ultimate's shading (he was dark)

User: "make Sephiroth more closely match Smash Ultimate's shader", "he's a bit dark by comparison to
other characters". His colour maps are dark (coat ~5% luminance; Zelda's 50-70%), but the conversion
darkened them twice more: Ultimate's AO baked into the colour (x0.45-1), and the normal map's alpha,
which Smash 4 reads as AO (docs/ultimate-fighter-port.md "Materials"), holding smoothness instead
(coat alpha ~0.13: diffuse at ~23%). Now the alpha is Ultimate's AO (gamma-encoded) and the colour
isn't darkened; Ultimate's per-material colour gain (`CustomVector8`) applied; his skin uses Zelda's
skin material (warm rim / specular / AO floor, her skin ramp). Estimated diffuse (linear colour x
the AO term, Smash Forge's formula) over the model: 0.011 -> 0.047 (c00), 0.002 -> 0.049 (c04),
Zelda 0.14. Skeleton files unchanged.
Package: `model/body/c00-c07` model.nud / model.nut / metal.nud.

## Next

1. Specials: Flare / Megaflare / Gigaflare, Blade Dash / Octaslash, Scintilla, Shadow Flare; the
   One-Winged Angel form; Final Smash.
2. Effects, sounds, portraits from the Ultimate zips.

## Test 42 (`build/sephiroth_test42.zip`): trails retract like Ultimate's

User: "Patch Smash 4's trail shader to retract like Ultimate's for Ultimate trails only". Ultimate's
trail shader samples its mask at U = 1 - t / fade, so as `AFTER_IMAGE_OFF` fades it the trail is cut
back from its tail into the sword (docs/ultimate-fighter-port.md); Smash 4's fades in place. Smash
4's trail keeps the same t and fade but no shader can see them; now (`tools/trail_shader.py`):
- `shader/effect_trail.nsh`: + trail shader 3 (Ultimate's 101), `tools/shaders/trail_retract.psh`.
- `code/cross_f.rpx` (on the latest, v19b): two stores of the trail vertex writer put t and the
  fade in the vertex colour's red / green, which the vanilla trail shaders never read.
- His 8 `Sword_Glow`s: Shader 3 (`tools/trail_shader.py acmd`; `tools/ultimate_acmd.py` now
  writes 3); his trail textures as Ultimate's pair (`tools/ultimate_trails.py --shader 3`: the
  colour texture as is, the mask in the second one's alpha with the 1.4 colour gain).
Vanilla trails keep shader 1 / 2 / 1001 and are unchanged. `tools/trail_shader_test.py`: the nsh
(other records byte for byte), the vanilla shaders' vertex-colour reads, shader 3's program run on a
Latte interpreter against Ultimate's formula (220 samples), the patched stores in Unicorn.

```
tools/latte_dis/build_asm.sh
python3 tools/trail_shader.py nsh VANILLA/shader/effect_trail.nsh OUT/shader/effect_trail.nsh
python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/trail_shader.py rpx IN.rpx)
python3 tools/trail_shader.py acmd test40/effect.bin OUT/fighter/edge/script/animcmd/body/effect.bin
python3 tools/ultimate_trails.py --shader 3 ULT/effect/fighter/edge/trail OUT/fighter/edge/effect/edge/trail \
    tex_edge_sword1.nutexb,tex_edge_sword2.nutexb=TexEdgeSwordTrace tex_edge_sword3.nutexb,tex_edge_sword4.nutexb=TexEdgeSwordTrace2
python3 tools/trail_shader_test.py VANILLA/shader/effect_trail.nsh OUT.rpx
```
Package: `shader/effect_trail.nsh`, `code/cross_f.rpx`, `fighter/edge/script/animcmd/body/effect.bin`,
`fighter/edge/effect/edge/trail/*.nut`.

## Test 43 (`build/sephiroth_test43.zip`): white patches on the sword and trims

User (shots): small parts of the model white and patchy (the sword, shoulder / sleeve trims, wrist
bands). Test 41's normal-map alpha (Ultimate's AO, PRM blue) was noise there: `resized()` scaled
the RGBA PRM with Pillow, which resizes RGBA premultiplied by alpha, and the PRM's alpha (specular)
is ~0 on the sword (def_edge_002: mean 0.5) and parts of the coat, so blue came out as black /
white blocks (sword normal alpha mean 59 instead of 230). `resized()` now scales channel by
channel. Package: `model/body/c00-c07/model.nut` (model.nud / metal.nud unchanged).

## Test 44 (`build/sephiroth_test44.zip`): emitter rotation order, endless speed lines

User, test 43 (shots): forward air's speed lines on the wrong plane, the effect around its cross
wrong, the lines never ending; neutral air a purple disc near the end; up air's trail jagged and
late; back air showing the whole swing at once; down air three crosses with a blue trail between.
- eft2 turns an emitter Z first (R = Rx Ry Rz), eft X first (R = Rz Ry Rx, as stored in vanilla's
  matrices): of 86 streak emitters in 31 fighters' VFXBs rotated about 2+ axes, the offset lies
  across the motion in 53 with Z first (13 with X first), along it in 10 (51). `vfxb_to_ptcl.py`
  (`eft_rotation`) re-expresses eft2's angles: forward air's lines (90, 0, 90) and the cross's
  rainbow ring (90, 0, 45), and 19 more emitters (dash attack, down smash, down throw, victory).
- An endless emitter that is turned off (Terminate_Graphic_Effect) with no fade rate stayed alive;
  it now gets one. `ultimate_acmd.py`: a NO_STOP follow that its own script turns off later is
  the plain follow (External_Graphic), so a script cut before the EFFECT_OFF_KIND (forward air
  landing before frame 17) still ends it (forward air's lines, neutral air's burst).
- EffectLibrary (KillzXGaming, the EffectConverter build the user sent, decompiled): eft2's
  particle types 0 billboard, 1 / 2 plates XY / XZ, 3 directional, 4 directional polygon, 5 / 6
  stripes, 7 primitive, 8 Y billboard (as converted); its v22 emitter layout matches `vfxb.py`.
- Checked, not changed: Graphic_Effect4 is EffectModule op 0x271A, a follow without the 0x8000
  (motion-bound) flag, and Terminate_Graphic_Effect reaches it (the manager's kill loop
  `0x032F0454` matches every record by id); eft's particle types 3 / 4 orient by the particle's
  world motion (v_inWldPosDf) and the eye vector / the emitter's Y (vertex shaders, uniforms read
  from the GX2 headers: `vm` 0, `pm` 4, `vpm` 8, `bm` 12, `ev` 16, `ep` 17 in the view block); UV
  scroll adds are per frame in both games (vanilla medians 0.04-0.05 vs 0.05-0.06).
Open: neutral air's disc, back / up air's trails, down air's crosses (the converted values match
Ultimate's; asked for Ultimate shots). `optional_old_trails/`: the trails on shader 1 to compare.
Package: the ptcl / efc and effect.bin.

## Test 45 (`build/sephiroth_test45.zip`): particle rotation, stripe meshes

Checked against the Ultimate moveset video (the user's Drive upload), frame by frame. Ultimate's
down air draws one tall thin spike above him and a star at the blade tip, its back air a crescent
that swings round, its neutral air a burst with no disc.
- Particle rotation is shader-keyed: a template turns its particles only if its vertex shader has
  `v_inRot` (all 3165 vanilla emitters with a rotation do). The templates ignored it: 92 of his 179
  turning emitters drew unturned. They included down air's flares, turned -90 degrees in Ultimate
  so their long axis runs along the plunge, which lay across it as crosses. Back air's slash arc
  (180 degrees, spinning) was unturned too. So were neutral air's rings (random turns), forward
  air's speed lines, up air's slash glow, and pieces of the throws and specials.
  `Templates` now ranks on rotation. One it can't bake ranks first; a fixed one (and any mesh's)
  ranks after the UV animation, which can only be frozen into a new mesh copy (his 240 KB arc
  glows: four copies, +0.7 MB). What no template draws is baked: a mesh's starting rotation into
  its vertices, a quad's fixed quarter turns into its texture and scale. Unturned now: 0. The
  mesh order is read from a turning mesh shader's vertex program: R = Rx Rz Ry (Y, then Z, then
  X), unlike the emitter's Rz Ry Rx. Lost: the spin of back / up air's arc glows (no template
  both spins a mesh and scrolls its UVs).
- eft2 stripe types (5 / 6) on a mesh -> type 4 (the emitter's frame), not type 3. Neutral air's
  `edge_light_impact` rainbow1 is a flat 69-unit disc, laid level (emitter X 90) and sent off in a
  random direction (all_dir 0.2); as type 3 it faced its motion, so it could face the camera as
  the purple disc. Also changed: the victory feathers and impact flashes (down smash, pummel,
  Gokumon impact).
Bank 6.31 MB (test 44: 6.33); ids and .efc unchanged; effect.bin is test 44's. Still open: up air's
trail jagged / late (Sword_Glow arguments of the same kind as Marth's / Ike's / Cloud's).
Package: the ptcl / efc and effect.bin, `optional_old_trails/` as test 44.

## Test 46 (`build/sephiroth_test46.zip`): forward air's X, slash arcs unturned again

User, test 45 (shots, with Ultimate's for comparison): forward tilt's arc a wide flat disc reaching
behind him (Ultimate: one swoosh in front); forward air's X drawn as a ">"; down smash a vertical
white bar.
- Forward air's X (`edge_sword_flash2` flash3 / flash3_b): eft2 pattern type 2 on a 1 x 1 sheet.
  Since test 39 it converted to a flipbook, whose UV scale (1 / cells) replaced the 2 x 2 mirrored
  repeat (test 35), so one quarter showed. A one-cell sheet is no flipbook now, and a flipbook's UV
  scale is repeat / cells. Only these two emitters changed.
- Directional meshes at rest (type 4) keep no particle rotation. The slash arcs are all turned Z
  180 (glows also Y -20 and a -15 degree a frame spin); unturned in test 36 ("nearly right"),
  turned in tests 44 / 45 (wrong: a disc, behind him too). Observed, not derived: Ultimate's
  directional basis at rest evidently cancels it (the sword glows, unturned, extend along +Y, so
  it isn't a flip of every such mesh).
Open: down smash's bar (likely `edge_smashlw_speedline` line3, a 23 x ~150 stripe quad at speed
0.1, converted as a directional quad); asked for an Ultimate shot. Bank 6.29 MB; ids / efc and
effect.bin unchanged. Package: the ptcl / efc.

## Test 47 (`build/sephiroth_test47.zip`): directional pieces by their own velocity

User: an official down smash clip. Ultimate: the speed lines lie along the sword as it comes down
(a thin streak and a wide faint band, `edge_smashlw_speedline` line1-3); no upright bar.
- eft's directional type 3 has two shader kinds: `v_inVec` (the particle's own velocity: 535 of
  1732 vanilla type-3 emitters) and `v_inWldPosDf` (its change in world position, which on a
  following emitter includes the bone's motion). No single emitter byte selects them. line3
  (23 x 180, speed 0.1) on the swinging sword had the second kind, so the sweep stood it upright.
  `Templates` now prefers `v_inVec` for type 3 (`VELOCITY_ATTR`). 3 emitters have no such template
  (Octaslash's sword flares, the pummel's ring).
- A quad's fixed quarter-turn UV rotation (nothing else animated) is turned in the image
  (down smash's lines 90 degrees, Octaslash's 90 / 180), so no template needs UV rotation.
Cost: the throws' flash lines lost their flipbook (one cell). Bank 6.28 MB; ids / efc and
effect.bin unchanged. Package: the ptcl / efc.

## Test 48 (`build/sephiroth_test48.zip`): refraction left out, shapes from the shaping texture

User, test 47 (shots and Ultimate clips of neutral, forward, back, up and down air): back / forward /
down throw and dash attack light up the stage; neutral air still off; forward air without its blade
glow and few speed lines; a blue-purple blob below him in forward / up / down air; back air a whole
flat ellipse (Ultimate: a short swoosh behind him).
- eft2 combiner shader type 1 (refraction: back throw's `indirect1` x2, the entry's `rifrection1`)
  is left out; drawn plain each was a tinted mesh.
- `shape_sampler`: when the texture `main_texture` picks fills the quad (border >= 0.1: Ultimate's
  tiling fire `ef_edge_fire05`, the slash glows' `swordflare03`) and another of the emitter's
  textures has a shape (border < 0.05; eft2 multiplies them, combiner blends 0), the shape is drawn
  and the fill folded in as its mean. 10 emitters: the hand / entry / throw auras, neutral air's
  wind-up fire, and the slash arcs' glows `light1` / `light3` (`edge_slash_arc`, `edge_slash_light`).
  Those glows are full discs (3,077 vertices, out to the rim) that Ultimate cuts to a band; uncut
  they made back air's and forward tilt's bright flat ellipse.
- A sampler's alpha comes from red when its combiner alpha input is 1 (`ef_cmn_grade00` flares:
  opaque alpha, the round shape in red).
- Directional meshes at rest that are flat ribbons along Y (the blade glows: 25.5 x 2 x ~0) get a
  copy crossed at 90 degrees about Y (`crossed_ribbon`), so the glow can't go edge-on.
- Checked: Smash 4's effect rotation (`0x03373478`, sincos `0x033723D8` run in Unicorn: sin to the
  first pointer) is R = Rz Ry Rx of the script's angles, as `ultimate_acmd.py` assumes.
Open: the blob (likely `edge_sword_light3`, the blade glow, misplaced: `optional_no_blade_glow/` has
test 44's effect.bin without it in forward / up / down air, to confirm); neutral air's burst.
Bank 6.37 MB; ids / efc unchanged. Package: the ptcl / efc, `optional_no_blade_glow/`.

User, test 48: up air, up smash and forward smash look right.

## Test 49 (`build/sephiroth_test49.zip`): bone effects turned in their sets (the facing flip)

User, test 48 (with `optional_no_blade_glow/`, then without, then facing each way): forward /
down air's blob is the blade glow (`edge_sword_light3`), only facing right; facing left it lies
along the blade. Up air / forward smash were right in the shots taken facing left.
- Smash 4 flips the angles of an effect on a bone for one facing direction. The flip changes the
  sign of the bone frame's X in the turn, so no angles put his glow (mesh +Y) along his blade
  (joint 24's +X) for both facings (vanilla sword effects lie along an axis the flip keeps).
  `tools/effect_variants.py` lists the fighter's own effects placed on a bone other than 0 with a
  turn (`scan`), `vfxb_to_ptcl.py --variants` adds a copy of each set with every emitter's
  transform turned by the script's angles (R = Rz Ry Rx: `turn_set`), and `apply` points the
  commands at the copies with angles 0 (which the flip keeps), copying the commands that name the
  effect (Terminate_Graphic_Effect, EFFECT_DETACH_KIND) for the copy in the same script.
  13 variants, 52 placements; ids "name@rx,ry,rz" (0x3420055-0x3420061) in `edge_effects.json`.
- Effects on bone 0 (his top: the slash arcs, down air's wind) look right in both facings: left.
```
python3 tools/effect_variants.py scan EFFECT_BIN fighters/edge/edge_effects.json VARIANTS.json
python3 tools/vfxb_to_ptcl.py ... --variants VARIANTS.json          (adds the "name@rx,ry,rz" ids)
python3 tools/effect_variants.py apply EFFECT_BIN fighters/edge/edge_effects.json OUT/effect.bin
```
Bank 6.50 MB, 97 efc entries. Package: the ptcl / efc and effect.bin.

## Test 50 (`build/sephiroth_test50.zip`): gradients on quads read from the centre

User, test 49: almost every move right; dash attack, neutral air, the throws and the grab not (the
purple effects flat and still; a pink diamond around the held opponent). Ultimate clip of the throws.
- `radial_gradient`: a quad whose texture is a one-way gradient (`ef_cmn_grade00`) draws it outward
  from the centre, as the flare meshes' polar UVs read it; flat, it lit a square (the pummel's and
  down throw's `pointlight1`). 2 emitters.
- Checked: eft's flipbook modes against vanilla (1 fit-to-life, frames 0; 2 loop and 4 once with
  frames a cell; 3 random, 4 random cells): his fire / smoke sheets (eft2 1 -> 1) do animate. What
  his purple effects lack is Ultimate's custom shaders: 38 emitters carry CADP / 21 CSDP (custom
  shader / action parameters), the fire / aura ones (combiner shader type 2) mix a tiling noise,
  a flipbook and a mask, often scrolled; Smash 4's templates draw one texture in one colour, and
  many lose their UV scroll ("UV animation: template has 0").
Bank 6.50 MB; ids / efc and effect.bin (test 49's) unchanged. Package: the ptcl / efc.

## Test 51 (`build/sephiroth_test51.zip`): a quad's samplers multiplied into its texture

User chose to keep converting Ultimate's purple effects (rather than rebuild them from Smash 4's).
- `bake_samplers` (quads; combiner blends 0): every other sampler of the emitter except distortion
  maps ('indirect') is sampled where Ultimate puts it on the quad (repeat, starting scale / shift /
  turn, wrap; a flipbook sampler's first cell) and multiplied into the channel the shape is read from,
  per cell of a flipbook main texture; the fill isn't folded in as a mean then. 29 emitters: the
  hand / entry / dash / throw auras and fire, the throws' smoke, the victory backdrop. Their scroll
  stays lost (frozen at the start).
Bank 6.56 MB; ids / efc and effect.bin (test 49's) unchanged. Package: the ptcl / efc.

## Test 52 (`build/sephiroth_test52.zip`): gradient glows fade to 0; a colour check for back throw

User, test 51 (shots): dash attack, grab, down / back / forward throw still off: translucent pink and
blue squares and a pink haze in back throw, a long white band in dash attack.
- `radial_gradient` rescales the profile to 0 at the rim (grade00's dark end is ~0.1: the down
  throw's bright `pointlight1` still lit a faint square).
- Checked statically, no cause found for back throw's squares: every quad's texture is ~0 at its
  border (cells of flipbooks included), every mesh has a mesh shader, blend 2 is subtract (vanilla
  `*_sub`). `optional_colour_check/`: the bank with `PtcEdgeThrowBBom` / `PtcEdgeThrowBBom2`
  emitters each in its own colour (legend in the commit's scratch log: red flare1, green ring1
  (subtract: shows pink), blue smokeBase, yellow aura2, cyan flareAdd1, magenta fire_g, orange
  particle1, white sparks1, lime line2_bk, sky line2 (Bom2); pink fireImpact1_g, brown aura1, teal
  smoke1_normal, violet lightning_ring1, gold lightning_ring1_bk, grey flashCenter_b, navy
  flashLine1_b, maroon flashLine1_f, olive flashCenter_f (Bom)).
Package: the ptcl / efc, `optional_colour_check/`.
