# Hitbox command parameters (Sm4shCommand)

Machine-readable version: `tools/Sm4shCommand/param_labels.json` (every slot of the 14 commands, with name, description,
values, evidence and confidence).

## How the commands reach the attack data

- **Built in the handler.** Hitbox `0x02BDB0EC`, Special_Hitbox `0x02BDBB20`, Special_Hitbox2
  `0x02BDBDCC`, ATTACK_FP_ATKW `0x02BDC07C` and the two Intensity commands (`0x02BDC5B8` / `0x02BDC944`)
  build the 0x68-byte attack data on the stack themselves. They then call AttackModule (accessor
  `+0x50`) vt `+0x54` = set_attack `0x02C086A8`, which copies the data to slot `[this+0x40] + id*0x84`.
- **Packed and sent to AttackModule.** The other commands copy their args into
  `{op, args...}` and call AttackModule vt `+0x334` (`0x02C0ACFC`, a switch on `op − 0x2710`):

  | Command | Op | Worker | Packed form |
  |---|---|---|---|
  | ATTACK_IND | 0x2712 | `0x02C0CE6C` (vt `+0x394`) | short |
  | ATTACK_FP_IND | 0x2713 | `0x02C0CE6C` (vt `+0x394`) | FP |
  | Extended_Hitbox | 0x272B | `0x02C0D210` (vt `+0x39C`) | short + 3 |
  | Extended_Special_Hitbox | 0x272C | `0x02C0D210` (vt `+0x39C`) | FP + 2 |
  | Collateral_Hitbox | 0x2731 | `0x02C0D9B8` (vt `+0x3DC`) | short |
  | Extended_Collateral_Hitbox | 0x2732 | `0x02C0D9B8` (vt `+0x3DC`) | short + 3 |
  | ATTACK_FP_IGNORE_THROW | 0x2733 | `0x02C0D9B8` (vt `+0x3DC`) | FP |
  | ATTACK_FP_CAPSULE_IGNORE_THROW | 0x2734 | `0x02C0D9B8` (vt `+0x3DC`) | FP + 3 |

- **Shared parser.** All the packed commands go through `0x02C0AA64`:
  - the prefix `0x02C0A96C` reads args 0–23 (the 24-param Hitbox layout);
  - with the FP flag, 17 more args go to data `+0x3E, +0x41, +0x42, +0x48, +0x49, +0x4A, +0x4B, +0x5C,
    +0x4D, +0x4E, +0x4F, +0x50, +0x51, +0x52, +0x53, +0x54, +0x57` (in that order);
  - without it, the Hitbox defaults are used (HitBits 63, Part 15, Shieldable 1, Facing = module byte
    `+0x11A`, the rest 0);
  - the arg count is checked against 25 / 42 + extra (`0x02C0AA54`).

## Slot layouts

- **24-param (Hitbox, Collateral_Hitbox, ATTACK_IND):** ID, Part, Bone, Damage, Angle, KBG, FKB, BKB,
  Size, X, Y, Z, Effect, Trip, Hitlag, SDI, Clang, Rebound, ShieldDamage, SFXLevel, SFXType, Ground/Air,
  Direct/Indirect, Type.
- **41-param FP (Special_Hitbox, Special_Hitbox2, ATTACK_FP_ATKW, ATTACK_FP_IND,
  ATTACK_FP_IGNORE_THROW):** the 24 above, then:

| Slot | Data | Name | Function | Conf. |
|---|---|---|---|---|
| 24 | +0x3E | HitBits | target category mask, 6 bits (63 = all) | high |
| 25 | +0x41 | *Unk41* | only Shulk's Back Slash front set (see below); reader not found | low |
| 26 | +0x42 | **CollisionPart** | victim hurtbox-part mask, 4 bits (always 15; Ultimate collision_part) | high |
| 27 | +0x48 | **NoScale** | size and offset ignore the owner's scale (scale → 1.0); unused in vanilla | medium |
| 28 | +0x49 | Shieldable | 0 = goes through shields (filter flag 0x04) | high |
| 29 | +0x4A | Reflectable | | high |
| 30 | +0x4B | Absorbable | | high |
| 31 | +0x5C | Rehit | rehit rate in frames | high |
| 32 | +0x4D | IgnoreInvuln | label kept, not verified (1 use: Wii Fit Trainer's d-tilt push box) | low |
| 33 | +0x4E | **HitAllStates** | widens the victim-state accept field from 3 to 7; only Puff Up FS | medium |
| 34 | +0x4F | FacingRestrict | LR check 0–6; Back Slash uses 3 (front) and 6 (back hit) | medium |
| 35 | +0x50 | **NoGrabRelease** | a hit from the fighter holding the victim doesn't release it; every pummel and throw | medium |
| 36 | +0x51 | TeamDamage | | high |
| 37 | +0x52 | DisableHitlag | | high |
| 38 | +0x53 | NoGFX | | medium |
| 39 | +0x54 | Flinchless | | medium |
| 40 | +0x57 | **Shape** (was StretchToggle) | collision shape kind: 0 sphere, 2 capsule | medium |

- **Capsule variants:**
  - Extended_Hitbox and Extended_Collateral_Hitbox: the 24 + X2, Y2, Z2 (Shape forced to 2).
  - Extended_Special_Hitbox: FP slots 0–39, then X2, Y2, Z2 at 40–42. Slot 40 is read as both Shape
    and X2, then Shape is overwritten with 2.
- **ATTACK_FP_ATKW:** slot 3 = **DamageWorkInt**. Damage = (float) WorkModule.get_int(slot 3), read when
  the hitbox is created.
- **Intensity_Special_Hitbox (47 params):**
  - ID, Part, Bone, Damage, Damage2, Angle, KBG, KBG2, FKB, FKB2, BKB, BKB2, Size, Size2, X, Y, Z, then
    Effect … Type (17–28), then the FP block (29–45, slot 45 = Shape), then 46 = **IntensityWorkFloat**.
  - IntensityWorkFloat is a WorkModule float ID holding a 0..1 ratio. Each value is
    `v1 + (v2 − v1) * ratio`. KBG, FKB and BKB are ints and their "2" values are floats.
- **Intensity_Extended_Special_Hitbox (49 params):** the same, with X2, Y2, Z2 at 45–47 and
  IntensityWorkFloat at 48 (Shape forced to 2).

## The four fully unknown commands

- **ATTACK_IND (DBDDC840)** uses the 24-param layout; **ATTACK_FP_IND (BD04BDC3)** uses the FP layout.
  They are indirect attacks. After set_attack, the worker `0x02C0CE6C` sets the hitbox's attacker
  (AttackModule vt `+0x2CC` → `+0xCC`):
  - to the LinkModule parent;
  - or, with no link, to the object's last attacker (DamageModule vt `+0x12C`).

  It also puts that object into the part's already-hit list (vt `+0x2F4` → `0x02C0F000`). The result:
  credit goes to the owner, and the owner can't be hit. ATTACK_FP_IND has 2 uses, both in common
  `game.bin`.
- **ATTACK_FP_IGNORE_THROW (97E2CEAA)** uses the FP layout. It is the FP form of Collateral_Hitbox
  (= ATTACK_IGNORE_THROW; Ultimate has the same macro): the fighter from LinkModule `+0xA4(0)` (the
  held / thrown victim) is pre-marked as already hit. It hits bystanders, not the thrown fighter.
- **ATTACK_FP_CAPSULE_IGNORE_THROW (633DECC0)** is broken as defined:
  - The worker wants 44 args (FP 41 + X2, Y2, Z2); the ACMD handler sends 43.
  - So the FP count check fails, and HitBits, CollisionPart, Shieldable, … Shape stay 0.
  - X2, Y2, Z2 are then read from slots 24–26.
  - Labels follow the intended layout (FP 0–40, X2 41, Y2 42). It has no vanilla uses.

## Corrections to existing labels

- **WBKB → FKB.** It is fixed / set knockback (the same value as "WBKB"; Ultimate calls it fkb).
- **Slot 26 Unknown → CollisionPart.**
- **StretchToggle → Shape.**
  - 0 = sphere, 2 = capsule. 2 copies X/Y/Z into X2/Y2/Z2 unless they are given.
  - Shapes are pooled per kind (`0x02C108C4`, `0x02C118E4`).
- **Blockability → Shieldable** (clearer name; the meaning is right).
- **Collateral_Hitbox.** acmd_info has 25 syntax labels for 24 params; the extra "HitBits" must go.
  Events.cfg is right.
- **Intensity_Special_Hitbox.** acmd_info has 46 format/syntax entries for 47 params (size 48). Missing:
  45 Shape and 46 IntensityWorkFloat. Events.cfg already has 47 entries; only the two "Unknown" names
  change.
- **ATTACK_FP_ATKW** slot 3 "Damage" → DamageWorkInt (int).
- **Formats.** The four unknown commands need the float types from Hitbox / Special_Hitbox: Damage,
  Size, X/Y/Z, Trip, Hitlag, SDI (+ X2/Y2 for the capsule form).
- **Ground/Air.** Note that bit 31 is a separate flag (data `+0x56`). It drops victim class 2 from the
  accept mask. It is used by inhales, Koopa's side-B catch, Little Mac's smashes / dash attack and
  Greninja's Shadow Sneak.
- **Special_Hitbox2** = Special_Hitbox plus an internal attack flag (data `+0x60` = 1). Hurt code
  `0x02C24DF4` then skips the victim's normal reaction call. Its only vanilla use is Marth / Lucina's
  Critical Hit finisher.

## Still unclear

- **Slot 25 (+0x41).** It is set only on Shulk's Back Slash front hitboxes, and no byte load of it was
  found in the battle code. A guess: "doesn't hit from behind".
- **Slot 33 and the Ground/Air bit 31.** The filter bits they change are known. Which victim states
  those target classes stand for (lying down, ledge, FS cutscene, …) is not, because that needs the
  hurtbox-side state packing.
- **Slot 32** keeps the IgnoreInvuln label without proof.
- **The value meanings of FacingRestrict, Type and Effect.** Only distributions and partial branches
  are known.
