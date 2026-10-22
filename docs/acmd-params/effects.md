# Effect / graphics ACMD commands: parameter labels

74 commands. Labels for **every** slot are in `tools/Sm4shCommand/param_labels.json`; this file is the
readable version. Confidence: **H** read off the handler / module code, **M** mechanism read off the code
but the meaning inferred (or inferred from values + an Ultimate equivalent), **L** values only / stub.

## How it was done

- Handler per command: CRC -> index table `0x100FAAB8`, handler table `0x10350ED8` (cross_f.rpx).
- Each handler run in unicorn with a fake module accessor whose module vtables all point at
  recording stubs; params filled with markers, so every module call shows which param lands in
  which register / MSC argument word (`emu.py`, `probe.py`, results `emu_out.txt`).
- Most effect handlers copy an args template and call a module's MSC handler; the EffectModule one
  (vtable `0x10105FE8`, `+0x2EC` = `0x02C2CEC8`) was disassembled per op, plus the trail creator,
  kill / light / follow internals, the AreaModule (wind) handler `0x02BFF64C` (+0x12C) and a few
  direct EffectModule vtable functions.
- Vanilla values: every use in the 1053 vanilla ACMD files.

## Findings that apply to many commands

- **EffectModule MSC ops** (EffectModule = accessor `+0xA0`): 0x2710 EFFECT (16 words: eff, bone,
  pos3, rot3, scale, rand pos3, rand rot3, terminate), 0x2711 ground-material EFFECT, 0x2712
  FOLLOW (+handle), 0x2713 FOLLOW unsync-vis (flag 0x400000), 0x2716 EFFECT_STRENGTH,
  0x2717 FOLLOW (facing-adjusted), 0x2718 FOLLOW_STRENGTH, 0x271A FOLLOW no-stop (+gfx offset,
  +mta), 0x271B/0x271C/0x2731 after-image/sword trail, 0x2723 OFF_KIND, 0x2729 EFFECT+light,
  0x272A FOLLOW+light, 0x272C EFFECT_COLOR, 0x272D EFFECT_ALPHA, 0x272E FOLLOW_ALPHA,
  0x272F FOLLOW_RND, 0x2730 FOLLOW_COLOR, 0x2732/0x2733 line circle req/remove,
  0x2738-0x2742 FLIP variants (0x2738 EFFECT_FLIP, 0x2739 FOLLOW_FLIP, 0x273A LANDING,
  0x273B FOLLOW_FLIP_RND, 0x273C FLIP_COLOR, 0x273D FOLLOW_FLIP_COLOR, 0x273E FLIP_ALPHA,
  0x273F FOLLOW_FLIP_ALPHA, 0x2740 FOLLOW_NO_STOP_FLIP, 0x2741 FOOT, 0x2742 DOWN), op 0x20
  remove common, op 0x28 sync scale.
- **Flip commands**: the ACMD handler moves its *last* param into MSC word 3. The module picks
  GFXRight (word 1) or GFXLeft (word 2) by `MotionModule(+0x44) vt+0x26C` (is_flip), and passes
  word 3 as the request's flip argument only when flipped -> the last param is the **flip type**
  (EF_FLIP style; 1 in ~95% of vanilla uses, 0/3/4 rare). Exact enum values not decoded (M).
- **Terminate** in follow forms is flag `0x4000`; follow requests also get `0x8000` except the
  NO_STOP forms (stop-in-hitlag bit). The after-image "Anchored" bool sets the same `0x4000`.
- **Alpha** params are percent (handler divides by 100); **colour** params are 0-255 (divided by
  255 in the module). Graphic_Effect7 = EFFECT_ALPHA (last param alpha), Graphic_Effect6 =
  EFFECT_FOLLOW_ALPHA.
- **Kill flags** (Terminate_Graphic_Effect p1/p2, EFFECT_OFF p1): bool1 kills emitter sets at once
  (else stop emitting and fade), bool2 also ends the attached light at once; both = delete now.
- **Trails** (Sword_Glow / AFTER_IMAGE*): tex index -> name table -> `<name>.nut`; frames >= 2;
  byte 'Axis' 0/1/2 = X/Y/Z; BlendMode < 14 (|0x900); Shader -> `"0x4F%06x"` (>=1000 adds a
  second pass). Sword_Glow p0 is texture 1 (acmd_info says "Color"). The f2 float in the
  AFTER_IMAGE2 / Sword_Glow forms is passed but never read.
- **Lights** (EFFECT_LIGHT, EFFECT_FOLLOW_LIGHT): RGB /255, intensity, offset xyz (x mirrored);
  EFFECT_LIGHT_END fades lights matching an attribute mask over N frames.
- **Wind** (AreaModule +0x60): Aesthetic_Wind_Effect = AREA_WIND_2ND (op 0x2715, rect area,
  angle in degrees, 361 = none), Aesthetic_Wind_Effect2 = AREA_WIND_2ND_RAD (op 0x2717, circle).
  The last int of each is optional (the AREA_WIND_2ND* hashes omit it).
- **acmd_info mismatch**: EFFECT_FLIP_COLOR has 21 params (size 22) but its syntax lists 20; the
  21st is Blue.
- **EFFECT_ROTW** handler is a stub (skips 16 params) -> names by analogy only.
- **EFFECT_FOLLOW_STR** p1 is a bone-*name* CRC32, only "ThrowN"/"TopN" resolve.
- **Morph_Model_Event** goes to ItemModule (+0x64) op 0x16, not a model morph: likely held-item
  visibility (L).

## Per command

### AFTER_IMAGE2_ON `6F4AACA8` (23 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Texture | H | trail texture index (looked up in the trail texture-name table, loaded as "<name>.nut"); no second texture in this form | 6 x19 (n=19) |
| 1 | BlurLength | H | trail length in frames (must be >= 2; history buffer = frames*16+1) | 5 x15, 7 x4 (n=19) |
| 2 | Bone1 | H | bone of trail edge point 1 | 25 x19 (n=19) |
| 3 | X1 | H | edge point 1 offset X | 0 x14, -0.00896f x5 (n=19) |
| 4 | Y1 | H | edge point 1 offset Y | 13.3f x7, 9.3f x6, 9.02227f x5, 9f x1 (n=19) |
| 5 | Z1 | H | edge point 1 offset Z | -2f x14, -1.89698f x5 (n=19) |
| 6 | Bone2 | H | bone of trail edge point 2 | 25 x19 (n=19) |
| 7 | X2 | H | edge point 2 offset X | 1.5f x14, -0.01245f x5 (n=19) |
| 8 | Y2 | H | edge point 2 offset Y | 19.3f x7, 12.3f x6, 12.522f x4, 15.3f x1, 13f x1 (n=19) |
| 9 | Z2 | H | edge point 2 offset Z | -2f x14, -1.85697f x5 (n=19) |
| 10 | Terminate | M | bool -> trail flag 0x4000 (the same bit follow effects use for Terminate: end with the action). acmd_info calls it "Anchored" on Sword_Glow; always 1 in vanilla | 1 x19 (n=19) |
| 11 | Graphic | H | effect attached to the blade while the trail is on (0 = none); created at Bone3 with the offset/rotation/size below | 0 x19 (n=19) |
| 12 | Bone3 | H | bone of the attached effect | 0 x19 (n=19) |
| 13 | X | H | offset from the bone, X | 0 x19 (n=19) |
| 14 | Y | H | offset from the bone, Y | 0 x19 (n=19) |
| 15 | Z | H | offset from the bone, Z | 0 x19 (n=19) |
| 16 | RotX | H | attached-effect rotation (degrees, converted to radians) about X | 0 x19 (n=19) |
| 17 | RotY | H | attached-effect rotation (degrees, converted to radians) about Y | 0 x19 (n=19) |
| 18 | RotZ | H | attached-effect rotation (degrees, converted to radians) about Z | 0 x19 (n=19) |
| 19 | Size | H | attached-effect scale (uniform; also the trail scale vector) | 1f x19 (n=19) |
| 20 | TrailMode | L | byte stored at trail+0x14 (word). 0 = default (texture samplers set up with 0x47F7); >2 changes the cull-3 path. Sword_Glow always 0; AFTER_IMAGE2_ON uses 8 | 8 x19 (n=19) |
| 21 | Axis | H | trail width axis: 0 = X, 1 = Y, other = Z (Ultimate EFFECT_AXIS_X/Y/Z). Mii Swordfighter uses 1 | 2 x19 (n=19) |
| 22 | Unused | M | float passed in f2 to EffectModule vt+0xEC and never read (0 for Sword_Glow, 4.0 for AFTER_IMAGE2_ON) | 4f x19 (n=19) |

Evidence: MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158 / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5304 picks (1,0,0)/(0,1,0)/(0,0,1) / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5530/0x032F5764 / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; vt+0xEC body has no f2 use

### AFTER_IMAGE2_ON_WORK `E07CF8BB` (23 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | TextureWork | H | work int variable id holding the trail texture index (looked up in the trail texture-name table, loaded as "<name>.nut"); no second texture in this form | no vanilla uses |
| 1 | BlurLength | H | trail length in frames (must be >= 2; history buffer = frames*16+1) | no vanilla uses |
| 2 | Bone1 | H | bone of trail edge point 1 | no vanilla uses |
| 3 | X1 | H | edge point 1 offset X | no vanilla uses |
| 4 | Y1 | H | edge point 1 offset Y | no vanilla uses |
| 5 | Z1 | H | edge point 1 offset Z | no vanilla uses |
| 6 | Bone2 | H | bone of trail edge point 2 | no vanilla uses |
| 7 | X2 | H | edge point 2 offset X | no vanilla uses |
| 8 | Y2 | H | edge point 2 offset Y | no vanilla uses |
| 9 | Z2 | H | edge point 2 offset Z | no vanilla uses |
| 10 | Terminate | M | bool -> trail flag 0x4000 (the same bit follow effects use for Terminate: end with the action). acmd_info calls it "Anchored" on Sword_Glow; always 1 in vanilla | no vanilla uses |
| 11 | GraphicWork | H | work int variable id holding effect attached to the blade while the trail is on (0 = none); created at Bone3 with the offset/rotation/size below | no vanilla uses |
| 12 | Bone3 | H | bone of the attached effect | no vanilla uses |
| 13 | X | H | offset from the bone, X | no vanilla uses |
| 14 | Y | H | offset from the bone, Y | no vanilla uses |
| 15 | Z | H | offset from the bone, Z | no vanilla uses |
| 16 | RotX | H | attached-effect rotation (degrees, converted to radians) about X | no vanilla uses |
| 17 | RotY | H | attached-effect rotation (degrees, converted to radians) about Y | no vanilla uses |
| 18 | RotZ | H | attached-effect rotation (degrees, converted to radians) about Z | no vanilla uses |
| 19 | Size | H | attached-effect scale (uniform; also the trail scale vector) | no vanilla uses |
| 20 | TrailMode | L | byte stored at trail+0x14 (word). 0 = default (texture samplers set up with 0x47F7); >2 changes the cull-3 path. Sword_Glow always 0; AFTER_IMAGE2_ON uses 8 | no vanilla uses |
| 21 | Axis | H | trail width axis: 0 = X, 1 = Y, other = Z (Ultimate EFFECT_AXIS_X/Y/Z). Mii Swordfighter uses 1 | no vanilla uses |
| 22 | Unused | M | float passed in f2 to EffectModule vt+0xEC and never read (0 for Sword_Glow, 4.0 for AFTER_IMAGE2_ON) | no vanilla uses |

Evidence: MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158 / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5304 picks (1,0,0)/(0,1,0)/(0,0,1) / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5530/0x032F5764 / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; vt+0xEC body has no f2 use

### Sword_Glow `D7F6CBCD` (26 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Texture1 | H | trail texture 1 index (name table -> "<name>.nut"; 0 = none) | 4 x38, 191 x35, 9 x33, 1 x27, 196 x26 (n=444) |
| 1 | Texture2 | H | trail texture 2 index (name table -> "<name>.nut"; 0 = none) | 143 x38, 192 x35, 144 x33, 137 x27, 197 x26 (n=444) |
| 2 | BlurLength | H | trail length in frames (must be >= 2; history buffer = frames*16+1) | 4 x99, 6 x76, 5 x74, 8 x68, 7 x46 (n=444) |
| 3 | Bone1 | H | bone of trail edge point 1 | 1002 x161, 1000 x148, 25 x55, 1011 x32, 1010 x18 (n=444) |
| 4 | X1 | H | edge point 1 offset X | 0 x375, 1f x35, 0.3f x25, 1.2f x9 (n=444) |
| 5 | Y1 | H | edge point 1 offset Y | 0 x295, 1.7f x49, 0.5f x31, 0.4f x22, 1f x16 (n=444) |
| 6 | Z1 | H | edge point 1 offset Z | 0 x220, 0.5f x164, 0.3f x33, 1f x6, -0.2f x6 (n=444) |
| 7 | Bone2 | H | bone of trail edge point 2 | 1002 x161, 1000 x148, 25 x55, 1011 x32, 1010 x18 (n=444) |
| 8 | X2 | H | edge point 2 offset X | -1e-05f x201, 0 x174, 13f x35, 11f x25, 15.8f x9 (n=444) |
| 9 | Y2 | H | edge point 2 offset Y | -2e-05f x161, 0 x73, 16f x54, 13.5f x27, 10.8f x24 (n=444) |
| 10 | Z2 | H | edge point 2 offset Z | 0 x220, 12.2f x104, 13f x36, -2f x20, 15.2f x12 (n=444) |
| 11 | Terminate | M | bool -> trail flag 0x4000 (the same bit follow effects use for Terminate: end with the action). acmd_info calls it "Anchored" on Sword_Glow; always 1 in vanilla | 1 x444 (n=444) |
| 12 | Graphic | H | effect attached to the blade while the trail is on (0 = none); created at Bone3 with the offset/rotation/size below | 0 x57, 0x3250000 x44, 0x3120000 x42, 0x31D0000 x38, 0x3200000 x34 (n=444) |
| 13 | Bone3 | H | bone of the attached effect | 1002 x161, 1000 x148, 25 x55, 1011 x32, 1010 x18 (n=444) |
| 14 | X | H | offset from the bone, X | 0 x434, -0.015f x10 (n=444) |
| 15 | Y | H | offset from the bone, Y | 0 x426, -0.05f x10, 0.8f x2, 0.83f x2, -0.88f x2 (n=444) |
| 16 | Z | H | offset from the bone, Z | 0 x441, -0.2f x3 (n=444) |
| 17 | RotX | H | attached-effect rotation (degrees, converted to radians) about X | 0 x413, 180f x31 (n=444) |
| 18 | RotY | H | attached-effect rotation (degrees, converted to radians) about Y | 0 x381, 90f x50, -90f x13 (n=444) |
| 19 | RotZ | H | attached-effect rotation (degrees, converted to radians) about Z | 0 x444 (n=444) |
| 20 | Size | H | attached-effect scale (uniform; also the trail scale vector) | 1f x441, 1.05f x3 (n=444) |
| 21 | TrailMode | L | byte stored at trail+0x14 (word). 0 = default (texture samplers set up with 0x47F7); >2 changes the cull-3 path. Sword_Glow always 0; AFTER_IMAGE2_ON uses 8 | 0 x444 (n=444) |
| 22 | Axis | H | trail width axis: 0 = X, 1 = Y, other = Z (Ultimate EFFECT_AXIS_X/Y/Z). Mii Swordfighter uses 1 | 0 x417, 1 x27 (n=444) |
| 23 | Unused | M | float passed in f2 to EffectModule vt+0xEC and never read (0 for Sword_Glow, 4.0 for AFTER_IMAGE2_ON) | 0 x444 (n=444) |
| 24 | BlendMode | M | trail blend/render state (must be < 14; OR 0x900; Ultimate TRAIL_BLEND_*). 11 almost always, 1 Lucario, 2 one Roy set. AFTER_IMAGE2 forms default to 2 | 11 x436, 1 x4, 2 x4 (n=444) |
| 25 | Shader | M | trail shader: loads shader "0x4F%06x"; values >= 1000 subtract 1000 and also load a second shader (n+1000). 1 almost always, 1001 Greninja, 0 Lucario | 1 x425, 1001 x13, 0 x4, 2 x2 (n=444) |

Evidence: MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158 / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5304 picks (1,0,0)/(0,1,0)/(0,0,1) / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5458/0x032F5640 "0x4f%06x" / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5530/0x032F5764 / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5A58 / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; vt+0xEC body has no f2 use

### AFTER_IMAGE3_ON_ATTACH_WORK `11097635` (26 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Texture1 | H | trail texture 1 index (name table -> "<name>.nut"; 0 = none) | no vanilla uses |
| 1 | Texture2 | H | trail texture 2 index (name table -> "<name>.nut"; 0 = none) | no vanilla uses |
| 2 | BlurLength | H | trail length in frames (must be >= 2; history buffer = frames*16+1) | no vanilla uses |
| 3 | Bone1 | H | bone of trail edge point 1 | no vanilla uses |
| 4 | X1 | H | edge point 1 offset X | no vanilla uses |
| 5 | Y1 | H | edge point 1 offset Y | no vanilla uses |
| 6 | Z1 | H | edge point 1 offset Z | no vanilla uses |
| 7 | Bone2 | H | bone of trail edge point 2 | no vanilla uses |
| 8 | X2 | H | edge point 2 offset X | no vanilla uses |
| 9 | Y2 | H | edge point 2 offset Y | no vanilla uses |
| 10 | Z2 | H | edge point 2 offset Z | no vanilla uses |
| 11 | Terminate | M | bool -> trail flag 0x4000 (the same bit follow effects use for Terminate: end with the action). acmd_info calls it "Anchored" on Sword_Glow; always 1 in vanilla | no vanilla uses |
| 12 | GraphicWork | H | work int variable id holding effect attached to the blade while the trail is on (0 = none); created at Bone3 with the offset/rotation/size below | no vanilla uses |
| 13 | Bone3 | H | bone of the attached effect | no vanilla uses |
| 14 | X | H | offset from the bone, X | no vanilla uses |
| 15 | Y | H | offset from the bone, Y | no vanilla uses |
| 16 | Z | H | offset from the bone, Z | no vanilla uses |
| 17 | RotX | H | attached-effect rotation (degrees, converted to radians) about X | no vanilla uses |
| 18 | RotY | H | attached-effect rotation (degrees, converted to radians) about Y | no vanilla uses |
| 19 | RotZ | H | attached-effect rotation (degrees, converted to radians) about Z | no vanilla uses |
| 20 | Size | H | attached-effect scale (uniform; also the trail scale vector) | no vanilla uses |
| 21 | TrailMode | L | byte stored at trail+0x14 (word). 0 = default (texture samplers set up with 0x47F7); >2 changes the cull-3 path. Sword_Glow always 0; AFTER_IMAGE2_ON uses 8 | no vanilla uses |
| 22 | Axis | H | trail width axis: 0 = X, 1 = Y, other = Z (Ultimate EFFECT_AXIS_X/Y/Z). Mii Swordfighter uses 1 | no vanilla uses |
| 23 | Unused | M | float passed in f2 to EffectModule vt+0xEC and never read (0 for Sword_Glow, 4.0 for AFTER_IMAGE2_ON) | no vanilla uses |
| 24 | BlendMode | M | trail blend/render state (must be < 14; OR 0x900; Ultimate TRAIL_BLEND_*). 11 almost always, 1 Lucario, 2 one Roy set. AFTER_IMAGE2 forms default to 2 | no vanilla uses |
| 25 | Shader | M | trail shader: loads shader "0x4F%06x"; values >= 1000 subtract 1000 and also load a second shader (n+1000). 1 almost always, 1001 Greninja, 0 Lucario | no vanilla uses |

Evidence: MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158 / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5304 picks (1,0,0)/(0,1,0)/(0,0,1) / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5458/0x032F5640 "0x4f%06x" / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5530/0x032F5764 / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5A58 / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; vt+0xEC body has no f2 use

### AFTER_IMAGE3_ON_WORK `F707ECF8` (26 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Texture1Work | H | work int variable id holding trail texture 1 index (name table -> "<name>.nut"; 0 = none) | 0x10000084 x45 (n=45) |
| 1 | Texture2Work | H | work int variable id holding trail texture 2 index (name table -> "<name>.nut"; 0 = none) | 0x10000085 x45 (n=45) |
| 2 | BlurLength | H | trail length in frames (must be >= 2; history buffer = frames*16+1) | 4 x22, 3 x7, 10 x6, 6 x5, 8 x3 (n=45) |
| 3 | Bone1 | H | bone of trail edge point 1 | 25 x45 (n=45) |
| 4 | X1 | H | edge point 1 offset X | 0 x45 (n=45) |
| 5 | Y1 | H | edge point 1 offset Y | 0.5f x45 (n=45) |
| 6 | Z1 | H | edge point 1 offset Z | 0 x45 (n=45) |
| 7 | Bone2 | H | bone of trail edge point 2 | 25 x45 (n=45) |
| 8 | X2 | H | edge point 2 offset X | -1e-05f x45 (n=45) |
| 9 | Y2 | H | edge point 2 offset Y | 13.5f x45 (n=45) |
| 10 | Z2 | H | edge point 2 offset Z | 0 x45 (n=45) |
| 11 | Terminate | M | bool -> trail flag 0x4000 (the same bit follow effects use for Terminate: end with the action). acmd_info calls it "Anchored" on Sword_Glow; always 1 in vanilla | 1 x45 (n=45) |
| 12 | GraphicWork | H | work int variable id holding effect attached to the blade while the trail is on (0 = none); created at Bone3 with the offset/rotation/size below | 0x10000083 x45 (n=45) |
| 13 | Bone3 | H | bone of the attached effect | 25 x45 (n=45) |
| 14 | X | H | offset from the bone, X | 0 x45 (n=45) |
| 15 | Y | H | offset from the bone, Y | 0 x45 (n=45) |
| 16 | Z | H | offset from the bone, Z | 0 x45 (n=45) |
| 17 | RotX | H | attached-effect rotation (degrees, converted to radians) about X | 0 x45 (n=45) |
| 18 | RotY | H | attached-effect rotation (degrees, converted to radians) about Y | 0 x45 (n=45) |
| 19 | RotZ | H | attached-effect rotation (degrees, converted to radians) about Z | 0 x45 (n=45) |
| 20 | Size | H | attached-effect scale (uniform; also the trail scale vector) | 1f x45 (n=45) |
| 21 | TrailMode | L | byte stored at trail+0x14 (word). 0 = default (texture samplers set up with 0x47F7); >2 changes the cull-3 path. Sword_Glow always 0; AFTER_IMAGE2_ON uses 8 | 0 x45 (n=45) |
| 22 | Axis | H | trail width axis: 0 = X, 1 = Y, other = Z (Ultimate EFFECT_AXIS_X/Y/Z). Mii Swordfighter uses 1 | 1 x45 (n=45) |
| 23 | Unused | M | float passed in f2 to EffectModule vt+0xEC and never read (0 for Sword_Glow, 4.0 for AFTER_IMAGE2_ON) | 0 x45 (n=45) |
| 24 | BlendMode | M | trail blend/render state (must be < 14; OR 0x900; Ultimate TRAIL_BLEND_*). 11 almost always, 1 Lucario, 2 one Roy set. AFTER_IMAGE2 forms default to 2 | 11 x45 (n=45) |
| 25 | Shader | M | trail shader: loads shader "0x4F%06x"; values >= 1000 subtract 1000 and also load a second shader (n+1000). 1 almost always, 1001 Greninja, 0 Lucario | 1 x45 (n=45) |

Evidence: MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158 / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5304 picks (1,0,0)/(0,1,0)/(0,0,1) / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5458/0x032F5640 "0x4f%06x" / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5530/0x032F5764 / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; 0x032F5A58 / MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158; vt+0xEC body has no f2 use

### AFTER_IMAGE_ON_WORK `50118FAF` (20 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | TextureWork | H | work int variable id holding the trail texture index (looked up in the trail texture-name table, loaded as "<name>.nut"); no second texture in this form | no vanilla uses |
| 1 | BlurLength | H | trail length in frames (must be >= 2; history buffer = frames*16+1) | no vanilla uses |
| 2 | Bone1 | H | bone of trail edge point 1 | no vanilla uses |
| 3 | X1 | H | edge point 1 offset X | no vanilla uses |
| 4 | Y1 | H | edge point 1 offset Y | no vanilla uses |
| 5 | Z1 | H | edge point 1 offset Z | no vanilla uses |
| 6 | Bone2 | H | bone of trail edge point 2 | no vanilla uses |
| 7 | X2 | H | edge point 2 offset X | no vanilla uses |
| 8 | Y2 | H | edge point 2 offset Y | no vanilla uses |
| 9 | Z2 | H | edge point 2 offset Z | no vanilla uses |
| 10 | Terminate | M | bool -> trail flag 0x4000 (the same bit follow effects use for Terminate: end with the action). acmd_info calls it "Anchored" on Sword_Glow; always 1 in vanilla | no vanilla uses |
| 11 | GraphicWork | H | work int variable id holding effect attached to the blade while the trail is on (0 = none); created at Bone3 with the offset/rotation/size below | no vanilla uses |
| 12 | Bone3 | H | bone of the attached effect | no vanilla uses |
| 13 | X | H | offset from the bone, X | no vanilla uses |
| 14 | Y | H | offset from the bone, Y | no vanilla uses |
| 15 | Z | H | offset from the bone, Z | no vanilla uses |
| 16 | RotX | H | attached-effect rotation (degrees, converted to radians) about X | no vanilla uses |
| 17 | RotY | H | attached-effect rotation (degrees, converted to radians) about Y | no vanilla uses |
| 18 | RotZ | H | attached-effect rotation (degrees, converted to radians) about Z | no vanilla uses |
| 19 | Size | H | attached-effect scale (uniform; also the trail scale vector) | no vanilla uses |

Evidence: MSC 0x02C2CEC8 case 0x271B/0x271C/0x2731 (0x02C307F8) -> EffectModule vt+0xEC (0x02C2BE54) -> trail create 0x032F9128/0x032F5158

### Aesthetic_Wind_Effect2 `3C95CD87` (9 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | AreaIndex | H | wind area slot (added to the module area base; Terminate_Wind_Effect takes the same index) | 1 x43, 0 x40 (n=83) |
| 1 | Speed | M | wind strength/speed (struct +0x40) | 1f x36, 2f x31, 3f x9, 4f x5, 0.1f x1 (n=83) |
| 2 | RadialUnk | L | radial-only float (struct +0x50; the angle is forced to 361 = no direction). Vanilla +/-0.02..0.08 | 0.05f x45, 0.02f x16, -0.05f x6, 0.08f x4, -0.02f x3 (n=83) |
| 3 | Duration | M | frames the wind lasts (struct +0x48); 300/1000 are long-lived and usually ended by Terminate_Wind_Effect, 2-8 are short gusts | 200f x25, 300f x20, 1000f x15, 2f x11, 20f x5 (n=83) |
| 4 | Rate | L | struct +0x4C, 0.2-1.0 in vanilla (strength multiplier / falloff) | 1f x66, 0.8f x9, 0.6f x6, 0.2f x2 (n=83) |
| 5 | X | H | area centre X (multiplied by facing) | 0 x57, -5f x5, 30f x4, 10f x3, -4f x3 (n=83) |
| 6 | Y | H | area centre Y | 0 x24, 8f x21, 10f x8, 6f x6, 5f x4 (n=83) |
| 7 | Radius | M | area radius (circle area; area entry shape byte 1) | 25f x13, 30f x12, 20f x12, 35f x7, 12f x6 (n=83) |
| 8 | Unk | L | optional int (only read when present), struct +0x58; vanilla 30-80 | 60 x24, 80 x24, 30 x18, 50 x14, 40 x3 (n=83) |

Evidence: AreaModule (+0x60) MSC 0x02BFF64C case 0x2715/0x2717 (0x02C0011C) -> wind struct -> AreaModule vt+0x11C -> area kind 25 (wind) / AreaModule (+0x60) MSC 0x02BFF64C case 0x2715/0x2717 (0x02C0011C) -> wind struct -> AreaModule vt+0x11C -> area kind 25 (wind); corpus: 97/103 Wind uses with 300 are terminated / AreaModule (+0x60) MSC 0x02BFF64C case 0x2715/0x2717 (0x02C0011C) -> wind struct -> AreaModule vt+0x11C -> area kind 25 (wind); read only if word count > 9

### Aesthetic_Wind_Effect `14C10D92` (10 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | AreaIndex | H | wind area slot (added to the module area base; Terminate_Wind_Effect takes the same index) | 0 x390 (n=390) |
| 1 | Speed | M | wind strength/speed (struct +0x40) | 3f x116, 2f x95, 1f x68, 0.5f x65, 0.2f x11 (n=390) |
| 2 | Angle | H | wind direction in degrees, mirrored by facing (180-a); 361 = no direction (radial) | 100f x52, 110f x49, 20f x30, 120f x29, 0 x27 (n=390) |
| 3 | Duration | M | frames the wind lasts (struct +0x48); 300/1000 are long-lived and usually ended by Terminate_Wind_Effect, 2-8 are short gusts | 2f x125, 300f x103, 3f x85, 8f x24, 4f x17 (n=390) |
| 4 | Rate | L | struct +0x4C, 0.2-1.0 in vanilla (strength multiplier / falloff) | 1f x160, 0.2f x80, 0.8f x38, 0.5f x32, 0.4f x25 (n=390) |
| 5 | X | H | area centre X (multiplied by facing) | 0 x219, -4f x40, 22f x21, -10f x20, 12f x17 (n=390) |
| 6 | Y | H | area centre Y | 12f x192, 8f x59, 10f x50, 5f x26, 30f x14 (n=390) |
| 7 | Width | M | area width/extent X (rect area; shape byte 0) | 30f x127, 24f x76, 50f x35, 40f x26, 20f x25 (n=390) |
| 8 | Height | M | area height/extent Y | 30f x130, 20f x82, 24f x80, 10f x26, 25f x24 (n=390) |
| 9 | Unk | L | optional int (only read when present), struct +0x58; vanilla 0-100 (80/50/40 common) | 80 x123, 50 x110, 40 x53, 0 x38, 30 x21 (n=390) |

Evidence: AreaModule (+0x60) MSC 0x02BFF64C case 0x2715/0x2717 (0x02C0011C) -> wind struct -> AreaModule vt+0x11C -> area kind 25 (wind) / AreaModule (+0x60) MSC 0x02BFF64C case 0x2715/0x2717 (0x02C0011C) -> wind struct -> AreaModule vt+0x11C -> area kind 25 (wind); constants 361, pi/180, 180 at 0x1010265C.. / AreaModule (+0x60) MSC 0x02BFF64C case 0x2715/0x2717 (0x02C0011C) -> wind struct -> AreaModule vt+0x11C -> area kind 25 (wind); corpus: 97/103 Wind uses with 300 are terminated / AreaModule (+0x60) MSC 0x02BFF64C case 0x2715/0x2717 (0x02C0011C) -> wind struct -> AreaModule vt+0x11C -> area kind 25 (wind); read only if word count > 0xA; AREA_WIND_2ND (9 params) omits it

### Terminate_Wind_Effect `D5D67F56` (1 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | AreaIndex | H | wind area slot to remove (AreaModule MSC 0x2716 -> vt+0x114) | 0 x204, 1 x44 (n=248) |

Evidence: AreaModule MSC 0x02C0045C

### DOWN_EFFECT `6A441545` (16 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x100000A x64 (n=64) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x64 (n=64) |
| 2 | X | H | offset from the bone, X | 0 x64 (n=64) |
| 3 | Y | H | offset from the bone, Y | 0 x64 (n=64) |
| 4 | Z | H | offset from the bone, Z | 0 x64 (n=64) |
| 5 | XRot | H | rotation (degrees) about X | 0 x64 (n=64) |
| 6 | YRot | H | rotation (degrees) about Y | 0 x64 (n=64) |
| 7 | ZRot | H | rotation (degrees) about Z | 0 x64 (n=64) |
| 8 | Size | H | uniform scale | 1f x64 (n=64) |
| 9 | RandomX | H | random offset range (+/-) on X | 0 x64 (n=64) |
| 10 | RandomY | H | random offset range (+/-) on Y | 0 x64 (n=64) |
| 11 | RandomZ | H | random offset range (+/-) on Z | 0 x64 (n=64) |
| 12 | RandomXRot | H | random rotation range (+/- degrees) about X | 0 x64 (n=64) |
| 13 | RandomYRot | H | random rotation range (+/- degrees) about Y | 0 x64 (n=64) |
| 14 | RandomZRot | H | random rotation range (+/- degrees) about Z | 0 x64 (n=64) |
| 15 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 0 x35, 1 x29 (n=64) |

Evidence: handler: GroundModule(+0x2C) vt+0x2CC(8) ground material lookup, then EffectModule vt+0x4C with the EFFECT layout; the material table may substitute the effect id

### DOWN_EFFECT_FLIP `EE1BAF5F` (18 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GFXRight | H | effect id used when the motion is not flipped | no vanilla uses |
| 1 | GFXLeft | H | effect id used when the motion is flipped (MotionModule is_flip) | no vanilla uses |
| 2 | Bone | H | bone id the effect is placed on (0 = top/root) | no vanilla uses |
| 3 | X | H | offset from the bone, X | no vanilla uses |
| 4 | Y | H | offset from the bone, Y | no vanilla uses |
| 5 | Z | H | offset from the bone, Z | no vanilla uses |
| 6 | XRot | H | rotation (degrees) about X | no vanilla uses |
| 7 | YRot | H | rotation (degrees) about Y | no vanilla uses |
| 8 | ZRot | H | rotation (degrees) about Z | no vanilla uses |
| 9 | Size | H | uniform scale | no vanilla uses |
| 10 | RandomX | H | random offset range (+/-) on X | no vanilla uses |
| 11 | RandomY | H | random offset range (+/-) on Y | no vanilla uses |
| 12 | RandomZ | H | random offset range (+/-) on Z | no vanilla uses |
| 13 | RandomXRot | H | random rotation range (+/- degrees) about X | no vanilla uses |
| 14 | RandomYRot | H | random rotation range (+/- degrees) about Y | no vanilla uses |
| 15 | RandomZRot | H | random rotation range (+/- degrees) about Z | no vanilla uses |
| 16 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | no vanilla uses |
| 17 | FlipType | M | EF_FLIP-style mirror mode, applied only when MotionModule is_flip (vt+0x26C) is true; passed to the request as the flip argument. Vanilla: 1 almost always (the usual mirror), 0 none, 3/4 rare | no vanilla uses |

Evidence: MSC 0x02C2FA8C / 0x02C3009C flip ops (0x2738-0x2742): MotionModule(+0x44) vt+0x26C picks word1 (not flipped) or word2 (flipped); word3 = flip arg (only when flipped); bone = word4; ACMD handler moves the last ACMD param into word3

### Graphic_Effect7 `868F5AC3` (17 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x100008F x59, 0x100000A x12, 0x1000090 x11, 0x3040007 x9, 0x100008E x7 (n=127) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x114, 3 x4, 12 x2, 24 x2, 2 x1 (n=127) |
| 2 | X | H | offset from the bone, X | 0 x86, 2f x5, 0.5f x4, -2f x4, 7f x3 (n=127) |
| 3 | Y | H | offset from the bone, Y | 0 x29, 11f x9, 4f x9, 8f x9, 7f x9 (n=127) |
| 4 | Z | H | offset from the bone, Z | 0 x44, 15f x9, 10f x8, 3f x7, 5f x5 (n=127) |
| 5 | XRot | H | rotation (degrees) about X | 0 x98, -90f x4, -18f x3, 180f x2, 13f x1 (n=127) |
| 6 | YRot | H | rotation (degrees) about Y | 0 x93, -90f x10, 180f x2, -75f x2, 90f x2 (n=127) |
| 7 | ZRot | H | rotation (degrees) about Z | 0 x95, 90f x8, -120f x6, 10f x3, 180f x2 (n=127) |
| 8 | Size | H | uniform scale | 1f x20, 1.5f x16, 1.2f x16, 1.6f x14, 0.9f x9 (n=127) |
| 9 | RandomX | H | random offset range (+/-) on X | 0 x126, 4f x1 (n=127) |
| 10 | RandomY | H | random offset range (+/-) on Y | 0 x124, 5f x2, 4f x1 (n=127) |
| 11 | RandomZ | H | random offset range (+/-) on Z | 0 x127 (n=127) |
| 12 | RandomXRot | H | random rotation range (+/- degrees) about X | 0 x125, 20f x2 (n=127) |
| 13 | RandomYRot | H | random rotation range (+/- degrees) about Y | 0 x123, 360f x4 (n=127) |
| 14 | RandomZRot | H | random rotation range (+/- degrees) about Z | 0 x80, 360f x45, 20f x2 (n=127) |
| 15 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x106, 0 x21 (n=127) |
| 16 | Alpha | H | alpha in percent (handler divides by 100; 100 = opaque, >100 allowed) | 150f x22, 200f x22, 40f x16, 80f x13, 70f x12 (n=127) |

Evidence: EffectModule MSC handler 0x02C2CEC8 generic EFFECT path (0x02C2FA8C): words read as eff, bone, pos[3], rot[3], scale, rand pos[3], rand rot[3], terminate; request vt+0x4C / handler converts the last param (/100) into MSC op 0x272D word 17 -> EffectModule vt+0x28C (alpha); == EFFECT_ALPHA

### EFFECT_ATTR `D8D9A901` (17 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x32A0001 x2 (n=2) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x2 (n=2) |
| 2 | X | H | offset from the bone, X | 4f x1, 0 x1 (n=2) |
| 3 | Y | H | offset from the bone, Y | 22f x2 (n=2) |
| 4 | Z | H | offset from the bone, Z | 0 x2 (n=2) |
| 5 | XRot | H | rotation (degrees) about X | 0 x2 (n=2) |
| 6 | YRot | H | rotation (degrees) about Y | 0 x2 (n=2) |
| 7 | ZRot | H | rotation (degrees) about Z | 0 x2 (n=2) |
| 8 | Size | H | uniform scale | 0.6f x1, 0.8f x1 (n=2) |
| 9 | RandomX | H | random offset range (+/-) on X | 0 x2 (n=2) |
| 10 | RandomY | H | random offset range (+/-) on Y | 0 x2 (n=2) |
| 11 | RandomZ | H | random offset range (+/-) on Z | 0 x2 (n=2) |
| 12 | RandomXRot | H | random rotation range (+/- degrees) about X | 0 x2 (n=2) |
| 13 | RandomYRot | H | random rotation range (+/- degrees) about Y | 0 x2 (n=2) |
| 14 | RandomZRot | H | random rotation range (+/- degrees) about Z | 0 x2 (n=2) |
| 15 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x2 (n=2) |
| 16 | Attribute | M | attribute/group bits stored with the effect (request stack arg); matched by EFFECT_OFF / EFFECT_REMOVE_ATTR masks. Vanilla 0x8000 | 32768 x2 (n=2) |

Evidence: handler calls EffectModule vt+0x4C directly with the EFFECT layout / probe: p16 -> vt+0x4C first stack arg

### EFFECT_COLOR `30392B40` (19 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x338002A x8, 0x3380013 x4, 0x100000F x4, 0x100008E x3, 0x32A000D x3 (n=43) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x31, 3 x5, 1 x2, 24 x2, 10 x1 (n=43) |
| 2 | X | H | offset from the bone, X | 0 x27, 8f x4, -2f x4, 7f x4, 5f x2 (n=43) |
| 3 | Y | H | offset from the bone, Y | 0 x28, 0.5f x4, 10f x4, -3f x3, 6f x2 (n=43) |
| 4 | Z | H | offset from the bone, Z | 0 x31, 1f x5, 15f x4, 5f x1, 4f x1 (n=43) |
| 5 | XRot | H | rotation (degrees) about X | 0 x36, -90f x4, -140f x1, -50f x1, -15f x1 (n=43) |
| 6 | YRot | H | rotation (degrees) about Y | 0 x33, -90f x8, 170f x1, 90f x1 (n=43) |
| 7 | ZRot | H | rotation (degrees) about Z | 0 x40, 60f x1, -60f x1, 10f x1 (n=43) |
| 8 | Size | H | uniform scale | 1f x24, 1.1f x4, 0.8f x4, 1.3f x3, 0.9f x2 (n=43) |
| 9 | RandomX | H | random offset range (+/-) on X | 0 x43 (n=43) |
| 10 | RandomY | H | random offset range (+/-) on Y | 0 x43 (n=43) |
| 11 | RandomZ | H | random offset range (+/-) on Z | 0 x43 (n=43) |
| 12 | RandomXRot | H | random rotation range (+/- degrees) about X | 0 x43 (n=43) |
| 13 | RandomYRot | H | random rotation range (+/- degrees) about Y | 0 x43 (n=43) |
| 14 | RandomZRot | H | random rotation range (+/- degrees) about Z | 0 x43 (n=43) |
| 15 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x25, 0 x18 (n=43) |
| 16 | Red | H | red 0-255 (divided by 255, EffectModule set colour vt+0x27C) | 255f x14, 0 x4, 220f x4, 247f x3, 11f x2 (n=43) |
| 17 | Green | H | green 0-255 (divided by 255, EffectModule set colour vt+0x27C) | 192f x8, 144f x4, 0 x4, 178f x3, 247f x3 (n=43) |
| 18 | Blue | H | blue 0-255 (divided by 255, EffectModule set colour vt+0x27C) | 255f x13, 247f x8, 30f x6, 100f x4, 200f x3 (n=43) |

Evidence: EffectModule MSC handler 0x02C2CEC8 generic EFFECT path (0x02C2FA8C): words read as eff, bone, pos[3], rot[3], scale, rand pos[3], rand rot[3], terminate; request vt+0x4C / MSC 0x272C: words 17-19 / 255 -> vt+0x27C

### EFFECT_COLOR_WORK `E3C26DB5` (19 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x32A0006 x3 (n=3) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x3 (n=3) |
| 2 | X | H | offset from the bone, X | 0 x3 (n=3) |
| 3 | Y | H | offset from the bone, Y | 15f x3 (n=3) |
| 4 | Z | H | offset from the bone, Z | 0 x3 (n=3) |
| 5 | XRot | H | rotation (degrees) about X | 0 x3 (n=3) |
| 6 | YRot | H | rotation (degrees) about Y | 0 x3 (n=3) |
| 7 | ZRot | H | rotation (degrees) about Z | 0 x3 (n=3) |
| 8 | Size | H | uniform scale | 1f x3 (n=3) |
| 9 | RandomX | H | random offset range (+/-) on X | 0 x3 (n=3) |
| 10 | RandomY | H | random offset range (+/-) on Y | 0 x3 (n=3) |
| 11 | RandomZ | H | random offset range (+/-) on Z | 0 x3 (n=3) |
| 12 | RandomXRot | H | random rotation range (+/- degrees) about X | 0 x3 (n=3) |
| 13 | RandomYRot | H | random rotation range (+/- degrees) about Y | 0 x3 (n=3) |
| 14 | RandomZRot | H | random rotation range (+/- degrees) about Z | 0 x3 (n=3) |
| 15 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 0 x3 (n=3) |
| 16 | RedWork | H | float work variable id holding the red value (0-255) | 1 x3 (n=3) |
| 17 | GreenWork | H | float work variable id holding the green value (0-255) | 2 x3 (n=3) |
| 18 | BlueWork | H | float work variable id holding the blue value (0-255) | 3 x3 (n=3) |

Evidence: EffectModule MSC handler 0x02C2CEC8 generic EFFECT path (0x02C2FA8C): words read as eff, bone, pos[3], rot[3], scale, rand pos[3], rand rot[3], terminate; request vt+0x4C / handler reads p16-p18 with WorkModule get_float (vt+0x44) and passes the results to MSC 0x272C

### EFFECT_CONTINUAL `C81F667E` (4 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | no vanilla uses |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | no vanilla uses |
| 2 | Size | H | scale | no vanilla uses |
| 3 | Terminate | H | bool -> flag 0x4000 | no vanilla uses |

Evidence: handler -> EffectModule vt+0x6C (0x02C2B58C): r4 eff, r5 bone, f1 = p2, r6 = p3 ? 0x4000 : 0, slot -1 = first free

### EFFECT_CONTINUAL_OFF `6F2F2212` (1 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Slot | M | continual-effect slot index to stop (vt+0x74 clears slot[p0].active; EFFECT_CONTINUAL takes the first free slot, so the first one is 0) | no vanilla uses |

Evidence: EffectModule vt+0x74 (0x02C2B790)

### EFFECT_DETACH_KIND `29BC5960` (2 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x338002C x4, 0x337000B x4, 0x3370007 x4, 0x337000C x4, 0x3370008 x4 (n=50) |
| 1 | EndFadeFrames | M | -1 = only detach; >= 0 = also end the effects (stop emitting) with a light fade over this many frames | 0xFFFFFFFF x50 (n=50) |

Evidence: EffectModule vt+0xDC (0x02C2BDA4): if p1 >= 0 end the kind first (stop emitting, light fade p1 frames: 0x0334C6C0 -> 0x032F0310 -> 0x0334F308), then detach (0x0334C82C)

### EFFECT_DETACH_KIND_WORK `9FCB5AD5` (2 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GraphicWork | H | work int variable id holding the effect id (read with WorkModule get_int) | 0x10000098 x4, 0x10000099 x2 (n=6) |
| 1 | EndFadeFrames | M | as EFFECT_DETACH_KIND p1 (-1 in vanilla) | 0xFFFFFFFF x6 (n=6) |

Evidence: EffectModule vt+0xDC (0x02C2BDA4): if p1 >= 0 end the kind first (stop emitting, light fade p1 frames: 0x0334C6C0 -> 0x032F0310 -> 0x0334F308), then detach (0x0334C82C)

### EFFECT_FLIP `46596E40` (18 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GFXRight | H | effect id used when the motion is not flipped | 0x100008D x18, 0x100008F x17, 0x100008E x17, 0x1000010 x15, 0x4300000 x14 (n=144) |
| 1 | GFXLeft | H | effect id used when the motion is flipped (MotionModule is_flip) | 0x100008D x18, 0x100008F x17, 0x100008E x17, 0x1000010 x15, 0x4300000 x14 (n=144) |
| 2 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x114, 2 x11, 2001 x7, 17 x5, 24 x5 (n=144) |
| 3 | X | H | offset from the bone, X | 0 x92, -2f x12, 1f x10, -3f x4, 3f x4 (n=144) |
| 4 | Y | H | offset from the bone, Y | 0 x32, 3f x12, 6f x12, 7f x10, 4f x8 (n=144) |
| 5 | Z | H | offset from the bone, Z | 0 x49, -1f x11, 5f x9, 2f x7, 8f x6 (n=144) |
| 6 | XRot | H | rotation (degrees) about X | 0 x100, 180f x8, -10f x5, 30f x2, 10f x2 (n=144) |
| 7 | YRot | H | rotation (degrees) about Y | 0 x103, -2f x6, -60f x4, -10f x4, -140f x3 (n=144) |
| 8 | ZRot | H | rotation (degrees) about Z | 0 x114, 10f x5, -10f x3, 90f x3, 2f x2 (n=144) |
| 9 | Size | H | uniform scale | 1f x45, 1.2f x12, 0.8f x11, 0.9f x9, 1.5f x9 (n=144) |
| 10 | RandomX | H | random offset range (+/-) on X | 0 x131, 6f x4, 5f x3, 3f x3, 25f x1 (n=144) |
| 11 | RandomY | H | random offset range (+/-) on Y | 0 x128, 3f x6, 4f x5, 5f x3, 2f x1 (n=144) |
| 12 | RandomZ | H | random offset range (+/-) on Z | 0 x133, 6f x4, 5f x3, 25f x1, 4f x1 (n=144) |
| 13 | RandomXRot | H | random rotation range (+/- degrees) about X | 0 x144 (n=144) |
| 14 | RandomYRot | H | random rotation range (+/- degrees) about Y | 0 x136, 180f x8 (n=144) |
| 15 | RandomZRot | H | random rotation range (+/- degrees) about Z | 0 x139, 360f x5 (n=144) |
| 16 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x126, 0 x18 (n=144) |
| 17 | FlipType | M | EF_FLIP-style mirror mode, applied only when MotionModule is_flip (vt+0x26C) is true; passed to the request as the flip argument. Vanilla: 1 almost always (the usual mirror), 0 none, 3/4 rare | 1 x130, 0 x5, 3 x5, 4 x4 (n=144) |

Evidence: MSC 0x02C2FA8C / 0x02C3009C flip ops (0x2738-0x2742): MotionModule(+0x44) vt+0x26C picks word1 (not flipped) or word2 (flipped); word3 = flip arg (only when flipped); bone = word4; ACMD handler moves the last ACMD param into word3

### EFFECT_FLIP_ALPHA `46C4655C` (19 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GFXRight | H | effect id used when the motion is not flipped | 0x100008F x8, 0x1000090 x7, 0x100008E x5, 0x100008D x4, 0x3330003 x3 (n=33) |
| 1 | GFXLeft | H | effect id used when the motion is flipped (MotionModule is_flip) | 0x100008F x8, 0x1000090 x7, 0x100008E x5, 0x100008D x4, 0x3330003 x3 (n=33) |
| 2 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x30, 25 x3 (n=33) |
| 3 | X | H | offset from the bone, X | 0 x17, -6.5f x4, -8f x4, -0.5f x3, -1f x2 (n=33) |
| 4 | Y | H | offset from the bone, Y | 9f x6, 2f x5, 5.7f x4, 10f x4, 0 x3 (n=33) |
| 5 | Z | H | offset from the bone, Z | 0 x7, -2f x5, 2f x4, 3f x3, 9f x2 (n=33) |
| 6 | XRot | H | rotation (degrees) about X | 0 x23, 18.7f x2, -100f x2, 180f x2, 20f x2 (n=33) |
| 7 | YRot | H | rotation (degrees) about Y | 0 x12, 15f x3, 130f x3, -105.8f x2, -9f x2 (n=33) |
| 8 | ZRot | H | rotation (degrees) about Z | 0 x16, 90f x3, 5f x3, 2f x2, 18f x2 (n=33) |
| 9 | Size | H | uniform scale | 0.8f x9, 0.6f x3, 1f x3, 1.2f x3, 1.4f x3 (n=33) |
| 10 | RandomX | H | random offset range (+/-) on X | 0 x33 (n=33) |
| 11 | RandomY | H | random offset range (+/-) on Y | 0 x33 (n=33) |
| 12 | RandomZ | H | random offset range (+/-) on Z | 0 x33 (n=33) |
| 13 | RandomXRot | H | random rotation range (+/- degrees) about X | 0 x33 (n=33) |
| 14 | RandomYRot | H | random rotation range (+/- degrees) about Y | 0 x33 (n=33) |
| 15 | RandomZRot | H | random rotation range (+/- degrees) about Z | 0 x33 (n=33) |
| 16 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x33 (n=33) |
| 17 | FlipType | M | EF_FLIP-style mirror mode, applied only when MotionModule is_flip (vt+0x26C) is true; passed to the request as the flip argument. Vanilla: 1 almost always (the usual mirror), 0 none, 3/4 rare | 1 x29, 0 x4 (n=33) |
| 18 | Alpha | H | alpha in percent (handler divides by 100; 100 = opaque, >100 allowed) | 50f x8, 200f x8, 60f x4, 20f x4, 40f x3 (n=33) |

Evidence: MSC 0x02C2FA8C / 0x02C3009C flip ops (0x2738-0x2742): MotionModule(+0x44) vt+0x26C picks word1 (not flipped) or word2 (flipped); word3 = flip arg (only when flipped); bone = word4; ACMD handler moves the last ACMD param into word3 / MSC 0x273E alpha word (handler /100) -> vt+0x28C

### EFFECT_FLIP_COLOR `F07214DF` (21 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GFXRight | H | effect id used when the motion is not flipped | no vanilla uses |
| 1 | GFXLeft | H | effect id used when the motion is flipped (MotionModule is_flip) | no vanilla uses |
| 2 | Bone | H | bone id the effect is placed on (0 = top/root) | no vanilla uses |
| 3 | X | H | offset from the bone, X | no vanilla uses |
| 4 | Y | H | offset from the bone, Y | no vanilla uses |
| 5 | Z | H | offset from the bone, Z | no vanilla uses |
| 6 | XRot | H | rotation (degrees) about X | no vanilla uses |
| 7 | YRot | H | rotation (degrees) about Y | no vanilla uses |
| 8 | ZRot | H | rotation (degrees) about Z | no vanilla uses |
| 9 | Size | H | uniform scale | no vanilla uses |
| 10 | RandomX | H | random offset range (+/-) on X | no vanilla uses |
| 11 | RandomY | H | random offset range (+/-) on Y | no vanilla uses |
| 12 | RandomZ | H | random offset range (+/-) on Z | no vanilla uses |
| 13 | RandomXRot | H | random rotation range (+/- degrees) about X | no vanilla uses |
| 14 | RandomYRot | H | random rotation range (+/- degrees) about Y | no vanilla uses |
| 15 | RandomZRot | H | random rotation range (+/- degrees) about Z | no vanilla uses |
| 16 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | no vanilla uses |
| 17 | FlipType | M | EF_FLIP-style mirror mode, applied only when MotionModule is_flip (vt+0x26C) is true; passed to the request as the flip argument. Vanilla: 1 almost always (the usual mirror), 0 none, 3/4 rare | no vanilla uses |
| 18 | Red | H | red 0-255 (divided by 255, EffectModule set colour vt+0x27C) | no vanilla uses |
| 19 | Green | H | green 0-255 (divided by 255, EffectModule set colour vt+0x27C) | no vanilla uses |
| 20 | Blue | H | blue 0-255 (divided by 255, EffectModule set colour vt+0x27C) | no vanilla uses |

Evidence: MSC 0x02C2FA8C / 0x02C3009C flip ops (0x2738-0x2742): MotionModule(+0x44) vt+0x26C picks word1 (not flipped) or word2 (flipped); word3 = flip arg (only when flipped); bone = word4; ACMD handler moves the last ACMD param into word3 / MSC 0x273C: words 19-21 / 255 -> vt+0x27C (the command really has 21 params; acmd_info syntax lists 20)

### Graphic_Effect6 `54BA7357` (11 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x100008E x49, 0x100008D x40, 0x32B0005 x32, 0x1000023 x23, 0x1000090 x22 (n=297) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x221, 2 x32, 1000 x22, 1 x6, 1001 x5 (n=297) |
| 2 | X | H | offset from the bone, X | 0 x183, 1f x16, -2f x10, 3f x10, 4f x10 (n=297) |
| 3 | Y | H | offset from the bone, Y | 0 x67, 4.5f x21, 15f x21, 5f x19, 10f x18 (n=297) |
| 4 | Z | H | offset from the bone, Z | 0 x117, -1f x27, 1f x18, 3f x18, -3f x13 (n=297) |
| 5 | XRot | H | rotation (degrees) about X | 0 x189, 90f x17, 180f x12, -25f x6, -10f x6 (n=297) |
| 6 | YRot | H | rotation (degrees) about Y | 0 x135, -60f x14, -90f x13, -70f x9, 90f x9 (n=297) |
| 7 | ZRot | H | rotation (degrees) about Z | 0 x172, 90f x28, -90f x12, 270f x11, 180f x5 (n=297) |
| 8 | Size | H | uniform scale | 1f x111, 1.2f x27, 0.9f x21, 0.6f x18, 1.1f x17 (n=297) |
| 9 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x279, 0 x18 (n=297) |
| 10 | Alpha | H | alpha in percent (handler divides by 100; 100 = opaque, >100 allowed) | 70f x57, 40f x52, 30f x38, 60f x37, 50f x26 (n=297) |

Evidence: EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64 / MSC 0x272E (EFFECT_FOLLOW_ALPHA): last word = alpha (handler /100) -> vt+0x28C

### EFFECT_FOLLOW_COLOR `E20C02D4` (13 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x10000DD x38, 0x30F0003 x23, 0x4000000 x19, 0x3380007 x18, 0x3190004 x12 (n=267) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x134, 25 x37, 24 x15, 3 x14, 12 x13 (n=267) |
| 2 | X | H | offset from the bone, X | 0 x232, -2f x10, 1.5f x6, 2f x5, 10f x4 (n=267) |
| 3 | Y | H | offset from the bone, Y | 0 x115, 6f x25, 7f x16, 10f x12, 15f x11 (n=267) |
| 4 | Z | H | offset from the bone, Z | 0 x165, 30f x19, 3f x13, 1f x12, -0.5f x6 (n=267) |
| 5 | XRot | H | rotation (degrees) about X | 0 x237, -90f x10, 180f x9, -10f x3, 90f x3 (n=267) |
| 6 | YRot | H | rotation (degrees) about Y | 0 x240, 180f x8, -90f x4, -1e-05f x4, -60f x2 (n=267) |
| 7 | ZRot | H | rotation (degrees) about Z | 0 x242, -106f x10, 90f x6, 45f x4, -10f x2 (n=267) |
| 8 | Size | H | uniform scale | 1f x122, 1.2f x22, 0.6f x14, 2f x10, 1.6f x9 (n=267) |
| 9 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x253, 0 x14 (n=267) |
| 10 | Red | H | red 0-255 (divided by 255, EffectModule set colour vt+0x27C) | 255f x76, 100f x21, 240f x18, 510f x13, 15f x9 (n=267) |
| 11 | Green | H | green 0-255 (divided by 255, EffectModule set colour vt+0x27C) | 255f x41, 100f x26, 150f x19, 0 x12, 140f x11 (n=267) |
| 12 | Blue | H | blue 0-255 (divided by 255, EffectModule set colour vt+0x27C) | 255f x69, 200f x22, 150f x19, 220f x19, 30f x9 (n=267) |

Evidence: EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64 / MSC 0x2730 (follow): 3 words / 255 -> vt+0x27C; note sheet "Generate Colored Graphic Effect" 0x2730

### EFFECT_FOLLOW_FLIP `7EF50766` (12 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GFXRight | H | effect id used when the motion is not flipped | 0x100008D x100, 0x100008E x68, 0x1000045 x40, 0x1000090 x38, 0x1000023 x28 (n=513) |
| 1 | GFXLeft | H | effect id used when the motion is flipped (MotionModule is_flip) | 0x100008D x105, 0x100008E x67, 0x1000045 x40, 0x1000090 x39, 0x1000023 x28 (n=513) |
| 2 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x438, 2 x27, 24 x23, 25 x11, 17 x7 (n=513) |
| 3 | X | H | offset from the bone, X | 0 x301, -3f x31, -1f x29, -2f x19, 3f x17 (n=513) |
| 4 | Y | H | offset from the bone, Y | 0 x56, 7f x44, 3f x42, 5f x40, 6f x39 (n=513) |
| 5 | Z | H | offset from the bone, Z | 0 x168, 3f x29, 1f x28, 2f x24, 9f x24 (n=513) |
| 6 | XRot | H | rotation (degrees) about X | 0 x308, 180f x52, -90f x20, -20f x8, 30f x7 (n=513) |
| 7 | YRot | H | rotation (degrees) about Y | 0 x216, 180f x52, 90f x24, -10f x19, 10f x17 (n=513) |
| 8 | ZRot | H | rotation (degrees) about Z | 0 x360, 90f x21, 10f x12, -10f x11, 180f x7 (n=513) |
| 9 | Size | H | uniform scale | 1f x138, 0.9f x47, 1.5f x35, 1.2f x32, 1.3f x25 (n=513) |
| 10 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x502, 0 x11 (n=513) |
| 11 | FlipType | M | EF_FLIP-style mirror mode, applied only when MotionModule is_flip (vt+0x26C) is true; passed to the request as the flip argument. Vanilla: 1 almost always (the usual mirror), 0 none, 3/4 rare | 1 x463, 0 x33, 3 x15, 4 x2 (n=513) |

Evidence: handler inlines the flip follow: MotionModule vt+0x26C, EffectModule vt+0x64(eff, p2 bone, pos p3-5, rot p6-8, f1 = p9), terminate p10, flip arg p11

### EFFECT_FOLLOW_FLIP_ALPHA `2ED684DE` (13 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GFXRight | H | effect id used when the motion is not flipped | 0x100008E x23, 0x1000023 x11, 0x334000A x10, 0x1000090 x6, 0x30F0002 x4 (n=74) |
| 1 | GFXLeft | H | effect id used when the motion is flipped (MotionModule is_flip) | 0x100008E x23, 0x1000023 x11, 0x334000A x10, 0x1000090 x6, 0x30F0002 x4 (n=74) |
| 2 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x60, 2 x12, 1 x2 (n=74) |
| 3 | X | H | offset from the bone, X | 0 x54, 1f x7, -7f x2, -2f x2, -3.5f x2 (n=74) |
| 4 | Y | H | offset from the bone, Y | 10f x10, 18.5f x8, 8f x6, 5f x6, 11f x5 (n=74) |
| 5 | Z | H | offset from the bone, Z | 0 x24, 3f x8, 7f x4, -8f x4, 2.5f x3 (n=74) |
| 6 | XRot | H | rotation (degrees) about X | 0 x34, 180f x5, 10f x4, -95f x4, -85f x4 (n=74) |
| 7 | YRot | H | rotation (degrees) about Y | 0 x25, -90f x8, 10f x7, -60f x5, -10f x4 (n=74) |
| 8 | ZRot | H | rotation (degrees) about Z | 0 x27, 90f x8, -5f x5, 40f x3, 10f x3 (n=74) |
| 9 | Size | H | uniform scale | 1.1f x13, 1f x10, 0.8f x9, 1.5f x9, 1.35f x6 (n=74) |
| 10 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x74 (n=74) |
| 11 | FlipType | M | EF_FLIP-style mirror mode, applied only when MotionModule is_flip (vt+0x26C) is true; passed to the request as the flip argument. Vanilla: 1 almost always (the usual mirror), 0 none, 3/4 rare | 1 x60, 0 x8, 3 x6 (n=74) |
| 12 | Alpha | H | alpha in percent (handler divides by 100; 100 = opaque, >100 allowed) | 60f x28, 40f x12, 50f x11, 70f x8, 15f x2 (n=74) |

Evidence: MSC 0x02C2FA8C / 0x02C3009C flip ops (0x2738-0x2742): MotionModule(+0x44) vt+0x26C picks word1 (not flipped) or word2 (flipped); word3 = flip arg (only when flipped); bone = word4; ACMD handler moves the last ACMD param into word3 / MSC 0x273F alpha word

### EFFECT_FOLLOW_FLIP_COLOR `9860F55D` (15 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GFXRight | H | effect id used when the motion is not flipped | 0x1000023 x17, 0x1000092 x7, 0x100008D x2, 0x100008E x2 (n=28) |
| 1 | GFXLeft | H | effect id used when the motion is flipped (MotionModule is_flip) | 0x1000023 x17, 0x1000092 x7, 0x100008D x2, 0x100008E x2 (n=28) |
| 2 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x19, 2 x9 (n=28) |
| 3 | X | H | offset from the bone, X | 0 x27, -1.5f x1 (n=28) |
| 4 | Y | H | offset from the bone, Y | 8f x5, 7f x4, 1f x4, 10f x4, -3f x3 (n=28) |
| 5 | Z | H | offset from the bone, Z | 0 x16, 3f x4, 4f x2, 1f x2, -6f x1 (n=28) |
| 6 | XRot | H | rotation (degrees) about X | 0 x21, 180f x3, -18f x1, 20f x1, -20f x1 (n=28) |
| 7 | YRot | H | rotation (degrees) about Y | 0 x16, -90f x8, 180f x2, -50f x1, 40f x1 (n=28) |
| 8 | ZRot | H | rotation (degrees) about Z | 0 x26, 200f x1, -40f x1 (n=28) |
| 9 | Size | H | uniform scale | 1.5f x14, 1f x7, 1.2f x4, 1.1f x1, 0.7f x1 (n=28) |
| 10 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x28 (n=28) |
| 11 | FlipType | M | EF_FLIP-style mirror mode, applied only when MotionModule is_flip (vt+0x26C) is true; passed to the request as the flip argument. Vanilla: 1 almost always (the usual mirror), 0 none, 3/4 rare | 1 x28 (n=28) |
| 12 | Red | H | red 0-255 (divided by 255, EffectModule set colour vt+0x27C) | 100f x17, 255f x9, 127f x2 (n=28) |
| 13 | Green | H | green 0-255 (divided by 255, EffectModule set colour vt+0x27C) | 180f x17, 240f x9, 178f x2 (n=28) |
| 14 | Blue | H | blue 0-255 (divided by 255, EffectModule set colour vt+0x27C) | 255f x17, 100f x9, 510f x2 (n=28) |

Evidence: MSC 0x02C2FA8C / 0x02C3009C flip ops (0x2738-0x2742): MotionModule(+0x44) vt+0x26C picks word1 (not flipped) or word2 (flipped); word3 = flip arg (only when flipped); bone = word4; ACMD handler moves the last ACMD param into word3 / MSC 0x273D colour words

### EFFECT_FOLLOW_FLIP_RND `072D2AAD` (18 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GFXRight | H | effect id used when the motion is not flipped | 0x1000023 x4 (n=4) |
| 1 | GFXLeft | H | effect id used when the motion is flipped (MotionModule is_flip) | 0x1000023 x4 (n=4) |
| 2 | Bone | H | bone id the effect is placed on (0 = top/root) | 2 x4 (n=4) |
| 3 | X | H | offset from the bone, X | 0 x4 (n=4) |
| 4 | Y | H | offset from the bone, Y | 0 x1, -9f x1, -6f x1, -3f x1 (n=4) |
| 5 | Z | H | offset from the bone, Z | 0 x4 (n=4) |
| 6 | XRot | H | rotation (degrees) about X | 0 x4 (n=4) |
| 7 | YRot | H | rotation (degrees) about Y | 0 x2, 110f x1, 40f x1 (n=4) |
| 8 | ZRot | H | rotation (degrees) about Z | 0 x4 (n=4) |
| 9 | Size | H | uniform scale | 0.8f x1, 0.3f x1, 0.5f x1, 0.7f x1 (n=4) |
| 10 | RandomX | H | random offset range (+/-) on X | 1f x4 (n=4) |
| 11 | RandomY | H | random offset range (+/-) on Y | 1f x4 (n=4) |
| 12 | RandomZ | H | random offset range (+/-) on Z | 1f x4 (n=4) |
| 13 | RandomXRot | H | random rotation range (+/- degrees) about X | 0 x4 (n=4) |
| 14 | RandomYRot | H | random rotation range (+/- degrees) about Y | 90f x4 (n=4) |
| 15 | RandomZRot | H | random rotation range (+/- degrees) about Z | 0 x4 (n=4) |
| 16 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x4 (n=4) |
| 17 | FlipType | M | EF_FLIP-style mirror mode, applied only when MotionModule is_flip (vt+0x26C) is true; passed to the request as the flip argument. Vanilla: 1 almost always (the usual mirror), 0 none, 3/4 rare | 1 x4 (n=4) |

Evidence: EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64 / EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64 (0x272F/0x273B random block) / MSC 0x02C2FA8C / 0x02C3009C flip ops (0x2738-0x2742): MotionModule(+0x44) vt+0x26C picks word1 (not flipped) or word2 (flipped); word3 = flip arg (only when flipped); bone = word4; ACMD handler moves the last ACMD param into word3

### EFFECT_FOLLOW_LIGHT `EF4016CA` (17 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x3060009 x6, 0x3040005 x4, 0x3060003 x2, 0x10000A4 x1, 0x1000022 x1 (n=14) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 2 x6, 0 x5, 22 x3 (n=14) |
| 2 | X | H | offset from the bone, X | 0 x11, 7.98004f x2, 8f x1 (n=14) |
| 3 | Y | H | offset from the bone, Y | 0 x11, -0.50584f x2, -0.5f x1 (n=14) |
| 4 | Z | H | offset from the bone, Z | 0 x6, 15f x2, 5f x2, -0.25092f x2, -0.25f x1 (n=14) |
| 5 | XRot | H | rotation (degrees) about X | 0 x11, -91.2728f x2, -90f x1 (n=14) |
| 6 | YRot | H | rotation (degrees) about Y | 0 x11, -1.7974f x2, -1.7f x1 (n=14) |
| 7 | ZRot | H | rotation (degrees) about Z | 0 x11, 176.373f x2, 176f x1 (n=14) |
| 8 | Size | H | uniform scale | 1f x10, 0.6f x2, 0.35f x1, 0.9f x1 (n=14) |
| 9 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x13, 0 x1 (n=14) |
| 10 | Red | H | light red 0-255 (/255) | 120f x9, 80f x4, 180f x1 (n=14) |
| 11 | Green | H | light green 0-255 | 120f x9, 50f x4, 74f x1 (n=14) |
| 12 | Blue | H | light blue 0-255 | 120f x9, 50f x4, 59f x1 (n=14) |
| 13 | LightIntensity | M | light intensity (stored at +0x40; EFFECT_LIGHT_END fades it to 0) | 20f x8, 16f x6 (n=14) |
| 14 | LightX | M | light offset X (mirrored by facing, PostureModule vt+0x74) | 1f x10, 0 x4 (n=14) |
| 15 | LightY | M | light offset Y | 1f x10, 0 x4 (n=14) |
| 16 | LightZ | M | light offset Z | 0 x14 (n=14) |

Evidence: handler -> EffectModule vt+0x25C (0x02C2CB08) -> 0x0334FD7C: colour (/255) -> light vt+0x84, intensity -> vt+0x8C (faded by EFFECT_LIGHT_END), offset -> effect+0x120 / handler: EffectModule vt+0x64 (follow) then vt+0x25C light

### EFFECT_FOLLOW_NO_STOP_FLIP `61A23DF6` (12 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GFXRight | H | effect id used when the motion is not flipped | 0x33E0001 x11, 0x300001B x11, 0x33E0002 x9, 0x300001C x9, 0x33E0004 x5 (n=65) |
| 1 | GFXLeft | H | effect id used when the motion is flipped (MotionModule is_flip) | 0x33E0001 x11, 0x300001B x11, 0x33E0002 x9, 0x300001C x9, 0x33E0004 x5 (n=65) |
| 2 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x65 (n=65) |
| 3 | X | H | offset from the bone, X | 0 x33, 1f x10, -1f x8, -6.5f x2, -1.5f x2 (n=65) |
| 4 | Y | H | offset from the bone, Y | 7f x14, 6f x11, 5f x6, 8f x5, 6.5f x4 (n=65) |
| 5 | Z | H | offset from the bone, Z | 0 x12, -2f x6, 3f x5, -7f x4, -1f x4 (n=65) |
| 6 | XRot | H | rotation (degrees) about X | 0 x10, 180f x5, -5f x4, -4f x4, -58f x4 (n=65) |
| 7 | YRot | H | rotation (degrees) about Y | 0 x19, 5f x8, -55f x4, 20f x2, -35f x2 (n=65) |
| 8 | ZRot | H | rotation (degrees) about Z | 0 x35, 82f x4, 20f x3, 34f x2, 212.014f x2 (n=65) |
| 9 | Size | H | uniform scale | 0.9f x18, 1f x14, 0.7f x8, 0.95f x6, 1.1f x6 (n=65) |
| 10 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x65 (n=65) |
| 11 | FlipType | M | EF_FLIP-style mirror mode, applied only when MotionModule is_flip (vt+0x26C) is true; passed to the request as the flip argument. Vanilla: 1 almost always (the usual mirror), 0 none, 3/4 rare | 1 x65 (n=65) |

Evidence: MSC 0x2740: flip follow without the 0x8000 (stop-in-hitlag) flag

### EFFECT_FOLLOW_NO_STOP_SLOW_ALL `99CC9AF2` (10 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | no vanilla uses |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | no vanilla uses |
| 2 | X | H | offset from the bone, X | no vanilla uses |
| 3 | Y | H | offset from the bone, Y | no vanilla uses |
| 4 | Z | H | offset from the bone, Z | no vanilla uses |
| 5 | XRot | H | rotation (degrees) about X | no vanilla uses |
| 6 | YRot | H | rotation (degrees) about Y | no vanilla uses |
| 7 | ZRot | H | rotation (degrees) about Z | no vanilla uses |
| 8 | Size | H | uniform scale | no vanilla uses |
| 9 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | no vanilla uses |

Evidence: handler calls EffectModule vt+0x64 directly (no 0x8000 flag, extra stack flag = 1 -> "slow all")

### EFFECT_FOLLOW_NO_STOP_WITH_HANDLE `D5FC182B` (13 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x337000B x4, 0x337000C x4, 0x3370007 x4, 0x3370008 x4, 0x337000A x4 (n=32) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x32 (n=32) |
| 2 | X | H | offset from the bone, X | 0 x32 (n=32) |
| 3 | Y | H | offset from the bone, Y | 10f x16, 11f x16 (n=32) |
| 4 | Z | H | offset from the bone, Z | 17f x32 (n=32) |
| 5 | XRot | H | rotation (degrees) about X | 0 x32 (n=32) |
| 6 | YRot | H | rotation (degrees) about Y | 100f x16, -100f x16 (n=32) |
| 7 | ZRot | H | rotation (degrees) about Z | 0 x32 (n=32) |
| 8 | Size | H | uniform scale | 1f x16, 1.15f x16 (n=32) |
| 9 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x32 (n=32) |
| 10 | GraphicOffset | M | added to the effect id before the request (selects a neighbouring effect entry); 0 in vanilla | 0 x32 (n=32) |
| 11 | MaterialAnim | M | effect material animation: loads "%02d.mta" with this value + 1 (-1 = none); Cloud uses 0/1 | 0 x16, 1 x16 (n=32) |
| 12 | HandleWork | H | work int variable id that receives the new effect handle (WorkModule set_int) | 0x10000085 x24, 0x10000086 x8 (n=32) |

Evidence: EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64 / EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64; 0x271A: after terminate two optional words: index offset (added to the effect id in vt+0x64) and material anim (stack arg -> "%02d.mta" index+1, -1 = none) / EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64; 0x271A: after terminate two optional words: index offset (added to the effect id in vt+0x64) and material anim (stack arg -> "%02d.mta" index+1, -1 = none); 0x0334FF08 / handler WorkModule set_int(handle, p12)

### EFFECT_FOLLOW_RND_WORK `F10FD85A` (16 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GraphicWork | H | work int variable id holding the effect id (read with WorkModule get_int) | 0x10000092 x6 (n=6) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x6 (n=6) |
| 2 | X | H | offset from the bone, X | 0 x6 (n=6) |
| 3 | Y | H | offset from the bone, Y | 10f x4, 13.8f x1, 14.2f x1 (n=6) |
| 4 | Z | H | offset from the bone, Z | 0 x2, -2f x2, 2f x2 (n=6) |
| 5 | XRot | H | rotation (degrees) about X | 180f x4, 0 x2 (n=6) |
| 6 | YRot | H | rotation (degrees) about Y | 0 x2, 180f x2, 90f x1, -90f x1 (n=6) |
| 7 | ZRot | H | rotation (degrees) about Z | -90f x2, -3f x2, 3f x2 (n=6) |
| 8 | Size | H | uniform scale | 1.2f x4, 1.1f x2 (n=6) |
| 9 | RandomX | H | random offset range (+/-) on X | 3f x4, 0 x2 (n=6) |
| 10 | RandomY | H | random offset range (+/-) on Y | 1f x4, 2f x2 (n=6) |
| 11 | RandomZ | H | random offset range (+/-) on Z | 3f x6 (n=6) |
| 12 | RandomXRot | H | random rotation range (+/- degrees) about X | 1f x4, 10f x2 (n=6) |
| 13 | RandomYRot | H | random rotation range (+/- degrees) about Y | 10f x4, 50f x2 (n=6) |
| 14 | RandomZRot | H | random rotation range (+/- degrees) about Z | 5f x4, 20f x2 (n=6) |
| 15 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x6 (n=6) |

Evidence: EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64 / EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64 (0x272F random block) / handler get_int(p0) -> MSC 0x272F word 1

### EFFECT_FOLLOW_STR `59829B55` (10 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | no vanilla uses |
| 1 | BoneNameHash | H | CRC32 of a bone name; only "ThrowN" (0xFC38B062) and "TopN" (0x98FBDE95) resolve, anything else -> bone 0 | no vanilla uses |
| 2 | X | H | offset from the bone, X | no vanilla uses |
| 3 | Y | H | offset from the bone, Y | no vanilla uses |
| 4 | Z | H | offset from the bone, Z | no vanilla uses |
| 5 | XRot | H | rotation (degrees) about X | no vanilla uses |
| 6 | YRot | H | rotation (degrees) about Y | no vanilla uses |
| 7 | ZRot | H | rotation (degrees) about Z | no vanilla uses |
| 8 | Size | H | uniform scale | no vanilla uses |
| 9 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | no vanilla uses |

Evidence: handler 0x02BEBD98: p1 -> 0x02BEBC34 (table of 2 bone-name CRC32s: 0xFC38B062 "ThrowN", 0x98FBDE95 "TopN") -> bone id by name, then EffectModule vt+0x64

### EFFECT_FOLLOW_STRENGTH `ED85CA70` (12 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | no vanilla uses |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | no vanilla uses |
| 2 | X | H | offset from the bone, X | no vanilla uses |
| 3 | Y | H | offset from the bone, Y | no vanilla uses |
| 4 | Z | H | offset from the bone, Z | no vanilla uses |
| 5 | XRot | H | rotation (degrees) about X | no vanilla uses |
| 6 | YRot | H | rotation (degrees) about Y | no vanilla uses |
| 7 | ZRot | H | rotation (degrees) about Z | no vanilla uses |
| 8 | Size | H | uniform scale | no vanilla uses |
| 9 | Strength | M | strength value; when non-zero the size becomes Size + Strength*SizePerStrength | no vanilla uses |
| 10 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | no vanilla uses |
| 11 | SizePerStrength | M | size added per unit of Strength | no vanilla uses |

Evidence: EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64 / EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64; 0x2718: extra word before terminate (strength) and after it (size per strength); size += strength*rate when strength != 0

### EFFECT_FOLLOW_SYNC_PARENT `4261788B` (11 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x337000D x4 (n=4) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x4 (n=4) |
| 2 | X | H | offset from the bone, X | 0 x4 (n=4) |
| 3 | Y | H | offset from the bone, Y | 10f x4 (n=4) |
| 4 | Z | H | offset from the bone, Z | 17f x4 (n=4) |
| 5 | XRot | H | rotation (degrees) about X | 0 x4 (n=4) |
| 6 | YRot | H | rotation (degrees) about Y | 0 x4 (n=4) |
| 7 | ZRot | H | rotation (degrees) about Z | 0 x4 (n=4) |
| 8 | Size | H | uniform scale | 1f x4 (n=4) |
| 9 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x4 (n=4) |
| 10 | ParentHandleWork | H | work int variable id holding the parent effect handle; the effect is only made if the parent exists and is synced to it | 0x10000086 x4 (n=4) |

Evidence: EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64 / handler 0x02BE4EF4: parent = get_int(p10); if EffectModule vt+0x15C(parent) (exists): MSC 0x2712 follow with p0-p9, then vt+0x354(new, parent)

### EFFECT_FOLLOW_UNSYNC_VIS_WHOLE `FC4BE069` (10 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x3170016 x2 (n=2) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x2 (n=2) |
| 2 | X | H | offset from the bone, X | 0 x2 (n=2) |
| 3 | Y | H | offset from the bone, Y | 7f x2 (n=2) |
| 4 | Z | H | offset from the bone, Z | 0 x2 (n=2) |
| 5 | XRot | H | rotation (degrees) about X | 0 x2 (n=2) |
| 6 | YRot | H | rotation (degrees) about Y | -90f x2 (n=2) |
| 7 | ZRot | H | rotation (degrees) about Z | 0 x2 (n=2) |
| 8 | Size | H | uniform scale | 0.7f x2 (n=2) |
| 9 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x2 (n=2) |

Evidence: EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64; 0x2713 adds flag 0x400000 (visibility not synced with the whole model)

### EFFECT_FOLLOW_WITH_HANDLE `1D9C1ECE` (11 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | no vanilla uses |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | no vanilla uses |
| 2 | X | H | offset from the bone, X | no vanilla uses |
| 3 | Y | H | offset from the bone, Y | no vanilla uses |
| 4 | Z | H | offset from the bone, Z | no vanilla uses |
| 5 | XRot | H | rotation (degrees) about X | no vanilla uses |
| 6 | YRot | H | rotation (degrees) about Y | no vanilla uses |
| 7 | ZRot | H | rotation (degrees) about Z | no vanilla uses |
| 8 | Size | H | uniform scale | no vanilla uses |
| 9 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | no vanilla uses |
| 10 | HandleWork | H | work int variable id that receives the new effect handle (WorkModule set_int) | no vanilla uses |

Evidence: EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64 / handler: MSC 0x2712 via vt+0x2FC (returns handle), WorkModule set_int(handle, p10)

### EFFECT_FOLLOW_WORK `B7458BB3` (10 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GraphicWork | H | work int variable id holding the effect id (read with WorkModule get_int) | 0x10000088 x53, 0x10000092 x23, 0x10000083 x8, 0x10000099 x3, 0x10000089 x3 (n=101) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 25 x66, 0 x32, 1 x2, 22 x1 (n=101) |
| 2 | X | H | offset from the bone, X | 0 x88, 1f x3, 2f x3, -1f x2, 5f x1 (n=101) |
| 3 | Y | H | offset from the bone, Y | 0 x67, 30f x5, 10f x4, 14f x3, 4f x3 (n=101) |
| 4 | Z | H | offset from the bone, Z | 0 x84, 2f x5, -2f x4, 1.5f x2, 1f x2 (n=101) |
| 5 | XRot | H | rotation (degrees) about X | 0 x86, 2f x3, -5f x2, 20f x1, -65f x1 (n=101) |
| 6 | YRot | H | rotation (degrees) about Y | 0 x75, -10f x4, 20f x4, 200f x3, 180f x2 (n=101) |
| 7 | ZRot | H | rotation (degrees) about Z | 0 x76, 177f x3, 183f x3, 175f x3, 190f x2 (n=101) |
| 8 | Size | H | uniform scale | 1f x79, 1.1f x11, 1.2f x7, 0.9f x2, 1.05f x1 (n=101) |
| 9 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x100, 0 x1 (n=101) |

Evidence: EffectModule MSC follow path 0x02C3009C: eff, bone, pos[3], rot[3], scale (word base+7), [extras], terminate -> flag 0x4000; request vt+0x64 / handler get_int(p0) -> MSC 0x2712 word 1

### EFFECT_GLOBAL `7C37DF64` (8 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x4370000 x1, 0x4170002 x1, 0x4170001 x1, 0x42F000B x1 (n=4) |
| 1 | X | M | global/screen position X (vanilla 960, -540: screen-space style coordinates for Final Smash effects) | 960f x4 (n=4) |
| 2 | Y | M | global/screen position Y | -540f x3, -120f x1 (n=4) |
| 3 | Z | M | global/screen position Z | 0 x4 (n=4) |
| 4 | XRot | H | rotation (degrees) about X | 0 x4 (n=4) |
| 5 | YRot | H | rotation (degrees) about Y | 0 x4 (n=4) |
| 6 | ZRot | H | rotation (degrees) about Z | 0 x4 (n=4) |
| 7 | Size | H | uniform scale | 1f x2, 17f x2 (n=4) |

Evidence: handler -> EffectModule vt+0x44 (0x02C29D10): r4 eff, r5 &pos(p1-3), r6 &rot(p4-6), f1 = p7, no bone

### EFFECT_GLOBAL_FOLLOW `CF86D9CB` (8 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | no vanilla uses |
| 1 | X | M | global position X | no vanilla uses |
| 2 | Y | M | global position Y | no vanilla uses |
| 3 | Z | M | global position Z | no vanilla uses |
| 4 | XRot | H | rotation (degrees) about X | no vanilla uses |
| 5 | YRot | H | rotation (degrees) about Y | no vanilla uses |
| 6 | ZRot | H | rotation (degrees) about Z | no vanilla uses |
| 7 | Size | H | uniform scale | no vanilla uses |

Evidence: handler -> EffectModule vt+0x44 (0x02C29D10): r4 eff, r5 &pos(p1-3), r6 &rot(p4-6), f1 = p7, no bone / handler -> EffectModule vt+0x44 (0x02C29D10): r4 eff, r5 &pos(p1-3), r6 &rot(p4-6), f1 = p7, no bone with follow flag 0x10000

### EFFECT_LIGHT `3D753F5E` (23 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x100000A x1 (n=1) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x1 (n=1) |
| 2 | X | H | offset from the bone, X | 0 x1 (n=1) |
| 3 | Y | H | offset from the bone, Y | 0 x1 (n=1) |
| 4 | Z | H | offset from the bone, Z | 0 x1 (n=1) |
| 5 | XRot | H | rotation (degrees) about X | 0 x1 (n=1) |
| 6 | YRot | H | rotation (degrees) about Y | 0 x1 (n=1) |
| 7 | ZRot | H | rotation (degrees) about Z | 0 x1 (n=1) |
| 8 | Size | H | uniform scale | 1f x1 (n=1) |
| 9 | RandomX | H | random offset range (+/-) on X | 0 x1 (n=1) |
| 10 | RandomY | H | random offset range (+/-) on Y | 0 x1 (n=1) |
| 11 | RandomZ | H | random offset range (+/-) on Z | 0 x1 (n=1) |
| 12 | RandomXRot | H | random rotation range (+/- degrees) about X | 0 x1 (n=1) |
| 13 | RandomYRot | H | random rotation range (+/- degrees) about Y | 0 x1 (n=1) |
| 14 | RandomZRot | H | random rotation range (+/- degrees) about Z | 0 x1 (n=1) |
| 15 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 0 x1 (n=1) |
| 16 | Red | H | light red 0-255 (/255) | 0 x1 (n=1) |
| 17 | Green | H | light green 0-255 | 255f x1 (n=1) |
| 18 | Blue | H | light blue 0-255 | 0 x1 (n=1) |
| 19 | LightIntensity | M | light intensity (stored at +0x40; EFFECT_LIGHT_END fades it to 0) | 5f x1 (n=1) |
| 20 | LightX | M | light offset X (mirrored by facing, PostureModule vt+0x74) | 2f x1 (n=1) |
| 21 | LightY | M | light offset Y | 1f x1 (n=1) |
| 22 | LightZ | M | light offset Z | 0 x1 (n=1) |

Evidence: handler -> EffectModule vt+0x25C (0x02C2CB08) -> 0x0334FD7C: colour (/255) -> light vt+0x84, intensity -> vt+0x8C (faded by EFFECT_LIGHT_END), offset -> effect+0x120 / handler: EffectModule vt+0x4C (EFFECT layout) then vt+0x25C light

### EFFECT_LIGHT_END `D5F5735F` (2 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | FadeFrames | H | frames to fade the effect light(s) out | 3 x6, 20 x4, 10 x1 (n=11) |
| 1 | AttrMask | M | attribute/group bits selecting the lights (vanilla 0x10000) | 0x10000 x11 (n=11) |

Evidence: EffectModule vt+0x264 (0x02C2CB14) -> 0x032F0D84: for lights whose attribute bits match p1, fade rate = intensity / p0

### EFFECT_OFF `5A3B874D` (2 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | AttrMask | M | attribute/group bits of the effects to end (vanilla 0x10000, 0x20000, 0x4000) | 0x10000 x3, 0x20000 x3, 16384 x2 (n=8) |
| 1 | KillParticles | M | bool: 1 = remove live particles and delete at once; 0 = stop emitting and let particles finish | 0 x5, 1 x3 (n=8) |

Evidence: handler 0x02BE0104 -> EffectModule vt+0xCC (kill by attribute) with bool2 = 1 -> 0x032F0454 -> per-effect 0x0334F308

### Terminate_Graphic_Effect `E8F38CA3` (3 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x100008D x74, 0x100008E x57, 0x317000C x49, 0x3360009 x36, 0x32F001B x33 (n=1413) |
| 1 | KillParticles | M | bool: remove live particles now (else stop emitting and let them die out) | 0 x945, 1 x468 (n=1413) |
| 2 | KillImmediately | M | bool: end the attached light immediately; with KillParticles the effect is deleted at once | 0 x869, 1 x544 (n=1413) |

Evidence: MSC 0x2723 (0x02C30D08) -> EffectModule vt+0xC4 kill kind(eff, b1, b2) -> 0x0334F308: b1 kills emitter sets now (0x04A55714) instead of fading (0x04A4B25C); b2 also ends the light at once; b1&&b2 delete the effect immediately

### EFFECT_OFF_KIND_WORK `89D3AD87` (3 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GraphicWork | H | work int variable id holding the effect id (read with WorkModule get_int) | 0x10000088 x51, 0x10000083 x5, 0x10000089 x4, 0x1000008A x2, 0x10000092 x1 (n=64) |
| 1 | KillParticles | M | as Terminate_Graphic_Effect p1 | 1 x58, 0 x6 (n=64) |
| 2 | KillImmediately | M | as Terminate_Graphic_Effect p2 | 1 x58, 0 x6 (n=64) |

Evidence: MSC 0x2723 (0x02C30D08) -> EffectModule vt+0xC4 kill kind(eff, b1, b2) -> 0x0334F308: b1 kills emitter sets now (0x04A55714) instead of fading (0x04A4B25C); b2 also ends the light at once; b1&&b2 delete the effect immediately

### EFFECT_REMOVE_ATTR `CCD48E8A` (1 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | AttrMask | M | attribute/group bits of the effects to remove (vt+0xB4 -> 0x0334C6C0); vanilla 0x20000 | 0x20000 x2 (n=2) |

Evidence: EffectModule vt+0xB4 (0x02005ABC)

### EFFECT_REMOVE_COMMON `0CA3C450` (1 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | CommonEffectId | L | id of a queued "common" effect entry to remove (MSC op 0x20 -> EffectModule vt+0x1E4); vanilla 37 | 37 x1 (n=1) |

Evidence: MSC 0x02C2EAF0 -> vt+0x1E4 (0x02C2C790) searches the +0x54 queue for this id

### EFFECT_REMOVE_LINE_CIRCLE `C31ABACD` (2 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | FadeFrames | M | > 0: fade the active line circle out over this many frames (0x03301A20); <= 0: remove at once | 6 x2, 10 x1, 8 x1, 4 x1 (n=5) |
| 1 | FadeFlag | L | bool passed with the fade (only used when FadeFrames > 0); 1 in vanilla | 1 x5 (n=5) |

Evidence: MSC 0x2733 / MSC 0x2733 (0x02C311B8)

### EFFECT_REQ_LINE_CIRCLE `36FA6671` (4 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Preset | M | line-circle preset index (x0x84 into the module table); 0 in vanilla | no vanilla uses |
| 1 | Bone | M | bone id the effect is placed on (0 = top/root) | no vanilla uses |
| 2 | SizeA | L | circle size parameter 1 (+0x50; equal to SizeB in vanilla) | no vanilla uses |
| 3 | SizeB | L | circle size parameter 2 (+0x54) | no vanilla uses |

Evidence: MSC 0x2732 (0x02C30F98): word1 * 0x84 -> line-circle preset, word2 bone (+0x3C module vt+0xF4 bone position), words 3-4 two floats (+0x50/+0x54), words 5-7 offset; word 8 (bool) and 9 (table index) optional

### EFFECT_REQ_LINE_CIRCLE_OFFSET `13B7328C` (7 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Preset | M | line-circle preset index (x0x84 into the module table); 0 in vanilla | 0 x3 (n=3) |
| 1 | Bone | M | bone id the effect is placed on (0 = top/root) | 0 x3 (n=3) |
| 2 | SizeA | L | circle size parameter 1 (+0x50; equal to SizeB in vanilla) | 10f x2, 6f x1 (n=3) |
| 3 | SizeB | L | circle size parameter 2 (+0x54) | 10f x2, 6f x1 (n=3) |
| 4 | X | M | offset from the bone, X | 0 x3 (n=3) |
| 5 | Y | M | offset from the bone, Y | 5f x1, 15f x1, 18f x1 (n=3) |
| 6 | Z | M | offset from the bone, Z | 50f x1, 500f x1, -5f x1 (n=3) |

Evidence: MSC 0x2732 (0x02C30F98): word1 * 0x84 -> line-circle preset, word2 bone (+0x3C module vt+0xF4 bone position), words 3-4 two floats (+0x50/+0x54), words 5-7 offset; word 8 (bool) and 9 (table index) optional

### EFFECT_ROTW `FA6CE96E` (16 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | L | effect id (0xKKKKNNNN: effect file group << 16 / entry) | no vanilla uses |
| 1 | Bone | L | bone id the effect is placed on (0 = top/root) | no vanilla uses |
| 2 | X | L | offset from the bone, X | no vanilla uses |
| 3 | Y | L | offset from the bone, Y | no vanilla uses |
| 4 | Z | L | offset from the bone, Z | no vanilla uses |
| 5 | XRot | L | rotation (degrees) about X | no vanilla uses |
| 6 | YRot | L | rotation (degrees) about Y | no vanilla uses |
| 7 | ZRot | L | rotation (degrees) about Z | no vanilla uses |
| 8 | Size | L | uniform scale | no vanilla uses |
| 9 | RandomX | L | random offset range (+/-) on X | no vanilla uses |
| 10 | RandomY | L | random offset range (+/-) on Y | no vanilla uses |
| 11 | RandomZ | L | random offset range (+/-) on Z | no vanilla uses |
| 12 | RandomXRot | L | random rotation range (+/- degrees) about X | no vanilla uses |
| 13 | RandomYRot | L | random rotation range (+/- degrees) about Y | no vanilla uses |
| 14 | RandomZRot | L | random rotation range (+/- degrees) about Z | no vanilla uses |
| 15 | Terminate | L | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | no vanilla uses |

Evidence: handler 0x02BDFC60 is a stub (skips 16 params, calls nothing); names by analogy with the EFFECT layout

### EFFECT_STRENGTH `056A8146` (18 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | no vanilla uses |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | no vanilla uses |
| 2 | X | H | offset from the bone, X | no vanilla uses |
| 3 | Y | H | offset from the bone, Y | no vanilla uses |
| 4 | Z | H | offset from the bone, Z | no vanilla uses |
| 5 | XRot | H | rotation (degrees) about X | no vanilla uses |
| 6 | YRot | H | rotation (degrees) about Y | no vanilla uses |
| 7 | ZRot | H | rotation (degrees) about Z | no vanilla uses |
| 8 | Size | H | uniform scale | no vanilla uses |
| 9 | Strength | M | strength value (size = Size + Strength*SizePerStrength when non-zero) | no vanilla uses |
| 10 | RandomX | H | random offset range (+/-) on X | no vanilla uses |
| 11 | RandomY | H | random offset range (+/-) on Y | no vanilla uses |
| 12 | RandomZ | H | random offset range (+/-) on Z | no vanilla uses |
| 13 | RandomXRot | H | random rotation range (+/- degrees) about X | no vanilla uses |
| 14 | RandomYRot | H | random rotation range (+/- degrees) about Y | no vanilla uses |
| 15 | RandomZRot | H | random rotation range (+/- degrees) about Z | no vanilla uses |
| 16 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | no vanilla uses |
| 17 | SizePerStrength | M | size added per unit of Strength | no vanilla uses |

Evidence: MSC 0x2716 (0x02C2FF9C): eff, bone, pos, rot, scale (word 9), strength (word 10), rand pos, rand rot, terminate (word 17), rate (word 18); size += strength*rate if strength != 0

### EFFECT_SYNC_SCALE `0141BB6A` (1 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Enable | H | bool -> EffectModule+0x1D: later follow effects are scaled by the owner model scale | 0 x2, 1 x2 (n=4) |

Evidence: MSC op 0x28 (0x02C2F0C0) -> vt+0x22C (stb +0x1D); read in req_follow 0x02C2B060

### EFFECT_WITH_HANDLE `1E42EE23` (17 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | no vanilla uses |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | no vanilla uses |
| 2 | X | H | offset from the bone, X | no vanilla uses |
| 3 | Y | H | offset from the bone, Y | no vanilla uses |
| 4 | Z | H | offset from the bone, Z | no vanilla uses |
| 5 | XRot | H | rotation (degrees) about X | no vanilla uses |
| 6 | YRot | H | rotation (degrees) about Y | no vanilla uses |
| 7 | ZRot | H | rotation (degrees) about Z | no vanilla uses |
| 8 | Size | H | uniform scale | no vanilla uses |
| 9 | RandomX | H | random offset range (+/-) on X | no vanilla uses |
| 10 | RandomY | H | random offset range (+/-) on Y | no vanilla uses |
| 11 | RandomZ | H | random offset range (+/-) on Z | no vanilla uses |
| 12 | RandomXRot | H | random rotation range (+/- degrees) about X | no vanilla uses |
| 13 | RandomYRot | H | random rotation range (+/- degrees) about Y | no vanilla uses |
| 14 | RandomZRot | H | random rotation range (+/- degrees) about Z | no vanilla uses |
| 15 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | no vanilla uses |
| 16 | HandleWork | H | work int variable id that receives the new effect handle (WorkModule set_int) | no vanilla uses |

Evidence: handler WorkModule set_int(handle, p16) / handler: EffectModule vt+0x4C (EFFECT layout)

### EFFECT_WORK `8FE9E295` (16 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GraphicWork | H | work int variable id holding the effect id (read with WorkModule get_int) | 0x10000091 x2, 0x10000096 x1, 0x10000094 x1, 0x10000095 x1 (n=5) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 1 x3, 0 x2 (n=5) |
| 2 | X | H | offset from the bone, X | 0 x3, 2f x2 (n=5) |
| 3 | Y | H | offset from the bone, Y | 10f x2, 8f x1, 14f x1, 12.5f x1 (n=5) |
| 4 | Z | H | offset from the bone, Z | 4f x3, 2f x1, 3f x1 (n=5) |
| 5 | XRot | H | rotation (degrees) about X | 0 x4, -75f x1 (n=5) |
| 6 | YRot | H | rotation (degrees) about Y | 0 x5 (n=5) |
| 7 | ZRot | H | rotation (degrees) about Z | 0 x4, 120f x1 (n=5) |
| 8 | Size | H | uniform scale | 1.1f x2, 1f x2, 0.9f x1 (n=5) |
| 9 | RandomX | H | random offset range (+/-) on X | 0 x5 (n=5) |
| 10 | RandomY | H | random offset range (+/-) on Y | 0 x5 (n=5) |
| 11 | RandomZ | H | random offset range (+/-) on Z | 0 x3, 2f x2 (n=5) |
| 12 | RandomXRot | H | random rotation range (+/- degrees) about X | 0 x5 (n=5) |
| 13 | RandomYRot | H | random rotation range (+/- degrees) about Y | 0 x5 (n=5) |
| 14 | RandomZRot | H | random rotation range (+/- degrees) about Z | 0 x3, 20f x2 (n=5) |
| 15 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x5 (n=5) |

Evidence: EffectModule MSC handler 0x02C2CEC8 generic EFFECT path (0x02C2FA8C): words read as eff, bone, pos[3], rot[3], scale, rand pos[3], rand rot[3], terminate; request vt+0x4C / handler get_int(p0) -> EffectModule vt+0x4C

### EFFECT_WORK_PR `E9396C35` (16 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | no vanilla uses |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | no vanilla uses |
| 2 | XWork | H | float work variable id for offset X | no vanilla uses |
| 3 | YWork | H | float work variable id for offset Y | no vanilla uses |
| 4 | ZWork | H | float work variable id for offset Z | no vanilla uses |
| 5 | XRotWork | H | float work variable id for rotation X | no vanilla uses |
| 6 | YRotWork | H | float work variable id for rotation Y | no vanilla uses |
| 7 | ZRotWork | H | float work variable id for rotation Z | no vanilla uses |
| 8 | Size | H | uniform scale | no vanilla uses |
| 9 | RandomX | H | random offset range (+/-) on X | no vanilla uses |
| 10 | RandomY | H | random offset range (+/-) on Y | no vanilla uses |
| 11 | RandomZ | H | random offset range (+/-) on Z | no vanilla uses |
| 12 | RandomXRot | H | random rotation range (+/- degrees) about X | no vanilla uses |
| 13 | RandomYRot | H | random rotation range (+/- degrees) about Y | no vanilla uses |
| 14 | RandomZRot | H | random rotation range (+/- degrees) about Z | no vanilla uses |
| 15 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | no vanilla uses |

Evidence: EffectModule MSC handler 0x02C2CEC8 generic EFFECT path (0x02C2FA8C): words read as eff, bone, pos[3], rot[3], scale, rand pos[3], rand rot[3], terminate; request vt+0x4C / handler reads these with WorkModule get_float (vt+0x44) and passes the values to MSC 0x2710 (EFFECT)

### EFFECT_WORK_R `BBAD115E` (16 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | 0x32A000F x5, 0x32A0005 x5, 0x32A0010 x3 (n=13) |
| 1 | Bone | H | bone id the effect is placed on (0 = top/root) | 2001 x13 (n=13) |
| 2 | X | H | offset from the bone, X | 0 x13 (n=13) |
| 3 | Y | H | offset from the bone, Y | 13f x10, 12f x3 (n=13) |
| 4 | Z | H | offset from the bone, Z | 0 x13 (n=13) |
| 5 | XRotWork | H | float work variable id for rotation X | 12 x13 (n=13) |
| 6 | YRotWork | H | float work variable id for rotation Y | 13 x13 (n=13) |
| 7 | ZRotWork | H | float work variable id for rotation Z | 14 x13 (n=13) |
| 8 | Size | H | uniform scale | 1f x12, 1.4f x1 (n=13) |
| 9 | RandomX | H | random offset range (+/-) on X | 0 x13 (n=13) |
| 10 | RandomY | H | random offset range (+/-) on Y | 0 x13 (n=13) |
| 11 | RandomZ | H | random offset range (+/-) on Z | 0 x13 (n=13) |
| 12 | RandomXRot | H | random rotation range (+/- degrees) about X | 0 x13 (n=13) |
| 13 | RandomYRot | H | random rotation range (+/- degrees) about Y | 0 x13 (n=13) |
| 14 | RandomZRot | H | random rotation range (+/- degrees) about Z | 0 x13 (n=13) |
| 15 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x13 (n=13) |

Evidence: EffectModule MSC handler 0x02C2CEC8 generic EFFECT path (0x02C2FA8C): words read as eff, bone, pos[3], rot[3], scale, rand pos[3], rand rot[3], terminate; request vt+0x4C / handler reads these with WorkModule get_float (vt+0x44) and passes the values to MSC 0x2710 (EFFECT)

### EM_EFFECT_CENTER `2440EFE2` (15 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | no vanilla uses |
| 1 | X | H | offset from the bone, X | no vanilla uses |
| 2 | Y | H | offset from the bone, Y | no vanilla uses |
| 3 | Z | H | offset from the bone, Z | no vanilla uses |
| 4 | XRot | H | rotation (degrees) about X | no vanilla uses |
| 5 | YRot | H | rotation (degrees) about Y | no vanilla uses |
| 6 | ZRot | H | rotation (degrees) about Z | no vanilla uses |
| 7 | Size | H | uniform scale | no vanilla uses |
| 8 | RandomX | H | random offset range (+/-) on X | no vanilla uses |
| 9 | RandomY | H | random offset range (+/-) on Y | no vanilla uses |
| 10 | RandomZ | H | random offset range (+/-) on Z | no vanilla uses |
| 11 | RandomXRot | H | random rotation range (+/- degrees) about X | no vanilla uses |
| 12 | RandomYRot | H | random rotation range (+/- degrees) about Y | no vanilla uses |
| 13 | RandomZRot | H | random rotation range (+/- degrees) about Z | no vanilla uses |
| 14 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | no vanilla uses |

Evidence: handler: enemy module (+0x74) vt+0x14C gives the centre bone, then EffectModule vt+0x4C(eff, centre, &pos p1-3, &rot p4-6, &rand p8-10, &randrot p11-13, terminate p14), f1 = p7

### EM_EFFECT_DAMAGE_CENTER `332DB456` (15 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Graphic | H | effect id (0xKKKKNNNN: effect file group << 16 / entry) | no vanilla uses |
| 1 | X | H | offset from the bone, X | no vanilla uses |
| 2 | Y | H | offset from the bone, Y | no vanilla uses |
| 3 | Z | H | offset from the bone, Z | no vanilla uses |
| 4 | XRot | H | rotation (degrees) about X | no vanilla uses |
| 5 | YRot | H | rotation (degrees) about Y | no vanilla uses |
| 6 | ZRot | H | rotation (degrees) about Z | no vanilla uses |
| 7 | Size | H | uniform scale | no vanilla uses |
| 8 | RandomX | H | random offset range (+/-) on X | no vanilla uses |
| 9 | RandomY | H | random offset range (+/-) on Y | no vanilla uses |
| 10 | RandomZ | H | random offset range (+/-) on Z | no vanilla uses |
| 11 | RandomXRot | H | random rotation range (+/- degrees) about X | no vanilla uses |
| 12 | RandomYRot | H | random rotation range (+/- degrees) about Y | no vanilla uses |
| 13 | RandomZRot | H | random rotation range (+/- degrees) about Z | no vanilla uses |
| 14 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | no vanilla uses |

Evidence: handler: enemy module (+0x74) vt+0x14C/0x134/0x13C give the centre bone, then EffectModule vt+0x4C(eff, centre, &pos p1-3, &rot p4-6, &rand p8-10, &randrot p11-13, terminate p14), f1 = p7; size multiplied by the enemy param table scale (0x102F6C00)

### FLASH_NO_STOP `7522830D` (4 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Red | M | red 0-255 | 255f x2, 200f x1, 190f x1 (n=4) |
| 1 | Green | M | green 0-255 | 255f x2, 180f x1, 0 x1 (n=4) |
| 2 | Blue | M | blue 0-255 | 255f x4 (n=4) |
| 3 | Alpha | M | alpha 0-255 | 90f x2, 150f x1, 80f x1 (n=4) |

Evidence: handler: ColorBlend module (+0x38) vt+0xCC then vt+0x4C(&[r,g,b,a], 0, 1)

### FOOT_EFFECT_FLIP `B208689A` (18 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GFXRight | H | effect id used when the motion is not flipped | 0x100000E x2 (n=2) |
| 1 | GFXLeft | H | effect id used when the motion is flipped (MotionModule is_flip) | 0x100000D x2 (n=2) |
| 2 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x2 (n=2) |
| 3 | X | H | offset from the bone, X | 0 x2 (n=2) |
| 4 | Y | H | offset from the bone, Y | 0 x2 (n=2) |
| 5 | Z | H | offset from the bone, Z | 0 x2 (n=2) |
| 6 | XRot | H | rotation (degrees) about X | 0 x2 (n=2) |
| 7 | YRot | H | rotation (degrees) about Y | 0 x2 (n=2) |
| 8 | ZRot | H | rotation (degrees) about Z | 0 x2 (n=2) |
| 9 | Size | H | uniform scale | 0.8f x1, 0.5f x1 (n=2) |
| 10 | RandomX | H | random offset range (+/-) on X | 0 x2 (n=2) |
| 11 | RandomY | H | random offset range (+/-) on Y | 0 x2 (n=2) |
| 12 | RandomZ | H | random offset range (+/-) on Z | 0 x2 (n=2) |
| 13 | RandomXRot | H | random rotation range (+/- degrees) about X | 0 x2 (n=2) |
| 14 | RandomYRot | H | random rotation range (+/- degrees) about Y | 0 x2 (n=2) |
| 15 | RandomZRot | H | random rotation range (+/- degrees) about Z | 0 x2 (n=2) |
| 16 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 1 x1, 0 x1 (n=2) |
| 17 | FlipType | M | EF_FLIP-style mirror mode, applied only when MotionModule is_flip (vt+0x26C) is true; passed to the request as the flip argument. Vanilla: 1 almost always (the usual mirror), 0 none, 3/4 rare | 0 x2 (n=2) |

Evidence: MSC 0x02C2FA8C / 0x02C3009C flip ops (0x2738-0x2742): MotionModule(+0x44) vt+0x26C picks word1 (not flipped) or word2 (flipped); word3 = flip arg (only when flipped); bone = word4; ACMD handler moves the last ACMD param into word3; 0x2741 skipped when EffectModule bytes +0x9F/+0xA0 are set

### LANDING_EFFECT_FLIP `515F97FF` (18 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | GFXRight | H | effect id used when the motion is not flipped | 0x100000D x83, 0x100000E x49, 0x1000020 x4, 0x334000E x1 (n=137) |
| 1 | GFXLeft | H | effect id used when the motion is flipped (MotionModule is_flip) | 0x100000E x82, 0x100000D x50, 0x1000020 x4, 0x334000D x1 (n=137) |
| 2 | Bone | H | bone id the effect is placed on (0 = top/root) | 0 x137 (n=137) |
| 3 | X | H | offset from the bone, X | 0 x100, 2f x19, -2f x8, -1f x5, 8f x1 (n=137) |
| 4 | Y | H | offset from the bone, Y | 0 x136, 1f x1 (n=137) |
| 5 | Z | H | offset from the bone, Z | 0 x129, 2f x7, 1f x1 (n=137) |
| 6 | XRot | H | rotation (degrees) about X | 0 x137 (n=137) |
| 7 | YRot | H | rotation (degrees) about Y | 0 x135, 180f x2 (n=137) |
| 8 | ZRot | H | rotation (degrees) about Z | 0 x137 (n=137) |
| 9 | Size | H | uniform scale | 1f x58, 1.2f x27, 0.9f x20, 0.8f x6, 1.25f x5 (n=137) |
| 10 | RandomX | H | random offset range (+/-) on X | 0 x137 (n=137) |
| 11 | RandomY | H | random offset range (+/-) on Y | 0 x137 (n=137) |
| 12 | RandomZ | H | random offset range (+/-) on Z | 0 x137 (n=137) |
| 13 | RandomXRot | H | random rotation range (+/- degrees) about X | 0 x137 (n=137) |
| 14 | RandomYRot | H | random rotation range (+/- degrees) about Y | 0 x137 (n=137) |
| 15 | RandomZRot | H | random rotation range (+/- degrees) about Z | 0 x137 (n=137) |
| 16 | Terminate | H | bool: the effect ends when the action/animation changes (follow forms: flag 0x4000) | 0 x111, 1 x26 (n=137) |
| 17 | FlipType | M | EF_FLIP-style mirror mode, applied only when MotionModule is_flip (vt+0x26C) is true; passed to the request as the flip argument. Vanilla: 1 almost always (the usual mirror), 0 none, 3/4 rare | 0 x100, 1 x21, 3 x13, 4 x3 (n=137) |

Evidence: MSC 0x02C2FA8C / 0x02C3009C flip ops (0x2738-0x2742): MotionModule(+0x44) vt+0x26C picks word1 (not flipped) or word2 (flipped); word3 = flip arg (only when flipped); bone = word4; ACMD handler moves the last ACMD param into word3; 0x273A substitutes the effect from the ground-material table (+0x28)

### LAST_EFFECT_SET_ALPHA `BF72BDCA` (1 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Alpha | H | alpha in percent (handler divides by 100; 100 = opaque, >100 allowed) | 50f x25, 60f x10, 80f x6, 70f x6, 40f x4 (n=53) |

Evidence: handler: f1 = p0/100 -> EffectModule vt+0x2B4 (last effect alpha)

### LAST_EFFECT_SET_COLOR `09C4CC49` (3 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Red | H | red 0-255 (/255) for the last effect | 255f x16, 50f x3, 25f x3, 20f x2, 222f x2 (n=45) |
| 1 | Green | H | green 0-255 (/255) for the last effect | 240f x7, 115f x3, 51f x3, 15f x3, 50f x3 (n=45) |
| 2 | Blue | H | blue 0-255 (/255) for the last effect | 100f x7, 255f x5, 76f x3, 47f x2, 221f x2 (n=45) |

Evidence: handler: vt+0x2FC (last handle), vt+0x27C(f1-f3 = p/255)

### LAST_EFFECT_SET_RATE `FD1F7ECF` (1 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Rate | H | playback rate of the last effect (1 = normal) | 1.5f x178, 1.2f x129, 2f x79, 1.3f x71, 1.1f x45 (n=737) |

Evidence: handler: f1 = p0 -> EffectModule vt+0x2A4

### LAST_EFFECT_SET_RATE_WORK `6E332637` (1 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | RateWork | H | float work variable id holding the rate (WorkModule get_float) for the last effect | 2 x4 (n=4) |

Evidence: handler: get_float(p0) -> vt+0x2A4

### LAST_EFFECT_SET_SCALE `83D4A124` (3 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | ScaleX | H | last effect scale X | no vanilla uses |
| 1 | ScaleY | H | last effect scale Y | no vanilla uses |
| 2 | ScaleZ | H | last effect scale Z | no vanilla uses |

Evidence: handler: &[p0,p1,p2] -> EffectModule vt+0x2AC

### LAST_EFFECT_SET_SCALE_W `D9CC663F` (3 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | ScaleXWork | H | float work variable id for last effect scale X | 0x1000006 x6 (n=6) |
| 1 | ScaleYWork | H | float work variable id for last effect scale Y | 0x1000006 x6 (n=6) |
| 2 | ScaleZWork | H | float work variable id for last effect scale Z | 0x1000006 x6 (n=6) |

Evidence: handler: get_float(p0..p2) -> vt+0x2AC

### LIGHT_AXIS `FE036C47` (14 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Red | M | red 0-255 (vanilla 70,50,160,255) | 70f x1 (n=1) |
| 1 | Green | M | green 0-255 (vanilla 70,50,160,255) | 50f x1 (n=1) |
| 2 | Blue | M | blue 0-255 (vanilla 70,50,160,255) | 160f x1 (n=1) |
| 3 | Alpha | M | alpha 0-255 (vanilla 70,50,160,255) | 255f x1 (n=1) |
| 4 | Unk4 | L | unknown float (0 in the only use) | 0 x1 (n=1) |
| 5 | Unk5 | L | unknown float (0 in the only use) | 0 x1 (n=1) |
| 6 | Unk6 | L | unknown float (0 in the only use) | 0 x1 (n=1) |
| 7 | Radius | L | light radius? (10 in the only use; SET_LIGHT_RADIUS is op 3) | 10f x1 (n=1) |
| 8 | Length | L | light length? (25; SET_LIGHT_LENGTH is op 4) | 25f x1 (n=1) |
| 9 | AxisX | L | axis/direction X? (0) | 0 x1 (n=1) |
| 10 | AxisY | L | axis Y? (0) | 0 x1 (n=1) |
| 11 | AxisZ | L | axis Z? (1) | 1f x1 (n=1) |
| 12 | Unk12 | L | unknown (0) | 0 x1 (n=1) |
| 13 | Unk13 | L | unknown (-1; maybe bone/frames, -1 = none) | -1f x1 (n=1) |

Evidence: handler -> ColorBlend module (+0x38) vt+0xF4 MSC op 1 with p0-p13 raw (the module handler was not decoded); one vanilla use (Samus laser)

### LIGHT_AXIS_FRM `70FBED79` (4 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Frames | M | int frame count (4, 28, 3, 7) | 4 x1, 28 x1, 3 x1, 7 x1 (n=4) |
| 1 | Unk1 | L | float 50-180 (length/size target?) | 100f x1, 140f x1, 180f x1, 50f x1 (n=4) |
| 2 | Unk2 | L | float 20 or 300 | 300f x3, 20f x1 (n=4) |
| 3 | Unk3 | L | float -0.75..1 (rate/direction?) | -0.5f x2, -0.75f x1, 1f x1 (n=4) |

Evidence: handler -> ColorBlend module (+0x38) vt+0xF4 MSC op 6 (p0-p3 raw); 4 vanilla uses in Samus laser

### SET_LIGHT_LENGTH `21FDA8DF` (1 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Length | M | light length (ColorBlend MSC op 4) | no vanilla uses |

Evidence: handler -> +0x38 vt+0xF4 op 4; no vanilla uses

### SET_LIGHT_RADIUS `1BFC5837` (1 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Radius | M | light radius (ColorBlend MSC op 3) | no vanilla uses |

Evidence: handler -> +0x38 vt+0xF4 op 3; no vanilla uses

### Morph_Model_Event `27213F09` (1 params)

| # | name | conf | meaning | vanilla values |
|---|------|------|---------|----------------|
| 0 | Visible | L | bool: held-item visibility (0 hide, 1 show) - ItemModule (+0x64) MSC op 0x16; like Ultimate ItemModule::set_have_item_visibility | 0 x159, 1 x84 (n=243) |

Evidence: handler -> ItemModule (+0x64, the module of Pickup/Throw/Item_Visibility) vt+0x234 op 0x16; used 0 then 1 in entry, dodge and Bowser up-B expression scripts
