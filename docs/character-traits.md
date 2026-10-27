# Character traits

Every character we work on gets a trait. When Kirby has that character's copy ability, he gets the
trait's changes (Kirby's MSC: `kirby_copy_trait()` / `kirby_trait_update()` at the end of
`fighters/kirby/kirby.c`). **Add a character here (and to `kirby_copy_trait()`) the first time we
work on them, with the trait the user specifies.**

Traits: **Rush**, **Shooter**, **Strike**, **Juggernaut**, **Normal**, **Technical**, **Barrage**.

| Character | Kind (ID) | Trait |
|---|---|---|
| Captain Falcon | `0x0C` | Rush |
| Sonic | `0x22` | Rush |
| Corrin | `0x39` | Rush |
| Little Mac | `0x29` | Rush |
| Bowser | `0x0F` | Strike |
| Marth | `0x12` | Strike |
| Donkey Kong | `0x04` | Strike |
| Luigi | `0x0B` | Technical |
| Supamario (new kind, Mario copy) | `0x41` | Normal |
| Sephiroth (`edge`, new kind, Ultimate port on Zelda's base) | `0x42` | Technical |
| Incineroar (`gaogaen`, new kind, Ultimate port on Bowser's base) | `0x43` | Juggernaut |
| Steve (`pickel`, new kind, Ultimate port on Pit's base) | `0x44` | Technical |
| Hero (`brave`, new kind, Ultimate port on Robin's base) | `0x45` | Shooter |
| Meta Knight | `0x17` | Normal |
| Samus | `0x06` | Shooter |
| Roy | `0x36` | Technical |
| Dr. Mario | `0x24` | Normal |
| Diddy Kong | `0x1B` | Rush |

Kirby himself (no copy) has no trait. A copied character that isn't listed counts as Normal.
Kind IDs: `reference/fighter_param_attributes.csv` (CharID column) or the copy kind int `0x100000A4`.

## What each trait gives Kirby's copy

| Trait | Changes |
|---|---|
| Rush | ×1.25 movement stats: walk (`0x01`–`0x03`), dash / run (`0x08`–`0x0B`), jump horizontal speed (`0x0D`, `0x0F`, `0x10`), air acceleration and max air speed (`0x14`–`0x16`), max fall and fast fall speed (`0x19`, `0x1B`). Not jump height (`0x11`–`0x13`), gravity (`0x18`, it would change jump height), traction or landing lag. Neutral air is the air rapid jab. |
| Strike | ×1.15 damage on Kirby's own hitboxes (anything that isn't a projectile / article: those are separate objects), ×1.2 hitstop for the opponent, Kirby's own hitstop unchanged. Native (`tools/strike_cave.py`, marker bit `0x8` from `kirby_trait_flags()`). Throws ×1.15 too. Knockback goes up with the damage, as it does for any harder hit. Not `Change_Hitbox_Damage`. **Critical hits:** each smash attack has a 1 in 8 chance (rolled at the windup, `strike_crit_*()`) to double the Strike values: ×2 damage on top of ×1.15 (×2.3), and exactly 2× the Strike hitstop for both Kirby (2× his normal) and the opponent (marker bit `0x10`), with a close camera zoom on Kirby when it connects. **Neutral air:** jab 2 in the air (1.6 / 1.4 frame duration, 6% / 43° hitbox, 1.2× hitstun, air grab cancel from frame 4, special cancel any time; `fighters/kirby/specials.md`). |
| Shooter | none yet |
| Juggernaut | none yet |
| Normal | none yet |
| Technical | none yet |
| Barrage | none yet |

Stat indices are `fighter_param` (`0x030000xx`), names in `reference/fighter_param_attributes.csv`.

### How the stat changes work

The stats are the character's shared `fighter_param` entry (one copy for every Kirby on the field),
so they can't be rewritten for one Kirby. Instead `tools/kirby_stat_cave.py` (part of the standard
`cross_f.rpx` build) hooks the function every stat read goes through (`WorkModuleImpl::get_float`,
`0x0200F628`). For an object whose instance int `0x1000008E` is `0x4B49xxxx` (only Kirby's MSC
writes that), it multiplies the stats of profile `xxxx & 0xF`:

| Profile | Trait | Stats | × |
|---|---|---|---|
| 0 | anything else | none | — |
| 1 | Rush | the Rush list above | 1.25 |
| 2 | Overdrive (below) | the Rush list | 1.25 × 1.2 = 1.5 |

Kirby's MSC writes the int every frame (`kirby_trait_profile()`); bits 8-11 hold the trait number
(0 none, 1 Normal, 2 Rush, 3 Shooter, 4 Strike, 5 Juggernaut, 6 Technical, 7 Barrage) for the damage panel's
trait badge: Kirby's panel shows the trait (icon + name, art from tools/trait_badge_art.py) while he
has a copy (tools/trait_badge_cave.py in the executable, tools/dmg_trait_badge.py adds the element to
ui/info/dmg; docs/native-notes.md "Damage panel"). Badge colours: Normal grey, Rush blue, Shooter
purple, Strike red, Juggernaut yellow, Technical black, Barrage orange (`TRAITS` in
`tools/trait_badge_art.py`). Icons: the user's art in `tools/trait_icons/<trait>.png` (all but Normal),
else a drawn one. A new trait also needs its number in `trait_badge_cave.py` (`TRAITS`, the last
frame) and `dmg_trait_badge.py` (`TRAITS`; seven 72-px rows fill the 512-px texture). A new trait with stat changes
needs a profile in `PROFILES` in `tools/kirby_stat_cave.py` and in `kirby_trait_profile()`.
Moveset changes (like Rush's neutral air) are MSC only (`global76` = current trait).

## Overdrive (Kirby's Corrin copy)

With Corrin's copy ability (kind `0x39`), Kirby's 3rd pummel (each CatchAttack counts) puts him
in **Overdrive** until he's KO'd or loses the copy; both also reset the pummel count.

- Movement stats ×1.2 on top of Rush (stat profile 2, ×1.5 of the base stats).
- Every animation ×1.2 (float ID `0x0F000098`, MotionModule's second rate; ACMD timing speeds
  up with it, and moves keep their own rate changes on top).
- The blue glow `0x10000C7` on the head (`HeadN` `0x16`), both arms (`LArmJ` `0xF`, `RArmJ`
  `0x13`) and the left leg (`LLegJ` `0x3`), removed and made again every frame.

MSC: `overdrive_*()` in `fighters/kirby/kirby.c` (`global82` pummel count, `global83` on). Needs
the patched `cross_f.rpx` (stat profile 2 and ID `0x0F000098`; the game crashes on that ID
without it, but it's only written once Overdrive starts).
