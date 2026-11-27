# Smash Run stat boosts (3DS) vs Smash Tour power-ups (Wii U)

Question (user, 2026-11-27): Smash Run collects stat boosts (speed, jump, attack, special, arms, defense); Smash for
Wii U's Smash Tour (`worldsmash`) has similar stat boosts. Do they work the same, and can the Wii U's Smash Tour path
apply Smash Run's stats in the port?

Short answer: very likely the same system. The Wii U executable still carries the fighter power-up machinery the 3DS
built for Smash Run, including a **Smash Run variant** of the defense category next to Smash Tour's, so applying Smash
Run stats on Wii U should mostly be setting the power-up points on the fighter and letting the Wii U's own code apply
them. The 3DS side of the formula is not read yet (code.bin's version isn't in the scratch copy): the Azahar trace
(`tools/smashrun_trace/`, category `stat`) records the values the 3DS computes, to check it.

Legend: **confirmed** = read from the code / data; **inferred** = follows from names or layout, not read in code.

## Wii U (cross_f.rpx, read statically)

### The data: `param/fighter/fighter_param_power_up.bin` (reference/params/fighter_param_power_up.csv)

8 groups of 24-byte records `{fighter_param ID, mul_a, mul_b, 0, rate, 0}`. Each group starts with a header record
naming its category stat (confirmed, docs/params/fighter_param.md):

| group | category | header stat | records | e.g. |
|---|---|---|---|---|
| g0 | speed | 0xD0 | 24 | walk / dash / run / air speeds and accelerations, mul_a 0.75, mul_b 1.4-3.4, rate 0.4 |
| g1 | jump | 0xD1 | 19 | jump speeds, gravity-ish stats, mul_a 0.85-1, mul_b 1.3-2.2 |
| g2 | air (special?) | 0xD2 | 9 | attack multipliers 0xDA-0xE0 (mul_b 3.2), hold speed |
| g3 | attack | 0xD3 | 6 | attack multipliers 0xE2-0xE6 (mul_b 3.5) |
| g4 | arms | 0xD8 | 13 | item throw speed / power, heal, item attack, capture cut |
| g5 | **defense_run** | 0xD9 | 13 | damage_mul 1.25 -> 0.13, shield, and lower move speeds (0.9) |
| g6 | (2-word table) | - | 6 | {0.7, 1} speed, {0.7, 1} jump, {1, 1} the rest: a per-category scale |
| g7 | **defense_tour** | 0xD9 | 13 | the same as g5 but damage_mul 1.25 -> 0.35 |

So the file has one defense curve for Smash Run (g5, the strong one: damage taken down to 0.13x) and one for Smash
Tour (g7, 0.35x). The other categories are shared (confirmed in the data; which code picks g5 or g7 is inferred).

### The code (confirmed: disassembly of cross_f.rpx)

- `0x02F1C5EC(entry, category, records, n, ..., points)`: the per-category step.
  - `t = points / 1000`. The divisor comes from fighter_param_common 0x25D (= 1000) for positive points and
    -0x25C (= 1000) for negative ones. `t` is clamped to [lower limit, 1.0]; the lower limit is the float at
    0x1013A3E4 (-1.0 inferred).
  - When the global `[0x102F90EC]` is set, `t` is multiplied by the category's g6 word: +0 for t > 0, +4 for
    t <= 0 (the manager's power_up block `+0x84`; the caller 0x02F1C550 reads `+0x18` / `+0x1C` there).
  - Then `0x02F1C354` (13 callers in the fighter WorkModule, 0x02F1C6xx-0x02F1D5xx).
- `0x02F1C354(list, from, to, scale?, table, n, base, t)`: for each record `{ID, a, b, c, d, e}` whose fighter_param ID
  falls in the table, the stat value `v` becomes
  - t > 0: `v' = (v * (A * (1 - t) + b * t) + c * t) * s28`
  - t <= 0: `v' = (v * (A * (1 + t) + d * (-t)) + e * (-t)) * s29`

  with `A = a` (mul_a) when `[0x102F90EC]` is set, else 1.0. `s28` / `s29` = floats +8 / +0x10 of an optional sixth
  argument (1.0 without one; the WorkModule callers pass none). Constants 1.0 / 0.0 at 0x1013A3A0 / A4. In the
  file c = e = 0, so it reduces to `v' = v * lerp(mul_a, mul_b, t)` for t in [0, 1] and `v * lerp(mul_a, rate, -t)`
  for t in [-1, 0].
- So, at 0 points a stat is `mul_a` times normal (0.75x speed, 0.85x jump: the "starting weaker" of the stat modes),
  at +1000 points `mul_b` times, at -1000 points `rate` times (inferred: rate = the multiplier at the bottom of the
  scale; the CSV header calls it "rate").

### Smash Tour's own params

`param/worldsmash/` (worldsmash_param, _item_param, _event_param, _enemy_param, _effect_param, _camera_param,
_debug_param) are the board game's (items, events, the board's enemies). The stat curves above are in
fighter_param_power_up, not in worldsmash (inferred from the file contents: no fighter_param IDs in worldsmash_*).
Where Smash Tour turns its collected stats into points (worldsmash code) is not read.

## 3DS (names from static.crs; code not read)

code.bin exports (the base game's static.crs; the update's has the same names, at other addresses):
- `app::FighterInformation::set_power_up_point(app::FighterPowerUpKind, float, bool)` (base 0x00527FF0; update
  0x00562EFC per the framework table) and `power_up_level(app::FighterPowerUpKind, bool)` (0x00527D34);
- `app::FighterInformation::set_power_up_temp(app::FighterPowerUpTempKind, app::FighterPowerUpKind, float, bool)`
  (0x0014C6EC): a temporary boost (inferred: the power-ups that raise a stat for a while);
- `app::FighterManager::set_power_up_streetpass(int, float x6)` (0x00441FCC): six stats at once (StreetPass);
- `app::WeaponModuleAccessor::power_up_param(int, app::FighterPowerUpPoint const&,
  lib::ParameterArray<FighterParamPowerUp::PowerUp, true> const&)` (0x0059CC98): the param type is
  `FighterParamPowerUp::PowerUp`, the same name as the Wii U's file (confirmed name; layout inferred to be the same);
- `app::FieldSmashUtility::get_run_and_climb_cp_{jump,move}_powerup_revision(short)`: the final battles' (race /
  climb) own jump / move corrections by power-up (names only).
- Smash Run's own files: `field_smash/powerup_bias_param.bin`, `field_smash/fighter_power_down_param.bin` (in the
  dump; not decoded here).

So the 3DS has the same pieces by name: a power-up kind enum, points set per kind, a level read per kind, and the
`FighterParamPowerUp::PowerUp` param arrays. What is not known yet:
- the 3DS's `fighter_param_power_up` values (the 3DS file is in the dump's data archive: to extract and compare with
  the Wii U's; if Smash Run's g5 matches the Wii U's g5 the Wii U file can be used as is);
- the 3DS's points scale (Smash Run shows the stat totals as numbers; the Wii U scale is +-1000 points -> t = +-1);
- whether the 3DS sets `[0x102F90EC]`'s counterpart (mul_a at 0 points, the g6 scale) in Smash Run.

## Can the port reuse the Wii U path?

Likely yes (inferred), and cheaply:
1. The Wii U already applies `fighter_param_power_up` to a fighter's stats from per-category points, with a Smash Run
   defense curve in the file. Setting a fighter's points per category (the Wii U's equivalent of
   `set_power_up_point`) should give Smash Run's multipliers with no new math.
2. To do: find the Wii U's points setter (the caller chain of 0x02F1C5EC up from the WorkModule; Smash Tour sets it
   at the start of each battle) and which flag selects g5 (run) over g7 (tour) and turns on `[0x102F90EC]`.
3. Then compare with the trace: for each `set_power_up_point(kind, points)` the 3DS logs, the
   `power_up_level(kind)` value it returns, and the fighter's run speed / jump height in the same session. The
   formula above predicts the multipliers; `analyse.py` lists the samples per stat kind.

## Trace checklist (tools/smashrun_trace/README.md, "Stat boosts and power-ups")

- Collect boosts of each stat and photograph the totals screen at the end.
- Use each power-up once.
- `python trace.py run --cats stat,item,effect,sound` for those runs.
