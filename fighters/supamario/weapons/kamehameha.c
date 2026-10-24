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

// ---------------------------------------------------------------------------------------------
// Supamario's Kamehameha (weapon kind 0x18B, article 5): a copy of the fireball's boilerplate
// (func_0 - func_40) and its own statuses. tools/supamario_kame_build.py replaces the KAME_* names.
//   0 / 1 / 2  fly (charge level 1 / 2 / 3; it is generated in 0 and the fighter sets its level's
//              status in the same frame): flies straight at KAME_SPEED_n for KAME_LIFE_n frames,
//              motion fly1 / fly2 / fly3: its ACMD has the head / start effects and the multi-hit
//              hitboxes; this script drops a body piece (KAME_SEG_n) at the head every
//              KAME_SEG_EVERY frames. Its range reached, or touching a wall (GroundModule 0x2722, as
//              the fireball's MSC checks it), it ends where it is.
//   3          hold: the beam connected (native: weapon_expand's on_hit asks for status 3 instead of
//              removing it), stays in place KAME_HOLD_n frames (more hits the longer the charge), still
//              multi-hitting: its fly motion starts again (test 18: its following head effects ended
//              with the status change and the MSC's still copies stayed after the beam; the fly ACMD
//              puts the head back, following, and its head hitbox, which holds the target, hits every
//              REHIT frames; no more body pieces)
//   4          finish: motion finish (its ACMD ends the beam's effects, the launcher)
// The end (the finish, or the range / a wall): the body pieces are replaced by dissolving ones
// (KAME_DIS_n, at the same places: they flash bright, go transparent and thin to a white line) and
// every other effect of the beam ends; the beam stays, without hitboxes, until they're done
// (KAME_DISSOLVE frames), then it is removed. The head / start / body effects have Terminate 1, so
// they also end when the game removes the beam (test 16: past a blast zone they stayed). KAME_MAX
// frames after it was fired it is removed whatever happened.
// Status changes: kame_status() = StatusModule(0x3, status, 0) (func_18 / func_19, as the vanilla weapon
// MSCs change theirs); the boilerplate's func_22 is StatusModule(0x2), the situation (tests 10 - 14
// used it: the hold never became the finish, and since test 12 the fallback removed the beam).
// kame_phase: 0 fly, 1 hold, 2 finish, 3 dissolving after the range / a wall. Reset when status 0 is
// entered (a new beam: weapons are pooled, so the last beam's values may still be here); keeps hold /
// finish from restarting if their status is entered again (test 10: the beam held and multi-hit for
// ever).
int kame_level;
int kame_frame;
int kame_life;
int kame_phase;
int kame_total;
int kame_flown;

void main()
{
    printf("ENTRY This Fighter is driven by msc.");
    func_0();
    global0 = sys_7(0);
    global1 = sys_7(0x1);
    kame_setup();
    sys_0(0x2, func_3);
    sys_0(0x3, func_7);
    sys_0(0x4, func_12);
    set_main(func_1);
}

void kame_setup()
{
    global7 = 0x5;
    kame_phase = 0;
    kame_total = 0;
    sv_set_mem(0x1, 0, 0, kame_pre);
    sv_set_mem(0x1, 0, 0x1, kame_pre);
    sv_set_mem(0x1, 0, 0x2, kame_pre);
    sv_set_mem(0x1, 0, 0x3, kame_pre);
    sv_set_mem(0x1, 0, 0x4, kame_pre);
    sv_set_mem(0x1, 0x1, 0, kame_fly_main);
    sv_set_mem(0x1, 0x1, 0x1, kame_fly_main);
    sv_set_mem(0x1, 0x1, 0x2, kame_fly_main);
    sv_set_mem(0x1, 0x1, 0x3, kame_hold_main);
    sv_set_mem(0x1, 0x1, 0x4, kame_finish_main);
    // motion indices as they are (no custom-variant offset: func_40 not installed)
    global11 = func_19;
    global21 = 0;
}

void kame_status(int status)
{
    StatusModule(0x3, status, 0);
}

int kame_pre()
{
    StatusModule(0x5, 0x2, 0, 0x5, 0, 0, 0, 0, 0, 0);
    return 0;
}

// the speed every frame: x = speed along the facing, no vertical speed, no acceleration / limit
void kame_move(float speed)
{
    KineticModule(0x11, 0, speed * PostureModuleF(0), 0);
    KineticModule(0xf, 0, 0, 0);
    KineticModule(0x15, 0, -1.0f, -1.0f);
}

float kame_speed()
{
    if (kame_level == 0x1)
    {
        return KAME_SPEED_2;
    }
    else if (kame_level == 0x2)
    {
        return KAME_SPEED_3;
    }
    return KAME_SPEED_1;
}

int kame_seg_id()
{
    if (kame_level == 0x1)
    {
        return KAME_SEG_2;
    }
    else if (kame_level == 0x2)
    {
        return KAME_SEG_3;
    }
    return KAME_SEG_1;
}

int kame_dis_id()
{
    if (kame_level == 0x1)
    {
        return KAME_DIS_2;
    }
    else if (kame_level == 0x2)
    {
        return KAME_DIS_3;
    }
    return KAME_DIS_1;
}

int kame_hold_frames()
{
    if (kame_level == 0x1)
    {
        return KAME_HOLD_2;
    }
    else if (kame_level == 0x2)
    {
        return KAME_HOLD_3;
    }
    return KAME_HOLD_1;
}

// every effect of the beam ends (the body pieces, the head)
void kame_fx_off()
{
KAME_FX_OFF
}

// the body pieces (dropped at the head every KAME_SEG_EVERY frames of the flight) replaced by
// dissolving ones at the same places, behind the head where it stopped. The last argument 1 puts
// them in the bone's frame (Z along the beam); with 0, Z was screen depth (test 18: a diagonal line)
void kame_dissolve()
{
    int f;
    int id;
    float z;
    id = kame_dis_id();
    f = KAME_SEG_FIRST;
    while (f <= kame_flown)
    {
        z = -(float)(kame_flown - f) * kame_speed();
        EffectModule(0x2710, id, 0, 0, 0, z, 0, 0, 0, 1.0f, 0, 0, 0, 0, 0, 0, 0x1);
        f += KAME_SEG_EVERY;
    }
    kame_fx_off();
}

// counts every frame of the beam's life: KAME_MAX frames, then it's removed
int kame_expired()
{
    kame_total += 1;
    if (kame_total > KAME_MAX)
    {
        kame_fx_off();
        BattleObject(0x9);
        return 1;
    }
    return 0;
}

void kame_fly_main()
{
    if (global4 == 0)
    {
        kame_phase = 0;
        kame_total = 0;
    }
    if (kame_phase != 0)
    {
        // a fly status asked for again after the hit: back to the hold / finish
        kame_status(0x2 + kame_phase);
        return;
    }
    kame_level = global4;
    kame_frame = 0;
    if (kame_level == 0x1)
    {
        kame_life = KAME_LIFE_2;
    }
    else if (kame_level == 0x2)
    {
        kame_life = KAME_LIFE_3;
    }
    else
    {
        kame_life = KAME_LIFE_1;
    }
    func_24(kame_level, 0, 1.0f);
    kame_move(kame_speed());
    callFunc3(kame_fly_loop);
}

// its range reached or a wall: it ends where it is (no hitboxes, the motion frozen: no more pieces)
void kame_end()
{
    kame_flown = kame_frame;
    kame_phase = 0x3;
    kame_frame = 0;
    AttackModule(0x2719);
    MotionModule(0x4, 0);
    kame_move(0);
    kame_dissolve();
}

void kame_fly_loop()
{
    if (kame_expired())
    {
        return;
    }
    if (kame_phase == 0x3)
    {
        kame_move(0);
        kame_frame += 1;
        if (kame_frame >= KAME_DISSOLVE)
        {
            BattleObject(0x9);
        }
        return;
    }
    if (kame_frame >= kame_life || kame_frame > 0x1 && GroundModule(0x2722))
    {
        kame_end();
        return;
    }
    if (kame_frame >= KAME_SEG_FIRST && kame_frame % KAME_SEG_EVERY == 0)
    {
        EffectModule(0x2710, kame_seg_id(), 0, 0, 0, 0, 0, 0, 0, 1.0f, 0, 0, 0, 0, 0, 0, 0x1);
    }
    kame_move(kame_speed());
    kame_frame += 1;
}

void kame_hold_main()
{
    if (kame_phase == 0)
    {
        kame_phase = 0x1;
        kame_flown = kame_frame;
        kame_frame = 0;
        func_24(kame_level, 0, 1.0f);
    }
    kame_move(0);
    callFunc3(kame_hold_loop);
}

void kame_hold_loop()
{
    if (kame_expired())
    {
        return;
    }
    kame_move(0);
    kame_frame += 1;
    if (kame_frame >= kame_hold_frames() + 0xa)
    {
        // the finish didn't start
        kame_fx_off();
        BattleObject(0x9);
        return;
    }
    if (kame_frame >= kame_hold_frames())
    {
        kame_status(0x4);
        return;
    }
}

void kame_finish_main()
{
    if (kame_phase != 0x2)
    {
        kame_phase = 0x2;
        kame_frame = 0;
        func_24(0x3, 0, 1.0f);
        MotionModule(0x4, 1.0f);
        kame_dissolve();
    }
    kame_move(0);
    callFunc3(kame_finish_loop);
}

void kame_finish_loop()
{
    if (kame_expired())
    {
        return;
    }
    kame_move(0);
    kame_frame += 1;
    if (kame_frame >= KAME_FINISH)
    {
        BattleObject(0x9);
        return;
    }
}
