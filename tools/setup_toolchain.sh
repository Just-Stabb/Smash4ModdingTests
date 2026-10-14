#!/usr/bin/env bash
# Fetches Jam1Garner's MSC-C decompiler (mscdec) and compiler (msclang) into tools/.
set -euo pipefail
cd "$(dirname "$0")"
[ -d mscdec ]  || git clone --depth 1 https://github.com/jam1garner/mscdec
[ -d msclang ] || git clone --depth 1 https://github.com/jam1garner/msclang
python3 -c "import pycparser" 2>/dev/null || python3 -m pip install pycparser
echo "Decompile: python3 tools/mscdec/mscdec.py file.mscsb -o file.c"
echo "Compile:   python3 tools/msclang/msclang.py file.c -o file.mscsb"
