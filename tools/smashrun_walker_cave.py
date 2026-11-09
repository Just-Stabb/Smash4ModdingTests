#!/usr/bin/env python3
"""Smash Run: the 3DS behaviours (AI) of five walking enemies the Wii U has none for, ported per kind from
enemy_fs.cro (docs/smash-run-port.md, "Step 2b" and "Fix v5"). Prints rpx_patch.py args, or patches an RPX (after
smashrun_menu.py's, smashrun_field_cave.py's and smashrun_enemy_cave.py's patches; IN.rpx is read for
BehaviorImpl's vtable):

  python3 tools/smashrun_walker_cave.py IN.rpx            the args
  python3 tools/smashrun_walker_cave.py IN.rpx OUT.rpx    IN with them (checks the hook words first)

Each kind is a BehaviorImpl (the Wii U's own enemy framework, the 3DS one: damage, knock-back, down, capture, death
stay its own) with its own state table, numbered as its 3DS table, each state's enter / update written from the
3DS functions (state id: enter / update in enemy_fs.cro). Calls are the Wii U's equivalents of the 3DS ones
(Behavior at the 3DS offset -4, the accessor's modules at the 3DS offset +0x80); "->" is a deferred change_state
(slot 72), "=>" the immediate one (slot 73); input = the AI stick (Behavior::move).

Kuribo (Goomba) 0x01, table 0x10F... (vtable 0xCD308):
  1 fall      kinetic 8, ground off, Fall loop; on the ground => 2
  2 landing   kinetic 0, ground on, Landing; at its end -> 3
  3 walk      WalkL at p+0x14 (0.6), kinetic 0xA (the walk animation's own movement), ground on; input (lr, 0);
              every interval frames (search 0: 100) search_target(search 0) -> if found: face it, => 4; off the
              ground -> 1; a ledge (variation 1 only; variation 0 walks off) or a wall ahead -> reverse_lr, -> 3
  4 notice    the startled hop: E+0x20 = p+0x1C (-0.4: back), kinetic 5, ground off, RunHoldL loop; on landing
              ground on; p+0x2C (30) frames after entering -> 5, the run counter 0
  5 run       RunL at p+0x28 (1.0), kinetic 0xA, ground on; the only state with the contact attack (vl attack
              list: state 5, KURIBO_BUMP); every 60 run frames search_target(search 1): a target behind -> 7;
              a wall ahead (or a ledge, variation 1: clear_speed_all) -> 7; off the ground -> 1; after p+0x30 (110)
              run frames -> 6
  6 brake     RunBrakeL, kinetic 2, ground on; at its end -> 3
  7 run turn  RunTurnL, kinetic 2, ground on; at a ledge clear_speed_all; at its end reverse_lr, => 5
  8 collapses stepped on (slot 21 on the 3DS, 20 here: below) => 8: kinetic 0, Collapses, ground on,
              notify_on_death (death flag, hit off, attacks cleared); at its end -> 10 (the 3DS's
              create_dead_item(1, 10) on frame p+0x38 (1) is the removal's defeat path here, fix v3)
  9 dead      Damage at rate 0, bullet() (the defeated enemy flies off) and the vl "bullet" attack (state 9: a
              flying body hits); kinetic flag 8 => 10
  10 remove   zima's 0x026D7B58 / 0x026D7B6C (EnemyManager remove_enemy_by_id)
  after damage on the ground 3, in the air / default 1, death 9 (slots 64-67)
Heiho (Shy Guy) 0x0B (vtable 0xCD978-ish, BehaviorHeiho): 1 fall (rising: wait), 2 landing (end: target behind ->
  5, else 4), 3 wait (Wait twice, then 50 %% reverse_lr, -> 4; the search below), 4 walk (the walk energy row,
  kinetic 1, Walk loop, random(60, 120) frames -> 3; a wall -> 6; a ledge (variations 1 / 2) -> 5; every 30
  frames search_target(search 0): face the target, -> 7), 5 turn (end: reverse_lr, => 9 while the run timer
  runs, else => 4), 6 wall hop (kinetic 5, Walk; landed on the same height (p+0x90) or a wall still ahead => 5,
  else => 2), 7 notice (set_kinetic_jump(0, 2.0, 0): two hops in place, RunHold; => 8), 8 hold (row 1 +0x10 frames
  (0), then face the target, -> 9), 9 run (the run energy row, kinetic 3, Run loop, 80 frames -> 12; the contact
  attack (state 9, HEIHO_BUMP); a wall -> 10; a ledge (variations 1 / 2) -> 10; every 30 frames search 1: a
  target behind -> 13), 10 wall run turn (RunTurn, end: reverse_lr => 9), 12 brake (RunBrake, kinetic 2; at its
  end and stopped -> 14), 13 run turn (RunTurn at p+0x78, kinetic 2; end: reverse_lr => 9), 14 settle (kinetic 21,
  Fall; kinetic flag 1 -> 4), 15 dead (DamageStart, bullet, state 15's bullet attack), 16 remove; 4 / 1 / 1 / 15.
Waddle Dee 0x13: 1 fall, 2 parasol fall (variations 0 / 1: start here and after a jump or a ledge), 3 landing
  (-> 4), 4 walk (Walk at p+0x84 (1.2), kinetic 1; every p+0x78 (100) frames p+0x7C %% (50) -> 6 jump; a wall:
  p+0x80 %% (50) -> 6, else -> 5; a ledge (variations 1 / 3) -> 5; off the ground -> 2 (variations 0 / 1) / 1),
  5 turn (end: reverse_lr => 4), 6 jump (kinetic 5, Jump; from the apex -> 2 / 1), 7 dead, 8 remove; 4 / 1 / 1 /
  7. No contact attack: its vl list has only the bullet (state 7).
Waddle Doo 0x19: 1 fall, 2 landing (end: the nearest target behind -> 4, else 3), 3 walk (Walk, kinetic 1; a wall
  -> 5; every 60 frames search_target(search 0) behind -> 4), 4 turn (=> 3), 5 jump (kinetic 5, Jump; landed on
  the same height or a wall ahead => 4, else => 3), 6 dead, 7 remove (the 3DS's 10 / 11: renumbered in fix v8 to
  save the empty rows); 3 / 1 / 1 / 6. No contact attack.
Churine 0x1F: 1 fall, 2 landing (end: unless it came from a hop, the nearest target behind -> 5; else 3), 3 walk
  (initialize again, Walk, kinetic 1; a wall -> 4; a ledge -> 5), 4 jump (initialize, kinetic 5, Jump; landed on
  the same height (row +0x18: 20) or a wall ahead => 5, else => 2), 5 turn (=> 3), 6 dead, 7 remove (the 3DS's
  8 / 9); 3 / 1 / 1 / 6. No contact attack.

Step 2c (docs/smash-run-port.md, "Step 2c"; code in region E):
White Bear 0x40 (create 0x7F420, table 0x111E8C): 1 fall (Fall loop; on the ground => 2), 2 landing (end: the nearest
  target behind -> 5, else 3), 3 walk (kinetic 1, Move loop; V1 = random(60, 120); stick (lr, 0); off the ground
  -> 1; a wall or ledge -> 5; the search counter V0++; a cool-down V2 > 0 counts down and skips the search; when V0
  passes search 1's interval (60): V0 = 0, search_target(group 1) found -> 6; V1 runs out -> 4), 4 special turn
  (SpecialTurn; end: reverse_lr => 3), 5 turn (Turn; same), 6 quake hold (QuakeHold at 1.5, V4 = 0; end -> 7: the
  3DS's is_in_view_area test (CameraModule is_clip_in) is taken as true), 7 quake jump (E+0x20 0, +0x24 / +0x2C
  1.5, +0x28 0, +0x3C 0.1, the kick vt+0xEC (the 3DS's KineticEnergy vt+0x74), kinetic 5, QuakeUp; V5 frames; speed
  y <= 0 -> 8), 8 quake fall (E+0x20 / +0x24 the current speed, +0x28 0, +0x2C 3, +0x3C 1, the kick, kinetic 5,
  QuakeFall; on the ground: V5 < 180 => 9, else => 2), 9 quake landing (kinetic 0, QuakeLanding at 1.0, 0.5 after
  the first; V4++; end: V4 < 3 and a 50 >> (V4 - 1) %% chance -> 7, else V2 = 60 -> 3), 10 dead (DamageStart,
  bullet, P2's bullet attack), 11 remove; 3 / 1 / 1 / 10. Not ported: the landing's camera quake, its absolute
  hit on the first grounded fighter (the bear's only attack: Behavior::hit_attack_absolute with P6, power 10,
  angle 90, bkb 40), its effects 0x7400000 / 0x7400001, set_weak_param(5, 2.0).
Gordo 0x08 (create 0x1A470, table 0x10F55C), variation 0: start (SMODE 1: set_rhombus, set_correct(0), set_lr(0, 1,
  1), no turn to a target), 1 spin (kinetic -1, ground off, Togetoge loop; the contact attack P2 entry 0: power 10,
  angle 65, kbg 50, fkb 50, bkb 100, size 8, node 3), 3 remove; slots 64-67 0 (never defeated: death state 0).
  Not ported: the per-frame energy-0 write steering it back to its spawn point (it holds it with kinetic -1),
  set_test_coll_stop(1), set_invincible_global(0), variations 1-3 (state 2: moving along a line or path).

Step 2c v2: the White Bear's landing (state 9 enter) also does request_quake(6) (0x026A9648), the 3DS's absolute
  hit on the first fighter on the ground (b_quake: MSC StatusModule(1) == 0, then the enemy's AttackModule MSC
  entry vt+0x334 with ops 0x2716 set_abs (ABS_WORDS) and 0x271D hit_absolute(the fighter's object id)) and its two
  effects (request_effect 0x026A951C / 0x026A94CC); Waddle Doo's leave (start: V7 = CFG LEAVE 600; the walk counts it
  down -> state 8: Fall at rate 0, the common leave (energy +0x30 / +0x34, kinetic 15, ground off, set_correct(0),
  effect 0x8000005 following node 0) for 300 frames -> remove); the death / collapse enters set DEFEATED (+0x19C)
  and the notify_on_remove hook gives the defeat path only to those (a leave is removed plainly).

Step 2e (docs/smash-run-port.md, "Step 2e"; region G, code_f): the fliers (FLIERS) Ghos 0x11 and Tiki Buzz 0x0F,
  walker-engine kinds with their own CFG VT / SIZE (0x230: the aerial module at AER 0x1B0) / tread box / handlers:
  VTF = VT but slots 10 / 27 / 41 / 69 (the kind's FDMG / F27 / FSTART / F69, else BehaviorImpl's). Ghos: 1 fly
  (slip homing on the nearest fighter, the wall bounce, 1200-frame leave timer), 2 stun (hit_return_frame), 3 leave,
  4 dead, 5 remove; contact P2 entry 1 in 1. Tiki Buzz: 1 fall, 2 dead, 3 fly (homing extend on fighter 0 + 35,
  search every 30 frames, 900-frame leave), 4 hold, 5 dive (uniform (0, -6); the only hitbox, P2 entry 0), 6 brake,
  7 landed (quake 3), 8 ready, 9 leave, 10 stomped (slot 20 and the stomp test, box (6, 11.72, 1.5)), 11 gone, 12
  remove. Region G is new code space past the old text region (textregion:0x2BC0000, grow:0x04BC0000).

Step 2f (docs/smash-run-port.md, "Step 2f"; region G): Furiijio 0x1A, a flier with its own object size (FU_SIZE) and
  vtable (`vtover`: slots 4 update_on_skip, 61 / 62 kinetic 26) and exit PMFs (a state's third entry): 1 fly (homing
  on the nearest fighter + 25, search every 50 frames after a 150-frame cool-down, 900-frame leave), 2 / 5 charge,
  3 / 6 aim (BeamN turned with set_node_rotate / placed with set_node_translate), 4 / 7 the ice beam (its own hitbox,
  P2 entry 0 / 1, freezing, slid out with AttackModule set_offset; three follow effects scaled / moved; 7 sweeps 180
  degrees), 8 leave, 9 dead, 10 remove. REQ_FOLLOW corrected to 0x026A95F8 (0x026A9584 is REQ_NODE), and the fliers'
  starts call set_rhombus with the Behavior.

Step 2g (docs/smash-run-port.md, "Step 2g"; region G, code_ph): Propeller Heiho 0x47 (PH_SIZE, `vtover` slots 55 /
  59, `dmg_labels`): 4 height, 5 patrol (cosine bob), 6 brake, 1 turn, 2 fly away, 7 stun, 3 dead, 8 remove, with the
  3DS's set_mode_normal / set_max_speed / get_height_from_ground / get_lr_to_nearest_target written over the Wii U's
  aerial module and GroundModule ray_check; it carries an item: the Wii U's Behavior::create_item 0x026A8D78 + the
  item's have(0x50000000) (create_item_and_have), held by Item::warp each frame (slot 59), swapped / dropped
  (Item::fall) in slot 55 and on damage (slot 10), removed with it (slot 27).
Step 2g v4: Ghos's immunity to direct hits (the 3DS's slot 31 0x113F0 / slot 11 0x11094): vt_ghos slot 31 f_g31 (the
  hit's AttackData byte +0x4C -> GH_IMM), slot 10 f_ghos_dmg (immune: DamageModuleImpl::init_damage(GH_DMG) 0x02C212F0,
  no reaction; else GH_DMG = the damage and BehaviorImpl's); Ghos's object GH_SIZE (two more words).

Step 2h (docs/smash-run-port.md, "Step 2h"; region H 0x04BC0000-0x04BD0000, code_h; the text region grown again):
  the stomp bounce: the stomp test now calls the kind's slot 20 (w_tread, or the kind's own handler) and u_bounce writes
  the fighter's tread multiplier (status float 0x1000006 = CFG BOUNCE, else the enemy's work float 0x11 = W+0x44, the
  value the Enemy's event 6 answers) and step count (int 0x10000006 = 0), through its WorkModule (MSC accessor +0x28,
  vt +0x4C / +0x8C); u_pend (at w_upd's start) writes the multiplier again while the fighter's status (+0x20 -> +0x48)
  is StepJump 0xB3 and drops it once it has left it (MSC StatusModule op 3 is a request). Kinds: Big Goomba 0x23
  (dk_*: its ACMD hitboxes through the 3DS hashset table, the 25-HP stomp), Spiny 0x4E (tg_*: the egg and the
  Spiny, always-on spikes, never stomped, the leave), Paratroopa / Koopa 0x03 (pt_*: the hop and the bite (aerial
  uniform mode), the wing loss, the walking leap, the shell item 0x94). STEP2H, CFG BOUNCE, `hs3ds` (a kind's 3DS
  hashset table), STEM_NAME (the 3DS motion files' capitalisation), `dead` as a motion index.

Step 2j (docs/smash-run-port.md "Step 2j"; region H, code_pk / code_fix2j): Pooka 0x20 (pk_*: walk, back-off and lunge
  with the 3DS bounce, the ghost / drop choice, the ghost's flight through walls, the HP-driven balloon and deflate,
  the pop's size-30 burst; slots 6 / 12 / 16 / 51 / 56 / 60 / 69 / 70; a flier-sized object PK_SIZE), and the
  accuracy audit's small fixes: Waddle Doo's slot 69 / random hop / Fall switch / hop threshold, Shy Guy's slot 69 /
  hop threshold, Waddle Dee's parasol fall in the aerial module, Goomba's notice ledge check and frame-1 dead item,
  White Bear's view test; Furiijio's beam angles back to the 3DS's (its effect models billboard themselves).

Step 2m (docs/smash-run-port.md "Step 2m"; region H, code_2m): sounds. Every 3DS play_se / stop_se of the ported
  kinds at its 3DS point (SE_EN: state-enter wrappers se_<kind>_<state>; the updates / exits / slots: se_heiho_7u,
  ch_pw_up, do_bm_up / se_doo_11x, gh_start / se_gh_dmg / se_gh_rm / gh_31, se_fu_bexit / se_fu_57 / se_fu_69,
  se_ph_start / se_ph_71 / se_ph2_up / se_ph_55 (ph_snd: one loop per kind), se_pk_dmg); snd_rows (cave_s) registers
  the 3DS soundlabeltable rows of the kinds' banks at their own numbers in the Wii U's loaded table (and points the
  twins' rows at the kinds' banks on Smash Run stages), so the 3DS ids play as they are (tools/smashrun_sound.py).
  Stalfos: sf7_up / sf8_up on mczakostalfos's state 7 / 8 update words: the 3DS's drop through a passable floor
  (L5F470) for kind 0x30.

Not ported (the README lists them): the Waddle Doo's beam (states 7 / 8: an article the Wii U has no weapon kind
for) and its leave timer (9) and random hop (6); the Churine's sleep powder (6 / 7: an effect and attack the Wii U
has no data for); the Waddle Dee's parasol float (EnemyAerialModule embedded in the 3DS object: the parasol fall is
a normal fall with the ParasolFall motion); sounds (play_se: the 3DS sound ids); per-state mesh visibility (no
Wii U path: the NUD baseline of fix v4 stands); the Kuribo notice hop's ledge check (check_cliff_distance_lr
with the kind's gl gravity); ray_check (Shy Guy / Doo / Churine hops: check_wall stands in); the variation-indexed
rows of variations 1-3 (the spawner makes variation 0). Values the 3DS reads from a kind's param struct
(EnemyParamAccessor slot [K]) at fixed offsets: the vl groups (+0xC group 0, +0x20 the search groups, +0x34 the
attacks) and an inline part from +0x48 (the kind's own group: Waddle Dee +0x78..+0x84 = 100 / 50 / 50 / 1.2, Shy
Guy +0x78 = 0.7, +0x90 = 1.0 -- inferred from the vl files' order; the Waddle Doo's hop height is a guess, 1.0).

The framework:
- vtable VT: a copy of BehaviorImpl's 0x1008AEBC (GHS: {delta, fn}, slot k's fn at +0xC + 8k) plus 74 / 75;
  overrides: 12 zima's 0x026D6E18 (capture motion), 20 w_tread (stepped on, below), 38 w_noflip (0, fix v3; step 2g v6: 1 for FLIP_TABLE kinds; --keep-flip: zima's `li r3, 1`),
  40 initialize (the kind's 3DS kinetic energy words), 41 start (set_rhombus, +0x10 = posture lr, face the
  nearest target, the kind's first state), 45 set_attack_data (below), 64-67 the kind's states (CFG), 72 / 73
  change_state(id) / the interrupt one (the kind's state table {enter, update, exit} PMFs to 0x026A3A44 /
  0x026A3AD4; unknown ids -> 1); dtor, update, damage / capture / death slots: BehaviorImpl's.
- create(acc, K, variation): operator new 0x03374578(OBJ_SIZE), Behavior ctor 0x02DB2DF0, BehaviorImpl's inline
  init as zima's create 0x026D6680 (+0xE4..: 0, +0xE8 common_state_func 0x102FDBCC, +0x120 = 1, +0x15C = -1), vptr
  VT, +0x168 = the kind's CFG, set_motion_label 0x02DB5B08 (+0xA8 = its script hashsets or 0),
  set_damage_motion_label 0x02DB5AD8 (the 3DS create's nine indices). +0x16C.. the kind's counters (V0-V8, Y0).
- set_attack_data(state) (slot 45; the 3DS kinds use Behavior::set_attack_data, the vl attack list by state):
  AttackModule clear_all 0x02C08324, then each of the kind's {state, InnerEnemyAttackParam} with this state:
  create_attack_data 0x02DB572C(this, entry), +0x84 / +0x88 = entry +4 / +8, set_attack 0x02C086A8(module, id,
  part, this+0x1C). So the contact hitbox is on only in the Kuribo's run (5) and the Shy Guy's run (9), and every
  kind's defeated body carries its bullet attack (as the Wii U's own minions' lists do).
- search_target(group): the 3DS reads the kind's vl search group {type, interval, 5 floats}; the Wii U's
  search_target(int) 0x026A70FC reads the param slot (mczakozima's here), so the cave passes the kind's own group
  to 0x026A70A4 (Behavior::search_target(type, this+0x10, f1..f5) -> EnemyAiModule check_target 0x02DB9F24).
  Others: get_nearest_target 0x026A7008, check_turn_to_target 0x026A6984, get_fighter_pos 0x026A690C,
  check_wall 0x026A68E4, check_cliff 0x026A6E24, clear_speed_all 0x026A67E8, is_current_stopped 0x026A679C,
  get_current_speed 0x026A678C, random_range (an xorshift in the cave).

Stomp (fix v6): a fighter's footstool on an enemy reaches it as Enemy event 6 (the handler the Enemy ctor registers,
0x02D8C450 -> 0x02D8C5D4): behaviour module 0x02DB98F4 -> behaviour slot 20 (fn at vt+0xAC), then the event gets a
param float (acc+0x315C vt+0x44, 0x11) back for the fighter's bounce. Slot 20 is the 3DS's slot 21 (the 3DS vtables
have two destructors: 3DS k = Wii U k + 1 up to slot 28 -- 13 capture motion / 12, 28 notify_on_remove / 27, and
zima overrides exactly this slot with a nop on both). BehaviorImpl's is a nop; the 3DS overrides it in kuribo
(=> 8 collapses), dekakuribo (add_damage(p+0x3C), => 10 / 11), patapata (variations 0 / 1 => 9, else 0x13),
tikibuzz, waddledee (parasol variations: p+0x8C into its parasol timer) and zima (a nop). w_tread => the kind's
CFG TREAD state (Kuribo 8; the other four 0: nothing, as on the 3DS but Waddle Dee's parasol timer, not ported).

Tread area (fix v7): a fighter can only stomp an enemy whose AreaModule area 0 (the tread area, kind 0xE) is on. The
Enemy builds its two areas from its param slot's +0x70 table (2 x {on, node, 4 floats}: 0x02D89860, add_area
0x02BFEA2C) and turns area i off where entry i's word 0 is 0 (0x02D8A24C; 0x02D8FB98 sets area 0 again from entry 0);
no code enables it (Behavior::enable_tread / disable_tread, 0x026A7614 / 0x026A75FC, are only for the few kinds that
switch it). S2 gives the walkers mczakozima's slot, whose table has the tread area off (as all four Fortress
minions'), so nothing could stomp them. The three reads -> area_N: a walker kind gets its own table, its 3DS vl's
last group (Kuribo {1, 2, 14, 8, 0, 0} on, Waddle Dee {1, 0, 10, 2, 0, 12} on; Shy Guy, Waddle Doo, Churine off, as
on the 3DS; area 1 (kind 9) theirs too); other kinds read their slot's as before.

Stomp detection (fix v8; in game the footstool never reached the Goomba even with its tread area on, so the fighter
side doesn't tread on these enemies -- the area set-up itself is the 3DS's, code.bin 0x756EE0: same kinds 0xE / 9,
same flags 0 / 40960.0): slot 3 (update) -> w_upd, then BehaviorImpl's update 0x026A4880. For a kind with a TREAD
state, not in it nor in its death state: each live fighter of slots 0-3 (the fighter table [[0x1035184C]]: entries
0x76B0 apart, +0x1E live >= 4, +0xC accessor, its PostureModule +0x18: x +0x10, y +0x14) whose y went from at / above
the tread box's top last frame (this +0x1A0 + 4 * slot; 0 = no last frame yet) to at / below it now, and not below
its bottom, within its half width -> change_state_interrupt(TREAD) and the fighter's MSC StatusModule(3, 0xB3, 0)
(change status to StepJump, the footstool jump: tools/position_vars_cave.py's way, ctx {0, accessor}). The box: the
Goomba's 3DS area 0 (node 2, 14 x 8, offset 0) as half width 7 around the posture x, centre the posture y + 2.53
(node 2 HipN in the bind pose), half height 4. Approximated: the box is not moved with the animation or the model's
scale, and the fighter's feet are its posture origin (not its ECB); no jump input is needed (a fall onto it does).
Step 2g v3: the test is relative to the enemy (PREV keeps the fighter's y minus the box top, so a rising / sinking
flier is handled) and swept (a crossing of the box top this frame counts down to the box's height + STOMP_SWEEP 4 below
it: a fast fall stepped over Tiki Buzz's 3-unit box); a defeated enemy (+0x19C) is skipped (Tiki Buzz's 11 / 12).

Hooks (2a's three stay as they are):
- F2, the factory 0x02DB94CC after 2a's hook: 0x02DB951C `cmplwi r12, 0x10` -> for the walker kinds
  module+8 = create(module+4, K, variation) then the factory's epilogue 0x02DB96E0; else the instruction and
  0x02DB9520.
- T2, battle load 0x02D9A46C `cmpwi r0, 1` (after 2a's table hook): on a Smash Run stage motion data set table
  0x10352610[K] = K's set.
- S2, the battle's param load 0x02D9A618 `lwz r0, 0x5EC(r28)` (after 2a's slot hook): on a Smash Run stage
  param slot[K] = slot[0x5A] (mczakozima: the activation and accessor set-up read [slot]+0x70 / +0x5C unchecked).

Motion data sets (+0 entries*, +4 count, +8..+0x14 0, the entries {hash, flags} from +0x18): K's 3DS
motion_data_set_<name> in its own order (so the 3DS motion indices hold), hash zlib.crc32(stem, 0xFFFFFFFF), flags
the 3DS word >> 16. Script hashsets (Kuribo, Shy Guy, Churine): crc32(lower(name) + ".init" / "" / ".exit").

Fix v3 (every Smash Run kind < 0x50, 2a's twins included):
- slot 38: the walker's returns 0, and the twins' (vtable words 0x1008FFCC zima, 0x1008F1D4 plasmawisp,
  0x1008EC68 darios) -> twin_flip: 1 for kinds >= 0x50, 0 below; their ADDR32 relocations moved to RELOC_DUMMY
  0x037EE73C. `--keep-flip` builds without it.
- initialize_after 0x02DB4AC8, 0x02DB4B20 `lwz r10, 0(r31)` -> for kinds < 0x50 set_lr(posture lr, 1, 1).
- notify_on_remove 0x02DB40E4 `mflr r0` -> for kinds < 0x50 type 0 becomes 3 (the defeat effect path 0x02DB3AB0).
- step 2g v3: slots 49 / 50 (set_lr / reverse_lr) -> w_slr / w_rlr (the game's, then w_yaw) in the cave's vtables and
  the twins' (TWIN_LR, relocations moved to RELOC_DUMMY): the 3DS-flip kinds (YAW_FLIP; from step 2g v6 only YAW_HOLD,
  the ones without a model.flp: the others flip for real, slot 38 = 1) keep yaw -90 at lr 1, their
  camera-facing lr -1 view, which the 3DS mirrors for lr 1 (lr 1 showed their backs: the "sometimes facing away" spawns).

Space: 0x04B86800-0x04B88000 (kind_expand.py's old space after smashrun_enemy_cave.py), 0x04B89000-0x04B8A000
(free between base_effects_cave.py and base_customs_cave.py) and 0x04BB8000-0x04BB8660 (the grown text after
weapon_expand.py, up to the text region's end 0x04BB8670; grow:0x04BB8660). Code in the first two and the area hooks
at the start of the third (with the stomp test's body), the stomp hook's frame in the fourth (fix v8: 0x04B84900-
0x04B84A00, zero and unclaimed between stage_omega_cave.py's LIMIT and boot_training_cave.py's CAVE, no branch, word
or lis / addi pair in the executable pointing into it), data after them (largest blocks first). To fit fix v7, state tables start at row 1 (id 0 -> 1 in change_state) and
P has five words.

Step 2k (code_2k, region H; docs/smash-run-port.md "Step 2k"): the Waddle Doo's beam (3DS states 7 / 8 as 10 / 11,
do_*: the Wii U's own weapon kind 0xAF through the 3DS's article set art_doo / spawner do_beam_cb, its own static param
object wdp in slot 0x19), the Churine's sleep powder (3DS 6 / 7 as 8 / 9, ch_*), the twins' own params (k2_twins:
param/enemy/fs/enemy_param_vl_<K>.bin in the twin's layout, tools/smashrun_twin_params.py), the White Bear's weakness
(wb_31 / wb_dmg). Test: tools/smashrun_step2k_test.py.

Step 2l (docs/smash-run-port.md "Step 2l"): every walker / flier kind its own static param object in its 3DS layout
(kind_param_blocks; S2 slot[K]); the Waddle Doo's hit effect in DO_FX (not V8, the landing's hop flag); the Waddle Dee's
parasol (art_dee / wd_para_cb / wd_drop: the Wii U's own weapon kind 0xAD); Lethinium's state 2 update through pw2_up
(no Fortress-only forced level-2 attack). Test: tools/smashrun_step2l_test.py.
"""
import math
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm, ha, lo  # noqa: E402
import smashrun_field_cave as F  # noqa: E402

CAVE, LIMIT = 0x04B86800, 0x04B88000
CAVE_B, LIMIT_B = 0x04B89000, 0x04B8A000
CAVE_C, LIMIT_C = 0x04BB8000, 0x04BB8660
CAVE_D, LIMIT_D = 0x04B84900, 0x04B84A00    # fix v8: free between stage_omega_cave.py and boot_training_cave.py
# step 2c: Smash Run's own unused space (zero and unreferenced in exe_v12, checked): the field cave's tail before its
# DATA (its code ends 0x04B7D430; F.CODE_LIMIT keeps it below CAVE_E), smashrun_enemy_cave.py's gaps (code to
# 0x04B8597C, sets to 0x04B8621C) and the old .text end before position_vars_cave.py's 0x04B78000
CAVE_E, LIMIT_E = 0x04B7D600, 0x04B7DF00    # code, then data
DATA_F = ((0x04B85980, 0x04B85C00), (0x04B86220, 0x04B86800), (0x04B77E20, 0x04B78000))     # data only
# step 2e: the fliers' code and data, in new code space after the text region's old end 0x04BB8670 (the RPL file
# info's textRegionSize raised to TEXT_REGION, the text section grown to LIMIT_G: nothing there in exe_v15)
CAVE_G, LIMIT_G = 0x04BB8680, 0x04BC0000
# step 2h: region H, the text grown again by 64 KB (the file info's textRegionSize raised with it; nothing is mapped
# there in exe_v24: the text ends at 0x04BC0000 and the data starts at 0x10000000)
CAVE_H, LIMIT_H = 0x04BC0000, 0x04BD0000
TEXT_REGION = LIMIT_H - 0x02000000
REGIONS = ((CAVE, LIMIT), (CAVE_B, LIMIT_B), (CAVE_C, LIMIT_C), (CAVE_D, LIMIT_D), (CAVE_E, LIMIT_E),
           (CAVE_G, LIMIT_G), (CAVE_H, LIMIT_H)) + DATA_F
GROW = LIMIT_H

# the framework (docs/smash-run-port.md, Step 2b / Fix v5)
OPNEW = 0x03374578
BEH_CTOR = 0x02DB2DF0
SET_MOTION_LABEL = 0x02DB5B08
SET_DAMAGE_LABEL = 0x02DB5AD8
CHANGE_MOTION = 0x02DB420C
BULLET = 0x02DB5158
CHANGE_KINETIC = 0x02DBE00C          # EnemyKineticModule (acc+0x30E8)
SET_ATTACH_GROUND = 0x02C37C6C       # GroundModule (acc+0x30DC)
IS_TOUCH = 0x02C38A24                # GroundModule; 8 = on the ground, 2 / 4 = wall left / right
MOTION_IS_END = 0x02C5F114           # MotionModule (acc+0x30F0)
ATK_CLEAR = 0x02C08324               # AttackModule (acc+0x30C8) clear_all
ATK_CREATE = 0x02DB572C              # Behavior::create_attack_data(InnerEnemyAttackParam const&)
ATK_SET = 0x02C086A8                 # AttackModule set_attack(id, part, AttackData&)
SET_RHOMBUS = 0x026A65BC
NEAREST = 0x026A7008                 # get_nearest_target() -> id / -1
CHECK_TURN = 0x026A6984              # check_turn_to_target(id, f1 distance)
CHECK_WALL = 0x026A68E4              # check_wall()
CHECK_CLIFF_LR = 0x026A6D88          # check_cliff with lr f1 (check_cliff_distance_lr by the speed)
CHECK_CLIFF = 0x026A6E24             # check_cliff(): the posture lr -> CHECK_CLIFF_LR
SEARCH = 0x026A70A4                  # search_target(type r4, &vec r5, f1..f5) -> check_target 0x02DB9F24
GET_TARGET_POS = 0x026A690C          # (out, this, id): get_fighter_pos (own position for id < 0)
GET_SPEED = 0x026A678C               # get_current_speed (out, this): get_sum_speed3f(1)
IS_STOPPED = 0x026A679C              # is_current_stopped(): |speed x| < 0.05
CLEAR_SPEED = 0x026A67E8             # clear_speed_all()
CHG_BASE = 0x026A3A44                # change_state_base(id, &update, &enter, &exit) (deferred)
CHG_INT = 0x026A3AD4                 # change_state_interrupt_base (now)
SET_CORRECT = 0x02C36458             # GroundModule set_correct(kind) (the twins' calls with 0 / 5)
# v2: Behavior helpers found on the Wii U (each the 3DS function's twin: the same module calls)
REQ_QUAKE = 0x026A9648               # request_quake(kind): CameraModule (acc+0x30CC) vt+0x1CC (3DS 0x7B0F0C)
REQ_EFFECT = 0x026A951C              # request_effect(id, &pos, &rot (degrees), scale) (3DS 0x7B12E0)
REQ_EFFECT0 = 0x026A94CC             # request_effect(id, &pos, scale) (3DS 0x7B1338)
REQ_FOLLOW = 0x026A95F8              # request_follow_effect(id, node, &offset, &rot, scale) -> handle (3DS 0x7B4AEC:
#                                      EffectModule req_follow 0x02C2AF98, the 3DS's 14-argument shape; step 2f)
REQ_NODE = 0x026A9584                # request_effect(id, node, &offset, &rot, scale) (3DS 0x7B1384: EffectModule req
#                                      on a node, the vtable slot after req(pos), as on the 3DS; not a follow: steps
#                                      2c-2e called this one as REQ_FOLLOW)
REMOVE_EFFECT = 0x026A95E4           # remove_effect(handle) (3DS 0x7B0EF0)
QUAKE_KIND = 6                       # the 3DS bear's request_quake(7); 6 is the largest any Wii U enemy asks for
NOTIFY_DEATH = 0x0269FD6C            # BehaviorImpl::notify_on_death (slot 71: death flag, hit off, attacks cleared)
# fix v7: the sites reading [param slot]+0x70 (the area table): (site, word, dst, base, the kind's register, kind * 4)
AREA_SITES = ((0x02D89898, 0x81450070, 10, 5, 0, True),       # the Enemy's area set-up: add_area(2 areas)
              (0x02D8A24C, 0x834C0070, 26, 12, 0, False),     # activation: area i off where entry i's word 0 == 0
              (0x02D8FB98, 0x810A0070, 8, 10, 0, True))       # area 0 (tread) on / off again by entry 0
TREAD_SLOT = 20                      # the 3DS's slot 21 (stepped on): Enemy event 6 -> module 0x02DB98F4 -> it
COMMON_PMF = 0x102FDBCC              # BehaviorImpl::common_state_func
BI_VT = 0x1008AEBC
ZIMA_CAPTURE_MOTION = 0x026D6E18     # slot 12
ZIMA_ONE = 0x026D7C98                # li r3, 1
ZIMA_REMOVE_ENTER = 0x026D7B58
ZIMA_REMOVE_UPDATE = 0x026D7B6C
SLOT_DONOR = 0x5A                    # mczakozima

MOTION_SETS = 0x10352610
PARAM_MGR = 0x102F6C00
SLOTS = 0x60

SITE_F, WORD_F = 0x02DB951C, 0x280C0010      # cmplwi r12, 0x10
FACTORY_NEXT, FACTORY_END = 0x02DB9520, 0x02DB96E0
SITE_T, WORD_T = 0x02D9A46C, 0x2C000001      # cmpwi r0, 1
SITE_S, WORD_S = 0x02D9A618, 0x801C05EC      # lwz r0, 0x5EC(r28)
# fix v3 (enemy-wide, for the Smash Run kinds < 0x50: 2a's four and the walkers)
SITE_ROT, WORD_ROT = 0x02DB4B20, 0x815F0000  # initialize_after: lwz r10, 0(r31)
SITE_DEATH, WORD_DEATH = 0x02DB40E4, 0x7C0802A6   # notify_on_remove: mflr r0
# ---- step 2e: the fliers (the Wii U's EnemyAerialModuleImpl, as mczakoplasmawisp embeds it; 3DS names / addresses)
AER = 0x1B0                          # the aerial module in a flier (0x74 bytes; the 3DS behaviours' +0x168)
FL_SIZE = 0x230                      # a flier object: the walker's 0x1B0, the aerial module, 3 words
AER_CTOR = 0x02DB2C44                # EnemyAerialModuleImpl(acc) (3DS 0x5F6BAC): +0 acc, +4 / +8 energies, mode -1
AER_UPDATE = 0x02DB28C8              # update() -> update(1.0, 1.0, true) 0x02DB2524 (3DS 0x5F6B80 / 0x5F66AC)
AER_SLIP_HOMING = 0x02DB28E4         # set_mode_slip_homing(f1-f6) (3DS 0x5F5F58: mode 2, params +0x10..+0x24)
AER_SLIP_HOMING_EXT = 0x02DB2A48     # set_mode_slip_homing_extend (3DS 0x5F64FC: slip homing, then mode 3)
AER_SET_SPEED = 0x02DB2BC0           # set_current_speed(Vector2&) (3DS 0x5F5C58): energy 0's speed x / y
GROUND_NORMAL = 0x02D64ABC           # GroundCollisionObject::get_ground_normal(mask) -> (r3, r4) = (x, y) bits
#                                      (3DS 0x96A538; the GroundModule's +0x18, as is_touch 0x02C38A24 reads it)
SET_PASSABLE = 0x02C367C4            # GroundModule set_passable_check(bool) (3DS 0x4E1B84)
SQRTF = 0x04ADEAB8                   # sqrtf (get_distance 0x02DB2C08 tail-calls it)
HIT_FACTOR = 0x02DB4ED4              # the 3DS's 0x9EB4C0 (hit_return_frame's factor: gl +0x158..+0x164, the
#                                      DamageModule (acc+0x30D4) float +0x6C through 0x026A81F8)
BI_NOTIFY_DMG = 0x026A3564           # BehaviorImpl::notify_on_damage (slot 10; the 3DS's slot 11)
# step 2g v4: Ghos's immunity (3DS slot 31 0x113F0 / slot 11 0x11094). The Wii U's slot 31 is the 3DS's: BehaviorImpl's
# 0x026A48EC (BI_VT +0x104) reads the hit record exactly as the 3DS's 0x3DD654 (r4 the hit: +0x14 AttackData, its
# byte +0x4C -> this +0x160; +0x20 the attacker record, byte +0x27 -> +0x15C); the EnemyBehaviorModule (acc+0x30EC,
# vtable 0x10122340) calls it through its +0xF4 entry 0x02DB9988 (Behavior +0xE0 vtable +0x104)
INIT_DAMAGE = 0x02C212F0             # DamageModuleImpl::init_damage(float) (3DS 0x4D30BC: every entry (Wii U 0xE4
#                                      bytes at [+0xC], [+8] of them; 3DS 0xE0) +0 = f, +4 / +8 / +0xC4 = 0, +0xD4 0)
GH_IMM, GH_DMG = FL_SIZE, FL_SIZE + 4    # Ghos's 3DS +0x1F4 (immune this hit) / +0x1F8 (the damage to restore)
GH_SE = FL_SIZE + 8                  # step 2m: the gas loop's sound handle (3DS +0x200)
GH_SIZE = FL_SIZE + 0xC
# step 2f (Furiijio; docs/smash-run-port.md "Step 2f")
CENTER_POS = 0x026A7104              # Behavior::center_pos (out, this): ModelModule node_global_position(center_node)
SET_NODE_ROT = 0x02C64188            # MotionModule set_node_rotate(node, &rad, compose) (3DS 0x501328) -> changed
SET_NODE_TRANS = 0x02C642C8          # MotionModule set_node_translate(node, &v, global, b) (3DS 0x501954)
MODEL_NODE_DIRTY = 0xC4              # the ModelModule (acc+0x3118) vt slot both callers make after a change (3DS +0x60)
ATK_SET_OFFSET = 0x02C09150          # AttackModule set_offset(id, &v) (3DS 0x4CB8B8; entries 0x84, +0x6C on)
EFF_SET_POS = 0x02C2C0C0             # EffectModule set_pos(handle, &v) (3DS 0x4DAF8C; EffectSystem 0x032F0978)
EFF_SET_SCALE = 0x02C2C120           # EffectModule set_scale(handle, &v) (3DS 0x4DB438; EffectSystem 0x032F0A48)
SINF, COSF, ACOSF = 0x04ADEB48, 0x04ADF434, 0x04ADF800      # libm (identified by running them; acosf: calc_angle's)
FU = 0x230                           # Furiijio's own fields after the flier's (object FU_SIZE)
FU_C, FU_ROT, FU_E = FU, FU + 0xC, FU + 0x18                 # center offset (3DS +0x218), node angles (+0x224), effects
FU_SE, FU_BND = FU + 0x28, FU + 0x2C  # step 2m: the beam's sound handle (3DS +0x260), the bound sound's flag (+0x264)
FU_SIZE = FU + 0x30
# step 2g (Propeller Heiho; docs/smash-run-port.md "Step 2g"): the Wii U's item calls and the helpers it was missing
CREATE_ITEM = 0x026A8D78             # Behavior::create_item(kind, var, &pos, &rot, bool) -> Item* (3DS 0x7B214C: init_normal
#                                      0x030519B4 + ItemManager::create_item 0x0305542C); create_item_and_have 0x7B4104
#                                      itself is gone on the Wii U (no caller): the cave does its two item calls
ITEM_MGR = 0x102F9B30                # [ITEM_MGR] = the ItemManager (lib::Singleton<app::ItemManager>::instance_)
FIND_ITEM = 0x030563AC               # ItemManager::find_item(id) -> Item* / 0 (3DS 0x3CD464; Item +0 id, +4 kind)
ITEM_WARP = 0x0303207C               # Item::warp(Vector3 const&) (3DS 0x74E174)
ITEM_FALL = 0x03032D78               # Item::fall(float, Vector3 const&) (3DS 0x74D6E4; ItemModule drop / throw call it)
IT_VT, IT_REMOVE, IT_ID, IT_HAVE = 0x24, 0x28C, 0x29C, 0x2FC   # the Item's vtable (+0x24; entries 8 bytes) slots 81
#                                      (remove(bool): +0x3B6E = 1), 83 (id), 95 (have(owner, ...)): the 3DS's
#                                      vt+0x144 / +0x14C / +0x17C (the same slot numbers)
NODE_GPOS = 0x0200739C               # ModelModule node_global_position(node, &v, bool) (acc+0x3118; 3DS 0x4A8xxx via
#                                      acc+0x3098, as center_pos 0x026A7104 calls it)
RAY_CHECK = 0x02C39F18               # GroundModule ray_check(V2 const& from, V2 const& dir, V2& out, bool) (3DS 0x9535F4)
IN_VIEW = 0x026A96BC                 # Behavior::is_in_view_area() (3DS 0x9EA804: CameraModule (acc+0x30CC) is_clip_in(1)
#                                      0x02C15EB8, the 3DS's 0x950DDC)
SUCCESS_PCT = 0x026A8618             # Behavior::success_by_percent(f1) (3DS 0x7B3BC4: the game's Randomizer < f1 x 0.01)
DAMAGE_TURN = 0x02DB4E84             # Behavior::damage_turn() (3DS 0x7B0814: DamageModule +0x98 lr != posture lr -> turn)
AER_UPDATE_XY = 0x02DB2524           # EnemyAerialModuleImpl::update(f1 x, f2 y, r4 brake) (3DS 0x5F66AC)
PH = 0x230                           # Propeller Heiho's own fields after the flier's (3DS +0x1DC..+0x20C)
PH_D, PH_B, PH_Y, PH_F, PH_T, PH_A, PH_R, PH_S, PH_DT, PH_I, PH_X = (PH + 4 * i for i in range(11))
PH_SIZE = PH + 0x2C
ITEM_NONE = 0x50000000
# step 2i: the stomped / killed Koopa's shell. The 3DS throws item 0x94 `patapata` (variation 1 for var 0 / 2, else
# 0): the Wii U item table has the kind (0x104157A0: {0x94, 0xB, 0xB, 0x101, 2, 0}) but no code path to its
# behaviour was found and its files (item/patapata/, a Smash Run item) are 3DS data, so the Wii U's Green Shell
# (kind 0x46 `greenshell`, the same kickable shell) is thrown instead, variation 0 (APPROXIMATED)
KOOPA_SHELL = (0x46, 0)
PH_FOOD, PH_GOLDBAG, PH_CUSTOM = 0x0E, 0x1D, 0x21  # tabemono (29 variations), goldbag, customizeitem (both games' tables)
PH_SWAP_FX = 0x100001C               # the item swap's effect (3DS: the item's EffectModule req, common effect 0x1C)
GL_INDEX, GL_BASE = 0x1E4, 0x34      # gl entry = [[PARAM_MGR] + 0x34] + 0x228 * [[PARAM_MGR] + 0x1E4 + 4 * (8K + var)]
VT_WORDS = [None]                    # BehaviorImpl's vtable words (read from the input), for code_f
TWIN_FLIP = ((0x1008FFCC, 0x026D7C98), (0x1008F1D4, 0x026D19F4), (0x1008EC68, 0x026CF200))
# step 2g v3: the kinds whose 3DS behaviour flips the model (slot 38 = is_flip_model returns 1: MotionModuleImpl::set_flip(lr
# == 1) in Behavior::set_lr 0x7B5778 / reverse_lr 0x7B034C; reference/smashrun_enemy_specs: kuribo, waddledee, waddledoo,
# churine, zima, plasmawisp, darios, tikibuzz, furiijio, propellerheiho; not heiho, stalfos, whitebear, gordo, ghos).
# Their models face the camera at lr -1 (yaw -90) and the 3DS shows lr +1 as that view mirrored; without the mirror
# (no Wii U flip table: fix v3) lr +1's yaw +90 showed their backs. w_yaw keeps yaw -90 for lr +1 (the mirror's front).
YAW_FLIP = (0x01, 0x13, 0x19, 0x1F, 0x0E, 0x12, 0x1D, 0x0F, 0x1A, 0x47, 0x23, 0x4E, 0x20)  # step 2h: dekakuribo, togezo
# step 2g v6: the real flip. The converted models now carry the 3DS model.flp as the Wii U's (tools/s3ds_enemy.py
# flp_bytes), so slot 38 returns 1 for the YAW_FLIP kinds that have one (FLIP_TABLE: the game's own set_lr 0x026A780C /
# reverse_lr 0x026A7A20 then call MotionModule 0x02C6108C(lr == 1, 1), the 3DS's set_flip(lr == 1, 1), and the anim
# mirror 0x036C48B0 mirrors the skeleton) and they keep lr x 90 (no yaw hold). Churine and Propeller Heiho flip on the
# 3DS but have no model.flp in either game (nothing to mirror): they keep the step 2g v3 yaw hold (YAW_HOLD).
FLIP_TABLE = (0x01, 0x13, 0x19, 0x0E, 0x12, 0x1D, 0x0F, 0x1A, 0x23, 0x4E, 0x20)   # step 2h: dekakuribo, togezo
YAW_HOLD = tuple(k for k in YAW_FLIP if k not in FLIP_TABLE)
SET_LR, REVERSE_LR = 0x026A780C, 0x026A7A20
# the twins' vtables (2a's zima / plasmawisp / darios use them): slots 49 / 50 -> w_slr / w_rlr (kinds >= 0x50 unchanged)
TWIN_LR = tuple((w - 0x13C + 0xC + 8 * k, orig, lab) for w, _f in TWIN_FLIP
                for k, orig, lab in ((49, SET_LR, 'w_slr'), (50, REVERSE_LR, 'w_rlr')))


def yaw_mask(kinds=None):
    m = [0, 0, 0]
    for k in YAW_HOLD if kinds is None else kinds:
        m[k >> 5] |= 1 << (k & 31)
    return m
RELOC_DUMMY = 0x037EE73C
SET_LR_SLOT = 49
KEEP_FLIP = False    # True: the variant that keeps the motion flip (only the rotation and death fixes)

OBJ_SIZE = 0x1B0                     # BehaviorImpl 0x168, +0x168 CFG*, +0x16C V0..V8, +0x190 Y0, +0x1A0 PREV


def V(i):
    return 0x16C + 4 * i


Y0 = 0x190
DEFEATED = 0x19C                     # v2: set by the death / collapse enters: the removal plays the defeat path
PREV = 0x1A0                         # fix v8: each fighter slot's (0-3) y last frame (0 = none yet)
FIGHTERS = 0x1035184C                # [[FIGHTERS]]: +0 entries, +8 count; entry 0x76B0: +0x1E live >= 4, +0xC acc
FIGHTER_ENTRY = 0x76B0
MSC_STATUS = 0x030B2B98              # MSC StatusModule wrapper (ctx {0, accessor}, args {words*, count})
STEP_JUMP = 0xB3                     # fighter status StepJump (the footstool jump off an opponent)
BI_UPDATE = 0x026A4880               # BehaviorImpl::update (slot 3): the state's update PMF
# the Goomba's tread area (its 3DS area 0: node 2, 14 x 8, offset 0): half width, centre above the posture
# (node 2 HipN 2.53 in its bind pose), half height
TREAD_BOX = (7.0, 2.53, 4.0)
# step 2n: the tread box in the model's scale. The 3DS area (AreaInstance set-up, code.bin 0x3D9278-0x3D92C4) takes the
# scale of its node's world matrix (|first column|, sqrt(m00^2 + m10^2 + m20^2); no node: the posture's +0x10) and,
# when it is not 1.0, multiplies the area's offset and size by it; the node matrix carries the model scale the enemy's
# activation sets (set_scale(gl entry +0x1C), docs/smash-run-port.md "Step 2a"). The boxes above are the vl's model
# units, so each is scaled here by its kind's +0x1C (Wii U param/enemy/gl/enemy_param.bin group 3, entry kind + 1,
# word 7: kuribo 1.2, tikibuzz 1.0, dekakuribo 1.3, patapata 1.5). A TNODE box's live node position is already scaled
TREAD_SCALE = {'kuribo': 1.2, 'tikibuzz': 1.0, 'dekakuribo': 1.3, 'patapata': 1.5}


def tread_box(w):
    """the kind's tread box (half width, centre above the posture / node, half height) in the model's scale"""
    s = TREAD_SCALE.get(w['name'], 1.0)
    return tuple(v * s for v in w.get('tbox', TREAD_BOX))
# step 2g v3: the stomp test is relative to the enemy (PREV keeps the fighter's y minus the box top) and swept: a
# crossing of the box top this frame counts down to the box's height + STOMP_SWEEP below it (a fast fall, 3.4 a
# frame at most, plus a rising flier, did step over Tiki Buzz's 3-unit box); dying / defeated enemies (+0x19C) skip
STOMP_SWEEP = 4.0
SLOT = {50: 0xC + 8 * 50, 72: 0xC + 8 * 72, 73: 0xC + 8 * 73}     # reverse_lr, change_state, interrupt

# CFG (per kind)
CF = {}
for _i, _n in enumerate(('KIND NST TAB START START01 R64 R65 R66 R67 REMOVE DEADMOT HASH EN ENN KICK SET ATK SRCH '
                         'FALLMOT LANDST LANDMOT TURNMOT TURNST WALKST HOPTHR HOPLAND HOPFLAG HOPMOT HOPLOOP ZERO TREAD AREA '
                         'SMODE LEAVE VT SIZE TB0 TB1 TB2 FSTART FDMG F69 F27 LVP TNODE BOUNCE VIS MVIS').split()):
    CF[_n] = 4 * _i
CF['DMG'] = 4 * len(CF)              # 9 words
CF['P'] = CF['DMG'] + 4 * 9          # the kind's own values P0.. (at least five words)
CFG_SIZE = CF['P'] + 4 * 5          # the walkers' (step 2c kinds have more P words: cfg_size())


def P(i):
    return CF['P'] + 4 * i


# InnerEnemyAttackParam (fs vl, 42 values; create_attack_data: +0xC node, +0x10 power, +0x14 angle, +0x18 kbg,
# +0x1C fkb, +0x20 bkb, +0x24 size, +0x28.. offset): the 3DS vl attack lists
KURIBO_BUMP = (5, 0, 0, 4, 1, 100, 100, 80, 0, 3, -1.0, 0.0, 0.0, 0, 0.0, 1.0, 1.0, 0, 0, 1, 0, 2, 3, 1, 2, 1, 0,
               9, 0, 1, 0, 0, 60, 0, 0, 1, 0, 0, 0, 0, 0, 0)
HEIHO_BUMP = (9, 0, 0, 0, 1, 50, 100, 60, 0, 4, 0.0, 8.0, 1.0, 0, 0.0, 1.0, 3.0, 0, 0, 1, 0, 1, 3, 1, 0, 1, 0,
              9, 0, 1, 0, 0, 4, 0, 0, 1, 0, 0, 0, 0, 0, 0)
# the defeated body's attack (Kuribo's; Waddle Dee's and Waddle Doo's are the same but for the state word, which
# create_attack_data does not read: the list holds the state)
BULLET_ATK = (9, 0, 0, 2, 2, 361, 100, 0, 50, 3, 0.0, 0.0, 0.0, 0, 0.0, 2.0, 1.0, 0, 0, 0, 2, 1, 3, 0, 2, 2, 0, 9,
              0, 0, 0, 0, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0)
HEIHO_BULLET = (15, 0, 0, 2, 2, 361, 100, 0, 50, 2, 0.0, 0.0, 0.0, 0, 0.0, 2.0, 1.0, 0, 0, 0, 2, 1, 3, 0, 0, 2, 0,
                9, 0, 0, 0, 0, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0)
CHURINE_BULLET = (8, 0, 0, 2, 1, 361, 100, 0, 50, 3, 0.0, 0.0, 0.0, 0, 0.0, 2.0, 1.0, 0, 0, 0, 2, 1, 3, 0, 2, 2, 0,
                  9, 0, 0, 0, 0, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0)
# step 2c (the vl files' P2 entries, typed as in the files): Gordo's spikes (states 1 and 2: the same entry but for
# the state word), the White Bear's defeated body (state 10)
GORDO_SPIKE = (1, 0, 0, 3, 10, 65, 50, 50, 100, 8, 0.0, 0.0, 0.0, 2, 0.0, 2.0, 1.0, 0, 0, 0, 2, 3, 7, 1, 2, 3, 0, 9,
               0, 0, 0, 0, 60, 0, 0, 0, 0, 1, 0, 0, 0, 0)
WHITEBEAR_BULLET = (10, 0, 0, 2, 8, 361, 100, 0, 50, 5, 0.0, 0.0, 0.0, 0, 0.0, 2.0, 1.0, 0, 0, 0, 2, 1, 3, 0, 0, 2, 0,
                    9, 0, 0, 0, 0, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0)
# v2: the White Bear's landing quake as an absolute attack: the AttackModule MSC op 0x2716 (set_abs) words in
# Throw_Specifier's order (kind, part, damage, angle, kbg, wbkb, bkb, effect, trip, hitlag, sdi, sfx level, sfx type,
# facing, disable hitlag, no reaction, type) from its vl P6 (InnerEnemyAttackAbsoluteParam {state 9, id 0, part 0,
# power 10, angle 90, kbg 100, fkb 0, bkb 40, 0, 1.0, 1.0, 1.0, 2, 1, 0, 0, 1, 0}; the 3DS struct's bytes / the
# three floats mapped by their order: effect 0, hitlag 1.0, sdi 1.0, sound level 2, sound type 1, facing 3 (the
# Wii U throws' default), no reaction 0, type 0)
ABS_WORDS = (0x2716, 0, 0, 10.0, 90, 100, 0, 40, 0, 0.0, 1.0, 1.0, 2, 1, 3, 0, 0, 0)
SPECS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reference', 'smashrun_enemy_specs')


def vl_group(kind, index):
    """the kind's fs vl group `index` (its entries, typed as in the file: floats stay floats), from the generated
    spec (reference/smashrun_enemy_specs/<kind>.json, read from the 3DS param files)"""
    import json
    with open(os.path.join(SPECS, kind + '.json')) as f:
        members = json.load(f)['params']['members']
    if index == 'struct':
        return [m for m in members if m['type'] == 'struct'][0]['values'][0]
    if index == 'struct2':                      # step 2h: the second inline struct
        return [m for m in members if m['type'] == 'struct'][1]['values'][0]
    return [m for m in members if m.get('index') == index][0]['values']


# step 2e: the fliers' vl P2 entries (the 3DS files' words)
GHOS_BODY = tuple(vl_group('ghos', 2)[1])          # state 1 (fly): power 3, angle 361, kbg 50, bkb 50, size 8, node 3
GHOS_BULLET = tuple(vl_group('ghos', 2)[0])        # state 4 (dead): power 3, angle 361, kbg 100, bkb 50, size 8
TIKI_DIVE = tuple(vl_group('tikibuzz', 2)[0])      # state 5 (dive): power 2, angle 60, kbg 120, fkb 50, size 4, y -1
TIKI_BULLET = tuple(vl_group('tikibuzz', 2)[1])    # state 2 (dead): power 2, angle 361, kbg 100, bkb 50, size 3
FU_BEAM0 = tuple(vl_group('furiijio', 2)[0])     # state 4 (beam): power 4, angle 361, kbg 100, fkb 100, size 2, node 3
FU_BEAM1 = tuple(vl_group('furiijio', 2)[1])     # state 7 (sweep beam): the same but +0x7C 140 (60 in entry 0)
FU_BULLET = tuple(vl_group('furiijio', 2)[2])    # state 9 (dead): power 3, angle 361, kbg 100, bkb 50, size 3, node 2
PH_BULLET = tuple(vl_group('propellerheiho', 2)[0])  # state 3 (dead): power 2, angle 361, kbg 100, bkb 50, size 2, node 2
ATTACKS = {'ph_bullet': PH_BULLET, 'fu_beam0': FU_BEAM0, 'fu_beam1': FU_BEAM1, 'fu_bullet': FU_BULLET, 'ghos_body': GHOS_BODY, 'ghos_bullet': GHOS_BULLET, 'tiki_dive': TIKI_DIVE, 'tiki_bullet': TIKI_BULLET, 'kuribo_bump': KURIBO_BUMP, 'heiho_bump': HEIHO_BUMP, 'bullet': BULLET_ATK, 'heiho_bullet': HEIHO_BULLET,
           'churine_bullet': CHURINE_BULLET, 'gordo_spike': GORDO_SPIKE, 'whitebear_bullet': WHITEBEAR_BULLET}
DAMAGE_LABELS = ('DamageStart', 'DamageFly', 'DamageFall', 'DownBound', 'DownBound', 'DownLoop', 'DownBoundEnd',
                 'DownWait')

# kinds (index in the name table 0x1041A22C). motions: the 3DS motion_data_set_<name> order (name, Wii U flags).
# energy: {offset: value} of the kind's 3DS initialize (variation 0); kick: it calls the kinetic module's vt
# (0x20000004). states: {3DS id: (enter, update)} (labels of this file, or game addresses). search: the vl search
# groups {type, interval, 5 floats}. attacks: (state, attack). P: the kind's own values (P0..).
WALKERS = (
    dict(name='kuribo', areas=((1, 2, 14.0, 8.0, 0.0, 0.0), (1, 2, 10.0, 12.0, 0.0, 0.0)), kind=0x01,
         motions=(('Collapses', 1), ('Damage', 1), ('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1),
                  ('DownBound', 1), ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1), ('Fall', 1),
                  ('Landing', 1), ('RunBrakeL', 1), ('RunHoldL', 1), ('RunL', 5), ('RunTurnL', 1), ('WalkL', 5)),
         dead='Damage', last='Fall', hashset=True, kick=True,
         energy={8: 2.0, 0xC: 1.5, 0x10: 0.02, 0x14: 0.001, 0x18: 0.01, 0x20: -0.4, 0x24: 1.6, 0x2C: 5.0,
                 0x40: 1.0, 0x44: 0.8},
         states={1: ('g_fall_en', 'g_fall_up'), 2: ('g_land_en', 'g_land_up'), 3: ('k_walk_en', 'k_walk_up'),
                 4: ('kc_ntc_en', 'k_ntc_up'), 5: ('k_run_en', 'k_run_up'), 6: ('k_brk_en', 'k_brk_up'),
                 7: ('k_rt_en', 'k_rt_up'), 8: ('kc_col_en', 'kc_col_up'), 9: ('g_dead_en', 'g_dead_up'),
                 10: 'remove'},
         tread=8,
         start=(1, 1), rets=(3, 1, 1, 9), remove=10, fall=('Fall', 2), landing='Landing', turn=None, turnst=0,
         walkst=3, hop=(0.0, 0, 0),
         search=((2, 100, 100.0, 40.0, 10.0, 10.0, 0.0), (2, 60, 150.0, 60.0, 0.0, 10.0, 0.0)),
         attacks=((5, 'kuribo_bump'), (9, 'bullet')),
         # walk rate, hop x, run rate, notice frames, run frames; step 2j: P5-P7 the collapse's dead item (P0 f14
         # frame 1, create_dead_item(1, 10)), P8 / P9 P0 f7 / f8 (the notice hop's ledge distance), 2, -2
         P=(0.6, -0.4, 1.0, 30, 110, 1, 10.0, 1.0, -0.4, 1.6, 2.0, -2.0)),
    dict(name='heiho', areas=((0, 0, 1.0, 1.0, 0.0, 0.0), (1, 2, 6.0, 10.0, 0.0, 0.0)), kind=0x0B,
         motions=(('Damage', 1), ('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1),
                  ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1), ('Fall', 1), ('Landing', 1), ('Run', 1),
                  ('RunBrake', 5), ('RunHold', 1), ('RunTurn', 1), ('Turn', 1), ('Wait', 1), ('Walk', 1)),
         dead='DamageStart', last='Fall', hashset=True, kick=True,
         energy={8: 0.3, 0xC: 10.0, 0x10: 0.3, 0x14: 0.0, 0x18: 0.0, 0x20: 0.5, 0x24: 2.5, 0x28: 0.5, 0x2C: 2.5,
                 0x40: 1.0},
         states={1: ('g_fall_en', 'g_fall_up'), 2: ('g_land_en', 'g_landt_up'), 3: ('h_wait_en', 'h_wait_up'),
                 4: ('h_walk_en', 'h_walk_up'), 5: ('g_turn_en', 'h_turn_up'), 6: ('g_hop_en', 'g_hop_up'),
                 7: ('h_ntc_en', 'h_ntc_up'), 8: ('h_hold_en', 'h_hold_up'), 9: ('h_run_en', 'h_run_up'),
                 10: ('h_wrt_en', 'h_wrt_up'), 12: ('h_brk_en', 'h_brk_up'), 13: ('h_rt_en', 'h_rt_up'),
                 14: ('h_set_en', 'h_set_up'), 15: ('g_dead_en', 'g_dead_up'), 16: 'remove'},
         start=(1, 1), rets=(4, 1, 1, 15), remove=16, fall=('Fall', 2), landing='Landing', turn='Turn', turnst=5,
         walkst=4, hop=(0.5, 2, 0), hop_motion=('Walk', 1),     # step 2j: P@0x90 0.5 (6 update 0x1B5B8)
         vtover={69: 'hh_69'}, fstart='w_start',                 # step 2j: slot 69 0x1BF70
         search=((2, 30, 120.0, 40.0, 10.0, 10.0, 0.0), (2, 30, 150.0, 36.0, 0.0, 12.0, 0.0)),
         attacks=((9, 'heiho_bump'), (15, 'heiho_bullet')),
         # walk frames min / max, hold frames (row 1 +0x10), run frames (row 2 +0x10), run turn rate (+0x78)
         P=(60, 120, 0, 80, 0.7),
         rows={'walk': {0x10: 0.3, 8: 0.3, 0x14: 0.0, 0x20: 0.5, 0x24: 2.5, 0x28: 0.5, 0x2C: 2.5},
               'run': {0x10: 0.8, 8: 0.8, 0x14: 0.0075, 0x20: 0.5, 0x24: 2.5, 0x28: 0.5, 0x2C: 2.5},
               'jump': {0x20: 0.0, 0x28: 0.0, 0x24: 2.0, 0x2C: 2.0, 0x1C: 0.0}}),
    dict(name='waddledee', areas=((1, 0, 10.0, 2.0, 0.0, 12.0), (1, 2, 10.0, 10.0, 0.0, 0.0)), kind=0x13,
         motions=(('Damage', 1), ('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1),
                  ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1), ('Fall', 1), ('Jump', 0x40),
                  ('Landing', 1), ('ParasolFall', 1), ('Turn', 1), ('Walk', 1)),
         dead='Damage', last='Jump', hashset=False, kick=False,
         energy={8: 0.2, 0x10: 0.2, 0x18: 0.0005, 0x20: 0.3, 0x24: 2.5, 0x28: 0.3, 0x2C: 2.5, 0x44: 1.0},
         states={1: ('wd1_en', 'g_fall_up'), 2: ('wd2_en', 'wd_para_up'), 3: ('wd3_en', 'g_land_up'),
                 4: ('wd4_en', 'd_walk_up'), 5: ('wd5_en', 'g_turn_up'), 6: ('wd6_en', 'd_jump_up'),
                 7: ('wd7_en', 'g_dead_up'), 8: 'remove'},     # step 2i: wdN_en = the enter + 0x5D04C (wd_show)
         vtover={51: 'wd_51', 60: 'wd_60', 69: 'wd_69', 71: 'wd_71'}, fstart='wd_start',
         start=(1, 2), rets=(4, 1, 1, 7), remove=8, fall=('Fall', 3), landing='Landing', turn='Turn', turnst=5,
         walkst=4, hop=(0.0, 0, 0),
         search=(),                   # 3DS {2, 30, 300, 100, 0, 10, 0}: never searches
         attacks=((7, 'bullet'),),
         size=FL_SIZE,                # step 2j: the aerial module (AER) for the parasol fall
         # walk rate (+0x84), jump interval / chance %, wall jump chance % (+0x78..); step 2j: P4 P0 f5 (0.2, the
         # parasol fall's speed), P5 -1 (its aerial update's y)
         P=(1.2, 100, 50, 50, 0.2, -1.0)),
    dict(name='waddledoo', areas=((0, 2, 1.0, 1.0, 0.0, 0.0), (1, 2, 8.0, 10.0, 0.0, 0.0)), kind=0x19,
         motions=(('BeamShot', 1), ('BeamShotHold', 1), ('Damage', 1), ('DamageFall', 1), ('DamageFly', 1),
                  ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1),
                  ('Fall', 1), ('Jump', 1), ('Landing', 1), ('Turn', 1), ('Walk', 1)),
         dead='Damage', last='Jump', hashset=False, kick=False,
         energy={8: 0.3, 0x10: 0.3, 0x20: 0.5, 0x24: 2.4, 0x28: 0.5, 0x2C: 2.4},
         states={1: ('g_fall_en', 'do_fall_up'), 2: ('g_land_en', 'g_landt_up'), 3: ('o_walk_en', 'o_walk_up'),
                 4: ('g_turn_en', 'g_turn_up'), 5: ('g_hop_en', 'do_hop_up'), 6: ('g_dead_en', 'g_dead_up'),
                 7: 'remove', 8: ('o_leave_en', 'o_leave_up'), 9: ('do_jump_en', 'do_jump_up'),   # step 2j: 9 = 3DS 6
                 10: ('do_ch_en', 'do_ch_up'), 11: ('do_bm_en', 'do_bm_up')},    # step 2k: the beam (3DS 7 / 8)
         vtover={55: 'do_55', 56: 'do_56', 57: 'do_57', 58: 'do_58', 69: 'do_69'}, fstart='w_start',  # 2i: the eyes
         # the 3DS's 10 / 11 / 9 (dead / remove / leave), 6 the hop (step 2j), 7 / 8 the beam (step 2k: 10 / 11)
         start=(1, 1), rets=(3, 1, 1, 6), remove=7, leave=600,   # start: +0x184 = PS8c f0 600
         size=0x1D0,                  # step 2k: DO_* (the beam's counters) after the walker's 0x1B0
         fall=('Fall', 2), landing='Landing', turn='Turn', turnst=4,
         walkst=3, hop=(0.5, 3, 0), hop_motion=('Jump', 0),     # step 2j: P@0xC0 0.5 (5 update 0x7D77C)
         search=((2, 60, 200.0, 200.0, 0.0, 0.0, 0.0), (2, 20, 60.0, 70.0, 30.0, 20.0, 0.0)),
         attacks=((6, 'bullet'),),
         # the leave (state 9, init_common_leave(P6 {300, 0.02, 30, -1, 0, 0, 3, 0, 0.85})): frames, the
         # energy's +0x30 (-0.02) / +0x34 (30), the leave effect's offset y and scale
         # step 2i: P5-P7 PS8c +0xB4 / +0xB8 / +0xBC (the blink); step 2j: P8 / P9 PS8c f1 / f2 (60, 50: the random hop)
         # step 2k (the beam, PS8c): P10 f3 1.0 (BeamShotHold rate), P11 f4 4.0 (BeamShot rate), P12 f5 150 (the
         # cool-down), P13 f8 2 (frames between shots), P14 f9 25 (the fan step, as a float), P15 180 / f9 = 7 shots
         # (0x7D0A4), P16 30.0 (the first angle, a literal at 0x7DB88)
         P=(300, -0.02, 30.0, 3.0, 0.85, 30, 50, 4, 60, 50, 1.0, 4.0, 150, 2, 25.0, 180 // 25, 30.0)),
    dict(name='churine', areas=((0, 0, 12.0, 12.0, 0.0, 0.0), (1, 3, 5.0, 10.0, 0.0, 4.0)), kind=0x1F,
         motions=(('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1),
                  ('DownLoop', 1), ('DownWait', 1), ('Jump', 1), ('Landing', 1), ('SleepPowder', 1), ('Turn', 1),
                  ('Walk', 1), ('Fall', 1)),
         dead='DamageStart', last='Fall', hashset=True, kick=False,
         energy={8: 0.7, 0x10: 0.1, 0x14: 0.05, 0x20: 0.2, 0x24: 2.5, 0x28: 0.2, 0x2C: 2.5},
         states={1: ('g_fall_en', 'g_fall_up'), 2: ('g_land_en', 'g_landt_up'), 3: ('c_walk_en', 'c_walk_up'),
                 4: ('c_jump_en', 'g_hop_up'), 5: ('g_turn_en', 'ch_turn_up'), 6: ('ch_dead_en', 'g_dead_up'),
                 7: 'remove', 8: ('ch_hop_en', 'ch_hop_up'), 9: ('ch_pw_en', 'ch_pw_up')},
         # the 3DS's 8 / 9 (dead / remove) as 6 / 7; step 2k: its 6 (the attack hop) / 7 (the sleep powder) as 8 / 9
         vtover={69: 'ch_69'}, fstart='ch_start',          # step 2k: slot 69 0x3DDE8, start 0x3CFF8 (+0x171 = 1)
         start=(1, 1), rets=(3, 1, 1, 6), remove=7, fall=('Fall', 2), landing='Landing', turn='Turn', turnst=5,
         walkst=3, hop=(20.0, 2, 1),
         search=((2, 3, 100.0, 35.0, 5.0, 5.0, 0.0),),      # step 2k: P1[0], the powder's search
         attacks=((6, 'churine_bullet'),),
         # step 2k (P0 f9..f13 and the literals of 6 / 7): P0 f9 1.0 (the hop's W+0x24), P1 10.0 (W+0x28 / +0x2C,
         # 0x3DC10), P2 f12 40 (the powder effect's frame), P3 / P4 f7 / f8 (0, 5: its offset), P5 f11 1.0 (scale),
         # P6 f10 1.4 (its rate), P7 f13 210 (the search cool-down), P8 / P9 90 / -90 (its rotation, 0x3DA68)
         P=tuple(vl_group('churine', 0)[0][i] for i in (9,)) + (10.0,) +
           tuple(vl_group('churine', 0)[0][i] for i in (12, 7, 8, 11, 10, 13)) + (90.0, -90.0)),
    # ---- step 2c
    # White Bear (Ice Climber) 0x40, BehaviorWhitebear (enemy_fs.cro create 0x7F420, table 0x111E8C)
    dict(name='whitebear', areas=((0, 2, 1.0, 1.0, 0.0, 0.0), (1, 3, 12.0, 26.0, 0.0, 5.0)), kind=0x40,
         motions=(('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1),
                  ('DownLoop', 1), ('DownWait', 1), ('Fall', 1), ('Landing', 1), ('Move', 1), ('QuakeFall', 1),
                  ('QuakeHold', 1), ('QuakeLanding', 1), ('QuakeUp', 1), ('SpecialTurn', 1), ('Turn', 1)),
         dead='DamageStart', last='Fall', hashset=True, kick=False,
         energy={0x10: 1.0, 8: 0.3, 0x14: 0.0},                 # initialize 0x7E738: P0 f1 / f2 / f3
         states={1: ('g_fall_en', 'g_fall_up'), 2: ('g_land_en', 'g_landt_up'), 3: ('b_walk_en', 'b_walk_up'),
                 4: ('b_sturn_en', 'g_turn_up'), 5: ('g_turn_en', 'g_turn_up'), 6: ('b_hold_en', 'wb_hold_up'),
                 7: ('b_up_en', 'b_up_up'), 8: ('b_fall_en', 'b_fall_up'), 9: ('b_land_en', 'b_land_up'),
                 10: ('g_dead_en', 'g_dead_up'), 11: 'remove'},
         start=(1, 1), rets=(3, 1, 1, 10), remove=11, fall=('Fall', 2), landing='Landing', turn='Turn', turnst=5,
         walkst=3, hop=(0.0, 0, 0),
         search=((2, 30, 300.0, 100.0, 0.0, 10.0, 0.0), (2, 60, 180.0, 140.0, 0.0, 10.0, 0.0)),
         attacks=((10, 'whitebear_bullet'),),
         # P0 (0x5C a row): walk frames f7 / f8, QuakeHold rate f9, jump f10, fall E+0x3C f11 / E+0x2C f12, landing
         # rate f13, long-fall frames f14, repeat chance f15 (%%, halved per landing), repeat landing rate f16, quakes
         # f17, search cool-down f18; 0.1 the jump's E+0x3C (a literal)
         P=(60, 120, 1.5, 1.5, 1.0, 3.0, 1.0, 180, 50, 0.5, 3, 60, 0.1,
            2.5, 8.0,         # v2: the landing effects' scales (0x7400000: the 3DS's (2.5, 1.7, 1) as 2.5; 0x7400001 8)
            5, vl_group('whitebear', 0)[0][19]),    # step 2k: set_weak_param(5, P0 f19 2.0) (its start 0x7E378)
         vtover={31: 'wb_31'}, fdmg='wb_dmg', fstart='w_start', size=0x1C0),  # step 2k: WB_W / WB_D (the weakness)
    # Gordo (Kirby) 0x08, BehaviorGordo (create 0x1A470, table 0x10F55C): variation 0 (the one the spawner makes)
    dict(name='gordo', areas=((0, 0, 12.0, 12.0, 0.0, 0.0), (0, 0, 14.0, 14.0, 0.0, 0.0)), kind=0x08,
         motions=(('Togetoge', 1),), no_damage_labels=True,       # its ctor 0x1A4A8: no hashsets, no damage labels
         dead=None, last=None, hashset=False, kick=True,
         energy={0x10: 0.0, 8: 0.0, 0x14: 0.0, 0x20: 0.0, 0x24: 0.0, 0x28: 0.0, 0x2C: 0.0, 0x40: 1.0, 0x18: 0.0,
                 0xC: 100.0},                                   # initialize 0x1A1D8 (variation 0's row: zeros)
         states={1: ('o_spin_en', 'o_nop'), 3: 'remove'},     # 2: variations 1-3 (moving on a path): not ported
         start=(1, 1), rets=(0, 0, 0, 0), remove=3, fall=(None, 0), landing=None, turn=None, turnst=0,
         walkst=0, hop=(0.0, 0, 0), smode=1,
         search=(),                   # 3DS {2, 30, 300, 100, 0, 10, 0}: never searches
         attacks=((1, 'gordo_spike'), (2, 'gordo_spike')),
         P=()),
)
_GS = vl_group('ghos', 'struct')     # P@0x8C: 20, 40, 96.0, 0.6, 0.8, 1200, 30.0
_GP7 = vl_group('ghos', 7)           # the two slip-homing sets
_GP6 = vl_group('ghos', 6)[0]        # the leave: {100, 0.02, 30, -1, 0, 0, 3, 0, 0.85}
_TP0 = vl_group('tikibuzz', 0)[0]    # Tiki Buzz's P0 row (variation 0)
_FS = vl_group('furiijio', 'struct')   # P@0x8C: 900, 2.5, 2, 1, 0.0, 1.0, 1.5, 25, 150, 20.0, 22, 4.5, 60, 34, 1, 1, 4.5, 140
_FP0 = vl_group('furiijio', 0)[0]      # P0 row, variation 0: set_mode_homing's six floats
_FP6 = vl_group('furiijio', 6)[0]      # the leave: {200, 0.01, 10, -1, 0, 0, 5, 0, 1}
DEG2RAD = struct.unpack('>f', bytes.fromhex('3C8EFA35'))[0]   # the 3DS literal (0.0174533)
# calc_angle's literals (3DS 0x7B01D8: pi / 2, 180, +-1 / pi), the clamp's -1 and the 2D rotation's small-angle
# test (0x67364: 1e-5)
FU_CALC = tuple(struct.unpack('>f', bytes.fromhex(h))[0] for h in ('3FC90FDB', '43340000', '3EA2F983', 'BEA2F983',
                                                                   'BF800000', '3727C5AC'))
FU_PD4 = 15.0                          # P@0xD4 (the beam hitbox's base offset; the spec's float after the struct)
_PP0 = vl_group('propellerheiho', 0)[0]    # P0 row (variation 0, 33 words: P(0)..P(32) = the 3DS P0 +0x00..+0x80)
_F = lambda h: struct.unpack('>f', bytes.fromhex(h))[0]  # noqa: E731
# Propeller Heiho's literals after its P0 row (the 3DS code's own constants; 0x3B360B61 = 1 / 360, 0x3C23D70A = 0.01)
PHK = dict(c01=33, c10=34, c50=35, c5=36, c1=37, cm1=38, c0=39, c360=40, deg=41, i360=42, half=43, stop=44, cm5=45)
PH_LIT = (_F('3DCCCCCD'), 10.0, 50.0, 5.0, 1.0, -1.0, 0.0, 360.0, DEG2RAD, _F('3B360B61'), 0.5, _F('3C23D70A'), -5.0)
FLIERS = (
    # Ghos (Kid Icarus) 0x11, BehaviorGhos (create 0x11560, table 0x10D350; docs/smash-run-port.md "Step 2e")
    dict(name='ghos', kind=0x11, flier=True, size=GH_SIZE, areas=tuple(tuple(e) for e in vl_group('ghos', 5)),
         motions=(('DamageStart', 1), ('FlyHoming', 1)), no_damage_labels=True,    # its ctor: no damage labels,
         dead='DamageStart', last=None, hashset=False, kick=False,                   # no hashsets
         energy={},                                      # initialize 0x10F74: bx lr
         states={1: ('f_g1_en', 'f_g1_up'), 2: ('gh2_en', 'gh2_up'), 3: ('f_leave_en', 'o_leave_up'),
                 4: ('gh_dead_en', 'g_dead_up'), 5: 'remove'},             # step 2i: gh_* = the f_* + the meshes
         start=(1, 1), rets=(1, 1, 1, 4), remove=5, fall=(None, 0), landing=None, turn=None, turnst=0, walkst=0,
         hop=(0.0, 0, 0), search=((0, 120, 300.0, 0.0, 0.0, 0.0, 0.0),),           # P1 (never searched)
         attacks=((1, 'ghos_body'), (4, 'ghos_bullet')),
         fstart='gh_start', fdmg='f_ghos_dmg', f69='f_ghos_69', f27='f_ghos_rm', lvp=19,
         vtover={55: 'f_g55', 31: 'f_g31'},              # step 2g v3: the 3DS's slot 55 0x10BA0 (the turn); v4: 31
         P=(_GS[0], _GS[1], int(_GS[2]), _GS[3], _GS[4], _GS[5], 0.1) + tuple(_GP7[0]) + tuple(_GP7[1]) +
           (_GP6[0], -_GP6[1], _GP6[2], _GP6[6], _GP6[8], 1.0, 0.0) + (_GS[6], DEG2RAD)),   # P26 P@0xA4 30, P27
    # Tiki Buzz (Kirby) 0x0F, BehaviorTikibuzz (create 0x78630, table 0x10E134)
    dict(name='tikibuzz', kind=0x0F, flier=True, size=FL_SIZE, areas=tuple(tuple(e) for e in vl_group('tikibuzz', 5)),
         motions=(('Attack', 1), ('AttackBrake', 1), ('AttackHold', 4), ('AttackUnguard', 1), ('DamageFall', 1),
                  ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1), ('DownLoop', 1),
                  ('DownWait', 1), ('Fly', 1), ('FlyReady', 1), ('Step', 1)),
         dead='DamageStart', last='Fly', hashset=False, kick=False,
         energy={0x44: _TP0[18]},                       # initialize 0x77DC8: energy +0x44 = P0 f18 (0.98)
         states={1: ('t_fall_en', 't_fall_up'), 2: ('g_dead_en', 'g_dead_up'), 3: ('tk_fly_en', 't_fly_up'),
                 4: ('t_hold_en', 't_hold_up'), 5: ('t_dive_en', 't_dive_up'), 6: ('t_brk_en', 't_brk_up'),
                 7: ('t_land_en', 't_land_up'), 8: ('t_rdy_en', 't_rdy_up'), 9: ('t_lv_en', 't_lv_up'),
                 10: ('tk_stomp_en', 't_stomp_up'), 11: ('tk_gone_en', 't_gone_up'), 12: 'remove'},
         tread=10, tbox=(6.0, 0.0, 1.5), tnode=3,      # area 0 (node 3 = HipN, 12 x 3): step 2g v5 centred on the
                                                       # live node (node_global_position), as the 3DS area is
         start=(3, 3), rets=(3, 3, 3, 2), remove=12, fall=(None, 0), landing=None, turn=None, turnst=0, walkst=0,
         hop=(0.0, 0, 0), search=tuple(tuple(g) for g in vl_group('tikibuzz', 1)),
         attacks=((5, 'tiki_dive'), (2, 'tiki_bullet')), fstart='tk_start', fdmg='tk_dmg', vtover={60: 'tk_60'},
         P=tuple(_TP0[:14]) + (int(_TP0[14]),) + tuple(_TP0[15:19]) + (float(_TP0[19]), _TP0[20]) +
           (vl_group('tikibuzz', 'struct')[0], _TP0[3], _TP0[4], _TP0[7], _TP0[8], _TP0[5], _TP0[6], 0.0)),
    # Furiijio (Kid Icarus) 0x1A, BehaviorFuriijio (create 0x6DC6C, table 0x10D168; docs/smash-run-port.md "Step 2f")
    dict(name='furiijio', kind=0x1A, flier=True, size=FU_SIZE, areas=tuple(tuple(e) for e in vl_group('furiijio', 5)),
         motions=(('DamageFall', 1), ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1),
                  ('DownLoop', 1), ('DownWait', 1), ('IceBeamShot', 1), ('IceBeamShotHold', 1), ('Move', 1)),
         dead='DamageStart', last='Move', hashset=False, kick=False,
         energy={},                                      # initialize 0x6C404: bx lr
         states={1: ('fu1_en', 'fu1_up'), 2: ('fu2_en', 'fu2_up'), 3: ('fu3_en', 'fu3_up'),
                 4: ('fu4_en', 'fu4_up', 'fu_bexit'), 5: ('fu5_en', 'fu5_up'), 6: ('fu6_en', 'fu6_up'),
                 7: ('fu7_en', 'fu7_up', 'fu_bexit'), 8: ('fu8_en', 'o_leave_up'), 9: ('fu9_en', 'g_dead_up'),
                 10: 'remove'},
         start=(1, 1), rets=(1, 1, 1, 9), remove=10, fall=(None, 0), landing=None, turn=None, turnst=0, walkst=0,
         hop=(0.0, 0, 0), search=tuple(tuple(g) for g in vl_group('furiijio', 1)),
         attacks=((4, 'fu_beam0'), (7, 'fu_beam1'), (9, 'fu_bullet')),
         fstart='f_fu_start', fdmg='f_fu_dmg', lvp=31,
         vtover={4: 'f_fu_skip', 61: 'f_fu_kin', 62: 'f_fu_kin'},
         P=tuple(_FP0[1:7]) + (_FS[0], _FS[1] * 10, _FS[2], _FS[3], _FS[4] * 10, _FS[5] * 10, _FS[6], _FS[7], _FS[8],
                               _FS[9] * 10, _FS[10], _FS[11], _FS[12], _FS[13], _FS[14], _FS[15], _FS[17],
                               180.0 / (_FS[17] or 1), FU_PD4, 1.5, 0.05, DEG2RAD, 90.0, 1.0, 0.0) +
           (_FP6[0], -_FP6[1], _FP6[2], _FP6[6], _FP6[8]) + FU_CALC),
    # Propeller Heiho (Mario) 0x47, BehaviorPropellerheiho (create 0x9AA38, table 0x111278; docs/smash-run-port.md
    # "Step 2g"): its ctor's damage labels (Damage x 8, Vertical); slot 69 always => 7, so they are never played
    dict(name='propellerheiho', kind=0x47, flier=True, size=PH_SIZE,
         areas=tuple(tuple(e) for e in vl_group('propellerheiho', 5)),
         motions=(('Damage', 1), ('Move', 1), ('TurnAir', 1), ('Vertical', 1)),
         dmg_labels=('Damage',) * 8 + ('Vertical',),
         dead='Damage', last='Vertical', hashset=False, kick=False,
         energy={},                                      # no initialize override
         states={1: ('ph1_en', 'ph1_up'), 2: ('ph2_en', 'ph2_up'), 3: ('ph3_en', 'ph3_up'), 4: ('ph4_en', 'ph4_up'),
                 5: ('ph5_en', 'ph5_up'), 6: ('ph6_en', 'ph6_up'), 7: ('ph7_en', 'ph7_up'), 8: 'remove'},
         start=(4, 4), rets=(4, 4, 4, 3), remove=8, fall=(None, 0), landing=None, turn=None, turnst=0, walkst=0,
         hop=(0.0, 0, 0), search=tuple(tuple(g) for g in vl_group('propellerheiho', 1)),
         attacks=((3, 'ph_bullet'),),
         fstart='f_ph_start', fdmg='f_ph_dmg', f69='f_ph_69', f27='f_ph_rm',
         vtover={55: 'f_ph_55', 59: 'f_ph_59'},
         P=tuple(_PP0) + PH_LIT),
)
WALKERS = WALKERS + FLIERS
# step 2h (docs/smash-run-port.md "Step 2h"; region H, code_h): Big Goomba, Spiny, Paratroopa / Koopa, Pooka
_DK0 = vl_group('dekakuribo', 0)[0]      # P0 row: f0..f19 (walk 2 / 1 / 10, rates, hops, 25 HP stomp, 28 close, 200)
# the 3DS create's hashset table (enemy_fs.cro 0xC5D3C: {name.init, name, name.exit} per motion): the scripts are
# named apart from the motions (AngryL's is "angry", motion 18's own Damage scripts)
DK_HS = (0x5D3BC3AA, 0xC0C12699, 0x0F46A3D0, 0x0E83541B, 0xD354F72A, 0x5CFE3461, 0x5EB275E0, 0xF1506564, 0x0CCF159A,
         0x8B2BBB41, 0x11C8546C, 0xD956DB3B, 0x23938046, 0x88866C6F, 0x71EEE03C, 0x7AB9FC7B, 0x592F6334, 0x28C49C01,
         0xB1F07FB5, 0x4BB1B3DE, 0xE38D1FCF, 0x5C6C76EE, 0x96507C35, 0x0E111694, 0x98299C4E, 0xCABD7352, 0xCA54FC34,
         0xDF4E2DE7, 0xFC437B83, 0x8D334D9D, 0x1C109455, 0x20F2E588, 0x4E6DF42F, 0x7FD00F18, 0xFB50DF0C, 0x2DAD6F62,
         0x916B53B2, 0xEF3ACE15, 0xC31633C8, 0x34D87757, 0xD7F912B4, 0x66A5172D, 0x9E38722F, 0x5076A4C0, 0xCC451255,
         0x6AC81B7E, 0x9A128179, 0x38B57B04, 0xDEEDAD68, 0xEC16504D, 0x8C90CD12, 0xD96E6992, 0x8D917A55, 0x8B1309E8,
         0x9EB09115, 0xBA133075, 0xCCCDF16F)
_TGS = vl_group('togezo', 'struct')      # PS8c: 0.4 (W+0x38), 10, 200 (walk frames), 150 (search frames)
_TG6 = vl_group('togezo', 6)[0]          # the leave: {120, 0.1, 5, 0, 0, 0, 3, 0, 0.85}
TG_SPIN = 30.0                           # the egg's spin, degrees a frame per unit of speed (the 3DS's common factor
#                                          EnemyParamAccessor +0x198 +0x90 x +0xA0 is not in the dump: approximated)
for _i, _n in enumerate(('tg_egg', 'tg_body', 'tg_eggdead', 'tg_dead')):    # togezo P2 0-3 (state 0, 0, 4, 12)
    ATTACKS[_n] = tuple(vl_group('togezo', 2)[_i])
# the 3DS create's hashset table (enemy_fs.cro 0xC75DC)
PT_HS = (0x82E7C6C0, 0x81E6391E, 0xD09AA6BA, 0x2E71FFFF, 0xA51BE995, 0x7C0C9F85, 0x8B2BBB41, 0x11C8546C, 0xD956DB3B,
         0x23938046, 0x88866C6F, 0x71EEE03C, 0x7AB9FC7B, 0x592F6334, 0x28C49C01, 0xB1F07FB5, 0x4BB1B3DE, 0xE38D1FCF,
         0x5C6C76EE, 0x96507C35, 0x0E111694, 0x98299C4E, 0xCABD7352, 0xCA54FC34, 0xDF4E2DE7, 0xFC437B83, 0x8D334D9D,
         0x1C109455, 0x20F2E588, 0x4E6DF42F, 0x7FD00F18, 0xFB50DF0C, 0x2DAD6F62, 0x8A5CA6C0, 0x538A83B3, 0xD821C6BA,
         0x6FE180E4, 0xCEFF938C, 0x3D9CE09E, 0x42FA02C2, 0xE96FB2C6, 0x108762B8, 0x916B53B2, 0xEF3ACE15, 0xC31633C8,
         0x1672FB23, 0x9E9898B1, 0x440F9B59, 0xFCEF9C58, 0x97CA47AB, 0xAE92FC22, 0xED2A8FBA, 0xA407A342, 0xBF57EFC0,
         0x28479585, 0x60DDFE28, 0x7A3AF5FF, 0x2E7A4ABC, 0x058D08B8, 0x7C072AC6, 0x1B824B30, 0xB749DECE, 0x49FF2B4A,
         0x7F3E1CA6, 0x20201547, 0x2D437CDC, 0xD96E6992, 0x8D917A55, 0x8B1309E8)
for _i, _n in enumerate(('pt_bite', 'pt_leap', 'pt_shell', 'pt_bullet')):  # patapata P2 0-3 (states 6, 16, 20, 8)
    ATTACKS[_n] = tuple(vl_group('patapata', 2)[_i])
STEP2H = (
    # Big Goomba (Mario) 0x23, BehaviorDekakuribo (create 0x86D84, table 0x10F374; docs/smash-run-port.md "Step 2h")
    dict(name='dekakuribo', kind=0x23, step2h=True, areas=tuple(tuple(e) for e in vl_group('dekakuribo', 5)),
         motions=(('AngryL', 1), ('AttackRunStart', 1), ('Collapses', 1), ('Damage', 1), ('DamageFall', 1),
                  ('DamageFly', 1), ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1), ('DownLoop', 1),
                  ('DownWait', 1), ('Fall', 1), ('Landing', 1), ('RunBrakeL', 1), ('RunL', 5), ('RunTurnL', 1),
                  ('Stepped', 1), ('WalkL', 5), ('Damage', 1)),
         dead=18, last='Fall', hashset=True, hs3ds=DK_HS, kick=True,
         energy={8: _DK0[1], 0xC: _DK0[2], 0x10: 0.0, 0x14: _DK0[5], 0x18: _DK0[3], 0x24: _DK0[7], 0x40: 1.0,
                 0x44: _DK0[14], 0x28: _DK0[6], 0x2C: _DK0[8]},     # initialize 0x8630C
         states={1: ('g_fall_en', 'g_fall_up'), 2: ('dk_land_en', 'g_land_up'), 3: ('dk_walk_en', 'dk_walk_up'),
                 4: ('dk_close_en', 'dk_close_up'), 5: ('dk_angry_en', 'dk_angry_up'), 6: ('dk_rs_en', 'dk_rs_up'),
                 7: ('dk_run_en', 'dk_run_up'), 8: ('dk_brk_en', 'k_brk_up'), 9: ('dk_rt_en', 'dk_rt_up'),
                 10: ('dk_step_en', 'dk_step_up'), 11: ('dk_col_en', 'dk_col_up'), 12: ('g_dead_en', 'g_dead_up'),
                 13: 'remove'},
         tread=11, tbox=(7.0, 6.0, 1.5),            # P5[0] {on, node 0, 14 x 3, offset (0, 6)}: 11 = skip in Collapses
         start=(1, 1), rets=(3, 1, 1, 12), remove=13, fall=('Fall', 2), landing='Landing', turn=None, turnst=0,
         walkst=3, hop=(0.0, 0, 0), search=tuple(tuple(g) for g in vl_group('dekakuribo', 1)),
         attacks=(),                                 # slot 45 is empty: every hitbox is the motions' ACMD
         vtover={45: 'o_nop', 20: 'dk_tread'}, fstart='w_start',
         P=tuple(_DK0) + (30.0, int(_DK0[19]), int(_DK0[10]), int(_DK0[13]))),   # P20 WalkL frames, P21-23 ints
    # Spiny (Mario) 0x4E, BehaviorTogezo (create 0x37F14, table 0x1119CC): variation 0 the egg (Paipo), 1 the Spiny
    dict(name='togezo', kind=0x4E, step2h=True, areas=tuple(tuple(e) for e in vl_group('togezo', 5)),
         motions=(('Change', 1), ('Damage', 1), ('Fall', 1), ('Landing', 1), ('Paipo', 1), ('Turn', 1), ('Walk', 1)),
         no_damage_labels=True, dead='Damage', last=None, hashset=False, kick=False, energy={},
         states={1: ('tg_efall_en', 'tg_efall_up'), 2: ('tg_ebnc_en', 'tg_ebnc_up'), 3: ('tg_estun_en', 'tg_estun_up'),
                 4: ('tg_edead_en', 'g_dead_up'), 5: ('tg_chg_en', 'tg_chg_up'), 6: ('tg_fall_en', 'g_fall_up'),
                 7: ('g_land_en', 'g_landt_up'), 8: ('tg_walk_en', 'tg_walk_up'), 9: ('g_turn_en', 'g_turn_up'),
                 10: ('tg_leave_en', 'o_leave_up'), 11: ('tg_stun_en', 'tg_stun_up'), 12: ('g_dead_en', 'g_dead_up'),
                 13: 'remove'},
         start=(1, 6), rets=(0, 0, 1, 4), remove=13, fall=('Fall', 7), landing='Landing', turn='Turn', turnst=9,
         walkst=8, hop=(0.0, 0, 0), search=tuple(tuple(g) for g in vl_group('togezo', 1)),
         attacks=(), vtover={40: 'tg_init', 45: 'tg_atk', 60: 'tg_60', 66: 'tg_66', 67: 'tg_67', 63: 'tg_63'}, fstart='tgv_start', f69='tg_69',
         lvp=18,                                     # TREAD 0: never stomped (its tread area is off, slot 21 BI's nop)
         P=tuple(vl_group('togezo', 0)[0]) + tuple(vl_group('togezo', 0)[1]) +
           (_TGS[0], _TGS[2], _TGS[3], vl_group('togezo', 'struct2')[0], TG_SPIN, DEG2RAD) +
           (_TG6[0], -_TG6[1], _TG6[2], _TG6[6], _TG6[8])),
    # Paratroopa / Koopa (Mario) 0x03, BehaviorPatapata (create 0x74108, table 0x110C80): variations 0 / 1 winged,
    # 2 / 3 walking (the wing loss adds 2); a flier-sized object (its bite uses the aerial module)
    dict(name='patapata', kind=0x03, step2h=True, flier=True, size=FL_SIZE,
         areas=tuple(tuple(e) for e in vl_group('patapata', 5)),
         motions=(('Bite', 1), ('BulletMode', 1), ('Damage', 1), ('DamageFall', 1), ('DamageFly', 1),
                  ('DamageStart', 1), ('DownBound', 1), ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1),
                  ('Fall', 1), ('Fly', 1), ('JumpAttack', 1), ('JumpHold', 1), ('Landing', 1), ('LandingJumpAttack', 1),
                  ('Fall', 1), ('NokonokoMode', 1), ('ShellMode', 1), ('ShellReturn', 1), ('TurnNokonoko', 1),
                  ('TurnPatapata', 1), ('Walk', 1)),     # 16: an entry with no name in the 3DS set (unused)
         dead='BulletMode', last='Fall', hashset=True, hs3ds=PT_HS, kick=False, energy={},
         states={1: ('pt_wfall_en', 'pt_wfall_up'), 2: ('pt_hop_en', 'pt_hop_up'), 3: ('pt_turn_en', 'pt_turn_up'),
                 5: ('pt_bw_en', 'pt_bw_up'), 6: ('pt_bite_en', 'pt_bite_up'), 7: ('pt_brec_en', 'pt_brec_up'),
                 8: ('g_dead_en', 'g_dead_up'), 9: ('pt_wl_en', 'pt_wl_up'), 10: ('g_fall_en', 'g_fall_up'),
                 11: ('g_land_en', 'g_land_up'), 12: ('pt_walk_en', 'pt_walk_up'), 13: ('g_turn_en', 'g_turn_up'),
                 14: ('pt_jh_en', 'pt_jh_up'), 15: ('pt_leap_en', 'pt_leap_up'), 16: ('pt_lh_en', 'pt_lh_up'),
                 17: ('pt_sl_en', 'pt_sl_up'), 18: ('pt_la_en', 'pt_la_up'), 19: ('pt_sh_en', 'pt_sh_up'),
                 20: ('pt_ss_en', 'pt_sh_up'), 23: 'remove'},
         tread=19, tbox=(2.0, 8.0, 4.0), bounce=1.0,   # P5[0] {on, node 0, 4 x 8, offset (0, 8)}; the user's 1.0
         start=(1, 1), rets=(2, 1, 1, 20), remove=23, fall=('Fall', 11), landing='Landing', turn='TurnNokonoko',
         turnst=13, walkst=12, hop=(0.0, 0, 0), search=tuple(tuple(g) for g in vl_group('patapata', 1)),
         attacks=((6, 'pt_bite'), (16, 'pt_leap'), (20, 'pt_shell'), (8, 'pt_bullet')),
         vtover={20: 'pt_tread', 64: 'pt_64', 65: 'pt_65', 66: 'pt_66', 67: 'pt_67', 63: 'pt_63'}, fstart='ptv_start', f69='pt_69',
         P=tuple(x for row in vl_group('patapata', 0) for x in row) + tuple(vl_group('patapata', 'struct')) +
           tuple(vl_group('patapata', 'struct2')) + (3.0, KOOPA_SHELL[0], 10.0, 1.0, -1.0)),
)
WALKERS = WALKERS + STEP2H
# ---- step 2j: Pooka (pooka 0x20; docs/smash-run-port.md "Step 2j"; enemy_fs.cro create 0x23C6C, table 0x10D9A8)
CHECK_CLIFF_DIST = 0x026A6CF4          # check_cliff_distance_lr(f1 distance, f2 lr) (3DS 0x9EAED4)
PK = FL_SIZE                         # Pooka's own words after the flier's (its object: PK_SIZE, the aerial module at
PK_SIZE = PK + 0x10                  # AER for energy 0): +0 deflating (3DS +0x189), +4 the model shown (GsbDrawModel::
#                                      is_visible: the last L65084 call), +8 an attack hit (slot 6, the 3DS's slot 7)
SET_FRAME = 0x02C5E494               # MotionModule set_frame(f1, r4 bool) (3DS 0x504928: the same flag byte +0x10F /
END_FRAME = 0x02C5E68C               # +0x113, frame +0x3C / +0x4C = 3DS +0x44 / +0x54); end_frame() -> r3 (3DS 0x953F98,
MOT_FRAME = 0x3C                     # u32 of +0x58 = 3DS +0x60); MOT_FRAME: the frame (3DS MotionModule +0x44)
ENABLE_HIT = 0x026A75D4              # Behavior::enable_hit (3DS 0x42FB14; disable_hit 0x026A75C0 = 3DS 0x7B0864)
CREATE_DEAD_ITEM = 0x02DB3944        # Behavior::create_dead_item(r4 bool, r5 int, f1, f2) (3DS 0x7B1984: the same
#                                      EnemyManager +0x5EC category test first: it returns at once unless 0 (fs), so on
#                                      the Smash Run stages (sm, field cave B) it drops nothing, as the removal's call)
PK_POP = 28                          # the pop's stand-in for SoundModule is_playing(0x6B10005): snd_se_enemy_Pooka_
#                                      Explosion is 9307 samples at 20000 Hz (the bank's TONE entry) = 27.9 frames
_PK0 = vl_group('pooka', 0)[0]       # P0 row f0..f35 (enemy_param_vl_pooka.bin)
ATTACKS['pk_lunge'] = tuple(vl_group('pooka', 2)[0])   # state 6: power 2, angle 20, kbg 100, bkb 50, size 5, node 4
ATTACKS['pk_pop'] = tuple(vl_group('pooka', 2)[1])     # state 11: power 6, angle 70, kbg 100, fixed 60, size 30, node 4
# the 3DS create's hashset table (the motion set's script hashes {init, main, exit} per motion, enemy_fs.cro 0xC47E0)
PK_HS = (0xF5DDECE6, 0x47C02D3B, 0xA7A08C9C, 0x5E9CC802, 0x2B37A469, 0x0CE1A878, 0xB58C363A, 0x8EF2C400, 0xE7F15640,
         0x23938046, 0x88866C6F, 0x71EEE03C, 0x7AB9FC7B, 0x592F6334, 0x28C49C01, 0xB1F07FB5, 0x4BB1B3DE, 0xE38D1FCF,
         0x5C6C76EE, 0x96507C35, 0x0E111694, 0x98299C4E, 0xCABD7352, 0xCA54FC34, 0xDF4E2DE7, 0xFC437B83, 0x8D334D9D,
         0x1C109455, 0x20F2E588, 0x4E6DF42F, 0x9AB9324C, 0xB86B689F, 0xC8C45236, 0x0CAE11BF, 0xEF3E3778, 0x5ED371C5,
         0x7F3E1CA6, 0x20201547, 0x2D437CDC)
# P36.. the literals of its code: 0.01, 100, 0.1, -0.8, 10, 20, 2, 180 / pi, pi / 180, 90, 180, 1, 0, -1, the pop
# timer's end (P34 - PK_POP), 1e-5, 3 (tan^2 60: state 3's drop test), 25 (P9 + 10), 0.5
PK_LIT = (0.01, 100.0, _F('3DCCCCCD'), _F('BF4CCCCD'), 10.0, 20.0, 2.0, 180.0 / math.pi, DEG2RAD, 90.0, 180.0, 1.0,
          0.0, -1.0, int(_PK0[34]) - PK_POP, _F('3727C5AC'), 3.0, _PK0[9] + 10.0, 0.5)
STEP2J = (
    # Pooka (Dig Dug) 0x20, BehaviorPooka: a flier-sized object (the aerial module: energy 0 for the ghost / slide)
    dict(name='pooka', kind=0x20, step2h=True, flier=True, size=PK_SIZE,
         areas=tuple(tuple(e) for e in vl_group('pooka', 5)),
         motions=(('Attack', 1), ('Attackhold', 1), ('Damageballoon', 1), ('DamageFall', 1), ('DamageFly', 1),
                  ('Damagestart', 1), ('DownBound', 1), ('DownBoundEnd', 1), ('DownLoop', 1), ('DownWait', 1),
                  ('Landiing', 1), ('Move', 1), ('Turn', 1)),
         dmg_labels=('Damagestart', 'DamageFly', 'DamageFall', 'DownBound', 'DownBound', 'DownLoop', 'DownBoundEnd',
                     'DownWait', 'Move'),
         dead='Damageballoon', last='Move', hashset=True, hs3ds=PK_HS, kick=False,
         energy={0x10: _PK0[1], 8: _PK0[2], 0x14: _PK0[3]},        # initialize 0x222BC
         states={1: ('pk_fall_en', 'pk_fall_up'), 2: ('pk_land_en', 'pk_land_up'), 3: ('pk_walk_en', 'pk_walk_up'),
                 4: ('pk_turn_en', 'pk_turn_up'), 5: ('pk_back_en', 'pk_back_up'), 6: ('pk_lunge_en', 'pk_lunge_up'),
                 7: ('pk_slide_en', 'pk_slide_up'), 8: ('pk_ghost_en', 'pk_ghost_up'), 9: ('pk_drop_en', 'pk_drop_up'),
                 10: ('pk_bal_en', 'pk_bal_up'), 11: ('pk_pop_en', 'pk_pop_up'), 12: 'remove'},
         start=(1, 1), rets=(3, 1, 1, 10), remove=12, fall=('Move', 2), landing='Landiing', turn='Turn', turnst=4,
         walkst=3, hop=(0.0, 0, 0), search=tuple(tuple(g) for g in vl_group('pooka', 1)),
         attacks=((6, 'pk_lunge'), (11, 'pk_pop')),       # Behavior::set_attack_data: P2 by state
         vtover={6: 'pk_hit', 12: 'pk_12', 16: 'pk_16', 51: 'pk_51', 56: 'pk_56', 60: 'pk_60', 70: 'pk_70'},
         fstart='pk_start', f69='pk_69',                  # TREAD 0: never stomped (tread area off, slot 21 BI's nop)
         P=tuple(_PK0) + PK_LIT),
)
WALKERS = WALKERS + STEP2J
KINDS = tuple(w['kind'] for w in WALKERS)


STEM_NAME = {'dekakuribo': 'DekaKuribo'}      # step 2h: the 3DS motion files' own capitalisation

# ---- step 2i: mesh switching (docs/smash-run-port.md "Step 2i"). The 3DS behaviours switch the meshes their model's
# normal.vmt lists through Behavior::set_mesh_visibility(vmt index, bool) (3DS 0x6618C4 -> ModelModulePartialImpl::
# set_node_visibility 0x6618D4: ModelModule +8 != 8 -> GsbDrawModel::set_mesh_visibility(int, bool) 0x7FB018) and the
# whole model through Behavior::set_visibility(bool) (0x661720). The Wii U's equivalents: the ModelModule (acc+0x3118)
# holds the model handle at +4 (vt+0x6C returns it); the handle API set_mesh_visibility_by_index 0x032FF6B4(handle,
# mesh, bool) -> 0x034232FC(model, mesh, bool, 0) writes bits 0-1 of the model's per-mesh byte ([model+0x7DC]+4,
# 0xFE at load: "not set") and is_valid 0x032FF640 (what the lua binding "set_mesh_visibility_by_index" 0x030F2880
# calls); ModelModule vt+0x164 = set_visibility(bool) 0x02007728 (the 3DS's 0x661720 line for line). The mesh index is
# the NUD's mesh order (the model's mesh list, 0x0342633C's by-name search runs over the same indices).
# VMT: each kind's normal.vmt (3DS index order); NUD_MESHES: the converted model.nud's meshes in order (a vmt name
# can be several NUD meshes: Big Goomba's three normal_mh); VIS_DEFAULT: the H3D model's visibility bit per vmt
# entry (the spawn state, h_vdef); MAT_VIS: the kinds whose faces the 3DS switches by material animation per motion
# (the converted material_anime.pac's MTAs, which the Wii U does not play for enemies): u_vis applies them per frame.
VMT = {
    'waddledee': ('waddledee_Cparasol_mh_VIS_O_OBJ', 'waddledee_Larm_mh_VIS_O_OBJ', 'waddledee_Lparasol_mh_VIS_O_OBJ',
                  'waddledee_Rarm_mh_VIS_O_OBJ', 'waddledee_Rparasol_mh_VIS_O_OBJ', 'waddledee_damage_mh_VIS_O_OBJ',
                  'waddledee_normal_mh_VIS_O_OBJ'),
    'waddledoo': ('waddledoo_eye_blink1_mh_VIS_O_OBJ', 'waddledoo_eye_blink2_mh_VIS_O_OBJ',
                  'waddledoo_eye_normal_mh_VIS_O_OBJ', 'waddledoo_tear_mh_VIS_O_OBJ'),
    'ghos': ('damage_VIS_O_OBJ', 'normal_VIS_O_OBJ'),
    'tikibuzz': ('Damage1_VIS_O_OBJ', 'Damage2_VIS_O_OBJ', 'Normal_VIS_O_OBJ'),
    'togezo': ('togezo_mh_VIS_O_OBJ', 'togezo_paipo_mh_VIS_O_OBJ'),
    'patapata': ('patapata_wing_VIS_O_OBJ',),
    'pooka': ('body_damage_mh_VIS_O_OBJ', 'body_normal_L_mh_VIS_O_OBJ', 'body_normal_R_mh_VIS_O_OBJ',
              'eye_damage_mh_VIS_O_OBJ', 'eye_normal_mh_VIS_O_OBJ', 'gogle_mh_VIS_O_OBJ', 'leg_mh_VIS_O_OBJ'),
    'kuribo': ('damage_mh', 'normal_mh'),                   # no vmt: the material animation's meshes (MAT_VIS)
    'dekakuribo': ('damage2_mh', 'damage_mh', 'normal_mh'),
}
NUD_MESHES = {
    'waddledee': VMT['waddledee'],
    'waddledoo': ('waddledoo_eye_blink1_mh_VIS_O_OBJ', 'waddledoo_eye_blink2_mh_VIS_O_OBJ',
                  'waddledoo_eye_normal_mh_VIS_O_OBJ', 'waddledoo_mh', 'waddledoo_tear_mh_VIS_O_OBJ'),
    'ghos': VMT['ghos'], 'tikibuzz': VMT['tikibuzz'], 'togezo': VMT['togezo'], 'pooka': VMT['pooka'],
    'patapata': ('body_mh', 'patapata_wing_VIS_O_OBJ'),
    'kuribo': ('damage_mh', 'normal_mh'),
    'dekakuribo': ('damage2_mh', 'damage_mh', 'normal_mh', 'normal_mh', 'normal_mh'),
}
VIS_DEFAULT = {                                             # the H3D models' visibility bits (s3ds_model.Bch)
    'waddledee': (1, 1, 1, 1, 1, 1, 1), 'waddledoo': (0, 0, 1, 1), 'ghos': (0, 1), 'tikibuzz': (0, 0, 1),
    'togezo': (1, 1), 'patapata': (1,), 'pooka': (0, 1, 1, 0, 1, 1, 1), 'kuribo': (0, 1), 'dekakuribo': (0, 0, 1),
}
MAT_VIS = {     # motion stem -> visible vmt entries (the converted material_anime.pac; other motions: default.mta)
    'kuribo': dict(default=(0, 1), **{m: (1, 0) for m in (
        'Collapses', 'Damage', 'DamageFall', 'DamageFly', 'DamageStart', 'DownBound', 'DownBoundEnd', 'DownLoop',
        'DownWait')}),
    'dekakuribo': dict(default=(0, 0, 1), **{m: (1, 0, 0) for m in ('Damage', 'DamageFly', 'DamageStart')},
                       **{m: (0, 1, 0) for m in ('Collapses', 'DamageFall', 'DownBound', 'DownBoundEnd', 'DownLoop',
                                                 'DownWait', 'Stepped')}),
}


def vis_table(name):
    """[n, default mask, then per vmt entry its NUD mesh indices packed from the top byte (0xFF: none; 4 at most)]"""
    out = [len(VMT[name]), sum(v << i for i, v in enumerate(VIS_DEFAULT[name]))]
    for m in VMT[name]:
        idx = [i for i, x in enumerate(NUD_MESHES[name]) if x == m][:4]
        out.append(sum(((idx[k] if k < len(idx) else 0xFF) << (24 - 8 * k)) for k in range(4)))
    return out


def mvis_table(w):
    """[motion count, then per motion index the visible-entry mask]"""
    t = MAT_VIS[w['name']]
    mask = lambda bits: sum(b << i for i, b in enumerate(bits))  # noqa: E731
    return [len(w['motions'])] + [mask(t.get(sfx, t['default'])) for sfx, _f in w['motions']]



def stem(name, sfx):
    return 'Enm%sBodyMain%s' % (STEM_NAME.get(name, name.capitalize()), sfx)


def motion_hash(s):
    return zlib.crc32(s.encode(), 0xFFFFFFFF)


def index(w, sfx):
    return [m for m, _f in w['motions']].index(sfx) if sfx else -1


def nstates(w):
    return max(k for k in w['states']) + 1


def fword(v):
    return struct.unpack('>I', struct.pack('>f', v))[0]


def word(v):
    return fword(v) if isinstance(v, float) else v & 0xFFFFFFFF


def sx(v):
    """signed 16-bit low half (for `addi` / `lwz` after `lis ha`)"""
    v = lo(v)
    return v - 0x10000 if v & 0x8000 else v


def branch(src, dst, link=False):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000
    return 0x48000000 | (off & 0x03FFFFFC) | (1 if link else 0)


def branch_target(src, word_):
    off = word_ & 0x03FFFFFC
    return src + (off - 0x4000000 if off & 0x2000000 else off)


def cfg_size(w):
    return CF['P'] + 4 * max(5, len(w['P']))


def damage_labels(w):
    """the nine set_damage_motion_label indices (all -1 for a kind whose 3DS create doesn't call it: then the call
    is skipped)"""
    if w.get('no_damage_labels'):
        return [-1] * 9
    if w.get('dmg_labels'):                     # step 2g: the 3DS create's own nine (motion names)
        return [index(w, s) for s in w['dmg_labels']]
    return [index(w, s) for s in DAMAGE_LABELS] + [index(w, w['last'])]


def cfg_values(w, D, fn=lambda x: 0):
    """the kind's CFG words (D: data labels, fn: code label -> address)"""
    n = w['name']
    lm = lambda s: index(w, s) if s else 0  # noqa: E731
    c = dict(KIND=w['kind'], NST=nstates(w), TAB=D['st_' + n] - 0x18, START=w['start'][0], START01=w['start'][1],
             R64=w['rets'][0], R65=w['rets'][1], R66=w['rets'][2], R67=w['rets'][3], REMOVE=w['remove'],
             DEADMOT=w['dead'] if isinstance(w['dead'], int) else lm(w['dead']), HASH=D.get('hs_' + n, 0), EN=D['en_' + n], ENN=len(w['energy']),
             KICK=1 if w['kick'] else 0, SET=D['set_' + n], ATK=D['atk_' + n], SRCH=D['sr_' + n],
             FALLMOT=lm(w['fall'][0]), LANDST=w['fall'][1], LANDMOT=lm(w['landing']), TURNMOT=lm(w['turn']),
             TURNST=w['turnst'], WALKST=w['walkst'], HOPTHR=fword(w['hop'][0]), HOPLAND=w['hop'][1],
             HOPFLAG=w['hop'][2], HOPMOT=lm(w.get('hop_motion', (None, 0))[0]),
             HOPLOOP=w.get('hop_motion', (None, 0))[1], ZERO=0, TREAD=w.get('tread', 0), AREA=D['ar_' + n],
             SMODE=w.get('smode', 0), LEAVE=w.get('leave', 0),
             VT=D['vt_' + n] if w.get('vtover') else D['vtf' if w.get('flier') else 'vt'], SIZE=w.get('size', OBJ_SIZE),
             TB0=fword(tread_box(w)[0]), TB1=fword(tread_box(w)[1]),
             TB2=fword(tread_box(w)[2]), FSTART=fn(w.get('fstart', 0)), FDMG=fn(w.get('fdmg', 0)),
             F69=fn(w.get('f69', 0)), F27=fn(w.get('f27', 0)), LVP=P(w['lvp']) if 'lvp' in w else 0,
             TNODE=w.get('tnode', 0), BOUNCE=fword(w.get('bounce', 0.0)),
             VIS=D.get('vis_' + n, 0), MVIS=D.get('mvis_' + n, 0))
    words = [0] * (cfg_size(w) // 4)
    for k, v in c.items():
        words[CF[k] // 4] = v & 0xFFFFFFFF
    for i, v in enumerate(damage_labels(w)):
        words[CF['DMG'] // 4 + i] = v & 0xFFFFFFFF
    for i, v in enumerate(w['P']):
        words[P(i) // 4] = word(v)
    return words


# ---------------------------------------------------------------- data
class Data:
    """the cave's data blocks: [(label, words, align)], placed by place()"""

    def __init__(self, vt_words):
        self.vt_words = vt_words
        self.addr, self.blocks = {}, []

    def build(self, cl, D=None):
        """cl: the code's labels; D: the data addresses of the previous pass (0s in the first)"""
        D = D or {}
        g = lambda k: D.get(k, 0)  # noqa: E731
        fn = lambda x: x if isinstance(x, int) else cl.get(x, 0)  # noqa: E731
        b = self.blocks = []
        b.append(('consts', [fword(0.0), fword(1.0), 0x2545F491, 0], 0x10))     # 0.0, 1.0, the xorshift state
        b.append(('abs_words', [word(v) for v in ABS_WORDS], 4))
        b.append(('fconsts', [0x43300000, 0x80000000], 8))      # the int -> double bias (f_hitret)
        b.append(('pend', [0] * 12, 4))     # step 2h: the stomp bounce, per fighter slot {accessor, multiplier, count}
        # step 2g v3: w_yaw (+0xC: the YAW_HOLD mask); step 2g v6: +0x18 the FLIP_TABLE mask (w_noflip / twin_flip)
        b.append(('yawk', [fword(1.0), fword(90.0), fword(-90.0)] + yaw_mask() + yaw_mask(FLIP_TABLE), 4))
        vt = list(self.vt_words) + [0, 0, 0, 0]          # 74 slots + 74 / 75
        over = {12: ZIMA_CAPTURE_MOTION, 38: ZIMA_ONE if KEEP_FLIP else fn('w_noflip'), 40: fn('w_init'),
                3: fn('w_upd'), 41: fn('w_start'), 45: fn('w_atk'), TREAD_SLOT: fn('w_tread'), 64: fn('w_r64'), 65: fn('w_r65'), 66: fn('w_r66'),
                67: fn('w_r67'), 72: fn('w_chg'), 73: fn('w_chgi'), 74: fn('w_chg'), 75: fn('w_chgi'),
                SET_LR_SLOT: fn('w_slr'), 50: fn('w_rlr')}       # step 2g v3: the 3DS flip's facing (YAW_FLIP)
        for k, f in over.items():
            vt[(0xC + 8 * k) // 4] = f
            vt[(0x8 + 8 * k) // 4] = 0
        b.append(('vt', vt, 4))
        vtf = list(vt)
        for k in (10, 27, 41, 69):
            vtf[(0xC + 8 * k) // 4] = fn('f_v%d' % k)
            vtf[(0x8 + 8 * k) // 4] = 0
        b.append(('vtf', vtf, 4))
        for w in WALKERS:                # step 2f: a kind's own vtable (VTF plus its overrides `vtover`)
            if w.get('vtover'):
                vk = list(vtf)
                for k, f in w['vtover'].items():
                    vk[(0xC + 8 * k) // 4] = fn(f)
                    vk[(0x8 + 8 * k) // 4] = 0
                b.append(('vt_' + w['name'], vk, 4))
        ktab = []
        for w in WALKERS:
            ktab += [w['kind'], g('cfg_' + w['name'])]
        b.append(('ktab', ktab + [0xFFFFFFFF], 4))
        # step 2k: the Waddle Doo's param object and article set, the twins' file names and object pointers
        for w in WALKERS:            # step 2l: every kind its own param object (step 2k: the Waddle Doo's)
            b += kind_param_blocks(w['name'], g)
        b.append(('art_doo', [g('art_doo') + 8, 1, WD_BEAM, 5, fn('do_beam_cb'), 0], 4))
        # step 2l: the Waddle Dee's (enemy_article_data_set_waddledee 0x111C08: {173, 1, 0x7C778})
        b.append(('art_dee', [g('art_dee') + 8, 1, WD_PARASOL, 1, fn('wd_para_cb'), 0], 4))
        b.append(('k2_dir', cstr('param/enemy/fs'), 4))
        for _t, k in TWIN_K:
            b.append(('k2_' + k, cstr('enemy_param_vl_%s.bin' % k), 4))
        b.append(('k2_objs', [0] * len(TWIN_K), 4))
        # step 2m: the 3DS sound rows (smashrun_sound.SND_ROWS: {row, bank id, label count, the list}, the lists as the
        # table's little-endian words), the twins' rows {row, the kind's bank (big-endian: stored byte-reversed), saved},
        # the Propeller Heiho's loop {handle, count} (enemy_fs.cro 0x111270: -1, 0), Stalfos's drop constants
        tab = []
        for row, (_k, bank, labs) in sorted(SND.SND_ROWS.items()):
            b.append(('snd_l_%x' % row, [struct.unpack('>I', struct.pack('<i', v))[0] for v in labs], 4))
            tab += [row, bank, len(labs), g('snd_l_%x' % row)]
        b.append(('snd_tab', tab + [0xFFFFFFFF], 4))
        b.append(('snd_twin', [x for row, (krow, _n, _b) in sorted(SND.TWIN_SND.items())
                               for x in (row, SND.SND_ROWS[krow][1], 0)] + [0xFFFFFFFF], 4))
        b.append(('ph_snd', [0xFFFFFFFF, 0], 4))
        b.append(('sf_consts', [fword(10.0), fword(-100.0)], 4))
        for name, entry in ATTACKS.items():
            b.append((name, [word(v) for v in entry], 4))
        for w in WALKERS:
            n = w['name']
            ms = w['motions']
            b.append(('set_' + n, [g('set_' + n) + 0x18, len(ms), 0, 0, 0, 0] +
                      [x for sfx, flags in ms for x in (motion_hash(stem(n, sfx)), flags)], 4))
            if w.get('hs3ds'):            # step 2h: the 3DS create's own hashset table (script names differ)
                b.append(('hs_' + n, list(w['hs3ds']), 4))
            elif w['hashset']:
                b.append(('hs_' + n, [zlib.crc32((sfx.lower() + x).encode()) for sfx, _f in ms
                                      for x in ('.init', '', '.exit')], 4))
            b.append(('en_' + n, [x for off, v in sorted(w['energy'].items()) for x in (off, fword(v))], 4))
            for row, en in sorted(w.get('rows', {}).items()):
                b.append(('row_%s_%s' % (n, row), [x for off, v in sorted(en.items()) for x in (off, fword(v))] +
                          [0xFFFFFFFF], 4))
            b.append(('sr_' + n, [word(v) for grp in w['search'] for v in grp], 4))
            b.append(('atk_' + n, [x for st, a in w['attacks'] for x in (st, g(a))] + [0xFFFFFFFF], 4))
            st = []
            for i in range(1, nstates(w)):         # row 0 is never used (id 0 -> 1)
                s = w['states'].get(i)
                if s == 'remove':
                    s = (ZIMA_REMOVE_ENTER, ZIMA_REMOVE_UPDATE)
                st += ([0xFFFF, fn(s[0]), 0xFFFF, fn(s[1])] + ([0xFFFF, fn(s[2])] if len(s) > 2 else [0, 0])
                       if s else [0] * 6)            # {enter, update, exit} PMFs (step 2f: an exit)
            b.append(('st_' + n, st, 4))
            b.append(('ar_' + n, [word(v) for e in w['areas'] for v in e], 4))
            if n in VMT:                  # step 2i: the mesh switch tables (h_vis / u_vis)
                b.append(('vis_' + n, vis_table(n), 4))
                if n in MAT_VIS:
                    b.append(('mvis_' + n, mvis_table(w), 4))
            need = ('st_', 'en_', 'set_', 'atk_', 'sr_', 'ar_') + (('hs_',) if w['hashset'] else ())
            need += tuple(p for p in ('vis_', 'mvis_') if (p == 'vis_' and n in VMT) or (p == 'mvis_' and n in MAT_VIS))
            dd = {p + n: g(p + n) for p in need}
            dd.update(vt=g('vt'), vtf=g('vtf'))
            if w.get('vtover'):
                dd['vt_' + n] = g('vt_' + n)
            b.append(('cfg_' + n, cfg_values(w, dd, fn), 4))
        return self

    def place(self, spans):
        """first fit into spans [(lo, hi)]; sets .addr, .chunks [(base, words)]"""
        spans = [list(s) for s in spans]
        self.addr, self.chunks = {}, []
        for label, words, al in sorted(self.blocks, key=lambda x: -len(x[1])):     # largest first
            for s in spans:
                a = (s[0] + al - 1) & ~(al - 1)
                if a + 4 * len(words) <= s[1]:
                    self.addr[label] = a
                    self.chunks.append((a, words))
                    s[0] = a + 4 * len(words)
                    break
            else:
                raise AssertionError('walker data does not fit (%s)' % label)
        self.free = [tuple(s) for s in spans]
        return self


# ---------------------------------------------------------------- code
def code(D):
    """two Asm units (regions A and B) from the data addresses D; returns (a, b)"""
    A, B = Asm(CAVE), Asm(CAVE_B)

    def far(a, t):
        a.asm("lis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctrl" % (t >> 16, t & 0xFFFF))

    def la(a, r, label):
        a.asm("lis %s, 0x%04X\naddi %s, %s, %d" % (r, ha(D[label]), r, r, sx(D[label])))

    def la4(label):
        return "lis r4, 0x%04X\naddi r4, r4, %d" % (ha(D[label]), sx(D[label]))

    def tail(a, t):
        a.asm("lis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctr" % (t >> 16, t & 0xFFFF))

    def lfs(a, fr, label, off=0):
        a.asm("lis r12, 0x%04X\nlfs %s, %d(r12)" % (ha(D[label] + off), fr, sx(D[label] + off)))

    # ---- the shared prologue / epilogue and helpers (r31 this, r30 CFG, r29 the AI input; helpers keep r28-r31)
    A.asm("""
    pro:
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        stmw r28, 0x20(r1)
        mr r31, r3
        lwz r30, 0x168(r3)
        mr r29, r4
        blr
    go:
        bl h_chg
    epi:
        lmw r28, 0x20(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    goi:
        bl h_chgi
        b epi
    h_chg:
        mr r3, r31
        lwz r12, 0xE0(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctr
    h_chgi:
        mr r3, r31
        lwz r12, 0xE0(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctr
    h_rev:
        mr r3, r31
        li r4, 1
        li r5, 1
        lwz r12, 0xE0(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctr
    h_kin:
        lwz r3, 0(r31)
        lwz r3, 0x30E8(r3)
        b 0x%08X
    h_att:
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        b 0x%08X
    h_gnd:
        li r4, 8
    h_touch:
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        b 0x%08X
    h_end:
        lwz r3, 0(r31)
        lwz r3, 0x30F0(r3)
        b 0x%08X
    """ % (SLOT[72], SLOT[73], SLOT[50], CHANGE_KINETIC, SET_ATTACH_GROUND, IS_TOUCH, MOTION_IS_END))
    # the Behavior helpers at 0x026Axxxx are beyond a `b` from the cave: through ctr
    for lab, t in (('h_wall', CHECK_WALL), ('h_cliff', CHECK_CLIFF), ('h_clear', CLEAR_SPEED),
                   ('h_stop', IS_STOPPED), ('h_near', NEAREST)):
        A.asm("%s:\nmr r3, r31" % lab)
        tail(A, t)
    A.asm("h_mot1:")
    lfs(A, 'f2', 'consts', 4)
    A.asm("h_mot:")
    lfs(A, 'f1', 'consts')
    A.asm("fmr f3, f1\nmr r3, r31\nb 0x%08X" % CHANGE_MOTION)
    A.asm("h_tchk:")                      # check_turn_to_target(r4 id, 0)
    lfs(A, 'f1', 'consts')
    A.asm("mr r3, r31")
    tail(A, CHECK_TURN)
    # h_vy0: f1 = the current speed's y, cr0 = f1 ? 0
    A.asm("""
    h_vy0:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        addi r3, r1, 8
        mr r4, r31
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        mtctr r12
        bctrl
        lfs f1, 0xC(r1)
        lis r12, 0x%04X
        lfs f0, %d(r12)
        fcmpu cr0, f1, f0
        b h_ret20
    """ % (GET_SPEED >> 16, GET_SPEED & 0xFFFF, ha(D['consts']), sx(D['consts'])))
    A.asm("""
    h_ret20:
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    h_dx:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        mr r5, r4
        addi r3, r1, 8
        mr r4, r31
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        mtctr r12
        bctrl
        lfs f1, 8(r1)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x10(r12)
        fsubs f1, f1, f0
        lfs f0, 0x10(r31)
        fmuls f1, f1, f0
        b h_ret20
    h_grp:
        lwz r12, %d(r30)
        mulli r0, r4, 0x1C
        add r12, r12, r0
        lwz r3, 4(r12)
        blr
    h_srch:
        lwz r12, %d(r30)
        mulli r0, r4, 0x1C
        add r12, r12, r0
        lwz r4, 0(r12)
        lfs f1, 0x10(r12)
        lfs f2, 0x14(r12)
        lfs f3, 8(r12)
        lfs f4, 0xC(r12)
        lfs f5, 0x18(r12)
        addi r5, r31, 0x10
        mr r3, r31
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        mtctr r12
        bctr
    h_mv:
        lwz r0, 0x10(r31)
        stw r0, 0(r29)
        lwz r0, 0x14(r31)
        stw r0, 4(r29)
        blr
    h_mv0:
        li r0, 0
        stw r0, 0(r29)
        stw r0, 4(r29)
        blr
    h_flag:
        lwz r12, 0(r31)
        lwz r12, 0x3130(r12)
        lwz r12, 8(r12)
        lwz r12, 0(r12)
        lwz r12, 0x14(r12)
        lwz r3, 0(r12)
        and. r3, r3, r4
        blr
    h_ebase:
        lwz r12, 0(r31)
        lwz r12, 0x3130(r12)
        lwz r10, 8(r12)
        lwz r10, 0(r10)
        lwz r10, 4(r10)
        blr
    h_en:
        mflr r9
        bl h_ebase
        mtlr r9
    en_loop:
        lwz r7, 0(r4)
        cmpwi r7, -1
        beqlr
        lwz r6, 4(r4)
        stwx r6, r10, r7
        addi r4, r4, 8
        b en_loop
    h_kick:
        lwz r12, 0(r31)
        lwz r3, 0x3130(r12)
        lwz r12, 0(r3)
        lwz r12, 0xFC(r12)
        mtctr r12
        lis r4, 0x2000
        ori r4, r4, 4
        bctr
    h_dy:
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        lfs f0, 0x%X(r31)
        fsubs f1, f1, f0
        fabs f1, f1
        blr
    h_sety:
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        stfs f1, 0x%X(r31)
        blr
    """ % (GET_TARGET_POS >> 16, GET_TARGET_POS & 0xFFFF, CF['SRCH'], CF['SRCH'], SEARCH >> 16,
           SEARCH & 0xFFFF, Y0, Y0))
    # h_rand(r3 lo, r4 hi) -> r3 in [lo, hi] (xorshift32 in consts+8)
    A.asm("h_rand:")
    la(A, 'r12', 'consts')
    A.asm("""
        lwz r0, 8(r12)
        slwi r11, r0, 13
        xor r0, r0, r11
        srwi r11, r0, 17
        xor r0, r0, r11
        slwi r11, r0, 5
        xor r0, r0, r11
        stw r0, 8(r12)
        subf r4, r3, r4
        addi r4, r4, 1
        divwu r11, r0, r4
        mullw r11, r11, r4
        subf r0, r11, r0
        add r3, r3, r0
        blr
    """)

    # ---- F2: the factory (r31 kind, r30 module, r29 variation, r12 = kind - 0x50)
    A.asm("cave_f:")
    la(A, 'r11', 'ktab')
    A.asm("""
    f_loop:
        lwz r10, 0(r11)
        cmpwi r10, -1
        beq f_other
        cmpw r10, r31
        beq f_mine
        addi r11, r11, 8
        b f_loop
    f_other:
        cmplwi r12, 0x10
        b 0x%08X
    f_mine:
        lwz r3, 4(r30)
        mr r4, r31
        mr r5, r29
        bl w_create
        stw r3, 8(r30)
        b 0x%08X
    """ % (FACTORY_NEXT, FACTORY_END))
    # ---- create(acc, kind, variation) -> the behaviour (0 for another kind / no memory)
    A.asm("""
    w_create:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r27, 0x1C(r1)
        mr r28, r3
        mr r29, r4
        mr r30, r5
        li r27, 0
    """)
    la(A, 'r11', 'ktab')
    A.asm("""
    c_loop:
        lwz r10, 0(r11)
        cmpwi r10, -1
        beq c_out
        cmpw r10, r29
        beq c_found
        addi r11, r11, 8
        b c_loop
    c_found:
        lwz r31, 4(r11)
        lwz r3, 0x%X(r31)
        bl 0x%08X
        mr. r27, r3
        beq c_out
        mr r4, r28
        mr r5, r29
        mr r6, r30
        bl 0x%08X
        li r0, 0
        addi r11, r27, 0xE0
        lwz r12, 0x%X(r31)
        addi r12, r12, -0xE4
        srwi r12, r12, 2
        mtctr r12
    c_zero:
        stwu r0, 4(r11)
        bdnz c_zero
        li r0, 1
        stb r0, 0x120(r27)
        li r0, -1
        stw r0, 0x15C(r27)
    """ % (CF['SIZE'], OPNEW, BEH_CTOR, CF['SIZE']))
    A.asm("""
        lwz r11, 0x%X(r31)
        stw r11, 0xE0(r27)
        lis r11, 0x%04X
        lwz r12, %d(r11)
        stw r12, 0xE8(r27)
        lwz r12, %d(r11)
        stw r12, 0xEC(r27)
        stw r31, 0x168(r27)
        mr r3, r27
        li r4, 0
        lwz r5, 0x%X(r31)
        bl 0x%08X
        lwz r4, 0x%X(r31)
        cmpwi r4, -1
        beq c_out
        mr r3, r27
    """ % (CF['VT'], ha(COMMON_PMF), sx(COMMON_PMF), sx(COMMON_PMF + 4), CF['HASH'], SET_MOTION_LABEL, CF['DMG']))
    for i, r in enumerate(('r4', 'r5', 'r6', 'r7', 'r8', 'r9', 'r10')):
        A.asm("lwz %s, 0x%X(r31)" % (r, CF['DMG'] + 4 * i))
    A.asm("""
        lwz r0, 0x%X(r31)
        stw r0, 8(r1)
        lwz r0, 0x%X(r31)
        stw r0, 0xC(r1)
        bl 0x%08X
    c_out:
        mr r3, r27
        lmw r27, 0x1C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    """ % (CF['DMG'] + 0x1C, CF['DMG'] + 0x20, SET_DAMAGE_LABEL))
    # ---- slot 40 initialize: the kinetic energy words (a leaf; the Churine's walk / hop call it too)
    A.asm("""
    w_init:
        lwz r11, 0x168(r3)
        lwz r12, 0(r3)
        lwz r12, 0x3130(r12)
        lwz r10, 8(r12)
        lwz r10, 0(r10)
        lwz r10, 4(r10)
        lwz r9, 0x%X(r11)
        lwz r8, 0x%X(r11)
        cmpwi r8, 0
        beq i_kick
        mtctr r8
    i_loop:
        lwz r7, 0(r9)
        lwz r6, 4(r9)
        stwx r6, r10, r7
        addi r9, r9, 8
        bdnz i_loop
    i_kick:
        lwz r0, 0x%X(r11)
        cmpwi r0, 0
        beqlr
        mr r3, r12
        lwz r12, 0(r3)
        lwz r12, 0xFC(r12)
        mtctr r12
        lis r4, 0x2000
        ori r4, r4, 4
        bctr
    """ % (CF['EN'], CF['ENN'], CF['KICK']))
    # ---- slot 41 start: set_rhombus, +0x10 = posture lr, face the nearest target, the first state
    # step 2i: the model's default meshes; step 2o: r3 = this again for set_rhombus (h_vdef used to return the last
    # set_mesh_visibility_by_index's 1 in r3: set_rhombus(1) read address 9, the step 2i crash at a Big Goomba /
    # Goomba / Waddle Dee / Waddle Doo spawn)
    A.asm("w_start:\nmflr r0\nbl pro\nmr r3, r31\nbl h_vdef\nmr r3, r31")
    far(A, SET_RHOMBUS)
    A.asm("lwz r0, 0x%X(r30)\ncmpwi r0, 0\nbeq s_lr\nbl h_smode" % CF['SMODE'])
    A.asm("""
    s_lr:
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x60(r12)
        stw r0, 0x10(r31)
        li r0, 0
        stw r0, 0x14(r31)
        stw r0, 0x18(r31)
        addi r11, r31, 0x168
        li r12, %d
        mtctr r12
    s_zero:
        stwu r0, 4(r11)
        bdnz s_zero
        lwz r0, 0x%X(r30)
        stw r0, 0x%X(r31)
        lwz r0, 0x%X(r30)
        cmpwi r0, 0
        bne s_state
        bl h_near
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        beq s_state
        bl h_rev
    s_state:
        lwz r4, 0x%X(r30)
        lwz r0, 0xC(r31)
        cmplwi r0, 1
        bgt s_go
        lwz r4, 0x%X(r30)
    s_go:
        b go
    """ % ((OBJ_SIZE - 0x16C) // 4, CF['LEAVE'], V(7), CF['SMODE'], CF['START'], CF['START01']))
    # ---- slot 20 (3DS 21): stepped on by a fighter (a footstool); the kind's state (CFG TREAD) => now, 0: nothing
    A.asm("""
    w_tread:
        lwz r12, 0x168(r3)
        lwz r4, 0x%X(r12)
        cmpwi r4, 0
        beqlr
        lwz r12, 0xE0(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctr
    """ % (CF['TREAD'], SLOT[73]))
    # ---- slots 64-67: the kind's states after damage on the ground / in the air / default, death
    for i, k in enumerate((64, 65, 66, 67)):
        A.asm("w_r%d:\nlwz r12, 0x168(r3)\nlwz r3, 0x%X(r12)\nblr" % (k, CF['R64'] + 4 * i))
    # ---- slots 72 / 73 change_state(id): the kind's table; unknown ids -> 1
    A.asm("""
    w_chg:
        lis r11, 0x%04X
        ori r11, r11, 0x%04X
        b w_chg2
    w_chgi:
        lis r11, 0x%04X
        ori r11, r11, 0x%04X
    w_chg2:
        lwz r12, 0x168(r3)
        lwz r0, 0x%X(r12)
        lwz r12, 0x%X(r12)
        cmplw r4, r0
        bge c2_one
        cmpwi r4, 0
        bne c2_in
    c2_one:
        li r4, 1
    c2_in:
        mulli r10, r4, 0x18
        add r6, r12, r10
        lwz r0, 0xC(r6)
        cmpwi r0, 0
        bne c2_ok
        li r4, 1
        addi r6, r12, 0x18
    c2_ok:
        addi r5, r6, 8
        addi r7, r6, 0x10
        mtctr r11
        bctr
    """ % (CHG_BASE >> 16, CHG_BASE & 0xFFFF, CHG_INT >> 16, CHG_INT & 0xFFFF, CF['NST'], CF['TAB']))
    # ---- slot 45 set_attack_data(state): clear_all, then the kind's attacks listed for this state
    A.asm("""
    w_atk:
        mflr r0
        bl pro
        mr r28, r4
        lwz r3, 0(r31)
        lwz r3, 0x30C8(r3)
        bl 0x%08X
        lwz r29, 0x%X(r30)
    a_loop:
        lwz r0, 0(r29)
        cmpwi r0, -1
        beq epi
        cmpw r0, r28
        bne a_next
        mr r3, r31
        lwz r4, 4(r29)
        bl 0x%08X
        lwz r12, 4(r29)
        lwz r4, 4(r12)
        lwz r5, 8(r12)
        stw r4, 0x84(r31)
        stw r5, 0x88(r31)
        lwz r3, 0(r31)
        lwz r3, 0x30C8(r3)
        addi r6, r31, 0x1C
        bl 0x%08X
    a_next:
        addi r29, r29, 8
        b a_loop
    """ % (ATK_CLEAR, CF['ATK'], ATK_CREATE, ATK_SET))

    # ---- states: f(a, label, body): a function with the shared prologue, `b epi` appended
    def st(a, label, body):
        a.asm("%s:\nmflr r0\nbl pro\n%s\nb epi" % (label, body))

    def en(a, label, kin, att, mot, loop, rate=None, extra='', pre=''):
        """an enter: [pre] kinetic, ground, motion (index / 'CFG field'), [extra]"""
        m = "lwz r4, 0x%X(r30)" % CF[mot] if isinstance(mot, str) else "li r4, %d" % mot
        r = "bl h_mot1" if rate is None else "lfs f2, 0x%X(r30)\nbl h_mot" % rate
        st(a, label, "%s\nli r4, %d\nbl h_kin\nli r4, %d\nbl h_att\n%s\nli r5, %d\n%s\n%s"
           % (pre, kin, att, m, loop, r, extra))

    # generic: fall (vy > 0: wait; on the ground => LANDST), landing, turn (end: reverse_lr => WALKST), dead
    en(A, 'g_fall_en', 8, 0, 'FALLMOT', 1)
    st(A, 'g_fall_up', "bl h_vy0\nbgt epi\nbl h_gnd\ncmpwi r3, 0\nbeq epi\nlwz r4, 0x%X(r30)\nb goi" % CF['LANDST'])
    en(A, 'g_land_en', 0, 1, 'LANDMOT', 0)
    st(A, 'g_land_up', "bl h_end\ncmpwi r3, 0\nbeq epi\nlwz r4, 0x%X(r30)\nb go" % CF['WALKST'])
    # landing that looks back (Shy Guy, Waddle Doo, Churine): unless V8 (a hop's landing), the nearest target
    # behind -> TURNST, else WALKST; V8 = 0
    st(A, 'g_landt_up', """
        bl h_end
        cmpwi r3, 0
        beq epi
        lwz r28, 0x%X(r30)
        lwz r0, 0x%X(r31)
        cmpwi r0, 0
        bne lt_go
        bl h_near
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        beq lt_go
        lwz r28, 0x%X(r30)
    lt_go:
        li r0, 0
        stw r0, 0x%X(r31)
        mr r4, r28
        b go""" % (CF['WALKST'], V(8), CF['TURNST'], V(8)))
    en(A, 'g_turn_en', 0, 1, 'TURNMOT', 0)
    st(A, 'g_turn_up', "bl h_end\ncmpwi r3, 0\nbeq epi\nbl h_rev\nlwz r4, 0x%X(r30)\nb goi" % CF['WALKST'])
    st(A, 'g_dead_en', "li r0, 1\nstw r0, 0x%X(r31)\nlwz r4, 0x%X(r30)\nli r5, 0\nbl h_mot0\nmr r3, r31\nbl 0x%08X"
       % (DEFEATED, CF['DEADMOT'], BULLET))
    A.asm("h_mot0:")                  # a motion at rate 0
    lfs(A, 'f2', 'consts')
    A.asm("b h_mot")
    st(A, 'g_dead_up', "li r4, 8\nbl h_flag\nbeq epi\nlwz r4, 0x%X(r30)\nb goi" % CF['REMOVE'])
    # a hop (Shy Guy 6, Waddle Doo 5, Churine 4): kinetic 5, ground off, Y0 = posture y; on landing: on the same
    # height (|dy| <= HOPTHR) or a wall still ahead (3DS ray_check(lr, 5)) => TURNST; else [HOPFLAG: V8 = 1] =>
    # HOPLAND
    st(A, 'g_hop_up', """
        bl h_vy0
        bgt epi
        bl h_gnd
        cmpwi r3, 0
        beq epi
        bl h_dy
        lfs f0, 0x%X(r30)
        fcmpu cr0, f1, f0
        ble hp_turn
        bl h_wall
        cmpwi r3, 0
        bne hp_turn
        lwz r0, 0x%X(r30)
        stw r0, 0x%X(r31)
        lwz r4, 0x%X(r30)
        b goi
    hp_turn:
        lwz r4, 0x%X(r30)
        b goi""" % (CF['HOPTHR'], CF['HOPFLAG'], V(8), CF['HOPLAND'], CF['TURNST']))
    # the hop enter of the Shy Guy (Walk loop) and the Waddle Doo (Jump): P-less, the motion from the kind's hop
    st(A, 'g_hop_en', "li r4, 5\nbl h_kin\nli r4, 0\nbl h_att\nlwz r4, 0x%X(r30)\nlwz r5, 0x%X(r30)\nbl h_mot1\n"
                      "bl h_sety" % (CF['HOPMOT'], CF['HOPLOOP']))

    # ---- Kuribo
    # walk: V0 frames, V3 target
    en(A, 'k_walk_en', 0xA, 1, 15, 1, rate=P(0), pre="li r0, 0\nstw r0, 0x%X(r31)" % V(0))
    st(A, 'k_walk_up', """
        li r4, 0
        bl h_grp
        lwz r0, 0x%X(r31)
        divwu r11, r0, r3
        mullw r11, r11, r3
        subf. r0, r11, r0
        bne kw_gnd
        li r4, 0
        bl h_srch
        stw r3, 0x%X(r31)
        cmpwi r3, 0
        blt kw_gnd
        mr r4, r3
        bl h_dx
        lfs f0, 0x%X(r30)
        fcmpu cr0, f1, f0
        bge kw_face
        bl h_rev
    kw_face:
        li r4, 4
        b goi
    kw_gnd:
        bl h_gnd
        cmpwi r3, 0
        bne kw_on
        li r4, 1
        bl h_chg
        b kw_in
    kw_on:
        bl h_cliff
        cmpwi r3, 0
        beq kw_wall
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        beq kw_rev
    kw_wall:
        bl k_wallt
        cmpwi r3, 0
        beq kw_in
    kw_rev:
        bl h_rev
        li r4, 3
        bl h_chg
    kw_in:
        bl h_mv
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)""" % (V(0), V(3), CF['ZERO'], V(0), V(0)))
    # k_wallt: is_touch(wall ahead: lr > 0 -> 4, else 2), cr0
    A.asm("k_wallt:\nlwz r0, 0x10(r31)\nli r4, 2\ncmpwi r0, 0\nble h_touch\nli r4, 4\nb h_touch")
    # notice: the startled hop (E+0x20 = P1, kinetic 5); V2 airborne; P3 frames after entering -> run (V1 = 0)
    en(A, 'k_ntc_en', 5, 0, 12, 1, pre="li r0, 0\nstw r0, 0x%X(r31)\nbl h_ebase\nlwz r0, 0x%X(r30)\nstw r0, 0x20(r10)"
       % (V(0), P(1)), extra="li r0, 1\nstw r0, 0x%X(r31)" % V(2))
    st(A, 'k_ntc_up', """
        lwz r0, 0x%X(r31)
        cmpwi r0, 1
        bne kn_wait
        bl h_vy0
        bgt kn_out
        bl h_gnd
        cmpwi r3, 0
        beq kn_out
        li r0, 0
        stw r0, 0x%X(r31)
        li r4, 1
        bl h_att
        b kn_out
    kn_wait:
        lwz r3, 0x%X(r31)
        lwz r0, 0x%X(r30)
        cmpw r3, r0
        ble kn_out
        li r4, 5
        bl h_chg
        li r0, 0
        stw r0, 0x%X(r31)
    kn_out:
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)""" % (V(2), V(2), V(0), P(3), V(1), V(0), V(0)))
    # run: V1 run frames; every search-1 interval a target behind -> 7; a wall / ledge (var 1) -> 7; off the
    # ground -> 1; after P4 frames -> 6
    en(A, 'k_run_en', 0xA, 1, 13, 1, rate=P(2))
    st(A, 'k_run_up', """
        li r4, 1
        bl h_grp
        lwz r0, 0x%X(r31)
        divwu r11, r0, r3
        mullw r11, r11, r3
        subf. r0, r11, r0
        bne kr_gnd
        li r4, 1
        bl h_srch
        stw r3, 0x%X(r31)
        cmpwi r3, 0
        blt kr_gnd
        mr r4, r3
        bl h_dx
        lfs f0, 0x%X(r30)
        fcmpu cr0, f1, f0
        bge kr_gnd
        li r4, 7
        bl h_chg
    kr_gnd:
        bl h_gnd
        cmpwi r3, 0
        bne kr_on
        li r4, 1
        bl h_chg
        b kr_time
    kr_on:
        bl h_cliff
        cmpwi r3, 0
        beq kr_wall
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        bne kr_wall
        bl h_clear
        b kr_turn
    kr_wall:
        bl k_wallt
        cmpwi r3, 0
        beq kr_time
    kr_turn:
        li r4, 7
        bl h_chg
    kr_time:
        lwz r3, 0x%X(r31)
        lwz r0, 0x%X(r30)
        cmpw r3, r0
        ble kr_in
        li r4, 6
        bl h_chg
    kr_in:
        bl h_mv
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)""" % (V(1), V(3), CF['ZERO'], V(1), P(4), V(1), V(1)))
    # brake: at a ledge (var 1) clear_speed_all, else off the ground -> 1; at its end -> 3; input (lr, 0)
    en(A, 'k_brk_en', 2, 1, 11, 0)
    st(A, 'k_brk_up', """
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        bne kb_g
        bl h_cliff
        cmpwi r3, 0
        beq kb_end
        bl h_clear
        b kb_end
    kb_g:
        bl h_gnd
        cmpwi r3, 0
        bne kb_end
        li r4, 1
        bl h_chg
    kb_end:
        bl h_end
        cmpwi r3, 0
        beq kb_in
        li r4, 3
        bl h_chg
    kb_in:
        bl h_mv
        li r0, 0
        stw r0, 4(r29)""")
    # run turn: at a ledge clear_speed_all; at its end reverse_lr => 5 (it came from the run)
    en(A, 'k_rt_en', 2, 1, 14, 0)
    st(A, 'k_rt_up', """
        bl h_cliff
        cmpwi r3, 0
        beq kt_end
        bl h_clear
    kt_end:
        bl h_end
        cmpwi r3, 0
        beq kt_in
        bl h_rev
        li r4, 5
        bl h_chgi
    kt_in:
        bl h_mv
        li r0, 0
        stw r0, 4(r29)""")

    # collapses (stepped on): kinetic 0, Collapses, ground on, notify_on_death; at its end -> 10 (the 3DS's
    # create_dead_item on frame 1 is left to the removal's defeat path, fix v3, which drops the items)
    en(A, 'k_col_en', 0, 1, 0, 0, extra="mr r3, r31\nlis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctrl\n"
       "li r0, 1\nstw r0, 0x%X(r31)" % (NOTIFY_DEATH >> 16, NOTIFY_DEATH & 0xFFFF, DEFEATED))
    st(A, 'k_col_up', "bl h_end\ncmpwi r3, 0\nbeq epi\nli r4, 10\nb go")

    # ---- Shy Guy (V0 search frames, V1 walk / hold frames, V2 run frames, V3 target, V4 hops / Wait loops,
    # V5 settle frames)
    def look(a, pfx, grp, then):
        """every interval frames (V0) search_target(grp) -> V3; found: `then` (asm, the id in r3)"""
        a.asm("""
        %s_look:
            li r4, %d
            bl h_grp
            lwz r11, 0x%X(r31)
            addi r11, r11, 1
            stw r11, 0x%X(r31)
            cmpw r11, r3
            ble epi
            li r0, 0
            stw r0, 0x%X(r31)
            li r4, %d
            bl h_srch
            stw r3, 0x%X(r31)
            cmpwi r3, -1
            beq epi
            mr r4, r3
            bl h_tchk
            cmpwi r3, 0
            %s""" % (pfx, grp, V(0), V(0), V(0), grp, V(3), then))

    en(A, 'h_wait_en', 2, 1, 15, 0, extra="li r0, 0\nstw r0, 0x%X(r31)" % V(4))
    st(A, 'h_wait_up', """
        bl h_gnd
        cmpwi r3, 0
        bne hw_on
        li r4, 1
        b go
    hw_on:
        bl h_end
        cmpwi r3, 0
        beq hh_look
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)
        cmpwi r3, 2
        blt hw_again
        li r3, 1
        li r4, 100
        bl h_rand
        cmpwi r3, 50
        bgt hw_walk
        bl h_rev
    hw_walk:
        li r4, 4
        b go
    hw_again:
        li r4, 15
        li r5, 0
        bl h_mot1
        b hh_look""" % (V(4), V(4)))
    look(A, 'hh', 0, "beq hl_n\nbl h_rev\nhl_n:\nli r4, 7\nb go")
    en(A, 'h_walk_en', 1, 1, 16, 1, pre=la4("row_heiho_walk") + "\nbl h_en\nbl h_kick",
       extra="lwz r3, 0x%X(r30)\nlwz r4, 0x%X(r30)\nbl h_rand\nstw r3, 0x%X(r31)" % (P(0), P(1), V(1)))
    st(A, 'h_walk_up', """
        bl h_mv
        bl h_gnd
        cmpwi r3, 0
        bne hk_on
        li r4, 1
        b go
    hk_on:
        bl h_wall
        cmpwi r3, 0
        beq hk_cl
        li r4, 6
        b go
    hk_cl:
        lwz r11, 0xC(r31)
        addi r11, r11, -1
        cmplwi r11, 1
        bgt hk_tm
        bl h_cliff
        cmpwi r3, 0
        beq hk_tm
        bl h_mv0
        li r4, 5
        b go
    hk_tm:
        lwz r3, 0x%X(r31)
        addi r3, r3, -1
        stw r3, 0x%X(r31)
        cmpwi r3, 0
        bgt hh_look
        li r4, 3
        b go""" % (V(1), V(1)))
    st(A, 'h_turn_up', """
        bl h_gnd
        cmpwi r3, 0
        bne ht_on
        li r4, 1
        b go
    ht_on:
        bl h_end
        cmpwi r3, 0
        beq epi
        bl h_rev
        lwz r0, 0x%X(r31)
        cmpwi r0, 0
        li r4, 4
        ble ht_g
        li r4, 9
    ht_g:
        b goi""" % V(2))
    en(A, 'h_ntc_en', 5, 0, 12, 1, pre=la4("row_heiho_jump") + "\nbl h_en\nbl h_kick",
       extra="li r0, 1\nstw r0, 0x%X(r31)" % V(4))
    st(A, 'h_ntc_up', """
        bl h_vy0
        bgt epi
        bl h_gnd
        cmpwi r3, 0
        beq epi
        lwz r3, 0x%X(r31)
        cmpwi r3, 2
        blt hn_hop
        li r4, 8
        b goi
    hn_hop:
        addi r3, r3, 1
        stw r3, 0x%X(r31)
        li r4, 5
        bl h_kin""" % (V(4), V(4)))
    en(A, 'h_hold_en', 0, 1, 12, 1, extra="lwz r0, 0x%X(r30)\nstw r0, 0x%X(r31)" % (P(2), V(1)))
    st(A, 'h_hold_up', """
        bl h_gnd
        cmpwi r3, 0
        bne hd_on
        li r4, 1
        b go
    hd_on:
        lwz r3, 0x%X(r31)
        addi r3, r3, -1
        stw r3, 0x%X(r31)
        cmpwi r3, 0
        bgt epi
        lwz r4, 0x%X(r31)
        bl h_tchk
        cmpwi r3, 0
        beq hd_run
        bl h_rev
    hd_run:
        li r4, 9
        b go""" % (V(1), V(1), V(3)))
    en(A, 'h_run_en', 3, 1, 10, 1, pre=la4("row_heiho_run") + "\nbl h_en\nbl h_kick",
       extra="lwz r0, 0x%X(r31)\ncmpwi r0, 0\nbgt hr_e\nlwz r0, 0x%X(r30)\nstw r0, 0x%X(r31)\nhr_e:"
       % (V(2), P(3), V(2)))
    st(A, 'h_run_up', """
        bl h_mv
        bl h_gnd
        cmpwi r3, 0
        bne hr_on
        li r0, 0
        stw r0, 0x%X(r31)
        li r4, 1
        b go
    hr_on:
        lwz r3, 0x%X(r31)
        addi r3, r3, -1
        stw r3, 0x%X(r31)
        cmpwi r3, 0
        bgt hr_w
        li r4, 12
        b go
    hr_w:
        bl h_wall
        cmpwi r3, 0
        bne hr_t
        lwz r11, 0xC(r31)
        addi r11, r11, -1
        cmplwi r11, 1
        bgt hr_look
        bl h_cliff
        cmpwi r3, 0
        beq hr_look
        bl h_mv0
    hr_t:
        li r4, 10
        b go""" % (V(2), V(2), V(2)))
    look(A, 'hr', 1, "beq epi\nli r4, 13\nb go")
    en(A, 'h_wrt_en', 0, 1, 13, 0)
    st(A, 'h_rt_up', "bl h_mv\nb h10_body")
    st(A, 'h_wrt_up', """
    h10_body:
        bl h_gnd
        cmpwi r3, 0
        bne h10_on
        li r4, 1
        b go
    h10_on:
        bl h_cliff
        cmpwi r3, 0
        beq h10_end
        bl h_clear
    h10_end:
        bl h_end
        cmpwi r3, 0
        beq epi
        bl h_rev
        li r4, 9
        b goi""")
    en(A, 'h_brk_en', 2, 1, 11, 0)
    st(A, 'h_brk_up', """
        bl h_mv
        bl h_cliff
        cmpwi r3, 0
        beq hb_g
        bl h_clear
    hb_g:
        bl h_gnd
        cmpwi r3, 0
        bne hb_on
        li r4, 1
        b go
    hb_on:
        bl h_end
        cmpwi r3, 0
        beq epi
        bl h_stop
        cmpwi r3, 0
        beq epi
        li r4, 14
        b go""")
    en(B, 'h_rt_en', 2, 1, 13, 0, rate=P(4))
    # settle after the brake: kinetic 21, ground off, Fall; kinetic flag 1 -> 4 (a 120-frame guard: the Wii U's
    # kinetic 21 is unverified)
    en(B, 'h_set_en', 21, 0, 8, 1, extra="li r0, 0\nstw r0, 0x%X(r31)" % V(5))
    st(B, 'h_set_up', """
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)
        cmpwi r3, 120
        bge hs_walk
        li r4, 1
        bl h_flag
        beq epi
    hs_walk:
        li r4, 4
        b go""" % (V(5), V(5)))

    # ---- Waddle Dee (V0 jump frames)
    en(B, 'd_para_en', 8, 0, 11, 1)
    en(B, 'd_walk_en', 1, 1, 13, 1, rate=P(0))
    st(B, 'd_walk_up', """
        bl h_mv
        bl h_gnd
        cmpwi r3, 0
        bne dw_on
    d_fall:
        lwz r0, 0xC(r31)
        li r4, 2
        cmplwi r0, 1
        ble dw_f
        li r4, 1
    dw_f:
        b go
    dw_on:
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)
        lwz r0, 0x%X(r30)
        cmpw r3, r0
        ble dw_wall
        li r0, 0
        stw r0, 0x%X(r31)
        li r3, 1
        li r4, 100
        bl h_rand
        lwz r0, 0x%X(r30)
        cmpw r3, r0
        ble dw_jump
    dw_wall:
        bl h_wall
        cmpwi r3, 0
        beq dw_cl
        li r3, 1
        li r4, 100
        bl h_rand
        lwz r0, 0x%X(r30)
        cmpw r3, r0
        bgt dw_turn
    dw_jump:
        li r4, 6
        b go
    dw_cl:
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        beq dw_c2
        cmpwi r0, 3
        bne epi
    dw_c2:
        bl h_cliff
        cmpwi r3, 0
        beq epi
    dw_turn:
        li r4, 5
        b go""" % (V(0), V(0), P(1), V(0), P(2), P(3)))
    en(B, 'd_jump_en', 5, 0, 9, 0)
    st(B, 'd_jump_up', "bl h_vy0\nbgt epi\nb d_fall")

    # ---- Waddle Doo: walk (a wall -> 5; every search-0 interval a target behind -> 4)
    en(B, 'o_walk_en', 1, 1, 14, 1)
    st(B, 'o_walk_up', """
        bl h_mv
        lwz r3, 0x%(V7)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V7)X(r31)
        cmpwi r3, 0
        bgt ow_g
        li r4, 8
        b go
    ow_g:
        bl h_gnd
        cmpwi r3, 0
        bne ow_on
        li r4, 1
        b go
    ow_on:
        bl h_wall
        cmpwi r3, 0
        beq.far do_owr              # step 2j: the random hop (3DS 0x7D568), then the search
        li r4, 5
        b go""" % dict(V7=V(7)))
    look(B, 'ow', 0, "beq epi\nli r4, 4\nb go")

    # ---- Churine: walk / jump (initialize first, as the 3DS's vt+0xA0)
    en(B, 'c_walk_en', 1, 1, 11, 1, pre="mr r3, r31\nbl w_init")
    st(B, 'c_walk_up', """
        bl h_mv
        bl h_gnd
        cmpwi r3, 0
        bne cw_on
        li r4, 1
        b go
    cw_on:
        bl h_wall
        cmpwi r3, 0
        beq cw_cl
        li r4, 4
        b go
    cw_cl:
        bl h_cliff
        cmpwi r3, 0
        beq.far ch_srch             # step 2k: the powder's search (3DS 0x3D76C)
        li r4, 5
        b go""")
    en(B, 'c_jump_en', 5, 0, 7, 1, pre="mr r3, r31\nbl w_init", extra="bl h_sety")

    # ---- fix v3 -----------------------------------------------------------------------------------------------
    B.asm("""
    w_noflip:
        lwz r12, 8(r3)
        li r3, 0
        cmplwi r12, 0x60
        bgelr
        lis r10, 0x%04X
        addi r10, r10, %d
        srwi r11, r12, 5
        slwi r11, r11, 2
        addi r11, r11, 0x18
        lwzx r11, r10, r11
        clrlwi r12, r12, 27
        srw r11, r11, r12
        clrlwi r3, r11, 31
        blr
    twin_flip:
        lwz r0, 8(r3)
        cmplwi r0, 0x50
        blt w_noflip
        li r3, 1
        blr
    cave_rot:
        lwz r0, 8(r31)
        cmplwi r0, 0x50
        bge rot_done
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x60(r12)
        mr r3, r31
        li r4, 1
        li r5, 1
        lwz r12, 0xE0(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctrl
    rot_done:
        lwz r10, 0(r31)
        b 0x%08X
    cave_death:
        lwz r12, 8(r3)
        cmplwi r12, 0x50
        bge death_go
        cmpwi r4, 0
        bne death_go
        lwz r12, 0xE0(r3)
        lis r11, 0x%04X
        addi r11, r11, %d
        cmpw r12, r11
        bne death_conv
        lwz r12, 0x%X(r3)
        cmpwi r12, 0
        beq death_go
    death_conv:
        li r4, 3
    death_go:
        mflr r0
        b 0x%08X
    """ % (ha(D['yawk']), sx(D['yawk']), 0xC + 8 * SET_LR_SLOT, SITE_ROT + 4, ha(D['vt']), sx(D['vt']), DEFEATED,
           SITE_DEATH + 4))
    # ---- T2: the motion data set table (r0 = category, r31 = mgr; r9-r12 free)
    B.asm("cave_t:")
    F.sr_check(B)
    B.asm("bgt t_done")
    for w in WALKERS:
        s, t = D['set_' + w['name']], MOTION_SETS + 4 * w['kind']
        B.asm("lis r11, 0x%04X\naddi r11, r11, %d\nlis r12, 0x%04X\nstw r11, %d(r12)" % (ha(s), sx(s), ha(t), sx(t)))
    # step 2k: the Waddle Doo's article set (the beam), read by the resource request and its accessor set-up
    for lab, k in (('art_doo', 0x19), ('art_dee', 0x13)):      # step 2l: the Waddle Dee's (the parasol)
        s, t = D[lab], ART_SETS + 4 * k
        B.asm("lis r11, 0x%04X\naddi r11, r11, %d\nlis r12, 0x%04X\nstw r11, %d(r12)" % (ha(s), sx(s), ha(t), sx(t)))
    B.asm("""
    t_done:
        cmpwi r0, 1
        b 0x%08X
    """ % (SITE_T + 4))
    # ---- S2: param slots (r28 = mgr, r3 the load's result: kept)
    B.asm("cave_s:")
    F.sr_check(B)
    B.asm("""
        bgt s2_nsr
        lis r12, 0x%04X
        lwz r12, %d(r12)
        cmpwi r12, 0
        beq s2_sr
    """ % (ha(PARAM_MGR), sx(PARAM_MGR)))
    # step 2l: every kind its own static param object in its 3DS layout (kind_param_blocks; step 2k only the Waddle
    # Doo's, the others borrowed mczakozima's slot 0x5A: its P3 hurtbox capsule and P4 ground box); then the twins'
    for w in WALKERS:
        o = D[param_label(w['name'])]
        B.asm("lis r11, 0x%04X\naddi r11, r11, %d\nstw r11, 0x%X(r12)" % (ha(o), sx(o), SLOTS + 4 * w['kind']))
    B.asm("bl k2_twins")
    # step 2m: the sound rows (snd_rows: r3 1 on a Smash Run stage, 0 on any other enemy battle: the twins' rows put
    # back), the Propeller Heiho's loop count reset (the 3DS's static in enemy_fs.cro's data, {-1, 0} at its load)
    B.asm("""
    s2_sr:
        lis r12, 0x%04X
        addi r12, r12, %d
        li r0, -1
        stw r0, 0(r12)
        li r0, 0
        stw r0, 4(r12)
        li r3, 1
        bl snd_rows
        b s2_done
    s2_nsr:
        li r3, 0
        bl snd_rows""" % (ha(D['ph_snd']), sx(D['ph_snd'])))
    B.asm("""
    s2_done:
        lwz r0, 0x5EC(r28)
        b 0x%08X
    """ % (SITE_S + 4))
    return A, B, code_e(D, en, st, far, lfs), code_f(D, VT_WORDS[0])


def code_e(D, en, st, far, lfs):
    """step 2c (region E): the White Bear's and the Gordo's own states (3DS enemy_fs.cro, addresses in the
    docstring of each), the start variant (SMODE) and helpers"""
    import re

    class Near(Asm):
        """conditional branches to the shared exits (epi / go / goi, in region A: beyond a bc's reach) go
        through local copies"""
        def asm(self, text):
            Asm.asm(self, re.sub(r'\b(b(?:eq|ne|gt|lt|ge|le))(\s+)(epi|go|goi)\b', r'\1\2e_\3', text))
    Ee = Near(CAVE_E)
    Ee.asm("e_epi:\nb epi\ne_go:\nb go\ne_goi:\nb goi")
    # ---- helpers: the start variant 1 (Gordo, start 0x19CB0): set_correct(0), set_lr(0.0, 1, 1) (lr 0: faces the
    # camera); the kinetic energy's second kick (3DS KineticEnergy vt+0x74 -> Wii U vt+0xEC: Behavior::
    # set_kinetic_jump's at 0x026A84A4); the current speed into r1+8 (x, y, z)
    Ee.asm("h_smode:\nmflr r28\nlwz r3, 0(r31)\nlwz r3, 0x30DC(r3)\nli r4, 0")
    far(Ee, SET_CORRECT)
    lfs(Ee, 'f1', 'consts')
    Ee.asm("""
        mr r3, r31
        li r4, 1
        li r5, 1
        lwz r12, 0xE0(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctrl
        mtlr r28
        blr
    h_kick2:
        lwz r12, 0(r31)
        lwz r3, 0x3130(r12)
        lwz r12, 0(r3)
        lwz r12, 0xEC(r12)
        mtctr r12
        lis r4, 0x2000
        ori r4, r4, 4
        bctr
    o_nop:
        blr
    """ % (0xC + 8 * SET_LR_SLOT))

    # ---- Gordo: 1 spin (enter 0x1A180: kinetic -1, ground off, Togetoge loop; the contact attack, P2 entry 0);
    # update 0x1A3FC -> 0x65D20 (writes energy 0 every frame: a speed of (home - position) x 0.5: not ported, see
    # the docs); 3 remove (death state 0: the Gordo is not defeated by damage)
    en(Ee, 'o_spin_en', -1, 0, 0, 1)

    # ---- White Bear (V0 search counter +0x16C, V1 walk timer +0x168, V2 search cool-down +0x178, V4 quakes +0x174,
    # V5 jump frames +0x170)
    # 3 walk (enter 0x7E678, update 0x7E950): kinetic 1, Move loop, V1 = random(P0 60, P1 120), V0 = 0
    en(Ee, 'b_walk_en', 1, 1, 9, 1, extra="lwz r3, 0x%X(r30)\nlwz r4, 0x%X(r30)\nbl h_rand\nstw r3, 0x%X(r31)\n"
       "li r0, 0\nstw r0, 0x%X(r31)" % (P(0), P(1), V(1), V(0)))
    st(Ee, 'b_walk_up', """
        bl h_mv
        bl h_gnd
        cmpwi r3, 0
        bne bw_on
        li r4, 1
        b go
    bw_on:
        bl h_wall
        cmpwi r3, 0
        bne bw_turn
        bl h_cliff
        cmpwi r3, 0
        beq bw_cnt
    bw_turn:
        li r4, 5
        b go
    bw_cnt:
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(V0)X(r31)
        lwz r3, 0x%(V2)X(r31)
        cmpwi r3, 0
        ble bw_srch
        addi r3, r3, -1
        stw r3, 0x%(V2)X(r31)
        cmpwi r3, 0
        bgt bw_tm
    bw_srch:
        li r4, 1
        bl h_grp
        lwz r0, 0x%(V0)X(r31)
        cmpw r3, r0
        bge bw_tm
        li r0, 0
        stw r0, 0x%(V0)X(r31)
        li r4, 1
        bl h_srch
        cmpwi r3, 0
        blt bw_tm
        li r4, 6
        b go
    bw_tm:
        lwz r3, 0x%(V1)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V1)X(r31)
        cmpwi r3, 0
        bgt epi
        li r4, 4
        b go""" % dict(V0=V(0), V1=V(1), V2=V(2)))
    # 4 special turn (enter 0x7E5C8: kinetic 0, SpecialTurn; update 0x7E8A8 = 5's: at its end reverse_lr => 3)
    en(Ee, 'b_sturn_en', 0, 1, 14, 0)
    # 6 quake hold (enter 0x7EB34: kinetic 0, QuakeHold at P0 f9 1.5, V4 = 0; update 0x7F10C: at its end
    # is_in_view_area -> 7, else -> 3; the camera test is not ported: in view)
    en(Ee, 'b_hold_en', 0, 1, 11, 0, rate=P(2), extra="li r0, 0\nstw r0, 0x%X(r31)" % V(4))
    st(Ee, 'b_hold_up', "bl h_end\ncmpwi r3, 0\nbeq epi\nli r4, 7\nb go")
    # 7 quake jump (enter 0x7ED14: E+0x20 0, +0x24 f10, +0x28 0, +0x2C f10, +0x3C 0.1, the kick, kinetic 5, ground
    # off, QuakeUp, V5 = 0; update 0x7F1F8: V5++, the speed's y <= 0 -> 8)
    en(Ee, 'b_up_en', 5, 0, 13, 0, pre="""bl h_ebase
        li r0, 0
        stw r0, 0x20(r10)
        stw r0, 0x28(r10)
        lwz r0, 0x%X(r30)
        stw r0, 0x24(r10)
        stw r0, 0x2C(r10)
        lwz r0, 0x%X(r30)
        stw r0, 0x3C(r10)
        bl h_kick2""" % (P(3), P(12)), extra="li r0, 0\nstw r0, 0x%X(r31)" % V(5))
    st(Ee, 'b_up_up', """
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)
        bl h_vy0
        bgt epi
        li r4, 8
        b go""" % (V(5), V(5)))
    # 8 quake fall (enter 0x7EBB4: E+0x20 / +0x24 = the current speed, +0x28 0, +0x2C f12 3, +0x3C f11 1, the kick,
    # kinetic 5, ground off, QuakeFall; update 0x7F168: V5++; on the ground: V5 < f14 (180) => 9, else => 2)
    pre8 = "addi r3, r1, 8\nmr r4, r31\nlis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctrl\n" \
           % (GET_SPEED >> 16, GET_SPEED & 0xFFFF)
    en(Ee, 'b_fall_en', 5, 0, 10, 0, pre=pre8 + """bl h_ebase
        lwz r0, 8(r1)
        stw r0, 0x20(r10)
        lwz r0, 0xC(r1)
        stw r0, 0x24(r10)
        li r0, 0
        stw r0, 0x28(r10)
        lwz r0, 0x%X(r30)
        stw r0, 0x2C(r10)
        lwz r0, 0x%X(r30)
        stw r0, 0x3C(r10)
        bl h_kick2""" % (P(5), P(4)))
    st(Ee, 'b_fall_up', """
        lwz r3, 0x%X(r31)
        addi r3, r3, 1
        stw r3, 0x%X(r31)
        mr r28, r3
        bl h_gnd
        cmpwi r3, 0
        beq epi
        lwz r0, 0x%X(r30)
        li r4, 9
        cmpw r0, r28
        bgt bf_go
        li r4, 2
    bf_go:
        b goi""" % (V(5), V(5), P(7)))
    # 9 quake landing (enter 0x7EE74: kinetic 0, ground on, QuakeLanding at f13 (1.0), f16 (0.5) after the first,
    # request_quake(7), the absolute quake hit, effects 0x7400000 / 0x7400001: not ported; V4++; update 0x7F244: at
    # its end, V4 < f17 (3) and success_by_percent(f15 / 2^(V4 - 1)) -> 7 (jump again), else V2 = f18 (60), -> 3;
    # the percentage as an integer: 50 >> (V4 - 1) is exact for V4 1 / 2, the only ones it is tested with)
    st(Ee, 'b_land_en', """
        li r4, 0
        bl h_kin
        li r4, 1
        bl h_att
        lfs f2, 0x%(P6)X(r30)
        lwz r0, 0x%(V4)X(r31)
        cmpwi r0, 0
        ble bl_rate
        lfs f2, 0x%(P9)X(r30)
    bl_rate:
        li r4, 12
        li r5, 0
        bl h_mot
        mr r3, r31
        li r4, %(QK)d
        lis r12, 0x%(RQH)04X
        ori r12, r12, 0x%(RQL)04X
        mtctr r12
        bctrl
        bl b_quake
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lwz r12, 0(r31)
        lwz r5, 0x311C(r12)
        addi r5, r5, 0x10
        mr r3, r31
        lis r4, 0x740
        addi r6, r1, 8
        lfs f1, 0x%(P13)X(r30)
        lis r12, 0x%(REH)04X
        ori r12, r12, 0x%(REL)04X
        mtctr r12
        bctrl
        mr r3, r31
        lis r4, 0x740
        ori r4, r4, 1
        addi r5, r1, 8
        lfs f1, 0x%(P14)X(r30)
        lis r12, 0x%(RZH)04X
        ori r12, r12, 0x%(RZL)04X
        mtctr r12
        bctrl
        lwz r3, 0x%(V4)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(V4)X(r31)""" % dict(P6=P(6), P9=P(9), V4=V(4), QK=QUAKE_KIND, RQH=REQ_QUAKE >> 16,
                                        RQL=REQ_QUAKE & 0xFFFF, REH=REQ_EFFECT >> 16, REL=REQ_EFFECT & 0xFFFF,
                                        RZH=REQ_EFFECT0 >> 16, RZL=REQ_EFFECT0 & 0xFFFF, P13=P(13), P14=P(14)))
    # ---- Waddle Doo's leave (v2; the 3DS state 9: enter 0x7CEC0 = Fall at rate 0, init_common_leave(P6) code.bin
    # 0x7B23B4: the leave time, energy +0x30 = -p1 / +0x34 = p2 and kinetic 15 (0x7B4E84), ground off,
    # set_correct(0), disable_jostle (not ported), the common leave effect 0x8000005 following node 0 at (0, 3, 0)
    # scale 0.85 (EnemyManager +0x5F8 clear); update 0x7D444 / update_common_leave 0x7B40B0: the time counts
    # down, at 0 the effect is removed and -> remove (no defeat: DEFEATED stays 0)); V6 the time, V5 the effect
    st(Ee, 'o_leave_en', """
        li r4, 10
        li r5, 0
        bl h_mot0
        lwz r0, 0x%(P0)X(r30)
        stw r0, 0x%(V6)X(r31)
        bl h_ebase
        lwz r0, 0x%(P1)X(r30)
        stw r0, 0x30(r10)
        lwz r0, 0x%(P2)X(r30)
        stw r0, 0x34(r10)
        li r4, 15
        bl h_kin
        li r4, 0
        bl h_att
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0
        lis r12, 0x%(SCH)04X
        ori r12, r12, 0x%(SCL)04X
        mtctr r12
        bctrl
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0x10(r1)
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        stw r0, 0x1C(r1)
        lwz r0, 0x%(P3)X(r30)
        stw r0, 0xC(r1)
        mr r3, r31
        lis r4, 0x800
        ori r4, r4, 5
        li r5, 0
        addi r6, r1, 8
        addi r7, r1, 0x14
        lfs f1, 0x%(P4)X(r30)
        lis r12, 0x%(RFH)04X
        ori r12, r12, 0x%(RFL)04X
        mtctr r12
        bctrl
        stw r3, 0x%(V5)X(r31)""" % dict(P0=P(0), P1=P(1), P2=P(2), P3=P(3), P4=P(4), V5=V(5), V6=V(6),
                                        SCH=SET_CORRECT >> 16, SCL=SET_CORRECT & 0xFFFF, RFH=REQ_FOLLOW >> 16,
                                        RFL=REQ_FOLLOW & 0xFFFF))
    st(Ee, 'o_leave_up', """
        lwz r3, 0x%(V6)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V6)X(r31)
        cmpwi r3, 0
        bgt epi
        mr r3, r31
        lwz r4, 0x%(V5)X(r31)
        lis r12, 0x%(RMH)04X
        ori r12, r12, 0x%(RML)04X
        mtctr r12
        bctrl
        li r0, 0
        stw r0, 0x%(V5)X(r31)
        lwz r4, 0x%(RM)X(r30)
        b go""" % dict(V5=V(5), V6=V(6), RMH=REMOVE_EFFECT >> 16, RML=REMOVE_EFFECT & 0xFFFF, RM=CF['REMOVE']))
    # the landing's absolute hit (v2; the 3DS 0x7EF04-0x7F01C: set_attack_absolute_data(P6), then for the fighter
    # entries in order the first on the ground gets hit_attack_absolute(P6 id 0, entry), once): the fighter table
    # (slots 0-3, live) as the stomp test reads it; on the ground = MSC StatusModule(1) (the situation) == 0; the
    # enemy's AttackModule (acc+0x30C8, AttackModuleImpl) through its MSC entry vt+0x334 as the ACMD
    # Throw_Specifier / Throw_Applier handlers (0x02BE6E88 / 0x02BE6FCC) do: op 0x2716 set_abs(kind 0, part 0, the
    # P6 values: 10.0, 90, 100, 0, 40, ...: ABS_WORDS), then op 0x271D (0x02C0B8E4 -> vt+0x74 hit_absolute(kind 0,
    # node 0, the fighter's object id = [its accessor + 0], hit group 0, 0))
    Ee.asm("""
    b_quake:
        mflr r0
        stwu r1, -0xA0(r1)
        stw r0, 0xA4(r1)
        stmw r26, 0x88(r1)
        lis r12, 0x%(FH)04X
        lwz r12, %(FL)d(r12)
        cmpwi r12, 0
        beq q_out
        lwz r26, 0(r12)
        cmpwi r26, 0
        beq q_out
        lwz r27, 8(r26)
        li r28, 0
    q_loop:
        cmpw r28, r27
        bge q_out
        cmpwi r28, 4
        bge q_out
        lwz r12, 0(r26)
        mulli r11, r28, 0x%(ENT)X
        add r12, r12, r11
        lbz r11, 0x1E(r12)
        cmplwi r11, 4
        blt q_next
        lwz r29, 0xC(r12)
        cmpwi r29, 0
        beq q_next
        li r0, 0
        stw r0, 8(r1)
        stw r29, 0xC(r1)
        li r0, 1
        stw r0, 0x10(r1)
        stw r0, 0x1C(r1)
        addi r0, r1, 0x10
        stw r0, 0x18(r1)
        addi r3, r1, 8
        addi r4, r1, 0x18
        lis r12, 0x%(MH)04X
        ori r12, r12, 0x%(ML)04X
        mtctr r12
        bctrl
        cmpwi r3, 0
        beq q_hit
    q_next:
        addi r28, r28, 1
        b q_loop
    q_hit:
        lwz r30, 0(r31)
        lwz r30, 0x30C8(r30)
        cmpwi r30, 0
        beq q_out
        lis r11, 0x%(AH)04X
        addi r11, r11, %(AL)d
        addi r12, r1, 0x1C
        li r0, %(NW)d
        mtctr r0
    q_copy:
        lwz r0, 0(r11)
        stwu r0, 4(r12)
        addi r11, r11, 4
        bdnz q_copy
        li r0, %(NW)d
        bl q_msc
        li r0, 0x271D
        stw r0, 0x20(r1)
        li r0, 0
        stw r0, 0x24(r1)
        stw r0, 0x28(r1)
        stw r0, 0x30(r1)
        stw r0, 0x34(r1)
        lwz r0, 0(r29)
        stw r0, 0x2C(r1)
        li r0, 6
        bl q_msc
    q_out:
        lmw r26, 0x88(r1)
        lwz r0, 0xA4(r1)
        mtlr r0
        addi r1, r1, 0xA0
        blr
    q_msc:
        stw r0, 0x1C(r1)
        addi r0, r1, 0x20
        stw r0, 0x18(r1)
        mr r3, r30
        addi r4, r1, 0x18
        lwz r12, 0(r30)
        lwz r12, 0x334(r12)
        mtctr r12
        bctr
    """ % dict(FH=ha(FIGHTERS), FL=sx(FIGHTERS), ENT=FIGHTER_ENTRY, MH=MSC_STATUS >> 16, ML=MSC_STATUS & 0xFFFF,
               NW=len(ABS_WORDS), AH=ha(D['abs_words']), AL=sx(D['abs_words'])))
    st(Ee, 'b_land_up', """
        bl h_end
        cmpwi r3, 0
        beq epi
        lwz r3, 0x%(V4)X(r31)
        lwz r0, 0x%(P10)X(r30)
        cmpw r0, r3
        ble bl_done
        addi r5, r3, -1
        lwz r28, 0x%(P8)X(r30)
        srw r28, r28, r5
        li r3, 0
        li r4, 99
        bl h_rand
        cmpw r3, r28
        bge bl_done
        li r4, 7
        b go
    bl_done:
        lwz r0, 0x%(P11)X(r30)
        stw r0, 0x%(V2)X(r31)
        li r4, 3
        b go""" % dict(V4=V(4), P10=P(10), P8=P(8), P11=P(11), V2=V(2)))
    return Ee


def code_f(D, vtw):
    """step 2e (region G): the fliers' framework (the vtable's dispatching slots 10 / 27 / 41 / 69, the leave) and
    each flier's own states (3DS enemy_fs.cro addresses in the comments). Conditional branches to the shared exits
    (region A) use .far."""
    G = Asm(CAVE_G)

    def far(t):
        G.asm("lis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctrl" % (t >> 16, t & 0xFFFF))

    def st(label, body):
        G.asm("%s:\nmflr r0\nbl pro\n%s\nb epi" % (label, body))

    def lfs(fr, label, off=0):
        G.asm("lis r12, 0x%04X\nlfs %s, %d(r12)" % (ha(D[label] + off), fr, sx(D[label] + off)))

    orig = lambda k: vtw[(0xC + 8 * k) // 4]  # noqa: E731
    # ---- the vtable's dispatching slots: the kind's CFG handler (FSTART / FDMG / F27 / F69), else BehaviorImpl's
    G.asm("""
    f_v41:
        lwz r12, 0x168(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctr
    """ % CF['FSTART'])
    for k, f in ((10, 'FDMG'), (27, 'F27'), (69, 'F69')):
        G.asm("""
        f_v%d:
            lwz r12, 0x168(r3)
            lwz r12, 0x%X(r12)
            cmpwi r12, 0
            bne f_v%d_go
            lis r12, 0x%04X
            ori r12, r12, 0x%04X
        f_v%d_go:
            mtctr r12
            bctr
        """ % (k, CF[f], k, orig(k) >> 16, orig(k) & 0xFFFF, k))
    # ---- shared helpers
    # f_aer: r3 = the aerial module; f_pass1: set_passable_check(1); f_gl: r3 = the kind's gl entry (Behavior +8
    # kind, +0xC variation; the Wii U's own lookup, e.g. 0x02DB4EF0)
    G.asm("""
    f_pass1:
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 1
        b 0x%08X
    f_gl:
        lis r12, 0x%04X
        lwz r12, %d(r12)
        lwz r9, 8(r31)
        lwz r10, 0xC(r31)
        slwi r9, r9, 3
        add r9, r9, r10
        slwi r9, r9, 2
        add r9, r9, r12
        lwz r9, 0x%X(r9)
        mulli r9, r9, 0x228
        lwz r3, 0x%X(r12)
        add r3, r3, r9
        blr
    f_kflag:
        lwz r12, 0(r31)
        lwz r12, 0x3130(r12)
        lwz r12, 8(r12)
        lwz r12, 0(r12)
        lwz r12, 0x14(r12)
        blr
    """ % (SET_PASSABLE, ha(PARAM_MGR), sx(PARAM_MGR), GL_INDEX, GL_BASE))
    # f_hitret: r3 = hit_return_frame() (3DS 0x9EA9B0): int(float(int gl[+0x154]) * factor), factor = HIT_FACTOR
    # (the 3DS 0x9EB4C0's Wii U copy); uses r1+8..+0x17 of the caller's frame
    G.asm("""
    f_hitret:
        mflr r0
        stw r0, 0x1C(r1)
        bl f_gl
        lwz r0, 0x154(r3)
        xoris r0, r0, 0x8000
        stw r0, 0xC(r1)
        lis r0, 0x4330
        stw r0, 8(r1)
        lfd f1, 8(r1)
    """)
    G.asm("lis r12, 0x%04X\nlfd f0, %d(r12)" % (ha(D['fconsts']), sx(D['fconsts'])))
    G.asm("""
        fsub f1, f1, f0
        frsp f1, f1
        stfs f1, 0x10(r1)
        mr r3, r31
        bl 0x%08X
        lfs f0, 0x10(r1)
        fmuls f1, f0, f1
        fctiwz f1, f1
        stfd f1, 8(r1)
        lwz r3, 0xC(r1)
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """ % HIT_FACTOR)
    # the common leave (3DS Behavior::init_common_leave 0x7B23B4 with the kind's InnerEnemyLeaveParam at CFG LVP:
    # frames, the energy's +0x30 (-speed), +0x34, the leave effect 0x8000005's offset y and scale): V6 = frames,
    # kinetic 15, ground off, set_correct(0), the effect following node 0 -> V5; update: o_leave_up (step 2c v2)
    st('f_leave_en', """
        lwz r28, 0x%(LVP)X(r30)
        add r28, r28, r30
        lwz r0, 0(r28)
        stw r0, 0x%(V6)X(r31)
        bl h_ebase
        lwz r0, 4(r28)
        stw r0, 0x30(r10)
        lwz r0, 8(r28)
        stw r0, 0x34(r10)
        li r4, 15
        bl h_kin
        li r4, 0
        bl h_att
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0
        bl 0x%(SC)08X
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0x10(r1)
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        stw r0, 0x1C(r1)
        lwz r0, 0xC(r28)
        stw r0, 0xC(r1)
        mr r3, r31
        lis r4, 0x800
        ori r4, r4, 5
        li r5, 0
        addi r6, r1, 8
        addi r7, r1, 0x14
        lfs f1, 0x10(r28)
        lis r12, 0x%(RFH)04X
        ori r12, r12, 0x%(RFL)04X
        mtctr r12
        bctrl
        stw r3, 0x%(V5)X(r31)""" % dict(LVP=CF['LVP'], V6=V(6), V5=V(5), SC=SET_CORRECT, RFH=REQ_FOLLOW >> 16,
                                       RFL=REQ_FOLLOW & 0xFFFF))
    # f_unleave: finalize_common_leave (3DS 0x7B475C: the leave effect removed, the count 0) when a leave runs, then
    # set_correct(5) (as Ghos's / Furiijio's slot 69 do after it)
    G.asm("""
    f_unleave:
        lwz r0, 0x%(V6)X(r31)
        cmpwi r0, 0
        blelr
        mflr r0
        stw r0, 0x1C(r1)
        mr r3, r31
        lwz r4, 0x%(V5)X(r31)
        lis r12, 0x%(RMH)04X
        ori r12, r12, 0x%(RML)04X
        mtctr r12
        bctrl
        li r0, 0
        stw r0, 0x%(V5)X(r31)
        stw r0, 0x%(V6)X(r31)
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 5
        lwz r0, 0x1C(r1)
        mtlr r0
        b 0x%(SC)08X
    """ % dict(V5=V(5), V6=V(6), RMH=REMOVE_EFFECT >> 16, RML=REMOVE_EFFECT & 0xFFFF, SC=SET_CORRECT))

    # ---- Ghos (kind 0x11; enemy_fs.cro create 0x11560, table 0x10D350). V0 the slip-homing timer (+0x1EC), V1
    # the leave timer (+0x1E8), V2 the stun frames (+0x1E4), V3 the target (+0x1F0), V4 the follow effect (+0x1FC),
    # V5 / V6 the common leave's effect / frames. P: 0 / 1 timer range (20, 40), 2 choice % (96), 3 bounce speed
    # (0.6), 4 max speed (0.8), 5 leave frames (1200), 6 0.1 (a literal), 7-12 / 13-18 the two P7 slip-homing sets,
    # 19-23 the leave param (P6: 100, -0.02, 30, 3, 0.85)
    # start 0x109C0: the aerial module (its ctor: the 3DS ctor 0x11598's), set_rhombus, set_lr(0, 1, 1) (lr 0: faces
    # the camera), V3 = the nearest fighter, +0x10 = posture lr, +0x14 / +0x18 = 0, V1 = 1200, -> 1, the body effect
    # 0x7110000 following node 0 -> V4 (set_node_visibility(1, 1) / (0, 0) and play_se(0x8A60000) not ported)
    G.asm("f_ghos_start:\nmflr r0\nbl pro\naddi r3, r31, 0x%X\nlwz r4, 0(r31)\nbl 0x%08X\nmr r3, r31" % (AER, AER_CTOR))   # step 2f: set_rhombus(this) (r3 was the aerial module)
    far(SET_RHOMBUS)
    lfs('f1', 'consts')
    G.asm("""
        mr r3, r31
        li r4, 1
        li r5, 1
        lwz r12, 0xE0(r3)
        lwz r12, 0x%(LR)X(r12)
        mtctr r12
        bctrl
        bl h_near
        stw r3, 0x%(V3)X(r31)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x60(r12)
        stw r0, 0x10(r31)
        li r0, 0
        stw r0, 0x14(r31)
        stw r0, 0x18(r31)
        stw r0, 0x%(GI)X(r31)
        stw r0, 0x%(GD)X(r31)
        lwz r0, 0x%(P5)X(r30)
        stw r0, 0x%(V1)X(r31)
        li r4, 1
        bl h_chg
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        stw r0, 0x1C(r1)
        mr r3, r31
        lis r4, 0x711
        li r5, 0
        addi r6, r1, 8
        addi r7, r1, 0x14
    """ % dict(LR=0xC + 8 * SET_LR_SLOT, V3=V(3), P5=P(5), V1=V(1), GI=GH_IMM, GD=GH_DMG))
    lfs('f1', 'consts', 4)
    far(REQ_FOLLOW)
    G.asm("stw r3, 0x%X(r31)\nb epi" % V(4))
    # L66BA4: V0 = random(P0, P1); random_choice(100 - P2, P2, 0, 0) (3DS 0x7B0DC4: weights -> index: 4 % index 0,
    # 96 % index 1) -> set_mode_slip_homing(P7 set [index]: s0 +0, s1 +0xC, s2 +8, s3 +0x14, s4 +4, s5 +0x10); called
    # from a state (its frame's +0x1C keeps the return, +0x10 / +0x14 the speed). Step 2g v3: index 1 (96 %) is the
    # SECOND set (+0x18: P13-18, max 1.5 a frame: the homing that charges at the target), index 0 (4 %) the slow
    # drift (P7-12, max 0.052 / 0.15); steps 2e-2g v2 had them swapped (Ghos drifted 96 % of the time).
    # Step 2g v2: the Wii U's 0x02DB28E4 is set_mode_HOMING (energy 0's init with speed 0); the 3DS's slip homing
    # 0x5F5F58 inits it with the current speed (energy +4 / +8), so the speed is kept: saved before, set back with
    # set_current_speed 0x02DB2BC0 after (else every re-pick, each 20-40 frames, stopped Ghos dead)
    G.asm("""
    f_gpick:
        mflr r0
        stw r0, 0x1C(r1)
        lwz r3, 0x%(P0)X(r30)
        lwz r4, 0x%(P1)X(r30)
        bl h_rand
        stw r3, 0x%(V0)X(r31)
        li r3, 0
        li r4, 99
        bl h_rand
        lwz r0, 0x%(P2)X(r30)
        addi r12, r30, 0x%(P13)X
        cmpw r3, r0
        blt gp_set
        addi r12, r30, 0x%(P7)X
    gp_set:
        lfs f1, 0(r12)
        lfs f2, 0xC(r12)
        lfs f3, 8(r12)
        lfs f4, 0x14(r12)
        lfs f5, 4(r12)
        lfs f6, 0x10(r12)
        lwz r12, 0x%(E0)X(r31)
        lfs f0, 0(r12)
        stfs f0, 0x10(r1)
        lfs f0, 4(r12)
        stfs f0, 0x14(r1)
        addi r3, r31, 0x%(AER)X
        bl 0x%(SH)08X
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 0x10
        bl 0x%(SS)08X
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """ % dict(P0=P(0), P1=P(1), V0=V(0), P2=P(2), P7=P(7), P13=P(13), AER=AER, SH=AER_SLIP_HOMING, E0=AER + 4,
               SS=AER_SET_SPEED))
    # step 2g v3, slot 55 (0x10BA0, every frame after the state update; vtable 0xCB840 + 55 x 4 = 0xCB91C): in states
    # other than 0 / 2 / 4 / 5 with a target (V3, 3DS +0x1F0): d = target - posture, normalised by its length (x, y);
    # rx = -dy x P26 (P@0xA4 30.0), ry = dx x P26 (degrees); set_rotation_order_xyz (not mapped: the Wii U's default
    # order assumed); node 2 (RotN) set_node_rotate((rx, ry, -ry) x 0.0174533, 0) (+ ModelModule vt+0xC4 on a
    # change); the posture's rotation (count +0x54 > 1: [+0x58] + 0x38, the Wii U's layout as 0x02DC3CC4 writes it;
    # 3DS +0x3C) = (rx, ry, 0), on a change ModelModule +0x20 = 0 and MotionModule +0xFC 1 -> 2 (as 0x02DC3D28)
    G.asm("""
    f_g55:
        mflr r0
        bl pro
        lwz r0, 4(r31)
        cmplwi r0, 5
        bgt g55_go
        cmpwi r0, 1
        beq g55_go
        cmpwi r0, 3
        bne g55_out
    g55_go:
        lwz r5, 0x%(V3)X(r31)
        cmpwi r5, -1
        beq g55_out
        addi r3, r1, 8
        mr r4, r31
    """ % dict(V3=V(3)))
    far(GET_TARGET_POS)
    G.asm("""
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f3, 8(r1)
        lfs f0, 0x10(r12)
        fsubs f3, f3, f0
        lfs f4, 0xC(r1)
        lfs f0, 0x14(r12)
        fsubs f4, f4, f0
        lfs f5, 0x10(r1)
        lfs f0, 0x18(r12)
        fsubs f5, f5, f0
        fmuls f2, f3, f3
        fmadds f2, f4, f4, f2
        fmadds f2, f5, f5, f2
        lis r12, 0x%(KH)04X
        lfs f0, %(KL)d(r12)
        fcmpu cr0, f2, f0
        beq g55_n
        stfs f3, 0x14(r1)
        stfs f4, 0x18(r1)
        fmr f1, f2
        bl 0x%(SQ)08X
        lis r12, 0x%(KH)04X
        lfs f0, %(KL4)d(r12)
        fdivs f0, f0, f1
        lfs f3, 0x14(r1)
        fmuls f3, f3, f0
        lfs f4, 0x18(r1)
        fmuls f4, f4, f0
    g55_n:
        lfs f0, 0x%(P26)X(r30)
        fmuls f6, f4, f0
        fneg f6, f6
        fmuls f7, f3, f0
        stfs f6, 0x14(r1)
        stfs f7, 0x18(r1)
        lfs f0, 0x%(P27)X(r30)
        fmuls f1, f6, f0
        stfs f1, 8(r1)
        fmuls f1, f7, f0
        stfs f1, 0xC(r1)
        fneg f1, f1
        stfs f1, 0x10(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30F0(r3)
        li r4, 2
        addi r5, r1, 8
        li r6, 0
        bl 0x%(SNR)08X
        cmpwi r3, 0
        beq g55_p
        bl fu_dirty
    g55_p:
        lwz r9, 0(r31)
        lwz r10, 0x311C(r9)
        lwz r0, 0x54(r10)
        cmplwi r0, 1
        ble g55_out
        lwz r11, 0x58(r10)
        addi r11, r11, 0x38
        lfs f6, 0x14(r1)
        lfs f7, 0x18(r1)
        lis r12, 0x%(KH)04X
        lfs f8, %(KL)d(r12)
        li r8, 1
        lfs f0, 0(r11)
        fcmpu cr0, f0, f6
        bne g55_s
        lfs f0, 4(r11)
        fcmpu cr0, f0, f7
        bne g55_s
        lfs f0, 8(r11)
        fcmpu cr0, f0, f8
        bne g55_s
        li r8, 0
    g55_s:
        stfs f6, 0(r11)
        stfs f7, 4(r11)
        stfs f8, 8(r11)
        cmpwi r8, 0
        beq g55_out
        lwz r11, 0x3118(r9)
        li r0, 0
        stw r0, 0x20(r11)
        lwz r11, 0x30F0(r9)
        lwz r0, 0xFC(r11)
        cmpwi r0, 1
        bne g55_out
        li r0, 2
        stw r0, 0xFC(r11)
    g55_out:
        b epi
    """ % dict(KH=ha(D['consts']), KL=sx(D['consts']), KL4=sx(D['consts'] + 4), SQ=SQRTF, P26=P(26), P27=P(27),
               SNR=SET_NODE_ROT))
    # step 2g v3: set_lr / reverse_lr (vtable slots 49 / 50) -> the game's, then w_yaw: for a YAW_FLIP kind (< 0x50)
    # whose posture lr is 1 and rotation (+0x64) the 90 set_lr / reverse_lr just wrote: -90 (the lr -1 view, which the
    # 3DS mirrors for lr 1), ModelModule +0x20 = 0 and MotionModule +0xFC 1 -> 2 (set_lr's own marks, 0x026A7930)
    G.asm("""
    w_slr:
        lis r12, 0x%(SH)04X
        ori r12, r12, 0x%(SL)04X
        b w_lrw
    w_rlr:
        lis r12, 0x%(RH)04X
        ori r12, r12, 0x%(RL)04X
    w_lrw:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        mr r31, r3
        mtctr r12
        bctrl
        mr r3, r31
        bl w_yaw
        lwz r0, 0x24(r1)
        mtlr r0
        lwz r31, 0x1C(r1)
        addi r1, r1, 0x20
        blr
    w_yaw:
        lwz r12, 8(r3)
        cmplwi r12, 0x60
        bgelr
        lis r10, 0x%(YH)04X
        addi r10, r10, %(YL)d
        srwi r11, r12, 5
        slwi r11, r11, 2
        addi r11, r11, 0xC
        lwzx r11, r10, r11
        clrlwi r12, r12, 27
        srw r11, r11, r12
        andi. r11, r11, 1
        beqlr
        lwz r9, 0(r3)
        lwz r8, 0x311C(r9)
        lfs f0, 0x60(r8)
        lfs f2, 0(r10)
        fcmpu cr0, f0, f2
        bnelr
        lfs f0, 0x64(r8)
        lfs f2, 4(r10)
        fcmpu cr0, f0, f2
        bnelr
        lfs f2, 8(r10)
        stfs f2, 0x64(r8)
        lwz r11, 0x3118(r9)
        li r0, 0
        stw r0, 0x20(r11)
        lwz r11, 0x30F0(r9)
        lwz r0, 0xFC(r11)
        cmpwi r0, 1
        bnelr
        li r0, 2
        stw r0, 0xFC(r11)
        blr
    """ % dict(SH=SET_LR >> 16, SL=SET_LR & 0xFFFF, RH=REVERSE_LR >> 16, RL=REVERSE_LR & 0xFFFF,
               YH=ha(D['yawk']), YL=sx(D['yawk'])))
    # L1120C, the wall bounce: on any contact (is_touch(0xFF)) v = energy 0's speed, n = get_ground_normal(0xFF);
    # r = |v|^2 / (P4 * P4); r < 0.1 (and r <= 1): nothing; else v reflected on n (v - 2 (n.v) n), normalised,
    # times P3 * min(r, 1) -> set_current_speed
    G.asm("""
    f_gbounce:
        mflr r0
        stw r0, 0x1C(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0xFF
        bl 0x%(TOUCH)08X
        cmpwi r3, 0
        beq gb_out
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        lwz r3, 0x18(r3)
        li r4, 0xFF
        bl 0x%(GN)08X
        stw r3, 8(r1)
        stw r4, 0xC(r1)
        lwz r12, 0x%(E0)X(r31)
        lfs f1, 0(r12)
        lfs f2, 4(r12)
        fmuls f5, f1, f1
        fmadds f5, f2, f2, f5
        lfs f6, 0x%(P4)X(r30)
        fmuls f6, f6, f6
        fdivs f5, f5, f6
        lfs f6, 0x%(ONE)X(r30)
        fcmpu cr0, f5, f6
        bgt gb_clamp
        lfs f7, 0x%(P6)X(r30)
        fcmpu cr0, f5, f7
        blt gb_out
        b gb_refl
    gb_clamp:
        fmr f5, f6
    gb_refl:
        lfs f3, 8(r1)
        lfs f4, 0xC(r1)
        fmuls f8, f3, f1
        fmadds f8, f4, f2, f8
        fadds f8, f8, f8
        fnmsubs f1, f3, f8, f1
        fnmsubs f2, f4, f8, f2
        lfs f0, 0x%(P3)X(r30)
        fmuls f5, f5, f0
        stfs f1, 8(r1)
        stfs f2, 0xC(r1)
        stfs f5, 0x10(r1)
        fmuls f1, f1, f1
        fmadds f1, f2, f2, f1
        lfs f0, 0x%(ZERO)X(r30)
        fcmpu cr0, f1, f0
        beq gb_set
        bl 0x%(SQ)08X
        lfs f5, 0x10(r1)
        fdivs f5, f5, f1
        lfs f1, 8(r1)
        lfs f2, 0xC(r1)
        fmuls f1, f1, f5
        fmuls f2, f2, f5
        stfs f1, 8(r1)
        stfs f2, 0xC(r1)
    gb_set:
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 8
        bl 0x%(SS)08X
    gb_out:
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """ % dict(TOUCH=IS_TOUCH, GN=GROUND_NORMAL, E0=AER + 4, P4=P(4), ONE=P(24), P6=P(6), P3=P(3), ZERO=P(25),
               SQ=SQRTF, AER=AER, SS=AER_SET_SPEED))
    # 1 fly (enter 0x1091C, update 0x10E24): kinetic 26, f_gpick, ground off, passable on, FlyHoming (loop), the
    # aerial target = V3 (set_target: +0x30 id, +0x40 offset 0, +0x2C 0). Update: the aerial update, V0 runs out ->
    # f_gpick, the bounce, V1 runs out -> 3 (leave). Contact attack: P2 entry 1 (set_attack_data(1))
    st('f_g1_en', """
        li r4, 26
        bl h_kin
        bl f_gpick
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 1
        li r5, 1
        bl h_mot1
        lwz r0, 0x%(V3)X(r31)
        stw r0, 0x%(T)X(r31)
        li r0, 0
        stw r0, 0x%(O)X(r31)
        stw r0, 0x%(O4)X(r31)
        stw r0, 0x%(O8)X(r31)
        stb r0, 0x%(F)X(r31)""" % dict(V3=V(3), T=AER + 0x30, O=AER + 0x40, O4=AER + 0x44, O8=AER + 0x48,
                                      F=AER + 0x2C))
    st('f_g1_up', """
        addi r3, r31, 0x%(AER)X
        bl 0x%(UPD)08X
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V0)X(r31)
        cmpwi r3, 0
        bgt g1_b
        bl f_gpick
    g1_b:
        bl f_gbounce
        lwz r3, 0x%(V1)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V1)X(r31)
        cmpwi r3, 0
        bgt.far epi
        li r4, 3
        b go""" % dict(AER=AER, UPD=AER_UPDATE, V0=V(0), V1=V(1)))
    # 2 stun (enter 0x10AD0, update 0x10EE4): kinetic 16, ground off, passable on, DamageStart (once), V2 =
    # hit_return_frame(), the kinetic flag 0x80 set (set_node_visibility(1, 0) / (0, 1): not ported); V2 runs out ->
    # flag 0x80 cleared, -> 1
    st('f_g2_en', """
        li r4, 16
        bl h_kin
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 0
        li r5, 0
        bl h_mot1
        bl f_hitret
        stw r3, 0x%(V2)X(r31)
        bl f_kflag
        lwz r0, 0(r12)
        ori r0, r0, 0x80
        stw r0, 0(r12)""" % dict(V2=V(2)))
    st('f_g2_up', """
        lwz r3, 0x%(V2)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V2)X(r31)
        cmpwi r3, 0
        bgt.far epi
        bl f_kflag
        lwz r0, 0(r12)
        rlwinm r0, r0, 0, 25, 23
        stw r0, 0(r12)
        li r4, 1
        b go""" % dict(V2=V(2)))
    # slot 31 (0x113F0; the Wii U calls its slot 31 with the hit record before notify_on_damage, as the 3DS): immune
    # (GH_IMM = 1) when the hit is direct. The 3DS: category 1 (a weapon) immune when is_weapon_as_fighter(kind)
    # (3DS weapon kinds 0x179 / 0x17A / 0x180-0x182), category 4 (an item) when held and not kind 0x12 / 0x24, any
    # other (a fighter's own attack) when the AttackData's byte +0x4C is set. Approximated: every category by that
    # byte (the Wii U's twins of is_weapon_as_fighter / Item::is_haved are not found; projectiles and thrown items
    # are indirect hitboxes); not ported: the module acc+0x3074 byte +0x5A2 = 0 / 1 and play_se(15)
    G.asm("""
    f_g31:
        b gh_31                     # step 2i: the 3DS's per-category rules (code_vis)
    """)
    # slot 10 notify_on_damage (0x11094): immune (GH_IMM) -> DamageModuleImpl::init_damage(GH_DMG) (the HP before
    # the hit) and no reaction; else GH_DMG = damage(0) (entry 0's +0, as 3DS DamageModuleImpl::damage(int)
    # 0x9512CC) and BehaviorImpl's; then V1 = P5 (1200: the leave timer restarts). stop_se not ported
    G.asm("f_ghos_dmg:\nmflr r0\nbl pro\nlwz r3, 0(r31)\nlwz r3, 0x30D4(r3)\nlbz r0, 0x%X(r31)\ncmpwi r0, 0\n"
          "beq gd_n\nlfs f1, 0x%X(r31)" % (GH_IMM, GH_DMG))
    far(INIT_DAMAGE)
    G.asm("b gd_t\ngd_n:\nlwz r3, 0xC(r3)\nlfs f0, 0(r3)\nstfs f0, 0x%X(r31)\nmr r3, r31" % GH_DMG)
    far(BI_NOTIFY_DMG)
    G.asm("gd_t:\nlwz r0, 0x%X(r30)\nstw r0, 0x%X(r31)\nb epi" % (P(5), V(1)))
    # slot 69 (0x113A4; the Wii U notify_on_damage calls it as the 3DS's does): a leave running -> finalised and
    # set_correct(5); => 2 (stun); returns 1 (the framework's own reaction skipped)
    st('f_ghos_69', "bl f_unleave\nli r4, 2\nbl h_chgi\nli r3, 1")
    # slot 27 notify_on_remove (the 3DS's 28, 0x11140): the body effect V4 removed, then BehaviorImpl's
    G.asm("""
    f_ghos_rm:
        mflr r0
        bl pro
        lwz r4, 0x%X(r31)
        cmpwi r4, 0
        beq gr_out
        mr r3, r31
        li r0, 0
        stw r0, 0x%X(r31)
    """ % (V(4), V(4)))
    far(REMOVE_EFFECT)
    G.asm("gr_out:\nmr r3, r31\nlmw r28, 0x20(r1)\nlwz r0, 0x34(r1)\nmtlr r0\naddi r1, r1, 0x30")
    G.asm("lis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctr" % (orig(27) >> 16, orig(27) & 0xFFFF))
    # ---- the aerial modes the Wii U has no setter for (3DS EnemyAerialModuleImpl: every setter is the mode word,
    # energy 0's init vt+0x1C(0x17, &speed, &zero3, acc) (3DS vt+0xC), energy 0 on (+0x18 = 1), energy 1 off):
    # f_amode(r4 mode; the speed at the caller's r1+8): set_mode_none 0x5F58C8 (-1, speed 0), set_mode_uniform
    # 0x5F5BD4 (5, the given speed: the update does nothing in mode 5, on both), set_mode_braking 0x5F5B48 (4, the
    # current speed; +0x18 / +0x1C the two params); set_mode_homing_extend 0x5F60F0 = set_mode_homing (the slip
    # variant with speed 0: f_ahome zeroes energy 0's speed, then the Wii U's slip_homing_extend 0x02DB2A48)
    G.asm("""
    f_anone:
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        li r4, -1
    f_amode:
        mflr r0
        stw r0, 0x1C(r1)
        stw r4, 0x%(M)X(r31)
        li r0, 0
        stw r0, 0x10(r1)
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        lwz r3, 0x%(E0)X(r31)
        lwz r12, 0x1C(r3)
        lwz r12, 0x1C(r12)
        mtctr r12
        li r4, 0x17
        addi r5, r1, 8
        addi r6, r1, 0x10
        lwz r7, 0x%(AER)X(r31)
        bctrl
        li r0, 1
        lwz r12, 0x%(E0)X(r31)
        stb r0, 0x18(r12)
        li r0, 0
        lwz r12, 0x%(E1)X(r31)
        stb r0, 0x18(r12)
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    f_ahome:
        mflr r0
        stw r0, 0x1C(r1)
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stfs f1, 0x10(r1)
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 8
        bl 0x%(SS)08X
        lfs f1, 0x10(r1)
        lfs f2, 4(r28)
        lfs f3, 8(r28)
        lfs f4, 0xC(r28)
        lfs f5, 0x10(r28)
        lfs f6, 0x14(r28)
        addi r3, r31, 0x%(AER)X
        lwz r0, 0x1C(r1)
        mtlr r0
        b 0x%(SHE)08X
    f_aupd:
        addi r3, r31, 0x%(AER)X
        b 0x%(UPD)08X
    """ % dict(M=AER + 0xC, E0=AER + 4, E1=AER + 8, AER=AER, SS=AER_SET_SPEED, SHE=AER_SLIP_HOMING_EXT,
               UPD=AER_UPDATE))

    # ---- Tikibuzz (kind 0x0F; create 0x78630, table 0x10E134). V0 the search counter (+0x1DC), V1 the search
    # cool-down (+0x1E0), V2 the dive frames (+0x1E4), V3 the stomp frames (+0x1E8), V4 the landing frames
    # (+0x1EC), V5 the leave frames (+0x1F4), V6 the target's y (+0x1FC), Y0 the last y (+0x1F8). P0-P20: its P0
    # row (variation 0), P21 the leave frames (P@0x78 f0: 200)
    def tp(i):
        return P(i)
    G.asm("f_tiki_start:\nmflr r0\nbl pro\naddi r3, r31, 0x%X\nlwz r4, 0(r31)\nbl 0x%08X\nmr r3, r31" % (AER, AER_CTOR))   # step 2f: set_rhombus(this) (r3 was the aerial module)
    far(SET_RHOMBUS)
    G.asm("""
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x60(r12)
        stw r0, 0x10(r31)
        li r0, 0
        stw r0, 0x14(r31)
        stw r0, 0x18(r31)
        bl h_near
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        beq ts_go
        bl h_rev
    ts_go:
        li r4, 3
        b go
    """)
    # 1 fall (0x77BD8 / 0x77E10): kinetic 8, ground off, Fly (loop); on the ground -> 3
    st('t_fall_en', "li r4, 8\nbl h_kin\nli r4, 0\nbl h_att\nli r4, 11\nli r5, 1\nbl h_mot1")
    st('t_fall_up', "bl h_gnd\ncmpwi r3, 0\nbeq.far epi\nli r4, 3\nb go")
    # 3 fly (0x78668 / 0x77A2C): ground off, passable, Y0 = y, Fly (loop), set_mode_homing_extend(f3, f4, f7, f8,
    # f5, f6), the swing fields (+0x54 = 1, +0x5C = 0, +0x58 = -1), the target fighter 0 at (0, f1 (35), 0), V0 = 0
    # (the meshes' visibility: not ported). Update: the aerial update, Y0 = y (the flap rate MotionModule +0x50 =
    # f9 / f10 rising / not: not ported); V1 > 0 counts down, else every search-0 interval (30) frames of V0
    # search_target(0) (15 x 60 below it) -> 4, V1 = int(f17) (152); V0 < f2 (900): V0++, else -> 9 (leave)
    st('t_fly_en', """
        li r4, 0
        bl h_att
        bl f_pass1
        bl h_sety
        li r4, 11
        li r5, 1
        bl h_mot1
        addi r28, r30, 0x%(PH)X
        lfs f1, 0(r28)
        bl f_ahome
        li r0, 1
        stb r0, 0x%(S54)X(r31)
        li r0, 0
        stw r0, 0x%(S5C)X(r31)
        stw r0, 0x%(V0)X(r31)
        stw r0, 0x%(T)X(r31)
        stw r0, 0x%(O)X(r31)
        stw r0, 0x%(O8)X(r31)
        stb r0, 0x%(F)X(r31)
        lis r0, 0xBF80
        stw r0, 0x%(S58)X(r31)
        lfs f1, 0x%(P1)X(r30)
        stfs f1, 0x%(O4)X(r31)""" % dict(PH=P(22), S54=AER + 0x54, S5C=AER + 0x5C, S58=AER + 0x58, V0=V(0),
                                         T=AER + 0x30, O=AER + 0x40, O4=AER + 0x44, O8=AER + 0x48, F=AER + 0x2C,
                                         P1=tp(1)))
    st('t_fly_up', """
        bl f_aupd
        bl h_sety
        lwz r3, 0x%(V1)X(r31)
        cmpwi r3, 0
        ble tf_srch
        addi r3, r3, -1
        stw r3, 0x%(V1)X(r31)
        b tf_cnt
    tf_srch:
        li r4, 0
        bl h_grp
        lwz r0, 0x%(V0)X(r31)
        divw r12, r0, r3
        mullw r12, r12, r3
        cmpw r12, r0
        bne tf_cnt
        li r4, 0
        bl h_srch
        cmpwi r3, -1
        beq tf_cnt
        li r4, 4
        bl h_chg
        lfs f1, 0x%(P17)X(r30)
        fctiwz f1, f1
        stfd f1, 8(r1)
        lwz r0, 0xC(r1)
        stw r0, 0x%(V1)X(r31)
        b epi
    tf_cnt:
        lwz r3, 0x%(V0)X(r31)
        lwz r0, 0x%(P2)X(r30)
        cmpw r0, r3
        ble tf_leave
        addi r3, r3, 1
        stw r3, 0x%(V0)X(r31)
        b epi
    tf_leave:
        li r4, 9
        b go""" % dict(V0=V(0), V1=V(1), P17=tp(17), P2=tp(2)))
    # 4 hold (0x780A4 / 0x78410): ground off, passable, AttackHold at f11 (0.75), set_mode_none, kinetic 11, V6 =
    # fighter 0's y (get_fighter_pos(0)); the aerial update, at the motion's end -> 5
    st('t_hold_en', """
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 2
        li r5, 0
        lfs f2, 0x%(P11)X(r30)
        bl h_mot
        bl f_anone
        li r4, 11
        bl h_kin
        addi r3, r1, 8
        mr r4, r31
        li r5, 0
        lis r12, 0x%(GH)04X
        ori r12, r12, 0x%(GL)04X
        mtctr r12
        bctrl
        lwz r0, 0xC(r1)
        stw r0, 0x%(V6)X(r31)""" % dict(P11=tp(11), GH=GET_TARGET_POS >> 16, GL=GET_TARGET_POS & 0xFFFF, V6=V(6)))
    st('t_hold_up', "bl f_aupd\nbl h_end\ncmpwi r3, 0\nbeq.far epi\nli r4, 5\nb go")
    # 5 dive (0x77964 / 0x77CB0; the contact attack, P2 entry 0): ground off, passable, Attack (loop),
    # set_mode_uniform((0, -f12)) (-6 a frame), V2 = 0; the aerial update; at / below V6 passable off; on the
    # ground => 7; V2 < f13 (9): V2++, else -> 6
    st('t_dive_en', """
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 0
        li r5, 1
        bl h_mot1
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0x%(V2)X(r31)
        lfs f1, 0x%(P12)X(r30)
        fneg f1, f1
        stfs f1, 0xC(r1)
        li r4, 5
        bl f_amode""" % dict(V2=V(2), P12=tp(12)))
    st('t_dive_up', """
        bl f_aupd
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        lfs f0, 0x%(V6)X(r31)
        fcmpu cr0, f1, f0
        bgt td_t
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0
        bl 0x%(SP)08X
    td_t:
        bl h_gnd
        cmpwi r3, 0
        beq td_c
        li r4, 7
        b goi
    td_c:
        lwz r3, 0x%(V2)X(r31)
        lwz r0, 0x%(P13)X(r30)
        cmpw r0, r3
        ble td_brk
        addi r3, r3, 1
        stw r3, 0x%(V2)X(r31)
        b epi
    td_brk:
        li r4, 6
        b go""" % dict(V6=V(6), SP=SET_PASSABLE, V2=V(2), P13=tp(13)))
    # 6 brake (0x78240 / 0x784B4): ground off, passable, AttackBrake at f16 (0.7), set_mode_braking(0, f15);
    # the aerial update; on the ground: speed 0, set_mode_none, at the motion's end -> 3; in the air: rising or
    # still (speed y >= 0) -> 3
    st('t_brk_en', """
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 1
        li r5, 0
        lfs f2, 0x%(P16)X(r30)
        bl h_mot
        lwz r12, 0x%(E0)X(r31)
        lwz r0, 0(r12)
        stw r0, 8(r1)
        lwz r0, 4(r12)
        stw r0, 0xC(r1)
        li r4, 4
        bl f_amode
        li r0, 0
        stw r0, 0x%(B0)X(r31)
        lwz r0, 0x%(P15)X(r30)
        stw r0, 0x%(B1)X(r31)""" % dict(P16=tp(16), E0=AER + 4, B0=AER + 0x18, B1=AER + 0x1C, P15=tp(15)))
    st('t_brk_up', """
        bl f_aupd
        bl h_vy0
        stfs f1, 0x18(r1)
        bl h_gnd
        cmpwi r3, 0
        beq tb_air
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 8
        bl 0x%(SS)08X
        bl f_anone
        bl h_end
        cmpwi r3, 0
        beq.far epi
        b tb_go
    tb_air:
        lfs f1, 0x18(r1)
        lfs f0, 0x%(Z)X(r30)
        fcmpu cr0, f1, f0
        blt.far epi
    tb_go:
        li r4, 3
        b go""" % dict(AER=AER, SS=AER_SET_SPEED, Z=P(28)))
    # 7 landed (0x78454 / 0x78554): ground on, AttackUnguard, set_mode_none, V4 = 0, request_quake(3); the aerial
    # update; V4 < f14 (45): V4++, else -> 8. 8 ready (0x77D7C / 0x78204): ground off, FlyReady, set_mode_none; at
    # its end -> 3
    st('t_land_en', """
        li r4, 1
        bl h_att
        li r4, 3
        li r5, 0
        bl h_mot1
        bl f_anone
        li r0, 0
        stw r0, 0x%(V4)X(r31)
        mr r3, r31
        li r4, 3
        lis r12, 0x%(QH)04X
        ori r12, r12, 0x%(QL)04X
        mtctr r12
        bctrl""" % dict(V4=V(4), QH=REQ_QUAKE >> 16, QL=REQ_QUAKE & 0xFFFF))
    st('t_land_up', """
        bl f_aupd
        lwz r3, 0x%(V4)X(r31)
        lwz r0, 0x%(P14)X(r30)
        cmpw r0, r3
        ble tl_go
        addi r3, r3, 1
        stw r3, 0x%(V4)X(r31)
        b epi
    tl_go:
        li r4, 8
        b go""" % dict(V4=V(4), P14=tp(14)))
    st('t_rdy_en', "li r4, 0\nbl h_att\nli r4, 12\nli r5, 0\nbl h_mot1\nbl f_anone")
    st('t_rdy_up', "bl h_end\ncmpwi r3, 0\nbeq.far epi\nli r4, 3\nb go")
    # 9 leave (0x7781C / 0x77C40): ground off, passable, Fly (loop), set_correct(0), set_mode_none, V5 = 200; the
    # aerial update; V5 runs out -> 12 (removed)
    st('t_lv_en', """
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 11
        li r5, 1
        bl h_mot1
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0
        bl 0x%(SC)08X
        bl f_anone
        lwz r0, 0x%(P21)X(r30)
        stw r0, 0x%(V5)X(r31)""" % dict(SC=SET_CORRECT, P21=tp(21), V5=V(5)))
    st('t_lv_up', """
        bl f_aupd
        lwz r3, 0x%(V5)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V5)X(r31)
        cmpwi r3, 0
        bgt.far epi
        lwz r4, 0x%(RM)X(r30)
        b go""" % dict(V5=V(5), RM=CF['REMOVE']))
    # 10 stomped (slot 21 -> 10; 0x77F04 / 0x78388): ground off, passable, Step, create_dead_item(1, 10) (the
    # removal's defeat path here: DEFEATED), disable_hit (notify_on_death: hit off, attacks cleared, as the Goomba's
    # collapse), V3 = 0, set_mode_uniform((0, -f19)) (-3), effect 0x70F0000 at the body (the meshes, play_se: not
    # ported); the aerial update; V3 < f20 (60) and not on the ground: V3++, else -> 11
    st('t_stomp_en', """
        li r0, 1
        stw r0, 0x%(DF)X(r31)
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 13
        li r5, 0
        bl h_mot1
        mr r3, r31
        lis r12, 0x%(NDH)04X
        ori r12, r12, 0x%(NDL)04X
        mtctr r12
        bctrl
        li r0, 0
        stw r0, 0x%(V3)X(r31)
        stw r0, 8(r1)
        lfs f1, 0x%(P19)X(r30)
        fneg f1, f1
        stfs f1, 0xC(r1)
        li r4, 5
        bl f_amode
        lis r4, 0x70F
        bl t_fx""" % dict(DF=DEFEATED, NDH=NOTIFY_DEATH >> 16, NDL=NOTIFY_DEATH & 0xFFFF, V3=V(3),
                                               P19=tp(19)))
    st('t_stomp_up', """
        bl f_aupd
        lwz r3, 0x%(V3)X(r31)
        lwz r0, 0x%(P20)X(r30)
        cmpw r0, r3
        ble ts_gone
        bl h_gnd
        cmpwi r3, 0
        bne ts_gone
        lwz r3, 0x%(V3)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(V3)X(r31)
        b epi
    ts_gone:
        li r4, 11
        b go""" % dict(V3=V(3), P20=tp(20)))
    # 11 gone (0x77E50 / 0x78378): kinetic 26, ground on, passable, effect 0x70F0001 at the body (set_visibility(0),
    # play_se: not ported); -> 12
    st('t_gone_en', "li r4, 26\nbl h_kin\nli r4, 1\nbl h_att\nbl f_pass1\nlis r4, 0x70F\nori r4, r4, 1\nbl t_fx")
    st('t_gone_up', "lwz r4, 0x%X(r30)\nb go" % CF['REMOVE'])
    # t_fx(r4 id): request_effect(id, the posture position, rotation 0, 1.0) (3DS EffectModuleImpl::req(id,
    # posture +0x14, ZERO, 1, ...))
    G.asm("""
    t_fx:
        mflr r0
        stw r0, 0x1C(r1)
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lwz r5, 0(r31)
        lwz r5, 0x311C(r5)
        addi r5, r5, 0x10
        addi r6, r1, 8
        mr r3, r31
    """)
    lfs('f1', 'consts', 4)
    G.asm("""
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        mtctr r12
        bctrl
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """ % (REQ_EFFECT >> 16, REQ_EFFECT & 0xFFFF))
    # ---- Furiijio (kind 0x1A; enemy_fs.cro create 0x6DC6C, table 0x10D168; docs/smash-run-port.md "Step 2f").
    # V0 the search counter (3DS +0x1DC), V1 the search cool-down (+0x1E4), V2 the leave timer (+0x1E8), V3 the target
    # (+0x1EC), V4 the state frames (+0x1E0), V5 / V6 the common leave, V7 the sweep step (+0x1F0), V8 the beam length
    # (+0x248); FU_C the centre offset (+0x218), FU_ROT BeamN's angles in degrees (+0x224), FU_E the beam's three
    # follow effects (+0x254 / +0x258 / +0x25C). The 3DS's node offset +0x230 is (P@0x9C x 10 = 0) rotated: zero.
    # P0-5 set_mode_homing (P0 row, variation 0), 6 leave frames 900, 7 target offset y 25 (2.5 x 10), 8 / 9 the
    # beam choice (random(0, 2) < 1: sweep), 10 0 (the node offset), 11 10 (the aim effect's offset), 12 1.5 (its
    # scale), 13 aim frames 25, 14 cool-down 150, 15 beam length cap 200, 16 charge frames 22, 17 growth 4.5, 18 beam
    # frames 60, 19 sweep charge 34, 20 / 21 the sweep side (random(0, 1) < 1), 22 sweep frames 140, 23 180 / 140,
    # 24 P@0xD4 15, 25 1.5, 26 0.05, 27 deg -> rad, 28 90, 29 1, 30 0, 31-35 the leave (P6), 36-41 FU_CALC
    fp = lambda i: P(i)  # noqa: E731
    d = dict(AER=AER, V0=V(0), V1=V(1), V2=V(2), V3=V(3), V4=V(4), V7=V(7), V8=V(8), C=FU_C, C4=FU_C + 4,
             C8=FU_C + 8, R=FU_ROT, R4=FU_ROT + 4, R8=FU_ROT + 8, E=FU_E, E4=FU_E + 4, E8=FU_E + 8,
             SNR=SET_NODE_ROT, SNT=SET_NODE_TRANS, DIRTY=MODEL_NODE_DIRTY, OFS=ATK_SET_OFFSET, EPOS=EFF_SET_POS,
             ESC=EFF_SET_SCALE, SQ=SQRTF, SIN=SINF, COS=COSF, ACOS=ACOSF, SS=AER_SET_SPEED, SH=AER_SLIP_HOMING,
             CK=CHANGE_KINETIC, BUL=BULLET, DEF=DEFEATED, DM=CF['DEADMOT'],
             **{'P%d' % i: fp(i) for i in range(42)})
    # fu_node: BeamN (node 3) turned to FU_ROT (set_node_rotate(3, rad, 0); a change -> the ModelModule's vt+0xC4, as
    # the Wii U's own callers do) and placed at the posture + FU_C (+ the zero offset) in global space
    # (set_node_translate(3, &v, 1, 0) + vt+0xC4: the 3DS's Behavior::set_node_global_position 0x7B5224). Step 2j:
    # FU_ROT is the 3DS's (0, a lr, 90) (fu3_en / fu6_en): the beam models' bones are Y-axial billboards (H3D billboard
    # mode 6 in BeamBG / BeamBG2 / BeamBody's flags), now tagged _BILLBOARDYAXIS_ in the converted effect models
    # (tools/s3ds_effect_models.py, BILLBOARD_IN_CODE empty), so the game turns their planes to the camera about the
    # beam; the step 2g v5 / v6 turn in the angles (x 90 x -lr) is gone (both games build the node matrix as Rz Ry Rx:
    # 3DS Matrix34::set_rotate_xyz 0x87D298, Wii U 0x033730A0). The 3DS's
    # set_rotation_order_zxy (ModelModule +0x21 = 1) is the model root's order (3DS 0xA6DBF8: the posture rotation
    # through set_rotate_zxy 0x87D3B4), the same as xyz for a yaw-only posture: nothing to port
    G.asm("""
    fu_node:
        mflr r0
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        lfs f0, 0x%(P27)X(r30)
        lfs f1, 0x%(R)X(r31)
        fmuls f1, f1, f0
        stfs f1, 8(r1)
        lfs f1, 0x%(R4)X(r31)
        fmuls f1, f1, f0
        stfs f1, 0xC(r1)
        lfs f1, 0x%(R8)X(r31)
        fmuls f1, f1, f0
        stfs f1, 0x10(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30F0(r3)
        li r4, 3
        addi r5, r1, 8
        li r6, 0
        bl 0x%(SNR)08X
        cmpwi r3, 0
        beq fu_n1
        bl fu_dirty
    fu_n1:
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x10(r12)
        lfs f0, 0x%(C)X(r31)
        fadds f1, f1, f0
        stfs f1, 8(r1)
        lfs f1, 0x14(r12)
        lfs f0, 0x%(C4)X(r31)
        fadds f1, f1, f0
        stfs f1, 0xC(r1)
        lfs f1, 0x18(r12)
        lfs f0, 0x%(C8)X(r31)
        fadds f1, f1, f0
        stfs f1, 0x10(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30F0(r3)
        li r4, 3
        addi r5, r1, 8
        li r6, 1
        li r7, 0
        bl 0x%(SNT)08X
        cmpwi r3, 0
        beq fu_n2
        bl fu_dirty
    fu_n2:
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    fu_dirty:
        lwz r3, 0(r31)
        lwz r3, 0x3118(r3)
        lwz r12, 0(r3)
        lwz r12, 0x%(DIRTY)X(r12)
        mtctr r12
        bctr
    fu_grow:
        lfs f1, 0x%(V8)X(r31)
        lfs f0, 0x%(P17)X(r30)
        fadds f1, f1, f0
        stfs f1, 0x%(V8)X(r31)
        lfs f0, 0x%(P15)X(r30)
        fcmpu cr0, f0, f1
        bgelr
        stfs f0, 0x%(V8)X(r31)
        blr
    fu_beam:
        mflr r0
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        lfs f1, 0x%(V8)X(r31)
        lfs f0, 0x%(P25)X(r30)
        fmuls f1, f1, f0
        lfs f0, 0x%(P24)X(r30)
        fadds f1, f1, f0
        stfs f1, 8(r1)
        li r0, 0
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30C8(r3)
        li r4, 0
        addi r5, r1, 8
        bl 0x%(OFS)08X
        lfs f1, 0x%(V8)X(r31)
        lfs f0, 0x%(P26)X(r30)
        fmuls f1, f1, f0
        stfs f1, 8(r1)
        lfs f0, 0x%(P29)X(r30)
        stfs f0, 0xC(r1)
        stfs f0, 0x10(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30D8(r3)
        lwz r4, 0x%(E4)X(r31)
        addi r5, r1, 8
        bl 0x%(ESC)08X
        lwz r0, 0x%(V8)X(r31)
        stw r0, 8(r1)
        li r0, 0
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30D8(r3)
        lwz r4, 0x%(E8)X(r31)
        addi r5, r1, 8
        bl 0x%(EPOS)08X
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    fu_clamp:
        lfs f0, 0x%(P40)X(r30)
        fcmpu cr0, f1, f0
        bge fu_cl1
        fmr f1, f0
        blr
    fu_cl1:
        lfs f0, 0x%(P29)X(r30)
        fcmpu cr0, f1, f0
        blelr
        fmr f1, f0
        blr
    fu_calc:
        mflr r0
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        stfs f1, 8(r1)
        stfs f2, 0xC(r1)
        fmuls f0, f1, f1
        fmuls f3, f2, f2
        fadds f1, f0, f3
        lfs f0, 0x%(P30)X(r30)
        fcmpu cr0, f1, f0
        beq fu_c1
        bl 0x%(SQ)08X
        lfs f0, 0x%(P29)X(r30)
        fdivs f0, f0, f1
        lfs f1, 8(r1)
        fmuls f1, f1, f0
        stfs f1, 8(r1)
        lfs f1, 0xC(r1)
        fmuls f1, f1, f0
        stfs f1, 0xC(r1)
    fu_c1:
        lfs f1, 0xC(r1)
        bl fu_clamp
        bl 0x%(ACOS)08X
        stfs f1, 0x10(r1)
        lfs f1, 8(r1)
        bl fu_clamp
        bl 0x%(ACOS)08X
        lfs f0, 0x%(P36)X(r30)
        lfs f2, 0x%(P38)X(r30)
        fcmpu cr0, f1, f0
        bge fu_c2
        lfs f2, 0x%(P39)X(r30)
    fu_c2:
        lfs f1, 0x10(r1)
        lfs f0, 0x%(P37)X(r30)
        fmuls f1, f1, f0
        fmuls f1, f1, f2
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    fu_angle:
        mflr r0
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        addi r3, r1, 8
        mr r4, r31
        lwz r5, 0x%(V3)X(r31)
    """ % d)
    far(GET_TARGET_POS)
    G.asm("""
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x10(r12)
        lfs f2, 0x%(C)X(r31)
        fadds f0, f0, f2
        lfs f1, 8(r1)
        fsubs f1, f1, f0
        lfs f0, 0x14(r12)
        lfs f3, 0x%(C4)X(r31)
        fadds f0, f0, f3
        lfs f2, 0xC(r1)
        fsubs f2, f2, f0
        bl fu_calc
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    fu_tgt:
        lwz r0, 0x%(V3)X(r31)
        stw r0, 0x%(T)X(r31)
        li r0, 0
        stw r0, 0x%(O)X(r31)
        stw r0, 0x%(O8)X(r31)
        stb r0, 0x%(F)X(r31)
        lwz r0, 0x%(P7)X(r30)
        stw r0, 0x%(O4)X(r31)
        blr
    fu_follow:
        mflr r0
        stw r0, 0x1C(r1)
        mr r3, r31
        addi r6, r1, 8
        addi r7, r1, 8
        lfs f1, 0x%(P29)X(r30)
        lis r12, 0x%(RFH)04X
        ori r12, r12, 0x%(RFL)04X
        mtctr r12
        bctrl
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """ % dict(d, T=AER + 0x30, O=AER + 0x40, O4=AER + 0x44, O8=AER + 0x48, F=AER + 0x2C, RFH=REQ_FOLLOW >> 16,
               RFL=REQ_FOLLOW & 0xFFFF))
    # start 0x6BE88: the aerial module (the 3DS ctor's), set_rhombus, +0x10 = posture lr, +0x14 / +0x18 = 0, its
    # fields zero, V2 = 900, V3 = the nearest fighter (turned to it: check_turn_to_target -> reverse_lr(1, 1)), the
    # aerial target V3 at (0, 25, 0), -> 1
    G.asm("f_fu_start:\nmflr r0\nbl pro\naddi r3, r31, 0x%X\nlwz r4, 0(r31)\nbl 0x%08X\nmr r3, r31" % (AER, AER_CTOR))
    far(SET_RHOMBUS)
    G.asm("""
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x60(r12)
        stw r0, 0x10(r31)
        li r0, 0
        stw r0, 0x14(r31)
        stw r0, 0x18(r31)
        stw r0, 0x%(V1)X(r31)
        stw r0, 0x%(V4)X(r31)
        stw r0, 0x%(V7)X(r31)
        stw r0, 0x%(V8)X(r31)
        li r12, 10
        mtctr r12
        addi r12, r31, 0x%(Cm4)X
    fs_z:
        stwu r0, 4(r12)
        bdnz fs_z
        lwz r0, 0x%(P6)X(r30)
        stw r0, 0x%(V2)X(r31)
        bl h_near
        stw r3, 0x%(V3)X(r31)
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        beq fs_t
        bl h_rev
    fs_t:
        bl fu_tgt
        li r4, 1
        b go
    """ % dict(d, Cm4=FU_C - 4))
    # 1 fly (0x6BF78 / 0x6C0E8): set_mode_homing(P0-5) (energy 0's speed 0, then the slip homing setter: mode 2),
    # passable, ground off, Move (loop), V0 = search_interval(0) (50). Update: no target -> the nearest (none: the
    # frame ends) and the aerial target at it; the aerial update; V0 / V1 count down; both below 0: V0 = 50,
    # search_target(0) found -> V3 = it, V2 = 900, random(0, 2) < 1 -> 5 (sweep), else -> 2; otherwise V2 counts down
    # -> 8 (leave) at 0
    st('fu1_en', """
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 8
        bl 0x%(SS)08X
        lfs f1, 0x%(P0)X(r30)
        lfs f2, 0x%(P1)X(r30)
        lfs f3, 0x%(P2)X(r30)
        lfs f4, 0x%(P3)X(r30)
        lfs f5, 0x%(P4)X(r30)
        lfs f6, 0x%(P5)X(r30)
        addi r3, r31, 0x%(AER)X
        bl 0x%(SH)08X
        bl f_pass1
        li r4, 0
        bl h_att
        li r4, 9
        li r5, 1
        bl h_mot1
        li r4, 0
        bl h_grp
        stw r3, 0x%(V0)X(r31)""" % d)
    st('fu1_up', """
        lwz r3, 0x%(V3)X(r31)
        cmpwi r3, -1
        bne fu1_a
        bl h_near
        stw r3, 0x%(V3)X(r31)
        cmpwi r3, -1
        beq.far epi
        bl fu_tgt
    fu1_a:
        bl f_aupd
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V0)X(r31)
        lwz r4, 0x%(V1)X(r31)
        addi r4, r4, -1
        stw r4, 0x%(V1)X(r31)
        cmpwi r3, 0
        bge fu1_l
        cmpwi r4, 0
        bge fu1_l
        li r4, 0
        bl h_grp
        stw r3, 0x%(V0)X(r31)
        li r4, 0
        bl h_srch
        cmpwi r3, -1
        beq fu1_l
        stw r3, 0x%(V3)X(r31)
        lwz r0, 0x%(P6)X(r30)
        stw r0, 0x%(V2)X(r31)
        li r3, 0
        lwz r4, 0x%(P8)X(r30)
        lwz r0, 0x%(P9)X(r30)
        add r4, r4, r0
        addi r4, r4, -1
        bl h_rand
        lwz r0, 0x%(P9)X(r30)
        cmpw r3, r0
        li r4, 5
        blt fu1_go
        li r4, 2
    fu1_go:
        b go
    fu1_l:
        lwz r3, 0x%(V2)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V2)X(r31)
        cmpwi r3, 0
        bgt.far epi
        li r4, 8
        b go""" % d)
    # 2 / 5 charge (0x6D0F0 / 0x6D4F0): set_current_speed(0, 0), passable, ground off, IceBeamShotHold (loop),
    # FU_C = center_pos() - the posture, request_effect(0x71A0000 / 0x71A0001, the posture + FU_C, 1); V4 = 22 / 34
    # (play_se 0x6A90001 not ported). Update (0x6D924 / 0x6DA4C): V4 below 0 -> 3 / 6
    G.asm("fu2_en:\nmflr r0\nbl pro\nlis r28, 0x71A\nlwz r0, 0x%(P16)X(r30)\nb fu_chg" % d)
    G.asm("fu5_en:\nmflr r0\nbl pro\nlis r28, 0x71A\nori r28, r28, 1\nlwz r0, 0x%(P19)X(r30)" % d)
    G.asm("""
    fu_chg:
        stw r0, 0x%(V4)X(r31)
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 8
        bl 0x%(SS)08X
        bl f_pass1
        li r4, 0
        bl h_att
        li r4, 8
        li r5, 1
        bl h_mot1
        addi r3, r1, 8
        mr r4, r31
    """ % d)
    far(CENTER_POS)
    G.asm("""
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 8(r1)
        lfs f0, 0x10(r12)
        fsubs f1, f1, f0
        stfs f1, 0x%(C)X(r31)
        fadds f1, f0, f1
        stfs f1, 8(r1)
        lfs f1, 0xC(r1)
        lfs f0, 0x14(r12)
        fsubs f1, f1, f0
        stfs f1, 0x%(C4)X(r31)
        fadds f1, f0, f1
        stfs f1, 0xC(r1)
        lfs f1, 0x10(r1)
        lfs f0, 0x18(r12)
        fsubs f1, f1, f0
        stfs f1, 0x%(C8)X(r31)
        fadds f1, f0, f1
        stfs f1, 0x10(r1)
        mr r3, r31
        mr r4, r28
        addi r5, r1, 8
        lfs f1, 0x%(P29)X(r30)
    """ % d)
    far(REQ_EFFECT0)
    G.asm("b epi")
    for k, nxt in ((2, 3), (5, 6)):
        st('fu%d_up' % k, """
            lwz r3, 0x%(V4)X(r31)
            addi r3, r3, -1
            stw r3, 0x%(V4)X(r31)
            cmpwi r3, 0
            bge.far epi
            li r4, %(N)d
            b go""" % dict(d, N=nxt))
    # 3 / 6 aim (0x6D224 / 0x6D624): V8 = 0, a = calc_angle(the target - (the posture + FU_C)) (3DS 0x7B01D8:
    # normalised, acos(y) x 180 / pi, negated when acos(x) < pi / 2); 3: FU_ROT = (0, a lr, 90); 6: the step V7 =
    # 180 / 140 x lr, random(0, 1) < 1: V7 negated and FU_ROT y = a lr + 90 lr, else a lr - 90 lr; then fu_node and
    # request_effect(0x71A0005, node 2, offset (10 sin b, 10 cos b, 0) (b = -FU_ROT y in radians: (10, 0) turned by
    # 0x67364, its x / y swapped), rot (0, 0, lr FU_ROT y), 1.5); V4 = 25. Update (0x6D948 / 0x6DA70): fu_node; V4
    # below 0 -> V1 = 150 (the cool-down), -> 4 / 7
    G.asm("""
    fu_aimfin:
        bl fu_node
        lfs f1, 0x%(R4)X(r31)
        lfs f0, 0x%(P27)X(r30)
        fneg f0, f0
        fmuls f1, f1, f0
        stfs f1, 0x14(r1)
        fabs f2, f1
        lfs f0, 0x%(P41)X(r30)
        fcmpu cr0, f2, f0
        bge fu_af1
        lwz r0, 0x%(P11)X(r30)
        stw r0, 0xC(r1)
        li r0, 0
        stw r0, 8(r1)
        b fu_af2
    fu_af1:
        bl 0x%(COS)08X
        lfs f0, 0x%(P11)X(r30)
        fmuls f1, f0, f1
        stfs f1, 0xC(r1)
        lfs f1, 0x14(r1)
        bl 0x%(SIN)08X
        lfs f0, 0x%(P11)X(r30)
        fmuls f1, f0, f1
        stfs f1, 8(r1)
    fu_af2:
        li r0, 0
        stw r0, 0x10(r1)
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x60(r12)
        lfs f1, 0x%(R4)X(r31)
        fmuls f1, f0, f1
        stfs f1, 0x1C(r1)
        mr r3, r31
        lis r4, 0x71A
        ori r4, r4, 5
        li r5, 2
        addi r6, r1, 8
        addi r7, r1, 0x14
        lfs f1, 0x%(P12)X(r30)
    """ % d)
    far(REQ_NODE)
    G.asm("lwz r0, 0x%(P13)X(r30)\nstw r0, 0x%(V4)X(r31)\nb epi" % d)
    st('fu3_en', """
        li r0, 0
        stw r0, 0x%(V8)X(r31)
        bl fu_angle
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x60(r12)
        fmuls f1, f1, f0
        stfs f1, 0x%(R4)X(r31)
        lwz r0, 0x%(P28)X(r30)
        stw r0, 0x%(R8)X(r31)
        lwz r0, 0x%(P30)X(r30)
        stw r0, 0x%(R)X(r31)
        b fu_aimfin""" % d)
    st('fu6_en', """
        li r0, 0
        stw r0, 0x%(V8)X(r31)
        bl fu_angle
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x60(r12)
        fmuls f1, f1, f0
        stfs f1, 8(r1)
        stfs f0, 0xC(r1)
        li r3, 0
        lwz r4, 0x%(P20)X(r30)
        lwz r0, 0x%(P21)X(r30)
        add r4, r4, r0
        addi r4, r4, -1
        bl h_rand
        lfs f0, 0xC(r1)
        lfs f2, 0x%(P23)X(r30)
        fmuls f2, f2, f0
        lfs f3, 0x%(P28)X(r30)
        fmuls f3, f0, f3
        lfs f1, 8(r1)
        lwz r0, 0x%(P21)X(r30)
        cmpw r3, r0
        bge fu6_b
        fneg f2, f2
        fadds f1, f1, f3
        b fu6_c
    fu6_b:
        fsubs f1, f1, f3
    fu6_c:
        stfs f2, 0x%(V7)X(r31)
        stfs f1, 0x%(R4)X(r31)
        lwz r0, 0x%(P28)X(r30)
        stw r0, 0x%(R8)X(r31)
        lwz r0, 0x%(P30)X(r30)
        stw r0, 0x%(R)X(r31)
        b fu_aimfin""" % d)
    for k, nxt in ((3, 4), (6, 7)):
        st('fu%d_up' % k, """
            bl fu_node
            lwz r3, 0x%(V4)X(r31)
            addi r3, r3, -1
            stw r3, 0x%(V4)X(r31)
            cmpwi r3, 0
            bge.far epi
            lwz r0, 0x%(P14)X(r30)
            stw r0, 0x%(V1)X(r31)
            li r4, %(N)d
            b go""" % dict(d, N=nxt))
    # 4 / 7 the beam (enter 0x6C258 / 0x6C980): IceBeamShot (loop), V4 = 60 / 140, fu_node, follow effects
    # 0x71A0002 on node 2, 0x71A0004 / 0x71A0003 on node 3 (BeamN) -> FU_E (play_se 0x6A90002 not ported); the
    # contact attack P2 entry 0 / 1 (set_attack_data). Update (0x6CB80 / 0x6CE24): [4: fu_node] V4 below 0 -> 1;
    # else V8 += 4.5 (at most 200), the hitbox offset (V8 x 1.5 + 15, 0, 0) (AttackModule set_offset(0)), FU_E[1]
    # scaled (V8 x 0.05, 1, 1), FU_E[2] at (V8, 0, 0); [7: FU_ROT y += V7, fu_node]. Exit (0x6D094 / 0x6D494): the
    # three effects removed (stop_se not ported)
    G.asm("fu4_en:\nmflr r0\nbl pro\nlwz r0, 0x%(P18)X(r30)\nb fu_bst\nfu7_en:\nmflr r0\nbl pro\n"
          "lwz r0, 0x%(P22)X(r30)" % d)
    G.asm("""
    fu_bst:
        stw r0, 0x%(V4)X(r31)
        li r4, 7
        li r5, 1
        bl h_mot1
        bl fu_node
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lis r4, 0x71A
        ori r4, r4, 2
        li r5, 2
        bl fu_follow
        stw r3, 0x%(E)X(r31)
        lis r4, 0x71A
        ori r4, r4, 4
        li r5, 3
        bl fu_follow
        stw r3, 0x%(E4)X(r31)
        lis r4, 0x71A
        ori r4, r4, 3
        li r5, 3
        bl fu_follow
        stw r3, 0x%(E8)X(r31)
        b epi
    """ % d)
    st('fu4_up', """
        bl fu_node
        lwz r3, 0x%(V4)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V4)X(r31)
        cmpwi r3, 0
        bge fu4_b
        li r4, 1
        b go
    fu4_b:
        bl fu_grow
        bl fu_beam""" % d)
    st('fu7_up', """
        lwz r3, 0x%(V4)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V4)X(r31)
        cmpwi r3, 0
        bge fu7_b
        li r4, 1
        b go
    fu7_b:
        bl fu_grow
        bl fu_beam
        lfs f1, 0x%(R4)X(r31)
        lfs f0, 0x%(V7)X(r31)
        fadds f1, f1, f0
        stfs f1, 0x%(R4)X(r31)
        bl fu_node""" % d)
    G.asm("fu_bexit:\nmflr r0\nbl pro\naddi r28, r31, 0x%(E)X\nli r29, 3\nfu_bx:\nmr r3, r31\nlwz r4, 0(r28)" % d)
    far(REMOVE_EFFECT)
    G.asm("li r0, 0\nstw r0, 0(r28)\naddi r28, r28, 4\naddi r29, r29, -1\ncmpwi r29, 0\nbne fu_bx\nb epi")
    # 8 leave (0x6C058 / 0x6C408): IceBeamShot at rate 0, init_common_leave(P6: 200 frames, -0.01, 10, effect
    # 0x8000005 at (0, 5, 0) x 1) -> f_leave_en; the common leave's end -> 10 (o_leave_up)
    G.asm("""
    fu8_en:
        mflr r0
        bl pro
        li r4, 7
        li r5, 0
        bl h_mot0
        mr r3, r31
        mr r4, r29
        lmw r28, 0x20(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        b f_leave_en
    """)
    # 9 dead (0x6C0AC / 0x6CB2C): set_mode_none, DamageStart at rate 0, bullet() (P2 entry 2), defeated; the
    # kinetic flag 8 -> 10 (g_dead_up)
    st('fu9_en', """
        bl f_anone
        li r0, 1
        stw r0, 0x%(DEF)X(r31)
        lwz r4, 0x%(DM)X(r30)
        li r5, 0
        bl h_mot0
        mr r3, r31
        bl 0x%(BUL)08X""" % d)
    # slot 10 notify_on_damage (the 3DS's 11, 0x6CB64): V2 = 900, then BehaviorImpl's
    G.asm("""
    f_fu_dmg:
        lwz r12, 0x168(r3)
        lwz r0, 0x%(P6)X(r12)
        stw r0, 0x%(V2)X(r3)
        lis r12, 0x%(BH)04X
        ori r12, r12, 0x%(BL)04X
        mtctr r12
        bctr
    f_fu_kin:
        lwz r3, 0(r3)
        lwz r3, 0x30E8(r3)
        li r4, 26
        b 0x%(CK)08X
    """ % dict(d, BH=BI_NOTIFY_DMG >> 16, BL=BI_NOTIFY_DMG & 0xFFFF))
    # slot 4 update_on_skip (the 3DS's 5, 0x6C438): BehaviorImpl's, then the per-frame node / beam set-up again
    # (3 / 6: fu_node; 4: fu_node, fu_beam; 7: fu_beam, fu_node), without the timers or the growth
    G.asm("f_fu_skip:\nmflr r0\nbl pro\nmr r3, r31")
    far(orig(4))
    G.asm("""
        lwz r0, 4(r31)
        cmpwi r0, 3
        beq fsk_n
        cmpwi r0, 6
        beq fsk_n
        cmpwi r0, 4
        beq fsk_4
        cmpwi r0, 7
        bne.far epi
        bl fu_beam
    fsk_n:
        bl fu_node
        b epi
    fsk_4:
        bl fu_node
        bl fu_beam
        b epi
    """)
    code_ph(G, D, far, st, orig)
    return G


def code_ph(G, D, far, st, orig):
    """step 2g: Propeller Heiho (kind 0x47; enemy_fs.cro create 0x9AA38, state table 0x111278; docs/smash-run-port.md
    "Step 2g"), in region G after the other fliers. Its fields PH_* are the 3DS's +0x1DC..+0x20C: PH_D the vertical
    direction (+0x1DC), PH_B the aerial update's brake flag (+0x1E0), PH_Y a height reference (+0x1E4, written only),
    PH_F the fly-away frames (+0x1F0), PH_T the state timer (+0x1F4), PH_A the bob angle in degrees (int, +0x1F8),
    PH_R turned (+0x1FC), PH_S the item swap timer (+0x200), PH_DT the drop timer (+0x204), PH_I the held item's id
    (+0x208, 0x50000000 none), PH_X dropped (+0x20C). P0-32: its P0 row (P@0x00..0x80), then the literals PHK."""
    d = dict(AER=AER, AM=AER + 0xC, A10=AER + 0x10, A14=AER + 0x14, A18=AER + 0x18, A1C=AER + 0x1C, A20=AER + 0x20,
             A24=AER + 0x24, E0=AER + 4, E1=AER + 8, PD=PH_D, PB=PH_B, PY=PH_Y, PF=PH_F, PT=PH_T, PA=PH_A, PR=PH_R,
             PS=PH_S, PDT=PH_DT, PI=PH_I, PX=PH_X, PHm4=PH - 4, DEF=DEFEATED, MGRH=ha(ITEM_MGR), MGRL=sx(ITEM_MGR),
             FCH=ha(D['fconsts']), FCL=sx(D['fconsts']), SS=AER_SET_SPEED, UXY=AER_UPDATE_XY, SC=SET_CORRECT,
             SP=SET_PASSABLE, BUL=BULLET, CTOR=AER_CTOR, VT=IT_VT, RM=IT_REMOVE, ID=IT_ID, HAVE=IT_HAVE,
             FXH=PH_SWAP_FX >> 16, FXL=PH_SWAP_FX & 0xFFFF, FOOD=PH_FOOD, GOLD=PH_GOLDBAG, CUST=PH_CUSTOM,
             **{'P%d' % i: P(i) for i in range(33)}, **{k.upper(): P(i) for k, i in PHK.items()})

    def call(t):
        return "lis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctrl" % (t >> 16, t & 0xFFFF)

    d.update(FIND=call(FIND_ITEM), SUCC=call(SUCCESS_PCT), CREATE=call(CREATE_ITEM), FALL=call(ITEM_FALL),
             WARP=call(ITEM_WARP), NGP=call(NODE_GPOS), RAY=call(RAY_CHECK), VIEW=call(IN_VIEW), TPOS=call(GET_TARGET_POS),
             GSPD=call(GET_SPEED), COS=call(COSF), DTURN=call(DAMAGE_TURN), RHOMB=call(SET_RHOMBUS),
             BIDMG=call(BI_NOTIFY_DMG), REQ=call(REQ_EFFECT))
    a = lambda text: G.asm(text % d)  # noqa: E731
    # ---- helpers (r31 this, r30 CFG; own frames)
    # ph_find: r3 = ItemManager::find_item(PH_I) (0 for none / removed)
    a("""
    ph_find:
        lwz r4, 0x%(PI)X(r31)
        lis r3, 0x%(MGRH)04X
        lwz r3, %(MGRL)d(r3)
        lis r12, 0x%(FIH)04X
        ori r12, r12, 0x%(FIL)04X
        mtctr r12
        bctr
    """.replace('%(FIH)04X', '%04X' % (FIND_ITEM >> 16)).replace('%(FIL)04X', '%04X' % (FIND_ITEM & 0xFFFF)))
    # ph_anormal(f1-f6): EnemyAerialModuleImpl::set_mode_normal (3DS 0x5F5A9C; no Wii U copy): mode 0, energy 0's
    # init(0x17, &zero2, &zero3, acc), energy 0 on, energy 1 off, energy 0 +0x38 / +0x3C and the module +0x20 / +0x24
    # = (f5, f6) (the max speed), +0x10..+0x1C = f1..f4 (the update's accel x / y, brake x / y)
    a("""
    ph_anormal:
        mflr r0
        stwu r1, -0x40(r1)
        stw r0, 0x44(r1)
        stfs f1, 0x20(r1)
        stfs f2, 0x24(r1)
        stfs f3, 0x28(r1)
        stfs f4, 0x2C(r1)
        stfs f5, 0x30(r1)
        stfs f6, 0x34(r1)
        li r0, 0
        stw r0, 0x%(AM)X(r31)
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        lwz r3, 0x%(E0)X(r31)
        lwz r12, 0x1C(r3)
        lwz r12, 0x1C(r12)
        mtctr r12
        li r4, 0x17
        addi r5, r1, 8
        addi r6, r1, 0x10
        lwz r7, 0x%(AER)X(r31)
        bctrl
        li r0, 1
        lwz r12, 0x%(E0)X(r31)
        stb r0, 0x18(r12)
        li r0, 0
        lwz r11, 0x%(E1)X(r31)
        stb r0, 0x18(r11)
        lfs f5, 0x30(r1)
        lfs f6, 0x34(r1)
        stfs f5, 0x38(r12)
        stfs f6, 0x3C(r12)
        stfs f5, 0x%(A20)X(r31)
        stfs f6, 0x%(A24)X(r31)
        lfs f1, 0x20(r1)
        stfs f1, 0x%(A10)X(r31)
        lfs f1, 0x24(r1)
        stfs f1, 0x%(A14)X(r31)
        lfs f1, 0x28(r1)
        stfs f1, 0x%(A18)X(r31)
        lfs f1, 0x2C(r1)
        stfs f1, 0x%(A1C)X(r31)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr
    # ph_maxspd(f1, f2): set_max_speed (3DS 0x5F58A0): the module +0x20 / +0x24; in mode 0 / 1 also energy 0's
    ph_maxspd:
        stfs f1, 0x%(A20)X(r31)
        stfs f2, 0x%(A24)X(r31)
        lwz r0, 0x%(AM)X(r31)
        cmplwi r0, 1
        bgt ms_out
        lwz r12, 0x%(E0)X(r31)
        stfs f1, 0x38(r12)
        stfs f2, 0x3C(r12)
    ms_out:
        blr
    # ph_setspd(f1, f2): set_current_speed(x, y) (3DS 0x5F5C7C -> the Vector2 setter, Wii U 0x02DB2BC0)
    ph_setspd:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        stfs f1, 8(r1)
        stfs f2, 0xC(r1)
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 8
        bl 0x%(SS)08X
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    # ph_upd(f1, f2, r4): EnemyAerialModuleImpl::update(x, y, brake) (3DS 0x5F66AC = Wii U 0x02DB2524)
    ph_upd:
        addi r3, r31, 0x%(AER)X
        b 0x%(UXY)08X
    # ph_i2f(r3) -> f1, ph_f2i(f1) -> r3 (truncating, as vcvt.s32.f32)
    ph_i2f:
        stwu r1, -0x20(r1)
        xoris r3, r3, 0x8000
        stw r3, 0xC(r1)
        lis r0, 0x4330
        stw r0, 8(r1)
        lfd f1, 8(r1)
        lis r12, 0x%(FCH)04X
        lfd f0, %(FCL)d(r12)
        fsub f1, f1, f0
        frsp f1, f1
        addi r1, r1, 0x20
        blr
    ph_f2i:
        stwu r1, -0x20(r1)
        fctiwz f1, f1
        stfd f1, 8(r1)
        lwz r3, 0xC(r1)
        addi r1, r1, 0x20
        blr
    # ph_hgt(r7 bool) -> f1: Behavior::get_height_from_ground(posture, 50, bool) (3DS 0x7B4C68: GroundModule
    # ray_check(pos, (0 x 50, -1 x 50), out, bool); hit -> pos y - out y, else 50)
    ph_hgt:
        mflr r0
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x10(r12)
        stfs f1, 8(r1)
        lfs f1, 0x14(r12)
        stfs f1, 0xC(r1)
        stfs f1, 0x20(r1)
        lfs f2, 0x%(C50)X(r30)
        lfs f0, 0x%(C0)X(r30)
        fmuls f3, f0, f2
        stfs f3, 0x10(r1)
        lfs f0, 0x%(CM1)X(r30)
        fmuls f3, f0, f2
        stfs f3, 0x14(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        addi r4, r1, 8
        addi r5, r1, 0x10
        addi r6, r1, 0x18
        %(RAY)s
        lfs f1, 0x%(C50)X(r30)
        cmpwi r3, 0
        beq hg_out
        lfs f1, 0x20(r1)
        lfs f0, 0x1C(r1)
        fsubs f1, f1, f0
    hg_out:
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    # ph_lrcmp: f1 = get_lr_to_nearest_target(posture lr) (3DS 0x9EB178: the nearest fighter's x vs the posture's:
    # 1 / -1, else the given lr), then cr0 = f1 ? posture lr
    ph_lrcmp:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        bl h_near
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x60(r12)
        cmpwi r3, 0
        blt lr_cmp
        mr r5, r3
        addi r3, r1, 8
        mr r4, r31
        %(TPOS)s
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f2, 0x10(r12)
        lfs f3, 8(r1)
        lfs f1, 0x%(C1)X(r30)
        fcmpu cr0, f2, f3
        blt lr_cmp
        lfs f1, 0x%(CM1)X(r30)
        bgt lr_cmp
        lfs f1, 0x60(r12)
    lr_cmp:
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x60(r12)
        fcmpu cr0, f1, f0
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    # ph_hpos(r5 out): where the item hangs (3DS slot 59 0x9A224): node 3 (HipN)'s global position (ModelModule
    # node_global_position(3, &v, 1)) + (0, P7 -10, 0), z = 0
    ph_hpos:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        stw r5, 0x1C(r1)
        li r0, 0
        stw r0, 0(r5)
        stw r0, 4(r5)
        stw r0, 8(r5)
        lwz r3, 0(r31)
        lwz r3, 0x3118(r3)
        li r4, 3
        li r6, 1
        %(NGP)s
        lwz r5, 0x1C(r1)
        lfs f0, 0x%(C0)X(r30)
        lfs f1, 0(r5)
        fadds f1, f1, f0
        stfs f1, 0(r5)
        lfs f1, 4(r5)
        lfs f2, 0x%(P7)X(r30)
        fadds f1, f1, f2
        stfs f1, 4(r5)
        stfs f0, 8(r5)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    # ph_drop: the held item falls (3DS slots 11 / 55: Item::fall(tabemono ? 0 : 1, ZERO)); none held, dropped
    ph_drop:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        bl ph_find
        cmpwi r3, 0
        beq dr_none
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lfs f1, 0x%(C0)X(r30)
        lwz r0, 4(r3)
        cmpwi r0, 0x%(FOOD)X
        beq dr_go
        lfs f1, 0x%(C1)X(r30)
    dr_go:
        addi r4, r1, 8
        %(FALL)s
    dr_none:
        lis r0, 0x5000
        stw r0, 0x%(PI)X(r31)
        li r0, 1
        stw r0, 0x%(PX)X(r31)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    # ph_pick (3DS 0x5A6F0): a held item is removed (Item vt slot 81 remove(0)); then success_by_percent(P9 10):
    # customizeitem 0x21, else (P10 20) goldbag 0x1D, else tabemono 0x0E variation random(0, 28); created and held:
    # Behavior::create_item(kind, var, posture, zero, 1) and the item's have(0x50000000, 0, -1, 0, 0) (slot 95) =
    # the 3DS's create_item_and_have 0x7B4104; PH_I = its id (slot 83), or none
    ph_pick:
        mflr r0
        stwu r1, -0x30(r1)
        stw r0, 0x34(r1)
        stw r28, 0x28(r1)
        lwz r0, 0x%(PI)X(r31)
        lis r12, 0x5000
        cmplw r0, r12
        beq pk_new
        bl ph_find
        cmpwi r3, 0
        beq pk_none
        lwz r12, 0x%(VT)X(r3)
        lwz r12, 0x%(RM)X(r12)
        mtctr r12
        li r4, 0
        bctrl
    pk_none:
        lis r0, 0x5000
        stw r0, 0x%(PI)X(r31)
    pk_new:
        lfs f1, 0x%(P9)X(r30)
        %(SUCC)s
        li r4, 0x%(CUST)X
        li r5, 0
        cmpwi r3, 0
        bne pk_make
        lfs f1, 0x%(P10)X(r30)
        %(SUCC)s
        li r4, 0x%(GOLD)X
        li r5, 0
        cmpwi r3, 0
        bne pk_make
        li r3, 0
        li r4, 28
        bl h_rand
        andi. r5, r3, 0x1FFF
        li r4, 0x%(FOOD)X
    pk_make:
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lwz r6, 0(r31)
        lwz r6, 0x311C(r6)
        addi r6, r6, 0x10
        addi r7, r1, 8
        li r8, 1
        mr r3, r31
        %(CREATE)s
        lis r0, 0x5000
        mr r28, r3
        cmpwi r28, 0
        beq pk_store
        lwz r12, 0x%(VT)X(r28)
        lwz r12, 0x%(HAVE)X(r12)
        mtctr r12
        mr r3, r28
        lis r4, 0x5000
        li r5, 0
        li r6, -1
        li r7, 0
        li r8, 0
        bctrl
        mr r3, r28
        lwz r12, 0x%(VT)X(r3)
        lwz r12, 0x%(ID)X(r12)
        mtctr r12
        bctrl
        mr r0, r3
    pk_store:
        stw r0, 0x%(PI)X(r31)
        lwz r28, 0x28(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    """)
    # ---- start 0x99010: the aerial module, set_rhombus, the fields (the ctor's: PH_I none), +0x10 = posture lr,
    # +0x14 / +0x18 = 0, turned to the nearest fighter (check_turn_to_target -> reverse_lr(1, 1)), the item picked,
    # PH_S = P8 60, PH_DT = P26 100, -> 4. Not ported: set_frame_material / set_rate_material(0) (the prop's material
    # animation stopped), play_se(0x6D20000) (the propeller loop, counted per kind)
    a("""
    f_ph_start:
        mflr r0
        bl pro
        addi r3, r31, 0x%(AER)X
        lwz r4, 0(r31)
        bl 0x%(CTOR)08X
        mr r3, r31
        %(RHOMB)s
        li r0, 0
        li r12, 11
        mtctr r12
        addi r12, r31, 0x%(PHm4)X
    ps_z:
        stwu r0, 4(r12)
        bdnz ps_z
        lis r0, 0x5000
        stw r0, 0x%(PI)X(r31)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x60(r12)
        stw r0, 0x10(r31)
        li r0, 0
        stw r0, 0x14(r31)
        stw r0, 0x18(r31)
        bl h_near
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        beq ps_t
        bl h_rev
    ps_t:
        bl ph_pick
        lwz r0, 0x%(P8)X(r30)
        stw r0, 0x%(PS)X(r31)
        lwz r0, 0x%(P26)X(r30)
        stw r0, 0x%(PDT)X(r31)
        li r4, 4
        b go
    """)
    # slot 59 (0x9A224, every frame): the held item warped to ph_hpos (Item::warp)
    a("""
    f_ph_59:
        mflr r0
        bl pro
        lwz r0, 0x%(PX)X(r31)
        cmpwi r0, 0
        bne.far epi
        bl ph_find
        mr r28, r3
        cmpwi r28, 0
        beq.far epi
        addi r5, r1, 8
        bl ph_hpos
        mr r3, r28
        addi r4, r1, 8
        %(WARP)s
        b epi
    """)
    # slot 55 (0x99E24, after the state's update): in states 4 / 5 with the item still held: PH_S counts down; at 0
    # a new item (ph_pick), PH_S = P8 60, the swap effect 0x100001C at the item ((-5, 5, 0), tabemono (0, 5, 5));
    # else PH_DT counts down; at 0 success_by_percent(P25 10) drops it (ph_drop; not in 5: -> 5, in 5: PH_T = P32
    # 60), or PH_DT = P24 180. Not ported: the body's tilt (posture rot z toward -vx / P15 x P20 in 5, else 0, 1
    # degree a frame; the posture rotation is not mapped) and play_se(0x6D20001) at the swap
    a("""
    f_ph_55:
        mflr r0
        bl pro
        lwz r0, 4(r31)
        cmpwi r0, 5
        beq p55_a
        cmpwi r0, 4
        bne.far epi
    p55_a:
        lwz r0, 0x%(PX)X(r31)
        cmpwi r0, 0
        bne.far epi
        lwz r3, 0x%(PS)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(PS)X(r31)
        cmpwi r3, 0
        bgt p55_drop
        bl ph_pick
        lwz r0, 0x%(P8)X(r30)
        stw r0, 0x%(PS)X(r31)
        bl ph_find
        mr r28, r3
        cmpwi r28, 0
        beq.far epi
        addi r5, r1, 8
        bl ph_hpos
        lfs f2, 0x%(CM5)X(r30)
        lfs f3, 0x%(C5)X(r30)
        lfs f4, 0x%(C0)X(r30)
        lwz r0, 4(r28)
        cmpwi r0, 0x%(FOOD)X
        bne p55_o
        fmr f2, f4
        fmr f4, f3
    p55_o:
        lfs f1, 8(r1)
        fadds f1, f1, f2
        stfs f1, 8(r1)
        lfs f1, 0xC(r1)
        fadds f1, f1, f3
        stfs f1, 0xC(r1)
        lfs f1, 0x10(r1)
        fadds f1, f1, f4
        stfs f1, 0x10(r1)
        li r0, 0
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        stw r0, 0x1C(r1)
        mr r3, r31
        lis r4, 0x%(FXH)04X
        ori r4, r4, 0x%(FXL)04X
        addi r5, r1, 8
        addi r6, r1, 0x14
        lfs f1, 0x%(C1)X(r30)
        %(REQ)s
        b epi
    p55_drop:
        lwz r3, 0x%(PDT)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(PDT)X(r31)
        cmpwi r3, 0
        bgt.far epi
        lfs f1, 0x%(P25)X(r30)
        %(SUCC)s
        cmpwi r3, 0
        beq p55_fail
        bl ph_drop
        lwz r0, 4(r31)
        cmpwi r0, 5
        beq p55_in5
        li r4, 5
        b go
    p55_in5:
        lwz r0, 0x%(P32)X(r30)
        stw r0, 0x%(PT)X(r31)
        b epi
    p55_fail:
        lwz r0, 0x%(P24)X(r30)
        stw r0, 0x%(PDT)X(r31)
        b epi
    """)
    # slot 10 notify_on_damage (the 3DS's 11, 0x9A330): BehaviorImpl's, then a held item falls (ph_drop)
    a("""
    f_ph_dmg:
        mflr r0
        bl pro
        mr r3, r31
        %(BIDMG)s
        lwz r0, 0x%(PX)X(r31)
        cmpwi r0, 0
        bne.far epi
        lwz r0, 0x%(PI)X(r31)
        lis r12, 0x5000
        cmplw r0, r12
        beq.far epi
        bl ph_drop
        b epi
    """)
    # slot 69 (0x9AA1C): => 7 (stun), returns 1 (the framework's damage reaction skipped)
    st('f_ph_69', "li r4, 7\nbl h_chgi\nli r3, 1")
    # slot 27 notify_on_remove (the 3DS's dtors 0x9AC10 / 0x9AC74 remove a held item: vt slot 81 remove(0)), then
    # BehaviorImpl's (r4 kept)
    a("""
    f_ph_rm:
        mflr r0
        bl pro
        bl ph_find
        cmpwi r3, 0
        beq pr_go
        lwz r12, 0x%(VT)X(r3)
        lwz r12, 0x%(RM)X(r12)
        mtctr r12
        li r4, 0
        bctrl
    pr_go:
        lis r0, 0x5000
        stw r0, 0x%(PI)X(r31)
        mr r3, r31
        mr r4, r29
        lmw r28, 0x20(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        lis r12, 0x%(O27H)04X
        ori r12, r12, 0x%(O27L)04X
        mtctr r12
        bctr
    """.replace('%(O27H)04X', '%04X' % (orig(27) >> 16)).replace('%(O27L)04X', '%04X' % (orig(27) & 0xFFFF)))
    zero6 = "lfs f1, 0x%(C0)X(r30)\nfmr f2, f1\nfmr f3, f1\nfmr f4, f1\nlfs f5, 0x%(C10)X(r30)\nfmr f6, f5\nbl ph_anormal"
    tpos = "mr r5, r3\naddi r3, r1, 8\nmr r4, r31\n%(TPOS)s"
    # 1 turn (0x99598 / 0x99D64): set_mode_normal(0, 0, 0.1, 0.1, 10, 10), ground off, passable, TurnAir once; at
    # its end reverse_lr(1, 1), PH_R = 1, => 4; else the aerial update(0, 0, 0)
    st('ph1_en', ("""
        lfs f1, 0x%(C0)X(r30)
        fmr f2, f1
        lfs f3, 0x%(C01)X(r30)
        fmr f4, f3
        lfs f5, 0x%(C10)X(r30)
        fmr f6, f5
        bl ph_anormal
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 2
        li r5, 0
        bl h_mot1""") % d)
    st('ph1_up', ("""
        bl h_end
        cmpwi r3, 0
        beq p1_u
        bl h_rev
        li r0, 1
        stw r0, 0x%(PR)X(r31)
        li r4, 4
        b goi
    p1_u:
        lfs f1, 0x%(C0)X(r30)
        fmr f2, f1
        li r4, 0
        bl ph_upd""") % d)
    # 2 fly away (0x99440 / 0x99CC4): set_mode_normal(0, P28 0.05, 0, 0, 10, 10), set_max_speed(0, P29 4), PH_D = 1,
    # PH_B = 0, speed (0, P27 0), ground off, passable, set_correct(0), Vertical loop at P31 2, PH_F = P30 300; each
    # frame while PH_F > 0 and is_in_view_area: update(0, PH_D, PH_B); else => 8 (removed: a held item goes with it)
    st('ph2_en', ("""
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(P28)X(r30)
        fmr f3, f1
        fmr f4, f1
        lfs f5, 0x%(C10)X(r30)
        fmr f6, f5
        bl ph_anormal
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(P29)X(r30)
        bl ph_maxspd
        lfs f0, 0x%(C1)X(r30)
        stfs f0, 0x%(PD)X(r31)
        li r0, 0
        stw r0, 0x%(PB)X(r31)
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(P27)X(r30)
        lfs f0, 0x%(C1)X(r30)
        fmuls f2, f2, f0
        bl ph_setspd
        li r4, 0
        bl h_att
        bl f_pass1
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0
        bl 0x%(SC)08X
        lfs f2, 0x%(P31)X(r30)
        li r4, 3
        li r5, 1
        bl h_mot
        lwz r0, 0x%(P30)X(r30)
        stw r0, 0x%(PF)X(r31)""") % d)
    st('ph2_up', ("""
        lwz r3, 0x%(PF)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(PF)X(r31)
        cmpwi r3, 0
        ble p2_out
        mr r3, r31
        %(VIEW)s
        cmpwi r3, 0
        beq p2_out
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(PD)X(r30)
        lwz r4, 0x%(PB)X(r31)
        bl ph_upd
        b epi
    p2_out:
        li r4, 8
        b go""").replace('0x%(PD)X(r30)', '0x%(PD)X(r31)') % d)
    # 3 dead (0x99624 / 0x9A2F8): kinetic 23, ground off, passable off, bullet() (P2 entry 0), defeated; the kinetic
    # flag 8 -> 8
    st('ph3_en', ("""
        li r0, 1
        stw r0, 0x%(DEF)X(r31)
        li r4, 23
        bl h_kin
        li r4, 0
        bl h_att
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0
        bl 0x%(SP)08X
        mr r3, r31
        bl 0x%(BUL)08X""") % d)
    st('ph3_up', "li r4, 8\nbl h_flag\nbeq.far epi\nli r4, 8\nb go")
    # 4 height (0x9A578 / 0x9A6F8): set_mode_normal(0, 0, 0, 0, 10, 10), PH_B = 0, ground off, passable, Vertical
    # loop, PH_T = P13 120, PH_D = the nearest fighter's side in y (-1 below / 1), |dy| < P14 3 => 5, speed (0, P12 1
    # x PH_D). Update: going down, low = height_from_ground(1) < 5 - P7 (15); PH_T counts down; at 0, on the ground,
    # low or a ceiling: PH_D = -1 (ceiling), 1 (ground / low), => 5 (PH_T > 0 or PH_R) or to the nearest's side (lr
    # differs => 1 turn, else 5); else at the target's height (within P14) the same choice; else update(0, PH_D, PH_B)
    st('ph4_en', (zero6 + """
        li r0, 0
        stw r0, 0x%(PB)X(r31)
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 3
        li r5, 1
        bl h_mot1
        lwz r0, 0x%(P13)X(r30)
        stw r0, 0x%(PT)X(r31)
        lfs f0, 0x%(C0)X(r30)
        stfs f0, 0x%(PD)X(r31)
        bl h_near
        cmpwi r3, 0
        blt p4e_s
        """ + tpos + """
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        lfs f2, 0xC(r1)
        lfs f0, 0x%(C1)X(r30)
        fcmpu cr0, f1, f2
        ble p4e_d
        lfs f0, 0x%(CM1)X(r30)
    p4e_d:
        stfs f0, 0x%(PD)X(r31)
        fsubs f3, f2, f1
        fabs f3, f3
        lfs f0, 0x%(P14)X(r30)
        fcmpu cr0, f3, f0
        bge p4e_s
        li r4, 5
        b go
    p4e_s:
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(P12)X(r30)
        lfs f0, 0x%(PD)X(r31)
        fmuls f2, f2, f0
        bl ph_setspd""") % d)
    st('ph4_up', ("""
        li r28, 0
        lfs f1, 0x%(PD)X(r31)
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f1, f0
        bge p4_a0
        li r7, 1
        bl ph_hgt
        lfs f0, 0x%(C5)X(r30)
        lfs f2, 0x%(P7)X(r30)
        fsubs f0, f0, f2
        fcmpu cr0, f0, f1
        ble p4_a0
        li r28, 1
    p4_a0:
        lwz r3, 0x%(PT)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(PT)X(r31)
        cmpwi r3, 0
        ble p4_b
        li r4, 8
        bl h_touch
        cmpwi r3, 0
        bne p4_b
        cmpwi r28, 0
        bne p4_b
        li r4, 1
        bl h_touch
        cmpwi r3, 0
        beq p4_a
    p4_b:
        li r4, 1
        bl h_touch
        cmpwi r3, 0
        beq p4_b1
        lfs f0, 0x%(CM1)X(r30)
        stfs f0, 0x%(PD)X(r31)
    p4_b1:
        li r4, 8
        bl h_touch
        or r3, r3, r28
        cmpwi r3, 0
        beq p4_b2
        lfs f0, 0x%(C1)X(r30)
        stfs f0, 0x%(PD)X(r31)
    p4_b2:
        lwz r0, 0x%(PT)X(r31)
        cmpwi r0, 0
        bgt p4_5
    p4_d:
        lwz r0, 0x%(PR)X(r31)
        cmpwi r0, 0
        bne p4_5
        bl ph_lrcmp
        beq p4_5
        li r4, 1
        b go
    p4_5:
        li r4, 5
        b go
    p4_a:
        bl h_near
        cmpwi r3, 0
        blt p4_c
        """ + tpos + """
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        lfs f2, 0xC(r1)
        lfs f4, 0x%(PD)X(r31)
        lfs f0, 0x%(C0)X(r30)
        lfs f5, 0x%(P14)X(r30)
        fcmpu cr0, f4, f0
        ble p4_a2
        fsubs f3, f2, f5
        fcmpu cr0, f1, f3
        bgt p4_d
    p4_a2:
        fcmpu cr0, f4, f0
        bge p4_c
        fadds f3, f2, f5
        fcmpu cr0, f1, f3
        blt p4_d
    p4_c:
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(PD)X(r31)
        lwz r4, 0x%(PB)X(r31)
        bl ph_upd""") % d)
    # 5 patrol (0x991D4 / 0x99848): set_mode_normal(0 x 4, 10, 10), PH_A = 0, PH_B = 1, PH_Y = y, ground off,
    # passable, Move loop at P23 0.5, PH_T = dropped ? P32 60 : random(P18 150, P19 450), PH_DT = P24 180. Update:
    # PH_T at 0: dropped => 2 (fly away); the nearest fighter more than P11 60 away in y => 4 (PH_R = 0); else PH_T =
    # random(150, 450) => 6 (brake). A wall => 1. Else the bob: PH_A += 360 / P17 (int, wrapped at 360), vy =
    # cos(PH_A) x P16 x (360 / P17) / 360; PH_D = the current vy's sign; (going down and below 15 above the ground
    # (height_from_ground(0)), or on the ground) and vy < 0: PH_A = 270, PH_D = 1, PH_Y = y - P16 / 2; else a
    # ceiling and vy > 0: PH_A = 90, PH_D = -1, PH_Y = y + P16 / 2; speed (P15 0.5 x move x, vy); PH_D = vy >= 0;
    # update(move x, PH_D, 0)
    st('ph5_en', (zero6 + """
        li r0, 0
        stw r0, 0x%(PA)X(r31)
        li r0, 1
        stw r0, 0x%(PB)X(r31)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x14(r12)
        stw r0, 0x%(PY)X(r31)
        li r4, 0
        bl h_att
        bl f_pass1
        lfs f2, 0x%(P23)X(r30)
        li r4, 1
        li r5, 1
        bl h_mot
        lwz r0, 0x%(PX)X(r31)
        cmpwi r0, 0
        lwz r3, 0x%(P32)X(r30)
        bne p5e_t
        lwz r3, 0x%(P18)X(r30)
        lwz r4, 0x%(P19)X(r30)
        bl h_rand
    p5e_t:
        stw r3, 0x%(PT)X(r31)
        lwz r0, 0x%(P24)X(r30)
        stw r0, 0x%(PDT)X(r31)""") % d)
    st('ph5_up', ("""
        lwz r3, 0x%(PT)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(PT)X(r31)
        cmpwi r3, 0
        bgt p5_go
        lwz r0, 0x%(PX)X(r31)
        cmpwi r0, 0
        beq p5_n
        li r4, 2
        b go
    p5_n:
        bl h_near
        cmpwi r3, 0
        blt p5_r
        """ + tpos + """
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        lfs f2, 0xC(r1)
        fsubs f3, f2, f1
        fabs f3, f3
        lfs f0, 0x%(P11)X(r30)
        fcmpu cr0, f3, f0
        ble p5_r
        li r4, 4
        bl h_chg
        li r0, 0
        stw r0, 0x%(PR)X(r31)
        b epi
    p5_r:
        lwz r3, 0x%(P18)X(r30)
        lwz r4, 0x%(P19)X(r30)
        bl h_rand
        stw r3, 0x%(PT)X(r31)
        li r4, 6
        b go
    p5_go:
        bl h_wall
        cmpwi r3, 0
        beq p5_w
        li r4, 1
        b go
    p5_w:
        lwz r3, 0x%(PA)X(r31)
        bl ph_i2f
        lfs f0, 0x%(C360)X(r30)
        lfs f2, 0x%(P17)X(r30)
        fdivs f2, f0, f2
        stfs f2, 0x18(r1)
        fadds f1, f1, f2
        bl ph_f2i
        stw r3, 0x%(PA)X(r31)
        cmpwi r3, 360
        blt p5_ang
        bl ph_i2f
        lfs f0, 0x%(C360)X(r30)
        fsubs f1, f1, f0
        bl ph_f2i
        stw r3, 0x%(PA)X(r31)
    p5_ang:
        li r4, 8
        bl h_touch
        mr r28, r3
        li r4, 1
        bl h_touch
        stw r3, 0x14(r1)
        lwz r3, 0x%(PA)X(r31)
        bl ph_i2f
        lfs f0, 0x%(DEG)X(r30)
        fmuls f1, f1, f0
        %(COS)s
        lfs f2, 0x%(P16)X(r30)
        lfs f0, 0x18(r1)
        fmuls f2, f2, f0
        lfs f0, 0x%(I360)X(r30)
        fmuls f2, f2, f0
        fmuls f1, f1, f2
        stfs f1, 0x1C(r1)
        lwz r12, 0x%(E0)X(r31)
        lfs f1, 4(r12)
        lfs f0, 0x%(C0)X(r30)
        lfs f2, 0x%(C1)X(r30)
        fcmpu cr0, f1, f0
        bge p5_dr
        lfs f2, 0x%(CM1)X(r30)
    p5_dr:
        stfs f2, 0x%(PD)X(r31)
        lwz r0, 0x%(PX)X(r31)
        cmpwi r0, 0
        bne p5_g
        lfs f1, 0x%(PD)X(r31)
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f1, f0
        bge p5_g
        li r7, 0
        bl ph_hgt
        lfs f0, 0x%(C5)X(r30)
        lfs f2, 0x%(P7)X(r30)
        fsubs f0, f0, f2
        fcmpu cr0, f0, f1
        bgt p5_l
    p5_g:
        cmpwi r28, 0
        beq p5_m
    p5_l:
        lfs f1, 0x1C(r1)
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f0, f1
        ble p5_m
        li r0, 270
        stw r0, 0x%(PA)X(r31)
        lfs f0, 0x%(C1)X(r30)
        stfs f0, 0x%(PD)X(r31)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        lfs f2, 0x%(P16)X(r30)
        lfs f3, 0x%(HALF)X(r30)
        fmuls f2, f2, f3
        fsubs f1, f1, f2
        b p5_y
    p5_m:
        lwz r0, 0x14(r1)
        cmpwi r0, 0
        beq p5_n2
        lfs f1, 0x1C(r1)
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f1, f0
        ble p5_n2
        li r0, 90
        stw r0, 0x%(PA)X(r31)
        lfs f0, 0x%(CM1)X(r30)
        stfs f0, 0x%(PD)X(r31)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x14(r12)
        lfs f2, 0x%(P16)X(r30)
        lfs f3, 0x%(HALF)X(r30)
        fmuls f2, f2, f3
        fadds f1, f1, f2
    p5_y:
        stfs f1, 0x%(PY)X(r31)
    p5_n2:
        lfs f1, 0x%(P15)X(r30)
        lfs f0, 0x10(r31)
        fmuls f1, f1, f0
        lfs f2, 0x1C(r1)
        bl ph_setspd
        lfs f0, 0x1C(r1)
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(C1)X(r30)
        fcmpu cr0, f0, f1
        bge p5_pd
        fmr f2, f1
    p5_pd:
        stfs f2, 0x%(PD)X(r31)
        lfs f1, 0x10(r31)
        li r4, 0
        bl ph_upd""") % d)
    # 6 brake (0x9934C / 0x99BD0): v = the current speed, set_mode_normal(0, 0, P21 0.05 x |vx| / max(|vy|, 0.1),
    # P21, 10, 10), speed v, PH_B = 1, ground off, passable, Move loop. Update: |v|^2 < 0.01: success_by_percent(P22
    # 100) => 2 (fly away); else the nearest's side differs => 1, else => 4 (PH_R = 0); moving: update(move x, PH_D,
    # PH_B)
    st('ph6_en', ("""
        addi r3, r1, 8
        mr r4, r31
        %(GSPD)s
        lfs f1, 8(r1)
        fabs f1, f1
        lfs f2, 0xC(r1)
        fabs f2, f2
        lfs f0, 0x%(C01)X(r30)
        fcmpu cr0, f2, f0
        bge p6_a
        fmr f2, f0
    p6_a:
        lfs f4, 0x%(P21)X(r30)
        fmuls f3, f4, f1
        fdivs f3, f3, f2
        lfs f1, 0x%(C0)X(r30)
        fmr f2, f1
        lfs f5, 0x%(C10)X(r30)
        fmr f6, f5
        bl ph_anormal
        lfs f1, 8(r1)
        lfs f2, 0xC(r1)
        bl ph_setspd
        li r0, 1
        stw r0, 0x%(PB)X(r31)
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 1
        li r5, 1
        bl h_mot1""") % d)
    st('ph6_up', ("""
        addi r3, r1, 8
        mr r4, r31
        %(GSPD)s
        lfs f1, 8(r1)
        fmuls f0, f1, f1
        lfs f1, 0xC(r1)
        fmuls f1, f1, f1
        fadds f0, f0, f1
        lfs f1, 0x10(r1)
        fmuls f1, f1, f1
        fadds f0, f0, f1
        lfs f1, 0x%(STOP)X(r30)
        fcmpu cr0, f0, f1
        bge p6_mv
        lfs f1, 0x%(P22)X(r30)
        %(SUCC)s
        cmpwi r3, 0
        beq p6_lr
        li r4, 2
        b go
    p6_lr:
        bl ph_lrcmp
        beq p6_4
        li r4, 1
        b go
    p6_4:
        li r4, 4
        bl h_chg
        li r0, 0
        stw r0, 0x%(PR)X(r31)
        b epi
    p6_mv:
        lfs f1, 0x10(r31)
        lfs f2, 0x%(PD)X(r31)
        lwz r4, 0x%(PB)X(r31)
        bl ph_upd""") % d)
    # 7 stun (0x99148 / 0x99674): Damage once, kinetic 16, ground off, damage_turn(), PH_T = hit_return_frame(), the
    # kinetic flag 0x80; update: on the ground clear_speed_all; PH_T below 0: flag 0x80 off, => 4; else move(ai).
    # Not ported: the posture's z rotation back to 0 (5 degrees a frame)
    st('ph7_en', ("""
        li r4, 0
        li r5, 0
        bl h_mot1
        li r4, 16
        bl h_kin
        li r4, 0
        bl h_att
        mr r3, r31
        %(DTURN)s
        bl f_hitret
        stw r3, 0x%(PT)X(r31)
        bl f_kflag
        lwz r0, 0(r12)
        ori r0, r0, 0x80
        stw r0, 0(r12)""") % d)
    st('ph7_up', ("""
        bl h_gnd
        cmpwi r3, 0
        beq p7_a
        bl h_clear
    p7_a:
        lwz r3, 0x%(PT)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(PT)X(r31)
        cmpwi r3, 0
        bge p7_mv
        bl f_kflag
        lwz r0, 0(r12)
        rlwinm r0, r0, 0, 25, 23
        stw r0, 0(r12)
        li r4, 4
        b goi
    p7_mv:
        bl h_mv""") % d)


def assemble(vt_words):
    """(A, B, Data): the code in regions A, B and E (A.area / A.stomp / A.e: the units of C, D, E), the data after
    it (passes until the data's addresses settle: the code's size does not depend on them)"""
    d = Data(vt_words)
    VT_WORDS[0] = vt_words
    D = {}
    keys = [lab for lab, _w, _a in Data(vt_words).build({}).blocks]
    for _pass in range(4):
        dd = {k: D.get(k, CAVE) for k in keys}
        A, B, Ee, Gg = code(dd)
        Hh = code_h(dd)
        C = area_code(dd)
        Dd = stomp_code()
        labels = dict(A.labels)
        for a in (B, C, Dd, Ee, Gg, Hh):
            labels.update(a.labels)
        for a in (A, B, C, Dd, Ee, Gg, Hh):
            a.labels.update(labels)
        ea, eb, ec, ed, ee, eg, eh = A.pc, B.pc, C.pc, Dd.pc, Ee.pc, Gg.pc, Hh.pc
        assert eg <= LIMIT_G, 'flier code too big (0x%X)' % eg
        assert eh <= LIMIT_H, 'step 2h code too big (0x%X)' % eh
        assert ed <= LIMIT_D, 'stomp code too big (0x%X)' % ed
        assert ea <= LIMIT and eb <= LIMIT_B and ee <= LIMIT_E, 'walker code too big (0x%X, 0x%X, 0x%X)' % (ea, eb, ee)
        spans = [((ea + 0xF) & ~0xF, LIMIT), ((eb + 0xF) & ~0xF, LIMIT_B), ((ec + 0xF) & ~0xF, LIMIT_C),
                 ((ed + 3) & ~3, LIMIT_D), ((ee + 0xF) & ~0xF, LIMIT_E), ((eg + 0xF) & ~0xF, LIMIT_G),
                 ((eh + 0xF) & ~0xF, LIMIT_H)] + list(DATA_F)
        d.build(labels, D)
        d.place(spans)
        if d.addr == D:
            break
        D = dict(d.addr)
    d.build(labels, D)
    d.place(spans)
    assert d.addr == D
    A.area = C
    A.stomp = Dd
    A.e = Ee
    A.g = Gg
    A.h = Hh
    return A, B, d


def stomp_code():
    """fix v8: slot 3 (update) -> w_upd: for a kind with a TREAD state, not in it nor dying / removed, each live
    fighter (slots 0-3) whose feet (posture y) went from at / above the tread box's top last frame to at / below it
    now, not below its bottom, within its half width -> change_state_interrupt(TREAD) and the fighter's
    StatusModule(3, STEP_JUMP, 0) (MSC's change status, as position_vars_cave.py does it); then BehaviorImpl's update"""
    Dd = Asm(CAVE_D)
    Dd.asm("""
    w_upd:
        stwu r1, -0x60(r1)
        mflr r0
        stw r0, 0x64(r1)
        stmw r24, 0x20(r1)
        stw r4, 0x40(r1)
        mr r31, r3
        bl u_pend
        lwz r30, 0x168(r31)
        lwz r29, 0x%(TREAD)X(r30)
        cmpwi r29, 0
        beq u_out
        lwz r0, 4(r31)
        cmpw r0, r29
        beq u_out
        lwz r12, 0x%(R67)X(r30)
        cmpw r0, r12
        beq u_out
        lwz r12, 0x%(DF)X(r31)
        cmpwi r12, 0
        bne u_out
        lwz r12, 0(r31)
        lwz r28, 0x311C(r12)
        addi r27, r30, 0x%(TB)X
        lwz r4, 0x%(TN)X(r30)
        cmpwi r4, 0
        beq u_post
        lwz r3, 0x3118(r12)
        addi r5, r1, 0x50
        li r6, 1
        lis r12, 0x%(NGH)04X
        ori r12, r12, 0x%(NGL)04X
        mtctr r12
        bctrl
        addi r28, r1, 0x40
    u_post:
        lis r12, 0x%(FH)04X
        lwz r12, %(FL)d(r12)
        cmpwi r12, 0
        beq u_out
        lwz r26, 0(r12)
        cmpwi r26, 0
        beq u_out
        li r25, -1
    u_next:
        addi r25, r25, 1
        lwz r0, 8(r26)
        cmpw r25, r0
        bge u_out
        cmplwi r25, 4
        bge u_out
        b u_body
    u_out:
        mr r3, r31
        lwz r4, 0x40(r1)
        lmw r24, 0x20(r1)
        lwz r0, 0x64(r1)
        mtlr r0
        addi r1, r1, 0x60
        lis r12, 0x%(BH)04X
        ori r12, r12, 0x%(BL)04X
        mtctr r12
        bctr
    """ % dict(TREAD=CF['TREAD'], R67=CF['R67'], FH=ha(FIGHTERS), FL=sx(FIGHTERS), BH=BI_UPDATE >> 16,
               BL=BI_UPDATE & 0xFFFF, TB=CF['TB0'], DF=DEFEATED, TN=CF['TNODE'], NGH=NODE_GPOS >> 16,
               NGL=NODE_GPOS & 0xFFFF))
    return Dd


def stomp_body(C):
    """the per-fighter test (in region C, after the area hooks; r25 slot, r26 the fighter table, r27 tbox, r28 the
    enemy's posture, r29 its TREAD state, r31 this)"""
    C.asm("""
    u_body:
        lwz r12, 0(r26)
        mulli r11, r25, 0x%(ENT)X
        add r12, r12, r11
        lbz r11, 0x1E(r12)
        cmplwi r11, 4
        blt b_next
        lwz r24, 0xC(r12)
        lwz r11, 0x18(r24)
        lfs f1, 0x14(r11)
        lfs f3, 0x14(r28)
        lfs f4, 4(r27)
        fadds f3, f3, f4
        lfs f5, 8(r27)
        fadds f4, f3, f5
        fsubs f1, f1, f4
        slwi r10, r25, 2
        add r10, r10, r31
        lwz r0, 0x%(PREV)X(r10)
        lfs f2, 0x%(PREV)X(r10)
        stfs f1, 0x%(PREV)X(r10)
        cmpwi r0, 0
        beq b_next
        fsubs f0, f1, f1
        fcmpu cr0, f2, f0
        blt b_next
        fcmpu cr0, f1, f0
        bgt b_next
        fadds f6, f5, f5
        lis r0, 0x%(SWH)04X
        stw r0, 0x1C(r1)
        lfs f7, 0x1C(r1)
        fadds f6, f6, f7
        fneg f6, f6
        fcmpu cr0, f1, f6
        blt b_next
        lfs f6, 0x10(r11)
        lfs f7, 0x10(r28)
        fsubs f6, f6, f7
        fabs f6, f6
        lfs f7, 0(r27)
        fcmpu cr0, f6, f7
        bgt b_next
        mr r3, r31
        lwz r12, 0xE0(r3)
        lwz r12, 0x%(S20)X(r12)
        mtctr r12
        bctrl
        li r0, 3
        stw r0, 0x10(r1)
        stw r0, 0x4C(r1)
        li r0, 0x%(STEP)X
        stw r0, 0x14(r1)
        li r0, 0
        stw r0, 0x18(r1)
        stw r0, 8(r1)
        stw r24, 0xC(r1)
        addi r0, r1, 0x10
        stw r0, 0x48(r1)
        addi r3, r1, 8
        addi r4, r1, 0x48
        lis r12, 0x%(MH)04X
        ori r12, r12, 0x%(ML)04X
        mtctr r12
        bctrl
        bl u_bounce
        b u_out
    b_next:
        b u_next
    """ % dict(ENT=FIGHTER_ENTRY, PREV=PREV, S20=0xC + 8 * TREAD_SLOT, STEP=STEP_JUMP, MH=MSC_STATUS >> 16,
               ML=MSC_STATUS & 0xFFFF, SWH=struct.unpack('>I', struct.pack('>f', STOMP_SWEEP))[0] >> 16))


GET_DAMAGE = 0x02C22ECC              # DamageModule (acc+0x30D4) get_damage(r4 index) -> f1 (entries 0xE4 apart, +0)
SET_CUR_DAMAGE = 0x026A7E58          # Behavior::set_current_damage(f1) (3DS 0x7B3688): init_damage(f1), HP W+0 = W+4 - damage
STEP_JUMP_SPEED = 0x02E79938         # the fighters' StepJump speed (this, &out, accessor): y = step_jump_speed_y x float
#                                      0x1000006 (x pow(float 0x20000B5, int 0x10000006 - 1) past one step); 3DS 0x97E080
WM_SET_FLOAT, WM_SET_INT = 0x4C, 0x8C    # WorkModule vt: set_float(f1, r4 id), set_int(r4 value, r5 id)
STATUS_KIND = 0x48                   # StatusModule (MSC accessor +0x20) +0x48 the status kind (tools/edge_counter_cave.py)
F_TREAD_MUL, I_STEP_COUNT = 0x01000006, 0x10000006
# step 2p: the fighter's tread target (LA int 0x10000008: StepJump's func_1149 links 3 to it, LinkModule op 5 =
# vt+0x34(3, id), and copies that object's link event 6 answer into float 0x1000006). A stale id there (an object
# that does not answer event 6) zeroed the bounce; the stepped enemy's own id would run its tread slot a second
# time (event 6 -> 0x02DB98F4 -> slot 20). u_bounce writes the invalid id (category 5: 0x02BF205C finds no object),
# so the link fails, func_1149 is skipped and float 0x1000006 keeps u_bounce's multiplier.
I_TREAD_TARGET, BO_ID_INVALID = 0x10000008, 0x50000000
DISABLE_HIT, DISABLE_TREAD = 0x026A75C0, 0x026A75FC   # Behavior::disable_hit / disable_tread (3DS 0x7B0864 / 0x7B0D50)
CREATE_THROW = 0x026A8F10            # Behavior::create_item_and_throw(kind, var, &pos, &speed, f1, r8, r9, r10) (3DS 0x7B4488)
PEND_N = 40                          # the pending re-write lasts this many cave-enemy updates (seen-flag bit 16)


def code_pk(H, st, call, d, D):
    """step 2j: Pooka (pooka 0x20), every state and slot from its 3DS code (enemy_fs.cro addresses in the comments;
    docs/smash-run-port.md "Step 2j", hand_read.json pooka port_step2j). V0 the turn / balloon timer (+0x168), V1 the
    ghost-check / re-aim / drop frames (+0x16C), V2 the search / back-off / balloon hold / pop timer (+0x170), V3 the
    ghost's follow effect (+0x174), V4 the forced search (+0x178), V5 the hit object (+0x17C), V6 the inflate
    threshold (+0x180, float), V7 the balloon frame (+0x184, float), V8 inflating (+0x188); PK +0 deflating (+0x189),
    +4 shown, +8 hit. P0-35 its P0 row, P36.. PK_LIT"""
    p = dict(d, AER=AER, E0=AER + 4, DF=PK, VS=PK + 4, HT=PK + 8, MF=MOT_FRAME, FCH=ha(D['fconsts']),
             FCL=sx(D['fconsts']), C01=P(36), C100=P(37), C0_1=P(38), CM08=P(39), C10=P(40), C20=P(41), C2=P(42),
             R2D=P(43), D2R=P(44), C90=P(45), C180=P(46), C1=P(47), C0=P(48), CM1=P(49), POPEND=P(50), EPS=P(51),
             C3=P(52), C25=P(53), C05=P(54), SI=SEARCH >> 16)
    a = lambda text: H.asm(text % p)  # noqa: E731
    c = lambda name, t: p.__setitem__(name, call(t))  # noqa: E731
    for name, t in (('RAY', RAY_CHECK), ('CPOS', CENTER_POS), ('TPOS', GET_TARGET_POS), ('SQ', SQRTF),
                    ('ACOS', ACOSF), ('COS', COSF), ('SIN', SINF), ('SPD', GET_SPEED), ('GN', GROUND_NORMAL),
                    ('SCOR', SET_CORRECT), ('DHIT', DISABLE_HIT), ('EHIT', ENABLE_HIT), ('FOL', REQ_FOLLOW),
                    ('RMFX', REMOVE_EFFECT), ('NODEFX', REQ_NODE), ('SETF', SET_FRAME), ('ENDF', END_FRAME),
                    ('SETD', SET_CUR_DAMAGE), ('MOT', CHANGE_MOTION), ('ACLR', ATK_CLEAR), ('DEAD', CREATE_DEAD_ITEM),
                    ('QUAKE', REQ_QUAKE), ('CAPM', ZIMA_CAPTURE_MOTION), ('ASPD', AER_SET_SPEED),
                    ('ACTOR', AER_CTOR), ('RHOMB', SET_RHOMBUS), ('PASS', SET_PASSABLE)):
        c(name, t)

    def st2(label, body):
        """a state / slot body with a 0x60 frame (scratch 8..0x37) and f29-f31 kept"""
        H.asm("%s:\nmflr r0\nbl pk_pro\n%s\nb pk_epi" % (label, body % p))

    a("""
    pk_pro:
        stwu r1, -0x60(r1)
        stw r0, 0x64(r1)
        stmw r28, 0x50(r1)
        stfd f31, 0x48(r1)
        stfd f30, 0x40(r1)
        stfd f29, 0x38(r1)
        mr r31, r3
        lwz r30, 0x168(r3)
        mr r29, r4
        blr
    pk_go:
        bl h_chg
    pk_epi:
        lfd f31, 0x48(r1)
        lfd f30, 0x40(r1)
        lfd f29, 0x38(r1)
        lmw r28, 0x50(r1)
        lwz r0, 0x64(r1)
        mtlr r0
        addi r1, r1, 0x60
        blr
    pk_goi:
        bl h_chgi
        b pk_epi
    pk_w:
        lwz r12, 0(r31)
        lwz r12, 0x3130(r12)
        lwz r12, 8(r12)
        lwz r12, 0(r12)
        lwz r10, 4(r12)
        blr
    pk_thr:
        lwz r12, 0(r31)
        lwz r12, 0x3130(r12)
        lwz r12, 8(r12)
        lwz r12, 0(r12)
        lwz r12, 4(r12)
        lfs f2, 0(r12)
        lfs f1, 4(r12)
        lfs f0, 0x%(C01)X(r30)
        fmuls f1, f1, f0
        lfs f0, 0x%(P23)X(r30)
        fmuls f1, f1, f0
        blr
    pk_e0:
        lwz r10, 0x%(E0)X(r31)
        blr
    pk_mm:
        lwz r3, 0(r31)
        lwz r3, 0x30F0(r3)
        blr
    pk_dead:
        lwz r12, 0(r31)
        lwz r12, 0x3130(r12)
        lwz r12, 8(r12)
        lwz r12, 0(r12)
        lwz r12, 0x14(r12)
        lwz r3, 0(r12)
        andi. r3, r3, 2
        blr
    pk_grav:
        mflr r11
        bl f_gl
        lfs f0, 0x120(r3)
        bl pk_w
        stfs f0, 0x3C(r10)
        lfs f0, 0x%(C1)X(r30)
        stfs f0, 0x40(r10)
        mtlr r11
        blr
    pk_pass0:
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0
    """)
    # set_passable_check(0) as a far tail call (keeps the caller's frame)
    H.asm("lis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctr" % (SET_PASSABLE >> 16, SET_PASSABLE & 0xFFFF))
    # pk_endf: f1 = float(end_frame()) (uses 8..0x1F(r1) of the caller's frame); pk_setf: set_frame(f1, true);
    # pk_dmg: set_current_damage(f1)
    a("""
    pk_endf:
        mflr r0
        stw r0, 0x1C(r1)
        bl pk_mm
        %(ENDF)s
        xoris r3, r3, 0x8000
        stw r3, 0xC(r1)
        lis r0, 0x4330
        stw r0, 8(r1)
        lfd f1, 8(r1)
        lis r12, 0x%(FCH)04X
        lfd f0, %(FCL)d(r12)
        fsub f1, f1, f0
        frsp f1, f1
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    pk_setf:
        mflr r0
        stw r0, 0x1C(r1)
        bl pk_mm
        li r4, 1
        %(SETF)s
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    pk_dmg:
        mflr r0
        stw r0, 0x1C(r1)
        mr r3, r31
        %(SETD)s
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """)
    # L65084(r4 body damage, r5 eye damage, r6 shown): shown 0 -> every mesh off and set_visibility(0) (the ghost /
    # the pop: the follow / burst effect draws it); 1 -> set_visibility(1), body_normal_L (posture lr -1.0) or _R =
    # !damage, the other 0, body_damage = damage, eye_damage = r5, eye_normal = !r5, gogle and leg on
    a("""
    pk_mesh:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stmw r27, 0xC(r1)
        mr r27, r4
        mr r28, r5
        stw r6, 0x%(VS)X(r31)
        cmpwi r6, 0
        bne pkm_on
        mr r3, r31
        li r4, 0
        li r5, 0x7F
        bl h_vset
        mr r3, r31
        li r4, 0
        bl h_whole
        b pkm_out
    pkm_on:
        mr r3, r31
        li r4, 1
        bl h_whole
        xori r9, r27, 1
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x60(r12)
        lis r11, 0xBF80
        li r8, 1
        cmpw r0, r11
        beq pkm_l
        li r8, 2
    pkm_l:
        slw r9, r9, r8
        or r9, r9, r27
        slwi r10, r28, 3
        or r9, r9, r10
        xori r10, r28, 1
        slwi r10, r10, 4
        or r9, r9, r10
        ori r4, r9, 0x60
        mr r3, r31
        li r5, 0x7F
        bl h_vset
    pkm_out:
        lmw r27, 0xC(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    pk_mn:
        li r4, 0
        li r5, 0
        li r6, 1
        b pk_mesh
    pk_md:
        li r4, 0
        li r5, 1
        li r6, 1
        b pk_mesh
    pk_md_if:
        lwz r0, 0x%(VS)X(r31)
        cmpwi r0, 0
        bne pk_md
        blr
    """)
    # pk_mot(r4 motion, r5 loop, f1 frame, f2 rate): Behavior::change_motion_state
    a("""
    pk_mot:
        lfs f3, 0x%(C0)X(r30)
        mr r3, r31
        b 0x%(MOTA)08X
    """ % dict(p, MOTA=CHANGE_MOTION))
    # pk_ray(r4 from, r5 dir, r6 out, r7 bool) -> r3: GroundModule ray_check (3DS 0x9535F4: bool 1 every collision,
    # 0 with the mask 0x102000: the passable floors left out)
    a("""
    pk_ray:
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        lis r12, 0x%(RH)04X
        ori r12, r12, 0x%(RL)04X
        mtctr r12
        bctr
    pk_len:
        fmuls f1, f1, f1
        fmuls f2, f2, f2
        fadds f1, f1, f2
        lis r12, 0x%(SQH)04X
        ori r12, r12, 0x%(SQL)04X
        mtctr r12
        bctr
    """ % dict(RH=RAY_CHECK >> 16, RL=RAY_CHECK & 0xFFFF, SQH=SQRTF >> 16, SQL=SQRTF & 0xFFFF))

    # start (0x21064): set_rhombus, stick x = posture lr, face the nearest target (check_turn_to_target -> reverse_lr),
    # V6 = P23 % of the max HP; the nearest fighter: ray (posture -> it, mask) clear but the reverse ray (it -> posture)
    # blocked (spawned inside a wall) => 8 ghost; else => 1
    st2('pk_start', """
        addi r3, r31, 0x%(AER)X
        lwz r4, 0(r31)
        %(ACTOR)s
        mr r3, r31
        bl h_vdef
        mr r3, r31
        %(RHOMB)s
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x60(r12)
        stw r0, 0x10(r31)
        li r0, 0
        stw r0, 0x14(r31)
        stw r0, 0x18(r31)
        stw r0, 0x%(DF)X(r31)
        stw r0, 0x%(HT)X(r31)
        stw r0, 0x%(V8)X(r31)
        stw r0, 0x%(V7)X(r31)
        li r0, -1
        stw r0, 0x%(V5)X(r31)
        li r0, 1
        stw r0, 0x%(VS)X(r31)
        bl h_near
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        beq pks_t
        bl h_rev
    pks_t:
        bl pk_thr
        stfs f1, 0x%(V6)X(r31)
        bl h_near
        cmpwi r3, 0
        blt pks_1
        mr r5, r3
        addi r3, r1, 8
        mr r4, r31
        %(TPOS)s
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x10(r12)
        lfs f2, 0x14(r12)
        stfs f1, 0x20(r1)
        stfs f2, 0x24(r1)
        lfs f3, 8(r1)
        lfs f4, 0xC(r1)
        fsubs f3, f3, f1
        fsubs f4, f4, f2
        stfs f3, 0x18(r1)
        stfs f4, 0x1C(r1)
        fneg f3, f3
        fneg f4, f4
        stfs f3, 0x30(r1)
        stfs f4, 0x34(r1)
        addi r4, r1, 0x20
        addi r5, r1, 0x18
        addi r6, r1, 0x28
        li r7, 0
        bl pk_ray
        cmpwi r3, 0
        bne pks_1
        addi r4, r1, 8
        addi r5, r1, 0x30
        addi r6, r1, 0x28
        li r7, 0
        bl pk_ray
        cmpwi r3, 0
        beq pks_1
        li r4, 8
        b pk_goi
    pks_1:
        li r4, 1
        b pk_goi""")
    # 1 fall (0x2141C / 0x22368): kinetic 8, ground off, passable off, reset_gravity, Move at rate 0 (loop) unless
    # the balloon is playing (motion 2) with HP below V6, the normal meshes; on the ground -> 2
    st2('pk_fall_en', """
        li r4, 8
        bl h_kin
        li r4, 0
        bl h_att
        bl pk_pass0
        bl pk_grav
        lwz r12, 0(r31)
        lwz r12, 0x30F0(r12)
        lwz r0, 0x%(MK)X(r12)
        cmpwi r0, 2
        bne pkf_m
        bl pk_thr
        lfs f1, 0x%(V6)X(r31)
        fcmpu cr0, f2, f1
        blt pkf_v
    pkf_m:
        li r4, 11
        li r5, 1
        lfs f1, 0x%(C0)X(r30)
        fmr f2, f1
        bl pk_mot
    pkf_v:
        bl pk_mn""" .replace('%(MK)X', '%X' % MOT_KIND))
    st2('pk_fall_up', "bl h_gnd\ncmpwi r3, 0\nbeq pk_epi\nli r4, 2\nb pk_go")
    # 2 landing (0x214D0 / 0x223A8): kinetic 0, ground on, passable off, Landiing; at its end the nearest target
    # behind (check_turn_to_target) -> 4, else -> 3
    st2('pk_land_en', """
        li r4, 0
        bl h_kin
        li r4, 1
        bl h_att
        bl pk_pass0
        li r4, 10
        li r5, 0
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(C1)X(r30)
        bl pk_mot
        bl pk_mn""")
    st2('pk_land_up', """
        bl h_end
        cmpwi r3, 0
        beq pk_epi
        bl h_near
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        li r4, 3
        beq pk_go
        li r4, 4
        b pk_go""")
    # 3 walk (0x21678 / 0x22494): the row's W+0x10 / +0x08 / +0x14, kinetic 1, ground on, Move at P6 (loop), the
    # normal meshes, V0 = random(P4, P5), V1 = P7, V2 = search_interval(0)
    st2('pk_walk_en', """
        bl pk_w
        lwz r0, 0x%(P1)X(r30)
        stw r0, 0x10(r10)
        lwz r0, 0x%(P2)X(r30)
        stw r0, 8(r10)
        lwz r0, 0x%(P3)X(r30)
        stw r0, 0x14(r10)
        li r4, 1
        bl h_kin
        li r4, 1
        bl h_att
        li r4, 11
        li r5, 1
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(P6)X(r30)
        bl pk_mot
        bl pk_mn
        lwz r3, 0x%(P4)X(r30)
        lwz r4, 0x%(P5)X(r30)
        bl h_rand
        stw r3, 0x%(V0)X(r31)
        lwz r0, 0x%(P7)X(r30)
        stw r0, 0x%(V1)X(r31)
        li r4, 0
        bl h_grp
        stw r3, 0x%(V2)X(r31)""")
    # update: move; off the ground -> 1; a ledge -> 4; V1 out (or a wall) -> the ghost / drop check (pk_gchk: -> 8 /
    # 9), then V1 = P7; V2 out (or V4): search_target(0) found -> 5, else V2 = the interval, V4 = 0; V0 out: the
    # nearest target behind -> 4, else V0 = random(P4, P5); a wall -> 4
    st2('pk_walk_up', """
        bl h_mv
        bl h_gnd
        cmpwi r3, 0
        bne pkw_g
        li r4, 1
        b pk_go
    pkw_g:
        bl h_cliff
        cmpwi r3, 0
        bne pkw_4
        lwz r3, 0x%(V1)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V1)X(r31)
        cmpwi r3, 0
        ble pkw_gh
        bl h_wall
        cmpwi r3, 0
        beq pkw_s
    pkw_gh:
        bl pk_gchk
        cmpwi r3, 0
        mr r4, r3
        bne pk_go
        lwz r0, 0x%(P7)X(r30)
        stw r0, 0x%(V1)X(r31)
    pkw_s:
        lwz r3, 0x%(V2)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V2)X(r31)
        cmpwi r3, 0
        ble pkw_do
        lwz r0, 0x%(V4)X(r31)
        cmpwi r0, 0
        beq pkw_t
    pkw_do:
        li r4, 0
        bl h_srch
        cmpwi r3, 0
        li r4, 5
        bge pk_go
        li r4, 0
        bl h_grp
        stw r3, 0x%(V2)X(r31)
        li r0, 0
        stw r0, 0x%(V4)X(r31)
    pkw_t:
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V0)X(r31)
        cmpwi r3, 0
        bgt pkw_wall
        bl h_near
        cmpwi r3, 0
        blt pkw_r
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        bne pkw_4
    pkw_r:
        lwz r3, 0x%(P4)X(r30)
        lwz r4, 0x%(P5)X(r30)
        bl h_rand
        stw r3, 0x%(V0)X(r31)
    pkw_wall:
        bl h_wall
        cmpwi r3, 0
        beq pk_epi
    pkw_4:
        li r4, 4
        b pk_go""")
    # pk_gchk (state 3, 0x22528..0x22730) -> r3 = 8 / 9 / 0: the nearest fighter T within P8 (200) of the centre C;
    # ray_check(C, T - C, every collision) hits at H1 nearer than T and within P9 (15) of C; then ray_check(C, T - C,
    # the passable floors left out): a hit H2 no farther than H1 -> 8 (a wall: the ghost); else (a passable floor in
    # the way) T within 30 degrees of straight below C (atan2 in (-120, -60): dy < 0 and 3 dx^2 < dy^2) -> 9 (drop)
    a("""
    pk_gchk:
        stwu r1, -0x50(r1)
        mflr r0
        stw r0, 0x54(r1)
        bl h_near
        cmpwi r3, 0
        blt pkg_no
        mr r5, r3
        addi r3, r1, 8
        mr r4, r31
        %(TPOS)s
        addi r3, r1, 0x18
        mr r4, r31
        %(CPOS)s
        lfs f1, 8(r1)
        lfs f0, 0x18(r1)
        fsubs f1, f1, f0
        stfs f1, 0x28(r1)
        lfs f2, 0xC(r1)
        lfs f0, 0x1C(r1)
        fsubs f2, f2, f0
        stfs f2, 0x2C(r1)
        bl pk_len
        stfs f1, 0x30(r1)
        lfs f0, 0x%(P8)X(r30)
        fcmpu cr0, f1, f0
        bgt pkg_no
        addi r4, r1, 0x18
        addi r5, r1, 0x28
        addi r6, r1, 0x34
        li r7, 1
        bl pk_ray
        cmpwi r3, 0
        beq pkg_no
        bl pkg_h
        stfs f1, 0x3C(r1)
        lfs f0, 0x30(r1)
        fcmpu cr0, f0, f1
        ble pkg_no
        lfs f0, 0x%(P9)X(r30)
        fcmpu cr0, f1, f0
        bgt pkg_no
        addi r4, r1, 0x18
        addi r5, r1, 0x28
        addi r6, r1, 0x34
        li r7, 0
        bl pk_ray
        cmpwi r3, 0
        beq pkg_ang
        bl pkg_h
        lfs f0, 0x3C(r1)
        fcmpu cr0, f1, f0
        bgt pkg_ang
        li r3, 8
        b pkg_out
    pkg_ang:
        lfs f2, 0x2C(r1)
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f2, f0
        bge pkg_no
        lfs f1, 0x28(r1)
        fmuls f1, f1, f1
        lfs f0, 0x%(C3)X(r30)
        fmuls f1, f1, f0
        fmuls f2, f2, f2
        fcmpu cr0, f1, f2
        bge pkg_no
        li r3, 9
        b pkg_out
    pkg_no:
        li r3, 0
    pkg_out:
        lwz r0, 0x54(r1)
        mtlr r0
        addi r1, r1, 0x50
        blr
    pkg_h:
        lfs f1, 0x34(r1)
        lfs f0, 0x18(r1)
        fsubs f1, f1, f0
        lfs f2, 0x38(r1)
        lfs f0, 0x1C(r1)
        fsubs f2, f2, f0
        b pk_len
    """)
    # 4 turn (0x2160C / 0x22440): kinetic 0, ground on, Turn, the normal meshes; end: reverse_lr(1, 1), => 3
    st2('pk_turn_en', """
        li r4, 0
        bl h_kin
        li r4, 1
        bl h_att
        li r4, 12
        li r5, 0
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(C1)X(r30)
        bl pk_mot
        bl pk_mn""")
    st2('pk_turn_up', "bl h_end\ncmpwi r3, 0\nbeq pk_epi\nbl h_rev\nli r4, 3\nb pk_goi")
    # 5 back-off (0x2343C / 0x23678): W+0x10 = 0.1, +0x08 = P13 (0.4), +0x14 = 0, kinetic 1, ground on, Attackhold at
    # P15 (1.5), the normal meshes (play_se 0x6B10006: not ported), V2 = int(P14) (40). Update: move with the stick
    # reversed; a ledge: clear_speed_all, kinetic 0; V2 out -> 6
    st2('pk_back_en', """
        bl pk_w
        lwz r0, 0x%(C0_1)X(r30)
        stw r0, 0x10(r10)
        lwz r0, 0x%(P13)X(r30)
        stw r0, 8(r10)
        li r0, 0
        stw r0, 0x14(r10)
        li r4, 1
        bl h_kin
        li r4, 1
        bl h_att
        li r4, 1
        li r5, 0
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(P15)X(r30)
        bl pk_mot
        bl pk_mn
        lfs f1, 0x%(P14)X(r30)
        fctiwz f1, f1
        stfd f1, 8(r1)
        lwz r0, 0xC(r1)
        stw r0, 0x%(V2)X(r31)""")
    st2('pk_back_up', """
        lfs f1, 0x10(r31)
        fneg f1, f1
        stfs f1, 0(r29)
        li r0, 0
        stw r0, 4(r29)
        bl h_cliff
        cmpwi r3, 0
        beq pkb_t
        bl h_clear
        li r4, 0
        bl h_kin
    pkb_t:
        lwz r3, 0x%(V2)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V2)X(r31)
        cmpwi r3, 0
        bgt pk_epi
        li r4, 6
        b pk_go""")
    # 6 lunge (0x21DAC / 0x22B40; P2 entry 0 armed by set_attack_data): W+0x20 = P16 (2), +0x24 = P17 (1), +0x28 /
    # +0x2C = 10, +0x1C = 0, +0x3C = the gl gravity, kinetic 5, ground off, Attack at P18 (0.1, loop), the normal
    # meshes (play_se 0x6B10007: not ported), V5 = -1, no hit
    st2('pk_lunge_en', """
        bl pk_w
        lwz r0, 0x%(P16)X(r30)
        stw r0, 0x20(r10)
        lwz r0, 0x%(P17)X(r30)
        stw r0, 0x24(r10)
        lwz r0, 0x%(C10)X(r30)
        stw r0, 0x28(r10)
        stw r0, 0x2C(r10)
        li r0, 0
        stw r0, 0x1C(r10)
        bl f_gl
        lwz r0, 0x120(r3)
        bl pk_w
        stw r0, 0x3C(r10)
        li r4, 5
        bl h_kin
        li r4, 0
        bl h_att
        li r4, 0
        li r5, 1
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(P18)X(r30)
        bl pk_mot
        bl pk_mn
        li r0, -1
        stw r0, 0x%(V5)X(r31)
        li r0, 0
        stw r0, 0x%(HT)X(r31)""")
    # update: a hit (slot 6) or a wall -> the bounce: n = the hit object's direction (APPROXIMATED: the nearest
    # fighter's position stands in for BattleObjectAccessor::center_pos of the hit object, not mapped) or the wall's
    # get_ground_normal(6); |n|^2 < 1e-5: none; n normalised, v = the current speed reflected (v - 2 (n.v) n), its
    # angle a (degrees, atan2): a < 90 -> clamp(a + P20, P21, 90), else clamp(a - P20, 90, 180 - P21); W+0x20 = lr
    # cos x P19 |v|, +0x24 = sin x P19 |v|, kinetic 5, AttackModule clear_all (the hitbox ends), V5 = -1; then speed y
    # <= 0 on the ground => 7
    st2('pk_lunge_up', """
        lwz r0, 0x%(HT)X(r31)
        cmpwi r0, 0
        bne pkl_hit
        bl h_wall
        cmpwi r3, 0
        beq pkl_land
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        lwz r3, 0x18(r3)
        li r4, 6
        %(GN)s
        stw r3, 8(r1)
        stw r4, 0xC(r1)
        b pkl_n
    pkl_hit:
        li r0, 0
        stw r0, 0x%(HT)X(r31)
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        bl h_near
        cmpwi r3, 0
        blt pkl_n
        mr r5, r3
        addi r3, r1, 0x10
        mr r4, r31
        %(TPOS)s
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x10(r1)
        lfs f0, 0x10(r12)
        fsubs f1, f1, f0
        stfs f1, 8(r1)
        lfs f1, 0x14(r1)
        lfs f0, 0x14(r12)
        fsubs f1, f1, f0
        stfs f1, 0xC(r1)
    pkl_n:
        lfs f1, 8(r1)
        lfs f2, 0xC(r1)
        fmuls f1, f1, f1
        fmuls f2, f2, f2
        fadds f1, f1, f2
        lfs f0, 0x%(EPS)X(r30)
        fcmpu cr0, f1, f0
        blt pkl_land
        lfs f1, 8(r1)
        lfs f2, 0xC(r1)
        bl pk_len
        lfs f0, 8(r1)
        fdivs f30, f0, f1
        lfs f0, 0xC(r1)
        fdivs f29, f0, f1
        addi r3, r1, 0x10
        mr r4, r31
        %(SPD)s
        lfs f1, 0x10(r1)
        lfs f2, 0x14(r1)
        fmuls f0, f30, f1
        fmuls f3, f29, f2
        fadds f0, f0, f3
        lfs f3, 0x%(C2)X(r30)
        fmuls f0, f0, f3
        fmuls f3, f30, f0
        fsubs f1, f1, f3
        fmuls f3, f29, f0
        fsubs f2, f2, f3
        stfs f1, 0x18(r1)
        stfs f2, 0x1C(r1)
        bl pk_len
        fmr f31, f1
        lfs f30, 0x%(C0)X(r30)
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f31, f0
        beq pkl_deg
        lfs f1, 0x18(r1)
        fdivs f1, f1, f31
        lfs f0, 0x%(C1)X(r30)
        fcmpu cr0, f1, f0
        ble pkl_c1
        fmr f1, f0
    pkl_c1:
        lfs f0, 0x%(CM1)X(r30)
        fcmpu cr0, f1, f0
        bge pkl_c2
        fmr f1, f0
    pkl_c2:
        %(ACOS)s
        lfs f0, 0x%(R2D)X(r30)
        fmuls f30, f1, f0
        lfs f1, 0x1C(r1)
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f1, f0
        bge pkl_deg
        fneg f30, f30
    pkl_deg:
        lfs f0, 0x%(C90)X(r30)
        fcmpu cr0, f30, f0
        bge pkl_b
        lfs f1, 0x%(P20)X(r30)
        fadds f30, f30, f1
        lfs f1, 0x%(P21)X(r30)
        fcmpu cr0, f30, f1
        bge pkl_a2
        fmr f30, f1
        b pkl_ang
    pkl_a2:
        fcmpu cr0, f30, f0
        ble pkl_ang
        fmr f30, f0
        b pkl_ang
    pkl_b:
        lfs f1, 0x%(P20)X(r30)
        fsubs f30, f30, f1
        lfs f1, 0x%(C180)X(r30)
        lfs f2, 0x%(P21)X(r30)
        fsubs f1, f1, f2
        fcmpu cr0, f30, f0
        bge pkl_b2
        fmr f30, f0
        b pkl_ang
    pkl_b2:
        fcmpu cr0, f30, f1
        ble pkl_ang
        fmr f30, f1
    pkl_ang:
        lfs f0, 0x%(P19)X(r30)
        fmuls f31, f31, f0
        lfs f0, 0x%(D2R)X(r30)
        fmuls f30, f30, f0
        fmr f1, f30
        %(COS)s
        fmuls f1, f1, f31
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x60(r12)
        fmuls f1, f1, f0
        bl pk_w
        stfs f1, 0x20(r10)
        fmr f1, f30
        %(SIN)s
        fmuls f1, f1, f31
        bl pk_w
        stfs f1, 0x24(r10)
        li r4, 5
        bl h_kin
        lwz r3, 0(r31)
        lwz r3, 0x30C8(r3)
        %(ACLR)s
        li r0, -1
        stw r0, 0x%(V5)X(r31)
    pkl_land:
        bl h_vy0
        bgt pk_epi
        bl h_gnd
        cmpwi r3, 0
        beq pk_epi
        li r4, 7
        b pk_goi""")
    # 7 slide (0x23214 / 0x23580): energy 0's speed kept through kinetic 26 (its +8 = 0), ground on, Landiing, the
    # normal meshes. Update: energy 0's x eased toward 0 by P22 (0.1) a frame (its +8 = 0); on the ground with |x| <
    # 0.1 -> 3
    st2('pk_slide_en', """
        bl pk_e0
        lfs f31, 0(r10)
        lfs f30, 4(r10)
        li r4, 26
        bl h_kin
        bl pk_e0
        stfs f31, 0(r10)
        stfs f30, 4(r10)
        li r0, 0
        stw r0, 8(r10)
        li r4, 1
        bl h_att
        li r4, 10
        li r5, 0
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(C1)X(r30)
        bl pk_mot
        bl pk_mn""")
    st2('pk_slide_up', """
        bl pk_e0
        lfs f1, 0(r10)
        lfs f2, 0x%(P22)X(r30)
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f1, f0
        blt pks_neg
        fcmpu cr0, f1, f2
        blt pks_z
        fsubs f1, f1, f2
        b pks_st
    pks_neg:
        fneg f3, f2
        fcmpu cr0, f1, f3
        bgt pks_z
        fadds f1, f1, f2
        b pks_st
    pks_z:
        fmr f1, f0
    pks_st:
        stfs f1, 0(r10)
        li r0, 0
        stw r0, 8(r10)
        fmr f31, f1
        bl h_gnd
        cmpwi r3, 0
        beq pk_epi
        fabs f1, f31
        lfs f0, 0x%(C0_1)X(r30)
        fcmpu cr0, f1, f0
        bge pk_epi
        li r4, 3
        b pk_go""")
    # 8 ghost (0x2129C / 0x219C4): kinetic 26, energy 0 zeroed (+0x1C / +0x20 / +0x2C / +0x30 / +0 / +4 / +8 0, +0x34 /
    # +0x38 10), ground off, set_correct(0) (no ground collision), disable_hit, Move (once), every mesh off and the
    # model hidden (L65084(0, 0, 0)), follow effect 0x7200000 (EfffsPookaGogle: the goggles) on node 1 -> V3, V1 = 0
    st2('pk_ghost_en', """
        li r4, 26
        bl h_kin
        bl pk_e0
        li r0, 0
        stw r0, 0x1C(r10)
        stw r0, 0x20(r10)
        stw r0, 0x2C(r10)
        stw r0, 0x30(r10)
        stw r0, 0(r10)
        stw r0, 4(r10)
        stw r0, 8(r10)
        lwz r0, 0x%(C10)X(r30)
        stw r0, 0x34(r10)
        stw r0, 0x38(r10)
        li r4, 0
        bl h_att
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 0
        %(SCOR)s
        mr r3, r31
        %(DHIT)s
        li r4, 11
        li r5, 0
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(C1)X(r30)
        bl pk_mot
        li r4, 0
        li r5, 0
        li r6, 0
        bl pk_mesh
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        mr r3, r31
        lis r4, 0x720
        li r5, 1
        addi r6, r1, 8
        addi r7, r1, 8
        lfs f1, 0x%(C1)X(r30)
        %(FOL)s
        stw r3, 0x%(V3)X(r31)
        li r0, 0
        stw r0, 0x%(V1)X(r31)""")
    # update: every P11 (30) frames: the nearest fighter T, posture P: ray_check(P, T - P, the floors left out) hits
    # within P9 + 10 (25) of P, or ray_check(T, P - T) hits within |T - P| + 20 of P: still inside -> fly: T within
    # P12 (200): energy 0's speed = P10 (0.5) toward T (calc_angle and (0, P10) rotated: the same vector), +8 0,
    # +0x18 (the 3DS +0x1C) 1; V1 = P11. Clear: set_correct(5), enable_hit, the normal meshes, the effect removed,
    # -> 1, V4 = 1 (search at once)
    st2('pk_ghost_up', """
        lwz r3, 0x%(V1)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V1)X(r31)
        cmpwi r3, 0
        bgt pk_epi
        bl h_near
        cmpwi r3, 0
        blt pkh_rs
        mr r5, r3
        addi r3, r1, 8
        mr r4, r31
        %(TPOS)s
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f3, 0x10(r12)
        lfs f4, 0x14(r12)
        stfs f3, 0x18(r1)
        stfs f4, 0x1C(r1)
        lfs f1, 8(r1)
        fsubs f1, f1, f3
        lfs f2, 0xC(r1)
        fsubs f2, f2, f4
        stfs f1, 0x20(r1)
        stfs f2, 0x24(r1)
        fneg f3, f1
        fneg f4, f2
        stfs f3, 0x30(r1)
        stfs f4, 0x34(r1)
        bl pk_len
        fmr f31, f1
        addi r4, r1, 0x18
        addi r5, r1, 0x20
        addi r6, r1, 0x28
        li r7, 0
        bl pk_ray
        cmpwi r3, 0
        beq pkh_r2
        bl pkh_d
        lfs f0, 0x%(C25)X(r30)
        fcmpu cr0, f1, f0
        ble pkh_fly
    pkh_r2:
        addi r4, r1, 8
        addi r5, r1, 0x30
        addi r6, r1, 0x28
        li r7, 0
        bl pk_ray
        cmpwi r3, 0
        beq pkh_out
        bl pkh_d
        lfs f0, 0x%(C20)X(r30)
        fadds f0, f0, f31
        fcmpu cr0, f1, f0
        ble pkh_fly
    pkh_out:
        lwz r3, 0(r31)
        lwz r3, 0x30DC(r3)
        li r4, 5
        %(SCOR)s
        mr r3, r31
        %(EHIT)s
        bl pk_mn
        mr r3, r31
        lwz r4, 0x%(V3)X(r31)
        %(RMFX)s
        li r0, 0
        stw r0, 0x%(V3)X(r31)
        li r4, 1
        bl h_chg
        li r0, 1
        stw r0, 0x%(V4)X(r31)
        b pk_epi
    pkh_fly:
        lfs f0, 0x%(P12)X(r30)
        fcmpu cr0, f0, f31
        blt pkh_rs
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f31, f0
        beq pkh_rs
        lfs f0, 0x%(P10)X(r30)
        fdivs f0, f0, f31
        lfs f1, 0x20(r1)
        fmuls f1, f1, f0
        lfs f2, 0x24(r1)
        fmuls f2, f2, f0
        bl pk_e0
        stfs f1, 0(r10)
        stfs f2, 4(r10)
        li r0, 0
        stw r0, 8(r10)
        li r0, 1
        stb r0, 0x18(r10)
    pkh_rs:
        lwz r0, 0x%(P11)X(r30)
        stw r0, 0x%(V1)X(r31)""")
    a("""
    pkh_d:
        lfs f1, 0x28(r1)
        lfs f0, 0x18(r1)
        fsubs f1, f1, f0
        lfs f2, 0x2C(r1)
        lfs f0, 0x1C(r1)
        fsubs f2, f2, f0
        b pk_len
    """)
    # 9 drop (0x21550 / 0x22418): kinetic 8, set_current_speed((0, -1, 0)) (energy 0), ground off, passable on, Move
    # (once), the normal meshes, V1 = 0; V1 reaches 10 -> 1
    st2('pk_drop_en', """
        li r4, 8
        bl h_kin
        lfs f0, 0x%(C0)X(r30)
        stfs f0, 8(r1)
        lfs f0, 0x%(CM1)X(r30)
        stfs f0, 0xC(r1)
        addi r3, r31, 0x%(AER)X
        addi r4, r1, 8
        %(ASPD)s
        li r4, 0
        bl h_att
        bl f_pass1
        li r4, 11
        li r5, 0
        lfs f1, 0x%(C0)X(r30)
        lfs f2, 0x%(C1)X(r30)
        bl pk_mot
        bl pk_mn
        li r0, 0
        stw r0, 0x%(V1)X(r31)""")
    st2('pk_drop_up', """
        lwz r3, 0x%(V1)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(V1)X(r31)
        cmpwi r3, 10
        blt pk_epi
        li r4, 1
        b pk_go""")
    # 10 balloon (slot 67, 69, 60, 70, 16; 0x21F74 / 0x22E90): the launch: x = the damage's speed x (DamageModule
    # +0x6C +0xC: the same struct on both, read at +0x30 by the kinetic-20 setters 3DS 0x645FC0 / Wii U 0x026A97D0),
    # -x if lr < 0, x (1 - P30 %%); y = P28 (1 - HP / thr) + P27 HP / thr; W+0x20 / +0x24 = x / y, +0x28 / +0x2C = 10,
    # +0x1C = P31, +0x3C = P32, kinetic 5, ground off (the ray_check_from_pos lift out of a floor: not ported),
    # Damageballoon at frame V7, rate 0, the damage meshes, V0 = int(P24) (15), V2 = dead ? P33 (0) : P25 (100),
    # inflating
    st2('pk_bal_en', """
        lwz r12, 0(r31)
        lwz r11, 0x30D4(r12)
        lfs f1, 0x78(r11)
        lwz r12, 0x311C(r12)
        lfs f0, 0x60(r12)
        lfs f2, 0x%(C0)X(r30)
        fcmpu cr0, f0, f2
        bge pkb_x
        fneg f1, f1
    pkb_x:
        lfs f0, 0x%(P30)X(r30)
        fmuls f0, f0, f1
        lfs f2, 0x%(C01)X(r30)
        fmuls f0, f0, f2
        fsubs f31, f1, f0
        bl pk_thr
        fdivs f2, f2, f1
        lfs f0, 0x%(C1)X(r30)
        fsubs f0, f0, f2
        lfs f3, 0x%(P28)X(r30)
        fmuls f0, f0, f3
        lfs f3, 0x%(P27)X(r30)
        fmuls f2, f2, f3
        fadds f30, f0, f2
        bl pk_w
        stfs f31, 0x20(r10)
        stfs f30, 0x24(r10)
        lwz r0, 0x%(C10)X(r30)
        stw r0, 0x28(r10)
        stw r0, 0x2C(r10)
        lwz r0, 0x%(P31)X(r30)
        stw r0, 0x1C(r10)
        lwz r0, 0x%(P32)X(r30)
        stw r0, 0x3C(r10)
        li r4, 5
        bl h_kin
        li r4, 0
        bl h_att
        li r4, 2
        li r5, 0
        lfs f1, 0x%(V7)X(r31)
        lfs f2, 0x%(C0)X(r30)
        bl pk_mot
        bl pk_md
        lfs f1, 0x%(P24)X(r30)
        fctiwz f1, f1
        stfd f1, 8(r1)
        lwz r0, 0xC(r1)
        stw r0, 0x%(V0)X(r31)
        bl pk_dead
        lwz r0, 0x%(P25)X(r30)
        beq pkb_h
        lwz r0, 0x%(P33)X(r30)
    pkb_h:
        stw r0, 0x%(V2)X(r31)
        li r0, 1
        stw r0, 0x%(V8)X(r31)
        li r0, 0
        stw r0, 0x%(DF)X(r31)""")
    # update: move; falling onto the ground: W+0x20 = the speed x (-x if lr < 0), +0x24 = -0.8 y, kinetic 5 (a
    # bounce). Inflating: pct = (V6 - HP) 100 / V6; V0 counts down: while it runs the frame moves 1/P24 of the way
    # to pct %% of end_frame (+0.1, at most end_frame: set_frame, V7); then V2 counts down: dead => 11 (the pop), else
    # deflating, V2 = P25. Deflating: frame - P26 (0.3) (>= 0, set_frame, V7), set_current_damage(max - V6 + frame /
    # end x V6) (HP climbs back to V6 with it; update_weaken: not ported); frame 0: HP = P29 (90) %% of max,
    # reset_gravity, -> 1
    st2('pk_bal_up', """
        bl h_mv
        bl h_vy0
        bgt pkb_i
        bl h_gnd
        cmpwi r3, 0
        beq pkb_i
        addi r3, r1, 8
        mr r4, r31
        %(SPD)s
        lfs f1, 8(r1)
        lfs f2, 0xC(r1)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x60(r12)
        lfs f3, 0x%(C0)X(r30)
        fcmpu cr0, f0, f3
        bge pkb_bx
        fneg f1, f1
    pkb_bx:
        lfs f0, 0x%(CM08)X(r30)
        fmuls f2, f2, f0
        bl pk_w
        stfs f1, 0x20(r10)
        stfs f2, 0x24(r10)
        li r4, 5
        bl h_kin
    pkb_i:
        lwz r0, 0x%(V8)X(r31)
        cmpwi r0, 0
        beq pkb_d
        bl pk_w
        lfs f0, 0(r10)
        lfs f2, 0x%(V6)X(r31)
        fsubs f0, f2, f0
        lfs f1, 0x%(C100)X(r30)
        fmuls f0, f0, f1
        fdivs f31, f0, f2
        bl pk_endf
        fmr f29, f1
        bl pk_mm
        lfs f30, 0x%(MF)X(r3)
        lfs f1, 0x%(C100)X(r30)
        fmuls f0, f30, f1
        fdivs f0, f0, f29
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V0)X(r31)
        cmpwi r3, 0
        bgt pkb_f
        lwz r3, 0x%(V2)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V2)X(r31)
        cmpwi r3, 0
        bgt pk_epi
        bl pk_dead
        li r4, 11
        bne pk_goi
        li r0, 0
        stw r0, 0x%(V8)X(r31)
        li r0, 1
        stw r0, 0x%(DF)X(r31)
        lwz r0, 0x%(P25)X(r30)
        stw r0, 0x%(V2)X(r31)
        b pk_epi
    pkb_f:
        fsubs f0, f31, f0
        fmuls f0, f0, f29
        lfs f1, 0x%(C01)X(r30)
        fmuls f0, f0, f1
        lfs f1, 0x%(P24)X(r30)
        fdivs f0, f0, f1
        fadds f0, f30, f0
        lfs f1, 0x%(C0_1)X(r30)
        fadds f1, f0, f1
        fcmpu cr0, f29, f1
        bge pkb_fs
        fmr f1, f29
    pkb_fs:
        stfs f1, 0x%(V7)X(r31)
        bl pk_setf
        b pk_epi
    pkb_d:
        bl pk_mm
        lfs f1, 0x%(MF)X(r3)
        lfs f0, 0x%(P26)X(r30)
        fsubs f1, f1, f0
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f1, f0
        bge pkb_d0
        fmr f1, f0
    pkb_d0:
        fmr f31, f1
        stfs f1, 0x%(V7)X(r31)
        bl pk_setf
        bl pk_endf
        fdivs f1, f31, f1
        lfs f2, 0x%(V6)X(r31)
        fmuls f1, f1, f2
        bl pk_w
        lfs f0, 4(r10)
        fsubs f0, f0, f2
        fadds f1, f1, f0
        bl pk_dmg
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f31, f0
        bgt pk_epi
        li r0, 0
        stw r0, 0x%(DF)X(r31)
        bl pk_w
        lfs f1, 4(r10)
        lfs f0, 0x%(P29)X(r30)
        fmuls f0, f0, f1
        lfs f2, 0x%(C01)X(r30)
        fmuls f0, f0, f2
        fsubs f1, f1, f0
        bl pk_dmg
        bl pk_grav
        li r4, 1
        b pk_go""")
    # 11 pop (0x217F4 / 0x22870; P2 entry 1 armed: the size-30 burst): kinetic -1, ground off (the inlined status
    # 0x2711 request on acc+0x30AC: not mapped), every mesh off and the model hidden (L65084(1, 1, 0)), effect
    # 0x7200001 (EfffsPookaBlowout) at node 3 (HipN) scale P35 (3) (play_se 0x6B10005: not ported), V2 = P34 (1),
    # DEFEATED (the removal's defeat path). Update: move; V2 reaches 0: create_dead_item(1, 0, 0, 0) (Wii U 0x02DB3944:
    # nothing in the sm category) and request_quake(3); the sound playing (APPROXIMATED: PK_POP frames, the tone's
    # length) -> 12 (removed)
    st2('pk_pop_en', """
        li r4, -1
        bl h_kin
        li r4, 0
        bl h_att
        li r4, 1
        li r5, 1
        li r6, 0
        bl pk_mesh
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        mr r3, r31
        lis r4, 0x720
        ori r4, r4, 1
        li r5, 3
        addi r6, r1, 8
        addi r7, r1, 8
        lfs f1, 0x%(P35)X(r30)
        %(NODEFX)s
        lwz r0, 0x%(P34)X(r30)
        stw r0, 0x%(V2)X(r31)
        li r0, 1
        stw r0, 0x%(DFT)X(r31)""".replace('%(DFT)X', '%X' % DEFEATED))
    st2('pk_pop_up', """
        bl h_mv
        lwz r3, 0x%(V2)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V2)X(r31)
        cmpwi r3, 0
        bgt pk_epi
        bne pkp_s
        mr r3, r31
        li r4, 0
        li r5, 0
        lfs f1, 0x%(C1)X(r30)
        lfs f2, 0x%(C0)X(r30)
        %(DEAD)s
        mr r3, r31
        li r4, 3
        %(QUAKE)s
    pkp_s:
        lwz r3, 0x%(V2)X(r31)
        lwz r0, 0x%(POPEND)X(r30)
        cmpw r3, r0
        bgt pk_epi
        li r4, 12
        b pk_go""")
    # slot 6 (the 3DS's 7, 0x23670: the attack-hit notification, +0x17C = the hit object): V5 = r4, the hit flag,
    # and BehaviorImpl's (+0x118 = 1)
    a("""
    pk_hit:
        stw r4, 0x%(V5)X(r3)
        li r0, 1
        stw r0, 0x%(HT)X(r3)
        stb r0, 0x118(r3)
        blr
    """)
    # slot 12 (the 3DS's 13, 0x232B8: the capture motion): HP >= the threshold: the gl capture motion (zima's slot 12
    # makes the same call: gl +0x54 at rate gl +0x48, loop), not inflating / deflating; shown: the damage meshes;
    # passable off; HP below: inflating; V4 = 0
    st2('pk_12', """
        bl pk_thr
        fcmpu cr0, f2, f1
        blt pk12_m
        mr r3, r31
        %(CAPM)s
        li r0, 0
        stw r0, 0x%(V8)X(r31)
        stw r0, 0x%(DF)X(r31)
    pk12_m:
        bl pk_md_if
        bl pk_pass0
        bl pk_thr
        fcmpu cr0, f2, f1
        bge pk12_o
        li r0, 1
        stw r0, 0x%(V8)X(r31)
        li r0, 0
        stw r0, 0x%(DF)X(r31)
    pk12_o:
        li r0, 0
        stw r0, 0x%(V4)X(r31)""")
    # slot 16 (the 3DS's 17, 0x236F0: the capture cut): => 10
    st2('pk_16', "li r4, 10\nb pk_goi")
    # slot 51 (0x65060): sync_lr_and_direction (BehaviorImpl's), then L65084(0, 1, 1)
    orig51 = VT_WORDS[0][(0xC + 8 * 51) // 4] if VT_WORDS[0] else 0
    st2('pk_51', "mr r3, r31\nmr r4, r29\n" + call(orig51) + "\nbl pk_md")
    # slot 56 (0x2376C; the common damage states call it each frame, Wii U 0x026A05E8.. before slot 59): inflating:
    # pct <= the frame's %% -> deflating; else the frame moves 1/P24 of the way (as 10); +0x120 = 0. Deflating: the
    # frame - P26 and the HP with it (as 10); at frame 0: +0x120 = 1, the gl capture motion (as slot 12), HP at
    # least P29 %%, V7 = 0, not deflating. Neither: +0x120 = 1
    st2('pk_56', """
        lwz r0, 0x%(V8)X(r31)
        cmpwi r0, 0
        beq pk56_d
        bl pk_w
        lfs f0, 0(r10)
        lfs f2, 0x%(V6)X(r31)
        fsubs f0, f2, f0
        lfs f1, 0x%(C100)X(r30)
        fmuls f0, f0, f1
        fdivs f31, f0, f2
        bl pk_endf
        fmr f29, f1
        bl pk_mm
        lfs f30, 0x%(MF)X(r3)
        lfs f1, 0x%(C100)X(r30)
        fmuls f0, f30, f1
        fdivs f0, f0, f29
        fcmpu cr0, f31, f0
        bgt pk56_f
        li r0, 0
        stw r0, 0x%(V8)X(r31)
        li r0, 1
        stw r0, 0x%(DF)X(r31)
        b pk56_0
    pk56_f:
        fsubs f0, f31, f0
        fmuls f0, f0, f29
        lfs f1, 0x%(C01)X(r30)
        fmuls f0, f0, f1
        lfs f1, 0x%(P24)X(r30)
        fdivs f0, f0, f1
        fadds f0, f30, f0
        lfs f1, 0x%(C0_1)X(r30)
        fadds f1, f0, f1
        fcmpu cr0, f29, f1
        bge pk56_fs
        fmr f1, f29
    pk56_fs:
        stfs f1, 0x%(V7)X(r31)
        bl pk_setf
    pk56_0:
        li r0, 0
        stb r0, 0x120(r31)
        b pk_epi
    pk56_d:
        lwz r0, 0x%(DF)X(r31)
        cmpwi r0, 0
        bne pk56_dd
    pk56_1:
        li r0, 1
        stb r0, 0x120(r31)
        b pk_epi
    pk56_dd:
        bl pk_mm
        lfs f1, 0x%(MF)X(r3)
        lfs f0, 0x%(P26)X(r30)
        fsubs f1, f1, f0
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f1, f0
        bge pk56_d0
        fmr f1, f0
    pk56_d0:
        fmr f31, f1
        stfs f1, 0x%(V7)X(r31)
        bl pk_setf
        bl pk_endf
        fdivs f1, f31, f1
        lfs f2, 0x%(V6)X(r31)
        fmuls f1, f1, f2
        bl pk_w
        lfs f0, 4(r10)
        fsubs f0, f0, f2
        fadds f1, f1, f0
        bl pk_dmg
        lfs f0, 0x%(C0)X(r30)
        fcmpu cr0, f31, f0
        bgt pk56_0
        li r0, 1
        stb r0, 0x120(r31)
        mr r3, r31
        %(CAPM)s
        bl pk_up90
        li r0, 0
        stw r0, 0x%(V7)X(r31)
        stw r0, 0x%(DF)X(r31)""")
    # pk_up90: HP below P29 %% of max -> set_current_damage(max - P29 %%)
    a("""
    pk_up90:
        mflr r0
        stw r0, 0x2C(r1)
        bl pk_w
        lfs f2, 4(r10)
        lfs f0, 0x%(P29)X(r30)
        fmuls f0, f0, f2
        lfs f1, 0x%(C01)X(r30)
        fmuls f0, f0, f1
        lfs f1, 0(r10)
        fcmpu cr0, f1, f0
        bge pku_o
        fsubs f1, f2, f0
        bl pk_dmg
    pku_o:
        lwz r0, 0x2C(r1)
        mtlr r0
        blr
    """)
    # slot 60 (0x22A68; the common states' end, Wii U 0x026A03AC..: after damage_wakeup): reset_gravity; HP >= V6:
    # HP at least P29 %%, V7 = 0, the normal meshes (update_weaken: not ported); else => 10
    st2('pk_60', """
        bl pk_grav
        bl pk_w
        lfs f1, 0(r10)
        lfs f0, 0x%(V6)X(r31)
        fcmpu cr0, f1, f0
        li r4, 10
        blt pk_goi
        bl pk_up90
        li r0, 0
        stw r0, 0x%(V7)X(r31)
        bl pk_mn""")
    # slot 69 (0x23A48; notify_on_damage's reaction hook): shown -> L65084(0, 1, 1); passable off; HP <= P23 %% of
    # max => 10 and returns 1 (no knock-back reaction); else 0
    st2('pk_69', """
        bl pk_md_if
        bl pk_pass0
        bl pk_thr
        li r28, 0
        fcmpu cr0, f2, f1
        bgt pk69_o
        li r4, 10
        bl h_chgi
        li r28, 1
    pk69_o:
        mr r3, r28""")
    # slot 70 (0x23B14; notify_on_damage without a reaction): common state (+0xE4) 4 / 5 / 6 / 8 / 9 / 0xD / 0x10 /
    # 0x11 / 0x12: shown -> L65084(0, 1, 1), passable off, +0x120 = 0, HP <= V6: Damageballoon at V7 (rate 0),
    # inflating; common state 0 and HP <= the threshold => 10
    st2('pk_70', """
        lwz r0, 0xE4(r31)
        li r12, 1
        slw r12, r12, r0
        lis r11, 0x7
        ori r11, r11, 0x2370
        and. r12, r12, r11
        bne pk70_c
        cmpwi r0, 0
        bne pk_epi
        bl pk_thr
        fcmpu cr0, f2, f1
        bgt pk_epi
        li r4, 10
        b pk_goi
    pk70_c:
        bl pk_md_if
        bl pk_pass0
        li r0, 0
        stb r0, 0x120(r31)
        bl pk_w
        lfs f1, 0(r10)
        lfs f0, 0x%(V6)X(r31)
        fcmpu cr0, f1, f0
        bgt pk_epi
        li r4, 2
        li r5, 0
        lfs f1, 0x%(V7)X(r31)
        lfs f2, 0x%(C0)X(r30)
        bl pk_mot
        li r0, 1
        stw r0, 0x%(V8)X(r31)
        li r0, 0
        stw r0, 0x%(DF)X(r31)""")


def code_fix2j(H, st, call, d, D):
    """step 2j: the accuracy audit's small fixes (docs/smash-run-enemies/accuracy-audit.md, each from its 3DS
    address; docs/smash-run-port.md "Step 2j")"""
    en = lambda label, kin, att, mot, loop, extra='': st(label, "li r4, %d\nbl h_kin\nli r4, %d\nbl h_att\nli r4, %d\nli r5, %d\nbl h_mot1\n%s" % (kin, att, mot, loop, extra))  # noqa: E731,E501
    p = dict(d, CF_LEAVE=CF['LEAVE'], MK=MOT_KIND, AERO=AER, DFT=DEFEATED, FX=DO_FX)
    a = lambda text: H.asm(text % p)  # noqa: E731
    # ---- Waddle Doo. Slot 69 (0x7E0E0): the old hit effect (+0x1A0: DO_FX, step 2l; V8 before) removed,
    # request_effect(0x7190001, center_pos, 1.0) -> DO_FX, the leave timer (+0x184: V7) back to PS8c f0 (CFG LEAVE,
    # 600) (0x7E12C); returns 0
    st('do_69', """
        lwz r4, 0x%(FX)X(r31)
        cmpwi r4, 0
        beq d69_e
        mr r3, r31
    """ % p + call(REMOVE_EFFECT) + """
    d69_e:
        addi r3, r1, 8
        mr r4, r31
    """ + call(CENTER_POS) + """
        mr r3, r31
        lis r4, 0x719
        ori r4, r4, 1
        addi r5, r1, 8
        lis r12, 0x%(CH)04X
        lfs f1, %(CL1)d(r12)
    """ % dict(p, CL1=sx(D['consts'] + 4)) + call(REQ_EFFECT0) + """
        stw r3, 0x%(FX)X(r31)
        lwz r0, 0x%(CF_LEAVE)X(r30)
        stw r0, 0x%(V7)X(r31)
        li r3, 0""" % p)
    # the walk's random hop (state 3 0x7D568, after the wall test, before the searches): +0x170 (V4) + 1 > PS8c f1
    # (60): V4 = 0, random_range(1, 100) <= PS8c f2 (50) -> 6 (here 9); continues in o_walk_up's search (ow_look)
    a("""
    do_owr:
        lwz r3, 0x%(V4)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(V4)X(r31)
        lwz r0, 0x%(P8)X(r30)
        cmpw r0, r3
        bge do_bsw                  # step 2k: the beam's search (3DS 0x7D5D0), then the turn search
        li r0, 0
        stw r0, 0x%(V4)X(r31)
        li r3, 1
        li r4, 100
        bl h_rand
        lwz r0, 0x%(P9)X(r30)
        cmpw r3, r0
        bgt do_bsw
        li r4, 9
        b go
    do_fallm:
        mflr r0
        stw r0, 0x1C(r1)
        bl h_vy0
        bge dfm_o
        lwz r12, 0(r31)
        lwz r12, 0x30F0(r12)
        lwz r0, 0x%(MK)X(r12)
        cmpwi r0, 10
        beq dfm_o
        li r4, 10
        li r5, 1
        bl h_mot1
    dfm_o:
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """)
    # 6 (here 9) the random hop (0x7CE10 / 0x7D2CC): kinetic 5, ground off, Jump (once); falling: Fall (no restart,
    # loop); speed y <= 0 on the ground => 3 (the beam search in it: with the beam, not ported). 5's update (0x7D6BC)
    # switches to Fall the same way (0x7D6F0), then the wall hop's landing test (g_hop_up, HOPTHR 0.5: 0x7D77C)
    en('do_jump_en', 5, 0, 11, 0)
    # step 2k: not landed -> the beam's search in the air (0x7D350: search_interval(1) / search_target(1), +0x19D = 1)
    st('do_jump_up', "bl do_fallm\nbl h_vy0\nbgt do_bsa\nbl h_gnd\ncmpwi r3, 0\nbeq do_bsa\nli r4, 3\nb goi")
    st('do_hop_up', "bl do_fallm\nmr r3, r31\nmr r4, r29\nbl g_hop_up")
    # ---- Shy Guy slot 69 (0x1BF70): the run timer (+0x174: V2) = 0; returns 0
    a("""
    hh_69:
        li r0, 0
        stw r0, 0x%(V2)X(r3)
        li r3, 0
        blr
    """)
    # ---- Waddle Dee 2 parasol fall (0x7C6BC / 0x7C8E0): the aerial module (a flier-sized object now; the start
    # builds it), set_mode_normal(0, 0, P0 f6 0.0005, 0, 10, 10) with the current speed (x, -P0 f5 0.2): the Wii U's
    # reduced module has no mode 0, its uniform mode at that speed stands in (APPROXIMATED: the 0.0005 acceleration
    # toward the stick is left out); ground off; ParasolFall (loop). Update: the aerial update(stick x, -1, true) (Wii U
    # 0x02DB2524 = 3DS 0x5F66AC); on the ground => 3
    st('wd_para_en', """
        addi r3, r1, 8
        mr r4, r31
    """ + call(GET_SPEED) + """
        lfs f0, 0x%(P4)X(r30)
        fneg f0, f0
        stfs f0, 0xC(r1)
        li r4, 5
        bl f_amode
        li r4, 0
        bl h_att
        li r4, 11
        li r5, 1
        bl h_mot1""" % p)
    st('wd_para_up', """
        addi r3, r31, 0x%(AERO)X
        lfs f1, 0x10(r31)
        lfs f2, 0x%(P5)X(r30)
        li r4, 1
    """ % p + call(AER_UPDATE_XY) + """
        bl h_gnd
        cmpwi r3, 0
        beq.far epi
        li r4, 3
        b goi""")
    a("wd_aer:\nmflr r0\nstw r0, 0x1C(r1)\naddi r3, r31, 0x%(AERO)X\nlwz r4, 0(r31)\n" % p + call(AER_CTOR) +
      "\nlwz r0, 0x1C(r1)\nmtlr r0\nblr")
    # ---- Goomba. 4 notice (0x33248..0x333A0): check_cliff_distance_lr(P0 f7 x (P0 f8 / the gl gravity + 2) x -2,
    # -lr) (Wii U 0x026A6CF4 = 3DS 0x9EAED4: f1 distance, f2 lr; 0x026A6D88 is its speed-distance caller): a ledge
    # behind -> W+0x20 = 0, else P0 f7 (-0.4); kinetic 5, ground off, RunHoldL (loop); +0x179 (V2) = 1
    st('kc_ntc_en', """
        li r0, 0
        stw r0, 0x%(V0)X(r31)
        bl f_gl
        lfs f0, 0x120(r3)
        lfs f1, 0x%(P9)X(r30)
        fdivs f1, f1, f0
        lfs f0, 0x%(P10)X(r30)
        fadds f1, f1, f0
        lfs f0, 0x%(P8)X(r30)
        fmuls f1, f1, f0
        lfs f0, 0x%(P11)X(r30)
        fmuls f1, f1, f0
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f2, 0x60(r12)
        fneg f2, f2
        mr r3, r31
    """ % p + call(CHECK_CLIFF_DIST) + """
        bl h_ebase
        lwz r0, 0x%(P8)X(r30)
        cmpwi r3, 0
        beq kcn_s
        li r0, 0
    kcn_s:
        stw r0, 0x20(r10)
        li r4, 5
        bl h_kin
        li r4, 0
        bl h_att
        li r4, 12
        li r5, 1
        bl h_mot1
        li r0, 1
        stw r0, 0x%(V2)X(r31)""" % p)
    # 8 collapses (0x32A08): on the state frame P0 f14 (1) create_dead_item(1, 10, 0, 0) (Wii U 0x02DB3944: nothing
    # in the sm category, as at the removal); then k_col_up (the end -> 10). V6 the state frames (+0x16C)
    st('kc_col_en', "mr r3, r31\nmr r4, r29\nbl k_col_en\nli r0, 0\nstw r0, 0x%(V6)X(r31)" % p)
    st('kc_col_up', """
        lwz r3, 0x%(V6)X(r31)
        lwz r0, 0x%(P5)X(r30)
        cmpw r3, r0
        bne kcc_n
        mr r3, r31
        li r4, 0
        li r5, 0
        lfs f1, 0x%(P7)X(r30)
        lfs f2, 0x%(P6)X(r30)
    """ % p + call(CREATE_DEAD_ITEM) + """
    kcc_n:
        lwz r3, 0x%(V6)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(V6)X(r31)
        mr r3, r31
        mr r4, r29
        bl k_col_up""" % p)
    # ---- White Bear 6 quake hold's end (0x7F0xx: is_in_view_area 0x9EA804 = Wii U IN_VIEW 0x026A96BC): in view -> 7,
    # else -> 3
    st('wb_hold_up', "bl h_end\ncmpwi r3, 0\nbeq.far epi\nmr r3, r31\n" + call(IN_VIEW) +
       "\ncmpwi r3, 0\nli r4, 7\nbne.far go\nli r4, 3\nb go")



# ---- step 2k (docs/smash-run-port.md "Step 2k"): Waddle Doo's beam on the Wii U's own weapon kind 0xAF, Churine's
# sleep powder, the twins' own params, the White Bear's weakness, the dead items
GEN_ART_ANGLE = 0x026A7DD8           # Behavior::generate_article_angle(r4 id, f1 angle, r5 bool) (3DS 0x7B4BF8: the
#                                      angle into the AI energy +0x54, then generate_article 0x026A7D40: ArticleModule
#                                      (acc+0x4C) vt+0x54 generate(id, 0, bool, -1), vt+0xD4 on the article made)
UTIL_ACTIVATE = 0x02C073A8           # ArticleModule::util_activate(Article&, BattleObjectActivateParam&) (3DS 0x7DEB4's)
ACT_PARAM = 0x026CF4F0               # BattleObjectActivateParam ctor (0xA8 bytes; mczakoplasmawisp's spawners)
ACT_PARAM_FREE = 0x033EBE74          # the dtor of its members +0x3C / +0x48 (r4 = 2), as those spawners
ACC_TEAM = 0x312C                    # [acc+0x312C]+4: vt+0x14 the team (3DS [acc+0x30AC]+4 vt+8)
EFF_EXIST = 0x0334C78C               # EffectSystem::is_exist(handle) (3DS EffectModuleImpl::is_exist_effect 0x7FA27C)
EFF_RATE_LAST = 0x02C2CB74           # EffectModule (acc+0x30D8) set_rate_last(f1) (3DS 0x4D6B18, line for line)
ART_SETS = 0x10352794                # the enemy article sets by kind (0x02DC6D88; {entries*, count}, entries {kind, max,
#                                      spawner, 0})
WD_BEAM = 0xAF                       # the Wii U's weapon kind 0xAF (enemy / waddledoo / beam): descriptor 0x1041DC90,
#                                      singleton 0x1056A74C, specializer vtable 0x101741F0 (init 0x0319FE98 = 3DS 0xA407C,
#                                      life 0x031A026C = 3DS 0xA467C), the 3DS's own kind 175
DO_SC, DO_CD, DO_TK, DO_IX, DO_ANG, DO_AIR = (0x1B0 + 4 * i for i in range(6))   # 3DS +0x16C / +0x180 / +0x174 /
#                                      +0x178 / (30 - 25 n) / +0x19D (search-1 count, cool-down, shot wait, shot index,
#                                      the next angle, charged in the air)
DO_FX = 0x1B0 + 4 * 6                # step 2l: the hit effect's handle (3DS +0x1A0; step 2j kept it in V8, which the
#                                      landing's turn test g_landt_up reads as the hop-landing flag: a hit skipped it)
WD_PARASOL = 0xAD                    # step 2l: the Wii U's weapon kind 0xAD (enemy / waddledee / parasol): descriptor
#                                      0x1041DC60 (param getter 0x0319FC90: [slot 0x13]+0xEC), flags 0x842 (0x40: a
#                                      model), specializer vtable 0x10173F50 (slots 2 / 5 / 6 / 7 / 14 / 20 = the 3DS's
#                                      0xADE04 / 0xAE0D0 / 0xADF64 / 0xADED0 / 0xAE2D0 / 0xAE73C), the 3DS's own kind 173
PW_ROW2_UP = 0x102FE778              # step 2l: mczakoplasmawisp's state table (0x102FE754, rows {0xFFFF, enter, 0xFFFF,
#                                      update, 0xFFFF | 0, exit}) row 2's update word (the hover / search 0x026D09A4)
PW_UP2 = 0x026D09A4
GEN_ART = 0x026A7D40                 # Behavior::generate_article(r4 id, r5 bool) (3DS 0x7B1BBC)
WD_PARAM = 0x19                      # param slot [mgr + 0x60 + 4 * 0x19] (the beam's init reads [mgr+0xC4] +0xC8 / +0xCC
#                                      / +0xDC: the 3DS waddledoo param object's layout, enemy_param_vl_waddledoo.bin)
SLOT_OFF = {0x57: 0x1214, 0x58: 0x13DC, 0x59: 0x14A4, 0x5A: 0x1684}   # the sm accessor's block (vt+0x14 0x026B4120)
TWIN_CTOR = {0x57: 0x026B37A8, 0x58: 0x026B3A1C, 0x59: 0x026B3C30, 0x5A: 0x026B3ED4}
TWIN_DTOR = {0x57: 0x026B3980, 0x58: 0x026B3BA4, 0x59: 0x026B3E30, 0x5A: 0x026B4034}   # (obj, 0): 0x026B43E0's calls
TWIN_PARSE = {0x57: 0x026B6370, 0x58: 0x026B6380, 0x59: 0x026B6390, 0x5A: 0x026B63A0}   # (handle&, obj): vt+0x24
# step 2o: each parser is `mr r12, r4; mr r4, r3; addi r3, r12, LOADER; b 0x033B4770`: the object's loader member;
# the loader's byte +8 is 1 after a clean parse and 0 after a token / layout error (0x033B4770 clears it, the error
# path 0x033B4894 leaves it; the game's own ctor + loader run in unicorn on the twins' sm files, step 2k's files and
# step 2a's 3DS-layout files: tools/smashrun_step2o_test.py)
TWIN_LOADER = {0x57: 0x1A4, 0x58: 0xA4, 0x59: 0x1BC, 0x5A: 0xAC}
#                                      0x026B44B0's per-kind loads (0x026B4884 / 0x026B48EC / 0x026B4954 / 0x026B49BC)
KIND_OF = {'plasmawisp': 0x12, 'darios': 0x1D, 'stalfos': 0x30, 'zima': 0x0E}
SM_ACC_VT = 0x1008BFB8               # the sm param accessor's vtable (ctor 0x026B40B8), [mgr+0x28D0]
RES_DIR = 0x032D7220                 # lib path object (this, char*, 1) (vt+0x24 0x026B4510)
RES_DIR2 = 0x032D9A30                # (this, 1) (0x026B451C)
RES_JOIN = 0x032D7140                # (dir, &out, name, 0) (0x026B49AC)
RES_NEW = 0x032D3E3C                 # an empty handle (this) (vt+0x14's)
RES_FREE = 0x032D4200                # (this, 2)
TWIN_K = ((0x57, 'plasmawisp'), (0x58, 'darios'), (0x59, 'stalfos'), (0x5A, 'zima'))
WB_W, WB_D = 0x1B0, 0x1B4           # the White Bear's weak hit noted (slot 31) / its damage before the hit
BI_SLOT31 = 0x026A48EC               # BehaviorImpl's slot 31 (the hit record: +0x14 AttackData, its +0x4C)

# ---- step 2m (docs/smash-run-port.md "Step 2m"): sounds, Stalfos's drop through a passable floor
import smashrun_sound as SND  # noqa: E402
PLAY_SE = 0x026A96EC                 # Behavior::play_se(r4 id, r5 bool) -> handle (3DS 0x7B59A8 -> SoundModuleImpl::
#                                      play_se 0x4C4B84): SoundModule acc+0x30F4 0x02C72214(module, id, 0, bool, 0, 0, 0)
STOP_SE = 0x026A970C                 # Behavior::stop_se(r4 handle, r5) (3DS 0x4C3148 stop_se_handle): 0x02C73750
SND_MGR = 0x102F7288                 # [[[[SND_MGR]] + 0x29C] + 4] = the loaded soundlabeltable.bin (+8 byte: loaded);
#                                      read by 0x0311EC30 (row -> {bank, count, offset}) / 0x0311EDC4 (label -> tone)
IS_PASSABLE_GROUND = 0x02C36EFC      # GroundModule is_passable_ground() (3DS 0x96AB30: [+0x18] entry 3, flag 0x2000)
DO_SE = 0x1CC                        # the Waddle Doo's beam sound handle (3DS +0x1A4; free word before its 0x1D0)
ST_ROW_UP = {7: (0x102FE944, 0x026D3EB4), 8: (0x102FE95C, 0x026D41E8)}   # mczakostalfos's table (0x102FE8A8, row n
#                                      at +0x18 (n - 1)): states 7 / 8's update words and the game's updates
ST_HELP = {'l5f7f8': 0x026D3008, 'l5f3a4': 0x026D3818, 'l5f110': 0x026D3A68, 'l5f754': 0x026D3DA4}   # the twin's
#                                      helpers = the 3DS's L5F7F8 / L5F3A4 / L5F110 / L5F754 (states 7 / 8)
# every 3DS state-enter play_se of a ported kind: (kind, Wii U state) -> (id, the handle's field or None); the state's
# enter becomes se_<kind>_<state> = the enter, then play_se (the 3DS calls it at the enter's end), handle stored
SE_EN = {('kuribo', 4): (0x28D0002, None), ('kuribo', 8): (0x28D0004, None),
         ('heiho', 6): (0x69B0002, None), ('heiho', 7): (0x69B0002, None),
         ('waddledoo', 11): (0x6A80000, DO_SE),
         ('tikibuzz', 4): (0x89C0000, None), ('tikibuzz', 5): (0x89C0001, None),
         ('tikibuzz', 10): (0x89C0002, None), ('tikibuzz', 11): (0x89C0003, None),
         ('furiijio', 2): (0x6A90001, None), ('furiijio', 5): (0x6A90001, None),
         ('furiijio', 4): (0x6A90002, FU_SE), ('furiijio', 7): (0x6A90002, FU_SE),
         ('dekakuribo', 2): (0x2910009, None), ('dekakuribo', 8): (0x2910008, None),
         ('dekakuribo', 10): (0x291000C, None), ('dekakuribo', 11): (0x291000B, None),
         ('togezo', 5): (0x6D90000, None),
         ('pooka', 5): (0x6B10006, None), ('pooka', 6): (0x6B10007, None), ('pooka', 11): (0x6B10005, None)}
SE_ORIG = {}
_BY = {w['name']: w for w in WALKERS}
for (_n, _s), _v in SE_EN.items():
    _st = _BY[_n]['states'][_s]
    SE_ORIG[(_n, _s)] = _st[0]
    _BY[_n]['states'][_s] = ('se_%s_%d' % (_n, _s),) + tuple(_st[1:])
_BY['heiho']['states'][7] = (_BY['heiho']['states'][7][0], 'se_heiho_7u')      # 7 update: the second hop's sound
_BY['waddledoo']['states'][11] = _BY['waddledoo']['states'][11][:2] + ('se_doo_11x',)   # 3DS 8 exit 0x7DD18
for _s in (4, 7):                                                                # 3DS 4 / 7 exits 0x6D094 / 0x6D494
    _BY['furiijio']['states'][_s] = _BY['furiijio']['states'][_s][:2] + ('se_fu_bexit',)
_BY['furiijio']['vtover'][57] = 'se_fu_57'       # 3DS slot 57 0x6DBDC (DownBoundEnd / DownWait: the bound sound)
_BY['furiijio']['f69'] = 'se_fu_69'              # 3DS slot 69 0x6DC48 (+0x264 = 0, returns 0)
_BY['ghos'].update(fdmg='se_gh_dmg', f27='se_gh_rm')        # 3DS slots 11 0x11094 / 28 0x11140: the gas loop stopped
_BY['propellerheiho'].update(fstart='se_ph_start')          # 3DS slot 41 0x99010: the propeller loop, one per kind
_BY['propellerheiho']['vtover'].update({55: 'se_ph_55', 71: 'se_ph_71'})   # 3DS slots 55 (the swap) / 71 (death)
_BY['propellerheiho']['states'][2] = (_BY['propellerheiho']['states'][2][0], 'se_ph2_up')   # 3DS 2 update 0x99CC4
_BY['pooka'].update(fdmg='se_pk_dmg')            # 3DS slot 11 0x22900: HP at the threshold -> play_se(0x6B10004)


def param_members(name):
    import json
    with open(os.path.join(SPECS, name + '.json')) as f:
        return json.load(f)['params']['members']


def param_size(members):
    """the object's size: past its last member (a vector {reader, elem size, count, data, flag} is 0x14 bytes)"""
    return max(m['offset'] + (0x14 if m['type'] == 'array' else 4 * len(m['values'][0]) if m['type'] == 'struct'
                              else 4) for m in members)


def param_label(name):
    return 'wdp' if name == 'waddledoo' else 'prm_' + name


def kind_param_blocks(name, g):
    """step 2l (step 2k's wd_param_blocks for every kind): the kind's static param object in its own 3DS layout
    (enemy_param_vl_<name>.bin through the spec: P0.. vectors {0, elem size, count, data, 0}, the structs and words
    at their 3DS offsets) and its arrays: [(label, words, align)]. The framework reads P3 (the hurtboxes, 0x02D896F4:
    +0x44 count (at most 15), +0x48 data, 0x30 an entry) and P4 (the ground box, the accessor set-up 0x02DA2BA0:
    +0x5C) from it, the weapons their kind's own params (0xAF the Doo's beam +0xC4.., 0xAD the Dee's parasol +0x88 /
    +0xB0.. / +0xEC)"""
    members = param_members(name)
    lab0 = param_label(name)
    obj = [0] * (param_size(members) // 4)
    out = []
    for m in members:
        o = m['offset'] // 4
        if m['type'] == 'array':
            lab = '%s_%d' % (lab0, m['index'])
            ents = m['values']
            out.append((lab, [word(v) for e in ents for v in e], 4))
            obj[o:o + 5] = [0, m['elem_size'], len(ents), g(lab), 0]
        elif m['type'] == 'struct':
            vals = m['values'][0]
            obj[o:o + len(vals)] = [word(v) for v in vals]
        else:
            obj[o] = word(m['value'])
    return [(lab0, obj, 4)] + out


def wd_param_blocks(g):
    """the static waddledoo param object (step 2k; kind_param_blocks since step 2l)"""
    return kind_param_blocks('waddledoo', g)


def cstr(s):
    b = s.encode() + b'\0'
    b += b'\0' * (-len(b) % 4)
    return list(struct.unpack('>%dI' % (len(b) // 4), b))


def code_2l_pw(H):
    """step 2l: Lethinium (plasmawisp, kind 0x12) on its twin's AI: mczakoplasmawisp's state 2 update (0x026D09A4)
    has a Fortress-only branch: at level 2 (+0x1EC; the 3DS +0x1E8) it counts +0x1E4 (set to P+0x138 120 by the
    level-up 0x026D04B0) down and, at 0, forces the level-2 attack (change_state(8), 0x026D0BE8..0x026D0C1C) with no
    search, no chance and no distance test. The 3DS's update (0x88E68: 0x88FD0..0x89224) has no such branch: at level
    2 it only skips the level counter and goes on to the attack timer +0x1E0, the search and the chance / distance
    test, as the Wii U's 0x026D0C48 path does. pw2_up (the row's update for both kinds): for kind 0x12 at level >= 2,
    +0x1E4 = 0x7FFFFFFF (its - 1 stays > 0, so 0x026D0BF4 takes the 0x026D0C48 path: the 3DS's), then the game's
    update. The twin (0x57) is unchanged."""
    H.asm("""
    pw2_up:
        lwz r0, 8(r3)
        cmpwi r0, 0x12
        bne pw2_go
        lwz r0, 0x1EC(r3)
        cmpwi r0, 2
        blt pw2_go
        lis r0, 0x7FFF
        ori r0, r0, 0xFFFF
        stw r0, 0x1E4(r3)
    pw2_go:
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        mtctr r12
        bctr
    """ % (PW_UP2 >> 16, PW_UP2 & 0xFFFF))


def code_2m(H, st, call, D):
    """step 2m (region H; docs/smash-run-port.md "Step 2m"): every 3DS play_se / stop_se of the ported kinds at the
    same points (smashrun_sound.SITES: enemy_fs.cro addresses), the 3DS sound rows registered in the Wii U's
    soundlabeltable at a battle's start (snd_rows), Stalfos's drop through a passable floor (3DS L5F470 in states 7 /
    8, missing from mczakostalfos)"""
    a = H.asm
    hi = lambda v: "lis r4, 0x%04X\nori r4, r4, 0x%04X" % (v >> 16, v & 0xFFFF)  # noqa: E731
    # h_se: play_se(r4 id, false) on this (r31) -> r3 handle; h_ses: stop_se(r4 handle, 0)
    a("h_se:\nmr r3, r31\nli r5, 0\nlis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctr" % (PLAY_SE >> 16,
                                                                                         PLAY_SE & 0xFFFF))
    a("h_ses:\nmr r3, r31\nli r5, 0\nlis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctr" % (STOP_SE >> 16,
                                                                                          STOP_SE & 0xFFFF))
    # the state enters with a sound (SE_EN): the enter, then play_se (the 3DS's last call in each), the handle kept
    for (n, sid), (snd, field) in sorted(SE_EN.items()):
        st('se_%s_%d' % (n, sid), "mr r3, r31\nmr r4, r29\nbl %s\n%s\nbl h_se\n%s" % (
            SE_ORIG[(n, sid)], hi(snd), "stw r3, 0x%X(r31)" % field if field else ''))
    # Shy Guy 7 update (0x1BD54): the second hop (V4 + 1, kinetic 5) plays 0x69B0002 (0x1BDD0)
    st('se_heiho_7u', "lwz r28, 0x%X(r31)\nmr r3, r31\nmr r4, r29\nbl h_ntc_up\nlwz r0, 0x%X(r31)\ncmpw r0, r28\n"
       "beq.far epi\n%s\nbl h_se" % (V(4), V(4), hi(0x69B0002)))
    # Waddle Doo 11 (the 3DS's 8) exit 0x7DD18: the beam's sound stopped if it still plays (+0x1A4 != -1)
    st('se_doo_11x', "lwz r4, 0x%X(r31)\ncmpwi r4, -1\nbeq.far epi\nbl h_ses\nli r0, -1\nstw r0, 0x%X(r31)"
       % (DO_SE, DO_SE))
    # Furiijio 4 / 7 exits (0x6D094 / 0x6D494): its effects removed (fu_bexit), the beam's sound (+0x260) stopped
    st('se_fu_bexit', "mr r3, r31\nmr r4, r29\nbl fu_bexit\nlwz r4, 0x%X(r31)\ncmpwi r4, -1\nbeq.far epi\nbl h_ses\n"
       "li r0, -1\nstw r0, 0x%X(r31)" % (FU_SE, FU_SE))
    # Furiijio slot 57 (0x6DBDC): not yet (+0x264), on the ground and the motion DownBoundEnd (4) / DownWait (6):
    # play_se(0x6A90003), +0x264 = 1; slot 69 (0x6DC48): +0x264 = 0, returns 0
    st('se_fu_57', """
        lbz r0, 0x%(B)X(r31)
        cmpwi r0, 0
        bne.far epi
        bl h_gnd
        cmpwi r3, 0
        beq.far epi
        lwz r3, 0(r31)
        lwz r3, 0x30F0(r3)
        lwz r0, 0x%(MK)X(r3)
        cmpwi r0, 4
        beq f57_s
        cmpwi r0, 6
        bne.far epi
    f57_s:
        %(ID)s
        bl h_se
        li r0, 1
        stb r0, 0x%(B)X(r31)""" % dict(B=FU_BND, MK=MOT_KIND, ID=hi(0x6A90003)))
    st('se_fu_69', "li r0, 0\nstb r0, 0x%X(r31)\nli r3, 0" % FU_BND)
    # Ghos slot 10 (the 3DS's 11, 0x11094): after the damage handling, the kinetic flag 2 and a handle (+0x200 >= 0)
    # -> stop_se, +0x200 = -1; slot 27 (the 3DS's 28, 0x11140): the handle stopped, then f_ghos_rm
    st('se_gh_dmg', """
        mr r3, r31
        mr r4, r29
        bl f_ghos_dmg
        lwz r12, 0(r31)
        lwz r12, 0x3130(r12)
        lwz r12, 8(r12)
        lwz r12, 0(r12)
        lwz r12, 0x14(r12)
        lwz r0, 0(r12)
        andi. r0, r0, 2
        beq.far epi
        lwz r4, 0x%(S)X(r31)
        cmpwi r4, 0
        blt.far epi
        bl h_ses
        li r0, -1
        stw r0, 0x%(S)X(r31)""" % dict(S=GH_SE))
    a("""
    se_gh_rm:
        mflr r0
        bl pro
        lwz r4, 0x%(S)X(r31)
        cmpwi r4, 0
        blt ghr_go
        bl h_ses
        li r0, -1
        stw r0, 0x%(S)X(r31)
    ghr_go:
        mr r3, r31
        mr r4, r29
        lmw r28, 0x20(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        b f_ghos_rm
    """ % dict(S=GH_SE))
    # Propeller Heiho: the propeller loop is one per kind (enemy_fs.cro data 0x111270 {handle -1, count 0}: ph_snd).
    # start (0x99010): count <= 0 -> play_se(0x6D20000) -> handle; count + 1. ph_dec (state 2 update 0x99D0C, slot 71
    # 0x99DD8): a handle (!= -1): count - 1, at 0 or below stop_se(handle), handle = -1
    ph = "lis r28, 0x%04X\naddi r28, r28, %d" % (ha(D['ph_snd']), sx(D['ph_snd']))
    st('se_ph_start', """
        mr r3, r31
        mr r4, r29
        bl f_ph_start
        %s
        lwz r0, 4(r28)
        cmpwi r0, 0
        bgt phs_c
        %s
        bl h_se
        stw r3, 0(r28)
    phs_c:
        lwz r12, 4(r28)
        addi r12, r12, 1
        stw r12, 4(r28)""" % (ph, hi(0x6D20000)))
    a("""
    ph_dec:
        mflr r27
        %s
        lwz r4, 0(r28)
        cmpwi r4, -1
        beq phd_o
        lwz r12, 4(r28)
        addi r12, r12, -1
        stw r12, 4(r28)
        cmpwi r12, 0
        bgt phd_o
        bl h_ses
        li r0, -1
        stw r0, 0(r28)
    phd_o:
        mtlr r27
        blr
    """ % ph)
    orig71 = VT_WORDS[0][(0xC + 8 * 71) // 4] if VT_WORDS[0] else 0
    st('se_ph_71', "stw r27, 8(r1)\nmr r3, r31\nmr r4, r29\n" + call(orig71) + "\nbl ph_dec\nlwz r27, 8(r1)")
    # state 2 update (0x99CC4): the timer +0x1F0 (PH_F) - 1 <= 0 or out of view -> the count, then -> 8 (the same test
    # made before the game's ph2_up, which then changes the state)
    st('se_ph2_up', """
        stw r27, 8(r1)
        li r28, 1
        lwz r3, 0x%(F)X(r31)
        addi r3, r3, -1
        cmpwi r3, 0
        ble ph2_c
        mr r3, r31
    """ % dict(F=PH_F) + call(IN_VIEW) + """
        li r28, 0
        cmpwi r3, 0
        bne ph2_c
        li r28, 1
    ph2_c:
        stw r28, 0xC(r1)
        mr r3, r31
        mr r4, r29
        bl ph2_up
        lwz r0, 0xC(r1)
        cmpwi r0, 0
        beq ph2_o
        bl ph_dec
    ph2_o:
        lwz r27, 8(r1)""")
    # slot 55 (0x99E24): the swap (states 4 / 5, the item held (PH_X 0), PH_S - 1 <= 0) plays 0x6D20001 (0x9A070:
    # every swap, the new item found or not)
    st('se_ph_55', """
        li r28, 0
        lwz r0, 4(r31)
        cmpwi r0, 4
        beq p55s_a
        cmpwi r0, 5
        bne p55s_c
    p55s_a:
        lwz r0, 0x%(X)X(r31)
        cmpwi r0, 0
        bne p55s_c
        lwz r3, 0x%(S)X(r31)
        addi r3, r3, -1
        cmpwi r3, 0
        bgt p55s_c
        li r28, 1
    p55s_c:
        mr r3, r31
        mr r4, r29
        bl f_ph_55
        cmpwi r28, 0
        beq.far epi
        %(ID)s
        bl h_se""" % dict(X=PH_X, S=PH_S, ID=hi(0x6D20001)))
    # Pooka slot 10 (the 3DS's 11, 0x22900): HP <= the threshold (pk_thr: max HP x P23 %%) -> play_se(0x6B10004)
    # (the hit stop / link stop of 0x22954..0x22A34: not mapped), then BehaviorImpl::notify_on_damage
    st('se_pk_dmg', "bl pk_thr\nfcmpu cr0, f2, f1\nbgt pkd_n\n%s\nbl h_se\npkd_n:\nmr r3, r31\nmr r4, r29\n%s"
       % (hi(0x6B10004), call(BI_NOTIFY_DMG)))
    # ---- snd_rows (cave_s, r3 = 1 on a Smash Run stage, 0 else): the loaded soundlabeltable ([[[[SND_MGR]] + 0x29C]
    # + 4], little-endian, 'STB\0' version 1): each 3DS row of snd_tab {row, bank id, label count, label list} written
    # where the row is empty (bank -1) or already that bank: {bank, count, the list's offset from the label base
    # (+0x10 + [+0xC]), 0}. snd_twin {row, the Smash Run kind's bank, saved}: on a Smash Run stage the twins' rows
    # 0xBE2-0xBE4 name the kinds' banks (the original id saved), on any other enemy battle the saved id is put back.
    a("""
    snd_rows:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r26, 0x18(r1)
        mr r26, r3
        lis r12, 0x%(MH)04X
        lwz r12, %(ML)d(r12)
        cmpwi r12, 0
        beq snr_o
        lwz r12, 0(r12)
        cmpwi r12, 0
        beq snr_o
        lwz r12, 0x29C(r12)
        cmpwi r12, 0
        beq snr_o
        lbz r0, 8(r12)
        cmpwi r0, 0
        beq snr_o
        lwz r31, 4(r12)
        cmpwi r31, 0
        beq snr_o
        lwz r0, 0(r31)
        lis r11, 0x5354
        ori r11, r11, 0x4200
        cmpw r0, r11
        bne snr_o
        li r11, 8
        lwbrx r30, r11, r31
        li r11, 0xC
        lwbrx r29, r11, r31
        add r29, r29, r31
        addi r29, r29, 0x10
        cmpwi r26, 0
        beq snr_tw
        lis r28, 0x%(TH)04X
        addi r28, r28, %(TL)d
    snr_l:
        lwz r3, 0(r28)
        cmpwi r3, -1
        beq snr_tw
        cmplw r3, r30
        bge snr_n
        slwi r4, r3, 4
        add r4, r4, r31
        addi r4, r4, 0x10
        lwbrx r5, r0, r4
        lwz r6, 4(r28)
        cmpwi r5, -1
        beq snr_w
        cmpw r5, r6
        bne snr_n
    snr_w:
        stwbrx r6, r0, r4
        lwz r7, 8(r28)
        li r0, 4
        stwbrx r7, r4, r0
        lwz r7, 0xC(r28)
        subf r7, r29, r7
        li r0, 8
        stwbrx r7, r4, r0
        li r0, 0
        stw r0, 0xC(r4)
    snr_n:
        addi r28, r28, 0x10
        b snr_l
    snr_tw:
        lis r28, 0x%(WH)04X
        addi r28, r28, %(WL)d
    snr_t:
        lwz r3, 0(r28)
        cmpwi r3, -1
        beq snr_o
        cmplw r3, r30
        bge snr_tn
        slwi r4, r3, 4
        add r4, r4, r31
        addi r4, r4, 0x10
        lwz r5, 8(r28)
        cmpwi r26, 0
        beq snr_back
        cmpwi r5, 0
        bne snr_set
        lwz r5, 0(r4)
        stw r5, 8(r28)
    snr_set:
        lwz r6, 4(r28)
        stwbrx r6, r0, r4
        b snr_tn
    snr_back:
        cmpwi r5, 0
        beq snr_tn
        stw r5, 0(r4)
        li r0, 0
        stw r0, 8(r28)
    snr_tn:
        addi r28, r28, 0xC
        b snr_t
    snr_o:
        lmw r26, 0x18(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    """ % dict(MH=ha(SND_MGR), ML=sx(SND_MGR), TH=ha(D['snd_tab']), TL=sx(D['snd_tab']), WH=ha(D['snd_twin']),
               WL=sx(D['snd_twin'])))
    # ---- Stalfos (kind 0x30 on mczakostalfos's AI): states 7 / 8 update (3DS 0x51D8C / 0x51FD0) as the game's
    # (0x026D3EB4 / 0x026D41E8) with the 3DS's L5F470 where the 3DS has it; the Fortress twin (0x59) runs the game's.
    # sf_drop = L5F470 (is_passable_ground, the nearest target's y + P+0xC8 x 10 below the posture's y,
    # is_exist_floor_under(100): Behavior 0x7B4230 = GroundModule ray_check from the touch position - (0, 10) along
    # (0, -100), here from the posture's position: APPROXIMATED) and, when it holds, the 3DS's set_attach_ground(0),
    # set_passable_check(1), set_correct(0), +0x1D4 = 8 -> r3 1
    pr = "lis r12, 0x102F\nlwz r12, 0x6C00(r12)\nlwz r12, 0x1C4(r12)"
    gm = "lwz r3, 0(r31)\nlwz r3, 0x30DC(r3)"
    a("""
    sf_drop:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        %(GM)s
    """ % dict(GM=gm) + call(IS_PASSABLE_GROUND) + """
        clrlwi. r3, r3, 24
        beq sfd_n
        mr r3, r31
    """ + call(NEAREST) + """
        mr r5, r3
        addi r3, r1, 8
        mr r4, r31
    """ + call(GET_TARGET_POS) + """
        %(PR)s
        lfs f0, 0xC8(r12)
        lis r12, 0x%(CH)04X
        lfs f2, %(CL)d(r12)
        lfs f1, 0xC(r1)
        fmadds f1, f0, f2, f1
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x14(r12)
        fcmpu cr0, f0, f1
        ble sfd_n
        lfs f1, 0x10(r12)
        stfs f1, 0x10(r1)
        fsubs f0, f0, f2
        stfs f0, 0x14(r1)
        li r0, 0
        stw r0, 0x18(r1)
        lis r12, 0x%(CH)04X
        lfs f0, %(CL4)d(r12)
        stfs f0, 0x1C(r1)
        %(GM)s
        addi r4, r1, 0x10
        addi r5, r1, 0x18
        addi r6, r1, 0x20
        li r7, 1
    """ % dict(PR=pr, GM=gm, CH=ha(D['sf_consts']), CL=sx(D['sf_consts']), CL4=sx(D['sf_consts'] + 4)) + call(RAY_CHECK)
      + """
        clrlwi. r3, r3, 24
        beq sfd_n
        %(GM)s
        li r4, 0
    """ % dict(GM=gm) + call(SET_ATTACH_GROUND) + "\n" + gm + "\nli r4, 1\n" + call(SET_PASSABLE) + "\n" + gm +
      "\nli r4, 0\n" + call(SET_CORRECT) + """
        li r0, 8
        stw r0, 0x1D4(r31)
        li r3, 1
        b sfd_o
    sfd_n:
        li r3, 0
    sfd_o:
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    """)
    for sid in (7, 8):
        word, orig = ST_ROW_UP[sid]
        tm = 0x188 if sid == 7 else 0x180
        a("""
        sf%(N)d_up:
            lwz r0, 8(r3)
            cmpwi r0, 0x30
            beq sf%(N)d_go
            lis r12, 0x%(OH)04X
            ori r12, r12, 0x%(OL)04X
            mtctr r12
            bctr
        sf%(N)d_go:
            mflr r0
            bl pro
            lwz r3, 0x%(TM)X(r31)
            addi r3, r3, -1
            stw r3, 0x%(TM)X(r31)
            lwz r3, 0x1B4(r31)
            addi r3, r3, -1
            stw r3, 0x1B4(r31)
        """ % dict(N=sid, OH=orig >> 16, OL=orig & 0xFFFF, TM=tm))
        if sid == 8:                     # move(input, this + 0x10) (3DS 0x52004: move(AiInput*, Vector3 const&))
            a("mr r3, r31\nmr r4, r29\naddi r5, r31, 0x10\n" + call(0x026A66DC))
        a("""
            bl h_gnd
            cmpwi r3, 0
            bne sf%(N)d_t
            li r4, 1
            b go
        sf%(N)d_t:
            lbz r0, 0x1C2(r31)
            cmpwi r0, 0
            beq sf%(N)d_a
            mr r3, r31
            li r4, 2
        """ % dict(N=sid) + call(0x026A70FC) + """
            stw r3, 0x1C8(r31)
            cmpwi r3, -1
            bne sf%(N)d_s
            li r0, 0
            stb r0, 0x1C2(r31)
            b sf%(N)d_a
        sf%(N)d_s:
            mr r3, r31
            li r4, 2
        """ % dict(N=sid) + call(0x026A706C) + """
            stw r3, 0x170(r31)
            %(PR)s
            lwz r0, 0xE8(r12)
            stw r0, 0x1A0(r31)
            li r4, 9
            b go
        sf%(N)d_a:
        """ % dict(N=sid, PR=pr))
        if sid == 7:                     # 7 only: L5F7F8(0, &out) true, out -1 -> 0x12 (0x51E50)
            a("li r0, -1\nstw r0, 8(r1)\nmr r3, r31\nli r4, 0\naddi r5, r1, 8\n" + call(ST_HELP['l5f7f8']) +
              "\ncmpwi r3, 0\nbeq sf7_b\nlwz r0, 8(r1)\ncmpwi r0, -1\nbne sf7_b\nli r4, 0x12\nb go\nsf7_b:")
        a("bl sf_drop\ncmpwi r3, 0\nbeq sf%d_c\nli r4, 1\nb go\nsf%d_c:" % (sid, sid))
        seq = ((ST_HELP['l5f3a4'], None), (ST_HELP['l5f110'], 0), (ST_HELP['l5f754'], 0)) if sid == 7 else \
            ((ST_HELP['l5f110'], 'gt'), (ST_HELP['l5f3a4'], None), (ST_HELP['l5f754'], 1))
        for fnc, arg in seq:
            if arg == 'gt':             # (+0x180 > 0)
                a("lwz r0, 0x180(r31)\nli r4, 0\ncmpwi r0, 0\nble sf8_g\nli r4, 1\nsf8_g:")
            elif arg is not None:
                a("li r4, %d" % arg)
            a("mr r3, r31\n" + call(fnc) + "\ncmpwi r3, 0\nbne.far epi")
        a("""
            bl h_wall
            cmpwi r3, 0
            bne sf%(N)d_w
            bl h_cliff
            cmpwi r3, 0
            beq sf%(N)d_e
        sf%(N)d_w:
            bl h_near
            mr r4, r3
            bl h_tchk
            cmpwi r3, 0
            bne sf%(N)d_turn
        """ % dict(N=sid))
        if sid == 8:                     # the input zeroed (0x521A8)
            a("li r0, 0\nstw r0, 0(r29)\nstw r0, 4(r29)")
        a("b sf%(N)d_e\nsf%(N)d_turn:\nli r4, 0x16\nb go\nsf%(N)d_e:" % dict(N=sid))
        if sid == 7:
            a("lwz r0, 0x188(r31)\ncmpwi r0, 0\nbgt.far epi\nli r4, 8\nb go")
        else:                            # +0x180 <= 0: L5F7F8(0, &out) true, out -1 -> 0x12
            a("lwz r0, 0x180(r31)\ncmpwi r0, 0\nbgt.far epi\nli r0, -1\nstw r0, 8(r1)\nmr r3, r31\nli r4, 0\n"
              "addi r5, r1, 8\n" + call(ST_HELP['l5f7f8']) + "\ncmpwi r3, 0\nbeq.far epi\nlwz r0, 8(r1)\n"
              "cmpwi r0, -1\nbne.far epi\nli r4, 0x12\nb go")


def code_2l(H, call, D):
    """step 2l: the Waddle Dee's parasol spawner (enemy_fs.cro 0x7C778, the article set 0x111C08 {173, 1, it}; the
    Wii U form of do_beam_cb): r3 the article, r4 the owner's accessor. node_global_position(9, &pos, true) (0x7C7B8),
    z = the GroundModule's +0x88 (3DS +0x80); the activate param (3DS offsets in brackets): +4 [+8] the position, +0x10
    [+0x14] the posture lr, +0x1C 0, +0x20 the owner's id, +0x28 its team, +0x2C the life [waddledee param +0xB0] (PSb0
    f0 120), +0x58 4, +0x60 0, +0x68 -lr (0x7C838: the weapon's init 0x0319F3FC = 3DS 0xADF64 multiplies PSb0 f1 1.0 by
    it: the parasol drifts backwards); util_activate; the members freed; returns 0"""
    H.asm("""
    wd_para_cb:
        stwu r1, -0x100(r1)
        mflr r0
        stw r0, 0x104(r1)
        stmw r29, 0xF0(r1)
        mr r31, r3
        mr r30, r4
        lis r29, 0x%(PH)04X
        addi r29, r29, %(PL)d
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lwz r3, 0x3118(r30)
        li r4, 9
        addi r5, r1, 8
        li r6, 1
    """ % dict(PH=ha(D['prm_waddledee']), PL=sx(D['prm_waddledee'])) + call(NODE_GPOS) + """
        lwz r12, 0x30DC(r30)
        lfs f0, 0x88(r12)
        stfs f0, 0x10(r1)
        lwz r12, 0x311C(r30)
        lfs f2, 0x60(r12)
        stfs f2, 0x14(r1)
        addi r3, r1, 0x18
    """ + call(ACT_PARAM) + """
        lfs f0, 8(r1)
        stfs f0, 0x1C(r1)
        lfs f0, 0xC(r1)
        stfs f0, 0x20(r1)
        lfs f0, 0x10(r1)
        stfs f0, 0x24(r1)
        lfs f0, 0x14(r1)
        stfs f0, 0x28(r1)
        fneg f0, f0
        stfs f0, 0x80(r1)
        li r0, 0
        stw r0, 0x34(r1)
        stb r0, 0x78(r1)
        stb r0, 0x84(r1)
        lwz r0, 0(r30)
        stw r0, 0x38(r1)
        lwz r0, 0xB0(r29)
        stw r0, 0x44(r1)
        li r0, 4
        stw r0, 0x70(r1)
        lwz r11, 0x%(TEAM)X(r30)
        addi r3, r11, 4
        lwz r12, 4(r11)
        lwz r12, 0x14(r12)
        mtctr r12
        bctrl
        stw r3, 0x40(r1)
        mr r3, r31
        addi r4, r1, 0x18
    """ % dict(TEAM=ACC_TEAM) + call(UTIL_ACTIVATE) + """
        addi r3, r1, 0x60
        li r4, 2
    """ + call(ACT_PARAM_FREE) + """
        addi r3, r1, 0x54
        li r4, 2
    """ + call(ACT_PARAM_FREE) + """
        li r3, 0
        lmw r29, 0xF0(r1)
        lwz r0, 0x104(r1)
        mtlr r0
        addi r1, r1, 0x100
        blr
    """)


def code_2k(H, st, call, d, D):
    """step 2k (region H): the Waddle Doo's beam (3DS states 7 / 8, the article's spawner), the Churine's sleep powder
    (states 6 / 7, its search, slot 69), the twins' params re-read from their own files; enemy_fs.cro addresses in the
    comments, docs/smash-run-port.md "Step 2k" """
    p = dict(d, SC=DO_SC, CD=DO_CD, TK=DO_TK, IX=DO_IX, ANG=DO_ANG, AIR=DO_AIR, LV=CF['LEAVE'], LST=CF['LANDST'], SE=DO_SE)
    a = lambda text: H.asm(text % p)  # noqa: E731
    # ---- Waddle Doo. The beam's search (fall 1 0x7D258, walk 3 0x7D5D0, jump 6 0x7D350; the wall hop 5 has none):
    # +0x16C (DO_SC) + 1 > search_interval(1) (20): the cool-down +0x180 (DO_CD) - 1 < 0: DO_SC = 0, search_target(1)
    # (60 x 70 at (30, 20)) found: walk: the leave timer +0x184 (V7) = PS8c f0 600 (0x7D62C); air: +0x19D = 1; => 7
    # (here 10). r28: 0 walk (not found: the turn search ow_look), 1 air (not found: done)
    a("""
    do_bsw:
        li r28, 0
        b do_bsrch
    do_bsa:
        li r28, 1
    do_bsrch:
        lwz r3, 0x%(SC)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(SC)X(r31)
        li r4, 1
        bl h_grp
        lwz r0, 0x%(SC)X(r31)
        cmpw r3, r0
        bge dbs_no
        lwz r3, 0x%(CD)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(CD)X(r31)
        cmpwi r3, 0
        bge dbs_no
        li r0, 0
        stw r0, 0x%(SC)X(r31)
        li r4, 1
        bl h_srch
        cmpwi r3, -1
        beq dbs_no
        cmpwi r28, 0
        bne dbs_air
        lwz r0, 0x%(LV)X(r30)
        stw r0, 0x%(V7)X(r31)
        b dbs_go
    dbs_air:
        li r0, 1
        stw r0, 0x%(AIR)X(r31)
    dbs_go:
        li r4, 10
        b go
    dbs_no:
        cmpwi r28, 0
        bne.far epi
        b ow_look
    """)
    # 1 fall (0x7D21C): on the ground => 2 (interrupt; no speed test), else the beam's search in the air
    st('do_fall_up', "bl h_gnd\ncmpwi r3, 0\nbeq do_bsa\nlwz r4, 0x%(LST)X(r30)\nb goi" % p)
    # charged / firing in the air (+0x19D): landing -> kinetic 0, ground on, the flag off (0x7DEF4 / 0x7DB0C)
    a("""
    do_land0:
        mflr r0
        stw r0, 0x1C(r1)
        lwz r0, 0x%(AIR)X(r31)
        cmpwi r0, 0
        beq dl0_o
        bl h_gnd
        cmpwi r3, 0
        beq dl0_o
        li r4, 0
        bl h_kin
        li r4, 1
        bl h_att
        li r0, 0
        stw r0, 0x%(AIR)X(r31)
    dl0_o:
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """)
    # 7 (here 10) the charge (0x7DD40 / 0x7DEEC): on the ground kinetic 0 and ground on; BeamShotHold at PS8c f3 (1.0);
    # its end => 8 (here 11)
    st('do_ch_en', """
        lwz r0, 0x%(AIR)X(r31)
        cmpwi r0, 0
        bne dch_m
        li r4, 0
        bl h_kin
        li r4, 1
        bl h_att
    dch_m:
        li r4, 1
        li r5, 0
        lfs f2, 0x%(P10)X(r30)
        bl h_mot""" % p)
    st('do_ch_up', "bl do_land0\nbl h_end\ncmpwi r3, 0\nbeq.far epi\nli r4, 11\nb go")
    # 8 (here 11) the beam (0x7D060 / 0x7DB04): BeamShot at PS8c f4 (4.0); 180 / f9 = 7 shots; the cool-down = f5
    # (150); each frame while shots remain: the wait +0x174 - 1 < 0: wait = f8 (2), generate_article_angle(0, (30 - f9 n)
    # x lr, false), n + 1 (0x7DBD4: a fan from 30 down to -120 degrees, 0 = up); all shot and the motion's end => 3.
    # play_se(0x6A80000) / stop_se (0x7D0D4 / 0x7DC18 / exit 0x7DD18): with the sounds (not this step)
    st('do_bm_en', """
        li r4, 0
        li r5, 0
        lfs f2, 0x%(P11)X(r30)
        bl h_mot
        li r0, 0
        stw r0, 0x%(TK)X(r31)
        stw r0, 0x%(IX)X(r31)
        lwz r0, 0x%(P16)X(r30)
        stw r0, 0x%(ANG)X(r31)
        lwz r0, 0x%(P12)X(r30)
        stw r0, 0x%(CD)X(r31)""" % p)
    st('do_bm_up', """
        bl do_land0
        lwz r3, 0x%(IX)X(r31)
        lwz r0, 0x%(P15)X(r30)
        cmpw r0, r3
        ble dbm_end
        lwz r3, 0x%(TK)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(TK)X(r31)
        cmpwi r3, 0
        bge.far epi
        lwz r0, 0x%(P13)X(r30)
        stw r0, 0x%(TK)X(r31)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x60(r12)
        lfs f1, 0x%(ANG)X(r31)
        fmuls f1, f1, f0
        lfs f0, 0x%(P14)X(r30)
        lfs f2, 0x%(ANG)X(r31)
        fsubs f2, f2, f0
        stfs f2, 0x%(ANG)X(r31)
        mr r3, r31
        li r4, 0
        li r5, 0
    """ % p + call(GEN_ART_ANGLE) + """
        lwz r3, 0x%(IX)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(IX)X(r31)
        b epi
    dbm_end:
        bl h_end
        cmpwi r3, 0
        beq.far epi
        lwz r4, 0x%(SE)X(r31)
        cmpwi r4, -1
        beq dbm_go
        bl h_ses
        li r0, -1
        stw r0, 0x%(SE)X(r31)
    dbm_go:
        li r4, 3
        b go""" % p)
    # the article's spawner (the 3DS article data set's 0x7DDB0; the Wii U form of mczakoplasmawisp's 0x026CF644):
    # r3 the article, r4 the owner's accessor. The position: node 3's global position + (PS8c f6 9 x lr, f7 0.75), z =
    # the GroundModule's +0x88 (3DS +0x80); the activate param: +4 position, +0x10 lr, +0x1C 0, +0x20 the owner's id,
    # +0x28 its team, +0x2C the life PSc4 f0 (8), +0x58 4, +0x60 0, +0x68 the angle (the AI energy's +0x54, set by
    # generate_article_angle); util_activate. The weapon's own init (0x0319FE98) then reads the speed PSc4 f1 (4) along
    # the angle, the attack P7[0] (2 %%, angle 361, kbg 100, fixed 100, size 1) and the effect 0x7190000 at PSc4 f2 (0.5)
    a("""
    do_beam_cb:
        stwu r1, -0x100(r1)
        mflr r0
        stw r0, 0x104(r1)
        stmw r29, 0xF0(r1)
        mr r31, r3
        mr r30, r4
        lis r29, 0x%(WH)04X
        addi r29, r29, %(WL)d
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lwz r3, 0x3118(r30)
        li r4, 3
        addi r5, r1, 8
        li r6, 1
    """ % dict(p, WH=ha(D['wdp']), WL=sx(D['wdp'])) + call(NODE_GPOS) + """
        lfs f0, 0xC(r1)
        lfs f1, 0xA8(r29)
        fadds f0, f0, f1
        stfs f0, 0xC(r1)
        lwz r12, 0x311C(r30)
        lfs f2, 0x60(r12)
        stfs f2, 0x14(r1)
        lfs f0, 8(r1)
        lfs f1, 0xA4(r29)
        fmadds f0, f2, f1, f0
        stfs f0, 8(r1)
        lwz r12, 0x30DC(r30)
        lfs f0, 0x88(r12)
        stfs f0, 0x10(r1)
        addi r3, r1, 0x18
    """ + call(ACT_PARAM) + """
        lfs f0, 8(r1)
        stfs f0, 0x1C(r1)
        lfs f0, 0xC(r1)
        stfs f0, 0x20(r1)
        lfs f0, 0x10(r1)
        stfs f0, 0x24(r1)
        lfs f0, 0x14(r1)
        stfs f0, 0x28(r1)
        li r0, 0
        stw r0, 0x34(r1)
        stb r0, 0x78(r1)
        stb r0, 0x84(r1)
        lwz r0, 0(r30)
        stw r0, 0x38(r1)
        lwz r0, 0xC4(r29)
        stw r0, 0x44(r1)
        li r0, 4
        stw r0, 0x70(r1)
        lwz r12, 0x3130(r30)
        lwz r12, 8(r12)
        lwz r12, 0(r12)
        lwz r12, 4(r12)
        lwz r0, 0x54(r12)
        stw r0, 0x80(r1)
        lwz r11, 0x%(TEAM)X(r30)
        addi r3, r11, 4
        lwz r12, 4(r11)
        lwz r12, 0x14(r12)
        mtctr r12
        bctrl
        stw r3, 0x40(r1)
        mr r3, r31
        addi r4, r1, 0x18
    """ % dict(TEAM=ACC_TEAM) + call(UTIL_ACTIVATE) + """
        addi r3, r1, 0x60
        li r4, 2
    """ + call(ACT_PARAM_FREE) + """
        addi r3, r1, 0x54
        li r4, 2
    """ + call(ACT_PARAM_FREE) + """
        li r3, 0
        lmw r29, 0xF0(r1)
        lwz r0, 0x104(r1)
        mtlr r0
        addi r1, r1, 0x100
        blr
    """)
    # ---- Churine (V0 +0x168 the search wait, V1 +0x16C the cool-down, V2 +0x170 a target to turn to, V3 +0x171 the
    # first frame, V5 +0x17C the powder effect, V6 +0x180 the powder's frames). The walk's search (0x3D76C, after the
    # ground / wall / ledge tests): V0 > 0: - 1; V1 > 0: - 1, still > 0: skip; V0 <= 0: search_target(0) (100 x 35 at
    # (5, 5)): found: behind -> V2 = 1, => 5 (turn) / => 6 (here 8); not found: V0 = search_interval(0) (3). Then (the
    # 3DS's +0x171, set by its start 0x3D064) the first frame => 6 (here 8) once.
    a("""
    ch_srch:
        lwz r3, 0x%(V0)X(r31)
        cmpwi r3, 0
        ble chs_cd
        addi r3, r3, -1
        stw r3, 0x%(V0)X(r31)
    chs_cd:
        lwz r3, 0x%(V1)X(r31)
        cmpwi r3, 0
        ble chs_w
        addi r3, r3, -1
        stw r3, 0x%(V1)X(r31)
        cmpwi r3, 0
        bgt chs_ff
    chs_w:
        lwz r3, 0x%(V0)X(r31)
        cmpwi r3, 0
        bgt chs_ff
        li r4, 0
        bl h_srch
        cmpwi r3, -1
        beq chs_nf
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        beq chs_atk
        li r0, 1
        stw r0, 0x%(V2)X(r31)
        li r4, 5
        b go
    chs_atk:
        li r4, 8
        b go
    chs_nf:
        li r4, 0
        bl h_grp
        stw r3, 0x%(V0)X(r31)
    chs_ff:
        lwz r0, 0x%(V3)X(r31)
        cmpwi r0, 0
        beq.far epi
        li r4, 8
        bl h_chg
        li r0, 0
        stw r0, 0x%(V3)X(r31)
        b epi
    """)
    # start (0x3CFF8): the walker's, then +0x171 = 1
    st('ch_start', "mr r3, r31\nmr r4, r29\nbl w_start\nli r0, 1\nstw r0, 0x%(V3)X(r31)" % p)
    # 5 turn (0x3D660): at the end reverse_lr, => 6 (here 8) if V2 else => 3 (interrupt), V2 = 0
    st('ch_turn_up', """
        bl h_end
        cmpwi r3, 0
        beq.far epi
        bl h_rev
        lwz r0, 0x%(V2)X(r31)
        li r4, 3
        cmpwi r0, 0
        beq cht_go
        li r4, 8
    cht_go:
        li r0, 0
        stw r0, 0x%(V2)X(r31)
        b goi""" % p)
    # 6 (here 8) the attack hop (0x3DBF0 / 0x3DD14): clear_speed_all, W+0x20 0, +0x24 P0 f9 (1), +0x28 / +0x2C 10, +0x1C
    # 0, kinetic 5, ground off, Jump at 1 (once); each frame the stick (lr, 1); speed y <= 0 on the ground => 7 (here
    # 9, interrupt)
    st('ch_hop_en', """
        bl h_clear
        bl h_ebase
        li r0, 0
        stw r0, 0x20(r10)
        stw r0, 0x1C(r10)
        lwz r0, 0x%(P0)X(r30)
        stw r0, 0x24(r10)
        lwz r0, 0x%(P1)X(r30)
        stw r0, 0x28(r10)
        stw r0, 0x2C(r10)
        li r4, 5
        bl h_kin
        li r4, 0
        bl h_att
        li r4, 7
        li r5, 0
        bl h_mot1""" % p)
    st('ch_hop_up', """
        lwz r0, 0x10(r31)
        stw r0, 0(r29)
        lis r12, 0x%(CH)04X
        lfs f0, %(C1)d(r12)
        stfs f0, 4(r29)
        bl h_vy0
        bgt.far epi
        bl h_gnd
        cmpwi r3, 0
        beq.far epi
        li r4, 9
        b goi""" % dict(p, C1=sx(D['consts'] + 4)))
    # 7 (here 9) the powder (0x3D3B4 / 0x3D970): kinetic 0, clear_speed_all, ground on, SleepPowder at 1 (once: its
    # ACMD, the converted attack.bin, arms the sleep hitboxes at frames 50 / 70 to 125), V6 = 0. Each frame V6 + 1; on
    # the ground: with the effect: gone (is_exist) -> V5 = 0, => 5, the cool-down V1 = P0 f13 (210); without it: from
    # frame P0 f12 (40) request_follow_effect(0x71F0000, node 1, (f7, f8, 0) = (0, 5, 0), (90 - 90 lr, -90, 0), f11 1)
    # -> V5, EffectModule set_rate_last(f10 1.4) (play_se(0x6B00001): with the sounds); off the ground: the effect
    # removed, => 1
    st('ch_pw_en', """
        li r4, 0
        bl h_kin
        bl h_clear
        li r4, 1
        bl h_att
        li r4, 9
        li r5, 0
        bl h_mot1
        li r0, 0
        stw r0, 0x%(V6)X(r31)""" % p)
    st('ch_pw_up', """
        lwz r3, 0x%(V6)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(V6)X(r31)
        bl h_gnd
        cmpwi r3, 0
        beq chp_air
        lwz r3, 0x%(V5)X(r31)
        cmpwi r3, 0
        beq chp_req
    """ % p + call(EFF_EXIST) + """
        cmpwi r3, 0
        bne.far epi
        li r0, 0
        stw r0, 0x%(V5)X(r31)
        li r4, 5
        bl h_chg
        lwz r0, 0x%(P7)X(r30)
        stw r0, 0x%(V1)X(r31)
        b epi
    chp_req:
        lwz r0, 0x%(P2)X(r30)
        lwz r3, 0x%(V6)X(r31)
        cmpw r0, r3
        bgt.far epi
        lwz r0, 0x%(P3)X(r30)
        stw r0, 8(r1)
        lwz r0, 0x%(P4)X(r30)
        stw r0, 0xC(r1)
        li r0, 0
        stw r0, 0x10(r1)
        stw r0, 0x1C(r1)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x60(r12)
        lfs f1, 0x%(P8)X(r30)
        fmuls f0, f0, f1
        fsubs f0, f1, f0
        stfs f0, 0x14(r1)
        lwz r0, 0x%(P9)X(r30)
        stw r0, 0x18(r1)
        mr r3, r31
        lis r4, 0x71F
        li r5, 1
        addi r6, r1, 8
        addi r7, r1, 0x14
        lfs f1, 0x%(P5)X(r30)
    """ % p + call(REQ_FOLLOW) + """
        stw r3, 0x%(V5)X(r31)
        lwz r3, 0(r31)
        lwz r3, 0x30D8(r3)
        lfs f1, 0x%(P6)X(r30)
    """ % p + call(EFF_RATE_LAST) + """
        lis r4, 0x6B0
        ori r4, r4, 1
        bl h_se
        b epi
    chp_air:
        bl ch_rmfx
        li r4, 1
        b go""")
    a("""
    ch_rmfx:
        lwz r4, 0x%(V5)X(r31)
        cmpwi r4, 0
        beqlr
        mflr r0
        stw r0, 0x1C(r1)
        mr r3, r31
    """ % p + call(REMOVE_EFFECT) + """
        li r0, 0
        stw r0, 0x%(V5)X(r31)
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """ % p)
    # slot 69 (0x3DDE8): in 7 (here 9) the effect removed; returns 0. 8 (here 6, dead) enter 0x3D36C: the same
    st('ch_69', "lwz r0, 4(r31)\ncmpwi r0, 9\nbne ch69_o\nbl ch_rmfx\nch69_o:\nli r3, 0")
    st('ch_dead_en', "bl ch_rmfx\nmr r3, r31\nmr r4, r29\nbl g_dead_en")
    # ---- White Bear: start 0x7E378 set_weak_param(5, P0 f19 2.0) -> 3DS DamageModuleImpl::set_weak_param 0x4D34C4 ->
    # its transactor ([DM+0x68]) vt+0x84 0x5F6D44: one {kind 5, x2.0} entry; read by the transactor's vt+0x90 0x966BE8
    # (through DamageModule 0x4D3020): a hit whose AttackData attribute byte +0x43 is the entry's kind takes its
    # damage x the multiplier. The Wii U's transactor has neither (no twin of 0x5F6D44 / 0x5F6D6C / 0x966BE8; its
    # DamageModule slot 38 0x02C23550 forwards to vt+0x124 like 0x4D3020): here slot 31 (the hit record, r4: +0x14
    # the AttackData) notes a hit of attribute P15 (5, fire) in WB_W, and slot 10 (notify_on_damage, after the damage
    # is added) adds that hit's damage once more x (P16 - 1): damage(0) - WB_D (the damage before it), through
    # set_current_damage (HP W+0 = max - damage), then BehaviorImpl's notify_on_damage (its defeat test sees it)
    a("""
    wb_31:
        lwz r12, 0x14(r4)
        li r0, 0
        cmpwi r12, 0
        beq wb31_s
        lbz r11, 0x43(r12)
        lwz r12, 0x168(r3)
        lwz r12, 0x%(P15)X(r12)
        cmpw r11, r12
        bne wb31_s
        li r0, 1
    wb31_s:
        stw r0, 0x%(WBW)X(r3)
        lis r12, 0x%(B31H)04X
        ori r12, r12, 0x%(B31L)04X
        mtctr r12
        bctr
    """ % dict(p, WBW=WB_W, B31H=BI_SLOT31 >> 16, B31L=BI_SLOT31 & 0xFFFF))
    st('wb_dmg', """
        lwz r0, 0x%(WBW)X(r31)
        cmpwi r0, 0
        beq wbd_n
        li r0, 0
        stw r0, 0x%(WBW)X(r31)
        lwz r3, 0(r31)
        lwz r3, 0x30D4(r3)
        li r4, 0
    """ % dict(p, WBW=WB_W) + call(GET_DAMAGE) + """
        lfs f0, 0x%(WBD)X(r31)
        fsubs f2, f1, f0
        lis r12, 0x%(CH)04X
        lfs f0, %(CL)d(r12)
        fcmpu cr0, f2, f0
        ble wbd_n
        lfs f3, 0x%(P16)X(r30)
        lfs f0, %(C1)d(r12)
        fsubs f3, f3, f0
        fmadds f1, f2, f3, f1
        mr r3, r31
    """ % dict(p, WBD=WB_D, C1=sx(D['consts'] + 4)) + call(SET_CUR_DAMAGE) + """
    wbd_n:
        lwz r3, 0(r31)
        lwz r3, 0x30D4(r3)
        li r4, 0
    """ + call(GET_DAMAGE) + """
        stfs f1, 0x%(WBD)X(r31)
        mr r3, r31
    """ % dict(WBD=WB_D) + call(BI_NOTIFY_DMG))
    # ---- the battle load (cave_t / cave_s, on a Smash Run stage): the Waddle Doo's article set (the beam, kind 0xAF,
    # max 5: the 3DS's enemy_article_data_set_waddledoo {175, 5, 0x7DDB0}) and its param slot (the static object)
    # are written there; k2_twins: the twins' param objects re-read from the Smash Run kinds' own files (below)
    code_2k_twins(H, call, p, D)


def code_2k_twins(H, call, p, D):
    """k2_twins (from cave_s on a Smash Run stage, after the param load and step 2a's slot[K] = slot[twin]): for each
    twin 0x57-0x5A whose Smash Run kind's own file (param/enemy/fs/enemy_param_vl_<K>.bin: the 3DS values in the
    twin's sm layout, tools/smashrun_twin_params.py) is found, a new object of the twin's class (its ctor with no
    object allocates one, as the sm accessor's vt+0x14 builds them) parsed from it with the twin's own parser (the
    call its vt+0x24 makes for the sm file); if the parse was clean (step 2o: the loader's +8 byte, TWIN_LOADER) and
    it holds attacks (+0x30, the base layout's attack count, > 0): slot[K] = it, and slot[twin] = it too (the twins'
    AIs read their own slot hard-coded: 31 / 31 / 44 sites) but for zima, whose slot the walkers borrow (step 2b's
    donor: its own object stays; the 7 hard-coded zima reads, +0xC and +0x7C..+0x90, read values the 3DS file and the
    Wii U file share).
    Step 2o (the user's code_diag_novis crash: Lethinium's cannon shot, article 3, weapon init 0x02AE050C, read
    [slot 0x57]+0x19C, the G8 vector's elements, as 0 and faulted at 0x02AE06B4; its G2 attacks were there, the
    twin had fought for 7 s):
    - a parse error no longer passes: step 2a's 3DS-layout file (the same path) parses G0-G5 and stops at G5 (the
      3DS has 8 words fewer), leaving G6-G8 (needles / laser / cannon) empty with +0x30 = 4, and step 2k took it.
      Every twin's 3DS-layout file fails the same way (loader +8 = 0; zima from G1, darios at its G6, stalfos
      parses its vectors but not its tail), the shipped files parse clean (unicorn, the game's own code);
    - an object is deleted (the twin's dtor with 1) only once its replacement is in the slots; when the file isn't
      there or doesn't parse, the previous object (k2_objs) stays and is put back in the slots (step 2k deleted
      first: a run that then found no file left the slots on a freed object; 0x02D9A5EC has two callers, 0x02FB6894
      and the scene method 0x02FD94B0)."""
    a = lambda text: H.asm(text)  # noqa: E731
    a("""
    k2_twins:
        stwu r1, -0x60(r1)
        mflr r0
        stw r0, 0x64(r1)
        stmw r26, 0x48(r1)
        lis r29, 0x%04X
        addi r29, r29, %d
    """ % (ha(D['k2_objs']), sx(D['k2_objs'])))
    a("""
        lis r28, 0x%04X
        lwz r28, %d(r28)
        cmpwi r28, 0
        beq k2t_o
        addi r3, r1, 0xC
        lis r4, 0x%04X
        addi r4, r4, %d
        li r5, 1
    """ % (ha(PARAM_MGR), sx(PARAM_MGR), ha(D['k2_dir']), sx(D['k2_dir'])) + call(RES_DIR) + """
        addi r3, r1, 0xC
        li r4, 1
    """ + call(RES_DIR2))
    for i, (t, k) in enumerate(TWIN_K):
        kind = KIND_OF[k]
        a("""
        addi r3, r1, 0xC
        addi r4, r1, 8
        lis r5, 0x%04X
        addi r5, r5, %d
        li r6, 0
        """ % (ha(D['k2_' + k]), sx(D['k2_' + k])) + call(RES_JOIN) + """
        lwz r0, 8(r1)
        cmpwi r0, 0
        beq k2t_%x_f
        addi r3, r1, 0x10
        """ % t + call(RES_NEW) + """
        mr r4, r3
        li r3, 0
        """ + call(TWIN_CTOR[t]) + """
        mr. r30, r3
        addi r3, r1, 0x10
        li r4, 2
        """ + call(RES_FREE) + """
        cmpwi r30, 0
        beq k2t_%x_f
        addi r3, r1, 8
        mr r4, r30
        """ % t + call(TWIN_PARSE[t]) + """
        lbz r0, 0x%X(r30)
        cmpwi r0, 1
        bne k2t_%x_bad
        lwz r0, 0x30(r30)
        cmpwi r0, 0
        bgt k2t_%x_ok
    k2t_%x_bad:
        mr r3, r30
        li r4, 1
        """ % (TWIN_LOADER[t] + 8, t, t, t) + call(TWIN_DTOR[t]) + """
        b k2t_%x_f
    k2t_%x_ok:
        lwz r27, %d(r29)
        stw r30, %d(r29)
        stw r30, 0x%X(r28)
        %s
        cmpwi r27, 0
        beq k2t_%x_h
        cmpw r27, r30
        beq k2t_%x_h
        mr r3, r27
        li r4, 1
        """ % (t, t, 4 * i, 4 * i, SLOTS + 4 * kind, '' if t == 0x5A else 'stw r30, 0x%X(r28)' % (SLOTS + 4 * t), t, t)
          + call(TWIN_DTOR[t]) + """
        b k2t_%x_h
    k2t_%x_f:
        lwz r27, %d(r29)
        cmpwi r27, 0
        beq k2t_%x_h
        stw r27, 0x%X(r28)
        %s
    k2t_%x_h:
        addi r3, r1, 8
        li r4, 2
        """ % (t, t, 4 * i, t, SLOTS + 4 * kind, '' if t == 0x5A else 'stw r27, 0x%X(r28)' % (SLOTS + 4 * t), t)
          + call(RES_FREE))
    a("""
        addi r3, r1, 0xC
        li r4, 2
    """ + call(RES_FREE) + """
    k2t_o:
        lmw r26, 0x48(r1)
        lwz r0, 0x64(r1)
        mtlr r0
        addi r1, r1, 0x60
        blr
    """)


def code_h(D):
    """step 2h (region H): the stomp bounce multiplier (u_bounce / u_pend) and the four kinds' states (Big Goomba
    dk_*, ...). 3DS enemy_fs.cro addresses in the comments; docs/smash-run-port.md "Step 2h"."""
    H = Asm(CAVE_H)

    def call(t):
        return "lis r12, 0x%04X\nori r12, r12, 0x%04X\nmtctr r12\nbctrl" % (t >> 16, t & 0xFFFF)

    def st(label, body):
        H.asm("%s:\nmflr r0\nbl pro\n%s\nb epi" % (label, body))

    def en(label, kin, att, mot, loop, rate=None, extra='', pre=''):
        r = "bl h_mot1" if rate is None else "lfs f2, 0x%X(r30)\nbl h_mot" % rate
        st(label, "%s\nli r4, %d\nbl h_kin\nli r4, %d\nbl h_att\nli r4, %d\nli r5, %d\n%s\n%s"
           % (pre, kin, att, mot, loop, r, extra))

    d = dict(PH=ha(D['pend']), PL=sx(D['pend']), CH=ha(D['consts']), CL=sx(D['consts']), BOUNCE=CF['BOUNCE'],
             SF=WM_SET_FLOAT, SI=WM_SET_INT, SK=STATUS_KIND, FTH=F_TREAD_MUL >> 16, FTL=F_TREAD_MUL & 0xFFFF,
             ICH=I_STEP_COUNT >> 16, ICL=I_STEP_COUNT & 0xFFFF, N=PEND_N, STEP=STEP_JUMP, ZERO=CF['ZERO'],
             BIH=BO_ID_INVALID >> 16, ITH=I_TREAD_TARGET >> 16, ITL=I_TREAD_TARGET & 0xFFFF,
             DF=DEFEATED, **{'V%d' % i: V(i) for i in range(9)}, **{'P%d' % i: P(i) for i in range(80)})
    a = lambda text: H.asm(text % d)  # noqa: E731

    # ---- the stomp bounce (the tread link event's answer, emulated). The fighter's StepJump (status 0xB3) sends
    # LinkEvent 6 to the stepped object only through link 3 (common MSC func_1149); the enemy answers its param 0x11
    # (Enemy event 6, 0x02D8C5D4: WorkModule acc+0x315C vt+0x44(0x11) = work float 0x11 = W+0x44, the value each
    # kind's 3DS initialize writes there, the Enemy ctor's default 1.0 otherwise) and the MSC copies it into status
    # float 0x1000006 and zeroes the step count int 0x10000006; the jump's speed (0x02E79938, 3DS 0x97E080) is
    # step_jump_speed_y x float 0x1000006. Our stomp has no link: u_bounce writes the two itself (CFG BOUNCE, else
    # W+0x44), now and (u_pend) on each cave-enemy update while the fighter is in 0xB3, until it leaves it.
    # Step 2p: and the fighter's tread target int 0x10000008 = BO_ID_INVALID, so that StepJump's func_1149 (which
    # links to whatever object that int names and copies its event 6 answer over float 0x1000006) is skipped: the
    # step 2o log showed a stale target zeroing the Big Goomba's bounce (hs fst=B, then the fall from rest) and the
    # stepped enemy's own id treading it twice (Goomba 8 -> 8, Paratroopa 9 -> 19, Big Goomba 10 -> 12).
    a("""
    u_bounce:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        lfs f1, 0x%(BOUNCE)X(r30)
        lis r12, 0x%(CH)04X
        lfs f0, %(CL)d(r12)
        fcmpu cr0, f1, f0
        bne ubn_have
        lwz r12, 0(r31)
        lwz r12, 0x3130(r12)
        lwz r12, 8(r12)
        lwz r12, 0(r12)
        lwz r12, 4(r12)
        lfs f1, 0x44(r12)
    ubn_have:
        lis r12, 0x%(PH)04X
        addi r12, r12, %(PL)d
        mulli r11, r25, 12
        add r12, r12, r11
        stw r24, 0(r12)
        stfs f1, 4(r12)
        li r0, %(N)d
        stw r0, 8(r12)
        mr r3, r24
        bl ub_set
        lwz r3, 0x28(r24)
        lwz r12, 0(r3)
        lwz r12, 0x%(SI)X(r12)
        mtctr r12
        li r4, 0
        lis r5, 0x%(ICH)04X
        ori r5, r5, 0x%(ICL)04X
        bctrl
        lwz r3, 0x28(r24)
        lwz r12, 0(r3)
        lwz r12, 0x%(SI)X(r12)
        mtctr r12
        lis r4, 0x%(BIH)04X
        lis r5, 0x%(ITH)04X
        ori r5, r5, 0x%(ITL)04X
        bctrl
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    ub_set:
        lwz r3, 0x28(r3)
        lwz r12, 0(r3)
        lwz r12, 0x%(SF)X(r12)
        mtctr r12
        lis r4, 0x%(FTH)04X
        ori r4, r4, 0x%(FTL)04X
        bctr
    u_pend:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        li r28, 0
    upd_loop:
        lis r27, 0x%(PH)04X
        addi r27, r27, %(PL)d
        mulli r0, r28, 12
        add r27, r27, r0
        lwz r10, 8(r27)
        clrlwi. r11, r10, 16
        beq upd_next
        addi r10, r10, -1
        stw r10, 8(r27)
        lwz r3, 0(r27)
        lwz r12, 0x20(r3)
        lwz r12, 0x%(SK)X(r12)
        cmpwi r12, 0x%(STEP)X
        bne upd_left
        oris r10, r10, 1
        stw r10, 8(r27)
        lfs f1, 4(r27)
        bl ub_set
        b upd_next
    upd_left:
        rlwinm. r10, r10, 0, 15, 15
        beq upd_next
        li r0, 0
        stw r0, 8(r27)
    upd_next:
        addi r28, r28, 1
        cmplwi r28, 4
        blt upd_loop
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        b u_vis                     # step 2i: the material-animation kinds' meshes
    """)

    # ---- Big Goomba (dekakuribo 0x23). V0 the state frames, V1 the run frames (+0x178), V2 the run start's
    # airborne flag (+0x181), V3 the target, V4 the close count (+0x184), V5 WalkL's loop phase (float), V6 the walk's
    # turn flag (+0x180). P0-19 its P0 row, P20 WalkL's frames, P21-23 f19 / f10 / f13 as ints
    quake = "mr r3, r31\nli r4, 3\n" + call(REQ_QUAKE)
    # 2 landing (0x85E30 / 0x864E0): kinetic 0, ground on, Landing, request_quake(3) (play_se 0x2910009: not ported);
    # at its end -> 3 (g_land_up)
    en('dk_land_en', 0, 1, 12, 0, extra=quake)
    # 3 walk (0x85F3C / 0x8675C)
    en('dk_walk_en', 0xA, 1, 17, 1, rate=P(4), pre="li r0, 0\nstw r0, 0x%X(r31)\nstw r0, 0x%X(r31)\nstw r0, 0x%X(r31)"
       % (V(0), V(5), V(6)))
    a("""
    dk_loop:
        lfs f1, 0x%(V5)X(r31)
        lfs f0, 0x%(P4)X(r30)
        fadds f1, f1, f0
        lfs f0, 0x%(P20)X(r30)
        li r3, 0
        fcmpu cr0, f1, f0
        blt dkl_st
        fsubs f1, f1, f0
        li r3, 1
    dkl_st:
        stfs f1, 0x%(V5)X(r31)
        blr
    dk_dist2:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        mr r5, r4
        addi r3, r1, 8
        mr r4, r31
    """ + call(GET_TARGET_POS) + """
        lfs f1, 8(r1)
        lfs f2, 0xC(r1)
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f0, 0x10(r12)
        fsubs f1, f1, f0
        lfs f0, 0x14(r12)
        fsubs f2, f2, f0
        fmuls f1, f1, f1
        fmadds f1, f2, f2, f1
        b h_ret20
    """)
    st('dk_walk_up', """
        lwz r0, 0x%(V6)X(r31)
        cmpwi r0, 0
        beq dkw_srch
        bl dk_loop
        cmpwi r3, 0
        bne dkw_rev
        bl h_clear
        b dkw_cnt
    dkw_rev:
        bl h_rev
        li r4, 3
        b goi
    dkw_srch:
        bl dk_loop
        li r4, 0
        bl h_grp
        lwz r10, 0x%(V0)X(r31)
        addi r0, r10, 1
        divwu r11, r0, r3
        mullw r11, r11, r3
        subf. r0, r11, r0
        bne dkw_gnd
        li r4, 0
        bl h_srch
        stw r3, 0x%(V3)X(r31)
        cmpwi r3, 0
        blt dkw_gnd
        mr r4, r3
        bl h_dx
        lfs f0, 0x%(ZERO)X(r30)
        fcmpu cr0, f1, f0
        bge dkw_face
        bl h_rev
    dkw_face:
        lwz r4, 0x%(V3)X(r31)
        bl dk_dist2
        lfs f0, 0x%(P18)X(r30)
        fmuls f0, f0, f0
        fcmpu cr0, f1, f0
        li r4, 4
        ble.far go
        li r4, 6
        b go
    dkw_gnd:
        bl h_gnd
        cmpwi r3, 0
        bne dkw_on
        li r4, 1
        bl h_chg
        b dkw_cnt
    dkw_on:
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        bne dkw_wall
        bl h_cliff
        cmpwi r3, 0
        bne dkw_flag
    dkw_wall:
        bl k_wallt
        cmpwi r3, 0
        beq dkw_cnt
    dkw_flag:
        li r0, 1
        stw r0, 0x%(V6)X(r31)
    dkw_cnt:
        bl h_mv
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(V0)X(r31)""" % d)
    # 4 close (0x86240 / 0x86B6C): W+0x24 / +0x2C = P16 / P17 (0), kinetic 5, ground off, Fall loop, V4 = 1; on the
    # ground: V4 < 3 -> kinetic 5 again, V4++; else -> 5
    en('dk_close_en', 5, 0, 11, 1, pre="bl h_ebase\nlwz r0, 0x%X(r30)\nstw r0, 0x24(r10)\nlwz r0, 0x%X(r30)\n"
       "stw r0, 0x2C(r10)\nli r0, 1\nstw r0, 0x%X(r31)" % (P(16), P(17), V(4)))
    st('dk_close_up', """
        bl h_vy0
        bgt.far epi
        bl h_gnd
        cmpwi r3, 0
        beq.far epi
        lwz r3, 0x%(V4)X(r31)
        cmpwi r3, 3
        bge dkc_go
        addi r3, r3, 1
        stw r3, 0x%(V4)X(r31)
        li r4, 5
        bl h_kin
        b epi
    dkc_go:
        li r4, 5
        b go""" % d)
    # 5 angry (0x858FC / 0x860A0): kinetic 0, ground on, AngryL loop (its ACMD stomps); P19 (200) frames -> 3
    en('dk_angry_en', 0, 1, 0, 1, pre="li r0, 0\nstw r0, 0x%X(r31)" % V(0))
    st('dk_angry_up', """
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(V0)X(r31)
        lwz r0, 0x%(P21)X(r30)
        cmpw r3, r0
        ble.far epi
        li r4, 3
        b go""" % d)
    # 6 run start (0x86DBC / 0x85BDC): W+0x24 / +0x2C = P7 / P8 (3 / 3.5), W+0x20 = P6 (-0.5: a hop back) unless a
    # ledge is behind (check_cliff_distance_lr(3 / g + 2, -lr): the cave's check_cliff with -lr), kinetic 5, ground
    # off, AttackRunStart at P11, V2 = 1; landed: V2 = 0, ground on; P22 (30) frames and landed -> 7 (V1 = 0)
    en('dk_rs_en', 5, 0, 1, 0, rate=P(11), pre="""
        bl h_ebase
        lwz r0, 0x%(P7)X(r30)
        stw r0, 0x24(r10)
        lwz r0, 0x%(P8)X(r30)
        stw r0, 0x2C(r10)
        lfs f1, 0x10(r31)
        fneg f1, f1
        mr r3, r31
    """ % d + call(CHECK_CLIFF_LR) + """
        mr r28, r3
        bl h_ebase
        li r0, 0
        cmpwi r28, 0
        bne dks_z
        lwz r0, 0x%(P6)X(r30)
    dks_z:
        stw r0, 0x20(r10)
        li r0, 1
        stw r0, 0x%(V2)X(r31)
        li r0, 0
        stw r0, 0x%(V0)X(r31)""" % d)
    st('dk_rs_up', """
        lwz r0, 0x%(V2)X(r31)
        cmpwi r0, 0
        beq dkr_t
        bl h_vy0
        bgt dkr_t
        bl h_gnd
        cmpwi r3, 0
        beq dkr_t
        li r0, 0
        stw r0, 0x%(V2)X(r31)
        li r4, 1
        bl h_att
    dkr_t:
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(V0)X(r31)
        lwz r0, 0x%(P22)X(r30)
        cmpw r3, r0
        ble.far epi
        lwz r0, 0x%(V2)X(r31)
        cmpwi r0, 1
        beq.far epi
        li r0, 0
        stw r0, 0x%(V1)X(r31)
        li r4, 7
        b go""" % d)
    # 7 run (0x85EA4 / 0x8651C): RunL at P9, kinetic 10 (its ACMD: the 6 %% head box, the quakes); every P1[1]
    # interval of V1 (first at 0) search: a target behind -> 9; a ledge (variation 1: clear_speed_all) or a wall -> 9;
    # off the ground -> 1; V1 > P23 (200, the turns don't reset it) -> 8; V1++
    en('dk_run_en', 0xA, 1, 14, 1, rate=P(9))
    st('dk_run_up', """
        li r4, 1
        bl h_grp
        lwz r0, 0x%(V1)X(r31)
        divwu r11, r0, r3
        mullw r11, r11, r3
        subf. r0, r11, r0
        bne dkn_gnd
        li r4, 1
        bl h_srch
        stw r3, 0x%(V3)X(r31)
        cmpwi r3, 0
        blt dkn_gnd
        mr r4, r3
        bl h_dx
        lfs f0, 0x%(ZERO)X(r30)
        fcmpu cr0, f1, f0
        bge dkn_gnd
        li r4, 9
        bl h_chg
    dkn_gnd:
        bl h_gnd
        cmpwi r3, 0
        bne dkn_on
        li r4, 1
        bl h_chg
        b dkn_time
    dkn_on:
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        bne dkn_wall
        bl h_cliff
        cmpwi r3, 0
        beq dkn_wall
        bl h_clear
        b dkn_turn
    dkn_wall:
        bl k_wallt
        cmpwi r3, 0
        beq dkn_time
    dkn_turn:
        li r4, 9
        bl h_chg
    dkn_time:
        lwz r3, 0x%(V1)X(r31)
        lwz r0, 0x%(P23)X(r30)
        cmpw r3, r0
        ble dkn_in
        li r4, 8
        bl h_chg
    dkn_in:
        bl h_mv
        lwz r3, 0x%(V1)X(r31)
        addi r3, r3, 1
        stw r3, 0x%(V1)X(r31)""" % d)
    # 8 brake (0x85954 / 0x860F0): RunBrakeL, kinetic 2 (play_se 0x2910008: not ported); update k_brk_up (-> 3)
    en('dk_brk_en', 2, 1, 13, 0)
    # 9 run turn (0x86F2C / 0x85CCC): RunTurnL at P12, kinetic 2; a ledge: clear_speed_all; at its end reverse_lr => 7
    en('dk_rt_en', 2, 1, 15, 0, rate=P(12))
    st('dk_rt_up', """
        bl h_cliff
        cmpwi r3, 0
        beq dkt_end
        bl h_clear
    dkt_end:
        bl h_end
        cmpwi r3, 0
        beq dkt_in
        bl h_rev
        li r4, 7
        bl h_chgi
    dkt_in:
        bl h_mv
        li r0, 0
        stw r0, 4(r29)""")
    # 10 stepped (0x86C14 / 0x86CC0): kinetic 0, Stepped, ground on (play_se 0x291000C: not ported); end -> 3
    en('dk_step_en', 0, 1, 16, 0)
    st('dk_step_up', "bl h_end\ncmpwi r3, 0\nbeq.far epi\nli r4, 3\nb go")
    # 11 collapses (0x859BC / 0x861A0): kinetic 0, Collapses, ground on, notify_on_death; end -> 13 (the 3DS's
    # create_dead_item(1, 20) is the removal's defeat path: DEFEATED)
    en('dk_col_en', 0, 1, 2, 0, extra="mr r3, r31\n" + call(NOTIFY_DEATH) + "\nli r0, 1\nstw r0, 0x%X(r31)" % DEFEATED)
    st('dk_col_up', "bl h_end\ncmpwi r3, 0\nbeq.far epi\nli r4, 13\nb go")
    # slot 20 (the 3DS's 21, 0x85FE0): add_damage(P15 = 25) (the damage module's damage + 25 -> set_current_damage:
    # HP W+0 = max - damage), HP > 0 => 10 (stepped), else HP = 0 => 11 (collapses)
    st('dk_tread', """
        lwz r3, 0(r31)
        lwz r3, 0x30D4(r3)
        li r4, 0
    """ + call(GET_DAMAGE) + """
        lfs f0, 0x%(P15)X(r30)
        fadds f1, f1, f0
        mr r3, r31
    """ % d + call(SET_CUR_DAMAGE) + """
        bl h_ebase
        lfs f1, 0(r10)
        lfs f0, 0x%(ZERO)X(r30)
        fcmpu cr0, f1, f0
        li r4, 10
        bgt dk_tgo
        stfs f0, 0(r10)
        li r4, 11
    dk_tgo:
        bl h_chgi""" % d)
    # ---- Spiny (togezo 0x4E). V0 the stun frames (+0x16C), V1 the walk timer (+0x170), V2 the search timer
    # (+0x174), V3 the egg's spin step (+0x178, degrees), V4 the spin angle (the posture rot the 3DS turns node 2 by),
    # V5 / V6 the common leave (effect, frames: f_leave_en / o_leave_up / f_unleave). P0-5 P0[0] (egg), P6-11
    # P0[1] (Spiny), P12 PS8c f0 (0.4), P13 / P14 PS8c f2 / f3 (200 / 150), P15 PS9c f0 (0.5), P16 the spin factor,
    # P17 DEG2RAD, P18-22 the leave (P6)
    tg = dict(R1=P(1), R2=P(2), R3=P(3), R5=P(5), **d)
    # slot 40 initialize (0x370C0): its P0 row by variation: W+0x10 = +0x08 = f1, +0x20 = +0x28 = f2, +0x24 = +0x2C =
    # f3, +0x0C = f5, +0x38 = PS8c f0
    st('tg_init', """
        lwz r0, 0xC(r31)
        li r28, 0
        cmpwi r0, 1
        bne tgi_row
        li r28, 24
    tgi_row:
        add r28, r28, r30
        bl h_ebase
        lwz r0, 0x%(R1)X(r28)
        stw r0, 0x10(r10)
        stw r0, 8(r10)
        lwz r0, 0x%(R2)X(r28)
        stw r0, 0x20(r10)
        stw r0, 0x28(r10)
        lwz r0, 0x%(R3)X(r28)
        stw r0, 0x24(r10)
        stw r0, 0x2C(r10)
        lwz r0, 0x%(R5)X(r28)
        stw r0, 0xC(r10)
        lwz r0, 0x%(P12)X(r30)
        stw r0, 0x38(r10)""" % tg)
    # W+0x40 = the row's f4 (the egg's bounce 0.8, the Spiny's 1)
    H.asm("""
    tg_w40:
        mflr r9
        bl h_ebase
        mtlr r9
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        lwz r0, 0x%(P4)X(r30)
        bne tgw_st
        lwz r0, 0x%(P10)X(r30)
    tgw_st:
        stw r0, 0x40(r10)
        blr
    """ % tg)
    # tg_arm(r4 = an InnerEnemyAttackParam): create_attack_data, set_attack(its id, part) (Behavior::set_attack_data's
    # arming); slot 45 set_attack_data (0x37568): the 3DS clears ids >= 1 only and arms P2 entries 2.. by state
    # (2: the egg's dead body in 4, 3: the Spiny's in 12, as id 0); here clear_all and id 0 again: the body (P2[var
    # == 1 ? 1 : 0], L62440) or the dead body
    st('tg_arm', """
        mr r28, r4
        mr r3, r31
    """ + call(ATK_CREATE) + """
        lwz r4, 4(r28)
        lwz r5, 8(r28)
        stw r4, 0x84(r31)
        stw r5, 0x88(r31)
        lwz r3, 0(r31)
        lwz r3, 0x30C8(r3)
        addi r6, r31, 0x1C
    """ + call(ATK_SET))
    st('tg_atk', """
        mr r28, r4
        lwz r3, 0(r31)
        lwz r3, 0x30C8(r3)
    """ + call(ATK_CLEAR) + """
        lis r4, 0x%(EH)04X
        addi r4, r4, %(EL)d
        cmpwi r28, 4
        beq tga_go
        lis r4, 0x%(DH)04X
        addi r4, r4, %(DL)d
        cmpwi r28, 12
        beq tga_go
        lis r4, 0x%(GH)04X
        addi r4, r4, %(GL)d
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        bne tga_go
        lis r4, 0x%(BH)04X
        addi r4, r4, %(BL)d
    tga_go:
        mr r3, r31
        bl tg_arm""" % dict(EH=ha(D['tg_eggdead']), EL=sx(D['tg_eggdead']), DH=ha(D['tg_dead']), DL=sx(D['tg_dead']),
                            GH=ha(D['tg_egg']), GL=sx(D['tg_egg']), BH=ha(D['tg_body']), BL=sx(D['tg_body'])))
    # slots 66 / 67: var 1 ? 6 : 1, var 1 ? 12 : 4
    H.asm("""
    tg_66:
        lwz r0, 0xC(r3)
        li r3, 1
        cmpwi r0, 1
        bnelr
        li r3, 6
        blr
    tg_67:
        lwz r0, 0xC(r3)
        li r3, 4
        cmpwi r0, 1
        bnelr
        li r3, 12
        blr
    """)
    # start (0x36CE0): set_rhombus, stick x = the posture lr (no turn to a target), the counters, V1 / V2 = P13 /
    # P14, the body attack (id 0), var 1 -> 6 (fall), else 1 (the egg's fall)
    st('tg_start', """
    """ + call(SET_RHOMBUS) + """
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x60(r12)
        stw r0, 0x10(r31)
        li r0, 0
        stw r0, 0x14(r31)
        stw r0, 0x18(r31)
        addi r11, r31, 0x168
        li r12, 9
        mtctr r12
    tgs_zero:
        stwu r0, 4(r11)
        bdnz tgs_zero
        lwz r0, 0x%(P13)X(r30)
        stw r0, 0x%(V1)X(r31)
        lwz r0, 0x%(P14)X(r30)
        stw r0, 0x%(V2)X(r31)
        mr r3, r31
        li r4, 0
        bl tg_atk
        li r4, 1
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        bne.far goi
        li r4, 6
        b goi""" % tg)
    # (step 2i: tgv_hatch, the hatch's node 2 reset and mesh swap)
    # the egg's spin (L6239C, slot 55 0x3740C): V3 = sign(-speed x) x |speed| x P16 x -lr (degrees a frame; the 3DS's
    # common factor EnemyParamAccessor +0x198 +0x90 x +0xA0 is not in the dump: P16 stands in); tg_turn: V4 += V3,
    # node 2 (RotN) set to (V4, 0, 0) radians (set_node_rotate, the ModelModule's vt+0xC4 on a change)
    H.asm("""
    tg_spin:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        addi r3, r1, 8
        mr r4, r31
    """ + call(GET_SPEED) + """
        lfs f1, 8(r1)
        lfs f2, 0xC(r1)
        fmuls f3, f1, f1
        fmadds f3, f2, f2, f3
        fmr f4, f3
        lis r12, 0x%(CH)04X
        lfs f0, %(CL)d(r12)
        fcmpu cr0, f3, f0
        ble tgp_z
        frsqrte f4, f3
        fmuls f4, f4, f3
    tgp_z:
        lfs f0, 0x%(P16)X(r30)
        fmuls f4, f4, f0
        lfs f0, 0x10(r31)
        fmuls f4, f4, f0
        lis r12, 0x%(CH)04X
        lfs f0, %(CL)d(r12)
        fcmpu cr0, f1, f0
        ble tgp_st
        fneg f4, f4
    tgp_st:
        stfs f4, 0x%(V3)X(r31)
        b h_ret20
    tg_turn:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        lfs f1, 0x%(V4)X(r31)
        lfs f0, 0x%(V3)X(r31)
        fadds f1, f1, f0
        stfs f1, 0x%(V4)X(r31)
        lfs f0, 0x%(P17)X(r30)
        fmuls f1, f1, f0
        stfs f1, 8(r1)
        li r0, 0
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30F0(r3)
        li r4, 2
        addi r5, r1, 8
        li r6, 0
    """ % tg + call(SET_NODE_ROT) + """
        cmpwi r3, 0
        beq.far h_ret20
        lwz r3, 0(r31)
        lwz r3, 0x3118(r3)
        lwz r12, 0(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctrl
        b h_ret20
    """ % MODEL_NODE_DIRTY)
    # 1 egg fall (0x36FEC / 0x37288): kinetic 8, ground off, Paipo loop, the spin, W+0x40 = f4; on the ground => 2
    en('tg_efall_en', 8, 0, 4, 1, extra="bl tg_spin\nbl tg_w40")
    st('tg_efall_up', "bl tg_turn\nbl h_gnd\ncmpwi r3, 0\nbeq.far epi\nli r4, 2\nb goi")
    # 2 egg bounce (0x37090 / 0x372C8): kinetic 4 (the bounce: W+0x40 its restitution, inferred); landed (speed y
    # <= 0, on the ground): |speed| < P15 (0.5) -> the hatch (L622F4: variation 1, initialize, the Spiny's body
    # attack; the mesh swap: no Wii U path) -> 5; else a new spin step
    st('tg_ebnc_en', "li r4, 4\nbl h_kin")
    st('tg_ebnc_up', """
        bl tg_turn
        bl h_vy0
        bgt.far epi
        bl h_gnd
        cmpwi r3, 0
        beq.far epi
        addi r3, r1, 8
        mr r4, r31
    """ + call(GET_SPEED) + """
        lfs f1, 8(r1)
        lfs f2, 0xC(r1)
        fmuls f1, f1, f1
        fmadds f1, f2, f2, f1
        lfs f0, 0x%(P15)X(r30)
        fmuls f0, f0, f0
        fcmpu cr0, f1, f0
        blt tgb_hatch
        bl tg_spin
        b epi
    tgb_hatch:
        bl tg_hatch
        li r4, 5
        b go
    tg_hatch:
        mflr r0
        stw r0, 0x1C(r1)
        li r0, 1
        stw r0, 0xC(r31)
        mr r3, r31
        bl tg_init
        mr r3, r31
        li r4, 5
        bl tg_atk
        mr r3, r31
        bl tgv_hatch
        lwz r0, 0x1C(r1)
        mtlr r0
        blr""" % tg)
    # 3 egg stun (slot 69, var 0; 0x36FA0 / 0x37260): kinetic 16, ground off, V0 = hit_return_frame(), a spin step;
    # V0 counted down -> 1
    st('tg_estun_en', "li r4, 16\nbl h_kin\nli r4, 0\nbl h_att\nbl f_hitret\nstw r3, 0x%X(r31)\nbl tg_spin" % V(0))
    st('tg_estun_up', """
        bl tg_turn
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V0)X(r31)
        cmpwi r3, 0
        bgt.far epi
        li r4, 1
        b go""" % tg)
    # 4 egg dead (slot 67, var 0; 0x370A4 / 0x3766C): bullet(), V3 = 0 (P2 entry 2 armed by set_attack_data); W
    # flags & 8 -> 13 (g_dead_up)
    st('tg_edead_en', "li r0, 1\nstw r0, 0x%X(r31)\nli r0, 0\nstw r0, 0x%X(r31)\nmr r3, r31\n" % (DEFEATED, V(3)) +
       call(BULLET))
    # 5 hatch (Change; 0x37A0C / 0x37E20): kinetic 5, ground off, Change, W+0x40 (play_se 0x6D90000: not ported); at
    # its end on the ground: the nearest target behind -> 9, else 8 (g_landt_up)
    en('tg_chg_en', 5, 0, 0, 0, extra="bl tg_w40")
    st('tg_chg_up', "bl h_gnd\ncmpwi r3, 0\nbeq.far epi\nmr r3, r31\nmr r4, r29\nbl g_landt_up")
    # 6 fall (0x377E8 / 0x37B48): kinetic 8, ground off, Fall loop, W+0x40; on the ground => 7 (g_fall_up)
    en('tg_fall_en', 8, 0, 2, 1, extra="bl tg_w40")
    # 8 walk (0x37984 / 0x37C7C): kinetic 1, Walk loop; move; off the ground -> 6; a wall -> 9; V1 (200) runs out ->
    # 10 (the leave); else while V2 (150) runs: every P1[0] interval (20) search_target(0) + check_turn_to_target -> 9
    en('tg_walk_en', 1, 1, 6, 1)
    st('tg_walk_up', """
        bl h_mv
        bl h_gnd
        cmpwi r3, 0
        bne tgk_on
        li r4, 6
        b go
    tgk_on:
        bl h_wall
        cmpwi r3, 0
        li r4, 9
        bne.far go
        lwz r3, 0x%(V1)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V1)X(r31)
        cmpwi r3, 0
        li r4, 10
        ble.far go
        lwz r28, 0x%(V2)X(r31)
        addi r28, r28, -1
        stw r28, 0x%(V2)X(r31)
        cmpwi r28, 0
        ble.far epi
        li r4, 0
        bl h_grp
        divwu r11, r28, r3
        mullw r11, r11, r3
        subf. r0, r11, r28
        bne.far epi
        li r4, 0
        bl h_srch
        cmpwi r3, 0
        blt.far epi
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        beq.far epi
        li r4, 9
        b go""" % tg)
    # 10 leave (0x378D8 / 0x37BF8): Fall at rate 0, init_common_leave(P6) (f_leave_en: CFG LVP), then o_leave_up
    st('tg_leave_en', "li r4, 2\nli r5, 0\nbl h_mot0\nmr r3, r31\nbl f_leave_en")
    # 11 stun (slot 69, var 1; 0x37760 / 0x37AB8): kinetic 16, ground off, Damage loop, V0 = hit_return_frame(), W
    # flags |= 0x80; counted down: on the ground flags &= ~0x80, -> 8; in the air -> 6
    en('tg_stun_en', 16, 0, 1, 1, extra="bl f_hitret\nstw r3, 0x%X(r31)\nbl f_kflag\nlwz r0, 0(r12)\nori r0, r0, 0x80\n"
       "stw r0, 0(r12)" % V(0))
    st('tg_stun_up', """
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V0)X(r31)
        cmpwi r3, 0
        bgt.far epi
        bl h_gnd
        cmpwi r3, 0
        li r4, 6
        beq.far go
        bl f_kflag
        lwz r0, 0(r12)
        rlwinm r0, r0, 0, 25, 23
        stw r0, 0(r12)
        li r4, 8
        b go""" % tg)
    # slot 69 (0x37EAC): a running leave ends (finalize_common_leave + set_correct(5): f_unleave), var 0 => 3, var 1
    # => 11; returns 1 (the framework's reaction is skipped)
    st('tg_69', """
        bl f_unleave
        li r4, 3
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        bne tg69_go
        li r4, 11
    tg69_go:
        bl h_chgi
        li r3, 1""")
    # ---- Paratroopa / Koopa (patapata 0x03). A flier-sized object (the aerial module at AER, for the bite). V0 the
    # search counter (+0x1DC), V1 the bite / leap cool-down (+0x1E8), V2 the attack timer (+0x1E0), V3 the hop's
    # first falling frame seen (+0x1F0), V4 the dead item still due (+0x1FC). P0-47 its P0 rows (12 words a
    # variation), P48-50 PS78 (60 %%, 30, 1.5), P51-61 PS84, P62 P@0xB0 (3: the shell item's height), P63 the item kind
    pt = dict(d, R1=P(1), R2=P(2), R3=P(3), R4=P(4), R5=P(5), R6=P(6), R8=P(8), R9=P(9), R10=P(10), R11=P(11),
              TEN=P(64), ONE=P(65), MONE=P(66), AM=AER + 0xC, SHV=KOOPA_SHELL[1])
    H.asm("""
    pt_row:
        lwz r28, 0xC(r31)
        mulli r28, r28, 48
        add r28, r28, r30
        blr
    pt_hopw:
        mflr r9
        bl pt_row
        bl h_ebase
        mtlr r9
        lwz r0, 0x%(R3)X(r28)
        stw r0, 8(r10)
        stw r0, 0x20(r10)
        stw r0, 0x28(r10)
        lwz r0, 0x%(R4)X(r28)
        stw r0, 0xC(r10)
        stw r0, 0x24(r10)
        stw r0, 0x2C(r10)
        blr
    pt_hop5:
        mflr r8
        bl pt_hopw
        mtlr r8
        lwz r0, 0x%(R5)X(r28)
        stw r0, 0x40(r10)
        blr
    pt_hop6:
        mflr r8
        bl pt_hopw
        mtlr r8
        lwz r0, 0x%(R6)X(r28)
        stw r0, 0x40(r10)
        blr
    """ % pt)
    # L5D968 (the walk) / L736B4 (the winged start): W+0x10 = f1, +0x08 = f2, +0x0C = 10, +0x40 = 1 (walk only),
    # +0x44 = f8, +0x14 / +0x18 = 0, the kinetic module's vt+0xFC(0x20000004) kick
    st('pt_walkw', """
        bl pt_row
        bl h_ebase
        lwz r0, 0x%(R1)X(r28)
        stw r0, 0x10(r10)
        lwz r0, 0x%(R2)X(r28)
        stw r0, 8(r10)
        lwz r0, 0x%(TEN)X(r30)
        stw r0, 0xC(r10)
        lwz r0, 0x%(ONE)X(r30)
        stw r0, 0x40(r10)
        b ptw_44
    pt_startw:
        mflr r0
        bl pro
        bl pt_row
        bl h_ebase
    ptw_44:
        lwz r0, 0x%(R8)X(r28)
        stw r0, 0x44(r10)
        li r0, 0
        stw r0, 0x14(r10)
        stw r0, 0x18(r10)
        bl h_kick""" % pt)
    # start (0x7234C): the aerial module, set_rhombus, lr, face the nearest target, the dead item due (V4 = 1);
    # winged (var 0 / 1): L736B4, => 1; walking (2 / 3): L5D968, => 10
    st('pt_start', """
        addi r3, r31, 0x%(AER)X
        lwz r4, 0(r31)
    """ % dict(AER=AER) + call(AER_CTOR) + "\nmr r3, r31\n" + call(SET_RHOMBUS) + """
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r0, 0x60(r12)
        stw r0, 0x10(r31)
        li r0, 0
        stw r0, 0x14(r31)
        stw r0, 0x18(r31)
        li r0, 1
        stw r0, 0x%(V4)X(r31)
        bl h_near
        mr r4, r3
        bl h_tchk
        cmpwi r3, 0
        beq pts_w
        bl h_rev
    pts_w:
        lwz r0, 0xC(r31)
        cmpwi r0, 2
        bge pts_k
        mr r3, r31
        bl pt_startw
        li r4, 1
        b goi
    pts_k:
        mr r3, r31
        bl pt_walkw
        li r4, 10
        b goi""" % pt)
    # 1 winged fall (0x7258C / 0x72820): L5DAB4, kinetic 8, ground off, Fly loop; on the ground => 2
    en('pt_wfall_en', 8, 0, 11, 1, pre="bl pt_hop6\nbl f_anone")
    st('pt_wfall_up', "bl h_gnd\ncmpwi r3, 0\nbeq.far epi\nli r4, 2\nb goi")
    # 2 hop (0x725E8 / 0x72860): L5D7EC, kinetic 5, ground off, Fly loop, V3 = 0. Update: its first falling frame:
    # V3 = 1, W+0x40 = f6 (L73E48; its energy 0 +0x38 / +0x3C writes: not ported); landed after that: var 1 60 %% a
    # search of group 2 and a target behind -> 3 (0x72954: no more this frame), else the request -> 2 (hop again,
    # 0x7292C) and the frame goes on (a later request this frame wins, as the 3DS's change_state); a wall -> 3; the
    # search when V0 <= 0 AND the cool-down V1 <= 0 (0x72970-0x72980; step 2o: was V0 | V1 <= 0, which let any
    # negative counter through: a search every frame and the 30-frame cool-down cut to V0's 11): V0 = group var's
    # interval, search_target(var): found -> face it, -> 5; else V0--, V1-- (0x729F8), move
    en('pt_hop_en', 5, 0, 11, 1, pre="bl pt_hop5\nli r0, 0\nstw r0, 0x%X(r31)" % V(3))
    st('pt_hop_up', """
        bl h_vy0
        bge pth_g
        lwz r0, 0x%(V3)X(r31)
        cmpwi r0, 0
        bne pth_g
        li r0, 1
        stw r0, 0x%(V3)X(r31)
        bl pt_row
        bl h_ebase
        lwz r0, 0x%(R6)X(r28)
        stw r0, 0x40(r10)
    pth_g:
        lwz r0, 0x%(V3)X(r31)
        cmpwi r0, 0
        beq pth_w
        bl h_vy0
        bgt pth_w
        bl h_gnd
        cmpwi r3, 0
        beq pth_w
        lwz r0, 0xC(r31)
        cmpwi r0, 1
        bne pth_re
        li r3, 1
        li r4, 100
        bl h_rand
        lwz r0, 0x%(P48)X(r30)
        cmpw r3, r0
        bgt pth_re
        li r4, 2
        bl h_srch
        cmpwi r3, 0
        blt pth_re
        mr r4, r3
        bl h_dx
        lfs f0, 0x%(ZERO)X(r30)
        fcmpu cr0, f1, f0
        bge pth_re
        li r4, 3
        b go
    pth_re:
        li r4, 2
        bl h_chg
    pth_w:
        bl h_wall
        cmpwi r3, 0
        li r4, 3
        bne.far go
        lwz r0, 0x%(V0)X(r31)
        cmpwi r0, 0
        bgt pth_cnt
        lwz r0, 0x%(V1)X(r31)
        cmpwi r0, 0
        bgt pth_cnt
        lwz r4, 0xC(r31)
        bl h_grp
        stw r3, 0x%(V0)X(r31)
        lwz r4, 0xC(r31)
        bl h_srch
        cmpwi r3, 0
        blt pth_cnt
        mr r4, r3
        bl h_dx
        lfs f0, 0x%(ZERO)X(r30)
        fcmpu cr0, f1, f0
        bge pth_bite
        bl h_rev
    pth_bite:
        li r4, 5
        b go
    pth_cnt:
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V0)X(r31)
        lwz r3, 0x%(V1)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V1)X(r31)
        bl h_mv""" % pt)
    # 3 turn on the ground (0x72FEC / 0x72A30): L5D7EC, kinetic 0, ground on, TurnPatapata; at its end reverse_lr
    # => 1 (g_turn_up with WALKST... its own: => 1)
    en('pt_turn_en', 0, 1, 21, 0, pre="bl pt_hop5")
    st('pt_turn_up', "bl h_end\ncmpwi r3, 0\nbeq.far epi\nbl h_rev\nli r4, 1\nb goi")
    # 5 bite wind-up (0x72F28 / 0x730F0): the aerial module's set_mode_normal(0, 0, 0, 0, 10, 10) with the current
    # speed (0, -P0 f11) -- the Wii U's reduced module has no mode 0: its uniform mode (f_amode 5) at that speed is
    # the same motion (no acceleration) --, ground off, Bite at P50 (1.5), V2 = P0 f9; the aerial update; V2 out -> 6
    st('pt_bw_en', """
        li r4, 0
        bl h_att
        li r4, 0
        li r5, 0
        lfs f2, 0x%(P50)X(r30)
        bl h_mot
        bl pt_row
        lwz r0, 0x%(R9)X(r28)
        stw r0, 0x%(V2)X(r31)
        li r0, 0
        stw r0, 8(r1)
        lfs f1, 0x%(R11)X(r28)
        fneg f1, f1
        stfs f1, 0xC(r1)
        li r4, 5
        bl f_amode""" % pt)
    H.asm("""
    pt_tick:
        lwz r3, 0x%(V2)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V2)X(r31)
        blr
    """ % pt)
    st('pt_bw_up', "bl f_aupd\nbl pt_tick\ncmpwi r3, 0\nbgt.far epi\nli r4, 6\nb go")
    # 6 bite (0x72714 / 0x72CEC; P2 entry 0 armed: 4 %%, angle -50): V2 = P0 f10; the aerial update; V2 out -> 7;
    # the motion's end -> 1 with the cool-down V1 = P49 (30)
    st('pt_bite_en', "bl pt_row\nlwz r0, 0x%(R10)X(r28)\nstw r0, 0x%(V2)X(r31)" % pt)
    st('pt_bite_up', """
        bl f_aupd
        bl h_end
        cmpwi r3, 0
        bne ptb_end
        bl pt_tick
        cmpwi r3, 0
        bgt.far epi
        li r4, 7
        b go
    ptb_end:
        lwz r0, 0x%(P49)X(r30)
        stw r0, 0x%(V1)X(r31)
        li r4, 1
        b go""" % pt)
    # 7 bite recovery (0x72A84 / 0x72ECC): the aerial update; at the motion's end -> 1, V1 = P49
    st('pt_brec_en', "nop")
    st('pt_brec_up', "bl f_aupd\nbl h_end\ncmpwi r3, 0\nbeq.far epi\nb ptb_end")
    # the wing loss (L in slots 20 / 69 / 9's enter): var += 2, the effect 0x7030000 at the posture (one shot), the
    # walk params (L5D968); the wing mesh off (step 2i: h_vsetr)
    st('pt_dewing', """
        lwz r3, 0xC(r31)
        cmpwi r3, 2
        bge.far epi
        addi r3, r3, 2
        stw r3, 0xC(r31)
        li r4, 0
        li r5, 1
        bl h_vsetr
        lis r4, 0x703
        bl t_fx
        mr r3, r31
        bl pt_walkw""")
    # 9 wing loss (0x72740 / 0x72D74): L5DAB4, kinetic 8, clear_speed_all, ground off, NokonokoMode, the wing loss;
    # at its end -> 10
    en('pt_wl_en', 8, 0, 17, 0, pre="bl pt_hop6\nbl f_anone", extra="bl h_clear\nli r4, 0\nli r5, 1\nbl h_vsetr\nmr r3, r31\nbl pt_dewing")
    st('pt_wl_up', "bl h_end\ncmpwi r3, 0\nbeq.far epi\nli r4, 10\nb go")
    # 12 walk (0x732A4 / 0x73898): kinetic 1, Walk loop; the search when V0 <= 0 AND V1 <= 0 (0x738A0-0x738B4; step
    # 2o: was V0 | V1 <= 0): V0 = group var + 1's interval, search_target(var + 1): found -> face it, -> 14; else
    # V0--, V1-- every frame (0x73928, before the ground check; step 2o: was only on the frames it moved), off the
    # ground -> 10, a wall (or var 3 and a ledge) -> 13, move
    en('pt_walk_en', 1, 1, 22, 1)
    st('pt_walk_up', """
        lwz r0, 0x%(V0)X(r31)
        cmpwi r0, 0
        bgt ptk_g
        lwz r0, 0x%(V1)X(r31)
        cmpwi r0, 0
        bgt ptk_g
        lwz r4, 0xC(r31)
        addi r4, r4, 1
        bl h_grp
        stw r3, 0x%(V0)X(r31)
        lwz r4, 0xC(r31)
        addi r4, r4, 1
        bl h_srch
        cmpwi r3, 0
        blt ptk_g
        mr r4, r3
        bl h_dx
        lfs f0, 0x%(ZERO)X(r30)
        fcmpu cr0, f1, f0
        li r4, 14
        bge.far go
        bl h_rev
        li r4, 14
        b go
    ptk_g:
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V0)X(r31)
        lwz r3, 0x%(V1)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V1)X(r31)
        bl h_gnd
        cmpwi r3, 0
        li r4, 10
        beq.far go
        bl h_wall
        cmpwi r3, 0
        bne ptk_t
        lwz r0, 0xC(r31)
        cmpwi r0, 3
        bne ptk_m
        bl h_cliff
        cmpwi r3, 0
        beq ptk_m
    ptk_t:
        li r4, 13
        b go
    ptk_m:
        bl h_mv""" % pt)
    # 14 jump hold (0x73D4C / 0x73ED0): kinetic 0, JumpHold at P51 (1); end -> 15
    en('pt_jh_en', 0, 1, 13, 0, rate=P(51))
    st('pt_jh_up', "bl h_end\ncmpwi r3, 0\nbeq.far epi\nli r4, 15\nb go")
    # 15 leap (0x73DB0 / 0x74010): set_kinetic_shoot(P53 3, P54 1, P55 0.075): W+0x20 = 3, +0x24 = 1, +0x28 = -1,
    # +0x2C = 10, +0x1C = 0.075, the kick, kinetic 5; ground off; JumpAttack at P52 (3); V2 = P0 f9; V0 = P61 (15);
    # move; V2 out -> 16
    st('pt_leap_en', """
        bl h_ebase
        lwz r0, 0x%(P53)X(r30)
        stw r0, 0x20(r10)
        lwz r0, 0x%(P54)X(r30)
        stw r0, 0x24(r10)
        lwz r0, 0x%(MONE)X(r30)
        stw r0, 0x28(r10)
        lwz r0, 0x%(TEN)X(r30)
        stw r0, 0x2C(r10)
        lwz r0, 0x%(P55)X(r30)
        stw r0, 0x1C(r10)
        bl h_kick
        li r4, 5
        bl h_kin
        li r4, 0
        bl h_att
        li r4, 12
        li r5, 0
        lfs f2, 0x%(P52)X(r30)
        bl h_mot
        bl pt_row
        lwz r0, 0x%(R9)X(r28)
        stw r0, 0x%(V2)X(r31)
        lwz r0, 0x%(P61)X(r30)
        stw r0, 0x%(V0)X(r31)""" % pt)
    st('pt_leap_up', "bl h_mv\nbl pt_tick\ncmpwi r3, 0\nbgt.far epi\nli r4, 16\nb go")
    # 16 the leap's hit (0x73688 / 0x73C98; P2 entry 1 armed: 2 %%): V2 = P0 f10; move; V2-- (clear_all at 0); V0--;
    # on the ground: V0 < 0 -> V1 = P60 (20), => 18; else => 17
    st('pt_lh_en', "bl pt_row\nlwz r0, 0x%(R10)X(r28)\nstw r0, 0x%(V2)X(r31)" % pt)
    H.asm("""
    pt_attick:
        mflr r0
        stw r0, 0x1C(r1)
        bl pt_tick
        cmpwi r3, 0
        bne ptt_v0
        lwz r3, 0(r31)
        lwz r3, 0x30C8(r3)
    """ + call(ATK_CLEAR) + """
    ptt_v0:
        lwz r3, 0x%(V0)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(V0)X(r31)
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """ % pt)
    st('pt_lh_up', """
        bl h_mv
        bl pt_attick
        bl h_gnd
        cmpwi r3, 0
        beq.far epi
        lwz r3, 0x%(V0)X(r31)
        cmpwi r3, 0
        li r4, 17
        bge.far goi
        lwz r0, 0x%(P60)X(r30)
        stw r0, 0x%(V1)X(r31)
        li r4, 18
        b goi""" % pt)
    # 17 slide (0x73F0C / 0x7405C): set_kinetic_brake_ground(P56 0.04) (W+0x14, kinetic 2), ground on; on the
    # ground: V2-- (clear_all at 0), V0-- < 0 -> V1 = P60, => 18; off it -> 10
    st('pt_sl_en', "bl h_ebase\nlwz r0, 0x%(P56)X(r30)\nstw r0, 0x14(r10)\nli r4, 2\nbl h_kin\nli r4, 1\nbl h_att" % pt)
    st('pt_sl_up', """
        bl h_gnd
        cmpwi r3, 0
        li r4, 10
        beq.far go
        bl pt_attick
        lwz r3, 0x%(V0)X(r31)
        cmpwi r3, 0
        bge.far epi
        lwz r0, 0x%(P60)X(r30)
        stw r0, 0x%(V1)X(r31)
        li r4, 18
        b goi""" % pt)
    # 18 landing attack (0x7355C / 0x739E0): set_kinetic_brake_ground(P58 0.1), LandingJumpAttack at P57; move;
    # end -> 12
    st('pt_la_en', """
        bl h_ebase
        lwz r0, 0x%(P58)X(r30)
        stw r0, 0x14(r10)
        li r4, 2
        bl h_kin
        li r4, 1
        bl h_att
        li r4, 15
        li r5, 0
        lfs f2, 0x%(P57)X(r30)
        bl h_mot""" % pt)
    st('pt_la_up', "bl h_mv\nbl h_end\ncmpwi r3, 0\nbeq.far epi\nli r4, 12\nb go")
    # 19 shell (stomped as a Koopa; 0x735C0 / 0x73A24) and 20 the spinning shell (killed as a Koopa; 0x73F48, P2
    # entry 2: 17 %%): kinetic 0 (19) / 16 (20), ShellMode (at 10 in 20), disable_hit, disable_tread,
    # set_current_damage(0); the first time the dead item (the removal's defeat path: DEFEATED; the 3DS's
    # set_already_dead_flag); update: at the motion's end on the ground create_item_and_throw(P63 0x94, var 0 / 2 ?
    # 1 : 0, position + (0, P62 - speed y, 0), the current speed, 0, true, -1, -1), then -> 23 (removed: the 3DS
    # hides it, set_visibility(0), and removes it)
    H.asm("""
    pt_shell:
        mflr r0
        stw r0, 0x1C(r1)
        mr r3, r31
    """ + call(DISABLE_HIT) + "\nmr r3, r31\n" + call(DISABLE_TREAD) + """
        lis r12, 0x%(CH)04X
        lfs f1, %(CL)d(r12)
        mr r3, r31
    """ % pt + call(SET_CUR_DAMAGE) + """
        lwz r0, 0x%(V4)X(r31)
        cmpwi r0, 0
        beq pts_d
        li r0, 1
        stw r0, 0x%(DF)X(r31)
    pts_d:
        lwz r0, 0x1C(r1)
        mtlr r0
        blr
    """ % pt)
    st('pt_sh_en', "li r4, 0\nbl h_kin\nli r4, 1\nbl h_att\nli r4, 18\nli r5, 0\nbl h_mot1\nbl pt_shell")
    st('pt_ss_en', "li r4, 16\nbl h_kin\nli r4, 0\nbl h_att\nli r4, 18\nli r5, 1\nlfs f2, 0x%X(r30)\nbl h_mot\n"
       "bl pt_shell" % P(64))
    st('pt_sh_up', """
        bl h_end
        cmpwi r3, 0
        beq.far epi
        bl h_gnd
        cmpwi r3, 0
        beq.far epi
        addi r3, r1, 0x14
        mr r4, r31
    """ + call(GET_SPEED) + """
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lfs f1, 0x10(r12)
        stfs f1, 8(r1)
        lfs f1, 0x14(r12)
        lfs f0, 0x%(P62)X(r30)
        fadds f1, f1, f0
        lfs f0, 0x18(r1)
        fsubs f1, f1, f0
        stfs f1, 0xC(r1)
        lfs f1, 0x18(r12)
        stfs f1, 0x10(r1)
        mr r3, r31
        lwz r4, 0x%(P63)X(r30)
        li r5, %(SHV)d
        addi r6, r1, 8
        addi r7, r1, 0x14
        lis r12, 0x%(CH)04X
        lfs f1, %(CL)d(r12)
        li r8, 1
        li r9, -1
        li r10, -1
    """ % pt + call(CREATE_THROW) + """
        lis r0, 0x%(NONE)04X
        cmpw r3, r0
        beq ptsh_n
        mr r3, r31
        li r4, 0
        bl h_whole
    ptsh_n:
        lwz r4, 0x%(RM)X(r30)
        b go""" % dict(RM=CF['REMOVE'], NONE=ITEM_NONE >> 16))
    # slot 20 (the 3DS's 21, 0x726BC): var 0 / 1 => 9 (the wing loss), else => 19 (the shell)
    st('pt_tread', "lwz r0, 0xC(r31)\nli r4, 9\ncmpwi r0, 2\nblt pt_tgo\nli r4, 19\npt_tgo:\nbl h_chgi")
    # slot 69 (0x73C00): a hit that does not kill: var 0 / 1 lose the wings (no state change); returns 0 (the
    # framework's damage reaction runs, then slots 64-66 by the new variation)
    st('pt_69', "bl pt_dewing\nli r3, 0")
    # slots 64-67 by variation: winged 2 / 1 / 1 / 8, walking 12 / 10 / 10 / 20
    for k, a_, b_ in ((64, 2, 12), (65, 1, 10), (66, 1, 10), (67, 8, 20)):
        H.asm("pt_%d:\nlwz r0, 0xC(r3)\nli r3, %d\ncmpwi r0, 2\nbltlr\nli r3, %d\nblr" % (k, a_, b_))
    # step 2p: slot 63 (called by change_state's 0x026A39E4 on every state change: 1 -> the push area / jostle on,
    # 0 -> off; BehaviorImpl's default 0x026A4848 is always 1): the 3DS overrides of patapata (0xB4EF8: 0 in states 8,
    # 16, 19, 20, 21) and togezo (0xB4940: 0 in 10, 11, 12)
    for lab, sts in (('pt_63', (8, 16, 19, 20, 21)), ('tg_63', (10, 11, 12))):
        H.asm("%s:\nlwz r0, 4(r3)\nli r3, 0\n%s\nli r3, 1\nblr" % (lab, '\n'.join(
            'cmpwi r0, %d\nbeqlr' % x for x in sts)))
    code_pk(H, st, call, d, D)              # step 2j: Pooka
    code_fix2j(H, st, call, d, D)           # step 2j: the audit's fixes
    code_2k(H, st, call, d, D)              # step 2k: the beam, the powder, the twins' params
    code_2l(H, call, D)                     # step 2l: the Waddle Dee's parasol
    code_2l_pw(H)                           # step 2l: Lethinium's level-2 attack as the 3DS's
    code_vis(H, st, call)
    code_2m(H, st, call, D)                  # step 2m: sounds, Stalfos's drop
    return H


BO_MGR = 0x102F6C30                  # [BO_MGR] = the BattleObjectManager
FIND_BO = 0x02BF2108                 # BattleObjectManager::find_battle_object(mgr, &out {object, vt}, id, bool)
BO_IS_NULL = 0x02BEF50C              # BattleObjectAccessor::is_null(&out)
ITEM_STATUS = 0x38E4                 # Item: [+0x38E4] +0x48 the status kind (0x0302DDC0; the 3DS [+0x3890] +0x48)
MM_IS_VALID = 0x032FF640             # model handle is_valid (id != -1 and model != 0)
MM_SET_MESH = 0x032FF6B4             # set_mesh_visibility_by_index(handle, mesh, bool) -> 0x034232FC(model, mesh, bool, 0)
MM_SET_VIS = 0x164                   # ModelModule vt: set_visibility(bool) 0x02007728 (3DS Behavior::set_visibility)
MOT_KIND = 0x38                      # MotionModule (acc+0x30F0) +0x38: the motion playing (getter 0x02C64C08)
BLINK_N = 0x194                      # Waddle Doo's blink counter (3DS +0x194); +0x198 (half) the phase count (+0x198),
BLINK_F = 0x19B                      # +0x19B the blinking flag (+0x19C); unused by every other kind
WD_LR_LEFT = 0xBF800000              # posture lr -1.0 (3DS 0x5D0F0: lr + 0x40800000 == 0)


def code_vis(H, st, call):
    """step 2i: the mesh switch (h_vis / h_vset / h_vdef / u_vis) and every 3DS set_mesh_visibility /
    set_node_visibility / set_visibility call of the ported kinds (docs/smash-run-port.md "Step 2i").

    Interface (for the next kinds, e.g. Pooka): put the kind in VMT / NUD_MESHES / VIS_DEFAULT (its cfg word VIS then
    points at its table), then from any code with r3 = the behaviour:
      bl h_vis     r4 = 3DS vmt index, r5 = 0 / 1 (Behavior::set_mesh_visibility; nothing for a kind without a table,
                   an index past the table, no model or ModelModule +8 == 8)
      bl h_vset    r4 = mask of visible entries, r5 = mask of the entries to set (bit i = vmt index i)
      bl h_vdef    the model's default (VIS_DEFAULT) on every entry, the blink words zeroed (call it from start)
      bl h_whole   r4 = 0 / 1: the whole model (Behavior::set_visibility)
    All keep r13-r31 / f14-f31, and h_vis / h_vset / h_vdef return r3 = the behaviour they were given (step 2o: they
    returned the mesh call's 1, which w_start passed on to set_rhombus); inside st() bodies r31 is the behaviour (h_visr /
    h_vsetr take r4 / r5 only).
    MAT_VIS kinds need no call: u_vis (every update, from u_pend) sets the playing motion's entries."""
    d = dict(VIS=CF['VIS'], MVIS=CF['MVIS'], MK=MOT_KIND, VSL=MM_SET_VIS, BN=BLINK_N, BN4=BLINK_N + 4, BF=BLINK_F)
    H.asm("""
    h_visr:
        mr r3, r31
    h_vis:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stmw r28, 0x10(r1)
        stw r3, 8(r1)
        lwz r12, 0x168(r3)
        lwz r28, 0x%(VIS)X(r12)
        cmpwi r28, 0
        beq hv_out
        lwz r0, 0(r28)
        cmplw r4, r0
        bge hv_out
        slwi r0, r4, 2
        add r29, r28, r0
        lwz r29, 8(r29)
        mr r30, r5
        lwz r12, 0(r3)
        lwz r31, 0x3118(r12)
        cmpwi r31, 0
        beq hv_out
        lwz r0, 8(r31)
        cmpwi r0, 8
        beq hv_out
        addi r3, r31, 4
    """ % d + call(MM_IS_VALID) + """
        cmpwi r3, 0
        beq hv_out
    hv_loop:
        rlwinm r4, r29, 8, 24, 31
        cmpwi r4, 0xFF
        beq hv_out
        addi r3, r31, 4
        mr r5, r30
    """ + call(MM_SET_MESH) + """
        slwi r29, r29, 8
        ori r29, r29, 0xFF
        b hv_loop
    hv_out:
        lwz r3, 8(r1)
        lmw r28, 0x10(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    h_vsetr:
        mr r3, r31
    h_vset:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stmw r28, 0x10(r1)
        stw r3, 8(r1)
        mr r31, r3
        mr r29, r4
        mr r28, r5
        lwz r12, 0x168(r31)
        lwz r12, 0x%(VIS)X(r12)
        cmpwi r12, 0
        beq hv_out
        lwz r0, 0(r12)
        li r11, 1
        slw r11, r11, r0
        addi r11, r11, -1
        and r28, r28, r11
        li r30, 0
    hs_loop:
        srw r0, r28, r30
        cmpwi r0, 0
        beq hv_out
        andi. r0, r0, 1
        beq hs_next
        mr r3, r31
        mr r4, r30
        srw r5, r29, r30
        andi. r5, r5, 1
        bl h_vis
    hs_next:
        addi r30, r30, 1
        b hs_loop
    h_vdef:
        li r0, 0
        stw r0, 0x%(BN)X(r3)
        stw r0, 0x%(BN4)X(r3)
        lwz r12, 0x168(r3)
        lwz r12, 0x%(VIS)X(r12)
        cmpwi r12, 0
        beqlr
        lwz r4, 4(r12)
        li r5, -1
        b h_vset
    h_whole:
        lwz r3, 0(r3)
        lwz r3, 0x3118(r3)
        cmpwi r3, 0
        beqlr
        lwz r12, 0(r3)
        lwz r12, 0x%(VSL)X(r12)
        mtctr r12
        bctr
    u_vis:
        lwz r12, 0x168(r31)
        lwz r11, 0x%(MVIS)X(r12)
        cmpwi r11, 0
        beqlr
        lwz r10, 0(r31)
        lwz r10, 0x30F0(r10)
        cmpwi r10, 0
        beqlr
        lwz r10, 0x%(MK)X(r10)
        lwz r0, 0(r11)
        cmplw r10, r0
        bgelr
        slwi r10, r10, 2
        add r11, r11, r10
        lwz r4, 4(r11)
        mr r3, r31
        li r5, -1
        b h_vset
    """ % d)

    def wrap(label, target, after, before=''):
        """a state / slot function: `before`, the ported function (r3 this, r4 its argument), then `after`"""
        st(label, "%s\nmr r3, r31\nmr r4, r29\nbl %s\n%s" % (before, target, after))

    vset = lambda m, c: "li r4, 0x%X\nli r5, 0x%X\nbl h_vsetr" % (m, c)  # noqa: E731
    vdef = "mr r3, r31\nbl h_vdef"
    # Ghos (vmt 0 damage, 1 normal; ModelModulePartialImpl::set_node_visibility(i, b) = the vmt switch). start
    # 0x109C0: normal on, damage off (0x10A7C / 0x10A94); 2 stun enter 0x10AD0: normal off, damage on (0x10B50 /
    # 0x10B68); its update 0x10EE4 when V2 runs out: normal on, damage off (0x10F3C / 0x10F54); 4 dead enter 0x10E84:
    # normal off, damage on (0x10EC0 / 0x10EDC)
    # step 2m: and the gas loop (0x10AA4: play_se(0x8A60000) -> +0x200)
    wrap('gh_start', 'f_ghos_start', "lis r4, 0x8A6\nbl h_se\nstw r3, 0x%X(r31)" % GH_SE,
         before=vdef + "\n" + vset(2, 3))
    wrap('gh2_en', 'f_g2_en', vset(1, 3))
    wrap('gh2_up', 'f_g2_up', "lwz r0, 0x%X(r31)\ncmpwi r0, 0\nbgt.far epi\n%s" % (V(2), vset(2, 3)))
    wrap('gh_dead_en', 'g_dead_en', vset(1, 3))
    # Tiki Buzz (0 Damage1, 1 Damage2, 2 Normal). slot 11 (Wii U 10) 0x7818C: notify_on_damage, then Damage1 on,
    # Damage2 / Normal off; slot 60 0x781CC: Normal only; 3 fly enter 0x78668: Normal only (0x78778..0x78798); 10
    # stomp enter 0x77F04: Damage2 only (0x77FD8..0x77FF8); 11 gone enter 0x77E50: set_visibility(0) (0x77EA0)
    wrap('tk_start', 'f_tiki_start', '', before=vdef)
    wrap('tk_fly_en', 't_fly_en', vset(4, 7))
    wrap('tk_stomp_en', 't_stomp_en', vset(2, 7))
    wrap('tk_gone_en', 't_gone_en', "mr r3, r31\nli r4, 0\nbl h_whole")
    st('tk_dmg', "mr r3, r31\nmr r4, r29\n" + call(BI_NOTIFY_DMG) + "\nmr r28, r3\n" + vset(1, 7) + "\nmr r3, r28")
    st('tk_60', vset(4, 7))
    # Spiny (0 togezo, 1 paipo, the egg). start 0x36CE0: var != 0 the Spiny (paipo off, togezo on: 0x36D54 / 0x36D64),
    # var 0 the egg (0x36D94 / 0x36DA4); the hatch L622F4 (tgv_hatch, from tg_hatch): node 2's rotation zeroed
    # (set_node_rotate(2, 0) 0x62354 + the model's dirty call), paipo off, togezo on (0x6237C / 0x62394); slot 60
    # 0x376A4: an egg (var != 1) hatches => 5 (the 3DS's vt+0x124: change_state_interrupt)
    st('tgv_start', vdef + "\nlwz r0, 0xC(r31)\nli r4, 2\ncmpwi r0, 0\nbeq tgvs_s\nli r4, 1\ntgvs_s:\nli r5, 3\n"
       "bl h_vsetr\nmr r3, r31\nmr r4, r29\nbl tg_start")
    st('tgv_hatch', """
        li r0, 0
        stw r0, 8(r1)
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        lwz r3, 0(r31)
        lwz r3, 0x30F0(r3)
        li r4, 2
        addi r5, r1, 8
        li r6, 0
    """ + call(SET_NODE_ROT) + """
        cmpwi r3, 0
        beq tgvh_v
        lwz r3, 0(r31)
        lwz r3, 0x3118(r3)
        lwz r12, 0(r3)
        lwz r12, 0x%X(r12)
        mtctr r12
        bctrl
    tgvh_v:
    """ % MODEL_NODE_DIRTY + vset(1, 3))
    st('tg_60', "lwz r0, 0xC(r31)\ncmpwi r0, 1\nbeq.far epi\nbl tg_hatch\nli r4, 5\nb goi")
    # Paratroopa / Koopa (0 the wing). start 0x7234C: walking (var 2 / 3) the wing off (0x724A8); the wing loss
    # (pt_dewing: slot 69 0x73C00's 0x73C3C, slot 20 -> 9) and 9's enter 0x72740 (0x727BC): the wing off; the shell's
    # end 0x73A24: the thrown item made (not 0x50000000) -> set_visibility(0) (0x73BC8). Not ported: slot 13
    # (0x72DB0, the capture motion) and state 21's set_visibility(1) (0x734C8; no code enters 21)
    st('ptv_start', vdef + "\nlwz r0, 0xC(r31)\ncmpwi r0, 2\nblt ptvs_g\n" + vset(0, 1) +
       "\nptvs_g:\nmr r3, r31\nmr r4, r29\nbl pt_start")
    # Waddle Dee (0 Cparasol, 1 Larm, 2 Lparasol, 3 Rarm, 4 Rparasol, 5 damage, 6 normal). wd_show = 0x5D04C, called
    # by start 0x7B9F0, every state's enter (1-7) and slot 51 0x5D034 (sync_lr_and_direction, then it): variation 2 /
    # 3 both arms, no parasol, and unless the motion is 0 (Damage) the normal face; 0 / 1 by the motion (MotionModule
    # +0x38; 3DS +0x40) and lr (L = lr -1.0): Jump 9 / Landing 10 / Walk 13 Rarm !L, Rparasol L, Larm L, Lparasol !L;
    # Turn 12 the other way round; ParasolFall 11 the centre parasol, no arm; the normal face. Not ported: its
    # +0x1EC (8 / 9) and the acc+0x88 module's vt+0x34 calls (the parasol's node), the parasol variations' sway
    # (slot 55 0x7C480: node scale, not a mesh)
    st('wd_show', """
        lwz r12, 0(r31)
        lwz r12, 0x30F0(r12)
        lwz r6, 0x%(MK)X(r12)
        lwz r0, 0xC(r31)
        cmplwi r0, 1
        ble wds_par
        li r4, 0x0A
        li r5, 0x1F
        cmpwi r6, 0
        beq wds_set
        li r4, 0x4A
        li r5, 0x7F
        b wds_set
    wds_par:
        lwz r12, 0(r31)
        lwz r12, 0x311C(r12)
        lwz r7, 0x60(r12)
        lis r8, 0x%(LH)04X
        li r5, 0x7F
        li r4, 0x41
        cmpwi r6, 11
        beq wds_set
        li r9, 0x52
        li r10, 0x4C
        cmpw r7, r8
        beq wds_l
        li r9, 0x4C
        li r10, 0x52
    wds_l:
        mr r4, r10
        cmpwi r6, 12
        beq wds_set
        mr r4, r9
        cmpwi r6, 9
        beq wds_set
        cmpwi r6, 10
        beq wds_set
        cmpwi r6, 13
        bne.far epi
    wds_set:
        bl h_vsetr""" % dict(MK=MOT_KIND, LH=WD_LR_LEFT >> 16))
    show = "mr r3, r31\nbl wd_show"
    for i, lab in ((1, 'g_fall_en'), (2, 'wd_para_en'), (3, 'g_land_en'), (4, 'd_walk_en'), (5, 'g_turn_en'),
                   (6, 'd_jump_en'), (7, 'g_dead_en')):
        wrap('wd%d_en' % i, lab, show)
    wrap('wd_start', 'w_start', show, before='bl wd_aer')      # step 2j: the aerial module (the parasol fall)
    orig51 = VT_WORDS[0][(0xC + 8 * 51) // 4] if VT_WORDS[0] else 0
    st('wd_51', "mr r3, r31\nmr r4, r29\n" + call(orig51) + "\n" + show)
    # the parasol drop 0x5CF90 (slots 69 / 71 / 13): var 0 / 1 -> var + 2 and initialize (vt+0xA0: slot 40); not
    # ported: generate_article(0) (the dropped parasol), the acc+0x88 calls, W+0x3C = +0x1E0. The damage face
    # 0x5CF18: both arms, no parasol, damage on, normal off. Slot 69 0x7C938: drop, damage face, 0; slot 71 0x7C460:
    # drop, damage face, BehaviorImpl::notify_on_death; slot 60 0x7C5FC: normal on, damage off
    # step 2l: generate_article(0, false) (0x5CFBC): the parasol, the Wii U's weapon kind 0xAD (art_dee, wd_para_cb)
    st('wd_drop', "lwz r3, 0xC(r31)\ncmplwi r3, 1\nbgt.far epi\naddi r3, r3, 2\nstw r3, 0xC(r31)\nmr r3, r31\n"
       "li r4, 0\nli r5, 0\n" + call(GEN_ART) + "\nmr r3, r31\nbl w_init")
    wdmg = "mr r3, r31\nbl wd_drop\n" + vset(0x2A, 0x7F)
    st('wd_69', wdmg + "\nli r3, 0")
    st('wd_71', wdmg + "\nmr r3, r31\nmr r4, r29\n" + call(NOTIFY_DEATH))
    st('wd_60', vset(0x40, 0x60))
    # Waddle Doo (0 blink1, 1 blink2, 2 normal, 3 tear). slot 55 0x7D8A8 (every frame, after the state's update):
    # not blinking -> the counter (+0x194) - 1; in the 3DS's state 10 (dead: ours 6) the tear and open eyes, the flag
    # off; in 3 (walk): the counter out -> random_range(P5 30, P6 50) frames, the phase count 0, blinking; while
    # blinking, phase = ++count / P7 (4): 0 open, 1 blink1, 2 blink2, 3 blink1, 4 open, 5 open and the flag off;
    # other states: open eyes, the flag off. Slots 56 0x7E090 / 57 0x7DFF0: tear and open eyes; 58 0x7E040: open
    d = dict(BN=BLINK_N, BP=BLINK_N + 4, BF=BLINK_F, P5=P(5), P6=P(6), P7=P(7))
    st('do_55', """
        lbz r0, 0x%(BF)X(r31)
        cmpwi r0, 0
        bne do55_s
        lwz r3, 0x%(BN)X(r31)
        addi r3, r3, -1
        stw r3, 0x%(BN)X(r31)
    do55_s:
        lwz r0, 4(r31)
        li r3, 0
        cmpwi r0, 6
        beq do55_dead
        cmpwi r0, 3
        beq do55_walk
        stb r3, 0x%(BF)X(r31)
        b do55_open
    do55_dead:
        stb r3, 0x%(BF)X(r31)
        li r4, 0xC
        b do55_set
    do55_walk:
        lbz r0, 0x%(BF)X(r31)
        cmpwi r0, 0
        bne do55_ph
        lwz r0, 0x%(BN)X(r31)
        cmpwi r0, 0
        bgt do55_open
        lwz r3, 0x%(P5)X(r30)
        lwz r4, 0x%(P6)X(r30)
        bl h_rand
        stw r3, 0x%(BN)X(r31)
        li r0, 0
        sth r0, 0x%(BP)X(r31)
        li r0, 1
        stb r0, 0x%(BF)X(r31)
    do55_ph:
        lhz r3, 0x%(BP)X(r31)
        addi r3, r3, 1
        sth r3, 0x%(BP)X(r31)
        lwz r4, 0x%(P7)X(r30)
        divw r3, r3, r4
        cmplwi r3, 5
        bgt.far epi
        blt do55_tab
        li r0, 0
        stb r0, 0x%(BF)X(r31)
        b do55_open
    do55_tab:
        li r4, 4
        cmpwi r3, 0
        beq do55_set
        cmpwi r3, 4
        beq do55_set
        li r4, 1
        cmpwi r3, 2
        bne do55_set
        li r4, 2
        b do55_set
    do55_open:
        li r4, 4
    do55_set:
        li r5, 0xF
        bl h_vsetr""" % d)
    # Ghos's slot 31 (0x113F0; hit r4: +0x14 the AttackData, +0x20 the attacker record: +0x18 its battle object id,
    # +0x1C its category byte, the Wii U record's ctor 0x02C0EC80 defaults them to 0x50000000 / 6 as the 3DS):
    # category 1 (a weapon): find_battle_object 0x02BF2108([0x102F6C30], &out, id, 0), not is_null 0x02BEF50C and
    # is_weapon_as_fighter(kind = object +4) -> immune; 4 (an item): ItemManager::find_item 0x030563AC, held
    # (Item::is_haved(0): status ([item +0x38E4] +0x48, getter 0x0302DDC0) 2) and its kind (+4) not 0x12 curryshot /
    # 0x24 fireflower -> immune; any other: the AttackData +0x4C byte. Immune: GH_IMM = 1, the SoundModule's (acc+0x30F4,
    # the 3DS acc+0x3074) flag +0x5AD (the 3DS +0x5A2; setter vt+0x84 0x026AB6E8) = 0; else GH_IMM = 0, the flag 1.
    # is_weapon_as_fighter (3DS 0x7B4368, no Wii U twin found): kinds 0x179 / 0x17A (Bayonetta's wickedweavearm /
    # leg) and 0x180-0x182 (Corrin's dragonhand / spearhand / waterdragon), the same numbers in the Wii U's weapon
    # table 0x10419C18. Not ported: play_se(15); is_haved's second test (the 3DS's module +0x38D8 vt+0x2C(4))
    H.asm("""
    gh_31:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r28, 0x20(r1)
        mr r31, r3
        lwz r30, 0x14(r4)
        lwz r29, 0x20(r4)
        li r28, 0
        cmpwi r29, 0
        beq g31_set
        lbz r0, 0x1C(r29)
        cmpwi r0, 1
        beq g31_wpn
        cmpwi r0, 4
        beq g31_item
        cmpwi r30, 0
        beq g31_set
        lbz r0, 0x4C(r30)
        cmpwi r0, 0
        beq g31_set
        b g31_imm
    g31_wpn:
        lis r3, 0x%(BOH)04X
        lwz r3, %(BOL)d(r3)
        addi r4, r1, 8
        lwz r5, 0x18(r29)
        li r6, 0
    """ % dict(BOH=ha(BO_MGR), BOL=sx(BO_MGR)) + call(FIND_BO) + """
        addi r3, r1, 8
    """ + call(BO_IS_NULL) + """
        cmpwi r3, 0
        bne g31_set
        lwz r3, 8(r1)
        lwz r3, 4(r3)
        cmpwi r3, 0x179
        beq g31_imm
        cmpwi r3, 0x17A
        beq g31_imm
        addi r0, r3, -0x180
        cmplwi r0, 2
        bgt g31_set
        b g31_imm
    g31_item:
        lis r3, 0x%(IMH)04X
        lwz r3, %(IML)d(r3)
        lwz r4, 0x18(r29)
    """ % dict(IMH=ha(ITEM_MGR), IML=sx(ITEM_MGR)) + call(FIND_ITEM) + """
        cmpwi r3, 0
        beq g31_set
        lwz r12, 0x%(IST)X(r3)
        lwz r0, 0x48(r12)
        cmpwi r0, 2
        bne g31_set
        lwz r0, 4(r3)
        cmpwi r0, 0x12
        beq g31_set
        cmpwi r0, 0x24
        beq g31_set
    g31_imm:
        li r28, 1
    g31_set:
        stb r28, 0x%(IMM)X(r31)
        lwz r3, 0(r31)
        lwz r3, 0x30F4(r3)
        cmpwi r3, 0
        beq g31_out
        xori r4, r28, 1
        lwz r12, 0(r3)
        lwz r12, 0x84(r12)
        mtctr r12
        bctrl
    g31_out:
        cmpwi r28, 1
        bne g31_x
        li r4, 15
        bl h_se
    g31_x:
        lmw r28, 0x20(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
    """ % dict(IST=ITEM_STATUS, IMM=GH_IMM))
    st('do_56', vset(0xC, 0xF))
    st('do_57', vset(0xC, 0xF))
    st('do_58', vset(0x4, 0xF))


def area_code(D):
    """fix v7: the three game sites that read a kind's area table [param slot]+0x70 (2 x {on, node, 4 floats}:
    area 0 the tread area, kind 0xE; area 1 kind 9) -> the walker kind's own table (its 3DS vl's), else the slot's
    (r9 / r0 / r12 free at each site; the functions keep LR on the stack)"""
    C = Asm(CAVE_C)
    C.asm("""
    area_tab:
        lis r12, 0x%04X
        addi r12, r12, %d
    at_loop:
        lwz r0, 0(r12)
        cmpwi r0, -1
        beq at_none
        cmpw r0, r9
        beq at_found
        addi r12, r12, 8
        b at_loop
    at_found:
        lwz r12, 4(r12)
        lwz r9, 0x%X(r12)
        blr
    at_none:
        li r9, 0
        blr
    """ % (ha(D['ktab']), sx(D['ktab']), CF['AREA']))
    for i, (site, word_, dst, base, kind_reg, shifted) in enumerate(AREA_SITES):
        C.asm("""
    area_%d:
        lwz r%d, 0x70(r%d)
        %s
        bl area_tab
        cmpwi r9, 0
        beq ar%d_out
        mr r%d, r9
    ar%d_out:
        b 0x%08X
        """ % (i, dst, base, ('srwi r9, r%d, 2' if shifted else 'mr r9, r%d') % kind_reg, i, dst, i, site + 4))
    stomp_body(C)
    return C


def read_vt(img):
    return [img.u32(BI_VT + 4 * i) for i in range((0xC + 8 * 74) // 4)]


def patches(img):
    A, B, d = assemble(read_vt(img))
    out = {}
    for lo_, hi_ in REGIONS:
        for addr in range(lo_, hi_, 4):
            out[addr] = 0
    for a in (A, B, A.area, A.stomp, A.e, A.g, A.h):
        for i, w in enumerate(a.words()):
            out[a.base + 4 * i] = w
    for base, words in d.chunks:
        for i, w in enumerate(words):
            out[base + 4 * i] = w
    out[SITE_F] = branch(SITE_F, A.addr('cave_f'))
    out[SITE_T] = branch(SITE_T, A.addr('cave_t'))
    out[SITE_S] = branch(SITE_S, A.addr('cave_s'))
    out[SITE_ROT] = branch(SITE_ROT, A.addr('cave_rot'))
    out[SITE_DEATH] = branch(SITE_DEATH, A.addr('cave_death'))
    for i, (site, _w, _d, _b, _k, _s) in enumerate(AREA_SITES):
        out[site] = branch(site, A.addr('area_%d' % i))
    for w, fn in TWIN_FLIP:
        out[w] = fn if KEEP_FLIP else A.addr('twin_flip')
    assert img.u32(PW_ROW2_UP) == PW_UP2 or A.h.base <= img.u32(PW_ROW2_UP) < LIMIT_H, hex(PW_ROW2_UP)
    out[PW_ROW2_UP] = A.h.addr('pw2_up')          # step 2l (its relocation moved to RELOC_DUMMY: args)
    for sid, (w, orig) in ST_ROW_UP.items():        # step 2m: mczakostalfos's states 7 / 8 update words -> sfN_up
        assert img.u32(w) == orig or A.h.base <= img.u32(w) < LIMIT_H, hex(w)
        out[w] = A.h.addr('sf%d_up' % sid)
    for w, orig, lab in TWIN_LR:
        # the game's word, or an earlier build's w_slr / w_rlr (anywhere in region G: later code moves them)
        assert img.u32(w) == orig or A.g.base <= img.u32(w) < A.g.base + 0x8000, hex(w)
        out[w] = A.g.addr(lab)
    return out, (A, B), d


def args(img):
    out, _a, _d = patches(img)
    res = ['textregion:0x%X' % TEXT_REGION, 'grow:0x%08X' % GROW] + ['0x%08X=0x%08X' % (k, v) for k, v in sorted(out.items())]
    if not KEEP_FLIP:
        res += ['reloc:0x%08X-0x%08X=0x%08X' % (w, w + 4, RELOC_DUMMY) for w, _fn in TWIN_FLIP]
    res += ['reloc:0x%08X-0x%08X=0x%08X' % (w, w + 4, RELOC_DUMMY) for w, _o, _l in TWIN_LR]
    res += ['reloc:0x%08X-0x%08X=0x%08X' % (PW_ROW2_UP, PW_ROW2_UP + 4, RELOC_DUMMY)]
    res += ['reloc:0x%08X-0x%08X=0x%08X' % (w, w + 4, RELOC_DUMMY) for w, _o in ST_ROW_UP.values()]
    return res


def in_cave(addr):
    return any(lo_ <= addr < hi_ for lo_, hi_ in REGIONS)


def main():
    global KEEP_FLIP
    if '--keep-flip' in sys.argv:
        sys.argv.remove('--keep-flip')
        KEEP_FLIP = True
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    import smashrun_enemy_cave as E
    img = E.Image(sys.argv[1])
    if len(sys.argv) == 2:
        print(' '.join(args(img)))
        return
    import rpx_patch
    for site, want in ((SITE_F, WORD_F), (SITE_T, WORD_T), (SITE_S, WORD_S), (SITE_ROT, WORD_ROT),
                       (SITE_DEATH, WORD_DEATH)) + tuple((s, w) for s, w, _d, _b, _k, _x in AREA_SITES):
        got = img.u32(site)
        assert got == want or (got >> 26 == 18 and in_cave(branch_target(site, got))), \
            '0x%08X holds 0x%08X, expected 0x%08X' % (site, got, want)
    if img.u32(E.SITE_F) >> 26 != 18:
        print('warning: tools/smashrun_enemy_cave.py is not applied (it clears this space and aliases its kinds)',
              file=sys.stderr)
    sys.argv = ['rpx_patch.py', sys.argv[1], sys.argv[2]] + args(img)
    rpx_patch.main()


if __name__ == '__main__':
    main()
