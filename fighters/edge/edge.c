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
int global22;
int global23;
int global24;
int global25;
int global26;
int global27;
int global28;
int global29;
int global30;
int global31;
float global32;
int global33;
int global34;
int global35;
int global36;
int global37;
int global38;
int global39;
int global40;
int global41;
int global42;
int global43;
int global44;
int global45;
int global46;
int global47;
float global48;
int global49;
float global50;
int global51;
int global52;
int global53;
int global54;
int global55;
int global56;
int global57;
int global58;
int global59;
int global60;
int global61;
int global62;
int global63;
int global64;

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
    printf("sys_line_status_end_init");
    callFunc3(func_2);
}

void func_2()
{
    printf("sys_line_status_end_control");
    global6 = StatusModule(0x9);
    if (global6 >= global7)
    {
        printf("Warning : @g_status_kind_next_(%d) >= @g_status_kind_max_(%d)", global6, global7);
        return;
    }
    func_18();
    func_3(global4);
}

void func_3(int arg0)
{
    int var1;
    if (sys_5(0x5))
    {
        sys_1(0x5);
    }
    func_4();
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

void func_4()
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

void func_5()
{
    printf("sys_line_status_shift_init");
    callFunc3(func_6);
}

void func_6()
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
        if (func_7(global4))
        {
            global4 = StatusModule(0x7);
            func_7(global4);
        }
        func_8(global4);
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

int func_7(int arg0)
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

void func_8(int arg0)
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
    func_9(arg0);
}

void func_9(int arg0)
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

void func_10()
{
    printf("sys_line_status_system_init");
    printf("PLATFORM CAFE");
    callFunc3(func_11);
}

void func_11()
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

int func_12(int arg0)
{
    if (arg0 < 0)
    {
        return -arg0;
    }
    return arg0;
}

float func_13(float arg0)
{
    if (arg0 < (float)0)
    {
        return -arg0;
    }
    return arg0;
}

void func_14(float arg0)
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

float func_15(float arg0, float arg1, float arg2)
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

void func_16(int arg0, int arg1)
{
    if (global11)
    {
        (*global11)(arg0, arg1);
    }
}

void func_17(int arg0, int arg1)
{
    StatusModule(0x3, arg0, arg1);
}

void func_18()
{
    int var0;
    int var1;
    if (global13)
    {
        (*global13)(var0, var1);
    }
}

int func_19(int arg0, int arg1)
{
    BattleObject(0x19, arg0, arg1);
    return 0x1;
}

void func_20(int arg0)
{
    StatusModule(0x2, arg0);
    global19 = global18;
    global18 = arg0;
}

void func_21(int arg0, int arg1)
{
    StatusModule(0x2, arg0, arg1);
    global19 = global18;
    global18 = arg0;
}

void func_22(int arg0, float arg1, int arg2)
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

void func_23(int arg0)
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

void func_24(int arg0)
{
    int var1;
    var1 = arg0;
    if (global21)
    {
        var1 = (*global21)(arg0);
    }
    MotionModule(0x25, var1);
}

void func_25(int arg0)
{
    int var1;
    var1 = arg0;
    if (global21)
    {
        var1 = (*global21)(arg0);
    }
    MotionModule(0x26, var1);
}

void func_26(int arg0, int arg1, int arg2)
{
    int var3;
    var3 = arg0;
    if (global21)
    {
        var3 = (*global21)(arg0);
    }
    MotionModule(0x26, var3, arg1, arg2);
}

void func_27(int arg0)
{
    int var1;
    var1 = arg0;
    if (global21)
    {
        var1 = (*global21)(arg0);
    }
    MotionModule(0x3, var1, MotionModuleF(0x1));
}

void func_28(int arg0, float arg1, int arg2)
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

void func_29(int arg0, float arg1, int arg2, int arg3)
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

int func_30(int arg0)
{
    if (randi(0, arg0) == 0)
    {
        return 0x1;
    }
    return 0;
}

int func_31(int arg0)
{
    int var1;
    var1 = MotionModule(0x7);
    if (var1 == arg0 || var1 == arg0 + 0x1 || var1 == arg0 + 0x2 || var1 == arg0 + 0x3)
    {
        return 0x1;
    }
    return 0;
}

int func_32(int arg0, int arg1)
{
    if (arg0 == arg1 || arg0 == arg1 + 0x1 || arg0 == arg1 + 0x2 || arg0 == arg1 + 0x3)
    {
        return 0x1;
    }
    return 0;
}

void func_33()
{
    PostureModule(0x271c);
    PostureModule(0x2);
}

int func_34()
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

void func_35(int arg0, float arg1, int arg2)
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

void func_36()
{
    printf("sys_line_waza_customize_init");
    callFunc3(func_37);
}

void func_37()
{
    printf("sys_line_waza_customize_control");
    if (global22)
    {
        (*global22)();
    }
}

void func_38()
{
    WorkModule(0x19, 0x1f000000);
    WorkModule(0x19, 0x1f000001);
    WorkModule(0x19, 0x1f000002);
    WorkModule(0x19, 0x1f000003);
    WorkModule(0x19, 0x1f000004);
    WorkModule(0x19, 0x1f000005);
    WorkModule(0x19, 0x1f000006);
    WorkModule(0x19, 0x1f000007);
}

int func_39()
{
    if (func_43())
    {
        return 0x1;
    }
    if (func_44())
    {
        return 0x1;
    }
    if (func_46())
    {
        return 0x1;
    }
    if (func_47())
    {
        return 0x1;
    }
    if (func_48())
    {
        return 0x1;
    }
    if (func_49())
    {
        return 0x1;
    }
    if (func_51())
    {
        return 0x1;
    }
    if (func_52())
    {
        return 0x1;
    }
    return 0;
}

void func_40()
{
    WorkModule(0x19, 0x1f000008);
    WorkModule(0x19, 0x1f00000a);
    WorkModule(0x19, 0x1f00000b);
    WorkModule(0x19, 0x1f00000c);
    WorkModule(0x19, 0x1f00000d);
    WorkModule(0x19, 0x1f00000e);
    WorkModule(0x19, 0x1f00000f);
    WorkModule(0x19, 0x1f000010);
    WorkModule(0x19, 0x1f000011);
}

int func_41()
{
    if (func_55())
    {
        return 0x1;
    }
    if (WorkModule(0x10, 0x2000000b))
    {
        func_16(0xd8, 0);
        return 0x1;
    }
    if (func_56())
    {
        return 0x1;
    }
    if (func_567())
    {
        return 0x1;
    }
    if (func_58())
    {
        return 0x1;
    }
    if (func_59())
    {
        return 0x1;
    }
    if (func_61())
    {
        return 0x1;
    }
    if (func_62())
    {
        return 0x1;
    }
    if (func_63())
    {
        return 0x1;
    }
    if (func_65())
    {
        return 0x1;
    }
    if (func_66())
    {
        return 0x1;
    }
    if (func_67())
    {
        return 0x1;
    }
    return 0;
}

int func_42()
{
    if (WorkModule(0x10, 0x2000001b))
    {
        StatusModule(0x2711, 0x57);
        return 0x1;
    }
    return 0;
}

int func_43()
{
    if (func_71(global23))
    {
        return 0x1;
    }
    if (global18 != 0)
    {
        return 0;
    }
    if (func_60())
    {
        return 0x1;
    }
    if (global24 & 0x2000)
    {
        if (WorkModule(0x15, 0x1e000063))
        {
            if (func_72(global25))
            {
                func_16(0x153, 0x1);
                return 0x1;
            }
        }
    }
    if (global24 & 0x4000)
    {
        if (WorkModule(0x15, 0x1e000064))
        {
            if (func_72(global26) && edge_hi_can())
            {
                func_16(0x154, 0x1);
                return 0x1;
            }
        }
    }
    if (global24 & 0x8000)
    {
        if (WorkModule(0x15, 0x1e000065))
        {
            if (func_72(global27))
            {
                if (edge_lw_can_counter())     // Sephiroth: not while the Phantom charges (test 105)
                {
                    func_16(0x155, 0x1);
                    return 0x1;
                }
            }
        }
    }
    if (global24 & 0x1000)
    {
        if (WorkModule(0x15, 0x1e000094))
        {
            if (global1 == 0x38)
            {
                if (BattleObject(0x61))
                {
                    func_16(0x156, 0x1);
                    return 0x1;
                }
                else if (WorkModule(0x10, 0x20000006) && WorkModule(0x10, 0x20000008))
                {
                    func_16(0x164, 0x1);
                    return 0x1;
                }
            }
            else if (BattleObject(0x61))
            {
                func_16(0x156, 0x1);
                return 0x1;
            }
        }
        if (WorkModule(0x15, 0x1e000062))
        {
            if (func_72(global28))
            {
                func_16(0x152, 0x1);
                return 0x1;
            }
        }
    }
    return 0;
}

int func_44()
{
    return func_45();
}

int func_45()
{
    if (global18 != 0)
    {
        return 0;
    }
    if ((global24 & 0x20000000) != 0 && WorkModule(0x15, 0x1e000076) == 0x1 && ItemModule(0x4) == 0x1 && ItemModule(0x5, 0x800000) == 0)
    {
        func_16(0x8c, 0);
        return 0x1;
    }
    if ((global29 & 0x1bf) != 0 && WorkModule(0x15, 0x1e000074) == 0x1)
    {
        if (ItemModule(0x5, 0x8) == 0x1 || ItemModule(0x5, 0x2) == 0x1 && ItemModule(0x1a) <= 0)
        {
            func_16(0x8c, 0);
            return 0x1;
        }
    }
    return 0;
}

int func_46()
{
    if (global18 != 0)
    {
        return 0;
    }
    if (global24 & 0x20000000)
    {
        if (WorkModule(0x15, 0x1e00006d))
        {
            func_16(0x35, 0x1);
            return 0x1;
        }
    }
    return 0;
}

int func_47()
{
    if (func_71(global30))
    {
        return 0x1;
    }
    if (global18 != 0)
    {
        return 0;
    }
    if (global24 & 0x1)
    {
        if (ItemModule(0x11) == 0x6f)
        {
            func_16(0x10d, 0x1);
            return 0x1;
        }
    }
    if ((global24 & 0x10) != 0)
    {
        if (WorkModule(0x15, 0x1e00007b) == 0x1 && ItemModule(0x5, 0x4) == 0x1)
        {
            func_16(0x94, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000082) == 0x1 && ItemModule(0x5, 0x2) == 0x1)
        {
            func_16(0x98, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000059))
        {
            func_16(0x2b, 0x1);
            return 0x1;
        }
    }
    if (global24 & 0x20)
    {
        if (WorkModule(0x15, 0x1e00005c))
        {
            func_16(0x31, 0x1);
            return 0x1;
        }
    }
    if (global24 & 0x40)
    {
        if (WorkModule(0x15, 0x1e00005f))
        {
            func_16(0x2e, 0x1);
            return 0x1;
        }
    }
    if (global24 & 0x4)
    {
        if (WorkModule(0x15, 0x1e000056))
        {
            func_16(0x29, 0x1);
            return 0x1;
        }
    }
    if (global24 & 0x1)
    {
        if (WorkModule(0x15, 0x1e000072))
        {
            if (0 < ItemModule(0))
            {
                if (ItemModule(0x22))
                {
                    func_16(0x8a, 0x1);
                    return 0x1;
                }
            }
        }
        if (WorkModule(0x15, 0x1e000073))
        {
            if (0 < ItemModule(0x1))
            {
                if (ItemModule(0x4) == 0)
                {
                    func_16(0x8b, 0x1);
                    return 0x1;
                }
            }
        }
    }
    else if (BattleObject(0x86, 0x1))
    {
        if (WorkModule(0x15, 0x1e000072))
        {
            if (0 < ItemModule(0))
            {
                if (ItemModule(0x22))
                {
                    func_16(0x8a, 0);
                    return 0x1;
                }
            }
        }
        if (WorkModule(0x15, 0x1e000073))
        {
            if (0 < ItemModule(0x1))
            {
                if (ItemModule(0x4) == 0)
                {
                    func_16(0x8b, 0);
                    return 0x1;
                }
            }
        }
    }
    if ((global24 & 0x2) != 0 && WorkModule(0x15, 0x1e00007d) == 0x1 && ItemModule(0x5, 0x4) == 0x1)
    {
        func_16(0x93, 0x1);
        return 0x1;
    }
    if (global24 & 0x8)
    {
        if (WorkModule(0x15, 0x1e000057))
        {
            func_16(0x2a, 0x1);
            return 0x1;
        }
    }
    if (global24 & 0x2)
    {
        if (WorkModule(0x15, 0x1e000081) == 0x1 && ItemModule(0x5, 0x2) == 0x1)
        {
            func_16(0x98, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000055))
        {
            func_16(0x28, 0x1);
            return 0x1;
        }
    }
    if ((global24 & 0x1) != 0)
    {
        if (WorkModule(0x15, 0x1e00007e) == 0x1 && ItemModule(0x5, 0x4) == 0x1)
        {
            func_16(0x92, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000080) == 0x1 && ItemModule(0x5, 0x2) == 0x1)
        {
            func_16(0x98, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000053))
        {
            if (WorkModule(0x6, 0x13000106) == 0x3)
            {
                func_16(0x26, 0x1);
                return 0x1;
            }
        }
        if (WorkModule(0x15, 0x1e000052))
        {
            func_16(0x25, 0x1);
            return 0x1;
        }
    }
    return 0;
}

int func_48()
{
    if (global18 != 0)
    {
        return 0;
    }
    if (global24 & 0x1000000)
    {
        if (WorkModule(0x15, 0x1e000026))
        {
            func_16(0x1f, 0x1);
            return 0x1;
        }
    }
    if (global24 & 0x2000000)
    {
        if (WorkModule(0x15, 0x1e000027))
        {
            func_16(0x20, 0x1);
            return 0x1;
        }
    }
    if (global24 & 0x4000000)
    {
        if (WorkModule(0x15, 0x1e000028))
        {
            func_16(0x21, 0x1);
            return 0x1;
        }
    }
    return 0;
}

int func_49()
{
    if (global18 != 0)
    {
        return 0;
    }
    if (WorkModule(0x15, 0x1e000029))
    {
        if (func_50())
        {
            func_16(0x1b, 0x1);
            return 0x1;
        }
    }
    return 0;
}

int func_50()
{
    if (ControlModule(0x2712, 0x3))
    {
        return 0x1;
    }
    return 0;
}

int func_51()
{
    int var0;
    int var1;
    if (global18 != 0)
    {
        return 0;
    }
    if (global24 & 0x200000)
    {
        if (WorkModule(0x15, 0x1e00002c))
        {
            func_16(0xa, 0x1);
            return 0x1;
        }
    }
    if (global24 & 0x100000)
    {
        if (WorkModule(0x15, 0x1e00002b))
        {
            if (ControlModule(0x271c))
            {
                var0 = ControlModule(0x14, 0, 0x14);
                var1 = ControlModule(0x15);
                WorkModule(0x7, var1 - var0, 0x1000007b);
                func_16(0xa, 0x1);
                return 0x1;
            }
        }
    }
    return 0;
}

int func_52(int arg0)
{
    if (global18 != 0)
    {
        return 0;
    }
    if (global31 & 0x2)
    {
        if (WorkModule(0x15, 0x1e000039) && BattleObject(0x80) == 0x1)
        {
            func_16(0x14d, 0);
            return 0x1;
        }
    }
    if (global31 & 0x4)
    {
        if (WorkModule(0x15, 0x1e00003b) && BattleObject(0x80) == 0x1)
        {
            func_16(0x14d, 0);
            return 0x1;
        }
    }
    if (global31 & 0x1)
    {
        if (WorkModule(0x15, 0x1e00003a) && BattleObject(0x80) == 0x1)
        {
            func_16(0x14d, 0);
            return 0x1;
        }
    }
    if (global24 & 0x80000)
    {
        if (WorkModule(0x15, 0x1e000031))
        {
            func_16(0x7, 0x1);
            return 0x1;
        }
    }
    if (global24 & 0x20000)
    {
        if (WorkModule(0x15, 0x1e00002d))
        {
            func_16(0x3, 0x1);
            return 0x1;
        }
    }
    if (WorkModule(0x15, 0x1e000034))
    {
        if (func_53())
        {
            if (arg0 == 0)
            {
                func_16(0x11, 0x1);
            }
            else
            {
                func_16(0x12, 0x1);
            }
            return 0x1;
        }
    }
    if (global24 & 0x40000)
    {
        if (WorkModule(0x15, 0x1e00002f))
        {
            func_16(0x6, 0x1);
            return 0x1;
        }
    }
    if (WorkModule(0x15, 0x1e00003c))
    {
        if (func_54())
        {
            func_16(0x1, 0x1);
            return 0x1;
        }
    }
    return 0;
}

int func_53()
{
    if (global32 <= WorkModuleF(0, 0x200001a))
    {
        return 0x1;
    }
    return 0;
}

int func_54()
{
    if (func_88() >= WorkModuleF(0, 0x2000001))
    {
        if (global32 > WorkModuleF(0, 0x200001a))
        {
            return 0x1;
        }
    }
    return 0;
}

int func_55()
{
    if (global18 != 0)
    {
        return 0;
    }
    if (func_71(global33))
    {
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00001c))
    {
        if (WorkModule(0x6, 0x1000000d) < WorkModule(0x6, 0x13000029))
        {
            func_16(0x17, 0);
            return 0x1;
        }
    }
    if (WorkModule(0x15, 0x1e00001b))
    {
        func_16(0x16, 0);
        return 0x1;
    }
    return 0;
}

int func_56()
{
    if (func_71(global34))
    {
        return 0;
    }
    if (global18 == 0x2 && GroundModule(0x2725) && global32 > WorkModuleF(0, 0x200006c) && WorkModule(0x15, 0x1e00001f) && GroundModule(0x2724) && WorkModule(0x6, 0x10000003) == 0)
    {
        WorkModule(0x2710, 0x2100000b);
        func_16(0x72, 0x1);
        return 0x1;
    }
    else if (WorkModule(0x10, 0x2100000b) == 0x1)
    {
        printf("DELETE_CHANGE_STATUS_REQUEST !!!!!!!");
        WorkModule(0x2711, 0x2100000b);
        StatusModule(0xc);
    }
    return 0;
}

int func_57()
{
    if (global18 == 0x2 && WorkModule(0x15, 0x1e00001f) && GroundModule(0x2724) && GroundModule(0x2725))
    {
        func_16(0x72, 0);
        return 0x1;
    }
    return 0;
}

int func_58()
{
    if (func_71(global35))
    {
        return 0x1;
    }
    if (global18 != 0x2)
    {
        return 0;
    }
    if (func_60())
    {
        return 0x1;
    }
    if (global24 & 0x4000)
    {
        if (WorkModule(0x15, 0x1e000064))
        {
            if (func_72(global26) && edge_hi_can())
            {
                func_16(0x154, 0x1);
                return 0x1;
            }
        }
    }
    if (global24 & 0x8000)
    {
        if (WorkModule(0x15, 0x1e000065))
        {
            if (func_72(global27))
            {
                if (edge_lw_can_counter())     // Sephiroth: not while the Phantom charges (test 105)
                {
                    func_16(0x155, 0x1);
                    return 0x1;
                }
            }
        }
    }
    if (global24 & 0x2000)
    {
        if (WorkModule(0x15, 0x1e000063))
        {
            if (func_72(global25))
            {
                func_16(0x153, 0x1);
                return 0x1;
            }
        }
    }
    if (global24 & 0x1000)
    {
        if (WorkModule(0x15, 0x1e000094))
        {
            if (global1 == 0x38)
            {
                if (BattleObject(0x61))
                {
                    func_16(0x156, 0x1);
                    return 0x1;
                }
                else if (WorkModule(0x10, 0x20000006) && WorkModule(0x10, 0x20000008))
                {
                    func_16(0x164, 0x1);
                    return 0x1;
                }
            }
            else if (BattleObject(0x61))
            {
                func_16(0x156, 0x1);
                return 0x1;
            }
        }
        if (WorkModule(0x15, 0x1e000062))
        {
            if (func_72(global28))
            {
                func_16(0x152, 0x1);
                return 0x1;
            }
        }
    }
    return 0;
}

int func_59()
{
    if (func_71(global36))
    {
        return 0x1;
    }
    if (global18 != 0x2)
    {
        return 0;
    }
    if ((global24 & 0x20000000) != 0 && WorkModule(0x15, 0x1e000076) == 0x1 && ItemModule(0x4) == 0x1 && ItemModule(0x5, 0x800000) == 0)
    {
        func_16(0x8c, 0);
        return 0x1;
    }
    if ((global29 & 0x1fe00) != 0 && WorkModule(0x15, 0x1e000074) == 0x1)
    {
        if (ItemModule(0x5, 0x8) == 0x1 || ItemModule(0x5, 0x2) == 0x1 && ItemModule(0x1a) <= 0)
        {
            func_16(0x8c, 0);
            return 0x1;
        }
    }
    return 0;
}

int func_60()
{
    if (WorkModule(0x10, 0x20000074) == 0)
    {
        return 0;
    }
    if (func_71(global37))
    {
        return 0x1;
    }
    return 0;
}

int func_61()
{
    int var0;
    if (global18 != 0x2)
    {
        return 0;
    }
    if (global38 & 0x1)
    {
        if (WorkModule(0x15, 0x1e000051))
        {
            if (WorkModule(0x6, 0x1300011f) != 0)
            {
                if (ControlModule(0x2712, 0x3))
                {
                    var0 = LinkModule(0x2, 0x3);
                    if (!var0)
                    {
                        func_16(0xf1, 0x1);
                        return 0x1;
                    }
                }
            }
        }
    }
    return 0;
}

int func_62()
{
    if (func_71(global39))
    {
        return 0x1;
    }
    if (global18 != 0x2)
    {
        return 0;
    }
    if (global24 & 0x400000)
    {
        if (WorkModule(0x15, 0x1e00003d))
        {
            func_16(0x22, 0x1);
            return 0x1;
        }
    }
    return 0;
}

int func_63()
{
    if (func_71(global40))
    {
        return 0x1;
    }
    if (global18 != 0x2)
    {
        return 0;
    }
    if ((global24 & 0x1) != 0)
    {
        if (WorkModule(0x15, 0x1e00008a) == 0x1 && func_64() == 0x1)
        {
            func_16(0xa1, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000061))
        {
            func_16(0x34, 0x1);
            return 0x1;
        }
    }
    return 0;
}

int func_64()
{
    if ((global29 & 0x600) != 0)
    {
        if (ItemModule(0x4) == 0x1)
        {
            if (ItemModule(0x5, 0x2) == 0x1 && ItemModule(0x5, 0x4) == 0)
            {
                return 0x1;
            }
        }
    }
    return 0;
}

int func_65()
{
    if (func_71(global41))
    {
        return 0x1;
    }
    if (global18 == 0x2)
    {
        if (global24 & 0x100000 && WorkModule(0x15, 0x1e000040) && ControlModule(0x271c) && WorkModule(0x6, 0x10000007) == 0 && func_83() >= WorkModuleF(0, 0x20000b6) && BattleObject(0x18))
        {
            func_16(0xb3, 0x1);
            return 0x1;
        }
        if (global38 & 0x10 && WorkModule(0x15, 0x1e000041) && WorkModule(0x6, 0x10000007) == 0 && func_83() >= WorkModuleF(0, 0x20000b6) && BattleObject(0x18))
        {
            func_16(0xb3, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000042) && BattleObject(0x18, 0x1))
        {
            func_16(0xb3, 0);
            return 0x1;
        }
    }
    return 0;
}

int func_66()
{
    if (func_71(global42))
    {
        return 0x1;
    }
    if (global18 != 0x2)
    {
        return 0;
    }
    if (WorkModule(0x6, 0x1300011e) == 0x1)
    {
        if (func_97() != 0)
        {
            func_16(0x6c, 0x1);
            return 0x1;
        }
    }
    if (WorkModule(0x6, 0x1300011d) == 0x1)
    {
        if (func_98() != 0)
        {
            func_16(0x6b, 0x1);
            return 0x1;
        }
    }
    return 0;
}

int func_67()
{
    if (func_71(global43))
    {
        return 0x1;
    }
    if (global18 != 0x2)
    {
        return 0;
    }
    if (WorkModule(0x6, 0x1300010c) == 0x1)
    {
        if (global24 & 0x100000)
        {
            if (WorkModule(0x15, 0x1e00003e))
            {
                if (WorkModule(0x6, 0x10000001) < WorkModule(0x6, 0x10000002))
                {
                    if (ControlModule(0x271c))
                    {
                        func_16(0xc, 0x1);
                        return 0x1;
                    }
                }
            }
        }
        if (global24 & 0x200000)
        {
            if (WorkModule(0x15, 0x1e00003f))
            {
                if (WorkModule(0x6, 0x10000001) < WorkModule(0x6, 0x10000002))
                {
                    func_16(0xc, 0x1);
                    return 0x1;
                }
            }
        }
    }
    else
    {
        if (global24 & 0x200000)
        {
            if (WorkModule(0x15, 0x1e000044))
            {
                if (WorkModule(0x6, 0x10000001) == 0x1)
                {
                    func_16(0xd, 0x1);
                    return 0x1;
                }
            }
        }
        if (global24 & 0x100000)
        {
            if (WorkModule(0x15, 0x1e000043))
            {
                if (WorkModule(0x6, 0x10000001) == 0x1)
                {
                    if (ControlModule(0x271c))
                    {
                        func_16(0xd, 0x1);
                        return 0x1;
                    }
                }
            }
        }
        if (WorkModule(0x15, 0x1e000045) && func_68() && WorkModule(0x6, 0x10000001) < WorkModule(0x6, 0x10000002))
        {
            func_16(0xd, 0x1);
            return 0x1;
        }
    }
    if (func_71(global44))
    {
        return 0x1;
    }
    return 0;
}

int func_68()
{
    int var0;
    var0 = WorkModule(0x6, 0x1300010c);
    if (var0 == 0x2)
    {
        if (WorkModule(0x6, 0x10000001) >= 0x2 && (ControlModule(0x2712, 0x2) || global32 >= WorkModuleF(0, 0x200001f) && ControlModule(0x271c)))
        {
            if (global4 != 0xd && global4 != 0xa4 || WorkModule(0x10, 0x2100000e) == 0x1)
            {
                if (global5 == 0xb3 && KineticModuleF(0x1, 0x1) > 0)
                {
                    return 0;
                }
                return 0x1;
            }
        }
    }
    else if (var0 == 0x3)
    {
        if (WorkModule(0x6, 0x10000001) >= 0x2 && (global24 & 0x200000 || global32 >= WorkModuleF(0, 0x200001f) && ControlModule(0x271c)))
        {
            if (global4 != 0xd && global4 != 0xa4 || WorkModule(0x10, 0x2100000e) == 0x1)
            {
                if (global5 == 0xb3 && KineticModuleF(0x1, 0x1) > 0)
                {
                    return 0;
                }
                return 0x1;
            }
        }
    }
    return 0;
}

void func_69()
{
    if (global18 == 0x2)
    {
        if (global31 & 0x20000)
        {
            PostureModule(0x2710);
        }
    }
}

void func_70()
{
    func_69();
}

int func_71(int arg0)
{
    if (arg0)
    {
        return (*arg0)();
    }
    return 0;
}

int func_72(int arg0)
{
    if (arg0)
    {
        return (*arg0)();
    }
    return 0x1;
}

void func_73()
{
    printf("sys_line_system_init");
    callFunc3(func_74);
}

void func_74()
{
    int var0;
    int var1;
    global19 = global18;
    global18 = StatusModule(0x1);
    func_77();
    global38 = ControlModule(0x9);
    global24 = ControlModule(0xa, 0);
    global31 = ControlModule(0xa, 0x1);
    global29 = ControlModule(0xa, 0x2);
    global45 = ControlModule(0xa, 0x3);
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

void func_75()
{
    ControlModule(0x2719);
    global46 = 0xfe;
}

void func_76()
{
    ControlModule(0x271a);
    global47 = 0xfe;
}

void func_77()
{
    global48 = ControlModuleF(0);
    global32 = ControlModuleF(0x1);
    global46 = ControlModule(0x2);
    global47 = ControlModule(0x3);
    global49 = ControlModule(0);
}

void func_78(int arg0)
{
    if (ControlModule(0xc))
    {
        ControlModule(0xb);
        global38 = ControlModule(0x9);
        global24 = ControlModule(0xa, 0);
        global31 = ControlModule(0xa, 0x1);
        global29 = ControlModule(0xa, 0x2);
        global45 = ControlModule(0xa, 0x3);
    }
    if (arg0)
    {
        callFunc3(arg0);
    }
}

void func_79(int arg0, int arg1)
{
    int var2;
    global50 = 0;
    global15 = 0;
    var2 = StatusModule(0xd);
    if (var2 == 0xd0 || var2 == 0xd2 || var2 == 0xfe)
    {
        return;
    }
    if (WorkModule(0x10, 0x2000004d))
    {
        if (func_108(arg0) == 0x1)
        {
            if (global18 == 0)
            {
                arg0 = 0x83;
            }
            else if (global18 == 0x2 || global18 == 0x1)
            {
                arg0 = 0x10;
            }
        }
    }
    StatusModule(0x3, arg0, arg1);
}

void func_80()
{
    global50 = 0;
    global15 = 0;
}

void func_81()
{
    float var0;
    if (WorkModule(0x10, 0x21000001))
    {
        if (global50 <= 2.0f)
        {
            if (FighterUtil(0x23, global6) || global6 == 0x152 || global6 == 0x153 || global6 == 0x154 || global6 == 0x155)
            {
                var0 = -WorkModuleF(0, 0x3000019);
                KineticModule(0x11, 0x1, var0);
                WorkModule(0x2711, 0x21000001);
            }
        }
    }
}

void func_82()
{
    edge_fx_sweep();                   // Sephiroth: endless effects outside their statuses off (multi-instance v1)
    edge_lw_ph_tick();                 // Sephiroth: Zelda's Phantom charging from down special (tests 103 / 104)
    edge_hi_air_tick();                // Sephiroth: up special once per air time (test 113)
    edge_tr_tick();                    // ... its trail's shapes (test 126)
    edge_s_line_tick();                // Shadow Flare's shot as a line while it flies (test 148)
    edge_hi_keep_in();                 // ... Octaslash's victims kept in the blast zones (test 127)
    if (!global3)
    {
        if (WorkModule(0x10, 0x21000001))
        {
            if (global50 < 1000000.0f)
            {
                global50 += 1.0f;
            }
        }
    }
    if (global8 || ControlModule(0x13))
    {
        global38 = ControlModule(0x9);
        global24 = ControlModule(0xa, 0);
        global31 = ControlModule(0xa, 0x1);
        global29 = ControlModule(0xa, 0x2);
        global45 = ControlModule(0xa, 0x3);
    }
}

float func_83()
{
    float var0;
    int var1;
    float var2;
    var0 = WorkModuleF(0, 0x300015f);
    var1 = WorkModule(0x6, 0x10000006);
    if (var1 > 0)
    {
        var2 = KineticModuleF(0x1, 0x1);
        var0 += var2 * WorkModuleF(0, 0x2000024);
        var0 *= MathF(0x2, WorkModuleF(0, 0x20000b5), var1 + 0x1);
    }
    return var0;
}

float func_84()
{
    return func_13(global48);
}

float func_85()
{
    return func_13(global32);
}

float func_86()
{
    return func_13(ControlModuleF(0x2));
}

float func_87()
{
    return func_13(ControlModuleF(0x3));
}

float func_88()
{
    float var0;
    float var1;
    var0 = PostureModuleF(0);
    var1 = global48 * var0;
    return var1;
}

float func_89()
{
    float var0;
    float var1;
    var0 = PostureModuleF(0);
    var1 = global48 * -var0;
    return var1;
}

float func_90()
{
    return KineticModuleF(0x2, 0x1);
}

float func_91()
{
    return KineticModuleF(0x1, 0x1);
}

float func_92()
{
    return KineticModuleF(0x4);
}

float func_93()
{
    return KineticModuleF(0x5);
}

void func_94()
{
    func_20(0x2);
    GroundModule(0x2710, 0x5);
}

int func_95()
{
    if (StopModule(0) == 0x1 || WorkModule(0x6, 0x11000003) > 0)
    {
        return 0x1;
    }
    return 0;
}

int func_96()
{
    int var0;
    var0 = 0;
    if (ControlModuleF(0x5, var0) <= 0)
    {
        return 0x1;
    }
    return 0;
}

int func_97()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    float var7;
    float var8;
    float var9;
    float var10;
    float var11;
    var0 = (float)0xffffffff;
    var1 = (float)0x1;
    var2 = 0;
    var3 = 0;
    if (GroundModule(0x2722, 0x2) != 0)
    {
        if (GroundModule(0xf, 0x2) == 0)
        {
            return 0;
        }
        var2 = var1;
    }
    else if (GroundModule(0x2722, 0x4) != 0)
    {
        if (GroundModule(0xf, 0x4) == 0)
        {
            return 0;
        }
        var2 = var0;
    }
    if (var2 != 0)
    {
        if (WorkModule(0x6, 0x1000000b) <= 0)
        {
            var4 = WorkModuleF(0, 0x20000af);
            if (var2 == var1 && global48 <= -var4 || var2 == var0 && global48 >= var4)
            {
                var5 = KineticModuleF(0x1, 0x1);
                if (var5 > 0)
                {
                    return 0;
                }
                var6 = (float)0;
                var7 = (float)0;
                if (var2 == var1)
                {
                    var6 = GroundModuleF(0x5, 0x2);
                    var7 = GroundModuleF(0x6, 0x2);
                }
                else
                {
                    var6 = GroundModuleF(0x5, 0x4);
                    var7 = GroundModuleF(0x6, 0x4);
                }
                var8 = MathF(0x1, var6, var7);
                var9 = var8 * -var2 * (float)0xb4 / M_PI + 90.0f;
                var10 = WorkModuleF(0, 0x20000b8);
                var11 = WorkModuleF(0, 0x20000b9);
                if (var9 < var10 && var9 > var11)
                {
                    return 0x1;
                }
            }
        }
    }
    return 0;
}

int func_98()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    if (!WorkModule(0x10, 0x2000006c))
    {
        var0 = (float)0xffffffff;
        var1 = (float)0x1;
        var2 = 0;
        if (GroundModule(0x2722, 0x2) != 0)
        {
            if (GroundModule(0xf, 0x2) == 0)
            {
                return 0;
            }
            var2 = var1;
        }
        else if (GroundModule(0x2722, 0x4) != 0)
        {
            if (GroundModule(0xf, 0x4) == 0)
            {
                return 0;
            }
            var2 = var0;
        }
        if (var2 != 0)
        {
            if (var2 != WorkModuleF(0, 0x2) || WorkModule(0x6, 0x10000005) <= 0)
            {
                var3 = WorkModuleF(0, 0x3000073);
                var4 = KineticModuleF(0, 0x1);
                if (func_13(var4) >= var3)
                {
                    var5 = WorkModuleF(0, 0x20000af);
                    var6 = WorkModuleF(0, 0x200001f);
                    if (var2 == var1 && (global48 >= var5 || global24 & 0x8000000) || var2 == var0 && (global48 <= -var5 || global24 & 0x10000000))
                    {
                        return 0x1;
                    }
                }
            }
        }
    }
    return 0;
}

int func_99()
{
    float var0;
    float var1;
    float var2;
    float var3;
    if (GroundModule(0x2724) && GroundModule(0x2725) && WorkModule(0x6, 0x10000003) == 0)
    {
        var0 = GroundModuleF(0x7);
        var1 = GroundModuleF(0x1);
        var2 = PostureModuleF(0x1);
        var3 = func_14(var1 - var2);
        if (var0 != var3)
        {
            return 0x1;
        }
        else
        {
            return 0;
        }
    }
    return 0;
}

void func_100(int arg0)
{
    if (arg0 != 0)
    {
        WorkModule(0x19, 0x1f000009);
    }
    else
    {
        WorkModule(0x1a, 0x1f000009);
    }
    GroundModule(0x2711, arg0);
}

void func_101()
{
    KineticModule(0, 0x6);
    func_20(0);
    GroundModule(0x2710, 0x1);
}

void func_102()
{
    KineticModule(0, 0);
    func_20(0x2);
    GroundModule(0x2710, 0x5);
}

void func_103()
{
    if (!WorkModule(0x10, 0x20000004))
    {
        ItemModule(0x6, 0, 0, 0xffffffff, 0x1);
        if (ItemModule(0x3))
        {
            WorkModule(0x2710, 0x20000004);
            ControlModule(0x271b);
            ControlModule(0x271f);
            global24 = 0;
            global31 = 0;
            global29 = 0;
            global45 = 0;
            global38 = 0;
        }
    }
}

void func_104()
{
    if ((global29 & 0x100000) != 0)
    {
        func_103();
    }
    else if (BattleObject(0x86, 0x1))
    {
        func_103();
    }
}

void func_105()
{
    if (ItemModule(0x4) == 0x1 && (global29 & 0x20000) != 0 && ItemModule(0x5, 0x800000) == 0)
    {
        ItemModule(0x7, 0, 0, WorkModuleF(0, 0x300003d));
        BattleObject(0x1c, 0x10);
        ControlModule(0x271b);
        ControlModule(0x271f);
        global24 = 0;
        global31 = 0;
        global29 = 0;
        global45 = 0;
        WorkModule(0x2710, 0x20000004);
    }
}

void func_106()
{
    if (global18 == 0)
    {
        KineticModule(0, 0x6);
        func_20(0);
        GroundModule(0x2710, 0x1);
        if (func_32(MotionModule(0x7), WorkModule(0x6, 0x11000003)) == 0x1)
        {
            func_23(WorkModule(0x6, 0x11000002));
        }
        else
        {
            func_22(WorkModule(0x6, 0x11000002), 0, 1.0f);
        }
        WorkModule(0x2711, 0x2100000d);
        WorkModule(0x7, 0x2, 0x11000004);
        WorkModule(0x16, 0x1e000000);
        WorkModule(0x17, 0x1e000002);
    }
    else
    {
        KineticModule(0, 0);
        func_20(0x2);
        GroundModule(0x2710, 0x5);
        if (func_32(MotionModule(0x7), WorkModule(0x6, 0x11000002)) == 0x1)
        {
            func_23(WorkModule(0x6, 0x11000003));
        }
        else
        {
            func_22(WorkModule(0x6, 0x11000003), 0, 1.0f);
        }
        WorkModule(0x2711, 0x2100000d);
        WorkModule(0x7, 0, 0x11000004);
        WorkModule(0x17, 0x1e000000);
        WorkModule(0x16, 0x1e000002);
    }
}

int func_107(int arg0)
{
    int var1;
    var1 = arg0;
    if (global51 != 0xffffffff)
    {
        if (var1 >= global51 && var1 < global52)
        {
            var1 += WorkModule(0x6, 0x10000048);
        }
        else if (var1 >= global52 && var1 < global53)
        {
            var1 += WorkModule(0x6, 0x10000049);
        }
        else if (var1 >= global53 && var1 < global54)
        {
            var1 += WorkModule(0x6, 0x1000004a);
        }
        else if (var1 >= global54 && var1 < global55)
        {
            var1 += WorkModule(0x6, 0x1000004b);
        }
    }
    return var1;
}

int func_108(int arg0)
{
    if (arg0 >= 0x25 && arg0 <= 0x2a || arg0 == 0x2b || arg0 == 0x2e || arg0 == 0x31 || FighterUtil(0x23, arg0) || arg0 == 0x35 || arg0 == 0x37 || arg0 == 0x75 || arg0 == 0x81 || arg0 == 0x87 || arg0 == 0x8c || arg0 == 0x8d || arg0 == 0x91 || arg0 == 0x92 || arg0 == 0x93 || arg0 == 0x94 || arg0 == 0x97 || arg0 >= 0x98 && arg0 <= 0xa2 || arg0 >= 0x152 && arg0 <= 0x156)
    {
        return 0x1;
    }
    return 0;
}

int func_109()
{
    int var0;
    var0 = ItemModule(0x11);
    return WorkModule(0x2712, 0x2000000b) == 0 && WorkModule(0x2712, 0x20000032) == 0 && var0 != 0;
}

void func_110()
{
    BattleObject(0x78);
}

void func_111()
{
    if (global6 == 0xe)
    {
        WorkModule(0x2710, 0x2000005f);
    }
}

void func_112()
{
    sv_set_mem(0x1, 0, 0xbf, func_1670);
    sv_set_mem(0x1, 0x1, 0xbf, func_1671);
    sv_set_mem(0x1, 0x2, 0xbf, func_1673);
    sv_set_mem(0x1, 0, 0xc0, func_1674);
    sv_set_mem(0x1, 0x1, 0xc0, func_1676);
    sv_set_mem(0x1, 0x2, 0xc0, func_1678);
    sv_set_mem(0x1, 0, 0xc1, func_1679);
    sv_set_mem(0x1, 0x1, 0xc1, func_1680);
    sv_set_mem(0x1, 0x2, 0xc1, func_1682);
    sv_set_mem(0x1, 0, 0xc2, func_1765);
    sv_set_mem(0x1, 0x1, 0xc2, func_1767);
    sv_set_mem(0x1, 0x2, 0xc2, func_1769);
    sv_set_mem(0x1, 0, 0xc3, func_1776);
    sv_set_mem(0x1, 0x1, 0xc3, func_1777);
    sv_set_mem(0x1, 0x2, 0xc3, func_1779);
    sv_set_mem(0x1, 0, 0xc4, func_1788);
    sv_set_mem(0x1, 0x1, 0xc4, func_1789);
    sv_set_mem(0x1, 0x2, 0xc4, func_1791);
    sv_set_mem(0x1, 0, 0xf6, func_1963);
    sv_set_mem(0x1, 0x1, 0xf6, func_1964);
    sv_set_mem(0x1, 0x2, 0xf6, func_1967);
    sv_set_mem(0x1, 0, 0xfa, func_1831);
    sv_set_mem(0x1, 0x1, 0xfa, func_1832);
    sv_set_mem(0x1, 0x2, 0xfa, func_1834);
    sv_set_mem(0x1, 0, 0xcc, func_1837);
    sv_set_mem(0x1, 0x1, 0xcc, func_1838);
    sv_set_mem(0x1, 0x2, 0xcc, func_1840);
    sv_set_mem(0x1, 0, 0xcd, func_1843);
    sv_set_mem(0x1, 0x1, 0xcd, func_1844);
    sv_set_mem(0x1, 0x2, 0xcd, func_1846);
    sv_set_mem(0x1, 0, 0x1a, func_481);
    sv_set_mem(0x1, 0x1, 0x1a, func_520);
    sv_set_mem(0x1, 0x2, 0x1a, func_540);
    sv_set_mem(0x1, 0, 0x102, func_1983);
    sv_set_mem(0x1, 0x1, 0x102, func_1984);
    sv_set_mem(0x1, 0x2, 0x102, func_1986);
    sv_set_mem(0x1, 0, 0x103, func_1987);
    sv_set_mem(0x1, 0x1, 0x103, func_1988);
    sv_set_mem(0x1, 0x2, 0x103, func_1990);
    sv_set_mem(0x1, 0, 0x11b, func_2195);
    sv_set_mem(0x1, 0x1, 0x11b, func_2196);
    sv_set_mem(0x1, 0x2, 0x11b, func_2198);
    sv_set_mem(0x1, 0, 0xce, func_1849);
    sv_set_mem(0x1, 0x1, 0xce, func_1850);
    sv_set_mem(0x1, 0x2, 0xce, func_1852);
    sv_set_mem(0x1, 0, 0xcf, func_1855);
    sv_set_mem(0x1, 0x1, 0xcf, func_1856);
    sv_set_mem(0x1, 0x2, 0xcf, func_1858);
    sv_set_mem(0x1, 0, 0x141, func_1861);
    sv_set_mem(0x1, 0x1, 0x141, func_1862);
    sv_set_mem(0x1, 0x2, 0x141, func_1864);
    sv_set_mem(0x1, 0, 0x11f, func_2201);
    sv_set_mem(0x1, 0x1, 0x11f, func_2202);
    sv_set_mem(0x1, 0x2, 0x11f, func_2204);
    sv_set_mem(0x1, 0, 0x120, func_2205);
    sv_set_mem(0x1, 0x1, 0x120, func_2206);
    sv_set_mem(0x1, 0x2, 0x120, func_2208);
    sv_set_mem(0x1, 0, 0x121, func_2209);
    sv_set_mem(0x1, 0x1, 0x121, func_2210);
    sv_set_mem(0x1, 0x2, 0x121, func_2212);
    sv_set_mem(0x1, 0, 0x126, func_2221);
    sv_set_mem(0x1, 0x1, 0x126, func_2222);
    sv_set_mem(0x1, 0x2, 0x126, func_2224);
    sv_set_mem(0x1, 0, 0x127, func_2225);
    sv_set_mem(0x1, 0x1, 0x127, func_2226);
    sv_set_mem(0x1, 0x2, 0x127, func_2228);
}

void func_113()
{
    sv_set_mem(0x1, 0, 0, func_670);
    sv_set_mem(0x1, 0, 0x1, func_697);
    sv_set_mem(0x1, 0, 0x2, func_699);
    sv_set_mem(0x1, 0, 0xa, func_469);
    sv_set_mem(0x1, 0, 0xb, func_472);
    sv_set_mem(0x1, 0, 0xc, func_474);
    sv_set_mem(0x1, 0, 0xd, func_475);
    sv_set_mem(0x1, 0, 0xe, func_476);
    sv_set_mem(0x1, 0, 0xf, func_477);
    sv_set_mem(0x1, 0, 0x10, func_977);
    sv_set_mem(0x1, 0, 0x16, func_478);
    sv_set_mem(0x1, 0, 0x17, func_479);
    sv_set_mem(0x1, 0, 0x18, func_480);
    sv_set_mem(0x1, 0, 0x19, func_978);
    sv_set_mem(0x1, 0, 0x3, func_700);
    sv_set_mem(0x1, 0, 0x4, func_701);
    sv_set_mem(0x1, 0, 0x5, func_702);
    sv_set_mem(0x1, 0, 0x6, func_705);
    sv_set_mem(0x1, 0, 0x7, func_706);
    sv_set_mem(0x1, 0, 0x8, func_707);
    sv_set_mem(0x1, 0, 0x9, func_708);
    sv_set_mem(0x1, 0, 0x11, func_593);
    sv_set_mem(0x1, 0, 0x12, func_594);
    sv_set_mem(0x1, 0, 0x13, func_595);
    sv_set_mem(0x1, 0, 0x14, func_596);
    sv_set_mem(0x1, 0, 0x15, func_597);
    sv_set_mem(0x1, 0, 0x1b, func_388);
    sv_set_mem(0x1, 0, 0x1c, func_389);
    sv_set_mem(0x1, 0, 0x1d, func_390);
    sv_set_mem(0x1, 0, 0x1e, func_391);
    sv_set_mem(0x1, 0, 0x1f, func_361);
    sv_set_mem(0x1, 0, 0x20, func_362);
    sv_set_mem(0x1, 0, 0x21, func_363);
    sv_set_mem(0x1, 0, 0x22, func_365);
    sv_set_mem(0x1, 0, 0x23, func_349);
    sv_set_mem(0x1, 0, 0x24, func_353);
    sv_set_mem(0x1, 0, 0x59, func_392);
    sv_set_mem(0x1, 0, 0x5a, func_393);
    sv_set_mem(0x1, 0, 0x5b, func_394);
    sv_set_mem(0x1, 0, 0x5c, func_395);
    sv_set_mem(0x1, 0, 0x5d, func_396);
    sv_set_mem(0x1, 0, 0x5e, func_397);
    sv_set_mem(0x1, 0, 0x5f, func_841);
    sv_set_mem(0x1, 0, 0x60, func_846);
    sv_set_mem(0x1, 0, 0x61, func_850);
    sv_set_mem(0x1, 0, 0x62, func_854);
    sv_set_mem(0x1, 0, 0x63, func_833);
    sv_set_mem(0x1, 0, 0x64, func_1697);
    sv_set_mem(0x1, 0, 0x65, func_1701);
    sv_set_mem(0x1, 0, 0x66, func_1705);
    sv_set_mem(0x1, 0, 0x67, func_1710);
    sv_set_mem(0x1, 0, 0x68, func_1715);
    sv_set_mem(0x1, 0, 0x71, func_671);
    sv_set_mem(0x1, 0, 0x69, func_633);
    sv_set_mem(0x1, 0, 0x6a, func_634);
    sv_set_mem(0x1, 0, 0x6b, func_643);
    sv_set_mem(0x1, 0, 0x6c, func_648);
    sv_set_mem(0x1, 0, 0x6d, func_653);
    sv_set_mem(0x1, 0, 0x6e, func_658);
    sv_set_mem(0x1, 0, 0x6f, func_662);
    sv_set_mem(0x1, 0, 0x70, func_666);
    sv_set_mem(0x1, 0, 0x72, func_147);
    sv_set_mem(0x1, 0, 0x73, func_148);
    sv_set_mem(0x1, 0, 0x74, func_149);
    sv_set_mem(0x1, 0, 0x75, func_150);
    sv_set_mem(0x1, 0, 0x76, func_151);
    sv_set_mem(0x1, 0, 0x77, func_152);
    sv_set_mem(0x1, 0, 0x78, func_153);
    sv_set_mem(0x1, 0, 0x79, func_154);
    sv_set_mem(0x1, 0, 0x7a, func_155);
    sv_set_mem(0x1, 0, 0x108, func_156);
    sv_set_mem(0x1, 0, 0x7b, func_1019);
    sv_set_mem(0x1, 0, 0x7c, func_1019);
    sv_set_mem(0x1, 0, 0x7d, func_157);
    sv_set_mem(0x1, 0, 0x7e, func_482);
    sv_set_mem(0x1, 0, 0x7f, func_483);
    sv_set_mem(0x1, 0, 0x80, func_484);
    sv_set_mem(0x1, 0, 0x81, func_485);
    sv_set_mem(0x1, 0, 0x82, func_486);
    sv_set_mem(0x1, 0, 0x83, func_1930);
    sv_set_mem(0x1, 0, 0x84, func_1934);
    sv_set_mem(0x1, 0, 0x85, func_1938);
    sv_set_mem(0x1, 0, 0x86, func_1943);
    sv_set_mem(0x1, 0, 0x87, func_1947);
    sv_set_mem(0x1, 0, 0x88, func_1951);
    sv_set_mem(0x1, 0, 0x89, func_1955);
    sv_set_mem(0x1, 0, 0x25, func_244);
    sv_set_mem(0x1, 0, 0x26, func_335);
    sv_set_mem(0x1, 0, 0x27, func_245);
    sv_set_mem(0x1, 0, 0x28, func_246);
    sv_set_mem(0x1, 0, 0x29, func_247);
    sv_set_mem(0x1, 0, 0x2a, func_248);
    sv_set_mem(0x1, 0, 0x2b, func_249);
    sv_set_mem(0x1, 0, 0x2c, func_250);
    sv_set_mem(0x1, 0, 0x2d, func_252);
    sv_set_mem(0x1, 0, 0x31, func_253);
    sv_set_mem(0x1, 0, 0x32, func_254);
    sv_set_mem(0x1, 0, 0x33, func_256);
    sv_set_mem(0x1, 0, 0x2e, func_257);
    sv_set_mem(0x1, 0, 0x2f, func_258);
    sv_set_mem(0x1, 0, 0x30, func_260);
    sv_set_mem(0x1, 0, 0x34, func_261);
    sv_set_mem(0x1, 0, 0x35, func_1032);
    sv_set_mem(0x1, 0, 0x36, func_1037);
    sv_set_mem(0x1, 0, 0x37, func_1044);
    sv_set_mem(0x1, 0, 0x38, func_1050);
    sv_set_mem(0x1, 0, 0x39, func_1054);
    sv_set_mem(0x1, 0, 0x3a, func_1059);
    sv_set_mem(0x1, 0, 0x3b, func_1066);
    sv_set_mem(0x1, 0, 0x3c, func_1071);
    sv_set_mem(0x1, 0, 0x3d, func_1076);
    sv_set_mem(0x1, 0, 0x3e, func_1080);
    sv_set_mem(0x1, 0, 0x3f, func_1087);
    sv_set_mem(0x1, 0, 0x40, func_1099);
    sv_set_mem(0x1, 0, 0x41, func_1110);
    sv_set_mem(0x1, 0, 0x42, func_1119);
    sv_set_mem(0x1, 0, 0x43, func_1124);
    sv_set_mem(0x1, 0, 0x44, func_1128);
    sv_set_mem(0x1, 0, 0x45, func_783);
    sv_set_mem(0x1, 0, 0x46, func_788);
    sv_set_mem(0x1, 0, 0x47, func_793);
    sv_set_mem(0x1, 0, 0x48, func_794);
    sv_set_mem(0x1, 0, 0x49, func_900);
    sv_set_mem(0x1, 0, 0x4a, func_908);
    sv_set_mem(0x1, 0, 0x4b, func_913);
    sv_set_mem(0x1, 0, 0x4c, func_795);
    sv_set_mem(0x1, 0, 0x4d, func_920);
    sv_set_mem(0x1, 0, 0x4e, func_924);
    sv_set_mem(0x1, 0, 0x4f, func_928);
    sv_set_mem(0x1, 0, 0x50, func_932);
    sv_set_mem(0x1, 0, 0x51, func_936);
    sv_set_mem(0x1, 0, 0x52, func_973);
    sv_set_mem(0x1, 0, 0x53, func_969);
    sv_set_mem(0x1, 0, 0x54, func_940);
    sv_set_mem(0x1, 0, 0x55, func_944);
    sv_set_mem(0x1, 0, 0x56, func_948);
    sv_set_mem(0x1, 0, 0x57, func_952);
    sv_set_mem(0x1, 0, 0x58, func_956);
    sv_set_mem(0x1, 0, 0xb3, func_1143);
    sv_set_mem(0x1, 0, 0xb4, func_1151);
    sv_set_mem(0x1, 0, 0xb5, func_1156);
    sv_set_mem(0x1, 0, 0xb6, func_1160);
    sv_set_mem(0x1, 0, 0xb7, func_1165);
    sv_set_mem(0x1, 0, 0x8a, func_1172);
    sv_set_mem(0x1, 0, 0x8b, func_1193);
    sv_set_mem(0x1, 0, 0x8c, func_1177);
    sv_set_mem(0x1, 0, 0x8d, func_1188);
    sv_set_mem(0x1, 0, 0x8e, func_1207);
    sv_set_mem(0x1, 0, 0x8f, func_1198);
    sv_set_mem(0x1, 0, 0x90, func_1202);
    sv_set_mem(0x1, 0, 0x91, func_1212);
    sv_set_mem(0x1, 0, 0x92, func_1726);
    sv_set_mem(0x1, 0, 0x93, func_1733);
    sv_set_mem(0x1, 0, 0x94, func_1739);
    sv_set_mem(0x1, 0, 0x96, func_1745);
    sv_set_mem(0x1, 0, 0x95, func_1751);
    sv_set_mem(0x1, 0, 0x97, func_1756);
    sv_set_mem(0x1, 0, 0x98, func_1326);
    sv_set_mem(0x1, 0, 0x99, func_1330);
    sv_set_mem(0x1, 0, 0x9a, func_1334);
    sv_set_mem(0x1, 0, 0x9b, func_1338);
    sv_set_mem(0x1, 0, 0x9c, func_1342);
    sv_set_mem(0x1, 0, 0x9d, func_1346);
    sv_set_mem(0x1, 0, 0x9e, func_1350);
    sv_set_mem(0x1, 0, 0x9f, func_1360);
    sv_set_mem(0x1, 0, 0xa0, func_1365);
    sv_set_mem(0x1, 0, 0xa1, func_1354);
    sv_set_mem(0x1, 0, 0xa2, func_1369);
    sv_set_mem(0x1, 0, 0xa3, func_568);
    sv_set_mem(0x1, 0, 0xa4, func_572);
    sv_set_mem(0x1, 0, 0xa5, func_577);
    sv_set_mem(0x1, 0, 0xa6, func_1216);
    sv_set_mem(0x1, 0, 0xc5, func_822);
    sv_set_mem(0x1, 0, 0xc6, func_828);
    sv_set_mem(0x1, 0, 0xd0, func_1220);
    sv_set_mem(0x1, 0, 0xd1, func_1224);
    sv_set_mem(0x1, 0, 0xd2, func_1228);
    sv_set_mem(0x1, 0, 0xd3, func_1251);
    sv_set_mem(0x1, 0, 0xd4, func_1255);
    sv_set_mem(0x1, 0, 0xd5, func_1259);
    sv_set_mem(0x1, 0, 0xd6, func_1264);
    sv_set_mem(0x1, 0, 0xd7, func_1268);
    sv_set_mem(0x1, 0, 0xd8, func_1272);
    sv_set_mem(0x1, 0, 0xd9, func_1276);
    sv_set_mem(0x1, 0, 0xda, func_1010);
    sv_set_mem(0x1, 0, 0xdb, func_837);
    sv_set_mem(0x1, 0, 0xdd, func_1285);
    sv_set_mem(0x1, 0, 0xde, func_1289);
    sv_set_mem(0x1, 0, 0xb1, func_211);
    sv_set_mem(0x1, 0, 0xb2, func_227);
    sv_set_mem(0x1, 0, 0x14c, func_212);
    sv_set_mem(0x1, 0, 0x14f, func_2157);
    sv_set_mem(0x1, 0, 0xb8, func_1583);
    sv_set_mem(0x1, 0, 0xb9, func_1594);
    sv_set_mem(0x1, 0, 0xba, func_1605);
    sv_set_mem(0x1, 0, 0xbb, func_1616);
    sv_set_mem(0x1, 0, 0xbc, func_1627);
    sv_set_mem(0x1, 0, 0xe9, func_1638);
    sv_set_mem(0x1, 0, 0xea, func_1643);
    sv_set_mem(0x1, 0, 0xeb, func_1648);
    sv_set_mem(0x1, 0, 0xbd, func_1653);
    sv_set_mem(0x1, 0, 0xbe, func_1659);
    sv_set_mem(0x1, 0, 0x109, func_1666);
    sv_set_mem(0x1, 0, 0xdf, func_1867);
    sv_set_mem(0x1, 0, 0xe3, func_1871);
    sv_set_mem(0x1, 0, 0xe2, func_1875);
    sv_set_mem(0x1, 0, 0xe5, func_1879);
    sv_set_mem(0x1, 0, 0xe4, func_1883);
    sv_set_mem(0x1, 0, 0xe0, func_1887);
    sv_set_mem(0x1, 0, 0xc7, func_1809);
    sv_set_mem(0x1, 0, 0xc8, func_1801);
    sv_set_mem(0x1, 0, 0xc9, func_1816);
    sv_set_mem(0x1, 0, 0xca, func_1824);
    sv_set_mem(0x1, 0, 0xcb, func_1827);
    sv_set_mem(0x1, 0, 0x14d, func_686);
    sv_set_mem(0x1, 0, 0x14e, func_692);
    sv_set_mem(0x1, 0, 0xe6, func_1898);
    sv_set_mem(0x1, 0, 0xe7, func_1891);
    sv_set_mem(0x1, 0, 0xe8, func_1895);
    sv_set_mem(0x1, 0, 0xec, func_1901);
    sv_set_mem(0x1, 0, 0xed, func_1908);
    sv_set_mem(0x1, 0, 0xef, func_1916);
    sv_set_mem(0x1, 0, 0xf0, func_1920);
    sv_set_mem(0x1, 0, 0xee, func_1912);
    sv_set_mem(0x1, 0, 0xf1, func_123);
    sv_set_mem(0x1, 0, 0xf2, func_128);
    sv_set_mem(0x1, 0, 0xf3, func_132);
    sv_set_mem(0x1, 0, 0xf4, func_138);
    sv_set_mem(0x1, 0, 0xf5, func_142);
    sv_set_mem(0x1, 0, 0xf7, func_1968);
    sv_set_mem(0x1, 0, 0xf8, func_1233);
    sv_set_mem(0x1, 0, 0x10e, func_1237);
    sv_set_mem(0x1, 0, 0xf9, func_1293);
    sv_set_mem(0x1, 0, 0xfe, func_1507);
    sv_set_mem(0x1, 0, 0xfb, func_1513);
    sv_set_mem(0x1, 0, 0xfc, func_1518);
    sv_set_mem(0x1, 0, 0xfd, func_1523);
    sv_set_mem(0x1, 0, 0xff, func_1977);
    sv_set_mem(0x1, 0, 0x100, func_1297);
    sv_set_mem(0x1, 0, 0x114, func_1301);
    sv_set_mem(0x1, 0, 0x101, func_1972);
    sv_set_mem(0x1, 0, 0x10a, func_1305);
    sv_set_mem(0x1, 0, 0x10b, func_1309);
    sv_set_mem(0x1, 0, 0x10c, func_1313);
    sv_set_mem(0x1, 0, 0x10d, func_1319);
    if (!sys_7(0xd))
    {
        sv_set_mem(0x1, 0, 0x14b, func_1959);
    }
    sv_set_mem(0x1, 0, 0xa7, func_2104);
    sv_set_mem(0x1, 0, 0xa8, func_2108);
    sv_set_mem(0x1, 0, 0xa9, func_2112);
    sv_set_mem(0x1, 0, 0xaa, func_2116);
    sv_set_mem(0x1, 0, 0xab, func_2120);
    sv_set_mem(0x1, 0, 0xac, func_2124);
    sv_set_mem(0x1, 0, 0xad, func_2128);
    sv_set_mem(0x1, 0, 0xae, func_2132);
    sv_set_mem(0x1, 0, 0xaf, func_2137);
    sv_set_mem(0x1, 0, 0xb0, func_2142);
    sv_set_mem(0x1, 0, 0x104, func_1991);
    sv_set_mem(0x1, 0, 0x105, func_1996);
    sv_set_mem(0x1, 0, 0x106, func_2001);
    sv_set_mem(0x1, 0, 0x107, func_2006);
    sv_set_mem(0x1, 0, 0x10f, func_2010);
    sv_set_mem(0x1, 0, 0x128, func_2173);
    sv_set_mem(0x1, 0, 0x129, func_2180);
    sv_set_mem(0x1, 0, 0x12a, func_2186);
    sv_set_mem(0x1, 0, 0x12b, func_2173);
    sv_set_mem(0x1, 0, 0x12c, func_2180);
    sv_set_mem(0x1, 0, 0x12d, func_2186);
    sv_set_mem(0x1, 0, 0x12e, func_2173);
    sv_set_mem(0x1, 0, 0x12f, func_2180);
    sv_set_mem(0x1, 0, 0x130, func_2186);
    sv_set_mem(0x1, 0, 0x131, func_2173);
    sv_set_mem(0x1, 0, 0x132, func_2192);
    sv_set_mem(0x1, 0, 0x133, func_2193);
    sv_set_mem(0x1, 0, 0x134, func_2173);
    sv_set_mem(0x1, 0, 0x135, func_2180);
    sv_set_mem(0x1, 0, 0x136, func_2186);
    sv_set_mem(0x1, 0, 0x124, func_2213);
    sv_set_mem(0x1, 0, 0x125, func_2217);
    sv_set_mem(0x1, 0, 0x122, func_2190);
    sv_set_mem(0x1, 0, 0x137, func_2150);
    sv_set_mem(0x1, 0, 0x138, func_2153);
    sv_set_mem(0x1, 0, 0x139, func_2230);
    sv_set_mem(0x1, 0, 0x13a, func_793);
    sv_set_mem(0x1, 0, 0x13d, func_788);
    sv_set_mem(0x1, 0, 0x13b, func_2191);
    sv_set_mem(0x1, 0, 0x13c, func_2174);
    sv_set_mem(0x1, 0, 0x13e, func_2175);
    sv_set_mem(0x1, 0, 0x13f, func_2180);
    sv_set_mem(0x1, 0, 0x140, func_2186);
    sv_set_mem(0x1, 0, 0x147, func_2235);
    sv_set_mem(0x1, 0, 0x110, func_2015);
    sv_set_mem(0x1, 0, 0x111, func_2020);
    sv_set_mem(0x1, 0, 0x112, func_2024);
    sv_set_mem(0x1, 0, 0x113, func_2028);
    sv_set_mem(0x1, 0, 0x118, func_2044);
    sv_set_mem(0x1, 0, 0x119, func_2049);
    sv_set_mem(0x1, 0, 0x11a, func_2053);
    sv_set_mem(0x1, 0, 0x115, func_2032);
    sv_set_mem(0x1, 0, 0x116, func_2036);
    sv_set_mem(0x1, 0, 0x117, func_2040);
    sv_set_mem(0x1, 0, 0x11c, func_2057);
    sv_set_mem(0x1, 0, 0x11d, func_2062);
    sv_set_mem(0x1, 0, 0x11e, func_2066);
    sv_set_mem(0x1, 0, 0x142, func_2070);
    sv_set_mem(0x1, 0, 0x143, func_2075);
    sv_set_mem(0x1, 0, 0x144, func_2079);
    sv_set_mem(0x1, 0, 0x145, func_2083);
    sv_set_mem(0x1, 0, 0x146, func_2087);
    sv_set_mem(0x1, 0, 0x148, func_2091);
    sv_set_mem(0x1, 0, 0x149, func_2096);
    sv_set_mem(0x1, 0, 0x14a, func_2100);
}

void func_114()
{
    sv_set_mem(0x1, 0x1, 0, func_672);
    sv_set_mem(0x1, 0x1, 0x1, func_709);
    sv_set_mem(0x1, 0x1, 0x2, func_711);
    sv_set_mem(0x1, 0x1, 0xa, func_487);
    sv_set_mem(0x1, 0x1, 0xb, func_492);
    sv_set_mem(0x1, 0x1, 0xc, func_495);
    sv_set_mem(0x1, 0x1, 0xd, func_498);
    sv_set_mem(0x1, 0x1, 0xe, func_501);
    sv_set_mem(0x1, 0x1, 0xf, func_504);
    sv_set_mem(0x1, 0x1, 0x10, func_979);
    sv_set_mem(0x1, 0x1, 0x16, func_507);
    sv_set_mem(0x1, 0x1, 0x17, func_513);
    sv_set_mem(0x1, 0x1, 0x18, func_517);
    sv_set_mem(0x1, 0x1, 0x19, func_981);
    sv_set_mem(0x1, 0x1, 0x3, func_713);
    sv_set_mem(0x1, 0x1, 0x4, func_716);
    sv_set_mem(0x1, 0x1, 0x5, func_720);
    sv_set_mem(0x1, 0x1, 0x6, func_723);
    sv_set_mem(0x1, 0x1, 0x7, func_725);
    sv_set_mem(0x1, 0x1, 0x8, func_727);
    sv_set_mem(0x1, 0x1, 0x9, func_731);
    sv_set_mem(0x1, 0x1, 0x11, func_598);
    sv_set_mem(0x1, 0x1, 0x12, func_601);
    sv_set_mem(0x1, 0x1, 0x13, func_605);
    sv_set_mem(0x1, 0x1, 0x14, func_607);
    sv_set_mem(0x1, 0x1, 0x15, func_609);
    sv_set_mem(0x1, 0x1, 0x1b, func_399);
    sv_set_mem(0x1, 0x1, 0x1c, func_405);
    sv_set_mem(0x1, 0x1, 0x1d, func_409);
    sv_set_mem(0x1, 0x1, 0x1e, func_412);
    sv_set_mem(0x1, 0x1, 0x1f, func_366);
    sv_set_mem(0x1, 0x1, 0x20, func_369);
    sv_set_mem(0x1, 0x1, 0x21, func_371);
    sv_set_mem(0x1, 0x1, 0x22, func_375);
    sv_set_mem(0x1, 0x1, 0x23, func_350);
    sv_set_mem(0x1, 0x1, 0x24, func_354);
    sv_set_mem(0x1, 0x1, 0x59, func_416);
    sv_set_mem(0x1, 0x1, 0x5a, func_418);
    sv_set_mem(0x1, 0x1, 0x5b, func_420);
    sv_set_mem(0x1, 0x1, 0x5c, func_422);
    sv_set_mem(0x1, 0x1, 0x5d, func_425);
    sv_set_mem(0x1, 0x1, 0x5e, func_427);
    sv_set_mem(0x1, 0x1, 0x5f, func_842);
    sv_set_mem(0x1, 0x1, 0x60, func_847);
    sv_set_mem(0x1, 0x1, 0x61, func_851);
    sv_set_mem(0x1, 0x1, 0x62, func_855);
    sv_set_mem(0x1, 0x1, 0x63, func_834);
    sv_set_mem(0x1, 0x1, 0x64, func_1698);
    sv_set_mem(0x1, 0x1, 0x65, func_1702);
    sv_set_mem(0x1, 0x1, 0x66, func_1706);
    sv_set_mem(0x1, 0x1, 0x67, func_1711);
    sv_set_mem(0x1, 0x1, 0x68, func_1716);
    sv_set_mem(0x1, 0x1, 0x71, func_674);
    sv_set_mem(0x1, 0x1, 0x69, func_635);
    sv_set_mem(0x1, 0x1, 0x6a, func_637);
    sv_set_mem(0x1, 0x1, 0x6b, func_644);
    sv_set_mem(0x1, 0x1, 0x6c, func_649);
    sv_set_mem(0x1, 0x1, 0x6d, func_654);
    sv_set_mem(0x1, 0x1, 0x6e, func_659);
    sv_set_mem(0x1, 0x1, 0x6f, func_663);
    sv_set_mem(0x1, 0x1, 0x70, func_667);
    sv_set_mem(0x1, 0x1, 0x72, func_158);
    sv_set_mem(0x1, 0x1, 0x73, func_161);
    sv_set_mem(0x1, 0x1, 0x74, func_165);
    sv_set_mem(0x1, 0x1, 0x75, func_167);
    sv_set_mem(0x1, 0x1, 0x76, func_169);
    sv_set_mem(0x1, 0x1, 0x77, func_171);
    sv_set_mem(0x1, 0x1, 0x78, func_173);
    sv_set_mem(0x1, 0x1, 0x79, func_175);
    sv_set_mem(0x1, 0x1, 0x7a, func_177);
    sv_set_mem(0x1, 0x1, 0x108, func_180);
    sv_set_mem(0x1, 0x1, 0x7b, func_1022);
    sv_set_mem(0x1, 0x1, 0x7c, func_1023);
    sv_set_mem(0x1, 0x1, 0x7d, func_183);
    sv_set_mem(0x1, 0x1, 0x7e, func_521);
    sv_set_mem(0x1, 0x1, 0x7f, func_523);
    sv_set_mem(0x1, 0x1, 0x80, func_525);
    sv_set_mem(0x1, 0x1, 0x81, func_527);
    sv_set_mem(0x1, 0x1, 0x82, func_529);
    sv_set_mem(0x1, 0x1, 0x83, func_1931);
    sv_set_mem(0x1, 0x1, 0x84, func_1935);
    sv_set_mem(0x1, 0x1, 0x85, func_1939);
    sv_set_mem(0x1, 0x1, 0x86, func_1944);
    sv_set_mem(0x1, 0x1, 0x87, func_1948);
    sv_set_mem(0x1, 0x1, 0x88, func_1952);
    sv_set_mem(0x1, 0x1, 0x89, func_1956);
    sv_set_mem(0x1, 0x1, 0x25, func_263);
    sv_set_mem(0x1, 0x1, 0x26, func_336);
    sv_set_mem(0x1, 0x1, 0x27, func_272);
    sv_set_mem(0x1, 0x1, 0x28, func_275);
    sv_set_mem(0x1, 0x1, 0x29, func_278);
    sv_set_mem(0x1, 0x1, 0x2a, func_281);
    sv_set_mem(0x1, 0x1, 0x2b, func_286);
    sv_set_mem(0x1, 0x1, 0x2c, func_288);
    sv_set_mem(0x1, 0x1, 0x2d, func_290);
    sv_set_mem(0x1, 0x1, 0x31, func_295);
    sv_set_mem(0x1, 0x1, 0x32, func_298);
    sv_set_mem(0x1, 0x1, 0x33, func_301);
    sv_set_mem(0x1, 0x1, 0x2e, func_303);
    sv_set_mem(0x1, 0x1, 0x2f, func_305);
    sv_set_mem(0x1, 0x1, 0x30, func_307);
    sv_set_mem(0x1, 0x1, 0x34, func_315);
    sv_set_mem(0x1, 0x1, 0x35, func_1034);
    sv_set_mem(0x1, 0x1, 0x36, func_1039);
    sv_set_mem(0x1, 0x1, 0x37, func_1046);
    sv_set_mem(0x1, 0x1, 0x38, func_1051);
    sv_set_mem(0x1, 0x1, 0x39, func_1056);
    sv_set_mem(0x1, 0x1, 0x3a, func_1061);
    sv_set_mem(0x1, 0x1, 0x3b, func_1067);
    sv_set_mem(0x1, 0x1, 0x3c, func_1073);
    sv_set_mem(0x1, 0x1, 0x3d, func_1077);
    sv_set_mem(0x1, 0x1, 0x3e, func_1082);
    sv_set_mem(0x1, 0x1, 0x3f, func_1091);
    sv_set_mem(0x1, 0x1, 0x40, func_1101);
    sv_set_mem(0x1, 0x1, 0x41, func_1112);
    sv_set_mem(0x1, 0x1, 0x42, func_1121);
    sv_set_mem(0x1, 0x1, 0x43, func_1125);
    sv_set_mem(0x1, 0x1, 0x44, func_1130);
    sv_set_mem(0x1, 0x1, 0x45, func_784);
    sv_set_mem(0x1, 0x1, 0x46, func_789);
    sv_set_mem(0x1, 0x1, 0x47, func_798);
    sv_set_mem(0x1, 0x1, 0x48, func_813);
    sv_set_mem(0x1, 0x1, 0x49, func_901);
    sv_set_mem(0x1, 0x1, 0x4a, func_910);
    sv_set_mem(0x1, 0x1, 0x4b, func_915);
    sv_set_mem(0x1, 0x1, 0x4c, func_815);
    sv_set_mem(0x1, 0x1, 0x4d, func_921);
    sv_set_mem(0x1, 0x1, 0x4e, func_925);
    sv_set_mem(0x1, 0x1, 0x4f, func_929);
    sv_set_mem(0x1, 0x1, 0x50, func_933);
    sv_set_mem(0x1, 0x1, 0x51, func_937);
    sv_set_mem(0x1, 0x1, 0x52, func_974);
    sv_set_mem(0x1, 0x1, 0x53, func_970);
    sv_set_mem(0x1, 0x1, 0x54, func_941);
    sv_set_mem(0x1, 0x1, 0x55, func_945);
    sv_set_mem(0x1, 0x1, 0x56, func_949);
    sv_set_mem(0x1, 0x1, 0x57, func_953);
    sv_set_mem(0x1, 0x1, 0x58, func_957);
    sv_set_mem(0x1, 0x1, 0xb3, func_1145);
    sv_set_mem(0x1, 0x1, 0xb4, func_1152);
    sv_set_mem(0x1, 0x1, 0xb5, func_1157);
    sv_set_mem(0x1, 0x1, 0xb6, func_1161);
    sv_set_mem(0x1, 0x1, 0xb7, func_1167);
    sv_set_mem(0x1, 0x1, 0x8a, func_1173);
    sv_set_mem(0x1, 0x1, 0x8b, func_1194);
    sv_set_mem(0x1, 0x1, 0x8c, func_1182);
    sv_set_mem(0x1, 0x1, 0x8d, func_1189);
    sv_set_mem(0x1, 0x1, 0x8e, func_1208);
    sv_set_mem(0x1, 0x1, 0x8f, func_1199);
    sv_set_mem(0x1, 0x1, 0x90, func_1204);
    sv_set_mem(0x1, 0x1, 0x91, func_1213);
    sv_set_mem(0x1, 0x1, 0x92, func_1729);
    sv_set_mem(0x1, 0x1, 0x93, func_1735);
    sv_set_mem(0x1, 0x1, 0x94, func_1741);
    sv_set_mem(0x1, 0x1, 0x96, func_1747);
    sv_set_mem(0x1, 0x1, 0x95, func_1752);
    sv_set_mem(0x1, 0x1, 0x97, func_1758);
    sv_set_mem(0x1, 0x1, 0x98, func_1327);
    sv_set_mem(0x1, 0x1, 0x99, func_1331);
    sv_set_mem(0x1, 0x1, 0x9a, func_1335);
    sv_set_mem(0x1, 0x1, 0x9b, func_1339);
    sv_set_mem(0x1, 0x1, 0x9c, func_1343);
    sv_set_mem(0x1, 0x1, 0x9d, func_1347);
    sv_set_mem(0x1, 0x1, 0x9e, func_1351);
    sv_set_mem(0x1, 0x1, 0x9f, func_1361);
    sv_set_mem(0x1, 0x1, 0xa0, func_1366);
    sv_set_mem(0x1, 0x1, 0xa1, func_1357);
    sv_set_mem(0x1, 0x1, 0xa2, func_1370);
    sv_set_mem(0x1, 0x1, 0xa3, func_569);
    sv_set_mem(0x1, 0x1, 0xa4, func_573);
    sv_set_mem(0x1, 0x1, 0xa5, func_578);
    sv_set_mem(0x1, 0x1, 0xa6, func_1217);
    sv_set_mem(0x1, 0x1, 0xc5, func_823);
    sv_set_mem(0x1, 0x1, 0xc6, func_829);
    sv_set_mem(0x1, 0x1, 0xd0, func_1221);
    sv_set_mem(0x1, 0x1, 0xd1, func_1225);
    sv_set_mem(0x1, 0x1, 0xd2, func_1229);
    sv_set_mem(0x1, 0x1, 0xd3, func_1252);
    sv_set_mem(0x1, 0x1, 0xd4, func_1256);
    sv_set_mem(0x1, 0x1, 0xd5, func_1260);
    sv_set_mem(0x1, 0x1, 0xd6, func_1265);
    sv_set_mem(0x1, 0x1, 0xd7, func_1269);
    sv_set_mem(0x1, 0x1, 0xd8, func_1273);
    sv_set_mem(0x1, 0x1, 0xd9, func_1277);
    sv_set_mem(0x1, 0x1, 0xda, func_1012);
    sv_set_mem(0x1, 0x1, 0xdb, func_838);
    sv_set_mem(0x1, 0x1, 0xdd, func_1286);
    sv_set_mem(0x1, 0x1, 0xde, func_1290);
    sv_set_mem(0x1, 0x1, 0xb1, func_213);
    sv_set_mem(0x1, 0x1, 0xb2, func_228);
    sv_set_mem(0x1, 0x1, 0x14c, func_216);
    sv_set_mem(0x1, 0x1, 0x14f, func_2158);
    sv_set_mem(0x1, 0x1, 0xb8, func_1584);
    sv_set_mem(0x1, 0x1, 0xb9, func_1595);
    sv_set_mem(0x1, 0x1, 0xba, func_1606);
    sv_set_mem(0x1, 0x1, 0xbb, func_1617);
    sv_set_mem(0x1, 0x1, 0xbc, func_1628);
    sv_set_mem(0x1, 0x1, 0xe9, func_1639);
    sv_set_mem(0x1, 0x1, 0xea, func_1644);
    sv_set_mem(0x1, 0x1, 0xeb, func_1649);
    sv_set_mem(0x1, 0x1, 0xbd, func_1654);
    sv_set_mem(0x1, 0x1, 0xbe, func_1660);
    sv_set_mem(0x1, 0x1, 0x109, func_1667);
    sv_set_mem(0x1, 0x1, 0xdf, func_1868);
    sv_set_mem(0x1, 0x1, 0xe3, func_1872);
    sv_set_mem(0x1, 0x1, 0xe2, func_1876);
    sv_set_mem(0x1, 0x1, 0xe5, func_1880);
    sv_set_mem(0x1, 0x1, 0xe4, func_1884);
    sv_set_mem(0x1, 0x1, 0xe0, func_1888);
    sv_set_mem(0x1, 0x1, 0xc7, func_1810);
    sv_set_mem(0x1, 0x1, 0xc8, func_1802);
    sv_set_mem(0x1, 0x1, 0xc9, func_1817);
    sv_set_mem(0x1, 0x1, 0xca, func_1825);
    sv_set_mem(0x1, 0x1, 0xcb, func_1828);
    sv_set_mem(0x1, 0x1, 0x14d, func_687);
    sv_set_mem(0x1, 0x1, 0x14e, func_693);
    sv_set_mem(0x1, 0x1, 0xe6, func_1899);
    sv_set_mem(0x1, 0x1, 0xe7, func_1892);
    sv_set_mem(0x1, 0x1, 0xe8, func_1896);
    sv_set_mem(0x1, 0x1, 0xec, func_1902);
    sv_set_mem(0x1, 0x1, 0xed, func_1909);
    sv_set_mem(0x1, 0x1, 0xef, func_1917);
    sv_set_mem(0x1, 0x1, 0xf0, func_1921);
    sv_set_mem(0x1, 0x1, 0xee, func_1913);
    sv_set_mem(0x1, 0x1, 0xf1, func_125);
    sv_set_mem(0x1, 0x1, 0xf2, func_129);
    sv_set_mem(0x1, 0x1, 0xf3, func_134);
    sv_set_mem(0x1, 0x1, 0xf4, func_139);
    sv_set_mem(0x1, 0x1, 0xf5, func_144);
    sv_set_mem(0x1, 0x1, 0xf7, func_1969);
    sv_set_mem(0x1, 0x1, 0xf8, func_1234);
    sv_set_mem(0x1, 0x1, 0x10e, func_1238);
    sv_set_mem(0x1, 0x1, 0xf9, func_1294);
    sv_set_mem(0x1, 0x1, 0xfe, func_1508);
    sv_set_mem(0x1, 0x1, 0xfb, func_1514);
    sv_set_mem(0x1, 0x1, 0xfc, func_1519);
    sv_set_mem(0x1, 0x1, 0xfd, func_1524);
    sv_set_mem(0x1, 0x1, 0xff, func_1979);
    sv_set_mem(0x1, 0x1, 0x100, func_1298);
    sv_set_mem(0x1, 0x1, 0x114, func_1302);
    sv_set_mem(0x1, 0x1, 0x101, func_1973);
    sv_set_mem(0x1, 0x1, 0x10a, func_1306);
    sv_set_mem(0x1, 0x1, 0x10b, func_1310);
    sv_set_mem(0x1, 0x1, 0x10c, func_1314);
    sv_set_mem(0x1, 0x1, 0x10d, func_1320);
    if (!sys_7(0xd))
    {
        sv_set_mem(0x1, 0x1, 0x14b, func_1960);
    }
    sv_set_mem(0x1, 0x1, 0xa7, func_2105);
    sv_set_mem(0x1, 0x1, 0xa8, func_2109);
    sv_set_mem(0x1, 0x1, 0xa9, func_2113);
    sv_set_mem(0x1, 0x1, 0xaa, func_2117);
    sv_set_mem(0x1, 0x1, 0xab, func_2121);
    sv_set_mem(0x1, 0x1, 0xac, func_2125);
    sv_set_mem(0x1, 0x1, 0xad, func_2129);
    sv_set_mem(0x1, 0x1, 0xae, func_2133);
    sv_set_mem(0x1, 0x1, 0xaf, func_2138);
    sv_set_mem(0x1, 0x1, 0xb0, func_2143);
    sv_set_mem(0x1, 0x1, 0x104, func_1992);
    sv_set_mem(0x1, 0x1, 0x105, func_1997);
    sv_set_mem(0x1, 0x1, 0x106, func_2002);
    sv_set_mem(0x1, 0x1, 0x107, func_2007);
    sv_set_mem(0x1, 0x1, 0x10f, func_2011);
    sv_set_mem(0x1, 0x1, 0x128, func_2176);
    sv_set_mem(0x1, 0x1, 0x129, func_2181);
    sv_set_mem(0x1, 0x1, 0x12a, func_2187);
    sv_set_mem(0x1, 0x1, 0x12b, func_2176);
    sv_set_mem(0x1, 0x1, 0x12c, func_2181);
    sv_set_mem(0x1, 0x1, 0x12d, func_2187);
    sv_set_mem(0x1, 0x1, 0x12e, func_2176);
    sv_set_mem(0x1, 0x1, 0x12f, func_2181);
    sv_set_mem(0x1, 0x1, 0x130, func_2187);
    sv_set_mem(0x1, 0x1, 0x131, func_2176);
    sv_set_mem(0x1, 0x1, 0x132, func_2181);
    sv_set_mem(0x1, 0x1, 0x133, func_2187);
    sv_set_mem(0x1, 0x1, 0x134, func_2176);
    sv_set_mem(0x1, 0x1, 0x135, func_2181);
    sv_set_mem(0x1, 0x1, 0x136, func_2187);
    sv_set_mem(0x1, 0x1, 0x124, func_2214);
    sv_set_mem(0x1, 0x1, 0x125, func_2218);
    sv_set_mem(0x1, 0x1, 0x137, func_2151);
    sv_set_mem(0x1, 0x1, 0x138, func_2154);
    sv_set_mem(0x1, 0x1, 0x139, func_2231);
    sv_set_mem(0x1, 0x1, 0x13a, func_798);
    sv_set_mem(0x1, 0x1, 0x13d, func_789);
    sv_set_mem(0x1, 0x1, 0x13b, func_2181);
    sv_set_mem(0x1, 0x1, 0x13c, func_2176);
    sv_set_mem(0x1, 0x1, 0x13e, func_2177);
    sv_set_mem(0x1, 0x1, 0x13f, func_2182);
    sv_set_mem(0x1, 0x1, 0x140, func_2187);
    sv_set_mem(0x1, 0x1, 0x147, func_2236);
    sv_set_mem(0x1, 0x1, 0x110, func_2016);
    sv_set_mem(0x1, 0x1, 0x111, func_2021);
    sv_set_mem(0x1, 0x1, 0x112, func_2025);
    sv_set_mem(0x1, 0x1, 0x113, func_2029);
    sv_set_mem(0x1, 0x1, 0x118, func_2045);
    sv_set_mem(0x1, 0x1, 0x119, func_2050);
    sv_set_mem(0x1, 0x1, 0x11a, func_2054);
    sv_set_mem(0x1, 0x1, 0x115, func_2033);
    sv_set_mem(0x1, 0x1, 0x116, func_2037);
    sv_set_mem(0x1, 0x1, 0x117, func_2041);
    sv_set_mem(0x1, 0x1, 0x11c, func_2058);
    sv_set_mem(0x1, 0x1, 0x11d, func_2063);
    sv_set_mem(0x1, 0x1, 0x11e, func_2067);
    sv_set_mem(0x1, 0x1, 0x142, func_2071);
    sv_set_mem(0x1, 0x1, 0x143, func_2076);
    sv_set_mem(0x1, 0x1, 0x144, func_2080);
    sv_set_mem(0x1, 0x1, 0x145, func_2084);
    sv_set_mem(0x1, 0x1, 0x146, func_2088);
    sv_set_mem(0x1, 0x1, 0x148, func_2092);
    sv_set_mem(0x1, 0x1, 0x149, func_2097);
    sv_set_mem(0x1, 0x1, 0x14a, func_2101);
}

void func_115()
{
    sv_set_mem(0x1, 0x2, 0, func_679);
    sv_set_mem(0x1, 0x2, 0x1, func_733);
    sv_set_mem(0x1, 0x2, 0x2, func_734);
    sv_set_mem(0x1, 0x2, 0xa, func_531);
    sv_set_mem(0x1, 0x2, 0xb, func_532);
    sv_set_mem(0x1, 0x2, 0xc, func_533);
    sv_set_mem(0x1, 0x2, 0xd, func_534);
    sv_set_mem(0x1, 0x2, 0xe, func_535);
    sv_set_mem(0x1, 0x2, 0xf, func_536);
    sv_set_mem(0x1, 0x2, 0x10, func_988);
    sv_set_mem(0x1, 0x2, 0x16, func_537);
    sv_set_mem(0x1, 0x2, 0x17, func_538);
    sv_set_mem(0x1, 0x2, 0x18, func_539);
    sv_set_mem(0x1, 0x2, 0x19, func_989);
    sv_set_mem(0x1, 0x2, 0x3, func_735);
    sv_set_mem(0x1, 0x2, 0x4, func_736);
    sv_set_mem(0x1, 0x2, 0x5, func_737);
    sv_set_mem(0x1, 0x2, 0x6, func_738);
    sv_set_mem(0x1, 0x2, 0x7, func_739);
    sv_set_mem(0x1, 0x2, 0x8, func_740);
    sv_set_mem(0x1, 0x2, 0x9, func_741);
    sv_set_mem(0x1, 0x2, 0x11, func_611);
    sv_set_mem(0x1, 0x2, 0x12, func_612);
    sv_set_mem(0x1, 0x2, 0x13, func_613);
    sv_set_mem(0x1, 0x2, 0x14, func_614);
    sv_set_mem(0x1, 0x2, 0x15, func_615);
    sv_set_mem(0x1, 0x2, 0x1b, func_429);
    sv_set_mem(0x1, 0x2, 0x1c, func_430);
    sv_set_mem(0x1, 0x2, 0x1d, func_431);
    sv_set_mem(0x1, 0x2, 0x1e, func_432);
    sv_set_mem(0x1, 0x2, 0x1f, func_380);
    sv_set_mem(0x1, 0x2, 0x20, func_381);
    sv_set_mem(0x1, 0x2, 0x21, func_382);
    sv_set_mem(0x1, 0x2, 0x22, func_384);
    sv_set_mem(0x1, 0x2, 0x23, func_352);
    sv_set_mem(0x1, 0x2, 0x24, func_356);
    sv_set_mem(0x1, 0x2, 0x59, func_433);
    sv_set_mem(0x1, 0x2, 0x5a, func_434);
    sv_set_mem(0x1, 0x2, 0x5b, func_435);
    sv_set_mem(0x1, 0x2, 0x5c, func_436);
    sv_set_mem(0x1, 0x2, 0x5d, func_437);
    sv_set_mem(0x1, 0x2, 0x5e, func_438);
    sv_set_mem(0x1, 0x2, 0x5f, func_844);
    sv_set_mem(0x1, 0x2, 0x60, func_849);
    sv_set_mem(0x1, 0x2, 0x61, func_853);
    sv_set_mem(0x1, 0x2, 0x62, func_857);
    sv_set_mem(0x1, 0x2, 0x63, func_836);
    sv_set_mem(0x1, 0x2, 0x64, func_1700);
    sv_set_mem(0x1, 0x2, 0x65, func_1704);
    sv_set_mem(0x1, 0x2, 0x66, func_1709);
    sv_set_mem(0x1, 0x2, 0x67, func_1714);
    sv_set_mem(0x1, 0x2, 0x68, func_1718);
    sv_set_mem(0x1, 0x2, 0x71, func_680);
    sv_set_mem(0x1, 0x2, 0x69, func_639);
    sv_set_mem(0x1, 0x2, 0x6a, func_640);
    sv_set_mem(0x1, 0x2, 0x6b, func_646);
    sv_set_mem(0x1, 0x2, 0x6c, func_652);
    sv_set_mem(0x1, 0x2, 0x6d, func_657);
    sv_set_mem(0x1, 0x2, 0x6e, func_661);
    sv_set_mem(0x1, 0x2, 0x6f, func_665);
    sv_set_mem(0x1, 0x2, 0x70, func_669);
    sv_set_mem(0x1, 0x2, 0x72, func_185);
    sv_set_mem(0x1, 0x2, 0x73, func_186);
    sv_set_mem(0x1, 0x2, 0x74, func_187);
    sv_set_mem(0x1, 0x2, 0x75, func_188);
    sv_set_mem(0x1, 0x2, 0x76, func_189);
    sv_set_mem(0x1, 0x2, 0x77, func_190);
    sv_set_mem(0x1, 0x2, 0x78, func_191);
    sv_set_mem(0x1, 0x2, 0x79, func_192);
    sv_set_mem(0x1, 0x2, 0x7a, func_193);
    sv_set_mem(0x1, 0x2, 0x108, func_194);
    sv_set_mem(0x1, 0x2, 0x7b, func_1026);
    sv_set_mem(0x1, 0x2, 0x7c, func_1026);
    sv_set_mem(0x1, 0x2, 0x7d, func_195);
    sv_set_mem(0x1, 0x2, 0x7e, func_541);
    sv_set_mem(0x1, 0x2, 0x7f, func_542);
    sv_set_mem(0x1, 0x2, 0x80, func_543);
    sv_set_mem(0x1, 0x2, 0x81, func_544);
    sv_set_mem(0x1, 0x2, 0x82, func_545);
    sv_set_mem(0x1, 0x2, 0x83, func_1933);
    sv_set_mem(0x1, 0x2, 0x84, func_1937);
    sv_set_mem(0x1, 0x2, 0x85, func_1942);
    sv_set_mem(0x1, 0x2, 0x86, func_1946);
    sv_set_mem(0x1, 0x2, 0x87, func_1950);
    sv_set_mem(0x1, 0x2, 0x88, func_1954);
    sv_set_mem(0x1, 0x2, 0x89, func_1958);
    sv_set_mem(0x1, 0x2, 0x25, func_320);
    sv_set_mem(0x1, 0x2, 0x26, func_339);
    sv_set_mem(0x1, 0x2, 0x27, func_321);
    sv_set_mem(0x1, 0x2, 0x28, func_322);
    sv_set_mem(0x1, 0x2, 0x29, edge_sn_end);  // Sephiroth: held up tilt (was func_323, empty)
    sv_set_mem(0x1, 0x2, 0x2a, func_324);
    sv_set_mem(0x1, 0x2, 0x2b, func_325);
    sv_set_mem(0x1, 0x2, 0x2c, func_326);
    sv_set_mem(0x1, 0x2, 0x2d, func_327);
    sv_set_mem(0x1, 0x2, 0x31, func_328);
    sv_set_mem(0x1, 0x2, 0x32, func_329);
    sv_set_mem(0x1, 0x2, 0x33, func_330);
    sv_set_mem(0x1, 0x2, 0x2e, func_331);
    sv_set_mem(0x1, 0x2, 0x2f, func_332);
    sv_set_mem(0x1, 0x2, 0x30, func_333);
    sv_set_mem(0x1, 0x2, 0x34, edge_sn_end);  // Sephiroth: held forward air (was func_334, empty)
    sv_set_mem(0x1, 0x2, 0x35, func_1036);
    sv_set_mem(0x1, 0x2, 0x36, func_1043);
    sv_set_mem(0x1, 0x2, 0x37, func_1049);
    sv_set_mem(0x1, 0x2, 0x38, func_1053);
    sv_set_mem(0x1, 0x2, 0x39, func_1058);
    sv_set_mem(0x1, 0x2, 0x3a, func_1065);
    sv_set_mem(0x1, 0x2, 0x3b, func_1070);
    sv_set_mem(0x1, 0x2, 0x3c, func_1075);
    sv_set_mem(0x1, 0x2, 0x3d, func_1079);
    sv_set_mem(0x1, 0x2, 0x3e, func_1086);
    sv_set_mem(0x1, 0x2, 0x3f, func_1098);
    sv_set_mem(0x1, 0x2, 0x40, func_1109);
    sv_set_mem(0x1, 0x2, 0x41, func_1118);
    sv_set_mem(0x1, 0x2, 0x42, func_1123);
    sv_set_mem(0x1, 0x2, 0x43, func_1127);
    sv_set_mem(0x1, 0x2, 0x44, func_1134);
    sv_set_mem(0x1, 0x2, 0x45, func_787);
    sv_set_mem(0x1, 0x2, 0x46, func_792);
    sv_set_mem(0x1, 0x2, 0x47, func_818);
    sv_set_mem(0x1, 0x2, 0x48, func_819);
    sv_set_mem(0x1, 0x2, 0x49, func_903);
    sv_set_mem(0x1, 0x2, 0x4a, func_912);
    sv_set_mem(0x1, 0x2, 0x4b, func_917);
    sv_set_mem(0x1, 0x2, 0x4c, func_821);
    sv_set_mem(0x1, 0x2, 0x4d, func_923);
    sv_set_mem(0x1, 0x2, 0x4e, func_927);
    sv_set_mem(0x1, 0x2, 0x4f, func_931);
    sv_set_mem(0x1, 0x2, 0x50, func_935);
    sv_set_mem(0x1, 0x2, 0x51, func_939);
    sv_set_mem(0x1, 0x2, 0x52, func_976);
    sv_set_mem(0x1, 0x2, 0x53, func_972);
    sv_set_mem(0x1, 0x2, 0x54, func_943);
    sv_set_mem(0x1, 0x2, 0x55, func_947);
    sv_set_mem(0x1, 0x2, 0x56, func_951);
    sv_set_mem(0x1, 0x2, 0x57, func_955);
    sv_set_mem(0x1, 0x2, 0x58, func_959);
    sv_set_mem(0x1, 0x2, 0xb3, func_1147);
    sv_set_mem(0x1, 0x2, 0xb4, func_1154);
    sv_set_mem(0x1, 0x2, 0xb5, func_1159);
    sv_set_mem(0x1, 0x2, 0xb6, func_1163);
    sv_set_mem(0x1, 0x2, 0xb7, func_1169);
    sv_set_mem(0x1, 0x2, 0x8a, func_1175);
    sv_set_mem(0x1, 0x2, 0x8b, func_1196);
    sv_set_mem(0x1, 0x2, 0x8c, func_1187);
    sv_set_mem(0x1, 0x2, 0x8d, func_1192);
    sv_set_mem(0x1, 0x2, 0x8e, func_1210);
    sv_set_mem(0x1, 0x2, 0x8f, func_1201);
    sv_set_mem(0x1, 0x2, 0x90, func_1206);
    sv_set_mem(0x1, 0x2, 0x91, func_1215);
    sv_set_mem(0x1, 0x2, 0x92, func_1732);
    sv_set_mem(0x1, 0x2, 0x93, func_1737);
    sv_set_mem(0x1, 0x2, 0x94, func_1744);
    sv_set_mem(0x1, 0x2, 0x96, func_1750);
    sv_set_mem(0x1, 0x2, 0x95, func_1755);
    sv_set_mem(0x1, 0x2, 0x97, func_1760);
    sv_set_mem(0x1, 0x2, 0x98, func_1329);
    sv_set_mem(0x1, 0x2, 0x99, func_1333);
    sv_set_mem(0x1, 0x2, 0x9a, func_1337);
    sv_set_mem(0x1, 0x2, 0x9b, func_1341);
    sv_set_mem(0x1, 0x2, 0x9c, func_1345);
    sv_set_mem(0x1, 0x2, 0x9d, func_1349);
    sv_set_mem(0x1, 0x2, 0x9e, func_1353);
    sv_set_mem(0x1, 0x2, 0x9f, func_1364);
    sv_set_mem(0x1, 0x2, 0xa0, func_1368);
    sv_set_mem(0x1, 0x2, 0xa1, func_1359);
    sv_set_mem(0x1, 0x2, 0xa2, func_1372);
    sv_set_mem(0x1, 0x2, 0xa3, func_571);
    sv_set_mem(0x1, 0x2, 0xa4, func_576);
    sv_set_mem(0x1, 0x2, 0xa5, func_580);
    sv_set_mem(0x1, 0x2, 0xa6, func_1219);
    sv_set_mem(0x1, 0x2, 0xc5, func_827);
    sv_set_mem(0x1, 0x2, 0xc6, func_832);
    sv_set_mem(0x1, 0x2, 0xd0, func_1223);
    sv_set_mem(0x1, 0x2, 0xd1, func_1227);
    sv_set_mem(0x1, 0x2, 0xd2, func_1232);
    sv_set_mem(0x1, 0x2, 0xd3, func_1254);
    sv_set_mem(0x1, 0x2, 0xd4, func_1258);
    sv_set_mem(0x1, 0x2, 0xd5, func_1263);
    sv_set_mem(0x1, 0x2, 0xd6, func_1267);
    sv_set_mem(0x1, 0x2, 0xd7, func_1271);
    sv_set_mem(0x1, 0x2, 0xd8, func_1275);
    sv_set_mem(0x1, 0x2, 0xd9, func_1280);
    sv_set_mem(0x1, 0x2, 0xdb, func_840);
    sv_set_mem(0x1, 0x2, 0xdd, func_1288);
    sv_set_mem(0x1, 0x2, 0xde, func_1292);
    sv_set_mem(0x1, 0x2, 0xb1, func_218);
    sv_set_mem(0x1, 0x2, 0xb2, func_233);
    sv_set_mem(0x1, 0x2, 0x14c, func_219);
    sv_set_mem(0x1, 0x2, 0x14f, func_2160);
    sv_set_mem(0x1, 0x2, 0xb8, func_1586);
    sv_set_mem(0x1, 0x2, 0xb9, func_1597);
    sv_set_mem(0x1, 0x2, 0xba, func_1608);
    sv_set_mem(0x1, 0x2, 0xbb, func_1619);
    sv_set_mem(0x1, 0x2, 0xbc, func_1630);
    sv_set_mem(0x1, 0x2, 0xe9, func_1642);
    sv_set_mem(0x1, 0x2, 0xea, func_1647);
    sv_set_mem(0x1, 0x2, 0xeb, func_1652);
    sv_set_mem(0x1, 0x2, 0xbd, func_1656);
    sv_set_mem(0x1, 0x2, 0xbe, func_1662);
    sv_set_mem(0x1, 0x2, 0x109, func_1669);
    sv_set_mem(0x1, 0x2, 0xdf, func_1870);
    sv_set_mem(0x1, 0x2, 0xe3, func_1874);
    sv_set_mem(0x1, 0x2, 0xe2, func_1878);
    sv_set_mem(0x1, 0x2, 0xe5, func_1882);
    sv_set_mem(0x1, 0x2, 0xe4, func_1886);
    sv_set_mem(0x1, 0x2, 0xe0, func_1890);
    sv_set_mem(0x1, 0x2, 0xc7, func_1812);
    sv_set_mem(0x1, 0x2, 0xc8, func_1804);
    sv_set_mem(0x1, 0x2, 0xc9, func_1820);
    sv_set_mem(0x1, 0x2, 0xca, func_1826);
    sv_set_mem(0x1, 0x2, 0xcb, func_1830);
    sv_set_mem(0x1, 0x2, 0x14d, func_691);
    sv_set_mem(0x1, 0x2, 0x14e, func_691);
    sv_set_mem(0x1, 0x2, 0xec, func_1904);
    sv_set_mem(0x1, 0x2, 0xed, func_1911);
    sv_set_mem(0x1, 0x2, 0xef, func_1919);
    sv_set_mem(0x1, 0x2, 0xf0, func_1923);
    sv_set_mem(0x1, 0x2, 0xee, func_1915);
    sv_set_mem(0x1, 0x2, 0xf1, func_127);
    sv_set_mem(0x1, 0x2, 0xf2, func_131);
    sv_set_mem(0x1, 0x2, 0xf3, func_137);
    sv_set_mem(0x1, 0x2, 0xf4, func_141);
    sv_set_mem(0x1, 0x2, 0xf5, func_146);
    sv_set_mem(0x1, 0x2, 0xf7, func_1971);
    sv_set_mem(0x1, 0x2, 0xf8, func_1236);
    sv_set_mem(0x1, 0x2, 0x10e, func_1240);
    sv_set_mem(0x1, 0x2, 0xf9, func_1296);
    sv_set_mem(0x1, 0x2, 0xfe, func_1512);
    sv_set_mem(0x1, 0x2, 0xfb, func_1517);
    sv_set_mem(0x1, 0x2, 0xfc, func_1522);
    sv_set_mem(0x1, 0x2, 0xfd, func_1526);
    sv_set_mem(0x1, 0x2, 0xff, func_1981);
    sv_set_mem(0x1, 0x2, 0x100, func_1300);
    sv_set_mem(0x1, 0x2, 0x114, func_1304);
    sv_set_mem(0x1, 0x2, 0x101, func_1976);
    sv_set_mem(0x1, 0x2, 0x10a, func_1308);
    sv_set_mem(0x1, 0x2, 0x10b, func_1312);
    sv_set_mem(0x1, 0x2, 0x10c, func_1316);
    sv_set_mem(0x1, 0x2, 0x10d, func_1323);
    if (!sys_7(0xd))
    {
        sv_set_mem(0x1, 0x2, 0x14b, func_1962);
    }
    sv_set_mem(0x1, 0x2, 0xa7, func_2107);
    sv_set_mem(0x1, 0x2, 0xa8, func_2111);
    sv_set_mem(0x1, 0x2, 0xa9, func_2115);
    sv_set_mem(0x1, 0x2, 0xaa, func_2119);
    sv_set_mem(0x1, 0x2, 0xab, func_2123);
    sv_set_mem(0x1, 0x2, 0xac, func_2127);
    sv_set_mem(0x1, 0x2, 0xad, func_2131);
    sv_set_mem(0x1, 0x2, 0xae, func_2135);
    sv_set_mem(0x1, 0x2, 0xaf, func_2140);
    sv_set_mem(0x1, 0x2, 0xb0, func_2145);
    sv_set_mem(0x1, 0x2, 0x104, func_1995);
    sv_set_mem(0x1, 0x2, 0x105, func_2000);
    sv_set_mem(0x1, 0x2, 0x106, func_2004);
    sv_set_mem(0x1, 0x2, 0x107, func_2009);
    sv_set_mem(0x1, 0x2, 0x10f, func_2013);
    sv_set_mem(0x1, 0x2, 0x128, func_2179);
    sv_set_mem(0x1, 0x2, 0x129, func_2184);
    sv_set_mem(0x1, 0x2, 0x12a, func_2189);
    sv_set_mem(0x1, 0x2, 0x12b, func_2179);
    sv_set_mem(0x1, 0x2, 0x12c, func_2184);
    sv_set_mem(0x1, 0x2, 0x12d, func_2189);
    sv_set_mem(0x1, 0x2, 0x12e, func_2179);
    sv_set_mem(0x1, 0x2, 0x12f, func_2184);
    sv_set_mem(0x1, 0x2, 0x130, func_2189);
    sv_set_mem(0x1, 0x2, 0x131, func_2179);
    sv_set_mem(0x1, 0x2, 0x132, func_2184);
    sv_set_mem(0x1, 0x2, 0x133, func_2189);
    sv_set_mem(0x1, 0x2, 0x134, func_2179);
    sv_set_mem(0x1, 0x2, 0x135, func_2184);
    sv_set_mem(0x1, 0x2, 0x136, func_2189);
    sv_set_mem(0x1, 0x2, 0x124, func_2216);
    sv_set_mem(0x1, 0x2, 0x125, func_2220);
    sv_set_mem(0x1, 0x2, 0x137, func_2152);
    sv_set_mem(0x1, 0x2, 0x138, func_2156);
    sv_set_mem(0x1, 0x2, 0x139, func_2233);
    sv_set_mem(0x1, 0x2, 0x13a, func_818);
    sv_set_mem(0x1, 0x2, 0x13d, func_792);
    sv_set_mem(0x1, 0x2, 0x13b, func_2184);
    sv_set_mem(0x1, 0x2, 0x13c, func_2179);
    sv_set_mem(0x1, 0x2, 0x13e, func_2179);
    sv_set_mem(0x1, 0x2, 0x13f, func_2185);
    sv_set_mem(0x1, 0x2, 0x140, func_2189);
    sv_set_mem(0x1, 0x2, 0x147, func_2238);
    sv_set_mem(0x1, 0x2, 0x110, func_2018);
    sv_set_mem(0x1, 0x2, 0x111, func_2023);
    sv_set_mem(0x1, 0x2, 0x112, func_2027);
    sv_set_mem(0x1, 0x2, 0x113, func_2031);
    sv_set_mem(0x1, 0x2, 0x118, func_2047);
    sv_set_mem(0x1, 0x2, 0x119, func_2052);
    sv_set_mem(0x1, 0x2, 0x11a, func_2056);
    sv_set_mem(0x1, 0x2, 0x115, func_2035);
    sv_set_mem(0x1, 0x2, 0x116, func_2039);
    sv_set_mem(0x1, 0x2, 0x117, func_2043);
    sv_set_mem(0x1, 0x2, 0x11c, func_2060);
    sv_set_mem(0x1, 0x2, 0x11d, func_2065);
    sv_set_mem(0x1, 0x2, 0x11e, func_2069);
    sv_set_mem(0x1, 0x2, 0x142, func_2073);
    sv_set_mem(0x1, 0x2, 0x143, func_2078);
    sv_set_mem(0x1, 0x2, 0x144, func_2082);
    sv_set_mem(0x1, 0x2, 0x145, func_2086);
    sv_set_mem(0x1, 0x2, 0x146, func_2090);
    sv_set_mem(0x1, 0x2, 0x148, func_2094);
    sv_set_mem(0x1, 0x2, 0x149, func_2099);
    sv_set_mem(0x1, 0x2, 0x14a, func_2103);
}

void func_116()
{
    sv_set_mem(0x1, 0x3, 0xd, func_585);
    sv_set_mem(0x1, 0x3, 0x1f, func_385);
    sv_set_mem(0x1, 0x3, 0x20, func_385);
    sv_set_mem(0x1, 0x3, 0x21, func_385);
    sv_set_mem(0x1, 0x3, 0x22, func_385);
    sv_set_mem(0x1, 0x3, 0x1b, func_447);
    sv_set_mem(0x1, 0x3, 0x1c, func_439);
    sv_set_mem(0x1, 0x3, 0x1e, func_459);
    sv_set_mem(0x1, 0x3, 0x59, func_468);
    sv_set_mem(0x1, 0x3, 0x6c, func_1721);
    sv_set_mem(0x1, 0x3, 0x6d, func_1721);
    sv_set_mem(0x1, 0x3, 0x6e, func_1721);
    sv_set_mem(0x1, 0x3, 0x6f, func_1721);
    sv_set_mem(0x1, 0x3, 0x70, func_1721);
    sv_set_mem(0x1, 0x3, 0x2b, func_344);
    sv_set_mem(0x1, 0x3, 0x2c, func_344);
    sv_set_mem(0x1, 0x3, 0x2d, func_344);
    sv_set_mem(0x1, 0x3, 0x31, func_344);
    sv_set_mem(0x1, 0x3, 0x32, func_344);
    sv_set_mem(0x1, 0x3, 0x33, func_344);
    sv_set_mem(0x1, 0x3, 0x2e, func_344);
    sv_set_mem(0x1, 0x3, 0x2f, func_344);
    sv_set_mem(0x1, 0x3, 0x30, func_344);
    sv_set_mem(0x1, 0x3, 0x72, func_203);
    sv_set_mem(0x1, 0x3, 0x73, func_196);
    sv_set_mem(0x1, 0x3, 0x74, func_196);
    sv_set_mem(0x1, 0x3, 0x75, func_196);
    sv_set_mem(0x1, 0x3, 0x76, func_196);
    sv_set_mem(0x1, 0x3, 0x77, func_196);
    sv_set_mem(0x1, 0x3, 0x78, func_196);
    sv_set_mem(0x1, 0x3, 0x79, func_196);
    sv_set_mem(0x1, 0x3, 0x7a, func_196);
    sv_set_mem(0x1, 0x3, 0x108, func_207);
    sv_set_mem(0x1, 0x3, 0x7b, func_1027);
    sv_set_mem(0x1, 0x3, 0x7c, func_1027);
    sv_set_mem(0x1, 0x3, 0x45, func_858);
    sv_set_mem(0x1, 0x3, 0x46, func_858);
    sv_set_mem(0x1, 0x3, 0x47, func_858);
    sv_set_mem(0x1, 0x3, 0x48, func_858);
    sv_set_mem(0x1, 0x3, 0x49, func_906);
    sv_set_mem(0x1, 0x3, 0x4a, func_909);
    sv_set_mem(0x1, 0x3, 0x4b, func_914);
    sv_set_mem(0x1, 0x3, 0x4c, func_894);
    sv_set_mem(0x1, 0x3, 0x4d, func_968);
    sv_set_mem(0x1, 0x3, 0x4e, func_990);
    sv_set_mem(0x1, 0x3, 0x4f, func_968);
    sv_set_mem(0x1, 0x3, 0x57, func_991);
    sv_set_mem(0x1, 0x3, 0x57, func_991);
    sv_set_mem(0x1, 0x3, 0x58, func_994);
    sv_set_mem(0x1, 0x3, 0xb1, func_220);
    sv_set_mem(0x1, 0x3, 0x10, func_581);
    sv_set_mem(0x1, 0x3, 0x19, edge_hi_landing_init); // func_586 + Sephiroth's Octaslash landing motion
    sv_set_mem(0x1, 0x3, 0x5d, func_858);
    sv_set_mem(0x1, 0x3, 0x60, func_858);
    sv_set_mem(0x1, 0x3, 0x61, func_858);
    sv_set_mem(0x1, 0x3, 0x63, func_858);
    sv_set_mem(0x1, 0x3, 0xa, func_584);
    sv_set_mem(0x1, 0x3, 0xe, func_581);
    sv_set_mem(0x1, 0x3, 0xf, func_581);
    sv_set_mem(0x1, 0x3, 0x16, func_586);
    sv_set_mem(0x1, 0x3, 0x17, func_586);
    sv_set_mem(0x1, 0x3, 0x18, func_586);
    sv_set_mem(0x1, 0x3, 0x1a, func_586);
    sv_set_mem(0x1, 0x3, 0xb2, func_234);
    sv_set_mem(0x1, 0x3, 0x11, func_622);
    sv_set_mem(0x1, 0x3, 0x12, func_622);
    sv_set_mem(0x1, 0x3, 0x13, func_626);
    sv_set_mem(0x1, 0x3, 0x14, func_626);
    sv_set_mem(0x1, 0x3, 0x69, func_1721);
    sv_set_mem(0x1, 0x3, 0x6a, func_1721);
    sv_set_mem(0x1, 0x3, 0x14f, func_2161);
    sv_set_mem(0x1, 0x3, 0x1, func_765);
    sv_set_mem(0x1, 0x3, 0x2, func_777);
    sv_set_mem(0x1, 0x3, 0x3, func_743);
    sv_set_mem(0x1, 0x3, 0x4, func_750);
    sv_set_mem(0x1, 0x3, 0x5, func_753);
    sv_set_mem(0x1, 0x3, 0x6, func_756);
    sv_set_mem(0x1, 0x3, 0x7, func_756);
    sv_set_mem(0x1, 0x3, 0x8, func_759);
    sv_set_mem(0x1, 0x3, 0x9, func_753);
    sv_set_mem(0x1, 0x3, 0x6b, func_1721);
    sv_set_mem(0x1, 0x3, 0xb3, func_1148);
    sv_set_mem(0x1, 0x3, 0xb7, func_1170);
    sv_set_mem(0x1, 0x3, 0x36, func_1038);
    sv_set_mem(0x1, 0x3, 0x38, func_1038);
    sv_set_mem(0x1, 0x3, 0x3a, func_1060);
    sv_set_mem(0x1, 0x3, 0x3b, func_1060);
    sv_set_mem(0x1, 0x3, 0x3c, func_1072);
    sv_set_mem(0x1, 0x3, 0x3e, func_1081);
    sv_set_mem(0x1, 0x3, 0x3f, func_1089);
    sv_set_mem(0x1, 0x3, 0x40, func_1100);
    sv_set_mem(0x1, 0x3, 0x41, func_1111);
    sv_set_mem(0x1, 0x3, 0x42, func_1120);
    sv_set_mem(0x1, 0x3, 0x44, func_1129);
    sv_set_mem(0x1, 0x3, 0xb8, func_1587);
    sv_set_mem(0x1, 0x3, 0xb9, func_1598);
    sv_set_mem(0x1, 0x3, 0xba, func_1609);
    sv_set_mem(0x1, 0x3, 0xbb, func_1620);
    sv_set_mem(0x1, 0x3, 0xbc, func_1631);
    sv_set_mem(0x1, 0x3, 0xbd, func_1657);
    sv_set_mem(0x1, 0x3, 0xbe, func_1663);
    sv_set_mem(0x1, 0x3, 0xec, func_1089);
    sv_set_mem(0x1, 0x3, 0xee, func_1089);
    sv_set_mem(0x1, 0x3, 0x8b, func_999);
    sv_set_mem(0x1, 0x3, 0x8e, func_999);
    sv_set_mem(0x1, 0x3, 0x8f, func_999);
    sv_set_mem(0x1, 0x3, 0x90, func_999);
    sv_set_mem(0x1, 0x3, 0x96, func_1761);
    sv_set_mem(0x1, 0x3, 0x95, func_1761);
    sv_set_mem(0x1, 0x3, 0x98, func_1537);
    sv_set_mem(0x1, 0x3, 0x99, func_1537);
    sv_set_mem(0x1, 0x3, 0x9a, func_1537);
    sv_set_mem(0x1, 0x3, 0x9b, func_1537);
    sv_set_mem(0x1, 0x3, 0x9c, func_1537);
    sv_set_mem(0x1, 0x3, 0x9d, func_1537);
    sv_set_mem(0x1, 0x3, 0x9e, func_1537);
    sv_set_mem(0x1, 0x3, 0x9f, func_1537);
    sv_set_mem(0x1, 0x3, 0xa0, func_1537);
    sv_set_mem(0x1, 0x3, 0xa1, func_1537);
    sv_set_mem(0x1, 0x3, 0xa2, func_1537);
    sv_set_mem(0x1, 0x3, 0xd3, func_1003);
    sv_set_mem(0x1, 0x3, 0xd4, func_1003);
    sv_set_mem(0x1, 0x3, 0xd5, func_1003);
    sv_set_mem(0x1, 0x3, 0xd6, func_1003);
    sv_set_mem(0x1, 0x3, 0xd7, func_1003);
    sv_set_mem(0x1, 0x3, 0xd8, func_1003);
    sv_set_mem(0x1, 0x3, 0xd9, func_1003);
    sv_set_mem(0x1, 0x3, 0xda, func_1011);
    sv_set_mem(0x1, 0x3, 0xdb, func_918);
    sv_set_mem(0x1, 0x3, 0xbf, func_1683);
    sv_set_mem(0x1, 0x3, 0xc0, func_1683);
    sv_set_mem(0x1, 0x3, 0xc1, func_1690);
    sv_set_mem(0x1, 0x3, 0x64, func_1721);
    sv_set_mem(0x1, 0x3, 0x65, func_1721);
    sv_set_mem(0x1, 0x3, 0x66, func_1721);
    sv_set_mem(0x1, 0x3, 0x67, func_1721);
    sv_set_mem(0x1, 0x3, 0x68, func_1721);
    sv_set_mem(0x1, 0x3, 0x71, func_677);
    sv_set_mem(0x1, 0x3, 0xc2, func_1770);
    sv_set_mem(0x1, 0x3, 0xc3, func_1780);
    sv_set_mem(0x1, 0x3, 0xc4, func_1792);
    sv_set_mem(0x1, 0x3, 0xc8, func_1805);
    sv_set_mem(0x1, 0x3, 0xc7, func_1813);
    sv_set_mem(0x1, 0x3, 0xc9, func_1821);
    sv_set_mem(0x1, 0x3, 0xfa, func_1835);
    sv_set_mem(0x1, 0x3, 0xcc, func_1841);
    sv_set_mem(0x1, 0x3, 0xcd, func_1847);
    sv_set_mem(0x1, 0x3, 0xce, func_1853);
    sv_set_mem(0x1, 0x3, 0xcf, func_1859);
    sv_set_mem(0x1, 0x3, 0x141, func_1865);
    sv_set_mem(0x1, 0x3, 0xff, func_1978);
    sv_set_mem(0x1, 0x3, 0x10e, func_1241);
    sv_set_mem(0x1, 0x3, 0x10c, func_1317);
    sv_set_mem(0x1, 0x3, 0x139, func_858);
    sv_set_mem(0x1, 0x3, 0x13a, func_858);
    sv_set_mem(0x1, 0x3, 0x13d, func_858);
    sv_set_mem(0x1, 0x3, 0x110, func_2019);
    sv_set_mem(0x1, 0x3, 0x118, func_2048);
    sv_set_mem(0x1, 0x3, 0x11c, func_2061);
    sv_set_mem(0x1, 0x3, 0x142, func_2074);
    sv_set_mem(0x1, 0x3, 0x148, func_2095);
}

void func_117()
{
    sv_set_mem(0x1, 0x4, 0x1, func_767);
    sv_set_mem(0x1, 0x4, 0x34, func_340);
    sv_set_mem(0x1, 0x4, 0x72, func_205);
    sv_set_mem(0x1, 0x4, 0x73, func_198);
    sv_set_mem(0x1, 0x4, 0x74, func_198);
    sv_set_mem(0x1, 0x4, 0x75, func_198);
    sv_set_mem(0x1, 0x4, 0x76, func_198);
    sv_set_mem(0x1, 0x4, 0x77, func_198);
    sv_set_mem(0x1, 0x4, 0x78, func_198);
    sv_set_mem(0x1, 0x4, 0x79, func_198);
    sv_set_mem(0x1, 0x4, 0x7a, func_198);
    sv_set_mem(0x1, 0x4, 0x108, func_208);
    sv_set_mem(0x1, 0x4, 0x7b, func_1029);
    sv_set_mem(0x1, 0x4, 0x7c, func_1029);
    sv_set_mem(0x1, 0x4, 0x45, func_859);
    sv_set_mem(0x1, 0x4, 0x46, func_859);
    sv_set_mem(0x1, 0x4, 0x47, func_859);
    sv_set_mem(0x1, 0x4, 0x48, func_859);
    sv_set_mem(0x1, 0x4, 0x49, func_907);
    sv_set_mem(0x1, 0x4, 0x4a, func_907);
    sv_set_mem(0x1, 0x4, 0x4b, func_907);
    sv_set_mem(0x1, 0x4, 0x4c, func_898);
    sv_set_mem(0x1, 0x4, 0xb1, func_221);
    sv_set_mem(0x1, 0x4, 0x58, func_995);
    sv_set_mem(0x1, 0x4, 0x10, func_582);
    sv_set_mem(0x1, 0x4, 0x19, func_590);
    sv_set_mem(0x1, 0x4, 0x5d, func_859);
    sv_set_mem(0x1, 0x4, 0x60, func_859);
    sv_set_mem(0x1, 0x4, 0x61, func_859);
    sv_set_mem(0x1, 0x4, 0x63, func_859);
    sv_set_mem(0x1, 0x4, 0xe, func_582);
    sv_set_mem(0x1, 0x4, 0xf, func_582);
    sv_set_mem(0x1, 0x4, 0x16, func_590);
    sv_set_mem(0x1, 0x4, 0x17, func_590);
    sv_set_mem(0x1, 0x4, 0x18, func_590);
    sv_set_mem(0x1, 0x4, 0x1a, func_590);
    sv_set_mem(0x1, 0x4, 0xb2, func_241);
    sv_set_mem(0x1, 0x4, 0x11, func_623);
    sv_set_mem(0x1, 0x4, 0x12, func_623);
    sv_set_mem(0x1, 0x4, 0x13, func_627);
    sv_set_mem(0x1, 0x4, 0x14, func_627);
    sv_set_mem(0x1, 0x4, 0x2, func_778);
    sv_set_mem(0x1, 0x4, 0x3, func_744);
    sv_set_mem(0x1, 0x4, 0x4, func_751);
    sv_set_mem(0x1, 0x4, 0x5, func_754);
    sv_set_mem(0x1, 0x4, 0x6, func_757);
    sv_set_mem(0x1, 0x4, 0x7, func_757);
    sv_set_mem(0x1, 0x4, 0x8, func_760);
    sv_set_mem(0x1, 0x4, 0x9, func_754);
    sv_set_mem(0x1, 0x4, 0x1b, func_449);
    sv_set_mem(0x1, 0x4, 0x1c, func_441);
    sv_set_mem(0x1, 0x4, 0x1e, func_461);
    sv_set_mem(0x1, 0x4, 0x1d, func_457);
    sv_set_mem(0x1, 0x4, 0xb7, func_1171);
    sv_set_mem(0x1, 0x4, 0x3f, func_1093);
    sv_set_mem(0x1, 0x4, 0x40, func_1102);
    sv_set_mem(0x1, 0x4, 0x41, func_1115);
    sv_set_mem(0x1, 0x4, 0xb8, func_1589);
    sv_set_mem(0x1, 0x4, 0xb9, func_1600);
    sv_set_mem(0x1, 0x4, 0xba, func_1611);
    sv_set_mem(0x1, 0x4, 0xbb, func_1622);
    sv_set_mem(0x1, 0x4, 0xbc, func_1633);
    sv_set_mem(0x1, 0x4, 0xec, func_1907);
    sv_set_mem(0x1, 0x4, 0xee, func_1093);
    sv_set_mem(0x1, 0x4, 0xbe, func_1664);
    sv_set_mem(0x1, 0x4, 0x8b, func_1000);
    sv_set_mem(0x1, 0x4, 0x8e, func_1000);
    sv_set_mem(0x1, 0x4, 0x8f, func_1000);
    sv_set_mem(0x1, 0x4, 0x90, func_1000);
    sv_set_mem(0x1, 0x4, 0x98, func_1540);
    sv_set_mem(0x1, 0x4, 0x99, func_1540);
    sv_set_mem(0x1, 0x4, 0x9a, func_1540);
    sv_set_mem(0x1, 0x4, 0x9b, func_1540);
    sv_set_mem(0x1, 0x4, 0x9c, func_1540);
    sv_set_mem(0x1, 0x4, 0x9d, func_1540);
    sv_set_mem(0x1, 0x4, 0x9e, func_1540);
    sv_set_mem(0x1, 0x4, 0x9f, func_1540);
    sv_set_mem(0x1, 0x4, 0xa0, func_1540);
    sv_set_mem(0x1, 0x4, 0xa1, func_1540);
    sv_set_mem(0x1, 0x4, 0xa2, func_1540);
    sv_set_mem(0x1, 0x4, 0xd3, func_1004);
    sv_set_mem(0x1, 0x4, 0xd4, func_1004);
    sv_set_mem(0x1, 0x4, 0xd5, func_1004);
    sv_set_mem(0x1, 0x4, 0xd6, func_1004);
    sv_set_mem(0x1, 0x4, 0xd7, func_1004);
    sv_set_mem(0x1, 0x4, 0xd8, func_1004);
    sv_set_mem(0x1, 0x4, 0xd9, func_1004);
    sv_set_mem(0x1, 0x4, 0xdb, func_859);
    sv_set_mem(0x1, 0x4, 0xc2, func_1771);
    sv_set_mem(0x1, 0x4, 0xc3, func_1782);
    sv_set_mem(0x1, 0x4, 0xc4, func_1794);
    sv_set_mem(0x1, 0x4, 0xc8, func_1806);
    sv_set_mem(0x1, 0x4, 0xc7, func_1814);
    sv_set_mem(0x1, 0x4, 0xc9, func_1822);
    sv_set_mem(0x1, 0x4, 0x10e, func_1242);
    sv_set_mem(0x1, 0x4, 0x41, func_1115);
    sv_set_mem(0x1, 0x4, 0x71, func_678);
    sv_set_mem(0x1, 0x4, 0xa, func_489);
    sv_set_mem(0x1, 0x4, 0x6c, func_1723);
    sv_set_mem(0x1, 0x4, 0x6d, func_1723);
    sv_set_mem(0x1, 0x4, 0x66, func_1723);
    sv_set_mem(0x1, 0x4, 0x67, func_1723);
    sv_set_mem(0x1, 0x4, 0x6b, func_1723);
    sv_set_mem(0x1, 0x4, 0x139, func_2234);
    sv_set_mem(0x1, 0x4, 0x13a, func_859);
    sv_set_mem(0x1, 0x4, 0x13d, func_859);
}

void func_118()
{
    sv_set_mem(0x1, 0x5, 0x1c, func_443);
    sv_set_mem(0x1, 0x5, 0x1b, func_453);
    sv_set_mem(0x1, 0x5, 0x1e, func_463);
    sv_set_mem(0x1, 0x5, 0x1d, func_458);
    sv_set_mem(0x1, 0x5, 0x6c, func_1722);
    sv_set_mem(0x1, 0x5, 0x6d, func_1722);
    sv_set_mem(0x1, 0x5, 0x66, func_1722);
    sv_set_mem(0x1, 0x5, 0x67, func_1722);
    sv_set_mem(0x1, 0x5, 0x6b, func_1722);
    sv_set_mem(0x1, 0x5, 0x18, func_591);
    sv_set_mem(0x1, 0x5, 0xb8, func_1592);
    sv_set_mem(0x1, 0x5, 0xb9, func_1603);
    sv_set_mem(0x1, 0x5, 0xba, func_1614);
    sv_set_mem(0x1, 0x5, 0xbb, func_1625);
    sv_set_mem(0x1, 0x5, 0xbc, func_1636);
    sv_set_mem(0x1, 0x5, 0x45, func_860);
    sv_set_mem(0x1, 0x5, 0x46, func_860);
    sv_set_mem(0x1, 0x5, 0x47, func_860);
    sv_set_mem(0x1, 0x5, 0x48, func_892);
    sv_set_mem(0x1, 0x5, 0x57, func_860);
    sv_set_mem(0x1, 0x5, 0x10e, func_1243);
    sv_set_mem(0x1, 0x5, 0x139, func_860);
    sv_set_mem(0x1, 0x5, 0x13a, func_860);
    sv_set_mem(0x1, 0x5, 0x13d, func_860);
}

void func_119()
{
    sv_set_mem(0x1, 0x6, 0x1c, func_445);
    sv_set_mem(0x1, 0x6, 0x1b, func_451);
    sv_set_mem(0x1, 0x6, 0x1e, func_466);
    sv_set_mem(0x1, 0x6, 0x6c, func_1725);
    sv_set_mem(0x1, 0x6, 0x6d, func_1725);
    sv_set_mem(0x1, 0x6, 0x6e, func_1725);
    sv_set_mem(0x1, 0x6, 0x6f, func_1725);
    sv_set_mem(0x1, 0x6, 0x70, func_1725);
    sv_set_mem(0x1, 0x6, 0x2b, func_347);
    sv_set_mem(0x1, 0x6, 0x2c, func_348);
    sv_set_mem(0x1, 0x6, 0x2d, func_348);
    sv_set_mem(0x1, 0x6, 0x33, func_348);
    sv_set_mem(0x1, 0x6, 0x32, func_348);
    sv_set_mem(0x1, 0x6, 0x30, func_348);
    sv_set_mem(0x1, 0x6, 0x2f, func_348);
    sv_set_mem(0x1, 0x6, 0x34, func_342);
    sv_set_mem(0x1, 0x6, 0x72, func_206);
    sv_set_mem(0x1, 0x6, 0x73, func_201);
    sv_set_mem(0x1, 0x6, 0x74, func_201);
    sv_set_mem(0x1, 0x6, 0x75, func_201);
    sv_set_mem(0x1, 0x6, 0x77, func_201);
    sv_set_mem(0x1, 0x6, 0x76, func_201);
    sv_set_mem(0x1, 0x6, 0x78, func_201);
    sv_set_mem(0x1, 0x6, 0x79, func_201);
    sv_set_mem(0x1, 0x6, 0x7a, func_201);
    sv_set_mem(0x1, 0x6, 0x108, func_209);
    sv_set_mem(0x1, 0x6, 0x7b, func_1031);
    sv_set_mem(0x1, 0x6, 0x7c, func_1031);
    sv_set_mem(0x1, 0x6, 0x45, func_861);
    sv_set_mem(0x1, 0x6, 0x46, func_861);
    sv_set_mem(0x1, 0x6, 0x47, func_889);
    sv_set_mem(0x1, 0x6, 0x48, func_893);
    sv_set_mem(0x1, 0x6, 0x49, func_889);
    sv_set_mem(0x1, 0x6, 0x4a, func_889);
    sv_set_mem(0x1, 0x6, 0x4b, func_889);
    sv_set_mem(0x1, 0x6, 0x57, func_993);
    sv_set_mem(0x1, 0x6, 0xb1, func_224);
    sv_set_mem(0x1, 0x6, 0x10, func_583);
    sv_set_mem(0x1, 0x6, 0x19, func_592);
    sv_set_mem(0x1, 0x6, 0x5d, func_861);
    sv_set_mem(0x1, 0x6, 0x60, func_861);
    sv_set_mem(0x1, 0x6, 0x61, func_861);
    sv_set_mem(0x1, 0x6, 0x63, func_861);
    sv_set_mem(0x1, 0x6, 0xe, func_583);
    sv_set_mem(0x1, 0x6, 0xf, func_583);
    sv_set_mem(0x1, 0x6, 0x16, func_592);
    sv_set_mem(0x1, 0x6, 0x17, func_592);
    sv_set_mem(0x1, 0x6, 0x18, func_592);
    sv_set_mem(0x1, 0x6, 0x1a, func_592);
    sv_set_mem(0x1, 0x6, 0xb2, func_243);
    sv_set_mem(0x1, 0x6, 0x11, func_625);
    sv_set_mem(0x1, 0x6, 0x12, func_625);
    sv_set_mem(0x1, 0x6, 0x13, func_628);
    sv_set_mem(0x1, 0x6, 0x14, func_628);
    sv_set_mem(0x1, 0x6, 0x69, func_1725);
    sv_set_mem(0x1, 0x6, 0x6a, func_1725);
    sv_set_mem(0x1, 0x6, 0x14f, func_2163);
    sv_set_mem(0x1, 0x6, 0x1, func_768);
    sv_set_mem(0x1, 0x6, 0x2, func_779);
    sv_set_mem(0x1, 0x6, 0x3, func_745);
    sv_set_mem(0x1, 0x6, 0x4, func_752);
    sv_set_mem(0x1, 0x6, 0x5, func_755);
    sv_set_mem(0x1, 0x6, 0x6, func_758);
    sv_set_mem(0x1, 0x6, 0x7, func_758);
    sv_set_mem(0x1, 0x6, 0x8, func_761);
    sv_set_mem(0x1, 0x6, 0x9, func_755);
    sv_set_mem(0x1, 0x6, 0x6b, func_1725);
    sv_set_mem(0x1, 0x6, 0xb3, func_1150);
    sv_set_mem(0x1, 0x6, 0xb4, func_1155);
    sv_set_mem(0x1, 0x6, 0xb6, func_1164);
    sv_set_mem(0x1, 0x6, 0x36, func_1042);
    sv_set_mem(0x1, 0x6, 0x38, func_1042);
    sv_set_mem(0x1, 0x6, 0x3a, func_1064);
    sv_set_mem(0x1, 0x6, 0x3b, func_1064);
    sv_set_mem(0x1, 0x6, 0x3e, func_1085);
    sv_set_mem(0x1, 0x6, 0x3f, func_1097);
    sv_set_mem(0x1, 0x6, 0x40, func_1097);
    sv_set_mem(0x1, 0x6, 0x41, func_1097);
    sv_set_mem(0x1, 0x6, 0x44, func_1133);
    sv_set_mem(0x1, 0x6, 0xb8, func_1593);
    sv_set_mem(0x1, 0x6, 0xb9, func_1604);
    sv_set_mem(0x1, 0x6, 0xba, func_1615);
    sv_set_mem(0x1, 0x6, 0xbb, func_1626);
    sv_set_mem(0x1, 0x6, 0xbc, func_1637);
    sv_set_mem(0x1, 0x6, 0xbd, func_1658);
    sv_set_mem(0x1, 0x6, 0xbe, func_1665);
    sv_set_mem(0x1, 0x6, 0x8b, func_1001);
    sv_set_mem(0x1, 0x6, 0x8e, func_1001);
    sv_set_mem(0x1, 0x6, 0x8f, func_1001);
    sv_set_mem(0x1, 0x6, 0x90, func_1001);
    sv_set_mem(0x1, 0x6, 0x96, func_1762);
    sv_set_mem(0x1, 0x6, 0x95, func_1762);
    sv_set_mem(0x1, 0x6, 0x98, func_1543);
    sv_set_mem(0x1, 0x6, 0x99, func_1543);
    sv_set_mem(0x1, 0x6, 0x9a, func_1543);
    sv_set_mem(0x1, 0x6, 0x9b, func_1543);
    sv_set_mem(0x1, 0x6, 0x9c, func_1543);
    sv_set_mem(0x1, 0x6, 0x9d, func_1543);
    sv_set_mem(0x1, 0x6, 0x9e, func_1543);
    sv_set_mem(0x1, 0x6, 0x9f, func_1543);
    sv_set_mem(0x1, 0x6, 0xa0, func_1543);
    sv_set_mem(0x1, 0x6, 0xa1, func_1543);
    sv_set_mem(0x1, 0x6, 0xa2, func_1543);
    sv_set_mem(0x1, 0x6, 0xd3, func_1006);
    sv_set_mem(0x1, 0x6, 0xd4, func_1006);
    sv_set_mem(0x1, 0x6, 0xd5, func_1006);
    sv_set_mem(0x1, 0x6, 0xd6, func_1006);
    sv_set_mem(0x1, 0x6, 0xd7, func_1006);
    sv_set_mem(0x1, 0x6, 0xd8, func_1006);
    sv_set_mem(0x1, 0x6, 0xd9, func_1006);
    sv_set_mem(0x1, 0x6, 0xda, func_1015);
    sv_set_mem(0x1, 0x6, 0xdb, func_919);
    sv_set_mem(0x1, 0x6, 0xbf, func_1689);
    sv_set_mem(0x1, 0x6, 0xc0, func_1689);
    sv_set_mem(0x1, 0x6, 0xc1, func_1696);
    sv_set_mem(0x1, 0x6, 0x64, func_1725);
    sv_set_mem(0x1, 0x6, 0x65, func_1725);
    sv_set_mem(0x1, 0x6, 0x66, func_1725);
    sv_set_mem(0x1, 0x6, 0x67, func_1725);
    sv_set_mem(0x1, 0x6, 0x68, func_1725);
    sv_set_mem(0x1, 0x6, 0x68, func_1725);
    sv_set_mem(0x1, 0x6, 0xc2, func_1775);
    sv_set_mem(0x1, 0x6, 0xc3, func_1786);
    sv_set_mem(0x1, 0x6, 0xc4, func_1798);
    sv_set_mem(0x1, 0x6, 0xc8, func_1808);
    sv_set_mem(0x1, 0x6, 0xc7, func_1815);
    sv_set_mem(0x1, 0x6, 0xc9, func_1823);
    sv_set_mem(0x1, 0x6, 0xfa, func_1836);
    sv_set_mem(0x1, 0x6, 0xcc, func_1842);
    sv_set_mem(0x1, 0x6, 0xcd, func_1848);
    sv_set_mem(0x1, 0x6, 0xce, func_1854);
    sv_set_mem(0x1, 0x6, 0xcf, func_1860);
    sv_set_mem(0x1, 0x6, 0x141, func_1866);
    sv_set_mem(0x1, 0x6, 0x10e, func_1244);
    sv_set_mem(0x1, 0x6, 0x139, func_861);
    sv_set_mem(0x1, 0x6, 0x13a, func_889);
    sv_set_mem(0x1, 0x6, 0x13d, func_861);
}

void func_120()
{
    
}

void func_121()
{
    sv_set_mem(0x1, 0x8, 0xb1, func_223);
    sv_set_mem(0x1, 0x8, 0x3f, func_1096);
    sv_set_mem(0x1, 0x8, 0x40, func_1108);
    sv_set_mem(0x1, 0x8, 0x41, func_1117);
    sv_set_mem(0x1, 0x8, 0xf6, func_1966);
    sv_set_mem(0x1, 0x8, 0xec, func_1096);
    sv_set_mem(0x1, 0x8, 0xee, func_1096);
}

void func_122()
{
    sv_set_mem(0x1, 0x3, 0x127, sv_get_mem(0x1, 0x3, 0x47));
    sv_set_mem(0x1, 0x4, 0x127, sv_get_mem(0x1, 0x4, 0x47));
    sv_set_mem(0x1, 0x6, 0x127, sv_get_mem(0x1, 0x6, 0x47));
    sv_set_mem(0x1, 0x5, 0x127, sv_get_mem(0x1, 0x5, 0x47));
    sv_set_mem(0x1, 0x7, 0x127, sv_get_mem(0x1, 0x7, 0x47));
    sv_set_mem(0x1, 0x8, 0x127, sv_get_mem(0x1, 0x8, 0x47));
}

int func_123()
{
    StatusModule(0x5, 0x2, 0x13, 0x5, 0x1, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0x1, 0, 0x1, 0x832, 0x4002, 0x1000, 0x20000);
    return 0;
}

void func_124()
{
    WorkModule(0xa, 0x11000003);
    if (WorkModule(0x10, 0x2100000d))
    {
        WorkModule(0x2710, 0x2100000e);
    }
    if (WorkModule(0x10, 0x2100000e) && !WorkModule(0x10, 0x2100000d))
    {
        GroundModule(0x2712, 0);
        WorkModule(0x2711, 0x2100000e);
    }
}

void func_125()
{
    int var0;
    int var1;
    WorkModule(0x19, 0x1f000008);
    var0 = WorkModule(0x6, 0x120000c1);
    if (global5 == 0x22)
    {
        var0 = WorkModule(0x6, 0x120000bf);
    }
    var0 -= 0x1;
    WorkModule(0x7, var0, 0x10000076);
    WorkModule(0x17, 0x1e00001c);
    if (MotionModule(0x22, 0x91))
    {
        func_22(0x91, 0, 1.0f);
    }
    if (!StopModule(0x1))
    {
        func_124();
    }
    global16 = func_124;
    var1 = WorkModule(0x6, 0x11000004);
    if (var1 >= 0x2)
    {
        GroundModule(0x2712, var1);
        WorkModule(0x1a, 0x1f000009);
    }
    func_78(func_126);
}

int func_126()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return 0x1;
    }
    if (func_55())
    {
        return 0x1;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (func_99() == 0x1 && WorkModule(0x2712, 0x2100000d))
    {
        func_16(0xf2, 0);
        return 0x1;
    }
    return 0;
}

void func_127()
{
    if (global6 != 0xf3 && global6 != 0xf2)
    {
        ArticleModule(0x2712, WorkModule(0x6, 0x11000002));
    }
}

int func_128()
{
    StatusModule(0x5, 0x2, 0x13, 0x4, 0, 0, 0, 0xc, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0x1, 0, 0x1, 0, 0x4002, 0, 0);
    return 0;
}

void func_129()
{
    WorkModule(0x19, 0x1f000008);
    WorkModule(0x7, 0x95, 0x11000005);
    if (!WorkModule(0x10, 0x21000010))
    {
        func_22(0x92, 0, 1.0f);
        MotionModule(0x4, 0);
    }
    ArticleModule(0x2713, WorkModule(0x6, 0x11000002), WorkModule(0x6, 0x11000004));
    func_78(func_130);
}

void func_130()
{
    if (func_55())
    {
        return 0x1;
    }
}

void func_131()
{
    if (global6 != 0xf3 && global6 != 0xf5)
    {
        ArticleModule(0x2712, WorkModule(0x6, 0x11000002));
    }
}

int func_132()
{
    StatusModule(0x5, 0x2, 0x58, 0x7, 0, 0, 0, 0xc, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0x1, 0, 0x1, 0, 0x2, 0, 0);
    return 0;
}

void func_133()
{
    if (global9 >= 1.0f)
    {
        WorkModule(0xa, 0x11000003);
        if (ControlModuleF(0x3) > WorkModuleF(0, 0x200001a))
        {
            WorkModule(0x2710, 0x21000013);
        }
    }
}

void func_134()
{
    float var0;
    float var1;
    float var2;
    var0 = GroundModuleF(0x7);
    PostureModule(0, -var0);
    PostureModule(0x2);
    func_22(0x93, 0, 1.0f);
    WorkModule(0x9, 0x10000044);
    WorkModule(0x19, 0x1f000008);
    if (!StopModule(0x1))
    {
        func_133();
    }
    global16 = func_133;
    BattleObject(0x6a);
    GroundModule(0x8, 0x1);
    var1 = KineticModuleF(0xa, 0x3);
    var2 = KineticModuleF(0xb, 0x3);
    WorkModule(0, var1, 0x1000006);
    WorkModule(0, var2, 0x1000007);
    func_78(func_136);
}

void func_135()
{
    float var0;
    float var1;
    float var2;
    var0 = KineticModuleF(0xa, 0x3);
    var1 = WorkModuleF(0, 0x3000016);
    if (func_13(var0) > var1)
    {
        if (var0 > 0)
        {
            var2 = var1 - var0;
        }
        else
        {
            var2 = -var1 - var0;
        }
        KineticModule(0x19, 0x3, var2, 0);
    }
}

void func_136()
{
    if (global9 >= 1.0f)
    {
        if (func_55())
        {
            func_135();
            return 0x1;
        }
        if (!GroundModule(0x2724))
        {
            func_16(0xe, 0);
            return;
        }
        if (WorkModule(0x10, 0x2100000f))
        {
            func_16(0xe, 0);
            return;
        }
        if (ControlModule(0x2710, 0) || ControlModule(0x2710, 0x1) || ControlModule(0x2710, 0x2) || WorkModule(0x6, 0x11000003) <= 0)
        {
            func_16(0xf4, 0);
            return;
        }
        if (global24 & 0x100000)
        {
            func_16(0xf4, 0);
            return;
        }
        if (ControlModuleF(0x1) <= WorkModuleF(0, 0x200001a) && WorkModule(0x10, 0x21000013))
        {
            func_16(0xe, 0);
            return;
        }
    }
}

void func_137()
{
    float var0;
    float var1;
    if (global6 != 0xf4)
    {
        ArticleModule(0x2712, WorkModule(0x6, 0x11000002));
        PostureModule(0x4, 0, 0, 0);
        if (global9 <= 5.0f)
        {
            var0 = WorkModuleF(0, 0x1000006);
            var1 = WorkModuleF(0, 0x1000007);
            KineticModule(0x11, 0x3, var0, var1);
        }
    }
}

int func_138()
{
    StatusModule(0x5, 0x2, 0x59, 0x7, 0, 0, 0x50000, 0x14, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0x1, 0, 0x1, 0, 0x2, 0, 0);
    return 0;
}

void func_139()
{
    float var0;
    float var1;
    float var2;
    WorkModule(0x19, 0x1f000008);
    ArticleModule(0x2713, WorkModule(0x6, 0x11000002), WorkModule(0x6, 0x11000003));
    BattleObject(0x72, 0x94);
    var0 = (float)MotionModule(0);
    var1 = (float)WorkModule(0x6, 0x11000005);
    MotionModule(0x4, var0 / var1);
    var2 = (float)WorkModule(0x6, 0x11000006);
    if (var2 >= 0)
    {
        MotionModule(0x2713, var2);
    }
    GroundModule(0x8, 0x1);
    func_78(func_140);
}

void func_140()
{
    if (func_55())
    {
        func_135();
        return 0x1;
    }
    if (WorkModule(0x10, 0x2100000f))
    {
        func_16(0xe, 0);
        return;
    }
    if (!GroundModule(0x2724))
    {
        func_16(0xe, 0);
        return;
    }
}

void func_141()
{
    ArticleModule(0x2712, WorkModule(0x6, 0x11000002));
    PostureModule(0x4, 0, 0, 0);
}

int func_142()
{
    StatusModule(0x5, 0x2, 0x13, 0x5, 0, 0, 0, 0x24, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0x1, 0, 0x1, 0, 0x2, 0, 0);
    return 0;
}

void func_143(int arg0, int arg1)
{
    if (!WorkModule(0x10, 0x21000010) && global9 >= (float)WorkModule(0x6, 0x11000007))
    {
        ArticleModule(0x2714, arg0, arg1);
        WorkModule(0x2710, 0x21000010);
    }
}

void func_144(int arg0)
{
    WorkModule(0x19, 0x1f000008);
    if (!StopModule(0x1))
    {
        (*arg0)();
    }
    global16 = arg0;
    func_78(func_145);
}

void func_145()
{
    if (func_55())
    {
        return 0x1;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        if (global18 == 0x2)
        {
            func_16(0xe, 0);
            return;
        }
    }
}

void func_146()
{
    ArticleModule(0x2712, WorkModule(0x6, 0x11000002));
}

int func_147()
{
    StatusModule(0x5, 0x1, 0x14, 0x4, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x4002, 0, 0);
    return 0;
}

int func_148()
{
    StatusModule(0x5, 0x1, 0x15, 0x4, 0, 0x1, 0, 0, 0, 0x60);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x4002, 0, 0);
    return 0;
}

int func_149()
{
    StatusModule(0x5, 0x1, 0x15, 0x4, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x1004002, 0, 0);
    return 0;
}

int func_150()
{
    StatusModule(0x5, 0x1, 0x16, 0x4, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1, 0x4002, 0x10, 0x200);
    return 0;
}

int func_151()
{
    StatusModule(0x5, 0x1, 0x16, 0x4, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x4002, 0, 0);
    return 0;
}

int func_152()
{
    StatusModule(0x5, 0x1, 0x16, 0x4, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x4002, 0, 0x1);
    return 0;
}

int func_153()
{
    StatusModule(0x5, 0x1, 0x15, 0x4, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x4002, 0, 0);
    return 0;
}

int func_154()
{
    StatusModule(0x5, 0x2, 0x4, 0x5, 0x4, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0, 0, 0x4);
    return 0;
}

int func_155()
{
    StatusModule(0x5, 0x2, 0x5, 0x5, 0x4, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0, 0, 0);
    return 0;
}

int func_156()
{
    StatusModule(0x5, 0x2, 0x17, 0x5, 0, 0x1, 0x82, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x4, 0, 0);
    return 0;
}

int func_157()
{
    StatusModule(0x5, 0x2, 0x13, 0x5, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_158()
{
    WorkModule(0x7, WorkModule(0x6, 0x1200006d), 0x11000002);
    func_78(func_159);
}

void func_159()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (!GroundModule(0x2724))
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (WorkModule(0x6, 0x11000002) <= 0 || GroundModuleF(0x2) <= GroundModuleF(0x11))
    {
        func_16(0x73, 0);
        return 0x1;
    }
    if (global18 == 0)
    {
        func_16(0, 0);
        return 0x1;
    }
}

void func_160()
{
    MotionModule(0x4, 1.0f);
}

void func_161()
{
    func_162();
    func_78(func_164);
}

void func_162()
{
    func_160();
}

int func_163()
{
    if (global18 == 0)
    {
        func_16(0, 0);
        return 0x1;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (!GroundModule(0x2724))
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (MotionModule(0x2712))
    {
        func_16(0x74, 0);
        return 0x1;
    }
    func_197();
    return 0;
}

void func_164()
{
    if (func_163())
    {
        return 0x1;
    }
}

void func_165()
{
    BattleObject(0xa, 0x1, WorkModule(0x6, 0x12000095));
    WorkModule(0x16, 0x1e00004c);
    WorkModule(0x16, 0x1e00004b);
    WorkModule(0x16, 0x1e000046);
    WorkModule(0x16, 0x1e000047);
    WorkModule(0x16, 0x1e000048);
    WorkModule(0x16, 0x1e000049);
    WorkModule(0x16, 0x1e000002);
    func_22(0x104, 0, 1.0f);
    WorkModule(0, 0, 0);
    WorkModule(0x12, 0x20000003);
    if (global5 == 0xf4)
    {
        if (GroundModule(0x2724))
        {
            GroundModule(0x12);
        }
    }
    func_78(func_166);
}

void func_166()
{
    if (global18 == 0)
    {
        func_16(0, 0);
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (!GroundModule(0x2724))
    {
        func_16(0xe, 0);
        return;
    }
    if (WorkModule(0x2712, 0x2100000f))
    {
        func_16(0x4c, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e00004c))
    {
        if (global18 == 0x1)
        {
            if (global38 & 0x10)
            {
                func_16(0x78, 0x1);
                return;
            }
        }
    }
    if (WorkModule(0x15, 0x1e00004b))
    {
        if (global18 == 0x1)
        {
            if (WorkModule(0x2712, 0x21000011))
            {
                func_16(0x78, 0x1);
                return;
            }
        }
    }
    if (WorkModule(0x15, 0x1e000046))
    {
        if (global18 == 0x1)
        {
            if (global38 & 0x1)
            {
                func_16(0x75, 0x1);
                return;
            }
        }
    }
    if (WorkModule(0x15, 0x1e000047))
    {
        if (global18 == 0x1)
        {
            if (global38 & 0x4)
            {
                func_16(0x75, 0x1);
                return;
            }
        }
    }
    if (WorkModule(0x15, 0x1e000048))
    {
        if (global18 == 0x1)
        {
            if (global38 & 0x40)
            {
                func_16(0x77, 0x1);
                return;
            }
        }
    }
    if (WorkModule(0x15, 0x1e000049))
    {
        if (global18 == 0x1)
        {
            if (WorkModule(0x2712, 0x2100000d))
            {
                func_16(0x76, 0);
                return;
            }
        }
    }
    if (WorkModule(0x15, 0x1e000002))
    {
        if (global18 == 0x1)
        {
            if (WorkModule(0x2712, 0x21000013))
            {
                func_16(0x108, 0);
                return;
            }
        }
    }
    if (WorkModule(0x15, 0x1e000002))
    {
        if (global18 == 0x1)
        {
            if (WorkModule(0x2712, 0x2100000e))
            {
                func_16(0xe, 0);
                return;
            }
        }
    }
    func_197();
}

void func_167()
{
    func_22(0x106, 0, 1.0f);
    BattleObject(0xd, 0x2, 0x52);
    func_78(func_168);
}

void func_168()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return;
        }
        if (global18 == 0x1)
        {
            func_16(0xe, 0);
            return;
        }
    }
    func_197();
}

void func_169()
{
    func_22(0x105, 0, 1.0f);
    func_78(func_170);
}

void func_170()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (global18 == 0x2)
    {
        printf("status_CliffClimb_Main SITUATION_KIND_AIR");
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return;
        }
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0x1)
        {
            func_16(0xe, 0);
            return;
        }
    }
    func_197();
}

void func_171()
{
    func_22(0x107, 0, 1.0f);
    func_78(func_172);
}

void func_172()
{
    float var0;
    float var1;
    float var2;
    float var3;
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (global18 == 0x2)
    {
        if (GroundModule(0x2716) == 0)
        {
            func_16(0xe, 0);
            return;
        }
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return;
        }
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0x1)
        {
            func_16(0xe, 0);
            return;
        }
    }
    var0 = GroundModuleF(0x2);
    var1 = PostureModuleF(0x2);
    if (var1 > var0 - 10.0f)
    {
        var2 = KineticModuleF(0xa, 0);
        var3 = KineticModuleF(0xb, 0);
        if (var3 < 0)
        {
            KineticModule(0x11, 0, var2, 0);
        }
    }
    func_197();
}

void func_173()
{
    ControlModule(0x271f);
    ControlModule(0x271b);
    func_76();
    WorkModule(0x16, 0x1e00004b);
    func_22(0x108, 0, 1.0f);
    func_78(func_174);
}

void func_174()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e00004b))
    {
        if (MotionModule(0x2712))
        {
            func_16(0x79, 0);
            return;
        }
    }
    func_197();
}

void func_175()
{
    ControlModule(0x271f);
    func_40();
    func_564();
    WorkModule(0x1a, 0x1f00000a);
    WorkModule(0x1a, 0x1f00000b);
    WorkModule(0x1a, 0x1f00000e);
    func_22(0x109, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_179();
    }
    global16 = func_179;
    func_78(func_176);
}

void func_176()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (global9 > 1.0f)
    {
        if (func_41())
        {
            return;
        }
    }
    if (func_565())
    {
        return;
    }
    if (func_58())
    {
        return 0x1;
    }
    if (func_59())
    {
        return 0x1;
    }
    if (func_63())
    {
        return 0x1;
    }
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return;
    }
    if (global9 > 1.0f)
    {
        func_555();
    }
    func_197();
}

void func_177()
{
    func_175();
    func_78(func_178);
}

void func_178()
{
    func_176();
}

void func_179()
{
    if (WorkModule(0x6, 0x11000003) <= 0)
    {
        WorkModule(0x19, 0x1f00000a);
        WorkModule(0x19, 0x1f00000b);
        WorkModule(0x19, 0x1f00000e);
        func_105();
        func_104();
    }
    func_550();
}

void func_180()
{
    int var0;
    int var1;
    float var2;
    float var3;
    float var4;
    float var5;
    WorkModule(0x7, 0, 0x10000057);
    var0 = 0xcd;
    if (global1 == 0x3a || global1 == 0x3c)
    {
        var0 = 0x24;
    }
    var1 = WorkModule(0x6, 0x1200007d);
    var2 = (float)MotionModule(0, var0);
    func_22(var0, 0, var2 / (float)var1);
    var3 = WorkModuleF(0, 0x200007b);
    var4 = WorkModuleF(0, 0x200007c);
    var5 = WorkModuleF(0, 0x3000018);
    KineticModule(0x2710, -var3, var4 * var5, 0);
    ShakeModule(0, 0, 0x5, 0, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_182();
    }
    global16 = func_182;
    func_78(func_181);
}

void func_181()
{
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return;
    }
    if (func_41())
    {
        return;
    }
}

void func_182()
{
    int var0;
    int var1;
    var0 = WorkModule(0x6, 0x10000057);
    var1 = WorkModule(0x6, 0x1200007d);
    if (var0 >= var1)
    {
        func_40();
        if (var0 == var1)
        {
            KineticModule(0xe, 0x2, 0, 0, 0, 0, 0, 0);
            KineticModule(0xb, 0x2);
        }
    }
    WorkModule(0x9, 0x10000057);
    func_550();
}

void func_183()
{
    KineticModule(0x2717, 0x2);
    WorkModule(0x16, 0x1e00000d);
    func_22(0x102, 0, 1.0f);
    func_78(func_184);
}

void func_184()
{
    if (func_56())
    {
        return 0x1;
    }
    if (global18 == 0x2)
    {
        if (MotionModule(0x2712) == 0x1)
        {
            func_16(0x4c, 0);
            return;
        }
    }
    if (WorkModule(0x15, 0x1e00000d))
    {
        if (global18 == 0)
        {
            func_16(0x4d);
            return;
        }
    }
    if (global9 == 8.0f)
    {
        KineticModule(0x2718, 0x2);
    }
}

void func_185()
{
    
}

void func_186()
{
    
}

void func_187()
{
    
}

void func_188()
{
    
}

void func_189()
{
    
}

void func_190()
{
    
}

void func_191()
{
    if (global6 != 0x79)
    {
        if (global18 != 0x1 && global18 != 0x2)
        {
            WorkModule(0x7, 0, 0x10000044);
        }
        if (global18 == 0 || global18 == 0x6)
        {
            WorkModule(0x11, 0x20000059);
        }
    }
}

void func_192()
{
    if (global18 == 0 || global18 == 0x6)
    {
        WorkModule(0x11, 0x20000059);
    }
}

void func_193()
{
    if (global18 == 0 || global18 == 0x6)
    {
        WorkModule(0x11, 0x20000059);
    }
}

void func_194()
{
    
}

void func_195()
{
    
}

void func_196()
{
    int var0;
    int var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    float var7;
    float var8;
    float var9;
    float var10;
    int var11;
    float var12;
    float var13;
    float var14;
    float var15;
    int var16;
    float var17;
    float var18;
    float var19;
    float var20;
    int var21;
    if (GroundModule(0x2724))
    {
        var0 = 0x1;
        var1 = 0;
        if (global4 == 0x73)
        {
            var2 = PostureModuleF(0);
            var3 = GroundModuleF(0x1);
            var4 = GroundModuleF(0x2);
            var5 = PostureModuleF(0x3);
            var6 = MotionModuleF(0x7);
            var7 = MotionModuleF(0x8);
            var8 = var3 + var7 * var2;
            var9 = var4 + var6;
            var10 = var5;
            ControlModule(0x2714, 0xd, 0);
            if (WorkModule(0x10, 0x20000059) == 0x1)
            {
                HitModule(0, 0x2);
            }
            var1 = 0x1;
        }
        else if (global4 == 0x75 || global4 == 0x76 || global4 == 0x77 || global4 == 0x78)
        {
            var1 = 0x1;
        }
        else if (global4 == 0x74)
        {
            var11 = (int)((float)WorkModule(0x6, 0x1200006f) * WorkModuleF(0, 0x30000fc));
            WorkModule(0x7, var11, 0x11000002);
            if (WorkModule(0x10, 0x20000059) == 0x1)
            {
                var12 = (float)WorkModule(0x6, 0x12000076);
                var13 = (float)WorkModule(0x6, 0x12000077);
                var14 = (float)WorkModule(0x6, 0x12000078);
                var15 = (float)WorkModule(0x6, 0x12000079);
                var16 = WorkModule(0x6, 0x1200007a);
                var17 = (float)WorkModule(0x6, 0x10000055);
                var18 = var12 * var17 / var13;
                if (var18 > var12)
                {
                    var18 = var12;
                }
                else if (var18 < (float)0)
                {
                    var18 = (float)0;
                }
                var19 = DamageModuleF(0);
                var20 = var14 - var14 * var19 / var15;
                if (var20 > var14)
                {
                    var20 = var14;
                }
                else if (var20 < (float)0)
                {
                    var20 = (float)0;
                }
                var21 = (int)(var18 + var20);
                if (var21 < var16)
                {
                    var21 = var16;
                }
                HitModule(0x2, var21);
                WorkModule(0x12, 0x20000059);
            }
            var1 = 0x1;
        }
        else if (global4 == 0x79)
        {
            var0 = 0;
        }
        if (var0 == 0x1)
        {
            WorkModule(0x11, 0x20000002);
        }
        if (var1 == 0x1)
        {
            GroundModule(0x2717, 0xe, 0x1);
        }
    }
}

void func_197()
{
    if (!global3)
    {
        func_199();
    }
}

void func_198()
{
    float var0;
    float var1;
    float var2;
    if (global4 == 0x74)
    {
        var0 = WorkModuleF(0, 0x2000071);
        if (func_13(global48) >= var0 || func_13(global32) >= var0)
        {
            if (global32 >= WorkModuleF(0, 0x200001f) && global47 < WorkModule(0x6, 0x12000020))
            {
                if (WorkModule(0x10, 0x21000010))
                {
                    WorkModule(0x11, 0x21000011);
                }
            }
            else if (WorkModule(0x10, 0x21000010))
            {
                var1 = ControlModuleF(0x4);
                var2 = WorkModuleF(0, 0x2000072);
                if (var1 > var2)
                {
                    if (global32 >= WorkModuleF(0, 0x200001f))
                    {
                        WorkModule(0x11, 0x2100000d);
                    }
                }
                else if (var1 > -var2 && global48 * PostureModuleF(0) >= 0)
                {
                    WorkModule(0x11, 0x2100000d);
                }
                else
                {
                    WorkModule(0x11, 0x2100000e);
                }
            }
        }
        else
        {
            WorkModule(0x11, 0x21000010);
        }
        if (WorkModule(0x6, 0x11000002) > 0)
        {
            WorkModule(0xa, 0x11000002);
        }
        if (WorkModule(0x6, 0x11000002) <= 0)
        {
            WorkModule(0x11, 0x2100000f);
        }
    }
}

void func_199()
{
    int var0;
    if (global4 == 0x74)
    {
        if (GroundModule(0x2722, 0x8))
        {
            func_20(0);
            func_16(0, 0);
        }
    }
    else if (global4 == 0x74 || global4 == 0x73 || global4 == 0x75 || global4 == 0x76 || global4 == 0x77 || global4 == 0x78)
    {
        if (GroundModule(0x2724))
        {
            var0 = 0;
            if (KineticModule(0x9, 0))
            {
                if (MotionModuleF(0x8) >= 0.30000001192092896f && MotionModuleF(0x7) >= -0.029999999329447746f)
                {
                    var0 = 0x1;
                }
            }
            if (var0)
            {
                KineticModule(0xa, 0);
                GroundModule(0x2717, 0xe, 0);
                func_20(0);
                GroundModule(0x2710, 0x2);
                GroundModule(0x3);
                GroundModule(0x13);
                WorkModule(0x11, 0x21000012);
            }
        }
        else if (global18 == 0)
        {
            if (GroundModule(0x9) == 0x4)
            {
                KineticModule(0xa, 0);
                GroundModule(0x2717, 0xe, 0);
                GroundModule(0x2710, 0x2);
                WorkModule(0x11, 0x21000012);
            }
        }
        else if (global18 == 0x1)
        {
            func_20(0x2);
            func_16(0xe, 0);
        }
    }
}

void func_200(int arg0)
{
    if (WorkModule(0x10, 0x20000002))
    {
        WorkModule(0x7, WorkModule(0x6, 0x12000073), 0x10000003);
        HitModule(0x2, 0);
    }
    WorkModule(0x2711, 0x20000002);
    if (arg0)
    {
        WorkModule(0x12, 0x20000002);
        GroundModule(0x13);
        HitModule(0x2, 0);
    }
}

void func_201()
{
    func_200(func_202(global6));
}

int func_202(int arg0)
{
    if (arg0 == 0x73 || arg0 == 0x74 || arg0 == 0x75 || arg0 == 0x76 || arg0 == 0x77 || arg0 == 0x78)
    {
        return 0;
    }
    return 0x1;
}

void func_203()
{
    KineticModule(0xe, 0x5, 0, 0, 0, 0, 0, 0);
    func_204(0x103);
}

void func_204(int arg0)
{
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    if (GroundModule(0x2724))
    {
        BattleObject(0x6f);
        var1 = ModelModuleF(0, 0x3);
        var2 = ModelModuleF(0x1, 0x3);
        var3 = GroundModuleF(0x7);
        var3 = -var3;
        PostureModule(0, var3);
        GroundModule(0x2717, 0xe, 0x1);
        func_22(arg0, 0, 1.0f);
        MotionModule(0x4, 0);
        PostureModule(0x2);
        var4 = ModelModuleF(0x3, 0x3, var1);
        var5 = ModelModuleF(0x4, 0x3, var2);
        var6 = PostureModuleF(0x3);
        PostureModule(0x3, var4, var5, var6);
        GroundModule(0x2717, 0xe, 0x1);
        GroundModule(0x11);
        WorkModule(0x2711, 0x2100000b);
        BattleObject(0x55, 0x1, 0x1b);
    }
}

void func_205()
{
    WorkModule(0xa, 0x11000002);
}

void func_206()
{
    if (func_202(global6))
    {
        GroundModule(0x13);
        WorkModule(0x7, WorkModule(0x6, 0x12000073), 0x10000003);
        GroundModule(0x13);
    }
    PostureModule(0x4, 0, 0, 0);
}

void func_207()
{
    
}

void func_208()
{
    
}

void func_209()
{
    
}

void func_210(int arg0)
{
    float var1;
    float var2;
    float var3;
    if (StageData(0x10) > 10.0f)
    {
        return;
    }
    var1 = func_13(arg0);
    if (var1 > 0)
    {
        var2 = 1.0f - (var1 - 0) / 340.0f;
        var3 = (1.0f - 0.5f) * var2 + 0.5f;
        if (var3 > 1.0f)
        {
            var3 = 1.0f;
        }
        PostureModule(0x2713, var3);
    }
}

int func_211()
{
    StatusModule(0x5, 0x5, 0x33, 0, 0, 0, 0, 0, 0, 0x100);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0x3e2, 0, 0);
    return 0;
}

int func_212()
{
    StatusModule(0x5, 0x5, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0x403e0, 0, 0);
    return 0;
}

void func_213()
{
    func_214();
    func_78(func_215);
}

void func_214()
{
    HitModule(0x2710, 0x3);
    AreaModule(0x2710, 0);
    ItemModule(0x10);
    ShadowModule(0x1);
    BattleObject(0x29);
}

void func_215()
{
    if (WorkModule(0x10, 0x2100000d))
    {
        func_16(0x14c, 0);
        return 0x1;
    }
}

void func_216()
{
    MotionModule(0x1, 0, 0, 0, 0);
    AreaModule(0x2710, 0);
    CameraModule(0x2717, 0);
    HitModule(0x2710, 0x3);
    ItemModule(0xf, 0);
    VisibilityModule(0x2710, 0);
    BattleObject(0x29);
    ShadowModule(0x1);
    PhysicsModule(0x1);
    BattleObject(0x68, 0);
    func_78(func_217);
}

void func_217()
{
    
}

void func_218()
{
    
}

void func_219()
{
    CameraModule(0x2717, 0x1);
    HitModule(0x2710, 0);
    VisibilityModule(0x2710, 0x1);
    EffectModule(0x2733, 0, 0);
}

void func_220()
{
    int var0;
    int var1;
    int var2;
    float var3;
    float var4;
    int var5;
    float var6;
    float var7;
    float var8;
    float var9;
    float var10;
    float var11;
    float var12;
    float var13;
    float var14;
    float var15;
    int var16;
    float var17;
    int var18;
    int var19;
    int var20;
    int var21;
    float var22;
    int var23;
    int var24;
    int var25;
    int var26;
    int var27;
    float var28;
    int var29;
    float var30;
    float var31;
    int var32;
    float var33;
    float var34;
    float var35;
    float var36;
    float var37;
    float var38;
    float var39;
    float var40;
    float var41;
    float var42;
    float var43;
    int var44;
    int var45;
    float var46;
    float var47;
    float var48;
    int var49;
    float var50;
    float var51;
    float var52;
    float var53;
    int var54;
    int var55;
    float var56;
    float var57;
    float var58;
    float var59;
    int var60;
    int var61;
    float var62;
    float var63;
    float var64;
    float var65;
    float var66;
    float var67;
    float var68;
    float var69;
    float var70;
    float var71;
    float var72;
    float var73;
    float var74;
    float var75;
    float var76;
    float var77;
    float var78;
    float var79;
    WorkModule(0x7, 0, 0x1000002e);
    var0 = WorkModule(0x6, 0x10000000);
    var1 = WorkModule(0x6, 0x1000002d);
    var2 = 0;
    var3 = var4 = 0;
    var5 = WorkModule(0x10, 0x2000001a);
    if (var5 == 0x1)
    {
        var6 = WorkModuleF(0, 0x2c);
        var7 = WorkModuleF(0, 0x2d);
        var8 = WorkModuleF(0, 0x2e);
    }
    else
    {
        var6 = ModelModuleF(0, 0x3);
        var7 = ModelModuleF(0x1, 0x3);
        var8 = ModelModuleF(0x2, 0x3);
    }
    WorkModule(0x7, 0xffffffff, 0x11000008);
    WorkModule(0x7, 0xffffffff, 0x11000009);
    if (var5)
    {
        var9 = StageData(0x2);
        var10 = StageData(0x3);
        var11 = StageData(0);
        var12 = StageData(0x1);
        var13 = var6;
        var14 = var7;
        var13 = StageData(0x14, var6, var7, 0x1000010);
        var14 = WorkModuleF(0, 0x1000010);
        var15 = WorkModuleF(0, 0x200012c);
        if (sys_7(0x13))
        {
            var15 = 0;
        }
        var16 = GroundModule(0x14, var6, var7, var8, 0, var15);
        if (var16 == 0xffffffff)
        {
            if (var1 != 0xffffffff)
            {
                if (var1 == 0)
                {
                    var14 = var9 + 0.009999999776482582f;
                }
                else if (var1 == 0x1)
                {
                    var14 = var10 - 0.009999999776482582f;
                }
                else if (var1 == 0x2)
                {
                    var13 = var11 - 0.009999999776482582f;
                }
                else if (var1 == 0x3)
                {
                    var13 = var12 + 0.009999999776482582f;
                }
                var6 = StageData(0x15, var13, var14, 0x1000010);
                var7 = WorkModuleF(0, 0x1000010);
                var16 = GroundModule(0x14, var6, var7, var8, 0, WorkModuleF(0, 0x200012c));
            }
        }
        if (var16 == 0x2)
        {
            if (var14 > var9)
            {
                var14 = var9;
            }
            if (var14 < var10)
            {
                var14 = var10;
            }
            var13 = var11 - 0.009999999776482582f;
            var3 = 50.0f;
            var6 = StageData(0x15, var13, var14, 0x1000010);
            var7 = WorkModuleF(0, 0x1000010);
            func_226(var6, var7, var8, 0, 0x1);
        }
        else if (var16 == 0x3)
        {
            if (var14 > var9)
            {
                var14 = var9;
            }
            if (var14 < var10)
            {
                var14 = var10;
            }
            var13 = var12 + 0.009999999776482582f;
            var3 = -50.0f;
            var6 = StageData(0x15, var13, var14, 0x1000010);
            var7 = WorkModuleF(0, 0x1000010);
            var17 = 180.0f * M_PI / (float)0xb4;
            func_226(var6, var7, var8, var17, 0x1);
        }
        else if (var16 == 0x1)
        {
            if (var13 > var12)
            {
                var13 = var12;
            }
            if (var13 < var11)
            {
                var13 = var11;
            }
            var14 = var10 - 0.009999999776482582f;
            var4 = 70.0f;
            var6 = StageData(0x15, var13, var14, 0x1000010);
            var7 = WorkModuleF(0, 0x1000010);
            var17 = 90.0f * M_PI / (float)0xb4;
            func_226(var6, var7, var8, var17, 0x1);
        }
        else if (var16 == 0)
        {
            if (var13 > var12)
            {
                var13 = var12;
            }
            if (var13 < var11)
            {
                var13 = var11;
            }
            var14 = var9 + 0.009999999776482582f;
            var4 = -60.0f;
            var6 = StageData(0x15, var13, var14, 0x1000010);
            var7 = WorkModuleF(0, 0x1000010);
            if (sys_7(0x11) == 0 && WorkModule(0x10, 0x20000027) == 0)
            {
                if (sys_7(0x12) == 0)
                {
                    var2 = 0;
                }
                else
                {
                    var2 = 0x1;
                }
            }
            else
            {
                var2 = 0x1;
            }
            var18 = 0;
            var19 = sys_7(0x7);
            var20 = FighterUtil(0x15);
            var21 = FighterUtil(0x16);
            if (var21 >= randi(0, 0x64) + 0x1)
            {
                var18 = 0x1;
            }
            if (sys_7(0x8) == 0x3)
            {
                var18 = 0x1;
            }
            if (WorkModule(0x10, 0x2000005b))
            {
                var18 = 0;
            }
            if (FighterUtil(0x13) == 0xffffffff)
            {
                var18 = 0;
            }
            if (var18)
            {
                if (var19 <= 0)
                {
                    var22 = WorkModuleF(0, 0x3000131);
                    var23 = FighterUtil(0x11);
                    WorkModule(0, var22 + 0, 0x100000f);
                    WorkModule(0x7, var23, 0x1100000a);
                }
                else if (FighterUtil(0x12))
                {
                    var23 = FighterUtil(0x11);
                    var24 = WorkModule(0x6, 0x1100000a);
                    if (var23 != var24)
                    {
                        var18 = 0;
                    }
                }
                else
                {
                    var18 = 0;
                }
            }
            if (var18)
            {
                var2 = 0x2;
            }
            else if (var20 >= randi(0, 0x64) + 0x1)
            {
                var2 = 0x1;
            }
            if (sys_7(0x9) == 0)
            {
                if (var2 == 0x2)
                {
                    var2 = 0;
                }
            }
            if (sys_7(0xa) == 0)
            {
                if (var2 == 0x1)
                {
                    var2 = 0;
                }
            }
            if (sys_7(0x4))
            {
                var2 = 0;
            }
            if (global5 == 0x124)
            {
                var2 = 0;
            }
            if (WorkModule(0x10, 0x20000061) && sys_7(0x8) == 0)
            {
                var2 = 0;
                WorkModule(0x2711, 0x20000061);
            }
            if (WorkModule(0x10, 0x20000062))
            {
                var2 = 0;
                WorkModule(0x2711, 0x20000062);
            }
            if (sys_7(0x8) == 0x1)
            {
                var2 = 0;
            }
            else if (sys_7(0x8) == 0x2)
            {
                var2 = 0x1;
            }
            var17 = 270.0f * M_PI / (float)0xb4;
            func_226(var6, var7, var8, var17, 0x1);
        }
    }
    else if (var1 == 0x6)
    {
        func_226(var6, var7, var8, var17, 0x1);
    }
    WorkModule(0x7, var2, 0x1000002e);
    if (var2 == 0)
    {
        CameraModule(0x2, 0);
        VisibilityModule(0x2710, 0);
        func_22(0, 0, 1.0f);
        SoundModule(0x2718, 0x47);
        var25 = 0x47;
        if (global1 == 0x32)
        {
            var25 = 0x23d00a0;
        }
        SoundModule(0x2710, var25, 0x1, 0x1, 0x1);
        var26 = WorkModule(0x6, 0x1300004c);
        var27 = SoundModule(0x2727, 0);
        if (var26 != 0 && randi(0, var26) == 0)
        {
            var27 = SoundModule(0x2727, 0x1);
        }
        SoundModule(0x2710, var27, 0x1, 0x1, 0x1);
        if (sys_7(0xf))
        {
            CameraModule(0x3, 0x6);
        }
        else
        {
            CameraModule(0x3, 0x5);
        }
        func_225();
        if (var5)
        {
            var28 = WorkModuleF(0, 0x200012c);
            var29 = EffectModule(0x1e, var6, var7, var8, var28);
            var30 = EffectModuleF(0, var6, var7, var8, var28);
            var31 = 1.0f;
            if (var29 == 0x1)
            {
                var31 = WorkModuleF(0, 0x200012d);
            }
            EffectModule(0x3, 0x1000016, var6, var7, var8, 0, 0, M_PI * var30, var31 * 1.0f, 0, FighterUtil(0x8));
            if (global1 == 0x32)
            {
                var3 = 70.0f * MathF(0x5, -3.1415927410125732f * var30);
                var4 = 70.0f * MathF(0x4, -3.1415927410125732f * var30);
                var32 = WorkModule(0x6, 0x1000003c);
                if (var32 < 0)
                {
                    var32 = 0;
                }
                else if (var32 > 0x7)
                {
                    var32 = 0x7;
                }
                EffectModule(0x3, 0x3320028 + var32, var6 + var3, var7 + var4, var8, 0, 0, 0, var31 * 1.0f, 0, 0xffffffff);
            }
            var33 = MathF(0x5, M_PI * var30);
            var34 = MathF(0x4, M_PI * var30);
            var35 = var33;
            var36 = -var34 * 16.0f / 9.0f;
            var37 = -var33;
            var38 = var34 * 16.0f / 9.0f;
            var39 = 0.5f;
            var40 = 1.5f;
            var41 = 0.5f;
            var42 = 1.5f;
            if (var30 > 0.4000000059604645f && var30 < 0.6000000238418579f || var30 > 1.399999976158142f && var30 < 1.600000023841858f)
            {
                var35 = -1.0f;
                var36 = 0;
                var37 = 1.0f;
                var38 = 0;
                var39 *= 9.0f / 16.0f;
                var40 *= 9.0f / 16.0f;
                var41 *= 9.0f / 16.0f;
                var42 *= 9.0f / 16.0f;
            }
            EffectModule(0x2735, 0, var35, var36, var37, var38, var39, var40, var41, var42, 0x1, 0x2);
            var43 = PostureModuleF(0);
            var44 = WorkModule(0x6, 0x1200012b) + 0x8;
            CameraModule(0x271e, var0, var43, var44);
            CameraModule(0x2, 0);
        }
        else
        {
            var45 = WorkModule(0x6, 0x130000cb);
            var46 = ModelModuleF(0, var45);
            var47 = ModelModuleF(0x1, var45);
            var48 = ModelModuleF(0x2, var45);
            EffectModule(0x3, 0x10000ae, var46, var47, var48, 0, 0, 0, 1.0f, 0, 0xffffffff);
            BattleObject(0x7f);
            if (global1 == 0x32)
            {
                var32 = WorkModule(0x6, 0x1000003c);
                if (var32 < 0)
                {
                    var32 = 0;
                }
                else if (var32 > 0x7)
                {
                    var32 = 0x7;
                }
                EffectModule(0x3, 0x3320028 + var32, var46, var47, var48, 0, 0, 0, 1.0f, 0, 0xffffffff);
            }
        }
    }
    else if (var2 == 0x1)
    {
        WorkModule(0x7, WorkModule(0x6, 0x12000130), 0x11000003);
        WorkModule(0x7, 0, 0x11000002);
        var27 = SoundModule(0x2727, 0x2);
        SoundModule(0x2710, var27, 0x1, 0x1, 0x1);
        if (var49 == 0xc5)
        {
            WorkModule(0x2710, 0x2100000e);
            ControlModule(0x19, 0x2, 0, 0, 0x3);
        }
        else
        {
            func_22(0x2e, 0, 1.0f);
        }
        WorkModule(0x2710, 0x2000001f);
        WorkModule(0x7, 0, 0x10000021);
        var50 = (StageData(0xc) * WorkModuleF(0, 0x2000134) - PostureModuleF(0x2)) / (float)WorkModule(0x6, 0x12000131);
        WorkModule(0, var50 + 0, 0x1000007);
        var51 = WorkModuleF(0, 0x2000133) / (float)WorkModule(0x6, 0x12000131);
        WorkModule(0, var51 + 0, 0x1000008);
        WorkModule(0, PostureModuleF(0x7) + 0, 0x1000011);
    }
    else if (var2 == 0x2)
    {
        WorkModule(0x7, WorkModule(0x6, 0x12000137), 0x11000003);
        WorkModule(0x7, 0, 0x11000002);
        WorkModule(0x2710, 0x2100000f);
        if (var49 == 0xc5)
        {
            WorkModule(0x2710, 0x2100000e);
            ControlModule(0x19, 0x2, 0, 0, 0x3);
        }
        else
        {
            func_22(0x2e, 0, 1.0f);
        }
        var52 = 0;
        var53 = 0;
        var54 = WorkModule(0x6, 0x11000008);
        if (var54 == 0)
        {
            var52 = -10.0f;
        }
        else if (var54 == 0x1)
        {
            var52 = 0;
        }
        else if (var54 == 0x2)
        {
            var52 = 10.0f;
        }
        var55 = 0xb4;
        var56 = (float)(randi(0, var55 * 0x2) - var55);
        var57 = WorkModuleF(0, 0x300012f) - 90.0f;
        var58 = WorkModuleF(0, 0x3000130) - 90.0f;
        var59 = var58 - var57;
        var60 = (int)(var59 / ((float)0x3 + 0));
        var61 = FighterUtil(0x14);
        if (var61 == 0)
        {
            var56 = var57 + (float)randi(0, var60) + 0;
        }
        else if (var61 == 0x1)
        {
            var56 = var57 + (float)(var60 * 0x1) + (float)randi(0, var60) + 0;
        }
        else if (var61 == 0x2)
        {
            var56 = var57 + (float)(var60 * 0x2) + (float)randi(0, var60) + 0;
        }
        WorkModule(0, var56 + 0, 0x100000e);
        var62 = ModelModuleF(0, 0);
        var63 = ModelModuleF(0x1, 0);
        var64 = ModelModuleF(0, 0x2);
        var65 = ModelModuleF(0x1, 0x2);
        var66 = MathF(0x3, var62 - var64, var63 - var65, 0);
        var67 = var66;
        var68 = var66;
        var67 -= WorkModuleF(0, 0x300012e);
        var68 -= WorkModuleF(0, 0x300012e);
        var53 -= MathF(0x4, var56 * M_PI / (float)0xb4) * var68;
        var53 += WorkModuleF(0, 0x3000132);
        var69 = WorkModuleF(0, 0x100000f);
        var70 = var52 + WorkModuleF(0, 0x200013c);
        var71 = var53 + WorkModuleF(0, 0x200013d);
        var72 = WorkModuleF(0, 0x200013e);
        WorkModule(0, var70 + 0, 0x100000a);
        WorkModule(0, var71 + 0, 0x100000b);
        WorkModule(0, var72 + 0, 0x100000c);
        var73 = var52;
        var74 = var53;
        var75 = -30.0f - var69;
        var76 = (float)WorkModule(0x6, 0x12000138);
        printf("*****************************$FL_end_x:%f\n*******************************", var73);
        var77 = (var73 - var70) / var76;
        var78 = (var74 - var71) / var76;
        var79 = (var75 - var72) / var76;
        WorkModule(0, var77 + 0, 0x1000006);
        WorkModule(0, var78 + 0, 0x1000007);
        WorkModule(0, var79 + 0, 0x1000008);
        func_22(0xfa, 0, 0);
        MotionModule(0x1b, 0);
        MotionModule(0x4, 0);
        MotionModule(0x2713, 0);
        CameraModule(0x2, 0);
        BattleObject(0x68, 0x1, 0.25f, 0.25f, 0.25f, 0.25f);
        BattleObject(0x83, 0x1);
    }
    WorkModule(0x7, 0, 0x11000006);
}

void func_221()
{
    int var0;
    int var1;
    int var2;
    int var3;
    float var4;
    float var5;
    float var6;
    float var7;
    int var8;
    float var9;
    float var10;
    float var11;
    float var12;
    float var13;
    float var14;
    float var15;
    float var16;
    float var17;
    var0 = WorkModule(0x6, 0x11000006);
    var1 = WorkModule(0x6, 0x1000002e);
    if (var0 == 0)
    {
        if (var1 == 0)
        {
            var0 = func_222();
        }
        else if (var1 == 0x1)
        {
            var2 = WorkModule(0x6, 0x11000002);
            if (var2 == 0)
            {
                var3 = WorkModule(0x6, 0x11000003);
                var3++;
                WorkModule(0x7, var3, 0x11000003);
                if (var3 > WorkModule(0x6, 0x12000131))
                {
                    var4 = PostureModuleF(0x1);
                    var5 = PostureModuleF(0x2);
                    var6 = PostureModuleF(0x3);
                    WorkModule(0x7, 0x1, 0x11000002);
                    EffectModule(0x3, 0x1000069, var4, var5, var6, 0, 0, 0, WorkModuleF(0, 0x3000031), 0, 0);
                    SoundModule(0x2710, 0x58, 0, 0x1, 0x1);
                    var0 = func_222();
                }
                else
                {
                    var4 = PostureModuleF(0x1);
                    var5 = PostureModuleF(0x2);
                    var6 = PostureModuleF(0x3);
                    var5 += WorkModuleF(0, 0x1000007);
                    var6 += WorkModuleF(0, 0x1000008);
                    PostureModule(0x3, var4, var5, var6);
                    func_210(var6);
                    if (WorkModule(0x10, 0x2100000e))
                    {
                        var7 = WorkModuleF(0, 0x1000009);
                        var7 += WorkModuleF(0, 0x2000135);
                        WorkModule(0, var7 + 0, 0x1000009);
                        FighterUtil(0x6, var7);
                    }
                }
            }
        }
        else if (var1 == 0x2)
        {
            var3 = WorkModule(0x6, 0x11000003);
            var3++;
            WorkModule(0x7, var3, 0x11000003);
            if (WorkModule(0x10, 0x2100000e))
            {
                var7 = WorkModuleF(0, 0x1000009);
                var7 += WorkModuleF(0, 0x2000146);
                WorkModule(0, var7 + 0, 0x1000009);
                FighterUtil(0x6, var7);
            }
            var2 = WorkModule(0x6, 0x11000002);
            if (var2 == 0)
            {
                var8 = WorkModule(0x6, 0x12000138);
                if (var3 > var8)
                {
                    WorkModule(0x7, 0, 0x11000003);
                    WorkModule(0x7, 0x1, 0x11000002);
                    var9 = WorkModuleF(0, 0x100000a);
                    var10 = WorkModuleF(0, 0x100000b);
                    var11 = WorkModuleF(0, 0x100000c);
                    var11 *= 30.0f / StageData(0x10);
                    var4 = StageData(0x4, var9, var10, var11);
                    var5 = StageData(0x5, var9, var10, var11);
                    var6 = StageData(0x6, var9, var10, var11);
                    EffectModule(0x2732, 0x1, 0, 10.0f, 10.0f, var4, var5, var6, 0, 0);
                    CameraModule(0x3, 0x6);
                    func_225();
                    var4 = PostureModuleF(0x1);
                    var5 = PostureModuleF(0x2);
                    var6 = PostureModuleF(0x3);
                    var12 = 90.0f * M_PI / (float)0xb4;
                    func_226(var4, var5, var6, var12, 0);
                    SoundModule(0x2710, 0x143, 0x1, 0x1, 0x1);
                    func_22(0xfa, 0, 1.0f);
                    MotionModule(0x1b, 0);
                    FighterUtil(0x17);
                }
                else
                {
                    var13 = WorkModuleF(0, 0x100000a) + WorkModuleF(0, 0x1000006);
                    var14 = WorkModuleF(0, 0x100000b) + WorkModuleF(0, 0x1000007);
                    var15 = WorkModuleF(0, 0x100000c) + WorkModuleF(0, 0x1000008);
                    WorkModule(0, var13 + 0, 0x100000a);
                    WorkModule(0, var14 + 0, 0x100000b);
                    WorkModule(0, var15 + 0, 0x100000c);
                }
            }
            else if (var2 == 0x1)
            {
                if (var3 > 0x14)
                {
                    WorkModule(0x7, 0x2, 0x11000002);
                    WorkModule(0x7, 0, 0x11000003);
                    WorkModule(0, 0 + 0, 0x1000006);
                    WorkModule(0, WorkModuleF(0, 0x2000142) + 0, 0x1000007);
                    WorkModule(0, WorkModuleF(0, 0x2000145) + 0, 0x1000008);
                    WorkModule(0, 0 + 0, 0x1000007);
                    if (sys_7(0x5) == 0)
                    {
                        CameraModule(0x2721, 0x1);
                    }
                }
            }
            else if (var2 == 0x2)
            {
                if (var3 > 0x50)
                {
                    WorkModule(0x7, 0x3, 0x11000002);
                    WorkModule(0x7, 0, 0x11000003);
                    SoundModule(0x2710, 0x47, 0, 0x1, 0x1);
                    if (sys_7(0xf))
                    {
                        CameraModule(0x3, 0x6);
                    }
                    else
                    {
                        CameraModule(0x3, 0x5);
                    }
                    ControlModule(0x2714, 0xe, 0);
                    var0 = func_222();
                }
                else
                {
                    var16 = WorkModuleF(0, 0x1000007);
                    var17 = sys_35(0, var16, 0.03999999910593033f, WorkModuleF(0, 0x2000144), WorkModuleF(0, 0x300001a));
                    var16 += var17;
                    WorkModule(0, var16 + 0, 0x1000006);
                    var13 = WorkModuleF(0, 0x100000a);
                    var14 = WorkModuleF(0, 0x100000b) - var16;
                    var15 = WorkModuleF(0, 0x100000c);
                    WorkModule(0, var13 + 0, 0x100000a);
                    WorkModule(0, var14 + 0, 0x100000b);
                    WorkModule(0, var15 + 0, 0x100000c);
                    WorkModule(0, var16 + 0, 0x1000007);
                }
            }
        }
    }
    WorkModule(0x7, var0, 0x11000006);
    if (var0 == 0x2)
    {
        WorkModule(0x2710, 0x2100000d);
        if (sys_7(0x5) == 0)
        {
            if (sys_7(0x7) == 0)
            {
                CameraModule(0x2721, 0);
            }
        }
    }
}

int func_222()
{
    return 0x2;
}

void func_223()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    float var7;
    float var8;
    int var9;
    int var10;
    int var11;
    int var12;
    int var13;
    float var14;
    float var15;
    if (WorkModule(0x10, 0x2100000f))
    {
        var0 = WorkModuleF(0, 0x100000a);
        var1 = WorkModuleF(0, 0x100000b);
        var2 = WorkModuleF(0, 0x100000c);
        var2 *= 30.0f / StageData(0x10);
        var3 = StageData(0x4, var0, var1, var2);
        var4 = StageData(0x5, var0, var1, var2);
        var5 = StageData(0x6, var0, var1, var2);
        ModelModule(0x7, 0, var3, var4, var5);
        var6 = StageData(0x7);
        var7 = StageData(0x8);
        var8 = StageData(0x9);
        if (PostureModuleF(0) < 0)
        {
            var7 += 90.0f;
        }
        else
        {
            var7 -= 90.0f;
        }
        var9 = WorkModule(0x6, 0x11000006);
        var10 = WorkModule(0x6, 0x1000002e);
        var11 = WorkModule(0x6, 0x11000003);
        var12 = WorkModule(0x6, 0x11000002);
        var13 = WorkModule(0x6, 0x12000138);
        if (var9 == 0 && var10 == 0x2 && var12 == 0 && var11 <= var13)
        {
            var14 = WorkModuleF(0, 0x100000d);
            var15 = sys_8(0x2) * SlowModuleF(0);
            var14 += WorkModuleF(0, 0x2000310) * var15;
            WorkModule(0, var14 + 0, 0x100000d);
            var6 += var14;
        }
        var8 += WorkModuleF(0, 0x100000e);
        PostureModule(0x4, var6, var7, var8);
        if (var9 == 0 && var10 == 0x2)
        {
            if (var12 == 0)
            {
                
            }
            else if (var12 == 0x1)
            {
                EffectModule(0x2734, 0x1, 10.0f, 10.0f, var3, var4, var5, 0);
            }
        }
    }
}

void func_224()
{
    int var0;
    int var1;
    int var2;
    var0 = WorkModule(0x6, 0x11000005);
    if (var0 != 0)
    {
        EffectModule(0x6, var0);
        WorkModule(0x7, 0, 0x11000005);
    }
    var1 = WorkModule(0x6, 0x1000002e);
    var2 = (int)0;
    if (var1 == 0)
    {
        var2 = WorkModule(0x6, 0x1200012b);
    }
    else if (var1 == 0x1)
    {
        var2 = WorkModule(0x6, 0x1200012b);
    }
    else if (var1 == 0x2)
    {
        var2 = WorkModule(0x6, 0x1200013b);
    }
    WorkModule(0x7, var2, 0x1000002f);
    WorkModule(0x11, 0x20000000);
    if (var1 == 0x2)
    {
        BattleObject(0x83, 0);
    }
    else if (var1 == 0x1)
    {
        PostureModule(0x2713, WorkModuleF(0, 0x1000011));
    }
}

void func_225()
{
    FighterUtil(0x1c);
}

void func_226(int arg0, int arg1, int arg2, int arg3, int arg4)
{
    FighterUtil(0x1a, arg0, arg1, arg2, arg3, arg4);
}

int func_227()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0x403e2, 0, 0);
    return 0;
}

void func_228()
{
    WorkModule(0, 0.0f, 0x0f000315);   // Rebirth: up special's air use back (VAR_21, edge_hi_used_var: test 127)
    func_230();
    func_78(func_229);
}

void func_229()
{
    if (func_231())
    {
        return;
    }
    func_681();
    if (func_41())
    {
        return 0x1;
    }
    func_240();
}

void func_230()
{
    CameraModule(0x2719);
    BattleObject(0xa, 0x1);
    AreaModule(0x2710, 0);
    VisibilityModule(0x2710, 0x1);
    BattleObject(0x29);
    MotionModule(0x1, 0, 0, 1.0f, 0);
    if (!StopModule(0x1))
    {
        func_232();
    }
    global16 = func_232;
}

void func_231()
{
    if (WorkModule(0x6, 0x11000004) > WorkModule(0x6, 0x12000148))
    {
        func_16(0xe, 0);
        return 0x1;
    }
}

void func_232()
{
    if (WorkModule(0x10, 0x2100000d))
    {
        WorkModule(0x9, 0x11000004);
        if (global32 <= WorkModuleF(0, 0x200001a))
        {
            func_16(0xe, 0x1);
            return 0x1;
        }
        if (func_88() <= WorkModuleF(0, 0x2000006))
        {
            func_16(0xe, 0x1);
            return 0x1;
        }
        if (func_84() >= WorkModuleF(0, 0x2000001))
        {
            func_16(0xe, 0x1);
            return 0x1;
        }
        if (!WorkModule(0x10, 0x2100000e))
        {
            func_40();
            BattleObject(0xc, 0x1);
            WorkModule(0x11, 0x2100000e);
        }
    }
}

void func_233()
{
    
}

void func_234()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    int var6;
    int var7;
    float var8;
    int var9;
    var0 = PostureModuleF(0x1);
    var1 = PostureModuleF(0x2);
    var2 = PostureModuleF(0x3);
    var3 = var0;
    var4 = var1;
    var5 = var2;
    var6 = WorkModule(0x6, 0x10000000);
    if (WorkModule(0x10, 0x20000027))
    {
        
    }
    else if (WorkModule(0x10, 0x20000021))
    {
        
    }
    else
    {
        var7 = WorkModule(0x6, 0x12000147);
        CameraModule(0x2, 0);
        var0 = var0 + 0;
        var1 = var1 + 100.0f;
        var2 = 0;
        PostureModule(0x3, var0, var1, var2);
        WorkModule(0x7, 0, 0x11000002);
        WorkModule(0x7, var7, 0x11000003);
        WorkModule(0, var0, 0x1000006);
        WorkModule(0, var1, 0x1000007);
        WorkModule(0, var3, 0x1000008);
        WorkModule(0, var4, 0x1000009);
        WorkModule(0x11, 0x20000001);
        if (!WorkModule(0x10, 0x20000033))
        {
            var8 = PostureModuleF(0);
            var9 = (int)0;
            CameraModule(0x271f, var6, var3, var4 + (float)var9, var5, var8, var7, 0.09399999678134918f);
            func_237(var0, var1, var2);
        }
        func_236(var6);
        GroundModule(0x1c, 0);
    }
    HitModule(0, 0x3);
    BattleObject(0x79, 0, 0x8);
}

void func_235()
{
    printf("status_Rebirth sub_end_move");
    WorkModule(0x11, 0x2100000d);
    WorkModule(0x12, 0x20000001);
    GroundModule(0x2710, 0x5);
    CameraModule(0x2, 0x1);
}

void func_236(int arg0)
{
    
}

void func_237(int arg0, int arg1, int arg2)
{
    float var3;
    int var4;
    var3 = WorkModuleF(0, 0x3000062);
    var4 = EffectModule(0x3, 0x1000061, arg0, arg1, arg2, 0, 0, 0, var3, 0, 0xffffffff);
    WorkModule(0x7, var4, 0x11000005);
}

void func_238(int arg0, int arg1, int arg2)
{
    int var3;
    var3 = WorkModule(0x6, 0x11000005);
    if (var3 != 0)
    {
        EffectModule(0x17, var3, arg0, arg1, arg2);
    }
}

void func_239()
{
    int var0;
    var0 = WorkModule(0x6, 0x11000005);
    if (var0 != 0)
    {
        EffectModule(0x6, var0);
        WorkModule(0x7, 0, 0x11000005);
    }
}

void func_240()
{
    if (!global3)
    {
        func_242();
    }
}

void func_241()
{
    int var0;
    int var1;
    if (!WorkModule(0x10, 0x21000011) && global9 > 1.0f)
    {
        printf("sub_rebirth_uniq_process_exec_status FIGHTER_EFFECT_KIND_REBIRTH");
        EffectModule(0x1f, 0x21, 0);
        WorkModule(0x2710, 0x21000011);
    }
    if (!WorkModule(0x10, 0x2100000d))
    {
        var0 = WorkModule(0x6, 0x11000002);
        var1 = WorkModule(0x6, 0x11000003);
        var0++;
        WorkModule(0x7, var0, 0x11000002);
        if (var0 > var1)
        {
            func_235();
            FighterUtil(0xe);
        }
        else if (!WorkModule(0x10, 0x21000010))
        {
            FighterUtil(0xf, WorkModuleF(0, 0x1000006), WorkModuleF(0, 0x1000007), 0, WorkModuleF(0, 0x1000008), WorkModuleF(0, 0x1000009), 0, var0, var1);
        }
    }
    else
    {
        FighterUtil(0xe);
    }
}

void func_242()
{
    int var0;
    int var1;
    float var2;
    float var3;
    float var4;
    if (!WorkModule(0x10, 0x2100000d))
    {
        if (!WorkModule(0x10, 0x2100000f))
        {
            var0 = WorkModule(0x6, 0x11000002);
            var1 = WorkModule(0x6, 0x11000003);
            if (var0 > var1 / 0x2)
            {
                BattleObject(0x31);
                BattleObject(0x54);
                WorkModule(0x11, 0x2100000f);
            }
        }
    }
    if (!WorkModule(0x10, 0x20000033))
    {
        var2 = PostureModuleF(0x1);
        var3 = PostureModuleF(0x2);
        var4 = PostureModuleF(0x3);
        func_238(var2, var3, var4);
    }
}

void func_243()
{
    int var0;
    int var1;
    var0 = WorkModule(0x6, 0x10000000);
    func_239();
    WorkModule(0x12, 0x20000001);
    if (!WorkModule(0x10, 0x20000027))
    {
        var1 = (int)((float)WorkModule(0x6, 0x12000149) * WorkModuleF(0, 0x30000fd));
        HitModule(0x1, var1, 0);
    }
    CameraModule(0x2, 0x1);
    FighterUtil(0x19, 0);
}

int func_244()
{
    StatusModule(0x5, 0, 0xf, 0x9, 0, 0x1, 2.0f, 0x40, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1, 0, 0x1, 0);
    return 0;
}

int func_245()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x52, 0, 0x4, 0x80);
    return 0;
}

int func_246()
{
    int var0;
    var0 = 0x1062;
    if (BattleObject(0x89) == 0)
    {
        var0 = 0x62;
    }
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, var0, 0, 0x2, 0x40);
    return 0;
}

int func_247()
{
    int var0;
    var0 = 0x1092;
    if (BattleObject(0x89) == 0)
    {
        var0 = 0x92;
    }
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, var0, 0, 0x2, 0x40);
    if (global48 < -0.12f && PostureModuleF(0) == 1.0f || global48 > 0.12f && PostureModuleF(0) == -1.0f)
    {
        PostureModule(0x2710); // reverse facing direction (universal: reverse tilts) (universal mechanics)
    }
    return 0;
}

int func_248()
{
    StatusModule(0x5, 0, 0xf, 0x9, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x10a2, 0, 0x2, 0x40);
    if (global48 < -0.12f && PostureModuleF(0) == 1.0f || global48 > 0.12f && PostureModuleF(0) == -1.0f)
    {
        PostureModule(0x2710); // reverse facing direction (universal: reverse tilts) (universal mechanics)
    }
    return 0;
}

int func_249()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0x180, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x210b2, 0, 0, 0x800);
    return 0;
}

int func_250()
{
    func_251(0, 0x4, 0x1c0);
    return 0;
}

void func_251(int arg0, int arg1, int arg2)
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, arg0, arg1, arg2, 0x9c0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x200b2, 0, 0, 0);
}

int func_252()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0x4, 0x4, 0x1c1, 0x860);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x200b2, 0, 0x40, 0);
    return 0;
}

int func_253()
{
    StatusModule(0x5, 0, 0x6, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x210c2, 0, 0, 0x800);
    return 0;
}

int func_254()
{
    func_255(0, 0x4, 0x1c0);
    return 0;
}

int func_255(int arg0, int arg1, int arg2)
{
    StatusModule(0x5, 0, 0x6, 0x2, 0, 0x1, arg0, arg1, arg2, 0x9c0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x200c2, 0, 0, 0);
    return 0;
}

int func_256()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0x4, 0x4, 0x1c1, 0x860);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x200c2, 0, 0x40, 0);
    return 0;
}

int func_257()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x210d2, 0, 0, 0x800);
    return 0;
}

int func_258()
{
    func_259(0, 0x4, 0x1c0);
    return 0;
}

int func_259(int arg0, int arg1, int arg2)
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, arg0, arg1, arg2, 0x9c0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x200d2, 0, 0, 0);
    return 0;
}

int func_260()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0x4, 0x4, 0x1c1, 0x860);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x200d2, 0, 0x40, 0);
    return 0;
}

int func_261()
{
    StatusModule(0x5, 0x2, 0x13, 0x5, 0, 0x1, 0x2002, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x4000, 0x8, 0x100);
    return 0;
}

void func_262()
{
    if (global5 != 0x25)
    {
        WorkModule(0x7, 0, 0x11000006);
    }
    if (ComboModule(0) >= WorkModule(0x6, 0x13000107))
    {
        ComboModule(0x2);
    }
    WorkModule(0x16, 0x1e000053);
}

void func_263()
{
    int var0;
    func_262();
    var0 = WorkModule(0x6, 0x13000106);
    if (!StopModule(0x1))
    {
        func_268();
    }
    global15 = func_268;
    if (var0 == 0)
    {
        if (ControlModule(0x2712, 0) == 0x1 && WorkModule(0x10, 0x21000013) == 0x1)
        {
            WorkModule(0x2710, 0x2100001a);
        }
        if (!StopModule(0x1))
        {
            func_266();
        }
        global16 = func_266;
    }
    else if (var0 == 0x1)
    {
        if (!StopModule(0x1))
        {
            func_267();
        }
        global16 = func_267;
    }
    else if (var0 == 0x2)
    {
        if (!StopModule(0x1))
        {
            func_267();
        }
        global16 = func_267;
    }
    func_78(func_270);
}

void func_264()
{
    if (!global3)
    {
        if (ControlModule(0x2710, 0) || ControlModule(0x2711, 0))
        {
            WorkModule(0x9, 0x11000003);
        }
    }
    else if (ControlModule(0x2726, 0) || ControlModule(0x2727, 0))
    {
        WorkModule(0x9, 0x11000003);
    }
}

void func_265()
{
    if (global38 & 0x1)
    {
        WorkModule(0x2710, 0x21000010);
    }
}

void func_266()
{
    if (ControlModule(0x2712, 0) == 0x1)
    {
        if (WorkModule(0x10, 0x21000013) == 0x1)
        {
            WorkModule(0x2710, 0x2100001a);
            WorkModule(0x2710, 0x2100001e);
        }
    }
    func_265();
}

void func_267()
{
    func_265();
    if (global38 & 0x1 && WorkModule(0x10, 0x2100000d) == 0x1)
    {
        WorkModule(0x2710, 0x21000012);
    }
    if (ControlModule(0x2712, 0) == 0x1)
    {
        if (AttackModule(0x2727))
        {
            if (WorkModule(0x10, 0x2100000d) == 0x1)
            {
                WorkModule(0x2710, 0x21000012);
            }
        }
        else
        {
            if (WorkModule(0x10, 0x21000013) == 0x1 && WorkModule(0x10, 0x21000019) == 0)
            {
                WorkModule(0x2710, 0x2100001a);
                WorkModule(0x2710, 0x2100001e);
                ComboModule(0x2);
            }
            if (WorkModule(0x10, 0x2100000e) == 0x1)
            {
                WorkModule(0x2710, 0x21000012);
                if (ControlModule(0x2710, 0) == 0x1)
                {
                    WorkModule(0x2710, 0x2100001f);
                }
            }
        }
    }
    else
    {
        WorkModule(0x2710, 0x21000019);
    }
    if (WorkModule(0x10, 0x2100001d) == 0x1 && WorkModule(0x10, 0x21000012) == 0x1 && ComboModule(0) == WorkModule(0x6, 0x13000107))
    {
        WorkModule(0x2710, 0x2100001a);
        ComboModule(0x2);
        if (WorkModule(0x10, 0x2100000e) == 0x1 && WorkModule(0x10, 0x2100001f) == 0)
        {
            WorkModule(0x2710, 0x2100001e);
        }
    }
}

void func_268()
{
    if (StatusModule(0x6))
    {
        func_269();
    }
    else if (ComboModule(0) < WorkModule(0x6, 0x13000107) && WorkModule(0x10, 0x21000012) == 0x1)
    {
        func_269();
    }
}

void func_269()
{
    int var0;
    int var1;
    int var2;
    int var3;
    ControlModule(0x271b);
    AttackModule(0x2719);
    AttackModule(0x2724);
    CancelModule(0x2711);
    ControlModule(0x271f);
    var0 = WorkModule(0x10, 0x2100000e);
    WorkModule(0x2711, 0x21000012);
    WorkModule(0x2711, 0x21000013);
    WorkModule(0x2711, 0x2100000d);
    WorkModule(0x2711, 0x2100000e);
    WorkModule(0x2711, 0x21000010);
    WorkModule(0x2711, 0x21000019);
    WorkModule(0x2711, 0x2100001a);
    WorkModule(0x2711, 0x21000011);
    ComboModule(0x1, 0);
    var1 = ComboModule(0);
    var2 = WorkModule(0x6, 0x13000106);
    if (var1 == 0x1)
    {
        func_22(FighterUtil(0x1e), 0, 1.0f);
        if (global1 != 0x34)
        {
            BattleObject(0xd, 0x2, 0x1, 0x1);
        }
        var3 = 0x1;
        if (WorkModule(0x10, 0x2100001e) && global5 == 0x25)
        {
            var3 = 0;
        }
        if (var3)
        {
            BattleObject(0x1c, 0x5);
        }
    }
    else if (var1 == 0x2)
    {
        func_22(0x51, 0, 1.0f);
        BattleObject(0xd, 0x2, 0x2);
        KineticModule(0x7, 0);
        BattleObject(0xe);
        var3 = 0x1;
        if (var0 && WorkModule(0x10, 0x2100001f) == 0)
        {
            var3 = 0;
        }
        if (var3)
        {
            BattleObject(0x1c, 0x5);
        }
    }
    else if (var1 == 0x3)
    {
        func_22(0x52, 0, 1.0f);
        BattleObject(0xd, 0x2, 0x3);
        BattleObject(0xe);
        var3 = 0x1;
        if (var0 && WorkModule(0x10, 0x2100001f) == 0)
        {
            var3 = 0;
        }
        if (var3)
        {
            BattleObject(0x1c, 0x5);
        }
    }
    WorkModule(0x2711, 0x2100001e);
    WorkModule(0x2711, 0x2100001f);
}

void func_270()
{
    int var0;
    func_264();
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (WorkModule(0x6, 0x13000108) != 0)
    {
        if (AttackModule(0x2727))
        {
            if (WorkModule(0x10, 0x21000011))
            {
                if (ControlModule(0x2712, 0))
                {
                    if (ComboModule(0) >= WorkModule(0x6, 0x13000107))
                    {
                        if (WorkModule(0x10, 0x2100000d))
                        {
                            if (global18 == 0)
                            {
                                func_16(0x26, 0x1);
                                return 0x1;
                            }
                        }
                    }
                }
            }
        }
        if (WorkModule(0x15, 0x1e000053))
        {
            if (WorkModule(0x10, 0x21000011))
            {
                if (WorkModule(0x6, 0x11000003) >= WorkModule(0x6, 0x13000056))
                {
                    if (global18 == 0)
                    {
                        printf("ATTACK 100 2 100_COUNT: %d, ENABLE_CNT: %d", WorkModule(0x6, 0x11000003), WorkModule(0x6, 0x13000056));
                        func_16(0x26, 0);
                        return 0x1;
                    }
                }
            }
        }
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    var0 = WorkModule(0x6, 0x13000106);
    if (var0 == 0)
    {
        if (WorkModule(0x10, 0x2100001a) == 0x1)
        {
            func_16(0x25, 0);
            return;
        }
    }
    else if (var0 == 0x1)
    {
        if (WorkModule(0x10, 0x2100001a) == 0x1)
        {
            func_16(0x25, 0);
            return;
        }
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0, 0);
        return;
    }
}

void func_271()
{
    if (WorkModule(0x6, 0x11000002) >= 0)
    {
        WorkModule(0xa, 0x11000002);
        if (WorkModule(0x6, 0x11000002) < 0)
        {
            WorkModule(0x17, 0x1e00006f);
            WorkModule(0x17, 0x1e00006e);
        }
    }
    WorkModule(0x9, 0x11000003);
    if (WorkModule(0x6, 0x11000003) <= WorkModule(0x6, 0x120001ef))
    {
        func_103();
    }
    if (WorkModule(0x6, 0x11000003) >= WorkModule(0x6, 0x1300000c) && WorkModule(0x10, 0x2100000d) == 0)
    {
        WorkModule(0x17, 0x1e00005c);
        WorkModule(0x2710, 0x2100000d);
    }
}

void func_272()
{
    func_22(0x56, 0, 1.0f);
    WorkModule(0x16, 0x1e00006f);
    WorkModule(0x16, 0x1e00006e);
    WorkModule(0x16, 0x1e00005c);
    WorkModule(0x7, WorkModule(0x6, 0x120000e0), 0x11000002);
    WorkModule(0x2711, 0x2100000d);
    if (!StopModule(0x1))
    {
        func_271();
    }
    global16 = func_271;
    func_78(func_273);
}

void func_273()
{
    int var0;
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e00006f) == 0x1 && func_88() <= WorkModuleF(0, 0x2000014) && ControlModule(0x2712, 0x3) == 0x1 && global18 == 0 && ItemModule(0x4) == 0)
    {
        func_16(0x39, 0x1);
        return;
    }
    if (WorkModule(0x15, 0x1e00006e) == 0x1 && ControlModule(0x2712, 0x3) == 0x1 && global18 == 0 && ItemModule(0x4) == 0)
    {
        func_16(0x37, 0x1);
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        var0 = WorkModule(0x6, 0x1300011c);
        if (var0 == 0x1)
        {
            func_16(0x12, 0);
        }
        else
        {
            func_16(0, 0);
        }
    }
}

void func_274()
{
    if (global38 & 0x1 && WorkModule(0x10, 0x2100000f) == 0x1)
    {
        WorkModule(0x2710, 0x21000010);
    }
}

void func_275()
{
    if (global5 == 0x8)
    {
        KineticModule(0, 0x7);
        if (global1 == 0x38)
        {
            KineticModule(0xe, 0, 0x2, 0, 0, 0, 0, 0);
            KineticModule(0xb, 0);
        }
    }
    ControlModule(0x271b);
    if (!StopModule(0x1))
    {
        func_274();
    }
    global16 = func_274;
    func_33();
    KineticModule(0x13, 0, PostureModuleF(0));
    func_78(func_277);
}

void func_276()
{
    int var0;
    float var1;
    ControlModule(0x271b);
    ControlModule(0x271f);
    WorkModule(0x2711, 0x2100000d);
    WorkModule(0x2711, 0x21000010);
    WorkModule(0x2710, 0x2100000f);
    ComboModule(0x1, 0x1);
    var0 = ComboModule(0);
    if (var0 == 0x1)
    {
        var1 = ControlModuleF(0x4);
        if (MotionModule(0xc, 0x57) == 0x1 && var1 > WorkModuleF(0, 0x2000032))
        {
            func_22(0x57, 0, 1.0f);
        }
        else if (MotionModule(0xc, 0x5b) == 0x1 && var1 < WorkModuleF(0, 0x2000033))
        {
            func_22(0x5b, 0, 1.0f);
        }
        else
        {
            func_22(FighterUtil(0x1f), 0, 1.0f);
        }
    }
    else if (var0 == 0x2)
    {
        func_22(0x59, 0, 1.0f);
        BattleObject(0xd, 0x2, 0x7);
        BattleObject(0xe);
        BattleObject(0x1c, 0x6);
    }
    else if (var0 == 0x3)
    {
        func_22(0x5a, 0, 1.0f);
        BattleObject(0xd, 0x2, 0x8);
        BattleObject(0xe);
        BattleObject(0x1c, 0x6);
    }
}

void func_277()
{
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (StatusModule(0x6) == 0x1 || ComboModule(0) < WorkModule(0x6, 0x13000109) && WorkModule(0x10, 0x21000010) == 0x1 && WorkModule(0x10, 0x2100000d) == 0x1)
    {
        func_276();
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0, 0);
        return;
    }
}

void func_278()
{
    func_22(FighterUtil(0x20), 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_274();
    }
    global16 = func_274;
    edge_sn_init_hi3();      // Sephiroth: held up tilt
    func_78(func_279);
}

void func_279()
{
    if (edge_sn_cancel())    // Sephiroth: held up tilt, side special cancel
    {
        return;
    }
    edge_sn_loop();          // Sephiroth: held up tilt
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (WorkModule(0x10, 0x21000010) == 0x1)
    {
        if (StatusModule(0x6) == 0x1 || ComboModule(0) < WorkModule(0x6, 0x13000109) && WorkModule(0x10, 0x21000010) == 0x1 && WorkModule(0x10, 0x2100000d) == 0x1)
        {
            func_276();
        }
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0, 0);
        return;
    }
}

void func_280()
{
    func_22(FighterUtil(0x21), 0, 1.0f);
    WorkModule(0x1b, 0x1e000034);
    WorkModule(0x1b, 0x1e00002f);
}

void func_281()
{
    func_280();
    if (!StopModule(0x1))
    {
        func_274();
    }
    global16 = func_274;
    func_78(func_282);
}

int func_282()
{
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return 0x1;
    }
    if (WorkModule(0x10, 0x21000010) == 0x1)
    {
        if (StatusModule(0x6) == 0x1 || ComboModule(0) < WorkModule(0x6, 0x13000109) && WorkModule(0x10, 0x21000010) == 0x1 && WorkModule(0x10, 0x2100000d) == 0x1)
        {
            func_276();
        }
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    /* Test 145: the down tilt motion ends crouched and holds the crouch long after its cancel frame, then
       SquatWait stood him up only at the motion's end. Past the cancel frame with down not held he stands
       up (SquatRv) at once; held, he stays in the move and ends in SquatWait as before. */
    if (CancelModule(0x2713) == 0x1 && global18 == 0)
    {
        if (!func_53())
        {
            func_16(0x15, 0);
            return 0x1;
        }
    }
    if (MotionModule(0x2712) == 0x1)
    {
        if (func_53())
        {
            func_16(0x12, 0);
        }
        else
        {
            func_16(0x15, 0);
        }
        return 0x1;
    }
    return 0;
}

void func_283()
{
    WorkModule(0xa, 0x11000005);
}

void func_284()
{
    if (global4 == 0x2c || global4 == 0x2d)
    {
        if (TurnModule(0) && TurnModule(0x1) == 0)
        {
            if (PostureModuleF(0) != WorkModuleF(0, 0x1000007))
            {
                TurnModule(0x2);
                WorkModule(0, PostureModuleF(0), 0x1000007);
            }
            if (PostureModuleF(0) != WorkModuleF(0, 0x1000008))
            {
                KineticModule(0x13, 0, WorkModuleF(0, 0x1000008));
            }
        }
    }
}

void func_285()
{
    if (TurnModule(0) && TurnModule(0x1) == 0)
    {
        if (PostureModuleF(0) == WorkModuleF(0, 0x1000007))
        {
            if (PostureModuleF(0) == 1.0f)
            {
                BattleObject(0x67, 1.0f);
            }
            else if (PostureModuleF(0) == -1.0f)
            {
                BattleObject(0x67, -1.0f);
            }
        }
        TurnModule(0x2711);
    }
}

void func_286()
{
    if (global5 == 0x8)
    {
        KineticModule(0, 0x7);
    }
    WorkModule(0x16, 0x1e00005a);
    WorkModule(0x16, 0x1e000058);
    PostureModule(0x2);
    func_22(0x5f, 0, 1.0f);
    func_78(func_287);
}

void func_287()
{
    int var0;
    var0 = WorkModule(0x10, 0x2100001b);
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e00005a) != 0 && var0 == 0x1 && ControlModule(0x2712, 0))
    {
        func_16(0x2c, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000058) && var0 == 0x1)
    {
        func_16(0x2d, 0);
        return 0x1;
    }
}

void func_288()
{
    float var0;
    float var1;
    int var2;
    float var3;
    if (!StopModule(0x1))
    {
        func_283();
    }
    global16 = func_283;
    var0 = WorkModuleF(0, 0x30000e1);
    var1 = (float)WorkModule(0x6, 0x1300005b);
    var2 = (int)(var1 / var0);
    WorkModule(0x7, var2, 0x11000008);
    var3 = WorkModuleF(0, 0x25);
    if (var3 > 0)
    {
        var2 = (int)((float)var2 * var3);
    }
    var0 = var1 / (float)var2;
    WorkModule(0x7, var2, 0x11000005);
    WorkModule(0x7, var2, 0x11000009);
    func_22(0x62, 0, var0);
    func_78(func_289);
}

void func_289()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    else if (global18 == 0)
    {
        if (WorkModule(0x6, 0x11000005) <= 0 || !ControlModule(0x2712, 0))
        {
            func_16(0x2d, 0x1);
            return 0x1;
        }
    }
}

void func_290()
{
    func_291(0x1);
    WorkModule(0x2710, 0x2100001c);
    func_78(func_293);
}

void func_291(int arg0)
{
    float var1;
    if (arg0 == 0x1)
    {
        var1 = ControlModuleF(0x4);
        if (MotionModule(0xc, 0x5e) == 0x1 && var1 > WorkModuleF(0, 0x2000038))
        {
            WorkModule(0x7, 0x5e, 0x11000002);
        }
        else if (MotionModule(0xc, 0x61) == 0x1 && var1 < WorkModuleF(0, 0x2000039))
        {
            WorkModule(0x7, 0x61, 0x11000002);
        }
        else
        {
            WorkModule(0x7, 0x5f, 0x11000002);
        }
    }
    else
    {
        WorkModule(0x7, 0x5f, 0x11000002);
    }
}

void func_292()
{
    int var0;
    int var1;
    float var2;
    ControlModule(0x271b);
    WorkModule(0x2711, 0x2100000d);
    ComboModule(0x1, 0x2);
    var0 = ComboModule(0);
    if (var0 == 0x1)
    {
        var1 = WorkModule(0x6, 0x11000002);
        var2 = WorkModuleF(0, 0x1000006);
        MotionModule(0x26, var1, var2, 1.0f);
    }
    else if (var0 == 0x2)
    {
        func_22(0x60, 0, 1.0f);
        BattleObject(0xe);
        BattleObject(0x1c, 0xb);
    }
}

void func_293()
{
    if (StatusModule(0x6) == 0x1 || ComboModule(0) < WorkModule(0x6, 0x1300010a) && global38 & 0x1 && WorkModule(0x10, 0x2100000d) == 0x1)
    {
        func_292();
    }
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0, 0);
        return;
    }
}

void func_294(int arg0)
{
    WorkModule(0x16, 0x1e00005d);
    WorkModule(0x16, 0x1e00005b);
    func_22(arg0, 0, 1.0f);
    func_78(func_296);
}

void func_295()
{
    func_294(0x63);
}

int func_296()
{
    int var0;
    var0 = WorkModule(0x10, 0x2100001b);
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00005d) != 0 && var0 == 0x1 && ControlModule(0x2712, 0))
    {
        func_16(0x32, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00005b) != 0 && var0 == 0x1)
    {
        func_16(0x33, 0);
        return 0x1;
    }
    return 0;
}

void func_297(int arg0)
{
    float var1;
    float var2;
    int var3;
    float var4;
    if (!StopModule(0x1))
    {
        func_283();
    }
    global16 = func_283;
    var1 = WorkModuleF(0, 0x30000e1);
    var2 = (float)WorkModule(0x6, 0x1300005c);
    var3 = (int)(var2 / var1);
    WorkModule(0x7, var3, 0x11000008);
    var4 = WorkModuleF(0, 0x25);
    if (var4 > 0)
    {
        var3 = (int)((float)var3 * var4);
    }
    var1 = var2 / (float)var3;
    WorkModule(0x7, var3, 0x11000005);
    WorkModule(0x7, var3, 0x11000009);
    func_22(arg0, 0, var1);
    func_78(func_299);
}

void func_298()
{
    func_297(0x64);
}

int func_299()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    else if (global18 == 0)
    {
        if (WorkModule(0x6, 0x11000005) <= 0 || !ControlModule(0x2712, 0))
        {
            func_16(0x33, 0x1);
            return 0x1;
        }
    }
    return 0;
}

void func_300(int arg0)
{
    float var1;
    WorkModule(0x2710, 0x2100001c);
    var1 = WorkModuleF(0, 0x1000006);
    MotionModule(0x26, arg0, var1, 1.0f);
    func_78(func_302);
}

void func_301()
{
    func_300(0x63);
}

void func_302()
{
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0, 0);
        return;
    }
}

void func_303()
{
    WorkModule(0x16, 0x1e000060);
    WorkModule(0x16, 0x1e00005e);
    func_22(0x65, 0, 1.0f);
    func_78(func_304);
}

void func_304()
{
    int var0;
    var0 = WorkModule(0x10, 0x2100001b);
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e000060) != 0 && var0 == 0x1 && ControlModule(0x2712, 0))
    {
        func_16(0x2f, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00005e) != 0 && var0 == 0x1)
    {
        func_16(0x30, 0);
        return 0x1;
    }
}

void func_305()
{
    float var0;
    float var1;
    int var2;
    float var3;
    if (!StopModule(0x1))
    {
        func_283();
    }
    global16 = func_283;
    var0 = WorkModuleF(0, 0x30000e1);
    var1 = (float)WorkModule(0x6, 0x1300005d);
    var2 = (int)(var1 / var0);
    WorkModule(0x7, var2, 0x11000008);
    var3 = WorkModuleF(0, 0x25);
    if (var3 > 0)
    {
        var2 = (int)((float)var2 * var3);
    }
    var0 = var1 / (float)var2;
    WorkModule(0x7, var2, 0x11000005);
    WorkModule(0x7, var2, 0x11000009);
    func_22(0x67, 0, var0);
    func_78(func_306);
}

int func_306()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    else if (global18 == 0)
    {
        if (WorkModule(0x6, 0x11000005) <= 0 || !ControlModule(0x2712, 0))
        {
            func_16(0x30, 0x1);
            return 0x1;
        }
    }
    return 0;
}

void func_307()
{
    WorkModule(0x2710, 0x2100001c);
    func_78(func_309);
}

void func_308()
{
    int var0;
    int var1;
    float var2;
    ControlModule(0x271b);
    WorkModule(0x2711, 0x2100000d);
    ComboModule(0x1, 0x2);
    var0 = ComboModule(0);
    if (var0 == 0x1)
    {
        var1 = 0x65;
        var2 = WorkModuleF(0, 0x1000006);
        MotionModule(0x26, var1, var2, 1.0f);
    }
    else if (var0 == 0x2)
    {
        func_22(0x66, 0, 1.0f);
        BattleObject(0xe);
        BattleObject(0x1c, 0xb);
    }
}

void func_309()
{
    if (StatusModule(0x6) == 0x1 || ComboModule(0) < WorkModule(0x6, 0x1300010b) && global38 & 0x1 && WorkModule(0x10, 0x2100000d) == 0x1)
    {
        func_308();
    }
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0, 0);
        return;
    }
}

void func_310()
{
    int var0;
    var0 = 0x68;
    var0 = func_311();
    func_22(var0, 0, 1.0f);
    WorkModule(0x7, var0, 0x11000002);
}

int func_311()
{
    int var0;
    int var1;
    var0 = 0x68;
    var1 = ControlModule(0x10);
    if (var1 == 0x1)
    {
        BattleObject(0xd, 0x2, 0xe);
    }
    else if (var1 == 0x2)
    {
        var0 = 0x69;
        BattleObject(0xd, 0x2, 0xf);
    }
    else if (var1 == 0x3)
    {
        var0 = 0x6a;
        BattleObject(0xd, 0x2, 0x12);
    }
    else if (var1 == 0x4)
    {
        var0 = 0x6b;
        BattleObject(0xd, 0x2, 0x13);
    }
    else if (var1 == 0x5)
    {
        var0 = 0x6c;
        BattleObject(0xd, 0x2, 0x14);
    }
    return var0;
}

void func_312(int arg0)
{
    ControlModule(0x271b);
    WorkModule(0x19, 0x1f000008);
    if (!StopModule(0x1))
    {
        func_316();
    }
    global16 = func_316;
    if (arg0 == 0x1)
    {
        func_310();
    }
    ControlModule(0x11);
}

void func_313()
{
    if (func_55())
    {
        return 0x1;
    }
}

void func_314()
{
    func_312(0x1);
}

void func_315()
{
    func_314();
    edge_sn_init();          // Sephiroth: held forward air
    func_78(func_319);
}

void func_316()
{
    WorkModule(0x9, 0x11000003);
    if (WorkModule(0x6, 0x11000003) <= WorkModule(0x6, 0x120001f0))
    {
        func_103();
    }
    edge_sn_550();           // Sephiroth: held forward air, no fast fall from the hold on
}

void func_317()
{
    if (global18 == 0)
    {
        if (WorkModule(0x10, 0x2100000d) == 0x1)
        {
            func_16(0x18, 0);
        }
        else
        {
            func_16(0x16, 0);
        }
        return 0x1;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (func_313())
    {
        return 0x1;
    }
}

int func_318()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return 0x1;
    }
    func_317();
    return 0;
}

void func_319()
{
    if (edge_sn_cancel())    // Sephiroth: held forward air, side special cancel
    {
        return;
    }
    edge_sn_loop();          // Sephiroth: held forward air
    if (func_318())
    {
        return;
    }
    if (edge_sn_free())      // Sephiroth: held forward air, no fast fall while the sword is out
    {
        func_555();
    }
    if (!global3)
    {
        func_341();
    }
}

void func_320()
{
    
}

void func_321()
{
    
}

void func_322()
{
    
}

void func_323()
{
    
}

void func_324()
{
    
}

void func_325()
{
    int var0;
    WorkModule(0, MotionModuleF(0x1) + 0, 0x1000006);
    var0 = global6;
    if (var0 == 0x2c)
    {
        KineticModule(0x11, 0, 0, 0);
    }
}

void func_326()
{
    PhysicsModule(0x8);
}

void func_327()
{
    
}

void func_328()
{
    func_325();
}

void func_329()
{
    PhysicsModule(0x8);
}

void func_330()
{
    
}

void func_331()
{
    func_325();
}

void func_332()
{
    PhysicsModule(0x8);
}

void func_333()
{
    
}

void func_334()
{
    
}

int func_335()
{
    StatusModule(0x5, 0, 0xf, 0x9, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x42, 0, 0x1, 0x20000000);
    return 0;
}

void func_336()
{
    if (MotionModule(0xc, 0x53))
    {
        func_22(0x53, 0, 1.0f);
    }
    WorkModule(0x7, 0, 0x11000007);
    func_78(func_337);
}

void func_337()
{
    int var0;
    int var1;
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    var0 = WorkModule(0x6, 0x11000007);
    if (var0 == 0)
    {
        var1 = MotionModule(0x7);
        if (var1 != 0x53 || MotionModule(0x2712))
        {
            WorkModule(0x2710, 0x21000015);
            WorkModule(0x2711, 0x21000016);
            WorkModule(0x2711, 0x21000017);
            func_22(0x54, 0, 1.0f);
            WorkModule(0x7, 0x1, 0x11000007);
        }
    }
    else if (var0 == 0x1)
    {
        if (!StopModule(0x1))
        {
            func_338();
        }
        global16 = func_338;
        if (!WorkModule(0x10, 0x21000015))
        {
            func_22(0x55, 0, 1.0f);
            WorkModule(0x7, 0x2, 0x11000007);
        }
    }
    else if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return;
        }
    }
}

void func_338()
{
    if (ControlModule(0x2710, 0) || ControlModule(0x2711, 0))
    {
        WorkModule(0x2710, 0x21000010);
    }
    if (WorkModule(0x10, 0x21000018))
    {
        if (WorkModule(0x10, 0x21000016))
        {
            WorkModule(0x2711, 0x21000016);
            if (WorkModule(0x10, 0x21000010))
            {
                WorkModule(0x2711, 0x21000010);
            }
            else if (ControlModule(0x2713, 0))
            {
                WorkModule(0x2711, 0x21000015);
            }
        }
    }
    else if (MotionModule(0xb))
    {
        WorkModule(0x2710, 0x21000018);
    }
    if (WorkModule(0x10, 0x21000021))
    {
        WorkModule(0x2711, 0x21000021);
        if (WorkModule(0x6, 0x11000004) > 0)
        {
            WorkModule(0xa, 0x11000004);
            if (WorkModule(0x6, 0x11000004) == 0)
            {
                WorkModule(0x2711, 0x21000015);
            }
        }
    }
}

void func_339()
{
    
}

void func_340()
{
    FighterUtil(0x1);
}

void func_341()
{
    FighterUtil(0x2);
}

void func_342()
{
    if (WorkModule(0x10, 0x2100000e))
    {
        if (global6 == 0x18 || global6 == 0x16 || global6 == 0x17)
        {
            KineticModule(0x3);
        }
    }
}

void func_343()
{
    if (global4 == 0x2b)
    {
        if (TurnModule(0) && TurnModule(0x1) == 0)
        {
            if (PostureModuleF(0) != WorkModuleF(0, 0x1000008))
            {
                BattleObject(0x67, WorkModuleF(0, 0x1000008));
                KineticModule(0x13, 0, WorkModuleF(0, 0x1000008));
            }
        }
    }
    else if (global4 == 0x2c || global4 == 0x2d)
    {
        func_284();
    }
}

void func_344()
{
    int var0;
    float var1;
    func_343();
    var0 = global4;
    if (var0 == 0x2e || var0 == 0x31 || var0 == 0x2b || var0 == 0x94)
    {
        if (WorkModuleF(0, 0x25) > 0)
        {
            DamageModule(0xb, 0x2, WorkModuleF(0, 0x27) + 0);
        }
    }
    else if (var0 == 0x2f || var0 == 0x32 || var0 == 0x2c || var0 == 0x96)
    {
        var1 = WorkModuleF(0, 0x200003f);
        DamageModule(0xa, var1);
        EffectModule(0x1f, 0x19, 0);
        if (BattleObject(0x6e, 0x31) == 0x1)
        {
            func_346();
        }
    }
    else if (var0 == 0x30 || var0 == 0x33 || var0 == 0x2d || var0 == 0x95)
    {
        func_345();
    }
}

void func_345()
{
    float var0;
    float var1;
    float var2;
    float var3;
    int var4;
    int var5;
    int var6;
    var0 = 1.0f;
    if (WorkModule(0x10, 0x21000002))
    {
        var1 = WorkModuleF(0, 0x1000000);
        var2 = WorkModuleF(0, 0x200003e);
        var0 = (var2 - 1.0f) * var1 + 1.0f;
    }
    var3 = WorkModuleF(0, 0x26);
    if (var3 > 1.0f)
    {
        var0 *= var3;
    }
    AttackModule(0x2728, var0);
    if (BattleObject(0x6e, 0x31) == 0x1 && WorkModuleF(0, 0x25) <= 0)
    {
        var4 = 0x1;
        if (var5 == 0x95)
        {
            var6 = ItemModule(0x11);
            if (var6 == 0x33 || var6 == 0x34)
            {
                var4 = 0;
            }
        }
        if (var4)
        {
            DamageModule(0xb, 0, 0);
        }
    }
    if (BattleObject(0x86, 0xa))
    {
        if (var5 != 0x95)
        {
            if (randi(0, 0x64) < WorkModule(0x6, 0x1200033d))
            {
                AttackModule(0x272e, WorkModuleF(0, 0x200033e));
                WorkModule(0x2710, 0x21000020);
            }
        }
    }
}

void func_346()
{
    int var0;
    int var1;
    float var2;
    float var3;
    float var4;
    var0 = BattleObject(0x77, 0x31);
    var1 = 0x9000087 + var0 - 0x1;
    var2 = WorkModuleF(0, var1);
    if (WorkModuleF(0, 0x25) > 0)
    {
        var3 = WorkModuleF(0, 0x27);
        if (var2 < var3)
        {
            var2 = var3;
        }
    }
    DamageModule(0xb, 0x2, var2 + 0);
    var4 = DamageModuleF(0xc);
    var1 = 0x9000084 + var0 - 0x1;
    var4 *= WorkModuleF(0, var1);
    DamageModule(0x10, var4);
}

void func_347()
{
    if (global4 == 0x2b || global4 == 0x2c || global4 == 0x2d)
    {
        if (global6 != 0x2b && global6 != 0x2c && global6 != 0x2d)
        {
            func_285();
        }
    }
}

void func_348()
{
    int var0;
    int var1;
    int var2;
    int var3;
    int var4;
    int var5;
    float var6;
    float var7;
    float var8;
    float var9;
    int var10;
    int var11;
    int var12;
    float var13;
    func_347();
    var0 = global4;
    var1 = global6;
    var2 = 0;
    if (var0 == 0x2f || var0 == 0x32 || var0 == 0x2c || var0 == 0x96)
    {
        var2 = 0x1;
    }
    if (var1 == 0x30 || var1 == 0x33 || var1 == 0x2d || var1 == 0x95)
    {
        if (var2 == 0x1)
        {
            if (var1 == 0x95)
            {
                var3 = 0x11000005;
                var4 = 0x11000007;
                var5 = 0x11000006;
            }
            else
            {
                var3 = 0x11000005;
                var4 = 0x11000009;
                var5 = 0x11000008;
            }
            var6 = (float)WorkModule(0x6, var3);
            var7 = (float)WorkModule(0x6, var4);
            if (var6 < 0)
            {
                var6 = 0;
            }
            var6 = var7 - var6;
            var8 = 0;
            var9 = (float)WorkModule(0x6, var5);
            if (var9 > 0)
            {
                var8 = var6 / var9;
            }
            WorkModule(0, var8 + 0, 0x1000000);
            if (var1 == 0x95)
            {
                var10 = ItemModule(0x11);
                if (var10 != 0x3a)
                {
                    var11 = (int)var6;
                    WorkModule(0x7, var11, 0x11000004);
                }
                else
                {
                    var12 = func_1740() + 0x2;
                    var13 = (float)MotionModule(0, var12);
                    var11 = (int)(var8 * var13);
                    WorkModule(0x7, var11, 0x11000004);
                }
            }
            WorkModule(0x2710, 0x21000002);
        }
        else
        {
            WorkModule(0, 0 + 0, 0x1000000);
            WorkModule(0x2711, 0x21000002);
        }
    }
    if (var2 == 0x1)
    {
        EffectModule(0x20, 0x19);
    }
    if (WorkModule(0x10, 0x21000020))
    {
        AttackModule(0x272e, 1.0f);
        WorkModule(0x2711, 0x21000020);
    }
}

int func_349()
{
    StatusModule(0x5, 0, 0x4b, 0x1, 0, 0x1, 0, 0, 0xe, 0x6c0);
    StatusModule(0x2713, 0x1, 0, 0x1, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_350()
{
    MotionModule(0x4, 0);
    func_78(func_351);
}

void func_351()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (global9 > 1.0f)
    {
        func_16(0x24, 0);
        return;
    }
}

void func_352()
{
    
}

int func_353()
{
    StatusModule(0x5, 0, 0x4b, 0x1, 0, 0x1, 0, 0, 0xe, 0);
    StatusModule(0x2713, 0x1, 0, 0x1, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_354()
{
    func_22(0x4f, 0, WorkModuleF(0, 0x1000003));
    func_78(func_355);
}

void func_355()
{
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712) == 0x1 && global18 == 0)
    {
        func_16(0, 0);
        return;
    }
}

void func_356()
{
    
}

void func_357()
{
    int var0;
    float var1;
    var0 = MotionModule(0x7);
    var1 = MotionModuleF(0x1);
    func_310();
    if (var0 == 0x1d || var0 == 0x1e)
    {
        if (WorkModule(0x10, 0x2000004e) == 0)
        {
            MotionModule(0x8, var0, 0, var1, 1.0f);
            MotionModule(0x13, 1.0f);
        }
        KineticModule(0, 0x50);
    }
    else
    {
        KineticModule(0, 0x13);
    }
}

void func_358()
{
    func_340();
}

void func_359()
{
    func_341();
    if (MotionModule(0x14))
    {
        KineticModule(0, 0x13);
    }
}

void func_360()
{
    func_342();
}

int func_361()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0, 0, 0x400000);
    return 0;
}

int func_362()
{
    if (func_364())
    {
        return 0x1;
    }
    StatusModule(0x5, 0, 0x6, 0x2, 0, 0, 0, 0, 0, 0); // roll-off: kinetic 0x6 (ACMD sets the speed) (universal mechanics)
    global62 = 0; // roll-off: new roll, shield-hold count starts over
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x80000, 0, 0x400001);
    return 0;
}

int func_363()
{
    if (func_364())
    {
        return 0x1;
    }
    StatusModule(0x5, 0, 0x6, 0x2, 0, 0, 0, 0x10, 0, 0); // roll-off: kinetic 0x6 (ACMD sets the speed) (universal mechanics)
    global62 = 0; // roll-off: new roll, shield-hold count starts over
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x80000, 0, 0x400001);
    return 0;
}

int func_364()
{
    if (ItemModule(0x4) == 0x1)
    {
        if (ControlModule(0x9) & 0x1)
        {
            if (ItemModule(0x5, 0x800000) == 0)
            {
                func_16(0x8c, 0);
                return 0x1;
            }
        }
    }
    return 0;
}

int func_365()
{
    StatusModule(0x5, 0x2, 0x13, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0, 0, 0x400002);
    return 0;
}

void func_366()
{
    func_76();
    func_22(0x4b, 0, 1.0f);
    ControlModule(0x2714, 0x18, 0);
    if (!StopModule(0x1))
    {
        func_368();
    }
    global16 = func_368;
    func_78(func_367);
}

void func_367()
{
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return;
        }
    }
}

void func_368()
{
    WorkModule(0x9, 0x11000002);
    if (WorkModule(0x6, 0x11000004) >= 0)
    {
        WorkModule(0xa, 0x11000004);
        if (WorkModule(0x6, 0x11000004) < 0)
        {
            WorkModule(0x17, 0x1e00006f);
            WorkModule(0x17, 0x1e00006e);
        }
    }
}

void func_369()
{
    float var0;
    if (global5 == 0x3)
    {
        WorkModule(0x16, 0x1e00006e);
        WorkModule(0x7, WorkModule(0x6, 0x120000e0), 0x11000004);
    }
    func_373();
    var0 = 1.0f;
    if (BattleObject(0x86, 0x4))
    {
        var0 = WorkModuleF(0, 0x2000333);
    }
    func_22(0x4c, 0, var0);
    func_78(func_370);
}

void func_370()
{
    rolloff_update(); // roll-off: edge sliding from the speed frame, not while shield is held (universal mechanics)
    if (func_374())
    {
        return;
    }
}

void func_371()
{
    float var0;
    if (global5 == 0x4 || global5 == 0x3 || global5 == 0x8)
    {
        WorkModule(0x16, 0x1e00006f);
        WorkModule(0x7, WorkModule(0x6, 0x120000e2), 0x11000004);
    }
    else if (global5 == 0x1b)
    {
        WorkModule(0x16, 0x1e00006f);
        WorkModule(0x9, 0x11000004);
    }
    func_373();
    var0 = 1.0f;
    if (BattleObject(0x86, 0x4))
    {
        var0 = WorkModuleF(0, 0x2000333);
    }
    func_22(0x4d, 0, var0);
    func_78(func_372);
}

void func_372()
{
    rolloff_update(); // roll-off: edge sliding from the speed frame, not while shield is held (universal mechanics)
    if (func_374())
    {
        return;
    }
}

void func_373()
{
    func_75();
    WorkModule(0x16, 0x1e000074);
    ControlModule(0x2714, 0x18, 0);
    if (!StopModule(0x1))
    {
        func_368();
    }
    global16 = func_368;
}

void func_374()
{
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return 0x1;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return 0x1;
        }
    }
    if (WorkModule(0x15, 0x1e000074))
    {
        if (global38 & 0x1)
        {
            if (ItemModule(0x4) == 0x1)
            {
                if (ItemModule(0x5, 0x800000) == 0)
                {
                    if (WorkModule(0x6, 0x11000002) <= WorkModule(0x6, 0x120001f5))
                    {
                        func_16(0x8c, 0);
                        return 0x1;
                    }
                }
            }
        }
    }
    if (WorkModule(0x15, 0x1e00006e) == 0x1 && global38 & 0x1 && ItemModule(0x4) == 0)
    {
        func_16(0x37, 0x1);
        return;
    }
}

void func_375()
{
    func_376();
    func_22(0x4e, 0, 1.0f);
    func_78(func_377);
}

void func_376()
{
    ControlModule(0x271b);
    WorkModule(0x7, 0, 0x11000002);
    WorkModule(0x19, 0x1f000008);
    WorkModule(0x16, 0x1e000074);
    WorkModule(0x16, 0x1e000051);
    WorkModule(0x16, 0x1e000014);
    WorkModule(0x16, 0x1e000013);
    WorkModule(0x16, 0x1e000017);
    WorkModule(0x16, 0x1e000016);
    WorkModule(0x16, 0x1e000015);
    WorkModule(0x16, 0x1e000018);
    WorkModule(0x17, 0x1e00001c);
    ControlModule(0x2714, 0x18, 0);
    if (!StopModule(0x1))
    {
        func_379();
    }
    global16 = func_379;
}

void func_377()
{
    if (func_378())
    {
        return;
    }
}

void func_378()
{
    int var0;
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000074))
    {
        if (global38 & 0x1)
        {
            if (ItemModule(0x4) == 0x1)
            {
                if (ItemModule(0x5, 0x800000) == 0)
                {
                    if (WorkModule(0x6, 0x11000002) <= WorkModule(0x6, 0x120001f5))
                    {
                        func_16(0x8c, 0);
                        return 0x1;
                    }
                }
            }
        }
    }
    if (WorkModule(0x15, 0x1e000051))
    {
        if (WorkModule(0x6, 0x1300011f) != 0)
        {
            if (ControlModule(0x2712, 0x3))
            {
                if (global38 & 0x1)
                {
                    var0 = LinkModule(0x2, 0x3);
                    if (!var0)
                    {
                        func_16(0xf1, 0x1);
                        return 0x1;
                    }
                }
            }
        }
    }
    if (WorkModule(0x2712, 0x2100000f))
    {
        if (WorkModule(0x15, 0x1e000014))
        {
            if (global18 == 0)
            {
                if (func_84() >= WorkModuleF(0, 0x2000082))
                {
                    if (WorkModule(0x6, 0x11000002) < WorkModule(0x6, 0x12000081))
                    {
                        func_16(0x65, 0x1);
                        return 0x1;
                    }
                }
            }
        }
        if (WorkModule(0x15, 0x1e000013))
        {
            if (global18 == 0)
            {
                if (WorkModule(0x6, 0x11000002) < WorkModule(0x6, 0x12000081))
                {
                    func_16(0x64, 0);
                    return 0x1;
                }
            }
        }
    }
    if (WorkModule(0x2712, 0x21000010))
    {
        if (WorkModule(0x15, 0x1e000017))
        {
            if (GroundModule(0x2722, 0x6) == 0x1)
            {
                if (ControlModule(0x2722, 0x2) < WorkModule(0x6, 0x12000081))
                {
                    if (WorkModule(0x6, 0x11000002) < WorkModule(0x6, 0x12000081))
                    {
                        func_16(0x67, 0);
                        return 0x1;
                    }
                }
            }
        }
        if (WorkModule(0x15, 0x1e000016))
        {
            if (GroundModule(0x2722, 0x6) == 0x1)
            {
                if (global32 >= WorkModuleF(0, 0x200001f))
                {
                    if (WorkModule(0x6, 0x11000002) < WorkModule(0x6, 0x12000081))
                    {
                        func_16(0x67, 0x1);
                        return 0x1;
                    }
                }
            }
        }
        if (WorkModule(0x15, 0x1e000015))
        {
            if (GroundModule(0x2722, 0x6) == 0x1)
            {
                if (WorkModule(0x6, 0x11000002) < WorkModule(0x6, 0x12000081))
                {
                    func_16(0x66, 0);
                    return 0x1;
                }
            }
        }
        if (WorkModule(0x15, 0x1e000018))
        {
            if (GroundModule(0x2722, 0x1) == 0x1)
            {
                if (WorkModule(0x6, 0x11000002) < WorkModule(0x6, 0x12000081))
                {
                    func_16(0x68, 0);
                    return 0x1;
                }
            }
        }
    }
    if (func_55())
    {
        return 0x1;
    }
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return 0x1;
    }
}

void func_379()
{
    WorkModule(0x9, 0x11000002);
    if (WorkModule(0x6, 0x11000002) <= WorkModule(0x6, 0x120001f1))
    {
        func_103();
    }
    if (ItemModule(0x4) == 0x1)
    {
        if (WorkModule(0x6, 0x11000002) <= WorkModule(0x6, 0x120001f5))
        {
            func_105();
        }
    }
    if (WorkModule(0x2712, 0x2100000d))
    {
        if (!WorkModule(0x2712, 0x2100000e))
        {
            KineticModule(0, 0);
            WorkModule(0x2710, 0x2100000e);
            BattleObject(0x17, 0x4);
        }
        func_550();
    }
    if (WorkModule(0x15, 0x1e00001c) == 0 && global9 >= (float)WorkModule(0x6, 0x1300002a))
    {
        WorkModule(0x16, 0x1e00001c);
    }
}

void func_380()
{
    
}

void func_381()
{
    if (global6 == 0xe) // roll-off: slid off an edge -> Fall without the air speed cap (universal mechanics)
    {
        WorkModule(0x13, 0x1, 0x20000044);
        global63 = 1; // roll-off: Fall's main scales the carried speed (rolloff_fall_speed)
        global64 = 1; // roll-off: Fall's end puts the cap back
    }
    func_383();
}

void func_382()
{
    if (global6 == 0xe) // roll-off: slid off an edge -> Fall without the air speed cap (universal mechanics)
    {
        WorkModule(0x13, 0x1, 0x20000044);
        global63 = 1; // roll-off: Fall's main scales the carried speed (rolloff_fall_speed)
        global64 = 1; // roll-off: Fall's end puts the cap back
    }
    func_383();
}

void func_383()
{
    KineticModule(0x11, 0, 0, 0);
}

void func_384()
{
    float var0;
    if (global6 == 0x16 && WorkModule(0x15, 0x1e00001c) == 0)
    {
        var0 = (float)WorkModule(0x6, 0x120000bf) / WorkModuleF(0, 0x20000c0);
        WorkModule(0, var0, 0);
    }
}

void func_385()
{
    int var0;
    if (global4 == 0x22)
    {
        var0 = global5;
        if (var0 == 0x4c)
        {
            WorkModule(0x11, 0x2100000f);
        }
        else if (var0 == 0x47 || var0 == 0x48 || var0 == 0x49 || var0 == 0x4a || var0 == 0x4b || var0 == 0x13a)
        {
            WorkModule(0x11, 0x2100000f);
            WorkModule(0x11, 0x21000010);
            KineticModule(0x16, 0);
            KineticModule(0x17, 0);
        }
    }
    else
    {
        KineticModule(0x7, 0x4);
    }
}

void func_386()
{
    int var0;
    float var1;
    func_385();
    var0 = MotionModule(0x7);
    var1 = MotionModuleF(0x1);
    func_22(0x4e, 0, 1.0f);
    if (var0 == 0x1d || var0 == 0x1e)
    {
        if (WorkModule(0x10, 0x2000004e) == 0)
        {
            MotionModule(0x8, var0, 0, var1, 1.0f);
            MotionModule(0x13, 1.0f);
        }
        KineticModule(0, 0x50);
    }
    else
    {
        KineticModule(0, 0x13);
    }
}

void func_387()
{
    if (MotionModule(0x14))
    {
        KineticModule(0, 0x13);
    }
}

int func_388()
{
    StatusModule(0x5, 0, 0x51, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x2000, 0, 0x200000);
    return 0;
}

int func_389()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0xc000, 0xec, 0xc0, 0x42);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x2000, 0, 0);
    return 0;
}

int func_390()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0x4000, 0x68, 0, 0x2);
    StatusModule(0x2713, 0, 0x1, 0x1, 0, 0, 0, 0, 0, 0);
    return 0;
}

int func_391()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0xc000, 0xcec, 0x1900, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x2000, 0, 0);
    return 0;
}

int func_392()
{
    StatusModule(0x5, 0x2, 0x23, 0x5, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0x2000, 0, 0x1000000);
    return 0;
}

int func_393()
{
    StatusModule(0x5, 0x2, 0xa, 0x5, 0, 0x1, 0, 0, 0, 0x1a0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0x2000, 0, 0);
    return 0;
}

int func_394()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 2.0f, 0, 0x8000, 0x1a0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0x2000, 0, 0);
    return 0;
}

int func_395()
{
    StatusModule(0x5, 0, 0xf, 0x1, 0, 0x1, 2.0f, 0, 0x8000, 0x1a0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x2000, 0, 0);
    return 0;
}

int func_396()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0x180);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x2000, 0, 0);
    return 0;
}

int func_397()
{
    StatusModule(0x5, 0, 0xf, 0x1, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x2000, 0, 0);
    return 0;
}

void func_398()
{
    BattleObject(0x2d);
}

void func_399()
{
    float var0;
    int var1;
    WorkModule(0x7, WorkModule(0x6, 0x120000c4) + 0x2, 0x11000002);
    var0 = (float)WorkModule(0x6, 0x120000d5) + 0;
    var1 = (int)(var0 * WorkModuleF(0, 0x30000f9) + 0.5f);
    WorkModule(0x7, var1, 0x11000003);
    func_22(0x47, 0, 1.0f);
    if (WorkModule(0x10, 0x2000004e) == 0)
    {
        MotionModule(0x8, 0x48);
        MotionModule(0x5, 0);
    }
    func_401();
    if (!StopModule(0x1))
    {
        func_403();
    }
    global16 = func_403;
    func_78(func_400);
}

void func_400()
{
    if (WorkModule(0x10, 0x2100000d) == 0 && global9 > (float)0)
    {
        func_398();
        WorkModule(0x2710, 0x2100000d);
    }
    if (global18 == 0x2)
    {
        if (GroundModule(0x2727))
        {
            func_16(0x7d, 0);
            return;
        }
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (func_402())
    {
        return;
    }
    if (WorkModuleF(0, 0x3) < 0)
    {
        func_16(0x59, 0);
        return;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0x1c, 0);
            return;
        }
    }
}

void func_401()
{
    WorkModule(0x16, 0x1e000075);
    if (global4 == 0x1b)
    {
        if (global5 == 0x4)
        {
            WorkModule(0x16, 0x1e00006f);
        }
    }
    if (global4 == 0x1b)
    {
        if (global5 == 0x4)
        {
            WorkModule(0x16, 0x1e00006e);
            WorkModule(0x7, WorkModule(0x6, 0x120000e0), 0x11000004);
        }
    }
    WorkModule(0x16, 0x1e00006d);
    WorkModule(0x16, 0x1e000026);
    WorkModule(0x16, 0x1e000027);
    WorkModule(0x16, 0x1e000028);
    WorkModule(0x19, 0x1f000006);
}

int func_402()
{
    if (func_71(global56))
    {
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000075))
    {
        if (ItemModule(0x4) == 0x1)
        {
            if (ItemModule(0x5, 0x800000) == 0)
            {
                if (global38 & 0x1)
                {
                    if (global18 == 0)
                    {
                        func_16(0x8c, 0);
                        return 0x1;
                    }
                }
            }
        }
    }
    if (global4 == 0x1b)
    {
        if (global5 == 0x4)
        {
            if (WorkModule(0x15, 0x1e00006f))
            {
                if (func_88() <= WorkModuleF(0, 0x2000014))
                {
                    if (ControlModule(0x2712, 0))
                    {
                        if (global18 == 0)
                        {
                            if (ItemModule(0x4) == 0)
                            {
                                func_16(0x39, 0x1);
                                return 0x1;
                            }
                        }
                    }
                }
            }
        }
    }
    if (WorkModule(0x15, 0x1e000026))
    {
        if (global31 & 0x10000)
        {
            if (global18 == 0)
            {
                func_16(0x1f, 0x1);
                return 0x1;
            }
        }
    }
    if (WorkModule(0x15, 0x1e000027))
    {
        if (global31 & 0x4000)
        {
            if (global18 == 0)
            {
                func_16(0x20, 0x1);
                return 0x1;
            }
        }
    }
    if (WorkModule(0x15, 0x1e000028))
    {
        if (global31 & 0x8000)
        {
            if (global18 == 0)
            {
                func_16(0x21, 0x1);
                return 0x1;
            }
        }
    }
    if (global4 == 0x1b)
    {
        if (global5 == 0x4)
        {
            if (WorkModule(0x15, 0x1e00006e))
            {
                if (ControlModule(0x2712, 0))
                {
                    if (global18 == 0)
                    {
                        if (ItemModule(0x4) == 0)
                        {
                            func_16(0x37, 0x1);
                            return 0x1;
                        }
                    }
                }
            }
        }
    }
    if (WorkModule(0x15, 0x1e00006d))
    {
        if (global24 & 0x20000000)
        {
            if (global18 == 0)
            {
                func_16(0x35, 0x1);
                return 0x1;
            }
        }
    }
    if (func_51())
    {
        return 0x1;
    }
    if (global31 & 0x200)
    {
        if (func_34())
        {
            func_16(0x71, 0x1);
            return 0x1;
        }
    }
    return 0;
}

void func_403()
{
    float var0;
    if (WorkModule(0x10, 0x20000070) == 0)
    {
        var0 = WorkModuleF(0, 0x20000c7);
        var0 /= WorkModuleF(0, 0x30000f6);
        WorkModule(0x3, var0, 0x3);
        if (WorkModuleF(0, 0x3) < WorkModuleF(0, 0x4))
        {
            WorkModule(0, WorkModuleF(0, 0x4), 0x3);
        }
    }
    if (WorkModule(0x6, 0x11000002) > 0)
    {
        WorkModule(0xa, 0x11000002);
    }
    if (WorkModule(0x6, 0x11000003) > 0)
    {
        WorkModule(0xa, 0x11000003);
    }
    if (WorkModule(0x6, 0x11000004) >= 0)
    {
        WorkModule(0xa, 0x11000004);
        if (WorkModule(0x6, 0x11000004) < 0)
        {
            WorkModule(0x17, 0x1e00006f);
            WorkModule(0x17, 0x1e00006e);
        }
    }
    func_404();
}

void func_404()
{
    WorkModule(0xa, 0x11000007);
    if (WorkModule(0x6, 0x11000007) <= 0)
    {
        BattleObject(0x85);
        WorkModule(0x7, 0x8, 0x11000007);
    }
}

void func_405()
{
    func_401();
    if (!StopModule(0x1))
    {
        func_407();
    }
    global16 = func_407;
    func_78(func_406);
}

void func_406()
{
    if (global18 == 0x2)
    {
        if (GroundModule(0x2727))
        {
            func_16(0x7d, 0);
            return;
        }
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (func_402())
    {
        return;
    }
    if (WorkModuleF(0, 0x3) < 0)
    {
        func_16(0x59, 0);
        return;
    }
    if (ControlModule(0x2713, 0x3))
    {
        if (WorkModule(0x6, 0x11000002) <= 0)
        {
            if (global18 == 0)
            {
                func_16(0x1d, 0x1);
                return;
            }
        }
    }
}

void func_407()
{
    func_403();
    if (WorkModule(0x6, 0x11000003) > 0)
    {
        WorkModule(0xa, 0x11000003);
    }
    if (WorkModule(0x6, 0x11000005) > 0)
    {
        WorkModule(0xa, 0x11000005);
    }
}

void func_408()
{
    WorkModule(0x16, 0x1e00002c);
    WorkModule(0x16, 0x1e00002b);
    if (WorkModule(0x6, 0x11000005) > 0)
    {
        WorkModule(0x19, 0x1f000000);
        WorkModule(0x19, 0x1f000001);
        WorkModule(0x19, 0x1f000003);
    }
    WorkModule(0x7, WorkModule(0x6, 0x120000df), 0x11000009);
}

void func_409()
{
    func_408();
    func_22(0x49, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_411();
    }
    global16 = func_411;
    func_78(func_410);
}

void func_410()
{
    if (CancelModule(0x2713) == 0x1)
    {
        if (func_39() != 0)
        {
            return;
        }
    }
    else
    {
        if (func_43())
        {
            return;
        }
        if (func_44())
        {
            return;
        }
        if (func_47())
        {
            return;
        }
    }
    if (global18 == 0x2)
    {
        if (GroundModule(0x2727))
        {
            func_16(0x7d, 0);
            return;
        }
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e00002c))
    {
        if (global38 & 0x10)
        {
            if (global18 == 0)
            {
                func_16(0xa, 0x1);
                return;
            }
        }
    }
    if (WorkModule(0x15, 0x1e00002b))
    {
        if (global32 >= WorkModuleF(0, 0x200001f))
        {
            if (global47 < WorkModule(0x6, 0x12000020))
            {
                if (ControlModule(0x271c))
                {
                    if (global18 == 0)
                    {
                        func_16(0xa, 0x1);
                        return;
                    }
                }
            }
        }
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return;
        }
    }
}

void func_411()
{
    if (WorkModule(0x6, 0x11000009) > 0)
    {
        WorkModule(0xa, 0x11000009);
        if (WorkModule(0x6, 0x11000009) == 0)
        {
            CancelModule(0x2710);
        }
    }
}

void func_412()
{
    func_413(0x1);
    if (!WorkModule(0x10, 0x2100000f))
    {
        BattleObject(0x55, 0x1, 0x4a);
        WorkModule(0x2710, 0x2100000f);
    }
    func_78(func_414);
}

void func_413(int arg0)
{
    int var1;
    int var2;
    func_75();
    if (WorkModule(0x6, 0x11000003) > 0)
    {
        WorkModule(0x7, 0, 0x11000002);
        WorkModule(0x7, WorkModule(0x6, 0x120000d6), 0x11000005);
        SoundModule(0x2710, 0xd9);
        if (BattleObject(0x6e, 0x37))
        {
            var1 = BattleObject(0x77, 0x37);
            var2 = WorkModule(0x6, 0x1900006c + var1 - 0x1);
            WorkModule(0x7, var2 + 0x1, 0x11000006);
            WorkModule(0x2711, 0x2100000e);
        }
    }
    else if (arg0 == 0x1)
    {
        BattleObject(0x2e);
    }
    WorkModule(0x16, 0x1e00002a);
    if (!StopModule(0x1))
    {
        func_415();
    }
    global16 = func_415;
}

void func_414()
{
    if (global18 == 0x2)
    {
        if (GroundModule(0x2727))
        {
            func_16(0x7d, 0);
            return;
        }
        func_16(0x4c, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e00002a))
    {
        if (WorkModule(0x6, 0x11000009) == 0)
        {
            func_16(0x1c, 0);
            return;
        }
    }
    if (WorkModule(0x6, 0x11000009) == 0)
    {
        if (global18 == 0)
        {
            func_16(0x1d, 0);
            return;
        }
    }
    if (WorkModule(0x6, 0x1100000b) >= WorkModule(0x6, 0x12000350))
    {
        if (global18 == 0 && ControlModule(0x2712, 0x3) == 0x1)
        {
            if (global31 & 0x10000)
            {
                func_16(0x1f, 0x1);
                return 0x1;
            }
            if (global31 & 0x4000)
            {
                func_16(0x20, 0x1);
                return 0x1;
            }
            if (global31 & 0x8000)
            {
                func_16(0x21, 0x1);
                return 0x1;
            }
        }
    }
}

void func_415()
{
    if (WorkModule(0x6, 0x11000002) > 0)
    {
        WorkModule(0xa, 0x11000002);
    }
    if (ControlModule(0x2713, 0x3))
    {
        if (WorkModule(0x6, 0x11000002) <= 0)
        {
            WorkModule(0x17, 0x1e00002a);
        }
    }
    if (WorkModule(0x6, 0x11000009) > 0)
    {
        WorkModule(0xa, 0x11000009);
    }
    func_404();
}

void func_416()
{
    WorkModule(0, WorkModuleF(0, 0x20000c9), 0x3);
    WorkModule(0x2710, 0x21000003);
    HitModule(0x2710, 0x2);
    func_22(0xf0, 0, 1.0f);
    SoundModule(0x2710, 0x62);
    func_78(func_417);
}

void func_417()
{
    if (MotionModule(0x2712))
    {
        func_16(0x5a, 0);
        return;
    }
    if (global18 == 0)
    {
        func_16(0x5b, 0);
        return;
    }
}

void func_418()
{
    func_22(0x2e, 0, 1.0f);
    ControlModule(0x2718, 0x9, 0);
    func_78(func_419);
}

void func_419()
{
    if (global18 == 0)
    {
        func_16(0x5b, 0);
        return;
    }
}

void func_420()
{
    if (FighterUtil(0))
    {
        WorkModule(0x11, 0x2100001e);
    }
    else
    {
        WorkModule(0x12, 0x2100001e);
    }
    if (WorkModule(0x10, 0x2100001e))
    {
        func_22(0xd5, 0, 1.0f);
    }
    else
    {
        func_22(0xdf, 0, 1.0f);
    }
    func_78(func_421);
}

void func_421()
{
    if (!GroundModule(0x2722, 0x8))
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0x5c, 0);
            return;
        }
    }
}

void func_422()
{
    int var0;
    if (WorkModule(0x10, 0x2100001e))
    {
        func_22(0xf3, 0, 1.0f);
    }
    else
    {
        func_22(0xf4, 0, 1.0f);
    }
    var0 = WorkModule(0x6, 0x12000311) + 0x1;
    WorkModule(0x7, var0, 0x11000011);
    if (!StopModule(0x1))
    {
        func_424();
    }
    global16 = func_424;
    func_78(func_423);
}

void func_423()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712))
    {
        if (WorkModule(0x10, 0x2000006f))
        {
            func_16(0x5e, 0);
            return;
        }
        if (global18 == 0)
        {
            func_16(0x5d, 0);
            return;
        }
    }
}

void func_424()
{
    int var0;
    var0 = WorkModule(0x6, 0x11000011);
    if (var0 > 0)
    {
        var0--;
        if (var0 <= 0 && WorkModule(0x10, 0x21000022) == 0)
        {
            HitModule(0x2710, 0);
            WorkModule(0x2710, 0x21000022);
        }
        WorkModule(0x7, var0, 0x11000011);
    }
}

void func_425()
{
    func_22(0xf1, 0, 1.0f);
    func_78(func_426);
}

void func_426()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (func_96() || WorkModule(0x10, 0x2000006f))
    {
        if (global18 == 0)
        {
            func_16(0x5e, 0);
            return;
        }
    }
}

void func_427()
{
    func_22(0xf5, 0, 1.0f);
    func_78(func_428);
}

void func_428()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (global5 == 0x63)
    {
        if (CancelModule(0x2713) == 0x1 && func_39() != 0)
        {
            return;
        }
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return;
        }
    }
}

void func_429()
{
    int var0;
    var0 = global6;
    if (var0 == 0x1c || var0 == 0x1e)
    {
        if (WorkModule(0x10, 0x2100000d) == 0)
        {
            func_398();
        }
    }
    else
    {
        EffectModule(0x2723, 0x1000013, 0x1, 0x1);
        EffectModule(0x2723, 0x1000014, 0x1, 0x1);
    }
}

void func_430()
{
    int var0;
    var0 = global6;
    if (var0 == 0x1c || var0 == 0x1e)
    {
        
    }
    else
    {
        EffectModule(0x2723, 0x1000013, 0x1, 0x1);
        EffectModule(0x2723, 0x1000014, 0x1, 0x1);
    }
}

void func_431()
{
    
}

void func_432()
{
    int var0;
    func_430();
    var0 = global6;
    if (var0 == 0x1c)
    {
        if (WorkModule(0x10, 0x2000004e) == 0)
        {
            MotionModule(0x8, 0x48);
            MotionModule(0x5, 0);
        }
    }
}

void func_433()
{
    
}

void func_434()
{
    
}

void func_435()
{
    
}

void func_436()
{
    
}

void func_437()
{
    
}

void func_438()
{
    
}

void func_439()
{
    func_440();
}

void func_440()
{
    ShieldModule(0x2710, 0x2, 0);
}

void func_441()
{
    func_442();
}

void func_442()
{
    func_449();
    func_465();
}

void func_443()
{
    func_444();
}

void func_444()
{
    func_453();
    func_465();
}

void func_445()
{
    func_446();
}

void func_446()
{
    ShieldModule(0x2711, 0x2, 0);
}

void func_447()
{
    func_448();
}

void func_448()
{
    ShieldModule(0x2710, 0x2, 0);
    func_455();
}

void func_449()
{
    func_450();
}

void func_450()
{
    func_455();
}

void func_451()
{
    func_452();
}

void func_452()
{
    ShieldModule(0x2711, 0x2, 0);
}

void func_453()
{
    func_456();
    func_454();
}

void func_454()
{
    if (BattleObject(0x5d) == 0x1)
    {
        global46 = 0xfe;
        ControlModule(0x271f);
        global24 = 0;
        global31 = 0;
        global29 = 0;
    }
    if (WorkModule(0x6, 0x11000003) > 0)
    {
        WorkModule(0xa, 0x11000003);
    }
}

void func_455()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    if (WorkModule(0x10, 0x2000004e) == 0)
    {
        var0 = WorkModuleF(0, 0x1000006);
        var1 = WorkModuleF(0, 0x1000007);
        var2 = ControlModuleF(0x7);
        var3 = ControlModuleF(0x8);
        var2 = var0 + (var2 - var0) * WorkModuleF(0, 0x20000d4);
        var3 = var1 + (var3 - var1) * WorkModuleF(0, 0x20000d4);
        var4 = MathF(0, var2 * var2 + var3 * var3);
        if (var4 > 1.0f)
        {
            var4 = 1.0f;
        }
        MotionModule(0xa, 1.0f - var4 - MotionModuleF(0x2));
        var5 = MathF(0x1, var3, var2 * PostureModuleF(0)) * (float)0xb4 / M_PI;
        if (var5 > 360.0f)
        {
            var5 -= (float)0x168;
        }
        else if (var5 < (float)0)
        {
            var5 += 360.0f;
        }
        MotionModule(0x34, var5);
        WorkModule(0, var2, 0x1000006);
        WorkModule(0, var3, 0x1000007);
    }
    func_456();
}

void func_456()
{
    float var0;
    float var1;
    float var2;
    int var3;
    var0 = WorkModuleF(0, 0x3) / WorkModuleF(0, 0x20000c2) * WorkModuleF(0, 0x20000d3);
    var1 = WorkModuleF(0, 0x20000c3);
    var2 = WorkModuleF(0, 0x300002d);
    var0 = (var1 + (1.0f - var1) * var0) * var2;
    var3 = 0x1a;
    ModelModule(0, var3, var0, var0, var0);
}

void func_457()
{
    func_465();
}

void func_458()
{
    func_465();
}

void func_459()
{
    func_460();
    func_456();
}

void func_460()
{
    int var0;
    float var1;
    int var2;
    int var3;
    float var4;
    int var5;
    float var6;
    float var7;
    float var8;
    float var9;
    ShieldModule(0x2710, 0x2, 0);
    var0 = 0x4a;
    var1 = WorkModuleF(0, 0x100000b) * WorkModuleF(0, 0x20000cc);
    var2 = WorkModule(0x6, 0x1100000a);
    if (WorkModule(0x10, 0x20000075) == 0x1)
    {
        var1 *= WorkModuleF(0, 0x20000ce);
    }
    if (WorkModule(0x6, 0x11000003) > 0)
    {
        var0 = FighterUtil(0x22);
        var1 *= WorkModuleF(0, 0x20000d7);
    }
    var1 += WorkModuleF(0, 0x20000cd);
    var3 = (int)var1;
    if (var2 != 0x50000000)
    {
        CaptureModule(0xc, var2);
        var4 = (float)(var3 + WorkModule(0x6, 0x120000df));
        var4 = var4 * WorkModuleF(0, 0x20000cf);
        var5 = (int)var4;
        WorkModule(0x7, var5, 0x10000082);
    }
    WorkModule(0x7, var3, 0x11000009);
    var6 = sys_40(0x10, var0);
    func_22(var0, 0, var6);
    var7 = var1 * WorkModuleF(0, 0x20000d0);
    if (WorkModule(0x6, 0x11000003) > 0)
    {
        var7 *= WorkModuleF(0, 0x20000d8);
    }
    if (var7 > WorkModuleF(0, 0x20000d1))
    {
        var7 = WorkModuleF(0, 0x20000d1);
    }
    var8 = var7 * -WorkModuleF(0, 0x100000c);
    var9 = 0;
    KineticModule(0xe, 0x4, 0xb, var8, var9, 0, 0, 0);
    KineticModule(0xb, 0x4);
}

void func_461()
{
    func_462();
}

void func_462()
{
    func_456();
    func_465();
}

void func_463()
{
    func_464();
}

void func_464()
{
    func_453();
    func_465();
}

void func_465()
{
    int var0;
    int var1;
    float var2;
    float var3;
    int var4;
    float var5;
    float var6;
    var0 = WorkModule(0x6, 0x11000006);
    if (var0 > 0)
    {
        if (WorkModule(0x10, 0x2100000e) == 0)
        {
            BattleObject(0x7b);
            var1 = BattleObject(0x77, 0x37);
            var2 = WorkModuleF(0, 0x9000069 + var1 - 0x1);
            AttackModule(0x271a, 0, var2);
            var3 = WorkModuleF(0, 0x300002d) * WorkModuleF(0, 0x900006f + var1 - 0x1);
            AttackModule(0x271b, 0, var3);
            BattleObject(0x7c);
            var4 = EffectModule(0x30);
            var5 = WorkModuleF(0, 0x1000009);
            var6 = var3 / var5;
            EffectModule(0x19, var4, var6, var6, var6);
            WorkModule(0x2710, 0x2100000e);
        }
        var0--;
        if (var0 <= 0)
        {
            AttackModule(0x2718, 0);
        }
        WorkModule(0x7, var0, 0x11000006);
    }
}

void func_466()
{
    func_467();
}

void func_467()
{
    ShieldModule(0x2711, 0x2, 0);
    EffectModule(0x20, 0x1b);
}

void func_468()
{
    EffectModule(0x4, 0x1000003, 0x1a);
    ControlModule(0x2714, 0x19, 0);
}

int func_469()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0, 0x10, 0, 0);
    return 0;
}

int func_470()
{
    if (WorkModule(0x2712, 0x2000000b))
    {
        StatusModule(0x2711, 0xd7);
        return 0x1;
    }
    else if (WorkModule(0x2712, 0x2000000f))
    {
        if (WorkModule(0x6, 0x10000041) < 0x2)
        {
            StatusModule(0x2711, 0xa3);
            return 0x1;
        }
    }
    else if (ItemModule(0x11) == 0x6c)
    {
        StatusModule(0x2711, 0xa0);
        return 0x1;
    }
    return 0;
}

void func_471()
{
    int var0;
    var0 = 0x1;
    if (KineticModule(0x18) == var0)
    {
        var0 = 0x32;
    }
    StatusModule(0x5, 0x2, var0, 0x5, 0x4, 0x1, 0x20, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0x1000010, 0, 0x4);
}

int func_472()
{
    if (func_470() != 0)
    {
        return 0x1;
    }
    func_471();
    return 0;
}

int func_473()
{
    if (WorkModule(0x2712, 0x2000000b))
    {
        StatusModule(0x2711, 0xd7);
        return 0x1;
    }
    else if (WorkModule(0x2712, 0x2000000f))
    {
        if (WorkModule(0x6, 0x10000041) < 0x10000041)
        {
            StatusModule(0x2711, 0xa4);
            return 0x1;
        }
    }
    else if (ItemModule(0x11) == 0x6c)
    {
        StatusModule(0x2711, 0xa0);
        return 0x1;
    }
    return 0;
}

int func_474()
{
    if (func_473() != 0)
    {
        return 0x1;
    }
    StatusModule(0x5, 0x2, 0x2, 0x5, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0x1000010, 0, 0x8);
    return 0;
}

int func_475()
{
    if (WorkModule(0x2712, 0x2000000b))
    {
        StatusModule(0x2711, 0xd7);
        return 0x1;
    }
    else if (WorkModule(0x2712, 0x2000000f) && WorkModule(0x6, 0x10000041) < 0x2)
    {
        StatusModule(0x2711, 0xa4);
        return 0x1;
    }
    else if (ItemModule(0x11) == 0x6c)
    {
        StatusModule(0x2711, 0xa0);
        return 0x1;
    }
    StatusModule(0x5, 0x2, 0x32, 0x5, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0x10, 0, 0x8);
    return 0;
}

int func_476()
{
    if (func_548())
    {
        return 0x1;
    }
    StatusModule(0x5, 0x2, 0x13, 0x5, 0x4, 0x1, 0x82, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0x1000010, 0, 0);
    return 0;
}

int func_477()
{
    if (func_548())
    {
        return 0x1;
    }
    StatusModule(0x5, 0x2, 0x13, 0x5, 0x4, 0x1, 0x82, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0x1000010, 0, 0);
    return 0;
}

int func_478()
{
    if (func_558())
    {
        return 0x1;
    }
    StatusModule(0x5, 0, func_559(), 0x3, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0, 0x10, 0, 0);
    return 0;
}

int func_479()
{
    if (func_558())
    {
        return 0x1;
    }
    StatusModule(0x5, 0, func_559(), 0x3, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0, 0x10, 0, 0);
    return 0;
}

int func_480()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0x4, 0, 0);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0, 0x10, 0x8, 0);
    return 0;
}

int func_481()
{
    return func_478();
}

int func_482()
{
    StatusModule(0x5, 0x2, 0x8, 0x5, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x10, 0, 0);
    return 0;
}

int func_483()
{
    StatusModule(0x5, 0x2, 0x32, 0x5, 0x2, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x10, 0, 0);
    return 0;
}

int func_484()
{
    StatusModule(0x5, 0, 0x9, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

int func_485()
{
    StatusModule(0x5, 0x2, 0xa, 0x5, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x542, 0, 0, 0);
    return 0;
}

int func_486()
{
    StatusModule(0x5, 0x2, 0x13, 0x5, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0x10, 0, 0);
    return 0;
}

void func_487()
{
    int var0;
    int var1;
    var0 = WorkModule(0x6, 0x1000007b);
    var1 = WorkModule(0x6, 0x12000020) + var0;
    if (global47 >= var1 || global49 <= 0)
    {
        WorkModule(0x2710, 0x2100000d);
    }
    WorkModule(0x7, 0, 0x1000007b);
    func_76();
    WorkModule(0x16, 0x1e000002);
    WorkModule(0x16, 0x1e000064);
    WorkModule(0x16, 0x1e00005c);
    WorkModule(0x16, 0x1e000076);
    WorkModule(0x16, 0x1e000074);
    WorkModule(0x17, 0x1e000099);
    if (WorkModule(0x10, 0x2000004c))
    {
        WorkModule(0x2710, 0x21000005);
    }
    func_78(func_488);
}

void func_488()
{
    if (func_71(global57))
    {
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000099))
    {
        func_16(0xb, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e000002))
    {
        if (global18 == 0x2)
        {
            func_16(0xe, 0);
            return;
        }
    }
    if (WorkModule(0x15, 0x1e000064))
    {
        if (global24 & 0x4000)
        {
            if (global18 == 0)
            {
                func_16(0x154, 0x1);
                return;
            }
        }
    }
    if (func_45())
    {
        return;
    }
    if (WorkModule(0x15, 0x1e00005c))
    {
        if (global31 & 0x8)
        {
            if (global18 == 0)
            {
                func_16(0x31, 0x1);
                return;
            }
        }
    }
}

void func_489()
{
    int var0;
    float var1;
    float var2;
    int var3;
    func_546();
    var0 = MotionModule(0x7);
    var1 = MotionModuleF(0x1);
    var2 = MotionModuleF(0xa);
    var3 = MotionModule(0, var0);
    if (var1 + var2 >= (float)var3)
    {
        func_20(0x2);
        GroundModule(0x2710, 0x5);
        KineticModule(0, 0x1);
        WorkModule(0x16, 0x1e000099);
    }
}

int func_490(int arg0)
{
    int var1;
    func_76();
    ControlModule(0x271b);
    func_40();
    func_564();
    if (WorkModule(0x10, 0x20000039))
    {
        var1 = 0x1a;
    }
    else
    {
        if (func_89() >= WorkModuleF(0, 0x2000021))
        {
            if (WorkModule(0x10, 0x21000005))
            {
                var1 = 0x1c;
            }
            else
            {
                var1 = 0x1b;
            }
        }
        else if (WorkModule(0x10, 0x21000005))
        {
            var1 = 0x1a;
        }
        else
        {
            var1 = 0x19;
        }
        if (WorkModule(0x10, 0x20000016))
        {
            SoundModule(0x2710, 0x350063);
        }
    }
    if (arg0 != 0xffffffff)
    {
        var1 = arg0;
    }
    func_22(var1, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_550();
    }
    global16 = func_550;
    return var1;
}

void func_491()
{
    if (WorkModule(0x10, 0x2000004b) == 0x1)
    {
        if (WorkModuleF(0, 0x1a) > 0)
        {
            ItemModule(0x27, 0x63, 0x3);
        }
    }
}

void func_492()
{
    func_491();
    func_490(0xffffffff);
    func_78(func_493);
}

void func_493()
{
    if (func_56())
    {
        return 0x1;
    }
    if (func_41())
    {
        return 0x1;
    }
    if (func_565())
    {
        return 0x1;
    }
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return 0x1;
    }
    func_555();
}

void func_494()
{
    if (WorkModule(0x10, 0x2000004b) == 0x1)
    {
        if (WorkModuleF(0, 0x1a) > 0)
        {
            ItemModule(0x27, 0x63, 0x3);
        }
    }
}

void func_495()
{
    func_494();
    func_496(0, 0);
    func_78(func_497);
}

int func_496(int arg0, int arg1)
{
    int var2;
    func_76();
    ControlModule(0x271b);
    if (global4 == 0xc)
    {
        WorkModule(0x2710, 0x2000006c);
        WorkModule(0x7, WorkModule(0x6, 0x120000ad), 0x11000003);
    }
    func_40();
    func_564();
    if (arg1 == 0)
    {
        WorkModule(0x9, 0x10000001);
    }
    if (WorkModule(0x6, 0x1300010d) != 0)
    {
        if (WorkModule(0x2712, 0x20000019) == 0)
        {
            WorkModule(0x2710, 0x2100000f);
        }
    }
    var2 = 0xffffffff;
    if (arg0 != 0)
    {
        var2 = arg0;
    }
    else if (func_89() >= WorkModuleF(0, 0x2000021))
    {
        var2 = 0x1e;
    }
    else
    {
        var2 = 0x1d;
    }
    if (var2 != 0xffffffff)
    {
        func_22(var2, 0, 1.0f);
    }
    if (WorkModule(0x2712, 0x20000016))
    {
        SoundModule(0x2710, 0x350064);
    }
    WorkModule(0x2711, 0x2000005c);
    if (!StopModule(0x1))
    {
        func_551();
    }
    global16 = func_551;
    return var2;
}

int func_497()
{
    if (func_56())
    {
        return 0x1;
    }
    if (func_41())
    {
        return 0x1;
    }
    if (func_565())
    {
        return 0x1;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0x2)
        {
            func_16(0xf, 0);
            return 0x1;
        }
    }
    if (WorkModule(0x6, 0x1300010d) != 0)
    {
        if (WorkModule(0x2712, 0x20000019) == 0)
        {
            if (func_566())
            {
                return 0x1;
            }
        }
    }
    func_555();
    return 0;
}

void func_498()
{
    int var0;
    func_75();
    func_76();
    ControlModule(0x271b);
    WorkModule(0x9, 0x10000001);
    func_40();
    if (WorkModule(0x6, 0x1300010d) != 0)
    {
        if (WorkModule(0x2712, 0x20000019) == 0)
        {
            WorkModule(0x2710, 0x2100000f);
        }
    }
    KineticModule(0, 0x3);
    var0 = func_499();
    func_22(var0, 0, 1.0f);
    WorkModule(0x2711, 0x2000005c);
    if (!StopModule(0x1))
    {
        func_552();
    }
    global16 = func_552;
    func_78(func_500);
}

int func_499()
{
    int var0;
    int var1;
    var0 = WorkModule(0x6, 0x10000001);
    var1 = WorkModule(0x6, 0x13000022);
    if (var0 > var1)
    {
        var0 = var1;
    }
    if (var0 == 0x2)
    {
        return 0x1f;
    }
    else if (var0 == 0x3)
    {
        return 0x20;
    }
    else if (var0 == 0x4)
    {
        return 0x21;
    }
    else if (var0 == 0x5)
    {
        return 0x22;
    }
    return 0x23;
}

void func_500()
{
    int var0;
    if (func_41())
    {
        return;
    }
    if (WorkModule(0x6, 0x1300010d) != 0)
    {
        if (WorkModule(0x2712, 0x20000019) == 0)
        {
            if (func_566())
            {
                return;
            }
        }
    }
    var0 = WorkModule(0x6, 0x10000001);
    if (WorkModule(0x6, 0x10000001) == WorkModule(0x6, 0x10000002))
    {
        if (MotionModule(0x2712) && global18 == 0x2)
        {
            func_16(0xf, 0);
            return;
        }
    }
    else if (MotionModule(0x2712) && global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
}

void func_501()
{
    func_502();
    rolloff_fall_speed(); // roll-off: speed carried off the ledge x rolloff_air_speed_mult() (universal mechanics)
    func_78(func_503);
}

void func_502()
{
    int var0;
    int var1;
    float var2;
    float var3;
    float var4;
    func_40();
    var0 = 0x24;
    var1 = MotionModule(0x7);
    WorkModule(0x2711, 0x2000004f);
    if (global5 == 0x1)
    {
        if (MotionModule(0xc, 0x30) == 0x1)
        {
            var2 = MotionModuleF(0x1);
            var0 = 0x2f;
            if (var1 == 0xa)
            {
                var3 = WorkModuleF(0, 0x300010e);
                var4 = WorkModuleF(0, 0x300010f);
            }
            else if (var1 == 0xb)
            {
                var3 = WorkModuleF(0, 0x3000110);
                var4 = WorkModuleF(0, 0x3000111);
            }
            else
            {
                var3 = WorkModuleF(0, 0x3000112);
                var4 = WorkModuleF(0, 0x3000113);
            }
            if (var3 > var4)
            {
                if (var2 < var4 || var2 >= var3)
                {
                    var0 = 0x30;
                }
            }
            else if (var2 >= var3 && var2 < var4)
            {
                var0 = 0x30;
            }
            WorkModule(0x11, 0x2100000e);
        }
    }
    else if (global5 == 0x4 || global5 == 0x3)
    {
        if (MotionModule(0xc, 0x32) == 0x1)
        {
            if (global5 == 0x3)
            {
                var2 = 0;
            }
            else
            {
                var2 = MotionModuleF(0x1);
            }
            var0 = 0x31;
            var3 = WorkModuleF(0, 0x3000114);
            var4 = WorkModuleF(0, 0x3000115);
            if (var3 > var4)
            {
                if (var2 < var4 || var2 >= var3)
                {
                    var0 = 0x32;
                }
            }
            else if (var2 >= var3 && var2 < var4)
            {
                var0 = 0x32;
            }
            WorkModule(0x11, 0x2100000e);
        }
        WorkModule(0x2710, 0x2000004f);
    }
    func_22(var0, 0, 1.0f);
    WorkModule(0x16, 0x1e00002c);
    WorkModule(0x16, 0x1e00002b);
    if (!StopModule(0x1))
    {
        func_550();
    }
    global16 = func_550;
}

void func_503()
{
    if (func_56())
    {
        return 0x1;
    }
    if (func_549())
    {
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00002c))
    {
        if (!ControlModule(0x2724))
        {
            if (global24 & 0x10)
            {
                if (WorkModule(0x2712, 0x2100000d))
                {
                    if (WorkModule(0x6, 0x11000005) <= WorkModule(0x6, 0x12000027))
                    {
                        func_16(0xb, 0x1);
                        return;
                    }
                }
            }
        }
    }
    if (WorkModule(0x15, 0x1e00002b))
    {
        if (global32 >= WorkModuleF(0, 0x2000023))
        {
            if (global31 & 0x10)
            {
                if (ControlModule(0x271c))
                {
                    if (WorkModule(0x2712, 0x2100000d))
                    {
                        if (WorkModule(0x6, 0x11000005) <= WorkModule(0x6, 0x12000027))
                        {
                            func_16(0xb, 0x1);
                            return;
                        }
                    }
                }
            }
        }
    }
    if (func_41())
    {
        return;
    }
    if (WorkModule(0x10, 0x2100000e) == 0x1)
    {
        if (MotionModule(0x2712) == 0x1)
        {
            func_22(0x24, 0, 1.0f);
            WorkModule(0x12, 0x2100000e);
        }
    }
    func_555();
}

void func_504()
{
    func_505();
    func_78(func_506);
}

void func_505()
{
    func_40();
    func_22(0x27, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_550();
    }
    global16 = func_550;
}

void func_506()
{
    if (func_56())
    {
        return 0x1;
    }
    if (func_549())
    {
        return 0x1;
    }
    if (func_41())
    {
        return;
    }
    func_555();
}

void func_507()
{
    func_508();
    func_510();
    func_78(func_511);
}

void func_508()
{
    if (func_109())
    {
        func_562();
        if (!StopModule(0x1))
        {
            func_560();
        }
        global16 = func_560;
    }
}

float func_509()
{
    float var0;
    float var1;
    float var2;
    float var3;
    if (global5 == 0x22)
    {
        var0 = WorkModuleF(0, 0);
        if (var0 != 0)
        {
            var1 = (float)WorkModule(0x6, 0x120000bf) * MotionModuleF(0x9) - 0.009999999776482582f;
        }
        else
        {
            var1 = WorkModuleF(0, 0x3000028);
        }
    }
    else if (global5 == 0x46 || global5 == 0x13d)
    {
        var2 = WorkModuleF(0, 0x3000028);
        var3 = (float)WorkModule(0x6, 0x1000003e);
        if (var3 > var2)
        {
            var1 = var3;
        }
        else
        {
            var1 = var2;
        }
    }
    else if (global5 == 0xf1)
    {
        var1 = (float)WorkModule(0x6, 0x10000076);
    }
    else
    {
        var1 = WorkModuleF(0, 0x3000028);
    }
    return var1;
}

void func_510()
{
    float var0;
    var0 = func_509();
    WorkModule(0, var0, 0x1000006);
}

void func_511()
{
    if (func_512())
    {
        return;
    }
}

int func_512()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (func_109())
    {
        if (func_563())
        {
            return 0x1;
        }
        if (func_561())
        {
            return 0x1;
        }
    }
    else if (MotionModule(0x2712))
    {
        func_16(0, 0);
        return 0x1;
    }
    return 0;
}

void func_513()
{
    func_514();
    func_78(func_515);
}

void func_514()
{
    func_22(0x3a, 0, 1.0f);
    if (func_109())
    {
        func_562();
        if (!StopModule(0x1))
        {
            func_560();
        }
        global16 = func_560;
    }
}

void func_515()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (func_109())
    {
        if (func_563())
        {
            return 0x1;
        }
        if (func_561())
        {
            return 0x1;
        }
    }
    else if (MotionModule(0x2712))
    {
        func_16(0, 0);
        return;
    }
}

void func_516()
{
    if (WorkModule(0x2712, 0x2100000e) == 0 && WorkModule(0x2712, 0x2100000d) == 0x1)
    {
        WorkModule(0x19, 0x1f000000);
        WorkModule(0x19, 0x1f000001);
        WorkModule(0x19, 0x1f000002);
        WorkModule(0x19, 0x1f000003);
        WorkModule(0x19, 0x1f000004);
        WorkModule(0x19, 0x1f000005);
        WorkModule(0x19, 0x1f000006);
        WorkModule(0x19, 0x1f000007);
        WorkModule(0x2710, 0x2100000e);
    }
    if (WorkModule(0x2712, 0x21000010) == 0x1)
    {
        WorkModule(0x16, 0x1e00000b);
        WorkModule(0x2711, 0x21000010);
    }
    else
    {
        WorkModule(0x17, 0x1e00000b);
    }
}

void func_517()
{
    func_518();
    func_78(func_519);
}

void func_518()
{
    if (func_109())
    {
        if (!StopModule(0x1))
        {
            func_516();
        }
        global16 = func_516;
    }
}

int func_519()
{
    int var0;
    int var1;
    var0 = func_109();
    if (var0)
    {
        var1 = WorkModule(0x10, 0x21000009) == 0;
        if (func_43())
        {
            return;
        }
        if (func_44())
        {
            return;
        }
        if (func_46())
        {
            return;
        }
        if (func_47())
        {
            return;
        }
        if (func_48())
        {
            return;
        }
        if (func_49())
        {
            return;
        }
        if (func_51())
        {
            return;
        }
        if (func_52(var1))
        {
            return;
        }
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (var0)
    {
        if (func_563() == 0x1)
        {
            return 0x1;
        }
    }
    else if (MotionModule(0x2712))
    {
        func_16(0, 0);
        return 0x1;
    }
    return 0;
}

void func_520()
{
    func_507();
}

void func_521()
{
    ControlModule(0x271b);
    WorkModule(0x16, 0x1e000020);
    WorkModule(0x16, 0x1e000021);
    func_22(0x41, 0, 1.0f);
    func_78(func_522);
}

void func_522()
{
    if (func_56())
    {
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000020))
    {
        if (MotionModule(0x2712))
        {
            if (global18 == 0x2)
            {
                func_16(0x7f, 0);
                return;
            }
        }
    }
    if (WorkModule(0x15, 0x1e000021))
    {
        if (global18 == 0)
        {
            func_16(0x80);
            return;
        }
    }
}

void func_523()
{
    WorkModule(0x2710, 0x20000019);
    WorkModule(0x16, 0x1e000021);
    WorkModule(0x16, 0x1e00004f);
    WorkModule(0x19, 0x1f000008);
    func_78(func_524);
}

void func_524()
{
    if (func_56())
    {
        return 0x1;
    }
    if (global18 == 0 && MotionModuleF(0x1) >= WorkModuleF(0, 0x200004a) && KineticModuleF(0x2, 0x1) >= WorkModuleF(0, 0x200004b))
    {
        func_16(0x80);
        return;
    }
    if (func_55())
    {
        return;
    }
    if (global18 == 0x2)
    {
        if (ControlModule(0x2710, 0x2) || ControlModule(0x2710, 0x1) || WorkModule(0x2712, 0x2100000d))
        {
            func_16(0x82);
            return;
        }
    }
    if (WorkModule(0x15, 0x1e00004f))
    {
        if (ControlModule(0x2710, 0))
        {
            if (global18 == 0x2)
            {
                func_16(0x81);
                return;
            }
        }
    }
}

void func_525()
{
    if (MotionModule(0xc, 0x46))
    {
        func_22(0x46, 0, 1.0f);
        WorkModule(0x16, 0x1e00000e);
    }
    else
    {
        WorkModule(0x16, 0x1e00000f);
    }
    func_78(func_526);
}

void func_526()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0xc, 0x46))
    {
        if (WorkModule(0x15, 0x1e00000e))
        {
            if (MotionModule(0x2712))
            {
                if (global18 == 0)
                {
                    func_16(0x50, 0);
                    return;
                }
            }
        }
    }
    else if (WorkModule(0x15, 0x1e00000f))
    {
        if (global18 == 0)
        {
            func_16(0x54, 0);
            return;
        }
    }
}

void func_527()
{
    WorkModule(0x19, 0x1f000008);
    func_22(0x44, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_550();
    }
    global16 = func_550;
    func_78(func_528);
}

void func_528()
{
    if (func_55())
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        if (WorkModule(0x6, 0x10000001) < WorkModule(0x6, 0x10000002))
        {
            func_16(0xf, 0);
            return;
        }
        else
        {
            func_16(0x10, 0);
            return;
        }
    }
}

void func_529()
{
    WorkModule(0x19, 0x1f000008);
    func_22(0x45, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_550();
    }
    global16 = func_550;
    func_78(func_530);
}

void func_530()
{
    if (func_56())
    {
        return 0x1;
    }
    if (func_55())
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        if (WorkModule(0x6, 0x10000001) < WorkModule(0x6, 0x10000002))
        {
            func_16(0xf, 0);
            return;
        }
        else
        {
            func_16(0x10, 0);
            return;
        }
    }
}

void func_531()
{
    
}

void func_532()
{
    
}

void func_533()
{
    WorkModule(0x2711, 0x2000006c);
}

void func_534()
{
    if (TurnModule(0) && TurnModule(0x1) == 0)
    {
        TurnModule(0x2711);
    }
}

void func_535()
{
    if (global64) // roll-off: Fall over, the air speed cap is back (universal mechanics)
    {
        global64 = 0;
        WorkModule(0x14, 0x20000044);
    }
    
}

void func_536()
{
    
}

void func_537()
{
    
}

void func_538()
{
    
}

void func_539()
{
    
}

void func_540()
{
    
}

void func_541()
{
    
}

void func_542()
{
    
}

void func_543()
{
    
}

void func_544()
{
    
}

void func_545()
{
    
}

void func_546()
{
    func_547(0x2100000d);
}

void func_547(int arg0)
{
    if (WorkModule(0x10, arg0))
    {
        if (ControlModule(0x2713, 0x2))
        {
            WorkModule(0x2710, 0x21000005);
        }
    }
    else if (global32 < WorkModuleF(0, 0x2000022))
    {
        WorkModule(0x2710, 0x21000005);
    }
}

int func_548()
{
    if (WorkModule(0x2712, 0x2000001b))
    {
        StatusModule(0x2711, 0x4c);
        return 0x1;
    }
    else if (WorkModule(0x2712, 0x2000000b))
    {
        StatusModule(0x2711, 0xd8);
        return 0x1;
    }
    else if (ItemModule(0x11) == 0x6c)
    {
        StatusModule(0x2711, 0xa1);
        return 0x1;
    }
    return 0;
}

int func_549()
{
    if (WorkModule(0x10, 0x2000000b))
    {
        func_16(0xd8, 0);
        return 0x1;
    }
    return 0;
}

void func_550()
{
    if (WorkModule(0x1c, 0x1f00000e))
    {
        func_105();
        func_104();
    }
    func_553();
}

void func_551()
{
    if (ControlModule(0x2712, 0x2))
    {
        WorkModule(0x9, 0x11000002);
    }
    else
    {
        WorkModule(0x7, 0, 0x11000002);
    }
    func_550();
    if (WorkModule(0x2712, 0x2100000f))
    {
        func_557();
    }
    if (WorkModule(0xf, 0x11000003))
    {
        WorkModule(0x2711, 0x2000006c);
    }
}

void func_552()
{
    if (ControlModule(0x2712, 0x2))
    {
        WorkModule(0x9, 0x11000002);
    }
    else
    {
        WorkModule(0x7, 0, 0x11000002);
    }
    func_550();
    if (WorkModule(0x10, 0x2100000f))
    {
        func_557();
    }
}

void func_553()
{
    if (func_554())
    {
        func_76();
        WorkModule(0x2710, 0x21000001);
        if (WorkModuleF(0, 0x24) > 0)
        {
            GroundModule(0x8, 0x1);
        }
        WorkModule(0x2710, 0x2000006b);
    }
}

int func_554()
{
    float var0;
    if (WorkModule(0x10, 0x21000001))
    {
        return 0;
    }
    if (KineticModule(0x4, 0x2) == 0 || KineticModule(0x5, 0x2) == 0x1)
    {
        return 0;
    }
    var0 = KineticModuleF(0x1, 0x1);
    if (global32 <= WorkModuleF(0, 0x2000046) && global47 < WorkModule(0x6, 0x12000047) && var0 < 0)
    {
        if (var0 >= -WorkModuleF(0, 0x300001b))
        {
            return 0x1;
        }
    }
    return 0;
}

void func_555()
{
    if (WorkModule(0x10, 0x20000047) == 0)
    {
        return;
    }
    if (func_556())
    {
        WorkModule(0x2710, 0x21000007);
        WorkModule(0x2711, 0x21000001);
    }
    else
    {
        WorkModule(0x2711, 0x21000007);
    }
}

int func_556()
{
    int var0;
    if (WorkModule(0x6, 0x1000006a) <= 0)
    {
        return 0;
    }
    if (KineticModule(0x4, 0x2) == 0 || KineticModule(0x5, 0x2) == 0x1)
    {
        return 0;
    }
    var0 = ControlModule(0x2712, 0x2);
    if ((var0 || global32 >= WorkModuleF(0, 0x200001f)) && func_91() < 0)
    {
        return 0x1;
    }
    if (var0 && global32 <= WorkModuleF(0, 0x200001a))
    {
        if (WorkModule(0x10, 0x21000007) == 0)
        {
            if (KineticModuleF(0xb, 0x1) > 0)
            {
                KineticModule(0x2719, 0x1);
            }
        }
        return 0x1;
    }
    return 0;
}

void func_557()
{
    float var0;
    float var1;
    if (func_84() >= WorkModuleF(0, 0x2000048))
    {
        if (WorkModule(0x2712, 0x21000011) == 0)
        {
            var0 = (float)global46 * -PostureModuleF(0);
            if (var0 < (float)WorkModule(0x6, 0x12000049))
            {
                WorkModule(0x2710, 0x21000011);
            }
        }
        else
        {
            var1 = (float)global46 * PostureModuleF(0);
            if (var1 < (float)WorkModule(0x6, 0x12000049))
            {
                WorkModule(0x2710, 0x21000012);
            }
        }
    }
}

int func_558()
{
    float var0;
    if (WorkModule(0x2712, 0x2000001b))
    {
        StatusModule(0x2711, 0x4d);
        return 0x1;
    }
    var0 = WorkModuleF(0, 0x28);
    if (var0 > 0)
    {
        StatusModule(0x2711, 0x3);
        return 0x1;
    }
    return 0;
}

int func_559()
{
    if (WorkModule(0x10, 0x21000001) && WorkModuleF(0, 0x24) > 0)
    {
        return 0x10;
    }
    return 0xf;
}

void func_560()
{
    if (WorkModule(0x10, 0x2100000f))
    {
        WorkModule(0x1b, 0x1e000036);
        WorkModule(0x16, 0x1e000034);
        WorkModule(0x2711, 0x2100000f);
    }
    if (!WorkModule(0x10, 0x2100000e))
    {
        if (WorkModule(0x10, 0x2100000d))
        {
            func_38();
            WorkModule(0x1b, 0x1e000034);
            WorkModule(0x16, 0x1e000036);
            WorkModule(0x2710, 0x2100000f);
            WorkModule(0x2710, 0x2100000e);
        }
    }
    if (WorkModule(0x10, 0x21000010))
    {
        WorkModule(0x16, 0x1e00000b);
        WorkModule(0x2711, 0x21000010);
    }
    else
    {
        WorkModule(0x17, 0x1e00000b);
    }
}

int func_561()
{
    if (func_39())
    {
        return 0x1;
    }
    if (func_71(global58))
    {
        return 0x1;
    }
    return 0;
}

void func_562()
{
    WorkModule(0x2710, 0x21000010);
    WorkModule(0x17, 0x1e00000b);
}

int func_563()
{
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return 0x1;
        }
    }
    if (WorkModule(0x15, 0x1e000036))
    {
        if (global32 <= WorkModuleF(0, 0x200001a))
        {
            if (global18 == 0)
            {
                func_16(0x12, 0x1);
                return 0x1;
            }
        }
    }
    return 0;
}

void func_564()
{
    WorkModule(0x16, 0x1e00001a);
}

int func_565()
{
    if (WorkModule(0x15, 0x1e00001a))
    {
        if (GroundModule(0x2722, 0x1))
        {
            if (global18 == 0x2)
            {
                func_16(0x6a, 0);
                return 0x1;
            }
        }
    }
    return 0;
}

int func_566()
{
    if (WorkModule(0x6, 0x11000002) >= WorkModule(0x6, 0x13000025))
    {
        if (WorkModule(0x2712, 0x21000010))
        {
            if (global18 == 0x2)
            {
                func_16(0x7e, 0x1);
                return 0x1;
            }
        }
    }
    if (WorkModule(0x2712, 0x21000012))
    {
        if (WorkModule(0x2712, 0x21000010))
        {
            if (global18 == 0x2)
            {
                func_16(0x7e, 0x1);
                return 0x1;
            }
        }
    }
    return 0;
}

int func_567()
{
    if (WorkModule(0x10, 0x2000004b) == 0)
    {
        return 0;
    }
    if (global4 == 0x10a || global4 == 0x10b)
    {
        return 0;
    }
    if ((ControlModule(0x2712, 0x2) || global32 >= WorkModuleF(0, 0x200001f)) && func_91() < 0)
    {
        func_16(0x10a, 0x1);
        return 0x1;
    }
    return 0;
}

int func_568()
{
    StatusModule(0x5, 0x2, 0x47, 0x5, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0x762, 0x10, 0x800, 0x4);
    return 0;
}

void func_569()
{
    ControlModule(0x271a);
    ControlModule(0x271b);
    ItemModule(0xf, 0);
    WorkModule(0x16, 0x1e00001c);
    WorkModule(0x16, 0x1e00001b);
    func_40();
    WorkModule(0x1a, 0x1f000008);
    WorkModule(0x9, 0x10000041);
    SoundModule(0x2710, 0x350021);
    if (WorkModule(0x10, 0x20000016))
    {
        SoundModule(0x2710, 0x350063);
    }
    func_22(0x15b, 0, 1.0f);
    func_78(func_570);
}

void func_570()
{
    float var0;
    if (func_56())
    {
        return;
    }
    if (func_41())
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0xa5, 0);
        return;
    }
    if (global18 == 0)
    {
        var0 = KineticModuleF(0x1, 0x1);
        if (WorkModule(0x15, 0x1e00001c) && WorkModule(0x6, 0x1000000d) < WorkModule(0x6, 0x13000029) && var0 < WorkModuleF(0, 0x3000159))
        {
            func_16(0x17, 0);
            return;
        }
        if (WorkModule(0x15, 0x1e00001b) && var0 < WorkModuleF(0, 0x3000159))
        {
            func_16(0x16, 0);
        }
    }
}

void func_571()
{
    
}

int func_572()
{
    StatusModule(0x5, 0x2, 0x48, 0x5, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0x762, 0x10, 0x800, 0x8);
    return 0;
}

void func_573()
{
    func_574();
    func_78(func_575);
}

void func_574()
{
    ControlModule(0x271a);
    ControlModule(0x271b);
    ItemModule(0xf, 0);
    WorkModule(0x9, 0x10000001);
    func_40();
    WorkModule(0x9, 0x10000041);
    SoundModule(0x2710, 0x350022);
    if (WorkModule(0x10, 0x20000016))
    {
        SoundModule(0x2710, 0x350064);
    }
    WorkModule(0x2711, 0x2000005c);
    func_22(0x15c, 0, 1.0f);
}

void func_575()
{
    if (func_56())
    {
        return;
    }
    if (func_41())
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0xa5, 0);
        return;
    }
    func_555();
}

void func_576()
{
    
}

int func_577()
{
    StatusModule(0x5, 0x2, 0x13, 0x5, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0x762, 0x10, 0, 0);
    return 0;
}

void func_578()
{
    ItemModule(0xf, 0);
    func_22(0x15d, 0, 1.0f);
    func_40();
    func_78(func_579);
}

void func_579()
{
    if (func_56())
    {
        return;
    }
    if (func_41())
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return;
    }
    func_555();
}

void func_580()
{
    
}

void func_581()
{
    float var0;
    int var1;
    float var2;
    float var3;
    if (global4 == 0xe)
    {
        WorkModule(0x7, 0x25, 0x11000002);
        WorkModule(0x7, 0x26, 0x11000003);
        if (WorkModule(0x10, 0x2000005f))
        {
            var0 = WorkModuleF(0, 0x20000a8);
            KineticModule(0x11, 0x1, var0);
        }
    }
    else if (global4 == 0xf)
    {
        WorkModule(0x7, 0x28, 0x11000002);
        WorkModule(0x7, 0x29, 0x11000003);
    }
    else if (global4 == 0x10)
    {
        WorkModule(0x7, 0x2b, 0x11000002);
        WorkModule(0x7, 0x2c, 0x11000003);
        var1 = WorkModule(0x6, 0x10000000);
        var2 = PostureModuleF(0x2);
        AudienceManager(0x1, var1, var2);
        EffectModule(0x1f, 0x18, 0);
    }
    WorkModule(0x7, 0xffffffff, 0x11000004);
    WorkModule(0, 0, 0x1000006);
    var3 = WorkModuleF(0, 0x1);
    if (var3 != 1.0f)
    {
        KineticModule(0x6, 0x2, var3);
    }
    if (global5 == 0x1 || global5 == 0x4 || global5 == 0x3)
    {
        WorkModule(0x2710, 0x2100000d);
    }
}

void func_582()
{
    float var0;
    float var1;
    float var2;
    float var3;
    int var4;
    float var5;
    int var6;
    if (WorkModule(0x10, 0x2100000e) == 0)
    {
        if (WorkModule(0x10, 0x2000004e) == 0)
        {
            var0 = WorkModuleF(0, 0x1000006);
            var1 = (global48 - var0) * WorkModuleF(0, 0x2000029);
            var0 += var1;
            var2 = func_13(var0);
            WorkModule(0, var0, 0x1000006);
            var3 = MotionModuleF(0x2);
            if (var2 < WorkModuleF(0, 0x200002a))
            {
                MotionModule(0x9);
                MotionModule(0xa, 1.0f - var3);
                WorkModule(0x7, 0xffffffff, 0x11000004);
            }
            else
            {
                var4 = WorkModule(0x6, 0x11000004);
                var5 = var0 * PostureModuleF(0);
                if (var5 > (float)0)
                {
                    var6 = WorkModule(0x6, 0x11000002);
                }
                else
                {
                    var6 = WorkModule(0x6, 0x11000003);
                }
                if (var6 != var4)
                {
                    MotionModule(0x9);
                    MotionModule(0x8, var6, 0x1, MotionModuleF(0x1));
                    WorkModule(0x7, var6, 0x11000004);
                }
                MotionModule(0xa, 1.0f - var2 - var3);
            }
        }
    }
    if (WorkModule(0x10, 0x2100000d))
    {
        WorkModule(0x9, 0x11000005);
    }
}

void func_583()
{
    MotionModule(0x9);
    WorkModule(0, 1.0f, 0x1);
    if (global4 == 0x10)
    {
        EffectModule(0x20, 0x18);
    }
}

void func_584()
{
    int var0;
    float var1;
    float var2;
    var0 = WorkModule(0x6, 0x1300000c);
    if (var0 == 0)
    {
        
    }
    var1 = (float)var0;
    var2 = (float)MotionModule(0, 0x18) / var1;
    if (var2 < 1.0f)
    {
        var2 += 0.0010000000474974513f;
    }
    func_22(0x18, 0, var2);
}

void func_585()
{
    float var0;
    var0 = PostureModuleF(0);
    if (global48 * var0 < WorkModuleF(0, 0x2000006))
    {
        BattleObject(0x1d, var0, 0x1);
    }
}

void func_586()
{
    float var0;
    float var1;
    int var2;
    int var3;
    int var4;
    if (global4 == 0x16 || global4 == 0x1a)
    {
        if (global4 == 0x1a)
        {
            EffectModule(0x2f, 0x1);
        }
        var0 = 1.0f;
        if (global5 == 0x22)
        {
            var1 = WorkModuleF(0, 0);
            if (var1 != 0)
            {
                var2 = MotionModule(0, 0x3b);
                var0 = (float)var2 / var1;
            }
        }
        else if (global5 == 0x46 || global5 == 0x13d)
        {
            var1 = (float)WorkModule(0x6, 0x1000003e);
            var2 = MotionModule(0, 0x3b);
            if (var1 > (float)var2)
            {
                var0 = (float)var2 / var1;
            }
        }
        func_22(0x3b, 0, var0);
    }
    else if (global4 == 0x17)
    {
        
    }
    else if (global4 == 0x18)
    {
        var3 = WorkModule(0x6, 0x11000002) - 0x68;
        var4 = 0x6d + var3;
        func_587(var4, 0x300001c + var3);
    }
    else if (global4 == 0x19)
    {
        var0 = 1.0f;
        var1 = WorkModuleF(0, 0);
        if (var1 != (float)0)
        {
            var2 = MotionModule(0, 0x2d);
            var0 = (float)var2 / var1;
        }
        func_22(0x2d, 0, var0);
    }
    if (WorkModule(0x10, 0x2000004f) == 0x1)
    {
        WorkModule(0x2710, 0x21000008);
        WorkModule(0x2711, 0x2000004f);
    }
}

void func_587(int arg0, int arg1)
{
    float var2;
    float var3;
    int var4;
    float var5;
    var2 = WorkModuleF(0, arg1);
    var3 = 1.0f;
    if (var2 != (float)0)
    {
        var4 = MotionModule(0, arg0);
        var5 = var2 + var2 * WorkModuleF(0, 0x20000be);
        var3 = (float)var4 / var5;
    }
    func_22(arg0, 0, var3);
}

void func_588()
{
    int var0;
    int var1;
    float var2;
    float var3;
    if (global4 == 0x18)
    {
        var0 = WorkModule(0x6, 0x11000002) - 0x68;
        var1 = 0x6d + var0;
        var2 = 1.0f;
        var3 = WorkModuleF(0, 0x300001c + var0);
        if (var3 != (float)0)
        {
            var2 = 1.0f;
        }
        func_22(var1, 0, var2);
    }
    else
    {
        func_586();
    }
}

void func_589(int arg0)
{
    int var1;
    float var2;
    WorkModule(0x9, 0x11000004);
    var1 = WorkModule(0x6, 0x11000004);
    var2 = WorkModuleF(0, arg0);
    if ((float)var1 >= var2)
    {
        WorkModule(0x11, 0x2100000d);
    }
}

void func_590()
{
    float var0;
    int var1;
    int var2;
    if (!WorkModule(0x10, 0x20000003))
    {
        if (global4 == 0x16 || global4 == 0x1a)
        {
            var0 = WorkModuleF(0, 0x1000006);
            if (var0 != -1.0f && var0 <= MotionModuleF(0x1))
            {
                WorkModule(0x11, 0x2100000d);
            }
        }
        else if (global4 == 0x17)
        {
            var0 = WorkModuleF(0, 0x3000027);
            if (var0 != -1.0f && var0 <= MotionModuleF(0x1))
            {
                WorkModule(0x11, 0x2100000d);
            }
        }
        else if (global4 == 0x18)
        {
            var1 = MotionModule(0x7);
            var2 = var1 - 0x6d;
            func_589(0x300001c + var2);
        }
        else if (global4 == 0x19)
        {
            
        }
    }
}

void func_591()
{
    int var0;
    int var1;
    if (!WorkModule(0x10, 0x20000003))
    {
        if (global4 == 0x18)
        {
            if (WorkModule(0x10, 0x21000012) == 0)
            {
                var0 = MotionModule(0x7);
                var1 = var0 - 0x6d;
                func_589(0x300001c + var1);
            }
        }
    }
}

void func_592()
{
    if (global4 == 0x1a)
    {
        EffectModule(0x2f, 0);
    }
    WorkModule(0, 0, 0);
    WorkModule(0x12, 0x20000003);
}

int func_593()
{
    if (func_548())
    {
        return 0x1;
    }
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0x1000010, 0, 0);
    return 0;
}

int func_594()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0, 0x1008010, 0, 0);
    return 0;
}

int func_595()
{
    StatusModule(0x5, 0, 0xe, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x1000010, 0, 0x8000000);
    return 0;
}

int func_596()
{
    StatusModule(0x5, 0, 0xe, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x1000010, 0, 0x8000000);
    return 0;
}

int func_597()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0x1000010, 0, 0);
    return 0;
}

void func_598()
{
    func_599();
    func_78(func_600);
}

void func_599()
{
    WorkModule(0x7, 0, 0x11000003);
    func_616();
    WorkModule(0x19, 0x1f000002);
    WorkModule(0x1b, 0x1e00003c);
    func_22(0x33, 0, 1.0f);
}

void func_600()
{
    if (func_549())
    {
        return 0x1;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    else if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0x12, 0);
            return;
        }
    }
    if (func_617())
    {
        return;
    }
    if (func_46())
    {
        return;
    }
    if (WorkModule(0x6, 0x11000002) == 0)
    {
        if (global18 == 0)
        {
            func_16(0x71, 0);
            return;
        }
    }
}

void func_601()
{
    BattleObject(0xa, 0x1, WorkModule(0x6, 0x12000095));
    func_616();
    WorkModule(0x16, 0x1e000035);
    WorkModule(0x1b, 0x1e000062);
    WorkModule(0x1b, 0x1e000063);
    WorkModule(0x1b, 0x1e00003c);
    if (WorkModule(0x6, 0x1300011b) == 0x1)
    {
        WorkModule(0x1b, 0x1e00002d);
        func_618();
        func_620();
    }
    func_604();
    func_78(func_602);
}

void func_602()
{
    int var0;
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (func_617())
    {
        return;
    }
    if (func_619())
    {
        return 0x1;
    }
    if (func_621())
    {
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000035))
    {
        if (global32 > WorkModuleF(0, 0x200001a))
        {
            if (global18 == 0)
            {
                func_16(0x15, 0x1);
                return 0x1;
            }
        }
    }
    var0 = 0;
    if (!StatusModule(0x6))
    {
        var0 = func_603();
    }
    if (var0)
    {
        func_604();
    }
}

int func_603()
{
    int var0;
    int var1;
    int var2;
    var0 = 0;
    var1 = MotionModule(0x7);
    if (var1 == 0x36)
    {
        if (ItemModule(0x25) != 0x36)
        {
            var0 = 0x1;
        }
    }
    else if (global9 >= 1.0f)
    {
        if (MotionModule(0x2712))
        {
            var0 = 0x1;
        }
        else if (ItemModule(0x4, 0) && ItemModule(0x11) == 0x51)
        {
            var2 = ItemModule(0x19);
            if (var2 != 0xffffffff && var2 != var1)
            {
                var0 = 0x1;
            }
        }
    }
    return var0;
}

void func_604()
{
    int var0;
    if (ItemModule(0x25) == 0x36)
    {
        func_22(0x36, 0, 1.0f);
    }
    else
    {
        var0 = FighterUtil(0x10, 0x34);
        if (var0 == 0x1)
        {
            func_22(0x35, 0, 1.0f);
        }
        else if (var0 == 0xffffffff)
        {
            MotionModule(0x2711, 0);
        }
        else
        {
            func_22(0x34, 0, 1.0f);
        }
    }
}

void func_605()
{
    func_616();
    WorkModule(0x16, 0x1e000057);
    WorkModule(0x16, 0x1e000035);
    WorkModule(0x1b, 0x1e000062);
    WorkModule(0x1b, 0x1e000063);
    WorkModule(0x1b, 0x1e00003c);
    WorkModule(0x1b, 0x1e000058);
    func_620();
    func_22(0x37, 0, 1.0f);
    func_78(func_606);
}

void func_606()
{
    float var0;
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (func_617())
    {
        return;
    }
    if (func_621())
    {
        return 0x1;
    }
    if (global32 <= WorkModuleF(0, 0x200001a))
    {
        var0 = func_88();
        if (var0 < WorkModuleF(0, 0x200001b) && var0 >= WorkModuleF(0, 0x200001d))
        {
            if (global18 == 0)
            {
                func_16(0x12, 0x1);
                return;
            }
        }
    }
    if (global38 & 0x1)
    {
        if (global18 == 0)
        {
            if (WorkModule(0x15, 0x1e000057))
            {
                func_16(0x2a, 0x1);
                return 0x1;
            }
        }
    }
    if (WorkModule(0x15, 0x1e000035))
    {
        if (global32 > WorkModuleF(0, 0x200001a))
        {
            if (global18 == 0)
            {
                func_16(0x15, 0x1);
                return 0x1;
            }
        }
    }
}

void func_607()
{
    func_616();
    WorkModule(0x16, 0x1e000057);
    WorkModule(0x16, 0x1e000035);
    WorkModule(0x1b, 0x1e000062);
    WorkModule(0x1b, 0x1e000063);
    WorkModule(0x1b, 0x1e00003c);
    WorkModule(0x1b, 0x1e000055);
    WorkModule(0x1b, 0x1e000058);
    func_618();
    func_22(0x38, 0, 1.0f);
    func_78(func_608);
}

void func_608()
{
    float var0;
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (func_617())
    {
        return;
    }
    if (func_619())
    {
        return 0x1;
    }
    if (global32 <= WorkModuleF(0, 0x200001a))
    {
        var0 = func_88();
        if (var0 >= WorkModuleF(0, 0x200001d) && var0 < WorkModuleF(0, 0x200001b))
        {
            if (global18 == 0)
            {
                func_16(0x12, 0x1);
                return;
            }
        }
    }
    if (global38 & 0x1)
    {
        if (global18 == 0)
        {
            if (WorkModule(0x15, 0x1e000057))
            {
                func_16(0x2a, 0x1);
                return 0x1;
            }
        }
    }
    if (WorkModule(0x15, 0x1e000035))
    {
        if (global32 > WorkModuleF(0, 0x200001a))
        {
            if (global18 == 0)
            {
                func_16(0x15, 0x1);
                return 0x1;
            }
        }
    }
}

void func_609()
{
    func_616();
    WorkModule(0x1b, 0x1e000062);
    WorkModule(0x1b, 0x1e000063);
    func_22(0x39, 0, 1.0f);
    func_78(func_610);
}

void func_610()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (CancelModule(0x2713) == 0x1)
    {
        if (func_53())
        {
            func_16(0x11);
            return;
        }
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (func_617())
    {
        return;
    }
    else if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return;
        }
    }
}

void func_611()
{
    
}

void func_612()
{
    
}

void func_613()
{
    
}

void func_614()
{
    
}

void func_615()
{
    
}

void func_616()
{
    WorkModule(0x19, 0x1f000000);
    WorkModule(0x19, 0x1f000001);
    WorkModule(0x19, 0x1f000003);
    WorkModule(0x19, 0x1f000005);
    WorkModule(0x19, 0x1f000006);
    WorkModule(0x19, 0x1f000007);
    WorkModule(0x1b, 0x1e00002f);
    WorkModule(0x1b, 0x1e000031);
    WorkModule(0x1b, 0x1e000034);
}

int func_617()
{
    int var0;
    float var1;
    if (func_43())
    {
        return 0x1;
    }
    if (func_44())
    {
        return 0x1;
    }
    if ((global24 & 0x10) != 0)
    {
        if (WorkModule(0x15, 0x1e00007b) == 0x1 && ItemModule(0x5, 0x4) == 0x1)
        {
            func_16(0x94, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000082) == 0x1 && ItemModule(0x5, 0x2) == 0x1)
        {
            func_16(0x98, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000059))
        {
            func_16(0x2b, 0x1);
            return 0x1;
        }
    }
    if (WorkModule(0x15, 0x1e000055))
    {
        if (global24 & 0x2)
        {
            var0 = ControlModule(0x16, 0, 0x1);
            var1 = PostureModuleF(0);
            printf("status_SquatWait_Main turn_lr: %d, lr: %f", var0, var1);
            if (var0 == 0x1 && var1 != -1.0f || var0 == 0x2 && var1 != 1.0f)
            {
                printf("status_SquatWait_Main 1");
                ControlModule(0x17, 0, 0x1);
                ControlModule(0x18, 0, 0x1);
                global24 = ControlModule(0xa, 0);
            }
            else
            {
                printf("status_SquatWait_Main 2");
                func_16(0x28, 0x1);
                return 0x1;
            }
        }
    }
    if (func_47())
    {
        return 0x1;
    }
    if (func_49())
    {
        return 0x1;
    }
    if (func_51())
    {
        return 0x1;
    }
    if (func_52())
    {
        return 0x1;
    }
    return 0;
}

void func_618()
{
    WorkModule(0x16, 0x1e000037);
}

int func_619()
{
    if (WorkModule(0x15, 0x1e000037))
    {
        if (global31 & 0x400)
        {
            if (global18 == 0)
            {
                func_16(0x13, 0x1);
                return 0x1;
            }
        }
    }
    return 0;
}

void func_620()
{
    WorkModule(0x16, 0x1e000038);
}

int func_621()
{
    if (WorkModule(0x15, 0x1e000038))
    {
        if (global31 & 0x800)
        {
            if (global18 == 0)
            {
                func_16(0x14, 0x1);
                return 0x1;
            }
        }
    }
    return 0;
}

void func_622()
{
    int var0;
    if (StatusModule(0) == 0x11)
    {
        var0 = 0xffffffff;
        WorkModule(0x7, var0, 0x11000002);
    }
}

void func_623()
{
    int var0;
    float var1;
    int var2;
    if (StatusModule(0) == 0x11)
    {
        var0 = WorkModule(0x6, 0x11000002);
        if (var0 > 0)
        {
            WorkModule(0xa, 0x11000002);
        }
        if (var0 == 0xffffffff && global32 <= WorkModuleF(0, 0x2000066) && global47 < WorkModule(0x6, 0x12000067) && GroundModule(0xd) == 0x1)
        {
            var1 = WorkModuleF(0, 0x2000069);
            var2 = (int)(var1 + (float)WorkModule(0x6, 0x11000004));
            WorkModule(0x7, var2, 0x11000002);
        }
    }
    func_624();
}

void func_624()
{
    int var0;
    int var1;
    float var2;
    if (BattleObject(0x6e, 0x4c) == 0x1)
    {
        WorkModule(0x9, 0x11000003);
        var0 = WorkModule(0x6, 0x11000003);
        var1 = BattleObject(0x77, 0x4c);
        if (var0 >= WorkModule(0x6, 0x1900004b + var1 - 0x1))
        {
            WorkModule(0x7, 0, 0x11000003);
            var2 = WorkModuleF(0, 0x900004e + var1 - 0x1);
            BattleObject(0x1a, var2);
        }
    }
}

void func_625()
{
    
}

void func_626()
{
    float var0;
    float var1;
    float var2;
    float var3;
    int var4;
    float var5;
    int var6;
    float var7;
    float var8;
    var0 = func_629();
    var1 = KineticModuleF(0, 0x1);
    var2 = (float)0;
    var3 = PostureModuleF(0);
    if (var1 * var3 < (float)0)
    {
        var2 = 0;
    }
    else
    {
        var2 = var1 / var0;
    }
    WorkModule(0, var2, 0x1000006);
    var4 = func_630();
    var5 = MotionModuleF(0, var4);
    var6 = MotionModule(0, var4);
    if (func_13(var5) < 0.5f)
    {
        var5 = 20.0f;
    }
    var7 = var0 / (var5 / (float)var6);
    var8 = func_13(var7);
    WorkModule(0, var8, 0x1000007);
}

void func_627()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    float var7;
    float var8;
    float var9;
    float var10;
    float var11;
    var0 = WorkModuleF(0, 0x16);
    var1 = WorkModuleF(0, 0x1000006);
    var2 = func_631();
    var3 = WorkModuleF(0, 0x3000002);
    var4 = var3 / var0;
    var5 = WorkModuleF(0, 0x3000001);
    var6 = var5 / var0;
    var7 = var2 * var6;
    if (var2 > (float)0)
    {
        var7 += var4;
    }
    else
    {
        var7 -= var4;
    }
    var8 = var2;
    var9 = var1 / var8;
    if (var9 > (float)0 && var9 < 1.0f)
    {
        var9 = 1.0f - var9;
        var7 = var9 * WorkModuleF(0, 0x2000002) * var7;
    }
    var10 = WorkModuleF(0, 0x3000007);
    var11 = var10 / var0;
    if (var8 == (float)0)
    {
        if (func_13(var11) > func_13(var11))
        {
            var7 = -var1;
        }
        else if (var1 > (float)0)
        {
            var7 = -var11;
        }
        else
        {
            var7 = var11;
        }
    }
    else if (var7 > (float)0)
    {
        if (var1 + var7 > var8)
        {
            var7 = -var11;
            if (var1 + var7 < var8)
            {
                var7 = var8 - var1;
            }
        }
    }
    else if (var1 + var7 < var8)
    {
        var7 = var11;
        if (var1 + var7 > var8)
        {
            var7 = var8 - var1;
        }
    }
    WorkModule(0, var1 + var7, 0x1000006);
    func_632();
}

void func_628()
{
    
}

int func_629()
{
    if (StatusModule(0) == 0x13)
    {
        return WorkModuleF(0, 0x16);
    }
    else if (StatusModule(0) == 0x14)
    {
        return WorkModuleF(0, 0x17);
    }
    else
    {
        printf("ASSERT :: FL_get_max_speed() - MA_MSC_STATUS_GET_STATUS_KIND\n");
    }
    return 0;
}

int func_630()
{
    if (StatusModule(0) == 0x13)
    {
        return 0x37;
    }
    else if (StatusModule(0) == 0x14)
    {
        return 0x38;
    }
    else
    {
        printf("ASSERT :: get_motion_kind() - MA_MSC_STATUS_GET_STATUS_KIND\n");
    }
    return 0xffffffff;
}

float func_631()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    var0 = global48 * PostureModuleF(0);
    var1 = (float)0;
    var2 = (float)0;
    var3 = (float)0;
    if (StatusModule(0) == 0x13)
    {
        var1 = WorkModuleF(0, 0x200001b);
        var2 = WorkModuleF(0, 0x200001c);
        if (var0 < var1)
        {
            return 0.5f;
        }
        else if (var0 > var2)
        {
            return 1.0f;
        }
    }
    else if (StatusModule(0) == 0x14)
    {
        var1 = WorkModuleF(0, 0x200001d);
        var2 = WorkModuleF(0, 0x200001e);
        if (var0 > var1)
        {
            return 0.5f;
        }
        else if (var0 < var2)
        {
            return 1.0f;
        }
    }
    else
    {
        printf("ASSERT :: FL_get_stick_x_rate() - MA_MSC_STATUS_GET_STATUS_KIND\n");
    }
    var4 = var2 - var1;
    if (func_13(var4) > 0)
    {
        var3 = (var0 - var1) / var4;
        var3 = var3 * 0.5f + 0.5f;
    }
    else
    {
        var3 = 1.0f;
    }
    return var3;
}

void func_632()
{
    float var0;
    float var1;
    float var2;
    var0 = WorkModuleF(0, 0x1000006);
    var1 = WorkModuleF(0, 0x1000007);
    var2 = var0 * var1;
    var2 = func_13(var2);
    MotionModule(0x4, var2);
}

int func_633()
{
    StatusModule(0x5, 0, 0x33, 0x1, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x2, 0, 0);
    return 0;
}

int func_634()
{
    StatusModule(0x5, 0x2, 0x2d, 0x5, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0x1, 0, 0x2, 0, 0);
    return 0;
}

void func_635()
{
    func_78(func_636);
}

void func_636()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (global18 == 0)
    {
        if (MotionModule(0x2712) == 0x1)
        {
            func_16(0, 0);
            return;
        }
    }
}

void func_637()
{
    if (!StopModule(0x1))
    {
        func_642();
    }
    global16 = func_642;
    MotionModule(0x4, WorkModuleF(0, 0x20000ac));
    func_78(func_638);
}

void func_638()
{
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0xe, 0);
        return;
    }
    if (GroundModule(0x2722, 0x1) != 0x1)
    {
        if (WorkModule(0x10, 0x2100000d) == 0x1)
        {
            func_16(0xe, 0);
            return;
        }
    }
}

void func_639()
{
    
}

void func_640()
{
    
}

int func_641()
{
    float var0;
    float var1;
    var0 = (float)0xffffffff;
    var1 = (float)0x1;
    if (GroundModule(0x2722, 0x2))
    {
        if (PostureModuleF(0) == var0)
        {
            if (func_90() > WorkModuleF(0, 0x3000003))
            {
                if (global18 == 0)
                {
                    func_16(0x69, 0x1);
                    return 0x1;
                }
            }
        }
    }
    if (GroundModule(0x2722, 0x4))
    {
        if (PostureModuleF(0) == var1)
        {
            if (func_90() > WorkModuleF(0, 0x3000003))
            {
                if (global18 == 0)
                {
                    func_16(0x69, 0x1);
                    return 0x1;
                }
            }
        }
    }
    return 0;
}

void func_642()
{
    if (WorkModule(0x10, 0x2100000d) == 0x1)
    {
        if (MotionModule(0x7) != 0x24)
        {
            MotionModule(0x1, 0x24, 0, 1.0f);
            if (func_41())
            {
                return;
            }
        }
        func_550();
    }
}

int func_643()
{
    StatusModule(0x5, 0x2, 0x33, 0x5, 0x4, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0x2, 0, 0x10);
    return 0;
}

void func_644()
{
    int var0;
    int var1;
    float var2;
    float var3;
    func_75();
    func_76();
    ControlModule(0x271b);
    var0 = WorkModule(0x6, 0x120000b1);
    WorkModule(0x7, var0, 0x11000002);
    var1 = WorkModule(0x6, 0x120000b3);
    WorkModule(0x7, var1, 0x11000004);
    WorkModule(0x9, 0x10000004);
    var2 = WorkModuleF(0, 0x20000b8);
    var3 = WorkModuleF(0, 0x20000b9);
    if (!StopModule(0x1))
    {
        func_647();
    }
    global16 = func_647;
    func_78(func_645);
}

void func_645()
{
    if (MotionModule(0x2712) != 0)
    {
        func_16(0xe, 0);
        return;
    }
    if (func_41())
    {
        return;
    }
}

void func_646()
{
    
}

void func_647()
{
    if (WorkModule(0x6, 0x11000002) > 0)
    {
        WorkModule(0xa, 0x11000002);
        if (WorkModule(0x6, 0x11000002) == 0)
        {
            func_40();
            KineticModule(0, 0x29);
            MotionModule(0x4, 1.0f);
        }
    }
    else if (WorkModule(0x6, 0x11000004) > 0)
    {
        WorkModule(0xa, 0x11000004);
    }
}

int func_648()
{
    StatusModule(0x5, 0x2, 0x33, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x2, 0, 0);
    return 0;
}

void func_649()
{
    WorkModule(0x19, 0x1f00000b);
    WorkModule(0x19, 0x1f00000e);
    if (!StopModule(0x1))
    {
        func_651();
    }
    global16 = func_651;
    func_78(func_650);
}

void func_650()
{
    if (GroundModule(0x2728) == 0)
    {
        func_16(0xe, 0);
        return;
    }
    else if (GroundModule(0x2722, 0x1) != 0)
    {
        func_16(0xe, 0);
        return;
    }
    else if (GroundModule(0x2722, 0x6) == 0)
    {
        func_16(0xe, 0);
        return;
    }
    if (global18 == 0)
    {
        func_16(0, 0);
        return;
    }
    if (global24 & 0x200000)
    {
        func_16(0x6b, 0x1);
        return;
    }
    if (global32 >= WorkModuleF(0, 0x200001f) && WorkModule(0x10, 0x2100000f))
    {
        func_16(0x6b, 0x1);
        return;
    }
    if (func_88() >= WorkModuleF(0, 0x20000af))
    {
        func_16(0x6b, 0x1);
        return;
    }
    if (global32 <= WorkModuleF(0, 0x2000046))
    {
        func_16(0x6f, 0x1);
        return;
    }
    if (MotionModule(0x2712) != 0 || WorkModule(0x10, 0x2100000e) != 0)
    {
        func_16(0x6d, 0);
        return;
    }
    if (func_59())
    {
        return;
    }
    if (func_63())
    {
        return;
    }
    if (func_1724() == 0x1)
    {
        return;
    }
}

void func_651()
{
    if (global32 < WorkModuleF(0, 0x2000022))
    {
        WorkModule(0x11, 0x2100000f);
    }
}

void func_652()
{
    WorkModule(0x7, WorkModule(0x6, 0x120000bd), 0x1000000b);
}

int func_653()
{
    StatusModule(0x5, 0x2, 0x33, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x2, 0, 0);
    return 0;
}

void func_654()
{
    WorkModule(0x19, 0x1f00000b);
    WorkModule(0x19, 0x1f00000e);
    func_23(0xef);
    MotionModule(0x4, 0);
    if (!StopModule(0x1))
    {
        func_656();
    }
    global16 = func_656;
    func_78(func_655);
}

void func_655()
{
    if (GroundModule(0x2722, 0x8) != 0)
    {
        func_16(0, 0);
        return;
    }
    if (GroundModule(0x2728) == 0)
    {
        func_16(0xe, 0);
        return;
    }
    else if (GroundModule(0x2722, 0x1) != 0)
    {
        func_16(0xe, 0);
        return;
    }
    else if (GroundModule(0x2722, 0x6) == 0)
    {
        func_16(0xe, 0);
        return;
    }
    else if (WorkModule(0x6, 0x11000004) <= 0)
    {
        func_16(0xe, 0);
        return;
    }
    if (global24 & 0x200000)
    {
        func_16(0x70, 0x1);
        return;
    }
    if (global32 >= WorkModuleF(0, 0x200001f) && WorkModule(0x10, 0x2100000f))
    {
        func_16(0x70, 0x1);
        return;
    }
    if (func_88() >= WorkModuleF(0, 0x20000af))
    {
        func_16(0x6e, 0x1);
        return;
    }
    if (global32 <= WorkModuleF(0, 0x2000046))
    {
        func_16(0x6f, 0x1);
        return;
    }
    if (func_59())
    {
        return;
    }
    if (func_63())
    {
        return;
    }
    if (func_1724() == 0x1)
    {
        return;
    }
}

void func_656()
{
    if (WorkModule(0x6, 0x11000004) > 0)
    {
        WorkModule(0xa, 0x11000004);
    }
    if (global32 < WorkModuleF(0, 0x2000022))
    {
        WorkModule(0x11, 0x2100000f);
    }
}

void func_657()
{
    WorkModule(0x7, WorkModule(0x6, 0x120000bd), 0x1000000b);
}

int func_658()
{
    StatusModule(0x5, 0x2, 0x2a, 0x5, 0x4, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_659()
{
    func_40();
    func_23(0xef);
    MotionModule(0x4, 1.0f);
    func_78(func_660);
}

void func_660()
{
    if (func_56())
    {
        return;
    }
    if (func_41())
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return;
    }
}

void func_661()
{
    
}

int func_662()
{
    StatusModule(0x5, 0x2, 0x2c, 0x5, 0x3, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0, 0, 0);
    return 0;
}

void func_663()
{
    func_40();
    func_23(0xef);
    MotionModule(0x4, 1.0f);
    func_78(func_664);
}

void func_664()
{
    if (func_56())
    {
        return;
    }
    if (func_41())
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return;
    }
}

void func_665()
{
    
}

int func_666()
{
    StatusModule(0x5, 0x2, 0x2b, 0x5, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0, 0, 0);
    return 0;
}

void func_667()
{
    int var0;
    var0 = 0x1;
    func_496(0, var0);
    func_78(func_668);
}

void func_668()
{
    int var0;
    var0 = func_497();
    if (var0)
    {
        return;
    }
}

void func_669()
{
    
}

int func_670()
{
    int var0;
    if (WorkModule(0x10, 0x2000001b))
    {
        StatusModule(0x2711, 0x4e);
        return 0x1;
    }
    else if (WorkModule(0x10, 0x2000000b))
    {
        StatusModule(0x2711, 0xd3);
        return 0x1;
    }
    else
    {
        var0 = ItemModule(0x11);
        if (var0 == 0)
        {
            StatusModule(0x2711, 0xa6);
            return 0x1;
        }
        else if (var0 == 0x6c)
        {
            StatusModule(0x2711, 0x98);
            return 0x1;
        }
    }
    StatusModule(0x5, 0, 0xf, 0x3, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0, 0x1, 0, 0, 0, 0x1008010, 0, 0);
    return 0;
}

int func_671()
{
    StatusModule(0x5, 0, 0x32, 0x7, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0x1, 0, 0, 0, 0);
    return 0;
}

void func_672()
{
    func_684();
    func_682();
    func_78(func_673);
}

void func_673()
{
    if (WorkModule(0x10, 0x2000000b))
    {
        func_16(0xd3, 0);
        return 0x1;
    }
    if (func_685())
    {
        return;
    }
    if (func_681())
    {
        return;
    }
}

void func_674()
{
    func_40();
    WorkModule(0x16, 0x1e00005f);
    WorkModule(0x16, 0x1e000065);
    WorkModule(0x16, 0x1e000076);
    WorkModule(0x16, 0x1e000074);
    func_22(0xfb, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_550();
    }
    global16 = func_550;
    func_78(func_675);
}

void func_675()
{
    if (WorkModule(0x6, 0x11000002) == 0)
    {
        if (!WorkModule(0x10, 0x2100000d))
        {
            WorkModule(0x2710, 0x2100000d);
            KineticModule(0, 0x13);
            func_676();
        }
        if (func_41())
        {
            return;
        }
        if (MotionModule(0x2712))
        {
            func_16(0xe, 0);
            return;
        }
    }
    else if (WorkModule(0x6, 0x11000002) > 0)
    {
        func_71(global35);
        if (func_72(global27))
        {
            if (WorkModule(0x15, 0x1e000065))
            {
                if (global24 & 0x8000)
                {
                    if (edge_lw_can_counter())     // Sephiroth: not while the Phantom charges (test 105)
                    {
                        func_16(0x155, 0x1);
                        return 0x1;
                    }
                }
            }
        }
        if ((global24 & 0x20000000) != 0 && WorkModule(0x15, 0x1e000076) == 0x1 && ItemModule(0x4) == 0x1 && ItemModule(0x5, 0x800000) == 0)
        {
            func_16(0x8c, 0);
            return 0x1;
        }
        if ((global24 & 0x1) != 0 && WorkModule(0x15, 0x1e000074) == 0x1)
        {
            if (ItemModule(0x5, 0x8) == 0x1 || ItemModule(0x5, 0x2) == 0x1 && ItemModule(0x1a) <= 0)
            {
                func_16(0x8c, 0);
                return 0x1;
            }
        }
        if (global32 <= WorkModuleF(0, 0x200003c) && ControlModule(0x2710, 0))
        {
            if (WorkModule(0x15, 0x1e00005f))
            {
                func_16(0x2e, 0x1);
                return 0x1;
            }
        }
    }
}

void func_676()
{
    func_76();
    GroundModule(0x2715);
    func_94();
    KineticModule(0x2710, 0, WorkModuleF(0, 0x2000068));
}

void func_677()
{
    float var0;
    int var1;
    var0 = WorkModuleF(0, 0x20000a1);
    var1 = (int)var0;
    WorkModule(0x7, var1, 0x11000002);
}

void func_678()
{
    int var0;
    var0 = WorkModule(0x6, 0x11000002);
    if (var0 > 0)
    {
        WorkModule(0xa, 0x11000002);
    }
}

void func_679()
{
    
}

void func_680()
{
    
}

void func_681()
{
    int var0;
    int var1;
    int var2;
    int var3;
    var0 = StatusModule(0x6);
    var1 = 0;
    if (!var0)
    {
        var2 = MotionModule(0x7);
        if (var2 == 0x19a)
        {
            if (MotionModule(0x2712) || WorkModule(0x10, 0x2000000a) == 0)
            {
                var1 = 0x1;
            }
        }
        else if (var2 == 0x5)
        {
            if (ItemModule(0x19) != 0x5)
            {
                var1 = 0x1;
            }
        }
        else if (MotionModule(0x2712))
        {
            var1 = 0x1;
        }
        else if (ItemModule(0x4, 0) && ItemModule(0x11) == 0x51)
        {
            var3 = ItemModule(0x19);
            if (var3 != 0xffffffff && var3 != var2)
            {
                var1 = 0x1;
            }
        }
    }
    if (var1)
    {
        func_682();
    }
}

void func_682()
{
    int var0;
    if (func_683() == 0)
    {
        var0 = FighterUtil(0xd, 0);
        if (var0 == 0x1)
        {
            func_22(0x1, 0, 1.0f);
        }
        else if (var0 == 0x2)
        {
            func_22(0x2, 0, 1.0f);
        }
        else if (var0 == 0x3)
        {
            func_22(0x3, 0, 1.0f);
        }
        else if (var0 == 0x4)
        {
            func_22(0x4, 0, 1.0f);
        }
        else if (var0 == 0xffffffff)
        {
            MotionModule(0x2711, 0);
        }
        else
        {
            func_22(0, 0, 1.0f);
        }
    }
}

int func_683()
{
    if (WorkModule(0x10, 0x2000000a))
    {
        if (MotionModule(0x7) == 0x19a)
        {
            MotionModule(0x2711, 0);
        }
        else
        {
            func_22(0x19a, 0, 1.0f);
        }
        return 0x1;
    }
    else if (ItemModule(0x4, 0))
    {
        if (ItemModule(0x19) == 0x5)
        {
            func_22(0x5, 0, 1.0f);
        }
        else if (MotionModule(0x7) == 0)
        {
            MotionModule(0x2711, 0);
        }
        else
        {
            func_22(0, 0, 1.0f);
        }
        return 0x1;
    }
    return 0;
}

void func_684()
{
    BattleObject(0x9);
    BattleObject(0xa, 0x1, WorkModule(0x6, 0x12000095));
    BattleObject(0xc, 0x1);
    func_38();
}

int func_685()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (func_39())
    {
        return 0x1;
    }
    if (func_694())
    {
        return 0x1;
    }
    return 0;
}

int func_686()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0, 0, 0x4000000);
    return 0;
}

void func_687()
{
    ControlModule(0x271b);
    if (sys_1F(0x1))
    {
        if (!WorkModule(0x10, 0x2000005e))
        {
            if (ControlModule(0x2712, 0x6))
            {
                callFunc3(func_688);
                return;
            }
        }
    }
    BattleObject(0x81);
    callFunc3(func_689);
}

void func_688()
{
    if (global9 < 2.0f)
    {
        return;
    }
    if (!ControlModule(0x2712, 0x6))
    {
        if (sys_1F(0x2))
        {
            WorkModule(0x2710, 0x2100000d);
            BattleObject(0x2b, 0x1);
            func_16(0x14e);
            return;
        }
        else
        {
            WorkModule(0x7, 0x1ab, 0x11000002);
            WorkModule(0x7, 0x1ac, 0x11000003);
        }
    }
    callFunc3(func_689);
}

void func_689()
{
    int var0;
    if (!WorkModule(0x10, 0x2100000d))
    {
        if (WorkModule(0x10, 0x2000005e))
        {
            var0 = randi(0, 0x3);
            if (var0 == 0)
            {
                WorkModule(0x7, 0x1a7, 0x11000002);
                WorkModule(0x7, 0x1a8, 0x11000003);
                BattleObject(0x2a, 0);
            }
            else if (var0 == 0x1)
            {
                WorkModule(0x7, 0x1ab, 0x11000002);
                WorkModule(0x7, 0x1ac, 0x11000003);
                BattleObject(0x2a, 0x1);
            }
            else if (var0 == 0x2)
            {
                WorkModule(0x7, 0x1a9, 0x11000002);
                WorkModule(0x7, 0x1aa, 0x11000003);
                var0 = randi(0, 0x2);
                if (var0 == 0x1)
                {
                    BattleObject(0x2a, 0x2);
                }
                else
                {
                    BattleObject(0x2a, 0x3);
                }
            }
        }
        else if (global31 & 0x2)
        {
            WorkModule(0x7, 0x1a7, 0x11000002);
            WorkModule(0x7, 0x1a8, 0x11000003);
            BattleObject(0x2a, 0);
        }
        else if (global31 & 0x4)
        {
            WorkModule(0x7, 0x1ab, 0x11000002);
            WorkModule(0x7, 0x1ac, 0x11000003);
            BattleObject(0x2a, 0x1);
        }
        else if (global31 & 0x1)
        {
            WorkModule(0x7, 0x1a9, 0x11000002);
            WorkModule(0x7, 0x1aa, 0x11000003);
            if (ControlModule(0x1e) == 0x1)
            {
                BattleObject(0x2a, 0x2);
            }
            else
            {
                BattleObject(0x2a, 0x3);
            }
        }
        if (MotionModule(0xc, WorkModule(0x6, 0x11000003)) == 0x1)
        {
            if (PostureModuleF(0) == -1.0f)
            {
                func_22(WorkModule(0x6, 0x11000003), 0, 1.0f);
            }
            else
            {
                func_22(WorkModule(0x6, 0x11000002), 0, 1.0f);
            }
        }
        else
        {
            func_22(WorkModule(0x6, 0x11000002), 0, 1.0f);
        }
    }
    callFunc3(func_690);
}

void func_690()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe);
        return;
    }
    if (!WorkModule(0x10, 0x2100000d))
    {
        if (MotionModule(0x2712))
        {
            func_16(0);
            return;
        }
    }
}

void func_691()
{
    
}

int func_692()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_693()
{
    
}

int func_694()
{
    float var0;
    var0 = 0.75f;
    if (GroundModule(0x2726, 0.8600000143051147f) == 0x1)
    {
        if (func_84() < var0)
        {
            if (!WorkModule(0x10, 0x20000028))
            {
                func_16(0x7b, 0x1);
                return 0x1;
            }
        }
    }
    return 0;
}

int func_695()
{
    float var0;
    var0 = 0.75f;
    if (GroundModule(0x2726, 0.8600000143051147f) == 0x1)
    {
        if (MotionModule(0x2712))
        {
            if (func_84() < var0)
            {
                if (!WorkModule(0x10, 0x20000028))
                {
                    func_16(0x7b, 0x1);
                    return 0x1;
                }
            }
        }
    }
    return 0;
}

void func_696()
{
    float var0;
    var0 = MotionModuleF(0x1);
    if (var0 > (float)0x2)
    {
        WorkModule(0x2711, 0x2100000a);
    }
}

int func_697()
{
    return func_698(0, 0, 0);
}

int func_698(int arg0, int arg1, int arg2)
{
    if (WorkModule(0x10, 0x2000000a))
    {
        StatusModule(0x2711, 0x4);
        return 0x1;
    }
    StatusModule(0x5, 0, 0xe, 0x3, 0, 0x1, arg0, arg1, arg2, 0);
    StatusModule(0x2713, 0x1, 0, 0x1, 0, 0, 0, 0x1000010, 0, 0x8000000);
    return 0;
}

int func_699()
{
    StatusModule(0x5, 0, 0xf, 0x3, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0x1000010, 0, 0);
    return 0;
}

int func_700()
{
    StatusModule(0x5, 0, 0x1b, 0x3, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0, 0x1, 0, 0, 0, 0x1000010, 0, 0x10000000);
    return 0;
}

int func_701()
{
    StatusModule(0x5, 0, 0x32, 0x3, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0x1000010, 0, 0x10000000);
    return 0;
}

int func_702()
{
    StatusModule(0x5, 0, 0x7, 0x3, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0x1000010, 0, 0);
    return 0;
}

void func_703()
{
    WorkModule(0x19, 0x1f000000);
    WorkModule(0x19, 0x1f000001);
    WorkModule(0x19, 0x1f000002);
    WorkModule(0x19, 0x1f000003);
    WorkModule(0x19, 0x1f000004);
    WorkModule(0x19, 0x1f000005);
    WorkModule(0x19, 0x1f000006);
    WorkModule(0x19, 0x1f000007);
    WorkModule(0x1b, 0x1e000031);
    WorkModule(0x1b, 0x1e00002f);
    WorkModule(0x1b, 0x1e00002d);
    WorkModule(0x1b, 0x1e00003c);
    WorkModule(0x1b, 0x1e000027);
    WorkModule(0x1b, 0x1e000028);
    WorkModule(0x2710, 0x2100000a);
    func_22(0x10, 0, 1.0f);
}

void func_704()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (global18 == 0 && MotionModule(0x2712))
    {
        func_16(0, 0);
        return 0x1;
    }
    func_696();
    if (func_43())
    {
        return 0x1;
    }
    if (func_44())
    {
        return 0x1;
    }
    if (func_46())
    {
        return 0x1;
    }
    if (func_47())
    {
        return 0x1;
    }
    if (global18 == 0)
    {
        if (WorkModule(0x10, 0x21000010) == 0)
        {
            if (global31 & 0x1000)
            {
                func_16(0x20, 0x1);
                return 0x1;
            }
            if (global31 & 0x2000)
            {
                func_16(0x21, 0x1);
                return 0x1;
            }
        }
    }
    if (func_48())
    {
        return 0x1;
    }
    if (func_49())
    {
        return 0x1;
    }
    if (func_51())
    {
        return 0x1;
    }
    if (func_52())
    {
        return 0x1;
    }
}

int func_705()
{
    StatusModule(0x5, 0, 0x35, 0x3, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0x1000010, 0, 0);
    return 0;
}

int func_706()
{
    StatusModule(0x5, 0, 0x32, 0x3, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0x1000010, 0, 0x10000000);
    return 0;
}

int func_707()
{
    StatusModule(0x5, 0, 0x1f, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0x1000010, 0, 0x10000000);
    return 0;
}

int func_708()
{
    StatusModule(0x5, 0, 0x7, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0x1000010, 0, 0);
    return 0;
}

void func_709()
{
    WorkModule(0x2710, 0x2100000d);
    WorkModule(0x19, 0x1f000000);
    WorkModule(0x19, 0x1f000001);
    WorkModule(0x19, 0x1f000002);
    WorkModule(0x19, 0x1f000003);
    WorkModule(0x19, 0x1f000004);
    WorkModule(0x19, 0x1f000005);
    WorkModule(0x19, 0x1f000006);
    WorkModule(0x19, 0x1f000007);
    WorkModule(0x1b, 0x1e00002f);
    WorkModule(0x1b, 0x1e00003c);
    WorkModule(0x17, 0x1e00000b);
    if (!StopModule(0x1))
    {
        func_742();
    }
    global16 = func_742;
    func_78(func_710);
}

void func_710()
{
    if (WorkModule(0x10, 0x2000000b))
    {
        func_16(0xd4, 0);
        return 0x1;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (func_694())
    {
        return;
    }
    if (func_43())
    {
        return;
    }
    if (func_44())
    {
        return;
    }
    if (func_46())
    {
        return;
    }
    if (func_47())
    {
        return;
    }
    if (func_48())
    {
        return;
    }
    if (func_49())
    {
        return;
    }
    if (func_51())
    {
        return;
    }
    if (func_52())
    {
        return;
    }
    if (func_84() < WorkModuleF(0, 0x2000001))
    {
        if (GroundModuleF(0) < 1.0f)
        {
            if (global18 == 0)
            {
                func_16(0x2);
                return;
            }
        }
    }
    if (func_88() < 0)
    {
        if (GroundModuleF(0) < 1.0f)
        {
            if (global18 == 0)
            {
                func_16(0x2);
                return;
            }
        }
    }
    if (func_84() < WorkModuleF(0, 0x2000001))
    {
        if (global18 == 0)
        {
            func_16(0, 0x1);
            return;
        }
    }
    if (func_88() < (float)0)
    {
        if (global18 == 0)
        {
            func_16(0, 0x1);
            return;
        }
    }
}

void func_711()
{
    int var0;
    int var1;
    float var2;
    float var3;
    float var4;
    func_684();
    var0 = 0xd;
    var1 = MotionModule(0x7);
    if (MotionModule(0xc, 0xf) == 0x1)
    {
        var2 = MotionModuleF(0x1);
        var0 = 0xe;
        if (var1 == 0xa)
        {
            var3 = WorkModuleF(0, 0x300010e);
            var4 = WorkModuleF(0, 0x300010f);
        }
        else if (var1 == 0xb)
        {
            var3 = WorkModuleF(0, 0x3000110);
            var4 = WorkModuleF(0, 0x3000111);
        }
        else
        {
            var3 = WorkModuleF(0, 0x3000112);
            var4 = WorkModuleF(0, 0x3000113);
        }
        if (var3 > var4)
        {
            if (var2 < var4 || var2 >= var3)
            {
                var0 = 0xf;
            }
        }
        else if (var2 >= var3 && var2 < var4)
        {
            var0 = 0xf;
        }
    }
    func_22(var0, 0, 0);
    func_78(func_712);
}

void func_712()
{
    if (func_685())
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0, 0);
        return;
    }
}

void func_713()
{
    func_22(0x11, 0, 1.0f);
    WorkModule(0x19, 0x1f000006);
    WorkModule(0x16, 0x1e000063);
    WorkModule(0x16, 0x1e000074);
    WorkModule(0x16, 0x1e000078);
    WorkModule(0x16, 0x1e000076);
    WorkModule(0x16, 0x1e000077);
    WorkModule(0x16, 0x1e00006f);
    WorkModule(0x16, 0x1e00006e);
    WorkModule(0x16, 0x1e00007b);
    WorkModule(0x16, 0x1e000082);
    WorkModule(0x16, 0x1e00005c);
    WorkModule(0x16, 0x1e000059);
    WorkModule(0x16, 0x1e00000b);
    WorkModule(0x16, 0x1e00007f);
    WorkModule(0x16, 0x1e000072);
    WorkModule(0x16, 0x1e000073);
    WorkModule(0x16, 0x1e000054);
    WorkModule(0x16, 0x1e000031);
    WorkModule(0x16, 0x1e000066);
    WorkModule(0x16, 0x1e000067);
    WorkModule(0x16, 0x1e000068);
    WorkModule(0x16, 0x1e000069);
    WorkModule(0x7, WorkModule(0x6, 0x1200000b), 0x11000003);
    func_75();
    if (!StopModule(0x1))
    {
        func_714();
    }
    global16 = func_714;
    func_78(func_715);
}

void func_714()
{
    if (WorkModule(0x6, 0x11000003) >= 0)
    {
        WorkModule(0xa, 0x11000003);
        if (WorkModule(0x6, 0x11000003) < 0)
        {
            WorkModule(0x17, 0x1e000031);
            WorkModule(0x16, 0x1e000030);
        }
    }
}

void func_715()
{
    float var0;
    if (func_71(global59))
    {
        return 0x1;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (run_attack_update()) // tilts / down smash out of the dash (universal mechanics)
    {
        return 0x1;
    }
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (func_60())
    {
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000063))
    {
        if (global24 & 0x2000)
        {
            if (func_72(global25))
            {
                func_16(0x153, 0x1);
                return;
            }
        }
    }
    if (global24 & 0x20 && WorkModule(0x15, 0x1e000074) == 0x1)
    {
        if (ItemModule(0x5, 0x8) == 0x1 || ItemModule(0x5, 0x2) == 0x1 && ItemModule(0x1a) <= 0)
        {
            func_16(0x8c, 0);
            return;
        }
    }
    if (WorkModule(0x15, 0x1e000074) == 0x1 && ItemModule(0x5, 0x8) == 0x1 && (global38 & 0x1) != 0 && WorkModule(0x2712, 0x2100000d) == 0)
    {
        func_16(0x8c, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e000078) == 0x1 && ItemModule(0x5, 0x8) == 0x1 && (global38 & 0x1) != 0)
    {
        func_16(0x8d, 0x1);
        return;
    }
    if (WorkModule(0x15, 0x1e000076) == 0x1 && ItemModule(0x4) == 0x1 && (global24 & 0x20000000) != 0 && WorkModule(0x2712, 0x2100000d) == 0 && ItemModule(0x5, 0x800000) == 0)
    {
        func_16(0x8c, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e000077) == 0x1 && ItemModule(0x4) == 0x1 && (global24 & 0x20000000) != 0 && ItemModule(0x5, 0x800000) == 0)
    {
        func_16(0x8d, 0x1);
        return;
    }
    if (WorkModule(0x15, 0x1e00006f) == 0x1 && func_88() <= WorkModuleF(0, 0x2000014) && (global24 & 0x20000000) != 0 && ItemModule(0x4) == 0)
    {
        func_16(0x39, 0x1);
        return;
    }
    if (WorkModule(0x15, 0x1e00006e) == 0x1 && (global24 & 0x20000000) != 0 && ItemModule(0x4) == 0)
    {
        func_16(0x37, 0x1);
        return;
    }
    if (WorkModule(0x15, 0x1e00007b) == 0x1 && ItemModule(0x5, 0x4) == 0x1 && (global31 & 0x20) != 0 && WorkModule(0x2712, 0x2100000d) == 0)
    {
        func_16(0x94, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000082) == 0x1 && ItemModule(0x5, 0x2) == 0x1 && (global38 & 0x1) != 0 && WorkModule(0x2712, 0x2100000d) == 0)
    {
        if (ItemModule(0x1a) <= 0)
        {
            func_16(0x8c, 0);
        }
        else
        {
            func_16(0x98, 0x1);
        }
        return;
    }
    if (WorkModule(0x15, 0x1e000059) == 0x1 && global31 & 0x20 && WorkModule(0x2712, 0x2100000d) == 0)
    {
        func_16(0x2b, 0x1);
        return;
    }
    if (WorkModule(0x15, 0x1e00007f) == 0x1 && ItemModule(0x5, 0x4) == 0x1 && (global38 & 0x1) != 0)
    {
        func_16(0x97, 0x1);
        return;
    }
    if (global24 & 0x20)
    {
        if (WorkModule(0x15, 0x1e00005c))
        {
            func_16(0x31, 0x1);
            return;
        }
    }
    if (WorkModule(0x15, 0x1e000054))
    {
        if (global38 & 0x1)
        {
            func_16(0x27, 0x1);
            return;
        }
    }
    if (WorkModule(0x15, 0x1e000072) == 0x1 && ItemModule(0) && ItemModule(0x22))
    {
        if ((global38 & 0x1) != 0)
        {
            func_16(0x8a, 0x1);
            return;
        }
        else if (BattleObject(0x86, 0x1))
        {
            func_16(0x8a, 0);
            return;
        }
    }
    if (WorkModule(0x15, 0x1e000073) == 0x1 && ItemModule(0x1) && ItemModule(0x4) == 0)
    {
        if ((global38 & 0x1) != 0)
        {
            func_16(0x8b, 0x1);
            return;
        }
        else if (BattleObject(0x86, 0x1))
        {
            func_16(0x8b, 0);
            return;
        }
    }
    var0 = MotionModuleF(0x1);
    if (WorkModule(0x15, 0x1e000031) == 0x1 && global24 & 0x80000)
    {
        func_16(0x7, 0x1);
        return;
    }
    if (WorkModule(0x15, 0x1e000030) == 0x1 && global24 & 0x80000)
    {
        func_16(0x8, 0x1);
        return;
    }
    if (global24 & 0x20000 && var0 >= (float)WorkModule(0x6, 0x1200000c))
    {
        func_16(0x3, 0x1);
        return;
    }
    if (ControlModule(0x2712, 0x3) == 0x1 && WorkModule(0x2712, 0x2100000e) == 0)
    {
        func_16(0x20, 0x1);
        return;
    }
    if (func_51())
    {
        return;
    }
    if (WorkModule(0x15, 0x1e00000a) == 0x1 && func_88() >= WorkModuleF(0, 0x200000e))
    {
        func_16(0x4, 0x1);
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        if (GroundModuleF(0) < 1.0f)
        {
            func_16(0x5, 0);
        }
        else
        {
            func_16(0, 0);
        }
        return;
    }
    if (func_641())
    {
        return;
    }
}

void func_716()
{
    func_22(0x12, 0, 1.0f);
    WorkModule(0x19, 0x1f000000);
    WorkModule(0x19, 0x1f000005);
    WorkModule(0x19, 0x1f000006);
    WorkModule(0x16, 0x1e000078);
    WorkModule(0x16, 0x1e000077);
    WorkModule(0x16, 0x1e000074);
    WorkModule(0x16, 0x1e00006f);
    WorkModule(0x16, 0x1e00006e);
    WorkModule(0x16, 0x1e00007f);
    WorkModule(0x16, 0x1e00005c);
    WorkModule(0x16, 0x1e000054);
    WorkModule(0x16, 0x1e000056); // up tilt out of run (universal mechanics)
    WorkModule(0x16, 0x1e000057); // down tilt out of run (universal mechanics)
    WorkModule(0x16, 0x1e00005f); // down smash out of run (universal mechanics)
    WorkModule(0x16, 0x1e000030);
    if (WorkModule(0x10, 0x2000000a))
    {
        WorkModule(0x16, 0x1e000092);
    }
    func_78(func_717);
}

void func_717()
{
    if (func_71(global60))
    {
        return 0x1;
    }
    if (WorkModule(0x10, 0x2000000b))
    {
        func_16(0xd4, 0);
        return 0x1;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (run_attack_update()) // tilts / down smash out of run (universal mechanics)
    {
        return 0x1;
    }
    if (func_43())
    {
        return;
    }
    if (global24 & 0x20 && WorkModule(0x15, 0x1e000074) == 0x1)
    {
        if (ItemModule(0x5, 0x8) == 0x1 || ItemModule(0x5, 0x2) == 0x1 && ItemModule(0x1a) <= 0)
        {
            func_16(0x8c, 0);
            return;
        }
    }
    if (WorkModule(0x15, 0x1e000078) == 0x1 && ItemModule(0x5, 0x8) == 0x1 && (global38 & 0x1) != 0)
    {
        func_16(0x8d, 0x1);
        return;
    }
    if (WorkModule(0x15, 0x1e000077) == 0x1 && ItemModule(0x4) == 0x1 && (global24 & 0x20000000) != 0 && ItemModule(0x5, 0x800000) == 0)
    {
        func_16(0x8d, 0x1);
        return;
    }
    if (WorkModule(0x15, 0x1e00006f) == 0x1 && WorkModuleF(0, 0x1000006) <= 0 && func_88() <= WorkModuleF(0, 0x2000014) && (global24 & 0x20000000) != 0 && ItemModule(0x4) == 0)
    {
        func_16(0x39, 0x1);
        return;
    }
    if (WorkModule(0x15, 0x1e00006e) == 0x1 && (global24 & 0x20000000) != 0 && ItemModule(0x4) == 0)
    {
        func_16(0x37, 0x1);
        return;
    }
    if (WorkModule(0x15, 0x1e00007f) == 0x1 && ItemModule(0x5, 0x4) == 0x1 && (global38 & 0x1) != 0)
    {
        func_16(0x97, 0x1);
        return;
    }
    if (global24 & 0x20)
    {
        if (WorkModule(0x15, 0x1e00005c))
        {
            func_16(0x31, 0x1);
            return;
        }
    }
    if (WorkModule(0x15, 0x1e000054))
    {
        if (global38 & 0x1)
        {
            func_16(0x27, 0x1);
            return;
        }
    }
    if (func_49())
    {
        return;
    }
    if (func_51())
    {
        return;
    }
    if (WorkModule(0x15, 0x1e000030) == 0x1)
    {
        if (WorkModuleF(0, 0x1000006) <= 0 && func_88() <= WorkModuleF(0, 0x2000014))
        {
            func_16(0x8, 0x1);
            return;
        }
    }
    if (WorkModule(0x10, 0x2000000a))
    {
        if (WorkModule(0x15, 0x1e000092) == 0x1)
        {
            if (func_84() < WorkModuleF(0, 0x2000001))
            {
                func_16(0x5, 0x1);
                return;
            }
        }
    }
    else if (func_84() < WorkModuleF(0, 0x200000e))
    {
        func_16(0x5, 0x1);
        return;
    }
    if (func_641())
    {
        return;
    }
}

int func_718(float arg0, float arg1, float arg2)
{
    if (arg0 > arg1)
    {
        if (arg2 < arg1 || arg2 >= arg0)
        {
            return 0x1;
        }
    }
    else if (arg2 >= arg0 && arg2 < arg1)
    {
        return 0x1;
    }
    return 0;
}

void func_719()
{
    int var0;
    float var1;
    float var2;
    float var3;
    var0 = 0x13;
    if (MotionModule(0xc, 0x15) == 0x1)
    {
        var1 = MotionModuleF(0x1);
        var0 = 0x14;
        var2 = WorkModuleF(0, 0x3000114);
        var3 = WorkModuleF(0, 0x3000115);
        if (func_718(var2, var3, var1) == 0x1)
        {
            var0 = 0x15;
        }
        else
        {
            var2 = WorkModuleF(0, 0x3000116);
            var3 = WorkModuleF(0, 0x3000117);
            if ((var2 != 0 || var3 != 0) && func_718(var2, var3, var1) == 0x1)
            {
                var0 = 0x15;
            }
        }
    }
    func_22(var0, 0, 1.0f);
    WorkModule(0x19, 0x1f000000);
    WorkModule(0x19, 0x1f000006);
    WorkModule(0x16, 0x1e000072);
    WorkModule(0x16, 0x1e000073);
    WorkModule(0x16, 0x1e000078);
    WorkModule(0x16, 0x1e00007f);
    WorkModule(0x16, 0x1e00005c);
    WorkModule(0x16, 0x1e000054);
    if (!StopModule(0x1))
    {
        func_721();
    }
    global16 = func_721;
}

void func_720()
{
    func_719();
    func_78(func_722);
}

void func_721()
{
    int var0;
    if (WorkModule(0x2712, 0x21000010) == 0)
    {
        var0 = MotionModuleF(0x1) >= BattleObjectF(0x63);
        if (WorkModule(0x6, 0x11000002) > WorkModule(0x6, 0x12000012) || var0)
        {
            if (var0 == 0)
            {
                WorkModule(0x17, 0x1e000063);
                WorkModule(0x17, 0x1e000064);
                WorkModule(0x17, 0x1e000065);
                WorkModule(0x17, 0x1e000094);
                WorkModule(0x17, 0x1e000062);
                WorkModule(0x17, 0x1e000076);
                WorkModule(0x17, 0x1e000074);
            }
            WorkModule(0x17, 0x1e000078);
            WorkModule(0x17, 0x1e00007f);
            WorkModule(0x17, 0x1e000054);
            WorkModule(0x2710, 0x21000010);
        }
    }
    WorkModule(0x9, 0x11000002);
}

void func_722()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (run_attack_update()) // tilts / down smash out of run (RunBrake) (universal mechanics)
    {
        return;
    }
    if (func_43())
    {
        return;
    }
    if (func_49())
    {
        return;
    }
    if (WorkModule(0x15, 0x1e000072) == 0x1 && ItemModule(0) && ItemModule(0x22) && global18 == 0)
    {
        if ((global38 & 0x1) != 0)
        {
            func_16(0x8a, 0x1);
            return;
        }
        else if (BattleObject(0x86, 0x1))
        {
            func_16(0x8a, 0);
            return;
        }
    }
    if (WorkModule(0x15, 0x1e000073) == 0x1 && ItemModule(0x1) && ItemModule(0x4) == 0 && global18 == 0)
    {
        if ((global38 & 0x1) != 0)
        {
            func_16(0x8b, 0x1);
            return;
        }
        else if (BattleObject(0x86, 0x1))
        {
            func_16(0x8b, 0);
            return;
        }
    }
    if (global24 & 0x20)
    {
        if (ItemModule(0x5, 0x8) == 0x1 || ItemModule(0x5, 0x2) == 0x1 && ItemModule(0x1a) <= 0)
        {
            func_16(0x8c, 0);
            return;
        }
    }
    func_45();
    if (WorkModule(0x15, 0x1e00007f) == 0x1 && ItemModule(0x5, 0x4) == 0x1 && (global38 & 0x1) != 0 && global18 == 0)
    {
        func_16(0x97, 0x1);
        return;
    }
    if (WorkModule(0x15, 0x1e000078) == 0x1 && ItemModule(0x5, 0x8) == 0x1 && (global38 & 0x1) != 0 && global18 == 0)
    {
        func_16(0x8d, 0x1);
        return;
    }
    if (global24 & 0x20)
    {
        if (WorkModule(0x15, 0x1e00005c))
        {
            func_16(0x31, 0x1);
            return;
        }
    }
    if (WorkModule(0x15, 0x1e000054) == 0x1 && global38 & 0x1)
    {
        func_16(0x27, 0x1);
        return;
    }
    if (func_51())
    {
        return;
    }
    if (WorkModule(0x2712, 0x2100000f) == 0x1 && func_88() <= WorkModuleF(0, 0x2000014))
    {
        func_16(0x8, 0x1);
        return;
    }
    if (func_695())
    {
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0, 0);
        return;
    }
}

void func_723()
{
    func_703();
    func_78(func_724);
}

void func_724()
{
    float var0;
    if (func_71(global61))
    {
        return 0x1;
    }
    if (dash_turn_attack_update()) // tilts / down smash turning out of a dash (universal mechanics)
    {
        return 0x1;
    }
    if (func_704())
    {
        return 0x1;
    }
    if (global18 == 0)
    {
        if (WorkModule(0x10, 0x2100000e))
        {
            if (WorkModule(0x10, 0x2100000d))
            {
                var0 = WorkModuleF(0, 0x2000007);
                if (global48 * -WorkModuleF(0, 0x1000006) >= var0)
                {
                    func_16(0x3, 0x1);
                    return 0x1;
                }
            }
        }
    }
}

void func_725()
{
    func_703();
    WorkModule(0x16, 0x1e000032);
    func_78(func_726);
}

void func_726()
{
    float var0;
    if (func_71(global61))
    {
        return 0x1;
    }
    if (dash_turn_attack_update()) // tilts / down smash turning out of a dash (universal mechanics)
    {
        return 0x1;
    }
    if (func_704())
    {
        return 0x1;
    }
    if (global18 == 0)
    {
        if (WorkModule(0x15, 0x1e000032))
        {
            if (WorkModule(0x10, 0x2100000e))
            {
                if (WorkModule(0x10, 0x2100000d))
                {
                    var0 = WorkModuleF(0, 0x2000007);
                    if (global48 * -WorkModuleF(0, 0x1000006) >= var0)
                    {
                        func_16(0x3, 0x1);
                        return 0x1;
                    }
                }
            }
        }
    }
}

void func_727()
{
    func_728();
    func_78(func_730);
}

void func_728()
{
    int var0;
    func_22(0x16, 0, 1.0f);
    var0 = WorkModule(0x6, 0x13000050);
    WorkModule(0x7, var0, 0x11000002);
    WorkModule(0x16, 0x1e00006f);
    WorkModule(0x7, 0, 0x10000056);
    WorkModule(0x7, WorkModule(0x6, 0x120000e2), 0x11000003);
    WorkModule(0x16, 0x1e000063);
    WorkModule(0x16, 0x1e000055);
    WorkModule(0x16, 0x1e000059);
    WorkModule(0x16, 0x1e00007d);
    WorkModule(0x16, 0x1e00007b);
    WorkModule(0x16, 0x1e000028);
    WorkModule(0x16, 0x1e000074);
    WorkModule(0x16, 0x1e000084);
    WorkModule(0x16, 0x1e000088);
    WorkModule(0x16, 0x1e00007b);
    WorkModule(0x16, 0x1e000066);
    WorkModule(0x16, 0x1e000067);
    WorkModule(0x16, 0x1e000068);
    WorkModule(0x16, 0x1e000069);
    WorkModule(0x2710, 0x2100000a);
    WorkModule(0x19, 0x1f000006);
    if (!StopModule(0x1))
    {
        func_729();
    }
    global16 = func_729;
}

void func_729()
{
    if (WorkModule(0x6, 0x11000002) >= 0)
    {
        WorkModule(0xa, 0x11000002);
        if (WorkModule(0x6, 0x11000002) < 0)
        {
            PostureModule(0x1);
        }
    }
    if (WorkModule(0x6, 0x11000003) >= 0)
    {
        WorkModule(0xa, 0x11000003);
        if (WorkModule(0x6, 0x11000003) < 0)
        {
            WorkModule(0x17, 0x1e00006f);
        }
    }
    WorkModule(0x9, 0x10000056);
    func_696();
}

void func_730()
{
    float var0;
    float var1;
    float var2;
    int var3;
    int var4;
    int var5;
    int var6;
    int var7;
    float var8;
    float var9;
    if (func_71(global59))
    {
        return 0x1;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return 0x1;
    }
    if (func_60())
    {
        return 0x1;
    }
    if (global18 == 0 && run_attack_update()) // tilts / down smash turning from a run (universal mechanics)
    {
        return 0x1;
    }
    var0 = PostureModuleF(0);
    var1 = global48 * var0;
    var2 = ControlModuleF(0);
    var3 = WorkModule(0x6, 0x12000017);
    var4 = WorkModule(0x6, 0x12000018);
    var5 = WorkModule(0x6, 0x10000056);
    var6 = 0;
    if (var5 >= var3 && var5 <= var3 + var4)
    {
        if (func_88() > 0)
        {
            var6 = 0x1;
        }
    }
    if (var6 == 0x1)
    {
        if (WorkModule(0x15, 0x1e000063))
        {
            if (func_72(global25))
            {
                if (global24 & 0x2000)
                {
                    func_16(0x153, 0x1);
                    return 0x1;
                }
            }
        }
        if (WorkModule(0x15, 0x1e00007b) && ItemModule(0x5, 0x4) == 0x1)
        {
            if (global24 & 0x10)
            {
                func_16(0x94, 0x1);
                return 0x1;
            }
        }
        if (WorkModule(0x15, 0x1e00007d) && ItemModule(0x5, 0x4) == 0x1)
        {
            if (global24 & 0x2)
            {
                func_16(0x93, 0x1);
                return 0x1;
            }
        }
        if (WorkModule(0x15, 0x1e000074) && ItemModule(0x5, 0x8) == 0x1)
        {
            if (global24 & 0x2)
            {
                func_16(0x8c, 0);
                return 0x1;
            }
        }
        if (WorkModule(0x15, 0x1e000088) && ItemModule(0x5, 0x2) == 0x1)
        {
            if (global24 & 0x10)
            {
                if (ItemModule(0x1a) <= 0)
                {
                    func_16(0x8c, 0);
                    return 0x1;
                }
                else
                {
                    func_16(0x98, 0x1);
                    return 0x1;
                }
            }
        }
        if (WorkModule(0x15, 0x1e000084) && ItemModule(0x5, 0x2) == 0x1)
        {
            if (global24 & 0x2)
            {
                if (ItemModule(0x1a) <= 0)
                {
                    func_16(0x8c, 0);
                    return 0x1;
                }
                else
                {
                    func_16(0x98, 0x1);
                    return 0x1;
                }
            }
        }
    }
    if (global18 == 0)
    {
        if (WorkModule(0x15, 0x1e00006f))
        {
            if (global24 & 0x20000000)
            {
                if (ItemModule(0x4) == 0)
                {
                    func_16(0x39, 0x1);
                    return 0x1;
                }
            }
        }
    }
    if (var6 == 0x1)
    {
        if (WorkModule(0x15, 0x1e000059))
        {
            if (global24 & 0x10)
            {
                var7 = ControlModule(0x16, 0, 0x4);
                var8 = PostureModuleF(0);
                if (var7 == 0x1 && var8 != -1.0f || var7 == 0x2 && var8 != 1.0f)
                {
                    ControlModule(0x17, 0, 0x4);
                    ControlModule(0x18, 0, 0x4);
                }
                else
                {
                    func_16(0x2b, 0x1);
                    return 0x1;
                }
            }
        }
        if (WorkModule(0x15, 0x1e000055))
        {
            if (global24 & 0x2)
            {
                var7 = ControlModule(0x16, 0, 0x1);
                var8 = PostureModuleF(0);
                if (var7 == 0x1 && var8 != -1.0f || var7 == 0x2 && var8 != 1.0f)
                {
                    ControlModule(0x17, 0, 0x1);
                    ControlModule(0x18, 0, 0x1);
                }
                else
                {
                    func_16(0x28, 0x1);
                    return 0x1;
                }
            }
        }
    }
    else
    {
        if (global24 & 0x10)
        {
            var7 = ControlModule(0x16, 0, 0x4);
            var8 = PostureModuleF(0);
            if (var7 == 0x1 && var8 != -1.0f || var7 == 0x2 && var8 != 1.0f)
            {
                ControlModule(0x17, 0, 0x4);
                ControlModule(0x18, 0, 0x4);
            }
        }
        if (global24 & 0x2)
        {
            var7 = ControlModule(0x16, 0, 0x1);
            var8 = PostureModuleF(0);
            if (var7 == 0x1 && var8 != -1.0f || var7 == 0x2 && var8 != 1.0f)
            {
                ControlModule(0x17, 0, 0x1);
                ControlModule(0x18, 0, 0x1);
            }
        }
    }
    if (global18 == 0)
    {
        if (WorkModule(0x15, 0x1e000028) == 0x1 && global24 & 0x4000000)
        {
            func_16(0x21, 0x1);
            return 0x1;
        }
        if (func_51())
        {
            return 0x1;
        }
        if (MotionModule(0x2712) || WorkModule(0x10, 0x2100000f) == 0x1)
        {
            if (func_88() >= WorkModuleF(0, 0x200000e))
            {
                func_16(0x4, 0x1);
                return 0x1;
            }
        }
        if (WorkModule(0x10, 0x2100000e))
        {
            if (WorkModule(0x10, 0x2100000d) == 0)
            {
                if (func_84() < WorkModuleF(0, 0x200000e))
                {
                    func_16(0x9, 0x1);
                    return 0x1;
                }
            }
        }
        if (WorkModule(0x10, 0x2100000e))
        {
            if (WorkModule(0x10, 0x2100000d) == 0)
            {
                if (func_89() >= var9)
                {
                    func_16(0, 0x1);
                    return 0x1;
                }
            }
        }
    }
}

void func_731()
{
    func_22(0x17, 0, 1.0f);
    func_78(func_732);
}

void func_732()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return 0x1;
    }
    if (global18 == 0 && run_attack_update()) // tilts / down smash turning from a run (TurnRunBrake) (universal mechanics)
    {
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00002c))
    {
        if (ControlModule(0x2712, 0x2))
        {
            func_16(0xa, 0x1);
            return 0x1;
        }
    }
    if (WorkModule(0x15, 0x1e00002b))
    {
        if (global32 >= WorkModuleF(0, 0x2000048))
        {
            if (ControlModule(0x271c))
            {
                func_16(0xa, 0x1);
                return 0x1;
            }
        }
    }
    if (func_694())
    {
        return 0x1;
    }
    if (global18 == 0)
    {
        if (MotionModule(0x2712))
        {
            func_16(0, 0);
            return 0x1;
        }
    }
}

void func_733()
{
    
}

void func_734()
{
    
}

void func_735()
{
    
}

void func_736()
{
    
}

void func_737()
{
    
}

void func_738()
{
    func_780();
}

void func_739()
{
    func_780();
}

void func_740()
{
    
}

void func_741()
{
    
}

void func_742()
{
    if (WorkModule(0x2712, 0x2100000d))
    {
        WorkModule(0x16, 0x1e00000b);
        WorkModule(0x2711, 0x2100000d);
    }
    else
    {
        WorkModule(0x17, 0x1e00000b);
    }
}

void func_743()
{
    CameraModule(0);
}

void func_744()
{
    int var0;
    var0 = WorkModule(0x6, 0x11000002);
    var0++;
    WorkModule(0x7, var0, 0x11000002);
    if (WorkModule(0x2712, 0x2100000d) == 0)
    {
        if ((float)var0 > WorkModuleF(0, 0x2000009))
        {
            WorkModule(0x2710, 0x2100000d);
        }
    }
    if (WorkModule(0x2712, 0x2100000e) == 0)
    {
        if ((float)var0 > WorkModuleF(0, 0x200000a))
        {
            WorkModule(0x2710, 0x2100000e);
        }
    }
    if (WorkModule(0x2712, 0x21000010) == 0)
    {
        WorkModule(0x2710, 0x21000010);
    }
}

void func_745()
{
    int var0;
    float var1;
    float var2;
    float var3;
    var0 = global6;
    if (var0 == 0x4)
    {
        
    }
    else if (var0 == 0x27)
    {
        
    }
    else if (var0 == 0xa)
    {
        
    }
    else if (var0 == 0x2b || var0 == 0x153)
    {
        var1 = KineticModuleF(0xb, 0x2);
        KineticModule(0x11, 0x2, 0, var1);
    }
    else if (global18 == 0)
    {
        var2 = WorkModuleF(0, 0x200000d);
        var3 = GroundModuleF(0);
        if (var3 < 1.0f)
        {
            var2 += (1.0f - var2) * (1.0f - var3);
        }
        KineticModule(0x8, 0x2, var2, 1.0f, 1.0f);
    }
    CameraModule(0x1);
}

void func_746()
{
    int var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    float var7;
    BattleObject(0x73);
    var0 = WorkModule(0x6, 0x130000cb);
    var1 = WorkModuleF(0, 0x30000cd);
    var2 = WorkModuleF(0, 0x30000ce);
    var3 = WorkModuleF(0, 0x30000cf);
    var4 = 1.0f;
    EffectModule(0x2717, 0x10000ea, var0, var1, var2, var3, 0, 0, 0, var4, 0);
    EffectModule(0x1f, 0x32, 0);
    func_747(0);
    var5 = WorkModuleF(0, 0x3000103);
    var6 = WorkModuleF(0, 0x3000104);
    var7 = WorkModuleF(0, 0x3000105);
    AttackModule(0x2720, 0, 0, var5, var6, var7);
    WorkModule(0x2710, 0x2100000e);
}

void func_747(int arg0)
{
    int var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    var1 = BattleObject(0x77, 0x36);
    var2 = WorkModuleF(0, 0x90000a8 + var1 - 0x1);
    var3 = WorkModuleF(0, 0x90000ab + var1 - 0x1);
    var4 = (float)WorkModule(0x6, 0x190000ae + var1 - 0x1) + 0;
    var5 = (float)arg0 / var4;
    if (var5 > 1.0f)
    {
        var5 = 1.0f;
    }
    var6 = var2 * (1.0f - var5) + var3 * var5;
    AttackModule(0x271a, 0, var6);
}

void func_748()
{
    EffectModule(0x9, 0x10000ea, 0, 0x1);
    WorkModule(0x2710, 0x2100000e);
    EffectModule(0x20, 0x32);
}

void func_749()
{
    float var0;
    float var1;
    float var2;
    float var3;
    var0 = WorkModuleF(0, 0x1000007);
    var1 = WorkModuleF(0, 0x1000008);
    if (WorkModule(0x10, 0x2000000a))
    {
        var2 = WorkModuleF(0, 0x200021d);
        var1 *= var2;
        if (var1 < var2)
        {
            var1 = var2;
        }
    }
    else
    {
        var1 *= func_13(var0);
    }
    var3 = WorkModuleF(0, 0x2000019);
    if (var1 > var3)
    {
        var1 = var3;
    }
    MotionModule(0x4, var1);
}

void func_750()
{
    float var0;
    int var1;
    float var2;
    float var3;
    if (BattleObject(0x6e, 0x36) == 0x1)
    {
        func_746();
    }
    var0 = WorkModuleF(0, 0x300000b);
    var1 = WorkModule(0x10, 0x2000000a);
    if (var1)
    {
        KineticModule(0, 0x46);
    }
    else
    {
        KineticModule(0, 0xe);
    }
    func_762(var0, 0x12, 0x1000007, 1.0f, 0x1000008, 0);
    if (var1)
    {
        var2 = WorkModuleF(0, 0x1000007);
        if (func_13(var2) < 1.0f)
        {
            var3 = WorkModuleF(0, 0x200021d);
            WorkModule(0, PostureModuleF(0) * var3 + 0, 0x1000007);
        }
    }
    func_749();
    CameraModule(0);
}

void func_751()
{
    float var0;
    float var1;
    var0 = WorkModuleF(0, 0x300000b);
    if (WorkModule(0x10, 0x2100000d))
    {
        func_762(var0, 0x12, 0x1000007, 1.0f, 0x1000008, 0);
        WorkModule(0x2711, 0x2100000d);
    }
    var1 = WorkModuleF(0, 0x1000007);
    func_774(var1, var0, WorkModuleF(0, 0x3000009), WorkModuleF(0, 0x300000a), WorkModuleF(0, 0x200000f), 0x1000007, 1.0f, 0);
    func_749();
    if (WorkModuleF(0, 0x1000006) > 0)
    {
        WorkModule(0x3, 1.0f, 0x1000006);
    }
    if (WorkModule(0x10, 0x2100000e))
    {
        WorkModule(0x9, 0x11000002);
        func_747(WorkModule(0x6, 0x11000002));
    }
}

void func_752()
{
    CameraModule(0x1);
    if (WorkModule(0x10, 0x2100000e))
    {
        func_748();
    }
}

void func_753()
{
    WorkModule(0, WorkModule(0x6, 0x1300004d), 0x1000006);
    WorkModule(0x11, 0x2100000f);
    CameraModule(0);
}

void func_754()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    int var6;
    if (WorkModule(0x10, 0x2100000e) == 0)
    {
        var0 = WorkModuleF(0, 0x300000b) * WorkModuleF(0, 0x2000011);
        var1 = KineticModuleF(0, 0x1);
        var1 = func_13(var1);
        var2 = MotionModuleF(0x1);
        var3 = BattleObjectF(0x63);
        if (var1 > var0 && var3 > var2)
        {
            var5 = WorkModuleF(0, 0x3000007) * WorkModuleF(0, 0x2000010) * GroundModuleF(0);
            var6 = (int)((var1 - var0) / var5);
            if (var6 == 0)
            {
                var4 = var3 - var2;
            }
            else
            {
                var4 = (var3 - var2) / (float)var6;
            }
        }
        else
        {
            var4 = 1.0f;
            WorkModule(0x11, 0x2100000e);
        }
        MotionModule(0x4, var4);
    }
    if (WorkModuleF(0, 0x1000006) > 0)
    {
        WorkModule(0x3, 1.0f, 0x1000006);
    }
}

void func_755()
{
    CameraModule(0x1);
}

void func_756()
{
    float var0;
    float var1;
    float var2;
    if (StatusModule(0) == 0x7)
    {
        var0 = 0;
        WorkModule(0, var0, 0x1000007);
        WorkModule(0x11, 0x2100000d);
    }
    else
    {
        var1 = WorkModuleF(0, 0x300004f);
        WorkModule(0, var1, 0x1000007);
        WorkModule(0x12, 0x2100000d);
    }
    WorkModule(0x12, 0x2100000f);
    var2 = PostureModuleF(0);
    WorkModule(0, var2, 0x1000006);
    PostureModule(0x1);
    CameraModule(0);
}

void func_757()
{
    float var0;
    float var1;
    float var2;
    int var3;
    float var4;
    float var5;
    float var6;
    float var7;
    WorkModule(0x12, 0x2100000e);
    var0 = 0;
    if (WorkModuleF(0, 0x1000007) > var0)
    {
        var1 = 1.0f;
        WorkModule(0x3, var1, 0x1000007);
    }
    else if (WorkModule(0x10, 0x2100000f) == 0)
    {
        WorkModule(0x11, 0x2100000f);
        WorkModule(0x11, 0x2100000e);
    }
    var2 = WorkModuleF(0, 0x2000007);
    var3 = WorkModule(0x6, 0x12000008);
    var4 = ControlModuleF(0);
    var5 = -WorkModuleF(0, 0x1000006);
    var6 = var4 * var5;
    var7 = (float)ControlModule(0x2);
    if (var6 > var2 && var7 < (float)var3)
    {
        WorkModule(0x11, 0x2100000d);
    }
}

void func_758()
{
    CameraModule(0x1);
}

void func_759()
{
    float var0;
    float var1;
    var0 = PostureModuleF(0);
    WorkModule(0, var0, 0x1000007);
    WorkModule(0x12, 0x2100000e);
    var1 = WorkModuleF(0, 0x2000016);
    WorkModule(0, var1, 0x1000006);
    WorkModule(0x12, 0x2100000d);
    if (WorkModule(0x10, 0x20000016))
    {
        SoundModule(0x2710, 0x350062);
    }
    CameraModule(0);
}

void func_760()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    if (WorkModule(0x10, 0x2100000d))
    {
        if (WorkModule(0x10, 0x2100000e) == 0)
        {
            var0 = 0;
            MotionModule(0x4, var0);
            WorkModule(0x11, 0x2100000e);
        }
        else
        {
            var1 = 0;
            var2 = WorkModuleF(0, 0x1000007);
            if (var2 * KineticModuleF(0, 0x1) <= var1)
            {
                var0 = 1.0f;
                MotionModule(0x4, var0);
                WorkModule(0x12, 0x2100000d);
            }
            else if (WorkModule(0x6, 0x11000002) < 0)
            {
                var3 = 1.0f;
                var4 = GroundModuleF(0);
                if (var4 < var3 && GroundModule(0x10, var2))
                {
                    var0 = 1.0f;
                    MotionModule(0x4, var0);
                    WorkModule(0x12, 0x2100000d);
                }
            }
        }
    }
}

void func_761()
{
    int var0;
    var0 = global6;
    if (var0 == 0x39 || var0 == 0x21)
    {
        PostureModule(0, WorkModuleF(0, 0x1000007));
    }
    CameraModule(0x1);
}

void func_762(float arg0, int arg1, int arg2, float arg3, int arg4, int arg5)
{
    float var6;
    float var7;
    float var8;
    float var9;
    float var10;
    int var11;
    float var12;
    float var13;
    var6 = KineticModuleF(0, 0x1);
    var7 = MotionModuleF(0, arg1);
    var8 = 0;
    var9 = arg3 * arg0;
    var10 = WorkModuleF(0, 0x2000289);
    if (var9 > var10)
    {
        var9 = var10;
    }
    if (arg5)
    {
        if (var6 * PostureModuleF(0) < 0)
        {
            var8 = var6 / arg0;
        }
    }
    else if (var6 * PostureModuleF(0) > 0)
    {
        var8 = var6 / arg0;
    }
    WorkModule(0, var8, arg2);
    var11 = MotionModule(0, arg1);
    var12 = var7 / (float)var11;
    if (var12 == 0)
    {
        var12 = 9.999999747378752e-05f;
    }
    var13 = var9 / var12;
    WorkModule(0, var13, arg4);
}

void func_763(int arg0, int arg1, int arg2, int arg3, int arg4, int arg5)
{
    float var6;
    int var7;
    float var8;
    float var9;
    int var10;
    int var11;
    var6 = func_13(WorkModuleF(0, arg3));
    var7 = func_770(var6, arg0, arg1, arg2);
    var8 = func_772(arg0, arg1, arg2, var7, var6, arg4, arg5);
    var9 = 0;
    var10 = MotionModule(0, var7);
    func_22(var7, var9, var8);
    var11 = MotionModule(0xe);
    MotionModule(0x5, func_772(arg0, arg1, arg2, var7, var6, 1.0f, 0x1000007));
}

void func_764(int arg0, int arg1, int arg2, int arg3)
{
    float var4;
    float var5;
    int var6;
    var4 = 1.0f;
    var5 = WorkModuleF(0, 0x3000003);
    arg0 = 0xc;
    var6 = 0;
    func_762(var5, arg0, 0x1000006, var4, 0x1000007, var6);
    func_763(arg1, arg2, arg3, 0x1000006, var4, 0x1000007);
    CameraModule(0);
}

void func_765()
{
    func_764(0xc, 0xc, 0xb, 0xa);
}

void func_766(int arg0, int arg1, int arg2, int arg3)
{
    float var4;
    float var5;
    float var6;
    float var7;
    float var8;
    float var9;
    var4 = 1.0f;
    var5 = WorkModuleF(0, 0x3000003);
    var6 = WorkModuleF(0, 0x3000001);
    var7 = WorkModuleF(0, 0x3000002);
    var8 = WorkModuleF(0, 0x2000002);
    var9 = WorkModuleF(0, 0x1000006);
    func_774(var9, var5, var6, var7, var8, 0x1000006, var4, 0x1);
    func_773(arg0, arg1, arg2, 0x1000006, var4, 0x1000007, arg3);
    if (StopModule(0x1) == 0 && SlowModule(0x2) == 0)
    {
        func_775();
    }
    func_776();
}

void func_767()
{
    func_766(0xc, 0xb, 0xa);
}

void func_768()
{
    CameraModule(0x1);
}

void func_769()
{
    float var0;
    var0 = WorkModuleF(0, 0x1000006);
    WorkModule(0, -var0, 0x1000006);
}

int func_770(float arg0, int arg1, int arg2, int arg3)
{
    float var4;
    int var5;
    var4 = 1.0f;
    var5 = 0;
    if (arg0 > WorkModuleF(0, 0x3000006) * var4)
    {
        var5 = arg1;
    }
    else if (arg0 >= WorkModuleF(0, 0x3000005) * var4)
    {
        var5 = arg2;
    }
    else
    {
        var5 = arg3;
    }
    return var5;
}

float func_771(float arg0, float arg1)
{
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    var2 = WorkModuleF(0, 0x3000004);
    var3 = arg0;
    if (var2 > 0)
    {
        var4 = 0.014999999664723873f * var2;
        var5 = 0.20000000298023224f * var2;
        var6 = arg0 * 2.0f;
        var3 = MathF(0xb, var4, var5, var6) * 0.5f;
        var3 *= 0.5f / arg1;
    }
    return var3;
}

float func_772(int arg0, int arg1, int arg2, int arg3, float arg4, float arg5, int arg6)
{
    float var7;
    float var8;
    float var9;
    float var10;
    var7 = 0;
    var8 = WorkModuleF(0, 0x3000005);
    if (arg3 == arg2)
    {
        var9 = func_771(arg4, var8);
        var7 = var9 / (var8 * 0.5f * arg5);
    }
    else if (arg3 == arg1)
    {
        var7 = arg4 / ((var8 * arg5 + WorkModuleF(0, 0x3000006) * arg5) * 0.5f);
    }
    else
    {
        var7 = arg4 / arg5;
    }
    var7 *= WorkModuleF(0, arg6);
    var7 *= WorkModuleF(0, 0x18);
    var10 = WorkModuleF(0, 0x2000004);
    if (var7 > var10)
    {
        var7 = var10;
    }
    return var7;
}

void func_773(int arg0, int arg1, int arg2, int arg3, int arg4, int arg5, int arg6)
{
    float var7;
    int var8;
    int var9;
    float var10;
    int var11;
    float var12;
    int var13;
    var7 = func_13(WorkModuleF(0, arg3));
    if (MotionModule(0x6))
    {
        var8 = MotionModule(0x7);
        var9 = MotionModule(0xe);
        var10 = func_772(arg0, arg1, arg2, var8, var7, arg4, arg5);
        MotionModule(0x4, var10);
        MotionModule(0x5, func_772(arg0, arg1, arg2, var9, var7, arg4, arg5));
    }
    else
    {
        var8 = func_770(var7, arg0, arg1, arg2);
        var10 = func_772(arg0, arg1, arg2, var8, var7, arg4, arg5);
        var11 = MotionModule(0x7);
        if (var8 != var11)
        {
            if (arg6 != 0)
            {
                if ((*arg6)(var8, var11) == 0x1)
                {
                    var12 = MotionModuleF(0x1);
                    func_22(var8, var12, var10);
                    return;
                }
            }
            var13 = MotionModule(0, var8);
            var12 = MotionModuleF(0x1) / (float)MotionModule(0) * (float)var13;
            func_22(var8, var12, var10);
            var9 = MotionModule(0xe);
            MotionModule(0x5, func_772(arg0, arg1, arg2, var9, var7, 1.0f, 0x1000007));
        }
        else
        {
            MotionModule(0x4, var10);
        }
    }
}

void func_774(float arg0, float arg1, float arg2, float arg3, float arg4, int arg5, float arg6, int arg7)
{
    float var8;
    float var9;
    float var10;
    float var11;
    float var12;
    float var13;
    float var14;
    float var15;
    float var16;
    float var17;
    var8 = ControlModuleF(0);
    var9 = arg2 / arg1;
    var10 = arg3 / arg1;
    var11 = var8 * var9 * arg6;
    if (var8 > 0)
    {
        var11 += var10 * arg6;
    }
    else
    {
        var11 += -var10 * arg6;
    }
    var12 = var8 * arg6;
    var13 = WorkModuleF(0, 0x2000289);
    if (var12 > var13)
    {
        var12 = var13;
    }
    if (arg7 == 0x1 && WorkModule(0x10, 0x2000004c))
    {
        var14 = WorkModuleF(0, 0x3000005) / arg6 - 0.0010000000474974513f;
        if (var12 > var14)
        {
            var12 = var14;
        }
        else if (var12 < -var14)
        {
            var12 = -var14;
        }
    }
    if (var12 > 9.999999747378752e-06f || var12 < -9.999999747378752e-06f)
    {
        var15 = arg0 / var12;
        if (var15 > 0 && var15 < 1.0f)
        {
            var15 = 1.0f - var15;
            var11 *= var15 * arg4;
        }
    }
    else
    {
        var11 = 0;
    }
    var16 = WorkModuleF(0, 0x3000007) / arg1;
    if (var12 == 0)
    {
        if (func_13(var16) > func_13(arg0))
        {
            var11 = -arg0;
        }
        else if (arg0 > 0)
        {
            var11 = -var16;
        }
        else
        {
            var11 = var16;
        }
    }
    else if (var11 > 0)
    {
        if (arg0 + var11 > var12)
        {
            var11 = -var16;
            if (arg0 + var11 < var12)
            {
                var11 = var12 - arg0;
            }
        }
    }
    else if (arg0 + var11 < var12)
    {
        var11 = var16;
        if (arg0 + var11 > var12)
        {
            var11 = var12 - arg0;
        }
    }
    var17 = arg0 + var11;
    WorkModule(0, var17, arg5);
}

void func_775()
{
    
}

void func_776()
{
    
}

void func_777()
{
    CameraModule(0);
}

void func_778()
{
    float var0;
    float var1;
    var0 = 0.0010000000474974513f;
    var1 = KineticModuleF(0, 0x1);
    if (!WorkModule(0x10, 0x2100000e))
    {
        if (func_13(var1) > var0)
        {
            MotionModule(0x4, WorkModuleF(0, 0x2000005));
            WorkModule(0x11, 0x2100000e);
        }
        else
        {
            MotionModule(0x4, 1.0f);
        }
    }
    else if (func_13(var1) <= var0)
    {
        MotionModule(0x4, 1.0f);
    }
}

void func_779()
{
    CameraModule(0x1);
}

void func_780()
{
    int var0;
    var0 = global6;
    if (var0 == 0x20 || var0 == 0x21)
    {
        PostureModule(0x1);
        PostureModule(0x2);
    }
    else if (WorkModule(0x10, 0x2100000f) == 0)
    {
        if (var0 == 0xa)
        {
            PostureModule(0x1);
            PostureModule(0x2);
        }
    }
}

void func_781()
{
    float var0;
    int var1;
    if (!global3 && global4 != 0x4b)
    {
        var0 = (float)WorkModule(0x6, 0x1000003e);
        var1 = (int)(var0 * WorkModuleF(0, 0x2000115));
        if (var1 > WorkModule(0x6, 0x12000116))
        {
            var1 = WorkModule(0x6, 0x12000116);
        }
        if (var1 > 0)
        {
            WorkModule(0x7, var1, 0x1100000c);
            WorkModule(0, 1.0f + 0, 0x100000c);
            WorkModule(0x2710, 0x21000015);
            KineticModule(0xc, 0x1);
            KineticModule(0xc, 0x4);
            StatusModule(0x2712, 0x1);
            GroundModule(0x2719, 0xff);
        }
    }
}

void func_782()
{
    if (WorkModule(0x10, 0x21000015))
    {
        KineticModule(0xb, 0x1);
        KineticModule(0xb, 0x4);
        StatusModule(0x2712, 0);
        MotionModule(0x4, WorkModuleF(0, 0x100000c));
        GroundModule(0x271a);
        WorkModule(0x2711, 0x21000015);
    }
}

int func_783()
{
    int var0;
    var0 = 0x4;
    if (WorkModule(0x6, 0x1000006b) != 0)
    {
        var0 |= 0x3e0;
    }
    StatusModule(0x5, 0, 0x20, 0x1, 0, 0x1, 0, 0, 0x80, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, var0, 0, 0);
    return 0;
}

void func_784()
{
    WorkModule(0x16, 0x1e000000);
    WorkModule(0x16, 0x1e000002);
    WorkModule(0x16, 0x1e000005);
    if (!StopModule(0x1))
    {
        func_785();
    }
    global16 = func_785;
    func_78(func_786);
}

void func_785()
{
    if (WorkModule(0x10, 0x2100000e) == 0x1 && WorkModule(0x10, 0x2100000d) == 0)
    {
        CancelModule(0x2710);
        WorkModule(0x2710, 0x2100000d);
    }
}

void func_786()
{
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (global18 == 0x2)
    {
        if (GroundModule(0x2727))
        {
            func_16(0x7d, 0);
            return;
        }
    }
    if (WorkModule(0x15, 0x1e000002) == 0x1 && WorkModule(0x10, 0x2100000e) == 0x1 && MotionModule(0x2712) == 0x1 && global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e000000) == 0x1)
    {
        if (WorkModule(0x10, 0x2100000e) == 0x1)
        {
            if (MotionModule(0x2712) == 0x1)
            {
                if (global18 == 0)
                {
                    func_16(0, 0);
                    return;
                }
            }
        }
    }
    if (GroundModule(0x2722, 0x2) == 0x1 && -KineticModuleF(0x4, 0x4) > WorkModuleF(0, 0x200010b))
    {
        func_16(0x49, 0);
        return 0x1;
    }
    if (GroundModule(0x2722, 0x4) == 0x1 && KineticModuleF(0x4, 0x4) > WorkModuleF(0, 0x200010b))
    {
        func_16(0x49, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000005) == 0x1 && global18 == 0x2)
    {
        func_16(0x4c, 0);
        return;
    }
}

void func_787()
{
    
}

int func_788()
{
    int var0;
    var0 = 0x4;
    if (WorkModule(0x6, 0x1000006b) != 0)
    {
        var0 |= 0x3e0;
    }
    StatusModule(0x5, 0x2, 0x21, 0x5, 0, 0x1, 0, 0, 0x80, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, var0, 0, 0);
    return 0;
}

void func_789()
{
    WorkModule(0x16, 0x1e000002);
    WorkModule(0x16, 0x1e00000d);
    WorkModule(0x16, 0x1e00001b);
    if (!StopModule(0x1))
    {
        func_790();
    }
    global16 = func_790;
    WorkModule(0, PostureModuleF(0x2) + 0, 0x100000b);
    func_78(func_791);
}

void func_790()
{
    int var0;
    if (StopModule(0) == 0)
    {
        if (WorkModule(0x10, 0x2100000e) == 0x1 && WorkModule(0x10, 0x2000000b) == 0 && WorkModule(0x10, 0x20000032) == 0)
        {
            if (WorkModule(0x10, 0x2100000d) == 0)
            {
                CancelModule(0x2710);
                KineticModule(0, 0);
                WorkModule(0x19, 0x1f00000a);
                BattleObject(0x17, 0x4);
                WorkModule(0x2710, 0x2100000d);
            }
            if (KineticModuleF(0x5, 0x4) <= 0)
            {
                WorkModule(0x19, 0x1f00000f);
                WorkModule(0x19, 0x1f000010);
                WorkModule(0x19, 0x1f000011);
            }
            func_550();
        }
        var0 = WorkModule(0x6, 0x1100000e);
        if (var0 > 0)
        {
            if (StatusModule(0x6) == 0)
            {
                var0--;
                if (var0 <= 0)
                {
                    KineticModule(0xf, 0x1, -WorkModuleF(0, 0x3000018));
                    KineticModule(0x15, 0x1, WorkModuleF(0, 0x3000019));
                }
                WorkModule(0x7, var0, 0x1100000e);
            }
        }
    }
}

void func_791()
{
    float var0;
    float var1;
    float var2;
    if (CancelModule(0x2713) == 0x1)
    {
        if (global18 == 0)
        {
            var0 = WorkModuleF(0, 0x100000b) - PostureModuleF(0x2);
            if (var0 < 2.0f)
            {
                func_16(0x1a, 0);
                return;
            }
        }
        if (func_41() != 0)
        {
            return;
        }
    }
    if (func_58())
    {
        return;
    }
    if (WorkModule(0x15, 0x1e000002) == 0x1 && WorkModule(0x10, 0x2100000e) == 0x1 && MotionModule(0x2712) == 0x1)
    {
        func_16(0xe, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e00000d) == 0x1 && global18 == 0 && KineticModuleF(0x3, 0x4) >= WorkModuleF(0, 0x2000058) && !(StopModule(0) == 0x1 || WorkModule(0x6, 0x11000003) > 0))
    {
        func_16(0x4d, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e00001b) == 0x1 && global18 == 0 && !(StopModule(0) == 0x1 || WorkModule(0x6, 0x11000003) > 0))
    {
        func_16(0x16, 0);
        return;
    }
    if (StatusModule(0x6) == 0)
    {
        var1 = PostureModuleF(0x2);
        var2 = PostureModuleF(0x9);
        if (var1 <= var2)
        {
            if (WorkModule(0x10, 0x21000014) == 0)
            {
                WorkModule(0, var2 + 0, 0x100000b);
                WorkModule(0x2710, 0x21000014);
            }
        }
        else
        {
            WorkModule(0x2711, 0x21000014);
        }
    }
}

void func_792()
{
    
}

int func_793()
{
    int var0;
    var0 = 0x4;
    if (WorkModule(0x6, 0x1000006b) != 0)
    {
        var0 |= 0x3e0;
    }
    StatusModule(0x5, 0x2, 0x22, 0x5, 0, 0x1, 0x11000000, 0, 0x80, 0);
    if (WorkModule(0x10, 0x2100001c))
    {
        var0 |= 0x8;
        WorkModule(0x2711, 0x2100001c);
    }
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, var0, 0, 0);
    return 0;
}

int func_794()
{
    int var0;
    var0 = 0x4;
    if (WorkModule(0x6, 0x1000006b) != 0)
    {
        var0 |= 0x3e0;
    }
    StatusModule(0x5, 0x2, 0x22, 0x5, 0, 0x1, 0, 0, 0x80, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, var0, 0, 0);
    return 0;
}

int func_795()
{
    StatusModule(0x5, 0x2, 0x5a, 0x5, 0x4, 0x1, 0x2, 0, 0, 0x100);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_796()
{
    float var0;
    float var1;
    float var2;
    float var3;
    if (BattleObject(0x57) == 0x1 && !WorkModule(0x10, 0x20000076))
    {
        EffectModule(0x2723, 0x100009f, 0x1, 0x1);
        EffectModule(0x2710, 0x100009f, WorkModule(0x6, 0x1300006a), 0, 0, 0, 0, 90.0f * PostureModuleF(0), 0, 1.0f, 0, 0, 0, 0, 0, 0, 0);
    }
    var0 = sys_40(0xe);
    if (var0 > 0)
    {
        var1 = ModelModuleF(0, 0x3);
        var2 = ModelModuleF(0x1, 0x3);
        var3 = ModelModuleF(0x2, 0x3);
        EffectModule(0x2732, 0x2, 0, var0, var0, var1, var2, var3, 0, 0x1);
    }
}

void func_797()
{
    WorkModule(0x16, 0x1e000005);
    WorkModule(0x16, 0x1e00000d);
    WorkModule(0x16, 0x1e000006);
    WorkModule(0x16, 0x1e000007);
    WorkModule(0x16, 0x1e000008);
    WorkModule(0x16, 0x1e000009);
    if (WorkModule(0x10, 0x21000018) == 0)
    {
        WorkModule(0x16, 0x1e000017);
        WorkModule(0x16, 0x1e000016);
        WorkModule(0x16, 0x1e000015);
        WorkModule(0x16, 0x1e000018);
        WorkModule(0x16, 0x1e000014);
        WorkModule(0x16, 0x1e000013);
    }
    else
    {
        WorkModule(0x17, 0x1e000017);
        WorkModule(0x17, 0x1e000016);
        WorkModule(0x17, 0x1e000015);
        WorkModule(0x17, 0x1e000018);
        WorkModule(0x17, 0x1e000014);
        WorkModule(0x17, 0x1e000013);
    }
}

void func_798()
{
    func_797();
    func_800();
    func_796();
    func_78(func_799);
}

int func_799()
{
    if (CancelModule(0x2713) == 0x1 && func_41() != 0)
    {
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000005))
    {
        if (MotionModule(0x2712))
        {
            if (WorkModule(0x10, 0x2100000e))
            {
                func_16(0x4c, 0);
                return 0x1;
            }
        }
    }
    if (func_805())
    {
        return 0x1;
    }
    if (func_806() == 0x1)
    {
        return 0x1;
    }
    if (func_807() == 0x1)
    {
        return 0x1;
    }
    if (func_808() == 0x1)
    {
        return 0x1;
    }
    return 0;
}

void func_800()
{
    if (DamageModuleF(0x7) < WorkModuleF(0, 0x200014b))
    {
        WorkModule(0x7, 0x1, 0x11000005);
    }
    else if (DamageModuleF(0x7) < WorkModuleF(0, 0x200014c))
    {
        WorkModule(0x7, 0x2, 0x11000005);
    }
    else
    {
        WorkModule(0x7, 0x3, 0x11000005);
    }
}

int func_801()
{
    if (BattleObject(0x86, 0))
    {
        return 0x1;
    }
    return ControlModule(0x2722, 0x3) < WorkModule(0x6, 0x12000081) && ControlModule(0x2723, 0x3) >= WorkModule(0x6, 0x12000080);
}

int func_802()
{
    if (WorkModule(0x10, 0x2000005a))
    {
        return 0;
    }
    if (WorkModule(0x15, 0x1e000017) == 0x1 && GroundModule(0x2722, 0x6) == 0x1 && func_801() == 0x1 && ControlModule(0x2722, 0x2) < WorkModule(0x6, 0x12000081) && func_95() == 0 && global18 == 0x2)
    {
        func_16(0x67, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000016) == 0x1 && GroundModule(0x2722, 0x6) == 0x1 && func_801() == 0x1 && global32 >= WorkModuleF(0, 0x200001f) && func_95() == 0 && global18 == 0x2)
    {
        func_16(0x67, 0x1);
        return 0x1;
    }
    return 0;
}

int func_803()
{
    if (WorkModule(0x10, 0x2000005a))
    {
        return 0;
    }
    if (WorkModule(0x15, 0x1e000015) == 0x1 && GroundModule(0x2722, 0x6) == 0x1 && func_801() == 0x1 && func_95() == 0 && global18 == 0x2)
    {
        func_16(0x66, 0x1);
        return 0x1;
    }
    return 0;
}

int func_804()
{
    if (WorkModule(0x10, 0x2000005a))
    {
        return 0;
    }
    if (WorkModule(0x15, 0x1e000018) == 0x1 && GroundModule(0x2722, 0x1) == 0x1 && func_801() == 0x1 && func_95() == 0 && global18 == 0x2)
    {
        func_16(0x68, 0x1);
        return 0x1;
    }
    return 0;
}

int func_805()
{
    if (func_802() == 0x1)
    {
        return 0x1;
    }
    if (func_803() == 0x1)
    {
        return 0x1;
    }
    if (func_804() == 0x1)
    {
        return 0x1;
    }
    if (func_59())
    {
        return 0x1;
    }
    if (func_61())
    {
        return 0x1;
    }
    if (func_62())
    {
        return 0x1;
    }
    if (func_63())
    {
        return 0x1;
    }
    if (!global3)
    {
        if (func_809())
        {
            return 0x1;
        }
    }
    else
    {
        func_811();
    }
    return 0;
}

int func_806()
{
    if (WorkModule(0x15, 0x1e000006) == 0x1 && global18 == 0x2 && GroundModule(0x2722, 0x2) == 0x1 && -KineticModuleF(0x4, 0x4) > WorkModuleF(0, 0x200010b) && WorkModule(0x6, 0x11000001) != 0x2 && WorkModuleF(0, 0x100000e) <= 0 && WorkModule(0x6, 0x10000043) <= WorkModule(0x6, 0x12000111))
    {
        func_16(0x49, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000007) == 0x1 && global18 == 0x2 && GroundModule(0x2722, 0x4) == 0x1 && KineticModuleF(0x4, 0x4) > WorkModuleF(0, 0x200010b) && WorkModule(0x6, 0x11000001) != 0x1 && WorkModuleF(0, 0x100000e) <= 0 && WorkModule(0x6, 0x10000043) <= WorkModule(0x6, 0x12000111))
    {
        func_16(0x49, 0);
        return 0x1;
    }
    return 0;
}

int func_807()
{
    if (WorkModule(0x15, 0x1e000008) == 0x1 && global18 == 0x2 && GroundModule(0x2722, 0x1) == 0x1 && KineticModuleF(0x5, 0x4) > WorkModuleF(0, 0x200010b) && WorkModule(0x6, 0x11000001) != 0x3 && WorkModule(0x6, 0x10000043) <= WorkModule(0x6, 0x12000111))
    {
        func_16(0x4a, 0);
        return 0x1;
    }
    return 0;
}

int func_808()
{
    if (WorkModule(0x15, 0x1e000009) == 0x1 && global18 == 0 && KineticModuleF(0x1, 0x2) <= -WorkModuleF(0, 0x2000113) && WorkModule(0x6, 0x11000001) != 0x4 && WorkModule(0x6, 0x10000043) <= WorkModule(0x6, 0x12000111))
    {
        func_16(0x4b, 0);
        return 0x1;
    }
    return 0;
}

int func_809()
{
    float var0;
    float var1;
    func_790();
    if (func_95() == 0)
    {
        if (WorkModule(0x10, 0x2100001a))
        {
            if (func_84() >= WorkModuleF(0, 0x2000082))
            {
                func_16(0x65, 0x1);
                return 0x1;
            }
            else
            {
                func_16(0x64, 0x1);
                return 0x1;
            }
        }
        if (WorkModule(0x10, 0x21000012) == 0)
        {
            var0 = func_93();
            var1 = (float)WorkModule(0x6, 0x11000004);
            if (var0 < -1.0f || var1 >= (float)WorkModule(0x6, 0x1200011d))
            {
                if (func_812())
                {
                    return 0x1;
                }
                WorkModule(0x2710, 0x21000012);
            }
        }
        else if (func_812())
        {
            return 0x1;
        }
        if (WorkModule(0x10, 0x2000000b) == 0 && WorkModule(0x10, 0x20000032) == 0)
        {
            if (WorkModule(0x6, 0x11000006) <= 0 && KineticModuleF(0x3, 0x4) <= WorkModuleF(0, 0x20000ff))
            {
                WorkModule(0x19, 0x1f00000b);
                WorkModule(0x19, 0x1f00000e);
                func_105();
                func_104();
            }
            if (WorkModule(0x6, 0x11000007) <= 0 && KineticModuleF(0x3, 0x4) <= WorkModuleF(0, 0x2000101))
            {
                WorkModule(0x19, 0x1f00000c);
                WorkModule(0x19, 0x1f00000d);
            }
        }
    }
    return 0;
}

int func_810()
{
    if (WorkModule(0x10, 0x2000005a))
    {
        return 0;
    }
    if (WorkModule(0x15, 0x1e000014) == 0x1 && global18 == 0 && func_801() == 0x1 && func_84() >= WorkModuleF(0, 0x2000082) && func_95() == 0)
    {
        func_16(0x65, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000013) == 0x1 && global18 == 0 && func_801() == 0x1 && func_95() == 0)
    {
        func_16(0x64, 0x1);
        return 0x1;
    }
    return 0;
}

int func_811()
{
    if (WorkModule(0x10, 0x2000005a))
    {
        return 0;
    }
    if (WorkModule(0x10, 0x2100001a))
    {
        return 0;
    }
    if (WorkModule(0x10, 0x21000019) == 0)
    {
        return 0;
    }
    if (WorkModule(0x10, 0x2100000f) == 0)
    {
        return 0;
    }
    if (WorkModule(0x10, 0x2100001b) == 0x1)
    {
        return 0;
    }
    if (WorkModule(0x15, 0x1e000014) == 0x1 && func_801() == 0x1 && func_84() >= WorkModuleF(0, 0x2000082))
    {
        WorkModule(0x2710, 0x2100001a);
        KineticModule(0x7, 0x4);
        GroundModule(0x2710, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000013) == 0x1 && func_801() == 0x1)
    {
        WorkModule(0x2710, 0x2100001a);
        KineticModule(0x7, 0x4);
        GroundModule(0x2710, 0x1);
        return 0x1;
    }
    return 0;
}

int func_812()
{
    if (func_810() == 0x1)
    {
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00000d) == 0x1)
    {
        if (!func_95())
        {
            if (func_808() == 0x1)
            {
                return 0x1;
            }
            if (global18 == 0)
            {
                func_16(0x4d, 0);
                return 0x1;
            }
        }
    }
    return 0;
}

void func_813()
{
    WorkModule(0x16, 0x1e000005);
    WorkModule(0x16, 0x1e000006);
    WorkModule(0x16, 0x1e000007);
    WorkModule(0x16, 0x1e000008);
    WorkModule(0x16, 0x1e000009);
    WorkModule(0x16, 0x1e000017);
    WorkModule(0x16, 0x1e000016);
    WorkModule(0x16, 0x1e000015);
    WorkModule(0x16, 0x1e000018);
    WorkModule(0x16, 0x1e000014);
    WorkModule(0x16, 0x1e000013);
    func_800();
    func_796();
    func_78(func_814);
}

void func_814()
{
    if (WorkModule(0x15, 0x1e000005))
    {
        if (WorkModule(0x10, 0x2100000e))
        {
            func_16(0x4c, 0);
            return;
        }
    }
    if (func_808() == 0x1)
    {
        return;
    }
    if (global18 == 0 && WorkModule(0x10, 0x2100001a) == 0)
    {
        func_16(0x4d, 0);
        return;
    }
    if (func_805())
    {
        return;
    }
    if (func_806() == 0x1)
    {
        return;
    }
    if (func_807() == 0x1)
    {
        return;
    }
}

void func_815()
{
    WorkModule(0x16, 0x1e00000d);
    if (0x47 == global5 || 0x48 == global5 || 0x49 == global5 || 0x4a == global5 || 0x4b == global5 || 0x13a == global5)
    {
        if (MotionModule(0x7) != 0x2e)
        {
            WorkModule(0, WorkModuleF(0, 0x2000120) + 0, 0x1000006);
        }
    }
    if (MotionModule(0x28) == 0x1)
    {
        WorkModule(0x2710, 0x2100000d);
    }
    else
    {
        WorkModule(0x2711, 0x2100000d);
    }
    if (0xc8 == global5 || 0x48 == global5)
    {
        MotionModule(0x27, 0x1);
    }
    if (WorkModule(0x10, 0x20000054))
    {
        WorkModule(0x16, 0x1e000013);
        WorkModule(0x16, 0x1e000014);
    }
    if (MotionModule(0x7) != 0x2e)
    {
        func_22(0x2e, 0, 1.0f);
    }
    if (!WorkModule(0x10, 0x2000001b))
    {
        if (!StopModule(0x1))
        {
            func_817();
        }
        global16 = func_817;
    }
    func_78(func_816);
}

void func_816()
{
    if (func_56())
    {
        return 0x1;
    }
    if (func_896())
    {
        return;
    }
    if (WorkModule(0x10, 0x20000054))
    {
        if (WorkModule(0x15, 0x1e000014) == 0x1 && global18 == 0 && (ControlModule(0x2722, 0x3) < 0x4 && ControlModule(0x2723, 0x3) >= WorkModule(0x6, 0x12000080) || BattleObject(0x86, 0)) && func_84() >= WorkModuleF(0, 0x2000082) && func_95() == 0)
        {
            func_16(0x65, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000013) == 0x1 && global18 == 0 && (ControlModule(0x2722, 0x3) < 0x4 && ControlModule(0x2723, 0x3) >= WorkModule(0x6, 0x12000080) || BattleObject(0x86, 0)) && func_95() == 0)
        {
            func_16(0x64, 0x1);
            return 0x1;
        }
    }
    if (WorkModule(0x15, 0x1e00000d))
    {
        if (global18 == 0)
        {
            if (BattleObject(0x86, 0))
            {
                if (WorkModule(0x15, 0x1e00003d))
                {
                    func_16(0x22, 0);
                    return;
                }
            }
            func_16(0x4d, 0);
            return;
        }
    }
    if (!WorkModule(0x10, 0x2000001b))
    {
        if (func_84() >= WorkModuleF(0, 0x2000127))
        {
            if (global31 & 0x40)
            {
                if (WorkModule(0x6, 0x11000002) <= 0)
                {
                    if (!WorkModule(0x10, 0x2000000b) && !WorkModule(0x10, 0x20000032) == 0)
                    {
                        func_16(0xe, 0x1);
                        return;
                    }
                }
            }
        }
    }
    func_897();
}

void func_817()
{
    float var0;
    if (0 < WorkModuleF(0, 0x1000006))
    {
        WorkModule(0x2, -1.0f, 0x1000006);
    }
    else
    {
        WorkModule(0, 0 + 0, 0x1000006);
    }
    var0 = WorkModuleF(0, 0x2000120);
    if (9.999999747378752e-06f < var0)
    {
        MotionModule(0x4, (var0 - WorkModuleF(0, 0x1000006)) / var0);
    }
    else
    {
        MotionModule(0x4, 1.0f);
    }
    if (WorkModule(0x6, 0x11000002) > 0)
    {
        WorkModule(0xa, 0x11000002);
    }
    else
    {
        func_105();
        func_104();
    }
}

void func_818()
{
    if (global6 == 0x47)
    {
        WorkModule(0x2711, 0x21000018);
    }
    else if (global6 == 0xb1)
    {
        func_820();
    }
}

void func_819()
{
    if (global6 == 0xb1)
    {
        func_820();
    }
}

void func_820()
{
    int var0;
    EffectModule(0x2723, 0x1000094, 0x1, 0x1);
    var0 = WorkModule(0x6, 0x10000065);
    EffectModule(0x2723, 0x1000095 + var0, 0x1, 0x1);
}

void func_821()
{
    WorkModule(0x2711, 0x20000054);
    if (WorkModule(0x10, 0x2100000d) == 0x1)
    {
        MotionModule(0x27, 0x1);
    }
    else
    {
        MotionModule(0x27, 0);
    }
    if (WorkModule(0x10, 0x20000072))
    {
        MotionModule(0x36, 0);
        WorkModule(0x2711, 0x20000072);
    }
}

int func_822()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0, 0x2000, 0x2c, 0x40, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0x1, 0, 0);
    return 0;
}

void func_823()
{
    AreaModule(0x2710, 0);
    SoundModule(0x2710, 0xc3);
    func_826();
    BattleObject(0x66, 0x1);
    if (!StopModule(0x1))
    {
        func_825();
    }
    global16 = func_825;
    func_78(func_824);
}

void func_824()
{
    int var0;
    var0 = WorkModule(0x10, 0x2100000f);
    if (StatusModule(0x6) == 0 && !var0 && global18 == 0x2 || var0 && global18 == 0 && WorkModule(0x6, 0x11000002) >= WorkModule(0x6, 0x11000004))
    {
        func_826();
    }
    if (func_96() || WorkModule(0x10, 0x2000006f))
    {
        func_16(0xc6, 0x1);
        return;
    }
}

void func_825()
{
    WorkModule(0x9, 0x11000002);
}

void func_826()
{
    if (global18 == 0)
    {
        KineticModule(0, 0x6);
        GroundModule(0x2710, 0x1);
        WorkModule(0x2711, 0x2100000f);
    }
    else
    {
        KineticModule(0, 0x44);
        GroundModule(0x2710, 0x5);
        WorkModule(0x2710, 0x2100000f);
    }
}

void func_827()
{
    BattleObject(0x66, 0);
}

int func_828()
{
    if (func_470() != 0)
    {
        return 0x1;
    }
    StatusModule(0x5, 0x2, 0x45, 0x5, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0, 0, 0);
    return 0;
}

void func_829()
{
    func_40();
    func_564();
    func_22(0x19, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_831();
    }
    global16 = func_831;
    func_78(func_830);
}

void func_830()
{
    if (func_56())
    {
        return;
    }
    if (func_41())
    {
        return;
    }
    if (func_565())
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return;
    }
    if (WorkModule(0x6, 0x11000002) >= WorkModule(0x6, 0x12000188))
    {
        func_16(0xe, 0);
        return;
    }
}

void func_831()
{
    WorkModule(0x9, 0x11000002);
    func_550();
}

void func_832()
{
    
}

int func_833()
{
    if (func_42())
    {
        return 0x1;
    }
    StatusModule(0x5, 0, 0x1a, 0x1, 0, 0x1, 0, 0, 0, 0);
    KineticModule(0x7, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x4000000, 0, 0);
    return 0;
}

void func_834()
{
    func_22(0xf2, 0, 1.0f);
    func_78(func_835);
}

void func_835()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (func_96() == 0x1 && global18 == 0 || WorkModule(0x10, 0x2000006f))
    {
        func_16(0x5e, 0);
        return;
    }
}

void func_836()
{
    int var0;
    var0 = WorkModule(0x6, 0x1200016d);
    WorkModule(0x7, var0, 0x10000080);
}

int func_837()
{
    StatusModule(0x5, 0, 0x32, 0x1, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0, 0, 0);
    return 0;
}

void func_838()
{
    GroundModule(0x2715);
    func_94();
    KineticModule(0, 0x4c);
    func_78(func_839);
}

void func_839()
{
    if (global18 == 0)
    {
        func_16(0x4d, 0);
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return;
    }
}

void func_840()
{
    func_1769();
    if (global6 == 0x4d)
    {
        WorkModule(0x2710, 0x20000066);
    }
    else
    {
        WorkModule(0x2711, 0x20000066);
    }
}

int func_841()
{
    if (func_42())
    {
        return 0x1;
    }
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0x4000000, 0, 0);
    return 0;
}

void func_842()
{
    func_22(0xf6, 0, 1.0f);
    func_78(func_843);
}

void func_843()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712))
    {
        if (WorkModule(0x10, 0x2000006f))
        {
            func_16(0x62, 0);
            return;
        }
        if (global18 == 0)
        {
            func_16(0x60, 0);
            return;
        }
    }
}

void func_844()
{
    func_845();
}

void func_845()
{
    if (global6 == 0x60)
    {
        
    }
    else
    {
        EffectModule(0x20, 0x1e);
    }
}

int func_846()
{
    if (func_42())
    {
        return 0x1;
    }
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0x80);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0x4000000, 0, 0);
    return 0;
}

void func_847()
{
    func_22(0xf7, 0, 1.0f);
    BattleObject(0x65, 0x1);
    func_78(func_848);
}

void func_848()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (func_96() == 0x1 && global18 == 0 || WorkModule(0x10, 0x2000006f))
    {
        func_16(0x62, 0);
        return;
    }
}

void func_849()
{
    BattleObject(0x65, 0);
    func_845();
}

int func_850()
{
    StatusModule(0x5, 0x2, 0x5b, 0x5, 0, 0x1, 0, 0, 0, 0x100);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0x4000000, 0, 0);
    return 0;
}

void func_851()
{
    func_22(0x2e, 0, 1.0f);
    if (!WorkModule(0x10, 0x2000001b))
    {
        if (!StopModule(0x1))
        {
            func_817();
        }
        global16 = func_817;
    }
    func_78(func_852);
}

void func_852()
{
    if (global18 == 0)
    {
        func_16(0x60, 0);
        return;
    }
    if (func_96() == 0x1 || WorkModule(0x10, 0x2000006f))
    {
        func_16(0xe, 0);
        return;
    }
}

void func_853()
{
    if (global6 != 0x60)
    {
        EffectModule(0x20, 0x1e);
    }
}

int func_854()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0x4000000, 0, 0);
    return 0;
}

void func_855()
{
    func_22(0xf8, 0, 1.0f);
    func_78(func_856);
}

void func_856()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return;
        }
    }
}

void func_857()
{
    func_845();
}

void func_858()
{
    int var0;
    float var1;
    int var2;
    int var3;
    int var4;
    int var5;
    if (global5 == 0x61)
    {
        return;
    }
    var0 = StatusModule(0);
    func_75();
    func_76();
    WorkModule(0x7, 0, 0x11000004);
    WorkModule(0x7, 0, 0x11000001);
    WorkModule(0x7, 0, 0x11000003);
    WorkModule(0x2711, 0x2100000e);
    if (DamageModule(0x1))
    {
        WorkModule(0x2710, 0x2100000f);
    }
    if (global19 == 0)
    {
        WorkModule(0x2710, 0x21000019);
    }
    else
    {
        WorkModule(0x2711, 0x21000019);
    }
    if (global5 == 0x4d || global5 == 0x4e || global5 == 0x4f || global5 == 0x50 || global5 == 0x51 || global5 == 0x52 || global5 == 0x57)
    {
        WorkModule(0x2710, 0x2100001b);
    }
    else
    {
        WorkModule(0x2711, 0x2100001b);
    }
    if (WorkModule(0x10, 0x2000005a))
    {
        func_2199(0x1);
    }
    if (var0 == 0x5d)
    {
        var1 = WorkModuleF(0, 0x2000086);
        if (StatusModule(0xa, 0x3) == 0x59)
        {
            var1 *= WorkModuleF(0, 0x30000f8);
        }
        var1 -= DamageModuleF(0);
        var1 *= WorkModuleF(0, 0x30000fe);
        ControlModule(0x6, var1, WorkModuleF(0, 0x2000088), WorkModuleF(0, 0x2000089));
        ControlModule(0x2718, 0x1a, 0);
        EffectModule(0x1f, 0x1d, 0);
    }
    else if (var0 == 0x60 || var0 == 0x61)
    {
        var1 = WorkModuleF(0, 0x2000157) + WorkModuleF(0, 0x2000159) * sys_8(0) + WorkModuleF(0, 0x2000158) * ((float)0x3 - DamageModuleF(0xb)) + WorkModuleF(0, 0x200015a) * DamageModuleF(0x8) + WorkModuleF(0, 0x200015b) * DamageModuleF(0);
        var1 *= sys_8(0x1);
        if (DamageModule(0x7) == 0xa)
        {
            var1 *= WorkModuleF(0, 0x200015e);
        }
        var1 *= WorkModuleF(0, 0x30000fe);
        ControlModule(0x6, var1, WorkModuleF(0, 0x200015c), WorkModuleF(0, 0x200015d), 0x1);
        EffectModule(0x1f, 0x1e, 0);
    }
    else if (var0 == 0x63)
    {
        if (DamageModule(0x7) == 0x1f)
        {
            var2 = 0x2000166;
        }
        else
        {
            var2 = 0x200015f;
        }
        var1 = WorkModuleF(0, var2) + WorkModuleF(0, var2 + 0x2000161 - 0x200015f) * sys_8(0) + WorkModuleF(0, var2 + 0x2000160 - 0x200015f) * (3.0f - DamageModuleF(0xb)) + WorkModuleF(0, var2 + 0x2000162 - 0x200015f) * DamageModuleF(0x8) + WorkModuleF(0, var2 + 0x2000163 - 0x200015f) * DamageModuleF(0);
        var1 *= WorkModuleF(0, 0x30000fe);
        ControlModule(0x6, var1, WorkModuleF(0, var2 + 0x2000164 - 0x200015f), WorkModuleF(0, var2 + 0x2000165 - 0x200015f), 0x3);
        ControlModule(0x2714, 0xd, 0);
    }
    else if (var0 == 0x13a || var0 == 0x13d)
    {
        WorkModule(0x2710, 0x21000010);
        var1 = (float)DamageModule(0x8);
        var1 *= WorkModuleF(0, 0x30000fe);
        var3 = (int)var1;
        WorkModule(0x7, var3, 0x11000003);
        WorkModule(0, 0 + 0, 0x1000007);
        printf("N");
        func_22(0xd0, 0, 0);
        if (KineticModule(0x4, 0x1))
        {
            WorkModule(0x2710, 0x21000011);
        }
        else
        {
            WorkModule(0x2711, 0x21000011);
        }
        KineticModule(0xc, 0x1);
        KineticModule(0xc, 0x4);
        StatusModule(0x2712, 0x1);
    }
    else
    {
        var4 = DamageModule(0x7);
        if (var4 != 0x3 && var4 != 0x14)
        {
            func_870(0);
        }
        else
        {
            WorkModule(0x2710, 0x21000010);
            var1 = (float)DamageModule(0x8);
            if (var4 == 0x14)
            {
                var1 *= WorkModuleF(0, 0x30000fe);
            }
            var3 = (int)var1;
            WorkModule(0x7, var3, 0x11000003);
            if (global5 == 0x4c)
            {
                MotionModule(0x4, 0);
            }
            else if (WorkModule(0x10, 0x2100001b) == 0x1)
            {
                if (FighterUtil(0) == 0x1)
                {
                    var5 = 0xd8;
                }
                else
                {
                    var5 = 0xe2;
                }
                func_22(var5, 0, 0);
            }
            else
            {
                WorkModule(0, 0 + 0, 0x1000007);
                func_22(0xd4, 0, 1.0f);
            }
            if (KineticModule(0x4, 0x1))
            {
                WorkModule(0x2710, 0x21000011);
            }
            else
            {
                WorkModule(0x2711, 0x21000011);
            }
            KineticModule(0xc, 0x1);
            KineticModule(0xc, 0x4);
            StatusModule(0x2712, 0x1);
        }
    }
}

void func_859()
{
    int var0;
    float var1;
    int var2;
    if (WorkModule(0x10, 0x21000010))
    {
        var0 = WorkModule(0x6, 0x11000003);
        if (var0 > 0)
        {
            var0--;
            WorkModule(0x7, var0, 0x11000003);
        }
        if (var0 <= 0)
        {
            WorkModule(0x2711, 0x21000010);
            KineticModule(0xb, 0x4);
            if (WorkModule(0x10, 0x21000011))
            {
                KineticModule(0xb, 0x1);
            }
            if (DamageModule(0x2) == 0)
            {
                BattleObject(0x5a);
            }
            StatusModule(0x2712, 0);
            var1 = WorkModuleF(0, 0x1000007);
            if (var1 != 0)
            {
                PostureModule(0, var1);
                PostureModule(0x2);
            }
            func_870(0x1);
            if (WorkModule(0x10, 0x20000060) == 0x1)
            {
                WorkModule(0x2711, 0x20000060);
                var2 = WorkModule(0x6, 0x10000073);
                EffectModule(0x6, var2);
            }
            WorkModule(0x2711, 0x2000003c);
        }
        else if (DamageModule(0x2) == 0 && WorkModule(0x10, 0x2000003c) == 0)
        {
            BattleObject(0x5b);
        }
    }
    else
    {
        func_871();
    }
}

void func_860()
{
    if (StopModule(0) && DamageModule(0x2) == 0 && WorkModule(0x10, 0x2000003c) == 0)
    {
        BattleObject(0x5b);
    }
}

void func_861()
{
    int var0;
    var0 = global4;
    WorkModule(0x2711, 0x2000003c);
    if (global18 != 0x2)
    {
        WorkModule(0x2711, 0x20000011);
    }
    if (WorkModule(0x10, 0x2100000f) && WorkModule(0x6, 0x1000003f) <= 0)
    {
        if (var0 == 0x154 || var0 == 0xc || var0 == 0xd)
        {
            KineticModule(0x7, 0x4);
            WorkModule(0x7, 0, 0x1000003e);
        }
    }
}

int func_862(int arg0, int arg1)
{
    int var2;
    var2 = WorkModule(0x6, 0x10000064);
    if (var2 != 0xffffffff)
    {
        return var2;
    }
    if (arg0 == 0)
    {
        if (arg1 == 0)
        {
            return 0xc9;
        }
        else if (arg1 == 0x1)
        {
            return 0xc6;
        }
        else if (arg1 == 0x2)
        {
            return 0xc3;
        }
    }
    else if (arg0 == 0x1)
    {
        if (arg1 == 0)
        {
            return 0xca;
        }
        else if (arg1 == 0x1)
        {
            return 0xc7;
        }
        else if (arg1 == 0x2)
        {
            return 0xc4;
        }
    }
    else if (arg0 == 0x2)
    {
        if (arg1 == 0)
        {
            return 0xcb;
        }
        else if (arg1 == 0x1)
        {
            return 0xc8;
        }
        else if (arg1 == 0x2)
        {
            return 0xc5;
        }
    }
    return 0xc6;
}

int func_863()
{
    int var0;
    int var1;
    int var2;
    var0 = DamageModule(0x3);
    var1 = DamageModule(0);
    if (var1 >= 0x3)
    {
        var1 = 0x2;
    }
    var2 = func_862(var1, var0);
    if (var2 == MotionModule(0x7))
    {
        var0 += randi(0, 0x2) + 0x1;
        if (var0 >= 0x3)
        {
            var0 -= 0x3;
        }
        return func_862(var1, var0);
    }
    return var2;
}

int func_864()
{
    int var0;
    int var1;
    var0 = WorkModule(0x6, 0x10000064);
    if (var0 != 0xffffffff)
    {
        return var0;
    }
    if (DamageModule(0xd) == 0x1)
    {
        return 0xfe;
    }
    var1 = DamageModule(0);
    if (var1 == 0)
    {
        return 0xcc;
    }
    else if (var1 == 0x1)
    {
        return 0xcd;
    }
    else if (var1 == 0x2)
    {
        return 0xce;
    }
    return 0xcc;
}

void func_865()
{
    int var0;
    float var1;
    float var2;
    int var3;
    int var4;
    float var5;
    var0 = (int)DamageModuleF(0x1);
    var1 = DamageModuleF(0x2);
    var2 = DamageModuleF(0x3);
    var3 = StatusModule(0);
    if (WorkModule(0x10, 0x2100000f))
    {
        var4 = WorkModule(0x6, 0x13000049);
        WorkModule(0x7, var4, 0x1000003f);
    }
    if (var0 > 0)
    {
        WorkModule(0x2711, 0x2100000e);
        WorkModule(0x7, var0, 0x1000003e);
        if (global18 == 0x2)
        {
            WorkModule(0x2710, 0x2000005c);
        }
        else
        {
            WorkModule(0x2711, 0x2000005c);
        }
    }
    else
    {
        WorkModule(0x2710, 0x2100000e);
        WorkModule(0x7, 0, 0x1000003e);
    }
    var4 = WorkModule(0x6, 0x12000073);
    WorkModule(0x7, var4, 0x10000003);
    var5 = WorkModuleF(0, 0x2000093);
    if (var1 * var1 + var2 * var2 > var5 * var5)
    {
        WorkModule(0x2710, 0x2000001f);
        var4 = WorkModule(0x6, 0x12000094);
        WorkModule(0x7, var4, 0x10000021);
    }
    var4 = WorkModule(0x6, 0x120000fe);
    WorkModule(0x7, var4, 0x11000006);
    var4 = WorkModule(0x6, 0x12000100);
    WorkModule(0x7, var4, 0x11000007);
}

void func_866(int arg0)
{
    float var1;
    float var2;
    var1 = (float)WorkModule(0x6, 0x1000003e);
    if (var1 > 0)
    {
        var2 = (float)MotionModule(0, arg0) / var1 * WorkModuleF(0, 0x20000fa);
        if (WorkModule(0x10, 0x20000076))
        {
            WorkModule(0, var2 + 0, 0x100000d);
            var2 = WorkModuleF(0, 0x20001ec);
        }
        MotionModule(0x4, var2);
    }
}

void func_867(int arg0)
{
    int var1;
    float var2;
    var1 = func_863();
    if (global5 == 0x4c && arg0 == 0 && StopModule(0) == 0x1)
    {
        WorkModule(0x7, var1, 0x1100000d);
    }
    else
    {
        WorkModule(0, 0 + 0, 0x1000007);
        var2 = (float)WorkModule(0x6, 0x120000f9);
        func_29(var1, 0, 1.0f, var2);
    }
    func_872();
    if (WorkModule(0x10, 0x20000076))
    {
        WorkModule(0x7, 0xffffffff, 0x1100000d);
    }
    func_866(var1);
}

void func_868()
{
    float var0;
    int var1;
    if (!WorkModule(0x10, 0x2100000e))
    {
        if (WorkModule(0x6, 0x1000003e) <= 0)
        {
            WorkModule(0x2710, 0x2100000e);
        }
    }
    if (WorkModule(0x10, 0x20000076) && !LinkModule(0x2, 0x7) && global9 > 1.0f)
    {
        WorkModule(0x2711, 0x20000076);
        var0 = WorkModuleF(0, 0x100000d);
        var1 = WorkModule(0x6, 0x1100000f);
        if (var1 != 0xffffffff)
        {
            func_22(var1, 0, var0);
            printf("sub_ftStatusUniqProcessDamage_execNormalDamageCommon motion kind: %d rate: %f", var1, var0);
        }
        else
        {
            MotionModule(0x4, var0);
            printf("sub_ftStatusUniqProcessDamage_execNormalDamageCommon motion rate: %f", var0);
        }
    }
    WorkModule(0x9, 0x11000004);
    WorkModule(0xf, 0x11000006);
    WorkModule(0xf, 0x11000007);
    if (WorkModule(0x10, 0x2000005a))
    {
        if (KineticModuleF(0x2, 0xffffffff) <= WorkModuleF(0, 0x1f))
        {
            func_2200(0x1);
        }
    }
}

void func_869()
{
    func_873();
}

void func_870(int arg0)
{
    int var1;
    var1 = global4;
    if (var1 == 0x127)
    {
        var1 = 0x47;
    }
    else if (var1 == 0x13a)
    {
        var1 = 0x47;
    }
    else if (var1 == 0x13d)
    {
        var1 = 0x46;
    }
    if (var1 == 0x48)
    {
        func_890(arg0);
    }
    else if (var1 == 0x47)
    {
        func_883(arg0);
    }
    else if (var1 == 0x46)
    {
        func_882(arg0);
    }
    else
    {
        func_867(arg0);
    }
}

void func_871()
{
    int var0;
    var0 = global4;
    if (var0 == 0x127)
    {
        var0 = 0x47;
    }
    else if (var0 == 0x13a)
    {
        var0 = 0x47;
    }
    if (var0 == 0x48)
    {
        func_891();
    }
    else if (var0 == 0x47)
    {
        func_887();
    }
    else
    {
        func_869();
    }
}

void func_872()
{
    int var0;
    var0 = global4;
    if (var0 == 0x127)
    {
        var0 = 0x47;
    }
    else if (var0 == 0x13a)
    {
        var0 = 0x47;
    }
    if (var0 == 0x48)
    {
        func_881();
    }
    else if (var0 == 0x47)
    {
        func_881();
    }
    else
    {
        func_865();
    }
}

void func_873()
{
    int var0;
    var0 = global4;
    if (var0 == 0x127)
    {
        var0 = 0x47;
    }
    else if (var0 == 0x13a)
    {
        var0 = 0x47;
    }
    if (var0 == 0x48)
    {
        func_884();
    }
    else if (var0 == 0x47)
    {
        func_884();
    }
    else
    {
        func_868();
    }
}

int func_874(int arg0)
{
    int var1;
    if (global4 == 0x127)
    {
        return 0x2e;
    }
    var1 = WorkModule(0x6, 0x10000064);
    if (var1 != 0xffffffff)
    {
        return var1;
    }
    if (arg0 == 0)
    {
        return 0xd1;
    }
    else if (arg0 == 0x1)
    {
        return 0xd0;
    }
    else if (arg0 == 0x2)
    {
        return 0xcf;
    }
    return 0xd0;
}

void func_875()
{
    float var0;
    int var1;
    int var2;
    var0 = DamageModuleF(0x9);
    if (var0 > BattleObjectParamFloat(0, 0x200001f) && var0 < BattleObjectParamFloat(0, 0x2000020))
    {
        return 0xd2;
    }
    else if (DamageModule(0xd) == 0x1)
    {
        return 0xfe;
    }
    else
    {
        var1 = DamageModule(0x3);
        var2 = func_874(var1);
        if (var2 == MotionModule(0x7))
        {
            var1 += randi(0, 0x2) + 0x1;
            if (var1 >= 0x3)
            {
                var1 -= 0x3;
            }
            var2 = func_874(var1);
        }
        return var2;
    }
}

int func_876(float arg0, int arg1, int arg2)
{
    int var3;
    int var4;
    float var5;
    var3 = 0;
    if (arg0 >= WorkModuleF(0, arg1) && StopModule(0x1) == 0 && SlowModule(0x2) == 0)
    {
        var3 = 0x1;
        if (arg2 != 0x11000010)
        {
            var4 = WorkModule(0x6, arg2);
            var5 = WorkModuleF(0, 0x100000a);
            if (var4 < WorkModule(0x6, 0x12000108) || var5 < WorkModuleF(0, 0x2000109))
            {
                var3 = 0;
            }
            WorkModule(0x9, arg2);
        }
    }
    else if (arg2 != 0x11000010)
    {
        WorkModule(0x7, 0, arg2);
    }
    return var3;
}

int func_877(int arg0, int arg1, int arg2, int arg3, int arg4)
{
    int var5;
    int var6;
    float var7;
    float var8;
    var5 = WorkModule(0x6, arg1);
    if (arg0 == 0)
    {
        if (var5 != 0)
        {
            EffectModule(0x6, var5, 0x12);
            WorkModule(0x7, 0, arg1);
        }
    }
    else
    {
        if (var5 != 0 && arg4 == 0x1)
        {
            EffectModule(0x6, var5, 0);
            var5 = 0;
        }
        if (var5 == 0)
        {
            if (global4 == 0x48)
            {
                var6 = WorkModule(0x6, 0x1300006d);
                var7 = WorkModuleF(0, 0x300006e);
                var8 = WorkModuleF(0, 0x300006f);
            }
            else
            {
                var6 = WorkModule(0x6, 0x1300006a);
                var7 = WorkModuleF(0, 0x300006b);
                var8 = WorkModuleF(0, 0x300006c);
            }
            var5 = EffectModule(0xb, arg2, var6, var7, var8, 0, 0, 0, 0, 1.0f, 0x1, 0, 0, arg3);
            WorkModule(0x7, var5, arg1);
        }
        return var5;
    }
    return 0;
}

void func_878()
{
    float var0;
    int var1;
    int var2;
    int var3;
    int var4;
    int var5;
    int var6;
    float var7;
    float var8;
    float var9;
    if (WorkModule(0x10, 0x21000016) == 0)
    {
        var0 = KineticModuleF(0x3, 0x4);
        var1 = WorkModule(0x6, 0x10000065);
        var2 = 0;
        if (var1 != WorkModule(0x6, 0x1100000b))
        {
            var2 = 0x1;
        }
        var3 = func_876(var0, 0x2000106, 0x11000010);
        func_877(var3, 0x11000002, 0x100000b, 0xffffffff, 0);
        var4 = func_876(var0, 0x2000107, 0x1100000a);
        var5 = func_877(var4, 0x11000008, 0x1000094, var1, var2);
        var6 = func_877(var4, 0x11000009, 0x1000095 + var1, 0xffffffff, var2);
        if (var5 != 0 || var6 != 0)
        {
            var7 = KineticModuleF(0, 0xffffffff);
            var8 = KineticModuleF(0x1, 0xffffffff);
            var9 = MathF(0x1, var8, var7) * (float)0xb4 / M_PI;
            if (var5 != 0)
            {
                EffectModule(0x18, var5, 0, 90.0f, var9);
            }
            if (var6 != 0)
            {
                EffectModule(0x18, var6, 0, 90.0f, var9);
            }
            WorkModule(0x7, var1, 0x1100000b);
        }
        else
        {
            WorkModule(0x7, 0xffffffff, 0x1100000b);
        }
    }
}

void func_879()
{
    int var0;
    var0 = WorkModule(0x6, 0x11000002);
    if (var0 != 0)
    {
        EffectModule(0x32, var0, 0);
    }
    var0 = WorkModule(0x6, 0x11000008);
    if (var0 != 0)
    {
        EffectModule(0x32, var0, 0x12);
    }
    var0 = WorkModule(0x6, 0x11000009);
    if (var0 != 0)
    {
        EffectModule(0x32, var0, 0x12);
    }
}

void func_880()
{
    CameraModule(0x4);
}

void func_881()
{
    func_865();
    GroundModule(0x2712, 0x1);
}

void func_882(int arg0)
{
    int var1;
    int var2;
    float var3;
    var1 = func_864();
    if (WorkModule(0x10, 0x20000076))
    {
        WorkModule(0x7, 0xffffffff, 0x1100000f);
    }
    if (global5 == 0x4c && arg0 == 0 && StopModule(0) == 0x1)
    {
        WorkModule(0x7, var1, 0x1100000d);
    }
    else if (WorkModule(0x10, 0x2100001b) == 0x1 && arg0 == 0 && StopModule(0) == 0x1)
    {
        WorkModule(0x7, var1, 0x1100000d);
        if (FighterUtil(0) == 0x1)
        {
            var1 = 0xd8;
        }
        else
        {
            var1 = 0xe2;
        }
        var2 = 0;
        if (WorkModule(0x10, 0x20000076))
        {
            if (global1 == 0x8)
            {
                var2 = 0x1;
            }
        }
        if (var2 == 0x1)
        {
            func_22(var1, 1.0f, 1.0f);
        }
        else
        {
            func_22(var1, 0, 1.0f);
        }
    }
    else
    {
        WorkModule(0, 0 + 0, 0x1000007);
        var3 = (float)WorkModule(0x6, 0x120000f9);
        if (WorkModule(0x10, 0x20000076) && global19 == 0)
        {
            WorkModule(0x7, var1, 0x1100000f);
            var1 = 0xc4;
            WorkModule(0x2710, 0x20000077);
        }
        func_29(var1, 0, 1.0f, var3);
    }
    func_872();
    if (WorkModule(0x10, 0x20000076))
    {
        WorkModule(0x7, 0xffffffff, 0x1100000d);
    }
    func_866(var1);
}

void func_883(int arg0)
{
    int var1;
    int var2;
    float var3;
    var1 = func_875();
    func_872();
    if (WorkModule(0x10, 0x20000076))
    {
        WorkModule(0x7, 0xffffffff, 0x1100000f);
    }
    if (global5 == 0x4c && arg0 == 0 && StopModule(0) == 0x1)
    {
        WorkModule(0x7, var1, 0x1100000d);
        if (WorkModule(0x10, 0x20000076) && global19 == 0)
        {
            WorkModule(0x2710, 0x20000077);
        }
        WorkModule(0, 1.0f + 0, 0x100000d);
    }
    else if (WorkModule(0x10, 0x2100001b) == 0x1 && arg0 == 0 && StopModule(0) == 0x1)
    {
        WorkModule(0x7, var1, 0x1100000d);
        if (FighterUtil(0) == 0x1)
        {
            var1 = 0xd8;
        }
        else
        {
            var1 = 0xe2;
        }
        var2 = 0;
        if (WorkModule(0x10, 0x20000076))
        {
            if (global1 == 0x8)
            {
                var2 = 0x1;
            }
        }
        if (var2 == 0x1)
        {
            func_22(var1, 1.0f, 1.0f);
        }
        else
        {
            func_22(var1, 0, 1.0f);
        }
        WorkModule(0, 1.0f + 0, 0x100000d);
    }
    else
    {
        WorkModule(0, 0 + 0, 0x1000007);
        var3 = (float)WorkModule(0x6, 0x120000f9);
        if (WorkModule(0x10, 0x20000076) && global19 == 0)
        {
            WorkModule(0x7, var1, 0x1100000f);
            var1 = 0xc4;
            WorkModule(0x2710, 0x20000077);
        }
        func_29(var1, 0, 1.0f, var3);
        func_866(var1);
    }
    if (WorkModule(0x10, 0x20000076))
    {
        WorkModule(0x7, 0xffffffff, 0x1100000d);
        if (global19 == 0)
        {
            WorkModule(0x2710, 0x20000077);
        }
        MotionModule(0x4, WorkModuleF(0, 0x20001ec));
    }
    func_880();
}

void func_884()
{
    func_868();
    func_878();
    FighterUtil(0x1);
    if (WorkModule(0x10, 0x21000013) == 0)
    {
        WorkModule(0x2710, 0x21000013);
        if (global18 == 0x2 && 0x1)
        {
            func_885();
        }
    }
    func_886();
    if (StopModule(0x1) == 0 && SlowModule(0x2) == 0)
    {
        if (func_888() != 0)
        {
            return 0x1;
        }
    }
}

void func_885()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    float var7;
    float var8;
    float var9;
    float var10;
    float var11;
    float var12;
    float var13;
    float var14;
    float var15;
    float var16;
    var0 = global48;
    var1 = global32;
    if (var0 != 0 || var1 != 0)
    {
        if (KineticModule(0x4, 0x4) == 0)
        {
            return;
        }
        var2 = KineticModuleF(0x4, 0x4);
        var3 = KineticModuleF(0x5, 0x4);
        var4 = 0;
        var5 = KineticModuleF(0x3, 0x4);
        if (var5 < 9.999999747378752e-06f)
        {
            return;
        }
        var6 = WorkModuleF(0, 0x200011a);
        if (MathF(0x1, func_13(var3), func_13(var2)) > var6)
        {
            var7 = MathF(0x1, var3, var2);
            var8 = func_13(var3 * var0 + -var2 * var1) / var5;
            var9 = var2 * var1 - var3 * var0;
            if (var9 < 0)
            {
                var8 = -var8;
            }
            var7 += var6 * var8;
            var10 = var7 * (float)0xb4 / M_PI;
            var10 = func_13(var10);
            var11 = 25.0f;
            if (var10 <= 90.0f - var11 || var10 >= 90.0f + var11)
            {
                var12 = 1.0f;
                var13 = WorkModuleF(0, 0x200011b);
                var14 = WorkModuleF(0, 0x200011c);
                if (var1 > 0)
                {
                    var12 = (var13 - 1.0f) * var1 + 1.0f;
                }
                else if (var1 < 0)
                {
                    var12 = 1.0f - (1.0f - var14) * -var1;
                }
                if (var12 < var14)
                {
                    var12 = var14;
                }
                if (var12 > var13)
                {
                    var12 = var13;
                }
                var5 = var5 * var12;
            }
            var15 = var5 * MathF(0x4, var7);
            var16 = var5 * MathF(0x5, var7);
            KineticModule(0xd, var15, var16);
        }
    }
}

void func_886()
{
    BattleObject(0x70);
}

void func_887()
{
    func_873();
}

void func_888()
{
    int var0;
    if (FighterUtil(0x2) == 0x1)
    {
        var0 = WorkModule(0x6, 0x1000003e);
        var0 = (int)((float)var0 * WorkModuleF(0, 0x200011f));
        WorkModule(0x7, var0, 0x1000003e);
    }
}

void func_889()
{
    CameraModule(0x5);
    if (WorkModule(0x10, 0x2000005a))
    {
        func_2200(0x1);
    }
    func_861();
    func_879();
    EffectModule(0x2733, 0, 0);
}

void func_890(int arg0)
{
    int var1;
    int var2;
    float var3;
    var1 = WorkModule(0x6, 0x10000064);
    if (var1 == 0xffffffff)
    {
        var1 = 0xd3;
    }
    if (WorkModule(0x10, 0x20000076))
    {
        WorkModule(0x7, 0xffffffff, 0x1100000f);
    }
    if (global5 == 0x4c && arg0 == 0 && StopModule(0) == 0x1)
    {
        WorkModule(0x7, var1, 0x1100000d);
    }
    else if (WorkModule(0x10, 0x2100001b) == 0x1 && arg0 == 0 && StopModule(0) == 0x1)
    {
        WorkModule(0x7, var1, 0x1100000d);
        if (FighterUtil(0) == 0x1)
        {
            var1 = 0xd8;
        }
        else
        {
            var1 = 0xe2;
        }
        var2 = 0;
        if (WorkModule(0x10, 0x20000076))
        {
            if (global1 == 0x8)
            {
                var2 = 0x1;
            }
        }
        if (var2 == 0x1)
        {
            printf("1");
            func_22(var1, 1.0f, 1.0f);
        }
        else
        {
            func_22(var1, 0, 1.0f);
        }
    }
    else if (StopModule(0) == 0x1)
    {
        WorkModule(0, 0 + 0, 0x1000007);
        WorkModule(0x7, var1, 0x1100000d);
        var1 = func_875();
        var3 = (float)WorkModule(0x6, 0x120000f9);
        if (WorkModule(0x10, 0x20000076) && global19 == 0)
        {
            WorkModule(0x7, var1, 0x1100000f);
            var1 = 0xc4;
            WorkModule(0x2710, 0x20000077);
        }
        func_29(var1, 0, 1.0f, var3);
    }
    else
    {
        func_22(var1, 0, 1.0f);
        WorkModule(0x2710, 0x21000017);
        FighterUtil(0x5);
    }
    func_881();
    if (WorkModule(0x10, 0x20000076))
    {
        WorkModule(0x7, 0xffffffff, 0x1100000d);
        WorkModule(0, MotionModuleF(0x9) + 0, 0x100000d);
        MotionModule(0x4, WorkModuleF(0, 0x20001ec));
    }
    func_880();
}

void func_891()
{
    func_884();
    if (WorkModule(0x10, 0x21000017) == 0x1)
    {
        FighterUtil(0x5);
    }
}

void func_892()
{
    func_860();
    if (WorkModule(0x10, 0x21000017) == 0x1)
    {
        FighterUtil(0x5);
    }
}

void func_893()
{
    func_889();
    FighterUtil(0x6, 0);
    EffectModule(0x2733, 0, 0);
}

void func_894()
{
    int var0;
    float var1;
    if (global5 == 0xbc)
    {
        var0 = WorkModule(0x6, 0x12000250);
        WorkModule(0x7, var0, 0x11000002);
        var1 = WorkModuleF(0, 0x2000251);
        KineticModule(0x11, 0x1, -var1);
    }
    if (WorkModule(0x10, 0x2000000b))
    {
        var0 = WorkModule(0x6, 0x12000225);
        WorkModule(0x7, var0, 0x1000001d);
    }
    else if (WorkModule(0x10, 0x20000032))
    {
        func_895(0);
    }
    else
    {
        func_895(0x1);
    }
    ControlModule(0x2718, 0x9, 0);
}

void func_895(int arg0)
{
    if (arg0 == 0x1)
    {
        if (!(WorkModule(0x10, 0x2100000e) || WorkModule(0x10, 0x2000001b)) && WorkModule(0x6, 0x11000002) <= 0)
        {
            WorkModule(0x19, 0x1f00000a);
            WorkModule(0x19, 0x1f00000b);
            WorkModule(0x19, 0x1f00000e);
            WorkModule(0x19, 0x1f000010);
            WorkModule(0x19, 0x1f000011);
            WorkModule(0x19, 0x1f00000d);
            WorkModule(0x2710, 0x2100000e);
        }
    }
    else if (WorkModule(0x10, 0x2100000e))
    {
        WorkModule(0x1a, 0x1f00000a);
        WorkModule(0x1a, 0x1f00000b);
        WorkModule(0x1a, 0x1f00000e);
        WorkModule(0x1a, 0x1f000010);
        WorkModule(0x1a, 0x1f000011);
        WorkModule(0x1a, 0x1f00000d);
        WorkModule(0x2711, 0x2100000e);
    }
}

void func_896()
{
    if (func_58())
    {
        return 0x1;
    }
    if (func_59())
    {
        return 0x1;
    }
    if (func_63())
    {
        return 0x1;
    }
    if (func_66())
    {
        return 0x1;
    }
    if (func_67())
    {
        return 0x1;
    }
    if (func_62())
    {
        return 0x1;
    }
}

void func_897()
{
    if (!global3)
    {
        func_899();
    }
}

void func_898()
{
    FighterUtil(0x1);
}

void func_899()
{
    if (WorkModule(0x10, 0x2000000b))
    {
        if (ControlModule(0x2710, 0) || ControlModule(0x2710, 0x1))
        {
            ControlModule(0x271b);
            func_16(0xd8, 0x1);
            return;
        }
        else
        {
            func_895(0);
        }
    }
    else if (WorkModule(0x10, 0x20000032))
    {
        if (func_1459())
        {
            return;
        }
        func_895(0);
    }
    else
    {
        FighterUtil(0x2);
        func_895(0x1);
    }
}

int func_900()
{
    StatusModule(0x5, 0x2, 0x24, 0x5, 0, 0x1, 0x1404000, 0x12, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x4, 0, 0);
    return 0;
}

void func_901()
{
    WorkModule(0x9, 0x10000043);
    WorkModule(0x16, 0x1e00000d);
    WorkModule(0x16, 0x1e000005);
    WorkModule(0x16, 0x1e000008);
    WorkModule(0x16, 0x1e000009);
    if (WorkModule(0x10, 0x21000018) == 0)
    {
        WorkModule(0x16, 0x1e000017);
        WorkModule(0x16, 0x1e000016);
        WorkModule(0x16, 0x1e000015);
        WorkModule(0x16, 0x1e000018);
        WorkModule(0x16, 0x1e000014);
        WorkModule(0x16, 0x1e000013);
    }
    else
    {
        WorkModule(0x17, 0x1e000017);
        WorkModule(0x17, 0x1e000016);
        WorkModule(0x17, 0x1e000015);
        WorkModule(0x17, 0x1e000018);
        WorkModule(0x17, 0x1e000014);
        WorkModule(0x17, 0x1e000013);
    }
    func_800();
    func_78(func_902);
}

void func_902()
{
    int var0;
    var0 = WorkModule(0x6, 0x10000064);
    if (var0 == 0xffffffff)
    {
        var0 = 0x2e;
    }
    if (WorkModule(0x15, 0x1e000005) == 0x1 && MotionModule(0x7) != var0 && MotionModule(0x2712) == 0x1)
    {
        func_22(var0, 0, 1.0f);
        if (0x2 != global1 && 0 != global1 && 0x1 != global1 && 0xc != global1 && 0x23 != global1 && 0xe != global1 && 0x13 != global1 && 0x18 != global1 && 0x1b != global1 && 0x1e != global1 && 0x1d != global1 && 0x21 != global1 && 0x22 != global1 && 0x26 != global1 && 0x27 != global1 && 0x28 != global1 && 0x29 != global1 && 0x2a != global1 && 0x2f != global1 && 0x30 != global1 && 0x32 != global1 && 0xf != global1 && 0xd != global1 && 0x10 != global1)
        {
            MotionModule(0x36, 0x1);
            WorkModule(0x2710, 0x20000072);
        }
    }
    if (WorkModule(0x15, 0x1e000005) == 0x1 && MotionModule(0x7) == var0 && WorkModule(0x10, 0x2100000e) == 0x1)
    {
        func_16(0x4c, 0);
        return;
    }
    if (func_805() == 0x1)
    {
        return;
    }
    if (func_807() == 0x1)
    {
        return;
    }
    if (func_808() == 0x1)
    {
        return;
    }
    if (func_806() == 0x1)
    {
        return;
    }
}

void func_903()
{
    func_782();
    WorkModule(0x2711, 0x21000018);
    if (WorkModule(0x10, 0x20000072) && 0x4c != global6)
    {
        MotionModule(0x36, 0);
        WorkModule(0x2711, 0x20000072);
    }
}

void func_904(int arg0)
{
    int var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    var1 = GroundModule(0xa);
    if (var1 != 0)
    {
        if (var1 & 0x8)
        {
            var2 = GroundModuleF(0x3, 0x8);
            var3 = GroundModuleF(0x4, 0x8);
            var4 = GroundModuleF(0x5, 0x8);
            var5 = GroundModuleF(0x6, 0x8);
        }
        else if (var1 & 0x1)
        {
            var2 = GroundModuleF(0x3, 0x1);
            var3 = GroundModuleF(0x4, 0x1);
            var4 = GroundModuleF(0x5, 0x1);
            var5 = GroundModuleF(0x6, 0x1);
        }
        else if (var1 & 0x2)
        {
            var2 = GroundModuleF(0x3, 0x2);
            var3 = GroundModuleF(0x4, 0x2);
            var4 = GroundModuleF(0x5, 0x2);
            var5 = GroundModuleF(0x6, 0x2);
        }
        else if (var1 & 0x4)
        {
            var2 = GroundModuleF(0x3, 0x4);
            var3 = GroundModuleF(0x4, 0x4);
            var4 = GroundModuleF(0x5, 0x4);
            var5 = GroundModuleF(0x6, 0x4);
        }
        var6 = MathF(0x1, -var4, var5);
        EffectModule(0x3, 0x1000008, var2, var3, GroundModuleF(0xc), 0, 0, var6, 1.0f, 0, 0xffffffff);
        if (arg0)
        {
            CameraModule(0x3, 0x3, var2, var3, 0);
        }
    }
}

void func_905()
{
    float var0;
    int var1;
    var0 = (float)WorkModule(0x6, 0x1000003e);
    var1 = (int)(var0 * WorkModuleF(0, 0x2000112));
    func_781();
    WorkModule(0x7, var1, 0x1000003e);
    WorkModule(0x2710, 0x2000005c);
    WorkModule(0x7, 0, 0x1000003f);
    GroundModule(0x2712, 0x1);
}

void func_906()
{
    float var0;
    float var1;
    float var2;
    int var3;
    int var4;
    int var5;
    var0 = KineticModuleF(0, 0x2);
    var1 = KineticModuleF(0x1, 0x2);
    func_905();
    if (GroundModule(0x2722, 0x4) == 0x1)
    {
        var2 = -1.0f;
    }
    else
    {
        var2 = 1.0f;
    }
    if (PostureModuleF(0) * var2 > 0)
    {
        var3 = 0xfe;
        if (func_13(var0) > 3.0f)
        {
            if (MathF(0x6) < 0.30000001192092896f)
            {
                var4 = WorkModule(0x6, 0x10000064);
                if (var4 != 0xffffffff)
                {
                    var3 = var4;
                }
                else
                {
                    var3 = 0x2e;
                }
            }
        }
        func_22(var3, 0, 1.0f);
        if (var3 == 0xfe)
        {
            FighterUtil(0x3, var2, var2, 1.0f, 0x1);
        }
        else
        {
            PostureModule(0, var2);
            PostureModule(0x2);
        }
    }
    else
    {
        GroundModule(0x2717, 0xb, 0x1);
        func_22(0xd0, 0, 1.0f);
    }
    WorkModule(0, WorkModuleF(0, 0x2000110) + 0, 0x100000e);
    if (var2 == -1.0f)
    {
        var5 = 0x1;
    }
    else
    {
        var5 = 0x2;
    }
    WorkModule(0x7, var5, 0x11000001);
    HitModule(0x2, WorkModule(0x6, 0x1200010c));
    func_904(0x1);
    ControlModule(0x2718, 0x8, 0);
    if (WorkModule(0x10, 0x21000015))
    {
        WorkModule(0, MotionModuleF(0x9) + 0, 0x100000c);
        MotionModule(0x4, 0);
    }
}

void func_907()
{
    float var0;
    int var1;
    func_884();
    var0 = WorkModuleF(0, 0x100000e);
    if (var0 > 0)
    {
        var0 -= 1.0f;
        WorkModule(0, var0 + 0, 0x100000e);
    }
    if (WorkModule(0x10, 0x21000015))
    {
        var1 = WorkModule(0x6, 0x1100000c);
        if (var1 > 0)
        {
            var1--;
            WorkModule(0x7, var1, 0x1100000c);
        }
        if (var1 <= 0)
        {
            func_782();
        }
    }
}

int func_908()
{
    StatusModule(0x5, 0x2, 0x25, 0x5, 0, 0x1, 0x1404000, 0x12, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x4, 0, 0);
    return 0;
}

void func_909()
{
    float var0;
    float var1;
    var0 = KineticModuleF(0, 0x2);
    func_905();
    func_22(0x100, 0, 1.0f);
    var1 = PostureModuleF(0);
    FighterUtil(0x4, var1, 0x1);
    WorkModule(0, WorkModuleF(0, 0x2000110) + 0, 0x100000e);
    WorkModule(0x7, 0x3, 0x11000001);
    WorkModule(0x7, 0, 0x10000043);
    HitModule(0x2, WorkModule(0x6, 0x1200010c));
    func_904(0x1);
    ControlModule(0x2718, 0x8, 0);
    if (WorkModule(0x10, 0x21000015))
    {
        WorkModule(0, MotionModuleF(0x9) + 0, 0x100000c);
        MotionModule(0x4, 0);
    }
}

void func_910()
{
    WorkModule(0x9, 0x10000043);
    WorkModule(0x16, 0x1e00000d);
    WorkModule(0x16, 0x1e000005);
    WorkModule(0x16, 0x1e000006);
    WorkModule(0x16, 0x1e000007);
    WorkModule(0x16, 0x1e000009);
    if (WorkModule(0x10, 0x21000018) == 0)
    {
        WorkModule(0x16, 0x1e000017);
        WorkModule(0x16, 0x1e000016);
        WorkModule(0x16, 0x1e000015);
        WorkModule(0x16, 0x1e000018);
        WorkModule(0x16, 0x1e000014);
        WorkModule(0x16, 0x1e000013);
    }
    else
    {
        WorkModule(0x17, 0x1e000017);
        WorkModule(0x17, 0x1e000016);
        WorkModule(0x17, 0x1e000015);
        WorkModule(0x17, 0x1e000018);
        WorkModule(0x17, 0x1e000014);
        WorkModule(0x17, 0x1e000013);
    }
    func_800();
    func_78(func_911);
}

void func_911()
{
    int var0;
    var0 = WorkModule(0x6, 0x10000064);
    if (var0 == 0xffffffff)
    {
        var0 = 0x2e;
    }
    if (WorkModule(0x15, 0x1e000005) == 0x1 && MotionModule(0x7) != var0 && MotionModule(0x2712) == 0x1)
    {
        func_22(var0, 0, 1.0f);
    }
    if (WorkModule(0x15, 0x1e000005) == 0x1 && MotionModule(0x7) == var0 && WorkModule(0x10, 0x2100000e) == 0x1)
    {
        func_16(0x4c, 0);
        return;
    }
    if (func_805() == 0x1)
    {
        return;
    }
    if (func_808() == 0x1)
    {
        return;
    }
    if (func_806() == 0x1)
    {
        return;
    }
}

void func_912()
{
    func_782();
    WorkModule(0x2711, 0x21000018);
}

int func_913()
{
    StatusModule(0x5, 0x2, 0x55, 0x5, 0, 0x1, 0x1404000, 0x12, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x4, 0, 0);
    return 0;
}

void func_914()
{
    int var0;
    func_905();
    if (FighterUtil(0) == 0x1)
    {
        var0 = 0xd5;
    }
    else
    {
        var0 = 0xdf;
    }
    func_22(var0, 0, 1.0f);
    WorkModule(0, WorkModuleF(0, 0x2000110) + 0, 0x100000e);
    WorkModule(0x7, 0x4, 0x11000001);
    WorkModule(0x7, 0, 0x10000043);
    HitModule(0x2, WorkModule(0x6, 0x1200010c));
    ControlModule(0x2718, 0x8, 0);
}

void func_915()
{
    WorkModule(0x9, 0x10000043);
    WorkModule(0x16, 0x1e00000d);
    WorkModule(0x16, 0x1e000005);
    WorkModule(0x16, 0x1e000006);
    WorkModule(0x16, 0x1e000007);
    WorkModule(0x16, 0x1e000008);
    if (WorkModule(0x10, 0x21000018) == 0)
    {
        WorkModule(0x16, 0x1e000017);
        WorkModule(0x16, 0x1e000016);
        WorkModule(0x16, 0x1e000015);
        WorkModule(0x16, 0x1e000018);
        WorkModule(0x16, 0x1e000014);
        WorkModule(0x16, 0x1e000013);
    }
    else
    {
        WorkModule(0x17, 0x1e000017);
        WorkModule(0x17, 0x1e000016);
        WorkModule(0x17, 0x1e000015);
        WorkModule(0x17, 0x1e000018);
        WorkModule(0x17, 0x1e000014);
        WorkModule(0x17, 0x1e000013);
    }
    WorkModule(0x2711, 0x20000003);
    func_800();
    func_78(func_916);
}

void func_916()
{
    float var0;
    float var1;
    float var2;
    int var3;
    if (WorkModule(0x15, 0x1e000005) == 0x1 && MotionModule(0x2712) == 0x1 && WorkModule(0x10, 0x2100000e) == 0x1)
    {
        func_16(0x4c, 0);
        return;
    }
    if (func_805() == 0x1)
    {
        return;
    }
    if (func_806() == 0x1)
    {
        return;
    }
    if (func_807() == 0x1)
    {
        return;
    }
    if (global9 == 1.0f)
    {
        var0 = KineticModuleF(0x4, 0x4);
        var1 = KineticModuleF(0x5, 0x4);
        var2 = MathF(0x1, var1, var0);
        if (var2 > BattleObjectParamFloat(0, 0x200001f) && var2 < BattleObjectParamFloat(0, 0x2000020))
        {
            var3 = 0xd2;
        }
        else
        {
            var3 = 0xd0;
        }
        func_22(var3, 0, 1.0f);
        func_866(var3);
    }
}

void func_917()
{
    WorkModule(0x2711, 0x21000018);
}

void func_918()
{
    int var0;
    int var1;
    int var2;
    float var3;
    float var4;
    float var5;
    float var6;
    float var7;
    int var8;
    var0 = DamageModule(0);
    var1 = DamageModule(0x3);
    if (var0 == 0x2)
    {
        if (var1 == 0x2)
        {
            var2 = 0xc5;
        }
        else if (var1 == 0x1)
        {
            var2 = 0xc8;
        }
        else
        {
            var2 = 0xcb;
        }
    }
    else if (var0 == 0x1)
    {
        if (var1 == 0x2)
        {
            var2 = 0xc4;
        }
        else if (var1 == 0x1)
        {
            var2 = 0xc7;
        }
        else
        {
            var2 = 0xca;
        }
    }
    else if (var1 == 0x2)
    {
        var2 = 0xc3;
    }
    else if (var1 == 0x1)
    {
        var2 = 0xc6;
    }
    else
    {
        var2 = 0xc9;
    }
    func_22(var2, 0, 1.0f);
    var3 = 0;
    if (GroundModule(0x2722, 0x8))
    {
        var4 = GroundModuleF(0x5, 0x8);
        var5 = GroundModuleF(0x6, 0x8);
        var3 = MathF(0x1, var4, var5);
    }
    var6 = GroundModuleF(0x3, 0x8);
    var7 = GroundModuleF(0x4, 0x8);
    var8 = EffectModule(0x3, 0x1000044, var6, var7, GroundModuleF(0xc), 0, 0, -var3, 1.0f, 0, 0xffffffff);
    WorkModule(0x7, var8, 0x11000003);
}

void func_919()
{
    int var0;
    var0 = WorkModule(0x6, 0x11000003);
    EffectModule(0x8, var0, 0x1, 0x1);
    func_861();
}

int func_920()
{
    StatusModule(0x5, 0, 0xffffffff, 0x1, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0x2, 0, 0x1, 0, 0, 0x10000, 0, 0);
    return 0;
}

void func_921()
{
    func_960();
    WorkModule(0x2711, 0x20000003);
    func_78(func_922);
}

void func_922()
{
    func_961();
    if (GroundModule(0x2722, 0x8))
    {
        KineticModule(0, 0x6);
    }
}

void func_923()
{
    if (global6 != 0xc2)
    {
        WorkModule(0x2711, 0x20000066);
    }
}

int func_924()
{
    StatusModule(0x5, 0, 0xffffffff, 0x1, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0x2, 0, 0x1, 0, 0, 0x10000, 0, 0);
    return 0;
}

void func_925()
{
    func_921();
    func_78(func_926);
}

void func_926()
{
    func_922();
}

void func_927()
{
    
}

int func_928()
{
    StatusModule(0x5, 0, 0xf, 0x1, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0x2, 0, 0x1, 0, 0, 0x10000, 0, 0);
    return 0;
}

void func_929()
{
    func_960();
    func_78(func_930);
}

void func_930()
{
    func_961();
}

void func_931()
{
    
}

int func_932()
{
    StatusModule(0x5, 0, 0xf, 0x1, 0, 0x1, 2.0f, 0, 0x8000, 0);
    StatusModule(0x2713, 0x1, 0x2, 0, 0x1, 0, 0, 0x10000, 0, 0);
    return 0;
}

void func_933()
{
    WorkModule(0, WorkModuleF(0, 0x200005b), 0x100000f);
    if (global5 == 0x52)
    {
        WorkModule(0x2710, 0x21000021);
    }
    else
    {
        WorkModule(0x2711, 0x21000021);
    }
    if (global5 == 0x80)
    {
        func_22(0xe0, 0, 1.0f);
    }
    else if (WorkModule(0x2712, 0x2100001e))
    {
        func_22(0xd6, 0, 1.0f);
    }
    else
    {
        func_22(0xe0, 0, 1.0f);
    }
    func_962();
    func_78(func_934);
}

void func_934()
{
    if (func_963())
    {
        return;
    }
}

void func_935()
{
    
}

int func_936()
{
    StatusModule(0x5, 0, 0xf, 0x1, 0, 0x1, 2.0f, 0, 0x8000, 0);
    StatusModule(0x2713, 0x1, 0x2, 0, 0x1, 0, 0, 0x10000, 0, 0);
    return 0;
}

void func_937()
{
    if (WorkModule(0x2712, 0x2100001e))
    {
        func_22(0xd6, 0, 1.0f);
    }
    else
    {
        func_22(0xe0, 0, 1.0f);
    }
    func_962();
    func_78(func_938);
}

void func_938()
{
    if (func_963())
    {
        return;
    }
}

void func_939()
{
    
}

int func_940()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 2.0f, 0, 0x8000, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_941()
{
    if (WorkModule(0x2712, 0x2100001e))
    {
        func_22(0xda, 0, 1.0f);
    }
    else
    {
        func_22(0xe4, 0, 1.0f);
    }
    func_78(func_942);
}

void func_942()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return 0x1;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return 0x1;
        }
    }
}

void func_943()
{
    
}

int func_944()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 2.0f, 0, 0x8000, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0x80000, 0, 0x1);
    return 0;
}

void func_945()
{
    int var0;
    var0 = ControlModule(0x1b);
    if (var0 != 0)
    {
        if (var0 == 0x1)
        {
            if (WorkModule(0x2712, 0x2100001e))
            {
                func_22(0xdc, 0, 1.0f);
            }
            else
            {
                func_22(0xe6, 0, 1.0f);
            }
        }
        else if (WorkModule(0x2712, 0x2100001e))
        {
            func_22(0xdd, 0, 1.0f);
        }
        else
        {
            func_22(0xe7, 0, 1.0f);
        }
    }
    else if (func_88() >= (float)0)
    {
        if (WorkModule(0x2712, 0x2100001e))
        {
            func_22(0xdc, 0, 1.0f);
        }
        else
        {
            func_22(0xe6, 0, 1.0f);
        }
    }
    else if (WorkModule(0x2712, 0x2100001e))
    {
        func_22(0xdd, 0, 1.0f);
    }
    else
    {
        func_22(0xe7, 0, 1.0f);
    }
    ControlModule(0x1c);
    func_78(func_946);
}

void func_946()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return 0x1;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return 0x1;
        }
    }
}

void func_947()
{
    
}

int func_948()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 2.0f, 0, 0x8000, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0x452, 0, 0x20, 0x400);
    return 0;
}

void func_949()
{
    if (WorkModule(0x2712, 0x2100001e))
    {
        func_22(0xdb, 0, 1.0f);
    }
    else
    {
        func_22(0xe5, 0, 1.0f);
    }
    func_78(func_950);
}

void func_950()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return 0x1;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return 0x1;
        }
    }
}

void func_951()
{
    
}

int func_952()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0x4, 0x1, -2.0f, 0, 0x8000, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0x10004, 0, 0);
    return 0;
}

void func_953()
{
    WorkModule(0x16, 0x1e000005);
    WorkModule(0x16, 0x1e000002);
    WorkModule(0x16, 0x1e00000f);
    WorkModule(0x16, 0x1e00000e);
    if (WorkModule(0x2712, 0x2100001f))
    {
        if (WorkModule(0x2712, 0x2100001e))
        {
            func_22(0xd8, 0, 1.0f);
        }
        else
        {
            func_22(0xe2, 0, 1.0f);
        }
    }
    else if (WorkModule(0x2712, 0x2100001e))
    {
        func_22(0xd7, 0, 1.0f);
    }
    else
    {
        func_22(0xe1, 0, 1.0f);
    }
    if (!StopModule(0x1))
    {
        func_965();
    }
    global16 = func_965;
    func_966();
    PhysicsModule(0x9);
    func_78(func_954);
}

void func_954()
{
    if (!WorkModule(0x2712, 0x21000022))
    {
        if (WorkModule(0x15, 0x1e000005))
        {
            if (global18 == 0x2)
            {
                func_16(0x4c, 0);
                return;
            }
        }
    }
    if (WorkModule(0x15, 0x1e000002))
    {
        if (MotionModule(0x2712))
        {
            if (global18 == 0x2)
            {
                func_16(0x4c, 0);
                return;
            }
        }
    }
    if (WorkModule(0x15, 0x1e00000f))
    {
        if (global18 == 0)
        {
            if (MotionModule(0x2712))
            {
                if (!WorkModule(0x2712, 0x2000001b))
                {
                    if (WorkModuleF(0, 0x100000f) <= (float)0)
                    {
                        func_16(0x54, 0);
                        return;
                    }
                }
            }
        }
    }
    if (WorkModule(0x15, 0x1e00000e))
    {
        if (global18 == 0)
        {
            if (MotionModule(0x2712))
            {
                func_16(0x51, 0);
                return;
            }
        }
    }
    func_967();
    if (StatusModule(0x6) == 0x1 || global18 == 0 && global19 != 0 || global18 == 0x2 && global19 == 0)
    {
        if (StatusModule(0x6) != 0x1)
        {
            WorkModule(0x2710, 0x21000023);
        }
        if (global18 == 0)
        {
            GroundModule(0x2710, 0x1);
            if (WorkModule(0x2712, 0x21000023))
            {
                KineticModule(0, 0x6);
            }
        }
        else
        {
            GroundModule(0x2710, 0x5);
            if (WorkModule(0x2712, 0x21000023))
            {
                KineticModule(0, 0xa);
            }
        }
    }
}

void func_955()
{
    
}

int func_956()
{
    StatusModule(0x5, 0x2, 0x24, 0x5, 0x4, 0x1, -2.0f, 0x2, 0x8000, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0x4, 0, 0);
    return 0;
}

void func_957()
{
    WorkModule(0x16, 0x1e000005);
    WorkModule(0x16, 0x1e00000d);
    if (!StopModule(0x1))
    {
        func_550();
    }
    global16 = func_550;
    func_78(func_958);
}

void func_958()
{
    if (WorkModule(0x15, 0x1e000005))
    {
        if (MotionModule(0x2712))
        {
            func_16(0x4c, 0);
            return;
        }
    }
    if (WorkModule(0x15, 0x1e00000d))
    {
        if (global18 == 0)
        {
            func_16(0x4f, 0);
            return;
        }
    }
}

void func_959()
{
    
}

void func_960()
{
    func_22(WorkModule(0x6, 0x11000010), 0, 1.0f);
    func_966();
    PhysicsModule(0x9);
}

void func_961()
{
    if (!GroundModule(0x2722, 0x8))
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (MotionModule(0x2712))
    {
        if (global38 & 0x1 || global38 & 0x4)
        {
            if (global18 == 0)
            {
                func_16(0x56, 0x1);
                return 0x1;
            }
        }
    }
    if (MotionModule(0x2712))
    {
        if (func_84() >= WorkModuleF(0, 0x200005d))
        {
            if (ControlModule(0x271d))
            {
                if (global18 == 0)
                {
                    func_16(0x55, 0x1);
                    return 0x1;
                }
            }
        }
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0x50, 0);
            return 0x1;
        }
    }
    func_967();
}

void func_962()
{
    if (!WorkModule(0x2712, 0x2000001b))
    {
        if (AreaModule(0x2713, 0x4))
        {
            AreaModule(0x2711, 0x4, 0x1);
        }
        if (!StopModule(0x1))
        {
            func_964();
        }
        global16 = func_964;
    }
    PhysicsModule(0x9);
}

void func_963()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (!WorkModule(0x2712, 0x2000001b))
    {
        if (ItemModule(0) && ItemModule(0x22) && ItemModule(0x2, 0x2000) && global38 & 0x1 && global18 == 0)
        {
            func_16(0x52, 0x1);
            return 0x1;
        }
        if (global38 & 0x1 || global38 & 0x4)
        {
            if (global18 == 0)
            {
                func_16(0x56, 0x1);
                return 0x1;
            }
        }
        if (global31 & 0x80)
        {
            if (global18 == 0)
            {
                func_16(0x55, 0x1);
                return 0x1;
            }
        }
        if (global31 & 0x100)
        {
            if (global18 == 0)
            {
                func_16(0x54, 0x1);
                return 0x1;
            }
        }
        if (WorkModuleF(0, 0x100000f) <= (float)0)
        {
            if (global18 == 0)
            {
                func_16(0x54, 0);
                return 0x1;
            }
        }
    }
}

void func_964()
{
    WorkModule(0x3, 1.0f, 0x100000f);
}

void func_965()
{
    func_964();
}

void func_966()
{
    WorkModule(0x16, 0x1e000006);
    WorkModule(0x16, 0x1e000007);
    WorkModule(0x16, 0x1e000011);
    WorkModule(0x16, 0x1e000012);
}

void func_967()
{
    if (WorkModule(0x15, 0x1e000006))
    {
        if (global18 == 0x2)
        {
            if (GroundModule(0x2722, 0x2))
            {
                if (-func_92() > WorkModuleF(0, 0x200010b))
                {
                    if (WorkModule(0x6, 0x11000001) != 0x2)
                    {
                        func_16(0x49, 0);
                        return;
                    }
                }
            }
        }
    }
    if (WorkModule(0x15, 0x1e000007))
    {
        if (global18 == 0x2)
        {
            if (GroundModule(0x2722, 0x4))
            {
                if (func_92() > WorkModuleF(0, 0x200010b))
                {
                    if (WorkModule(0x6, 0x11000001) != 0x1)
                    {
                        func_16(0x49, 0);
                        return;
                    }
                }
            }
        }
    }
    if (WorkModule(0x15, 0x1e000011))
    {
        if (global18 == 0)
        {
            if (GroundModule(0x2722, 0x2))
            {
                if (-func_92() > WorkModuleF(0, 0x200010b))
                {
                    if (WorkModule(0x6, 0x11000001) != 0x2)
                    {
                        func_16(0x58, 0);
                        return;
                    }
                }
            }
        }
    }
    if (WorkModule(0x15, 0x1e000012))
    {
        if (global18 == 0)
        {
            if (GroundModule(0x2722, 0x4))
            {
                if (func_92() > WorkModuleF(0, 0x200010b))
                {
                    if (WorkModule(0x6, 0x11000001) != 0x1)
                    {
                        func_16(0x58, 0);
                        return;
                    }
                }
            }
        }
    }
}

void func_968()
{
    int var0;
    var0 = 0;
    if (FighterUtil(0))
    {
        var0 = 0xd5;
        WorkModule(0x11, 0x2100001e);
    }
    else
    {
        var0 = 0xdf;
        WorkModule(0x12, 0x2100001e);
    }
    WorkModule(0x7, var0, 0x11000010);
}

int func_969()
{
    StatusModule(0x5, 0xffffffff, 0xf, 0x1, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0x2, 0, 0x1, 0, 0, 0x8, 0, 0);
    return 0;
}

void func_970()
{
    if (GroundModule(0x2722, 0x8))
    {
        func_20(0);
    }
    WorkModule(0, WorkModuleF(0, 0x200005b) + 0, 0x100000f);
    WorkModule(0x2710, 0x2100001e);
    func_22(0xe0, 0, 1.0f);
    func_962();
    func_78(func_971);
}

void func_971()
{
    if (func_963())
    {
        return;
    }
}

void func_972()
{
    
}

int func_973()
{
    StatusModule(0x5, 0, 0xf, 0x1, 0, 0x1, 2.0f, 0, 0x8000, 0);
    StatusModule(0x2713, 0x1, 0x2, 0, 0x1, 0, 0, 0x10000, 0, 0);
    return 0;
}

void func_974()
{
    if (AreaModule(0x2713, 0x4))
    {
        AreaModule(0x2711, 0x4, 0x1);
    }
    if (WorkModule(0x2712, 0x2100001e))
    {
        func_22(0xd9, 0, 1.0f);
    }
    else
    {
        func_22(0xe3, 0, 1.0f);
    }
    if (!StopModule(0x1))
    {
        func_964();
    }
    global16 = func_964;
    PhysicsModule(0x9);
    func_78(func_975);
}

void func_975()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0x50, 0);
        return;
    }
}

void func_976()
{
    
}

int func_977()
{
    if (func_548())
    {
        return 0x1;
    }
    StatusModule(0x5, 0x2, 0x13, 0x5, 0x4, 0x1, 0x82, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0x10, 0, 0);
    return 0;
}

int func_978()
{
    StatusModule(0x5, 0, func_559(), 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0, 0x10, 0, 0);
    return 0;
}

void func_979()
{
    WorkModule(0x16, 0x1e00001e);
    MotionModule(0x1, 0x2a, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_550();
    }
    global16 = func_550;
    func_78(func_980);
}

void func_980()
{
    if (func_56())
    {
        return 0x1;
    }
    if (func_549())
    {
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00001e) != 0 && global18 == 0)
    {
        func_16(0x19, 0);
        return 0x1;
    }
}

void func_981()
{
    func_983();
    func_78(func_984);
}

void func_982()
{
    func_983();
    func_78(func_987);
}

void func_983()
{
    if (func_109())
    {
        func_562();
    }
}

void func_984()
{
    func_986();
}

void func_985()
{
    if (func_109())
    {
        if (func_563() != 0)
        {
            return 0x1;
        }
    }
    else
    {
        if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
        {
            return;
        }
        if (MotionModule(0x2712) != 0)
        {
            func_16(0, 0);
            return 0x1;
        }
    }
}

void func_986()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    func_985();
}

void func_987()
{
    if (global18 == 0x2)
    {
        func_16(0x10, 0);
        return 0x1;
    }
    func_985();
}

void func_988()
{
    
}

void func_989()
{
    
}

void func_990()
{
    int var0;
    float var1;
    var0 = 0;
    if (MotionModule(0xc, 0xde) == 0x1)
    {
        var0 = 0xde;
        WorkModule(0x11, 0x2100001e);
    }
    else
    {
        var0 = 0xe8;
        WorkModule(0x12, 0x2100001e);
    }
    WorkModule(0x7, var0, 0x11000010);
    var1 = (float)MotionModule(0, var0);
    WorkModule(0, var1, 0x100000e);
}

void func_991()
{
    if (global5 != 0x4d && global5 != 0x50 && global5 != 0x57)
    {
        WorkModule(0x12, 0x2100001e);
        WorkModule(0x12, 0x2100001f);
        WorkModule(0, 0, 0x100000f);
    }
    func_865();
    if (global18 == 0)
    {
        KineticModule(0, 0x20);
    }
    else
    {
        KineticModule(0, 0x21);
        WorkModule(0x11, 0x21000022);
    }
}

void func_992()
{
    func_868();
    if (WorkModuleF(0, 0x100000f) > 0)
    {
        WorkModule(0x3, 1.0f, 0x100000f);
    }
}

void func_993()
{
    WorkModule(0x2711, 0x2000003c);
    if (global18 != 0x2)
    {
        WorkModule(0x2711, 0x20000011);
    }
}

void func_994()
{
    float var0;
    int var1;
    float var2;
    float var3;
    float var4;
    int var5;
    int var6;
    float var7;
    float var8;
    float var9;
    float var10;
    float var11;
    func_996();
    if (global4 == 0x58)
    {
        var0 = KineticModuleF(0x4);
        if (var0 < 0)
        {
            var1 = 0x1;
        }
        else
        {
            var1 = 0;
        }
        var2 = PostureModuleF(0);
        if (var1 == 0x1)
        {
            var3 = -1.0f;
        }
        else
        {
            var3 = 1.0f;
        }
        if (var2 * var3 > 0)
        {
            func_22(0xfe, 0, 1.0f);
            FighterUtil(0x3, var3, var3, 1.0f, 0);
        }
        else
        {
            GroundModule(0x2717, 0xb, 0x1);
            func_22(0xd0, 0, 1.0f);
        }
        var4 = WorkModuleF(0, 0x2000110);
        WorkModule(0, var4, 0x100000e);
        if (var1 == 0x1)
        {
            WorkModule(0x7, 0x1, 0x11000001);
        }
        else
        {
            WorkModule(0x7, 0x2, 0x11000001);
        }
        var5 = WorkModule(0x6, 0x1200010c);
        HitModule(0x2, var5);
        var6 = GroundModule(0xa);
        if (var6 != 0)
        {
            if (var6 & 0x8)
            {
                var7 = GroundModuleF(0x3, 0x8);
                var8 = GroundModuleF(0x4, 0x8);
                var9 = GroundModuleF(0x5, 0x8);
                var10 = GroundModuleF(0x6, 0x8);
            }
            else if (var6 & 0x1)
            {
                var7 = GroundModuleF(0x3, 0x1);
                var8 = GroundModuleF(0x4, 0x1);
                var9 = GroundModuleF(0x5, 0x1);
                var10 = GroundModuleF(0x6, 0x1);
            }
            else if (var6 & 0x2)
            {
                var7 = GroundModuleF(0x3, 0x2);
                var8 = GroundModuleF(0x4, 0x2);
                var9 = GroundModuleF(0x5, 0x2);
                var10 = GroundModuleF(0x6, 0x2);
            }
            else if (var6 & 0x4)
            {
                var7 = GroundModuleF(0x3, 0x4);
                var8 = GroundModuleF(0x4, 0x4);
                var9 = GroundModuleF(0x5, 0x4);
                var10 = GroundModuleF(0x6, 0x4);
            }
            var11 = MathF(0x1, -var9, var10);
            EffectModule(0x3, 0x1000008, var7, var8, GroundModuleF(0xc), 0, 0, var11, 1.0f, 0, 0xffffffff);
            CameraModule(0x3, 0x3, var7, var8, 0);
        }
        ControlModule(0x2718, 0x8, 0);
    }
}

void func_995()
{
    func_997();
    if (WorkModuleF(0, 0x100000e) > 0)
    {
        WorkModule(0x3, 1.0f, 0x100000e);
    }
}

void func_996()
{
    func_865();
}

void func_997()
{
    func_868();
}

void func_998()
{
    float var0;
    float var1;
    float var2;
    var0 = WorkModuleF(0, 0x1000007);
    var1 = WorkModuleF(0, 0x1000008);
    var1 *= func_13(var0);
    var2 = WorkModuleF(0, 0x2000004);
    if (var1 > var2)
    {
        var1 = var2;
    }
    MotionModule(0x4, var1);
}

void func_999()
{
    float var0;
    float var1;
    if (global4 == 0x8b)
    {
        var0 = sys_40(0) * WorkModuleF(0, 0x20000a6);
        func_22(0x127, 0, var0);
    }
    else if (global4 == 0x90)
    {
        KineticModule(0, 0xe);
        var1 = WorkModuleF(0, 0x300003b);
        func_762(var1, 0x128, 0x1000007, 1.0f, 0x1000008, 0);
        func_998();
    }
}

void func_1000()
{
    float var0;
    float var1;
    if (global4 == 0x90)
    {
        var0 = WorkModuleF(0, 0x1000007);
        var1 = WorkModuleF(0, 0x300003b);
        func_774(var0, var1, WorkModuleF(0, 0x3000039), WorkModuleF(0, 0x300003a), WorkModuleF(0, 0x2000002), 0x1000007, 1.0f, 0);
        func_998();
    }
}

void func_1001()
{
    if (global6 == 0x8b || global6 == 0x91 || global6 == 0x8e || global6 == 0x8f || global6 == 0x90)
    {
        
    }
    else if (ItemModule(0x4) != 0)
    {
        ItemModule(0x8);
    }
}

void func_1002()
{
    int var0;
    int var1;
    if (WorkModule(0x10, 0x21000010))
    {
        return;
    }
    if (sys_7(0x15))
    {
        if (WorkModule(0x6, 0x1000001e) == 0xffffffff)
        {
            var0 = ItemModule(0x11);
            if (var0 == 0x31)
            {
                var1 = SoundModule(0x272a, 0x1);
                printf("**** hammer %d", var1);
                WorkModule(0x7, var1, 0x1000001e);
            }
            else if (var0 == 0x30)
            {
                var1 = SoundModule(0x272a, 0x2);
                printf("**** golden hammer %d", var1);
                WorkModule(0x7, var1, 0x1000001e);
            }
        }
        WorkModule(0x2710, 0x21000010);
    }
}

void func_1003()
{
    float var0;
    int var1;
    if (global4 == 0xd4)
    {
        var0 = KineticModuleF(0, 0x1);
        WorkModule(0, var0, 0x1000006);
    }
    if (FighterUtil(0xb, global5) == 0)
    {
        ItemModule(0x1c, 0);
        WorkModule(0x7, 0, 0x11000004);
        WorkModule(0x7, 0, 0x11000003);
        WorkModule(0x12, 0x2100000e);
        VisibilityModule(0x2714);
        if (ItemModule(0x11) == 0x31)
        {
            EffectModule(0x1f, 0x14, 0);
            var1 = ItemModule(0x1e, 0);
            WorkModule(0x7, var1, 0x11000003);
            if (WorkModule(0x10, 0x2000000c) == 0)
            {
                ItemModule(0x1d, 0x1);
            }
        }
        else
        {
            EffectModule(0x1f, 0x15, 0);
            ItemModule(0x1d, 0x1);
        }
        func_1002();
        ControlModule(0x19, 0x2, 0, 0, 0x1);
    }
}

void func_1004()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    float var7;
    int var8;
    int var9;
    float var10;
    float var11;
    float var12;
    int var13;
    if (global4 == 0xd4)
    {
        var0 = sys_40(0x2);
        var1 = WorkModuleF(0, 0x3000003);
        var2 = WorkModuleF(0, 0x3000001);
        var3 = WorkModuleF(0, 0x3000002);
        var4 = WorkModuleF(0, 0x2000002);
        var5 = WorkModuleF(0, 0x1000006);
        func_774(var5, var1, var2, var3, var4, 0x1000006, var0, 0);
        var6 = sys_40(0x8);
        var7 = var1 - var6;
        var7 += 1.0f;
        printf("sub_uniq_process_hammer_exec_status $FL_hammer_speed_mul: %f", var7);
        KineticModule(0x11, 0, WorkModuleF(0, 0x1000006) * var7, 0);
    }
    var8 = ItemModule(0x11) == 0x30;
    if (var8)
    {
        var9 = WorkModule(0x6, 0x11000004);
        if (WorkModule(0x10, 0x2000000d) == 0)
        {
            if (ControlModule(0x2710, 0) || ControlModule(0x2710, 0x2) && global18 != 0)
            {
                var9 = WorkModule(0x6, 0x1200022a) - WorkModule(0x6, 0x11000006);
                var10 = PostureModuleF(0x1);
                var11 = PostureModuleF(0x2);
                var12 = PostureModuleF(0x3);
                EffectModule(0x3, 0x100000a, var10, var11, var12, 0, 0, 0, 1.0f, 0, 0xffffffff);
            }
        }
        if (global18 == 0x2)
        {
            if (var9 > 0)
            {
                var9--;
                if (var9 <= 0)
                {
                    WorkModule(0x11, 0x2000000d);
                }
            }
            if (var9 > 0)
            {
                var13 = WorkModule(0x6, 0x11000005);
                var13++;
                if (var13 > WorkModule(0x6, 0x1200022b))
                {
                    var13 = 0;
                    WorkModule(0x9, 0x11000006);
                }
                WorkModule(0x7, var13, 0x11000005);
                KineticModule(0x2719, 0x1);
                KineticModule(0x2717, 0x1);
            }
            else
            {
                KineticModule(0x2718, 0x1);
            }
        }
        else if (var9 > 0)
        {
            var9--;
        }
        WorkModule(0x7, var9, 0x11000004);
        if (WorkModule(0x10, 0x2100000e) == 0)
        {
            var13 = WorkModule(0x6, 0x1000001c);
            if (var13 < WorkModule(0x6, 0x12000229))
            {
                WorkModule(0x11, 0x2100000e);
                EffectModule(0x1f, 0x16, 0);
            }
        }
    }
}

int func_1005()
{
    func_1002();
    if (global3 == 0)
    {
        if (func_1007() != 0)
        {
            return 0x1;
        }
    }
    if (func_1008() != 0)
    {
        return 0x1;
    }
    return 0;
}

void func_1006()
{
    if (FighterUtil(0xb, global6) == 0)
    {
        if (ItemModule(0x11) == 0x31)
        {
            ItemModule(0x1d, 0x2);
            EffectModule(0x20, 0x14);
        }
        else
        {
            ItemModule(0x1d, 0x2);
            EffectModule(0x20, 0x15);
        }
        ControlModule(0x1a, 0x2, 0x1);
        EffectModule(0x2723, 0x100000b, 0, 0);
    }
}

void func_1007()
{
    int var0;
    var0 = WorkModule(0x6, 0x11000003);
    if (var0 > 0)
    {
        var0--;
        if (var0 <= 0)
        {
            WorkModule(0x11, 0x2000000c);
            ItemModule(0x1d, 0);
        }
        WorkModule(0x7, var0, 0x11000003);
    }
    if (MotionModule(0xb) == 0x1)
    {
        BattleObject(0xd, 0x2, 0x77, 0x1);
        ItemModule(0x28);
    }
}

void func_1008()
{
    
}

int func_1009()
{
    return 0x1;
}

int func_1010()
{
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3ea, 0, 0);
    BattleObject(0x8e, 0x1b);
    return 0;
}

void func_1011()
{
    int var0;
    var0 = global5;
    if (var0 != 0xda)
    {
        WorkModule(0x2711, 0x2100000d);
        WorkModule(0x2711, 0x2100000f);
        WorkModule(0x7, 0, 0x11000002);
        WorkModule(0x7, 0xce, 0x11000002);
    }
    else
    {
        
    }
}

int func_1012()
{
    if (!StatusModule(0x6))
    {
        if (global3 == 0)
        {
            if (func_1013() != 0)
            {
                return 0x1;
            }
        }
        if (func_1014() != 0)
        {
            return 0x1;
        }
    }
    return 0;
}

int func_1013()
{
    return 0;
}

int func_1014()
{
    if (LinkModule(0x2, 0))
    {
        LinkModule(0x2716, 0, 0);
    }
    BattleObject(0x27);
    func_20(0x2);
    GroundModule(0x2710, 0);
    KineticModule(0x3);
    KineticModule(0x2);
    func_1016();
    return 0;
}

void func_1015()
{
    int var0;
    if (global6 == 0xda)
    {
        var0 = func_1018();
        WorkModule(0x7, var0, 0x11000003);
        if (MotionModule(0x7) != 0xd0)
        {
            func_22(var0, 0, 1.0f);
        }
    }
    if (global6 == 0x44 || global6 == 0xda)
    {
        
    }
    else
    {
        printf("sub_uniq_process_link_final_exit capture cut");
        LinkModule(0xb);
        CaptureModule(0x5, 0);
        CaptureModule(0x1);
    }
}

void func_1016()
{
    int var0;
    var0 = func_1017();
    if (WorkModule(0x2712, 0x2100000f) == 0x1 || var0 == 0)
    {
        if (WorkModule(0x2712, 0x2100000f) == 0x1)
        {
            printf("sub_check_cancel FIGHTER_STATUS_LINK_FINAL_FLAG_ABORT");
        }
        printf("$is_link : %d", var0);
        if (global18 == 0)
        {
            printf("sub_check_cancel FIGHTER_STATUS_KIND_LANDING_LIGHT");
            func_16(0x17, 0);
            return;
        }
        else
        {
            printf("sub_check_cancel FIGHTER_STATUS_KIND_FALL");
            func_16(0xe, 0);
            return;
        }
    }
}

int func_1017()
{
    return BattleObject(0x28);
}

int func_1018()
{
    int var0;
    int var1;
    var0 = 0x8;
    var1 = randi(0, var0);
    if (0 == var1)
    {
        return 0xc4;
    }
    else if (0x1 == var1)
    {
        return 0xc5;
    }
    else if (0x2 == var1)
    {
        return 0xc7;
    }
    else if (0x3 == var1)
    {
        return 0xc8;
    }
    else if (0x4 == var1)
    {
        return 0xca;
    }
    else if (0x5 == var1)
    {
        return 0xcb;
    }
    else if (0x6 == var1)
    {
        return 0xcd;
    }
    else if (0x7 == var1)
    {
        return 0xce;
    }
    return 0xc4;
}

int func_1019()
{
    StatusModule(0x5, 0, 0x34, 0x3, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0, 0x1, 0, 0, 0, 0x10, 0, 0);
    return 0;
}

void func_1020()
{
    func_38();
    WorkModule(0x1b, 0x1e00003c);
}

int func_1021()
{
    float var0;
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (func_39())
    {
        return 0x1;
    }
    var0 = 0.75f;
    if (func_88() >= var0)
    {
        if (global18 == 0)
        {
            func_16(0x1, 0x1);
            return 0x1;
        }
    }
    return 0;
}

void func_1022()
{
    func_1020();
    func_22(0xfc, 0, 1.0f);
    func_78(func_1024);
}

void func_1023()
{
    func_1020();
    func_22(0xfd, 0, 1.0f);
    func_78(func_1025);
}

void func_1024()
{
    if (func_1021())
    {
        return 0x1;
    }
    if (MotionModule(0x2712) != 0)
    {
        func_16(0x7c, 0);
        return 0x1;
    }
}

void func_1025()
{
    if (func_1021())
    {
        return 0x1;
    }
    func_1028();
}

void func_1026()
{
    
}

void func_1027()
{
    float var0;
    float var1;
    float var2;
    if (global4 == 0x7b)
    {
        var0 = PostureModuleF(0x1);
        var1 = PostureModuleF(0x2);
        var2 = PostureModuleF(0x3);
        PostureModule(0x3, var0, var1, var2);
    }
}

void func_1028()
{
    if (!global3)
    {
        func_1030();
    }
}

void func_1029()
{
    int var0;
    var0 = WorkModule(0x6, 0x11000002);
    var0++;
    WorkModule(0x7, 0, 0x11000002);
}

void func_1030()
{
    int var0;
    int var1;
    int var2;
    var0 = global4;
    if (var0 == 0x7c)
    {
        var1 = global18;
        if (var1 == 0)
        {
            if (GroundModule(0x2726, 0.8600000143051147f) == 0)
            {
                var2 = WorkModule(0x6, 0x11000002);
                if (GroundModule(0x2726, 2.75f) == 0 || var2 > 0x78)
                {
                    func_16(0, 0);
                }
            }
        }
    }
}

void func_1031()
{
    
}

int func_1032()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x5, 0x4000000, 0, 0x20000);
    return 0;
}

void func_1033()
{
    func_22(0x72, 0, 1.0f);
    WorkModule(0x16, 0x1e000000);
}

void func_1034()
{
    ItemModule(0xf, 0);
    func_1033();
    func_78(func_1035);
}

void func_1035()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000000) == 0x1 && MotionModule(0x2712) == 0x1 && global18 == 0)
    {
        func_16(0, 0);
        return 0x1;
    }
}

void func_1036()
{
    
}

int func_1037()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0x4);
    StatusModule(0x2713, 0, 0, 0, 0x1, 0, 0, 0x4000002, 0, 0);
    return 0;
}

void func_1038()
{
    CatchModule(0x2710);
}

void func_1039()
{
    ItemModule(0xf, 0);
    func_22(0x75, 0, 1.0f);
    func_78(func_1041);
}

void func_1040()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return 0x1;
    }
    if (global18 == 0x2)
    {
        func_16(0x3d, 0);
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0x3a, 0);
        return;
    }
}

void func_1041()
{
    func_1040();
    if (global9 >= 1.0f && global18 == 0)
    {
        func_16(0x3a, 0);
    }
}

void func_1042()
{
    if (global6 != 0x3a)
    {
        CatchModule(0x2711);
    }
    if (WorkModule(0x10, 0x2100000d) == 0)
    {
        ModelModule(0x2, 0x1);
    }
}

void func_1043()
{
    if (global6 == 0x3a)
    {
        BattleObject(0x2f);
    }
}

int func_1044()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x5, 0x4000000, 0, 0x20000);
    return 0;
}

void func_1045()
{
    func_22(0x73, 0, 1.0f);
    WorkModule(0x7, WorkModule(0x6, 0x120000e2), 0x11000002);
    WorkModule(0x16, 0x1e000000);
    if (!StopModule(0x1))
    {
        func_1047();
    }
    global16 = func_1047;
}

void func_1046()
{
    ItemModule(0xf, 0);
    func_1045();
    func_78(func_1048);
}

void func_1047()
{
    if (WorkModule(0x6, 0x11000002) >= 0)
    {
        WorkModule(0xa, 0x11000002);
        if (WorkModule(0x6, 0x11000002) <= WorkModule(0x6, 0x120000e2) - 0x2)
        {
            if (WorkModule(0x15, 0x1e00006f) == 0)
            {
                WorkModule(0x16, 0x1e00006f);
            }
        }
        if (WorkModule(0x6, 0x11000002) < 0)
        {
            WorkModule(0x17, 0x1e00006f);
        }
    }
}

void func_1048()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00006f) == 0x1 && func_88() <= WorkModuleF(0, 0x2000014) && global18 == 0 && 0x1)
    {
        func_16(0x39, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000000) == 0x1 && MotionModule(0x2712) == 0x1 && global18 == 0)
    {
        func_16(0, 0);
        return 0x1;
    }
}

void func_1049()
{
    
}

int func_1050()
{
    StatusModule(0x5, 0, 0x49, 0x2, 0, 0x1, 0, 0, 0, 0x4);
    StatusModule(0x2713, 0, 0, 0, 0x1, 0, 0, 0x4000002, 0, 0);
    return 0;
}

void func_1051()
{
    ItemModule(0xf, 0);
    func_22(0x75, 0, 1.0f);
    func_78(func_1052);
}

void func_1052()
{
    func_1041();
}

void func_1053()
{
    func_1043();
}

int func_1054()
{
    StatusModule(0x5, 0, 0x7, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x5, 0x4000000, 0, 0x20000);
    return 0;
}

void func_1055()
{
    if (global5 == 0x8)
    {
        func_22(0x74, MotionModuleF(0x1), 1.0f);
    }
    else
    {
        func_22(0x74, 0, 1.0f);
    }
    PostureModule(0x1);
    WorkModule(0x16, 0x1e000000);
}

void func_1056()
{
    ItemModule(0xf, 0);
    func_1055();
    func_78(func_1057);
}

void func_1057()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return 0x1;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000000) == 0x1 && MotionModule(0x2712) == 0x1 && global18 == 0)
    {
        func_16(0, 0);
        return 0x1;
    }
}

void func_1058()
{
    if (global6 == 0x36)
    {
        PostureModule(0x2);
    }
}

int func_1059()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0x4);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x4000002, 0, 0);
    return 0;
}

void func_1060()
{
    if (global5 == 0x36)
    {
        ControlModule(0x2718, 0x4, 0);
    }
}

void func_1061()
{
    ItemModule(0xf, 0);
    func_22(0x75, 0, 1.0f);
    WorkModule(0x16, 0x1e00006a);
    WorkModule(0x16, 0x1e00006b);
    WorkModule(0x16, 0x1e00006c);
    func_78(func_1063);
}

int func_1062()
{
    if (global38 & 0x1 && global18 == 0)
    {
        func_16(0x3b, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00006a) == 0x1 && func_86() < WorkModuleF(0, 0x2000007) && func_84() >= WorkModuleF(0, 0x2000007) && global18 == 0)
    {
        WorkModule(0x7, 0x1e00006a, 0x11000003);
        func_16(0x3e, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00006b) == 0x1 && ControlModuleF(0x3) < WorkModuleF(0, 0x200003a) && global32 >= WorkModuleF(0, 0x200003a) && global18 == 0)
    {
        WorkModule(0x7, 0x1e00006b, 0x11000003);
        func_16(0x3e, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00006c) == 0x1 && ControlModuleF(0x3) > WorkModuleF(0, 0x200003c) && global32 <= WorkModuleF(0, 0x200003c) && global18 == 0)
    {
        WorkModule(0x7, 0x1e00006c, 0x11000003);
        func_16(0x3e, 0x1);
        return 0x1;
    }
    return 0;
}

void func_1063()
{
    if (global18 == 0x2)
    {
        func_16(0x3d, 0);
        return;
    }
    if (StatusModule(0x6) == 0x1)
    {
        return;
    }
    func_1062();
}

void func_1064()
{
    if (global6 != 0x3a && global6 != 0x3b && global6 != 0x3c && global6 != 0x3e && global6 != 0xdc)
    {
        CatchModule(0x2711);
    }
}

void func_1065()
{
    if (global6 == 0x3e)
    {
        if (WorkModule(0x10, 0x2100000d) == 0x1)
        {
            if (func_84() >= WorkModuleF(0, 0x2000007))
            {
                if (func_88() < 0)
                {
                    WorkModule(0x7, 0x79, 0x11000002);
                }
                else
                {
                    WorkModule(0x7, 0x78, 0x11000002);
                }
            }
            else if (global32 >= WorkModuleF(0, 0x200003a))
            {
                WorkModule(0x7, 0x7a, 0x11000002);
            }
            else if (global32 <= WorkModuleF(0, 0x200003c))
            {
                WorkModule(0x7, 0x7b, 0x11000002);
            }
            else
            {
                WorkModule(0x7, 0x78, 0x11000002);
            }
        }
        else if (WorkModule(0x6, 0x11000003) == 0x1e00006a)
        {
            if (func_88() > 0)
            {
                WorkModule(0x7, 0x78, 0x11000002);
            }
            else
            {
                WorkModule(0x7, 0x79, 0x11000002);
            }
        }
        else if (WorkModule(0x6, 0x11000003) == 0x1e00006b)
        {
            WorkModule(0x7, 0x7a, 0x11000002);
        }
        else
        {
            WorkModule(0x7, 0x7b, 0x11000002);
        }
    }
}

int func_1066()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0x4);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0x482, 0x4000002, 0x1000, 0x40000);
    return 0;
}

void func_1067()
{
    ItemModule(0xf, 0);
    WorkModule(0x16, 0x1e00006a);
    WorkModule(0x16, 0x1e00006b);
    WorkModule(0x16, 0x1e00006c);
    func_22(0x76, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_1068();
    }
    global16 = func_1068;
    func_78(func_1069);
}

void func_1068()
{
    if (WorkModule(0x10, 0x2100000d))
    {
        func_1062();
    }
}

void func_1069()
{
    if (global18 == 0x2)
    {
        func_16(0x3d, 0);
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0x3a, 0);
        return;
    }
}

void func_1070()
{
    func_1065();
}

int func_1071()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x4000000, 0, 0);
    return 0;
}

void func_1072()
{
    float var0;
    float var1;
    var0 = KineticModuleF(0xa, 0x3);
    var1 = KineticModuleF(0xb, 0x3);
    var0 += WorkModuleF(0, 0x20000f0) * -PostureModuleF(0);
    KineticModule(0x11, 0x3, var0, var1);
}

void func_1073()
{
    ItemModule(0xf, 0);
    func_22(0x77, 0, 1.0f);
    WorkModule(0x7, 0xffffffff, 0x11000002);
    func_78(func_1074);
}

void func_1074()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return;
        }
        else if (global18 == 0x2)
        {
            func_16(0xe, 0);
            return;
        }
    }
    if (global18 != WorkModule(0x6, 0x11000002))
    {
        if (global18 == 0)
        {
            KineticModule(0, 0x2f);
            GroundModule(0x2710, 0x1);
        }
        else
        {
            KineticModule(0, 0);
            GroundModule(0x2710, 0x5);
        }
        WorkModule(0x7, global18, 0x11000002);
    }
}

void func_1075()
{
    
}

int func_1076()
{
    if (func_470() != 0)
    {
        return 0x1;
    }
    StatusModule(0x5, 0x2, 0x30, 0x5, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_1077()
{
    ItemModule(0xf, 0);
    WorkModule(0x19, 0x1f000008);
    func_22(0x77, 0, 1.0f);
    KineticModule(0, 0x30);
    WorkModule(0x16, 0x1e000002);
    func_78(func_1078);
}

void func_1078()
{
    if (WorkModule(0x15, 0x1e000002) == 0x1 && MotionModule(0x2712) == 0x1)
    {
        func_16(0xe, 0);
        return;
    }
}

void func_1079()
{
    
}

int func_1080()
{
    int var0;
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0x4, 0, 0);
    var0 = 0x80000;
    if (WorkModule(0x6, 0x11000002) == 0x7b)
    {
        var0 = 0x100000;
    }
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0x40001, 0x4000002, 0x2000, var0);
    return 0;
}

void func_1081()
{
    int var0;
    int var1;
    var0 = WorkModule(0x6, 0x11000002) - 0x78;
    LinkModule(0x271b, 0xb, 0x7c + var0, (0x1 << var0 & WorkModule(0x6, 0x13000074)) != 0, 0x11000006, 0x11000007, 0x1000006);
    var1 = LinkModule(0x1, 0);
    WorkModule(0x7, var1, 0x11000005);
    HitModule(0x1, WorkModule(0x6, 0x120000f3), 0);
    JostleModule(0, var1);
}

void func_1082()
{
    ItemModule(0xf, 0);
    func_22(WorkModule(0x6, 0x11000002), 0, WorkModuleF(0, 0x1000006));
    func_1083();
    func_78(func_1084);
}

void func_1083()
{
    int var0;
    var0 = WorkModule(0x6, 0x11000002);
    if (var0 == 0x78)
    {
        BattleObject(0xd, 0x2, 0x49);
    }
    else if (var0 == 0x79)
    {
        BattleObject(0xd, 0x2, 0x4a);
    }
    else if (var0 == 0x7a)
    {
        BattleObject(0xd, 0x2, 0x4b);
    }
    else if (var0 == 0x7b)
    {
        BattleObject(0xd, 0x2, 0x4c);
    }
}

void func_1084()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (global18 == 0x2)
    {
        if (CatchModule(0x2712) == 0)
        {
            func_16(0xe, 0);
        }
        else
        {
            func_16(0x3d, 0);
        }
        return;
    }
    if (MotionModule(0x2712) == 0x1 && global18 == 0)
    {
        func_16(0, 0);
        return;
    }
}

void func_1085()
{
    JostleModule(0, 0x50000000);
    if (global6 != 0 && global6 != 0x3c)
    {
        CatchModule(0x2711);
    }
}

void func_1086()
{
    
}

int func_1087()
{
    float var0;
    StatusModule(0x5, 0xffffffff, 0x2e, 0x7, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3, 0, 0);
    var0 = -LinkModuleF(0x7, 0);
    PostureModule(0, var0);
    PostureModule(0x2);
    return 0;
}

int func_1088(int arg0, int arg1)
{
    float var2;
    float var3;
    float var4;
    float var5;
    int var6;
    float var7;
    var2 = CaptureModuleF(0);
    var3 = PostureModuleF(0x7);
    var4 = PostureModuleF(0x2);
    var5 = var4;
    var6 = WorkModule(0x6, 0x13000123);
    if (var6 == 0)
    {
        var4 += 12.5f * var3;
        var5 += 8.5f * var3;
    }
    else if (var6 == 0x1)
    {
        var4 += 8.5f * var3;
        var5 = var4;
    }
    else
    {
        printf("ASSERT invalid motion_height");
    }
    var7 = WorkModuleF(0, 0x20000e7);
    if (var2 >= var4 + var7)
    {
        WorkModule(0x2710, 0x21000011);
    }
    else
    {
        WorkModule(0x2711, 0x21000011);
    }
    if (WorkModule(0x10, 0x2000004a))
    {
        if (WorkModule(0x6, 0x13000126) == 0)
        {
            return arg0;
        }
    }
    else if (var2 >= var5 + var7)
    {
        return arg0;
    }
    return arg1;
}

void func_1089()
{
    float var0;
    int var1;
    int var2;
    int var3;
    CaptureModule(0xa);
    KineticModule(0xe, 0x3, 0x16, 0, 0, 0, 0, 0);
    KineticModule(0x15, 0x3, -1.0f, -1.0f);
    KineticModule(0xb, 0x3);
    var0 = (float)WorkModule(0x6, 0x120000ec) + DamageModuleF(0) * WorkModuleF(0, 0x20000ed);
    var0 *= CaptureModuleF(0x3, 0x30000f1);
    var0 *= WorkModuleF(0, 0x30000fe);
    ControlModule(0x6, var0, WorkModuleF(0, 0x20000e3), WorkModuleF(0, 0x20000e4));
    var1 = CaptureModule(0);
    if (var1 > 0)
    {
        WorkModule(0x7, var1, 0x11000004);
    }
    var2 = CaptureModule(0xb);
    if (var2 > 0)
    {
        WorkModule(0x7, var2, 0x11000005);
    }
    if (CaptureModule(0x7))
    {
        var3 = func_1088(0x88 + var1, 0x8b + var2);
    }
    else
    {
        var3 = 0x88 + var1;
    }
    WorkModule(0x7, var3, 0x11000002);
    GroundModule(0x15, 0x1);
}

void func_1090()
{
    WorkModule(0x7, WorkModule(0x6, 0x120000e8), 0x11000003);
}

void func_1091()
{
    func_1090();
    WorkModule(0x7, 0xffffffff, 0x11000006);
    WorkModule(0x16, 0x1e000024);
    WorkModule(0x2711, 0x20000003);
    func_1094();
    func_78(func_1095);
}

void func_1092(int arg0, int arg1, int arg2)
{
    float var3;
    float var4;
    int var5;
    int var6;
    var3 = CaptureModuleF(0x1);
    var4 = CaptureModuleF(0x2);
    if (global18 == 0x2)
    {
        if (PostureModuleF(0) == -1.0f)
        {
            var5 = 0x50;
        }
        else
        {
            var5 = 0xa0;
        }
        if (GroundModule(0x2722, var5) == 0x1)
        {
            if (WorkModule(0x10, 0x2100000f) == 0x1)
            {
                var3 = var4 = 0;
            }
            else
            {
                WorkModule(0x2710, 0x2100000f);
            }
        }
        else
        {
            WorkModule(0x2711, 0x2100000f);
        }
    }
    KineticModule(0x11, 0x3, var3, var4);
    if (global18 == 0)
    {
        if (CaptureModule(0x7) == 0x1)
        {
            var6 = func_1088(arg0, arg1);
        }
        else
        {
            var6 = arg0;
            func_1088(arg0, arg0);
        }
        if (WorkModule(0x10, 0x21000011) == 0x1)
        {
            GroundModule(0x2710, 0x5);
            WorkModule(0x2711, 0x2100000f);
            return;
        }
        if (var6 != WorkModule(0x6, arg2))
        {
            WorkModule(0x7, var6, arg2);
            func_23(var6);
        }
    }
}

void func_1093()
{
    int var0;
    int var1;
    var0 = WorkModule(0x6, 0x11000004);
    var1 = WorkModule(0x6, 0x11000005);
    func_1092(0x88 + var0, 0x8b + var1, 0x11000002);
}

void func_1094()
{
    int var0;
    int var1;
    if (global18 != WorkModule(0x6, 0x11000006))
    {
        if (global18 == 0)
        {
            GroundModule(0x2710, 0x1);
            var0 = WorkModule(0x6, 0x11000002);
        }
        else
        {
            GroundModule(0x2710, 0x5);
            if (WorkModule(0x10, 0x2000004a))
            {
                var0 = WorkModule(0x6, 0x11000002);
            }
            else
            {
                var1 = WorkModule(0x6, 0x11000004);
                var0 = 0x88 + var1;
            }
        }
        if (WorkModule(0x10, 0x2100000d) == 0x1)
        {
            if (global1 == 0x19 || global1 == 0x11)
            {
                if (MotionModule(0x2712) == 0x1)
                {
                    WorkModule(0x2710, 0x21000012);
                }
            }
            func_23(var0);
        }
        else
        {
            func_22(var0, 0, 1.0f);
            WorkModule(0x2710, 0x2100000d);
        }
        WorkModule(0x7, global18, 0x11000006);
    }
}

void func_1095()
{
    func_1094();
    if (WorkModule(0x15, 0x1e000024) == 0x1)
    {
        if (global1 == 0x19 || global1 == 0x11)
        {
            if (MotionModule(0x2712) == 0x1 || WorkModule(0x10, 0x21000012) == 0x1)
            {
                func_16(0x40, 0);
                return;
            }
        }
        else if (MotionModule(0x2712) == 0x1)
        {
            func_16(0x40, 0);
            return;
        }
    }
    if (global1 == 0x19 || global1 == 0x11)
    {
        WorkModule(0x2711, 0x21000012);
    }
}

void func_1096()
{
    CaptureModule(0xa);
}

void func_1097()
{
    if (global6 != 0x3f && global6 != 0x40 && global6 != 0x41 && global6 != 0xee && global6 != 0xef && global6 != 0xf0 && global6 != 0x44 && global6 != 0xbf && global6 != 0xc0)
    {
        KineticModule(0x11, 0x3, 0, 0);
        CaptureModule(0x1);
    }
}

void func_1098()
{
    
}

int func_1099()
{
    StatusModule(0x5, 0xffffffff, 0x2e, 0x7, 0, 0, 0x1c000, 0x3c, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xb, 0, 0);
    return 0;
}

void func_1100()
{
    int var0;
    int var1;
    int var2;
    KineticModule(0xb, 0x3);
    var0 = WorkModule(0x6, 0x11000002);
    var1 = WorkModule(0x6, 0x11000004);
    var2 = WorkModule(0x6, 0x11000005);
    if (var0 == 0x88 + var1 || var0 == 0x8a + var1)
    {
        var0 = 0x89 + var1;
    }
    else if (var0 == 0x8b + var1 || var0 == 0x8d + var1)
    {
        var0 = 0x8c + var2;
    }
    else
    {
        printf("ASSERT invalid motion");
    }
    WorkModule(0x7, var0, 0x11000002);
    GroundModule(0x15, 0x1);
    if (StatusModule(0xa) == 0x3f)
    {
        ControlModule(0x2718, 0x4, 0);
    }
}

void func_1101()
{
    WorkModule(0x16, 0x1e000025);
    WorkModule(0x7, 0xffffffff, 0x11000006);
    func_1106();
    if (!StopModule(0x1))
    {
        func_1103();
    }
    global16 = func_1103;
    func_78(func_1107);
}

void func_1102()
{
    int var0;
    int var1;
    var0 = WorkModule(0x6, 0x11000004);
    var1 = WorkModule(0x6, 0x11000005);
    func_1092(0x89 + var0, 0x8c + var1, 0x11000002);
}

void func_1103()
{
    if (WorkModule(0x6, 0x11000003) >= 0)
    {
        WorkModule(0xa, 0x11000003);
        if (ControlModule(0x2710, 0x2) == 0x1)
        {
            WorkModule(0x2710, 0x2100000e);
        }
        if (global32 >= WorkModuleF(0, 0x2000023) && global47 < WorkModule(0x6, 0x12000020))
        {
            WorkModule(0x2710, 0x2100000e);
        }
    }
}

int func_1104()
{
    if (ControlModuleF(0x5) <= 0)
    {
        if (WorkModule(0x10, 0x2100000e) == 0x1 || global18 == 0x2)
        {
            func_16(0x43, 0);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000025) == 0x1)
        {
            func_16(0x42, 0);
            return 0x1;
        }
    }
    return 0;
}

int func_1105()
{
    float var0;
    float var1;
    float var2;
    if (FighterUtil(0x1d) == 0x1)
    {
        var0 = func_13(CaptureModuleF(0x1));
        var1 = func_13(CaptureModuleF(0x2));
        var2 = 1.0f / LinkModuleF(0xa, 0);
        if (var2 < 1.0f)
        {
            var0 *= var2;
            var1 *= var2;
        }
        if (var0 > WorkModuleF(0, 0x20000ea) || var1 > WorkModuleF(0, 0x20000eb))
        {
            func_16(0x42, 0);
            return 0x1;
        }
    }
    return 0;
}

void func_1106()
{
    int var0;
    int var1;
    if (global18 != WorkModule(0x6, 0x11000006))
    {
        if (global18 == 0)
        {
            GroundModule(0x2710, 0x2);
            var0 = WorkModule(0x6, 0x11000002);
        }
        else
        {
            GroundModule(0x2710, 0x5);
            if (WorkModule(0x10, 0x2000004a))
            {
                var0 = WorkModule(0x6, 0x11000002);
            }
            else
            {
                var1 = WorkModule(0x6, 0x11000004);
                var0 = 0x89 + var1;
            }
        }
        if (WorkModule(0x10, 0x2100000d) == 0x1)
        {
            func_23(var0);
        }
        else
        {
            func_22(var0, 0, 1.0f);
            WorkModule(0x2710, 0x2100000d);
        }
        WorkModule(0x7, global18, 0x11000006);
    }
}

void func_1107()
{
    func_1106();
    if (func_1104() == 0x1)
    {
        return;
    }
    if (func_1105() == 0x1)
    {
        return;
    }
}

void func_1108()
{
    CaptureModule(0xa);
}

void func_1109()
{
    func_1098();
}

int func_1110()
{
    StatusModule(0x5, 0xffffffff, 0x2e, 0x7, 0, 0, 0x1c000, 0x3c, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xf, 0, 0);
    return 0;
}

void func_1111()
{
    int var0;
    int var1;
    int var2;
    KineticModule(0xb, 0x3);
    var0 = WorkModule(0x6, 0x11000002);
    var1 = WorkModule(0x6, 0x11000004);
    var2 = WorkModule(0x6, 0x11000005);
    if (var0 == 0x88 + var1 || var0 == 0x89 + var1 || var0 == 0x8a + var1)
    {
        var0 = 0x8a + var1;
    }
    else if (var0 == 0x8b + var2 || var0 == 0x8c + var2 || var0 == 0x8d + var2)
    {
        var0 = 0x8d + var2;
    }
    else
    {
        printf("ASSERT invalid motion_kind");
    }
    WorkModule(0x7, var0, 0x11000002);
    GroundModule(0x15, 0x1);
}

void func_1112()
{
    WorkModule(0x16, 0x1e000025);
    WorkModule(0x16, 0x1e000024);
    WorkModule(0x7, 0xffffffff, 0x11000006);
    func_1113();
    func_78(func_1116);
}

void func_1113()
{
    int var0;
    int var1;
    if (global18 != WorkModule(0x6, 0x11000006))
    {
        if (global18 == 0)
        {
            GroundModule(0x2710, 0x2);
            var0 = WorkModule(0x6, 0x11000002);
        }
        else
        {
            GroundModule(0x2710, 0x5);
            if (WorkModule(0x10, 0x2000004a))
            {
                var0 = WorkModule(0x6, 0x11000002);
            }
            else
            {
                var1 = WorkModule(0x6, 0x11000004);
                var0 = 0x8a + var1;
            }
        }
        if (WorkModule(0x10, 0x2100000d) == 0x1)
        {
            func_23(var0);
        }
        else
        {
            func_22(var0, 0, 1.0f);
            WorkModule(0x2710, 0x2100000d);
        }
        WorkModule(0x7, global18, 0x11000006);
    }
}

int func_1114()
{
    func_1113();
    if (WorkModule(0x15, 0x1e000025) == 0x1 && ControlModuleF(0x5) <= 0)
    {
        func_16(0x42, 0);
        return 0x1;
    }
    return 0;
}

void func_1115()
{
    int var0;
    int var1;
    var0 = WorkModule(0x6, 0x11000004);
    var1 = WorkModule(0x6, 0x11000005);
    func_1092(0x8a + var0, 0x8d + var1, 0x11000002);
}

void func_1116()
{
    func_1114();
    if (WorkModule(0x15, 0x1e000024) == 0x1)
    {
        if (MotionModule(0x2712) == 0x1)
        {
            func_16(0x40, 0);
            return;
        }
    }
}

void func_1117()
{
    CaptureModule(0xa);
}

void func_1118()
{
    func_1098();
}

int func_1119()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0x1, 0, 0, 0, 0, 0);
    return 0;
}

void func_1120()
{
    int var0;
    float var1;
    float var2;
    if (global18 == 0)
    {
        var0 = 0x3;
    }
    else
    {
        var0 = 0x2;
    }
    var1 = KineticModuleF(0xa, var0);
    var2 = KineticModuleF(0xb, var0);
    var1 += WorkModuleF(0, 0x20000f0) * -PostureModuleF(0);
    KineticModule(0x11, var0, var1, var2);
    KineticModule(0xb, var0);
}

void func_1121()
{
    func_22(0x8e, 0, 1.0f);
    WorkModule(0x7, 0xffffffff, 0x11000002);
    PhysicsModule(0xb, 0);
    func_78(func_1122);
}

void func_1122()
{
    if (CancelModule(0x2713) == 0x1)
    {
        if (global18 == 0)
        {
            if (func_39() != 0)
            {
                return;
            }
        }
        else if (global18 == 0x2)
        {
            if (func_41() != 0)
            {
                return;
            }
        }
    }
    if (MotionModule(0x2712) == 0x1)
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return;
        }
        else if (global18 == 0x2)
        {
            func_16(0xe, 0);
            return;
        }
    }
    if (global18 != WorkModule(0x6, 0x11000002))
    {
        if (global18 == 0)
        {
            KineticModule(0, 0x2f);
            GroundModule(0x2710, 0x1);
        }
        else
        {
            KineticModule(0, 0);
            GroundModule(0x2710, 0x5);
        }
        WorkModule(0x7, global18, 0x11000002);
    }
}

void func_1123()
{
    int var0;
    PhysicsModule(0xb, 0x1);
    var0 = WorkModule(0x6, 0x120000f8);
    WorkModule(0x7, var0, 0x10000058);
    WorkModule(0x2711, 0x20000031);
}

int func_1124()
{
    int var0;
    if (func_470() != 0)
    {
        return 0x1;
    }
    if (global5 == 0x100)
    {
        var0 = 0x54;
    }
    else if (global5 == 0x101)
    {
        var0 = 0x56;
    }
    else if (global5 == 0xf6)
    {
        var0 = 0x57;
    }
    else
    {
        var0 = 0x30;
    }
    StatusModule(0x5, 0x2, var0, 0x5, 0x4, 0x1, 0, 0, 0, 0x4);
    StatusModule(0x2713, 0, 0, 0x1, 0x1, 0, 0, 0, 0, 0);
    return 0;
}

void func_1125()
{
    WorkModule(0x19, 0x1f000008);
    WorkModule(0x7, WorkModule(0x6, 0x120000e9), 0x11000002);
    func_22(0x8f, 0, 1.0f);
    WorkModule(0x16, 0x1e000002);
    PhysicsModule(0xb, 0);
    func_78(func_1126);
}

void func_1126()
{
    if (func_55())
    {
        return;
    }
    if (CancelModule(0x2713) == 0x1 && func_41() != 0)
    {
        return;
    }
    if (WorkModule(0x15, 0x1e000002) == 0x1 && MotionModule(0x2712) == 0x1)
    {
        func_16(0xe, 0);
        return;
    }
}

void func_1127()
{
    int var0;
    PhysicsModule(0xb, 0x1);
    var0 = WorkModule(0x6, 0x120000f8);
    WorkModule(0x7, var0, 0x10000058);
    WorkModule(0x2711, 0x20000031);
}

int func_1128()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0x4, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0xe, 0, 0);
    return 0;
}

void func_1129()
{
    int var0;
    int var1;
    CaptureModule(0x2);
    var0 = WorkModule(0x6, 0x13000120);
    var1 = 0x96;
    if (0x1 == var0)
    {
        MotionModule(0x29, 0x4);
    }
    else if (0x3 == var0)
    {
        MotionModule(0x29, 0x8);
    }
    LinkModule(0x2716, 0, 0x3);
}

void func_1130()
{
    func_22(WorkModule(0x6, 0x11000002), 0, 1.0f);
    func_78(func_1132);
}

void func_1131()
{
    
}

void func_1132()
{
    func_1131();
}

void func_1133()
{
    int var0;
    float var1;
    float var2;
    float var3;
    var0 = 0;
    if (global6 == 0x53)
    {
        var0 = FighterUtil(0xc);
    }
    CaptureModule(0x4);
    if (var0 == 0x1)
    {
        GroundModule(0x271c);
        GroundModule(0x271b);
        var1 = GroundModuleF(0x8);
        var2 = GroundModuleF(0x9);
        var3 = PostureModuleF(0x3);
        PostureModule(0x3, var1, var2, var3);
        GroundModule(0x2716);
        if (GroundModule(0xa) & 0x8)
        {
            var1 = GroundModuleF(0x8);
            var2 = GroundModuleF(0x9);
            PostureModule(0x3, var1, var2, var3);
            GroundModule(0x2710, 0x1);
            func_20(0);
        }
    }
}

void func_1134()
{
    int var0;
    var0 = WorkModule(0x6, 0x120000f8);
    WorkModule(0x7, var0, 0x10000058);
    WorkModule(0x2711, 0x20000031);
}

int func_1135()
{
    int var0;
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0, 0, 0x4, 0, 0);
    var0 = 0x80000;
    if (WorkModule(0x6, 0x11000002) == 0x7b)
    {
        var0 = 0x100000;
    }
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0x40001, 0x4000002, 0x2000, var0);
    return 0;
}

void func_1136()
{
    KineticModule(0xc, 0x5);
    func_22(WorkModule(0x6, 0x11000002), 0, 1.0f);
    WorkModule(0x16, 0x1e000093);
    func_1083();
    if (!StopModule(0x1))
    {
        func_1138();
    }
    global16 = func_1138;
    func_78(func_1137);
}

void func_1137()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (WorkModule(0x15, 0x1e000093) && global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (MotionModule(0x2712))
    {
        KineticModule(0, 0x13);
        func_16(0xe, 0);
        return 0x1;
    }
    func_1141();
}

void func_1138()
{
    if (WorkModule(0x10, 0x2100000d))
    {
        GroundModule(0x2710, 0x5);
        func_20(0x2);
        KineticModule(0, 0x12);
        WorkModule(0x17, 0x1e000093);
        WorkModule(0x2711, 0x2100000d);
    }
}

void func_1139()
{
    KineticModule(0xb, 0x5);
    if (global18 == 0)
    {
        KineticModule(0xe, 0, 0x2, 0, 0, 0, 0, 0);
    }
    else
    {
        KineticModule(0xe, 0, 0x4, 0, 0, 0, 0, 0);
    }
    KineticModule(0xc, 0);
}

void func_1140()
{
    int var0;
    int var1;
    var0 = WorkModule(0x6, 0x11000002);
    var1 = var0 - 0x79;
    BattleObject(0x5e, 0xb, 0x7d + var1);
    if (var0 == 0x7a)
    {
        CameraModule(0x2720, 0);
    }
    WorkModule(0x2710, 0x2000002d);
    WorkModule(0x2711, 0x2000001d);
    HitModule(0x1, WorkModule(0x6, 0x120000f3), 0);
}

void func_1141()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    int var6;
    GroundModule(0x8, 0x1);
    var0 = KineticModuleF(0, 0x1);
    var1 = KineticModuleF(0x1, 0x1);
    if (var1 < 0)
    {
        var2 = PostureModuleF(0x2);
        var3 = StageData(0x2);
        var4 = StageData(0xc);
        var5 = var4 + func_13(var3 - var4) * 0.5f;
        var6 = 0;
        if (var2 > var5)
        {
            var6 = 0x1;
        }
        if (var6)
        {
            GroundModule(0x2710, 0);
            func_20(0x2);
        }
        else
        {
            GroundModule(0x2710, 0x5);
        }
    }
}

void func_1142()
{
    if (WorkModule(0x6, 0x11000002) == 0x7a)
    {
        CameraModule(0x2720, 0x7);
    }
    if (global6 == 0xe)
    {
        if (!MotionModule(0x2712))
        {
            CatchModule(0x2711);
        }
    }
    else
    {
        CatchModule(0x2711);
    }
}

int func_1143()
{
    if (WorkModule(0x10, 0x2000000b))
    {
        StatusModule(0x2711, 0xd7);
        return 0x1;
    }
    StatusModule(0x5, 0x2, 0x33, 0x5, 0x4, 0, 0, 0, 0, 0x1);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0x10, 0, 0);
    return 0;
}

void func_1144()
{
    if (!WorkModule(0x10, 0x2100000d))
    {
        if (WorkModule(0x10, 0x2100000e))
        {
            if (ControlModule(0x2713, 0x2))
            {
                WorkModule(0x2710, 0x21000005);
            }
        }
        else if (global32 < WorkModuleF(0, 0x2000022))
        {
            WorkModule(0x2710, 0x21000005);
        }
    }
}

void func_1145()
{
    if (ControlModule(0x2710, 0x2))
    {
        WorkModule(0x2710, 0x2100000e);
        ControlModule(0x271b);
    }
    else
    {
        ControlModule(0x271a);
    }
    WorkModule(0x9, 0x10000006);
    WorkModule(0x7, WorkModule(0x6, 0x120000b7), 0x10000007);
    WorkModule(0x7, 0x1, 0x11000000);
    func_1149();
    if (!StopModule(0x1))
    {
        func_1144();
    }
    global16 = func_1144;
    func_78(func_1146);
}

void func_1146()
{
    if (MotionModule(0x2712) || WorkModule(0x10, 0x2100000d) || !LinkModule(0x2, 0x3))
    {
        func_16(0xb, 0);
        return;
    }
}

void func_1147()
{
    WorkModule(0x7, WorkModule(0x6, 0x120000b7), 0x10000007);
}

void func_1148()
{
    
}

void func_1149()
{
    if (LinkModule(0x5, 0x3, WorkModule(0x6, 0x10000008)))
    {
        LinkModule(0x3, 0x3, 0x6, 0x11000004, 0x1000007, 0x21000010);
        if (WorkModule(0x10, 0x21000010) == 0x1)
        {
            func_22(0x3c, 0, 1.0f);
            LinkModule(0x7, 0x3, 0, WorkModule(0x6, 0x11000004), 0x5);
            LinkModule(0xc, 0x3);
        }
        else
        {
            WorkModule(0x2710, 0x2100000d);
            PostureModule(0x3, WorkModuleF(0, 0x1000007), WorkModuleF(0, 0x1000008), GroundModuleF(0xc));
        }
        if (!WorkModule(0x10, 0x21000011))
        {
            WorkModule(0x7, 0, 0x10000006);
        }
        WorkModule(0, WorkModuleF(0, 0x1000009) + 0, 0x1000006);
    }
}

void func_1150()
{
    FighterUtil(0x7);
}

int func_1151()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_1152()
{
    func_22(0x3d, 0, 1.0f);
    func_78(func_1153);
}

void func_1153()
{
    if (MotionModule(0x2712) && global18 == 0)
    {
        func_16(0xb5, 0);
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
}

void func_1154()
{
    
}

void func_1155()
{
    LinkModule(0x4, 0x3, 0x7, 0);
}

int func_1156()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_1157()
{
    func_22(0x40, 0, 1.0f);
    func_78(func_1158);
}

void func_1158()
{
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (MotionModule(0x2712) && global18 == 0)
    {
        func_16(0, 0);
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
}

void func_1159()
{
    
}

int func_1160()
{
    StatusModule(0x5, 0x2, 0x33, 0x5, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0x1, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_1161()
{
    func_22(0x3e, 0, 1.0f);
    func_78(func_1162);
}

void func_1162()
{
    if (MotionModule(0x2712))
    {
        func_16(0xb7, 0);
        return;
    }
}

void func_1163()
{
    
}

void func_1164()
{
    LinkModule(0x4, 0x3, 0x7, 0);
}

int func_1165()
{
    StatusModule(0x5, 0x2, 0x13, 0x5, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_1166()
{
    if (!WorkModule(0x2712, 0x2100000f))
    {
        if (WorkModule(0x6, 0x11000003) <= 0)
        {
            printf("sub_tread_fall_uniq_check FIGHTER_STATUS_TREAD_WORK_INT_RECOVERY_FRAME <= 0");
            func_40();
            WorkModule(0x2710, 0x2100000f);
            func_100(0x4);
        }
    }
}

void func_1167()
{
    func_22(0x3f, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_1166();
    }
    global16 = func_1166;
    func_78(func_1168);
}

void func_1168()
{
    if (WorkModule(0x2712, 0x2100000f))
    {
        if (func_41())
        {
            return;
        }
    }
    if (global18 == 0)
    {
        func_16(0x4d, 0);
        return;
    }
}

void func_1169()
{
    
}

void func_1170()
{
    WorkModule(0x7, WorkModule(0x6, 0x13000038), 0x11000003);
}

void func_1171()
{
    WorkModule(0xf, 0x11000003);
}

int func_1172()
{
    StatusModule(0x5, 0, 0x32, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x8000000, 0, 0);
    return 0;
}

void func_1173()
{
    KineticModule(0, 0xf);
    if (ItemModule(0x2, 0x2000))
    {
        if (KineticModuleF(0x2, 0x1) >= WorkModuleF(0, 0x3000003) * WorkModuleF(0, 0x200020b))
        {
            func_22(0x114, 0, 1.0f);
        }
        else
        {
            func_22(0x113, 0, 1.0f);
        }
    }
    else if (KineticModuleF(0x2, 0x1) >= WorkModuleF(0, 0x3000003) * WorkModuleF(0, 0x200020b))
    {
        func_22(0x112, 0, 1.0f);
    }
    else
    {
        func_22(0x111, 0, 1.0f);
    }
    func_78(func_1174);
}

void func_1174()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0, 0);
        return;
    }
}

void func_1175()
{
    
}

int func_1176()
{
    if (ItemModule(0x11) == 0x69)
    {
        StatusModule(0x2711, 0xf8);
        return 0x1;
    }
    return 0;
}

int func_1177()
{
    if (func_1176())
    {
        return 0x1;
    }
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x7d2, 0x8000000, 0, 0x10000);
    return 0;
}

void func_1178()
{
    
}

void func_1179()
{
    
}

void func_1180()
{
    if ((global29 & 0xf) != 0)
    {
        if ((global29 & 0x1) != 0)
        {
            WorkModule(0x7, 0x119, 0x11000002);
            WorkModule(0x7, 0x123, 0x11000003);
        }
        else if ((global29 & 0x2) != 0)
        {
            WorkModule(0x7, 0x11a, 0x11000002);
            WorkModule(0x7, 0x124, 0x11000003);
            WorkModule(0, -PostureModuleF(0), 0x1000006);
        }
        else if ((global29 & 0x4) != 0)
        {
            WorkModule(0x7, 0x11b, 0x11000002);
            WorkModule(0x7, 0x125, 0x11000003);
        }
        else
        {
            WorkModule(0x7, 0x11c, 0x11000002);
            WorkModule(0x7, 0x126, 0x11000003);
        }
        WorkModule(0x11, 0x2000002e);
    }
    else if ((global29 & 0x10) != 0)
    {
        WorkModule(0x7, 0x117, 0x11000002);
        WorkModule(0x7, 0x121, 0x11000003);
    }
    else if ((global29 & 0x20) != 0)
    {
        WorkModule(0x7, 0x118, 0x11000002);
        WorkModule(0x7, 0x122, 0x11000003);
    }
    else if ((global29 & 0x40) != 0 && (ItemModule(0x4) == 0 || ItemModule(0x5, 0x8) == 0))
    {
        WorkModule(0x7, 0x11e, 0x11000002);
        WorkModule(0x7, 0x11e, 0x11000003);
    }
    else if ((global29 & 0x80) != 0)
    {
        WorkModule(0x7, 0x115, 0x11000002);
        WorkModule(0x7, 0x11f, 0x11000003);
    }
    else if ((global29 & 0x100) != 0)
    {
        WorkModule(0x7, 0x116, 0x11000002);
        WorkModule(0x7, 0x120, 0x11000003);
        WorkModule(0, -PostureModuleF(0), 0x1000006);
    }
}

void func_1181()
{
    if ((global29 & 0x15400) != 0)
    {
        if ((global29 & 0x400) != 0)
        {
            WorkModule(0x7, 0x123, 0x11000002);
            WorkModule(0x7, 0x119, 0x11000003);
        }
        else if ((global29 & 0x1000) != 0)
        {
            WorkModule(0x7, 0x124, 0x11000002);
            WorkModule(0x7, 0x11a, 0x11000003);
            WorkModule(0, -PostureModuleF(0), 0x1000006);
        }
        else if ((global29 & 0x4000) != 0)
        {
            WorkModule(0x7, 0x125, 0x11000002);
            WorkModule(0x7, 0x11b, 0x11000003);
        }
        else
        {
            WorkModule(0x7, 0x126, 0x11000002);
            WorkModule(0x7, 0x11c, 0x11000003);
        }
        WorkModule(0x11, 0x2000002e);
    }
    else if ((global29 & 0x200) != 0)
    {
        WorkModule(0x7, 0x11f, 0x11000002);
        WorkModule(0x7, 0x115, 0x11000003);
    }
    else if ((global29 & 0x800) != 0)
    {
        WorkModule(0x7, 0x120, 0x11000002);
        WorkModule(0x7, 0x116, 0x11000003);
        WorkModule(0, -PostureModuleF(0), 0x1000006);
    }
    else if ((global29 & 0x2000) != 0)
    {
        WorkModule(0x7, 0x121, 0x11000002);
        WorkModule(0x7, 0x117, 0x11000003);
    }
    else if ((global29 & 0x8000) != 0)
    {
        WorkModule(0x7, 0x122, 0x11000002);
        WorkModule(0x7, 0x118, 0x11000003);
    }
}

void func_1182()
{
    if (global5 == 0x8)
    {
        WorkModule(0x2710, 0x21000011);
        KineticModule(0, 0x7);
        KineticModule(0xb, 0);
    }
    else
    {
        WorkModule(0x2711, 0x21000011);
    }
    WorkModule(0, PostureModuleF(0), 0x1000006);
    if (WorkModule(0x6, 0x11000002) == 0)
    {
        if (global18 == 0)
        {
            func_1180();
        }
        else
        {
            func_1181();
        }
    }
    ControlModule(0x271f);
    func_75();
    func_76();
    ControlModule(0x271b);
    WorkModule(0x7, 0xffffffff, 0x11000006);
    WorkModule(0x11, 0x2100000f);
    func_1183();
    func_78(func_1185);
}

void func_1183()
{
    if (global18 != WorkModule(0x6, 0x11000006))
    {
        if (WorkModule(0x10, 0x2100000f) == 0)
        {
            WorkModule(0x7, WorkModule(0x6, 0x11000002), 0x11000004);
            WorkModule(0x7, WorkModule(0x6, 0x11000003), 0x11000002);
            WorkModule(0x7, WorkModule(0x6, 0x11000004), 0x11000003);
        }
        if (WorkModule(0x10, 0x2100000d) == 0x1)
        {
            func_23(WorkModule(0x6, 0x11000002));
        }
        else
        {
            func_22(WorkModule(0x6, 0x11000002), 0, 1.0f);
            WorkModule(0x11, 0x2100000d);
        }
        if (global18 == 0)
        {
            GroundModule(0x2710, 0x2);
            if (WorkModule(0x10, 0x21000011) == 0)
            {
                KineticModule(0, 0xf);
            }
            WorkModule(0x2711, 0x20000003);
        }
        else
        {
            GroundModule(0x2710, 0x5);
            KineticModule(0, 0);
        }
        WorkModule(0x7, global18, 0x11000006);
        WorkModule(0x12, 0x2100000f);
    }
}

void func_1184()
{
    
}

void func_1185()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    func_1184();
    func_1183();
    if (WorkModule(0x10, 0x21000010))
    {
        func_16(0xf8);
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        if (global18 == 0x2)
        {
            func_16(0xe, 0);
        }
        else
        {
            func_16(0, 0);
        }
        return;
    }
}

void func_1186()
{
    
}

void func_1187()
{
    func_1186();
    WorkModule(0x12, 0x2000002e);
    if (global18 == 0)
    {
        WorkModule(0x2711, 0x20000003);
    }
}

int func_1188()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x7d2, 0x8000000, 0, 0x10000);
    return 0;
}

void func_1189()
{
    WorkModule(0, PostureModuleF(0), 0x1000006);
    WorkModule(0x16, 0x1e000074);
    func_22(0x11d, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_1190();
    }
    global16 = func_1190;
    func_78(func_1191);
}

void func_1190()
{
    WorkModule(0x9, 0x11000005);
    if (WorkModule(0x6, 0x11000005) >= WorkModule(0x6, 0x1300000c))
    {
        WorkModule(0x17, 0x1e000074);
    }
}

void func_1191()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    func_1184();
    if (WorkModule(0x10, 0x21000010))
    {
        func_16(0xf8);
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712) == 0x1 && global18 == 0)
    {
        func_16(0, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e000074) == 0x1 && (global38 & 0x1) != 0 && ControlModule(0x271c) == 0 && global32 >= WorkModuleF(0, 0x200003a) && global18 == 0)
    {
        func_16(0x8c, 0);
        return;
    }
}

void func_1192()
{
    func_1186();
}

int func_1193()
{
    if (ItemModule(0x23) == 0xb)
    {
        StatusModule(0x2711, 0xf9);
        return 0x1;
    }
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x8000000, 0, 0);
    return 0;
}

void func_1194()
{
    func_78(func_1195);
}

void func_1195()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0x4c, 0);
        return;
    }
    if (global18 == 0 && MotionModule(0x2712) == 0x1)
    {
        if (ItemModule(0x4))
        {
            if (ItemModule(0x11) == 0x6000001f)
            {
                func_16(0x91, 0);
            }
            else
            {
                func_16(0x8e, 0);
            }
        }
        else
        {
            func_16(0, 0);
        }
        return;
    }
}

void func_1196()
{
    
}

int func_1197()
{
    if (global18 == 0x2)
    {
        func_16(0x4c, 0);
        return 0x1;
    }
    if (global18 == 0 && global24 & 0x1)
    {
        func_16(0x91, 0);
        return 0x1;
    }
    if (ItemModule(0x4) == 0 && global18 == 0)
    {
        func_16(0, 0);
        return 0x1;
    }
    return 0;
}

int func_1198()
{
    StatusModule(0x5, 0, 0xf, 0x1, 0, 0x1, 0, 0x4, 0x180, 0x40);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x8000010, 0, 0);
    return 0;
}

void func_1199()
{
    TurnModule(0x2710, 0x1);
    WorkModule(0x2711, 0x2100000e);
    func_78(func_1200);
}

void func_1200()
{
    if (func_1197())
    {
        return;
    }
    if (global18 == 0 && TurnModule(0) == 0)
    {
        func_16(0x8e, 0);
        return;
    }
    if (WorkModule(0x6, 0x13000121) == 0x1)
    {
        if (!WorkModule(0x10, 0x2100000e) && TurnModule(0x3))
        {
            MotionModule(0x1b, !MotionModule(0x2e));
            WorkModule(0x2710, 0x2100000e);
        }
    }
}

void func_1201()
{
    float var0;
    int var1;
    if (TurnModule(0) && TurnModule(0x1) == 0)
    {
        TurnModule(0x2711);
    }
    if (WorkModule(0x6, 0x13000121) == 0x1)
    {
        if (WorkModule(0x10, 0x2100000e))
        {
            var0 = PostureModuleF(0);
            var1 = MotionModule(0x2e);
            if (var0 == 1.0f && var1 == 0x1)
            {
                MotionModule(0x1b, 0);
            }
            else if (var0 == -1.0f && var1 == 0)
            {
                MotionModule(0x1b, 0x1);
            }
        }
    }
}

int func_1202()
{
    StatusModule(0x5, 0, 0x32, 0x1, 0, 0x1, 0, 0x4, 0x180, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x8000010, 0, 0);
    return 0;
}

void func_1203()
{
    int var0;
    var0 = WorkModule(0x6, 0x11000002);
    if (var0 == 0)
    {
        return 0;
    }
    else
    {
        return WorkModuleF(0, 0x3000119);
    }
}

void func_1204()
{
    float var0;
    var0 = func_1203();
    func_22(0x128, var0, 1.0f);
    func_78(func_1205);
}

void func_1205()
{
    float var0;
    if (func_1197())
    {
        return;
    }
    if (global18 == 0)
    {
        var0 = func_88();
        if (var0 < WorkModuleF(0, 0x20001fc))
        {
            func_16(0x8e, 0);
            return;
        }
    }
}

void func_1206()
{
    float var0;
    int var1;
    if (global6 == 0x8e)
    {
        var0 = MotionModuleF(0x1);
        if (var0 >= WorkModuleF(0, 0x3000118) && var0 < WorkModuleF(0, 0x300011a))
        {
            var1 = 0x1;
        }
        else
        {
            var1 = 0;
        }
        WorkModule(0x7, var1, 0x11000002);
    }
}

int func_1207()
{
    StatusModule(0x5, 0, 0xf, 0x1, 0, 0x1, 0, 0x4, 0x180, 0x40);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x8000010, 0, 0);
    return 0;
}

void func_1208()
{
    float var0;
    float var1;
    float var2;
    if (global5 != 0x8b && global5 != 0x91 && global5 != 0x8e && global5 != 0x8f && global5 != 0x90)
    {
        var0 = (float)MotionModule(0, 0x127);
        var1 = sys_40(0) * WorkModuleF(0, 0x20000a6);
        func_22(0x127, var0, var1);
    }
    else if (global5 == 0x90)
    {
        var2 = func_1203();
        MotionModule(0x1, 0x128, var2, 0, 6.0f);
    }
    func_78(func_1209);
}

void func_1209()
{
    float var0;
    if (func_1197())
    {
        return;
    }
    if (global18 == 0)
    {
        var0 = func_88();
        if (var0 >= WorkModuleF(0, 0x20001fc))
        {
            func_16(0x90, 0);
            return;
        }
        if (var0 <= WorkModuleF(0, 0x20001fd))
        {
            func_16(0x8f, 0);
            return;
        }
    }
}

void func_1210()
{
    
}

void func_1211()
{
    int var0;
    float var1;
    WorkModule(0, PostureModuleF(0) + 0, 0x1000006);
    if ((global29 & 0x1) != 0)
    {
        WorkModule(0x7, 0x12f, 0x11000002);
        WorkModule(0x2710, 0x2000002e);
    }
    else if ((global29 & 0x2) != 0)
    {
        WorkModule(0x7, 0x130, 0x11000002);
        WorkModule(0, -PostureModuleF(0) + 0, 0x1000006);
        WorkModule(0x2710, 0x2000002e);
    }
    else if ((global29 & 0x4) != 0)
    {
        WorkModule(0x7, 0x131, 0x11000002);
        WorkModule(0x2710, 0x2000002e);
    }
    else if ((global29 & 0x8) != 0)
    {
        WorkModule(0x7, 0x132, 0x11000002);
        WorkModule(0x2710, 0x2000002e);
    }
    else if ((global29 & 0x10) != 0)
    {
        WorkModule(0x7, 0x12d, 0x11000002);
    }
    else if ((global29 & 0x20) != 0)
    {
        WorkModule(0x7, 0x12e, 0x11000002);
    }
    else if ((global29 & 0x80000) != 0)
    {
        WorkModule(0x7, 0x12c, 0x11000002);
        WorkModule(0, -PostureModuleF(0) + 0, 0x1000006);
    }
    else
    {
        WorkModule(0x7, 0x12b, 0x11000002);
    }
    var0 = WorkModule(0x6, 0x11000002);
    var1 = WorkModuleF(0, 0x20000a7);
    func_22(var0, 0, var1);
    ControlModule(0x271f);
    func_75();
    func_76();
    ControlModule(0x271b);
    global24 = 0;
    global31 = 0;
    global29 = 0;
}

int func_1212()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x7d2, 0x8000000, 0, 0x10000);
    return 0;
}

void func_1213()
{
    KineticModule(0, 0xf);
    func_1211();
    func_78(func_1214);
}

void func_1214()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (global18 == 0 && MotionModule(0x2712) == 0x1)
    {
        func_16(0, 0);
        return;
    }
}

void func_1215()
{
    if (ItemModule(0x4))
    {
        if (ItemModule(0x24) == 0x1)
        {
            ItemModule(0x8);
        }
    }
}

int func_1216()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x8000000, 0, 0);
    return 0;
}

void func_1217()
{
    func_22(0x197, 0, 1.0f);
    BattleObject(0x23);
    func_78(func_1218);
}

void func_1218()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0, 0);
        return;
    }
    if (global9 == 12.0f)
    {
        ItemModule(0x14);
    }
}

void func_1219()
{
    if (ItemModule(0x11) == 0)
    {
        BattleObject(0x24, 0);
    }
}

int func_1220()
{
    StatusModule(0x5, 0x4, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0x782, 0x4403ea, 0x800, 0);
    return 0;
}

void func_1221()
{
    HitModule(0x2710, 0x2);
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    BattleObject(0x29);
    PostureModule(0x271b, 0);
    WorkModule(0x2710, 0x20000001);
    func_22(0x160, 0, 1.0f);
    func_78(func_1222);
}

void func_1222()
{
    
}

void func_1223()
{
    if (global6 != 0xd1)
    {
        WorkModule(0x2710, 0x2100000d);
        ItemModule(0x10, 0x1);
    }
}

int func_1224()
{
    StatusModule(0x5, 0x2, 0x1, 0x5, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0x782, 0, 0x800, 0);
    return 0;
}

void func_1225()
{
    func_40();
    func_564();
    func_22(0x1b, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_550();
    }
    global16 = func_550;
    func_78(func_1226);
}

void func_1226()
{
    if (func_56())
    {
        return 0x1;
    }
    if (func_41())
    {
        return;
    }
    if (func_565())
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return;
    }
}

void func_1227()
{
    
}

int func_1228()
{
    StatusModule(0x5, 0x4, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0x792, 0x4403ea, 0x800, 0);
    return 0;
}

void func_1229()
{
    HitModule(0x2710, 0x2);
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    BattleObject(0x29);
    WorkModule(0x2710, 0x20000001);
    func_22(0x15e, 0, 1.0f);
    WorkModule(0x2710, 0x20000065);
    func_78(func_1230);
}

void func_1230()
{
    if (MotionModule(0x2712))
    {
        BattleObject(0x30);
        CameraModule(0x2717, 0);
        func_22(0x15f, 0, 1.0f);
        callFunc3(func_1231);
        return;
    }
}

void func_1231()
{
    
}

void func_1232()
{
    CameraModule(0x2717, 0x1);
}

int func_1233()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0x822, 0x4403ea, 0x800, 0);
    return 0;
}

void func_1234()
{
    func_33();
    WorkModule(0, PostureModuleF(0), 0x1000006);
    ControlModule(0x271f);
    func_75();
    func_76();
    ControlModule(0x271b);
    DamageModule(0xb, 0x1, (float)0 + 0);
    VisibilityModule(0x2710, 0);
    MotionModule(0x4, 0);
    ItemModule(0x10, 0);
    ItemModule(0xe, 0x6a, 0, 0, 0x1);
    func_78(func_1235);
}

void func_1235()
{
    
}

void func_1236()
{
    if (global6 != 0x10e)
    {
        ItemModule(0x1d, 0);
        LinkModule(0x9, 0, 0, 0, 0, 0, 0);
        LinkModule(0x2717, 0x3);
    }
    VisibilityModule(0x2710, 0x1);
}

int func_1237()
{
    StatusModule(0x5, 0x2, 0x32, 0x5, 0x4, 0x1, 0, 0, 0x40, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0, 0, 0);
    return 0;
}

void func_1238()
{
    func_40();
    func_564();
    func_22(0xd3, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_550();
    }
    global16 = func_550;
    func_78(func_1239);
}

void func_1239()
{
    if (func_56())
    {
        return 0x1;
    }
    if (func_41())
    {
        return;
    }
    if (func_565())
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return;
    }
}

void func_1240()
{
    
}

void func_1241()
{
    float var0;
    float var1;
    var0 = WorkModuleF(0, 0x1000006);
    ModelModule(0x1, 0x2, var0 + 90.0f, 0, 0, 0x1);
    var1 = WorkModuleF(0, 0x2000306) * func_13(MathF(0x4, var0 * M_PI / (float)0xb4));
    func_1318(var1, WorkModuleF(0, 0x2000307));
}

void func_1242()
{
    float var0;
    var0 = WorkModuleF(0, 0x1000006);
    ModelModule(0x1, 0x2, var0 + 90.0f, 0, 0, 0x1);
}

void func_1243()
{
    float var0;
    var0 = WorkModuleF(0, 0x1000006);
    ModelModule(0x1, 0x2, var0 + 90.0f, 0, 0, 0x1);
}

void func_1244()
{
    ModelModule(0x2, 0x2);
}

void func_1245()
{
    if (global18 == 0)
    {
        if (global24 & 0x200000)
        {
            func_16(0xd6, 0x1);
            return;
        }
        if (global24 & 0x100000 && ControlModule(0x271c))
        {
            func_16(0xd6, 0x1);
            return;
        }
    }
}

void func_1246()
{
    if (func_34())
    {
        if (global31 & 0x200)
        {
            func_676();
        }
    }
}

void func_1247()
{
    func_1246();
}

void func_1248()
{
    int var0;
    float var1;
    BattleObject(0x23);
    var0 = WorkModule(0x6, 0x11000007);
    if (FighterUtil(0xa))
    {
        var1 = MotionModuleF(0x9);
        func_23(var0);
        MotionModule(0x4, var1);
    }
    else
    {
        func_22(var0, 0, 1.0f);
        if (ItemModule(0x11) == 0x30)
        {
            MotionModule(0x4, 2.0f);
        }
    }
}

void func_1249()
{
    if (WorkModule(0x10, 0x2000000b))
    {
        BattleObject(0x24, 0x2);
    }
}

void func_1250()
{
    func_1249();
    if (TurnModule(0) && !TurnModule(0x1))
    {
        TurnModule(0x2711);
    }
}

int func_1251()
{
    int var0;
    if (global5 == 0xd4 || global5 == 0xd5 || global5 == 0xd9)
    {
        var0 = 0x40;
    }
    else
    {
        var0 = 0;
    }
    StatusModule(0x5, 0, 0xf, 0x3, 0, 0x1, 0x1c000, 0x18, 0, var0);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0x772, 0x10, 0x800, 0);
    return 0;
}

void func_1252()
{
    WorkModule(0x7, 0x155, 0x11000007);
    func_1248();
    if (!StopModule(0x1))
    {
        func_1247();
    }
    global16 = func_1247;
    func_78(func_1253);
}

int func_1253()
{
    if (WorkModule(0x10, 0x2000000b) == 0 && global18 == 0)
    {
        func_16(0, 0);
        return 0;
    }
    if (global18 == 0x2)
    {
        func_16(0xd8, 0);
        return 0;
    }
    if (global18 == 0)
    {
        if (func_88() <= WorkModuleF(0, 0x2000006))
        {
            func_16(0xd5, 0x1);
            return 0;
        }
    }
    if (global18 == 0)
    {
        if (func_88() >= WorkModuleF(0, 0x2000001))
        {
            func_16(0xd4, 0x1);
            return 0;
        }
    }
    func_1245();
    func_1005();
    return 0;
}

int func_1254()
{
    func_1249();
    return 0;
}

int func_1255()
{
    StatusModule(0x5, 0, 0xf, 0x3, 0, 0x1, 0x1c000, 0x18, 0, 0x40);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0x772, 0x10, 0x800, 0x8000000);
    return 0;
}

void func_1256()
{
    WorkModule(0x7, 0x156, 0x11000007);
    func_1248();
    if (!StopModule(0x1))
    {
        func_1247();
    }
    global16 = func_1247;
    func_78(func_1257);
}

int func_1257()
{
    if (WorkModule(0x10, 0x2000000b) == 0 && global18 == 0)
    {
        func_16(0, 0);
        return 0;
    }
    if (global18 == 0x2)
    {
        func_16(0xd8, 0);
        return 0;
    }
    if (global18 == 0)
    {
        if (func_84() < WorkModuleF(0, 0x2000001))
        {
            func_16(0xd3, 0x1);
            return 0;
        }
        if (func_88() < 0)
        {
            func_16(0xd3, 0x1);
            return 0;
        }
    }
    func_1245();
    func_1005();
    return 0;
}

int func_1258()
{
    func_1249();
    return 0;
}

int func_1259()
{
    StatusModule(0x5, 0, 0xf, 0x3, 0, 0x1, 0x1c000, 0x18, 0, 0x40);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0x772, 0x10, 0x800, 0);
    return 0;
}

void func_1260()
{
    WorkModule(0x7, 0x156, 0x11000007);
    func_1248();
    TurnModule(0x2710, 0x3);
    if (!StopModule(0x1))
    {
        func_1247();
    }
    global16 = func_1247;
    func_78(func_1261);
}

int func_1261()
{
    if (!WorkModule(0x10, 0x2000000b) && global18 == 0)
    {
        func_16(0, 0);
        return 0;
    }
    if (global18 == 0x2)
    {
        func_16(0xd8, 0);
        return 0;
    }
    if (!TurnModule(0) && global18 == 0)
    {
        func_16(0xd3, 0);
        return 0;
    }
    func_1245();
    func_1005();
    return 0;
}

void func_1262()
{
    WorkModule(0x9, 0x11000002);
    if (WorkModule(0x10, 0x2100000d))
    {
        if (!(global24 & 0x15))
        {
            
        }
    }
    else if (global32 < (float)0x2000022)
    {
        
    }
}

int func_1263()
{
    func_1250();
    return 0;
}

int func_1264()
{
    StatusModule(0x5, 0, 0xf, 0x3, 0, 0x1, 0x1c000, 0x18, 0, 0x40);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0x772, 0x10, 0x800, 0);
    return 0;
}

void func_1265()
{
    WorkModule(0x7, 0x156, 0x11000007);
    func_1248();
    if (!StopModule(0x1))
    {
        func_1262();
    }
    global16 = func_1262;
    func_78(func_1266);
}

int func_1266()
{
    if (WorkModule(0x10, 0x2000000b) == 0 && global18 == 0)
    {
        func_16(0, 0);
        return 0;
    }
    if (global18 == 0)
    {
        if (WorkModule(0x6, 0x11000002) > WorkModule(0x6, 0x1300000c))
        {
            func_16(0xd7, 0);
            return 0;
        }
    }
    if (global18 == 0x2)
    {
        func_16(0xd8, 0);
        return 0;
    }
    if (global47 >= WorkModule(0x6, 0x12000020) || global49 <= 0)
    {
        WorkModule(0x11, 0x2100000d);
    }
    func_1005();
    return 0;
}

int func_1267()
{
    func_1249();
    return 0;
}

int func_1268()
{
    StatusModule(0x5, 0x2, 0x1, 0x5, 0, 0x1, 0x1c000, 0x18, 0, 0x40);
    StatusModule(0x2713, 0, 0, 0, 0, 0x1, 0x772, 0x10, 0x800, 0x4);
    return 0;
}

void func_1269()
{
    WorkModule(0x7, 0x157, 0x11000007);
    func_1248();
    func_78(func_1270);
}

int func_1270()
{
    if (WorkModule(0x10, 0x2000000b) == 0)
    {
        func_16(0xe, 0);
        return 0;
    }
    if (global18 == 0)
    {
        func_16(0xd9, 0);
        return 0;
    }
    func_1005();
    return 0;
}

int func_1271()
{
    func_1249();
    return 0;
}

int func_1272()
{
    StatusModule(0x5, 0x2, 0x13, 0x5, 0, 0x1, 0x1c000, 0x18, 0, 0x40);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0x1, 0x772, 0x10, 0x800, 0);
    return 0;
}

void func_1273()
{
    WorkModule(0x7, 0x157, 0x11000007);
    func_1248();
    func_78(func_1274);
}

int func_1274()
{
    if (!WorkModule(0x10, 0x2000000b))
    {
        func_16(0xe, 0);
        return 0;
    }
    if (global18 == 0)
    {
        func_16(0xd9, 0);
        return 0;
    }
    func_1005();
    return 0;
}

int func_1275()
{
    func_1249();
    return 0;
}

int func_1276()
{
    StatusModule(0x5, 0, 0xf, 0x3, 0, 0x1, 0x1c000, 0x18, 0, 0x40);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0x772, 0x10, 0x800, 0);
    return 0;
}

void func_1277()
{
    WorkModule(0x7, 0x156, 0x11000007);
    func_1248();
    if (!StopModule(0x1))
    {
        func_1279();
    }
    global16 = func_1279;
    func_78(func_1278);
}

int func_1278()
{
    if (global18 == 0)
    {
        if (WorkModule(0x6, 0x11000002) > WorkModule(0x6, 0x12000224))
        {
            func_16(0xd3, 0);
            return 0;
        }
    }
    if (global18 == 0x2)
    {
        func_16(0xd8, 0);
        return 0;
    }
    if (global18 == 0)
    {
        if (WorkModule(0x10, 0x2000000b) == 0)
        {
            func_16(0xd8, 0);
            return 0;
        }
    }
    func_1005();
    return 0;
}

void func_1279()
{
    WorkModule(0x9, 0x11000002);
}

int func_1280()
{
    func_1249();
    return 0;
}

void func_1281()
{
    if (global18 == 0)
    {
        GroundModule(0x2710, 0x1);
        KineticModule(0, 0x6);
    }
    else
    {
        GroundModule(0x2710, 0x5);
        KineticModule(0xc, 0);
        KineticModule(0xc, 0x1);
        KineticModule(0xc, 0x3);
        KineticModule(0xc, 0x2);
        KineticModule(0xc, 0x4);
    }
}

void func_1282()
{
    AreaModule(0x2710, 0);
    MotionModule(0x19, 0x1);
    if (global5 == 0xf)
    {
        WorkModule(0x7, 0xf, 0x11000005);
    }
    else if (global5 == 0x10)
    {
        WorkModule(0x7, 0x10, 0x11000005);
    }
    else
    {
        WorkModule(0x7, 0xe, 0x11000005);
    }
    func_1281();
}

void func_1283()
{
    if (StatusModule(0x6) == 0 && global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        func_1281();
    }
    if (WorkModule(0x6, 0x11000002) >= WorkModule(0x6, 0x11000003))
    {
        if (global18 == 0x2)
        {
            func_16(WorkModule(0x6, 0x11000005));
            return 0x1;
        }
        else if (global18 == 0)
        {
            if (MotionModule(0x2712))
            {
                func_16(0);
                return 0x1;
            }
        }
    }
}

void func_1284()
{
    if (global18 == 0x2)
    {
        KineticModule(0xb, 0x1);
        KineticModule(0xb, 0x2);
        KineticModule(0xb, 0x4);
        KineticModule(0x8, 0x2, 1.0f, 0);
    }
}

int func_1285()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0, 0x2, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0, 0, 0);
    return 0;
}

void func_1286()
{
    func_1282();
    func_78(func_1287);
}

void func_1287()
{
    if (func_1283())
    {
        return;
    }
}

void func_1288()
{
    func_1284();
}

int func_1289()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0, 0x2, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0, 0, 0);
    return 0;
}

void func_1290()
{
    func_1282();
    func_78(func_1291);
}

void func_1291()
{
    if (func_1283())
    {
        return;
    }
}

void func_1292()
{
    func_1284();
}

int func_1293()
{
    StatusModule(0x5, 0, 0x32, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x8000000, 0, 0);
    return 0;
}

void func_1294()
{
    func_22(0x199, 0, 1.0f);
    func_78(func_1295);
}

void func_1295()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (global18 == 0x2)
    {
        func_16(0x4c, 0);
        return;
    }
    if (MotionModule(0x2712) == 0x1 || WorkModule(0x10, 0x2100000d) && WorkModule(0x10, 0x2100000e))
    {
        func_16(0, 0);
        return;
    }
}

void func_1296()
{
    
}

int func_1297()
{
    StatusModule(0x5, 0x2, 0x53, 0x5, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0, 0, 0);
    return 0;
}

void func_1298()
{
    float var0;
    float var1;
    var0 = LinkModuleF(0x7, 0);
    PostureModule(0, -var0);
    PostureModule(0x2);
    func_22(0x89, 0, 1.0f);
    WorkModule(0x2710, 0x21000003);
    var1 = (float)WorkModule(0x6, 0x1200030a) + DamageModuleF(0) * WorkModuleF(0, 0x200030b);
    ControlModule(0x6, var1, WorkModuleF(0, 0x2000308), WorkModuleF(0, 0x2000309));
    func_78(func_1299);
}

void func_1299()
{
    if (ControlModuleF(0x5) <= 0)
    {
        func_16(0x43, 0);
    }
}

void func_1300()
{
    CaptureModule(0x1);
}

int func_1301()
{
    StatusModule(0x5, 0x2, 0x33, 0x5, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0, 0, 0);
    return 0;
}

void func_1302()
{
    float var0;
    int var1;
    var0 = -LinkModuleF(0x7, 0);
    PostureModule(0, var0);
    PostureModule(0x2);
    var1 = CaptureModule(0x8);
    WorkModule(0x7, var1, 0x11000002);
    CaptureModule(0x9, 0);
    func_22(0x2e, 0, 1.0f);
    WorkModule(0x2710, 0x21000003);
    func_78(func_1303);
}

void func_1303()
{
    float var0;
    if (WorkModule(0x10, 0x2100000d) && !WorkModule(0x10, 0x2100000e))
    {
        var0 = (float)WorkModule(0x6, 0x12000315) + DamageModuleF(0) * WorkModuleF(0, 0x2000316);
        ControlModule(0x6, var0, WorkModuleF(0, 0x2000313), WorkModuleF(0, 0x2000314));
        WorkModule(0x2710, 0x2100000e);
    }
    if (WorkModule(0x10, 0x2100000e))
    {
        if (ControlModuleF(0x5) <= 0)
        {
            func_16(0x43, 0);
        }
    }
}

void func_1304()
{
    int var0;
    CaptureModule(0x1);
    var0 = WorkModule(0x6, 0x11000002);
    CaptureModule(0x9, var0);
}

int func_1305()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0x2, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x1000010, 0, 0);
    return 0;
}

void func_1306()
{
    float var0;
    var0 = 6.0f;
    MotionModule(0x1, 0x19b, 0, 1.0f, var0);
    GroundModule(0x2710, 0x5);
    func_20(0x2);
    WorkModule(0x2711, 0x2000005c);
    if (!StopModule(0x1))
    {
        func_550();
    }
    global16 = func_550;
    func_78(func_1307);
}

void func_1307()
{
    if (func_56())
    {
        return 0x1;
    }
    if (WorkModule(0x6, 0x11000002) <= 0)
    {
        func_16(0x10b, 0);
        return;
    }
}

void func_1308()
{
    
}

int func_1309()
{
    StatusModule(0x5, 0x2, 0x32, 0x5, 0x2, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x1000010, 0, 0);
    return 0;
}

void func_1310()
{
    func_40();
    WorkModule(0x17, 0x1e00003e);
    WorkModule(0x17, 0x1e00003f);
    WorkModule(0x17, 0x1e000044);
    WorkModule(0x17, 0x1e000043);
    WorkModule(0x17, 0x1e000045);
    if (!StopModule(0x1))
    {
        func_550();
    }
    global16 = func_550;
    func_78(func_1311);
}

void func_1311()
{
    if (WorkModule(0x15, 0x1e00003e) == 0)
    {
        if (WorkModuleF(0, 0x1a) <= 0)
        {
            WorkModule(0x16, 0x1e00003e);
            WorkModule(0x16, 0x1e00003f);
            WorkModule(0x16, 0x1e000044);
            WorkModule(0x16, 0x1e000043);
            WorkModule(0x16, 0x1e000045);
        }
    }
    if (func_56())
    {
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00001b) && global18 == 0)
    {
        func_16(0x16, 0);
        return 0x1;
    }
    if (func_41())
    {
        return;
    }
}

void func_1312()
{
    
}

int func_1313()
{
    StatusModule(0x5, 0x2, 0x32, 0x5, 0x4, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0x2, 0, 0, 0);
    return 0;
}

void func_1314()
{
    func_40();
    func_564();
    func_22(0x19, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_550();
    }
    global16 = func_550;
    func_78(func_1315);
}

void func_1315()
{
    if (func_56())
    {
        return 0x1;
    }
    if (func_41())
    {
        return;
    }
    if (func_565())
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return;
    }
}

void func_1316()
{
    
}

void func_1317()
{
    func_1318(WorkModuleF(0, 0x2000302), WorkModuleF(0, 0x2000303));
}

void func_1318(float arg0, float arg1)
{
    float var2;
    float var3;
    float var4;
    float var5;
    var2 = KineticModuleF(0, 0x1);
    var3 = KineticModuleF(0x1, 0x1);
    var4 = PostureModuleF(0);
    var2 = var2 * WorkModuleF(0, 0x300000e) + arg0 * var4;
    var3 = var3 * WorkModuleF(0, 0x2000024) + arg1;
    var5 = WorkModuleF(0, 0x300000f);
    if (var2 > var5)
    {
        var2 = var5;
    }
    else if (var2 < -var5)
    {
        var2 = -var5;
    }
    KineticModule(0xe, 0x1, 0, 0, var3, 0, 0, 0);
    KineticModule(0xe, 0x2, 0, var2, 0, 0, 0, 0);
    KineticModule(0xb, 0x1);
    KineticModule(0xb, 0x2);
    KineticModule(0xc, 0);
    KineticModule(0xc, 0x3);
}

int func_1319()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x8000000, 0, 0);
    return 0;
}

void func_1320()
{
    func_22(0x198, 0, 1.0f);
    BattleObject(0x23);
    if (!StopModule(0x1))
    {
        func_1322();
    }
    global16 = func_1322;
    func_78(func_1321);
}

void func_1321()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
    }
    if (WorkModule(0x10, 0x2100000f) && MotionModule(0x2712) == 0x1)
    {
        func_16(0, 0);
        return;
    }
}

void func_1322()
{
    int var0;
    if (WorkModule(0x10, 0x2100000d) == 0)
    {
        return;
    }
    if (WorkModule(0x10, 0x2100000e) == 0)
    {
        MotionModule(0x4, 0);
        ItemModule(0x1d, 0);
        WorkModule(0x2710, 0x2100000e);
    }
    if (WorkModule(0x10, 0x2100000f) == 0)
    {
        var0 = ItemModule(0x1e, 0x1);
        if (var0 == 0)
        {
            BattleObject(0x62);
            MotionModule(0x4, 1.0f);
            ItemModule(0x1d, 0x1);
            WorkModule(0x2710, 0x2100000f);
        }
    }
}

void func_1323()
{
    if (ItemModule(0x11) == 0x6f)
    {
        BattleObject(0x24, 0);
    }
    if (WorkModule(0x10, 0x2100000e) == 0x1 && WorkModule(0x10, 0x2100000f) == 0)
    {
        ItemModule(0x1d, 0x2);
    }
}

void func_1324()
{
    
}

int func_1325()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return 0x1;
    }
    if (ItemModule(0x4) == 0)
    {
        if (global18 == 0x2)
        {
            func_16(0xe, 0);
            return 0x1;
        }
        else if (global18 == 0)
        {
            func_16(0, 0);
            return 0x1;
        }
    }
    return 0;
}

int func_1326()
{
    StatusModule(0x5, 0, 0xf, 0x3, 0, 0x1, 0x68020, 0x1fff8, 0x3c0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x1, 0x8000010, 0x4000, 0);
    return 0;
}

void func_1327()
{
    int var0;
    if (global5 == 0x8)
    {
        WorkModule(0x2710, 0x21000010);
        KineticModule(0, 0x7);
        KineticModule(0xb, 0);
    }
    else
    {
        WorkModule(0x2711, 0x21000010);
    }
    ControlModule(0x271b);
    func_1324();
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        func_1397();
    }
    else if (var0 == 0x24)
    {
        func_1419();
    }
    else if (var0 == 0x27)
    {
        func_1441();
    }
    else if (var0 == 0x6c)
    {
        func_1467();
    }
    else if (var0 == 0x29)
    {
        func_1397();
    }
    else if (var0 == 0x2d)
    {
        func_1489();
    }
    else if (var0 == 0x2b)
    {
        func_1397();
    }
    func_78(func_1328);
}

void func_1328()
{
    int var0;
    if (func_1325())
    {
        return;
    }
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        if (func_1398())
        {
            return;
        }
    }
    else if (var0 == 0x24)
    {
        if (func_1420())
        {
            return;
        }
    }
    else if (var0 == 0x27)
    {
        if (func_1442())
        {
            return;
        }
    }
    else if (var0 == 0x6c)
    {
        if (func_1468())
        {
            return;
        }
    }
    else if (var0 == 0x29)
    {
        if (func_1398())
        {
            return;
        }
    }
    else if (var0 == 0x2d)
    {
        if (func_1490())
        {
            return;
        }
    }
    else if (var0 == 0x2b)
    {
        if (func_1398())
        {
            return;
        }
    }
    if (global3 == 0)
    {
        func_1541();
    }
    func_1542();
}

void func_1329()
{
    
}

int func_1330()
{
    StatusModule(0x5, 0, 0xf, 0x3, 0, 0x1, 0x68020, 0x1fff8, 0x3c0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x1, 0x8000010, 0x4000, 0);
    return 0;
}

void func_1331()
{
    int var0;
    if (WorkModule(0x10, 0x21000010) == 0x1)
    {
        KineticModule(0, 0x7);
        KineticModule(0xb, 0);
    }
    func_1324();
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        func_1399();
    }
    else if (var0 == 0x24)
    {
        func_1421();
    }
    else if (var0 == 0x27)
    {
        func_1443();
    }
    else if (var0 == 0x6c)
    {
        func_1469();
    }
    else if (var0 == 0x29)
    {
        func_1399();
    }
    else if (var0 == 0x2d)
    {
        func_1491();
    }
    else if (var0 == 0x2b)
    {
        func_1399();
    }
    func_78(func_1332);
}

void func_1332()
{
    int var0;
    if (func_1325())
    {
        return;
    }
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        if (func_1400())
        {
            return;
        }
    }
    else if (var0 == 0x24)
    {
        if (func_1422())
        {
            return;
        }
    }
    else if (var0 == 0x27)
    {
        if (func_1444())
        {
            return;
        }
    }
    else if (var0 == 0x6c)
    {
        if (func_1470())
        {
            return;
        }
    }
    else if (var0 == 0x29)
    {
        if (func_1400())
        {
            return;
        }
    }
    else if (var0 == 0x2d)
    {
        if (func_1492())
        {
            return;
        }
    }
    else if (var0 == 0x2b)
    {
        if (func_1400())
        {
            return;
        }
    }
    if (global3 == 0)
    {
        func_1541();
    }
    func_1542();
}

void func_1333()
{
    
}

int func_1334()
{
    StatusModule(0x5, 0, 0xf, 0x3, 0, 0x1, 0x68020, 0x1fff8, 0x3c0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x1, 0x8000010, 0x4000, 0);
    return 0;
}

void func_1335()
{
    int var0;
    func_1324();
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        func_1403();
    }
    else if (var0 == 0x24)
    {
        func_1425();
    }
    else if (var0 == 0x27)
    {
        func_1447();
    }
    else if (var0 == 0x6c)
    {
        func_1473();
    }
    else if (var0 == 0x29)
    {
        func_1403();
    }
    else if (var0 == 0x2d)
    {
        func_1495();
    }
    else if (var0 == 0x2b)
    {
        func_1403();
    }
    func_78(func_1336);
}

void func_1336()
{
    int var0;
    if (func_1325())
    {
        return;
    }
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        if (func_1404())
        {
            return;
        }
    }
    else if (var0 == 0x24)
    {
        if (func_1426())
        {
            return;
        }
    }
    else if (var0 == 0x27)
    {
        if (func_1448())
        {
            return;
        }
    }
    else if (var0 == 0x6c)
    {
        if (func_1474())
        {
            return;
        }
    }
    else if (var0 == 0x29)
    {
        if (func_1404())
        {
            return;
        }
    }
    else if (var0 == 0x2d)
    {
        if (func_1496())
        {
            return;
        }
    }
    else if (var0 == 0x2b)
    {
        if (func_1404())
        {
            return;
        }
    }
    if (global3 == 0)
    {
        func_1541();
    }
    func_1542();
}

void func_1337()
{
    
}

int func_1338()
{
    StatusModule(0x5, 0, 0xf, 0x1, 0, 0x1, 0x68020, 0x1fff8, 0x3c0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x1, 0x8000010, 0x4000, 0);
    return 0;
}

void func_1339()
{
    int var0;
    func_1324();
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        func_1401();
    }
    else if (var0 == 0x24)
    {
        func_1423();
    }
    else if (var0 == 0x27)
    {
        func_1445();
    }
    else if (var0 == 0x6c)
    {
        func_1471();
    }
    else if (var0 == 0x29)
    {
        func_1401();
    }
    else if (var0 == 0x2d)
    {
        func_1493();
    }
    else if (var0 == 0x2b)
    {
        func_1401();
    }
    func_78(func_1340);
}

void func_1340()
{
    int var0;
    if (func_1325())
    {
        return;
    }
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        if (func_1402())
        {
            return;
        }
    }
    else if (var0 == 0x24)
    {
        if (func_1424())
        {
            return;
        }
    }
    else if (var0 == 0x27)
    {
        if (func_1446())
        {
            return;
        }
    }
    else if (var0 == 0x6c)
    {
        if (func_1472())
        {
            return;
        }
    }
    else if (var0 == 0x29)
    {
        if (func_1402())
        {
            return;
        }
    }
    else if (var0 == 0x2d)
    {
        if (func_1494())
        {
            return;
        }
    }
    else if (var0 == 0x2b)
    {
        if (func_1402())
        {
            return;
        }
    }
    if (global3 == 0)
    {
        func_1541();
    }
    func_1542();
}

void func_1341()
{
    
}

int func_1342()
{
    StatusModule(0x5, 0, 0xf, 0x1, 0, 0x1, 0x68020, 0x1fff8, 0x3c0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x1, 0x8000010, 0x4000, 0);
    return 0;
}

void func_1343()
{
    int var0;
    func_1324();
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        func_1405();
    }
    else if (var0 == 0x24)
    {
        func_1427();
    }
    else if (var0 == 0x27)
    {
        func_1449();
    }
    else if (var0 == 0x6c)
    {
        func_1475();
    }
    else if (var0 == 0x29)
    {
        func_1405();
    }
    else if (var0 == 0x2d)
    {
        func_1497();
    }
    else if (var0 == 0x2b)
    {
        func_1405();
    }
    func_78(func_1344);
}

void func_1344()
{
    int var0;
    if (func_1325())
    {
        return;
    }
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        if (func_1406())
        {
            return;
        }
    }
    else if (var0 == 0x24)
    {
        if (func_1428())
        {
            return;
        }
    }
    else if (var0 == 0x27)
    {
        if (func_1450())
        {
            return;
        }
    }
    else if (var0 == 0x6c)
    {
        if (func_1474())
        {
            return;
        }
    }
    else if (var0 == 0x29)
    {
        if (func_1406())
        {
            return;
        }
    }
    else if (var0 == 0x2d)
    {
        if (func_1498())
        {
            return;
        }
    }
    else if (var0 == 0x2b)
    {
        if (func_1406())
        {
            return;
        }
    }
    if (global3 == 0)
    {
        func_1541();
    }
    func_1542();
}

void func_1345()
{
    
}

int func_1346()
{
    StatusModule(0x5, 0, 0x32, 0x3, 0, 0x1, 0x68020, 0x1fff8, 0x3c0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x1, 0x8000010, 0x4000, 0);
    return 0;
}

void func_1347()
{
    int var0;
    if (WorkModule(0x10, 0x21000010) == 0x1)
    {
        KineticModule(0, 0x7);
        KineticModule(0xb, 0);
    }
    func_75();
    func_1324();
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        func_1407();
    }
    else if (var0 == 0x24)
    {
        func_1429();
    }
    else if (var0 == 0x27)
    {
        func_1451();
    }
    else if (var0 == 0x6c)
    {
        func_1477();
    }
    else if (var0 == 0x29)
    {
        func_1407();
    }
    else if (var0 == 0x2d)
    {
        func_1499();
    }
    else if (var0 == 0x2b)
    {
        func_1407();
    }
    func_78(func_1348);
}

void func_1348()
{
    int var0;
    if (func_1325())
    {
        return;
    }
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        if (func_1408())
        {
            return;
        }
    }
    else if (var0 == 0x24)
    {
        if (func_1430())
        {
            return;
        }
    }
    else if (var0 == 0x27)
    {
        if (func_1452())
        {
            return;
        }
    }
    else if (var0 == 0x6c)
    {
        if (func_1478())
        {
            return;
        }
    }
    else if (var0 == 0x29)
    {
        if (func_1408())
        {
            return;
        }
    }
    else if (var0 == 0x2d)
    {
        if (func_1500())
        {
            return;
        }
    }
    else if (var0 == 0x2b)
    {
        if (func_1408())
        {
            return;
        }
    }
    if (global3 == 0)
    {
        func_1541();
    }
    func_1542();
}

void func_1349()
{
    
}

int func_1350()
{
    StatusModule(0x5, 0, 0x32, 0x3, 0, 0x1, 0x68020, 0x1fff8, 0x3c0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x1, 0x8000010, 0x4000, 0);
    return 0;
}

void func_1351()
{
    int var0;
    func_75();
    func_1324();
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        func_1409();
    }
    else if (var0 == 0x24)
    {
        func_1431();
    }
    else if (var0 == 0x27)
    {
        func_1453();
    }
    else if (var0 == 0x6c)
    {
        func_1479();
    }
    else if (var0 == 0x29)
    {
        func_1409();
    }
    else if (var0 == 0x2d)
    {
        func_1501();
    }
    else if (var0 == 0x2b)
    {
        func_1409();
    }
    func_78(func_1352);
}

void func_1352()
{
    int var0;
    if (func_1325())
    {
        return;
    }
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        if (func_1410())
        {
            return;
        }
    }
    else if (var0 == 0x24)
    {
        if (func_1432())
        {
            return;
        }
    }
    else if (var0 == 0x27)
    {
        if (func_1454())
        {
            return;
        }
    }
    else if (var0 == 0x6c)
    {
        if (func_1480())
        {
            return;
        }
    }
    else if (var0 == 0x29)
    {
        if (func_1410())
        {
            return;
        }
    }
    else if (var0 == 0x2d)
    {
        if (func_1502())
        {
            return;
        }
    }
    else if (var0 == 0x2b)
    {
        if (func_1410())
        {
            return;
        }
    }
    if (global3 == 0)
    {
        func_1541();
    }
    func_1542();
}

void func_1353()
{
    
}

int func_1354()
{
    int var0;
    if (ItemModule(0x11) == 0x6c)
    {
        var0 = 0x4;
    }
    else
    {
        var0 = 0;
    }
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, var0, 0x1, 0x68020, 0x1fff8, 0x3c0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0x1, 0x1, 0x8000010, 0x4000, 0);
    return 0;
}

void func_1355()
{
    func_75();
    func_1324();
    if (global18 == 0)
    {
        func_676();
    }
    func_94();
}

void func_1356()
{
    int var0;
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        func_1393();
    }
    else if (var0 == 0x24)
    {
        func_1415();
    }
    else if (var0 == 0x27)
    {
        func_1437();
    }
    else if (var0 == 0x6c)
    {
        func_1460();
    }
    else if (var0 == 0x29)
    {
        func_1393();
    }
    else if (var0 == 0x2d)
    {
        func_1485();
    }
    else if (var0 == 0x2b)
    {
        func_1393();
    }
}

void func_1357()
{
    func_1355();
    KineticModule(0, 0x13);
    func_1356();
    func_78(func_1358);
}

void func_1358()
{
    int var0;
    if (func_1325())
    {
        return;
    }
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        if (func_1394())
        {
            return;
        }
    }
    else if (var0 == 0x24)
    {
        if (func_1416())
        {
            return;
        }
    }
    else if (var0 == 0x27)
    {
        if (func_1438())
        {
            return;
        }
    }
    else if (var0 == 0x6c)
    {
        if (func_1461())
        {
            return;
        }
    }
    else if (var0 == 0x29)
    {
        if (func_1394())
        {
            return;
        }
    }
    else if (var0 == 0x2d)
    {
        if (func_1486())
        {
            return;
        }
    }
    else if (var0 == 0x2b)
    {
        if (func_1394())
        {
            return;
        }
    }
    if (global3 == 0)
    {
        func_1541();
    }
    func_1542();
}

void func_1359()
{
    
}

int func_1360()
{
    StatusModule(0x5, 0, 0xf, 0x3, 0, 0x1, 0x68020, 0x1fff8, 0x3c0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x1, 0x8000010, 0x4000, 0);
    return 0;
}

void func_1361()
{
    int var0;
    WorkModule(0x2711, 0x21000005);
    if (global32 >= (float)WorkModule(0x6, 0x12000020) || global49 <= 0)
    {
        WorkModule(0x2710, 0x2100000e);
    }
    func_75();
    func_1324();
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        func_1411();
    }
    else if (var0 == 0x24)
    {
        func_1433();
    }
    else if (var0 == 0x27)
    {
        func_1455();
    }
    else if (var0 == 0x6c)
    {
        func_1481();
    }
    else if (var0 == 0x29)
    {
        func_1411();
    }
    else if (var0 == 0x2d)
    {
        func_1503();
    }
    else if (var0 == 0x2b)
    {
        func_1411();
    }
    if (!StopModule(0x1))
    {
        func_1363();
    }
    global16 = func_1363;
    func_78(func_1362);
}

void func_1362()
{
    int var0;
    if (func_1325())
    {
        return;
    }
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        if (func_1412())
        {
            return;
        }
    }
    else if (var0 == 0x24)
    {
        if (func_1434())
        {
            return;
        }
    }
    else if (var0 == 0x27)
    {
        if (func_1456())
        {
            return;
        }
    }
    else if (var0 == 0x6c)
    {
        if (func_1482())
        {
            return;
        }
    }
    else if (var0 == 0x29)
    {
        if (func_1412())
        {
            return;
        }
    }
    else if (var0 == 0x2d)
    {
        if (func_1504())
        {
            return;
        }
    }
    else if (var0 == 0x2b)
    {
        if (func_1412())
        {
            return;
        }
    }
    if (global3 == 0)
    {
        func_1541();
    }
    func_1542();
}

void func_1363()
{
    func_547(0x2100000e);
}

void func_1364()
{
    
}

int func_1365()
{
    int var0;
    if (ItemModule(0x11) == 0x6c)
    {
        var0 = 0x4;
    }
    else
    {
        var0 = 0;
    }
    StatusModule(0x5, 0x2, 0x1, 0x5, var0, 0x1, 0x68020, 0x1fff8, 0x3c0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0x1, 0x1, 0x8000010, 0x4000, 0);
    return 0;
}

void func_1366()
{
    int var0;
    func_1324();
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        func_1395();
    }
    else if (var0 == 0x24)
    {
        func_1417();
    }
    else if (var0 == 0x27)
    {
        func_1439();
    }
    else if (var0 == 0x6c)
    {
        func_1462();
    }
    else if (var0 == 0x29)
    {
        func_1395();
    }
    else if (var0 == 0x2d)
    {
        func_1487();
    }
    else if (var0 == 0x2b)
    {
        func_1395();
    }
    func_78(func_1367);
}

void func_1367()
{
    int var0;
    if (func_1325())
    {
        return;
    }
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        if (func_1396())
        {
            return;
        }
    }
    else if (var0 == 0x24)
    {
        if (func_1418())
        {
            return;
        }
    }
    else if (var0 == 0x27)
    {
        if (func_1440())
        {
            return;
        }
    }
    else if (var0 == 0x6c)
    {
        if (func_1463())
        {
            return;
        }
    }
    else if (var0 == 0x29)
    {
        if (func_1396())
        {
            return;
        }
    }
    else if (var0 == 0x2d)
    {
        if (func_1488())
        {
            return;
        }
    }
    else if (var0 == 0x2b)
    {
        if (func_1396())
        {
            return;
        }
    }
    if (global3 == 0)
    {
        func_1541();
    }
    func_1542();
}

void func_1368()
{
    
}

int func_1369()
{
    StatusModule(0x5, 0, 0xf, 0x3, 0, 0x1, 0x68020, 0x1fff8, 0x3c0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x1, 0x8000010, 0x4000, 0);
    return 0;
}

void func_1370()
{
    int var0;
    WorkModule(0x2711, 0x20000003);
    func_1324();
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        func_1413();
    }
    else if (var0 == 0x24)
    {
        func_1435();
    }
    else if (var0 == 0x27)
    {
        func_1457();
    }
    else if (var0 == 0x6c)
    {
        func_1483();
    }
    else if (var0 == 0x29)
    {
        func_1413();
    }
    else if (var0 == 0x2d)
    {
        func_1505();
    }
    else if (var0 == 0x2b)
    {
        func_1413();
    }
    func_78(func_1371);
}

void func_1371()
{
    int var0;
    if (func_1325())
    {
        return;
    }
    var0 = ItemModule(0x11);
    if (var0 == 0x25)
    {
        if (func_1414())
        {
            return;
        }
    }
    else if (var0 == 0x24)
    {
        if (func_1436())
        {
            return;
        }
    }
    else if (var0 == 0x27)
    {
        if (func_1458())
        {
            return;
        }
    }
    else if (var0 == 0x6c)
    {
        if (func_1484())
        {
            return;
        }
    }
    else if (var0 == 0x29)
    {
        if (func_1414())
        {
            return;
        }
    }
    else if (var0 == 0x2d)
    {
        if (func_1506())
        {
            return;
        }
    }
    else if (var0 == 0x2b)
    {
        if (func_1414())
        {
            return;
        }
    }
    if (global3 == 0)
    {
        func_1541();
    }
    func_1542();
}

void func_1372()
{
    
}

void func_1373()
{
    WorkModule(0x2711, 0x2100000f);
    WorkModule(0x16, 0x1e00008a);
    WorkModule(0x16, 0x1e00008b);
    WorkModule(0x16, 0x1e00008c);
    WorkModule(0x16, 0x1e00008d);
    WorkModule(0x16, 0x1e00002d);
    WorkModule(0x16, 0x1e000088);
    WorkModule(0x16, 0x1e000031);
    WorkModule(0x16, 0x1e000089);
    WorkModule(0x16, 0x1e000084);
    WorkModule(0x16, 0x1e000086);
}

int func_1374()
{
    int var0;
    if (WorkModule(0x15, 0x1e00008a) && global18 == 0x2)
    {
        var0 = WorkModule(0x6, 0x1100000a);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008b) && WorkModule(0x10, 0x2100000d))
    {
        var0 = WorkModule(0x6, 0x1100000a);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008c) && global24 & 0x200000)
    {
        var0 = WorkModule(0x6, 0x1100000c);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008d) && global24 & 0x100000 && ControlModule(0x271c))
    {
        var0 = WorkModule(0x6, 0x1100000c);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00002d) && WorkModule(0x10, 0x2100000f) && global24 & 0x20000)
    {
        func_16(0x3, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000088) && global24 & 0x20000)
    {
        var0 = WorkModule(0x6, 0x11000008);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000031) && WorkModule(0x10, 0x2100000f) && global24 & 0x80000)
    {
        func_16(0x7, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000089) && global24 & 0x80000)
    {
        var0 = WorkModule(0x6, 0x11000009);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000084) && func_88() >= WorkModuleF(0, 0x2000001))
    {
        var0 = WorkModule(0x6, 0x11000004);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000086) && func_89() >= WorkModuleF(0, 0x2000001))
    {
        var0 = WorkModule(0x6, 0x11000005);
        func_16(var0, 0x1);
        return 0x1;
    }
    return 0;
}

void func_1375()
{
    WorkModule(0x16, 0x1e00008a);
    WorkModule(0x16, 0x1e00008b);
    WorkModule(0x16, 0x1e00008c);
    WorkModule(0x16, 0x1e00008d);
    WorkModule(0x16, 0x1e00002d);
    WorkModule(0x16, 0x1e000088);
    WorkModule(0x16, 0x1e000083);
}

int func_1376()
{
    int var0;
    if (WorkModule(0x15, 0x1e00008a) && global18 == 0x2)
    {
        var0 = WorkModule(0x6, 0x1100000a);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008b) && WorkModule(0x10, 0x2100000d))
    {
        var0 = WorkModule(0x6, 0x1100000a);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008c) && global24 & 0x200000)
    {
        var0 = WorkModule(0x6, 0x1100000c);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008d) && global24 & 0x100000 && ControlModule(0x271c))
    {
        var0 = WorkModule(0x6, 0x1100000c);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00002d) && WorkModule(0x10, 0x2100000f) && global24 & 0x20000)
    {
        func_16(0x3, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000088) && global24 & 0x20000)
    {
        var0 = WorkModule(0x6, 0x11000008);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (func_84() < WorkModuleF(0, 0x2000001) && GroundModuleF(0) < 1.0f)
    {
        var0 = WorkModule(0x6, 0x11000006);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (func_88() < 0 && GroundModuleF(0) < 1.0f)
    {
        var0 = WorkModule(0x6, 0x11000006);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000083) && func_88() < WorkModuleF(0, 0x2000001))
    {
        var0 = WorkModule(0x6, 0x11000003);
        func_16(var0, 0x1);
        return 0x1;
    }
    return 0;
}

void func_1377()
{
    WorkModule(0x16, 0x1e00008a);
    WorkModule(0x16, 0x1e00008b);
    WorkModule(0x16, 0x1e00008c);
    WorkModule(0x16, 0x1e00008d);
    WorkModule(0x16, 0x1e000031);
    WorkModule(0x16, 0x1e000089);
    WorkModule(0x16, 0x1e000083);
}

int func_1378()
{
    int var0;
    if (WorkModule(0x15, 0x1e00008a) && global18 == 0x2)
    {
        var0 = WorkModule(0x6, 0x1100000a);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008b) && WorkModule(0x10, 0x2100000d))
    {
        var0 = WorkModule(0x6, 0x1100000a);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008c) && global24 & 0x200000)
    {
        var0 = WorkModule(0x6, 0x1100000c);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008d) && global24 & 0x100000 && ControlModule(0x271c))
    {
        var0 = WorkModule(0x6, 0x1100000c);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000031) && WorkModule(0x10, 0x2100000f) && global24 & 0x80000)
    {
        func_16(0x7, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000089) && global24 & 0x80000)
    {
        var0 = WorkModule(0x6, 0x11000009);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (func_84() < WorkModuleF(0, 0x2000001) && GroundModuleF(0) < 1.0f)
    {
        var0 = WorkModule(0x6, 0x11000007);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (func_89() < 0 && GroundModuleF(0) < 1.0f)
    {
        var0 = WorkModule(0x6, 0x11000007);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000083) && func_89() < WorkModuleF(0, 0x2000001))
    {
        var0 = WorkModule(0x6, 0x11000003);
        func_16(var0, 0x1);
        return 0x1;
    }
    return 0;
}

void func_1379()
{
    func_22(0x167, 0, 1.0f);
    MotionModule(0x30);
    WorkModule(0x16, 0x1e00008a);
    WorkModule(0x16, 0x1e00008b);
    WorkModule(0x16, 0x1e00008c);
    WorkModule(0x16, 0x1e00008d);
    WorkModule(0x16, 0x1e000083);
    WorkModule(0x16, 0x1e000084);
    WorkModule(0x16, 0x1e000086);
}

int func_1380()
{
    int var0;
    if (WorkModule(0x15, 0x1e00008a) && global18 == 0x2)
    {
        var0 = WorkModule(0x6, 0x1100000a);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008b) && WorkModule(0x10, 0x2100000d))
    {
        var0 = WorkModule(0x6, 0x1100000a);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008c) && global24 & 0x200000)
    {
        var0 = WorkModule(0x6, 0x1100000c);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008d) && global24 & 0x100000 && ControlModule(0x271c))
    {
        var0 = WorkModule(0x6, 0x1100000c);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008c) && MotionModule(0x2712))
    {
        var0 = WorkModule(0x6, 0x11000003);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000084) && func_88() >= WorkModuleF(0, 0x2000001))
    {
        var0 = WorkModule(0x6, 0x11000004);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000086) && func_89() >= WorkModuleF(0, 0x2000001))
    {
        var0 = WorkModule(0x6, 0x11000005);
        func_16(var0, 0x1);
        return 0x1;
    }
    return 0;
}

void func_1381()
{
    func_22(0x16c, 0, 1.0f);
    MotionModule(0x30);
    WorkModule(0x16, 0x1e00008a);
    WorkModule(0x16, 0x1e00008b);
    WorkModule(0x16, 0x1e00008c);
    WorkModule(0x16, 0x1e00008d);
    WorkModule(0x16, 0x1e000083);
    WorkModule(0x16, 0x1e000084);
    WorkModule(0x16, 0x1e000086);
}

int func_1382()
{
    int var0;
    if (WorkModule(0x15, 0x1e00008a) && global18 == 0x2)
    {
        var0 = WorkModule(0x6, 0x1100000a);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008b) && WorkModule(0x10, 0x2100000d))
    {
        var0 = WorkModule(0x6, 0x1100000a);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008c) && global24 & 0x200000)
    {
        var0 = WorkModule(0x6, 0x1100000c);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008d) && global24 & 0x100000 && ControlModule(0x271c))
    {
        var0 = WorkModule(0x6, 0x1100000c);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000083) && MotionModule(0x2712))
    {
        var0 = WorkModule(0x6, 0x11000003);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000084) && func_88() >= WorkModuleF(0, 0x2000001))
    {
        var0 = WorkModule(0x6, 0x11000004);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000086) && func_89() >= WorkModuleF(0, 0x2000001))
    {
        var0 = WorkModule(0x6, 0x11000005);
        func_16(var0, 0x1);
        return 0x1;
    }
    return 0;
}

void func_1383()
{
    float var0;
    var0 = func_88();
    if (var0 < 0)
    {
        TurnModule(0x2710, 0x2, 0);
        PostureModule(0x271c);
    }
    if (WorkModule(0x10, 0x21000010) == 0)
    {
        KineticModule(0, 0x1c);
    }
    func_22(0x168, 0, 1.0f);
    WorkModule(0x16, 0x1e00008a);
    WorkModule(0x16, 0x1e00008c);
    WorkModule(0x16, 0x1e00008d);
    WorkModule(0x16, 0x1e000083);
}

int func_1384()
{
    int var0;
    if (WorkModule(0x15, 0x1e00008a) && global18 == 0x2)
    {
        var0 = WorkModule(0x6, 0x1100000a);
        func_16(var0, 0);
        return 0x1;
    }
    if (MotionModule(0x2712) && GroundModuleF(0) < 1.0f)
    {
        var0 = WorkModule(0x6, 0x11000006);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008c) && global24 & 0x200000)
    {
        var0 = WorkModule(0x6, 0x1100000c);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008d) && global24 & 0x100000 && ControlModule(0x271c))
    {
        var0 = WorkModule(0x6, 0x1100000c);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000083) && MotionModule(0x2712))
    {
        var0 = WorkModule(0x6, 0x11000003);
        func_16(var0, 0);
        return 0x1;
    }
    return 0;
}

void func_1385()
{
    KineticModule(0, 0x1d);
    func_22(0x16d, 0, 1.0f);
    WorkModule(0x16, 0x1e00008a);
    WorkModule(0x16, 0x1e00008c);
    WorkModule(0x16, 0x1e00008d);
    WorkModule(0x16, 0x1e000083);
}

int func_1386()
{
    int var0;
    if (WorkModule(0x15, 0x1e00008a) && global18 == 0x2)
    {
        var0 = WorkModule(0x6, 0x1100000a);
        func_16(var0, 0);
        return 0x1;
    }
    if (MotionModule(0x2712) && GroundModuleF(0) < 1.0f)
    {
        var0 = WorkModule(0x6, 0x11000007);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008c) && global24 & 0x200000)
    {
        var0 = WorkModule(0x6, 0x1100000c);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008d) && global24 & 0x100000 && ControlModule(0x271c))
    {
        var0 = WorkModule(0x6, 0x1100000c);
        func_16(var0, 0x1);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000083) && MotionModule(0x2712))
    {
        var0 = WorkModule(0x6, 0x11000003);
        func_16(var0, 0);
        return 0x1;
    }
    return 0;
}

void func_1387()
{
    func_22(0x16e, 0, 1.0f);
    WorkModule(0x16, 0x1e00008a);
    WorkModule(0x16, 0x1e00008d);
}

int func_1388()
{
    int var0;
    if (WorkModule(0x15, 0x1e00008a) && global18 == 0x2)
    {
        var0 = WorkModule(0x6, 0x1100000a);
        func_16(var0, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e00008d) && MotionModule(0x2712))
    {
        var0 = WorkModule(0x6, 0x1100000b);
        func_16(var0, 0);
        return 0x1;
    }
    return 0;
}

void func_1389()
{
    func_22(0x16f, 0, 1.0f);
    func_1373();
    WorkModule(0x16, 0x1e000083);
}

int func_1390()
{
    int var0;
    if (WorkModule(0x15, 0x1e00008a) && global18 == 0x2)
    {
        var0 = WorkModule(0x6, 0x1100000a);
        func_16(var0, 0);
        return 0x1;
    }
    if (MotionModuleF(0x1) > WorkModuleF(0, 0x3000028))
    {
        if (WorkModule(0x15, 0x1e00008b) && WorkModule(0x10, 0x2100000d))
        {
            var0 = WorkModule(0x6, 0x1100000a);
            func_16(var0, 0);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e00008c) && global24 & 0x200000)
        {
            var0 = WorkModule(0x6, 0x1100000c);
            func_16(var0, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e00008d) && global24 & 0x100000 && ControlModule(0x271c))
        {
            var0 = WorkModule(0x6, 0x1100000c);
            func_16(var0, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e00002d) && WorkModule(0x10, 0x2100000f) && global24 & 0x20000)
        {
            func_16(0x3, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000088) && global24 & 0x20000)
        {
            var0 = WorkModule(0x6, 0x11000008);
            func_16(var0, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000031) && WorkModule(0x10, 0x2100000f) && global24 & 0x80000)
        {
            func_16(0x7, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000089) && global24 & 0x80000)
        {
            var0 = WorkModule(0x6, 0x11000009);
            func_16(var0, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000084) && func_88() >= WorkModuleF(0, 0x2000001))
        {
            var0 = WorkModule(0x6, 0x11000004);
            func_16(var0, 0x1);
            return 0x1;
        }
        if (WorkModule(0x15, 0x1e000086) && func_89() >= WorkModuleF(0, 0x2000001))
        {
            var0 = WorkModule(0x6, 0x11000005);
            func_16(var0, 0x1);
            return 0x1;
        }
    }
    if (WorkModule(0x15, 0x1e000083) && MotionModule(0x2712))
    {
        var0 = WorkModule(0x6, 0x11000003);
        func_16(var0, 0);
        return 0x1;
    }
    return 0;
}

void func_1391()
{
    WorkModule(0x16, 0x1e00008f);
}

int func_1392()
{
    int var0;
    if (WorkModule(0x15, 0x1e00008f) && global18 == 0)
    {
        var0 = WorkModule(0x6, 0x1100000d);
        func_16(var0, 0);
        return 0x1;
    }
    return 0;
}

void func_1393()
{
    func_1391();
}

int func_1394()
{
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return 0x1;
    }
    return func_1392();
}

void func_1395()
{
    func_1391();
}

int func_1396()
{
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return 0x1;
    }
    return func_1392();
}

void func_1397()
{
    WorkModule(0x16, 0x1e000000);
    func_1373();
}

int func_1398()
{
    if (WorkModule(0x15, 0x1e000000) && MotionModule(0x1a, 0x1) && global18 == 0)
    {
        func_16(0, 0);
        return 0x1;
    }
    return func_1374();
}

void func_1399()
{
    WorkModule(0x16, 0x1e00003c);
    func_1375();
}

int func_1400()
{
    if (WorkModule(0x15, 0x1e00003c) && MotionModule(0x1a, 0x1) && global18 == 0)
    {
        func_16(0x1, 0);
        return 0x1;
    }
    return func_1376();
}

void func_1401()
{
    WorkModule(0x16, 0x1e00003c);
    func_1377();
}

int func_1402()
{
    if (WorkModule(0x15, 0x1e00003c) && MotionModule(0x1a, 0x1) && global18 == 0)
    {
        func_16(0x1, 0);
        return 0x1;
    }
    return func_1378();
}

void func_1403()
{
    func_1379();
}

int func_1404()
{
    return func_1380();
}

void func_1405()
{
    func_1381();
}

int func_1406()
{
    return func_1382();
}

void func_1407()
{
    func_1383();
}

int func_1408()
{
    return func_1384();
}

void func_1409()
{
    func_1385();
}

int func_1410()
{
    return func_1386();
}

void func_1411()
{
    func_1387();
}

int func_1412()
{
    return func_1388();
}

void func_1413()
{
    func_1389();
}

int func_1414()
{
    return func_1390();
}

void func_1415()
{
    func_1391();
}

int func_1416()
{
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return 0x1;
    }
    return func_1392();
}

void func_1417()
{
    func_1391();
}

int func_1418()
{
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return 0x1;
    }
    return func_1392();
}

void func_1419()
{
    WorkModule(0x16, 0x1e000000);
    func_1373();
}

int func_1420()
{
    if (WorkModule(0x15, 0x1e000000) && MotionModule(0x1a, 0x1) && global18 == 0)
    {
        func_16(0, 0);
        return 0x1;
    }
    return func_1374();
}

void func_1421()
{
    WorkModule(0x16, 0x1e00003c);
    func_1375();
}

int func_1422()
{
    if (WorkModule(0x15, 0x1e00003c) && MotionModule(0x1a, 0x1) && global18 == 0)
    {
        func_16(0x1, 0);
        return 0x1;
    }
    return func_1376();
}

void func_1423()
{
    WorkModule(0x16, 0x1e00003c);
    func_1377();
}

int func_1424()
{
    if (WorkModule(0x15, 0x1e00003c) && MotionModule(0x1a, 0x1) && global18 == 0)
    {
        func_16(0x1, 0);
        return 0x1;
    }
    return func_1378();
}

void func_1425()
{
    func_1379();
}

int func_1426()
{
    return func_1380();
}

void func_1427()
{
    func_1381();
}

int func_1428()
{
    return func_1382();
}

void func_1429()
{
    func_1383();
}

int func_1430()
{
    return func_1384();
}

void func_1431()
{
    func_1385();
}

int func_1432()
{
    return func_1386();
}

void func_1433()
{
    func_1387();
}

int func_1434()
{
    return func_1388();
}

void func_1435()
{
    func_1389();
}

int func_1436()
{
    return func_1390();
}

void func_1437()
{
    WorkModule(0x16, 0x1e000002);
    func_1391();
}

int func_1438()
{
    if (WorkModule(0x15, 0x1e000002) && MotionModule(0x2712) && WorkModule(0x6, 0x1100000e) >= 0x3)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    return func_1392();
}

void func_1439()
{
    WorkModule(0x16, 0x1e000002);
    func_1391();
}

int func_1440()
{
    if (WorkModule(0x15, 0x1e000002) && MotionModule(0x2712) && WorkModule(0x6, 0x1100000e) >= 0x3)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    return func_1392();
}

void func_1441()
{
    WorkModule(0x16, 0x1e000000);
    func_1373();
}

int func_1442()
{
    if (WorkModule(0x15, 0x1e000000) && MotionModule(0x1a, 0x1) && WorkModule(0x6, 0x1100000e) >= 0x3 && global18 == 0)
    {
        func_16(0, 0);
        return 0x1;
    }
    return func_1374();
}

void func_1443()
{
    WorkModule(0x16, 0x1e00003c);
    func_1375();
}

int func_1444()
{
    if (WorkModule(0x15, 0x1e00003c) && MotionModule(0x1a, 0x1) && WorkModule(0x6, 0x1100000e) >= 0x3 && global18 == 0)
    {
        func_16(0x1, 0);
        return 0x1;
    }
    return func_1376();
}

void func_1445()
{
    WorkModule(0x16, 0x1e00003c);
    func_1377();
}

int func_1446()
{
    if (WorkModule(0x15, 0x1e00003c) && MotionModule(0x1a, 0x1) && WorkModule(0x6, 0x1100000e) >= 0x3 && global18 == 0)
    {
        func_16(0x1, 0);
        return 0x1;
    }
    return func_1378();
}

void func_1447()
{
    func_1379();
}

int func_1448()
{
    return func_1380();
}

void func_1449()
{
    func_1381();
}

int func_1450()
{
    return func_1382();
}

void func_1451()
{
    func_1383();
}

int func_1452()
{
    return func_1384();
}

void func_1453()
{
    func_1385();
}

int func_1454()
{
    return func_1386();
}

void func_1455()
{
    func_1387();
}

int func_1456()
{
    return func_1388();
}

void func_1457()
{
    func_1389();
}

int func_1458()
{
    return func_1390();
}

int func_1459()
{
    if (global38 & 0x1)
    {
        func_16(0xfb, 0x1);
        return 0x1;
    }
    return 0;
}

void func_1460()
{
    func_1391();
}

int func_1461()
{
    if (func_56())
    {
        return 0x1;
    }
    if (func_1459())
    {
        return 0x1;
    }
    return func_1392();
}

void func_1462()
{
    func_1391();
}

int func_1463()
{
    if (func_56())
    {
        return 0x1;
    }
    if (func_1459())
    {
        return 0x1;
    }
    return func_1392();
}

void func_1464()
{
    WorkModule(0x17, 0x1e000089);
}

void func_1465()
{
    WorkModule(0x16, 0x1e00008e);
}

int func_1466()
{
    int var0;
    if (WorkModule(0x15, 0x1e00008e) && func_89() >= WorkModuleF(0, 0x2000007) && global24 & 0x80000)
    {
        if (ControlModule(0x2712, 0x3))
        {
            var0 = WorkModule(0x6, 0x11000009);
        }
        else
        {
            var0 = WorkModule(0x6, 0x11000008);
        }
        func_16(var0, 0x1);
        return 0x1;
    }
    return 0;
}

void func_1467()
{
    WorkModule(0x16, 0x1e000000);
    func_1373();
    func_1464();
    func_1465();
}

int func_1468()
{
    if (func_1459())
    {
        return 0x1;
    }
    if (func_1374())
    {
        return 0x1;
    }
    return func_1466();
}

void func_1469()
{
    WorkModule(0x16, 0x1e00003c);
    func_1375();
    func_1464();
    func_1465();
}

int func_1470()
{
    if (func_1459())
    {
        return 0x1;
    }
    if (func_1376())
    {
        return 0x1;
    }
    return func_1466();
}

void func_1471()
{
    WorkModule(0x16, 0x1e00003c);
    func_1377();
    func_1464();
    func_1465();
}

int func_1472()
{
    if (func_1459())
    {
        return 0x1;
    }
    if (func_1378())
    {
        return 0x1;
    }
    return func_1466();
}

void func_1473()
{
    func_1379();
    func_1464();
}

int func_1474()
{
    if (func_1459())
    {
        return 0x1;
    }
    return func_1380();
}

void func_1475()
{
    func_1381();
    func_1464();
}

int func_1476()
{
    if (func_1459())
    {
        return 0x1;
    }
    return func_1382();
}

void func_1477()
{
    func_1383();
    func_1464();
}

int func_1478()
{
    if (func_1459())
    {
        return 0x1;
    }
    return func_1384();
}

void func_1479()
{
    func_1385();
    func_1464();
}

int func_1480()
{
    if (func_1459())
    {
        return 0x1;
    }
    return func_1386();
}

void func_1481()
{
    func_1387();
}

int func_1482()
{
    if (func_1459())
    {
        return 0x1;
    }
    return func_1388();
}

void func_1483()
{
    func_1389();
    func_1464();
    func_1465();
}

int func_1484()
{
    if (func_1459())
    {
        return 0x1;
    }
    if (func_1390())
    {
        return 0x1;
    }
    if (MotionModuleF(0x1) > WorkModuleF(0, 0x3000028))
    {
        return func_1466();
    }
    return 0;
}

void func_1485()
{
    WorkModule(0x16, 0x1e000002);
    func_1391();
}

int func_1486()
{
    if (WorkModule(0x15, 0x1e000002) && MotionModule(0x2712) && WorkModule(0x6, 0x1100000e) >= 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    return func_1392();
}

void func_1487()
{
    WorkModule(0x16, 0x1e000002);
    func_1391();
}

int func_1488()
{
    if (WorkModule(0x15, 0x1e000002) && MotionModule(0x2712) && WorkModule(0x6, 0x1100000e) >= 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    return func_1392();
}

void func_1489()
{
    WorkModule(0x16, 0x1e000000);
    func_1373();
}

int func_1490()
{
    if (WorkModule(0x15, 0x1e000000) && MotionModule(0x1a, 0x1) && WorkModule(0x6, 0x1100000e) >= 0x2 && global18 == 0)
    {
        func_16(0, 0);
        return 0x1;
    }
    return func_1374();
}

void func_1491()
{
    WorkModule(0x16, 0x1e00003c);
    func_1375();
}

int func_1492()
{
    if (WorkModule(0x15, 0x1e00003c) && MotionModule(0x1a, 0x1) && WorkModule(0x6, 0x1100000e) >= 0x2 && global18 == 0)
    {
        func_16(0x1, 0);
        return 0x1;
    }
    return func_1376();
}

void func_1493()
{
    WorkModule(0x16, 0x1e00003c);
    func_1377();
}

int func_1494()
{
    if (WorkModule(0x15, 0x1e00003c) && MotionModule(0x1a, 0x1) && WorkModule(0x6, 0x1100000e) >= 0x2 && global18 == 0)
    {
        func_16(0x1, 0);
        return 0x1;
    }
    return func_1378();
}

void func_1495()
{
    func_1379();
}

int func_1496()
{
    return func_1380();
}

void func_1497()
{
    func_1381();
}

int func_1498()
{
    return func_1382();
}

void func_1499()
{
    func_1383();
}

int func_1500()
{
    return func_1384();
}

void func_1501()
{
    func_1385();
}

int func_1502()
{
    return func_1386();
}

void func_1503()
{
    func_1387();
}

int func_1504()
{
    return func_1388();
}

void func_1505()
{
    func_1389();
}

int func_1506()
{
    return func_1390();
}

int func_1507()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0x1, 0x84403ea, 0, 0);
    return 0;
}

void func_1508()
{
    KineticModule(0x2716, 0);
    KineticModule(0x2716, 0x1);
    KineticModule(0x2716, 0x2);
    KineticModule(0x2716, 0x3);
    ItemModule(0x12, 0x2);
    EffectModule(0x2732, 0, 0, 10.0f, 10.0f, 0, 0, 0, 0x1, 0x3);
    HitModule(0x2710, 0x2);
    func_1511();
    if (!StopModule(0x1))
    {
        func_1510();
    }
    global16 = func_1510;
    func_78(func_1509);
}

void func_1509()
{
    int var0;
    if (StatusModule(0x6) == 0 && global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        func_1511();
    }
    var0 = ItemModule(0x1e, 0x1);
    if (var0 == 0x1)
    {
        EffectModule(0x2733, 0x1e, 0x1);
        BattleObject(0x53);
        if (global18 == 0)
        {
            func_16(0x98, 0);
        }
        else
        {
            func_16(0xa1, 0);
        }
    }
}

void func_1510()
{
    WorkModule(0x9, 0x11000002);
}

void func_1511()
{
    if (global18 == 0)
    {
        GroundModule(0x2710, 0x1);
    }
    else
    {
        GroundModule(0x2710, 0x5);
    }
    if (WorkModule(0x2712, 0x2100000d) == 0)
    {
        func_22(0x18e, 0, 1.0f);
        WorkModule(0x2710, 0x2100000d);
    }
}

void func_1512()
{
    int var0;
    KineticModule(0x2715, 0);
    KineticModule(0x2715, 0x1);
    KineticModule(0x2715, 0x2);
    KineticModule(0x2715, 0x3);
    var0 = 0;
    if (ItemModule(0x4) == 0x1)
    {
        ItemModule(0x1b);
        var0 = ItemModule(0x1e, 0x1);
    }
    if (var0 == 0)
    {
        EffectModule(0x2733, 0x1e, 0x1);
        BattleObject(0x53);
    }
}

void func_1513()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x17e2, 0x80003e2, 0x4000, 0x8000);
}

void func_1514()
{
    HitModule(0x2710, 0x1);
    AreaModule(0x2710, 0);
    KineticModule(0x3);
    ItemModule(0x13, 0);
    func_78(func_1515);
}

void func_1515()
{
    if (StatusModule(0x6) == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        func_1516(0x191, 0x194, 0x2100000d);
    }
    if (WorkModule(0x10, 0x2100000e) && !WorkModule(0x10, 0x2100000f))
    {
        ItemModule(0xb);
        ItemModule(0x13, 0x1);
        WorkModule(0x2710, 0x2100000f);
        WorkModule(0x7, 0, 0x11000002);
        if (!StopModule(0x1))
        {
            func_1521();
        }
        global16 = func_1521;
        BattleObject(0x55, 0x1, 0x1c);
    }
    if (MotionModule(0x2712))
    {
        func_16(0xfc, 0);
        return 0x1;
    }
}

void func_1516(int arg0, int arg1, int arg2)
{
    if (global18 == 0)
    {
        KineticModule(0, 0xf);
        GroundModule(0x2710, 0x1);
        if (WorkModule(0x2712, arg2))
        {
            func_23(arg0);
        }
        else
        {
            func_22(arg0, 0, 1.0f);
            WorkModule(0x2710, arg2);
        }
    }
    else
    {
        KineticModule(0, 0x11);
        GroundModule(0x2710, 0x5);
        if (WorkModule(0x2712, arg2))
        {
            func_23(arg1);
        }
        else
        {
            func_22(arg1, 0, 1.0f);
            WorkModule(0x2710, arg2);
        }
    }
}

void func_1517()
{
    
}

void func_1518()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0x20);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x7e2, 0x80003e2, 0x4000, 0);
}

void func_1519()
{
    WorkModule(0x2711, 0x2100000d);
    AreaModule(0x2710, 0);
    func_1516(0x192, 0x195, 0x2100000d);
    if (!StopModule(0x1))
    {
        func_1521();
    }
    global16 = func_1521;
    func_78(func_1520);
}

void func_1520()
{
    if (StatusModule(0x6) == 0 && global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        func_1516(0x192, 0x195, 0x2100000d);
    }
    if (WorkModule(0x6, 0x11000002) >= WorkModule(0x6, 0x1200030e))
    {
        func_16(0xfd, 0);
        return 0x1;
    }
}

void func_1521()
{
    WorkModule(0x9, 0x11000002);
}

void func_1522()
{
    
}

void func_1523()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0x20);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x80003e2, 0x4000, 0);
}

void func_1524()
{
    WorkModule(0x2711, 0x2100000d);
    AreaModule(0x2710, 0);
    ItemModule(0x13, 0x2);
    func_78(func_1525);
}

void func_1525()
{
    if (StatusModule(0x6) == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        func_1516(0x193, 0x196, 0x2100000d);
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
        }
        else
        {
            func_16(0xe, 0);
        }
        return 0x1;
    }
}

void func_1526()
{
    ItemModule(0x10, 0);
}

int func_1527(int arg0)
{
    return func_1528(arg0) == 0x1 || func_1529(arg0) == 0x1;
}

int func_1528(int arg0)
{
    return arg0 == WorkModule(0x6, 0x11000003) || arg0 == WorkModule(0x6, 0x11000004) || arg0 == WorkModule(0x6, 0x11000006) || arg0 == WorkModule(0x6, 0x11000005) || arg0 == WorkModule(0x6, 0x11000007) || arg0 == WorkModule(0x6, 0x11000008) || arg0 == WorkModule(0x6, 0x11000009) || arg0 == WorkModule(0x6, 0x1100000c) || arg0 == WorkModule(0x6, 0x1100000d);
}

int func_1529(int arg0)
{
    return arg0 == WorkModule(0x6, 0x1100000a) || arg0 == WorkModule(0x6, 0x1100000b);
}

void func_1530(int arg0, int arg1)
{
    int var2;
    int var3;
    int var4;
    float var5;
    float var6;
    int var7;
    float var8;
    float var9;
    var2 = global4;
    var3 = global5;
    if (var2 == WorkModule(0x6, 0x11000003) || var2 == WorkModule(0x6, 0x1100000d))
    {
        var4 = 0;
        var5 = 0;
        var6 = 1.0f;
        if (func_1529(var3) == 0x1)
        {
            var5 = MotionModuleF(0x1);
            var6 = MotionModuleF(0x9);
            var4 = 0x1;
        }
        var7 = 0x163;
        func_22(var7, 0, 1.0f);
        if (MotionModule(0x15, 0x1) == 0xffffffff)
        {
            if (var4 == 0x1)
            {
                MotionModule(0x17, 0x1, arg0, 0, var5, var6, 0x1);
            }
            else
            {
                MotionModule(0x17, 0x1, arg0, 0, var5, var6);
            }
        }
    }
    else if (var2 == WorkModule(0x6, 0x11000004))
    {
        var8 = sys_40(0x2);
        var9 = WorkModuleF(0, 0x3000040);
        func_762(var9, 0xc, 0x1000006, var8, 0x1000007, 0);
        func_763(0x166, 0x165, 0x164, 0x1000006, var8, 0x1000007);
    }
    else if (var2 == WorkModule(0x6, 0x11000005))
    {
        var8 = sys_40(0x2);
        var9 = WorkModuleF(0, 0x3000040) * WorkModuleF(0, 0x2000208);
        func_762(var9, 0xc, 0x1000006, var8, 0x1000007, 0x1);
        func_763(0x16b, 0x16a, 0x169, 0x1000006, var8, 0x1000007);
    }
    else if (func_1529(var2) == 0x1)
    {
        var4 = 0;
        var5 = 0;
        var6 = 1.0f;
        if (func_1528(var3) == 0x1)
        {
            var5 = WorkModuleF(0, 0x1000006);
            if (var5 != -1.0f)
            {
                var6 = WorkModuleF(0, 0x1000007);
                var4 = 0x1;
            }
            else
            {
                var5 = 0;
            }
        }
        if (MotionModule(0x15, 0x1) != 0xffffffff)
        {
            MotionModule(0x19, 0x1);
        }
        if (var4 == 0x1)
        {
            MotionModule(0x3, arg1, var5, var6);
        }
        else
        {
            MotionModule(0x1, arg1, var5, var6);
        }
    }
}

void func_1531(int arg0, int arg1)
{
    int var2;
    int var3;
    int var4;
    float var5;
    float var6;
    float var7;
    float var8;
    var2 = global4;
    var3 = global5;
    if (var2 == WorkModule(0x6, 0x11000003) || var2 == WorkModule(0x6, 0x1100000d))
    {
        var4 = 0;
        var5 = 0;
        var6 = 1.0f;
        if (func_1529(var3) == 0x1)
        {
            var5 = MotionModuleF(0x1);
            var6 = MotionModuleF(0x9);
            var4 = 0x1;
        }
        if (var4 == 0x1)
        {
            MotionModule(0x3, arg0, var5, var6);
        }
        else
        {
            MotionModule(0x1, arg0, var5, var6);
        }
    }
    else if (var2 == WorkModule(0x6, 0x11000004))
    {
        var7 = sys_40(0x2);
        var8 = WorkModuleF(0, 0x3000040);
        func_762(var8, 0xc, 0x1000006, var7, 0x1000007, 0);
        func_763(0x166, 0x165, 0x164, 0x1000006, var7, 0x1000007);
    }
    else if (var2 == WorkModule(0x6, 0x11000005))
    {
        var7 = sys_40(0x2);
        var8 = WorkModuleF(0, 0x3000040) * WorkModuleF(0, 0x2000208);
        func_762(var8, 0xc, 0x1000006, var7, 0x1000007, 0x1);
        func_763(0x16b, 0x16a, 0x169, 0x1000006, var7, 0x1000007);
    }
    else if (func_1529(var2) == 0x1)
    {
        var4 = 0;
        var5 = 0;
        var6 = 1.0f;
        if (func_1528(var3) == 0x1)
        {
            var5 = MotionModuleF(0x1);
            var6 = MotionModuleF(0x9);
            var4 = 0x1;
        }
        if (var4 == 0x1)
        {
            MotionModule(0x3, arg1, var5, var6);
        }
        else
        {
            MotionModule(0x1, arg1, var5, var6);
        }
    }
}

void func_1532()
{
    int var0;
    float var1;
    float var2;
    float var3;
    var0 = global4;
    if (var0 == WorkModule(0x6, 0x11000004))
    {
        var1 = sys_40(0x2);
        func_774(WorkModuleF(0, 0x1000006), WorkModuleF(0, 0x3000040), WorkModuleF(0, 0x300003e), WorkModuleF(0, 0x300003f), WorkModuleF(0, 0x2000002), 0x1000006, var1, 0x1);
        func_773(0x166, 0x165, 0x164, 0x1000006, var1, 0x1000007);
    }
    else if (var0 == WorkModule(0x6, 0x11000005))
    {
        var1 = sys_40(0x2);
        func_774(WorkModuleF(0, 0x1000006), WorkModuleF(0, 0x3000040) * WorkModuleF(0, 0x2000208), WorkModuleF(0, 0x300003e), WorkModuleF(0, 0x300003f), WorkModuleF(0, 0x2000002), 0x1000006, var1, 0x1);
        func_773(0x16b, 0x16a, 0x169, 0x1000006, var1, 0x1000007);
    }
    else if (var0 == WorkModule(0x6, 0x11000006) || var0 == WorkModule(0x6, 0x11000007))
    {
        var2 = 0.0010000000474974513f;
        var3 = KineticModuleF(0, 0x1);
        if (func_13(var3) <= var2)
        {
            MotionModule(0x4, 1.0f);
        }
    }
}

void func_1533(int arg0)
{
    float var1;
    float var2;
    if (func_1527(arg0) == 0x1)
    {
        var1 = -1.0f;
        if (MotionModule(0x15, 0x1) != 0xffffffff)
        {
            var1 = MotionModuleF(0xd, 0x1);
            var2 = MotionModuleF(0xe, 0x1);
            WorkModule(0, var2 + 0, 0x1000007);
        }
        WorkModule(0, var1 + 0, 0x1000006);
        if (func_1529(arg0) == 0x1)
        {
            if (MotionModule(0x15, 0x1) != 0xffffffff)
            {
                MotionModule(0x19, 0x1);
            }
        }
        WorkModule(0x7, 0x3, 0x11000000);
        if (WorkModule(0x10, 0x2000004c))
        {
            WorkModule(0x2710, 0x21000005);
        }
    }
    else
    {
        if (MotionModule(0x15, 0x1) != 0xffffffff)
        {
            MotionModule(0x19, 0x1);
        }
        ItemModule(0x1b);
    }
}

void func_1534(int arg0)
{
    float var1;
    if (func_1527(arg0) == 0x1)
    {
        var1 = -1.0f;
        WorkModule(0, var1 + 0, 0x1000006);
        WorkModule(0x7, 0x3, 0x11000000);
        if (WorkModule(0x10, 0x2000004c))
        {
            WorkModule(0x2710, 0x21000005);
        }
    }
    else
    {
        if (MotionModule(0x15, 0x1) != 0xffffffff)
        {
            MotionModule(0x19, 0x1);
        }
        ItemModule(0x1b);
    }
}

void func_1535()
{
    int var0;
    var0 = ItemModule(0x11);
    WorkModule(0x7, var0, 0x11000002);
    if (var0 == 0x25)
    {
        func_1544();
    }
    else if (var0 == 0x27)
    {
        func_1556();
    }
    else if (var0 == 0x24)
    {
        func_1549();
    }
    else if (var0 == 0x6c)
    {
        func_1567();
    }
    else if (var0 == 0x29)
    {
        func_1572();
    }
    else if (var0 == 0x2d)
    {
        func_1573();
    }
    else if (var0 == 0x2b)
    {
        func_1582();
    }
}

void func_1536()
{
    WorkModule(0x7, 0x98, 0x11000003);
    WorkModule(0x7, 0x99, 0x11000004);
    WorkModule(0x7, 0x9b, 0x11000005);
    WorkModule(0x7, 0x9a, 0x11000006);
    WorkModule(0x7, 0x9c, 0x11000007);
    WorkModule(0x7, 0x9d, 0x11000008);
    WorkModule(0x7, 0x9e, 0x11000009);
    WorkModule(0x7, 0xa1, 0x1100000a);
    WorkModule(0x7, 0xa0, 0x1100000b);
    WorkModule(0x7, 0x9f, 0x1100000c);
    WorkModule(0x7, 0xa2, 0x1100000d);
}

void func_1537()
{
    func_1536();
    func_1535();
}

void func_1538()
{
    BattleObject(0x23);
}

void func_1539(int arg0)
{
    BattleObject(0x24, arg0);
}

void func_1540()
{
    int var0;
    var0 = WorkModule(0x6, 0x11000002);
    if (var0 == 0x25)
    {
        func_1545();
    }
    else if (var0 == 0x27)
    {
        func_1557();
    }
    else if (var0 == 0x24)
    {
        func_1550();
    }
    else if (var0 == 0x6c)
    {
        func_1568();
    }
    else if (var0 == 0x29)
    {
        func_1545();
    }
    else if (var0 == 0x2d)
    {
        func_1574();
    }
    else if (var0 == 0x2b)
    {
        func_1545();
    }
}

void func_1541()
{
    int var0;
    var0 = WorkModule(0x6, 0x11000002);
    if (var0 == 0x25)
    {
        func_1546();
    }
    else if (var0 == 0x27)
    {
        func_1558();
    }
    else if (var0 == 0x24)
    {
        func_1551();
    }
    else if (var0 == 0x6c)
    {
        func_1569();
    }
    else if (var0 == 0x29)
    {
        func_1546();
    }
    else if (var0 == 0x2d)
    {
        func_1575();
    }
    else if (var0 == 0x2b)
    {
        func_1546();
    }
}

void func_1542()
{
    int var0;
    var0 = WorkModule(0x6, 0x11000002);
    if (var0 == 0x25)
    {
        func_1547();
    }
    else if (var0 == 0x27)
    {
        func_1559();
    }
    else if (var0 == 0x24)
    {
        func_1552();
    }
    else if (var0 == 0x6c)
    {
        func_1570();
    }
    else if (var0 == 0x29)
    {
        func_1547();
    }
    else if (var0 == 0x2d)
    {
        func_1576();
    }
    else if (var0 == 0x2b)
    {
        func_1547();
    }
    if (global18 == 0)
    {
        if (GroundModule(0xd) == 0x1)
        {
            if (global31 & 0x200)
            {
                WorkModule(0x2710, 0x2100000d);
            }
        }
    }
}

void func_1543()
{
    int var0;
    int var1;
    var0 = global6;
    var1 = WorkModule(0x6, 0x11000002);
    if (var1 == 0x25)
    {
        func_1548(var0);
    }
    else if (var1 == 0x27)
    {
        func_1560(var0);
    }
    else if (var1 == 0x24)
    {
        func_1553(var0);
    }
    else if (var1 == 0x6c)
    {
        func_1571(var0);
    }
    else if (var1 == 0x29)
    {
        func_1548(var0);
    }
    else if (var1 == 0x2d)
    {
        func_1577(var0);
    }
    else if (var1 == 0x2b)
    {
        func_1548(var0);
    }
}

void func_1544()
{
    int var0;
    int var1;
    var0 = global5;
    if ((var0 == 0x98 || var0 == 0x98 || var0 == 0x99 || var0 == 0x9a || var0 == 0x9b || var0 == 0x9c || var0 == 0x9d || var0 == 0x9e || var0 == 0xa1 || var0 == 0xa0 || var0 == 0x9f || var0 == 0xa2) == 0)
    {
        func_1538();
    }
    var1 = ItemModule(0x1a);
    if (var1 == 0)
    {
        func_1530(0x172, 0x173);
        if ((var0 == 0x98 || var0 == 0x98 || var0 == 0x99 || var0 == 0x9a || var0 == 0x9b || var0 == 0x9c || var0 == 0x9d || var0 == 0x9e || var0 == 0xa1 || var0 == 0xa0 || var0 == 0x9f || var0 == 0xa2) == 0)
        {
            SoundModule(0x2710, 0x350057);
        }
    }
    else
    {
        func_1530(0x170, 0x171);
    }
    if ((var0 == 0x98 || var0 == 0x98 || var0 == 0x99 || var0 == 0x9a || var0 == 0x9b || var0 == 0x9c || var0 == 0x9d || var0 == 0x9e || var0 == 0xa1 || var0 == 0xa0 || var0 == 0x9f || var0 == 0xa2) == 0)
    {
        BattleObject(0xd, 0x2, 0x71, 0x1);
        BattleObject(0x1c, 0xf);
    }
}

void func_1545()
{
    func_1532();
}

void func_1546()
{
    
}

void func_1547()
{
    
}

void func_1548(int arg0)
{
    if ((arg0 == 0x98 || arg0 == 0x98 || arg0 == 0x99 || arg0 == 0x9a || arg0 == 0x9b || arg0 == 0x9c || arg0 == 0x9d || arg0 == 0x9e || arg0 == 0xa1 || arg0 == 0xa0 || arg0 == 0x9f || arg0 == 0xa2) == 0)
    {
        func_1539(0x2);
    }
    func_1533(arg0);
}

void func_1549()
{
    if ((global5 == 0x98 || global5 == 0x98 || global5 == 0x99 || global5 == 0x9a || global5 == 0x9b || global5 == 0x9c || global5 == 0x9d || global5 == 0x9e || global5 == 0xa1 || global5 == 0xa0 || global5 == 0x9f || global5 == 0xa2) == 0)
    {
        func_1538();
        WorkModule(0x2711, 0x21000011);
        WorkModule(0x7, 0, 0x1100000e);
        BattleObject(0xd, 0x2, 0x72, 0x1);
        BattleObject(0x1c, 0xf);
    }
    func_1530(0x174, 0x175);
}

void func_1550()
{
    int var0;
    int var1;
    var0 = WorkModule(0x6, 0x1100000e);
    if (var0 == 0)
    {
        if (WorkModule(0x10, 0x21000011))
        {
            func_1554();
            if (ItemModule(0x1a) > 0)
            {
                BattleObject(0x55, 0x1, 0x1c);
            }
        }
    }
    else if (var0 == 0x1)
    {
        if (ControlModule(0x2712, 0) == 0)
        {
            var1 = WorkModule(0x6, 0x12000202);
            if (ControlModule(0x2722, 0) >= var1)
            {
                WorkModule(0x2710, 0x21000012);
                WorkModule(0x2710, 0x2100000f);
            }
        }
    }
    func_1532();
}

void func_1551()
{
    int var0;
    int var1;
    int var2;
    int var3;
    var0 = WorkModule(0x6, 0x1100000e);
    if (var0 == 0x1)
    {
        var1 = WorkModule(0x6, 0x1100000f);
        if (WorkModule(0x10, 0x21000012))
        {
            if (var1 >= WorkModule(0x6, 0x12000200))
            {
                func_1555();
            }
        }
        var2 = WorkModule(0x6, 0x11000010);
        var2--;
        WorkModule(0x7, var2, 0x11000010);
        if (var2 <= 0)
        {
            var3 = WorkModule(0x6, 0x12000201);
            WorkModule(0x7, var3, 0x11000010);
            WorkModule(0x9, 0x1100000f);
            if (ItemModule(0x1a) == 0)
            {
                SoundModule(0x2710, 0x35005a);
            }
            else
            {
                ItemModule(0xb);
                ControlModule(0x2714, 0, 0);
                if (var1 % 0x2 == 0)
                {
                    EffectModule(0x2711, 0x1000009, 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 1.0f + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0x1);
                }
            }
        }
    }
}

void func_1552()
{
    
}

void func_1553(int arg0)
{
    if ((arg0 == 0x98 || arg0 == 0x98 || arg0 == 0x99 || arg0 == 0x9a || arg0 == 0x9b || arg0 == 0x9c || arg0 == 0x9d || arg0 == 0x9e || arg0 == 0xa1 || arg0 == 0xa0 || arg0 == 0x9f || arg0 == 0xa2) == 0)
    {
        func_1539(0x2);
        if (WorkModule(0x10, 0x21000011))
        {
            ItemModule(0x1d, 0x1);
        }
    }
    func_1533(arg0);
}

void func_1554()
{
    if (MotionModule(0x15, 0x1) != 0xffffffff)
    {
        MotionModule(0x21, 0x1, 0);
    }
    else
    {
        MotionModule(0x4, 0);
    }
    WorkModule(0x7, 0x1, 0x1100000e);
}

void func_1555()
{
    if (MotionModule(0x15, 0x1) != 0xffffffff)
    {
        MotionModule(0x21, 0x1, 1.0f);
    }
    else
    {
        MotionModule(0x4, 1.0f);
    }
    WorkModule(0x7, 0x2, 0x1100000e);
}

void func_1556()
{
    int var0;
    int var1;
    if ((global5 == 0x98 || global5 == 0x98 || global5 == 0x99 || global5 == 0x9a || global5 == 0x9b || global5 == 0x9c || global5 == 0x9d || global5 == 0x9e || global5 == 0xa1 || global5 == 0xa0 || global5 == 0x9f || global5 == 0xa2) == 0)
    {
        func_1538();
        WorkModule(0x2711, 0x21000011);
        WorkModule(0x7, 0, 0x1100000e);
        WorkModule(0x7, WorkModule(0x6, 0x120001ff), 0x1100000f);
        WorkModule(0x7, 0, 0x11000010);
        SoundModule(0x2710, 0x350049);
        BattleObject(0x1c, 0xf);
    }
    var0 = ItemModule(0x1a);
    var1 = WorkModule(0x6, 0x1100000e);
    if (var1 == 0)
    {
        if (var0 == 0)
        {
            func_1530(0x17e, 0x182);
        }
        else
        {
            func_1530(0x176, 0x17a);
        }
    }
    else if (var1 == 0x1)
    {
        if (var0 == 0)
        {
            func_1530(0x17f, 0x183);
        }
        else
        {
            func_1530(0x177, 0x17b);
        }
    }
    else if (var1 == 0x2)
    {
        if (var0 == 0)
        {
            func_1530(0x17e, 0x182);
        }
        else
        {
            func_1530(0x176, 0x17a);
        }
    }
    else if (var1 == 0x3)
    {
        if (var0 == 0)
        {
            func_1530(0x180, 0x184);
        }
        else
        {
            func_1530(0x178, 0x17c);
        }
        ItemModule(0x1d, 0x1);
    }
    else if (var1 == 0x4)
    {
        if (var0 == 0)
        {
            func_1530(0x181, 0x185);
        }
        else
        {
            func_1530(0x179, 0x17d);
        }
    }
}

void func_1557()
{
    int var0;
    var0 = WorkModule(0x6, 0x1100000e);
    if (var0 == 0)
    {
        if (ControlModule(0x2713, 0))
        {
            WorkModule(0x2710, 0x21000011);
        }
    }
    else if (var0 == 0x1)
    {
        if (ControlModule(0x2710, 0))
        {
            WorkModule(0x7, WorkModule(0x6, 0x120001ff), 0x1100000f);
        }
    }
    func_1532();
}

void func_1558()
{
    int var0;
    int var1;
    int var2;
    var0 = WorkModule(0x6, 0x1100000e);
    if (var0 == 0)
    {
        WorkModule(0x9, 0x11000010);
        if (func_1561() == 0x1)
        {
            if (WorkModule(0x10, 0x21000011))
            {
                func_1565();
                if (ItemModule(0x1a) > 0)
                {
                    BattleObject(0x55, 0x1, 0x1c);
                }
            }
            else
            {
                func_1563();
            }
        }
    }
    else if (var0 == 0x1)
    {
        if (func_1561() == 0x1)
        {
            var1 = WorkModule(0x6, 0x1100000f);
            var1--;
            WorkModule(0x7, var1, 0x1100000f);
            if (var1 <= 0)
            {
                func_1566();
            }
            else
            {
                func_1562();
            }
        }
    }
    else if (var0 == 0x2)
    {
        WorkModule(0x9, 0x11000010);
        var2 = WorkModule(0x6, 0x11000010);
        if (ControlModule(0x2712, 0) == 0 || var2 >= WorkModule(0x6, 0x120001fe))
        {
            func_1564();
        }
    }
}

void func_1559()
{
    
}

void func_1560(int arg0)
{
    if ((arg0 == 0x98 || arg0 == 0x98 || arg0 == 0x99 || arg0 == 0x9a || arg0 == 0x9b || arg0 == 0x9c || arg0 == 0x9d || arg0 == 0x9e || arg0 == 0xa1 || arg0 == 0xa0 || arg0 == 0x9f || arg0 == 0xa2) == 0)
    {
        func_1539(0x2);
        ItemModule(0x1d, 0x1);
        if (WorkModule(0x6, 0x1100000e) == 0x2)
        {
            ItemModule(0x21, WorkModule(0x6, 0x11000010));
        }
    }
    func_1533(arg0);
}

int func_1561()
{
    if (MotionModule(0x15, 0x1) != 0xffffffff)
    {
        return MotionModule(0x1a, 0x1);
    }
    return MotionModule(0x2712);
}

void func_1562()
{
    if (MotionModule(0x15, 0x1) != 0xffffffff)
    {
        MotionModule(0x23, 0x1, 0);
    }
    else
    {
        MotionModule(0x2711, 0);
    }
    if (ItemModule(0x1a) == 0)
    {
        SoundModule(0x2710, 0x350055);
    }
}

void func_1563()
{
    WorkModule(0x7, 0x2, 0x1100000e);
    ItemModule(0x1d, 0);
    BattleObject(0xd, 0x2, 0x75, 0x1);
}

void func_1564()
{
    int var0;
    int var1;
    var0 = ItemModule(0x1a);
    if (MotionModule(0x15, 0x1) != 0xffffffff)
    {
        if (var0 == 0)
        {
            var1 = 0x180;
        }
        else
        {
            var1 = 0x178;
        }
        MotionModule(0x18, 0x1);
        MotionModule(0x17, 0x1, var1, 0, 0, 1.0f);
    }
    else
    {
        if (var0 == 0)
        {
            var1 = 0x184;
        }
        else
        {
            var1 = 0x17c;
        }
        func_22(var1, 0, 1.0f);
    }
    ItemModule(0x1d, 0x1);
    if (var0 == 0)
    {
        SoundModule(0x2710, 0x350055);
    }
    WorkModule(0x7, 0x3, 0x1100000e);
    if (var0 > 0)
    {
        BattleObject(0x55, 0x1, 0x1c);
    }
    BattleObject(0xd, 0x2, 0x75, 0);
}

void func_1565()
{
    int var0;
    int var1;
    var0 = ItemModule(0x1a);
    if (MotionModule(0x15, 0x1) != 0xffffffff)
    {
        if (var0 == 0)
        {
            var1 = 0x17f;
        }
        else
        {
            var1 = 0x177;
        }
        MotionModule(0x18, 0x1);
        MotionModule(0x17, 0x1, var1, 0, 0, 1.0f);
    }
    else
    {
        if (var0 == 0)
        {
            var1 = 0x183;
        }
        else
        {
            var1 = 0x17b;
        }
        func_22(var1, 0, 1.0f);
    }
    if (var0 == 0)
    {
        SoundModule(0x2710, 0x350055);
    }
    WorkModule(0x7, 0x1, 0x1100000e);
    BattleObject(0xd, 0x2, 0x74, 0x1);
}

void func_1566()
{
    int var0;
    int var1;
    var0 = ItemModule(0x1a);
    if (MotionModule(0x15, 0x1) != 0xffffffff)
    {
        if (var0 == 0)
        {
            var1 = 0x181;
        }
        else
        {
            var1 = 0x179;
        }
        MotionModule(0x18, 0x1);
        MotionModule(0x17, 0x1, var1, 0, 0, 1.0f);
    }
    else
    {
        if (var0 == 0)
        {
            var1 = 0x185;
        }
        else
        {
            var1 = 0x17d;
        }
        func_22(var1, 0, 1.0f);
    }
    WorkModule(0x7, 0x4, 0x1100000e);
    WorkModule(0x2710, 0x2100000f);
}

void func_1567()
{
    if ((global5 == 0x98 || global5 == 0x98 || global5 == 0x99 || global5 == 0x9a || global5 == 0x9b || global5 == 0x9c || global5 == 0x9d || global5 == 0x9e || global5 == 0xa1 || global5 == 0xa0 || global5 == 0x9f || global5 == 0xa2) == 0)
    {
        func_1538();
        MotionModule(0x18, 0x1);
        MotionModule(0x17, 0x1, 0x18f, 0, 0, 1.0f);
    }
    func_1531(0x163, 0x190);
}

void func_1568()
{
    func_1532();
}

void func_1569()
{
    
}

void func_1570()
{
    
}

void func_1571(int arg0)
{
    func_1534(arg0);
}

void func_1572()
{
    int var0;
    var0 = global5;
    if ((var0 == 0x98 || var0 == 0x98 || var0 == 0x99 || var0 == 0x9a || var0 == 0x9b || var0 == 0x9c || var0 == 0x9d || var0 == 0x9e || var0 == 0xa1 || var0 == 0xa0 || var0 == 0x9f || var0 == 0xa2) == 0)
    {
        func_1538();
    }
    func_1530(0x18a, 0x18b);
    if ((var0 == 0x98 || var0 == 0x98 || var0 == 0x99 || var0 == 0x9a || var0 == 0x9b || var0 == 0x9c || var0 == 0x9d || var0 == 0x9e || var0 == 0xa1 || var0 == 0xa0 || var0 == 0x9f || var0 == 0xa2) == 0)
    {
        BattleObject(0xd, 0x2, 0x7f, 0x1);
        BattleObject(0x1c, 0xf);
    }
}

void func_1573()
{
    int var0;
    int var1;
    if ((global5 == 0x98 || global5 == 0x98 || global5 == 0x99 || global5 == 0x9a || global5 == 0x9b || global5 == 0x9c || global5 == 0x9d || global5 == 0x9e || global5 == 0xa1 || global5 == 0xa0 || global5 == 0x9f || global5 == 0xa2) == 0)
    {
        func_1538();
        WorkModule(0x2711, 0x21000011);
        WorkModule(0x2711, 0x21000012);
        WorkModule(0x7, 0, 0x11000011);
        WorkModule(0x7, 0, 0x1100000e);
        BattleObject(0x1c, 0xf);
    }
    var0 = ItemModule(0x1a);
    var1 = WorkModule(0x6, 0x1100000e);
    if (var1 == 0)
    {
        func_1530(0x186, 0x188);
    }
    else if (var1 == 0x1)
    {
        func_1530(0x186, 0x188);
    }
    else if (var1 == 0x2)
    {
        func_1530(0x187, 0x189);
    }
}

void func_1574()
{
    int var0;
    int var1;
    var0 = WorkModule(0x6, 0x1100000e);
    if (var0 == 0x1)
    {
        if (ControlModule(0x2712, 0) == 0)
        {
            var1 = WorkModule(0x6, 0x120002f1);
            if (ControlModule(0x2722, 0) >= var1)
            {
                WorkModule(0x2710, 0x21000011);
                WorkModule(0x2710, 0x2100000f);
            }
        }
    }
    func_1532();
}

void func_1575()
{
    int var0;
    int var1;
    int var2;
    int var3;
    int var4;
    int var5;
    var0 = WorkModule(0x6, 0x1100000e);
    if (var0 == 0)
    {
        if (WorkModule(0x10, 0x21000012) == 0 && ItemModule(0x1a) > 0)
        {
            EffectModule(0x2711, 0x1000009, 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 1.0f + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0x1);
            WorkModule(0x2710, 0x21000012);
        }
        if (func_1578() == 0x1)
        {
            if (ItemModule(0x1a) > 0)
            {
                BattleObject(0x55, 0x1, 0x1c);
            }
            func_1580();
        }
    }
    else if (var0 == 0x1)
    {
        var1 = WorkModule(0x6, 0x1100000f);
        if (WorkModule(0x10, 0x21000011))
        {
            if (var1 >= WorkModule(0x6, 0x120002ef))
            {
                func_1581();
                return;
            }
        }
        var2 = WorkModule(0x6, 0x11000010);
        var2--;
        WorkModule(0x7, var2, 0x11000010);
        var3 = ItemModule(0x1a);
        if (var2 <= 0)
        {
            var4 = WorkModule(0x6, 0x120002f0);
            WorkModule(0x7, var4, 0x11000010);
            WorkModule(0x9, 0x1100000f);
            if (var3 == 0)
            {
                
            }
            else
            {
                ItemModule(0xb);
                ControlModule(0x2714, 0, 0);
            }
        }
        if (var3 > 0)
        {
            var5 = WorkModule(0x6, 0x11000011);
            var5--;
            if (var5 <= 0)
            {
                var5 = 0x8;
                EffectModule(0x2711, 0x1000019, 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 1.0f + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0x1);
            }
            WorkModule(0x7, var5, 0x11000011);
        }
    }
}

void func_1576()
{
    
}

void func_1577(int arg0)
{
    if ((arg0 == 0x98 || arg0 == 0x98 || arg0 == 0x99 || arg0 == 0x9a || arg0 == 0x9b || arg0 == 0x9c || arg0 == 0x9d || arg0 == 0x9e || arg0 == 0xa1 || arg0 == 0xa0 || arg0 == 0x9f || arg0 == 0xa2) == 0)
    {
        func_1539(0x2);
        if (WorkModule(0x6, 0x1100000e) == 0x1)
        {
            ItemModule(0x1d, 0x1);
        }
    }
    func_1533(arg0);
}

int func_1578()
{
    if (MotionModule(0x15, 0x1) != 0xffffffff)
    {
        return MotionModule(0x1a, 0x1);
    }
    return MotionModule(0x2712);
}

void func_1579()
{
    if (MotionModule(0x15, 0x1) != 0xffffffff)
    {
        MotionModule(0x23, 0x1, 0);
    }
    else
    {
        MotionModule(0x2711, 0);
    }
}

void func_1580()
{
    WorkModule(0x7, 0x1, 0x1100000e);
    ItemModule(0x1d, 0);
    BattleObject(0xd, 0x2, 0x80, 0x1);
}

void func_1581()
{
    int var0;
    if (MotionModule(0x15, 0x1) != 0xffffffff)
    {
        var0 = 0x187;
        MotionModule(0x18, 0x1);
        MotionModule(0x17, 0x1, var0, 0, 0, 1.0f);
    }
    else
    {
        var0 = 0x189;
        func_22(var0, 0, 1.0f);
    }
    WorkModule(0x7, 0x2, 0x1100000e);
    ItemModule(0x1d, 0x1);
    WorkModule(0x2710, 0x2100000f);
}

void func_1582()
{
    int var0;
    var0 = global5;
    if ((var0 == 0x98 || var0 == 0x98 || var0 == 0x99 || var0 == 0x9a || var0 == 0x9b || var0 == 0x9c || var0 == 0x9d || var0 == 0x9e || var0 == 0xa1 || var0 == 0xa0 || var0 == 0x9f || var0 == 0xa2) == 0)
    {
        func_1538();
    }
    func_1530(0x18c, 0x18d);
    if ((var0 == 0x98 || var0 == 0x98 || var0 == 0x99 || var0 == 0x9a || var0 == 0x9b || var0 == 0x9c || var0 == 0x9d || var0 == 0x9e || var0 == 0xa1 || var0 == 0xa0 || var0 == 0x9f || var0 == 0xa2) == 0)
    {
        BattleObject(0xd, 0x2, 0x81, 0x1);
        BattleObject(0x1c, 0xf);
    }
}

int func_1583()
{
    StatusModule(0x5, 0xffffffff, 0x33, 0x7, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1584()
{
    int var0;
    func_22(0x1be, 0, 1.0f);
    if (global18 == 0)
    {
        var0 = WorkModule(0x6, 0x13000123);
        if (var0 == 0)
        {
            GroundModule(0x7, -5.199999809265137f);
        }
    }
    func_78(func_1585);
}

void func_1585()
{
    func_1588();
}

void func_1586()
{
    int var0;
    float var1;
    float var2;
    float var3;
    if (global18 == 0)
    {
        var0 = WorkModule(0x6, 0x13000123);
        if (var0 == 0)
        {
            var1 = PostureModuleF(0x1);
            var2 = PostureModuleF(0x2);
            var3 = PostureModuleF(0x3);
            PostureModule(0x3, var1, var2 + -5.199999809265137f, var3);
        }
    }
    GroundModule(0x7, 0);
}

void func_1587()
{
    int var0;
    int var1;
    PostureModule(0, -LinkModuleF(0x7, 0));
    PostureModule(0x2);
    var0 = 0;
    var1 = WorkModule(0x6, 0x13000120);
    if (var1 == 0x1)
    {
        var0 = 0x1;
    }
    else if (var1 == 0x3)
    {
        var0 = 0x2;
    }
    MotionModule(0x29, var0);
    LinkModule(0x2716, 0, 0x3);
}

int func_1588()
{
    if (global3 == 0)
    {
        if (func_1590() != 0)
        {
            return 0x1;
        }
    }
    if (func_1591() != 0)
    {
        return 0x1;
    }
    return 0;
}

void func_1589()
{
    
}

int func_1590()
{
    return 0;
}

int func_1591()
{
    return 0;
}

void func_1592()
{
    
}

void func_1593()
{
    if (global6 != 0x44)
    {
        CaptureModule(0x4);
    }
}

int func_1594()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1595()
{
    func_22(0x1c1, 0, 1.0f);
    func_78(func_1596);
}

void func_1596()
{
    func_16(0xbc, 0);
    return;
    func_1599();
}

void func_1597()
{
    
}

void func_1598()
{
    int var0;
    int var1;
    PostureModule(0, -LinkModuleF(0x7, 0));
    PostureModule(0x2);
    var0 = 0;
    var1 = WorkModule(0x6, 0x13000120);
    if (var1 == 0x1)
    {
        var0 = 0x4;
    }
    else if (var1 == 0x3)
    {
        var0 = 0x8;
    }
    MotionModule(0x29, var0);
    WorkModule(0x7, 0x1c1, 0x11000002);
    LinkModule(0x2716, 0, 0x3);
}

int func_1599()
{
    if (global3 == 0)
    {
        if (func_1601() != 0)
        {
            return 0x1;
        }
    }
    if (func_1602() != 0)
    {
        return 0x1;
    }
    return 0;
}

void func_1600()
{
    
}

int func_1601()
{
    return 0;
}

int func_1602()
{
    return 0;
}

void func_1603()
{
    
}

void func_1604()
{
    if (global6 == 0x44 || global6 == 0xbc)
    {
        return;
    }
    else
    {
        CaptureModule(0x5, 0);
        CaptureModule(0x1);
    }
}

int func_1605()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1606()
{
    func_22(0x1c2, 0, 1.0f);
    func_78(func_1607);
}

void func_1607()
{
    func_1610();
}

void func_1608()
{
    
}

void func_1609()
{
    int var0;
    int var1;
    PostureModule(0, -LinkModuleF(0x7, 0));
    PostureModule(0x2);
    var0 = 0;
    var1 = WorkModule(0x6, 0x13000120);
    if (var1 == 0x1)
    {
        var0 = 0x4;
    }
    else if (var1 == 0x3)
    {
        var0 = 0x8;
    }
    MotionModule(0x29, var0);
    CaptureModule(0x2);
    LinkModule(0x2716, 0, 0x3);
}

int func_1610()
{
    if (global3 == 0)
    {
        if (func_1612() != 0)
        {
            return 0x1;
        }
    }
    if (func_1613() != 0)
    {
        return 0x1;
    }
    return 0;
}

void func_1611()
{
    
}

int func_1612()
{
    return 0;
}

int func_1613()
{
    return 0;
}

void func_1614()
{
    
}

void func_1615()
{
    if (global6 == 0xbb || global6 == 0xbc)
    {
        return;
    }
    else
    {
        CaptureModule(0x1);
    }
}

int func_1616()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1617()
{
    func_22(0x1c3, 0, 1.0f);
    func_78(func_1618);
}

void func_1618()
{
    func_1621();
}

void func_1619()
{
    
}

void func_1620()
{
    int var0;
    int var1;
    var0 = 0;
    var1 = WorkModule(0x6, 0x13000120);
    if (var1 == 0x1)
    {
        var0 = 0x4;
    }
    else if (var1 == 0x3)
    {
        var0 = 0x8;
    }
    MotionModule(0x29, var0);
    CaptureModule(0x2);
}

int func_1621()
{
    if (global3 == 0)
    {
        if (func_1623() != 0)
        {
            return 0x1;
        }
    }
    if (func_1624() != 0)
    {
        return 0x1;
    }
    return 0;
}

void func_1622()
{
    
}

int func_1623()
{
    return 0;
}

int func_1624()
{
    return 0;
}

void func_1625()
{
    
}

void func_1626()
{
    if (global6 == 0xbc)
    {
        return;
    }
    else
    {
        CaptureModule(0x1);
    }
}

int func_1627()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1628()
{
    func_22(WorkModule(0x6, 0x11000002), 0, 1.0f);
    func_78(func_1629);
}

void func_1629()
{
    if (MotionModule(0x2712))
    {
        func_16(0x4c, 0);
    }
    func_1632();
}

void func_1630()
{
    if (global5 == 0xba || global5 == 0xbb)
    {
        
    }
    else
    {
        WorkModule(0x2710, 0x20000054);
    }
}

void func_1631()
{
    int var0;
    int var1;
    var0 = 0;
    var1 = WorkModule(0x6, 0x13000120);
    if (var1 == 0x1)
    {
        var0 = 0x4;
    }
    else if (var1 == 0x3)
    {
        var0 = 0x8;
    }
    MotionModule(0x29, var0);
    CaptureModule(0x2);
    LinkModule(0x2716, 0, 0x3);
}

int func_1632()
{
    if (global3 == 0)
    {
        if (func_1634() != 0)
        {
            return 0x1;
        }
    }
    if (func_1635() != 0)
    {
        return 0x1;
    }
    return 0;
}

void func_1633()
{
    
}

int func_1634()
{
    return 0;
}

int func_1635()
{
    return 0;
}

void func_1636()
{
    
}

void func_1637()
{
    if (global5 == 0xba && global5 == 0xbb)
    {
        CaptureModule(0x5, 0);
        CaptureModule(0x1);
    }
    else
    {
        if (MotionModule(0x2712))
        {
            CaptureModule(0x5, 0);
        }
        CaptureModule(0x1);
    }
}

int func_1638()
{
    StatusModule(0x5, 0xffffffff, 0x33, 0x7, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1639()
{
    if (WorkModule(0x2712, 0x2100000d))
    {
        func_22(0x1d4, 0, 1.0f);
    }
    else if (WorkModule(0x6, 0x13000120) == 0x3)
    {
        func_22(0x1d7, 0, 1.0f);
    }
    else
    {
        func_22(0x1d1, 0, 1.0f);
    }
    LinkModule(0x2716, 0, 0x3);
    func_1641();
    func_78(func_1640);
}

void func_1640()
{
    if (StatusModule(0x6) == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        func_1641();
    }
    if (CancelModule(0x2713) == 0x1)
    {
        if (global18 == 0 && func_39() != 0)
        {
            return;
        }
        else if (global18 == 0x2 && func_41() != 0)
        {
            return;
        }
    }
}

void func_1641()
{
    if (global18 == 0)
    {
        KineticModule(0, 0x6);
        GroundModule(0x2710, 0x1);
    }
    else
    {
        KineticModule(0, 0xa);
        GroundModule(0x2710, 0x5);
    }
}

void func_1642()
{
    
}

int func_1643()
{
    StatusModule(0x5, 0xffffffff, 0x33, 0x7, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1644()
{
    func_22(WorkModule(0x6, 0x11000002), 0, 1.0f);
    func_1646();
    func_78(func_1645);
}

void func_1645()
{
    if (StatusModule(0x6) == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        func_1646();
    }
    if (CancelModule(0x2713) == 0x1)
    {
        if (global18 == 0 && func_39() != 0)
        {
            return;
        }
        else if (global18 == 0x2 && func_41() != 0)
        {
            return;
        }
    }
}

void func_1646()
{
    int var0;
    if (global18 == 0)
    {
        KineticModule(0, 0x6);
        GroundModule(0x2710, 0x1);
    }
    else
    {
        var0 = WorkModule(0x6, 0x11000002);
        if (var0 == 0x1d3 || var0 == 0x1d9)
        {
            KineticModule(0, 0xd);
        }
        else
        {
            KineticModule(0, 0xa);
        }
        GroundModule(0x2710, 0x5);
    }
}

void func_1647()
{
    
}

int func_1648()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1649()
{
    int var0;
    var0 = MotionModule(0x7);
    if (var0 == 0x1d3 || var0 == 0x1d9 || var0 == 0x1d6)
    {
        func_78(func_1650);
    }
    else
    {
        func_78(func_1651);
    }
}

void func_1650()
{
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0xe, 0);
        return;
    }
}

void func_1651()
{
    
}

void func_1652()
{
    
}

int func_1653()
{
    StatusModule(0x5, 0xffffffff, 0x33, 0x7, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1654()
{
    func_22(0x1ce, 0, 1.0f);
    func_78(func_1655);
}

void func_1655()
{
    
}

void func_1656()
{
    
}

void func_1657()
{
    int var0;
    int var1;
    PostureModule(0, LinkModuleF(0x7, 0));
    PostureModule(0x2);
    var0 = WorkModule(0x6, 0x13000120);
    var1 = 0;
    if (var0 == 0x1)
    {
        var1 = 0x1;
    }
    else if (var0 == 0x3)
    {
        var1 = 0x2;
    }
    MotionModule(0x29, var1);
    LinkModule(0x2716, 0, 0x3);
}

void func_1658()
{
    if (global6 != 0x44)
    {
        CaptureModule(0x4);
    }
}

int func_1659()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1660()
{
    int var0;
    float var1;
    int var2;
    float var3;
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    func_22(0x1da, 0, 1.0f);
    CameraModule(0x2720, 0x7);
    var0 = WorkModule(0x6, 0x10000000);
    var1 = PostureModuleF(0);
    var2 = 0x64;
    CameraModule(0x271e, var0, var1, var2);
    var3 = PostureModuleF(0x2);
    WorkModule(0, var3, 0x1000006);
    func_78(func_1655);
}

void func_1661()
{
    
}

void func_1662()
{
    int var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    float var7;
    int var8;
    var0 = WorkModule(0x6, 0x10000000);
    var1 = PostureModuleF(0x1);
    var2 = PostureModuleF(0x2);
    var3 = PostureModuleF(0x3);
    var4 = var1;
    var5 = var2;
    var6 = var3;
    var7 = PostureModuleF(0);
    var8 = WorkModule(0x6, 0x12000147);
    CameraModule(0x271f, var0, var4, var5, var6, var7, var8, 0);
}

void func_1663()
{
    int var0;
    int var1;
    CaptureModule(0x2);
    var0 = 0;
    var1 = WorkModule(0x6, 0x13000120);
    if (0x1 == var1)
    {
        var0 = 0x1;
    }
    else if (0x3 == var1)
    {
        var0 = 0x2;
    }
    else
    {
        
    }
    MotionModule(0x29, var0);
    LinkModule(0x2716, 0, 0x3);
}

void func_1664()
{
    float var0;
    if (WorkModule(0x10, 0x2100000d) == 0 && LinkModule(0xd, 0) == 0x2)
    {
        var0 = PostureModuleF(0x2);
        if (var0 < WorkModuleF(0, 0x1000006))
        {
            CameraModule(0x2720, 0x7);
            WorkModule(0x11, 0x2100000d);
        }
    }
}

void func_1665()
{
    if (global6 != 0x44)
    {
        CaptureModule(0x4);
    }
    else
    {
        LinkModule(0xb);
    }
}

int func_1666()
{
    StatusModule(0x5, 0x2, 0x33, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3ea, 0, 0);
    return 0;
}

void func_1667()
{
    int var0;
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    WorkModule(0x2711, 0x2000001c);
    if (MotionModule(0x7) == 0xffffffff)
    {
        var0 = randi(0, 0x5);
        if (var0 == 0x1)
        {
            func_22(0xd0, 0, 1.0f);
        }
        else if (var0 == 0x2)
        {
            func_22(0xd1, 0, 1.0f);
        }
        else if (var0 == 0x3)
        {
            func_22(0xd2, 0, 1.0f);
        }
        else if (var0 == 0x4)
        {
            func_22(0xd3, 0, 1.0f);
        }
        else
        {
            func_22(0xcf, 0, 1.0f);
        }
    }
    MotionModule(0x4, 0);
    HitModule(0x2710, 0x2);
    func_78(func_1668);
}

void func_1668()
{
    if (WorkModule(0x10, 0x2100000d) && global9 >= 3.0f)
    {
        func_16(0xe, 0);
    }
}

void func_1669()
{
    
}

int func_1670()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1671()
{
    WorkModule(0x2710, 0x20000065);
    func_22(0x7c, 0, 1.0f);
    func_78(func_1672);
}

int func_1672()
{
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0xc0, 0);
        return 0x1;
    }
    if (func_1684())
    {
        return 0x1;
    }
    return 0;
}

void func_1673()
{
    
}

int func_1674()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1675()
{
    if (ControlModuleF(0x5) <= 0)
    {
        LinkModule(0x2713, 0, 0x4ba);
    }
}

void func_1676()
{
    WorkModule(0x2710, 0x20000065);
    func_22(0x96, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_1675();
    }
    global16 = func_1675;
    func_78(func_1677);
}

int func_1677()
{
    if (func_1684())
    {
        return 0x1;
    }
    return 0;
}

void func_1678()
{
    
}

int func_1679()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0x1, 0, 0x4, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1680()
{
    func_22(WorkModule(0x6, 0x11000002), 0, 1.0f);
    func_78(func_1681);
}

int func_1681()
{
    if (func_1691())
    {
        return 0x1;
    }
    return 0;
}

void func_1682()
{
    
}

void func_1683()
{
    float var0;
    float var1;
    float var2;
    float var3;
    int var4;
    int var5;
    if (global4 == 0xbf)
    {
        var0 = WorkModuleF(0, 0x20001c0);
        var1 = WorkModuleF(0, 0x20001c1);
        var2 = WorkModuleF(0, 0x20001c2);
        var3 = DamageModuleF(0) * var1 + var0;
        ControlModule(0x6, var3, 0, var2);
        var4 = 0;
        var5 = WorkModule(0x6, 0x13000120);
        if (0x1 == var5)
        {
            var4 = 0x4;
        }
        else if (0x3 == var5)
        {
            var4 = 0x8;
        }
        MotionModule(0x29, var4);
        CaptureModule(0x2);
        LinkModule(0x2716, 0, 0x3);
    }
    else if (global4 == 0xc0)
    {
        var4 = 0;
        var5 = WorkModule(0x6, 0x13000120);
        if (0x1 == var5)
        {
            var4 = 0x1;
        }
        else if (0x3 == var5)
        {
            var4 = 0x2;
        }
        MotionModule(0x29, var4);
    }
}

int func_1684()
{
    if (global3 == 0)
    {
        if (func_1686() != 0)
        {
            return 0x1;
        }
    }
    if (func_1687() != 0)
    {
        return 0x1;
    }
    return 0;
}

void func_1685()
{
    
}

int func_1686()
{
    float var0;
    float var1;
    if (global4 == 0xc0)
    {
        var0 = ControlModuleF(0x5);
        if (LinkModule(0xd, 0) == 0)
        {
            var1 = WorkModuleF(0, 0x20001c2);
        }
        else
        {
            var1 = WorkModuleF(0, 0x20001c3);
        }
        ControlModule(0x6, var0, 1.0f, var1);
    }
    return 0;
}

int func_1687()
{
    return 0;
}

void func_1688()
{
    
}

void func_1689()
{
    float var0;
    if (global6 != 0xc0 && global6 != 0xc1)
    {
        var0 = -LinkModuleF(0x7, 0);
        PostureModule(0, var0);
        PostureModule(0x2);
        CaptureModule(0x1);
    }
}

void func_1690()
{
    int var0;
    int var1;
    var0 = 0;
    var1 = WorkModule(0x6, 0x13000120);
    if (var1 == 0x1)
    {
        var0 = 0x4;
    }
    else if (var1 == 0x3)
    {
        var0 = 0x8;
    }
    MotionModule(0x29, var0);
}

int func_1691()
{
    if (global3 == 0)
    {
        if (func_1693() != 0)
        {
            return 0x1;
        }
    }
    if (func_1694() != 0)
    {
        return 0x1;
    }
    return 0;
}

void func_1692()
{
    
}

int func_1693()
{
    return 0;
}

int func_1694()
{
    return 0;
}

void func_1695()
{
    
}

void func_1696()
{
    CaptureModule(0x4);
}

int func_1697()
{
    StatusModule(0x5, 0, 0x4d, 0x1, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0, 0x2, 0, 0x800000);
    return 0;
}

void func_1698()
{
    BattleObject(0x9);
    WorkModule(0x2711, 0x20000003);
    func_22(0xe9, 0, 1.0f);
    func_78(func_1699);
}

void func_1699()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (MotionModule(0x2712) == 0x1 && global18 == 0)
    {
        func_16(0, 0);
        return;
    }
}

void func_1700()
{
    
}

int func_1701()
{
    StatusModule(0x5, 0, 0x4e, 0x2, 0, 0x1, 0x2000, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0, 0x80002, 0, 0x800000);
    return 0;
}

void func_1702()
{
    BattleObject(0x9);
    WorkModule(0x2711, 0x20000003);
    if (func_88() >= 0)
    {
        func_22(0xea, 0, 1.0f);
    }
    else
    {
        func_22(0xeb, 0, 1.0f);
    }
    func_78(func_1703);
}

void func_1703()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return;
    }
    if (MotionModule(0x2712) == 0x1 && global18 == 0)
    {
        func_16(0, 0);
        return;
    }
}

void func_1704()
{
    
}

int func_1705()
{
    StatusModule(0x5, 0x2, 0x33, 0x5, 0x3, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0x1, 0, 0x2, 0, 0x800000);
    return 0;
}

void func_1706()
{
    BattleObject(0x9);
    func_75();
    func_76();
    WorkModule(0x7, 0, 0x10000004);
    WorkModule(0x7, WorkModule(0x6, 0x12000084), 0x11000002);
    WorkModule(0x16, 0x1e000017);
    WorkModule(0x16, 0x1e000016);
    if (!StopModule(0x1))
    {
        func_1707();
    }
    global16 = func_1707;
    func_78(func_1708);
}

void func_1707()
{
    if (WorkModule(0x6, 0x11000002) > 0)
    {
        WorkModule(0xa, 0x11000002);
        if (WorkModule(0x6, 0x11000002) == 0)
        {
            func_40();
            KineticModule(0, 0x27);
            MotionModule(0x4, 1.0f);
        }
    }
}

void func_1708()
{
    if (func_41())
    {
        return;
    }
    if (WorkModule(0x15, 0x1e000017) == 0x1 && ControlModule(0x2722, 0x2) < WorkModule(0x6, 0x12000081) && WorkModule(0x6, 0x11000002) > 0)
    {
        func_16(0x67, 0x1);
        return;
    }
    if (WorkModule(0x15, 0x1e000016) == 0x1 && global32 >= WorkModuleF(0, 0x200001f) && WorkModule(0x6, 0x11000002) > 0)
    {
        func_16(0x67, 0x1);
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0xe, 0);
        return;
    }
}

void func_1709()
{
    
}

int func_1710()
{
    StatusModule(0x5, 0x2, 0x33, 0x5, 0x3, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0x2, 0, 0);
    return 0;
}

void func_1711()
{
    BattleObject(0x9);
    func_75();
    func_76();
    WorkModule(0x7, WorkModule(0x6, 0x12000084), 0x11000002);
    if (!StopModule(0x1))
    {
        func_1712();
    }
    global16 = func_1712;
    func_78(func_1713);
}

void func_1712()
{
    if (WorkModule(0x6, 0x11000002) > 0)
    {
        WorkModule(0xa, 0x11000002);
        if (WorkModule(0x6, 0x11000002) == 0)
        {
            func_40();
            KineticModule(0, 0x28);
            MotionModule(0x4, 1.0f);
        }
    }
}

void func_1713()
{
    if (func_41())
    {
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0xe, 0);
        return;
    }
}

void func_1714()
{
    
}

int func_1715()
{
    StatusModule(0x5, 0x2, 0x33, 0x5, 0x3, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0x1, 0, 0x2, 0, 0x800000);
    return 0;
}

void func_1716()
{
    BattleObject(0x9);
    if (!StopModule(0x1))
    {
        func_550();
    }
    global16 = func_550;
    func_78(func_1717);
}

void func_1717()
{
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0xe, 0);
        return;
    }
}

void func_1718()
{
    
}

float func_1719()
{
    float var0;
    int var1;
    var0 = 0;
    var1 = GroundModule(0xa);
    if ((var1 & 0x4) != 0)
    {
        var0 = -1.0f;
    }
    else if ((var1 & 0x2) != 0)
    {
        var0 = 1.0f;
    }
    return var0;
}

void func_1720(int arg0)
{
    int var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    var1 = GroundModule(0xa);
    if (var1 != 0)
    {
        if (var1 & 0x8)
        {
            var2 = GroundModuleF(0x3, 0x8);
            var3 = GroundModuleF(0x4, 0x8);
            var4 = GroundModuleF(0x5, 0x8);
            var5 = GroundModuleF(0x6, 0x8);
        }
        else if (var1 & 0x1)
        {
            var2 = GroundModuleF(0x3, 0x1);
            var3 = GroundModuleF(0x4, 0x1);
            var4 = GroundModuleF(0x5, 0x1);
            var5 = GroundModuleF(0x6, 0x1);
        }
        else if (var1 & 0x2)
        {
            var2 = GroundModuleF(0x3, 0x2);
            var3 = GroundModuleF(0x4, 0x2);
            var4 = GroundModuleF(0x5, 0x2);
            var5 = GroundModuleF(0x6, 0x2);
        }
        else if (var1 & 0x4)
        {
            var2 = GroundModuleF(0x3, 0x4);
            var3 = GroundModuleF(0x4, 0x4);
            var4 = GroundModuleF(0x5, 0x4);
            var5 = GroundModuleF(0x6, 0x4);
        }
        var6 = MathF(0x1, -var4, var5);
        EffectModule(0x3, arg0, var2, var3, GroundModuleF(0xc), 0, 0, var6, 1.0f, 0, 0xffffffff);
    }
}

void func_1721()
{
    int var0;
    float var1;
    float var2;
    float var3;
    int var4;
    float var5;
    float var6;
    int var7;
    var0 = StatusModule(0);
    if (var0 == 0x64 || var0 == 0x65)
    {
        func_1720(0x100002b);
        ControlModule(0x2714, 0xd, 0);
    }
    else if (var0 == 0x66)
    {
        func_22(0xec, 0, 1.0f);
        var1 = func_1719();
        FighterUtil(0x3, var1, var1, 1.0f, 0x1);
        HitModule(0x2, WorkModule(0x6, 0x12000085));
        func_1720(0x100002b);
        ControlModule(0x2714, 0xd, 0);
    }
    else if (var0 == 0x67)
    {
        var2 = 0;
        var1 = func_1719();
        if (MotionModule(0x7) == 0xec)
        {
            var2 = MotionModuleF(0x1);
        }
        else
        {
            func_1720(0x100002b);
        }
        if (var3 != 0)
        {
            func_23(0xed);
        }
        else
        {
            func_22(0xed, var2, 1.0f);
        }
        if (var1 != 0)
        {
            FighterUtil(0x3, var1, var1, 1.0f, 0x1);
        }
        HitModule(0x2, WorkModule(0x6, 0x12000085));
    }
    else if (var0 == 0x6b)
    {
        func_22(0xed, 0, 1.0f);
        var1 = func_1719();
        if (var1 != 0)
        {
            FighterUtil(0x3, var1, var1, 1.0f, 0x1);
            func_1720(0x1000086);
        }
        WorkModule(0, var1, 0x2);
        WorkModule(0x7, WorkModule(0x6, 0x120000ae), 0x10000005);
    }
    else if (var0 == 0x6c)
    {
        func_22(0xef, 0, 1.0f);
        var1 = func_1719();
        if (var1 == -1.0f)
        {
            GroundModule(0x2719, 0x4);
        }
        else
        {
            GroundModule(0x2719, 0x2);
        }
        FighterUtil(0x3, var1, var1, 1.0f, 0x1);
        func_1720(0x1000086);
    }
    else if (var0 == 0x6d)
    {
        var4 = WorkModule(0x6, 0x1000000c);
        WorkModule(0x9, 0x1000000c);
        var5 = (float)WorkModule(0x6, 0x120000ba);
        if (var4 > 0)
        {
            var6 = WorkModuleF(0, 0x20000bb);
            var5 *= MathF(0x2, var6, var4 - 0x1);
        }
        var7 = (int)var5;
        WorkModule(0x7, var7, 0x11000004);
        if (PostureModuleF(0) == -1.0f)
        {
            GroundModule(0x2719, 0x4);
        }
        else
        {
            GroundModule(0x2719, 0x2);
        }
    }
    else if (var0 == 0x6e || var0 == 0x70 || var0 == 0x6f)
    {
        
    }
    else if (var0 == 0x68)
    {
        func_22(0xee, 0, 1.0f);
        FighterUtil(0x4, PostureModuleF(0), 0x1);
        ControlModule(0x2714, 0xd, 0);
        func_1720(0x100002b);
    }
    else if (var0 == 0x69)
    {
        func_22(0xff, 0, 1.0f);
        var1 = PostureModuleF(0);
        FighterUtil(0x3, var1, -var1, -1.0f, 0x1);
        ControlModule(0x2714, 0xd, 0);
    }
    else if (var0 == 0x6a)
    {
        func_22(0x101, 0, 1.0f);
        FighterUtil(0x4, PostureModuleF(0), 0x1);
    }
}

void func_1722()
{
    float var0;
    var0 = WorkModuleF(0, 0x1000006);
    if (var0 != 0)
    {
        FighterUtil(0x6, var0);
    }
}

int func_1723()
{
    int var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    var0 = StatusModule(0);
    if (var0 == 0x6c || var0 == 0x6d)
    {
        var1 = PostureModuleF(0);
        var2 = sys_40(0xf, var1);
        WorkModule(0, var2, 0x1000006);
        var3 = 0;
        var4 = 1.0f;
        if (var1 == 1.0f)
        {
            var3 = GroundModuleF(0x5, 0x2);
            var4 = GroundModuleF(0x6, 0x2);
        }
        else
        {
            var3 = GroundModuleF(0x5, 0x4);
            var4 = GroundModuleF(0x6, 0x4);
        }
        var5 = MathF(0x1, var3, var4);
        var6 = var5 * -var1 * (float)0xb4 / M_PI + 90.0f;
        WorkModule(0, var6, 0x1000007);
    }
    else if (var0 == 0x66 || var0 == 0x67 || var0 == 0x6b)
    {
        if (MotionModuleF(0x9) == 0)
        {
            var2 = sys_40(0xf, PostureModuleF(0));
            WorkModule(0, var2, 0x1000006);
        }
    }
    return 0;
}

int func_1724()
{
    float var0;
    var0 = WorkModuleF(0, 0x1000007);
    if (var0 >= WorkModuleF(0, 0x20000b8) || var0 <= WorkModuleF(0, 0x20000b9))
    {
        func_16(0xe, 0);
        return 0x1;
    }
    return 0;
}

void func_1725()
{
    if (global4 == 0x6a)
    {
        KineticModule(0x7, 0x1);
    }
}

int func_1726()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1, 0x8000000, 0x800, 0x4000);
    return 0;
}

int func_1727()
{
    int var0;
    var0 = ItemModule(0x11);
    if (var0 == 0x2f)
    {
        return 0x133;
    }
    else if (var0 == 0x33)
    {
        return 0x139;
    }
    else if (var0 == 0x34)
    {
        return 0x139;
    }
    else if (var0 == 0x38)
    {
        return 0x13d;
    }
    else if (var0 == 0x35)
    {
        return 0x143;
    }
    else if (var0 == 0x3c)
    {
        return 0x149;
    }
    else if (var0 == 0x3a)
    {
        WorkModule(0, ItemModuleF(0, 0) + 0, 0x1000007);
        return 0x14f;
    }
    return 0x133;
}

float func_1728()
{
    int var0;
    int var1;
    int var2;
    var0 = ItemModule(0x11);
    if (var0 == 0x2f)
    {
        var1 = 0;
    }
    else if (var0 == 0x33)
    {
        var1 = 0x1;
    }
    else if (var0 == 0x34)
    {
        var1 = 0x1;
    }
    else if (var0 == 0x38)
    {
        var1 = 0x3;
    }
    else if (var0 == 0x35)
    {
        var1 = 0x4;
    }
    else if (var0 == 0x3c)
    {
        var1 = 0x5;
    }
    else if (var0 == 0x3a)
    {
        var1 = 0x6;
    }
    if (global4 == 0x92)
    {
        var2 = 0;
    }
    else if (global4 == 0x93)
    {
        var2 = 0x1;
    }
    else if (global4 == 0x94 || global4 == 0x95)
    {
        var2 = 0x2;
    }
    else if (global4 == 0x97)
    {
        var2 = 0x4;
    }
    return sys_40(0x1, var1, var2);
}

void func_1729()
{
    int var0;
    var0 = func_1727();
    func_22(var0, 0, func_1728());
    if (var0 == 0x133)
    {
        BattleObject(0xd, 0x2, 0x55, 0x1);
        BattleObject(0x33);
    }
    else if (var0 == 0x139)
    {
        BattleObject(0xd, 0x2, 0x59, 0x1);
        BattleObject(0x37);
    }
    else if (var0 == 0x13d)
    {
        BattleObject(0xd, 0x2, 0x61, 0x1);
        BattleObject(0x3f);
    }
    else if (var0 == 0x143)
    {
        BattleObject(0xd, 0x2, 0x65, 0x1);
        BattleObject(0x43);
    }
    else if (var0 == 0x149)
    {
        BattleObject(0xd, 0x2, 0x69, 0x1);
        BattleObject(0x4b);
    }
    else if (var0 == 0x14f)
    {
        BattleObject(0xd, 0x2, 0x6d, 0x1);
        BattleObject(0x47);
    }
    func_78(func_1731);
}

int func_1730()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return 0x1;
    }
    if (CancelModule(0x2713) == 0x1)
    {
        if (global18 == 0 && func_39() != 0)
        {
            return 0x1;
        }
        else if (global18 == 0x2 && func_41() != 0)
        {
            return 0x1;
        }
    }
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (MotionModule(0x2712) == 0x1 && global18 == 0)
    {
        func_16(0, 0);
        return 0x1;
    }
    return 0;
}

void func_1731()
{
    if (func_1730() == 0x1)
    {
        return;
    }
}

void func_1732()
{
    int var0;
    if (ItemModule(0x4) == 0x1)
    {
        ItemModule(0x13, 0x65);
        var0 = ItemModule(0x11);
        if (var0 == 0x2f || var0 == 0x3a)
        {
            ItemModule(0xa, 0, 1.0f);
        }
    }
}

int func_1733()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1, 0x8000000, 0x800, 0x4000);
    return 0;
}

int func_1734()
{
    int var0;
    var0 = ItemModule(0x11);
    if (var0 == 0x2f)
    {
        return 0x134;
    }
    else if (var0 == 0x33)
    {
        return 0x13a;
    }
    else if (var0 == 0x34)
    {
        return 0x13a;
    }
    else if (var0 == 0x38)
    {
        return 0x13e;
    }
    else if (var0 == 0x35)
    {
        return 0x144;
    }
    else if (var0 == 0x3c)
    {
        return 0x14a;
    }
    else if (var0 == 0x3a)
    {
        WorkModule(0, ItemModuleF(0, 0) + 0, 0x1000007);
        return 0x150;
    }
    return 0x134;
}

void func_1735()
{
    int var0;
    if (global5 == 0x8)
    {
        KineticModule(0, 0x7);
    }
    func_33();
    var0 = func_1734();
    func_22(var0, 0, func_1728());
    if (var0 == 0x134)
    {
        BattleObject(0xd, 0x2, 0x56, 0x1);
        BattleObject(0x34);
    }
    else if (var0 == 0x13a)
    {
        BattleObject(0xd, 0x2, 0x5a, 0x1);
        BattleObject(0x38);
    }
    else if (var0 == 0x13e)
    {
        BattleObject(0xd, 0x2, 0x62, 0x1);
        BattleObject(0x40);
    }
    else if (var0 == 0x144)
    {
        BattleObject(0xd, 0x2, 0x66, 0x1);
        BattleObject(0x44);
    }
    else if (var0 == 0x14a)
    {
        BattleObject(0xd, 0x2, 0x6a, 0x1);
        BattleObject(0x4c);
    }
    else if (var0 == 0x150)
    {
        BattleObject(0xd, 0x2, 0x6e, 0x1);
        BattleObject(0x48);
    }
    func_78(func_1736);
}

void func_1736()
{
    if (func_1730() == 0x1)
    {
        return;
    }
}

void func_1737()
{
    func_1732();
}

void func_1738(int arg0)
{
    if (arg0 == 0x1)
    {
        ItemModule(0x1c, 0, 0);
    }
}

int func_1739()
{
    int var0;
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x20001, 0x8000000, 0, 0);
    var0 = ItemModule(0x11);
    if (var0 == 0x33 || var0 == 0x34)
    {
        StatusModule(0x2711, 0x95);
        func_1738(0x1);
        if (global48 >= WorkModuleF(0, 0x2000007))
        {
            PostureModule(0x2712);
        }
        else if (-global48 >= WorkModuleF(0, 0x2000007))
        {
            PostureModule(0x2711);
        }
        return 0x1;
    }
    return 0;
}

int func_1740()
{
    int var0;
    var0 = ItemModule(0x11);
    if (var0 == 0x2f)
    {
        return 0x135;
    }
    else if (var0 == 0x33)
    {
        return 0x13b;
    }
    else if (var0 == 0x34)
    {
        return 0x13b;
    }
    else if (var0 == 0x38)
    {
        return 0x13f;
    }
    else if (var0 == 0x35)
    {
        return 0x145;
    }
    else if (var0 == 0x3c)
    {
        return 0x14b;
    }
    else if (var0 == 0x3a)
    {
        WorkModule(0, ItemModuleF(0, 0) + 0, 0x1000007);
        return 0x151;
    }
    return 0x135;
}

void func_1741()
{
    int var0;
    if (global5 == 0x8)
    {
        KineticModule(0, 0x7);
    }
    if (global48 >= WorkModuleF(0, 0x2000007))
    {
        PostureModule(0x2712);
    }
    else if (-global48 >= WorkModuleF(0, 0x2000007))
    {
        PostureModule(0x2711);
    }
    PostureModule(0x2);
    var0 = func_1740();
    WorkModule(0x7, var0, 0x11000002);
    func_22(var0, 0, func_1728());
    if (var0 == 0x135)
    {
        BattleObject(0xd, 0x2, 0x57, 0x1);
    }
    else if (var0 == 0x13f)
    {
        BattleObject(0xd, 0x2, 0x63, 0x1);
    }
    else if (var0 == 0x145)
    {
        BattleObject(0xd, 0x2, 0x67, 0x1);
    }
    else if (var0 == 0x14b)
    {
        BattleObject(0xd, 0x2, 0x6b, 0x1);
    }
    else if (var0 == 0x151)
    {
        BattleObject(0xd, 0x2, 0x6f, 0x1);
    }
    WorkModule(0x16, 0x1e00007c);
    func_78(func_1742);
}

void func_1742()
{
    int var0;
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    var0 = func_1743();
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    if (WorkModule(0x15, 0x1e00007c) == 0x1 && var0 == 0x1 && ControlModule(0x2712, 0) == 0x1 && global18 == 0)
    {
        func_16(0x96, 0x1);
        return;
    }
    if (var0 == 0x1 && global18 == 0)
    {
        func_16(0x95, 0);
        return;
    }
}

int func_1743()
{
    if (WorkModule(0x10, 0x21000011))
    {
        return 0x1;
    }
    return 0;
}

void func_1744()
{
    WorkModule(0, MotionModuleF(0x1), 0x1000006);
    if (!(global6 == 0x96 || global6 == 0x95))
    {
        func_1732();
    }
}

int func_1745()
{
    func_1746(0, 0, 0x40);
    return 0;
}

int func_1746(int arg0, int arg1, int arg2)
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, arg0, arg1, arg2, 0x9c0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x20001, 0x8000000, 0, 0);
    return 0;
}

void func_1747()
{
    int var0;
    float var1;
    float var2;
    int var3;
    float var4;
    var0 = func_1740() + 0x2;
    var1 = WorkModuleF(0, 0x30000e1);
    var2 = (float)MotionModule(0, var0);
    var3 = (int)(var2 / var1);
    WorkModule(0x7, var3, 0x11000006);
    var4 = WorkModuleF(0, 0x25);
    if (var4 > 0)
    {
        var3 = (int)((float)var3 * var4);
    }
    var1 = var2 / (float)var3;
    WorkModule(0x7, var3, 0x11000005);
    WorkModule(0x7, var3, 0x11000007);
    func_22(var0, 0, var1);
    func_78(func_1748);
}

void func_1748()
{
    int var0;
    var0 = func_1749();
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return;
    }
    else if (global18 == 0)
    {
        if (var0)
        {
            func_16(0x95, 0);
            return;
        }
        if (ControlModule(0x2713, 0) == 0x1)
        {
            func_16(0x95, 0x1);
            return;
        }
    }
}

int func_1749()
{
    if (StatusModule(0x6) != 0x1)
    {
        WorkModule(0xa, 0x11000005);
    }
    if (WorkModule(0x6, 0x11000005) <= 0)
    {
        return 0x1;
    }
    return 0;
}

void func_1750()
{
    PhysicsModule(0x8);
    if (!(global6 == 0x95))
    {
        func_1732();
    }
}

int func_1751()
{
    int var0;
    var0 = ItemModule(0x11);
    if (var0 == 0x33 || var0 == 0x34)
    {
        StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0x860);
    }
    else
    {
        StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0x4, 0x10, 0x41, 0x860);
    }
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x20001, 0x8000000, 0x800, 0x4000);
    return 0;
}

void func_1752()
{
    int var0;
    int var1;
    float var2;
    float var3;
    WorkModule(0x2710, 0x21000012);
    var0 = ItemModule(0x11);
    if (var0 == 0x33 || var0 == 0x34)
    {
        func_33();
    }
    ControlModule(0x271b);
    var1 = func_1740();
    var2 = WorkModuleF(0, 0x1000006);
    var3 = 1.0f;
    var0 = ItemModule(0x11);
    if (var0 == 0x33 || var0 == 0x34)
    {
        var3 /= WorkModuleF(0, 0x3000100);
    }
    MotionModule(0x26, var1, var2, var3);
    if (var1 == 0x13b)
    {
        BattleObject(0xd, 0x2, 0x5b, 0x1);
    }
    else
    {
        if (var1 == 0x135)
        {
            BattleObject(0x35);
        }
        else if (var1 == 0x13f)
        {
            BattleObject(0x41);
        }
        else if (var1 == 0x145)
        {
            BattleObject(0x45);
        }
        else if (var1 == 0x14b)
        {
            BattleObject(0x4d);
        }
        else if (var1 == 0x151)
        {
            BattleObject(0x49);
        }
        var1++;
        if (MotionModule(0xc, var1) == 0x1)
        {
            WorkModule(0x11, 0x21000010);
        }
    }
    WorkModule(0x7, var1, 0x11000002);
    if (!StopModule(0x1))
    {
        func_1753();
    }
    global16 = func_1753;
    func_78(func_1754);
}

void func_1753()
{
    if (ControlModule(0x2713, 0) == 0x1)
    {
        WorkModule(0x11, 0x2100000e);
    }
    else if (ControlModule(0x2710, 0) == 0x1)
    {
        WorkModule(0x11, 0x2100000f);
    }
}

void func_1754()
{
    if (func_1730() == 0x1)
    {
        return;
    }
    if (WorkModule(0x10, 0x21000010) == 0x1)
    {
        if (WorkModule(0x10, 0x2100000d) == 0x1 && WorkModule(0x10, 0x2100000e) == 0 || WorkModule(0x10, 0x2100000d) == 0x1 && WorkModule(0x10, 0x2100000f) == 0x1)
        {
            func_22(WorkModule(0x6, 0x11000002), 0, func_1728());
            WorkModule(0x12, 0x21000010);
        }
    }
}

void func_1755()
{
    func_1732();
    if (ItemModule(0x11) == 0x33 || ItemModule(0x11) == 0x34)
    {
        
    }
}

int func_1756()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1, 0x8000000, 0x800, 0x4000);
    return 0;
}

int func_1757()
{
    int var0;
    var0 = ItemModule(0x11);
    if (var0 == 0x2f)
    {
        return 0x138;
    }
    else if (var0 == 0x33)
    {
        return 0x13c;
    }
    else if (var0 == 0x34)
    {
        return 0x13c;
    }
    else if (var0 == 0x38)
    {
        return 0x142;
    }
    else if (var0 == 0x35)
    {
        return 0x148;
    }
    else if (var0 == 0x3c)
    {
        return 0x14e;
    }
    else if (var0 == 0x3a)
    {
        WorkModule(0, ItemModuleF(0, 0) + 0, 0x1000007);
        return 0x154;
    }
    return 0x138;
}

void func_1758()
{
    int var0;
    var0 = func_1757();
    func_22(var0, 0, func_1728());
    if (var0 == 0x138)
    {
        BattleObject(0xd, 0x2, 0x58, 0x1);
        BattleObject(0x36);
    }
    else if (var0 == 0x13c)
    {
        BattleObject(0xd, 0x2, 0x5c, 0x1);
        BattleObject(0x3a);
    }
    else if (var0 == 0x142)
    {
        BattleObject(0xd, 0x2, 0x64, 0x1);
        BattleObject(0x42);
    }
    else if (var0 == 0x148)
    {
        BattleObject(0xd, 0x2, 0x68, 0x1);
        BattleObject(0x46);
    }
    else if (var0 == 0x14e)
    {
        BattleObject(0xd, 0x2, 0x6c, 0x1);
        BattleObject(0x4e);
    }
    else if (var0 == 0x154)
    {
        BattleObject(0xd, 0x2, 0x70, 0x1);
        BattleObject(0x4a);
    }
    func_78(func_1759);
}

void func_1759()
{
    if (func_1730() == 0x1)
    {
        return;
    }
}

void func_1760()
{
    func_1732();
}

void func_1761()
{
    if (global4 == 0x95 || global4 == 0x96)
    {
        func_344();
    }
}

void func_1762()
{
    if (global4 == 0x95 || global4 == 0x96)
    {
        func_348();
    }
    ItemModule(0x13, 0x5);
}

void func_1763()
{
    int var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    var0 = WorkModule(0x6, 0x11000003);
    EffectModule(0x8, var0, 0x1, 0x1);
    if (GroundModule(0x2722, 0x8))
    {
        var1 = GroundModuleF(0x3, 0x8);
        var2 = GroundModuleF(0x4, 0x8);
        var3 = GroundModuleF(0xc);
        PostureModule(0x3, var1, var2, var3);
        var4 = GroundModuleF(0xa);
        var5 = GroundModuleF(0xb);
        GroundModule(0x1a, var4, var5);
    }
    GroundModule(0x7, 0);
}

void func_1764()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    int var5;
    var0 = GroundModuleF(0x5, 0x8);
    var1 = GroundModuleF(0x6, 0x8);
    var2 = MathF(0x1, var0, var1);
    var3 = GroundModuleF(0x3, 0x8);
    var4 = GroundModuleF(0x4, 0x8);
    var5 = WorkModule(0x6, 0x11000003);
    EffectModule(0x17, var5, var3, var4, GroundModuleF(0xc));
    EffectModule(0x18, var5, 0, 0, -(var2 * (float)0xb4 / M_PI));
}

int func_1765()
{
    if (func_42())
    {
        WorkModule(0x2711, 0x20000071);
        return 0x1;
    }
    if (!WorkModule(0x10, 0x20000066) && global5 == 0x4d || global5 == 0x50 || global5 == 0x57 || global5 == 0x51)
    {
        WorkModule(0x2711, 0x20000071);
        WorkModule(0x2711, 0x20000066);
        StatusModule(0x2711, 0x57);
        return 0x1;
    }
    WorkModule(0x2711, 0x20000066);
    StatusModule(0x5, 0, 0x33, 0x1, 0, 0x1, 0, 0, 0x40, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0x400000a, 0, 0);
    return 0;
}

void func_1766()
{
    WorkModule(0xa, 0x11000002);
}

void func_1767()
{
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    WorkModule(0x7, WorkModule(0x6, 0x1200016e), 0x11000002);
    DamageModule(0xb, 0x2, WorkModuleF(0, 0x2000179) + 0);
    if (!StopModule(0x1))
    {
        func_1766();
    }
    global16 = func_1766;
    func_78(func_1768);
}

int func_1768()
{
    if (func_96() == 0x1)
    {
        func_16(0xc4, 0x1);
        return 0x1;
    }
    if (global18 == 0x2)
    {
        func_16(0xc4, 0);
        return 0x1;
    }
    if (WorkModule(0x6, 0x11000002) <= 0)
    {
        func_16(0xc3, 0);
        return 0x1;
    }
    return 0;
}

void func_1769()
{
    DamageModule(0xb, 0, 0 + 0);
}

void func_1770()
{
    int var0;
    int var1;
    int var2;
    int var3;
    float var4;
    float var5;
    float var6;
    float var7;
    float var8;
    float var9;
    float var10;
    float var11;
    float var12;
    float var13;
    float var14;
    float var15;
    float var16;
    int var17;
    var0 = WorkModule(0x6, 0x130000b5);
    var1 = WorkModule(0x10, 0x20000071);
    if (var1)
    {
        var2 = 0;
    }
    else
    {
        var2 = DamageModule(0);
    }
    var3 = 0;
    if (var2 == 0)
    {
        if (var0 == 0)
        {
            var3 = 0xc9;
        }
        else if (var0 == 0x1)
        {
            var3 = 0xc6;
        }
        else if (var0 == 0x2)
        {
            var3 = 0xc3;
        }
    }
    else if (var2 == 0x1)
    {
        if (var0 == 0)
        {
            var3 = 0xca;
        }
        else if (var0 == 0x1)
        {
            var3 = 0xc7;
        }
        else if (var0 == 0x2)
        {
            var3 = 0xc4;
        }
    }
    else if (var2 == 0x2)
    {
        if (var0 == 0)
        {
            var3 = 0xcb;
        }
        else if (var0 == 0x1)
        {
            var3 = 0xc8;
        }
        else if (var0 == 0x2)
        {
            var3 = 0xc5;
        }
    }
    func_22(var3, 0, 0);
    if (var1)
    {
        var4 = 0;
    }
    else
    {
        var4 = DamageModuleF(0x8);
    }
    var5 = WorkModuleF(0, 0x200016f) + WorkModuleF(0, 0x2000171) * sys_8(0) + WorkModuleF(0, 0x2000170) * (3.0f - (float)BattleObject(0x1b)) + WorkModuleF(0, 0x2000172) * var4 + WorkModuleF(0, 0x2000173) * DamageModuleF(0);
    var5 *= WorkModuleF(0, 0x30000fe);
    ControlModule(0x6, var5, WorkModuleF(0, 0x2000174), WorkModuleF(0, 0x2000175), 0xffffffff, 0x1);
    var6 = ModelModuleF(0, 0);
    var7 = ModelModuleF(0x1, 0);
    var8 = ModelModuleF(0, 0x3);
    var9 = ModelModuleF(0x1, 0x3);
    var10 = (var9 - var7) / (float)(WorkModule(0x6, 0x1200016e) - 0x1);
    WorkModule(0, var10 + 0, 0x1000006);
    var11 = GroundModuleF(0x5, 0x8);
    var12 = GroundModuleF(0x6, 0x8);
    var13 = MathF(0x1, var11, var12);
    var14 = GroundModuleF(0x3, 0x8);
    var15 = GroundModuleF(0x4, 0x8);
    var16 = WorkModuleF(0, 0x3000031);
    var17 = EffectModule(0x3, 0x1000044, var14, var15, PostureModuleF(0x3), 0, 0, -var13, var16, 0, 0xffffffff);
    WorkModule(0x7, var17, 0x11000003);
}

void func_1771()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    float var7;
    float var8;
    var0 = GroundModuleF(0x15);
    var1 = GroundModuleF(0x17);
    var2 = GroundModuleF(0x13);
    var3 = WorkModuleF(0, 0x1000007);
    if (var0 < var1)
    {
        var4 = var0;
    }
    else
    {
        var4 = var1;
    }
    var3 += WorkModuleF(0, 0x1000006);
    var5 = PostureModuleF(0x7);
    if (var2 + var3 + 1.0f * var5 > var4)
    {
        var3 = var4 - (var2 + 1.0f * var5);
    }
    func_1764();
    WorkModule(0, var3 + 0, 0x1000007);
    GroundModule(0x7, var3 / var5);
    var6 = PostureModuleF(0x1);
    var7 = PostureModuleF(0x2);
    var8 = PostureModuleF(0x3);
    PostureModule(0x3, var6, var7 - var3 / var5, var8);
}

int func_1772()
{
    return 0;
}

int func_1773()
{
    return 0;
}

void func_1774()
{
    
}

void func_1775()
{
    WorkModule(0x2711, 0x20000071);
    func_861();
    if (global6 != 0xc3)
    {
        func_1763();
    }
}

int func_1776()
{
    StatusModule(0x5, 0, 0x33, 0x1, 0, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0x40);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0x400000a, 0, 0);
    return 0;
}

void func_1777()
{
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    DamageModule(0xb, 0x2, WorkModuleF(0, 0x2000179) + 0);
    BattleObject(0x64, 0x1);
    func_78(func_1778);
}

void func_1778()
{
    if (func_96() == 0x1)
    {
        func_16(0xc4, 0x1);
        return 0x1;
    }
    if (global18 == 0x2)
    {
        func_16(0xc4, 0);
        return 0x1;
    }
    if (func_1781())
    {
        return 0x1;
    }
}

void func_1779()
{
    func_1769();
    BattleObject(0x64, 0);
}

void func_1780()
{
    
}

int func_1781()
{
    if (global3 == 0)
    {
        if (func_1783() != 0)
        {
            return 0x1;
        }
    }
    if (func_1784() != 0)
    {
        return 0x1;
    }
    return 0;
}

void func_1782()
{
    
}

int func_1783()
{
    if (GroundModule(0x2722, 0x8))
    {
        func_1764();
    }
    return 0;
}

int func_1784()
{
    return 0;
}

void func_1785()
{
    
}

void func_1786()
{
    func_1763();
}

void func_1787()
{
    WorkModule(0x2, 1.0f, 0x1000008);
    if (WorkModuleF(0, 0x1000008) >= WorkModuleF(0, 0x2000177))
    {
        WorkModule(0x19, 0x1f000008);
        WorkModule(0x19, 0x1f00000a);
        WorkModule(0x19, 0x1f00000b);
        WorkModule(0x19, 0x1f00000c);
        WorkModule(0x19, 0x1f00000d);
        WorkModule(0x19, 0x1f00000e);
        WorkModule(0x19, 0x1f00000f);
        WorkModule(0x19, 0x1f000010);
        WorkModule(0x19, 0x1f000011);
        func_100(0x4);
    }
}

int func_1788()
{
    if (func_470() != 0)
    {
        return 0x1;
    }
    StatusModule(0x5, 0x2, 0x32, 0x5, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x2, 0x1, 0x1, 0, 0, 0x2, 0, 0);
    return 0;
}

void func_1789()
{
    func_22(0x19, 0, 1.0f);
    DamageModule(0xb, 0, 0 + 0);
    if (!StopModule(0x1))
    {
        func_1787();
    }
    global16 = func_1787;
    func_78(func_1790);
}

void func_1790()
{
    if (func_41() != 0)
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0xe, 0);
        return 0x1;
    }
    func_1793();
}

void func_1791()
{
    
}

void func_1792()
{
    float var0;
    var0 = WorkModuleF(0, 0x3000158) * WorkModuleF(0, 0x2000176);
    KineticModule(0, 0);
    KineticModule(0x11, 0x1, var0);
    KineticModule(0x11, 0x3, 0, 0);
    KineticModule(0x11, 0x2, 0, 0);
    WorkModule(0, 0 + 0, 0x1000008);
}

int func_1793()
{
    if (global3 == 0)
    {
        if (func_1795() != 0)
        {
            return 0x1;
        }
    }
    if (func_1796() != 0)
    {
        return 0x1;
    }
    return 0;
}

void func_1794()
{
    
}

int func_1795()
{
    return 0;
}

int func_1796()
{
    return 0;
}

void func_1797()
{
    
}

void func_1798()
{
    
}

void func_1799()
{
    BattleObject(0x1e);
}

void func_1800(int arg0)
{
    BattleObject(0x1f, arg0);
}

int func_1801()
{
    StatusModule(0x5, 0x4, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0x2, 0, 0x1, 0, 0, 0xbe2, 0, 0);
    return 0;
}

void func_1802()
{
    HitModule(0x2710, 0x2);
    AreaModule(0x2710, 0);
    VisibilityModule(0x2710, 0);
    BattleObject(0xa, 0x1);
    func_22(0xffffffff, 0, 1.0f);
    WorkModule(0x19, 0x1f000008);
    func_78(func_1803);
}

void func_1803()
{
    func_1807();
    if (func_812())
    {
        return;
    }
    if (WorkModule(0x15, 0x1e00000d) == 0x1 && global18 == 0)
    {
        func_16(0x4d, 0);
        return;
    }
    if (func_806() == 0x1)
    {
        return;
    }
    if (func_807() == 0x1)
    {
        return;
    }
}

void func_1804()
{
    float var0;
    float var1;
    var0 = GroundModuleF(0xa);
    var1 = GroundModuleF(0xb);
    GroundModule(0x1a, var0, var1);
}

void func_1805()
{
    int var0;
    func_1799();
    WorkModule(0x7, 0, 0x11000005);
    var0 = WorkModule(0x6, 0x10000017);
    if (var0 == 0xa)
    {
        WorkModule(0x7, 0, 0x11000002);
        WorkModule(0x2710, 0x2100000d);
    }
    else if (var0 == 0xb)
    {
        WorkModule(0x7, 0, 0x11000002);
        WorkModule(0x2710, 0x2100000d);
    }
    else if (var0 == 0xc)
    {
        WorkModule(0x7, 0x1, 0x11000002);
        WorkModule(0x2710, 0x2100000d);
    }
    else if (var0 == 0xd)
    {
        WorkModule(0x7, 0x1, 0x11000002);
        WorkModule(0x2710, 0x2100000d);
    }
    BattleObject(0x20);
    WorkModule(0x2710, 0x20000041);
    WorkModule(0, WorkModuleF(0, 0x200019b) + 0, 0x12);
}

void func_1806()
{
    int var0;
    float var1;
    float var2;
    int var3;
    var0 = WorkModule(0x6, 0x11000002);
    if (var0 == 0)
    {
        if (global38 & 0x1 || global38 & 0x4)
        {
            WorkModule(0x7, 0x1, 0x11000002);
            BattleObject(0x21);
        }
    }
    else if (var0 == 0x2)
    {
        if (WorkModule(0x10, 0x2100000e))
        {
            if (WorkModule(0x10, 0x2100000f))
            {
                WorkModule(0x2711, 0x20000041);
                AreaModule(0x2710, 0x1);
                var1 = PostureModuleF(0x1);
                var2 = PostureModuleF(0x2);
                GroundModule(0x1a, var1, var2);
                func_16(0x4c, 0);
            }
        }
        else
        {
            var3 = WorkModule(0x6, 0x11000005);
            if (var3 != 0)
            {
                if (KineticModuleF(0x3, 0x3) < WorkModuleF(0, 0x2000106))
                {
                    EffectModule(0x6, var3);
                    WorkModule(0x7, 0, 0x11000005);
                }
            }
            if (WorkModule(0x10, 0x2100000d) == 0x1)
            {
                if (KineticModuleF(0x3, 0x3) < WorkModuleF(0, 0x1000006))
                {
                    func_16(0x4c, 0);
                }
            }
            WorkModule(0x2711, 0x20000041);
        }
    }
}

void func_1807()
{
    
}

void func_1808()
{
    func_1800(0);
    VisibilityModule(0x2710, 0x1);
}

int func_1809()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x1, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0xbe2, 0, 0);
    return 0;
}

void func_1810()
{
    if (WorkModule(0x10, 0x2000000b) == 0x1)
    {
        ItemModule(0x8);
    }
    HitModule(0x2710, 0x2);
    AreaModule(0x2710, 0);
    CancelModule(0x2712);
    func_78(func_1811);
}

void func_1811()
{
    
}

void func_1812()
{
    
}

void func_1813()
{
    int var0;
    int var1;
    int var2;
    float var3;
    func_1799();
    BattleObject(0x22);
    var0 = WorkModule(0x6, 0x10000017);
    if (var0 == 0x13 || var0 == 0x15)
    {
        var3 = WorkModuleF(0, 0x1000006) - PostureModuleF(0x1);
        if (func_13(var3) < 1.0f)
        {
            var2 = 0x33;
            if (WorkModule(0x10, 0x2100000d) == 0)
            {
                var1 = 0xb;
                WorkModule(0x7, 0x2, 0x11000002);
            }
            else
            {
                var1 = 0;
                WorkModule(0x7, 0x3, 0x11000002);
            }
        }
        else if (var3 * PostureModuleF(0) < 0)
        {
            var1 = 0x10;
            var2 = 0x33;
            WorkModule(0x7, 0, 0x11000002);
        }
        else
        {
            var1 = 0xb;
            var2 = 0xe;
            WorkModule(0x7, 0x1, 0x11000002);
        }
        if (MotionModule(0x7) != var1)
        {
            func_22(var1, 0, 1.0f);
        }
        GroundModule(0x2710, 0x2);
        func_20(0);
        KineticModule(0, var2);
    }
    else if (var0 == 0x14)
    {
        var1 = 0x3f;
        func_22(var1, 0, 1.0f);
        GroundModule(0x2710, 0x5);
        func_20(0x2);
        KineticModule(0, 0x33);
    }
}

void func_1814()
{
    int var0;
    int var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    float var7;
    float var8;
    float var9;
    float var10;
    var0 = WorkModule(0x6, 0x10000017);
    if (var0 == 0x13 || var0 == 0x15)
    {
        var1 = WorkModule(0x6, 0x11000002);
        if (var1 == 0)
        {
            if (MotionModule(0x2712) == 0x1)
            {
                PostureModule(0x1);
                PostureModule(0x2);
                WorkModule(0x7, 0x1, 0x11000002);
                func_22(0xb, 0, 1.0f);
                KineticModule(0, 0xe);
            }
        }
        else if (var1 == 0x1)
        {
            var2 = WorkModuleF(0, 0x1000006) - PostureModuleF(0x1);
            if (var2 * PostureModuleF(0) < 0)
            {
                KineticModule(0, 0x33);
                if (WorkModule(0x10, 0x2100000d) == 0)
                {
                    WorkModule(0x7, 0x2, 0x11000002);
                }
                else
                {
                    func_22(0, 0, 1.0f);
                    WorkModule(0x7, 0x3, 0x11000002);
                }
            }
        }
        else if (var1 == 0x2)
        {
            if (PostureModuleF(0) < 0)
            {
                var3 = -90.0f;
            }
            else
            {
                var3 = 90.0f;
            }
            var4 = PostureModuleF(0x4);
            var5 = PostureModuleF(0x5);
            var6 = PostureModuleF(0x6);
            var7 = var3 - var5;
            var5 += var7 * 0.4699999988079071f;
            PostureModule(0x4, var4, var5, var6);
            var8 = PostureModuleF(0x1);
            var9 = PostureModuleF(0x2);
            var10 = PostureModuleF(0x3) - 0.4000000059604645f;
            PostureModule(0x3, var8, var9, var10);
        }
        else if (var1 == 0x3)
        {
            if (MotionModuleF(0x1) >= (float)MotionModule(0))
            {
                MotionModule(0x2711, 0);
            }
        }
    }
    else if (var0 == 0x14)
    {
        var8 = PostureModuleF(0x1);
        var9 = PostureModuleF(0x2);
        var10 = PostureModuleF(0x3);
        var8 += (WorkModuleF(0, 0x1000006) - var8) * 0.05000000074505806f;
        var9 += (WorkModuleF(0, 0x1000007) - var9) * 0.05000000074505806f;
        var10 -= 0.4000000059604645f;
        PostureModule(0x3, var8, var9, var10);
    }
}

void func_1815()
{
    func_1800(0);
}

int func_1816()
{
    StatusModule(0x5, 0x4, 0x33, 0, 0, 0, 0x100000, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0x2, 0, 0, 0x1, 0, 0, 0, 0);
    return 0;
}

void func_1817()
{
    GroundModule(0x272a);
    func_1818();
    func_78(func_1819);
}

void func_1818()
{
    float var0;
    float var1;
    var0 = 1.0f;
    var1 = 0;
    func_22(0x18, var0, var1);
    WorkModule(0x7, 0x5, 0x11000000);
}

void func_1819()
{
    
}

void func_1820()
{
    
}

void func_1821()
{
    func_1799();
    BattleObject(0x2c);
}

void func_1822()
{
    
}

void func_1823()
{
    int var0;
    func_1800(0);
    var0 = WorkModule(0x6, 0x1200007f);
    WorkModule(0x7, var0, 0x10000012);
}

int func_1824()
{
    if (func_470() != 0)
    {
        return 0x1;
    }
    StatusModule(0x5, 0x2, 0x1, 0x5, 0x4, 0, 0x100000, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0x1, 0, 0x1, 0, 0, 0, 0x4);
    return 0;
}

void func_1825()
{
    float var0;
    float var1;
    if (WorkModule(0x10, 0x21000014))
    {
        printf("status_GimmickSpringJump from tokusetsu ring.");
    }
    var0 = PostureModuleF(0x1);
    var1 = PostureModuleF(0x2);
    GroundModule(0x1a, var0, var1);
    ControlModule(0x2714, 0xd, 0);
    func_492();
}

void func_1826()
{
    float var0;
    float var1;
    var0 = GroundModuleF(0xa);
    var1 = GroundModuleF(0xb);
    GroundModule(0x1a, var0, var1);
}

int func_1827()
{
    StatusModule(0x5, 0, 0xf, 0x1, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_1828()
{
    func_22(0xc8, 0, 1.0f);
    func_78(func_1829);
}

void func_1829()
{
    if (global18 == 0x2)
    {
        func_16(0x4c, 0);
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0, 0);
        return;
    }
}

void func_1830()
{
    
}

int func_1831()
{
    StatusModule(0x5, 0x4, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0xbe2, 0, 0);
    return 0;
}

void func_1832()
{
    HitModule(0x2710, 0x2);
    AreaModule(0x2710, 0);
    VisibilityModule(0x2710, 0);
    ItemModule(0xf, 0);
    ItemModule(0x16, 0);
    func_22(0xffffffff, 0, 1.0f);
    func_78(func_1833);
}

void func_1833()
{
    
}

void func_1834()
{
    
}

void func_1835()
{
    func_1799();
    BattleObject(0x51);
}

void func_1836()
{
    func_1800(0x1);
}

int func_1837()
{
    StatusModule(0x5, 0xffffffff, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0xbe2, 0, 0);
    return 0;
}

void func_1838()
{
    AreaModule(0x2710, 0);
    DamageModule(0x6, 0x1);
    MotionModule(0x4, 0);
    MotionModule(0x5, 0);
    func_78(func_1839);
}

void func_1839()
{
    
}

void func_1840()
{
    float var0;
    float var1;
    var0 = PostureModuleF(0x1);
    var1 = PostureModuleF(0x2);
    GroundModule(0x1a, var0, var1);
}

void func_1841()
{
    func_1799();
}

void func_1842()
{
    func_1800(0);
}

int func_1843()
{
    StatusModule(0x5, 0x2, 0x33, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0x9e2, 0, 0);
    return 0;
}

void func_1844()
{
    AreaModule(0x2710, 0);
    MotionModule(0x4, 0);
    WorkModule(0x7, 0x4, 0x11000003);
    func_78(func_1845);
}

int func_1845()
{
    if (WorkModule(0x10, 0x2100000e))
    {
        if (WorkModule(0xf, 0x11000002))
        {
            func_16(0x4c, 0);
            return;
        }
        if (WorkModule(0x6, 0x11000003) <= 0)
        {
            if (func_812())
            {
                return 0x1;
            }
            if (global18 == 0)
            {
                func_16(0x4d, 0);
                return 0x1;
            }
            if (func_806() == 0x1)
            {
                return 0x1;
            }
            if (func_807() == 0x1)
            {
                return 0x1;
            }
        }
    }
    return 0;
}

void func_1846()
{
    
}

void func_1847()
{
    func_1799();
}

void func_1848()
{
    float var0;
    float var1;
    float var2;
    func_1800(0);
    var0 = KineticModuleF(0x4);
    var1 = KineticModuleF(0x5);
    var2 = KineticModuleF(0xb, 0x1);
    printf("damage x: %f y: %f, gravity y: %f", var0, var1, var2);
    KineticModule(0x11, 0x1, var2 + var1);
    KineticModule(0xd, var0, 0);
}

int func_1849()
{
    StatusModule(0x5, 0x4, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0xbe2, 0, 0);
    return 0;
}

void func_1850()
{
    float var0;
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    ItemModule(0x16, 0);
    BattleObject(0x6b, 0x1);
    func_22(0x12, 0, WorkModuleF(0, 0x200021d));
    var0 = (float)WorkModule(0x6, 0x120002e7);
    var0 += DamageModuleF(0) * WorkModuleF(0, 0x20002e8);
    ControlModule(0x6, var0, WorkModuleF(0, 0x20002e9), WorkModuleF(0, 0x20002ea));
    func_78(func_1851);
}

void func_1851()
{
    if (ControlModuleF(0x5) <= 0)
    {
        WorkModule(0x2710, 0x21000005);
        func_16(0xb, 0x1);
        return 0x1;
    }
}

void func_1852()
{
    BattleObject(0x6b, 0);
}

void func_1853()
{
    func_1799();
    BattleObject(0x52);
}

void func_1854()
{
    func_1800(0x1);
}

int func_1855()
{
    StatusModule(0x5, 0x4, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0xbe2, 0, 0);
    return 0;
}

void func_1856()
{
    float var0;
    HitModule(0x2710, 0x2);
    AreaModule(0x2710, 0);
    MotionModule(0x4, 0);
    var0 = (float)WorkModule(0x6, 0x120002eb);
    var0 += DamageModuleF(0) * WorkModuleF(0, 0x20002ec);
    ControlModule(0x6, var0, WorkModuleF(0, 0x20002ed), WorkModuleF(0, 0x20002ee));
    WorkModule(0, var0 + 0, 0x1000006);
    func_78(func_1857);
}

void func_1857()
{
    int var0;
    var0 = 0;
    if (WorkModule(0x10, 0x2100000e))
    {
        var0 = 0x1;
    }
    if (ControlModuleF(0x5) <= 0)
    {
        var0 = 0x1;
        WorkModule(0x2710, 0x2100000d);
    }
    if (var0)
    {
        if (global18 == 0x2)
        {
            func_16(0xe, 0);
        }
        else if (WorkModule(0x10, 0x2100000e) && WorkModule(0x10, 0x21000010))
        {
            func_16(0x63, 0);
        }
        else
        {
            MotionModule(0x4, 1.0f);
            func_16(0, 0);
        }
        return 0x1;
    }
}

void func_1858()
{
    float var0;
    float var1;
    HitModule(0x2710, 0);
    AreaModule(0x2710, 0x1);
    VisibilityModule(0x2710, 0x1);
    var0 = PostureModuleF(0x1);
    var1 = PostureModuleF(0x2);
    GroundModule(0x1a, var0, var1);
}

void func_1859()
{
    func_1799();
}

void func_1860()
{
    func_1800(0x1);
}

int func_1861()
{
    StatusModule(0x5, 0x4, 0x33, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0xbe2, 0, 0);
    return 0;
}

void func_1862()
{
    AreaModule(0x2710, 0);
    func_78(func_1863);
}

void func_1863()
{
    if (WorkModule(0x10, 0x2100000d))
    {
        if (StatusModule(0) == 0x141)
        {
            func_16(0xe, 0);
            return;
        }
    }
}

void func_1864()
{
    float var0;
    float var1;
    AreaModule(0x2710, 0x1);
    VisibilityModule(0x2710, 0x1);
    var0 = PostureModuleF(0x1);
    var1 = PostureModuleF(0x2);
    GroundModule(0x1a, var0, var1);
}

void func_1865()
{
    func_1799();
}

void func_1866()
{
    func_1800(0x1);
}

int func_1867()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0x1, 0, 0x400002, 0, 0);
    return 0;
}

void func_1868()
{
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    ItemModule(0x16, 0);
    func_22(0x2e, 0, 1.0f);
    LinkModule(0x2716, 0, 0x3);
    func_78(func_1869);
}

void func_1869()
{
    
}

void func_1870()
{
    
}

int func_1871()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0x1, 0, 0x2, 0, 0);
    return 0;
}

void func_1872()
{
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    ItemModule(0x16, 0);
    WorkModule(0x2711, 0x2000001c);
    func_22(WorkModule(0x6, 0x11000005), 0, 3.0f);
    func_78(func_1873);
}

void func_1873()
{
    
}

void func_1874()
{
    if (global6 != 0xe2)
    {
        CameraModule(0x6, 0x1, 0xffffffff);
    }
}

int func_1875()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0x1, 0, 0x2, 0, 0);
    return 0;
}

void func_1876()
{
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    ItemModule(0x16, 0);
    func_22(0xffffffff, 0, 1.0f);
    func_78(func_1877);
}

void func_1877()
{
    
}

void func_1878()
{
    CameraModule(0x6, 0x1, 0xffffffff);
}

int func_1879()
{
    StatusModule(0x5, 0x2, 0x32, 0x5, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0x3ea, 0, 0);
    return 0;
}

void func_1880()
{
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    ItemModule(0x16, 0);
    if (WorkModule(0x10, 0x2100000d))
    {
        func_22(0xffffffff, 0, 1.0f);
    }
    else
    {
        func_22(0xffffffff, 0, 1.0f);
    }
    func_78(func_1881);
}

void func_1881()
{
    
}

void func_1882()
{
    
}

int func_1883()
{
    StatusModule(0x5, 0x2, 0x32, 0x5, 0, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1884()
{
    if (WorkModuleF(0, 0x1000006) < -0.5f || WorkModuleF(0, 0x1000006) > 0.5f)
    {
        func_22(0xfe, 0, 1.0f);
    }
    else
    {
        func_22(0xcc, 0, 1.0f);
    }
    func_78(func_1885);
}

void func_1885()
{
    
}

void func_1886()
{
    
}

int func_1887()
{
    StatusModule(0x5, 0x2, 0x32, 0x5, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0x2, 0, 0);
    return 0;
}

void func_1888()
{
    func_22(0xcc, 0, 1.0f);
    func_78(func_1889);
}

void func_1889()
{
    
}

void func_1890()
{
    
}

int func_1891()
{
    printf("status_pre_BittenWario");
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1892()
{
    printf("status_BittenWario");
    ItemModule(0x16, 0);
    if (!StopModule(0x1))
    {
        func_1894();
    }
    global16 = func_1894;
    func_78(func_1893);
}

void func_1893()
{
    printf("status_BittenWario_Main");
}

void func_1894()
{
    printf("sub_status_BittenWario_uniq");
    if (func_96())
    {
        printf("clatter_recover");
        LinkModule(0x2713, 0, 0x10);
    }
}

int func_1895()
{
    printf("status_pre_BittenWarioEnd");
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1896()
{
    printf("status_BittenWarioEnd");
    ItemModule(0x16, 0);
    func_78(func_1897);
}

void func_1897()
{
    printf("status_BittenWarioEnd_Main");
}

int func_1898()
{
    printf("status_pre_BittenWarioStart 111");
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1899()
{
    printf("status_BittenWarioStart");
    ItemModule(0x16, 0);
    LinkModule(0x2716, 0, 0x3);
    func_78(func_1900);
}

void func_1900()
{
    if (MotionModuleF(0x1) >= WorkModuleF(0, 0x1000006))
    {
        func_16(0xe7);
        return;
    }
}

int func_1901()
{
    StatusModule(0x5, 0xffffffff, 0x33, 0x7, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3ea, 0, 0);
    return 0;
}

void func_1902()
{
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    ItemModule(0x16, 0);
    func_1905();
    func_78(func_1903);
}

void func_1903()
{
    int var0;
    int var1;
    var0 = StatusModule(0x6);
    var1 = 0;
    if (!var0)
    {
        if (global19 == 0 && global18 == 0x2)
        {
            var1 = 0x1;
        }
        else if (global19 == 0x2 && global18 == 0)
        {
            var1 = 0x1;
        }
    }
    if (var1)
    {
        func_1905();
    }
}

void func_1904()
{
    
}

void func_1905()
{
    int var0;
    if (global18 == 0)
    {
        if (!WorkModule(0x10, 0x20000040))
        {
            GroundModule(0x2710, 0x1);
            var0 = WorkModule(0x6, 0x11000002);
            if (WorkModule(0x10, 0x2100000d))
            {
                func_22(var0, 0, 1.0f);
            }
            else
            {
                func_23(var0);
                WorkModule(0x2710, 0x2100000d);
            }
        }
    }
    else if (!WorkModule(0x10, 0x20000040))
    {
        GroundModule(0x2710, 0x5);
        if (WorkModule(0x10, 0x2100000d))
        {
            func_22(0x88, 0, 1.0f);
        }
        else
        {
            func_23(0x88);
            WorkModule(0x2710, 0x2100000d);
        }
    }
}

void func_1906()
{
    
}

void func_1907()
{
    printf("sub_uniq_process_capture_yoshi_exec");
    if (WorkModule(0x10, 0x20000040) == 0)
    {
        printf("sub_uniq_process_capture_yoshi_exec false");
        func_1093();
    }
}

int func_1908()
{
    StatusModule(0x5, 0x2, 0x32, 0x5, 0x4, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x4003ea, 0, 0);
    return 0;
}

void func_1909()
{
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    ItemModule(0x16, 0);
    BattleObject(0xa, 0x1);
    func_78(func_1910);
}

void func_1910()
{
    
}

void func_1911()
{
    
}

int func_1912()
{
    float var0;
    StatusModule(0x5, 0xffffffff, 0x33, 0x7, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x400003, 0, 0);
    var0 = -LinkModuleF(0x7, 0);
    PostureModule(0, var0);
    PostureModule(0x2);
    return 0;
}

void func_1913()
{
    func_1090();
    func_1905();
    func_78(func_1914);
}

void func_1914()
{
    func_1094();
}

void func_1915()
{
    
}

int func_1916()
{
    StatusModule(0x5, 0xffffffff, 0x33, 0x7, 0, 0, 0x1c000, 0x3c, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xb, 0, 0);
    return 0;
}

void func_1917()
{
    if (!StopModule(0x1))
    {
        func_1103();
    }
    global16 = func_1103;
    func_78(func_1918);
}

void func_1918()
{
    if (func_1104() == 0x1)
    {
        return;
    }
    func_1105();
}

void func_1919()
{
    
}

int func_1920()
{
    StatusModule(0x5, 0xffffffff, 0x33, 0x7, 0, 0, 0x1c000, 0x3c, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xf, 0, 0);
    return 0;
}

void func_1921()
{
    WorkModule(0x16, 0x1e000025);
    WorkModule(0x16, 0x1e000024);
    func_1113();
    func_78(func_1922);
}

void func_1922()
{
    if (WorkModule(0x15, 0x1e000024) == 0x1 && MotionModule(0x2712))
    {
        func_16(0xef, 0);
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000025) == 0x1 && ControlModuleF(0x5) <= 0)
    {
        func_16(0x42, 0);
        return 0x1;
    }
}

void func_1923()
{
    
}

void func_1924()
{
    
}

int func_1925()
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    return 0;
}

void func_1926()
{
    func_1924();
}

int func_1927()
{
    if (func_1925())
    {
        return 0x1;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0x85, 0);
            return 0x1;
        }
    }
    return 0;
}

void func_1928()
{
    func_1924();
}

void func_1929()
{
    if (func_1925())
    {
        return 0x1;
    }
    if (CancelModule(0x2713) == 0x1 && func_39() != 0)
    {
        return 0x1;
    }
    if (MotionModule(0x2712))
    {
        func_16(0, 0);
        return 0x1;
    }
}

int func_1930()
{
    StatusModule(0x5, 0, 0x52, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x3, 0x10000, 0, 0);
    return 0;
}

void func_1931()
{
    func_1926();
    func_22(0x10b, 0, 1.0f);
    func_78(func_1932);
}

void func_1932()
{
    if (func_1927())
    {
        return;
    }
}

void func_1933()
{
    
}

int func_1934()
{
    StatusModule(0x5, 0, 0x20, 0x1, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x3, 0x10004, 0, 0);
    return 0;
}

void func_1935()
{
    WorkModule(0x7, WorkModule(0x6, 0x1200008e), 0x1000000a);
    func_1926();
    func_22(0x10a, 0, 1.0f);
    PhysicsModule(0x9);
    func_78(func_1936);
}

void func_1936()
{
    if (global18 == 0x2)
    {
        if (GroundModule(0x2727))
        {
            func_16(0x7d, 0);
            return;
        }
    }
    if (func_1927())
    {
        return;
    }
}

void func_1937()
{
    WorkModule(0x2711, 0x20000011);
}

int func_1938()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x10000, 0, 0);
    return 0;
}

void func_1939()
{
    WorkModule(0x7, WorkModule(0x6, 0x1200008e), 0x11000002);
    func_1924();
    func_22(0x10c, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_1940();
    }
    global16 = func_1940;
    PhysicsModule(0x9);
    func_78(func_1941);
}

void func_1940()
{
    if (WorkModule(0x6, 0x11000002) > 0)
    {
        WorkModule(0xa, 0x11000002);
    }
}

void func_1941()
{
    float var0;
    float var1;
    if (global18 == 0)
    {
        if (ControlModule(0x2710, 0))
        {
            func_16(0x87, 0x1);
            return;
        }
        if (ControlModule(0x2710, 0x1))
        {
            func_16(0x87, 0x1);
            return;
        }
        var0 = WorkModuleF(0, 0x200005d);
        if (func_88() >= var0)
        {
            if (ControlModule(0x271d))
            {
                func_16(0x88, 0x1);
                return;
            }
        }
        if (func_89() >= var0)
        {
            if (ControlModule(0x271d))
            {
                func_16(0x89, 0x1);
                return;
            }
        }
        var1 = WorkModuleF(0, 0x200005c);
        if (global32 >= var1)
        {
            if (!ControlModule(0x271d))
            {
                func_16(0x86, 0x1);
                return;
            }
        }
        if (WorkModule(0x6, 0x11000002) <= 0)
        {
            func_16(0x86, 0);
            return;
        }
    }
    if (func_1925())
    {
        return;
    }
}

void func_1942()
{
    
}

int func_1943()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_1944()
{
    func_1928();
    func_22(0x10d, 0, 1.0f);
    func_78(func_1945);
}

void func_1945()
{
    if (func_1929())
    {
        return;
    }
}

void func_1946()
{
    
}

int func_1947()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0, 0x1, 0x20);
    return 0;
}

void func_1948()
{
    func_1928();
    func_22(0x10e, 0, 1.0f);
    func_78(func_1949);
}

void func_1949()
{
    if (func_1929())
    {
        return;
    }
}

void func_1950()
{
    
}

int func_1951()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x80000, 0, 0x1);
    return 0;
}

void func_1952()
{
    func_1928();
    func_22(0x10f, 0, 1.0f);
    func_78(func_1953);
}

void func_1953()
{
    if (func_1929())
    {
        return;
    }
}

void func_1954()
{
    
}

int func_1955()
{
    StatusModule(0x5, 0, 0xf, 0x2, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x80000, 0, 0x1);
    return 0;
}

void func_1956()
{
    func_1928();
    func_22(0x110, 0, 1.0f);
    func_78(func_1957);
}

void func_1957()
{
    if (func_1929())
    {
        return;
    }
}

void func_1958()
{
    
}

int func_1959()
{
    StatusModule(0x5, 0x2, 0x5c, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0x1, 0x2, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_1960()
{
    MotionModule(0x4, 0);
    func_38();
    func_40();
    func_78(func_1961);
}

void func_1961()
{
    if (global18 == 0x2)
    {
        if (func_58())
        {
            return;
        }
        if (func_59())
        {
            return;
        }
        if (func_61())
        {
            return;
        }
        if (func_62())
        {
            return;
        }
        if (func_63())
        {
            return;
        }
    }
    else
    {
        if (func_43())
        {
            return;
        }
        if (func_44())
        {
            return;
        }
        if (func_46())
        {
            return;
        }
        if (func_47())
        {
            return;
        }
        if (func_48())
        {
            return;
        }
        if (func_49())
        {
            return;
        }
    }
}

void func_1962()
{
    
}

int func_1963()
{
    StatusModule(0x5, 0x2, 0x2e, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_1964()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    KineticModule(0xe, 0x3, 0x16, 0, 0, 0, 0, 0);
    KineticModule(0x15, 0x3, -1.0f, -1.0f);
    KineticModule(0xb, 0x3);
    func_22(0xd4, 0, 1.0f);
    GroundModule(0x15, 0x1);
    var0 = DamageModuleF(0);
    var1 = WorkModuleF(0, 0x20001dd);
    var2 = 1.0f;
    var3 = WorkModuleF(0, 0x20001df);
    var4 = WorkModuleF(0, 0x20001de);
    if (9.999999747378752e-06f < var4)
    {
        if (var0 < var4)
        {
            var3 = var3 * (var4 - var0) / var4;
        }
        else
        {
            var3 = 0;
        }
    }
    else
    {
        var3 = 0;
    }
    ControlModule(0x6, var1, var2, var3);
    CaptureModule(0xa);
    func_78(func_1965);
}

void func_1965()
{
    float var0;
    float var1;
    int var2;
    float var3;
    if (MotionModule(0x2712))
    {
        func_22(0xd4, 0, 1.0f);
    }
    if (func_96())
    {
        printf("clatter_recover");
        func_16(0x43, 0);
        return 0x1;
    }
    var0 = CaptureModuleF(0x1);
    var1 = CaptureModuleF(0x2);
    if (var0 < 0)
    {
        var2 = 0x50;
    }
    else
    {
        var2 = 0xa0;
    }
    if (GroundModule(0x2722, var2) == 0x1)
    {
        if (WorkModule(0x10, 0x2100000f) == 0x1)
        {
            var0 = var1 = 0;
        }
        else
        {
            WorkModule(0x2710, 0x2100000f);
        }
    }
    else
    {
        WorkModule(0x2711, 0x2100000f);
    }
    var3 = 0.20000000298023224f;
    KineticModule(0x11, 0x3, var0 * var3, var1 * var3);
    CaptureModule(0xa);
}

void func_1966()
{
    CaptureModule(0xa);
}

void func_1967()
{
    if (global6 == 0x43)
    {
        PostureModule(0, -LinkModuleF(0x7, 0));
        PostureModule(0x2);
    }
    if (global6 != 0x42)
    {
        LinkModule(0x2713, 0, 0x28);
    }
    if (LinkModule(0x2, 0))
    {
        LinkModule(0x6, 0);
    }
    ControlModule(0x6, 0, 0, 0);
}

int func_1968()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x4003ea, 0, 0);
    return 0;
}

void func_1969()
{
    VisibilityModule(0x2710, 0);
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    ItemModule(0x16, 0);
    HitModule(0x2710, 0x2);
    func_22(0xffffffff, 0, 1.0f);
    func_78(func_1970);
}

void func_1970()
{
    if (ControlModuleF(0x5) <= 0)
    {
        func_16(0x43, 0);
        return;
    }
}

void func_1971()
{
    VisibilityModule(0x2710, 0x1);
    AreaModule(0x2710, 0x1);
    ItemModule(0xf, 0x1);
    ItemModule(0x16, 0x1);
}

int func_1972()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x4003ea, 0, 0);
    return 0;
}

void func_1973()
{
    float var0;
    var0 = PostureModuleF(0x7);
    WorkModule(0, var0 + 0, 0x1000006);
    WorkModule(0x7, 0xffffffff, 0x11000002);
    WorkModule(0x7, 0xffffffff, 0x11000003);
    HitModule(0x2710, 0x2);
    AreaModule(0x2710, 0);
    func_22(0x2e, 0, 1.0f);
    func_78(func_1974);
}

void func_1974()
{
    if (WorkModule(0x6, 0x11000002) < 0 || WorkModule(0x6, 0x11000003) < 0)
    {
        return;
    }
    func_1975();
}

void func_1975()
{
    int var0;
    float var1;
    float var2;
    var0 = WorkModule(0x6, 0x11000003);
    if (var0 > 0)
    {
        var0--;
        if (var0 == 0)
        {
            VisibilityModule(0x2710, 0);
            ItemModule(0xf, 0);
            ItemModule(0x16, 0);
            WorkModule(0x2710, 0x2100000d);
        }
        else
        {
            var1 = (float)var0 * 1.0f / (float)WorkModule(0x6, 0x11000002);
            var2 = WorkModuleF(0, 0x1000006) * var1;
            PostureModule(0x2713, var2);
        }
        WorkModule(0x7, var0, 0x11000003);
    }
}

void func_1976()
{
    float var0;
    var0 = WorkModuleF(0, 0x1000006);
    PostureModule(0x2713, var0);
    VisibilityModule(0x2710, 0x1);
}

int func_1977()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_1978()
{
    WorkModule(0x11, 0x20000001);
    HitModule(0x271a, 0x1);
    AreaModule(0x2710, 0);
    BattleObject(0x29);
}

void func_1979()
{
    MotionModule(0x4, 0);
    func_78(func_1980);
}

void func_1980()
{
    
}

void func_1981()
{
    HitModule(0x271a, 0);
}

void func_1982()
{
    VisibilityModule(0x2710, 0x1);
    MotionModule(0x4, WorkModuleF(0, 0x1000006));
    BattleObject(0x82, 0x1);
}

int func_1983()
{
    StatusModule(0x5, 0x4, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0x3e8, 0, 0);
    return 0;
}

void func_1984()
{
    BattleObject(0x82, 0);
    WorkModule(0, MotionModuleF(0x9) + 0, 0x1000006);
    AreaModule(0x2710, 0);
    HitModule(0x2710, 0x3);
    MotionModule(0x4, 0);
    WorkModule(0x2710, 0x20000001);
    EffectModule(0x2726, 0x2a);
    SoundModule(0x272c, 0x4a60051);
    func_78(func_1985);
}

int func_1985()
{
    if (WorkModule(0x10, 0x2100000d))
    {
        WorkModule(0x2711, 0x2100000d);
        BattleObject(0x58);
        return 0x1;
    }
    return 0;
}

void func_1986()
{
    WorkModule(0x2711, 0x20000001);
    if (global6 != 0x103)
    {
        func_1982();
    }
}

int func_1987()
{
    StatusModule(0x5, 0x4, 0x33, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0, 0, 0x3e8, 0, 0);
    return 0;
}

void func_1988()
{
    AreaModule(0x2710, 0);
    HitModule(0x2710, 0x3);
    VisibilityModule(0x2710, 0);
    EffectModule(0x2726, 0x2b);
    SoundModule(0x272c, 0x4a60052);
    func_78(func_1989);
}

int func_1989()
{
    if (WorkModule(0x10, 0x2100000d))
    {
        func_16(0xe, 0);
        return 0x1;
    }
    return 0;
}

void func_1990()
{
    func_1982();
}

int func_1991()
{
    StatusModule(0x5, 0xffffffff, 0x33, 0x2, 0, 0, 0, 0, 0x10c0, 0);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0, 0x4002, 0, 0);
    return 0;
}

void func_1992()
{
    WorkModule(0x2711, 0x20000003);
    func_1994();
    func_78(func_1993);
}

void func_1993()
{
    if (global18 == 0x2)
    {
        if (GroundModule(0x2722, 0x6))
        {
            func_16(0xe, 0);
            return;
        }
    }
    if (global18 == 0)
    {
        if (GroundModule(0x2722, 0x6))
        {
            func_16(0, 0);
            return;
        }
    }
    if (func_85() >= WorkModuleF(0, 0x200018a))
    {
        if (global20 >= WorkModuleF(0, 0x200018b))
        {
            func_16(0x106, 0x1);
            return;
        }
    }
    if (MotionModule(0x2712))
    {
        func_16(0x106, 0x1);
        return;
    }
    if (func_43())
    {
        return 0x1;
    }
    if (func_44())
    {
        return 0x1;
    }
    if (func_47())
    {
        return 0x1;
    }
    if (func_55())
    {
        return 0x1;
    }
    if (global19 == 0x2 && global18 == 0 || global19 == 0 && global18 == 0x2)
    {
        func_1994();
    }
}

void func_1994()
{
    int var0;
    int var1;
    int var2;
    int var3;
    var0 = 0x1b7;
    var1 = 0x1b8;
    var2 = 0x1b9;
    var3 = 0x1ba;
    if (WorkModule(0x6, 0x13000121) == 0x1)
    {
        var1 = 0x1b7;
        var3 = 0x1b9;
    }
    if (global18 == 0)
    {
        GroundModule(0x2710, 0x1);
        WorkModule(0x19, 0x1f000000);
        WorkModule(0x19, 0x1f000001);
        WorkModule(0x19, 0x1f000003);
        WorkModule(0x1a, 0x1f000008);
        if (PostureModuleF(0) == 1.0f)
        {
            if (WorkModule(0x10, 0x21000004))
            {
                func_23(var0);
            }
            else
            {
                func_22(var0, 0, 1.0f);
                WorkModule(0x2710, 0x21000004);
            }
        }
        else if (WorkModule(0x10, 0x21000004))
        {
            func_23(var1);
        }
        else
        {
            func_22(var1, 0, 1.0f);
            WorkModule(0x2710, 0x21000004);
        }
    }
    else if (global18 == 0x2)
    {
        GroundModule(0x2710, 0x5);
        WorkModule(0x1a, 0x1f000000);
        WorkModule(0x1a, 0x1f000001);
        WorkModule(0x1a, 0x1f000003);
        WorkModule(0x19, 0x1f000008);
        if (PostureModuleF(0) == 1.0f)
        {
            if (WorkModule(0x10, 0x21000004))
            {
                func_23(var2);
            }
            else
            {
                func_22(var2, 0, 1.0f);
                WorkModule(0x2710, 0x21000004);
            }
        }
        else if (WorkModule(0x10, 0x21000004))
        {
            func_23(var3);
        }
        else
        {
            func_22(var3, 0, 1.0f);
            WorkModule(0x2710, 0x21000004);
        }
    }
}

void func_1995()
{
    
}

int func_1996()
{
    StatusModule(0x5, 0x6, 0x19, 0x7, 0, 0, 0, 0, 0x10c0, 0);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0, 0x4002, 0, 0);
    return 0;
}

void func_1997()
{
    func_1998();
    func_78(func_1999);
}

void func_1998()
{
    if (PostureModuleF(0) == 1.0f)
    {
        func_22(0x1bb, 0, 1.0f);
    }
    else if (WorkModule(0x6, 0x13000121) == 0x1)
    {
        func_22(0x1bb, 0, 1.0f);
    }
    else
    {
        func_22(0x1bc, 0, 1.0f);
    }
    MotionModule(0x36, 0x1);
    WorkModule(0x16, 0x1e000065);
    WorkModule(0x16, 0x1e000074);
    WorkModule(0x16, 0x1e00005f);
    WorkModule(0x16, 0x1e000057);
}

void func_1999()
{
    if (MotionModule(0x2712))
    {
        func_16(0x106, 0x1);
        return;
    }
    if (GroundModule(0x2722, 0x6))
    {
        func_16(0xe, 0x1);
        return;
    }
    if (global18 == 0)
    {
        func_16(0, 0x1);
        return;
    }
    if (StatusModule(0x6))
    {
        func_71(global23);
        func_71(global30);
        if (global24 & 0x8000)
        {
            if (WorkModule(0x15, 0x1e000065))
            {
                if (func_72(global27))
                {
                    if (edge_lw_can_counter())     // Sephiroth: not while the Phantom charges (test 105)
                    {
                        func_16(0x155, 0x1);
                        return;
                    }
                }
            }
        }
        if ((global24 & 0x1) != 0 && WorkModule(0x15, 0x1e000074) == 0x1)
        {
            if (ItemModule(0x5, 0x8) == 0x1 || ItemModule(0x5, 0x2) == 0x1 && ItemModule(0x1a) <= 0)
            {
                func_16(0x8c, 0);
                return 0x1;
            }
        }
        if (global24 & 0x40)
        {
            if (WorkModule(0x15, 0x1e00005f))
            {
                func_16(0x2e, 0x1);
                return 0x1;
            }
        }
        if (global24 & 0x8)
        {
            if (WorkModule(0x15, 0x1e000057))
            {
                func_16(0x2a, 0x1);
                return 0x1;
            }
        }
        WorkModule(0x17, 0x1e000065);
        WorkModule(0x17, 0x1e000074);
        WorkModule(0x17, 0x1e00005f);
        WorkModule(0x17, 0x1e000057);
        GroundModule(0x2715);
        func_94();
    }
}

void func_2000()
{
    MotionModule(0x36, 0);
}

int func_2001()
{
    StatusModule(0x5, 0x6, 0x18, 0x5, 0, 0, 0, 0, 0x10c0, 0);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0, 0x4002, 0, 0);
    return 0;
}

void func_2002()
{
    printf("status_Ladder");
    WorkModule(0x7, 0x2, 0x11000000);
    WorkModule(0x19, 0x1f000008);
    if (!StopModule(0x1))
    {
        func_2005();
    }
    global16 = func_2005;
    func_78(func_2003);
}

void func_2003()
{
    if (func_55())
    {
        return 0x1;
    }
    if (global24 & 0x200000)
    {
        func_16(0xb, 0x1);
        return;
    }
    if (WorkModule(0x10, 0x2100000d))
    {
        func_16(0xe, 0);
        return;
    }
    if (GroundModule(0x2722, 0x6))
    {
        func_16(0xe, 0);
        return;
    }
}

void func_2004()
{
    printf("status_end_Ladder");
}

void func_2005()
{
    if (func_84() >= WorkModuleF(0, 0x200018e))
    {
        WorkModule(0x9, 0x11000002);
        if (WorkModule(0x6, 0x11000002) > WorkModule(0x6, 0x1200018d))
        {
            if (global48 >= 0)
            {
                PostureModule(0x2712);
            }
            else
            {
                PostureModule(0x2711);
            }
            PostureModule(0x2719);
            WorkModule(0x2710, 0x2100000d);
        }
    }
}

int func_2006()
{
    StatusModule(0x5, 0xffffffff, 0x19, 0x5, 0, 0, 0, 0, 0x10c0, 0);
    StatusModule(0x2713, 0x1, 0, 0, 0, 0, 0, 0x4002, 0, 0);
    return 0;
}

void func_2007()
{
    func_78(func_2003);
}

void func_2008()
{
    if (GroundModule(0x2722, 0x7))
    {
        func_16(0xe, 0);
        return;
    }
}

void func_2009()
{
    if (global6 == 0)
    {
        func_22(0, 0, 1.0f);
        GroundModule(0x271b);
    }
}

int func_2010()
{
    StatusModule(0x5, 0x2, 0x32, 0x5, 0, 0, 0, 0, 0, 0x40);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x4403e2, 0, 0);
    return 0;
}

void func_2011()
{
    MotionModule(0x4, 0);
    WorkModule(0x2710, 0x21000006);
    KineticModule(0, 0xc);
    AreaModule(0x2710, 0);
    HitModule(0x2710, 0x3);
    WorkModule(0x2710, 0x2100000e);
    WorkModule(0x2711, 0x2000001d);
    WorkModule(0x2710, 0x20000038);
    if (!StopModule(0x1))
    {
        func_2014();
    }
    global16 = func_2014;
    func_78(func_2012);
}

void func_2012()
{
    if (WorkModule(0x10, 0x2100000e) == 0)
    {
        VisibilityModule(0x2710, 0x1);
        if (global18 == 0)
        {
            func_16(0, 0);
        }
        else
        {
            func_16(0xe, 0);
        }
    }
}

void func_2013()
{
    WorkModule(0x2711, 0x20000038);
}

void func_2014()
{
    if (WorkModule(0x10, 0x2100000f) && !WorkModule(0x10, 0x21000010))
    {
        BattleObject(0xc, 0x1);
        WorkModule(0x2710, 0x21000010);
    }
    else if (!WorkModule(0x10, 0x2100000f) && WorkModule(0x10, 0x21000010))
    {
        BattleObject(0xc, 0);
        WorkModule(0x2711, 0x21000010);
    }
}

int func_2015()
{
    WorkModule(0x2710, 0x21000006);
    StatusModule(0x5, 0x2, 0x32, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3e4, 0, 0);
    BattleObject(0x8e, 0x1e);
    return 0;
}

void func_2016()
{
    AreaModule(0x2710, 0);
    HitModule(0x2710, 0x2);
    func_22(0xd2, 0, 1.0f);
    func_78(func_2017);
}

void func_2017()
{
    
}

void func_2018()
{
    
}

void func_2019()
{
    KineticModule(0x2);
    KineticModule(0x3);
    KineticModule(0xe, 0x3, 0x16, 0, 0, 0, 0, 0);
    KineticModule(0x11, 0x3, -0.8299999833106995f * PostureModuleF(0), 4.760000228881836f);
    KineticModule(0xf, 0x3, 0, 0);
    KineticModule(0xb, 0x3);
    KineticModule(0xe, 0x1, 0, 0, 0, 0, 0, 0);
    KineticModule(0xb, 0x1);
}

int func_2020()
{
    WorkModule(0x2710, 0x21000006);
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    return 0;
}

void func_2021()
{
    AreaModule(0x2710, 0);
    func_78(func_2022);
}

void func_2022()
{
    
}

void func_2023()
{
    
}

int func_2024()
{
    WorkModule(0x2710, 0x21000006);
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    return 0;
}

void func_2025()
{
    WorkModule(0x2710, 0x2100000d);
    func_78(func_2026);
}

void func_2026()
{
    float var0;
    var0 = MotionModuleF(0x1);
    if (WorkModule(0x10, 0x2100000d) == 0x1)
    {
        if (var0 >= 3.0f)
        {
            WorkModule(0x2711, 0x2100000d);
            func_22(0x2e, 0, 1.0f);
            MotionModule(0x4, 4.0f);
        }
    }
}

void func_2027()
{
    AreaModule(0x2710, 0);
}

int func_2028()
{
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    return 0;
}

void func_2029()
{
    func_78(func_2030);
}

void func_2030()
{
    
}

void func_2031()
{
    if (global6 == 0x47)
    {
        WorkModule(0x2710, 0x21000018);
        WorkModule(0x2710, 0x2100001c);
    }
}

int func_2032()
{
    WorkModule(0x2710, 0x21000006);
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    BattleObject(0x8e, 0x1e);
    return 0;
}

void func_2033()
{
    AreaModule(0x2710, 0);
    VisibilityModule(0x2710, 0);
    func_22(0, 0, 1.0f);
    KineticModule(0x3);
    KineticModule(0x2);
    func_78(func_2034);
}

void func_2034()
{
    
}

void func_2035()
{
    
}

int func_2036()
{
    WorkModule(0x2710, 0x21000006);
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    return 0;
}

void func_2037()
{
    VisibilityModule(0x2710, 0x1);
    AreaModule(0x2710, 0);
    func_22(0xf1, 0, 1.0f);
    KineticModule(0x3);
    KineticModule(0x2);
    func_78(func_2038);
}

void func_2038()
{
    
}

void func_2039()
{
    AreaModule(0x2710, 0);
}

int func_2040()
{
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    return 0;
}

void func_2041()
{
    func_78(func_2042);
}

void func_2042()
{
    
}

void func_2043()
{
    if (global6 == 0x47)
    {
        WorkModule(0x2710, 0x21000018);
        WorkModule(0x2710, 0x2100001c);
    }
}

int func_2044()
{
    WorkModule(0x2710, 0x21000006);
    StatusModule(0x5, 0x2, 0x32, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3e4, 0, 0);
    BattleObject(0x8e, 0x1e);
    return 0;
}

void func_2045()
{
    AreaModule(0x2710, 0);
    HitModule(0x2710, 0x2);
    func_22(0xd2, 0, 1.0f);
    func_78(func_2046);
}

void func_2046()
{
    
}

void func_2047()
{
    
}

void func_2048()
{
    KineticModule(0x2);
    KineticModule(0x3);
    KineticModule(0xe, 0x3, 0x16, 0, 0, 0, 0, 0);
    KineticModule(0x11, 0x3, -0.8299999833106995f * PostureModuleF(0), 4.760000228881836f);
    KineticModule(0xf, 0x3, 0, 0);
    KineticModule(0xb, 0x3);
    KineticModule(0xe, 0x1, 0, 0, 0, 0, 0, 0);
    KineticModule(0xb, 0x1);
}

int func_2049()
{
    WorkModule(0x2710, 0x21000006);
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    return 0;
}

void func_2050()
{
    AreaModule(0x2710, 0);
    func_78(func_2051);
}

void func_2051()
{
    
}

void func_2052()
{
    
}

int func_2053()
{
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    return 0;
}

void func_2054()
{
    func_78(func_2055);
}

void func_2055()
{
    
}

void func_2056()
{
    if (global6 == 0x47)
    {
        WorkModule(0x2710, 0x21000018);
        WorkModule(0x2710, 0x2100001c);
    }
}

int func_2057()
{
    WorkModule(0x2710, 0x21000006);
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3e4, 0, 0);
    BattleObject(0x8e, 0x1e);
    return 0;
}

void func_2058()
{
    AreaModule(0x2710, 0);
    HitModule(0x2710, 0x2);
    if (global18 == 0)
    {
        func_22(0xc5, 0, 1.0f);
    }
    else
    {
        func_22(0xce, 0, 1.0f);
    }
    MotionModule(0x4, 0.699999988079071f);
    func_20(0x2);
    GroundModule(0x2710, 0x5);
    func_78(func_2059);
}

void func_2059()
{
    
}

void func_2060()
{
    
}

void func_2061()
{
    KineticModule(0x2);
    KineticModule(0x3);
}

int func_2062()
{
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    return 0;
}

void func_2063()
{
    AreaModule(0x2710, 0);
    func_78(func_2064);
}

void func_2064()
{
    
}

void func_2065()
{
    
}

int func_2066()
{
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    return 0;
}

void func_2067()
{
    func_78(func_2068);
}

void func_2068()
{
    
}

void func_2069()
{
    if (global6 == 0x47)
    {
        WorkModule(0x2710, 0x21000018);
        WorkModule(0x2710, 0x2100001c);
    }
}

int func_2070()
{
    WorkModule(0x2710, 0x21000006);
    StatusModule(0x5, 0x2, 0x32, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3e4, 0, 0);
    BattleObject(0x8e, 0x1e);
    return 0;
}

void func_2071()
{
    AreaModule(0x2710, 0);
    HitModule(0x2710, 0x2);
    WorkModule(0x2710, 0x20000038);
    func_22(0xd2, 0, 1.0f);
    func_78(func_2072);
}

void func_2072()
{
    
}

void func_2073()
{
    WorkModule(0x2711, 0x20000038);
}

void func_2074()
{
    KineticModule(0x2);
    KineticModule(0x3);
    KineticModule(0xe, 0x3, 0x16, 0, 0, 0, 0, 0);
    KineticModule(0x11, 0x3, -0.8299999833106995f * PostureModuleF(0), 4.760000228881836f);
    KineticModule(0xf, 0x3, 0, 0);
    KineticModule(0xb, 0x3);
    KineticModule(0xe, 0x1, 0, 0, 0, 0, 0, 0);
    KineticModule(0xb, 0x1);
}

int func_2075()
{
    WorkModule(0x2710, 0x21000006);
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    return 0;
}

void func_2076()
{
    AreaModule(0x2710, 0);
    func_78(func_2077);
}

void func_2077()
{
    
}

void func_2078()
{
    
}

int func_2079()
{
    WorkModule(0x2710, 0x21000006);
    StatusModule(0x5, 0x2, 0x32, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3e4, 0, 0);
    BattleObject(0x8e, 0x1e);
    return 0;
}

void func_2080()
{
    AreaModule(0x2710, 0);
    HitModule(0x2710, 0x2);
    WorkModule(0x2710, 0x20000038);
    WorkModule(0x2710, 0x21000006);
    KineticModule(0, 0xc);
    func_78(func_2081);
}

void func_2081()
{
    
}

void func_2082()
{
    WorkModule(0x2711, 0x20000038);
}

int func_2083()
{
    WorkModule(0x2710, 0x21000006);
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    return 0;
}

void func_2084()
{
    AreaModule(0x2710, 0);
    HitModule(0x2710, 0x3);
    func_78(func_2085);
}

void func_2085()
{
    
}

void func_2086()
{
    HitModule(0x2710, 0);
}

int func_2087()
{
    StatusModule(0x5, 0x2, 0x32, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    return 0;
}

void func_2088()
{
    func_78(func_2089);
}

void func_2089()
{
    
}

void func_2090()
{
    if (global6 == 0x47)
    {
        WorkModule(0x2710, 0x21000018);
        WorkModule(0x2710, 0x2100001c);
    }
}

int func_2091()
{
    WorkModule(0x2710, 0x21000006);
    StatusModule(0x5, 0x2, 0x32, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3e4, 0, 0);
    BattleObject(0x8e, 0x1e);
    return 0;
}

void func_2092()
{
    float var0;
    int var1;
    float var2;
    float var3;
    int var4;
    AreaModule(0x2710, 0);
    HitModule(0x2710, 0x2);
    var0 = WorkModuleF(0, 0x3000031);
    var1 = WorkModule(0x6, 0x1300006a);
    var2 = WorkModuleF(0, 0x300006b);
    var3 = WorkModuleF(0, 0x300006c);
    var4 = EffectModule(0xb, 0x4390001, var1, var2, var3, 0, 0, 0, 0, var0, 0x1, 0, 0, 0xffffffff);
    func_22(0xd2, 0, 1.0f);
    func_78(func_2093);
}

void func_2093()
{
    
}

void func_2094()
{
    EffectModule(0x9, 0x4390001, 0x1, 0x1);
}

void func_2095()
{
    KineticModule(0x2);
    KineticModule(0x3);
    KineticModule(0xe, 0x3, 0x16, 0, 0, 0, 0, 0);
    KineticModule(0x11, 0x3, -0.8299999833106995f * PostureModuleF(0), 4.760000228881836f);
    KineticModule(0xf, 0x3, 0, 0);
    KineticModule(0xb, 0x3);
    KineticModule(0xe, 0x1, 0, 0, 0, 0, 0, 0);
    KineticModule(0xb, 0x1);
}

int func_2096()
{
    WorkModule(0x2710, 0x21000006);
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    return 0;
}

void func_2097()
{
    AreaModule(0x2710, 0);
    PostureModule(0, 1.0f);
    PostureModule(0x2719);
    func_78(func_2098);
}

void func_2098()
{
    float var0;
    int var1;
    int var2;
    if (WorkModule(0x10, 0x2100000e))
    {
        var0 = WorkModuleF(0, 0x3000031);
        var1 = 0x3;
        var2 = EffectModule(0xb, 0x4390009, var1, 0, 0, 0, 0, 0, 0, var0, 0x1, 0, 0, 0xffffffff);
        WorkModule(0x2711, 0x2100000e);
    }
}

void func_2099()
{
    EffectModule(0x9, 0x4390009, 0x1, 0x1);
}

int func_2100()
{
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403ea, 0, 0);
    return 0;
}

void func_2101()
{
    func_78(func_2102);
}

void func_2102()
{
    
}

void func_2103()
{
    if (global6 == 0x47)
    {
        WorkModule(0x2710, 0x21000018);
        WorkModule(0x2710, 0x2100001c);
    }
}

int func_2104()
{
    StatusModule(0x5, 0x3, 0x39, 0x5, 0, 0x1, 0x2000, 0x30, 0, 0x1);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x2000, 0, 0, 0);
    return 0;
}

void func_2105()
{
    WorkModule(0, 0, 0);
    WorkModule(0x12, 0x20000003);
    func_2146();
    func_22(0x24, 0, 1.0f);
    func_78(func_2106);
}

void func_2106()
{
    
}

void func_2107()
{
    
}

int func_2108()
{
    StatusModule(0x5, 0x3, 0x3a, 0x5, 0, 0x1, 0x2000, 0x30, 0, 0x1);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x2000, 0, 0, 0);
    return 0;
}

void func_2109()
{
    func_2146();
    func_22(0x19c, 0, 1.0f);
    func_78(func_2110);
}

void func_2110()
{
    
}

void func_2111()
{
    
}

int func_2112()
{
    StatusModule(0x5, 0x3, 0x3c, 0x5, 0, 0x1, 0x2000, 0x30, 0, 0x1);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x2000, 0, 0, 0);
    return 0;
}

void func_2113()
{
    func_2146();
    if (WorkModule(0x10, 0x2100000d))
    {
        func_22(0x19e, 0, 1.0f);
    }
    else
    {
        func_22(0x19d, 0, 1.0f);
    }
    func_78(func_2114);
}

void func_2114()
{
    if (MotionModule(0x2712))
    {
        func_16(0xaa, 0);
        return;
    }
}

void func_2115()
{
    
}

int func_2116()
{
    StatusModule(0x5, 0x3, 0x3c, 0x5, 0, 0x1, 0x2000, 0x30, 0, 0x1);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x2000, 0, 0, 0);
    return 0;
}

void func_2117()
{
    func_2148();
    func_2146();
    func_22(0x19f, 0, 1.0f);
    func_78(func_2118);
}

void func_2118()
{
    if (func_2147())
    {
        return;
    }
    if (func_2149())
    {
        return;
    }
    if (func_88() <= WorkModuleF(0, 0x2000006))
    {
        func_16(0xad, 0x1);
        return;
    }
    if (func_84() >= WorkModuleF(0, 0x2000001))
    {
        func_16(0xab, 0x1);
        return;
    }
}

void func_2119()
{
    
}

int func_2120()
{
    StatusModule(0x5, 0x3, 0x3b, 0x5, 0, 0x1, 0x2000, 0x30, 0, 0x1);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x2000, 0, 0, 0);
    return 0;
}

void func_2121()
{
    func_2148();
    func_22(0x1a0, 0, 1.0f);
    func_78(func_2122);
}

void func_2122()
{
    if (func_84() < WorkModuleF(0, 0x2000001))
    {
        func_16(0xac, 0x1);
        return;
    }
    if (func_88() < (float)0)
    {
        func_16(0xac, 0x1);
        return;
    }
    if (func_2147())
    {
        return;
    }
    if (func_2149())
    {
        return;
    }
}

void func_2123()
{
    
}

int func_2124()
{
    StatusModule(0x5, 0x3, 0x3c, 0x5, 0, 0x1, 0x2000, 0x30, 0, 0x1);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x2000, 0, 0, 0);
    return 0;
}

void func_2125()
{
    func_2148();
    func_22(0x1a1, 0, 1.0f);
    func_78(func_2126);
}

void func_2126()
{
    if (MotionModule(0x2712))
    {
        func_16(0xaa, 0);
        return;
    }
    if (func_88() <= WorkModuleF(0, 0x2000006))
    {
        func_16(0xad, 0x1);
        return;
    }
    if (CancelModule(0x2713) == 0x1)
    {
        if (func_88() >= WorkModuleF(0, 0x2000001))
        {
            func_16(0xab, 0x1);
            return;
        }
    }
    if (func_2147())
    {
        return;
    }
    if (func_2149())
    {
        return;
    }
}

void func_2127()
{
    
}

int func_2128()
{
    StatusModule(0x5, 0x3, 0x3c, 0x5, 0, 0x1, 0x2000, 0x30, 0, 0x1);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x2000, 0, 0, 0);
    return 0;
}

void func_2129()
{
    PostureModule(0x2710);
    func_2148();
    func_22(0x1a2, 0, 1.0f);
    func_78(func_2130);
}

void func_2130()
{
    if (MotionModule(0x2712))
    {
        func_16(0xaa, 0);
        return;
    }
    if (CancelModule(0x2713) == 0x1)
    {
        if (func_88() >= WorkModuleF(0, 0x2000001))
        {
            func_16(0xab, 0x1);
            return;
        }
    }
    if (func_2147())
    {
        return;
    }
    if (func_2149())
    {
        return;
    }
}

void func_2131()
{
    
}

int func_2132()
{
    StatusModule(0x5, 0x3, 0x3d, 0x5, 0, 0x1, 0x2000, 0x30, 0, 0x1);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_2133()
{
    func_76();
    ControlModule(0x271b);
    WorkModule(0x7, 0, 0x11000003);
    if (WorkModule(0x6, 0x10000013) < WorkModule(0x6, 0x12000194))
    {
        WorkModule(0x9, 0x10000013);
    }
    WorkModule(0x7, 0x4, 0x11000000);
    func_22(0x19, 0, 1.0f);
    MotionModule(0x4, 0);
    if (!StopModule(0x1))
    {
        func_2136();
    }
    global16 = func_2136;
    func_78(func_2134);
}

void func_2134()
{
    if (WorkModule(0x6, 0x11000003) > WorkModule(0x6, 0x12000191))
    {
        func_16(0xb, 0);
        return;
    }
}

void func_2135()
{
    
}

void func_2136()
{
    WorkModule(0x9, 0x11000003);
}

int func_2137()
{
    StatusModule(0x5, 0x3, 0x3e, 0x5, 0, 0x1, 0x2000, 0x30, 0, 0x1);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0x4, 0, 0, 0);
    return 0;
}

void func_2138()
{
    WorkModule(0x7, 0, 0x11000003);
    func_22(0x1a3, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_2141();
    }
    global16 = func_2141;
    func_78(func_2139);
}

void func_2139()
{
    if (WorkModule(0x6, 0x11000003) >= WorkModule(0x6, 0x12000199))
    {
        func_16(0xb0, 0);
    }
    if (func_2147())
    {
        return;
    }
}

void func_2140()
{
    
}

void func_2141()
{
    WorkModule(0x9, 0x11000003);
}

int func_2142()
{
    StatusModule(0x5, 0x3, 0x3f, 0, 0, 0, 0x2000, 0x30, 0, 0x1);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0x4, 0x800, 0, 0);
    return 0;
}

void func_2143()
{
    HitModule(0x2710, 0x3);
    AreaModule(0x2710, 0);
    func_22(0x1a4, 0, 1.0f);
    func_78(func_2144);
}

void func_2144()
{
    
}

void func_2145()
{
    
}

void func_2146()
{
    int var0;
    var0 = ItemModule(0x11);
    if (var0 == 0x73 || var0 == 0x77 || var0 == 0x3e || var0 == 0x4c)
    {
        ItemModule(0x8);
    }
}

int func_2147()
{
    if (global24 & 0x200000)
    {
        func_16(0xae, 0x1);
        return 0x1;
    }
    if (global24 & 0x100000)
    {
        func_16(0xae, 0x1);
        return 0x1;
    }
    return 0;
}

void func_2148()
{
    WorkModule(0x7, WorkModule(0x6, 0x12000196), 0x11000002);
}

int func_2149()
{
    if (WorkModule(0x10, 0x2000001b))
    {
        func_16(0xb0, 0);
        return 0x1;
    }
    if (WorkModule(0x6, 0x10000014) >= WorkModule(0x6, 0x11000002))
    {
        func_16(0xaf, 0);
        return 0x1;
    }
    return 0;
}

int func_2150()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xa, 0, 0);
    return 0;
}

void func_2151()
{
    int var0;
    int var1;
    float var2;
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    CaptureModule(0x2);
    var0 = WorkModule(0x6, 0x13000120);
    if (var0 == 0x1)
    {
        var1 = 0x1;
    }
    else if (var0 == 0x3)
    {
        var1 = 0x2;
    }
    MotionModule(0x29, var1);
    LinkModule(0x2716, 0, 0x3);
    var2 = LinkModuleF(0x7, 0);
    PostureModule(0, -var2);
    func_22(0x20d, 0, 1.0f);
    DamageModule(0x12, 0x2);
    LinkModule(0x271d, 0, 0xbfc0058);
    func_78(func_1655);
}

void func_2152()
{
    int var0;
    DamageModule(0x12, 0xffffffff);
    CaptureModule(0x4);
    var0 = WorkModule(0x6, 0x120000f8);
    WorkModule(0x7, var0, 0x10000058);
    WorkModule(0x2711, 0x20000031);
}

int func_2153()
{
    StatusModule(0x5, 0x2, 0x33, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3e6, 0, 0);
    return 0;
}

void func_2154()
{
    func_35(0xd4, 0, 1.0f);
    func_78(func_2155);
}

void func_2155()
{
    
}

void func_2156()
{
    
}

int func_2157()
{
    StatusModule(0x5, 0, 0x33, 0x2, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_2158()
{
    ItemModule(0xf, 0);
    HitModule(0x271a, 0x1);
    AreaModule(0x2710, 0);
    BattleObject(0x29);
    BattleObject(0xa, 0x1);
    if (global1 == 0x5 || global1 == 0xe)
    {
        MotionModule(0x32);
    }
    if (PostureModuleF(0) == -1.0f && MotionModule(0x22, 0x1a6))
    {
        func_22(0x1a6, 0, 1.0f);
    }
    else if (MotionModule(0x22, 0x1a5))
    {
        func_22(0x1a5, 0, 1.0f);
    }
    else
    {
        func_16(0);
        return;
    }
    func_78(func_2159);
}

void func_2159()
{
    if (MotionModule(0x2712))
    {
        func_16(0);
    }
    if (!global3)
    {
        func_2162();
    }
    if (StatusModule(0x6) == 0x1 || global18 == 0 && global19 != 0 || global18 == 0x2 && global19 == 0)
    {
        if (global18 == 0)
        {
            GroundModule(0x2710, 0x2);
        }
        else
        {
            GroundModule(0x2710, 0x5);
        }
    }
}

void func_2160()
{
    if (global1 == 0x5 || global1 == 0xe)
    {
        MotionModule(0x31);
    }
}

void func_2161()
{
    int var0;
    printf("------------------sub_entry_uniq_process_init()------------------");
    WorkModule(0x2710, 0x20000001);
    var0 = PostureModuleF(0) == -1.0f;
    if (global1 == 0x3)
    {
        ArticleModule(0x2710, 0x4);
        if (var0)
        {
            ArticleModule(0x2715, 0x4, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x4, 0x1, 0x1);
        }
    }
    else if (global1 == 0x9)
    {
        ArticleModule(0x2710, 0x4);
        if (var0)
        {
            ArticleModule(0x2715, 0x4, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x4, 0x1, 0x1);
        }
    }
    else if (global1 == 0x15)
    {
        printf("------------------sub_entry_uniq_process_init()------------------");
        ArticleModule(0x2710, 0x4);
        if (var0)
        {
            ArticleModule(0x2715, 0x4, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x4, 0x1, 0x1);
        }
    }
    else if (global1 == 0x16)
    {
        WorkModule(0, WorkModuleF(0, 0x6000007) + 0, 0x30);
        ArticleModule(0x2710, 0);
        if (var0)
        {
            ArticleModule(0x2715, 0, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0, 0x1, 0x1);
        }
        WorkModule(0x2710, 0x2000007c);
    }
    else if (global1 == 0x3b)
    {
        ArticleModule(0x2710, 0);
        if (var0)
        {
            ArticleModule(0x2715, 0, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0, 0x1, 0x1);
        }
        WorkModule(0x2710, 0x2000007c);
    }
    else if (global1 == 0x13)
    {
        ArticleModule(0x2710, 0x7);
    }
    else if (global1 == 0xc)
    {
        ArticleModule(0x2710, 0);
        if (var0)
        {
            ArticleModule(0x2715, 0, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0, 0x1, 0x1);
        }
    }
    else if (global1 == 0x17)
    {
        ArticleModule(0x2710, 0);
        if (var0)
        {
            ArticleModule(0x2715, 0, 0x17, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0, 0x18, 0x1);
        }
    }
    else if (global1 == 0xb)
    {
        ArticleModule(0x2710, 0x1);
        if (var0)
        {
            ArticleModule(0x2715, 0x1, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x1, 0x1, 0x1);
        }
    }
    else if (global1 == 0x6)
    {
        ArticleModule(0x2710, 0x8);
        if (var0)
        {
            ArticleModule(0x2715, 0x8, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x8, 0x1, 0x1);
        }
    }
    else if (global1 == 0x8)
    {
        ArticleModule(0x2710, 0x1f);
        if (var0)
        {
            ArticleModule(0x2715, 0x1f, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x1f, 0x1, 0x1);
        }
    }
    else if (global1 == 0x1b)
    {
        ArticleModule(0x2710, 0x4);
        if (var0)
        {
            ArticleModule(0x2715, 0x4, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x4, 0x1, 0x1);
        }
    }
    else if (global1 == 0x4)
    {
        ArticleModule(0x2710, 0x2);
        if (var0)
        {
            ArticleModule(0x2715, 0x2, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x2, 0x1, 0x1);
        }
    }
    else if (global1 == 0xa)
    {
        ArticleModule(0x2710, 0x4);
        if (var0)
        {
            ArticleModule(0x2715, 0x4, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x4, 0x1, 0x1);
        }
    }
    else if (global1 == 0x23)
    {
        ArticleModule(0x2710, 0x1);
        ArticleModule(0x2715, 0x1, 0, 0x1);
    }
    else if (global1 == 0x21)
    {
        ArticleModule(0x2710, 0x4);
        ArticleModule(0x2715, 0x4, 0, 0x1);
    }
    else if (global1 == 0x30)
    {
        ArticleModule(0x2710, 0x4);
        ArticleModule(0x2715, 0x4, 0, 0x1);
    }
    else if (global1 == 0xe)
    {
        ArticleModule(0x2710, 0);
        if (var0)
        {
            ArticleModule(0x2715, 0, 0x18, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0, 0x1c, 0x1);
        }
    }
    else if (global1 == 0x1c)
    {
        ArticleModule(0x2710, 0x6);
        if (var0)
        {
            ArticleModule(0x2715, 0x6, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x6, 0x1, 0x1);
        }
    }
    else if (global1 == 0x27)
    {
        ArticleModule(0x2710, 0);
    }
    else if (global1 == 0x2a)
    {
        ArticleModule(0x2710, 0x10);
        if (var0)
        {
            ArticleModule(0x2715, 0x10, 0x1, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x10, 0x2, 0x1);
        }
    }
    else if (global1 == 0x31)
    {
        ArticleModule(0x2710, 0x3);
        ArticleModule(0x2715, 0x3, 0x2, 0x1);
    }
    else if (global1 == 0x2b)
    {
        ArticleModule(0x2710, 0x9);
        if (var0)
        {
            ArticleModule(0x2715, 0x9, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x9, 0x1, 0x1);
        }
    }
    else if (global1 == 0x1a)
    {
        ArticleModule(0x2710, 0x1);
        if (var0)
        {
            ArticleModule(0x2715, 0x1, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x1, 0x1, 0x1);
        }
    }
    else if (global1 == 0x28)
    {
        ArticleModule(0x2710, 0x2);
        ArticleModule(0x2710, 0x3);
        if (var0)
        {
            ArticleModule(0x2715, 0x2, 0, 0x1);
            ArticleModule(0x2715, 0x3, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x2, 0x1, 0x1);
            ArticleModule(0x2715, 0x3, 0x1, 0x1);
        }
    }
    else if (global1 == 0x19)
    {
        ArticleModule(0x2710, 0x4);
        if (var0)
        {
            ArticleModule(0x2715, 0x4, 0x1, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x4, 0x2, 0x1);
        }
    }
    else if (global1 == 0x24)
    {
        ArticleModule(0x2710, 0x1);
        if (var0)
        {
            ArticleModule(0x2715, 0x1, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x1, 0x1, 0x1);
        }
    }
    else if (global1 == 0x29)
    {
        ArticleModule(0x272d, 0x1);
        if (var0)
        {
            ArticleModule(0x272e, 0x1, 0, 0x1);
        }
        else
        {
            ArticleModule(0x272e, 0x1, 0x1, 0x1);
        }
        ArticleModule(0x2710, 0x2);
        if (var0)
        {
            ArticleModule(0x2715, 0x2, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x2, 0x1, 0x1);
        }
    }
    else if (global1 == 0x25)
    {
        ArticleModule(0x2710, 0);
        if (var0)
        {
            ArticleModule(0x2715, 0, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0, 0x1, 0x1);
        }
    }
    else if (global1 == 0x35)
    {
        ArticleModule(0x2710, 0x6);
        if (var0)
        {
            ArticleModule(0x2715, 0x6, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0x6, 0x1, 0x1);
        }
    }
    else if (global1 == 0x36)
    {
        ArticleModule(0x2710, 0);
        if (var0)
        {
            ArticleModule(0x2715, 0, 0, 0x1);
        }
        else
        {
            ArticleModule(0x2715, 0, 0x1, 0x1);
        }
    }
    GroundModule(0x2, 0x1);
    GroundModule(0x2717, 0x8, 0x1);
    GroundModule(0x2714, WorkModuleF(0, 0x300009a), 0, 4.0f);
    GroundModule(0x2721, 0);
    WorkModule(0x2710, 0x2000003d);
}

void func_2162()
{
    if (MotionModule(0x2712))
    {
        GroundModule(0x2, 0);
        if (GroundModule(0x2716))
        {
            func_20(0);
            func_16(0, 0x1);
        }
        else
        {
            func_20(0x2);
            func_16(0xe, 0x1);
        }
    }
}

void func_2163()
{
    printf("--------------sub_entry_uniq_process_exit()----------------");
    WorkModule(0x2711, 0x20000001);
    GroundModule(0x2, 0);
    HitModule(0x271a, 0);
    if (global1 == 0x3)
    {
        ArticleModule(0x2711, 0x4);
    }
    else if (global1 == 0x9)
    {
        ArticleModule(0x2711, 0x4);
    }
    else if (global1 == 0x15)
    {
        ArticleModule(0x2711, 0x4);
    }
    else if (global1 == 0x16)
    {
        if (ArticleModule(0x2717, 0))
        {
            ArticleModule(0x2712, 0);
        }
    }
    else if (global1 == 0x3b)
    {
        if (ArticleModule(0x2717, 0))
        {
            ArticleModule(0x2712, 0);
        }
    }
    else if (global1 == 0xc)
    {
        if (ArticleModule(0x2717, 0))
        {
            ArticleModule(0x2712, 0);
        }
    }
    else if (global1 == 0x17)
    {
        if (ArticleModule(0x2717, 0))
        {
            ArticleModule(0x2712, 0);
        }
    }
    else if (global1 == 0xb)
    {
        ArticleModule(0x2711, 0x1);
    }
    else if (global1 == 0x6)
    {
        ArticleModule(0x2711, 0x8);
    }
    else if (global1 == 0x8)
    {
        ArticleModule(0x2711, 0x1f);
    }
    else if (global1 == 0x4)
    {
        ArticleModule(0x2711, 0x2);
    }
    else if (global1 == 0xa)
    {
        ArticleModule(0x2711, 0x4);
    }
    else if (global1 == 0x23)
    {
        ArticleModule(0x2711, 0x1);
    }
    else if (global1 == 0x21)
    {
        ArticleModule(0x2711, 0x4);
    }
    else if (global1 == 0x30)
    {
        ArticleModule(0x2711, 0x4);
    }
    else if (global1 == 0xe)
    {
        ArticleModule(0x2711, 0);
    }
    else if (global1 == 0x1c)
    {
        ArticleModule(0x2711, 0x6);
    }
    else if (global1 == 0x1a)
    {
        ArticleModule(0x2711, 0x1);
    }
    else if (global1 == 0x2a)
    {
        ArticleModule(0x2711, 0x10);
    }
    else if (global1 == 0x31)
    {
        if (ArticleModule(0x2717, 0x3))
        {
            ArticleModule(0x2711, 0x3);
        }
    }
    else if (global1 == 0x28)
    {
        ArticleModule(0x2711, 0x2);
        ArticleModule(0x2711, 0x3);
    }
    else if (global1 == 0x2d)
    {
        if (ArticleModule(0x2717, 0xc))
        {
            ArticleModule(0x2711, 0xc);
        }
    }
    else if (global1 == 0x19)
    {
        ArticleModule(0x2711, 0x4);
    }
    else if (global1 == 0x2b)
    {
        ArticleModule(0x2711, 0x9);
    }
    else if (global1 == 0x24)
    {
        ArticleModule(0x2711, 0x1);
    }
    else if (global1 == 0x29)
    {
        if (ArticleModule(0x2717, 0x1))
        {
            ArticleModule(0x2711, 0x1);
        }
        if (ArticleModule(0x2717, 0x2))
        {
            ArticleModule(0x2711, 0x2);
        }
    }
    else if (global1 == 0x25)
    {
        ArticleModule(0x2711, 0);
    }
    else if (global1 == 0x13)
    {
        ArticleModule(0x2711, 0x7);
    }
    else if (global1 == 0x35)
    {
        ArticleModule(0x2711, 0x6);
    }
    else if (global1 == 0x36)
    {
        ArticleModule(0x2711, 0);
    }
}

int func_2164()
{
    StatusModule(0x5, 0, 0x33, 0x2, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_2165()
{
    func_78(func_2166);
}

void func_2166()
{
    
}

void func_2167()
{
    
}

int func_2168()
{
    StatusModule(0x5, 0, 0x33, 0x2, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_2169()
{
    func_78(func_2170);
}

void func_2170()
{
    
}

void func_2171()
{
    
}

int func_2172(int arg0, int arg1)
{
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0x1c, 0x6100, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, arg1 | 0x2 | 0x3e0, 0, 0);
    BattleObject(0x8e, arg0);
    return 0;
}

int func_2173()
{
    return func_2172(0x1a, 0);
}

int func_2174()
{
    return func_2172(0x1b, 0);
}

int func_2175()
{
    return func_2172(0x1a, 0x2000000);
}

void func_2176()
{
    AreaModule(0x2710, 0);
    DamageModule(0xb, 0x1, (float)0 + 0);
    func_22(WorkModule(0x6, 0x11000003), 0, 1.0f);
    func_78(func_2178);
}

void func_2177()
{
    AreaModule(0x2710, 0);
    DamageModule(0xb, 0x1, (float)0 + 0);
    func_78(func_2178);
}

void func_2178()
{
    
}

void func_2179()
{
    DamageModule(0xb, 0, (float)0 + 0);
}

int func_2180()
{
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3e2, 0, 0);
    return 0;
}

void func_2181()
{
    AreaModule(0x2710, 0);
    DamageModule(0xb, 0x1, (float)0 + 0);
    func_22(WorkModule(0x6, 0x11000003), 0, 1.0f);
    func_78(func_2183);
}

void func_2182()
{
    if (MotionModule(0x28) == 0x1)
    {
        WorkModule(0x2710, 0x21000011);
    }
    else
    {
        WorkModule(0x2711, 0x21000011);
    }
    if (WorkModule(0x6, 0x11000004) < 0)
    {
        MotionModule(0x27, 0x1);
    }
    func_2181();
}

void func_2183()
{
    
}

void func_2184()
{
    float var0;
    float var1;
    DamageModule(0xb, 0, (float)0 + 0);
    var0 = PostureModuleF(0x1);
    var1 = PostureModuleF(0x2);
    GroundModule(0x1a, var0, var1);
}

void func_2185()
{
    func_2184();
    if (WorkModule(0x10, 0x21000011) == 0x1)
    {
        MotionModule(0x27, 0x1);
    }
    else
    {
        MotionModule(0x27, 0);
    }
}

int func_2186()
{
    StatusModule(0x5, 0x2, 0x32, 0x5, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3e2, 0, 0);
    return 0;
}

void func_2187()
{
    AreaModule(0x2710, 0);
    DamageModule(0xb, 0x1, (float)0 + 0);
    func_22(WorkModule(0x6, 0x11000003), 0, 1.0f);
    func_78(func_2188);
}

void func_2188()
{
    
}

void func_2189()
{
    DamageModule(0xb, 0, (float)0 + 0);
}

int func_2190()
{
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403e2, 0, 0);
    BattleObject(0x8e, 0x1a);
    return 0;
}

int func_2191()
{
    StatusModule(0x5, 0, 0x32, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3e2, 0, 0);
    return 0;
}

int func_2192()
{
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0x200);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3e2, 0, 0);
    return 0;
}

int func_2193()
{
    StatusModule(0x5, 0x2, 0x32, 0x5, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0x200);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3e2, 0, 0);
    return 0;
}

int func_2194()
{
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0x200);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x3e2, 0, 0);
    return 0;
}

int func_2195()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403e2, 0, 0);
    BattleObject(0x8e, 0x1e);
    return 0;
}

void func_2196()
{
    func_2199(0);
    func_22(0xffffffff, 0, 1.0f);
    func_78(func_2197);
}

void func_2197()
{
    
}

void func_2198()
{
    if (global6 != 0x47 && global6 != 0x48)
    {
        func_2200(0);
    }
}

void func_2199(int arg0)
{
    int var1;
    int var2;
    WorkModule(0x2710, 0x2000005a);
    if (arg0)
    {
        HitModule(0x2710, 0x3);
    }
    else
    {
        HitModule(0x2710, 0x2);
    }
    AreaModule(0x2710, 0);
    VisibilityModule(0x2710, 0);
    ItemModule(0xf, 0);
    ItemModule(0x16, 0);
    if (arg0)
    {
        var1 = WorkModule(0x6, 0x10000075);
        if (var1 == 0)
        {
            var2 = 0x431000b;
        }
        else if (var1 == 0x1)
        {
            var2 = 0x431000a;
        }
        else if (var1 == 0x2)
        {
            var2 = 0x4310008;
        }
        else
        {
            var2 = 0x4310009;
        }
        EffectModule(0xb, var2, 0, 0, 0, 0, 0, 0, 0, 1.0f, 0x1, 0x400000, 0, 0);
    }
}

void func_2200(int arg0)
{
    WorkModule(0x2711, 0x2000005a);
    HitModule(0x2710, 0);
    AreaModule(0x2710, 0x1);
    VisibilityModule(0x2710, 0x1);
    ItemModule(0xf, 0x1);
    ItemModule(0x16, 0x1);
    if (arg0)
    {
        EffectModule(0xa, 0x400000, 0x1, 0x1);
    }
}

int func_2201()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x40be2, 0, 0);
    BattleObject(0x8e, 0x1e);
    return 0;
}

void func_2202()
{
    WorkModule(0x2710, 0x20000001);
    WorkModule(0x2710, 0x20000065);
    AreaModule(0x2710, 0);
    func_22(0x2e, 0, 1.0f);
    func_78(func_2203);
}

void func_2203()
{
    
}

void func_2204()
{
    WorkModule(0x2711, 0x20000065);
    VisibilityModule(0x2710, 0x1);
    HitModule(0x2710, 0);
}

int func_2205()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0x403e2, 0, 0);
    BattleObject(0x8e, 0xffffffff);
    return 0;
}

void func_2206()
{
    HitModule(0x2710, 0x2);
    AreaModule(0x2710, 0);
    func_22(0x2e, 0, 0);
    func_78(func_2207);
}

void func_2207()
{
    
}

void func_2208()
{
    
}

int func_2209()
{
    StatusModule(0x5, 0x2, 0x33, 0x7, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x4003ea, 0, 0);
    return 0;
}

void func_2210()
{
    AreaModule(0x2710, 0);
    DamageModule(0xb, 0x1, (float)0 + 0);
    func_22(0x2e, 0, 1.0f);
    func_78(func_2211);
}

void func_2211()
{
    if (WorkModule(0x10, 0x2100000d))
    {
        DamageModule(0xb, 0, (float)0 + 0);
    }
    else
    {
        DamageModule(0xb, 0x1, (float)0 + 0);
    }
}

void func_2212()
{
    DamageModule(0xb, 0, (float)0 + 0);
}

int func_2213()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x4003ea, 0, 0);
    return 0;
}

void func_2214()
{
    VisibilityModule(0x2710, 0);
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    ItemModule(0x16, 0);
    HitModule(0x2710, 0x2);
    WorkModule(0x2710, 0x21000003);
    func_22(0xffffffff, 0, 1.0f);
    func_78(func_2215);
}

void func_2215()
{
    if (ControlModuleF(0x5) <= 0)
    {
        func_16(0x43, 0);
        return;
    }
}

void func_2216()
{
    VisibilityModule(0x2710, 0x1);
    AreaModule(0x2710, 0x1);
    ItemModule(0xf, 0x1);
    ItemModule(0x16, 0x1);
    HitModule(0x2710, 0);
    if (global6 != 0xb1)
    {
        HitModule(0x1, WorkModule(0x6, 0x11000002), 0);
    }
}

int func_2217()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0, 0x4003ea, 0, 0);
    return 0;
}

void func_2218()
{
    AreaModule(0x2710, 0);
    ItemModule(0xf, 0);
    ItemModule(0x16, 0);
    HitModule(0x2710, 0x2);
    WorkModule(0x2710, 0x20000001);
    func_22(0x89, 0, 1.0f);
    func_78(func_2219);
}

void func_2219()
{
    
}

void func_2220()
{
    
}

int func_2221()
{
    StatusModule(0x5, 0x4, 0x33, 0, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x2, 0, 0x1, 0x1, 0, 0x40be2, 0, 0);
    BattleObject(0x8e, 0x1a);
    return 0;
}

void func_2222()
{
    HitModule(0x2710, 0x3);
    AreaModule(0x2710, 0);
    DamageModule(0xb, 0x1, (float)0 + 0);
    WorkModule(0x2710, 0x20000001);
    func_22(0x2e, 0, 1.0f);
    func_78(func_2223);
}

void func_2223()
{
    
}

void func_2224()
{
    VisibilityModule(0x2710, 0x1);
}

int func_2225()
{
    return func_793();
}

void func_2226()
{
    WorkModule(0x2710, 0x21000016);
    func_797();
    func_800();
    BattleObject(0x6c);
    func_78(func_2227);
}

int func_2227()
{
    if (func_799())
    {
        return 0x1;
    }
    if (global9 >= 3.0f && WorkModule(0x10, 0x2100001d) == 0)
    {
        BattleObject(0x6d);
        WorkModule(0x2710, 0x2100001d);
    }
    func_2229();
    return 0;
}

void func_2228()
{
    
}

void func_2229()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    int var7;
    int var8;
    if (AttackModule(0, 0) == 0x1)
    {
        if (WorkModuleF(0, 0x100000e) == 0)
        {
            var0 = AttackModuleF(0, 0, 0);
            WorkModule(0, var0 + 0, 0x100000e);
            AttackModule(0x271b, 0, WorkModuleF(0, 0x3000030));
        }
        var1 = KineticModuleF(0x4);
        var2 = KineticModuleF(0x5);
        var3 = MathF(0, var1 * var1 + var2 * var2);
        var4 = WorkModuleF(0, 0x2000150);
        var5 = WorkModuleF(0, 0x2000151);
        if (var3 < var5 || var4 < var5)
        {
            AttackModule(0x2718, 0);
        }
        else
        {
            var6 = WorkModuleF(0, 0x100000e);
            var0 = var6 * (var3 - var5) / (var4 - var5);
            if (var0 > var6)
            {
                var0 = var6;
            }
            AttackModule(0x271a, 0, var0, 0);
            var7 = (int)MathF(0x1, var2, var1 * -PostureModuleF(0));
            var8 = (int)((float)(var7 * 0xb4) / M_PI);
            if (var8 < 0)
            {
                var8 += 0x168;
            }
            AttackModule(0x2739, 0, var8);
        }
    }
}

int func_2230()
{
    if (func_42())
    {
        return 0x1;
    }
    StatusModule(0x5, 0, 0x1a, 0x1, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0, 0, 0, 0, 0, 0x4, 0, 0);
    return 0;
}

void func_2231()
{
    func_22(0xc3, 0, 1.0f);
    WorkModule(0x2711, 0x21000022);
    WorkModule(0x2711, 0x21000023);
    WorkModule(0x2711, 0x21000024);
    func_78(func_2232);
}

void func_2232()
{
    if (global18 != 0)
    {
        func_16(0xe, 0);
        return;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0x50, 0);
            return 0x1;
        }
    }
}

void func_2233()
{
    
}

void func_2234()
{
    int var0;
    float var1;
    float var2;
    float var3;
    float var4;
    int var5;
    func_859();
    if (WorkModule(0x10, 0x21000022) == 0)
    {
        if (func_95() == 0)
        {
            PhysicsModule(0x9);
            var0 = 0;
            if (MotionModule(0xc, 0xe8) == 0x1)
            {
                var0 = 0xe8;
                WorkModule(0x12, 0x2100001e);
            }
            else
            {
                var0 = 0xde;
                WorkModule(0x11, 0x2100001e);
            }
            func_22(var0, 0, 1.0f);
            WorkModule(0x2710, 0x21000022);
        }
    }
    else if (WorkModule(0x10, 0x21000024) == 0)
    {
        var1 = MotionModuleF(0x1);
        if (var1 >= WorkModuleF(0, 0x20001e2))
        {
            var2 = WorkModuleF(0, 0x20001e3);
            var3 = (float)WorkModule(0x6, 0x11000011) + 0;
            var3 *= WorkModuleF(0, 0x30000fe);
            var4 = 1.0f;
            if (var3 != 0)
            {
                var4 = var2 / var3;
            }
            MotionModule(0x4, var4);
            var5 = (int)var3;
            WorkModule(0x7, var5, 0x11000011);
            WorkModule(0x2710, 0x21000024);
            WorkModule(0x2710, 0x21000023);
        }
    }
    else if (WorkModule(0x10, 0x21000023))
    {
        WorkModule(0xa, 0x11000011);
        if (WorkModule(0x6, 0x11000011) <= 0)
        {
            MotionModule(0x4, 1.0f);
            WorkModule(0x2711, 0x21000023);
        }
    }
}

int func_2235()
{
    StatusModule(0x5, 0x2, 0x33, 0x5, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0x1, 0, 0, 0xa6, 0, 0);
    return 0;
}

void func_2236()
{
    float var0;
    KineticModule(0x3);
    KineticModule(0xc, 0x4);
    KineticModule(0xc, 0x5);
    KineticModule(0xc, 0x7);
    KineticModule(0xc, 0x6);
    MotionModule(0x4, WorkModuleF(0, 0x20001ec));
    var0 = (float)WorkModule(0x6, 0x120001e8);
    var0 += DamageModuleF(0) * WorkModuleF(0, 0x20001e9);
    ControlModule(0x6, var0, WorkModuleF(0, 0x20001ea), WorkModuleF(0, 0x20001eb), 0xffffffff, 0x1);
    WorkModule(0x2711, 0x20000077);
    func_78(func_2237);
}

void func_2237()
{
    int var0;
    printf("status_KamuiPierce_Main clatter: %f", ControlModuleF(0x5));
    if (!LinkModule(0x2, 0x7) || WorkModule(0x10, 0x2100000d) || ControlModuleF(0x5) <= 0)
    {
        var0 = 0x4c;
        func_16(var0, 0);
        return 0x1;
    }
}

void func_2238()
{
    float var0;
    float var1;
    if (LinkModule(0x2, 0x7) == 0x1)
    {
        LinkModule(0x6, 0x7);
    }
    ControlModule(0x7);
    ShakeModule(0x2, 0x3);
    KineticModule(0xb, 0x4);
    KineticModule(0xb, 0x5);
    KineticModule(0xb, 0x7);
    MotionModule(0x4, 1.0f);
    WorkModule(0x2711, 0x20000076);
    var0 = PostureModuleF(0x1);
    var1 = PostureModuleF(0x2);
    GroundModule(0x1a, var0, var1);
}

void main()
{
    printf("ENTRY This Fighter is driven by msc.");
    func_0();
    global0 = sys_7(0);
    global1 = sys_7(0x1);
    func_2242();
    sys_0(0x2, func_1);
    sys_0(0x3, func_5);
    sys_0(0x4, func_10);
    set_main(func_73);
}

void func_2240()
{
    func_112();
    func_113();
    func_114();
    func_115();
    func_116();
    func_117();
    func_118();
    func_119();
    func_120();
    func_121();
    func_122();
}

void func_2241()
{
    global48 = 0;
    global32 = 0;
    global38 = 0;
    global24 = 0;
    global31 = 0;
    global29 = 0;
    global45 = 0;
    global50 = 0;
    global22 = 0;
    global51 = 0xffffffff;
    global52 = 0xffffffff;
    global53 = 0xffffffff;
    global54 = 0xffffffff;
    global55 = 0xffffffff;
    global33 = 0;
    global28 = 0;
    global25 = 0;
    global27 = 0;
    global26 = 0;
    global37 = 0;
    global11 = func_79;
    global12 = func_80;
    global14 = func_82;
    global13 = func_81;
    global21 = func_107;
    sys_0(0x7, func_36);
    BattleObject(0x32, 0x2f, 0x10000083, 0x20000078);
}

void func_2242()
{
    global7 = 0x15d;
    func_2240();
    func_2244();
    func_2245();
    func_2246();
    func_2247();
    func_2248();
    func_2241();
    func_2243();
}

void func_2243()
{
    global51 = 0x211;
    global52 = 0x219;
    global53 = 0x231;
    global54 = 0x241;
    global55 = 0x259;
}

void func_2244()
{
    sv_set_mem(0x1, 0, 0x152, func_2249);
    sv_set_mem(0x1, 0x1, 0x152, edge_n_main); // Sephiroth: Flare (was Nayru's Love func_2250)
    sv_set_mem(0x1, 0x2, 0x152, edge_n_none);
    sv_set_mem(0x1, 0, 0x153, func_2261);
    sv_set_mem(0x1, 0x1, 0x153, edge_s_start_main); // Sephiroth: Shadow Flare (was Din's Fire's
    sv_set_mem(0x1, 0x2, 0x153, edge_n_none);       // func_2262 / 2264)
    sv_set_mem(0x1, 0, 0x154, edge_hi_start_pre);   // Sephiroth: up special start (was Farore's Wind's
    sv_set_mem(0x1, 0x1, 0x154, edge_hi_start_main); // func_2277 / 2278 / 2280)
    sv_set_mem(0x1, 0x2, 0x154, edge_hi_end);
    sv_set_mem(0x1, 0, 0x155, edge_lw_pre);         // Sephiroth: Scintilla's stance (was Phantom Slash's
    sv_set_mem(0x1, 0x1, 0x155, edge_lw_main);       // func_2299 / 2300 / 2302)
    sv_set_mem(0x1, 0x2, 0x155, edge_lw_end);
    sv_set_mem(0x1, 0, 0x156, func_2312);
    sv_set_mem(0x1, 0x1, 0x156, func_2313);
    sv_set_mem(0x1, 0x2, 0x156, func_2316);
    sv_set_mem(0x1, 0, 0x157, func_2272);
    sv_set_mem(0x1, 0x1, 0x157, edge_s_hold_main);  // Sephiroth: Shadow Flare's hold (was func_2273 /
    sv_set_mem(0x1, 0x2, 0x157, edge_n_none);       // 2275)
    sv_set_mem(0x1, 0, 0x158, func_2267);
    sv_set_mem(0x1, 0x1, 0x158, edge_s_shot_main);  // Sephiroth: Shadow Flare's shot (was func_2268 /
    sv_set_mem(0x1, 0x2, 0x158, edge_n_none);       // 2270)
    sv_set_mem(0x1, 0, 0x159, edge_hi_rush_pre);    // Sephiroth: Blade Dash / Octaslash (was the warp,
    sv_set_mem(0x1, 0x1, 0x159, edge_hi_rush_main); // func_2282 / 2283 / 2286)
    sv_set_mem(0x1, 0x2, 0x159, edge_hi_end);
    sv_set_mem(0x1, 0, 0x15a, edge_hi_end_pre);     // Sephiroth: the up special's ground / air end (was
    sv_set_mem(0x1, 0x1, 0x15a, edge_hi_end_main);  // Farore's Wind's end, func_2287 / 2288 / 2290)
    sv_set_mem(0x1, 0x2, 0x15a, edge_hi_end);
    sv_set_mem(0x1, 0, 0x15b, func_2303);            // Sephiroth: Scintilla's slash (Ultimate's
    sv_set_mem(0x1, 0x1, 0x15b, edge_lw_hit_main);   // SPECIAL_LW_HIT; Zelda's pre kept: kinetic and work
    sv_set_mem(0x1, 0x2, 0x15b, edge_lw_end);        // kept, as Ultimate's KEEP_ALL) (was func_2304 / 2307)
    sv_set_mem(0x1, 0, 0x15c, func_2308);            // Sephiroth: the shield broken (SPECIAL_LW_END; was
    sv_set_mem(0x1, 0x1, 0x15c, edge_lw_break_main); // func_2309 / 2311)
    sv_set_mem(0x1, 0x2, 0x15c, edge_lw_end);
}

void func_2245()
{
    sv_set_mem(0x1, 0x3, 0x152, edge_n_none);
    sv_set_mem(0x1, 0x3, 0x153, edge_n_none);       // Shadow Flare: set up in its main (was func_2266)
    sv_set_mem(0x1, 0x3, 0x154, edge_n_none);       // Sephiroth's up special: set up in its mains
    sv_set_mem(0x1, 0x3, 0x159, edge_n_none);
    sv_set_mem(0x1, 0x3, 0x15a, edge_n_none);       // (was func_2291)
}

void func_2246()
{
    sv_set_mem(0x1, 0x4, 0x152, edge_n_none);
    sv_set_mem(0x1, 0x4, 0x154, edge_hi_exec);      // Sephiroth's up special: Ultimate's exec (status
    sv_set_mem(0x1, 0x4, 0x159, edge_hi_exec);      // condition 44)
    sv_set_mem(0x1, 0x4, 0x15a, edge_hi_exec);      // (was func_2293)
}

void func_2247()
{
    sv_set_mem(0x1, 0x5, 0x152, func_2259);
    sv_set_mem(0x1, 0x5, 0x154, edge_hi_exec_stop); // ... and exec_stop (48): the pitch in hitlag
    sv_set_mem(0x1, 0x5, 0x159, edge_hi_exec_stop);
    sv_set_mem(0x1, 0x5, 0x15a, edge_hi_exec_stop); // (was func_2296)
}

void func_2248()
{
    sv_set_mem(0x1, 0x6, 0x152, func_2260);
    sv_set_mem(0x1, 0x6, 0x15a, edge_n_none);       // (was func_2297)
}

int func_2249()
{
    func_69();
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1192, 0x1000, 0x80, 0x1000);
    return 0;
}

void func_2250()
{
    WorkModule(0x7, WorkModule(0x6, 0x15000000), 0x11000002);
    if (!StopModule(0x1))
    {
        func_2252();
    }
    global16 = func_2252;
    func_78(func_2251);
}

void func_2251()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return 0x1;
    }
    if (StatusModule(0x6) == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        if (global18 == 0)
        {
            GroundModule(0x2710, 0x9);
            KineticModule(0, 0x6);
            if (WorkModule(0x10, 0x2100000d))
            {
                func_23(0x211);
            }
            else
            {
                func_22(0x211, 0, 1.0f);
                WorkModule(0x2710, 0x2100000d);
            }
        }
        else
        {
            GroundModule(0x2710, 0x5);
            KineticModule(0, 0x64);
            if (WorkModule(0x10, 0x2100000d))
            {
                func_23(0x215);
            }
            else
            {
                func_22(0x215, 0, 1.0f);
                WorkModule(0x2710, 0x2100000d);
            }
        }
    }
    if (MotionModule(0x2712) == 0x1)
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return;
        }
        else if (global18 == 0x2)
        {
            func_16(0xe, 0);
            return;
        }
    }
}

void func_2252()
{
    if (global18 != 0)
    {
        WorkModule(0xa, 0x11000002);
        if (WorkModule(0x6, 0x11000002) <= 0)
        {
            KineticModule(0xb, 0x1);
        }
        else
        {
            KineticModule(0xc, 0x1);
        }
    }
}

void func_2253()
{
    
}

void func_2254()
{
    float var0;
    float var1;
    if (global18 != 0)
    {
        var0 = WorkModuleF(0, 0x5000001);
        var1 = KineticModuleF(0, 0xffffffff);
        KineticModule(0x3);
        KineticModule(0x11, 0x3, var1 / var0, 0);
        KineticModule(0xb, 0x3);
    }
}

int func_2255()
{
    if (global3 == 0)
    {
        if (func_2257() != 0)
        {
            return 0x1;
        }
    }
    if (func_2258() != 0)
    {
        return 0x1;
    }
    return 0;
}

void func_2256()
{
    int var0;
    var0 = 0;
    if (WorkModule(0x10, 0x2100000e))
    {
        ShieldModule(0, 0x3, var0, 0x1, 0x3);
        WorkModule(0x2711, 0x2100000e);
    }
    if (WorkModule(0x10, 0x2100000f))
    {
        ShieldModule(0, 0x3, var0, 0, 0x3);
        WorkModule(0x2711, 0x2100000f);
    }
}

int func_2257()
{
    return 0;
}

int func_2258()
{
    return 0;
}

void func_2259()
{
    
}

void func_2260()
{
    ShieldModule(0, 0x3, 0, 0x1, 0x3);
}

int func_2261()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x11412, 0x1000, 0x200, 0x1000);
    return 0;
}

void func_2262()
{
    WorkModule(0x7, WorkModule(0x6, 0x16000001), 0x11000003);
    WorkModule(0x7, WorkModule(0x6, 0x16000000), 0x11000004);
    WorkModule(0x2711, 0x2100000d);
    func_33();
    if (!StopModule(0x1))
    {
        func_2265();
    }
    global16 = func_2265;
    func_78(func_2263);
}

void func_2263()
{
    if (StatusModule(0x6) == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        if (global18 == 0)
        {
            KineticModule(0, 0x6);
            GroundModule(0x2710, 0x9);
            if (WorkModule(0x10, 0x2100000d))
            {
                func_23(0x219);
            }
            else
            {
                func_22(0x219, 0, 1.0f);
                WorkModule(0x2710, 0x2100000d);
            }
        }
        else
        {
            KineticModule(0, 0x65);
            GroundModule(0x2710, 0x5);
            if (WorkModule(0x10, 0x2100000d))
            {
                func_23(0x225);
            }
            else
            {
                func_22(0x225, 0, 1.0f);
                WorkModule(0x2710, 0x2100000d);
            }
        }
    }
    if (MotionModule(0x2712))
    {
        func_16(0x157, 0);
        return;
    }
    if (!StatusModule(0x6) && ControlModule(0x2713, 0x1) && WorkModule(0x6, 0x11000004) <= 0 && ArticleModule(0x2717, 0))
    {
        func_16(0x158, 0x1);
        return;
    }
}

void func_2264()
{
    
}

void func_2265()
{
    WorkModule(0xa, 0x11000003);
    if (ArticleModule(0x2717, 0))
    {
        WorkModule(0xa, 0x11000004);
    }
    if (WorkModule(0x6, 0x11000003) >= 0)
    {
        KineticModule(0xc, 0x1);
    }
    else
    {
        KineticModule(0xb, 0x1);
    }
    if (WorkModule(0x10, 0x2100000e))
    {
        ArticleModule(0x2710, 0);
        WorkModule(0x2711, 0x2100000e);
    }
}

void func_2266()
{
    if (global18 != 0)
    {
        KineticModule(0x7, 0x1);
    }
}

int func_2267()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x10412, 0, 0x200, 0);
    return 0;
}

void func_2268()
{
    float var0;
    WorkModule(0x2711, 0x2100000d);
    var0 = WorkModuleF(0, 0x6000005);
    if (var0 != 0)
    {
        WorkModule(0, var0 + 0, 0);
    }
    if (!StopModule(0x1))
    {
        func_2271();
    }
    global16 = func_2271;
    func_78(func_2269);
}

void func_2269()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return 0x1;
    }
    if (StatusModule(0x6) == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        if (global18 == 0)
        {
            KineticModule(0, 0x6);
            GroundModule(0x2710, 0x9);
            if (WorkModule(0x10, 0x2100000d))
            {
                func_23(0x221);
            }
            else
            {
                func_22(0x221, 0, 1.0f);
                WorkModule(0x2710, 0x2100000d);
            }
        }
        else
        {
            KineticModule(0, 0x65);
            GroundModule(0x2710, 0x5);
            if (WorkModule(0x10, 0x2100000d))
            {
                func_23(0x22d);
            }
            else
            {
                func_22(0x22d, 0, 1.0f);
                WorkModule(0x2710, 0x2100000d);
            }
        }
    }
    if (MotionModule(0x2712) == 0x1)
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return;
        }
        if (global18 == 0x2)
        {
            if (WorkModuleF(0, 0x6000005) == 0)
            {
                func_16(0xe, 0);
                return;
            }
            else
            {
                func_16(0x10, 0);
                return;
            }
        }
    }
}

void func_2270()
{
    
}

void func_2271()
{
    if (WorkModule(0x10, 0x2100000f))
    {
        if (ArticleModule(0x2717, 0))
        {
            ArticleModule(0x2713, 0, 0x1);
        }
        WorkModule(0x2711, 0x2100000f);
    }
    if (global18 != 0)
    {
        WorkModule(0xa, 0x11000003);
        if (WorkModule(0x6, 0x11000003) >= 0)
        {
            KineticModule(0xc, 0x1);
        }
        else
        {
            KineticModule(0xb, 0x1);
        }
    }
}

int func_2272()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x10412, 0, 0x200, 0);
    return 0;
}

void func_2273()
{
    WorkModule(0x2711, 0x2100000d);
    if (!StopModule(0x1))
    {
        func_2276();
    }
    global16 = func_2276;
    func_78(func_2274);
}

void func_2274()
{
    if (StatusModule(0x6) == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        if (global18 == 0)
        {
            KineticModule(0, 0x6);
            GroundModule(0x2710, 0x9);
            if (WorkModule(0x10, 0x2100000d))
            {
                func_23(0x21d);
            }
            else
            {
                func_22(0x21d, 0, 1.0f);
                WorkModule(0x2710, 0x2100000d);
            }
        }
        else
        {
            KineticModule(0, 0x65);
            GroundModule(0x2710, 0x5);
            if (WorkModule(0x10, 0x2100000d))
            {
                func_23(0x229);
            }
            else
            {
                func_22(0x229, 0, 1.0f);
                WorkModule(0x2710, 0x2100000d);
            }
        }
    }
    if (WorkModule(0x6, 0x11000004) <= 0)
    {
        if (ControlModule(0x2713, 0x1))
        {
            func_16(0x158, 0x1);
        }
        else if (ArticleModule(0x2717, 0) == 0)
        {
            func_16(0x158, 0);
        }
        return 0x1;
    }
}

void func_2275()
{
    
}

void func_2276()
{
    WorkModule(0xa, 0x11000004);
    if (global18 != 0)
    {
        WorkModule(0xa, 0x11000003);
        if (WorkModule(0x6, 0x11000003) >= 0)
        {
            KineticModule(0xc, 0x1);
        }
        else
        {
            KineticModule(0xb, 0x1);
        }
    }
}

int func_2277()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1422, 0, 0x100, 0x1000);
    return 0;
}

void func_2278()
{
    func_78(func_2279);
}

void func_2279()
{
    int var0;
    if (func_56())
    {
        return 0x1;
    }
    var0 = StatusModule(0x6);
    if (var0 == 0 && MotionModule(0x2712))
    {
        func_16(0x159, 0);
        return;
    }
    if (var0 == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        if (global18 == 0)
        {
            GroundModule(0x2710, 0x1);
            KineticModule(0, 0x6);
            if (WorkModule(0x10, 0x2100000d))
            {
                func_23(0x231);
            }
            else
            {
                func_22(0x231, 0, 1.0f);
                WorkModule(0x2710, 0x2100000d);
            }
        }
        else
        {
            GroundModule(0x2710, 0x5);
            KineticModule(0, 0x66);
            if (WorkModule(0x10, 0x2100000d))
            {
                func_23(0x239);
            }
            else
            {
                func_22(0x239, 0, 1.0f);
                WorkModule(0x2710, 0x2100000d);
            }
        }
    }
}

void func_2280()
{
    WorkModule(0x7, GroundModule(0x18), 0x11000004);
}

void func_2281()
{
    float var0;
    float var1;
    if (global18 == 0)
    {
        KineticModule(0x3);
    }
    else
    {
        var0 = KineticModuleF(0, 0xffffffff);
        var1 = KineticModuleF(0x1, 0xffffffff);
        var0 = var0 / WorkModuleF(0, 0x7000000);
        var1 = var1 / WorkModuleF(0, 0x7000001);
        KineticModule(0x3);
        KineticModule(0x11, 0x3, var0, 0);
        KineticModule(0xb, 0x3);
        KineticModule(0x11, 0x1, var1);
        KineticModule(0xb, 0x1);
    }
}

int func_2282()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0x2);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x422, 0x10040000, 0x100, 0);
    return 0;
}

void func_2283()
{
    int var0;
    HitModule(0x2710, 0x2);
    VisibilityModule(0x2710, 0);
    BattleObject(0xa, 0);
    BattleObject(0xc, 0);
    var0 = 0;
    var0 = !var0;
    GroundModule(0x2713, var0);
    func_100(WorkModule(0x6, 0x11000004));
    WorkModule(0x7, 0, 0x11000002);
    if (!StopModule(0x1))
    {
        func_2285();
    }
    global16 = func_2285;
    func_78(func_2284);
}

void func_2284()
{
    if (func_56())
    {
        return 0x1;
    }
    if (WorkModule(0x6, 0x11000002) >= WorkModule(0x6, 0x17000004))
    {
        func_16(0x15a, 0);
        return;
    }
    if (StatusModule(0x6) == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
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

void func_2285()
{
    int var0;
    int var1;
    WorkModule(0x9, 0x11000002);
    var0 = WorkModule(0x6, 0x11000002);
    if (var0 == WorkModule(0x6, 0x17000005))
    {
        var1 = 0x1;
        var1 = !var1;
        GroundModule(0x2713, var1);
    }
    if (var0 == WorkModule(0x6, 0x17000006))
    {
        func_100(0x2);
    }
}

void func_2286()
{
    
}

int func_2287()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x422, 0, 0x100, 0);
    return 0;
}

void func_2288()
{
    if (global18 == 0)
    {
        GroundModule(0x2710, 0x1);
        func_22(0x235, 0, 1.0f);
        WorkModule(0x7, 0, 0x11000003);
    }
    else
    {
        GroundModule(0x2710, 0x5);
        func_22(0x23d, 0, 1.0f);
        WorkModule(0, WorkModuleF(0, 0x700000d) + 0, 0);
        WorkModule(0, WorkModuleF(0, 0x700000c) + 0, 0x1);
        WorkModule(0x7, 0x2, 0x11000003);
    }
    func_78(func_2289);
}

void func_2289()
{
    if (func_56())
    {
        return 0x1;
    }
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return 0x1;
    }
    if (WorkModule(0x6, 0x11000003) == 0)
    {
        if (global18 == 0x2)
        {
            func_16(0xe, 0);
            return;
        }
        if (MotionModule(0x2712) == 0x1)
        {
            func_16(0, 0);
            return;
        }
    }
    else
    {
        if (MotionModule(0x2712) == 0x1)
        {
            func_16(0x10, 0);
            return;
        }
        if (global18 == 0)
        {
            func_16(0x19, 0);
            return;
        }
    }
    func_2292();
}

void func_2290()
{
    VisibilityModule(0x2710, 0x1);
}

void func_2291()
{
    float var0;
    float var1;
    float var2;
    var0 = WorkModuleF(0, 0x700000b);
    var1 = KineticModuleF(0, 0xffffffff);
    var2 = KineticModuleF(0x1, 0xffffffff);
    KineticModule(0x3);
    if (global18 == 0)
    {
        KineticModule(0, 0x6);
        KineticModule(0x11, 0x3, var1 * var0, 0);
        KineticModule(0xb, 0x3);
    }
    else
    {
        KineticModule(0, 0xb);
        KineticModule(0x11, 0x3, var1 * var0, var2 * var0);
        KineticModule(0x14, 0x3, KineticModuleF(0x6, 0x3), -1.0f);
        KineticModule(0xb, 0x3);
        KineticModule(0xc, 0x1);
    }
    VisibilityModule(0x2710, 0x1);
}

int func_2292()
{
    if (global3 == 0)
    {
        if (func_2294() != 0)
        {
            return 0x1;
        }
    }
    if (func_2295() != 0)
    {
        return 0x1;
    }
    return 0;
}

void func_2293()
{
    
}

int func_2294()
{
    float var0;
    float var1;
    float var2;
    if (global18 != 0)
    {
        if (WorkModule(0x10, 0x2100000e))
        {
            var0 = KineticModuleF(0, 0x1);
            var1 = KineticModuleF(0x1, 0x1);
            KineticModule(0x11, 0x1, var1);
            KineticModule(0xb, 0x1);
            var2 = WorkModuleF(0, 0x3000016) * WorkModuleF(0, 0x700000a);
            if (var0 < -var2)
            {
                var0 = -var2;
            }
            else if (var0 > var2)
            {
                var0 = var2;
            }
            var1 = 0;
            KineticModule(0x11, 0x3, var0, var1);
        }
        else
        {
            var0 = KineticModuleF(0xa, 0x3);
            var1 = KineticModuleF(0xb, 0x3);
            var1 = var1 - var1 / 10.0f;
            KineticModule(0x11, 0x3, var0, var1);
        }
    }
    return 0;
}

int func_2295()
{
    return 0;
}

void func_2296()
{
    
}

void func_2297()
{
    
}

int func_2298(int arg0, int arg1, int arg2, int arg3, int arg4)
{
    int var5;
    int var6;
    int var7;
    if (arg0 == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        if (global18 == 0)
        {
            func_20(0);
            GroundModule(0x2710, 0x9);
            KineticModule(0, arg3);
            var5 = arg1;
            var6 = arg2;
        }
        else
        {
            func_20(0x2);
            GroundModule(0x2710, 0x5);
            KineticModule(0, arg4);
            var5 = arg2;
            var6 = arg1;
        }
        var7 = MotionModule(0x7) - WorkModule(0x6, 0x1000004b);
        if (var7 != var5)
        {
            if (var7 == var6)
            {
                func_23(var5);
            }
            else
            {
                func_22(var5, 0, 1.0f);
            }
        }
        return 0x1;
    }
    return 0;
}

int func_2299()
{
    StatusModule(0x5, 0xffffffff, 0xffffffff, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1432, 0x1000, 0x400, 0x1000);
    return 0;
}

void func_2300()
{
    if (ArticleModule(0x2717, 0x2))
    {
        WorkModule(0x2710, 0x2100000f);
    }
    else
    {
        ArticleModule(0x2710, 0x2);
    }
    WorkModule(0x2711, 0x2100000e);
    func_78(func_2301);
}

void func_2301()
{
    int var0;
    int var1;
    var0 = StatusModule(0x6);
    if (var0 == 0)
    {
        if (ControlModule(0x2713, 0x1))
        {
            WorkModule(0x2710, 0x2100000e);
        }
        if (MotionModule(0x2712))
        {
            if (WorkModule(0x10, 0x2100000f))
            {
                var1 = 0x15c;
            }
            else
            {
                var1 = 0x15b;
            }
            func_16(var1, 0);
            return 0x1;
        }
    }
    func_2298(var0, 0x241, 0x245, 0x6, 0xa);
}

void func_2302()
{
    if (WorkModule(0x10, 0x2100000f) == 0)
    {
        if (global6 == 0x15b)
        {
            ArticleModule(0x2714, 0x2, 0x1);
        }
        else
        {
            ArticleModule(0x2714, 0x2, 0x4);
        }
    }
}

int func_2303()
{
    StatusModule(0x5, 0xffffffff, 0xffffffff, 0x7, 0, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x432, 0, 0x400, 0);
    return 0;
}

void func_2304()
{
    WorkModule(0x7, 0, 0x11000002);
    if (!StopModule(0x1))
    {
        func_2306();
    }
    global16 = func_2306;
    func_78(func_2305);
}

void func_2305()
{
    float var0;
    int var1;
    int var2;
    if (ControlModule(0x2713, 0x1) || WorkModule(0x10, 0x2100000e))
    {
        func_16(0x15c, 0x1);
        return 0x1;
    }
    var0 = WorkModuleF(0, 0x8000000);
    var1 = (int)(var0 * 7.0f);
    var2 = WorkModule(0x6, 0x11000002);
    if (var2 >= var1)
    {
        if (WorkModule(0x10, 0x21000010) == 0)
        {
            ArticleModule(0x2715, 0x2, 0x8 + WorkModule(0x6, 0x1000004b));
            WorkModule(0x2710, 0x21000010);
        }
        if (var2 >= WorkModule(0x6, 0x18000001) + var1)
        {
            func_16(0x15c, 0x1);
            return 0x1;
        }
    }
    func_2298(StatusModule(0x6), 0x249, 0x24d, 0x6, 0xa);
}

void func_2306()
{
    WorkModule(0x9, 0x11000002);
}

void func_2307()
{
    float var0;
    float var1;
    int var2;
    if (global6 == 0x15c)
    {
        var0 = (float)WorkModule(0x6, 0x11000002);
        var1 = var0 / WorkModuleF(0, 0x8000000);
        if (var1 > 7.0f)
        {
            var1 = 7.0f;
        }
        var2 = (int)var1;
        var1 = (float)var2;
        WorkModule(0, var1 + 0, 0x1000006);
        ArticleModule(0x271a, 0x2);
        BattleObject(0x55, 0x1, 0x1c);
    }
    else
    {
        ArticleModule(0x2714, 0x2, 0x4);
    }
    PhysicsModule(0x8);
}

int func_2308()
{
    StatusModule(0x5, 0xffffffff, 0xffffffff, 0x7, 0, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x432, 0, 0x400, 0);
    return 0;
}

void func_2309()
{
    func_78(func_2310);
}

void func_2310()
{
    int var0;
    int var1;
    var0 = StatusModule(0x6);
    if (var0 == 0)
    {
        if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
        {
            return 0x1;
        }
        if (MotionModule(0x2712))
        {
            if (global18 == 0)
            {
                var1 = 0;
            }
            else
            {
                var1 = 0xe;
            }
            func_16(var1, 0);
            return 0x1;
        }
    }
    if (func_2298(var0, 0x251, 0x255, 0x6, 0xa))
    {
        if (global18 == 0x2 && var0)
        {
            KineticModule(0x11, 0x1, WorkModuleF(0, 0x8000002));
        }
    }
}

void func_2311()
{
    
}

int func_2312()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0, 0x10000, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1442, 0x1003e2, 0, 0);
    return 0;
}

void func_2313()
{
    BattleObject(0x25);
    KineticModule(0, 0x33);
    ArticleModule(0x2710, 0x3);
    WorkModule(0x2711, 0x2100000d);
    BattleObject(0x88, 0);
    func_2315();
    func_78(func_2314);
}

void func_2314()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
            return;
        }
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0x2)
        {
            func_16(0xe, 0);
            return;
        }
    }
    if (StatusModule(0x6) == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        func_2315();
    }
}

void func_2315()
{
    if (global18 == 0)
    {
        GroundModule(0x2710, 0x1);
        if (WorkModule(0x10, 0x2100000d))
        {
            func_23(0x259);
            ArticleModule(0x2715, 0x3, 0, 0x1);
        }
        else
        {
            func_22(0x259, 0, 1.0f);
            ArticleModule(0x2715, 0x3, 0, 0);
        }
    }
    else
    {
        GroundModule(0x2710, 0x5);
        if (WorkModule(0x10, 0x2100000d))
        {
            func_23(0x25a);
            ArticleModule(0x2715, 0x3, 0x1, 0x1);
        }
        else
        {
            func_22(0x25a, 0, 1.0f);
            ArticleModule(0x2715, 0x3, 0x1, 0);
        }
    }
    WorkModule(0x2710, 0x2100000d);
}

void func_2316()
{
    ArticleModule(0x2711, 0x3);
    if (ArticleModule(0x2717, 0x4))
    {
        ArticleModule(0x2712, 0x4);
    }
    BattleObject(0x26);
    BattleObject(0x88, 0x1);
    if (WorkModule(0x10, 0x21000010))
    {
        func_111();
    }
}

// ===================================================================
// Universal mechanics (docs/universal-mechanics.md), added by tools/universal_mechanics.py; the same
// code as Captain Falcon's / Kirby's / Luigi's / Sonic's.
// Roll-off: the rolls' ACMD gives them their speed (EscapeF +S / EscapeB -S added at frame
// rolloff_start_frame(), 0 at frame 27); kinetic 0x6 so the animation doesn't move the fighter.
// Every roll frame: before the speed frame, or while shield is held (ControlModule(0x2712, 3)),
// ground correction 0x2 (stops at edges); from the speed frame on, 0x1 (can slide off). Sliding off
// goes to Fall, which keeps the roll's speed: the roll end sets flag 0x20000044 (no max air speed)
// when the next status is Fall, and Fall's end clears it. rolloff_fall_speed() scales the carried
// speed once. Lock: global62 counts the frames in a row shield has been held this roll; at
// rolloff_lock_frames() (10) the roll can't slide off for the rest of it. global63: slid off.
// global64: the roll-off took the air speed cap off (Fall's end puts it back).
// ===================================================================
float rolloff_start_frame() { return 5.0f; } // = the ACMD's speed frame
float rolloff_clear_frames() { return 3.0f; } // the carried speed is cleared on the roll's frames before this
int   rolloff_lock_frames()  { return 10; }   // shield held this many frames in a row: no roll-off for the rest of the roll
float rolloff_air_speed_mult() { return 1.0f; } // speed carried off a ledge x this (1.0 = unchanged)

void rolloff_fall_speed()
{
    float x;
    float y;
    if (global63 != 0)
    {
        global63 = 0;
        if (rolloff_air_speed_mult() != 1.0f)
        {
            x = KineticModuleF(0xa, 0x3);
            y = KineticModuleF(0xb, 0x3);
            KineticModule(0x11, 0x3, x * rolloff_air_speed_mult(), y);
        }
    }
}

void rolloff_update()
{
    if (MotionModuleF(0x1) < 1.0f)
    {
        global62 = 0; // new roll
    }
    if (MotionModuleF(0x1) < rolloff_clear_frames()) // no speed carried into the roll (it comes in when the roll
    {                                                // starts; the ACMD's clear didn't reach it), well before the
        KineticModule(0x11, 0x3, 0, 0);              // ACMD adds the roll's speed (user)
        KineticModule(0x11, 0x2, 0, KineticModuleF(0xb, 0x2)); // and a dash's slide, energy 2 (user: a back roll
    }                                                          // out of a dash went almost nowhere)
    if (global62 < rolloff_lock_frames())
    {
        if (ControlModule(0x2712, 0x3))
        {
            global62++;
        }
        else
        {
            global62 = 0;
        }
    }
    if (MotionModuleF(0x1) >= rolloff_start_frame() && !ControlModule(0x2712, 0x3) && global62 < rolloff_lock_frames())
    {
        GroundModule(0x2710, 0x1);
    }
    else
    {
        GroundModule(0x2710, 0x2);
    }
}

// ===================================================================
// Tilts / down smash out of run, the dash and the turns (universal mechanic): when attack is
// pressed, stick Y <= -run_tilt_y() (0.5): down smash if flicked down in the last run_smash_flick()
// (4) frames or the down smash command is set, else down tilt; stick Y >= run_tilt_y(): up tilt.
// Shield out of run is the game's own (Run main turns the Shield group on).
// ===================================================================
float run_tilt_y()      { return 0.5f; }
int   run_smash_flick() { return 4; }

int run_attack_update()
{
    if (!(global38 & 0x1)) // attack pressed this frame
    {
        return 0;
    }
    if (global24 & 0x20) // up smash: the loops' own check
    {
        return 0;
    }
    if (global24 & 0x40 || global32 <= -run_tilt_y() && global47 < run_smash_flick())
    {
        func_16(0x2e, 0x1); // AttackLw4Start
        return 0x1;
    }
    if (global32 <= -run_tilt_y())
    {
        func_16(0x2a, 0x1); // AttackLw3
        return 0x1;
    }
    if (global32 >= run_tilt_y())
    {
        func_16(0x29, 0x1); // AttackHi3
        return 0x1;
    }
    return 0;
}

// Turn (0x6) / TurnDash (0x7) loops: tilts / down smash when the turn came out of a Dash (0x3).
int dash_turn_attack_update()
{
    if (global5 != 0x3 || global18 != 0)
    {
        return 0;
    }
    return run_attack_update();
}

// ---- Sephiroth's neutral special: Flare / Megaflare / Gigaflare (status 0x152, Zelda's Nayru's Love;
// fighters/edge/specials.md). Ultimate's SpecialNStart charges (charge kind S from frame 20, M from 32,
// L from 100: its game script's set_int frames) and fires Gigaflare itself at frame 120; released
// before 100 (and from frame 20, cancel_start_frame) it goes to SpecialN1 (Flare, level S) or
// SpecialN2 (Megaflare, level M), which fire at frame 13; shield while charging -> SpecialNCancel.
// The fire article (article 5, weapon kind 0x18C, fighters/edge/weapons/fire.c) learns its level
// through Zelda's side special's custom slot (int 0x10000049: Din's Fire's creation callback 0x02F97C90
// copies it into the new weapon's 0x10000005; the neutral one, 0x10000048, isn't read: every charge
// fired a Flare), set while it is generated. Motions straight through MotionModule (not
// func_22 / func_23: they add Zelda's custom-move offset, global21). In the air (param_special_n):
// the fall slowed while charging (gravity x start_accel_y_mul_air 0.7, max fall x
// start_max_speed_y_mul_air 0.55) until the fire motion's ENABLE_FALL_SPEED frame (NStart 140, N1 35,
// N2 33).
int edge_n_state;
int edge_n_level;
int edge_n_fired;
int edge_n_released;

int edge_n_motion(int ground)
{
    if (global18 == 0x2)
    {
        return ground + 0x4;
    }
    return ground;
}

int edge_n_ground_motion()
{
    if (edge_n_state == 0x1)
    {
        if (edge_n_level == 0x1)
        {
            return 0x213;   // SpecialN2
        }
        return 0x211;       // SpecialN1
    }
    if (edge_n_state == 0x2)
    {
        return 0x214;       // SpecialNCancel
    }
    return 0x212;           // SpecialNStart
}

void edge_n_kinetic()
{
    if (global18 == 0x2)
    {
        GroundModule(0x2710, 0x5);
        KineticModule(0, 0x64);
    }
    else
    {
        GroundModule(0x2710, 0x9);
        KineticModule(0, 0x6);
    }
}

// the charge's slowed fall (energy 1: gravity), until the motion's fall frame
void edge_n_air()
{
    float f;
    if (global18 != 0x2)
    {
        return;
    }
    f = MotionModuleF(0x1);
    if (edge_n_state == 0 && f < 140.0f || edge_n_state == 0x1 && f < 33.0f)
    {
        KineticModule(0xf, 0x1, -0.0756f);
        KineticModule(0x14, 0x1, 1.012f);
    }
}

void edge_n_generate()
{
    int slot;
    slot = WorkModule(0x6, 0x10000049);
    WorkModule(0x7, edge_n_level, 0x10000049);
    ArticleModule(0x2710, 0x5);
    WorkModule(0x7, slot, 0x10000049);
    edge_n_fired = 0x1;
}

// the charge's effects (SpecialNStart's EFFECT_FOLLOWs on haver / the body, endless) end with the
// charge: Ultimate's SpecialN1 / N2 / NCancel scripts never turn them off, its status does (test 59:
// "the refraction effect never goes away when released"). Ids: edge_effects.json (the plain sets and
// their turned (90, 0, 90) variants); off as its EFFECT_OFF_KIND(false, true): emission stops, the
// particles play out
void edge_n_charge_off()
{
    EffectModule(0x2723, 0x3420055, 0, 0x1); // edge_fire1_hold
    EffectModule(0x2723, 0x3420056, 0, 0x1); // edge_fire2_hold
    EffectModule(0x2723, 0x3420057, 0, 0x1); // edge_fire2_hold_aura
    EffectModule(0x2723, 0x3420059, 0, 0x1); // edge_fire2_hold_flash
    EffectModule(0x2723, 0x342005A, 0, 0x1); // edge_fire3_hold_flash
    EffectModule(0x2723, 0x34200A7, 0, 0x1); // edge_fire1_hold@90,0,90
    EffectModule(0x2723, 0x34200A8, 0, 0x1); // edge_fire2_hold@90,0,90
    EffectModule(0x2723, 0x34200A9, 0, 0x1); // edge_fire2_hold_flash@90,0,90
    EffectModule(0x2723, 0x34200AA, 0, 0x1); // edge_fire3_hold_flash@90,0,90
}

void edge_n_change(int state)
{
    edge_n_charge_off();
    edge_n_state = state;
    MotionModule(0x1, edge_n_motion(edge_n_ground_motion()), 0, 1.0f);
    global20 = 0;
}

void edge_n_loop()
{
    float f;
    if (StatusModule(0x6) == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        edge_n_kinetic();
        MotionModule(0x3, edge_n_motion(edge_n_ground_motion()));
    }
    f = MotionModuleF(0x1);
    if (edge_n_state == 0)
    {
        if (f >= 100.0f)
        {
            edge_n_level = 0x2;
        }
        else if (f >= 32.0f)
        {
            edge_n_level = 0x1;
        }
        if (ControlModule(0x2712, 0x1) == 0)
        {
            edge_n_released = 0x1;
        }
        // the charge cancelled into a roll on the ground (test 143, the user: "make Neutral special's charging
        // cancelable into roll"): the roll inputs as the shield's own check reads them (func_48: global24 0x2000000
        // forward, 0x4000000 back), in the window the shield cancel has (frames 20 - 99), before it (a roll's input
        // holds shield too)
        if (f >= 20.0f && f < 100.0f && global18 == 0 && (global24 & 0x2000000) != 0)
        {
            edge_n_charge_off();
            func_16(0x20, 0x1);
            return;
        }
        if (f >= 20.0f && f < 100.0f && global18 == 0 && (global24 & 0x4000000) != 0)
        {
            edge_n_charge_off();
            func_16(0x21, 0x1);
            return;
        }
        if (f >= 20.0f && f < 100.0f && ControlModule(0x2710, 0x3))
        {
            edge_n_change(0x2);
        }
        else if (f >= 20.0f && f < 100.0f && edge_n_released)
        {
            edge_n_change(0x1);
        }
        else if (f >= 120.0f && edge_n_fired == 0)
        {
            edge_n_generate();
        }
    }
    else if (edge_n_state == 0x1)
    {
        if (f >= 13.0f && edge_n_fired == 0)
        {
            edge_n_generate();
        }
    }
    edge_n_air();
    // actionable from the motion's cancel frame (vl group 1: Ultimate's, Flare 56, Megaflare 70,
    // Gigaflare 172, cancel 8), as Zelda's own statuses (func_39: ground, func_41: air)
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (MotionModule(0x2712) == 0x1)
    {
        if (global18 == 0)
        {
            func_16(0, 0);
        }
        else
        {
            func_16(0xe, 0);
        }
    }
}

void edge_n_main()
{
    edge_n_state = 0;
    edge_n_level = 0;
    edge_n_fired = 0;
    edge_n_released = 0;
    edge_n_kinetic();
    if (global18 == 0x2)
    {
        KineticModule(0x11, 0x1, 0);
    }
    MotionModule(0x1, edge_n_motion(0x212), 0, 1.0f);
    global20 = 0;
    func_78(edge_n_loop);
}

void edge_n_none()
{
    
}

// ---- Sephiroth's up special: Blade Dash / Octaslash (fighters/edge/specials.md "Up special"), Ultimate's
// status code (lua2cpp_edge.nro, the spec's function addresses f_7203e<addr>) in Zelda's three up-special
// statuses (Smash 4 has no free status numbers: Zelda's table ends at 0x15C, global7 = 0x15D):
//   0x154 START (Ultimate's FIGHTER_STATUS_KIND_SPECIAL_HI: 09a70 / 17e40 / 19910, exec 03650)
//   0x159 RUSH, Blade Dash and Octaslash in one (0xe2a4 / 0xe2a8: 0a500 / 175b0, 0acc0 / 15c90), the
//         charge flag picking the params as Ultimate's P[c] does
//   0x15A END, the ground end and the air end in one (0xe2ac: 0b360 / 15510; 0xe2b0: 0be60 / 14b30)
// and Octaslash's landing (Ultimate's LANDING_FALL_SPECIAL init hook 03d40) on LandingFallSpecial 0x19's
// init (edge_hi_landing_init). The status work Ultimate keeps across them (KEEP_ALL) is in globals here.
// Params: vl.prc param_special_hi[0] (fighter_param_vl here is Zelda's layout: the values are written in).
// Motions straight through MotionModule (func_22 / func_23 add Zelda's custom-move offset): 0x231 / 0x239
// SpecialHiStart / SpecialAirHiStart, 0x235 SpecialHi1 (both situations: Ultimate has no air rush motion),
// 0x237 SpecialHi2, 0x236 / 0x238 SpecialHi1End / SpecialHi2End, 0x23E / 0x23F SpecialAirHi1End /
// SpecialAirHi2End, 0x232 SpecialHi2Landing (extra_kinds.json "motions").
// Kinetic energies: 1 gravity, 2 control, 3 stop (Ultimate's STOP, energy id 3 in its ExeFS hook too).
int   edge_hi_charged;    // 0xe364 F_CHARGED: Octaslash
int   edge_hi_decided;    // the direction is decided (the start's 17e40 -> 19910 shift)
float edge_hi_dir_x;      // 0xe374 / 0xe378: the aim at the decide frame
float edge_hi_dir_y;
float edge_hi_rx;         // f_16f20's result: the rush direction (ground-adjusted)
float edge_hi_ry;
int   edge_hi_on_ground;
float edge_hi_rot;        // 0xe368 ROT: the body's pitch on joint "rot" (degrees; negative = nose up)
float edge_hi_rot_target; // 0xe37c ROT_TARGET
int   edge_hi_landed;     // 0xe384 LANDED_DURING_RUSH
int   edge_hi_count;      // 0xe388 RUSH_COUNTER
int   edge_hi_end_air;    // END: 0 the ground end (0xe2ac), 1 the air end (0xe2b0)
int   edge_hi_control;    // the air end's control is on (0xe38c ENABLE_CONTROL handled)
int   edge_hi_cliff;      // the ledge-grab mode set last (func_100), -1 none yet
float edge_hi_fx_x;       // the aim effect's place / roll (f_18b30), for edge_hi_direction()
float edge_hi_fx_y;
float edge_hi_fx_roll;
int   edge_hi_fx;         // 0xe370: the aim effect's handle (0 none yet; Ultimate's 4016 = none)

// P[c](name): the plain or the charged_ value
float edge_hi_p(float plain, float charged)
{
    if (edge_hi_charged)
    {
        return charged;
    }
    return plain;
}

// ---- test 113 (the user's up special concept, stage 1): Octaslash steers (360 degrees since test 114) and
// loops its multi-hit (the 2nd hit to the one before the last: SpecialHi2 frames 4 - 15) while the special button is
// held, for edge_hi_loop_frames() or until it is let go, the time starting again on every hit; its hits pull the last
// fighter hit along in front of him (edge_hi_link). Blade Dash (tap) keeps its full aim, lands in 22 frames, and ends
// in a normal fall. Either is usable once per air time: landing or a ledge grab gives it back, being hit doesn't.
// No MSC globals left (port_check C5): the state is this object's VARs (tools/acmd_ext_cave.py)
int   edge_hi_used_var() { return 0x0f000315; }   // VAR_21: 1 once up special was used (cleared on the ground / ledge / respawn)
int   edge_hi_pass_var() { return 0x0f000314; }   // VAR_20 (ACMD): Octaslash's pass: 0 plain, 1 first pass held, 2 a
                                                  // looped pass (SpecialHi2's first hit and start effects skipped)
int   edge_hi_timer_var() { return 0x0f00030c; }  // VAR_12: Octaslash's loop frames left
float edge_hi_loop_frames() { return 100.0f; }    // the set duration (frames), again from each hit (test 126: 100)
float edge_hi_loop_from() { return 4.0f; }        // SpecialHi2: the 2nd hit's frame (Ultimate game_specialhi2)
float edge_hi_loop_to() { return 14.0f; }         // ... the 7th (one before SpecialHi2End's), the motion's last frame:
                                                  // played again the frame after (test 115; test 113 waited for 16,
                                                  // past its end, so it never looped and the pose held)
int   edge_hi_wrap_var() { return 0x0f00030e; }   // VAR_14: 1 once the loop's pass has been on its last frame a frame
float edge_hi_cruise() { return 2.4f; }           // held Octaslash's speed once its brake gets there (test 115, the
                                                  // user: "moves far too fast" at a steady 6.2; test 116: 2.2; test 126: 2.4)
int   edge_hi_total_var() { return 0x0f00030f; }  // VAR_15: frames looped in all (in hitlag too)
float edge_hi_loop_max() { return 180.0f; }       // the loop's most, hits or not (test 116, the user: "Held up special
                                                  // loops indefinitely when an opponent is hit")
float edge_hi_air_cut() { return 15.0f; }         // Blade Dash's air end: Fall here (test 120, the user: 8 frames earlier;
                                                  // test 116: 23, the frame before its animation starts into the fall,
                                                  // d02specialairhi1end: legs / Rot move from 24)
float edge_hi_turn_c() { return 0.990268f; }      // the steering: 8 degrees a frame (cos / sin)
float edge_hi_turn_s() { return 0.139173f; }
float edge_hi_link_d() { return 10.0f; }          // autolink: the fighter hit kept this far along his rush,
float edge_hi_link_h() { return 3.0f; }           // this much higher (feet to feet: his middle less theirs),
float edge_hi_link_k() { return 0.6f; }           // closing this part of the gap a frame,
float edge_hi_link_r() { return 30.0f; }          // when within this

// 1 when up special can start: on the ground, or not yet used this time in the air
int edge_hi_can()
{
    if (global18 == 0 || WorkModuleF(0, edge_hi_used_var()) == 0.0f)
    {
        return 0x1;
    }
    return 0;
}

// func_82 (every frame): landing (on the ground outside up special) or a ledge grab (CliffCatchMove / CliffCatch /
// CliffWait 0x72 - 0x74) gives up special back
void edge_hi_air_tick()
{
    // on the ground, the ledge, or dead / respawning (0xB1 Dead, 0xB2 Rebirth: test 127, "make up special's air count
    // reset on respawn")
    if (global18 == 0 && global4 != 0x154 && global4 != 0x159 && global4 != 0x15a || global4 >= 0x72 && global4 <= 0x74
        || global4 == 0xb1 || global4 == 0xb2)
    {
        WorkModule(0, 0.0f, edge_hi_used_var());
    }
}

// 1 while Octaslash goes on: the special button held
int edge_hi_held()
{
    if (edge_hi_charged && ControlModule(0x2712, 0x1) && WorkModuleF(0, 0x0f000101) == 1.0f)   // SELF_SPECIAL too
    {
        return 0x1;
    }
    return 0;
}

// a hit of Octaslash's (SELF_HIT_NOW): its time starts again
void edge_hi_hit_check()
{
    if (edge_hi_charged && (float)edge_hi_count >= 15.0f)
    {
        WorkModule(0, WorkModuleF(0, edge_hi_total_var()) + 1.0f, edge_hi_total_var());
    }
    if (edge_hi_charged && WorkModuleF(0, 0x0f0000a1) == 1.0f)
    {
        WorkModule(0, edge_hi_loop_frames(), edge_hi_timer_var());
    }
}

// Octaslash: every fighter in hitstun kept inside the blast zones (test 127, the user: "make opponents hit by it unable
// to be KO'd by the blast zone during the duration of the entire attack, including the ending hit"). Test 128 (the user:
// it "still allows for KOing in the blast zone"): test 127 stopped as he left the end status, while the finisher's
// launch carries them on after it; now a fighter in hitstun while he's in held Octaslash's rush / end is marked (his
// TIMER_0 - 7, one a player slot: 0x0F000320 + slot, counting down a frame at a time) and kept marked while its hitstun
// lasts and 40 frames after (the launch's speed left), kept 20 inside the side / bottom blast zones and 30 under the top
// (StageData 0 - 3) by moving it there (0x0F000020 + 4 x slot: set slot X / Y)
void edge_hi_keep_in()
{
    int slot;
    int on;
    float x;
    float y;
    float lo;
    float hi;
    float t;
    // a shape made (TIMER_13, from its commit to his next up special): no one kept in, so a shape's hit can KO (test
    // 138, the user: "Please allow shapes to KO opponents. Right now, regardless of damage or knockback a shape cannot
    // KO at all": its hit lands in Octaslash's end, where everyone in hitstun was marked and held inside)
    if (WorkModuleF(0, 0x0f00032d) > 0.0f)
    {
        slot = 0;
        while (slot < 0x8)
        {
            WorkModule(0, 0.0f, 0x0f000320 + slot);
            slot = slot + 1;
        }
        return;
    }
    on = 0;
    if (edge_hi_charged && (global4 == 0x159 || global4 == 0x15a))
    {
        on = 0x1;
    }
    slot = 0;
    while (slot < 0x8)
    {
        t = WorkModuleF(0, 0x0f000320 + slot);
        x = WorkModuleF(0, 0x0f000020 + 0x4 * slot);
        y = WorkModuleF(0, 0x0f000021 + 0x4 * slot);
        if (WorkModuleF(0, 0x0f000023 + 0x4 * slot) != 0.0f && (x != PostureModuleF(0x1) || y != PostureModuleF(0x2)))
        {
            if (WorkModuleF(0, 0x0f000058 + 0x8 * slot) > 0.0f && (on || t > 0.0f))
            {
                WorkModule(0, 40.0f, 0x0f000320 + slot);
                t = 40.0f;
            }
            if (t > 0.0f)
            {
                lo = StageData(0) + 20.0f;
                hi = StageData(0x1) - 20.0f;
                if (x < lo)
                {
                    WorkModule(0, lo, 0x0f000020 + 0x4 * slot);
                }
                if (x > hi)
                {
                    WorkModule(0, hi, 0x0f000020 + 0x4 * slot);
                }
                lo = StageData(0x3) + 20.0f;
                hi = StageData(0x2) - 30.0f;
                if (y < lo)
                {
                    WorkModule(0, lo, 0x0f000021 + 0x4 * slot);
                }
                if (y > hi)
                {
                    WorkModule(0, hi, 0x0f000021 + 0x4 * slot);
                }
            }
        }
        else
        {
            WorkModule(0, 0.0f, 0x0f000320 + slot);
        }
        slot = slot + 1;
    }
}

// held Octaslash: the rush direction (edge_hi_rx / ry) turns toward the stick, 8 degrees a frame the shorter way
// round, all the way round (test 114, the user: "allow a full 360 degrees of movement"; test 113 kept it to his
// front); a neutral stick keeps it. He keeps his facing: going back he's pitched past 90 (a loop). On the ground,
// turning more than about 20 degrees up takes him off it
void edge_hi_steer()
{
    float lr;
    float sx;
    float sy;
    float l;
    float cx;
    float cy;
    float cr;
    float sg;
    lr = PostureModuleF(0);
    sx = global48;
    sy = global32;
    l = MathF(0, sx * sx + sy * sy);
    if (l < 0.25f)
    {
        return;
    }
    sx = sx / l;
    sy = sy / l;
    cx = edge_hi_rx;
    cy = edge_hi_ry;
    if (cx * sx + cy * sy >= edge_hi_turn_c())
    {
        edge_hi_rx = sx;
        edge_hi_ry = sy;
    }
    else
    {
        cr = cx * sy - cy * sx;
        sg = 1.0f;
        if (cr < 0.0f)
        {
            sg = -1.0f;
        }
        if (func_13(cr) < 0.0001f)
        {
            // straight back the other way: through his front
            sg = 1.0f;
            if (cy * lr > 0.0f)
            {
                sg = -1.0f;
            }
        }
        edge_hi_rx = cx * edge_hi_turn_c() - cy * edge_hi_turn_s() * sg;
        edge_hi_ry = cx * edge_hi_turn_s() * sg + cy * edge_hi_turn_c();
    }
    if (global18 == 0 && edge_hi_ry > 0.35f)
    {
        func_20(0x2);
        GroundModule(0x2710, 0x5);
    }
}

// Octaslash's autolink: the last fighter hit (still in hitstun, near) pulled to edge_hi_link_d() along his rush
// (LASTHIT_OFFSET_X / _Y, docs/position-variables.md: X along his facing)
void edge_hi_link()
{
    float ox;
    float oy;
    float tx;
    float ty;
    if (WorkModuleF(0, 0x0f0000a0) != 1.0f || WorkModuleF(0, 0x0f000050) <= 0.0f)   // SELF_HIT, LASTHIT_HITSTUN
    {
        return;
    }
    if (edge_hi_charged)
    {
        return;                        // held Octaslash sends them away (test 134: its slashes' fixed knockback), not in
    }
    ox = WorkModuleF(0, 0x0f000055);
    oy = WorkModuleF(0, 0x0f000056);
    if (ox * ox + oy * oy > edge_hi_link_r() * edge_hi_link_r())
    {
        return;
    }
    tx = edge_hi_link_d() * edge_hi_rx * PostureModuleF(0);
    ty = edge_hi_link_h() + edge_hi_link_d() * edge_hi_ry;
    tx = ox + (tx - ox) * edge_hi_link_k();
    ty = oy + (ty - oy) * edge_hi_link_k();
    // the place it's pulled to kept inside the blast zones as edge_hi_keep_in's (test 131, the user: "opponents can still
    // be dragged and KO'd by the top blastzone by Octaslash": the pull, in his status loop, put them past the top after
    // his per-frame hook's clamp, above it with him); the offset is along his facing (X) and up (Y)
    ox = PostureModuleF(0x1) + tx * PostureModuleF(0);
    oy = PostureModuleF(0x2) + ty;
    if (ox < StageData(0) + 20.0f)
    {
        ox = StageData(0) + 20.0f;
    }
    if (ox > StageData(0x1) - 20.0f)
    {
        ox = StageData(0x1) - 20.0f;
    }
    if (oy < StageData(0x3) + 20.0f)
    {
        oy = StageData(0x3) + 20.0f;
    }
    if (oy > StageData(0x2) - 30.0f)
    {
        oy = StageData(0x2) - 30.0f;
    }
    WorkModule(0, (ox - PostureModuleF(0x1)) * PostureModuleF(0), 0x0f000055);
    WorkModule(0, oy - PostureModuleF(0x2), 0x0f000056);
    edge_hi_keep_in();                 // and every one marked, after the pull (it's in his per-frame hook too)
}

// ---- the up special trail (tests 123 - 126, the user's concept stages 2 and 3: "Tap up and hold up special both leave a
// purple line trail that persists for 6 seconds following Sephiroth's movement until he begins falling. When multiple
// lines form a closed shape inside, a purple glow effect that scales with the size of the shape appears 12 frames after,
// fading in and creating a hitbox slightly larger than the shape formed"; test 126: "The lines should go away when
// forming a shape, and the old lines from the last uses of up special should be usable to create shapes. Also please
// make other shapes possible that aren't circles", "I'd like for the formed shape to mirror the lines that the closed
// shape was made of"). His middle's path from the attack's start (the rush) to the air end's first falling frame (or the
// ground end), points edge_tr_seg() apart (one a frame at most), numbered block x 1024 + n (block 1 - 15, a new one each
// trail: edge_tr_block). `trail` articles (weapons/trail.c, tools/edge_trail_msc.py) draw it, each a stretch of 16
// points (15 pieces) from the one before's last, 360 frames. His shared 4 - 6 (VAR_28 - VAR_30: free in up special;
// Shadow Flare's orbs use 0 - 3, the Phantom 7, the snake runs 0 - 6 only while the sword's out): 5 the newest point
// (packed, edge_tr_pack), 6 its number (-1 once the trail's over), 4 a crossing reported by an article (-m, m the piece
// crossed). A shape: the trail crossing an earlier piece of itself (a loop: its points m + 1 .. newest - 1), or an old
// trail twice (its own points between the two crossings and the old trail's between the pieces it crossed). Then, a
// step a frame with the trail paused (shared 6 the step): the shape's points marked (one or two ranges), their sums
// (x, y; x^2, y^2; x y) in 5 / 4, and the commit (5 the middle): the articles drop those pieces of line and fill the
// shape from its middle to them; a `fill` article (weapons/fill.c, tools/edge_fill_msc.py) at the middle takes the
// ellipse fitted to the points (its long axis' angle, its half axes from the spread: a = sqrt(2 l1), b = sqrt(2 l2))
// in 4 and is the shape's hitbox. His VAR_0 - VAR_11 (the snake runs', free in up special) keep the steps. The
// protocol is modelled in tools/edge_trail_sim.py. Test 123 made one article per 8-long piece, 40 at most: the game
// crashed loading him (64 article slots a fighter: docs/native-notes.md "Article instance cap")
int   edge_tr_block;                             // the last trail's block (1 - 15; the MSC's last global, 0x86)
int   edge_tr_art() { return 0xb; }              // article 11 (Zelda's 0 - 4, fire, flare1, flare2, flash, snake,
                                                 // snaketip, trail, fill: tools/extra_kinds.json, 24 at most: test 128)
int   edge_tr_fill_art() { return 0xc; }         // article 12, fill (3 at most)
float edge_tr_seg() { return 4.0f; }             // the points' spacing
int   edge_tr_per() { return 15; }               // pieces an article draws
float edge_tr_mid() { return 9.0f; }             // his middle above his feet
int   edge_tr_cross_var() { return 0x0f00031c; } // VAR_28 (shared 4)
int   edge_tr_new_var() { return 0x0f00031d; }   // VAR_29 (shared 5)
int   edge_tr_num_var() { return 0x0f00031e; }   // VAR_30 (shared 6)
int   edge_tr_q_var() { return 0x0f000300; }     // VAR_0: the shape's step, -1 - -5 (0 none; negative: the snake
                                                 // runs' codes in it are never, so his per-frame hook can't take them)
int   edge_tr_floor_var() { return 0x0f000301; } // VAR_1: a loop counts only if it closes on a piece from here (the
                                                 // last shape's end: a second lap round makes its own loop, not two)
int   edge_tr_qn_var() { return 0x0f000302; }    // VAR_2: the shape's points
int   edge_tr_sp_var() { return 0x0f000303; }    // VAR_3: the newest point, kept through the steps
int   edge_tr_sn_var() { return 0x0f000304; }    // VAR_4: its number
int   edge_tr_cool_var() { return 0x0f000305; }  // VAR_5: frames before another shape counts
int   edge_tr_om_var() { return 0x0f000306; }    // VAR_6: an old trail's piece crossed first (0 none)
int   edge_tr_on_var() { return 0x0f000307; }    // VAR_7: the newest point's number then
int   edge_tr_s1_var() { return 0x0f000308; }    // VAR_8 - VAR_11: the sums (VAR_8 the second range's mark before)
int   edge_tr_s2_var() { return 0x0f000309; }
int   edge_tr_s3_var() { return 0x0f00030a; }
int   edge_tr_s4_var() { return 0x0f00030b; }
float edge_tr_sum1() { return -1001.5f; }        // the steps (shared 6; tools/edge_trail_msc.py SUM1 ...)
float edge_tr_sum2() { return -1002.5f; }
float edge_tr_sum3() { return -1003.5f; }
float edge_tr_commit() { return -1004.5f; }
float edge_tr_cancel() { return -1005.5f; }      // a shape not made (test 128: near the blast zones)
float edge_tr_scale() { return 1.3f; }           // the shape's fill and hitbox x this (test 127: 1.2; 1.3 test 132)
// test 148: Shadow Flare's shot as a line while it flies (edge_s_line_tick)
int   edge_tr_shot_var() { return 0x0f00032e; }  // TIMER_14: 9999 while the shot's line (or its shape's steps) runs
int   edge_tr_fresh_var() { return 0x0f00032f; } // TIMER_15: frames its place may go unrefreshed before it's over
int   edge_tr_place_var() { return 0x0f00031b; } // VAR_27 (shared 3): the shot's place, flare1 writes it (-1: stopped)
int   edge_tr_pen_var() { return 0x0f00030c; }   // VAR_12 (Octaslash's loop frames, free then): the place last read,
                                                 // the line's pen; -1 once its line is over (one line a shot)
int   edge_tr_shot_from() { return 0x2fd; }      // its points' numbers: block 15 x 1024 + 765 (51 x 15) on, so the
                                                 // articles know it and draw no line (trail.c tr_hidden)

// 1 while the shot's line (or its shape's steps) runs
int edge_tr_shot()
{
    if (WorkModuleF(0, edge_tr_shot_var()) > 0.0f)
    {
        return 0x1;
    }
    return 0;
}

float edge_tr_pack(float x, float y)
{
    int ix;
    int iy;
    ix = (int)((x + 512.0f) * 2.0f + 0.5f);
    iy = (int)((y + 512.0f) * 2.0f + 0.5f);
    if (ix < 0)
    {
        ix = 0;
    }
    if (ix > 0x7ff)
    {
        ix = 0x7ff;
    }
    if (iy < 0)
    {
        iy = 0;
    }
    if (iy > 0x7ff)
    {
        iy = 0x7ff;
    }
    return (float)(ix * 0x800 + iy);
}

float edge_tr_x(float v)
{
    return (float)((int)v / 0x800) * 0.5f - 512.0f;
}

float edge_tr_y(float v)
{
    int c;
    c = (int)v;
    return (float)(c - (c / 0x800) * 0x800) * 0.5f - 512.0f;
}

// a point: the newest, numbered n; a new stretch's article from every edge_tr_per()-th
void edge_tr_point(float p, int n)
{
    int i;
    WorkModule(0, p, edge_tr_new_var());
    WorkModule(0, (float)n, edge_tr_num_var());
    i = n - (n / 0x400) * 0x400;
    if (i - (i / edge_tr_per()) * edge_tr_per() == 0)
    {
        ArticleModule(0x2710, edge_tr_art());
    }
}

// the trail starts here (the rush's main): a new block (Blade Dash 1 - 14 in turn; held Octaslash 15, its trail not
// staying: test 127, "only make Blade Dash lines persist after use"), its point 0
int edge_tr_cur_block()
{
    if (edge_hi_charged || edge_tr_shot())
    {
        return 0xf;                        // held Octaslash's, or Shadow Flare's shot's (test 148): neither stays
    }
    return edge_tr_block;
}

// the trail's first number: block x 1024 (the shot's: + 765, test 148)
int edge_tr_start_num()
{
    int b;
    b = edge_tr_cur_block();
    if (edge_tr_shot())
    {
        return b * 0x400 + edge_tr_shot_from();
    }
    return b * 0x400;
}

// the trail's state set up for a new one (edge_tr_begin, edge_tr_shot_begin)
void edge_tr_reset()
{
    int i;
    int n;
    WorkModule(0, 0.0f, edge_tr_cross_var());
    i = 0x300;
    while (i <= 0x30b)
    {
        WorkModule(0, 0.0f, 0x0f000000 + i);   // VAR_0 - VAR_11
        i = i + 1;
    }
    n = edge_tr_start_num();
    WorkModule(0, (float)n, edge_tr_floor_var());
    WorkModule(0, 0.0f, 0x0f000328);
    WorkModule(0, 0.0f, 0x0f000329);
    WorkModule(0, 5.0f, 0x0f00032a);
    WorkModule(0, 0.0f, 0x0f00032b);
    WorkModule(0, 0.0f, 0x0f00032c);
    // point 0 up a frame before point 1 can follow it (VAR_10, 2 frames, his per-frame hook counting it down): test 131,
    // point 1 could be written the frame point 0 was (the rush's main and loop), the old lines' articles never saw point
    // 0, so tested no first piece, and a line started where another ended never met it (the user's clip: "this shape
    // should be able to form a triangle")
    WorkModule(0, 2.0f, edge_tr_s3_var());
    WorkModule(0, edge_tr_pack4(PostureModuleF(0x1), PostureModuleF(0x2)), edge_tr_s4_var());
}

void edge_tr_begin()
{
    int b;
    int n;
    float h;
    float p;
    WorkModule(0, 0.0f, edge_tr_shot_var());      // a shot's line still running (its steps) is over (test 148)
    if (edge_hi_charged == 0)
    {
        edge_tr_block = edge_tr_block - (edge_tr_block / 0xe) * 0xe + 1;
    }
    edge_tr_reset();
    WorkModule(0, 0.0f, 0x0f00032d);               // the blast-zone keep-in back (test 138)
    h = edge_tr_h();                       // locals first (test 135: no nested script calls as arguments)
    p = edge_tr_pack(PostureModuleF(0x1), PostureModuleF(0x2) + h);
    b = edge_tr_cur_block();
    n = b * 0x400;
    edge_tr_point(p, n);
}

// Shadow Flare's shot's line starts at its place p (test 148: edge_s_line_tick)
void edge_tr_shot_begin(float p)
{
    int n;
    WorkModule(0, 9999.0f, edge_tr_shot_var());
    edge_tr_reset();
    n = edge_tr_start_num();
    edge_tr_point(p, n);
}

// sin by its series (no sin in MSC; trail.c tr_sin the same), x folded into -pi/2 .. pi/2
float edge_tr_sin(float x)
{
    float x2;
    if (x > 1.5707963f)
    {
        x = 3.1415927f - x;
    }
    if (x < -1.5707963f)
    {
        x = -3.1415927f - x;
    }
    x2 = x * x;
    return x * (1.0f - x2 / 6.0f * (1.0f - x2 / 20.0f * (1.0f - x2 / 42.0f)));
}

// test 128: Blade Dash's line goes on while he still moves the slash's way (the user: "Blade Dash lines should only
// stop being made once Sephiroth stops moving in the direction the slash is in in the animation", "This line should
// reach all the way to Sephiroth's back"): his position last frame in VAR_11 (packed at 0.25: (x + 512) x 4 x 4096 +
// (y + 512) x 4, exact in a float; VAR_11 is the steps' only while VAR_0 < 0), his move since along the slash
// (edge_hi_rx / ry: world space, edge_hi_resolve) under 0.4 a frame for 3 frames running (TIMER_10, 0x0F00032A, set to
// 2 each frame he moves; 5 as the trail starts) = stopped (test 131: and moving more than 20 degrees off it). In hitlag (0x0F000043) or while a shape's steps run he
// isn't. Test 128 took the direction x his facing (edge_hi_rx is already the world's) and a single still frame as
// stopped: facing left a Blade Dash's line ended at once (the user: "The lines don't appear anymore on Blade Dash"). TIMER_8 (0x0F000328): frames the line may go on into Fall after the move (20); TIMER_9: he's been in the
// air in this trail (then on the ground its points are at his feet + 1, not his middle: the line reaches the floor he
// landed on, test 128: "Lines still don't cover all the way to the ground on landing")
float edge_tr_pack4(float x, float y)
{
    return (float)((int)((x + 512.0f) * 4.0f + 0.5f) * 0x1000 + (int)((y + 512.0f) * 4.0f + 0.5f));
}

int edge_tr_bd_stop()
{
    float v;
    float x;
    float y;
    float px;
    float py;
    float d;
    if (edge_hi_charged)
    {
        return 0;
    }
    if (WorkModuleF(0, edge_tr_q_var()) != 0.0f)
    {
        return 0;                          // a shape's steps: VAR_11 theirs
    }
    x = PostureModuleF(0x1);
    y = PostureModuleF(0x2);
    v = WorkModuleF(0, edge_tr_s4_var());
    WorkModule(0, edge_tr_pack4(x, y), edge_tr_s4_var());
    if (v <= 0.0f || WorkModuleF(0, 0x0f000043) != 0.0f)
    {
        return 0;
    }
    px = (float)((int)v / 0x1000) * 0.25f - 512.0f;
    py = (float)((int)v - ((int)v / 0x1000) * 0x1000) * 0.25f - 512.0f;
    d = (x - px) * edge_hi_rx + (y - py) * edge_hi_ry;
    // and on the slash's line: across it under tan 20 of along (test 131, the user: "the line continues to be drawn for
    // too long, it begins curving": gravity bending his path after the slash)
    v = (x - px) * edge_hi_ry - (y - py) * edge_hi_rx;
    if (v < 0.0f)
    {
        v = -v;
    }
    if (d >= 0.4f && v <= d * 0.364f)
    {
        WorkModule(0, 2.0f, 0x0f00032a);
        return 0;
    }
    if (WorkModuleF(0, 0x0f00032a) <= 0.0f)
    {
        return 0x1;
    }
    return 0;
}

// his middle's height above his feet for the trail now: his feet + 1 on the ground once he's been in the air in it
float edge_tr_h()
{
    if (global18 != 0)
    {
        WorkModule(0, 9999.0f, 0x0f000329);
        return edge_tr_mid();
    }
    if (WorkModuleF(0, 0x0f000329) > 0.0f)
    {
        return 1.0f;
    }
    return edge_tr_mid();
}

// edge_tr_step(edge_tr_bd_stop()) with the stop in a local first (test 135: MSC-C breaks a call passed as another
// script function's argument when it calls functions itself, docs/MSC-C_Guide.md; tests 128 - 134 passed it so, every
// frame of every up special: Octaslash's own crossings made no shape from test 128 on)
void edge_tr_bd_step()
{
    int s;
    s = edge_tr_bd_stop();
    edge_tr_step(s);
}

// the trail still being laid (or its last steps): 1
int edge_tr_running()
{
    float q;
    q = WorkModuleF(0, edge_tr_q_var());
    if (q == -6.0f)
    {
        return 0;
    }
    if (q < 0.0f)
    {
        return WorkModuleF(0, edge_tr_sn_var()) >= 1024.0f;
    }
    return WorkModuleF(0, edge_tr_num_var()) >= 1024.0f;
}

// a range's mark step: start x 512 + count + 0.5
float edge_tr_mark(int start, int count)
{
    return (float)(start * 0x200 + count) + 0.5f;
}

// the shape's steps, one a frame (VAR_0 = -step), from his per-frame hook (edge_tr_tick: they go on after the trail's
// over): 1 the second range's mark or the first sums, 2 - 4 the sums read and the next asked, the ellipse fitted and
// the commit, 5 the trail as it was (or over: VAR_4 -1)
void edge_tr_steps()
{
    int q;
    int i;
    float n;
    float cx;
    float cy;
    float vxx;
    float vyy;
    float vxy;
    float d;
    float l1;
    float l2;
    float t;
    float a;
    float b;
    q = -(int)WorkModuleF(0, edge_tr_q_var());
    if (q >= 0xb)
    {
        edge_tr_find(q);
        return;
    }
    if (q == 1)
    {
        // the ranges still to mark (VAR_8 - VAR_10)
        i = 0x308;
        while (i <= 0x30a)
        {
            if (WorkModuleF(0, 0x0f000000 + i) > 0.0f)
            {
                WorkModule(0, WorkModuleF(0, 0x0f000000 + i), edge_tr_num_var());
                WorkModule(0, 0.0f, 0x0f000000 + i);
                return;
            }
            i = i + 1;
        }
        WorkModule(0, 0.0f, edge_tr_new_var());
        WorkModule(0, 0.0f, edge_tr_cross_var());
        WorkModule(0, edge_tr_sum1(), edge_tr_num_var());
        WorkModule(0, -2.0f, edge_tr_q_var());
        return;
    }
    if (q == 2 || q == 3)
    {
        WorkModule(0, WorkModuleF(0, edge_tr_new_var()), 0x0f000308 + 0x2 * (q - 2));
        WorkModule(0, WorkModuleF(0, edge_tr_cross_var()), 0x0f000309 + 0x2 * (q - 2));
        WorkModule(0, 0.0f, edge_tr_new_var());
        WorkModule(0, 0.0f, edge_tr_cross_var());
        if (q == 2)
        {
            WorkModule(0, edge_tr_sum2(), edge_tr_num_var());
        }
        else
        {
            WorkModule(0, edge_tr_sum3(), edge_tr_num_var());
        }
        WorkModule(0, -(float)(q + 1), edge_tr_q_var());
        return;
    }
    if (q == 4)
    {
        n = WorkModuleF(0, edge_tr_qn_var());
        cx = WorkModuleF(0, edge_tr_s1_var()) / n;
        cy = WorkModuleF(0, edge_tr_s2_var()) / n;
        vxx = WorkModuleF(0, edge_tr_s3_var()) / n - cx * cx;
        vyy = WorkModuleF(0, edge_tr_s4_var()) / n - cy * cy;
        vxy = WorkModuleF(0, edge_tr_new_var()) / n - cx * cy;
        d = MathF(0, (vxx - vyy) * (vxx - vyy) * 0.25f + vxy * vxy);
        l1 = (vxx + vyy) * 0.5f + d;
        l2 = (vxx + vyy) * 0.5f - d;
        if (l2 < 0.0f)
        {
            l2 = 0.0f;
        }
        t = MathF(0x1, 2.0f * vxy, vxx - vyy) * 0.5f * 57.29578f;   // the long axis, -90 - 90 degrees
        if (t < 0.0f)
        {
            t = t + 180.0f;
        }
        // the fit kept (VAR_8 the angle in 128ths of 180, VAR_9 / VAR_10 the half axes x 1.2: "at least 1.2x the size of
        // the shape", test 127) and the points' extents along / across it asked (EXTENT: a triangle's corners reach
        // further than its spread says)
        WorkModule(0, (float)(int)(t * 128.0f / 180.0f), edge_tr_s1_var());
        WorkModule(0, MathF(0, 2.0f * l1) * edge_tr_scale(), edge_tr_s2_var());
        WorkModule(0, MathF(0, 2.0f * l2) * edge_tr_scale(), edge_tr_s3_var());
        WorkModule(0, -100000.0f, edge_tr_new_var());
        WorkModule(0, -100000.0f, edge_tr_cross_var());
        WorkModule(0, -(float)(0xfa0 + (int)WorkModuleF(0, edge_tr_s1_var())) - 0.5f, edge_tr_num_var());
        WorkModule(0, -7.0f, edge_tr_q_var());
        return;
    }
    if (q == 7)
    {
        // the furthest along (5) / across (4) read; the furthest back asked (EXTENT of minus: 4200 +)
        WorkModule(0, WorkModuleF(0, edge_tr_new_var()), edge_tr_s4_var());
        WorkModule(0, WorkModuleF(0, edge_tr_cross_var()), edge_tr_qn_var());
        WorkModule(0, -100000.0f, edge_tr_new_var());
        WorkModule(0, -100000.0f, edge_tr_cross_var());
        WorkModule(0, -(float)(0x1068 + (int)WorkModuleF(0, edge_tr_s1_var())) - 0.5f, edge_tr_num_var());
        WorkModule(0, -8.0f, edge_tr_q_var());
        return;
    }
    if (q == 8)
    {
        // the shape: the middle of its extents, half axes the fit's or 1.2 x the extents (the larger)
        i = (int)WorkModuleF(0, edge_tr_s1_var());
        t = (float)i * 0.0245437f;                       // pi / 128
        vxx = edge_tr_sin(1.5707963f - t);               // the axis (cos, sin)
        vyy = edge_tr_sin(t);
        l1 = WorkModuleF(0, edge_tr_s4_var());           // along: max, min
        l2 = -WorkModuleF(0, edge_tr_new_var());
        vxy = WorkModuleF(0, edge_tr_qn_var());          // across: max, min
        d = -WorkModuleF(0, edge_tr_cross_var());
        cx = (l1 + l2) * 0.5f;
        cy = (vxy + d) * 0.5f;
        n = cx;
        cx = n * vxx - cy * vyy;
        cy = n * vyy + cy * vxx;
        a = WorkModuleF(0, edge_tr_s2_var());
        b = WorkModuleF(0, edge_tr_s3_var());
        if ((l1 - l2) * 0.5f * edge_tr_scale() > a)
        {
            a = (l1 - l2) * 0.5f * edge_tr_scale();
        }
        if ((vxy - d) * 0.5f * edge_tr_scale() > b)
        {
            b = (vxy - d) * 0.5f * edge_tr_scale();
        }
        if (b > a)
        {
            n = a;
            a = b;
            b = n;
            i = i + 0x40;
            i = i - (i / 0x80) * 0x80;
        }
        t = (float)i * 180.0f / 128.0f;
        if (a < 3.0f)
        {
            a = 3.0f;
        }
        if (a > 127.0f)
        {
            a = 127.0f;
        }
        if (b < 3.0f)
        {
            b = 3.0f;
        }
        if (b > a)
        {
            b = a;
        }
        // (tests 128 - 133 refused shapes near StageData 0 - 3's bounds; test 134, the user: "Remove the shape forming
        // restriction": every shape is made. CANCEL stays in the articles, unused)
        WorkModule(0, edge_tr_pack(cx, cy), edge_tr_new_var());
        WorkModule(0, (float)(i * 0x10000 + (int)(a * 2.0f) * 0x100 + (int)(b * 2.0f)), edge_tr_cross_var());
        WorkModule(0, edge_tr_commit(), edge_tr_num_var());
        ArticleModule(0x2710, edge_tr_fill_art());   // the hitbox: it reads 5 / 4 as it's made
        WorkModule(0, 9999.0f, 0x0f00032d);          // and it can KO: edge_hi_keep_in off till the next up special (138)
        // and the trail that made it ends here: the restore (step 5) writes its end, not its number (test 139, the user:
        // "occasionally a stray line is left rather than deleted once a shape is made": the path laid after the commit,
        // through Octaslash's forced end or the rest of a Blade Dash, was a new line the commit hadn't cleared)
        WorkModule(0, edge_tr_end_code(), edge_tr_sn_var());
        WorkModule(0, -5.0f, edge_tr_q_var());
        if (global4 == 0x159 && edge_hi_charged)
        {
            // a shape made in Octaslash ends it, its finisher pulling in (test 127: "force Sephiroth to end Octaslash
            // with the finisher hit angle that sends towards him, inside the shape"): VAR_20 3, the rush loop's. Test
            // 136: pending (TIMER_12) until the restore (step 5), a frame on: test 127 - 135 ended the move the frame
            // the commit went out, and the next step overwrote the commit before the articles read it (the user's
            // diagnostic: the loop was measured, nothing drawn, the lines kept)
            WorkModule(0, 9999.0f, 0x0f00032c);
        }
        return;
    }
    // 5: the trail as it was (VAR_11 his position: edge_tr_bd_stop's); a pending Octaslash end now (TIMER_12, test 136)
    if (WorkModuleF(0, 0x0f00032c) > 0.0f)
    {
        WorkModule(0, 0.0f, 0x0f00032c);
        if (global4 == 0x159 && edge_hi_charged)
        {
            WorkModule(0, 3.0f, edge_hi_pass_var());
        }
    }
    WorkModule(0, edge_tr_pack4(PostureModuleF(0x1), PostureModuleF(0x2)), edge_tr_s4_var());
    WorkModule(0, 0.0f, edge_tr_s3_var());             // VAR_10: the sums' till now (edge_tr_step reads it as the wait)
    WorkModule(0, 0.0f, edge_tr_cross_var());
    WorkModule(0, WorkModuleF(0, edge_tr_sp_var()), edge_tr_new_var());
    WorkModule(0, WorkModuleF(0, edge_tr_sn_var()), edge_tr_num_var());
    WorkModule(0, WorkModuleF(0, edge_tr_sn_var()), edge_tr_floor_var());
    WorkModule(0, 10.0f, edge_tr_cool_var());
    WorkModule(0, 0.0f, edge_tr_q_var());
}

// the trail's end: -1 (it stays: Blade Dash), -2 (held Octaslash's: its articles go)
float edge_tr_end_code()
{
    if (edge_tr_shot())
    {
        return -2.0f;                      // Shadow Flare's shot's line doesn't stay (test 148)
    }
    // (test 130: after a shape that ended it, VAR_20 3, -1 too: its lines are gone already, and its glow's articles
    // then go once it's over as Blade Dash's do, not through the -2 path; the user: Octaslash's shape "effect still
    // doesn't appear")
    if (edge_hi_charged && WorkModuleF(0, edge_hi_pass_var()) != 3.0f)
    {
        return -2.0f;
    }
    return -1.0f;
}

// a range between two pieces of one trail (their start numbers): the points between, start x 512 + count + 0.5; 0 none
float edge_tr_between(int a, int b)
{
    int lo;
    int hi;
    lo = a;
    hi = b;
    if (b < a)
    {
        lo = b;
        hi = a;
    }
    if (hi == lo)
    {
        return 0.0f;
    }
    return edge_tr_mark(lo + 1, hi - lo);
}

int edge_tr_count(float code)
{
    int c;
    if (code <= 0.0f)
    {
        return 0;
    }
    c = (int)code;
    return c - (c / 0x200) * 0x200;
}

// JQ X Y: asks the articles for a junction of trails X and Y (5 / 4 then X's piece, Y's)
void edge_tr_jq(int x, int y)
{
    WorkModule(0, 0.0f, edge_tr_new_var());
    WorkModule(0, 0.0f, edge_tr_cross_var());
    WorkModule(0, -(float)(0xbb8 + x * 0x10 + y) - 0.5f, edge_tr_num_var());
}

// the old trail candidates in between: Blade Dash blocks from the newest back, i 0 - 5
int edge_tr_cand(int i)
{
    int z;
    z = edge_tr_block - 1 - i;
    while (z < 0)
    {
        z = z + 0xe;
    }
    return z + 1;
}

// crossing old trail Y (piece q) after old trail X (piece p in VAR_6, own number then n1 in VAR_7): is there a
// junction X - Y (a shape of three lines) or X - Z - Y (four)? Asked a step a frame (VAR_0 -11 / -12 / -13; VAR_1 q,
// VAR_2 the candidate Z, VAR_8 / VAR_9 X - Z's pieces), the trail paused (VAR_3 / VAR_4 keep it)
void edge_tr_find_start(int q, int num)
{
    WorkModule(0, WorkModuleF(0, edge_tr_new_var()), edge_tr_sp_var());
    WorkModule(0, (float)num, edge_tr_sn_var());
    WorkModule(0, (float)q, edge_tr_floor_var());
    WorkModule(0, -1.0f, edge_tr_qn_var());
    WorkModule(0, (float)num, edge_tr_s4_var());   // the number crossed at (VAR_4 is the restore's: the end, if it ends)
    edge_tr_jq((int)WorkModuleF(0, edge_tr_om_var()) / 0x400, q / 0x400);
    WorkModule(0, -11.0f, edge_tr_q_var());
}

// the next candidate Z (not X, Y or this trail) asked X - Z, or none left: no shape, Y kept as the first crossing
void edge_tr_find_next()
{
    int i;
    int x;
    int y;
    int z;
    int n;
    x = (int)WorkModuleF(0, edge_tr_om_var()) / 0x400;
    y = (int)WorkModuleF(0, edge_tr_floor_var()) / 0x400;
    i = (int)WorkModuleF(0, edge_tr_qn_var()) + 1;
    while (i < 6)
    {
        z = edge_tr_cand(i);
        if (z != x && z != y && z != (int)WorkModuleF(0, edge_tr_s4_var()) / 0x400)
        {
            WorkModule(0, (float)i, edge_tr_qn_var());
            edge_tr_jq(x, z);
            WorkModule(0, -12.0f, edge_tr_q_var());
            return;
        }
        i = i + 1;
    }
    WorkModule(0, WorkModuleF(0, edge_tr_floor_var()), edge_tr_om_var());
    WorkModule(0, WorkModuleF(0, edge_tr_s4_var()), edge_tr_on_var());
    WorkModule(0, 0.0f, edge_tr_cross_var());
    WorkModule(0, WorkModuleF(0, edge_tr_sp_var()), edge_tr_new_var());
    WorkModule(0, WorkModuleF(0, edge_tr_sn_var()), edge_tr_num_var());
    n = edge_tr_start_num();
    WorkModule(0, (float)n, edge_tr_floor_var());
    WorkModule(0, 0.0f, edge_tr_q_var());
}

// the path's ranges marked from now: this trail's points since the first crossing, then X's, (Z's,) Y's between the
// pieces crossed and the junctions
void edge_tr_find_shape(float rx, float rz, float ry)
{
    int num;
    int n1;
    float r1;
    int cnt;
    num = (int)WorkModuleF(0, edge_tr_s4_var());
    n1 = (int)WorkModuleF(0, edge_tr_on_var());
    r1 = edge_tr_mark(n1, num - n1);
    cnt = (num - n1) + edge_tr_count(rx) + edge_tr_count(rz) + edge_tr_count(ry);
    if (cnt < 3 || num - n1 >= 0x200)
    {
        WorkModule(0, 5.0f, edge_tr_qn_var());
        edge_tr_find_next();               // too small: as nothing found
        return;
    }
    WorkModule(0, (float)cnt, edge_tr_qn_var());
    WorkModule(0, rx, edge_tr_s1_var());
    WorkModule(0, rz, edge_tr_s2_var());
    WorkModule(0, ry, edge_tr_s3_var());
    WorkModule(0, 0.0f, edge_tr_cross_var());
    WorkModule(0, r1, edge_tr_num_var());
    WorkModule(0, -1.0f, edge_tr_q_var());
    WorkModule(0, 0.0f, edge_tr_om_var());
}

void edge_tr_find(int q)
{
    float j5;
    float j4;
    int p;
    int qy;
    float rx;
    float rz;
    float ry;
    j5 = WorkModuleF(0, edge_tr_new_var());
    j4 = WorkModuleF(0, edge_tr_cross_var());
    p = (int)WorkModuleF(0, edge_tr_om_var());
    qy = (int)WorkModuleF(0, edge_tr_floor_var());
    if (q == 0xb)
    {
        if (j5 >= 1024.0f)
        {
            // X - Y: three lines
            rx = edge_tr_between(p, (int)j5);
            ry = edge_tr_between((int)j4, qy);
            edge_tr_find_shape(rx, 0.0f, ry);
            return;
        }
        edge_tr_find_next();
        return;
    }
    if (q == 0xc)
    {
        if (j5 >= 1024.0f)
        {
            WorkModule(0, j5, edge_tr_s1_var());   // X - Z: then Z - Y
            WorkModule(0, j4, edge_tr_s2_var());
            edge_tr_jq((int)j4 / 0x400, qy / 0x400);
            WorkModule(0, -13.0f, edge_tr_q_var());
            return;
        }
        edge_tr_find_next();
        return;
    }
    if (j5 >= 1024.0f)
    {
        // X - Z - Y: four lines
        rx = edge_tr_between(p, (int)WorkModuleF(0, edge_tr_s1_var()));
        rz = edge_tr_between((int)WorkModuleF(0, edge_tr_s2_var()), (int)j5);
        ry = edge_tr_between((int)j4, qy);
        edge_tr_find_shape(rx, rz, ry);
        return;
    }
    edge_tr_find_next();
}

// a shape found: its ranges marked from this frame (the first now, the second next: VAR_8), the trail kept to go on
void edge_tr_shape(int s1, int c1, int s2, int c2, int num)
{
    WorkModule(0, WorkModuleF(0, edge_tr_new_var()), edge_tr_sp_var());
    WorkModule(0, (float)num, edge_tr_sn_var());
    WorkModule(0, (float)(c1 + c2), edge_tr_qn_var());
    WorkModule(0, 0.0f, edge_tr_s1_var());
    WorkModule(0, 0.0f, edge_tr_s2_var());
    WorkModule(0, 0.0f, edge_tr_s3_var());
    if (c2 > 0)
    {
        WorkModule(0, edge_tr_mark(s2, c2), edge_tr_s1_var());
    }
    WorkModule(0, 0.0f, edge_tr_cross_var());
    WorkModule(0, edge_tr_mark(s1, c1), edge_tr_num_var());
    WorkModule(0, -1.0f, edge_tr_q_var());
    WorkModule(0, 0.0f, edge_tr_om_var());
}

// his per-frame hook (func_82): a shape's steps
void edge_tr_tick()
{
    float q;
    q = WorkModuleF(0, edge_tr_q_var());
    if (q == -6.0f)
    {
        WorkModule(0, WorkModuleF(0, edge_tr_sn_var()), edge_tr_num_var());   // the trail's end
        WorkModule(0, 0.0f, edge_tr_q_var());
        return;
    }
    if (q == 0.0f && WorkModuleF(0, edge_tr_s3_var()) > 0.0f)
    {
        WorkModule(0, WorkModuleF(0, edge_tr_s3_var()) - 1.0f, edge_tr_s3_var());
    }
    // one step a frame at most (TIMER_11 up for a frame after each: test 136, in case this hook runs twice in a frame,
    // as on a status change, which would skip a step's code before the articles read it)
    if ((q <= -1.0f && q >= -5.0f || q <= -7.0f && q >= -8.0f || q <= -11.0f && q >= -13.0f)
        && WorkModuleF(0, 0x0f00032b) <= 0.0f)
    {
        edge_tr_steps();
        WorkModule(0, 1.0f, 0x0f00032b);
    }
    // Blade Dash's line on into Fall while he still moves the slash's way (test 128), TIMER_8 frames at most; any other
    // status (landing, an aerial: the snake sword shares these variables) ends it
    if (WorkModuleF(0, 0x0f000328) > 0.0f && global4 != 0x159 && global4 != 0x15a)
    {
        if (global4 != 0xe || WorkModuleF(0, 0x0f000328) <= 1.0f || edge_sn_out() || edge_tr_running() == 0)
        {
            WorkModule(0, 0.0f, 0x0f000328);
            edge_tr_step(0x1);
        }
        else if (edge_tr_bd_stop())
        {
            WorkModule(0, 0.0f, 0x0f000328);
            edge_tr_step(0x1);
        }
        else
        {
            edge_tr_step(0);
        }
    }
}

// every frame it's laid: a crossing looked at, else a point once he's edge_tr_seg() from the last;
// `last` puts down what's left (from 1 long) and ends the trail
void edge_tr_step(int last)
{
    float v;
    float x;
    float y;
    float dx;
    float dy;
    float d;
    float c;
    int num;
    int m;
    int m1;
    int lo;
    int hi;
    int c1;
    int c2;
    if (WorkModuleF(0, edge_tr_q_var()) < 0.0f)
    {
        if (last)
        {
            WorkModule(0, edge_tr_end_code(), edge_tr_sn_var());   // over once the steps are done
        }
        return;                            // the trail waits for the steps
    }
    if (WorkModuleF(0, edge_tr_num_var()) < 1024.0f)
    {
        return;
    }
    if (WorkModuleF(0, edge_tr_s3_var()) > 0.0f && last == 0)
    {
        return;                            // point 0 not seen yet (edge_tr_begin)
    }
    if (WorkModuleF(0, edge_tr_cool_var()) > 0.0f)
    {
        WorkModule(0, WorkModuleF(0, edge_tr_cool_var()) - 1.0f, edge_tr_cool_var());
    }
    c = WorkModuleF(0, edge_tr_cross_var());
    WorkModule(0, 0.0f, edge_tr_cross_var());
    num = (int)WorkModuleF(0, edge_tr_num_var());
    if (c <= -1024.0f && WorkModuleF(0, edge_tr_cool_var()) <= 0.0f && last == 0)
    {
        m = (int)(-c);
        if (m / 0x400 == num / 0x400)
        {
            // its own trail: a loop, its points m + 1 .. num - 1
            if ((float)m >= WorkModuleF(0, edge_tr_floor_var()) && num - 1 - m >= 3 && num - 1 - m < 0x200)
            {
                edge_tr_shape(m + 1, num - 1 - m, 0, 0, num);
                return;
            }
        }
        else
        {
            // an old trail: the second time across it closes a shape (its own points since the first, the old
            // trail's between the two pieces crossed); the first is kept
            m1 = (int)WorkModuleF(0, edge_tr_om_var());
            if (m1 > 0 && m1 / 0x400 != m / 0x400)
            {
                // another old trail: a shape if the two meet (directly or through a third): edge_tr_find
                edge_tr_find_start(m, num);
                return;
            }
            if (m1 > 0 && m1 / 0x400 == m / 0x400 && m1 != m)
            {
                lo = m1;
                hi = m;
                if (m < m1)
                {
                    lo = m;
                    hi = m1;
                }
                c1 = num - (int)WorkModuleF(0, edge_tr_on_var());
                c2 = hi - lo;
                if (c1 + c2 >= 3 && c1 < 0x200 && c2 < 0x200)
                {
                    edge_tr_shape((int)WorkModuleF(0, edge_tr_on_var()), c1, lo + 1, c2, num);
                    return;
                }
            }
            WorkModule(0, (float)m, edge_tr_om_var());
            WorkModule(0, (float)num, edge_tr_on_var());
        }
    }
    v = WorkModuleF(0, edge_tr_new_var());
    if (edge_tr_shot())
    {
        c = WorkModuleF(0, edge_tr_pen_var());     // the pen: Shadow Flare's shot's place (test 148)
        x = edge_tr_x(c);
        y = edge_tr_y(c);
    }
    else
    {
        x = PostureModuleF(0x1);
        y = PostureModuleF(0x2) + edge_tr_h();
    }
    dx = x - edge_tr_x(v);
    dy = y - edge_tr_y(v);
    d = dx * dx + dy * dy;
    if (d >= edge_tr_seg() * edge_tr_seg() || last && d >= 1.0f)
    {
        v = edge_tr_pack(x, y);
        edge_tr_point(v, num + 1);
    }
    if (last)
    {
        // over next frame (his per-frame hook): the articles take this last point first (test 127: the piece to where
        // he landed was lost, the end written over it in the same frame)
        WorkModule(0, -6.0f, edge_tr_q_var());
        WorkModule(0, edge_tr_end_code(), edge_tr_sn_var());
    }
}

// test 148, the user: "make side special act as a line that can finish a shape", then "side special should not create a
// new visible line, but act as one while it is active". Shadow Flare's shot (weapons/flare1.c) writes its place into his
// VAR_27 (shared 3, packed as edge_tr_pack) every frame it flies, -1 once it stops (it hit / its end). From his
// per-frame hook (after edge_tr_tick) a trail is laid along it as one is along him in up special: block 15 (a trail that
// doesn't stay, as held Octaslash's: they can't overlap, the shot is over long before SHOT's cancel frame), its numbers
// from 15 x 1024 + 765 (edge_tr_shot_from) so its articles draw no line (trail.c tr_hidden: "should not create a new
// visible line"), the pen its place (VAR_12, edge_tr_step); its crossings with the lines on screen close shapes as any
// trail's do (fill, hitbox, every line cleared; the trail ends with its shape). Over when the shot stops, or its place
// hasn't come for 4 frames (TIMER_15: removed by the game, a shield); ended with -2, its articles go once a fill is over:
// nothing of it stays. Only started in SHOT (0x158), when no trail is laid and no shape's steps run (else that shot
// makes no line); one line a shot (VAR_12 -1 from SHOT's start and after its line, 0 from edge_s_generate)
void edge_s_line_tick()
{
    float v;
    float q;
    v = WorkModuleF(0, edge_tr_place_var());
    q = WorkModuleF(0, edge_tr_q_var());
    if (edge_tr_shot() == 0)
    {
        if (v > 0.0f && global4 == 0x158 && edge_s_fired && WorkModuleF(0, edge_tr_pen_var()) == 0.0f && q >= 0.0f
            && WorkModuleF(0, edge_tr_num_var()) < 1024.0f && edge_sn_out() == 0)
        {
            WorkModule(0, v, edge_tr_pen_var());
            WorkModule(0, 0.0f, edge_tr_place_var());
            WorkModule(0, 4.0f, edge_tr_fresh_var());
            edge_tr_shot_begin(v);
        }
        return;
    }
    WorkModule(0, 9999.0f, edge_tr_shot_var());
    if (v > 0.0f && WorkModuleF(0, edge_tr_fresh_var()) > 0.0f)
    {
        WorkModule(0, v, edge_tr_pen_var());
        WorkModule(0, 0.0f, edge_tr_place_var());
        WorkModule(0, 4.0f, edge_tr_fresh_var());
        edge_tr_step(0);
    }
    else if (v < 0.0f || WorkModuleF(0, edge_tr_fresh_var()) <= 0.0f)
    {
        // stopped: the line ends at its last place (edge_tr_step 1; again each frame until it's over: it waits for a
        // shape's steps)
        WorkModule(0, 0.0f, edge_tr_place_var());
        WorkModule(0, 0.0f, edge_tr_fresh_var());
        edge_tr_step(0x1);
    }
    if (WorkModuleF(0, edge_tr_q_var()) >= 0.0f && WorkModuleF(0, edge_tr_num_var()) < 1024.0f)
    {
        WorkModule(0, 0.0f, edge_tr_shot_var());   // its line and steps over
        WorkModule(0, -1.0f, edge_tr_pen_var());
    }
}

// the rush's y: the stop energy's plus the gravity energy's (test 106: in the air the rush's y is on the gravity
// energy, edge_hi_rush_set)
float edge_hi_vy()
{
    return KineticModuleF(0xb, 0x3) + KineticModuleF(0x1, 0x1);
}

// the rush's speed on its frame, by Ultimate's numbers (ExeFS 0x9e5100's brake: rush_speed 13.5 / 6.2, less
// rush_brake 1.72 / 0.47 a frame from count rush_brake_frame 2 / 6), not read back from the engine
float edge_hi_rush_m()
{
    float m;
    float bf;
    m = edge_hi_p(13.5f, 6.2f);
    bf = edge_hi_p(2.0f, 6.0f);
    if ((float)edge_hi_count >= bf)
    {
        m = m - edge_hi_p(1.72f, 0.47f) * ((float)edge_hi_count - bf + 1.0f);
    }
    if (edge_hi_held() && m < edge_hi_cruise())
    {
        return edge_hi_cruise();           // held Octaslash: the normal brake down to its cruise, then kept (test 115)
    }
    if (m < 0.0f)
    {
        m = 0.0f;
    }
    return m;
}

// the rush's velocity (dx, dy) * m: on the ground on the stop energy along the floor, as before; in the air x on the
// stop energy and y on the gravity energy (gravity 0), which Smash 4 moves him by for sure (test 106, the user: tap
// up special "still barely gives height" after test 101 lifted the stop energy's limit; the gravity energy's speed
// is what held forward air's fall and Scintilla's break set, both seen working)
void edge_hi_rush_set(float dx, float dy, float m)
{
    // (dx, dy) is a world direction already: the aim is the raw stick, the floor tangent has the facing in it
    KineticModule(0x10, 0x3, 0.0f, 0.0f);
    if (global18 == 0)
    {
        KineticModule(0x11, 0x3, dx * m, dy * m);
        KineticModule(0x11, 0x1, 0.0f);
    }
    else
    {
        KineticModule(0x11, 0x3, dx * m, 0.0f);
        KineticModule(0x11, 0x1, dy * m);
    }
}

float edge_hi_ground_angle() { return 90.0f; } // f_16f20's K (NRO rodata 0x265620, not in the dump):
                                               // approximate; vanilla Smash 4 Fox's Fire Fox uses 90
float edge_hi_deg() { return 57.29578f; }      // degrees per radian

// the unsigned angle between two vectors (radians, 0..pi)
float edge_hi_angle(float ax, float ay, float bx, float by)
{
    return MathF(0x1, func_13(ax * by - ay * bx), ax * bx + ay * by);
}

// f_16f20: the rush direction for an aim (x, y) -> edge_hi_rx / ry / on_ground. On the ground, an aim at
// least K from the floor normal goes along the floor (its tangent in the facing direction)
void edge_hi_resolve(float x, float y)
{
    float nx;
    float ny;
    float lr;
    float l;
    edge_hi_on_ground = 0;
    if (global18 == 0)
    {
        nx = GroundModuleF(0x5, 0x8);
        ny = GroundModuleF(0x6, 0x8);
        if (nx != 0.0f || ny != 0.0f)
        {
            if (edge_hi_angle(nx, ny, x, y) * edge_hi_deg() >= edge_hi_ground_angle())
            {
                lr = PostureModuleF(0);
                x = ny * lr;
                y = -nx * lr;
                edge_hi_on_ground = 0x1;
            }
        }
    }
    l = MathF(0, x * x + y * y);
    if (l < 0.0001f)
    {
        x = 0.0f;
        y = 1.0f;
        l = 1.0f;
    }
    edge_hi_rx = x / l;
    edge_hi_ry = y / l;
}

// ROT for a direction: -sign(y) * angle((lr, 0), d) (09a70's ROT_TARGET, f_16b60 during the rush)
float edge_hi_pitch_of(float x, float y)
{
    float a;
    a = edge_hi_angle(PostureModuleF(0), 0.0f, x, y) * edge_hi_deg();
    if (y > 0.0f)
    {
        return -a;
    }
    return a;
}

// the body pitch on joint "rot" (Ultimate f_02cf0: ModelModule::set_joint_rotate("rot", (ROT, 0, 0)), every
// frame and in hitlag). Smash 4's MSC op is the same: ModelModule(0x1, joint, x, y, z, mode) in degrees; joint
// id 2 = RotN, his "rot" (model.jtb). Mode 1 composes with the animation, as vanilla's common status 0x10E
// tilts RotN (mode 2 composes the other way: the one to try if the tilt turns about the wrong axis; mode 0
// replaces the animated rotation, as Pikachu's Quick Attack). The rotation stays until removed
// (edge_hi_pitch_reset), status changes don't clear it
void edge_hi_pitch_apply()
{
    ModelModule(0x1, 0x2, edge_hi_rot, 0.0f, 0.0f, 0x1);
}

// the pitch for this frame (start: 0 -> ROT_TARGET between the decide and rot_end frames; rush: along the
// speed; air end: back to 0 between rotate_back_begin / end), then applied
void edge_hi_pitch()
{
    float f;
    float b;
    float e;
    float t;
    float vx;
    float vy;
    f = MotionModuleF(0x1);
    if (global4 == 0x154)
    {
        edge_hi_rot = 0.0f;
        if (edge_hi_decided)
        {
            b = edge_hi_p(18.0f, 30.0f);   // rot_decide_frame
            e = edge_hi_p(23.0f, 35.0f);   // rot_end_frame
            t = (f - b) / (e - b);
            if (t < 0.0f)
            {
                t = 0.0f;
            }
            if (t > 1.0f)
            {
                t = 1.0f;
            }
            edge_hi_rot = edge_hi_rot_target * t;
        }
    }
    else if (global4 == 0x159)
    {
        vx = KineticModuleF(0xa, 0x3);
        vy = edge_hi_vy();
        if (func_13(vx) + func_13(vy) > 0.0001f)
        {
            edge_hi_rot = edge_hi_pitch_of(vx, vy);
        }
    }
    else if (global4 == 0x15a && edge_hi_end_air)
    {
        b = edge_hi_p(11.0f, 18.0f);       // rotate_back_begin_frame
        e = edge_hi_p(15.0f, 53.0f);       // rotate_back_end_frame (Blade Dash: 44, back by its Fall: 23 in test 116, 15 since 120)
        if (f >= b)
        {
            t = e - b;
            if (t <= 0.0f)
            {
                t = 1.0f;
            }
            t = 1.0f - (f - b) / t;
            if (t < 0.0f)
            {
                t = 0.0f;
            }
            if (t > 1.0f)
            {
                t = 1.0f;
            }
            edge_hi_rot = edge_hi_rot_target * t;
        }
    }
    else
    {
        edge_hi_rot = 0.0f;
    }
    edge_hi_pitch_apply();
}

// f_14650: the pitch back to 0 at once (the joint's rotation removed: every way out of the up special)
void edge_hi_pitch_reset()
{
    edge_hi_rot = 0.0f;
    ModelModule(0x2, 0x2);
}

int edge_hi_fx_direction() { return 0x342006E; } // fx edge_octaslash_direction

// f_18b30: the aim effect, edge_octaslash_direction (Ultimate: req once, the handle kept in 0xe370, set_pos /
// set_rot every frame, visible while 0xe36c, which is on for the whole start), at pos + (0, 8 * scale) +
// v * 14 * scale (direction_effect_offset_y / direction_effect_radius), rolled -sign(v.x) * angle(up, v),
// coloured direction_effect_color[team colour] through set_rgb_partial_last (not here: below).
// Smash 4 (cross_f.rpx, EffectModule's MSC handler 0x02C2CEC8, docs/native-notes.md): 0x3 a request at a world
// place, 0x17 / 0x18 a handle's world position / rotation (degrees)
void edge_hi_direction(float x, float y)
{
    float s;
    s = PostureModuleF(0x7);
    edge_hi_fx_x = PostureModuleF(0x1) + x * 14.0f * s;
    edge_hi_fx_y = PostureModuleF(0x2) + 8.0f * s + y * 14.0f * s;
    edge_hi_fx_roll = edge_hi_angle(0.0f, 1.0f, x, y) * edge_hi_deg();
    if (x > 0.0f)
    {
        edge_hi_fx_roll = -edge_hi_fx_roll;
    }
    if (edge_hi_fx == 0 && edge_hi_fx_direction() != 0)
    {
        // a world request (0x3, the turn in radians), as Smash 4's own code moves effects by handle (func_1764:
        // 0x3, then 0x17 / 0x18): test 63-65 asked with 0x272C (the bone request + colour) and the arrow drifted
        // off from him, thin. The colour (direction_effect_color by team) has no MSC op on a handle: the
        // emitters' own colour for now
        edge_hi_fx = EffectModule(0x3, edge_hi_fx_direction(), edge_hi_fx_x, edge_hi_fx_y, PostureModuleF(0x3) + 6.0f, 0, 0,
                                  edge_hi_fx_roll * 0.0174533f, 1.0f, 0, 0xffffffff);
    }
    if (edge_hi_fx != 0)
    {
        // 6 toward the camera: at his own depth his coat and sword hid part of it (test 67, "slightly hidden")
        EffectModule(0x17, edge_hi_fx, edge_hi_fx_x, edge_hi_fx_y, PostureModuleF(0x3) + 6.0f);
        EffectModule(0x18, edge_hi_fx, 0.0f, 0.0f, edge_hi_fx_roll);
    }
}

// 09dd0's kill_kind(edge_octaslash_direction, true, true)
void edge_hi_direction_kill()
{
    if (edge_hi_fx != 0)
    {
        EffectModule(0x6, edge_hi_fx);
        EffectModule(0x2723, edge_hi_fx_direction(), 0x1, 0x1);
        edge_hi_fx = 0;
    }
}

// the ledge-grab mode (func_100: 0 none, 2 snap from both sides = Ultimate's ALWAYS_BOTH_SIDES, 4 while
// falling = its ON_DROP_BOTH_SIDES, inferred), set when it changes
void edge_hi_cliff_mode(int mode)
{
    if (edge_hi_cliff != mode)
    {
        edge_hi_cliff = mode;
        func_100(mode);
    }
}

// f_147f0: the landing lag of the special fall / landing that follows (landing_fix_frame 27 / 56) in the
// landing frame float (LandingFallSpecial 0x19 plays its motion over it), the special fall's air speed as is
void edge_hi_landing_frame()
{
    if (global6 == 0x19 || global6 == 0x10)
    {
        WorkModule(0, edge_hi_p(22.0f, 56.0f), 0);   // Blade Dash 22 (Ultimate 27; test 113, the user: slightly lower)
        WorkModule(0, 1.0f, 0x1);
    }
}

// Ultimate's EffectModule::kill_kind(edge_octaslash_line) (the rush's line, made by its effect script)
void edge_hi_line_kill()
{
    EffectModule(0x2723, 0x342004B, 0x1, 0x1);
}

int edge_hi_start_pre()
{
    func_69();
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1422, 0, 0x100, 0x1000);
    return 0;
}

int edge_hi_rush_pre()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x422, 0, 0x100, 0);
    return 0;
}

int edge_hi_end_pre()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x422, 0, 0x100, 0);
    return 0;
}

// sub_set_special_start_common_kinetic_setting("param_special_hi") and f_13d60 (again when the situation
// changes): ground x speed x 0.4, brake 0.1; air x speed x 0.4, brake 0.02, y speed x 0.4, fall capped at
// 0.1 of his, no drift (start_control_* 0); gravity -0.06 (f_188f0, every frame in the loop)
void edge_hi_start_kinetic()
{
    float vx;
    float vy;
    vx = KineticModuleF(0, 0xffffffff);
    vy = KineticModuleF(0x1, 0xffffffff);
    if (global18 == 0x2)
    {
        GroundModule(0x2710, 0x5);
        KineticModule(0, 0xa);
        KineticModule(0x11, 0x3, vx * 0.4f, 0.0f);
        KineticModule(0x10, 0x3, 0.02f, 0.0f);
        KineticModule(0xb, 0x3);
        KineticModule(0x11, 0x1, vy * 0.4f);
        KineticModule(0xf, 0x1, -0.06f);
        KineticModule(0x14, 0x1, WorkModuleF(0, 0x3000019) * 0.1f);
        KineticModule(0xb, 0x1);
        KineticModule(0x11, 0x2, 0.0f, 0.0f);
        KineticModule(0xc, 0x2);
    }
    else
    {
        GroundModule(0x2710, 0x2);   // ground, stopping at edges (inferred: the common special start's)
        KineticModule(0, 0x6);
        KineticModule(0x11, 0x3, vx * 0.4f, 0.0f);
        KineticModule(0x10, 0x3, 0.1f, 0.0f);
        KineticModule(0xb, 0x3);
    }
}

int edge_hi_start_motion()
{
    if (global18 == 0x2)
    {
        return 0x239;
    }
    return 0x231;
}

// 17e40 / 19910: the start's frames
void edge_hi_start_loop()
{
    float f;
    float x;
    float y;
    float l;
    if (StatusModule(0x6) == 0 && (global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0))
    {
        edge_hi_start_kinetic();
        MotionModule(0x3, edge_hi_start_motion());
    }
    if (global18 == 0x2)
    {
        KineticModule(0xf, 0x1, -0.06f);   // start_gravity
    }
    f = MotionModuleF(0x1);
    if (edge_hi_decided == 0)
    {
        x = global48;
        y = global32;
        if (func_13(x) + func_13(y) < 0.5f)
        {
            x = 0.0f;
            y = 1.0f;
        }
        l = MathF(0, x * x + y * y);
        x = x / l;
        y = y / l;
        edge_hi_direction(x, y);
        if (f >= edge_hi_p(18.0f, 30.0f))  // rot_decide_frame
        {
            edge_hi_dir_x = x;
            edge_hi_dir_y = y;
            if (func_13(global48) > 0.125f)
            {
                PostureModule(0x5);        // set_stick_lr
                PostureModule(0x2);        // update_rot_y_lr
            }
            edge_hi_resolve(x, y);
            edge_hi_rot_target = edge_hi_pitch_of(edge_hi_rx, edge_hi_ry);
            edge_hi_decided = 0x1;
        }
    }
    else
    {
        edge_hi_direction(edge_hi_dir_x, edge_hi_dir_y);
        SlopeModule(0x2710, 0);            // slope(MA_MSC_CMD_SLOPE_SLOPE, 2692): no leg slope (Fox's too)
        if (edge_hi_charged)
        {
            if (MotionModule(0x2712))
            {
                func_16(0x159, 0);
                return;
            }
        }
        else if (f >= 23.0f)               // rot_end_frame
        {
            func_16(0x159, 0);
            return;
        }
    }
    edge_hi_pitch();
}

// 09a70
void edge_hi_start_main()
{
    edge_hi_charged = 0x1;
    edge_hi_decided = 0;
    edge_hi_dir_x = 0.0f;
    edge_hi_dir_y = 1.0f;
    edge_hi_rot = 0.0f;
    edge_hi_rot_target = 0.0f;
    edge_hi_landed = 0;
    edge_hi_count = 0;
    edge_hi_end_air = 0;
    edge_hi_control = 0;
    edge_hi_cliff = 0xffffffff;
    edge_hi_fx = 0;
    WorkModule(0, 0.0f, edge_hi_pass_var());
    edge_hi_start_kinetic();
    MotionModule(0x1, edge_hi_start_motion(), 0, 1.0f);
    global20 = 0;
    func_78(edge_hi_start_loop);
}

// 09dd0
void edge_hi_start_end()
{
    edge_hi_direction_kill();
    edge_hi_rot = edge_hi_rot_target;
    if (global6 != 0x159)
    {
        edge_hi_pitch_reset();
    }
}

// f_157d0 + 0a500 / 0acc0: the rush along the decided direction (re-resolved: the situation may have
// changed since), 13.5 a frame (Octaslash 6.2) on energy 3, no gravity, no drift
void edge_hi_rush_main()
{
    float s;
    edge_hi_resolve(edge_hi_dir_x, edge_hi_dir_y);
    if (edge_hi_on_ground)
    {
        func_20(0);
        GroundModule(0x2710, 0x1);         // correct 1204 (GROUND, inferred: he can dash off an edge)
    }
    else
    {
        func_20(0x2);
        GroundModule(0x2710, 0x5);
    }
    s = edge_hi_p(13.5f, 6.2f);            // rush_speed
    KineticModule(0, 0xd);                 // as Fox's Fire Fox rush
    KineticModule(0x11, 0x1, 0.0f);        // the gravity energy carries the air rush's y, gravity 0 (test 106)
    KineticModule(0xf, 0x1, 0.0f);
    KineticModule(0x14, 0x1, 20.0f);       // its fall cap past any rush speed
    KineticModule(0xb, 0x1);
    KineticModule(0x11, 0x2, 0.0f, 0.0f);
    KineticModule(0xc, 0x2);
    edge_hi_rush_set(edge_hi_rx, edge_hi_ry, s);
    // no speed limit on it (-1): Smash 4 caps the stop energy's y in the air unless lifted, as Zelda's Farore's
    // Wind does in its air end (zelda.mscsb func_2291: KineticModule(0x14, 3, x limit, -1)); test 101, the user:
    // "Tap up special doesn't go far enough when going upwards"
    KineticModule(0x14, 0x3, -1.0f, -1.0f);
    KineticModule(0xb, 0x3);
    WorkModule(0, edge_hi_loop_frames(), edge_hi_timer_var());
    WorkModule(0, 0.0f, edge_hi_pass_var());
    WorkModule(0, 0.0f, edge_hi_wrap_var());
    edge_tr_begin();                       // the trail (test 123)
    WorkModule(0, 0.0f, edge_hi_total_var());
    if (edge_hi_charged || edge_hi_on_ground == 0)
    {
        // once per air time: used from the attack on (test 116; was the start). A Blade Dash along the ground doesn't
        // use it, so off an edge he has it still (test 130, the user: "make the Blade Dash not consume an air use if
        // it leaves an edge")
        WorkModule(0, 1.0f, edge_hi_used_var());
    }
    edge_hi_count = 0;                     // init 04890 / 04950
    edge_hi_landed = 0;
    edge_hi_cliff = 0xffffffff;
    if (edge_hi_charged)
    {
        MotionModule(0x1, 0x237, 0, 1.0f); // SpecialHi2
        edge_hi_cliff_mode(0);             // game_specialhi2: cliff check NONE at frame 0
    }
    else
    {
        MotionModule(0x1, 0x235, 0, 1.0f); // SpecialHi1
        edge_hi_cliff_mode(0x2);           // pre: ALWAYS_BOTH_SIDES (to frame 6: edge_hi_rush_loop)
    }
    global20 = 0;
    edge_hi_pitch();
    func_78(edge_hi_rush_loop);
}

// the END status, ground (edge_hi_end_air 0) or air
void edge_hi_to_end(int air)
{
    edge_hi_end_air = air;
    func_16(0x15a, 0);
}

// 175b0 / 15c90
void edge_hi_rush_loop()
{
    float f;
    float vx;
    float vy;
    if (func_56())                         // sub_transition_group_check_air_cliff
    {
        return;
    }
    f = MotionModuleF(0x1);
    if (edge_hi_charged == 0 && f >= 6.0f)
    {
        edge_hi_cliff_mode(0);             // game_specialhi1 frame 6: cliff check NONE
    }
    edge_tr_bd_step();       // the trail (test 123; Blade Dash's: while he moves the slash's way, test 128)
    vx = KineticModuleF(0xa, 0x3);
    vy = edge_hi_vy();
    if (global19 != 0 && global18 == 0)    // landed mid-rush
    {
        // f_164c0: within landing_fall_special_angle (25) of straight down -> f_16820 + landing
        if (func_13(vx) + func_13(vy) > 0.0001f && edge_hi_angle(0.0f, -1.0f, vx, vy) * edge_hi_deg() <= 25.0f
            && edge_hi_held() == 0)        // held Octaslash goes on along the floor (test 127)
        {
            KineticModule(0x11, 0x3, vx * 0.25f, 0.0f);   // landing_speed_x_mul (both 0.25)
            func_16(0x19, 0);
            return;
        }
        if (edge_hi_charged == 0)
        {
            edge_hi_landed = 0x1;
            edge_hi_to_end(0);
            return;
        }
        GroundModule(0x2710, 0x1);         // Octaslash keeps rushing along the floor
    }
    if (edge_hi_charged)
    {
        if (WorkModuleF(0, edge_hi_pass_var()) == 3.0f)
        {
            // a shape made: the end now, its finisher pulling toward him (SpecialHi2End's hits at angle 366 for VAR_20 3)
            if (global18 == 0)
            {
                edge_hi_to_end(0);
            }
            else
            {
                edge_hi_to_end(0x1);
            }
            return;
        }
        edge_hi_link();
        if ((float)edge_hi_count >= 15.0f && edge_hi_held() && WorkModuleF(0, edge_hi_timer_var()) > 0.0f
            && WorkModuleF(0, edge_hi_total_var()) < edge_hi_loop_max())
        {
            // past its pass and still held: SpecialHi2 again from the 2nd hit (the script skips the 1st on pass 2)
            if (f >= edge_hi_loop_to())
            {
                if (WorkModuleF(0, edge_hi_wrap_var()) == 1.0f)
                {
                    WorkModule(0, 0.0f, edge_hi_wrap_var());
                    WorkModule(0, 2.0f, edge_hi_pass_var());
                    MotionModule(0x1, 0x237, edge_hi_loop_from(), 1.0f);
                }
                else
                {
                    WorkModule(0, 1.0f, edge_hi_wrap_var());   // its last hit (frame 14) out for a frame first
                }
            }
            if (f >= 1.0f)
            {
                GroundModule(0x2713, 0);
            }
            edge_hi_pitch();
            return;
        }
        if (WorkModuleF(0, edge_hi_pass_var()) != 2.0f)
        {
            WorkModule(0, (float)edge_hi_held(), edge_hi_pass_var());   // 1: the first pass, held (no end flash)
        }
    }
    if ((float)edge_hi_count >= edge_hi_p(7.0f, 15.0f))   // rush_frame
    {
        // Ultimate also takes a floor within ground_check_distance (0.01) below as the ground (attach_ground):
        // here the situation alone
        if (global18 == 0)
        {
            edge_hi_to_end(0);
        }
        else
        {
            edge_hi_to_end(0x1);
        }
        return;
    }
    if (f >= 1.0f)                         // rush_xlu_frame: set_passable_check(false)
    {
        GroundModule(0x2713, 0);
    }
    edge_hi_pitch();
}

// 0a6c0 / 0ae80
void edge_hi_rush_end()
{
    if (global6 != 0x15a || edge_hi_end_air == 0 && edge_hi_charged)
    {
        edge_tr_step(0x1);                 // the trail ends but into the air end (it goes on while he rises; Blade
                                           // Dash's into either end: on while he moves the slash's way, test 128)
    }
    if (global6 != 0x15a)
    {
        edge_hi_line_kill();
    }
    if (global6 != 0x15a || edge_hi_end_air == 0)
    {
        edge_hi_pitch_reset();
    }
    edge_hi_landing_frame();
}

// in the air, touching a wall or ceiling (GroundModule 0x2722: 1 ceiling, 2 / 4 the walls, as vanilla's wall /
// ceiling bounces read them): the rush's direction (edge_hi_rx / ry) with the surface's normal taken out, so it
// slides along it (test 101, the user: Octaslash "seems to 'bounce' Sephiroth off of diagonal stage geometry")
void edge_hi_slide(int side)
{
    float nx;
    float ny;
    float d;
    float l;
    float x;
    float y;
    if (GroundModule(0x2722, side) == 0)
    {
        return;
    }
    nx = GroundModuleF(0x5, side);
    ny = GroundModuleF(0x6, side);
    if (nx == 0.0f && ny == 0.0f)
    {
        return;
    }
    d = edge_hi_rx * nx + edge_hi_ry * ny;
    x = edge_hi_rx - d * nx;
    y = edge_hi_ry - d * ny;
    l = MathF(0, x * x + y * y);
    if (l < 0.05f)
    {
        return;                            // straight into it: the engine stops him there
    }
    edge_hi_rx = x / l;
    edge_hi_ry = y / l;
}

// the rush's speed each frame (ExeFS 0x9e5100, Ultimate's kinetic hook on energy 3 during the rush): on the
// ground along the floor's tangent keeping its size; from rush count rush_brake_frame (2, Octaslash 6) a
// brake of rush_brake (1.72 / 0.47) along the path. In the air (test 101) the speed is kept on the rush's own
// line, slid along any wall / ceiling touched (edge_hi_slide): the engine's push off slanted stage sides sent it
// back the other way
void edge_hi_rush_speed()
{
    float ax;
    float ay;
    float nx;
    float ny;
    float lr;
    float dx;
    float dy;
    if (global18 == 0)
    {
        lr = PostureModuleF(0);
        nx = GroundModuleF(0x5, 0x8);
        ny = GroundModuleF(0x6, 0x8);
        if (nx == 0.0f && ny == 0.0f)
        {
            ny = 1.0f;
        }
        if (edge_hi_held())
        {
            // held Octaslash on the floor: along it the way the aim goes (its x), the aim kept, so steering up takes
            // him off it (test 127, the user: on the ground he "can only move forward until leaving the edge": the aim
            // was set to the floor's way every frame, so the steering never got anywhere)
            dx = ny;
            dy = -nx;
            if (edge_hi_rx * dx + edge_hi_ry * dy < 0.0f)
            {
                dx = -dx;
                dy = -dy;
            }
            if (func_13(edge_hi_rx * ny - edge_hi_ry * nx) < 0.1f)
            {
                dx = 0.0f;                 // aimed straight into it: still
                dy = 0.0f;
            }
            edge_hi_rush_set(dx, dy, edge_hi_rush_m());
            return;
        }
        dx = ny * lr;
        dy = -nx * lr;
        edge_hi_rx = dx;                   // off the floor, it goes on this way
        edge_hi_ry = dy;
    }
    else
    {
        // the aim slid along what it touches this frame only, the aim itself kept: off the surface it goes on the
        // way it was aimed (test 105, the user's clip: test 101 kept the slid way, so under a stage's slanted side it
        // went on up and away along it past the corner: the "bounce")
        ax = edge_hi_rx;
        ay = edge_hi_ry;
        edge_hi_slide(0x1);
        edge_hi_slide(0x2);
        edge_hi_slide(0x4);
        dx = edge_hi_rx;
        dy = edge_hi_ry;
        edge_hi_rx = ax;
        edge_hi_ry = ay;
    }
    edge_hi_rush_set(dx, dy, edge_hi_rush_m());
}

// 0b360: the ground end
void edge_hi_end_ground_main()
{
    float vx;
    float mul;
    vx = KineticModuleF(0xa, 0x3);
    mul = edge_hi_p(0.6f, 0.9f);           // ground_speed_x_mul
    if (edge_hi_landed)
    {
        mul = 0.25f;                       // landing_speed_x_mul
    }
    GroundModule(0x2710, 0x1);             // correct GROUND: walking off goes to Fall
    KineticModule(0, 0x6);
    KineticModule(0x11, 0x3, vx * mul, 0.0f);
    KineticModule(0x10, 0x3, edge_hi_p(0.12f, 0.06f), 0.0f);   // landing_brake_x
    KineticModule(0xb, 0x3);
    edge_hi_cliff_mode(0);
    if (edge_hi_charged)
    {
        MotionModule(0x1, 0x238, 0, 1.0f); // SpecialHi2End
    }
    else
    {
        MotionModule(0x1, 0x236, 0, 1.0f); // SpecialHi1End
    }
}

// 0be60: the air end
void edge_hi_end_air_main()
{
    float vx;
    float vy;
    float mul;
    edge_hi_rot_target = edge_hi_rot;
    vx = KineticModuleF(0xa, 0x3);
    vy = edge_hi_vy();
    mul = edge_hi_p(0.4f, 0.9f);           // rush_end_speed_mul
    GroundModule(0x2710, 0x5);
    KineticModule(0, 0xa);
    KineticModule(0x11, 0x3, vx * mul, 0.0f);
    KineticModule(0x10, 0x3, 0.02f, 0.0f); // rush_end_brake_x
    KineticModule(0xb, 0x3);
    KineticModule(0x11, 0x1, vy * mul);    // the rush's y into gravity (inferred) x the same mul
    KineticModule(0xf, 0x1, -0.12f);       // rush_end_gravity_accel
    KineticModule(0x14, 0x1, WorkModuleF(0, 0x3000019));
    KineticModule(0xb, 0x1);
    KineticModule(0x11, 0x2, 0.0f, 0.0f);
    KineticModule(0xc, 0x2);
    edge_hi_control = 0;
    edge_hi_cliff_mode(0x4);               // pre: cliff 1728 (ON_DROP_BOTH_SIDES, inferred)
    if (edge_hi_charged)
    {
        MotionModule(0x1, 0x23f, 0, 1.0f); // SpecialAirHi2End
    }
    else
    {
        MotionModule(0x1, 0x23e, 0, 1.0f); // SpecialAirHi1End
    }
}

// 15510 / 14b30
void edge_hi_end_loop()
{
    float f;
    f = MotionModuleF(0x1);
    if (edge_hi_end_air == 0)
    {
        if (edge_hi_charged == 0)
        {
            edge_tr_bd_step();   // Blade Dash's line on through the slide (test 128)
        }
        if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))   // cancel 27 / 56
        {
            return;
        }
        if (global18 == 0x2)
        {
            func_16(0xe, 0);
            return;
        }
        if (MotionModule(0x2712))
        {
            func_16(0, 0);
            return;
        }
        return;
    }
    if (edge_hi_charged)                   // game_specialairhi2end: NONE at 1, ALWAYS_BOTH_SIDES at 6
    {
        if (f >= 6.0f)
        {
            edge_hi_cliff_mode(0x2);
        }
        else if (f >= 1.0f)
        {
            edge_hi_cliff_mode(0);
        }
    }
    if (edge_hi_charged == 0)
    {
        edge_tr_bd_step();   // Blade Dash's: on while he moves the slash's way (test 128)
    }
    else if (edge_hi_vy() > 0.0f)
    {
        edge_tr_step(0);                   // the trail: on while he rises (test 123)
    }
    else
    {
        edge_tr_step(0x1);                 // ... it ends as he begins to fall
    }
    if (func_56())
    {
        return;
    }
    if (global18 == 0)
    {
        func_16(0x19, 0);
        return;
    }
    if (edge_hi_charged == 0 && f >= edge_hi_air_cut())
    {
        func_16(0xe, 0);                   // Blade Dash: Fall the frame before the animation turns to falling (test 116)
        return;
    }
    if (MotionModule(0x2712))
    {
        if (edge_hi_charged)
        {
            func_16(0x10, 0);
        }
        else
        {
            func_16(0xe, 0);               // Blade Dash: a normal fall (test 113; Ultimate: FallSpecial)
        }
        return;
    }
    edge_hi_pitch();
    // ENABLE_CONTROL (both air ends' game scripts at frame 18): drift with max speed x
    // control_speed_x_max_mul 0.5 (control_accel_x_mul 0.5 not applied: no Smash 4 op known)
    if (edge_hi_control == 0 && f >= 18.0f)
    {
        edge_hi_control = 0x1;
        KineticModule(0xe, 0x2, 0, 0.0f, 0.0f, 0, 0, 0);
        KineticModule(0x6, 0x2, 0.5f);
        KineticModule(0xb, 0x2);
    }
}

void edge_hi_end_main()
{
    edge_hi_cliff = 0xffffffff;
    if (edge_hi_end_air)
    {
        edge_hi_end_air_main();
    }
    else
    {
        edge_hi_end_ground_main();
    }
    global20 = 0;
    func_78(edge_hi_end_loop);
}

// 0ba00 / 0c700
void edge_hi_end_end()
{
    if (edge_hi_charged == 0 && global6 == 0xe && edge_tr_running())
    {
        WorkModule(0, 20.0f, 0x0f000328);  // Blade Dash's line on into Fall (his per-frame hook: test 128)
    }
    else
    {
        edge_tr_step(0x1);
    }
    edge_hi_line_kill();
    edge_hi_pitch_reset();
    if (edge_hi_end_air)
    {
        edge_hi_landing_frame();
    }
}

void edge_hi_end()
{
    if (global4 == 0x154)
    {
        edge_hi_start_end();
    }
    else if (global4 == 0x159)
    {
        edge_hi_rush_end();
    }
    else
    {
        edge_hi_end_end();
    }
}

// exec (out of hitlag): 03650 the start's button check (Octaslash = special held until DECIDED_RUSH, the
// start scripts' frame 18), 038b0 / 03930 the rush counter (+ the ExeFS speed hook)
void edge_hi_exec()
{
    if (global4 == 0x154)
    {
        if (MotionModuleF(0x1) < 18.0f && ControlModule(0x2712, 0x1) == 0)
        {
            edge_hi_charged = 0;
        }
    }
    else if (global4 == 0x159)
    {
        edge_hi_count++;
        edge_hi_hit_check();
        if (edge_hi_held())
        {
            edge_hi_steer();               // test 113
        }
        if (edge_hi_charged && (float)edge_hi_count > 15.0f)
        {
            WorkModule(0, WorkModuleF(0, edge_hi_timer_var()) - 1.0f, edge_hi_timer_var());
        }
        edge_hi_rush_speed();
    }
}

// exec_stop (in hitlag): 02ac0 / 02c60 / 02c90 / 02cc0, the pitch applied again
void edge_hi_exec_stop()
{
    if (global4 == 0x159)
    {
        edge_hi_hit_check();
    }
    if (global4 != 0x15a || edge_hi_end_air)   // the ground end has none (reset as the rush ended)
    {
        edge_hi_pitch_apply();
    }
}

// LandingFallSpecial 0x19's init: the common one (func_586: LandingFallSpecial over the landing frames),
// then Ultimate's 03d40: straight out of Octaslash's rush, SpecialHi2Landing (0x232, its landing hit)
void edge_hi_landing_init()
{
    float l;
    func_586();
    if (global5 == 0x159 && edge_hi_charged)
    {
        l = WorkModuleF(0, 0);
        if (l <= 0.0f)
        {
            l = 56.0f;
        }
        MotionModule(0x1, 0x232, 0, (float)MotionModule(0, 0x232) / l);
    }
}

// ---- Sephiroth's down special: Scintilla (fighters/edge/specials.md "Down special"), Ultimate's status code
// (lua2cpp_edge.nro, the spec's function addresses f_7203e<addr>) and its native counter (ExeFS FighterEdge
// 0x9e02f0 / 0x9e05b0 / 0x9e11f0) in Zelda's three Phantom Slash statuses (her phantom article is no longer
// generated; its files are kept):
//   0x155 STANCE (FIGHTER_STATUS_KIND_SPECIAL_LW: pre 0c790, main 0cb70, loop 143b0, end 0cec0)
//   0x15B HIT, the slash that releases the flash, countered or not (0xe2b4: 0d1f0 / 0d5f0 / 13fb0)
//   0x15C END, the shield broken (0xe2b8: 0d770 / 0db70 / 11f00)
// All three run f_123d0 (the air physics: edge_lw_frame) each frame. Ultimate keeps the status work across
// them (KEEP_ALL): globals here. Params: vl.prc param_special_lw (written in: his vl file is Zelda's layout).
// The shield is the native cave's (tools/edge_counter_cave.py, docs/native-notes.md): his shield group 1, a
// capsule r 6 from (0, 2, 8.3) to (0, 20, 8.3) (special_lw_shield_data), switched on here from the stance's
// frame 7 (game_speciallw's SHIELD_ON) until the stance ends. A hit on it: status float 0x01000006 = its
// damage d, flag 0x21000010 on, flag 0x21000011 on for a projectile (the cave cancels the hit's damage and
// knockback; this MSC changes the status: d > shield_max 25 -> END, else HIT).
// Motions straight through MotionModule (func_22 adds Zelda's custom-move offset): 0x241 / 0x245 SpecialLw /
// SpecialAirLw, 0x249 / 0x24D SpecialLwHit / SpecialAirLwHit, 0x251 / 0x255 SpecialLwEnd / SpecialAirLwEnd
// (Zelda's SpecialLw / Loop / Attack slots: ultimate_fighter.py MOTION_STANDINS).
// Kinetic energies: 1 gravity, 2 control, 3 stop.
int   edge_lw_shield;     // the shield group is on (frame 7 of the stance until it ends)
int   edge_lw_countered;  // 0xe3a4 IS_HIT_SHIELD: a hit landed on the shield
int   edge_lw_proj;       // that hit was a projectile's (hitstop 10, not 20)
float edge_lw_dmg;        // its damage d (shield_max - the shield's HP, 0x1000007)
int   edge_lw_control;    // 0xe390 ENABLE_CONTROL_X reached (the game scripts' frame: here the motion's)
int   edge_lw_fall;       // 0xe398 ENABLE_FALL_SPEED reached
int   edge_lw_float;      // 0xe3a8: the air counter's slowed fall applied
int   edge_lw_fired;      // the flash generated
int   edge_lw_xlu;        // the countered slash's intangibility is on (WHOLE_HIT XLU, frames 0-11)
float edge_lw_rate;       // the motion rate set (the whiff's FT_MOTION_RATE)

// the effect ids MSC uses (edge_effects.json; tools/edge_specials_build.py writes the id in when it compiles
// this file; 0: not in his bank yet, the call is left out)
int edge_lw_fx_shield() { return 0; } // fx edge_senkou_shield
int edge_lw_fx_break2() { return 0; } // fx edge_senkou_shield_break2

int edge_lw_motion(int ground)
{
    if (global18 == 0x2)
    {
        return ground + 0x4;
    }
    return ground;
}

int edge_lw_ground_motion()
{
    if (global4 == 0x15b)
    {
        return 0x249;
    }
    if (global4 == 0x15c)
    {
        return 0x251;
    }
    return 0x241;
}

// gravity (energy 1): the special start's (air_accel_y x start_accel_y_mul_air 0.8, the fall capped at
// air_speed_y_stable x start_max_speed_y_mul_air 0.25), x shield_speed_y_mul_air 0.2 once countered in the air
// (f_123d0 @12de8), his own from ENABLE_FALL_SPEED (@12d18)
void edge_lw_gravity()
{
    float g;
    float m;
    g = WorkModuleF(0, 0x3000018);
    m = WorkModuleF(0, 0x3000019);
    if (edge_lw_fall == 0)
    {
        g = g * 0.8f;
        m = m * 0.25f;
        if (edge_lw_float)
        {
            g = g * 0.2f;
            m = m * 0.2f;
        }
    }
    KineticModule(0xf, 0x1, -g);
    KineticModule(0x14, 0x1, m);
}

// ENABLE_CONTROL_X in the air (f_123d0 @1248c): the stop energy off, drift (energy 2) seeded with the x speed,
// max speed x control_max_speed_x_mul_air_flag_enable 0.6 (its accel x 0.3 not applied: no Smash 4 op known)
void edge_lw_drift(float vx)
{
    KineticModule(0x11, 0x3, 0.0f, 0.0f);
    KineticModule(0xc, 0x3);
    KineticModule(0xe, 0x2, 0, 0.0f, 0.0f, 0, 0, 0);
    KineticModule(0x11, 0x2, vx, 0.0f);
    KineticModule(0x6, 0x2, 0.6f);
    KineticModule(0xb, 0x2);
}

// sub_set_special_start_common_kinetic_setting("param_special_lw") (and again when the situation changes,
// x speed kept: xmul 1): ground x speed x start_speed_x_mul_ground 0.6, brake 0.1; air x speed x 0.6, brake
// 0.009, y speed kept (x 1.0), no drift (start_control_* 0) unless ENABLE_CONTROL_X, edge_lw_gravity()
void edge_lw_kinetic(float xmul)
{
    float vx;
    float vy;
    vx = KineticModuleF(0, 0xffffffff);
    vy = KineticModuleF(0x1, 0xffffffff);
    if (global18 == 0x2)
    {
        GroundModule(0x2710, 0x5);
        KineticModule(0, 0xa);
        if (edge_lw_control)
        {
            edge_lw_drift(vx * xmul);
        }
        else
        {
            KineticModule(0x11, 0x3, vx * xmul, 0.0f);
            KineticModule(0x10, 0x3, 0.009f, 0.0f);
            KineticModule(0xb, 0x3);
            KineticModule(0x11, 0x2, 0.0f, 0.0f);
            KineticModule(0xc, 0x2);
        }
        KineticModule(0x11, 0x1, vy);
        edge_lw_gravity();
        KineticModule(0xb, 0x1);
    }
    else
    {
        GroundModule(0x2710, 0x9);   // Zelda's own down special's ground correction (func_2298)
        KineticModule(0, 0x6);
        KineticModule(0x11, 0x3, vx * xmul, 0.0f);
        KineticModule(0x10, 0x3, 0.1f, 0.0f);
        KineticModule(0xb, 0x3);
    }
}

// f_123d0 and the loops' sub_change_motion_by_situation: each frame of the three statuses. ctrl / fall: the
// motion frames of the game scripts' ENABLE_CONTROL_X / ENABLE_FALL_SPEED
void edge_lw_frame(float ctrl, float fall)
{
    float f;
    float vy;
    int m;
    if (StatusModule(0x6) == 0 && (global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0))
    {
        edge_lw_kinetic(1.0f);
        m = edge_lw_ground_motion();
        m = edge_lw_motion(m);
        MotionModule(0x3, m);
    }
    f = MotionModuleF(0x1);
    if (edge_lw_control == 0 && f >= ctrl)
    {
        edge_lw_control = 0x1;
        if (global18 == 0x2)
        {
            vy = KineticModuleF(0, 0xffffffff);
            edge_lw_drift(vy);
        }
    }
    if (edge_lw_fall == 0 && f >= fall)
    {
        edge_lw_fall = 0x1;
        if (global18 == 0x2)
        {
            edge_lw_gravity();
        }
    }
    if (global18 != 0x2)
    {
        return;
    }
    // countered in the air (not broken): the fall slowed to shield_speed_y_mul_air 0.2, once
    if (global4 == 0x15b && edge_lw_countered && edge_lw_fall == 0 && edge_lw_float == 0)
    {
        edge_lw_float = 0x1;
        vy = KineticModuleF(0x1, 0xffffffff);
        KineticModule(0x11, 0x1, vy * 0.2f);
        edge_lw_gravity();
    }
    // the rise capped at air_invoke_speed_y_limit 1.35 (@13658)
    vy = KineticModuleF(0x1, 0xffffffff);
    if (vy > 1.35f)
    {
        KineticModule(0x11, 0x1, 1.35f);
    }
}

void edge_lw_shield_off()
{
    if (edge_lw_shield)
    {
        ShieldModule(0, 0x2, 0, 0, 0x1);
        edge_lw_shield = 0;
    }
}

// the native per-frame (0x9e05b0) on a blocked hit: hitstop hit_stop_frame 20 (hit_stop_frame_shoot 10 for a
// projectile) and a shake (hit_shake_mul 0.15)
void edge_lw_hitstop()
{
    int n;
    n = 0x14;
    if (edge_lw_proj)
    {
        n = 0xa;
    }
    StopModule(0x2, n);
    ShakeModule(0, 0, n, 0, 0, 0.15f);
}

// the flash (article 8, weapon kind 0x18F, fighters/edge/weapons/flash.c): its tier through Zelda's side
// special custom slot (int 0x10000049, copied by Din's Fire's creation callback 0x02F97C90 into the weapon's
// 0x10000005), set while it is generated: 0 the whiff, 1-5 a counter at clamp(d / shield_damage_charge_max 18,
// 0, 1) = 0, .25, .5, .75, 1 (nearest)
void edge_lw_generate()
{
    int slot;
    int tier;
    float p;
    tier = 0;
    if (edge_lw_countered)
    {
        p = edge_lw_dmg / 18.0f;
        if (p < 0.0f)
        {
            p = 0.0f;
        }
        if (p > 1.0f)
        {
            p = 1.0f;
        }
        tier = 0x1 + (int)(p * 4.0f + 0.5f);
    }
    slot = WorkModule(0x6, 0x10000049);
    WorkModule(0x7, tier, 0x10000049);
    ArticleModule(0x2710, 0x8);
    WorkModule(0x7, slot, 0x10000049);
    edge_lw_fired = 0x1;
}

int edge_lw_pre()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1432, 0x1000, 0x400, 0x1000);   // Zelda's func_2299's
    return 0;
}

// ---- Zelda's Phantom with Scintilla (user, test 99: "make down special also charge Zelda's Phantom, and force it
// to activate if the counter is hit"; asked: hold B to charge, as Zelda's Phantom Slash). Her article 2 (`phantom`,
// her files in his folder) driven as her own statuses do (vanilla zelda.mscsb func_2300 - 2307): made at the
// stance's start (none if one is still out: 0x2717), its charging status (1) from the stance's frame 7 (the counter
// on), a frame of charge each frame B is held, its full-charge look (ArticleModule(0x2715, 2, 8 + slot)) at
// 7 x 7 frames (param 0x08000000: frames a level, 7 levels), and sent (the level in status float 0x1000006, then
// ArticleModule(0x271a, 2)) when down special is pressed again (test 104; B let go before), 240 frames after full
// charge (test 104; Zelda's 0x18000001: 60), or at once when the
// counter is hit. Since test 103 the charge runs in his per-frame hook (edge_lw_ph_tick, from func_82) whatever
// status he's in, so it can be held past the stance (tests 100 - 102 held the stance at frame 30 while it charged).
// Its state is in his VAR_16 - VAR_18 (the MSC's globals are full: port_check C5)
// his effects that never end by themselves (edge_effects.json sets with endless emitters, his bank) off whenever
// he isn't in the status they belong to (multi-instance bugs v1, the user: "Sephiroth still keeps the purple phantom
// release glow on his hand permanently after using down special"; their screenshot: a purple / blue glow on him).
// Ultimate's scripts start them and its status code ends them (port_check E10 lists the ones no script ends); here
// a status left by another way than the script that ends them (hit, grabbed, a release from any status) kept them:
// - Flare's charge (SpecialNStart's EFFECT_FOLLOWs on haver, edge_n_charge_off): Flare's status (0x152) only; it
//   ended only on the release / cancel / roll paths, not when the charge was cut (hit, grabbed, the Phantom's
//   release press);
// - edge_catch_handaura (haver; and its turned copy): the grab statuses 0x35 - 0x3B and the throw (0x3E): Ultimate's
//   CatchWait starts it and its ThrowF / ThrowHi / CatchCut scripts never end it (lua2cpp_edge), so a forward /
//   up throw or a grab break left it on his hand;
// - Scintilla's counter glow (edge_senkou_shield_success1 - 7): its hit status (0x15B) only (its script ends them at
//   frame 3).
// Off as Ultimate's EFFECT_OFF_KIND(false, true): emission stops, the particles play out
void edge_fx_sweep()
{
    if (global4 != 0x152)
    {
        edge_n_charge_off();
    }
    if ((global4 < 0x35 || global4 > 0x3b) && global4 != 0x3e)
    {
        EffectModule(0x2723, 0x3420029, 0, 0x1); // edge_catch_handaura
        EffectModule(0x2723, 0x3420098, 0, 0x1); // edge_catch_handaura@90,0,90
    }
    if (global4 != 0x15b)
    {
        EffectModule(0x2723, 0x3420079, 0, 0x1); // edge_senkou_shield_success1
        EffectModule(0x2723, 0x342007a, 0, 0x1); // edge_senkou_shield_success2
        EffectModule(0x2723, 0x342007b, 0, 0x1); // edge_senkou_shield_success3
        EffectModule(0x2723, 0x342007c, 0, 0x1); // edge_senkou_shield_success4
        EffectModule(0x2723, 0x342007d, 0, 0x1); // edge_senkou_shield_success5
        EffectModule(0x2723, 0x342007e, 0, 0x1); // edge_senkou_shield_success6
        EffectModule(0x2723, 0x342007f, 0, 0x1); // edge_senkou_shield_success7
    }
}

int edge_lw_ph_var() { return 0x0f000310; }     // VAR_16: 0 none, 1 made, 2 charging, 3 sent
int edge_lw_chg_var() { return 0x0f000311; }    // VAR_17: frames charged
int edge_lw_full_var() { return 0x0f000312; }   // VAR_18: 1 once fully charged
float edge_lw_ph_keep() { return 240.0f; }      // frames after full charge before it's forced out (user, test 107:
                                                // "when the Phantom is forcibly released": 240; test 104: 120)

// the down special inputs (func_43, func_58, func_675, func_1999) start the counter only when this is 1: not while
// the Phantom charges, so that press only sends it (user, test 105: "when down special is pressed again while
// Phantom is charging or charged Sephiroth cannot use his counter down special until after the Phantom is
// released")
int edge_lw_can_counter()
{
    if (WorkModuleF(0, 0x0f000310) == 2.0f)   // edge_lw_ph(): charging
    {
        return 0;
    }
    // sent and still out (test 106, the user: "Scintilla still isn't disabled while the Phantom is charging/being
    // released": his per-frame hook runs before the status loop's input checks, so the press had already sent it,
    // state 3, when they ran)
    if (WorkModuleF(0, 0x0f000310) == 3.0f && ArticleModule(0x2717, 0x2))
    {
        return 0;
    }
    return 0x1;
}

// he can act (the free statuses: Wait to TurnRunBrake 0x0 - 0x9, the jumps and falls 0xB - 0xF, crouching 0x11 - 0x15;
// or a move past its cancel frame): the Phantom goes on down special only then; otherwise on any special press, any
// or no direction (user, test 110: "allow the special button with any or no direction to be used to release the
// Phantom when Sephiroth is not actionable")
int edge_lw_free()
{
    if (edge_sn_out())
    {
        return 0;                      // the snake sword out (held forward air / up tilt): never (test 115, the user: it
                                       // couldn't be let go with a fighter on the sword: the held move can sit past
                                       // its cancel frame)
    }
    if (global4 <= 0x9 || global4 >= 0xb && global4 <= 0xf || global4 >= 0x11 && global4 <= 0x15)
    {
        return 0x1;
    }
    if (CancelModule(0x2713) == 0x1)
    {
        return 0x1;
    }
    return 0;
}

// a down special press sends it only from near the end of the counter move (user, test 105: "make it so the
// Phantom cannot be released until near the end of Sephiroth's counter down special"): not in the stance, from
// frame 42 of the slash (actionable at 52) / 32 of the break (42); outside them at once. A counter hit still sends
// it at once (test 99)
int edge_lw_ph_open()
{
    if (global4 == 0x155)
    {
        return 0;
    }
    if (global4 == 0x15b)
    {
        if (MotionModuleF(0x1) >= 42.0f)
        {
            return 0x1;
        }
        return 0;
    }
    if (global4 == 0x15c)
    {
        if (MotionModuleF(0x1) >= 32.0f)
        {
            return 0x1;
        }
        return 0;
    }
    return 0x1;
}
float edge_lw_ph_down() { return -0.5f; }

// special pressed: SELF_SPECIAL_PRESSED, or its raw bit (MSC button 15, 0x800) pressed, which the A+B smash setting
// doesn't take: with it on, B pressed while A is held (the held sword) gives smash, not special (test 119)
int edge_lw_special_pressed()
{
    if (WorkModuleF(0, 0x0f000109) == 1.0f || ControlModule(0x2710, 0xf))
    {
        return 0x1;
    }
    return 0;
}       // stick y at or below this with B pressed: down special again

float edge_lw_ph()
{
    return WorkModuleF(0, edge_lw_ph_var());
}

void edge_lw_ph_set(float v)
{
    WorkModule(0, v, edge_lw_ph_var());
}

void edge_lw_ph_start()
{
    if (edge_lw_ph() == 2.0f)
    {
        edge_lw_ph_send();             // this down special's press sends the one charging (no new one: it's out)
    }
    edge_lw_ph_set(0.0f);
    WorkModule(0, 0.0f, edge_lw_chg_var());
    WorkModule(0, 0.0f, edge_lw_full_var());
    if (ArticleModule(0x2717, 0x2))
    {
        return;                        // one still out (Zelda's flag 0x2100000f): none this time
    }
    ArticleModule(0x2710, 0x2);
    edge_lw_ph_set(1.0f);
}

// sent at the charge so far (func_2307): level = frames / frames-a-level, whole, at most 7, in status float
// 0x1000006 (the cave's damage slot: a hit's d is read before this), then ArticleModule(0x271a, 2)
void edge_lw_ph_send()
{
    float lv;
    float keep;
    if (edge_lw_ph() != 2.0f)
    {
        return;
    }
    lv = WorkModuleF(0, edge_lw_chg_var()) / WorkModuleF(0, 0x8000000);
    if (lv > 7.0f)
    {
        lv = 7.0f;
    }
    lv = (float)((int)lv);
    edge_lw_ph_target();
    keep = WorkModuleF(0, 0x1000006);  // whatever status he's in (test 103): its float put back after
    WorkModule(0, lv, 0x1000006);
    ArticleModule(0x271a, 0x2);
    BattleObject(0x55, 0x1, 0x1c);
    WorkModule(0, keep, 0x1000006);
    edge_lw_ph_set(3.0f);
}

// the Phantom's tracking (test 106): if the last fighter he hit (combat target 2) is in hitstun, its place goes in his
// VAR_31 for the Phantom's attack to take (weapons/phantom.c ph_track: 2^21 + (x + 512) * 1024 + (y + 512), whole
// units, |x|, |y| up to 511); else 0. VAR_31 is the held sword's run counter only while its articles are made
// a fighter held on his sword now (the snake block's edge_sn_s, held forward air / up tilt): its place packed with
// 2^22 (the Phantom follows it up and down, test 107: "make the Phantom track opponents vertically when held by
// Sephiroth's snake sword"), else 0
int edge_lw_ph_held()
{
    int slot;
    float x;
    float y;
    if (edge_sn_out() == 0)
    {
        return 0;                              // the sword isn't out: its per-slot places aren't live (test 110)
    }
    slot = 1;
    while (slot <= 0x8)
    {
        if (edge_sn_s(slot) >= 0.0f)
        {
            x = WorkModuleF(0, 0x0f000020 + 0x4 * (slot - 1));   // POS_SLOTn_X / Y
            y = WorkModuleF(0, 0x0f000021 + 0x4 * (slot - 1));
            if (x < -511.0f)
            {
                x = -511.0f;
            }
            if (x > 511.0f)
            {
                x = 511.0f;
            }
            if (y < -511.0f)
            {
                y = -511.0f;
            }
            if (y > 511.0f)
            {
                y = 511.0f;
            }
            return 0x400000 + (int)(x + 512.5f) * 0x400 + (int)(y + 512.5f);
        }
        slot = slot + 1;
    }
    return 0;
}

float edge_lw_ph_near() { return 15.0f; }       // the hitstun tracking only for a fighter this near him (test 109: 15;
                                                // test 108: 10)

void edge_lw_ph_target()
{
    float lr;
    float x;
    float y;
    float ox;
    float oy;
    int code;
    code = edge_lw_ph_held();
    if (code != 0)
    {
        WorkModule(0, (float)code, 0x0f00031f);
        return;
    }
    // in hitstun and within 10 of him (test 108, the user: "the tracking for opponents in hitstun (except when being
    // hit by snake sword) only applies horizontally to opponents within 10 units of Sephiroth"; the Phantom takes x
    // only from this code)
    ox = WorkModuleF(0, 0x0f000055);              // LASTHIT_OFFSET_X / _Y: the fighter less him
    oy = WorkModuleF(0, 0x0f000056);
    if (WorkModuleF(0, 0x0f000050) > 0.0f && ox * ox + oy * oy <= edge_lw_ph_near() * edge_lw_ph_near())   // LASTHIT_HITSTUN
    {
        lr = PostureModuleF(0);
        x = PostureModuleF(0x1) + lr * WorkModuleF(0, 0x0f000055);   // LASTHIT_OFFSET_X (along his facing)
        y = PostureModuleF(0x2) + WorkModuleF(0, 0x0f000056);
        if (x < -511.0f)
        {
            x = -511.0f;
        }
        if (x > 511.0f)
        {
            x = 511.0f;
        }
        if (y < -511.0f)
        {
            y = -511.0f;
        }
        if (y > 511.0f)
        {
            y = 511.0f;
        }
        code = 0x200000 + (int)(x + 512.5f) * 0x400 + (int)(y + 512.5f);
    }
    WorkModule(0, (float)code, 0x0f00031f);
}

// the Phantom's slash is out (weapons/phantom.c ph_hit_report: -(2^21 + the slash's middle) in his VAR_31): a fighter
// held on the sword with its middle (feet + 8) within edge_lw_ph_hit_r of it is let go, their stage collision back, so
// they fly from its hit (test 120, the user: "when Phantom hits a held opponent, they get released"; tests 121 / 122:
// only that one, not test 120's any damage to any held one; test 122: the slash's place, as the Phantom can't read its
// own hit)
float edge_lw_ph_hit_r() { return 14.0f; }

void edge_lw_ph_lets_go()
{
    float v;
    int c;
    int ix;
    float x;
    float y;
    float dx;
    float dy;
    int slot;
    v = WorkModuleF(0, 0x0f00031f);
    if (v > -2097152.0f)
    {
        return;
    }
    WorkModule(0, 0.0f, 0x0f00031f);
    if (edge_sn_out() == 0)
    {
        return;
    }
    c = (int)(-v) - 0x200000;
    ix = c / 0x400;
    x = (float)(ix - 0x200);
    y = (float)(c - ix * 0x400 - 0x200);
    slot = 1;
    while (slot <= 0x8)
    {
        if (edge_sn_s(slot) >= 0.0f)
        {
            dx = WorkModuleF(0, 0x0f000020 + 0x4 * (slot - 1)) - x;   // POS_SLOTn_X / Y
            dy = WorkModuleF(0, 0x0f000021 + 0x4 * (slot - 1)) + 8.0f - y;
            if (dx * dx + dy * dy <= edge_lw_ph_hit_r() * edge_lw_ph_hit_r())
            {
                edge_sn_ground(slot, 5.0f);     // stage collision back (air)
                edge_sn_s_set(slot, -1.0f);
            }
        }
        slot = slot + 1;
    }
}

// made but not sent (the stance interrupted): it goes (func_2302 / 2307: status 4)
void edge_lw_ph_drop()
{
    if (edge_lw_ph() == 1.0f || edge_lw_ph() == 2.0f)
    {
        ArticleModule(0x2714, 0x2, 0x4);
    }
    edge_lw_ph_set(0.0f);
}

// the stance's frame 7 (the counter on): the Phantom into its charging status (the press that started the stance is
// long over by then, so it doesn't send it)
void edge_lw_ph_frame(float f)
{
    if (edge_lw_ph() == 1.0f && f >= 7.0f)
    {
        ArticleModule(0x2714, 0x2, 0x1);       // its charging status (func_2302)
        edge_lw_ph_set(2.0f);
    }
}

// every frame, whatever status he's in, actionable or not (func_82, his per-frame hook global14; in hitlag too, the
// charge counting only outside it: user, test 104, "I want to be able to release Phantom when Sephiroth isn't
// actionable"): the Phantom charges
// and goes when down special is pressed again or 240 frames past full charge (test 107), so it can be held after the stance,
// actionable or not (user, test 103: "make it so Phantom can be held after it begins, even when Sephiroth isn't
// actionable"; tests 100 - 102 held the stance at frame 30 while it charged). KO'd: it goes
void edge_lw_ph_tick()
{
    float c;
    float per;
    int held;
    int any;
    // any special press sends it only if he couldn't act this frame AND the one before (test 115, the user: "Phantom
    // now releases on any special button pressed rather than down special": a special started from neutral reads its
    // press on the frame his status is already the special's). VAR_13: 1 if he could act last frame
    any = 0;
    if (edge_lw_free() == 0 && WorkModuleF(0, 0x0f00030d) == 0.0f)
    {
        any = 0x1;
    }
    WorkModule(0, (float)edge_lw_free(), 0x0f00030d);
    // hit while it's out (charging, or sent and still there): it goes (user, test 104: "if Sephiroth is hit while
    // Phantom is out, it should disappear (if he's not in the middle of countering)": a hit his counter takes puts
    // him in no damage status). Damage statuses: 0x45 - 0x4B (Damage ... DamageFlyTop), 0x41 CaptureDamage, 0x57
    // DownDamage
    if (edge_lw_ph() >= 1.0f && (global4 >= 0x45 && global4 <= 0x4b || global4 == 0x41 || global4 == 0x57))
    {
        if (ArticleModule(0x2717, 0x2))
        {
            ArticleModule(0x2714, 0x2, 0x4);
        }
        edge_lw_ph_set(0.0f);
        return;
    }
    edge_lw_ph_lets_go();
    if (edge_lw_ph() == 3.0f && ArticleModule(0x2717, 0x2))
    {
        // sent and still out: a fighter held on his sword kept up to date for it to follow (test 107); none, his
        // code (2^22 and up only: VAR_31 is the sword's run counter while its articles are made) taken back
        held = edge_lw_ph_held();
        if (held != 0)
        {
            WorkModule(0, (float)held, 0x0f00031f);
        }
        else if (WorkModuleF(0, 0x0f00031f) >= 4194304.0f)
        {
            WorkModule(0, 0.0f, 0x0f00031f);
        }
        return;
    }
    if (edge_lw_ph() != 2.0f)
    {
        return;
    }
    if (global4 == 0xb1 || global4 == 0xb2)   // Dead / Rebirth
    {
        edge_lw_ph_drop();
        return;
    }
    per = WorkModuleF(0, 0x8000000);
    c = WorkModuleF(0, edge_lw_chg_var());
    if (!global3)                              // the charge counts outside hitlag; the press is read in it too
    {
        c = c + 1.0f;
        WorkModule(0, c, edge_lw_chg_var());
    }
    if (c >= per * 7.0f && WorkModuleF(0, edge_lw_full_var()) == 0)
    {
        ArticleModule(0x2715, 0x2, 0x8 + WorkModule(0x6, 0x1000004b));   // full charge (func_2305)
        WorkModule(0, 1.0f, edge_lw_full_var());
    }
    // sent when down special is pressed again (SELF_SPECIAL_PRESSED with the stick down: user, test 104, "change
    // Phantom's release to being when the down special is pressed again rather than released"; tests 100 - 103: B
    // let go), or 240 frames past full charge (test 107; test 104: 120; Zelda's param 0x18000001: 60)
    if ((edge_lw_special_pressed() && (WorkModuleF(0, 0x0f000111) <= edge_lw_ph_down() || any)
         && edge_lw_ph_open())
        || c >= per * 7.0f + edge_lw_ph_keep())
    {
        edge_lw_ph_send();
    }
}

// 143b0: the stance's frames
void edge_lw_loop()
{
    if (WorkModule(0x10, 0x21000010))
    {
        // a hit on the shield (the cave's flag): its damage kept at once (the status floats may reset)
        edge_lw_dmg = WorkModuleF(0, 0x1000006);
        edge_lw_proj = WorkModule(0x10, 0x21000011);
        edge_lw_countered = 0x1;
        edge_lw_shield_off();
        edge_lw_ph_send();             // the counter hit: the Phantom out at once, charged so far
        if (edge_lw_dmg > 25.0f)       // shield_max: broken
        {
            func_16(0x15c, 0);
        }
        else
        {
            func_16(0x15b, 0);
        }
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0x15b, 0);             // no hit: the whiff slash
        return;
    }
    if (edge_lw_shield == 0 && MotionModuleF(0x1) >= 7.0f)
    {
        ShieldModule(0, 0x2, 0, 0x1, 0x1);   // game_speciallw frame 7: SHIELD_ON
        edge_lw_shield = 0x1;
    }
    edge_lw_ph_frame(MotionModuleF(0x1));
    edge_lw_frame(1000.0f, 1000.0f);
}

// 0cb70
void edge_lw_main()
{
    edge_lw_shield = 0;
    edge_lw_countered = 0;
    edge_lw_proj = 0;
    edge_lw_dmg = 0.0f;
    edge_lw_control = 0;
    edge_lw_fall = 0;
    edge_lw_float = 0;
    edge_lw_fired = 0;
    edge_lw_xlu = 0;
    edge_lw_rate = 1.0f;
    WorkModule(0x2711, 0x21000010);
    edge_lw_kinetic(0.6f);
    MotionModule(0x1, edge_lw_motion(0x241), 0, 1.0f);
    edge_lw_ph_start();
    global20 = 0;
    func_78(edge_lw_loop);
}

// the whiff's game script: frames 1-5 at FT_MOTION_RATE 2 (half speed), 30-50 at 1.15
void edge_lw_whiff_rate(float f)
{
    float r;
    r = 1.0f;
    if (f >= 1.0f && f < 5.0f)
    {
        r = 0.5f;
    }
    else if (f >= 30.0f && f < 50.0f)
    {
        r = 0.8695652f;
    }
    if (r != edge_lw_rate)
    {
        edge_lw_rate = r;
        MotionModule(0x4, r);
    }
}

// 13fb0: the slash's frames (countered: control at 26, fall at 28; whiff 15 / 20; actionable at 52)
void edge_lw_hit_loop()
{
    float f;
    f = MotionModuleF(0x1);
    if (f >= 52.0f && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
        }
        else
        {
            func_16(0xe, 0);
        }
        return;
    }
    if (edge_lw_fired == 0 && f >= 7.0f)
    {
        edge_lw_generate();            // game_speciallwhit frame 7: generate_article(FLASH)
    }
    if (edge_lw_countered)
    {
        if (edge_lw_xlu && f >= 12.0f)
        {
            HitModule(0x2710, 0);      // frame 12: WHOLE_HIT(NORMAL)
            edge_lw_xlu = 0;
        }
        edge_lw_frame(26.0f, 28.0f);
    }
    else
    {
        edge_lw_whiff_rate(f);
        edge_lw_frame(15.0f, 20.0f);
    }
}

// 0d5f0 (+ the scripts' frame 0: countered, SET_SPEED_EX(0, 0) and WHOLE_HIT(XLU); the native hitstop)
void edge_lw_hit_main()
{
    WorkModule(0x2711, 0x21000010);
    edge_lw_control = 0;
    edge_lw_fall = 0;
    edge_lw_float = 0;
    edge_lw_fired = 0;
    edge_lw_xlu = 0;
    edge_lw_rate = 1.0f;
    MotionModule(0x1, edge_lw_motion(0x249), 0, 1.0f);
    if (edge_lw_countered)
    {
        KineticModule(0x11, 0x3, 0.0f, 0.0f);
        KineticModule(0x11, 0x2, 0.0f, 0.0f);
        if (global18 == 0x2)
        {
            KineticModule(0x11, 0x1, 0.0f);
        }
        HitModule(0x2710, 0x2);
        edge_lw_xlu = 0x1;
        edge_lw_hitstop();
    }
    global20 = 0;
    func_78(edge_lw_hit_loop);
}

// 11f00: the broken shield's frames (control and fall at 18, actionable at 42)
void edge_lw_break_loop()
{
    float f;
    f = MotionModuleF(0x1);
    if (f >= 42.0f && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            func_16(0, 0);
        }
        else
        {
            func_16(0xe, 0);
        }
        return;
    }
    edge_lw_frame(18.0f, 18.0f);
}

// 0db70 (+ game_speciallwend frame 0: SET_SPEED_EX(-1.4, 0) on the ground, (-0.8, 0.8) in the air; the
// native hitstop)
void edge_lw_break_main()
{
    float lr;
    WorkModule(0x2711, 0x21000010);
    edge_lw_control = 0;
    edge_lw_fall = 0;
    edge_lw_float = 0;
    edge_lw_xlu = 0;
    edge_lw_rate = 1.0f;
    MotionModule(0x1, edge_lw_motion(0x251), 0, 1.0f);
    lr = PostureModuleF(0);
    if (global18 == 0x2)
    {
        KineticModule(0x11, 0x3, -0.8f * lr, 0.0f);
        KineticModule(0x11, 0x1, 0.8f);
    }
    else
    {
        KineticModule(0x11, 0x3, -1.4f * lr, 0.0f);
    }
    edge_lw_hitstop();
    global20 = 0;
    func_78(edge_lw_break_loop);
}

// 0cec0 (the stance's end; HIT's and END's return 0): into END the shield effect stops; any exit but HIT /
// END (grabbed, hit from behind...) kills it and plays effect_speciallwinterrupt (edge_senkou_shield_break2 on
// top at (0, 13, 12) x 0.85). The shield group goes off with the stance. HIT / END: the intangibility and the
// whiff's rate put back
void edge_lw_end()
{
    int id;
    if (global4 == 0x155)
    {
        if (edge_lw_ph() == 1.0f)
        {
            edge_lw_ph_drop();         // interrupted before it charged (frame 7): it goes; charging: goes on
        }
        if (edge_lw_rate != 1.0f)
        {
            MotionModule(0x4, 1.0f);
            edge_lw_rate = 1.0f;
        }
        edge_lw_shield_off();
        id = edge_lw_fx_shield();
        if (global6 == 0x15c)
        {
            if (id != 0)
            {
                EffectModule(0x2723, id, 0, 0);
            }
        }
        else if (global6 != 0x15b)
        {
            if (id != 0)
            {
                EffectModule(0x2723, id, 0x1, 0x1);
            }
            id = edge_lw_fx_break2();
            if (id != 0)
            {
                EffectModule(0x2710, id, 0, 0, 13.0f, 12.0f, 0, 0, 0, 0.85f, 0, 0, 0, 0, 0, 0, 0x1);
            }
        }
        return;
    }
    if (edge_lw_xlu)
    {
        HitModule(0x2710, 0);
        edge_lw_xlu = 0;
    }
    if (edge_lw_rate != 1.0f)
    {
        MotionModule(0x4, 1.0f);
        edge_lw_rate = 1.0f;
    }
}

// ---- Sephiroth's side special: Shadow Flare (fighters/edge/specials.md "Side special"), from Ultimate's status
// code (lua2cpp_edge: START 08940 / 1ac20, HOLD 08f00 / 035d0 / 1a4c0, SHOT 09510 / 1a060), vl.prc
// param_special_s and the ExeFS's flare1 generation (main.bin 0x9e1770). Zelda's Din's Fire statuses carry it:
// 0x153 START (SpecialSStart 0x219 / SpecialAirSStart 0x225), 0x157 HOLD (SpecialSLoop 0x21D / 0x229: Ultimate's
// special_s_hold), 0x158 SHOT (SpecialSEnd 0x221 / 0x22D: Ultimate's special_s). Kinetics: Ultimate's
// sub_set_special_start_common_kinetic_setting(param_special_s), re-applied on a ground / air change (the motion
// swapped, its frame kept). The shot: flare1 (article 6, weapon 0x18D, weapons/flare1.c), made on SHOT's frame 8
// (Ultimate's game_specials generate_article); the hold count and the situation go to it through Zelda's side
// special custom slot (int 0x10000049, copied by Din's Fire's creation callback into the weapon's 0x10000005).
int edge_s_hold;      // K[0xe3b0]: the hold's frames (Ultimate's status work int 0x11000005)
int edge_s_fired;

int edge_s_motion(int ground, int air)
{
    if (global18 == 0x2)
    {
        return air;
    }
    return ground;
}

// param_special_s start_*: ground x speed x 0.5, brake 0.1; air x speed x 0.6, brake 0.008, y speed x 0.75,
// gravity and max fall x 0.85 (start_accel_y_mul_air / start_max_speed_y_mul_air: his air_accel_y 0x3000018,
// air_speed_y_stable 0x3000019). Air control (accel x 0.1, max x 0.6) is left off (approximation: no MSC op
// for its multipliers is known)
void edge_s_kinetic()
{
    float vx;
    float vy;
    vx = KineticModuleF(0, 0xffffffff);
    vy = KineticModuleF(0x1, 0xffffffff);
    if (global18 == 0x2)
    {
        GroundModule(0x2710, 0x5);
        KineticModule(0, 0xa);
        KineticModule(0x11, 0x3, vx * 0.6f, 0.0f);
        KineticModule(0x10, 0x3, 0.008f, 0.0f);
        KineticModule(0xb, 0x3);
        KineticModule(0x11, 0x1, vy * 0.75f);
        KineticModule(0xf, 0x1, -WorkModuleF(0, 0x3000018) * 0.85f);
        KineticModule(0x15, 0x1, WorkModuleF(0, 0x3000019) * 0.85f);
        KineticModule(0xb, 0x1);
        KineticModule(0x11, 0x2, 0.0f, 0.0f);
        KineticModule(0xc, 0x2);
    }
    else
    {
        GroundModule(0x2710, 0x9);          // Din's Fire's ground correction (Zelda's func_2263)
        KineticModule(0, 0x6);
        KineticModule(0x11, 0x3, vx * 0.5f, 0.0f);
        KineticModule(0x10, 0x3, 0.1f, 0.0f);
        KineticModule(0xb, 0x3);
    }
}

// every loop: on a ground / air change the motion swapped (frame kept) and the kinetics again; the air's gravity
void edge_s_situation(int ground, int air)
{
    if (StatusModule(0x6) == 0 && (global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0))
    {
        edge_s_kinetic();
        MotionModule(0x3, edge_s_motion(ground, air));
    }
    if (global18 == 0x2)
    {
        KineticModule(0xf, 0x1, -WorkModuleF(0, 0x3000018) * 0.85f);
    }
}

// 1ac20
// test 129, the user: "make side special's startup slightly faster": the start (7 frames) and the shot up to its
// frame 8 (the flare made) at edge_s_quick() (Ultimate's x 1), set every frame (a ground / air swap re-sets the motion)
float edge_s_quick() { return 1.25f; }

void edge_s_start_loop()
{
    edge_s_situation(0x219, 0x225);
    MotionModule(0x4, edge_s_quick());
    if (MotionModule(0x2712))
    {
        func_16(0x157, 0);
        return;
    }
}

// 08940
void edge_s_start_main()
{
    edge_s_hold = 0;
    edge_s_fired = 0;
    edge_s_kinetic();
    MotionModule(0x1, edge_s_motion(0x219, 0x225), 0, 1.0f);
    global20 = 0;
    func_78(edge_s_start_loop);
}

// 1aad0: turned round when leaving the hold with the stick back (stick x . lr <= common turn_stick_x -0.2;
// global48 is the stick's screen x, as the reverse tilts read it: test 64 compared it alone, turning him whenever
// it was held left)
void edge_s_turn()
{
    if (global48 * PostureModuleF(0) <= -0.2f)
    {
        PostureModule(0x2710);              // reverse_lr
        PostureModule(0x2);                 // update_rot_y_lr
    }
}

// 035d0 (exec: the count) + 1a4c0: the shot on the special button's release (after its first frame) or at
// hold_max 27
void edge_s_hold_loop()
{
    edge_s_situation(0x21d, 0x229);
    edge_s_hold += 1;
    if (ControlModule(0x2713, 0x1) && edge_s_hold > 0x1 || edge_s_hold >= 0x1b)
    {
        edge_s_turn();
        func_16(0x158, 0);
        return;
    }
}

// 08f00
void edge_s_hold_main()
{
    edge_s_hold = 0;
    MotionModule(0x1, edge_s_motion(0x21d, 0x229), 0, 1.0f);
    global20 = 0;
    func_78(edge_s_hold_loop);
}

// game_specials frame 8: generate_article(FLARE1); the hold's frames (0 - 27) + 32 in the air to the weapon
void edge_s_generate()
{
    int slot;
    int v;
    v = edge_s_hold;
    if (v > 0x1b)
    {
        v = 0x1b;
    }
    if (global18 == 0x2)
    {
        v += 0x20;
    }
    slot = WorkModule(0x6, 0x10000049);
    WorkModule(0x7, v, 0x10000049);
    WorkModule(0, 0.0f, edge_tr_place_var());     // its line (test 148, edge_s_line_tick): no place yet, a line to make
    WorkModule(0, 0.0f, edge_tr_pen_var());
    ArticleModule(0x2710, 0x6);
    WorkModule(0x7, slot, 0x10000049);
    edge_s_fired = 0x1;
}

// 1a060: actionable from the motion's cancel frame (CancelModule::is_enable_cancel: Ultimate's motion_list
// special_s / special_air_s cancel 31, vl group 1 byte 2 of 0x221 / 0x22D), at the motion's end Wait or Fall
// (no special fall, no landing lag)
void edge_s_shot_loop()
{
    edge_s_situation(0x221, 0x22d);
    if (MotionModuleF(0x1) < 8.0f)
    {
        MotionModule(0x4, edge_s_quick());   // to the flare quicker (test 129); its cancel frame 31 as before
    }
    else
    {
        MotionModule(0x4, 1.0f);
    }
    if (edge_s_fired == 0 && MotionModuleF(0x1) >= 8.0f)
    {
        edge_s_generate();
    }
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0x2)
        {
            func_16(0xe, 0);
            return;
        }
        func_16(0, 0);
        return;
    }
}

// 09510
void edge_s_shot_main()
{
    edge_s_fired = 0;
    WorkModule(0, -1.0f, edge_tr_pen_var());      // no shot line till its shot is made (test 148, edge_s_generate)
    MotionModule(0x1, edge_s_motion(0x221, 0x22d), 0, 1.0f);
    global20 = 0;
    func_78(edge_s_shot_loop);
}

// ==== SNAKE FAIR (tools/edge_snake_msc.py) ====
// Sephiroth: held forward air, the extending sword (fighters/edge/snake_fair.md)
float edge_sn_s1;
float edge_sn_s2;
float edge_sn_s3;
float edge_sn_s4;
float edge_sn_s5;
float edge_sn_s6;
float edge_sn_s7;
float edge_sn_s8;
float edge_sn_oh1;
float edge_sn_oh2;
float edge_sn_oh3;
float edge_sn_oh4;
float edge_sn_oh5;
float edge_sn_oh6;
float edge_sn_oh7;
float edge_sn_oh8;
float edge_sn_ov1;
float edge_sn_ov2;
float edge_sn_ov3;
float edge_sn_ov4;
float edge_sn_ov5;
float edge_sn_ov6;
float edge_sn_ov7;
float edge_sn_ov8;

float edge_sn_s(int k)
{
    if (k == 1)
    {
        return edge_sn_s1;
    }
    if (k == 2)
    {
        return edge_sn_s2;
    }
    if (k == 3)
    {
        return edge_sn_s3;
    }
    if (k == 4)
    {
        return edge_sn_s4;
    }
    if (k == 5)
    {
        return edge_sn_s5;
    }
    if (k == 6)
    {
        return edge_sn_s6;
    }
    if (k == 7)
    {
        return edge_sn_s7;
    }
    if (k == 8)
    {
        return edge_sn_s8;
    }
    return 0.0f;
}

void edge_sn_s_set(int k, float v)
{
    if (k == 1)
    {
        edge_sn_s1 = v;
    }
    if (k == 2)
    {
        edge_sn_s2 = v;
    }
    if (k == 3)
    {
        edge_sn_s3 = v;
    }
    if (k == 4)
    {
        edge_sn_s4 = v;
    }
    if (k == 5)
    {
        edge_sn_s5 = v;
    }
    if (k == 6)
    {
        edge_sn_s6 = v;
    }
    if (k == 7)
    {
        edge_sn_s7 = v;
    }
    if (k == 8)
    {
        edge_sn_s8 = v;
    }
}

float edge_sn_oh(int k)
{
    if (k == 1)
    {
        return edge_sn_oh1;
    }
    if (k == 2)
    {
        return edge_sn_oh2;
    }
    if (k == 3)
    {
        return edge_sn_oh3;
    }
    if (k == 4)
    {
        return edge_sn_oh4;
    }
    if (k == 5)
    {
        return edge_sn_oh5;
    }
    if (k == 6)
    {
        return edge_sn_oh6;
    }
    if (k == 7)
    {
        return edge_sn_oh7;
    }
    if (k == 8)
    {
        return edge_sn_oh8;
    }
    return 0.0f;
}

void edge_sn_oh_set(int k, float v)
{
    if (k == 1)
    {
        edge_sn_oh1 = v;
    }
    if (k == 2)
    {
        edge_sn_oh2 = v;
    }
    if (k == 3)
    {
        edge_sn_oh3 = v;
    }
    if (k == 4)
    {
        edge_sn_oh4 = v;
    }
    if (k == 5)
    {
        edge_sn_oh5 = v;
    }
    if (k == 6)
    {
        edge_sn_oh6 = v;
    }
    if (k == 7)
    {
        edge_sn_oh7 = v;
    }
    if (k == 8)
    {
        edge_sn_oh8 = v;
    }
}

float edge_sn_ov(int k)
{
    if (k == 1)
    {
        return edge_sn_ov1;
    }
    if (k == 2)
    {
        return edge_sn_ov2;
    }
    if (k == 3)
    {
        return edge_sn_ov3;
    }
    if (k == 4)
    {
        return edge_sn_ov4;
    }
    if (k == 5)
    {
        return edge_sn_ov5;
    }
    if (k == 6)
    {
        return edge_sn_ov6;
    }
    if (k == 7)
    {
        return edge_sn_ov7;
    }
    if (k == 8)
    {
        return edge_sn_ov8;
    }
    return 0.0f;
}

void edge_sn_ov_set(int k, float v)
{
    if (k == 1)
    {
        edge_sn_ov1 = v;
    }
    if (k == 2)
    {
        edge_sn_ov2 = v;
    }
    if (k == 3)
    {
        edge_sn_ov3 = v;
    }
    if (k == 4)
    {
        edge_sn_ov4 = v;
    }
    if (k == 5)
    {
        edge_sn_ov5 = v;
    }
    if (k == 6)
    {
        edge_sn_ov6 = v;
    }
    if (k == 7)
    {
        edge_sn_ov7 = v;
    }
    if (k == 8)
    {
        edge_sn_ov8 = v;
    }
}


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
        ModelModule(0, 1003, edge_sn_hidden(), edge_sn_hidden(), edge_sn_hidden());
    }
    else
    {
        ModelModule(0, 1003, 1.0f, 1.0f, 1.0f);
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
    while (i < 12 / 2)
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

// the articles: 12 runs (each takes its number from VAR_31) and the point
void edge_sn_generate()
{
    int k;
    WorkModule(0, 0.0f, 0x0f00031f);
    k = 0;
    while (k < 12)
    {
        ArticleModule(0x2710, 9);
        k = k + 1;
    }
    ArticleModule(0x2710, 10);
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
        if (edge_sn_since < edge_sn_turn_wait() || edge_sn_n >= 12 || want == opp)
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
    while (slot <= 8)
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
    while (slot <= 8)
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
    while (slot <= 8)
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
    while (slot <= 8)
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

// attack held: SELF_ATTACK, or its raw bit (MSC button 14, 0x200), which the A+B smash setting doesn't clear: with it
// on, B pressed while A is held turns both into smash (0x20) and clears attack's 0x1 until both are let go, so the hold
// ended (test 119, the user: "pressing special while holding up tilt or forward air ends the hold")
int edge_sn_attack()
{
    if (WorkModuleF(0, 0x0f000100) == 1.0f || ControlModule(0x2712, 0xe))
    {
        return 0x1;
    }
    return 0;
}

void edge_sn_init()
{
    edge_sn_reset();
    edge_sn_move = 0;
    if (MotionModule(0x7) == edge_sn_motion() && edge_sn_attack())
    {
        edge_sn_state = 0x1;
    }
}

// the up tilt status's main (func_278): the hold check starts if attack is held
void edge_sn_init_hi3()
{
    edge_sn_reset();
    edge_sn_move = 0x1;
    if (edge_sn_attack())
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
    while (k <= 12)
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
// special after the hilt reaches Sephiroth, specifically if he hit them with any part of the attack"): if the move hit
// anyone (his own hits, SELF_HIT, or the point's catch), the side special input (global24 0x2000, as func_43 reads it;
// the status's own transition terms left out) goes into side special (0x153) from the frame the sword is back at the
// hilt (state 5 on; test 128 opened it from the return, state 4: test 129, the user: "The side B cancel should wait
// until the frame it hits the hilt"; side special's startup made faster instead, edge_s_quick). And
// on the ground the grab input (global24 0x20000000, no item held, as the ground statuses read it) goes into a grab
// (0x35 Catch, as func_46 / Wait's; test 128 / 129 used 0x37, the dash grab: test 130) (test 128: "allow snakesword's hilt return to be cancelled into grab if on the ground"), on the same
// terms as side special's (test 129, the user: "The same rules that apply to side special's cancel should apply to
// grab": the hilt, and the move hit; test 128 took it from the return, hit or not). Run first in the aerial / up
// tilt loops: 1 if it did
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
    if (edge_sn_state >= 0x5 && WorkModuleF(0, edge_sn_hit_var()) == 1.0f && global18 == 0
        && (global24 & 0x20000000) != 0 && ItemModule(0x4) == 0)
    {
        func_16(0x35, 0x1);
        return 0x1;
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
    if (edge_sn_attack())                       // attack held
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

// ==== SNAKE FAIR END ====
