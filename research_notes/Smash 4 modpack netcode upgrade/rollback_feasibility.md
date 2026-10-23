# Rollback / improved-lockstep feasibility for Smash 4 (Wii U): RPX (code caves) vs Cemu vs console plugin

Scope note: sources were fetched 2026-10-23. Cemu source was read at commit `29f2f1fae4631e2317977debd9eacd55cc28dd7d` (2026-10-22) of github.com/cemu-project/Cemu; file links point to `main`. Local notes are the user's reverse-engineering docs in `/home/user/Smash4ModdingTests/docs`. Several sites (words.infil.net, dolphin-emu.org docs, GitHub wikis) could not be fetched from this environment; claims that would have come from them are listed as gaps.

## 1. Rollback fundamentals: requirements, GGPO design, how state size and re-simulation cost scale

### Takeaway
Rollback requires a fully deterministic simulation that can save, load and step one frame without rendering, all fast enough that loading a state and re-simulating N frames fits inside one 16.7 ms frame alongside the normal frame. Retrofitting rollback onto a finished commercial game is expensive: Mortal Kombat X took about 8 programmer-years, and Rivals of Aether gave up. The usual design pairs a small fixed input delay (2-3 frames) with rollback for anything later than that.

### Cited Findings
- GGPO's stated requirements: "The game simulation must be fully deterministic. That is, for any given game state and inputs, advancing the game state by exactly 1 frame must result in identical game states for all players." It also says "Your game engine must be able to load, save, and execute a single simulation frame without rendering the result of that frame." — [GGPO Developer Guide](https://github.com/pond3r/ggpo/blob/master/doc/DeveloperGuide.md)
- GGPO integrates through callbacks: `save_game_state(buffer, len, checksum, frame)`, `load_game_state(buffer, len)`, `advance_frame`, `free_buffer`. The application calls `ggpo_synchronize_inputs` every frame, rollback frames included. When that call returns non-OK, GGPO "has reached its internal prediction limit" and the game must not advance. — [GGPO Developer Guide](https://github.com/pond3r/ggpo/blob/master/doc/DeveloperGuide.md)
- GGPO on RNG: the RNG seed must be the same at frame 0 for both players, and "the state of the random number generator is included in your game state". On effects and sounds: they "need to be deferred until after the rollback is finished... most easily accomplished by separating your game state from your render state." — [GGPO Developer Guide](https://github.com/pond3r/ggpo/blob/master/doc/DeveloperGuide.md)
- GGPO has a "sync test" session that "will execute a 1 frame rollback for every frame of your game" and compares the states (via checksum) to find non-determinism. This is the standard tool for desync detection during development. — [GGPO Developer Guide](https://github.com/pond3r/ggpo/blob/master/doc/DeveloperGuide.md)
- GGPO's guidance on input delay: "for this type of game [fighting], any frame delay larger than 1 can be noticed by most intermediate players". When the frame delay is shorter than the transmit time, rollbacks are about (transmit frames − delay frames) long, e.g. 4 − 1 = 3. — [GGPO Developer Guide](https://github.com/pond3r/ggpo/blob/master/doc/DeveloperGuide.md)
- On re-simulation cost, the Ars article says the game must "re-simulate all these frames back to the present (and then also serialize all of them!)" within one frame. MKX took an average of 10 ms of its 16 ms budget under delay-based netcode, and a "naive rollback solution" more than tripled that to 32 ms per frame. A developer quoted: "That thing you could have done in 16ms... now needs to fit into 1ms if you want to simulate it 10 times in a single frame." — [Ars Technica, "Explaining how fighting games use delay-based and rollback netcode" (2019)](https://arstechnica.com/gaming/2019/10/explaining-how-fighting-games-use-delay-based-and-rollback-netcode/)
- Retrofit cost, from the same article: rollback in Mortal Kombat X "took approximately eight man-years of time split between many programmers over 10 months". Rivals of Aether's studio explored converting a finished game "but eventually had to move on when it was proving too costly". Skullgirls added GGPO "in about two weeks early in development using his custom engine". — [Ars Technica](https://arstechnica.com/gaming/2019/10/explaining-how-fighting-games-use-delay-based-and-rollback-netcode/)
- Killer Instinct "always adds three frames of delay. It gives us 45ms... pings can be 90ms before you start having any rollbacks occurring at all", and 150 ms ping is playable "with just a couple frames of rollback". Before rollback, MKX's delay-based netcode "would fluctuate between five and 20 frames of delay". — [Ars Technica](https://arstechnica.com/gaming/2019/10/explaining-how-fighting-games-use-delay-based-and-rollback-netcode/)
- Both rollback and delay-based netcode need frame-advantage or time sync. Otherwise the player who is ahead gets repeated one-sided rollbacks. The usual fix is to "briefly pause the player who is ahead for one or two frames". — [Ars Technica](https://arstechnica.com/gaming/2019/10/explaining-how-fighting-games-use-delay-based-and-rollback-netcode/)
- Object create/destroy, particles and audio are the classic retrofit problems. Projectiles are often kept alive for extra frames so a rollback can "un-destroy" them, and Street Fighter x Tekken shipped with "horrific sound bugs" from rollback. — [Ars Technica](https://arstechnica.com/gaming/2019/10/explaining-how-fighting-games-use-delay-based-and-rollback-netcode/)
- Melee precedent: Slippi's rollback does not use full Dolphin savestates. `SlippiSavestate` copies four guest-RAM ranges every save: `0x80005520-0x80005940`, `0x803B7240-0x804DEC00` (data and BSS), `0x8065C000-0x8071B000`, and the main heap (bounds read at run time from `0x804D76B8` / `0x804D76BC`, default `0x80BD5C40-0x811AD5A0`). It excludes sound-related and XFB/VI blocks. Computed from those constants, the default ranges total about 7.74 MiB. — [Slippi Ishiiruka `SlippiSavestate.cpp`](https://github.com/project-slippi/Ishiiruka/blob/slippi/Source/Core/Core/Slippi/SlippiSavestate.cpp)
- A Dolphin developer, quoted in a forum thread, explains why generic emulator savestates are slow for rollback: they store "the entire state of the emulated GameCube/Wii, not just things like the positions and states of characters and projectiles". A forum user reports that Dolphin flushes the JIT cache on save. — [Dolphin forums, "rollback netcode"](https://forums.dolphin-emu.org/Thread-rollback-netcode) (forum, secondhand)

### Inferences
- Cost model (estimate): per displayed frame, worst case = load(S) + N × step_without_render + N × save(S) + 1 normal frame. With S as a plain memcpy at about 10 GB/s single-threaded on a desktop (an assumed figure, not sourced):
  - 8 MiB (Melee/Slippi-sized) ≈ 0.8 ms per save or load;
  - 64 MiB ≈ 6-7 ms;
  - 1 GiB ≈ 100 ms.

  So emulator-level rollback over the whole 1 GiB of MEM2 is impossible per frame. Only a game-aware subset (Slippi-style), or dirty-page or delta tracking, can fit.
- The Slippi design is the template for an emulator-assisted, game-aware rollback: the emulator does the memory copy, and game knowledge decides which regions to copy and which to exclude (sound, framebuffers). It shows a known fighting game's battle state can be captured as a few MB of guest RAM. GameCube main RAM is 24 MB, a general hardware fact not separately sourced here, so Slippi copies roughly a third of it.

### Gaps
- Infil's netcode article (words.infil.net) and Tony Cannon's Game Developer Magazine article could not be fetched (connection reset), so their figures are not included.
- No authoritative Slippi write-up was fetched that gives per-frame save/load time or the maximum rollback window. Slippi's in-game Melee ASM changes (as opposed to its Dolphin-side code) were not examined.

## 2. Emulator-level rollback inside Cemu (whole-machine or game-aware save/restore)

### Takeaway
Cemu has no savestate system at all, official or merged: no serialization of PPC, MMU, GPU or HLE-OS state. Its memory map reserves 1 GiB of MEM2 plus 32 MiB of MEM1 and several other areas, so full-machine per-frame snapshots are out of reach. The parts that make rollback hard are all non-deterministic:
- guest time is derived from the host TSC (RDTSC);
- the GPU runs on its own host thread, and pipelines compile asynchronously;
- HLE OS objects (threads, alarms, sockets, file handles, GX2 and audio state) live in host C++ structures, not only in guest RAM.

The only plausible Cemu route is Slippi-style: snapshot the guest-RAM ranges that hold Smash 4's battle state, and leave the emulator and OS state alone.

### Cited Findings
- No save-state PRs in mainline: a GitHub search of cemu-project/Cemu PRs for "savestate" returned 0 open and 0 closed. — [Cemu PR search](https://github.com/cemu-project/Cemu/pulls?q=is%3Apr+savestate)
- A grep of the current Cemu source for `savestate|save_state|SaveState` matches only the graphic-packs window (unrelated). — [Cemu source tree](https://github.com/cemu-project/Cemu/tree/main/src) (local clone, commit 29f2f1f)
- Cemu's old bug tracker closed the save/load-state request (#161, 2019). The closing comment: "save states arnt feasible on newer generation emulators including Wii U... Games on Cemu regularly use over 2gb of ram and some up to or over 8gb of ram." This was a tracker moderator, not necessarily a developer, and the RAM figures are host-process usage, not guest RAM. — [Cemu bug tracker #161](https://bugs.cemu.info/issues/161)
- A search-engine summary says a cemu-libretro fork's README lists save states as unsupported because Cemu has no serialization of PPC/MMU/GPU/HLE state. I could not open the page to verify. — [RetroArch issue #14416 (Cemu core request)](https://github.com/libretro/RetroArch/issues/14416) (unverified)
- Wii U hardware: Espresso CPU, 3 cores at 1243.125 MHz; Latte GPU at 549.999 MHz; 32 MB MEM1; 2 GB MEM2 "with 1 GB reserved for the operating system and unavailable to games"; 12.8 GB/s total DDR3 bandwidth. — [WiiUBrew: Hardware](https://wiiubrew.org/wiki/Hardware)
- Cemu's guest address map (`MMU.cpp`):
  - MEM2 at `0x10000000`, size `0x40000000` ("main memory area (1GB)");
  - MEM1 at `0xF4000000`, 32 MiB;
  - FGBUCKET 64 MiB;
  - optional OVERLAY_AREA 448 MiB;
  - TEXT_AREA for module code, up to 224 MiB;
  - a 4 MiB CODECAVE at `0x01800000`;
  - a 32 MiB Cemu-private area;
  - three 20 KiB locked-cache areas, one per core.

  — [Cemu `src/Cafe/HW/MMU/MMU.cpp`](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/HW/MMU/MMU.cpp)
- Cemu CPU modes: `SinglecoreInterpreter`, `SinglecoreRecompiler`, `DualcoreRecompiler` ("deprecated and not used anymore"), `MulticoreRecompiler`, `Auto`. — [Cemu `src/config/CemuConfig.h`](https://github.com/cemu-project/Cemu/blob/main/src/config/CemuConfig.h)
- **Smash 4 is pinned to single-core:** Cemu's bundled default game profiles for all three regions (`0005000010144F00` USA, `0005000010145000` EUR, `0005000010110E00` JPN) set `cpuMode = Singlecore-Recompiler` and `streamoutBufferCacheSize = 48`. — [Cemu `bin/gameProfiles/default/0005000010144f00.ini`](https://github.com/cemu-project/Cemu/blob/main/bin/gameProfiles/default/0005000010144f00.ini)
- Guest time comes from the host clock. `coreinit_GetMFTB()` returns `PPCInterpreter_getMainCoreCycleCounter() / 20` ("bus clock is 1/5th of core clock, timer clock is 1/4th of bus clock"). `PPCInterpreter_getMainCoreCycleCounter()` returns `PPCTimer_getFromRDTSC()`, which scales host `__rdtsc()` deltas to `CORE_CLOCK = 1243125000`. `OSGetTime`, `OSGetSystemTime` and `OSGetTick` all derive from this. — [Cemu `coreinit_Time.cpp`](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/OS/libs/coreinit/coreinit_Time.cpp), [`PPCTimer.cpp`](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/HW/Espresso/PPCTimer.cpp), [`PPCInterpreterMain.cpp`](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/HW/Espresso/Interpreter/PPCInterpreterMain.cpp)
- Guest thread scheduling counts emulated cycles, not host time. The default quantum is `kThreadQuantumDefault = 45000` cycles. Each timeslice adds a "slight randomized variance" of 0-127 cycles from a per-core Lehmer LCG seeded with 12345, added to avoid lock live-locks seen in Mario Party 10. The LCG is itself deterministic. — [Cemu `coreinit_Thread.cpp` (`__OSThreadStartTimeslice`)](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/OS/libs/coreinit/coreinit_Thread.cpp), [`GameProfile.h`](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/GameProfile/GameProfile.h)
- The GPU runs on its own host thread: `sLatteThread = std::thread(Latte_ThreadEntry)`. `GX2GetSwapStatus` reports flip request and execute counts from the GPU's shared area. — [Cemu `LatteThread.cpp`](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/HW/Latte/Core/LatteThread.cpp), [`GX2_Misc.cpp`](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/OS/libs/gx2/GX2_Misc.cpp)
- Async shader/pipeline compilation is on by default (`ConfigValue<bool> async_compile{ true }`). — [Cemu `CemuConfig.h`](https://github.com/cemu-project/Cemu/blob/main/src/config/CemuConfig.h)
- Dolphin, by contrast, has an emulated "fake timebase". Netplay clients send it every 60 frames (`SendTimeBase()`, `GetFakeTimeBase()`), and a mismatch produces `DesyncDetected` "Player {} desynced!". — [Dolphin `NetPlayClient.cpp`](https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/Core/NetPlayClient.cpp)

### Inferences
- **Whole-machine snapshots are infeasible:**
  - Guest RAM alone could be up to 1 GiB MEM2 + 32 MiB MEM1 + 64 MiB FG bucket (about 100 ms per copy at 10 GB/s, an estimate).
  - Cemu would also need serializers for every HLE module (coreinit threads, mutexes, alarms, FS, sockets, GX2, snd_core, VPAD/KPAD) and for the Latte GPU and Vulkan resource state. None of these exist.
  - The PPC recompiler's code cache stays valid across a restore only if code memory doesn't change, which holds for a fixed RPX plus static caves.
- **The game-aware subset route is plausible but unmeasured.** A Cemu patch would `memcpy` selected guest ranges (Smash 4's battle heap(s) and .data/.bss) into a ring buffer each frame, at a hook point at the top of the game's per-frame update. The guest-to-host mapping is a flat base pointer per range, so the copy itself is cheap.
- **Dirty-page tracking** (write-protecting host pages with mprotect/VirtualProtect, or diffing against the last snapshot) could cut per-frame copies to the pages the battle actually touches. Two cautions:
  - this would need cooperation with the recompiler's fast-memory access path (not examined);
  - page faults on every first write per frame cost time.
- **Single-core helps determinism.** All three guest cores are interleaved on one host thread with cycle-based quanta, so CPU-side interleaving is reproducible to the extent that events don't depend on host time. The remaining non-determinism is anything the game reads from `OSGetTime`/`OSGetTick`/`mftb`, plus OS alarms and timers firing at host-time-dependent points.
  - The guest timer reads host RDTSC, so two Cemu instances, or one instance re-running frames, will see different times.
  - Per local notes, Smash's second RNG instance is seeded from the clock (see §3). A lockstep or rollback Cemu would need a virtual timebase (cycle-counted like Dolphin's, or frozen per game frame).
  - The GPU thread and async shader compiles only affect timing (frame drops), not game logic, as long as the game logic never reads GPU results back. That is unverified for Smash 4.
- **Re-simulation speed is the second blocker.** Smash 4 already needs a single host thread to emulate three PPC cores. N-frame re-simulation needs that thread to run N+1 game frames per 16.7 ms, while skipping or deferring GPU command execution and audio during resim frames. Cemu can't separate "game logic" from "render submission" in guest code; it would have to drop GX2 command submission during resim, which is game-specific.

### Gaps
- No Cemu fork with working savestates was found. Forks may exist that this search missed: the GitHub search API was blocked, and only the mainline PR page was checked.
- Smash 4's actual MEM2/MEM1 footprint and its battle-heap layout (how many heaps, which addresses, and whether fighters, articles and items come from a dedicated battle heap) are not documented in the local notes beyond the allocator entry points. Measuring this in Cemu is the first experiment.
- Whether Smash 4's battle code reads `OSGetTime`/`mftb` anywhere (other than seeding the clock RNG) is unknown.
- Cemu's per-frame cost for Smash 4 on typical hardware (host ms per guest frame) was not found, so the resim headroom is unquantified.

## 3. Game-level rollback inside Smash 4 (cross_f.rpx); is the game deterministic?

### Takeaway
Smash 4 is input-deterministic on a given version and build, which is the precondition for both lockstep and rollback:
- replays store only inputs, the random seed and the rules, and CPU players are re-simulated rather than recorded;
- the online mode is lockstep.

Game-level rollback inside the RPX is still the hardest route:
- the battle state spans fighters with dozens of modules, ACMD/MSC interpreter state, weapons/articles, items, stage objects, the RNG, the camera, effects (ptcl/eft) and sound;
- all of it lives in heap-allocated C++ objects with pointers, so it can't be serialized field by field from code caves;
- the Wii U's 1.24 GHz Espresso has to re-simulate several frames per frame.

The realistic in-game variant is Slippi-style: snapshot whole heap regions plus .data/.bss, exclude sound and render buffers, and treat effects and sound as cosmetic.

### Cited Findings
- Smash 4 replays: "each human player's input data, the match's random seed, and the general rules are saved, so when a replay is watched, the game actually regenerates the match from this data." Replays of earlier versions "may become desynced due to gameplay changes", so older replays become unviewable. — [SmashWiki: Replay](https://www.ssbwiki.com/Replay)
- "Replays do not save the input data from CPU players; instead, each CPU player simply replays the match from scratch, which due to the AI's actions being influenced by RNG, results in them reacting to everything the exact same way as long as the RNG seed is the same." — [SmashWiki: Replay](https://www.ssbwiki.com/Replay)
- Replay length is about 10 minutes in Smash 4. Wii U replays are named `rd000.bin`-`rdfff.bin` (cap 4,096). — [SmashWiki: Replay](https://www.ssbwiki.com/Replay)
- Asynchronous loading breaks timing in replays: "If a character or other element is loaded during a match faster than expected (such as because of pausing or online lag), then the replay of that match will 'freeze' and finish loading the element before it can continue." Replays can also randomly desync and play correctly on a later try, cause unknown. — [SmashWiki: Replay](https://www.ssbwiki.com/Replay)
- Online desync handling: when a console loads data (e.g. a Final Smash after opening a Smash Ball) it tells the other consoles. If they disagree, "After around 10 seconds, both ends acknowledge that a desynch has occured, and all players are disconnected." Also: "In Super Smash Bros. for Wii U and Ultimate, the player using a hack is instantly disconnected from the match upon using a move that could desynchronize the game." The Smash series "has historically used a 'delay-based' netcode". — [SmashWiki: Online desynchronization](https://www.ssbwiki.com/Online_desynchronization)
- Moveset and physics hacks that not all players share are "nearly guaranteed to desynch"; players with identical hacks "generally do not cause a desynch". — [SmashWiki: Online desynchronization](https://www.ssbwiki.com/Online_desynchronization)
- Local RE notes on the RNG: the game's RNG is xorshift128 ×4 at `0x105759C0`. Instance 0 is the battle's, "seeded per match, replays / online". Instance 1 is "seeded from the clock", accessed through `0x024F6BE8(n)` = x % n. — [docs/minecraft-world.md, lines ~740-741](/home/user/Smash4ModdingTests/docs/minecraft-world.md)
  - Kirby's copy-loss roll uses this RNG (`0x105759C0`) `% 100`. — [docs/native-notes.md, ~line 186](/home/user/Smash4ModdingTests/docs/native-notes.md)
  - One note gives the RNG as `0x105659C0` (a projectile's random angle spread). That is probably a typo for `0x105759C0`; unverified. — [docs/native-notes.md, ~line 103](/home/user/Smash4ModdingTests/docs/native-notes.md)
- The modpack's own caves use the clock RNG and time base: the biome pick ("no L: random (the time base)") and the monster roll ("on the clock RNG"). The notes flag "online / replays (a clock pick isn't synced)". — [docs/minecraft-world.md, ~lines 768-784](/home/user/Smash4ModdingTests/docs/minecraft-world.md)
- Inputs are applied deterministically at the input layer: the Smash-button / Stick Smash setting "is applied to the inputs themselves (where the game applies Tap Jump and A+B), so replays play back as played." — [docs/controls.md, ~line 39](/home/user/Smash4ModdingTests/docs/controls.md)
- Per-frame object stepping (local notes):
  - ACMD object step entries: fighters `0x02E408B8`, weapons `0x02BAD64C`, items(?) `0x03048064`. They "run every unpaused frame".
  - The interpreter keeps a 0x38-byte state per script (`0x02BEE950`), including a nested CALL state that is freed separately.
  - ACMD `Thread_Start` supports "up to 32 threads at once, across all objects".

  — [docs/native-notes.md, ~lines 1212-1222](/home/user/Smash4ModdingTests/docs/native-notes.md), [docs/acmd-extra-commands.md, ~lines 115-157](/home/user/Smash4ModdingTests/docs/acmd-extra-commands.md)
- Allocation and objects (local notes):
  - `operator new` is `0x03374578(size)`, `operator delete` is `0x0337460C`, heap alloc is `0x03374530`.
  - `BattleObject`: +4 kind, +0xC module accessor, +0x1E state byte.
  - The FighterParamManager (`[0x102FF448]`, fixed-size `0x25B0` allocation) is constant data during a battle.

  — [docs/native-notes.md, ~lines 1235-1242](/home/user/Smash4ModdingTests/docs/native-notes.md), [docs/kind-expansion-ram.md](/home/user/Smash4ModdingTests/docs/kind-expansion-ram.md)
- Scene system (local notes): scenes are registered by name with factories (table `0x100CBD90`), changed through the scene manager `0x033B9F18`, and modes are launched by the root sequence controller's launcher `0x02C881D4`. — [docs/boot-training.md](/home/user/Smash4ModdingTests/docs/boot-training.md)
- The Ars article's general retrofit warnings apply here: MKX's 8 programmer-years; object destruction and re-creation; particles and audio. — [Ars Technica](https://arstechnica.com/gaming/2019/10/explaining-how-fighting-games-use-delay-based-and-rollback-netcode/)

### Inferences
- **Determinism:** the replay design (inputs + seed + rules; CPU AI re-simulated from the seed) means the battle simulation is a pure function of inputs, the battle RNG seed and the rules on one version. Lockstep online implies the same across consoles. Two caveats:
  - the random replay desyncs and the "freeze while loading" behaviour show that asset streaming is asynchronous and gated (the simulation waits for the load), not part of the simulated state;
  - it is unknown whether the battle depends on GPU readbacks or on the clock RNG. Cosmetic code presumably uses instance 1.
- **What a snapshot must include (estimate of scope):**
  - every live `BattleObject` (fighters, weapons/articles, items, enemies/assist trophies, stage gimmicks) with all module objects behind the module accessor: status, motion, kinetic/physics, attack/hit/hurt, work variables, link, ground/collision, shield, damage, stop/hitlag, camera targets;
  - ACMD agents' interpreter state, including nested CALL states that are separately heap-allocated, and the global 32-entry thread pool;
  - MSC script VM state (stack, locals, globals);
  - the RNG (16 words at `0x105759C0`);
  - the battle manager, timer, stock and score;
  - stage object state, including moving collision and LVD-derived data;
  - item spawner state;
  - the camera, if any gameplay depends on it (e.g. blast zones and camera-following stages);
  - the pad manager's per-slot histories (`0x1057581C`), since the 10-frame buffer and smash-input detection depend on previous frames.

  Effects (ptcl/eft emitters), sound voices and render-side model state are cosmetic. A rollback can let them diverge or rebuild them, but the game spawns effects from ACMD, so resim frames would spawn duplicates unless effect and sound calls are suppressed during resim.
- **Why field-by-field serialization from caves is impractical:** state is spread across hundreds of heap objects linked by raw pointers, with allocation and free events every frame (projectiles, effects, ACMD nested states). The only tractable in-RPX design is to snapshot whole memory ranges:
  - give the battle a dedicated, fixed-address arena (hook `operator new` / heap alloc during a battle scene);
  - copy that arena plus the game's .data/.bss every frame;
  - copy it back on rollback. Pointers stay valid because addresses don't change.

  This is exactly Slippi's approach (main heap + data/BSS minus sound regions). Two complications:
  - the battle must not hold live pointers into memory outside the arena that change per frame (sound, effect and GPU buffers), or those must be excluded and their handles re-validated;
  - resource loads mid-match (Final Smash, Pokémon Trainer swaps, items) allocate during the battle and would need to be pinned or preloaded.
- **Console performance (estimate):** an in-RPX rollback on real hardware needs the Espresso (1.24 GHz, 3 cores) to run the battle logic several times per frame. The simulation share of Smash 4's frame time is unknown. Eight-player Smash exists on Wii U, which suggests 2-player battle logic is a fraction of the budget, but that is not evidence of 3-5x headroom. Copying even 16 MiB per frame on the Wii U's 12.8 GB/s DDR3 would cost a few ms (estimate), so any in-RPX rollback must keep snapshots small.
- **Cemu-hosted game-aware rollback is the most tractable variant:** Cemu supplies fast memcpy, plenty of host RAM for a ring buffer, and an external netcode library (e.g. GGPO-style) in C++. Game knowledge from the RPX notes defines which ranges to save and where the frame boundary hook goes. The RPX side would add caves for:
  - a "frame boundary" marker;
  - a "resim mode" flag that suppresses effects, sound and render;
  - a fixed battle arena.
- **Modpack implication:** every mod cave that uses the clock RNG or time base (biome pick, monster roll) is a desync source under any lockstep or rollback scheme. Such caves must switch to battle RNG instance 0, or to a seed derived from the match seed, and inputs must be read only through the synced pad path.

### Gaps
- No local note documents Smash 4's main game loop or frame boundary (which function steps all battle objects once per frame), the battle heap's address and size, the MSC VM's state layout, or how the effect and sound systems hold references to battle objects.
- Whether the battle simulation runs on one guest thread or is split across Espresso cores is not documented locally or found online. It matters for determinism under multi-core emulation, though Cemu pins Smash 4 to single-core anyway.
- I found no public prior attempt at rollback for Smash 4 or Smash Ultimate (game-level or emulator-level).

## 4. Improved delay-based lockstep: what can be tuned, realistic gains, how to hook Smash 4's PIA-based sync

### Takeaway
Smash 4 online is delay-based lockstep over Nintendo's PIA P2P library (UDP mesh, host, NAT traversal via the NEX game server). Offline input-to-action latency is already about 7 frames (SmashWiki), and no reliable measurement of the extra online delay was found. Realistic lockstep gains:
- a fixed, minimal input delay chosen from measured RTT, instead of an adaptive or inflated one;
- direct or relayed UDP with port forwarding;
- frame-pacing and time-sync fixes.

These can cut a few frames and reduce stutter, but cannot hide RTT the way rollback does: one-way latency must fit inside the delay window. The most promising hook is the pad manager's network slots (17-24), not PIA itself.

### Cited Findings
- PIA is "Nintendo's networking library that provides a framework to set up and maintain peer-to-peer connections". "All peer-to-peer packets are sent through UDP." Network types: NEX (matchmaking by game servers, "often requires NAT traversal"), LDN and LAN. A group of consoles is a "mesh" with a single host that handles joins; host migration picks a new host. — [Pretendo Nintendo Wiki: PIA](https://nintendo-wiki.pretendo.network/docs/pia)
- PIA protocols available to games: Unreliable, Reliable, Broadcast Reliable, Stream Broadcast Reliable, Clone, Sync, and Session management. NAT traversal: `RequestProbeInitiation(Ext)` on the NEX game server, then direct probe request/reply. — [Pretendo Nintendo Wiki: PIA](https://nintendo-wiki.pretendo.network/docs/pia)
- The PIA Sync protocol's message types:
  - `0x01` Start, `0x02` End, `0x03` Start end, `0x04` End alone;
  - acks `0x11`-`0x14`;
  - `0x21` "Data message (raw)", `0x22` "Data message (compressed)".

  — [Pretendo Nintendo Wiki: PIA Sync protocol](https://nintendo-wiki.pretendo.network/docs/pia/protocols/sync)
- PIA packet format:
  - magic `32 AB 98 64`;
  - header with connection id, packet id and source/destination timers;
  - in old versions, messages encrypted with AES-ECB under the session key, with an HMAC-MD5 of the whole packet appended; later versions use AES-GCM.
  - The version table lists PIA 5.11+ header versions 3, 4, 5...

  — [Pretendo Nintendo Wiki: PIA packet format](https://nintendo-wiki.pretendo.network/docs/pia/protocol)
- Smash 4 frame delay: "In Super Smash Bros 4, seven frames of delay between pressing the button and the game actually outputting the respective action are always present, regardless of gameplay mode". For Ultimate, "at least 4 frames of delay are present in online matches". — [SmashWiki: Frame delay](https://www.ssbwiki.com/Frame_delay)
- SmashWiki's Input lag page gives a different decomposition: "3 frames for Smash 4 on the Wii U" of input lag, with "About one additional frame of display lag". — [SmashWiki: Input lag](https://www.ssbwiki.com/Input_lag) (conflicts in definition with the 7-frame figure above; both are community wiki claims)
- Delay-based netcode pauses both games "until a player's given input is communicated to and confirmed", "usually combined with an artificial delay of a couple frames". "Smash 4 and Ultimate make the delay persist into offline modes." — [SmashWiki: Online desynchronization](https://www.ssbwiki.com/Online_desynchronization)
- Dynamic delay tends to "change too late to avoid having a few game pauses" and keeps delay "inflated for longer than is needed". Time sync between peers is needed regardless of netcode type. — [Ars Technica](https://arstechnica.com/gaming/2019/10/explaining-how-fighting-games-use-delay-based-and-rollback-netcode/)
- Local notes on the pad manager slot array `0x1057581C`: 26 wrappers. Slot 0 is the GamePad, 1 a dummy, 2-8 Wii Remotes/Pro, 9-16 the GameCube adapter, **17-24 "3DS / network"**. Wrapper `+8` is the status: held buttons in the game's own layout, stick X/Y floats at `+8`/`+0xC`, pressed at `+0x68`, pad type at `+0x7C`, valid-this-frame at `+0x87`. All are "polled every frame, also while loading". — [docs/minecraft-world.md, ~lines 728-736](/home/user/Smash4ModdingTests/docs/minecraft-world.md)
- Nintendo Network ended April 8, 2024. Pretendo (a private server) keeps Smash 4 online alive, and "emulators like Cemu also support online play for Super Smash Bros. for Wii U". — [SmashWiki: Nintendo Network](https://www.ssbwiki.com/Nintendo_Network)
- A search summary of Wikipedia says Smash for Wii U became publicly available on Pretendo in January 2025 (not opened directly). — [Wikipedia: Pretendo Network](https://en.wikipedia.org/wiki/Pretendo_Network) (secondhand)
- Precedent for patching PIA ports: Pretendo's Inkay plugin applies a "P2P port override for better connection stability (if you port forward)" for Mario Kart 8, Minecraft: Wii U Edition and Splatoon, plus modpack-specific MK8 matchmaking "by simulating extra DLC". Smash is not listed. — [PretendoNetwork/Inkay](https://github.com/PretendoNetwork/Inkay)

### Inferences
- **Hook point:**
  - Remote players' inputs appear in the pad manager's network slots (17-24) as ordinary pad wrappers. So a replacement lockstep can leave PIA's mesh and session code alone and replace only how those wrappers are filled: from a custom UDP transport (a direct socket via `nsysnet`/`nn::socket` imports), keyed by frame number.
  - The local player's frame-N input is captured, sent, and both consoles advance frame N only when all inputs for N are present: classic lockstep with an explicit frame number.
  - Whether Smash 4 uses PIA's Sync protocol or the Unreliable protocol for its per-frame input exchange is unknown. Finding the PIA send/receive call sites in `cross_f.rpx` (PIA is statically linked into the game, by inference) is the RE step.
- **Tunables, roughly by expected gain:**
  1. fixed input delay = ceil(one-way latency / 16.7 ms) + 1 instead of the game's adaptive buffer (gain depends on how conservative the stock buffer is, which is unmeasured);
  2. direct P2P with port forwarding, or a low-latency relay when NAT traversal fails;
  3. a time-sync handshake that keeps both consoles on the same frame, which removes one-sided stalls;
  4. sending each input packet with the last K frames' inputs (redundancy) so a single lost UDP packet doesn't stall;
  5. wired LAN/Ethernet adapters (the Wii U's Wi-Fi is 802.11b/g/n per WiiUBrew).
- **Realistic ceiling:** under lockstep, the delay can never be lower than the one-way network latency in frames (about 1 frame per 16.7 ms of one-way latency) without stalls. Cutting from the stock online buffer to the minimum gives maybe 1-4 frames at regional pings (estimate; the stock online buffer is unmeasured). The offline 7-frame base latency is untouched.
- **Mod compatibility:** custom lockstep between modded clients is fine if all peers run byte-identical RPX and data (identical hacks "generally do not cause a desynch"). It also sidesteps Nintendo/Pretendo matchmaking mixing modded and vanilla players. A build hash exchanged at connect is advisable.

### Gaps
- Smash 4's online input delay or buffer value, and whether it adapts per match, has no reliable source; a Smashboards thread speculates it is "scaled". Needs measurement, e.g. in Cemu via Pretendo, or in the RPX by finding the buffer constant.
- Which PIA version Smash 4 (Wii U) links, and which PIA protocol carries its inputs, were not found. NintendoClients' wiki (github.com/kinnay/NintendoClients/wiki) returned HTTP 403 from this environment.
- No local note covers Smash 4's network code (grep for "pia", "nex", "network" in docs found only the pad-slot note).
- Whether Smash for Wii U has any LAN mode is not verified; it appears to rely on NEX matchmaking.

## 5. Cemu-side lockstep netplay (Dolphin-style)

### Takeaway
A Dolphin-style netplay in Cemu means:
- identical boot (same RPX, mods and save data);
- exchanging each guest frame's controller state at the HLE input layer (`VPADRead`/`WPADRead`/`KPADRead`);
- pausing emulation on missing input;
- a periodic state hash for desync detection.

Cemu has clean injection points and already runs Smash 4 single-core. But guest time is host-RDTSC-based and nothing in Cemu is engineered for determinism. A virtual, deterministic timebase is mandatory, and residual non-determinism has to be found empirically (sync-test style). This route needs no RE of Smash 4's netcode and works for local modes (e.g. Smash mode with friends). It doesn't give rollback, and its latency is no better than ideal lockstep.

### Cited Findings
- Cemu HLE input entry points:
  - `VPADRead(channel, status, length, error)` calls `controller->VPADRead(*status, ...)` per channel;
  - `padscoreExport_WPADRead` calls `controller->WPADRead(wpadStatus)`;
  - `_KPADRead(channel, samplingBufs, length, errResult)` serves Wii Remote/Pro/Classic.

  — [Cemu `vpad.cpp`](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/OS/libs/vpad/vpad.cpp), [Cemu `padscore.cpp`](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/OS/libs/padscore/padscore.cpp)
- Cemu's host input APIs include a GameCube adapter provider (`src/input/api/GameCube`), plus SDL, XInput, DirectInput, DSU, Keyboard and Wiimote. — [Cemu `src/input/api`](https://github.com/cemu-project/Cemu/tree/main/src/input/api)
- Cemu implements the Wii U socket library (`nsysnet`, about 2,300 lines) on host sockets, which is what lets games' PIA/NEX traffic reach Pretendo. — [Cemu `nsysnet.cpp`](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/OS/libs/nsysnet/nsysnet.cpp)
- Guest timebase is host-RDTSC-derived (`PPCTimer_getFromRDTSC`), and thread quanta are cycle-based with a deterministic LCG jitter. — see §2 sources: [`PPCTimer.cpp`](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/HW/Espresso/PPCTimer.cpp), [`coreinit_Thread.cpp`](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/OS/libs/coreinit/coreinit_Thread.cpp)
- Dolphin netplay's synchronization machinery, the model to copy:
  - per-player pad buffers with an adjustable size (`OnPadBuffer`, `AdjustPadBufferSize`);
  - host-sent initial RTC (`m_initial_rtc`);
  - save-data sync (`SyncSaveData` with Raw/GCI/Wii/GBA sub-ids);
  - cheat/code sync (`SyncCodes`);
  - a `strict_settings_sync` option;
  - timebase-based desync detection every 60 frames (`SendTimeBase` / `DesyncDetected`);
  - "golf mode" (only one player at a time gets zero latency).

  — [Dolphin `NetPlayClient.cpp`](https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/Core/NetPlayClient.cpp), [Dolphin `NetPlayProto.h`](https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/Core/NetPlayProto.h)
- Smash 4's replay determinism (inputs + seed + rules) supports input-only sync, provided both instances start from the same state. — [SmashWiki: Replay](https://www.ssbwiki.com/Replay)

### Inferences
- **Build outline in Cemu:**
  1. a session layer: host/clients, a hash of the RPX + graphic packs/mods + `mlc01` save data, then save-data transfer, as Dolphin's SyncSaveData does;
  2. a deterministic timebase: replace `PPCTimer_getFromRDTSC()` for guest-visible time with a counter driven by emulated cycles, or by guest vsync count (60 Hz frames), seeded identically on all peers. Do the same for the RTC (`OSGetTime`'s `ppcCyclesSince2000TimerClock`);
  3. frame boundary = guest vsync/flip (GX2 swap). At each boundary, read local host input, send `{frame, pad state}`, and block until all peers' frame-N inputs arrive (with a pad buffer of B frames);
  4. serve those buffered states from `VPADRead`/`KPADRead`/`WPADRead` instead of live host controllers. Map peer i to a fixed emulated controller slot;
  5. desync detection: every 60 frames, hash a small known region (e.g. the battle RNG at `0x105759C0` and fighter positions) and compare.
- **Determinism risks in Cemu:**
  1. Host-time leakage. Guest code calling `OSGetTime`/`OSGetTick`/`mftb`, OS alarms, and `OSSleepTicks` wake-ups all depend on host time until virtualized. Even then, thread wake-up order depends on when the virtual time advances relative to emulated cycles.
  2. GPU/CPU coupling. If the game polls GX2 state (e.g. `GX2GetSwapStatus`, flip counts, occlusion queries) and branches on it, the result depends on host GPU speed. Async shader compilation changes timing but not values, unless the game measures time.
  3. File I/O completion timing (async FS callbacks) in the HLE FS layer.
  4. Audio callbacks driven by the host audio thread.
  5. Multi-core mode (avoided: Smash 4's profile is single-core).
  6. Floating-point equivalence across host CPUs. The x86-64 vs AArch64 Cemu backends may differ in FMA and rounding paths (not verified).
- Because Smash 4's match logic depends only on inputs + seed + rules, a pragmatic shortcut is to sync from the character-select screen onward. Exact boot-time determinism isn't needed if the match seed is forced identical: hook the per-match seed of RNG instance 0 to a value the netplay host sends, and keep the frame counter aligned at match start. That still needs RPX knowledge (where the match is seeded), which the local notes don't have yet.
- **Lockstep latency in Cemu** is no better than §4's ceiling, plus Cemu's own presentation latency (host vsync, swap-chain buffering). Benefits over stock online: works with mods, direct IP, no matchmaking server, any mode.

### Gaps
- No Cemu netplay PR or fork was found. GitHub issue/PR search via API was blocked; only a PR-list page for "savestate" was checked.
- Whether Smash 4 reads time or GPU state in battle logic is unknown, and determines how much Cemu work step 2 needs.
- No data on Cemu-vs-Cemu determinism across different host CPUs/GPUs.

## 6. Console side (real Wii U): homebrew networking plugins, feasibility, Cemu↔console crossplay

### Takeaway
Aroma's Wii U Plugin System (WUPS) gives a supported way to run code inside a game process:
- function replacement for OS RPL exports (e.g. coreinit, `nsysnet` sockets, `vpad`, `padscore`);
- application start/end hooks;
- in-memory patching precedent from Pretendo's Inkay (P2P port overrides, MK8 modpack matchmaking).

A console plugin plus the RPX's own caves could implement custom lockstep (§4). Console rollback is limited by the Espresso's CPU headroom and by the difficulty of game-level state capture (§3). Cemu↔console crossplay is possible only if both sides run the identical protocol and simulation; with rollback, cross-platform floating-point determinism between Cemu's recompiler and real Espresso becomes an extra risk.

### Cited Findings
- WUPS function replacement, from the example plugin source:
  - `DECL_FUNCTION(int, FSOpenFile, ...)`, calling the original through `real_FSOpenFile(...)`;
  - registration via `WUPS_MUST_REPLACE(FSOpenFile, WUPS_LOADER_LIBRARY_COREINIT, FSOpenFile)`, "(In general it's WUPS_LOADER_LIBRARY_ + the name of the RPL in caps lock)";
  - "Currently it's only possible to override functions that are loaded from .rpl files of OSv10";
  - lifecycle hooks `INITIALIZE_PLUGIN()`, `ON_APPLICATION_START()`, `ON_APPLICATION_ENDS()`.

  — [WiiUPluginSystem example plugin `main.cpp`](https://github.com/wiiu-env/WiiUPluginSystem/blob/main/plugins/example_plugin_cpp/src/main.cpp)
- "The Wii U Plugin System is a library to create plugins for the WiiUPluginLoaderBackend." — [wiiu-env/WiiUPluginSystem](https://github.com/wiiu-env/WiiUPluginSystem)
- Inkay "is an Aroma/WUPS plugin that patches various Nintendo Network URLs on a Wii U to use Pretendo Network instead". It "includes game-specific patches", including a "P2P port override for better connection stability" for Mario Kart 8, Minecraft: Wii U Edition and Splatoon. "Inkay's patches are all temporary, and only applied in-memory without modifying your console." — [PretendoNetwork/Inkay](https://github.com/PretendoNetwork/Inkay)
- Wii U hardware: 3-core Espresso at 1243.125 MHz; 1 GB of MEM2 available to games; 32 MB MEM1; 12.8 GB/s total memory bandwidth; 802.11b/g/n Wi-Fi; USB 2.0 ports. — [WiiUBrew: Hardware](https://wiiubrew.org/wiki/Hardware)
- Cemu can join Pretendo with a dumped console account (Cemu 2.0+, "Pretendo" network service), so Cemu and console players already meet in stock Smash 4 online through the same PIA protocol. — [WiiUBrew: Pretendo Network](https://wiiubrew.org/wiki/Pretendo_Network) (via search summary), [SmashWiki: Nintendo Network](https://www.ssbwiki.com/Nintendo_Network)
- Address mapping between console and Cemu (local note): Manifold's console builds add `0x0A000000` to code and `0x00503000` to data addresses relative to the ELF/Cemu addresses used in the notes. — [docs/native-notes.md, "Console addresses"](/home/user/Smash4ModdingTests/docs/native-notes.md)

### Inferences
- **Console plugin design for improved lockstep:**
  - the modpack's patched RPX contains caves that fill the network pad slots from a shared ring buffer and expose a frame counter;
  - a WUPS plugin (or caves alone, importing `nsysnet` socket functions) runs a UDP transport on a background thread (another Espresso core) and fills the ring buffer.

  WUPS replacement only covers OS RPL exports, so game-internal functions (PIA is statically linked, by inference) must be patched by caves or by in-memory writes at application start, as Inkay does, using the console address offsets above.
- **Crossplay:** a custom lockstep protocol implemented both as a Cemu feature and as a console plugin or RPX caves gives Cemu↔console play, provided:
  - the RPX and data are byte-identical;
  - all non-determinism sources (clock RNG, time reads) are removed in the RPX itself rather than in Cemu.

  So putting the netcode in the RPX (caves + `nsysnet`) is the crossplay-friendly choice: Cemu needs no changes, because the guest's socket calls already work through Cemu's `nsysnet`.
- **Rollback on console** would need game-level snapshotting inside the RPX (§3) and enough Espresso headroom to re-simulate. Both are unproven, and crossplay rollback adds the Cemu-vs-hardware floating-point equivalence question. Lockstep has the same requirement, but there divergence surfaces as a desync, not as a mismatched correction. Stock online play already mixes Cemu and console players, which is weak evidence that Cemu's FPU emulation matches hardware closely enough for Smash 4's lockstep.

### Gaps
- No existing Wii U homebrew project implementing custom game netplay (lockstep or rollback) for any title was found.
- WUPS documentation on patching game-executable code, as opposed to RPL exports, and on threading/socket use inside plugins was not fetched. Only the example plugin was read.
- Smash 4's CPU utilization per core on real hardware (headroom for re-simulation) is unknown.
- Whether any player reports of Cemu↔console desyncs on Pretendo Smash 4 exist was not checked.
