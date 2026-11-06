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

// ---- Sephiroth's Shadow Flare: flare1 (weapon kind 0x18D, a copy of Zelda's dein; his article 6). The scaffolding
// above is dein's MSC; its statuses are replaced (fighters/edge/specials.md "Side special"). From Ultimate's
// edge_flare1 / edge_flaredummy / edge_flare2 status code (lua2cpp_edge 7203e25d10.., 2e300.., 272e0..), vl.prc
// param_flare1 / param_flaredummy / param_flare2 and the ExeFS's native parts (main.bin 0x9e1770 generation,
// 0x33eccf0 / 0x33ecf80 flare1, 0x33f00e8 / 0x33f06xx dummy, 0x33ee1c8 flare2).
// Ultimate: the shot (flare1) hitting a fighter makes a flaredummy on that fighter (one per target), which keeps
// ceil(n) orbs (flare2, each its own object) circling the fighter, then sends them in one after another. Smash 4
// has no MSC way for a weapon to make other weapons or reach another one, so this one object does all three:
// status 0 FLY (flare1), 1 HIT (the hit: find the fighter hit), 2 ORBIT / 3 CONVE (the dummy and its orbs).
// The orbs are effects moved by handle (EffectModule 0x3 / 0x17) and hitboxes 0-4 of this object, placed each
// frame (AttackModule(0x1, id, x, y, z)). Ultimate's orbs are objects of their own (a hit record each); a dein copy
// has 2 Parts (hit records; dein's set-up 0x032107B4, Part 2+ crashed on the hit, bisect 70), so orb i is Part
// i % 2 and an orb that starts, strikes or explodes clears its Part's record (fl_clear: the orbit script's
// Hit_Log_Clear), as Ultimate's new status does.
// Per target state (a second shot on the same fighter adds orbs and life, Ultimate's forwarded event) lives on
// the target: its SLOTn_SHARED_k variables (0x0F000340 + 8 x slot + k, tools/acmd_ext_cave.py): 0 the
// controller's life, 1 its heartbeat (changes every frame), 2 orbs to add, 3 frames to add.
// Per orb (this object's own VAR_0-19, 0x0F000300 + k): state (0 none, 1 orbiting, 2 striking, 3 gone), its
// timer (the 5-frame appear, then the strike delay), its radius, its radial speed. Effect handles in globals.
int fl_status;
int fl_phase;          // 0 flying, 1 hit, 2 the controller (weapons are pooled: reset on status 0)
int fl_total;
int fl_life;
float fl_r;            // charge ratio: hold / hold_max 27 (main.bin 0x9e1770: flare1 work float 4)
float fl_n;            // orbs: max(1, loop_max 3 x r) (work float 3)
float fl_speed;
int fl_slot;           // the target's player slot (0 - 7)
int fl_owner;          // Sephiroth's slot (the fighter at the spawn's origin), never a target
int fl_tries;
int fl_count;          // orbs made (ceil(n))
int fl_pool;           // orbit_life_max 210: frames a later shot can add
int fl_beat;
float fl_rot;          // the orbit's phase (the dummy's rot_x, degrees)
float fl_spin;         // its speed
float fl_cx;
float fl_cy;
float fl_cz;
float fl_rad;          // the target's orbit radius and ring centre (fl_target_shape)
int fl_joint;
float fl_oup;
float fl_ofwd;
float fl_up;
float fl_fwd;
int fl_clr0;           // hit records to clear (Part 0 / 1) when the orbit script runs next (fl_hitboxes)
int fl_clr1;
int fl_beam;          // the beam's effect handle while the shot flies (fl_fly_main lays it, the loop moves it)
float fl_y0;          // the shot's height (Ultimate's spawn), held while it flies (test 81: on the ground it sat on the floor)
int fl_fx0;
int fl_fx1;
int fl_fx2;
int fl_fx3;
int fl_fx4;

int fl_fx_beam() { return 0; } // fx edge_shadowflare_beam
int fl_fx_beam_hit() { return 0; } // fx edge_shadowflare_beam_hit
int fl_fx_bullet() { return 0; } // fx edge_shadowflare_bullet
int fl_fx_attack() { return 0; } // fx edge_shadowflare_bullet_attack
int fl_fx_exp() { return 0; } // fx edge_shadowflare_bullet_hit
int fl_fx_end() { return 0; } // fx edge_shadowflare_bullet_end

// dein's own (func_49 / func_55)
int fl_pre()
{
    StatusModule(0x5, 0x2, 0, 0x5, 0, 0, 0xffffffff, 0xffffffff, 0xffffffff, 0);
    return 0;
}

void fl_to(int status)
{
    StatusModule(0x3, status, 0);
}

void fl_move(float vx, float vy)
{
    KineticModule(0x11, 0, vx, vy);
    KineticModule(0xf, 0, 0, 0);
    KineticModule(0x15, 0, -1.0f, -1.0f);
}

// a safety net: removed 720 frames after it was made whatever happened (240 + 210 orbit, the strikes)
int fl_expired()
{
    fl_total += 1;
    if (fl_total > 0x2d0)
    {
        BattleObject(0x9);
        return 1;
    }
    return 0;
}

float fl_var(int k)
{
    return WorkModuleF(0, 0x0f000300 + k);
}

void fl_set(int k, float v)
{
    WorkModule(0, v, 0x0f000300 + k);
}

float fl_shared(int k)
{
    return WorkModuleF(0, 0x0f000340 + 0x8 * fl_slot + k);
}

void fl_share(int k, float v)
{
    WorkModule(0, v, 0x0f000340 + 0x8 * fl_slot + k);
}

int fl_fx(int i)
{
    if (i == 0) { return fl_fx0; }
    if (i == 0x1) { return fl_fx1; }
    if (i == 0x2) { return fl_fx2; }
    if (i == 0x3) { return fl_fx3; }
    return fl_fx4;
}

void fl_fx_set(int i, int h)
{
    if (i == 0) { fl_fx0 = h; }
    if (i == 0x1) { fl_fx1 = h; }
    if (i == 0x2) { fl_fx2 = h; }
    if (i == 0x3) { fl_fx3 = h; }
    if (i == 0x4) { fl_fx4 = h; }
}

// an orb's effect: the old one off (0x6 by handle), the new one at (x, y) (0x3: a world place, no turn)
void fl_fx_play(int i, int id, float x, float y, float scale)
{
    if (fl_fx(i) != 0)
    {
        EffectModule(0x6, fl_fx(i));
        fl_fx_set(i, 0);
    }
    if (id != 0)
    {
        fl_fx_set(i, EffectModule(0x3, id, x, y, fl_cz, 0, 0, 0, scale, 0, 0xffffffff));
    }
}

// Sephiroth's slot: the nearest fighter of his kind (0x42, the kind variable 0x0F0000BD + 8 x slot) to where Din's
// callback spawned this; the shot is placed from his own position (test 73 on). (Tests 72 - 74's beam on the floor was
// the beam effect laid at the callback's point before the move: fl_fly_main lays it now, test 75)
int fl_owner_slot(int air, float lr)
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

// ---- 0 FLY (260a0 / 26000 / 26c00): straight along his facing at speed_x 5.5 x lerp(1, speed_mul 1.5, r) for
// life 7 frames, power x lerp(1, power_mul 3, r) (0x33eccf0); a wall / the floor ends it (Ultimate's End: the beam
// left to fade). Placed at Ultimate's spawn: his position + (lr x offset_x 10, offset_y 10) (air: offset_x_air 10,
// offset_y_air 7), from his own position (fl_owner_slot). Fly lasts
// its life only (Ultimate also ends it on touching a wall / the floor: left out. Test 65's GroundModule(0x2722)
// and test 66's "moved under half its speed" both ended it at once, inferred from the user: "the initial hit
// still doesn't show up")
void fl_fly_loop()
{
    if (fl_expired())
    {
        return;
    }
    fl_life -= 1;
    if (fl_life <= 0)
    {
        fl_to(0x4);
        return;
    }
    fl_move(fl_speed * PostureModuleF(0), 0);
    PostureModule(0x2714, PostureModuleF(0x1), fl_y0, PostureModuleF(0x3));
    if (fl_beam != 0)                          // Ultimate's beam follows the shot (EFFECT_FOLLOW on top) until Hit / End
    {                                          // leave it (EFFECT_DETACH_KIND)
        EffectModule(0x17, fl_beam, PostureModuleF(0x1), PostureModuleF(0x2), PostureModuleF(0x3));
    }
}

void fl_fly_main()
{
    int v;
    int air;
    float lr;
    if (global4 == 0)
    {
        fl_phase = 0;
        fl_total = 0;
    }
    if (fl_phase != 0)
    {
        fl_to(0x1);
        return;
    }
    v = WorkModule(0x6, 0x10000005);
    air = 0;
    if (v >= 0x20)
    {
        air = 0x1;
        v -= 0x20;
    }
    if (v < 0 || v > 0x1b)
    {
        v = 0;
    }
    fl_r = (float)v / 27.0f;
    fl_n = 3.0f * fl_r;
    if (fl_n < 1.0f)
    {
        fl_n = 1.0f;
    }
    fl_speed = 5.5f * (1.0f + 0.5f * fl_r);
    fl_life = 0x7;
    fl_fx0 = fl_fx1 = fl_fx2 = fl_fx3 = fl_fx4 = 0;
    lr = PostureModuleF(0);
    fl_owner = fl_owner_slot(air, lr);
    // fired on the ground, the shot is made a grounded object and sat on the floor whatever its spawn (user, test 80
    // clip: the beam along the floor on the ground, at his hand in the air; tests 65 / 66 found it touching the floor
    // at once): it flies in the air, its correction the air's, and its height is held every frame (fl_fly_loop)
    StatusModule(0x2, 0x2);
    GroundModule(0x2710, 0x5);
    if (fl_owner >= 0)                         // Ultimate's spawn (main.bin 0x9e1770): his position + (lr x
    {                                          // offset_x 10, offset_y 10), air (offset_x_air 10, offset_y_air 7)
        if (air)
        {
            PostureModule(0x2714, WorkModuleF(0, 0x0f000020 + 0x4 * fl_owner) + 10.0f * lr,
                          WorkModuleF(0, 0x0f000021 + 0x4 * fl_owner) + 7.0f, PostureModuleF(0x3));
        }
        else
        {
            PostureModule(0x2714, WorkModuleF(0, 0x0f000020 + 0x4 * fl_owner) + 10.0f * lr,
                          WorkModuleF(0, 0x0f000021 + 0x4 * fl_owner) + 10.0f, PostureModuleF(0x3));
        }
    }
    fl_y0 = PostureModuleF(0x2);
    if (fl_owner >= 0)
    {
        fl_y0 = WorkModuleF(0, 0x0f000021 + 0x4 * fl_owner) + 10.0f;
        if (air)
        {
            fl_y0 = WorkModuleF(0, 0x0f000021 + 0x4 * fl_owner) + 7.0f;
        }
    }
    // Fly's beam (edge_shadowflare_beam: Ultimate's EFFECT_FOLLOW on top at frame 0) played here, at the moved place,
    // along his facing (the effect's Z), and moved with the shot by the loop: played from Fly's script it took the top
    // joint's matrix from before the move, Din's creation point on the floor (tests 72 - 74); laid once and left
    // there (test 75) it stayed centred on the spawn, back through him (user: "offset into the wrong axis")
    fl_beam = EffectModule(0x3, fl_fx_beam(), PostureModuleF(0x1), fl_y0, PostureModuleF(0x3), 0,
                           1.5707964f * lr, 0, 1.0f, 0, 0xffffffff);
    func_24(0, 0, 1.0f);                       // fly
    AttackModule(0x2728, 1.0f + 2.0f * fl_r);
    fl_move(fl_speed * lr, 0);
    callFunc3(fl_fly_loop);
}

// ---- 4 END: the beam left (End's EFFECT_DETACH_KIND), removed the next frame (its notify at frame 1)
void fl_end_loop()
{
    BattleObject(0x9);
}

void fl_end_main()
{
    fl_phase = 0x1;
    fl_move(0, 0);
    AttackModule(0x2719);
    func_24(0x2, 0, 1.0f);                     // end
    callFunc3(fl_end_loop);
}

// ---- 1 HIT (the on_hit method: its attack connected): Hit's effects (the beam left, edge_shadowflare_beam_hit).
// The fighter hit: the nearest one to it (within 30) other than Sephiroth, one in hitstop counted 4 x nearer
// (positions and hitstop through the slot variables, docs/position-variables.md). One already circled by a live controller
// (its heartbeat moving) gets this shot's orbs and life (Ultimate's dummy: n = min(n + shot n, P 5), life +=
// min(int(orbit_life_ext_min 30 + 150 r), the pool)); otherwise this object becomes its controller
int fl_find()
{
    int s;
    int best;
    float x;
    float y;
    float dx;
    float dy;
    float d;
    float bd;
    x = PostureModuleF(0x1);
    y = PostureModuleF(0x2);
    best = 0xffffffff;
    bd = 900.0f;
    s = 0;
    while (s < 0x8)
    {
        if (s != fl_owner && WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0)
        {
            dx = WorkModuleF(0, 0x0f000020 + 0x4 * s) - x;
            dy = WorkModuleF(0, 0x0f000021 + 0x4 * s) + 9.0f - y;
            d = dx * dx + dy * dy;
            if (WorkModuleF(0, 0x0f00005b + 0x8 * s) > 0)
            {
                d = d * 0.25f;
            }
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

void fl_hit_loop()
{
    float hb;
    if (fl_expired())
    {
        return;
    }
    fl_move(0, 0);
    if (fl_slot < 0)
    {
        fl_slot = fl_find();
        if (fl_slot < 0)
        {
            fl_tries += 1;
            if (fl_tries > 0x3)
            {
                BattleObject(0x9);
            }
            return;
        }
        fl_beat = (int)fl_shared(0x1);
        return;
    }
    hb = fl_shared(0x1);
    if (fl_shared(0) > 0 && (int)hb != fl_beat)
    {
        fl_share(0x2, fl_shared(0x2) + fl_n);
        fl_share(0x3, fl_shared(0x3) + (float)(0x1e + (int)(150.0f * fl_r)));
        BattleObject(0x9);
        return;
    }
    fl_to(0x2);
}

void fl_hit_main()
{
    if (fl_phase == 0)
    {
        fl_phase = 0x1;
        fl_slot = 0xffffffff;
        fl_tries = 0;
        AttackModule(0x2719);
        func_24(0x1, 0, 1.0f);                 // hit
    }
    fl_move(0, 0);
    callFunc3(fl_hit_loop);
}

// ---- the controller: the target's centre (Ultimate: its fighter_param edge_flare_node, `waist` for 92 of 94
// fighters, + edge_flare_offset_x/y/z in that joint's axes) and orbit radius edge_flare_radius (x its scale, taken
// as 1), per fighter kind (the slot's kind, 0x0F0000A0 + 8 x target + 5). Smash 4's MSC can't read another
// fighter's joint, so the variable cave reads the target's own ModelModuleF(axis, bone) for it (test 72: the
// rest-pose centre of test 71 sat 19.5 over a hunched Donkey Kong and the ring dipped into him; test 71: one radius /
// height for everyone, 14 / 9, put the ring inside him, whose orbs then hit him while orbiting)
// ---- flare targets (generated: tools/edge_flare_targets.py) ----
// fl_rad: Ultimate's edge_flare_radius; fl_joint: its edge_flare_node's bone index in the Smash 4 model,
// fl_oup / fl_ofwd: its offsets up / forward (rest-pose axes, x its size); fl_up / fl_fwd: the rest-pose
// centre from its position, if the joint can't be read. Unknown kinds keep 14, no joint, 9 / 0.
void fl_target_shape(int k)
{
    fl_rad = 14.0f;
    fl_joint = -1;
    fl_oup = 0;
    fl_ofwd = 0;
    fl_up = 9.0f;
    fl_fwd = 0;
    if (k == 0x0) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = 1.00f; fl_ofwd = 0.50f; fl_up = 7.74f; fl_fwd = 0.50f; }   // miifighter (miifighter WaistN)
    if (k == 0x1) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = 1.00f; fl_ofwd = 0.50f; fl_up = 7.74f; fl_fwd = 0.50f; }   // miiswordsman (miiswordsman WaistN)
    if (k == 0x2) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = 1.00f; fl_ofwd = 0.50f; fl_up = 7.74f; fl_fwd = 0.50f; }   // miigunner (miigunner WaistN)
    if (k == 0x3) { fl_rad = 13.00f; fl_joint = 0xb; fl_oup = 1.00f; fl_ofwd = 0.00f; fl_up = 7.57f; fl_fwd = 0.03f; }   // mario (mario WaistN)
    if (k == 0x4) { fl_rad = 17.00f; fl_joint = 0xb; fl_oup = 3.97f; fl_ofwd = 3.04f; fl_up = 19.48f; fl_fwd = 3.34f; }   // donkey (donkey WaistN)
    if (k == 0x5) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -1.00f; fl_ofwd = 0.10f; fl_up = 10.35f; fl_fwd = 0.69f; }   // link (link WaistN)
    if (k == 0x6) { fl_rad = 15.00f; fl_joint = 0xb; fl_oup = -2.46f; fl_ofwd = -0.44f; fl_up = 12.27f; fl_fwd = -1.15f; }   // samus (samus WaistN)
    if (k == 0x7) { fl_rad = 14.50f; fl_joint = 0xb; fl_oup = 2.65f; fl_ofwd = 0.97f; fl_up = 9.21f; fl_fwd = 1.95f; }   // yoshi (yoshi WaistN)
    if (k == 0x8) { fl_rad = 12.00f; fl_joint = 0xb; fl_oup = 0.00f; fl_ofwd = 0.00f; fl_up = 4.42f; fl_fwd = 0.00f; }   // kirby (kirby WaistN)
    if (k == 0x9) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = 0.00f; fl_ofwd = 0.00f; fl_up = 9.09f; fl_fwd = 0.68f; }   // fox (fox WaistN)
    if (k == 0xa) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = 1.91f; fl_ofwd = 0.16f; fl_up = 5.38f; fl_fwd = -0.69f; }   // pikachu (pikachu WaistN)
    if (k == 0xb) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = 1.50f; fl_ofwd = 0.00f; fl_up = 8.97f; fl_fwd = 0.03f; }   // luigi (luigi WaistN)
    if (k == 0xc) { fl_rad = 14.50f; fl_joint = 0xb; fl_oup = -2.09f; fl_ofwd = 0.21f; fl_up = 11.82f; fl_fwd = -0.30f; }   // captain (captain WaistN)
    if (k == 0xd) { fl_rad = 12.50f; fl_joint = 0xb; fl_oup = 2.00f; fl_ofwd = 0.03f; fl_up = 7.00f; fl_fwd = 0.12f; }   // ness (ness WaistN)
    if (k == 0xe) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -1.00f; fl_ofwd = -1.00f; fl_up = 9.60f; fl_fwd = -0.50f; }   // peach (peach WaistN)
    if (k == 0xf) { fl_rad = 17.50f; fl_joint = 0xb; fl_oup = 1.62f; fl_ofwd = -0.26f; fl_up = 12.66f; fl_fwd = 0.67f; }   // koopa (koopa WaistN)
    if (k == 0x10) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -1.99f; fl_ofwd = -1.01f; fl_up = 9.62f; fl_fwd = -0.66f; }   // zelda (zelda WaistN)
    if (k == 0x11) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = -1.55f; fl_ofwd = 0.92f; fl_up = 10.30f; fl_fwd = 1.39f; }   // sheik (sheik WaistN)
    if (k == 0x12) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -1.93f; fl_ofwd = -0.94f; fl_up = 10.19f; fl_fwd = -0.70f; }   // marth (marth WaistN)
    if (k == 0x13) { fl_rad = 12.00f; fl_joint = 0xb; fl_oup = 1.00f; fl_ofwd = 0.50f; fl_up = 7.91f; fl_fwd = 0.50f; }   // gamewatch (gamewatch WaistN)
    if (k == 0x14) { fl_rad = 16.00f; fl_joint = 0xb; fl_oup = -1.92f; fl_ofwd = 0.00f; fl_up = 12.64f; fl_fwd = -0.58f; }   // ganon (ganon WaistN)
    if (k == 0x15) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = -1.04f; fl_ofwd = 0.15f; fl_up = 9.05f; fl_fwd = 0.92f; }   // falco (falco WaistN)
    if (k == 0x16) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = 1.48f; fl_ofwd = -0.27f; fl_up = 6.57f; fl_fwd = 0.14f; }   // wario (wario WaistN)
    if (k == 0x17) { fl_rad = 13.00f; fl_joint = 0xb; fl_oup = 0.00f; fl_ofwd = 0.00f; fl_up = 5.56f; fl_fwd = 0.00f; }   // metaknight (metaknight WaistN)
    if (k == 0x18) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -1.49f; fl_ofwd = 0.21f; fl_up = 10.16f; fl_fwd = 0.81f; }   // pit (pit WaistN)
    if (k == 0x19) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = -1.50f; fl_ofwd = 0.03f; fl_up = 10.53f; fl_fwd = 0.28f; }   // szerosuit (szerosuit WaistN)
    if (k == 0x1a) { fl_rad = 11.50f; fl_joint = 0xb; fl_oup = 1.90f; fl_ofwd = -0.00f; fl_up = 5.03f; fl_fwd = 0.23f; }   // pikmin (pikmin WaistN)
    if (k == 0x1b) { fl_rad = 13.00f; fl_joint = 0xb; fl_oup = 1.10f; fl_ofwd = 0.89f; fl_up = 8.75f; fl_fwd = 1.25f; }   // diddy (diddy WaistN)
    if (k == 0x1c) { fl_rad = 16.00f; fl_joint = 0xb; fl_oup = 2.36f; fl_ofwd = 0.98f; fl_up = 9.61f; fl_fwd = 1.41f; }   // dedede (dedede WaistN)
    if (k == 0x1d) { fl_rad = 14.50f; fl_joint = 0xb; fl_oup = -1.50f; fl_ofwd = 0.02f; fl_up = 11.75f; fl_fwd = 0.27f; }   // ike (ike WaistN)
    if (k == 0x1e) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = 0.00f; fl_ofwd = 0.00f; fl_up = 9.25f; fl_fwd = 0.06f; }   // lucario (lucario WaistN)
    if (k == 0x1f) { fl_rad = 15.00f; fl_joint = 0x2a; fl_oup = 1.00f; fl_ofwd = 0.50f; fl_up = 11.05f; fl_fwd = 0.50f; }   // robot (robot Waist3N)
    if (k == 0x20) { fl_rad = 12.50f; fl_joint = 0xb; fl_oup = 1.50f; fl_ofwd = 0.00f; fl_up = 7.47f; fl_fwd = 0.00f; }   // toonlink (toonlink WaistN)
    if (k == 0x21) { fl_rad = 16.00f; fl_joint = 0xb; fl_oup = 2.48f; fl_ofwd = 1.96f; fl_up = 9.85f; fl_fwd = 2.61f; }   // lizardon (plizardon WaistN)
    if (k == 0x22) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = 0.97f; fl_ofwd = -0.48f; fl_up = 9.18f; fl_fwd = -0.48f; }   // sonic (sonic WaistN)
    if (k == 0x23) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = 0.00f; fl_ofwd = 0.00f; fl_up = 5.00f; fl_fwd = 0.00f; }   // purin (purin WaistN)
    if (k == 0x24) { fl_rad = 13.00f; fl_joint = 0xb; fl_oup = 1.00f; fl_ofwd = 0.00f; fl_up = 7.57f; fl_fwd = 0.03f; }   // mariod (mariod WaistN)
    if (k == 0x25) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -1.85f; fl_ofwd = -0.90f; fl_up = 9.77f; fl_fwd = -0.67f; }   // lucina (lucina WaistN)
    if (k == 0x26) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -1.49f; fl_ofwd = 0.21f; fl_up = 10.16f; fl_fwd = 0.81f; }   // pitb (pitb WaistN)
    if (k == 0x27) { fl_rad = 15.00f; fl_joint = 0xb; fl_oup = -0.96f; fl_ofwd = -0.57f; fl_up = 10.93f; fl_fwd = -0.33f; }   // rosetta (rosetta WaistN)
    if (k == 0x28) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -1.44f; fl_ofwd = 0.00f; fl_up = 10.16f; fl_fwd = 0.00f; }   // wiifit (wiifit WaistN)
    if (k == 0x29) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = -1.02f; fl_ofwd = 0.67f; fl_up = 9.57f; fl_fwd = 0.79f; }   // littlemac (littlemac WaistN)
    if (k == 0x2a) { fl_rad = 13.00f; fl_joint = 0xb; fl_oup = 2.00f; fl_ofwd = 0.00f; fl_up = 6.98f; fl_fwd = 0.00f; }   // murabito (murabito WaistN)
    if (k == 0x2b) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -1.43f; fl_ofwd = -0.95f; fl_up = 10.59f; fl_fwd = -0.34f; }   // palutena (palutena WaistN)
    if (k == 0x2c) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -1.49f; fl_ofwd = 0.13f; fl_up = 10.11f; fl_fwd = 0.13f; }   // reflet (reflet WaistN)
    if (k == 0x2d) { fl_rad = 13.00f; fl_joint = 0xb; fl_oup = 3.00f; fl_ofwd = -1.00f; fl_up = 9.55f; fl_fwd = -1.71f; }   // duckhunt (duckhunt WaistN)
    if (k == 0x2e) { fl_rad = 14.50f; fl_joint = 0xb; fl_oup = -1.46f; fl_ofwd = -0.34f; fl_up = 9.68f; fl_fwd = 0.05f; }   // koopajr (koopajr WaistN)
    if (k == 0x2f) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -1.49f; fl_ofwd = 0.14f; fl_up = 10.38f; fl_fwd = 0.42f; }   // shulk (shulk WaistN)
    if (k == 0x30) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = 0.50f; fl_ofwd = 0.50f; fl_up = 10.94f; fl_fwd = 0.50f; }   // gekkouga (gekkouga WaistN)
    if (k == 0x31) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = -2.00f; fl_ofwd = 0.00f; fl_up = 7.40f; fl_fwd = 0.00f; }   // pacman (pacman WaistN)
    if (k == 0x32) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = 0.00f; fl_ofwd = 0.00f; fl_up = 7.69f; fl_fwd = 0.16f; }   // rockman (rockman WaistN)
    if (k == 0x33) { fl_rad = 15.00f; fl_joint = 0xb; fl_oup = -0.00f; fl_ofwd = -1.00f; fl_up = 11.31f; fl_fwd = -0.84f; }   // mewtwo (mewtwo WaistN)
    if (k == 0x34) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -2.50f; fl_ofwd = 0.00f; fl_up = 10.70f; fl_fwd = 0.00f; }   // ryu (ryu WaistN)
    if (k == 0x35) { fl_rad = 12.50f; fl_joint = 0xb; fl_oup = 1.99f; fl_ofwd = 0.53f; fl_up = 7.00f; fl_fwd = 0.62f; }   // lucas (lucas WaistN)
    if (k == 0x36) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -1.91f; fl_ofwd = -0.93f; fl_up = 10.08f; fl_fwd = -0.69f; }   // roy (roy WaistN)
    if (k == 0x37) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -1.50f; fl_ofwd = 0.01f; fl_up = 11.12f; fl_fwd = 0.28f; }   // cloud (cloud WaistN)
    if (k == 0x38) { fl_rad = 14.50f; fl_joint = 0xb; fl_oup = -2.73f; fl_ofwd = -1.24f; fl_up = 11.35f; fl_fwd = -1.14f; }   // bayonetta (bayonetta WaistN)
    if (k == 0x39) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = -1.97f; fl_ofwd = 0.17f; fl_up = 9.75f; fl_fwd = 0.17f; }   // kamui (kamui WaistN)
    if (k == 0x3a) { fl_rad = 54.57f; fl_joint = 0xb; fl_oup = 1.78f; fl_ofwd = 0.24f; fl_up = 39.47f; fl_fwd = 1.45f; }   // koopag (koopa WaistN)
    if (k == 0x3b) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = 1.48f; fl_ofwd = -0.27f; fl_up = 6.57f; fl_fwd = 0.14f; }   // warioman (wario WaistN)
    if (k == 0x3c) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = -1.02f; fl_ofwd = 0.67f; fl_up = 13.29f; fl_fwd = 0.89f; }   // littlemacg (littlemac WaistN)
    if (k == 0x3d) { fl_rad = 13.50f; fl_joint = 0xb; fl_oup = 0.00f; fl_ofwd = 0.00f; fl_up = 9.25f; fl_fwd = 0.06f; }   // lucariom (lucario WaistN)
    if (k == 0x3e) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = 1.00f; fl_ofwd = 0.50f; fl_up = 7.74f; fl_fwd = 0.50f; }   // miienemyf (miifighter WaistN)
    if (k == 0x3f) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = 1.00f; fl_ofwd = 0.50f; fl_up = 7.74f; fl_fwd = 0.50f; }   // miienemys (miiswordsman WaistN)
    if (k == 0x40) { fl_rad = 14.00f; fl_joint = 0xb; fl_oup = 1.00f; fl_ofwd = 0.50f; fl_up = 7.74f; fl_fwd = 0.50f; }   // miienemyg (miigunner WaistN)
    if (k == 0x41) { fl_rad = 13.00f; fl_joint = 0xb; fl_oup = 1.00f; fl_ofwd = 0.00f; fl_up = 7.57f; fl_fwd = 0.03f; }   // supamario (mario WaistN)
    if (k == 0x42) { fl_rad = 15.50f; fl_joint = 0xb; fl_oup = -3.00f; fl_ofwd = 0.00f; fl_up = 10.64f; fl_fwd = 0.00f; }   // edge (edge WaistN)
    if (k == 0x43) { fl_rad = 14.50f; fl_joint = 0xb; fl_oup = -0.41f; fl_ofwd = -0.02f; fl_up = 8.29f; fl_fwd = 0.40f; }   // gaogaen (gaogaen WaistN)
    if (k == 0x44) { fl_rad = 13.00f; fl_joint = 0xb; fl_oup = 1.50f; fl_ofwd = 0.00f; fl_up = 8.50f; fl_fwd = 0.00f; }   // pickel (pickel WaistN)
    if (k == 0x45) { fl_rad = 15.00f; fl_joint = 0xb; fl_oup = -1.50f; fl_ofwd = 0.00f; fl_up = 10.52f; fl_fwd = 0.00f; }   // brave (brave WaistN)
    if (k == 0x46) { fl_rad = 11.00f; fl_joint = 0xb; fl_oup = 0.45f; fl_ofwd = 0.22f; fl_up = 5.52f; fl_fwd = 0.71f; }   // pzenigame (pzenigame WaistN)
}
// ---- end of flare targets ----

int fl_target_lost()
{
    float st;
    if (WorkModuleF(0, 0x0f000023 + 0x4 * fl_slot) == 0)
    {
        return 1;
    }
    st = WorkModuleF(0, 0x0f0000ba + 0x8 * fl_slot);
    if (st == 177.0f || st == 178.0f || st == 335.0f)      // Dead 0xB1, Rebirth 0xB2, Entry 0x14F
    {
        return 1;
    }
    return 0;
}

void fl_centre()
{
    float lr;
    float jx;
    float jy;
    lr = WorkModuleF(0, 0x0f000023 + 0x4 * fl_slot);
    fl_cx = WorkModuleF(0, 0x0f000020 + 0x4 * fl_slot) + fl_fwd * lr;
    fl_cy = WorkModuleF(0, 0x0f000021 + 0x4 * fl_slot) + fl_up;
    if (fl_joint >= 0)                     // the joint where it is now (0x0F000290 + 4 x target: the bone, then
    {                                      // its x / y), + the offsets
        WorkModule(0, (float)fl_joint, 0x0f00029c + 0x4 * fl_slot);
        jx = WorkModuleF(0, 0x0f00029d + 0x4 * fl_slot);
        jy = WorkModuleF(0, 0x0f00029e + 0x4 * fl_slot);
        if (jx != 0 || jy != 0)
        {
            fl_cx = jx + fl_ofwd * lr;
            fl_cy = jy + fl_oup;
        }
    }
    fl_cz = WorkModuleF(0, 0x0f000022 + 0x4 * fl_slot);
    PostureModule(0x2714, fl_cx, fl_cy, fl_cz);
}

// the slot angle of orb i (f_7203e290f0: the dummy's phase + 360 / count x its index), radians
float fl_angle(int i)
{
    return (fl_rot + 360.0f / (float)fl_count * (float)i) * 0.0174533f;
}

// an orb at radius rho on its slot: its effect and its hitbox (the offset in this object's frame: z along its
// facing, y up)
void fl_place(int i, float rho)
{
    fl_place_hb(i, rho, 0x1);
}

// hb 0: no hitbox to move (an appearing orb's is removed: test 67 crashed when the shot hit, inferred from setting
// a removed hitbox's offsets)
void fl_place_hb(int i, float rho, int hb)
{
    float a;
    float dx;
    float dy;
    a = fl_angle(i);
    dx = rho * MathF(0x4, a);
    dy = rho * MathF(0x5, a);
    if (fl_fx(i) != 0)
    {
        EffectModule(0x17, fl_fx(i), fl_cx + dx, fl_cy + dy, fl_cz);
    }
    if (hb && fl_var(i) >= 2.0f)           // only a striking / exploding orb has a hitbox (fl_hitboxes)
    {
        AttackModule(0x1, i, 0, dy, dx * PostureModuleF(0));
    }
}

// the orbs' hitboxes again (ids 0-4 from the orbit script, the Parts asked by fl_clear with new hit records): the
// ones not in play off,
// a striking orb's (state 2) TRY damage / angle, an exploding one's (3) EXP size on top
void fl_hitboxes()
{
    int i;
    float st;
    fl_set(0x14, (float)(fl_clr0 + 0x2 * fl_clr1));   // VAR_20: the orbit script's Hit_Log_Clear (1 / 2 / 3)
    func_24(fl_status, 0, 1.0f);
    i = 0;
    while (i < 0x5)
    {
        st = fl_var(i);
        if (st == 2.0f || st == 3.0f)
        {
            AttackModule(0x271a, i, 6.5f);
            AttackModule(0x2739, i, 0x35);
            if (st == 3.0f)
            {
                AttackModule(0x271b, i, 5.0f);         // test 140: 5 (3.5 before)
            }
        }
        else                                   // orbiting (or appearing, gone, not made): none. Ultimate's
        {                                      // orbiting orbs (Fly, 7 damage) never hit their own target (user's
            AttackModule(0x2718, i);           // Ultimate clip: they pass through Donkey Kong's hands, no damage);
        }                                      // a hitbox can't leave one fighter out, so they hit no one here
        i += 1;
    }
}

// 1 while an orb is exploding (state 3: test 140, the next waits for it)
int fl_exploding()
{
    int i;
    i = 0;
    while (i < fl_count)
    {
        if (fl_var(i) == 3.0f)
        {
            return 0x1;
        }
        i += 1;
    }
    return 0;
}

// orb i's Part (i % 2) gets a new hit record at the next fl_hitboxes
void fl_clear(int i)
{
    if (i == 0x1 || i == 0x3)
    {
        fl_clr1 = 0x1;
    }
    else
    {
        fl_clr0 = 0x1;
    }
}

// a frame's clears done: none asked until the next
void fl_clear_done()
{
    fl_clr0 = 0;
    fl_clr1 = 0;
    fl_set(0x14, 0);
}

// Ultimate's ORBIT loop step 4: ceil(n) orbs, the new ones made at the centre (PRE: sliding to their slot over
// orbit_frame 5: pos = slot + (pos - slot) x k / 5, k 4..0)
void fl_make_orbs()
{
    int want;
    int i;
    want = (int)fl_n;
    if ((float)want < fl_n)
    {
        want += 1;
    }
    if (want > 0x5)
    {
        want = 0x5;
    }
    if (want <= fl_count)
    {
        return;
    }
    i = fl_count;
    while (i < want)
    {
        fl_set(i, 1.0f);
        fl_set(0x5 + i, 5.0f);
        fl_set(0xa + i, fl_rad);
        fl_set(0xf + i, 0);
        fl_fx_play(i, fl_fx_bullet(), fl_cx, fl_cy, 1.0f);
        i += 1;
    }
    fl_count = want;
    fl_hitboxes();
}

// the slide's radius factor after k of the 5 appear frames: prod (j / 5), j = k..4
float fl_appear(float k)
{
    float f;
    float j;
    f = 1.0f;
    j = k;
    while (j < 5.0f)
    {
        f = f * j / 5.0f;
        j += 1.0f;
    }
    return f;
}

// orbit speed lerp(orbit_speed_min 0.4, orbit_speed_max 0.8, n / P 5) (the target's 0x19f190006a: 5 for all but
// Giga Bowser); the phase + 2 pi x speed degrees a frame (f_7203e2f270)
void fl_spin_on()
{
    fl_rot += 2.0f * 3.14159f * fl_spin;
    if (fl_rot >= 360.0f)
    {
        fl_rot -= 360.0f;
    }
}

void fl_orbit_orbs()
{
    int i;
    float t;
    i = 0;
    while (i < fl_count)
    {
        if (fl_var(i) == 1.0f)
        {
            t = fl_var(0x5 + i);
            if (t > 0)
            {
                t -= 1.0f;
                fl_set(0x5 + i, t);
                if (t <= 0)
                {
                    fl_clear(i);
                    fl_hitboxes();
                }
                fl_place_hb(i, fl_var(0xa + i) * (1.0f - fl_appear(t)), t <= 0);
            }
            else
            {
                fl_place(i, fl_var(0xa + i));
            }
        }
        i += 1;
    }
}

// the end of every orb (the target gone): edge_shadowflare_bullet_end where it was
void fl_finish()
{
    int i;
    i = 0;
    while (i < fl_count)
    {
        if (fl_var(i) == 1.0f || fl_var(i) == 2.0f)
        {
            fl_fx_play(i, fl_fx_end(), fl_cx + fl_var(0xa + i) * MathF(0x4, fl_angle(i)),
                       fl_cy + fl_var(0xa + i) * MathF(0x5, fl_angle(i)), 1.0f);
            fl_fx_set(i, 0);
        }
        i += 1;
    }
    fl_share(0, 0);
    BattleObject(0x9);
}

// ---- 2 ORBIT (2f490 / 2e640 / 30a30): life orbit_life 240 (+ shots' extensions out of orbit_life_max 210)
void fl_orbit_loop()
{
    int ext;
    fl_clear_done();
    if (fl_expired())
    {
        return;
    }
    fl_move(0, 0);
    if (fl_target_lost())
    {
        fl_finish();
        return;
    }
    fl_centre();
    if (fl_shared(0x2) > 0)
    {
        fl_n += fl_shared(0x2);
        if (fl_n > 5.0f)
        {
            fl_n = 5.0f;
        }
        fl_share(0x2, 0);
    }
    if (fl_shared(0x3) > 0)
    {
        ext = (int)fl_shared(0x3);
        if (ext > fl_pool)
        {
            ext = fl_pool;
        }
        fl_pool -= ext;
        fl_life += ext;
        fl_share(0x3, 0);
    }
    fl_life -= 1;
    fl_beat += 1;
    fl_share(0, (float)fl_life + 1.0f);
    fl_share(0x1, (float)fl_beat);
    if (fl_life <= 0)
    {
        fl_to(0x3);
        return;
    }
    fl_make_orbs();
    fl_spin = 0.4f + 0.4f * fl_n / 5.0f;
    fl_spin_on();
    fl_orbit_orbs();
}

void fl_orbit_main()
{
    int i;
    if (fl_phase == 0x1)
    {
        fl_phase = 0x2;
        fl_clear_done();
        fl_life = 0xf0;
        fl_pool = 0xd2;
        fl_count = 0;
        fl_rot = 0;
        i = 0;
        while (i < 0x14)
        {
            fl_set(i, 0);
            i += 1;
        }
        fl_status = 0x3;                       // the orbit script (FLARE1_MOTIONS)
        fl_target_shape((int)WorkModuleF(0, 0x0f0000bd + 0x8 * fl_slot));
        fl_centre();
        fl_share(0x2, 0);
        fl_share(0x3, 0);
        fl_beat += 1;
        fl_share(0, (float)fl_life);
        fl_share(0x1, (float)fl_beat);
        fl_make_orbs();
    }
    fl_move(0, 0);
    callFunc3(fl_orbit_loop);
}

// ---- 3 CONVE (2f500 / 2ecc0 / 2f5e0) and the orbs' strikes (flare2 TRY 2af20 / 283b0 / 2c980, EXP 2b830 /
// 2bce0). R = n / 5 (the dummy's float the conve_* pairs are lerped by: native, inferred). The spin brakes
// lerp(conve_min_brake .1, conve_max_brake .1, R) a frame to a floor lerp(conve_min_speed_min .3, conve_max .4, R);
// orb i strikes after conve_frame 8 x i frames (inferred: 0x33ee1c8): radial speed from -lerp(conve_min_reverse 4,
// conve_max_reverse 5.2, R) (out first), + lerp(conve_min_accel .45, .85, R) a frame up to lerp(conve_min_speed_max
// 7, 14, R); its radius - v, then v further in (TRY's set_pos); within conve_radius 0.5 (or v): EXP, one frame
// (6.5 damage, size 3.5), edge_shadowflare_bullet_hit x 1.3, gone. TRY: 6.5 damage, 53 degrees, size 1.5
// (Ultimate's KBG 75 / BKB 50 against the orbit's 75 / 65: the BKB kept at the orbit's, no MSC op for it).
// Each strike (and its EXP) starts its Part's hit record anew (fl_clear), as Ultimate's new status does.
float fl_lerp(float a, float b, float t)
{
    return a + (b - a) * t;
}

void fl_conve_loop()
{
    int i;
    int live;
    float R;
    float v;
    float rho;
    float t;
    fl_clear_done();
    if (fl_expired())
    {
        return;
    }
    fl_move(0, 0);
    if (fl_target_lost())
    {
        fl_finish();
        return;
    }
    fl_centre();
    fl_beat += 1;
    fl_share(0x1, (float)fl_beat);
    R = fl_n / 5.0f;
    fl_spin = fl_spin - 0.1f;
    if (fl_spin < fl_lerp(0.3f, 0.4f, R))
    {
        fl_spin = fl_lerp(0.3f, 0.4f, R);
    }
    fl_spin_on();
    live = 0;
    i = 0;
    while (i < fl_count)
    {
        if (fl_var(i) == 1.0f)
        {
            live += 1;
            t = fl_var(0x5 + i) - 1.0f;
            fl_set(0x5 + i, t);
            if (t <= 0)
            {
                fl_set(i, 2.0f);
                fl_set(0xf + i, -fl_lerp(4.0f, 5.2f, R));
                fl_clear(i);
                fl_hitboxes();
                rho = fl_var(0xa + i);
                fl_fx_play(i, fl_fx_attack(), fl_cx + rho * MathF(0x4, fl_angle(i)),
                           fl_cy + rho * MathF(0x5, fl_angle(i)), 1.0f);
            }
            fl_place(i, fl_var(0xa + i));
        }
        else if (fl_var(i) == 2.0f)
        {
            live += 1;
            v = fl_var(0xf + i) + fl_lerp(0.45f, 0.85f, R);
            if (v > fl_lerp(7.0f, 14.0f, R))
            {
                v = fl_lerp(7.0f, 14.0f, R);
            }
            fl_set(0xf + i, v);
            rho = fl_var(0xa + i) - v;
            if (rho < 0)
            {
                rho = 0;
            }
            fl_set(0xa + i, rho);
            rho = rho - v;
            if ((rho <= 0.5f || rho <= v) && (WorkModuleF(0, 0x0f00005b + 0x8 * fl_slot) > 0 || fl_exploding()))
            {
                // at the centre with the target still in hitstop (another orb's hit) or another orb exploding: it waits
                // there, its EXP after (test 112, the user: the orbs "don't connect with the opponent, mostly when
                // there's more than one orb": a strike landing in the hitlag of the one before it was lost; test 140:
                // "Side special when charged still does not always have each orb connect": two exploding at once (a
                // fighter takes one hit a frame from them, and they share 2 Parts) lost one)
                fl_set(0xa + i, 0);
                fl_place(i, 0.5f);
            }
            else if (rho <= 0.5f || rho <= v)
            {
                // EXP: 3 frames at the centre (test 140; 1 before: a launched fighter could be off the centre that
                // frame), its hit record new once at its start (one hit), then gone
                fl_set(i, 3.0f);
                fl_set(0xf + i, 3.0f);
                fl_clear(i);
                fl_hitboxes();
                fl_place(i, 0.5f);
                fl_fx_play(i, fl_fx_exp(), fl_cx, fl_cy, 1.3f);
                fl_fx_set(i, 0);
            }
            else
            {
                fl_place(i, rho);
            }
        }
        else if (fl_var(i) == 3.0f)
        {
            live += 1;
            fl_set(0xf + i, fl_var(0xf + i) - 1.0f);
            if (fl_var(0xf + i) <= 0)
            {
                fl_set(i, 4.0f);
                AttackModule(0x2718, i);
            }
            else
            {
                fl_place(i, 0.5f);
            }
        }
        i += 1;
    }
    if (live == 0)
    {
        fl_share(0, 0);
        BattleObject(0x9);
    }
}

void fl_conve_main()
{
    int i;
    if (fl_phase == 0x2)
    {
        fl_phase = 0x3;
        fl_share(0, 0);                        // a later shot starts its own controller
        i = 0;
        while (i < fl_count)
        {
            fl_set(0x5 + i, 8.0f * (float)i + 1.0f);
            i += 1;
        }
        fl_status = 0x3;
    }
    fl_move(0, 0);
    callFunc3(fl_conve_loop);
}

void fl_setup()
{
    global7 = 0x5;                             // the status count (dein's func_8: statuses >= it are refused;
                                               // test 64: 0x2 from fire.c kept the shot from becoming the orbs)
    fl_phase = 0;
    fl_total = 0;
    sv_set_mem(0x1, 0, 0, fl_pre);
    sv_set_mem(0x1, 0, 0x1, fl_pre);
    sv_set_mem(0x1, 0, 0x2, fl_pre);
    sv_set_mem(0x1, 0, 0x3, fl_pre);
    sv_set_mem(0x1, 0, 0x4, fl_pre);
    sv_set_mem(0x1, 0x1, 0, fl_fly_main);
    sv_set_mem(0x1, 0x1, 0x1, fl_hit_main);
    sv_set_mem(0x1, 0x1, 0x2, fl_orbit_main);
    sv_set_mem(0x1, 0x1, 0x3, fl_conve_main);
    sv_set_mem(0x1, 0x1, 0x4, fl_end_main);
    // motion indices as they are (no custom-variant offset: func_40 not installed)
    global11 = func_19;
    global21 = 0;
}

void main()
{
    printf("ENTRY This Fighter is driven by msc.");
    func_0();
    global0 = sys_7(0);
    global1 = sys_7(0x1);
    fl_setup();
    sys_0(0x2, func_3);
    sys_0(0x3, func_7);
    sys_0(0x4, func_12);
    set_main(func_1);
}
