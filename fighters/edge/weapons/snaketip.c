// Sephiroth: held forward air's snaketip (weapon kind 0x19A, a copy of Zelda's light arrow): its MSC (tools/edge_snake_articles_msc.py)
int global0;
int global1;
int global2;
int global3;
int global4;
int global5;
int global6;
int global7;
int global8;
float global9;
float global10;
int global11;
int global12;
int global13;
int global14;
int global15;
int global16;
int global17;
int global18;
int global19;
float global20;
int global21;

void func_0()
{
    global0 = 0;
    global1 = 0;
    global2 = 0;
    global3 = 0;
    global4 = 0xffffffff;
    global5 = 0xffffffff;
    global6 = 0xffffffff;
    global7 = 0x100;
    global8 = 0;
    global9 = global10 = 0;
    global11 = 0;
    global12 = 0;
    global13 = 0;
    global14 = 0;
    global15 = 0;
    global16 = 0;
    global17 = 0;
    global18 = 0;
    global19 = 0;
    global20 = 0;
    global21 = 0;
}

void func_1()
{
    printf("sys_line_system_init");
    callFunc3(func_2);
}

void func_2()
{
    int var0;
    int var1;
    global19 = global18;
    global18 = StatusModule(0x1);
    var0 = StatusModule(0);
    if (var0 != 0xffffffff)
    {
        if (!(StopModule(0x1) || SlowModule(0x3)))
        {
            var1 = sv_get_mem(0x1, 0x4, var0);
            if (var1 != 0)
            {
                (*var1)();
            }
        }
        else
        {
            var1 = sv_get_mem(0x1, 0x5, var0);
            if (var1 != 0)
            {
                (*var1)();
            }
        }
    }
}

void func_3()
{
    printf("sys_line_status_end_init");
    callFunc3(func_4);
}

void func_4()
{
    printf("sys_line_status_end_control");
    global6 = StatusModule(0x9);
    if (global6 >= global7)
    {
        printf("Warning : @g_status_kind_next_(%d) >= @g_status_kind_max_(%d)", global6, global7);
        return;
    }
    func_20();
    func_5(global4);
}

void func_5(int arg0)
{
    int var1;
    if (sys_5(0x5))
    {
        sys_1(0x5);
    }
    func_6();
    if (arg0 >= 0)
    {
        var1 = sv_get_mem(0x1, 0x2, arg0);
        if (var1 != 0)
        {
            (*var1)();
        }
        var1 = sv_get_mem(0x1, 0x6, arg0);
        if (var1 != 0)
        {
            (*var1)();
        }
    }
}

void func_6()
{
    if (sys_5(0x1))
    {
        sys_1(0x1);
    }
    if (sys_5(0x6))
    {
        sys_1(0x6);
    }
}

void func_7()
{
    printf("sys_line_status_shift_init");
    callFunc3(func_8);
}

void func_8()
{
    int var0;
    printf("sys_line_status_shift_control");
    if (global6 != global4 && global6 != 0xffffffff || StatusModule(0x6))
    {
        if (global6 >= global7)
        {
            printf("Warning : @g_status_kind_next_(%d) >= @g_status_kind_max_(%d)", global6, global7);
            return;
        }
        global8 = 0x1;
        global5 = global4;
        global4 = global6;
        if (func_9(global4))
        {
            global4 = StatusModule(0x7);
            func_9(global4);
        }
        func_10(global4);
        var0 = sv_get_mem(0x1, 0x3, global4);
        if (var0 != 0)
        {
            global2 = var0;
        }
        global9 = global10 = 0;
        global16 = 0;
        if (global12 != 0)
        {
            (*global12)();
        }
    }
}

int func_9(int arg0)
{
    int var1;
    int var2;
    printf("sub_pre_status_msc: LINE_STATUS_SHIFT status_now:%d", arg0);
    if (arg0 < 0)
    {
        printf("[Error]sub_pre_status_msc undefined status_now");
        return 0;
    }
    var1 = 0;
    var2 = sv_get_mem(0x1, 0, arg0);
    if (var2 != 0)
    {
        var1 = (*var2)();
    }
    else
    {
        var1 = 0;
    }
    return var1;
}

void func_10(int arg0)
{
    int var1;
    printf("sub_set_status_msc: LINE_STATUS_SHIFT status_now:%d", arg0);
    if (arg0 < 0)
    {
        printf("[Error]sub_set_status_msc undefined status_now");
        return;
    }
    var1 = sv_get_mem(0x1, 0x1, arg0);
    if (var1 != 0)
    {
        sys_0(0x5, var1);
    }
    func_11(arg0);
}

void func_11(int arg0)
{
    int var1;
    if (arg0 < 0)
    {
        return;
    }
    var1 = sv_get_mem(0x1, 0x7, arg0);
    if (var1 != 0)
    {
        sys_0(0x1, var1);
    }
    var1 = sv_get_mem(0x1, 0x8, arg0);
    if (var1 != 0)
    {
        sys_0(0x6, var1);
    }
}

void func_12()
{
    printf("sys_line_status_system_init");
    printf("PLATFORM CAFE");
    callFunc3(func_13);
}

void func_13()
{
    if (StopModule(0x1) == 0)
    {
        if (global8 == 0 && global9 < 1000000.0f)
        {
            if (SlowModule(0x2) == 0x1)
            {
                global9 += SlowModuleF(0);
                global3 = 0x1;
            }
            else
            {
                global9 = global10 + 1.0f;
                global10 = global9;
                global3 = 0;
            }
        }
        else
        {
            global3 = SlowModule(0x2);
        }
    }
    else
    {
        global3 = 0x1;
    }
    if (global14 != 0)
    {
        (*global14)();
    }
    global18 = StatusModule(0x1);
    global20 = MotionModuleF(0x1);
    if (global2 != 0)
    {
        (*global2)();
        global2 = 0;
    }
    if (!global3)
    {
        if (global15 != 0)
        {
            (*global15)();
        }
        if (global16 != 0)
        {
            (*global16)();
        }
    }
    global8 = 0;
}

int func_14(int arg0)
{
    if (arg0 < 0)
    {
        return -arg0;
    }
    return arg0;
}

float func_15(float arg0)
{
    if (arg0 < (float)0)
    {
        return -arg0;
    }
    return arg0;
}

void func_16(float arg0)
{
    if (arg0 < 0)
    {
        return -1.0f;
    }
    else
    {
        return 1.0f;
    }
}

float func_17(float arg0, float arg1, float arg2)
{
    if (arg0 < arg1)
    {
        return arg1;
    }
    else if (arg0 > arg2)
    {
        return arg2;
    }
    return arg0;
}

void func_18(int arg0, int arg1)
{
    if (global11)
    {
        (*global11)(arg0, arg1);
    }
}

void func_19(int arg0, int arg1)
{
    StatusModule(0x3, arg0, arg1);
}

void func_20()
{
    int var0;
    int var1;
    if (global13)
    {
        (*global13)(var0, var1);
    }
}

int func_21(int arg0, int arg1)
{
    BattleObject(0x19, arg0, arg1);
    return 0x1;
}

void func_22(int arg0)
{
    StatusModule(0x2, arg0);
    global19 = global18;
    global18 = arg0;
}

void func_23(int arg0, int arg1)
{
    StatusModule(0x2, arg0, arg1);
    global19 = global18;
    global18 = arg0;
}

void func_24(int arg0, float arg1, int arg2)
{
    int var3;
    var3 = arg0;
    if (global21)
    {
        var3 = (*global21)(arg0);
    }
    MotionModule(0x1, var3, arg1, arg2);
    global20 = arg1;
}

void func_25(int arg0)
{
    int var1;
    var1 = arg0;
    if (global21)
    {
        var1 = (*global21)(arg0);
    }
    MotionModule(0x3, var1);
    global20 = MotionModuleF(0x1);
}

void func_26(int arg0)
{
    int var1;
    var1 = arg0;
    if (global21)
    {
        var1 = (*global21)(arg0);
    }
    MotionModule(0x25, var1);
}

void func_27(int arg0)
{
    int var1;
    var1 = arg0;
    if (global21)
    {
        var1 = (*global21)(arg0);
    }
    MotionModule(0x26, var1);
}

void func_28(int arg0, int arg1, int arg2)
{
    int var3;
    var3 = arg0;
    if (global21)
    {
        var3 = (*global21)(arg0);
    }
    MotionModule(0x26, var3, arg1, arg2);
}

void func_29(int arg0)
{
    int var1;
    var1 = arg0;
    if (global21)
    {
        var1 = (*global21)(arg0);
    }
    MotionModule(0x3, var1, MotionModuleF(0x1));
}

void func_30(int arg0, float arg1, int arg2)
{
    int var3;
    var3 = arg0;
    if (global21)
    {
        var3 = (*global21)(arg0);
    }
    MotionModule(0x2b, var3, arg1, arg2);
    global20 = arg1;
}

void func_31(int arg0, float arg1, int arg2, int arg3)
{
    int var4;
    var4 = arg0;
    if (global21)
    {
        var4 = (*global21)(arg0);
    }
    MotionModule(0x1, var4, arg1, arg2, arg3);
    global20 = arg1;
}

int func_32(int arg0)
{
    if (randi(0, arg0) == 0)
    {
        return 0x1;
    }
    return 0;
}

int func_33(int arg0)
{
    int var1;
    var1 = MotionModule(0x7);
    if (var1 == arg0 || var1 == arg0 + 0x1 || var1 == arg0 + 0x2 || var1 == arg0 + 0x3)
    {
        return 0x1;
    }
    return 0;
}

int func_34(int arg0, int arg1)
{
    if (arg0 == arg1 || arg0 == arg1 + 0x1 || arg0 == arg1 + 0x2 || arg0 == arg1 + 0x3)
    {
        return 0x1;
    }
    return 0;
}

void func_35()
{
    PostureModule(0x271c);
    PostureModule(0x2);
}

int func_36()
{
    if (global18 == 0)
    {
        if (GroundModule(0xd))
        {
            return 0x1;
        }
    }
    return 0;
}

void func_37(int arg0, float arg1, int arg2)
{
    int var3;
    var3 = arg0;
    if (global21)
    {
        var3 = (*global21)(arg0);
    }
    MotionModule(0x38, var3, arg1, arg2);
    global20 = arg1;
}

void func_38()
{
    
}

float func_39()
{
    float var0;
    var0 = KineticModuleF(0x2, 0x1);
    return var0;
}

int func_40(int arg0)
{
    return arg0 + WorkModule(0x6, 0x10000005);
}

void main()
{
    printf("ENTRY This Fighter is driven by msc.");
    func_0();
    global0 = sys_7(0);
    global1 = sys_7(0x1);
    func_43();
    sys_0(0x2, func_3);
    sys_0(0x3, func_7);
    sys_0(0x4, func_12);
    set_main(func_1);
}

void func_42()
{
    global11 = func_19;
    global21 = 0;           // motion indices as they are (flare1.c)
}

void func_43()
{
    global7 = 0x1;
    func_44();
    func_42();
}

void func_44()
{
    sv_set_mem(0x1, 0, 0, func_45);
    sv_set_mem(0x1, 0x1, 0, func_46);
    sv_set_mem(0x1, 0x2, 0, func_48);
}

int func_45()
{
    StatusModule(0x5, 0xffffffff, 0, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}



void func_48()
{
    
}

// ---- Sephiroth's held forward air (tools/edge_snake_articles_msc.py)
int sn_slot;            // his player slot (0 - 7), -1: not found
int sn_index;           // the run this article draws (1 - 12); 0: the point
int sn_life;            // frames left (a safety net: removed after 900 whatever happened)
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
    sn_bh = 11.06f;
    sn_bv = 13.35f;
    if (WorkModuleF(0, 0x0f0000a0 + 0x8 * (sn_slot + 0x3) + 0x2) == 41.0f)
    {
        sn_bh = 1.14f;
        sn_bv = 27.18f;
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

// the point: at the path's drawn end, along its last run (its hitbox and trail: its ACMD)
int sn_fx() { return 0; } // fx edge_sword_flash2
int sn_fx_h;            // the newest flash's handle (0: none)
int sn_fx_t;            // frames to the next flash
float sn_last;          // the drawn length last frame
int sn_shld;            // test 148: 1 once it hit a shield, 2 once its hit records were cleared for the way back

// fair's flash at the blade's end (edge_sword_flash2, its frame 13) carried out with the point while the sword grows:
// a new one every 6 frames at the point's end, the newest moved with it (EffectModule 0x3 / 0x17, as Shadow
// Flare's orbs). Fair's own played once at the real blade's end and stayed by his hand (user, test 91: "the sword
// effects aren't travelling upstream with the sword movement")
void sn_flash(float len)
{
    float lr;
    float x;
    float y;
    float z;
    lr = WorkModuleF(0, 0x0f000023 + 0x4 * sn_slot);
    x = PostureModuleF(0x1) + lr * 3.48f * sn_dh(sn_d);
    y = PostureModuleF(0x2) + 3.48f * sn_dv(sn_d);
    z = PostureModuleF(0x3);
    if (len > sn_last + 0.5f)
    {
        if (sn_fx_t <= 0)
        {
            sn_fx_h = EffectModule(0x3, sn_fx(), x, y, z, 0, 0, 0, 1.0f, 0, 0xffffffff);
            sn_fx_t = 6;
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
    sn_walk(12, len);
    sn_place(sn_h, sn_v, sn_d);
    sn_flash(len);
}

void func_46()
{
    sn_slot = sn_find_owner();
    sn_life = 900;
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
// 0, which it is in) and leaves the shielding fighter in its hit record, so it isn't hit again; it was shielded if this
// frame's hit kinds hold the shield's (AttackModule 0x2726 with mask 0x4: 1 << 2, docs/native-notes.md). Once the
// sword goes back (the drawn length, his VAR_30, shorter than last frame: only the retract shortens it), motion 1
// (`snaketipclear`, tools/edge_specials_build.py) clears its records and sets its hitbox again, so from then on it can
// hit that fighter. Not shielded: no change (a fighter it caught stays out of its record and isn't hit twice)
void sn_shield_check(float before)
{
    if (sn_shld == 0 && AttackModule(0x2726, 0x4))
    {
        sn_shld = 0x1;
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
