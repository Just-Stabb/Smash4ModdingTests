// Zap's lightning (weapon kind 0x191, article 7; placed.c): on the fighter the bolt hit, 3 frames after Hero
// sees the hit (param_special_s activate_wait_frame_*), 8 frames (param_spark life_*). Motions 0 / 1 / 2:
// Ultimate's brave_spark SpecialS1 / S2 / S32 (Zap, Zapple, Kazap).
void placed_config()
{
    pl_wait = 0x3;
}

int placed_life(int level)
{
    return 0x8;
}

void placed_tick(int level, int frame)
{
}
