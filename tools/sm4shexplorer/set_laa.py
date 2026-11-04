#!/usr/bin/env python3
"""Mark a 32-bit Windows exe large address aware (4 GB of address space on 64-bit Windows instead
of 2 GB), like `editbin /LARGEADDRESSAWARE`, and write its PE checksum (as `editbin /RELEASE`):
a header edited after the build with a stale checksum is one more thing antivirus heuristics
weigh.

  python3 tools/sm4shexplorer/set_laa.py Sm4shFileExplorer.exe
"""
import struct
import sys


def pe_checksum(d, off):
    """the PE optional header checksum (imagehlp's CheckSumMappedFile): 16-bit folded sum of the file
    with its own field as 0, plus the file size"""
    b = bytes(d[:off]) + b'\0\0\0\0' + bytes(d[off + 4:]) + b'\0' * (len(d) % 2)
    s = 0
    for (w,) in struct.iter_unpack('<H', b):
        s += w
        s = (s & 0xFFFF) + (s >> 16)
    return ((s & 0xFFFF) + (s >> 16) + len(d)) & 0xFFFFFFFF


d = bytearray(open(sys.argv[1], 'rb').read())
pe = struct.unpack('<I', d[0x3C:0x40])[0]
assert d[pe:pe + 4] == b'PE\0\0', 'not a PE file'
ch = struct.unpack('<H', d[pe + 22:pe + 24])[0]
d[pe + 22:pe + 24] = struct.pack('<H', ch | 0x20)
off = pe + 24 + 64
s = pe_checksum(d, off)
d[off:off + 4] = struct.pack('<I', s)
open(sys.argv[1], 'wb').write(d)
print('characteristics 0x%04X -> 0x%04X, checksum 0x%08X' % (ch, ch | 0x20, s))
