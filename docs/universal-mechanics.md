# Universal mechanics (wanted on every character)

These are the user's own mechanic changes. Every fighter should eventually get them.

**Every fighter has them now** (user's `fighter-modded-scripts-only.zip`, 65 folders, Supamario left
out for now): Captain Falcon, Kirby, Luigi and Sonic by hand (below); everyone else, the
non-playable forms included (Giga Bowser, Wario-Man, Giga Mac, Mega Lucario, the Fighting Mii Team),
with the tools:

1. MSC: decompile (`tools/mscdec` with `-x tools/mscinfo.xml`; strings with raw line breaks need
   escaping; its `gvIsOffset` table had 64 entries, so a file already patched (65+ globals) failed:
   `tools/setup_toolchain.sh` widens it), then
   `python3 tools/universal_mechanics.py IN.c OUT.c [--air-mult M]`, then msclang. The patcher finds
   every function through the status table (`sv_set_mem(0x1, kind, status, func_N)`; a fighter's own
   script that calls the common one, like Palutena's EscapeF pre or Yoshi's roll main, is followed),
   skips parts a fighter already has (Corrin's, Meta Knight's, Dr. Mario's and Mewtwo's own reverse
   tilts), adds three globals and the helper functions at the end. Roll-off momentum is Hero's
   ("Roll-off momentum" below): the per-frame hook (global14's function, `func_82`) calls
   `rolloff_hold_update()`, and Fall's end is left alone. `--upgrade IN.c OUT.c` gives a fighter
   patched by the earlier version (decompiled, or a source such as `fighters/pzenigame/pzenigame.c`)
   Hero's momentum, its speeds and multiplier unchanged.
2. Check: `python3 tools/msc_fingerprint.py ORIGINAL.mscsb REBUILT.mscsb --added 12` compares what each
   function does (calls, constants, variables; not the bytes, which msclang lays out differently).
   An unedited round trip was the same in every function for every fighter (a few layout-only
   differences: an extra `else` jump, `-0.1` folded); after the patch exactly the patched functions
   differ, and only by additions (plus the rolls' kinetic type `0xf` -> `0x6`). Corrin, Giga Mac,
   Mega Lucario, Meta Knight and Ryu were patched from their sources in `fighters/` (each compiles to
   the user's file exactly).
3. ACMD: `tools/rolloff_acmd.py` on the user's `game.bin` (`--plain --add` for the default 2.2,
   `--clear-first` where the roll-off speed was already there). Only EscapeF / EscapeB change; every
   other script was checked identical, and a plain load / save gives every user file back byte for byte.

Speeds and air multipliers: default 2.2 / 1.0; Captain Falcon 2.4 / 1.0; Kirby 2.1 / 1.0 (Overdrive
2.8 / 1.05, `fighters/kirby/specials.md`); Luigi 1.6 / 1.1; Sonic 2.76 / 1.0; **Pikachu 8 / 0.2** (user).

**Speed cleared before the roll's speed (user: it wasn't, for anyone):** the roll's kinetic type
`0x6` sets up energy 3 with the speed the fighter had (a dash, a run), and the ACMD's
`Add/Set_Momentum(0, 0, 1)` didn't clear it. `rolloff_update()` sets energy 3's speed to 0
(`KineticModule(0x11, 3, 0, 0)`) on the roll's frames before `rolloff_clear_frames()` (3), in every
fighter (the four hand-done ones too). Clearing it up to `rolloff_start_frame()` (5) also wiped the
ACMD's speed (user: rolls didn't move): the MSC's motion frame reads one less than the ACMD's frame
when the speed is added, so the clear has to stop well before it. So the ACMD speed is in energy 3.
A dash's speed is in **energy 2** (Dash's kinetic type `0x1b` sets up energy 2: `0x02E7A5B0` table →
`0x02E7BBD8` → `0x02C5474C(2, ...)`); the roll's type `0x6` only sets up energy 3 and leaves energy 2
running, so a roll out of a dash kept the dash's speed (user: a back roll out of a dash went almost
nowhere). The clear also zeroes energy 2's X (`KineticModule(0x11, 2, 0, its Y)`).

**Rolls that turn around early (user: Ryu's forward roll went backwards):** the speed is along the
facing at the speed frame. Ryu (`Reverse_Direction` at frame 4) and Wii Fit Trainer (1) turn
before frame 5, so `rolloff_acmd.py --add` flips the sign when the roll has turned an odd number of
times by then.

**Rolls that call waiting subroutines (user: Samus' rolls didn't move):** Samus', Mii Gunner's and
the Mii Team gunner's rolls start with `CALL`s of scripts that wait (FRAME 1 / 2 / 18, then 30 / 34).
A call runs in place and its waits hold up the caller, so the roll-off commands appended after
them ran at frame 34: the speed was set and cleared at once (and their turn is at frame 18, not 0,
so the forward roll's sign was flipped too). `rolloff_acmd.py --add` now inlines calls of scripts
that wait before adding the speed, so it lands on frame 5 (`build/roll_fix_samus_miigunner.zip`).

**Ground speed cap (picked fighters only, user):** on the ground the roll's speed (kinetic energy 3,
the one type 0x6 sets up: `0x02E7A4DC` case 6 → `0x02C5474C(3, ...)`) is held to the energy's speed
limit, so a roll speed above it is cut down (Pikachu's 80 rolled like 8). `universal_mechanics.py
--ground-uncapped` makes `rolloff_update()` call `KineticModule(0x15, 3, -1, -1)` every roll frame
(no limit: the game's own pattern after resetting energy 3, `KineticModule(0xe, 3, ...)`). On:
**Pikachu**, **Corrin**, **Meta Knight**, **Samus**, **Roy** (user; Meta Knight's own game.bin had no
roll-off yet: `--plain --add` 2.2; Samus' and Roy's had it). Not in game-tested yet: that op 0x15 is the limit that applies here.

## Reverse tilts

Up tilt and down tilt can be done facing the other way: if the stick is held backward
(away from where the fighter faces, |X| > 0.12) when the attack button is pressed, the fighter
turns around before the tilt. MSC, in the common status pre scripts:

- `func_247` (AttackHi3 `0x29` pre) and `func_248` (AttackLw3 `0x2A` pre), after the two
  `StatusModule` calls:

```c
if ((global48 < -0.12f && PostureModuleF(0) == 1.0f) || (global48 > 0.12f && PostureModuleF(0) == -1.0f))
{
    PostureModule(0x2710); // reverse facing direction
}
```

`global48` = stick X. The function numbers are the common ones and are the same in every
fighter checked so far (Kirby, Captain Falcon, Bowser, Meta Knight, Charizard, Greninja,
Corrin...), but check the status table (`sv_set_mem(0x1, 0, 0x29/0x2A, func_N)`) per fighter.
Forward tilt doesn't need it (back + A already turns it around).

Done: Kirby, Meta Knight, Corrin (user); Captain Falcon (copied from Kirby's); Luigi; Sonic.

## Tilts, down smash and shield out of run

Up tilt (AttackHi3 `0x29`), down tilt (AttackLw3 `0x2A`), down smash (AttackLw4Start `0x2E`) and
shield (GuardOn `0x1B`) can be done straight out of a run (Run `0x4`). Up tilt, down tilt and down
smash (**not shield**: shield still does a forward roll, EscapeF `0x20`) also come out of the initial
dash (Dash `0x3`), of a turn out of a dash (Turn `0x6` / TurnDash `0x7` whose previous status,
`global5`, is Dash) and of a turn from a run (TurnRun `0x8` / TurnRunBrake `0x9`). Confirmed in game out of a run (user).
MSC, in the common Run scripts (same function numbers in Kirby and Captain Falcon; check
`sv_set_mem(0x1, 0x1, 0x4, func_N)` per fighter):

- **Run main** (`func_716`): turn the tilt transitions on, after the `0x1e000054` (dash attack) line:

```c
WorkModule(0x16, 0x1e000056); // up tilt (CONT_ATTACK_HI3)
WorkModule(0x16, 0x1e000057); // down tilt (CONT_ATTACK_LW3)
WorkModule(0x16, 0x1e00005f); // down smash (CONT_ATTACK_LW4_START)
```

- **Run loop** (`func_717`): nothing to add. It already calls `func_43`, which checks the up tilt
  command (`global24 & 0x4`, `0x1e000056`) and the down tilt command (`global24 & 0x8`,
  `0x1e000057`) and the down smash command (`global24 & 0x40`, `0x1e00005f`) before the dash
  attack check, and `func_49` (shield, `0x1e000029`, on through the
  Shield group `0x1f000005` that Run main already turns on).

**In game the commands didn't come out while running** (dash attack won), so the Run loop also
reads the stick itself: `run_attack_update()`, called in `func_717` before `func_43` and the dash
attack check. When attack is pressed (`global38 & 0x1`): stick Y (`global32`) ≤ −`run_tilt_y()`
(0.5) → down smash if the stick was flicked down within `run_smash_flick()` (4) frames
(`global47`) or the down smash command (`global24 & 0x40`) is set, else down tilt; stick Y ≥ 0.5 →
up tilt; otherwise nothing (dash attack). The up smash command (`global24 & 0x20`) is left to the
run loop's own up smash check.

**Still dash attack in game with only that:** tilting the stick up / down drops stick X, which ends
the run in RunBrake (`0x5`, loop `func_722`), and RunBrake has its own dash attack transition
(`0x1e000054` + attack). So `run_attack_update()` is also called in the RunBrake loop, before
`func_43` and that check (`sv_set_mem(0x1, 0x1, 0x5, func_N)` → main → `func_78(loop)` per fighter).

Dash and turns: `run_attack_update()` at the top of the Dash loop (`func_715`, after the air
check), and `dash_turn_attack_update()` (= `run_attack_update()` when `global5 == 0x3` and on the
ground) in the Turn (`func_724`) and TurnDash (`func_726`) loops. Turning from a run (user):
`run_attack_update()` on the ground in the TurnRun loop (`func_730`, after the `func_60` check) and
the TurnRunBrake loop (`func_732`, after the CancelModule check). Up smash (`global24 & 0x20`) is
still the loops' own.

Done: Kirby, Captain Falcon, Luigi, Sonic.

## Roll-off

Both rolls keep their speed off a ledge instead of stopping at it ("roll-off"). The user's
design, implemented on top of the user's first version from Captain Falcon's `captain.mscsb`.
**Hero's (`brave`) implementation is the universal version** (user, CLAUDE.md): its momentum
mechanics (4 - 6 below) are every fighter's; each fighter keeps its own roll-off speed and air
multiplier.

1. **The roll's animation doesn't move the fighter; ACMD gives it its speed.** Roll pre (EscapeF
   `0x20` = common `func_362`, EscapeB `0x21` = `func_363`): `StatusModule(0x5, 0, 0x6, 0x2, …)`,
   kinetic `0x6` (the originals use `0xF`, motion movement).
2. **ACMD speed** (`EscapeF`, `EscapeB`): `Add/Set_Momentum(0, 0, 1)` at frame 0,
   `(0, 0, 1)` then `(SPEED, 0, 0)` at frame 5 (the speed is cleared first (user), so the roll-off
   speed doesn't add to speed the fighter already has; added once, the speed then changes however
   the game changes it), `(0, 0, 1)` at 27. The back roll gets −SPEED. For a game.bin made before
   the clear: `tools/rolloff_acmd.py IN OUT --clear-first` (EscapeF and EscapeB).
   `tools/rolloff_acmd.py IN OUT --plain --add SPEED EscapeF EscapeB` (Captain Falcon 2.4, Kirby
   2.1; a roll that already has its own speed keeps it).
3. **Sliding off from the speed frame, not while shielding.** Every roll frame
   (`rolloff_update()`, first in the roll loops `func_370` / `func_372`): before
   `rolloff_start_frame()` (5) or while the shield button is held (`ControlModule(0x2712, 3)`),
   ground correction `0x2` (stops at edges, like crouching / shielding); otherwise `0x1` (can
   slide off, like a rebound).
   **Shield lock:** once shield has been held `rolloff_lock_frames()` (10) frames in a row during
   the roll, the roll can't slide off for the rest of it, even after shield is let go. The count
   (an int global: Kirby `global72`, Captain Falcon `global62`) is reset in the roll pre scripts
   and goes back to 0 whenever shield is released before reaching 10.
4. **The speed at the edge carries over on its own.** Sliding off sends the roll to Fall
   (`func_374`), or straight into an attack buffered off the edge, and the fighter keeps the roll's
   current speed with no extra code. The speed is set once (the ACMD), never per frame.
   (v3 also stored the speed every roll frame and gave it again in Fall's main; that doubled the
   speed on top of the carried momentum, with no air cap, and could fling fighters to the blast
   zone, so it was removed.)
   **Air speed multiplier:** `rolloff_air_speed_mult()` (default **1.0** = unchanged) scales that
   carried speed. The roll end (`func_381` / `func_382`) marks the slide-off (Kirby `global73`,
   Captain Falcon `global63`), and Fall's main (`func_501`) calls `rolloff_fall_speed()` once:
   kinetic energy 3's X speed (`KineticModuleF(0xa, 0x3)`, the speed the air speed cap applies to)
   × the multiplier, Y kept (`KineticModule(0x11, 0x3, x, y)`, the same way the game scales it, e.g.
   Kirby's `func_1072`). Only once, so the fall then slows it as usual (v3 set the speed every
   frame, which is what flung fighters). A slide straight into a buffered attack has no Fall: the
   per-frame hook applies the multiplier once instead, the frame after (the slide-off mark still set
   outside Fall and the rolls, in the air; on the ground the mark is dropped, so no later Fall scales
   an unrelated fall).
5. **No air speed cap from it.** The roll end (key 2: `func_381` / `func_382`) sets flag
   `0x20000044` (lifts the max horizontal air speed) when the next status (`global6`) is Fall
   (`0xE`) **or he's already in the air** (`StatusModule(0x1) == 2`: an attack buffered off the
   edge, Hero fix 62), and marks the cap as taken off by the roll-off. Fall's end (`func_535`) no
   longer touches it.
6. **Roll-off momentum (Hero's, fixes 61 / 62 / 85): the cap stays off while the stick holds the way
   he moves.** Every frame, from the per-frame hook (global14's function: `func_82`; Hero's
   `brave_frame` calls `func_82` then it), `rolloff_hold_update()`:
   - **The way he moves** (`rolloff_dir`, 1 right / −1 left) is taken once he's off, from his X
     (position variable `0x0F000000`) against the last frame's (`rolloff_last_x`, more than 0.01
     apart): not his facing, which a roll's turn can flip (fix 62).
   - **The cap comes back** (`WorkModule(0x14, 0x20000044)`, the mark cleared) when he's not in the
     air (landed, grabbed a ledge), when he's hit (status Damage `0x45` - DamageFall `0x4C`), or when
     the stick stops holding that way: the raw stick X on screen (`0x0F000260`) × the way under
     `rolloff_hold_x()` (0.3), let go or turned. On a frame attack or special is pressed
     (`ControlModule(0x2710, 0 / 1)`) the stick doesn't count: a stick click's attack / special zeroes
     the stick for that frame (fix 85); the next frame it does.
   - Until then the cap stays off through Fall and any air action after it (an aerial, a special, an
     air dodge, a double jump), and air friction slows the speed as usual.
   The position / stick variables are the executable's (`tools/position_vars_cave.py`, in the
   standard `cross_f.rpx`).

History: v1 (mine) used an ACMD shield flag; v2 set the speed every frame (constant speed). The
user's first version cleared the air speed flag at the start of Fall and only checked shield in
the roll's end; its `0x208000e0` / `0x1000004` save / restore is gone.

**Default speed: 2.2** for any character without a specified roll-off speed (`--add` with no
number uses it). **Default air speed multiplier: 1.0** (`rolloff_air_speed_mult()`). The user confirmed the current version (v3 minus the Fall speed boost) is
right as-is.

History of the momentum: Captain Falcon / Kirby put the cap back at every Fall end; the patched
fighters at Fall's end after a roll-off; Luigi and Sonic kept it off until grounded (Luigi's with
"carried speed only goes down"); Hero tested the stick-held version (fixes 61, 62, 84, 85; his
roll-off aerial direction picks of fixes 62 - 69 were removed in fix 76: the executable's buffered
aerial fix keeps the direction). The user made Hero's the universal version.

### Hero's momentum for every fighter (`$S/fighters_rolloff_hero_v1.zip`)

Every fighter with roll-off (69 MSC files; Supamario has none yet) runs Hero's momentum:

- **Patched fighters** (`universal_mechanics_all`'s 56, plus Corrin, Meta Knight, Samus and Roy from
  their no-ground-cap builds and Ganondorf from `ganon_upb_v6`; Incineroar / Steve use Bowser's /
  Pit's file): the latest shipped MSC decompiled, `universal_mechanics.py --upgrade`, compiled. Each
  decompile compiled back to the same functions first (`msc_fingerprint`: 0 differ), and after the
  upgrade only the roll ends, Fall's end and `func_82` differ (`--added 2`). Bayonetta's roll ends are
  her own (`func_2260` / `func_2261`).
- **Squirtle** (`fighters/pzenigame/pzenigame.c`): `--upgrade` on the source.
- **Sephiroth** (`fighters/edge/edge.c`): the same, except that his MSC already uses globals up to
  `0x86` (port_check C5: the most seen working), so his `rolloff_hold_update` adds none: the way he
  moves is kept in `global64` (1 off / not known yet, 2 right, 3 left) and read from the sign of his
  carried speed (kinetic energy 3's X) instead of his X against the last frame's.
- **Captain Falcon, Kirby, Luigi, Sonic** (hand-written): the same roll ends, hook and helper
  (`rolloff_cap`, `rolloff_dir`, `rolloff_last_x`). Their Fall end only puts the cap back when no
  roll-off holds it (Kirby / Luigi still clear it there for their air dodge's Fall). Luigi's jump
  momentum (`global68`, until grounded, speed only going down) and Kirby's Luigi / Sonic copy's jump
  momentum (`global93`) are unchanged: their roll-off part is now Hero's, and while the jump's
  momentum is on, the roll-off's release doesn't put the cap back. Sonic's `rolloff_momentum_update`
  (until grounded) is gone.
- **Hero** stays as he is (the reference; his Acceleratle ×2 roll is his own).

`tools/rolloff_hold_test.py FILE.mscsb|DIR` runs the compiled MSC through the roll-off's frames in a
small MSC interpreter (the modules stubbed) and compares each fighter's flag trace with Hero's
`brave.mscsb`: a slide into Fall then an aerial, a buffered aerial, landing, a hit, a stick click,
moving left, a weak stick, a roll ending on the ground; and the carried speed × the fighter's
multiplier (Fall's main or the hook). 69 of 69 as Hero's. Not tested in game.

Done: every fighter but Supamario: default 2.2 / 1.0, Captain Falcon 2.4 / 1.0, Kirby 2.1 / 1.0
(Overdrive 2.8 / 1.05), Luigi 1.6 / 1.1, Sonic 2.76 / 1.0, Pikachu 8 / 0.2, Hero 2.2 / 1.0 (Acceleratle
×2), with Hero's momentum.
