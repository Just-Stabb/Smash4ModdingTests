#!/usr/bin/env python3
"""Read / write the game's MSBT text files (ui/message/*.msbt: big-endian, UTF-16, sections LBL1 /
ATR1 / TXT2). Little-endian files (Smash 3DS's) are read too: texts are kept big-endian, so build() writes
the Wii U form (header byte-order mark and encoding fields big-endian).

  python3 tools/msbt.py FILE [PATTERN]     list labels (containing PATTERN) and their text
"""
import struct
import sys


def _hash(label, groups):
    h = 0
    for c in label.encode('ascii'):
        h = (h * 0x492 + c) & 0xFFFFFFFF
    return h % groups


class Msbt:
    def __init__(self, data):
        assert data[:8] == b'MsgStdBn' and data[8:10] in (b'\xfe\xff', b'\xff\xfe'), 'not an MSBT'
        e = '>' if data[8:10] == b'\xfe\xff' else '<'
        self.endian = e
        self.header = bytearray(data[:0x20])
        if e == '<':
            # the Wii U header: BOM fe ff, the u16 / u32 fields big-endian
            self.header[8:10] = b'\xfe\xff'
            for o, f in ((0xE, 'H'), (0x12, 'I')):
                n = struct.calcsize(f)
                self.header[o:o + n] = struct.pack('>' + f, struct.unpack('<' + f, data[o:o + n])[0])
        self.groups = 0
        self.labels = {}            # label -> text index
        self.texts = []             # raw UTF-16 bytes, without the terminator
        self.atr = None
        o = 0x20
        while o < len(data):
            mag, size = data[o:o + 4], struct.unpack(e + 'I', data[o + 4:o + 8])[0]
            body = data[o + 16:o + 16 + size]
            if mag == b'LBL1':
                self.groups = struct.unpack(e + 'I', body[:4])[0]
                for g in range(self.groups):
                    n, off = struct.unpack(e + 'II', body[4 + 8 * g:12 + 8 * g])
                    for _ in range(n):
                        ln = body[off]
                        name = body[off + 1:off + 1 + ln].decode('ascii')
                        self.labels[name] = struct.unpack(e + 'I', body[off + 1 + ln:off + 5 + ln])[0]
                        off += 5 + ln
            elif mag == b'ATR1':
                self.atr = body if e == '>' else struct.pack('>II', *struct.unpack('<II', body[:8])) + body[8:]
            elif mag == b'TXT2':
                n = struct.unpack(e + 'I', body[:4])[0]
                offs = list(struct.unpack(e + '%dI' % n, body[4:4 + 4 * n])) + [len(body)]
                for i in range(n):
                    t = body[offs[i]:offs[i + 1]]
                    if t.endswith(b'\0\0'):
                        t = t[:-2]
                    if e == '<':        # UTF-16 units (text and control codes alike) to big-endian
                        t = b''.join(t[k + 1:k + 2] + t[k:k + 1] for k in range(0, len(t) - 1, 2))
                    self.texts.append(t)
            o += 16 + size
            o = (o + 15) & ~15

    def text(self, label):
        return self.texts[self.labels[label]].decode('utf-16-be')

    def set(self, label, text):
        raw = text.encode('utf-16-be')
        if label in self.labels:
            self.texts[self.labels[label]] = raw
        else:
            self.labels[label] = len(self.texts)
            self.texts.append(raw)

    def build(self):
        def section(mag, body):
            out = mag + struct.pack('>I', len(body)) + b'\0' * 8 + body
            return out + b'\xab' * (-len(out) % 16)
        buckets = [[] for _ in range(self.groups)]
        for name, idx in self.labels.items():
            buckets[_hash(name, self.groups)].append((name, idx))
        lbl = bytearray(struct.pack('>I', self.groups))
        entries = bytearray()
        base = 4 + 8 * self.groups
        for b in buckets:
            lbl += struct.pack('>II', len(b), base + len(entries))
            for name, idx in b:
                entries += bytes([len(name)]) + name.encode('ascii') + struct.pack('>I', idx)
        lbl += entries
        n = len(self.texts)
        atr = struct.pack('>II', n, 0) if self.atr is not None and struct.unpack('>I', self.atr[4:8])[0] == 0 \
            else self.atr
        txt = bytearray(struct.pack('>I', n))
        pos = 4 + 4 * n
        body = bytearray()
        for t in self.texts:
            txt += struct.pack('>I', pos + len(body))
            body += t + b'\0\0'
        txt += body
        out = section(b'LBL1', bytes(lbl)) + section(b'ATR1', atr) + section(b'TXT2', bytes(txt))
        hdr = bytearray(self.header)
        hdr[0x12:0x16] = struct.pack('>I', 0x20 + len(out))
        return bytes(hdr) + out


def main():
    m = Msbt(open(sys.argv[1], 'rb').read())
    pat = sys.argv[2] if len(sys.argv) > 2 else ''
    for name in sorted(m.labels):
        if pat in name:
            print('%s = %r' % (name, m.text(name)))


if __name__ == '__main__':
    main()
