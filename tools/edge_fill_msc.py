#!/usr/bin/env python3
"""Sephiroth's up special closed-shape fill (fighters/edge/specials.md "Up special", test 125, the user's concept stage
3): writes fighters/edge/weapons/fill.c = the snake run's base (Zelda's dein, fighters/edge/weapons/snake.c up to its
own section) + the fill's code.

A `fill` article is made by Sephiroth (edge.c edge_tr_step) when his trail closes a loop, at the loop's middle: his
shared 5 its place (packed: (x + 512) x 2 x 2048 + (y + 512) x 2), shared 4 its radius, read as it's made. A purple
disc (tools/edge_snake_articles.py build_fill: a middle joint C and RIM rim joints R0 - R15 the MSC moves out to the
radius) fades in from frame DELAY ("appears 12 frames after, fading in": grows to the radius over GROW frames), then
its hitbox (motion 1 - 5 by the radius' tier, edge_specials_build.py fill_scripts: "a hitbox slightly larger than the
shape formed, the damage and knockback scaling with the size of the shape") for HIT frames, then motion 0 (hitboxes
off), held, shrinks away, removed.

  python3 tools/edge_fill_msc.py
"""
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EDGE = os.path.join(ROOT, 'fighters', 'edge')
RIM = 16
DELAY = 12
GROW = 8
HIT = 4
HOLD_END = 40
END = 50
TIERS = (8.0, 13.0, 19.0, 26.0)      # radius upper bounds of tiers 1 - 4 (5: past 26); edge_specials_build.FILL_TIERS


def generate():
    src = open(os.path.join(EDGE, 'weapons', 'snake.c')).read()
    base = src[:src.index("// ---- Sephiroth's held forward air (tools/edge_snake_articles_msc.py)")]
    cos = '\n'.join('    if (k == %d)\n    {\n        return %.6ff;\n    }' % (k, math.cos(2 * math.pi * k / RIM))
                    for k in range(RIM))
    sin = '\n'.join('    if (k == %d)\n    {\n        return %.6ff;\n    }' % (k, math.sin(2 * math.pi * k / RIM))
                    for k in range(RIM))
    tiers = '\n'.join('    if (fi_r < %.1ff)\n    {\n        return %d;\n    }' % (t, i + 1) for i, t in enumerate(TIERS))
    body = '''// ---- Sephiroth's up special closed-shape fill (tools/edge_fill_msc.py; test 125)
int fi_slot;            // his player slot (0 - 7), -1: not found
int fi_frame;           // frames since made
float fi_r;             // the shape's radius
float fi_x;             // its middle
float fi_y;
float fi_px;            // fi_unpack's result
float fi_py;

float fi_cos(int k)
{
COS
    return 1.0f;
}

float fi_sin(int k)
{
SIN
    return 0.0f;
}

// the hitbox's tier (its motion, 1 - 5) by the radius
int fi_tier()
{
TIERS
    return 5;
}

int fi_find_owner()
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

float fi_shared(int k)
{
    return WorkModuleF(0, 0x0f000340 + 0x8 * fi_slot + k);
}

void fi_unpack(float v)
{
    int c;
    int ix;
    c = (int)v;
    ix = c / 0x800;
    fi_px = (float)ix * 0.5f - 512.0f;
    fi_py = (float)(c - ix * 0x800) * 0.5f - 512.0f;
}

void fi_still()
{
    KineticModule(0x11, 0, 0, 0);
    KineticModule(0xf, 0, 0, 0);
}

// the disc's radius now: none before DELAY_N, grown over GROW_N frames, held to HOLD_N, shrunk to END_N
float fi_vis()
{
    if (fi_frame < DELAY_N)
    {
        return 0.0f;
    }
    if (fi_frame < DELAY_N + GROW_N)
    {
        return fi_r * (float)(fi_frame - DELAY_N) / (float)GROW_N;
    }
    if (fi_frame < HOLD_N)
    {
        return fi_r;
    }
    return fi_r * (float)(END_N - fi_frame) / (float)(END_N - HOLD_N);
}

// the rim joints R_k (0x7D3 + k: C is 0x7D2) at the radius, in the screen plane (the model's Y and Z: facing 1)
void fi_pose()
{
    int k;
    float r;
    PostureModule(0, 1.0f);
    PostureModule(0x2714, fi_x, fi_y, PostureModuleF(0x3));
    r = fi_vis();
    k = 0;
    while (k < RIM_N)
    {
        ModelModule(0x7, 0x7d3 + k, 0, r * fi_sin(k), r * fi_cos(k));
        k = k + 1;
    }
}

void func_46()
{
    fi_slot = fi_find_owner();
    fi_frame = 0;
    fi_r = 0.0f;
    fi_x = PostureModuleF(0x1);
    fi_y = PostureModuleF(0x2);
    if (fi_slot >= 0)
    {
        fi_unpack(fi_shared(0x5));
        fi_x = fi_px;
        fi_y = fi_py;
        fi_r = fi_shared(0x4);
        PostureModule(0x2714, fi_x, fi_y, WorkModuleF(0, 0x0f000022 + 0x4 * fi_slot));
    }
    fi_still();
    fi_pose();
    func_24(0, 0, 1.0f);
    callFunc3(func_47);
}

void func_47()
{
    fi_frame = fi_frame + 1;
    if (fi_frame >= END_N || fi_slot < 0)
    {
        BattleObject(0x9);
        return 0x1;
    }
    if (fi_frame == DELAY_N + GROW_N)
    {
        func_24(fi_tier(), 0, 1.0f);       // the hitbox (its tier's motion: the script's frame 0)
    }
    if (fi_frame == DELAY_N + GROW_N + HIT_N)
    {
        func_24(0, 0, 1.0f);               // hitboxes off
    }
    fi_still();
    fi_pose();
}
'''
    body = (body.replace('COS', cos).replace('SIN', sin).replace('TIERS', tiers)
            .replace('RIM_N', str(RIM)).replace('DELAY_N', str(DELAY)).replace('GROW_N', str(GROW))
            .replace('HOLD_N', str(HOLD_END)).replace('END_N', str(END)).replace('HIT_N', str(HIT)))
    return base + body


if __name__ == '__main__':
    path = os.path.join(EDGE, 'weapons', 'fill.c')
    open(path, 'w').write(generate())
    print('wrote %s' % path)
