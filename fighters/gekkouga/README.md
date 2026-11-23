# Greninja (`gekkouga`) MSC

`gekkouga.c` is Greninja's MSC as shipped: his decompiled vanilla MSC (special-move scripts labelled with `//` comments;
see [specials.md](specials.md)) with named syscalls, plus the universal mechanics (docs/universal-mechanics.md) and the
**Clones v1** mod (below: `clones.c` appended, a few sites patched). The vanilla decompile (62 globals, 2,414 functions)
is in git (`git show 0932c7b:fighters/gekkouga/gekkouga.c`); `tools/gekkouga_build.py msc VANILLA.c OUT.c` makes this
file from it. Greninja's trait (docs/character-traits.md): **Technical** (kind `0x30`).

## Build

```sh
./tools/setup_toolchain.sh
python3 tools/msclang/msclang.py -x tools/mscinfo.xml fighters/gekkouga/gekkouga.c -o gekkouga.mscsb
```

The unmodified vanilla file compiled, and decompiling the result gave back the same
code. The only differences are cosmetic: `\n` inside four `printf` strings is
printed as a real line break, the hand-written `//` comments are gone, and
`!(a == b)` comes back as `a != b`.

## Layout

| Lines | Contents |
|---|---|
| 1–62 | `global0`–`global61` (IDs are positional, never reorder) |
| `func_0`–`func_2239` | Common fighter library (same numbering as the sheet's `script_N`) |
| `main()` (line ~36186) | Entry: `func_2242()` sets up the fighter, then `set_main(func_73)` |
| `func_2240`–`func_2260` | Fighter init. `func_2243`/`func_2244` register the action scripts below |
| `func_2261`+ | Greninja's own action scripts |

**Add new functions after `func_2413` (end of file) and new globals after `global61`.**

Greninja-specific function-pointer globals set in `func_2242`: `global23`,
`global56`, `global57`, `global59`, `global60`, `global61` = `func_2377`, and
`global35` = `func_2378`.

## Action scripts registered by Greninja

Generated with `python3 tools/action_table.py fighters/gekkouga/gekkouga.c --from-main`.
Action names come from the sheet's Actions tab; the blank ones (0x157+) are
Greninja-only actions such as special-move follow-up states.

| Action | Name | Key | Script | Registered in |
|---|---|---|---|---|
| 0xC | JumpAerial | start (1) | `func_2384` | `func_2243` |
| 0x16 | LandingHeavy | start (1) | `func_2246` | `func_2243` |
| 0x16 | LandingHeavy | end (2) | `func_2247` | `func_2243` |
| 0x17 | LandingLight | start (1) | `func_2248` | `func_2243` |
| 0x18 | LandingAirN/F/B/Hi/Lw | start (1) | `func_2250` | `func_2243` |
| 0x18 | LandingAirN/F/B/Hi/Lw | end (2) | `func_2251` | `func_2243` |
| 0x18 | LandingAirN/F/B/Hi/Lw | start (3) | `func_2249` | `func_2243` |
| 0x19 | LandingFallSpecial | start (1) | `func_2252` | `func_2243` |
| 0x30 | AttackLw4 | start (1) | `func_2386` | `func_2243` |
| 0x33 | AttackHi4 | start (1) | `func_2387` | `func_2243` |
| 0x34 | AttackAirN/F/B/Hi/Lw | start (1) | `func_2382` | `func_2243` |
| 0x4D | DownBound | start (1) | `func_2254` | `func_2243` |
| 0x73 | CliffCatch | start (1) | `func_2253` | `func_2243` |
| 0xA7 |  | start (1) | `func_2258` | `func_2243` |
| 0xC8 | Cannon | start (1) | `func_2256` | `func_2243` |
| 0xC9 |  | start (1) | `func_2255` | `func_2243` |
| 0xCD |  | start (1) | `func_2257` | `func_2243` |
| 0x152 | SpecialN | start (0) | `func_2261` | `func_2243` |
| 0x152 | SpecialN | start (1) | `func_2262` | `func_2243` |
| 0x152 | SpecialN | end (2) | `func_2264` | `func_2243` |
| 0x153 | SpecialS | start (0) | `func_2287` | `func_2243` |
| 0x153 | SpecialS | start (1) | `func_2289` | `func_2243` |
| 0x153 | SpecialS | end (2) | `func_2292` | `func_2243` |
| 0x153 | SpecialS | start (3) | `func_2288` | `func_2244` |
| 0x153 | SpecialS | frame (4) | `func_2245` | `func_2244` |
| 0x153 | SpecialS | hitlag frame (5) | `func_2245` | `func_2244` |
| 0x153 | SpecialS | end (6) | `func_2245` | `func_2244` |
| 0x153 | SpecialS | frame (7) | `func_2245` | `func_2244` |
| 0x153 | SpecialS | frame+hitlag (8) | `func_2245` | `func_2244` |
| 0x154 | SpecialHi | start (0) | `func_2301` | `func_2243` |
| 0x154 | SpecialHi | start (1) | `func_2302` | `func_2243` |
| 0x154 | SpecialHi | end (2) | `func_2305` | `func_2243` |
| 0x154 | SpecialHi | start (3) | `func_2317` | `func_2244` |
| 0x154 | SpecialHi | frame (4) | `func_2318` | `func_2244` |
| 0x154 | SpecialHi | hitlag frame (5) | `func_2245` | `func_2244` |
| 0x154 | SpecialHi | end (6) | `func_2245` | `func_2244` |
| 0x154 | SpecialHi | frame (7) | `func_2245` | `func_2244` |
| 0x154 | SpecialHi | frame+hitlag (8) | `func_2306` | `func_2244` |
| 0x155 | SpecialLw | start (0) | `func_2335` | `func_2243` |
| 0x155 | SpecialLw | start (1) | `func_2336` | `func_2243` |
| 0x155 | SpecialLw | end (2) | `func_2338` | `func_2243` |
| 0x155 | SpecialLw | start (3) | `func_2340` | `func_2244` |
| 0x155 | SpecialLw | frame (4) | `func_2342` | `func_2244` |
| 0x155 | SpecialLw | hitlag frame (5) | `func_2245` | `func_2244` |
| 0x155 | SpecialLw | end (6) | `func_2343` | `func_2244` |
| 0x155 | SpecialLw | frame (7) | `func_2245` | `func_2244` |
| 0x155 | SpecialLw | frame+hitlag (8) | `func_2245` | `func_2244` |
| 0x156 | Final | start (0) | `func_2388` | `func_2243` |
| 0x156 | Final | start (1) | `func_2389` | `func_2243` |
| 0x156 | Final | end (2) | `func_2392` | `func_2243` |
| 0x157 |  | start (0) | `func_2265` | `func_2243` |
| 0x157 |  | start (1) | `func_2266` | `func_2243` |
| 0x157 |  | end (2) | `func_2268` | `func_2243` |
| 0x158 |  | start (0) | `func_2269` | `func_2243` |
| 0x158 |  | start (1) | `func_2270` | `func_2243` |
| 0x158 |  | end (2) | `func_2272` | `func_2243` |
| 0x158 |  | start (3) | `func_2281` | `func_2244` |
| 0x158 |  | frame (4) | `func_2245` | `func_2244` |
| 0x158 |  | hitlag frame (5) | `func_2245` | `func_2244` |
| 0x158 |  | end (6) | `func_2245` | `func_2244` |
| 0x158 |  | frame (7) | `func_2245` | `func_2244` |
| 0x158 |  | frame+hitlag (8) | `func_2245` | `func_2244` |
| 0x159 |  | start (0) | `func_2273` | `func_2243` |
| 0x159 |  | start (1) | `func_2274` | `func_2243` |
| 0x159 |  | end (2) | `func_2276` | `func_2243` |
| 0x15A |  | start (0) | `func_2277` | `func_2243` |
| 0x15A |  | start (1) | `func_2278` | `func_2243` |
| 0x15A |  | end (2) | `func_2280` | `func_2243` |
| 0x15A |  | start (3) | `func_2281` | `func_2244` |
| 0x15A |  | frame (4) | `func_2245` | `func_2244` |
| 0x15A |  | hitlag frame (5) | `func_2245` | `func_2244` |
| 0x15A |  | end (6) | `func_2245` | `func_2244` |
| 0x15A |  | frame (7) | `func_2245` | `func_2244` |
| 0x15A |  | frame+hitlag (8) | `func_2245` | `func_2244` |
| 0x15B |  | start (0) | `func_2293` | `func_2243` |
| 0x15B |  | start (1) | `func_2294` | `func_2243` |
| 0x15B |  | end (2) | `func_2296` | `func_2243` |
| 0x15C |  | start (0) | `func_2297` | `func_2243` |
| 0x15C |  | start (1) | `func_2298` | `func_2243` |
| 0x15C |  | end (2) | `func_2300` | `func_2243` |
| 0x15D |  | start (0) | `func_2307` | `func_2243` |
| 0x15D |  | start (1) | `func_2308` | `func_2243` |
| 0x15D |  | end (2) | `func_2312` | `func_2243` |
| 0x15D |  | start (3) | `func_2319` | `func_2244` |
| 0x15D |  | frame (4) | `func_2323` | `func_2244` |
| 0x15D |  | hitlag frame (5) | `func_2325` | `func_2244` |
| 0x15D |  | end (6) | `func_2245` | `func_2244` |
| 0x15D |  | frame (7) | `func_2245` | `func_2244` |
| 0x15D |  | frame+hitlag (8) | `func_2245` | `func_2244` |
| 0x15E |  | start (0) | `func_2330` | `func_2243` |
| 0x15E |  | start (1) | `func_2332` | `func_2243` |
| 0x15E |  | end (2) | `func_2334` | `func_2243` |
| 0x15E |  | start (3) | `func_2331` | `func_2244` |
| 0x15E |  | frame (4) | `func_2245` | `func_2244` |
| 0x15E |  | hitlag frame (5) | `func_2245` | `func_2244` |
| 0x15E |  | end (6) | `func_2245` | `func_2244` |
| 0x15E |  | frame (7) | `func_2245` | `func_2244` |
| 0x15E |  | frame+hitlag (8) | `func_2245` | `func_2244` |
| 0x15F |  | start (0) | `func_2313` | `func_2243` |
| 0x15F |  | start (1) | `func_2314` | `func_2243` |
| 0x15F |  | end (2) | `func_2316` | `func_2243` |
| 0x15F |  | start (3) | `func_2326` | `func_2244` |
| 0x15F |  | frame (4) | `func_2327` | `func_2244` |
| 0x15F |  | hitlag frame (5) | `func_2245` | `func_2244` |
| 0x15F |  | end (6) | `func_2329` | `func_2244` |
| 0x15F |  | frame (7) | `func_2245` | `func_2244` |
| 0x15F |  | frame+hitlag (8) | `func_2245` | `func_2244` |
| 0x160 |  | start (0) | `func_2345` | `func_2243` |
| 0x160 |  | start (1) | `func_2346` | `func_2243` |
| 0x160 |  | end (2) | `func_2348` | `func_2243` |
| 0x160 |  | start (3) | `func_2349` | `func_2244` |
| 0x160 |  | frame (4) | `func_2245` | `func_2244` |
| 0x160 |  | hitlag frame (5) | `func_2245` | `func_2244` |
| 0x160 |  | end (6) | `func_2350` | `func_2244` |
| 0x160 |  | frame (7) | `func_2245` | `func_2244` |
| 0x160 |  | frame+hitlag (8) | `func_2245` | `func_2244` |
| 0x161 |  | start (0) | `func_2351` | `func_2243` |
| 0x161 |  | start (1) | `func_2352` | `func_2243` |
| 0x161 |  | end (2) | `func_2355` | `func_2243` |
| 0x161 |  | start (3) | `func_2358` | `func_2244` |
| 0x161 |  | frame (4) | `func_2359` | `func_2244` |
| 0x161 |  | hitlag frame (5) | `func_2360` | `func_2244` |
| 0x161 |  | end (6) | `func_2245` | `func_2244` |
| 0x161 |  | frame (7) | `func_2245` | `func_2244` |
| 0x161 |  | frame+hitlag (8) | `func_2245` | `func_2244` |
| 0x162 |  | start (0) | `func_2361` | `func_2243` |
| 0x162 |  | start (1) | `func_2362` | `func_2243` |
| 0x162 |  | end (2) | `func_2364` | `func_2243` |
| 0x162 |  | start (3) | `func_2365` | `func_2244` |
| 0x162 |  | frame (4) | `func_2366` | `func_2244` |
| 0x162 |  | hitlag frame (5) | `func_2245` | `func_2244` |
| 0x162 |  | end (6) | `func_2245` | `func_2244` |
| 0x162 |  | frame (7) | `func_2245` | `func_2244` |
| 0x162 |  | frame+hitlag (8) | `func_2245` | `func_2244` |
| 0x163 |  | start (0) | `func_2367` | `func_2243` |
| 0x163 |  | start (1) | `func_2369` | `func_2243` |
| 0x163 |  | end (2) | `func_2371` | `func_2243` |
| 0x163 |  | start (3) | `func_2368` | `func_2244` |
| 0x163 |  | frame (4) | `func_2245` | `func_2244` |
| 0x163 |  | hitlag frame (5) | `func_2245` | `func_2244` |
| 0x163 |  | end (6) | `func_2245` | `func_2244` |
| 0x163 |  | frame (7) | `func_2245` | `func_2244` |
| 0x163 |  | frame+hitlag (8) | `func_2245` | `func_2244` |
| 0x164 |  | start (0) | `func_2372` | `func_2243` |
| 0x164 |  | start (1) | `func_2374` | `func_2243` |
| 0x164 |  | end (2) | `func_2376` | `func_2243` |
| 0x164 |  | start (3) | `func_2373` | `func_2244` |
| 0x164 |  | frame (4) | `func_2245` | `func_2244` |
| 0x164 |  | hitlag frame (5) | `func_2245` | `func_2244` |
| 0x164 |  | end (6) | `func_2245` | `func_2244` |
| 0x164 |  | frame (7) | `func_2245` | `func_2244` |
| 0x164 |  | frame+hitlag (8) | `func_2245` | `func_2244` |
| 0x165 |  | start (0) | `func_2394` | `func_2243` |
| 0x165 |  | start (1) | `func_2395` | `func_2243` |
| 0x165 |  | end (2) | `func_2398` | `func_2243` |
| 0x166 |  | start (0) | `func_2399` | `func_2243` |
| 0x166 |  | start (1) | `func_2400` | `func_2243` |
| 0x166 |  | end (2) | `func_2402` | `func_2243` |
| 0x167 |  | start (0) | `func_2403` | `func_2243` |
| 0x167 |  | start (1) | `func_2404` | `func_2243` |
| 0x167 |  | end (2) | `func_2406` | `func_2243` |
| 0x168 |  | start (0) | `func_2407` | `func_2243` |
| 0x168 |  | start (1) | `func_2408` | `func_2243` |
| 0x168 |  | end (2) | `func_2411` | `func_2243` |

## Clones v1 (`greninja_clones_v1.zip`)

The user's design: down special charges (hold) an ability that makes two clones; a burnout after it; smash attacks
keep their charge, only come out fully charged, auto-release once full, and chain. Everything below is in
`fighters/gekkouga/clones.c` (his MSC), `fighters/gekkouga/weapons/clone.c` (the clone article's MSC),
`tools/gekkouga_build.py` (MSC sites, ACMD, data), `tools/gekkouga_clone_cave.py` (the executable, exe_v46z_gk1:
docs/native-notes.md "Greninja's clones"). Tests: `tools/gekkouga_clones_test.py` (104 checks: MSC logic in an MSC
interpreter, the clone MSC, the scripts, the package, msc_stack_check, import_call_check) and
`tools/gekkouga_clone_cave_test.py` (56 unicorn checks, release and diag exe). Build:

```sh
python3 tools/gekkouga_build.py msc VANILLA.c fighters/gekkouga/gekkouga.c
python3 tools/gekkouga_build.py all VANILLA_ROOT USER_ROOT OUT      # VANILLA_ROOT/fighter/gekkouga (model, motion),
                                                                    # USER_ROOT/fighter/gekkouga/script/animcmd (his scripts)
python3 tools/rpx_patch.py exe_v46z_ui10.rpx exe_v46z_gk1.rpx $(python3 tools/gekkouga_clone_cave.py --rpx exe_v46z_ui10.rpx)
```

Sources: the base MSC is vanilla + `universal_mechanics.py` (it compiles to the same functions as the user's
`fighters_rolloff_hero_v1` gekkouga.mscsb: msc_fingerprint 0 differ); the scripts are the user's
(`fighter-modded-scripts-only.zip`: his roll-off game.bin and AttackAirN's shield-break hit); the clone's model / motion
are vanilla Smash 4 (`fighter-smash4-vanilla.zip`: model/body c00-c07, motion/body/main.pac).

### Down special: the charge (status 0x155, no counter)

- `gk_lw_press()` replaces the four down special inputs (`func_43`, `func_58`, `func_675`, `func_1999`): during the
  ability / burnout nothing; charged: the ability starts (no status change); else SpecialLw (0x155).
- 0x155's main is the vanilla one (motion 0x271 / 0x289) with `gk_lw_main()`, its loop `gk_lw_loop()`: the counter
  shape is never switched on (no `func_2344`, no IASA); while special is held (`ControlModule(0x2712, 1)`) the stance
  is held at frame `gk_lw_hold_frame()` = **14** (its vanilla counter window is 8-30; rate 0), released -> Wait / Fall
  with the charge kept. The vanilla stance effect 0x3300009 (frame 5, the afterimage flash) is requested again every
  **20** frames while held. Air: the vanilla stance physics (slow fall).
- `gk_lw_tick()` (global16: not in hitlag) adds 1 a frame up to `gk_lw_full()` = **300** (the user's 5 s). At 300 the
  stance ends with the common star flash 0x1000069; charged and idle, the common sparkle 0x10000BD over his head every
  **45** frames.
- **The bar**: 10 pips, one lit every 30 frames: the common effect 0x1000047 ("small colour-changing light",
  reference/msc-note-sheet/Global_GFX_IDs.csv: a continuous one) following joint 0 at y 25, spaced 2.2 along his
  facing (left to right on screen), killed when the stance ends. Approximate: the effect's look in game is untested.
- Kept: across presses and stocks (MSC globals); 0 at the match's start (Entry 0x14F).

### The ability (720 frames)

- Activation: the charge used; frame 0 article 6 (the left-spawned clone, VAR_30 = 1) is made, frame 3 article 7
  (VAR_30 = 2), each with the Substitution smoke (vanilla SpecialLwHit's 0x3300006, size 1.3) at his X -/+ **14**
  (`gk_gap()`), at his Y + 6.
- Every frame (`gekkouga_frame()`, func_82: hitstop included): the channel his clones read (his VAR_24 / 25 the two
  offsets, 26 the clones alive, 27 / 28 / 29 the motion / frame / rate to play: his MotionModule(7) / MotionModuleF(1)
  / MotionModuleF(0xA), or Wait1 (0) / Fall (0x24) while on a ledge (0x72-0x7A), hit / grabbed / down (0x3F-0x5B),
  in his Final Smash (0x156, 0x165-0x168) or KO'd; 31 = 4747 while the ability runs); VAR_20 (flags for the exe:
  1 tag hidden, 4 clones out, 2 burnout); the clone capsules (below); a clone hit (VAR_21).
- **Swap**: special pressed this frame (`ControlModule(0x2710, 1)`) with the stick down (Y < -0.3): the press is cleared
  (Buffer_Clear's MSC variable `0x0F0003C9` = 32: specials; and this frame's special command bits), then with X < -0.25
  the left-spawned clone, X > 0.25 the right-spawned one: he moves by its offset (`WorkModule(2, off, 0x0F000000)`,
  the game's set_pos: no status, sound, effect or camera command), its offset becomes minus it, the other clone's
  offset minus it too (it stays where it is). A gone clone: nothing. **10** frames before another swap.
- **A clone hit**: the exe reports VAR_21 = 10000 + (the hitting object's X - his X); the alive clone with the
  nearest offset is removed (ArticleModule 0x2712), its smoke, and his Substitution log made where it stood: he is
  put there for the call (`PostureModule(3)`), `BattleObject(0x3F7)` (the log: item kind 0x89; 0x3F8 the rare doll,
  0x8A, with SpecialLw param 0x8000003's chance, vanilla's), and put back, all in the same frame.
- The capsules: his shield group 1 (built by the exe as 4 capsules on joint 0 at z = -28, -14, 14, 28 along his
  facing, y 3-15, radius 5.5); each frame shape i is on when an alive clone's offset x his facing falls in its band.
- The end (720 frames): both clones removed (smoke), the channel closed (VAR_31 0), the burnout. A KO (0xB1 / 0xB2)
  ends the ability without a burnout.

The clone article (weapon kind 0x1A1, his articles 6 / 7: docs/native-notes.md "Greninja's clones"): bunshin's native
kind (his Final Smash clone) with KineticModule / AttackModule; model/clone/c00-c07 = his body's (the owner's
costume), motion/clone/main.pac = his body's (every motion); its MSC (`weapons/clone.c`, his moon article's framework)
finds him (the slot whose SLOTn_SHARED_7 is 4747, nearest), its id (his VAR_30 on its first frame), and every frame
stands at his X + its offset and his Y, faces his way, and plays his motion: a new motion or a restart (his frame
lower than last frame's) -> `MotionModule(1, kind, his frame, his rate)`, else his rate and, more than a frame off
(its own hitlag), his frame. Hidden when not alive / the channel is closed. Its scripts (`gekkouga_build.py`
`clone_scripts`): his body game scripts that have hitboxes (37), hitbox / timing commands only (flags, grabs,
articles, motion rates dropped; loops / conditions kept whole), bones as the article's joints (0x7D0 + his model.jtb
table-0 entry: the forward smash's 0x19 -> 0x7E9; a table-1 joint goes to its nearest ancestor in table 0: the scarf's swing bones 0x40B / 0x40D / 0x40F (SWG_CMant4 / 6 / 8__swing) -> 0x7E2, HeadN: approximate), his smashes'
damage x **1.4** (Smash 4's full charge, which an article's attack doesn't get); not his counter attacks or Final
Smash; their effect scripts (25) with EFFECT / follow / flip / Sword_Glow only; no sound.

### The burnout (480 frames)

- Down special: nothing (the press cleared, `gk_lw_press()` 0, even charged).
- Grey: `ColorBlendModule(0x2711, 110, 110, 110, 170)` + priority `0x65` every frame (his Final Smash's fade uses the
  same op / priority), `0x2711` alpha 0 and `0x2713` (FLASH_OFF) at the end.
- Half speed: VAR_20 bit 2 -> the exe puts the Timer item's slow on him (SlowModule slot 3, rate 2, its own frames;
  cleared when the bit goes): animations, movement, status (the game's per-object slow).

### Smash attacks

- Stored per smash (`gk_s4`, `gk_hi4`, `gk_lw4`, frames 0 - **60**: Smash 4's hold), per player (his MSC), kept across
  stocks, 0 at the match's start.
- Start statuses (0x2B / 0x31 / 0x2E, mains `func_286` / `func_295` / `func_303` + `gk_sm_start_main`; loops
  `gk_sm_start_loop`): at the hold point (the scripts' flag 0x2100001B: frames 8 / 9 / 5) an automatic one releases
  (the attack status with keep, the hold exit's values: ratio float 0x1000000 = 1.0, flag 0x21000002), a held one
  holds, a released one goes to Wait (no attack). Automatic: a stored full charge (used: back to 0) or a chain
  (the store untouched).
- Hold statuses (0x2C / 0x32 / 0x2F): `gk_sm_hold_tick` (global16, not in hitlag) adds 1 to the store (capped at
  60), `gk_sm_hold_loop`: full -> the star flash and Wait (ready, no attack); released -> Wait (kept, no attack).
- Chains (`gk_chain_try` first in the attack loops `func_293` / `func_302` / `func_309`): on the ground, from the
  frame the move's last hitbox ends (**forward 16, up 22, down 19**: the scripts' last Remove_All_Hitboxes) to the
  move's end, a smash command (global24 0x10 / 0x20 / 0x40) not yet used in the chain starts that smash (auto); a
  forward smash the other way turns first. The chain (`gk_chain`) ends when he leaves the smash statuses (0x2B-0x33):
  Wait after the move, a hit, any other action; after all three it can't continue.
- Growth: every smash that comes out is a full charge (stored or chained), so the growth for the full charge
  frames (60 of 60) is applied in the scripts: his attacks4 / attacks4hi / attacks4lw / attackhi4 / attacklw4 hitbox
  Size and effect Size x **1.5** (`gk_smash_grow()`, 33 values). Damage / knockback: the game's own full-charge x1.4
  (the ratio 1.0).
- Down smash out of a run (universal mechanics) enters 0x2E: the same rules.

### What is approximate / untested (nothing has run in game)

- The clones don't have their own physics: a fixed offset from him (off a ledge they float; launched, they go with
  him). They mirror his motions, not his inputs. (v2: they fall: "Clones v2".)
- Clone "hurtboxes" are capsules on his shield, not the article's: a hit is given to the nearest clone by the hitting
  object's position; a hit touching a clone and him meets the shape first (the clone takes it); the common shield
  spark shows. The cave-built group replaces his counter shape (his 5-shape pool: the guard's + 4).
- An article's hit doesn't give him hitlag; a clone in its hitlag catches back up with his frame. (v2: it does.)
- No hand / face part animations on the clones (only main.pac); no sound; no smash-charge effects on them. (v2: hands
  and face.)
- The name tag: the HUD cursor of his player number moved off screen (FAR = -100000) after the HUD placed it: assumes
  the HUD's player order is the fighter table's.
- The base kind's native code (bunshin) runs for the clone; its singleton's other methods are bunshin's.

## Clones v2 (`greninja_clones_v2.zip`)

The user's v2 request (v1 not yet tested in game): the clones get his face and hand animation, a clone's landed hit
puts him in hitlag, and the clones fall instead of floating. The package is an update over v1: only the files that
differ from it (both MSCs, 5 motion pacs, 4 face files x 8 colours) and README.txt, with exe_v46z_gk2 (+ diag).
Tests: `tools/gekkouga_clones_test.py ... --v1=greninja_clones_v1.zip` (147 checks), `tools/gekkouga_clone_cave_test.py`
(66 unicorn checks on gk2 and gk2_diag), `tools/supamario_ui_cave_test.py` (outline5 -> gk2) 422 / 0,
`tools/import_call_check.py` 0 on both. No script or motion slot changed: Sm4shCommand stays v1.7.26.

```sh
python3 tools/rpx_patch.py exe_v46z_ui10.rpx exe_v46z_gk2.rpx $(python3 tools/gekkouga_clone_cave.py --rpx exe_v46z_ui10.rpx)
python3 tools/rpx_patch.py exe_v46z_ui10_diag.rpx exe_v46z_gk2_diag.rpx \
    $(python3 tools/gekkouga_clone_cave.py --rpx exe_v46z_ui10_diag.rpx --diag)
```

### Face and hands

- The clone weapon's motion info (exe) now carries his: its words 2-5 = his fighter motion info's (`0x1037C470`: the
  parts list `0x10378F70` x 6, the groups `0x10378FA0` x 5) and its 668 entries keep his flags (v1: 0). A part entry
  is {a 668-word table: motion kind -> that part's animation hash, the part id}: Lhand 4, Rhand 3, Gekkougapt1 6,
  Gekkougapt2 7, Gekkougasw1 8 (and one with no table). The clone plays motion K with his main.pac, so the part
  tables line up with its motion kinds.
- `motion/clone/` gets his body's lhand / rhand / gekkougapt1 / gekkougapt2 / gekkougasw1.pac (`CLONE_MOTION_PACS`);
  `model/clone/cXX/` his body cXX's material_anime_eye / eyelid / face.pac (the per-motion eye, eyelid, mouth material
  animations; the eyelid's are mesh visibility by mesh name) and model.moi (`CLONE_FACE_FILES`). Not model.sbwl /
  model.ik (bunshin's file set has neither).
- His expression scripts hold no face changes (SLOPE, rumble, visibility, SET_CURSOR, item / article visibility): not
  copied; the face is the material animations per motion.
- Approximate: no vanilla weapon has motion parts (every weapon descriptor's motion info has words 2-5 zero), so
  whether the article's MotionModule plays them, and whether the article's resource load takes the extra pacs, is
  untested. The fighter's set-up and the article's both pass the motion info through the init block's `+0x58`
  (`0x02E5412C` / `0x02BCBB30`), which suggests the same consumer.

### Hitlag from a clone's hit

- Exe: the clone's hit method (its singleton vtable `+0xAC`), for result bits 0x17 (a hit 0x13, a shield 0x4) still
  returns 0 (kept) and now first reads the clone's VAR_0 (its owner's slot, 1-8: the clone MSC writes it every frame)
  through the clone's WorkModule (weapon `+0x28` the accessor, `+0x28` its WorkModule, get_float vt `+0x44`), finds
  that fighter table entry (`[[0x1035184C]]`: count `+8`, entries `+0` x 0x76B0, live `+0x1E` >= 4) and sets its
  VAR_22 (`0x0F000316`) = 1.0 (his WorkModule: `[entry + 0x28] + 0x726C`, set_float vt `+0x4C`). Diag: `S4GL clone
  hit landed: owner slot N hitlag`.
- MSC (`gk_clone_hitlag`, every frame of the ability, first): VAR_22 set -> cleared; not already in hitlag
  (`StopModule(1)`) -> `StopModule(2, n)`, n = the biggest "hitstop of the last hit taken" (`0x0F000044 + 8 x target`)
  among the fighters in hitstop now (`0x0F000043 + 8 x target`, targets 3-10 = slots 1-8; docs/position-variables.md),
  at least `gk_hitlag_min()` = **4**. Already in hitlag (his own hit, or the other clone's on the same frame): nothing
  more (no stacking).
- The freeze: the channel's rate is 0 while he is in hitlag (`StopModule(1)`), the clones' fall too.
- Approximate: the length is read the frame after the hit (the victim's hitstop of that hit, as he'd have had); on a
  shield or a non-fighter it is the minimum unless a fighter is in hitstop then.

### The clones' fall (`gk_physics`)

- His MSC owns each clone's place: `gk_lx / gk_ly / gk_lvy` (left-spawned), `gk_rx / gk_ry / gk_rvy`, frames falling
  on its own `gk_lfall / gk_rfall`. X = his X + its offset (unless he is detached). Y:
  - he is in the air by his own doing (situation 2, not detached, not on a ledge): it copies his vertical movement
    (dy = his Y - his last Y: a jump with him, from its own height);
  - else gravity **0.18** / max fall **1.85** (his `fighter_param` 0x03000018 / 0x03000019,
    reference/fighter_param_attributes.csv);
  - moving down it lands on the first floor of the segment (x, from) -> (x, y + dy - 0.5) (standing last frame: down
    to y + dy - `gk_snap()` **3**, slopes): the stage line test the exe has had since exe_v46w (`Line_Test`'s MSC
    variables `0x0F0003D0`-`3D8`, his own: Space 1 world, Floors 0 = passable platforms too; LINE_KIND 1 a floor).
    From = y + 3 falling on its own, y - 0.05 while copying him (a platform drop isn't stopped by the platform he left).
  - frozen while he is in hitlag.
- **Detached** (he is launched / grabbed / thrown / down: statuses 0x3F-0x5B): X fixed too (they stay where they were)
  and they fall; when he is out of those statuses: back in formation (his X + offset, his Y) with a smoke each.
- **Off the stage**: falling on its own more than `gk_fall_frames()` = **100** frames -> removed with its smoke, no log
  (the blast zone isn't read).
- **On a ledge** (0x72-0x7A): no copy (they stand or fall).
- The channel (his VAR_24-31, v2): 24 / 25 the left clone's X / Y, 26 / 27 the right one's, 28 his motion's frame, 29
  its rate (0 in hitlag), 30 its kind, 31 = 4747000 + flags (1 / 2 alive, 4 / 8 being made: the first 2 frames after
  each `ArticleModule(0x2710)`, 16 / 32 falling on its own more than 2 frames). Mirror-off statuses: Wait1, Fall
  when he is in the air with them (copying).
- The clone MSC: finds him (the slot whose VAR_31 is 4747000 + 0-63, nearest), which clone from the "being made" bit
  (none yet: it waits hidden), stands at its X / Y, faces his way, plays his motion (Fall 0x24 from 0 at its own loop
  while its fall flag is on), writes its VAR_0 = his slot.
- **Swap**: he goes to the clone's (x, y) (`WorkModule(2, dx, 0x0F000000)` and `(2, dy, 0x0F000001)`), it to his old
  (x, y); the other clone stays.
- **Capsules** only for clones in formation (alive, not detached, within 3 of his Y): his shield shapes are at his
  height; a clone on another floor or left behind can't be hit (v1's hurtbox design).
- **The name tag**: also the vanilla cursor op `BattleObject(0xA, 0)` (ACMD SET_CURSOR's, Rebirth's `func_230`
  shows it with 1) at the start and every 60 frames, `BattleObject(0xA, 1)` at the natural end; the exe's HUD hide stays.

### What is approximate / untested (v2)

- Whether the article plays motion parts / loads the part pacs and face files (above).
- Walls and ceilings don't stop a clone; no slide on steep slopes; a clone copying his fall isn't counted as "off the
  stage" (it goes when he is KO'd).
- The hitlag starts a frame after the hit; its length as above.
- Launched: they play Wait1 (Fall while falling) and come back by smoke, not by walking.

## Clones v3 (`greninja_clones_v3.zip`)

The user's v1 + v2 test ("clones don't appear"; the smash growth not visible), v2's limits, and new smash requests.
The package is an update over v1 + v2: both MSCs, his body effect.bin, exe_v46z_gk3 (+ diag) and README.txt.

### The clones never appeared (v1 / v2): the resource category

The weapon u16 flags (`0x1018A970` table, the cave copy for kinds past 0x184) bits 0x80 / 0x1 / 0x100 are the
resource request's categories 1 / 4 / 8 (`0x030C37AC`: `0x0320E6AC` / `0x0320E634` / `0x0320E6C0`; none -> 2, loaded
with the fighter): the loader walks the fighter's article list and adds a kind's files only when the request's mask has
its category. Bunshin's 0x87D has 0x1 (4: his Final Smash load, like his tatami 0x871 / moon 0x871), and the clone
copied it: its model / motions were never loaded outside a Final Smash, so no clone was made (the user's log: the
ability ran, S4GT / S4GS, nothing of the clones). v3: 0x87C (`CATEGORY_BITS` cleared). Diag (TEST_ONLY): `S4GF slot
flags gen` on every change of his VAR_20 (MSC bits: 1 tag, 2 slow, 8 ready, 16 / 32 the clones made; gen = the last
`ArticleModule(0x2710)` result, his VAR_23), `S4GI` the clone's set-up (+0x1C, the object made), `S4GC` its first
frame with its id / owner slot (its MSC ran), `S4GU` the HUD's first hide of a player's tag. Not explained yet: the
tag not hiding in the user's log (S4GT logged; S4GU will say whether the HUD part ran) and 48 `GX2RSetAttributeBuffer`
errors ~8 s before the ability (during the charge).

### Smash attacks (v3: the user)

- One store (`gk_smash`) for all three smashes, full **120** frames (`gk_smash_full()`): any hold adds to it; full ->
  the flash and Wait (no attack); the next smash of any direction releases at once and empties the store; a chain's
  smashes release at full without it (the store untouched). The hold loop is ours (`gk_sm_hold_loop`), so the vanilla
  60-frame hold limit doesn't apply; the release sets the hold's exit values (ratio 1.0: the game's full-charge damage).
- Effects: his attacks4 / attackhi4 / attacklw4 effect scripts' Size x **5** and their Sword_Glow points x5 (the trail's
  length; the user's "no size increase": v1 / v2 scaled only Size x1.5, not the trail, the main visual). Hitbox Size
  stays x1.5. The hold scripts' (attacks4hold / attackhi4hold / attacklw4hold) effects are at size 0 and his MSC
  (`gk_sm_fx`, from the hold tick) draws them by the charge: 1 + 4 x charge / 120 (linear): the sparkle 0x1000019 and
  flash 0x1000010 every 5 frames, the water sword 0x3300007 killed and made again every 10 (both hands for up / down).
  The clone's copies of the smash effects are unscaled. Tests: `tools/gekkouga_clones_test.py ... --v1=greninja_clones_v1.zip --v2=greninja_clones_v2.zip`
(173 checks), `tools/gekkouga_clone_cave_test.py` (81 / 84 unicorn checks, gk3 / gk3_diag), `supamario_ui_cave_test.py`
(outline5 -> gk3) 0 failures, `import_call_check` 0 on both. No script or slot changed (Sm4shCommand stays v1.7.26).

```sh
python3 tools/rpx_patch.py exe_v46z_ui10.rpx exe_v46z_gk3.rpx $(python3 tools/gekkouga_clone_cave.py --rpx exe_v46z_ui10.rpx)
```

### Found: the clone article's per-frame template

The weapon switches run a per-kind template (docs/native-notes.md "Greninja's clones" v3). The clone's base kind was
bunshin, whose update template updates only its own modules (+0x18 / +0x24 / +0x38 / +0x44 / +0x8C / +0xA0 / +0xB4 /
+0xB8): never the AttackModule (`0x02C08230` on accessor +0x50) or the KineticModule v1 added to its row. v1 / v2's
clone hitboxes therefore likely never updated. v3's base kind (the switches only) is **lizardonm (0x15C)**, Charizard's
Final Smash form: its template updates bunshin's modules plus +0x1C, Kinetic +0x34, Attack +0x50, Hit +0x58, +0xA4
(no GroundModule), and its module row (bunshin's slots + Kinetic, Attack, Hit 6 `0x02BCC808`, Damage 20 `0x02BCC9D0`)
is the clone's whole row. Its templates call the specializer only through the vtable (no direct calls into
lizardonm's own code, scanned in all 11 switches), so the clone keeps bunshin's specializer methods (its vtable copy).

### (a) Hurtboxes anywhere, exact clone, independent hits

- Exe: the clone's specializer +0x1C (bunshin's is a `blr`) gives its HitModule his 8 hurtboxes (his vl group 5,
  vanilla `fighter_param_vl_gekkouga.bin`: bones 12 19 22 16 8 4 9 5 as the article's joints 0x7D0 + jtb, checked with
  `gekkouga_build.bone_map`) through vt +0x4C(&{data, 8}, 0), the Duck Hunt can's set-up call.
- A hit on it: the poller in the specializer's +0x64 / +0x84 / +0x8C / +0x94 (every frame phase the templates call,
  `(spec, weapon)`) reads its DamageModule vt +0x7C(0) (the damage taken this frame, Mii Gunner's flame pillar's read)
  and, when > 0, writes its owner's VAR_21 = 20000 + its VAR_1 (its id, its MSC writes it) through his WorkModule, then
  runs bunshin's method with the same arguments. His MSC kills exactly that clone (log at its place).
- His shield-capsule route is off (MSC flags bit 4 no longer set, shapes never on): no shield spark, and an attack
  touching him and a clone hits both (separate objects, separate hit records). The exe's group-1 / slot 42 / 43 parts
  stay (dormant).

### (b) Walls and ceilings, (d) slopes

`gk_clone_phys` with `gk_line` (the stage line test, Line_Test's variables: kind 1 floor, 2 wall, 3 ceiling, hit X / Y):
- X: a horizontal test at its feet + `gk_wall_y()` **5** from where it is to its target (his X + offset); a wall stops
  it `gk_wall_gap()` **3** short (its offset gives way); free again, it goes back. Swaps use its real place (his move
  = its X - his X, the other clone keeps its place).
- Up: a test from its head (+ `gk_head()` **15**) by the rise; a ceiling stops it (vy 0).
- Standing (it stood last frame): the floor under its new X from y + reach down to y + dy - reach, reach = `gk_snap()`
  **2** + `gk_slope()` **1.4** x its step (a floor line has normal Y >= 0.6: at most 1.33 per unit). A cliff face is a
  wall line (kind 2), not a step. Falling: from y + 0.5. Copying his jump: its floor stops it once it lands while he is
  still coming down; level with him (y = his last Y) the floor he left is skipped (a platform drop).

### (c) The blast zone

The game removes a weapon past the stage's blast zone without its MSC (seen in game for Supamario's kamehameha, a
fireball copy). v3: each clone's MSC sets its bit (1 / 2) in his VAR_30 (SLOTn_SHARED_6) every frame; his MSC reads and
clears it every frame (`gk_heartbeat`); a clone older than 6 frames whose bit is off **3** frames running is gone
(`gk_gone`: no log). The channel's motion kind moved into VAR_28 (kind x 1024 + frame) to free VAR_30. Fallback: 300
frames falling on its own. Not found: the stage's dead-range data in the Wii U executable (searched: the fighters'
outfield / dead event `0x02E1A45C`, the weapon templates' helpers; the 3DS's `GroundUtility::check_dead_area` has no
Wii U counterpart identified), so the MSC doesn't read the blast zone itself.

### (e) / (f) Hitlag at the hit, from the damage

Weapons have no attacker hitstop handler (the weapon class's vt +0xEC is `li r3, 0; blr`), so the clone's hit-result
method (+0xAC, called when its attack connects / is shielded) does it: from the clone's AttackModule hit records (`+0x14`
arrays of 0x174, `+0x18` count, node `+0x27` hitbox id; slots `[+0x40] + id x 0x84`, `+0x18` damage) the hitbox with the
most damage that has records; `0x02C2678C(his accessor, its data, damage, 1.0 (the attacker handler's multiplier,
`0x10105DCC`), side 1, its own multiplier)` = the game's attacker hitstop; his StopModule (accessor +0x48) vt
+0x8C(frames, 1) (the fighters' setter keeps the longer: no stacking). VAR_22 = 1.0 still: his MSC's fallback (the
victims' hitstop, at least 4) only if he isn't in hitlag by then. Not applied: the attacker handler's rate (HitModule
vt +0x17C, 1 normally) and acmd_ext's per-hitbox attacker hitlag extras.

### (g) Left-behind clones

Kept: they reappear next to him in smoke when he is out of the launched / grabbed statuses (walking back could take
them through gaps and walls).

### What is approximate / untested (v3)

- In game: the template swap, the hurtbox set-up, the damage poll, the native removal past the blast zone for this kind.
- The hitlag hitbox: the strongest with records during the move (usually the one that just hit).
- One wall test height; the fallback fall timer.

## Clones v4 (`greninja_clones_v4.zip`)

The user's v3 runs crashed when a clone was made (the release exe, then gk3_diag: two `S4GI` lines at the match start,
the clone objects built; `S4GF flags=8` ready; the crash on the press, before the clone's first frame). The cause isn't
known from the logs, so the native parts became build features (`tools/gekkouga_clone_cave.py --features`, `FEATURES`):
`template` (lizardonm's per-frame routine and module row; else bunshin's exact row and routine: no Attack / Hit / Damage),
`parts` (his motion parts and flags on the clone), `hurt` (its hurtboxes at +0x1C), `poll` (the damage pollers). The
release exe exe_v46z_gk4 is the safe set (none of them: the clones are visual only); TEST_ONLY has one diag exe per
`VARIANTS` step: A_safe, B_template, C_hurt (template + hurt + poll), D_full (= v3). More diag: `S4GJ` after the set-up,
`S4GP` the first update of a made clone (the +0x64 poller, before its MSC names it), and his MSC now makes each clone a
frame after requesting it (VAR_20 bits 64 / 128, logged by `S4GF`), so the log brackets the generate.

The `GX2RSetAttributeBuffer` bursts in the user's logs aren't the clones': the same burst is in an older log of theirs
(a Supamario test) at the match start; the clone objects are built at the match start too, just before it.

Smash hitboxes grow with the effects (the user): `GROW` 5 (was 1.5) on his attacks4 / attackhi4 / attacklw4 hitbox Size;
on his water-sword bones (`SWORD_BONES` 24 / 25) the hitbox offsets x5 too, as the sword effect and its trail grow from
the bone; body-bone hitboxes (the up smash's geyser on bone 0, the forward smash's forearm on 23) keep their place. The
biggest is 30 (6 x 5), his largest vanilla hitbox's size (his Final Smash). The clone's copies get the same hitboxes, and
now his smash effects too (`flatten`: their conditions' True branches; v3's clones had none). Tests:
`gekkouga_clones_test.py ... --v1 --v2 --v3`, `gekkouga_clone_cave_test.py --features=...` on every exe in the package,
`supamario_ui_cave_test.py` on gk4, `import_call_check` 0 on all five.

## Clones v5 (`greninja_clones_v5.zip`)

The user's v4 logs: A_safe made both clones and the game updated them (`S4GP`), but the clone MSC never ran (no `S4GC`),
and his heartbeat dropped each ~8 frames later; B_template (lizardonm) crashed inside the generate (`flags=65`, then
nothing). Why A's MSC never ran: the MSC agent is weapon row slot 8 (accessor +0x1C, constructor `0x02BCC820`):
shuriken / water / moon have it, bunshin / tatami / monsterball (no MSC files) don't, and bunshin's per-frame template
doesn't update +0x1C; moon's is bunshin's plus that update. v5's feature sets (`tools/gekkouga_clone_cave.py`
`FEATURES`, `VARIANTS`):
- safe (release exe_v46z_gk5, TEST_ONLY A_safe): base kind moon (0xFC), bunshin's row + moon's MSC agent;
- attack (B_attack): base Mario's pump (0x2: bunshin's template + the agent + the AttackModule's update; u16 0x87C like
  the clone), bunshin's row + the pump's Attack / +0x2C / agent;
- hurt (C_hurt): base mewtwom (0x168), its row + lizardonm's DamageModule (slot 20), hurtboxes and damage pollers;
- parts (D_parts): v2's motion parts on the safe set.
lizardonm is out (the v4 crash). His MSC: a clone never heard from is kept 120 frames (`gk_beat_grace()`) before the
heartbeat drops it (v4: 6 + 3), its "being made" bit stays until its heartbeat is first seen, and VAR_23 holds the
removal reason (`gk_why`: 100 heartbeat, 200 hit, 300 end / KO, 400 fall, + the clone's id), logged by `S4GF gen=`.
Diag `S4GV r29 cursor`: every HUD cursor call's index once (the tag: v4 had no `S4GU`).

## Clones v6 (`greninja_clones_v6.zip`)

The user's v5 A_safe log: the clone MSC runs now (`S4GC`), no crash; but both clones reported `id=1` (owner slot 1 is
right: the clone counts slots from 1, `S4GF` from 0), one clone was "completely black" and vanished within a second,
the other "poofed instantly", and both were dropped by the heartbeat (102 at the grace, 101 later).
- **id**: his "being made" bit (VAR_31 4 / 8) is now only the last-made clone's (`gk_last_made`); v5 kept the left's on
  until its heartbeat was seen, so the right clone, made 3 frames later, took id 1 too: both stood at the left place
  and beat bit 1, the right one was dropped as never heard from.
- **black**: the clone's specializer was a copy of bunshin's, whose +0x34 (`0x02AF6738`, at its start) sets the model
  colour (0, 0, 0, 255) through [acc+0x38] vt +0x4C (the Final Smash's shadow clones) and links it to its owner
  ([acc+0x68] vt +0x3BC). Now a copy of the moon's (`VT_BASE` 0xFC), whose +0x34 only sets the model scale.
- Diag `S4GX clone id at x y`: each clone's posture every 30 frames, its first 8 logs.
- **The charge gauge on his damage panel** (the user): the pips over his head and the ready sparkle are gone (the star
  flash at full stays). His MSC writes VAR_19 = mode x 1000 + 0-100 (`gk_gauge`: 1 the charge, 100 = ready; 2 the
  ability's time left; 3 the burnout's; 0 none). The exe hooks the damage panel's update (InfoGadgetDmg vtable +0x3C,
  `0x100871D8 + 0x3C`, which points at the trait badge cave: we call it first) and for each panel slot whose starting
  kind and current fighter are Greninja (the trait badge's slot -> fighter route: `[0x102F7024]` entry -> object ->
  accessor -> WorkModule) shows Little Mac's KO meter (`ko_mc`, the slot's +0x18C) and sets it with the game's
  `0x02663C54(panel, slot, 0-100)` (num_0 / num_1-10 / ko blinking; it no-ops on an unchanged label), coloured per mode
  with `0x032CDF80` (as is / blue / grey), hidden for mode 0. Diag `S4GB slot mode value` on every tenth. Tested in
  unicorn (`gekkouga_clone_cave_test.py` panel checks: the hook, the calls per mode, the colours, Little Mac's and empty
  slots untouched); the art is Little Mac's meter (its full frame reads "KO").

## Clones v7 (`greninja_clones_v7.zip`)

The user's v6 A_safe log: ids 1 / 2, both clones alive for the 12 s and placed right (`S4GX`), the gauge values right
(`S4GB`), no `S4GV` at all; on screen: no clones, no gauge, the tag shown. Executables only:
- **Invisible clones**: the moon's specializer +0x34 (`0x02AF6B2C`) sets the model scale from the start's init block
  +0x68 ([acc+0x18] vt +0xE4), which the Final Smash fills and our generate leaves 0. The clone's +0x34 is now ours
  (`w_start`): nothing (diag `S4GZ` logs the init's scale x100).
- **No gauge**: the panel's colour transform multipliers are 0-100 (as its alpha, "Panel alpha"); v6's 0xFF alpha hid
  the meter. `GAUGE_COLOURS` now 0-100 (as is / blue / grey).
- **The name tag**: the HUD hook (`0x028E40B4`) never ran in game: that bl is skipped unless the cursor's
  `0x03091830` says so. The tag now goes through the game's own SET_CURSOR route (the ACMD handler `0x02BE7C80`): slot 13
  sends his object (`[accessor + 0]`) the message {0xA, visible} (`0x02BF2108` (manager, &handle, id, 1), `0x02BF019C`
  (&handle, &{`0x1010CC00`, 6, &{&{0xA, v}, 2}, 0})) when the tag bit comes on and every 30 frames after (`gk_tags`),
  {0xA, 1} once when it goes. Diag `S4GW`.
- **The round gauge** (the user's vector set, 41672): `tools/gekkouga_gauge_art.py` extracts the round elements from its
  5250 x 3500 preview as white + alpha 256-px layers (`LAYERS`: ticks row 1 #3, dots row 1 #5, arcs row 1 #4, heavy
  row 2 #5, each with its scale, speed (degrees a frame) and alpha; `FILL`: the open arc meter, 11 fill frames revealed
  clockwise) and renders a preview (GIF + contact sheet). `tools/gekkouga_gauge_flx.py SRC_DMG OUT` adds the clip
  `gkgauge_mc` (rings `gk_ticks_mc` / `gk_dots_mc` / `gk_arcs_mc` / `gk_heavy_mc`, the track, `gk_fill_mc` 11 frames) to
  panel sprites 1-4 on a new 1024 x 1024 texture (GIDX 0x2800FE30), as `dmg_trait_badge.py` does. The exe (`gk_panel`):
  when `gkgauge_mc` is in his slot's root clip (`gk_find`: the names interned every frame, `0x032CCAA0`), the KO meter
  is hidden, the gauge shown and tinted per mode, each ring turned by its speed from its kept angle (`0x032CDEDC`), the
  fill on frame 1 + value / 10 and stopped; else the KO meter route. Not built into the package: it needs the user's
  current `data/ui/info/dmg` (the trait badge / Hero's menu in it). Tested in unicorn (the driver); the builder is
  untested until those files arrive.

## Clones v8 (`greninja_clones_v8.zip`)

The user's v7 A_safe log: the panel bar shows and the name tag hides, but no clones; `S4GZ` gave the start's scale 2.76
(the v6 / v7 "scale 0" reading was wrong), the clones lived 12 s with their ids and places. `S4GW object=00000000` is
his object id 0 (the tag hides), now logged as `object id=%d`.
- **The cause, in the clone's MSC** (`weapons/clone.c`): `cl_show` kept the visibility it set (1 / 0), and `cl_frame`
  reset it to 1 each time it looked for him again, without a call. A clone that waited a frame for its id
  (`VisibilityModule(0x2710, 0)`) was never shown again. In v5 the right clone took the left's lingering "being made"
  bit, never waited and was drawn (black: bunshin's start); in v6 / v7 the bit comes the frame after the generate, so
  both waited. Now `cl_shown` = the value last set + 1 (0 never set); the test checks wait (hidden), id (shown), then
  no more calls, and fails on the v7 script.
- **Bunshin's start** (`0x02AF6738`, read in full): ColorBlendModule (accessor +0x38) vt +0x4C(&(0, 0, 0, 255), slot 0,
  0); LinkModule (+0x68) set_attribute vt +0x3BC(link 3, 0, 1) and (3, 0xD, 1); EffectModule (+0xA0) vt +0xB4(0x20000,
  0), vt +0xA4(0x1000047, 0x20000). None of these shows the model: a weapon is drawn by its VisibilityModule (+0xA8)
  +8 AND, only with a link attribute 7, the parent's (`0x02C77004` / `0x02C560C8`). The v5 clone's fade was the
  heartbeat removal (the id clash). The specializer vtables of bunshin and the moon differ only at +0x34.
- New TEST_ONLY variant **E_bstart** (feature `bstart`): the start runs bunshin's, then ColorBlendModule vt +0x44(0)
  (slot 0 off, as Terminate_Overlays' handler `0x02BE37B8`). The release and A-D keep v7's empty start.
- Diag `S4GM` / `S4GN` (`w_ddiag`, on the clone's first frame (its 4th poll) and with each `S4GX`): VisibilityModule +8
  and is_visible, ModelModule (+0x3C) +8 mode and its instance's +0x7DB, ColorBlendModule +0x50 (slot 0) / +0xD9; the
  posture z and +0x5C scale, LinkModule +0x84, the ModelModule pointer.
- Package: exe_v46z_gk8 (+ diag A-E) and the clone's `clone.mscsb`. Cave tests 97 (release), 107 (A / B / D / E),
  113 (C); `gekkouga_clones_test` 202 checks with `--v1` to `--v7`.

## Clones v9 (`greninja_clones_v9.zip`)

Confirmed by the user in v8: the clones show (A_safe), their attacks hit (B_attack), C_hurt doesn't crash, the panel bar
shows. Not working in v8: the tongue / water left in the world, hits on a clone (C_hurt: no damage line over ~18 DK
hits), the name tag (the user's correction: it never hid). Release = v8's B set (`RELEASE` = attack); TEST_ONLY
A_attack, C_hurt (attack + hurt), D_parts (attack + parts).
- **Tongue / water** (`tools/gekkouga_build.py` `full_motions`, `rebind`, `empty_sb`): an article never steps its
  swing bones, so with his model.sb they were placed once in the world and stayed (the user's clip: the tongue on the
  floor under the jumping clones, the water streaks stretched back; D_parts' keyed sw1 is overridden by the swing). The
  clone's model.sb lists no swing bones (Cloud's empty form); every main.pac motion gets his part motions' bones
  (lhand / rhand / pt1 / pt2 / sw1; 12 thrown motions without parts take Wait1's), tracks in vbn order; the vertices
  on bones no motion keys (HLP elbow / leg helpers, the LegB / water swing drops) move to their nearest keyed ancestor
  (exact while the bone would sit at its bind offset). `gekkouga_clones_test.model_tests`: merged poses equal his
  main + parts (Wait1, every bone), no vertex on an unposed bone, sb empty; they fail on v8's files.
- **Hurtboxes**: the generic weapon params (`0x032107B4`) give every weapon 1 hurt group (params +0x9C: +0xB4 count,
  +0xB8 groups, +0xAC 0x14); HitModule (vtable `0x10107774`) setup vt +0x14 (`0x02C42570`) starts it empty, reset vt
  +0x34 calls clear-all vt +0x3C (`0x02C42CE4`); the clone's hurtboxes were added only at its construction (spec
  +0x1C, the match load). v9's start (+0x34) clears and re-adds them. Diag `S4GK` (at the start: groups, count before /
  after, group 0's records, collision objects) and `S4GO` (with each `S4GX`: count, objects, the first record).
- **Name tag**: the SET_CURSOR message's first word is `0x100FCC00` (the handler's `lis 0x1010` / `addi -0x3400`; its
  vtable +0x14 `0x02BE9724` returns +4 = type 6); v7 / v8 sent `0x1010CC00` (string data). The send `0x02BF019C`
  calls `[obj+0x24]` vt +0x21C (the receiver; its table is built at run time, not traced). The cave test reads the
  word from the handler. `S4GW` also logs gone (0 = his object found) and the handle.

## Clones v9.1 (`greninja_clones_v9_1.zip`)

The user's v9 A_attack log: frozen while the match loaded (nothing after the boot lines, not even the clones'
set-up `S4GI`), so before the clone objects were built: the data, not v9's exe changes (they run in the match). The two
load-time changes were the empty model.sb (12 bytes) and the merged main.pac (3.8 MB). The swing loader (`0x036B8040`:
magic `SWB ` after the LE swap `0x036B73F4`, version 0x10005 -> `0x036B7C40`, count at +8 -> `[+0x50]`, entries 0x468
from `0x04AD7978`) takes count 0 (the Ultimate ports' fighters use it), but never on an article with SWG_ bones; the hang
is not pinned offline. v9.1 (data only, v9's exe stays): his own main.pac and model.sb back (v8's), and model.nud with
only its vertex bone indices changed: every vertex on a bone main.pac doesn't key (37 bones: parts, swing, helpers) on
its nearest keyed ancestor (`CLONE_POSED = 'main'`): rigid tongue / jaw / fingers on the clones, nothing on an unposed
bone. TEST_ONLY_DATA: `original_model_nud` (if v9.1 still hangs), `merged_main_pac`, `empty_model_sb` (to pin v9's).

## Clones v10 (`greninja_clones_v10.zip`)

The user's v9.1: loads (also with the merged main.pac: v9's freeze was the empty model.sb), tongue / water on the
clones but rigid; C_hurt crashed (IP 0x04BED250); the tag never hid, also with v9's well-formed message (gone=0).
- **Tongue** (`CLONE_POSED = 'merged'`, `unswing_sb`): the merged main.pac (byte for byte v9.1's TEST_ONLY one), his
  own model.nud with only the 8 bones no motion keys rebound (HLP x4, LegB / water swing drops), and his model.sb with
  the 9 SWG_CMant entries' bone hashes inverted: the parser (`0x036B8040`) looks each entry's bone up (`0x036B0318`)
  and skips a miss (`0x036B8474`; its second pass skips entries never set up, byte +4), so the count / size stay (13,
  1832 bytes) and the tongue is an ordinary keyed chain (his sw1 keys), not a swing chain left in the world.
  `gekkouga_clones_test.sb_parse` mirrors the parser. Physics sway on the clones: not done (see below).
- **C_hurt crash**: S4GO read HitModule +0x44 (the records' capacity, 0x14) as the records pointer; it is +0x48. The
  read is range-checked now (0x10000000-0x80000000); the unicorn test runs the game's layout and a bad word.
- **Name tag**: the player-marker HUD (`ui/info/plycursor`, `inf_plycursor_*`; its set-up `0x028E3B90` reads the
  resource table `0x1033B120`): its update calls `0x028E3E18(hud, player)` for each of 8 players (`0x028E4020`), which
  shows the marker only while the player block's byte `+0x2B75` (block = hud + player x 0x2B00) is set, else fades it
  (`+0xC0+0x2AB8` alpha, the 13 parts at `+0xC0+0x40`, 0x340 each, through `0x029003AC`). `plyc` (trampoline
  `0x037EE570`) zeroes that byte before the call while s13's hide counter is up (his tag bit), saving it and putting it
  back once after. Diag `S4GU` once per hide. The message route stays (harmless).
- **Swing (for the sway)**: the swing data is bound by the motion library (`0x0330E030` calls the parser in the
  motion / model bind), and `0x03318A20`-style wrappers act on `[obj+0x20]` (the swing system); the step and what gates
  it for articles are not found yet. Copying his post-swing tongue pose onto the clones would use MotionModule
  set_node_rotate (`0x02C64188`) per bone; his post-swing local rotations' location is not found yet either.

## Clones v11 (`greninja_clones_v11.zip`)

The user's v10: loads, the name tag hides (plyc confirmed; kept), the tongue invisible (the unswung model.sb), clones
not hit (C_hurt log: S4GK 8 boxes / 1 object, S4GO's record = our hurtbox data copied at record +8 by `0x02C44354`).
- **Release data** (`CLONE_RELEASE = 'rigid'`): the merged main.pac, v9.1's model.nud (every vertex on a main.pac
  bone: visible, rigid tongue), his own model.sb. The release exe is v10's byte for byte (not shipped).
- **Sway** (feature `sway`, TEST_ONLY E_sway + TEST_ONLY_DATA/sway = his own nud / sb): a fighter's frame calls its
  MotionModule's swing update `0x02C67064` (from `0x02E3543C`; it needs MotionModule +0x38 / +0x14, reads posture,
  model, motion, stop, +0x60 and slow modules, sets the rate `0x03318A10`, then the motion object's swing
  `0x03314FB8`: set-up `0x036B715C` once (+0xF1), step `0x036B726C`); the weapons' templates call only the motion
  updates (`0x02C5C2BC`, `0x02C5D2B4`, `0x02C5D464`, `0x02C5C4C8`), never it: the v8 stuck tongue. `w_sway` calls it
  once a frame from the +0x94 phase when every module is there. Diag `S4GQ` (every build's draw diag): MotionModule,
  +0x38, motion object, swing system, its +0xB4 flags, +0xF1.
- **C_hurt**: `S4GY` logs the hurtboxes' collision object 0's first words at each start.

## Clones v12 (`greninja_clones_v12.zip`, TEST_ONLY exes only)

The user's v11 E_sway crashed at the first clone's first frame (MotionModule's whole swing update `0x02C67064` on an
article). v12 (the release and data stay v10's / v11's):
- **F_hitcheck** (feature `hitcheck`, `w_hitchk`, the +0x94 phase): every other live fighter's AttackModule entries
  (container am +8: +0xC entries 0x174 each, +0x10 count; an entry: +0 first node, +4 count, +0x18 node pointers; a
  node: +0x3C on, its x / y box +0x18 / +0x1C min, +0x20 / +0x24 max: the same boxes the game's pair pass
  `0x02C0F6F0` tests first) against the clone's box (x +- 6, y to y + 18, `HC_BOX`); same team (TeamModule acc +0x6C,
  +8) and his own slot skipped; a hit sets his VAR_21 = 20000 + its id (his MSC's hurt path: smoke and the log) once
  per clone life (its VAR_4, cleared at each start). Diag `S4GH hit check: attacker slot hitbox clone id x y`. Not
  covered: projectiles / items, the attacker's hitlag. Unicorn: hits, node off, the four sides, team, owner skipped.
- **E_sway**: only the motion object's swing rate `0x03318A10(motion, 1.0)` and swing set-up / step `0x03314FB8`;
  diag `S4GR` before / after its first call (VAR_5). The +0x94 wrapper now runs its calls before restoring the
  arguments (v11's ran after: the moon's +0x94 is a `blr`, so harmless).
- Assists: Ghirahim and Lyn both have the empty 12-byte model.sb; Lyn's Hair1N-5N are keyed in all 6 of her motions
  (her model.nhb is the 64-byte empty form): no swing on either.

## Clones v13 (`greninja_clones_v13.zip`)

The user's v12: F_hitcheck works in game (`S4GH attacker slot=2 ...` removed both clones); E_sway: no crash, the
clones' motion has no swing system (`S4GQ swing=00000000`, so no step ran); a clone dropped as 101 had fallen off the
edge (intended).
- **Release** = attack + hitcheck (`RELEASE`); ladder A_release, D_parts, E_sway (C_hurt's hurtbox route dropped).
- **Hit check v13** (`w_hitchk` / `hc_box`): every live battle object of the categories 0 (fighters, 0x76B0), 1
  (weapons, 0x1E20) and 4 (items, 0x3B88) in the object holder `[0x1035184C]` (+4 x category: {objects, ?, count};
  an object +0x1E live >= 4, +0xC its module accessor, as `0x02BF205C` / `0x02BF2108` read them); his team skipped (a
  fighter's -1 never matches; a weapon / item equal to his always: his shuriken, the clones). The attacker's hitlag:
  `HITSTOP_FN(accessor, AttackModule +0x40 + hitbox x 0x84, its damage +0x18, mul, 1, 1)` on its StopModule (+0x48)
  vt +0x8C(frames, 1). S4GH: attacker category x 16 + index, hitbox, clone, hitlag, place.
- **E_sway bind** (`wsw_bind`, once a life, VAR_6): the motion bind's swing tail (0x0330E000 - 0x0330E03C):
  `0x03327448()` (a swing system), stored at motion +0x20, `0x036C60E0([mo+0x1C], [mo+0x18], swing, 9, 9,
  [[[mo+0x18]]+8])`, `0x036B8040(swing, sb)`, `0x036B736C(swing, nhb)`; sb / nhb from its model instance (+0x6FC /
  +0x700, `0x034205FC` copies them from the creation params' +0x10 / +0x18), else his. S4GR stages 2 (sources), 3
  (bound), 0 / 1 (first step). The bind needs the motion's model link mode != 8.
- **His MSC**: `gk_gone` reports 400 + id when the clone was falling on its own (past the blast zone), else 100 + id.
- Diag: S4GX every 60 frames for the clone's whole life. The cave limit is 0x04BF4000 (was 0x04BEE000).

## Burn v1 (`greninja_burn_v1.zip`, over clones v13; exe_v46z_gkb1)

The user's burn mechanic (mechanics only: the fire visuals wait for the fire flipbooks; the smashes' fire trail is
designed for v2 with them). Feature `burn` (in `RELEASE`), `tools/gekkouga_clone_cave.py` `burn_him` / `w_burn` /
`burn_scan` / `burn_add` / `burn_tick`:
- **Hits**: each new node of a hit log of his (or his clone's) AttackModule while he (it) plays a burning motion
  (MotionModule accessor +0x44, +0x38 the motion kind = his motion.mtable index: attackairn 104, attackairf 105,
  attacks4 95, attackhi4 99, attacklw4 101) adds one instance to the victim. A hit log: [AttackModule entry +0x130]
  (+4 first node, +8 count; a node +4 next, +0x18 the hit object's id, +0x23 the hit container's type: 1 hurtbox, 2
  shield). Processed counts per attacker context (his slot x 3 + 0 / 1 / 2) and entry; outside the moves the counts
  follow the logs (nothing burns).
- **Instances**: 8 victims x `BURN_CAP` (32) x 16 bytes {frames, tick << 16 | interval, owner slot, damage}; each
  Greninja's slot 13 ticks only his own (their own timings), raw percent through the victim's DamageModule vt +0x74(0,
  f1) (MSC DamageModule(9, %)'s op: no hit, so invincibility / intangibility don't matter). A victim not live: its
  instances end.
- **Values** (`BURN_MOVES`; damage a tick, interval, duration; total; burn v2.1: the floor 1 %, see "Burn v2.1"): smashes 0.4 % / 6 f / 240 f = 16 %, forward
  air 0.3 % / 10 f / 180 f = 5.4 %, neutral air 0.25 % / 15 f / 180 f = 3 %. Shielded: half the frames, 20 % of the
  damage, raised so the total is at least `BURN_MIN_TOTAL` 3 % (`burn_shield_damage`: all five clamp to 3 %). The
  module asserts every instance (shielded or not) totals at least 3 %; the cave test checks it and that the clamp
  only applies where the rule falls short.
- Diag `S4BA` (an instance added) and `S4BT` (each victim's damage from him in the last 60 frames, his stacks on it).
- Unicorn (`burn_checks`): a hit, no double count, a shielded hit, independent timers, Wait1 / old hits ignored, a
  restarted log (multi-hit), reflector / weapon / out-of-range records ignored, the cap, another Greninja's timing,
  16 % over 240 frames in 40 ticks, a gone victim, a clone's hit for its owner.
- Not verified in game: that a shielded hit is logged in the attacker's hit log with type 2.

## Burn v1.1 (`greninja_burn_v1_1.zip`, over burn v1; exe_v46z_gkb2)

The user's burn v1 test: burns work and stack, but kept ticking after a KO; shield factor 20 % -> 35 %.
- **KO clear** (`burn_tick`): each frame, for every victim holding a burn (anyone's), its status kind (accessor
  `+0x20` StatusModule, `+0x48`): Dead `0xB1` / Rebirth `0xB2`, or the fighter not live -> its whole list emptied (every
  Greninja's instances) before any tick. Diag `S4BK victim status owner`. A hit on the respawn platform burns nothing.
- **Shield** `BURN_SHIELD_DAMAGE` 0.35 (50 % duration, the 3 % floor kept). Today's rows all still clamp (50 % / 35 %
  gives 2.8 % for the smashes, 0.945 % forward air, 0.525 % neutral air): shielded 0.15 % / 6 f / 120 f, 0.333 % /
  10 f / 90 f, 0.5 % / 15 f / 90 f = 3 % each, as in v1.
- Unicorn (`burn_checks`): status 0 / 0xB0 / 0xB3 keep ticking; 0xB1 / 0xB2 with two owners' burns: empty at once, no
  tick after; diag S4BK once. `gekkouga_clone_cave_test` 143 (release) / 161 (diag) checks, 0 failures;
  `supamario_ui_cave_test` 0 failures; `import_call_check` 0 on both; both exes rebuild byte for byte.

## Burn v1.2 (`greninja_burn_v1_2.zip`, over burn v1.1; exe_v46z_gkb3)

The user: burns carried into the next match after quitting early. `gk_clear` joins the game's clear-all chain (its
last `b 0x02FB349C`, found by `outline_cave.clear_tail`; run at match start / end or quit, rematch / restart, training
reset) and empties the burn lists and processed counts, the tag hide counters, the slow states and the tag message
countdowns (the cursor's saved byte is kept for its restore). Diag `S4BR` once per Greninja slot after each clear.
Unicorn (`clear_checks`): the chain's last b -> gk_clear, back at `0x02FB349C` with r3 / r10 kept, every list empty,
the next match's 12 frames tick nothing. Cave tests 149 (release) / 167 (diag), 0 failures; supamario_ui_cave_test 0;
import_call_check 0; both rebuild byte for byte. Not covered: his MSC's own state (clones, smash store, gauge) on a
training reset (it resets at Entry / KO).

## Skeleton v1 (`greninja_skeleton_v1.zip`, over burn v1.2; exe_v46z_gks1, Sm4shCommand v1.7.27)

The user: side special (Shadow Sneak) no longer teleports him; a Running Skeleton (25 HP) appears at the shadow, runs
slowly in a straight line, is large and solid (a wall, standable), explodes after 3 s with an extremely strong burn,
and at 0 HP goes in a puff of smoke with no hitbox. Later: it doesn't stop at ledges (it falls).

- **His side (clones.c, `gk_ss_tick` in place of `func_2291`, `tools/gekkouga_build.py` `MSC_BODIES`)**: the start-up
  (`0x16000006`) and the shadow's time (`0x16000007`) as vanilla, no vanish (no Visibility / Hit / AreaModule calls), no
  teleport; at the frame vanilla teleports him (21 with the vanilla params) `gk_sk_spawn(0x31, 0x32)` (the shadow's
  place: his instance floats): his VAR_15 = 1, VAR_16 / 17 the place, VAR_18 his facing, `ArticleModule(0x2710, 8)`;
  then Wait / Fall. The request lapses after 5 frames (one skeleton at a time: with one out, nothing is made).
  VAR_14 (written by the exe: the clear-all count & 7) changing resets his ability / burnout / charges (`gk_reset`: a
  training reset; burn v1.2's audit).
- **The article** (weapon kind 0x1A2, article 8, folder `skeleton`; `tools/gekkouga_clone_cave.py` feature `skeleton`,
  in `RELEASE`): a bunshin descriptor copy with 3 motions (the hydrant's motion hash `0xB16D0064`), u16 flags bunshin's
  without the Final Smash categories and the owner's colour (c00 only), base kind Mario's pump (its template updates the
  AttackModule), the clone's module row with slot 5 (the GroundModule) the hydrant's (`0x02BCC7FC`), its own singleton
  (the moon's vtable: +0x34 `sk_start`, +0x94 `sk_94`, +0xAC `sk_hit`: its explosion connecting doesn't remove it).
  Files (`gekkouga_build.py skeleton PACMAN_FIGHTER OUT_FIGHTER`): model/skeleton/c00 = Pac-Man's hydrant's model (a
  carrier) + `skeleton.lvd`; motion/skeleton/main.pac = the hydrant's; scripts `SkeletonRun` / `SkeletonExplode` /
  `SkeletonSmoke` (motion kinds 0 / 1 / 2); `weapons/skeleton.c` its MSC.
- **The exe's part (`sk_frame`, +0x94 every frame)**: the claim (its VAR_0 0: the first live Greninja whose VAR_15 is on;
  his 16-18 copied to its VAR_1-3, its VAR_0 = his slot, his VAR_15 cleared); running (its VAR_5 1): the collision made
  once (below), moved with it every frame, the hit check (below); exploded / smoked (VAR_5 2 / 3): the collision removed;
  its scale 2.0 while running (the stand-in body), 1.0 after; its explosion's hits scanned by `burn_scan` with the
  skeleton row (context slot x 4 + 3; burn v1's contexts became x 4).
- **Collision (the hydrant's route)**: Pac-Man's hydrant (weapon 0x12D) and Fox / Falco's Landmaster have a GroundModule
  class (`0x02AC2948` init; vtable `0x100D3178`, the hydrant's subclass `0x100ED868`) that makes stage grounds from an
  .lvd in the article's files: its specializer +0x3C (`0x02B34508`) does `0x030C40A8([0x102F9028] +0x30, &bundle, kind,
  0, 0)`, `0x032D7140(&bundle, &file, "firehydrant.lvd", 1)`, `0x032D69B8(gm +0xEC, &file)`, `0x02AC2B84(gm, 1, 0, 0)`
  (the grounds, +0xF0 / +0xF4, via `0x02D49F2C`), `0x02AC2EF0(gm, 0)` (on), `0x032D4200(&handle, 2)` x 2; its update
  puts each vertex on a joint (`0x02B38950`: `0x02AC30C0` place / `0x02AC312C` move, then `0x02AC3204` the lines). The
  skeleton does the same with its own kind and `skeleton.lvd` (4 vertices: x +- 6, y + 2 / + 28: a wall each side, a
  floor on top) and moves the vertices itself from its posture (move: riders carried); `0x02AC29D8` removes them (the
  GroundModule's own end calls it too). The user's Gogoat lead: no .lvd and none of these functions for it (the ground
  makers `0x02D49F2C` are stage / mode code, e.g. the Home-Run barrier `0x02A8E9C0`); in Smash 4 Gogoat carries its
  summoner (a ride), not a standable top.
- **HP (`sk_hits`)**: the clone hit check's objects (fighters, weapons, items; his team skipped, his body, itself), per
  attacker the entries on (`sk_box` r4) and over its box (x +- 6, y to y + 28; r3); a hit when an entry over it isn't
  latched: the lowest one's damage added to its VAR_4, VAR_9 + 1, VAR_7 / 8 the place (the attacker's X / Y + 8 kept in
  its box), the attacker's hitlag; then every entry on is latched until it goes off (once per attack). 16 attackers per
  skeleton.
- **Its MSC (`sk_frame`)**: waits for the claim (30 frames, then removed); starts at VAR_1 / 2 (snapped to a floor),
  facing VAR_3; runs 0.7 a frame (a wall at foot + 5 within its step + 2 stops it), standing it follows the floor (3 up /
  down), off a ledge it falls (0.18 / 1.85, his) and lands; frozen in hitlag; a new hit (VAR_9) the spark at VAR_7 / 8;
  VAR_4 >= 25 the smoke (phase 3, removed 3 frames later); 180 frames the explosion effect (phase 2), its explode motion
  the next frame (its scale back to 1), removed 40 frames later. Past the blast zone the game removes it.
- **Values**: speed 0.7, HP 25, fuse 180, gravity 0.18 / max fall 1.85, box 12 x 28; explosion (`SK_BOOM`) 15 %, 50
  degrees, KBG 50, BKB 40, size 22 at bone 0 Y 14, flame, FacingRestrict 5 (from its middle), 4 frames (Smash 4's
  formula: 135 knockback on Mario at 130 %); burn row `0x101A2` 0.6 % / 6 f / 360 f = 36 % (the strongest), shielded
  0.21 % x 30 = 6.3 %.
- **Visuals (placeholder)**: the flipbooks (`$S/greninja_fire_effects_v1.zip`) belong in his effect bank
  (effect/fighter/gekkouga/ef_gekkouga.eff), which isn't in the workspace; v1 shows the carrier (the hydrant) x 2 as its
  body (`sk_show_model()`), the common spark 0x1000025, bomb explosion 0x1000017, item smoke 0x1000021 (`sk_fx_*`).
- Diag: S4SS spawned, S4SC collision (1 made / 3 failed), S4SH hit, S4SX phase, S4SF collision removed; S4BA its burns
  (move 65954).
- Tests: `gekkouga_clone_cave_test.py` 183 / 205 (release / diag; `skeleton_checks`: the tables / row / descriptor /
  singleton / list, the claim, the collision calls (made, moved, gone, a missing .lvd, a wrong GroundModule), hits once
  per attack, the lowest of two, his team / himself skipped, the explosion's removal and burns, the strongest row, the
  scale); `gekkouga_clones_test.py ... --v1 ... --v13 --vb1 --vb11 --vb12` 230 / 0 (`skeleton_side_tests`,
  `skeleton_tests`, `skeleton_data_tests`, the package); msc_stack_check 0 (skeleton.mscsb 35 globals);
  import_call_check 0; supamario_ui_cave_test 0; both exes rebuild byte for byte; Sm4shCommand v1.7.27 290 / 1 (the
  known effect.bin else-if count) and 248 / 0.
- Not confirmed in game: the collision on a new article, riders and pushed fighters, FFA projectiles' team check, the
  knockback, the carrier's look.

## Clones v14 (`greninja_clones_v14.zip`, over skeleton v1; exe_v46z_gk14) and Skeleton v1.1

The user: fix the clones' tongue and water (swing bones the game steps only for fighters). Two routes, plus the user's
skeleton v1 report ("no collision": its log shows `S4SC state=1` every spawn).
- **Pose copy (feature `pose`, now in `RELEASE`)**: `w_pose` in each of the clone's four frame phases (+0x64 / +0x84 /
  +0x8C / +0x94, the vtable's pollers): for each of his 13 swing bones (`POSE_BONES`: SWG_CMant0-8 60-68 on anchor 39,
  SWG_LLegB_01 / Lwater01 / RLegB_01 / Rwater01 69-72 on 3 / 15 / 7 / 19), the clone's world matrix = C_a x inverse(H_a)
  x H_b (`m34_inv` uniform-scale rigid inverse, `m34_mul` 3x4 [R | t] rows). His matrices: his MotionModule +0x14's
  object (the one a fighter's swing update steps) when it has the layout (`mo_ok`), else +0x10; the clone's: its +0x10
  (+0xC the world matrices, 0x30 each, as get_world_matrix `0x02C64588` -> `0x033179C8`; at least `POSE_MIN` 73 bones,
  `0x0330DE2C`). Harmless on the installed rigid-tongue data; seen with TEST_ONLY_DATA/sway (his own nud / sb). Diag
  `S4TP` (bone 64 on him / the clone x100, the phases that found the clone's own pose since our write).
- **E_sway (TEST_ONLY)**: v13's bind crashed in game at its first clone frame (log_v13_E_crash: IP 0x04BED1F4 reading
  [[mm+0x14]+4]+4 with [mm+0x14]+4 = 6): a weapon's MotionModule +0x14 is not the model / motion object. v14 binds /
  steps [mm+0x10] after `mo_ok` (+4 a pointer whose +4 is the mode, not 8; +0x1C a pointer) and checks [+0x18] / its
  first word before the bind; S4GQ logs +0x14 and +0x10. E_sway is `RELEASE - pose + sway`.
- **Skeleton v1.1**: its ground gone (handle +0x160 -1, or none) while it runs -> made again (`SK_REMAKE` 3 a life, then
  VAR_6 4: lost; diag `S4SG`); a 2-vertex ground (TEST_ONLY_DATA/skeleton_floor_only: the hydrant's .lvd with only its
  line moved to x +- 6, y + 28) has its top line moved; diag `S4SC` adds the bundle / lvd handles, its GroundModule and
  its bytes +0xF8-+0xFB, `S4SD` / `S4SE` every 30 frames (the ground, its line count, the first two vertices, the
  handle's id / flags; the ground manager's +0x19C, the GroundModule's +0x18 object's +0x248 / +0x234, the ground's
  +0x68 / +0x7C / +0x82). Why fighters ignore the made grounds is not found yet.
- TEST_ONLY_DATA: sway (his model.nud / model.sb, c00-c07), rigid (the release's model.nud back), skeleton_floor_only.
- Tests: cave 192 / 216 / 221 (release / A_release / E_sway; `pose_checks`: the 13 bones against numpy, the rest
  untouched, the tongue relative to its anchor, his +0x14 preferred, the clone's odd +0x14 ignored, no owner / short
  skeleton; `sway_checks`: the v13 crash layout, bad +4 / +0x1C; skeleton v1.1's remake / lost / floor-only);
  `gekkouga_clones_test ... --vs1` 237 / 0; supamario_ui_cave_test 0; import_call_check 0; byte-for-byte rebuilds.

## Clones v15 (`greninja_clones_v15.zip`, over v14; exe_v46z_gk15)

**Confirmed in game: native swing (v14 E_sway)** (the user: "E_sway works and the clones have their own swing physics";
log_v14_E_sway_ok: S4GR stages 0 -> 1, no bind needed: the clone's MotionModule +0x10 object already has a swing system,
v13 read +0x14). So:
- `RELEASE` = attack, hitcheck, burn, skeleton, sway (v14's E_sway set; the release exe is its non-diag build, the
  TEST_ONLY A_release its diag build plus v1.2's hydrant comparison lines). The pose copy is TEST_ONLY G_pose (v14's
  A_release exe byte for byte).
- Data (`gekkouga_build.py` `CLONE_RELEASE = 'own'`): the clones' c00-c07 model.nud = his own (v14's TEST_ONLY_DATA/sway;
  model.sb his own already); `TEST_ONLY_DATA/rigid` keeps the stiff-tongue nud (v9.1's) as the fallback. `cmd_data`
  rebuilt from the vanilla files gives exactly these (only the 8 nud files differ from v14's release).
- Skeleton v1.2 diag (the user: no collision, the floor-only lvd too; its ground is made, active (+0x68 0), at its top and
  moving with it): `col_dump` logs the same words of its grounds (tag 1, from `sk_coldiag`) and of Pac-Man's own hydrant
  (tag 2: the hydrant's specializer +0x94 is a lone `blr` at `0x02B38314`, only its vtable `0x100ED3F8` uses it; the diag
  build branches it through `HYD_TRAMP` 0x037EE530 to `hyd_diag`, every 60 calls): S4CD the handle (+0x40-+0x4C callbacks,
  +0xA4 / +0xA8), S4CE / S4CF the ground (+0x60-+0x88), S4CG the GroundModule +0xF8 and its +0x18 object (+0x230 / +0x240 /
  +0x248), S4CH the handle's +0x160-+0x16C and the ground's +0x30 / +0x34. S4SE's arguments fixed (v1.1 passed 9: its last
  was garbage). Found on the way: module row slot 17 is accessor +0x8C (the full slot -> accessor map: 0 +0x34, 1 +0x4C, 2
  +0x50, 3 +0x24, 4 +0xA0, 5 +0x2C, 6 +0x58, 7 +0x44, 8 +0x1C, 9 +0x7C, 10 +0x70, 11 +0xA4, 12 +0xA8, 13 +0x38, 14 +0xB4,
  15 +0x64, 16 +0x60, 17 +0x8C, 18 +0x30, 19 +0x40, 20 +0x54, 21 +0x90, 22 +0xAC, 23 +0xB0, 24 +0x84, 25 +0xB8, 26
  +0xC4, 27 +0x78); the hydrant's +0x3C sets it up first (vt +0x3C(5), +0x74 / +0xC4 its vl floats +0x4C0 / +0x4C4, +0x54(1))
  and the skeleton has no slot 17 module: a lead if the comparison shows nothing.
- Tests: cave 197 / 224 / 219 (release / A_release / G_pose); `gekkouga_clones_test ... --v14` 236 / 0;
  supamario_ui_cave_test 0; import_call_check 0; byte-for-byte rebuilds.

## Skeleton v1.2 (`greninja_skeleton_v1_2.zip`, over clones v15; exe_v46z_gks2)

**The collision** (the user's log_v15_hydrant, A_release's S4CD - S4CH lines: Pac-Man's hydrant's ground +0x68 / +0x6C
-1, +0x72 1, handle +0x163 1, GroundModule +0xFB 1; the skeleton's all 0). `0x02AC2EF0(gm, 0)`, which v1 - v1.1 called
after making the grounds as the hydrant's set-up does, turns them OFF: the hydrant makes its ground off and its status
hook turns it on when it lands (`(gm, 1)`, `0x02B3746C`), which then happens in the per-frame `0x02AC2E54` (+0x163 1,
masks -1, `0x02D5D6E0`). v1.2 (`tools/gekkouga_clone_cave.py` `sk_col_make` / `sk_col_place`): `GC_ON (gm, 1)` and
`GC_ENABLE` (`0x02AC2E54`) right after making them, `GC_ENABLE` again after each move (a no-op once on). The hydrant's
handle callbacks only set its own WorkModule flag 0x10000010 on contact: not used (docs/native-notes.md "Article grounds
are made OFF"). The diag build keeps the comparison lines. `SK_SCALE` 2.0 -> 1.0 (the carrier no longer shows).

**The look** (`tools/gekkouga_fx.py`, `gekkouga_build.py effects`: his vanilla bank + the user's flipbooks
`greninja_fire_effects_v1` = $S/fire_out/pkg, made by `tools/fx_video_to_flipbook.py`): four sets appended to
gekkouga.010d0000.ptcl / .efc (entries 0x16 - 0x19, flags 0x100; his 20 sets / 22 entries unchanged):

| Id | Set | Flipbook | Size / place | Blend |
|---|---|---|---|---|
| 0x3300016 / 0x3300017 | PtcGekkougaSkeletonR / L | skeleton_run, 55 cells 6 x 10 on 2048², 30 fps, loop (L: each cell mirrored) | 60.9 x 36.6: the body (alpha >= 0.5 rows 0.141 - 0.907 of a cell) 28 tall, its feet (sidecar anchor 0.933 of the frame = 0.9125 of the cell) on the call's point | normal |
| 0x3300018 | PtcGekkougaSkeletonHit | impact_sparks, 24 cells, 30 fps, one-shot | 18 x 18, centred | normal |
| 0x3300019 | PtcGekkougaSkeletonBoom | explosion_simple_24, 40 cells, 15 fps, one-shot (2.7 s) | 52.4 x 61.1: 44 wide at its widest (u 0.08 - 0.93 = the hitbox's 22 x 2), its base (v 0.895) on the call's point | normal |

- Every emitter is a copy of Kirby's `PtcKirbyStoneEnd/stone` (its shader imported once): the only kind among the 7128
  vanilla emitters that is a CPU particle (follow type 0 keeps it on a following call's live matrix), a camera billboard,
  a flipbook program, colour combiner 1 (alpha from the texture's alpha), one BC3 RGBA texture, unlit, normal blend.
  One particle per call, still, white, alpha 1; the texture the atlas as BC3 (one mip, clamped).
- **32 cells at most per emitter** (docs/ptcl-format.md 0x4E0, docs/native-notes.md "eft flipbooks hold 32 cells"):
  longer flipbooks are runs of up to 31 cells on emitters born in turn (`flip_plan`): the skeleton 28 + 27 cells
  (start 0 / 56, born again every 110 frames, life 57 / 55), the explosion 20 + 20 (start 0 / 80, life 81 / 80); a run is
  held on its last cell one extra frame (its table's last entry twice, mode 4 wraps) so the hand-over frame shows both
  adjacent cells. Loops: fade 1.0 (ended: gone at once); one-shots fade 0 (a fade doesn't cut them).
- **Its MSC** (`weapons/skeleton.c`): the carrier hidden (`sk_show_model` 0); at the start `EffectModule(0x26, 0)` and
  `(0x1C, 1)` (a hidden model hides its following effects: docs/native-notes.md "Effects follow the model's visibility")
  then `EffectModule(0x2717, R or L by its way, joint 0, ..., 1.0)`; explosion / smoke end both (`0x2723`); the hit spark
  at the hit (op 3), the explosion at its feet (op 3, size 1), the smoke still the common puff.
- Tests: `tools/gekkouga_fx_test.py` 19 / 0 (vanilla sets / entries unchanged, the ids in skeleton.c, each emitter's
  fields, every frame of two loops / each one-shot's life drawn by Kirby's program in `tools/latte_exec.py` on the CB2 the
  game's code fills: the right cell, hand-overs, nothing after a one-shot; the feet at the call's point and 28 tall, the
  explosion's 44, the mirror); `gekkouga_clone_cave_test` 201 / 228 / 223 (release / A_release / G_pose; `col_on_checks`:
  the game's GC_ON / GC_ENABLE / 0x02D5D6E0 leave the hydrant's words); `gekkouga_clones_test ... --v15` 236 / 0;
  supamario_ui_cave_test 0 (release); import_call_check 0; byte-for-byte rebuilds. Not confirmed in game: everything here.

## Burn v2 (`greninja_burn_v2.zip`, over skeleton v1.2; exe_v46z_gkb4, Sm4shCommand v1.7.28)

Feature `burn2` (in `RELEASE`; skeleton v1.2's exe is `RELEASE - burn2`), `tools/gekkouga_clone_cave.py` `burn2_src`.

- **Fire on burning fighters** (`bfx_vic`, from `burn_tick`'s `bt_next`: every Greninja's pass, each victim): the level
  (the victim's burn instances, anyone's, at most `BFX_LEVELS` 5) against the one shown (`bfx_lvl`, shared: the second
  Greninja in a frame finds it shown); a change calls the victim's EffectModule MSC handler (accessor +0xA0, vt +0x2EC:
  the call ACMD's Terminate makes, `{args, count}`): `0x2723 (BFX_ID, 1, 1)` (another level) / `(0, 0)` (none: a fade),
  then `0x2717 (BFX_ID, joint 0, 0 x 6, size, 0)` (following, position only), size 1 + 0.15 x (level - 1) (1.0 - 1.6).
  `BFX_ID` 0x330001A (PtcGekkougaFireBody). gk_clear empties the levels. Diag `S4BF victim level old -> new`.
- **Fire at his water's ends** (`gekkouga_build.add_fire_tips`, after `scale_smash`; the clone's scripts copy them):
  External_Graphic 0x330001B (PtcGekkougaFireTip) on each water sword's hand joint at Y = -11 x the sword's size (its
  Sword_Glow's second point: -55 in the smashes, -11 in forward air), size 2.0 (smashes) / 0.7 (forward air), put just
  before the sword's command (inside its IS_FLAG block: the True offsets grow, `insert_cmds`), ended just before its
  Terminate; neutral air: two at joint 0 (Y 8.5, Z +- 10), size 1, FRAME 24 + Terminate. Up smash's water is its two
  swords (0x3300011, EffGekkougaAttackHi, is up tilt's model). `strip_fire_tips` undoes it (tests).
- **Fire trails**: his MSC (`clones.c` `gk_trail_tick`, from `gk_chain_try` each frame of the attack statuses, on the
  ground) at the smash's main hit (forward 13, up 18, down 16) writes request k = his VAR_4k (type 1 / 2 / 3), +1 / +2 the
  place, +3 his facing: his and each clone's not falling on its own (`gk_cx` / `gk_cy`), `ArticleModule(0x2710, 9)` each;
  the requests lapse after 5 frames (`gk_tr_clear`). The article: weapon kind `TR_KIND` 0x1A3 "firetrail" (article 9,
  `TR_MAX` 6 at once; registered as the skeleton: bunshin descriptor copy with 3 motions of the hydrant's hash, pump's
  template, the clone's row, the moon's vtable with the skeleton's +0x34 / +0xAC and +0x94 `tr_94`). `tr_frame`: the claim
  (`tr_claim`: the first live Greninja with a request -> its VAR_0 his slot, VAR_1-4 the request, VAR_5 a free context of
  his: `tr_ttl` 0, kept `TR_TTL` 3 frames by each of its frames, counted down by his `burn_him`; its processed counts
  cleared; none free: 0, no burns), then `burn_scan` with the trail row and context `TR_CTX0` (32) + slot x 6 + n. Its
  MSC (`weapons/firetrail.c`): placed, facing his way, motion type - 1 held at rate 0 (its game script's hitboxes at
  frame 0), its effects unhooked from its hidden model (0x26 / 0x1C), a flame (0x330001C, PtcGekkougaFireTrail) a frame:
  forward 5 at x 10 - 42, up a column of 4 at y 0 - 42, down 4 each side at 10 - 37; at 165 the fire fades (0x2723 (0,
  0), its set's 1/15), at 180 ended and removed. Its hitboxes (`gekkouga_build.TR_BOXES`, Special_Hitbox on bone 0):
  forward Z 14 / 26 / 38 (size 7, Y 5), up Y 8 / 22 / 36 / 50 (size 9), down Z +- 14 / +- 30 (size 8, Y 5); 0.1 %,
  angle 361, KBG / FKB / BKB 0, Hitlag 0, DisableHitlag, NoGFX, Flinchless, re-hit 35, ground and air, shieldable.
  Burn row `TR_ROW` (0x101A3) 0.25 % / 15 f / 180 f = 3 %; shielded 0.5 % x 6 = 3 % (raised to the floor).
- **His bank** (`tools/gekkouga_fx.py`, entries 0x1A - 0x1C after skeleton v1.2's): PtcGekkougaFireBody (fire_small_4,
  30 tall: ~16 of flame, ~21 wide, its base at the call, fade 15), PtcGekkougaFireTip (fire_torch_012, 15 tall, centred,
  ~7 of flame at size 1), PtcGekkougaFireTrail (fire_ground_10, 22 tall: ~14.5 of flame, base at the call, fade 15); all
  additive, 2 emitters each (39 - 46 cells). His .ptcl 15.2 MB.
- Sm4shCommand v1.7.28: `FireTrailS4` / `FireTrailHi4` / `FireTrailLw4` in ModAnimNames.txt (-> the carrier's
  animation). `new_var_test` 290 / 1 (the known effect.bin else-if count), `hitbox_var_test` 248 / 0.
- Tests: `gekkouga_clone_cave_test` 228 / 257 / 252 (release / A_release / G_pose; `burn2_checks`: the row, the fire's
  calls level by level, shared between Greninjas, a victim gone; the trail's tables, claims, contexts kept / freed /
  run out, its hits' burns plain and shielded); `gekkouga_fx_test` 29 / 0; `gekkouga_clones_test ... --vs12` 262 / 0
  (`trail_side_tests`, `firetrail_tests`, `trail_data_tests`, the tips, the package); supamario_ui_cave_test 0;
  import_call_check 0; byte-for-byte rebuilds. Not confirmed in game: everything here.

## Burn v2.1 (`greninja_burn_v2_1.zip`, over burn v2; exe_v46z_gkb5)

The user: "Change the minimum burn damage to 1%". Feature `floor1` (in `RELEASE`; burn v2's exe_v46z_gkb4 is `RELEASE -
floor1`, skeleton v1.2's `RELEASE - burn2 - floor1`): `burn_floor(feats)` 1 % (`BURN_MIN_TOTAL`; 3 % `BURN_MIN_TOTAL_OLD`
without it), the shielded damage a tick in the moves table (`burn_shield_damage(row, floor)`). Unshielded rows unchanged.

| Row | Unshielded | Shielded (35 % a tick, half the frames) v2 -> v2.1 |
|---|---|---|
| smashes (95 / 99 / 101) | 0.4 % / 6 f / 240 f = 16 % | 3 % (0.15 x 20) -> 2.8 % (0.14 x 20, unclamped) |
| forward air (105) | 0.3 % / 10 f / 180 f = 5.4 % | 3 % -> 1 % (0.945 % raised: 0.111 x 9) |
| neutral air (104) | 0.25 % / 15 f / 180 f = 3 % | 3 % -> 1 % (0.525 % raised: 0.167 x 6) |
| skeleton explosion (0x101A2) | 0.6 % / 6 f / 360 f = 36 % | 6.3 % (0.21 x 30) |
| fire trail (0x101A3) | 0.25 % / 15 f / 180 f = 3 % | 3 % -> 1 % (0.525 % raised: 0.167 x 6) |

Neutral air's and the trail's unshielded 3 % could now go lower (the user's call). Tests: cave 229 / 258 / 253 (the floor
per feature set; every row >= 1 %, the clamp only where 35 % / 50 % falls under it, the shielded totals above);
`gekkouga_clones_test ... --vb2` 262 / 0; supamario_ui_cave_test 0; import_call_check 0; gks2 / gkb4 / gkb5 rebuild byte
for byte.

## Burn v2.2 (`greninja_burn_v2_2.zip`, over burn v2.1; data only, exe_v46z_gkb5)

The user, after the neutral air preview (`tools/gekkouga_nair_preview.py`: his model posed in AttackAirN, fx_render's
effects): "Can you wrap neutral air's water edges in fire?". Burn v2's two side flames (0x330001B at Z +- 10) are
replaced by **PtcGekkougaFireRing** (0x330001D, efc entry 0x1D, `gekkouga_fx.FIRE_RING`), made with the water burst on
its call (`gekkouga_build.FIRE_RING`: External_Graphic at joint 0, Y 8.5, size 1.45, right after the burst's; played out,
no Terminate; the clone's copy too):
- 3 emitters x 5 flames (fire_small_4's first 31 cells, additive, 6.5 tall quads at size 1), each emission on an even
  circle (volume 2, XZ turned Z +90 into the YZ plane: the burst's billboards face the camera, side-on), radius 5, the
  groups' circles a 15th of a turn apart (15 evenly round), flying out at 0.9 a frame with air resistance 0.8 (~9 by frame
  10: x 1.45 = 13, the burst's bright edge in fx_render's render; its faint mist reaches ~21), alpha 0.6 -> 1 by 12 %, held
  to 45 %, out by the end of their 14 frames, scale 0.6 -> 1 by 30 %, fade rate 0 (played out).
- Out of step: each group's table starts 10 cells further on. eft's random start (0x4D9) is no help: its code
  (`0x04A54A88`) picks one random cell per emitter and shifts the emitter's UV by it (all its particles alike; outside our
  table's cells it would leave the atlas), so the flipbook tables do it.
- A first try (radius 6, 1.6 a frame, 9 tall) wrapped far outside the burst in the preview; tuned against it.
- Tests: `gekkouga_fx_test` 32 / 0 (`ring_checks`: the 3 emitters' fields, 15 flames evenly round in the YZ plane at one
  radius, 5 -> ~9 by frame 10, gone after 14, the groups' cells 10 apart advancing every 2 frames); `gekkouga_clones_test
  ... --vb21` 260 / 0 (the ring on the burst's call, v2's side flames gone, the scripts otherwise unchanged; the installed
  gkb5 rebuilt from the script). Preview `$S/gk_preview/nair_v2.png` / `.gif`. Not confirmed in game.

## Burn v2.3 (`greninja_burn_v2_3.zip`, over burn v2.2; data only, exe_v46z_gkb5)

The user: "Can you make the ring use varying fire effects, rotations and fire direction based on Greninja's position in
the circle". The ring (`tools/gekkouga_fx.py` `ring_flames` / `ring_fields` / `ring_emitters`) is now one emitter a flame
(15 a set, the most a vanilla set has is 16), each:
- its own footage, in turn round the ring (`RING_ASSETS`: fire_small_4 6.5, fire_torch_012 9, fire_small_5 6,
  fire_ground_10 8, fire_torch_026 7 tall quads at size 1; each its first 31 cells from its own random start cell);
- one particle at radius 5 at its angle phi round the call's YZ plane (24 degrees apart, +- 4), flying out along it
  (emit direction (0, sin phi, cos phi), directional speed 0.9, air 0.8: ~9 by frame 10, x 1.45 = 13);
- turned (rotation Z: a billboard's turn on screen, counter-clockwise: checked with a rotated skeleton in fx_render) by
  phi - its footage's own tip direction (`ring_tip_angle`: base -> tip of the bottom / top 35 % of each cell's alpha,
  median over its first 31 cells: small_4 123, torch_012 95, small_5 51, ground_10 99, torch_026 143 degrees) +- 12
  degrees, sized x 0.85 - 1.15 (fixed by a seed);
- facing left the game mirrors the call's places but not a billboard's turn: **PtcGekkougaFireRingL** (0x330001E, entry
  0x1E) has the turns for the places as seen (180 - phi); neutral air plays the pair with EFFECT_FOLLOW_FLIP (right /
  left, FlipType 1 as up tilt's) on the burst's call.
His bank: two more clips (fire_small_5, fire_torch_026: +2 MB, 17.4 MB). Tests: `gekkouga_fx_test` 37 / 0 (`ring_checks`
for both sets: each flame's fields, neighbours differ, every tip out from the centre as seen within the jitter, the ring's
growth in fx_render); `gekkouga_clones_test ... --vb22` 260 / 0. Preview `$S/gk_preview/nair_v3.png` / `.gif` (facing
right). Not confirmed in game.

## Aerial chain v1 (`greninja_aerialchain_v1.zip`, over burn v2.3; data only, exe_v46z_gkb5)

Three requests in one package, all MSC (his `gekkouga.mscsb` and the clone's `clone.mscsb`); the exe stays gkb5.

### Aerial chain

The user: "Can you make Greninja's aerials chain like his smash attacks do, but only if it hits an opponent".
`clones.c` `gk_ac_*`, hooked into the aerial status (AttackAir `0x34`) by `tools/gekkouga_build.py` `MSC_EDITS`:
- `func_2382` (its start), after `func_314` picked the motion into `0x11000002`: `gk_ac_start` notes the aerial (kind
  1 neutral - 5 down = motion `0x68` - `0x6C` - `0x67`), starts a new chain unless this start is a chain's (`gk_ac_req`),
  adds it to the chain's used set, and clears its attack's "hit since it started" (`AttackModule(0x2724)`).
- `func_2383` (its loop), after `func_56`'s own interrupts: `gk_ac_try`. A hit is the attack's hit since it started on a
  hurtbox (`AttackModule(0x2727, 2)`; native-notes: `+0xC8`; kind 4, a shield, is not counted) or a clone's copy of
  the aerial landing (the exe's VAR_22, read by `gk_clone_hitlag` -> `gk_ac_clone_hit`; the exe sets it for a clone's
  shielded hit too: it can't tell). The window opens the frame after the hit (not while he is in hitlag) and stays open
  to the move's end. In it, in the air, with the attack command (`global24 & 1`, as vanilla `func_63`'s aerial entry)
  the game's air attack kind (`ControlModule(0x10)`: stick + attack or the C-stick; anything but 1 - 5 is neutral, as
  `func_311`) not used yet in this chain re-enters `0x34` (`func_16(0x34, 1)`: the same status again, as the jab's
  re-entry; `func_311` picks that aerial's motion, facing as vanilla, so a back air is still a back air).
- Each aerial once a chain; `gekkouga_frame` ends the chain on any status but `0x34` (landing, a special, an air dodge,
  a jump, being hit, a ledge grab); after all five nothing more is accepted. Landing lag, fast fall and drift are the
  game's (nothing touched). Smash chains (`gk_chain_try`) are separate and unchanged.
- Diag (no exe change): his VAR_20 flags from bit 256 (the TEST_ONLY exe's `S4GF` line logs every change): 256 x the
  aerial (1 - 5), 2048 hit seen, 4096 window open, 8192 x the chain's used bits (2 neutral, 4 forward, 8 back, 16 up,
  32 down).

### Smash charge effects

The user: "Also make Smash attacks charging not use giant effects for the dust or sparkle". `gk_sm_fx` (the hold's
effects every 5 frames): the dust (`0x1000019` PtcCommonRunSmoke) and sparkle (`0x1000010` PtcCommonSmashFlashS) at
`gk_sm_dust_size()` = 1, their vanilla hold scripts' size, at every charge level. Left as it was (and asked about): his
water sword (`0x3300007`), remade every 10 frames of the hold at the charge's size (1 at 0 to 5 at full: it grows as
the hitbox does); the release's effects (ACMD `EFFECT_GROW`) stay x5 at full.

### Clone delay

The user: "Can you give each clone a frame delay? The left clone should have a 1 frame delay and the right clone should
have a 2 frame delay". Each clone replays his state `gk_delay(id)` / `cl_delay()` of his frames late (the left-spawned
clone 1, the right-spawned one 2):
- His side (`gk_physics` -> `gk_delayed`): the copied inputs of its physics, his X and (while it copies it) his vertical
  movement and the "copying" decision, from a history of his last 3 frames (`gk_hx1` / `gk_hx2`, `gk_last_oy` /
  `gk_hy2` / `gk_hy3`, `gk_hcopy`); its own physics (walls, floors, ceilings, its own fall, the detach on a launch) run
  on the frame.
- The clone's side (`cl_frame`, `cl_push` / `cl_pick`): his channel's motion kind and frame (VAR_28), rate (VAR_29) and
  facing, its own 3-entry history; its hitboxes and effects follow its motion frame, so they come out 1 / 2 frames late.
- First frames: no history yet: his state now, held while it fills (a clone made: its count from 0, `gk_set_hn`).
- His hitlag: no history kept on his frozen frames (his side: `gk_physics` returns; the clone's: the channel's new
  flag 64, its rate 0 where it is), so they freeze and go on in step.
- A swap (and a return to formation after a launch) starts his side's history over (his old places, with the swap's
  new offsets, would put the clones off by the swap's move): they go on from his place now, held for their delay; the
  clone's motion history is kept (the swap changes no motion).
- Not delayed: the native swing (each clone's own, release `sway`); `G_pose`'s TEST_ONLY bone copy is his current pose.

Tests (`gekkouga_clones_test`): `aerial_chain_tests` (hit opens the window the frame after, whiff / shield / hitlag /
ground / no input don't, repeats refused, all five, landing and a jump end it, a clone's hit counts, the diag bits, the
charge's dust / sparkle 1 and sword sizes at 0 - 120 for all three smashes), `delay_tests` (his side: walk, jump,
hitlag, swap, back in formation) and `clone_delay_tests` (the clone: 1 / 2 frames late, first frames, facing, frozen,
history dropped when not alive); the physics / playback tests written before the delay run with it stubbed to 0.
Not confirmed in game.

## Skeleton v1.3 (`greninja_skeleton_v1_3.zip`, over aerial chain v1; exe_v46z_gkb6)

The user's skeleton v1.2 clip (`$S/gk_in/sk12clip/a.mp4`): the look works; it runs through DK (no collision); it is
gone ~0.8 s after ~1 s and comes back. Then: "different fire effects on the opponent to denote more/stronger fire
stacks", "have the fire effects be visible the entire time", "forward air ... more fire along the edges of the water
blade and ... larger", and "Greninja's roll doesn't move him anywhere ... 2.5 roll speed with a 1.24 roll speed
multiplier" ("if the roll script is already in place, uncap his roll speed").

- **The blink (every looping fire)**: `tools/gekkouga_fx.py flip_emitters` put a run's birth in emitter +0x448, which is
  eft's emission count random (percent), not a start frame (docs/native-notes.md "eft emitter timing"): every run was
  born at frame 0 (the second drawn over the first), nothing from the first run's end (57) to the next period (110), the
  re-births thinned. Now +0x44C (emit start) holds it, +0x448 0, a one-shot's end frame = its start + 1 (the same clock).
  The skeleton (R / L), the burning fighter's fire, the water-tip flames, the trails and the new sets.
  `tools/gekkouga_fx_test.py timing_checks`: eft's timing (`eft_timing`, read from the update / emission code) over 600
  frames draws every looping set on every frame; the v1.2 placement in the same model gives the clip's gap (57 - 109).
  `ptcl.py` names +0x448 `emit_rate_random` (`start_frame` an alias); `fx_render` starts emitters at +0x44C. Not changed:
  `vfxb_to_ptcl.py` / `xv2_to_ptcl.py` write start frames into +0x448 too (other fighters' ports).
- **Burn tiers** (exe feature `tiers`, `tools/gekkouga_clone_cave.py` `BFX_TIERS` / `BFX_TIER_IDS` / `bfx_tier`): the
  fire on a burning fighter by tier, from all its burns: instances, remaining damage (each damage a tick x frames left /
  interval) and the strongest rate (x 60 / interval); the highest tier one of whose minimums is met (4: 6 / 20 % / 6 %/s,
  3: 4 / 8 % / 4 %/s, 2: 2 / 4 % / 1.8 %/s), 1 with any burn. So one neutral air 1, a forward air 2, a smash 3, the
  explosion 4; weak burns climb by count. Each tier its set (size 1): PtcGekkougaFireBody1 0x330001F (fire_torch_012 22
  tall), FireBody 0x330001A (burn v2's, tier 2), FireBody3 0x3300020 (fire_small_5 42), FireBody4 0x3300021
  (fire_ground_10 56 + fire_small_5 40 layered, colour x 1.25); swapped only on a tier change (0x2723 (old, 1, 1),
  0x2717 new), a 15-frame fade when the burns end (0x2723 (id, 0, 0)). Preview `$S/gk_preview/burn_tiers.png`
  (`tools/gekkouga_burn_preview.py`: his model in Wait1 as a grey stand-in).
- **Forward air's blade flames**: PtcGekkougaFireBlade (0x3300022, `gekkouga_fx.py` `FIRE_BLADE`): 6 flames, one emitter
  each, bases from 2.5 to 11 down the sword's joint (its -Y, as the sword), the n-air ring's clips in turn, each its own
  start cell, 1.8x the ring's heights, +- 14 degrees (billboards: upright, they can't turn with the blade), looping until
  ended; `gekkouga_build.py` `FIRE_BLADE_SCRIPTS` calls it at the sword's own External_Graphic (joint 25, size 1) in place
  of burn v2's tip flame, ended with the sword; the clones' forward air too. Preview `$S/gk_preview/fair.png` / `.gif`
  (`tools/gekkouga_fair_preview.py`). Unresolved there: model.jtb table 0 makes the sword's joint 25 ThrowN, which
  AttackAirF holds still at his origin; the preview draws it on RHaveN (the hand in front) instead. The same mapping is
  the clones' (the user's "forward air's water sword doesn't move" on them): not fixed here.
- **Roll-off**: his game.bin's rolls had no roll-off speed (vanilla EscapeF, no EscapeB), while his MSC's rolls are
  kinetic type 0x6 (moved only by that speed): they stood still. `gekkouga_build.py add_rolloff`: `rolloff_acmd.add_speed`
  2.5 (EscapeB -2.5) at frame 5, cleared at 0 / 5 / 27; `cmd_msc` runs `universal_mechanics.py --air-mult 1.24
  --ground-uncapped` (`KineticModule(0x15, 3, -1, -1)` on the roll frames). `rolloff_hold_test --mult gekkouga=1.24`: as
  Hero's.
- **Collision attempt** (exe feature `gmupd`): the hydrant's update template runs its GroundModule's frame update
  (`0x02C34258`) every frame, Mario's pump's (the skeleton's base kind) never does (docs/native-notes.md "The hydrant's
  GroundModule frame update"); `sk_col_place` now calls it on every moved frame before the vertices (the hydrant's
  order). Not confirmed; the next step is the user's A_release log (S4SD / S4SE, S4CD - S4CH with the hydrant).
- Exes: exe_v46z_gkb6 = RELEASE (+ tiers, gmupd); TEST_ONLY A_release / G_pose. exe_v46z_gkb5 still rebuilds byte for
  byte (RELEASE - tiers - gmupd).
- Tests: `gekkouga_clone_cave_test` 239 / 268 / 263 (release / A_release / G_pose; `tier_checks`: the Python reference
  and the exe on 10 cases, swaps only on a tier change, the fade; the GroundModule update before the vertices);
  `gekkouga_fx_test` 51 / 0; `rolloff_hold_test` gekkouga ok; `gekkouga_clones_test ... --vac` 307 / 0;
  supamario_ui_cave_test 0; import_call_check 0. Not confirmed in game: everything here.

## Clone fixes v1 (`greninja_clonefix_v1.zip`, over skeleton v1.3; data only, exe_v46z_gkb6)

The user (screenshots `$S/gk_in/clone_fx/`): "the clones don't copy effects like neutral special's shuriken, forward air's
water sword doesn't move, Up air's twist doesn't appear, down air's effects stay on clones indefinitely, grab's effect
doesn't appear. Back air is missing it's blue inner trail", "Smash attack charging effects never clear for the clones".
The audit (his body effect.bin against the clone's): 28 clone effect scripts, only for motions with hitboxes and only
Graphic_Effect2 / External_Graphic / EFFECT_FLIP / EFFECT_FOLLOW_FLIP / Terminate / Sword_Glow; up air's twist is
Graphic_Effect5, the grabs (Catch / CatchDash / CatchTurn / CatchWait: no hitbox) never copied.
- **Effect scripts** (`gekkouga_build.py` `clone_effect`, `CLONE_EFFECT`, `CLONE_EFFECT_SKIP`): every motion's effect
  script (not his Final Smash's), its conditions' True branches (`flatten`, as v4's smashes), every effect request kind
  his scripts use (+ Graphic_Effect / 3 / 4 / 5, External_Graphic_Effect2, LANDING_EFFECT_FLIP, EFFECT_COLOR,
  LAST_EFFECT_SET_RATE), joints remapped; skipped: scripts that call / jump / loop (Run / Walk dust, Attack100,
  SpecialNHold, ...); a request on a joint past his model.jtb tables (an appeal's joint 26) left out. 100 scripts.
- **Stuck effects** (`weapons/clone.c` `cl_move_end`): a fighter's following effects end with his move; the clone's one
  status never ends and a script left early never reaches its Terminates (down air's streaks, the smashes' x5 water
  swords when he cancels / chains / jumps). On a new motion kind (not a restart) the clone ends every following effect
  with a fade: `EffectModule(0x2D, 0)` (vt +0xD4 `0x02C2BD44`: the object's following effects, `0x0334F308(record, 0,
  0)`; docs/native-notes.md). World requests (Graphic_Effect: puffs, sparks) play out.
- **Not fixed**: neutral special's shuriken (an article; a clone can't generate one: it needs exe code generating his
  shuriken at the clone's place, not done); forward air's sword on the clones (joint 25 = model.jtb table 0's ThrowN,
  still at his origin in AttackAirF's data, on him too: why it swings on him is not found); back air's inner trail (the
  clone's script is his exactly: likely a fighter-only effect colour, not found); "clones ... clip back to a set position
  constantly" on the ground (`$S/gk_in/clone_move/a.mp4`): not reproduced in the MSC test (walking at 2 a frame they
  follow his X 1 / 2 frames late, no jumps).
- Tests: `gekkouga_clones_test.clone_fx_tests` (hold -> up smash -> restart -> jump -> its own fall: 0x2D before each new
  move only; up air / grabs / down air / forward / back air / up smash request his effects; all 100 scripts his requests
  in his order); the v4 smash-size check now compares with his. Not confirmed in game.

## Fire trail fix v1 (`greninja_firetrail_fix_v1.zip`, over clone fixes v1; data only, exe_v46z_gkb6)

The user (burn v2+ in game): "the lingering fire trails left by smash attacks seem to be in the wrong axis" (down smash:
a diagonal line receding into the screen; up smash: a column of flames, each with a hard flat bottom).
- **The axis** (`weapons/firetrail.c` `tr_fx_dz`): the flames were requested on joint 0 (0x2717) with their offset on
  local X x its way. The trail turns its model by its way (`PostureModule(0, way)`, `(2)`: as the clones, a fighter's
  frame, +Z forward), so local X is depth. Now the offset is local Z (no x the way: the turn mirrors it): forward smash
  10 - 42 ahead, down smash +- 10 - 37, **up smash +- 6 / 14 on the ground under it** (where its geyser rises; v1 - clone
  fixes v1: a column of 4 over it at Y 0 - 42; an interpretation, the coordinator asked the user). Preview
  `$S/gk_preview/trails.png` (`tools/gekkouga_trail_preview.py`).
- **Hard bottoms** (`tools/gekkouga_fx.py` `soften_bottom`, `FIRE_SOFT_BOTTOM` 0.16): the atlases' frames are clear at
  their edges; the hard edge is the flame's own base, opaque to its last row. Every fire flipbook (additive sets: the
  trail, the tiers, the tips, forward air's blade, the n-air ring) is faded linearly from its lowest lit row over 16 %
  of the frame's height, per cell (colour too: additive).
- Tests: `gekkouga_clones_test ... --vcf` 313 / 0; `firetrail_tests` (each smash facing right and left: the flames' X 0, Y 0, local Z along
  the way; the facing turn); `gekkouga_fx_test.soft_checks` (the bases' biggest row-to-row alpha drop, as built: 11 - 22
  of 255 against the footage's 80 - 130; fire_torch_012's wisps 23 already). Not confirmed in game.

## Skeleton v1.4 (`greninja_skeleton_v1_4.zip`, over fire trail fix v1; release exe exe_v46z_gkb6, new TEST_ONLY diag)

Also the clone fixes v2 items (one package).
- **Skeleton walls**: the user, with v1.3: "doesn't have collision on its sides, but has collision on top" (v1.3's
  GroundModule frame update made the top work), and "I believe the test one is there": skeleton v1.1's TEST_ONLY
  floor-only skeleton.lvd (the top line only). v1.4 ships the box skeleton.lvd (`skeleton_lvd`: 4 vertices up the left
  side, across the top, down the right, x +- 6 / y 2 - 28; normals out of the solid, each line's direction turned
  counter-clockwise as the hydrant's floor line; materials the hydrant's) in INSTALL_TO_data, over the test one. No
  Landmaster or stage .lvd is in the workspace to compare wall lines with. TEST_ONLY exes: `sk_coldiag` adds **S4SV**
  (every 30 frames: the skeleton's place and vertices 2 / 3, x10, after S4SD's 0 / 1): `skeleton_checks` moves all 4
  through the game's vertex list and reads them back. The release exe is unchanged (gkb6, byte for byte).
- **The clones on the ground** (the user's two clips: they "clip back to a set position constantly", bunch and
  separate): his walk / run / dash attack / dash grab motions carry TransN forward (WalkMiddle 22 a loop, Run 33,
  AttackDash 25.5); a fighter's kinetics turn it into his movement, an article draws it, so each clone's model ran ahead
  of its place (already his X + its offset) and snapped back every loop. `gekkouga_build.py root_still`: the clone's
  main.pac keeps TransN's X / Z at 0 on every frame (Y, rotation as they were). `ground_move_tests`: walk 1.43, dash 1.6,
  run 2.08 (his fighter_param), turnaround, run back, skid, two dash-turns: each clone exactly his X 1 / 2 frames back
  +- 14 (world sides), no jump over 1.5 x 2.08; every clone motion's TransN still sideways. Diag (no exe change): every
  10 frames on the ground with clones out his VAR_23 = reasons x 10000 + (left error + 50) x 100 + (right error + 50)
  (error: the clone's X - his X - its offset, +- 49; reasons 1 / 2 wall, 4 history restart, 8 back in formation, 16 / 32
  falling on its own), flags bit 1048576 toggled so the TEST_ONLY exe's S4GF line logs it (gen=).
- **The clones' forward air sword** (the user: "Clones also still display trails incorrectly": the sword, its trail and
  flames hang straight down): his joint 25 (forward air's sword and trail, the smashes' second sword, SpecialNHold's
  shuriken) is model.jtb table 0's ThrowN, which no motion of his moves (main.pac's track constant, no part pac keys
  it): on him something native moves it (not found); on the clone it stays still. `CLONE_JOINT_FIX` {25: LHaveN}: the
  clone's effects and hitboxes on his joint 25 use its left hand (the smashes' two swords are 24 = RHaveN and 25; the
  shuriken is charged on 25), TEST_ONLY_DATA clone_sword_rhave (the right hand) / clone_sword_thrown (as before) to
  compare. Back air's inner trail is on joint 2 (HipN, animated on the clones): not this, still open.
- **Up smash's trail hitboxes** on its flames (+- 6 / 14, Y 5; fire trail fix v1 moved the flames only).
- Tests: cave A_release 269 / G_pose 264 / release 239; `gekkouga_clones_test ... --vft` 321 / 0. Not confirmed in game.

## Skeleton v1.5 (`greninja_skeleton_v1_5.zip`, over v1.4; exe_v46z_gkb7)

The user: the box "closer to the skeleton's body rather than its outer flames"; "a contact burn damage ... about 4%
overall but rehits quickly ... about 70% overall if it was for 1 second"; "make the explosion have 1.6x hitstun"; "make
the explosion effect and hitbox slightly bigger and do a lot of shield damage"; "HaveR fixed the sword"; its sounds.
- **Body box** (exe feature `skbody`, `SK_BODY` / `sk_dims` / `sk_verts`): measured on skeleton_run's 55 cells as drawn
  (5.60 px a unit): the bones (red over the flame) reach 26.6 (skull top, median), the ribcage spans -2.3 / +2.7 round the
  spine, the spine 2.2 ahead of the picture's centre. The billboards move back 2.2 along joint 0's local Z (the skeleton
  turns its model by its way: `gekkouga_fx.py SK_SPINE_X`, both sets); skeleton.lvd x +- 3.5, walls from 2, top 24; the
  HP hit box the same. Preview `$S/gk_preview/skeleton_box.png` (`tools/gekkouga_skeleton_box_preview.py`).
- **Contact burn** (exe feature `sktouch`, `SK_TOUCH_ROW` 0.35 % every 6 frames for 60 = 3.5 %; `gekkouga_build.py
  SK_TOUCH` / `sk_run_script`): SkeletonRun puts a capsule (joint 0, radius 3.5, Y 3.5 - 20.5) on 2 frames, off 1 (vanilla
  up air's multi-hit pattern: the hit log restarts), no knockback / hitlag / flinch, 0.1 %; the exe's `sk_frame` scans its
  running hits with the contact row (its explosion's with the skeleton row). 1 s of contact: 20 touches = 70 % (+ 2 %),
  at most 20 instances alive (cap 32); shielded: the 1 % floor each.
- **Explosion**: Extra_Special_Hitbox (the ACMD extension) HitstunMul 1.6; size 22 -> 27 and its footage 44 -> 54 wide
  (`SK_BOOM_DIAMETER`); ShieldDamage +40 (15 + 40 = 55 against a fresh shield's 50: a full break; the formula as Smash 4's
  damage + shield damage, its multipliers not in the workspace's references).
- **Clones' joint 25**: the right hand (`CLONE_JOINT_FIX` {25: RHaveN}), confirmed in game (v1.4's TEST_ONLY
  clone_sword_rhave); the TEST_ONLY variants dropped.
- **Sounds** (`tools/gekkouga_sound.py`, the `fighter_own_bank.py` route: silence trimmed under -45 dBFS, mono 48 kHz
  IDSP one-shots at a -0.5 dBFS peak, TONE entries copied from his Special_L01): 6 tones appended to snd_se_Gekkouga
  (BINF 2058 kept: 104 -> 110 tones) and their labels 91 - 96 to his soundlabeltable row 0x768 (ids 0x0768005B -
  0x07680060: spawn 1 / 2, voice 1 / 2 (-3 dB), death, explosion), on the newest table in the workspace
  ($S/v14/out/sound/config/soundlabeltable.bin, Supamario / Byleth rows; only his row changes). `weapons/skeleton.c`:
  `sk_snd_spawn` (one of the two, `randi`), `sk_snd_voice` (the first 10 - 40 frames in, then each next at the last one's
  length - 30 + 0 - 90 frames: up to 0.5 s overlap, up to 1 s gap), `sk_snd_end` (its voices stopped, SoundModule 0x2714
  both, then the death's / explosion's); it stays hidden until that sound has played (`sk_boom_frames` 40 -> 120,
  `sk_smoke_frames` 3 -> 36), so a new skeleton waits that long. `fighter_own_bank.build_bank` skips the bank's 14 empty
  TONE entries when looking for the template; `rolloff_hold_test.VM` evaluates its binary ops lazily (a negative right
  operand tripped the shifts).
- Tests: cave 240 / 270 / 265; `gekkouga_fx_test` 52 / 0; `gekkouga_clones_test ... --vs14` 323 / 0 (`skeleton_sound_tests`: ids =
  the table's, spawn pick, voice timing / overlap bounds, stops and the death / explosion sounds, removal after them; the
  contact script's frames and fields; the explosion's HitstunMul / size / shield damage; the package's bank / table);
  supamario_ui_cave_test 0; import_call_check 0. Not confirmed in game: everything but the clone sword's hand.

## Skeleton v1.6 (`greninja_skeleton_v1_6.zip`, over v1.5; exe_v46z_gkb8)

The user: "please make it so that the Skeleton always spawns from this distance, regardless of if the button is held.
Make sure the shadow matches" (`$S/gk_in/clone_fx/skeleton_spawn_distance.png`), then "Can you also disable side special
from being used while a Skeleton is alive", and "Please stop packaging G_pose".
- **The shadow (read from the exe)**: docs/native-notes.md "Greninja's side special shadow": the hold starts in his
  MSC (`func_2379`: flag 0x2000007C, 0x35 = 2), his slot 13 moves the shadow 1.2 a frame up to the vl max 70 while
  held (at least 5 frames), then status 0x153 with the shadow frozen at his place + 0x35 (a tap: 9.2). v1 - v1.5 made
  the skeleton there.
- **The distance**: 36 (`gk_sk_dist()` = `gekkouga_clone_cave.py SK_DIST`): the screenshot, his middle to the skeleton's
  spine 590 - 610 px at 16.2 px a unit (the skeleton's bones 26.6 tall = 430 px, 3x): 36.5 - 37.7; also the vanilla
  speed kept through the whole move, 2 + 1.2 x (6 + 22) = 35.6.
- **Exe feature `skdist`** (`SK_DIST_PATCH`, in RELEASE): the hold's cap is SK_DIST in place of 0x0600000C (no vl file
  shipped): held, the shadow stops at 36. **MSC** (`clones.c gk_ss_shadow`, called from `gk_ss_tick`): in SpecialS, a
  shorter shadow (a tap, a hold let go early) goes on evenly to 36 by SpecialS frame 20 (`0x16000006 + 0x16000007 -
  2`); the skeleton is made at 21 from 0x31 / 0x32 as before, so it is always on the shadow. **The hold kept**: it
  still delays the release (to vanilla's 90 frames) for timing, the distance doesn't change (the README asks the user
  whether the hold should do nothing instead).
- **No side special while a skeleton runs**: `weapons/skeleton.c sk_beat`: while running (phase 1) bit 4 in its owner's
  VAR_30 (SLOTn_SHARED_6, the clones' heartbeat word) every frame; `clones.c gk_sk_heartbeat` (every frame in
  `gekkouga_frame`, before the clones' `gk_heartbeat` clears the word) takes it out and keeps `gk_sk_live` 2 frames;
  `gk_ss_allowed()` (0 with `gk_sk_live` or `gk_sk_req_t`, the request in flight) gates `func_2379`'s press (MSC_EDITS:
  the hold's start is the only way in: the vanilla side special transition is off every frame there). "Alive" ends at
  the explosion / smoke (not at the removal after its sound, up to 2 s): the coordinator's suggestion. Clone articles
  (later) owned by him write the same bit.
- **G_pose dropped** (`VARIANTS` = A_release only); the `pose` feature code stays (the exes up to v1.5 rebuild with it;
  `gekkouga_clones_test.exe_members` adds G_pose back for those packages).
- Tests: cave 242 / 272 (release / A_release; `skdist_checks`: the game's own advance words in unicorn: 2 -> 3.2, 9.2 ->
  10.4, 34 -> 35.2, 35.5 -> 36, 36 stays; gkb7 = RELEASE - skdist byte for byte, 241); `gekkouga_clones_test ... --vs15`
  329 / 0 (`skeleton_v16_tests`: a tap / the first frame / a cut hold / a full hold all end at 36 by frame 20, even
  steps, never past, the skeleton at 21; side special blocked from the first heartbeat, through 100 frames, free 2 frames
  after, ground and air; the request in flight blocks; func_2379's only change; `skeleton_tests`: the heartbeat while
  running (the clones' bits kept), none after the explosion); supamario_ui_cave_test 0; import_call_check 0. Not
  confirmed in game: everything here.

## Tilt chain v1 (`greninja_tilt_chain_v1.zip`, over skeleton v1.6; data only, exe_v46z_gkb8)

The user: "please make jab chain into tilts (except rapid jab) and have tilts chain into tilts"; on hit only, each tilt
once per chain (their choices). Modelled on the aerial chain (`clones.c gk_tc_*`):
- `gk_tc_start(k)` in the status mains (MSC_EDITS: jab Attack 0x25 `func_263` k 4, AttackS3 0x28 `func_275` 1,
  AttackHi3 0x29 `func_278` 2, AttackLw3 0x2A `func_281` 3): a new chain unless a chain cancel asked for it (`gk_tc_req`);
  a tilt marks itself used (2 / 4 / 8), a jab doesn't; AttackModule 0x2724 (its hits from 0). Jab 1 - 3 re-enter 0x25;
  the rapid jab is Attack100 0x26 (`func_336`), not hooked.
- `gk_tc_try()` first in their loops (`MSC_TILT_CHAIN`: `func_270` / `277` / `279` / `282`, before the IASA check):
  AttackModule 0x2727 kind 2 (a hurtbox; a shield doesn't count) opens the window the frame after, not in hitlag, on the
  ground (situation 0); the game's tilt bits (global24 0x4 up, 0x8 down, 0x2 forward: func_43's order) with no smash bit
  (0x70: left to the game) -> `func_16(0x27 + k, 1)` for a tilt not used yet.
- Ends (`gk_tc_end`) in `gekkouga_frame` on any status but 0x25 / 0x28 / 0x29 / 0x2A, and on `gk_reset`.
- Clones: a clone's landed copy (the exe's VAR_22, `gk_clone_hitlag`) counts as a hit (`gk_tc_clone_hit`), shield or not
  (VAR_22 can't tell).
- Diag: in a jab / tilt VAR_20 gets 2097152 + the aerial chain's fields for the tilt chain (256 x the move: 1 / 2 / 3
  tilts, 4 jab; 2048 hit; 4096 window; 8192 x the used bits): under 2^24, so VAR_20's low flag bits stay exact in the
  float.
- Tests: `gekkouga_clones_test ... --vs16` 358 / 0 (`tilt_chain_tests`: the hooks' places, a whiff / shield / hitlag /
  smash input / air refused, jab -> forward -> up -> down, repeats refused, all three, the diag, the ends (walk, jump,
  shield, hit, special, smash, aerial, rapid jab), the rapid jab without a chain, a clone's hit). Not confirmed in game.

## Burn tint v1 (`greninja_burn_tint_v1.zip`, over tilt chain v1; exe_v46z_gkb9)

The user: "based on burn amount and strength, please tint the opponent into an orange more with a feint red outline", then
"The higher strength levels should turn into a hot red". Exe feature `btint` (in RELEASE; `gekkouga_clone_cave.py`
`BTINT_*`, `bti_vic` / `bti_shell` / `bti_unshell`, called after `bfx_vic` in burn_tick):
- **Level**: the fire's tier (`bfx_lvl`, BFX_TIERS: count / remaining damage / strongest rate), stepped once a frame by
  the first live Greninja's burn_tick (later ones skip it).
- **Colour table** (overlay rgb, alpha; outline rgb, alpha, width px of 1280 x 720):

  | tier | overlay | alpha | outline | alpha | width |
  | --- | --- | --- | --- | --- | --- |
  | 1 | light orange 1.0 / 0.60 / 0.20 | 0.18 | red 1.0 / 0.12 / 0.06 | 0.28 | 1.5 |
  | 2 | orange 1.0 / 0.47 / 0.14 | 0.26 | 1.0 / 0.10 / 0.05 | 0.34 | 1.75 |
  | 3 | red-orange 1.0 / 0.35 / 0.10 | 0.34 | 1.0 / 0.08 / 0.04 | 0.40 | 2.0 |
  | 4 | hot red 1.2 / 0.15 / 0.05 (red over 1: heat) | 0.42 | 1.0 / 0.06 / 0.03 | 0.48 | 2.5 |

- **Overlay**: the victim's ColorBlendModule (accessor +0x38) vt +0x4C(&rgba 0-1, slot 1, 0) every frame while it burns
  (drawn lit x (1 - a) + rgb x a); slot 1 shows only when slot 0 is off or lower in priority (vt +0xAC), so the game's own
  flashes (slot 0) win; vt +0x44(1) clears it.
- **Outline**: an entry of `outline_shell_cave.py`'s table in the base exe (os_tab `0x04BE5F5C`, 16 x 0x50; os_count
  `0x04BE5388` asserted) held (phase 2, no frames, blend 0); only when the victim has no entry (an ACMD Outline_Shell's:
  Supamario's Ultra Instinct glow stays); ours dropped if a command changes it (its width no longer ours) and never
  freed then; os_frame drops it itself on a KO / model change.
- **Clears**: the burns end -> both fade over BTINT_FADE 15 frames (the fire's fade), then the slot cleared and the entry
  freed; Dead / Rebirth -> off at once; gk_clear (match / training reset) -> tier 0, fade -1: off the next frame.
- Preview `$S/gk_preview/burn_tint.png` (`tools/gekkouga_tint_preview.py`: his textured model, the overlay formula and a
  dilated band; the outline's width approximate).
- Tests: cave 259 / 289 (`btint_checks`: the table, tiers 1 / 2 / 4 overlay + entry, every frame, the 15-frame fade on
  the same entry then off (count 0), a command's entry left alone, a taken-over entry not written / not freed, KO at
  once, the reset, an earlier Greninja's burn_tick doing it; gk_clear's state; gkb8 = RELEASE - btint byte for byte);
  supamario_ui_cave_test 0; import_call_check 0. Not confirmed in game: everything here.

## Skeleton v1.7 (`greninja_skeleton_v1_7.zip`, over burn tint v1; exe_v46z_gkb10)

The user: "make the explosion hitbox from the skeleton more active (until right before all of the orange is gone in the
explosion.) and fix the skeleton's ability to multihit, it seems inconsistent now", "please make the skeleton slightly
slower", "The skeleton sounds don't play. I made sure I had the correct files."
- **The explosion's window** (`gekkouga_build.py SK_BOOM_FRAMES` = `weapons/skeleton.c sk_boom_hit_frames()` = 101):
  explosion_simple_24's orange (`gekkouga_clones_test.boom_orange`: pixels with alpha > 0.3, R > 0.45, saturation > 0.35,
  R > B + 0.25, per cell; 4 game frames a cell) peaks in cells 14 - 16 (~4560 px), is 5 % of that in cell 24, 2 % in 25
  (frames 100 - 103), 1 % in 26, none from 28 (frame 112). The hitbox: set at the explode motion's frame 0 (the effect's
  frame 1) and turned off by its MSC (`AttackModule(0x2719)`: its hit records kept) at the effect's frame 102. The
  explode motion (the hydrant's, 30 / 48 frames) would loop and run its script again (the hitbox set again: a second
  hit on everyone), so the MSC holds it (rate 0) from the frame after. One hit an opponent (Rehit 0); 15 %, hitstun x 1.6,
  shield damage, burn, size 27 unchanged (no shrink: Change_Hitbox_Size's effect on the records isn't known).
- **The contact burn's misses (exe feature `mark`)**: burn_scan counted each hit log's records; every new Hitbox command
  frees the Part's records and the next hit is appended in the same frame, so a victim standing in the on 2 / off 1
  hitbox showed "1 record, as before" at every re-set (docs/native-notes.md "Hit records are freed by every new
  hitbox"). Now the append's three callers go through `MARK_TRAMP` (0x037EE580: clears the new record's +0x2E padding,
  then `b 0x02C10F40`) and burn_scan burns every record not marked (0xA5 at +0x2E) and marks it (all his burns: his moves,
  the clones', the skeleton's, the trails'). SkeletonRun is now one capsule set once a loop with the game's rehit rate
  3 (`SK_TOUCH_REHIT`; Hitbox.csv field 31); TEST_ONLY_DATA/skeleton_toggle has v1.6's on 2 / off 1 (with v1.7's
  explosion). Unicorn: a victim standing in it 60 frames, a hit every 3 frames, re-set before each hit in the same frame
  or a growing log: 20 burns (70 %); gkb9's counting route: fewer.
- **The sounds (exe feature `sksnd`)**: the skeleton's module row (the clone's: bunshin's with the pump's empty slots
  filled) had no SoundModule (slot 11, accessor +0xA4): the weapon set-up put the null SoundModule there, whose MSC handler
  returns 0: every SoundModule call of its MSC was dropped without an error (docs/native-notes.md "An article with no
  SoundModule plays nothing"). The bank and table were built by fighter_own_bank's route (Supamario's, working); his 110
  tones / labels 91 - 96 are as tested in v1.5. Its slot 11 is now `0x02BCC844` (the hydrant's / the shuriken's weapon
  SoundModule). Diag: its MSC notes each play (`sk_play`: VAR_13 the count, VAR_14 the label, VAR_15 the answer) and the
  TEST_ONLY exe logs **S4SN** (owner, count, label, answer, its SoundModule) on each. TEST_ONLY_DATA/sound_via_greninja:
  his installed MSC (tilt chain v1's, git bc7e3ea) + `SoundModule(0x2710, 0x0768005B)` in `gk_sk_spawn`
  (`gekkouga_build.sound_test_msc`): separates "the sound" from "the article".
- **Speed** 0.7 -> **0.58** (`sk_speed`); its run flipbook slowed as much (`gekkouga_fx.SK_RUN_RATE`, `flip_seq`: 55 cells
  in 66 entries, every 5th cell twice, 132 frames a cycle; 3 emitters of 22) so the stride keeps to the ground as before.
- Exes: exe_v46z_gkb10 = RELEASE (+ mark, sksnd); gkb9 = RELEASE - mark - sksnd byte for byte. The diag build's cave
  ends at 0x04BF3BBC (limit 0x04BF4000).
- Tests: cave 265 / 296 (`mark_checks`: 20 burns both ways, every record marked, the trampoline, the three sites; the
  row's slot 11 and the null module; S4SN; gkb9 260 / 290 with "the counts miss"); `gekkouga_fx_test` 52 / 0 (the slowed
  sequence as eft plays it); `gekkouga_clones_test ... --vbt` 365 / 0 (the explosion's window against the measured orange,
  the held motion and the 0x2719 at 102, the contact's rehit, the toggle data, 0.58, the sound notes, the package);
  supamario_ui_cave_test 0; import_call_check 0. Not confirmed in game: everything here.

## Aligned kick v1 (`greninja_aligned_kick_v1.zip`, over skeleton v1.7; data only, exe_v46z_gkb10)

The brief: during the ability, down special with no left / right starts an aligned attack (the counter's up-diagonal
kick on all three, the user's arrowhead sketch `$S/gk_in/clone_fx/aligned_kick_shape.png`), tapped / held variants, his
peak above theirs, swaps any time, normal Fall, once an airtime; after it the clones are **split** (the user: "Clones
should mirror inputs. They should not regroup when landing. If shield + special is pressed, Greninja should do a quick,
short animation and the clones should slowly move back to him"). Plus two user bugs (a swap at an aerial's landing left
its effect on the clone; the charge gauge should reset at a KO).

**Globals freed first** (his MSC had 127 of 128): his 64 New_Var slots (`0x0F000380 + i`, his own object's: floats,
whole numbers exact, read 0 until written, cleared at a KO) hold state now (`clones.c` `gk_vi` / `gk_svi`, `gk_bv` /
`gk_bs` / `gk_bvi` / `gk_bsi`). Moved: `gk_fx_t` (slot 0), `gk_cursor_t` (1), `gk_cl_why` (2), `gk_cl_t` (3), `gk_gen_req`
(4), `gk_hold_first` (5); removed (written, never read): `gk_pips`, `gk_spawn_bits`, `gk_spawn_t`. 118 of 128 now; every
new value is a slot. Slots: 8 the clones' mode (0 formation, 1 the kick, 2 split, 3 regrouping), 9 the kick used this
airtime, 10 the kick's clock, 11 its variant (1 tapped, 2 held), 12 the regroup's clock, 13 the effects epoch, 14 his
situation last frame; 16 x b + k for body b (1 the left-spawned clone, 2 the right-spawned one, 3 him): k 0 action, 1
frames in it, 2 motion kind, 3 its start frame, 4 the command's seq, 5 facing, 6 X speed, 7 Y speed (his; the clones'
are `gk_lvy` / `gk_rvy`), 8 flight frames left, 9 air jumps, 10 smash charge, 11 smash chain, 12 tilted, 13 aux (smash
type + 8 x auto / the aerial / the landing lag), 14 / 15 the regroup's start.

**The kick** (`gk_ak_*`): `gk_input` lets a stick-down special with |X| <= 0.25 through (no buffer clear) during the
ability, so the game's down special input (func_43 / func_58 / func_675 / func_1999, only when he can act) reaches
`gk_lw_press` -> `gk_ak_try` (not used this airtime, no kick / regroup running) -> status 0x161 (SpecialLwAttack, unused
since clones v1). `MSC_BODIES`: its pre (`gk_ak_pre`: situation air, Hydro Pump jet's first line), main (`gk_ak_main`: the
kick motion 0x28D at 5/8, flag 0x2100001C (his game script's up-diagonal branch: 13 %, 60 degrees, frames 5 - 20), the
effect / sound flags off (their False branches play), `FighterUtil(6, 270)`: turned straight up), init (`gk_ak_init`: his
energies 1 / 3 at our speeds, no limits), exec (`gk_ak_exec`: the rotation every frame), end (`gk_ak_end`: upright).
- Timeline: the kick's clock (gekkouga_frame, which runs before the status's global16 in a frame) 0 - 7 the startup (all
  three still; the clones' motion paused on frame clock x 5/8, stepped by him); at 8 (`gk_ak_launch`) the variant
  (special held -> held) and three paths: him 78 up in 15 frames (5.2 a frame), each clone toward the centre line at 53
  degrees (the sketch's arrows: 52 / 54), 64 (tapped: they cross above him, ending 24.5 past it) or 46.5 (held: 28
  across, ending at +14 / -14 on the other side), 15 frames; then a quarter of the speed kept and gravity (0.18, 1.85).
  Peaks: him ~81, the clones ~53 (tapped) / ~38 (held). He ends in Fall (0xE) at 23 (a landing after the lift-off:
  LandingLight 0x17).
- Swaps (`gk_swap_free`): places exchanged and the momentum: a flight's rest (speed, frames) goes with the place; in 0x161
  his path is ours; else his speed set (energy 1 vertical, energy 3 horizontal: approximate) and the clone gets his
  SPEED_X / SPEED_Y.
- Once an airtime (slot 9): cleared on the ground (not in 0x161) or on a ledge.
- A kick cut before its kick frame (he was hit): the clones back in formation where they are.

**The channel in free mode** (his VAR_31 flags + 128): VAR_28 / VAR_29 each clone's command (`gk_fpack`: kind + 1024 x
start frame + 2^20 facing left + 2^21 tilted + 2^22 paused + 2^23 seq, under 2^24). The clone (`weapons/clone.c
cl_free`): a new kind or seq -> that motion from the start frame (its scripts from there), else on at rate 1 (0 when he is
frozen, flags 64); paused: held on the frame; tilted: `PostureModule(4, -53, 0, 0)` (relative to its facing: its kick
along its flight); `(int)` of the float without + 0.5 (past 2^23 the + 0.5 rounds to even: a wrong kind). Back in
formation: upright, his motion from the channel again. The clone's kick scripts (`gekkouga_build.clone_kick`: the 0x1C
branch's hitboxes on bone 4 as the article's, frames 5 - 20; his kick's effects).

**Split clones** (`gk_free_frame` -> `gk_fc`): from his stick, `global24` (CAT1), attack held; nothing while he is hit /
on a ledge / calling them. Ground (`gk_fg`): wait / walk (0xB, 1.43 x |X| / 0.75) / dash (0x11, 1.6, 10 frames) / run
(0x12, 2.08); jump (squat 0x18, 4 frames, then JumpF 0x19: 4.07 full / 2.82 hop by the jump still held, X x 0.8 + stick x
0.95 up to 1.3); smash > tilt > jab / dash attack: smashes `gk_fsm_begin` / `gk_fsms` / `gk_fsmh` (his rules: the start
to its hold frame 8 / 9 / 5, held -> the hold motion charging its own store to 120, released early / full -> Wait, a full
store or a chain releases on its own from the hold frame), chains (`gk_fchain`: from 16 / 22 / 19, each once), jab 1 -> 2
-> 3 (a new press from 6 frames in), tilts (forward faces the stick), the fire trail at its smash's hit; friction 0.045.
Air (`gk_fa`): one double jump (JumpAerialF 0x1B), the aerial from the command bits (forward / back by its own facing:
`gk_aerial`), drift (1.18 max, 0.08 accel, 0.015 friction), fast fall (2.96 with the stick down). Ends: his vl group 1
cancel frames (`gk_mlen`: jab 22 / 22 / 36, dash attack 33, tilts 39 / 33 / 27, smashes 50 / 52 / 55, aerials 65 / 55 /
46 / 42 / 57), else the motion's length. Movement (`gk_fmove`): walls, floors (slopes), off a ledge it falls, ceilings,
landing (LandingAir 0x6D - 0x71 with his aerial landing lag 12 / 15 / 13 / 15 / 32, else LandingLight 4 frames); no
regroup on landing. No ledges, specials, grabs, shields.

**The regroup** (`gk_rg_*`): split, special pressed with shield held, when he can act (statuses up to 0x15 but helpless,
or guard 0x1B - 0x1D): the press eaten and status 0x160 (SpecialLwHit's slot, unused): the stance (speciallw /
specialairlw) at 0.4 for 19 frames (motion frames 0 - 7.6: before its vl intangible window 8 - 19), its init the stance's
physics (`func_2340`); the clones (mode 3) eased (smoothstep) over 75 frames from where they were to his X -/+ 14 and his
Y (walking on his floor, else floating; no wall tests), then formation (their offsets, history from now).

**The user's bugs**: (1) a swap (formation or free) and his landing in formation flip the effects epoch (slot 13 ->
flags 256); the clone (`cl_fx_epoch`) fades its following effects (`EffectModule(0x2D, 0)`) on a change; `cl_move_end` now
fades on any new kind, also after its motion was forgotten (-1). (2) a KO (0xB1 / 0xB2) sets `gk_lw_charge` 0 (the gauge
0, no ready blink); the smash store is still kept (the original spec).

Tests (`gekkouga_clones_test ... --vs17` 410 / 0): `aligned_kick_tests` / `aligned_kick_more_tests` (the trigger standing
and in the air, the swap still on left / right, the main's motion / rate / rotation / flag, the startup's paused commands,
both variants' paths and his peak, the end in Fall upright, the swap mid-flight, once an airtime), `split_tests` (aerials
by facing, landing lag, no regroup, walk / dash / run, jab 1 -> 2, up tilt, a forward smash's hold and early release, a
stored up smash's auto release, a chain, a jump, the regroup's call / slow return / formation), `bugfix_tests`,
`clone_free_tests` (the article's commands, pause, restart by seq, freeze, back to formation, the epoch), `kick_data_tests`;
the earlier tests updated (the down special during the ability, the charge at a KO, the epoch bit). Not confirmed in game.

## Clone articles v1 (`greninja_clone_articles_v1.zip`, over aligned kick v1; exe_v46z_gkb11)

The user: "allow clones to spawn duplicate articles, such as the skeletons, water shuriken and hydro pump (clone skeletons
should spawn on top of each other, forming a stack of skeletons)"; plus two answers / bugs: a KO also clears the stored
smash charge, and "When using the clone kick, the clones never clear the hitbox from the kick". Only clones in formation
(copying his moves: alive, not falling on its own, not split / kicking / regrouping) make articles (`gk_art_clones`).
- **Skeletons (a stack)**: `gk_sk_spawn` queues the clones' (`gk_sk_stack`: slot 15 the clones still to ask for, 6 / 7 his
  skeleton's place); `gk_sk_queue` (every frame) asks for the next once his request was claimed (his VAR_15 back to 0 while
  `gk_sk_req_t` runs): his VAR_15 = 1 + the level (1 the first clone's, 2 the next), its place his skeleton's X and its Y +
  24 x the level, his facing, `ArticleModule(0x2710, 8)`; one a frame (the clones' delays); dropped if a request isn't
  claimed in time. Exe (feature `cart`): his article list allows 3 skeletons (`SK_LEVELS`); the claim gives each its
  level (his VAR_15 - 1 -> its VAR_20); each running skeleton writes its accessor / a frame counter / x / y into
  `SK_SEAT[owner][level]` (let go when it explodes / smokes) and one with a level reads the one below's into its VAR_17
  (1 there) / 18 / 19 / 21 (its counter mod 10); its HP latches a bank per level. Its MSC (`weapons/skeleton.c
  sk_seat_step`): while the one below is there and its counter moves, it sits on its top (x, y + 24: the skeleton.lvd top
  line), else it falls (his gravity) and runs on. Side special stays blocked while any runs (each beats).
- **Water shurikens**: `gk_sh_copies` (MSC_EDITS: right after his `ArticleModule(0x2719, 0)` in SpecialNShot `func_2271` /
  SpecialNMaxShot `func_2279`): per clone out, `ArticleModule(0x2710, 0)` then `(0x2719, 0)` (generated and shot as his:
  the shot reads his charge), slot 57 the clones waiting (the channel's flags 512 / 1024, 3 frames: `gk_sh_tick`). His
  shuriken's MSC is now ours (`weapons/shuriken.c`: vanilla shuriken.mscsb decompiled, recompiling to the same functions,
  + `sh_frame` on global14): a shuriken in its first 2 frames with a copy waiting claims the first clone not claimed this
  frame (claim bits 64 / 128 in his VAR_30, cleared by him each frame) and, once shot (status 2 / 4), moves once by that
  clone's place minus his. His own (made at his hold, long before) is never a copy. Exe: 9 shurikens (`SH_MAX`).
- **Hydro Pump's water**: not done: the water (article 1, 0xFA) is made by native code each jet (no MSC / ACMD
  `ArticleModule(0x2710, 1)` in his files), so neither route above reaches it.
- **The clones' hitboxes** (the user's kick bug): the clone article's one status never ends, so hitboxes set by a script
  stayed until the script's own Remove_All_Hitboxes; the kick's is at FRAME 20 of a 20-frame motion (frames 0 - 19: never
  reached), and any move a clone leaves early (a landing, a cancel, a chain, a split command) had the same hole.
  `cl_move_end` (every new motion or restart, formation and free) now clears them first (`AttackModule(0x2719)`, its hit
  records kept). His own kick ends with a status change (cleared).
- **A KO** (the user: yes, clear the stored smash charge too): `gk_smash`, `gk_sm_auto`, `gk_chain_req`, the split
  clones' stores (slot k 10) to 0 at 0xB1 / 0xB2, with the down special's charge (aligned kick v1). Nothing is kept
  across stocks now (Clones v1 / v3's "kept across stocks" no longer applies).
- Exe: exe_v46z_gkb11 = RELEASE (+ cart); the cave limit is `LIMIT_CART` 0x04BF8000 with cart (the diag build ends at
  0x04BF48C8); gkb10 = RELEASE - cart byte for byte (its LIMIT kept).
- Tests: cave 271 / 302 (`cart_checks`: the claim's levels, the stack table and seat VARs, the one below gone, its own
  entry let go, the latch banks; the article list's 9 / 3 and the 64-instance cap); `gekkouga_clones_test ... --vak` 422 /
  0 (`clone_articles_tests`: the skeleton queue (levels, places, one a frame, one clone, dropped), the shot's copies and
  the channel bits, the KO's resets, the seat and the fall, the shurikens' claims and move, his own untouched, the clone's
  clear on each new motion); supamario_ui_cave_test 0; import_call_check 0. Not confirmed in game.

## Round gauge v1 (`greninja_round_gauge_v1.zip`, over clone articles v1; data only, exe_v46z_gkb11)

Clones v7's round gauge, now built: the user sent their `ui/info/dmg` (the base game's, `$S/gk_in/ui_full/x/ui/info/dmg/`,
and the update's, `$S/gk_in/dmg/x/dmg/`: only 5 / 7 images there; the other ~128 texlist entries are run-time textures).
Built on the update's (the one the game loads). Its img-00133 / 00134 are not the update's but this workspace's own mods
(GIDX 0x2800FE00 / 0x2800FE01: the trait badge's and Hero's menu's textures), so the folder already has the trait badge.
- Art: `tools/gekkouga_gauge_art.py extract $S/gk_in/futui/x/41672.jpg ART` (41672.eps's 5250 x 3500 preview; LAYERS /
  FILL as in v7). Build: `tools/gekkouga_gauge_flx.py $S/gk_in/dmg/x/dmg ART OUT`: dmg.flx (+ `gkgauge_mc` in panel sprites
  1 - 4: the four rings, the track, the 11-frame fill), texlist.lst (16 entries on a new slot 135, the 353 existing entries
  / 135 slots as they were), img-00135.nut (1024 x 1024, GIDX 0x2800FE30). Only those three ship.
- Places (`PLACES`): rendered on the user's file (`tools/flx_render.py`), v7's places sat on the CPU level ("Lv.") and the
  trait badge's star; now in Little Mac's KO meter band (hidden while the gauge shows) right of the trait badge (its right
  edge + the gauge's radius + 2 - 3): panels 3 / 4 (1 - 2 / 3 - 4 players) (122, -58) x 0.24, panel 1 (5 - 8) (72, -52) x 0.16,
  panel 2 (small) (38, -27) x 0.12.
- The exe's driver (`gk_panel`, since v7: finds `gkgauge_mc` and its rings / fill by name, hides the KO meter, turns the
  rings, sets the fill frame, tints cyan / blue / grey by his VAR_19's mode) is unchanged.
- Previews: `$S/gk_preview/round_gauge.gif`, `round_gauge_sheet.png`, `round_gauge_panels.png` (before / with the gauge /
  full, per layout; the renderer draws every layer, Hero's menu included).
- Tests (`gekkouga_clones_test ... --vca --gauge-src= --gauge-jpg=` 427 / 0, `gauge_tests`): the three files rebuilt byte
  for byte from the user's folder and the art, the new slot 135 and its 16 cells, every existing entry / slot / sprite /
  image kept, the clip in panels 1 - 4 with the exe's GAUGE_NAMES and 11 fill frames, no overlap with the trait badge.
  Not confirmed in game.

## Clone fixes v3 (`greninja_clonefix_v3.zip`, over clone articles v1; independent of round gauge v1; data only, exe_v46z_gkb11)

Four user reports.
- **"make it so the use of down special just activates the clones. Please disable clone kick for the first 10 frames of
  clones existing"**:
  - The cause: the full gauge's press stayed in the game's command buffer and was read again on the next frames as
    the ability's down special, which is now the aligned kick (`gk_lw_press` -> `gk_ak_try`). That could start a kick
    before the clones were made, with no flight for a clone not made yet (the MSC interpreter: a kick at frame 1 / 3).
  - Now `gk_activate` clears the specials' buffer and the frame's special bits (`gk_lw_eat`) and locks the kick (slot 60
    = 0).
  - `gk_ak_arm` (each ability frame) arms it once `gk_seq >= gk_ak_lock()` (11: the left clone is made on the ability's
    2nd frame, so its first 10 frames) **and** special is not held.
  - Until then `gk_ak_try` refuses, and `gk_input` drops any stick-down press (`gk_lw_eat`, not buffered past the
    lockout). Swaps aren't locked.
  - Tests (`clonefix_v3_tests`):
    - activation held 30 frames (the input site asked on every held frame): no kick, armed at the release;
    - a press at frame 5 (even if it reached the site through frame 10): no kick;
    - frame 11: no kick;
    - a fresh press at 12, at 20, or after a held activation: the kick.
- **"articles spawned from clones spawn from the main body"** (the skeletons excepted, unchanged):
  - The copies' one move (v1) is most likely undone by the game placing the shot at his hand after it (the shuriken's
    MSC never sets its place; my reading, not seen).
  - `weapons/shuriken.c` `sh_frame` now sets the copy at the clone's **live** place (the channel's VAR_24-27, wherever it
    stands) + his hand's offset.
  - For `sh_fix_frames()` (8) frames it compares where the game left it with where it was set and with that minus the
    offset (his path). Nearer his path: set again.
  - The claim window is 3 frames (was 2).
  - Facing: copies are only made in formation (`gk_art_clones`), where the clones face his way.
  - Diag: each set is reported once a frame in his VAR_30 (`256 x (clone + 4 x set-again + 8 x (place - the clone's, in
    2s))`, `sh_report`). His `gk_sh_report` turns it into VAR_23 = 701 / 702 (set) or 801 / 802 (set again) + 1000 x
    the place, and flips the flags' 1048576 bit (slot 62), so A_release's S4GF line logs it.
- **"after using the clone kick and landing, clones don't have some of their effects show (ex. smash attack
  charging/release)"**:
  - Charging: his hold effects are his MSC's (`gk_sm_fx`, on him; the hold scripts loop: no clone script).
    - A split clone's hold command (action 4) now carries its own charge in the start frame's field (`gk_fpack`).
    - `weapons/clone.c` `cl_sm_fx` draws his hold effects on the clone (hold kinds 0x62 / 0x64 / 0x67, from frame 0):
      every 5 of its charge the dust / sparkle at 1, every 10 the sword at `1 + 4 x charge / 120`. Its hand is 0x7E8,
      as its scripts'. Nothing while the charge doesn't change.
  - Release: an automatic / chained split smash restarted its start motion at the hold frame (`gk_fsms`), which
    skipped the scripts' hold-frame swords and fire. It now plays on from 0.
  - Audit (`gekkouga_build.py` `effect_jump`): every split kind plays the same clone script as formation. His scripts
    that only JUMP to another (the double jumps, the aerials' landings: 15) had no clone script in either mode; they
    now get the target's.
  - Still none: Walk / Run dust (loops).
- **"clones will sometimes despawn early when using down special"** (the user couldn't reproduce it):
  - No behaviour change for it.
  - Every removal now has its own reason in VAR_23 (A_release's S4GF `gen=`):
    - 100 + id heartbeat lost and 400 + id fell off, both + 1000 x the clone's last place (`gk_why_at`: X/10 + 40 + 81
      x (Y/10 + 40));
    - 200 + id hit;
    - 300 + id the timer;
    - 500 his KO / rebirth status;
    - 600 a battle reset.
  - The periodic diag line no longer overwrites a reason written that frame (slot 61).
  - Found offline: a kick 30 from a 60-wide stage's edge left a split clone past the edge; it fell and was gone (401 /
    402). An off-stage float-back was offered, not done.
- Tests: `gekkouga_clones_test` (see the report's counts); `clonefix_v3_tests`, `split_tests`, `clone_free_tests`,
  `clone_articles_tests`, `clone_fx_tests`. Not confirmed in game.

## Freeze fix v1 (`greninja_freeze_fix_v1.zip`, over clone fixes v3; data only, exe_v46z_gkb11)

The user: clone fixes v3's files froze the game at Greninja's load (gkb11's A_release had loaded clone articles v1's
data fine).
- **Cause:**
  - Every opcode of v3's three MSCs was compared with the game's own Greninja MSCs (his, shuriken, moon) and clone
    articles v1's. The only new one is 0x19 (bitXor), once, in his `gekkouga_frame`: v3's diag line
    `flags = flags ^ (gk_vi(62) * 1048576)`, run every frame from his load.
  - No shipped MSC uses bitXor. Most likely the game's interpreter doesn't take it; the game's code for it was not
    read.
- **Fix:** the flip by `+` / `-` on `flags & 1048576`.
- **Guard:** `gekkouga_clones_test.msc_ops_tests` checks every built MSC's opcodes against `MSC_GAME_OPS` (the
  game's own Greninja MSCs and clone articles v1's). docs/native-notes.md.
- **TEST_ONLY_DATA** `revert_1` - `revert_4`: each of v3's four files as before v3 (his MSC, the clone's effect.bin,
  the clone's MSC, the shuriken's MSC), to swap one at a time if the freeze stays.
- Not confirmed in game.

## Round gauge v1.1 (`greninja_round_gauge_v1_1.zip`, over freeze fix v1; exe_v46z_gkb12)

The user (v1 in game, screenshot `$S/gk_in/clone_fx/round_gauge_ingame.webp`): "far too small. It should be about the
size of the fighter emblem (pokeball), slightly smaller. Also it's appearing on fighters other than Greninja".
- **Size / place** (`tools/gekkouga_gauge_flx.py` `build(v11=True)`, `emblem_places`):
  - centred on each panel sprite's `mark_mc` (the series emblem: a 254 px quad x its scale), its whole cell
    `GAUGE_EMBLEM` 0.87 of it: panels 3 / 4 x 0.561 (144 of 165 px), 1 x 0.420, 2 x 0.453;
  - drawn right above the emblem (depth + 1; every other part of panels 1 - 4 one depth up, `raise_above`, their places
    theirs only), under the percent, the portrait and the rest.
- **Greninja only:**
  - v1's clip was visible in the shared panel layout, and only Greninja's panel was driven by the exe (`gk_panel`), so
    every panel showed it.
  - Now it is placed with alpha 0. The exe's colour (alpha 100) and visibility show it on his panel only, when his
    VAR_19 has a mode.
- **Colour** (exe feature `gauge2`, `GAUGE_COLOURS2`): the charge (mode 1) cyan (25 / 90 / 100; was "as is": white).
  The diag's S4GB line adds `gauge clip=%08X` (0: not found, the KO meter's way).
- Previews: `$S/gk_preview/round_gauge_v1_1_panels.png` (without / with the gauge, per layout; the emblem is a run-time
  picture: the grey box).
- Tests:
  - `gauge_tests(v11)`: rebuilt byte for byte; centre / scale / alpha 0 per panel; depths;
  - v1's flx still rebuilds byte for byte with `v11=False`;
  - the cave test's colour check, by feature;
  - gkb11 rebuilds byte for byte without `gauge2`.
- **The charge's invulnerability** (the user: "please remove the invulnerability from the charge"):
  - His vl group 1 gives SpecialLw / SpecialAirLw (motions 0x271 / 0x289) the intangible window 8 - 19. The fighter
    update sets intangible when the frame crosses 8 and clears it when it crosses 19 (docs/native-notes.md "The motion's
    intangible window").
  - The charge holds the motion at frame 14 (`gk_lw_hold_frame`), so from frame 8 he was intangible for the whole
    charge.
  - Fix: `tools/gekkouga_build.py vl` (`VL_EDITS`) ships his vanilla `fighter_param_vl_gekkouga.bin` with those 4 bytes
    0 (new in the mod), and `gk_lw_main` / `gk_lw_loop` set `HitModule(0, 0)` every frame, as Core Breaker v11 does.
  - Nothing else in the stance makes him intangible: its scripts only toggle the counter flag 0x2100000D, and the
    counter shield (`func_2339`) is out of the loop since clones v1.
  - The regroup (0x160) plays frames 0 - 7.6 of the same motion (never reaches the window either way).
  - The aligned kick's motions (0x279 / 0x28D) keep their window 1 - 4 (the vanilla counter attack's): the user, "The
    kick having invincibility is fine".
  - Tests: `invuln_tests` (the vl bytes, only 4 changed; the stance's MSC over 40 held frames: `HitModule(0, 0)` each
    frame, nothing intangible, no shield).
- Not confirmed in game.
