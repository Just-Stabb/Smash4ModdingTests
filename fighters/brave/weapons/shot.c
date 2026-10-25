// Hero's flying spell articles: compiled after thunder_base.c and before flash.c / explosion.c / deathball.c /
// sleep.c (their shot_config(): speeds, lives, what a hit does (sh_hit), its end (sh_end), each frame's own
// part (sh_tick: 1 holds it there)), as tools/brave_build.py does.

// ---- Command Selection's projectiles (copies of Robin's thunder, fighters/brave/README.md): Sizz / Sizzle
// (flash, article 10), Bang / Kaboom (explosion, 11), Whack / Thwack (deathball, 12), Snooze (sleep, 14).
// The owner's custom N slot (int 0x10000048, which the game copies into this weapon's 0x10000005) = level
// (0 / 1) + 4 x his player slot. Status 0 flies straight ahead at sh_speed for sh_life frames playing motion
// `level` (Ultimate's scripts: its hitboxes and effects), then sh_end(); status 1 (a hit: extra_kinds.json
// "on_hit": 1) runs sh_hit(), whose sh_burst(motion, frames) stops it there, plays that motion for those
// frames and removes it, or which goes on flying. Weapons are pooled: status 0 resets everything.
int sh_level;
int sh_owner;
int sh_frame;
int sh_total;
int sh_phase;
int sh_burst_frames;
int sh_hits;
float sh_speed;
int sh_life;
// shot_config()
float sh_speed_s;
float sh_speed_l;
int sh_life_s;
int sh_life_l;

int sh_pre()
{
    StatusModule(0x5, 0x2, 0, 0x5, 0, 0, 0, 0, 0, 0);
    return 0;
}

void sh_move(float speed)
{
    KineticModule(0x11, 0, speed * PostureModuleF(0), 0);
    KineticModule(0xf, 0, 0, 0);
    KineticModule(0x15, 0, -1.0f, -1.0f);
}

void sh_remove()
{
    BattleObject(0x9);
}

// stopped where it is: `motion` for `frames`, then removed (once)
void sh_burst(int motion, int frames)
{
    if (sh_phase != 0)
    {
        return;
    }
    sh_phase = 0x1;
    sh_frame = 0;
    sh_burst_frames = frames;
    AttackModule(0x2719);
    func_24(motion, 0, 1.0f);
}

void sh_loop()
{
    sh_total += 1;
    if (sh_total > 0x12c)
    {
        sh_remove();    // a safety net
        return;
    }
    sh_frame += 1;
    if (sh_phase != 0)
    {
        sh_move(0);
        if (sh_frame >= sh_burst_frames)
        {
            sh_remove();
        }
        return;
    }
    if (sh_tick())
    {
        return;         // the article's own part this frame (deathball.c: a KO) holds it
    }
    if (sh_frame >= sh_life || sh_frame > 0x1 && GroundModule(0x2722))
    {
        sh_end();
        if (sh_phase == 0)
        {
            sh_remove();
        }
        return;
    }
    sh_move(sh_speed);
}

void sh_main()
{
    int c;
    if (global4 == 0)
    {
        sh_phase = 0;
        sh_total = 0;
        sh_hits = 0;
    }
    c = WorkModule(0x6, 0x10000005);
    if (c < 0)
    {
        c = 0;
    }
    sh_owner = c / 0x4;
    sh_level = c - sh_owner * 0x4;
    if (sh_level > 0x1)
    {
        sh_level = 0x1;
    }
    sh_frame = 0;
    sh_speed = sh_speed_s;
    sh_life = sh_life_s;
    if (sh_level == 0x1)
    {
        sh_speed = sh_speed_l;
        sh_life = sh_life_l;
    }
    func_24(sh_level, 0, 1.0f);
    sh_move(sh_speed);
    callFunc3(sh_loop);
}

// a hit: the article's own reaction, then on
void sh_hit_main()
{
    sh_hit();
    if (sh_phase == 0)
    {
        sh_move(sh_speed);
    }
    callFunc3(sh_loop);
}

void sh_setup()
{
    global7 = 0x2;
    sh_phase = 0;
    sh_total = 0;
    sh_hits = 0;
    sv_set_mem(0x1, 0, 0, sh_pre);
    sv_set_mem(0x1, 0, 0x1, sh_pre);
    sv_set_mem(0x1, 0x1, 0, sh_main);
    sv_set_mem(0x1, 0x1, 0x1, sh_hit_main);
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
    shot_config();
    sh_setup();
    sys_0(0x2, func_3);
    sys_0(0x3, func_7);
    sys_0(0x4, func_12);
    set_main(func_1);
}
