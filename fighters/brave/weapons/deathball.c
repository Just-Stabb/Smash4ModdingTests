// Whack / Thwack's curse (weapon kind 0x195, article 11; shot.c): Whack a ball at 1.3 a frame for 120 frames,
// Thwack a wide field that barely moves for 20 (Ultimate's param_deathball). Each fighter it touches is
// KO'd outright with a chance of (1 + 200 x (t - 20) / 280 + 20 x u / 300) % (t its damage, 20-300; u
// Hero's, at most 300: SmashWiki's Whack formula), rolled once a fighter a cast: KO'd on the spot through
// that player slot's KO variable (docs/position-variables.md: 0x0F000100 + 0x20 x (3 + slot) + 0x1F, flag
// 0x20000043 on it, as Kamikazee's own KO). Until fix 57 a Death hitbox (effect 0x10, Smash Run's Orne) did
// it, whose hit effect crashed the game (a vertex buffer out of range). The fighters near it are found
// through the position variables (slot X / Y, DAMAGE), Hero's own slot (the custom number's sh_owner) left
// out. Motions 0 / 1: Ultimate's brave_deathball DeathBall1 / DeathBall2.
// Fix 79 (the user's): Whack lives 620 frames and homes hard (dbl_steer) on the opponent nearest to it on its
// first frame (that fighter for good); reflected (the game flips its facing: docs/native-notes.md
// "Reflection"; flipped again by Hero, back to the first target) it homes on Hero instead. Any hit (its
// hitbox connecting or meeting a shield: the on_hit status) removes it; a fighter shielding there isn't
// rolled for. Thwack is as it was.
void shot_config()
{
    sh_speed_s = 1.3f;
    sh_speed_l = 0.3f;
    sh_life_s = 0x26c;     // 620 (the user's; Ultimate's 120)
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
    if ((float)randi(0, 0x64) < p)
    {
        WorkModule(0, 1.0f, 0x0f00017f + 0x20 * s);     // slot s's KO
    }
}

// Whack's homing: speed 1.3 always (Ultimate's), the direction turned a quarter of the way to the target's
// middle (its Y + 10) each frame
int dbl_target;
float dbl_face0;
float dbl_vx;
float dbl_vy;

float dbl_sqrt(float v)
{
    float g;
    int i;
    if (v <= 0)
    {
        return 0;
    }
    g = v;
    if (g < 1.0f)
    {
        g = 1.0f;
    }
    i = 0;
    while (i < 0x8)
    {
        g = (g + v / g) * 0.5f;
        i += 1;
    }
    return g;
}

int dbl_exists(int s)
{
    if (s < 0 || s >= 0x8)
    {
        return 0;
    }
    return WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0;
}

// the opponent nearest to it (-1: none)
int dbl_nearest()
{
    int s;
    int best;
    float d;
    float bd;
    float dx;
    float dy;
    best = 0xffffffff;
    bd = 0;
    s = 0;
    while (s < 0x8)
    {
        if (s != sh_owner && dbl_exists(s))
        {
            dx = WorkModuleF(0, 0x0f000020 + 0x4 * s) - PostureModuleF(0x1);
            dy = WorkModuleF(0, 0x0f000021 + 0x4 * s) - PostureModuleF(0x2);
            d = dx * dx + dy * dy;
            if (best < 0 || d < bd)
            {
                best = s;
                bd = d;
            }
        }
        s += 1;
    }
    return best;
}

int dbl_reflected()
{
    return PostureModuleF(0) * dbl_face0 < 0;
}

void dbl_steer(int t)
{
    float dx;
    float dy;
    float d;
    if (!dbl_exists(t))
    {
        return;
    }
    dx = WorkModuleF(0, 0x0f000020 + 0x4 * t) - PostureModuleF(0x1);
    dy = WorkModuleF(0, 0x0f000021 + 0x4 * t) + 10.0f - PostureModuleF(0x2);
    d = dbl_sqrt(dx * dx + dy * dy);
    if (d < 0.01f)
    {
        return;
    }
    dbl_vx = dbl_vx + (dx / d * sh_speed - dbl_vx) * 0.25f;
    dbl_vy = dbl_vy + (dy / d * sh_speed - dbl_vy) * 0.25f;
    d = dbl_sqrt(dbl_vx * dbl_vx + dbl_vy * dbl_vy);
    if (d < 0.01f)
    {
        dbl_vx = dx;
        dbl_vy = dy;
        d = dbl_sqrt(dx * dx + dy * dy);
    }
    dbl_vx = dbl_vx / d * sh_speed;
    dbl_vy = dbl_vy / d * sh_speed;
}

// Whack's frames (Thwack: shot.c's own)
int sh_tick()
{
    int t;
    if (sh_level != 0)
    {
        return 0;
    }
    if (sh_frame == 0x1)
    {
        dbl_face0 = PostureModuleF(0);
        dbl_target = dbl_nearest();
        dbl_vx = sh_speed * dbl_face0;
        dbl_vy = 0;
    }
    if (sh_frame >= sh_life)
    {
        sh_remove();
        return 0x1;
    }
    t = dbl_target;
    if (dbl_reflected())
    {
        t = sh_owner;
    }
    dbl_steer(t);
    KineticModule(0x11, 0, dbl_vx, dbl_vy);
    KineticModule(0xf, 0, 0, 0);
    KineticModule(0x15, 0, -1.0f, -1.0f);
    return 0x1;
}

int dbl_shielding(int s)
{
    float st;
    st = WorkModuleF(0, 0x0f0000ba + 0x8 * s);      // slot s's status (docs/position-variables.md)
    return st >= 27.0f && st <= 30.0f;              // GuardOn / Guard / GuardOff / GuardDamage (0x1B-0x1E)
}

void sh_hit()
{
    int s;
    float x;
    float y;
    float dx;
    float dy;
    float r;
    int refl;
    x = PostureModuleF(0x1);
    y = PostureModuleF(0x2);
    r = 14.0f;
    refl = 0;
    if (sh_level == 0x1)
    {
        r = 30.0f;
    }
    else
    {
        refl = dbl_reflected();
    }
    s = 0;
    while (s < 0x8)
    {
        if ((s != sh_owner || refl) && dbl_exists(s) && (sh_hits / dbl_bit(s)) % 0x2 == 0)
        {
            dx = WorkModuleF(0, 0x0f000020 + 0x4 * s) - x;
            dy = y - WorkModuleF(0, 0x0f000021 + 0x4 * s);
            if (dx < r && dx > -r && dy < r + 20.0f && dy > -r)
            {
                sh_hits = sh_hits + dbl_bit(s);
                if (sh_level == 0x1 || !dbl_shielding(s))
                {
                    dbl_roll(s);
                }
            }
        }
        s += 1;
    }
    if (sh_level == 0)
    {
        // Whack: gone on a hit or a shield (shot.c's loop removes it next frame: a burst of 0 frames)
        sh_phase = 0x1;
        sh_frame = 0;
        sh_burst_frames = 0;
        AttackModule(0x2719);
    }
}

void sh_end()
{
}
