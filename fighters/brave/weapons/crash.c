// Magic Burst / Kamikazee's blast (weapon kind 0x196, article 12; placed.c, 8 levels): on Hero (fix v4: his slot
// from his marker, weapons/placed.c pl_marked_hero; the level, 0-3 in the custom number, the MP tier from the marker). Motions: 0 Magic Burst with 100 MP spent (Ultimate's brave_crash Crash1: its
// rings of hits to frame 93), 1 Kamikazee's (Crash2: the explosion at frame 10), 2 CrashEnd1 (not used), 3-6
// Magic Burst with 20 / 40 / 60 / 80 MP: Crash1 with every hit's damage x 0.2 / 0.4 / 0.6 / 0.8
// (tools/brave_build.py CRASH_TIERS; brave.c picks the tier from the MP spent, rounded up).
void placed_config()
{
    pl_mark_kind = 0x2;  // fix v4: Hero's marker carries the level (the MP tier / Kamikazee)
    pl_wait = 0;
    pl_levels = 0x8;
}

int placed_life(int level)
{
    if (level == 0x1)
    {
        return 0x28;
    }
    return 0x5f;
}

void placed_tick(int level, int frame)
{
}
