// Greninja's fire trail (weapon kind 0x1A3, his article 9, at most 6 at once: fighters/gekkouga/README.md "Burn v2").
// The framework is his moon article's (vanilla moon.mscsb, decompiled, as weapons/skeleton.c): one status that does
// nothing; the trail itself is tr_frame(), run every frame (global14). At each smash's main hit his MSC asks for one at
// his place and one at each clone's (his VAR_0 - VAR_11) and makes them (ArticleModule 0x2710, 9); the executable
// (tools/gekkouga_clone_cave.py tr_frame) gives each its owner and request (its VAR_0 - VAR_4: his slot, the smash (1
// forward, 2 up, 3 down), the place, his facing) and burns whoever its hitboxes hit with the trail row (0.25 % every 15
// frames for 3 s). This script places it (it stays put), plays the smash's motion (kind = smash - 1: its game script's
// hitboxes, no knockback / hitlag / flinch, re-hit every 35 frames; held at its first frame) and its fire (his bank's
// PtcGekkougaFireTrail, along the smash's path, one more each frame), fades the fire for its last 15 frames and goes at
// 180. Its model (Pac-Man's hydrant's, a carrier for its joints) is hidden.
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
    global21 = func_40;
    global14 = tr_frame; // the fire trail: every frame, hitstop included (below)
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
    StatusModule(0x5, 0x2, 0x2, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_46()
{
    callFunc3(func_47);
}

void func_47()
{
    
}

void func_48()
{
    
}



// ===================================================================
// the fire trail
// ===================================================================
int tr_on;             // 1 once started (its owner known)
int tr_wait;           // frames waited for its owner (the executable's claim)
int tr_t;              // frames since it started
int tr_type;           // 1 forward, 2 up, 3 down
int tr_fx_n;           // flames made so far
float tr_x;            // its place, its way
float tr_y;
float tr_dir;

int tr_life() { return 180; }             // 3 s (the user)
int tr_fade() { return 15; }              // its fire fades over its last frames (the set's fade 1 / 15)
int tr_wait_max() { return 30; }          // never claimed: removed
int tr_fx() { return 0x330001c; }         // his bank's PtcGekkougaFireTrail (fire_ground_10: its base on the point)
float tr_fx_size() { return 1.0f; }

float tr_var(int n)
{
    return WorkModuleF(0, 0x0f000300 + n);
}

// the flames along the smash's path (units from its place, x along its way): forward smash 5 on the ground ahead (10 -
// 42), up smash a column of 4 over it (0 - 42: each ~14.5 tall), down smash 4 each side (10 - 37)
int tr_fx_count()
{
    if (tr_type == 0x1)
    {
        return 5;
    }
    if (tr_type == 0x2)
    {
        return 4;
    }
    return 8;
}

float tr_fx_dx(int k)
{
    if (tr_type == 0x1)
    {
        return 10.0f + 8.0f * (float)k;
    }
    if (tr_type == 0x2)
    {
        return 0;
    }
    if (k % 2 == 0)
    {
        return 10.0f + 9.0f * (float)(k / 2);
    }
    return -10.0f - 9.0f * (float)(k / 2);
}

float tr_fx_dy(int k)
{
    if (tr_type == 0x2)
    {
        return 14.0f * (float)k;
    }
    return 0;
}

// its start: the place / smash / way the executable copied from him
void tr_start()
{
    tr_type = (int)(tr_var(1) + 0.5f);
    if (tr_type < 0x1 || tr_type > 0x3)
    {
        tr_type = 0x1;
    }
    tr_x = tr_var(2);
    tr_y = tr_var(3);
    tr_dir = 1.0f;
    if (tr_var(4) < 0)
    {
        tr_dir = -1.0f;
    }
    PostureModule(0, tr_dir);
    PostureModule(0x2);
    PostureModule(0x3, tr_x, tr_y, 0);
    EffectModule(0x26, 0);                // its fire doesn't follow its (hidden) model's visibility
    EffectModule(0x1C, 0x1);
    MotionModule(0x1, tr_type - 0x1, 0, 0);   // its smash's hitboxes (the game script's first commands), held (rate 0)
    tr_on = 0x1;
    tr_t = 0;
    tr_fx_n = 0;
}

void tr_frame()
{
    float dx;
    VisibilityModule(0x2710, 0);          // the carrier model: hidden
    if (tr_on == 0)
    {
        if (tr_var(0) < 0.5f)
        {
            tr_wait += 1;
            if (tr_wait > tr_wait_max())
            {
                BattleObject(0x9);
            }
            return;
        }
        tr_start();
    }
    if (tr_fx_n < tr_fx_count())          // a flame a frame (their flipbooks out of step)
    {
        dx = tr_fx_dx(tr_fx_n) * tr_dir;
        EffectModule(0x2717, tr_fx(), 0, dx, tr_fx_dy(tr_fx_n), 0, 0, 0, 0, tr_fx_size(), 0);
        tr_fx_n += 1;
    }
    tr_t += 1;
    if (tr_t == tr_life() - tr_fade())
    {
        EffectModule(0x2723, tr_fx(), 0, 0);     // its fire fades (the set's fade 1 / 15 a frame)
    }
    if (tr_t >= tr_life())
    {
        EffectModule(0x2723, tr_fx(), 0x1, 0x1);
        BattleObject(0x9);
        return;
    }
    PostureModule(0x3, tr_x, tr_y, 0);
}
