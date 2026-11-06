#!/usr/bin/env python3
"""A model of Sephiroth's up special trail / shape protocol (fighters/edge/edge.c edge_tr_*, weapons/trail.c from
tools/edge_trail_msc.py, weapons/fill.c from tools/edge_fill_msc.py): his points, crossings and shape steps through his
shared 4 - 6 and the trail articles' tests and answers, line for line, run with the articles updated after and before
him. Cases: a held Octaslash circle (a loop); a U from one up special closed by a straight line from the next (old
lines); a tilted ellipse (another shape); a triangle of three Blade Dashes and a four-sided shape of four (junctions:
test 127); a Blade Dash's last point (the landing) taken. Prints each shape (middle, long axis' angle, half axes, the pieces gone).

  python3 tools/edge_trail_sim.py
"""
import math

SEG, PER, PTS = 4.0, 15, 16
SUM1, SUM2, SUM3, COMMIT, CANCEL = -1001.5, -1002.5, -1003.5, -1004.5, -1005.5


def pack(x, y):
    ix = min(max(int((x + 512) * 2 + 0.5), 0), 2047)
    iy = min(max(int((y + 512) * 2 + 0.5), 0), 2047)
    return float(ix * 2048 + iy)


def unpack(v):
    c = int(v)
    ix = c // 2048
    return ix * 0.5 - 512, (c - ix * 2048) * 0.5 - 512


def tsin(x):
    # sin by its series (MSC has no sin: edge.c edge_tr_sin, trail.c tr_sin), x folded into -pi/2 .. pi/2
    if x > math.pi / 2:
        x = math.pi - x
    if x < -math.pi / 2:
        x = -math.pi - x
    x2 = x * x
    return x * (1 - x2 / 6 * (1 - x2 / 20 * (1 - x2 / 42)))


def axes(t7):
    th = t7 * math.pi / 128
    return tsin(math.pi / 2 - th), tsin(th)


EXT = 3.0


def ext(a, b):
    (ax, ay), (bx, by) = a, b
    l = math.hypot(bx - ax, by - ay)
    if l <= 0.01:
        return a, b
    dx, dy = (bx - ax) * EXT / l, (by - ay) * EXT / l
    return (ax - dx, ay - dy), (bx + dx, by + dy)


def cross(a, b, c, d):
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = a, b, c, d
    d1 = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    d2 = (bx - ax) * (dy - ay) - (by - ay) * (dx - ax)
    d3 = (dx - cx) * (ay - cy) - (dy - cy) * (ax - cx)
    d4 = (dx - cx) * (by - cy) - (dy - cy) * (bx - cx)
    # a point on the other line counts on its + side (>= 0), so a path through a corner crosses once, not never
    return ((d1 >= 0) != (d2 >= 0)) and ((d3 >= 0) != (d4 >= 0))


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
            s.junctions = []
            s.vanish = False
            s.dead = False

        def counts(s, k):
            return k > 0 or s.base % 1024 == 0

        def test(s, p, num):
            sh = s.w.sh
            same = s.base // 1024 == num // 1024
            for k in range(len(s.pts) - 1):
                if k in s.gone or (same and not s.base + k <= num - 4):    # own trail: pieces that can close a loop (132)
                    continue
                if (cross(s.sp, p, s.pts[k], s.pts[k + 1]) if same else
                        cross(*ext(s.sp, p), *ext(s.pts[k], s.pts[k + 1]))):   # other trails: both 3 longer (test 131)
                    if sh[4] > -1000 or same:
                        sh[4] = -float(s.base + k)
                    if not same and not any(jk == k and jn // 1024 == num // 1024 for jk, jn in s.junctions):
                        if len(s.junctions) < 4:
                            s.junctions.append((k, num - 1))

        def answer(s, v):
            sh = s.w.sh
            if v > 0:
                code = int(v)
                st, cnt = code // 512, code % 512
                for k in range(len(s.pts)):
                    if st <= s.base + k < st + cnt:
                        s.mark.add(k)
                return
            if -4328 <= v <= -4000:
                # EXTENT: the marked points' furthest along the axis and across it (max into 5 / 4; 4200 +: of minus)
                c = int(-v) - 4000
                sg = 1.0
                if c >= 200:
                    c -= 200
                    sg = -1.0
                co, si = axes(c)
                for k in sorted(s.mark):
                    x, y = s.pts[k]
                    u, w = sg * (x * co + y * si), sg * (-x * si + y * co)
                    sh[5] = max(sh[5], u)
                    sh[4] = max(sh[4], w)
                return
            if v == CANCEL:
                s.mark = set()
                return
            if v == COMMIT:
                if s.mark:
                    s.fill = set()
                    for k in range(len(s.pts) - 1):
                        if (k in s.mark or k + 1 in s.mark) and k not in s.gone:
                            s.fill.add(k)
                    s.centre = unpack(sh[5])
                s.gone |= set(range(len(s.pts)))       # every line goes (test 128)
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
            if s.dead:
                return
            sh = s.w.sh
            v = sh[6]
            if v in (-1.0, -2.0):
                if not s.over and v == -2.0:
                    s.vanish = True
                s.over = True
                if s.vanish:
                    s.dead = True
                return
            if v < -1000 or v - int(v) > 0.25:
                if -1006 <= v <= -1001 or v > 524288 or -4328 <= v <= -4000:
                    s.answer(v)
                if -3256 <= v <= -3000:
                    c = int(-v) - 3000
                    x, y = c // 16, c % 16
                    b = s.base // 1024
                    if b in (x, y):
                        o = y if b == x else x
                        for jk, jn in s.junctions:
                            if jn // 1024 == o and jk not in s.gone:
                                if b == x:
                                    sh[5], sh[4] = float(s.base + jk), float(jn)
                                else:
                                    sh[5], sh[4] = float(jn), float(s.base + jk)
                return
            num = int(v)
            if num < 1024 or num == s.seen:
                return
            nb, ob = num // 1024, s.base // 1024
            if nb <= 14 and ob <= 14 and nb != ob and (nb - ob + 14) % 14 >= 6:
                s.dead = True
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

    def cur(self):
        return 15 if self.charged else self.block

    def begin(self, x, y, charged=False):
        self.charged = charged
        if not charged:
            self.block = self.block % 14 + 1
        self.sh[4] = 0.0
        for i in range(12):
            self.V[i] = 0.0
        self.V[1] = float(self.cur() * 1024)
        self.V[10] = 2.0        # point 0 seen a frame before point 1 (test 131: the old lines tested no first piece)
        self.point(pack(x, y), self.cur() * 1024)

    def steps(self):
        sh, V = self.sh, self.V
        q = -int(V[0])
        if q >= 11:
            self.find(q)
            return
        if q == 1:
            for i in (8, 9, 10):
                if V[i] > 0:
                    sh[6] = V[i]
                    V[i] = 0.0
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
            V[8] = float(int(t * 128 / 180))
            V[9] = math.sqrt(2 * l1) * 1.3
            V[10] = math.sqrt(2 * l2) * 1.3
            sh[5] = sh[4] = -100000.0
            sh[6] = -(4000 + V[8]) - 0.5
            V[0] = -7
            return
        if q == 7:
            V[11], V[2] = sh[5], sh[4]
            sh[5] = sh[4] = -100000.0
            sh[6] = -(4200 + V[8]) - 0.5
            V[0] = -8
            return
        if q == 8:
            t7 = int(V[8])
            co, si = axes(t7)
            umax, wmax, umin, wmin = V[11], V[2], -sh[5], -sh[4]
            cu, cw = (umax + umin) / 2, (wmax + wmin) / 2
            cx, cy = cu * co - cw * si, cu * si + cw * co
            a = max(V[9], (umax - umin) / 2 * 1.3)
            b = max(V[10], (wmax - wmin) / 2 * 1.3)
            if b > a:
                a, b = b, a
                t7 = (t7 + 64) % 128
            a = min(max(a, 3), 127)
            b = min(max(b, 3), a)
            sh[5] = pack(cx, cy)
            sh[4] = float(t7 * 65536 + int(a * 2) * 256 + int(b * 2))
            sh[6] = COMMIT
            V[4] = self.end_code()      # the trail ends with its shape (test 139)
            self.shapes.append(dict(mid=(round(cx, 1), round(cy, 1)), angle=round(t7 * 180 / 128, 1), a=round(a, 1),
                                    b=round(b, 1)))
            V[0] = -5
            return
        sh[4] = 0.0
        sh[5] = V[3]
        sh[6] = V[4]
        V[10] = 0.0
        V[1] = V[4]
        V[5] = 10
        V[0] = 0

    def shape(self, s1, c1, s2, c2, num):
        sh, V = self.sh, self.V
        V[3] = sh[5]
        V[4] = float(num)
        V[2] = float(c1 + c2)
        V[8] = (s2 * 512 + c2 + 0.5) if c2 > 0 else 0.0
        V[9] = V[10] = 0.0
        sh[4] = 0.0
        sh[6] = s1 * 512 + c1 + 0.5
        V[0] = -1
        V[6] = 0.0

    # ---- the junction search (edge.c edge_tr_find*)
    def jq(self, x, y):
        self.sh[5] = self.sh[4] = 0.0
        self.sh[6] = -(3000 + x * 16 + y) - 0.5

    def find_start(self, q, num):
        V, sh = self.V, self.sh
        V[3] = sh[5]
        V[4] = float(num)
        V[1] = float(q)
        V[2] = -1.0
        V[11] = float(num)      # the number crossed at (VAR_4 is the restore's: the trail's end, if it ends meanwhile)
        self.jq(int(V[6]) // 1024, q // 1024)
        V[0] = -11

    def cand(self, i):
        z = self.block - 1 - i
        while z < 0:
            z += 14
        return z + 1

    def find_next(self):
        V, sh = self.V, self.sh
        x, y = int(V[6]) // 1024, int(V[1]) // 1024
        i = int(V[2]) + 1
        while i < 6:
            z = self.cand(i)
            if z not in (x, y, int(V[11]) // 1024):
                V[2] = float(i)
                self.jq(x, z)
                V[0] = -12
                return
            i += 1
        V[6], V[7] = V[1], V[11]
        sh[4] = 0.0
        sh[5], sh[6] = V[3], V[4]
        V[1] = float(self.cur() * 1024)
        V[0] = 0

    @staticmethod
    def between(a, b):
        lo, hi = min(a, b), max(a, b)
        return 0.0 if hi == lo else (lo + 1) * 512 + (hi - lo) + 0.5

    @staticmethod
    def count(code):
        return 0 if code <= 0 else int(code) % 512

    def find_shape(self, rx, rz, ry):
        V, sh = self.V, self.sh
        num, n1 = int(V[11]), int(V[7])
        cnt = (num - n1) + self.count(rx) + self.count(rz) + self.count(ry)
        if cnt < 3 or num - n1 >= 512:
            V[2] = 5.0
            self.find_next()
            return
        V[2] = float(cnt)
        V[8], V[9], V[10] = rx, rz, ry
        sh[4] = 0.0
        sh[6] = n1 * 512 + (num - n1) + 0.5
        V[0] = -1
        V[6] = 0.0

    def find(self, q):
        V, sh = self.V, self.sh
        j5, j4 = sh[5], sh[4]
        p, qy = int(V[6]), int(V[1])
        if q == 11:
            if j5 >= 1024:
                self.find_shape(self.between(p, int(j5)), 0.0, self.between(int(j4), qy))
            else:
                self.find_next()
            return
        if q == 12:
            if j5 >= 1024:
                V[8], V[9] = j5, j4
                self.jq(int(j4) // 1024, qy // 1024)
                V[0] = -13
            else:
                self.find_next()
            return
        if j5 >= 1024:
            self.find_shape(self.between(p, int(V[8])), self.between(int(V[9]), int(j5)), self.between(int(j4), qy))
        else:
            self.find_next()

    def end_code(self):
        return -2.0 if self.charged else -1.0

    def step(self, x, y, last=False):
        sh, V = self.sh, self.V
        if V[0] < 0:
            if last:
                V[4] = self.end_code()
            return
        if sh[6] < 1024:
            return
        if V[10] > 0 and not last:
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
                if m1 > 0 and m1 // 1024 != m // 1024:
                    self.find_start(m, num)
                    return
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
            V[0] = -6
            V[4] = self.end_code()

    def tick(self):
        if self.V[0] == -6:
            self.sh[6] = self.V[4]
            self.V[0] = 0
            return
        if self.V[0] == 0 and self.V[10] > 0:
            self.V[10] -= 1
        if -5 <= self.V[0] <= -1 or -8 <= self.V[0] <= -7 or -13 <= self.V[0] <= -11:
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


def run_path(w, path, order, charged=False):
    w.begin(*path[0], charged=charged)
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
        w.idle(30, order)
        r = 2.4 / math.radians(8)
        print('circle (radius %.1f):' % r, w.shapes, 'pieces gone', sum(len(a.gone) for a in w.arts))
        w = World()
        u = line((-30, 60), (-30, 20)) + line((-30, 20), (30, 20))[1:] + line((30, 20), (30, 60))[1:]
        run_path(w, u, order)
        w.idle(20, order)
        run_path(w, line((-50, 45), (50, 45)), order)
        w.idle(30, order)
        print('U (x -30 - 30, y 20 - 60) closed at y 45 by the next up special:', w.shapes,
              'pieces gone', sum(len(a.gone) for a in w.arts))
        w = World()
        run_path(w, ellipse(0, 60, 40, 15, 30), order)
        w.idle(30, order)
        print('ellipse (a 40, b 15, 30 degrees) (x 1.2):', w.shapes)
        print('  trail over after the steps:', w.sh[6] == -1.0)
        w = World()
        run_path(w, line((-40, 20), (40, 80)), order)       # / 
        w.idle(5, order)
        run_path(w, line((40, 20), (-40, 80)), order)       # \ : an X, meeting at (0, 50)
        w.idle(5, order)
        run_path(w, line((-50, 70), (50, 70)), order)       # across both arms above: a triangle (0, 50) (-26.7, 70) (26.7, 70)
        w.idle(30, order)
        print('triangle of three Blade Dashes (middle about (0, 63.3)):', w.shapes)
        w = World()
        run_path(w, line((-30, 80), (-30, 10)), order)      # | left
        w.idle(5, order)
        run_path(w, line((-40, 20), (40, 20)), order)       # _ bottom, crossing the left
        w.idle(5, order)
        run_path(w, line((30, 10), (30, 80)), order)        # | right, crossing the bottom
        w.idle(5, order)
        run_path(w, line((-45, 60), (45, 60)), order)       # top across both sides: a square (-30..30, 20..60)
        w.idle(30, order)
        print('four Blade Dashes (a 60 x 40 rectangle, middle (0, 40)):', w.shapes)
        w = World()
        run_path(w, line((-60, 9), (40, 9)), order)         # along the ground
        w.idle(5, order)
        run_path(w, line((40, 9), (-40, 90)), order)        # from where it ended, up-left: they only touch (test 131's clip)
        w.idle(5, order)
        run_path(w, line((30, 100), (-50, 0)), order)       # across the second, down through the first
        w.idle(30, order)
        print('triangle on a line\'s end (test 131):', w.shapes)
        w = World()
        run_path(w, line((0, 60), (40, 20)), order)         # a dash into the floor at (40, 20)
        w.idle(5, order)
        last = [a for a in w.arts][-1]
        print('a Blade Dash to (40, 20): its last point taken', last.pts[-1])
