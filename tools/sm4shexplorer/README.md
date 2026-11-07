# Sm4shExplorer: faster builds, "Extract vanilla", "Clean vanilla files", "Build to Folder", merging folders

`sm4shexplorer-faster.patch` (7 commits) applies to https://github.com/thefungus/Sm4shExplorer
(`e349175`, the latest commit): `git am sm4shexplorer-faster.patch`. The exe is in
`build/sm4shexplorer_faster_v8.zip` (replaces `Sm4shFileExplorer.exe`; the DLLs and plugins are
unchanged).

**Build (v7 on):** with Microsoft's C# compiler (Roslyn, from the .NET SDK: Ubuntu's `dotnet-sdk-8.0`),
run by mono's `xbuild` (which still makes the `.resources`), against mono's .NET 4.5 reference
assemblies; Visual Studio gives the same kind of exe.

    printf '#!/bin/sh\nexec dotnet /usr/lib/dotnet/sdk/8.0.133/Roslyn/bincore/csc.dll "$@"\n' > roslyn/csc
    chmod +x roslyn/csc
    xbuild Sm4shFileExplorer/Sm4shFileExplorer.csproj /p:Configuration=Release \
        /p:CscToolPath=$PWD/roslyn /p:CscToolExe=csc
    python3 tools/sm4shexplorer/set_laa.py Sm4shFileExplorer/bin/Release/Sm4shFileExplorer.exe

**Why (v7):** v1-v6 were compiled by mono's `mcs`. Chrome refused to download v6 (Safe Browsing) and
Windows Security flagged it once extracted (user). An `mcs` exe looks like nothing Windows normally
runs: build time 0 (1970), an extra `.sdata` section, no manifest, no debug directory, checksum 0
(and v2-v6 had their header edited for large address aware with no checksum written). Unsigned, new
and odd-looking is what reputation / machine-learning detections flag. The Roslyn exe has a real
build time, only `.text` / `.rsrc` / `.reloc`, the default Windows manifest and a debug directory;
`set_laa.py` now also writes the PE checksum. Same code: the same types and assembly references as
v6 (only the compilers' names for hidden closure classes differ). Not signed: a new unsigned exe
can still get Chrome's "not commonly downloaded" warning ("Keep") or a SmartScreen prompt until it
builds reputation; a code-signing certificate is the only full fix. A false positive can be reported
at https://www.microsoft.com/en-us/wdsi/filesubmission (Defender) and
https://safebrowsing.google.com/safebrowsing/report_error/ (Chrome).

## Merging folders (v8)

User: "make Sm4shExplorer able to merge every folder including the data folders, currently you can only merge
folders below certain hierarchies (ex. data, data(us_en), param)". Before, a folder dropped on the tree always
became a folder of its own name inside the target (dropping `param` on `param` made `param/param`), and nothing
could be dropped on the partitions (`data`, `data(us_en)`...: the drag check refused nodes without a parent).
Now (`Sm4shProject.MergeReason`, `UI/Main.cs treeView_DragOver`):
- the partitions take drops like any folder;
- a dropped folder is **merged** (its contents go straight into the target) when it has the target's own name
  (`data` on `data`, `data(us_en)` on `data(us_en)`, `param` on `param`, `fighter` on `fighter`...), or when it
  isn't a folder of the target and every folder in it already is (a mod package's top folder holding `ui/`,
  `param/`, `stage/`... dropped on `data`);
- anything else is added as before: a new fighter / stage / costume folder is still made inside the target
  (dropping `edge` on `fighter` gives `fighter/edge`, dropping `ui` on `data` gives `data/ui`, the same place).
- The log says when it merged and why. Folders themselves no longer log "forbidden extension".

Test: `merge_test.cs` (mono; compiled against the built exe) runs `MergeReason` and the real
`AddFileToWorkspace` on a fake workspace: 15 checks (the 9 decisions above and 6 copies), 0 failures.

    dotnet /usr/lib/dotnet/sdk/8.0.133/Roslyn/bincore/csc.dll -out:MergeTest.exe -r:Sm4shFileExplorer.exe \
        -r:/usr/lib/mono/4.5/System.Windows.Forms.dll -r:/usr/lib/mono/4.5/mscorlib.dll -r:/usr/lib/mono/4.5/System.dll \
        -r:/usr/lib/mono/4.5/System.Core.dll -nostdlib merge_test.cs
    mono MergeTest.exe EMPTY_DIR        # with Sm4shFileExplorer.exe and its DLLs next to MergeTest.exe

Build note: a fresh checkout needs the NuGet packages Microsoft.WindowsAPICodePack.Core / .Shell 1.1.0 unzipped
into `packages/` (the project's HintPaths).

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
