
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
int gk_smash;          // v3: the smash charge kept (frames, 0 - gk_smash_full()), one for all three smashes
int gk_hold_first;     // v3: the hold's first tick (its effects made at once)
int gk_gen_req;        // v4 diag: 0x40 / 0x80 the left / right clone made next frame
int gk_seen;           // v5: 1 / 2 the clone's heartbeat seen (its script runs and found him)
int gk_last_made;      // v6: the clone made last (only its "being made" bit is on)
int gk_chain;          // the smashes used in this chain: 1 forward, 2 up, 4 down (0 no chain)
int gk_chain_req;      // the smash a chain cancel asked for (its start status reads it)
int gk_sm_auto;        // this smash releases on its own: 1 a full stored charge, 2 a chain
float gk_lx;           // v2: the clones' own places (left-spawned / right-spawned) and vertical speeds
float gk_ly;
float gk_lvy;
float gk_rx;
float gk_ry;
float gk_rvy;
float gk_last_oy;      // his Y last frame (the clones copy his vertical movement in the air); clone delay: 1 of his
                       // (unfrozen) frames back
float gk_hx1;          // clone delay (the user: "the left clone ... 1 frame delay and the right clone ... 2"): his X 1 / 2
float gk_hx2;          // of his unfrozen frames back ...
float gk_hy2;          // ... his Y 2 / 3 back ...
float gk_hy3;
int gk_hcopy;          // ... "copying his vertical movement" then (bit 1: 1 back, 2: 2 back) ...
int gk_cl_why;         // clone fixes v2 diag: what overrode the clones' places since the last line (1 / 2 a wall held the
                       // left / right one, 4 their history started over, 8 back in formation, 16 / 32 falling on its own)
int gk_cl_t;           // ... frames to the next line (every 10 while he is on the ground with clones out)
int gk_hn;             // ... and how many of those each clone may use: the left's (0 - 3) + 4 x the right's (from 0 when
                       // it is made, at a swap, back in formation)
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
int gk_gen;            // skeleton v1: the executable's clear-all count (his VAR_14) last seen ...
int gk_gen_seen;       // ... 1 once read: a change is a training reset / restart (the state below starts over)
int gk_sk_req_t;       // skeleton v1: frames his skeleton request (VAR_15) stays up for the executable's claim
int gk_tr_done;        // burn v2: the attack status whose fire trail was asked for (0: none yet)
int gk_ac_used;        // aerial chain v1: the aerials used in this chain (bit 1 << kind: 1 neutral ... 5 down)
int gk_ac_kind;        // the aerial now (1 - 5; 0 none)
int gk_ac_hit;         // frames since this aerial hit an opponent (0: not yet)
int gk_ac_req;         // 1: the next aerial start is a chain's (the chain kept)
int gk_tr_req_t;       // burn v2: frames his trail requests (VAR_0 - VAR_11) stay up for the executable's claims

int gk_lw_full() { return 300; }          // 5 seconds held (the user)
int gk_ability_frames() { return 720; }   // 12 seconds
int gk_burnout_frames() { return 480; }   // 8 seconds
float gk_gap() { return 14.0f; }          // the clones' spacing (tools/gekkouga_clone_cave.py GAP)
int gk_lw_hold_frame() { return 14; }     // the stance's frame held while charging (its counter window 8 - 30)
int gk_pip_count() { return 10; }         // the charge bar: one pip a 30 frames
int gk_smash_full() { return 120; }       // v3: the full smash charge (the user; Smash 4's own hold is 60)
float gk_smash_grow() { return 5.0f; }    // v4: the smashes' hitbox size at full charge, as their effects (ACMD:
                                          // gekkouga_build.py GROW; sword-bone hitboxes' offsets too)
float gk_smash_fx_max() { return 5.0f; }  // v3: their effects' size at full charge (ACMD EFFECT_GROW; the hold: gk_sm_fx)
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
int gk_beat_grace() { return 120; }       // v5: frames a clone whose heartbeat was never seen is kept anyway
int gk_hitlag_min() { return 4; }         // a clone hit's hitlag on him when no victim's hitstop is found
int gk_sk_req_frames() { return 5; }      // skeleton v1: the request's life (a skeleton out already: none is made)
int gk_tr_req_frames() { return 5; }      // burn v2: the trail requests' life (6 trails out already: none is made)

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
    int gen;
    st = global4;
    gen = (int)(WorkModuleF(0, 0x0f00030e) + 0.5f);   // skeleton v1: the executable's clear-all count & 7 (VAR_14)
    if (gk_gen_seen && gen != gk_gen)
    {
        gk_reset();                       // a training reset / restart / new match: his state starts over
    }
    gk_gen = gen;
    gk_gen_seen = 0x1;
    if (gk_sk_req_t > 0)
    {
        gk_sk_req_t -= 1;
        if (gk_sk_req_t == 0)
        {
            WorkModule(0, 0 + 0, 0x0f00030f);   // not claimed: no skeleton was made (one is out already)
        }
    }
    if (gk_tr_req_t > 0)
    {
        gk_tr_req_t -= 1;
        if (gk_tr_req_t == 0)
        {
            gk_tr_clear();                // burn v2: not claimed (6 trails out already)
        }
    }
    if (st != gk_tr_done)
    {
        gk_tr_done = 0;                   // burn v2: out of that attack: the next one asks again
    }
    if (st != 0x34)
    {
        gk_ac_end();                      // aerial chain v1: anything but an aerial (landing, a special, an air dodge,
    }                                     // being hit, a ledge grab, a jump) ends the chain
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
        gk_smash = 0;
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
    if (gk_lw_charge >= gk_lw_full())
    {
        flags = flags | 0x8;              // v3 diag: the ability ready (the TEST_ONLY exe logs flag changes: S4GF)
    }
    flags = flags | gk_alive * 16;        // v3 diag: 16 / 32 the clones out
    flags = flags | gk_ac_diag();         // aerial chain v1 diag (256 up: the exe's S4GF line logs a change)
    flags = flags | gk_cl_diag();         // clone fixes v2 diag (1048576 toggled: an S4GF line with VAR_23)
    if (gk_ability > 0)
    {
        flags = flags | gk_gen_req;       // v4 diag: 64 / 128 a clone about to be made (next frame)
    }
    WorkModule(0, (float)flags + 0, 0x0f000314);
    gk_gauge();
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
    gk_cl_why = gk_cl_why | 0x4;
    gk_hn = 0;                            // clone delay: his old places mean nothing now (both offsets changed): the
    gk_swap_cd = 10;                      // clones go on from his new place (held for their delay, then delayed)
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
    gk_hn = 0;
    gk_hcopy = 0;
    gk_cursor_t = 0;
    EffectModule(0x2723, 0x10000bd, 0x1, 0x1);
}

void gk_ability_update()
{
    // v4: each clone is requested a frame before it is made (flags bit 64 / 128: the TEST_ONLY exe logs the request
    // before the generate runs, and its result the frame after)
    gk_gen_req = 0;
    if (gk_seq == 0)
    {
        gk_gen_req = 0x40;
    }
    if (gk_seq == 3)
    {
        gk_gen_req = 0x80;
    }
    if (gk_seq == 1)
    {
        gk_spawn(0x1);
    }
    if (gk_seq == 4)
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
    int r;
    off = gk_off(id);
    gk_set_c(id, PostureModuleF(0x1) + off, PostureModuleF(0x2), 0);
    gk_set_fall_t(id, 0);
    gk_set_hn(id, 0);                     // clone delay: no history yet: his place now, held for its delay
    gk_spawn_bits = 0x4 * id;
    gk_spawn_t = 3;
    if (id == 0x1)
    {
        r = ArticleModule(0x2710, 0x6);
    }
    else
    {
        r = ArticleModule(0x2710, 0x7);
    }
    WorkModule(0, (float)r + 0, 0x0f000317);   // v3 diag: the generate's result (the TEST_ONLY exe logs it: S4GF gen=)
    gk_alive = gk_alive | id;
    gk_seen = gk_seen & (0x3 - id);
    gk_last_made = id;
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
void gk_clone_phys(int id, float ox, float oy, float lastoy, int copy, int frozen)
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
            gk_cl_why = gk_cl_why | id;   // clone fixes v2 diag: a wall held it (1 the left clone, 2 the right)
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
        dy = oy - lastoy;
        vy = dy;
        t = 0;
        from = y + 0.5f;                  // its floor stops it (it landed while he still comes down) ...
        if (gk_abs(y - lastoy) < 0.1f)
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
        gk_why(400, id);
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
        gk_hn = 0;                        // (clone delay: from his place now)
        gk_cl_why = gk_cl_why | 0xc;
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
    if (frozen)
    {
        return;                           // his hitlag: the clones freeze with him (no history kept: they stay in step)
    }
    gk_delayed(0x1, ox, oy, copy);
    gk_delayed(0x2, ox, oy, copy);
    gk_hy3 = gk_hy2;                      // clone delay: this frame into the history
    gk_hy2 = gk_last_oy;
    gk_last_oy = oy;
    gk_hx2 = gk_hx1;
    gk_hx1 = ox;
    gk_hcopy = (gk_hcopy * 2 + copy) & 0x3;
    gk_set_hn(0x1, gk_get_hn(0x1) + 1);
    gk_set_hn(0x2, gk_get_hn(0x2) + 1);
}

// ---- clone delay (fighters/gekkouga/README.md "Clone delay"): each clone replays him gk_delay(id) of his frames late
// (the left-spawned 1, the right-spawned 2): its place here (his X, and his vertical movement while it copies it) and
// its motion / frame / rate / facing in its own MSC (weapons/clone.c: the channel's history). Its own physics (walls,
// floors, its fall) run on the frame. Frozen frames (his hitlag) are no frames: no history is kept, they freeze.
int gk_delay(int id) { return id; }        // 1 the left-spawned clone, 2 the right-spawned one

int gk_get_hn(int id)
{
    if (id == 0x1)
    {
        return gk_hn & 0x3;
    }
    return (gk_hn / 4) & 0x3;
}

void gk_set_hn(int id, int n)
{
    if (n > 0x3)
    {
        n = 0x3;
    }
    if (id == 0x1)
    {
        gk_hn = (gk_hn & 0xc) + n;
    }
    else
    {
        gk_hn = (gk_hn & 0x3) + n * 4;
    }
}

float gk_hist_x(int i, float ox)
{
    if (i == 0x1)
    {
        return gk_hx1;
    }
    if (i == 0x2)
    {
        return gk_hx2;
    }
    return ox;
}

float gk_hist_y(int i, float oy)
{
    if (i == 0x1)
    {
        return gk_last_oy;
    }
    if (i == 0x2)
    {
        return gk_hy2;
    }
    if (i == 0x3)
    {
        return gk_hy3;
    }
    return oy;
}

int gk_hist_copy(int i, int copy)
{
    if (i == 0)
    {
        return copy;
    }
    return (gk_hcopy / i) & 0x1;
}

// one clone's frame from his state gk_delay(id) frames back (fewer while its history fills: his place now at first)
void gk_delayed(int id, float ox, float oy, int copy)
{
    int n;
    int i;
    float lastoy;
    n = gk_get_hn(id);
    i = gk_delay(id);
    if (i > n)
    {
        i = n;
    }
    lastoy = gk_hist_y(i, oy);            // no frame before it in its history: no vertical movement
    if (i + 1 <= n)
    {
        lastoy = gk_hist_y(i + 1, oy);
    }
    gk_clone_phys(id, gk_hist_x(i, ox), gk_hist_y(i, oy), lastoy, gk_hist_copy(i, copy), 0);
}

// the channel his clones read (his VAR_24 - VAR_31, SLOTn_SHARED_0 - 7): their places, his motion (v3: its kind x 1024
// + its frame in VAR_28), its rate (0 while he is in hitlag: they freeze with him), VAR_30 their heartbeat (theirs to
// write: gk_heartbeat), 4747000 + flags (1 / 2 alive, 4 / 8 being made, 16 / 32 falling on its own: it plays Fall;
// clone delay: 64 he is frozen: their delayed playback pauses)
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
    flags = flags | (gk_alive & gk_last_made & (0x3 - gk_seen)) * 4;   // v5 / v6: "being made" (only the clone made
                                          // last, until its heartbeat is first seen: v5 kept the left's on while the
                                          // right one was made, and both took id 1)
    if (gk_lfall > 2)
    {
        flags = flags | 0x10;
    }
    if (gk_rfall > 2)
    {
        flags = flags | 0x20;
    }
    if (StopModule(0x1))
    {
        flags = flags | 0x40;             // clone delay: he is frozen (hitlag): their playback pauses (no history kept)
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
    gk_ac_clone_hit();                    // aerial chain v1: a clone's copy of his aerial landed: it hit
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
        gk_why(200, id);
    }
}

// v3: each clone's MSC adds its bit (1 / 2) to his VAR_30 every frame; the game removes a weapon past the stage's blast
// zone without its MSC: a clone whose bit stays off gk_beat_miss() frames is gone (no log, no removal call needed).
// v5: only once its heartbeat has been seen (its script runs and found him); never seen: gk_beat_grace() frames first
void gk_heartbeat()
{
    int beat;
    beat = (int)(WorkModuleF(0, 0x0f00031e) + 0.5f);
    WorkModule(0, 0 + 0, 0x0f00031e);
    gk_lage += 1;
    gk_rage += 1;
    if (beat & 0x1)
    {
        gk_seen = gk_seen | 0x1;
    }
    if (beat & 0x2)
    {
        gk_seen = gk_seen | 0x2;
    }
    if ((gk_alive & 0x1) && ((gk_seen & 0x1) || gk_lage > gk_beat_grace()))
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
    if ((gk_alive & 0x2) && ((gk_seen & 0x2) || gk_rage > gk_beat_grace()))
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

// v5 diag: why a clone went (his VAR_23, logged by the TEST_ONLY exe as "gen="): 100 + id heartbeat lost (the game
// removed it, or its script never ran), 200 + id hit, 300 + id the ability's end / a KO, 400 + id fell off (v13: also
// a heartbeat lost while it was falling on its own: past the blast zone), or the fall fallback;
// 1 = the last generate's answer otherwise
void gk_why(int code, int id)
{
    WorkModule(0, (float)(code + id) + 0, 0x0f000317);
}

// a clone the game already removed: off the books (its smoke where it was last, as a kill without a log). v13: one
// that was falling on its own when it stopped reporting fell off the stage (the game removed it past the blast zone):
// 400 + id, as the fall fallback; 100 + id otherwise
void gk_gone(int id)
{
    int fell;
    fell = gk_fall_t(id) > 2;
    gk_kill(id, 0);
    if (fell)
    {
        gk_why(400, id);
        return;
    }
    gk_why(100, id);
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
        gk_why(300, 0x1);
    }
    if (gk_alive & 0x2)
    {
        gk_kill(0x2, 0);
        gk_why(300, 0x2);
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
    gk_fx_t = 45;                         // v6: no sparkle over his head (the panel's gauge blinks "KO" when ready)
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
    // v6 (the user): no pips over his head any more: the gauge is on his damage panel (gk_gauge, the executable)
}

// v6: the damage panel gauge (his VAR_19, the executable shows it on Little Mac's KO meter in his panel): mode x 1000 +
// 0-100. 1: the charge (100 = ready, the meter's blinking "KO" frame), 2: the ability's time left, 3: the burnout's
// time left (grey); 0 nothing (hidden)
void gk_gauge()
{
    int g;
    g = 0;
    if (gk_burnout > 0)
    {
        g = 3000 + gk_pct(gk_burnout, gk_burnout_frames());
    }
    else if (gk_ability > 0)
    {
        g = 2000 + gk_pct(gk_ability, gk_ability_frames());
    }
    else if (gk_lw_charge > 0)
    {
        g = 1000 + gk_lw_charge * 100 / gk_lw_full();
    }
    WorkModule(0, (float)g + 0, 0x0f000313);
}

// time left as 1 - 99 (100 is the meter's "full / ready" frame: only the charge's)
int gk_pct(int left, int all)
{
    int v;
    v = left * 100 / all;
    if (v < 1)
    {
        v = 1;
    }
    if (v > 99)
    {
        v = 99;
    }
    return v;
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
// v3: one charge for all three smashes (the user): t is ignored
int gk_sm_get(int t)
{
    return gk_smash;
}

void gk_sm_set(int t, int v)
{
    gk_smash = v;
}

// v3: the charge's effect size: 1 at 0 to gk_smash_fx_max() at full, linear
float gk_sm_size(int v)
{
    return 1.0f + (gk_smash_fx_max() - 1.0f) * (float)v / (float)gk_smash_full();
}

// v3: the hold's effects (its effect scripts' own at size 0, gekkouga_build.py). Every 5 frames the charge's dust
// (0x1000019, PtcCommonRunSmoke) and sparkle (0x1000010, PtcCommonSmashFlashS: at the sword (forward) / over him (up) /
// at his feet (down)): aerial chain v1 package (the user: "smash attacks charging not use giant effects for the dust or
// sparkle"): at their vanilla size 1 (v3 - burn v2.3: x the charge's size, 1 - 5); every 10 frames his water sword
// (0x3300007, both hands for up / down) made again at the charge's size (still growing: a live effect can't be resized).
float gk_sm_dust_size() { return 1.0f; }
void gk_sm_fx(int t, int v, int first)
{
    float sz;
    sz = gk_sm_size(v);
    if (first || v % 5 == 0)
    {
        EffectModule(0x2710, 0x1000019, 0, -2.0f, 0, 0, 0, 0, 0, gk_sm_dust_size(), 0, 0, 0, 0, 0, 0, 0);
        if (t == 0x1)
        {
            EffectModule(0x2712, 0x1000010, 25, 0, -5.5f, 0, 0, 0, 0, gk_sm_dust_size(), 0);
        }
        else if (t == 0x2)
        {
            EffectModule(0x2710, 0x1000010, 0, 0, 18.0f, 0, 0, 0, 0, gk_sm_dust_size(), 0, 0, 0, 0, 0, 0, 0);
        }
        else
        {
            EffectModule(0x2710, 0x1000010, 0, 0, 3.0f, 0, 0, 0, 0, gk_sm_dust_size(), 0, 0, 0, 0, 0, 0, 0);
        }
    }
    if (first || v % 10 == 0)
    {
        EffectModule(0x2723, 0x3300007, 0x1, 0x1);
        EffectModule(0x2712, 0x3300007, 25, -0.00001f, 0, 0, 180.0f, -90.0f, 0, sz, 0x1);
        if (t != 0x1)
        {
            EffectModule(0x2712, 0x3300007, 24, -0.00001f, 0, 0, 180.0f, -90.0f, 0, sz, 0x1);
        }
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
        gk_hold_first = 0x1;              // the hold's effects start at the kept charge's size
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
    v = gk_sm_get(t);
    gk_sm_fx(t, v, gk_hold_first);
    gk_hold_first = 0;
    v = v + 1;
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
    gk_trail_tick(cur);                   // burn v2: its fire trail at the smash's hit
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

// ---- skeleton v1: a reset of the battle (the executable's clear-all count changed: training reset, restart): the
// ability / burnout ended, the chain, the kept charges 0 (as at the match's start)
void gk_reset()
{
    if (gk_ability > 0 || gk_alive != 0)
    {
        gk_end_ability(0);
        BattleObject(0xa, 0x1);           // the name tag back
    }
    if (gk_burnout > 0)
    {
        gk_burnout = 0;
        gk_overlay_off();
    }
    gk_chain = 0;
    gk_lw_charge = 0;
    gk_smash = 0;
    gk_sk_req_t = 0;
    WorkModule(0, 0 + 0, 0x0f00030f);
    gk_tr_req_t = 0;
    gk_tr_done = 0;
    gk_tr_clear();
    gk_ac_end();
}

// ---- skeleton v1: Shadow Sneak (SpecialS 0x153) without the vanish and the teleport: its per-frame (global16, in
// place of func_2291): the start-up (0x16000006 frames) and the shadow's time (0x16000007) as vanilla, but he stays
// where he is, seen and hittable; where he'd have reappeared (the shadow's place: his instance floats 0x31 / 0x32) the
// Running Skeleton is made, and he ends the move (Wait / Fall)
void gk_ss_tick()
{
    WorkModule(0x9, 0x10000085);
    if (WorkModule(0x6, 0x10000085) >= WorkModule(0x6, 0x16000006))
    {
        WorkModule(0x9, 0x11000002);
        if (WorkModule(0x6, 0x11000002) >= WorkModule(0x6, 0x16000007))
        {
            gk_sk_spawn(WorkModuleF(0, 0x31), WorkModuleF(0, 0x32));
            if (global18 == 0)
            {
                func_16(0, 0);            // Wait
            }
            else
            {
                func_16(0xe, 0);          // Fall
            }
        }
    }
}

// the request (his VAR_15 = 1, VAR_16 / 17 the place, VAR_18 his facing: the executable copies them into the new
// skeleton as it claims it) and the skeleton made (article 8, one at a time: with one out, nothing is made and the
// request lapses)
void gk_sk_spawn(float x, float y)
{
    int r;
    WorkModule(0, 1.0f + 0, 0x0f00030f);
    WorkModule(0, x + 0, 0x0f000310);
    WorkModule(0, y + 0, 0x0f000311);
    WorkModule(0, PostureModuleF(0) + 0, 0x0f000312);
    gk_sk_req_t = gk_sk_req_frames();
    r = ArticleModule(0x2710, 0x8);
    WorkModule(0, (float)r + 0, 0x0f000317);   // diag: the generate's result (the TEST_ONLY exe logs it: S4GF gen=)
}

// ---- burn v2: the smashes' fire trails (fighters/gekkouga/README.md "Burn v2"). At each smash's main hit (attacks4 13,
// attackhi4 18, attacklw4 16: its game script) a fire trail (article 9, weapon kind 0x1A3: weapons/firetrail.c) at his
// place, and one at each clone's (they play his smash with him): request k in his VAR_4k (type: 1 forward, 2 up, 3 down),
// VAR_4k+1 / +2 the place, VAR_4k+3 his facing; the executable copies one into each new trail as it claims it
int gk_tr_frame(int t)
{
    if (t == 0x1)
    {
        return 13;
    }
    if (t == 0x2)
    {
        return 18;
    }
    return 16;
}

int gk_tr_type(int t)
{
    if (t == 0x1)
    {
        return 0x1;
    }
    if (t == 0x2)
    {
        return 0x2;
    }
    return 0x3;
}

void gk_tr_clear()
{
    WorkModule(0, 0 + 0, 0x0f000300);
    WorkModule(0, 0 + 0, 0x0f000304);
    WorkModule(0, 0 + 0, 0x0f000308);
}

void gk_tr_ask(int k, int type, float x, float y)
{
    int r;
    WorkModule(0, (float)type + 0, 0x0f000300 + k * 4);
    WorkModule(0, x + 0, 0x0f000301 + k * 4);
    WorkModule(0, y + 0, 0x0f000302 + k * 4);
    WorkModule(0, PostureModuleF(0) + 0, 0x0f000303 + k * 4);
    r = ArticleModule(0x2710, 0x9);
}

void gk_trail_tick(int cur)
{
    int k;
    int type;
    if (gk_tr_done == global4 || global18 != 0)
    {
        return;
    }
    if (MotionModuleF(0x1) < (float)gk_tr_frame(cur))
    {
        return;
    }
    gk_tr_done = global4;
    type = gk_tr_type(cur);
    gk_tr_ask(0, type, PostureModuleF(0x1), PostureModuleF(0x2));
    k = 0x1;
    if ((gk_alive & 0x1) && gk_lfall == 0)
    {
        gk_tr_ask(k, type, gk_cx(0x1), gk_cy(0x1));
        k += 1;
    }
    if ((gk_alive & 0x2) && gk_rfall == 0)
    {
        gk_tr_ask(k, type, gk_cx(0x2), gk_cy(0x2));
    }
    gk_tr_req_t = gk_tr_req_frames();
}

// ---- aerial chain v1 (fighters/gekkouga/README.md "Aerial chain v1"; the user: "make Greninja's aerials chain like his
// smash attacks do, but only if it hits an opponent"). An aerial (AttackAir 0x34: neutral / forward / back / up / down,
// kind 1 - 5 = its motion 0x68 - 0x6C) that hits an opponent (its attack's hurtbox hits since it started: AttackModule
// 0x2727 kind 2; a shield doesn't count; a clone's copy of it landing counts: the exe's VAR_22, which can't tell a shield)
// can be cancelled, from the frame after the hit (not in hitlag) to its end, into a different aerial: an attack input
// (the stick or the C-stick: the game's own air attack kind, ControlModule 0x10) of one not used yet in this chain
// re-enters 0x34 (that aerial, picked by func_311 as any aerial). Each aerial once a chain; the chain ends on anything but
// an aerial (landing, a special, an air dodge, being hit, a ledge grab, a jump) or after all five. Landing lag, fast fall,
// drift: the game's. Smash chains unaffected.
int gk_ac_hit_kinds() { return 0x2; }        // AttackModule 0x2727's kinds: 2 a hurtbox (4 a shield: not counted)

void gk_ac_end()
{
    gk_ac_used = 0;
    gk_ac_kind = 0;
    gk_ac_hit = 0;
    gk_ac_req = 0;
}

// the aerial's start (func_2382, after func_314 picked its motion into 0x11000002)
void gk_ac_start()
{
    int k;
    k = WorkModule(0x6, 0x11000002) - 0x67;
    if (k < 0x1 || k > 0x5)
    {
        k = 0;
    }
    if (gk_ac_req == 0)
    {
        gk_ac_used = 0;                   // not a chain's: a new chain
    }
    gk_ac_req = 0;
    gk_ac_kind = k;
    if (k != 0)
    {
        gk_ac_used = gk_ac_used | (1 << k);
    }
    gk_ac_hit = 0;
    AttackModule(0x2724);                 // its "hit since it started" from 0
}

// a clone's copy of his aerial landed (the exe's VAR_22: gk_clone_hitlag)
void gk_ac_clone_hit()
{
    if (global4 == 0x34 && gk_ac_hit == 0)
    {
        gk_ac_hit = 0x1;
    }
}

// the aerial's loop (func_2383, every frame): 1 = cancelled into the next aerial
int gk_ac_try()
{
    int k;
    if (gk_ac_hit > 0)
    {
        gk_ac_hit += 1;
    }
    else if (AttackModule(0x2727, gk_ac_hit_kinds()))
    {
        gk_ac_hit = 0x1;                  // hit: the window opens the next frame
    }
    if (gk_ac_hit < 0x2 || StopModule(0x1) || global18 != 0x2)
    {
        return 0;
    }
    if ((global24 & 0x1) == 0)
    {
        return 0;
    }
    k = ControlModule(0x10);
    if (k < 0x1 || k > 0x5)
    {
        k = 0x1;                          // func_311 plays a neutral air for any other answer
    }
    if ((gk_ac_used & (1 << k)) != 0)
    {
        return 0;                         // used in this chain already
    }
    gk_ac_req = 0x1;
    func_16(0x34, 0x1);
    return 0x1;
}

// diag: VAR_20's bits from 256 (the exe's S4GF logs a change): 256 x the aerial now (0 - 5), 2048 hit seen, 4096 the window
// open, 8192 x the chain's used bits (1 << kind: 2 neutral ... 32 down, so 16384 - 524288)
int gk_ac_diag()
{
    int d;
    d = gk_ac_kind * 256;
    if (gk_ac_hit > 0)
    {
        d = d | 2048;
    }
    if (gk_ac_hit >= 0x2)
    {
        d = d | 4096;
    }
    return d + gk_ac_used * 8192;
}

// ---- clone fixes v2 diag (the user: the clones "follow grounded movement incorrectly"): every 10 frames while he is on
// the ground with clones out, his VAR_23 = the reasons x 10000 + (the left clone's X - its target + 50) x 100 + (the
// right one's + 50) (target: his X + its offset; each rounded, clamped to +- 49; a missing clone 99), and flags bit
// 1048576 toggled, so the TEST_ONLY exe's S4GF line logs it (gen=); the reasons (gk_cl_why) then start over
int gk_cl_err(int id)
{
    float d;
    if ((gk_alive & id) == 0)
    {
        return 99;
    }
    d = gk_cx(id) - PostureModuleF(0x1) - gk_off(id);
    if (d > 49.0f)
    {
        d = 49.0f;
    }
    if (d < -49.0f)
    {
        d = -49.0f;
    }
    if (d < 0)
    {
        return 50 - (int)(0.5f - d);
    }
    return 50 + (int)(d + 0.5f);
}

int gk_cl_diag()
{
    if (gk_ability <= 0 || gk_alive == 0 || StatusModule(0x1) != 0)
    {
        return (gk_cl_t & 0x1) * 1048576;
    }
    if (gk_lfall > 2)
    {
        gk_cl_why = gk_cl_why | 0x10;
    }
    if (gk_rfall > 2)
    {
        gk_cl_why = gk_cl_why | 0x20;
    }
    gk_cl_t += 1;
    if (gk_cl_t % 10 == 0)
    {
        WorkModule(0, (float)(gk_cl_why * 10000 + gk_cl_err(0x1) * 100 + gk_cl_err(0x2)) + 0, 0x0f000317);
        gk_cl_why = 0;
    }
    return ((gk_cl_t / 10) & 0x1) * 1048576;
}
