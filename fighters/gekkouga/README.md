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
  him). They mirror his motions, not his inputs.
- Clone "hurtboxes" are capsules on his shield, not the article's: a hit is given to the nearest clone by the hitting
  object's position; a hit touching a clone and him meets the shape first (the clone takes it); the common shield
  spark shows. The cave-built group replaces his counter shape (his 5-shape pool: the guard's + 4).
- An article's hit doesn't give him hitlag; a clone in its hitlag catches back up with his frame.
- No hand / face part animations on the clones (only main.pac); no sound; no smash-charge effects on them.
- The name tag: the HUD cursor of his player number moved off screen (FAR = -100000) after the HUD placed it: assumes
  the HUD's player order is the fighter table's.
- The base kind's native code (bunshin) runs for the clone; its singleton's other methods are bunshin's.
