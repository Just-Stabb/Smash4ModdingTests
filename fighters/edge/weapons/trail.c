// Sephiroth: held forward air's snake (weapon kind 0x199, a copy of Zelda's light arrow): its MSC (tools/edge_snake_articles_msc.py)
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
    global21 = 0;           // motion indices as they are (flare1.c)
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
    StatusModule(0x5, 0xffffffff, 0, 0, 0, 0, 0, 0, 0, 0);
    return 0;
}



void func_48()
{
    
}

// ---- Sephiroth's up special trail (tools/edge_trail_msc.py; test 124): one stretch of the purple line his path leaves
// during either up special's attack, up to 16 points; still, removed after 360 frames
int tr_slot;            // his player slot (0 - 7), -1: not found
int tr_life;            // frames left
int tr_base;            // its first point's number
int tr_seen;            // the newest point's number seen
int tr_n;               // points taken
int tr_stale;           // 1: the trail it belongs to is over: it does nothing more
int tr_answered;        // the last query answered
float tr_sx;            // the newest point seen
float tr_sy;
float tr_ox;            // its first point (where it stands)
float tr_oy;
float tr_px;            // tr_unpack's result
float tr_py;
float tr_x0;
float tr_y0;
float tr_x1;
float tr_y1;
float tr_x2;
float tr_y2;
float tr_x3;
float tr_y3;
float tr_x4;
float tr_y4;
float tr_x5;
float tr_y5;
float tr_x6;
float tr_y6;
float tr_x7;
float tr_y7;
float tr_x8;
float tr_y8;
float tr_x9;
float tr_y9;
float tr_x10;
float tr_y10;
float tr_x11;
float tr_y11;
float tr_x12;
float tr_y12;
float tr_x13;
float tr_y13;
float tr_x14;
float tr_y14;
float tr_x15;
float tr_y15;

int tr_points() { return 16; }

float tr_get_x(int k)
{
    if (k == 0)
    {
        return tr_x0;
    }
    if (k == 1)
    {
        return tr_x1;
    }
    if (k == 2)
    {
        return tr_x2;
    }
    if (k == 3)
    {
        return tr_x3;
    }
    if (k == 4)
    {
        return tr_x4;
    }
    if (k == 5)
    {
        return tr_x5;
    }
    if (k == 6)
    {
        return tr_x6;
    }
    if (k == 7)
    {
        return tr_x7;
    }
    if (k == 8)
    {
        return tr_x8;
    }
    if (k == 9)
    {
        return tr_x9;
    }
    if (k == 10)
    {
        return tr_x10;
    }
    if (k == 11)
    {
        return tr_x11;
    }
    if (k == 12)
    {
        return tr_x12;
    }
    if (k == 13)
    {
        return tr_x13;
    }
    if (k == 14)
    {
        return tr_x14;
    }
    if (k == 15)
    {
        return tr_x15;
    }
    return 0.0f;
}

float tr_get_y(int k)
{
    if (k == 0)
    {
        return tr_y0;
    }
    if (k == 1)
    {
        return tr_y1;
    }
    if (k == 2)
    {
        return tr_y2;
    }
    if (k == 3)
    {
        return tr_y3;
    }
    if (k == 4)
    {
        return tr_y4;
    }
    if (k == 5)
    {
        return tr_y5;
    }
    if (k == 6)
    {
        return tr_y6;
    }
    if (k == 7)
    {
        return tr_y7;
    }
    if (k == 8)
    {
        return tr_y8;
    }
    if (k == 9)
    {
        return tr_y9;
    }
    if (k == 10)
    {
        return tr_y10;
    }
    if (k == 11)
    {
        return tr_y11;
    }
    if (k == 12)
    {
        return tr_y12;
    }
    if (k == 13)
    {
        return tr_y13;
    }
    if (k == 14)
    {
        return tr_y14;
    }
    if (k == 15)
    {
        return tr_y15;
    }
    return 0.0f;
}

void tr_set(int k, float x, float y)
{
    if (k == 0)
    {
        tr_x0 = x;
        tr_y0 = y;
    }
    if (k == 1)
    {
        tr_x1 = x;
        tr_y1 = y;
    }
    if (k == 2)
    {
        tr_x2 = x;
        tr_y2 = y;
    }
    if (k == 3)
    {
        tr_x3 = x;
        tr_y3 = y;
    }
    if (k == 4)
    {
        tr_x4 = x;
        tr_y4 = y;
    }
    if (k == 5)
    {
        tr_x5 = x;
        tr_y5 = y;
    }
    if (k == 6)
    {
        tr_x6 = x;
        tr_y6 = y;
    }
    if (k == 7)
    {
        tr_x7 = x;
        tr_y7 = y;
    }
    if (k == 8)
    {
        tr_x8 = x;
        tr_y8 = y;
    }
    if (k == 9)
    {
        tr_x9 = x;
        tr_y9 = y;
    }
    if (k == 10)
    {
        tr_x10 = x;
        tr_y10 = y;
    }
    if (k == 11)
    {
        tr_x11 = x;
        tr_y11 = y;
    }
    if (k == 12)
    {
        tr_x12 = x;
        tr_y12 = y;
    }
    if (k == 13)
    {
        tr_x13 = x;
        tr_y13 = y;
    }
    if (k == 14)
    {
        tr_x14 = x;
        tr_y14 = y;
    }
    if (k == 15)
    {
        tr_x15 = x;
        tr_y15 = y;
    }
}

int tr_find_owner()
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

float tr_shared(int k)
{
    return WorkModuleF(0, 0x0f000340 + 0x8 * tr_slot + k);
}

// a point as he packs it (edge.c edge_tr_pack): (x + 512) x 2 whole x 2048 + (y + 512) x 2 whole, half units
void tr_unpack(float v)
{
    int c;
    int ix;
    c = (int)v;
    ix = c / 0x800;
    tr_px = (float)ix * 0.5f - 512.0f;
    tr_py = (float)(c - ix * 0x800) * 0.5f - 512.0f;
}

// 1 if the pieces (ax, ay) - (bx, by) and (cx, cy) - (dx, dy) cross (properly: not at an end)
int tr_cross(float ax, float ay, float bx, float by, float cx, float cy, float dx, float dy)
{
    float d1;
    float d2;
    float d3;
    float d4;
    d1 = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
    d2 = (bx - ax) * (dy - ay) - (by - ay) * (dx - ax);
    d3 = (dx - cx) * (ay - cy) - (dy - cy) * (ax - cx);
    d4 = (dx - cx) * (by - cy) - (dy - cy) * (bx - cx);
    if ((d1 > 0.0f && d2 < 0.0f || d1 < 0.0f && d2 > 0.0f) && (d3 > 0.0f && d4 < 0.0f || d3 < 0.0f && d4 > 0.0f))
    {
        return 0x1;
    }
    return 0;
}

// the newest piece (tr_sx, tr_sy) - (x, y), number num - 1 - num, against this stretch's own pieces not next to it: a
// crossing at piece m (its start's number) is reported in shared 4 as -m, the latest m kept
void tr_test(float x, float y, int num)
{
    int k;
    int m;
    float r;
    k = 0;
    while (k < tr_n - 1 && tr_base + k + 1 <= num - 2)
    {
        if (tr_cross(tr_sx, tr_sy, x, y, tr_get_x(k), tr_get_y(k), tr_get_x(k + 1), tr_get_y(k + 1)))
        {
            m = tr_base + k;
            r = tr_shared(0x4);
            if (r > -1000.0f || (float)m > -r)
            {
                WorkModule(0, -(float)m, 0x0f000340 + 0x8 * tr_slot + 0x4);
            }
        }
        k = k + 1;
    }
}

// a query (shared 6 = start x 512 + count + 0.5): its points numbered start .. start + count - 1 added to shared 5 (x)
// and 4 (y), once
void tr_answer(float v)
{
    int code;
    int st;
    int cnt;
    int k;
    float sx;
    float sy;
    code = (int)v;
    if (code == tr_answered)
    {
        return;
    }
    tr_answered = code;
    st = code / 0x200;
    cnt = code - st * 0x200;
    sx = 0.0f;
    sy = 0.0f;
    k = 0;
    while (k < tr_n)
    {
        // its first point is the stretch before's last: counted there (but the trail's first)
        if (tr_base + k >= st && tr_base + k < st + cnt && (k > 0 || tr_base == 1000))
        {
            sx = sx + tr_get_x(k);
            sy = sy + tr_get_y(k);
        }
        k = k + 1;
    }
    WorkModule(0, tr_shared(0x5) + sx, 0x0f000340 + 0x8 * tr_slot + 0x5);
    WorkModule(0, tr_shared(0x4) + sy, 0x0f000340 + 0x8 * tr_slot + 0x4);
}

// every frame: stale once the trail's over; a query answered; a new point tested against its pieces, and taken if it's
// this stretch's next
void tr_take()
{
    float v;
    int num;
    if (tr_stale || tr_slot < 0)
    {
        return;
    }
    v = tr_shared(0x6);
    if (v < 0.0f)
    {
        tr_stale = 0x1;
        return;
    }
    if (v - (float)((int)v) > 0.25f)
    {
        tr_answer(v);
        return;
    }
    num = (int)v;
    if (num <= tr_seen)
    {
        return;
    }
    tr_unpack(tr_shared(0x5));
    if (num == tr_seen + 1)
    {
        tr_test(tr_px, tr_py, num);
    }
    if (num == tr_base + tr_n && tr_n < tr_points())
    {
        tr_set(tr_n, tr_px, tr_py);
        tr_n = tr_n + 1;
    }
    tr_seen = num;
    tr_sx = tr_px;
    tr_sy = tr_py;
}

void tr_still()
{
    KineticModule(0x11, 0, 0, 0);
    KineticModule(0xf, 0, 0, 0);
}

// the joints: P_k at point k (the last taken for those past it), relative to the first point
void tr_pose()
{
    int k;
    int j;
    PostureModule(0, 1.0f);
    PostureModule(0x2714, tr_ox, tr_oy, PostureModuleF(0x3));
    k = 0;
    while (k < tr_points())
    {
        j = k;
        if (j > tr_n - 1)
        {
            j = tr_n - 1;
        }
        ModelModule(0x7, 0x7d2 + k, 0, tr_get_y(j) - tr_oy, tr_get_x(j) - tr_ox);
        k = k + 1;
    }
}

int tr_over()
{
    tr_life -= 1;
    if (tr_life <= 0 || tr_slot < 0)
    {
        BattleObject(0x9);
        return 0x1;
    }
    return 0;
}

void func_46()
{
    tr_slot = tr_find_owner();
    tr_life = 360;
    tr_n = 0;
    tr_stale = 0;
    tr_answered = 0;
    tr_ox = PostureModuleF(0x1);
    tr_oy = PostureModuleF(0x2);
    tr_base = 0;
    if (tr_slot >= 0)
    {
        tr_base = (int)tr_shared(0x6);
        tr_unpack(tr_shared(0x5));
        tr_ox = tr_px;
        tr_oy = tr_py;
        PostureModule(0x2714, tr_ox, tr_oy, WorkModuleF(0, 0x0f000022 + 0x4 * tr_slot));
    }
    tr_set(0, tr_ox, tr_oy);
    tr_n = 1;
    tr_seen = tr_base;
    tr_sx = tr_ox;
    tr_sy = tr_oy;
    tr_still();
    tr_pose();
    func_24(0, 0, 1.0f);
    callFunc3(func_47);
}

void func_47()
{
    if (tr_over())
    {
        return 0x1;
    }
    tr_still();
    tr_take();
    tr_pose();
}
