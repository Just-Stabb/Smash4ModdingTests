# ACMD command parameters

Labels and meanings for every previously unknown parameter of Sm4shCommand's command table: 400 commands. They
were read off the game's command handlers (`cross_f.rpx`: command CRC → `0x100FAAB8` → handler table
`0x10350ED8`), the module code those handlers call, and every use in the 1053 vanilla fighter ACMD files.

- **Data:** `tools/Sm4shCommand/param_labels.json`. Keyed by command hash; each slot has a name, a
  description, its vanilla values, the evidence and a confidence (high / medium / low).
- **Applying it:** `python3 tools/Sm4shCommand/apply_param_labels.py` (`--check` to preview). This
  - writes the names, types and sizes into SALT's `CMD_INFO.cs`;
  - regenerates `tools/acmd_info.json`;
  - regenerates `SM4SHCommand/Events.cfg`, whose `Param: Name = description` lines are the editor's
    tooltips. The command list (View > Commands) shows them as well.
- **Write-ups:**

  | File | Covers |
  |---|---|
  | [hitbox](acmd-params/hitbox.md) | the 14 hitbox commands (Hitbox, Special_Hitbox, the capsule, intensity, indirect and ignore-throw forms) |
  | [throws-grabs-other](acmd-params/throws-grabs-other.md) | throws, grabs, search boxes and the other attack-family commands (28) |
  | [effects](acmd-params/effects.md) | effect, trail, light and colour commands (74) |
  | [misc-a](acmd-params/misc-a.md) | compares, wind areas, charge, item and article commands (118) |
  | [misc-b](acmd-params/misc-b.md) | sound, camera, item AI, trace and other commands (151) |

## What changed in the table

- **Parameter names.** Every `unknown` slot of these commands has a name now. Existing names were
  checked, and wrong ones corrected. Examples:
  - Hitbox `WBKB` → `FKB`, `StretchToggle` → `Shape`, slot 26 → `CollisionPart`;
  - throw slots that were labelled as bones are really hit groups.
- **Types.** 85 commands had parameters typed int that the game reads as floats, or the reverse, so
  the editor showed `1065353216` instead of `1.0`. They were found from the handlers (`lfs`) and by
  checking vanilla values: an int slot whose every use is a float bit pattern. Most were effect
  commands (offsets, rotations, sizes, colours), plus ATK_POWER_MUL, START_CHARGE and the unknown
  hitbox forms. Sword_Trace's blur length went the other way, from float to int. Changing a type
  doesn't change any file: scripts are decompiled from the binary with the new type.
- **Sizes.** Collateral_Hitbox had 25 names for 24 parameters, and Intensity_Special_Hitbox 46 for 47.
- **Command names.** 62 `unk_XXXXXXXX` commands got a name:
  - **Hash-verified.** These names hash to the command's CRC, e.g. `EFFECT_FLW_POS_NO_STOP`,
    `SET_TAKEOUT_SE`, `LAST_PARTICLE_SET_COLOR`, `LAST_EFFECT_SET_DISABLE_SYSTEM_SLOW`.
  - **Descriptive.** The others were named from their handler. Their description says so and gives
    the old `unk_` name. Examples: `START_CHARGE_2_joint_form`, `Int_Var_Compare_Type`,
    `PLAY_STEP_FLIPPABLE`.
- **Real names of misnamed commands.** 20 named commands hash to a different, real name. Their names
  are kept, because existing scripts use them; the real name is added to the description:
  - Disallow_Vertical_Movement is CLR_SPEED, and Disallow_Horizontal_Movement is ENABLE_ENERGY;
  - Low_Voice_Clip is PLAY_SEQUENCE, and Slope_Full is SLOPE_INTP;
  - External_Graphic is EFFECT_FOLLOW, and Sound_Effect is PLAY_SE;
  - Add/Subtract_Momentum is SET_SPEED;
  - and 13 more (listed in [misc-b](acmd-params/misc-b.md)).

## Worth knowing when writing scripts

- **ATTACK_FP_CAPSULE_IGNORE_THROW is broken as defined.** Its handler sends 43 arguments to a
  worker that wants 44, so HitBits … Shape stay 0. Use Extended_Special_Hitbox and a
  Collateral-style ignore instead. Details: [hitbox](acmd-params/hitbox.md).
- **PLAY_STEP_FLIPPABLE ignores its second sound.** The handler passes parameter 0 twice.
- **No-op commands.** GET_PITCH, GET_VOLUME, IT_WINDOW and the MODIFY_RHOMBUS_* commands do nothing.
- **Ground/Air bit 31** is a separate flag: it stops the hitbox from hitting one victim class.
  Inhales and command grabs use it.
- **Confidence.** Low-confidence labels rest on vanilla values only. The tooltips show the
  confidence.
