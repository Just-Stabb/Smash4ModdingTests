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

## Test 53 (`build/sephiroth_test53.zip`): shape in every channel, uncapped tints, the dark-fire shader

User, test 52 colour check (back / down / forward throw, grab shots): back throw's square is yellow
(`aura2`); the grab's hand has a purple square behind it; jab (test 51 shots): lines too pink.
- The squares: two templates' pixel shaders take alpha from the texture's alpha, not its red
  (Pikachu's `spark1`, colour mode 1, and Koopa's `pointlight1`, a mode-2 shader with distortion:
  the grab / forward throw hand `fire1` and `aura2`, the entry `aura2`, back throw's `aura2`, 9
  emitters with the turned copies), and vanilla's BC4 channel selectors (R R R 1) gave them alpha 1
  over the whole quad. Shapes now select R R R R
  (`SHAPE_SEL`): every template reads the shape, from red or alpha.
- Jab's tint: `ultimate_acmd.py` capped EFFECT_FOLLOW_COLOR at 255 per channel, so (0.75, 0.5, 1.5)
  became (191, 127, 255), pink. Uncapped (vanilla goes to 714: Falco); 9 commands (jab 1 / 3,
  ledge, getup and trip attacks), patched into test 49's effect.bin in place.
- Ultimate's own shaders, read from the effect file's BNSH (`tools/eft_shader_dis.py`; the user
  pointed to SSBU shader tools): custom shader 4 with flag 64 (dash attack's fires, aura and spark,
  the dash aura, Shadow Flare's finger aura, his aura: 13 emitters) colours by its alpha shape and
  outputs colour x shape x 2. `combine` does the same (`PREMULT_SHADER`), the x shape per pixel
  through the template's colour mode (2: colour 1 black; 1: as is; 0: the shape's mean).
  (`fireBlack`'s orange in the earlier dump was its unused constant; its keys are dark violet.)
- Dash attack's `FlashLine1` (the long white band) is as long as Ultimate's (55 x 1.61; scale_min /
  max are camera-distance limits, off); left as is.
Bank 6.56 MB; ids / efc unchanged; effect.bin: test 49's with the 9 tints. Package: the ptcl / efc
and effect.bin.

## Test 54 (`build/sephiroth_test54.zip`): channel selectors by the template's sampling

User, test 53 (shots): grab right; forward smash a dark band along the blade (it was right before);
down throw / pummel too faint; back throw better but magenta light everywhere; dash attack still
the white line; down air bright (its data is test 52's: Ultimate's has a bright blue-white streak
down the blade too).
- R R R R suits every template but one kind: a pixel shader that samples only the texture's alpha
  (`SAMPLE Rn.___w`, shader 123: the sword flares' `swordflare2`, down throw's `ring1`) uses it as
  a mask over a mesh shaped by its own view-angle falloff, and wants vanilla's alpha 1; with the
  shape there forward smash's flare drew a dark band. `alpha_mask_shader` reads the template's
  sample masks with tools/latte_dis/latte-dis; those keep the template's selectors.
- Shader 133 (back throw's flare discs) also reads alpha but colours by the texture: R R R R stays
  (with R R R 1 its 83-unit `flareAdd1` drew one flat magenta disc: test 52's pink haze).
- Dash attack's `FlashLine1`: Ultimate draws it lerp(colour 1, colour 0, texture rgb) x texture
  alpha, `ef_cmn_line06`'s rgb a white core ~1 unit wide and its alpha a wide glow (blue there:
  colour 1). `combine` folds both into one bluish white, the glow as bright as Ultimate's but
  white. Not changed: a two-colour fit (colour 0 / 1 from the texture's rgb against its alpha) would
  also change the approved sword flares.
Bank 6.56 MB; effect.bin test 53's. Package: the ptcl / efc and effect.bin.

## Test 55 (`build/sephiroth_test55.zip`): dash attack's line in two colours

User, test 54: option 2, the two-colour fit for dash attack's line only.
- `TWO_COLOUR` (one entry: `P_EdgeAttackDash2` / `FlashLine1`): `combine` keeps the alpha shape
  (the glow) and fits the texture's rgb against it (r ~ k1 + (k0 - k1) x shape, weighted by the
  shape: k0 1.00, k1 0.00), so the lerp template draws colour 1 + (colour 0 - colour 1) x shape
  with colour 0 = Ultimate's colour 0 track (white, lilac at the end) and colour 1 its colour 1
  (blue 0.13, 0.11, 1.0): a white core in a blue glow. Each track gets its own key fit / sections.
Bank 6.56 MB, the one emitter changed; effect.bin test 53's. Package: the ptcl / efc and effect.bin.

## Test 56 (`build/sephiroth_test56.zip`): the sampler's U / V wraps the right way round

User, test 55 (shot): dash attack still a band: as wide as the quad (6 units), solid to one sharp
edge, soft on the other: `ef_cmn_line06` (half a line, dark to bright across U, mirrored by the
repeat 2) sampled clamped across U.
- The eft sampler word holds U's wrap in bits 24-27 and V's in 28-31 (docs/ptcl-format.md), not
  the reverse: in the 374 vanilla emitters repeated along U only, bits 24-27 are always mirror and
  28-31 mirror / repeat / clamp (47 clamp: the other axis); the V-only ones agree. Every emitter
  with different wraps had them swapped since test 31 (124 here: the sword glows, slash arcs, the
  throws' rings). An odd number of quarter turns baked into a texture also swaps its repeat and
  wraps now.
Bank 6.56 MB; effect.bin test 53's. Package: the ptcl / efc and effect.bin.

User, test 56: dash attack's line gone; everything else looks right except jab and the throws.

## Test 57 (`build/sephiroth_test57.zip`): neutral special (Flare / Megaflare / Gigaflare)

The first of his specials (fighters/edge/specials.md: the plan, the move's logic, the build).
- Executable: test 42's + the four new article kinds (fire 0x18C, flare1 0x18D, flare2 0x18E, flash
  0x18F after Zelda's five; `weapon_expand.py` takes a base without a vtable 2 (dein's) now) and
  the 11 new motion slots' animations (`extra_kinds.json`). `kind_expand_test.py` /
  `weapon_expand_test.py`: 0 failed.
- `edge.mscsb`: `fighters/edge/edge.c` (vanilla Zelda + the universal mechanics, as shipped: only
  the status table functions differ, `msc_fingerprint.py --added 9`) with the move in status 0x152.
- Scripts: test 22's game / test 53's effect scripts plus the 8 special ones; `main.pac` test 22's
  plus 11 animations; effect bank test 56's plus the 20 Flare effects and 7 turned copies.
- No sounds (none of his are converted yet).


## Fix 11 (`build/hero_seph_fix11.zip`)

`edge.mscsb` rebuilt with the fixed msclang (`tools/msclang_nested_call.patch`, fighters/brave/README.md
fix 11): `edge_n_change` / `edge_n_loop`'s `MotionModule(..., edge_n_motion(edge_n_ground_motion()), ...)`
never got `edge_n_motion`'s value (the stack a value off in his neutral special).

## Fix 13 (`build/fix13_diag.zip`): Megaflare / Gigaflare

Every charge fired a Flare: Din's Fire's creation callback (`0x02F97C90`, shared by his `fire` /
`flare1` / `flare2` / `flash`) copies the owner's int `0x10000049` (Zelda's side special custom slot:
`lwz r0, 0x124(ints)` -> the creation info's byte `+0x5C`, which becomes the weapon's `0x10000005`), not
the neutral one `edge_n_generate` set. It sets `0x10000049` now. (Robin's thunder callback copies
`0x10000048`, `+0x120`: Hero's slot is right.)

## Test 58 (`build/sephiroth_test58.zip`): his clothes less washed out

User (shot, neutral lighting): "Sephiroth's clothes are a bit too light". His materials are Zelda's body
material, whose specular (white x2, a broad lobe) and rim (0.91) are added over any colour: on his
coat (colour ~0.05) a light grey sheen. Now scaled by Ultimate's reflectance per material
(docs/ultimate-fighter-port.md "Specular and rim"): coat / skirt specular 1 -> 0.1 (c04: 1.8 -> 0.18),
rim 0.91 -> 0.32. Package: `model/body/c00-c07/model.nud` (textures as test 43's).


## Test 59 (`build/sephiroth_test59.zip`): his effects on Ultimate's own programs

User (after Squirtle's effects were finished): "Can you rebuild Sephiroth's effects?" The bank rebuilt with
today's `vfxb_to_ptcl.py` (test 57's command: `build_edgefx.sh`, his 86 effects + `variants57.json`; `ef_edge.eff`
fetched again from the user's Drive zip, only that entry): every one of his 425 emitters is drawn by Ultimate's own
vertex and pixel programs (the universal shader path, docs/eft-universal-shader-scope.md; Squirtle's confirmed in
game), 0 fallbacks; 39 of them fade where they meet the scene (soft particles, the game's depth texture). Ids and
.efc unchanged: test 57's effect scripts (body and the fire article's) stay.
- Bank 18.8 MB (test 57: 9.4): the programs carry the emitter's own constants, so they don't share (shaders 7.1
  MB, textures 6.0, meshes 4.2). Squirtle's 11.5 MB loads; this size is untested in game.
- port_check over the Sephiroth chain: the same errors with and without it (none from the bank).
- Package: `fighter/edge/effect/edge/edge.010d0000.{ptcl,efc}`.

## Test 60 (`build/sephiroth_test60.zip`): Ultimate's common effects, the Flare charge ends on release

User, test 59 (4 clips): "he still seems to use some of the old fixes for effects, which I don't want for him (jabs,
dash attack, etc). Flare and its variants look ok when charging (slightly off) and it seems like the refraction effect
never goes away when released. Throws also seem slightly off." Then: "Neutral air also looks slightly off."
- The "old fixes": his scripts' `sys_*` effects (dust, smash flashes, the jab / dash / run smokes, landing, jumps,
  stars...) were Smash 4's common effects standing in. The bank now carries Ultimate's own common sets from
  `effect/system/common/ef_common.eff` (`vfxb_to_ptcl.py --extra-eff`, named by `ultimate_port.common_sets`, tinted
  as his scripts tint them: `ultimate_tints.tint_args`), on Ultimate's programs like his own: 26 sets, every
  `sys_*` name his Ultimate scripts use (22) plus the four Smash 4 common effects the translator maps back to an
  Ultimate name in his kept scripts (`sys_spin_wind`, `sys_damage_fire`, `sys_whirlwind_l`, `sys_flash`). Built by
  `tools/edge_fx_build.py` (new: test 59's command plus the common sets; reproduces this bank byte for byte).
  Smash 4 common calls in his body effect script: 35 -> 11, all in moves still Zelda's (up special's spin wind,
  down special's flash) or with no Ultimate set (`sys_screw`, `sys_bomb_a`: port_check E3 lists them).
- `edge_effects.json`: his edge_* ids unchanged; the common sets' ids after them (some sys ids renumbered, the
  scripts retranslated with them: `edge_specials_build.py`, test 57's game.bin kept). The weapon scripts come out
  the same.
- Flare's release: Ultimate's SpecialNStart turns its charge effects on with `EFFECT_FOLLOW` (`edge_fire1_hold`,
  `edge_fire2_hold`, the body's `edge_fire2_hold_aura`, `edge_fire2_hold_flash`, `edge_fire3_hold_flash`; their
  distorting fire parts are the "refraction") and only turns them off itself later in the charge; SpecialN1 / N2 /
  NCancel never do, so Ultimate's status code must. Ours (`edge_n_change`) only swapped the motion: now
  `edge_n_charge_off` turns them off (plain ids and the (90, 0, 90) variants his scripts call; as
  `EFFECT_OFF_KIND(false, true)`: emission stops, particles play out) on every change out of the charge. The burst's
  own refraction parts (`rifrection1`, Smash 4's distortion pass) were checked: one-shot, 30 / 40-frame lives, as
  Ultimate's. port_check E8 (new) checks every `EffectModule(..., 0xID, ...); // name` id in edge.c against
  edge_effects.json.
- `edge.mscsb` from today's `edge.c` (so it also has the cancel-frame check, commit cf6e4a4); msc_stack_check: 0 of
  2337 scripts with problems.
- Not done in this test: the "slightly off" Flare charge, throws and neutral air (beyond their common effects, which
  change here). Their converted values match Ultimate's file; what differs needs a closer look against Ultimate
  footage (open).
- port_check over the Sephiroth chain + this: no new errors (the rest are earlier packages' and the base's:
  models l00-l07, sound tables, Zelda's Nayru's Love meshes E5, game.bin S4 / S5).
- Bank 24.1 MB (test 59: 18.8 MB, which loaded).
- Package: `fighter/edge/effect/edge/edge.010d0000.{ptcl,efc}`, `script/animcmd/body/effect.bin`,
  `script/msc/edge.mscsb`.

## Test 61 (`build/sephiroth_test61.zip`): up special, Blade Dash / Octaslash

User: "Can you make Sephiroth's moves function like in Ultimate and port over his MSC? ... You can port all of the
specials and code." Source: Ultimate's status code, the user's `lua2cpp_decomp.zip` (ssbu-recomp of
`lua2cpp_edge.nro`), read with `tools/recomp_annotate.py`; the brake and the counter's native parts from the ExeFS.
- The move: fighters/edge/specials.md "Up special" (Ultimate's functions per behaviour; approximated: the ground
  aim limit K 90 degrees (NRO rodata not in the dump), the air end's control accel x 0.5 (no Smash 4 op), jostle
  areas / victim pull, `shield_speed_mul`).
- Body pitch: Smash 4's MSC has joint rotation (`ModelModule(0x1, joint, x, y, z, mode)`, every fighter's common
  status 0x10E, Pikachu's Quick Attack): RotN (joint 2) pitched with mode 1, removed on every exit (it persists).
- Effects: the 15 Octaslash effects his scripts use (`edge_octaslash_*`: arc / arc2 / charge / sword flare / speed
  line / direction / the 8 afterimages and wing) added (`edge_fx_build.py --add`), 10 turned variants
  (variants61 = test 57's 20 + 10); the turned variants after them renumbered (the Flare charge-off ids in edge.c
  moved: port_check E8). Bank 26.9 MB. A converter crash on `edge_octaslash_charge` fixed (mx_exec: 16 output slots).
- Also in game.bin (translator since ports_dash_fix's): throws' hitboxes before the release NoGrabRelease (port_check
  S5 gone), jab 2's hitstop (Extra_Special_Hitbox).
- Executable: fix 91's + the 0x232 motion record (SpecialHi2Landing on the landing animation): 1 word.
- port_check over the chain: no new errors (fewer: A2, S5 gone; S7 only the final smash); C2 / C4 warn on the up
  special's code: the scale read is meant (the aim effect's offset) and the rush speed is world X from the
  world-space stick (global48), both as Ultimate.
- Package: the bank, body game / effect / expression / sound / motion.mtable, edge.mscsb, code/cross_f.rpx (not the vl
  file: ports_shapes' is newer).

## Test 62 (`build/sephiroth_test62.zip`): down special, Scintilla

From Ultimate's status code (the user's decomp) and its native parts in the ExeFS (shield HP, hitstop, flash place
and charge: fighters/edge/specials.md "Down special" for every source and approximation).
- Statuses 0x155 stance / 0x15B counter or whiff slash / 0x15C shield broken, his MSC only: Zelda's Phantom article
  is no longer generated, its files untouched (the user keeps it for later).
- The shield: `tools/edge_counter_cave.py` (executable, kind 0x42 only): shield group 1 a capsule on joint 0 (radius
  6, (0, 2, 8.3)-(0, 20, 8.3): Ultimate's virtualflashshield), the first hit on it in 0x155 reported (damage, side,
  projectile) with no damage / knockback; his MSC turns it on at frame 7 and changes status (d > 25: broken;
  otherwise the counter; hitstop 20, 10 for a projectile). Unicorn self-test 0 failures.
- The flash (article 8, weapon 0x18F, `weapons/flash.c`): 5 counter tiers by d / 18 + a whiff tier (Smash 4 has no
  hitbox lerp), Ultimate's hitboxes interpolated per tier, effect scale 1.2 + 0.8 p (whiff 0.65), set at his
  position + (lr x (16 + 3.5 d / 25) (whiff 14.5), 10.5) (Din's callback spawns weapons at his head: the flash moves
  itself), 16 frames.
- Effects: the 29 `edge_senkou_*` effects added (no turned variants needed); the common sets / variants after them
  renumbered (effect.bin retranslated; the Flare charge-off ids in edge.c follow: E8). Bank 27.7 MB. A converter
  crash on `edge_senkou_hold_attack` fixed (`radial_gradient`: one axis for all channels).
- port_check over the chain: no new errors; C4 warns on `edge_lw_drift` (the drift seeded with his own world speed:
  meant) as on the up special.
- Package: the bank, body game / effect / expression / sound / motion.mtable, the flash's scripts and MSC,
  edge.mscsb, code/cross_f.rpx (test 61's + the cave). Not the vl file (ports_shapes' is newer).
- In game, untested: whether a cave-built shield shape catches hits (Hero's cave-built reflector never did; this one
  is built at setup as Marth's / Link's), its side when he faces left, the projectile flag.

## Test 62b (`build/sephiroth_test62b.zip`): the crash at load (tests 61 / 62)

User: "Sephiroth crashes when loaded" (tests 61 and 62; test 60 loads). Bisected with the user (overlays over test
62): the effect bank (test 60's loads with everything else of 62); not its file size (P1: 27.2 MB loads) nor its
set / emitter counts (P2: 162 / 906 load), but the shader entries (P3: a loading bank + 12 unused shader copies
crashes). Cause: every bank in a match shares one 44 MiB effect heap, each shader entry costs ~17 KB there (its own
program copy) and his bank (~13.5 MiB with Octaslash's effects, 14.2 with Scintilla's) ran it out
(docs/native-notes.md "Effect heap"). Fix: `tools/effect_heap_patch.py` in the executable (effect heap 60 MiB, the
16 MiB taken from the 460 MiB resource heap; 2 words). port_check E9 (new) catches a bank over the heap. Package:
test 62's files with the patched executable (install over test 60).
- User, test 62b: "He loads now" (the effect heap patch confirmed in game).

## Test 63 (`build/sephiroth_test63.zip`): down special's loop, the up special's aim arrow

- User, test 62b: "down special loops infinitely and breaks his MSC immediately". Scintilla's slash plays in Zelda's
  SpecialLwLoop / SpecialAirLwLoop slots (0x249 / 0x24D), whose motion-table entries carry the loop flag (0x2): the
  motion never ended, so the counter / whiff status (waiting for `MotionModule(0x2712)`) never left. Fix: flag
  overrides 0x0 in `tools/extra_kinds.json` (the executable's kind 0x42 motion table: 2 words differ from 62b's).
  port_check M9 (new) warns on any slot like it.
- User: "add the arrow effect used in Ultimate to show what direction he's aiming in". `edge_octaslash_direction`
  in the up special's start, as Ultimate's f_18b30: requested once (Smash 4's EffectModule 0x272C: the bone request
  plus a colour, read from cross_f.rpx: docs/native-notes.md), then placed every frame at his position + (0, 8 x
  scale) + aim x 14 x scale and rolled to the aim (0x17 / 0x18 by handle), coloured direction_effect_color
  (effect.prc) by `FighterUtil(0x8)`, the colour index the KO blast takes (inferred: player / team colour), killed
  at the start's end (its kill_kind). After the decide frame it stays on the decided direction.
- port_check over the chain + this: no new errors.
- Package (install over 62b): `script/msc/edge.mscsb`, `code/cross_f.rpx`.

## Test 64 (`build/sephiroth_test64.zip`): side special, Shadow Flare

- User: "Go ahead with Shadow Flare next". Ultimate's START / HOLD / SHOT on Zelda's Din's Fire statuses, the shot
  (flare1) and, after it hits a fighter, the orbs on that fighter: specials.md "Side special" (sources, numbers,
  what is approximated: the orbit's centre / radius, orbs that can't be hit, TRY / EXP BKB, reflection, air drift).
- The orbs share state per target through the new `SLOTn_SHARED_k` variables (`tools/acmd_ext_cave.py`, emulator
  test 0 failures). Found on the way: the standard executable's `0x0F0003xx` variables (VAR_, TIMER_, ...) read 0
  since Hero fix 79 (position_vars_cave re-applied after acmd_ext_cave undid its hook); `edge_specials_build.py
  --rpx` now applies acmd_ext_cave last (port_check X1 checks it).
- Effects: the 9 `edge_shadowflare_*` added (bank 29.1 MB; the common sets / variants after them moved 9 ids, the
  Flare charge-off ids in edge.c with them: E8). flare1: `"on_hit": 1`, max 4 (`tools/extra_kinds.json`).
- port_check over the chain + this: no new errors.
- Package (install over 63): the bank, body game / effect / sound, flare1's scripts and MSC, edge.mscsb,
  code/cross_f.rpx. Not the vl file (ports_shapes' is newer).
- Untested in game: the hit-target search (in hitstop, nearest), the orbs' hitbox placement by MSC, a weapon's
  shared-variable writes on a fighter, EffectModule 0x3 / 0x17 on world-placed effects.

## Test 65 (`build/sephiroth_test65.zip`): Shadow Flare's orbs, Scintilla's multi-hit

User, test 64 (clip): "Side special doesn't create the orbs"; "Down special's effects look incorrect, not layered or
full and doesn't multihit".
- Orbs: the shot hit (its beam_hit played) but never became the orbs: flare1.c kept fire.c's status count
  (`global7 = 0x2`) while registering statuses up to 4, and the scaffold refuses a status at or past it. Now 5.
  The hit fighter is now the nearest one (hitstop counted 4 x nearer) other than Sephiroth, his slot found at the
  spawn (the shot's spawn point minus his head offset). port_check W2 (new) checks weapon MSC status counts.
- Scintilla: the flash (a dein copy) kept dein's hit method, which removes the weapon when its attack connects: the
  multi-hit (rehit 5 from frame 0, the finisher at 15) ended at the first hit, its effects with it. Now
  `"on_hit": 0` (stay in its status) with the shield bit (`"on_hit_bits": "0x17"`). port_check W3 (new).
  The whiff's look (the burst gone after ~12 frames in the clip) isn't changed: to compare with Ultimate's.
- port_check over the chain + this: no new errors.
- Package (install over 64): code/cross_f.rpx, script/msc/flare1/flare1.mscsb.

## Test 66 (`build/sephiroth_test66.zip`): Shadow Flare's shot, his turn, Scintilla's finisher, the aim arrow

User, test 65: "The main hit for side special doesn't appear now. It also seems to automatically turn him and
sometimes face the opposite direction. Down special's multihit ender doesn't happen." And (clip): "the arrow on Up
special doesn't appear correctly and nowhere near the correct location".
- The shot: with the end status working (test 65) its wall / floor test (`GroundModule(0x2722)`, the Flare's) ended
  it at once (inferred: 10 above the floor). Now a wall is "moved under half its speed since the last frame".
- The turn: `global48` is the stick's screen x (the reverse tilts compare it with the facing); the hold's turn
  compared it alone (turned whenever held left). Now stick x x lr <= -0.2, Ultimate's.
- The finisher: the multi-hit's Part 0 hit log stays over Remove_All_Hitboxes, so the frame-15 finisher (Part 0)
  missed whoever the multi-hit had hit. The finisher is Part 1 now (as Supamario's Kamehameha finish).
- The arrow: moved by handle (0x17 / 0x18) after a 0x272C request (the bone request + colour) it drifted away from
  him, thin (clip). Now a world request (0x3) as Smash 4's own code does before moving one (func_1764); its team
  colour is dropped (no MSC op colours a handle): the emitters' own colour.
- port_check over the chain + this: no new errors.
- Package (install over 65): flash game.bin, edge.mscsb, flare1.mscsb.

## Test 67 (`build/sephiroth_test67.zip`): Shadow Flare's shot, Scintilla's finisher and layers

User, test 66: "side special's initial hit still doesn't show up"; "Down special's finishing hit also doesn't land";
"Up special's arrow is a bit cut off" (shot: now placed along the aim; part of the chevron missing).
- The shot: no wall test at all now (test 66's "moved under half its speed" likely saw the kinetic's one-frame
  lag as a stop); it flies its 7 frames (Ultimate's life; past a wall: left out).
- Scintilla: the flash's removal (17 frames counted in its MSC, hitlag included) came before its script (stopped in
  each multi-hit's hitlag) reached the frame-15 finisher. (Assumed here: a dein copy's script never passes frame 0;
  wrong, user: "Flare's explosions do hit"; the port_check W4 added for it is gone again.) Its scripts are frame 0 now (attack*: the multi-hit, edge_senkou_hold, the first hold_attack) and
  finish* (the frame-15 finisher, Part 1); flash.c counts its frames outside hitlag and plays the rest:
  edge_senkou_hold_attack at 2 / 4 / 6 / 8 / 10 (Ultimate's offsets, +- 7 at random), edge_senkou_hold_end at 14,
  the finisher at 15, gone at 17. extra_kinds `"motions": 12`.
- The arrow: not changed (a directional quad, Ultimate's billboard type 6; to compare with Ultimate's).
- port_check over the chain + this: no new errors (W4 on fire).
- Package (install over 66): code/cross_f.rpx (the flash's 12 motions), the flash's scripts and MSC, flare1.mscsb.
- User, test 67: "Down B works and side B causes a crash specifically if it hits an opponent. Down B's effects look
  the same as before."

## Test 68 (`build/sephiroth_test68.zip`): Shadow Flare's crash on a hit (attempt)

User, test 67: "Flare's explosions do hit. Down B works and side B causes a crash specifically if it hits an opponent.
Down B's effects look the same as before."
- The crash (inferred, no log yet): an appearing orb's hitbox is removed (no attack in flare2's PRE) but its offsets
  were still set every frame (`AttackModule(0x1, id, ...)` on a removed hitbox). Now only an orb whose hitbox is in
  play is moved.
- Scintilla's look: unchanged (Ultimate's layers: the dark sphere, the bright star flare of edge_senkou_hold_end,
  the effect lights tinting him): to compare offline with fx_render.
- Package (install over 67): flare1.mscsb.

## Test 69 (`build/sephiroth_test69.zip`): the aim arrow in front of him

User: "Up special's arrow is also still slightly hidden". It was at his own depth, so his coat and sword (nearer the
camera) covered part of it: now 6 toward the camera. Package (install over 67 / 68): edge.mscsb, flare1.mscsb (test
68's crash attempt, included).

## Bisect 70 (`build/sephiroth_bisect70.zip`): Shadow Flare's crash on a hit

User, test 69: "Sephiroth side special still crashes when it hits an opponent"; Cemu's log ends on
`GX2RSetAttributeBuffer(): Offset exceeds buffer size` 32 times a frame (no exception line). That message came before
from the NU model renderer's vertex streams (Supamario's Kamehameha models; Hero's Whack, a hit effect not loaded in a
normal match). The shot's own hit (test 64: hit effect 0x13 purple, no crash) isn't it. What starts with the orbs:
their effects (`edge_shadowflare_bullet`: 8 emitters, sphere meshes, x 5 orbs), their hitboxes (ids 0-4, Parts 0-4),
the shared variables on the target. Three overlays of `flare1.mscsb` over test 69, one part off each: A no orb
effects, B no orb hitboxes, C no shared variables.

User: "A and C crash but B does not": the orb hitboxes. Dein's attack set-up (`0x032107B4`, weapon kind 0x22's
object, vt +0xC) gives every dein copy 7 hitbox IDs and **2 Parts** (hit-record groups); the module indexes the
groups by a hitbox's Part without a check (`0x02C08848`), so the orbs' Parts 2-4 wrote their hit records past the
array when they connected (`docs/native-notes.md` "AttackModule sizes").

## Test 70 (`build/sephiroth_test70.zip`): Shadow Flare's orbs on Parts 0-1

- Orb i's hitbox is Part i % 2 (IDs 0-4 stay: 7 there).
- Ultimate's orbs are objects of their own, a hit record each, and a new status (appear done, TRY, EXP) starts a new
  one. Smash 4's MSC has no command that clears hit records (`0x2718` / `0x2719` keep them), so a new ACMD command,
  `Hit_Log_Clear(Part)` (`tools/acmd_ext_cave.py`, `docs/acmd-extra-commands.md`), runs the game's own clear
  (`0x02C10660` on the Part's lists). The orbit script starts with it on the Parts flare1.c flags in VAR_20 (1 / 2 /
  3 both) when an orb's appear ends, it strikes or explodes. Still approximated: the 3 orbs on Part 0 (and the 2 on
  Part 1) share a record while orbiting (rehit 45 per Part, not per orb), and an orb's clear also clears the others
  on its Part (8 frames apart, so the earlier strike is mostly over).
- `code/cross_f.rpx`: test 67's with the new command (only the ACMD cave changes: 97 words in
  `0x04B90004`-`0x04B91FF4`; 2 words of that cave are left). Emulator tests (`tools/acmd_ext_test.py`): Part 0 / 1
  (both lists), out of range, -1, skipped, no AttackModule.
- port_check W4 (new, ERROR): a new article's hitbox ID / Part past its base's AttackModule (`WEAPON_ATTACK_SLOTS`:
  dein 7 / 2); it flags test 69's orbit script.
- port_check over the chain + this: no new errors (39 -> 38: W4 gone).

## Test 71 (`build/sephiroth_test71.zip`): Shadow Flare's orbit per fighter

User, test 70 (clip on Donkey Kong): the shot's hit is right (1%, a small stun), but an orb then hits for 7% and
launches him while orbiting; charged, "the same hitboxes that the orb use multihit many times over but at the
incorrect timings". The orbiting orbs have Ultimate's edge_flare2 Fly hitbox (7 damage, 50 degrees, rehit 45), but
Ultimate's ring sits on each fighter's `edge_flare_node` (`waist`) + offsets at `edge_flare_radius`, all per fighter
in `fighter_param.prc` (Donkey Kong: radius 17, offsets 4 / 3 / 0), just outside the body. The port used 14 around
his position + 9 for everyone: inside Donkey Kong, so every orbit pass hit him (every 45 frames, and again after each
orb's new record).

- `tools/edge_flare_targets.py` writes the table into flare1.c (`fl_target_shape`, 71 kinds): radius from Ultimate;
  centre = the joint on the Smash 4 model's rest pose (`model.vbn`; the ports' own models) with Ultimate's offsets in
  its axes, x the model size (fighter_param 0x0300002C; a port keeps its base's), as height / forward offset from the
  fighter's position. Charizard is Ultimate's `plizardon`; Giga Bowser (Ultimate: radius 0) takes Bowser's row with
  the radius x his waist height / Bowser's (54.6, approximated).
- The target's kind: new read-only quantity +5 of `0x0F0000A0 + 8 x target` (`SLOTn_KIND`, `tools/position_vars_cave.py`;
  emulator tests in `tools/position_vars_test.py`). flare1.c reads it when the orbit starts.
- Still approximated: the centre doesn't follow the target's animation (Ultimate's follows the joint), size changes
  aren't followed.
- `code/cross_f.rpx`: test 70's with the variable cave rebuilt (488 words, all its own), the ACMD cave applied after
  it as before (`Hit_Log_Clear` tests unchanged).
- port_check F1 (new, WARN): a fighter kind with no row in the table. Over the chain + 70 + this: no new errors.

## Test 72 (`build/sephiroth_test72.zip`): Shadow Flare's orbit on the moving waist, no orbit hits; Scintilla's wall

User, test 71 (clips): side special "acts almost the same as before"; down special's effects still wrong; the up
special's arrow still cut off.
- Shadow Flare: Donkey Kong still took the 7% orbit hit 1.2 s after the shot (no strike is due for 4 s). The ring was
  centred on his T-pose waist (19.5 up); in game he's hunched, his arms on the floor, inside a 17-wide ring. Now
  the centre is the target's waist joint where it is each frame: a new variable range reads a fighter's joint
  through its own `ModelModuleF(axis, bone)` (`0x0F000290 + 4 x target`: write the bone, read X / Y / Z;
  `tools/position_vars_cave.py`, emulator tests), the bone per fighter from `tools/edge_flare_targets.py` (`WaistN`,
  ROB `Waist3N`), + Ultimate's offsets in the joint's rest-pose axes.
- And in the user's Ultimate clip the orbiting orbs pass through Donkey Kong's hands with no damage at all: the
  orbiting orbs never hit their own target there. A Smash 4 hitbox can't leave one fighter out, so orbiting orbs
  have no hitbox now (someone else walking into the ring isn't hit, approximated); strikes (TRY, 6.5) and explosions
  (EXP) as before, their offsets set only while they have one.
- Scintilla: Ultimate's barrier (`edge_senkou_shield`) is a honeycomb wall, 7 rows of 4-5 hexagon meshes, each row a
  child emitter of HexagonFlare01 (one still particle); the converter drops mesh children and all but one child
  (eft's children are quads, one each), so only Hexagon08's column showed. `vfxb_to_ptcl.py` `promote_children`: such
  children become emitters of their own (rows at 9.9 ... -13.8, from frame 3). The bank is test 64's otherwise (every
  effect id the same, 29.17 MB).
- The arrow (`edge_octaslash_direction`, one directional quad `tri1`: half a chevron, mirrored across U with the
  2 x U repeat): one arm of the outer chevron ends in a diagonal cut in game. Not found from the data; asked the user
  for Ultimate footage of it.
- port_check over the chain + 70 / 71 / this: no new errors.

## Test 73 (`build/sephiroth_test73.zip`): Ultimate's cancel windows; Shadow Flare's height and flash

User, test 72 (clips, Ultimate's beside ours): "Side Special spawns too low and produces too much light, down special
and side special have different recovery than in Ultimate, down special still looks off"; and the rule "when doing an
Ultimate port, ensure the cancel windows are the same" (CLAUDE.md, `port_check` C1, the guide's bug catalogue).
- Cancel windows (Ultimate's motion_list cancel frames, `CancelModule::is_enable_cancel` in the status code):
  - Shadow Flare's shot (`edge_s_shot_loop`) never tested its cancel and played to its end: now actionable from 31
    (`special_s` / `special_air_s`), as Ultimate's 1a060.
  - The vl file with Ultimate's cancel frames was built for every test since 58 but left out of the packages: the game
    kept test 57's, where Blade Dash's end cancelled at 34 (Ultimate 27), Octaslash's at 35 (56), the shot at 40 (31),
    Scintilla's slash / break at 0 / 47 (52 / 42; their loops test the frame themselves, so those two were right).
    Shipped now (`param/fighter/fighter_param_vl_edge.bin`).
  - The taunts kept Zelda's 80 / 100 / 110: Ultimate's 50 (`ultimate_acmd.py` `CANCEL_ONLY`).
  - The same vl brings the rest of what the build has written since test 58 (all from Ultimate's motion_list): the
    blend frames into 13 common motions (byte 1), and no intangibility on the up special's 0x231 / 0x232 / 0x239
    (Zelda's Farore's Wind frames, bytes 3 / 4 = 34, were still on: Ultimate's Blade Dash has none).
  - Scintilla's whiff: 28 (stance) + 59 (the slash to its cancel at 52: frames 1-5 at half speed, 30-50 at 1 / 1.15)
    = interruptible at 87, SmashWiki's figure; unchanged.
- Shadow Flare's shot flew along the floor (Ultimate: from his hand, offset_y 10). It was placed from the point Din's
  callback spawns it at, taken as his head (18.6 up, from the converted motion); in game that point is ~9 lower. The
  shot now finds Sephiroth's slot by kind (0x42, `SLOTn_KIND`) and is placed at his position + (lr x 10, 10), air
  (lr x 10, 7), Ultimate's offsets (main.bin 0x9e1770).
- The flash at his hand (`edge_shadowflare_start`): same size and place as Ultimate's (both ~9 units across on the
  clips), but deep violet where Ultimate's is lavender (the disc's mean on white: ours 151 / 76 / 211, Ultimate's
  186 / 157 / 237: about 0.55 x the coverage). FlareBack2's alpha x 0.55 (`--test-alpha-for`): matched by measurement,
  not from the data. Why the converted disc is denser (its colour keys black -> purple over a 4-frame life, draw path
  21) is still open.
- port_check over the chain + 70-72 / this: 38 errors as before (none new), C1 clean.
- Still open: Scintilla's barrier is fainter than Ultimate's bright cyan wall and has no white dissolve before the
  slash (Ultimate frames 8-10); the arrow (footage asked for).

## Test 74 (`build/sephiroth_test74.zip`): Scintilla's barrier

User, test 73: "Side B works now, fix down special's barrier next" (test 73's clips: the wall a thin, faint column
where Ultimate's is a bright honeycomb, and no white dissolve before the slash).
- Ultimate's wall rows (edge_senkou_shield Hexagon01-07) and the dissolve / end rows (`success1-7`,
  `success_end*`, `success_end*_l`) are line emitters: eft2 volume 13, 4 or 5 hexagons evenly along X over 13.8 /
  18.3, both ends (the rows alternate: a honeycomb). eft's line (cross_f 0x04A51B08) runs along Z, its length the
  radius's z and its count the particles of an emission; the converter wrote neither, so each row was one hexagon
  and the rows stacked into a column (7 hexagons for Ultimate's 31). Now each line is an arc of eft's even circle
  (0x04A4BF18: (R sin a, 0, R cos a), an arc's points start + sweep i / (n - 1)): R 1000 about pi, the emitter
  moved back R along Z, n points an emission. They lie along X to 0.04 units (`vfxb_to_ptcl.py` `LINE_R`).
  51 emitters: the wall, the dissolve and end rows, Octaslash's `edge_octaslash_line` hitline2_1 (7 along 40) and
  Shadow Flare's `edge_shadowflare_beam_hit` line2 (5 along 40, line_center -0.5 taken as eft's own: the points
  shifted by -c L / 2, inferred).
- The wall's faintness was mostly the count (one hexagon a row); compared on fx_render the wall and the white
  dissolve (the success rows at the slash's frame 0, gone by 3) now come out as rows of 4 / 5. Its brightness
  against Ultimate's still to check on the next clip.
- `port_check` E8 eft-line-volume (a converted emitter left on eft's line volume); over the chain + this: 38
  errors as before, none new.

## Test 75 (`build/sephiroth_test75.zip`): Scintilla's wall along Z; Shadow Flare's beam where the shot is

User, test 74 (clip): "Down specials wall looks more full but stiff and still incorrect. Side special's initial hit
effect still seems to spawn too low."
- The wall: test 74 was wrong about the axis. Ultimate places an "XY polygon" mesh by its emitter's matrix alone
  (vfxb_to_ptcl.py's notes, Squirtle's wave1s), and Scintilla's hexagon mesh lies in its YZ plane (2 tall, 1.73 wide
  at scale 1), so the rows can only tile along Z, as eft's own line runs (fx_render's model of main.bin's emission
  draws them so too). Laid along X (test 74), every hexagon stood across its row: the gaps and the stiff look.
  Now each row is eft's line: radius (0, 0, line_length), line_center at 0x374 (vanilla keeps -1 / 0 / 1 there: a
  fraction, as eft2's), num_divide_line particles an emission: rows of 4 / 5 hexagons 5 tall x 4.33 wide
  (x 2.5), 4.6 apart along a row and 3.95 between rows: Ultimate's packed honeycomb. Test 73's only bugs were the
  length and the count. Same for the dissolve / end rows, Octaslash's line and the beam hit's line2 (51 emitters).
- The beam (`edge_shadowflare_beam`, a 30-long streak whose particles stay where they're born): Fly's script laid it
  at frame 0 with EFFECT_FOLLOW on the shot's top joint, and that joint's matrix is the one from before flare1.c
  moves the shot (Din's creation point, on the floor). So the streak on the floor in tests 72 - 74 was never where
  the shot was: test 73's "the creation point is ~9 lower" was a wrong reading of it. fl_fly_main now lays the beam
  itself (EffectModule 0x3, world placed, turned to his facing) at the moved place, his position + (lr x 10, 10)
  (air 7); Fly's script has no beam now. The shot's hitboxes still take the top joint's matrix on their first
  frame (the creation point, one frame).
- `port_check` E8 eft-line-volume now flags a converted line without its own length (eft2's default radius) and
  test 74's arcs; over the chain + this: 38 errors as before, E8 clean.

## Test 76 (`build/sephiroth_test76.zip`): Shadow Flare's beam travels with the shot

User, test 75: "Down special wall looks right now, fix the up special arrow next, side special seems to be offset into
the wrong axis now" (a screenshot: the beam at hand height, but laid back through him).
- Test 75 laid the beam once at the spawn (EffectModule 0x3) and left it there: centred on the spawn, the 30-long streak
  reached back through him and never moved. Ultimate's is an EFFECT_FOLLOW on the shot (its particles follow the
  emitter: eft follow type 0), so fl_fly_loop now moves it with the shot every frame (EffectModule 0x17 by handle,
  `fl_beam`) until the shot hits or ends, then leaves it (Ultimate's EFFECT_DETACH_KIND).
- The arrow (`edge_octaslash_direction`): fx_render's new `--effect NAME --call x,y,z,rx,ry,rz,size` draws one effect
  on its own. Ultimate's own vertex program, run on the arrow, gives U 0 - 2 across the quad (the texture is half a
  double chevron, mirrored at U 1 into the whole), V 0 - 1; the sampler mirrors U (0) and repeats V (1); edge.c places
  it by EffectModule 0x3 (radians) and turns it by 0x18 (degrees, as vanilla's own calls); no depth fade on it. Nothing
  in the data shows a cut, so test 76 leaves it as it was; a screenshot of ours (and of Ultimate's) asked for.
  (fx_render's own mirrored half draws as a sliver on both sides: its mirror sampling, not the port's.)

## Test 77 (`build/sephiroth_test77.zip`): the aim arrow whole

User, test 76 (a screenshot and a clip of Ultimate's up special, from their native build): the arrow is a whole double
chevron along the aim; ours "cut off" since test 63 ("one arm of the outer chevron ends in a diagonal cut").
- The arrow's program (Ultimate's own, the universal path) makes each corner from the vertex id's bits: x from bit 0,
  y from bit 1 (`if (p0) r4 = 0.5`, `if (p1) r5 = 0.5` after taking bits 0 - 1 of `uint(gl_VertexID)`), the strip
  order, and Ultimate draws its quads as strips. eft draws its quad as GX2 QUADS (cross_f 0x04A66B54: mode 0x13, its
  corners at 0x04A66B9C cyclic), and the lowering gave every program the cyclic table's id: the quad folded, a wedge
  from two corners to the middle missing. fx_render (its new `--effect` and FX_UV_RAMP texture) showed the fold on
  both sides, as it drew Ultimate's side with the same cyclic triangles. Now such programs get the id of eft's own
  corner (`ult_to_latte.quad_id_bits`); both sides draw the whole double chevron.
- The same program pattern is in 348 of his emitters (attack lines, sword flashes, ...): each was missing that wedge
  too, a cut end on long thin ones. All are drawn whole now (the bank is the only file in this package).
- Placement checked against the clip (the training grid, 16.6 px a unit): the arrow's centre at (0.5, 7.5) from his
  position + 13 along the aim; ours (0, 8) + 14.

## Test 78 (`build/sephiroth_test78.zip`): forward air's speed lines lie along the swing; test 77's arrow

User, test 76 (clip): forward air's speed lines "vertical instead of horizontal". Test 77 (the aim arrow whole, above)
was held back for a check of the quad fix over all his programs and goes out in this one.
- Ultimate's `EFFECT_FLW_POS(_NO_STOP)` follows the bone's position: the offset turns with the bone, the effect's
  angles stay in the fighter's frame. Smash 4's position-only follow turns neither, so the translator follows such
  calls fully (the offset right) but took their angles in the bone's frame: the lines on `swordl2` stood along the
  blade. `ultimate_acmd.py` now takes the angles into the joint's frame through the joint's turn at the spawn frame in
  the script's own Ultimate animation (motion_list -> `c05attackairf.nuanmb` etc., `BonePose`). The joint's turn while
  the effect lasts stays: 0.1 degrees in forward air's frames 13 - 17, 6 in up tilt's 20 - 25.
- Calls changed: forward air's speed line and sword flash, up tilt's speed line, down air's flash, dash attack's three
  hand effects (aura, dash, dash2). 7 turned variants added (`variants78.json` = test 72's 30 + 7; ids 0x34200B6 -
  0x34200BC); the common sys_* sets after them moved 7 ids (body scripts rebuilt; the articles' scripts and edge.c use
  none of them).
- Quad fix check (`ult_to_latte_test.py edge --mode eft --stage vs`, all 696 vertex programs, in chunks): 693 pass;
  567 / 621 abort the test's native executor and 657 (sparks1) differs, the same with the lowering before the fix.
- Package: the bank (ptcl, efc: bank 29.25 MB, 139 sets) and the body effect.bin. port_check over the install chain
  and tests 70 - 78: 38 errors, as test 77 (none new).

## Test 79 (`build/sephiroth_test79.zip`): held forward air, the extending sword

User: forward air as now when tapped. Held 6 frames or longer, the sword extends like Snake, steered in the 4
cardinal directions:
- It turns every 8 frames, can't cross itself, and can't go back until it is 24 units forward.
- It goes back along its path on release.
- Fighters the tip hits ride along and take a second hit.
- The sword trail follows the tip.

User's numbers: 3 units a frame, 300 at most, slightly lower gravity, normal landing lag (landing drops them),
tip-only catch, 5% catch, end hit 11% at fair's angle with less knockback growth.

The design, constants and what isn't proven in game: `fighters/edge/snake_fair.md`.
- **Model:** 15 new bones (the blade, 13 runs, the point) with their pieces, in every costume. 15 small bones
  folded for room: finger tips and lips; the skirt kept.
- **MSC:** the `SNAKE FAIR` block of `edge.c` (`tools/edge_snake_msc.py`), its globals under 0x86.
- **ACMD:** fair's game and effect scripts (`edge_specials_build.py snake_fair_scripts`).

Package:
- `model/body/c00-c07/` `model.vbn`, `model.jtb`, `model.nud`, `metal.nud`. The materials are test 58's
  (`--materials-from`); the textures are unchanged.
- `script/msc/edge.mscsb`.
- `script/animcmd/body/game.bin` and `effect.bin`.

port_check over the install chain and tests 70–79: 30 errors, 8 fewer than test 78. The ones gone are the old
skeleton's joint table 0, which the new jtb fixes. No new errors.

## Test 80 (`build/sephiroth_test80.zip`): test 79 crashed loading him; back to test 78's Sephiroth

User (Cemu log): the game crashes when Sephiroth loads.
- **Cause:** test 79's MSC hid the extending sword's 15 pieces every frame from load, with ModelModule scale on 15
  joints. Every joint the MSC poses is an entry in the model's joint-override list. The game appends one per new
  joint (`0x02C64078`) and never checks the list's size.
  - The extra entries overwrote the heap: the log's vertex-buffer errors, then a hash lookup reading a count of
    0x3A83126E, the 0.001 hide scale.
  - Vanilla scripts pose one or two fixed joints.
- **Test 80:**
  - Model files: the 136-bone skeleton and joint table (`model.vbn`, `model.jtb`) as before test 79, test 58's own
    `model.nud`, and the matching `metal.nud`, for every costume.
  - Test 78's `edge.mscsb`, `game.bin` and `effect.bin`.
  - `edge.c` restored and the held forward air turned off in the build (`edge_specials_build.py` `SNAKE_FAIR`).
- **New check:** `port_check` C6 joint-overrides flags joint ops run from a loop and table-1 joint IDs (1000+).
- port_check over the chain and tests 70–80: no new errors.

The held forward air needs its runs drawn without posing many joints of his own model. The candidates are
articles (one stretched blade piece each, posed by its own posture) or world-placed effects. See
`fighters/edge/snake_fair.md`.

## Test 81 (`build/sephiroth_test81.zip`): his skeleton back; Shadow Flare's shot at hand height on the ground

User, test 80 (clips): "Sephiroth's bones seem incorrect and the sword doesn't appear in any attacks"; side special
"still spawns too low, but this time specifically on the ground".
- **Skeleton:** tests 79 and 80 built his skeleton with `--joints SwordL1,SwordR1` (a stale command) instead of
  this README's `--have SwordL1,SwordR1`.
  - With `--have`, LHaveN / RHaveN play the sword bones and the motions animate them. With `--joints`, the swords
    are bones of their own that no motion moves, and every bone after them shifts.
  - Test 80 shipped test 58's meshes (built for the `--have` skeleton) on the `--joints` one: the coat's panels
    rigid, the sword left at its bind.
  - Rebuilt with `--have`, every costume's `model.nud` is byte for byte test 58's. Test 81 ships that build's
    `model.vbn`, `model.jtb`, `metal.nud` and `model.nud`.
  - New check: `port_check` M9 have-bones (a `--have` port's skeleton with bones of their own by those names).
- **Shadow Flare's shot:** fired on the ground, it sat on the floor; in the air it was at his hand.
  - Clip: the start flash at his hand, the beam along the floor.
  - Tests 65 / 66 had already found the grounded shot touching the floor as soon as it spawned.
  - Fix: its fly status puts it in the air (situation and the air's ground correction). Its spawn height (his
    position + 10, air + 7, Ultimate's) is held every frame it flies, and its beam is laid at that height.
  - `weapons/flare1.c` → `flare1.mscsb`.
- port_check over the chain and tests 70–81: no new errors.

## Test 82 (`build/sephiroth_test82.zip`): the held forward air again, its sword drawn by articles

User: "Go ahead with the article version of forward air". The design and the whole build are in
`fighters/edge/snake_fair.md`; in short:
- **Two new article kinds**, copies of Zelda's light arrow (`tools/extra_kinds.json`): `snake` 0x199 (a run of the
  extended blade, up to 12 at once) and `snaketip` 0x19A (the point, kept on hit). They are his articles 9 and 10.
  Each has its own model (`model/snake`, `model/snaketip`, from `tools/edge_snake_articles.py`), its own MSC
  (`weapons/snake.c`, `weapons/snaketip.c`, from `tools/edge_snake_articles_msc.py`) and its own scripts.
- **Each article poses itself.** It reads his path from his slot-shared variables (VAR_24–VAR_31) every frame,
  places and turns itself with its own posture, and a run stretches its one end joint to its length. His own model
  poses only one joint: EdgeBladeL (bone 26), to hide the real blade while the extended one is out.
- **His skeleton:** test 81's (`--have`) plus EdgeBladeL at bone 26 in every costume, UplipL1 folded to keep 136
  bones; `--materials-from` test 58. Every costume's `model.vbn`, `model.jtb`, `model.nud` and `metal.nud` ship.
- **His MSC** (`edge.c`, `tools/edge_snake_msc.py`): the joint posing is gone. The move publishes the path and
  makes the articles, and the catch is the tip's position (a fighter in hitstun within 22 of the tip).
- **The point's scripts:** the 5% catch and the sword trail, moved from his scripts onto the point.
- `tools/weapon_expand.py`: new kinds need only be consecutive overall (sorted), not in the file's order.
- `ModAnimNames.txt`: `Move`, the articles' one motion. Sm4shCommand reads the file from beside its exe, so
  copying the new file there is enough.
- Checks:
  - `kind_expand_test`: no failures.
  - `weapon_expand_test`: one failure, Hero's (fighter 0x45) article list in a different order than the test
    expects. The shipped test 72 executable fails it the same way, so it isn't new.
  - `port_check` over the chain and tests 70–82: 30 errors, the same as test 81. No new errors or warnings; C6
    (joint overrides) is clean.
- Package (install over 81): `code/cross_f.rpx`; `model/body/c00`–`c07` (`model.vbn`, `model.jtb`, `model.nud`,
  `metal.nud`); `model/snake`, `model/snaketip`; `script/animcmd/body` `game.bin` / `effect.bin`;
  `script/animcmd/weapon/snake`, `snaketip`; `script/msc/edge.mscsb`, `snake/snake.mscsb`,
  `snaketip/snaketip.mscsb`.
- Not proven in game: see snake_fair.md's last section (op 7 on a weapon's joint, the light arrow's copies loading
  their models, 12 at once, the turn signs, the trail on a weapon).

## Test 83 (`build/sephiroth_test83.zip`): the held forward air's articles get a MotionModule; the hold after the clean hit

User, test 82: "When forward air is held, the sword doesn't extend and there is no hitbox." And: "On this next build,
can you make the holding window start after the initial hitbox of tap forward air?"
- **Cause:** a weapon kind's modules come from its row of 28 constructors (`0x103464A8`, docs/native-notes.md "Weapon
  modules"). Zelda's light arrow, the articles' base, has no MotionModule (slot 7, accessor `+0x44`, a null
  constructor). A weapon's ACMD runs off its motion, so the point's scripts (the 5% catch, the trail) never ran.
  - The copies also had the arrow's spawner (its article list callback `0x02F9815C`). It makes the arrow on the
    owner's joint 0x19 in mode 4 (on his hand), where dein's (`0x02F97C90`) makes it free.
  - Ruled out: the copies' files load (the loader's categories, flags `0x80` / `0x1` / `0x100`: the arrow has none,
    as dein); the slot-shared path variables (as Shadow Flare's); the arrow's AttackModule (the same set-up as
    dein's, 7 IDs / 2 Parts: the point's ID 0 Part 0 fits).
- **Fix** (`tools/weapon_expand.py`, `tools/extra_kinds.json`):
  - `"modules": {"from": "dein", "slots": [5, 7]}`: snake / snaketip get their own module row in the cave, the
    arrow's with dein's MotionModule and slot 5 (Mario's fireball has both: a model and ACMD hitboxes). The
    module set-up's stub returns that row for them.
  - `"spawn_from": "dein"`: their article list entries take dein's spawner.
  - Their models ship for every colour (c00–c07): the arrow's kind takes its model in the owner's colour (flag 0x10).
- **The hold window** (`tools/edge_snake_msc.py`): the tapped move plays first, its clean hit (13–14) and late hit
  (15–18) included. Attack held from the start through frame 21 (the 6 frames after the clean hit) extends the sword:
  the motion goes back to frame 13 (sword straight ahead), freezes, and the rest is as before.
- **Tests:**
  - `weapon_expand_test`: 0 failed (new: each own module row emulated, the base's with dein's slots 5 / 7). Its
    article-list expectation now puts new articles before the first special entry, as the build does: the old
    Hero (0x45) failure was the test's.
  - `kind_expand_test`: 0 failed.
  - `port_check` over the chain and tests 70–83: 30 errors, the same as 82; nothing new.
- **New check:** `port_check` W5 weapon-motion (a copy of a kind without a MotionModule that has scripts). W4 knows
  the light arrow's AttackModule (7 / 2).
- Package (install over 82): `code/cross_f.rpx`, `script/msc/edge.mscsb`, `model/snake` / `model/snaketip` c01–c07.

## Test 84 (`build/sephiroth_test84.zip`): the held forward air's trail and facing

User, test 83 (clip): "The sword seems to stretch extremely awkwardly with an active hitbox that seems to turn
opponents towards the camera after hitting them." "The sword is diagonal somehow rather than a straight line."
- **The clip:** the articles work now. The extended sword is the thin dark line straight ahead of him, the colour
  of his blade. The wide white wedge, diagonal from near his body to the tip, is the point's trail (`Sword_Glow`),
  not the sword. DK, hit, is turned to face the camera.
- **The trail:** its two points were across the point along local X and Y both (±2.5). Turned (−angle, 90, 0), the
  article's X is depth: a wide ribbon at a slant, partly facing the camera. Now the points are 1.5 either side along
  local Y only, across the blade in the screen plane whichever way it runs.
  - The articles were made at his body (dein's spawner: his joint 0x13) and placed only after their motion, and so
    their scripts, had started. The trail's first point was at his body. Each now places itself before starting
    its motion.
- **The facing:** the articles never set one. A fighter hit takes the attacker's facing, and 0 draws it facing the
  camera. Each article now takes his (`PostureModule(0, lr)`, every frame).
- **Facing left:** the turn (0x2717) takes the world's angle (Pit's arrow's: 0 right, 180 left), and the articles
  used the run's angle relative to his facing, so facing left they'd have extended to the right. Now 180 − angle.
- **New check:** `port_check` W6 weapon-facing (a weapon MSC that turns itself and never sets its facing).
- port_check over the chain and tests 70–84: 30 errors, as before; nothing new. The MSCs' stack check: clean.
- Package (install over 83): `script/msc/snake/snake.mscsb`, `script/msc/snaketip/snaketip.mscsb`,
  `script/animcmd/weapon/snaketip/effect.bin`.

## Test 85 (`build/sephiroth_test85.zip`): the held forward air's base at the blade, the real blade hidden

User, test 84 (clip, then a frame): "The sword still looks diagonal and appears very incorrect." "The opponent no longer
turns towards the camera when hit." "I just found out that the base of the sword is spawning at the incorrect
location": at his feet.
- **The diagonal:** each run is one blade slice whose near ring is pinned at its run's start and far ring at its
  end. In the frames the near ring was at his feet and the far ring out on the path: one straight piece from his feet
  to the tip, steeper as the tip went up.
  - The near ring and the whole point were on the article bone named HaveN. The light arrow's kind (flag 0x10) is a
    held weapon, and the game draws its HaveN on the owner. EndN, a child of TopN, followed the article.
  - Now the articles have a fourth bone, BaseN (a child of TopN, identity), carrying the near ring and the point.
    Nothing is on HaveN. EndN keeps index 2, so the stretch on joint 0x7D2 is unchanged.
- **The real blade never hid** (tests 82–84): ModelModule's joint 26 isn't bone 26. IDs below 1000 are his joint
  table 0's, which has 26 entries (0–25); 1000+ are table 1's (ACMD's); a bone is 2000 + its index, as the articles'
  0x7D2 and Mario's pump use. The blade (bone 26) is now 0x7EA. `port_check` C6 flags literal IDs 1000–1999 only.
- The opponent facing the camera: fixed in test 84 (user).
- port_check over the chain and tests 70–85: 30 errors, as before; nothing new. The MSCs' stack check: clean.
- Package (install over 84): `model/snake` and `model/snaketip` c00–c07 (`model.vbn`, `model.jtb`, `model.nud`),
  `script/msc/edge.mscsb`.

## Test 86 (`build/sephiroth_test86.zip`): the held forward air's pieces rebased on dein; the blade on joint 1003

User, test 85 (clip): "The base and blade are still wrong."
- **The clip:** the same as test 84. A thin line one blade long, horizontal, at his feet (a run, the right length and
  way, in the wrong place), and the diagonal ribbon from his feet through the tip (the point's trail, sampling both
  places). The real blade still out.
- **The pieces:** the articles were drawn at his feet whatever their PostureModule said, so test 85's BaseN changed
  nothing. Their base, Zelda's light arrow, runs its own native per-kind code (Zelda's Final Smash arrow, made on
  the bow), which keeps it on its owner. dein's copies (fire, flare1, flare2, flash) are the ones proven to sit where
  their MSC places them (Shadow Flare's shot and orbs, every frame). snake / snaketip are now dein copies, with flag
  0x40 (the kind has a model: read only by the generic model set-up and file loader) set by `weapon_expand.py`'s new
  `"flags_set"`. dein's module row has the MotionModule (the stretch and the scripts), its spawner is free, its
  AttackModule 7 IDs / 2 Parts.
- **The blade:** the joint overrides are the MotionModule's, naming joints as ACMD does. His joint table 0 has 26
  entries (0–25); table 1 from 1000, whose 4th entry is EdgeBladeL (bone 26) in every costume: 1003. Tests 82–84's 26
  and test 85's 0x7EA named nothing. (Test 79's crash shows table-1 IDs are taken: its 15 went in.) `port_check` C6
  no longer flags literal IDs, only joint ops from loops.
- `weapon_expand_test`: 0 failed (its flag accessors now read each one's bit from its rlwinm: they aren't in bit
  order, 0x0320E698 is 0x40). `kind_expand_test`: 0 failed. port_check over the chain and tests 70–86: 30 errors,
  as before. MSC stack check clean.
- Package (install over 85): `code/cross_f.rpx`, `script/msc/edge.mscsb`.

## Test 87 (`build/sephiroth_test87.zip`): the blade back after the held forward air

User, test 86: "The sword doesn't appear in any move any more, just the sword trace and hilt."
- The hide on joint 1003 works (tests 82–85's joints named nothing). But the blade was shown again with
  `ModelModule(2, joint)`, which doesn't undo the override: after one held forward air the blade stayed hidden.
- Now it is scaled back to 1 (`ModelModule(0, 1003, 1, 1, 1)`), and the next aerial does that too if a move ended
  with it hidden (`edge_sn_hid`, the global `edge_sn_released` freed in test 83).
- port_check over the chain and tests 70–87: 30 errors, as before. MSC stack check clean.
- Package (install over 86): `script/msc/edge.mscsb`.

## Test 88 (`build/sephiroth_test88.zip`): the extended sword starts at his hilt as it is

User, test 87 (clips): "The sword no longer stretches oddly but isn't aligned correctly."
- The clips: the pieces are where their MSC puts them now (dein copies), the real blade hidden (joint 1003) and back
  after the move. The run after a turn up is a vertical line from the end of the forward path. From the hilt a short
  thin line runs up-right at about 40 degrees, which no piece should; the first run (straight ahead) is hard to see
  under the trail and a platform edge.
- Fair's own sword is straight ahead from frame 12 to 22 (Ultimate's c05attackairf, swordl1's X), so the frozen frame
  13 pose isn't it.
- The path started at Ultimate's frame-13 numbers (11.06 forward, 13.35 up) from his position, at his depth. Now each
  article reads his EdgeBladeL (bone 26) every frame through the joint variables (`0x0F00029C + 4 x slot`, as Shadow
  Flare's ring) and starts the path 0.82 along the blade from it, at the hilt's depth (Ultimate's numbers if the read
  gives nothing).
- port_check over the chain and tests 70–88: 30 errors, as before. MSC stack check clean.
- Package (install over 87): `script/msc/snake/snake.mscsb`, `script/msc/snaketip/snaketip.mscsb`.

## Test 89 (`build/sephiroth_test89.zip`): the forward pieces drawn again

User, test 88 (clip): "The sword still isn't aligned with the hilt, and doesn't appear at all when holding forward.
Holding up/down makes the sword appear, but at an incorrect placement."
- Forward / back pieces invisible, up / down ones drawn: the turn was Pit's arrow's (−pitch, 90, 0), and since test
  84 the articles also have his facing (`PostureModule(0, lr)`), which turns the model lr × 90 about Y itself: 180 in
  all, a horizontal run pointing into the screen, seen end-on. A vertical one is vertical either way. The up / down
  pieces looked misplaced because the forward piece joining them to the hilt wasn't drawn (clip 7.9 s: a down run
  hanging from the end of the forward path).
- Now (−pitch, 0, 0): the facing turns it his way, so the pitch is relative to his facing either way (test 84's
  180 − pitch for facing left is gone).
- port_check over the chain and tests 70–89: 30 errors, as before. MSC stack check clean.
- Package (install over 88): `script/msc/snake/snake.mscsb`, `script/msc/snaketip/snaketip.mscsb`.

## Test 90 (`build/sephiroth_test90.zip`): the extended sword from his hilt

User, test 89: "The forward sword appears now but still isn't aligned with the hilt" (clip).
- The clip: the forward sword straight and the right shape, but drawn at his feet, starting a little behind the
  hilt: his position + 0.82, about 13 below.
- The articles read his hilt through the joint variables writing "26" (EdgeBladeL's model.vbn index). The value is a
  joint ID (`ModelModuleF(axis, joint)`, as ACMD's: model.jtb table 0), and his table 0 has 26 entries: 26 read his
  root. EdgeBladeL sits on his LHaveN (bone 24, playing SwordL1) at identity, and LHaveN is table 0's joint 23 (the
  table swaps 23 / 24) in every costume: the articles read joint 23. `docs/position-variables.md` corrected.
- port_check over the chain and tests 70–90: 30 errors, as before. MSC stack check clean.
- Package (install over 89): `script/msc/snake/snake.mscsb`, `script/msc/snaketip/snaketip.mscsb`.

## Test 91 (`build/sephiroth_test91.zip`): the extended sword from the hilt's frozen place

User, test 90 (frame): "The sword is much closer to being aligned but still isn't." The extended sword ran straight,
but about 4–5 units above the hilt and starting about 7 behind it: his shoulder.
- The joint read (LHaveN, joint 23) gives the joint's unanimated place, not the frozen fair pose: the rest pose's hand
  is out at the shoulder. Shadow Flare reads a waist, which barely moves, so it never showed.
- The path now starts at Ultimate's frozen-frame numbers again (c05attackairf frame 13: hilt 10.25 forward, 13.32 up;
  the blade's body 0.82 on: 11.06, 13.35) from his position, at his depth. Measured on the user's frame (about 6 px a
  unit), the hilt is about 13.7 up and 11.7 ahead: those numbers. Tests 82–87 used them too, but never with a visible
  forward piece in the right place (the light arrow's feet, then the end-on turn).
- `docs/position-variables.md` and the port guide note both behaviours.
- port_check over the chain and tests 70–91: 30 errors, as before. MSC stack check clean.
- Package (install over 90): `script/msc/snake/snake.mscsb`, `script/msc/snaketip/snaketip.mscsb`.

## Test 92 (`build/sephiroth_test92.zip`): the point drawn once; fair's flash carried out with it

User, test 91 (frame): "The sword is aligned now. The tip of the sword looks off. Also, the sword effects aren't
travelling upstream with the sword movement."
- **The point:** every piece was drawn twice, the second copy turned 90 degrees about the blade (`snake_sword._crossed`),
  to look the same width turned any way. The articles turn by pitch about their depth axis, so the blade's face stays
  to the camera; the point's copy, a curved katana tip on edge, drew a dark X across it. The point is now drawn once
  (`snake_sword.article_pieces`: 44 vertices, was 88).
- **The effects:** fair's frame-13 effects (`edge_sword_flash2`, the tip's flash; `edge_attack_speedline`) play once at
  the real blade's end and stayed by his hand while the sword grew. The point now carries the flash: every 6 frames
  while the drawn length grows it plays `edge_sword_flash2` at its end (`EffectModule` 0x3) and moves the newest with
  it every frame (0x17), as Shadow Flare's orbs. The speed lines aren't carried (their angle is the sword joint's).
- port_check over the chain and tests 70–92: 30 errors, as before. MSC stack check clean.
- Package (install over 91): `model/snaketip` c00–c07 `model.nud`, `script/msc/snaketip/snaketip.mscsb`.

## Test 93 (`build/sephiroth_test93.zip`): 0.4x gravity, no direction = keep going, no fast fall in the hold

User: "can you make the gravity 0.4x during the hold, and treat holding with no direction as continuing in the same
direction (initial direction is forward) and disable fast fall during the hold."
- `tools/edge_snake_msc.py`: `edge_sn_grav` 0.4 (was 0.7); with no direction held the steering takes the current run's
  (the first is forward), so the tip keeps going; while extending / retracting the fast-fall flag (0x21000007) is
  kept off and the aerial loop's fast-fall check (`func_555`, in `func_319`) is skipped (`edge_sn_free`, a new
  "replace" hook).
- User, same day: "the opponent doesn't seem to travel back down the same path of the sword once the button is
  released." The hold code puts each caught fighter at its catch point on the path less the retracted length every
  frame (`edge_sn_hold_caught`, `edge_sn_point` walking the runs): not changed here; a clip of a catch and release
  is needed to tell whether the fighter was caught at all (the catch: in hitstun, feet within 22 of the point).
- port_check over the chain and tests 70–93: 30 errors, as before. MSC stack check clean.
- Package (install over 92): `script/msc/edge.mscsb`.

## Test 94 (`build/sephiroth_test94.zip`): caught fighters wait for the retracting end

User: "Keep in mind, opponents attached should only travel back from the point of the sword that they are on." And:
"They stay pinned when I keep holding" (the catch works).
- The sword retracts by shortening from its end; the pieces short of it stay where they are. A caught fighter was
  moved back by the retracted length at once (`edge_sn_s - edge_sn_back`), so it slid toward the hilt along sword
  still out past it, out of step with the sword. Now its place is min(where it was caught, the drawn length): it
  stays put until the end gets back to it, then rides back with the end along the path
  (`tools/edge_snake_msc.py` `edge_sn_hold_caught`).
- port_check over the chain and tests 70–94: 30 errors, as before. MSC stack check clean.
- Package (install over 93): `script/msc/edge.mscsb`.

## Test 95 (`build/sephiroth_test95.zip`): caught fighters put on the sword; 0.1x gravity in the hold

User: "It works, but only if they aren't hit with the initial hit of forward air. Also please set the gravity to 0.2",
then "make the gravity 0.1", then: "The hitbox for returning is small and the initial hit doesn't forcibly align the
opponent inside the sword".
- The catch kept a fighter where the point found it (its feet's offset from the path), so one caught off the
  sword's line came back beside the sword and the end hit, on the sword, missed it. Now the caught fighter is put on
  the sword: its middle (`edge_sn_centre`, 7 above its feet, game units) at the point's middle, and held there along
  the path (`tools/edge_snake_msc.py` `edge_sn_catch_new`). The 7 is a typical fighter's middle, not read per fighter.
- `edge_sn_grav` 0.1 (was 0.4).
- port_check over the chain and tests 70–95: 30 errors, as before. MSC stack check clean.
- Package (install over 94): `script/msc/edge.mscsb`.

## Test 96 (`build/sephiroth_test96.zip`): low gravity through the end hit; dragged fighters pass through the stage

User: "The gravity should apply after the initial hold and until after the sword comes back on the release. Opponents
being dragged back towards the sword during the release shouldn't have stage collision."
- Gravity: 0.1x from the hold (frame 21, as before) through the retract, and now on after the sword is back, through
  the end hit, to motion frame 19 (fair's own hitbox clear; `edge_sn_grav_end`); normal from there. Was: normal again
  the frame the sword was back. Any end of the move before that (landing, a hit) puts it back to normal.
- Dragged fighters: while the sword retracts, each caught fighter gets `GroundModule(0x2710, 0)` every frame (no ground
  correction, as Smash 4's grab statuses set for a held fighter), so the stage doesn't stop it; 5 (air) when it's let
  go (the sword back, or the move ending). Sephiroth's MSC can't call that on another fighter, so the executable's
  variable cave got it: hit / status variable q 6 (`0x0F0000A0 + 8 × target + 6`, Sm4shCommand `TARGET_GROUND`;
  `tools/position_vars_cave.py`, `docs/position-variables.md`), checked in `tools/position_vars_test.py`.
  `tools/edge_specials_build.py --rpx` now puts position_vars_cave's words on again (its relocation moves are made
  once), before acmd_ext_cave.
- Not changed: caught while it extends, they keep stage collision. A fighter let go inside the stage relies on the
  game pushing it out.
- Tests: position_vars_test and acmd_ext_test on the shipped `cross_f.rpx`: 0 failures. port_check over the chain and
  tests 70–96: 30 errors, as before. MSC stack check clean.
- Package (install over 95): `code/cross_f.rpx`, `script/msc/edge.mscsb`.

## Test 97 (`build/sephiroth_test97.zip`): no fast fall in held forward air

User: "fast falling still seems enabled on held forward air, please disable it".
- The fast fall is flag `0x21000001`, set by `func_553` (its check `func_554`: stick flicked down while falling),
  which the aerial's per-frame `func_316` reaches through `func_550`. Tests 93–96 skipped only `func_555` (in the
  loop, `func_319`) and kept `0x21000007` off, neither of which is the fast fall.
- Now, from the hold to the move's end (`edge_sn_free`: states 3–6), `func_316` runs `edge_sn_550` instead (`func_550`'s
  item / other checks without `func_553`), and the loop keeps `0x21000001` off; a fast fall begun before the hold
  (the tapped move's frames) is undone as `func_81` does: fall speed back to the max fall speed (param `0x3000019`)
  if it's past it (`KineticModule(0x11, 1, -max)`).
- port_check over the chain and tests 70–97: 30 errors, as before. MSC stack check clean.
- Package (install over 96): `script/msc/edge.mscsb`.

## Test 98 (`build/sephiroth_test98.zip`): held up tilt

User: "please make held Up tilt work the same way that held forward air does", then "for up tilt, make the default
direction up".
- Up tilt held through its hold window extends the sword the same way as held forward air (steering, catching,
  dragging back with no stage collision, the end hit), from its own frozen pose. `fighters/edge/snake_fair.md` "Held
  up tilt" has the details.
- From Ultimate's `c02attackhi3` (`ultimate_acmd.BonePose` on swordl1): the sword straight up from motion frame 20,
  hilt 1.14 forward and 26.36 up there; the blade's start 0.82 above it. Hit frames from the port's AttackHi3 (Ultimate's):
  pull 17, clean 20–22, late 23–32. The hold window opens at 23, confirmed at 29; the motion goes back to 20.
- The first run goes up; with nothing held it keeps its way. Down (against the first run) needs the tip 24 past
  the normal reach, as fair's back.
- `tools/edge_snake_msc.py`: `edge_sn_move` (0 fair, 1 up tilt; global 0x85) picks the window, freeze frame, base and
  first direction; gravity left alone for up tilt. Hooks in `func_278` / `func_279`, and `edge_sn_end` as up tilt's
  end (was the empty `func_323`). The articles read his status to take up tilt's base.
- `tools/edge_specials_build.py` `snake_hi3_scripts`: up tilt's hits / effects gated to the tapped move; the end hit
  (frame 20's hitboxes, 11%, KBG 40, +2 size) on frames 21–22 after the sword is back.
- Approximated: the end hit's numbers follow fair's (the user's for fair), not anything of Ultimate's.
- port_check over the chain and tests 70–98: 30 errors, as before. MSC stack checks clean (his, snake, snaketip).
- Package (install over 97): `script/animcmd/body/game.bin`, `effect.bin`, `script/msc/edge.mscsb`,
  `script/msc/snake/snake.mscsb`, `script/msc/snaketip/snaketip.mscsb`.

## Test 99 (`build/sephiroth_test99.zip`): up tilt's down after 16 sideways; the sword back after 5 seconds

User: "Can you let up tilt go down after moving 16 units forward or back and please make both up tilt and forward air
retract after 5 seconds have passed."
- Up tilt: down is allowed once the tip is 16 or more forward or back of the sword's start (`edge_sn_down_side`). Test
  98 had forward air's rule turned upward (24 past the sword's reach up), which a turn back down along the sword
  could never use.
- Both moves: the sword starts going back after 300 frames (5 seconds) out, whether attack is still held or not. The
  count is his `VAR_22` (`0x0F000316`, unused by his other scripts), reset when the sword starts to extend, so no MSC
  global is spent.
- port_check over the chain and tests 70–99: 30 errors, as before. MSC stack check clean.
- Package (install over 98): `script/msc/edge.mscsb`.

## Test 100 (`build/sephiroth_test100.zip`): held forward air falls slow and steady; Scintilla charges Zelda's Phantom

User: "Can you make held forward air not accelerate downwards over time and set fall speed to something extremely
low. Also please make down special also charge Zelda's Phantom, and force it to activate if the counter is hit."
Asked how the Phantom should charge: "Hold B to charge" (as Zelda's).
- **Held forward air:** from the hold until the end hit is over (frame 19), no gravity (the gravity energy's accel 0)
  and the fall speed set to 0.1 a frame every frame (`edge_sn_float`, `KineticModule(0x11, 1, -0.1)` as the game's
  `func_81` sets it), whatever his speed was when the hold began (rising included). Tests 93–99 scaled gravity
  (x 0.4, then x 0.1), so he still sped up. `edge_sn_fall` is the number.
- **Scintilla + Zelda's Phantom** (`edge.c` `edge_lw_ph_*`; Zelda's own code: vanilla zelda.mscsb `func_2300`–`2307`,
  decompiled):
  - The stance makes her Phantom (article 2: her files are in his folder) unless one is still out.
  - From the stance's frame 7 (the counter on) it is in its charging status and charges a frame each frame B is
    held; the stance holds at frame 30 meanwhile, so the counter stays up as long as B is held.
  - Full charge at 49 frames (7 levels of 7, his vl `0x08000000` / Zelda's), its full-charge look then; 60 frames
    later (`0x18000001`) it goes by itself.
  - Sent (level = frames / 7, at most 7, in status float `0x1000006`, then `ArticleModule(0x271a, 2)`) when B is let
    go, at that limit, or at once when the counter is hit. Then the stance goes on: the whiff slash after a release,
    the counter slash / break after a hit, as before.
  - The stance interrupted (grabbed, hit from behind) before it's sent: the Phantom goes (status 4).
  - A tap of B: frame 7 sends it at level 0 (Zelda's tap).
  - Its state is in his VAR_16–VAR_18, not MSC globals (they're full: port_check C5).
- Not proven in game: that the Phantom's native code works on a Sephiroth (its kind is Zelda's, its owner his);
  where it stands is its own (native), not moved.
- port_check over the chain and tests 70–100: 30 errors, as before. MSC stack check clean.
- Package (install over 99): `script/msc/edge.mscsb`.

## Test 101 (`build/sephiroth_test101.zip`): Blade Dash's full height; Octaslash slides along slanted stage sides

User: "Tap up special doesn't go far enough when going upwards, held up special seems to 'bounce' Sephiroth off of
diagonal stage geometry, making recovery hard".
- **Height:** the rush is on the stop energy (energy 3), whose speed Smash 4 limits in the air unless a script lifts
  the limit: Zelda's own Farore's Wind does in its air end (vanilla zelda.mscsb `func_2291`:
  `KineticModule(0x14, 3, x limit, -1)`). The rush never did, so its y speed was capped and an upward Blade Dash fell
  short of Ultimate's ~68 units. `edge_hi_rush_main` now sets `KineticModule(0x14, 0x3, -1, -1)` (no limit).
- **Bounce:** in the air the rush's speed is now set along its own direction every frame, and where it touches a
  ceiling or a wall (`GroundModule(0x2722, 1 / 2 / 4)`, the flags vanilla's wall / ceiling bounces read) the
  surface's normal is taken out of that direction (`edge_hi_slide`), so it slides along slanted stage sides instead
  of being turned back. On the ground it still follows the floor (Ultimate's hook), and its direction there carries
  on if it leaves the floor. Not Ultimate's code (its hook only re-aims on the ground): the engine's push-out was what
  turned the rush around here.
- Not proven in game: the touch normal's sign on walls / ceilings (the slide takes the normal out either way).
- port_check over the chain and tests 70–101: 30 errors, as before. MSC stack check clean.
- Package (install over 100): `script/msc/edge.mscsb`.

## Test 102 (`build/sephiroth_test102.zip`): caught fighters can't be KO'd by a blast zone; dragged all the way to the hilt

User: "Can you make it so when an opponent is attached to Sephiroth's held sword, they cannot be KO'd by the blast
zone. Also please make it so the opponent is dragged to the hilt rather than the closest base piece to the hilt
because the final hit never connects."
- **Blast zones:** the place each caught fighter is put every frame is clamped inside the blast zones: 15 inside the
  left / right / bottom ones, its feet 30 under the top one. The bounds are `StageData(0)` left, `(1)` right, `(2)`
  top, `(3)` bottom: the game's own Dead status (`func_220`) clamps its KO place to them. Once let go they can be KO'd
  as usual (by the end hit, say).
- **To the hilt:** caught fighters were held at least 60% of the way out the blade (`edge_sn_hold_caught`), and the
  retract stopped when the sword was back at its own length, so they ended near its end. Now, with the sword at its
  length, the retract goes on pulling them in at its speed (6 a frame, about 4 frames) until all are at the hilt
  (`edge_sn_pull`), then the move goes on to the end hit as before.
- port_check over the chain and tests 70–102: 30 errors, as before. MSC stack check clean.
- Package (install over 101): `script/msc/edge.mscsb`.

## Test 103 (`build/sephiroth_test103.zip`): the Phantom held past the stance; only up tilt has the hilt hit (42 degrees)

User: "Can you make it so Phantom can be held after it begins, even when Sephiroth isn't actionable? Also the hilt
hitbox isn't connecting. I actually think only Up tilt should have the hilt hitbox now. Please make the up tilt hilt
hitbox a 42 degree angle."
- **Phantom:** the charge moved out of the stance into his per-frame hook (`func_82`, run every frame through
  `global14` whatever the status; `edge_lw_ph_tick`, outside hitlag). From the stance's frame 7 it charges while B is
  held, through the slash, landing lag, being hit, anything, and goes when B is let go or 60 frames after full charge
  (a counter hit still sends it at once). The stance no longer holds at frame 30: it plays out as normal. When it's
  sent outside the stance, his status float `0x1000006` is put back after the call. The stance interrupted before
  frame 7: it goes; KO'd (Dead / Rebirth) while it charges: it goes.
- **Hilt hit:** forward air's end hit is gone (`snake_fair_scripts`); its caught fighters drop (hitstun 0) once they
  reach the hilt (`edge_sn_finish`). Up tilt's end hit (frames 21–22) is now angle 42 (was up tilt's 90 / 91), still
  11%, KBG 40, frame 20's four hitboxes each 2 bigger.
- Not found yet: why the hilt hit didn't connect on forward air. If up tilt's doesn't either, a clip of the moment
  the sword comes back is needed (the end hit runs from the ACMD frame after the frozen one; that the frame runs after
  the freeze is still unproven in game: snake_fair.md "Not proven").
- port_check over the chain and tests 70–103: 30 errors, as before. MSC stack check clean.
- Package (install over 102): `script/animcmd/body/game.bin`, `script/msc/edge.mscsb`.

## Test 104 (`build/sephiroth_test104.zip`): the Phantom sent by pressing down special again; 120 frames; gone when he's hit

User: "Can you change Phantom's release to being when the down special is pressed again rather than released, and keep
it for 120 frames after full charge?", "Keep in mind, I want to be able to release Phantom when Sephiroth isn't
actionable", "Also, if Sephiroth is hit while Phantom is out, it should disappear (if he's not in the middle of
countering)".
- **Release:** pressing down special again (B pressed, `SELF_SPECIAL_PRESSED`, with the stick at or below -0.5)
  sends it, read every frame in his per-frame hook whatever the status, in hitlag too (the charge counts only
  outside it), so it works while he isn't actionable. If he's actionable, that press also starts a new down special:
  its start sends the charging Phantom and makes no new one (one is out).
- **120 frames:** it goes by itself 120 frames after full charge (was Zelda's 60).
- **Hit:** while it's out (charging, or sent and still there), Sephiroth going into a damage status (0x45–0x4B,
  0x41 hit while grabbed, 0x57 hit while down) makes it vanish (its status 4). A hit his counter takes doesn't (no
  damage status).
- port_check over the chain and tests 70–104: 30 errors, as before. MSC stack check clean.
- Package (install over 103): `script/msc/edge.mscsb`.

## Test 105 (`build/sephiroth_test105.zip`): Phantom release rules; Octaslash's slide only while touching; bigger hilt hit

User: "when down special is pressed again while Phantom is charging or charged Sephiroth cannot use his counter down
special until after the Phantom is released. Also, please make it so the Phantom cannot be released until near the
end of Sephiroth's counter down special." / "the hilt hitbox is still not hitting. Maybe the hitbox could be a bit
bigger" / "Sephiroth is still bouncing off of diagonal stage geometry during held up special" (clip).
- **No counter while the Phantom charges:** the four down special input checks (`func_43`, `func_58`, `func_675`,
  `func_1999`) go to the counter (0x155) only when `edge_lw_can_counter()`: not while the Phantom charges. The press
  just sends it.
- **Release window:** a down special press sends it only from near the end of the counter move (`edge_lw_ph_open`):
  never in the stance, from frame 42 of the slash (actionable at 52), 32 of the break (42); outside the move at
  once. A counter hit still sends it at once (test 99's ask).
- **Octaslash:** the clip shows the rush going up into a stage's slanted underside, then on up and away from the
  stage along it: test 101's slide changed the aim for good. Now the aim is slid along a surface only on the frames
  it touches it (`edge_hi_rush_speed`), and off the surface it goes on the way it was aimed (past the corner, toward
  the stage).
- **Hilt hit (up tilt):** each hitbox 6 bigger than up tilt's (was 2), out on frames 21–24 (was 21–22); the caught
  fighters' hold hitstop is ended as they're let go (`edge_sn_release`), in case hitstop kept the hit off them.
- port_check over the chain and tests 70–105: 30 errors, as before. MSC stack check clean.
- Package (install over 104): `script/animcmd/body/game.bin`, `script/msc/edge.mscsb`.

## Test 106 (`build/sephiroth_test106.zip`): Scintilla off while the Phantom is out; Blade Dash's y on the gravity energy; Phantom tracking

User: "Scintilla still isn't disabled while the Phantom is charging/being released, tap Up special still barely
gives height. Can you make the Phantom have tracking right at the start of its release specifically if the last
opponent Sephiroth hit is in hitstun?" and "The tracking should not switch facing directions for the Phantom."
- **Scintilla:** his per-frame hook (`func_82`) runs before the status loop's input checks, so the down special
  press had already sent the Phantom (state 3) when the counter's check looked for "charging". `edge_lw_can_counter`
  now also says no while it's sent and still out (`ArticleModule(0x2717, 2)`).
- **Blade Dash height:** test 101's lifted limit didn't help, so the air rush's y no longer goes through the stop
  energy: x stays on it, y goes on the gravity energy (gravity 0, fall cap 20), whose speed Smash 4 is seen to move
  him by (held forward air's fall, Scintilla's break). The speed each frame is Ultimate's schedule (13.5, braked 1.72
  a frame from count 2; Octaslash 6.2 / 0.47 / 6), not read back from the engine (`edge_hi_rush_m`,
  `edge_hi_rush_set`). On the ground it's on the stop energy along the floor as before. The landing angle, the body
  pitch and the air end's carried y read both energies (`edge_hi_vy`).
- **Phantom tracking:** as it's sent, if the last fighter he hit (`LASTHIT_HITSTUN` > 0) is in hitstun, that
  fighter's place goes in his VAR_31 (packed: 2^21 + (x + 512) x 1024 + (y + 512)); the Phantom's own script, now
  his (`fighters/edge/weapons/phantom.c`: Zelda's vanilla phantom.mscsb decompiled, with `ph_track`), reads it as his
  slot's SLOTn_SHARED_7 in its attack's main and again on its first frame, and stands 10 behind the fighter along
  its own facing, at the fighter's height (its slash's hitboxes are 14 ahead). Its facing is never changed.
- Not proven in game: that the Phantom's MSC loads from his folder (`script/msc/phantom/`, as his other articles'),
  and that its native release doesn't move it back after the MSC places it (hence the second placement).
- port_check over the chain and tests 70–106: 30 errors, as before. MSC stack checks clean (his, the Phantom's).
- Package (install over 105): `script/msc/edge.mscsb`, `script/msc/phantom/phantom.mscsb` (new).

## Test 107 (`build/sephiroth_test107.zip`): the Phantom follows a fighter held on the sword up and down; side special cancel

User: "Can you make the Phantom track opponents vertically when held by Sephiroth's snake sword?" and "please make
held up tilt and forward air cancellable into side special after the hilt reaches Sephiroth, specifically if he hit
them with any part of the attack".
- **Phantom:** a fighter held on the sword (`edge_sn_s` >= 0) is its target before the last-hit-in-hitstun one: its
  place goes in his VAR_31 packed with 2^22 as the Phantom is sent and every frame after while it's out
  (`edge_lw_ph_held`; taken back, 2^22 and up only, when none is held). The Phantom (`weapons/phantom.c`) is now
  placed at the end of its attack's main, after its own ground set-up (test 106 placed it before, which likely kept
  it on the ground), put in the air (`StatusModule(2, 2)`, `GroundModule(0x2710, 5)`) for a held fighter, and then
  follows that fighter's height every frame of its attack (`ph_follow_frame`: x and facing kept) until it's let go.
- **Side special cancel:** from the sword back at the hilt (state 5 on), if the move hit anyone (his own hits,
  `SELF_HIT`, or the point catching someone: his VAR_19), the side special input (`global24 & 0x2000`, as `func_43`
  reads it) goes into side special (`edge_sn_cancel`, run first in the aerial and up tilt loops). Tapped moves are
  unchanged.
- **Forced release at 240:** the user, "make Phantom holdable for up to 240 frames", then "I meant when the Phantom
  is forcibly released": it goes by itself 240 frames after full charge (`edge_lw_ph_keep`; test 104: 120).
- port_check over the chain and tests 70–107: 30 errors, as before. MSC stack checks clean.
- Package (install over 106): `script/msc/edge.mscsb`, `script/msc/phantom/phantom.mscsb`.

## Test 108 (`build/sephiroth_test108.zip`): the hitstun tracking only near him, and only horizontal

User: "Please make sure the tracking for opponents in hitstun (except when being hit by snake sword) only applies
horizontally to opponents within 10 units of Sephiroth".
- `edge_lw_ph_target`: the last fighter hit in hitstun is tracked only if it's within 10 of him (straight distance
  from his `LASTHIT_OFFSET_X / _Y`, `edge_lw_ph_near`).
- `weapons/phantom.c` `ph_track`: for that tracking the Phantom takes the fighter's x only and keeps its own height.
  A fighter held on the sword is still followed up and down as in test 107.
- port_check over the chain and tests 70–108: 30 errors, as before. MSC stack checks clean.
- Package (install over 107): `script/msc/edge.mscsb`, `script/msc/phantom/phantom.mscsb`.

## Test 109 (`build/sephiroth_test109.zip`): the hitstun tracking within 15, height by at most 8

User: "Can you make Phantom's 10 unit tracking 15 units and also adjust its height to 8 units at most?"
- `edge_lw_ph_near` 15 (was 10): the last fighter hit, in hitstun, within 15 of him (straight distance) is tracked.
- `weapons/phantom.c` `ph_track`: for that tracking the Phantom takes the fighter's x and moves toward its height by
  at most 8 up or down (`ph_lift`; test 108 kept its own height). A fighter held on the sword is still followed up
  and down fully.
- port_check over the chain and tests 70–109: 30 errors, as before. MSC stack checks clean.
- Package (install over 108): `script/msc/edge.mscsb`, `script/msc/phantom/phantom.mscsb`.

## Test 110 (`build/sephiroth_test110.zip`): the Phantom follows held fighters from whenever they're held; any special releases it while he can't act

User: "Phantom doesn't seem to track held opponents" and "please allow the special button with any or no direction
to be used to release the Phantom when Sephiroth is not actionable".
- **Held tracking:** the Phantom only followed a fighter held on the sword if one was held at the moment it was
  sent; one caught after (the Phantom already out) was never followed. Now `ph_follow_frame` checks every frame of
  its attack and starts following (into the air, its height to the fighter's) whenever his VAR_31 holds a held
  fighter (he updates it every frame while the Phantom is out). Also `edge_lw_ph_held` counts a fighter as held only
  while the sword is out (`edge_sn_out`): the per-slot places start at 0 in a match, which read as "held".
- **Release:** `edge_lw_free()`: his free statuses (0x0–0x9, 0xB–0xF, 0x11–0x15) or a move past its cancel frame
  (`CancelModule(0x2713)`). Not free: any special press sends the Phantom (any or no direction); free: down special
  only (the others stay his specials). The counter move's window (test 105) still applies.
- port_check over the chain and tests 70–110: 30 errors, as before. MSC stack checks clean.
- Package (install over 109): `script/msc/edge.mscsb`, `script/msc/phantom/phantom.mscsb`.

## Test 111 (`build/sephiroth_test111.zip`): his own Phantom kind, so its script (the tracking) is the one that runs

User: "Phantom still doesn't follow a held opponent or move to them at all".
- Cause: a weapon's files (model, motion, ACMD, MSC) load by its weapon kind's owner (the path tables,
  docs/weapon-expansion.md). His article 2 was still Zelda's own Phantom kind, owned by "zelda", so the game read
  `fighter/zelda/script/msc/phantom/` and his `script/msc/phantom/phantom.mscsb` (tests 106–110: the tracking) was
  never used.
- Fix: a Phantom kind of his own, 0x19B, owned by "edge", a copy of hers (`extra_kinds.json` plain entry
  `"phantom": "0x19B"`: `weapon_expand.py`'s remap puts it in his article 2 in her kind's place; its native cases
  go to hers). Her Phantom's model, motion and ACMD are copied into his folder by the build
  (`edge_specials_build.py`). `weapon_expand_test.py`: 0 failed (his articles: 0x22, 0x23, 0x19B, 0x24, 0x25, ...).
- `port_check` W7 weapon-owner (new): an error for a `fighters/NAME/weapons/X.c` shipped as `script/msc/X/` that
  isn't one of the fighter's own weapon kinds; port guide catalogue row added.
- Not proven in game: that the Phantom's native code works the same under the new kind (Supamario's copies of
  Mario's weapons do). Its ACMD's effect ids still name Zelda's effect bank (as before), so its effects show only if
  her bank is loaded.
- port_check over the chain and tests 70–111: 30 errors, as before. MSC stack checks clean.
- Package (install over 110): `code/cross_f.rpx`, `model/phantom/`, `motion/phantom/`,
  `script/animcmd/weapon/phantom/` (hers, now read from his folder).

## Test 112 (`build/sephiroth_test112.zip`): no negative shield damage (new rule); Shadow Flare's orbs wait out hitstop

User: "New Rule for Ultimate ports, ensure shield damage values aren't negative--it causes an instant shield break
that way" and "Sometime side special's orbs don't connect with the opponent, mostly when there's more than one orb".
- **Shield damage:** Ultimate's negative shield damage was written as is; Smash 4 reads it unsigned, so every such
  hit broke a shield. His package had it in 19 scripts (body 2, Flare 5, Shadow Flare 1, Scintilla's flash 11).
  `ultimate_acmd.py` now writes 0 at least for every port; `port_check` S9 shield-negative is an ERROR; the rule is
  in CLAUDE.md and the port guide's catalogue. S9 is gone from his package.
- **Shadow Flare's orbs:** strikes come 8 frames apart and each orb's EXP lasts one frame; with more than one orb, an
  EXP could land while the target was still in hitstop from the orb before, and was lost. Now a striking orb that
  reaches the centre while the target is in hitstop (its slot's hitstop variable) waits there and explodes on the
  first frame after (`weapons/flare1.c`).
- port_check over the chain and tests 70–112: 30 errors, as before (55 warnings: S9 gone). MSC stack checks clean.
- Package (install over 111): `script/animcmd/body/game.bin`, `script/animcmd/weapon/fire|flare1|flash/game.bin`,
  `script/msc/flare1/flare1.mscsb`.

## Test 113 (`build/sephiroth_test113.zip`): up special concept, stage 1: held Octaslash steers and loops, autolink, Blade Dash changes, once per air

User: the up special concept (purple line trails, closed shapes filled with a scaling glow and hitbox; held
Octaslash "allows 180 degree forward up and down rotating movement at the speed it normally moves at, but looping
between the 2nd hit and the hit before the final hit for a set duration or until the special button is released",
the timer reset on a hit; "The hits should aggressively autolink into each other. Tap up special should have no
aiming restriction, slightly lower landing lag and not put into special fall unlike Octaslash. Both versions of up
special should only be usable once in the air and reset on landing or grabbing ledge but not when hit."). Staged:
this test is everything but the trails and the shapes (next: the trail articles; then the shape fill and hitbox).
- **Held Octaslash:** steers toward the stick 8 degrees a frame through his front only, at a steady 6.2; past its
  normal 15 frames, while held, SpecialHi2's frames 4 - 15 (hits 2 - 7) loop, for 60 frames, again from every hit;
  let go -> its final hit and SpecialFall. The script skips the first hit and the start effects on looped passes.
- **Autolink:** the last fighter hit, in hitstun and near, is pulled each frame to 10 in front along the rush.
- **Blade Dash:** full aim as before; landing lag 22 (was Ultimate's 27); the air end ends in Fall, not SpecialFall.
- **Once per air time** for both: back on landing or a ledge grab, not on being hit.
- Details and constants: `specials.md` "Up special". Not tested in game (the loop's motion restart at frame 4
  assumes the script runs straight past frames 0 - 3).
- port_check over the chain and tests 70–113: 30 errors, as before.
- Package (install over 112): `script/animcmd/body/game.bin`, `effect.bin`, `script/msc/edge.mscsb`.

## Test 114 (`build/sephiroth_test114.zip`): held Octaslash steers the full 360 degrees

User (before testing 113): "can you allow a full 360 degrees of movement?" `edge_hi_steer` no longer keeps the turn to
his front: the rush turns toward any stick direction, 8 degrees a frame the shorter way round. He keeps his facing, so
heading back he's pitched past 90 degrees (a loop) rather than turned around.
- port_check over the chain and tests 70–114: 30 errors, as before.
- Package (install over 113): `script/msc/edge.mscsb`.

## Test 115 (`build/sephiroth_test115.zip`): Octaslash loops and slows; Phantom release fixes

User (test 114's clip): "Octoslash when held moves far too fast ... the attack doesn't loop either. It does hold the
animation oddly. Phantom now releases on any special button pressed rather than down special, the special button
release is only supposed to be when Sephiroth is not actionable (ex. Forward air, Down smash). Phantom doesn't allow
itself to be released while an oppenent is attached to the snake sword, and it doesn't seem like it tracks either."
- **Loop:** SpecialHi2's animation ends on frame 14 (Ultimate's `d02specialhi2.nuanmb`); the restart waited for 16,
  so it never came and the last pose held. Now it plays again from frame 4 the frame after it reaches 14.
- **Speed:** held, it brakes as Ultimate's (6.2, less 0.47 a frame from frame 6) down to 2.0, then keeps 2.0.
- **Phantom, any special:** a special started from neutral reads its press on the frame he's already in the
  special's status, which counted as "not actionable". Now any special sends it only if he couldn't act on that frame
  and the one before (VAR_13); otherwise down special only, as before.
- **Phantom, a fighter on the sword:** held forward air / up tilt can sit past the move's cancel frame, which counted
  as actionable (down special only). Now he counts as not actionable whenever the snake sword is out. The tracking of
  a held fighter is unchanged: it couldn't be seen while the release didn't work.
- port_check over the chain and tests 70–115: 30 errors, as before.
- Package (install over 114): `script/msc/edge.mscsb`.

## Test 116 (not sent: folded into 117): Phantom held-fighter offset, loop cap, speed 2.2, Blade Dash ends at 23, air use from the attack

User (clips of the Phantom and tap up special): "When Phantom tracks a held opponent, it spawns inside of them ... The
distance from the opponent used in this clip is what I'd like the offset to be. Held up special loops indefinitely when
an opponent is hit. Also please make the speed of the movement 2.2, and make tap up special cancel right before the
the point where Sephiroth would begin falling in the animation. Also make it so that up special's air use is only used
after the attacking portion of either up special begins." and "Also please make Phantom stop tracking after the attack
finishes."
- **Phantom offset:** a fighter held on the sword: the Phantom is placed 65 behind it (`phantom.c ph_held_reach`; was 10).
  Measured on the clip: Sephiroth (21.5 tall: head bone 19.0 + head) ~212 px, the Phantom's orb to DK ~650 px.
- **Phantom stops following** once its attack's last hitbox is out (`ph_hit_end`: frame 12 / 15 / 28 by charge, from
  Zelda's phantom game.bin).
- **Octaslash loop:** still started again by each hit, but 180 frames of loop at most (counted in hitlag too); held
  now needs both ControlModule's held special and SELF_SPECIAL. Speed held: 2.2.
- **Blade Dash:** the air end goes to Fall at frame 23 (its animation turns into the fall from 24), pitch back by then.
- **Once per air time:** spent as the rush (the attack) begins, not at the start.
- port_check over the chain and tests 70–116: 30 errors, as before.
- Package (install over 115): `script/msc/edge.mscsb`, `script/msc/phantom/phantom.mscsb`.

## Test 117 (`build/sephiroth_test117.zip`): test 116's changes + no purple flash left on his hand

User: "When releasing Phantom, Sephiroth permanently has a purple effect on his hand until doing it again." Every
attack script of the Phantom (Zelda's, copied) starts with `Graphic_Effect4(0x3100016, bone 0x7DA)`: Zelda's purple
flash on her hand as she sends it, which her release status ends. Sephiroth sends it from any status, so nothing
ended it. The build now takes it out of the Phantom's effect.bin (17 scripts: `edge_specials_build.py
phantom_hand_flash`); he has no such hand pose.
- Test 116 (above) wasn't sent: this package has its changes too.
- port_check over the chain, tests 70–115 and 117: 30 errors, as before.
- Package (install over 115): `script/msc/edge.mscsb`, `script/msc/phantom/phantom.mscsb`,
  `script/animcmd/weapon/phantom/effect.bin`.

## Test 118 (`build/sephiroth_test118.zip`): the Phantom follows a held fighter sideways too

User (clip: held up tilt catches DK, the Phantom sent while the sword reels him in): "Phantom won't hit an opponent
being retracted by the snake sword." The Phantom was placed 65 behind him at its release but then followed him only up
and down: the sword pulled him back past it while it dashed, and its slash (frame 11 on, 20 ahead) met nothing. Now
each frame of its attack (to its last hitbox) it also moves sideways by as much as he did since the last frame
(`phantom.c ph_follow_frame`, `ph_hx`), so the gap is the one its slash is made for, as if he stood still.
- port_check over the chain, tests 70–115, 117 and 118: 30 errors, as before.
- Package (install over 117): `script/msc/phantom/phantom.mscsb`.

