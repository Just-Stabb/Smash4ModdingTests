# Sm4shExplorer: faster builds, "Extract vanilla", "Clean vanilla files" and "Build to Folder"

`sm4shexplorer-faster.patch` (6 commits) applies to https://github.com/thefungus/Sm4shExplorer
(`e349175`, the latest commit): `git am sm4shexplorer-faster.patch`. Built with mono's `xbuild`
(`/p:Configuration=Release`), then `python3 tools/sm4shexplorer/set_laa.py Sm4shFileExplorer.exe`;
the exe is in `build/sm4shexplorer_faster_v6.zip` (replaces `Sm4shFileExplorer.exe`; the DLLs and
plugins are unchanged).

## Why builds were slow

Every build, for every package (folder packed as one file, e.g. `fighter/kirby`) holding a mod
file, Sm4shExplorer:
1. extracted **every** file of the package from the DT files (or the update's packed file) to the
   temp folder, **decompressing** each one;
2. read each back and **compressed** it again (zlib level 6, one file at a time);
3. checked, for each file, all the files after it to know if it ended a folder (quadratic in the
   package's file count), and wrote the padding one byte at a time.

It also compressed every loose mod file again on every build.

## What changed

- **Untouched package files are taken as the game stores them** (`RFManager.TryGetStoredData`):
  their compressed bytes are read straight from the DT file / packed file and written into the new
  package with their original sizes; in the temp folder they're only empty placeholders (so the
  package's file and folder list is built exactly as before). Only the mod's own files are read and
  compressed. Files the update has on their own, externally-patched files (`OverridePackedFile`),
  empty files and data starting with padding still go the old way.
- **Compression cache** (`cache/compressed/`, next to the exe): compressed data by content hash
  (SHA-1 + size), so an unchanged mod file isn't compressed again. Entries no build used for
  30 days are deleted at the end of a build.
- **Parallel compression**: the files of a package, and the loose mod files, are compressed on all
  cores; the package is then written in order as before.
- The "last file in a folder" check is a lookup built once per package (checked against the old
  loop on 300 random file trees: identical), and padding is written in blocks.

The package layout, padding, sizes and flags are computed exactly as before. The one difference
in the output: an untouched file the old code would have recompressed now keeps the game's own
compressed data, which the game already reads.

## Memory (v2)

v1 often failed with `System.OutOfMemoryException` (user): the exe is 32-bit (x86, 2 GB of
address space) and v1 held a whole package in memory several times (the untouched files' stored
data from extraction on, every file's data, the package in a MemoryStream and its copy). v2:
- the package is written straight to its `packed` file;
- an untouched file's location is kept at extraction, its data read only when the package is written;
- files are read / compressed in batches (about 32 MB or 256 files, on all cores), each file's
  data let go once written; loose mod files' data too;
- the exe is marked large address aware (`set_laa.py`): 4 GB on 64-bit Windows. (It stays 32-bit:
  the music plugin's audio library is native 32-bit.)

## Package cache (v3)

A package whose inputs haven't changed since a build isn't rebuilt: after packing, its `packed`
file and every file's resource values (offset, sizes, package flag) are saved in
`cache/packages/<key>.packed` / `.meta`; the next build with the same key copies the file to the
export folder and sets the values (log: "unchanged, taken from the cache"). The key is a hash of
the package's path, its mod files (path, size, content hash), the game's own files in it (source,
location, sizes) and a version string. Release builds only (debug builds write packages
unpacked). Entries no build used for 30 days are deleted. It costs disk space: a copy of each
modded package (a fighter's is often 100-300 MB).

## Extract vanilla

Right-click → **Extract vanilla**: extracts the game's own version (file or folder) to
`extract/vanilla/`, even where the workspace has a mod file, and leaves the mod file alone
(plain **Extract** still gives the mod's version when there is one). It's greyed out for files only
the mod has.

## Clean vanilla files (v4)

A workspace often holds files that are the game's own, unchanged (a whole folder extracted to edit
one file in it). Each makes the build rebuild its package, and ships in the build for nothing.
**Project → Clean vanilla files from workspace...** (or right-click a mod folder / file → **Clean
vanilla files**, for just that part):
1. in the background, every workspace file the game also has is compared with the game's own
   version: the one the game loads (the update's if it has one, else the DT files'), decompressed,
   as Extract writes it (`RFManager.GetVanillaData`). A different size is enough to keep a file;
   same size: byte for byte. Mod-only files, files of resources marked removed, and (without the
   DT files) files only the DT files have are left alone;
2. the identical ones are listed (count, size; all of them in the console) and, on **Yes**, moved
   to `<workspace>_removed_vanilla/<date>/` with the same paths (next to the workspace folder, so
   builds don't see them; nothing is deleted), the folders they leave empty removed, the plugins
   told as for "Remove mod files" (any can keep a file), and the tree refreshed.

A package whose workspace files were all vanilla is then not rebuilt at all (the game's own is
used), and the others pack only real mod files.

Not tested on a game dump yet (none here): built with 0 errors, the patch reproduces the source
exactly, and the empty-folder clean-up was run on a fake workspace (emptied folders removed up to
the partition folders, a folder still holding a file kept).

## Tested (user)

v3 in a real build: builds are faster, and with the package cache, rebuilding unchanged packages
is over 1000x faster for large packs. (v1's out-of-memory error was fixed in v2.)

## New files in packaged folders (v5)

A file the game doesn't have, in a folder the game reads as one package (`ui/replace/chr/chr_10/`
and the other portrait sets, a fighter's folder, ...), starts with offset 0, and the original code
takes offset 0 on a file as "a package of its own" (`ResourceItem.IsAPackage`): unless the folder was
set to **Pack this folder**, the file was written loose with flag `0x400` in the resource table,
inside the packaged folder, and the game crashed reading the package (user: Supamario's `chr_10`
icon; Cemu: `ResourceSystem:Reading` on `data/ui/replace/chr/chr_10/packed` with a size of
`0xFFE7B682`; the table had `chr_10_Supamario_01.nut` at offset 0, flags `0xC05`, while the other
portrait folders, set to pack, had theirs in the package). `BuildNewResources` now puts such a file in
its package (offset 1, as a file set "in package"); files in folders that aren't packages are built
as before.

## Build to Folder (e.g. a Cemu graphic pack)

Project > **Build to Folder...** builds the mod (packed, like Build) into a folder you pick instead
of `export/release`. Project > **Build to <folder>** (Ctrl+Alt+B) builds into the last one again.
The folder is remembered in the project.

- **Layout:** the build goes in the folder's `content/patch`, the same layout as `export/release`.
  That is what a Cemu graphic pack lays over the game: `Cemu/graphicPacks/<pack>/content/patch/...`.
- **What's replaced:** only `content/patch` is deleted before building. The rest of the folder
  (`rules.txt`, other files) is kept. The release build, by contrast, empties its whole folder.
- **rules.txt:** if the folder has none, Sm4shExplorer offers to write one, so Cemu lists it as a
  graphic pack for Smash 4. It covers all three regions (title IDs `0005000010144F00`,
  `0005000010145000`, `0005000010110E00`) and uses rules version 6 (Cemu 1.25 and later). Enable
  the pack in Cemu's Options > Graphic packs.
- **Blocked folders:** a folder holding (or inside) the workspace or the game folder is refused,
  since the build would wipe it.
- **SD card:** it doesn't offer to copy the build to an SD card afterwards.
