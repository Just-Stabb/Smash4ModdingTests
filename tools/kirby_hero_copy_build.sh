#!/bin/sh
# Kirby's MSC for the two Hero / Sephiroth copy installs (fighters/kirby/specials.md "Hero copy fix v1"):
#   B (exe_v46e, the v6 sword models): fighters/kirby/kirby.c as it is;
#   A (exe_v45g, no held sword): the same with khm_sword_on() 0 (the sword spells never drawn).
#   sh tools/kirby_hero_copy_build.sh OUT_DIR   -> OUT_DIR/kirby_A.mscsb, OUT_DIR/kirby_B.mscsb
set -e
T=$(dirname "$0")
OUT=${1:?OUT_DIR}
mkdir -p "$OUT"
python3 "$T/msclang/msclang.py" -x "$T/mscinfo.xml" "$T/../fighters/kirby/kirby.c" -o "$OUT/kirby_B.mscsb"
sed 's/^int khm_sword_on() { return 0x1; }/int khm_sword_on() { return 0; }/' "$T/../fighters/kirby/kirby.c" > "$OUT/kirby_A.c"
grep -q '^int khm_sword_on() { return 0; }' "$OUT/kirby_A.c"
python3 "$T/msclang/msclang.py" -x "$T/mscinfo.xml" "$OUT/kirby_A.c" -o "$OUT/kirby_A.mscsb"
