#!/usr/bin/env python3
"""A model of Sephiroth's up special trail / shape protocol (fighters/edge/edge.c edge_tr_*, weapons/trail.c from
tools/edge_trail_msc.py, weapons/fill.c from tools/edge_fill_msc.py): his points, crossings and shape steps through his
shared 4 - 6 and the trail articles' tests and answers, line for line, run with the articles updated after and before
him. Cases: a held Octaslash circle (a loop); a U from one up special closed by a straight line from the next (old
lines); a tilted ellipse (another shape). Prints each shape (middle, long axis' angle, half axes, the pieces gone).

  python3 tools/edge_trail_sim.py
"""
import math

SEG, PER, PTS = 4.0, 15, 16
SUM1, SUM2, SUM3, COMMIT = -1001.5, -1002.5, -1003.5, -1004.5


def pack(x, y):
    ix = min(max(int((x + 512) * 2 + 0.5), 0), 2047)
    iy = min(max(int((y + 512) * 2 + 0.5), 0), 2047)
    return float(ix * 2048 + iy)


def unpack(v):
    c = int(v)
    ix = c // 2048
    return ix * 0.5 - 512, (c - ix * 2048) * 0.5 - 512


def cross(a, b, c, d):
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = a, b, c, d
    d1 = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    d2 = (bx - ax) * (dy - ay) - (by - ay) * (dx - ax)
    d3 = (dx - cx) * (ay - cy) - (dy - cy) * (ax - cx)
    d4 = (dx - cx) * (by - cy) - (dy - cy) * (bx - cx)
    return ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4))


class World:
    def __init__(self):
        self.sh = {4: 0.0, 5: 0.0, 6: 0.0}
        self.V = {i: 0.0 for i in range(12)}
        self.block = 0
        self.arts = []
        self.shapes = []

    # ---- the article (trail.c)
    class Art:
        def __init__(s, w):
            s.w = w
            s.base = int(w.sh[6])
            s.pts = [unpack(w.sh[5])]
            s.seen = s.base
            s.sp = s.pts[0]
            s.over = False
            s.mark = set()
            s.gone = set()
            s.fill = set()

        def counts(s, k):
            return k > 0 or s.base % 1024 == 0

        def test(s, p, num):
            sh = s.w.sh
            same = s.base // 1024 == num // 1024
            for k in range(len(s.pts) - 1):
                if k in s.gone or (same and not s.base + k + 1 <= num - 2):
                    continue
                if cross(s.sp, p, s.pts[k], s.pts[k + 1]):
                    if sh[4] > -1000 or same:
                        sh[4] = -float(s.base + k)

        def answer(s, v):
            sh = s.w.sh
            if v > 0:
                code = int(v)
                st, cnt = code // 512, code % 512
                for k in range(len(s.pts)):
                    if st <= s.base + k < st + cnt:
                        s.mark.add(k)
                return
            if v == COMMIT:
                if s.mark:
                    s.fill = set()
                    for k in range(len(s.pts) - 1):
                        if k in s.mark or k + 1 in s.mark:
                            if k not in s.gone:
                                s.fill.add(k)
                            s.gone.add(k)
                    s.centre = unpack(sh[5])
                s.mark = set()
                return
            a = b = 0.0
            for k in sorted(s.mark):
                if not s.counts(k):
                    continue
                x, y = s.pts[k]
                if v == SUM1:
                    a += x
                    b += y
                elif v == SUM2:
                    a += x * x
                    b += y * y
                elif v == SUM3:
                    a += x * y
            sh[5] += a
            sh[4] += b

        def tick(s):
            sh = s.w.sh
            v = sh[6]
            if v == -1.0:
                s.over = True
                return
            if v < -1000 or v - int(v) > 0.25:
                if -1005 <= v <= -1001 or v > 524288:
                    s.answer(v)
                return
            num = int(v)
            if num < 1024 or num == s.seen:
                return
            p = unpack(sh[5])
            if num == s.seen + 1:
                s.test(p, num)
            if not s.over and num == s.base + len(s.pts) and len(s.pts) < PTS:
                s.pts.append(p)
            s.seen = num
            s.sp = p

    # ---- Sephiroth (edge.c)
    def point(self, p, n):
        self.sh[5] = p
        self.sh[6] = float(n)
        if (n % 1024) % PER == 0:
            self.arts.append(World.Art(self))

    def begin(self, x, y):
        self.block = self.block % 15 + 1
        self.sh[4] = 0.0
        for i in range(12):
            self.V[i] = 0.0
        self.V[1] = float(self.block * 1024)
        self.point(pack(x, y), self.block * 1024)

    def steps(self):
        sh, V = self.sh, self.V
        q = -int(V[0])
        if q == 1:
            if V[8] > 0:
                sh[6] = V[8]
                V[8] = 0.0
                return
            sh[5] = sh[4] = 0.0
            sh[6] = SUM1
            V[0] = -2
            return
        if q in (2, 3):
            V[8 + 2 * (q - 2)] = sh[5]
            V[9 + 2 * (q - 2)] = sh[4]
            sh[5] = sh[4] = 0.0
            sh[6] = SUM2 if q == 2 else SUM3
            V[0] = -(q + 1)
            return
        if q == 4:
            n = V[2]
            cx, cy = V[8] / n, V[9] / n
            vxx = V[10] / n - cx * cx
            vyy = V[11] / n - cy * cy
            vxy = sh[5] / n - cx * cy
            d = math.sqrt((vxx - vyy) ** 2 * 0.25 + vxy * vxy)
            l1, l2 = (vxx + vyy) / 2 + d, max((vxx + vyy) / 2 - d, 0)
            t = math.degrees(math.atan2(2 * vxy, vxx - vyy)) / 2
            if t < 0:
                t += 180
            a = min(max(math.sqrt(2 * l1), 3), 127)
            b = min(max(math.sqrt(2 * l2), 3), a)
            sh[5] = pack(cx, cy)
            sh[4] = float(int(t * 128 / 180) * 65536 + int(a * 2) * 256 + int(b * 2))
            sh[6] = COMMIT
            self.shapes.append(dict(mid=(round(cx, 1), round(cy, 1)), angle=round(t, 1), a=round(a, 1), b=round(b, 1),
                                    n=int(n)))
            V[0] = -5
            return
        sh[4] = 0.0
        sh[5] = V[3]
        sh[6] = V[4]
        V[1] = V[4]
        V[5] = 10
        V[0] = 0

    def shape(self, s1, c1, s2, c2, num):
        sh, V = self.sh, self.V
        V[3] = sh[5]
        V[4] = float(num)
        V[2] = float(c1 + c2)
        V[8] = (s2 * 512 + c2 + 0.5) if c2 > 0 else 0.0
        sh[4] = 0.0
        sh[6] = s1 * 512 + c1 + 0.5
        V[0] = -1
        V[6] = 0.0

    def step(self, x, y, last=False):
        sh, V = self.sh, self.V
        if V[0] < 0:
            if last:
                V[4] = -1.0
            return
        if sh[6] < 1024:
            return
        if V[5] > 0:
            V[5] -= 1
        c = sh[4]
        sh[4] = 0.0
        num = int(sh[6])
        if c <= -1024 and V[5] <= 0 and not last:
            m = int(-c)
            if m // 1024 == num // 1024:
                if m >= V[1] and 3 <= num - 1 - m < 512:
                    self.shape(m + 1, num - 1 - m, 0, 0, num)
                    return
            else:
                m1 = int(V[6])
                if m1 > 0 and m1 // 1024 == m // 1024 and m1 != m:
                    lo, hi = min(m, m1), max(m, m1)
                    c1, c2 = num - int(V[7]), hi - lo
                    if c1 + c2 >= 3 and c1 < 512 and c2 < 512:
                        self.shape(int(V[7]), c1, lo + 1, c2, num)
                        return
                V[6] = float(m)
                V[7] = float(num)
        lx, ly = unpack(sh[5])
        d = (x - lx) ** 2 + (y - ly) ** 2
        if d >= SEG * SEG or (last and d >= 1):
            self.point(pack(x, y), num + 1)
        if last:
            sh[6] = -1.0

    def tick(self):
        if -5 <= self.V[0] <= -1:
            self.steps()

    def frame(self, x, y, last, order):
        if order == 'articles first':
            for a in list(self.arts):
                a.tick()
            self.tick()
            self.step(x, y, last)
        else:
            self.tick()
            self.step(x, y, last)
            for a in list(self.arts):
                a.tick()

    def idle(self, frames, order):
        for _ in range(frames):
            if order == 'articles first':
                for a in list(self.arts):
                    a.tick()
                self.tick()
            else:
                self.tick()
                for a in list(self.arts):
                    a.tick()


def run_path(w, path, order):
    w.begin(*path[0])
    for i, (x, y) in enumerate(path[1:]):
        w.frame(x, y, i == len(path) - 2, order)


def circle():
    pts, x, y, ang = [(0.0, 50.0)], 0.0, 50.0, 0.0
    for _ in range(140):
        ang += math.radians(8)
        x += 2.4 * math.cos(ang)
        y += 2.4 * math.sin(ang)
        pts.append((x, y))
    return pts


def line(a, b, speed=6.0):
    n = max(int(math.hypot(b[0] - a[0], b[1] - a[1]) / speed), 1)
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]


def ellipse(cx, cy, a, b, tilt, laps=1.15, steps=120):
    t0 = math.radians(tilt)
    out = []
    for i in range(int(steps * laps) + 1):
        u = 2 * math.pi * i / steps
        x, y = a * math.cos(u), b * math.sin(u)
        out.append((cx + x * math.cos(t0) - y * math.sin(t0), cy + x * math.sin(t0) + y * math.cos(t0)))
    return out


if __name__ == '__main__':
    for order in ('Sephiroth first', 'articles first'):
        print('==', order)
        w = World()
        run_path(w, circle(), order)
        w.idle(10, order)
        r = 2.4 / math.radians(8)
        print('circle (radius %.1f):' % r, w.shapes, 'pieces gone', sum(len(a.gone) for a in w.arts))
        w = World()
        u = line((-30, 60), (-30, 20)) + line((-30, 20), (30, 20))[1:] + line((30, 20), (30, 60))[1:]
        run_path(w, u, order)
        w.idle(20, order)
        run_path(w, line((-50, 45), (50, 45)), order)
        w.idle(10, order)
        print('U (x -30 - 30, y 20 - 60) closed at y 45 by the next up special:', w.shapes,
              'pieces gone', sum(len(a.gone) for a in w.arts))
        w = World()
        run_path(w, ellipse(0, 60, 40, 15, 30), order)
        w.idle(10, order)
        print('ellipse (a 40, b 15, 30 degrees):', w.shapes)
        print('  trail over after the steps:', w.sh[6] == -1.0)
