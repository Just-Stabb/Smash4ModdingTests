#!/bin/sh
# Builds vfx_trace.dll (an OpenSmash-Ultimate mod for Windows) on Linux with clang + lld, no Windows SDK:
#   tools/opensmash/build_vfx_trace.sh OPENSMASH_DIR OUT_DIR
# OPENSMASH_DIR: a checkout of OpenSmash-Ultimate/ssbu-recomp (its fighter_sdk/include/hook.h).
# On Windows the port's own tool builds the same source: python fighter_sdk\tools\build_mod.py vfx_trace.cpp <folder>
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
SDK=${1:?OpenSmash checkout}/fighter_sdk/include
OUT=${2:?output folder}
mkdir -p "$OUT"
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
printf 'LIBRARY kernel32.dll\nEXPORTS\nCreateFileA\nWriteFile\nCloseHandle\nGetEnvironmentVariableA\nVirtualQuery\nAcquireSRWLockExclusive\nReleaseSRWLockExclusive\nGetModuleFileNameA\nGetModuleHandleExA\nQueryPerformanceCounter\n' > "$T/kernel32.def"
llvm-dlltool -m i386:x86-64 -d "$T/kernel32.def" -l "$T/kernel32.lib"
clang++ --target=x86_64-pc-windows-msvc -std=c++14 -O2 -ffreestanding -fno-exceptions -fno-rtti -mno-stack-arg-probe \
    -Wall -Wextra -Wno-unused-parameter -DVFX_FREESTANDING -I "$SDK" -c "$HERE/vfx_trace.cpp" -o "$T/vfx_trace.o"
lld-link /dll /entry:DllMain /nodefaultlib /machine:x64 /out:"$OUT/vfx_trace.dll" "$T/vfx_trace.o" "$T/kernel32.lib"
rm -f "$OUT/vfx_trace.lib" "$OUT/vfx_trace.exp"
echo "built $OUT/vfx_trace.dll"
