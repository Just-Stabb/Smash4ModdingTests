// Greninja's Parabeetle (weapon kind 0x1A4, his article 10: fighters/gekkouga/README.md "Parabeetle v1"). The framework
// is his moon article's (vanilla moon.mscsb, decompiled, as weapons/skeleton.c): one status that does nothing; the
// beetle itself is pb_frame(), run every frame (global14). His up special's stance end asks for it (his VAR_12: the
// request code, clones.c gk_pb_req) and makes it (ArticleModule 0x2710, 10); the executable (tools/gekkouga_clone_cave.py
// pb_frame) gives it its owner (its VAR_0) and the code (its VAR_1: his facing x (1 his own, 2 / 3 his left / right
// clone's, + 4 when he was on the ground)), and makes its collision from parabeetle.lvd (one drop-through floor line on
// its top, the hydrant's route as the skeleton's), moved with it every frame (riders carried) while its VAR_5 is 1 and
// removed when it is 2. This script flies it: from just under his (or the clone's) feet, forward his way, a swoop down
// then a steady rise, pb_life() frames; then it flies off up and away (no collision) and is removed. Its model and
// motions are the user's Wii Parabeetle (tools/mdl0_to_nud.py, tools/chr0_to_omo.py): motion 0 wait (flying), 1 rise,
// 2 ridden (the press when landed on).
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
    global14 = pb_frame; // the Parabeetle: every frame, hitstop included (below)
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
// the Parabeetle
// ===================================================================
int pb_on;             // 1 once started (its owner known)
int pb_wait;           // frames waited for its owner (the executable's claim)
int pb_t;              // frames flying
int pb_phase;          // 1 flying (its collision on), 2 leaving (no collision)
int pb_slot;           // its owner's slot (1 - 8)
int pb_which;          // 1 his, 2 / 3 his left / right clone's
int pb_ground;         // 1: asked for on the ground (it starts higher: its swoop ends just over the floor)
int pb_kind;           // the motion kind playing (0 wait, 1 rise, 2 ridden)
int pb_kind_t;         // frames in it
int pb_rode;           // frames something has been on it (0: nothing)
int pb_free;           // frames nothing has been on it since something was
int pb_on_n;           // frames in a row something's feet have been on its line (on it from the 2nd: one falling or
                       // jumping through the line's band is in it for a frame at most)
float pb_x0;           // where it started (its origin: its collision line is pb_top() over it), its way
float pb_y0;
float pb_dir;
float pb_x;
float pb_y;
float pb_vx;           // leaving: its speed
float pb_vy;

int pb_life() { return 240; }             // 4 s flying (the user: "about 4 seconds"), then it flies off
int pb_leave_frames() { return 30; }      // ... for 0.5 s (no collision), then removed
float pb_speed() { return 0.75f; }        // forward, units a frame (Greninja walks 1.43 / runs 2.08): 180 units in 4 s
float pb_dip() { return 8.0f; }           // the swoop: down this far ...
int pb_dip_frames() { return 20; }        // ... over this many frames (half a cosine: its speed 0 at both ends)
float pb_rise_v() { return 0.4f; }        // then it rises: up to this many units a frame ...
int pb_rise_ease() { return 30; }         // ... reached in this many frames (an even push), then steady: up 74 by 240
float pb_top() { return 10.6f; }          // its collision line over its origin (tools/gekkouga_clone_cave.py PB_TOP: the
                                          // shell's top, 10.84 at the model's scale 1.25 in every motion, its root's bob
                                          // taken out: pb_bob)
float pb_half() { return 10.0f; }         // ... from x - this to x + this (20 wide: 1.7 x his 12)
float pb_gap() { return 0.3f; }           // in the air its top starts this far under his feet
float pb_lift() { return 11.5f; }         // on the ground: its line this far over his feet: its lowest (the swoop's bottom,
                                          // frame 20, the wait motion's bob then 2.5 under its first frame's) 1 over the floor
float pb_leave_vx() { return 1.6f; }      // leaving: forward ...
float pb_leave_vy() { return 0.6f; }      // ... and up, rising faster each frame
float pb_leave_ay() { return 0.12f; }
float pb_ride_below() { return 1.0f; }    // something's feet within this under its line ...
float pb_ride_above() { return 1.5f; }    // ... or this over it ...
float pb_ride_side() { return 1.5f; }     // ... and its X within the line's ends +- this: on it
int pb_ridden_frames() { return 7; }      // the ridden motion (the user's ridden.chr0, 7 frames: the press)
int pb_wait_max() { return 30; }          // never claimed (nobody asked): removed
int pb_fx_puff() { return 0x1000021; }    // its arrival: the common smoke puff (an item's), small
float pb_fx_puff_size() { return 0.8f; }

float pb_var(int n)
{
    return WorkModuleF(0, 0x0f000300 + n);
}

void pb_set(int n, float v)
{
    WorkModule(0, v + 0, 0x0f000300 + n);
}

// his shared variables (SLOTn_SHARED_k: his VAR_24 - 31): 0 / 1 his left clone's X / Y, 2 / 3 his right clone's, 6 the
// heartbeats, 7 = 4747000 + the clones' flags (1 / 2 alive)
float pb_shared(int k)
{
    return WorkModuleF(0, 0x0f000340 + 8 * (pb_slot - 1) + k);
}

// a player slot's fighter: its X / Y (n 0 / 1), its kind (-1: none), its status kind (position variables)
float pb_slot_pos(int s, int n)
{
    return WorkModuleF(0, 0x0f000020 + 4 * (s - 1) + n);
}

int pb_slot_kind(int s)
{
    return (int)WorkModuleF(0, 0x0f0000a0 + 8 * (s + 2) + 5);
}

int pb_slot_status(int s)
{
    return (int)WorkModuleF(0, 0x0f0000a0 + 8 * (s + 2) + 2);
}

// its height over its start at frame t: the swoop (down pb_dip() in pb_dip_frames(), half a cosine), then the rise
// (speed from 0 to pb_rise_v() over pb_rise_ease() frames, then steady)
float pb_curve(int t)
{
    float u;
    float d;
    d = pb_dip();
    if (t <= pb_dip_frames())
    {
        return -d * (1.0f - MathF(0x4, M_PI * (float)t / (float)pb_dip_frames())) / 2.0f;
    }
    u = (float)(t - pb_dip_frames());
    if (u <= (float)pb_rise_ease())
    {
        return -d + pb_rise_v() * u * u / (2.0f * (float)pb_rise_ease());
    }
    return -d + pb_rise_v() * (float)pb_rise_ease() / 2.0f + pb_rise_v() * (u - (float)pb_rise_ease());
}

// its root's bob (the source's skl_root Y, x 1.25, taken out of its motions: tools/gekkouga_build.py PB_ROOT): the whole
// article bobs by it, so its collision line (pb_top() over its place) stays on its shell. Fitted to the motions' values
// (tools/gekkouga_clones_test.py checks every frame within 0.1): wait 3 harmonics of its 80 frames, rise 1 of 40, ridden
// its 7 frames' values
float pb_bob()
{
    float t;
    float w;
    int i;
    float a;
    float b;
    t = MotionModuleF(0x1);
    if (pb_kind == 0x2)
    {
        i = (int)t;
        if (i >= 6)
        {
            return 0;
        }
        a = pb_ridden_y(i);
        b = pb_ridden_y(i + 1);
        return a + (b - a) * (t - (float)i);
    }
    if (pb_kind == 0x1)
    {
        w = 2.0f * M_PI * t / 40.0f;
        return -0.0045f + 0.7418f * MathF(0x4, w) - 1.0257f * MathF(0x5, w);
    }
    w = 2.0f * M_PI * t / 80.0f;
    return 0.007f + 0.7598f * MathF(0x4, w) - 1.8181f * MathF(0x5, w) - 0.0388f * MathF(0x4, 2.0f * w) +
        0.0352f * MathF(0x5, 2.0f * w) + 0.1015f * MathF(0x4, 3.0f * w) - 0.048f * MathF(0x5, 3.0f * w);
}

float pb_ridden_y(int i)
{
    if (i == 0x1)
    {
        return -1.06f;
    }
    if (i == 0x2)
    {
        return -1.875f;
    }
    if (i == 0x3)
    {
        return -1.582f;
    }
    if (i == 0x4)
    {
        return -0.938f;
    }
    if (i == 0x5)
    {
        return -0.293f;
    }
    return 0;
}

void pb_motion(int k)
{
    if (k != pb_kind)
    {
        pb_kind = k;
        pb_kind_t = 0;
        MotionModule(0x1, k, 0, 1.0f);
    }
}

// its start: the code the executable copied from his request (its VAR_1), the place from his (the slot's position) or
// his clone's (his shared variables). Its place (pb_x, pb_y) is its path's; the article is at pb_y + pb_bob() (its
// root's bob, its line with it)
void pb_start()
{
    int c;
    float code;
    float x;
    float y;
    pb_slot = (int)(pb_var(0) + 0.5f);
    code = pb_var(1);
    pb_dir = 1.0f;
    if (code < 0)
    {
        pb_dir = -1.0f;
        code = -code;
    }
    c = (int)(code + 0.5f);
    pb_ground = 0;
    if (c >= 4)
    {
        pb_ground = 0x1;
        c -= 4;
    }
    pb_which = c;
    if (c == 0x2)
    {
        x = pb_shared(0);
        y = pb_shared(0x1);
    }
    else if (c == 0x3)
    {
        x = pb_shared(0x2);
        y = pb_shared(0x3);
    }
    else
    {
        pb_which = 0x1;
        x = pb_slot_pos(pb_slot, 0);
        y = pb_slot_pos(pb_slot, 0x1);
    }
    pb_kind = -1;
    pb_motion(0);
    pb_x0 = x;
    pb_y0 = y - pb_top() - pb_gap() - pb_bob();   // its line (its place + its bob + pb_top()) just under his feet
    if (pb_ground)
    {
        pb_y0 = y - pb_top() + pb_lift() - pb_bob();
    }
    pb_x = pb_x0;
    pb_y = pb_y0;
    PostureModule(0, pb_dir);
    PostureModule(0x2);
    PostureModule(0x3, pb_x, pb_y + pb_bob(), 0);
    VisibilityModule(0x2710, 0x1);
    pb_on = 0x1;
    pb_t = 0;
    pb_phase = 0x1;
    pb_set(5, 1.0f);                      // the executable: its collision made, moved with it
    pb_rode = 0;
    pb_free = 0;
    EffectModule(0x3, pb_fx_puff(), pb_x, pb_y + pb_top() * 0.5f, 0, 0, 0, 0, pb_fx_puff_size(), 0, 0xffffffff);
}

// on its line: a fighter's feet (any slot: the position variables), or a clone of its owner's (his shared places, while
// alive); 1 + 2 when its owner is one of them
int pb_riders()
{
    int s;
    int n;
    float top;
    float x;
    float y;
    int flags;
    n = 0;
    top = pb_y + pb_bob() + pb_top();
    s = 0x1;
    while (s <= 0x8)
    {
        if (pb_slot_kind(s) > 0 && pb_slot_status(s) != 0xb1 && pb_slot_status(s) != 0xb2)
        {
            x = pb_slot_pos(s, 0);
            y = pb_slot_pos(s, 0x1);
            if (pb_on_line(x, y, top))
            {
                n = n | 0x1;
                if (s == pb_slot)
                {
                    n = n | 0x2;
                }
            }
        }
        s += 1;
    }
    flags = (int)(pb_shared(7) + 0.5f) - 4747000;   // (his VAR_31: 4747000 + flags while his clones are out, else 0)
    if (flags >= 0)
    {
        if ((flags & 0x1) && pb_on_line(pb_shared(0), pb_shared(0x1), top))
        {
            n = n | 0x1;
        }
        if ((flags & 0x2) && pb_on_line(pb_shared(0x2), pb_shared(0x3), top))
        {
            n = n | 0x1;
        }
    }
    return n;
}

int pb_on_line(float x, float y, float top)
{
    if (y < top - pb_ride_below() || y > top + pb_ride_above())
    {
        return 0;
    }
    if (x < pb_x - pb_half() - pb_ride_side() || x > pb_x + pb_half() + pb_ride_side())
    {
        return 0;
    }
    return 0x1;
}

// its owner on it: bit 8 in his VAR_30 (SLOTn_SHARED_6, the clones' heartbeat word: 1 / 2 the clones', 4 the skeleton's,
// 64 / 128 the shurikens'): his clones copy his vertical movement while he rides (clones.c gk_pb_heartbeat)
void pb_beat()
{
    int beat;
    beat = (int)(pb_shared(6) + 0.5f);
    if ((beat & 0x8) == 0)
    {
        WorkModule(0, (float)(beat + 0x8) + 0, 0x0f000340 + 8 * (pb_slot - 1) + 6);
    }
}

// its motion: nothing on it: wait (flying) through the swoop, rise while it rises; something lands on it: ridden (the
// press, once), then rise while it carries (the source game's own: a Parabeetle rises with its rider)
void pb_anim(int ride)
{
    if (ride)
    {
        if (pb_rode == 0)
        {
            pb_kind = -1;
            pb_motion(0x2);               // just landed on: the press (from its first frame)
        }
        pb_rode += 1;
        pb_free = 0;
        if (pb_kind == 0x2 && pb_kind_t < pb_ridden_frames())
        {
            return;
        }
        pb_motion(0x1);
        return;
    }
    if (pb_rode > 0)
    {
        pb_free += 1;
        if (pb_free < 0x3)
        {
            return;                       // (a frame or two off the line: still ridden)
        }
        pb_rode = 0;
    }
    if (pb_kind == 0x2 && pb_kind_t < pb_ridden_frames())
    {
        return;
    }
    if (pb_t > pb_dip_frames())
    {
        pb_motion(0x1);
    }
    else
    {
        pb_motion(0);
    }
}

void pb_leave()
{
    pb_phase = 0x2;
    pb_t = 0;
    pb_set(5, 2.0f);                      // the executable: its collision removed (anyone on it falls)
    pb_vx = pb_leave_vx() * pb_dir;
    pb_vy = pb_leave_vy();
    pb_motion(0x1);
}

void pb_frame()
{
    int ride;
    int st;
    if (pb_on == 0)
    {
        if (pb_var(0) < 0.5f)
        {
            VisibilityModule(0x2710, 0);
            pb_wait += 1;
            if (pb_wait > pb_wait_max())
            {
                BattleObject(0x9);
            }
            return;
        }
        pb_start();
    }
    st = pb_slot_status(pb_slot);
    if (st == 0xb1 || st == 0xb2)
    {
        pb_set(5, 2.0f);
        BattleObject(0x9);                // its owner KO'd (Dead / Rebirth): removed (his MSC removes his articles at a KO too)
        return;
    }
    pb_kind_t += 1;
    if (pb_phase == 0x2)
    {
        pb_t += 1;
        if (pb_t >= pb_leave_frames())
        {
            BattleObject(0x9);
            return;
        }
        pb_x = pb_x + pb_vx;
        pb_y = pb_y + pb_vy;
        pb_vy = pb_vy + pb_leave_ay();
        PostureModule(0x3, pb_x, pb_y + pb_bob(), 0);
        return;
    }
    if (StopModule(0x1))
    {
        return;
    }
    pb_t += 1;
    if (pb_t >= pb_life())
    {
        pb_leave();
        return;
    }
    pb_x = pb_x0 + pb_speed() * pb_dir * (float)pb_t;
    pb_y = pb_y0 + pb_curve(pb_t);
    ride = pb_riders();
    if (ride & 0x1)
    {
        pb_on_n += 1;
    }
    else
    {
        pb_on_n = 0;
    }
    if (pb_on_n < 0x2)
    {
        ride = 0;
    }
    pb_set(8, (float)ride + 0);           // diag: 1 something on it, 3 its owner too
    if (ride & 0x2)
    {
        pb_beat();
    }
    pb_anim(ride & 0x1);
    PostureModule(0x3, pb_x, pb_y + pb_bob(), 0);
}
