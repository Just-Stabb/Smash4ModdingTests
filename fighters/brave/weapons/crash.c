// Magic Burst / Kamikazee's blast (weapon kind 0x196, article 13; placed.c): on Hero (his player slot in the
// custom number), Magic Burst's (level 0, Crash1: its rings of hits to frame 93) or Kamikazee's (level 1,
// Crash2: the explosion at frame 10). Motions 0 / 1: Ultimate's brave_crash Crash1 / Crash2.
void placed_config()
{
    pl_wait = 0;
    pl_life_s = 0x5f;
    pl_life_m = 0x28;
    pl_life_l = 0x28;
}
