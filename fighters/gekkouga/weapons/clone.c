// Greninja's clone (weapon kind 0x1A1, his articles 6 / 7: fighters/gekkouga/README.md "Clones v1" - "Clones v3").
// The framework is his moon article's (vanilla moon.mscsb, decompiled): one status that does nothing. The clone itself
// is cl_frame(), run every frame (global14): it finds him (the player slot whose SLOTn_SHARED_7 is 4747000 + flags,
// nearest to where it was made) and which clone it is (his "being made" bit 4 / 8), stands where his MSC puts it (v2:
// his VAR_24 / 25 or VAR_26 / 27: it falls and lands on its own there), faces his way and plays the motion he gives
// (VAR_28 kind x 1024 + frame (v3), VAR_29 rate: his own, Wait1 / Fall while he is on a ledge, hit, ...; Fall while it
// falls on its own, flags 16 / 32); v3: its VAR_1 = which clone, its bit in his VAR_30 every frame (the heartbeat); its scripts are his body's hitboxes (script/animcmd/weapon/clone, tools/gekkouga_build.py).
// Its VAR_0 = his slot (v2: the executable's clone hit method gives him its landed hits' hitlag). Hidden when he closes
// the channel (his VAR_31 0) or it is not alive any more; he removes it (ArticleModule 0x2712).
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
    global14 = cl_frame; // Greninja's clone: every frame, hitstop included (below)
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
// the clone
// ===================================================================
int cl_slot;           // his player slot (1 - 8), 0 not found yet
int cl_id;             // 1 the left-spawned clone (his article 6), 2 the right-spawned one (7)
int cl_motion;         // the motion playing (-1 none yet)
float cl_last_f;       // his motion frame last frame
int cl_shown;          // v8: the visibility it last set + 1 (0: never set, so the next cl_show sets it). v1 - v7
                       // kept 1 / 0 and reset it to 1 ("shown") whenever it looked for him again: a clone that
                       // waited a frame for its id (hidden) was then never shown again: the invisible clones
int cl_t;              // frames alive
float cl_hk0;          // clone delay: his channel's motion (VAR_28: kind x 1024 + frame) now, 1 and 2 of his unfrozen
float cl_hk1;          // frames back ...
float cl_hk2;
float cl_hr0;          // ... its rate (VAR_29) ...
float cl_hr1;
float cl_hr2;
float cl_hl0;          // ... his facing ...
float cl_hl1;
float cl_hl2;
int cl_hn;             // ... and how many are kept (0 - 3)

int cl_magic() { return 4747; }

// SLOTn_SHARED_k: VAR_(24 + k) of the fighter in player slot n
float cl_shared(int slot, int k)
{
    return WorkModuleF(0, 0x0f000340 + 8 * (slot - 1) + k);
}

// slot n's X / Y / facing (the position variables)
float cl_slot_pos(int slot, int n)
{
    return WorkModuleF(0, 0x0f000020 + 4 * (slot - 1) + n);
}

float cl_abs(float v)
{
    if (v < 0)
    {
        return -v;
    }
    return v;
}

// v2: his flags (VAR_31 - 4747000), 0x1000 when slot n isn't a Greninja with clones out (clone delay: up to 127: 64 he
// is frozen)
int cl_flags(int slot)
{
    float v;
    v = cl_shared(slot, 7) - 4747000.0f;
    if (v < -0.5f || v > 127.5f)
    {
        return 0x1000;
    }
    return (int)(v + 0.5f);
}

// him: a slot whose VAR_31 is the magic (4747000 + flags), the nearest to here (he made it at his place)
int cl_find()
{
    int s;
    int best;
    float d;
    float bd;
    best = 0;
    bd = 1000000.0f;
    s = 1;
    while (s <= 8)
    {
        if (cl_flags(s) < 0x1000)
        {
            d = cl_abs(cl_slot_pos(s, 0) - PostureModuleF(0x1)) + cl_abs(cl_slot_pos(s, 1) - PostureModuleF(0x2));
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

void cl_show(int on)
{
    if (on + 1 != cl_shown)
    {
        VisibilityModule(0x2710, on);
        cl_shown = on + 1;
    }
}

// which clone this is: his "being made" bit (4 the left one, 8 the right one); none in the first frames: wait
int cl_which(int flags)
{
    if (flags & 0x4)
    {
        return 0x1;
    }
    if (flags & 0x8)
    {
        return 0x2;
    }
    return 0;
}

// every frame (hitstop included): its place (his MSC's: it stands / falls / lands there), his facing, his motion
// (Fall while it falls on its own), its owner's slot in its VAR_0 (the executable gives him its hits' hitlag)
// v3: its heartbeat: its bit (1 / 2) in his VAR_30 (SLOTn_SHARED_6) every frame; he clears it every frame, and a
// clone whose bit stays off is one the game removed (past the blast zone)
void cl_beat()
{
    int beat;
    beat = (int)(cl_shared(cl_slot, 6) + 0.5f);
    if ((beat & cl_id) == 0)
    {
        WorkModule(0, (float)(beat + cl_id) + 0, 0x0f000340 + 8 * (cl_slot - 1) + 6);
    }
}

void cl_frame()
{
    int flags;
    int k;
    float f;
    float r;
    float lr;
    cl_t += 1;
    if (cl_slot == 0 || cl_id == 0)
    {
        cl_motion = 0xffffffff;
        cl_hn = 0;
        cl_slot = cl_find();
        if (cl_slot == 0)
        {
            cl_show(0);
            return;
        }
        cl_id = cl_which(cl_flags(cl_slot));
        if (cl_id == 0)
        {
            cl_slot = 0;
            cl_show(0);
            return;
        }
    }
    WorkModule(0, (float)cl_slot + 0, 0x0f000300);
    WorkModule(0, (float)cl_id + 0, 0x0f000301);   // v3: which clone (the executable reports its hurtbox's hits with it)
    flags = cl_flags(cl_slot);
    if (flags >= 0x1000)
    {
        cl_show(0);                       // his ability ended: he removes it
        return;
    }
    if ((flags & cl_id) == 0)
    {
        cl_hn = 0;
        cl_show(0);
        return;
    }
    if (cl_id == 0x1)
    {
        PostureModule(0x3, cl_shared(cl_slot, 0), cl_shared(cl_slot, 1), 0);
    }
    else
    {
        PostureModule(0x3, cl_shared(cl_slot, 2), cl_shared(cl_slot, 3), 0);
    }
    cl_beat();
    if ((flags & 0x40) == 0 || cl_hn == 0)
    {
        cl_push(cl_shared(cl_slot, 4), cl_shared(cl_slot, 5), cl_slot_pos(cl_slot, 3));
    }
    k = cl_pick();                        // clone delay: his state cl_delay() frames back
    lr = cl_hist(k, cl_hl0, cl_hl1, cl_hl2);
    if (lr != 0 && PostureModuleF(0) != lr)
    {
        PostureModule(0, lr);
        PostureModule(0x2);
    }
    f = cl_hist(k, cl_hk0, cl_hk1, cl_hk2);
    r = cl_hist(k, cl_hr0, cl_hr1, cl_hr2);
    if (flags & 0x40)
    {
        r = 0;                            // he is frozen (hitlag): so is its playback, where it is
    }
    k = (int)(f / 1024.0f);               // v3: his VAR_28 = kind x 1024 + frame
    f = f - (float)(k * 1024);
    if (flags & (0x10 * cl_id))
    {
        k = 0x24;                         // falling on its own: Fall (its own loop)
        if (k != cl_motion)
        {
            cl_move_end(k);
            MotionModule(0x1, k, 0, 1.0f);
            cl_motion = k;
        }
        MotionModule(0x4, r);
        cl_last_f = 0;
        cl_show(1);
        return;
    }
    if (k != cl_motion || f + 0.5f < cl_last_f)
    {
        cl_move_end(k);
        MotionModule(0x1, k, f, r);       // his new motion (or his restart), from his frame: its script runs from it
        cl_motion = k;
    }
    else
    {
        MotionModule(0x4, r);
        if (cl_abs(f - MotionModuleF(0x1)) > 1.0f)
        {
            MotionModule(0x2713, f);      // back on his frame (after its own hitlag)
        }
    }
    cl_last_f = f;
    cl_show(1);
}

// ---- clone delay (fighters/gekkouga/README.md "Clone delay"; the user: "the left clone should have a 1 frame delay and
// the right clone should have a 2 frame delay"): it plays his motion, frame, rate and facing as his channel gave them
// cl_delay() of his frames before (its place: his MSC's, delayed there the same way); fewer while its history fills
// (at first: now, then held). His frozen frames (hitlag, flag 64) are no frames: nothing kept, its playback paused.
int cl_delay() { return cl_id; }          // 1 the left-spawned clone, 2 the right-spawned one

void cl_push(float kf, float r, float lr)
{
    cl_hk2 = cl_hk1;
    cl_hk1 = cl_hk0;
    cl_hk0 = kf;
    cl_hr2 = cl_hr1;
    cl_hr1 = cl_hr0;
    cl_hr0 = r;
    cl_hl2 = cl_hl1;
    cl_hl1 = cl_hl0;
    cl_hl0 = lr;
    if (cl_hn < 0x3)
    {
        cl_hn += 1;
    }
}

// the history entry to play: cl_delay() back, or the oldest kept while it fills
int cl_pick()
{
    int i;
    i = cl_delay();
    if (i > cl_hn - 1)
    {
        i = cl_hn - 1;
    }
    if (i < 0)
    {
        i = 0;
    }
    return i;
}

float cl_hist(int i, float v0, float v1, float v2)
{
    if (i == 0x1)
    {
        return v1;
    }
    if (i == 0x2)
    {
        return v2;
    }
    return v0;
}

// ---- clone fixes v1 (the user: "down air's effects stay on clones indefinitely", "smash attacks charging effects never
// clear for the clones"): a fighter's following effects end with its moves (his scripts' Terminates, his status ends);
// the clone's one status never ends and a script left early (his move cancelled, landed, chained) never reaches its
// Terminates. So on a new motion kind (not a restart of the same one) every following effect of the clone is ended
// with a fade (EffectModule int op 0x2D (0): vt +0xD4, docs/native-notes.md): its last move's sword / water / streaks.
// World effects (Graphic_Effect: one-shots at a place) play out as on him.
void cl_move_end(int k)
{
    if (cl_motion != 0xffffffff && k != cl_motion)
    {
        EffectModule(0x2d, 0);
    }
}
