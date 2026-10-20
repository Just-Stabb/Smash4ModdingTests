# Sm4shExplorer: faster builds and "Extract vanilla"

`sm4shexplorer-faster.patch` (3 commits) applies to https://github.com/thefungus/Sm4shExplorer
(`e349175`, the latest commit): `git am sm4shexplorer-faster.patch`. Built with mono's `xbuild`
(`/p:Configuration=Release`), then `python3 tools/sm4shexplorer/set_laa.py Sm4shFileExplorer.exe`;
the exe is in `build/sm4shexplorer_faster_v3.zip` (replaces `Sm4shFileExplorer.exe`; the DLLs and
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

## Not tested in a real build

Compiled and logic-checked here (no game dump in this environment): try it on a copy of a
workspace and compare an export with the old exe's before relying on it.
