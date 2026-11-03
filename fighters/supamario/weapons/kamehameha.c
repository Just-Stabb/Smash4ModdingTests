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
int kame_shielded;      // fix 85: flying on through a shield it met
int kame_owner;         // fix 87: Supamario's slot (the fighter at or behind the spawn point, nearest it)
int kame_catch;         // fix 86: the fly motion catching up to this frame (0: not)
float kame_catch_rate;  // its rate once there (0: frozen, the hold; 1: on, flying)

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

// effect `id` at every body piece's place (dropped at the head every KAME_SEG_EVERY frames of the
// flight), behind the head where it stopped. The last argument 1 puts them in the bone's frame (Z
// along the beam); with 0, Z was screen depth (test 18: a diagonal line)
void kame_pieces(int id)
{
    int f;
    float z;
    f = KAME_SEG_FIRST;
    while (f <= kame_flown)
    {
        z = -(float)(kame_flown - f) * kame_speed();
        EffectModule(0x2710, id, 0, 0, 0, z, 0, 0, 0, 1.0f, 0, 0, 0, 0, 0, 0, 0x1);
        // the pieces' frames: KAME_SEG_FIRST, then every KAME_SEG_EVERY-th
        f += 0x1;
        while (f % KAME_SEG_EVERY != 0)
        {
            f += 0x1;
        }
    }
}

// the end: the body pieces replaced by dissolving ones
void kame_dissolve()
{
    kame_pieces(kame_dis_id());
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

// Fix 85 (user): the hold creeps forward (KAME_CREEP a frame) so a moving target stays in it; a shield doesn't
// stop it: it flies on, multi-hitting the shield (kame_shielded); its body hitbox covers the whole beam until it
// dissolves (tools/supamario_kame_build.py fly_game: the hold plays the fly motion from the frame it hit at,
// frozen, kame_hold_begin). A fighter around the head (from 10 behind it to 20 ahead, its feet 8 above to 28
// below it: Supamario stays behind it): 2 one not shielding, 1 only shielding ones (status 0x1B-0x1E, the slot's
// STATUS variable, docs/position-variables.md), 0 none
int kame_near()
{
    int s;
    int r;
    float x;
    float y;
    float f;
    float dx;
    float dy;
    float st;
    x = PostureModuleF(0x1);
    y = PostureModuleF(0x2);
    f = PostureModuleF(0);
    r = 0;
    s = 0;
    while (s < 0x8)
    {
        if (WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0)
        {
            dx = (WorkModuleF(0, 0x0f000020 + 0x4 * s) - x) * f;
            dy = y - WorkModuleF(0, 0x0f000021 + 0x4 * s);
            if (s != kame_owner && dx > -10.0f && dx < 32.0f && dy > -8.0f && dy < 28.0f)
            {
                st = WorkModuleF(0, 0x0f0000ba + 0x8 * s);
                if (st >= 27.0f && st <= 30.0f)
                {
                    if (r == 0)
                    {
                        r = 0x1;
                    }
                }
                else
                {
                    r = 0x2;
                }
            }
        }
        s += 1;
    }
    return r;
}

// the lingering body capsule's frames (fix 86, user: the whole flight was too much): the head's last
// KAME_LINGER_n frames
int kame_linger()
{
    if (kame_level == 0x1)
    {
        return KAME_LINGER_2;
    }
    else if (kame_level == 0x2)
    {
        return KAME_LINGER_3;
    }
    return KAME_LINGER_1;
}

// the fly motion again from frame 0 (its head effects and hitboxes back: a status change ends them), run to
// frame `f` in one game frame (rate f: every command on the way runs, the body capsule ends as long as at f),
// then at rate `after` (kame_catch_update). Fix 86: fix 85 started it at frame f instead, which most likely ran
// none of the commands before f (user: on a shield it deleted itself: no head, no hitboxes)
void kame_play_to(int f, float after)
{
    if (f > kame_linger())
    {
        f = kame_linger();      // nothing in the script past the capsule's last frame
    }
    func_24(kame_level, 0, 1.0f);
    if (f < 0x1)
    {
        MotionModule(0x4, after);
        kame_catch = 0;
        return;
    }
    MotionModule(0x4, (float)f);
    kame_catch = f;
    kame_catch_rate = after;
}

void kame_catch_update()
{
    if (kame_catch > 0 && MotionModuleF(0x1) >= (float)kame_catch - 0.01f)
    {
        MotionModule(0x4, kame_catch_rate);
        kame_catch = 0;
    }
}

// fix 86 (user: the multi-hits should force the opponent into the tip of the beam, where the finish hits: held by
// the lingering body they never got it): every fighter not shielding in the body (behind the head, up to the
// capsule's length and 8 more, its feet 8 above to 28 below the head) is moved toward the head along the beam,
// half the way a frame (at most 12, at least 1.5); `snap`: all the way (the finish). Through the slot position
// variables (docs/position-variables.md: a weapon may write them); Supamario stays behind the start
void kame_pull(int snap)
{
    int s;
    int n;
    float x;
    float y;
    float f;
    float dx;
    float dy;
    float len;
    float st;
    float step;
    x = PostureModuleF(0x1);
    y = PostureModuleF(0x2);
    f = PostureModuleF(0);
    n = kame_flown;
    if (n > kame_linger())
    {
        n = kame_linger();
    }
    len = (float)n * kame_speed() + 8.0f;
    s = 0;
    while (s < 0x8)
    {
        if (WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0)
        {
            dx = (WorkModuleF(0, 0x0f000020 + 0x4 * s) - x) * f;
            dy = y - WorkModuleF(0, 0x0f000021 + 0x4 * s);
            st = WorkModuleF(0, 0x0f0000ba + 0x8 * s);
            if (s != kame_owner && dx < -1.0f && dx > -len && dy > -8.0f && dy < 28.0f && (st < 27.0f || st > 30.0f))
            {
                step = -dx;
                if (snap == 0)
                {
                    step = -dx * 0.5f;
                    if (step > 12.0f)
                    {
                        step = 12.0f;
                    }
                    if (step < 1.5f)
                    {
                        step = 1.5f;
                    }
                    if (step > -dx)
                    {
                        step = -dx;
                    }
                }
                WorkModule(0, WorkModuleF(0, 0x0f000020 + 0x4 * s) + step * f, 0x0f000020 + 0x4 * s);
            }
        }
        s += 1;
    }
}

// fix 87 (user: the pull took Supamario into the tip, not the opponent; at low charge a shield still stopped
// it): Supamario's slot, left out of kame_near and kame_pull: at the beam's spawn (status 0) the fighter at or
// behind its start (along its facing, up to 2 ahead) nearest to it (-1: none)
int kame_find_owner()
{
    int s;
    int best;
    float x;
    float y;
    float f;
    float dx;
    float dy;
    float d;
    float bd;
    x = PostureModuleF(0x1);
    y = PostureModuleF(0x2);
    f = PostureModuleF(0);
    best = 0xffffffff;
    bd = 0;
    s = 0;
    while (s < 0x8)
    {
        if (WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0)
        {
            dx = (WorkModuleF(0, 0x0f000020 + 0x4 * s) - x) * f;
            dy = WorkModuleF(0, 0x0f000021 + 0x4 * s) - y;
            d = dx * dx + dy * dy;
            if (dx < 2.0f && (best < 0 || d < bd))
            {
                best = s;
                bd = d;
            }
        }
        s += 1;
    }
    return best;
}

// the hold begins: where it hit, the fly motion run to that frame and frozen (the body capsule as long as it was),
// fresh body pieces
void kame_hold_begin()
{
    kame_phase = 0x1;
    kame_flown = kame_frame;
    kame_frame = 0;
    kame_shielded = 0;
    kame_play_to(kame_flown, 0);
    // fresh body pieces: theirs last the flight only (KAME_SEG_n's hold, so a beam the game
    // removes at a blast zone leaves its body half as long: user, test 29), these the hold and
    // the finish
    EffectModule(0x2723, kame_seg_id(), 0x1, 0x1);
    kame_pieces(kame_seg_id());
}

void kame_fly_main()
{
    if (global4 == 0)
    {
        kame_phase = 0;
        kame_total = 0;
        kame_shielded = 0;
        kame_catch = 0;
        kame_owner = kame_find_owner();
    }
    if (kame_phase != 0)
    {
        // a fly status asked for again after the hit: back to the hold / finish
        kame_status(0x2 + kame_phase);
        return;
    }
    // the charge level: Supamario's custom slot (int 0x10000048), which the game copies into a new
    // weapon's 0x10000005 (init struct +0x5C, 0x02F062C0), set to the level while he generates it
    // (tests 21 / 22: ArticleModule 0x2713 from him never changed the status: he doesn't keep the
    // beam's handle, as 0x2717 "exists" says no for it)
    kame_level = WorkModule(0x6, 0x10000005);
    if (kame_level < 0 || kame_level > 0x2)
    {
        kame_level = 0;
    }
    // for the finish's ACMD (its one script picks the launcher by it): 1 / 2 / 3, in the fireball's
    // life variable (nothing counts it down since test 15)
    WorkModule(0x7, kame_level + 0x1, 0x10000004);
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
    if (kame_phase == 0x1)
    {
        kame_hold_loop();       // a hold begun while flying on through a shield
        return;
    }
    if (kame_expired())
    {
        return;
    }
    kame_catch_update();
    if (kame_shielded && kame_phase == 0 && AttackModule(0x2727))
    {
        // connected again while flying on through a shield: on if it's only shields, else the hold
        if (kame_near() == 0x1)
        {
            AttackModule(0x2724);
        }
        else
        {
            kame_hold_begin();
            kame_move(KAME_CREEP);
            return;
        }
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
    if (kame_frame == KAME_SEG_FIRST || (kame_frame > KAME_SEG_FIRST && kame_frame % KAME_SEG_EVERY == 0))
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
        if (kame_near() == 0x1)
        {
            // a shield (fix 85): it flies on, its hitboxes back (the fly motion again from its frame: the status
            // change took them), multi-hitting the shield; a later hit on a fighter not shielding holds it
            kame_shielded = 0x1;
            kame_play_to(kame_frame, 1.0f);
            AttackModule(0x2724);
            kame_move(kame_speed());
            callFunc3(kame_fly_loop);
            return;
        }
        kame_hold_begin();
    }
    kame_move(KAME_CREEP);
    callFunc3(kame_hold_loop);
}

void kame_hold_loop()
{
    if (kame_expired())
    {
        return;
    }
    kame_catch_update();
    kame_move(KAME_CREEP);      // fix 85: creeping forward
    kame_pull(0x1);             // fix 86: into the tip (fix 87: all the way every frame, user: the opponent, not the owner)
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
        kame_pull(0x1);         // fix 86: everyone in the body to the tip, where the launcher is
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
