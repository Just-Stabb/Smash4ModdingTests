#!/usr/bin/env python3
"""Sephiroth's held forward air (the extending "snake" sword): writes its MSC-C block into fighters/edge/edge.c
(between the SNAKE markers, appended at the end the first time) and hooks it into the aerial status (0x34:
main func_315, loop func_319, end slot 2); since test 82 its sword is drawn by articles (snake / snaketip, tools/edge_snake_articles*.py).

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

SEGMENTS = 12          # the path's runs at most: the run articles (tools/extra_kinds.json snake max 12)
JOINT_BLADE = 1003     # EdgeBladeL (bone 26): his model.jtb table 1's 4th entry in every costume (124/105, 123/100, 12, 26).
                       # The joint overrides are the MotionModule's, by joint ID as ACMD's: table 0 below 1000 (26
                       # entries: tests 82-84's 26 was past it), table 1 from 1000 (test 79's 1005+ were accepted: 15
                       # entries crashed him); 0x7D0 + n is a weapon's jtb entry n (Mario's pump), not a fighter's (test 85)
ART_RUN = 9            # his article list (Zelda's 0 - 4, fire 5, flare1 6, flare2 7, flash 8): snake, snaketip
ART_TIP = 10
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
float edge_sn_hold() { return 6.0f; }          // held this many frames after the window opens: the extending version
// up tilt (status 0x29) works the same way (user, test 97: "make held Up tilt work the same way that held forward
// air does"; "for up tilt, make the default direction up"): edge_sn_move 1, its numbers from Ultimate's c02attackhi3
// (the sword straight up from motion frame 20, clean hit 20 - 22, late 23 - 32); on the ground, so no gravity change
int   edge_sn_move;       // the move held: 0 forward air, 1 up tilt

float edge_sn_window()                          // the hold window opens after the tapped move's clean hit
{
    if (edge_sn_move)
    {
        return 23.0f;                           // up tilt: clean hit 20 - 22
    }
    return 15.0f;                               // forward air: clean hit 13 - 14
}
// the frame the sword points straight ahead (its hit frame): the motion goes back to it and holds while the sword is out
float edge_sn_freeze()
{
    if (edge_sn_move)
    {
        return 20.0f;                           // up tilt: the sword straight up from frame 20 (c02attackhi3 frame 20:
    }                                           // swordl1 x (0, 1, 0))
    return 13.0f;
}
float edge_sn_speed() { return 3.0f; }         // the tip's speed while a direction is held
float edge_sn_retract() { return 6.0f; }       // the speed back along the path once the button is let go
float edge_sn_turn_wait() { return 8.0f; }     // frames between turns
float edge_sn_max() { return 300.0f; }         // the path's length at most
float edge_sn_back_min() { return 24.0f; }     // back only once the tip is this far past the sword's own reach
float edge_sn_down_side() { return 16.0f; }    // up tilt: down only once the tip is this far forward or back of the
                                               // sword's start (user, test 98)
float edge_sn_life() { return 300.0f; }        // the sword goes back by itself after this many frames out, held or
                                               // not: 5 seconds (user, test 98)
int   edge_sn_timer() { return 0x0f000316; }   // VAR_22: frames since the sword started to extend
int   edge_sn_hit_var() { return 0x0f000313; } // VAR_19: 1 once this move hit anyone (his hits or the point's catch)
float edge_sn_gap() { return 3.0f; }           // the tip keeps this far off the sword's other runs
float edge_sn_fall() { return 0.1f; }          // from the hold until the end hit is over: falling at this, steady
                                               // (no gravity), whatever his speed was (user, test 99: "not
                                               // accelerate downwards over time and set fall speed to something
                                               // extremely low"; tests 95 - 99: gravity x 0.1, still speeding up)
float edge_sn_grav_end() { return 19.0f; }     // the motion frame the end hit is over at (fair's own clear at 19):
                                               // his own gravity from there
float edge_sn_catch() { return 22.0f; }        // a fighter hit, its feet within this of the tip, is caught
float edge_sn_bz_side() { return 15.0f; }      // a caught fighter is kept this far inside the side / bottom blast
float edge_sn_bz_top() { return 30.0f; }       // zones, and its feet this far under the top one (user, test 101:
                                               // "when an opponent is attached ... they cannot be KO'd by the blast
                                               // zone"; StageData 0 / 1 / 2 / 3: left / right / top / bottom, as
                                               // the Dead status (func_220) clamps its KO place to them)
float edge_sn_centre() { return 7.0f; }        // a caught fighter is held with its middle this far above its feet on
                                               // the sword (game units: whoever's scale), so the hits that follow
                                               // the sword back find it (user, test 94)
float edge_sn_base_x() { return -0.51f; }      // the blade's start at the freeze frame (Ultimate's c05attackairf
float edge_sn_base_v()                          // frame 13, swordl1 x (0.818, 0, 0.048)), along +Z there; up tilt:
{                                               // c02attackhi3 frame 20, the hilt 1.14 forward, 26.36 up, the blade's
    if (edge_sn_move)                           // start 0.82 above it
    {
        return 27.18f;
    }
    return 13.35f;
}
float edge_sn_base_h()
{
    if (edge_sn_move)
    {
        return 1.14f;
    }
    return 11.06f;
}
int edge_sn_first()                             // the first run's direction (and with nothing held at the start):
{                                               // forward air forward, up tilt up
    return edge_sn_move;
}
float edge_sn_blade() { return 21.98f; }       // the blade's body (0.82 - 22.80 along the sword)
float edge_sn_tip() { return 3.48f; }          // its point
float edge_sn_hidden() { return 0.001f; }      // a hidden piece's scale
int   edge_sn_var() { return 0x0f000317; }     // VAR_23: 0 the normal move, 1 extending, 2 the end hit (ACMD)

int   edge_sn_state;      // 0 off, 1 checking the hold, 3 extending, 4 retracting, 5 end hit (low
                          // gravity), 6 over
int   edge_sn_hid;        // the blade hidden (1): shown again at the next aerial / up tilt if a move left it so
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

// the blade hidden (one joint override: EdgeBladeL scaled away) or shown again (scaled back to 1: ModelModule 2 left
// it hidden, test 86, the blade gone from every move after a held forward air)
void edge_sn_blade_hide(int hide)
{
    if (hide)
    {
        ModelModule(0, BLADE, edge_sn_hidden(), edge_sn_hidden(), edge_sn_hidden());
    }
    else
    {
        ModelModule(0, BLADE, 1.0f, 1.0f, 1.0f);
    }
    edge_sn_hid = hide;
}

// the path for the articles (tools/edge_snake_articles_msc.py): his VAR_24 - VAR_29 the runs, two a float (direction
// x 1024 + length x 2, the odd run in the low 12 bits), VAR_30 the length drawn (below 0: over)
void edge_sn_publish(float drawn)
{
    int i;
    int a;
    int b;
    float la;
    float lb;
    i = 0;
    while (i < SEGMENTS / 2)
    {
        la = edge_sn_l(2 * i + 1);
        lb = edge_sn_l(2 * i + 2);
        a = edge_sn_d(2 * i + 1) * 1024 + (int)(la * 2.0f + 0.5f);
        b = edge_sn_d(2 * i + 2) * 1024 + (int)(lb * 2.0f + 0.5f);
        if (2 * i + 1 > edge_sn_n)
        {
            a = 0;
        }
        if (2 * i + 2 > edge_sn_n)
        {
            b = 0;
        }
        WorkModule(0, (float)(a + b * 4096), 0x0f000318 + i);
        i = i + 1;
    }
    WorkModule(0, drawn, 0x0f00031e);
}

// the articles: SEGMENTS runs (each takes its number from VAR_31) and the point
void edge_sn_generate()
{
    int k;
    WorkModule(0, 0.0f, 0x0f00031f);
    k = 0;
    while (k < SEGMENTS)
    {
        ArticleModule(0x2710, ART_RUN);
        k = k + 1;
    }
    ArticleModule(0x2710, ART_TIP);
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
    cur = edge_sn_d(edge_sn_n);
    if (want < 0)               // no direction held: on the way it goes (user, test 92; the first run is forward,
                                // up tilt's up)
    {
        want = cur;
    }
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
        if (want == edge_sn_first() + 2)        // back on the first run's way (forward air: back; up tilt: down)
        {
            edge_sn_point(edge_sn_total);
            if (edge_sn_move)
            {
                // up tilt: once the tip is 16 forward or back of where the sword starts (user, test 98: "let up
                // tilt go down after moving 16 units forward or back"; test 98 had fair's rule, 24 past its reach up)
                if (edge_sn_abs(edge_sn_ph - edge_sn_base_h()) < edge_sn_down_side())
                {
                    ok = 0;
                }
            }
            else
            {
                // forward air: once the tip is well past the sword's own reach forward
                fwd = edge_sn_ph - edge_sn_base_h();
                if (fwd < edge_sn_blade() + edge_sn_back_min())
                {
                    ok = 0;
                }
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

// a player slot's stage collision (docs/position-variables.md, hit / status q 6: GroundModule(0x2710, value) on
// it): 0 none, as a grabbed fighter; 5 air
void edge_sn_ground(int slot, float kind)
{
    WorkModule(0, kind, 0x0f0000a0 + 0x8 * (slot + 2) + 0x6);
}

// fighters the tip has hit (in hitstun, their feet near the point: its hits are the article's, not his):
// caught where they are, relative to the tip
void edge_sn_catch_new()
{
    int slot;
    float ox;
    float oy;
    float th;
    float tv;
    float dx;
    float dy;
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
                // on the sword: its middle at the point's middle, not where the point found it (user, test 94:
                // "the initial hit doesn't forcibly align the opponent inside the sword", so on the way back it
                // was off the sword and the end hit missed it)
                edge_sn_s_set(slot, edge_sn_total - edge_sn_back);
                WorkModule(0, 1.0f, edge_sn_hit_var());
                edge_sn_oh_set(slot, th - edge_sn_ph);
                edge_sn_ov_set(slot, tv - edge_sn_pv - edge_sn_centre() / edge_sn_scale);
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
    float ox;
    float oy;
    float sx;
    float sy;
    float lr;
    float wx;
    float wy;
    float lo;
    float hi;
    slot = 1;
    while (slot <= SLOTS)
    {
        if (edge_sn_s(slot) >= 0.0f)
        {
            // where it was caught, until the sword, shortening from its end, gets back to it: then with the end
            // (user, test 93: "opponents attached should only travel back from the point of the sword that they are
            // on"; tests 79 - 93 moved them back by the retracted length at once, off the sword still out past them)
            s = edge_sn_s(slot);
            if (s > edge_sn_total - edge_sn_back)
            {
                s = edge_sn_total - edge_sn_back;
            }
            // (tests 79 - 101 stopped them 60% of the way out the blade: the end hit missed them; now they come to
            // the hilt, edge_sn_pull)
            edge_sn_point(s);
            ox = (edge_sn_ph + edge_sn_oh(slot)) * edge_sn_scale;
            oy = (edge_sn_pv + edge_sn_ov(slot)) * edge_sn_scale;
            // inside the blast zones whatever the sword does
            lr = PostureModuleF(0);
            sx = PostureModuleF(0x1);
            sy = PostureModuleF(0x2);
            wx = sx + lr * ox;
            wy = sy + oy;
            lo = StageData(0) + edge_sn_bz_side();
            hi = StageData(0x1) - edge_sn_bz_side();
            if (wx < lo)
            {
                wx = lo;
            }
            if (wx > hi)
            {
                wx = hi;
            }
            lo = StageData(0x3) + edge_sn_bz_side();
            hi = StageData(0x2) - edge_sn_bz_top();
            if (wy < lo)
            {
                wy = lo;
            }
            if (wy > hi)
            {
                wy = hi;
            }
            WorkModule(0, (wx - sx) * lr, edge_sn_slot_var(slot, 5));
            WorkModule(0, wy - sy, edge_sn_slot_var(slot, 6));
            WorkModule(0, 2.0f, edge_sn_slot_var(slot, 4));
            WorkModule(0, 20.0f, edge_sn_slot_var(slot, 0));
            if (edge_sn_state == 0x4)
            {
                // dragged back through the stage, not stopped by it (user, test 95: "Opponents being dragged back
                // towards the sword during the release shouldn't have stage collision")
                edge_sn_ground(slot, 0.0f);
            }
        }
        slot = slot + 1;
    }
}

// the sword back at its own length: the caught fighters still out on it pulled on toward the hilt, the retract's
// speed a frame (user, test 101: "make it so the opponent is dragged to the hilt rather than the closest base piece
// to the hilt because the final hit never connects"). 1 while any was still short of it
int edge_sn_pull()
{
    int slot;
    int any;
    float s;
    any = 0;
    slot = 1;
    while (slot <= SLOTS)
    {
        s = edge_sn_s(slot);
        if (s >= 0.0f)
        {
            if (s > edge_sn_total - edge_sn_back)
            {
                s = edge_sn_total - edge_sn_back;
            }
            if (s > 0.0f)
            {
                any = 0x1;
                s = s - edge_sn_retract();
                if (s < 0.0f)
                {
                    s = 0.0f;
                }
            }
            edge_sn_s_set(slot, s);
        }
        slot = slot + 1;
    }
    return any;
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
        if (edge_sn_s(slot) >= 0.0f)
        {
            WorkModule(0, 0.0f, edge_sn_slot_var(slot, 4));   // out of the hold's hitstop, for the end hit (test 105)
        }
        if (edge_sn_s(slot) >= 0.0f && edge_sn_state == 0x4)
        {
            edge_sn_ground(slot, 5.0f);         // stage collision back (in the air)
        }
        edge_sn_s_set(slot, -1.0f);
        slot = slot + 1;
    }
}

void edge_sn_gravity(float mul)
{
    if (edge_sn_move)
    {
        return;                                 // up tilt: on the ground
    }
    KineticModule(0xf, 0x1, -(WorkModuleF(0, 0x3000018) * mul));
}

// held forward air: no gravity, the fall speed set to edge_sn_fall every frame (the gravity energy's speed,
// KineticModule(0x11, 1, v), as func_81 sets it)
void edge_sn_float()
{
    if (edge_sn_move)
    {
        return;
    }
    edge_sn_gravity(0.0f);
    KineticModule(0x11, 0x1, -edge_sn_fall());
}

// 1 while the sword is out (extending or retracting): its caught fighters' places are live (edge.c's Phantom,
// edge_lw_ph_held: test 110)
int edge_sn_out()
{
    if (edge_sn_state == 0x3 || edge_sn_state == 0x4)
    {
        return 0x1;
    }
    return 0;
}

// the aerial's fast-fall checks (func_550 -> func_553 in func_316, func_555 in func_319) run only when this is 1: not
// from the hold to the move's end (user, test 92: holding down steers it, it mustn't fast fall him too; test 96:
// "fast falling still seems enabled on held forward air")
int edge_sn_free()
{
    if (edge_sn_state >= 0x3)
    {
        return 0;
    }
    return 0x1;
}

// no fast fall: its flag (0x21000001, set by func_553; tests 93 - 96 cleared 0x21000007, which isn't it) off, and
// one begun before the hold (the tapped move's frames) undone as func_81 does: the fall speed back to the max
// fall speed (0x3000019) if it is past it
void edge_sn_no_fastfall()
{
    float maxfall;
    if (WorkModule(0x10, 0x21000001))
    {
        WorkModule(0x2711, 0x21000001);
        maxfall = WorkModuleF(0, 0x3000019);
        if (KineticModuleF(0x1, 0x1) < -maxfall)
        {
            KineticModule(0x11, 0x1, -maxfall);
        }
    }
    WorkModule(0x2711, 0x21000007);
}

// func_316's func_550 without its fast fall (func_553) while the sword is out
void edge_sn_550()
{
    if (edge_sn_free())
    {
        func_550();
        return;
    }
    if (WorkModule(0x1c, 0x1f00000e))
    {
        func_105();
        func_104();
    }
    edge_sn_no_fastfall();
}

// the aerial status's main: the move picked; the hold check starts if it's forward air with the button held
void edge_sn_reset()
{
    WorkModule(0, 0.0f, edge_sn_hit_var());
    edge_sn_setvar(0.0f);
    edge_sn_state = 0;
    edge_sn_release(0);
    if (edge_sn_hid)
    {
        edge_sn_blade_hide(0);
    }
}

void edge_sn_init()
{
    edge_sn_reset();
    edge_sn_move = 0;
    if (MotionModule(0x7) == edge_sn_motion() && WorkModuleF(0, 0x0f000100) == 1.0f)
    {
        edge_sn_state = 0x1;
    }
}

// the up tilt status's main (func_278): the hold check starts if attack is held
void edge_sn_init_hi3()
{
    edge_sn_reset();
    edge_sn_move = 0x1;
    if (WorkModuleF(0, 0x0f000100) == 1.0f)
    {
        edge_sn_state = 0x1;
    }
}

void edge_sn_begin()
{
    int k;
    int m;
    m = WorkModule(0x6, 0x11000002);            // the aerial's motion (func_310): back to the freeze frame, held there
    if (edge_sn_move)
    {
        m = MotionModule(0x7);                  // up tilt's (func_278: FighterUtil(0x20))
    }
    func_22(m, edge_sn_freeze(), 1.0f);
    MotionModule(0x4, 0.0f);
    edge_sn_scale = WorkModuleF(0, 0x300002c);
    if (edge_sn_scale <= 0.0f)
    {
        edge_sn_scale = 1.0f;
    }
    edge_sn_n = 1;
    edge_sn_run_set(1, edge_sn_first(), edge_sn_blade());
    k = 2;
    while (k <= SEGMENTS)
    {
        edge_sn_run_set(k, 0, 0.0f);
        k = k + 1;
    }
    edge_sn_total = edge_sn_blade();
    edge_sn_back = 0.0f;
    edge_sn_since = edge_sn_turn_wait();
    WorkModule(0, 0.0f, edge_sn_timer());
    edge_sn_blade_hide(0x1);
    edge_sn_publish(edge_sn_total);
    edge_sn_generate();
    edge_sn_state = 0x3;
}

void edge_sn_finish()
{
    edge_sn_release(edge_sn_move == 0);         // forward air has no end hit since test 103: its caught drop
    edge_sn_blade_hide(0);
    edge_sn_publish(-1.0f);
    edge_sn_setvar(2.0f);
    edge_sn_state = 0x5;                        // still low gravity: normal at edge_sn_grav_end
    MotionModule(0x4, 1.0f);
}

// the held move's side special cancel (user, test 107: "make held up tilt and forward air cancellable into side
// special after the hilt reaches Sephiroth, specifically if he hit them with any part of the attack"): from the
// sword back at the hilt (state 5 on), if the move hit anyone (his own hits, SELF_HIT, or the point's catch), the
// side special input (global24 0x2000, as func_43 reads it; the status's own transition terms left out) goes into
// side special (0x153). Run first in the aerial / up tilt loops: 1 if it did
int edge_sn_cancel()
{
    if (edge_sn_state == 0)
    {
        return 0;
    }
    if (WorkModuleF(0, 0x0f0000a0) == 1.0f)    // SELF_HIT: his attack has connected
    {
        WorkModule(0, 1.0f, edge_sn_hit_var());
    }
    if (edge_sn_state >= 0x5 && WorkModuleF(0, edge_sn_hit_var()) == 1.0f && (global24 & 0x2000) != 0)
    {
        if (func_72(global25))
        {
            func_16(0x153, 0x1);
            return 0x1;
        }
    }
    return 0;
}

// the aerial status's loop, every frame
void edge_sn_loop()
{
    float f;
    int held;
    if (edge_sn_state >= 0x3)
    {
        edge_sn_no_fastfall();                  // and func_553 / func_555 skipped: edge_sn_free
    }
    if (edge_sn_state == 0x5 && MotionModuleF(0x1) >= edge_sn_grav_end())
    {
        edge_sn_gravity(1.0f);
        edge_sn_state = 0x6;
    }
    if (edge_sn_state == 0x5)
    {
        edge_sn_float();
    }
    if (edge_sn_state == 0 || edge_sn_state >= 0x5)
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
        // the tapped move plays first (its hits at 13 and 15); held from its start to the end of the window
        if (f < edge_sn_window() + edge_sn_hold())
        {
            return;
        }
        edge_sn_setvar(1.0f);
        edge_sn_begin();
    }
    edge_sn_float();
    if (edge_sn_state == 0x3)
    {
        WorkModule(0, WorkModuleF(0, edge_sn_timer()) + 1.0f, edge_sn_timer());
        if (held == 0 || WorkModuleF(0, edge_sn_timer()) >= edge_sn_life())
        {
            edge_sn_state = 0x4;                // let go, or out 5 seconds: back
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
            if (edge_sn_pull())
            {
                edge_sn_publish(edge_sn_blade());   // the sword at its length, the caught still coming in
                edge_sn_hold_caught();
                return;
            }
            edge_sn_hold_caught();
            edge_sn_finish();
            return;
        }
    }
    edge_sn_publish(edge_sn_total - edge_sn_back);
    edge_sn_catch_new();
    edge_sn_hold_caught();
}

// the aerial status's end (landing, a hit, ...): anyone caught dropped, the sword back
void edge_sn_end()
{
    if (edge_sn_state >= 0x3 && edge_sn_state <= 0x4)
    {
        edge_sn_release(0x1);
        edge_sn_blade_hide(0);
        edge_sn_publish(-1.0f);
    }
    if (edge_sn_state >= 0x3 && edge_sn_state <= 0x5)
    {
        edge_sn_gravity(1.0f);
    }
    edge_sn_release(0);
    edge_sn_state = 0;
    edge_sn_setvar(0.0f);
}
'''


def block():
    gl, fn = [], []
    for kind, name, n in (('float', 'edge_sn_s', SLOTS), ('float', 'edge_sn_oh', SLOTS), ('float', 'edge_sn_ov', SLOTS)):
        g, f = indexed(kind, name, n)
        gl.append(g)
        fn.append(f)
    body = BODY.replace('BLADE', str(JOINT_BLADE)).replace('SEGMENTS', str(SEGMENTS)).replace('SLOTS', str(SLOTS))
    body = body.replace('ART_RUN', str(ART_RUN)).replace('ART_TIP', str(ART_TIP))
    assert not re.search(r'\b(BLADE|SEGMENTS|SLOTS|ART_RUN|ART_TIP)\b', body), 'placeholder left'
    return '\n'.join([BEGIN, '// Sephiroth: held forward air, the extending sword (fighters/edge/snake_fair.md)', ''.join(gl),
                      '\n'.join(fn), body, END]) + '\n'


HOOKS = [
    # (function, the line to find in it, what to put before / after)
    ('func_315', '    func_314();\n', 'after', '    edge_sn_init();          // Sephiroth: held forward air\n'),
    ('func_319', '    if (func_318())\n', 'before', '    edge_sn_loop();          // Sephiroth: held forward air\n'),
    ('func_316', '    func_550();\n', 'replace',
     '    edge_sn_550();           // Sephiroth: held forward air, no fast fall from the hold on\n'),
    # up tilt (status 0x29): main func_278, loop func_279
    ('func_278', '    func_78(func_279);\n', 'before', '    edge_sn_init_hi3();      // Sephiroth: held up tilt\n'),
    ('func_279', '    if (CancelModule(0x2713) == 0x1 && func_39() != 0)\n', 'before',
     '    edge_sn_loop();          // Sephiroth: held up tilt\n'),
    # the side special cancel, first in both loops (after the loop hooks above: found by their lines)
    ('func_279', '    edge_sn_loop();          // Sephiroth: held up tilt\n', 'before',
     '    if (edge_sn_cancel())    // Sephiroth: held up tilt, side special cancel\n    {\n        return;\n    }\n'),
    ('func_319', '    edge_sn_loop();          // Sephiroth: held forward air\n', 'before',
     '    if (edge_sn_cancel())    // Sephiroth: held forward air, side special cancel\n    {\n        return;\n    }\n'),
    ('func_319', '    func_555();\n', 'replace',
     '    if (edge_sn_free())      // Sephiroth: held forward air, no fast fall while the sword is out\n    {\n'
     '        func_555();\n    }\n'),
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
        if where == 'replace':
            part = part.replace(line, add, 1)
        else:
            part = part.replace(line, line + add if where == 'after' else add + line, 1)
        src = src[:start] + part + src[stop + 1:]
    # the aerial status's end (slot 2, empty func_334 in the base)
    reg = 'sv_set_mem(0x1, 0x2, 0x34, func_334);'
    if reg in src:
        src = src.replace(reg, 'sv_set_mem(0x1, 0x2, 0x34, edge_sn_end);  // Sephiroth: held forward air (was func_334, empty)')
    reg = 'sv_set_mem(0x1, 0x2, 0x29, func_323);'      # up tilt's end (empty func_323)
    if reg in src:
        src = src.replace(reg, 'sv_set_mem(0x1, 0x2, 0x29, edge_sn_end);  // Sephiroth: held up tilt (was func_323, empty)')
    open(path, 'w').write(src)
    print('snake fair block: %d lines' % block().count('\n'))


if __name__ == '__main__':
    main()
