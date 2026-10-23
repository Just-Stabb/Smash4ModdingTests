# Dragon Ball Xenoverse 2 effects: EEPK, EMP, ETR, EMM (and a Kamehameha walk-through)

`tools/xv2vfx.py` reads a XV2 effect package (the `.eepk` and the files it names) into plain
Python dicts, writes them as JSON plus a readable `summary.txt`, and checks them:

    python3 tools/xv2vfx.py dump DIR OUTDIR     one JSON per file + summary.txt
    python3 tools/xv2vfx.py check DIR           sanity asserts, byte coverage, corruption tests
    python3 tools/xv2vfx.py show FILE           one .eepk / .emp / .etr / .emm / .ema as JSON

The binary layouts below are a port of the readers in **LazyBone152's XV2-Tools**
(`Xv2CoreLib/EMP_NEW/Parser.cs` + `EMP File.cs`, `ETR/ETR_File.cs`, `EEPK/EEPK_File.cs`,
`EMM/Parser.cs`, `Animation/EMA/EMA_File.cs`). Field names are the C# names. Where the C# reader
skips bytes, the meaning comes from the matching C# writer (`Deserializer.cs` / `Write()`).
EMB containers (`.emb`: textures, and the `.pbind.emb` / `.tbind.emb` that hold the EMP / ETR
files) are read by `tools/xv2emb.py`.

Every reader records which bytes it consumed. A byte that no field covers must be zero (alignment
padding), or the reader raises `FormatError`. It also raises on unknown node, emitter, emission,
scroll, asset or modifier types, on a keyframed `(Parameter, Component)` that has no name, on
boolean bytes other than 0 / 1, and on offsets out of range. All of the Kamehameha package
parses with no unconsumed non-zero byte (1 EEPK, 8 EMP, 3 ETR, 5 EMM): see `check`.

## Package and cross references

Everything is little-endian. Strings are ASCII.

- **`.eepk`**: the effect index. It has *asset containers*, one per asset type (EMO models,
  PBIND particles, TBIND traces, LIGHT light animations, CBIND colour changes). Each
  container lists its assets, and each asset lists its file names. It also has *effects*,
  identified by an id; each effect is a list of *effect parts*.
- An effect part picks `(AssetType, AssetIndex)`: an asset of the container of that type. It
  also gives the bone to attach to (`ESK`), the start frame, offsets, scale and flags.
- The **PBIND** container names `ContainerEmbPath` (`*.pbind.emb`: the EMP files, by name),
  `MaterialEmmPath` (`*.ptcl.emm`) and `TextureEmbPath` (`*.ptcl.emb`, DDS textures). A PBIND asset's
  `Files[0]` is an EMP name in the `.pbind.emb`.
- In an EMP, an emission node's texture part has a `MaterialID` (an index into the `.ptcl.emm`
  materials; 0xFFFF = none) and a list of *texture sampler* indices. A sampler's `EmbIndex` is a
  texture index in the `.ptcl.emb` (255 = none). The EMP itself holds the sampler (UV mode, scroll,
  sprite sheet).
- **TBIND** works the same way: `*.tbind.emb` holds the ETR files, `*.trc.emm` the materials and
  `*.trc.emb` the textures.
- EMO assets list `.emo` (model), `.emm`, `.emb` (textures), `.mat.ema` (material animation) and
  `.obj.ema` (object animation). LIGHT assets list a `.light.ema`. These are only noted, not parsed
  (EMA: header and animation lengths only).

`load_package()` resolves these references. In the dumped JSON, each sampler gets a `TextureRef`
(the texture file name), and each emission `Texture` and ETR node gets a `MaterialRef` (the
material name).

## Units

| quantity | unit |
|---|---|
| EEPK `StartTime`, EMA frames | frames (60 / s) |
| EMP `Lifetime`, `StartTime`, `BurstFrequency` (+ `_Variance`) | frames |
| EMP keyframe `Time` | **percent of the node's life**, 0..100 (XV2-Tools scales by 1/100) |
| ETR `StartTime`, `ExtrudeDuration`, `HoldDuration`, keyframe `Time` | frames |
| EMP node `Rotation`, emitter `Angle`, emission `StartRotation` | degrees |
| EMP `ActiveRotation` | degrees per second (XV2-Tools comment) |
| EEPK `Rotation*`, ETR `Rotation` | stored as radians; shown in degrees, as XV2-Tools does |
| sizes and positions (`ScaleBase`, `Size`, `Position`, ETR `Scale`) | XV2 world units (about metres), times the EEPK part's `ScaleMin..Max` |
| colours | linear float RGBA; values above 1 occur (glow) |

`_Variance` fields are random ranges added to the base value (`value + rand * variance`, as
XV2-Tools treats them).

## EEPK

Header (24 bytes): `+0` "#EPK", `+4` u16 0xFFFE, `+6` u16 24, `+8` i32 Version (37568),
`+12` u16 asset container count, `+14` u16 effect table length, `+16` i32 container offset,
`+20` i32 effect table offset. The effect table has one i32 per effect id (0 = no effect).

**Asset container** (48 bytes):

| offset | field |
|---|---|
| +0 | i32 `AssetSpawnLimit` |
| +4 | u8 `I_04`..`I_07` |
| +8 | i32 `AssetListLimit` |
| +12 | i32 `I_12` |
| +16 | u16 `AssetType` (0 EMO, 1 PBIND, 2 TBIND, 3 LIGHT, 4 CBIND) |
| +18 | 12 zero bytes |
| +30 | u16 asset count |
| +32 | i32 asset table offset, relative to the container |
| +36 | i32 `ContainerEmbPath` string offset, relative to the container (0 = none) |
| +40 | i32 `MaterialEmmPath` string offset (same) |
| +44 | i32 `TextureEmbPath` string offset (same) |

**Asset** (12 bytes):

| offset | field |
|---|---|
| +0 | i16 `I_00` |
| +2 | u8 type (must match the container) |
| +3 | u8 file count |
| +4 | i32 offset of one file-type byte per file (0 EMO, 1 EMM, 2 EMB, 3 EMA, 4 EMP, 5 ETR, 7 ECF, 255 none) |
| +8 | i32 offset of an i32 per file, each the offset of a name string |

All asset offsets are relative to the asset.

**Effect** (16 bytes): `+0` u16 id (must equal its table index), `+2` u16 `I_02`, `+4` 6 zero
bytes, `+10` u16 part count, `+12` i32 parts offset (relative to the effect).

**EffectPart** (100 bytes):

| offset | field |
|---|---|
| +0 | u16 `AssetIndex` |
| +2 | u8 `AssetType` |
| +3 | u8 `AttachementType` (0 External, 1 Unk1, 2 Bone, 3 Camera) |
| +4 | u8 `Orientation` (0 None, 1 User, 2 AttachmentBone, 3 Camera, 4 RotateMovement) |
| +5 | u8 `Deactivation` (0 Never, 1 Immediate, 2 LoopCancel) |
| +6 | u8 `I_06`, u8 `I_07` |
| +8 | i32 `I_08`, `I_12`, `I_16`, `I_20` |
| +24 | f32 `AvoidSphere` |
| +28 | u16 `StartTime` (frames after the effect starts) |
| +30 | u16 `EMA_AnimationIndex` |
| +32 | u8 `Flags1`: 0x01 PositionUpdate, 0x02 RotateUpdate, 0x04 InstantUpdate, 0x08 OnGroundOnly, 0x10 UseTimeScale, 0x20 UseBoneDirection, 0x40 EnableRotationValues, 0x80 UseScreenCenterToBoneDirection |
| +33 | 0 |
| +34 | i16 `I_34` |
| +36 | u32 `Flags2`: 0x1 EMA_Loop, 0x1000000 NoGlare, 0x4000000 InverseTransparentDrawOrder, 0x8000000 RelativePositionZ_To_AbsolutePositionZ, 0x10000000 ScaleZ_To_BonePositionZ, 0x80000000 ObjectOrientation_To_XXXX. Bits 16-19 are `I_38_a` and bits 20-23 `I_38_b` |
| +40 | f32 Position X Y Z |
| +52 | f32 `RotationX_Min`, `X_Max`, `Y_Min`, `Y_Max`, `Z_Min`, `Z_Max` (radians; random between min and max) |
| +76 | f32 `ScaleMin`, `ScaleMax` (a uniform scale for the whole asset) |
| +84 | f32 `NearFadeDistance`, `FarFadeDistance` |
| +92 | u16 `EMA_LoopStartFrame`, `EMA_LoopEndFrame` |
| +96 | i32 `ESK` (the bone name string, relative to the part) |

## EMP (particles)

Header (32 bytes):

| offset | field |
|---|---|
| +0 | "#EMP" |
| +4 | u16 0xFFFE |
| +6 | u16 24 |
| +8 | u16 Version: 37568 DBXV2, 37632 SDBH. SDBH samplers and sprite keyframes are 8 bytes longer |
| +10 | 0 |
| +12 | i16 root node count |
| +14 | i16 texture sampler count |
| +16 | i32 first node offset (32) |
| +20 | i32 sampler table offset |
| +24 | 8 zero bytes |

The file has the nodes (each followed by its extra data), then the samplers. Before each node
the writer adds zero padding so the node is 16-byte aligned.

### Node tree

Each node has a next-sibling offset (`+152`) and a first-child offset (`+156`), both relative to
the node itself (0 = none). The root nodes are the first sibling chain. The child count at `+146`
matches the chain length (checked). There are three node types:

- **Null**: a group / transform node.
- **Emitter**: has a shape. It spawns its children (emitters or emissions) at points of the
  shape.
- **Emission**: draws particles. In this package, emissions can have children too: the
  `*_yoin` (Japanese for "afterglow") particles under `*_loop` nodes.

The common timing fields drive spawning. A node becomes active `StartTime (+rand
StartTime_Variance)` frames after its parent and lives `Lifetime (+rand Lifetime_Variance)`
frames. While it lives, it emits `Burst (+rand Burst_Variance)` children every `BurstFrequency`
frames (0 = once). `MaxInstances` caps the live children (-1 / 0 = no cap). With the `Loop` flag the
node restarts when its life ends, until the EEPK part is deactivated (`Deactivation` LoopCancel /
Immediate).

### ParticleNode (160 bytes)

| offset | field |
|---|---|
| +0 | 32s `Name` |
| +32 | u16 `NodeFlags`: 0x2 Loop, 0x8 FlashOnGen, 0x800 Hide, 0x1000 EnableScaleXY, 0x4000 EnableSecondaryColor (others unknown: Unk1/3/5..11/14/16) |
| +34 | u8 `NodeFlags2`: 0x10 RandomRotationDir, 0x40 RandomUpVector (others unknown) |
| +35 | u8 `BillboardType` (0 Camera, 1 Front, 2 None; only AutoOriented emissions use it) |
| +36 | u8 emitter type / emission type (below) |
| +37 | u8 `NodeType` (0 Null, 1 Emitter, 2 Emission) |
| +38 | i16 `MaxInstances` |
| +40 | u16 `Lifetime`, `Lifetime_Variance` |
| +44 | u8 `StartTime`, `StartTime_Variance`, `BurstFrequency`, `BurstFrequency_Variance` |
| +48 | u16 `I_48`, `I_50` |
| +52 | u16 `Burst`, `Burst_Variance` |
| +56 | u16 `I_56`..`I_62` |
| +64 | f32 `Position` XYZ, then 0 (W) |
| +80 | f32 `Position_Variance` XYZ, 0 |
| +96 | f32 `Rotation` XYZ (degrees), 0 |
| +112 | f32 `Rotation_Variance` XYZ, 0 |
| +128 | u16 `I_128`, `I_130` |
| +132 | f32 `F_132` |
| +136 | u16 `I_136`: 0 Null / ConeExtrude / ShapeDraw, 1 emitters, 2 other emissions (as the writer puts it; checked) |
| +138 | u16 keyframed value count |
| +140 | i32 keyframed values offset, relative to node + 136 |
| +144 | u16 modifier count |
| +146 | u16 child count |
| +148 | i32 modifiers offset, relative to the node |
| +152 | i32 next sibling (relative) |
| +156 | i32 first child (relative) |

Node `Position` / `Rotation` place the node relative to its parent. The emitters in this package
use `Rotation (-90, 0, 0)` or `(90, 0, 0)` to point their up vector along the beam axis.

### Emitter data (at node + 160; type byte +36)

- **0 Point** (`VerticalDistribution`; the C# comments call it "cone"): f32 `Position`,
  `Position_Variance`, `Velocity`, `Velocity_Variance`, `Angle`, `Angle_Variance`, `F_1`, `F_2`
  (32 bytes). Particles start `Position` along the up vector and leave at up to `Angle` degrees
  from it, at `Velocity`.
- **1 Sphere** (`SphericalDistribution`): f32 `Size` (radius), `Size_Variance`, `Velocity`,
  `Velocity_Variance` (16 bytes). Velocity is radial; negative means inward.
- **2 / 3 Circle or Square**: f32 `Position`, `_Variance`, `Velocity`, `_Variance`, `Angle`,
  `_Variance`, `Size`, `_Variance`, `Size2`, `_Variance`, i32 `Shape` (0 Circle, 1 Square),
  f32 `EdgeIncrement` (48 bytes). The C# sets `EmitFromArea = (type == 2)`, but its
  `NodeSpecificType` names type 2 `ShapePerimeterDistribution` and type 3
  `ShapeAreaDistribution`. The two names disagree; both are kept as the C# has them. `Size` is
  the radius (Square: the X size), `Size2` the Square's other side.

### Emission data (type byte +36)

At node + 160 is the **ParticleTexture** (112 bytes):

| offset | field |
|---|---|
| +0 | u8 `I_00`..`I_03` |
| +4 | f32 `RenderDepth` |
| +8 | i32 `I_08`, `I_12` |
| +16 | u16 `MaterialID` (EMM material) |
| +18 | i16 texture count |
| +20 | i32 offset (relative to the node) of the texture pointer list: one i32 per texture, the offset of a sampler, relative to the node (0 = empty slot). The reader turns these into sampler indices: `TextureEntryRef` |
| +24 | f32 `ScaleBase`, `ScaleBase_Variance` |
| +32 | f32 `ScaleXY.X`, `ScaleXY_Variance.X`, `ScaleXY.Y`, `ScaleXY_Variance.Y` |
| +48 | f32 `Color1` R G B, `Color1_Transparency` (alpha) |
| +64 | f32 `Color_Variance` R G B A |
| +80 | f32 `Color2` R G B, `Color2_Transparency` |
| +96 | f32 `F_96`, `F_100`, `F_104`, `F_108` |

`ScaleBase` is the particle size. With `EnableScaleXY`, the quad is `ScaleXY.X` by `ScaleXY.Y`
instead. `Color2` is used only with `EnableSecondaryColor` (a gradient across the particle).

Then, at node + 272, the data for the emission type:

- **0 AutoOriented** (a billboard quad; `BillboardType` from node +35): f32 `StartRotation`,
  `_Variance`, `ActiveRotation`, `_Variance` (16 bytes).
- **1 AutoOriented_VisibleOnSpeed**: a quad stretched along its velocity (`VelocityOriented`).
  No data. All the streaks, lines and flame tongues here use it.
- **2 Default** (no billboard): `StartRotation`, `_Variance`, `ActiveRotation`, `_Variance`,
  `RotationAxis` XYZ, 0 (32 bytes).
- **3 ConeExtrude**: u16 `Duration`, `Duration_Variance`, `StepDuration`, point count - 1,
  `I_08`, `I_10`, then i32 offset (relative to the node) of 16-byte points (`WorldScaleFactor`,
  `WorldScaleAdd`, `WorldOffsetFactor`, `WorldOffsetFactor2`). This is an extruded ribbon whose
  width follows the points.
- **4 Mesh**: `StartRotation`, `_Variance`, `ActiveRotation`, `_Variance`, `RotationAxis` XYZ, 0,
  i32 `I_32`, i32 EMG offset (relative to the node), `I_40`, `I_44`, plus an embedded EMG model.
  The EMG is **not ported**: the reader raises if one is present (none are in this package).
- **5 ShapeDraw**: `StartRotation`, `_Variance`, `ActiveRotation`, `_Variance`, u16 point count
  - 1, u16 `BillboardType`, i32 points offset (relative to the node), u16 `I_24`..`I_30`; then 8-byte
  points (X, Y). The points are a 2D outline drawn as a strip of width `ScaleXY.Y` around it,
  scaled by `ScaleXY.X`. Here they are always on the unit circle, starting at 90 degrees. Most are
  closed rings of 19 or 25 points; some are open arcs, such as `Kmh_Ring`'s 240-280 degree arcs and
  the half-ring `ring_2` in `Kmh_4ptcl`. This is how the shockwave and swirl rings are made.

### Keyframed values (16 bytes each)

| offset | field |
|---|---|
| +0 | u8 `Parameter` |
| +1 | u8: low nibble `Component`, high nibble `Interpolate` (0 = step, 1 = linear) |
| +2 | u8 `Loop` |
| +3 | u8 `I_03` |
| +4 | f32 `DefaultValue` (used by modifiers) |
| +8 | u16 `Duration` |
| +10 | i16 keyframe count |
| +12 | i32 data offset, relative to this entry |

The data is: count × u16 `Time`, zero-padded to 4 bytes; count × f32 `Value`; then, when count > 1,
a frame-to-keyframe index table of `Time[last] + 1` u16 entries (keyframe *s* repeated
`Time[s+1] - Time[s]` times, the first also covering `0..Time[0]`, the last once), padded to 4.
The reader checks this table against the times. `Duration` is `Time[last] + 1` when count > 1,
else 0; all 376 values in this package follow that rule. Times are percent of the node's life.
With `Loop`, the sequence repeats every `Duration`.

`(Parameter, Component)` names a property (C# `KeyframedValueType`). The reader stores it as
`Target`:

| Parameter | node type | Component 0 / 1 / 2 / 3 |
|---|---|---|
| 0 | all | `Position` X / Y / Z |
| 1 | all | `Rotation` X / Y / Z; 3 = `ActiveRotation` (AutoOriented, Default, Mesh, ShapeDraw) |
| 2 | emission | `ScaleBase` (comp. 0); with EnableScaleXY: `ScaleXY.X` / `ScaleXY.Y` / `ScaleBase` |
| 2 | sphere emitter | `Size` / `Velocity` |
| 2 | other emitters | `Position` (along up) / `Velocity` / `Angle` |
| 3 | emission | `Color1` R / G / B / `Color1_Transparency` |
| 3 | circle / square emitter | `Size` / `Size2` |
| 4 | emission | `Color2` R / G / B / `Color2_Transparency` |

A keyframed property overrides the constant in the node. The constant is normally the first
keyframe value.

### Modifiers (8 bytes each)

`+0` u8 `Type`, `+1` u8 `Flags`, `+2` u16 keyframed value count, `+4` i32 offset (relative to this
entry) of the keyframed values (same 16-byte format). The EMP types and their targets
(`EMP_Modifier.DecompileEmp`):

| Type | targets |
|---|---|
| 4 Translation, 5 Acceleration, 6 AngleTranslation, 7 AngleAcceleration, 8 PointLoop, 10 Jitter, 12 Attract | (0, 0..2) `Axis` XYZ, (1, 0) `Factor` |
| 9 Vortex | (0, \*) `Axis`, (1, \*) `Direction`, (2, 0) `Radial`, (2, 1) `RotationRate` |
| 11 Drag | (0, 0) `DragStrength` |

For example, `Acceleration` with Axis (0, 1, 0) and Factor 2 is upward acceleration (a gravity
of -2 would be Factor -2). `Translation` is a constant velocity along `Axis`.

### Texture sampler (`EMP_TextureSamplerDef`, 28 bytes; SDBH 36)

| offset | field |
|---|---|
| +0 | u8 `I_00` |
| +1 | u8 `EmbIndex` (texture in the `.ptcl.emb`) |
| +2 | u8: low nibble `KeyframeType` (0 Sequential, 1 SequentialLoop, 2 Random, 3 Unk3), high nibble `I_02_b` |
| +3 | u8: `I_03_a`, `I_03_b` |
| +4 | u8 `FilteringMin`, `FilteringMag` (0 None, 1 Point, 2 Linear) |
| +6 | u8 `RepetitionU`, `RepetitionV` (0 Wrap, 1 Mirror, 2 Clamp, 3 Border) |
| +8 | u8 `SymmetryU`, `SymmetryV` |
| +10 | u16 `ScrollType` |

What follows depends on `ScrollType`:

- **0 Static**: f32 `ScrollU`, `ScrollV`, `ScaleU`, `ScaleV`. A fixed UV offset and size, so a
  sub-rectangle of the texture.
- **1 Speed**: f32 `ScrollSpeed_U`, `ScrollSpeed_V` (UV per frame), then 8 zero bytes.
- **2 SpriteSheet**: 10 zero bytes, i16 keyframe count, i32 offset (relative to sampler + 12) of
  20-byte keyframes: i32 `Time` (frames this cell is shown), f32 `ScrollU`, `ScrollV` (the cell's
  UV origin), `ScaleU`, `ScaleV` (cell size). `KeyframeType` says how the cells play: in order, in
  a loop, or one random cell per particle (`Random`, e.g. `tsubu00`).

## ETR (traces / beam bodies)

Header (24 bytes): `+0` "#ETR", `+4` u16 0xFFFE, `+6` u16 24, `+8` i32 Version (37568),
`+12` i16 node count, `+14` i16 sampler count, `+16` i32 node offset (24), `+20` i32 sampler offset.
Nodes are 176 bytes, back to back; each node's extra data follows all the nodes. Samplers use the
EMP format (DBXV2 size).

**ETR_Node** (176 bytes):

| offset | field |
|---|---|
| +0 | 32s `AttachBone` |
| +32 | 32s `AttachBone2` |
| +64 | f32 `Position` XYZ |
| +76 | f32 `Rotation` XYZ (radians) |
| +88 | u8 `I_88` |
| +89 | u8 extrude path count - 1 |
| +90 | u16 `StartTime` |
| +92 | u8 `I_92` |
| +93 | u8 `SegementFrameSize` (C# comment: "NumberFrameForNextSegment") |
| +94 | i16 `ExtrudeDuration` (frames the trail grows) |
| +96 | u32 `Flags` (below) |
| +100 | i32 `I_100` |
| +104 | f32 `PositionExtrudeZ` |
| +108 | u16 `MaterialID` (`.trc.emm`) |
| +110 | u16 texture count |
| +112 | i32 texture pointer list (relative to the node; as EMP) |
| +116 | i32 extrude data (relative to the node): (count) 16-byte `ExtrudePaths` (`ConeExtrudePoint`), then the shape points |
| +120 | f32 `Color1` RGB, `Color1_Transparency` |
| +136 | f32 `Color2` RGB, `Color2_Transparency` |
| +152 | f32 `Scale` (width / radius) |
| +156 | i32 shape point count - 1 (0 = none) |
| +160 | u16 `HoldDuration` (frames the full trail stays, then fades) |
| +162 | u16 modifier count |
| +164 | i32 modifiers offset (relative to node + 120) |
| +168 | u16 `I_168` (1) |
| +170 | u16 keyframed value count |
| +172 | i32 keyframed values offset (relative to node + 168) |

`Flags`: 0x1 AutoOrientation, 0x4 NoDegrade, 0x8 DoublePointOfMiddleSection, 0x100
DisplayMiddleSection, 0x200 UVPauseOnExtrude, 0x10000 UVPauseOnHold (others unknown). The XV2-Tools
preview draws a Color1 to Color2 gradient unless NoDegrade is set.

`ExtrudeShapePoints` (X, Y in -1..1) are the cross-section of the extruded tube. With none, the
trace is a flat ribbon. Here the outer layers use closed circles of 25 or 13 points, so they are
round tubes of radius `Scale`.

**ETR keyframed value** (16 bytes): `+0` u8 `ETR_InterpolationType`, `+1` u8 `Parameter`, `+2` u8
`Component` (low nibble) | `Interpolate` (high nibble), `+3` u8 `I_03` (9), `+4` u16 0, `+6` u16
count, `+8` i32 times offset, `+12` i32 values offset (both relative to the entry). The times are
u16 **frames**, padded to 4; the values are f32. After the values the writer appends **204 zero bytes**
("no idea what these are" in the C#; XenoXML zeroes them too). The reader consumes them and keeps
them (`_dummy_204`) if any is non-zero.

`ETR_InterpolationType` says when the keyframes apply:

- 0 DefaultEnd: over the hold, from the end of the extrude.
- 1 Default: over the extrude.
- 2 ShapeStartToEnd: along the trail's length.

Targets: (0, 0..2) `Color1` RGB, (0, 3) `Color1_Transparency`, (1, \*) `Color2`, (2, 0) `Scale`.

ETR modifiers use the EMP 8-byte format, with types 2 Translation, 3 Acceleration,
4 InverseTranslation, 5 InverseAcceleration and 7 Unk7. Unk7 targets are (1, \*) `Axis2`, (2, 0)
`Unk7_20` and (2, 1) `Unk7_21`. The Kamehameha has none.

## EMM (materials)

`+0` "#EMM", `+4` u16 0xFFFE, `+6` u16, `+8` i32 Version, `+12` i32 offset of the material count.
This offset is also the header size, 16 or 32. A 32-byte header has `+16` i32 `Unknown_Data`
offset (68 bytes of i32 at the end of the file). Then come i32 count and count × i32 material
offsets (relative to the header size; 0 = null).

Material: 32s `Name`, 32s `ShaderProgram`, `+64` i16 parameter count, `+66` u16 `I_66`, then
40-byte parameters: 32s `Name`, i32 `Type` (0 Float, 1 Bool, 65536 Float2, 65537 Int), 4-byte value.

Parameters used by the particle materials here:

- `AlphaBlend` = 1 with `AlphaBlendType` 0 normal (alpha), 1 additive or 2 subtractive.
- `Glare` and `GlareColR/G/B/A`: the bloom contribution.
- `ZWriteMask`, `AlphaSortMask`, `BackFace`, `TwoSidedRender`.
- `LowRez` / `LowRezSmoke`: drawn into the half-resolution buffer.
- `MatOffset0X`: the soft-particle fade distance on `SoftParticleDecal`.

Material names encode this: `add*` additive, `nml*` normal, `sub` subtractive, `_G` glare,
`_BF` backface, `_LR2/4` low resolution. One exception: `add_G` is `AlphaBlendType` 0 (normal), not
additive.

## EMA (noted only)

`+8` i32 Version, `+12` i32 skeleton offset, `+16` u16 animation count, `+18` u16 `EmaType` (3 obj,
4 light, 8 mat), `+32` i32 animation offsets. An animation has `+0` u16 EndFrame, `+2` u16
command count, `+4` i32 value count, `+10` u16 FloatPrecision (1 f16, 2 f32, 0 Vector4 f32),
`+12` name (offset + 11), `+16` values. `read_ema` lists names, lengths and raw values. The
commands (which light or material property each curve drives) are not decoded.

## Not ported

- **EMG meshes** inside Mesh emissions (type 4): the reader raises if it meets one.
- XV2-Tools' "full decompile" step. It merges the per-component keyframed values into
  colour / vector tracks and fills in loop copies and end keyframes. The reader keeps the raw
  per-component lists (with `Target` names), which is what the file holds.
- Hue tools, the UI and XML. EMA command and keyframe decoding (light colours and intensities,
  material curves). EMO models. ECF (colour-change, `CBIND`) files: there are none here.

---

## Kamehameha (000_GOK_KMH)

The package is Goku's Kamehameha effect (`000` = Goku's character code). It has 8 effect ids and
4 asset containers:

- **EMO**: models `Kmh_Fire`, `Kmh_Bas`, `Kmh_Hand`.
- **PBIND**: 8 EMPs.
- **TBIND**: 3 ETRs.
- **LIGHT**: `Kmh_Crg`, `Kmh_Fire`, `Kmh_Bas` light EMAs.

The game's BAC / BSA (skill files, not part of this export) spawn these ids. The roles below are
read from the data: bones, timing, contents.

There is **no impact or explosion effect** in this EEPK. The hit effect comes from another
(common) EEPK.

### Effect ids

| id | role | bone | parts (start frame, EEPK scale) |
|---|---|---|---|
| **0** | **charge** in the left hand | `g_L_Hand` | `Kmh_Crg.light` (EMA_Loop, LoopCancel); `Kmh_tsubu.emp` t0; `Kmh_Crg.emp` t0 ×0.4, t42 ×0.6, t78 ×1.0; `Kmh_CrgON.emp` t42 ×0.8, t78 ×1.2; `Kmh_Fire.light` t42 ×0.8, t78 ×1.2 |
| **10** | the same charge on `b_C_Hand` (a centre hand bone), offset (-0.1, 0, 0.1) | `b_C_Hand` | as id 0, power-ups at t30 / t70 (light at t30 / t72) |
| **15** | **long (held) charge** | `g_L_Hand` | `Kmh_Crg.light` + `Kmh_Crg.emp` ×1.0 restarted every 40 frames, t0..t280 (8 copies, ~5 s) |
| **1** | **fire**: the burst at the hands on release | `g_L_Hand` | `Kmh_Fire.emo` (30-frame obj / mat animation), `Kmh_Fire.light` (60 frames), `Kmh_Ring.emp` ×0.8; all t0, LoopCancel |
| **3** | **beam**, size 1 | `TRS` | `Kmh_Bas.light` (loop); `Kmh_Bas.emo` ×1.6 (80-frame animation, EMA_Loop); `Kmh_Fireptcl.emp` ×1.6 at z -0.3; `Kmh_Wav.emp` ×1.8; `Kmh_4ptcl.emp` ×1.6 at z -0.15; **`Kmh_Beam.etr`** (External); `Kmh_Hand.emo` ×0.45 at z -0.3 (EMA loop 20..50); `Kmh_LineAll.emp` ×1.0 |
| **4** | beam, size 2 | `TRS` | as 3 with `Kmh_Beam2.etr`: Bas ×2.0, Fireptcl ×1.8 at z -0.5, Wav ×2.0 at z +0.15, 4ptcl ×2.0, Hand ×0.5 at z -0.5. No LineAll |
| **5** | beam, size 3 | `TRS` | as 4 with `Kmh_Beam3.etr`: Bas ×2.5, Fireptcl ×2.2 at z -0.7, Wav ×2.3 at z +0.3, 4ptcl ×2.0, Hand ×0.6 at z -0.7 |
| **16** | beam, size 3, faded near the camera | `TRS` | id 5 with larger near-fade distances (`NearFadeDistance..FarFadeDistance`: Bas 3..500 instead of 1..500, Fireptcl 2..500, Hand 3..500) and fades added to 4ptcl (1..500) and Beam3 (2.5..200). Probably for a camera close to the beam |

`TRS` is the root of the spawned projectile (BSA): the beam head. In the beam ids, every
particle EMP and both models follow that object. The ETR is `External`; its nodes attach to
bone `TRS` themselves and extrude from where the projectile started, so the trace is the beam's
body.

Timeline:

- **Charge** (0 / 10 / 15):
  - **Frame 0**: a small glow and swirl appears at the hand. `Kmh_tsubu` draws streaks into
    the hand for 50 frames.
  - **Frames 42 and 78** (30 / 70 for id 10): a "power up" pulse (`Kmh_CrgON`: flash and ring)
    and a bigger `Kmh_Crg`. The light grows (×0.8, ×1.2).
- **Fire** (1): a burst of the fire model, a light, and the expanding shockwave arcs of
  `Kmh_Ring`, at the moment of release.
- **Beam** (3 / 4 / 5): the head looks the same in all three sizes. The ETR body:

  | ETR | grows over | holds | ends at |
  |---|---|---|---|
  | Beam | 60 frames | 18-20 frames | ~78 |
  | Beam2 | 80 frames | 18-22 frames | ~98-102 |
  | Beam3 | 100 frames (one layer 80) | 20-24 frames | ~120-124 |

  The looping EMPs (Wav, 4ptcl, LineAll, parts of Fireptcl) run until the effect is cancelled.

### The EMPs

Colours below are `Color1` RGB and alpha. Sizes are `ScaleBase` or `ScaleXY` before the EEPK
scale. Lives are in frames. Blend is from the EMM material. Textures are at `scratchpad/kmhx/`.

**Kmh_Crg.emp**: the charge ball (16 nodes, non-looping, done by ~frame 92):

- `sprite`: a `circle00` crescent glow. Size 0.35→1, colour (0, 1→0, 1) (cyan to blue), additive,
  life 26, spinning.
- `line` / `line_2`: `ray00` streaks, velocity-oriented, swirling in (Vortex modifier).
  - `line`: 0.085 × 0.8, cyan with white `Color2`, additive.
  - `line_2`: blue (0.35, 0.64, 1), normal blend.
- `sprite_1*`: three stacked `4ptcl` orbs, life 60, alpha in / out:
  - a 0.15 additive (0.83, 1, 1);
  - a 0.3 normal (0, 0.7, 1);
  - a 0.325 **subtractive** orange (1, 0.3, 0), which reads as a dark blue core.
- `flash`: a 0.275→1 additive `4ptcl` flash (0.46, 1, 1), 12 frames.
- `ring`, `ring_1`, `ring_2`: ShapeDraw arcs (`4ptcl`), radius 0.35 / 0.25 / 0.7 shrinking to 0.01,
  random rotation 180° in all axes, every 5±3 frames. Cyan-white, normal blend with glare.
- `sprite_2`: `tex01` (a blue vortex) 0.75→0, normal blend, life 16, spinning.

**Kmh_CrgON.emp**: the power-up pulse (5 nodes, ~14 frames):

- a `circle00` sprite 0.285→0.6;
- an additive `4ptcl` flash 0.275→1;
- a ShapeDraw `circle00` arc ring 0.25→0.75.

**Kmh_tsubu.emp**: the inflow (3 nodes, ~66 frames). A Sphere emitter, radius 1, velocity -4
(inward), 1 particle per frame for 50 frames. It emits velocity-oriented `4ptcl` lines 0.01 × 0.25
(and 0.005 × 0.25), (0.4, 0.7, 1) going to white or purple, alpha 0.1→1, additive, life 16.

**Kmh_Ring.emp**: the firing shockwave (5 nodes, ~54 frames). A Point emitter (rotated 90° on X)
fires 1 at velocity 6. Its children are ShapeDraw arcs rolled -32° on Z, all `nml_LR2_G_BF` /
`nml_G_BF`:

- `wev01_2`: `Wev01`, ScaleXY.X 1→2.5, life 26.
- `wev01`: `Wev01`, 2.75→3.75 × 0.5, start 4, life 40.
- `wev02` / `wev02_1`: `wev02`, 3.15→4.15 × 1→0.1, start 16 / 8, life 26.

The colours go from (0, 0.5, 1) to (0.8, 1, 1), with `Color2` (0.5, 1, 1).

**Kmh_Fireptcl.emp**: the beam head's flames and sparks (20 nodes; `up_1`, `edge_1` and
`directional` loop):

- `4circle` / `4circle_L`: big `4circle00` glows, 0.55 and 1→1.75→1.5, deep blue (0, 0.3, 1).
  One is normal blend, one additive. `RenderDepth` -0.5 / -0.3 (drawn in front).
- `up_1` (Circle radius 0.3, angle 45±12): `wev00` / `_Gr` / `_Re`. These are velocity-oriented
  `Wev00` flame tongues, 0.2 × 0.77, in cyan, green-cyan and blue, life 12, pushed back along -Z
  (Acceleration).
- `up_1_1` (Circle radius 0.25, velocity 1.4→0): `wev01`, blue (0.16, 0.37, 1), 0.2 × 0.6, life 20.
- `up_1_2`: `wev00_1` additive (0.3, 1, 1), `wev00_2`, and `wev01_short` additive with a white
  `Color2`. 0.35 × 1.15, life 22.
- `4ptcl02`: a 0.6 additive white flash, 12 frames.
- `edge` / `edge_1` (Circle radius 0.5, velocity 4-5±4-5): `tsubu00` sparks 0.1 (0.34, 0.74, 1)
  with Drag 5. Also `line` / `line_1`, thin white streaks 0.0025-0.005 × 0.2-0.3.
- `directional` (looping, every 4±3 frames, up to 16): ShapeDraw `wev02` arcs 0.55→1.35, colour
  (0.33, 0.76, 1), alpha 0.2→1→0.2.

**Kmh_Wav.emp**: the head's flicker (13 nodes, all looping):

- `edge` (Circle radius 0.1, angle 20±10, 4 every 2 frames): velocity-oriented `Wev00` flames.
  0.17 × 0.32, life 8. One blue (0.17, 0.47, 1) normal, one cyan (0, 1, 1) at alpha 0.6.
- `sprite_Loop*`: 4-frame looping `4ptcl02` glows:
  - 0.2 additive white;
  - 0.45 cyan (0.36, 1, 1) at alpha 0.6, normal;
  - a 0.35 × 0.15 spinning additive streak.
  Each has 15-frame "yoin" afterglow children: 0.35→0.05 and 0.6→0.
- `aura00` puffs: 0.25-0.35, white→cyan, additive, life 32.

**Kmh_4ptcl.emp**: the core glow and the big halo (38 nodes, all roots loop):

- `4ptcl02_loop_1`: a 0.8 **soft particle** `4ptcl02` (`nml_GB_soft`), blue (0, 0.3, 1) at
  alpha 0.3. It is the large halo.
- `4ptcl02_loop`: a 0.5 additive white core.
- `4ptcl_loop`: a 0.65 (0.19, 0.64, 1) at alpha 0.5.

Each of these three has a `*_yoin` child, 12-16 frames, whose red and green fade out, leaving
(0, 0.5, 1).

Under them:

- `aura00` puffs: 0.3-0.55, cyan (0.5, 1, 1) / (0.25, 0.5, 1), additive, life 32-48, drifting
  back along -Z and up.
- `sprite_2*`: `tsubu00` sparks 0.1, 20 per burst, with Vortex and Drag.
- Long streak emitters along the beam axis: Point emitters at `Position_Variance` 3-7 with
  velocity-oriented particles:
  - `Wev01` wisps 0.05-0.1 × 0.6-1;
  - `4ptcl02` lines 0.025 × 1→2;
  - `4ptcl` dust 0.005-0.035 (with Vortex), (0.5, 1, 1).
- `ring` / `ring_1`: ShapeDraw `aura00` arcs 0.35 / 0.25 × 2.5, rotating 150-220° over life,
  placed 4 and 7 units back.
- `ring_2*`: `smk00` smoke arcs 0.45→1 × 0.125.
- `directional_3`: a velocity-oriented `4ptcl` 0.45 × 1 (0, 0.6, 1), additive (`4ptcl_half*`).

**Kmh_LineAll.emp**: speed lines around the beam, only in id 3 (14 nodes, looping):

- Square / Circle edge emitters 0.3-0.75, rotated 90° on X:
  - `ray00` additive lines (0.05, 1, 1), 0.025 × 0.8→1.25;
  - `ray03` lines 0.1 × 0.5 and 0.05 × 0.25, fading blue.
- `stripe` / `stripe_1`: ConeExtrude ribbons (`ray03`, 24 frames, 3 points), blue (0.28, 0.6, 1) /
  green (0.28, 1, 0.76). They are spun by a Vortex (Radial 10, RotationRate 40), giving the
  spiral stripes.
- `ring` / `ring_1`: ShapeDraw `wev02` arcs 0.75→1.5 and 0.85→1.75, every 16 frames, velocity 7±3.
- `sprite*`: `tsubu00` sparks 0.025.

### The ETRs: the beam body

Each ETR has 3 nodes on bone `TRS`, `StartTime` 0, `AutoOrientation | NoDegrade |
DisplayMiddleSection` (+ `DoublePointOfMiddleSection` / `Unk5` / `Unk17` / `Unk18`):

| node | texture | material | shape | Scale (Beam / 2 / 3) | UV speed (per frame) | keyframes |
|---|---|---|---|---|---|---|
| 0 core | `beam00` (white core, soft blue edges) | `TraceNML` (normal blend, glare 0.5 / 0.98 / 1.15) | flat ribbon | 0.69 / 0.79 / 0.94 | V -0.05 / -0.08 / -0.05 | over the hold: Scale →0.2-0.04 →0.005, alpha 1 →0 in the last 4 frames |
| 1 | `ring_beamCor` (blue swirl; Beam3: `T2_UV01`) | `TraceNML2` (normal, glare 0 / 1.1 / 1.1) | round tube, 25 points (Beam2 / 3: 13) | 0.65 / 0.75 / 0.8 | V 0.1 | `Color1_Transparency` along the length (ShapeStartToEnd): 0 at the start, 1 from frame 1, 0 at the end; Scale shrinks over the hold |
| 2 | `T2_UV01` (cyan noise; Beam3: `ring_beamCor`) | `TraceNML2` | round tube, 13 points | 0.45 / 0.55 / 0.8 | (0.01, 0.04) / (0.01, 0.07) / (0.01, 0.07) | as node 1 |

All colours are white: (1, 1, 1), with `Color1` alpha 0 animated up. The blue comes from the
textures and the glare. `ExtrudeDuration` 60 / 80 / 100 frames (58 / 80 / 80 for some layers);
`HoldDuration` 18-24.

### What matters for a Smash 4 rebuild

- **Palette**: almost everything is cyan to deep blue.
  - Main tints: (0, 0.3, 1), (0.19, 0.64, 1), (0.35, 0.64, 1), (0.5, 1, 1), (0, 1, 1), and white
    cores.
  - The one warm colour, (1, 0.3, 0), is drawn **subtractive**, so it darkens to blue.
  - Brightness comes from additive `4ptcl02`, `aura00` and `4circle00` layers plus glare.
- **Textures to port**:
  - `beam00`, `ring_beamCor`, `T2_UV01`: the beam body, as scrolling ribbons.
  - `4ptcl` / `4ptcl02`: round glows, 2-cell sprite sheets.
  - `aura00` (4×4 sprite sheet), `Wev00` (4 flame frames), `Wev01` / `wev02` (4×2 wisp sheets),
    `circle00`, `4circle00` (2×2), `tsubu00` (random cells), `ray00` / `ray03` (streaks), `smk00`,
    `tex01` (vortex).
- **Sizes**: the EEPK scale multiplies the EMP sizes.
  - Charge (id 0): ×0.4 → 1.0.
  - Beam (ids 3 / 4 / 5): ×1.6 / 2.0 / 2.5.
  - Beam head glow: ~0.5-0.8 × that. Shock rings at firing: 1-4 units × 0.8.
  - Beam body radius: 0.45-0.94.
  - XV2 units are about metres; scale to Smash by the ratio of character heights.
- **Timing**: both games run at 60 fps, so frame counts carry over.
  - Charge steps at 0 / 42 / 78.
  - The beam grows over 60 / 80 / 100 frames, then shrinks and fades over ~20.
  - Most particles live 8-40 frames. The head layers loop until cancelled.
- **Not particles**:
  - The beam head's solid shape is the **`Kmh_Bas.emo` model**: material `T1_VFX_MTN_DIS_ALPHA`,
    additive core `BasB`, scrolling `TexScrl0V` 4.94, 80-frame loop.
  - The hand glow is `Kmh_Hand.emo`, the fire burst `Kmh_Fire.emo`.
  - These need a Smash model effect (an .efc model entry) or a large billboard substitute.
