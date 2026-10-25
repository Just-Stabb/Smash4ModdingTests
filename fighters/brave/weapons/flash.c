// Sizz / Sizzle's flame (weapon kind 0x193, article 10; shot.c): 6 / 8 a frame for 14 / 12 frames (Ultimate's
// param_flash speed / life); a hit stops it in a pillar of fire (FlashHit1 / 2, pillar_life 25 frames).
// Motions 0 / 1: Ultimate's brave_flash Flash1 / Flash2, 2 / 3: FlashHit1 / FlashHit2.
void shot_config()
{
    sh_speed_s = 6.0f;
    sh_speed_l = 8.0f;
    sh_life_s = 0xe;
    sh_life_l = 0xc;
}

void sh_hit()
{
    sh_burst(0x2 + sh_level, 0x19);
}

void sh_end()
{
}
