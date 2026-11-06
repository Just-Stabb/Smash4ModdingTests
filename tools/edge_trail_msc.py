#!/usr/bin/env python3
"""Sephiroth's up special trail article (fighters/edge/specials.md "Up special", test 124): writes
fighters/edge/weapons/trail.c = the snake run's base (Zelda's dein, fighters/edge/weapons/snake.c up to its own
section) + the trail's code. MSC-C has no arrays, so its POINTS points are numbered globals behind generated if-chains.

One article draws one stretch of the path: up to POINTS points (POINTS - 1 pieces), its model's joints P0 - P15
(tools/edge_snake_articles.py build_trail: ribbons between consecutive joints) moved to them every frame, relative to
its first point (ModelModule(0x7, 0x7D2 + k, depth, y, x): its facing 1 turns its model +Z to the world's +X).
Sephiroth (edge.c edge_tr_*) talks to the articles through his shared variables 4 - 6 (test 125, stage 3):
  5: the newest point (packed: (x + 512) x 2 x 2048 + (y + 512) x 2); 6: its number (from 1000), -1 once the trail is
  over (every article seeing it is stale from then: it takes, tests and answers nothing more), or a query: start x 512
  + count + 0.5 (5 and 4 are then sums the articles add to: their points numbered start .. start + count - 1, x into 5,
  y into 4, once a query);
  4: a closed shape: an article whose own piece (m, m + 1) the newest piece (number - 1, number) crosses (not one
  next to it) writes -m there (the latest m wins: the smallest loop); he reads and clears it each frame.
An article takes the newest point while its number follows its last and is within its stretch (its first point's
number + POINTS - 1).

  python3 tools/edge_trail_msc.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EDGE = os.path.join(ROOT, 'fighters', 'edge')
POINTS = 16
LIFE = 360          # the user: "persists for 6 seconds"


def ifchain(fmt):
    return '\n'.join('    if (k == %d)\n    {\n%s\n    }' % (k, fmt.replace('#', str(k))) for k in range(POINTS))


def generate():
    src = open(os.path.join(EDGE, 'weapons', 'snake.c')).read()
    base = src[:src.index("// ---- Sephiroth's held forward air (tools/edge_snake_articles_msc.py)")]
    head = '''// ---- Sephiroth's up special trail (tools/edge_trail_msc.py; test 124): one stretch of the purple line his path leaves
// during either up special's attack, up to %d points; still, removed after %d frames
int tr_slot;            // his player slot (0 - 7), -1: not found
int tr_life;            // frames left
int tr_base;            // its first point's number
int tr_seen;            // the newest point's number seen
int tr_n;               // points taken
int tr_stale;           // 1: the trail it belongs to is over: it does nothing more
int tr_answered;        // the last query answered
float tr_sx;            // the newest point seen
float tr_sy;
float tr_ox;            // its first point (where it stands)
float tr_oy;
float tr_px;            // tr_unpack's result
float tr_py;
''' % (POINTS, LIFE)
    head += ''.join('float tr_x%d;\nfloat tr_y%d;\n' % (k, k) for k in range(POINTS))
    body = '''
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
    if ((d1 > 0.0f && d2 < 0.0f || d1 < 0.0f && d2 > 0.0f) && (d3 > 0.0f && d4 < 0.0f || d3 < 0.0f && d4 > 0.0f))
    {
        return 0x1;
    }
    return 0;
}

// the newest piece (tr_sx, tr_sy) - (x, y), number num - 1 - num, against this stretch's own pieces not next to it: a
// crossing at piece m (its start's number) is reported in shared 4 as -m, the latest m kept
void tr_test(float x, float y, int num)
{
    int k;
    int m;
    float r;
    k = 0;
    while (k < tr_n - 1 && tr_base + k + 1 <= num - 2)
    {
        if (tr_cross(tr_sx, tr_sy, x, y, tr_get_x(k), tr_get_y(k), tr_get_x(k + 1), tr_get_y(k + 1)))
        {
            m = tr_base + k;
            r = tr_shared(0x4);
            if (r > -1000.0f || (float)m > -r)
            {
                WorkModule(0, -(float)m, 0x0f000340 + 0x8 * tr_slot + 0x4);
            }
        }
        k = k + 1;
    }
}

// a query (shared 6 = start x 512 + count + 0.5): its points numbered start .. start + count - 1 added to shared 5 (x)
// and 4 (y), once
void tr_answer(float v)
{
    int code;
    int st;
    int cnt;
    int k;
    float sx;
    float sy;
    code = (int)v;
    if (code == tr_answered)
    {
        return;
    }
    tr_answered = code;
    st = code / 0x200;
    cnt = code - st * 0x200;
    sx = 0.0f;
    sy = 0.0f;
    k = 0;
    while (k < tr_n)
    {
        // its first point is the stretch before's last: counted there (but the trail's first)
        if (tr_base + k >= st && tr_base + k < st + cnt && (k > 0 || tr_base == 1000))
        {
            sx = sx + tr_get_x(k);
            sy = sy + tr_get_y(k);
        }
        k = k + 1;
    }
    WorkModule(0, tr_shared(0x5) + sx, 0x0f000340 + 0x8 * tr_slot + 0x5);
    WorkModule(0, tr_shared(0x4) + sy, 0x0f000340 + 0x8 * tr_slot + 0x4);
}

// every frame: stale once the trail's over; a query answered; a new point tested against its pieces, and taken if it's
// this stretch's next
void tr_take()
{
    float v;
    int num;
    if (tr_stale || tr_slot < 0)
    {
        return;
    }
    v = tr_shared(0x6);
    if (v < 0.0f)
    {
        tr_stale = 0x1;
        return;
    }
    if (v - (float)((int)v) > 0.25f)
    {
        tr_answer(v);
        return;
    }
    num = (int)v;
    if (num <= tr_seen)
    {
        return;
    }
    tr_unpack(tr_shared(0x5));
    if (num == tr_seen + 1)
    {
        tr_test(tr_px, tr_py, num);
    }
    if (num == tr_base + tr_n && tr_n < tr_points())
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

// the joints: P_k at point k (the last taken for those past it), relative to the first point
void tr_pose()
{
    int k;
    int j;
    PostureModule(0, 1.0f);
    PostureModule(0x2714, tr_ox, tr_oy, PostureModuleF(0x3));
    k = 0;
    while (k < tr_points())
    {
        j = k;
        if (j > tr_n - 1)
        {
            j = tr_n - 1;
        }
        ModelModule(0x7, 0x7d2 + k, 0, tr_get_y(j) - tr_oy, tr_get_x(j) - tr_ox);
        k = k + 1;
    }
}

int tr_over()
{
    tr_life -= 1;
    if (tr_life <= 0 || tr_slot < 0)
    {
        BattleObject(0x9);
        return 0x1;
    }
    return 0;
}

void func_46()
{
    tr_slot = tr_find_owner();
    tr_life = LIFE_N;
    tr_n = 0;
    tr_stale = 0;
    tr_answered = 0;
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
    body = (body.replace('POINTS_N', str(POINTS)).replace('LIFE_N', str(LIFE))
            .replace('GETX', ifchain('        return tr_x#;'))
            .replace('GETY', ifchain('        return tr_y#;'))
            .replace('SETXY', ifchain('        tr_x# = x;\n        tr_y# = y;')))
    return base + head + body


if __name__ == '__main__':
    path = os.path.join(EDGE, 'weapons', 'trail.c')
    open(path, 'w').write(generate())
    print('wrote %s (%d points)' % (path, POINTS))
