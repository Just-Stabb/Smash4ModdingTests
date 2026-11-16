#!/usr/bin/env python3
"""The Ultimate port pipeline in one place (docs/ultimate-port-guide.md): what a port needs, in order,
with every rule the ports so far learned the hard way applied by default.

  python3 tools/ultimate_port.py status NAME          sources found, config, the base's known traps
  python3 tools/ultimate_port.py init NAME --base BASE --kind 0x47 --ui-name "Name" [--trait shooter]
                                                       fighters/NAME/port.json, filled from Ultimate's files
  python3 tools/ultimate_port.py effects NAME          the effects his scripts use: his own, and Ultimate's
                                                       common ones mapped to ef_common.eff's emitter sets
  python3 tools/ultimate_port.py stats NAME FIGHTER_PARAM_BIN OUT_BIN
  python3 tools/ultimate_port.py plan NAME [--out DIR] every step's command, in order, with its inputs
  python3 tools/ultimate_port.py run NAME STEP [STEP ...] [--out DIR]   run steps of the plan
  python3 tools/ultimate_port.py variants NAME [--out DIR]               (the plan's 'variants' step)
  python3 tools/ultimate_port.py check NAME PKG [PKG ...]               tools/port_check.py

Sources (Ultimate's files, the vanilla game): port_sources.json (tools/port_sources.py). Per fighter:
fighters/NAME/port.json (init writes it; edit it for what can't be read off the files). The base's
known behaviour: reference/port_bases.json.

Rules built in (each one a bug a port shipped with):
- the body scripts start from the universal-mechanics game.bin (roll-off, reverse tilts...), never
  vanilla's (Hero fix 57 / Bowser jabs v3 lost the roll speed);
- extra joints go to joint table 1 (--joints), never table 0 (Sephiroth test 20, Squirtle v5);
- the model folders ship model.nud with model.nut (Hero fix 17) and the motions step's
  material_anime pacs, not the model step's (Hero fix 74);
- every fighter and costume gets texture ids of its own (tools/fighter_texture_ids.py, registered by init in
  reference/port_bases.json "_texture_ids"): the game keys loaded textures by id, and the ports' shared 0x40EB0000
  drew a P2 Squirtle with a P1 Steve's textures (fighters_texid_fix_v1);
- Ultimate's common effects (sys_*) are converted from ef_common.eff into the port's bank (Squirtle:
  Smash 4's stood in for all of them; Hero's attack line, fix 63-70) and turned effects on bones get
  variants (effect_variants.py: Sephiroth test 49, Squirtle's dash attack);
- stats from Ultimate's fighter_param.prc by name (tools/ultimate_stats.py), never left as the base's;
- stock icons from Ultimate's stock icon art (--stock-icon), not the select render shrunk (Squirtle);
- the translator maps Ultimate-only angles (367 / 368 -> 366) and catch-only throw hitboxes
  (NoGrabRelease) itself (tools/ultimate_acmd.py);
- port_check.py runs on the finished package: a port isn't sent with an ERROR.
"""
import argparse
import glob
import json
import os
import re
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import port_sources  # noqa: E402

TRAITS = ('rush', 'shooter', 'strike', 'juggernaut', 'normal', 'technical', 'barrage')
# Ultimate's sys_* effect -> ef_common.eff set: P_Cmn + the name's words joined (sys_dash_smoke ->
# P_CmnDashSmoke), with these spellings; 46 of the 57 Squirtle / Hero use, the rest by these
COMMON_WORDS = {'atk': 'attack', 'erace': 'erase', 'h': 'horizontal', 'v': 'vertical', 'mball': 'monsterball'}


def cfg_path(name):
    return os.path.join(ROOT, 'fighters', name, 'port.json')


def load_cfg(name):
    p = cfg_path(name)
    if not os.path.exists(p):
        sys.exit('%s: no fighters/%s/port.json (ultimate_port.py init)' % (name, name))
    return json.load(open(p))


def bases():
    return json.load(open(os.path.join(ROOT, 'reference/port_bases.json')))


def dump_scripts(src, ult):
    d = src.dump(ult)
    return sorted(glob.glob(os.path.join(d, '*', '*.txt'))) if d else []


def used_effects(src, ult):
    """(the fighter's own effect names, Ultimate's common sys_* names) its scripts play"""
    own, common = set(), set()
    for p in dump_scripts(src, ult):
        for n in re.findall(r'Hash40::new\("([a-z0-9_]+)"\)', open(p, errors='replace').read()):
            if n.startswith(ult + '_'):
                own.add(n)
            elif n.startswith('sys_'):
                common.add(n)
    return sorted(own), sorted(common)


def common_sets(names, eff_path):
    """{sys name: ef_common.eff emitter set} by Ultimate's naming (P_Cmn + the words); unmatched -> None"""
    import vfxb
    sets = {s.lower(): s for s in vfxb.Eff(eff_path).sets}
    out = {}
    for n in names:
        raw = n[4:].split('_')
        tries = ['p_cmn' + ''.join(COMMON_WORDS.get(w, w) for w in raw), 'p_cmn' + ''.join(raw)]
        out[n] = next((sets[t] for t in tries if t in sets), None)
    return out


def standard_bones():
    return {'top', 'rot', 'hip', 'waist', 'bust', 'neck', 'head', 'clavicler', 'claviclel', 'shoulderr',
            'shoulderl', 'armr', 'arml', 'handr', 'handl', 'legr', 'legl', 'kneer', 'kneel', 'footr', 'footl',
            'toer', 'toel', 'haver', 'havel', 'throw', 'trans'}


def attack_bones(src, ult):
    """bones Ultimate's hitboxes use that aren't the 26 standard ones (joints to add: --joints)"""
    out = {}
    for p in dump_scripts(src, ult):
        if '/%s/' % ult not in p.replace('\\', '/'):
            continue
        for b in re.findall(r'macros::(?:ATTACK|CATCH)\(agent, [^;]*?Hash40::new\("(\w+)"\)', open(p, errors='replace').read()):
            if b.lower() not in standard_bones():
                out[b] = out.get(b, 0) + 1
    return out


# ------------------------------------------------------------------ commands
def cmd_status(a):
    src = port_sources.load()
    cfg = json.load(open(cfg_path(a.name))) if os.path.exists(cfg_path(a.name)) else None
    ult = (cfg or {}).get('ult', a.name)
    print('%s (Ultimate %s): %s' % (a.name, ult, 'fighters/%s/port.json' % a.name if cfg else 'no port.json yet'))
    for k, v in src.report(ult):
        print('  %-18s %s' % (k, v or '-- not found (port_sources.json)'))
    base = (cfg or {}).get('base')
    if base and base in bases():
        print('\n%s as a base (reference/port_bases.json):' % base)
        for t in bases()[base].get('traps', []):
            print('  - ' + t)


def cmd_init(a):
    src = port_sources.load()
    ult = a.ult or a.name
    if os.path.exists(cfg_path(a.name)) and not a.force:
        sys.exit('fighters/%s/port.json exists (--force to rewrite)' % a.name)
    own, common = used_effects(src, ult)
    joints = attack_bones(src, ult)
    skel = src.ult_file(ult, 'model/body/c00/model.nusktb')
    if skel:                    # the dump writes bone names in lower case: the skeleton's spelling
        import ssbh_data_py
        real = {b.name.lower(): b.name for b in ssbh_data_py.skel_data.read_skel(skel).bones}
        joints = {real.get(k.lower(), k): v for k, v in joints.items()}
    costumes = sorted(os.path.basename(p) for p in glob.glob(os.path.join(src.ult_dir(ult) or '/nonexistent', 'model/body/c0*')))
    costumes = costumes or ['c%02d' % i for i in range(8)]
    trait = (a.trait or '').lower()
    if trait and trait not in TRAITS:
        sys.exit('trait: one of %s' % ', '.join(TRAITS))
    cfg = {
        '_comment': 'tools/ultimate_port.py; fields: docs/ultimate-port-guide.md "port.json"',
        'ult': ult, 'kind': a.kind, 'base': a.base, 'ui_name': a.ui_name, 'trait': trait or None,
        'rolloff': {'speed': 2.2, 'air_mult': 1.0},
        'costumes': costumes,
        'model': {'max_bones': 136, 'joints': sorted(joints), 'have': None},
        'motions': {'add': []},
        'effects': {'own': own, 'common': common, 'tint_for': {}, 'hdr_white_for': [], 'bone_path': {}},
        'stats': {'jump_scale': [1.0, 1.0]},
        'portraits': {'cross': None, 'stock_icon': True},
        'specials': {'msc': '%s.c' % a.name, 'acmd': 'specials_acmd.json', 'build': None},
    }
    os.makedirs(os.path.dirname(cfg_path(a.name)), exist_ok=True)
    json.dump(cfg, open(cfg_path(a.name), 'w'), indent=1)
    import fighter_texture_ids        # its texture-id block (reference/port_bases.json "_texture_ids")
    tx = fighter_texture_ids.register(a.name, kind=int(a.kind, 0))
    print('texture ids: %s - 0x%08X (tools/fighter_texture_ids.py scheme %s)' % (
        tx['base'], int(tx['base'], 0) + 0xFFFF, a.name))
    print('wrote fighters/%s/port.json: %d costumes, joints to add %s, %d own effects, %d common' % (
        a.name, len(costumes), joints or 'none', len(own), len(common)))
    if not trait:
        print('NOTE: no trait yet: ask the user (CLAUDE.md), then add it to docs/character-traits.md and kirby_copy_trait()')


def cmd_effects(a):
    src = port_sources.load()
    ult = port_sources.ult_name(a.name)
    own, common = used_effects(src, ult)
    eff = src.find('ult_effects', 'system/common/ef_common.eff') or src.get('ef_common')
    print('%d own effects: %s' % (len(own), ' '.join(own)))
    if eff:
        m = common_sets(common, eff)
        print('\n%d common effects -> ef_common.eff sets (vfxb_to_ptcl.py --extra-eff ef_common.eff NAME=SET ...):' % len(common))
        for n, s in sorted(m.items()):
            print('  %-28s %s' % (n, s or "-- no set: stays Smash 4's (reference/ultimate_sys_effects.json)"))
    else:
        print('\ncommon: %s (no ef_common.eff in port_sources.json "ef_common")' % ' '.join(common))


def cmd_stats(a):
    src = port_sources.load()
    cfg = load_cfg(a.name)
    js = ','.join(str(x) for x in cfg.get('stats', {}).get('jump_scale', [1.0, 1.0]))
    prc = src.find('ult_common', 'param/fighter_param.prc')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, 'ultimate_stats.py'), prc, src['labels'], cfg['ult'],
                        a.fighter_param, a.out, cfg['kind'], '--jump-scale', js])
    sys.exit(r.returncode)


# common moves whose slot the base may not have (ultimate_acmd.SLOT_MOVES): the Smash 4 animation name's tail
SLOT_MOVE_ANIMS = {'Attack100Start': 'c00attack100start', 'Attack100': 'c00attack100', 'Attack100End': 'c00attack100end',
                   'AttackS4Hi': 'c03attacks4hi', 'AttackS4Lw': 'c03attacks4lw'}


def slot_moves_for(add, base_dir):
    """the SLOT_MOVES the port has animations for: given by port.json motions.add (Byleth on ZSS: the rapid jab, the
    angled forward smashes; their slots in extra_kinds.json "motions") or the base's own main.pac"""
    have = {a.lower() for a in add}
    pac = os.path.join(base_dir, 'motion/body/main.pac')
    if os.path.exists(pac):
        import omo
        for n, _d in omo.pac_read(pac):
            i = n.find('Main')
            if i >= 0:
                have.add(n[i + 4:-4].lower())
    return [k for k, v in SLOT_MOVE_ANIMS.items() if v in have]


def plan(name, out):
    """[(step, description, argv)] with paths resolved; '?' where an input is missing"""
    src = port_sources.load()
    cfg = load_cfg(name)
    ult, base, kind = cfg['ult'], cfg['base'], cfg['kind']
    py = 'python3'
    t = lambda tool: os.path.join('tools', tool)          # noqa: E731
    U = src.ult_dir(ult) or '?ULT/' + ult
    dump = src.dump(ult) or '?DUMP/lua2cpp_' + ult
    base_dir = src.get('base_fighter_dirs', {}).get(base) or src.find('base_fighters', base) or '?BASE/' + base
    work = os.path.join(out, 'work')
    pkg = os.path.join(out, name)
    fighter = os.path.join(pkg, 'fighter', name)
    body = os.path.join(work, 'body')                 # the universal-mechanics body scripts
    m = cfg.get('model', {})
    joints = ['--joints', ','.join(m['joints'])] if m.get('joints') else []
    have = ['--have', m['have']] if m.get('have') else []
    mb = ['--max-bones', str(m.get('max_bones', 136))]
    cache = ['--anim-cache', os.path.join(work, 'anim_cache.json')]
    steps = [('body', 'the base\'s body scripts with the universal mechanics (roll-off): build/universal_mechanics_all.zip',
              [py, t('ultimate_port.py'), 'unpack-body', name, body])]
    import fighter_texture_ids
    for c in cfg.get('costumes', ['c00']):
        steps.append(('model-' + c, 'model %s (table-1 joints, NUD + NUT together, its own texture ids)' % c,
                      [py, t('ultimate_fighter.py'), 'model', os.path.join(U, 'model/body', c),
                       os.path.join(base_dir, 'model/body', c), os.path.join(fighter, 'model/body', c),
                       '--tex-id', '0x%08X' % fighter_texture_ids.body_id(name, c),
                       '--empty', src.get('empty_dir', '?EMPTY'), *mb, *joints, *have,
                       '--motions', os.path.join(U, 'motion/body/c00'), *cache]))
    add = cfg.get('motions', {}).get('add', [])
    steps.append(('motions', 'motions + the material_anime pacs (these ship, not the model step\'s)',
                  [py, t('ultimate_fighter.py'), 'motions', os.path.join(U, 'motion/body/c00'), os.path.join(U, 'model/body/c00'),
                   base_dir, fighter, *mb, *joints, *have, *cache] + (['--add', ','.join(add)] if add else [])
                  # port.json motions.extra_vis: visibility the motions don't carry (held article models: Steve's tools,
                  # Byleth's weapons), a JSON in the fighter's folder
                  + (['--extra-vis', os.path.join('fighters', name, cfg['motions']['extra_vis'])]
                     if cfg.get('motions', {}).get('extra_vis') else [])))
    # the low models (model/body/l00-l07): the off-screen magnifier and 8-player Smash draw them, not cXX; a port
    # without them was invisible in the magnifier (Squirtle v6, user). Ultimate's own low model where the costume has a
    # lod.xmb (its lowest level of detail: Byleth's body_low / hair_low / coat / skirt), else copies of cXX
    # (docs/params/fighter_files.md: Hero's are); after the motions step, which adds the face packs to the model folders
    steps.append(('low-models', 'the low models (l00-l07, magnifier / 8-player Smash): Ultimate\'s LOD (lod.xmb), else copies',
                  [py, t('ultimate_port.py'), 'low-models', name, '--out', out]))
    # Ultimate's victory cameras (camera/fighter/<ult>/c00/j02win1-3): Smash 4 camera motions in Corrin's final-camera
    # form (tools/ultimate_camera.py: fighter/NAME/camera/result/winN); port_check R1. Smash 4's result screen frames
    # the winner from param/ui/result_param.bin and plays no camera motion yet (an executable hook to come)
    steps.append(('camera', 'the win cameras (Ultimate\'s j02win1-3 -> camera/result/winN camera_motion.omo / .vbn)',
                  [py, t('ultimate_camera.py'), 'convert', name, '--out', out]))
    eff = src.eff(ult) or '?EFF/ef_%s.eff' % ult
    e = cfg.get('effects', {})
    ids = os.path.join(ROOT, 'fighters', name, '%s_effects.json' % name)
    fx = os.path.join(work, 'fx')
    base_fx = os.path.join(base_dir, 'effect', base)          # the base's bank: its folder, else vanilla's
    if not os.path.isdir(base_fx):
        base_fx = os.path.join(src.get('vanilla', '?VANILLA'), 'fighter', base, 'effect', base)
    common_eff = src.find('ult_effects', 'system/common/ef_common.eff') or src.get('ef_common')
    extra = []
    if common_eff and e.get('common'):
        pairs = ['%s=%s' % (k, v) for k, v in sorted(common_sets(e['common'], common_eff).items()) if v]
        extra = ['--extra-eff', common_eff] + pairs if pairs else []
    # the colours Ultimate puts on effects at run time (tools/ultimate_tints.py): the fighter's common_effect_0 on
    # its attack lines / arcs and the script colours every call of an effect sets; port.json tint_for overrides
    import ultimate_tints
    tint = ultimate_tints.tint_args(ult, os.path.join(dump, ult), e.get('tint_for'))
    hdr = ['--hdr-white-for', ','.join(e['hdr_white_for'])] if e.get('hdr_white_for') else []
    steps.append(('effects', 'his effect bank: his own sets, Ultimate\'s common ones (variants: after the scripts)',
                  [py, t('vfxb_to_ptcl.py'), eff, base_fx, fx, kind, ids, *e.get('own', []),
                   '--prefix', 'Ptc' + name.capitalize(), '--templates',
                   *(sorted(glob.glob(src.get('vanilla', '?') + '/fighter/*/effect/*/*.ptcl')) or ['?TEMPLATES']),
                   '--variants-last', *extra, *tint, *hdr]))
    snd = [r for r in src.roots('ult_sound') if os.path.exists(os.path.join(r, 'bank/fighter/se_%s.nus3audio' % ult))]
    steps.append(('sound', 'his se / voice banks, sequences, label table',
                  [py, t('ultimate_sound.py'), snd[0] if snd else '?SOUND',
                   # the base's banks renamed for him: add_fighter.py's folder (port_sources kind_folders)
                   src.get('kind_folders', {}).get(name) or '?KIND_FOLDER/fighter/' + name, src.get('soundlabeltable', '?LABELS'),
                   os.path.join(work, 'sound'), '--name', name.capitalize(), '--ult-name', ult, '--dump', dump]))
    snd_ids = os.path.join(work, 'sound', 'sound_ids.json')
    slot_moves = slot_moves_for(add, base_dir)
    steps.append(('scripts', 'Ultimate\'s scripts into the base\'s slots (game / effect / sound / expression, vl frames)',
                  [py, t('ultimate_acmd.py'), os.path.join(dump, ult), os.path.join(body, 'game.bin'),
                   os.path.join(fighter, 'script/animcmd/body/game.bin'), os.path.join(fighter, 'model/body/c00'),
                   '--others', body, os.path.join(fighter, 'script/animcmd/body'),
                   '--motion-list', os.path.join(U, 'motion/body/c00/motion_list.bin'),
                   '--mtable', os.path.join(body, 'motion.mtable'), os.path.join(fighter, 'script/animcmd/body/motion.mtable'),
                   '--vl', os.path.join(body, 'vl.bin'), os.path.join(pkg, 'param/fighter/fighter_param_vl_%s.bin' % name),
                   '--vl-kind', bases().get(base, {}).get('vl_kind', base),
                   '--effects', 'reference/ultimate_sys_effects.json,' + ids, os.path.join(U, 'model/body/c00/model.nusktb')]
                  + (['--translate', os.path.join('fighters', name, e2)] if (e2 := cfg.get('specials', {}).get('acmd'))
                     and os.path.exists(os.path.join(ROOT, 'fighters', name, e2)) else [])
                  + (['--slot-moves', ','.join(slot_moves)] if slot_moves else [])
                  + ['--sound-ids', snd_ids, '--expressions', '--vec-targets', os.path.join(work, 'vec_targets.json')]))
    # Ultimate's "carry the hit fighter to a point" (angle 368 + set_vec_target_pos): no Smash 4 hitbox field, so an MSC
    # pull per move (tools/vec_target.py, Sephiroth's up tilt's method): paste it into fighters/NAME/NAME.c and call
    # it from the per-frame hook (port_check S10); port.json vec_target: status {script: kind} for specials,
    # hand_made {script: how}, mask_var (a free VAR_n)
    vt = cfg.get('vec_target', {})
    steps.append(('vec-target', 'the MSC pull for set_vec_target_pos moves (paste into %s.c, call per frame)' % name,
                  [py, t('vec_target.py'), 'msc', name, os.path.join(dump, ult), '--out', os.path.join(work, name + '_vec_target.c'),
                   '--mask-var', vt.get('mask_var', '0x0F00030E')]
                  + sum((['--status', '%s=%s' % kv] for kv in sorted(vt.get('status', {}).items())), [])
                  + sum((['--skip', k] for k in sorted(vt.get('hand_made', {}))), [])))
    # the fighter's own build (MSC, articles, special slots): port.json specials.build + build_args, with
    # {dump} {ult} {body} {vl} {model} {base} {pkg} {work} {fx} {sound}
    sp = cfg.get('specials', {})
    if sp.get('build'):
        fill = dict(dump=dump, ult=U, body=body, vl=os.path.join(body, 'vl.bin'), model=os.path.join(fighter, 'model/body/c00'),
                    base=base_dir, pkg=pkg, work=work, fx=fx, sound=os.path.join(work, 'sound'))
        steps.append(('specials', 'his specials (MSC, articles): the fighter\'s own build script',
                      [py, sp['build']] + ([x.format(**fill) for x in sp['build_args']] if sp.get('build_args') else ['...'])))
    # the turned effects are only known once the scripts are translated: scan them, rebuild the bank with
    # the variants, point the scripts at them (the effects step alone has none: Squirtle's dash attack)
    steps.append(('variants', 'turned effects on bones: scan the translated effect.bin, rebuild the bank with variants, apply',
                  [py, t('ultimate_port.py'), 'variants', name, '--out', out]))
    steps.append(('shapes', 'hurtboxes, ECB, ledge box from Ultimate\'s vl.prc',
                  [py, t('ultimate_vl_shapes.py'), os.path.join(pkg, 'param/fighter/fighter_param_vl_%s.bin' % name),
                   os.path.join(pkg, 'param/fighter/fighter_param_vl_%s.bin' % name), os.path.join(U, 'param/vl.prc'),
                   os.path.join(fighter, 'model/body/c00')]))
    steps.append(('stats', 'stats from Ultimate\'s fighter_param.prc',
                  [py, t('ultimate_port.py'), 'stats', name, src.get('fighter_param', '?CURRENT/fighter_param.bin'),
                   os.path.join(pkg, 'param/fighter/fighter_param.bin')]))
    p = cfg.get('portraits', {})
    steps.append(('portraits', 'portraits, stock icons (Ultimate\'s), name plates',
                  [py, t('ultimate_portraits.py'), '--ult-ui', (src.roots('ult_ui') or ['?UI'])[0], '--s4-chr',
                   src.get('s4_chr', '?S4_CHR'), '--templates',
                   # add_fighter.py's portraits for him (the base's art, his ids): port_sources templates.NAME
                   (src.get('templates') or {}).get(name, '?TEMPLATES'), '--ult', ult,
                   '--ult-base', bases().get(base, {}).get('ult', base), '--ui-name', cfg['ui_name'],
                   '--s4-base', base.capitalize(), '--out', pkg] + (['--stock-icon'] if p.get('stock_icon', True) else [])
                  + (['--cross', p['cross']] if p.get('cross') else [])
                  + [x for k, v in sorted((p.get('set_fits') or {}).items()) for x in ('--set-fit', '%s=%s' % (k, v))]
                  + (['--sets', ','.join(p['sets'])] if p.get('sets') else [])))
    steps.append(('check', 'the package against every bug class so far', [py, t('port_check.py'), name, pkg]))
    return steps


def cmd_plan(a):
    cfg = load_cfg(a.name)
    print('# %s (Ultimate %s) on %s, kind %s: %s' % (a.name, cfg['ult'], cfg['base'], cfg['kind'], a.out))
    for t in bases().get(cfg['base'], {}).get('traps', []):
        print('# base trap: ' + t)
    for step, desc, argv in plan(a.name, a.out):
        print('\n# %s: %s' % (step, desc))
        print(' '.join(shlex.quote(x) for x in argv))
        missing = [x for x in argv if '?' in x]
        if missing:
            print('#   missing: %s' % ', '.join(missing))


def cmd_run(a):
    steps = {s: argv for s, _d, argv in plan(a.name, a.out)}
    for s in a.steps:
        argv = steps.get(s)
        if argv is None:
            sys.exit('%s: no such step (%s)' % (s, ', '.join(steps)))
        missing = [x for x in argv if '?' in x or x == '...']
        if missing:
            sys.exit('%s: inputs missing: %s' % (s, ', '.join(missing)))
        print('== %s' % s, flush=True)
        r = subprocess.run(argv, cwd=ROOT)
        if r.returncode:
            sys.exit('%s failed (%d)' % (s, r.returncode))


def cmd_variants(a):
    """effect_variants.py scan -> the effects step again with --variants -> apply, on the translated effect.bin"""
    steps = {s: argv for s, _d, argv in plan(a.name, a.out)}
    fighter = os.path.join(a.out, a.name, 'fighter', a.name)
    eff_bin = os.path.join(fighter, 'script/animcmd/body/effect.bin')
    ids = os.path.join(ROOT, 'fighters', a.name, '%s_effects.json' % a.name)
    var = os.path.join(a.out, 'work', 'variants.json')
    # the scan finds no turned effect in scripts already pointed at their variants (a second run): the
    # variants found before are kept, so the step can run again without the bank losing them
    old = json.load(open(var)) if os.path.exists(var) else []
    if subprocess.run([sys.executable, os.path.join(HERE, 'effect_variants.py'), 'scan', eff_bin, ids, var],
                      cwd=ROOT).returncode:
        sys.exit('variants: the scan failed')
    found = json.load(open(var))
    keys = {(v['effect'], tuple(v['rot'])) for v in found}
    json.dump(found + [v for v in old if (v['effect'], tuple(v['rot'])) not in keys], open(var, 'w'), indent=1)
    for argv in (steps['effects'] + ['--variants', var],
                 [sys.executable, os.path.join(HERE, 'effect_variants.py'), 'apply', eff_bin, ids, eff_bin]):
        print('-- ' + ' '.join(shlex.quote(x) for x in argv), flush=True)
        if subprocess.run(argv, cwd=ROOT).returncode:
            sys.exit('variants: %s failed' % os.path.basename(argv[1]))
    # the bank into the package, named for the fighter (vfxb_to_ptcl names it after the base's)
    import shutil
    fx = os.path.join(a.out, 'work', 'fx')
    dest = os.path.join(fighter, 'effect', a.name)
    os.makedirs(dest, exist_ok=True)
    for f in os.listdir(fx):
        if f.endswith(('.010d0000.ptcl', '.010d0000.efc')):
            shutil.copy(os.path.join(fx, f), os.path.join(dest, a.name + f[f.index('.010d0000'):]))
    print('bank -> %s' % dest)


def cmd_unpack_body(a):
    """the base's body scripts: vanilla effect / sound / expression / motion.mtable, the universal-mechanics
    game.bin (build/universal_mechanics_all.zip)"""
    import shutil
    import zipfile
    cfg = load_cfg(a.name)
    src = port_sources.load()
    base = cfg['base']
    van = os.path.join(src['vanilla'], 'fighter', base, 'script/animcmd/body')
    os.makedirs(a.dest, exist_ok=True)
    for f in ('effect.bin', 'sound.bin', 'expression.bin', 'motion.mtable'):
        shutil.copy(os.path.join(van, f), a.dest)
    z = zipfile.ZipFile(os.path.join(ROOT, 'build/universal_mechanics_all.zip'))
    want = [n for n in z.namelist() if n.endswith('fighter/%s/script/animcmd/body/game.bin' % base)]
    if not want:
        sys.exit('build/universal_mechanics_all.zip has no %s game.bin' % base)
    open(os.path.join(a.dest, 'game.bin'), 'wb').write(z.read(want[0]))
    vk = bases().get(base, {}).get('vl_kind', base)
    shutil.copy(os.path.join(src['vanilla'], 'param/fighter/fighter_param_vl_%s.bin' % vk), os.path.join(a.dest, 'vl.bin'))
    print('%s: vanilla effect / sound / expression / motion.mtable / vl (vl.bin), universal-mechanics game.bin' % a.dest)


def cmd_low_models(a):
    """model/body/lNN for each costume: Ultimate's own low model where the costume has one (its lod.xmb: the lowest
    level of detail, body_low for body_high ...; tools/ultimate_fighter.py model --lod-low), else a copy of cNN.
    The lNN folder is cNN's (the face / eyelid packs, model.nut and the rest) with the low build's model.nud /
    metal.nud, their textures named by cNN's ids (each picture matched by content): lNN keeps cNN's ids and .nut
    (fighter_texture_ids: "the same ids as cNN when its .nut holds the same textures")"""
    import shutil
    import tempfile
    import fighter_texture_ids as T
    cfg = load_cfg(a.name)
    body = os.path.join(a.out, a.name, 'fighter', a.name, 'model/body')
    src = port_sources.load()
    U = src.ult_dir(cfg['ult'])
    steps = {k: v for k, _d, v in plan(a.name, a.out)} if U else {}
    done = []
    for c in cfg.get('costumes', ['c00']):
        src_dir = os.path.join(body, c)
        if not os.path.isdir(src_dir):
            sys.exit('low-models: no %s (run the model steps first)' % src_dir)
        dst = os.path.join(body, 'l' + c[1:])
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src_dir, dst)
        lod = U and os.path.exists(os.path.join(U, 'model/body', c, 'lod.xmb')) and not a.copies
        if not lod or 'model-' + c not in steps:
            done.append('l%s (copy)' % c[1:])
            continue
        argv = list(steps['model-' + c])
        tmp = tempfile.mkdtemp(prefix='lod_')
        argv[argv.index(os.path.join(body, c))] = tmp
        r = subprocess.run([sys.executable] + [os.path.join(ROOT, x) if x.startswith('tools/') else x for x in argv[1:]]
                           + ['--lod-low'], cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            sys.exit('low-models %s: %s' % (c, r.stderr[-2000:]))
        by_pic = {h: tid for _hp, _at, tid, h in T.nut_textures(open(os.path.join(src_dir, 'model.nut'), 'rb').read())}
        own = {tid: h for _hp, _at, tid, h in T.nut_textures(open(os.path.join(tmp, 'model.nut'), 'rb').read())}
        missing = [hex(t) for t, h in own.items() if h not in by_pic]
        if missing:
            sys.exit('low-models %s: the low model uses pictures %s not in %s/model.nut' % (c, missing, c))
        mapping = {t: by_pic[h] for t, h in own.items()}
        for f in ('model.nud', 'metal.nud'):
            if os.path.exists(os.path.join(tmp, f)):
                open(os.path.join(dst, f), 'wb').write(T.nud_set_ids(open(os.path.join(tmp, f), 'rb').read(), mapping))
        for f in ('model.vbn', 'model.jtb'):              # the same skeleton (needed_bones reads every mesh): checked
            if open(os.path.join(tmp, f), 'rb').read() != open(os.path.join(src_dir, f), 'rb').read():
                sys.exit('low-models %s: %s differs from %s\'s' % (c, f, c))
        shutil.rmtree(tmp)
        done.append('l%s (Ultimate\'s LOD)' % c[1:])
    print('low models: %s' % ', '.join(done))


def cmd_check(a):
    r = subprocess.run([sys.executable, os.path.join(HERE, 'port_check.py'), a.name] + a.pkgs)
    sys.exit(r.returncode)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('status')
    p.add_argument('name')
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser('init')
    p.add_argument('name')
    p.add_argument('--ult')
    p.add_argument('--base', required=True)
    p.add_argument('--kind', required=True)
    p.add_argument('--ui-name', required=True)
    p.add_argument('--trait')
    p.add_argument('--force', action='store_true')
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser('effects')
    p.add_argument('name')
    p.set_defaults(fn=cmd_effects)
    p = sub.add_parser('stats')
    p.add_argument('name')
    p.add_argument('fighter_param')
    p.add_argument('out')
    p.set_defaults(fn=cmd_stats)
    for n, fn in (('plan', cmd_plan), ('run', cmd_run)):
        p = sub.add_parser(n)
        p.add_argument('name')
        if n == 'run':
            p.add_argument('steps', nargs='+')
        p.add_argument('--out', default=os.path.join(ROOT, 'build', 'port'))
        p.set_defaults(fn=fn)
    p = sub.add_parser('variants')
    p.add_argument('name')
    p.add_argument('--out', default=os.path.join(ROOT, 'build', 'port'))
    p.set_defaults(fn=cmd_variants)
    p = sub.add_parser('unpack-body')
    p.add_argument('name')
    p.add_argument('dest')
    p.set_defaults(fn=cmd_unpack_body)
    p = sub.add_parser('low-models')
    p.add_argument('name')
    p.add_argument('--out', default=os.path.join(ROOT, 'build', 'port'))
    p.add_argument('--copies', action='store_true', help='copies of cNN even where Ultimate has a low model')
    p.set_defaults(fn=cmd_low_models)
    p = sub.add_parser('check')
    p.add_argument('name')
    p.add_argument('pkgs', nargs='+')
    p.set_defaults(fn=cmd_check)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
