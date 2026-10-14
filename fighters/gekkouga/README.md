# Greninja (`gekkouga`) MSC

`gekkouga.c` is Greninja's decompiled MSC with named syscalls. It has 62
globals and 2,414 functions.

## Build

```sh
./tools/setup_toolchain.sh
python3 tools/msclang/msclang.py -x tools/mscinfo.xml fighters/gekkouga/gekkouga.c -o gekkouga.mscsb
```

The unmodified file compiles, and decompiling the result gives back the same
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
