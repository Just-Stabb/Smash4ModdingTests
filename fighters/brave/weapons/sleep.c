// Snooze's gust (weapon kind 0x197, article 14; shot.c): 1.3 a frame for 50 frames (Ultimate's param_sleep),
// on through what it hits (its hitboxes put them to sleep: Effect 9). Motion 0: Ultimate's brave_sleep Sleep.
void shot_config()
{
    sh_speed_s = 1.3f;
    sh_speed_l = 1.3f;
    sh_life_s = 0x32;
    sh_life_l = 0x32;
}

void sh_hit()
{
}

void sh_end()
{
}
