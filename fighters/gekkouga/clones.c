
// ===================================================================
// Greninja's clones and smash charges (fighters/gekkouga/README.md "Clones v1" - "Clones v3")
//
// Down special: held, it charges (the Substitution stance, no counter); 300 frames held in all (kept between
// presses and stocks) make it ready, and the next down special starts the ABILITY (720 frames): two clones
// (articles 6 / 7, weapon kind 0x1A1, fighters/gekkouga/weapons/clone.c) left and right of him that play his
// motions and hit with his hitboxes, his name tag hidden; down special + left / right swaps him with that clone.
// A clone hit (his counter shape's capsules at the clones, tools/gekkouga_clone_cave.py) turns into a log.
// Then the BURNOUT (480 frames): no down special, grey, half speed (the Timer's slow, the executable).
// Smash attacks: the charge is kept, a release before full is no attack, a full charge releases on its own the
// next time, and smashes chain (each once) from the end of the last one's hitboxes.
//
// The executable reads VAR_20 (flags: 1 tag hidden, 2 burnout slow, 4 clones out) and writes VAR_21 (a clone
// hit: 10000 + the hitting object's X - his X) and VAR_22 (v2: a clone's hit landed: his hitlag). His clones read his
// VAR_24 - VAR_31 (SLOTn_SHARED_0 - 7), v2: 24 / 25 the left clone's X / Y, 26 / 27 the right one's, 28 his motion's
// kind x 1024 + frame (v3), 29 its rate (0 in hitlag), 30 the clones' heartbeat (v3: they write it), 31 = 4747000 +
// flags (1 / 2 alive, 4 / 8 being made, 16 / 32 falling). v3: the clones' own hurtboxes (VAR_21 = 20000 + the hit
// clone's id), walls / ceilings / slopes for their places, his hitlag set by the executable at the hit.
// v2: the clones' places are his MSC's (their own fall with his gravity, his GroundModule's line test for the floor:
// gk_physics); a clone's landed hit gives him its hitlag (gk_clone_hitlag); the clones play his hand / face parts.
// ===================================================================
int gk_lw_charge;      // the down special's charge: frames held (0 - gk_lw_full()); kept between presses / stocks
int gk_ability;        // the ability: frames left
int gk_burnout;        // the burnout: frames left
int gk_alive;          // clones out: 1 the left-spawned one (article 6), 2 the right-spawned one (article 7)
float gk_off_l;        // the left-spawned clone's X offset from him (world)
float gk_off_r;        // the right-spawned clone's
int gk_seq;            // frames since the ability started (the clones are made at 0 and 3)
int gk_swap_cd;        // frames before another swap
int gk_pips;           // charge pips shown over his head
int gk_fx_t;           // frames to the next "ready" sparkle
int gk_s4;             // smash charges kept (frames, 0 - gk_smash_full()): forward
int gk_hi4;            // up
int gk_lw4;            // down
int gk_chain;          // the smashes used in this chain: 1 forward, 2 up, 4 down (0 no chain)
int gk_chain_req;      // the smash a chain cancel asked for (its start status reads it)
int gk_sm_auto;        // this smash releases on its own: 1 a full stored charge, 2 a chain
float gk_lx;           // v2: the clones' own places (left-spawned / right-spawned) and vertical speeds
float gk_ly;
float gk_lvy;
float gk_rx;
float gk_ry;
float gk_rvy;
float gk_last_oy;      // his Y last frame (the clones copy his vertical movement in the air)
float gk_floor_y;      // gk_floor()'s answer
float gk_hit_x;        // gk_line()'s point
float gk_hit_y;
int gk_lmiss;          // v3: frames each clone's heartbeat (his VAR_30, its MSC) has been missing ...
int gk_rmiss;
int gk_lage;           // ... and frames since it was made
int gk_rage;
int gk_det;            // he was launched / held last frame (the clones detached)
int gk_spawn_bits;     // the channel's "being made" bit (4 left, 8 right) ...
int gk_spawn_t;        // ... for this many more frames
int gk_cursor_t;       // frames to the next name tag hide
int gk_lfall;          // frames each clone has fallen on its own (0 standing / copying him)
int gk_rfall;

int gk_lw_full() { return 300; }          // 5 seconds held (the user)
int gk_ability_frames() { return 720; }   // 12 seconds
int gk_burnout_frames() { return 480; }   // 8 seconds
float gk_gap() { return 14.0f; }          // the clones' spacing (tools/gekkouga_clone_cave.py GAP)
int gk_lw_hold_frame() { return 14; }     // the stance's frame held while charging (its counter window 8 - 30)
int gk_pip_count() { return 10; }         // the charge bar: one pip a 30 frames
int gk_smash_full() { return 60; }        // a smash's full charge (Smash 4's hold)
float gk_smash_grow() { return 1.5f; }    // the smashes' hitbox / effect size at full charge (ACMD: gekkouga_build.py)
int gk_magic() { return 4747; }
float gk_gravity() { return 0.18f; }      // his gravity (fighter_param 0x03000018: reference/fighter_param_attributes.csv)
float gk_max_fall() { return 1.85f; }     // his max fall speed (0x03000019)
int gk_fall_frames() { return 300; }      // v3 fallback: a clone falling on its own this long is gone (the game's own
                                          // blast zone removal comes first: gk_heartbeat)
float gk_snap() { return 2.0f; }          // a standing clone keeps to a floor this far up / down, plus ...
float gk_slope() { return 1.4f; }         // ... this x its step (floors are lines with normal Y >= 0.6: at most 1.33)
float gk_wall_y() { return 5.0f; }        // the wall test's height above its feet
float gk_wall_gap() { return 3.0f; }      // how far it stays from a wall
float gk_head() { return 15.0f; }         // its height (the ceiling test)
int gk_beat_miss() { return 3; }          // frames without its heartbeat: the game removed it (the blast zone)
int gk_hitlag_min() { return 4; }         // a clone hit's hitlag on him when no victim's hitstop is found

float gk_abs(float v)
{
    if (v < 0)
    {
        return -v;
    }
    return v;
}

// ---- every frame (func_82, his per-frame hook; hitstop included)
void gekkouga_frame()
{
    int st;
    int flags;
    st = global4;
    if (st == 0xb1 || st == 0xb2 || st == 0x14f)
    {
        if (gk_ability > 0 || gk_alive != 0)
        {
            gk_end_ability(0);
        }
        if (gk_burnout > 0)
        {
            gk_burnout = 0;
            gk_overlay_off();
        }
        gk_chain = 0;
    }
    if (st == 0x14f)
    {
        gk_lw_charge = 0;                 // the match's start (Entry): every kept charge from 0
        gk_s4 = 0;
        gk_hi4 = 0;
        gk_lw4 = 0;
    }
    gk_input();
    if (gk_ability > 0)
    {
        gk_ability_update();
    }
    else if (gk_burnout > 0)
    {
        gk_burnout_update();
    }
    else
    {
        gk_ready_fx();
    }
    if (gk_chain != 0 && (st < 0x2b || st > 0x33))
    {
        gk_chain = 0;                     // anything but a smash ends the chain
    }
    flags = 0;
    if (gk_ability > 0)
    {
        flags = flags | 0x1;              // name tag hidden
    }
    // v3: bit 4 (clones out: his shield shapes report hits) no longer set: the clones have their own hurtboxes
    if (gk_burnout > 0)
    {
        flags = flags | 0x2;              // the burnout's slow
    }
    WorkModule(0, (float)flags + 0, 0x0f000314);
}

// ---- down special presses while the ability / burnout runs: swaps, or nothing (no status)
void gk_input()
{
    float sx;
    float sy;
    if (gk_swap_cd > 0)
    {
        gk_swap_cd -= 1;
    }
    if (gk_ability <= 0 && gk_burnout <= 0)
    {
        return;
    }
    if (ControlModule(0x2710, 0x1) == 0)
    {
        return;                           // special not pressed this frame
    }
    sy = ControlModuleF(0x1);
    if (sy > -0.3f)
    {
        return;                           // not a down special (neutral / side / up specials as normal)
    }
    WorkModule(0, 32.0f + 0, 0x0f0003c9); // Buffer_Clear (specials) for this fighter: no down special status
    global24 = global24 - (global24 & 0xf000); // nor this frame's special bits (the status loop reads them after this hook)
    if (gk_ability <= 0)
    {
        return;                           // burnout: down special disabled
    }
    sx = ControlModuleF(0);
    if (gk_swap_cd > 0)
    {
        return;
    }
    if (sx < -0.25f)
    {
        gk_swap(0x1);
    }
    else if (sx > 0.25f)
    {
        gk_swap(0x2);
    }
}

// his place and that clone's swapped (v2: the clone's own place, his GroundModule-tested fall): he goes where it
// stands, it takes his place; the other clone stays where it is (its offset from him changes). Silent: no status,
// sound, effect or camera command. A gone clone, or while he is launched / held (detached): nothing.
void gk_swap(int id)
{
    float o;
    float ox;
    float oy;
    float cx;
    float cy;
    if ((gk_alive & id) == 0 || gk_det)
    {
        return;
    }
    ox = PostureModuleF(0x1);
    oy = PostureModuleF(0x2);
    cx = gk_cx(id);
    cy = gk_cy(id);
    o = cx - ox;                          // his move (its offset, or less when a wall held it)
    if (id == 0x1)
    {
        gk_off_l = -o;
        gk_off_r = gk_off_r - o;
    }
    else
    {
        gk_off_r = -o;
        gk_off_l = gk_off_l - o;
    }
    WorkModule(0x2, cx - ox + 0, 0x0f000000);   // his X / Y to the clone's (the position variables: the game's set_pos)
    WorkModule(0x2, cy - oy + 0, 0x0f000001);
    gk_set_c(id, ox, oy, 0);
    gk_set_fall_t(id, 0);
    gk_last_oy = cy;
    gk_swap_cd = 10;
}

// ---- the input sites' down special (func_43, func_58, func_675, func_1999): 1 = entered the stance
int gk_lw_press()
{
    if (gk_ability > 0 || gk_burnout > 0)
    {
        return 0;
    }
    if (gk_lw_charge >= gk_lw_full())
    {
        gk_activate();
        return 0;
    }
    func_16(0x155, 0x1);
    return 0x1;
}

void gk_activate()
{
    gk_lw_charge = 0;
    gk_ability = gk_ability_frames();
    gk_alive = 0;
    gk_off_l = -gk_gap();
    gk_off_r = gk_gap();
    gk_seq = 0;
    gk_fx_t = 0;
    gk_det = 0;
    gk_last_oy = PostureModuleF(0x2);
    gk_cursor_t = 0;
    EffectModule(0x2723, 0x10000bd, 0x1, 0x1);
}

void gk_ability_update()
{
    if (gk_seq == 0)
    {
        gk_spawn(0x1);
    }
    if (gk_seq == 3)
    {
        gk_spawn(0x2);
    }
    gk_seq += 1;
    if (gk_spawn_t > 0)
    {
        gk_spawn_t -= 1;
    }
    gk_clone_hitlag();
    gk_check_hit();
    gk_heartbeat();
    gk_physics();
    gk_channel();
    gk_shapes_update();
    if (gk_cursor_t <= 0)
    {
        BattleObject(0xa, 0);             // his player cursor (name tag) hidden: SET_CURSOR(0)'s op (Rebirth shows it with 1)
        gk_cursor_t = 60;
    }
    gk_cursor_t -= 1;
    gk_ability -= 1;
    if (gk_ability <= 0)
    {
        gk_end_ability(0x1);
    }
}

// a clone made: at his place + its offset, his Y; its id told by the channel's spawn bit (4 left, 8 right) for 3 frames
void gk_spawn(int id)
{
    float off;
    off = gk_off(id);
    gk_set_c(id, PostureModuleF(0x1) + off, PostureModuleF(0x2), 0);
    gk_set_fall_t(id, 0);
    gk_spawn_bits = 0x4 * id;
    gk_spawn_t = 3;
    if (id == 0x1)
    {
        ArticleModule(0x2710, 0x6);
    }
    else
    {
        ArticleModule(0x2710, 0x7);
    }
    gk_alive = gk_alive | id;
    if (id == 0x1)
    {
        gk_lage = 0;
        gk_lmiss = 0;
    }
    else
    {
        gk_rage = 0;
        gk_rmiss = 0;
    }
    gk_puff_at(gk_cx(id), gk_cy(id));
}

// the Substitution's smoke (vanilla SpecialLwHit's 0x3300006) at a place (its Y + 6)
void gk_puff_at(float x, float y)
{
    EffectModule(0x3, 0x3300006, x, y + 6.0f, PostureModuleF(0x3), 0, 0, 0, 1.3f, 0, 0xffffffff);
}

// statuses the clones don't copy (ledge, being hit / grabbed / down, the Final Smash, KO): they idle / fall
int gk_mirror_off(int st)
{
    if (st >= 0x72 && st <= 0x7a)
    {
        return 0x1;
    }
    if (st >= 0x3f && st <= 0x5b)
    {
        return 0x1;
    }
    if (st == 0x156 || st >= 0x165 && st <= 0x168 || st == 0xb1 || st == 0xb2)
    {
        return 0x1;
    }
    return 0;
}

// he is launched / grabbed / thrown / down: the clones no longer travel with him (they stay and fall where they are)
int gk_detached(int st)
{
    if (st >= 0x3f && st <= 0x5b)
    {
        return 0x1;
    }
    return 0;
}

// he is on a ledge: they don't hang with him (they fall)
int gk_on_ledge(int st)
{
    if (st >= 0x72 && st <= 0x7a)
    {
        return 0x1;
    }
    return 0;
}

float gk_off(int id)
{
    if (id == 0x1)
    {
        return gk_off_l;
    }
    return gk_off_r;
}

float gk_cx(int id)
{
    if (id == 0x1)
    {
        return gk_lx;
    }
    return gk_rx;
}

float gk_cy(int id)
{
    if (id == 0x1)
    {
        return gk_ly;
    }
    return gk_ry;
}

float gk_cvy(int id)
{
    if (id == 0x1)
    {
        return gk_lvy;
    }
    return gk_rvy;
}

void gk_set_c(int id, float x, float y, float vy)
{
    if (id == 0x1)
    {
        gk_lx = x;
        gk_ly = y;
        gk_lvy = vy;
    }
    else
    {
        gk_rx = x;
        gk_ry = y;
        gk_rvy = vy;
    }
}

// the stage line test of his own GroundModule (Line_Test's MSC variables, world space, passable platforms too) from
// (x0, y0) to (x1, y1): the kind of the first line met (0 none, 1 floor, 2 wall, 3 ceiling), gk_hit_x / gk_hit_y there
int gk_line(float x0, float y0, float x1, float y1)
{
    WorkModule(0, x0 + 0, 0x0f0003d0);
    WorkModule(0, y0 + 0, 0x0f0003d1);
    WorkModule(0, x1 + 0, 0x0f0003d2);
    WorkModule(0, y1 + 0, 0x0f0003d3);
    WorkModule(0, 1.0f + 0, 0x0f0003d4);
    if (WorkModuleF(0, 0x0f0003d4) < 0.5f)
    {
        return 0;
    }
    gk_hit_x = WorkModuleF(0, 0x0f0003d6);
    gk_hit_y = WorkModuleF(0, 0x0f0003d7);
    return (int)(WorkModuleF(0, 0x0f0003d8) + 0.5f);
}

// the first floor (a line with normal Y >= 0.6, passable platforms included) from (x, y0) down to (x, y1): 1 = found,
// gk_floor_y its height
int gk_floor(float x, float y0, float y1)
{
    if (gk_line(x, y0, x, y1) != 0x1)
    {
        return 0;
    }
    gk_floor_y = gk_hit_y;
    return 0x1;
}

// one clone's frame (v3):
// X: with him (his X + its offset) unless he is detached; a wall (a stage line too steep for a floor) between where it
//    is and there stops it against the wall (its offset gives way; free again, it goes back to its offset).
// Y: while he is in the air by his own doing it copies his vertical movement, else it falls with his gravity / max fall
//    speed; going up, a ceiling stops it; going down it lands on the first floor (platforms too). Standing, it follows
//    the floor under its new X, up or down as far as the steepest floor can go for that step (slopes, steps).
// Frozen while he is in hitlag. Gone when the game removes it (the blast zone: gk_heartbeat) or, as a fallback, after
// gk_fall_frames() falling on its own.
void gk_clone_phys(int id, float ox, float oy, int copy, int frozen)
{
    float x;
    float y;
    float vy;
    float dy;
    float ny;
    float nx;
    float from;
    float to;
    float reach;
    int t;
    if ((gk_alive & id) == 0)
    {
        return;
    }
    x = gk_cx(id);
    y = gk_cy(id);
    vy = gk_cvy(id);
    t = gk_fall_t(id);
    if (frozen)
    {
        return;
    }
    nx = x;
    if (!gk_det)
    {
        nx = ox + gk_off(id);
    }
    if (gk_abs(nx - x) > 0.01f)
    {
        if (gk_line(x, y + gk_wall_y(), nx, y + gk_wall_y()) == 0x2)
        {
            if (nx > x)
            {
                nx = gk_hit_x - gk_wall_gap();
            }
            else
            {
                nx = gk_hit_x + gk_wall_gap();
            }
            if (gk_abs(nx - x) > gk_abs(ox + gk_off(id) - x))
            {
                nx = x;
            }
        }
    }
    reach = gk_snap() + gk_slope() * gk_abs(nx - x);
    x = nx;
    if (copy)
    {
        dy = oy - gk_last_oy;
        vy = dy;
        t = 0;
        from = y + 0.5f;                  // its floor stops it (it landed while he still comes down) ...
        if (gk_abs(y - gk_last_oy) < 0.1f)
        {
            from = y - 0.05f;             // ... unless it is level with him: the floor he left (a platform drop)
        }
        to = y + dy - 0.5f;
    }
    else
    {
        vy = vy - gk_gravity();
        if (vy < -gk_max_fall())
        {
            vy = -gk_max_fall();
        }
        dy = vy;
        from = y + 0.5f;
        to = y + dy - 0.5f;
        if (t == 0)
        {
            from = y + reach;             // it stood last frame: the floor under its new X, a slope up or down
            to = y + dy - reach;
        }
        t += 1;
    }
    ny = y + dy;
    if (dy > 0.01f)
    {
        if (gk_line(x, y + gk_head(), x, ny + gk_head()) == 0x3)
        {
            ny = gk_hit_y - gk_head();    // a ceiling: no higher
            vy = 0;
        }
    }
    else
    {
        if (gk_floor(x, from, to))
        {
            ny = gk_floor_y;
            vy = 0;
            t = 0;
        }
    }
    gk_set_c(id, x, ny, vy);
    gk_set_fall_t(id, t);
    if (t > gk_fall_frames())
    {
        gk_kill(id, 0);                   // fallback: fallen far off the stage
    }
}

int gk_fall_t(int id)
{
    if (id == 0x1)
    {
        return gk_lfall;
    }
    return gk_rfall;
}

void gk_set_fall_t(int id, int t)
{
    if (id == 0x1)
    {
        gk_lfall = t;
    }
    else
    {
        gk_rfall = t;
    }
}

void gk_physics()
{
    float ox;
    float oy;
    int det;
    int copy;
    int frozen;
    ox = PostureModuleF(0x1);
    oy = PostureModuleF(0x2);
    det = gk_detached(global4);
    frozen = StopModule(0x1);
    if (gk_det && !det)
    {
        gk_det = 0;                       // back from a launch: the clones back in formation (smoke)
        if (gk_alive & 0x1)
        {
            gk_set_c(0x1, ox + gk_off_l, oy, 0);
            gk_lfall = 0;
            gk_puff_at(gk_lx, gk_ly);
        }
        if (gk_alive & 0x2)
        {
            gk_set_c(0x2, ox + gk_off_r, oy, 0);
            gk_rfall = 0;
            gk_puff_at(gk_rx, gk_ry);
        }
    }
    gk_det = det;
    copy = 0;
    if (!det && StatusModule(0x1) == 0x2 && !gk_on_ledge(global4))
    {
        copy = 0x1;
    }
    gk_clone_phys(0x1, ox, oy, copy, frozen);
    gk_clone_phys(0x2, ox, oy, copy, frozen);
    gk_last_oy = oy;
}

// the channel his clones read (his VAR_24 - VAR_31, SLOTn_SHARED_0 - 7): their places, his motion (v3: its kind x 1024
// + its frame in VAR_28), its rate (0 while he is in hitlag: they freeze with him), VAR_30 their heartbeat (theirs to
// write: gk_heartbeat), 4747000 + flags (1 / 2 alive, 4 / 8 being made, 16 / 32 falling on its own: it plays Fall)
void gk_channel()
{
    int k;
    float f;
    float r;
    int flags;
    k = MotionModule(0x7);
    f = MotionModuleF(0x1);
    r = MotionModuleF(0xa);
    if (gk_mirror_off(global4))
    {
        k = 0;                            // Wait1 (standing; a clone falling on its own plays Fall: flags 16 / 32)
        if (StatusModule(0x1) == 0x2 && !gk_det && !gk_on_ledge(global4))
        {
            k = 0x24;                     // Fall (in the air with him: his Final Smash, ...)
        }
        f = 0;
        r = 1.0f;
    }
    if (StopModule(0x1))
    {
        r = 0;
    }
    flags = gk_alive;
    if (gk_spawn_t > 0)
    {
        flags = flags | gk_spawn_bits;
    }
    if (gk_lfall > 2)
    {
        flags = flags | 0x10;
    }
    if (gk_rfall > 2)
    {
        flags = flags | 0x20;
    }
    WorkModule(0, gk_lx + 0, 0x0f000318);
    WorkModule(0, gk_ly + 0, 0x0f000319);
    WorkModule(0, gk_rx + 0, 0x0f00031a);
    WorkModule(0, gk_ry + 0, 0x0f00031b);
    WorkModule(0, (float)(k * 1024) + f, 0x0f00031c);
    WorkModule(0, r + 0, 0x0f00031d);
    WorkModule(0, 4747000.0f + (float)flags, 0x0f00031f);
}

// a clone's hit landed (the executable's clone hit method: his VAR_22 = 1): he takes the hitlag he'd have had, the
// biggest hitstop now running on a fighter (the victims': their "hitstop of the last hit"), at least gk_hitlag_min();
// not again while he is in hitlag (two clones on one frame: one hitlag)
void gk_clone_hitlag()
{
    int s;
    float h;
    float n;
    if (WorkModuleF(0, 0x0f000316) < 0.5f)
    {
        return;
    }
    WorkModule(0, 0 + 0, 0x0f000316);
    if (StopModule(0x1))
    {
        return;
    }
    n = 0;
    s = 1;
    while (s <= 8)
    {
        if (WorkModuleF(0, 0x0f000043 + 8 * (s + 2)) > 0.5f)
        {
            h = WorkModuleF(0, 0x0f000044 + 8 * (s + 2));
            if (h > n)
            {
                n = h;
            }
        }
        s += 1;
    }
    if (n < (float)gk_hitlag_min())
    {
        n = (float)gk_hitlag_min();
    }
    StopModule(0x2, (int)n);
}

// v3: a clone's own hurtbox was hit (the executable: his VAR_21 = 20000 + its id, from the clone's damage this frame):
// exactly that clone turns into the log. (v1 / v2's 10000 + dx shield-capsule report: no longer made, ignored.)
void gk_check_hit()
{
    float h;
    int id;
    h = WorkModuleF(0, 0x0f000315);
    if (h < 0.5f)
    {
        return;
    }
    WorkModule(0, 0 + 0, 0x0f000315);
    if (h < 15000.0f)
    {
        return;
    }
    id = (int)(h - 20000.0f + 0.5f);
    if (id == 0x1 || id == 0x2)
    {
        gk_kill(id, 0x1);
    }
}

// v3: each clone's MSC adds its bit (1 / 2) to his VAR_30 every frame; the game removes a weapon past the stage's blast
// zone without its MSC: a clone whose bit stays off gk_beat_miss() frames is gone (no log, no removal call needed)
void gk_heartbeat()
{
    int beat;
    beat = (int)(WorkModuleF(0, 0x0f00031e) + 0.5f);
    WorkModule(0, 0 + 0, 0x0f00031e);
    gk_lage += 1;
    gk_rage += 1;
    if ((gk_alive & 0x1) && gk_lage > 6)
    {
        if (beat & 0x1)
        {
            gk_lmiss = 0;
        }
        else
        {
            gk_lmiss += 1;
            if (gk_lmiss >= gk_beat_miss())
            {
                gk_gone(0x1);
            }
        }
    }
    if ((gk_alive & 0x2) && gk_rage > 6)
    {
        if (beat & 0x2)
        {
            gk_rmiss = 0;
        }
        else
        {
            gk_rmiss += 1;
            if (gk_rmiss >= gk_beat_miss())
            {
                gk_gone(0x2);
            }
        }
    }
}

// a clone the game already removed: off the books (its smoke where it was last, as a kill without a log)
void gk_gone(int id)
{
    gk_kill(id, 0);
}

// a clone gone: removed, its smoke, and (hit) the Substitution log (rare: the doll) where it stood
void gk_kill(int id, int log)
{
    float x;
    float y;
    float z;
    float chance;
    if ((gk_alive & id) == 0)
    {
        return;
    }
    if (id == 0x1)
    {
        ArticleModule(0x2712, 0x6);
    }
    else
    {
        ArticleModule(0x2712, 0x7);
    }
    gk_alive = gk_alive & (0x3 - id);
    gk_puff_at(gk_cx(id), gk_cy(id));
    if (log)
    {
        x = PostureModuleF(0x1);          // the log is made at his place (0x3F7's item): he is there for it
        y = PostureModuleF(0x2);
        z = PostureModuleF(0x3);
        PostureModule(0x3, gk_cx(id), gk_cy(id), z);
        chance = WorkModuleF(0, 0x8000003) / 100.0f;
        if (MathF(0x6) <= chance)
        {
            BattleObject(0x3f8);
        }
        else
        {
            BattleObject(0x3f7);
        }
        PostureModule(0x3, x, y, z);
    }
}

void gk_end_ability(int burn)
{
    if (gk_alive & 0x1)
    {
        gk_kill(0x1, 0);
    }
    if (gk_alive & 0x2)
    {
        gk_kill(0x2, 0);
    }
    gk_alive = 0;
    gk_ability = 0;
    gk_shapes_update();
    WorkModule(0, 0 + 0, 0x0f00031f);
    if (burn)
    {
        BattleObject(0xa, 0x1);           // the name tag back
        gk_burnout = gk_burnout_frames();
    }
}

// v1 / v2's clone capsules (his shield group 1, the executable's 4 shapes): v3 keeps them off (the clones have their
// own hurtboxes; his counter shape group stays built but never switched on)
int gk_shapes_want()
{
    return 0;
}

void gk_shapes_update()
{
    int want;
    want = gk_shapes_want();
    ShieldModule(0, 0x2, 0, (want & 0x1) != 0, 0x1);
    ShieldModule(0, 0x2, 0x1, (want & 0x2) != 0, 0x1);
    ShieldModule(0, 0x2, 0x2, (want & 0x4) != 0, 0x1);
    ShieldModule(0, 0x2, 0x3, (want & 0x8) != 0, 0x1);
}

// ---- the burnout: grey (the Final Smash's overlay op, re-set every frame), half speed (the executable)
void gk_burnout_update()
{
    ColorBlendModule(0x2711, 110.0f, 110.0f, 110.0f, 170.0f);
    ColorBlendModule(0x271a, 0x65);
    gk_burnout -= 1;
    if (gk_burnout <= 0)
    {
        gk_overlay_off();
    }
}

void gk_overlay_off()
{
    ColorBlendModule(0x2711, 0, 0, 0, 0);
    ColorBlendModule(0x2713);
}

// ---- charged and waiting: a small sparkle over his head every 45 frames
void gk_ready_fx()
{
    if (gk_lw_charge < gk_lw_full())
    {
        return;
    }
    if (gk_fx_t > 0)
    {
        gk_fx_t -= 1;
        return;
    }
    gk_fx_t = 45;
    EffectModule(0x2710, 0x10000bd, 0, 0, 22.0f, 0, 0, 0, 0, 0.8f, 0, 0, 0, 0, 0, 0, 0);
}

// ---- the charge stance (SpecialLw 0x155, his old counter: no counter shape now)
void gk_lw_main()
{
    gk_pips = 0;
    gk_bar();
    if (!StopModule(0x1))
    {
        gk_lw_tick();
    }
    global16 = gk_lw_tick;
}

// per frame of the stance (not in hitlag): the charge, its bar, the stance's afterimages again
void gk_lw_tick()
{
    if (gk_lw_charge < gk_lw_full())
    {
        gk_lw_charge += 1;
    }
    gk_bar();
    if (MotionModuleF(0x1) >= (float)gk_lw_hold_frame())
    {
        gk_fx_t += 1;
        if (gk_fx_t >= 20)
        {
            gk_fx_t = 0;
            EffectModule(0x2710, 0x3300009, 0, 0, 11.0f, 5.0f, 0, 0, 0, 1.0f, 0, 0, 0, 0, 0, 0, 0);
        }
    }
}

// the charge bar: pips (0x1000047) in a row over his head, one lit every gk_lw_full() / gk_pip_count() frames
void gk_bar()
{
    int lit;
    float lr;
    lit = gk_lw_charge * gk_pip_count() / gk_lw_full();
    lr = PostureModuleF(0);
    while (gk_pips < lit)
    {
        EffectModule(0x2712, 0x1000047, 0, 0, 25.0f, ((float)gk_pips - 4.5f) * 2.2f * lr, 0, 0, 0, 0.35f, 0x1);
        gk_pips += 1;
    }
}

int gk_lw_loop()
{
    if (global19 == 0 && global18 == 0x2)
    {
        func_23(0x289);
        func_2341(0);
        GroundModule(0x2710, 0x5);
        gk_pips = 0;                      // the motion change ended the pips (terminate): drawn again
    }
    else if (global19 == 0x2 && global18 == 0)
    {
        gk_pips = 0;
        func_23(0x271);
        func_2341(0);
        KineticModule(0x11, 0x1, 0);
        KineticModule(0xf, 0x1, 0);
        GroundModule(0x2710, 0x1);
    }
    if (gk_lw_charge >= gk_lw_full())
    {
        EffectModule(0x2710, 0x1000069, 0, 0, 12.0f, 0, 0, 0, 0, 1.0f, 0, 0, 0, 0, 0, 0, 0);
        gk_lw_exit();                     // full: ready (the next down special is the ability)
        return 0x1;
    }
    if (ControlModule(0x2712, 0x1) == 0)
    {
        gk_lw_exit();                     // released: the charge is kept
        return 0x1;
    }
    if (MotionModuleF(0x1) >= (float)gk_lw_hold_frame())
    {
        MotionModule(0x4, 0 + 0);         // the stance held
    }
    else
    {
        MotionModule(0x4, 1.0f);
    }
    return 0;
}

void gk_lw_exit()
{
    EffectModule(0x2723, 0x1000047, 0x1, 0x1);
    if (global18 == 0)
    {
        func_16(0, 0);
    }
    else
    {
        func_16(0xe, 0);
    }
}

// ---- smash attacks: t = 1 forward, 2 up, 4 down
int gk_sm_get(int t)
{
    if (t == 0x1)
    {
        return gk_s4;
    }
    if (t == 0x2)
    {
        return gk_hi4;
    }
    return gk_lw4;
}

void gk_sm_set(int t, int v)
{
    if (t == 0x1)
    {
        gk_s4 = v;
    }
    else if (t == 0x2)
    {
        gk_hi4 = v;
    }
    else
    {
        gk_lw4 = v;
    }
}

int gk_sm_type(int st)
{
    if (st >= 0x2b && st <= 0x2d)
    {
        return 0x1;
    }
    if (st >= 0x31 && st <= 0x33)
    {
        return 0x2;
    }
    if (st >= 0x2e && st <= 0x30)
    {
        return 0x4;
    }
    return 0;
}

int gk_sm_start_status(int t)
{
    if (t == 0x1)
    {
        return 0x2b;
    }
    if (t == 0x2)
    {
        return 0x31;
    }
    return 0x2e;
}

int gk_sm_hold_status(int t)
{
    if (t == 0x1)
    {
        return 0x2c;
    }
    if (t == 0x2)
    {
        return 0x32;
    }
    return 0x2f;
}

int gk_sm_attack_status(int t)
{
    if (t == 0x1)
    {
        return 0x2d;
    }
    if (t == 0x2)
    {
        return 0x33;
    }
    return 0x30;
}

// the chain window: from the last hitbox's end (attacks4 16, attackhi4 22, attacklw4 19) to the move's end
int gk_sm_window(int t)
{
    if (t == 0x1)
    {
        return 16;
    }
    if (t == 0x2)
    {
        return 22;
    }
    return 19;
}

// start statuses' main (0x2B / 0x31 / 0x2E): releases on its own when chained or fully charged
void gk_sm_start_main(int t)
{
    gk_sm_auto = 0;
    if (gk_chain_req == t)
    {
        gk_sm_auto = 0x2;
    }
    else if (gk_sm_get(t) >= gk_smash_full())
    {
        gk_sm_auto = 0x1;
    }
    gk_chain_req = 0;
}

// start statuses' loop: at the hold point (ACMD flag 0x2100001B) the attack (auto), the hold (attack held) or
// nothing (released before: no attack, nothing charged)
int gk_sm_start_loop(int t)
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (WorkModule(0x10, 0x2100001b) != 0x1)
    {
        return 0;
    }
    if (gk_sm_auto)
    {
        gk_sm_release(t);
        return 0x1;
    }
    if (ControlModule(0x2712, 0))
    {
        func_16(gk_sm_hold_status(t), 0x1);
        return 0x1;
    }
    func_16(0, 0);
    return 0x1;
}

// the attack at full charge: the hold's exit values (ratio 1, charged), the stored charge used (not a chain's)
void gk_sm_release(int t)
{
    if (gk_sm_auto == 0x1)
    {
        gk_sm_set(t, 0);
    }
    gk_chain = gk_chain | t;
    WorkModule(0, 1.0f + 0, 0x1000000);
    WorkModule(0x2710, 0x21000002);
    func_16(gk_sm_attack_status(t), 0x1);
}

// hold statuses' per-frame (not in hitlag; replaces func_283): the charge grows, kept
void gk_sm_hold_tick()
{
    int t;
    int v;
    WorkModule(0xa, 0x11000005);
    t = gk_sm_type(global4);
    if (t == 0)
    {
        return;
    }
    v = gk_sm_get(t) + 1;
    if (v > gk_smash_full())
    {
        v = gk_smash_full();
    }
    gk_sm_set(t, v);
}

// hold statuses' loop: full -> ready (no attack: the next use releases it), released -> kept (no attack)
int gk_sm_hold_loop(int t)
{
    if (global18 == 0x2)
    {
        func_16(0xe, 0);
        return 0x1;
    }
    if (gk_sm_get(t) >= gk_smash_full())
    {
        EffectModule(0x2710, 0x1000069, 0, 0, 12.0f, 0, 0, 0, 0, 0.8f, 0, 0, 0, 0, 0, 0, 0);
        func_16(0, 0);
        return 0x1;
    }
    if (!ControlModule(0x2712, 0))
    {
        func_16(0, 0);
        return 0x1;
    }
    return 0;
}

// attack statuses' loop: a smash not used yet in this chain cancels into its start (auto-released)
int gk_chain_try(int cur)
{
    int t;
    if (gk_sm_type(global4) != cur || global18 != 0)
    {
        return 0;
    }
    if (MotionModuleF(0x1) < (float)gk_sm_window(cur))
    {
        return 0;
    }
    t = 0;
    if (global24 & 0x10)
    {
        t = 0x1;
    }
    else if (global24 & 0x20)
    {
        t = 0x2;
    }
    else if (global24 & 0x40)
    {
        t = 0x4;
    }
    if (t == 0 || (gk_chain & t) != 0)
    {
        return 0;
    }
    gk_chain_req = t;
    if (t == 0x1 && ControlModuleF(0) * PostureModuleF(0) < -0.25f)
    {
        PostureModule(0x1);               // a forward smash the other way: turned first
        PostureModule(0x2);
    }
    func_16(gk_sm_start_status(t), 0x1);
    return 0x1;
}
