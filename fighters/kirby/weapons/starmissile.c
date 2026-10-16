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
    global7 = 0x2;
    func_44();
    func_45();
    func_42();
}

void func_44()
{
    sv_set_mem(0x1, 0, 0, func_49);
    sv_set_mem(0x1, 0x1, 0, func_50);
    sv_set_mem(0x1, 0x2, 0, func_53);
    sv_set_mem(0x1, 0, 0x1, func_54);
    sv_set_mem(0x1, 0x1, 0x1, func_55);
    sv_set_mem(0x1, 0x2, 0x1, func_58);
}

void func_45()
{
    sv_set_mem(0x1, 0x3, 0, func_59);
    sv_set_mem(0x1, 0x4, 0, func_60);
    sv_set_mem(0x1, 0x6, 0, func_62);
    sv_set_mem(0x1, 0x5, 0, func_61);
    sv_set_mem(0x1, 0x7, 0, func_48);
    sv_set_mem(0x1, 0x8, 0, func_48);
    sv_set_mem(0x1, 0x3, 0x1, func_59);
    sv_set_mem(0x1, 0x4, 0x1, func_60);
    sv_set_mem(0x1, 0x6, 0x1, func_62);
    sv_set_mem(0x1, 0x5, 0x1, func_61);
    sv_set_mem(0x1, 0x7, 0x1, func_48);
    sv_set_mem(0x1, 0x8, 0x1, func_48);
}

void func_46()
{
    
}

void func_47()
{
    
}

void func_48()
{
    
}

int func_49()
{
    StatusModule(0x5, 0x2, 0, 0x5, 0, 0, 0xffffffff, 0xffffffff, 0xffffffff, 0);
    return 0;
}

void func_50()
{
    func_24(0, 0, 1.0f);
    callFunc3(func_51);
}

void func_51()
{
    
}

void func_52()
{
    
}

void func_53()
{
    
}

int func_54()
{
    StatusModule(0x5, 0x2, 0xffffffff, 0x5, 0, 0, 0xffffffff, 0xffffffff, 0xffffffff, 0);
    return 0;
}

void func_55()
{
    func_24(0x4, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_57();
    }
    global16 = func_57;
    callFunc3(func_56);
}

void func_56()
{
    
}

// [starmissile status 1 per-frame] count down lifetime 0x11000002; remove the star at 0 or on touching ground
void func_57()
{
    // Aim (added): Kirby passes the stick angle in int 0x11000000 (1000 + degrees + 90, see
    // starmissile_aim_code in kirby.c); that int is also the damage the game applies, so put
    // the real damage back on the first frame and keep the angle in global17 (unused before):
    // 0 = not read yet, -1 = done / no aim, 1000+ = angle code still to apply.
    if (global17 == 0)
    {
        global17 = WorkModule(0x6, 0x11000000);
        if (global17 >= 1000)
        {
            WorkModule(0x7, starmissile_damage(), 0x11000000);
        }
        else
        {
            global17 = -1;
        }
    }
    if (global17 >= 1000 && starmissile_aim(global17 - 1090))
    {
        global17 = -1;
    }
    // Disappear when the hitbox connects (added).
    if (AttackModule(0x2726) || AttackModule(0x2727, 0x2))
    {
        // Copy-ability counter (added, needs the patched cross_f.rpx): native code reads this
        // star's newest hit target and counts the hit on the owner Kirby; on the 12th it hands
        // Kirby that fighter's copy ability. Without the RPX patch this command does nothing.
        BattleObject(0x1f4);
        BattleObject(0x9);
        return;
    }
    // Damage: the game sets the hitbox power from int 0x11000000 itself (0x02B03888), which
    // overrode an AttackModule set here. Kirby's MSC sets it at spawn (starmissile_power in kirby.c).
    WorkModule(0xa, 0x11000002);
    if (WorkModule(0x6, 0x11000002) <= 0)
    {
        BattleObject(0x9);
    }
    else if (GroundModule(0x2722, 0xff))
    {
        BattleObject(0x9);
    }
}

void func_58()
{
    
}

// [starmissile init, both statuses] status 1 (flying) sets the lifetime
void func_59()
{
    WorkModule(0x2711, 0x21000000);
    if (global4 == 0)
    {
        
    }
    else if (global4 == 0x1)
    {
        // Lifetime of the flying star in frames (counted down in func_57; at 0 the star is removed).
        // Was WorkModule(0x6, 0x12000013), the weapon parameter.
        WorkModule(0x7, 24, 0x11000002);
    }
}

void func_60()
{
    float var0;
    float var1;
    float var2;
    float var3;
    float var4;
    float var5;
    float var6;
    float var7;
    if (WorkModule(0x6, 0x11000001) == 0x2)
    {
        var0 = WorkModuleF(0, 0x1000002);
        var1 = var0 + WorkModuleF(0, 0x200000d);
        if (var1 > 360.0f)
        {
            var1 -= 360.0f;
        }
        var2 = var0 + var1;
        if (PostureModuleF(0) == 1.0f)
        {
            var2 = -var2;
        }
        PostureModule(0x4, 0, 0, var2 + 0);
        WorkModule(0, var1 + 0, 0x1000002);
    }
    else
    {
        var3 = KineticModuleF(0xa, 0);
        var4 = KineticModuleF(0xb, 0);
        var5 = WorkModuleF(0, 0x1000000);
        var6 = PostureModuleF(0);
        var7 = MathF(0x3, var3, var4, 0);
        if (var7 > var5)
        {
            var3 = var3 * (var7 - var5) / var7;
            var4 = var4 * (var7 - var5) / var7;
        }
        else
        {
            var3 = 0;
        }
        KineticModule(0x11, 0, var3, var4);
        var0 = WorkModuleF(0, 0x1000002);
        var1 = var0 + WorkModuleF(0, 0x200000d);
        if (var1 > 360.0f)
        {
            var1 -= 360.0f;
        }
        var2 = var0 + var1;
        if (PostureModuleF(0) == 1.0f)
        {
            var2 = -var2;
        }
        PostureModule(0x4, 0, 0, var2 + 0);
        WorkModule(0, var1 + 0, 0x1000002);
    }
}

void func_61()
{
    float var0;
    float var1;
    var0 = WorkModuleF(0, 0x1000002);
    var1 = var0;
    if (PostureModuleF(0) == 1.0f)
    {
        var1 = -var1;
    }
    PostureModule(0x4, 0, 0, var1 + 0);
}

void func_62()
{
    if (WorkModule(0x10, 0x21000000) == 0)
    {
        LinkModule(0x4, 0, 0x1b, 0);
        WorkModule(0x2710, 0x21000000);
    }
}


int starmissile_damage() { return 2; } // keep equal to starmissile_power() in kirby.c (whole numbers)

// Turn the star's current speed (energy 0) to deg degrees above (+) / below (-) forward, keeping
// its speed. Forward = the sign of its horizontal speed. Returns 0 while it has no speed yet.
int starmissile_aim(int deg)
{
    float vx;
    float vy;
    float speed;
    float ang;
    float fwd;
    vx = KineticModuleF(0xa, 0);
    vy = KineticModuleF(0xb, 0);
    speed = MathF(0x3, vx, vy, 0); // length of (vx, vy)
    if (speed < 0.01f)
    {
        return 0;
    }
    fwd = 1.0f;
    if (vx < 0)
    {
        fwd = -1.0f;
    }
    ang = (float)deg * 0.017453292f;
    KineticModule(0x11, 0, MathF(0x4, ang) * speed * fwd, MathF(0x5, ang) * speed);
    return 0x1;
}
