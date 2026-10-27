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
            if (func_72(global26))
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
                func_16(0x155, 0x1);
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
            if (func_72(global26))
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
                func_16(0x155, 0x1);
                return 0x1;
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
    sv_set_mem(0x1, 0x2, 0x29, func_323);
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
    sv_set_mem(0x1, 0x2, 0x34, func_334);
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
    sv_set_mem(0x1, 0x3, 0x19, func_586);
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
    brave_n_stored = 0;     // Hero: a stored Frizz charge doesn't outlive the stock
    brave_rebirth();        // nor his MP spent, buffs or an open Command Selection menu
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
    func_78(func_279);
}

void func_279()
{
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
    if (MotionModule(0x2712) == 0x1)
    {
        func_16(0x12, 0);
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
    var1 = rolloff_aerial(ControlModule(0x10));  // Hero: a C-stick flick buffered in a roll-off (fix 62)
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
    func_78(func_319);
}

void func_316()
{
    WorkModule(0x9, 0x11000003);
    if (WorkModule(0x6, 0x11000003) <= WorkModule(0x6, 0x120001f0))
    {
        func_103();
    }
    func_550();
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
    if (func_318())
    {
        return;
    }
    func_555();
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
    if (global6 == 0xe || StatusModule(0x1) == 0x2) // roll-off: slid off an edge (into Fall, or an attack
    {                                               // buffered off the edge: Hero's test, fix 62) -> no air speed cap
        WorkModule(0x13, 0x1, 0x20000044);
        global63 = 1; // roll-off: Fall's main scales the carried speed (rolloff_fall_speed)
        global64 = 1; // roll-off: the cap comes back when the stick lets go of the roll's way (rolloff_hold_update)
        rolloff_dir = 0;    // Hero's test: the way his speed goes, from his movement (rolloff_hold_update)
        rolloff_air_t = 0x8;
        rolloff_airborne = 0x1;
    }
    else
    {
        rolloff_cstick = 0;
    }
    func_383();
}

void func_382()
{
    if (global6 == 0xe || StatusModule(0x1) == 0x2) // roll-off: slid off an edge (into Fall, or an attack
    {                                               // buffered off the edge: Hero's test, fix 62) -> no air speed cap
        WorkModule(0x13, 0x1, 0x20000044);
        global63 = 1; // roll-off: Fall's main scales the carried speed (rolloff_fall_speed)
        global64 = 1; // roll-off: the cap comes back when the stick lets go of the roll's way (rolloff_hold_update)
        rolloff_dir = 0;    // Hero's test: the way his speed goes, from his movement (rolloff_hold_update)
        rolloff_air_t = 0x8;
        rolloff_airborne = 0x1;
    }
    else
    {
        rolloff_cstick = 0;
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
    // roll-off (Hero's test, user): Fall's end no longer puts the air speed cap back; it stays off into
    // the next air action for as long as the stick holds the roll's way (rolloff_hold_update)
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
                    func_16(0x155, 0x1);
                    return 0x1;
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
                    func_16(0x155, 0x1);
                    return;
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
    global26 = brave_hi_can;    // Hero: Woosh once per airtime (brave_hi_can)
    global37 = 0;
    global11 = func_79;
    global12 = func_80;
    global14 = brave_frame;     // Hero: func_82, then his MP, buffs and panel (brave_frame)
    global13 = func_81;
    global21 = func_107;
    sys_0(0x7, func_36);
    BattleObject(0x32, 0x2f, 0x10000083, 0x20000078);
}

void func_2242()
{
    global7 = 0x172;
    func_2240();
    func_2243();
    func_2241();
    func_2244();
}

void func_2243()
{
    sv_set_mem(0x1, 0, 0, func_2263);
    sv_set_mem(0x1, 0x1, 0x8c, func_2264);
    sv_set_mem(0x1, 0x2, 0x8c, func_2265);
    sv_set_mem(0x1, 0, 0x16d, func_2255);
    sv_set_mem(0x1, 0x1, 0x16d, func_2256);
    sv_set_mem(0x1, 0x2, 0x16d, func_2258);
    sv_set_mem(0x1, 0, 0x16e, func_2259);
    sv_set_mem(0x1, 0x1, 0x16e, func_2260);
    sv_set_mem(0x1, 0x2, 0x16e, func_2262);
    sv_set_mem(0x1, 0x1, 0x25, func_2278);
    sv_set_mem(0x1, 0x1, 0x26, func_2285);
    sv_set_mem(0x1, 0x2, 0x26, func_2288);
    sv_set_mem(0x1, 0x1, 0x27, func_2279);
    sv_set_mem(0x1, 0x1, 0x28, func_2280);
    sv_set_mem(0x1, 0x1, 0x29, func_2281);
    sv_set_mem(0x1, 0x1, 0x2a, func_2282);
    sv_set_mem(0x1, 0x1, 0x75, func_2283);
    sv_set_mem(0x1, 0x1, 0x56, func_2284);
    sv_set_mem(0x1, 0x1, 0x87, func_2289);
    sv_set_mem(0x1, 0x1, 0x34, func_2252);
    sv_set_mem(0x1, 0x2, 0x34, func_2253);
    sv_set_mem(0x1, 0x1, 0x2b, func_2266);
    sv_set_mem(0x1, 0x1, 0x31, func_2270);
    sv_set_mem(0x1, 0x1, 0x2e, func_2274);
    sv_set_mem(0x1, 0x2, 0x2b, func_2267);
    sv_set_mem(0x1, 0x2, 0x31, func_2271);
    sv_set_mem(0x1, 0x2, 0x2e, func_2275);
    sv_set_mem(0x1, 0x2, 0x2c, func_2268);
    sv_set_mem(0x1, 0x2, 0x32, func_2272);
    sv_set_mem(0x1, 0x2, 0x2f, func_2276);
    sv_set_mem(0x1, 0x2, 0x2d, func_2269);
    sv_set_mem(0x1, 0x2, 0x33, func_2273);
    sv_set_mem(0x1, 0x2, 0x30, func_2277);
    sv_set_mem(0x1, 0, 0x152, brave_n_pre);   // Hero: Frizz / Frizzle / Kafrizz (was Thunder func_2291-func_2294)
    sv_set_mem(0x1, 0x1, 0x152, brave_n_main);
    sv_set_mem(0x1, 0x2, 0x152, brave_n_end);
    sv_set_mem(0x1, 0, 0x157, func_2295);
    sv_set_mem(0x1, 0x1, 0x157, func_2296);
    sv_set_mem(0x1, 0x2, 0x157, func_2298);
    sv_set_mem(0x1, 0, 0x158, func_2299);
    sv_set_mem(0x1, 0x1, 0x158, func_2300);
    sv_set_mem(0x1, 0x2, 0x158, func_2302);
    sv_set_mem(0x1, 0, 0x159, func_2303);
    sv_set_mem(0x1, 0x1, 0x159, func_2304);
    sv_set_mem(0x1, 0x2, 0x159, func_2306);
    sv_set_mem(0x1, 0, 0x15a, func_2307);
    sv_set_mem(0x1, 0x1, 0x15a, func_2308);
    sv_set_mem(0x1, 0x2, 0x15a, func_2311);
    sv_set_mem(0x1, 0, 0x15b, func_2312);
    sv_set_mem(0x1, 0x1, 0x15b, func_2313);
    sv_set_mem(0x1, 0x2, 0x15b, func_2315);
    sv_set_mem(0x1, 0, 0x153, brave_s_pre);   // Hero: Zap / Zapple / Kazap (was Arcfire func_2316-func_2319)
    sv_set_mem(0x1, 0x1, 0x153, brave_s_main);
    sv_set_mem(0x1, 0x2, 0x153, brave_n_end);
    sv_set_mem(0x1, 0, 0x154, brave_hi_pre);  // Hero: Woosh / Swoosh / Kaswoosh (was Elwind func_2320-func_2323)
    sv_set_mem(0x1, 0x1, 0x154, brave_hi_main);
    sv_set_mem(0x1, 0x2, 0x154, brave_n_end);
    sv_set_mem(0x1, 0, 0x15c, func_2324);
    sv_set_mem(0x1, 0x1, 0x15c, func_2325);
    sv_set_mem(0x1, 0x2, 0x15c, func_2327);
    sv_set_mem(0x1, 0, 0x15d, func_2328);
    sv_set_mem(0x1, 0x1, 0x15d, func_2329);
    sv_set_mem(0x1, 0x2, 0x15d, func_2331);
    sv_set_mem(0x1, 0, 0x155, brave_lw_pre);  // Hero: Command Selection (was Nosferatu func_2332-func_2335)
    sv_set_mem(0x1, 0x1, 0x155, brave_lw_main);
    sv_set_mem(0x1, 0x2, 0x155, brave_lw_end);
    sv_set_mem(0x1, 0, 0x15e, func_2336);
    sv_set_mem(0x1, 0x1, 0x15e, func_2337);
    sv_set_mem(0x1, 0x2, 0x15e, func_2340);
    sv_set_mem(0x1, 0, 0x15f, func_2341);
    sv_set_mem(0x1, 0x1, 0x15f, func_2342);
    sv_set_mem(0x1, 0x2, 0x15f, func_2344);
    sv_set_mem(0x1, 0, 0x156, func_2345);
    sv_set_mem(0x1, 0x1, 0x156, func_2346);
    sv_set_mem(0x1, 0x2, 0x156, func_2349);
    sv_set_mem(0x1, 0, 0x16f, func_2368);
    sv_set_mem(0x1, 0x1, 0x16f, func_2369);
    sv_set_mem(0x1, 0x2, 0x16f, func_2372);
    sv_set_mem(0x1, 0, 0x170, func_2373);
    sv_set_mem(0x1, 0x1, 0x170, func_2374);
    sv_set_mem(0x1, 0x2, 0x170, func_2376);
    sv_set_mem(0x1, 0, 0x163, func_2355);
    sv_set_mem(0x1, 0x1, 0x163, func_2356);
    sv_set_mem(0x1, 0x2, 0x163, func_2358);
    sv_set_mem(0x1, 0, 0x171, func_2359);
    sv_set_mem(0x1, 0x1, 0x171, func_2360);
    sv_set_mem(0x1, 0x2, 0x171, func_2362);
    sv_set_mem(0x1, 0, 0x164, func_2363);
    sv_set_mem(0x1, 0x1, 0x164, func_2364);
    sv_set_mem(0x1, 0x2, 0x164, func_2367);
    sv_set_mem(0x1, 0, 0x161, func_2351);
    sv_set_mem(0x1, 0x1, 0x161, func_2352);
    sv_set_mem(0x1, 0x2, 0x161, func_2354);
}

void func_2244()
{
    global51 = 0x21f;
    global52 = 0x257;
    global53 = 0x25f;
    global54 = 0x277;
    global55 = 0x28f;
}

void func_2245(int arg0)
{
    int var1;
    int var2;
    float var3;
    float var4;
    float var5;
    int var6;
    float var7;
    if (arg0 == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        if (global18 == 0)
        {
            func_20(0);
            GroundModule(0x2710, WorkModule(0x6, 0x11000006));
            KineticModule(0, WorkModule(0x6, 0x11000004));
            var1 = WorkModule(0x6, 0x11000002);
            var2 = WorkModule(0x6, 0x11000003);
            if (!arg0)
            {
                if (0x152 == global4 || 0x157 == global4 || 0x158 == global4 || 0x15a == global4 || 0x159 == global4 || 0x15b == global4 || 0x153 == global4 || 0x155 == global4 || 0x15e == global4 || 0x15f == global4)
                {
                    EffectModule(0x2710, 0x1000006, 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0.5f + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0);
                }
            }
        }
        else
        {
            func_20(0x2);
            GroundModule(0x2710, WorkModule(0x6, 0x11000007));
            KineticModule(0, WorkModule(0x6, 0x11000005));
            if (0x152 == global4 || 0x157 == global4)
            {
                var3 = -0.08900000154972076f;
                KineticModule(0xf, 0x1, var3 * WorkModuleF(0, 0x5000008));
                var4 = KineticModuleF(0x1, 0x1);
                var5 = WorkModuleF(0, 0x5000009);
                if (var5 <= var4)
                {
                    KineticModule(0x11, 0x1, var5);
                }
            }
            var1 = WorkModule(0x6, 0x11000003);
            var2 = WorkModule(0x6, 0x11000002);
        }
        var6 = MotionModule(0x7);
        if (!func_32(var6, var1) || var1 == 0x257 || var1 == 0x25b)
        {
            var7 = 1.0f;
            if (arg0 == 0)
            {
                var7 = MotionModuleF(0x9);
            }
            if (func_32(var6, var2))
            {
                func_23(var1);
                MotionModule(0x4, var7);
            }
            else
            {
                func_22(var1, 0, var7);
            }
        }
    }
}

int func_2246()
{
    int var0;
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return 0x1;
    }
    if (MotionModule(0x2712))
    {
        if (global18 == 0)
        {
            var0 = 0;
        }
        else
        {
            var0 = 0xe;
        }
        func_16(var0, 0);
        return 0x1;
    }
    return 0;
}

void func_2247()
{
    int var0;
    int var1;
    var0 = WorkModule(0x6, 0x1000008c);
    if (0 < var0)
    {
        if (WorkModule(0x10, 0x2000007a))
        {
            
        }
        else
        {
            VisibilityModule(0x2711, 0, 0x1);
            WorkModule(0x2710, 0x2000007a);
        }
    }
    else
    {
        // Hero: int 0x1000008E is his buffs' marker (brave_frame), not Robin's Levin Sword recharge
        var1 = WorkModule(0x6, 0x14000003);
    }
}

void func_2248()
{
    printf("-----use_thundersword()----------");
    WorkModule(0x7, WorkModule(0x6, 0x14000001), 0x1000008d);
    WorkModule(0xa, 0x1000008c);
    if (WorkModule(0x6, 0x1000008c) <= 0)
    {
        BattleObject(0x3ec, 0x7, 0x1, 0x10000091);
    }
}

void func_2249()
{
    func_2247();
    if (WorkModule(0x10, 0x2000007a))
    {
        func_2248();
    }
}

void func_2250()
{
    if (WorkModule(0x10, 0x2000007a))
    {
        VisibilityModule(0x2711, 0, 0);
        WorkModule(0x2711, 0x2000007a);
    }
}

int func_2251()
{
    printf("----------check_switchto_normalsword(%d)----", WorkModule(0x6, 0x1000008c));
    if (WorkModule(0x6, 0x1000008c) <= 0)
    {
        func_2250();
        return 0x1;
    }
    return 0;
}

void func_2252()
{
    int var0;
    int var1;
    func_314();
    var0 = WorkModule(0x6, 0x11000002);
    if (var0 != 0x68)
    {
        if (var0 == 0x69 || var0 == 0x6a)
        {
            var1 = ControlModule(0x4);
            if (ControlModule(0x2724))
            {
                var1 = 0;
            }
        }
        else if (var0 == 0x6b || var0 == 0x6c)
        {
            var1 = ControlModule(0x5);
            if (ControlModule(0x2724))
            {
                var1 = 0;
            }
        }
        if (var1 < 0x5)
        {
            func_2247();
            WorkModule(0x7, 0x1, 0x11000004);
        }
    }
    else
    {
        func_2250();
    }
    if (WorkModule(0x10, 0x2000007a))
    {
        func_2248();
    }
    func_78(func_319);
}

void func_2253()
{
    func_2251();
    func_334();
}

int func_2254()
{
    // Hero: no tome or Levin Sword to throw away (brave_keep_items)
    WorkModule(0x7, 0, 0x10000091);
    return 0;
}

void func_2255()
{
    printf("-----status_pre_ResurrectionThundersword");
}

void func_2256()
{
    printf("-----status_ResurrectionThundersword");
    BattleObject(0x3ec, 0x7, 0, 0x10000093);
    VisibilityModule(0x2711, 0, 0x1);
    WorkModule(0x2710, 0x2000007a);
    WorkModule(0x7, WorkModule(0x6, 0x14000001), 0x1000008d);
    func_22(0x295, 0, 1.0f);
    func_78(func_2257);
}

void func_2257()
{
    int var0;
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return 0x1;
    }
    var0 = StatusModule(0x6);
    if (!var0)
    {
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
        }
    }
}

void func_2258()
{
    
}

void func_2259()
{
    
}

void func_2260()
{
    int var0;
    int var1;
    BattleObject(0x3eb, 0x10000093, 0x10000092);
    var0 = WorkModule(0x6, 0x10000092);
    BattleObject(0x3ea, var0);
    BattleObject(0x3ec, var0, 0, 0x10000093);
    var1 = 0x32c001a;
    if (0 == var0)
    {
        EffectModule(0x2712, 0x32c001a, 0x18, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 1.0f + 0, 0);
    }
    else if (0x4 == var0)
    {
        EffectModule(0x2712, 0x32c001b, 0x18, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 1.0f + 0, 0);
    }
    else if (0x5 == var0)
    {
        EffectModule(0x2712, 0x32c001c, 0x18, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 1.0f + 0, 0);
    }
    else if (0x6 == var0)
    {
        EffectModule(0x2712, 0x32c001d, 0x18, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 1.0f + 0, 0);
    }
    func_22(0x296, 0, 1.0f);
    func_78(func_2261);
}

void func_2261()
{
    int var0;
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return 0x1;
    }
    var0 = StatusModule(0x6);
    if (!var0)
    {
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
        }
    }
}

void func_2262()
{
    
}

void func_2263()
{
    if (0 < func_670())
    {
        return 0x1;
    }
    if (0 < func_2254())
    {
        return 0x1;
    }
}

void func_2264()
{
    int var0;
    BattleObject(0x3eb, 0x10000091, 0x10000092);
    var0 = WorkModule(0x6, 0x10000092);
    if (0x7 == var0)
    {
        BattleObject(0x3ec, 0x7, 0, 0x10000091);
        WorkModule(0x7, 0x11e, 0x11000002);
        WorkModule(0x7, 0x11e, 0x11000003);
        CancelModule(0x2710);
    }
    else if (0xffffffff != var0)
    {
        BattleObject(0x3ec, var0, 0, 0x10000091);
        WorkModule(0x7, 0x11e, 0x11000002);
        WorkModule(0x7, 0x11e, 0x11000003);
        CancelModule(0x2710);
    }
    func_1182();
}

void func_2265()
{
    ItemModule(0x7, 0, 0, WorkModuleF(0, 0x300003d), 0x3);
    func_1187();
}

void func_2266()
{
    func_2249();
    func_286();
}

void func_2267()
{
    if (global6 != 0x2c && global6 != 0x2d)
    {
        func_2251();
    }
    func_325();
}

void func_2268()
{
    if (global6 != 0x2d)
    {
        func_2251();
    }
    func_326();
}

void func_2269()
{
    func_2251();
    func_327();
}

void func_2270()
{
    func_2249();
    func_295();
}

void func_2271()
{
    if (global6 != 0x32 && global6 != 0x33)
    {
        func_2251();
    }
    func_328();
}

void func_2272()
{
    if (global6 != 0x33)
    {
        func_2251();
    }
    func_329();
}

void func_2273()
{
    func_2251();
    func_330();
}

void func_2274()
{
    func_2249();
    func_303();
}

void func_2275()
{
    if (global6 != 0x2f && global6 != 0x30)
    {
        func_2251();
    }
    func_331();
}

void func_2276()
{
    if (global6 != 0x30)
    {
        func_2251();
    }
    func_332();
}

void func_2277()
{
    func_2251();
    func_333();
}

void func_2278()
{
    func_2250();
    func_263();
}

void func_2279()
{
    func_2250();
    func_272();
}

void func_2280()
{
    func_2250();
    brave_s3_main();
}

void func_2281()
{
    func_2250();
    func_278();
}

void func_2282()
{
    func_2250();
    func_281();
}

void func_2283()
{
    func_2250();
    func_167();
}

void func_2284()
{
    func_2250();
    func_949();
}

void func_2285()
{
    WorkModule(0xa, 0x1000008a);
    if (WorkModule(0x6, 0x1000008a) <= 0)
    {
        BattleObject(0x3ec, 0x5, 0x1, 0x10000091);
    }
    BattleObject(0x3ea, 0x5);
    WorkModule(0x7, WorkModule(0x6, 0x1700000a), 0x11000008);
    func_22(0x53, 0, 1.0f);
    func_78(func_2287);
}

void func_2286()
{
    int var0;
    var0 = WorkModule(0x6, 0x11000008);
    if (var0 <= 0)
    {
        if (WorkModule(0x6, 0x1000008a) <= 0)
        {
            WorkModule(0x2711, 0x21000015);
        }
        else
        {
            WorkModule(0xa, 0x1000008a);
            WorkModule(0x7, WorkModule(0x6, 0x1700000a), 0x11000008);
        }
    }
    else
    {
        WorkModule(0xa, 0x11000008);
    }
}

void func_2287()
{
    func_2286();
    func_337();
}

void func_2288()
{
    if (WorkModule(0x6, 0x1000008a) <= 0)
    {
        BattleObject(0x3ec, 0x5, 0x1, 0x10000091);
    }
    func_339();
}

void func_2289()
{
    func_2250();
    func_1948();
}

int func_2290(int arg0)
{
    if (0 == arg0)
    {
        return WorkModule(0x6, 0x15000004);
    }
    else if (0x1 == arg0)
    {
        return WorkModule(0x6, 0x15000005);
    }
    else if (0x2 == arg0)
    {
        return WorkModule(0x6, 0x15000006);
    }
    else if (0x3 == arg0)
    {
        return WorkModule(0x6, 0x15000007);
    }
    return 0;
}

int func_2291()
{
    printf("status_pre_SpecialN");
    func_69();
    printf("------------thunder kind(%d)", WorkModule(0x6, 0x10000085));
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1190, 0x1000, 0x80, 0x1000);
    if (WorkModule(0x6, 0x10000085) == 0x3)
    {
        StatusModule(0x2711, 0x159);
        return 0x1;
    }
    return 0;
}

void func_2292()
{
    printf("status_SpecialN");
    WorkModule(0x7, 0, 0x10000090);
    WorkModule(0x7, 0x21f, 0x11000002);
    WorkModule(0x7, 0x23b, 0x11000003);
    WorkModule(0x7, 0x6, 0x11000004);
    WorkModule(0x7, 0xa, 0x11000005);
    WorkModule(0x7, 0x2, 0x11000006);
    WorkModule(0x7, 0x5, 0x11000007);
    func_78(func_2293);
}

void func_2293()
{
    int var0;
    printf("sub_SpecialN");
    var0 = StatusModule(0x6);
    if (var0 == 0 && MotionModule(0x2712))
    {
        func_16(0x157, 0);
        return 0x1;
    }
    func_2245(var0);
}

void func_2294()
{
    
}

int func_2295()
{
    printf("status_pre_SpecialNHold");
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x190, 0, 0x80, 0);
    return 0;
}

void func_2296()
{
    int var0;
    float var1;
    int var2;
    printf("status_SpecialNHold");
    WorkModule(0x7, 0x223, 0x11000002);
    WorkModule(0x7, 0x23f, 0x11000003);
    WorkModule(0x7, 0x6, 0x11000004);
    WorkModule(0x7, 0xa, 0x11000005);
    WorkModule(0x7, 0x2, 0x11000006);
    WorkModule(0x7, 0x5, 0x11000007);
    WorkModule(0x16, 0x1e000027);
    WorkModule(0x16, 0x1e000028);
    var0 = WorkModule(0x6, 0x10000085);
    if (0x2 == var0)
    {
        var1 = WorkModuleF(0, 0x5000002);
        var2 = (int)var1;
        WorkModule(0x7, var2, 0x11000008);
    }
    else if (0x1 == var0)
    {
        var1 = WorkModuleF(0, 0x5000001);
        var2 = (int)var1;
        WorkModule(0x7, var2, 0x11000008);
    }
    else
    {
        WorkModule(0x7, 0, 0x11000008);
        BattleObject(0x3ea, var0);
    }
    func_78(func_2297);
}

void func_2297()
{
    int var0;
    printf("sub_SpecialNHold");
    var0 = StatusModule(0x6);
    if (global38 & 0x4)
    {
        func_16(0x158, 0x1);
        return 0x1;
    }
    if (global38 & 0x40)
    {
        if (0x2 != global18)
        {
            func_16(0x1b, 0x1);
        }
        else
        {
            func_16(0x22, 0x1);
        }
        return 0x1;
    }
    if (WorkModule(0x15, 0x1e000027) != 0)
    {
        if (0x2 != global18 && global31 & 0x4000)
        {
            func_16(0x20, 0x1);
            return 0x1;
        }
    }
    if (WorkModule(0x15, 0x1e000028) != 0)
    {
        if (0x2 != global18 && global31 & 0x8000)
        {
            func_16(0x21, 0x1);
            return 0x1;
        }
    }
    func_2245(var0);
    MotionModule(0x4, WorkModuleF(0, 0x30));
}

void func_2298()
{
    if (WorkModule(0x6, 0x10000085) == 0x3)
    {
        BattleObject(0x75);
    }
}

int func_2299()
{
    printf("status_pre_SpecialNShoot");
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x10192, 0, 0x80, 0);
    return 0;
}

void func_2300()
{
    int var0;
    int var1;
    int var2;
    printf("status_SpecialNShoot");
    var0 = WorkModule(0x6, 0x10000085);
    var1 = WorkModule(0x6, 0x10000083);
    var2 = func_2290(var0);
    if (0 < var1)
    {
        WorkModule(0x2710, 0x2100000f);
    }
    else
    {
        WorkModule(0x2711, 0x2100000f);
    }
    if (WorkModule(0x10, 0x2100000f))
    {
        WorkModule(0x7, var1 - var2, 0x10000083);
        if (WorkModule(0x6, 0x10000083) <= 0)
        {
            BattleObject(0x3ec, 0, 0x1, 0x10000091);
        }
    }
    else
    {
        BattleObject(0x3ea, 0xffffffff);
    }
    if (0 == var0)
    {
        WorkModule(0x7, 0x22b, 0x11000002);
        WorkModule(0x7, 0x247, 0x11000003);
    }
    else
    {
        WorkModule(0x7, 0x227, 0x11000002);
        WorkModule(0x7, 0x243, 0x11000003);
    }
    WorkModule(0x7, 0x6, 0x11000004);
    WorkModule(0x7, 0xa, 0x11000005);
    WorkModule(0x7, 0x2, 0x11000006);
    WorkModule(0x7, 0x5, 0x11000007);
    func_78(func_2301);
}

void func_2301()
{
    int var0;
    int var1;
    printf("sub_SpecialNShoot");
    var0 = StatusModule(0x6);
    if (var0 == 0 && func_2246())
    {
        return 0x1;
    }
    if (!WorkModule(0x10, 0x2100000f) && 9.0f <= global20)
    {
        if (!WorkModule(0x10, 0x2100000d))
        {
            EffectModule(0x2712, 0x32c0014, 0x11, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 1.0f + 0, 0x1);
            WorkModule(0x2710, 0x2100000d);
        }
    }
    if (WorkModule(0x10, 0x2100000e))
    {
        if (WorkModule(0x10, 0x2100000f))
        {
            BattleObject(0x3ed, 0, 0x10000092);
            var1 = WorkModule(0x6, 0x10000085);
            printf("FIGHTER_REFLET_INSTANCE_WORK_ID_INT_TEMP_MAGIC_KIND--(%d %d)--", WorkModule(0x6, 0x10000092), WorkModule(0x6, 0x15000000));
            if (0 != var1 || WorkModule(0x6, 0x10000092) < WorkModule(0x6, 0x15000000))
            {
                if (0x8 == global1)
                {
                    if (0 == var1)
                    {
                        SoundModule(0x2710, 0x8b50000);
                    }
                    else if (0x1 == var1)
                    {
                        SoundModule(0x2710, 0x8b50001);
                    }
                    else if (0x2 == var1)
                    {
                        SoundModule(0x2710, 0x8b50002);
                    }
                }
                else if (0 == var1)
                {
                    SoundModule(0x2710, 0x770001a);
                }
                else if (0x1 == var1)
                {
                    SoundModule(0x2710, 0x770001b);
                }
                else if (0x2 == var1)
                {
                    SoundModule(0x2710, 0x770001c);
                }
                ArticleModule(0x2710, 0x2);
            }
        }
        WorkModule(0x2711, 0x2100000e);
    }
    func_2245(var0);
}

void func_2302()
{
    WorkModule(0x7, 0, 0x10000085);
}

int func_2303()
{
    printf("status_pre_SpecialNTronStart");
    WorkModule(0x7, 0, 0x10000090);
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1190, 0, 0x80, 0);
    return 0;
}

void func_2304()
{
    int var0;
    int var1;
    int var2;
    printf("status_SpecialNTronStart");
    var0 = WorkModule(0x6, 0x10000085);
    var1 = func_2290(var0);
    var2 = WorkModule(0x6, 0x10000083);
    WorkModule(0x7, var2 - var1, 0x10000083);
    if (WorkModule(0x6, 0x10000083) <= 0)
    {
        BattleObject(0x3ec, 0, 0x1, 0x10000091);
    }
    BattleObject(0x3ea, 0x3);
    WorkModule(0x7, 0x22f, 0x11000002);
    WorkModule(0x7, 0x24b, 0x11000003);
    WorkModule(0x7, 0x6, 0x11000004);
    WorkModule(0x7, 0xa, 0x11000005);
    WorkModule(0x7, 0x2, 0x11000006);
    WorkModule(0x7, 0x5, 0x11000007);
    func_78(func_2305);
}

void func_2305()
{
    int var0;
    printf("sub_SpecialNTronStart");
    var0 = StatusModule(0x6);
    if (var0 == 0 && MotionModule(0x2712))
    {
        func_16(0x15a, 0);
        return 0x1;
    }
    func_2245(var0);
}

void func_2306()
{
    EffectModule(0x20, 0x1a);
    EffectModule(0x9, 0x32c0013, 0x1, 0);
    if (0x15a != global6)
    {
        WorkModule(0x7, 0, 0x10000085);
    }
}

int func_2307()
{
    printf("status_pre_SpecialNTronHold");
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x10192, 0, 0x80, 0);
    return 0;
}

void func_2308()
{
    printf("status_SpecialNTronHold");
    WorkModule(0x7, 0x233, 0x11000002);
    WorkModule(0x7, 0x24f, 0x11000003);
    WorkModule(0x7, 0x6, 0x11000004);
    WorkModule(0x7, 0xa, 0x11000005);
    WorkModule(0x7, 0x2, 0x11000006);
    WorkModule(0x7, 0x5, 0x11000007);
    WorkModule(0x7, 0, 0x11000008);
    WorkModule(0x2711, 0x2100000e);
    if (!StopModule(0x1))
    {
        func_2310();
    }
    global16 = func_2310;
    func_78(func_2309);
}

void func_2309()
{
    
}

void func_2310()
{
    int var0;
    int var1;
    printf("sub_SpecialNTronHold");
    var0 = StatusModule(0x6);
    var1 = WorkModule(0x6, 0x11000008);
    if (ControlModule(0x2713, 0x1))
    {
        WorkModule(0x2710, 0x2100000e);
    }
    if (WorkModule(0x6, 0x1500000b) < var1)
    {
        func_16(0x15b, 0x1);
        return 0x1;
    }
    if (WorkModule(0x10, 0x2100000e) && WorkModule(0x6, 0x1500000a) < var1)
    {
        func_16(0x15b, 0x1);
        return 0x1;
    }
    func_2245(var0);
    WorkModule(0x9, 0x11000008);
}

void func_2311()
{
    if (0x15b != global6)
    {
        WorkModule(0x7, 0, 0x10000085);
    }
}

int func_2312()
{
    printf("status_pre_SpecialNTronEnd");
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x190, 0, 0x80, 0);
    return 0;
}

void func_2313()
{
    printf("status_SpecialNTronEnd");
    WorkModule(0x7, 0x237, 0x11000002);
    WorkModule(0x7, 0x253, 0x11000003);
    WorkModule(0x7, 0x6, 0x11000004);
    WorkModule(0x7, 0xa, 0x11000005);
    WorkModule(0x7, 0x2, 0x11000006);
    WorkModule(0x7, 0x5, 0x11000007);
    func_78(func_2314);
}

void func_2314()
{
    int var0;
    printf("sub_SpecialNTronEnd");
    var0 = StatusModule(0x6);
    if (var0 == 0 && func_2246())
    {
        return 0x1;
    }
    func_2245(var0);
}

void func_2315()
{
    WorkModule(0x7, 0, 0x10000085);
    if (WorkModule(0x10, 0x2000007a))
    {
        VisibilityModule(0x2711, 0, 0x1);
    }
    else
    {
        VisibilityModule(0x2711, 0, 0);
    }
}

int func_2316()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x11412, 0x1000, 0x200, 0x1000);
    return 0;
}

void func_2317()
{
    float var0;
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return 0x1;
    }
    WorkModule(0x7, 0x257, 0x11000002);
    WorkModule(0x7, 0x25b, 0x11000003);
    WorkModule(0x7, 0x6, 0x11000004);
    WorkModule(0x7, 0xa, 0x11000005);
    WorkModule(0x7, 0x2, 0x11000006);
    WorkModule(0x7, 0x5, 0x11000007);
    WorkModule(0x7, 0x4, 0x10000090);
    var0 = WorkModuleF(0, 0x2f);
    if (var0 <= 0)
    {
        WorkModule(0x2711, 0x2100000f);
    }
    else
    {
        WorkModule(0x2710, 0x2100000f);
    }
    if (WorkModule(0x10, 0x2100000f))
    {
        WorkModule(0, var0 - 1.0f + 0, 0x2f);
        if (WorkModuleF(0, 0x2f) <= 0)
        {
            BattleObject(0x3ec, 0x4, 0x1, 0x10000091);
        }
        BattleObject(0x3ea, 0x4);
    }
    else
    {
        BattleObject(0x3ea, 0xffffffff);
    }
    func_78(func_2318);
}

void func_2318()
{
    int var0;
    var0 = StatusModule(0x6);
    if (var0 == 0 && func_2246())
    {
        return 0x1;
    }
    if (!var0)
    {
        if (!WorkModule(0x10, 0x2100000f) && 12.0f <= global20)
        {
            if (!WorkModule(0x10, 0x2100000d))
            {
                EffectModule(0x2712, 0x32c0014, 0x11, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 1.0f + 0, 0x1);
                WorkModule(0x2710, 0x2100000d);
            }
        }
        if (WorkModule(0x10, 0x2100000e))
        {
            if (WorkModule(0x10, 0x2100000f))
            {
                ArticleModule(0x2710, 0x4);
            }
            WorkModule(0x2711, 0x2100000e);
        }
    }
    func_2245(var0);
}

void func_2319()
{
    
}

void func_2320()
{
    int var0;
    printf("-----------------status_pre_SpecialHi()-----------------");
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x11422, 0x1000, 0x100, 0x1000);
    var0 = WorkModule(0x6, 0x1000008a);
    if (var0 < 0x1)
    {
        StatusModule(0x2711, 0x15d);
        return 0x1;
    }
    else
    {
        printf("SUCCEED!");
        return 0;
    }
}

void func_2321()
{
    printf("-----------------status_SpecialHi()-----------------");
    WorkModule(0x7, 0x5, 0x10000090);
    if (global18 == 0)
    {
        GroundModule(0x2710, 0x2);
        KineticModule(0, 0x6);
        func_22(0x25f, 0, 1.0f);
        WorkModule(0x2711, 0x20000079);
    }
    else
    {
        GroundModule(0x2710, 0x5);
        KineticModule(0, 0xa);
        func_22(0x26b, 0, 1.0f);
        WorkModule(0x2710, 0x20000079);
    }
    WorkModule(0xa, 0x1000008a);
    if (WorkModule(0x6, 0x1000008a) <= 0)
    {
        BattleObject(0x3ec, 0x5, 0x1, 0x10000091);
    }
    WorkModule(0, WorkModuleF(0, 0x700000d) + 0, 0);
    func_78(func_2322);
}

void func_2322()
{
    int var0;
    printf("-----------------sub_SpecialHi()-----------------");
    if (func_56())
    {
        return 0x1;
    }
    var0 = StatusModule(0x6);
    if (!var0)
    {
        if (global19 != 0 && global18 == 0)
        {
            func_16(0x19, 0);
            return 0x1;
        }
        if (MotionModule(0x2712))
        {
            func_16(0x10, 0);
            return 0x1;
        }
    }
}

void func_2323()
{
    
}

int func_2324()
{
    printf("status_pre_SpecialHi2");
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x10422, 0, 0x100, 0);
    return 0;
}

void func_2325()
{
    printf("-----------------status_SpecialHi2()-----------------");
    GroundModule(0x2710, 0x5);
    if (WorkModule(0x10, 0x20000079))
    {
        func_22(0x26f, 0, 1.0f);
    }
    else
    {
        func_22(0x263, 0, 1.0f);
    }
    WorkModule(0xa, 0x1000008a);
    if (WorkModule(0x6, 0x1000008a) <= 0)
    {
        BattleObject(0x3ec, 0x5, 0x1, 0x10000091);
    }
    func_78(func_2326);
}

void func_2326()
{
    int var0;
    printf("-----------------sub_SpecialHi2()-----------------");
    if (func_56())
    {
        return 0x1;
    }
    var0 = StatusModule(0x6);
    if (!var0)
    {
        if (global19 != 0 && global18 == 0)
        {
            func_16(0x19, 0);
            return 0x1;
        }
        if (MotionModule(0x2712))
        {
            func_16(0x10, 0);
            return 0x1;
        }
    }
}

void func_2327()
{
    printf("status_end_SpecialHi2");
}

int func_2328()
{
    printf("status_pre_SpecialHiFail");
    WorkModule(0x7, 0x5, 0x10000090);
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x10422, 0, 0x100, 0x1000);
    return 0;
}

void func_2329()
{
    printf("status_SpecialHiFail");
    if (global18 == 0)
    {
        GroundModule(0x2710, 0x2);
        KineticModule(0, 0x6);
        func_22(0x267, 0, 1.0f);
    }
    else
    {
        GroundModule(0x2710, 0x5);
        KineticModule(0, 0xa);
        func_22(0x273, 0, 1.0f);
    }
    BattleObject(0x3ea, 0xffffffff);
    func_78(func_2330);
}

void func_2330()
{
    int var0;
    printf("sub_SpecialHiFail");
    var0 = StatusModule(0x6);
    if (9.0f <= global20)
    {
        if (!WorkModule(0x10, 0x2100000d))
        {
            EffectModule(0x2712, 0x32c0014, 0x11, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 1.0f + 0, 0x1);
            WorkModule(0x2710, 0x2100000d);
        }
    }
    if (global19 != 0 && global18 == 0)
    {
        WorkModule(0, WorkModuleF(0, 0x700000d) + 0, 0);
        func_16(0x19, 0);
        return 0x1;
    }
    if (var0 == 0 && MotionModule(0x2712))
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

void func_2331()
{
    printf("status_end_SpecialHiFail");
}

int func_2332()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1432, 0x1000, 0x400, 0x1000);
    return 0;
}

void func_2333()
{
    WorkModule(0x7, 0x6, 0x10000090);
    WorkModule(0x7, 0x277, 0x11000002);
    WorkModule(0x7, 0x283, 0x11000003);
    WorkModule(0x7, 0x65, 0x11000004);
    WorkModule(0x7, 0x64, 0x11000005);
    WorkModule(0x7, 0x2, 0x11000006);
    WorkModule(0x7, 0x5, 0x11000007);
    WorkModule(0x7, 0x50000000, 0x11000008);
    AttackModule(0x2, 0x1);
    if (WorkModule(0x6, 0x10000086) <= 0)
    {
        WorkModule(0x2710, 0x2000007b);
    }
    else
    {
        WorkModule(0xa, 0x10000086);
        BattleObject(0x3ea, 0x6);
        if (WorkModule(0x6, 0x10000086) <= 0)
        {
            BattleObject(0x3ec, 0x6, 0x1, 0x10000091);
        }
    }
    func_78(func_2334);
}

void func_2334()
{
    int var0;
    int var1;
    int var2;
    var0 = StatusModule(0x6);
    if (sys_3A(0x2715, 0))
    {
        if (!BattleObject(0x3e8, WorkModuleF(0, 0x8000002), WorkModuleF(0, 0x8000003)))
        {
            sys_3A(0x2711, 0);
            sys_3A(0x2711, 0x1);
        }
    }
    if (var0 == 0 && MotionModule(0x2712))
    {
        var2 = WorkModule(0x6, 0x1100000b);
        if (!WorkModule(0x10, 0x2000007b) && 0x1 == var2)
        {
            var1 = 0x15e;
        }
        else
        {
            var1 = 0x15f;
        }
        func_16(var1, 0);
        return 0x1;
    }
    func_2245(var0);
}

void func_2335()
{
    
}

int func_2336()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x432, 0, 0x400, 0);
    return 0;
}

void func_2337()
{
    WorkModule(0x7, 0x27b, 0x11000002);
    WorkModule(0x7, 0x287, 0x11000003);
    WorkModule(0x7, 0x6, 0x11000004);
    WorkModule(0x7, 0x66, 0x11000005);
    WorkModule(0x7, 0x2, 0x11000006);
    WorkModule(0x7, 0x5, 0x11000007);
    WorkModule(0x7, 0, 0x11000009);
    WorkModule(0x2710, 0x21000010);
    AttackModule(0x2, 0x1);
    if (!StopModule(0x1))
    {
        func_2339();
    }
    global16 = func_2339;
    func_78(func_2338);
}

void func_2338()
{
    
}

void func_2339()
{
    int var0;
    float var1;
    int var2;
    int var3;
    float var4;
    int var5;
    int var6;
    var0 = StatusModule(0x6);
    if (var0 == 0)
    {
        var1 = WorkModuleF(0, 0x1000009) * -0.20000000298023224f;
        if (WorkModule(0x10, 0x2100000f) && 0x2 == global18)
        {
            printf("-------FIGHTER_REFLET_STATUS_SPECIAL_LW_CAPTURE_FLOAT_GAP_Y(%f)------------------", var1);
            KineticModule(0x11, 0x3, 0, var1);
        }
        else
        {
            KineticModule(0x11, 0x3, 0, 0);
        }
        var2 = WorkModule(0x6, 0x1100000b);
        if (var2 == 0x1)
        {
            KineticModule(0x11, 0x1, 0);
            KineticModule(0xc, 0x1);
            WorkModule(0x7, WorkModule(0x6, 0x18000005), 0x1100000a);
            WorkModule(0x7, 0x2, 0x1100000b);
        }
        else if (var2 == 0x2)
        {
            var3 = WorkModule(0x6, 0x1100000a);
        }
        BattleObject(0x3e9, 0x1000008);
        var4 = WorkModuleF(0, 0x1000008);
        if (var4 > 0)
        {
            BattleObject(0x1a, var4, WorkModule(0x10, 0x21000010), 0x7640025);
            WorkModule(0x2711, 0x21000010);
        }
        var5 = WorkModule(0x6, 0x11000009);
        if (0x2 != WorkModule(0x6, 0x1000004b) && 0 < var5 && !(var5 & 0x1f) && var2 == 0x2)
        {
            var6 = EffectModule(0xb, 0x1000035, 0, 0, 0, 0, 0, 0, 0, 1.0f, 0x1, 0x4000, 0, 0xffffffff);
            SoundModule(0x2710, 0x7640025);
        }
        WorkModule(0x9, 0x11000009);
    }
    func_2245(var0);
}

void func_2340()
{
    WorkModule(0x2711, 0x20000080);
    if (global6 != 0x15f)
    {
        CatchModule(0x2711);
    }
    AttackModule(0x2, 0);
}

int func_2341()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0x4000, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x432, 0, 0x400, 0);
    return 0;
}

void func_2342()
{
    WorkModule(0x7, 0x27f, 0x11000002);
    WorkModule(0x7, 0x28b, 0x11000003);
    WorkModule(0x7, 0x6, 0x11000004);
    WorkModule(0x7, 0xa, 0x11000005);
    WorkModule(0x7, 0x2, 0x11000006);
    WorkModule(0x7, 0x5, 0x11000007);
    WorkModule(0x2711, 0x21000011);
    if (WorkModule(0x10, 0x2000007b))
    {
        EffectModule(0x2712, 0x32c0014, 0x11, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 0 + 0, 1.0f + 0, 0);
        BattleObject(0x3ea, 0xffffffff);
    }
    else if (0x155 == global5)
    {
        WorkModule(0x2710, 0x21000011);
    }
    func_78(func_2343);
}

void func_2343()
{
    int var0;
    int var1;
    int var2;
    var0 = StatusModule(0x6);
    if (var0 == 0)
    {
        var1 = WorkModule(0x10, 0x2100000e);
        if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
        {
            return 0x1;
        }
        if (MotionModule(0x2712))
        {
            if (global18 == 0)
            {
                var2 = 0;
            }
            else if (var1 == 0x1)
            {
                var2 = 0x10;
            }
            else
            {
                var2 = 0xe;
            }
            func_16(var2, 0);
            return 0x1;
        }
    }
    func_2245(var0);
}

void func_2344()
{
    WorkModule(0x2711, 0x20000080);
    WorkModule(0x2711, 0x2000007b);
}

int func_2345()
{
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1442, 0x1003e2, 0, 0);
    return 0;
}

void func_2346()
{
    BattleObject(0x25);
    AreaModule(0x2710, 0);
    BattleObject(0xa, 0);
    BattleObject(0xc, 0);
    WorkModule(0x2711, 0x2100000d);
    WorkModule(0x2711, 0x2000007d);
    WorkModule(0x7, 0, 0x1000009d);
    func_2348();
    func_78(func_2347);
}

void func_2347()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (WorkModule(0x10, 0x2100000e) && WorkModule(0x10, 0x2100000f))
    {
        func_16(0x16f, 0);
    }
    if (StatusModule(0x6) == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        func_2348();
    }
}

void func_2348()
{
    if (global18 == 0)
    {
        GroundModule(0x2710, 0x1);
    }
    else
    {
        GroundModule(0x2710, 0x5);
    }
    if (WorkModule(0x10, 0x2100000d))
    {
        func_23(0x28f);
    }
    else
    {
        func_22(0x28f, 0, 1.0f);
        WorkModule(0x2710, 0x2100000d);
    }
}

void func_2349()
{
    func_2350();
}

void func_2350()
{
    if (global6 == 0x16f || global6 == 0x170 || global6 == 0x163 || global6 == 0x171 || global6 == 0x164 || global6 == 0x161)
    {
        
    }
    else
    {
        if (ArticleModule(0x2717, 0x5))
        {
            ArticleModule(0x2711, 0x5);
        }
        HitModule(0x2710, 0);
        BattleObject(0x26);
    }
}

int func_2351()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x442, 0x1003e2, 0, 0);
    return 0;
}

void func_2352()
{
    BattleObject(0xa, 0x1);
    BattleObject(0xc, 0x1);
    func_22(0x290, 0, 1.0f);
    func_78(func_2353);
}

void func_2353()
{
    printf("----------------status_FinalFail_Main-------------------");
    if (MotionModule(0x2712))
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
    }
}

void func_2354()
{
    func_2350();
}

int func_2355()
{
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x442, 0x1003e2, 0, 0);
    return 0;
}

void func_2356()
{
    WorkModule(0x2711, 0x21000010);
    AreaModule(0x2710, 0);
    BattleObject(0xa, 0);
    BattleObject(0xc, 0);
    func_22(0x292, 0, 1.0f);
    func_78(func_2357);
}

void func_2357()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (MotionModule(0x2712))
    {
        func_16(0x171, 0);
    }
}

void func_2358()
{
    
}

int func_2359()
{
    StatusModule(0x5, 0x2, 0x32, 0, 0, 0, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x442, 0x1003e2, 0, 0);
    return 0;
}

void func_2360()
{
    WorkModule(0x7, 0xffffffff, 0x1100000a);
    WorkModule(0x2711, 0x21000010);
    AreaModule(0x2710, 0);
    BattleObject(0xa, 0);
    BattleObject(0xc, 0);
    func_22(0x293, 0, 1.0f);
    KineticModule(0xc, 0x5);
    func_78(func_2361);
}

void func_2361()
{
    int var0;
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    var0 = WorkModule(0x6, 0x1100000a);
    if (0xffffffff != var0)
    {
        BattleObject(0x3ea, var0);
        WorkModule(0x7, 0xffffffff, 0x1100000a);
    }
    if (MotionModule(0x2712))
    {
        func_16(0x164, 0);
    }
}

void func_2362()
{
    func_2350();
}

int func_2363()
{
    StatusModule(0x5, 0xffffffff, 0xf, 0x5, 0, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x442, 0x1003e2, 0, 0);
    return 0;
}

void func_2364()
{
    AreaModule(0x2710, 0);
    BattleObject(0xa, 0);
    BattleObject(0xc, 0);
    func_22(0x294, 0, 1.0f);
    func_2366();
    func_78(func_2365);
}

void func_2365()
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
        if (global18 == 0x2)
        {
            func_16(0xe, 0);
            return;
        }
    }
    if (StatusModule(0x6) == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        func_2366();
    }
}

void func_2366()
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

void func_2367()
{
    float var0;
    float var1;
    float var2;
    float var3;
    if (ArticleModule(0x2717, 0x5))
    {
        printf("===========================REMOVE_ARTICLE");
        ArticleModule(0x2711, 0x5);
    }
    BattleObject(0x26);
    var0 = PostureModuleF(0);
    var1 = PostureModuleF(0x1);
    var2 = PostureModuleF(0x2);
    var3 = PostureModuleF(0x7);
    PostureModule(0x3, var1 + var0 * var3 * 10.707099914550781f, var2, 0);
    PostureModule(0x2710);
    PostureModule(0x2719);
}

int func_2368()
{
    StatusModule(0x5, 0xffffffff, 0x33, 0x7, 0, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x442, 0x1003e2, 0, 0);
    return 0;
}

void func_2369()
{
    float var0;
    int var1;
    float var2;
    float var3;
    float var4;
    AreaModule(0x2710, 0);
    BattleObject(0xa, 0);
    BattleObject(0xc, 0);
    HitModule(0x2710, 0x2);
    KineticModule(0xc, 0x5);
    WorkModule(0x2711, 0x2100000e);
    WorkModule(0x2711, 0x2100000f);
    WorkModule(0x2711, 0x2100000d);
    WorkModule(0x2711, 0x21000010);
    var0 = PostureModuleF(0);
    var1 = 0xffffffff;
    var2 = 1.0f / PostureModuleF(0x7);
    if (var0 < 0)
    {
        var3 = 960.0f;
        var4 = -WorkModuleF(0, 0x4000017);
        var1 = EffectModule(0x3, 0x42c000a, var3, var4, 0, 0, 0, 0, var2, 0, 0);
    }
    else
    {
        var3 = 960.0f;
        var4 = -WorkModuleF(0, 0x4000017);
        var1 = EffectModule(0x3, 0x42c0009, var3, var4, 0, 0, 0, 0, var2, 0, 0);
    }
    WorkModule(0x7, var1, 0x100000a2);
    func_2371();
    func_78(func_2370);
}

void func_2370()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
    if (StatusModule(0x6) == 0x1 || global19 == 0 && global18 == 0x2 || global19 != 0 && global18 == 0)
    {
        func_2371();
    }
}

void func_2371()
{
    if (global18 == 0)
    {
        GroundModule(0x2710, 0x1);
        if (WorkModule(0x10, 0x2100000d))
        {
            
        }
        else
        {
            WorkModule(0x2710, 0x2100000d);
        }
    }
    else
    {
        GroundModule(0x2710, 0x5);
        if (WorkModule(0x10, 0x2100000d))
        {
            
        }
        else
        {
            WorkModule(0x2710, 0x2100000d);
        }
    }
}

void func_2372()
{
    func_2350();
}

int func_2373()
{
    StatusModule(0x5, 0x2, 0x33, 0, 0, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x442, 0x1003e2, 0, 0);
    return 0;
}

void func_2374()
{
    WorkModule(0x2711, 0x21000010);
    AreaModule(0x2710, 0);
    BattleObject(0xa, 0);
    BattleObject(0xc, 0);
    HitModule(0x2710, 0x2);
    func_78(func_2375);
}

void func_2375()
{
    if (CancelModule(0x2713) == 0x1 && (func_39() != 0 || func_41() != 0))
    {
        return;
    }
}

void func_2376()
{
    float var0;
    float var1;
    func_2350();
    var0 = PostureModuleF(0x1);
    var1 = PostureModuleF(0x2);
    GroundModule(0x1a, var0, var1);
}

// ===================================================================
// Universal mechanics (docs/universal-mechanics.md), added by tools/universal_mechanics.py; the same
// code as Captain Falcon's / Kirby's / Luigi's / Sonic's.
// Roll-off: the rolls' ACMD gives them their speed (EscapeF +S / EscapeB -S added at frame
// rolloff_start_frame(), 0 at frame 27); kinetic 0x6 so the animation doesn't move Reflet.
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
float rolloff_hold_x() { return 0.3f; } // Hero's test: the stick past this, on screen, the roll's way keeps the cap off

// Hero's test of a new roll-off (user): the speed carried off a ledge isn't held to the air speed cap
// (flag 0x20000044 off) until the stick stops holding the way that speed goes (its screen X, the position
// variable 0x0F000260, times rolloff_dir under rolloff_hold_x()), whatever he's doing in the air (Fall or
// an attack buffered off the edge); it's also back on landing or a ledge (situation not air) and when he's
// hit (Damage 0x45 - DamageFall 0x4C). Before: Fall's end put it back. rolloff_dir: the way his speed goes
// on screen (1 right, -1 left), from his movement (X, position variable 0x0F000000, against the last
// frame's) once he's off (fix 62, user: fix 61 took his facing, which a roll's turn can flip); global64:
// the cap is off from a roll-off.
float rolloff_dir;
float rolloff_last_x;

// Hero's test: an aerial buffered with the C-stick in a roll that rolls off came out neutral (user): on
// the ground the C-stick is a smash input, so the buffered command had no air direction and the aerial
// kind (ControlModule(0x10), func_311) went by the main stick. The roll keeps the last C-stick flick
// (past 0.5) on screen (rolloff_cstick: 1 right, 2 left, 3 up, 4 down; the
// position variables' raw C-stick, SELF_CSTICK_X_RAW 0x0F000261 / SELF_CSTICK_Y 0x0F000113); an aerial out of the roll-off (rolloff_air_t, frames since the slide-off, up to
// 8) takes it as forward / back / up / down with the facing it has then. The attack button pressed in the
// roll keeps the main stick as it is then (SELF_STICK_X_RAW 0x0F000260 / SELF_STICK_Y 0x0F000111; 5:
// neutral): fix 64, user: the buffered aerial went by the stick held before the roll-off, whatever it was
// when he pressed.
int rolloff_cstick;
int rolloff_air_t;
int rolloff_fast;       // Hero: the roll's speed scaled this roll (brave_roll_mult)
int rolloff_airborne;   // the first aerial of a roll-off's airtime goes by the stick as it starts (fix 66)

// the main stick now, as rolloff_cstick's codes: raw X on screen and Y, neutral (5) below 0.3 either way
int rolloff_stick_dir()
{
    float x;
    float y;
    x = WorkModuleF(0, 0x0f000260);
    y = WorkModuleF(0, 0x0f000111);
    if (y > 0.3f && y * y > x * x)
    {
        return 0x3;
    }
    if (y < -0.3f && y * y > x * x)
    {
        return 0x4;
    }
    if (x > 0.3f)
    {
        return 0x1;
    }
    if (x < -0.3f)
    {
        return 0x2;
    }
    return 0x5;
}

void rolloff_cstick_update()
{
    float x;
    float y;
    if (ControlModule(0x2710, 0))
    {
        rolloff_cstick = rolloff_stick_dir();   // attack pressed in the roll: the main stick then
        return;
    }
    x = WorkModuleF(0, 0x0f000261);     // the C-stick: raw X on screen, and Y (fix 63: ControlModuleF(7 / 8)
    y = WorkModuleF(0, 0x0f000113);     // followed the control stick, user)
    if (y > 0.5f && y * y > x * x)
    {
        rolloff_cstick = 0x3;
    }
    else if (y < -0.5f && y * y > x * x)
    {
        rolloff_cstick = 0x4;
    }
    else if (x * x > 0.25f)
    {
        if (x > 0)
        {
            rolloff_cstick = 0x1;
        }
        else
        {
            rolloff_cstick = 0x2;
        }
    }
}

// the aerial kind (ControlModule(0x10): 1 neutral, 2 forward, 3 back, 4 up, 5 down); rolloff_cstick 1 right,
// 2 left, 3 up, 4 down, 5 neutral
int rolloff_aerial(int kind)
{
    int c;
    c = rolloff_cstick;
    rolloff_cstick = 0;
    if (rolloff_air_t <= 0)
    {
        c = 0;      // a press / flick kept from the roll counts only for the slide-off's 8 frames
    }
    if (c == 0)
    {
        if (rolloff_airborne == 0)
        {
            return kind;
        }
        // pressed after the slide-off (fix 65, user: fix 64 changed nothing for the control stick): the
        // game's kind still went by the stick held in the roll; the stick now instead. For the airtime's
        // first aerial, not only the first 8 frames (fix 66, user: inconsistent facing against his
        // motion: past the 8 frames the game's kind was back)
        c = rolloff_stick_dir();
    }
    rolloff_airborne = 0;
    if (c == 0x5)
    {
        return 0x1;
    }
    if (c == 0x3)
    {
        return 0x4;
    }
    if (c == 0x4)
    {
        return 0x5;
    }
    if ((c == 0x1) == (PostureModuleF(0x7) > 0))
    {
        return 0x2;
    }
    return 0x3;
}

void rolloff_hold_update()
{
    float x;
    x = WorkModuleF(0, 0x0f000000);
    if (global64)
    {
        if (rolloff_dir == 0)
        {
            if (x > rolloff_last_x + 0.01f)
            {
                rolloff_dir = 1.0f;
            }
            else if (x < rolloff_last_x - 0.01f)
            {
                rolloff_dir = -1.0f;
            }
        }
        if (StatusModule(0x1) != 0x2 || global4 >= 0x45 && global4 <= 0x4c
            || rolloff_dir != 0 && WorkModuleF(0, 0x0f000260) * rolloff_dir < rolloff_hold_x())
        {
            global64 = 0;
            rolloff_dir = 0;
            WorkModule(0x14, 0x20000044);
        }
    }
    rolloff_last_x = x;
    if (StatusModule(0x1) != 0x2 || global4 >= 0x45 && global4 <= 0x4c)
    {
        rolloff_airborne = 0;   // landed, grabbed the ledge or hit
    }
    if (rolloff_air_t > 0)
    {
        rolloff_air_t -= 1;
        if (rolloff_air_t == 0)
        {
            rolloff_cstick = 0;
        }
    }
}

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
    float x;
    float m;
    if (MotionModuleF(0x1) < 1.0f)
    {
        global62 = 0; // new roll
        rolloff_cstick = 0;
        rolloff_fast = 0;
    }
    rolloff_cstick_update();
    if (rolloff_fast == 0 && MotionModuleF(0x1) >= 6.0f)
    {
        // Hero: the roll's speed (the ACMD's momentum at frame 5, energy 3) x2 under Acceleratle (fix 66,
        // user); carried off an edge the same
        rolloff_fast = 0x1;
        m = brave_roll_mult();
        if (m != 1.0f)
        {
            x = KineticModuleF(0xa, 0x3);
            KineticModule(0x11, 0x3, x * m, KineticModuleF(0xb, 0x3));
        }
    }
    if (brave_roll_mult() != 1.0f)
    {
        KineticModule(0x15, 0x3, -1.0f, -1.0f);    // under Acceleratle, every roll frame: energy 3's ground
    }                                               // speed limit off (universal-mechanics.md "Ground speed
                                                    // cap"), so the x2 isn't cut back (user)
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

// ---- Hero's MP (fighters/brave/README.md "MP"): Ultimate's param_mp. 100 at most, full at the start and
// after each stock; 1 back a second (sp_recover_frame 60) but not while a special is charging or the
// menu is open (brave_mp_pause, set by those loops each frame); 0.8 x the damage his other moves deal
// (sp_attack_mul; the damage the other fighters took while his attack had hit, his own specials not
// counted). Each special costs MP (brave_cost / brave_n_cost / ...): what he can't pay for doesn't come
// out. Shown under his damage (tools/trait_badge_cave.py's gauge: int 0x1000009C = 0x4D50GGBB, G his MP,
// B what's left after the cost in view, brave_cost_view, set by the loops each frame).
// brave_frame (global14, every frame) also keeps his buffs (int 0x1000008E: tools/kirby_stat_cave.py's
// stat profile, tools/strike_cave.py's damage bit) and the Command Selection window's ints.
float brave_mp;
int brave_mp_init;
int brave_mp_pause;
int brave_cost_view;
float brave_dmg_seen;
int brave_slot;
// buffs: frames left (Acceleratle, Oomph, Bounce), Psyche Up until a hit lands, Hocus Pocus's invisibility
int brave_speed_t;

// the roll's speed under Acceleratle (rolloff_update)
float brave_roll_mult()
{
    if (brave_speed_t > 0)
    {
        return 2.0f;
    }
    return 1.0f;
}
int brave_attack_t;
int brave_reflect_t;
int brave_psyche;
int brave_invisible_t;
int brave_poison_t;     // Hocus Pocus's poison: frames left (1.1% every 20 frames, 27.5% in all)
int brave_sleep_pending; // Hocus Pocus's sleep cast in the air: frames left to land and fall asleep
int brave_sleep_arm;    // the sleep status started: its time still to set (brave_sleep_update)
int brave_metal_on;
// the window (brave_lw_*): 0 shut, 1 open (choosing), 2 cast (the spell's row only), 3 closing
int brave_menu;
int brave_menu_anim;
int brave_menu_t;
int brave_menu_rows;
int brave_menu_cursor;
int brave_menu_grey;

// spell n's cost (Ultimate's param_special_lw_command_data sp); Magic Burst (8) takes all there is (at least 1)
int brave_cost(int n)
{
    int c;
    c = 0;
    if (n == 0x1) { c = 0x7; }
    else if (n == 0x2) { c = 0x8; }
    else if (n == 0x3) { c = 0x14; }
    else if (n == 0x4) { c = 0x9; }
    else if (n == 0x5) { c = 0x25; }
    else if (n == 0x6) { c = 0xa; }
    else if (n == 0x7) { c = 0x1e; }
    else if (n == 0x8)
    {
        c = (int)brave_mp;
        if (c < 0x1)
        {
            c = 0x1;
        }
    }
    else if (n == 0x9) { c = 0x1; }
    else if (n == 0xa) { c = 0x6; }
    else if (n == 0xb) { c = 0xd; }
    else if (n == 0xc) { c = 0x10; }
    else if (n == 0xd) { c = 0xe; }
    else if (n == 0xe) { c = 0x10; }
    else if (n == 0xf) { c = 0x4; }
    else if (n == 0x10) { c = 0x8; }
    else if (n == 0x11) { c = 0xc; }
    else if (n == 0x12) { c = 0xb; }
    else if (n == 0x13) { c = 0x6; }
    else if (n == 0x14) { c = 0xf; }
    else if (n == 0x15) { c = 0xe; }
    return c;
}

// Frizz / Frizzle / Kafrizz, Zap / Zapple / Kazap, Woosh / Swoosh / Kaswoosh (param_special_n / s / hi sp_*)
int brave_n_cost(int level)
{
    if (level == 0x1) { return 0x10; }
    if (level == 0x2) { return 0x24; }
    return 0x6;
}

int brave_s_cost(int level)
{
    if (level == 0x1) { return 0x12; }
    if (level == 0x2) { return 0x2a; }
    return 0x8;
}

int brave_hi_cost(int level)
{
    if (level == 0x1) { return 0x9; }
    if (level == 0x2) { return 0x12; }
    return 0x5;
}

int brave_can_pay(int cost)
{
    return (float)cost <= brave_mp;
}

void brave_pay(int cost)
{
    brave_mp = brave_mp - (float)cost;
    if (brave_mp < 0)
    {
        brave_mp = 0;
    }
}

void brave_add_mp(float v)
{
    brave_mp = brave_mp + v;
    if (brave_mp > 100.0f)
    {
        brave_mp = 100.0f;
    }
}

// the other fighters' damage in all (the position variables' slot DAMAGE, docs/position-variables.md)
float brave_others_damage()
{
    int s;
    float d;
    s = 0;
    d = 0;
    while (s < 0x8)
    {
        if (s != brave_slot && WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0)
        {
            d = d + WorkModuleF(0, 0x0f000177 + 0x20 * s);
        }
        s += 1;
    }
    return d;
}

int brave_special_status()
{
    return global4 >= 0x152 && global4 <= 0x155;
}

// the buffs' glows: Ultimate's game code plays them (FighterSpecializer_Brave::special_lw_active_command:
// req_follow on virtualcenter, his hip, bone 3, at his effect_scale 0.95, Y 180 facing left): Oomph's
// sys_special_attack_up and Acceleratle's sys_special_speed_up (ef_common's, 0x345007A / B) and Bounce's barrier
// brave_reflect (0x3450066), for as long as the buff lasts. A recast starts it again; the end lets its
// particles finish (the effects' own fade); a KO kills it at once
void brave_glow(int id, int on)
{
    if (on)
    {
        EffectModule(0x2723, id, 0x1, 0x1);
        EffectModule(0x2717, id, 0x3, 0, 0, 0, 0, 0, 0, 0.95f, 0);
    }
    else
    {
        EffectModule(0x2723, id, 0, 0);
    }
}

void brave_buffs_off()
{
    brave_speed_t = 0;
    brave_attack_t = 0;
    brave_reflect_t = 0;
    brave_psyche = 0;
    if (brave_invisible_t > 0)
    {
        VisibilityModule(0x2710, 0x1);
    }
    brave_invisible_t = 0;
    brave_poison_t = 0;
    brave_sleep_pending = 0;
    brave_sleep_arm = 0;
    brave_reflect(0);
    brave_metal(0);
    EffectModule(0x2723, 0x3450066, 0x1, 0x1);
    EffectModule(0x2723, 0x345007a, 0x1, 0x1);
    EffectModule(0x2723, 0x345007b, 0x1, 0x1);
    EffectModule(0x2723, 0x345004e, 0x1, 0x1);
}

// Kaclang's metal: the Metal Box's own (fix 59; tools/position_vars_cave.py's ITEM variable 0x0F000099:
// 1 on, 2 off, through the game's 0x02E15DE4): the metal look (ModelModule +0x6D), its physics and
// knockback resistance (work flag 0x20000012) and its footsteps. Fix 57's flag alone gave no look.
// Called every frame while he's steel: only a change reaches the game
void brave_metal(int on)
{
    if (on && brave_metal_on == 0)
    {
        WorkModule(0, 1.0f, 0x0f000099);
    }
    else if (on == 0 && brave_metal_on)
    {
        WorkModule(0, 2.0f, 0x0f000099);
    }
    brave_metal_on = on;
}

// Hocus Pocus's item states (the ITEM variable, 0x0F000099): 3 giant (Super Mushroom), 4 small (Poison
// Mushroom), 5 Super Star, 6 Lip's Stick flower, 7 the Timer's slow on every other fighter. The game's
// own functions, with the items' own durations
void brave_item(float code)
{
    WorkModule(0, code, 0x0f000099);
}

// Hocus Pocus's item-like states on him: 0 giant, 1 Starman, 3 timer, 6 sleep, 7 small, 8 flower, 9 invisible
void brave_state(int o)
{
    if (o == 0)
    {
        brave_item(3.0f);
    }
    else if (o == 0x1)
    {
        brave_item(5.0f);
    }
    else if (o == 0x3)
    {
        brave_item(7.0f);
    }
    else if (o == 0x7)
    {
        brave_item(4.0f);
    }
    else if (o == 0x8)
    {
        brave_item(6.0f);
    }
    else if (o == 0x9)
    {
        VisibilityModule(0x2710, 0);
        brave_invisible_t = 0x258;
    }
    else if (o == 0x6)
    {
        brave_sleep_start();
    }
}

// Hocus Pocus's sleep: the game's own sleep (FuraSleepStart 0x5F -> FuraSleepLoop 0x60 -> FuraSleepEnd 0x62,
// as a sleep hit gives), lasting until the mash counter (ControlModule 0x6 sets it, ControlModuleF(0x5)
// reads it: func_96) runs out: 240 frames, 1 a frame and 8 a press off (the sleep hit's common params
// 0x15C / 0x15D). In the air he falls asleep when he lands (within various_frame, 450)
void brave_sleep_start()
{
    if (global18 == 0)
    {
        brave_sleep_arm = 0x1;
        func_16(0x5f, 0);
    }
    else
    {
        brave_sleep_pending = 0x1c2;
    }
}

void brave_sleep_update()
{
    if (brave_sleep_arm && (global4 == 0x5f || global4 == 0x60))
    {
        ControlModule(0x6, 240.0f, 1.0f, 8.0f, 0x1);
        brave_sleep_arm = 0;
    }
    if (brave_sleep_pending > 0)
    {
        brave_sleep_pending -= 1;
        if (global18 == 0 && (global4 == 0 || global4 >= 0x16 && global4 <= 0x1a))
        {
            brave_sleep_pending = 0;
            brave_sleep_arm = 0x1;
            func_16(0x5f, 0);
        }
    }
}

// a new stock (Rebirth, func_235) or the match's start: full MP, no buffs, the window shut
void brave_rebirth()
{
    brave_mp = 100.0f;
    brave_mp_init = 0x1;
    brave_slot = -1;
    brave_menu = 0;
    brave_menu_anim = 0;
    brave_hi_used = 0;
    if (brave_crit_cam > 0)
    {
        brave_item(9.0f);   // KO'd during a crit's closeup: the camera back
    }
    brave_crit_cam = 0;
    brave_buffs_off();
    WorkModule(0x7, 0, 0x1000009e);
}

void brave_mp_update()
{
    float d;
    if (brave_mp_init == 0 || global4 == 0x14f)
    {
        brave_rebirth();    // the match's start (Entry)
    }
    if (brave_mp_pause == 0)
    {
        brave_add_mp(1.0f / 60.0f);
    }
    brave_mp_pause = 0;
    if (brave_slot < 0)
    {
        brave_slot = brave_self_slot();
    }
    d = brave_others_damage();
    if (d > brave_dmg_seen && WorkModuleF(0, 0x0f0000a0) >= 0.5f && brave_special_status() == 0)
    {
        brave_add_mp(0.8f * (d - brave_dmg_seen));
    }
    brave_dmg_seen = d;
}

// buffs: the marker int 0x1000008E = 0x4B49xxxx (tools/kirby_stat_cave.py profile 3 in bits 0-2:
// Acceleratle's speeds; tools/strike_cave.py's bit 0x8: x1.15 damage, Oomph or Psyche Up), 0 without one
void brave_buff_update()
{
    int m;
    if (brave_speed_t > 0)
    {
        brave_speed_t -= 1;
        if (brave_speed_t == 0)
        {
            brave_glow(0x345007b, 0);
        }
    }
    if (brave_attack_t > 0)
    {
        brave_attack_t -= 1;
        if (brave_attack_t == 0)
        {
            brave_glow(0x345007a, 0);
        }
    }
    if (brave_reflect_t > 0)
    {
        brave_reflect_t -= 1;
        if (brave_reflect_t == 0)
        {
            brave_reflect(0);
        }
        else
        {
            // fix 58: on again every frame. Bounce lasts 720 frames over many statuses; Kirby's air side B
            // (which reflects) turns its reflector on inside the one status, Hero's went once at the cast
            // and didn't reflect: the same calls, so a status change most likely shuts it
            brave_reflect_shape();
        }
    }
    if (brave_invisible_t > 0)
    {
        brave_invisible_t -= 1;
        if (brave_invisible_t == 0)
        {
            VisibilityModule(0x2710, 0x1);
        }
    }
    if (brave_poison_t > 0)
    {
        brave_poison_t -= 1;
        if (brave_poison_t % 0x14 == 0)
        {
            WorkModule(0x2, 1.1f, 0x0f000117);     // his damage + 1.1
        }
    }
    // Psyche Up: spent on the hit that landed, or by a throw (fix 64, user: throws take it, cave's throw
    // path): a grab's pummels (catch statuses 0x35-0x3D) and the throw's own hits keep it for the throw,
    // spent when the throw (0x3E) ends
    if (brave_psyche && brave_special_status() == 0
        && (WorkModuleF(0, 0x0f0000a1) >= 0.5f && (global4 < 0x35 || global4 > 0x3e)
            || global5 == 0x3e && global4 != 0x3e))
    {
        brave_psyche = 0;
        brave_glow(0x345004e, 0);
    }
    // the marker's bits (tools/strike_cave.py, tools/hero_buff_cave.py): 3 Acceleratle's speeds, 0x20
    // Oomph (x1.6 damage, x1.1 knockback) and 0x40 Psyche Up (x1.2 knockback, x1.65 shield damage) on his
    // physical attacks (not his specials), 0x80 Oomph's x1.2 damage taken, 0x10 a critical smash attack
    m = 0;
    if (brave_speed_t > 0)
    {
        m = m + 0x3;
    }
    if (brave_attack_t > 0)
    {
        m = m + 0x80;
        if (brave_special_status() == 0)
        {
            m = m + 0x20;
        }
    }
    if (brave_psyche && brave_special_status() == 0)
    {
        m = m + 0x40;
    }
    if (m == 0)
    {
        WorkModule(0x7, 0, 0x1000008e);
    }
    else
    {
        WorkModule(0x7, 0x4b490000 + m, 0x1000008e);
    }
}

// the window and the gauge (tools/trait_badge_cave.py): int 0x1000009E = 0x4845xxxx (bit 2 shown, bits 0-1
// the cursor, bit 3 closing, bit 4 blinking off, bit 5 cast, bits 8-10 the animation's frame, 11-14 the
// pointer's frame: Ultimate's spin, 2 frames each),
// 0x1000009F = 0x48xxxxxx (the rows' spells, bit 20 + row greyed), 0x1000009C = 0x4D50GGBB
void brave_panel_update()
{
    int a;
    int g;
    int b;
    g = (int)brave_mp;
    b = g;
    if (brave_cost_view > 0 && brave_cost_view <= g)
    {
        b = g - brave_cost_view;
    }
    brave_cost_view = 0;
    WorkModule(0x7, 0x4d500000 + g * 0x100 + b, 0x1000009c);
    if (brave_menu == 0)
    {
        WorkModule(0x7, 0, 0x1000009e);
        WorkModule(0x7, 0, 0x1000009f);
        return;
    }
    if (brave_menu_anim < 0x7)
    {
        brave_menu_anim += 1;
    }
    brave_menu_t += 1;
    if (brave_menu == 0x3 && brave_menu_anim > 0x4)
    {
        brave_menu = 0;     // closed
        WorkModule(0x7, 0, 0x1000009e);
        WorkModule(0x7, 0, 0x1000009f);
        return;
    }
    a = 0x48450004 + brave_menu_cursor + (brave_menu_anim - 0x1) * 0x100 + (brave_menu_t / 0x2 % 0x10) * 0x800;
    if (brave_menu == 0x3)
    {
        a = a + 0x8;
    }
    if (brave_menu == 0x2)
    {
        a = a + 0x20;   // the cast spell's row window
    }
    // the last 2 seconds of the time limit (480 frames, command_select_blink_frame 360): blinking
    if (brave_menu == 0x1 && brave_menu_t >= 0x168 && brave_menu_t / 0x4 % 0x2 == 0x1)
    {
        a = a + 0x10;
    }
    WorkModule(0x7, a, 0x1000009e);
    WorkModule(0x7, 0x48000000 + brave_menu_rows + brave_menu_grey * 0x100000, 0x1000009f);
}

void brave_menu_open(int rows, int cursor)
{
    brave_menu = 0x1;
    brave_menu_anim = 0;
    brave_menu_t = 0;
    brave_menu_rows = rows;
    brave_menu_cursor = cursor;
    brave_menu_grey = 0;
}

// shut: the menu closes (its animation); a cast spell's row window just goes (view_wnd_hide)
void brave_menu_close()
{
    if (brave_menu == 0x1)
    {
        brave_menu = 0x3;
        brave_menu_anim = 0;
    }
    else if (brave_menu == 0x2)
    {
        brave_menu = 0;
    }
}

// Robin's tome and Levin Sword uses (Thunder 0x10000083, Elwind float 0x2f, Arcfire 0x1000008a, Nosferatu
// 0x10000086, the Levin Sword 0x1000008c): Robin's attacks still count them down, and a spent one
// (BattleObject 0x3ec: bits in 0x10000091) sent Hero into her discard status 0x8c, a tome or the sword
// thrown away, then her pick-up one. Hero has neither: kept full every frame, nothing spent
void brave_keep_items()
{
    WorkModule(0x7, 0x63, 0x10000083);
    WorkModule(0, 99.0f, 0x2f);
    WorkModule(0x7, 0x63, 0x1000008a);
    WorkModule(0x7, 0x63, 0x10000086);
    WorkModule(0x7, 0x63, 0x1000008c);
    WorkModule(0x7, 0, 0x10000091);
}

// Ultimate's lot_critical: each smash attack (statuses 0x2B-0x33, from the windup) is a critical hit 1 time
// in 8, rolled when it starts; int 0x1000009A is 1 for the whole of it, and his smash scripts take
// Ultimate's critical hitboxes on it (tools/brave_build.py CRIT_INT)
int brave_crit_rolled;
int brave_crit;

void brave_crit_update()
{
    if (global4 < 0x2b || global4 > 0x33)
    {
        brave_crit_rolled = 0;
        brave_crit = 0;
    }
    else if (brave_crit_rolled == 0)
    {
        brave_crit_rolled = 0x1;
        brave_crit = 0;
        if (randi(0, 0x8) == 0)
        {
            brave_crit = 0x1;
        }
    }
    WorkModule(0x7, brave_crit * 0x3e8, 0x1000009a);   // 1000 (fix 62): Robin's native code counts this int
                                                        // down a frame at a time (0x02F635F0: ints 0x98-0x9C,
                                                        // his tomes' recharge), which made 1 read 0 by the hit
}

// the critical hit's show (Ultimate's param_critical: the game slowed to 1/4 for critical_frame 40, the
// camera in on him; it plays when the crit hitboxes connect): a smash attack that rolled it (brave_crit) or
// Hatchet Man (spell 20, always critical). The hit: self's HIT variable (0x0F0000A0, on until the move
// ends); the slow: SlowModule(0, rate, frames) (ACMD Time_Manipulation_Whole's call); the camera: the ITEM
// variable's 8 (closeup) / 9 (back) (tools/position_vars_cave.py, ACMD Camera_Closeup / Normal_Camera's calls)
int brave_crit_shown;
int brave_crit_cam;

void brave_crit_show()
{
    int crit;
    crit = brave_crit;
    if (global4 == 0x155 && brave_lw_spell == 0x14)
    {
        crit = 0x1;
    }
    if (crit == 0)
    {
        brave_crit_shown = 0;
    }
    else if (brave_crit_shown == 0 && WorkModuleF(0, 0x0f0000a0) >= 0.5f)
    {
        brave_crit_shown = 0x1;
        SlowModule(0, 0x4, 0x28);
        brave_item(8.0f);
        brave_crit_cam = 0x28;
    }
    if (brave_crit_cam > 0)
    {
        brave_crit_cam -= 1;
        if (brave_crit_cam == 0)
        {
            brave_item(9.0f);
        }
    }
}

void brave_frame()
{
    func_82();
    brave_keep_items();
    brave_mp_update();
    brave_crit_update();
    brave_crit_show();
    brave_hi_refresh();
    rolloff_hold_update();
    brave_buff_update();
    brave_sleep_update();
    brave_panel_update();
}

// Bounce's reflector (as Kirby's air side B, tools/kirby_sideb_reflect_acmd.py: kind 3, ID 0, group 3; the
// group made for Robin's kind by tools/brave_reflect_cave.py): a capsule around him, x1.5 damage, x1.2 speed
// and life, no threshold; its barrier with it (brave_glow)
void brave_reflect_shape()
{
    ShieldModule(0x2717, 0x3, 0, 0, 12.0f, 0, 4.0f, 0, 0, 15.0f, 0, 1.5f, 1.2f, 999.0f, 0, 1.2f, 0x3);
    ShieldModule(0, 0x3, 0, 0x1, 0x3);
}

void brave_reflect(int on)
{
    if (on)
    {
        brave_reflect_shape();
        brave_glow(0x3450066, 0x1);
    }
    else
    {
        ShieldModule(0, 0x3, 0, 0, 0x3);
        brave_glow(0x3450066, 0);
    }
}

// ---- Hero's side tilt (status 0x28, Robin's func_275 / func_277): Ultimate's shield bash (AttackS3, motion
// 0x58), then on a second attack press its sword slash AttackS3S2 (motion 0x59, Ultimate's c01attacks32):
// Ultimate enables it from frame 16 (ENABLE_COMBO). The game's own side-tilt combo (func_276, fighter_param
// 265) didn't take for him in game, so Hero's loop does it: a press from frame 3 on (the one that started
// the tilt is past by then: the status's third frame on) is kept, and from motion frame 16 it plays the
// slash (once; fighter_param 265 stays Robin's 1, so func_276 doesn't also try).
int brave_s3_pressed;
int brave_s3_second;
int brave_s3_t;

void brave_s3_loop()
{
    float f;
    brave_s3_t += 1;
    f = MotionModuleF(0x1);
    if (brave_s3_second == 0 && brave_s3_t > 0x2)
    {
        if (global38 & 0x1)
        {
            brave_s3_pressed = 0x1;
        }
        if (brave_s3_pressed && f >= 16.0f && global18 != 0x2)
        {
            brave_s3_second = 0x1;
            func_22(0x59, 0, 1.0f);
            return;
        }
    }
    func_277();
}

void brave_s3_main()
{
    brave_s3_pressed = 0;
    brave_s3_second = 0;
    brave_s3_t = 0;
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
    func_78(brave_s3_loop);
}

// ---- Hero's neutral special: Frizz / Frizzle / Kafrizz (status 0x152, Robin's Thunder; fighters/brave/README.md).
// Ultimate's SpecialNStart (8 frames) then SpecialNHold (a 101-frame loop) until it's fired; the charge is
// the frames charging (param_special_n hold_frame_m 18: Frizzle, hold_frame_l 81: Kafrizz: then the flash
// and the charge is stored, as Ultimate's; a stored Kafrizz is cast at once). Special pressed again (not
// released: fix 57) -> SpecialN1 / N2 / N3, which fire the fireball (article 6, weapon kind 0x190,
// fighters/brave/weapons/fireball.c) at frame 10 / 11 / 16; the charge stops at the strongest level his MP
// pays for and casts it (brave_n_max_level); shield while charging -> SpecialNCancel, the
// charge kept for the next one (brave_n_stored; a stock lost clears it, func_235). The fireball learns its
// level through the custom N slot (int 0x10000048 -> the weapon's 0x10000005), set while it is generated (as
// Sephiroth's Flare). Robin's motion slots: 0x21F start, 0x223 hold, 0x227 / 0x228 / 0x229 N1 / N2 / N3 (the
// shoot and its custom-move variants), 0x22F cancel (Thoron's start); air + 0x1C. Robin's helpers do the
// rest: func_2245 (ground / air: kinetic, ground correction, the motion swapped keeping its frame, from the
// 0x11000002-7 work ints), func_2246 (actionable from the motion's cancel frame, wait / fall at its end).
// In the air the fall is slowed while charging and through Frizz (start_accel_y_mul_air 0.8 /
// start_max_speed_y_mul_air 0.8, shoot_*_s 0.8: Robin's gravity 0.089, fall 1.5). No MP yet: every cast works.
int brave_n_state;
int brave_n_hold;
int brave_n_stored;
int brave_n_level;
int brave_n_fired;
int brave_n_released;

int brave_n_pre()
{
    printf("status_pre_SpecialN");
    func_69();
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1190, 0x1000, 0x80, 0x1000);
    return 0;
}

int brave_n_ground_motion()
{
    if (brave_n_state == 0x1)
    {
        return 0x223;               // SpecialNHold
    }
    if (brave_n_state == 0x2)
    {
        return 0x227 + brave_n_level;   // SpecialN1 / N2 / N3
    }
    if (brave_n_state == 0x3)
    {
        return 0x22f;               // SpecialNCancel
    }
    if (brave_n_state == 0x4)
    {
        return 0x220;               // not enough MP: SpecialLwFail
    }
    return 0x21f;                   // SpecialNStart
}

// the state's motion from frame 0 (ground or air), and the motions func_2245 swaps between
void brave_n_change(int state)
{
    int m;
    int a;
    brave_n_state = state;
    m = brave_n_ground_motion();
    a = m + 0x1c;
    if (state == 0x4)
    {
        a = 0x246;
    }
    WorkModule(0x7, m, 0x11000002);
    WorkModule(0x7, a, 0x11000003);
    if (global18 == 0x2)
    {
        m = a;
    }
    func_22(m, 0, 1.0f);
    if (global18 == 0x2 && state == 0x2 && brave_n_level != 0)
    {
        // Frizzle / Kafrizz: his own fall again
        KineticModule(0xf, 0x1, -0.089f);
        KineticModule(0x14, 0x1, 1.5f);
    }
}

void brave_n_air()
{
    if (global18 != 0x2)
    {
        return;
    }
    if (brave_n_state < 0x2 || brave_n_state == 0x2 && brave_n_level == 0)
    {
        KineticModule(0xf, 0x1, -0.0712f);
        KineticModule(0x14, 0x1, 1.2f);
    }
}

// an article with its custom number (the custom N slot while it's generated: the weapon's 0x10000005)
void brave_generate(int article, int custom)
{
    int slot;
    slot = WorkModule(0x6, 0x10000048);
    WorkModule(0x7, custom, 0x10000048);
    ArticleModule(0x2710, article);
    WorkModule(0x7, slot, 0x10000048);
}

void brave_n_generate()
{
    brave_generate(0x6, brave_n_level);
    brave_n_fired = 0x1;
}

// the level held so long (0 / 1 / 2), lowered to one his MP pays for
int brave_n_hold_level()
{
    int level;
    level = 0;
    if (brave_n_hold >= 0x51)
    {
        level = 0x2;
    }
    else if (brave_n_hold >= 0x12)
    {
        level = 0x1;
    }
    while (level > 0 && brave_can_pay(brave_n_cost(level)) == 0)
    {
        level -= 1;
    }
    return level;
}

// the strongest level his MP pays for (-1: none); the charge stops there (fix 57: it went on charging for
// a level he couldn't pay, then gave the one he could on release)
int brave_n_max_level()
{
    int level;
    level = 0x2;
    while (level >= 0 && brave_can_pay(brave_n_cost(level)) == 0)
    {
        level -= 1;
    }
    return level;
}

int brave_n_level_frame(int level)
{
    if (level == 0x2)
    {
        return 0x51;
    }
    if (level == 0x1)
    {
        return 0x12;
    }
    return 0;
}

int brave_n_fire_frame()
{
    if (brave_n_level == 0x1)
    {
        return 0xb;
    }
    if (brave_n_level == 0x2)
    {
        return 0x10;
    }
    return 0xa;
}

void brave_n_loop()
{
    float f;
    func_2245(StatusModule(0x6));
    f = MotionModuleF(0x1);
    if (brave_n_state == 0)
    {
        brave_mp_pause = 0x1;
        if (MotionModule(0x2712) == 0x1)
        {
            brave_n_change(0x1);
        }
    }
    else if (brave_n_state == 0x1)
    {
        brave_n_hold += 1;
        brave_mp_pause = 0x1;
        brave_cost_view = brave_n_cost(brave_n_hold_level());
        if (ControlModule(0x2710, 0x1))
        {
            brave_n_released = 0x1;     // Ultimate's: special pressed again fires (a release doesn't)
        }
        // fix 61 (user): no casting by itself when his MP runs short of the next level (fix 57 did): he
        // charges on, and the press casts the strongest level held that he pays for (brave_n_hold_level)
        if (ControlModule(0x2710, 0x3))
        {
            brave_n_stored = brave_n_hold;
            brave_n_change(0x3);
        }
        else if (brave_n_released)
        {
            brave_n_level = brave_n_hold_level();
            if (brave_can_pay(brave_n_cost(brave_n_level)))
            {
                brave_pay(brave_n_cost(brave_n_level));
                brave_n_change(0x2);
            }
            else
            {
                brave_n_change(0x4);
            }
        }
        else if (brave_n_hold >= 0x51)
        {
            // fully charged (Kafrizz): Ultimate's SpecialNHoldMax flash (brave_chant_finish on top, as
            // its script), then the charge is stored and he stops, as a shield cancel
            EffectModule(0x2717, 0x345002b, 0, 0, 9.0f, 0, 0, -1.0472f, 0, 1.0f, 0);
            brave_n_stored = brave_n_hold;
            brave_n_change(0x3);
        }
        else if (MotionModule(0x2712) == 0x1)
        {
            brave_n_change(0x1);    // the hold loops
        }
    }
    else
    {
        if (brave_n_state == 0x2 && brave_n_fired == 0 && f >= (float)brave_n_fire_frame())
        {
            brave_n_generate();
        }
        if (func_2246())
        {
            return;
        }
    }
    brave_n_air();
}

void brave_n_main()
{
    printf("status_SpecialN (Hero)");
    brave_n_state = 0;
    brave_n_level = 0;
    brave_n_fired = 0;
    brave_n_released = 0;
    brave_n_hold = brave_n_stored;  // a stored charge goes on from where it was (and is lost if he's hit)
    brave_n_stored = 0;
    if (brave_n_hold >= 0x51)
    {
        brave_n_released = 0x1;     // a stored Kafrizz is cast at once
    }
    WorkModule(0x7, 0, 0x10000090);
    WorkModule(0x7, 0x21f, 0x11000002);
    WorkModule(0x7, 0x23b, 0x11000003);
    WorkModule(0x7, 0x6, 0x11000004);
    WorkModule(0x7, 0xa, 0x11000005);
    WorkModule(0x7, 0x2, 0x11000006);
    WorkModule(0x7, 0x5, 0x11000007);
    func_2245(0x1);
    brave_n_air();
    func_78(brave_n_loop);
}

void brave_n_end()
{
    
}

// ---- Hero's side special: Zap / Zapple / Kazap (status 0x153, Robin's Arcfire; fighters/brave/README.md).
// SpecialSStart (8 frames), then SpecialSHold while special is held; Zapple from 9 frames held, Kazap at 26
// (param_special_s hold_frame_m / _l; hold_frame_max 26: it goes off by itself). Released -> SpecialS1 (Zap)
// / S2 (Zapple); Kazap: SpecialS3 (the sword raised; Ultimate's lightning reaches him at about frame 19: it
// starts 85 above at frame 10, 10 a frame) then SpecialS32 (the strike). The bolts are his own hitboxes; when
// one hits a fighter, Zap's lightning lands on that fighter: the spark article (article 7, weapon kind 0x191,
// weapons/spark.c) at its player slot (custom number level + 4 x slot; the slot found from the last fighter
// hit's offset, docs/position-variables.md), once a fighter per cast. Motions (ground / air): start 0x258 /
// 0x25C, hold 0x259 / 0x25D, Zap 0x257 / 0x25B, Zapple 0x25A / 0x25E, Kazap 0x230 / 0x24C and 0x231 / 0x24D.
int brave_s_state;
int brave_s_hold;
int brave_s_level;
int brave_s_released;
int brave_s_sparked;

// the player slot (0-7) of the fighter at (x, y), -1 if none (an empty slot reads facing 0)
int brave_slot_of(float x, float y)
{
    int s;
    float dx;
    float dy;
    s = 0;
    while (s < 0x8)
    {
        if (WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0)
        {
            dx = WorkModuleF(0, 0x0f000020 + 0x4 * s) - x;
            dy = WorkModuleF(0, 0x0f000021 + 0x4 * s) - y;
            if (dx < 1.0f && dx > -1.0f && dy < 1.0f && dy > -1.0f)
            {
                return s;
            }
        }
        s += 1;
    }
    return -1;
}

int brave_self_slot()
{
    float x;
    float y;
    x = WorkModuleF(0, 0x0f000000);
    y = WorkModuleF(0, 0x0f000001);
    return brave_slot_of(x, y);
}

// 1 << s for s 0-7
int brave_bit(int s)
{
    int b;
    int i;
    b = 0x1;
    i = 0;
    while (i < s)
    {
        b = b * 0x2;
        i += 1;
    }
    return b;
}

int brave_s_ground_motion()
{
    if (brave_s_state == 0x1)
    {
        return 0x259;
    }
    if (brave_s_state == 0x2)
    {
        if (brave_s_level == 0)
        {
            return 0x257;
        }
        return 0x25a;
    }
    if (brave_s_state == 0x3)
    {
        return 0x230;
    }
    if (brave_s_state == 0x4)
    {
        return 0x231;
    }
    if (brave_s_state == 0x5)
    {
        return 0x220;   // not enough MP: SpecialLwFail
    }
    return 0x258;
}

int brave_s_air_motion()
{
    if (brave_s_state == 0x1)
    {
        return 0x25d;
    }
    if (brave_s_state == 0x2)
    {
        if (brave_s_level == 0)
        {
            return 0x25b;
        }
        return 0x25e;
    }
    if (brave_s_state == 0x3)
    {
        return 0x24c;
    }
    if (brave_s_state == 0x4)
    {
        return 0x24d;
    }
    if (brave_s_state == 0x5)
    {
        return 0x246;
    }
    return 0x25c;
}

void brave_s_change(int state)
{
    int g;
    int a;
    brave_s_state = state;
    g = brave_s_ground_motion();
    a = brave_s_air_motion();
    WorkModule(0x7, g, 0x11000002);
    WorkModule(0x7, a, 0x11000003);
    if (global18 == 0x2)
    {
        g = a;
    }
    func_22(g, 0, 1.0f);
}

// the bolt hit a fighter: the lightning on it (once a fighter)
void brave_s_spark()
{
    float x;
    float y;
    int s;
    int b;
    if (WorkModuleF(0, 0x0f0000a0) < 0.5f)
    {
        return;
    }
    x = WorkModuleF(0, 0x0f000055) * WorkModuleF(0, 0x0f000003) + WorkModuleF(0, 0x0f000000);
    y = WorkModuleF(0, 0x0f000056) + WorkModuleF(0, 0x0f000001);
    s = brave_slot_of(x, y);
    if (s < 0)
    {
        return;
    }
    b = brave_bit(s);
    if ((brave_s_sparked / b) % 0x2 == 0x1)
    {
        return;
    }
    brave_s_sparked = brave_s_sparked + b;
    brave_generate(0x7, brave_s_level + 0x4 * s);
}

// the level held so long, lowered to one his MP pays for
int brave_s_hold_level()
{
    int level;
    level = 0;
    if (brave_s_hold >= 0x1a)
    {
        level = 0x2;
    }
    else if (brave_s_hold >= 0x9)
    {
        level = 0x1;
    }
    while (level > 0 && brave_can_pay(brave_s_cost(level)) == 0)
    {
        level -= 1;
    }
    return level;
}

// the strongest level his MP pays for (-1: none); the charge stops there and casts it (fix 57)
int brave_s_max_level()
{
    int level;
    level = 0x2;
    while (level >= 0 && brave_can_pay(brave_s_cost(level)) == 0)
    {
        level -= 1;
    }
    return level;
}

int brave_s_level_frame(int level)
{
    if (level == 0x2)
    {
        return 0x1a;
    }
    if (level == 0x1)
    {
        return 0x9;
    }
    return 0;
}

void brave_s_loop()
{
    float f;
    int top;
    func_2245(StatusModule(0x6));
    if (ControlModule(0x2712, 0x1) == 0)
    {
        brave_s_released = 0x1;
    }
    f = MotionModuleF(0x1);
    if (brave_s_state == 0)
    {
        brave_mp_pause = 0x1;
        if (MotionModule(0x2712) == 0x1)
        {
            brave_s_change(0x1);
        }
    }
    else if (brave_s_state == 0x1)
    {
        brave_s_hold += 1;
        brave_mp_pause = 0x1;
        brave_cost_view = brave_s_cost(brave_s_hold_level());
        top = brave_s_max_level();
        if (top < 0x2 && brave_s_hold >= brave_s_level_frame(top))
        {
            brave_s_released = 0x1;     // as charged as his MP allows: cast it; none paid for: the misfire
                                        // at once (fix 61: fix 58 had him charge on; only Zap does this)
        }
        if (brave_s_hold >= 0x1a && brave_s_hold_level() == 0x2)
        {
            brave_s_level = 0x2;
            brave_pay(brave_s_cost(0x2));
            brave_s_change(0x3);
        }
        else if (brave_s_released)
        {
            brave_s_level = brave_s_hold_level();
            if (brave_can_pay(brave_s_cost(brave_s_level)))
            {
                brave_pay(brave_s_cost(brave_s_level));
                brave_s_change(0x2);
            }
            else
            {
                brave_s_change(0x5);
            }
        }
        else if (MotionModule(0x2712) == 0x1)
        {
            brave_s_change(0x1);    // the hold loops
        }
    }
    else if (brave_s_state == 0x3)
    {
        if (f >= 19.0f)
        {
            brave_s_change(0x4);
        }
    }
    else
    {
        brave_s_spark();
        if (func_2246())
        {
            return;
        }
    }
}

int brave_s_pre()
{
    printf("status_pre_SpecialS (Hero)");
    func_69();
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1190, 0x1000, 0x80, 0x1000);
    return 0;
}

void brave_s_main()
{
    printf("status_SpecialS (Hero)");
    brave_s_state = 0;
    brave_s_hold = 0;
    brave_s_level = 0;
    brave_s_released = 0;
    brave_s_sparked = 0;
    WorkModule(0x7, 0x258, 0x11000002);
    WorkModule(0x7, 0x25c, 0x11000003);
    WorkModule(0x7, 0x6, 0x11000004);
    WorkModule(0x7, 0xa, 0x11000005);
    WorkModule(0x7, 0x2, 0x11000006);
    WorkModule(0x7, 0x5, 0x11000007);
    func_2245(0x1);
    func_78(brave_s_loop);
}

// ---- Hero's up special: Woosh / Swoosh / Kaswoosh (status 0x154, Robin's Elwind; fighters/brave/README.md).
// SpecialHiStart (4 frames), then SpecialHiHold while special is held; Swoosh from 10 frames held, Kaswoosh
// at 28 (param_special_hi hold_frame_m / _l; hold_frame_max 28: it goes off by itself). Then SpecialHi1 / 2 / 3:
// the whirlwind (the tornado article, article 8, weapon kind 0x192, weapons/tornado.c, put at his own player
// slot) at frame 4 / 6 / 8, and he rises from frame 5 / 12 / 11 (the game script's JUMP_START): Ultimate's
// rise is jump_distance_* 42 / 64 / 99 at jump_accel_y_* 0.145 / 0.16 / 0.1 a frame, here a start speed of
// sqrt(2 x distance x accel) slowed by that accel to 0, then end_accel_y 0.96 x his gravity with
// end_max_speed_y_* 0.955 / 0.828 / 0.86 x his fall speed (Robin's 0.089 / 1.5) to the motion's end, then
// a plain Fall (0xE; fix 60: no SpecialFall, user); landing during it -> LandingFallSpecial (0x19, his
// landing lag). Once per airtime, shared by the three (brave_hi_used: brave_hi_can, global26). Ledges from frame 11 / 20 / 18 (the game
// script's cliff check; Robin's func_56). In the air while charging: the fall held to 0.3 x (start_max_speed_y_mul_air).
// Motions (ground / air): start 0x260 / 0x26C, hold 0x261 / 0x26D, Woosh 0x25F / 0x26B, Swoosh 0x262 /
// 0x26E, Kaswoosh 0x263 / 0x26F.
int brave_hi_state;
int brave_hi_hold;
int brave_hi_level;
int brave_hi_released;
int brave_hi_tornado;
int brave_hi_launched;
int brave_hi_rising;
int brave_hi_empty;
int brave_hi_cliff;
int brave_hi_used;      // Woosh / Swoosh / Kaswoosh taken off this airtime (fix 60)

// up special allowed (global26, func_72 in the special input checks): once per airtime, back on landing,
// on a ledge, when hit (Damage 0x45 - DamageFall 0x4C) or a new stock (brave_hi_refresh, brave_rebirth)
int brave_hi_can()
{
    if (brave_hi_used)
    {
        return 0;
    }
    return 0x1;
}

void brave_hi_refresh()
{
    if (global18 != 0x2 || global4 >= 0x45 && global4 <= 0x4c)
    {
        brave_hi_used = 0;
    }
}

int brave_hi_jump_motion(int air)
{
    if (brave_hi_empty)
    {
        if (air)
        {
            return 0x247;   // not enough MP: SpecialAirHiEmpty (a hop)
        }
        return 0x221;
    }
    if (brave_hi_level == 0x1)
    {
        if (air)
        {
            return 0x26e;
        }
        return 0x262;
    }
    if (brave_hi_level == 0x2)
    {
        if (air)
        {
            return 0x26f;
        }
        return 0x263;
    }
    if (air)
    {
        return 0x26b;
    }
    return 0x25f;
}

void brave_hi_change(int state)
{
    int g;
    int a;
    brave_hi_state = state;
    g = 0x260;
    a = 0x26c;
    if (state == 0x1)
    {
        g = 0x261;
        a = 0x26d;
    }
    else if (state == 0x2)
    {
        g = brave_hi_jump_motion(0);
        a = brave_hi_jump_motion(0x1);
    }
    WorkModule(0x7, g, 0x11000002);
    WorkModule(0x7, a, 0x11000003);
    if (global18 == 0x2)
    {
        g = a;
    }
    func_22(g, 0, 1.0f);
}

// the level's frames: kind 0 the whirlwind, 1 the rise, 2 ledges
int brave_hi_frame(int kind)
{
    if (brave_hi_level == 0x1)
    {
        if (kind == 0)
        {
            return 0x6;
        }
        if (kind == 0x1)
        {
            return 0xc;
        }
        return 0x14;
    }
    if (brave_hi_level == 0x2)
    {
        if (kind == 0)
        {
            return 0x8;
        }
        if (kind == 0x1)
        {
            return 0xb;
        }
        return 0x12;
    }
    if (kind == 0)
    {
        return 0x4;
    }
    if (kind == 0x1)
    {
        return 0x5;
    }
    return 0xb;
}

void brave_hi_launch()
{
    float v;
    float a;
    v = 3.49f;
    a = 0.145f;
    if (brave_hi_empty)
    {
        v = 1.7f;
    }
    else if (brave_hi_level == 0x1)
    {
        v = 4.525f;
        a = 0.16f;
    }
    else if (brave_hi_level == 0x2)
    {
        v = 4.45f;
        a = 0.1f;
    }
    func_20(0x2);
    GroundModule(0x2710, 0x5);
    KineticModule(0, 0);            // FALL: he drifts as he rises (Ultimate's jump_accel_x_*; AIR_STOP held him)
    KineticModule(0x11, 0x1, v);
    KineticModule(0xf, 0x1, -a);
    brave_hi_launched = 0x1;
    brave_hi_rising = 0x1;
    brave_hi_used = 0x1;
}

void brave_hi_fall()
{
    float m;
    m = 1.4325f;
    if (brave_hi_level == 0x1)
    {
        m = 1.242f;
    }
    else if (brave_hi_level == 0x2)
    {
        m = 1.29f;
    }
    KineticModule(0xf, 0x1, -0.08544f);
    KineticModule(0x14, 0x1, m);
}

// the level held so long (fix 62: not lowered to one his MP pays for, user: that was auto-casting the
// cheaper one, and with Kaswoosh never paid for the charge looped; one he can't pay for is the empty hop)
int brave_hi_hold_level()
{
    int level;
    level = 0;
    if (brave_hi_hold >= 0x1c)
    {
        level = 0x2;
    }
    else if (brave_hi_hold >= 0xa)
    {
        level = 0x1;
    }
    return level;
}

// the strongest level his MP pays for (-1: none); the charge stops there and casts it (fix 57)
int brave_hi_max_level()
{
    int level;
    level = 0x2;
    while (level >= 0 && brave_can_pay(brave_hi_cost(level)) == 0)
    {
        level -= 1;
    }
    return level;
}

int brave_hi_level_frame(int level)
{
    if (level == 0x2)
    {
        return 0x1c;
    }
    if (level == 0x1)
    {
        return 0xa;
    }
    return 0;
}

void brave_hi_loop()
{
    float f;
    int s;
    int top;
    if (brave_hi_state < 0x2)
    {
        func_2245(StatusModule(0x6));
    }
    if (ControlModule(0x2712, 0x1) == 0)
    {
        brave_hi_released = 0x1;
    }
    f = MotionModuleF(0x1);
    if (brave_hi_state == 0)
    {
        brave_mp_pause = 0x1;
        if (MotionModule(0x2712) == 0x1)
        {
            brave_hi_change(0x1);
        }
    }
    else if (brave_hi_state == 0x1)
    {
        brave_hi_hold += 1;
        brave_mp_pause = 0x1;
        brave_cost_view = brave_hi_cost(brave_hi_hold_level());
        top = brave_hi_max_level();
        if (top < 0)
        {
            brave_hi_released = 0x1;    // no level paid for: the empty jump at once (fix 61); otherwise he
                                        // charges on (no casting by itself short of the full hold, 28)
        }
        if (brave_hi_hold >= 0x1c || brave_hi_released)
        {
            brave_hi_level = brave_hi_hold_level();
            if (brave_can_pay(brave_hi_cost(brave_hi_level)))
            {
                brave_pay(brave_hi_cost(brave_hi_level));
            }
            else
            {
                brave_hi_empty = 0x1;
                brave_hi_level = 0;
            }
            brave_hi_change(0x2);
        }
    }
    else
    {
        if (brave_hi_tornado == 0 && brave_hi_empty == 0 && f >= (float)brave_hi_frame(0))
        {
            s = brave_self_slot();
            brave_hi_tornado = 0x1;
            brave_generate(0x8, brave_hi_level + 0x4 * s);
        }
        if (brave_hi_launched == 0 && f >= (float)brave_hi_frame(0x1))
        {
            brave_hi_launch();
        }
        else if (brave_hi_rising && KineticModuleF(0x1, 0x1) <= 0)
        {
            brave_hi_rising = 0;
            brave_hi_fall();
        }
        if (brave_hi_launched)
        {
            if (f >= (float)brave_hi_frame(0x2) && brave_hi_cliff == 0)
            {
                func_100(0x2);      // the game script's cliff check (ALWAYS_BOTH_SIDES): ledges from here
                brave_hi_cliff = 0x1;
            }
            if (brave_hi_cliff && func_56())
            {
                return;
            }
            if (global19 != 0 && global18 == 0)
            {
                func_16(0x19, 0);
                return;
            }
        }
        if (MotionModule(0x2712) == 0x1)
        {
            func_16(0xe, 0);    // a plain Fall: his jumps, attacks and specials (fix 60; Woosh itself waits
            return;             // for the next airtime)
        }
    }
    if (brave_hi_state < 0x2 && global18 == 0x2)
    {
        KineticModule(0x14, 0x1, 0.45f);
    }
}

int brave_hi_pre()
{
    printf("status_pre_SpecialHi (Hero)");
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x11422, 0x1000, 0x100, 0x1000);
    return 0;
}

void brave_hi_main()
{
    printf("status_SpecialHi (Hero)");
    brave_hi_state = 0;
    brave_hi_hold = 0;
    brave_hi_level = 0;
    brave_hi_released = 0;
    brave_hi_tornado = 0;
    brave_hi_launched = 0;
    brave_hi_rising = 0;
    brave_hi_empty = 0;
    brave_hi_cliff = 0;
    WorkModule(0x7, 0x260, 0x11000002);
    WorkModule(0x7, 0x26c, 0x11000003);
    WorkModule(0x7, 0x6, 0x11000004);
    WorkModule(0x7, 0xa, 0x11000005);
    WorkModule(0x7, 0x2, 0x11000006);
    WorkModule(0x7, 0x5, 0x11000007);
    func_2245(0x1);
    func_78(brave_hi_loop);
}

// ---- Hero's down special: Command Selection (status 0x155, Robin's Nosferatu; fighters/brave/README.md).
// SpecialLwStart (20 frames) then SpecialLwSelect (a loop) with the menu open: four of the 21 spells drawn at
// random, weighted by Ultimate's param_special_lw_command_data lot_prob (brave_lw_weight), the ones his MP
// doesn't pay for greyed out and put last; shown in his damage panel (brave_panel_update). The stick (up /
// down past 0.5, again every 12 frames while held) moves the cursor; attack, or special once it has been
// let go, casts the spell (its row stays up 70 frames, decided_command_window_close_frame; a greyed one:
// SpecialLwFail); shield, jump, or 480 frames (command_select_time_limit, blinking from 360) shuts it:
// SpecialLwCancel. His MP doesn't come back while the menu is open. The spells' motions, ground / air: start
// 0x277 / 0x283, select 0x278 / 0x284, cancel 0x279 / 0x285, then spell n at its slot (brave_lw_spell_motion,
// extra_kinds.json "motions"). In the air the fall is held to 0.45 while choosing. The spells (brave_lw_cast):
//  1 Heal          11% healed at frame 6 (param_special_lw cure_add_life)
//  2 / 3 Sizz / Sizzle      the flash article (9, weapons/shot.c) at frame 6
//  4 / 5 Bang / Kaboom      the explosion article (10) at frame 6
//  6 / 7 Whack / Thwack     the deathball article (11) at frame 6: a fighter it hits may be KO'd outright
//                  (a Death hitbox, effect 0x10: weapons/deathball.c)
//  8 Magic Burst   all his MP; the crash article (12, weapons/crash.c) on him at frame 20, its damage x the MP
//                  spent / 100 (in fifths: brave_burst_motion), held in the air
//                  until frame 136 (FULLBURST_INTERRUPT / ENABLE_GRAVITY)
//  9 Kamikazee     the crash article's blast (level 1) at frame 20, then he's KO'd on the spot (DEATH_RESERVE:
//                  brave_self_ko)
// 10 Kaclang       steel from SpecialLw10Start's end: invincible for 300 frames (steel_frame) in
//                  SpecialLw10 (falling fast in the air), then SpecialLw10End
// 11 Acceleratle   600 frames faster (speed_up_frame; tools/kirby_stat_cave.py profile 3)
// 12 Oomph         720 frames of x1.15 damage (attack_up_frame; tools/strike_cave.py)
// 13 Bounce        720 frames of a reflector (reflect_frame; brave_reflect)
// 14 Snooze        the sleep article (13) at frame 6: its gust puts fighters to sleep
// 15 Hocus Pocus   Ultimate's outcomes and odds (brave_hocus_pocus): giant, Starman, full MP, timer, no MP,
//                  poison, sleep, small, flower, invisible, or another spell cast for its 4 MP
// 16 Zoom          up off the screen (SpecialLw16Hi, flying_speed_y 9, intangible), then down (SpecialLw16Lw,
//                  flying_down_speed_y 7) above a fighter on the ground, landing with SpecialLw16End
// 17 - 20 Flame Slash, Kacrackle Slash, Metal Slash, Hatchet Man (sword moves: their hitboxes are in
//                  their scripts, Ultimate's SpecialLw17-20)
// 21 Psyche Up     x1.15 damage until his next hit lands
int brave_lw_state;
int brave_lw_frame;
int brave_lw_cursor;
int brave_lw_spells;
int brave_lw_spell;
int brave_lw_released;
int brave_lw_stick;
int brave_lw_repeat;
int brave_lw_done;
int brave_lw_sub;
int brave_lw_t;
int brave_lw_burst;     // Magic Burst: the MP it took

// a spell's draw weight (Ultimate's lot_prob)
int brave_lw_weight(int n)
{
    if (n == 0x1) { return 0x7; }
    if (n == 0x2 || n == 0x4 || n == 0xb || n == 0xc || n == 0xd || n == 0x15) { return 0x10; }
    if (n == 0x3 || n == 0x5) { return 0x14; }
    if (n == 0x6) { return 0xc; }
    if (n == 0x7) { return 0x8; }
    if (n == 0x8 || n == 0x9 || n == 0xa) { return 0x5; }
    if (n == 0xe) { return 0x11; }
    if (n == 0xf) { return 0x3; }
    if (n == 0x10) { return 0xf; }
    if (n == 0x11 || n == 0x12 || n == 0x14) { return 0x12; }
    if (n == 0x13) { return 0x7; }
    return 0;
}

// a spell's motion (0 ground, 1 air); 0 = SpecialLwFail's
int brave_lw_spell_motion(int n, int air)
{
    int g;
    int a;
    g = 0x220;
    a = 0x246;
    if (n == 0x1) { g = 0x222; a = 0x248; }
    else if (n == 0x2) { g = 0x224; a = 0x249; }
    else if (n == 0x3) { g = 0x225; a = 0x24a; }
    else if (n == 0x4) { g = 0x226; a = 0x24e; }
    else if (n == 0x5) { g = 0x22a; a = 0x24f; }
    else if (n == 0x6) { g = 0x22b; a = 0x250; }
    else if (n == 0x7) { g = 0x22c; a = 0x251; }
    else if (n == 0x8) { g = 0x22d; a = 0x252; }
    else if (n == 0x9) { g = 0x22e; a = 0x253; }
    else if (n == 0xa) { g = 0x232; a = 0x254; }
    else if (n == 0xb) { g = 0x235; a = 0x264; }
    else if (n == 0xc) { g = 0x236; a = 0x265; }
    else if (n == 0xd) { g = 0x237; a = 0x266; }
    else if (n == 0xe) { g = 0x238; a = 0x267; }
    else if (n == 0xf) { g = 0x239; a = 0x268; }
    else if (n == 0x10) { g = 0x23a; a = 0x269; }
    else if (n >= 0x11 && n <= 0x14) { g = 0x27a + n - 0x11; a = g + 0xc; }
    else if (n == 0x15) { g = 0x240; a = 0x26a; }
    if (air)
    {
        return a;
    }
    return g;
}

// row k's spell (0-3)
int brave_lw_row(int k)
{
    int v;
    int i;
    v = brave_lw_spells;
    i = 0;
    while (i < k)
    {
        v = v / 0x20;
        i += 1;
    }
    return v % 0x20;
}

// the rows his MP doesn't pay for (bit k: row k)
int brave_lw_grey()
{
    int k;
    int n;
    int g;
    g = 0;
    k = 0;
    while (k < 0x4)
    {
        n = brave_lw_row(k);
        if (n != 0 && brave_can_pay(brave_cost(n)) == 0)
        {
            g = g + brave_bit(k);
        }
        k += 1;
    }
    return g;
}

// four spells, weighted, no repeats; then the ones he can pay for first
void brave_lw_draw()
{
    int k;
    int n;
    int total;
    int r;
    int taken;
    int pick;
    int mul;
    int pass;
    int drawn;
    brave_lw_spells = 0;
    taken = 0;
    mul = 0x1;
    k = 0;
    while (k < 0x4)
    {
        total = 0;
        n = 0x1;
        while (n <= 0x15)
        {
            if ((taken / brave_bit(n)) % 0x2 == 0)
            {
                total = total + brave_lw_weight(n);
            }
            n += 1;
        }
        pick = 0;
        if (total > 0)
        {
            r = randi(0, total);
            n = 0x1;
            while (n <= 0x15 && pick == 0)
            {
                if ((taken / brave_bit(n)) % 0x2 == 0)
                {
                    r = r - brave_lw_weight(n);
                    if (r < 0)
                    {
                        pick = n;
                    }
                }
                n += 1;
            }
        }
        if (pick != 0)
        {
            taken = taken + brave_bit(pick);
            brave_lw_spells = brave_lw_spells + pick * mul;
        }
        mul = mul * 0x20;
        k += 1;
    }
    drawn = brave_lw_spells;
    brave_lw_spells = 0;
    mul = 0x1;
    pass = 0;
    while (pass < 0x2)
    {
        k = 0;
        while (k < 0x4)
        {
            n = (drawn / brave_bit(0x5 * k)) % 0x20;
            if (n != 0 && brave_can_pay(brave_cost(n)) == 1 - pass)
            {
                brave_lw_spells = brave_lw_spells + n * mul;
                mul = mul * 0x20;
            }
            k += 1;
        }
        pass += 1;
    }
}

// the state's motions from frame 0 (ground / air: func_2245 swaps them)
void brave_lw_motion(int g, int a)
{
    WorkModule(0x7, g, 0x11000002);
    WorkModule(0x7, a, 0x11000003);
    if (global18 == 0x2)
    {
        g = a;
    }
    func_22(g, 0, 1.0f);
}

void brave_lw_change(int state, int g, int a)
{
    brave_lw_state = state;
    brave_lw_frame = 0;
    brave_lw_motion(g, a);
}

// the cursor: up / down past half, again every 12 frames held; rows with no spell skipped
// the buttons buffered so far dropped (as Robin's item pick-up, func_103): the menu's shield cancel was
// shielding afterwards, and the special press picking a spell (Hocus Pocus) starting Frizz after it
void brave_clear_input()
{
    ControlModule(0x271b);
    ControlModule(0x271f);
    global24 = 0;
    global31 = 0;
    global29 = 0;
    global45 = 0;
    global38 = 0;
}

void brave_lw_move()
{
    int dir;
    int i;
    dir = 0;
    if (global32 > 0.5f)
    {
        dir = -1;
    }
    else if (global32 < -0.5f)
    {
        dir = 0x1;
    }
    if (brave_lw_stick == 0x2)
    {
        // the stick still held from down special's input: nothing until it's let go
        if (dir == 0)
        {
            brave_lw_stick = 0;
        }
        return;
    }
    if (dir == 0)
    {
        brave_lw_stick = 0;
        return;
    }
    if (dir == brave_lw_stick)
    {
        brave_lw_repeat += 1;
        if (brave_lw_repeat < 0xc)
        {
            return;
        }
    }
    brave_lw_stick = dir;
    brave_lw_repeat = 0;
    i = 0;
    while (i < 0x4)
    {
        brave_lw_cursor = (brave_lw_cursor + dir + 0x4) % 0x4;
        if (brave_lw_row(brave_lw_cursor) != 0)
        {
            return;
        }
        i += 1;
    }
}

// the first time this cast gets here (bit: 1, 2, 4, ...)
int brave_lw_once(int bit)
{
    if ((brave_lw_done / bit) % 0x2 == 0x1)
    {
        return 0;
    }
    brave_lw_done = brave_lw_done + bit;
    return 0x1;
}

// his player slot for an article put on him (placed.c: 8 = none, it stays where it's made)
int brave_lw_slot()
{
    int s;
    s = brave_self_slot();
    if (s < 0)
    {
        s = 0x8;
    }
    return s;
}

// Heal: his damage down by v, with the common healing sparkle (GFX 0x35, a food's) on his hip: Ultimate
// plays its glow from the status code, not the script (fix 57: none showed)
void brave_heal(float v)
{
    float d;
    d = WorkModuleF(0, 0x0f000117) - v;
    if (d < 0)
    {
        d = 0;
    }
    WorkModule(0, d, 0x0f000117);
    EffectModule(0x2717, 0x1000035, 0x3, 0, 0, 0, 0, 0, 0, 1.0f, 0);
}

// Kamikazee: KO'd on the spot, as in Stamina mode (instance flag 0x20000043, "causes KO": the fighter
// explodes as if KO'd; the user's Captain Falcon's 1-in-100 jab sets it the same way)
void brave_self_ko()
{
    WorkModule(0x2710, 0x20000043);
}

// Zoom's landing place: above a fighter on the ground (at random), else the stage's middle
void brave_zoom_place()
{
    int s;
    int count;
    int pick;
    float x;
    float y;
    count = 0;
    s = 0;
    while (s < 0x8)
    {
        if (s != brave_slot && WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0 && WorkModuleF(0, 0x0f000176 + 0x20 * s) < 0.5f)
        {
            count += 1;
        }
        s += 1;
    }
    x = 0;
    y = 60.0f;
    if (count > 0)
    {
        pick = randi(0, count);
        s = 0;
        while (s < 0x8)
        {
            if (s != brave_slot && WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0 && WorkModuleF(0, 0x0f000176 + 0x20 * s) < 0.5f)
            {
                if (pick == 0)
                {
                    x = WorkModuleF(0, 0x0f000020 + 0x4 * s);
                    y = WorkModuleF(0, 0x0f000021 + 0x4 * s);
                }
                pick -= 1;
            }
            s += 1;
        }
    }
    WorkModule(0, x, 0x0f000000);
    WorkModule(0, y + 120.0f, 0x0f000001);
}

// flying straight up / down at v (no gravity)
void brave_fly(float v)
{
    KineticModule(0xf, 0x1, 0);
    KineticModule(0x14, 0x1, 10.0f);
    KineticModule(0x11, 0x1, v);
}

// Hocus Pocus (Ultimate's outcomes and odds, SmashWiki "Hocus Pocus effects", in 1/100 %): giant 4.88, Starman
// 1.22, full MP 3.96, timer 6.10, no MP 6.10, poison 6.10, sleep 6.10, small 5.49, flower 6.10, invisible 6.10;
// or another spell, cast for the 4 MP Hocus Pocus took (Heal / Kaclang 1.52, Kamikazee 0.91, every other one
// 2.44; Magic Burst still takes all the MP): he casts it then and there (its motion and its part)
int brave_hp_weight(int o)
{
    if (o == 0) { return 0x1e8; }               // giant 488
    if (o == 0x1) { return 0x7a; }              // Starman 122
    if (o == 0x2) { return 0x18c; }             // full MP 396
    if (o == 0x7) { return 0x225; }             // small 549
    if (o <= 0x9) { return 0x262; }             // timer, no MP, poison, sleep, flower, invisible: 610
    o = o - 0x9;                                // 10 + the spell (1-21)
    if (o == 0x1 || o == 0xa) { return 0x98; }  // Heal, Kaclang 152
    if (o == 0x9) { return 0x5b; }              // Kamikazee 91
    if (o == 0xf) { return 0; }                 // not itself
    return 0xf4;                                // 244
}

// a spell picked by Hocus Pocus: from its frame 0, as if chosen
void brave_hp_cast(int n)
{
    if (n == 0x8)
    {
        brave_lw_burst = (int)(brave_mp + 0.999f) + 0x4;
        brave_mp = 0;
    }
    brave_lw_spell = n;
    brave_lw_done = 0;
    brave_lw_sub = 0;
    brave_lw_t = 0;
    brave_lw_motion(brave_lw_spell_motion(n, 0), brave_lw_spell_motion(n, 0x1));
}

void brave_hocus_pocus()
{
    int o;
    int r;
    int total;
    total = 0;
    o = 0;
    while (o <= 0x1e)
    {
        total = total + brave_hp_weight(o);
        o += 1;
    }
    r = randi(0, total);
    o = 0;
    while (o < 0x1e && r >= brave_hp_weight(o))
    {
        r = r - brave_hp_weight(o);
        o += 1;
    }
    if (o >= 0xa)
    {
        brave_hp_cast(o - 0x9);
        return;
    }
    if (o == 0x2) { brave_mp = 100.0f; }
    else if (o == 0x4) { brave_mp = 0; }
    else if (o == 0x5) { brave_poison_t = 0x1f4; }
    else { brave_state(o); }    // the item-like states (brave_state)
}

// Kaclang: 0 SpecialLw10Start (steel from frame 20; in the air a hop of 3.4 at frame 10), 1 SpecialLw10
// for 300 frames (5 seconds): metal, invincible, no action; in the air SpecialAirLw10 (its hitbox) falling
// with left / right control (kinetic type 0, Ultimate's ENABLE_CONTROL_ENERGY) until he lands; 2
// SpecialLw10End
int brave_kaclang(float f)
{
    if (brave_lw_sub < 0x2 && (brave_lw_sub == 0x1 || f >= 20.0f))
    {
        WorkModule(0, 2.0f, 0x0f00011c);    // invincible, renewed each frame
        brave_metal(0x1);
    }
    if (brave_lw_sub == 0)
    {
        if (global18 == 0x2 && f >= 10.0f && brave_lw_once(0x1))
        {
            KineticModule(0x11, 0x1, 3.4f);
        }
        if (MotionModule(0x2712) == 0x1)
        {
            brave_lw_sub = 0x1;
            brave_lw_t = 0;
            brave_lw_motion(0x233, 0x255);
        }
        return 0x2;
    }
    if (brave_lw_sub == 0x1)
    {
        brave_lw_t += 1;
        if (global18 == 0x2)
        {
            if (brave_lw_once(0x2))
            {
                KineticModule(0, 0);        // FALL: left / right control
            }
            KineticModule(0xf, 0x1, -0.2f);
            KineticModule(0x14, 0x1, 3.0f);
        }
        if (brave_lw_t >= 0x12c)
        {
            brave_lw_sub = 0x2;
            brave_metal(0);
            brave_lw_motion(0x234, 0x256);
            KineticModule(0xf, 0x1, -0.089f);
            KineticModule(0x14, 0x1, 1.5f);
        }
        else if (MotionModule(0x2712) == 0x1)
        {
            brave_lw_motion(0x233, 0x255);  // the loop
        }
        return 0x2;
    }
    return 0;
}

// Zoom: 0 SpecialLw16Start, 1 SpecialLw16Hi (up for 40 frames), 2 SpecialLw16Lw (down to the ground), 3 End
int brave_zoom(float f)
{
    if (brave_lw_sub == 0x1 || brave_lw_sub == 0x2)
    {
        WorkModule(0, 2.0f, 0x0f00011b);    // intangible, renewed each frame
    }
    if (brave_lw_sub == 0)
    {
        if (MotionModule(0x2712) == 0x1)
        {
            brave_lw_sub = 0x1;
            brave_lw_t = 0;
            brave_lw_motion(0x23c, 0x23c);
            func_20(0x2);
            GroundModule(0x2710, 0x5);
            KineticModule(0, 0xa);
            brave_fly(9.0f);
        }
        return 0x2;
    }
    if (brave_lw_sub == 0x1)
    {
        brave_lw_t += 1;
        brave_fly(9.0f);
        if (brave_lw_t >= 0x28)
        {
            brave_lw_sub = 0x2;
            brave_lw_t = 0;
            brave_zoom_place();
            brave_lw_motion(0x23d, 0x23d);
            brave_fly(-7.0f);
        }
        return 0x2;
    }
    if (brave_lw_sub == 0x2)
    {
        brave_lw_t += 1;
        if (global18 == 0)
        {
            brave_lw_sub = 0x3;
            brave_lw_motion(0x23e, 0x23e);
            return 0x2;
        }
        if (brave_lw_t > 0x96)
        {
            KineticModule(0xf, 0x1, -0.089f);
            KineticModule(0x14, 0x1, 1.5f);
            func_16(0xe, 0);    // no ground under him: falling
            return 0x1;
        }
        brave_fly(-7.0f);
        return 0x2;
    }
    return 0;
}

// Magic Burst's blast for the MP it took (weapons/crash.c): 81-100 the full one (motion 0), else 20 / 40 / 60 /
// 80 % of its damage (motions 3-6), the MP rounded up to the next 20
int brave_burst_motion()
{
    if (brave_lw_burst > 0x50)
    {
        return 0;
    }
    if (brave_lw_burst > 0x3c)
    {
        return 0x6;
    }
    if (brave_lw_burst > 0x28)
    {
        return 0x5;
    }
    if (brave_lw_burst > 0x14)
    {
        return 0x4;
    }
    return 0x3;
}

// the spell's own part, each frame of the cast: 0 on as usual, 1 the status changed, 2 its motion goes on
int brave_lw_cast(float f)
{
    int n;
    n = brave_lw_spell;
    if (n == 0x1)
    {
        if (f >= 6.0f && brave_lw_once(0x1))
        {
            brave_heal(11.0f);
        }
    }
    else if (n == 0x2 || n == 0x3)
    {
        if (f >= 6.0f && brave_lw_once(0x1))
        {
            brave_generate(0x9, n - 0x2);
        }
    }
    else if (n == 0x4 || n == 0x5)
    {
        if (f >= 6.0f && brave_lw_once(0x1))
        {
            brave_generate(0xa, n - 0x4);
        }
    }
    else if (n == 0x6 || n == 0x7)
    {
        if (f >= 6.0f && brave_lw_once(0x1))
        {
            brave_generate(0xb, n - 0x6 + 0x4 * brave_lw_slot());
        }
    }
    else if (n == 0x8)
    {
        if (f >= 20.0f && brave_lw_once(0x1))
        {
            brave_generate(0xc, brave_burst_motion() + 0x8 * brave_lw_slot());
        }
        if (global18 == 0x2 && f >= 20.0f && f < 136.0f)
        {
            KineticModule(0xf, 0x1, 0);
            KineticModule(0x11, 0x1, 0);
        }
        if (f >= 136.0f && brave_lw_once(0x2))
        {
            KineticModule(0xf, 0x1, -0.089f);
            KineticModule(0x14, 0x1, 1.5f);
        }
    }
    else if (n == 0x9)
    {
        if (f >= 20.0f && brave_lw_once(0x1))
        {
            brave_generate(0xc, 0x1 + 0x8 * brave_lw_slot());
        }
        if (MotionModule(0x2712) == 0x1 && brave_lw_once(0x2))
        {
            brave_self_ko();    // DEATH_RESERVE: at the motion's end
        }
        return 0x1;             // no acting out of it (func_2246's cancel frame let him escape the blast, fix 57)
    }
    else if (n == 0xa)
    {
        return brave_kaclang(f);
    }
    else if (n == 0xb)
    {
        if (f >= 11.0f && brave_lw_once(0x1))
        {
            brave_speed_t = 0x258;
            brave_glow(0x345007b, 0x1);
        }
    }
    else if (n == 0xc)
    {
        if (f >= 11.0f && brave_lw_once(0x1))
        {
            brave_attack_t = 0x2d0;
            brave_glow(0x345007a, 0x1);
        }
    }
    else if (n == 0xd)
    {
        if (f >= 11.0f && brave_lw_once(0x1))
        {
            brave_reflect_t = 0x2d0;
            brave_reflect(0x1);
        }
    }
    else if (n == 0xe)
    {
        if (f >= 6.0f && brave_lw_once(0x1))
        {
            brave_generate(0xd, 0);
        }
    }
    else if (n == 0xf)
    {
        if (f >= 1.0f && brave_lw_once(0x1))
        {
            brave_hocus_pocus();
        }
    }
    else if (n == 0x10)
    {
        return brave_zoom(f);
    }
    else if (n == 0x15)
    {
        if (f >= 6.0f && brave_lw_once(0x1))
        {
            brave_psyche = 0x1;
            brave_glow(0x345004e, 0x1);     // brave_charge_hold, until the hit that spends it
        }
    }
    return 0;
}

void brave_lw_loop()
{
    int n;
    int r;
    func_2245(StatusModule(0x6));
    brave_lw_frame += 1;
    if (ControlModule(0x2712, 0x1) == 0)
    {
        brave_lw_released = 0x1;
    }
    if (brave_lw_state < 0x2)
    {
        brave_mp_pause = 0x1;
        if (brave_lw_state == 0 && MotionModule(0x2712) == 0x1)
        {
            brave_lw_change(0x1, 0x278, 0x284);
        }
        brave_lw_move();
        n = brave_lw_row(brave_lw_cursor);
        brave_menu_cursor = brave_lw_cursor;
        brave_menu_grey = brave_lw_grey();
        brave_cost_view = brave_cost(n);
        if (ControlModule(0x2710, 0x3) || ControlModule(0x2710, 0x2) || brave_lw_frame >= 0x1e0 && brave_lw_state == 0x1)
        {
            brave_clear_input();
            brave_menu_close();
            brave_lw_change(0x3, 0x279, 0x285);
            return;
        }
        if (n != 0 && (ControlModule(0x2710, 0) || brave_lw_released && ControlModule(0x2710, 0x1)))
        {
            // the cast: only its row stays up; he turns round to a stick held back (Ultimate's command
            // spells do)
            brave_clear_input();
            if (ControlModuleF(0) < -0.5f)
            {
                PostureModule(0, -PostureModuleF(0x7));
                PostureModule(0x2);
            }
            brave_menu = 0x2;
            brave_menu_rows = n * brave_bit(0x5 * brave_lw_cursor);
            brave_menu_grey = (brave_menu_grey / brave_bit(brave_lw_cursor)) % 0x2 * brave_bit(brave_lw_cursor);
            if (brave_can_pay(brave_cost(n)))
            {
                brave_lw_burst = (int)(brave_mp + 0.999f);  // Magic Burst: all of it, rounded up
                brave_pay(brave_cost(n));
                if (n == 0x8)
                {
                    brave_mp = 0;
                }
            }
            else
            {
                n = 0;      // SpecialLwFail
            }
            brave_lw_spell = n;
            brave_lw_done = 0;
            brave_lw_sub = 0;
            brave_lw_t = 0;
            brave_lw_change(0x2, brave_lw_spell_motion(n, 0), brave_lw_spell_motion(n, 0x1));
            return;
        }
        if (global18 == 0x2)
        {
            KineticModule(0x14, 0x1, 0.45f);
        }
        return;
    }
    if (brave_lw_state == 0x2)
    {
        if (brave_lw_frame >= 0x46)
        {
            brave_menu_close();
        }
        r = brave_lw_cast(MotionModuleF(0x1));
        if (r == 0x1)
        {
            return;
        }
        if (r == 0x2)
        {
            return;
        }
    }
    if (func_2246())
    {
        return;
    }
}

int brave_lw_pre()
{
    printf("status_pre_SpecialLw (Hero)");
    StatusModule(0x5, 0xffffffff, 0x32, 0x7, 0, 0x1, 0, 0, 0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x1190, 0x1000, 0x80, 0x1000);
    return 0;
}

void brave_lw_main()
{
    printf("status_SpecialLw (Hero)");
    brave_lw_state = 0;
    brave_lw_frame = 0;
    brave_lw_cursor = 0;
    brave_lw_spell = 0;
    brave_lw_released = 0;
    brave_lw_stick = 0x2;           // brave_lw_move: wait for the stick to come back first
    brave_lw_repeat = 0;
    brave_lw_done = 0;
    brave_lw_sub = 0;
    brave_lw_t = 0;
    brave_lw_draw();
    WorkModule(0x7, 0x277, 0x11000002);
    WorkModule(0x7, 0x283, 0x11000003);
    WorkModule(0x7, 0x6, 0x11000004);
    WorkModule(0x7, 0xa, 0x11000005);
    WorkModule(0x7, 0x2, 0x11000006);
    WorkModule(0x7, 0x5, 0x11000007);
    func_2245(0x1);
    brave_menu_open(brave_lw_spells, 0);
    brave_menu_grey = brave_lw_grey();
    func_78(brave_lw_loop);
}

void brave_lw_end()
{
    brave_menu_close();
    brave_metal(0);         // out of Kaclang early: the Metal Box flag off
    if (brave_lw_spell == 0x8 || brave_lw_spell == 0xa || brave_lw_spell == 0x10)
    {
        // out of Magic Burst's hover / Kaclang's fall / Zoom's flight early (hit): his own fall again
        KineticModule(0xf, 0x1, -0.089f);
        KineticModule(0x14, 0x1, 1.5f);
    }
}
