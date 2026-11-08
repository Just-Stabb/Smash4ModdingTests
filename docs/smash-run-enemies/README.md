# Smash Run enemies: behaviour specs read from the 3DS code

One spec per Smash Run enemy kind (the 80 kinds 0x00-0x4F with a `param/enemy/fs/enemy_param_vl_<kind>.bin`), read
from the 3DS update's `enemy_fs.cro` (one `app::Behavior<Kind>` per enemy on the shared `Behavior` / `BehaviorImpl`
framework, docs/smash-run-port.md) and the kinds' own data, for porting the behaviours to the Wii U with parity.

- `reference/smashrun_enemy_specs/<kind>.json`: the machine-readable spec (schema below).
- `docs/smash-run-enemies/<kind>.md`: the same, readable: the hand-read summary first ("Reading", for the kinds read
  so far), then the generated overview, motions, attack params, params, states, vtable overrides, helpers, weapons,
  ACMD.
- `reference/smashrun_enemy_specs/hand_read.json`: the hand-read conclusions (the generator merges them in).
- `tools/s3ds_enemy_spec.py`: the generator (usage in its docstring):

```
python3 tools/s3ds_enemy_spec.py --cro S3DS/cro_upd/enemy_fs.cro --params S3DS/param/enemy/fs \
    --enemy-root S3DS/enemy --symbols S3DS/static_symbols.txt --readme [KIND ...]
```

## How to read a spec (the porting recipe)

- **States** are the 3DS state ids (rows of the kind's state table, `{enter, update, exit}` ARM PMFs). The Wii U
  framework is the same (`change_state` slot 72 = pending, applied at the end of the frame; 73 = interrupt, exit and
  enter now). State 0 is unused in every kind.
- **When it is dangerous.** Three sources, in this order:
  1. The framework's `Behavior::set_attack_data(state)` (vtable slot 45, called by both change_state bases on every
     state change): `AttackModule::clear_all`, then for each entry of param group 2 (`InnerEnemyAttackParam`, 42
     words) whose `state` field equals the new state, `create_attack_data(entry)` + `AttackModule::set_attack(id,
     part)`. So a kind's contact hitboxes are its P2 entries, live exactly in the states they name (the "attack armed
     on entry" lines). A second path arms the entry whose state = slot 48's value when slot 47 returns true (every
     kind here keeps the defaults: false / -1). **23 kinds override slot 45** (table below): their hitboxes are set
     by their own code (listed under Vtable overrides / Helpers), the P2 table is only data.
  2. Explicit attack calls in the state code (`create_attack_data`, `AttackModuleImpl::set_attack` / `clear`,
     `set_attack_power`, `hit_attack_absolute` ...), listed per state.
  3. ACMD `attack.bin` scripts of the motions a state plays (the "ACMD hitboxes" lines; 3DS little-endian ACMD,
     the Wii U command table).
  4. Articles (weapons): `generate_article*(index, ...)`; the kind's `enemy_article_data_set_<kind>` lists the weapon
     kinds; each `WeaponSpecializer_Enemy<Kind><Name>` is analysed too (its attack usually comes from a 41-word
     param group of the owner = InnerEnemyAttackParam without the state field).
  The defeated body is dangerous too: in 60 of the 77 behaviours the death state (slot 67) calls `bullet()` (the
  body flies off) with a P2 "death" entry (power 1-12, angle 361, bkb 50) for it; the other 17 (bacula, cucco,
  darknut, deathskull, generator, gordo, killercannon, koshinigami, magnumkiller, orne, patapata, pooka, shotzo,
  togezo, totsukotsu, wanwan, wanwanpile) have no such state, a death state 0 (cannot die by damage) or their own
  death code.
- **Param references**: `P<g>[e].<field>=value`: group g of the kind's fs vl in the reader's order (P0 the kind's
  basic params, P1 the search params (`search_type, interval, range_x?, range_y?, offset_x?, offset_y?, f6`), P2
  the attack list; P3 / P4 / P5 are common to every kind too, read by the framework, meaning not resolved), entry e (or `var->...`: indexed by the variation, values per variation shown). `P@0xNN` a scalar
  member, `PSNN.fK` field K of an inline struct member at offset NN, `gl.fNN` the common enemy_param entry (0x228
  bytes, not read: the 3DS gl file is not in the dump copy). A param of another kind (hard-coded slot) is prefixed
  with that kind.
- **Expressions**: `this.fNNN` behaviour fields (3DS offsets; Wii U = 3DS - 4 for the Behavior part), `this.var`
  the variation, `this.move_x` / `move_y` the AI stick (+0x14 / +0x18), `mod.X` the accessor's modules (3DS
  acc+0x3000+off: Ai 0x3040, Attack 0x3048, Damage 0x3054, Effect 0x3058, Ground 0x305C, Kinetic 0x3068, Motion
  0x3070, Model 0x3098, Posture 0x309C (+0x14 position, +0x60 lr), KineticEnergy 0x30B0), `retN:name` a call's
  result, `phi(rX)` a value that differs between paths, `?` unknown. `mod.KineticEnergy...+0xNN = v` lines are the
  AI movement energy's parameters (`[[[acc+0x30B0]+8]+0]+4`, see below).
- **Guards**: `[if A && B]` = the conditions that hold on every acyclic path to the call (the last three in the .md;
  all in the JSON); `[when C]` = a predicated call. Branches on the kind index and null checks of the param slot /
  modules are folded (always taken).

## Schema (`<kind>.json`)

Top-level keys (one per line group; values compact JSON):

| key | content |
|---|---|
| `kind`, `kind_index` | name, index in the Wii U / 3DS enemy kind table (0x1041A22C) |
| `behavior_class`, `create`, `ctor`, `object_size` | `app::Behavior<Kind>`, CRO addresses (hex strings, CRO offsets) |
| `notes` | anything the generator could not resolve (param parse errors ...) |
| `params` | `object_offset` (in the FieldSmash param block), `ctor`, `reader`, `members`: the param object's members in read order: `{type: array, offset, index, elem_size, format [[width, count]...], offsets, widths, names, values: [[entry fields]...]}`, `{type: struct, offset, format, offsets, values: [[...]]}`, `{type: float/int/..., offset, value}`. The slot `[EnemyParamAccessor+0x60+4*kind]` is this object: array `i` count at +offset+8, data at +offset+0xC |
| `motion_data_set`, `motions` | the set's address; per motion index: `name` (short), `anim` (full .bch / OMO name), `hash` (crc32 of `anim`, zero start), `flags` (0x10000 normal, 0x50000 loop, 0x400000 ...), `frames`, `loop` (H3D flag), `script_hashes` (crc32 of name.init / name / name.exit: the ACMD keys) |
| `meshes` | `normal.vmt` names (the index `set_mesh_visibility` takes) |
| `vtable`, `vtable_slots` | per slot: `{name, fn}` (own function), `{name, impl, shared: true}` (framework import), `returns` (N for a `mov r0, #N; bx lr`, `nop` for `bx lr`). Slot names: README "framework" below |
| `state_table`, `states` | per state: `id`, `enter` / `update` / `exit` (function addresses or null), `summary`: `{enter: [items], enter_derived: [items], update..., exit...}` |
| items | `{cat, call, args, at, motion?, mesh?, state?, slot?, impl?, if?, guard?}` for calls (`cat`: motion, kinetic, ground, target, random, attack, effect, sound, spawn, visibility, lr, lifecycle, state, helper, vcall, module, icall, other), `{cat, store, val, ...}` for stores (kinetic energy, motion module, this fields), `{cat: param, ref, value}` for each param read. `*_derived`: the key items (state, motion, attack, visibility, spawn, effect, sound, lifecycle, kinetic, lr) of the function and every local helper it reaches, with `via` (helper chain) and the guards concatenated |
| `vtable_functions` | items of each overridden vtable slot |
| `helpers` | items of each other local function reached (`L<addr>` in the items) |
| `functions` | every analysed function: `blocks: [{addr, guard, events, term}]`; events `{a, op: call / lcall / vcall / mcall / icall / store / param, ...}`; `term` `{type: if (cond, then, else) / goto / fall / return / tailcall / switch}`: a pseudo-code listing of the function |
| `attacks` | the P2 entries with names: `entry, state, id, part, node, power, angle, kbg, fkb, bkb, size, x, y, z, bone` (bone: `node` as the enemies' node -> bone converter reads it (3DS 0x7B8F10, Wii U 0x030833B4): node 0 -> bone 0, node N -> model.jtb entry N - 1 (1-based), node >= 0x1000 -> bone node - 0x1000), `other` (the remaining words with their AttackData offsets) |
| `joints` | model.jtb joints as bone names |
| `acmd` | per motion: `{attack / effect / sound: {main / init / exit: [[command, params...]...]}}` (3DS ACMD decoded with tools/acmd_info.json) |
| `articles` | `article_data_set`, `entries` ([weapon kind, count?, data ptr, 0] per article index), `weapons`: per weapon class `{class, vtable, slots: {k: {name, fn, items}}}` |
| `tags` | rough automatic class: walker / flyer / crawler / stationary, + shooter, spawner, links, acmd-hitboxes, large (>= 20 states) |
| `hand_read` | (read kinds) `class, summary, variations, states {id: text}, danger [{states, source, power, angle, kbg, fkb, bkb, size, node, offset, note}], targeting, kinetics, projectiles, death, meshes` |

## Framework notes (3DS, all kinds)

- Factory: code.bin imports each `Behavior<Kind>::create(EnemyModuleAccessor&, kind, variation)` by name;
  create = `operator new(size)` + the ctor (Behavior ctor, BehaviorImpl init, vptr, `set_motion_label(hashsets)`,
  `set_damage_motion_label(9 motion indices)`).
- Start: slot 40 `initialize` (writes the movement energy's parameters from params), slot 41 `start`
  (`set_rhombus`, stick x = posture lr, face `get_nearest_target` with `check_turn_to_target` + `reverse_lr`, the
  first state, usually 1 = Fall), slot 42 `initialize_after`.
- Per frame: slot 4 runs the current update PMF, which writes the AI stick (this+0x14 / +0x18 -> AiInput); slot 55
  (`every_frame?`, inferred) is a per-frame hook (frame counters, blinking, squash animations); slot 54 resets the
  state frame counter (inferred from Kuribo: +0x16C = 0).
- Damage / death: the framework's `notify_on_damage` handles reactions with the damage motions; slots 64 / 65 / 66
  name the states to return to after damage (ground / air / default) and 67 the death state, which in most
  kinds plays a damage pose at rate 0, calls `bullet()` (the body flies off with the P2 "death" entry armed) and goes
  to the remove state (`EnemyManager::remove_enemy_by_id`) when the kinetic module's flag 8 is set (60 kinds; see
  above for the others). Slots 69 / 71
  (`notify_on_death`) are where kinds drop items (parasol) or kill effects. Slot 21 (`notify_on_tread?`, inferred:
  Kuribo -> Collapses, Dekakuribo takes 25 damage, Patapata loses its wings, Tikibuzz) is the stomp reaction.
- Search: `search_interval(i)` = P1[i].interval; `search_target(i)` = `EnemyAiModule::check_target(P1[i].type,
  this+0x14, P1[i].f4, f5, f2, f3, f6)` (code.bin 0x9EA658) -> fighter entry or -1; `check_turn_to_target(target, 0)`
  = 1 when the target is behind.
- Movement: `change_kinetic(id)` selects the movement (code.bin 0x6463BC: ids 0-27, each enabling energy 0 in mode
  `id`; 10 enables two): 0 stop, 1 walk, 2 brake, 3 run, 4 bounce, 5 jump, 8 fall, 10 Kuribo's walk/run, 21, 26
  float / trace (meanings from use). The behaviours write the energy's parameters at `[[[acc+0x30B0]+8]+0]+4`
  (+0x08 .. +0x44) in `initialize` and some state enters: the field meanings are not resolved (the Wii U kinetic
  module has the same layout: copy the values).
- Motions: `change_motion_state(index, start frame, rate, loop, f)`; the walk enter of Kuribo also writes the rate
  into MotionModule +0x50.

### Framework calls used by the behaviours

3DS addresses from `static_symbols.txt` (code.bin); Wii U addresses where docs/smash-run-port.md or the step 2
research give them.

<!-- generated:framework -->
| function (enemy_fs import) | 3DS code.bin | Wii U | functions using it |
|---|---|---|---|
| `Behavior::change_motion_state` | 0x007B3C2C | 0x02DB420C | 749 |
| `GroundModuleImpl::set_attach_ground` | 0x004E1814 | 0x02C37C6C | 680 |
| `EnemyKineticModuleImpl::change_kinetic` | 0x006463BC | 0x02DBE00C | 590 |
| `GroundModuleImpl::is_touch` | 0x0096A600 | 0x02C38A24 | 327 |
| `MotionModuleImpl::is_end` | 0x00953EBC |  | 315 |
| `GroundModuleImpl::set_passable_check` | 0x004E1B84 |  | 246 |
| `Behavior::play_se` | 0x007B59A8 | 0x026A96EC | 217 |
| `Behavior::get_nearest_target` | 0x009EAA5C | 0x026A7008 | 162 |
| `Behavior::check_turn_to_target` | 0x009EAC10 | 0x026A6984 | 149 |
| `Behavior::move` | 0x009EB574 / 0x009EB588 | 0x026A66D0 | 135 |
| `Behavior::random_range` | 0x007B0AD8 / 0x007B0B2C |  | 134 |
| `Behavior::get_current_speed` | 0x0096EBE8 |  | 120 |
| `Behavior::set_mesh_visibility` | 0x006618C4 |  | 116 |
| `EnemyAerialModuleImpl::update` | 0x005F66AC / 0x005F6B80 |  | 113 |
| `Behavior::search_interval` | 0x009EA818 | 0x026A706C | 108 |
| `Behavior::get_target_pos` | 0x009EA7AC |  | 103 |
| `Behavior::search_target` | 0x0095782C / 0x009EA658 | 0x026A70FC | 102 |
| `EnemyManager::remove_enemy_by_id` | 0x003E53EC | 0x02D9C0E0 | 78 |
| `Behavior::Behavior` | 0x007B5CB0 | 0x02DB2DF0 | 77 |
| `BehaviorImpl::change_common_state` | 0x003DBAA0 |  | 77 |
| `BehaviorImpl::change_state_base` | 0x003DB3D8 | 0x026A3A44 | 77 |
| `BehaviorImpl::change_state_interrupt_base` | 0x003DD678 | 0x026A3AD4 | 77 |
| `operator new` | 0x00103E41 / 0x00159F28 | 0x03374578 | 77 |
| `Behavior::check_wall` | 0x009EA4B8 | 0x026A68E4 | 74 |
| `Behavior::set_rhombus` | 0x007B087C | 0x026A65BC | 74 |
| `Behavior::set_motion_label` | 0x007B211C | 0x02DB5B08 | 73 |
| `Behavior::bullet` | 0x007B304C | 0x02DB5158 | 67 |
| `Behavior::request_effect` | 0x007B12E0 / 0x007B1338 |  | 64 |
| `MotionModuleImpl::set_node_rotate` | 0x00501328 |  | 59 |
| `Behavior::set_damage_motion_label` | 0x007B4E6C | 0x02DB5AD8 | 51 |
| `GroundModuleImpl::set_correct` | 0x004E06DC |  | 51 |
| `Behavior::check_cliff` | 0x009EA55C |  | 50 |
| `EnemyAerialModuleImpl::set_current_speed` | 0x005F5C58 / 0x005F5C7C |  | 50 |
| `PostureModulePartialImpl::rot` | 0x009811F0 |  | 47 |
| `Behavior::set_kinetic_jump` | 0x006462EC |  | 43 |
| `Behavior::remove_effect` | 0x007B0EF0 |  | 41 |
| `Behavior::request_follow_effect` | 0x007B4AEC | 0x026A9584 / 0x026A95F8 | 41 |
| `Behavior::set_motion_no_restart` | 0x007B4B44 |  | 41 |
| `Behavior::center_pos` | 0x009EA464 |  | 39 |
| `EnemyAerialModuleImpl::set_mode_none` | 0x005F58C8 |  | 38 |
| `Behavior::request_quake` | 0x007B0F0C |  | 37 |
| `EnemyAerialModuleImpl::get_speed` | 0x00966BDC |  | 35 |
| `EnemyAerialModuleImpl::set_mode_normal` | 0x005F5A9C |  | 35 |
| `KineticModuleImpl::get_energy` | 0x00533B08 |  | 35 |
| `Behavior::set_visibility` | 0x00661720 |  | 34 |
| `Behavior::clear_speed_all` | 0x007B1628 |  | 33 |
| `Behavior::success_by_percent` | 0x007B3BC4 | 0x026A8618 | 33 |
| `EnemyAiModuleImpl::get_fighter_pos` | 0x00957970 |  | 30 |
| `Behavior::stop_se` | 0x004C3148 |  | 29 |
| `MotionModuleImpl::set_frame_material` | 0x007FB7FC |  | 29 |
| `BehaviorImpl::notify_on_damage` | 0x003DA8BC | 0x026A3564 | 28 |
| `BehaviorImpl::notify_on_death` | 0x003DA850 |  | 28 |
| `EffectModuleImpl::req` | 0x004D98CC / 0x004D9A98 | 0x02C29D10 | 28 |
| `EnemyAerialModuleImpl::EnemyAerialModuleImpl` | 0x005F6BAC |  | 28 |
| `Behavior::set_rotation_order_xyz` | 0x007B4CEC |  | 27 |
| `ModelModulePartialImpl::node_global_position` | 0x00661954 / 0x00661A98 |  | 27 |
| `Behavior::change_script_state` | 0x006E469C / 0x007B3CB8 | 0x02DB4184 | 26 |
| `Behavior::random_choice` | 0x007B0DC4 / 0x007B0E80 |  | 25 |
| `MotionModuleImpl::end_frame` | 0x00953F68 / 0x00953F98 |  | 24 |
| `AttackModuleImpl::set_attack` | 0x004CB5D4 / 0x004CB7E8 | 0x02C086A8 | 23 |
| `BattleObjectManager::find_battle_object` | 0x00592390 |  | 23 |
| `Behavior::calc_angle` | 0x007B01D8 |  | 23 |
| `Behavior::disable_hit` | 0x007B0864 |  | 23 |
| `AttackModuleImpl::clear_all` | 0x004CF6A0 | 0x02C08324 | 22 |
| `Behavior::create_attack_data` | 0x007B2A1C / 0x007B2B60 | 0x02DB572C | 22 |
| `Behavior::generate_article` | 0x007B1BBC |  | 21 |
| `GroundCollisionObject::get_ground_normal` | 0x0096A538 |  | 21 |
| `Behavior::clear_speed_x` | 0x007B0B80 |  | 19 |
| `BehaviorImpl::update_on_skip` | 0x003DA80C |  | 19 |
| `MotionModuleImpl::change_motion` | 0x004FFEDC | 0x02C5D730 | 19 |
| `Behavior::init_common_leave` | 0x007B23B4 |  | 18 |
| `Behavior::ray_check` | 0x007B5A9C / 0x007B5B10 |  | 18 |
| `Behavior::update_common_leave` | 0x007B40B0 |  | 18 |
| `EnemyAerialModuleImpl::set_target_point` | 0x005F5C40 |  | 18 |
| `AttackModuleImpl::clear` | 0x004CE5AC |  | 17 |
| `Behavior::get_lr_to_nearest_target` | 0x009EB178 |  | 17 |
| `Behavior::set_shield_state` | 0x007B2124 |  | 17 |
| `Behavior::set_weaken_type` | 0x007B18F0 |  | 17 |
| `EnemyAiModuleImpl::check_target` | 0x0095783C |  | 16 |
| `MotionModuleImpl::is_looped` | 0x005048D0 |  | 16 |
| `MotionModuleImpl::set_rate_material` | 0x005015AC |  | 16 |
| `Behavior::success_by_fraction` | 0x007B408C |  | 15 |
| `MotionModuleImpl::set_node_translate` | 0x00501954 |  | 15 |
| `Behavior::is_exist_floor_under` | 0x007B4230 |  | 14 |
| `EffectModuleSimple::remove` | 0x0055DFDC |  | 14 |
| `GroundModuleImpl::is_passable_ground` | 0x0096AB30 |  | 14 |
| `ModelModulePartialImpl::set_node_visibility` | 0x006618D4 |  | 14 |
| `Behavior::calc_donkey_handslap_damage_fs` | 0x007B55BC |  | 13 |
| `Behavior::check_cliff_distance` | 0x009EAEC0 |  | 13 |
| `Behavior::check_cliff_distance_lr` | 0x009EAED4 |  | 13 |
| `Behavior::create_dead_item` | 0x007B1984 |  | 13 |
| `Behavior::enable_hit` | 0x0042FB14 |  | 13 |
| `Behavior::is_in_view_area` | 0x009EA804 |  | 13 |
| `Behavior::notify_on_remove` | 0x007B36E4 | 0x02DB40E4 | 13 |
| `EnemyAerialModuleImpl::set_mode_braking` | 0x005F5B48 |  | 13 |
| `EnemyAerialModuleImpl::set_target` | 0x005F5884 |  | 13 |
| `MotionModuleImpl::set_node_scale` | 0x00501034 |  | 13 |
| `Behavior::get_target_distance_sqr` | 0x009EB0EC |  | 12 |
| `Behavior::hit_return_frame` | 0x009EA9B0 |  | 12 |
| `Behavior::reverse_lr` | 0x007B034C | 0x026A7A20 | 12 |
| `Behavior::set_current_damage` | 0x007B3688 |  | 12 |
| `EventDispatcher::remove_listeners` | 0x0080EE78 |  | 12 |
| `FighterEntry::get_fighter_accessor` | 0x003FE868 |  | 12 |
| `Behavior::set_node_global_position` | 0x007B5224 |  | 11 |
| `KineticModuleImpl::get_kinetic_type` | 0x0095952C |  | 11 |
| `BattleObjectAccessor::is_null` | 0x009620F0 |  | 10 |
| `BattleObjectAccessor::module_accessor` | 0x00961F8C |  | 10 |
| `Behavior::ray_check_from_pos` | 0x007B2E34 / 0x007B2E78 |  | 10 |
| `Behavior::set_damage_motion_label_simple` | 0x007B55D4 |  | 10 |
| `EnemyAerialModuleImpl::set_max_speed` | 0x005F58A0 |  | 10 |
| `Behavior::check_cliff_lr` | 0x009EA704 | 0x026A6D88 | 9 |
| `Behavior::clear_speed_y` | 0x007B0BAC |  | 9 |
| `Behavior::enable_ground_damage` | 0x007B417C |  | 9 |
| `EnemyAerialModuleImpl::set_mode_slip_normal` | 0x005F6024 |  | 9 |
| `EnemyGroundLineTraceModuleImpl::end_trace` | 0x0070A090 |  | 9 |
| `EnemyManager::find_by_btlobj_id` | 0x0093E940 |  | 9 |
| `HitModuleImpl::set_status` | 0x007B6EF0 |  | 9 |
| `BattleObjectAccessor::is_active` | 0x00962144 |  | 8 |
| `Behavior::calc_angle3` | 0x007B05E4 |  | 8 |
| `Behavior::generate_article_angle` | 0x007B4BF8 |  | 8 |
| `Behavior::is_falling` | 0x009EA500 |  | 8 |
| `EffectModuleImpl::set_scale` | 0x004DB438 |  | 8 |
| `EnemyManager::request_defeat_boss` | 0x003E5898 |  | 8 |
| `AttackModuleImpl::sleep` | 0x004CE99C |  | 7 |
| `BattleObjectAccessor::center_pos` | 0x00961EA8 |  | 7 |
| `BattleObjectAccessor::check_transition_status` | 0x00962030 |  | 7 |
| `BattleObjectAccessor::pos` | 0x009620B4 |  | 7 |
| `Behavior::get_node_global_position` | 0x009EB214 |  | 7 |
| `EffectModuleImpl::is_exist_effect` | 0x007FA27C |  | 7 |
| `EnemyAerialModuleImpl::set_mode_homing` | 0x005F59C4 |  | 7 |
| `EnemyAerialModuleImpl::set_mode_slip_homing` | 0x005F5F58 |  | 7 |
| `GroundModuleImpl::ray_check` | 0x009533F4 / 0x009534A8 |  | 7 |
| `GsbDrawModel::get_world_matrix` | 0x007FA8CC |  | 7 |
| `HitModuleImpl::set_check_catch` | 0x007B6FF4 |  | 7 |
| `MotionModuleImpl::get_world_matrix` | 0x00501468 |  | 7 |
| `SimpleGameSceneBase::process_timing` | 0x005BC9D0 |  | 7 |
| `BattleObjectAccessor::category` | 0x00962110 |  | 6 |
| `Behavior::check_wall_jump_or_turn` | 0x009EB008 |  | 6 |
| `Behavior::finalize_common_leave` | 0x007B475C |  | 6 |
| `Behavior::get_current_speed_all` | 0x009EAD88 |  | 6 |
| `Behavior::get_ground_angle` | 0x007B01B4 |  | 6 |
| `Behavior::get_target_angle` | 0x009EA8F8 |  | 6 |
| `Behavior::invalid_ignore_damage` | 0x009EADF4 |  | 6 |
| `Behavior::is_current_stopped` | 0x009EAAC8 |  | 6 |
| `Behavior::is_motion_playing_at_frame` | 0x009EB334 |  | 6 |
| `Behavior::is_need_damage_fly` | 0x009EAB00 |  | 6 |
| `Behavior::set_rotation_order_zxy` | 0x007B4D04 |  | 6 |
| `DamageModuleImpl::damage` | 0x009512CC |  | 6 |
| `DamageModuleImpl::init_damage` | 0x004D30BC |  | 6 |
| `EnemyAerialModuleImpl::set_mode_homing_extend` | 0x005F60F0 |  | 6 |
| `ItemManager::find_item` | 0x003CD464 |  | 6 |
| `BattleObjectAccessor::kind` | 0x009620CC |  | 5 |
| `Behavior::damage_turn` | 0x007B0814 | 0x02DB4E84 | 5 |
| `Behavior::delete_hit` | 0x007B0338 |  | 5 |
| `Behavior::disable_ground_damage` | 0x007B46BC |  | 5 |
| `Behavior::disable_jostle_ex` | 0x007B22D4 |  | 5 |
| `Behavior::get_current_damage` | 0x009512B8 |  | 5 |
| `Behavior::reset_gravity` | 0x007B0F64 |  | 5 |
| `Behavior::set_lr` | 0x007B5778 | 0x026A780C | 5 |
| `Behavior::sync_lr_and_direction` | 0x00646274 | 0x026A7BD8 | 5 |
| `Behavior::update_weaken` | 0x007B0FE8 |  | 5 |
| `EffectModuleImpl::set_pos` | 0x004DAF8C |  | 5 |
| `EnemyAerialModuleImpl::enable_extend_swing` | 0x005F5C94 |  | 5 |
| `EnemyAerialModuleImpl::set_mode_uniform` | 0x005F5BD4 |  | 5 |
| `EnemyAiModuleImpl::get_nearest_fighter` | 0x00958038 |  | 5 |
| `EnemyGenerator::get_remeine_gen_count_from_appear_id` | 0x0046755C |  | 5 |
| `EnemyKineticModuleImpl::get_sum_speed3f` | 0x0096EBFC |  | 5 |
| `HitModuleImpl::set_invincible_global` | 0x0042EE50 |  | 5 |
| `MotionModuleImpl::set_frame` | 0x00504928 |  | 5 |
| `SoundModuleImpl::is_playing` | 0x004C27BC |  | 5 |
| `ValueControllerAim::update` | 0x0058E5C0 |  | 5 |
| `ValueControllerStandard::update` | 0x00688974 |  | 5 |
| `AttackModuleImpl::set_offset` | 0x004CB8B8 |  | 4 |
| `AttackModuleImpl::set_vector` | 0x004CB8E8 |  | 4 |
| `BattleObjectAccessor::id` | 0x00962090 |  | 4 |
| `Behavior::create_enemy` | 0x007B099C / 0x007B0A18 |  | 4 |
| `Behavior::get_height_from_ground` | 0x007B4C68 |  | 4 |
| `Behavior::get_target_distance` | 0x009EAB20 |  | 4 |
| `Behavior::set_kinetic_brake_ground` | 0x007B51F4 |  | 4 |
| `CameraModuleImpl::is_clip_in` | 0x00950DDC |  | 4 |
| `EffectModuleImpl::req_follow` | 0x004D5E2C |  | 4 |
| `EnemyAerialModuleImpl::set_brake` | 0x005F6BA0 |  | 4 |
| `GroundModuleImpl::get_down_line` | 0x00952704 |  | 4 |
| `Matrix34::get_rotate` | 0x009F2C7C |  | 4 |
| `Matrix34::mul` | 0x0087D4EC |  | 4 |
| `Matrix34::set_quaternion` | 0x0087D1CC |  | 4 |
| `MotionModuleImpl::set_direct_update_mode_material` | 0x007FB8B0 |  | 4 |
| `SoundModuleImpl::play_se` | 0x004C4B84 |  | 4 |
| `StopModulePartialImpl::leave_stop_internal` | 0x00636950 |  | 4 |
| `operator new[]` | 0x0016F148 |  | 4 |
| `BattleObjectAccessor::BattleObjectAccessor` | 0x005CB894 |  | 3 |
| `Behavior::abort_bullet` | 0x007B098C |  | 3 |
| `Behavior::check_turn_to_enemy_target` | 0x009EB294 |  | 3 |
| `Behavior::check_wall_touched` | 0x007B2974 |  | 3 |
| `Behavior::create_item_and_throw` | 0x007B4488 |  | 3 |
| `Behavior::disable_tread` | 0x007B0D50 |  | 3 |
| `Behavior::get_attacker_info` | 0x009EAA18 |  | 3 |
| `Behavior::get_target_distance_x` | 0x009EAD9C |  | 3 |
| `Behavior::ignore_damage` | 0x009EA614 |  | 3 |
| `Behavior::set_attack_data` | 0x007B1694 | 0x02DB58B8 | 3 |
| `Behavior::set_current_speed` | 0x007B24B4 |  | 3 |
| `Behavior::set_shield_data` | 0x007B1828 |  | 3 |
| `EffectModuleImpl::set_rate_last` | 0x004D6B18 |  | 3 |
| `EffectModuleImpl::set_rot` | 0x004DAF98 |  | 3 |
| `EffectModuleImpl::set_visible` | 0x007F9C9C |  | 3 |
| `EffectSystem::set_pause` | 0x007FA304 |  | 3 |
| `EnemyAerialModuleImpl::set_accel` | 0x005F6B94 |  | 3 |
| `EnemyAerialModuleImpl::set_mode_braking_max_speed` | 0x005F625C |  | 3 |
| `EnemyAerialModuleImpl::set_mode_slip_normal_extend` | 0x005F6514 |  | 3 |
| `EnemyGenerator::get_layout_data` | 0x00948AA0 |  | 3 |
| `EnemyKineticModuleImpl::get_sum_speed` | 0x0096EAC4 |  | 3 |
| `FighterManager::get_entry_id` | 0x0046E3A0 |  | 3 |
| `GsbDrawModel::is_visible` | 0x009EE85C |  | 3 |
| `GsbDrawModel::set_visible` | 0x007FA5DC |  | 3 |
| `GsbDrawModel::set_world_matrix` | 0x007FA8D8 |  | 3 |
| `GsbDrawModel::~GsbDrawModel` | 0x007FB9E0 |  | 3 |
| `GsbDrawSceneManager::delete_draw_model` | 0x008369EC / 0x00836A04 |  | 3 |
| `GsbResourceManager::delete_model_request` | 0x008299CC / 0x008299FC |  | 3 |
| `HitModuleImpl::add` | 0x0042EF48 / 0x0042EF90 |  | 3 |
| `HitModuleImpl::clean` | 0x007BF9A8 |  | 3 |
| `HitModuleImpl::set_status_all` | 0x007B6F48 |  | 3 |
| `Item::fall` | 0x0074D6E4 |  | 3 |
| `ItemManager::ejection_item` | 0x00432860 |  | 3 |
| `Matrix34::get_quaternion` | 0x009F2D78 |  | 3 |
| `Matrix34::scale` | 0x0087D69C |  | 3 |
| `Matrix34::set_rotate_xyz` | 0x0087D298 |  | 3 |
| `MotionModuleImpl::get_node_srt` | 0x00953CD8 |  | 3 |
| `ValueControllerAim::ValueControllerAim` | 0x0058E620 |  | 3 |
| `ValueControllerStandard::ValueControllerStandard` | 0x00688A34 |  | 3 |
| `Behavior::add_fighter_powers` | 0x007B25B8 |  | 2 |
| `Behavior::count_createted_active_enemy` | 0x009EB38C |  | 2 |
| `Behavior::disable_jostle` | 0x007B1284 |  | 2 |
| `Behavior::disable_kinetic_damage` | 0x007B4BA8 |  | 2 |
| `Behavior::get_fighter_entry_id_by_btl_obj_id` | 0x007B56D4 |  | 2 |
| `Behavior::get_fighter_situation` | 0x007B4A44 |  | 2 |
| `Behavior::get_pos_on_shape` | 0x007B1C10 |  | 2 |
| `Behavior::hit_attack_absolute` | 0x007B3D28 |  | 2 |
| `Behavior::is_generate_shoot` | 0x009EAA2C |  | 2 |
| `Behavior::is_no_reaction_damage` | 0x009EAE70 |  | 2 |
| `Behavior::is_weapon_as_fighter` | 0x007B4368 |  | 2 |
| `Behavior::set_attack_absolute_data` | 0x007B50AC |  | 2 |
| `Behavior::set_limit_speed` | 0x007B17FC |  | 2 |
| `CEffectScreen::cancel_fill` | 0x008026C8 |  | 2 |
| `CameraMan::instance` | 0x007BE8D4 |  | 2 |
| `CameraModuleImpl::set_status` | 0x004D0474 |  | 2 |
| `ColorBlendModuleImpl::off_flash` | 0x005CD39C |  | 2 |
| `ColorBlendModuleImpl::set_flash` | 0x005CD438 / 0x005CD4BC |  | 2 |
| `EffectModuleImpl::detach_all` | 0x004D5BDC |  | 2 |
| `EffectModuleSimple::kill` | 0x007F9C24 |  | 2 |
| `Enemy::get_protection_priority` | 0x009E7E7C |  | 2 |
| `Enemy::is_flag_death` | 0x00756818 |  | 2 |
| `Enemy::is_linked` | 0x0094BE94 |  | 2 |
| `EnemyDamageModuleImpl::add_weak_param_multi` | 0x005F6D6C |  | 2 |
| `EnemyDamageModuleImpl::set_enable_unique_effect` | 0x005F6CA4 |  | 2 |
| `EnemyGenerator::create_child` | 0x00466228 |  | 2 |
| `EnemyGenerator::get_next_enemy_kind` | 0x00466F14 |  | 2 |
| `EnemyGroundLineTraceModuleImpl::EnemyGroundLineTraceModuleImpl` | 0x0070A170 |  | 2 |
| `EnemyGroundLineTraceModuleImpl::can_inv_trace_start` | 0x00709998 |  | 2 |
| `EnemyGroundLineTraceModuleImpl::get_trace_normal` | 0x009938A8 |  | 2 |
| `EnemyGroundLineTraceModuleImpl::is_ground_or_wall` | 0x007092D4 |  | 2 |
| `EnemyGroundLineTraceModuleImpl::set_inv_start_once` | 0x00709904 |  | 2 |
| `EnemyGroundLineTraceModuleImpl::set_move_ex_flag` | 0x00709234 |  | 2 |
| `EnemyGroundLineTraceModuleImpl::set_speed_normal` | 0x00709244 |  | 2 |
| `EnemyGroundLineTraceModuleImpl::set_trace_param` | 0x00709220 |  | 2 |
| `EnemyGroundLineTraceModuleImpl::setup_trace` | 0x007083D8 |  | 2 |
| `EnemyGroundLineTraceModuleImpl::update` | 0x00709FB8 |  | 2 |
| `EnemyManager::is_roof_attach_type` | 0x003E5874 |  | 2 |
| `EnemyManager::set_already_dead_flag` | 0x003E5C84 |  | 2 |
| `EnemyTerritoryModuleImpl::set` | 0x0068CF70 |  | 2 |
| `FieldSmashManager::get_treasurebox_ejection_data` | 0x00528BA0 |  | 2 |
| `GlobalParameter::global_melee_parameter` | 0x00134C4C |  | 2 |
| `GroundModuleImpl::get_touch_pos` | 0x0095279C |  | 2 |
| `GroundModuleImpl::modify_rhombus` | 0x004E0E20 |  | 2 |
| `GroundModuleImpl::pass_floor` | 0x004E0570 |  | 2 |
| `GsbDrawModel::GsbDrawModel` | 0x007FB968 / 0x007FB98C |  | 2 |
| `GsbDrawModel::is_valid` | 0x009EEB70 |  | 2 |
| `GsbDrawSceneManager::add_draw_model` | 0x008369AC / 0x008369C4 |  | 2 |
| `HitModuleImpl::get_part_size` | 0x00945F90 |  | 2 |
| `ItemParamAccessor::game_param` | 0x0052EABC |  | 2 |
| `ModelModulePartialImpl::set_visibility` | 0x00661730 |  | 2 |
| `MotionModuleImpl::node_rotate` | 0x004FF6C0 |  | 2 |
| `MotionModuleImpl::set_flip` | 0x0050458C |  | 2 |
| `ParameterArrayBase::ParameterArrayBase` | 0x001552BC |  | 2 |
| `ParameterArrayBase::create_base` | 0x0017B428 |  | 2 |
| `ParameterArrayBase::destroy_base` | 0x00169898 |  | 2 |
| `Resource::Resource` | 0x0013F54C / 0x0016BBB0 |  | 2 |
| `ShakeModuleImpl::req` | 0x004C225C |  | 2 |
| `SoundEnemyOrne::is_playing` | 0x00491B58 |  | 2 |
| `SoundEnemyOrne::update` | 0x00491BE4 |  | 2 |
| `ValueControllerAimMinMax::update` | 0x006AF1A8 |  | 2 |
| `level_data::Path::get_length` | 0x0092E868 |  | 2 |
| `level_data::Path::get_point_of_path` | 0x0092E8F0 |  | 2 |
| `operator delete[]` | 0x002FEB54 |  | 2 |
| `BattleObjectAccessor::lr` | 0x0096209C |  | 1 |
| `BattleObjectManager::begin_object` | 0x00591A18 |  | 1 |
| `BattleObjectManager::end_object` | 0x00591658 |  | 1 |
| `Behavior::calc_angle2` | 0x007B04FC |  | 1 |
| `Behavior::calc_angle4` | 0x007B06C0 |  | 1 |
| `Behavior::cancel_reserved_enemy` | 0x007B4478 |  | 1 |
| `Behavior::change_motion_state_script_only` | 0x007B5600 |  | 1 |
| `Behavior::change_script_state_none` | 0x007B509C |  | 1 |
| `Behavior::check_cliff_ray_lr` | 0x007B28A8 |  | 1 |
| `Behavior::comp_angle4` | 0x007B07A8 |  | 1 |
| `Behavior::create_item_and_have` | 0x007B4104 |  | 1 |
| `Behavior::create_reserved_enemy` | 0x007B4568 |  | 1 |
| `Behavior::damage_wakeup` | 0x007B0BD8 |  | 1 |
| `Behavior::disable_hit_part` | 0x007B1B24 |  | 1 |
| `Behavior::disable_shadow` | 0x007B12B0 |  | 1 |
| `Behavior::enable_hit_part` | 0x007B1638 |  | 1 |
| `Behavior::enable_kinetic_damage` | 0x007B470C |  | 1 |
| `Behavior::enable_shadow` | 0x007B0DA8 |  | 1 |
| `Behavior::enable_tread` | 0x00461134 |  | 1 |
| `Behavior::generate_article_pos` | 0x007B41A4 |  | 1 |
| `Behavior::get_distance_on_shape` | 0x007B478C |  | 1 |
| `Behavior::get_enemy_target_pos` | 0x009EACA8 |  | 1 |
| `Behavior::get_node_global_rotation` | 0x009EB254 |  | 1 |
| `Behavior::get_turn_type` | 0x009EA5CC | 0x02DB46BC | 1 |
| `Behavior::invincible_hit` | 0x007B12C8 |  | 1 |
| `Behavior::is_target_alive` | 0x007B1650 |  | 1 |
| `Behavior::is_target_invincible` | 0x007B42C4 |  | 1 |
| `Behavior::remove_all_continual_effect` | 0x004D9458 |  | 1 |
| `Behavior::reserve_enemy` | 0x007B0F50 |  | 1 |
| `Behavior::search_enemy_target` | 0x009EABB8 |  | 1 |
| `Behavior::set_death_flag` | 0x007B13F4 |  | 1 |
| `Behavior::set_flash_color` | 0x007B17CC |  | 1 |
| `Behavior::set_kinetic_controllable_jump` | 0x007B5538 |  | 1 |
| `Behavior::set_kinetic_shoot` | 0x007B24E0 |  | 1 |
| `Behavior::update_hp` | 0x007B5BF4 | 0x02DB4D74 | 1 |
| `BehaviorImpl::damage_reaction` | 0x003DB9E8 |  | 1 |
| `BehaviorImpl::notify_on_capture_cut` | 0x003DBCC8 | 0x026A46F4 | 1 |
| `CEffectScreen::request_fill` | 0x00802BA0 |  | 1 |
| `CameraData::get_clip_bounds` | 0x0093BAF4 |  | 1 |
| `CameraData::is_clip_in` | 0x0093BA90 |  | 1 |
| `DamageModuleImpl::add_damage` | 0x004D2FE4 |  | 1 |
| `DamageModuleImpl::set_weak_param` | 0x004D34C4 |  | 1 |
| `EffectModuleImpl::remove_after_image` | 0x008283E8 |  | 1 |
| `EffectModuleImpl::remove_all_after_image` | 0x004D9648 |  | 1 |
| `EffectModuleImpl::req_after_image_no_parent` | 0x004D96A8 |  | 1 |
| `EffectModuleImpl::reset_common` | 0x004D6544 |  | 1 |
| `EffectModuleImpl::set_alpha` | 0x007FA298 |  | 1 |
| `EffectModuleImpl::set_alpha_last` | 0x004D6B4C |  | 1 |
| `EffectModuleImpl::set_frame` | 0x007FA2D8 |  | 1 |
| `EffectTrailManager::set_offset` | 0x00828310 |  | 1 |
| `EnemyAerialModuleImpl::set_mode_slip_homing_extend` | 0x005F64FC |  | 1 |
| `EnemyDamageModuleImpl::clear_weak_param` | 0x005F6D58 |  | 1 |
| `EnemyDamageModuleImpl::set_disable_fire_damage_effect` | 0x005F6CF8 |  | 1 |
| `EnemyGroundLineTraceModuleImpl::can_turn_over` | 0x00708A5C |  | 1 |
| `EnemyGroundLineTraceModuleImpl::reset_speed` | 0x007083CC |  | 1 |
| `EnemyManager::create_request` | 0x003E3E14 |  | 1 |
| `EnemyManager::is_creatable_enemy_cost` | 0x0093EE30 |  | 1 |
| `EnemyTerritoryModuleImpl::EnemyTerritoryModuleImpl` | 0x0068CF90 |  | 1 |
| `FieldSmashAdjustDifficulty::get_enemy_hp_mul` | 0x00987ED8 |  | 1 |
| `FighterEntry::req_power_down_effect` | 0x003FEB08 |  | 1 |
| `FighterInformation::set_power_up_point` | 0x00562EFC |  | 1 |
| `FighterManager::get_fighter_pos` | 0x00949704 |  | 1 |
| `GroundModuleImpl::center_pos` | 0x009523D0 |  | 1 |
| `GroundModuleImpl::correct_pos` | 0x00952488 |  | 1 |
| `GroundModuleImpl::get_attach_movement_speed` | 0x004E3718 |  | 1 |
| `GroundModuleImpl::get_touch_attack_data` | 0x00952E34 |  | 1 |
| `GroundModuleImpl::get_touch_length` | 0x004E1550 |  | 1 |
| `GroundModuleImpl::get_touch_line` | 0x00952948 |  | 1 |
| `GroundModuleImpl::modify_circle` | 0x004E0DEC |  | 1 |
| `GroundModuleImpl::set_circle_follow_node` | 0x004E35B8 |  | 1 |
| `GroundModuleImpl::set_test_coll_stop` | 0x004E1BF0 |  | 1 |
| `GsbDrawModel::pre_render` | 0x007FA34C |  | 1 |
| `GsbDrawModel::process` | 0x00826BEC |  | 1 |
| `GsbDrawModel::set_shadow_position` | 0x007FAC10 |  | 1 |
| `GsbDrawModel::set_shadow_size` | 0x007FA8C0 |  | 1 |
| `GsbResourceManager::create_model` | 0x00829578 |  | 1 |
| `HitModuleImpl::set_offset` | 0x007B6EA4 |  | 1 |
| `Item::is_haved` | 0x009E6518 |  | 1 |
| `Item::warp` | 0x0074E174 / 0x0074E30C |  | 1 |
| `ItemManager::remove_item` | 0x003C94C8 |  | 1 |
| `ItemParamAccessor::get_item_kind` | 0x0052EC68 |  | 1 |
| `ItemResourceLoader::get_model_and_motion` | 0x00574714 |  | 1 |
| `Matrix34::set_rotate_x` | 0x0087CF64 |  | 1 |
| `MotionModuleImpl::deactivate` | 0x004FF38C |  | 1 |
| `Resource::~Resource` | 0x0016BC18 |  | 1 |
| `ShakeModuleImpl::stop` | 0x004C2318 |  | 1 |
| `SoundBGM::interrupt_bgm` | 0x007BA5B8 |  | 1 |
| `SoundEnemyOrne::SoundEnemyOrne` | 0x00491E40 |  | 1 |
| `SoundEnemyOrne::set_distance_max` | 0x00491B70 |  | 1 |
| `SoundEnemyOrne::set_distance_min` | 0x00491B7C |  | 1 |
| `SoundEnemyOrne::set_fighter_distance` | 0x00491B94 |  | 1 |
| `SoundEnemyOrne::set_position` | 0x00491B64 |  | 1 |
| `SoundEnemyOrne::set_volume_rate_min` | 0x00491B88 |  | 1 |
| `SoundEnemyOrne::start` | 0x00491DBC |  | 1 |
| `SoundEnemyOrne::stop` | 0x00491D6C |  | 1 |
| `SoundModuleImpl::play_se_pos` | 0x004C2988 |  | 1 |
| `SoundModuleImpl::stop_se` | 0x004C4D9C |  | 1 |
| `ValueControllerAim::update_rotation` | 0x0058E504 |  | 1 |
| `ValueControllerAimMinMax::ValueControllerAimMinMax` | 0x006AF22C |  | 1 |
| `void nw::h3d::SkeletonState::UpdateWorldMtxsImpl<false, true>` | 0x00A5E9AC / 0x00A5F2E8 |  | 1 |
<!-- /generated:framework -->

### Behaviour vtable slots (3DS; Wii U slot = 3DS - 1 for slots <= 27, equal from 29)

0 dtor, 4 update(AiInput*), 5 update_on_skip, 6 get_viewout_type, 7-9 attack-hit notifications (inferred), 11
notify_on_damage, 13 capture motion (inferred), 14 notify_on_capture_inner, 16 notify_on_common_thrown, 17
notify_on_capture_cut, 21 notify_on_tread (inferred), 28 notify_on_remove, 37 get_turn_type, 38 flip model with lr
(inferred), 39 is_down, 40 initialize, 41 start, 42 initialize_after, 43 update_hp, 44 damage_turn, 45
set_attack_data(state), 46 set_attack_power, 47 / 48 alternative attack state (inferred), 49 set_lr, 50 reverse_lr,
51 sync_lr_and_direction, 52 center_node, 53 clung_node, 54 / 55 state-change / per-frame hooks (inferred), 63
called by change_state_base with the new state (inferred), 64-67 states after damage / death state, 69 / 70 / 71
death / leave hooks (71 notify_on_death), 72 change_state, 73 change_state_interrupt, 74 / 75 the kinds' wrappers
around change_state_base / change_state_interrupt_base.

## All 80 kinds

Class: the hand-read class where there is one, else the automatic tags. Contact attacks: the P2 entries as
`state:power` (only armed per state when set_attack_data is "default"). ACMD hitboxes: motions with an attack.bin
script. Articles: the weapon classes the kind owns.

<!-- generated:kinds -->
| idx | kind | class | states | contact attacks (P2: state:power) | ACMD hitboxes | articles | set_attack_data | hand-read |
|---|---|---|---|---|---|---|---|---|
| 0x00 | [killer](killer.md) | stationary | 7 | 1:3, 2:3, 3:3, 4:8, 5:3, 5:3 | - | - | own 0x31a90 |  |
| 0x01 | [kuribo](kuribo.md) | walker | 11 | 5:1, 9:2 | - | - | default | yes |
| 0x02 | [tac](tac.md) | walker+acmd-hitboxes | 14 | 12:2 | Theft | - | default |  |
| 0x03 | [patapata](patapata.md) | walker+large | 24 | 6:4, 16:2, 20:17, 8:2 | - | - | default |  |
| 0x04 | [galthunder](galthunder.md) | no behaviour in enemy_fs.cro | 0 | 9:2 | 0x780d84e3 | - | - |  |
| 0x05 | [galice](galice.md) | no behaviour in enemy_fs.cro | 0 | 9:2 | 0x780d84e3 | - | - |  |
| 0x06 | [galfire](galfire.md) | no behaviour in enemy_fs.cro | 0 | 9:2 | 0x780d84e3 | - | - |  |
| 0x07 | [peahat](peahat.md) | flyer+shooter | 10 | 6:8 | - | shot | own 0x33c04 |  |
| 0x08 | [gordo](gordo.md) | stationary | 4 | 1:10, 2:10 | - | - | default | yes |
| 0x09 | [kihunter](kihunter.md) | flyer+shooter+acmd-hitboxes | 17 | 15:6 | BodyAttack2 | acidbullet | default |  |
| 0x0A | [monoeye](monoeye.md) | stationary+shooter | 9 | 7:2 | - | shot | default |  |
| 0x0B | [heiho](heiho.md) | walker | 17 | 9:1, 15:2 | - | - | default | yes |
| 0x0C | [mettaur](mettaur.md) | stationary+shooter | 10 | 8:2 | - | bullet | default |  |
| 0x0D | [shotzo](shotzo.md) | stationary+shooter | 8 | 8:0 | - | shot | default |  |
| 0x0E | [zima](zima.md) | crawler | 8 | 4:4, 6:6 | - | - | own 0x14dbc | yes |
| 0x0F | [tikibuzz](tikibuzz.md) | flier (dive bomber) | 13 | 5:2, 2:2 | - | - | default | yes |
| 0x10 | [ghost](ghost.md) | flyer+links | 9 | 0:0, 2:2 | - | - | own 0x66244 |  |
| 0x11 | [ghos](ghos.md) | flier (homing) | 6 | 4:3, 1:3 | - | - | default | yes |
| 0x12 | [plasmawisp](plasmawisp.md) | flyer+shooter | 11 | 2:3, 2:6, 2:9, 1:12 | - | hadoudan, laser, needle | own 0x8936c | yes |
| 0x13 | [waddledee](waddledee.md) | walker | 9 | 7:2 | - | parasol | default | yes |
| 0x14 | [critter](critter.md) | walker+acmd-hitboxes | 16 | 14:6 | BiteAttackHold, motion1(BiteAttack), BiteAttack, BiteAttackTurn, motion5(BiteAttackTurn), SpinAttack, motion18(SpinAttack) | - | default |  |
| 0x15 | [octorock](octorock.md) | walker+shooter | 15 | 13:3 | - | rock | default |  |
| 0x16 | [togemet](togemet.md) | crawler | 7 | 5:2, 5:4, 3:1, 3:4 | - | - | own 0x55c5c |  |
| 0x17 | [korokorobomb](korokorobomb.md) | walker | 17 | 13:12, 15:8, 14:12 | - | - | default |  |
| 0x18 | [mite](mite.md) | walker+shooter+large | 26 | 10:3, 8:2, 12:2, 15:1 | - | - | default |  |
| 0x19 | [waddledoo](waddledoo.md) | walker+shooter | 12 | 10:2 | - | beam | default | yes |
| 0x1A | [furiijio](furiijio.md) | flyer | 11 | 4:4, 7:4, 9:3 | - | - | default |  |
| 0x1B | [dafune](dafune.md) | flyer | 6 | 4:2 | - | flowermine | default |  |
| 0x1C | [brontoburt](brontoburt.md) | flyer+acmd-hitboxes | 14 | 4:1, 6:2 | Spin | - | own 0x82024 |  |
| 0x1D | [darios](darios.md) | stationary turret | 9 | 6:6 | - | - | default | yes |
| 0x1E | [dogars](dogars.md) | stationary+acmd-hitboxes | 9 | 7:2 | Smog, Float | - | default |  |
| 0x1F | [churine](churine.md) | walker | 10 | 8:1 | SleepPowder | sleeppowder | default | yes |
| 0x20 | [pooka](pooka.md) | walker | 13 | 6:2, 11:6 | - | - | default |  |
| 0x21 | [pokkuri](pokkuri.md) | flyer+shooter | 7 | 4:2 | - | largeshot, shot | default |  |
| 0x22 | [magnumkiller](magnumkiller.md) | stationary | 8 | 1:6, 1:6, 2:6, 2:6, 3:6, 3:6, 5:15, 6:18, 6:18, 8:20 | - | - | own 0x98568 |  |
| 0x23 | [dekakuribo](dekakuribo.md) | walker+acmd-hitboxes | 14 | 0:6 | RunL, WalkL, motion18(Damage), AngryL, Landing | - | none (empty) |  |
| 0x24 | [hammerbros](hammerbros.md) | walker+shooter | 10 | 8:6 | - | hammer | default |  |
| 0x25 | [keronpa](keronpa.md) | flyer+shooter | 12 | 2:2, 2:2, 2:2, 2:2, 9:12, 8:0, 10:30 | - | fire | own 0x4589c |  |
| 0x26 | [reo](reo.md) | flyer | 10 | 0:3, 0:3, 1:6 | - | - | own 0xc0c0 |  |
| 0x27 | [mahva](mahva.md) | flyer+links | 11 | 6:0, 1:6 | - | - | own 0x1fca0 |  |
| 0x28 | [shandera](shandera.md) | flyer+shooter | 13 | 2:6 | - | fireball, firetornado | default |  |
| 0x29 | [redead](redead.md) | walker+acmd-hitboxes | 13 | 11:6 | Attack1, Attack2, motion2(Attack2) | - | default |  |
| 0x2A | [starman](starman.md) | stationary+shooter | 13 | 11:7 | - | pkbeamgamma, pkbeamomega | default |  |
| 0x2B | [bokkuncannon](bokkuncannon.md) | walker+shooter+large | 20 | 18:8, 18:8 | - | beam, missile, shot | default |  |
| 0x2C | [kamek](kamek.md) | flyer+shooter | 14 | 12:6 | - | magicshot | default |  |
| 0x2D | [bubble](bubble.md) | flyer | 15 | 0:1, 0:1, 0:1, 0:1, 0:1, 0:1, 4:7, 4:9, 11:5, 13:6, 13:9, 13:9 | - | - | own 0x28ca4 |  |
| 0x2E | [eggrobo](eggrobo.md) | flyer+shooter | 12 | 7:1, 7:3, 10:8 | - | bullet | own 0x435fc |  |
| 0x2F | [zully](zully.md) | flyer+acmd-hitboxes | 8 | 6:6 | Claw | - | default |  |
| 0x30 | [stalfos](stalfos.md) | walker+melee | 25 | 23:10 | motion7(Attack1), Attack1, motion6(Attack2), motion9(Attack1), motion10(Attack2), AttackHold, motion8(Attack2), Fightingmove, Attack2, Jumpattack, motion5(Attack1), Fightingturn, motion31(Jumpattack) | - | default | yes |
| 0x31 | [bokkun](bokkun.md) | walker+acmd-hitboxes+large | 21 | 10:6, 10:4, 10:2, 13:6, 13:4, 13:2, 11:6, 11:4, 11:2, 19:10, 19:10 | SwingL, SwingAir, SwingS, motion21(Damage) | - | none (empty) |  |
| 0x32 | [bacula](bacula.md) | stationary | 4 | 1:4 | - | - | none (empty) |  |
| 0x33 | [deathpod](deathpod.md) | stationary+shooter | 10 | 3:12 | - | lastshot, shot | default |  |
| 0x34 | [flage](flage.md) | flyer+acmd-hitboxes | 10 | 8:7 | RushEnd, RushWait, RushAttack | - | default |  |
| 0x35 | [dosudosu](dosudosu.md) | walker+acmd-hitboxes+large | 21 | - | Walk | - | none (empty) |  |
| 0x36 | [bokkunmage](bokkunmage.md) | walker+shooter+acmd-hitboxes | 16 | 14:8, 14:8 | MagicL, MagicS | magic | default |  |
| 0x37 | [cucco](cucco.md) | flyer+spawner+links | 18 | 8:6 | - | - | default |  |
| 0x38 | [shinigami](shinigami.md) | walker+spawner+acmd-hitboxes | 13 | 13:18 | Turn, Feint, Scythe, Cry, Walk, motion17(DamageStart), ScytheHold, Landing, TurnCry, Surprise | - | none (empty) |  |
| 0x39 | [koshinigami](koshinigami.md) | stationary | 5 | 1:2 | - | - | default |  |
| 0x3A | [wanwanpile](wanwanpile.md) | flyer+spawner | 13 | 1:0 | - | - | default |  |
| 0x3B | [wanwan](wanwan.md) | flyer+links+acmd-hitboxes | 9 | 2:6, 6:14, 7:24 | motion2(Bite), 0x3ba08443, 0x66160195, 0x6a853177, Bite, 0x908a0c14, 0xc1afb920 | - | none (empty) |  |
| 0x3C | [deathskull](deathskull.md) | walker+acmd-hitboxes+large | 29 | 1:0, 3:0, 7:0, 8:0, 9:0, 23:0, 24:0, 25:0 | AttackTurn, AttackSpike, RushRun, Awake, AttackUpper | - | default |  |
| 0x3D | [chappy](chappy.md) | walker+acmd-hitboxes+large | 29 | 27:20, 29:0 | HeadAttack, BiteAttack, HipAttack, RunAttack, BiteAttackHold, HipAttackEnd | - | default |  |
| 0x3E | [metroid](metroid.md) | stationary+links | 10 | 8:6 | - | - | default |  |
| 0x3F | [totsukotsu](totsukotsu.md) | flyer+shooter+acmd-hitboxes | 9 | 0:12 | Fly | shot | default |  |
| 0x40 | [whitebear](whitebear.md) | walker | 12 | 10:8 | - | - | default | yes |
| 0x41 | [darknut](darknut.md) | walker+shooter+acmd-hitboxes+large | 25 | 23:10 | Armorwait, Armorattack2, Armorattack3hold2, Armorattack3, Nakedattack2, Armormove, Armorattack1, Armorattack3hold1, Armorattack1hold, Nakedattack1 | sword | default |  |
| 0x42 | [meganta](meganta.md) | walker+shooter+acmd-hitboxes+large | 23 | 21:15, 23:0 | motion10(Rolling), Rolling | homingbullet | default |  |
| 0x43 | [orne](orne.md) | flyer | 8 | 0:0 | - | - | none (empty) |  |
| 0x44 | [bonkers](bonkers.md) | walker+shooter+acmd-hitboxes+large | 24 | 10:15 | Turn, HammerSwingEnd, BombThrowHold, HammerSwingHold, HammerSHold, HammerL, HammerAir, HammerLHold, BombThrow, HammerS, HammerSwing | coconut | default |  |
| 0x45 | [devilcar](devilcar.md) | walker+acmd-hitboxes | 19 | 16:15, 0:3, 17:30 | motion7(SpinAttackHold), SpinAttackHold, JumpAttack | - | own 0x58d68 |  |
| 0x46 | [popperam](popperam.md) | walker+shooter | 12 | 10:2 | - | gravel | default |  |
| 0x47 | [propellerheiho](propellerheiho.md) | flyer | 9 | 3:2 | - | - | default |  |
| 0x48 | [cake](cake.md) | flyer | 7 | 5:2 | - | - | default |  |
| 0x49 | [mimicco](mimicco.md) | walker+acmd-hitboxes+large | 20 | 18:8 | RushAttackFinish, RushAttackDash, InterceptAttack, RushAttackJump, SpinAttackFinish, RushAttack, SpinAttack | - | default |  |
| 0x4A | [ohganemochi](ohganemochi.md) | walker | 15 | 13:12 | - | - | default |  |
| 0x4B | [shiroiobake](shiroiobake.md) | walker | 13 | 10:1 | - | - | default |  |
| 0x4C | [generator](generator.md) | stationary+spawner | 6 | 6:0 | - | - | default |  |
| 0x4D | [jugem](jugem.md) | flyer+spawner | 9 | 7:6 | - | - | default |  |
| 0x4E | [togezo](togezo.md) | walker | 14 | 0:1, 0:1, 4:5, 12:5 | - | - | own 0x37568 |  |
| 0x4F | [killercannon](killercannon.md) | stationary+spawner | 8 | 0:0 | - | - | none (empty) |  |
<!-- /generated:kinds -->

## Coverage and what remains unresolved

- **Automatic** (all 77 kinds with a behaviour): create / ctor / damage motion labels, vtable slots, state table,
  every state function and helper decoded (CFG + symbolic values), motion indices named, params resolved by the
  reader's own layout (all 80 vl files parse to the last token), attack lists with bones, articles and weapon
  specializers, ACMD.
- **Hand-read** (`hand_read.json`): the 5 walkers (kuribo, heiho, waddledee, waddledoo, churine) and step 2c's
  whitebear and gordo completely (with the code addresses read, "read");
  zima, plasmawisp, darios mostly (Darios's beam entry selection and Plasma Wisp's article / param mapping are
  partly inferred); stalfos only its attack sources. The other 69 kinds have the generated specs only.
- **galthunder, galice, galfire** (0x04-0x06): no behaviour, motion data set or article set in enemy_fs.cro (their
  models / motions / attack.bin / params exist, and their animations are all named `EnmGalFire*`). Where (or
  whether) the 3DS creates them is not found (not in enemy_fs.cro or enemy.cro; code.bin's factory imports the
  create functions by name and has none for them).
- **Energy parameters** (`[[[acc+0x30B0]+8]+0]+4` +0x08..+0x44) and the kinetic ids: which field is which speed /
  acceleration is not resolved (the energy's update is in code.bin without symbols). Walk vs run speeds of the
  same kinetic id (Kuribo 10) differ only by these fields and the motion rate.
- **Slot names** marked "?" are inferred from use (7-9, 13, 21, 38, 47, 48, 54, 55, 63).
- **gl entry** (`gl.fNN`): the 3DS `param/enemy/gl/enemy_param.bin` is not in the dump copy here; values not shown
  (the Wii U's own gl entries for the Smash Run kinds exist: docs/smash-run-port.md step 2a).
- **Weapon specializer slot names** (WeaponSpecializer vtable) are unnamed where overridden; their attack fields are
  named by analogy with InnerEnemyAttackParam (checked for waddledoo_beam: id f0, part f1, power f3, size f8).
- **Article entries**: `[weapon kind, n, data, 0]`; `n` is probably the maximum alive (inferred); weapon kind ids
  are the 3DS weapon kind table's (not mapped to the Wii U's 34 Smash Run weapon kinds).
- **Loops**: the analyser runs each block once (no loop iteration): values computed in loops show as `phi(...)`;
  guards ignore back edges.
- **dosudosu**: its attack group is the 45-word `InnerEnemyAttackParamOffset2` (elem 0xB4): field names not applied.
