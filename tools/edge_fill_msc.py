#!/usr/bin/env python3
"""Sephiroth's up special closed-shape hitbox (fighters/edge/specials.md "Up special", tests 125 / 126, the user's
concept stage 3): writes fighters/edge/weapons/fill.c = the snake run's base (Zelda's dein, fighters/edge/weapons/snake.c
up to its own section) + the fill's code.

A `fill` article is made by Sephiroth (edge.c edge_tr_*) when a shape closes, at its middle: his shared 5 its place
(packed: (x + 512) x 2 x 2048 + (y + 512) x 2), shared 4 the ellipse fitted to its points (angle x 65536 + a x 256 + b:
the angle 0 - 127 for 0 - 180 degrees, the half axes a >= b in half units), read as it's made. The shape itself (its
glow) is drawn by the trail articles (tools/edge_trail_msc.py). The fill turns along the long axis and puts its joints
J0 - J4 (0x7D2 - 0x7D6) along it, from -(a - b) to a - b; from frame HIT_START to HIT_END (test 127, the user: "make
the hitbox ... happen on frame 4, and linger until the effect fades": the trail articles' fill is gone at their
FILL_END) its hitbox motion (edge_specials_build.py fill_scripts: a sphere on each joint, its size by b and its damage /
knockback by the shape's size, from its own VAR_0 / VAR_1; one hit a fighter): "a hitbox slightly larger than the shape
formed, the damage and knockback scaling with the size of the shape".

  python3 tools/edge_fill_msc.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EDGE = os.path.join(ROOT, 'fighters', 'edge')
HIT_START = 4
HIT_END = 50        # tools/edge_trail_msc.py FILL_END: the fill's glow gone
SPHERES = 5
SIZE_TIERS = (5.0, 8.0, 12.0, 17.0)       # b up to (tiers 1 - 4; 5 past): edge_specials_build.FILL_SIZES
DAMAGE_TIERS = (8.0, 13.0, 19.0, 26.0)    # sqrt(a b) up to: edge_specials_build.FILL_DAMAGE


def generate():
    src = open(os.path.join(EDGE, 'weapons', 'snake.c')).read()
    base = src[:src.index("// ---- Sephiroth's held forward air (tools/edge_snake_articles_msc.py)")]
    st = '\n'.join('    if (b <= %.1ff)\n    {\n        return %d;\n    }' % (t, i + 1) for i, t in enumerate(SIZE_TIERS))
    dt = '\n'.join('    if (r <= %.1ff)\n    {\n        return %d;\n    }' % (t, i + 1) for i, t in enumerate(DAMAGE_TIERS))
    body = '''// ---- Sephiroth's up special closed-shape hitbox (tools/edge_fill_msc.py; tests 125 / 126)
int fi_slot;            // his player slot (0 - 7), -1: not found
int fi_frame;           // frames since made
float fi_x;             // the shape's middle
float fi_y;
float fi_t;             // its long axis' angle (degrees)
float fi_a;             // its half axes
float fi_b;
float fi_lr;            // its facing as made (test 127: setting it to 1 didn't turn its model)
float fi_px;            // fi_unpack's result
float fi_py;

int fi_size_tier(float b)
{
ST
    return 5;
}

int fi_damage_tier(float r)
{
DT
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

// along the long axis: its +Z is the world's +X x its facing, pitched up by the angle (from its facing's side: 180 -
// the angle facing left); the joints spread along +Z
void fi_pose()
{
    int k;
    float h;
    PostureModule(0x2714, fi_x, fi_y, PostureModuleF(0x3));
    if (fi_lr > 0.0f)
    {
        PostureModule(0x2717, -fi_t, 0, 0);
    }
    else
    {
        PostureModule(0x2717, -(180.0f - fi_t), 0, 0);
    }
    h = fi_a - fi_b;
    k = 0;
    while (k < SPHERES_N)
    {
        ModelModule(0x7, 0x7d2 + k, 0, 0, -h + h * 2.0f * (float)k / (float)(SPHERES_N - 1));
        k = k + 1;
    }
}

void func_46()
{
    int c;
    int ia;
    fi_slot = fi_find_owner();
    fi_frame = 0;
    fi_lr = PostureModuleF(0);
    PostureModule(0, fi_lr);           // its facing set (its own: no turn), so fighters it hits face it (port_check W6)
    fi_x = PostureModuleF(0x1);
    fi_y = PostureModuleF(0x2);
    fi_t = 0.0f;
    fi_a = 4.0f;
    fi_b = 4.0f;
    if (fi_slot >= 0)
    {
        fi_unpack(fi_shared(0x5));
        fi_x = fi_px;
        fi_y = fi_py;
        c = (int)fi_shared(0x4);
        ia = c / 0x100;
        fi_b = (float)(c - ia * 0x100) * 0.5f;
        fi_t = (float)(ia / 0x100) * 180.0f / 128.0f;
        fi_a = (float)(ia - (ia / 0x100) * 0x100) * 0.5f;
        PostureModule(0x2714, fi_x, fi_y, WorkModuleF(0, 0x0f000022 + 0x4 * fi_slot));
    }
    WorkModule(0, (float)fi_size_tier(fi_b), 0x0f000300);              // VAR_0: the spheres' size (its script)
    WorkModule(0, (float)fi_damage_tier(MathF(0, fi_a * fi_b)), 0x0f000301);   // VAR_1: the damage
    fi_still();
    fi_pose();
    func_24(0, 0, 1.0f);
    callFunc3(func_47);
}

void func_47()
{
    fi_frame = fi_frame + 1;
    if (fi_frame >= HIT_END_N + 2 || fi_slot < 0)
    {
        BattleObject(0x9);
        return 0x1;
    }
    if (fi_frame == HIT_START_N)
    {
        func_24(0x1, 0, 1.0f);             // the hitbox (the script's frame 0)
    }
    if (fi_frame == HIT_END_N)
    {
        func_24(0, 0, 1.0f);               // hitboxes off
    }
    fi_still();
    fi_pose();
}
'''
    for k, v in (('SPHERES_N', SPHERES), ('HIT_START_N', HIT_START), ('HIT_END_N', HIT_END)):
        body = body.replace(k, str(v))
    return base + body.replace('ST\n', st + '\n', 1).replace('DT\n', dt + '\n', 1)


if __name__ == '__main__':
    path = os.path.join(EDGE, 'weapons', 'fill.c')
    open(path, 'w').write(generate())
    print('wrote %s' % path)
