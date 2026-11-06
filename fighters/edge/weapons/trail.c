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

// ---- Sephiroth's up special trail (tools/edge_trail_msc.py; tests 124 / 126): one stretch of the purple line his
// path leaves during either up special's attack, up to 16 points; still, removed after 360 frames
int tr_slot;            // his player slot (0 - 7), -1: not found
int tr_life;            // frames left
int tr_base;            // its first point's number
int tr_seen;            // the newest point's number seen
int tr_n;               // points taken
int tr_over_t;          // 1: its trail is over (it takes no more points)
int tr_mark;            // points marked for the shape being asked (bit k: point k)
int tr_gone;            // pieces gone (bit k: piece k, points k - k + 1)
int tr_fill;            // pieces filling the shape (bit k)
int tr_ft;              // frames since the fill began (-1 none)
int tr_vanish;          // 1: its trail doesn't stay (held Octaslash's): it goes once its fill is over
float tr_lr;            // its facing as made (its model's +Z is the world's +X x this: test 127, a line turned the
                        // wrong way when he faced left; tests 124 - 126 set the facing to 1, which didn't turn it)
float tr_cx;            // the fill's middle
float tr_cy;
float tr_ox;            // its first point (where it stands)
float tr_oy;
float tr_px;            // tr_unpack's result
float tr_py;
float tr_sx;            // the newest point seen
float tr_sy;
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
int tr_jk0;
int tr_jn0;
int tr_jk1;
int tr_jn1;
int tr_jk2;
int tr_jn2;
int tr_jk3;
int tr_jn3;

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

// 1 << k
int tr_bit(int k)
{
    int b;
    b = 1;
    while (k > 0)
    {
        b = b * 2;
        k = k - 1;
    }
    return b;
}

int tr_has(int mask, int k)
{
    if ((mask / tr_bit(k)) - (mask / tr_bit(k + 1)) * 2 != 0)
    {
        return 0x1;
    }
    return 0;
}

// junction j: its piece (-1 none) / the other trail's piece number
int tr_get_jk(int k)
{
    if (k == 0)
    {
        return tr_jk0;
    }
    if (k == 1)
    {
        return tr_jk1;
    }
    if (k == 2)
    {
        return tr_jk2;
    }
    if (k == 3)
    {
        return tr_jk3;
    }
    return -1;
}

int tr_get_jn(int k)
{
    if (k == 0)
    {
        return tr_jn0;
    }
    if (k == 1)
    {
        return tr_jn1;
    }
    if (k == 2)
    {
        return tr_jn2;
    }
    if (k == 3)
    {
        return tr_jn3;
    }
    return 0;
}

void tr_set_j(int k, int p, int n)
{
    if (k == 0)
    {
        tr_jk0 = p;
        tr_jn0 = n;
    }
    if (k == 1)
    {
        tr_jk1 = p;
        tr_jn1 = n;
    }
    if (k == 2)
    {
        tr_jk2 = p;
        tr_jn2 = n;
    }
    if (k == 3)
    {
        tr_jk3 = p;
        tr_jn3 = n;
    }
}

// a crossing with another trail kept (its piece p, the other's piece number n), once
void tr_junction(int p, int n)
{
    int k;
    k = 0;
    while (k < 4)
    {
        if (tr_get_jk(k) == p && tr_get_jn(k) / 0x400 == n / 0x400)
        {
            return;
        }
        k = k + 1;
    }
    k = 0;
    while (k < 4)
    {
        if (tr_get_jk(k) < 0)
        {
            tr_set_j(k, p, n);
            return;
        }
        k = k + 1;
    }
}

// JQ X Y: its junctions with the other one's trail: X's piece number in 5, Y's in 4
void tr_junctions(int x, int y)
{
    int b;
    int k;
    int o;
    b = tr_base / 0x400;
    if (b == x)
    {
        o = y;
    }
    else if (b == y)
    {
        o = x;
    }
    else
    {
        return;
    }
    k = 0;
    while (k < 4)
    {
        if (tr_get_jk(k) >= 0 && tr_get_jn(k) / 0x400 == o && tr_has(tr_gone, tr_get_jk(k)) == 0)
        {
            if (b == x)
            {
                tr_share(0x5, (float)(tr_base + tr_get_jk(k)));
                tr_share(0x4, (float)tr_get_jn(k));
            }
            else
            {
                tr_share(0x5, (float)tr_get_jn(k));
                tr_share(0x4, (float)(tr_base + tr_get_jk(k)));
            }
        }
        k = k + 1;
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

void tr_share(int k, float v)
{
    WorkModule(0, v, 0x0f000340 + 0x8 * tr_slot + k);
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
    if ((d1 >= 0.0f && d2 < 0.0f || d1 < 0.0f && d2 >= 0.0f) && (d3 >= 0.0f && d4 < 0.0f || d3 < 0.0f && d4 >= 0.0f))
    {
        return 0x1;
    }
    return 0;
}

// the newest piece (tr_sx, tr_sy) - (x, y), numbers num - 1 - num, against this stretch's own pieces still drawn (in
// its own trail, not the ones next to it): one crossed, m its start's number, reported in shared 4 as -m
// every piece tested is taken 3.0f longer at both ends (test 131, the user's clip: a Blade Dash started where the last
// one ended, the two lines meeting end to end, never crossing, so the triangle they made with a third wasn't found);
// its own trail's pieces as they are, and only those that can close a loop (3 points between: test 132). Test 135:
// plain ifs and its own scratch (test 132's `same && tr_cross(..) || same == 0 && tr_cross(..)` and the parameters
// reused as scratch: Octaslash's own crossings, the only users of the first half, never made a shape)
void tr_test(float x, float y, int num)
{
    int k;
    int same;
    int hit;
    float ax;
    float ay;
    float bx;
    float by;
    float cx;
    float cy;
    float dx;
    float dy;
    float ex;
    float ey;
    float l;
    same = 0;
    if (tr_base / 0x400 == num / 0x400)
    {
        same = 0x1;
    }
    ax = tr_sx;
    ay = tr_sy;
    bx = x;
    by = y;
    if (same == 0)
    {
        l = MathF(0, (bx - ax) * (bx - ax) + (by - ay) * (by - ay));
        if (l > 0.01f)
        {
            l = 3.0f / l;
            ex = (bx - ax) * l;
            ey = (by - ay) * l;
            ax = ax - ex;
            ay = ay - ey;
            bx = bx + ex;
            by = by + ey;
        }
    }
    k = 0;
    while (k < tr_n - 1)
    {
        hit = 0;
        if (tr_has(tr_gone, k) == 0)
        {
            cx = tr_get_x(k);
            cy = tr_get_y(k);
            dx = tr_get_x(k + 1);
            dy = tr_get_y(k + 1);
            if (same)
            {
                if (tr_base + k <= num - 4)
                {
                    hit = tr_cross(ax, ay, bx, by, cx, cy, dx, dy);
                }
            }
            else
            {
                l = MathF(0, (dx - cx) * (dx - cx) + (dy - cy) * (dy - cy));
                if (l > 0.01f)
                {
                    l = 3.0f / l;
                    ex = (dx - cx) * l;
                    ey = (dy - cy) * l;
                    cx = cx - ex;
                    cy = cy - ey;
                    dx = dx + ex;
                    dy = dy + ey;
                }
                hit = tr_cross(ax, ay, bx, by, cx, cy, dx, dy);
            }
        }
        if (hit)
        {
            if (tr_shared(0x4) > -1000.0f || same)
            {
                tr_share(0x4, -(float)(tr_base + k));
            }
            if (same == 0)
            {
                tr_junction(k, num - 1);
            }
        }
        k = k + 1;
    }
}

// 1 if point k is counted here (a stretch's first point is the one before's last, counted there; a trail's first, here)
int tr_counts(int k)
{
    if (k > 0 || tr_base - (tr_base / 0x400) * 0x400 == 0)
    {
        return 0x1;
    }
    return 0;
}

// sin by its series (no sin in MSC; edge.c edge_tr_sin the same), x folded into -pi/2 .. pi/2
float tr_sin(float x)
{
    float x2;
    if (x > 1.5707963f)
    {
        x = 3.1415927f - x;
    }
    if (x < -1.5707963f)
    {
        x = -3.1415927f - x;
    }
    x2 = x * x;
    return x * (1.0f - x2 / 6.0f * (1.0f - x2 / 20.0f * (1.0f - x2 / 42.0f)));
}

// EXTENT (-(4000 + t) - 0.5; 4200 + t: of minus): the marked points' furthest along the axis at t x 180 / 128 degrees
// (into 5) and across it (into 4), the larger kept
void tr_extent(int c)
{
    float sg;
    float co;
    float si;
    float u;
    float w;
    int k;
    sg = 1.0f;
    if (c >= 200)
    {
        c = c - 200;
        sg = -1.0f;
    }
    u = (float)c * 0.0245437f;
    co = tr_sin(1.5707963f - u);
    si = tr_sin(u);
    k = 0;
    while (k < tr_n)
    {
        if (tr_has(tr_mark, k))
        {
            u = sg * (tr_get_x(k) * co + tr_get_y(k) * si);
            w = sg * (tr_get_y(k) * co - tr_get_x(k) * si);
            if (u > tr_shared(0x5))
            {
                tr_share(0x5, u);
            }
            if (w > tr_shared(0x4))
            {
                tr_share(0x4, w);
            }
        }
        k = k + 1;
    }
}

// a step of a shape asked (shared 6 = v): mark, a sum, or the commit
void tr_answer(float v)
{
    int code;
    int st;
    int cnt;
    int k;
    float a;
    float b;
    float x;
    float y;
    if (v > 0.0f)
    {
        code = (int)v;
        st = code / 0x200;
        cnt = code - st * 0x200;
        k = 0;
        while (k < tr_n)
        {
            if (tr_base + k >= st && tr_base + k < st + cnt)
            {
                tr_mark = tr_mark | tr_bit(k);
            }
            k = k + 1;
        }
        return;
    }
    if (v == -1005.5f)
    {
        tr_mark = 0;
        return;
    }
    if (v == -1004.5f)
    {
        if (tr_mark != 0)
        {
            tr_unpack(tr_shared(0x5));
            tr_cx = tr_px;
            tr_cy = tr_py;
            tr_fill = 0;
            k = 0;
            while (k < tr_n - 1)
            {
                if (tr_has(tr_mark, k) || tr_has(tr_mark, k + 1))
                {
                    if (tr_has(tr_gone, k) == 0)
                    {
                        tr_fill = tr_fill | tr_bit(k);
                    }
                }
                k = k + 1;
            }
            tr_ft = 0;
        }
        // every line goes (test 128): all its pieces, the one from its newest point on too (a trail still being laid
        // starts again from its next point)
        tr_gone = tr_bit(tr_n) - 1;
        tr_mark = 0;
        return;
    }
    a = 0.0f;
    b = 0.0f;
    k = 0;
    while (k < tr_n)
    {
        if (tr_has(tr_mark, k) && tr_counts(k))
        {
            x = tr_get_x(k);
            y = tr_get_y(k);
            if (v == -1001.5f)
            {
                a = a + x;
                b = b + y;
            }
            if (v == -1002.5f)
            {
                a = a + x * x;
                b = b + y * y;
            }
            if (v == -1003.5f)
            {
                a = a + x * y;
            }
        }
        k = k + 1;
    }
    tr_share(0x5, tr_shared(0x5) + a);
    tr_share(0x4, tr_shared(0x4) + b);
}

// every frame: a shape's step answered; a new point tested against its pieces, and taken if it's its trail's next
void tr_take()
{
    float v;
    int num;
    if (tr_slot < 0)
    {
        return;
    }
    v = tr_shared(0x6);
    if (v == -1.0f || v == -2.0f)
    {
        if (tr_over_t == 0 && v == -2.0f)
        {
            tr_vanish = 0x1;
        }
        tr_over_t = 0x1;
        return;
    }
    if (v < -1000.0f || v - (float)((int)v) > 0.25f)
    {
        if (v <= -1001.0f && v >= -1006.0f || v > 524288.0f)
        {
            tr_answer(v);
        }
        if (v <= -4000.0f && v >= -4328.0f)
        {
            tr_extent((int)(-v) - 4000);
        }
        if (v <= -3000.0f && v >= -3256.0f)
        {
            num = (int)(-v) - 3000;
            tr_junctions(num / 0x10, num - (num / 0x10) * 0x10);
        }
        return;
    }
    num = (int)v;
    if (num < 0x400 || num == tr_seen)
    {
        return;                 // not a trail's (the snake sword's runs share these), or seen
    }
    // a new Blade Dash trail 6 or more after this one's: this one goes
    if (num / 0x400 <= 0xe && tr_base / 0x400 <= 0xe && num / 0x400 != tr_base / 0x400
        && (num / 0x400 - tr_base / 0x400 + 0xe) - ((num / 0x400 - tr_base / 0x400 + 0xe) / 0xe) * 0xe >= 6)
    {
        tr_vanish = 0x1;
        tr_over_t = 0x1;
        tr_gone = tr_bit(tr_points()) - 1;
    }
    tr_unpack(tr_shared(0x5));
    if (num == tr_seen + 1)
    {
        tr_test(tr_px, tr_py, num);
    }
    if (tr_over_t == 0 && num == tr_base + tr_n && tr_n < tr_points())
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

// the fill's size now (0 - 1): none before 12, grown over 8 frames, held to 40, shrunk to 50
float tr_grow()
{
    if (tr_ft < 12)
    {
        return 0.0f;
    }
    if (tr_ft < 12 + 8)
    {
        return (float)(tr_ft - 12) / (float)8;
    }
    if (tr_ft < 40)
    {
        return 1.0f;
    }
    if (tr_ft < 50)
    {
        return (float)(50 - tr_ft) / (float)(50 - 40);
    }
    return 0.0f;
}

void tr_joint(int bone, float x, float y)
{
    ModelModule(0x7, 0x7d0 + bone, 0, y - tr_oy, (x - tr_ox) * tr_lr);
}

// the joints: the line's pieces still drawn between their points (gone / not yet: both ends on its start), the fill's
// wedge points from the middle out to their points by tr_grow()
void tr_pose()
{
    int k;
    int j;
    float t;
    float cx;
    float cy;
    PostureModule(0x2714, tr_ox, tr_oy, PostureModuleF(0x3));
    k = 0;
    while (k < tr_points() - 1)
    {
        j = k;
        if (j > tr_n - 1)
        {
            j = tr_n - 1;
        }
        tr_joint(19 + 2 * k, tr_get_x(j), tr_get_y(j));
        if (k < tr_n - 1 && tr_has(tr_gone, k) == 0)
        {
            j = k + 1;
        }
        tr_joint(19 + 1 + 2 * k, tr_get_x(j), tr_get_y(j));
        k = k + 1;
    }
    t = 0.0f;
    cx = tr_ox;
    cy = tr_oy;
    if (tr_ft >= 0)
    {
        t = tr_grow() * 1.30f;
        cx = tr_cx;
        cy = tr_cy;
    }
    tr_joint(2, cx, cy);
    k = 0;
    while (k < tr_points())
    {
        if (k < tr_n && t > 0.0f && (tr_has(tr_fill, k) || k > 0 && tr_has(tr_fill, k - 1)))
        {
            tr_joint(3 + k, cx + (tr_get_x(k) - cx) * t, cy + (tr_get_y(k) - cy) * t);
        }
        else
        {
            tr_joint(3 + k, cx, cy);
        }
        k = k + 1;
    }
}

int tr_over()
{
    tr_life -= 1;
    if (tr_ft >= 0)
    {
        tr_ft = tr_ft + 1;
        if (tr_ft >= 50)
        {
            tr_ft = -1;
            tr_fill = 0;
        }
    }
    if (tr_life <= 0 || tr_slot < 0 || tr_vanish && tr_ft < 0
        || tr_over_t && tr_ft < 0 && tr_n > 1 && (tr_gone & (tr_bit(tr_n - 1) - 1)) == tr_bit(tr_n - 1) - 1)
    {
        BattleObject(0x9);      // its time's up, or all its pieces are gone and its fill is over
        return 0x1;
    }
    return 0;
}

void func_46()
{
    int k;
    tr_slot = tr_find_owner();
    tr_life = 360;
    tr_n = 0;
    tr_over_t = 0;
    tr_mark = 0;
    tr_gone = 0;
    tr_fill = 0;
    tr_ft = -1;
    tr_vanish = 0;
    tr_lr = PostureModuleF(0);
    if (tr_lr == 0.0f)
    {
        tr_lr = 1.0f;
    }
    k = 0;
    while (k < 4)
    {
        tr_set_j(k, -1, 0);
        k = k + 1;
    }
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
    tr_cx = tr_ox;
    tr_cy = tr_oy;
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
