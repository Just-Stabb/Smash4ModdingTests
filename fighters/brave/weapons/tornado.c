// Woosh's whirlwind (weapon kind 0x192, article 8; placed.c): where Hero is when he makes it, for 24 / 33 / 52
// frames (param_tornado life_*). Motions 0 / 1 / 2: Ultimate's brave_tornado SpecialHi1 / Hi2 / Hi3 (Woosh,
// Swoosh, Kaswoosh).
void placed_config()
{
    pl_wait = 0;
}

int placed_life(int level)
{
    if (level == 0x1)
    {
        return 0x21;
    }
    if (level == 0x2)
    {
        return 0x34;
    }
    return 0x18;
}

// Kaswoosh's launch (Ultimate's second hitboxes, `if life <= 2`): 2 frames before its end, motion slot 3
// (tools/brave_build.py specialhi3launch: its hitboxes at once)
void placed_tick(int level, int frame)
{
    if (level == 0x2 && frame == 0x32)
    {
        func_24(0x3, 0, 1.0f);
    }
}
