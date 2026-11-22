// Greninja's Running Skeleton (weapon kind 0x1A2, his article 8: fighters/gekkouga/README.md "Skeleton v1"). The
// framework is his moon article's (vanilla moon.mscsb, decompiled, as weapons/clone.c): one status that does nothing;
// the skeleton itself is sk_frame(), run every frame (global14). His side special's release asks for it (his VAR_15 -
// VAR_18) and makes it (ArticleModule 0x2710, 8); the executable (tools/gekkouga_clone_cave.py sk_frame) gives it its
// owner and start (its VAR_0 - VAR_3), its collision (a wall each side and a floor on top, the hydrant's route), its
// damage taken (VAR_4: opponents' attacks, once each), the hits (VAR_7 - VAR_9) and its explosion's burn. This script
// runs it: from the start it runs straight on at sk_speed() (stopped by walls, off ledges it falls with his gravity),
// at 0 HP it goes in a puff of smoke (no hitbox), at sk_fuse() frames it explodes (motion 1: its game script's hitbox).
// Its phase in VAR_5 (1 running, 2 exploded, 3 smoked) for the executable. Its model (Pac-Man's hydrant's, a carrier for
// its joints and its collision file) is hidden: the skeleton is the effect sk_fx_body().
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
    global14 = sk_frame; // the Running Skeleton: every frame, hitstop included (below)
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
// the Running Skeleton
// ===================================================================
int sk_on;             // 1 once started (its owner known)
int sk_wait;           // frames waited for its owner (the executable's claim)
int sk_t;              // frames running
int sk_phase;          // 1 running, 2 exploded, 3 smoked
int sk_end_t;          // frames since it exploded / smoked
int sk_stand;          // 1 standing on a floor
int sk_hits;           // hits seen (its VAR_9)
float sk_x;            // its place, its way (1 right, -1 left), its vertical speed
float sk_y;
float sk_dir;
float sk_vy;
float sk_hit_x;        // sk_line()'s point
float sk_hit_y;

int sk_fuse() { return 180; }             // 3 s: the explosion (the user)
float sk_hp() { return 25.0f; }           // its HP (the user); the executable's SK_HP the same
float sk_speed() { return 0.7f; }         // slow: units a frame (Greninja walks 1.2 / runs 1.6+)
float sk_gravity() { return 0.18f; }      // off a ledge it falls as he does (his 0x03000018 / 0x03000019)
float sk_max_fall() { return 1.85f; }
float sk_snap() { return 3.0f; }          // standing: the floor under its next step this far up / down (slopes, steps)
float sk_wall_y() { return 5.0f; }        // the wall test's height
float sk_wall_ahead() { return 2.0f; }    // ... and how far past its step (inside its own walls: x +- 6)
float sk_mid() { return 14.0f; }          // its middle (28 tall): its explosion / smoke there
int sk_boom_frames() { return 40; }       // the explosion: removed after this (its hitbox: the game script's frames 1 - 4)
int sk_smoke_frames() { return 3; }       // the smoke: removed after this (no hitbox)
int sk_wait_max() { return 30; }          // never claimed (nobody asked): removed

// effects (skeleton v1; placeholders until its flipbooks: sk_fx_* return the ids)
int sk_fx_spark() { return 0x1000025; }   // a hit: the common glancing-blow spark
int sk_fx_boom() { return 0x1000017; }    // the explosion: the common bomb explosion
int sk_fx_smoke() { return 0x1000021; }   // 0 HP: the common smoke puff (an item's)
int sk_fx_body() { return 0; }            // the skeleton itself (0: none)
float sk_fx_boom_size() { return 2.2f; }
float sk_fx_smoke_size() { return 3.0f; }
float sk_fx_spark_size() { return 1.6f; }

float sk_var(int n)
{
    return WorkModuleF(0, 0x0f000300 + n);
}

void sk_set(int n, float v)
{
    WorkModule(0, v + 0, 0x0f000300 + n);
}

// the stage line test from its own GroundModule (Line_Test's MSC variables, world space, passable platforms too) from
// (x0, y0) to (x1, y1): the kind of the first line met (0 none, 1 floor, 2 wall, 3 ceiling), sk_hit_x / _y there
int sk_line(float x0, float y0, float x1, float y1)
{
    WorkModule(0, x0 + 0, 0x0f0003d0);
    WorkModule(0, y0 + 0, 0x0f0003d1);
    WorkModule(0, x1 + 0, 0x0f0003d2);
    WorkModule(0, y1 + 0, 0x0f0003d3);
    WorkModule(0, 1.0f + 0, 0x0f0003d4);
    if (WorkModuleF(0, 0x0f0003d4) < 0.5f)
    {
        return 0;
    }
    sk_hit_x = WorkModuleF(0, 0x0f0003d6);
    sk_hit_y = WorkModuleF(0, 0x0f0003d7);
    return (int)(WorkModuleF(0, 0x0f0003d8) + 0.5f);
}

// a world-place effect (op 3, as his Substitution smoke)
void sk_fx_at(int id, float x, float y, float size)
{
    if (id != 0)
    {
        EffectModule(0x3, id, x, y, 0, 0, 0, 0, size, 0, 0xffffffff);
    }
}

void sk_body_on()
{
    if (sk_fx_body() != 0)
    {
        EffectModule(0x2710, sk_fx_body(), 0, 0, 0, 0, 0, 0, 0, 1.0f, 0, 0, 0, 0, 0, 0, 0);
    }
}

void sk_body_off()
{
    if (sk_fx_body() != 0)
    {
        EffectModule(0x2723, sk_fx_body(), 0x1, 0x1);
    }
}

// its start: the place / way the executable copied from him (the shadow's place, his facing)
void sk_start()
{
    sk_x = sk_var(1);
    sk_y = sk_var(2);
    sk_dir = 1.0f;
    if (sk_var(3) < 0)
    {
        sk_dir = -1.0f;
    }
    sk_vy = 0;
    sk_stand = 0;
    if (sk_line(sk_x, sk_y + sk_snap(), sk_x, sk_y - sk_snap()) == 0x1)
    {
        sk_y = sk_hit_y;
        sk_stand = 0x1;
    }
    PostureModule(0, sk_dir);
    PostureModule(0x2);
    PostureModule(0x3, sk_x, sk_y, 0);
    sk_on = 0x1;
    sk_t = 0;
    sk_hits = 0;
    sk_phase = 0x1;
    sk_set(5, 1.0f);
    MotionModule(0x1, 0, 0, 1.0f);        // run (motion 0)
    sk_body_on();
}

// a step: straight on (a wall stops it, it keeps running in place), standing it follows the floor, off a ledge it
// falls (his gravity) and lands on the first floor
void sk_move()
{
    float nx;
    float ny;
    nx = sk_x + sk_speed() * sk_dir;
    if (sk_line(sk_x, sk_y + sk_wall_y(), nx + sk_wall_ahead() * sk_dir, sk_y + sk_wall_y()) == 0x2)
    {
        nx = sk_x;
    }
    if (sk_stand)
    {
        if (sk_line(nx, sk_y + sk_snap(), nx, sk_y - sk_snap()) == 0x1)
        {
            sk_y = sk_hit_y;
            sk_x = nx;
            return;
        }
        sk_stand = 0;                     // off the ledge
        sk_vy = 0;
    }
    sk_vy = sk_vy - sk_gravity();
    if (sk_vy < -sk_max_fall())
    {
        sk_vy = -sk_max_fall();
    }
    ny = sk_y + sk_vy;
    if (sk_line(nx, sk_y + 0.5f, nx, ny - 0.5f) == 0x1)
    {
        ny = sk_hit_y;
        sk_stand = 0x1;
        sk_vy = 0;
    }
    sk_x = nx;
    sk_y = ny;
}

void sk_explode()
{
    sk_phase = 0x2;
    sk_end_t = 0;
    sk_set(5, 2.0f);                      // the executable: its collision removed, its explosion's hits burn
    sk_body_off();
    MotionModule(0x1, 0x1, 0, 1.0f);      // explode (motion 1): its game script's hitbox
    sk_fx_at(sk_fx_boom(), sk_x, sk_y + sk_mid(), sk_fx_boom_size());
}

void sk_smoke()
{
    sk_phase = 0x3;
    sk_end_t = 0;
    sk_set(5, 3.0f);
    sk_body_off();
    MotionModule(0x1, 0x2, 0, 1.0f);      // smoke (motion 2: no hitbox)
    sk_fx_at(sk_fx_smoke(), sk_x, sk_y + sk_mid(), sk_fx_smoke_size());
}

void sk_frame()
{
    int h;
    VisibilityModule(0x2710, 0);          // the carrier model never shows
    if (sk_on == 0)
    {
        if (sk_var(0) < 0.5f)
        {
            sk_wait += 1;
            if (sk_wait > sk_wait_max())
            {
                BattleObject(0x9);
            }
            return;
        }
        sk_start();
    }
    if (sk_phase != 0x1)
    {
        sk_end_t += 1;
        if (sk_phase == 0x2 && sk_end_t >= sk_boom_frames() || sk_phase == 0x3 && sk_end_t >= sk_smoke_frames())
        {
            BattleObject(0x9);
        }
        return;
    }
    sk_t += 1;
    h = (int)(sk_var(9) + 0.5f);
    if (h != sk_hits)
    {
        sk_hits = h;                      // a hit: the spark where it was hit
        sk_fx_at(sk_fx_spark(), sk_var(7), sk_var(8), sk_fx_spark_size());
    }
    if (sk_var(4) >= sk_hp())
    {
        sk_smoke();
        return;
    }
    if (sk_t >= sk_fuse())
    {
        sk_explode();
        return;
    }
    if (!StopModule(0x1))
    {
        sk_move();
    }
    PostureModule(0x3, sk_x, sk_y, 0);
}
