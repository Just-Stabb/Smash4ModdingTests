#!/usr/bin/env python3
"""Mark a 32-bit Windows exe large address aware (4 GB of address space on 64-bit Windows instead
of 2 GB), like `editbin /LARGEADDRESSAWARE`.

  python3 tools/sm4shexplorer/set_laa.py Sm4shFileExplorer.exe
"""
import struct
import sys

d = bytearray(open(sys.argv[1], 'rb').read())
pe = struct.unpack('<I', d[0x3C:0x40])[0]
assert d[pe:pe + 4] == b'PE\0\0', 'not a PE file'
ch = struct.unpack('<H', d[pe + 22:pe + 24])[0]
d[pe + 22:pe + 24] = struct.pack('<H', ch | 0x20)
open(sys.argv[1], 'wb').write(d)
print('characteristics 0x%04X -> 0x%04X' % (ch, ch | 0x20))
