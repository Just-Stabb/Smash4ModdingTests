#!/usr/bin/env python3
"""Rewrite an RPX with its sections packed, removing dead space.

  python3 tools/rpx_compact.py IN.rpx OUT.rpx

rpx_patch.py moves a section that no longer fits in its place (a grown code section) to the end of
the file and zero-fills its old space; over many builds those dead copies made Smash 4's cross_f.rpx
grow from ~22 MB to over 300 MB. This keeps the ELF header and the section header table where they
are, lays every section's file data out again in its current file order (64-byte aligned) right
after them, updates the section offsets and cuts the file to its new end. The section data bytes
themselves are copied unchanged (so every CRC and the file info stay valid); the result is checked
section by section against the input.
"""
import struct
import sys

ALIGN = 64


def load(d):
    if d[:4] != b'\x7fELF':
        sys.exit('not an ELF/RPX file')
    shoff, = struct.unpack('>I', d[0x20:0x24])
    shentsize, shnum = struct.unpack('>HH', d[0x2E:0x32])
    secs = [list(struct.unpack('>10I', d[shoff + i * shentsize:shoff + i * shentsize + 40])) for i in range(shnum)]
    return shoff, shentsize, secs


def compact(d):
    shoff, shentsize, secs = load(d)
    head_end = max(0x34, shoff + shentsize * len(secs))
    with_data = [i for i, s in enumerate(secs) if s[4] and s[5] and s[1] != 8]   # NOBITS has no file data
    first = min((secs[i][4] for i in with_data), default=head_end)
    assert first >= head_end, 'section data before the header table end: not handled'
    out = bytearray(d[:head_end])
    new_secs = [list(s) for s in secs]
    for i in sorted(with_data, key=lambda i: secs[i][4]):
        pos = (len(out) + ALIGN - 1) & ~(ALIGN - 1)
        out += b'\0' * (pos - len(out))
        off, size = secs[i][4], secs[i][5]
        out += d[off:off + size]
        new_secs[i][4] = pos
    for i, s in enumerate(new_secs):
        struct.pack_into('>10I', out, shoff + i * shentsize, *s)
    return bytes(out), secs, new_secs


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    d = open(sys.argv[1], 'rb').read()
    out, old, new = compact(d)
    for i, (a, b) in enumerate(zip(old, new)):
        if a[4] and a[5] and a[1] != 8:
            assert d[a[4]:a[4] + a[5]] == out[b[4]:b[4] + b[5]], 'section %d differs' % i
        assert a[:4] + a[5:] == b[:4] + b[5:], 'section %d header changed beyond its offset' % i
    open(sys.argv[2], 'wb').write(out)
    print('%s: %d -> %d bytes (sections verified)' % (sys.argv[2], len(d), len(out)))


if __name__ == '__main__':
    main()
