# Smash Run port: accuracy audit against the 3DS code

Read-only audit of every ported Smash Run kind against the 3DS code (enemy_fs.cro of the update, code.bin), at HEAD d43a726 (tools/smashrun_walker_cave.py, reference/smashrun_enemy_specs/hand_read.json, docs/smash-run-port.md). Addresses are enemy_fs.cro offsets unless they say code.bin (0x3xxxxx-0x9xxxxx) or Wii U (0x02xxxxxx). The machine-readable copy is reference/smashrun_enemy_specs/accuracy_audit.json.

How it was read: each kind's state functions from the generated listings (tools/s3ds_enemy_spec.py, reference/smashrun_enemy_specs/KIND.json, every item with its address), checked against the ARM where a value or a branch mattered (tools: scratchpad s2c/armdis.py, cbdis.py), then against the cave's labels for that kind. The walkers (Goomba, Shy Guy, Waddle Dee, Waddle Doo, Churine), the White Bear and the Gordo were compared state by state; the fliers and the step 2h kinds were re-read in their own steps (hand_read reread_v4 / step2g_v5 / port_step2h), so this audit lists what those readings left approximated or unported and adds the sounds; for the twins (Zima, Plasma Wisp, Darios, Stalfos) the 3DS fs params were diffed against the Wii U sm params the twins actually read, and the sound calls on both sides were listed.

Severity: **wrong** (differs from the 3DS), **missing** (3DS behaviour not ported), **approximated** (ported differently on purpose), **ok** (checked, matches). Tier: 1 = a player notices first (damage, speed, timing, missing attacks), 2 = visual / sound, 3 = minor.

## Prioritised fix list: the top 15 by player impact

Step 2j (docs/smash-run-port.md "Step 2j") fixed: 6 (the parasol fall; the dropped parasol is still missing), 7 (the view test; set_weak_param still missing), 8, 9, 10, 15, and Waddle Doo's leave-timer reset on damage (1, the beam still missing); Furiijio's beam billboards in its effect models' data.

Step 2k (docs/smash-run-port.md "Step 2k") fixed: 1 (the beam: the Wii U's own weapon kind 0xAF, its trigger, the leave-timer reset by the beam's search), 2 (the sleep powder and its search), 3, 4, 5 (the twins read their kinds' own params: tools/smashrun_twin_params.py, k2_twins), 7 (set_weak_param, approximated: the bear doubles attribute-5 hits' damage itself). Found: every walker kind but the Waddle Doo still borrows mczakozima's param object (its P3 hurtbox capsule, P4): a new framework row. Open: the twins' AI state by state, the dead items (the Wii U has no FieldSmash item manager: read in "Step 2k"), sounds.

Step 2l (docs/smash-run-port.md "Step 2l") fixed: every walker / flier kind's own param object (the framework row: P3 hurtboxes / P4 ground boxes from the kind's vl), the Waddle Doo's hit-effect handle (it sat in V8, the landing's hop flag: a hit skipped the landing's turn), 6 (the dropped parasol: the Wii U's own weapon kind 0xAD), and Lethinium's Fortress-only forced level-2 attack; the twins compared state by state (tools/smashrun_twin_compare.py; open leads in "Not audited (left)"). Found: the Waddle Dee's own parasol shield (start 0x7BB1C: two parts at node 8) is not ported.


Step 2m (docs/smash-run-port.md "Step 2m") fixed: 11 and 12 (every 3DS play_se / stop_se of the ported kinds at its 3DS point; the 3DS soundlabeltable rows of their banks registered in the Wii U's at a battle's start, so the 3DS ids and the converted ACMD ids name the same tones; the twins' own rows pointed at the kinds' banks on Smash Run stages), the tier-2 sound rows (26-35, 37, 39, 41, 42, 44, 47, 49, 51-54), and the Stalfos leads: 9 update, 22 enter and the attack motion variants read equal; 7 / 8 update lacked the 3DS's L5F470 (drop through a passable floor to a target below): ported. The Waddle Dee's parasol shield: read, nothing to port (the 3DS creates its reflector parts off and never turns them on). Found: the Wii U framework's own fs_common sounds (row 0x4A6) have no bank on the Wii U.

Step 2n (docs/smash-run-port.md "Step 2n") fixed: the stompable kinds' tread boxes were in the vl's model units, the 3DS's in the model's scale (AreaInstance set-up code.bin 0x3D9278-0x3D92C4 multiplies an area's offset and size by its node's world scale; Wii U gl +0x1C: Goomba 1.2, Big Goomba 1.3, Paratroopa 1.5): Big Goomba's box now 9.1 / 7.8 / 1.95, the Paratroopa's 3 / 12 / 6 (its half width was 2); Furiijio's mist and every effect emitter with an RGBA texture: the 3DS emitter's own fragment set-up (its MATC block, +0x158: TEV stage 0 takes the colour from the texture's rgb and the alpha from one channel) was read as one shape for both, the colour multiplied by the alpha (cool_air a deep blue): two channels now. Checked, not the cause of the step 2i crash (its log's GX2R lines are every battle's start): the mesh switch (bounded, the engine's own path), the restored NUDs, the Green Shell, the cave's objects and loops (new unicorn guards). Open: the crash's cause (the log build), the Paratroopa's wings (not found statically).

Step 2o (docs/smash-run-port.md "Step 2o") fixed: the step 2i crash (w_start passed h_vdef's r3 = 1 to set_rhombus at every Goomba / Big Goomba / Waddle Dee / Waddle Doo spawn); Lethinium's cannon-shot crash (k2_twins took a twin param file that parsed with an error, e.g. step 2a's 3DS-layout file: G6-G8 empty; now refused by the loader's +8 byte, and no object is deleted before its replacement is in the slots); **Paratroopa / Koopa attack cadence (wrong, tier 1)**: the search tested V0 | V1 <= 0 where the 3DS tests V0 <= 0 and V1 <= 0 (0x72970 / 0x738A0): a search every frame once a counter went negative, the bite's 30-frame cool-down cut to 11 hop frames and the Koopa's 20 to 1 walk frame; the hop's landing frame stopped the frame where the 3DS goes on (0x7292C); the Koopa's counters ran only on frames it moved (the 3DS every walk frame, 0x73928). Open: the Big Goomba gives no bounce in game (same stomp path as the other kinds; its ACMD hitboxes stay active through Stepped: the log build's hs / pd lines), the Paratroopa's wings.

1. Waddle Doo: the beam (its only attack) and its trigger are missing; the leave timer is never reset (600 frames after spawning it leaves mid-fight)
2. Churine: the sleep powder (its only attack) and its search are missing: harmless except its death flight
3. Plasma Wisp: runs on the Wii U sm params: laser 5 % / bkb 60 (3DS 3 / 50), cannon 10 / 160 (9 / 150), search 240 / 200 / 150 (200 / 140 / 20), level timers
4. Darios: Wii U params: 150-frame charge (3DS 90), beam angle 30 / size 4 / power 6 / bkb 70 (3DS 367 / 6 / 5 / 60)
5. Zima: Wii U params: contact 5 % / bkb 60 (3DS 4 % / 70)
6. Waddle Dee: the parasol fall (variation 0, the spawned one) is a normal fast fall; the parasol is never dropped
7. White Bear: set_weak_param(5, 2.0) missing (the 3DS doubles its damage from element 5); its quake ignores the in-view test
8. Waddle Doo: the random 50 % hop is missing; hop threshold 1.0 vs the 3DS 0.5
9. Shy Guy: wall-hop landing threshold 1.0 vs the 3DS 0.5; the run timer is not reset on damage (slot 69)
10. Goomba: the notice hop has no ledge check: it can hop backwards off a ledge
11. Framework: no sound is played by any cave-ported kind (32 play_se / stop_se sites in their 3DS code; the twins play the Wii U twins' own) (fixed, step 2m)
12. Framework: converted ACMD Sound_Effect ids are the 3DS bank ids (Shy Guy, White Bear, Big Goomba, Paratroopa): wrong or no sound on the Wii U (fixed, step 2m: right once the rows are registered)
13. Spiny: the egg is drawn as the Spiny (no mesh swap)
14. Paratroopa / Koopa: the wings stay after the wing loss; item 0x94 (the shell) unchecked
15. Goomba: the dead item is dropped at removal, not on Collapses frame 1
## Full fix list by tier

Tier 1 (gameplay):

1. Framework, slot 69 (on damage) for the walkers (missing): F69 handlers: h69 V2 = 0; o69 V7 = CFG LEAVE + REQ_EFFECT0(0x7190001, center_pos, 1.0)
2. Goomba, notice hop x speed (approximated): CHECK_CLIFF_LR 0x026A6D88 with that distance and -lr; 0 on a hit
3. Shy Guy, hop landing threshold (wrong): hop[0] = 0.5
4. Shy Guy, run timer on damage (missing): F69: V2 = 0
5. Waddle Dee, parasol fall (state 2; variation 0 = the spawned one) (wrong): the flier aerial module (AER, as Paratroopa's pt_*): set_mode_normal / uniform (0, -0.2) and its update
6. Waddle Doo, the beam (its only attack) (missing): a weapon: reuse a Wii U article slot (e.g. plasmawisp's needle path 0x102FE844) with the 3DS beam params, or a cave hitbox sweep
7. Waddle Doo, beam trigger (missing): with the beam
8. Waddle Doo, random hop (missing): a state 6 = g_hop_en without the wall test
9. Waddle Doo, hop landing threshold (wrong): hop[0] = 0.5
10. Waddle Doo, leave timer (wrong): reset V7 on damage (F69) and on the beam
11. Churine, the sleep powder (its only attack) (missing): states 6 / 7: the ACMD hitboxes are already in the converted attack.bin (the hashsets run SleepPowder); the effect is converted (step 2d banks)
12. Churine, search (missing): with the powder
13. White Bear, damage weakness (missing): find the Wii U set_weak_param twin (Behavior helpers 0x026A6xxx-0x026A9xxx) and call it in the start
14. White Bear, view test before the quake (approximated): IN_VIEW 0x026A96BC is mapped since step 2g: use it
15. White Bear, absolute hit (approximated): confirm the field mapping (effect / hitlag / sdi / sound) in game
16. Paratroopa / Koopa, shell item 0x94 (approximated): check item 0x94 in game
17. Zima, contact attack (wrong): give K its own param slot: the Wii U sm layout with the 3DS values (a patched copy of the twin's vl)
18. Plasma Wisp, search groups (wrong): own param slot
19. Plasma Wisp, laser (P7) (wrong): own param slot
20. Plasma Wisp, cannon / hadoudan (P8) (wrong): own param slot
21. Plasma Wisp, large needle (P6 e1) (wrong): own param slot
22. Plasma Wisp, level timers (inline struct) (wrong): own param slot (word map)
23. Darios, charge time (wrong): own param slot
24. Darios, beam attack P6 e0 (wrong): own param slot
25. Darios, beam attack P6 e1 (wrong): own param slot

Tier 2 (visual, sounds):

26. Framework, sounds (missing): see the sound-porting plan (fixed, step 2m)
27. Framework, ACMD sounds in the converted animcmd (wrong): remap the Sound_Effect ids with the bank-id table (sound plan) when converting; until then they play whatever the Wii U has at that id, or nothing (check in game) (fixed, step 2m)
28. Goomba, stomp -> Collapses (approximated): call the Wii U create_dead_item twin on frame 1 (find it beside create_item 0x026A8D78)
29. Goomba, sound: notice (missing): sound plan (fixed, step 2m)
30. Goomba, sound: collapse (missing): sound plan (fixed, step 2m)
31. Shy Guy, sounds (missing): sound plan (fixed, step 2m)
32. Waddle Dee, parasol drop (missing): a weapon article, or an item-like prop
33. Waddle Doo, hit effect (missing): F69
34. Waddle Doo, sounds (missing): with the beam (fixed, step 2m)
35. Churine, sounds (missing): with the powder (fixed, step 2m)
36. White Bear, quake kind (approximated): check the Wii U camera quake table for 7
37. White Bear, sounds (wrong): sound plan (fixed, step 2m)
38. Ghos, damage mesh / rotation order (missing): see the table
39. Ghos, sounds (missing): sound plan (fixed, step 2m)
40. Tiki Buzz, flap rate / meshes (missing): see the table
41. Tiki Buzz, sounds (missing): sound plan (fixed, step 2m)
42. Furiijio, sounds (missing): sound plan (the beam is a handle: stop it in the exit PMFs fu already has) (fixed, step 2m)
43. Propeller Heiho, tilt (missing): see the table
44. Propeller Heiho, sounds (missing): sound plan (loop: one per kind, stop when the last one goes) (fixed, step 2m)
45. Big Goomba, eyes (missing): see the table
46. Big Goomba, damage face meshes (missing): see the table
47. Big Goomba, sounds (missing): sound plan (fixed, step 2m)
48. Spiny, egg mesh (missing): mesh visibility per variation (the model.mta path, or the Wii U set_mesh_visibility twin)
49. Spiny, sounds (missing): sound plan (fixed, step 2m)
50. Paratroopa / Koopa, wing mesh (missing): mesh visibility
51. Paratroopa / Koopa, sounds (wrong): sound plan (fixed, step 2m)
52. Plasma Wisp, sounds (approximated): they play if bank 0xBE2 resolves to K's bank (snd_se_enemy_Plasmawisp, the twin's tone order): check in game (fixed, step 2m)
53. Darios, sounds (approximated): check in game (fixed, step 2m)
54. Stalfos, sounds (wrong): the twin never plays the 3DS's 0000 / 0001 / 0002 at those states: add them after the bank map (fixed, step 2m)

Tier 3 (minor):

55. Framework, fall: speed gate (approximated): a CFG flag: skip h_vy0 for the kinds whose 3DS fall has no speed test
56. Framework, speed y test energy mask (approximated): call the Wii U get_sum_speed3f with -9 for the Kuribo notice
57. Framework, variations (missing): spawn the 3DS layout variations (field_smash placement data) once the kinds are stable
58. Goomba, walk wall / ledge re-entry (approximated): h_chgi
59. Goomba, tread box (approximated): node_global_position(2) as Tiki Buzz does (v5)
60. Shy Guy, state 11 (run wall hop: Run, kinetic 5, sound, landing -> 2 / 10) (missing): port it with 6's code if a caller turns up (variations 1 / 2)
61. Shy Guy, hop wall test (approximated): RAY_CHECK 0x02C39F18 is mapped (step 2g): use it
62. Shy Guy, wait (approximated): fall through to hh_look after the -> 4
63. Shy Guy, brake (approximated): clear_speed_x 0x026A67F4
64. Shy Guy, settle (approximated): check kinetic 21 on the Wii U, drop the guard
65. Waddle Dee, stomp (missing): port with the parasol
66. Waddle Doo, jump -> Fall motion (missing): switch to FALLMOT when vy < 0
67. Waddle Doo, leave (state 9) (approximated): code.bin 0x7B23B4 / 0x7B40B0 read in step 2c v2
68. White Bear, fall speed gate (approximated): framework item
69. Gordo, home steering (approximated): only matters if something moves it
70. Gordo, start flags (missing): find the Wii U twins
71. Gordo, moving variations 1-3 (missing): variations
72. Ghos, immunity rules (approximated): see the table
73. Tiki Buzz, collision object (missing): see the table
74. Furiijio, rotation order (approximated): see the table
75. Furiijio, variations 1 / 2 (missing): see the table
76. Propeller Heiho, material (missing): see the table
77. Propeller Heiho, swap effect (approximated): see the table
78. Propeller Heiho, nearest target (approximated): see the table
79. Big Goomba, is_looped / ledge distance (approximated): see the table
80. Spiny, spin factor (approximated): read the common param from the Wii U accessor
81. Spiny, slots 60 / 13 (missing): see the table
82. Paratroopa / Koopa, bite descent mode (approximated): see the table
83. Paratroopa / Koopa, first falling frame (approximated): see the table
84. Paratroopa / Koopa, slots 13 / 71, states 21 / 22 (missing): see the table
85. Zima, group 4 word 9 (wrong): same
86. Zima, inline struct (corner timer 100-200 etc.) (approximated): map word by word when building the slot
87. Zima, AI code (approximated): not diffed instruction by instruction (left)
88. Plasma Wisp, AI code (approximated): not diffed instruction by instruction (left)
89. Darios, inline struct (approximated): word map
90. Darios, AI code (approximated): not diffed (left)
91. Stalfos, group 4 word 9 (wrong): own param slot
92. Stalfos, group 5 e1 word 1 (wrong): own param slot
93. Stalfos, groups 6 / 7 word 6 (wrong): own param slot (the model scale is K's 2.4 from gl; these may be scale-related)
94. Stalfos, AI code (approximated): not diffed (left)


## Framework (every walker-engine kind)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| AI kinetic energy layout ([[[[acc+0x30B0]+8]+0]+4], Wii U acc+0x3130) | 3DS 0x645FC0 (kinetic 20 setter) writes +0x10 / +0x14 / +0x70 / +0x74 / +0x78 / +0x90 / +0x94 | Wii U twin 0x026A97D0 writes the same offsets; w_init / h_en write the 3DS offsets unchanged | ok | none: this energy is NOT shifted (only the KineticModule get_energy(n) energies are: 3DS clear_speed_x 0x7B0B80 +4/+0xC vs Wii U 0x026A67F4 +0/+8, handled for the aerial module) |
| energy kick | 3DS 0x32C4C / 0x1AB50: module [acc+0x30B0] vt+0x7C with r1 = 0x20000004 only (the spec's float args are stale registers) | h_kick / i_kick: vt+0xFC, r4 = 0x20000004 | ok |  |
| param slot of the walker kinds | each kind its own param object (P3 hurtbox, P4 ground, ...) | step 2l: every walker / flier kind its own static object in its 3DS layout (kind_param_blocks, S2); the framework reads P3 at 0x02D896F4 (+0x44 / +0x48), P4 at 0x02DA2BA0 (+0x5C) | fixed (step 2l) | |
| state frame counter order | common_state_func 0x3DA218: enter, slot 54 (vt+0xD8, reset), update, slot 55 (vt+0xDC, ++) | V-counters reset in the enter, incremented at the end of the update | ok |  |
| fall: speed gate | Kuribo 1 (0x32C70), Waddle Doo 1 (0x7D21C), White Bear 1, Waddle Dee 1: is_touch(8) only; Shy Guy 1 (0x1B0A8) tests speed y <= 0 first | g_fall_up always waits for h_vy0 <= 0 | approximated | a CFG flag: skip h_vy0 for the kinds whose 3DS fall has no speed test |
| speed y test energy mask | Kuribo 4 (0x325F4) get_sum_speed3f(-9) (every energy but 3) | h_vy0 = get_current_speed 0x026A678C = get_sum_speed3f(1) | approximated | call the Wii U get_sum_speed3f with -9 for the Kuribo notice |
| slot 69 (on damage) for the walkers | Shy Guy 0x1BF70 (run timer +0x174 = 0), Waddle Doo 0x7E0E0 (leave timer = 600, hit effect 0x7190001 at center_pos), Waddle Dee 0x7C938 (parasol helpers 0x5CF90 / 0x5CF18), Churine 0x3DDE8 (powder effect removed in 7); all return 0 | VT slot 69 = BehaviorImpl's for these kinds (F69 0) | fixed in step 2j for Shy Guy (hh_69) and Waddle Doo (do_69); Waddle Dee's since step 2i (wd_69); Churine's (the powder effect) with its powder | F69 handlers: h69 V2 = 0; o69 V7 = CFG LEAVE + REQ_EFFECT0(0x7190001, center_pos, 1.0) |
| variations | every kind has per-variation rows / behaviour (P0[var], var-gated ledge turns, Gordo 1-3 movers, Waddle Dee 2/3 parasol-less, Furiijio / Paratroopa rows) | the spawner makes variation 0 (Spiny / Paratroopa pass the create param) | missing | spawn the 3DS layout variations (field_smash placement data) once the kinds are stable |
| sounds | every play_se / stop_se below (Behavior::play_se 0x7B59A8) | every site at the same point (docs/smash-run-port.md "Step 2m": state-enter wrappers SE_EN, the updates / exits / slots, Behavior::play_se 0x026A96EC / stop_se 0x026A970C); the 3DS rows registered in the Wii U soundlabeltable at a battle's start (snd_rows): a 3DS id plays its own tone | fixed (step 2m) |  |
| ACMD sounds in the converted animcmd | Sound_Effect with 3DS ids: Shy Guy Run 0x69B0001 / RunBrake 0x69B0003, White Bear QuakeUp 0x6CC0000 / QuakeLanding 0x6CC0001, Big Goomba 0x2910000-0x2910009, Paratroopa 0x28E0000 / 0x28E0001 / 0x28E0003 / 0x28E0004 | the ids are soundlabeltable rows of the kinds' banks; with the rows registered (snd_rows) they name the same tones on the Wii U: no remap needed (checked by name, smashrun_step2m_test.py) | fixed (step 2m) |  |

## Goomba (kuribo 0x01; create 0x33248, table 0x110138)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| states / transitions 1-10 | 0x32760..0xB4088 (spec states 1-10) | g_fall / g_land / k_walk / k_ntc / k_run / k_brk / k_rt / k_col / g_dead / remove | ok |  |
| walk search | 3: (f16c % 100) == 0, check_target(2, (10, 10), (100, 40)), behind -> reverse_lr, interrupt 4 (0x32F40) | k_walk_up: V0 % 100, h_srch group 0, h_dx, goi 4 | ok |  |
| walk wall / ledge re-entry | 3: reverse_lr + change_state_interrupt(3) (re-enter now) | h_rev + h_chg 3 (deferred) | approximated | h_chgi |
| notice hop x speed | 4 enter 0x33314: check_cliff_distance_lr(f7 x (f8 / gl+0x120 + 2) x -2, -lr): a ledge behind -> E+0x20 = 0, else -0.4 | k_ntc_en: E+0x20 = -0.4 always | fixed (step 2j: kc_ntc_en, Wii U check_cliff_distance_lr 0x026A6CF4) | CHECK_CLIFF_LR 0x026A6D88 with that distance and -lr; 0 on a hit |
| notice timers | 4: airborne until speed y <= 0 and ground; then f16c > 30 -> 5, f170 = 0 | V2 / V0 > P3 30, V1 = 0 | ok |  |
| run | 5: rate 1.0, kinetic 10; search every 60 run frames (150 x 60, offset (0, 10)); behind -> 7; var 1 ledge clear + 7; wall -> 7; > 110 -> 6 | k_run_up | ok |  |
| brake / run turn | 6 RunBrakeL kinetic 2; 7 RunTurnL, end reverse_lr, interrupt 5 (f168 == 5) else 3 | k_brk / k_rt: always => 5 | ok | 7 is only entered from 5 |
| contact attack | P2 entry 0 in 5: power 1, angle 100, kbg 100, fkb 80, bkb 0, size 3, node 4, offset (-1, 0, 0) | KURIBO_BUMP (identical, checked against the vl) | ok |  |
| death flight | 9: Damage at rate 0, bullet(), P2 entry 1 (power 2, angle 361, kbg 100, bkb 50, size 3, node 2); flag 8 -> 10 | g_dead_en / g_dead_up, BULLET_ATK | ok |  |
| stomp -> Collapses | 8 (slot 21): kinetic 0, Collapses, notify_on_death; frame f16c == 1 create_dead_item(1, 10, 0, 0) (0x32A08); end -> 10 | k_col_en / k_col_up; the item drop is the removal's defeat path (fix v3) | fixed (step 2j: kc_col_up calls create_dead_item 0x02DB3944 on frame 1; it drops nothing in the sm category, as the removal's call) | call the Wii U create_dead_item twin on frame 1 (find it beside create_item 0x026A8D78) |
| tread box | 3DS area 0 {on, node 2, 14 x 8, 0, 0} moves with node 2 | TREAD_BOX (7, 2.53, 4) around the posture, not animated | approximated | node_global_position(2) as Tiki Buzz does (v5) |
| sound: notice | 4 enter 0x333A4 play_se(0x28D0002) | se_kuribo_4: the enter, then play_se(0x28D0002) | fixed (step 2m) |  |
| sound: collapse | 8 enter 0x323A4 play_se(0x28D0004) | se_kuribo_8: the enter, then play_se(0x28D0004) | fixed (step 2m) |  |
| RunL ACMD effects | External_Graphic 0x1000026, Graphic_Effect2 0x1000019 every 10 frames (common bank) | converted ACMD runs (hashsets) | ok | common effect ids not re-checked here |

## Shy Guy (heiho 0x0B; create 0x1C024, table 0x10F6CC)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| states 1-10, 12-16 | 0x1A898.. | g_* / h_* (table numbered as the 3DS) | ok |  |
| state 11 (run wall hop: Run, kinetic 5, sound, landing -> 2 / 10) | 0x1B92C / 0x1BBCC | not in the table (no caller found in the spec) | missing | port it with 6's code if a caller turns up (variations 1 / 2) |
| hop landing threshold | 6 update 0x1B5B8: \|y - y0\| > P@0x90 = 0.5 and ray_check == 0 -> 2, else -> 5 | HOPTHR 1.0 (hop=(1.0, 2, 0); the docstring's "inferred" 1.0) | fixed (step 2j: HOPTHR 0.5) | hop[0] = 0.5 |
| hop wall test | ray_check(lr, 5, 1) 0x1B5B8 | check_wall 0x026A68E4 | approximated | RAY_CHECK 0x02C39F18 is mapped (step 2g): use it |
| wait | 3: Wait twice, then random_range(1, 100) <= 50 reverse_lr, -> 4; the search runs that frame too (it can override with 7) | h_wait_up: -> 4 skips the search | approximated | fall through to hh_look after the -> 4 |
| walk | 4: walk row (0.3 / 0.3 / 0 / 0.5 / 2.5), kinetic 1; random_range(60, 120); wall -> 6; var 1/2 ledge -> 5; search every 30 (120 x 40, (10, 10)) -> 7 | h_walk_* | ok |  |
| notice | 7: set_kinetic_jump(0, 2.0, 0, 1), RunHold; two hops (f17c 1 -> 2) -> 8 | row_heiho_jump + kick, V4 | ok |  |
| hold / run | 8: f170 = P0[var].f4 (var 0: 0); 9: f174 = 80 only if <= 0, run row (0.8, 0.0075), kinetic 3; wall: var 1/2 check_wall_jump_or_turn -> 6 else 10 (0x1B70C); off ground f174 = 0 | h_hold / h_run | ok | var 0 only |
| brake | 12: RunBrake, kinetic 2; check_cliff -> clear_speed_x (0x1BB50); end and stopped -> 14 | h_brk_up: h_clear (clear_speed_all) | approximated | clear_speed_x 0x026A67F4 |
| settle | 14: kinetic 21, Fall; kinetic flag 1 -> 4 | h_set_*: + a 120-frame guard (Wii U kinetic 21 unverified) | approximated | check kinetic 21 on the Wii U, drop the guard |
| run timer on damage | slot 69 0x1BF70: +0x174 = 0 | not ported | fixed (step 2j: hh_69) | F69: V2 = 0 |
| contact / bullet | P2 entry 0 (state 9) power 1, angle 50, kbg 100, fkb 60, size 4, offset (0, 8, 1); entry 1 (15) | HEIHO_BUMP / HEIHO_BULLET (identical) | ok |  |
| sounds | play_se(0x69B0002): 6 enter 0x1AC50, 7 enter 0x1BA88, 7 re-hop 0x1BDD0, 11 enter 0x1B99C; ACMD Run 0x69B0001, RunBrake 0x69B0003 | se_heiho_6 / se_heiho_7 (enters), se_heiho_7u (the second hop); 11 has no caller; the ACMD ids right as they are | fixed (step 2m) |  |

## Waddle Dee (waddledee 0x13; create 0x7C9D8, table 0x111B20)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| parasol fall (state 2; variation 0 = the spawned one) | EnemyAerialModule set_mode_normal(accel P0.f6 0.0005, max 10, 10), speed (x kept, -0.2), ParasolFall loop, aerial update with the stick each frame | d_para_en: a normal fall (kinetic 8) with the ParasolFall motion | fixed (step 2j: wd_para_en / wd_para_up in the aerial module; its uniform mode stands in for mode 0, the 0.0005 stick acceleration left out) | the flier aerial module (AER, as Paratroopa's pt_*): set_mode_normal / uniform (0, -0.2) and its update |
| parasol drop | slots 13 / 69 / 71 -> L5CF90 generate_article(0) (the parasol weapon, kind 173, set 0x111C08 {173, 1, 0x7C778}) for var 0 / 1 | step 2l: wd_drop generate_article(0, false) -> the Wii U's weapon kind 0xAD (art_dee, spawner wd_para_cb = 0x7C778, its own init 0x0319F3FC = 0xADF64 on the Dee's param object); slot 13 not ported | fixed (step 2l) | |
| parasol shield | start 0x7BB1C (var 0 / 1): a ShieldModule group of 2 parts at node 8 (PS88 +0x98 ..), switched off by the drop (acc+0x88 vt+0x34 (0 / 1, 0, 0), 0x5CFC0) | not ported (the Wii U Dee has no shield: the drop's two set_status calls left out with it) | missing | Behavior::set_shield_data / the Wii U ShieldModule (acc+0x84) |
| stomp | slot 21 0x7BF04: parasol variations write P@0x8C into the parasol timer | w_tread TREAD 0 (nothing) | missing | port with the parasol |
| walk / turn / jump | 4: Walk 1.2, every 100 frames 50 % -> 6; wall: > 50 -> 5 else 6; var 1/3 ledge -> 5; off ground -> 2 (var 0/1); 6: apex -> 2 | d_walk / g_turn / d_jump, P=(1.2, 100, 50, 50) | ok |  |
| energy | initialize: +0x10 0.2, +8 0.2, +0x20/+0x28 0.3, +0x24/+0x2C 2.5, +0x44 1, +0x18 0.0005 (var 0/1) | same | ok |  |
| bullet | P2 entry 0 (state 7) power 2, angle 361, size 3 | BULLET_ATK (identical but the state word, unread) | ok |  |
| the parasol's reflector (start 0x7BB1C) | a ShieldGroup of two parts (node 8: (P+0x98, 0, 0), size P+0x9C; node 7: (P+0xA0, P+0xA8, P+0xA4), size P+0xAC) added to the module acc+0x88 (vt+0x20), then set_status(0 / 1, 0, 0) (0x684930: status 0 = the part inactive); the drop 0x5CF90 the same; nothing turns it on | none | ok | nothing to port: on the 3DS it never blocks or reflects (step 2m) |
| sounds | none in its code | - | ok |  |

## Waddle Doo (waddledoo 0x19; create 0x7E148, table 0x111C14)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| the beam (its only attack) | 7 BeamShotHold (rate PS8c.f3 1) -> 8 BeamShot (rate 4): 180 / 25 = 7 shots, one every 2 frames, generate_article_angle(0, (30 - 25n) x lr) (0x7DBD4), play_se(0x6A80000) handle +0x1A4 (0x7D0D4), stop_se on the end (0x7DC18) and in exit 0x7DD18; cool-down f180 = 150 | not ported (no Wii U weapon kind) | fixed (step 2k) | the Wii U's own weapon kind 0xAF (the 3DS's 175: native code, descriptor, singleton) with the 3DS's article set {0xAF, 5, the spawner 0x7DDB0 ported} and the Doo's own param object; states 10 / 11 (do_ch_*, do_bm_*) |
| beam trigger | fall 1 / walk 3 / jumps 5, 6: every search_interval(1) = 20 frames once f180 < 0: search_target(1) (60 x 70, offset (30, 20)) -> f19d / 7; walk also f184 = 600 | not ported | fixed (step 2k) | do_bsrch in the walk / fall / jump: search_interval(1), the cool-down, search_target(1); the walk resets the leave timer |
| random hop | 3: f170 counter, random_range(1, 100) <= PS8c.f2 50 -> 6 (Jump, kinetic 5) | not ported | fixed (step 2j: do_owr, state 9 = the 3DS 6) | a state 6 = g_hop_en without the wall test |
| hop landing threshold | 5 update 0x7D77C: \|y - y0\| > P@0xC0 = 0.5 | HOPTHR 1.0 ("a guess") | fixed (step 2j: HOPTHR 0.5) | hop[0] = 0.5 |
| jump -> Fall motion | 5 / 6: is_falling -> set_motion_no_restart(Fall) (0x7D6F0) | Jump motion kept | fixed (step 2j: do_fallm in 5 and 9) | switch to FALLMOT when vy < 0 |
| leave timer | f184 = 600 at start; reset to 600 by a beam (0x7D62C) and by damage (slot 69 0x7E12C); walk counts it down -> 9 | V7 = 600, walk counts down; never reset | fixed (step 2j damage, step 2k the beam's search) | V7 = 600 on damage and on the beam's search finding a fighter |
| hit effect | slot 69 0x7E114: request_effect(0x7190001, center_pos, 1.0), handle +0x1A0 (old one removed) | step 2j: do_69 with the handle in V8 (+0x18C), which g_landt_up reads as the hop-landing flag (a hit skipped the landing's turn); step 2l: its own field DO_FX (+0x1C8) | fixed (step 2l) | |
| turn search | 3: every search_interval(0) = 60 frames search_target(0) behind -> 4 | o_walk_up | ok |  |
| leave (state 9) | init_common_leave(P6 {300, 0.02, 30, ...}): energy +0x30 / +0x34, kinetic 15, effect 0x8000005 | o_leave_* (8) | approximated | code.bin 0x7B23B4 / 0x7B40B0 read in step 2c v2 |
| sounds | beam play_se 0x6A80000 / stop_se | se_waddledoo_11 (-> DO_SE), the motion end and the exit se_doo_11x stop it | fixed (step 2m) |  |

## Churine (churine 0x1F; create 0x3DEE0, table 0x10C550)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| the sleep powder (its only attack) | 6 attack hop (energy +0x24 1, +0x28/+0x2C 10, kinetic 5, Jump) -> 7 SleepPowder: ACMD hitboxes frame 50 (id 1, power 1, angle 361, kbg 7, size 8, offset (0, 4, 11), effect 13 = sleep) and 70 (id 2, kbg 3, size 25, offset (0, 4, 40)) to 125; from frame 40 follow effect 0x71F0000 (rate 1.4, scale 1); play_se(0x6B00001) on landing (0x3DB28); effect end -> 5, cool-down 210 | not ported ("no data") | fixed (step 2k) | states 8 / 9 (the 3DS 6 / 7): the hop, SleepPowder (its converted ACMD hitboxes: effect 9 = sleep, the 3DS's value; "13" above is the CollisionPart word), the follow effect 0x71F0000 and set_rate_last 1.4, the cool-down 210; slot 69 / dead enter remove it |
| search | walk: every search_interval(0) (3) frames search_target(0) (100 x 35, (5, 5)) -> 6 (turn first, f170 = 1); a first-frame flag f171 -> 6 once | search=() (none) | fixed (step 2k) | ch_srch: search_target(0) every 3 frames (V0), the cool-down (V1), behind -> turn first (V2), the start's first-frame attack (V3) |
| walk / hop / turn | 3: initialize again, Walk; wall -> 4; ledge -> 5; 4: landing higher than 20 and no wall -> 2 (f178), else 5 | c_walk / c_jump / g_hop_up (HOPTHR 20) | ok |  |
| bullet | P2 entry 0 (state 8) power 1, angle 361, size 3 | CHURINE_BULLET (identical) | ok |  |
| sounds | play_se 0x6B00001 (powder) | ch_pw_up: play_se(0x6B00001) with the powder effect | fixed (step 2m) |  |

## White Bear (whitebear 0x40; create 0x7F420, table 0x111E8C)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| damage weakness | start: set_weak_param(5, P0.f19 2.0) | not ported | fixed, approximated (step 2k) | no weak table on the Wii U (none of 0x5F6D44 / 0x5F6D6C / 0x966BE8 has a twin): slot 31 notes attribute-5 hits (AttackData +0x43), slot 10 doubles their damage through set_current_damage before BehaviorImpl's notify_on_damage; the knockback is the hit's own |
| view test before the quake | 6 end: is_in_view_area() -> 7 else 3 | taken as true | fixed (step 2j: wb_hold_up, IN_VIEW) | IN_VIEW 0x026A96BC is mapped since step 2g: use it |
| quake kind | request_quake(7) on landing | QUAKE_KIND 6 | approximated | check the Wii U camera quake table for 7 |
| absolute hit | P6 {state 9, power 10, angle 90, kbg 100, bkb 40, 1.0, 1.0, 1.0, 2, 1, ...} on the first fighter whose module +0x24 vt+0x68 == 0 | ABS_WORDS via MSC set_abs / hit_absolute; "grounded" = MSC StatusModule(1) == 0 | approximated | confirm the field mapping (effect / hitlag / sdi / sound) in game |
| states / timers | walk V1 60-120, search 60, cool-down 60, QuakeHold 1.5, jump +0x24/+0x2C 1.5, +0x3C 0.1, fall +0x2C 3 / +0x3C 1, landing < 180 -> 9, quakes 3 with 50 >> (n - 1) % | cave states 1-11 | ok |  |
| fall speed gate | 1: is_touch only | g_fall_up waits for vy <= 0 | approximated | framework item |
| effects | landing 0x7400000 / 0x7400001 (request_effect) | step 2c v2 | ok |  |
| sounds | ACMD QuakeUp 0x6CC0000, QuakeLanding 0x6CC0001 (no play_se in code) | ACMD ids right as they are (row 0x6CC registered) | fixed (step 2m) |  |

## Gordo (gordo 0x08; create 0x1A470, table 0x10F55C)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| home steering | 1 update helper 0x65D20: get_energy(0) speed = (home - position) x 0.5 each frame | kinetic -1 (holds still) | approximated | only matters if something moves it |
| start flags | set_test_coll_stop(1), set_invincible_global(0) | not ported | missing | find the Wii U twins |
| moving variations 1-3 | state 2: along x / y at 0.5 (set_correct 5), or the layout path | not spawned | missing | variations |
| contact | P2 entry 0: power 10, angle 65, kbg 50, fkb 50, bkb 100, size 8, node 3 | GORDO_SPIKE (identical) | ok |  |
| sounds | none | - | ok |  |

## Ghos (ghos 0x11; create 0x11560, table 0x10D350)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| states / homing / leave 1200 / stun / immunity | re-read in steps 2e-2g v4 (hand_read ghos) | code_f gh_*, f_g31 / f_ghos_dmg | ok |  |
| immunity rules | slot 31 0x113F0: weapon / held item / +0x5A2 flag | AttackData +0x4C byte | approximated |  |
| damage mesh / rotation order | set_node_visibility, set_rotation_order_xyz (slot 55) | not ported | missing |  |
| sounds | start (slot 41) play_se(0x8A60000) -> handle +0x200 (0x10AA4); stop_se on damage when kinetic flag 2 (slot 11 0x110F4) and on remove (slot 28 0x11180); immune hit play_se(15) (slot 31 0x11454, common id 15) | gh_start -> GH_SE, se_gh_dmg / se_gh_rm stop it, gh_31 plays 15 on an immune hit | fixed (step 2m) |  |

## Tiki Buzz (tikibuzz 0x0F; create 0x78630, table 0x10E134)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| states / dive / stomp | re-read v4 / v5 (hand_read) | code_f tk_* | ok |  |
| collision object | start: GroundCollisionObject +0x141 = 4, +0x142 = 0, set_circle_follow_node(2) | not mapped (Wii U layout past +0x100 differs) | missing |  |
| flap rate / meshes | MotionModule +0x50, set_mesh_visibility, set_visibility(0) | not ported | missing |  |
| sounds | 4 hold 0x89C0000 (0x78170), 5 dive 0x89C0001 (0x77A0C), 10 stomped 0x89C0002 (0x78040), 11 gone 0x89C0003 (0x77EF0) | se_tikibuzz_4 / 5 / 10 / 11 | fixed (step 2m) |  |

## Furiijio (furiijio 0x1A; create 0x6DC6C, table 0x10D168)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| states / beam / sweep / effects | re-read v4 / v5 / v6 | code_f fu_* | ok |  |
| rotation order | set_rotation_order_zxy | no Wii U setter | approximated |  |
| variations 1 / 2 | P0 rows 1 / 2 | not spawned | missing |  |
| sounds | 2 / 5 charge 0x6A90001 (0x6D1EC / 0x6D5EC), 4 / 7 beam 0x6A90002 (0x6C3CC / 0x6CAF4) -> handle +0x260, stop_se in the exits (0x6D0E0 / 0x6D4E0); slot 57 bound 0x6A90003 (0x6DC34) | se_furiijio_2 / 5, se_furiijio_4 / 7 (-> FU_SE), se_fu_bexit stops it, se_fu_57 / se_fu_69 the bound sound | fixed (step 2m) |  |

## Propeller Heiho (propellerheiho 0x47; create 0x9AA38, table 0x111278)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| states / item | re-read v4 | code_ph | ok |  |
| tilt | slot 55: posture rot z toward -vx / P15 x P20 30 in 5, 1 deg a frame; the stun's 5-degree return | not ported | missing |  |
| material | set_frame_material / set_rate_material(0) at start | not ported | missing |  |
| swap effect | the item's EffectModule, joint 0 | Behavior request at the hold position + offset | approximated |  |
| nearest target | EnemyAiModule::get_nearest_fighter from the posture | get_nearest_target | approximated |  |
| sounds | start play_se(0x6D20000) the propeller loop, counted per kind (slot 41 0x990C8); swap 0x6D20001 (slot 55 0x9A070) | se_ph_start / se_ph_71 / se_ph2_up with ph_snd {handle, count} (reset each battle: approximated), se_ph_55 the swap | fixed (step 2m) |  |

## Big Goomba (dekakuribo 0x23; create 0x86D84, table 0x10F374)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| states 1-13, stomp (+25 damage, 40 HP) | step 2h reading | code_h dk_* | ok |  |
| is_looped / ledge distance | WalkL loop test; check_cliff_distance_lr with the distance | WalkL 30 / 0.3 frames; check_cliff without the distance | approximated |  |
| eyes | slot 3 0x869F8: set_frame_material(angle to fighter 0 / 2pi x 60, clamp 1..59) | not ported | missing |  |
| damage face meshes | set_mesh_visibility | not ported | missing |  |
| sounds | 2 landing 0x2910009 (0x85E84), 8 brake 0x2910008 (0x859AC), 10 stepped 0x291000C (0x86C70), 11 collapse 0x291000B (0x85A20); ACMD WalkL 0x2910000 / 0x2910001, RunL 0x2910002 / 0x2910003, RunTurnL 0x2910006 / 0x2910007, AngryL 0x2910009 | se_dekakuribo_2 / 8 / 10 / 11; the ACMD ids right as they are | fixed (step 2m) |  |

## Spiny (togezo 0x4E; create 0x37F14, table 0x1119CC)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| egg / hatch / walk / leave / slot 69 | step 2h reading | code_h tg_* | ok |  |
| egg mesh | var 0 draws the Paipo (egg) mesh, var 1 the Spiny | no mesh swap: the egg is drawn as the Spiny | missing | mesh visibility per variation (the model.mta path, or the Wii U set_mesh_visibility twin) |
| spin factor | EnemyParamAccessor +0x198 +0x90 x +0xA0 | 30 deg / frame per unit speed | approximated | read the common param from the Wii U accessor |
| slots 60 / 13 | forced hatch (caller unknown) / capture motion | not ported | missing |  |
| sounds | 5 hatch play_se 0x6D90000 (0x37AA4) | se_togezo_5 | fixed (step 2m) |  |

## Paratroopa / Koopa (patapata 0x03; create 0x74108, table 0x110C80)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| hop / bite / wing loss / leap / shell | step 2h reading | code_h pt_* | ok |  |
| bite descent mode | aerial set_mode_normal(0, 0, 0, 0, 10, 10) | uniform mode (0, -P0 f11) | approximated |  |
| wing mesh | wing loss hides the wings (set_mesh_visibility) | wing mesh stays | missing | mesh visibility |
| first falling frame | energy 0 writes | not ported | approximated |  |
| slots 13 / 71, states 21 / 22 | - | not ported | missing |  |
| shell item 0x94 | create_item_and_throw(0x94) | 0x026A8F10; the Wii U item's code / files unchecked | approximated | check item 0x94 in game |
| sounds | ACMD only: Bite 0x28E0000 (frame 10), JumpAttack 0x28E0001 (11), NokonokoMode 0x28E0003, ShellMode 0x28E0004 | the ACMD ids right as they are (row 0x28E registered) | fixed (step 2m) |  |

## Zima (zima 0x0E; Wii U twin mczakozima 0x5A)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| contact attack | 3DS fs vl P2 entry 0: power 4, bkb 70, word 32 = 60 | Wii U sm vl: power 5, bkb 60, word 32 = 240 (the twin reads the Wii U sm vl (param slot[K] = slot[twin], step 2a S-hook), not the 3DS fs vl) | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| group 4 word 9 | 15.0 | 6.0 | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| inline struct (corner timer 100-200 etc.) | 9 words / entry | 12 words / entry (Wii U layout; 3DS values 100 / 200 / 50 / 5.0 / 4.5 present) | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| AI code | 3DS states 1-7 (hand_read zima) | Wii U mczakozima 0x026D6680..0x026D7CA0 | approximated | not diffed instruction by instruction (left) |
| sounds | none in the 3DS code | the twin has no Behavior::play_se either | ok |  |

## Plasma Wisp (plasmawisp 0x12; Wii U twin mczakoplasmawisp 0x57)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| search groups | P1 e0 range 200; e1 interval 5, 140, 20 | Wii U 240; 10, 200, 150 | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| laser (P7) | power 3, bkb 50 | power 5, bkb 60 | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| cannon / hadoudan (P8) | power 9, bkb 150 | power 10, bkb 160 | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| large needle (P6 e1) | word 2 = 1, word 6 = 50 | word 2 = 3, word 6 = 60 | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| level timers (inline struct) | 28 words: 100 / 250 / 10 / 50 ... | 32 words (Wii U layout): 200 / 200 / 20 / 5 ... | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| AI code | 3DS states 1-10 (hand_read plasmawisp) | Wii U mczakoplasmawisp (0x026D0000..0x026D1E00) | approximated | not diffed instruction by instruction (left) |
| sounds | 0x6A20000 needle / laser charge (4 / 6 enter 0x89E88 / 0x89DA8), 0x6A20001 needle (4 end 0x8A12C), 0x6A20002 laser (0x89FB8), 0x6A20003 cannon (0x8A23C), 0x6A20004 level up (helper 0x899E4) | the twin's 0xBE20000-4 at the 3DS's points; row 0xBE2 names the kind's bank (5019) on a Smash Run stage (snd_rows) | fixed (step 2m) |  |

## Darios (darios 0x1D; Wii U twin mczakodarios 0x58)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| charge time | P0.f6 = 90 frames | Wii U 150 | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| beam attack P6 e0 | angle 367, fkb 10, size 6, word 16 = 6.0, word 27 = 15 | angle 30, fkb 1, size 4, 10.0, 13 | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| beam attack P6 e1 | power 5, bkb 60, size 6, word 27 = 15 | power 6, bkb 70, size 4, 13 | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| inline struct | 6 words / entry | 9 words / entry | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| AI code | 3DS states 1-8 | Wii U mczakodarios (0x026CBA64..0x026CF4DC) | approximated | not diffed (left) |
| sounds | charge 0x6B20000 (4 enter 0x2F484), beam 0x6B20001 (5 enter 0x2E028), stop_se handle +0x19C (helper 0x643AC) | the twin's 0xBE30000 / 1; row 0xBE3 names the kind's bank (5037) on a Smash Run stage | fixed (step 2m) |  |

## Stalfos (stalfos 0x30; Wii U twin mczakostalfos 0x59)

| item | 3DS (address, value) | our port (label / value) | severity | suggested fix |
|---|---|---|---|---|
| group 4 word 9 | 20.0 | 11.0 | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| group 5 e1 word 1 | 0 | 3 | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| groups 6 / 7 word 6 | 3.0 | 2.4 | fixed (step 2k) | the kind's own file in the twin's layout (tools/smashrun_twin_params.py: every word the 3DS's, the twin's extra words kept), parsed into its own object by k2_twins |
| AI code | 3DS states 1-24 (hand_read stalfos); hitboxes ACMD (K's attack.bin runs) | Wii U mczakostalfos (0x026D2000..0x026D6000), compared state by state (step 2l tools/smashrun_twin_compare.py; step 2m read: 9 update, 22 enter, the attack motions' variants equal; 7 / 8 update lacked L5F470) | fixed (step 2m) | sf7_up / sf8_up (kind 0x30): the game's updates with the 3DS's drop through a passable floor to a target below (its floor ray from the posture, not the touch position: approximated) |
| sounds | 0x6BF0005 landing (2 / 14 / 16 enter), 0x6BF0000 (10 / 11 ground touch), 0x6BF0001 (13), 0x6BF0002 (15 enter), slot 29 0x6BF0003, slot 30 0x4A60079 (common bank) | the twin plays all of them (0xBE40000 / 1 through its helper 0x026D4DA0, the audit missed it); row 0xBE4 names the kind's bank (5052) on a Smash Run stage; slot 30's 0x4A60079 (fs_common, no Wii U bank) not mapped | fixed (step 2m) but slot 30 |  |

## Sound-porting plan

Ported in step 2m (docs/smash-run-port.md "Step 2m", tools/smashrun_sound.py). A sound id is (soundlabeltable row << 16) | label in both games; the row gives the bank id (the .nus3bank's BINF id), the label the tone (Wii U 0x0311EDBC / 0x0311EF88 on [[[[0x102F7288]] + 0x29C] + 4]). The Wii U table has no row for any Smash Run bank and their 3DS row numbers are all empty in it: snd_rows registers the 3DS rows at their own numbers at a Smash Run battle's start (in the loaded table, nothing shipped), so every 3DS id, in code and in the converted ACMD, names the same tone on the Wii U (compared by name). The twins' rows 0xBE2-0xBE4 name the kinds' banks on Smash Run stages (put back elsewhere). The Wii U API:

| call | 3DS | Wii U |
|---|---|---|
| Behavior::play_se(id, bool) -> handle | 3DS 0x7B59A8 -> SoundModuleImpl::play_se 0x4C4B84 | Wii U 0x026A96EC(r3 behaviour, r4 id, r5 bool) -> SoundModule (acc+0x30F4) 0x02C72214(module, id, 0, bool, 0, 0, 0) |
| Behavior::stop_se(handle, int) | 3DS 0x4C3148 -> SoundModuleImpl::stop_se_handle 0x4C3158 | Wii U 0x026A970C(r3, r4 handle) -> 0x02C73750 |
| bank file | 3DS enemy/KIND/snd_se_enemy_KIND.nus3bank | Wii U sound/se/snd_se_enemy_%s.nus3bank with the capitalised name table 0x1041A534 (the converted 3DS banks, BINF ids unchanged) |

Still open: row 0x4A6 (snd_se_fs_common: the Wii U framework's own enemy sounds, e.g. 0x02DBF40C / 0x02DBF434, and Stalfos's slot 30) has no Wii U bank file.

Per kind (every 3DS sound, its id and when it plays):

- Shy Guy: play_se(0x69B0002): 6 enter 0x1AC50, 7 enter 0x1BA88, 7 re-hop 0x1BDD0, 11 enter 0x1B99C; ACMD Run 0x69B0001, RunBrake 0x69B0003
- Waddle Dee: none in its code
- Waddle Doo: beam play_se 0x6A80000 / stop_se
- Churine: play_se 0x6B00001 (powder)
- White Bear: ACMD QuakeUp 0x6CC0000, QuakeLanding 0x6CC0001 (no play_se in code)
- Gordo: none
- Ghos: start (slot 41) play_se(0x8A60000) -> handle +0x200 (0x10AA4); stop_se on damage when kinetic flag 2 (slot 11 0x110F4) and on remove (slot 28 0x11180); immune hit play_se(15) (slot 31 0x11454, common id 15)
- Tiki Buzz: 4 hold 0x89C0000 (0x78170), 5 dive 0x89C0001 (0x77A0C), 10 stomped 0x89C0002 (0x78040), 11 gone 0x89C0003 (0x77EF0)
- Furiijio: 2 / 5 charge 0x6A90001 (0x6D1EC / 0x6D5EC), 4 / 7 beam 0x6A90002 (0x6C3CC / 0x6CAF4) -> handle +0x260, stop_se in the exits (0x6D0E0 / 0x6D4E0); slot 57 bound 0x6A90003 (0x6DC34)
- Propeller Heiho: start play_se(0x6D20000) the propeller loop, counted per kind (slot 41 0x990C8); swap 0x6D20001 (slot 55 0x9A070)
- Big Goomba: 2 landing 0x2910009 (0x85E84), 8 brake 0x2910008 (0x859AC), 10 stepped 0x291000C (0x86C70), 11 collapse 0x291000B (0x85A20); ACMD WalkL 0x2910000 / 0x2910001, RunL 0x2910002 / 0x2910003, RunTurnL 0x2910006 / 0x2910007, AngryL 0x2910009
- Spiny: 5 hatch play_se 0x6D90000 (0x37AA4)
- Paratroopa / Koopa: ACMD only: Bite 0x28E0000 (frame 10), JumpAttack 0x28E0001 (11), NokonokoMode 0x28E0003, ShellMode 0x28E0004
- Zima: none in the 3DS code
- Plasma Wisp: 0x6A20000 needle / laser charge (4 / 6 enter 0x89E88 / 0x89DA8), 0x6A20001 needle (4 end 0x8A12C), 0x6A20002 laser (0x89FB8), 0x6A20003 cannon (0x8A23C), 0x6A20004 level up (helper 0x899E4)
- Darios: charge 0x6B20000 (4 enter 0x2F484), beam 0x6B20001 (5 enter 0x2E028), stop_se handle +0x19C (helper 0x643AC)
- Stalfos: 0x6BF0005 landing (2 / 14 / 16 enter), 0x6BF0000 (10 / 11 ground touch), 0x6BF0001 (13), 0x6BF0002 (15 enter), slot 29 0x6BF0003, slot 30 0x4A60079 (common bank)
- Waddle Doo: beam play_se(0x6A80000) on entering 8 (0x7D0D4), handle +0x1A4; stop_se at the end (0x7DC18) and in the exit (0x7DD30).
- Churine: play_se(0x6B00001) in the powder state 7 (0x3DB28), on landing with +0x17C == 0.

## Not audited (left)

- The twins' AI (step 2l, tools/smashrun_twin_compare.py over every state's enter / update / exit, docs/smash-run-port.md "Step 2l"): the four Wii U state tables have the 3DS's state count (7 / 10 / 8 / 24), their exits at the same states, the same transitions, kinetics, ground flags and motions; Zima and Darios match (the remaining token differences are the 3DS's array reads and a node rotation the 3DS summary keeps in a helper). Lethinium: the Wii U adds a level-2 forced attack (+0x1E4 timer, P+0x138) and a cool-down word (P+0x134) after its level-2 attack: fixed (pw2_up, the param word). Stalfos (step 2m): 9 update, 22 enter and the attack motions' variants read equal; 7 / 8 update lacked the 3DS's L5F470 drop (ported: sf7_up / sf8_up); its sounds are the twin's own (all but slot 30's fs_common one).
- The fliers (Ghos, Tiki Buzz, Furiijio, Propeller Heiho) and the step 2h kinds (Big Goomba, Spiny, Paratroopa) were not re-read line by line here: their own steps' readings (hand_read) are taken as the 3DS side, and their listed approximations are carried over.
- The common effect ids in the converted ACMD (0x1000019 / 0x1000026 / 0x100008E) and the twins' effect calls.
