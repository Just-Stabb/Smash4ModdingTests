#!/bin/bash
# Builds envydis (envytools' NVIDIA GPU disassembler, MIT; Maxwell = -m gm107: the Switch's GPU) into
# tools/maxwell_dis/envydis. Needs cmake, flex, bison, libxml2-dev. Sources in tools/maxwell_dis/src
# (git-ignored).
set -e
cd "$(dirname "$0")"
[ -d src ] || git clone -q --depth 1 https://github.com/envytools/envytools.git src
mkdir -p src/build && cd src/build
cmake .. -DCMAKE_BUILD_TYPE=Release > /dev/null
make -j8 envydis > /dev/null
cp envydis/envydis ../../envydis
echo built "$(cd ../.. && pwd)/envydis"
