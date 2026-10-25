// Bang / Kaboom's bomb (weapon kind 0x194, article 10; shot.c): 2.2 / 3.7 a frame for 35 / 22 frames
// (Ultimate's param_explosion speed / life), then, or on a hit, it explodes where it is (Explode1 / 2: 32 /
// 45 frames). Motions 0 / 1: Ultimate's brave_explosion Move1 / Move2, 2 / 3: Explode1 / Explode2.
void shot_config()
{
    sh_speed_s = 2.2f;
    sh_speed_l = 3.7f;
    sh_life_s = 0x23;
    sh_life_l = 0x16;
}

void sh_explode()
{
    if (sh_level == 0x1)
    {
        sh_burst(0x3, 0x2d);
    }
    else
    {
        sh_burst(0x2, 0x20);
    }
}

void sh_hit()
{
    sh_explode();
}

void sh_end()
{
    sh_explode();
}

int sh_tick()
{
    return 0;
}
