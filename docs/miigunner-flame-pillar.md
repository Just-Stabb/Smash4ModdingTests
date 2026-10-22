# Mii Gunner's Flame Pillar: how it attaches to an opponent

Static analysis of vanilla `cross_f.rpx` plus the vanilla article files (`fighter/miigunner/script/
{animcmd,msc}/weapon/flamepillar`). Weapon kind **`0x123`** (`flamepillar`), Mii Gunner's article id
**7** (max 2 at once; article table `0x1013CCE0`, entry 7 = `{0x123, 2, 0x02F2CEF4, 0}`).

**Short answer:** the shot doesn't stick to the opponent. A native **hit-result callback** written
for this weapon turns the shot into the pillar **at the point where it hit**. Every other projectile
is removed on hit; this one switches to its second status instead. The pillar then stands (or
hangs) there and hits.

## Step by step

1. **Spawn** (native, `0x02F2CEF4`, the article-table callback). The shot spawns at Mii Gunner's
   bone `0x19`, offset by his side-B params X 3.2 / Y 1.1. It is aimed by his ground or air params
   (`special_s`, vl `m13`):

   | | Angle | Speed |
   |---|---|---|
   | Ground | −15° | 2.5 |
   | Air | −43° | 2.8 |

2. **Kinetics** (native, specializer `+0x34` = `0x02B20FC4`). The main energy gets speed × (cos, sin)
   of the angle. A gravity energy gets accel −`0x02000003` (0.05) and max `0x02000004` (1.5), but
   status 0 turns it off (MSC `KineticModule(0xc, 2)`), so the shot flies in a straight line.
3. **Status 0, "shoot"** (MSC + ACMD `shoot` `0x7044FCBE`).
   - It lives `0x12000000` = 20 frames.
   - It becomes the pillar on touching ground (MSC `GroundModule(0x2722, 0xff)` → status 1).
   - At 0 life it is removed. The status-0 exit (`func_56`) plays the puff `0x1000021` whenever the
     next status isn't the pillar.
   - Hitbox: 4%, 80°, KBG 80, BKB 40, size 3, Hitlag 1, **SDI 0**, Rehit 0.
4. **The hit → pillar switch** (native, specializer `+0xAC` = **`0x02B21468`**). The base weapon
   method `0x02B89C38` calls this hit-result callback with the result bits from the hit message
   (`msg+8`). In status 0 (StatusModule vt `+0x8C`, which reads `+0x48`, = 0):
   - **bits `0x3`** (the shot's attack connected: the cases the default handler treats as "hit →
     remove"): `StatusModule vt+0x2C(1)` requests **status 1**, returns 0. Nothing is removed.
   - **bits `0x14`**: `weapon+0x1E18 = 1` (removed, no pillar → the puff).
   - **anything else**: the default handler `0x0320EE2C`:
     - `0x13` → remove (`+0x1E14 = 1`, `+0x1E18 = 1`), which is what happens to a fireball;
     - `0x4` → remove unless byte `+0x46` is set;
     - `0x8` → the reflect / absorb checks.

   In status 1 the callback returns 0 for any of `0x17`: the pillar is never removed by its own
   hits, clanks or shield contact.
5. **Status 1, "pillar"** (MSC + ACMD `pillar` `0xDC128957`).
   - **Placement:**
     - MSC `func_62` moves it up `0x02000002` = 2.0 (`PostureModule(0x2716, 0, 2.0, 0)`).
     - `KineticModule(0xc, 0)` stops the main energy, so it stays where the shot was. That is the
       opponent's position on a direct hit.
     - In the air, `func_59` turns gravity back on (`KineticModule(0xb, 2)`), so it sinks at
       0.05/frame² (max 1.5). On the ground, gravity is off and it stays on the floor
       (`GroundModule(0x2710, 2/5)`).
   - **Life:** `0x12000001` = 40 frames.
   - **Shrinking:** its scale goes from 1.0 to `0x02000006` = 0.7 over that life (`func_63`). The
     hitboxes shrink with it (NoScale 0).
   - **Hitbox:** two Special_Hitboxes:
     - 6%, 45°, KBG 70, BKB 40, size 6.5 at Y 0 and 4.5 at Y 6;
     - Hitlag 1.5, **DisableHitlag 1** (the pillar doesn't freeze);
     - Clang 0, Rebound 0, Rehit 0: one hit per target.
   - **Effect:** `0x302000F` restarts every 9 frames.
6. **The pillar can be hit** (native).
   - Specializer `+0x1C` (`0x02B20F60`) gives the weapon hurtboxes from the next vl block (`m35`:
     1 box, ±2.4).
   - MSC `HitModule(0x2712, part, state)` enables part 0 for the shot and part 1 for the pillar.
   - Specializer `+0xE4` (`0x02B21588`): in status 1, damage the pillar takes this frame (DamageModule
     vt `+0x7C`) × `0x02000005` = **10 frames** comes off its life (int `0x10000004`, floored at 0).
     So 4% of damage ends it.

So on a direct hit, the opponent takes the shot (4%, 80°, no SDI, little knockback). The pillar
then forms on the same spot and hits them (6%, 45°). It looks attached because the pillar appears
on the opponent instead of on the floor. Whether that second hit always lands on the same target
depends on the hit list being reset when the motion changes (shot motion 0 → pillar motion 1, both
hitboxes ID 0 / Part 0). That is the usual behaviour, but I haven't verified it here.

## What lives where

| Part | Where |
|---|---|
| Damage, angles, sizes, hitlag, SDI | ACMD `weapon/flamepillar/game.bin` (`shoot`, `pillar`) |
| Lifetimes, ground → pillar, the +2 lift, shrink, gravity in the air, the miss puff | MSC `flamepillar.mscsb` |
| Shot speed / angle / spawn offset | Mii Gunner vl `m13` (`0x06000000`–`0x06000005`) |
| Lifetimes 20 / 40, lift 2.0, gravity 0.05 / 1.5, damage → life 10, final scale 0.7 | vl `m34` (weapon `flamepillar`, `0x12000000`–`0x02000006`) |
| **Hit → pillar** (instead of removal), pillar not removed by hits, damage shortens the pillar | native specializer, vtable **`0x100E8E94`** (pairs `{0, fn}`): `+0xAC` `0x02B21468`, `+0xE4` `0x02B21588`, `+0x34` `0x02B20FC4`, `+0x1C` `0x02B20F60` |

The 11 weapon-kind switches (docs/weapon-expansion-code.md) have no Flame-Pillar-specific logic.
They call generic template wrappers. The only uncommon one is the hurtbox-module update
`0x02B9E028`, which it shares with Phantom, Gordo, Beast, the clay pigeon and the can (weapons that
can be hit).

## Modding it

- **Change what the pillar does:** edit the `pillar` ACMD (the hitboxes; add Rehit for multi-hit,
  e.g. 5 frames; change the angle). Or edit vl `m34`: life, lift, shrink, how fast damage kills it.
- **Make it not form on a hit:** turn `0x02B21468`'s `bits & 3` branch into the default handler (one
  word: `0x02B214B8` `beq` → `b 0x02B21558`). The shot is then removed on hit like a fireball, and a
  pillar only forms on the ground.
- **Make it stick (follow the opponent):** nothing in vanilla does that. MSC can't name the target
  it hit. A follow needs native code: store the victim's ID from the hit message in the callback,
  then copy its position each frame in status 1 (e.g. a cave on specializer `+0xE4`).
- **Give another projectile the same behaviour:** point that weapon kind's specializer `+0xAC` at a
  callback like `0x02B21468`. It only assumes "status 0 = flying, status 1 = burst" and asks
  StatusModule for status 1, so it can be reused as is by any weapon whose MSC has a status 1. Give
  its MSC a status 1 that stops it and runs the burst ACMD. Without the native callback the default
  handler removes it on hit before its MSC can react. A copy made with `tools/weapon_expand.py`
  shares the base kind's specializer, so a Flame Pillar copy keeps this behaviour.

## Not confirmed

- **The exact meaning of the result bits** (which bit is a hurtbox vs a shield vs a clank). The
  above is from how the default handler treats them.
- **Specializer `+0x3C`** (`0x02B21444`) registers `0x02B211B4` with the module at accessor `+0x3C`.
  It does camera / position maths and looks visual only.
- **The pillar hitting the same victim right after the shot.** See above; in-game test: a direct hit
  at 0% should deal 10%.
