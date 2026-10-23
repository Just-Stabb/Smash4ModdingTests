# Netcode precedents: how modding communities upgraded or replaced netcode without source access (for a Smash 4 Wii U modpack)

Research date: 2026-10-23. Note on method: medium.com, ssbwiki.com, docs.libretro.com, timeextension.com, khang06.github.io and dolphin-emu.org could not be fetched from this environment (DNS failures), so some facts come from search-result snippets of those pages rather than full reads; these are marked "(search snippet)". The strongest primary evidence gathered is the Slippi Ishiiruka source code (SlippiSavestate.cpp) and the Cemu GitHub issue #898.

## Project Slippi (Melee): how rollback was built, how long, what made it possible

### Takeaway
Slippi's rollback is a hybrid: a Dolphin fork (Ishiiruka) does the networking and a custom "savestate" that copies only selected regions of the game's main RAM (static data/BSS plus the game heap, about 8 MB), not a full Dolphin savestate, while ASM patches inside Melee talk to the emulator over a fake EXI device. It shipped June 22, 2020 after roughly 7 months of full-time work by Fizzi on top of years of earlier Slippi (replay) infrastructure, and it depends on one fixed, fully mapped game binary (Melee NTSC 1.02).

### Cited Findings
- Slippi's own wiki: "Rollback is accomplished by work done between the Slippi SSBM ASM code and the Ishiiruka code." Data moves between the game's ASM and the emulator through "EXI communication" (`EXI_DeviceSlippi.cpp`); when Melee launches Ishiiruka applies the ASM modifications, and during matches it logs game state reported by the ASM. — [slippi-wiki GETTING_STARTED.md](https://github.com/project-slippi/slippi-wiki/blob/master/GETTING_STARTED.md)
- Ishiiruka's `SlippiSavestate.cpp` saves/restores **only selected memory regions, not full RAM**; the full-RAM line `// p.DoArray(Memory::m_pRAM, Memory::RAM_SIZE);` is commented out. Regions: `0x80005520–0x80005940` ("Data Sections 0 and 1"), `0x803b7240–0x804DEC00` ("Data Sections 2-7 ... including BSS", ~1.2 MB), `0x8065c000–0x8071b000` ("Unknown Region", ~0.78 MB), and the heap `0x80bd5c40–0x811AD5A0` (~6.1 MB, bounds read at runtime from pointers at `0x804d76b8`/`0x804d76bc`). — [Ishiiruka SlippiSavestate.cpp](https://raw.githubusercontent.com/project-slippi/Ishiiruka/slippi/Source/Core/Core/Slippi/SlippiSavestate.cpp)
- The same file excludes ~21 "Sound stuff" blocks (largest 0x1EE80 at 0x80433C64), the XFB/VI memory block (0x804c0980), and several small hand-identified addresses; it supports "preserve blocks" that are kept across a load (copied out before restore and written back after). Of emulated hardware state, only `ExpansionInterface::DoState` is active; VideoInterface, SerialInterface, ProcessorInterface, DSP, DVDInterface, GPFifo and AudioInterface DoState calls are commented out, and CPU registers are not saved. — [Ishiiruka SlippiSavestate.cpp](https://raw.githubusercontent.com/project-slippi/Ishiiruka/slippi/Source/Core/Core/Slippi/SlippiSavestate.cpp)
- `EXI_DeviceSlippi.h` keeps a pool of savestates (`std::map<s32, std::unique_ptr<SlippiSavestate>> activeSavestates; std::deque<...> availableSavestates;`), i.e. one per in-flight frame; a comment in `EXI_DeviceSlippi.cpp` says it "Forces savestate to re-init regions when a new ISO is loaded". — [GitHub code search, project-slippi/Ishiiruka](https://github.com/project-slippi/Ishiiruka/blob/slippi/Source/Core/Core/HW/EXI_DeviceSlippi.h)
- A Hacker News commenter (not official) on the Dolphin May/June 2020 progress report said the developer had to build a way to generate arbitrary game states because Dolphin savestates were not performant enough, and that Slippi still adds ~2 frames of input delay to reduce visible rollbacks. — [Hacker News thread](https://news.ycombinator.com/item?id=23739074) (search snippet; consistent with the source code above)
- Rollback + integrated matchmaking released in the Slippi Dolphin build on June 22, 2020. — [SmashWiki: Slippi](https://www.ssbwiki.com/Slippi) (search snippet); Fizzi's announcement tweet dated around then: [x.com/fizzi36](https://x.com/fizzi36/status/1275096470765490176)
- Fizzi announced rollback "after 7 months of full time work"; GBAtemp also reports seven months full-time. — [Medium article by J. Chung](https://medium.com/@jchung.bsd/how-one-man-just-changed-the-face-of-competitive-super-smash-bros-melee-3e39bc2c4d57) (search snippet); [GBAtemp thread](https://gbatemp.net/threads/project-slippi-is-a-build-of-dolphin-that-adds-rollback-netcode-to-super-smash-bros-melee-netplay.568152/page-2) (search snippet)
- Post-launch netcode work continued: Ishiiruka v2.4.0 (Feb 2022) added improvements that "attempt to keep players better in sync with dynamic emulation speed, reducing one-sided rollback scenarios." — [Ishiiruka release v2.4.0](https://github.com/project-slippi/Ishiiruka/releases/tag/v2.4.0) (search snippet)
- A port of Slippi to mainline Dolphin exists as an opt-in beta; rollback logic "reaches deep into the emulator's state management", which is why it was kept separate from mainline. — [tech-insider.org comparison (low-quality aggregator)](https://tech-insider.org/dolphin-vs-slippi-vs-primehack-2026/) (search snippet; treat with caution)
- Slippi's spectator/netplay surface has had security issues (an RCE writeup exists). — [khang06, "Slipping up Slippi with spectator RCE"](https://khang06.github.io/slippirce/) (title only; page not fetchable)

### Inferences
- The key enabler was **game-level knowledge**: the team mapped Melee's memory well enough to know which ~8 MB of RAM is gameplay state and which parts (sound, XFB, interrupt state) must be excluded or preserved. That relies on a single frozen binary (NTSC 1.02) and years of community reverse-engineering; an approach "snapshot the whole emulated console" was avoided for speed.
- Because it skips GPU/DSP/CPU-register state, Slippi rolls back at frame boundaries where the game loop is in a known state, signalled by the in-game ASM over EXI. The Smash 4 analogue would be a hook in the game's main loop (RPX code cave) that tells the emulator "frame boundary, snapshot now."
- "7 months full time" understates total effort: replay/EXI infrastructure predated it by years (Slippi began as a replay project around 2018). I could not confirm the start date from a primary source.

### Gaps
- Fizzi's own Medium posts (e.g. on desync fighting, rollback design) could not be fetched; exact desync-detection mechanism (checksums of game state?) and ISO-hash check details were not confirmed from primary sources.
- Team size at rollback launch (Fizzi plus contributors such as the ASM/Gecko code authors) not confirmed from a primary source.
- Matchmaking server architecture (slippi.gg, ranked launched later) not researched in depth.

## Dolphin netplay (delay-based lockstep) for Project M / Project+ / Brawl mods

### Takeaway
Brawl mods use Dolphin's stock netplay, which is delay-based (an adjustable input buffer), deterministic lockstep: it only works if every player runs the same emulator build, the same ISO, the same Gecko codes and the same SD-card mod contents. Mismatches cause desyncs, and Dolphin's desync detection can flag false positives when code lists differ.

### Cited Findings
- Desync troubleshooting: a desync is "something different is happening on both sides"; settings must be "for the most part, identical"; most common cause is "Different ISOs / Bad Dump"; aspect-ratio Gecko codes must match; Dolphin "will still report a false positive desync if you have different codes checked"; memory cards had to be disabled on newer builds because they "do not sync" like they did in 4.0-652. — [SmashLadder Desync Troubleshooting Guide](https://www.smashladder.com/guides/view/258a) (search snippet)
- Brawl mods like Project M load via an SD-card image; older guides require "Enable cheats" and "Insert SD Card" checked. — [Dolphin forums PM guide (2013)](https://forums.dolphin-emu.org/Thread-updated-first-post-how-to-play-brawl-project-m-etc-unofficial?page=13) (search snippet; dated)
- Specific Dolphin build choice mattered historically: a bug report says a later build desynced while "Anther's recommended Netplay version of 5.0-123" worked. — [Dolphin bug #11687](https://bugs.dolphin-emu.org/issues/11687?tab=notes) (search snippet)
- HDR's announcement describes its tunable online delay as "akin to Dolphin input buffer", confirming Dolphin netplay is delay/buffer-based. — [HDR on X](https://x.com/hewdrawremix/status/1597744718778990593)

### Inferences
- Dolphin netplay's model (same build + same game files + same codes, synchronized inputs only) is the closest existing precedent to what a Smash 4 modpack would need for a Cemu "netplay" fork: deterministic emulation plus identical mod content, with a content hash check at lobby time.
- Project+ ships a single packaged Dolphin build + SD image, which is how it avoids mismatch; a Smash 4 modpack could likewise ship a pinned Cemu build + pinned mod folder hash.

### Gaps
- Current (2025-2026) Project+ official netplay docs and whether P+ uses Dolphin's SD-card sync / "Netplay checks" feature were not retrieved (Dolphin blog and P+ site not reachable). Dolphin's netplay "Golf mode"/host input authority details not covered.

## Smash Ultimate modding: HDR, ARCropolis/Skyline mods online, latency slider, desync

### Takeaway
No Ultimate mod replaces the game's netcode; instead the community changes the **input delay** the stock netcode uses (HDR's built-in option and the standalone "latency-slider-de" Skyline plugin) and relies on the game's existing P2P/LDN online. Gameplay mods only stay in sync when both players run identical mod sets.

### Cited Findings
- HDR (Nov 2022 beta): "Online input latency can now be individually selected and tuned by both parties, akin to Dolphin input buffer!" — [HDR on X](https://x.com/hewdrawremix/status/1597744718778990593)
- `Naxdy/latency-slider-de`: "A skyline mod that enables manual choosing of desired input latency in Smash Ultimate, compatible with every online mode." Rust, created 2024-02-20, last updated 2026-10-09, ~81 stars. — [GitHub: Naxdy/latency-slider-de](https://github.com/Naxdy/latency-slider-de)
- Community HDR netplay guide (Yuzu/Steam Deck): pick a buffer of roughly opponent ping / 8; default 4 usually works; the latency slider is a separate download; disabling all mods in Yuzu also disables the latency slider and training-mode patches. — [The Outcaster's Notebook: HDR Netplay Guide](https://theoutcastersnotebook.com/post/hdr-netplay-guide/) (search snippet)
- HDR has an open issue requesting a "Play Vanilla" button in the HDR launcher (i.e. switching between modded and vanilla online is a known friction). — [HDR issue #2615](https://github.com/HDR-Development/HewDraw-Remix/issues/2615) (title only)
- HDR releases are distributed from a dedicated repo, so every player installs the same versioned package. — [HDR-Releases](https://github.com/HDR-Development/HDR-Releases)

### Inferences
- The Ultimate precedent maps directly onto Smash 4: Smash 4 also has delay-based P2P online with an internal input delay; a Smash 4 analogue of latency-slider (patch the delay value in the RPX) is a far smaller project than rollback.
- The Ultimate community never attempted rollback in a Switch emulator; consistent with Cemu's situation (no savestates at all), this suggests full emulator-level rollback for 7th/8th-gen HLE emulators is not a path communities have successfully taken.

### Gaps
- No primary source found for how mismatched HDR/ARCropolis mods desync, or for any Ultimate netcode-replacement attempt. latency-slider-de README could not be read (repo access restricted in this session).

## Other rollback retrofits without source (and which used emulator savestates vs in-game state)

### Takeaway
Emulator-level savestate rollback works well for small, fast-to-snapshot systems (arcade via FBNeo/Fightcade, N64 via RMG-K in 2026, RetroArch cores); Slippi is the main example of game-aware partial-RAM rollback on a 6th-gen console. The well-known GG XX AC+R rollback was an official publisher patch, not a community mod.

### Cited Findings
- Fightcade's main emulator FightcadeFBNeo uses FBNeo with a "modified GGPO netcode", described as rollback-based P2P netplay. — [Flathub: Fightcade](https://flathub.org/en/apps/com.fightcade.Fightcade) (community-packaged, secondary)
- GGPO is a rollback SDK that uses input prediction and speculative execution instead of delaying inputs; MIT-licensed; Windows-only builds. — [GitHub: pond3r/ggpo](https://github.com/pond3r/ggpo)
- RMG-K (fork of the RMG N64 emulator) added rollback netplay in May 2026 using the GekkoNet framework (integrated by NyxTheShield, developer CigNus); limited to two players; a tester played Spain–Australia at 4 frames delay vs 9 previously; headline quote "it was honestly not that hard". Shown with GoldenEye; Smash 64 mentioned only in secondary coverage. — [Time Extension](https://www.timeextension.com/news/2026/05/it-was-honestly-not-that-hard-this-nintendo-64-emulator-lets-you-play-online-with-rollback-netcode) (search snippet); [inkl mirror](https://www.inkl.com/news/nintendo-64-emulator-just-implemented-rollback-netcode-for-the-entire-library-it-was-honestly-not-that-hard)
- RetroArch netplay depends on core savestate (serialization) compatibility; an issue tracks problems when cores are backwards-incompatible across versions. — [RetroArch issue #14149](https://github.com/libretro/RetroArch/issues/14149) (search snippet)
- Guilty Gear XX AC+R: GGPO rollback was an **official** Arc System Works Steam update, public beta in Oct 2020 ("publictest - GGPOupdatetest"), released Dec 22, 2020; input delay selectable 0–4 frames. — [Gematsu](https://www.gematsu.com/2020/12/guilty-gear-xx-accent-core-plus-r-for-pc-ggpo-rollback-netcode-update-now-available); [EventHubs](https://eventhubs.com/news/2020/oct/29/guilty-gear-rollback-beta)
- Other recompilation projects are adding rollback by snapshotting recompiled game state (e.g. CBFD-Recompiled-Netplay rollback issues; nesrecomp rollback PR with a "determinism probe"). — [CBFD-Recompiled-Netplay #22](https://github.com/easymod0/CBFD-Recompiled-Netplay/issues/22); [nesrecomp PR #24](https://github.com/mstan/nesrecomp/pull/24)

### Inferences
- Emulator-savestate rollback scales with snapshot cost: N64 (8 MB RAM) and arcade boards are trivial to snapshot every frame; Wii U (much larger RAM, HLE OS modules, GPU state) is not. Slippi shows the workaround: snapshot only the game's own state.
- Static recompilation projects are a newer path to rollback; no Wii U/Smash 4 recomp exists to my knowledge (not verified).

### Gaps
- Smash Remix's specific netplay setup (its own recommended emulator/netplay) not confirmed. Fightcade/FBNeo GGPO technical internals, SF3 / SFV community rollback mods, Skullgirls, Brawlhalla, Rivals and Them's Fightin' Herds were not researched (budget); RetroArch's own netplay docs unreachable.

## Smash 4 Wii U online / netplay projects and Wii U (Cemu) savestate/netplay status

### Takeaway
Smash 4's official online ended April 8, 2024; online now runs on the original game netcode via Pretendo (supported by Cemu since 2.0 and by modded consoles). No Cemu netplay or rollback fork was found, and Cemu still has no savestates: issue #898 remains open (as of early 2026), with the lead dev listing a large per-module implementation burden.

### Cited Findings
- Official Smash 4 online ended April 8, 2024, with the Wii U/3DS online shutdown; replacement servers, primarily Pretendo, resurrect online modes. — [SmashWiki: Online play](https://www.ssbwiki.com/Online_play) (search snippet); [Wikipedia: Pretendo Network](https://en.wikipedia.org/wiki/Pretendo_Network)
- Cemu supports Pretendo online (since 2.0); requires dumping online files from your own Wii U with Dumpling. — [cemu.cfw.guide Online Play](https://cemu.cfw.guide/online-play.html) (search snippet)
- One report says Smash 4 For Glory/For Fun work on Pretendo with "occasional desync issues". — [EmuDesk](https://emudesk.com/issues/cemu-pretendo-network-wii-u-online-2026) (search snippet; low-quality source)
- Cemu issue #898 "Revisiting Save States" (opened 2023-07-11) is still open; a duplicate was linked on 2026-01-31. Maintainer Exzap: the main obstacle is implementation work, since Cemu is HLE with much dynamic runtime state; a savestate would need every PPC thread context (`OSThread_t`), a full RAM dump, load/store code for each CafeOS module/driver and each IOSU module, VRAM-only textures, vertex/uniform caches, and settings; pause/resume should come first; an earlier attempt by ChrisNonyminus was unfinished. Netplay is never mentioned. Users in 2025-2026 note the lack of savestates blocks a libretro core and RL work. — [Cemu issue #898](https://github.com/cemu-project/Cemu/issues/898)
- An older Cemu feature request was closed as save states "arnt feasible on newer generation emulators including Wii U". — [Cemu bug tracker #161](https://bugs.cemu.info/issues/161) (search snippet)
- No Cemu netplay fork or Wii U rollback project turned up in searches. — (negative result; searches documented above)

### Inferences
- Slippi-style rollback for Smash 4 on Cemu would need (a) a Cemu fork with fast partial-RAM snapshot/restore triggered by an in-game hook, (b) proof that Smash 4's gameplay state lives in known memory with no hidden state in GPU/CafeOS modules, (c) Cemu determinism across machines (JIT, multi-core recompiler, timing). Console players could not use it at all, so it would split the player base; a console-compatible option is limited to tuning the existing delay-based netcode (like Ultimate's latency slider) over Pretendo.
- Mod-content hashing at lobby time (like Dolphin/Slippi checks) is the transferable lesson for keeping a modpack in sync on both Cemu and console.

### Gaps
- No found Smash 4 community discussion of netplay/rollback (Smash 4 competitive community, Sm4sh modding Discords) — likely lives on Discord, not indexed. decaf-emu savestate status not checked. Smash 4's internal online input delay value/location not researched here.
