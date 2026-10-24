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

## Next

1. Specials: Flare / Megaflare / Gigaflare, Blade Dash / Octaslash, Scintilla, Shadow Flare; the
   One-Winged Angel form; Final Smash.
2. Effects, sounds, portraits from the Ultimate zips.
