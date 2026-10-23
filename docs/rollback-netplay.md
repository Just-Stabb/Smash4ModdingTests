# Rollback netplay (Cemu only)

Goal: two-player rollback netplay for the modpack, in a patched Cemu (the user's choice; console
players can't join). Research behind it: `reports/Smash 4 modpack netcode upgrade.md`. Cemu patches
and build steps: `cemu/README.md`.

## Design (Slippi's, moved to Cemu)

Slippi does rollback for Melee by snapshotting **the game's own memory** (its static data and heap,
about 8 MB; no CPU, GPU or audio state) at a frame boundary the game signals, and re-running frames
from it with corrected inputs. Here:

1. **Same start.** Both sides load the match themselves (menus and loading aren't synced, so their
   timing can differ); the netplay layer forces the same battle seed, the same clock seed and the
   same match settings, then starts exchanging inputs at the battle's first frame.
2. **Inputs.** Each side sends its pad state per frame with a few frames of input delay; Cemu feeds
   the game the agreed inputs at its controller reads (`VPADRead`, `KPADReadEx`, `HPADRead`: each is
   called from one place in the game).
3. **Rollback.** At each frame boundary Cemu snapshots the battle's memory; when a remote input
   arrives that differs from the prediction, it restores the snapshot of that frame and re-runs the
   frames since then with rendering and sound skipped, then continues.
4. **Desync check.** Both sides hash the battle state every N frames and compare.
5. **Same files.** A hash of the modpack's gameplay files is exchanged before connecting.

## What the game gives us (cross_f.rpx: vanilla and the modpack's)

| thing | where | notes |
|---|---|---|
| RNG | `0x105759C0`: 4 x xorshift128 (16 bytes each) | instance 0 = the battle's, instance 1 = the clock-seeded one (menus, our biome / monster picks); `0x024F6BE8(n)` = instance 1 `% n`; the battle code steps instance 0 inline in hundreds of places |
| battle seed | `0x02D87E00(r4 = seed)`: `lis r3, 0x1057; addi r3, r3, 0x59C0; b 0x0337413C` | seeds instance 0 (`0x0337413C`: sead-style init with `0x6C078965`) and re-seeds instance 1 from the clock; called from 4 places (`0x0285BD8C`, `0x02FB82E4`, `0x02FDA3B8`, `0x02FF6A0C`: the match setups of the different modes) with the seed from the match settings |
| clock seed | `0x033740D8()` | `OSGetTime` -> calendar -> a seed; used by `0x0337413C` and by the instance 1 re-seed `0x0337436C` (called from 6 places) |
| controller reads | `VPADRead` at `0x03370884` (in `0x03370848`), `KPADReadEx` at `0x03371D84` (in `0x03371CF4`), `HPADRead` at `0x0345867C` (in `0x03458640`) | each function is a virtual method (vtables `0x10199C1C`, `0x10199C94`, `0x101A5B24`); in Cemu all three are host functions |
| threads | 13 `OSCreateThread` sites | named: `core0_scene_render`, `Audio output`, `MP4 TV Play`, `MP4 Manager`, `nus::AXInitThread`, `nus::DeviceUpdateThread`; 6 more named at run time |
| time | `OSGetTime` 36 call sites, `OSGetSystemTime` 17, `OSGetTick` 1; 821 inline `mftb` | in Cemu every one of these (and alarms, sleeps) reads `PPCInterpreter_getMainCoreCycleCounter()` = the host's clock |
| heaps | `MEMCreateExpHeapEx` 8 sites, `MEMAllocFromExpHeapEx` 62 | the battle's heap(s) to be found by the probe |
| other network | `nn_uds` (local wireless), `nsysnet`, `nlibcurl` imports | the game's own online (Pia) isn't used by this |

## What Cemu gives us (commit 29f2f1f)

- **Game hooks**: `GamePatch.cpp` already writes HLE opcodes (`(1 << 26) | index`) into some games'
  code at load; the recompiler ends a block at an HLE opcode and continues at whatever instruction
  pointer the host function leaves (next instruction, or LR). The probe hooks the battle seed and the
  clock seed this way; the frame-boundary and snapshot hooks will too.
- **Time**: one function, `PPCInterpreter_getMainCoreCycleCounter()`, is the source of all guest time
  (`mftb` in recompiled code calls `OSGetSystemTime`). A deterministic clock goes there.
- **Threads**: in single-core mode (Smash 4's default profile) all guest threads run on one host
  thread, switched by cycle counts, which makes a frame-boundary snapshot simpler.
- **Memory**: MEM2 is one committed 1 GiB block at guest `0x10000000` (`memory_base + addr`), so a
  snapshot is plain copies of guest ranges.
- **No savestates**, and nothing that skips GPU work; both are ours to add.

## Phases

| phase | what | status |
|---|---|---|
| 1 | Probe (`cemu/patches/0001`): seeds, threads, time reads, heaps, frame times, memory written during battle; seed overrides for a determinism test | written, compile-checked; needs a run on the user's PC |
| 2 | Determinism: forced seeds and settings at battle start; a battle-only deterministic clock if the probe shows battle code reading time; our clock-based caves (biome, monsters) take the netplay seed; same input recording, same result on two PCs | after the probe log |
| 3 | Snapshot / restore at the frame boundary: the ranges the probe finds, plus a sync test (run, restore, re-run, compare hashes); re-simulation with GPU and sound skipped; speed measured (how many frames re-run inside 16.7 ms) | |
| 4 | Netplay: 2 players, input exchange with delay + prediction + rollback (GekkoNet or a GGPO-style loop), direct IP / relay, desync hashes, file-hash check, a small UI | |

## Risks (known now)

- **Speed**: a rollback of k frames re-runs k game frames inside one; the probe's frame times show
  how much room Cemu leaves on the user's PC.
- **Threads touching battle state** (animation or effect workers) mid-frame would make a frame
  boundary snapshot inconsistent; the probe's thread list and memory map are the first check.
- **Streaming loads during a battle** (Final Smash models, stage parts) finish at host-dependent
  times; they have to be made to happen at the same frame on both sides, or excluded.
- **Floating point**: both sides run the same recompiler on x86-64, so results should match between
  PCs; to be confirmed by the phase 2 test.
