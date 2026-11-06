// Sephiroth: held forward air's snake (weapon kind 0x199, a copy of Zelda's light arrow): its MSC (tools/edge_snake_articles_msc.py)
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

// ---- Sephiroth's up special closed-shape fill (tools/edge_fill_msc.py; test 125)
int fi_slot;            // his player slot (0 - 7), -1: not found
int fi_frame;           // frames since made
float fi_r;             // the shape's radius
float fi_x;             // its middle
float fi_y;
float fi_px;            // fi_unpack's result
float fi_py;

float fi_cos(int k)
{
    if (k == 0)
    {
        return 1.000000f;
    }
    if (k == 1)
    {
        return 0.923880f;
    }
    if (k == 2)
    {
        return 0.707107f;
    }
    if (k == 3)
    {
        return 0.382683f;
    }
    if (k == 4)
    {
        return 0.000000f;
    }
    if (k == 5)
    {
        return -0.382683f;
    }
    if (k == 6)
    {
        return -0.707107f;
    }
    if (k == 7)
    {
        return -0.923880f;
    }
    if (k == 8)
    {
        return -1.000000f;
    }
    if (k == 9)
    {
        return -0.923880f;
    }
    if (k == 10)
    {
        return -0.707107f;
    }
    if (k == 11)
    {
        return -0.382683f;
    }
    if (k == 12)
    {
        return -0.000000f;
    }
    if (k == 13)
    {
        return 0.382683f;
    }
    if (k == 14)
    {
        return 0.707107f;
    }
    if (k == 15)
    {
        return 0.923880f;
    }
    return 1.0f;
}

float fi_sin(int k)
{
    if (k == 0)
    {
        return 0.000000f;
    }
    if (k == 1)
    {
        return 0.382683f;
    }
    if (k == 2)
    {
        return 0.707107f;
    }
    if (k == 3)
    {
        return 0.923880f;
    }
    if (k == 4)
    {
        return 1.000000f;
    }
    if (k == 5)
    {
        return 0.923880f;
    }
    if (k == 6)
    {
        return 0.707107f;
    }
    if (k == 7)
    {
        return 0.382683f;
    }
    if (k == 8)
    {
        return 0.000000f;
    }
    if (k == 9)
    {
        return -0.382683f;
    }
    if (k == 10)
    {
        return -0.707107f;
    }
    if (k == 11)
    {
        return -0.923880f;
    }
    if (k == 12)
    {
        return -1.000000f;
    }
    if (k == 13)
    {
        return -0.923880f;
    }
    if (k == 14)
    {
        return -0.707107f;
    }
    if (k == 15)
    {
        return -0.382683f;
    }
    return 0.0f;
}

// the hitbox's tier (its motion, 1 - 5) by the radius
int fi_tier()
{
    if (fi_r < 8.0f)
    {
        return 1;
    }
    if (fi_r < 13.0f)
    {
        return 2;
    }
    if (fi_r < 19.0f)
    {
        return 3;
    }
    if (fi_r < 26.0f)
    {
        return 4;
    }
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

// the disc's radius now: none before 12, grown over 8 frames, held to 40, shrunk to 50
float fi_vis()
{
    if (fi_frame < 12)
    {
        return 0.0f;
    }
    if (fi_frame < 12 + 8)
    {
        return fi_r * (float)(fi_frame - 12) / (float)8;
    }
    if (fi_frame < 40)
    {
        return fi_r;
    }
    return fi_r * (float)(50 - fi_frame) / (float)(50 - 40);
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
    while (k < 16)
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
    if (fi_frame >= 50 || fi_slot < 0)
    {
        BattleObject(0x9);
        return 0x1;
    }
    if (fi_frame == 12 + 8)
    {
        func_24(fi_tier(), 0, 1.0f);       // the hitbox (its tier's motion: the script's frame 0)
    }
    if (fi_frame == 12 + 8 + 4)
    {
        func_24(0, 0, 1.0f);               // hitboxes off
    }
    fi_still();
    fi_pose();
}
