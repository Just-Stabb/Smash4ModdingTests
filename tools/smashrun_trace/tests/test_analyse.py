#!/usr/bin/env python3
"""analyse.py on a synthetic session (update map, the Goomba's hand-read behaviour plus planted mistakes) and the diff
against the repo's specs.

  python3 tools/smashrun_trace/tests/test_analyse.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import analyse     # noqa: E402

FAILS = []
N = [0]


def check(c, msg):
    N[0] += 1
    if not c:
        FAILS.append(msg)
        print('FAIL:', msg)


def synthetic():
    ev = [{'t': 'session', 'f': 0, 'map': 'update', 'toolkit': '1.0.0'}]
    I = '0x0C000100'
    own = {'inst': I, 'kind': 'kuribo'}
    ev.append({'t': 'call', 'f': 1, 'cat': 'stage', 'hook': 'app::StageFieldSmash::StageFieldSmash()', 'args': {},
               'caller': '0x0'})
    ev.append({'t': 'spawn', 'f': 5, 'inst': I, 'kind': 'kuribo', 'var': 1})
    f = 10
    x = 0.0
    for cycle in range(3):
        for sid, dur, vx in ((3, 100, 0.6), (4, 31, -0.4), (5, 111, 1.0), (6, 20, 0.2)):
            ev.append({'t': 'state', 'f': f, 'kind': 'kuribo', 'inst': I, 'role': 'enter', 'state': sid,
                       'pos': [x, 0.0, 0.0], 'lr': 1.0})
            if sid == 4:
                # the hand-read CRY at the enter's call site (0x333A4 -> return address 0x333A8)
                ev.append({'t': 'call', 'f': f, 'cat': 'sound', 'hook': 'app::Behavior::play_se(unsigned int, bool)',
                           'args': {'this': I, 'a0': 0x28D0002, 'a1': False}, 'owner': own,
                           'caller': 'enemy_fs+0x333A8'})
            if sid == 5:
                ev.append({'t': 'call', 'f': f, 'cat': 'attack', 'hook': 'app::Behavior::create_attack_data('
                           'EnemyParamVL::InnerEnemyAttackParam const&)', 'args': {'this': I}, 'owner': own,
                           'caller': 'enemy_fs+0x1000', 'attack': {'state': 5, 'id': 0, 'part': 0, 'node': 4,
                                                                   'power': 1, 'angle': 100, 'kbg': 100, 'fkb': 80,
                                                                   'bkb': 0, 'size': 3, 'x': -1.0, 'y': 0.0,
                                                                   'z': 0.0}})
                ev.append({'t': 'call', 'f': f + 2, 'cat': 'rng', 'hook': 'app::Behavior::random_range(int, int)',
                           'args': {'this': I, 'a0': 1, 'a1': 100}, 'owner': own, 'caller': 'enemy_fs+0x2000',
                           'id': 100 + cycle})
                ev.append({'t': 'ret', 'f': f + 2, 'id': 100 + cycle, 'r0': 37, 'r0_s': 37, 's0': 0.0})
            # a position sample half way through the state
            ev.append({'t': 'state', 'f': f + dur // 2, 'kind': 'kuribo', 'inst': I, 'role': 'update', 'state': sid,
                       'pos': [x + vx * (dur // 2), 0.0, 0.0]})
            x += vx * dur
            f += dur
    # planted mistakes: an attack with a wrong angle, a sound in the wrong state, a transition 6 -> 2
    ev.append({'t': 'state', 'f': f, 'kind': 'kuribo', 'inst': I, 'role': 'enter', 'state': 5, 'pos': [x, 0, 0]})
    ev.append({'t': 'call', 'f': f, 'cat': 'attack', 'hook': 'app::Behavior::create_attack_data(x)', 'args': {},
               'owner': own, 'caller': 'enemy_fs+0x1000', 'attack': {'state': 5, 'id': 0, 'power': 1, 'angle': 45,
                                                                      'kbg': 100, 'fkb': 80, 'bkb': 0, 'size': 3,
                                                                      'node': 4}})
    ev.append({'t': 'call', 'f': f + 1, 'cat': 'sound', 'hook': 'app::Behavior::play_se(unsigned int, bool)',
               'args': {'a0': 0x28D0004}, 'owner': own, 'caller': 'enemy_fs+0x5000'})
    ev.append({'t': 'state', 'f': f + 50, 'kind': 'kuribo', 'inst': I, 'role': 'enter', 'state': 2})
    # params dump equal to the spec's P0, a wrong P1 interval
    spec = json.load(open(os.path.join(analyse.REPO_SPECS, 'kuribo.json')))
    groups = []
    for m in spec['params']['members']:
        if m['type'] == 'array':
            vals = [list(r) for r in m['values']]
            if m['index'] == 1:
                vals[0][1] = 90
            groups.append({'index': m['index'], 'values': vals})
    ev.append({'t': 'dump', 'f': f + 60, 'what': 'params', 'kind': 'kuribo', 'groups': groups})
    # items / chest / stat / door / hazard / spawner
    for i in range(10):
        ev.append({'t': 'call', 'f': 1000 + i, 'cat': 'item', 'hook': 'app::ItemManager::create_item(x)',
                   'args': {'a0': '0x1', 'a0_raw': '%08x' % (3 if i < 7 else 5)}, 'caller': 'code.bin:0x1'})
    ev.append({'t': 'call', 'f': 1100, 'cat': 'chest', 'hook': 'app::GconEventTreasure::setup(lib::Vector3, float, '
               'bool)', 'args': {'this': '0x1', 'a0': [1, 2, 0], 'a1': 0.0, 'a2': True}})
    for v in (1.0, 2.5, 4.0):
        ev.append({'t': 'call', 'f': 1200, 'cat': 'stat', 'hook': 'app::FighterInformation::set_power_up_point('
                   'app::FighterPowerUpKind, float, bool)', 'args': {'a0': 2, 'a1': v, 'a2': True}})
    ev.append({'t': 'call', 'f': 1300, 'cat': 'door', 'hook': 'app::GconEventDoor::setup_data(lib::Vector3, '
               'unsigned int, bool)', 'args': {'this': '0xD', 'a0': [100.0, -20.0, 0.0], 'a1': 3, 'a2': True}})
    for k in range(4):
        ev.append({'t': 'call', 'f': 2000 + 90 * k, 'cat': 'hazard', 'hook': 'app::GimmickControllerBase::'
                   'as_set_all_enabled(bool)', 'args': {'this': '0xA', 'a0': k % 2 == 0}})
    ev.append({'t': 'call', 'f': 2500, 'cat': 'spawn', 'hook': 'app::EnemyManager::create_request(x)',
               'args': {'a0_raw': '01000000'}})
    return ev


def main():
    p = tempfile.mktemp(suffix='.jsonl')
    with open(p, 'w') as fh:
        for e in synthetic():
            fh.write(json.dumps(e) + '\n')
    out = tempfile.mktemp(suffix='.md')
    js = tempfile.mktemp(suffix='.json')
    an, d = analyse.main([p, '--out', out, '--json', js])
    k = an.kinds['kuribo']
    check(k['trans'][(3, 4)] == 3 and k['trans'][(4, 5)] == 3 and k['trans'][(5, 6)] == 3, 'transitions counted')
    st4 = analyse.mmm(k['states'][4])
    check(st4 and st4['min'] == 31 and st4['max'] == 31, 'state 4 lasts 31 frames: %s' % st4)
    st5 = analyse.mmm(k['states'][5])
    check(st5 and st5['median'] == 111, 'state 5 lasts 111 frames')
    sp3 = [a for a, _b, _c in k['speeds'][3]]
    check(sp3 and abs(sp3[0] - 0.6) < 1e-6, 'walk speed 0.6 / frame from the positions: %s' % sp3[:3])
    a5 = k['attacks'][5]
    check(a5 and a5[0]['on'] == 0 and a5[0]['off'] == 111, 'attack on at frame 0, off at 111 (the state change)')
    x = d['kuribo']
    conf = '\n'.join(x['confirmed'])
    mis = '\n'.join(x['mismatches'])
    check('transition 3 -> 4' in conf and 'transition 5 -> 6' in conf, 'spec transitions confirmed')
    check('sound 0x28D0002 in state 4' in conf, 'the CRY sound confirmed in state 4')
    check('sound call site 0x333A4' in conf, 'exact call site confirmed (update map)')
    check('attack entry 0 (state 5): every field' in conf, 'the charge attack confirmed')
    check('angle trace 45 spec 100' in mis, 'a wrong attack angle reported: %s' % mis)
    check('sound 0x28D0004 played in state 5' in mis, 'a sound in the wrong state reported')
    check('transition 5 -> 2' in mis, 'an unknown transition reported')
    check('params P0 (1 entries) equal the vl values' in conf, 'P0 confirmed')
    check('P1[0].f1 trace 90 spec 100' in mis, 'the wrong search interval reported')
    text = open(out).read()
    check('## Spawns' in text and 'StageFieldSmash' in text, 'spawn table by stage')
    check("'app::ItemManager::create_item': 10" in text, 'item tally')
    check('last set_power_up_point value per stat kind: {2: 4.0}' in text, 'stat totals')
    check('as_set_all_enabled->as_set_all_enabled' in text and '90 / 90 / 90' in text, 'hazard phase lengths')
    check('GconEventDoor::setup_data' in text and '100.0' in text, 'door positions listed')
    j = json.load(open(js))
    check('kuribo' in j['diff'], 'JSON report')
    print('analyse: %d checks, %d failed' % (N[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
