// Greninja's water shuriken (weapon 0xF9, his article 0): vanilla shuriken.mscsb decompiled (tools/mscdec: recompiles to
// the same functions, msc_fingerprint 0 differ) + clone articles v1 (fighters/gekkouga/README.md "Clone articles v1", the
// end of this file: a clone's copy moves by that clone's offset).
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
    global14 = sh_frame; // Greninja mod: clone articles v1 (below)
}

void func_43()
{
    global7 = 0x6;
    func_44();
    func_45();
    func_46();
    func_42();
}

void func_44()
{
    sv_set_mem(0x1, 0, 0, func_47);
    sv_set_mem(0x1, 0x1, 0, func_48);
    sv_set_mem(0x1, 0x2, 0, func_50);
    sv_set_mem(0x1, 0, 0x1, func_51);
    sv_set_mem(0x1, 0x1, 0x1, func_52);
    sv_set_mem(0x1, 0x2, 0x1, func_54);
    sv_set_mem(0x1, 0, 0x2, func_55);
    sv_set_mem(0x1, 0x1, 0x2, func_56);
    sv_set_mem(0x1, 0x2, 0x2, func_59);
    sv_set_mem(0x1, 0, 0x3, func_60);
    sv_set_mem(0x1, 0x1, 0x3, func_61);
    sv_set_mem(0x1, 0x2, 0x3, func_63);
    sv_set_mem(0x1, 0, 0x4, func_64);
    sv_set_mem(0x1, 0x1, 0x4, func_65);
    sv_set_mem(0x1, 0x2, 0x4, func_68);
    sv_set_mem(0x1, 0, 0x5, func_69);
    sv_set_mem(0x1, 0x1, 0x5, func_70);
    sv_set_mem(0x1, 0x2, 0x5, func_72);
}

void func_45()
{
    sv_set_mem(0x1, 0x3, 0x2, func_73);
    sv_set_mem(0x1, 0x3, 0x4, func_73);
}

void func_46()
{
    sv_set_mem(0x1, 0x6, 0x2, func_75);
    sv_set_mem(0x1, 0x6, 0x4, func_75);
}

int func_47()
{
    StatusModule(0x5, 0x2, 0x2, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_48()
{
    printf("Shuriken status_Start");
    func_24(0, 0, 1.0f);
    callFunc3(func_49);
}

void func_49()
{
    
}

void func_50()
{
    
}

int func_51()
{
    StatusModule(0x5, 0x2, 0x2, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_52()
{
    printf("Shuriken status_Hold");
    func_24(0x4, 0, 1.0f);
    callFunc3(func_53);
}

void func_53()
{
    
}

void func_54()
{
    
}

int func_55()
{
    StatusModule(0x5, 0x2, 0, 0x5, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_56()
{
    printf("Shuriken status_Shot");
    WorkModule(0x2711, 0x20000005);
    func_24(0x8, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_58();
    }
    global16 = func_58;
    callFunc3(func_57);
}

void func_57()
{
    float var0;
    var0 = PostureModuleF(0);
    PostureModule(0x4, 25.0f * var0, -90.0f, 0);
    if (GroundModule(0x2722))
    {
        printf("status_Shot_Main GROUND_TOUCH");
        BattleObject(0x9);
        return;
    }
}

void func_58()
{
    printf("status_shot_uniq %d", WorkModule(0x6, 0x10000004));
    WorkModule(0xa, 0x10000004);
    if (WorkModule(0x6, 0x10000004) <= 0)
    {
        printf("Shuriken status_Shot_Main RemoveWeapon");
        BattleObject(0x9);
        return;
    }
}

void func_59()
{
    EffectModule(0x2d, 0x5);
}

int func_60()
{
    printf("Shuriken status_pre_MaxStart");
    StatusModule(0x5, 0x2, 0x2, 0x5, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_61()
{
    printf("Shuriken status_MaxStart");
    func_24(0xc, 0, 1.0f);
    callFunc3(func_62);
}

void func_62()
{
    
}

void func_63()
{
    
}

int func_64()
{
    StatusModule(0x5, 0x2, 0, 0x5, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_65()
{
    printf("Shuriken status_MaxShot");
    WorkModule(0x2711, 0x20000005);
    func_24(0x10, 0, 1.0f);
    if (!StopModule(0x1))
    {
        func_67();
    }
    global16 = func_67;
    callFunc3(func_66);
}

void func_66()
{
    float var0;
    var0 = PostureModuleF(0);
    PostureModule(0x4, 25.0f * var0, -90.0f, 0);
    if (GroundModule(0x2722))
    {
        func_18(0x5);
        return;
    }
}

void func_67()
{
    printf("status_maxshot_uniq %d", WorkModule(0x6, 0x10000004));
    WorkModule(0xa, 0x10000004);
    if (WorkModule(0x6, 0x10000004) <= 0)
    {
        func_18(0x5);
        return;
    }
}

void func_68()
{
    
}

int func_69()
{
    StatusModule(0x5, 0x2, 0, 0x5, 0, 0, 0, 0, 0, 0);
    return 0;
}

void func_70()
{
    printf("Shuriken status_MaxShotVanish");
    callFunc3(func_71);
}

void func_71()
{
    float var0;
    float var1;
    float var2;
    float var3;
    var0 = PostureModuleF(0);
    PostureModule(0x4, 25.0f * var0, -90.0f, 0);
    EffectModule(0x2d, 0x5);
    var1 = PostureModuleF(0x1);
    var2 = PostureModuleF(0x2);
    var3 = PostureModuleF(0x3);
    EffectModule(0x3, 0x3300013, var1, var2, var3, 0, 0, 0, 1.399999976158142f, 0, 0xffffffff);
    BattleObject(0x9);
}

void func_72()
{
    
}

void func_73()
{
    
}

void func_74()
{
    
}

void func_75()
{
    
}



// ===================================================================
// clone articles v1: his clones' shuriken copies. His MSC (clones.c gk_sh_copies) generates and shoots one more shuriken per
// clone out, right after his own shot, and marks them waiting in his channel's flags (512 the left-spawned clone's, 1024 the
// right-spawned one's; kept 3 frames). A shuriken in its first frames with a copy waiting claims it (the first one not yet
// claimed this frame: claim bits 64 / 128 in his VAR_30, cleared by him every frame) and, once shot (status 2 Shot / 4
// MaxShot), moves by that clone's place minus his (his channel's VAR_24 / 25 or 26 / 27: the clone's live place, wherever
// it stands; his place: the position variables), then flies on as shot (his facing = the clone's: copies are made only in
// formation; his charge). His own shuriken was made long before (his hold): never a copy.
// Clone fix v3 (the user: "articles spawned from clones spawn from the main body, rather than spawning from the clone"):
// the copies were seen at his hand: the one move (v1) can be undone by the game placing the shot at his hand after it. Now
// for sh_fix_frames() frames after the move each frame checks where the game left it: nearer to the path from his hand
// (where it was set minus the offset) than to where it was set -> re-placed by the game: moved by the offset again.
// Diag: each set reports (once a frame: VAR_30 + 256 x the report, his MSC turns it into his VAR_23 for the S4GF line,
// clones.c gk_sh_report): the clone, first set / set again, and the copy's place minus the clone's (2s, -40 - 40).
// ===================================================================
int sh_t;              // frames alive
int sh_slot;           // its owner's slot (1 - 8), 0 none
int sh_clone;          // the clone it is a copy for (1 / 2), 0 none (his own)
int sh_moved;          // frames since its move (0 not moved yet)
float sh_dx;           // clone fix v3: the offset it was moved by (the clone's place minus his, at the shot)
float sh_dy;
float sh_lx;           // ... where it was last (set or seen)
float sh_ly;
int sh_rep;            // ... a report waiting (1 first set, 2 set again)
float sh_rx;           // ... its place minus the clone's, at that set
float sh_ry;

int sh_fix_frames() { return 8; }

float sh_shared(int slot, int k)
{
    return WorkModuleF(0, 0x0f000340 + 8 * (slot - 1) + k);
}

float sh_slot_pos(int slot, int n)
{
    return WorkModuleF(0, 0x0f000020 + 4 * (slot - 1) + n);
}

float sh_abs(float v)
{
    if (v < 0)
    {
        return -v;
    }
    return v;
}

// its owner: the nearest Greninja with clones out (his VAR_31 4747000 + flags)
int sh_find()
{
    int s;
    int best;
    float d;
    float bd;
    float v;
    best = 0;
    bd = 1000000.0f;
    s = 1;
    while (s <= 8)
    {
        v = sh_shared(s, 7) - 4747000.0f;
        if (v > -0.5f && v < 2047.5f)
        {
            d = sh_abs(sh_slot_pos(s, 0) - PostureModuleF(0x1)) + sh_abs(sh_slot_pos(s, 1) - PostureModuleF(0x2));
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

void sh_claim()
{
    int flags;
    int wait;
    int beat;
    int c;
    sh_slot = sh_find();
    if (sh_slot == 0)
    {
        return;
    }
    flags = (int)(sh_shared(sh_slot, 7) - 4747000.0f + 0.5f);
    wait = (flags / 512) % 4;
    beat = (int)(sh_shared(sh_slot, 6) + 0.5f);
    c = 0;
    if ((wait & 0x1) && (beat & 64) == 0)
    {
        c = 0x1;
    }
    else if ((wait & 0x2) && (beat & 128) == 0)
    {
        c = 0x2;
    }
    if (c == 0)
    {
        return;
    }
    sh_clone = c;
    WorkModule(0, (float)(beat + 64 * c) + 0, 0x0f000340 + 8 * (sh_slot - 1) + 6);
}

int sh_q(float v)
{
    int q;
    q = (int)(v / 2.0f + 20.5f);
    if (v < -41.0f)
    {
        q = 0;
    }
    if (q > 40)
    {
        q = 40;
    }
    return q;
}

// the report to his MSC (one a frame: none there yet), else tried again next frame
void sh_report()
{
    int beat;
    int r;
    beat = (int)(sh_shared(sh_slot, 6) + 0.5f);
    if (beat >= 256)
    {
        return;
    }
    r = sh_clone + 4 * (sh_rep - 1) + 8 * (sh_q(sh_rx) + 41 * sh_q(sh_ry));
    WorkModule(0, (float)(beat + 256 * r) + 0, 0x0f000340 + 8 * (sh_slot - 1) + 6);
    sh_rep = 0;
}

void sh_set(float x, float y, int kind)
{
    PostureModule(0x3, x, y, PostureModuleF(0x3));
    sh_lx = x;
    sh_ly = y;
    sh_rx = x - sh_shared(sh_slot, 2 * sh_clone - 2);
    sh_ry = y - sh_shared(sh_slot, 2 * sh_clone - 1);
    sh_rep = kind;
    sh_report();
}

void sh_frame()
{
    float x;
    float y;
    float e1;
    float e2;
    sh_t += 1;
    if (sh_t <= 3 && sh_clone == 0)
    {
        sh_claim();
    }
    if (sh_rep != 0)
    {
        sh_report();
    }
    if (sh_clone == 0 || (global4 != 0x2 && global4 != 0x4))
    {
        return;
    }
    x = PostureModuleF(0x1);
    y = PostureModuleF(0x2);
    if (sh_moved == 0)
    {
        sh_dx = sh_shared(sh_slot, 2 * sh_clone - 2) - sh_slot_pos(sh_slot, 0);
        sh_dy = sh_shared(sh_slot, 2 * sh_clone - 1) - sh_slot_pos(sh_slot, 1);
        sh_moved = 0x1;
        sh_set(x + sh_dx, y + sh_dy, 0x1);
        return;
    }
    if (sh_moved > sh_fix_frames())
    {
        return;
    }
    sh_moved += 1;
    e1 = sh_abs(x - sh_lx) + sh_abs(y - sh_ly);
    e2 = sh_abs(x - (sh_lx - sh_dx)) + sh_abs(y - (sh_ly - sh_dy));
    if (e2 < e1)
    {
        sh_set(x + sh_dx, y + sh_dy, 0x2);   // the game put it back on his path: onto the clone's again
        return;
    }
    sh_lx = x;
    sh_ly = y;
}
