// Hero's flying spell articles: compiled after thunder_base.c and before flash.c / explosion.c / deathball.c /
// sleep.c (their shot_config(): speeds, lives, what a hit does (sh_hit), its end (sh_end), each frame's own
// part (sh_tick: 1 holds it there)), as tools/brave_build.py does.

// ---- Command Selection's projectiles (copies of Robin's thunder, fighters/brave/README.md): Sizz / Sizzle
// (flash, article 9), Bang / Kaboom (explosion, 10), Whack / Thwack (deathball, 11), Snooze (sleep, 13).
// The owner's custom N slot (int 0x10000048, which the game copies into this weapon's 0x10000005) = level
// (0 / 1); the caster is found here (sh_find_owner). (level + 4 x (the caster's player slot + 1) is still read, but a
// custom number past 3 draws the projectile invisible: Kirby's fix v2, port_check W10.) Status 0 flies straight ahead at sh_speed for sh_life frames playing motion
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
    if (sh_total > sh_life + 0x12c)
    {
        sh_remove();    // a safety net (its life and 300 frames)
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

// Hero's player slot (0 - 7; 8 none): the fighter of his kind (0x45, the kind variable 0x0F0000BD + 8 x slot) nearest
// to the article, which his spawner makes at his hand. The custom number holds the level only (0 / 1): it also picks
// the article's native param block (4 entries, custom 0-3: tools/weapon_expand.py CUSTOM_CLAMP), and level + 4 x slot
// read past it for P2 and later, whose Whack / Thwack never appeared (multi-instance bugs v1)
// the live fighter nearest to the article (its kind 0x45 or Kirby's 8 only when kind is 1); 8 none
int sh_nearest(int kind)
{
    int s;
    int best;
    float d;
    float bd;
    float dx;
    float dy;
    best = 0x8;
    bd = 0;
    s = 0;
    while (s < 0x8)
    {
        if (WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0)
        {
            // a Hero, or a Kirby (his Hero copy casts these from the stone: fighters/kirby/specials.md "Hero copy:
            // Stone = Command Selection"); the nearest of them to the article, which is made at the caster's hand
            if (kind == 0 || (int)WorkModuleF(0, 0x0f0000bd + 0x8 * s) == 0x45
                || (int)WorkModuleF(0, 0x0f0000bd + 0x8 * s) == 0x8)
            {
                dx = WorkModuleF(0, 0x0f000020 + 0x4 * s) - PostureModuleF(0x1);
                dy = WorkModuleF(0, 0x0f000021 + 0x4 * s) - PostureModuleF(0x2);
                d = dx * dx + dy * dy;
                if (best == 0x8 || d < bd)
                {
                    best = s;
                    bd = d;
                }
            }
        }
        s += 1;
    }
    return best;
}

// Kirby's Hero copy (fix v3): a Kirby in his stone (statuses 0x155 / 0x175 / 0x176: the Stone casts these), within 30
// of the article (made at his hand), nearest first; 8 none. Before the Hero-or-Kirby search, which can take an
// opponent Hero nearer to the article for the caster (Whack then aims away from him and never rolls on him).
int sh_stone_kirby()
{
    int s;
    int best;
    float st;
    float d;
    float bd;
    float dx;
    float dy;
    best = 0x8;
    bd = 900.0f;
    s = 0;
    while (s < 0x8)
    {
        st = WorkModuleF(0, 0x0f0000ba + 0x8 * s);
        if (WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0 && (int)WorkModuleF(0, 0x0f0000bd + 0x8 * s) == 0x8
            && (st == 341.0f || st == 373.0f || st == 374.0f))
        {
            dx = WorkModuleF(0, 0x0f000020 + 0x4 * s) - PostureModuleF(0x1);
            dy = WorkModuleF(0, 0x0f000021 + 0x4 * s) - PostureModuleF(0x2);
            d = dx * dx + dy * dy;
            if (d < bd)
            {
                best = s;
                bd = d;
            }
        }
        s += 1;
    }
    return best;
}

int sh_find_owner()
{
    int s;
    s = sh_stone_kirby();
    if (s != 0x8)
    {
        return s;
    }
    s = sh_nearest(0x1);
    if (s == 0x8)
    {
        s = sh_nearest(0);      // none of his kind found: the fighter whose hand it was made at
    }
    return s;
}

// Kirby's Hero copy (fix v4; the user: "Kirby's Stone spells hit other opponents; they fail only against Hero"): the
// spawner (Robin's thunder's, 0x02F643A4) makes the projectile at the caster's hand joint in 3D (0x020073FC, the joint's
// world position: joint 0x10 LHandN for a Kirby), and the stone's pose holds that hand 5.0 off his plane (Kirby's
// SpecialLw / SpecialAirLw end poses: LHandN at model (-5.0, 10.7, 4.0), the first axis the game's depth; Frizz's
// cast pose 0.9). Smash 4's hit test is 3D: Sizz (radius 3) 5 deep reaches only hurtboxes wider than 2, and Hero's
// are Ultimate's (hip / waist 2.0, head 1.55, arms 0.95: param/vl.prc hit_data) where vanilla bodies are 2.4 - 5.0
// (Robin 2.4, Link 2.6, Mario 3.1, Kirby 5.0): it passed in front of Hero only. Cast from the stone, the projectile is
// put on its caster's plane (his position variable Z) at the start; Hero's own (made at his hand, near his plane)
// unchanged.
void sh_plane(int s)
{
    PostureModule(0x3, PostureModuleF(0x1), PostureModuleF(0x2), WorkModuleF(0, 0x0f000022 + 0x4 * s));
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
    if (sh_owner == 0)
    {
        sh_owner = sh_find_owner();    // the level alone in the custom number (Hero's own and Kirby's Hero copy's)
        if (sh_owner < 0x8 && sh_owner == sh_stone_kirby())
        {
            sh_plane(sh_owner);        // fix v4: cast from Kirby's stone: on his plane
        }
    }
    else
    {
        sh_owner = sh_owner - 0x1;     // level + 4 x (the caster's slot + 1): nobody sends it since fix v3 (Kirby's
    }                                  // fix v2 did: a custom number past 3 left the projectile invisible)
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
