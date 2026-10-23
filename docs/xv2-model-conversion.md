# Xenoverse 2 effect models -> Smash 4 effect models

Turns the 3D models in Dragon Ball Xenoverse 2 effect packages (an `.eepk`'s EMO assets: `X.emo`
mesh + skeleton, `X.emm` materials, `X.emb` textures, `X.obj.ema` bone animation, `X.mat.ema`
material animation, `X.light.ema` light) into Smash 4 effect model folders
(`fighter/<name>/effect/<name>/model/<Name>/`: `model.nud / .nut / .vbn / .omo / .mta / .xmb`, see
docs/efc-format.md "Effect models"). First used for the Kamehameha port (Goku's `000_GOK_KMH`).

```
python3 tools/xv2model.py dump Kmh_Fire.emo [out.json]       # EMO / EMM / EMA: summary (+ JSON)
python3 tools/xv2_to_nud.py SRC_DIR all OUT_DIR --prefix EffSupamarioKame --preview PNG_DIR
python3 tools/xv2_to_nud.py verify OUT_DIR/EffSupamarioKameFire --src SRC_DIR --preview PNG_DIR
```

`NAME` is an EMO base name, a glob or `all`; `Kmh_Fire` becomes `<prefix>Fire`. `--preview`
re-reads every written file with the repo's own readers, checks the round trips and renders an
orthographic contact sheet per model (rows: the whole model, then each mesh; columns: side view at
four frames, front view).

## Formats (tools/xv2model.py)

Little-endian; ported from LazyBone152's XV2-Tools (`Xv2CoreLib/EMO`, `EMG`, `EMD` (vertex and
sampler layouts), `EMM/Parser.cs`, `Animation/EMA/EMA_File.cs`, `Animation/EMA/Skeleton.cs`). The
field-by-field layout is in the module's docstring. In short:

- **EMO** = parts (one per skeleton bone that has geometry; a bone's `EmoPartIndex` links it) ->
  EMG blocks -> meshes. A mesh: vertex flags (0x1 position, 0x2 normal, 0x4 UV, 0x8 UV2,
  0x40 colour, 0x80 tangent, 0x200 blend weights, 0x8000 half floats), texture lists (samplers:
  EMB index, address mode U/V, filter, UV scale) and submeshes (material name, texture list,
  u16 triangle-list indices, bone list). The skeleton: 80-byte bones (parent / child / sibling /
  part, a 4x4 relative matrix, row vectors).
- **EMM**: named materials: shader program (`T1_VFX_MTN`, `T1_VFX_MTN_DIS_ALPHA` here) + a list of
  named scalar parameters (`MatCol1R`, `TexScrl0V`, `AlphaBlendType`, ...).
- **EMA**: a skeleton (obj: the model's bones; mat: one "bone" per EMM material, its index the
  material's) and animations of commands (bone, parameter, component) with keyframes (u8 / u16
  time, value index; linear, quadratic or cubic Bezier with offset control values). obj
  parameters: position, rotation (Euler degrees, X roll / Y pitch / Z yaw ->
  `MathHelpers.EulerToQuaternion`), scale; mat: MatCol0-3 (RGBA), TexScrl0-3 (UV); light: colour,
  radii. A missing component takes its default (0, scale 1), not the bind pose.
- The animations end on a key equal to frame 0 (the loop point): frames 0 .. end - 1 are used.

## Mapping

| XV2 | Smash 4 |
|---|---|
| skeleton | `model.vbn`: `TopN` + the EMO's bones (names kept, parents shifted by one); little-endian `' NBV'` 2.1 as all 444 vanilla effect models; every bone at the origin (138 vanilla effect VBNs are) |
| obj.ema | `model.omo`: every bone, every frame, its full local transform (position x scale, quaternion, scale); constant tracks stored as constants (pos 0x20, rot 7, scale 0x201), the rest interpolated (0x08, 5, 0x081). Bezier keys are evaluated per frame. |
| part / EMG mesh / submesh group | one NUD mesh, single-bound (bind 8) to the part's bone; triangle list; positions x scale, normals (vertex type 6), colours 255 -> 127 (= 1.0, as the vanilla effects), one UV (half floats) |
| EMM material | effect shader `0xB0201100` (0x100 UV transform, 0x1000 vertex colour), `+ 0x40000` (angle fade) when `IncidenceAlphaBias < 1` |
| `AlphaBlendType` 0 / 1 / 2 | src 5 / dst 1 (`A_AB`), 5 / 2 (`A_ADD`), 5 / 3 (`A_SUB`, the game's subtractive: e.g. Ness's PK Thunder) |
| `BackFace` 1 (or `TwoSidedRender`) | cull 0 (both sides); without it cull 1029 (back faces) |
| `AlphaTest n` | alpha function 0x204 (greater), ref n |
| sampler | the texture (wrap 0/1/2 -> 1/2/3, filter 3/2, as the game's), its UV scale -> `NU_effScaleUV` |
| `MatCol1` x `MatCol2` | `NU_effColorGain` (MatCol1's RGB as one brightness: their mean, see below; A the alpha) |
| `TexScrl0` | `NU_effTransUV` |
| `IncidenceAlphaBias b` | `NU_angleFadeParams [0, 1 - b]` (alpha x (1 - mix(x, y, fresnel)): facing 1, edge-on b) |
| mat.ema | `model.mta` (MTA4, header value 1 and u2 0 as the game's effect MTAs): per material `NU_effColorGain` and `NU_effTransUV` a frame, linked by `NU_materialHash` (a float 4096..8192 from a CRC of the material name); no material animation -> an empty `model.mta` (148 vanilla effect models have one) |
| EMB (DDS) | `model.nut`: NTWU (GX2), BC1 if fully opaque else BC3, one mip (`nut.write_ntwu`) |
| - | `model.xmb`: Mario's `EffMarioSmashImpact` one (`effect_near`), written by `xmb_write` (byte-identical to the game's file) |
| light.ema, glare (`Glare`, `GlareCol`), `LowRez`, `ZWriteMask`, `VsFlag*`, `AnimationChannel`, MatCol0 / MatCol3 | not converted |

Vanilla reference (scanned: the 444 effect model folders of the game's fighters): materials are
`0xB020xxxx` effect shaders (`0xB0201000` 702, `0xB0201100` 578, `0xB0241100` 397, ...), flag bits
0x100 = UV transform props (`NU_effRotUV / ScaleUV / TransUV`), 0x1000 = vertex colours, 0x40000 =
`NU_angleFadeParams` with normals, 0x20000 = `NU_effCombinerColor0/1`; blend (all polygons) 5/2
1120, 5/1 571, 0/0 447, 37/1 102, 5/3 17 (`A_SUB` in every MTA material name that covers them);
src 37 = 5 + z-test off (`AT_ZTEST_OFF`); cull 0 (1956) or 1029 (439).

### Scale

`SCALE = 8.5` Smash units per XV2 unit (`--scale`): Mario is ~15 units tall (his body
`model.vbn`: HeadN at y 10.2, hat at 13.2, the body model's bounding sphere reaching ~16), Goku in
XV2 ~1.75 (XV2 units are metres); 15 / 1.75 = 8.6. The EEPK still scales each instance (the
ACMD effect's Size does that in Smash): `000_GOK_KMH.eepk` places Kmh_Fire at `g_L_Hand` x 1.0,
Kmh_Bas at `TRS` x 1.6 / 2.0 / 2.5 (charge levels), Kmh_Hand at `TRS` x 0.45 / 0.5 / 0.6, z -0.3
.. -0.7.

### Texture ids

Fighter effect textures are `0x151 KK nnn` (KK the fighter: Mario 0x11 -> `0x151110xx`, Pit
0x1D, ... Kamui 0x49) and Final Smash ones `0x153 KK nnn` (FinMario `0x153120xx`).
`0x1514 1nnn` (KK 0x41, Supamario's kind id) is used by no vanilla effect model; the conversions
take `0x15141A00` + 0x10 x (the EMO's index among SRC_DIR's EMOs, sorted) + the EMB index
(`--tex-base`). Kamehameha: Kmh_Bas `0x15141A00` / `0x15141A01`, Kmh_Fire `0x15141A10`,
Kmh_Hand `0x15141A20` / `0x15141A21`.

### Axes, winding, UVs

No axis change: both games are Y up, and the meshes' winding is counter-clockwise against their
normals (checked per mesh: every triangle's cross product agrees with its vertex normals; the
converter flips a mesh that doesn't). The beams run along +Z after the TRS bone's X -90 (Fire,
Bas); the hand ball's tail runs to -Z. UVs are kept as they are (XV2's V runs -1..0 here, with
repeat wrapping).

## The Kamehameha (000_GOK_KMH)

| Model | XV2 parts | verts / tris | bones | frames | textures | blend |
|---|---|---|---|---|---|---|
| EffSupamarioKameFire | Fire (flame-wisp cone) | 309 / 416 | 4 | 30 | 0x15141A10 128x256 BC1 | add |
| EffSupamarioKameBas | Cor (beam core), BasB, BasB1 (flame domes), BasB_kushi (fins) | 735 / 1156 | 7 | 80 | 0x15141A00 256x128 BC3, 0x15141A01 128x128 BC1 | add (Cor, BasB), alpha (BasB1, kushi) |
| EffSupamarioKameHand | cor (glow ball + tail), hand (dark ball) | 1058 / 1952 | 5 | 60 | 0x15141A20 / 0x15141A21 256x256 BC3 | alpha (cor), subtract (hand) |

Size at scale 1 (all frames): Fire up to 33 long (+Z) and 32 across; Bas 11 across, the core to
z 10.7; Hand ball 37 across (the `hand` sphere scales x3.5), tail to z -50.

## Approximated / to check in game

- **MatCol semantics are unknown** (the VFX shaders aren't documented in XV2-Tools; its defaults:
  MatCol0-2 (1,1,1,1), MatCol3 (0,0,1,1)). Taken as: MatCol1 = brightness (mean of RGB) + alpha,
  MatCol2 = RGB tint. As a plain RGB multiplier (`--matcol1 rgb`) Kmh_Bas's core goes
  yellow-green (its MatCol1 animates G to 2 and B to 0.5), which can't be the intent of a blue
  Kamehameha. MatCol0 / MatCol3 (perhaps the rim colour of the incidence term) are ignored.
- `BackFace 1` read as "draw back faces" (the open shells: cones, domes) - if it means "cull",
  the shells just get an inside as well.
- `IncidenceAlphaBias` -> angle fade, `IncidencePower` ignored.
- Static `TexScrl` values with no mat.ema key are read as UV per second (none here: every
  scrolled component is animated). The direction / order of Smash's `NU_effScaleUV` and
  `NU_effTransUV` (uv x scale + trans assumed) is unverified.
- One mip per texture (`write_ntwu`); vanilla effect textures have 6-8 mips (`mip 6` kept in the
  material). Far zooms may shimmer.
- Glare / bloom (XV2's `Glare`, `GlareCol`) has no counterpart: the additive parts will look
  flatter than in XV2. The light EMAs (a point light following the effect) are not converted.
- The OMO's frame count = the EMA's end frame; whether a model-only .efc entry loops its OMO /
  MTA or stops at the end is untested (the XV2 entries loop: `EMA_Loop`).
- Not yet loaded in game: needs an .efc entry each (`tools/efc.py add ... --set 0 --model
  EffSupamarioKameBas`) and an ACMD effect call at the hands with the EEPK sizes.
