// Whack / Thwack's curse (weapon kind 0x195, article 12; shot.c): Whack a ball at 1.3 a frame for 120 frames,
// Thwack a wide field that barely moves for 20 (Ultimate's param_deathball). Each fighter it touches is
// KO'd outright with a chance of (1 + 200 x (t - 20) / 280 + 20 x u / 300) % (t its damage, 20-300; u
// Hero's, at most 300: SmashWiki's Whack formula), rolled once a fighter a cast: the curse goes onto that
// fighter for DBL_KO_FRAMES frames playing motion 2 (tools/brave_build.py's deathballko: a Death hitbox,
// effect 0x10, which KOs on the spot as Smash Run's Orne does; its own hit group, unblockable, fighters
// only), then back where it was, on its way. The fighters near it are found through the position
// variables (docs/position-variables.md: slot X / Y, DAMAGE), Hero's own slot (the custom number's
// sh_owner) left out. Motions 0 / 1: Ultimate's brave_deathball DeathBall1 / DeathBall2.
int dbl_ko_slot;
int dbl_ko_t;
float dbl_x;
float dbl_y;
float dbl_z;

int dbl_ko_frames()
{
    return 0x3;
}

void shot_config()
{
    sh_speed_s = 1.3f;
    sh_speed_l = 0.3f;
    sh_life_s = 0x78;
    sh_life_l = 0x14;
}

int dbl_bit(int s)
{
    int b;
    int i;
    b = 0x1;
    i = 0;
    while (i < s)
    {
        b = b * 0x2;
        i += 1;
    }
    return b;
}

float dbl_clamp(float v, float lo, float hi)
{
    if (v < lo)
    {
        return lo;
    }
    if (v > hi)
    {
        return hi;
    }
    return v;
}

void dbl_roll(int s)
{
    float t;
    float u;
    float p;
    t = dbl_clamp(WorkModuleF(0, 0x0f000177 + 0x20 * s), 20.0f, 300.0f);
    u = 0;
    if (sh_owner < 0x8)
    {
        u = dbl_clamp(WorkModuleF(0, 0x0f000177 + 0x20 * sh_owner), 0, 300.0f);
    }
    p = 1.0f + 200.0f * (t - 20.0f) / 280.0f + 20.0f * u / 300.0f;
    if ((float)randi(0, 0x64) < p && dbl_ko_t == 0)
    {
        dbl_ko_slot = s;
        dbl_ko_t = dbl_ko_frames();
        dbl_x = PostureModuleF(0x1);
        dbl_y = PostureModuleF(0x2);
        dbl_z = PostureModuleF(0x3);
        func_24(0x2, 0, 1.0f);      // the Death hitbox
    }
}

// a KO under way: on the fighter, then back to where it was and on
int sh_tick()
{
    if (sh_frame <= 0x1)
    {
        dbl_ko_t = 0;   // a new cast (weapons are pooled)
    }
    if (dbl_ko_t == 0)
    {
        return 0;
    }
    dbl_ko_t -= 1;
    if (dbl_ko_t == 0)
    {
        PostureModule(0x3, dbl_x, dbl_y, dbl_z);
        func_24(sh_level, 0, 1.0f);
        return 0;
    }
    if (WorkModuleF(0, 0x0f000023 + 0x4 * dbl_ko_slot) != 0)
    {
        PostureModule(0x3, WorkModuleF(0, 0x0f000020 + 0x4 * dbl_ko_slot), WorkModuleF(0, 0x0f000021 + 0x4 * dbl_ko_slot),
            WorkModuleF(0, 0x0f000022 + 0x4 * dbl_ko_slot));
    }
    sh_move(0);
    return 0x1;
}

void sh_hit()
{
    int s;
    float x;
    float y;
    float dx;
    float dy;
    float r;
    x = PostureModuleF(0x1);
    y = PostureModuleF(0x2);
    r = 14.0f;
    if (sh_level == 0x1)
    {
        r = 30.0f;
    }
    s = 0;
    while (s < 0x8)
    {
        if (s != sh_owner && WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0 && (sh_hits / dbl_bit(s)) % 0x2 == 0)
        {
            dx = WorkModuleF(0, 0x0f000020 + 0x4 * s) - x;
            dy = y - WorkModuleF(0, 0x0f000021 + 0x4 * s);
            if (dx < r && dx > -r && dy < r + 20.0f && dy > -r)
            {
                sh_hits = sh_hits + dbl_bit(s);
                dbl_roll(s);
            }
        }
        s += 1;
    }
}

void sh_end()
{
}
