#!/bin/bash
# Builds latte-dis (Wii U GX2 / Latte shader disassembler, decaf-emu's libgpu disassembler; GPL-3.0)
# into tools/latte_dis/latte-dis. Fetches decaf-emu's sources and the library versions it pins
# (gsl-lite, cnl, fmt 8.1.1) into tools/latte_dis/src (git-ignored).
set -e
cd "$(dirname "$0")"
mkdir -p src && cd src
fetch() {  # dir url commit
  [ -d "$1" ] && return
  mkdir "$1" && git -C "$1" init -q && git -C "$1" remote add origin "$2"
  git -C "$1" fetch -q --depth 1 origin "$3" && git -C "$1" checkout -q FETCH_HEAD
}
if [ ! -d decaf ]; then
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/decaf-emu/decaf-emu.git decaf
  git -C decaf sparse-checkout set src/libgpu/latte src/libgpu/src/latte src/common
fi
fetch cnl https://github.com/johnmcfarlane/cnl.git 2dde6e62e608a4adc3c5504f067575efa4910568
fetch fmt https://github.com/fmtlib/fmt.git b6f4ceaed0a0a24ccf575fab6c56dd50ccf6f1a9
fetch gsl-lite https://github.com/gsl-lite/gsl-lite.git d6c8af99a1d95b3db36f26b4f22dc3bad89952de
D=decaf/src
g++ -std=c++20 -O1 -w -DFMT_HEADER_ONLY -Ifmt/include -Igsl-lite/include -Icnl/include -I$D -I$D/libgpu -I$D/libgpu/src \
  ../main.cpp $D/libgpu/src/latte/latte_disassembler*.cpp $D/libgpu/src/latte/latte_instructions.cpp -o ../latte-dis
echo built "$(cd .. && pwd)/latte-dis"
