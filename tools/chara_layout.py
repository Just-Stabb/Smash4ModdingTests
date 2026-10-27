#!/usr/bin/env python3
"""Character select grid arrangements in ui/lumen/chara/chara.lm (Lumen LMB): rewrite the
`num_NNN` frames of the face-layout sprite so every count from FIRST up has a clean grid.

  python3 tools/chara_layout.py IN.lm OUT.lm [--first 58] [--last N] [--style user4|user5] [--png sheet.png]

--last: only the counts up to N (the file grows ~3 KB a count; all of 58-96 is +130 KB)

The game shows `num_%03d` with the number of character select entries (0x028BEE20) and binds
face_001.. face_NNN in list order (0x028BE920). Each num_ frame of the layout sprite (the one with
the num_ labels whose placements are named face_NNN) is a delta on the previous frame; here every
face of a rewritten frame gets an explicit placement (existing tags re-aimed, move tags added),
so each rewritten frame no longer depends on the one before it.

Each num_ frame also has a keyframe (tag 0xF105, after the sprite's last frame): its full state,
which a goto shows; a rewritten frame's keyframe gets the same placements (v2 left them alone and,
reading the last frame's children up to the sprite's end, gave every keyframe num_096's).

Style user4 (the user's honeycomb CSS): 4 rows, odd rows from x -869.5, even rows from -807.5,
124.5 apart, rows at y -156.5 / -51 / 54.5 / 160 (their num_057); 15 + 14 + 15 + 14 = 58 fit at
scale 1, the last two entries at the right end of rows 3 and 4 (as their num_057). Above 58 the
grid gets more columns and is scaled down to the same width (transform matrices).

Style user5 (Squirtle on, `--first 63`): 5 rows in the 4 rows' height, icons at 0.75, rows of c / c - 1
(c >= 13) centred on the 4-row grid's centre, the last two entries at the right ends of rows 4 and 5;
past 19 columns (93 entries) narrower again to the 4-row grid's width.
"""
import math
import struct
import sys

HEADER = 0x40
T_SYMBOLS, T_TRANSFORMS, T_POSITIONS = 0xF001, 0xF003, 0xF103
T_SPRITE, T_FRAME, T_LABEL, T_PLACE, T_REMOVE, T_END = 0x27, 0x1, 0x2B, 0x4, 0x5, 0xFF00
T_KEYFRAME = 0xF105
NONE = 0xFFFFFFFF
POS_FLAG = 0x80000000


def read_tags(d):
    out, o = [], HEADER
    while o < len(d):
        t, n = struct.unpack('>II', d[o:o + 8])
        out.append([t, bytearray(d[o + 8:o + 8 + 4 * n])])
        o += 8 + 4 * n
        if t == T_END:
            break
    assert o == len(d), (hex(o), len(d))
    return out


def write(head, tags):
    body = b''.join(struct.pack('>II', t, len(b) // 4) + bytes(b) for t, b in tags)
    h = bytearray(head)
    struct.pack_into('>I', h, 0x1C, HEADER + len(body))
    return bytes(h) + body


def words(b):
    return list(struct.unpack('>%dI' % (len(b) // 4), b))


def pack(w):
    return bytearray(struct.pack('>%dI' % len(w), *w))


def symbols(b):
    n = struct.unpack('>I', b[:4])[0]
    o, s = 4, []
    for _ in range(n):
        ln = struct.unpack('>I', b[o:o + 4])[0]
        o += 4
        s.append(bytes(b[o:o + ln]).decode('cp932', 'replace'))
        o += (ln + 4) & ~3
    return s


def table(b, k):
    n = struct.unpack('>I', b[:4])[0]
    return [struct.unpack('>%df' % k, bytes(b[4 + 4 * k * j:4 + 4 * k * (j + 1)])) for j in range(n)]


def append_rows(tag, rows, k):
    """append float rows to a positions (k=2) / transforms (k=6) table tag; return their indices"""
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
        """tag index range of the sprite whose labels are num_NNN and whose places are face_NNN"""
        i = 0
        while i < len(self.tags):
            if self.tags[i][0] == T_SPRITE:
                j = i + 1
                while j < len(self.tags) and self.tags[j][0] in (T_FRAME, T_LABEL, T_PLACE, T_REMOVE, 0xC, 0xF105, 0xF014):
                    j += 1
                labs = [self.sy[words(b)[0]] for t, b in self.tags[i + 1:j] if t == T_LABEL]
                names = [self.sy[words(b)[3]] for t, b in self.tags[i + 1:j] if t == T_PLACE and words(b)[3]]
                if any(x.startswith('num_') for x in labs) and any(x.startswith('face_0') for x in names):
                    return i, j
                i = j
            else:
                i += 1
        raise SystemExit('no face layout sprite')

    def frames(self):
        """[(frame tag index, [tag indices of its children])], labels {frame: name}; a frame's
        children are the T_FRAME's count of tags after it (the sprite's keyframes follow its last
        frame: keyframes())"""
        a, b = self.layout_sprite()
        fr, labels = [], {}
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
        return fr, labels

    def keyframes(self):
        """{frame: [tag indices of its keyframe's placements]}: the full display state of each frame,
        which a goto (the game's gotoAndStop num_NNN) shows"""
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
        """{depth: transform reference} of frame f's keyframe placements"""
        return {words(self.tags[i][1])[5] >> 16: words(self.tags[i][1])[7]
                for i in self.keyframes()[f] if self.tags[i][0] == T_PLACE}

    def simulate(self):
        """the display state after each frame: [{depth: {char, name, m}}]"""
        pos = table(self.tags[self.ti[T_POSITIONS]][1], 2)
        xf = table(self.tags[self.ti[T_TRANSFORMS]][1], 6)

        def mat(i):
            if i == NONE:
                return None
            if i & POS_FLAG:
                x, y = pos[i & 0xFFFF]
                return (1.0, 0.0, 0.0, 1.0, x, y)
            return xf[i]
        state, out = {}, []
        fr, _ = self.frames()
        for _fi, kids in fr:
            for i in kids:
                t, body = self.tags[i]
                w = words(body)
                if t == T_REMOVE:
                    state.pop(w[1] >> 16, None)
                elif t == T_PLACE:
                    d, mode = w[5] >> 16, w[4] >> 16
                    if mode == 1 or d not in state:
                        state[d] = dict(char=w[0], name=self.sy[w[3]] if w[3] else '', m=mat(w[7]))
                    elif w[7] != NONE:
                        state[d] = dict(state[d], m=mat(w[7]))
            out.append({d: dict(e) for d, e in state.items()})
        return out


def keyframes_match(lm, states, frames=None):
    """every keyframe (of `frames`, default all) = the state its frames build (the user's file holds to it)"""
    pos = table(lm.tags[lm.ti[T_POSITIONS]][1], 2)
    xf = table(lm.tags[lm.ti[T_TRANSFORMS]][1], 6)

    def mat(i):
        if i == NONE:
            return None
        if i & POS_FLAG:
            x, y = pos[i & 0xFFFF]
            return (1.0, 0.0, 0.0, 1.0, x, y)
        return xf[i]
    return all({d: mat(r) for d, r in lm.keyframe_state(f).items()} == {d: e['m'] for d, e in states[f].items()}
               for f in (range(len(states)) if frames is None else frames))


def faces(st):
    return {int(e['name'][5:]): (d, e) for d, e in st.items() if e['name'].startswith('face_0')}


# ---------------------------------------------------------------- layouts
ROWS_Y = [-156.5, -51.0, 54.5, 160.0]
ODD_X0, EVEN_X0, DX = -869.5, -807.5, 124.5


def user4(n):
    """[(x, y, scale)] for faces 1..n: the user's 4-row honeycomb, scaled down past 58"""
    c = max(15, math.ceil((n + 2) / 4))           # odd-row columns; capacity 4c - 2
    s = 14.0 / (c - 1)
    cx, cy = (ODD_X0 + ODD_X0 + 14 * DX) / 2, (ROWS_Y[0] + ROWS_Y[3]) / 2
    dx, dy = DX * s, (ROWS_Y[1] - ROWS_Y[0]) * s

    def slot(r, k):
        if s == 1.0:
            return ((ODD_X0 if r % 2 == 0 else EVEN_X0) + k * DX, ROWS_Y[r])
        x0 = cx - (c - 1) * dx / 2 + (dx / 2 if r % 2 else 0)
        return (x0 + k * dx, cy + (r - 1.5) * dy)
    caps = [c, c - 1, c, c - 1]
    # the last two entries at the right ends of rows 3 and 4 (as the user's num_057)
    ends = [slot(2, caps[2] - 1), slot(3, caps[3] - 1)]
    fill = caps[:2] + [caps[2] - 1, caps[3] - 1]
    out, rest = [], n - 2
    for r in range(4):
        for k in range(fill[r]):
            if len(out) < rest:
                out.append(slot(r, k))
    assert len(out) == rest, (n, len(out))
    return [(x, y, s) for x, y in out + ends]


def user5(n):
    """[(x, y, scale)] for faces 1..n: the honeycomb in 5 rows in the 4 rows' height (icons at 0.75),
    rows of c / c - 1 centred on the 4-row grid's centre, narrower still past 19 columns"""
    c = max(13, math.ceil((n + 2) / 5))           # odd-row columns; capacity 5c - 2
    s = min(0.75, 14.0 / (c - 1))
    cx, cy = (ODD_X0 + ODD_X0 + 14 * DX) / 2, (ROWS_Y[0] + ROWS_Y[3]) / 2
    dx, dy = DX * s, (ROWS_Y[3] - ROWS_Y[0]) / 4

    def slot(r, k):
        x0 = cx - (c - 1) * dx / 2 + (dx / 2 if r % 2 else 0)
        return (x0 + k * dx, cy + (r - 2) * dy)
    caps = [c, c - 1, c, c - 1, c]
    # the last two entries at the right ends of rows 4 and 5, as user4 keeps them on its last two rows
    ends = [slot(3, caps[3] - 1), slot(4, caps[4] - 1)]
    fill = caps[:3] + [caps[3] - 1, caps[4] - 1]
    out, rest = [], n - 2
    for r in range(5):
        for k in range(fill[r]):
            if len(out) < rest:
                out.append(slot(r, k))
    assert len(out) == rest, (n, len(out))
    return [(x, y, s) for x, y in out + ends]


STYLES = {'user4': user4, 'user5': user5}


def relayout(lm, first, style, last=None):
    fr, labels = lm.frames()
    states = lm.simulate()
    changed = []
    for fi in range(len(fr)):
        fr, labels = lm.frames()          # tag indices move with every insert
        ftag, kids = fr[fi]
        lab = labels.get(fi, '')
        if not lab.startswith('num_'):
            continue
        n = int(lab[4:])
        if n < first or (last and n > last):
            continue
        st = faces(states[fi])
        assert sorted(st) == list(range(1, n + 1)), (lab, sorted(st)[:5], len(st))
        want = style(n)
        pos_rows, xf_rows, keys = [], [], []
        for k in range(1, n + 1):
            x, y, s = want[k - 1]
            if s == 1.0:
                keys.append(('p', len(pos_rows)))
                pos_rows.append((x, y))
            else:
                keys.append(('x', len(xf_rows)))
                xf_rows.append((s, 0.0, 0.0, s, x, y))
        pidx = append_rows(lm.tags[lm.ti[T_POSITIONS]], pos_rows, 2)
        xidx = append_rows(lm.tags[lm.ti[T_TRANSFORMS]], xf_rows, 6)
        ref = {}
        for k, (kind, j) in zip(range(1, n + 1), keys):
            ref[k] = (POS_FLAG | pidx[j]) if kind == 'p' else xidx[j]
        by_depth = {d: k for k, (d, _e) in st.items()}
        touched = set()
        for i in kids:
            t, body = lm.tags[i]
            if t != T_PLACE:
                continue
            w = words(body)
            d = w[5] >> 16
            if d in by_depth:
                w[7] = ref[by_depth[d]]
                lm.tags[i][1] = pack(w)
                touched.add(d)
        add = []
        for k in range(1, n + 1):
            d = st[k][0]
            if d not in touched:
                add.append([T_PLACE, pack([0, NONE, 0, 0, 0x20000, d << 16, 0, ref[k], NONE, NONE, 0, 0])])
        fw = words(lm.tags[ftag][1])
        fw[1] += len(add)
        lm.tags[ftag][1] = pack(fw)
        at = (kids[-1] + 1) if kids else ftag + 1
        lm.tags[at:at] = add
        # the frame's keyframe (its full state, what a goto shows): the same placements
        moved = set()
        for i in lm.keyframes()[fi]:
            t, body = lm.tags[i]
            w = words(body)
            if t == T_PLACE and (w[5] >> 16) in by_depth:
                w[7] = ref[by_depth[w[5] >> 16]]
                lm.tags[i][1] = pack(w)
                moved.add(w[5] >> 16)
        assert moved == set(by_depth), (lab, 'faces missing from the keyframe')
        changed.append((lab, len(add)))
        lm.ti = {t: i for i, (t, _) in reversed(list(enumerate(lm.tags)))}
    return changed


def sheet(lm, counts, path):
    from PIL import Image, ImageDraw
    states = lm.simulate()
    fr, labels = lm.frames()
    lab2f = {v: k for k, v in labels.items()}
    W, H = 520, 190
    img = Image.new('RGB', (W, H * len(counts)), (30, 30, 40))
    d = ImageDraw.Draw(img)
    for r, n in enumerate(counts):
        st = faces(states[lab2f['num_%03d' % n]])
        oy = r * H
        d.text((4, oy + 2), 'num_%03d: %d faces' % (n, len(st)), fill=(255, 255, 0))
        for k, (_dep, e) in st.items():
            m = e['m']
            x, y, s = W / 2 + m[4] * 0.25, oy + H / 2 + 8 + m[5] * 0.33, m[0]
            hw = 15 * s
            col = (255, 90, 90) if k > n - 2 else (170, 210, 255)
            d.rectangle((x - hw, y - hw, x + hw, y + hw), outline=col)
            d.text((x - 8, y - 5), str(k), fill=col)
    img.save(path)


def main():
    a = sys.argv[1:]
    src, dst = a[0], a[1]
    first = int(a[a.index('--first') + 1]) if '--first' in a else 58
    last = int(a[a.index('--last') + 1]) if '--last' in a else None
    style = STYLES[a[a.index('--style') + 1] if '--style' in a else 'user4']
    data = open(src, 'rb').read()
    lm = Lm(data)
    assert lm.data() == data, 'round trip'
    lm0 = Lm(data)
    assert keyframes_match(lm0, lm0.simulate()), 'the input: a keyframe differs from its frame'
    before = lm.simulate()
    changed = relayout(lm, first, style, last)
    out = lm.data()
    open(dst, 'wb').write(out)
    after = Lm(out).simulate()
    assert len(before) == len(after)
    fr, labels = Lm(out).frames()
    def kept(fi):
        n = int(labels[fi][4:])
        return n < first or (last is not None and n > last)
    # frames past --last are deltas on the rewritten ones, so their played-through state can move;
    # the game jumps to num_<count> (its keyframe), and those keyframes are checked unchanged below
    same = sum(1 for fi in range(len(before)) if kept(fi) and before[fi] == after[fi])
    below = [fi for fi in range(len(before)) if int(labels[fi][4:]) < first]
    assert all(before[fi] == after[fi] for fi in below), 'a frame below the range changed'
    upto = [fi for fi in range(len(after)) if last is None or int(labels[fi][4:]) <= last]
    assert keyframes_match(Lm(out), after, upto), 'a keyframe differs from its frame'
    assert all(Lm(out).keyframe_state(f) == lm0.keyframe_state(f) for f in range(len(before))
               if kept(f)), 'a keyframe outside the range changed'
    print('%s: %d frames rewritten (%s), %d other frames unchanged, %d -> %d bytes' % (
        dst, len(changed), ', '.join('%s +%d' % c for c in changed[:4]) + (' ...' if len(changed) > 4 else ''),
        same, len(data), len(out)))
    if '--png' in a:
        sheet(Lm(out), [57, 58, 59, 60, 62, 66], a[a.index('--png') + 1])


if __name__ == '__main__':
    main()
