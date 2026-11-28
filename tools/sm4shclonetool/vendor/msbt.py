"""MSBT text files (labels, UTF-16 texts): read and write.

Adapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; the tool
sets the code addresses itself, see its README "The executable")."""
import struct
import sys

def _hash(label, groups):
    h = 0
    for c in label.encode('ascii'):
        h = h * 1170 + c & 4294967295
    return h % groups

class Msbt:

    def __init__(self, data):
        assert data[:8] == b'MsgStdBn' and data[8:10] in (b'\xfe\xff', b'\xff\xfe'), 'not an MSBT'
        e = '>' if data[8:10] == b'\xfe\xff' else '<'
        self.endian = e
        self.header = bytearray(data[:32])
        if e == '<':
            self.header[8:10] = b'\xfe\xff'
            for o, f in ((14, 'H'), (18, 'I')):
                n = struct.calcsize(f)
                self.header[o:o + n] = struct.pack('>' + f, struct.unpack('<' + f, data[o:o + n])[0])
        self.groups = 0
        self.labels = {}
        self.texts = []
        self.atr = None
        o = 32
        while o < len(data):
            mag, size = (data[o:o + 4], struct.unpack(e + 'I', data[o + 4:o + 8])[0])
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
                    if t.endswith(b'\x00\x00'):
                        t = t[:-2]
                    if e == '<':
                        t = b''.join((t[k + 1:k + 2] + t[k:k + 1] for k in range(0, len(t) - 1, 2)))
                    self.texts.append(t)
            o += 16 + size
            o = o + 15 & ~15

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
            out = mag + struct.pack('>I', len(body)) + b'\x00' * 8 + body
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
        atr = struct.pack('>II', n, 0) if self.atr is not None and struct.unpack('>I', self.atr[4:8])[0] == 0 else self.atr
        txt = bytearray(struct.pack('>I', n))
        pos = 4 + 4 * n
        body = bytearray()
        for t in self.texts:
            txt += struct.pack('>I', pos + len(body))
            body += t + b'\x00\x00'
        txt += body
        out = section(b'LBL1', bytes(lbl)) + section(b'ATR1', atr) + section(b'TXT2', bytes(txt))
        hdr = bytearray(self.header)
        hdr[18:22] = struct.pack('>I', 32 + len(out))
        return bytes(hdr) + out

def main():
    m = Msbt(open(sys.argv[1], 'rb').read())
    pat = sys.argv[2] if len(sys.argv) > 2 else ''
    for name in sorted(m.labels):
        if pat in name:
            print('%s = %r' % (name, m.text(name)))
if __name__ == '__main__':
    main()
