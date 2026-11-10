#!/usr/bin/env python3
"""The MSC of Sephiroth's held forward air's articles (fighters/edge/snake_fair.md): fighters/edge/weapons/snake.c (a run
of the extended blade, up to 12) and snaketip.c (its point), from Zelda's light arrow's MSC (decompiled: their base
kind's, tools/extra_kinds.json) with its status 0 replaced.

  python3 tools/edge_snake_articles_msc.py LIGHTINGBOWARROW.mscsb

Every frame each article places itself from Sephiroth's own state, his VAR_24 - VAR_31 (the slot-shared variables:
any object reads them as SLOTn_SHARED_k, docs/acmd-extra-commands.md), written by his MSC (tools/edge_snake_msc.py):
  VAR_24 - VAR_29  the path's runs, two a float: run 2i+1 in the low 12 bits, run 2i+2 in the next 12; a run's code is
                   direction x 1024 + length x 2 (0 forward, 1 up, 2 back, 3 down, along his facing)
  VAR_30           the length drawn (the path retracts from its end); below 0: the move is over, the articles go
  VAR_31           the runs' counter: each run, made, takes the next number (run k draws the path's k-th run)
The path starts at the blade's start at forward air's frame 13 (BASE_H / BASE_V, his model's +Z / +Y from his
position) and lies in his model plane. A run is placed at its start (PostureModule 0x2714), turned along its direction
(0x2717: (-pitch, 0, 0), his facing turning it his way) and stretched to its drawn length (ModelModule 7 on joint 0x7D2, its EndN:
tools/edge_snake_articles.py); the point at the path's drawn end, turned along its last run.
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BASE_H, BASE_V = 11.06, 13.35          # tools/edge_snake_msc.py edge_sn_base_h / _v: the blade's start, frozen frame 13
HI3_H, HI3_V = 1.14, 27.18             # held up tilt's (edge_sn_move 1): c02attackhi3 frame 20, the sword straight up
HI3_STATUS = 0x29                      # his status in up tilt (AttackHi3)
RUNS = 12
FX_EVERY = 6                           # frames between the point's flashes while the sword grows
TIP_LEN = 3.48                         # the point's length (tools/edge_snake_articles.py)
SN_GUARD_R = 22.0                      # test 150: a guarding fighter's middle this near the point: it was shielded

COMMON = r'''
// ---- Sephiroth's held forward air (tools/edge_snake_articles_msc.py)
int sn_slot;            // his player slot (0 - 7), -1: not found
int sn_index;           // the run this article draws (1 - 12); 0: the point
int sn_life;            // frames left (a safety net: removed after SN_LIFE whatever happened)
float sn_h;             // sn_walk's result: the point along the path, its run's direction
float sn_v;
int sn_d;
float sn_bh;            // the path's start (the blade's, frozen frame 13: sn_base), his model plane; sn_bz its depth
float sn_bv;
float sn_bz;

float sn_base_h() { return sn_bh; }
float sn_base_v() { return sn_bv; }

// the path starts at the blade's start in the frozen frame-13 pose (Ultimate's c05attackairf frame 13: the hilt 10.25
// forward, 13.32 up; the blade's body 0.82 on: BASE_H / BASE_V) from his position, at his depth. Tests 88 - 90 read his
// hand through the joint variables instead: joint 26 read his root (the sword from his feet), joint 23 (LHaveN) a
// point at his shoulder behind the hilt (its unanimated place, not the frozen pose): user, test 90's frame
// Held up tilt (user, test 97) uses the same path from its own frozen pose: his status (hit / status variable q 2
// of his slot, docs/position-variables.md) tells which
void sn_base()
{
    sn_bh = BASE_Hf;
    sn_bv = BASE_Vf;
    if (WorkModuleF(0, 0x0f0000a0 + 0x8 * (sn_slot + 0x3) + 0x2) == HI3_STATUSf)
    {
        sn_bh = HI3_Hf;
        sn_bv = HI3_Vf;
    }
    sn_bz = WorkModuleF(0, 0x0f000022 + 0x4 * sn_slot);
}

int sn_find_owner()
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

float sn_shared(int k)
{
    return WorkModuleF(0, 0x0f000340 + 0x8 * sn_slot + k);
}

void sn_share(int k, float v)
{
    WorkModule(0, v, 0x0f000340 + 0x8 * sn_slot + k);
}

// run j's code (direction x 1024 + length x 2)
int sn_code(int j)
{
    int c;
    int i;
    i = (j - 1) / 2;
    c = (int)sn_shared(i);
    if (j - 2 * i == 2)
    {
        c = c / 4096;
    }
    return c - (c / 4096) * 4096;
}

float sn_dh(int d)
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

float sn_dv(int d)
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

// the path from its start up to `upto` runs, at most `len` of it drawn -> sn_h / sn_v (where it ends), sn_d (the last
// run's direction); returns how much of it was drawn
float sn_walk(int upto, float len)
{
    int j;
    int c;
    int d;
    float l;
    float acc;
    sn_h = sn_base_h();
    sn_v = sn_base_v();
    sn_d = 0;
    acc = 0.0f;
    j = 1;
    while (j <= upto)
    {
        c = sn_code(j);
        d = c / 1024;
        l = (float)(c - d * 1024) * 0.5f;
        if (acc + l > len)
        {
            l = len - acc;
        }
        if (l < 0.0f)
        {
            l = 0.0f;
        }
        if (l > 0.0f || j == 1)
        {
            sn_d = d;
        }
        sn_h = sn_h + l * sn_dh(d);
        sn_v = sn_v + l * sn_dv(d);
        acc = acc + l;
        j += 1;
    }
    return acc;
}

float sn_pitch(int d)
{
    if (d == 1)
    {
        return 90.0f;
    }
    if (d == 2)
    {
        return 180.0f;
    }
    if (d == 3)
    {
        return -90.0f;
    }
    return 0.0f;
}

// put this article at (h, v) of his model plane, turned along d, facing his way. Its facing (PostureModule 0, his: a
// fighter it hits takes it, 0 left them facing the camera, test 83) already turns the model to his side (lr x 90 about
// Y), so the turn (0x2717) is only the run's pitch about X: (-pitch, 0, 0), relative to his facing either way. Tests
// 84 - 88 added Pit's arrow's 90 about Y on top: 180, a forward run seen end-on (invisible), up / down ones fine
void sn_place(float h, float v, int d)
{
    float lr;
    lr = WorkModuleF(0, 0x0f000023 + 0x4 * sn_slot);
    PostureModule(0, lr);
    PostureModule(0x2714, WorkModuleF(0, 0x0f000020 + 0x4 * sn_slot) + lr * h, WorkModuleF(0, 0x0f000021 + 0x4 * sn_slot) + v,
                  sn_bz);
    PostureModule(0x2717, -sn_pitch(d), 0, 0);
}

// over: the move ended (VAR_30 below 0), he's gone, or the safety net
int sn_over()
{
    sn_life -= 1;
    if (sn_slot < 0 || sn_life <= 0 || WorkModuleF(0, 0x0f000023 + 0x4 * sn_slot) == 0 || sn_shared(0x6) < 0.0f)
    {
        BattleObject(0x9);
        return 0x1;
    }
    return 0;
}

void sn_still()
{
    KineticModule(0x11, 0, 0, 0);
    KineticModule(0xf, 0, 0, 0);
}
'''

RUN = r'''
// a run: placed at the start of its run, stretched to its drawn part (0: nothing drawn)
void sn_frame()
{
    float before;
    float upto;
    float h;
    float v;
    float len;
    sn_base();
    before = sn_walk(sn_index - 1, sn_shared(0x6));
    h = sn_h;
    v = sn_v;
    upto = sn_walk(sn_index, sn_shared(0x6));
    len = upto - before;
    sn_place(h, v, sn_d);
    ModelModule(0x7, 0x7d2, 0, 0, len);
}

void func_46()
{
    sn_slot = sn_find_owner();
    sn_life = SN_LIFE;
    sn_index = 0;
    if (sn_slot >= 0)
    {
        sn_index = (int)sn_shared(0x7) + 1;     // VAR_31: the runs' counter
        sn_share(0x7, (float)sn_index);
    }
    sn_still();
    if (sn_over() == 0)
    {
        sn_frame();         // placed before its motion (and scripts) start: the point's trail begins at the point
    }
    func_24(0, 0, 1.0f);
    callFunc3(func_47);
}

void func_47()
{
    if (sn_over())
    {
        return 0x1;
    }
    sn_still();
    sn_frame();
}
'''

TIP = r'''
// the point: at the path's drawn end, along its last run (its hitbox and trail: its ACMD)
int sn_fx() { return 0; } // fx edge_sword_flash2
int sn_fx_h;            // the newest flash's handle (0: none)
int sn_fx_t;            // frames to the next flash
float sn_last;          // the drawn length last frame
int sn_shld;            // test 148: 1 once it hit a shield, 2 once its hit records were cleared for the way back

// fair's flash at the blade's end (edge_sword_flash2, its frame 13) carried out with the point while the sword grows:
// a new one every FX_EVERY frames at the point's end, the newest moved with it (EffectModule 0x3 / 0x17, as Shadow
// Flare's orbs). Fair's own played once at the real blade's end and stayed by his hand (user, test 91: "the sword
// effects aren't travelling upstream with the sword movement")
void sn_flash(float len)
{
    float lr;
    float x;
    float y;
    float z;
    lr = WorkModuleF(0, 0x0f000023 + 0x4 * sn_slot);
    x = PostureModuleF(0x1) + lr * TIP_LENf * sn_dh(sn_d);
    y = PostureModuleF(0x2) + TIP_LENf * sn_dv(sn_d);
    z = PostureModuleF(0x3);
    if (len > sn_last + 0.5f)
    {
        if (sn_fx_t <= 0)
        {
            sn_fx_h = EffectModule(0x3, sn_fx(), x, y, z, 0, 0, 0, 1.0f, 0, 0xffffffff);
            sn_fx_t = FX_EVERY;
        }
    }
    if (sn_fx_t > 0)
    {
        sn_fx_t -= 1;
        if (sn_fx_h)
        {
            EffectModule(0x17, sn_fx_h, x, y, z);
        }
    }
    sn_last = len;
}

void sn_frame()
{
    float len;
    sn_base();
    len = sn_shared(0x6);
    sn_walk(RUNS, len);
    sn_place(sn_h, sn_v, sn_d);
    sn_flash(len);
}

void func_46()
{
    sn_slot = sn_find_owner();
    sn_life = SN_LIFE;
    sn_index = 0;
    sn_shld = 0;
    sn_still();
    if (sn_over() == 0)
    {
        sn_frame();         // placed before its motion (and scripts) start: the point's trail begins at the point
    }
    func_24(0, 0, 1.0f);
    callFunc3(func_47);
}

// test 148, the user: "Make the tip of snakesword not disappear when being shielded, if it is shielded, make it unable to
// hit the same character as it hit previously until the snakesword is being pulled back to where it came from". A shield
// hit no longer removes it (tools/extra_kinds.json snaketip "on_hit_bits" 0x17: the shield result asks for its status
// 0, which it is in) and leaves the shielding fighter in its hit record, so it isn't hit again. Once the sword goes back
// (the drawn length, his VAR_30, shorter than last frame: only the retract shortens it), motion 1 (`snaketipclear`,
// tools/edge_specials_build.py) clears its records and sets its hitbox again on Part 1 (a dein copy's other hit record:
// new, whatever the clear did), so from then on it can hit that fighter.
// Test 150 (the user: "the snake tip doesn't reactivate when Sephiroth releases the button/on its way back to the
// hilt"): test 148 took "shielded" only from this frame's hit kinds (AttackModule 0x2726 with mask 0x4), which may never
// report a shield hit on a weapon; now also a fighter guarding (status 0x1B - 0x1E, docs/position-variables.md) whose
// middle is within SN_GUARD_R of the point, any frame the sword grows, counts; and the way back's hitbox is on Part 1, a
// record of its own. A fighter it caught can be hit once more on the way back only then (a shield in the move)
int sn_guard_near()
{
    int s;
    float st;
    float dx;
    float dy;
    s = 0;
    while (s < 0x8)
    {
        if (s != sn_slot && WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0)
        {
            st = WorkModuleF(0, 0x0f0000a0 + 0x8 * (s + 0x3) + 0x2);
            if (st >= 27.0f && st <= 30.0f)
            {
                dx = WorkModuleF(0, 0x0f000020 + 0x4 * s) - PostureModuleF(0x1);
                dy = WorkModuleF(0, 0x0f000021 + 0x4 * s) + 8.0f - PostureModuleF(0x2);
                if (dx * dx + dy * dy < SN_GUARD_Rf * SN_GUARD_Rf)
                {
                    return 0x1;
                }
            }
        }
        s += 1;
    }
    return 0;
}

void sn_shield_check(float before)
{
    if (sn_shld == 0 && sn_last >= before - 0.5f)
    {
        if (AttackModule(0x2726, 0x4) || sn_guard_near())
        {
            sn_shld = 0x1;
        }
    }
    if (sn_shld == 0x1 && sn_last < before - 0.5f)
    {
        sn_shld = 0x2;
        func_24(0x1, 0, 1.0f);
    }
}

void func_47()
{
    float before;
    if (sn_over())
    {
        return 0x1;
    }
    sn_still();
    before = sn_last;
    sn_frame();
    sn_shield_check(before);
    if (AttackModule(0x2726))
    {
        AttackModule(0x2724);
    }
}
'''


def decompile(mscsb):
    out = tempfile.mktemp(suffix='.c')
    subprocess.run([sys.executable, os.path.join(HERE, 'mscdec', 'mscdec.py'), '-x', os.path.join(HERE, 'mscinfo.xml'),
                    '-o', out, mscsb], check=True, capture_output=True)
    text = open(out).read()
    os.unlink(out)
    return text


def body(text, fn):
    m = re.search(r'\n(void|int) %s\(\)\n\{\n.*?\n\}\n' % fn, text, re.S)
    assert m, fn
    return m


def generate(base_c, own):
    text = base_c
    # status 0's main / loop (func_46 / func_47) replaced, the motion offset (func_40: + 0x10000005) not installed
    for fn in ('func_47', 'func_46'):
        m = body(text, fn)
        text = text[:m.start()] + '\n' + text[m.end():]
    assert '    global21 = func_40;\n' in text
    text = text.replace('    global21 = func_40;\n', '    global21 = 0;           // motion indices as they are (flare1.c)\n')
    code = (COMMON + own).replace('BASE_Hf', '%.2ff' % BASE_H).replace('BASE_Vf', '%.2ff' % BASE_V)
    code = code.replace('HI3_Hf', '%.2ff' % HI3_H).replace('HI3_Vf', '%.2ff' % HI3_V)
    code = code.replace('HI3_STATUSf', '%.1ff' % HI3_STATUS)
    code = code.replace('SN_LIFE', '900').replace('RUNS', str(RUNS)).replace('FX_EVERY', str(FX_EVERY))
    code = code.replace('TIP_LENf', '%.2ff' % TIP_LEN).replace('SN_GUARD_Rf', '%.1ff' % SN_GUARD_R)
    return text.rstrip('\n') + '\n' + code


def main():
    base = decompile(sys.argv[1])
    for name, own in (('snake', RUN), ('snaketip', TIP)):
        path = os.path.join(ROOT, 'fighters', 'edge', 'weapons', name + '.c')
        head = ('// Sephiroth: held forward air\'s %s (weapon kind %s, a copy of Zelda\'s light arrow): its MSC '
                '(tools/edge_snake_articles_msc.py)\n' % (name, {'snake': '0x199', 'snaketip': '0x19A'}[name]))
        open(path, 'w').write(head + generate(base, own))
        print(path)


if __name__ == '__main__':
    main()
