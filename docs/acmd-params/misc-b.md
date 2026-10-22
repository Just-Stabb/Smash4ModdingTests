# ACMD unknown parameters: misc batch B

151 commands, 495 previously unknown slots (plus 11 named slots confirmed). Every unknown slot is labelled
in `tools/Sm4shCommand/param_labels.json`.

Previously unknown slots by confidence: high 172, medium 137, low 186.

## How the labels were found

- **Handlers**: hash → index through the CRC table at 0x100FAAB8, handler = `[0x10350ED8 + 4*index]` in
  `cross_f.rpx`. Every handler was disassembled and annotated (which module accessor offset, which vtable
  slot, which arg goes in which register, float vs word loads).
- **MSC ops**: commands that call a module's MSC handler pass `{op, args...}`. The op numbers were recovered
  for every command in the game (not only this batch), so an unknown command that sends the same op as a
  named one gets that one's meaning. Module MSC handlers located in .text: Kinetic 0x2C510C4 (vtable
  0x10108848), Article 0x2C05FB0, Attack 0x2C0ACFC, Camera 0x2C160F0, ColorBlend 0x2C1A2F8, Control
  0x2C1C7D0, Effect 0x2C2CEC8, Ground 0x2C3A454, Hit 0x2C43610, Link 0x2C58578, Motion 0x2C6164C, Sound
  0x2C73C34 (vtable 0x1010BFB4).
- **Names**: CRC32 of the upper-case macro name equals the command hash. Candidate names were tested
  (Ultimate macro names, module vocabulary, 1-4 token combinations). A hit was only kept when it fits the
  handler; chance collisions (WALL_CURSOR_IMAGE3, WINDOW_VIS_FRM, ADD_PASSABLE_SP_MUL, ...) are listed as
  rejected.
- **Values**: every slot's vanilla histogram comes from all fighter ACMD in the dump (1053 files; 74 of the
  151 commands are used).
- **Conditions**: the compare type used by the condition commands indexes table 0x1035181C (int) or
  0x10351804 (float): 0 ==, 1 !=, 2 <=, 3 >=, 4 <, 5 >.

## Names fixed or found (hash verified)

| Hash | Current | Correct | Evidence |
|---|---|---|---|
| 08E67529 | Disallow_Vertical_Movement | CLR_SPEED | Kinetic op 7: clears one energy's speed |
| A160AB16 | Disallow_Horizontal_Movement | ENABLE_ENERGY | Kinetic op 0xB sets energy->enabled=1 (UNABLE_ENERGY, op 0xC, sets 0) |
| 3D2CFA86 | Low_Voice_Clip | PLAY_SEQUENCE | Same code as PLAY_SEQUENCE_DAMAGESTOP |
| 961521C4 | Slope_Full | SLOPE_INTP | Slope op 0x2711 (status, frames) |
| 51BF42D5 | unk | EFFECT_FLW_POS_NO_STOP | Effect vt+0x64, pos-only follow, no hitlag-stop flag |
| 524EF3F5 | unk | EFFECT_FLW_POS_UNSYNC_VIS | Same call with flags 0x408000 |
| D4FC6AC3 | unk | EFFECT_FLW_UNSYNC_VIS | Full follow, 0x408000 |
| D98926B9 | unk | EFFECT_FLW_POS_STR | Bone given by name, like EFFECT_FOLLOW_STR |
| D86F0143 | unk | EFFECT_FLW_POS_STRENGTH | EFFECT_FOLLOW_STRENGTH layout, op 0x2719 |
| E1D78BFB | unk | LAST_EFFECT_SET_OFFSET_TO_CAMERA_FLAT | Effect vt+0x2CC, LAST_EFFECT_SET_* block |
| E6181A6B | unk | LAST_EFFECT_SET_DISABLE_SYSTEM_SLOW | Effect vt+0x2BC |
| 8F27D612 | unk | LAST_PARTICLE_SET_COLOR | Effect vt+0x284 next to LAST_EFFECT_SET_COLOR |
| 687F9320 | unk | SET_PLAY_INHIVIT | Sound vt+0x204 (SE, frames) |
| 5FC8FA49 | unk | SET_TAKEOUT_SE | Sound vt+0x1CC |
| 5D5AF322 | unk | SET_TAKEOUT_SE_STATUS | Sound vt+0x1D4 |
| C7B586AF | unk | MII_HEAD_OFFSET (probable) | 3-token hit; command is only used by Mii fighters |

Outside this batch but hash-verified on the way (for whoever owns them): FC061097 External_Graphic =
EFFECT_FOLLOW, 089EBF6C External_Graphic_Effect2 = EFFECT_FLW_POS, 0EDC8BFD Graphic_Effect4 =
EFFECT_FOLLOW_NO_STOP, 54BA7357 Graphic_Effect6 = EFFECT_FOLLOW_ALPHA, D8B91949 Add/Subtract_Momentum =
SET_SPEED, 26E9C6BE Add/Set_Momentum2 = SET_SPEED_EX, 6D8D18B7 Disallow_Certain_Movements =
SUSPEND_ENERGY, 3D155C42 Enable_Certain_Movements = RESUME_ENERGY, 2D942090 Pickup_Item = PICKUP_ITEM,
965E035A Fire_Weapon = SHOOT_ITEM_BULLET, 83197B9A Set_Weight_Hitbox = ATTACK_SET_NO_WEIGHT_REACTION (probable; 4-token search hit),
E5751F0A Sound_Effect = PLAY_SE, FB98EE28 Transient_Sound_Effect = PLAY_STATUS, F920748A Stop_Sound_Effect
= STOP_SE, E022FE8A Sound_Effect3 = PLAY_LANDING_SE, F7016A91 Sound_Effect4 = PLAY_DOWN_SE.

Names marked "descriptive" in the table are proposals from the handler; their hashes did not match.

## Notable findings

- **SLOPE values are bit flags**: 1 top/body, 2 left leg, 4 right leg, 6 both legs, 9 = 1+8, 0 none.
  SLOPE_TOE takes one leg (2/4) and an angle limit (60 in most scripts).
- **Several unknowns are argument-count variants of a known op**: START_CHARGE with 2 or 6 physics joint
  ids (DK, Bowser, ROB smash holds), SET_SPEED_EX with 2 args, THROW_ITEM_OFFSET with 4,
  GENERATE_ARTICLE_ENABLE with 2/3, SHOOT_EXIST_ARTICLE with 2, IT_GET_NODE_POS with 3 or 7,
  IT_AI_MOVE / IT_AI_MOVE_BRAKE with extra bool flags, and STOP_SE_ALL / SET_VOLUME with an explicit last arg.
- **unk_92A88908 is byte-for-byte Set_Kinetic_Handler** (Kinetic op 0 → change kinetic type).
- **Voice-set condition**: unk_5121D3C3 picks win/appeal voice sub-scripts. Only fighters with two
  voice sets use it (Wii Fit M/F, Robin M/F, Ike, and the JP/EN-voiced characters).
  unk_7FCE1BCF picks Bowser Jr.'s per-Koopaling win sounds (0-7).
- **Bayonetta's dodge and Witch Time scripts**: unk_CD0C1CC9 is on at frame 1 and off at frame 5 in every
  dodge and in down special. This looks like the Witch Time trigger window.
- **No-op handlers** (arguments are ignored by the game): unk_A728E2C6, IT_MOVE, IT_CAMERA_OFFSET, and all
  four arguments of unk_F061A233 (plain THROW_ITEM op 7).
- CAM_OFFSET's first argument is a float, not an int. SA_SET's 2 is SITUATION_KIND_AIR.
  MOT_SET_RATE_W, SET_RATE_ARTICLE_W and FRAME_W read float work variables. SET_RATE_ARTICLE_V and
  unk_935AC2ED / unk_5961371C read the game's built-in value tables (0x103518A8 float, 0x10351880 int).

## Still unknown, and why

- **Fighter-specific ops** (unk_467A5ED5, 7002E722, E2E96674, F6218798, F7B97AC1, CD0C1CC9, 8B925A6C,
  B2E91D0C for Bayonetta; D014D5A8, D2B4D575 for Cloud; BE0C4A94, B3480157 for Mega Man; 55205F20): these
  send op 0x3E8-0x3EF to the fighter class's own MSC handler (object vt+0x21C). Each fighter has its own
  switch, and Bayonetta's could not be located without symbols. Labels come from script usage (low/medium).
- **Item-only commands on accessor+0xCC and the item kinetic functions** (0x303xxxx / 0x308Dxxxx): unused
  in fighter ACMD. The argument order is exact, but most semantics are inferred from the named sibling
  that calls the same function.
- **SoundModule overrides**: the base SoundModule vtable returns 0 for vt+0x23C/+0x244. The fighter
  override that holds the voice-set logic was not traced, so 5121D3C3/7FCE1BCF are labelled from usage.
- **Physics op meanings** (58E8478D op 2, BBB819D9 op 0xA, START_CHARGE floats): the PhysicsModule MSC
  handler was not found (it has no 0x27xx switch). The START_CHARGE float triples are labelled
  generically (low).
- Unused command families with an opaque callee: 56A2339E, B570C933, A3E0DE1B / B6C47C1B, 93857203 /
  E4824295, C76174F3, 8E016BA0, FE6B9F2F, DE950B48, C4AF2746, D5E769C4, FC1C2985, DD526C98, 8E3DBED5.

## All 151 commands

Slot confidence: H high, M medium, L low. Bold = hash-verified (or probable) macro name, put in the JSON `name` field; italic = descriptive label only (JSON `_descriptive_name`, `name` stays null). Full per-slot text (description, values with vanilla histograms, evidence) is in `tools/Sm4shCommand/param_labels.json`.

| Hash | Current name | Proposed name | Name status | Vanilla uses | What the handler does | Slots |
|---|---|---|---|---|---|---|
| 467A5ED5 | unk_467A5ED5 |  | unresolved (CRC hit WALL_CURSOR_IMAGE3 rejected: nonsense for this handler) | 1 | Bayonetta-only fighter command: sends agent-specific op 0x3EB with 1 arg to the fighter object (0x2BF2108 get object by id, 0x2BF019C -> object->vt+0x21C 'agent MSC command') | 0 flag (L) |
| 49E83F6F | unk_49E83F6F |  | unresolved | 0 | Item kinetic setter: KineticModule (item) 0x308D18C(word, vecA=(p1,p2), vecB=(p3,0)) | 0 mode (L); 1 x (M); 2 y (M); 3 x2 (L) |
| 50B5DFBD | unk_50B5DFBD | _START_CHARGE (2-joint form)_ (descriptive) | descriptive; hash not matched | 3 | PhysicsModule MSC op 7 = the same op START_CHARGE (C52B4328, CRC-verified) uses, with 8 args instead of 7: smash-charge physics (body swell/shake while holding a smash) | 0 rate_a1 (L); 1 rate_a2 (L); 2 rate_a3 (L); 3 rate_b1 (L); 4 rate_b2 (L); 5 rate_b3 (L); 6 joint1 (M); 7 joint2 (M) |
| 5121D3C3 | unk_5121D3C3 |  | descriptive; hash not matched (proposed IF_VOICE_TYPE) | 244 | Condition: SoundModule vt+0x23C(p0) compared (cmp p1) with p2, result stored for the following True/Else block. Used only by characters with two voice sets (Wii Fit M/F, Robin M/F, Ike PoR/RD, and the JP/EN-voiced Pit, Palutena, Lucina, Shulk, Bayonetta, Fox, Falco, Lucario, Meta Knight, Mewtwo, Sonic, Jigglypuff, Ryu, Little Mac) to pick the matching win/appeal voice sub-script | 0 voice_type (M); 1 compare (H); 2 value (H) |
| 51A2AD03 | unk_51A2AD03 | _SET_VOLUME (3-arg form)_ (descriptive) | descriptive; hash not matched | 0 | SoundModule vt+0xDC(p0, p1, p2): same method as SET_VOLUME (D9FDDCEC), which passes 0 as the third arg | 0 se (M); 1 volume (M); 2 frames (L) |
| 51BF42D5 | unk_51BF42D5 | **EFFECT_FLW_POS_NO_STOP** | CRC-verified, consistent with handler | 6 | EffectModule vt+0x64 (req_follow) with 'position only' (r8=1) and without the 0x8000 'stop with hitlag' flag that EFFECT_FLW_POS (089EBF6C) sets | 0 effect (H); 1 bone (H); 2 x (H); 3 y (H); 4 z (H); 5 rot_x (H); 6 rot_y (H); 7 rot_z (H); 8 scale (H); 9 terminate (H) |
| 51FA432A | unk_51FA432A |  | unresolved | 3 | EffectModule vt+0xB4(p0, p1): same method as EFFECT_REMOVE_ATTR (CCD48E8A, 1 arg); used by Zelda's dead scripts | 0 attr (M); 1 arg2 (L) |
| 524EF3F5 | unk_524EF3F5 | **EFFECT_FLW_POS_UNSYNC_VIS** | CRC-verified, consistent with handler | 32 | EffectModule vt+0x64, position-only follow (r8=1), flags 0x408000 (0x400000 = visibility not synced with the owner, 0x8000 stop with hitlag) | 0 effect (H); 1 bone (H); 2 x (H); 3 y (H); 4 z (H); 5 rot_x (H); 6 rot_y (H); 7 rot_z (H); 8 scale (H); 9 terminate (H) |
| 53F0D3E1 | unk_53F0D3E1 | _ARTICLE_VISIBILITY (3-arg form)_ (descriptive) | descriptive; hash not matched | 0 | ArticleModule MSC op 0x271C with 3 args (Article_Visibility 0202C138 uses the same op with 2) | 0 article (M); 1 state (M); 2 arg3 (L) |
| 55205F20 | unk_55205F20 |  | unresolved | 0 | fighter-specific op 0x14 (1 arg) sent to the fighter object; unused in vanilla ACMD | 0 value (L) |
| 56A2339E | unk_56A2339E |  | unresolved (CRC hit ENDIF_UNDO_SND rejected) | 0 | Item-only (accessor+0xCC) function 0x3030988(p0, p1, p2) | 0 id (L); 1 value1 (L); 2 value2 (L) |
| 585B1516 | unk_585B1516 | _GET_TRACE_TARGET_VEC (int form)_ (descriptive) | descriptive; hash not matched | 0 | GroundModule vt+0x4EC(p0) (same as GET_TRACE_TARGET_VEC FAC3816A) -> stores int(x) in variable p1 and int(y) in variable p2 (WorkModule MSC set_int) | 0 dist (L); 1 out_x_var (H); 2 out_y_var (H); 3 unused (H) |
| 58E8478D | unk_58E8478D |  | unresolved | 0 | PhysicsModule MSC op 2 with one float | 0 value (L) |
| 5961371C | unk_5961371C |  | descriptive; hash not matched (proposed FLOAT_VALUE_COMPARE) | 0 | Condition: compares two built-in float values: getter[p0] (cmp p1) getter[p2], via 0x2BFBF30 (table 0x103518A8) and float-compare 0x2BEE010 | 0 value_a (M); 1 compare (H); 2 value_b (M) |
| 5B23A4DE | unk_5B23A4DE | _SET_LR_ (descriptive) | descriptive; SET_LR/LR hashes do not match | 0 | PostureModule vt+0x124(float): the facing setter that STICK_LR (AC4919B5) calls with the stick direction | 0 lr (M) |
| 5D5AF322 | unk_5D5AF322 | **SET_TAKEOUT_SE_STATUS** | CRC-verified, consistent (SoundModule vt+0x1D4, next to SET_TAKEOUT_SE's vt+0x1CC) | 7 | Registers the item take-out sound for the current status only | 0 se (H) |
| 5DADD1BF | unk_5DADD1BF | _INT_VAR_COMPARE_VAR_ (descriptive) | descriptive; hash not matched | 0 | Condition: WorkModule get_int(p0) (cmp p1) get_int(p2) (vt+0x84 = get_int, as used by ADD_INT) | 0 var_a (H); 1 compare (H); 2 var_b (H) |
| 5DD6C56C | unk_5DD6C56C | _SLOPE_TOE (1-arg form)_ (descriptive) | descriptive; hash not matched | 0 | SlopeModule MSC op 0x2713 (same op as SLOPE_TOE) with only the slope-status argument | 0 slope_status (M) |
| 5FC8FA49 | unk_5FC8FA49 | **SET_TAKEOUT_SE** | CRC-verified, consistent (SoundModule vt+0x1CC) | 146 | Sets the sound played when the fighter takes an item/weapon out | 0 se (H) |
| 666B608E | unk_666B608E | _STOP_SE_ALL (1-arg form)_ (descriptive) | descriptive; hash not matched | 0 | SoundModule vt+0x124(p0, 0): STOP_SE_ALL (602DD264) calls the same method with p0 = 0 | 0 arg (L) |
| 687F9320 | unk_687F9320 | **SET_PLAY_INHIVIT** | CRC-verified, consistent (SoundModule vt+0x204) | 231 | Blocks re-playing a sound effect for some frames (used on step/brake sounds) | 0 se (H); 1 frames (H) |
| 6BA1B159 | unk_6BA1B159 | _IT_GET_NODE_POS (2D form)_ (descriptive) | descriptive; hash not matched | 0 | Item function 0x303F060(node, varX, varY, -1, 0,0,0): IT_GET_NODE_POS without Z output | 0 node (M); 1 out_x_var (H); 2 out_y_var (H) |
| 6CCC7540 | unk_6CCC7540 | _IT_GET_NODE_POS (offset form)_ (descriptive) | descriptive; IT_GET_NODE_POS_OFFSET does not match | 0 | Item function 0x303F060(node, varX, varY, varZ, offX, offY, offZ) | 0 node (M); 1 out_x_var (H); 2 out_y_var (H); 3 out_z_var (H); 4 offset_x (M); 5 offset_y (M); 6 offset_z (M) |
| 6CD94C77 | unk_6CD94C77 | _THROW_ITEM_OFFSET (4-arg form)_ (descriptive) | descriptive; hash not matched (CRC hit CAM_INVINCIBLE_CLOSEUP_CENTER rejected) | 12 | ItemModule MSC op 0x15 = THROW_ITEM_OFFSET's op, with 4 args; Sonic's heavy-item throws | 0 offset_x (M); 1 offset_y (M); 2 arg3 (L); 3 arg4 (L) |
| 7002E722 | unk_7002E722 |  | unresolved | 4 | Bayonetta-only fighter op 0x3EA (1 arg) | 0 flag (L) |
| 70498D78 | unk_70498D78 | _CAM_ZOOM_IN (6-arg form)_ (descriptive) | descriptive; hash not matched (CRC hit ARTICLE_REST_COLLISION_POSTURE rejected) | 3 | CameraModule vt+0xE4 (the zoom-in used by CAM_ZOOM_IN and Camera_Closeup) with an extra bool; Camera_Closeup passes 0 for that bool | 0 frames (M); 1 arg1 (L); 2 distance (M); 3 rot_x (M); 4 rot_y (M); 5 flag (L) |
| 73E2040C | unk_73E2040C | _AFTER_IMAGE (27-arg sword-trail form)_ (descriptive) | descriptive; hash not matched | 7 | EffectModule MSC op 0x2731 (the Sword_Glow / AFTER_IMAGE3_ON_WORK op) with one more trailing arg; reads WorkModule get_int too. Cloud only | 0 trail_effect (L); 1 trail_effect2 (L); 2 blur_length (M); 3 bone1 (M); 4 x1 (M); 5 y1 (M); 6 z1 (M); 7 bone2 (M); 8 x2 (M); 9 y2 (M); 10 z2 (M); 11 anchored (M); 12 effect (M); 13 bone3 (M); 14 ex (M); 15 ey (M); 16 ez (M); 17 erx (M); 18 ery (M); 19 erz (M); 20 size (M); 21 unk21 (L); 22 unk22 (L); 23 unk23 (L); 24 unk24 (L); 25 unk25 (L); 26 extra (L) |
| 78E846E0 | unk_78E846E0 | _IT_AI_MOVE (2-flag form)_ (descriptive) | descriptive; hash not matched | 0 | Item kinetic 0x308D0DC(10 floats, bool p10, bool p11, 1): IT_AI_MOVE passes 0, 0 for the two bools | 0 f0 (L); 1 f1 (L); 2 f2 (L); 3 f3 (L); 4 f4 (L); 5 f5 (L); 6 f6 (L); 7 f7 (L); 8 f8 (L); 9 f9 (L); 10 flag_a (M); 11 flag_b (M) |
| 7E977FAA | unk_7E977FAA | _START_CHARGE (6-joint form)_ (descriptive) | descriptive; hash not matched | 14 | PhysicsModule MSC op 7 (START_CHARGE) with 12 args: 6 charge floats + 6 joint ids. Bowser / Giga Bowser / ROB smash holds | 0 rate_a1 (L); 1 rate_a2 (L); 2 rate_a3 (L); 3 rate_b1 (L); 4 rate_b2 (L); 5 rate_b3 (L); 6 joint1 (M); 7 joint2 (M); 8 joint3 (M); 9 joint4 (M); 10 joint5 (M); 11 joint6 (M) |
| 7FCE1BCF | unk_7FCE1BCF | _IF_SOUND_VARIATION_ (descriptive) | descriptive; hash not matched | 25 | Condition: (SoundModule vt+0x244() == p0) (cmp p1) p2. Bowser Jr. picks the Koopaling-specific win sounds (0-7) with it; Little Mac final smash picks between two SEs | 0 variation (M); 1 compare (H); 2 value (H) |
| 8B925A6C | unk_8B925A6C |  | unresolved | 1 | AttackModule vt+0x4EC(p0, 1, 0); the attack-module 'all hitboxes' setter right after Set_Weight_All_Hitboxes (0x4E4 = ATTACK_SET_NO_WEIGHT_REACTION-style per-id at 0x4DC). Bayonetta d-smash | 0 value (L) |
| 8E016BA0 | unk_8E016BA0 |  | unresolved | 0 | EffectModule vt+0x1AC(2 words, 12 floats, 2 words); unused in vanilla | 0 effect (M); 1 bone (M); 2 x (L); 3 y (L); 4 z (L); 5 rot_x (L); 6 rot_y (L); 7 rot_z (L); 8 f8 (L); 9 f9 (L); 10 f10 (L); 11 f11 (L); 12 f12 (L); 13 f13 (L); 14 w14 (L); 15 w15 (L) |
| 8E3DBED5 | unk_8E3DBED5 |  | unresolved (CRC hit FT_BRAKE_CHANGER_LIMITED rejected) | 0 | accessor+0x74 module (unidentified; sits between SearchModule +0x70 and TurnModule +0x78) vt+0xDC(p0, 0x50000000). Handler is the first function in .text | 0 value (L) |
| 8F27D612 | unk_8F27D612 | **LAST_PARTICLE_SET_COLOR** | CRC-verified, consistent (EffectModule vt+0x284 next to LAST_EFFECT_SET_COLOR vt+0x27C) | 58 | Tints the particles of the last created effect | 0 r (H); 1 g (H); 2 b (H) |
| 92A88908 | unk_92A88908 | _CHANGE_KINETIC_ (descriptive) | descriptive; KINETIC_CHANGE/CHANGE_KINETIC do not match | 0 | KineticModule MSC op 0 = byte-for-byte the same handler as Set_Kinetic_Handler (E74D94EE): KineticModule vt+0xEC(p0) | 0 kinetic_type (H) |
| 935AC2ED | unk_935AC2ED | _EFFECT_FOLLOW (value form)_ (descriptive) | descriptive; hash not matched (CRC hit WINDOW_VIS_FRM rejected) | 1 | EffectModule MSC op 0x2712 (EFFECT_FOLLOW's op) with 12 args; last arg is an index into the built-in int-value table 0x10351880 (0x2BFBF18) whose value is passed on | 0 effect (H); 1 bone (H); 2 x (H); 3 y (H); 4 z (H); 5 rot_x (H); 6 rot_y (H); 7 rot_z (H); 8 scale (H); 9 terminate (M); 10 arg10 (L); 11 value_src (M) |
| 93857203 | unk_93857203 |  | unresolved | 0 | Item function 0x303F614(p0, p1, p2, -1, -1); E4824295 is the 2-arg form (p2 = -1) | 0 a (L); 1 b (L); 2 c (L) |
| 96E6DDC4 | unk_96E6DDC4 | _PICKUP_ITEM (3-arg form)_ (descriptive) | descriptive; hash not matched (CRC hit ADD_UP_ALPHA_GRAVITY rejected) | 0 | ItemModule MSC op 6 = PICKUP_ITEM's op (2D942090 is CRC-verified PICKUP_ITEM, 1 arg; Pickup_Item2 2 args) | 0 arg0 (M); 1 arg1 (L); 2 arg2 (L) |
| 9E3105F2 | unk_9E3105F2 | _EFFECT_FOLLOW_FLIP (work form)_ (descriptive) | descriptive; hash not matched | 16 | EffectModule MSC op 0x2739 (00559051 uses it with 14 args); reads WorkModule get_int; GFX right/left pair like the *_FLIP commands | 0 effect_r (H); 1 effect_l (H); 2 bone (H); 3 x (H); 4 y (H); 5 z (H); 6 rot_x (H); 7 rot_y (H); 8 rot_z (H); 9 scale (H); 10 terminate (M); 11 arg11 (L); 12 work_var (M) |
| A08B9A5A | unk_A08B9A5A |  | unresolved | 0 | Item kinetic 0x308D18C(p0, vecA=(p1, 0), default vecB) | 0 mode (L); 1 x (M) |
| A0FA2515 | unk_A0FA2515 | _IF_STATUS_SE_PLAYING_ (descriptive) | descriptive; hash not matched (CRC hit AFTER_CONTINUAL_TRAIL_LIMITED rejected) | 37 | Condition: SoundModule vt+0x214(se) = 1 when that SE is playing in the status-SE list (+0x428 table) (cmp p1) p2. Pit/Kirby/Bowser play a status SE only if it is not already playing | 0 se (H); 1 compare (H); 2 value (H) |
| A3E0DE1B | unk_A3E0DE1B |  | unresolved | 0 | Item function 0x303F18C(6 floats, 3 words); B6C47C1B is the same call with an explicit last float | 0 f0 (L); 1 f1 (L); 2 f2 (L); 3 f3 (L); 4 f4 (L); 5 f5 (L); 6 w6 (L); 7 w7 (L); 8 w8 (L) |
| A728E2C6 | unk_A728E2C6 |  | unresolved | 0 | No-op: the handler only skips its argument (same stub as IT_MOVE) | 0 unused (H) |
| A8DDAC53 | unk_A8DDAC53 |  | unresolved | 0 | SoundModule: two calls through the sound object with p0 and int(p1) | 0 se (L); 1 value (L) |
| AAE5133F | unk_AAE5133F | _IT_GET_NODE_ROT (3D form)_ (descriptive) | descriptive; hash not matched | 0 | Item function 0x303F8B0(node, varX, varY, varZ): IT_GET_NODE_ROT passes -1 for the 4th | 0 node (M); 1 out_x_var (M); 2 out_y_var (M); 3 out_z_var (M) |
| ACE34E4C | unk_ACE34E4C | _IT_AI_MOVE_BRAKE (flag form)_ (descriptive) | descriptive; hash not matched | 0 | Item kinetic 0x308D1DC((p0,p1), bool p2); IT_AI_MOVE_BRAKE passes false | 0 brake_x (M); 1 brake_y (M); 2 flag (M) |
| AE994DAF | unk_AE994DAF |  | unresolved | 38 | MotionModule MSC op 0x1E (MATERIAL_ANIM_SET_FRAME is 0x1C, MATERIAL_ANIM_SET_RATE 0x1D): a material-animation on/off switch | 0 enable (M) |
| B078C69A | unk_B078C69A | _IT_SCALE_ANIM (full form)_ (descriptive) | descriptive; hash not matched | 0 | Item function 0x303ED50(p0, p1, p2, p3, 1.0); IT_SCALE_ANIM(p0) passes (p0, -1, 0.001, 1.0, 1.0) | 0 frames (M); 1 arg1 (L); 2 scale_from (L); 3 scale_to (L) |
| B09F03B2 | unk_B09F03B2 |  | unresolved (4-token hit PLAY_Y_REG_BULLET rejected) | 3 | AttackModule vt+0x4CC(hitbox id, bool): per-hitbox flag setter (ATTACK_SET_ATTACK_LEVEL is 0x4C4). Lucas PK Thunder 2 | 0 hitbox_id (M); 1 flag (M) |
| B2E91D0C | unk_B2E91D0C |  | unresolved | 14 | MotionModule vt+0x2EC after 0x2E87A5C: same slot as FT_START_ADJUST_MOTION_FRAME (6A5DB458); Bayonetta attacks | 0 rate (L) |
| B3480157 | unk_B3480157 |  | unresolved | 1 | Mega Man fighter op 0x3E8 with 2 args (BE0C4A94 = same op with 3 args) | 0 part (L); 1 state (L) |
| B459AB04 | unk_B459AB04 | _GENERATE_ARTICLE_ENABLE (2-arg form)_ (descriptive) | descriptive; hash not matched | 0 | ArticleModule MSC op 0x2718 (GENERATE_ARTICLE_ENABLE) with 2 args | 0 article (M); 1 arg (L) |
| B570C933 | unk_B570C933 |  | unresolved | 0 | Item function 0x3033458(p0, p1, p2) | 0 w (L); 1 f1 (L); 2 f2 (L) |
| B6C47C1B | unk_B6C47C1B |  | unresolved | 0 | Item function 0x303F18C (6 floats, 3 words, float) - A3E0DE1B with an explicit last float (A3E0DE1B passes 1.0) | 0 f0 (L); 1 f1 (L); 2 f2 (L); 3 f3 (L); 4 f4 (L); 5 f5 (L); 6 w6 (L); 7 w7 (L); 8 w8 (L); 9 f9 (L) |
| B89F681C | unk_B89F681C |  | descriptive; hash not matched (proposed SUSPEND_ENERGY_ATTR) | 33 | KineticModule MSC op 0x271B -> vt+0xC4(bool p0, mask p1): for every kinetic energy whose attribute & p1, calls energy method 0x54 (p0 = 1) or 0x5C (p0 = 0) - suspend / resume by reserve attribute | 0 suspend (M); 1 attr_mask (M) |
| BBB819D9 | unk_BBB819D9 |  | unresolved | 82 | PhysicsModule MSC op 0xA (bool). Every fighter's expression script 0x88E566BC sets it 1 at frame 2 and 0 at frame 46 | 0 enable (M) |
| BE0C4A94 | unk_BE0C4A94 |  | unresolved | 72 | Mega Man fighter op 0x3E8 (3 args); expression scripts | 0 part (L); 1 state (L); 2 frames (L) |
| BFC0031F | unk_BFC0031F | _SHOOT_EXIST_ARTICLE (2-arg form)_ (descriptive) | descriptive; hash not matched | 8 | ArticleModule MSC op 0x271A (SHOOT_EXIST_ARTICLE) with 2 args; Wii Fit Sun Salutation shoot | 0 article (M); 1 arg (L) |
| BFCBE5FF | unk_BFCBE5FF | _GENERATE_ARTICLE_ENABLE (2-arg form, alt)_ (descriptive) | descriptive; hash not matched | 0 | ArticleModule MSC op 0x2718 with (p0, p1); B459AB04 builds the same call | 0 article (M); 1 arg (L) |
| C35E9B92 | unk_C35E9B92 | _GENERATE_ARTICLE_ENABLE (3-arg form)_ (descriptive) | descriptive; hash not matched | 4 | ArticleModule MSC op 0x2718 with 3 args; Mega Man neutral special | 0 article (M); 1 arg1 (L); 2 arg2 (L) |
| C4AF2746 | unk_C4AF2746 |  | unresolved (4-token hit rejected) | 0 | SoundModule vt+0x224(p0) (tail call) | 0 value (L) |
| C76174F3 | unk_C76174F3 |  | unresolved (CRC hit EFFECT_FLAG_AESTHETIC_HITBOXES rejected) | 0 | Item function 0x303F2E0(bool) | 0 flag (M) |
| C7B586AF | unk_C7B586AF | **MII_HEAD_OFFSET** | CRC match (3-token search); plausible: Mii fighters only, Mii-specific fighter op 0x3E8 | 196 | Mii head offset / rotation over time | 0 offset_a (L); 1 offset_b (L); 2 frames (M) |
| CA9052EB | unk_CA9052EB |  | unresolved (CRC hit AFTER_CLR_COMPARE_OVERLAYS rejected) | 0 | PostureModule vt+0x3C((x,y,z), 1): the position setter INIT_POS uses | 0 x (M); 1 y (M); 2 z (M) |
| CD0C1CC9 | unk_CD0C1CC9 |  | unresolved | 10 | Bayonetta fighter op 0x3EE: on (1) at frame 1 and off (0) at frame 5 of every dodge and of Witch Time (speciallw): the Witch Time trigger window | 0 enable (M) |
| D014D5A8 | unk_D014D5A8 |  | unresolved | 2 | Cloud fighter op 0x3EB (3 args); final smash | 0 effect (L); 1 arg1 (L); 2 arg2 (L) |
| D2B4D575 | unk_D2B4D575 |  | unresolved | 1 | Cloud fighter op 0x3EA (2 args) | 0 arg0 (L); 1 arg1 (L) |
| D3D9401B | unk_D3D9401B | _SET_SPEED_EX (2-arg form)_ (descriptive) | descriptive; hash not matched | 22 | KineticModule MSC op 0x2713 = SET_SPEED_EX's op (26E9C6BE is CRC-verified SET_SPEED_EX, 4 args) with only the 2 speeds | 0 speed_x (H); 1 speed_y (H) |
| D4FC6AC3 | unk_D4FC6AC3 | **EFFECT_FLW_UNSYNC_VIS** | CRC-verified, consistent | 47 | EffectModule vt+0x64 full follow (r8=0) with flags 0x408000 (unsynced visibility, stop with hitlag) | 0 effect (H); 1 bone (H); 2 x (H); 3 y (H); 4 z (H); 5 rot_x (H); 6 rot_y (H); 7 rot_z (H); 8 scale (H); 9 terminate (H) |
| D5E769C4 | unk_D5E769C4 |  | unresolved | 0 | ColorBlendModule MSC op 5 (one word); FLASH_OFF is op 0x2713, COL_PRI 0x271A | 0 value (L) |
| D78CAACC | unk_D78CAACC |  | unresolved | 0 | Item kinetic 0x308D18C(p0, vecA=(p1,p2), default vecB) | 0 mode (L); 1 x (M); 2 y (M) |
| D86F0143 | unk_D86F0143 | **EFFECT_FLW_POS_STRENGTH** | CRC-verified, consistent (same 12-arg layout and op family as EFFECT_FOLLOW_STRENGTH) | 0 | EffectModule MSC op 0x2719 (EFFECT_FOLLOW_STRENGTH is 0x2718) | 0 effect (H); 1 bone (H); 2 x (H); 3 y (H); 4 z (H); 5 rot_x (H); 6 rot_y (H); 7 rot_z (H); 8 scale (H); 9 strength (M); 10 terminate (M); 11 rate (L) |
| D8FF2A7F | unk_D8FF2A7F | _IT_AI_ROT (2-vector form)_ (descriptive) | descriptive; hash not matched | 0 | Item kinetic 0x308CF64(vecA=(p0,p1,p2), vecB=(p3,p4,p5)); IT_AI_ROT passes a default vector (0x10575A30) as vecB | 0 rot_x (M); 1 rot_y (M); 2 rot_z (M); 3 vec2_x (L); 4 vec2_y (L); 5 vec2_z (L) |
| D97D2806 | unk_D97D2806 | _IF_SE_PLAYING_ (descriptive) | descriptive; hash not matched | 0 | Condition: SoundModule vt+0x20C(se) = 1 when that SE (PLAY_SE list, +0xA4 table) is playing (cmp p1) p2 | 0 se (H); 1 compare (H); 2 value (H) |
| D98926B9 | unk_D98926B9 | **EFFECT_FLW_POS_STR** | CRC-verified, consistent (bone resolved from a string like EFFECT_FOLLOW_STR) | 0 | EffectModule vt+0x64, position-only follow, bone looked up via 0x2BEBC34/0x3083370 from p1 | 0 effect (H); 1 bone (H); 2 x (H); 3 y (H); 4 z (H); 5 rot_x (H); 6 rot_y (H); 7 rot_z (H); 8 scale (H); 9 terminate (H) |
| DD526C98 | unk_DD526C98 |  | unresolved (CRC hit CHANGE_VIS_ELSE_MUL rejected) | 0 | AttackModule MSC op 0x2721 with 2 args (copied straight from the script); neighbours: 0x2720 Move_Hitbox, 0x2723 ATK_WHOLE | 0 hitbox_id (L); 1 value (L) |
| DE950B48 | unk_DE950B48 |  | unresolved | 0 | SoundModule vt+0x254(p0): forwards to the global sound manager (0x102F7288 -> 0x3127E60) | 0 value (L) |
| E1D78BFB | unk_E1D78BFB | **LAST_EFFECT_SET_OFFSET_TO_CAMERA_FLAT** | CRC-verified, consistent (EffectModule vt+0x2CC in the LAST_EFFECT_SET_* block) | 66 | Pushes the last effect toward / away from the camera | 0 offset (H) |
| E1E1175A | unk_E1E1175A | _IT_AI_MOVE (1-flag form)_ (descriptive) | descriptive; hash not matched | 0 | Item kinetic 0x308D0DC(10 floats, bool p10, false, 1) | 0 f0 (L); 1 f1 (L); 2 f2 (L); 3 f3 (L); 4 f4 (L); 5 f5 (L); 6 f6 (L); 7 f7 (L); 8 f8 (L); 9 f9 (L); 10 flag_a (M) |
| E2A24D87 | unk_E2A24D87 | _RENEW_TRACE (result form)_ (descriptive) | descriptive; hash not matched | 0 | GroundModule vt+0x50C(p0, p1, bool p2, p4) = RENEW_TRACE's method, then stores the result in int variable p3 (WorkModule set_int) | 0 f0 (L); 1 f1 (L); 2 flag (M); 3 out_var (H); 4 arg (L) |
| E2E96674 | unk_E2E96674 |  | unresolved | 44 | Bayonetta fighter op 0x3EF (word, float, float); Bullet-Arts / bullet hitbox scripts list one per Extended_Special_Hitbox id | 0 ID (M); 1 length (L); 2 width (L) |
| E4824295 | unk_E4824295 |  | unresolved | 0 | Item function 0x303F614(p0, p1, -1, -1, -1) (2-arg form of 93857203) | 0 a (L); 1 b (L) |
| E59FB667 | unk_E59FB667 |  | unresolved | 1 | EffectModule vt+0x2E4 with one word (built into a stack struct with a default from 0x10575xxx); Rosalina side special | 0 value (L) |
| E6181A6B | unk_E6181A6B | **LAST_EFFECT_SET_DISABLE_SYSTEM_SLOW** | CRC-verified, consistent (EffectModule vt+0x2BC, LAST_EFFECT_SET_* block) | 0 | Makes the last effect ignore global slow-motion | 0 disable (H) |
| ED4B60E1 | unk_ED4B60E1 |  | descriptive; hash not matched (proposed IF_INT) | 0 | Condition: result = WorkModule get_int(p0) (true when the int variable is non-zero) | 0 var (H) |
| F061A233 | unk_F061A233 | _THROW_ITEM (4-arg form)_ (descriptive) | descriptive; hash not matched | 0 | ItemModule MSC op 7 (THROW_ITEM) with no arguments: all 4 script arguments are ignored | 0 unused0 (H); 1 unused1 (H); 2 unused2 (H); 3 unused3 (H) |
| F2C328A7 | unk_F2C328A7 | _SHOOT_ITEM_BULLET (1-arg form)_ (descriptive) | descriptive; hash not matched | 0 | ItemModule MSC op 0xB = SHOOT_ITEM_BULLET's op (965E035A, CRC-verified) with an argument | 0 arg (L) |
| F6218798 | unk_F6218798 |  | unresolved | 10 | Bayonetta fighter op 0x3EC (word, float, word); expression scripts of smash attacks and final | 0 frames (L); 1 value (L); 2 mode (L) |
| F7B97AC1 | unk_F7B97AC1 |  | unresolved | 18 | Bayonetta fighter op 0x3E9 (5 words); one per gun right after unk_1B41048C (Bullet Arts setup) | 0 gun (M); 1 arg1 (L); 2 arg2 (L); 3 arg3 (L); 4 frames (L) |
| FA435729 | unk_FA435729 | _EFFECT_FOLLOW_NO_STOP (work form)_ (descriptive) | descriptive; hash not matched | 1 | EffectModule MSC op 0x271A (EFFECT_FOLLOW_NO_STOP's op) with 11 args; last arg is an int variable read with WorkModule get_int | 0 effect (H); 1 bone (H); 2 x (H); 3 y (H); 4 z (H); 5 rot_x (H); 6 rot_y (H); 7 rot_z (H); 8 scale (H); 9 terminate (H); 10 work_var (M) |
| FC1C2985 | unk_FC1C2985 |  | unresolved | 0 | AttackModule vt+0x324(p0, 1, 0) (ATK_KEEP_RUMBLE is vt+0x32C) | 0 value (L) |
| FE6B9F2F | unk_FE6B9F2F |  | unresolved | 0 | EffectModule vt+0x1A4 (screen-effect block: Screen_Tint 0x19C, 8E016BA0 0x1AC, End_Screen_Tint 0x1B4) | 0 effect (M); 1 bone (M); 2 x (L); 3 y (L); 4 z (L); 5 rot_x (L); 6 rot_y (L); 7 rot_z (L); 8 f8 (L); 9 f9 (L); 10 f10 (L); 11 w11 (L); 12 flag (L) |
| 3CFB7580 | ADD_POS |  | name kept (ADD_POS) | 0 | PostureModule: pos = vt+0x44() + (p0,p1,p2) -> vt+0x4C (set pos) | 0 x (H); 1 y (H); 2 z (H) |
| 663DE182 | ADD_SPEED_NO_LIMIT |  | name kept (ADD_SPEED_NO_LIMIT) | 3 | KineticModule MSC op 0x271A(p0, p1): adds speed without clamping to the speed limit | 0 speed_x (M); 1 speed_y (M) |
| 08E67529 | Disallow_Vertical_Movement | **CLR_SPEED** | CRC-verified (current name Disallow_Vertical_Movement is wrong) | 1 | KineticModule MSC op 7: KineticModule vt+0x54(energy id) -> energy vt+0x24 (clear that energy's speed) | 0 energy (H) |
| A160AB16 | Disallow_Horizontal_Movement | **ENABLE_ENERGY** | CRC-verified (current name Disallow_Horizontal_Movement is wrong) | 24 | KineticModule MSC op 0xB: energy(p0)->enabled = 1; UNABLE_ENERGY (op 0xC) sets it to 0 | 0 energy (H) |
| 49610D3F | FRAME_W |  | name kept (FRAME_W) | 0 | Wait until the frame number stored in a float variable (WorkModule vt+0x44 = get_float) | 0 frame_var (H) |
| 2E9BD610 | FT_MOTION_ANGLE |  | name kept (FT_MOTION_ANGLE) | 40 | Fighter-level: gets the fighter's kinetic energy 0 (KineticModule vt+0x54(0), the motion energy) and calls 0x2E836D0(energy, angle, p1): rotates the animation-driven movement by an angle | 0 angle (H); 1 mode (L) |
| C7429968 | GET_TRACE_TARGET_POSTURE_POS |  | name kept (GET_TRACE_TARGET_POSTURE_POS) | 0 | GroundModule vt+0x4F4(p0) -> int(x) to variable p1, int(y) to variable p2 | 0 dist (L); 1 out_x_var (H); 2 out_y_var (H) |
| 6E417C5C | IT_AI_DIR_ROT_MODE |  | name kept (IT_AI_DIR_ROT_MODE) | 0 | Item kinetic 0x308D26C(p0) | 0 mode (M) |
| AA1ACDAF | IT_AI_MOVE |  | name kept (IT_AI_MOVE) | 0 | Item kinetic 0x308D0DC(10 floats, false, false, 1) | 0 f0 (L); 1 f1 (L); 2 f2 (L); 3 f3 (L); 4 f4 (L); 5 f5 (L); 6 f6 (L); 7 f7 (L); 8 f8 (L); 9 f9 (L) |
| 79CAF3BB | IT_AI_MOVE_BRAKE |  | name kept (IT_AI_MOVE_BRAKE) | 0 | Item kinetic 0x308D1DC((p0,p1), false) | 0 brake_x (M); 1 brake_y (M) |
| E69F056C | IT_AI_ROT |  | name kept (IT_AI_ROT) | 0 | Item kinetic 0x308CF64((p0,p1,p2), default vector) | 0 rot_x (M); 1 rot_y (M); 2 rot_z (M) |
| C6C035C6 | IT_CREATE_ANGLE_WITH_GRAVITY |  | name kept (IT_CREATE_ANGLE_WITH_GRAVITY) | 0 | Item function 0x30340D8(ItemID, p1, float var p2, float var p3, float var p4, RotX, RotY): the three 'Variable' args are float variables read through WorkModule | 0 ItemID (H); 1 arg1 (L); 2 Variable1 (H); 3 Variable2 (H); 4 Variable3 (H); 5 RotX (M); 6 RotY (M) |
| 7528A2BC | IT_GET_NODE_POS |  | name kept (IT_GET_NODE_POS) | 0 | Item function 0x303F060(node, varX, varY, varZ, 0, 0, 0): writes a node's position into float variables | 0 node (M); 1 out_x_var (H); 2 out_y_var (H); 3 out_z_var (H) |
| E8C8E371 | IT_GET_NODE_ROT |  | name kept (IT_GET_NODE_ROT) | 0 | Item function 0x303F8B0(node, var1, var2, -1) | 0 node (M); 1 out_x_var (M); 2 out_y_var (M) |
| 994CF8FF | IT_MOVE |  | name kept (IT_MOVE) | 0 | No-op: the handler only skips its argument | 0 unused (H) |
| A4826100 | IT_SCALE |  | name kept (IT_SCALE) | 0 | Item function 0x303EFC8(scale) | 0 scale (H) |
| A75BDF91 | IT_SCALE_ANIM |  | name kept (IT_SCALE_ANIM) | 0 | Item function 0x303ED50(p0, -1, 0.001, 1.0, 1.0): grows the item from 0.001 to 1.0 | 0 frames (M) |
| 2663C7BA | IT_SLOPE_TYPE |  | name kept (IT_SLOPE_TYPE) | 0 | Item kinetic 0x308D218(p0) | 0 slope_type (M) |
| AF988735 | SLOPE |  | name kept (SLOPE) | 10086 | SlopeModule MSC op 0x2710: slope (ground-angle) leg alignment status | 0 slope_status (H) |
| 961521C4 | Slope_Full | **SLOPE_INTP** | CRC-verified (current name Slope_Full) | 6151 | SlopeModule MSC op 0x2711: SLOPE with interpolation | 0 slope_status (H); 1 frames (H) |
| 74B61BAC | SLOPE_TOE |  | name kept (SLOPE_TOE, CRC-verified) | 51 | SlopeModule MSC op 0x2713(status, angle) | 0 slope_status (H); 1 max_angle (M) |
| 032C73B5 | SYNC_POS_NODE |  | name kept (SYNC_POS_NODE) | 0 | PostureModule vt+0x12C(p0) | 0 node (M) |
| 4E761504 | CAMERA_SET_UPDATE_POS |  | name kept (CAMERA_SET_UPDATE_POS) | 2 | CameraModule MSC op 0x2720(p0) | 0 mode (L) |
| 20DB2106 | CAM_OFFSET |  | name kept (CAM_OFFSET) | 14 | CameraModule MSC op 0x2712(p0, p1): both arguments are floats | 0 offset_x (M); 1 offset_y (M) |
| E940DCC2 | Camera_Closeup | _CAM_ZOOM_IN (5-arg form)_ (descriptive) | descriptive; hash not matched (Camera_Closeup is a tool name) | 51 | CameraModule vt+0xE4(ZoomTime, p1, Distance, (XRot, YRot), false) = the CAM_ZOOM_IN method | 0 ZoomTime (H); 1 arg1 (L); 2 Distance (H); 3 XRot (M); 4 YRot (M) |
| A8D82049 | ITEM_EMPTY_SE |  | name kept (ITEM_EMPTY_SE) | 8 | Fighter-level op 0x16 (2 args): sounds played when a shooting item is empty | 0 se1 (M); 1 se2 (M) |
| AFEA0B23 | IT_BASE_ROT |  | name kept (IT_BASE_ROT) | 0 | Item kinetic 0x308D274(vec3) | 0 rot_x (M); 1 rot_y (M); 2 rot_z (M) |
| D0344D95 | IT_CAMERA_OFFSET |  | name kept (IT_CAMERA_OFFSET) | 0 | No-op: the handler only skips its 2 arguments | 0 unused0 (H); 1 unused1 (H) |
| E0F4DA21 | IT_SET_COUNTER |  | name kept (IT_SET_COUNTER) | 0 | Writes p0 into the item's work block (+0x3C of WorkModule's first table) | 0 count (M) |
| 451797FF | IT_SET_ROT |  | name kept (IT_SET_ROT) | 0 | Writes (p0, p1, 0.0) into the posture rotation vector (PostureModule +0x58) and refreshes the model when it changed | 0 rot_x (M); 1 rot_y (M) |
| 3E6F2200 | IT_SET_SE |  | name kept (IT_SET_SE) | 0 | Stores p0 in the item work block at +0x70 | 0 se (M) |
| FB4AE8F4 | SET_TEAM_OWNER |  | name kept (SET_TEAM_OWNER) | 0 | Item function 0x303FA04(p0, p1) | 0 team (L); 1 arg (L) |
| 84730CC5 | MATERIAL_ANIM_SET_FRAME |  | name kept (MATERIAL_ANIM_SET_FRAME) | 36 | MotionModule MSC op 0x1C(frame) | 0 frame (H) |
| 3A52D8B7 | MATERIAL_ANIM_SET_RATE |  | name kept (MATERIAL_ANIM_SET_RATE) | 2 | MotionModule MSC op 0x1D(rate) | 0 rate (H) |
| 752E6714 | MOT_SET_RATE_W |  | name kept (MOT_SET_RATE_W) | 20 | MotionModule MSC op 4 (Set_Frame_Speed's op) with the rate read from a float variable | 0 rate_var (H) |
| 7F0F890E | PLAY_FLY_VOICE |  | name kept (PLAY_FLY_VOICE) | 255 | SoundModule vt+0xD4(p0, p1): damage-fly voice | 0 voice1 (M); 1 voice2 (M) |
| 3D2CFA86 | Low_Voice_Clip | **PLAY_SEQUENCE** | CRC-verified (current name Low_Voice_Clip) | 1668 | SoundModule vt+0x7C(seq, 0, 1); handler identical to PLAY_SEQUENCE_DAMAGESTOP | 0 sequence (H) |
| 40639C05 | PLAY_SEQUENCE_DAMAGESTOP |  | name kept (PLAY_SEQUENCE_DAMAGESTOP) | 3 | SoundModule vt+0x7C(seq, 0, 1) (same code as PLAY_SEQUENCE) | 0 sequence (H) |
| 3A775D26 | PLAY_SE_NO_3D |  | name kept (PLAY_SE_NO_3D) | 519 | SoundModule vt+0x5C(se) | 0 se (H) |
| B73EF69C | PLAY_SE_REMAIN |  | name kept (PLAY_SE_REMAIN) | 544 | SoundModule vt+0x54(se, 0, 1) (PLAY_SE / Sound_Effect uses the same method) | 0 se (H) |
| E06A5D00 | REG_LANDING_SE |  | name kept (REG_LANDING_SE) | 33 | SoundModule vt+0x144(se); PLAY_LANDING_SE_REG plays it | 0 se (H) |
| 42D70BB3 | SA_SET |  | name kept (SA_SET) | 64 | StatusModule vt+0xEC(kind, 0): set situation kind (also used by SET_AIR) | 0 situation (H) |
| A5187BBC | SET_CURSOR |  | name kept (SET_CURSOR) | 186 | Fighter-level op 0xA(bool): shows / hides the player cursor (pointer above the fighter) | 0 visible (M) |
| F885CB9C | SET_FRAME_ARTICLE |  | name kept (SET_FRAME_ARTICLE) | 3 | ArticleModule MSC op 0x271F(article, frame) | 0 article (H); 1 frame (H) |
| 395DA2D1 | SET_OFFSET_ARTICLE |  | name kept (SET_OFFSET_ARTICLE) | 2 | ArticleModule MSC op 0x272A(article, ?, ?, float) | 0 article (H); 1 arg1 (L); 2 arg2 (L); 3 offset (M) |
| F0005966 | SET_PITCH |  | name kept (SET_PITCH) | 0 | SoundModule vt+0xFC(se, pitch) | 0 se (H); 1 pitch (H) |
| 374A735E | SET_PITCH_STATUS |  | name kept (SET_PITCH_STATUS) | 0 | SoundModule vt+0x10C(pitch) | 0 pitch (H) |
| 19A86DA9 | SET_PITCH_STATUS_HANDLE |  | name kept (SET_PITCH_STATUS_HANDLE) | 0 | SoundModule vt+0x114(handle, pitch) | 0 handle (M); 1 pitch (H) |
| 7A34BE78 | SET_POS_ARTICLE |  | name kept (SET_POS_ARTICLE) | 1 | ArticleModule MSC op 0x2729(article, ?, x, y) | 0 article (H); 1 arg1 (L); 2 x (M); 3 y (M) |
| 2B62F859 | SET_RATE_ARTICLE |  | name kept (SET_RATE_ARTICLE) | 8 | ArticleModule MSC op 0x2720(article, rate) | 0 article (H); 1 rate (H) |
| 26ED10F4 | SET_RATE_ARTICLE_V |  | name kept (SET_RATE_ARTICLE_V) | 2 | ArticleModule MSC op 0x2720(article, value[p1]) with the rate taken from the built-in float-value table | 0 article (H); 1 value_src (M) |
| 51EA2062 | SET_RATE_ARTICLE_W |  | name kept (SET_RATE_ARTICLE_W) | 4 | ArticleModule MSC op 0x2720(article, get_float(var)) | 0 article (H); 1 rate_var (H) |
| FAE6FD8D | SET_ROT |  | name kept (SET_ROT) | 0 | PostureModule vt+0xA4(x, y, z) | 0 rot_x (H); 1 rot_y (H); 2 rot_z (H) |
| 46396A70 | SET_ROT_ARTICLE |  | name kept (SET_ROT_ARTICLE) | 1 | ArticleModule MSC op 0x272B(article, ?, rot_a, rot_b) | 0 article (H); 1 arg1 (L); 2 rot_a (M); 3 rot_b (M) |
| 1511931F | SET_SHADOW |  | name kept (SET_SHADOW) | 8 | ShadowModule vt+0x4C(bool) | 0 visible (H) |
| D9FDDCEC | SET_VOLUME |  | name kept (SET_VOLUME) | 0 | SoundModule vt+0xDC(se, volume, 0) | 0 se (H); 1 volume (H) |
| 83A45688 | VIS_RESET_DEFAULT |  | name kept (VIS_RESET_DEFAULT) | 1 | VisibilityModule MSC op 0x2715(group) | 0 group (H) |
| F4940C87 | VIS_SET_ARTICLE |  | name kept (VIS_SET_ARTICLE) | 28 | ArticleModule MSC op 0x271D(article, group, state) | 0 article (H); 1 group (M); 2 state (M) |
| 15F0023E | VIS_SET_DEFAULT |  | name kept (VIS_SET_DEFAULT) | 501 | VisibilityModule MSC op 0x2712(group, state): sets the default state of a mesh-visibility group (Model_Changer is op 0x2711) | 0 group (H); 1 state (H) |
