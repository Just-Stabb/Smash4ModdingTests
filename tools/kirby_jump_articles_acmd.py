#!/usr/bin/env python3
"""Kirby jumps ACMD edit: remove the test GENERATE_ARTICLE spawns from the air jumps.

  python3 tools/kirby_jump_articles_acmd.py IN_game.bin OUT_game.bin

jumpaerialf3 / f4 / f5 each spawned six articles (IDs 6-0xB, 0xC-0x11, 0x12-0x17) on frames
1, 8, 16, 25, 33 and 40; those were left in for testing. Everything else (flags,
Model_Changer, frame timing) stays.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

GEN = acmd.BY_NAME["generate_article"]
SCRIPTS = ["jumpaerialf1", "jumpaerialf2", "jumpaerialf3", "jumpaerialf4", "jumpaerialf5", "jumpf", "jumpb"]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = acmd.ACMDFile.load(src)
    for name in SCRIPTS:
        s = f.script(name)
        if s is not None:
            s[:] = [c for c in s if c.ident != GEN]
    f.save(dst)


if __name__ == "__main__":
    main()
