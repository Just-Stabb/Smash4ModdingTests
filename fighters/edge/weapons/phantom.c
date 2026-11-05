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
int ph_track_again;       // Sephiroth: the tracking done again on its attack's first frame
int ph_follow;            // Sephiroth: following a fighter held on his sword up and down (test 107)

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
}

void func_43()
{
    global7 = 0x5;
    func_44();
    func_42();
}

void func_44()
{
    sv_set_mem(0x1, 0, 0, func_45);
    sv_set_mem(0x1, 0x1, 0, func_46);
    sv_set_mem(0x1, 0x2, 0, func_48);
    sv_set_mem(0x1, 0, 0x1, func_49);
    sv_set_mem(0x1, 0x1, 0x1, func_50);
    sv_set_mem(0x1, 0x2, 0x1, func_52);
    sv_set_mem(0x1, 0, 0x2, func_53);
    sv_set_mem(0x1, 0x1, 0x2, func_54);
    sv_set_mem(0x1, 0x2, 0x2, func_56);
    sv_set_mem(0x1, 0, 0x3, func_57);
    sv_set_mem(0x1, 0x1, 0x3, func_58);
    sv_set_mem(0x1, 0x2, 0x3, func_60);
    sv_set_mem(0x1, 0, 0x4, func_61);
    sv_set_mem(0x1, 0x1, 0x4, func_62);
    sv_set_mem(0x1, 0x2, 0x4, func_64);
}

int func_45()
{
    StatusModule(0x5, 0xffffffff, 0xffffffff, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_46()
{
    VisibilityModule(0x2710, 0);
    HitModule(0x2710, 0x3);
    EffectModule(0x26, 0);
    func_24(0, 0, 1.0f);
    callFunc3(func_47);
}

void func_47()
{
    
}

void func_48()
{
    
}

int func_49()
{
    StatusModule(0x5, 0xffffffff, 0xffffffff, 0, 0, 0, 0, 0, 0, 0x20);
    return 0;
}

void func_50()
{
    func_24(0x4, 0, 1.0f);
    callFunc3(func_51);
}

void func_51()
{
    
}

void func_52()
{
    
}

int func_53()
{
    StatusModule(0x5, 0xffffffff, 0x20, 0, 0, 0x1, 0, 0, 0, 0x20);
    return 0;
}

void func_54()
{
    int var0;
    float var1;
    float var2;
    int var3;
    float var4;
    float var5;
    ph_follow = 0;              // Sephiroth: the tracking is placed at the end of this main (test 107)
    var0 = WorkModule(0x6, 0x10000007);
    var1 = WorkModuleF(0, 0x4);
    var2 = WorkModuleF(0, 0x2000003) * var1;
    AttackModule(0x272d, var2);
    if (var0 == 0x2)
    {
        func_22(0x2);
    }
    else
    {
        func_22(0);
    }
    if (var1 <= 2.0f)
    {
        if (var0 == 0)
        {
            var3 = 0xc;
        }
        else
        {
            var3 = 0x18;
        }
    }
    else if (var1 <= 6.0f)
    {
        if (var0 == 0)
        {
            var3 = 0x10;
        }
        else
        {
            var3 = 0x1c;
        }
    }
    else if (var0 == 0)
    {
        var3 = 0x14;
    }
    else
    {
        var3 = 0x20;
    }
    func_24(var3, 0, 1.0f);
    VisibilityModule(0x2710, 0x1);
    BattleObject(0x3e8, 0x6);
    var4 = PostureModuleF(0x1);
    var5 = PostureModuleF(0x2);
    GroundModule(0x1a, var4, var5);
    ph_track(0);                // Sephiroth: to a fighter held on his sword, or the last he hit in hitstun (tests
    ph_track_again = 0x1;       // 106 / 107), after its own ground set-up above (test 106's, before it, kept it down)
    callFunc3(func_55);
}

void func_55()
{
    int var0;
    if (ph_track_again)         // Sephiroth: again on the first frame, in case its release placed it after the main
    {
        ph_track(0x1);
        ph_track_again = 0;
    }
    ph_follow_frame();          // Sephiroth: up and down with a fighter held on his sword (test 107)
    if (WorkModule(0x10, 0x20000005) == 0 && WorkModuleF(0, 0x2) > 0)
    {
        var0 = (int)MotionModuleF(0x1);
        if (MotionModule(0) - 0x5 <= var0)
        {
            BattleObject(0x3e9, 0x6);
            HitModule(0x2710, 0x3);
        }
    }
    if (MotionModule(0x2712))
    {
        func_18(0x4, 0);
        return 0x1;
    }
    if (global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        if (WorkModule(0x10, 0x20000004))
        {
            if (global18 == 0)
            {
                GroundModule(0x2710, 0x1);
            }
            else
            {
                GroundModule(0x2710, 0x5);
            }
        }
    }
}

void func_56()
{
    
}

int func_57()
{
    StatusModule(0x5, 0xffffffff, 0xffffffff, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_58()
{
    WorkModule(0x2711, 0x20000005);
    HitModule(0x2710, 0x3);
    func_24(0x24, 0, 1.0f);
    WorkModule(0x7, WorkModule(0x6, 0x12000005), 0x10000004);
    callFunc3(func_59);
}

int func_59()
{
    int var0;
    int var1;
    if (WorkModule(0x10, 0x20000005) == 0 && WorkModuleF(0, 0x2) > 0)
    {
        var0 = (int)MotionModuleF(0x1);
        if (MotionModule(0) - 0x5 <= var0)
        {
            BattleObject(0x3e9, 0x6);
        }
    }
    var1 = WorkModule(0x6, 0x10000004) - 0x1;
    if (var1 >= 0)
    {
        WorkModule(0x7, var1, 0x10000004);
    }
    else if (WorkModule(0x10, 0x20000005) == 0 && WorkModule(0x10, 0x20000006) == 0x1 && MotionModule(0x2712))
    {
        BattleObject(0x9);
        return 0x1;
    }
    return 0;
}

void func_60()
{
    
}

int func_61()
{
    StatusModule(0x5, 0xffffffff, 0xffffffff, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_62()
{
    if (WorkModule(0x10, 0x20000005) == 0)
    {
        BattleObject(0x3e9, 0x6);
    }
    HitModule(0x2710, 0x3);
    func_24(0x28, 0, 1.0f);
    callFunc3(func_63);
}

int func_63()
{
    if (WorkModule(0x10, 0x20000005) == 0 && WorkModule(0x10, 0x20000006) == 0x1)
    {
        BattleObject(0x9);
        return 0x1;
    }
    return 0;
}

void func_64()
{
    
}

// ---- Sephiroth's Zelda's Phantom (fighters/edge/weapons/phantom.c: Zelda's vanilla phantom.mscsb, decompiled, with
// this). Tracking at the start of its attack (status 2), the user's (test 106): "make the Phantom have tracking right
// at the start of its release specifically if the last opponent Sephiroth hit is in hitstun"; "The tracking should not
// switch facing directions for the Phantom". Sephiroth (edge.c edge_lw_ph_send) puts that fighter's place in his
// VAR_31 as he sends it (2^21 + (x + 512) * 1024 + (y + 512), whole units; 0 none), which this reads as his slot's
// SLOTn_SHARED_7 (in its attack's main and again on its first frame, then clears it); it is then placed PH_REACH behind the fighter along its own facing (kept), at its height,
// so its slash (hitboxes 14 ahead) meets it

// his player slot (0 - 7): the nearest Sephiroth (kind 0x42), -1 none (the snake articles' sn_find_owner)
int ph_find_owner()
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

float ph_reach() { return 10.0f; }
float ph_lift() { return 8.0f; }   // the hitstun tracking's height change at most (test 109)

void ph_track(int clear)
{
    int slot;
    int c;
    int ix;
    int iy;
    float v;
    float x;
    float y;
    slot = ph_find_owner();
    if (slot < 0)
    {
        return;
    }
    v = WorkModuleF(0, 0x0f000347 + 0x8 * slot);
    if (v >= 4194304.0f)
    {
        // a fighter held on his sword (2^22 + the place, kept up to date by him each frame): there, in the air, then
        // followed up and down (ph_follow_frame)
        c = (int)v - 0x400000;
        ix = c / 0x400;
        iy = c - ix * 0x400;
        x = (float)(ix - 0x200) - PostureModuleF(0) * ph_reach();
        y = (float)(iy - 0x200);
        StatusModule(0x2, 0x2);
        GroundModule(0x2710, 0x5);
        PostureModule(0x2714, x, y, PostureModuleF(0x3));
        ph_follow = 0x1;
        return;
    }
    if (v < 2097152.0f)
    {
        return;
    }
    if (clear)
    {
        WorkModule(0, 0.0f, 0x0f000347 + 0x8 * slot);
    }
    c = (int)v - 0x200000;
    ix = c / 0x400;
    iy = c - ix * 0x400;
    x = (float)(ix - 0x200) - PostureModuleF(0) * ph_reach();
    // the fighter in hitstun: its x, and toward its height by at most PH_LIFT (test 109, the user: "adjust its height
    // to 8 units at most"; test 108 kept its own height)
    y = (float)(iy - 0x200) - PostureModuleF(0x2);
    if (y > ph_lift())
    {
        y = ph_lift();
    }
    if (y < -ph_lift())
    {
        y = -ph_lift();
    }
    PostureModule(0x2714, x, PostureModuleF(0x2) + y, PostureModuleF(0x3));
}

// every frame of its attack while following: the held fighter's height (its x kept, its facing kept); let go (his
// code gone), it stops
void ph_follow_frame()
{
    int slot;
    int c;
    int ix;
    int iy;
    float v;
    if (ph_follow == 0)
    {
        return;
    }
    slot = ph_find_owner();
    if (slot < 0)
    {
        ph_follow = 0;
        return;
    }
    v = WorkModuleF(0, 0x0f000347 + 0x8 * slot);
    if (v < 4194304.0f)
    {
        ph_follow = 0;
        return;
    }
    c = (int)v - 0x400000;
    ix = c / 0x400;
    iy = c - ix * 0x400;
    PostureModule(0x2714, PostureModuleF(0x1), (float)(iy - 0x200), PostureModuleF(0x3));
}

