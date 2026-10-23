# Cemu patches: Smash 4 rollback netplay

Rollback netplay for Smash 4 runs in Cemu (docs/rollback-netplay.md). The Cemu changes are kept here
as patches against one pinned Cemu commit; you build Cemu yourself.

- Base: `cemu-project/Cemu` commit `29f2f1fae4631e2317977debd9eacd55cc28dd7d` (2026-10-22).
- Patches, applied in order:

| patch | what |
|---|---|
| `patches/0001-smash4-rollback-probe.patch` | Phase 1 probe: logs battle seeds, clock seeds, threads, time reads, heap creation, frame times and which memory a battle writes; can force the seeds |

## Build on Windows

Needs git and Visual Studio 2022 with "C++ CMake tools for Windows" and a Windows 10/11 SDK (Cemu's
BUILD.md).

```
git clone --recursive https://github.com/cemu-project/Cemu Cemu-smash4
cd Cemu-smash4
git checkout 29f2f1fae4631e2317977debd9eacd55cc28dd7d
git submodule update --init --recursive
git apply path\to\Smash4ModdingTests\cemu\patches\0001-smash4-rollback-probe.patch
```

Then open the `Cemu-smash4` folder in Visual Studio ("Open a local folder"), Project > Configure CMake
(the first time takes a long while: it builds the dependencies), choose the release configuration,
and Build All. The exe lands in `bin\`. It uses the same settings folder as your installed Cemu
(`%APPDATA%\Cemu`: game paths, keys, controllers, graphic packs) unless a folder named `portable`
sits next to the exe, in which case it keeps its own settings there.

Checked here: the patch applies to that commit, and the five files it changes compile (syntax check
against Cemu's headers with g++). A full build wasn't possible here (no room for the dependencies).

## Probe (0001): how to run it and what to send back

The probe turns itself on only when the game's code matches Smash 4's executable at its two hook
addresses (vanilla or the modpack's). It writes `smash4_probe.log` in Cemu's user folder (next to
`log.txt`: `%APPDATA%\Cemu`, or the `portable` folder). Set `CEMU_SMASH4_PROBE_OFF=1` to disable it.

1. Settings: CPU mode **Single-core recompiler** (Cemu's own game profile for the USA / EUR versions
   already sets it; set it by hand for the Japanese one).
2. Run the modpack, play two short matches in Training or Smash mode (one on Battlefield, one on the
   Minecraft stage if you can), leave to the menu, close Cemu.
3. Send me `smash4_probe.log` and `log.txt`.

Determinism check (optional, after that): start Cemu from a command prompt with a fixed seed,

```
set CEMU_SMASH4_SEED=0x12345678
set CEMU_SMASH4_CLOCKSEED=0x9ABCDEF0
Cemu.exe
```

and play the same CPU-vs-CPU match twice (same characters, stage, rules, no inputs once it starts).
With both seeds fixed, the logged `rng0` / `rng1` values should match line for line between the two
runs if the battle depends only on the seeds; where they part is where something else (time, threads,
loading) leaks in.

What the log shows:
- `battle seed 0x... (caller ...)`: each time the game seeds the battle RNG (instance 0), and the
  active threads at that moment (name, entry point, priority).
- `clock seed taken`: each time the game seeds from the clock (RNG instance 1, used by menus, our
  biome / monster picks).
- every 60 input reads: average / longest frame time, both RNG states, and the game's time reads by
  calling address.
- every 600 reads after a battle seed (`CEMU_SMASH4_HASH_EVERY`, 0 = off): which 64 KiB blocks of
  the 1 GiB MEM2 changed since the last sample. That's the memory a rollback snapshot has to cover.
  Each sample reads all of MEM2, so expect a short hitch every 10 s.
- `heap create`: the game's expanded heaps (start, size, caller).

## Updating the base

When moving to a newer Cemu: check out the new commit, `git apply --3way` each patch, fix conflicts,
regenerate the patch with `git diff`, update the commit above.
