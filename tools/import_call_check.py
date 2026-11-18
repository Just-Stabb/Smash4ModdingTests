#!/usr/bin/env python3
"""Find cave code that calls an imported function (GX2*, OS*, ...) with a plain `bl` to the address the FILE's own
calls point at. That address is NOT the function at run time: Cemu resolves each import to an HLE entry of its own
and rewrites the game's REL24 calls at load (rpl.cpp: a relative `bl` when in reach, else an absolute `bla` to a
trampoline), and the file's targets lie in the grown text, i.e. other caves' code (0x04B7BD08 is in APC_CODE). A cave
calls an import through the run-time target of one of the game's own calls (tools/outline_shell_cave.py os_resolve)
or a relocated veneer (diag_crumbs_cave.py's OSReport). Outline_Shell v2-v5 called GX2 this way and crashed the game
at its first shell (the user's v5 crash log).

  python3 tools/import_call_check.py BASE.rpx PATCHED.rpx     # every changed word that is such a call
  direct_import_calls(base_path, words) -> [(address, import name)]  (words: {address: word}, a cave's build)
"""
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _target(at, w):
    off = w & 0x03FFFFFC
    if off & 0x02000000:
        off -= 0x04000000
    return (0 if w & 2 else at) + off


def file_import_targets(base_path):
    """{the file's bl target of an import: its name}, from the game's REL24 relocations against imports"""
    from diag_crumbs_test import import_relocs
    import kind_expand as K
    img = K.Image(base_path)
    out = {}
    for at, typ, _v, name in import_relocs(base_path):
        if typ == 10:
            out.setdefault(_target(at & ~3, img.w(at & ~3)), name)
    return out


def direct_import_calls(base_path, words):
    imp = file_import_targets(base_path)
    return [(a, imp[_target(a, w)]) for a, w in sorted(words.items())
            if (w >> 26) == 18 and w & 1 and _target(a, w) in imp]


def main():
    import kind_expand as K
    base, patched = K.Image(sys.argv[1]), K.Image(sys.argv[2])
    words = {}
    for a in range(0x02000000, 0x05000000, 4):
        try:
            w = patched.w(a)
        except KeyError:
            continue
        try:
            o = base.w(a)
        except KeyError:
            o = None
        if w != o:
            words[a] = w
    hits = direct_import_calls(sys.argv[1], words)
    for a, n in hits:
        print('0x%08X  bl %s (the file\'s target: not the function at run time)' % (a, n))
    print('%d direct import call(s)' % len(hits))
    sys.exit(1 if hits else 0)


if __name__ == '__main__':
    main()
