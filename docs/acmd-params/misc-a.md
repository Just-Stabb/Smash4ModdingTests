# ACMD unknown parameters: misc batch A

This batch covers 118 commands from `batch_misc_a.json`, with 445 slots in total: the 418 unknown slots plus the existing names, which were checked again. The full per-slot labels (name, desc, values, evidence, confidence) are in `tools/Sm4shCommand/param_labels.json`, keyed by command hash.

Confidence across the 445 slots:

| Confidence | Slots |
|---|---|
| High | 90 |
| Medium | 127 |
| Low | 228 |

## Method

- **Handlers.** For each command, the handler comes from `cross_f.rpx`: the CRC→index table at `0x100FAAB8`, then the handler table at `0x10350ED8`. I read:
  - each parameter load and its type (`lwz` / `lfs` / `lhz` / `lbz`);
  - the module it uses, taken from the accessor offset;
  - the vtable slot, or the MSC op and the order of its arguments.
- **Module internals.** Where the vtable was known, I followed the call into the module:
  - AttackModule `0x10103524`;
  - SoundModule `0x1010BFB4`;
  - WorkModule (from `docs/native-notes.md`).
- **Corpus.** Vanilla values come from the 1053 fighter ACMD files. Animation names come from CRC32 of the `.omo` names in the motion `.pac` files, plus guessed item-swing names (`starrodswing3/4`, `lipstickswing3/4`, `clubswing1/3/4/dash`, `swordswing1/3/4/dash`).
- **Cross-checks.** Ultimate's macros and module functions, and the MSC note sheet (`reference/msc-note-sheet`).

## Renamed commands (proposed)

| Hash | Old | Proposed | Why |
|---|---|---|---|
| 01A5A27C | unk_01A5A27C | PLAY_STEP_FLIPPABLE | Calls SoundModule `+0xBC`, which picks SE 1 or SE 2 by MotionModule `+0x26C` (motion flipped) and then plays it through `+0xB4` (PLAY_STEP / Sound_Effect2). The vanilla pairs are swapped left/right footstep IDs. |
| 040FD56E | unk_040FD56E | Slope_Full2 | SlopeModule op `0x2711`, the same op as Slope_Full (status, frames), with a third argument that is always 1. |
| 0A539357 | unk_0A539357 | EFFECT_FOLLOW_VARIATION | EffectModule op `0x2712` (External_Graphic's op) plus a work variable. Vanilla passes `0x1000003C`, the costume ID, so the effect is coloured per costume (Yoshi, Sonic, R.O.B.). |
| 0A7BF1D4 | unk_0A7BF1D4 | GENERATE_ARTICLE2 | ArticleModule op `0x2710` (GENERATE_ARTICLE's op) with an extra flag. |
| 16945ACC | unk_16945ACC | ATTACK_MOTION_FLIP | A full 41-word ATTACK layout (handler `0x020000A0`). It negates Z when the motion is flipped. |
| 1C843790 | unk_1C843790 | SET_POS | PostureModule `+0x4C` set_pos(x, y, z). |
| 2953BFDE | unk_2953BFDE | Sword_Glow2 | EffectModule op `0x2731`, Sword_Glow's op: Sword_Glow's 26 slots plus one extra int (Shulk, Cloud, Zelda). |
| 2E8ABC2E | unk_2E8ABC2E | Screen_Tint2 | Same EffectModule `+0x19C` call as Screen_Tint, with the layer fixed at 0 and the priority at `0x80`. |
| 377D36CB | unk_377D36CB | Float_Var_Compare_Var | Compares float var with float var; used by Lucario. |
| 2E66078A | unk_2E66078A | Float_Compare_Var | Compares a float type with a float var. |
| 407A065D | unk_407A065D | Float_Var_Compare_Type | Compares a float var with a float type. |
| 44B6E0FE | unk_44B6E0FE | Int_Compare_Var | Compares an int type with an int var. |
| 2AAAE129 | unk_2AAAE129 | Int_Var_Compare_Type | Compares an int var with an int type. |
| 33B1D068 | unk_33B1D068 | Int_Compare_Type_Type | Compares an int type with an int type. |

**Compare methods**, from `0x02BEE010` / `0x02BEE028`:

| Method | Comparison |
|---|---|
| 0 | `==` |
| 1 | `!=` |
| 2 | `<=` |
| 3 | `>=` |
| 4 | `<` |
| 5 | `>` |

A "type" is the Int_Compare / Float_Compare value-kind index, looked up through getter tables `0x10351880` (int) and `0x103518A8` (float).

## Notable findings

- **Screen_Tint labels are off by one.** The real order is:
  1. mode
  2. transition frames
  3. R
  4. G
  5. B
  6. A (bytes)
  7. layer (int)
  8. priority (low byte)

  The old labels (TransitionTime, Red, Green, Blue, Alpha, Duration, unknown, TransitionOutTime) start one slot early.
- **PLAY_STEP_FLIPPABLE ignores its second sound.** The handler passes param 0 twice (`mr r5, r4`), so the flipped sound is never used.
- **Slots that are really floats.** The handler reads these with `lfs`, so their format should be float:
  - ATK_POWER_MUL;
  - ATK_POWER_MUL_STATUS (vanilla `0x3F800000` = 1.0);
  - AREA_WIND_2ND p1–p8;
  - AREA_WIND_2ND_RAD p5 (X; marked int);
  - START_CHARGE p0–p5;
  - unk_0A539357 p2–p8;
  - unk_2953BFDE, at the same slots as Sword_Glow;
  - unk_1C843790;
  - unk_0FEF7676 p4–p5;
  - several IT_* commands.
- **No-op handlers.** These only advance the script, so their parameters are never read:
  - GET_PITCH, GET_VOLUME;
  - IT_IS_EXIST_PERCENT, IT_WINDOW, Item_Time_Manipulation;
  - MODIFY_RHOMBUS_UP, MODIFY_RHOMBUS_DOWN, MODIFY_RHOMBUS_WIDTH.
- **EXECUTE(frame)** sets the script's execute flag (byte `flags+8`, which every command checks) once the current frame is at or past the value.
- **ArticleModule ops**, through vtable `+0x17C`:

  | Op | Command |
  |---|---|
  | `0x2710` | GENERATE_ARTICLE |
  | `0x2711` | Article_Event |
  | `0x2712` | Remove_Article |
  | `0x2716` | MOT_CHANGE_EXIST_ARTICLE (article, motion) |
  | `0x2718` | GENERATE_ARTICLE_ENABLE |
  | `0x271A` | SHOOT_EXIST_ARTICLE |
  | `0x2730` | VIS_BACK_DEFAULT_ARTICLE (article, group) |

  IS_EXIST_ARTICLE and IS_GENERATABLE_ARTICLE call vtable `+0xFC` and `+0x10C` directly.
- **GroundModule ops**, through vtable `+0x4BC`:

  | Op | Command |
  |---|---|
  | `0x1D` | IGNORE_BOX2D_GROUND |
  | `0x1E` | IGNORE_BOX2D_SHAPE |
  | `0x2713` | PASSABLE_CHECK |
  | `0x2717` | GROUND_SHAPE_FLAG (flag 8 = Ultimate's RHOMBUS_MODIFY_FLAG_FIX, bool) |

- **Rumble / Rumble_Loop** are ControlModule ops `0x2714` / `0x2718` with (kind, start frame?).
- **Camera.** QUAKE and QUAKE_STOP call CameraModule `+0x1C4` / `+0x1D4` (kind 1–6).
- **Time_Manipulation_Whole** is SlowModule set_whole (rate, frames).
- **UNABLE_ENERGY** is KineticModule op `0xC` (disable energy, by ID).
- **SUB_FLOAT_2(a, b)** computes var a −= var b.
- **unk_4290DF6A** writes int vars `0x1000001C` and `0x1000001D` directly.
- **ATK_* commands:**

  | Command | What it does |
  |---|---|
  | ATK_POWER_ADD | adds an int var to hitbox damage (slot `+0x18`) |
  | ATK_KEEP_RUMBLE | hitbox `+0x65` = 1 |
  | ATK_REFERENCE_NODE | stores (joint, axis) at `+0xE0` / `+0xE4` and reads them as a ModelModule matrix column |
  | ATK_LERP / ATK_LERP_RATIO | AttackModule `+0x3C4` / `+0x3D4` |
  | ATK_WHOLE | per-hitbox byte `+0x3D` |
  | ATK_HIT_ABS_WC / WV / VV | Throw_Applier's call, with the target taken from a work var (W), a value kind (V) or a constant (C) |

- **REFLECTOR slot 12** is the boolean Ultimate passes as `false` in `shield!(MA_MSC_CMD_REFLECTOR, ...)`. Type 2 is the Home-Run Bat group.

## What stays unknown, and why

- **Item-side commands (IT_\*, unk_0DE1E7A0, unk_0FEF7676, unk_36F14B53, unk_3EEF0FF9, unk_41F67BC5, unk_131E5816).** No fighter script uses them and I had no item ACMD corpus. Their handlers call item functions (`0x0303xxxx` / `0x0308xxxx`) that I did not trace, so only the parameter types are given.
- **ItemModule ops (Item_Property op `0xA`, ITEM_ACTION op `0x13`, Pickup ops 6 / 9, Fire op `0xC`).** The op switch inside ItemModule was not located. The meanings come from the item-swing animation context only.
- **BattleObject message `0x3E8` (unk_1B41048C for Bayonetta, unk_2068DF37 for Mega Man).** The meaning lives in each fighter's specializer and was not traced.
- **AREA_WIND_2ND(_RAD) middle floats and START_CHARGE triplets.** The handlers only pack an array into a module whose fighter-side MSC switch I did not find, so these rest on vanilla values and Ultimate's argument shapes.
- **Trace commands, BGM commands, unk_1B26C673, unk_22E2E4C6, unk_3B31D521 / unk_00559051 / unk_12ABD222 effect extras, EM_STOP, unk_37CA2121 (AttackModule `+0x104` float).** Only the call target and argument types are known.
