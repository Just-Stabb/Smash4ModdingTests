// Link's arrow (weapon bowarrow, article 1): fighter/link/script/msc/bowarrow/bowarrow.mscsb, decompiled from the
// user's upload (vanilla; it rebuilds to the same functions). Changed: the flight lifetime is doubled (func_63,
// status 0's init). See fighters/link/README.md.
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
}

void func_43()
{
    global7 = 0x3;
    func_44();
    func_45();
    func_46();
    func_47();
    func_42();
}

void func_44()
{
    sv_set_mem(0x1, 0, 0, func_48);
    sv_set_mem(0x1, 0, 0x1, func_49);
    sv_set_mem(0x1, 0, 0x2, func_50);
}

void func_45()
{
    sv_set_mem(0x1, 0x1, 0, func_51);
    sv_set_mem(0x1, 0x1, 0x1, func_53);
    sv_set_mem(0x1, 0x1, 0x2, func_55);
}

void func_46()
{
    sv_set_mem(0x1, 0x2, 0, func_58);
    sv_set_mem(0x1, 0x2, 0x1, func_59);
    sv_set_mem(0x1, 0x2, 0x2, func_60);
}

void func_47()
{
    sv_set_mem(0x1, 0x3, 0, func_63);
    sv_set_mem(0x1, 0x3, 0x1, func_63);
    sv_set_mem(0x1, 0x3, 0x2, func_63);
}

void func_48()
{
    StatusModule(0x5, 0x2, 0x2, 0, 0, 0, 0, 0, 0, 0);
}

void func_49()
{
    StatusModule(0x5, 0x2, 0, 0x5, 0, 0, 0, 0, 0, 0);
}

void func_50()
{
    StatusModule(0x5, 0x2, 0x2, 0x7, 0, 0, 0, 0, 0, 0x6);
}

void func_51()
{
    func_24(0, 0, 1.0f);
    callFunc3(func_52);
}

int func_52()
{
    return 0;
}

void func_53()
{
    func_24(0x4, 0, 1.0f);
    AttackModule(0x271a, 0, (float)WorkModule(0x6, 0x11000000) + 0);
    if (!StopModule(0x1))
    {
        func_61();
    }
    global16 = func_61;
    callFunc3(func_54);
}

int func_54()
{
    if (GroundModule(0x2722, 0xff) != 0)
    {
        func_18(0x2, 0);
        return 0x1;
    }
    return 0;
}

void func_55()
{
    WorkModule(0, MathF(0x6) * 4.0f - 2.0f + 0, 0x3);
    BattleObject(0xc);
    GroundModule(0x2719, 0xff);
    GroundModule(0x2710, 0x5);
    func_24(0x8, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_62();
    }
    global16 = func_62;
    callFunc3(func_56);
}

int func_56()
{
    float var0;
    float var1;
    if (global9 == 1.0f)
    {
        AttackModule(0x2719);
        if (global1 == 0xd0)
        {
            if (WorkModule(0x6, 0x10000005) == 0x1)
            {
                var0 = WorkModuleF(0, 0x4);
                var1 = WorkModuleF(0, 0x5);
                EffectModule(0x2710, 0x3200006, 0, -var0, -var1, 0, 0, 0, 0, 1.0f, 0, 0, 0, 0, 0, 0, 0);
            }
        }
    }
    func_57();
    return 0;
}

void func_57()
{
    WorkModule(0, MathF(0x6) + 0, 0x1000000);
}

void func_58()
{
    
}

void func_59()
{
    
}

void func_60()
{
    
}

void func_61()
{
    int var0;
    WorkModule(0xa, 0x10000004);
    var0 = WorkModule(0x6, 0x10000004);
    if (var0 <= 0)
    {
        BattleObject(0x9);
    }
}

void func_62()
{
    int var0;
    int var1;
    WorkModule(0xa, 0x11000000);
    WorkModule(0xa, 0x10000004);
    var0 = WorkModule(0x6, 0x10000004);
    var1 = GroundModule(0x2728);
    if (var0 <= 0 || var1 == 0)
    {
        BattleObject(0x9);
    }
}

void func_63()
{
    int var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    int var6;
    float var7;
    float var8;
    float var9;
    float var10;
    float var11;
    float var12;
    int var13;
    int var14;
    if (global4 == 0)
    {
        // flight lifetime (user: twice as long): vl group 19 entry 0 (40 frames; customs 25 / 11) x 2.
        // 0x10000004 counts down only in flight (status 1, func_61); 0x10000003 keeps the full value.
        var0 = WorkModule(0x6, 0x12000000) * 0x2;
        WorkModule(0x7, var0, 0x10000003);
        WorkModule(0x7, var0, 0x10000004);
        BattleObject(0x3e8);
    }
    else if (global4 == 0x1)
    {
        var1 = PostureModuleF(0);
        var2 = WorkModuleF(0, 0x1);
        var3 = WorkModuleF(0, 0x2);
        var4 = WorkModuleF(0, 0x2000004);
        var5 = WorkModuleF(0, 0x2000003);
        var6 = (int)((var4 - var5) * var2 + var5);
        if (var2 >= 1.0f)
        {
            var6 *= (int)WorkModuleF(0, 0x2000005);
        }
        WorkModule(0x7, var6, 0x11000000);
        var7 = WorkModuleF(0, 0x2000002);
        var8 = WorkModuleF(0, 0x2000001);
        var9 = WorkModuleF(0, 0x2000007);
        var10 = (var7 - var8) * var2 + var8;
        var10 *= WorkModuleF(0, 0x2000008);
        var11 = MathF(0x4, var3) * var10 * var1;
        var12 = MathF(0x5, var3) * var10;
        KineticModule(0x11, 0, var11, var12);
        KineticModule(0x15, 0, -1.0f, -1.0f);
        KineticModule(0xf, 0, 0, -var9);
    }
    else if (global4 == 0x2)
    {
        var13 = WorkModule(0x6, 0x12000006);
        WorkModule(0x7, var13, 0x10000003);
        WorkModule(0x7, var13, 0x10000004);
        var14 = 0x3 + randi(0, 0x3);
        WorkModule(0x7, var14, 0x11000000);
    }
}

