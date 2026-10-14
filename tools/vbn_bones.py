#!/usr/bin/env python3
"""Lists the bones in a Smash 4 model.vbn: index (what ModelModule takes), name, parent.

Usage: python3 tools/vbn_bones.py path/to/model.vbn
"""
import struct
import sys


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    d = open(sys.argv[1], 'rb').read()
    e = '<' if d[:4] == b' NBV' else '>'
    count = struct.unpack(e + 'I', d[8:12])[0]
    off = 28
    bones = []
    for _ in range(count):
        name = d[off:off + 64].split(b'\0')[0].decode('ascii', 'replace')
        _type, parent, _hash = struct.unpack(e + 'IiI', d[off + 64:off + 76])
        bones.append((name, parent))
        off += 76
    print("| Index | Bone | Parent |")
    print("|---|---|---|")
    for i, (name, parent) in enumerate(bones):
        pname = bones[parent][0] if 0 <= parent < count else "-"
        print("| 0x%X | %s | %s |" % (i, name, pname))


if __name__ == "__main__":
    main()
