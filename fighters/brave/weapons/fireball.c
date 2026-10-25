// Hero's fireball article: compiled after thunder_base.c (Robin's thunder MSC up to func_40, decompiled), as
// tools/brave_build.py does.

// ---- Hero's Frizz / Frizzle / Kafrizz (weapon kind 0x190, a copy of Robin's thunder; his article 6). The
// scaffolding (thunder_base.c) is thunder's MSC; its statuses are replaced (fighters/brave/README.md). Level 0 / 1 / 2
// (S / M / L): Hero's custom N slot (int 0x10000048) while he generates it, which the game copies into the
// new weapon's 0x10000005. Motions: 0 / 1 / 2 the flight (Ultimate's brave_fireball SpecialN1 / N2 / N3:
// its hitbox and bullet effect), 3 / 4 / 5 the burst (BurstS / M / L: the hit effect; Kafrizz's explosion
// hitboxes). Status 0 flies (Ultimate's param_fireball: Frizz 1.6, slowing from frame 30 (deccel_start_frame_s),
// Frizzle 2.4, Kafrizz 0.3 growing by 0.1 a frame up to 4.0; life 56 / 46 / 58), status 1 bursts where it is:
// at its life's end, on a wall / the floor, or when it hits (extra_kinds.json "on_hit": 1); then it's removed
// (Ultimate's bursts end by a notify at frame 3; Kafrizz's last hit is at 19, burst_frame_l 21).
// Weapons are pooled: the state is reset when status 0 is entered.
int fb_level;
int fb_frame;
int fb_life;
int fb_phase;
int fb_total;
float fb_speed;

// thunder's own (func_47)
int fb_pre()
{
    StatusModule(0x5, 0x2, 0, 0x5, 0, 0, 0, 0, 0, 0);
    return 0;
}

void fb_status(int status)
{
    StatusModule(0x3, status, 0);
}

void fb_move(float speed)
{
    KineticModule(0x11, 0, speed * PostureModuleF(0), 0);
    KineticModule(0xf, 0, 0, 0);
    KineticModule(0x15, 0, -1.0f, -1.0f);
}

int fb_burst_frames()
{
    if (fb_level == 0x2)
    {
        return 0x16;
    }
    return 0x4;
}

// a safety net: removed 200 frames after it was made whatever happened
int fb_expired()
{
    fb_total += 1;
    if (fb_total > 0xc8)
    {
        BattleObject(0x9);
        return 1;
    }
    return 0;
}

void fb_fly_loop()
{
    if (fb_expired())
    {
        return;
    }
    fb_frame += 1;
    if (fb_frame >= fb_life || fb_frame > 0x1 && GroundModule(0x2722))
    {
        fb_status(0x1);
        return;
    }
    if (fb_level == 0x2)
    {
        fb_speed = fb_speed + 0.1f;
        if (fb_speed > 4.0f)
        {
            fb_speed = 4.0f;
        }
    }
    else if (fb_level == 0 && fb_frame >= 0x1e)
    {
        fb_speed = fb_speed - 0.04f;
        if (fb_speed < 0.4f)
        {
            fb_speed = 0.4f;
        }
    }
    fb_move(fb_speed);
}

void fb_fly_main()
{
    if (global4 == 0)
    {
        fb_phase = 0;
        fb_total = 0;
    }
    if (fb_phase != 0)
    {
        fb_status(0x1);
        return;
    }
    fb_level = WorkModule(0x6, 0x10000005);
    if (fb_level < 0 || fb_level > 0x2)
    {
        fb_level = 0;
    }
    fb_frame = 0;
    if (fb_level == 0x1)
    {
        fb_speed = 2.4f;
        fb_life = 0x2e;
    }
    else if (fb_level == 0x2)
    {
        fb_speed = 0.3f;
        fb_life = 0x3a;
    }
    else
    {
        fb_speed = 1.6f;
        fb_life = 0x38;
    }
    func_24(fb_level, 0, 1.0f);
    fb_move(fb_speed);
    callFunc3(fb_fly_loop);
}

void fb_burst_loop()
{
    if (fb_expired())
    {
        return;
    }
    fb_move(0);
    fb_frame += 1;
    if (fb_frame >= fb_burst_frames())
    {
        BattleObject(0x9);
        return;
    }
}

void fb_burst_main()
{
    if (fb_phase == 0)
    {
        fb_phase = 0x1;
        fb_frame = 0;
        AttackModule(0x2719);
        func_24(0x3 + fb_level, 0, 1.0f);
    }
    fb_move(0);
    callFunc3(fb_burst_loop);
}

void fb_setup()
{
    global7 = 0x2;
    fb_phase = 0;
    fb_total = 0;
    sv_set_mem(0x1, 0, 0, fb_pre);
    sv_set_mem(0x1, 0, 0x1, fb_pre);
    sv_set_mem(0x1, 0x1, 0, fb_fly_main);
    sv_set_mem(0x1, 0x1, 0x1, fb_burst_main);
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
    fb_setup();
    sys_0(0x2, func_3);
    sys_0(0x3, func_7);
    sys_0(0x4, func_12);
    set_main(func_1);
}
