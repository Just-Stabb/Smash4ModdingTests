#!/usr/bin/env python3
"""Sephiroth's up special trail article (fighters/edge/specials.md "Up special", tests 124 / 126): writes
fighters/edge/weapons/trail.c = the snake run's base (Zelda's dein, fighters/edge/weapons/snake.c up to its own
section) + the trail's code. MSC-C has no arrays: its POINTS points are numbered globals behind generated if-chains.

One article draws one stretch of a trail: up to POINTS points (POINTS - 1 pieces), still at its first point, facing +1
(its model's +Z is the world's +X). Its model (tools/edge_snake_articles.py build_trail), moved by joint every frame
(ModelModule(0x7, 0x7D0 + bone, 0, dy, dx), relative to its first point):
  - the line: piece k a ribbon between its own joints A_k / B_k (bones 19 + 2k / 20 + 2k), at points k / k + 1, or
    both on point k (nothing drawn) once the piece is part of a closed shape ("The lines should go away when forming a
    shape");
  - the shape's fill: wedges C - W_k - W_k+1 (C bone 2, W_k bone 3 + k) for the pieces that closed it, from the
    shape's middle C to the pieces' own points ("the formed shape to mirror the lines that the closed shape was made
    of"), grown in from the middle from FILL_DELAY frames after, held, shrunk away; W_k on C otherwise.
Sephiroth (edge.c edge_tr_*) talks to the articles through his shared variables 4 - 6:
  5: the newest point (packed: (x + 512) x 2 x 2048 + (y + 512) x 2); 6: its number (block x 1024 + n, block 1 - 15,
  a new one each trail: unique among trails still drawn); -1 once the trail's over;
  4: a crossing: an article whose own piece m (its start's number) the newest piece crosses (not one next to it, not
  one already gone) writes -m there; he reads and clears it each frame.
  A closed shape is asked of the articles a step a frame, 6 holding the step (5 / 4 the sums they add to):
    start x 512 + count + 0.5: mark the points numbered start .. start + count - 1 (one or two of these);
    SUM1 / SUM2 / SUM3: the marked points' x / y, x^2 / y^2, x y added to 5 / 4 (5) (each point once: a stretch's
    first point is the stretch before's last, counted there);
    COMMIT: 5 the shape's middle: the pieces with a marked end fill (the wedges), and every piece of every line goes
    (test 128, the user: "When a shape is formed, all lines aren't cleared": all of them now, not only the shape's).
    CANCEL: the marks dropped (a shape near the blast zones isn't made: test 128).
      JQ X Y (-(3000 + X x 16 + Y) - 0.5): a junction between trails (blocks) X and Y: an article of either with one
    writes X's piece in 5 and Y's in 4 (test 127: shapes of three or four lines).
      EXTENT (-(4000 + t) - 0.5, t the fitted axis in 128ths of 180 degrees; 4200 + t: of minus): the marked points'
    furthest along the axis into 5 and across it into 4 (the larger kept): the shape's box, its hitbox at least 1.2 x
    it.
  An article keeps testing and answering after its trail is over (old lines make shapes too), but takes no points. A
  crossing with another trail's piece is kept as a junction (its piece, the other's number: JUNCTIONS at most).
  Shadow Flare's shot (test 148: "side special should not create a new visible line, but act as one while it is active")
  lays a trail of block 15 numbered from 15 x 1024 + SHOT_FROM (edge.c edge_s_line_tick): its articles draw no line
  (tr_hidden: every piece on its start), but test, mark, sum and fill as any.
  -2 ends a trail that doesn't stay (held Octaslash's, test 127; the shot's): its articles go once their fill is over. A new Blade
  Dash trail (block 1 - 14; Octaslash's is 15) puts out the trails KEEP or more before it (the user: "delete the oldest
  line if a new line has been made after the 6th line").
Its trail's points are taken while their number follows its last and are within its stretch. Removed after LIFE
frames, or once all its pieces are gone and its fill is over.

  python3 tools/edge_trail_msc.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EDGE = os.path.join(ROOT, 'fighters', 'edge')
POINTS = 16
LIFE = 360          # the user: "persists for 6 seconds"
SUM1, SUM2, SUM3, COMMIT, CANCEL = -1001.5, -1002.5, -1003.5, -1004.5, -1005.5
FILL_DELAY, FILL_GROW, FILL_HOLD, FILL_END = 12, 8, 40, 50    # the glow; the fill article hits from 4 to FILL_END (edge_fill_msc.py)
FILL_SCALE = 1.3    # the fill drawn this much bigger than the shape (test 127, the user: "at least 1.2x the size"; 1.3
                    # since test 132: "rather than full and larger than the lines that it is made of")
JUNCTIONS = 4
KEEP = 6
SHOT_FROM = 765     # Shadow Flare's shot's trail: its numbers from block 15 x 1024 + this (51 x 15: a stretch starts there)
EXT = 3.0           # the pieces tested taken this much longer at both ends (lines meeting end to end cross: test 131)
C_BONE, W_BONE, A_BONE = 2, 3, 3 + POINTS                     # bones: TopN, HaveN, C, W0 - W15, A0 / B0 ... A14 / B14


def ifchain(fmt, n=POINTS):
    return '\n'.join('    if (k == %d)\n    {\n%s\n    }' % (k, fmt.replace('#', str(k))) for k in range(n))


def generate():
    src = open(os.path.join(EDGE, 'weapons', 'snake.c')).read()
    base = src[:src.index("// ---- Sephiroth's held forward air (tools/edge_snake_articles_msc.py)")]
    head = '''// ---- Sephiroth's up special trail (tools/edge_trail_msc.py; tests 124 / 126): one stretch of the purple line his
// path leaves during either up special's attack, up to %d points; still, removed after %d frames
int tr_slot;            // his player slot (0 - 7), -1: not found
int tr_life;            // frames left
int tr_base;            // its first point's number
int tr_seen;            // the newest point's number seen
int tr_n;               // points taken
int tr_over_t;          // 1: its trail is over (it takes no more points)
int tr_mark;            // points marked for the shape being asked (bit k: point k)
int tr_gone;            // pieces gone (bit k: piece k, points k - k + 1)
int tr_fill;            // pieces filling the shape (bit k)
int tr_ft;              // frames since the fill began (-1 none)
int tr_vanish;          // 1: its trail doesn't stay (held Octaslash's): it goes once its fill is over
float tr_lr;            // its facing as made (its model's +Z is the world's +X x this: test 127, a line turned the
                        // wrong way when he faced left; tests 124 - 126 set the facing to 1, which didn't turn it)
float tr_cx;            // the fill's middle
float tr_cy;
float tr_ox;            // its first point (where it stands)
float tr_oy;
float tr_px;            // tr_unpack's result
float tr_py;
float tr_sx;            // the newest point seen
float tr_sy;
''' % (POINTS, LIFE)
    head += ''.join('float tr_x%d;\nfloat tr_y%d;\n' % (k, k) for k in range(POINTS))
    head += ''.join('int tr_jk%d;\nint tr_jn%d;\n' % (k, k) for k in range(JUNCTIONS))
    body = r'''
int tr_points() { return POINTS_N; }

float tr_get_x(int k)
{
GETX
    return 0.0f;
}

float tr_get_y(int k)
{
GETY
    return 0.0f;
}

void tr_set(int k, float x, float y)
{
SETXY
}

// 1 << k
int tr_bit(int k)
{
    int b;
    b = 1;
    while (k > 0)
    {
        b = b * 2;
        k = k - 1;
    }
    return b;
}

int tr_has(int mask, int k)
{
    if ((mask / tr_bit(k)) - (mask / tr_bit(k + 1)) * 2 != 0)
    {
        return 0x1;
    }
    return 0;
}

// junction j: its piece (-1 none) / the other trail's piece number
int tr_get_jk(int k)
{
GETJK
    return -1;
}

int tr_get_jn(int k)
{
GETJN
    return 0;
}

void tr_set_j(int k, int p, int n)
{
SETJ
}

// a crossing with another trail kept (its piece p, the other's piece number n), once
void tr_junction(int p, int n)
{
    int k;
    k = 0;
    while (k < JUNC_N)
    {
        if (tr_get_jk(k) == p && tr_get_jn(k) / 0x400 == n / 0x400)
        {
            return;
        }
        k = k + 1;
    }
    k = 0;
    while (k < JUNC_N)
    {
        if (tr_get_jk(k) < 0)
        {
            tr_set_j(k, p, n);
            return;
        }
        k = k + 1;
    }
}

// JQ X Y: its junctions with the other one's trail: X's piece number in 5, Y's in 4
void tr_junctions(int x, int y)
{
    int b;
    int k;
    int o;
    b = tr_base / 0x400;
    if (b == x)
    {
        o = y;
    }
    else if (b == y)
    {
        o = x;
    }
    else
    {
        return;
    }
    k = 0;
    while (k < JUNC_N)
    {
        if (tr_get_jk(k) >= 0 && tr_get_jn(k) / 0x400 == o && tr_has(tr_gone, tr_get_jk(k)) == 0)
        {
            if (b == x)
            {
                tr_share(0x5, (float)(tr_base + tr_get_jk(k)));
                tr_share(0x4, (float)tr_get_jn(k));
            }
            else
            {
                tr_share(0x5, (float)tr_get_jn(k));
                tr_share(0x4, (float)(tr_base + tr_get_jk(k)));
            }
        }
        k = k + 1;
    }
}

int tr_find_owner()
{
    int s;
    int best;
    float dx;
    float dy;
    float d;
    float bd;
    best = 0xffffffff;
    bd = 1000000.0f;
    s = 0;
    while (s < 0x8)
    {
        if (WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0 && (int)WorkModuleF(0, 0x0f0000bd + 0x8 * s) == 0x42)
        {
            dx = WorkModuleF(0, 0x0f000020 + 0x4 * s) - PostureModuleF(0x1);
            dy = WorkModuleF(0, 0x0f000021 + 0x4 * s) - PostureModuleF(0x2);
            d = dx * dx + dy * dy;
            if (d < bd)
            {
                bd = d;
                best = s;
            }
        }
        s += 1;
    }
    return best;
}

float tr_shared(int k)
{
    return WorkModuleF(0, 0x0f000340 + 0x8 * tr_slot + k);
}

void tr_share(int k, float v)
{
    WorkModule(0, v, 0x0f000340 + 0x8 * tr_slot + k);
}

// a point as he packs it (edge.c edge_tr_pack): (x + 512) x 2 whole x 2048 + (y + 512) x 2 whole, half units
void tr_unpack(float v)
{
    int c;
    int ix;
    c = (int)v;
    ix = c / 0x800;
    tr_px = (float)ix * 0.5f - 512.0f;
    tr_py = (float)(c - ix * 0x800) * 0.5f - 512.0f;
}

// 1 if the pieces (ax, ay) - (bx, by) and (cx, cy) - (dx, dy) cross (properly: not at an end)
int tr_cross(float ax, float ay, float bx, float by, float cx, float cy, float dx, float dy)
{
    float d1;
    float d2;
    float d3;
    float d4;
    d1 = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
    d2 = (bx - ax) * (dy - ay) - (by - ay) * (dx - ax);
    d3 = (dx - cx) * (ay - cy) - (dy - cy) * (ax - cx);
    d4 = (dx - cx) * (by - cy) - (dy - cy) * (bx - cx);
    if ((d1 >= 0.0f && d2 < 0.0f || d1 < 0.0f && d2 >= 0.0f) && (d3 >= 0.0f && d4 < 0.0f || d3 < 0.0f && d4 >= 0.0f))
    {
        return 0x1;
    }
    return 0;
}

// the newest piece (tr_sx, tr_sy) - (x, y), numbers num - 1 - num, against this stretch's own pieces still drawn (in
// its own trail, not the ones next to it): one crossed, m its start's number, reported in shared 4 as -m
// every piece tested is taken EXT_N longer at both ends (test 131, the user's clip: a Blade Dash started where the last
// one ended, the two lines meeting end to end, never crossing, so the triangle they made with a third wasn't found);
// its own trail's pieces as they are, and only those that can close a loop (3 points between: test 132). Test 135:
// plain ifs and its own scratch (test 132's `same && tr_cross(..) || same == 0 && tr_cross(..)` and the parameters
// reused as scratch: Octaslash's own crossings, the only users of the first half, never made a shape)
void tr_test(float x, float y, int num)
{
    int k;
    int same;
    int hit;
    float ax;
    float ay;
    float bx;
    float by;
    float cx;
    float cy;
    float dx;
    float dy;
    float ex;
    float ey;
    float l;
    same = 0;
    if (tr_base / 0x400 == num / 0x400)
    {
        same = 0x1;
    }
    ax = tr_sx;
    ay = tr_sy;
    bx = x;
    by = y;
    if (same == 0)
    {
        l = MathF(0, (bx - ax) * (bx - ax) + (by - ay) * (by - ay));
        if (l > 0.01f)
        {
            l = EXT_N / l;
            ex = (bx - ax) * l;
            ey = (by - ay) * l;
            ax = ax - ex;
            ay = ay - ey;
            bx = bx + ex;
            by = by + ey;
        }
    }
    k = 0;
    while (k < tr_n - 1)
    {
        hit = 0;
        if (tr_has(tr_gone, k) == 0)
        {
            cx = tr_get_x(k);
            cy = tr_get_y(k);
            dx = tr_get_x(k + 1);
            dy = tr_get_y(k + 1);
            if (same)
            {
                if (tr_base + k <= num - 4)
                {
                    hit = tr_cross(ax, ay, bx, by, cx, cy, dx, dy);
                }
            }
            else
            {
                l = MathF(0, (dx - cx) * (dx - cx) + (dy - cy) * (dy - cy));
                if (l > 0.01f)
                {
                    l = EXT_N / l;
                    ex = (dx - cx) * l;
                    ey = (dy - cy) * l;
                    cx = cx - ex;
                    cy = cy - ey;
                    dx = dx + ex;
                    dy = dy + ey;
                }
                hit = tr_cross(ax, ay, bx, by, cx, cy, dx, dy);
            }
        }
        if (hit)
        {
            if (tr_shared(0x4) > -1000.0f || same)
            {
                tr_share(0x4, -(float)(tr_base + k));
            }
            if (same == 0)
            {
                tr_junction(k, num - 1);
            }
        }
        k = k + 1;
    }
}

// 1 if point k is counted here (a stretch's first point is the one before's last, counted there; a trail's first, here:
// numbered block x 1024, or block x 1024 + SHOT_FROM_N for Shadow Flare's shot's, test 148)
int tr_counts(int k)
{
    int i;
    i = tr_base - (tr_base / 0x400) * 0x400;
    if (k > 0 || i == 0 || i == SHOT_FROM_N)
    {
        return 0x1;
    }
    return 0;
}

// 1 for a stretch of Shadow Flare's shot's trail (numbered from block x 1024 + SHOT_FROM_N, test 148): its line isn't
// drawn ("side special should not create a new visible line, but act as one while it is active"), its fill is
int tr_hidden()
{
    if (tr_base - (tr_base / 0x400) * 0x400 >= SHOT_FROM_N)
    {
        return 0x1;
    }
    return 0;
}

// sin by its series (no sin in MSC; edge.c edge_tr_sin the same), x folded into -pi/2 .. pi/2
float tr_sin(float x)
{
    float x2;
    if (x > 1.5707963f)
    {
        x = 3.1415927f - x;
    }
    if (x < -1.5707963f)
    {
        x = -3.1415927f - x;
    }
    x2 = x * x;
    return x * (1.0f - x2 / 6.0f * (1.0f - x2 / 20.0f * (1.0f - x2 / 42.0f)));
}

// EXTENT (-(4000 + t) - 0.5; 4200 + t: of minus): the marked points' furthest along the axis at t x 180 / 128 degrees
// (into 5) and across it (into 4), the larger kept
void tr_extent(int c)
{
    float sg;
    float co;
    float si;
    float u;
    float w;
    int k;
    sg = 1.0f;
    if (c >= 200)
    {
        c = c - 200;
        sg = -1.0f;
    }
    u = (float)c * 0.0245437f;
    co = tr_sin(1.5707963f - u);
    si = tr_sin(u);
    k = 0;
    while (k < tr_n)
    {
        if (tr_has(tr_mark, k))
        {
            u = sg * (tr_get_x(k) * co + tr_get_y(k) * si);
            w = sg * (tr_get_y(k) * co - tr_get_x(k) * si);
            if (u > tr_shared(0x5))
            {
                tr_share(0x5, u);
            }
            if (w > tr_shared(0x4))
            {
                tr_share(0x4, w);
            }
        }
        k = k + 1;
    }
}

// a step of a shape asked (shared 6 = v): mark, a sum, or the commit
void tr_answer(float v)
{
    int code;
    int st;
    int cnt;
    int k;
    float a;
    float b;
    float x;
    float y;
    if (v > 0.0f)
    {
        code = (int)v;
        st = code / 0x200;
        cnt = code - st * 0x200;
        k = 0;
        while (k < tr_n)
        {
            if (tr_base + k >= st && tr_base + k < st + cnt)
            {
                tr_mark = tr_mark | tr_bit(k);
            }
            k = k + 1;
        }
        return;
    }
    if (v == CANCEL_V)
    {
        tr_mark = 0;
        return;
    }
    if (v == COMMIT_V)
    {
        if (tr_mark != 0)
        {
            tr_unpack(tr_shared(0x5));
            tr_cx = tr_px;
            tr_cy = tr_py;
            tr_fill = 0;
            k = 0;
            while (k < tr_n - 1)
            {
                if (tr_has(tr_mark, k) || tr_has(tr_mark, k + 1))
                {
                    if (tr_has(tr_gone, k) == 0)
                    {
                        tr_fill = tr_fill | tr_bit(k);
                    }
                }
                k = k + 1;
            }
            tr_ft = 0;
        }
        // every line goes (test 128): all its pieces, the one from its newest point on too (a trail still being laid
        // starts again from its next point)
        tr_gone = tr_bit(tr_n) - 1;
        tr_mark = 0;
        return;
    }
    a = 0.0f;
    b = 0.0f;
    k = 0;
    while (k < tr_n)
    {
        if (tr_has(tr_mark, k) && tr_counts(k))
        {
            x = tr_get_x(k);
            y = tr_get_y(k);
            if (v == SUM1_V)
            {
                a = a + x;
                b = b + y;
            }
            if (v == SUM2_V)
            {
                a = a + x * x;
                b = b + y * y;
            }
            if (v == SUM3_V)
            {
                a = a + x * y;
            }
        }
        k = k + 1;
    }
    tr_share(0x5, tr_shared(0x5) + a);
    tr_share(0x4, tr_shared(0x4) + b);
}

// every frame: a shape's step answered; a new point tested against its pieces, and taken if it's its trail's next
void tr_take()
{
    float v;
    int num;
    if (tr_slot < 0)
    {
        return;
    }
    v = tr_shared(0x6);
    if (v == -1.0f || v == -2.0f)
    {
        if (tr_over_t == 0 && v == -2.0f)
        {
            tr_vanish = 0x1;
        }
        tr_over_t = 0x1;
        return;
    }
    if (v < -1000.0f || v - (float)((int)v) > 0.25f)
    {
        if (v <= -1001.0f && v >= -1006.0f || v > 524288.0f)
        {
            tr_answer(v);
        }
        if (v <= -4000.0f && v >= -4328.0f)
        {
            tr_extent((int)(-v) - 4000);
        }
        if (v <= -3000.0f && v >= -3256.0f)
        {
            num = (int)(-v) - 3000;
            tr_junctions(num / 0x10, num - (num / 0x10) * 0x10);
        }
        return;
    }
    num = (int)v;
    if (num < 0x400 || num == tr_seen)
    {
        return;                 // not a trail's (the snake sword's runs share these), or seen
    }
    // a new Blade Dash trail KEEP_N or more after this one's: this one goes
    if (num / 0x400 <= 0xe && tr_base / 0x400 <= 0xe && num / 0x400 != tr_base / 0x400
        && (num / 0x400 - tr_base / 0x400 + 0xe) - ((num / 0x400 - tr_base / 0x400 + 0xe) / 0xe) * 0xe >= KEEP_N)
    {
        tr_vanish = 0x1;
        tr_over_t = 0x1;
        tr_gone = tr_bit(tr_points()) - 1;
    }
    tr_unpack(tr_shared(0x5));
    if (num == tr_seen + 1)
    {
        tr_test(tr_px, tr_py, num);
    }
    if (tr_over_t == 0 && num == tr_base + tr_n && tr_n < tr_points())
    {
        tr_set(tr_n, tr_px, tr_py);
        tr_n = tr_n + 1;
    }
    tr_seen = num;
    tr_sx = tr_px;
    tr_sy = tr_py;
}

void tr_still()
{
    KineticModule(0x11, 0, 0, 0);
    KineticModule(0xf, 0, 0, 0);
}

// the fill's size now (0 - 1): none before DELAY_N, grown over GROW_N frames, held to HOLD_N, shrunk to END_N
float tr_grow()
{
    if (tr_ft < DELAY_N)
    {
        return 0.0f;
    }
    if (tr_ft < DELAY_N + GROW_N)
    {
        return (float)(tr_ft - DELAY_N) / (float)GROW_N;
    }
    if (tr_ft < HOLD_N)
    {
        return 1.0f;
    }
    if (tr_ft < END_N)
    {
        return (float)(END_N - tr_ft) / (float)(END_N - HOLD_N);
    }
    return 0.0f;
}

void tr_joint(int bone, float x, float y)
{
    ModelModule(0x7, 0x7d0 + bone, 0, y - tr_oy, (x - tr_ox) * tr_lr);
}

// the joints: the line's pieces still drawn between their points (gone / not yet: both ends on its start), the fill's
// wedge points from the middle out to their points by tr_grow()
void tr_pose()
{
    int k;
    int j;
    float t;
    float cx;
    float cy;
    PostureModule(0x2714, tr_ox, tr_oy, PostureModuleF(0x3));
    k = 0;
    while (k < tr_points() - 1)
    {
        j = k;
        if (j > tr_n - 1)
        {
            j = tr_n - 1;
        }
        tr_joint(A_BONE_N + 2 * k, tr_get_x(j), tr_get_y(j));
        if (k < tr_n - 1 && tr_has(tr_gone, k) == 0 && tr_hidden() == 0)
        {
            j = k + 1;
        }
        tr_joint(A_BONE_N + 1 + 2 * k, tr_get_x(j), tr_get_y(j));
        k = k + 1;
    }
    t = 0.0f;
    cx = tr_ox;
    cy = tr_oy;
    if (tr_ft >= 0)
    {
        t = tr_grow() * SCALE_V;
        cx = tr_cx;
        cy = tr_cy;
    }
    tr_joint(C_BONE_N, cx, cy);
    k = 0;
    while (k < tr_points())
    {
        if (k < tr_n && t > 0.0f && (tr_has(tr_fill, k) || k > 0 && tr_has(tr_fill, k - 1)))
        {
            tr_joint(W_BONE_N + k, cx + (tr_get_x(k) - cx) * t, cy + (tr_get_y(k) - cy) * t);
        }
        else
        {
            tr_joint(W_BONE_N + k, cx, cy);
        }
        k = k + 1;
    }
}

int tr_over()
{
    tr_life -= 1;
    if (tr_ft >= 0)
    {
        tr_ft = tr_ft + 1;
        if (tr_ft >= END_N)
        {
            tr_ft = -1;
            tr_fill = 0;
        }
    }
    if (tr_life <= 0 || tr_slot < 0 || tr_vanish && tr_ft < 0
        || tr_over_t && tr_ft < 0 && tr_n > 1 && (tr_gone & (tr_bit(tr_n - 1) - 1)) == tr_bit(tr_n - 1) - 1)
    {
        BattleObject(0x9);      // its time's up, or all its pieces are gone and its fill is over
        return 0x1;
    }
    return 0;
}

void func_46()
{
    int k;
    tr_slot = tr_find_owner();
    tr_life = LIFE_N;
    tr_n = 0;
    tr_over_t = 0;
    tr_mark = 0;
    tr_gone = 0;
    tr_fill = 0;
    tr_ft = -1;
    tr_vanish = 0;
    tr_lr = PostureModuleF(0);
    if (tr_lr == 0.0f)
    {
        tr_lr = 1.0f;
    }
    k = 0;
    while (k < JUNC_N)
    {
        tr_set_j(k, -1, 0);
        k = k + 1;
    }
    tr_ox = PostureModuleF(0x1);
    tr_oy = PostureModuleF(0x2);
    tr_base = 0;
    if (tr_slot >= 0)
    {
        tr_base = (int)tr_shared(0x6);
        tr_unpack(tr_shared(0x5));
        tr_ox = tr_px;
        tr_oy = tr_py;
        PostureModule(0x2714, tr_ox, tr_oy, WorkModuleF(0, 0x0f000022 + 0x4 * tr_slot));
    }
    tr_cx = tr_ox;
    tr_cy = tr_oy;
    tr_set(0, tr_ox, tr_oy);
    tr_n = 1;
    tr_seen = tr_base;
    tr_sx = tr_ox;
    tr_sy = tr_oy;
    tr_still();
    tr_pose();
    func_24(0, 0, 1.0f);
    callFunc3(func_47);
}

void func_47()
{
    if (tr_over())
    {
        return 0x1;
    }
    tr_still();
    tr_take();
    tr_pose();
}
'''
    reps = {'POINTS_N': POINTS, 'LIFE_N': LIFE, 'DELAY_N': FILL_DELAY, 'GROW_N': FILL_GROW, 'HOLD_N': FILL_HOLD,
            'END_N': FILL_END, 'A_BONE_N': A_BONE, 'C_BONE_N': C_BONE, 'W_BONE_N': W_BONE,
            'SHOT_FROM_N': SHOT_FROM, 'COMMIT_V': '%.1ff' % COMMIT, 'CANCEL_V': '%.1ff' % CANCEL, 'JUNC_N': JUNCTIONS, 'EXT_N': '%.1ff' % EXT, 'KEEP_N': KEEP, 'SCALE_V': '%.2ff' % FILL_SCALE, 'SUM1_V': '%.1ff' % SUM1, 'SUM2_V': '%.1ff' % SUM2, 'SUM3_V': '%.1ff' % SUM3}
    for k, v in sorted(reps.items(), key=lambda kv: -len(kv[0])):
        body = body.replace(k, str(v))
    body = (body.replace('GETX', ifchain('        return tr_x#;'))
            .replace('GETY', ifchain('        return tr_y#;'))
            .replace('SETXY', ifchain('        tr_x# = x;\n        tr_y# = y;'))
            .replace('GETJK', ifchain('        return tr_jk#;', JUNCTIONS))
            .replace('GETJN', ifchain('        return tr_jn#;', JUNCTIONS))
            .replace('SETJ', ifchain('        tr_jk# = p;\n        tr_jn# = n;', JUNCTIONS)))
    return base + head + body


if __name__ == '__main__':
    path = os.path.join(EDGE, 'weapons', 'trail.c')
    open(path, 'w').write(generate())
    print('wrote %s (%d points)' % (path, POINTS))
