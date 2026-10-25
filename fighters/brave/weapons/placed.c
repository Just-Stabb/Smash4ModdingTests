// Hero's placed articles: compiled after thunder_base.c and before spark.c / tornado.c / crash.c (their
// placed_config(): the wait and the levels; placed_life(level)), as tools/brave_build.py does.

// ---- Articles put on a fighter (copies of Robin's thunder): spark (Zap's lightning on the fighter the bolt
// hit, his article 7), tornado (Woosh's whirlwind where he starts, article 8) and crash (Magic Burst /
// Kamikazee on him, article 12). The owner's custom N slot (int 0x10000048, which the game copies into this
// weapon's 0x10000005) = level + pl_levels (4; crash's 8) x a player slot (0-7):
// the article moves to that slot's fighter (the position variables 0x0F000020 + 4 x slot, X / Y / Z /
// facing: tools/position_vars_cave.py), waits pl_wait frames on an empty motion, plays motion `level` (its
// hitboxes and effects: Ultimate's brave_spark / brave_tornado scripts) for its life and is removed. A hit
// asks for status 1 (extra_kinds.json "on_hit": 1, instead of thunder's removal) unless the article is in
// it already, and a status change clears its hitboxes: Swoosh / Kaswoosh (re-hitting every 7 frames) hit
// once. So status 0 only resets (weapons are pooled) and goes to status 1 at once, which places it and
// plays its motion; a hit then changes nothing.
int pl_level;
int pl_slot;
int pl_frame;
int pl_total;
int pl_wait;
int pl_life;
int pl_levels;
int pl_started;

// thunder's own (func_47)
int pl_pre()
{
    StatusModule(0x5, 0x2, 0, 0x5, 0, 0, 0, 0, 0, 0);
    return 0;
}

void pl_still()
{
    KineticModule(0x11, 0, 0, 0);
    KineticModule(0xf, 0, 0, 0);
    KineticModule(0x15, 0, -1.0f, -1.0f);
}

void pl_place()
{
    float x;
    float y;
    float z;
    if (pl_slot < 0 || pl_slot > 0x7 || WorkModuleF(0, 0x0f000023 + 0x4 * pl_slot) == 0)
    {
        return;         // no such fighter: where the game put it
    }
    x = WorkModuleF(0, 0x0f000020 + 0x4 * pl_slot);
    y = WorkModuleF(0, 0x0f000021 + 0x4 * pl_slot);
    z = WorkModuleF(0, 0x0f000022 + 0x4 * pl_slot);
    PostureModule(0x3, x, y, z);
}

void pl_loop()
{
    pl_total += 1;
    if (pl_total > 0xc8)
    {
        BattleObject(0x9);  // a safety net
        return;
    }
    pl_still();
    pl_frame += 1;
    if (pl_frame == pl_wait)
    {
        func_24(pl_level, 0, 1.0f);
    }
    if (pl_frame >= pl_wait + pl_life)
    {
        BattleObject(0x9);
        return;
    }
}

void pl_main()
{
    pl_started = 0;
    StatusModule(0x3, 0x1, 0);
}

// status 1: the article's set-up and life (once), then on as before
void pl_hit_main()
{
    int c;
    if (pl_started)
    {
        callFunc3(pl_loop);
        return;
    }
    pl_started = 0x1;
    c = WorkModule(0x6, 0x10000005);
    if (c < 0)
    {
        c = 0;
    }
    pl_slot = c / pl_levels;
    pl_level = c - pl_slot * pl_levels;
    pl_life = placed_life(pl_level);
    pl_frame = 0;
    pl_total = 0;
    pl_place();
    pl_still();
    if (pl_wait == 0)
    {
        func_24(pl_level, 0, 1.0f);
    }
    else
    {
        func_24(0x17, 0, 1.0f);     // an empty slot while it waits
    }
    callFunc3(pl_loop);
}

void pl_setup()
{
    global7 = 0x2;
    sv_set_mem(0x1, 0, 0, pl_pre);
    sv_set_mem(0x1, 0, 0x1, pl_pre);
    sv_set_mem(0x1, 0x1, 0, pl_main);
    sv_set_mem(0x1, 0x1, 0x1, pl_hit_main);
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
    pl_levels = 0x4;
    placed_config();
    pl_setup();
    sys_0(0x2, func_3);
    sys_0(0x3, func_7);
    sys_0(0x4, func_12);
    set_main(func_1);
}
