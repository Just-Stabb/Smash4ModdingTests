# Sm4shCloneTool Aroma plugin

A Wii U plugin (Aroma, WUPS 0.9) that applies a Sm4shCloneTool clone patch to Super Smash Bros. for Wii U in memory
when the game starts, so the console runs the game's **own, unmodified cross_f.rpx**. One plugin binary works for every
clone set: the clones are in the patch file the tool writes (`--exe-output aroma`, or "Aroma plugin patch file" in the
window).

**Not yet run on a console.** What was checked, and how, is at the end of this file.

## Install

From a package built with the Aroma output, copy the contents of `INSTALL_TO_sd/` to the root of the SD card:

```
wiiu/environments/aroma/plugins/sm4shclonetool.wps     the plugin
wiiu/sm4shclonetool/0005000010144F00.patch             the project's patch (USA)
wiiu/sm4shclonetool/0005000010145000.patch             (EUR)
wiiu/sm4shclonetool/0005000010110E00.patch             (JPN)
```

and the clones' data files (`INSTALL_TO_data/`) as for any build (your mod's `content/patch/data`). Keep the game's own
`code/cross_f.rpx`: the plugin refuses a modified one. The game needs its v288 update.

At every start of Smash 4 the plugin shows a notification: "clone patch applied" or why it patched nothing.

## What it does

At each application start (`ON_APPLICATION_START`), for the running title only if it is Smash 4 (USA / EUR / JPN):

1. reads `sd:/wiiu/sm4shclonetool/<title id>.patch` (else `sm4sh.patch` in that folder);
2. checks the file: magic, format, CRC-32, the running title in its list, the update's title version (`MCP_GetTitleInfo`
   of `0005000E-...`) = the file's (288);
3. compares every word of the game the patch changes (about 450 for a few clones) with the original the file records;
   **one mismatch and nothing is written** (another mod, another executable, the tool's patched rpx installed too);
4. copies the code cave (the tool's code space: code, tables, and the data the game writes at run time) into the
   plugin's own memory (`src/cave.S`, a 1 MB + 64 KB block of its `.text`) at an address equal to the file's link base
   modulo 0x10000, and relocates it (below);
5. writes the game's words through the kernel (`KernelCopyData` on physical addresses, Aroma's libkernel: the game's
   code is read-only to applications) after the cave is flushed; then flushes / invalidates the caches.

`src/patch_core.c` holds steps 2-5 without any Wii U call (the tool's tests compile it on a PC and compare it with the
Python implementation, `sm4shclonetool/patchset.py`), `src/main.c` the Wii U side.

### Why the cave moves, and how

The patched rpx puts the cave at `0x04B78000`, after the game's code, and grows the executable's code section (and its
text region past `0x04BB8670` for many clones). In memory, after the console's loader, neither is possible: the loader
maps the text region the file asked for, and the game's code region is read-only to the game (it executes, it does
not write). The cave also holds data the game writes at run time (the character select's random pools, Kirby's copy
table, the new characters' records), so it must be writable as well as executable: the plugin's own memory.

The patch is relocatable because the tool's generators take the code space's base as a parameter: the tool generates
the patch at its base and at three probe bases and classifies every word that changes (`patchset.py`):

| kind | what | relocated by the plugin (cave base = link base + delta, delta a multiple of 0x10000) |
|---|---|---|
| ADDR32 | a cave address as data (tables, descriptors, pointers) | `+= delta` |
| HA16 / HI16 | the high half of a cave address (`lis` / `addis`) | immediate `+= delta >> 16` |
| LO16 | the low half (`addi`, `ori`, a load's displacement) | unchanged at that alignment |
| REL24 game -> cave | a hook (`b` / `bl` into the cave) | made absolute: `ba` / `bla` (the cave is below 0x02000000, where an absolute branch reaches from anywhere) |
| REL24 cave -> game | the cave's calls / jumps back into the game (out of reach from the plugin's memory) | already in the file as a branch to a veneer `lis rN / ori rN / mtctr rN / bctr`, appended to the cave; rN and ctr dead at the target (checked on the game's code by `ppcflow.py`) |

The relocation table is checked when it is made (it must predict the generators' own output at another base word for
word), and the tests run the relocated image in the tool's hook emulations.

## The patch file (format 1, big-endian)

```
0x00  "S4CTPTCH"
0x08  u32 format (1)          u32 game version (288)     u32 link base (0x04B78000)   u32 align (0x10000)
0x18  u32 cave size           u32 game words (N)         u32 cave relocations (R)     u32 title ids (T)
0x28  u32 meta length (M)
0x2C  T x u64 title ids
      M bytes: zlib(JSON) {tool, fighters, stages, source_sha1, image}, padded to 4
      N x {u32 address, u32 original, u32 new (at the link base), u32 kind: 0 abs, 1 HA16, 2 ADDR32, 3 REL24}
      R x u32 (cave offset | kind << 28), kinds 1 / 2
      the cave (cave size bytes, as at the link base, veneers included)
      u32 CRC-32 of everything before it
```

`python cli.py patchinfo --patch FILE.patch [--exe cross_f.rpx]` prints what a file holds (and whether that
executable's words are the originals).

## Build

Needs devkitPPC, wut, WUPS and Aroma's libkernel and libnotifications (devkitPro's `wiiu-dev`, and the wiiu-env
releases / docker images `ghcr.io/wiiu-env/wiiupluginsystem`, `libkernel`, `libnotifications`, installed under
`$DEVKITPRO/wups` and `$DEVKITPRO/wums`). Then `make` (`make CAVE_KB=2048` for a bigger cave; 1024 KB holds about 140
fighter clones). The tool ships the plugin it was tested with (`sm4shclonetool.wps`, built with devkitPPC (GCC 16.2),
wut and WUPS 0.9.1); the package's builds copy it into `INSTALL_TO_sd/`.

## What was checked, and what was not

Checked (the tool's tests, on the game's v288 executable):
- the patch set applied at the tool's own base equals the patched rpx's memory image byte for byte (every section,
  but the marker block);
- relocated as the plugin places it (0x00908000), the tool's hook emulations (the results screen's announcer call, the
  sound aliases, Kirby's copy grant / resources / names / voice bound / copy scripts / copy bank, the random select's
  refill / pick / remove / count, the online helper, the stage refill, the custom-move map) give what they give on the
  patched rpx;
- the C code (`patch_core.c`, built for a PC) writes the same game words and cave bytes as the Python implementation,
  and refuses (writing nothing) a changed word, a damaged file, another title, another update version, a buffer out of
  reach;
- the plugin builds (no warnings).

Not confirmed on a console:
- that `ON_APPLICATION_START` comes after the loader has finished with `cross_f.rpx` and before the game runs (it is
  where Aroma plugins patch game code; the original-word check refuses if the code isn't there yet);
- that Aroma's plugin memory (where `.text` and so the cave are) is below 0x02000000, executable and **writable** from
  the game (the plugin refuses an address at or past 0x02000000; it can't test the permissions without risking a
  crash: if the plugin's text is not writable, the game would fault on its first write to the cave, e.g. at the
  character select's random pick);
- `MCP_GetTitleInfo` on the update title giving 288 (if it fails, the original words still decide);
- the other regions' v288 executables being the same as the USA one (the original-word check refuses any difference).
