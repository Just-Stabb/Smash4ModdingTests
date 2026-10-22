# Non-damage hitbox-family ACMD commands: parameter map

Source: cross_f.rpx handlers (CRC → 0x100FAAB8 → handler table 0x10350ED8), the module code they call, and 1053 vanilla ACMD files. Every slot of every command is listed below. "old" is the acmd_info.json name and type, and is shown only when it differs. Confidence is H, M or L.

Key modules:
- AttackModule: accessor +0x50.
- HitModule: +0x58.
- ItemModule: +0x64.
- SearchModule: +0x70.
- GrabModule: +0xAC. Its vtable is 0x10106448 and its MSC handler is 0x02C32D58.
- Item agent: +0xCC.

## Throw_Specifier `DF057B20` (handler 0x2be6e88)
- **p0 Kind** (old: ID) [H]: Absolute-attack slot: 0 = throw, 1 = catch (the hit dealt while held, e.g. pummel-like / release). Ultimate: ATTACK_ABSOLUTE_KIND. *Values:* 710 uses: 1 x365, 0 x345. *Evidence:* MSC op 0x2716 -> AttackModule::set_abs (vtable +0x64, 0x02C08A3C): slot = [AM+0x48] + kind*0x98
- **p1 Part** (old: Bone) [H]: Hitbox group index (not a bone): stored at abs slot+0x88 and indexes the 0x174-byte group records like set_attack's part. Corrects "Bone". *Values:* 710 uses: 0 x702, 1 x8. *Evidence:* set_abs stores it at slot+0x88; group records [AM+0x14]/[AM+0x38] indexed by it
- **p2 Damage** [H]: Throw damage (%). *Values:* 710 uses: 3.0 x289, 4.0 x62, 5.0 x59, 2.0 x57, 6.0 x49, 8.0 x42, 10.0 x36, 7.0 x26 .... *Evidence:* +0x18
- **p3 Angle** [H]: Launch angle (361 = Sakurai angle). *Values:* 710 uses: 361 x396, 45 x72, 80 x26, 0 x26, 90 x23, 70 x17, 50 x13, 60 x10 .... *Evidence:* +0x20
- **p4 KBG** [H]: Knockback growth. *Values:* 710 uses: 100 x343, 80 x44, 50 x38, 60 x29, 65 x22, 10 x22, 110 x17, 90 x13 .... *Evidence:* +0x24
- **p5 WBKB** [H]: Weight-based (set) knockback. *Values:* 710 uses: 0 x671, 1 x34, 30 x3, 130 x1, 100 x1. *Evidence:* +0x28
- **p6 BKB** [H]: Base knockback. *Values:* 710 uses: 60 x218, 40 x130, 0 x65, 70 x53, 90 x40, 80 x38, 100 x34, 50 x26 .... *Evidence:* +0x2C
- **p7 Effect** [H]: Hit effect / element (collision attribute). *Values:* 710 uses: 0 x650, 2 x21, 21 x10, 26 x6, 19 x6, 5 x6, 3 x4, 37 x3 .... *Evidence:* +0x43
- **p8 Trip** (old: Unknown) [M]: Trip chance (+0x30). Vanilla 0.0, or 1.0 only on the intermediate hits of multi-hit throws (always together with Hitlag 0.0). Corrects "Unknown". *Values:* 710 uses: 0.0 x622, 1.0 x87, 0.5 x1. *Evidence:* stored at +0x30 = Special_Hitbox trip slot
- **p9 HitlagMult** (old: Hitlag) [H]: Hitlag (hitstop) multiplier. *Values:* 710 uses: 1.0 x608, 0.0 x101, 2.0 x1. *Evidence:* +0x34
- **p10 SDIMult** (old: Unknown) [M]: SDI multiplier (+0x38); 1.0 default, 0.0 on 8 throws. Corrects "Unknown". *Values:* 710 uses: 1.0 x702, 0.0 x8. *Evidence:* stored at +0x38 = Special_Hitbox SDI slot
- **p11 SFXLevel** [H]: Hit sound level (0 S, 1 M, 2 L, 3 LL). *Values:* 710 uses: 0 x620, 2 x73, 1 x16, 3 x1. *Evidence:* +0x44
- **p12 SFXType** [H]: Hit sound type (punch/kick/slash/...). *Values:* 710 uses: 0 x613, 2 x46, 3 x12, 8 x7, 49 x7, 50 x5, 11 x4, 5 x3 .... *Evidence:* +0x45
- **p13 FacingRestriction** [H]: Launch-direction restriction (+0x4F). *Values:* 710 uses: 3 x660, 0 x43, 4 x6, 1 x1. *Evidence:* +0x4F
- **p14 DisableHitlag** [H]: Bool (== 1): no hitstop at all on this hit. Vanilla 1 on almost every throw; 0 on one throw script (0xD72C4C6A) for many fighters and on the final-smash abs hits. *Values:* 710 uses: 1 x685, 0 x25. *Evidence:* +0x52; 0x02C2678C returns 0 hitstop when set
- **p15 NoReaction** (old: Unknown) [L]: Bool (== 1) -> the +0x53 field (Special_Hitbox "NoGFX" slot). When set, the victim's DamageModule skips a hit-reaction call (0x02C21F5C, 0x02C22CAC, 0x02C24270). Vanilla: 1 on 702 of 710 throws; 0 only on final-smash / command-grab abs hits (Sheik/Zelda/Pit-B finals, Bowser/Giga Bowser, Mewtwo, Meta Knight). *Values:* 710 uses: 1 x702, 0 x8. *Evidence:* +0x53 readers in DamageModule
- **p16 Type** [M]: Attack type (+0x55): normal / item / ...; drives what counts as the hit category. *Values:* 710 uses: 8 x567, 0 x137, 2 x6. *Evidence:* +0x55 (read at 0x02C093A0)

## Throw_Specifier2 `FAA85333` (handler 0x2bdb790)
- **p0 Kind** (old: ID) [H]: Absolute-attack slot: 0 = throw, 1 = catch (the hit dealt while held, e.g. pummel-like / release). Ultimate: ATTACK_ABSOLUTE_KIND. *Values:* 34 uses: 0 x27, 1 x6, 2 x1. *Evidence:* direct call to set_abs (no MSC); MSC op 0x2716 -> AttackModule::set_abs (vtable +0x64, 0x02C08A3C): slot = [AM+0x48] + kind*0x98
- **p1 Part** (old: Bone) [H]: Hitbox group index (not a bone): stored at abs slot+0x88 and indexes the 0x174-byte group records like set_attack's part. Corrects "Bone". *Values:* 34 uses: 0 x34. *Evidence:* direct call to set_abs (no MSC); set_abs stores it at slot+0x88; group records [AM+0x14]/[AM+0x38] indexed by it
- **p2 Damage** [H]: Throw damage (%). *Values:* 34 uses: 3.0 x6, 7.0 x6, 5.6 x4, 8.0 x3, 9.0 x3, 6.4 x2, 7.2 x2, 11.2 x2 .... *Evidence:* direct call to set_abs (no MSC); +0x18
- **p3 Angle** [H]: Launch angle (361 = Sakurai angle). *Values:* 34 uses: 361 x12, 45 x8, 85 x6, 70 x6, 280 x1, 60 x1. *Evidence:* direct call to set_abs (no MSC); +0x20
- **p4 KBG** [H]: Knockback growth. *Values:* 34 uses: 60 x18, 100 x7, 65 x5, 55 x1, 16 x1, 58 x1, 160 x1. *Evidence:* direct call to set_abs (no MSC); +0x24
- **p5 WBKB** [H]: Weight-based (set) knockback. *Values:* 34 uses: 0 x34. *Evidence:* direct call to set_abs (no MSC); +0x28
- **p6 BKB** [H]: Base knockback. *Values:* 34 uses: 50 x7, 80 x7, 40 x6, 65 x6, 60 x6, 45 x1, 90 x1. *Evidence:* direct call to set_abs (no MSC); +0x2C
- **p7 Effect** [H]: Hit effect / element (collision attribute). *Values:* 34 uses: 0 x18, 5 x8, 3 x4, 19 x4. *Evidence:* direct call to set_abs (no MSC); +0x43
- **p8 Trip** (old: Unknown) [declared int, really float] [M]: Trip chance (+0x30). Vanilla 0.0, or 1.0 only on the intermediate hits of multi-hit throws (always together with Hitlag 0.0). Corrects "Unknown". acmd_info declares it int: must be float (format bug). *Values:* 34 uses: 0.0 x33, 1.0 x1. *Evidence:* direct call to set_abs (no MSC); stored at +0x30 = Special_Hitbox trip slot
- **p9 HitlagMult** (old: Hitlag) [H]: Hitlag (hitstop) multiplier. *Values:* 34 uses: 1.0 x30, 0.0 x4. *Evidence:* direct call to set_abs (no MSC); +0x34
- **p10 SDIMult** (old: Unknown) [M]: SDI multiplier (+0x38); 1.0 default, 0.0 on 8 throws. Corrects "Unknown". *Values:* 34 uses: 1.0 x31, 0.0 x3. *Evidence:* direct call to set_abs (no MSC); stored at +0x38 = Special_Hitbox SDI slot
- **p11 SFXLevel** [H]: Hit sound level (0 S, 1 M, 2 L, 3 LL). *Values:* 34 uses: 0 x28, 2 x6. *Evidence:* direct call to set_abs (no MSC); +0x44
- **p12 SFXType** [H]: Hit sound type (punch/kick/slash/...). *Values:* 34 uses: 0 x30, 8 x4. *Evidence:* direct call to set_abs (no MSC); +0x45
- **p13 FacingRestriction** [H]: Launch-direction restriction (+0x4F). *Values:* 34 uses: 3 x33, 0 x1. *Evidence:* direct call to set_abs (no MSC); +0x4F
- **p14 DisableHitlag** [H]: Raw value (not compared to 1) -> +0x52: no hitstop when nonzero. *Values:* 34 uses: 1 x33, 0 x1. *Evidence:* direct call to set_abs (no MSC); +0x52; 0x02C2678C returns 0 hitstop when set
- **p15 NoReaction** (old: Unknown) [L]: Raw value -> +0x53 (see Throw_Specifier p15). *Values:* 34 uses: 1 x34. *Evidence:* direct call to set_abs (no MSC); +0x53 readers in DamageModule
- **p16 Type** [M]: Attack type (+0x55). Throw_Specifier2 additionally forces +0x50 = 1 (the Special_Hitbox unknown slot-35 field). *Values:* 34 uses: 8 x31, 0 x3. *Evidence:* direct call to set_abs (no MSC); +0x55 (read at 0x02C093A0)

## Intensity_Throw_Specifier `321297B0` (handler 0x2bdb8c8)
- **p0 Kind** (old: ID) [H]: Absolute-attack slot: 0 = throw, 1 = catch (the hit dealt while held, e.g. pummel-like / release). Ultimate: ATTACK_ABSOLUTE_KIND. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* MSC op 0x2716 -> AttackModule::set_abs (vtable +0x64, 0x02C08A3C): slot = [AM+0x48] + kind*0x98
- **p1 Part** (old: Bone) [H]: Hitbox group index (not a bone): stored at abs slot+0x88 and indexes the 0x174-byte group records like set_attack's part. Corrects "Bone". *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* set_abs stores it at slot+0x88; group records [AM+0x14]/[AM+0x38] indexed by it
- **p2 Damage** [H]: Damage at intensity 0. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* +0x18 lerp
- **p3 Damage2** [H]: Damage at intensity 1. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* lerp(p2,p3,I)
- **p4 Angle** [H]: Launch angle (361 = Sakurai angle). *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* +0x20
- **p5 KBG** [H]: KBG at intensity 0. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* lerp
- **p6 KBG2** [declared float, really int] [H]: KBG at intensity 1. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* lerp
- **p7 WBKB** [H]: WBKB at intensity 0. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* lerp
- **p8 WBKB2** [declared float, really int] [H]: WBKB at intensity 1. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* lerp
- **p9 BKB** [H]: BKB at intensity 0. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* lerp
- **p10 BKB2** [declared float, really int] [H]: BKB at intensity 1. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* lerp
- **p11 Effect** (old: Effect?) [H]: Hit effect / element (collision attribute). *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* +0x43
- **p12 Trip** (old: Unknown) [M]: Trip chance (+0x30). Vanilla 0.0, or 1.0 only on the intermediate hits of multi-hit throws (always together with Hitlag 0.0). Corrects "Unknown". *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* stored at +0x30 = Special_Hitbox trip slot
- **p13 HitlagMult** (old: Hitlag) [H]: Hitlag (hitstop) multiplier. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* +0x34
- **p14 SDIMult** (old: Unknown) [M]: SDI multiplier (+0x38); 1.0 default, 0.0 on 8 throws. Corrects "Unknown". *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* stored at +0x38 = Special_Hitbox SDI slot
- **p15 SFXLevel** [H]: Hit sound level (0 S, 1 M, 2 L, 3 LL). *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* +0x44
- **p16 SFXType** [H]: Hit sound type (punch/kick/slash/...). *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* +0x45
- **p17 FacingRestriction** [H]: Launch-direction restriction (+0x4F). *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* +0x4F
- **p18 DisableHitlag** [H]: Bool (== 1): no hitstop at all on this hit. Vanilla 1 on almost every throw; 0 on one throw script (0xD72C4C6A) for many fighters and on the final-smash abs hits. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* +0x52; 0x02C2678C returns 0 hitstop when set
- **p19 NoReaction** (old: Type) [M]: Bool -> +0x53 (see Throw_Specifier p15). Corrects "Type" (acmd_info has Type one slot early). *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* +0x53
- **p20 Type** (old: Unknown) [H]: Attack type (+0x55). Corrects "Unknown". *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* +0x55
- **p21 IntensityVar** (old: Unknown) [H]: WorkModule FLOAT variable ID read with get_float; when != 0 every pair (Damage, KBG, WBKB, BKB) is interpolated by that variable (0..1). Corrects "Unknown". *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* WorkModule vtable +0x44 get_float(var)
- **p22 Unk50** (old: Unknown) [L]: Written to the +0x50 attack field (Special_Hitbox unknown slot 35; Throw_Specifier2 forces it to 1). No reader found in the attack/damage modules: meaning still unknown. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* stb +0x50

## Throw_Applier `D8DF1DCC` (handler 0x2be6fcc)
- **p0 Kind** (old: ID) [H]: Absolute-attack slot to apply (0 throw, 1 catch, 2 used once) - must match a Throw_Specifier Kind. *Values:* 289 uses: 0 x288, 2 x1. *Evidence:* MSC op 0x271D -> AttackModule hit_absolute
- **p1 Bone** [H]: Joint whose world position is the hit position (ModelModule get_joint_global_pos). 26 = throw joint on fighters. *Values:* 289 uses: 26 x286, 0 x3. *Evidence:* ModelModule vtable +0xEC
- **p2 TargetObjectVar** (old: Unknown) [H]: WorkModule INT variable holding the grabbed opponent's object ID (standard 0x11000005). *Values:* 289 uses: 0x11000005 x276, 0x11000003 x4, 0x1100000b x3, 0x11000009 x3, 0x11000008 x2, 0x11000002 x1. *Evidence:* WorkModule get_int(var); Ultimate ATK_HIT_ABS target
- **p3 TargetHitGroupVar** (old: Unknown) [H]: WorkModule INT variable holding the opponent's hit (hurtbox) group (standard 0x11000006). *Values:* 289 uses: 0x11000006 x276, 0x11000004 x4, 0x1100000c x3, 0x1100000a x3, 0x11000009 x2, 0x11000003 x1. *Evidence:* get_int(var)
- **p4 TargetHitNoVar** (old: Unknown) [H]: WorkModule INT variable holding the opponent's hit (hurtbox) number (standard 0x11000007). *Values:* 289 uses: 0x11000007 x276, 0x11000005 x4, 0x1100000d x3, 0x1100000b x3, 0x1100000a x2, 0x11000004 x1. *Evidence:* get_int(var)

## Special_Throw_Applier `CDBE8A34` (handler 0x2bdb69c)
- **p0 Kind** (old: ID) [H]: Absolute-attack slot to apply (0 throw, 1 catch, 2 used once) - must match a Throw_Specifier Kind. *Values:* 24 uses: 0 x24. *Evidence:* direct AttackModule::hit_absolute call (no MSC); MSC op 0x271D -> AttackModule hit_absolute
- **p1 Bone** [H]: Joint whose world position is the hit position (ModelModule get_joint_global_pos). 26 = throw joint on fighters. Specials use 2009 (the special-throw joint). *Values:* 24 uses: 2009 x24. *Evidence:* direct AttackModule::hit_absolute call (no MSC); ModelModule vtable +0xEC
- **p2 TargetObjectVar** (old: Unknown) [H]: WorkModule INT variable with the target object ID (specials: 0x11000001). *Values:* 24 uses: 0x11000001 x24. *Evidence:* direct AttackModule::hit_absolute call (no MSC); WorkModule get_int(var); Ultimate ATK_HIT_ABS target
- **p3 TargetHitGroupVar** (old: Unknown) [H]: WorkModule INT variable with the target hit group (specials: 0x11000002). *Values:* 24 uses: 0x11000002 x24. *Evidence:* direct AttackModule::hit_absolute call (no MSC); get_int(var)
- **p4 TargetHitNoVar** (old: Unknown) [H]: WorkModule INT variable with the target hit number (specials: 0x11000003). *Values:* 24 uses: 0x11000003 x24. *Evidence:* direct AttackModule::hit_absolute call (no MSC); get_int(var)

## Intensity_Throw_Applier `5C44F13A` (handler 0x2bdb38c)
- **p0 Kind** (old: ID) [H]: Absolute-attack slot to apply (0 throw, 1 catch, 2 used once) - must match a Throw_Specifier Kind. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* MSC op 0x271D -> AttackModule hit_absolute
- **p1 Bone** [H]: Joint whose world position is the hit position (ModelModule get_joint_global_pos). 26 = throw joint on fighters. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* ModelModule vtable +0xEC
- **p2 TargetObjectVar** (old: Unknown) [H]: WorkModule INT variable holding the grabbed opponent's object ID (standard 0x11000005). *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* WorkModule get_int(var); Ultimate ATK_HIT_ABS target
- **p3 TargetHitGroup** (old: Unknown) [M]: Literal hit group number (not a variable, unlike Throw_Applier). *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* passed straight through
- **p4 TargetHitNoVar** (old: Unknown) [H]: WorkModule INT variable holding the opponent's hit (hurtbox) number (standard 0x11000007). *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* get_int(var)

## Grab_Collision `548F2D4C` (handler 0x2bd74c8)
- **p0 ID** [H]: Grab box id (0..). *Values:* 60 uses: 0 x26, 1 x20, 2 x13, 3 x1. *Evidence:* GrabModule MSC 0x02C32D58 op 0x2710 -> parser 0x02C32C18 -> GrabModule set (vtable +0x4C, 0x02C32580); slot = [GM+0xC] + id*0x2C
- **p1 Bone** [H]: Joint the box follows (0x3F0 is remapped to 26 for some kinds in Grab_Collision2). *Values:* 60 uses: 26 x25, 23 x17, 0 x12, 1008 x6. *Evidence:* data+0x1C (half)
- **p2 Size** [H]: Radius (scaled by the fighter's scale). *Values:* 60 uses: 4.0 x12, 2.8 x11, 3.0 x7, 1.5 x7, 3.5 x5, 2.5 x5, 1.8 x5, 5.5 x3 .... *Evidence:* data+0x18; scaled by GM+0x24*GM+0x2C
- **p3 X** [H]: Offset X. *Values:* 60 uses: 0.0 x54, -2.0 x3, 1.2 x3. *Evidence:* data+0x00
- **p4 Y** [H]: Offset Y. *Values:* 60 uses: 0.0 x42, 6.6 x9, -0.5 x6, 6.0 x3. *Evidence:* data+0x04
- **p5 Z** [H]: Offset Z. *Values:* 60 uses: 0.0 x37, 10.7 x2, 17.0 x2, 24.0 x2, -1.0 x2, 2.5 x2, -3.2 x2, 1.3 x2 .... *Evidence:* data+0x08
- **p6 TargetStatus** (old: Action) [M]: Status kind the grabbed target is put in (63 = normal grab pull; command grabs use their own capture statuses, e.g. Bowser 190, Falcon 189, Ganon 184-186, Kirby/Dedede 223). Ultimate CATCH status argument. *Values:* 60 uses: 63 x51, 238 x9. *Evidence:* data+0x1E (half); matches Ultimate CATCH(status, situation)
- **p7 SituationMask** (old: Ground/Air) [H]: Target situation mask: 1 ground, 2 air, 3 both. Ultimate COLLISION_SITUATION_MASK. *Values:* 60 uses: 3 x46, 1 x10, 2 x4. *Evidence:* data+0x22 -> filter word bits 13-15

## Grab_Collision2 `1EAF840C` (handler 0x2bd77b4)
- **p0 ID** [H]: Grab box id (0..). *Values:* 73 uses: 0 x38, 1 x31, 2 x3, 3 x1. *Evidence:* GrabModule MSC 0x02C32D58 op 0x2710 -> parser 0x02C32C18 -> GrabModule set (vtable +0x4C, 0x02C32580); slot = [GM+0xC] + id*0x2C
- **p1 Bone** [H]: Joint the box follows (0x3F0 is remapped to 26 for some kinds in Grab_Collision2). *Values:* 73 uses: 0 x55, 19 x6, 24 x4, 16 x4, 1008 x4. *Evidence:* data+0x1C (half)
- **p2 Size** [H]: Radius (scaled by the fighter's scale). *Values:* 73 uses: 5.0 x11, 3.0 x7, 4.0 x5, 4.5 x4, 2.5 x4, 6.0 x3, 7.0 x3, 4.2 x3 .... *Evidence:* data+0x18; scaled by GM+0x24*GM+0x2C
- **p3 X** [H]: Offset X. *Values:* 73 uses: 0.0 x59, -2.0 x8, -1.0 x4, -0.9 x2. *Evidence:* data+0x00
- **p4 Y** [H]: Offset Y. *Values:* 73 uses: 8.0 x14, 0.0 x8, 6.0 x7, 10.0 x6, 2.0 x5, 7.0 x5, 9.0 x4, -0.5 x4 .... *Evidence:* data+0x04
- **p5 Z** [H]: Offset Z. *Values:* 73 uses: 1.0 x13, 0.0 x4, 11.0 x4, 17.0 x4, 1.5 x3, 5.0 x3, 3.0 x3, 10.0 x3 .... *Evidence:* data+0x08
- **p6 TargetStatus** (old: Action) [M]: Status kind the grabbed target is put in (63 = normal grab pull; command grabs use their own capture statuses, e.g. Bowser 190, Falcon 189, Ganon 184-186, Kirby/Dedede 223). Ultimate CATCH status argument. *Values:* 73 uses: 63 x12, 190 x10, 223 x9, 230 x6, 236 x6, 184 x6, 246 x6, 233 x4 .... *Evidence:* data+0x1E (half); matches Ultimate CATCH(status, situation)
- **p7 SituationMask** (old: Ground/Air) [H]: Target situation mask: 1 ground, 2 air, 3 both. Ultimate COLLISION_SITUATION_MASK. *Values:* 73 uses: 3 x39, 1 x19, 2 x15. *Evidence:* data+0x22 -> filter word bits 13-15
- **p8 CanGrabInvincible** (old: Unknown) [M]: Bool: 1 (all vanilla uses) keeps the default target hit-status mask 3; 0 passes 2 to the parser, which clears bit 1 (mask = 1, only "normal" hurtboxes - an invincible/out-of-normal-state target cannot be grabbed). *Values:* 73 uses: 1 x73. *Evidence:* handler: arr[9] = (p8 ? 0 : 2); parser +0x20 = 3 & ~arr[9] -> filter word hit-status bits

## Grab_Collision3 `323FB9D4` (handler 0x2bd6c74)
- **p0 ID** (old: Part) [H]: Grab box id (0..). *Values:* 6 uses: 0 x6. *Evidence:* GrabModule MSC 0x02C32D58 op 0x2710 -> parser 0x02C32C18 -> GrabModule set (vtable +0x4C, 0x02C32580); slot = [GM+0xC] + id*0x2C
- **p1 Bone** [H]: Joint the box follows (0x3F0 is remapped to 26 for some kinds in Grab_Collision2). *Values:* 6 uses: 2001 x6. *Evidence:* data+0x1C (half)
- **p2 Size** [H]: Radius (scaled by the fighter's scale). *Values:* 6 uses: 3.0 x5, 3.5 x1. *Evidence:* data+0x18; scaled by GM+0x24*GM+0x2C
- **p3 X** [H]: Offset X. *Values:* 6 uses: 0.0 x6. *Evidence:* data+0x00
- **p4 Y** [H]: Offset Y. *Values:* 6 uses: 1.0 x6. *Evidence:* data+0x04
- **p5 Z** [H]: Offset Z. *Values:* 6 uses: 1.0 x6. *Evidence:* data+0x08
- **p6 TargetStatus** (old: HitBits) [M]: Status kind the grabbed target is put in (63 = normal grab pull; command grabs use their own capture statuses, e.g. Bowser 190, Falcon 189, Ganon 184-186, Kirby/Dedede 223). Ultimate CATCH status argument. *Values:* 6 uses: 63 x6. *Evidence:* data+0x1E (half); matches Ultimate CATCH(status, situation)
- **p7 SituationMask** (old: Air/Ground) [H]: Target situation mask: 1 ground, 2 air, 3 both. Ultimate COLLISION_SITUATION_MASK. *Values:* 6 uses: 3 x6. *Evidence:* data+0x22 -> filter word bits 13-15
- **p8 HitStatusExclude** (old: unknown) [M]: Bits removed from the target hit-status mask (default 3): mask = 3 & ~value. 0 in vanilla (Pikmin). Corrects "unknown". *Values:* 6 uses: 0 x6. *Evidence:* parser: +0x20 = 3 & ~arr[9]
- **p9 Flag26** (old: unknown) [L]: Bool stored in grab data +0x26 (also set by Extended_Grab_Collision2 p11). Its reader was not found; vanilla 0. *Values:* 6 uses: 0 x6. *Evidence:* parser: +0x26 = (arr[10] != 0) when count >= 11

## Extended_Grab_Collision `7B48FE1C` (handler 0x2bd790c)
- **p0 ID** [H]: Grab box id (0..). *Values:* 174 uses: 0 x171, 1 x3. *Evidence:* GrabModule MSC 0x02C32D58 op 0x2710 -> parser 0x02C32C18 -> GrabModule set (vtable +0x4C, 0x02C32580); slot = [GM+0xC] + id*0x2C
- **p1 Bone** [H]: Joint the box follows (0x3F0 is remapped to 26 for some kinds in Grab_Collision2). *Values:* 174 uses: 0 x168, 1 x3, 26 x3. *Evidence:* data+0x1C (half)
- **p2 Size** [H]: Radius (scaled by the fighter's scale). *Values:* 174 uses: 3.3 x40, 2.6 x21, 3.0 x18, 3.1 x16, 2.5 x11, 3.8 x10, 4.0 x9, 3.7 x6 .... *Evidence:* data+0x18; scaled by GM+0x24*GM+0x2C
- **p3 X** [H]: Offset X. *Values:* 174 uses: 0.0 x174. *Evidence:* data+0x00
- **p4 Y** [H]: Offset Y. *Values:* 174 uses: 8.0 x41, 6.6 x39, 7.0 x29, 6.0 x14, 9.0 x10, 8.5 x8, 5.0 x7, 5.5 x6 .... *Evidence:* data+0x04
- **p5 Z** [H]: Offset Z. *Values:* 174 uses: 4.0 x103, -4.0 x51, 5.0 x3, 13.0 x2, -5.0 x2, 8.0 x2, 4.5 x2, 0.5 x2 .... *Evidence:* data+0x08
- **p6 TargetStatus** (old: Action) [M]: Status kind the grabbed target is put in (63 = normal grab pull; command grabs use their own capture statuses, e.g. Bowser 190, Falcon 189, Ganon 184-186, Kirby/Dedede 223). Ultimate CATCH status argument. *Values:* 174 uses: 63 x174. *Evidence:* data+0x1E (half); matches Ultimate CATCH(status, situation)
- **p7 SituationMask** (old: Ground/Air) [H]: Target situation mask: 1 ground, 2 air, 3 both. Ultimate COLLISION_SITUATION_MASK. *Values:* 174 uses: 3 x174. *Evidence:* data+0x22 -> filter word bits 13-15
- **p8 X2** [H]: Capsule end X (makes the box a capsule, shape type 2). *Values:* 174 uses: 0.0 x174. *Evidence:* op 0x2714: data+0x0C, shape +0x25 = 2
- **p9 Y2** [H]: Capsule end Y. *Values:* 174 uses: 8.0 x41, 6.6 x39, 7.0 x29, 6.0 x15, 9.0 x10, 8.5 x8, 5.0 x7, 5.5 x6 .... *Evidence:* data+0x10
- **p10 Z2** [H]: Capsule end Z. *Values:* 174 uses: -14.7 x16, 8.7 x15, 10.6 x14, 11.5 x5, 9.3 x4, 10.7 x4, -5.0 x4, 9.7 x4 .... *Evidence:* data+0x14

## Extended_Grab_Collision2 `EF787D43` (handler 0x2bd79c0)
- **p0 ID** [H]: Grab box id (0..). *Values:* 3 uses: 0 x3. *Evidence:* GrabModule MSC 0x02C32D58 op 0x2710 -> parser 0x02C32C18 -> GrabModule set (vtable +0x4C, 0x02C32580); slot = [GM+0xC] + id*0x2C
- **p1 Bone** [H]: Joint the box follows (0x3F0 is remapped to 26 for some kinds in Grab_Collision2). *Values:* 3 uses: 0 x3. *Evidence:* data+0x1C (half)
- **p2 Size** [H]: Radius (scaled by the fighter's scale). *Values:* 3 uses: 3.6 x2, 2.9 x1. *Evidence:* data+0x18; scaled by GM+0x24*GM+0x2C
- **p3 X** [H]: Offset X. *Values:* 3 uses: 0.0 x3. *Evidence:* data+0x00
- **p4 Y** [H]: Offset Y. *Values:* 3 uses: 6.6 x3. *Evidence:* data+0x04
- **p5 Z** [H]: Offset Z. *Values:* 3 uses: 4.5 x1, -3.8 x1, 4.0 x1. *Evidence:* data+0x08
- **p6 TargetStatus** (old: Action) [M]: Status kind the grabbed target is put in (63 = normal grab pull; command grabs use their own capture statuses, e.g. Bowser 190, Falcon 189, Ganon 184-186, Kirby/Dedede 223). Ultimate CATCH status argument. *Values:* 3 uses: 63 x3. *Evidence:* data+0x1E (half); matches Ultimate CATCH(status, situation)
- **p7 SituationMask** (old: Ground/Air) [H]: Target situation mask: 1 ground, 2 air, 3 both. Ultimate COLLISION_SITUATION_MASK. *Values:* 3 uses: 3 x3. *Evidence:* data+0x22 -> filter word bits 13-15
- **p8 X2** [H]: Capsule end X (makes the box a capsule, shape type 2). *Values:* 3 uses: 0.0 x3. *Evidence:* op 0x2714: data+0x0C, shape +0x25 = 2
- **p9 Y2** [H]: Capsule end Y. *Values:* 3 uses: 6.6 x3. *Evidence:* data+0x10
- **p10 Z2** [H]: Capsule end Z. *Values:* 3 uses: 10.5 x1, -14.4 x1, 8.4 x1. *Evidence:* data+0x14
- **p11 Flag26** (old: unknown) [L]: Bool -> grab data +0x26 (same field as Grab_Collision3 p9). Mega Man uses 1 (all 3 uses). Reader not found. *Values:* 3 uses: 1 x3. *Evidence:* parser: +0x26 = (arr[12] != 0) when count >= 13

## FT_CATCH_SP `46F15F52` (handler 0x2bd76c0)
- **p0 ID** (old: unknown) [H]: Grab box id (0..). *Values:* 6 uses: 0 x2, 1 x2, 2 x2. *Evidence:* same op 0x2710 as Grab_Collision but arr[9] fixed to 2 -> hit-status mask 1 (cannot grab invincible targets); GrabModule MSC 0x02C32D58 op 0x2710 -> parser 0x02C32C18 -> GrabModule set (vtable +0x4C, 0x02C32580); slot = [GM+0xC] + id*0x2C
- **p1 Bone** (old: unknown) [H]: Joint the box follows (0x3F0 is remapped to 26 for some kinds in Grab_Collision2). *Values:* 6 uses: 0 x6. *Evidence:* data+0x1C (half)
- **p2 Size** (old: unknown) [declared int, really float] [H]: Radius (scaled by the fighter's scale). Declared int in acmd_info but read as FLOAT (format bug). *Values:* 6 uses: 15.0 x6. *Evidence:* data+0x18; scaled by GM+0x24*GM+0x2C
- **p3 X** (old: unknown) [declared int, really float] [H]: Offset X. Declared int in acmd_info but read as FLOAT (format bug). *Values:* 6 uses: 0.0 x6. *Evidence:* data+0x00
- **p4 Y** (old: unknown) [declared int, really float] [H]: Offset Y. Declared int in acmd_info but read as FLOAT (format bug). *Values:* 6 uses: 11.0 x6. *Evidence:* data+0x04
- **p5 Z** (old: unknown) [declared int, really float] [H]: Offset Z. Declared int in acmd_info but read as FLOAT (format bug). *Values:* 6 uses: 52.0 x2, 37.0 x2, 20.0 x2. *Evidence:* data+0x08
- **p6 TargetStatus** (old: unknown) [M]: Status kind the grabbed target is put in (63 = normal grab pull; command grabs use their own capture statuses, e.g. Bowser 190, Falcon 189, Ganon 184-186, Kirby/Dedede 223). Ultimate CATCH status argument. *Values:* 6 uses: 190 x6. *Evidence:* data+0x1E (half); matches Ultimate CATCH(status, situation)
- **p7 SituationMask** (old: unknown) [H]: Target situation mask: 1 ground, 2 air, 3 both. Ultimate COLLISION_SITUATION_MASK. *Values:* 6 uses: 1 x3, 3 x3. *Evidence:* data+0x22 -> filter word bits 13-15

## Search_Collision `44081C21` (handler 0x2bda3a0)
- **p0 ID** [H]: Search box id. *Values:* 46 uses: 0 x44, 1 x1, 2 x1. *Evidence:* SearchModule (accessor +0x70) vtable +0x4C set_search 0x02C6D680(id, part, data); slot = [SM+0x1AC] + id*0x28
- **p1 Part** [H]: Search group (0x174-byte group records like attacks). *Values:* 46 uses: 0 x46. *Evidence:* slot+0x24; group [SM+0x14] + part*0x174
- **p2 Bone** [H]: Joint. *Values:* 46 uses: 0 x34, 19 x4, 3 x3, 13 x2, 17 x1, 25 x1, 24 x1. *Evidence:* data+0x10 (half)
- **p3 Size** [H]: Radius. *Values:* 46 uses: 6.0 x9, 4.0 x5, 10.0 x4, 7.5 x4, 7.38 x3, 7.0 x3, 12.0 x3, 4.5 x3 .... *Evidence:* data+0x0C
- **p4 X** [H]: Offset X. *Values:* 46 uses: 0.0 x40, -2.0 x5, 300.0 x1. *Evidence:* data+0x00
- **p5 Y** [H]: Offset Y. *Values:* 46 uses: 0.0 x13, 3.0 x10, 10.0 x5, 9.0 x5, 6.0 x4, 2.0 x3, 8.0 x3, -36.0 x1 .... *Evidence:* data+0x04
- **p6 Z** [H]: Offset Z. *Values:* 46 uses: 0.0 x27, 5.0 x5, 4.0 x4, 1.5 x3, 10.0 x3, 15.0 x1, 20.0 x1, 2.0 x1 .... *Evidence:* data+0x08
- **p7 CollisionKindMask** (old: Unknown) [M]: Which collision kinds the search detects (filter word bits 0-6): 2 = hurtboxes (most), 1 = attacks (Wario Chomp, Dedede Inhale), 14 = 2|4|8 (Yellow Pikmin). Ultimate COLLISION_KIND_MASK. *Values:* 46 uses: 2 x26, 1 x10, 14 x10. *Evidence:* data+0x12 -> filter word bits 0-6 (grab boxes use the constant 2 here)
- **p8 HitStatusMask** (old: Unknown) [M]: Target hit-status mask (bits 7-12, 6 bits): 1 normal only, 3, 7, 31, 63 = every status. Ultimate HIT_STATUS_MASK. *Values:* 46 uses: 1 x22, 7 x12, 63 x6, 3 x5, 31 x1. *Evidence:* data+0x14 (half) -> filter bits 7-12; grabs use 3/1 here
- **p9 SituationMask** (old: Ground/Air) [H]: Target situation mask: 3 = ground|air, 7 = also the third situation bit. Ultimate COLLISION_SITUATION_MASK (GA / GA_ODD). *Values:* 46 uses: 3 x30, 7 x16. *Evidence:* data+0x16 -> filter bits 13-15
- **p10 Unused** (old: Unknown) [H]: Skipped by the handler (never read). Always 0 in vanilla. *Values:* 46 uses: 0 x46. *Evidence:* handler reads params 0-9 and 11-16 only
- **p11 CategoryMask** (old: Unknown) [M]: Target category mask (bits 16-19): 15 = everything (fighters, items, ...), 9 = fighters only (+ bit 3). Grab boxes use the constant 9. Ultimate COLLISION_CATEGORY_MASK. *Values:* 46 uses: 15 x36, 9 x10. *Evidence:* data+0x17 -> filter bits 16-19
- **p12 PartMask** (old: Unknown) [M]: Target hurtbox part mask (bits 20-23): 1 = body, 15 = all. Ultimate COLLISION_PART_MASK. *Values:* 46 uses: 1 x30, 15 x16. *Evidence:* data+0x18 -> filter bits 20-23
- **p13 IgnoreScale** (old: Unknown) [H]: Bool: size/offset are not multiplied by the owner's scale (scale forced to 1.0). *Values:* 46 uses: 0 x46. *Evidence:* data+0x19 -> 0x02C6E688 picks 1.0 instead of SM+0x1B4
- **p14 RehitRate** [H]: Frames before the same target can be found again (hit-log timer, same mechanism as an attack's rehit); 0 = once. *Values:* 46 uses: 1 x28, 0 x17, 60 x1. *Evidence:* slot+0x1E -> 0x02C10B90 (also used by AttackModule for its rehit)
- **p15 Flag1C** (old: SelfAffectionToggle) [L]: Bool stored per search slot and as a module-wide flag (SM+0x2E). Set by Samus bomb, Crash Bomb, Kirby inhale, Wario-Man. "SelfAffectionToggle" is the old guess; reader not found. *Values:* 46 uses: 0 x36, 1 x10. *Evidence:* data+0x1C -> slot+0x20, SM+0x2E
- **p16 ShapeType** (old: Unknown) [M]: Collision shape: 0 sphere, 2 the capsule/extended shape used by Extended grabs. Vanilla 2 only on some final-smash searches. *Values:* 46 uses: 0 x40, 2 x6. *Evidence:* data+0x1D -> 0x02C108C4 shape pool index

## SET_SEARCH_OPPONENT `8965B9D6` (handler 0x2bda4bc)
- **p0 ID** (old: Unknown) [H]: Search box id. *Values:* 5 uses: 0 x5. *Evidence:* SearchModule MSC 0x02C6DF88 op 5 -> 0x02C6E7EC
- **p1 Part** (old: Unknown) [H]: Search group; must match the box's part or nothing happens. *Values:* 5 uses: 0 x5. *Evidence:* slot+0x24 compare
- **p2 Field** (old: Unknown) [H]: Which filter field to overwrite: 0 collision kind, 1 hit status, 2 situation, 3 category, 4 part, 5 3-bit bits 24-26 (default 7), 6 2-bit bits 27-28, 7 3-bit bits 29-31. *Values:* 5 uses: 5 x5. *Evidence:* jump table 0x02C6E81C (rlwimi into the shape's filter word)
- **p3 Value** (old: Unknown) [M]: New value for that field. Vanilla (Wario Chomp, Dedede Inhale) sets field 5 to 2: field 5 is most likely the owner relation (self / opponent / team), so 2 = opponents only - hence SET_SEARCH_OPPONENT. *Values:* 5 uses: 2 x5. *Evidence:* corpus 0,0,5,2

## IT_SEARCH `65037812` (handler 0x2bea774)
- **p0 SearchKind** (old: unknown) [M]: Item-script command (IT_*): runs the item agent's target search (0x0302F794, switch on kind 0-20) with all result variables = -1, i.e. the search kind to run. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* accessor +0xCC item agent; 0x0303F614(kind, -1, -1, -1, -1)

## SEARCH_CLR_ALL `B39C1A7C` (handler 0x2bda570)
No parameters: SearchModule vtable +0x3C clear_all.

## HIT_STOP_MUL `640F63A0` (handler 0x2bd8af8)
- **p0 Multiplier** (old: unknown) [declared int, really float] [H]: Hitstop multiplier. Declared int in acmd_info but read as FLOAT (format bug). *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* HitModule (accessor +0x58) MSC op 0x271B -> vtable +0x184 0x02C441E8: HM+0x58 = mul
- **p1 Target** (old: unknown) [M]: Byte stored at HM+0x71: which side the multiplier applies to (Ultimate HitModule::set_hit_stop_mul target). A 3rd float (HM+0x60) defaults to 0.0. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* HM+0x71

## SET_ATTACK_HIT_STOP `05B66D19` (handler 0x2be8140)
- **p0 Value** (old: unknown) [L]: Forwarded to the fighter's MSC as a battle-object event (event 6, args [0x5F, value]); effect is decided by the MSC script. Unused in vanilla. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* 0x02BF2108 + 0x02BF019C

## ATTACK_SET_ATTACK_LEVEL `AEAE97FF` (handler 0x2bddcbc)
- **p0 ID** (old: unknown) [H]: Hitbox id. *Values:* 6 uses: 0 x6. *Evidence:* AttackModule vtable +0x4C4 (0x02C0DDB4): slot [AM+0x40] + id*0x84
- **p1 Level** (old: unknown) [M]: Attack level byte (slot+0x62, default 0). Only Ryu's Focus Attack sets 0/1/2 (charge stages: level 2 crumples). Ultimate AttackModule::set_attack_level. *Values:* 6 uses: 0 x2, 1 x2, 2 x2. *Evidence:* only the low byte is read

## ATTACK_SET_CHECK_BACK `7D1058C3` (handler 0x2bdd940)
- **p0 Part** (old: unknown) [H]: Hitbox group: hits only targets BEHIND the fighter (group+0x15C = -LR, +0x16D = 0). *Values:* 9 uses: 1 x9. *Evidence:* AttackModule MSC op 0x2736

## ATTACK_SET_CHECK_FRONT `7F55AAA2` (handler 0x2bdd8a4)
- **p0 Part** (old: unknown) [H]: Hitbox group: hits only targets IN FRONT of the fighter (group+0x15C = LR, +0x16D = 0). *Values:* 9 uses: 0 x9. *Evidence:* AttackModule MSC op 0x2735

## ATTACK_SET_CHECK_FRONT_LR `D41DF827` (handler 0x2bddc20)
- **p0 Part** (old: unknown) [M]: Hitbox group: front check in mode 2 (group+0x15C = LR, +0x16D = 2) - front relative to the attack's own LR (Mewtwo bindball). *Values:* 1 uses: 0 x1. *Evidence:* AttackModule MSC op 0x273F

## FT_ATTACK_ABS_CAMERA_QUAKE `227B36A1` (handler 0x2be8820)
- **p0 Kind** (old: unknown) [H]: Absolute-attack kind (0 throw, 1 catch). *Values:* 101 uses: 0 x101. *Evidence:* AttackModule vtable +0x4D4 (0x02C0DDDC) with abs=1: [AM+0x48]+kind*0x98
- **p1 CameraQuake** (old: unknown) [H]: Camera-shake kind for that throw hit (slot+0x5B; set_abs default 8). Vanilla 0 = none. Ultimate FT_ATTACK_ABS_CAMERA_QUAKE(kind, CAMERA_QUAKE_KIND_*). *Values:* 101 uses: 0 x101. *Evidence:* slot+0x5B

## GROUND_COLLISION `14712DA5` (handler 0x2bd4d50)
- **p0 Unused** (old: unknown) [H]: GROUND_COLLISION is a stub: the handler only skips its one parameter. *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* handler 0x02BD4D50 is a no-op

## THROW_ITEM `307D6993` (handler 0x2bec1a4)
- **p0 Unused** (old: unknown) [H]: Ignored: THROW_ITEM sends ItemModule MSC op 7 with no arguments (throw using the current motion's item-throw params). *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* ItemModule (accessor +0x64) MSC 0x02C49C7C op 7 -> vtable +0x114
- **p1 Unused** (old: unknown) [H]: Ignored (see p0). *Values:* unused in vanilla (0 uses in 1053 ACMD files). *Evidence:* handler skips it

## Throw_Item2 `6E053790` (handler 0x2bec238)
- **p0 Unused** (old: Unknown) [H]: Ignored: Throw_Item2 is identical to THROW_ITEM (MSC op 7, no args). Vanilla always 1, 0, 2. *Values:* 106 uses: 1 x106. *Evidence:* same code as THROW_ITEM
- **p1 Unused** (old: Unknown) [H]: Ignored. *Values:* 106 uses: 0 x106. *Evidence:* 
- **p2 Unused** (old: Unknown) [H]: Ignored. *Values:* 106 uses: 2 x106. *Evidence:* 

## THROW_ITEM_OFFSET `50730439` (handler 0x2bec7cc)
- **p0 OffsetX** (old: Unknown) [M]: Item release offset X (forward). *Values:* 763 uses: 0.0 x272, 12.0 x53, 14.0 x41, 10.0 x40, 13.0 x35, 11.0 x33, 18.0 x31, 1.0 x19 .... *Evidence:* MSC op 0x15: vector (p0, p1, 0) -> ItemModule vtable +0x11C (throw with offset)
- **p1 OffsetY** (old: Unknown) [M]: Item release offset Y (up). *Values:* 763 uses: 10.0 x64, 0.1 x51, 7.0 x51, 11.0 x44, 14.0 x41, 0.0 x40, 15.0 x35, 12.0 x35 .... *Evidence:* second component
- **p2 Unused** (old: Unknown) [H]: Never read by the handler (vanilla always 1). *Values:* 763 uses: 1 x763. *Evidence:* handler skips p2-p4
- **p3 Unused** (old: Unknown) [H]: Never read (vanilla always 0). *Values:* 763 uses: 0 x763. *Evidence:* 
- **p4 Unused** (old: Unknown) [H]: Never read (vanilla always 2). *Values:* 763 uses: 2 x763. *Evidence:* 

## THROW_ITEM_OFFSET_MOTION `2F20B6C7` (handler 0x2bec960)
- **p0 OffsetX** (old: unknown) [declared int, really float] [M]: Release offset X. Declared int but FLOAT (format bug). *Values:* 3 uses: 10.0 x3. *Evidence:* MSC op 0x26
- **p1 OffsetY** (old: unknown) [declared int, really float] [M]: Release offset Y. Declared int but FLOAT. *Values:* 3 uses: 17.5 x3. *Evidence:* 
- **p2 Motion** (old: unknown) [M]: Motion whose item-throw speed/angle params are used instead of the current motion's (Villager 299). *Values:* 3 uses: 299 x3. *Evidence:* 0x02C49A4C(motion) then 0x02C49AA8/B3C/C08/C60 read the throw params
