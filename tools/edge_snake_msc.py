#!/usr/bin/env python3
"""Sephiroth's held forward air (the extending "snake" sword): writes its MSC-C block into fighters/edge/edge.c
(between the SNAKE markers, appended at the end the first time) and hooks it into the aerial status (0x34:
main func_315, loop func_319, end slot 2) and the per-frame system line (func_74).

  python3 tools/edge_snake_msc.py [fighters/edge/edge.c]

The design: fighters/edge/snake_fair.md. MSC-C has no arrays, so the runs of the path (direction x 1000 + length)
are this object's VAR_0 - VAR_12 (0x0F000300 + k, tools/acmd_ext_cave.py), and the caught fighters (per player slot:
path position, -1 when not caught, and offset) numbered globals through generated if-chain helpers: the MSC's
globals stay under 0x86, the most seen working (tools/port_check.py C5).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SEGMENTS = 13          # tools/snake_sword.py SPEC['segments']
JOINT_BLADE = 1005     # model.jtb table 1: SwordL1 1003, SwordR1 1004, then snake_sword.bone_names()
JOINT_SEG0 = 1006      # EdgeSnake01 .. EdgeSnake13 = 1006 .. 1018
JOINT_TIP = 1019
SLOTS = 8

BEGIN = '// ==== SNAKE FAIR (tools/edge_snake_msc.py) ===='
END = '// ==== SNAKE FAIR END ===='


def indexed(kind, name, count, base=1):
    """getter / setter if-chains over globals name1..nameN"""
    g = ''.join('%s %s%d;\n' % (kind, name, k) for k in range(base, base + count))
    get = '%s %s(int k)\n{\n' % (kind, name)
    for k in range(base, base + count):
        get += '    if (k == %d)\n    {\n        return %s%d;\n    }\n' % (k, name, k)
    get += '    return %s;\n}\n' % ('0' if kind == 'int' else '0.0f')
    put = 'void %s_set(int k, %s v)\n{\n' % (name, kind)
    for k in range(base, base + count):
        put += '    if (k == %d)\n    {\n        %s%d = v;\n    }\n' % (k, name, k)
    put += '}\n'
    return g, get + '\n' + put


BODY = r'''
// constants (model units; the path lies in the fighter's model plane: h forward (+Z), v up (+Y))
int   edge_sn_motion() { return 0x69; }        // AttackAirF (func_311)
float edge_sn_hold() { return 6.0f; }          // held this many frames: the extending version
float edge_sn_freeze() { return 13.0f; }       // the frame the sword points straight ahead (its hit frame)
float edge_sn_speed() { return 3.0f; }         // the tip's speed while a direction is held
float edge_sn_retract() { return 6.0f; }       // the speed back along the path once the button is let go
float edge_sn_turn_wait() { return 8.0f; }     // frames between turns
float edge_sn_max() { return 300.0f; }         // the path's length at most
float edge_sn_back_min() { return 24.0f; }     // back only once the tip is this far past the sword's own reach
float edge_sn_gap() { return 3.0f; }           // the tip keeps this far off the sword's other runs
float edge_sn_grav() { return 0.7f; }          // gravity x this while extending / retracting
float edge_sn_catch() { return 22.0f; }        // a fighter hit, its feet within this of the tip, is caught
float edge_sn_base_x() { return -0.51f; }      // the blade's start at the freeze frame (Ultimate's c05attackairf
float edge_sn_base_v() { return 13.35f; }      // frame 13, swordl1 x (0.818, 0, 0.048)), along +Z there
float edge_sn_base_h() { return 11.06f; }
float edge_sn_blade() { return 21.98f; }       // the blade's body (0.82 - 22.80 along the sword)
float edge_sn_tip() { return 3.48f; }          // its point
float edge_sn_hidden() { return 0.001f; }      // a hidden piece's scale
int   edge_sn_var() { return 0x0f000317; }     // VAR_23: 0 the normal move, 1 extending, 2 the end hit (ACMD)

int   edge_sn_state;      // 0 off, 1 checking the hold, 2 held (to the freeze), 3 extending, 4 retracting, 5 end hit
int   edge_sn_released;   // the button let go between the hold check and the freeze
int   edge_sn_n;          // runs in the path
float edge_sn_since;      // frames since the last turn
float edge_sn_total;      // the path's length
float edge_sn_back;       // retracted so far
float edge_sn_scale;      // model -> world (Character Size Multiplier)
float edge_sn_ph;         // edge_sn_point's result
float edge_sn_pv;
int   edge_sn_pd;

// run k (1..13): VAR_(k-1) of this object, direction x 1000 + length (globals are scarce: tools/port_check.py C5)
int edge_sn_d(int k)
{
    float v;
    v = WorkModuleF(0, 0x0f000300 + k - 1);
    if (v >= 3000.0f)
    {
        return 3;
    }
    if (v >= 2000.0f)
    {
        return 2;
    }
    if (v >= 1000.0f)
    {
        return 1;
    }
    return 0;
}

float edge_sn_l(int k)
{
    float v;
    v = WorkModuleF(0, 0x0f000300 + k - 1);
    while (v >= 1000.0f)
    {
        v = v - 1000.0f;
    }
    return v;
}

void edge_sn_run_set(int k, int d, float l)
{
    WorkModule(0, (float)d * 1000.0f + l, 0x0f000300 + k - 1);
}

float edge_sn_dh(int d)
{
    if (d == 0)
    {
        return 1.0f;
    }
    if (d == 2)
    {
        return -1.0f;
    }
    return 0.0f;
}

float edge_sn_dv(int d)
{
    if (d == 1)
    {
        return 1.0f;
    }
    if (d == 3)
    {
        return -1.0f;
    }
    return 0.0f;
}

void edge_sn_setvar(float v)
{
    WorkModule(0, v, edge_sn_var());
}

// the point s along the path (clamped to it) -> edge_sn_ph / pv, the run's direction edge_sn_pd
void edge_sn_point(float s)
{
    int k;
    int d;
    float h;
    float v;
    float l;
    h = edge_sn_base_h();
    v = edge_sn_base_v();
    d = 0;
    if (s < 0.0f)
    {
        s = 0.0f;
    }
    k = 1;
    while (k <= edge_sn_n)
    {
        d = edge_sn_d(k);
        l = edge_sn_l(k);
        if (s <= l || k == edge_sn_n)
        {
            if (s > l)
            {
                s = l;
            }
            edge_sn_ph = h + s * edge_sn_dh(d);
            edge_sn_pv = v + s * edge_sn_dv(d);
            edge_sn_pd = d;
            return;
        }
        h = h + l * edge_sn_dh(d);
        v = v + l * edge_sn_dv(d);
        s = s - l;
        k = k + 1;
    }
    edge_sn_ph = h;
    edge_sn_pv = v;
    edge_sn_pd = d;
}

float edge_sn_abs(float a)
{
    if (a < 0.0f)
    {
        return -a;
    }
    return a;
}

// distance (the larger axis gap: runs are axis-aligned) from (h, v) to run k
float edge_sn_dist(int k, float h, float v)
{
    int j;
    float h0;
    float v0;
    float h1;
    float v1;
    float l;
    float t;
    float dh;
    float dv;
    int d;
    h0 = edge_sn_base_h();
    v0 = edge_sn_base_v();
    j = 1;
    while (j < k)
    {
        d = edge_sn_d(j);
        l = edge_sn_l(j);
        h0 = h0 + l * edge_sn_dh(d);
        v0 = v0 + l * edge_sn_dv(d);
        j = j + 1;
    }
    d = edge_sn_d(k);
    l = edge_sn_l(k);
    h1 = h0 + l * edge_sn_dh(d);
    v1 = v0 + l * edge_sn_dv(d);
    if (h1 < h0)
    {
        t = h0;
        h0 = h1;
        h1 = t;
    }
    if (v1 < v0)
    {
        t = v0;
        v0 = v1;
        v1 = t;
    }
    dh = 0.0f;
    if (h < h0)
    {
        dh = h0 - h;
    }
    if (h > h1)
    {
        dh = h - h1;
    }
    dv = 0.0f;
    if (v < v0)
    {
        dv = v0 - v;
    }
    if (v > v1)
    {
        dv = v - v1;
    }
    if (dh > dv)
    {
        return dh;
    }
    return dv;
}

// would the tip (its body's end at (h, v), its point ahead in direction d) come within the gap of another run
int edge_sn_blocked(float h, float v, int d)
{
    int k;
    float th;
    float tv;
    th = h + edge_sn_tip() * edge_sn_dh(d);
    tv = v + edge_sn_tip() * edge_sn_dv(d);
    k = 1;
    while (k < edge_sn_n - 1)
    {
        if (edge_sn_dist(k, h, v) < edge_sn_gap() || edge_sn_dist(k, th, tv) < edge_sn_gap())
        {
            return 0x1;
        }
        k = k + 1;
    }
    return 0;
}

// a piece's bone: placed at (h, v), turned along d, its X stretched to len (ModelModule 7 / 1 / 0)
void edge_sn_piece(int joint, float h, float v, int d, float len)
{
    float ry;
    float rz;
    ry = 0.0f;
    rz = 0.0f;
    if (d == 0)
    {
        ry = -90.0f;
    }
    if (d == 2)
    {
        ry = 90.0f;
    }
    if (d == 1)
    {
        rz = 90.0f;
    }
    if (d == 3)
    {
        rz = -90.0f;
    }
    ModelModule(0x7, joint, edge_sn_base_x(), v, h);
    ModelModule(0x1, joint, 0.0f, ry, rz, 0);
    ModelModule(0, joint, len, 1.0f, 1.0f);
}

void edge_sn_hide_piece(int joint)
{
    ModelModule(0, joint, edge_sn_hidden(), edge_sn_hidden(), edge_sn_hidden());
}

// the snake's pieces hidden and the real blade shown (or the other way round)
void edge_sn_show_blade(int show)
{
    int k;
    if (show)
    {
        ModelModule(0, BLADE, 1.0f, 1.0f, 1.0f);
        k = 0;
        while (k < SEGMENTS)
        {
            edge_sn_hide_piece(SEG0 + k);
            k = k + 1;
        }
        edge_sn_hide_piece(TIP);
    }
    else
    {
        edge_sn_hide_piece(BLADE);
    }
}

// the path drawn up to length len: each run its bone, the point at the end
void edge_sn_pose(float len)
{
    int k;
    int d;
    float h;
    float v;
    float l;
    float acc;
    h = edge_sn_base_h();
    v = edge_sn_base_v();
    acc = 0.0f;
    d = 0;
    k = 1;
    while (k <= SEGMENTS)
    {
        l = 0.0f;
        if (k <= edge_sn_n)
        {
            l = edge_sn_l(k);
            if (acc + l > len)
            {
                l = len - acc;
            }
        }
        if (l > 0.0f)
        {
            d = edge_sn_d(k);
            edge_sn_piece(SEG0 + k - 1, h, v, d, l);
            h = h + l * edge_sn_dh(d);
            v = v + l * edge_sn_dv(d);
            acc = acc + l;
        }
        else
        {
            edge_sn_hide_piece(SEG0 + k - 1);
        }
        k = k + 1;
    }
    edge_sn_piece(TIP, h, v, d, edge_sn_tip());
}

int edge_sn_cardinal()
{
    float x;
    float y;
    x = WorkModuleF(0, 0x0f000110);    // SELF_STICK_X: along his facing
    y = WorkModuleF(0, 0x0f000111);
    if (edge_sn_abs(x) < 0.5f && edge_sn_abs(y) < 0.5f)
    {
        return -1;
    }
    if (edge_sn_abs(x) >= edge_sn_abs(y))
    {
        if (x > 0.0f)
        {
            return 0;
        }
        return 2;
    }
    if (y > 0.0f)
    {
        return 1;
    }
    return 3;
}

// one frame of steering: a held direction moves the tip on (turning when allowed), none stops it
void edge_sn_steer()
{
    int want;
    int cur;
    int opp;
    int ok;
    float step;
    float h;
    float v;
    float l;
    float fwd;
    want = edge_sn_cardinal();
    edge_sn_since = edge_sn_since + 1.0f;
    if (want < 0)
    {
        return;
    }
    cur = edge_sn_d(edge_sn_n);
    if (want != cur)
    {
        ok = 0x1;
        opp = cur + 2;
        if (opp >= 4)
        {
            opp = opp - 4;
        }
        if (edge_sn_since < edge_sn_turn_wait() || edge_sn_n >= SEGMENTS || want == opp)
        {
            ok = 0;
        }
        if (want == 2)
        {
            edge_sn_point(edge_sn_total);
            fwd = edge_sn_ph - edge_sn_base_h();
            if (fwd < edge_sn_blade() + edge_sn_back_min())
            {
                ok = 0;
            }
        }
        if (ok == 0)
        {
            return;
        }
        edge_sn_n = edge_sn_n + 1;
        edge_sn_run_set(edge_sn_n, want, 0.0f);
        edge_sn_since = 0.0f;
        cur = want;
    }
    step = edge_sn_speed();
    if (edge_sn_total + step > edge_sn_max())
    {
        step = edge_sn_max() - edge_sn_total;
    }
    if (step <= 0.0f)
    {
        return;
    }
    edge_sn_point(edge_sn_total);
    h = edge_sn_ph + step * edge_sn_dh(cur);
    v = edge_sn_pv + step * edge_sn_dv(cur);
    if (edge_sn_blocked(h, v, cur))
    {
        return;
    }
    l = edge_sn_l(edge_sn_n);
    edge_sn_run_set(edge_sn_n, cur, l + step);
    edge_sn_total = edge_sn_total + step;
}

int edge_sn_slot_var(int slot, int q)
{
    return 0x0f000058 + 0x8 * (slot - 1) + q;    // player slot's hitstun (+0) / hitstop (+4) / offset X, Y (+5, +6)
}

// fighters the tip has just hit: caught where they are, relative to the tip
void edge_sn_catch_new()
{
    int slot;
    float ox;
    float oy;
    float th;
    float tv;
    float dx;
    float dy;
    if (WorkModuleF(0, 0x0f0000a0) != 1.0f)       // SELF_HIT: the tip has connected since the last check
    {
        return;
    }
    WorkModule(0, 0.0f, 0x0f0000a0);              // back to 0 (AttackModule 0x2724), for the next one
    edge_sn_point(edge_sn_total - edge_sn_back);
    th = edge_sn_ph + edge_sn_tip() * 0.5f * edge_sn_dh(edge_sn_pd);
    tv = edge_sn_pv + edge_sn_tip() * 0.5f * edge_sn_dv(edge_sn_pd);
    slot = 1;
    while (slot <= SLOTS)
    {
        if (edge_sn_s(slot) < 0.0f && WorkModuleF(0, edge_sn_slot_var(slot, 0)) > 0.0f)
        {
            ox = WorkModuleF(0, edge_sn_slot_var(slot, 5)) / edge_sn_scale;
            oy = WorkModuleF(0, edge_sn_slot_var(slot, 6)) / edge_sn_scale;
            dx = ox - th;
            dy = oy - tv;
            if ((ox != 0.0f || oy != 0.0f) && dx * dx + dy * dy < edge_sn_catch() * edge_sn_catch())
            {
                edge_sn_s_set(slot, edge_sn_total - edge_sn_back);
                edge_sn_oh_set(slot, ox - edge_sn_ph);
                edge_sn_ov_set(slot, oy - edge_sn_pv);
            }
        }
        slot = slot + 1;
    }
}

// the caught fighters held on the path (frozen: hitstop and hitstun refreshed), each where it was hit, moving
// back along the path as the sword retracts
void edge_sn_hold_caught()
{
    int slot;
    float s;
    slot = 1;
    while (slot <= SLOTS)
    {
        if (edge_sn_s(slot) >= 0.0f)
        {
            s = edge_sn_s(slot) - edge_sn_back;
            if (s < edge_sn_blade() * 0.6f)
            {
                s = edge_sn_blade() * 0.6f;
            }
            edge_sn_point(s);
            WorkModule(0, (edge_sn_ph + edge_sn_oh(slot)) * edge_sn_scale, edge_sn_slot_var(slot, 5));
            WorkModule(0, (edge_sn_pv + edge_sn_ov(slot)) * edge_sn_scale, edge_sn_slot_var(slot, 6));
            WorkModule(0, 2.0f, edge_sn_slot_var(slot, 4));
            WorkModule(0, 20.0f, edge_sn_slot_var(slot, 0));
        }
        slot = slot + 1;
    }
}

// let go of the caught fighters: drop (landing, interrupted) or leave them in hitstun for the end hit
void edge_sn_release(int drop)
{
    int slot;
    slot = 1;
    while (slot <= SLOTS)
    {
        if (edge_sn_s(slot) >= 0.0f && drop)
        {
            WorkModule(0, 0.0f, edge_sn_slot_var(slot, 0));
        }
        edge_sn_s_set(slot, -1.0f);
        slot = slot + 1;
    }
}

void edge_sn_gravity(float mul)
{
    KineticModule(0xf, 0x1, -(WorkModuleF(0, 0x3000018) * mul));
}

// the aerial status's main: the move picked; the hold check starts if it's forward air with the button held
void edge_sn_init()
{
    edge_sn_setvar(0.0f);
    edge_sn_state = 0;
    edge_sn_released = 0;
    edge_sn_release(0);
    if (MotionModule(0x7) == edge_sn_motion() && WorkModuleF(0, 0x0f000100) == 1.0f)
    {
        edge_sn_state = 0x1;
    }
}

void edge_sn_begin()
{
    int k;
    MotionModule(0x4, 0.0f);
    edge_sn_scale = WorkModuleF(0, 0x300002c);
    if (edge_sn_scale <= 0.0f)
    {
        edge_sn_scale = 1.0f;
    }
    edge_sn_n = 1;
    edge_sn_run_set(1, 0, edge_sn_blade());
    k = 2;
    while (k <= SEGMENTS)
    {
        edge_sn_run_set(k, 0, 0.0f);
        k = k + 1;
    }
    edge_sn_total = edge_sn_blade();
    edge_sn_back = 0.0f;
    edge_sn_since = edge_sn_turn_wait();
    edge_sn_show_blade(0);
    edge_sn_state = 0x3;
    if (edge_sn_released)
    {
        edge_sn_state = 0x4;
    }
}

void edge_sn_finish()
{
    edge_sn_release(0);
    edge_sn_show_blade(0x1);
    edge_sn_gravity(1.0f);
    edge_sn_setvar(2.0f);
    edge_sn_state = 0x5;
    MotionModule(0x4, 1.0f);
}

// the aerial status's loop, every frame
void edge_sn_loop()
{
    float f;
    int held;
    if (edge_sn_state == 0 || edge_sn_state == 0x5)
    {
        return;
    }
    f = MotionModuleF(0x1);
    held = 0;
    if (WorkModuleF(0, 0x0f000100) == 1.0f)    // SELF_ATTACK held
    {
        held = 0x1;
    }
    if (edge_sn_state == 0x1)
    {
        if (held == 0)
        {
            edge_sn_state = 0;
            return;
        }
        if (f >= edge_sn_hold())
        {
            edge_sn_state = 0x2;
            edge_sn_setvar(1.0f);
        }
        return;
    }
    if (edge_sn_state == 0x2)
    {
        if (held == 0)
        {
            edge_sn_released = 0x1;
        }
        if (f >= edge_sn_freeze())
        {
            edge_sn_begin();
        }
        else
        {
            return;
        }
    }
    edge_sn_gravity(edge_sn_grav());
    if (edge_sn_state == 0x3)
    {
        if (held == 0)
        {
            edge_sn_state = 0x4;
        }
        else
        {
            edge_sn_steer();
        }
    }
    if (edge_sn_state == 0x4)
    {
        edge_sn_back = edge_sn_back + edge_sn_retract();
        if (edge_sn_total - edge_sn_back <= edge_sn_blade())
        {
            edge_sn_back = edge_sn_total - edge_sn_blade();
            edge_sn_hold_caught();
            edge_sn_finish();
            return;
        }
    }
    edge_sn_catch_new();
    edge_sn_hold_caught();
    edge_sn_pose(edge_sn_total - edge_sn_back);
}

// the aerial status's end (landing, a hit, ...): anyone caught dropped, the sword back
void edge_sn_end()
{
    if (edge_sn_state >= 0x3 && edge_sn_state <= 0x4)
    {
        edge_sn_release(0x1);
        edge_sn_show_blade(0x1);
    }
    edge_sn_release(0);
    edge_sn_state = 0;
    edge_sn_setvar(0.0f);
}

// every frame (func_74): outside the move, the snake's pieces hidden and the real blade shown (they persist,
// but a respawn resets the model)
void edge_sn_frame()
{
    if (edge_sn_state < 0x3)
    {
        edge_sn_show_blade(0x1);
    }
}
'''


def block():
    gl, fn = [], []
    for kind, name, n in (('float', 'edge_sn_s', SLOTS), ('float', 'edge_sn_oh', SLOTS), ('float', 'edge_sn_ov', SLOTS)):
        g, f = indexed(kind, name, n)
        gl.append(g)
        fn.append(f)
    body = BODY.replace('BLADE', str(JOINT_BLADE)).replace('SEG0', str(JOINT_SEG0)).replace('TIP,', '%d,' % JOINT_TIP)
    body = body.replace('(TIP)', '(%d)' % JOINT_TIP).replace('SEGMENTS', str(SEGMENTS)).replace('SLOTS', str(SLOTS))
    assert not re.search(r'\b(BLADE|SEG0|TIP|SEGMENTS|SLOTS)\b', body), 'placeholder left'
    return '\n'.join([BEGIN, '// Sephiroth: held forward air, the extending sword (fighters/edge/snake_fair.md)', ''.join(gl),
                      '\n'.join(fn), body, END]) + '\n'


HOOKS = [
    # (function, the line to find in it, what to put before / after)
    ('func_315', '    func_314();\n', 'after', '    edge_sn_init();          // Sephiroth: held forward air\n'),
    ('func_319', '    if (func_318())\n', 'before', '    edge_sn_loop();          // Sephiroth: held forward air\n'),
    ('func_74', '    func_77();\n', 'after', '    edge_sn_frame();         // Sephiroth: held forward air\n'),
]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'fighters/edge/edge.c')
    src = open(path).read()
    if BEGIN in src:
        src = src[:src.index(BEGIN)] + block() + src[src.index(END) + len(END) + 1:]
    else:
        src = src.rstrip('\n') + '\n\n' + block()
    for fn, line, where, add in HOOKS:
        m = re.search(r'\n[a-z]+ %s\(\)\n\{\n' % fn, src)
        assert m, fn
        start = m.end()
        stop = src.index('\n}\n', start)
        part = src[start:stop + 1]
        if add in part:
            continue
        assert line in part, (fn, line)
        part = part.replace(line, line + add if where == 'after' else add + line, 1)
        src = src[:start] + part + src[stop + 1:]
    # the aerial status's end (slot 2, empty func_334 in the base)
    reg = 'sv_set_mem(0x1, 0x2, 0x34, func_334);'
    if reg in src:
        src = src.replace(reg, 'sv_set_mem(0x1, 0x2, 0x34, edge_sn_end);  // Sephiroth: held forward air (was func_334, empty)')
    open(path, 'w').write(src)
    print('snake fair block: %d lines' % block().count('\n'))


if __name__ == '__main__':
    main()
