
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
int gk_sk_live;        // skeleton v1.6: frames a skeleton of his still counts as running (its heartbeat: bit 4 of VAR_30)
int gk_alive;          // clones out: 1 the left-spawned one (article 6), 2 the right-spawned one (article 7)
float gk_off_l;        // the left-spawned clone's X offset from him (world)
float gk_off_r;        // the right-spawned clone's
int gk_seq;            // frames since the ability started (the clones are made at 0 and 3)
int gk_swap_cd;        // frames before another swap
int gk_smash;          // v3: the smash charge kept (frames, 0 - gk_smash_full()), one for all three smashes
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
int gk_tc_used;        // tilt chain v1: the tilts used in this chain (bit 1 << kind: 2 forward, 4 up, 8 down)
int gk_tc_kind;        // the move now: 0 none, 1 forward / 2 up / 3 down tilt, 4 a jab (1 - 3)
int gk_tc_hit;         // frames since this move hit an opponent (0: not yet)
int gk_tc_req;         // 1: the next tilt start is a chain's (the chain kept)
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
int gk_sk_beat_miss() { return 2; }       // skeleton v1.6: frames without its heartbeat before it counts as gone
float gk_sk_dist() { return 36.0f; }      // skeleton v1.6: the shadow's / skeleton's fixed distance ahead of him (his
                                          // instance float 0x35; tools/gekkouga_clone_cave.py SK_DIST, the hold's cap)
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
    gk_svi(61, 0);                        // clone fix v3 diag: no removal reason written this frame yet
    gen = (int)(WorkModuleF(0, 0x0f00030e) + 0.5f);   // skeleton v1: the executable's clear-all count & 7 (VAR_14)
    if (gk_gen_seen && gen != gk_gen)
    {
        gk_reset();                       // a training reset / restart / new match: his state starts over
    }
    gk_gen = gen;
    gk_gen_seen = 0x1;
    gk_sk_heartbeat();
    gk_sk_queue();                        // clone articles v1: the clones' skeletons, one a frame after his
    gk_sh_tick();                         // ... and their shurikens' claim bits
    gk_sh_report();                       // clone fix v3 diag: a shuriken copy's report (before the heartbeat's clear)
    if (gk_sk_req_t > 0)
    {
        gk_sk_req_t -= 1;
        if (gk_sk_req_t == 0)
        {
            WorkModule(0, 0 + 0, 0x0f00030f);   // not claimed: no skeleton was made (one is out already)
            gk_svi(15, 0);
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
    if (st != 0x25 && st != 0x28 && st != 0x29 && st != 0x2a)
    {
        gk_tc_end();                      // tilt chain v1: anything but a jab (1 - 3) or a tilt ends the chain
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
            gk_why(500, 0);               // clone fix v3 diag: ended by his KO / rebirth status (300: the timer)
        }
        if (gk_burnout > 0)
        {
            gk_burnout = 0;
            gk_overlay_off();
        }
        gk_chain = 0;
        gk_lw_charge = 0;                 // aligned kick v1 package (the user: "the clone charge gauge should reset when
                                          // Greninja is KO'd"): the down special's charge (and its gauge / ready blink)
        gk_smash = 0;                     // clone articles v1 package (the user: a KO also clears the stored smash charge):
        gk_sm_auto = 0;                   // the store, its auto release, a chain asked for; the split clones' own stores
        gk_chain_req = 0;
        gk_bsi(0x1, 10, 0);
        gk_bsi(0x2, 10, 0);
    }
    if (st == 0x14f)
    {
        gk_lw_charge = 0;                 // the match's start (Entry): every kept charge from 0
        gk_smash = 0;
    }
    if (st != 0x161 && (StatusModule(0x1) == 0 || gk_on_ledge(st)))
    {
        gk_svi(9, 0);                     // aligned kick v1: once an airtime (landed, or on a ledge)
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
    flags = flags | gk_tc_diag();         // tilt chain v1 diag (2097152 + the same fields, in a jab / tilt)
    flags = flags | gk_cl_diag();         // clone fixes v2 diag (1048576 toggled: an S4GF line with VAR_23)
    flags = flags ^ (gk_vi(62) * 1048576); // clone fix v3 diag: ... and flipped at each shuriken copy's report
    if (gk_ability > 0)
    {
        flags = flags | gk_vi(4);         // v4 diag: 64 / 128 a clone about to be made (next frame; gk_gen_req)
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
    if (gk_ability > 0 && gk_rg_try())
    {
        return;                           // aligned kick v1: shield + special while split: the regroup
    }
    sy = ControlModuleF(0x1);
    if (sy > -0.3f)
    {
        return;                           // not a down special (neutral / side / up specials as normal)
    }
    sx = ControlModuleF(0);
    if (gk_ability > 0 && gk_abs(sx) <= 0.25f)
    {
        if (gk_vi(60) == 0)
        {
            gk_lw_eat();                  // clone fix v3: the kick locked (the activating press, the first 10 frames):
        }                                 // this press is dropped, not buffered for later
        return;                           // aligned kick v1: no left / right: the game's down special input goes on
    }                                     // (func_43 / func_58 ... -> gk_lw_press -> gk_ak_try, when he can act)
    gk_lw_eat();                          // no down special status
    if (gk_ability <= 0)
    {
        return;                           // burnout: down special disabled
    }
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
    if ((gk_alive & id) == 0 || (gk_det && gk_vi(8) == 0))
    {
        return;
    }
    ox = PostureModuleF(0x1);
    oy = PostureModuleF(0x2);
    cx = gk_cx(id);
    cy = gk_cy(id);
    if (gk_vi(8) != 0)
    {
        gk_swap_free(id, ox, oy, cx, cy); // aligned kick v1: free clones: places and momentum exchanged
        return;
    }
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
    gk_fx_flip();                         // the clones' following effects faded (the user: a swap at an aerial's landing
    gk_last_oy = cy;                      // left its effect on the clone)
    gk_cl_why_or(0x4);
    gk_hn = 0;                            // clone delay: his old places mean nothing now (both offsets changed): the
    gk_swap_cd = 10;                      // clones go on from his new place (held for their delay, then delayed)
}

// ---- the input sites' down special (func_43, func_58, func_675, func_1999): 1 = entered the stance
int gk_lw_press()
{
    if (gk_ability > 0)
    {
        return gk_ak_try();               // aligned kick v1 (down special with no left / right during the ability)
    }
    if (gk_burnout > 0)
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

// a special press dropped: Buffer_Clear (specials) for this fighter, and this frame's special bits (the status loop
// reads them after his frame hook)
void gk_lw_eat()
{
    WorkModule(0, 32.0f + 0, 0x0f0003c9);
    global24 = global24 - (global24 & 0xf000);
}

// clone fix v3 (the user: "make it so the use of down special just activates the clones ... disable clone kick for the
// first 10 frames of clones existing"): slot 60 the kick armed: 0 from the activation; 1 once gk_ak_lock() frames of the
// ability have run AND special is not held (the activating press let go). Until then gk_ak_try refuses and gk_input
// drops any down special press (gk_lw_eat), so neither the activating press (held or buffered) nor a press in the lockout
// starts the kick later; a fresh press after it does.
int gk_ak_lock() { return 11; }          // gk_seq after the ability's frame: the left clone is made on its 2nd frame, so a
                                        // press is refused through its frame 11 (the clones' first 10) and taken from 12

void gk_ak_arm()
{
    if (gk_vi(60) == 0 && gk_seq >= gk_ak_lock() && ControlModule(0x2712, 0x1) == 0)
    {
        gk_svi(60, 0x1);
    }
}

void gk_activate()
{
    gk_lw_charge = 0;
    gk_svi(60, 0);                        // clone fix v3: the kick locked; the activating press used up (one press,
    gk_lw_eat();                          // one action: not buffered on into the kick)
    gk_ability = gk_ability_frames();
    gk_alive = 0;
    gk_off_l = -gk_gap();
    gk_off_r = gk_gap();
    gk_seq = 0;
    gk_svi(0, 0);                         // (gk_fx_t)
    gk_det = 0;
    gk_last_oy = PostureModuleF(0x2);
    gk_hn = 0;
    gk_hcopy = 0;
    gk_svi(1, 0);                         // (gk_cursor_t)
    gk_svi(8, 0);                         // aligned kick v1: formation, the kick not used
    gk_svi(9, 0);
    EffectModule(0x2723, 0x10000bd, 0x1, 0x1);
}

void gk_ability_update()
{
    int t;
    // v4: each clone is requested a frame before it is made (flags bit 64 / 128: the TEST_ONLY exe logs the request
    // before the generate runs, and its result the frame after)
    t = 0;                                // (gk_gen_req)
    if (gk_seq == 0)
    {
        t = 0x40;
    }
    if (gk_seq == 3)
    {
        t = 0x80;
    }
    gk_svi(4, t);
    if (gk_seq == 1)
    {
        gk_spawn(0x1);
    }
    if (gk_seq == 4)
    {
        gk_spawn(0x2);
    }
    gk_seq += 1;
    gk_ak_arm();                          // clone fix v3: the kick's lockout
    gk_clone_hitlag();
    gk_check_hit();
    gk_heartbeat();
    gk_land_fx();
    if (gk_vi(8) != 0)
    {
        gk_free_frame();                  // aligned kick v1: kicking / split / regrouping: their own movement
    }
    else
    {
        gk_physics();
    }
    gk_channel();
    gk_shapes_update();
    t = gk_vi(1);                         // (gk_cursor_t)
    if (t <= 0)
    {
        BattleObject(0xa, 0);             // his player cursor (name tag) hidden: SET_CURSOR(0)'s op (Rebirth shows it with 1)
        t = 60;
    }
    gk_svi(1, t - 1);
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
            gk_cl_why_or(id);             // clone fixes v2 diag: a wall held it (1 the left clone, 2 the right)
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
        gk_cl_why_or(0xc);
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
    flags = flags | gk_vi(13) * 256;      // aligned kick v1 package: the effects' epoch (a change: they fade theirs)
    flags = flags | gk_vi(57) * 512;      // clone articles v1: their shuriken copies waiting for their claim (1 / 2)
    WorkModule(0, gk_lx + 0, 0x0f000318);
    WorkModule(0, gk_ly + 0, 0x0f000319);
    WorkModule(0, gk_rx + 0, 0x0f00031a);
    WorkModule(0, gk_ry + 0, 0x0f00031b);
    if (gk_vi(8) != 0)
    {
        flags = flags | 0x80;             // aligned kick v1: free: VAR_28 / VAR_29 each clone's own motion (gk_fpack)
        WorkModule(0, (float)gk_fpack(0x1) + 0, 0x0f00031c);
        WorkModule(0, (float)gk_fpack(0x2) + 0, 0x0f00031d);
        WorkModule(0, 4747000.0f + (float)flags, 0x0f00031f);
        return;
    }
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
    gk_tc_clone_hit();                    // tilt chain v1: ... of his jab / tilt
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
// 1 = the last generate's answer otherwise. Clone fix v3: 500 his KO / rebirth status ended it (300 now only the
// timer's end), 600 a battle reset; a heartbeat lost (100 / 400 + id) also gives the clone's last place (gk_why_at:
// + 1000 x (X/10 + 40 + 81 x (Y/10 + 40)), each 0 - 80); slot 61 = 1 the frame a reason is written (the periodic diag
// line, gk_cl_diag, doesn't overwrite it then)
void gk_why(int code, int id)
{
    WorkModule(0, (float)(code + id) + 0, 0x0f000317);
    gk_svi(61, 0x1);
}

int gk_why_q(float v)
{
    int q;
    q = (int)(v / 10.0f + 40.5f);
    if (v < -405.0f)
    {
        q = 0;
    }
    if (q > 80)
    {
        q = 80;
    }
    return q;
}

void gk_why_at(int code, int id, float x, float y)
{
    gk_why(code + 1000 * (gk_why_q(x) + 81 * gk_why_q(y)), id);
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
        gk_why_at(400, id, gk_cx(id), gk_cy(id));
        return;
    }
    gk_why_at(100, id, gk_cx(id), gk_cy(id));
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
    gk_svi(8, 0);                         // aligned kick v1: the clones' mode
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
    int t;
    if (gk_lw_charge < gk_lw_full())
    {
        return;
    }
    t = gk_vi(0);                         // (gk_fx_t)
    if (t > 0)
    {
        gk_svi(0, t - 1);
        return;
    }
    gk_svi(0, 45);                         // v6: no sparkle over his head (the panel's gauge blinks "KO" when ready)
}

// ---- the charge stance (SpecialLw 0x155, his old counter: no counter shape now)
void gk_lw_main()
{
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
    int t;
    if (gk_lw_charge < gk_lw_full())
    {
        gk_lw_charge += 1;
    }
    gk_bar();
    if (MotionModuleF(0x1) >= (float)gk_lw_hold_frame())
    {
        t = gk_vi(0) + 1;                 // (gk_fx_t)
        gk_svi(0, t);
        if (t >= 20)
        {
            gk_svi(0, 0);
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
    }
    else if (global19 == 0x2 && global18 == 0)
    {
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
        gk_svi(5, 0x1);                   // the hold's effects start at the kept charge's size (gk_hold_first)
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
    int first;
    WorkModule(0xa, 0x11000005);
    t = gk_sm_type(global4);
    if (t == 0)
    {
        return;
    }
    v = gk_sm_get(t);
    first = gk_vi(5);                     // (gk_hold_first)
    gk_sm_fx(t, v, first);
    gk_svi(5, 0);
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
        gk_why(600, 0);                   // clone fix v3 diag: ended by a battle reset (the clear-all count)
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
    gk_sk_live = 0;
    WorkModule(0, 0 + 0, 0x0f00030f);
    gk_tr_req_t = 0;
    gk_tr_done = 0;
    gk_tr_clear();
    gk_ac_end();
    gk_tc_end();
}

// ---- skeleton v1: Shadow Sneak (SpecialS 0x153) without the vanish and the teleport: its per-frame (global16, in
// place of func_2291): the start-up (0x16000006 frames) and the shadow's time (0x16000007) as vanilla, but he stays
// where he is, seen and hittable; where he'd have reappeared (the shadow's place: his instance floats 0x31 / 0x32) the
// Running Skeleton is made, and he ends the move (Wait / Fall)
void gk_ss_tick()
{
    WorkModule(0x9, 0x10000085);
    gk_ss_shadow();
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

// skeleton v1.6 (the user: "always spawns from this distance, regardless of if the button is held"): the shadow's
// distance ahead of him (instance float 0x35: the executable's slot 13 places the shadow, 0x31 / 0x32, from it every
// frame of the hold and of SpecialS) goes on from where the hold left it (2 + 1.2 a frame, capped at gk_sk_dist() by the
// executable: feature skdist) to gk_sk_dist() evenly by SpecialS frame 0x16000006 + 0x16000007 - 2 (20 with his params:
// the skeleton is made at 21 from the shadow's place, 0x31 / 0x32); so a tap and a hold both end there
void gk_ss_shadow()
{
    float d;
    int left;
    d = WorkModuleF(0, 0x35);
    if (d < gk_sk_dist())
    {
        left = WorkModule(0x6, 0x16000006) + WorkModule(0x6, 0x16000007) - 0x1 - WorkModule(0x6, 0x10000085);
        if (left < 0x1)
        {
            left = 0x1;
        }
        d = d + (gk_sk_dist() - d) / (float)left;
        if (d > gk_sk_dist())
        {
            d = gk_sk_dist();
        }
        WorkModule(0, d + 0, 0x35);
    }
}

// skeleton v1.6: his running skeletons' heartbeat (weapons/skeleton.c sk_beat: bit 4 of his VAR_30, every frame) taken
// out of VAR_30 every frame (before the clones' heartbeat, gk_heartbeat, reads the rest); seen: a skeleton runs for
// gk_sk_beat_miss() more frames
void gk_sk_heartbeat()
{
    int beat;
    beat = (int)(WorkModuleF(0, 0x0f00031e) + 0.5f);
    if (beat & 0x4)
    {
        WorkModule(0, (float)(beat - 0x4) + 0, 0x0f00031e);
        gk_sk_live = gk_sk_beat_miss();
    }
    else if (gk_sk_live > 0)
    {
        gk_sk_live -= 1;
    }
}

// skeleton v1.6 (the user: "disable side special from being used while a Skeleton is alive"): his side special's input
// (func_2379, the hold's start: the only way in, the vanilla side special transition is off every frame there) does
// nothing while a skeleton of his runs (its heartbeat, gk_sk_live) or one is asked for and not claimed yet (gk_sk_req_t);
// on the ground and in the air. "Alive" ends at its explosion / its smoke at 0 HP, not at its removal (its sound's end)
int gk_ss_allowed()
{
    if (gk_sk_live > 0 || gk_sk_req_t > 0)
    {
        return 0;
    }
    return 0x1;
}

// the request (his VAR_15 = 1, VAR_16 / 17 the place, VAR_18 his facing: the executable copies them into the new
// skeleton as it claims it) and the skeleton made (article 8, one at a time: with one out, nothing is made and the
// request lapses)
void gk_sk_spawn(float x, float y)
{
    int r;
    gk_sk_stack(x, y);                    // clone articles v1: his clones' skeletons queued (stacked on his)
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

void gk_tr_ask(int k, int type, float x, float y, float lr)
{
    int r;
    WorkModule(0, (float)type + 0, 0x0f000300 + k * 4);
    WorkModule(0, x + 0, 0x0f000301 + k * 4);
    WorkModule(0, y + 0, 0x0f000302 + k * 4);
    WorkModule(0, lr + 0, 0x0f000303 + k * 4);
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
    gk_tr_ask(0, type, PostureModuleF(0x1), PostureModuleF(0x2), PostureModuleF(0));
    gk_tr_req_t = gk_tr_req_frames();
    if (gk_vi(8) != 0)
    {
        return;                           // aligned kick v1: free clones make their own smashes' trails (gk_fatk)
    }
    k = 0x1;
    if ((gk_alive & 0x1) && gk_lfall == 0)
    {
        gk_tr_ask(k, type, gk_cx(0x1), gk_cy(0x1), PostureModuleF(0));
        k += 1;
    }
    if ((gk_alive & 0x2) && gk_rfall == 0)
    {
        gk_tr_ask(k, type, gk_cx(0x2), gk_cy(0x2), PostureModuleF(0));
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

// ---- tilt chain v1 (fighters/gekkouga/README.md "Tilt chain v1"; the user: "please make jab chain into tilts (except
// rapid jab) and have tilts chain into tilts"; on hit only, each tilt once a chain). A jab (Attack 0x25: jab 1 - 3; not
// the rapid jab, Attack100 0x26, nor its finisher) or a tilt (AttackS3 0x28 / AttackHi3 0x29 / AttackLw3 0x2A) that hits
// an opponent (AttackModule 0x2727 kind 2, as the aerial chain; a shield doesn't count; a clone's copy landing does: the
// exe's VAR_22) can be cancelled, from the frame after the hit (not in hitlag) to its end, on the ground, into a tilt not
// used yet in this chain: the game's tilt input (global24 0x2 forward / 0x4 up / 0x8 down, checked up / down / forward as
// func_43 does; a smash input, 0x10 / 0x20 / 0x40, is left to the game). Each tilt once a chain; a jab starting it isn't a
// use. The chain ends on anything but a jab or a tilt (moving, jumping, shielding, being hit, specials, smashes, aerials)
// or after all three. Smash / aerial chains unaffected.
void gk_tc_end()
{
    gk_tc_used = 0;
    gk_tc_kind = 0;
    gk_tc_hit = 0;
    gk_tc_req = 0;
}

// the move's start (its status main: k 1 forward / 2 up / 3 down tilt, 4 a jab)
void gk_tc_start(int k)
{
    if (gk_tc_req == 0)
    {
        gk_tc_used = 0;                   // not a chain's: a new chain
    }
    gk_tc_req = 0;
    gk_tc_kind = k;
    if (k >= 0x1 && k <= 0x3)
    {
        gk_tc_used = gk_tc_used | (1 << k);
    }
    gk_tc_hit = 0;
    AttackModule(0x2724);                 // its "hit since it started" from 0
}

// a clone's copy of his jab / tilt landed (the exe's VAR_22: gk_clone_hitlag)
void gk_tc_clone_hit()
{
    if ((global4 == 0x25 || global4 == 0x28 || global4 == 0x29 || global4 == 0x2a) && gk_tc_kind != 0 && gk_tc_hit == 0)
    {
        gk_tc_hit = 0x1;
    }
}

// the tilt for this frame's input (0 none; a smash input: none, the game's)
int gk_tc_input()
{
    if ((global24 & 0x70) != 0)
    {
        return 0;
    }
    if (global24 & 0x4)
    {
        return 0x2;
    }
    if (global24 & 0x8)
    {
        return 0x3;
    }
    if (global24 & 0x2)
    {
        return 0x1;
    }
    return 0;
}

// the move's loop (every frame, first): 1 = cancelled into the next tilt
int gk_tc_try()
{
    int k;
    if (gk_tc_kind == 0)
    {
        return 0;
    }
    if (gk_tc_hit > 0)
    {
        gk_tc_hit += 1;
    }
    else if (AttackModule(0x2727, gk_ac_hit_kinds()))
    {
        gk_tc_hit = 0x1;                  // hit: the window opens the next frame
    }
    if (gk_tc_hit < 0x2 || StopModule(0x1) || global18 != 0)
    {
        return 0;
    }
    k = gk_tc_input();
    if (k == 0 || (gk_tc_used & (1 << k)) != 0)
    {
        return 0;                         // no tilt input, or that tilt used in this chain already
    }
    gk_tc_req = 0x1;
    func_16(0x27 + k, 0x1);               // 0x28 forward / 0x29 up / 0x2A down tilt
    return 0x1;
}

// diag: in a jab / tilt, VAR_20's aerial chain fields hold the tilt chain's, with 2097152 on: 256 x the move (1 forward,
// 2 up, 3 down tilt, 4 jab), 2048 hit seen, 4096 the window open, 8192 x the used bits (2 / 4 / 8)
int gk_tc_diag()
{
    int d;
    if (gk_tc_kind == 0)
    {
        return 0;
    }
    d = 2097152 + gk_tc_kind * 256 + gk_tc_used * 8192;
    if (gk_tc_hit > 0)
    {
        d = d | 2048;
    }
    if (gk_tc_hit >= 0x2)
    {
        d = d | 4096;
    }
    return d;
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
    int t;
    if (gk_ability <= 0 || gk_alive == 0)
    {
        gk_svi(3, 0);                     // (gk_cl_t)
        gk_svi(2, 0);                     // (gk_cl_why)
        return 0;
    }
    if (StatusModule(0x1) != 0)
    {
        return ((gk_vi(3) / 10) & 0x1) * 1048576;   // in the air: no line, the bit as it was
    }
    if (gk_lfall > 2)
    {
        gk_cl_why_or(0x10);
    }
    if (gk_rfall > 2)
    {
        gk_cl_why_or(0x20);
    }
    t = gk_vi(3) + 1;                     // (gk_cl_t)
    gk_svi(3, t);
    if (t % 10 == 0 && gk_vi(61) == 0)  // (clone fix v3: not over a clone's removal reason written this frame)
    {
        WorkModule(0, (float)(gk_vi(2) * 10000 + gk_cl_err(0x1) * 100 + gk_cl_err(0x2)) + 0, 0x0f000317);
        gk_svi(2, 0);                     // (gk_cl_why)
    }
    return ((t / 10) & 0x1) * 1048576;
}

// ===================================================================
// New_Var slots (aligned kick v1: his MSC had 127 of 128 globals). Each fighter has 64 slot variables of its own
// (0x0F000380 + i, docs/acmd-extra-commands.md "New_Var": floats, whole numbers exact, read 0 until written, cleared
// with his VAR_n at a KO); his MSC keeps state there instead of in globals (fighters/gekkouga/README.md "Aligned kick
// v1", the slot table). 0 - 15 his own: 0 gk_fx_t, 1 gk_cursor_t, 2 gk_cl_why, 3 gk_cl_t, 4 gk_gen_req, 5 gk_hold_first
// (moved out of the globals), 8 the clones' mode (0 formation, 1 the aligned kick, 2 split, 3 regrouping), 9 the kick
// used this airtime, 10 the kick's clock, 11 its variant (1 tapped, 2 held), 12 the regroup's clock, 13 the clones' effects
// epoch (flags 256), 14 his situation last frame (clone articles v1: 6 / 7, 15, 57 - 59: there; clone fix v3: 60 the
// kick armed, 61 a removal reason written this frame, 62 the shuriken reports' parity); 16 x b + k body b's
// (1 the left-spawned clone, 2 the right-spawned one, 3 him): k 0 action, 1 frames in it, 2 motion kind, 3 its start
// frame, 4 the command's seq, 5 facing, 6 X speed, 7 Y speed (his; the clones' are gk_lvy / gk_rvy), 8 flight frames
// left, 9 air jumps used, 10 smash charge, 11 smash chain, 12 tilted (the kick), 13 aux (smash type + 8 x auto / the
// aerial / the landing lag), 14 / 15 the regroup's start X / Y
// ===================================================================
int gk_vi(int i)
{
    return (int)WorkModuleF(0, 0x0f000380 + i);
}

void gk_svi(int i, int v)
{
    WorkModule(0, (float)v + 0, 0x0f000380 + i);
}

float gk_bv(int b, int k)
{
    return WorkModuleF(0, 0x0f000380 + 16 * b + k);
}

int gk_bvi(int b, int k)
{
    return (int)WorkModuleF(0, 0x0f000380 + 16 * b + k);
}

void gk_bs(int b, int k, float v)
{
    WorkModule(0, v + 0, 0x0f000380 + 16 * b + k);
}

void gk_bsi(int b, int k, int v)
{
    WorkModule(0, (float)v + 0, 0x0f000380 + 16 * b + k);
}

void gk_cl_why_or(int bits)
{
    int w;
    w = gk_vi(2);
    gk_svi(2, w | bits);
}

// ===================================================================
// Aligned kick v1 (fighters/gekkouga/README.md "Aligned kick v1"; the user's sketch: an arrowhead). During the ability,
// down special with no left / right (stick down, |X| <= 0.25) while he can act starts it (gk_lw_press -> gk_ak_try: once
// an airtime): his SpecialLwAttack slot (0x161, unused since clones v1: no counter) is ours: the counter's up-diagonal kick
// (his game script's 0x2100001C hitboxes: 13 %, 60 degrees) on him and on both clones at once (their 1 / 2-frame delays
// skipped). The startup: gk_ak_startup() frames (the motion's 5 to its kick, slowed to 5/8: a tap is easier to tell from a
// hold), all three still. At the kick: special still held -> HELD, else TAPPED; he flies straight up gk_ak_rise() in
// gk_ak_flight() frames; each clone flies up toward the centre line (53 degrees, the sketch) gk_ak_far() along its
// diagonal (tapped: they cross above him and end beyond) or gk_ak_near() (held: they end next to him at the spawn spacing,
// on the other side); his peak is well above theirs. Then a quarter of the speed is carried, gravity; he ends in Fall (not
// a free fall), the clones are SPLIT. Swaps any time (gk_swap_free): place and momentum (a flight's rest) exchanged.
// ===================================================================
int gk_ak_startup() { return 8; }         // game frames to the kick (the motion's frame 5: its hitboxes, his and theirs)
int gk_ak_kick_mf() { return 5; }         // the motion's kick frame (speciallwattack / specialairlwattack: FRAME 5)
float gk_ak_rate0() { return 0.625f; }    // the startup's rate (5 motion frames in 8)
int gk_ak_flight() { return 15; }         // frames of flight (the kick's hitboxes: motion frames 5 - 20)
int gk_ak_len() { return 23; }            // the move: startup + flight (the motion's 20 frames)
float gk_ak_rise() { return 78.0f; }      // his rise (straight up)
float gk_ak_far() { return 64.0f; }       // a clone's flight along its diagonal, tapped
float gk_ak_near() { return 46.5f; }      // ... held: 28 across (from -14 to +14) at 53 degrees
float gk_ak_cos() { return 0.6018f; }     // the diagonal: 53 degrees over the horizontal (the sketch's arrows: 52 / 54)
float gk_ak_sin() { return 0.7986f; }
float gk_ak_keep() { return 0.25f; }      // the speed carried past a flight's end
float gk_ak_tilt() { return 270.0f; }     // his kick turned straight up (FighterUtil 6: the counter's rush direction, up)

int gk_ak_try()
{
    int m;
    if (gk_vi(60) == 0)
    {
        gk_lw_eat();
        return 0;                         // clone fix v3: locked (the activating press, the first 10 frames)
    }
    if (gk_vi(9) != 0)
    {
        return 0;                         // once an airtime
    }
    m = gk_vi(8);
    if (m == 0x1 || m == 0x3)
    {
        return 0;                         // a kick's flight / the regroup still running
    }
    func_16(0x161, 0x1);
    return 0x1;
}

// his status 0x161's pre (func_2351's body): in the air (as Hydro Pump's jet, func_2307), its kinetic type kept
int gk_ak_pre()
{
    StatusModule(0x5, 0x2, 0x32, 0x5, 0x2, 0x1, 0xffffe000, 0xfffffffc, 0xffffffc0, 0);
    StatusModule(0x2713, 0, 0x1, 0, 0, 0, 0x432, 0x2000000, 0x400, 0);
    return 0;
}

// its init (func_2358's body): his speeds are ours (gk_ak_tick), no limits
void gk_ak_init()
{
    WorkModule(0x2710, 0x2100001c);
    KineticModule(0x14, 0x3, 100.0f, 0);
    KineticModule(0x11, 0x3, 0, 0);
    KineticModule(0xb, 0x3);
    KineticModule(0x14, 0x1, 100.0f);
    KineticModule(0x11, 0x1, 0);
    KineticModule(0xb, 0x1);
}

// its main (func_2352's body)
void gk_ak_main()
{
    float r;
    WorkModule(0x2711, 0x21000018);       // his effect / sound scripts' False branches: the kick's effects and sound
    WorkModule(0x2711, 0x21000019);
    WorkModule(0x2711, 0x2100001a);
    WorkModule(0x2711, 0x2100001b);
    WorkModule(0x2711, 0x2100001d);
    WorkModule(0x2711, 0x2100001e);
    WorkModule(0x2711, 0x2100001f);
    WorkModule(0x2710, 0x2100001c);       // the up-diagonal kick's hitboxes (his game script's 0x2100001C branch)
    r = gk_ak_rate0();
    func_22(0x28d, 0, r);
    MotionModule(0x4, r);
    GroundModule(0x2710, 0x5);
    FighterUtil(0x6, 270.0f);
    WorkModule(0, 270.0f + 0, 0x100000b);
    gk_ak_begin();
    global16 = gk_ak_tick;
    func_78(gk_ak_loop);
}

// its exec (func_2359's body): his rotation every frame (the counter's)
void gk_ak_exec()
{
    FighterUtil(0x6, WorkModuleF(0, 0x100000b));
}

// its end (func_2355's body)
void gk_ak_end()
{
    VisibilityModule(0x2710, 0x1);
    FighterUtil(0x6, 0);
}

// the move starts: the clones' mode 1 (free, kicking), its clock 0; his path still; each clone faces the centre line
void gk_ak_begin()
{
    float ox;
    int c;
    gk_svi(8, 0x1);
    gk_svi(9, 0x1);
    gk_svi(10, 0);
    gk_svi(11, 0);
    gk_bsi(3, 0x1, 0);
    gk_bs(3, 6, 0);
    gk_bs(3, 7, 0);
    gk_bsi(3, 8, 0);
    ox = PostureModuleF(0x1);
    c = 0x1;
    while (c <= 0x2)
    {
        if (gk_alive & c)
        {
            gk_ak_clone_begin(c, ox);
        }
        c += 1;
    }
}

void gk_ak_clone_begin(int c, float ox)
{
    float x;
    float y;
    float lr;
    x = gk_cx(c);
    y = gk_cy(c);
    lr = 1.0f;
    if (x > ox)
    {
        lr = -1.0f;
    }
    gk_bs(c, 5, lr);
    gk_bsi(c, 0, 12);                     // kicking
    gk_bsi(c, 12, 0x1);                   // tilted along its flight
    gk_bs(c, 6, 0);
    gk_bsi(c, 8, 0);
    gk_bsi(c, 9, 0);
    gk_bsi(c, 11, 0);
    gk_set_c(c, x, y, 0);
    gk_set_fall_t(c, 0);
    gk_fcmd(c, 0x28d, 0);
}

// the kick frame (the clock at gk_ak_startup()): the variant, the three flights
void gk_ak_launch()
{
    int held;
    int c;
    int f;
    float d;
    float ox;
    float v;
    float lr;
    held = ControlModule(0x2712, 0x1);
    d = gk_ak_far();
    if (held)
    {
        d = gk_ak_near();
    }
    gk_svi(11, held + 1);
    f = gk_ak_flight();
    v = gk_ak_rise() / (float)f;
    gk_bs(3, 6, 0);
    gk_bs(3, 7, v);
    gk_bsi(3, 8, f);
    ox = PostureModuleF(0x1);
    c = 0x1;
    while (c <= 0x2)
    {
        if ((gk_alive & c) && gk_bvi(c, 0) == 12)
        {
            lr = 1.0f;
            if (gk_cx(c) > ox)
            {
                lr = -1.0f;
            }
            gk_bs(c, 5, lr);
            gk_bs(c, 6, lr * d * gk_ak_cos() / (float)f);
            v = d * gk_ak_sin() / (float)f;
            gk_set_vy(c, v);
            gk_bsi(c, 8, f);
        }
        c += 1;
    }
}

// his status's per-frame (not in hitlag; gekkouga_frame runs first in the frame): the startup still, then his path
// (his own or a clone's, swapped), then gravity
void gk_ak_tick()
{
    int t;
    int ft;
    float vx;
    float vy;
    t = gk_bvi(3, 0x1) + 1;
    gk_bsi(3, 0x1, t);
    vx = 0;
    vy = 0;
    if (t == gk_ak_startup())
    {
        MotionModule(0x4, 1.0f);
    }
    if (t >= gk_ak_startup())
    {
        ft = gk_bvi(3, 8);
        vx = gk_bv(3, 6);
        vy = gk_bv(3, 7);
        if (ft > 0)
        {
            ft -= 1;
            gk_bsi(3, 8, ft);
            if (ft == 0)
            {
                gk_bs(3, 6, vx * gk_ak_keep());
                gk_bs(3, 7, vy * gk_ak_keep());
            }
        }
        else
        {
            vy = vy - gk_gravity();
            if (vy < -gk_max_fall())
            {
                vy = -gk_max_fall();
            }
            vx = vx * 0.95f;
            gk_bs(3, 6, vx);
            gk_bs(3, 7, vy);
        }
    }
    KineticModule(0x11, 0x3, vx, 0);
    KineticModule(0x11, 0x1, vy);
}

// his status's loop: a landing after the lift-off (a normal landing), the move's end: Fall (not a free fall) / Wait
int gk_ak_loop()
{
    int t;
    t = gk_bvi(3, 0x1);
    if (t > gk_ak_startup() + 0x1 && global18 == 0)
    {
        func_16(0x17, 0);
        return 0x1;
    }
    if (t >= gk_ak_len())
    {
        if (global18 == 0)
        {
            func_16(0, 0);
        }
        else
        {
            func_16(0xe, 0);
        }
        return 0x1;
    }
    return 0;
}

// a clone's frame of the kick: still in the startup (its motion paused frame by frame: gk_fpack), then its flight (walls
// and ceilings stop it), then a quarter of its speed carried: split, in the air
void gk_kick_step(int c)
{
    int ft;
    float x;
    float y;
    float vx;
    float vy;
    float nx;
    float ny;
    if (gk_vi(10) < gk_ak_startup() && gk_vi(8) == 0x1)
    {
        return;
    }
    ft = gk_bvi(c, 8);
    x = gk_cx(c);
    y = gk_cy(c);
    vx = gk_bv(c, 6);
    vy = gk_cvy(c);
    nx = gk_fwall(x, y, vx);
    ny = y + vy;
    if (vy > 0.01f)
    {
        if (gk_line(nx, y + gk_head(), nx, ny + gk_head()) == 0x3)
        {
            ny = gk_hit_y - gk_head();    // a ceiling: the flight ends
            ft = 0x1;
        }
    }
    else if (gk_floor(nx, y + 0.5f, ny - 0.5f))
    {
        ny = gk_floor_y;                  // (a flight going down: a swap gave it his) a floor ends it
        ft = 0x1;
    }
    gk_set_c(c, nx, ny, vy);
    ft -= 1;
    gk_bsi(c, 8, ft);
    if (ft <= 0)
    {
        gk_bs(c, 6, vx * gk_ak_keep());
        vy = vy * gk_ak_keep();
        gk_set_vy(c, vy);
        gk_bsi(c, 0, 10);                 // split: in the air, its own inputs (his)
        gk_bsi(c, 12, 0);                 // upright
    }
}

// ===================================================================
// Split clones (the user: "Clones should mirror inputs. They should not regroup when landing. If shield + special is
// pressed, Greninja should do a quick, short animation and the clones should slowly move back to him"). After the aligned
// kick each clone runs its own actions from his controller (his stick, the game's command bits global24 (CAT1), attack
// held) in its own situation, with its own physics (his walk / dash / run / air / jump / gravity values, the stage line
// tests): on the ground wait / walk / dash / run, jab 1 - 3, tilts, dash attack, smashes (their start, hold, charge, auto
// release and chains, his rules: a charge of its own), jumps (squat, full hop / short hop); in the air aerials (forward /
// back by its own facing), its double jump, drift, fast fall; landings (an aerial's landing lag his). No ledges, no
// specials, no grabs, no shields. Its motion is commanded through the channel (gk_fpack: VAR_28 / VAR_29); its scripts
// are his (hitboxes, effects): its hits count as his. They don't regroup on landing; shield + special does (gk_rg_*).
// ===================================================================
float gk_walk_max() { return 1.43f; }     // his fighter_param: 0x03000003 walk max
float gk_dash_v() { return 1.6f; }        // 0x03000008 dash initial speed
float gk_run_max() { return 2.08f; }      // 0x0300000B run max
float gk_friction() { return 0.045f; }    // 0x03000007 ground friction
int gk_squat_frames() { return 4; }       // 0x1300000C jump startup frames
float gk_jump_vy() { return 4.07f; }      // 0x03000011 jump height 46 at his gravity 0.18: sqrt(2 x 0.18 x 46)
float gk_hop_vy() { return 2.82f; }       // 0x03000012 hop height 22.1
float gk_ajump_vy() { return 4.07f; }     // 0x03000013 air jump height 46
float gk_air_max() { return 1.18f; }      // 0x03000016 air speed max
float gk_air_acc() { return 0.08f; }      // 0x03000014 + 0x03000015 air acceleration (0.07 + 0.01)
float gk_air_fric() { return 0.015f; }    // 0x03000017 air friction
float gk_fastfall() { return 2.96f; }     // 0x0300001B fast fall speed
int gk_dash_frames() { return 10; }       // its dash before the run
int gk_land_frames() { return 4; }        // a plain landing

// the frame an action can end (the clone's motion): his vl group 1 byte 2 (the cancel frame) when it has one, else the
// motion's length (vanilla fighter_param_vl_gekkouga.bin, his motion/body/main.pac)
int gk_mlen(int k)
{
    if (k == 0x50 || k == 0x51)
    {
        return 22;                        // jab 1 / 2
    }
    if (k == 0x52)
    {
        return 36;
    }
    if (k == 0x56 || k == 0x5c)
    {
        return 33;                        // dash attack, up tilt
    }
    if (k == 0x58)
    {
        return 39;                        // forward tilt
    }
    if (k == 0x5d)
    {
        return 27;                        // down tilt
    }
    if (k == 0x5f)
    {
        return 50;                        // forward smash
    }
    if (k == 0x63)
    {
        return 52;                        // up smash
    }
    if (k == 0x65)
    {
        return 55;                        // down smash
    }
    if (k == 0x68)
    {
        return 65;                        // neutral air
    }
    if (k == 0x69)
    {
        return 55;                        // forward air
    }
    if (k == 0x6a)
    {
        return 46;                        // back air
    }
    if (k == 0x6b)
    {
        return 42;                        // up air
    }
    if (k == 0x6c)
    {
        return 57;                        // down air
    }
    if (k == 0x19)
    {
        return 40;                        // JumpF (motion length)
    }
    if (k == 0x1b)
    {
        return 43;                        // JumpAerialF
    }
    if (k == 0x28d || k == 0x279)
    {
        return 20;                        // the kick
    }
    return 0;
}

// an aerial's landing lag (his fighter_param 0x0300001C - 0x03000020)
int gk_alag(int k)
{
    if (k == 0x1)
    {
        return 12;
    }
    if (k == 0x3)
    {
        return 13;
    }
    if (k == 0x5)
    {
        return 32;
    }
    return 15;
}

int gk_sm_hold_mf(int t)
{
    if (t == 0x1)
    {
        return 8;                         // the scripts' hold flag 0x2100001B (attacks4 8, attackhi4 9, attacklw4 5)
    }
    if (t == 0x2)
    {
        return 9;
    }
    return 5;
}

int gk_sm_start_kind(int t)
{
    if (t == 0x1)
    {
        return 0x5f;
    }
    if (t == 0x2)
    {
        return 0x63;
    }
    return 0x65;
}

int gk_sm_hold_kind(int t)
{
    if (t == 0x1)
    {
        return 0x62;
    }
    if (t == 0x2)
    {
        return 0x64;
    }
    return 0x67;
}

void gk_set_vy(int c, float vy)
{
    if (c == 0x1)
    {
        gk_lvy = vy;
    }
    else
    {
        gk_rvy = vy;
    }
}

// a new motion for clone c: kind from frame f0 (the clone restarts it on a new seq)
void gk_fcmd(int c, int kind, int f0)
{
    int s;
    s = 0x1 - gk_bvi(c, 4);
    gk_bsi(c, 4, s);
    gk_bsi(c, 2, kind);
    gk_bsi(c, 3, f0);
    gk_bsi(c, 0x1, 0);
}

// its command in the channel: kind + 1024 x start frame + 2^20 facing left + 2^21 tilted + 2^22 paused + 2^23 seq
// (under 2^24: exact in the float); the kick's startup: paused at the clock's frame of the motion (5 in 8)
int gk_fpack(int c)
{
    int v;
    int f0;
    v = gk_bvi(c, 2);
    f0 = gk_bvi(c, 3);
    if (gk_bvi(c, 0) == 12 && gk_vi(8) == 0x1 && gk_vi(10) < gk_ak_startup())
    {
        f0 = gk_vi(10) * gk_ak_kick_mf() / gk_ak_startup();
        v = v + 4194304;
    }
    if (gk_bvi(c, 0) == 0x4)
    {
        f0 = gk_bvi(c, 10);               // clone fix v3: a smash's hold: its own charge (the clone draws its effects)
    }
    v = v + f0 * 1024;
    if (gk_bv(c, 5) < 0)
    {
        v = v + 1048576;
    }
    if (gk_bvi(c, 12))
    {
        v = v + 2097152;
    }
    if (gk_bvi(c, 4))
    {
        v = v + 8388608;
    }
    return v;
}

// back to formation (the regroup's end, or a kick cut before its kick): copying him again from the offsets they have
void gk_free_end()
{
    float ox;
    float oy;
    ox = PostureModuleF(0x1);
    oy = PostureModuleF(0x2);
    gk_svi(8, 0);
    gk_off_l = gk_lx - ox;
    gk_off_r = gk_rx - ox;
    gk_lfall = 0;
    gk_rfall = 0;
    gk_lvy = 0;
    gk_rvy = 0;
    gk_hn = 0;
    gk_hcopy = 0;
    gk_last_oy = oy;
    gk_det = gk_detached(global4);
    gk_bsi(0x1, 0, 0);
    gk_bsi(0x2, 0, 0);
    gk_bsi(0x1, 12, 0);
    gk_bsi(0x2, 12, 0);
}

// every frame of the ability while the clones are free (mode 1 - 3; gk_physics in formation)
void gk_free_frame()
{
    int m;
    int t;
    int cmd;
    int held;
    float sx;
    float sy;
    float hlr;
    if (StopModule(0x1))
    {
        return;                           // his hitlag: they freeze with him
    }
    m = gk_vi(8);
    if (m == 0x1)
    {
        t = gk_vi(10) + 1;
        gk_svi(10, t);
        if (t <= gk_ak_startup() && global4 != 0x161)
        {
            gk_free_end();                // his kick cut before the kick: nothing flew, back in formation
            return;
        }
        if (t == gk_ak_startup())
        {
            gk_ak_launch();
        }
    }
    if (m == 0x3)
    {
        t = gk_vi(12) + 1;
        gk_svi(12, t);
    }
    sx = ControlModuleF(0);
    sy = ControlModuleF(0x1);
    cmd = global24;
    held = ControlModule(0x2712, 0);
    if (gk_mirror_off(global4) || global4 == 0x160)
    {
        sx = 0;                           // he is hit / on a ledge / calling them: no input for them
        sy = 0;
        cmd = 0;
        held = 0;
    }
    hlr = PostureModuleF(0);
    if (gk_alive & 0x1)
    {
        gk_fc(0x1, sx, sy, cmd, held, hlr);
    }
    if (gk_alive & 0x2)
    {
        gk_fc(0x2, sx, sy, cmd, held, hlr);
    }
    if (m == 0x1 && !gk_kicking(0x1) && !gk_kicking(0x2) && gk_vi(10) >= gk_ak_startup())
    {
        gk_svi(8, 0x2);                   // both flights over: split
    }
    if (m == 0x3 && gk_vi(12) >= gk_rg_frames())
    {
        gk_free_end();                    // regrouped: formation again
    }
}

int gk_kicking(int c)
{
    if ((gk_alive & c) && gk_bvi(c, 0) == 12)
    {
        return 0x1;
    }
    return 0;
}

// one clone's frame (free): its action from his inputs, then its movement
void gk_fc(int c, float sx, float sy, int cmd, int held, float hlr)
{
    int a;
    int t;
    t = gk_bvi(c, 0x1) + 1;
    gk_bsi(c, 0x1, t);
    a = gk_bvi(c, 0);
    if (a == 12)
    {
        gk_kick_step(c);
        return;
    }
    if (a == 13)
    {
        gk_rg_step(c);
        return;
    }
    if (a < 10)
    {
        gk_fg(c, sx, cmd, held, sy);
    }
    else
    {
        gk_fa(c, sx, cmd, hlr);
    }
    gk_fmove(c, sy);
}

void gk_face(int c, float sx)
{
    if (sx > 0.2f)
    {
        gk_bs(c, 5, 1.0f);
    }
    else if (sx < -0.2f)
    {
        gk_bs(c, 5, -1.0f);
    }
}

void gk_idle(int c)
{
    gk_bsi(c, 0, 0);
    gk_bsi(c, 11, 0);
    gk_fcmd(c, 0, 0);
}

float gk_toward(float v, float to, float step)
{
    if (v > to + step)
    {
        return v - step;
    }
    if (v < to - step)
    {
        return v + step;
    }
    return to;
}

// ---- on the ground: 0 wait / walk / run, 1 jump squat, 2 an attack, 3 a smash's start, 4 its hold, 5 a landing
void gk_fg(int c, float sx, int cmd, int held, float sy)
{
    int a;
    int t;
    float vx;
    a = gk_bvi(c, 0);
    t = gk_bvi(c, 0x1);
    if (a != 0)
    {
        vx = gk_bv(c, 6);
        vx = gk_toward(vx, 0, 0.045f);    // his ground friction
        gk_bs(c, 6, vx);
    }
    if (a == 0x1)
    {
        if (t >= gk_squat_frames())
        {
            gk_jump(c, sx, sy);
        }
        return;
    }
    if (a == 0x5)
    {
        if (t >= gk_bvi(c, 13))
        {
            gk_idle(c);
        }
        return;
    }
    if (a == 0x2)
    {
        gk_fatk(c, cmd, sx);
        return;
    }
    if (a == 0x3)
    {
        gk_fsms(c, held);
        return;
    }
    if (a == 0x4)
    {
        gk_fsmh(c, held);
        return;
    }
    if (cmd & 0x300000)
    {
        gk_bsi(c, 0, 0x1);                // jump (button or stick): the squat
        gk_fcmd(c, 0x18, 0);
        return;
    }
    if (gk_fg_attack(c, sx, cmd))
    {
        return;
    }
    gk_fwalk(c, sx);
}

void gk_jump(int c, float sx, float sy)
{
    float vy;
    float vx;
    vy = gk_hop_vy();
    if (ControlModule(0x2712, 0x2) || sy > 0.5f)
    {
        vy = gk_jump_vy();                // jump still held at the squat's end: a full jump
    }
    vx = gk_bv(c, 6) * 0.8f + sx * 0.95f; // his ground-to-air x 0.8, + 0.95 by the stick, at most 1.3
    if (vx > 1.3f)
    {
        vx = 1.3f;
    }
    if (vx < -1.3f)
    {
        vx = -1.3f;
    }
    gk_bs(c, 6, vx);
    gk_set_vy(c, vy);
    gk_set_fall_t(c, 0x1);
    gk_bsi(c, 0, 10);
    gk_fcmd(c, 0x19, 0);                  // JumpF
}

// an attack from his command bits: smash (0x10 forward, 0x20 up, 0x40 down) > tilt (0x2 / 0x4 / 0x8) > jab / dash attack
int gk_fg_attack(int c, float sx, int cmd)
{
    int t;
    int k;
    float vx;
    t = 0;
    if (cmd & 0x10)
    {
        t = 0x1;
    }
    else if (cmd & 0x20)
    {
        t = 0x2;
    }
    else if (cmd & 0x40)
    {
        t = 0x4;
    }
    if (t != 0)
    {
        if (t == 0x1)
        {
            gk_face(c, sx);
        }
        gk_bsi(c, 11, 0);                 // a new chain
        k = 0;
        if (gk_bvi(c, 10) >= gk_smash_full())
        {
            k = 0x1;                      // a stored full charge: it releases on its own
        }
        gk_fsm_begin(c, t, k);
        return 0x1;
    }
    k = 0;
    if (cmd & 0x4)
    {
        k = 0x5c;
    }
    else if (cmd & 0x8)
    {
        k = 0x5d;
    }
    else if (cmd & 0x2)
    {
        k = 0x58;
        gk_face(c, sx);
    }
    else if (cmd & 0x1)
    {
        k = 0x50;
        vx = gk_bv(c, 6);
        if (gk_abs(vx) > gk_walk_max())
        {
            k = 0x56;                     // running: dash attack
        }
    }
    if (k == 0)
    {
        return 0;
    }
    gk_bsi(c, 0, 0x2);
    gk_bsi(c, 13, 0);
    gk_fcmd(c, k, 0);
    return 0x1;
}

void gk_fsm_begin(int c, int t, int au)
{
    int k;
    gk_bsi(c, 0, 0x3);
    gk_bsi(c, 13, t + 8 * au);
    k = gk_sm_start_kind(t);
    gk_fcmd(c, k, 0);
}

// an attack's frames: jab 1 -> 2 -> 3 on a new attack press, a smash's chain (from its last hitbox's end), its end
void gk_fatk(int c, int cmd, float sx)
{
    int k;
    int t;
    int f;
    int st;
    float x;
    float y;
    float lr;
    k = gk_bvi(c, 2);
    t = gk_bvi(c, 0x1);
    f = gk_bvi(c, 3) + t;
    st = gk_bvi(c, 13);
    if ((k == 0x50 || k == 0x51) && t >= 6 && (cmd & 0x7f) == 0x1)
    {
        gk_fcmd(c, k + 0x1, 0);
        return;
    }
    if (st != 0)
    {
        if (f == gk_tr_frame(st))
        {
            x = gk_cx(c);                 // burn v2: its fire trail at its smash's main hit
            y = gk_cy(c);
            lr = gk_bv(c, 5);
            k = gk_tr_type(st);
            gk_tr_ask(c, k, x, y, lr);
            gk_tr_req_t = gk_tr_req_frames();
            k = gk_bvi(c, 2);
        }
        if (f >= gk_sm_window(st) && gk_fchain(c, cmd, sx))
        {
            return;
        }
    }
    if (f >= gk_mlen(k))
    {
        gk_idle(c);
    }
}

int gk_fchain(int c, int cmd, float sx)
{
    int t;
    int used;
    t = 0;
    if (cmd & 0x10)
    {
        t = 0x1;
    }
    else if (cmd & 0x20)
    {
        t = 0x2;
    }
    else if (cmd & 0x40)
    {
        t = 0x4;
    }
    used = gk_bvi(c, 11);
    if (t == 0 || (used & t) != 0)
    {
        return 0;
    }
    if (t == 0x1)
    {
        gk_face(c, sx);
    }
    gk_fsm_begin(c, t, 0x2);
    return 0x1;
}

// a smash's start: at its hold frame an automatic one (a full stored charge: used; a chain) releases, a held one holds,
// a released one is no attack (his rules: gk_sm_start_loop)
void gk_fsms(int c, int held)
{
    int aux;
    int t;
    int au;
    int k;
    int f;
    aux = gk_bvi(c, 13);
    t = aux % 8;
    au = aux / 8;
    f = gk_sm_hold_mf(t);
    if (gk_bvi(c, 0x1) < f)
    {
        return;
    }
    if (au != 0)
    {
        if (au == 0x1)
        {
            gk_bsi(c, 10, 0);
        }
        k = gk_bvi(c, 11);
        gk_bsi(c, 11, k | t);
        gk_bsi(c, 0, 0x2);
        gk_bsi(c, 13, t);
        k = gk_sm_start_kind(t);
        if (gk_bvi(c, 2) != k)
        {
            gk_fcmd(c, k, f);
        }                                 // clone fix v3: already playing it from 0 (no restart at the hold frame: its
        return;                           // script's frame-8 sword / its release effects play on as his)
    }
    if (held)
    {
        gk_bsi(c, 0, 0x4);
        k = gk_sm_hold_kind(t);
        gk_fcmd(c, k, 0);
        return;
    }
    gk_idle(c);
}

// the hold: its charge grows (its own, up to gk_smash_full()); full -> ready (no attack: the next releases at once),
// released -> kept (no attack)
void gk_fsmh(int c, int held)
{
    int v;
    v = gk_bvi(c, 10) + 1;
    if (v > gk_smash_full())
    {
        v = gk_smash_full();
    }
    gk_bsi(c, 10, v);
    if (v >= gk_smash_full() || !held)
    {
        gk_idle(c);
    }
}

void gk_fwalk(int c, float sx)
{
    float ax;
    float vx;
    float lr;
    int k;
    int want;
    ax = gk_abs(sx);
    k = gk_bvi(c, 2);
    vx = gk_bv(c, 6);
    want = 0;
    if (ax < 0.2f)
    {
        vx = gk_toward(vx, 0, 0.045f);
    }
    else
    {
        lr = 1.0f;
        if (sx < 0)
        {
            lr = -1.0f;
        }
        gk_bs(c, 5, lr);
        if (ax < 0.75f)
        {
            want = 0xb;                   // WalkMiddle
            vx = gk_walk_max() * ax / 0.75f * lr;
        }
        else
        {
            want = 0x12;                  // Run, after its dash
            if (k != 0x11 && k != 0x12)
            {
                want = 0x11;
            }
            else if (k == 0x11 && gk_bvi(c, 0x1) < gk_dash_frames())
            {
                want = 0x11;
            }
            vx = gk_run_max() * lr;
            if (want == 0x11)
            {
                vx = gk_dash_v() * lr;
            }
        }
    }
    gk_bs(c, 6, vx);
    if (want != k)
    {
        gk_fcmd(c, want, 0);
    }
}

// ---- in the air: 10 jump / fall, 11 an aerial
void gk_fa(int c, float sx, int cmd, float hlr)
{
    int a;
    int t;
    int k;
    float vx;
    a = gk_bvi(c, 0);
    t = gk_bvi(c, 0x1);
    k = gk_bvi(c, 2);
    if (a == 11)
    {
        if (t >= gk_mlen(k))
        {
            gk_bsi(c, 0, 10);
            gk_fcmd(c, 0x24, 0);
        }
        gk_fdrift(c, sx);
        return;
    }
    if ((cmd & 0x300000) && gk_bvi(c, 9) == 0)
    {
        gk_bsi(c, 9, 0x1);                // its double jump
        gk_set_vy(c, gk_ajump_vy());
        vx = sx * 0.9f;
        gk_bs(c, 6, vx);
        gk_fcmd(c, 0x1b, 0);              // JumpAerialF
        return;
    }
    k = gk_aerial(c, cmd, hlr);
    if (k != 0)
    {
        gk_bsi(c, 0, 11);
        gk_bsi(c, 13, k);
        gk_fcmd(c, 0x67 + k, 0);          // AttackAirN / F / B / Hi / Lw (0x68 - 0x6C)
        gk_fdrift(c, sx);
        return;
    }
    k = gk_bvi(c, 2);
    if (k != 0x24 && t >= gk_mlen(k))
    {
        gk_fcmd(c, 0x24, 0);              // its jump's / the kick's motion over: Fall
    }
    gk_fdrift(c, sx);
}

// the aerial his command asks for (1 neutral, 2 forward, 3 back, 4 up, 5 down), forward / back by its facing
int gk_aerial(int c, int cmd, float hlr)
{
    int k;
    float lr;
    if ((cmd & 0xf81) == 0)
    {
        return 0;
    }
    k = 0x1;
    if (cmd & 0x400)
    {
        k = 0x4;
    }
    else if (cmd & 0x800)
    {
        k = 0x5;
    }
    else if (cmd & 0x100)
    {
        k = 0x2;
    }
    else if (cmd & 0x200)
    {
        k = 0x3;
    }
    else if ((cmd & 0x80) == 0)
    {
        k = ControlModule(0x10);          // only the attack bit: the game's air attack kind (as gk_ac_try)
        if (k < 0x1 || k > 0x5)
        {
            k = 0x1;
        }
    }
    if (k == 0x2 || k == 0x3)
    {
        lr = gk_bv(c, 5);
        if (lr * hlr < 0)
        {
            k = 0x5 - k;                  // his forward is its back
        }
    }
    return k;
}

void gk_fdrift(int c, float sx)
{
    float vx;
    vx = gk_bv(c, 6);
    if (gk_abs(sx) < 0.2f)
    {
        vx = gk_toward(vx, 0, 0.015f);
    }
    else
    {
        vx = gk_toward(vx, sx * gk_air_max(), 0.08f);
    }
    gk_bs(c, 6, vx);
}

// a wall between x and x + vx at its knees stops it there (gk_clone_phys's test); the X it gets to
float gk_fwall(float x, float y, float vx)
{
    float nx;
    nx = x + vx;
    if (gk_abs(vx) < 0.01f)
    {
        return x;
    }
    if (gk_line(x, y + gk_wall_y(), nx, y + gk_wall_y()) == 0x2)
    {
        if (vx > 0)
        {
            return gk_hit_x - gk_wall_gap();
        }
        return gk_hit_x + gk_wall_gap();
    }
    return nx;
}

// its movement: on the ground along the floor (off a ledge it falls); in the air gravity, fast fall, ceilings, landing
void gk_fmove(int c, float sy)
{
    float x;
    float y;
    float vx;
    float vy;
    float nx;
    float ny;
    float reach;
    float d;
    int a;
    int t;
    a = gk_bvi(c, 0);
    x = gk_cx(c);
    y = gk_cy(c);
    vy = gk_cvy(c);
    vx = gk_bv(c, 6);
    t = gk_fall_t(c);
    nx = gk_fwall(x, y, vx);
    d = nx - x - vx;
    if (gk_abs(d) > 0.01f)
    {
        gk_bs(c, 6, 0);                   // a wall
    }
    if (a < 10)
    {
        d = nx - x;
        reach = gk_snap() + gk_slope() * gk_abs(d);
        if (gk_floor(nx, y + reach, y - reach))
        {
            gk_set_c(c, nx, gk_floor_y, 0);
            gk_set_fall_t(c, 0);
            return;
        }
        gk_set_c(c, nx, y, 0);            // off a ledge: it falls
        gk_set_fall_t(c, 0x1);
        gk_bsi(c, 0, 10);
        gk_fcmd(c, 0x24, 0);
        return;
    }
    vy = vy - gk_gravity();
    if (vy < -gk_max_fall())
    {
        vy = -gk_max_fall();
    }
    if (sy < -0.66f && vy < 0)
    {
        vy = -gk_fastfall();
    }
    ny = y + vy;
    if (vy > 0.01f)
    {
        if (gk_line(nx, y + gk_head(), nx, ny + gk_head()) == 0x3)
        {
            ny = gk_hit_y - gk_head();
            vy = 0;
        }
    }
    else if (gk_floor(nx, y + 0.5f, ny - 0.5f))
    {
        gk_set_c(c, nx, gk_floor_y, 0);
        gk_set_fall_t(c, 0);
        gk_fland(c);
        return;
    }
    gk_set_c(c, nx, ny, vy);
    t += 1;
    gk_set_fall_t(c, t);
    if (t > gk_fall_frames())
    {
        gk_kill(c, 0);                    // fallback: fallen far off the stage
        gk_why(400, c);
    }
}

void gk_fland(int c)
{
    int k;
    gk_bsi(c, 9, 0);
    if (gk_bvi(c, 0) == 11)
    {
        k = gk_bvi(c, 13);
        gk_bsi(c, 0, 0x5);
        gk_bsi(c, 13, gk_alag(k));
        gk_fcmd(c, 0x6c + k, 0);          // LandingAirN / F / B / Hi / Lw (0x6D - 0x71), his landing lag
        return;
    }
    gk_bsi(c, 0, 0x5);
    gk_bsi(c, 13, gk_land_frames());
    gk_fcmd(c, 0x3a, 0);                  // LandingLight
}

// ---- the regroup (the user: shield + special: "Greninja should do a quick, short animation and the clones should slowly
// move back to him"): while split, special pressed with shield held, when he can act (standing, moving, in the air,
// shielding): the press is eaten (no special) and his SpecialLwHit slot (0x160, unused: no counter) plays the start of his
// counter stance (speciallw / specialairlw, frames 0 - 7.6: before its intangible window 8 - 19, at 0.4: gk_rg_anim()
// frames), the stance's own slow fall; the clones walk (same floor) / float back to their formation places (his X -/+ 14,
// his Y) over gk_rg_frames() (eased: slow start and end; not through walls' tests: they float), then formation
int gk_rg_frames() { return 75; }         // 1.25 s
int gk_rg_anim() { return 19; }
float gk_rg_rate() { return 0.4f; }

int gk_rg_ok(int st)
{
    if (st == 0x10)
    {
        return 0;                         // helpless
    }
    if (st <= 0x15)
    {
        return 0x1;                       // wait, walk, dash, run, turns, squat, jumps, fall
    }
    if (st >= 0x1b && st <= 0x1d)
    {
        return 0x1;                       // shielding
    }
    return 0;
}

int gk_rg_try()
{
    if (gk_vi(8) != 0x2)
    {
        return 0;
    }
    if (ControlModule(0x2712, 0x3) == 0)
    {
        return 0;
    }
    if (!gk_rg_ok(global4))
    {
        return 0;
    }
    WorkModule(0, 32.0f + 0, 0x0f0003c9); // Buffer_Clear (specials): no special status
    global24 = global24 - (global24 & 0xf000);
    func_16(0x160, 0x1);
    return 0x1;
}

// his status 0x160's main (func_2346's body)
void gk_rg_main()
{
    float r;
    r = gk_rg_rate();
    if (global18 == 0)
    {
        func_22(0x271, 0, r);
    }
    else
    {
        func_22(0x289, 0, r);
    }
    MotionModule(0x4, r);
    gk_rg_begin();
    func_78(gk_rg_loop);
}

// its loop (func_2347's body)
int gk_rg_loop()
{
    if (global9 >= (float)gk_rg_anim())
    {
        if (global18 == 0)
        {
            func_16(0, 0);
        }
        else
        {
            func_16(0xe, 0);
        }
        return 0x1;
    }
    if (global19 == 0 && global18 == 0x2)
    {
        func_23(0x289);
        MotionModule(0x4, gk_rg_rate());
    }
    else if (global19 == 0x2 && global18 == 0)
    {
        func_23(0x271);
        MotionModule(0x4, gk_rg_rate());
    }
    return 0;
}

void gk_rg_begin()
{
    int c;
    float x;
    float y;
    if (gk_vi(8) != 0x2)
    {
        return;
    }
    gk_svi(8, 0x3);
    gk_svi(12, 0);
    c = 0x1;
    while (c <= 0x2)
    {
        if (gk_alive & c)
        {
            x = gk_cx(c);
            y = gk_cy(c);
            gk_bs(c, 14, x);
            gk_bs(c, 15, y);
            gk_bsi(c, 0, 13);
            gk_bsi(c, 12, 0);
            gk_bs(c, 6, 0);
            gk_set_vy(c, 0);
            gk_fcmd(c, 0x24, 0);
        }
        c += 1;
    }
}

float gk_form_off(int c)
{
    if (c == 0x1)
    {
        return -gk_gap();
    }
    return gk_gap();
}

// a clone's regroup frame: eased (smoothstep) from where it was to its formation place now
void gk_rg_step(int c)
{
    float u;
    float s;
    float tx;
    float ty;
    float x0;
    float y0;
    float x;
    float y;
    float d;
    int k;
    u = (float)gk_vi(12) / (float)gk_rg_frames();
    if (u > 1.0f)
    {
        u = 1.0f;
    }
    s = u * u * (3.0f - 2.0f * u);
    d = gk_form_off(c);
    tx = PostureModuleF(0x1) + d;
    ty = PostureModuleF(0x2);
    x0 = gk_bv(c, 14);
    y0 = gk_bv(c, 15);
    x = x0 + (tx - x0) * s;
    y = y0 + (ty - y0) * s;
    if (tx > x0 + 0.5f)
    {
        gk_bs(c, 5, 1.0f);
    }
    else if (tx < x0 - 0.5f)
    {
        gk_bs(c, 5, -1.0f);
    }
    k = 0x24;                             // floating back (Fall)
    d = ty - y0;
    if (gk_abs(d) < 3.0f && gk_fall_t(c) == 0)
    {
        k = 0xb;                          // walking back on his floor (WalkMiddle)
    }
    if (u >= 1.0f)
    {
        k = 0;
    }
    if (k != gk_bvi(c, 2))
    {
        gk_fcmd(c, k, 0);
    }
    gk_set_c(c, x, y, 0);
}

// ---- swaps while free (the user: "he can swap with a clone at any point during the move (and after), taking its
// position and momentum"): places exchanged, and the speeds: a flight's rest (its speed and frames) go with it; in his
// kick status his path is ours (gk_ak_tick), else his speed is set (the vertical on his gravity energy, the horizontal
// on his stop energy: approximate); the clone gets his (his kick path, or his speed now: SPEED_X / SPEED_Y)
void gk_swap_free(int id, float ox, float oy, float cx, float cy)
{
    float hvx;
    float hvy;
    float cvx;
    float cvy;
    int hft;
    int cft;
    int a;
    hft = 0;
    if (global4 == 0x161)
    {
        hvx = gk_bv(3, 6);
        hvy = gk_bv(3, 7);
        hft = gk_bvi(3, 8);
    }
    else
    {
        hvx = WorkModuleF(0, 0x0f000332);
        hvy = WorkModuleF(0, 0x0f000333);
    }
    cvx = gk_bv(id, 6);
    cvy = gk_cvy(id);
    cft = gk_bvi(id, 8);
    a = gk_bvi(id, 0);
    if (a != 12)
    {
        cft = 0;
    }
    WorkModule(0x2, cx - ox + 0, 0x0f000000);
    WorkModule(0x2, cy - oy + 0, 0x0f000001);
    gk_fx_flip();
    if (global4 == 0x161)
    {
        gk_bs(3, 6, cvx);
        gk_bs(3, 7, cvy);
        gk_bsi(3, 8, cft);
    }
    else
    {
        KineticModule(0x11, 0x1, cvy);
        KineticModule(0x11, 0x3, cvx, 0);
        KineticModule(0xb, 0x3);
    }
    gk_set_c(id, ox, oy, hvy);
    gk_bs(id, 6, hvx);
    gk_bsi(id, 8, hft);
    if (hft > 0)
    {
        gk_bsi(id, 0, 12);                // it flies his path's rest
        gk_bsi(id, 12, 0x1);
    }
    else if (a == 12 || StatusModule(0x1) == 0x2)
    {
        gk_bsi(id, 0, 10);
        gk_bsi(id, 12, 0);
        gk_set_fall_t(id, 0x1);
        gk_fcmd(id, 0x24, 0);
    }
    else
    {
        gk_set_fall_t(id, 0);
        gk_idle(id);
    }
    gk_swap_cd = 10;
}

// ---- aligned kick v1 package (the user: "If the original swaps into a clone during an aerial while landing, the effect will
// stay attached to the clone until it disappears"): the clones' following effects end (EffectModule 0x2D: a fade) when the
// channel's effects epoch (flags 256, his slot 13) changes: at every swap (formation or free) and at his landing in
// formation (his aerial's effects on them end with his; free clones end theirs at their own landing: a new motion)
void gk_fx_flip()
{
    gk_svi(13, 0x1 - gk_vi(13));
}

void gk_land_fx()
{
    int s;
    s = StatusModule(0x1);
    if (gk_vi(8) == 0 && gk_vi(14) == 0x2 && s == 0)
    {
        gk_fx_flip();
    }
    gk_svi(14, s);
}

// ===================================================================
// Clone articles v1 (fighters/gekkouga/README.md "Clone articles v1"; the user: "allow clones to spawn duplicate articles,
// such as the skeletons, water shuriken and hydro pump (clone skeletons should spawn on top of each other, forming a stack
// of skeletons)"). The clones in formation copy his moves; when his move makes an article, each clone out (alive, in
// formation, not falling on its own) gets its own, his (his hits, his KO credit):
// - his skeleton (side special): the clones' are asked for one a frame after his (each when the one before was claimed:
//   his VAR_15 = 1 + the level, 1 the first clone's, 2 the next), at his skeleton's X, its Y + 24 x the level, his way;
//   each sits on the one below (weapons/skeleton.c sk_seat_step; the executable's stack table, feature cart)
// - his water shuriken (neutral special's shot, with its charge): right after his shot, one generated and shot per clone
//   (ArticleModule 0x2710 / 0x2719 on article 0, as his); each copy (weapons/shuriken.c) claims a clone from the channel's
//   bits 512 / 1024 (slot 16, kept 3 frames) and its claim bits in his VAR_30 (64 / 128), and moves by that clone's offset
// Slots: 6 / 7 his skeleton's place, 15 the clones' skeletons still to ask for (1 / 2), 57 the shuriken copies waiting
// (1 / 2), 58 their frames left, 59 the levels asked for so far (57 - 63: his body's k 9 - 15, unused)
// ===================================================================
int gk_art_clones()
{
    int c;
    int bits;
    bits = 0;
    if (gk_ability <= 0 || gk_vi(8) != 0 || gk_det)
    {
        return 0;
    }
    c = 0x1;
    while (c <= 0x2)
    {
        if ((gk_alive & c) && gk_fall_t(c) <= 2)
        {
            bits = bits | c;
        }
        c += 1;
    }
    return bits;
}

void gk_sk_stack(float x, float y)
{
    float fx;
    float fy;
    int b;
    b = gk_art_clones();
    fx = x;
    fy = y;
    gk_svi(15, b);
    gk_svi(59, 0);
    WorkModule(0, fx + 0, 0x0f000386);
    WorkModule(0, fy + 0, 0x0f000387);
}

// his request claimed (his VAR_15 back to 0 while it was up): the next clone's skeleton, one level up
void gk_sk_queue()
{
    int b;
    int c;
    int lv;
    float x;
    float y;
    int r;
    b = gk_vi(15);
    if (b == 0 || gk_sk_req_t <= 0 || WorkModuleF(0, 0x0f00030f) > 0.5f)
    {
        return;
    }
    c = 0x1;
    if ((b & 0x1) == 0)
    {
        c = 0x2;
    }
    gk_svi(15, b - c);
    lv = gk_vi(59) + 1;
    gk_svi(59, lv);
    x = WorkModuleF(0, 0x0f000386);
    y = WorkModuleF(0, 0x0f000387) + 24.0f * (float)lv;
    WorkModule(0, (float)(lv + 1) + 0, 0x0f00030f);
    WorkModule(0, x + 0, 0x0f000310);
    WorkModule(0, y + 0, 0x0f000311);
    WorkModule(0, PostureModuleF(0) + 0, 0x0f000312);
    gk_sk_req_t = gk_sk_req_frames();
    r = ArticleModule(0x2710, 0x8);
}

// his shot (SpecialNShot / SpecialNMaxShot, right after his ArticleModule(0x2719, 0)): one shuriken per clone out, generated
// and shot as his (his charge: the shot reads it), claimed by the copy (the channel's bits) and moved by that clone's offset
void gk_sh_copies()
{
    int b;
    int r;
    b = gk_art_clones();
    if (b == 0)
    {
        return;
    }
    gk_svi(57, b);
    gk_svi(58, 3);
    if (b & 0x1)
    {
        r = ArticleModule(0x2710, 0);
        ArticleModule(0x2719, 0);
    }
    if (b & 0x2)
    {
        r = ArticleModule(0x2710, 0);
        ArticleModule(0x2719, 0);
    }
}

// clone fix v3 diag: a shuriken copy's report in his VAR_30 (256 x: clone + 4 x (0 first set, 1 set again) + 8 x (its
// place minus the clone's: X/2 + 20 + 41 x (Y/2 + 20), each 0 - 40); weapons/shuriken.c sh_report): his VAR_23 = 700 / 800
// + the clone + 1000 x the place (the S4GF line: slot 62 flips the flags' 1048576 bit so the line is written)
void gk_sh_report()
{
    int beat;
    int r;
    beat = (int)(WorkModuleF(0, 0x0f00031e) + 0.5f);
    if (beat < 256)
    {
        return;
    }
    r = beat / 256;
    WorkModule(0, (float)(beat % 256) + 0, 0x0f00031e);
    gk_why(700 + 100 * ((r / 4) % 2) + 1000 * (r / 8), r % 4);
    gk_svi(62, 0x1 - gk_vi(62));
}

void gk_sh_tick()
{
    int t;
    t = gk_vi(58);
    if (t <= 0)
    {
        return;
    }
    gk_svi(58, t - 1);
    if (t - 1 <= 0)
    {
        gk_svi(57, 0);
    }
}
