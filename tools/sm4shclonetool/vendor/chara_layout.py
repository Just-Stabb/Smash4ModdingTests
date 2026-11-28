"""Lumen (.lm) files: read the character select's face-layout sprite (frames num_NNN, places face_NNN) and simulate
its display list.

Adapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; the tool
sets the code addresses itself, see its README "The executable")."""
import math
import struct
import sys
HEADER = 64
T_SYMBOLS, T_TRANSFORMS, T_POSITIONS = (61441, 61443, 61699)
T_SPRITE, T_FRAME, T_LABEL, T_PLACE, T_REMOVE, T_END = (39, 1, 43, 4, 5, 65280)
T_KEYFRAME = 61701
NONE = 4294967295
POS_FLAG = 2147483648

def read_tags(d):
    out, o = ([], HEADER)
    while o < len(d):
        t, n = struct.unpack('>II', d[o:o + 8])
        out.append([t, bytearray(d[o + 8:o + 8 + 4 * n])])
        o += 8 + 4 * n
        if t == T_END:
            break
    assert o == len(d), (hex(o), len(d))
    return out

def write(head, tags):
    body = b''.join((struct.pack('>II', t, len(b) // 4) + bytes(b) for t, b in tags))
    h = bytearray(head)
    struct.pack_into('>I', h, 28, HEADER + len(body))
    return bytes(h) + body

def words(b):
    return list(struct.unpack('>%dI' % (len(b) // 4), b))

def pack(w):
    return bytearray(struct.pack('>%dI' % len(w), *w))

def symbols(b):
    n = struct.unpack('>I', b[:4])[0]
    o, s = (4, [])
    for _ in range(n):
        ln = struct.unpack('>I', b[o:o + 4])[0]
        o += 4
        s.append(bytes(b[o:o + ln]).decode('cp932', 'replace'))
        o += ln + 4 & ~3
    return s

def table(b, k):
    n = struct.unpack('>I', b[:4])[0]
    return [struct.unpack('>%df' % k, bytes(b[4 + 4 * k * j:4 + 4 * k * (j + 1)])) for j in range(n)]

def append_rows(tag, rows, k):
    n = struct.unpack('>I', tag[1][:4])[0]
    for r in rows:
        tag[1] += struct.pack('>%df' % k, *r)
    struct.pack_into('>I', tag[1], 0, n + len(rows))
    return list(range(n, n + len(rows)))

class Lm:

    def __init__(self, data):
        self.head = data[:HEADER]
        self.tags = read_tags(data)
        self.sy = symbols(self.tags[0][1])
        self.ti = {t: i for i, (t, _) in reversed(list(enumerate(self.tags)))}
        assert self.tags[self.ti[T_POSITIONS]][0] == T_POSITIONS

    def data(self):
        return write(self.head, self.tags)

    def layout_sprite(self):
        i = 0
        while i < len(self.tags):
            if self.tags[i][0] == T_SPRITE:
                j = i + 1
                while j < len(self.tags) and self.tags[j][0] in (T_FRAME, T_LABEL, T_PLACE, T_REMOVE, 12, 61701, 61460):
                    j += 1
                labs = [self.sy[words(b)[0]] for t, b in self.tags[i + 1:j] if t == T_LABEL]
                names = [self.sy[words(b)[3]] for t, b in self.tags[i + 1:j] if t == T_PLACE and words(b)[3]]
                if any((x.startswith('num_') for x in labs)) and any((x.startswith('face_0') for x in names)):
                    return (i, j)
                i = j
            else:
                i += 1
        raise SystemExit('no face layout sprite')

    def frames(self):
        a, b = self.layout_sprite()
        fr, labels = ([], {})
        i = a + 1
        while i < b:
            t, body = self.tags[i]
            if t == T_LABEL:
                w = words(body)
                labels[w[1]] = self.sy[w[0]]
            elif t in (T_FRAME, T_KEYFRAME):
                n = words(body)[1]
                if t == T_FRAME:
                    fr.append([i, list(range(i + 1, i + 1 + n))])
                i += 1 + n
                continue
            i += 1
        return (fr, labels)

    def keyframes(self):
        a, b = self.layout_sprite()
        out = {}
        i = a + 1
        while i < b:
            t, body = self.tags[i]
            if t in (T_FRAME, T_KEYFRAME):
                w = words(body)
                if t == T_KEYFRAME:
                    out[w[0]] = list(range(i + 1, i + 1 + w[1]))
                i += 1 + w[1]
                continue
            i += 1
        return out

    def keyframe_state(self, f):
        return {words(self.tags[i][1])[5] >> 16: words(self.tags[i][1])[7] for i in self.keyframes()[f] if self.tags[i][0] == T_PLACE}

    def simulate(self):
        pos = table(self.tags[self.ti[T_POSITIONS]][1], 2)
        xf = table(self.tags[self.ti[T_TRANSFORMS]][1], 6)

        def mat(i):
            if i == NONE:
                return None
            if i & POS_FLAG:
                x, y = pos[i & 65535]
                return (1.0, 0.0, 0.0, 1.0, x, y)
            return xf[i]
        state, out = ({}, [])
        fr, _ = self.frames()
        for _fi, kids in fr:
            for i in kids:
                t, body = self.tags[i]
                w = words(body)
                if t == T_REMOVE:
                    state.pop(w[1] >> 16, None)
                elif t == T_PLACE:
                    d, mode = (w[5] >> 16, w[4] >> 16)
                    if mode == 1 or d not in state:
                        state[d] = dict(char=w[0], name=self.sy[w[3]] if w[3] else '', m=mat(w[7]))
                    elif w[7] != NONE:
                        state[d] = dict(state[d], m=mat(w[7]))
            out.append({d: dict(e) for d, e in state.items()})
        return out

def faces(st):
    return {int(e['name'][5:]): (d, e) for d, e in st.items() if e['name'].startswith('face_0')}
