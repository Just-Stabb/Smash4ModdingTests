#!/bin/bash
# Builds latte-asm (decaf-emu's latte-assembler: Latte shader text -> GX2 .gsh; GPL-3.0) into
# tools/latte_dis/latte-asm, without its GLSL front end (glslang + AMD's shader analyzer). Needs
# build.sh's checkout (run it first); adds the assembler's sources and the header-only libraries it
# pins (cpp-peglib, excmd, spdlog) to tools/latte_dis/src (git-ignored).
set -e
cd "$(dirname "$0")"
[ -d src/decaf ] || ./build.sh
cd src
fetch() {  # dir url commit
  [ -d "$1" ] && return
  mkdir "$1" && git -C "$1" init -q && git -C "$1" remote add origin "$2"
  git -C "$1" fetch -q --depth 1 origin "$3" && git -C "$1" checkout -q FETCH_HEAD
}
git -C decaf sparse-checkout add tools/latte-assembler src/libgfd src/libdecaf/src/cafe/libraries/gx2 src/libcpu
fetch peglib https://github.com/yhirose/cpp-peglib.git 79f4d90c19a1ffad613c89b470e11b313275e982
fetch excmd https://github.com/exjam/excmd.git 930d0fa20ba053cf4796e56ec5ea930d68ebcb06
fetch spdlog https://github.com/gabime/spdlog.git eb3220622e73a4889eee355ffa37972b3cac3df5
A=decaf/tools/latte-assembler
mkdir -p asm_build
python3 - "$A" <<'EOF'
import sys
a = sys.argv[1]
src = open(a + '/src/main.cpp').read()
src = src.replace('#include "glsl_compiler.h"\n', '').replace('#include <glslang/Public/ShaderLang.h>\n', '')
i, j = src.index('      if (options.has("compile")) {'), src.index('      } else if (options.has("assemble")) {')
src = src[:i] + '      if (options.has("assemble")) {' + src[j + len('      } else if (options.has("assemble")) {'):]
open('asm_build/main.cpp', 'w').write(src)
open('asm_build/grammar.h', 'w').write('const char *LatteGrammar = R"(\n' + open(a + '/resources/grammar.txt').read() + ')";\n')
EOF
D=decaf/src
g++ -std=c++17 -O1 -w -DFMT_HEADER_ONLY -DSPDLOG_FMT_EXTERNAL -DSPDLOG_HEADER_ONLY \
  -Ifmt/include -Igsl-lite/include -Icnl/include -Ipeglib -Iexcmd/src -Ispdlog/include -Iasm_build \
  -I$A/src -I$D -I$D/libgfd -I$D/libgpu -I$D/libgpu/src \
  asm_build/main.cpp ../asm_support.cpp $(ls $A/src/*.cpp | grep -v -e /main.cpp -e glsl_compiler) \
  $D/libgfd/src/*.cpp $D/libgpu/src/latte/latte_instructions.cpp -o ../latte-asm
echo built "$(cd .. && pwd)/latte-asm"
