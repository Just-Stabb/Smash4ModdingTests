#!/usr/bin/env python3
"""Repo-side generator of the tracer's data (needs the 3DS dump; the user never runs it).

  python3 tools/smashrun_trace/dev/build_data.py catalog --static-crs STATIC.crs --cro-dir CRO_DIR [--label base]
  python3 tools/smashrun_trace/dev/build_data.py map-cro --cro ENEMY_FS.cro --label base
  python3 tools/smashrun_trace/dev/build_data.py map-specs --label update

Writes into tools/smashrun_trace/srtrace/:
- catalog.json: the framework hooks, by MANGLED NAME (resolved at run time through the game's own loaded static.crs /
  CRO export tables, so the same catalogue works on the base game and the update): category, demangled signature
  (the argument decoder reads it), the module that exports it, whether it is hot (called many times a frame), and
  the addresses known per version (`expected`: base from the base static.crs, update from
  docs/smash-run-enemies/README.md's framework table) for cross-checking.
- maps/enemy_fs_<label>.json: per enemy kind, the hand-read functions as enemy_fs.cro FILE OFFSETS (state enter /
  update / exit, the vtable slots the traces need), the kind's create export (used at run time to check the map
  matches the loaded module before any breakpoint goes in), the behaviour fields the code reads (this.fNNN), and the
  param object's layout (dump-params). `map-specs` takes them from reference/smashrun_enemy_specs/*.json (the
  update's enemy_fs.cro, which the specs were read from); `map-cro` derives them from a CRO file with
  tools/s3ds_enemy_spec.py's reader (used for the base game's module, and by the tests).

No game data goes into these files: names, offsets and layouts only.
"""
import argparse
import hashlib
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(HERE, '..', 'srtrace')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(HERE, '..'))

import s3ds_unpack as U                                       # noqa: E402
from srtrace import abi                                        # noqa: E402

SPECS = os.path.join(ROOT, 'reference', 'smashrun_enemy_specs')
README = os.path.join(ROOT, 'docs', 'smash-run-enemies', 'README.md')

# (category, regex on the demangled name, hot?, wants return value?)
RULES = [
    # frame clock candidates (calibrate-clock picks; default the first that exists)
    ('clock', r'^app::StageManager::process_fix_position\(\)$', False, False),
    ('clock', r'^app::RushManager::process_fix_position\(\)$', False, False),
    ('clock', r'^app::GameOperatorRuleCheckObjFrameCounter::update_frame_counter\(bool\)$', False, False),
    # random numbers
    ('rng', r'^app::GameManager::(randi|randf|set_random_seed)\(', True, True),
    ('rng', r'^app::StageRandom::get\(', True, True),
    ('rng', r'^app::StagePrivateRandom::', True, True),
    ('rng', r'^app::ItemUtil::sync_random', True, True),
    ('rng', r'^app::Behavior::(random_range|random_choice|success_by_percent|success_by_fraction)\(', False, True),
    ('rng', r'^app::UiFsItemDatabase::get_random_rate\(', False, True),
    ('rng', r'^app::NetInterface::set_global_rand_seed\(', False, False),
    # enemy state framework / lifecycle
    ('state', r'^app::BehaviorImpl::(change_state_base|change_state_interrupt_base|change_common_state)\(', False, False),
    ('damage', r'^app::BehaviorImpl::(notify_on_damage|notify_on_death)\(', False, False),
    ('damage', r'^app::Behavior::(bullet|update_hp|set_weaken_type|set_shield_state|set_shield_data|disable_hit|'
               r'notify_on_remove|damage_turn)\(', False, False),
    ('motion', r'^app::Behavior::(change_motion_state|change_script_state|set_motion_no_restart)\(', False, False),
    ('kinetic', r'^app::EnemyKineticModuleImpl::change_kinetic\(', False, False),
    ('kinetic', r'^app::Behavior::(set_kinetic_jump|clear_speed_all|clear_speed_x|move)\(', False, False),
    ('facing', r'^app::Behavior::(set_lr|reverse_lr|sync_lr_and_direction)\(', False, False),
    # AI
    ('ai', r'^app::Behavior::(search_target|search_interval|get_nearest_target|check_turn_to_target|'
           r'get_lr_to_nearest_target|get_target_pos|check_wall|check_cliff|check_cliff_distance_lr|ray_check|'
           r'calc_angle|center_pos)\(', False, True),
    ('ai', r'^app::EnemyAiModuleImpl::(check_target|get_fighter_pos)\(', False, True),
    # leave / despawn / spawn
    ('leave', r'^app::Behavior::(init_common_leave|update_common_leave)\(', False, True),
    ('leave', r'^app::EnemyManager::(remove_enemy_by_id|set_already_dead_flag|cancel_request|add_kill_count|'
              r'notify_stage_command)\(', False, False),
    ('spawn', r'^app::EnemyManager::(create_request|reserve_request_no_setup|request_defeat_boss)\(', False, True),
    ('spawn', r'^app::EnemyGenerator::', False, True),
    ('spawn', r'^app::StageEnemyLayout::', False, True),
    ('spawn', r'^app::StageBaseFs::', False, True),
    # attacks / hitboxes
    ('attack', r'^app::Behavior::(create_attack_data|set_attack_power|set_attack_absolute_data|set_attack_data)\(',
     False, False),
    ('attack', r'^app::AttackModuleImpl::(set_attack|clear|clear_all|set_offset|set_offset2|set_power|set_size|'
               r'set_node|set_vector|set_reaction)\b', False, False),
    ('article', r'^app::Behavior::(generate_article\w*)\(', False, True),
    # effects (every effect request, any owner)
    ('effect', r'^app::Behavior::(request_effect|request_follow_effect|remove_effect|request_quake)\(', False, True),
    ('effect', r'^app::EffectModuleImpl::(req|req_follow|req_common|remove_common|set_rgb|set_color|set_alpha|'
               r'set_alpha_last|set_rate_last|set_scale|set_pos|set_rot|set_frame|set_visible|set_particle_scale|'
               r'detach_all|req_after_image_no_parent)\(', False, True),
    ('effect', r'^app::(Item::req_lost_effect|FighterEntry::req_power_down_effect)\(', False, False),
    ('effect', r'^app::DamageEffectorImpl::req_common_effect_param\(', False, False),
    # sounds
    ('sound', r'^app::Behavior::(play_se|stop_se)\(', False, True),
    ('sound', r'^app::SoundModuleImpl::(play_se|stop_se)\b', False, True),
    ('sound', r'^app::SoundSystem::play_se\(', False, True),
    ('sound', r'^app::StageSoundPlayer::', False, False),
    ('sound', r'^app::Gcon\w+::set_sound_data\(', False, False),
    # items / drops / power-ups / chests
    ('item', r'^app::ItemManager::(create_item|remove_item|lot_create_item|lot_create_item_with_arrival_effect|'
             r'ejection_item|out_pocket_item|request_lost_all|set_lot_delay_frame)\(', False, True),
    ('item', r'^app::ItemModuleImpl::(drop_item|pickup|have_item|throw)\w*\(', False, False),
    ('item', r'^app::FsItemAutoSet::', False, True),
    ('item', r'^app::Behavior::create_dead_item\(', False, True),
    ('item', r'^app::ItemParamAccessor::get_param\(', True, True),
    ('chest', r'^app::FieldSmashManager::', False, True),
    ('chest', r'^app::Gcon(Event|Multi)Treasure::', False, True),
    ('stat', r'^app::FighterInformation::(set_power_up_point|set_power_up_temp|power_up_level|add_power_up\w*)\(',
     False, True),
    ('stat', r'^app::FighterManager::set_power_up_streetpass\(', False, False),
    ('stat', r'^app::WeaponModuleAccessor::power_up_param\(', False, False),
    ('stat', r'^app::FieldSmashUtility::', False, True),
    ('stat', r'^app::FighterEntry::set_gold\(', False, False),
    ('stat', r'^app::GlobalParameterLib::(add_gold|sub_gold)\(', False, False),
    # doors / warps
    ('door', r'^app::Gcon(Event|Multi)Door::', False, True),
    ('door', r'^app::GconEventWarp::', False, True),
    ('door', r'^app::GconEventTreasure::set_miniroom_exit\(', False, False),
    # stage hazards (gimmicks): their attack shapes (as_), damage / hurt shapes (ds_), solid shapes (ss_)
    ('hazard', r'^app::GimmickControllerBase::(as_|ds_|ss_|activate|deactivate|on_activate|on_deactivate|'
               r'on_notify_on_damage|on_start_capture)', False, True),
    ('hazard', r'^app::Gcon(Attack|DamageBase|OneShotDeathFloorFs|MoveFloor|Pillar|MultiBlock|Capsule|Target|'
               r'Area|Cell|ShapeLite|SearchCapsule|Transformable|ModelRelatedMoveFloor\w*|EventBarrel|MultiBarrel|'
               r'EventSpring|MultiSpring)::', False, True),
    ('hazard', r'^app::GimmickAreaModuleImpl::', False, False),
    ('hazard', r'^app::StageDangerZone::', False, False),
    ('hazard', r'^app::GimmickEventPresenter::', False, False),
    # params
    ('param', r'^app::EnemyParamAccessor::', False, True),
    ('param', r'^app::ItemParamAccessor::(game_param|get_state_param_buffer_address)\(', False, True),
    # results
    ('result', r'^app::RecFieldSmash\w*::', False, False),
]
# called every frame (per object): only with --hot / --mode full (and the tracer's rate limit disables any hook
# that fires more than hot_limit times in hot_window seconds anyway)
HOT = [r'::(as|ds|ss)_transform_shape\(', r'::as_set_shape_velocity\(', r'update_sleep_status\(', r'::pre_update\(',
       r'EffectModuleImpl::(set_pos|set_rot|set_frame)\(',
       r'StageSoundPlayer::set_object_position\(', r'::(entry_chack|get_entry_num|get_entry_pos|get_entry_is_open)\(',
       r'Behavior::(center_pos|get_target_pos|calc_angle)\(', r'AttackModuleImpl::(set_offset|set_offset2|set_vector)\(',
       r'GimmickAreaModuleImpl::', r'ds_get_(damage|vector|owner_object_id|log_list)\(', r'as_get_(num_shapes|log_list)\(',
       r'ss_get_log_list\(', r'RecFieldSmash\w*::(is_|get_|has_)']
# data exports the dumps read (singletons): name -> what
SINGLETONS = ['EnemyParamAccessor', 'FieldSmashManager', 'EnemyManager', 'EnemyGenerator', 'ItemManager',
              'FighterManager', 'StageManager', 'ItemParamAccessor', 'BattleObjectManager', 'SoundSystem',
              'EquipmentManager', 'FighterParamAccessor', 'ItemSwitch']
# CRO exports to hook (module, demangled regex, category)
CRO_RULES = [
    ('main_field', r'^app::StageFieldSmash::StageFieldSmash\(\)$', 'stage'),
    ('main_field', r'^app::StageFsMiniroom::StageFsMiniroom\(\)$', 'stage'),
    ('enemy_fs', r'^app::EnemyParamAccessorInstanceFieldSmash::EnemyParamAccessorInstanceFieldSmash\(\)$', 'param'),
    ('menu', r'^app::FsViewResult1Scene::FsViewResult1Scene\(\)$', 'result'),
    ('menu', r'^app::FsViewFinalInfoScene::FsViewFinalInfoScene\(\)$', 'result'),
    ('menu', r'^app::FsViewItemSetScene::FsViewItemSetScene\(\)$', 'result'),
]
# behaviour vtable slots the tracer hooks (when the kind has its own function there)
# EnemyModuleAccessor module slots (update, docs/smash-run-enemies/README.md: acc + 0x3000 + X)
ACCESSOR = {'Ai': 0x3040, 'Attack': 0x3048, 'Damage': 0x3054, 'Effect': 0x3058, 'Ground': 0x305C, 'Kinetic': 0x3068,
            'BehaviorModule': 0x306C, 'Motion': 0x3070, 'Model': 0x3098, 'Posture': 0x309C, 'KineticEnergy': 0x30B0}
SLOTS = {4: 'update', 13: 'capture', 21: 'tread', 28: 'remove', 40: 'initialize', 41: 'start', 43: 'update_hp',
         44: 'damage_turn', 45: 'set_attack_data', 55: 'every_frame', 63: 'on_change_state', 67: 'death_state',
         69: 'slot69', 71: 'notify_on_death'}


def mangled_exports(path):
    x = open(path, 'rb').read()
    ex = U.exports(x)
    dem = U.demangle([n for _a, n in ex])
    return x, [(a, n, d) for (a, n), d in zip(ex, dem)]


def readme_addresses():
    """framework table of docs/smash-run-enemies/README.md: short name -> [update addresses]"""
    out = {}
    if not os.path.exists(README):
        return out
    for line in open(README):
        m = re.match(r'\| `([^`]+)` \| (0x[0-9A-F]+(?: / 0x[0-9A-F]+)*) \|', line)
        if m:
            out[m.group(1)] = [int(v, 16) for v in m.group(2).split(' / ')]
    return out


def cmd_catalog(a):
    crs, syms = mangled_exports(a.static_crs)
    upd = readme_addresses()
    hooks = []
    seen = set()
    for addr, mang, dem in syms:
        if not (0x100000 <= addr < 0xA83000):       # code only
            continue
        for cat, rx, hot, ret in RULES:
            if re.search(rx, dem):
                if mang in seen:
                    break
                seen.add(mang)
                name, args, _c = abi.split_args(dem)
                short = '::'.join(name.split('::')[1:])
                hot = hot or any(re.search(h, dem) for h in HOT)
                e = {'name': dem, 'mangled': mang, 'module': 'static', 'cat': cat, 'hot': hot, 'ret': ret,
                     'thumb': bool(addr & 1), 'expected': {a.label: '0x%08X' % addr},
                     'prio': [r[1] for r in RULES].index(rx)}
                # the update's address when the README lists this overload's name (single address: unambiguous)
                if short in upd and len(upd[short]) == 1:
                    e['expected']['update_readme'] = '0x%08X' % upd[short][0]
                elif short in upd:
                    e['expected']['update_readme_candidates'] = ['0x%08X' % v for v in upd[short]]
                hooks.append(e)
                break
    singles = {}
    for addr, mang, dem in syms:
        m = re.match(r'^lib::Singleton<app::(\w+)>::instance_$', dem)
        if m and m.group(1) in SINGLETONS:
            singles[m.group(1)] = {'mangled': mang, 'expected': {a.label: '0x%08X' % addr}}
        m = re.match(r'^app::InstanceList<app::GimmickControllerBase>::s_instance_$', dem)
        if m:
            singles['InstanceList<GimmickControllerBase>'] = {'mangled': mang, 'expected': {a.label: '0x%08X' % addr}}
    cro_hooks = []
    for mod, rx, cat in CRO_RULES:
        p = os.path.join(a.cro_dir, mod + '.cro')
        if not os.path.exists(p):
            continue
        _x, ex = mangled_exports(p)
        for off, mang, dem in ex:
            if re.search(rx, dem):
                cro_hooks.append({'name': dem, 'mangled': mang, 'module': mod, 'cat': cat, 'hot': False, 'ret': False,
                                  'thumb': False, 'expected': {a.label: 'cro+0x%X' % off}})
    counts = {}
    for h in hooks + cro_hooks:
        counts[h['cat']] = counts.get(h['cat'], 0) + 1
    out = {'about': 'Framework hooks by mangled name (tools/smashrun_trace/dev/build_data.py catalog). Resolved at run '
                    'time through the loaded static.crs / CRO export tables.',
           'source': {'static_crs_sha1': hashlib.sha1(crs).hexdigest(), 'label': a.label},
           'counts': counts, 'hooks': hooks + cro_hooks, 'singletons': singles}
    json.dump(out, open(os.path.join(OUT, 'catalog.json'), 'w'), indent=0, sort_keys=True)
    print('catalog: %d hooks (%s), %d singletons' % (len(hooks) + len(cro_hooks), counts, len(singles)))


def behaviour_fields(spec):
    s = json.dumps(spec.get('functions', {})) + json.dumps(spec.get('hand_read', {}))
    offs = set()
    for m in re.finditer(r'this[.+](?:f|0x)([0-9a-f]{2,3})\b', s):
        v = int(m.group(1), 16)
        if 0x1C <= v < 0x400:
            offs.add(v & ~3)
    return sorted(offs)


def param_layout(spec):
    p = spec.get('params') or {}
    out = []
    for m in p.get('members', []):
        if m.get('type') == 'array':
            out.append({'type': 'array', 'offset': m['offset'], 'index': m['index'], 'elem_size': m['elem_size'],
                        'offsets': m['offsets'], 'widths': m['widths'], 'names': m.get('names')})
        else:
            out.append({k: m[k] for k in ('type', 'offset') if k in m})
    return {'object_offset': p.get('object_offset'), 'members': out}


def cls_mangled(cls):
    return '_ZN3app%d%s6createERNS_19EnemyModuleAccessorEii' % (len(cls), cls)


def cmd_map_specs(a):
    kinds = {}
    for fn in sorted(os.listdir(SPECS)):
        if not fn.endswith('.json') or fn in ('hand_read.json', 'accuracy_audit.json'):
            continue
        sp = json.load(open(os.path.join(SPECS, fn)))
        if not sp.get('behavior_class') or not sp.get('create'):
            continue
        st = {}
        for s in sp.get('states', []):
            if s['id'] and (s['enter'] or s['update'] or s['exit']):
                st[str(s['id'])] = {k: (int(s[k], 16) if s[k] else None) for k in ('enter', 'update', 'exit')}
        slots = {}
        for k, v in sp.get('vtable_slots', {}).items():
            if int(k) in SLOTS and v.get('fn'):
                slots[SLOTS[int(k)]] = int(v['fn'], 16)
            elif int(k) in SLOTS and v.get('impl'):
                slots[SLOTS[int(k)]] = 'import:' + v['impl']
            if int(k) == 67 and 'returns' in v:
                slots['death_state_id'] = v['returns']
        kinds[sp['kind']] = {'index': int(sp['kind_index'], 16), 'class': sp['behavior_class'],
                             'create': int(sp['create'], 16), 'create_mangled': cls_mangled(sp['behavior_class']),
                             'vtable': int(sp['vtable'], 16) if sp.get('vtable') else None,
                             'state_table': int(sp['state_table'], 16) if sp.get('state_table') else None,
                             'object_size': int(sp['object_size'], 16) if sp.get('object_size') else None,
                             'states': st, 'slots': slots, 'fields': behaviour_fields(sp),
                             'params': param_layout(sp), 'hand_read': 'hand_read' in sp}
    out = {'module': 'enemy_fs', 'label': a.label, 'source': 'reference/smashrun_enemy_specs (the update\'s '
           'enemy_fs.cro)', 'file_segments': None, 'kinds': kinds, 'accessor': ACCESSOR,
           'accessor_source': 'docs/smash-run-enemies/README.md (update: acc+0x3000+X)'}
    if a.segments:
        out['file_segments'] = json.loads(a.segments)
    p = os.path.join(OUT, 'maps', 'enemy_fs_%s.json' % a.label)
    json.dump(out, open(p, 'w'), indent=0, sort_keys=True)
    print('map %s: %d kinds' % (p, len(kinds)))


def cmd_map_cro(a):
    import s3ds_enemy_spec as S
    c = S.Cro(a.cro)
    vts = S.find_vtables(c)
    kinds = {}
    for kind in S.KINDS:
        cls = create = None
        for nm, ad in c.exp_by_name.items():
            m = re.match(r'app::(Behavior\w+)::create\(app::EnemyModuleAccessor&, int, int\)$', nm)
            if m and m.group(1).lower() == 'behavior' + kind:
                cls, create = m.group(1), ad
        if not cls:
            continue
        vt = vts.get(cls)
        slots, table = {}, None
        if vt:
            for k in range(80):
                w = c.word(vt + 4 * k)
                if w[0] == 'ptr' and c.code_lo <= w[1] < c.code_hi:
                    if k in SLOTS:
                        slots[SLOTS[k]] = w[1]
                    if k == 72:
                        f = w[1]
                        for j in range(12):
                            ins = struct.unpack_from('<I', c.x, f + 4 * j)[0]
                            if ins & 0x0F7F0000 == 0x051F0000:          # ldr rX, [pc, #imm]
                                imm = ins & 0xFFF
                                lit = f + 4 * j + 8 + (imm if ins & 0x00800000 else -imm)
                                ww = c.word(lit)
                                if ww[0] == 'ptr' and not (c.code_lo <= ww[1] < c.code_hi):
                                    table = ww[1]
                                    break
                elif w[0] == 'imp' and k in SLOTS:
                    slots[SLOTS[k]] = 'import:' + S.short_name(w[1])
                elif w[0] == 'c' and k > 2 and w[1] != 0:
                    break
        st = {}
        if table:
            for i in range(1, 64):
                e = []
                ok = True
                for j in range(3):
                    ww = c.word(table + 24 * i + 8 * j)
                    if ww[0] == 'ptr' and c.code_lo <= ww[1] < c.code_hi:
                        e.append(ww[1])
                    elif ww == ('c', 0):
                        e.append(None)
                    else:
                        ok = False
                if not ok:
                    break
                if any(e):
                    st[str(i)] = dict(zip(('enter', 'update', 'exit'), e))
        kinds[kind] = {'index': S.KINDS.index(kind), 'class': cls, 'create': create, 'create_mangled': cls_mangled(cls),
                       'vtable': vt, 'state_table': table, 'states': st, 'slots': slots, 'fields': [],
                       'params': None, 'hand_read': False}
    # fields / params from the update's specs (the Behavior layout is shared)
    upd = os.path.join(OUT, 'maps', 'enemy_fs_update.json')
    if os.path.exists(upd):
        u = json.load(open(upd))['kinds']
        for k, v in kinds.items():
            if k in u:
                v['fields'] = u[k]['fields']
                v['params'] = u[k]['params']
    out = {'module': 'enemy_fs', 'label': a.label, 'source': os.path.basename(a.cro) + ' sha1 ' +
           hashlib.sha1(c.x).hexdigest(), 'file_segments': [list(s) for s in c.segs], 'kinds': kinds,
           'accessor': {k: v - a.accessor_shift for k, v in ACCESSOR.items()},
           'accessor_source': 'update - 0x%X: the base enemy_fs.cro reads Posture at +0x303C, the movement energy at '
                              '+0x3050, Kinetic at +0x3008 and Ground at +0x2FFC where the update reads +0x309C / '
                              '+0x30B0 / +0x3068 / +0x305C (the Goomba notice-hop enter, base 0x33B98); the other '
                              'modules inferred by the same shift' % a.accessor_shift}
    p = os.path.join(OUT, 'maps', 'enemy_fs_%s.json' % a.label)
    json.dump(out, open(p, 'w'), indent=0, sort_keys=True)
    print('map %s: %d kinds, %d with a state table' % (p, len(kinds), sum(1 for v in kinds.values() if v['states'])))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd')
    p = sub.add_parser('catalog')
    p.add_argument('--static-crs', required=True)
    p.add_argument('--cro-dir', required=True)
    p.add_argument('--label', default='base')
    p = sub.add_parser('map-specs')
    p.add_argument('--label', default='update')
    p.add_argument('--segments', help='JSON [[off, size, type], ...] of the update enemy_fs.cro (default: unknown; '
                                      'text offsets need none)')
    p = sub.add_parser('map-cro')
    p.add_argument('--cro', required=True)
    p.add_argument('--label', default='base')
    p.add_argument('--accessor-shift', type=lambda v: int(v, 0), default=0x60)
    a = ap.parse_args()
    {'catalog': cmd_catalog, 'map-specs': cmd_map_specs, 'map-cro': cmd_map_cro}[a.cmd](a)


if __name__ == '__main__':
    main()
