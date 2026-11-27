#!/usr/bin/env python3
"""The tracer against the fake Azahar (tests/fake_azahar.py: Unicorn running the dump's own enemy_fs.cro, loaded and
relocated as the RO service loads it, behind a Citra-style GDB stub).

  python3 tools/smashrun_trace/tests/test_fake_azahar.py [DUMP_DIR]     (default: $S3DS_DUMP)

DUMP_DIR holds static.crs and cro/{enemy_fs,main_field}.cro (the base game's: the dump's RomFS; the update's
code.bin / CROs are not in the scratch copy, so the base game's map, srtrace/maps/enemy_fs_base.json, is used).
Checks, with Z0 breakpoints and again with the BKPT fallback (a stub without Z0):
- the module scan finds static.crs / enemy_fs / main_field at the bases they were loaded at, and the map chosen is
  the base map (every kind's create export at the map's offset);
- the CRO loader's relocations: the Goomba's vtable words point at the run-time functions;
- the real Goomba create (enemy_fs + its offset): a spawn event with the kind / variation / instance;
- the real Goomba notice-hop enter (state 4): a state event; its play_se call through the module's import veneer
  logged with id 0x28D0002 (hand read: CRY) and the Goomba as the owner; the hop speed it writes (P0 f7 = -0.4)
  in the snapshot's energy words;
- create_attack_data with the Goomba's P2 entry 0: power 1, angle 100, KBG 100, FKB 80, BKB 0, size 3, node 4;
- random_range: the call and its return value 42; an effect request through the Goomba's Effect module (owner via
  module); spawn / door / chest / stat / hazard / sound calls with their decoded arguments;
- the frame clock (StageManager::process_fix_position) numbering the events;
- every breakpoint removed and memory restored (the BKPT run) at the end;
- dump params: the Goomba's P0 / P1 / P2 read back from the EnemyParamAccessor singleton.
"""
import json
import os
import struct
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import world as Wd                  # noqa: E402
import fake_azahar as F             # noqa: E402
from srtrace import tracer          # noqa: E402

FAILS = []
PASSES = [0]


def check(cond, msg):
    if cond:
        PASSES[0] += 1
    else:
        FAILS.append(msg)
        print('FAIL:', msg)


def build(dump):
    w = Wd.World(dump)
    m = w.m
    mp = json.load(open(os.path.join(os.path.dirname(HERE), 'srtrace', 'maps', 'enemy_fs_base.json')))
    k = mp['kinds']['kuribo']
    w.param_accessor({'kuribo': 1})
    acc = w.accessor(mp['accessor'])
    a = w.addr
    # check_cliff_distance_lr: no ledge behind (so the hop keeps P0 f7)
    for d, fn in w.by_dem.items():
        if 'check_cliff_distance_lr' in d:
            m.specials[fn & ~1] = lambda mm: mm.set_reg(0, 0)
    clock = a('app::StageManager::process_fix_position()')
    create = w.ef.base + k['create']
    st4 = w.ef.base + k['states']['4']['enter']
    # the instance the create will make: operator new's first allocation from here on
    # P2 entry 0 / an AttackData / params for the framework calls
    p2 = [x for x in w.params['kuribo'] if x.get('index') == 2][0]
    ent = m.alloc(168)
    for off, v in zip(p2['offsets'], p2['values'][0]):
        m.write(ent + off, struct.pack('<f', v) if isinstance(v, float) else struct.pack('<i', v))
    door = w.gimmick_object('GconEventDoor')
    mgr = m.alloc(0x100)
    cparam = m.alloc(0x40)
    m.write(cparam, struct.pack('<IIff', 1, 2, 30.0, 4.0))
    box = m.alloc(0x40)
    atkdata = m.alloc(0x80)
    m.write(atkdata, struct.pack('<ff', 12.0, 361.0))
    fi = m.alloc(0x100)
    gim = m.alloc(0x100)
    sndmod = m.alloc(0x100)
    steps = []
    tick = lambda: steps.append(('clock', clock, {}, None, None))
    tick()
    steps.append(('create', create, {0: acc, 1: 1, 2: 0}, None, None))
    tick()

    # registers given as a function are filled in when the step starts (the instance exists after the create ran)
    Late = lambda fn: fn
    inst = lambda: find_inst(m, acc)
    steps.append(('st4', st4, Late(lambda: {0: inst()}), None, None))
    tick()
    steps.append(('atk', a('app::Behavior::create_attack_data(EnemyParamVL::InnerEnemyAttackParam const&)'),
                  Late(lambda: {0: inst(), 1: ent}), None, None))
    steps.append(('rng', a('app::Behavior::random_range(int, int)'), Late(lambda: {0: inst(), 1: 0, 2: 100}), None,
                  None))
    effect_mod = m.r32(acc + mp['accessor']['Effect'])
    vec_a, vec_b = m.alloc(16), m.alloc(16)
    m.write(vec_a, struct.pack('<3f', 0.0, 5.0, 0.0))
    m.write(vec_b, struct.pack('<3f', 0.0, 0.0, 90.0))
    eff = 'app::EffectModuleImpl::req(int, lib::Vector3 const&, lib::Vector3 const&, float, unsigned int, int, bool, int)'
    steps.append(('effect', a(eff), {0: effect_mod, 1: 0x1000026, 2: vec_a, 3: vec_b}, {0: 1.5}, [0, 3, 1, 0]))
    tick()
    steps.append(('spawn', a('app::EnemyManager::create_request(app::Enemy::EnemyCreateParam const&)'),
                  {0: mgr, 1: cparam}, None, None))
    steps.append(('door', a('app::GconEventDoor::setup_data(lib::Vector3, unsigned int, bool)'), {0: door, 1: 3, 2: 1},
                  {0: 100.0, 1: -20.0, 2: 0.0}, None))
    steps.append(('stat', a('app::FighterInformation::set_power_up_point(app::FighterPowerUpKind, float, bool)'),
                  {0: fi, 1: 2, 2: 1}, {0: 3.5}, None))
    steps.append(('chest', a('app::FieldSmashManager::get_treasurebox_ejection_data(int, '
                             'app::FieldSmashTreasureboxEjectionData*)'), {0: mgr, 1: 1, 2: box}, None, None))
    steps.append(('hazard', a('app::GimmickControllerBase::as_set_attack_data(unsigned int, app::AttackData const&)'),
                  {0: gim, 1: 0, 2: atkdata}, None, None))
    steps.append(('sound', a('app::SoundModuleImpl::play_se(unsigned int, bool, bool, bool, bool)'),
                  {0: sndmod, 1: 0x28D0004, 2: 1, 3: 0}, None, [0]))
    for _ in range(3):
        tick()
    return w, mp, steps, acc


def find_inst(m, acc):
    # the Behavior whose accessor word (+4) is acc: the create's allocation (heap scan)
    for a in range(F.HEAP + 0x10000, m.heap, 0x10):
        if m.r32(a + 4) == acc and m.r32(a + 0xC) == 1:
            return a
    return 0


def run_trace(dump, z0=True, extra_cfg=None, more_steps=None):
    w, mp, steps, acc = build(dump)
    if more_steps:
        steps = steps[:2] + more_steps(w, mp, acc) + steps[2:]
    sc = F.Scenario(w.m, steps)
    srv = F.GDBServer(w.m, sc, z0=z0).start()
    out = tempfile.mktemp(suffix='.jsonl')
    cfg = {'port': srv.port, 'out': out, 'map': 'auto', 'mode': 'light', 'reconnect': False, 'dump_on_stage': False,
           'rescan_every': 1e9, 'cats': None}
    cfg.update(extra_cfg or {})
    tr = tracer.Tracer(cfg, log_print=lambda *a: None)
    th = threading.Thread(target=tr.run, daemon=True)
    th.start()
    th.join(120)
    check(not th.is_alive(), 'the tracer finished (z0=%s)' % z0)
    srv.close()
    evs = [json.loads(l) for l in open(out)]
    tr.out_path = out
    return w, mp, evs, sc, tr, srv


def verify(dump, z0):
    tag = '[%s] ' % ('Z0' if z0 else 'BKPT')
    w, mp, evs, sc, tr, srv = run_trace(dump, z0)
    by = lambda t: [e for e in evs if e['t'] == t]
    sess = by('session')
    check(len(sess) == 1 and sess[0]['map'] == 'base', tag + 'session header with the base map: %s' %
          (sess[0]['map'] if sess else None))
    mods = {x['name']: int(x['base'], 16) for x in (sess[0]['modules'] if sess else [])}
    check(mods.get('enemy_fs') == Wd.CRO_BASES['enemy_fs'][0], tag + 'enemy_fs found at its load base')
    check(mods.get('main_field') == Wd.CRO_BASES['main_field'][0], tag + 'main_field found at its load base')
    check(mods.get('|static|') == Wd.CRS_ADDR, tag + 'static.crs found at its address')
    seg = [x for x in sess[0]['modules'] if x['name'] == 'enemy_fs'][0]['segments'] if sess else []
    check(seg and int(seg[2][0], 16) == Wd.CRO_BASES['enemy_fs'][1], tag + 'enemy_fs .data at the data buffer')
    spawn = by('spawn')
    check(len(spawn) == 1 and spawn[0]['kind'] == 'kuribo' and spawn[0]['var'] == 0, tag + 'spawn event: %s' % spawn)
    inst = spawn[0]['inst'] if spawn else None
    st = [e for e in by('state') if e.get('state') == 4]
    check(len(st) == 1 and st[0]['role'] == 'enter' and st[0]['inst'] == inst, tag + 'state 4 enter event')
    if st:
        check(st[0].get('pos') == [10.0, 2.5, 0.0] and st[0].get('lr') == 1.0, tag + 'snapshot position / lr: %s %s' %
              (st[0].get('pos'), st[0].get('lr')))
        check(st[0]['fn'] == 'enemy_fs+0x%X' % mp['kinds']['kuribo']['states']['4']['enter'], tag + 'state fn offset')
    calls = by('call')
    se = [c for c in calls if c['hook'] == 'app::Behavior::play_se(unsigned int, bool)']
    check(len(se) == 1 and se[0]['args'].get('a0') == 0x28D0002, tag + 'play_se 0x28D0002 from the real state code: %s'
          % [c['args'] for c in se])
    if se:
        check(se[0].get('owner', {}).get('kind') == 'kuribo' and se[0]['owner']['inst'] == inst, tag + 'play_se owner')
        # the notice-hop enter ends with a tail call (b play_se): the return address is the enter's caller's, here
        # the scenario's
        check(se[0]['caller'] == '0x%08X' % F.RET_MAGIC, tag + 'play_se tail-called by the enter: %s' % se[0]['caller'])
        check(se[0].get('ctx_state') == 4, tag + 'play_se in the state 4 context')
    st4_frame = st[0]['f'] if st else None
    # the hop speed the real code wrote: visible in the next snapshot of the energy (P0 f7 = -0.4 at +0x20)
    e20 = struct.unpack('<f', w.m.read(w.energy + 0x20, 4))[0]
    check(abs(e20 + 0.4) < 1e-6, tag + 'the notice hop wrote P0 f7 = -0.4 to the energy +0x20 (got %r)' % e20)
    later = [e for e in by('call') if e.get('owner', {}).get('inst') == inst]
    atk_ev = [e for e in evs if e['t'] == 'state' and e.get('inst') == inst]
    check(atk_ev and atk_ev[0].get('energy') is not None, tag + 'energy words in the snapshot')
    atk = [c for c in calls if 'create_attack_data' in c['hook']]
    check(len(atk) == 1, tag + 'create_attack_data logged')
    if atk:
        a = atk[0]['attack']
        check((a['power'], a['angle'], a['kbg'], a['fkb'], a['bkb'], a['size'], a['node'], a['x'], a['state']) ==
              (1, 100, 100, 80, 0, 3, 4, -1.0, 5), tag + 'attack fields: %s' % a)
        check(atk[0]['owner']['kind'] == 'kuribo', tag + 'attack owner')
    rr = [c for c in calls if 'random_range(int, int)' in c['hook']]
    rets = {r['id']: r for r in by('ret')}
    check(len(rr) == 1 and rr[0]['args'].get('a0') == 0 and rr[0]['args'].get('a1') == 100, tag + 'random_range args')
    if rr:
        check(rets.get(rr[0]['id'], {}).get('r0') == 42, tag + 'random_range returned 42: %s' % rets.get(rr[0]['id']))
    ef = [c for c in calls if c['hook'].startswith('app::EffectModuleImpl::req(int, lib::Vector3')]
    check(len(ef) == 1 and ef[0]['args'].get('a0') == 0x1000026, tag + 'effect id')
    if ef:
        check(ef[0]['args'].get('a1_val') == [0.0, 5.0, 0.0] and ef[0]['args'].get('a2_val') == [0.0, 0.0, 90.0],
              tag + 'effect offsets / rotation: %s' % ef[0]['args'])
        check(ef[0]['args'].get('a3') == 1.5, tag + 'effect scale (s0) %s' % ef[0]['args'].get('a3'))
        check(ef[0]['args'].get('a4') == 0 and ef[0]['args'].get('a5') == 3, tag + 'effect stack args %s' % ef[0]['args'])
        check(ef[0].get('owner', {}).get('via') == 'Effect' and ef[0]['owner']['kind'] == 'kuribo',
              tag + 'effect owner through the Effect module: %s' % ef[0].get('owner'))
    sp = [c for c in calls if 'create_request' in c['hook']]
    check(len(sp) == 1 and sp[0]['args'].get('a0_raw', '').startswith('0100000002000000'), tag + 'create_request param')
    dr = [c for c in calls if 'GconEventDoor::setup_data' in c['hook']]
    check(len(dr) == 1 and dr[0]['args'].get('a0') == [100.0, -20.0, 0.0] and dr[0]['args'].get('a1') == 3 and
          dr[0]['args'].get('a2') is True, tag + 'door setup_data args %s' % (dr[0]['args'] if dr else None))
    stt = [c for c in calls if 'set_power_up_point' in c['hook']]
    check(len(stt) == 1 and stt[0]['args'].get('a0') == 2 and stt[0]['args'].get('a1') == 3.5, tag + 'stat args')
    ch = [c for c in calls if 'get_treasurebox_ejection_data' in c['hook']]
    check(len(ch) == 1 and ch[0]['args'].get('a0') == 1 and ch[0]['cat'] == 'chest', tag + 'chest call')
    hz = [c for c in calls if 'as_set_attack_data' in c['hook']]
    check(len(hz) == 1 and hz[0]['cat'] == 'hazard' and hz[0]['args'].get('a1_raw', '').startswith('00004041'),
          tag + 'hazard attack data')
    snd = [c for c in calls if c['hook'].startswith('app::SoundModuleImpl::play_se')]
    check(len(snd) == 1 and snd[0]['args'].get('a0') == 0x28D0004 and snd[0]['args'].get('a3') is False,
          tag + 'SoundModuleImpl::play_se args %s' % (snd[0]['args'] if snd else None))
    # frames: clock ticks before / between the steps
    check(spawn and spawn[0]['f'] == 1 and st4_frame == 2, tag + 'frame numbers (spawn %s, state %s)' %
          (spawn and spawn[0]['f'], st4_frame))
    check(ef and ef[0]['f'] == 3 and dr and dr[0]['f'] == 4, tag + 'frames of the effect / door')
    raws = by('raw')
    check(raws and raws[0]['inst'] == inst and len(raws[0]['this']) >= 0x200 * 2, tag + 'raw dump on first sight')
    # nothing left behind
    check(not w.m.bps, tag + 'every Z0 breakpoint removed: %s' % w.m.bps)
    if not z0:
        bk = struct.pack('<I', 0xE1200070)
        left = [a for a in tr.t.bps] + [h for h in (w.addr('app::Behavior::play_se(unsigned int, bool)'),)
                                       if w.m.read(h & ~1, 4) == bk]
        check(not left, tag + 'every BKPT word restored: %s' % left)
        check(any(p.startswith('M') for p in srv.packets), tag + 'the BKPT fallback wrote memory')
    print('%s%d events, scenario %s' % (tag, len(evs), [x for x in sc.log if not isinstance(x, str)] or 'ok'))
    return tr.out_path


def verify_full(dump):
    """full mode: the Goomba's real walk update (state 3) three times, a clock tick before each"""
    def extra(w, mp, acc):
        up = w.ef.base + mp['kinds']['kuribo']['states']['3']['update']
        clock = w.addr('app::StageManager::process_fix_position()')
        out = []
        for _ in range(3):
            out.append(('clock', clock, {}, None, None))
            out.append(('walk', up, lambda: {0: find_inst(w.m, acc)}, None, None))
        return out
    w, mp, evs, sc, tr, srv = run_trace(dump, True, {'mode': 'full'}, extra)
    ups = [e for e in evs if e['t'] == 'state' and e.get('role') == 'update' and e.get('state') == 3]
    check(len(ups) == 3 and [e['f'] for e in ups] == [2, 3, 4], '[full] three walk updates on frames 2-4: %s' %
          [e['f'] for e in ups])
    cs = [e for e in evs if e['t'] == 'call' and 'change_state_interrupt_base' in e['hook']]
    check(len(cs) == 3 and all(c['args'].get('a0') == 3 for c in cs) and all(c['owner']['kind'] == 'kuribo'
                                                                             for c in cs),
          '[full] the real walk update re-enters state 3 (wall ahead, hand read): %s' % [c['args'].get('a0') for c in cs])
    rv = [e for e in evs if e['t'] == 'call' and 'reverse_lr' in e['hook']]
    check(len(rv) == 3 and rv[0]['cat'] == 'facing', '[full] reverse_lr before each re-enter')
    cl = [e for e in evs if e['t'] == 'call' and 'check_cliff()' in e['hook']]
    check(len(cl) == 3 and cl[0]['cat'] == 'ai', '[full] the AI ledge check logged')
    check(not w.m.bps, '[full] breakpoints removed')


def verify_dump_params(dump):
    w, mp, steps, acc = build(dump)
    sc = F.Scenario(w.m, [])
    srv = F.GDBServer(w.m, sc).start()
    out = tempfile.mktemp(suffix='.jsonl')
    tr = tracer.Tracer({'port': srv.port, 'out': out, 'reconnect': False, 'dry': True}, log_print=lambda *a: None)
    tr.run(one_shot=lambda t: (t.dump_params(), t.dump_objects()))
    srv.close()
    evs = [json.loads(l) for l in open(out)]
    d = [e for e in evs if e['t'] == 'dump' and e.get('what') == 'params' and e.get('kind') == 'kuribo']
    check(len(d) == 1, '[dump] kuribo params dumped')
    if d:
        g = {x['index']: x for x in d[0]['groups']}
        spec = json.load(open(os.path.join(Wd.ROOT, 'reference', 'smashrun_enemy_specs', 'kuribo.json')))
        sv = {m['index']: m['values'] for m in spec['params']['members'] if m['type'] == 'array'}
        for gi in (0, 1, 2):
            got = g.get(gi, {}).get('values')
            ok = got is not None and all(abs(a - b) < 1e-5 for ra, rb in zip(got, sv[gi]) for a, b in zip(ra, rb))
            check(ok and len(got) == len(sv[gi]), '[dump] P%d equals the spec values' % gi)
    o = [e for e in evs if e['t'] == 'dump' and e.get('what') == 'object']
    check(any(e['class'] == 'N3app13GconEventDoorE' for e in o), '[dump] the door object found by its RTTI name')
    check(not w.m.bps and not any(p.startswith('Z0') for p in srv.packets), '[dump] dry: no breakpoint planted')


def main():
    dump = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('S3DS_DUMP')
    if not dump or not os.path.exists(os.path.join(dump, 'static.crs')):
        print('SKIP: no dump (pass DUMP_DIR with static.crs and cro/enemy_fs.cro)')
        return 0
    log = verify(dump, True)
    verify(dump, False)
    verify_full(dump)
    # the analysis of the fake session against the repo's specs (base map: no exact call sites)
    import analyse
    an, d = analyse.main([log, '--out', tempfile.mktemp(suffix='.md')])
    conf = d.get('kuribo', {}).get('confirmed', [])
    check(any('sound 0x28D0002 in state 4' in c for c in conf), '[analyse] the real code\'s CRY confirmed in state 4')
    check(not d.get('kuribo', {}).get('mismatches'), '[analyse] no mismatch: %s' % d.get('kuribo', {}).get('mismatches'))
    verify_dump_params(dump)
    print('fake Azahar: %d passed, %d failed' % (PASSES[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
