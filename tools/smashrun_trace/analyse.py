#!/usr/bin/env python3
"""Smash Run trace analysis: turns the tracer's JSON-lines logs into per-kind reports and a diff against the repo's
port specs.

  python analyse.py LOG.jsonl [LOG2.jsonl ...] [--out report.md] [--json report.json]
                    [--specs DIR] [--hand-read FILE] [--apply-confirmations]

Report sections:
- per enemy kind: the state machine (transitions with counts), per-state frame counts (min / median / max, from
  enter to the next enter), speeds per state (position change per frame from the snapshots), attacks per state with
  their on / off frames relative to the state's start and every field, effects / sounds per state with frame
  offsets, AI calls (inputs, return values, the state taken next), RNG calls, params (dumps);
- spawns: per kind and per stage / room (the last stage load seen), per minute; leave / despawn: lifetimes, the
  trigger calls (init / update_common_leave, remove_enemy_by_id) and the state the enemy was in;
- items / drops / chests / power-ups: tallies per hook and per value (with the RNG calls next to them), stat boosts
  (set_power_up_point per stat kind, running totals), power-up level samples (stat -> multiplier curve);
- doors / hazards: every door / warp call with its position, every hazard object's call timeline and phase lengths;
- the spec diff (reference/smashrun_enemy_specs/<kind>.json, hand_read.json): transitions, sounds, effects,
  attacks and params the trace shows that the specs don't (MISMATCH) and those both have (CONFIRMED). Call sites are
  matched exactly when the trace ran on the map the specs were read from (the update's enemy_fs.cro).
--apply-confirmations writes the result into hand_read.json as each kind's "azahar_trace" entry (confirmed /
mismatches / the sessions it came from); without it nothing in the repo changes.
"""
import argparse
import json
import os
import re
import statistics
import sys
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_SPECS = os.path.abspath(os.path.join(HERE, '..', '..', 'reference', 'smashrun_enemy_specs'))
FPS = 60.0


def load(paths):
    evs, sessions = [], []
    for p in paths:
        for line in open(p, encoding='utf-8'):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            e['_file'] = os.path.basename(p)
            if e.get('t') == 'session':
                sessions.append(e)
            evs.append(e)
    return evs, sessions


def mmm(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return {'n': len(xs), 'min': min(xs), 'median': statistics.median(xs), 'max': max(xs)}


def fmt_mmm(d):
    if not d:
        return '-'
    med = d['median']
    med = ('%g' % med) if isinstance(med, (int, float)) else med
    return '%s / %s / %s (n=%d)' % (('%g' % d['min']), med, ('%g' % d['max']), d['n'])


def site(caller):
    """'enemy_fs+0x333A8' -> call site offset 0x333A4 (the return address - 4)"""
    m = re.match(r'enemy_fs\+0x([0-9A-Fa-f]+)$', caller or '')
    return int(m.group(1), 16) - 4 if m else None


class Analysis:
    def __init__(s, evs, sessions):
        s.evs = evs
        s.sessions = sessions
        s.maps = Counter(x.get('map') for x in sessions)
        s.kinds = defaultdict(lambda: {'inst': set(), 'states': defaultdict(list), 'trans': Counter(),
                                       'speeds': defaultdict(list), 'attacks': defaultdict(list),
                                       'effects': defaultdict(list), 'sounds': defaultdict(list),
                                       'ai': [], 'rng': [], 'params': None, 'lifetimes': [], 'leave': [],
                                       'spawns': 0, 'slots': Counter()})
        s.items, s.chests, s.stats, s.doors, s.hazards = [], [], [], [], defaultdict(list)
        s.spawns, s.rng_all, s.power_levels = [], [], []
        s.stage_by_frame = []
        s.objects = []
        s.rets = {}
        s.run()

    def run(s):
        inst_state = {}            # inst -> (state, enter frame, kind)
        inst_last = {}             # inst -> (frame, pos)
        inst_first = {}
        inst_kind = {}
        open_attacks = defaultdict(list)    # inst -> [attack records still on]
        for e in s.evs:
            if e.get('t') == 'ret':
                s.rets[(e['_file'], e['id'])] = e
        stage = None
        for e in s.evs:
            t = e.get('t')
            f = e.get('f')
            if t == 'spawn':
                k = s.kinds[e['kind']]
                k['spawns'] += 1
                inst_first[e['inst']] = f
                inst_kind[e['inst']] = e['kind']
                s.spawns.append({'kind': e['kind'], 'var': e.get('var'), 'f': f, 'stage': stage})
            elif t in ('state', 'slot'):
                kind, inst = e['kind'], e['inst']
                k = s.kinds[kind]
                k['inst'].add(inst)
                inst_kind[inst] = kind
                inst_first.setdefault(inst, f)
                if t == 'slot':
                    k['slots'][e['role']] += 1
                if e.get('pos') is not None:
                    lf = inst_last.get(inst)
                    cur = inst_state.get(inst)
                    if lf and f is not None and lf[0] is not None and f > lf[0] and cur:
                        dt = f - lf[0]
                        vx = (e['pos'][0] - lf[1][0]) / dt
                        vy = (e['pos'][1] - lf[1][1]) / dt
                        k['speeds'][cur[0]].append((round(vx, 4), round(vy, 4), dt))
                    inst_last[inst] = (f, e['pos'])
                if t == 'state' and e.get('role') == 'enter':
                    prev = inst_state.get(inst)
                    if prev:
                        k['states'][prev[0]].append(f - prev[1] if f is not None and prev[1] is not None else None)
                        k['trans'][(prev[0], e['state'])] += 1
                    inst_state[inst] = (e['state'], f, kind)
                    for a in open_attacks.pop(inst, []):
                        a['off'] = f - a['state_f'] if f is not None and a.get('state_f') is not None else None
            elif t == 'call':
                cat = e.get('cat')
                own = e.get('owner') or {}
                inst = own.get('inst')
                kind = own.get('kind')
                st = inst_state.get(inst) if inst else None
                rel = (f - st[1]) if (st and f is not None and st[1] is not None) else None
                sid = st[0] if st else e.get('ctx_state')
                ret = s.rets.get((e['_file'], e.get('id')))
                rv = ret and {'r0': ret.get('r0_s'), 's0': ret.get('s0')}
                if cat == 'stage':
                    stage = e['hook'].split('::')[1] if '::' in e['hook'] else e['hook']
                    s.stage_by_frame.append((f, stage))
                if kind:
                    k = s.kinds[kind]
                    if cat == 'attack':
                        rec = {'hook': e['hook'], 'state': sid, 'on': rel, 'state_f': st[1] if st else None,
                               'fields': e.get('attack') or e.get('args'), 'site': site(e.get('caller'))}
                        if 'clear' in e['hook']:
                            for a in open_attacks.pop(inst, []):
                                a['off'] = rel
                        else:
                            k['attacks'][sid].append(rec)
                            open_attacks[inst].append(rec)
                    elif cat == 'effect':
                        k['effects'][sid].append({'hook': e['hook'], 'at': rel, 'id': e['args'].get('a0'),
                                                  'args': e['args'], 'site': site(e.get('caller'))})
                    elif cat == 'sound':
                        k['sounds'][sid].append({'hook': e['hook'], 'at': rel, 'id': e['args'].get('a0'),
                                                 'site': site(e.get('caller'))})
                    elif cat == 'ai':
                        k['ai'].append({'hook': e['hook'], 'state': sid, 'at': rel, 'args': e['args'], 'ret': rv,
                                        'f': f})
                    elif cat == 'rng':
                        k['rng'].append({'hook': e['hook'], 'state': sid, 'args': e['args'], 'ret': rv,
                                         'site': site(e.get('caller'))})
                    elif cat == 'leave':
                        k['leave'].append({'hook': e['hook'], 'state': sid, 'f': f, 'args': e['args'], 'ret': rv})
                if cat == 'rng':
                    s.rng_all.append({'hook': e['hook'], 'caller': e.get('caller'), 'args': e['args'], 'ret': rv,
                                      'f': f})
                elif cat in ('item',):
                    s.items.append({'hook': e['hook'], 'f': f, 'args': e['args'], 'ret': rv, 'owner': kind,
                                    'stage': stage, 'caller': e.get('caller')})
                elif cat == 'chest':
                    s.chests.append({'hook': e['hook'], 'f': f, 'args': e['args'], 'ret': rv, 'stage': stage,
                                     'this': e['args'].get('this')})
                elif cat == 'stat':
                    s.stats.append({'hook': e['hook'], 'f': f, 'args': e['args'], 'ret': rv})
                    if 'power_up_level' in e['hook'] and rv:
                        s.power_levels.append((e['args'].get('a0'), rv.get('s0')))
                elif cat == 'door':
                    s.doors.append({'hook': e['hook'], 'f': f, 'args': e['args'], 'this': e['args'].get('this'),
                                    'stage': stage})
                elif cat == 'hazard':
                    s.hazards[e['args'].get('this')].append({'hook': e['hook'], 'f': f, 'args': e['args']})
                elif cat == 'spawn' and not kind:
                    s.spawns.append({'hook': e['hook'], 'f': f, 'args': e['args'], 'stage': stage, 'ret': rv})
                elif cat == 'leave' and 'remove_enemy_by_id' in e['hook']:
                    pass
            elif t == 'dump':
                if e.get('what') == 'params':
                    s.kinds[e['kind']]['params'] = e['groups']
                elif e.get('what') == 'object':
                    s.objects.append(e)
            elif t == 'raw':
                pass
        # lifetimes: spawn (or first sight) -> last event of the instance
        last = {}
        for e in s.evs:
            inst = e.get('inst') or (e.get('owner') or {}).get('inst')
            if inst and e.get('f') is not None:
                last[inst] = e['f']
        for inst, kind in inst_kind.items():
            if inst in inst_first and inst in last:
                s.kinds[kind]['lifetimes'].append(last[inst] - inst_first[inst])

    # ------------------------------------------------------------------------------------------------ report
    def report(s):
        L = []
        w = L.append
        w('# Smash Run trace report')
        w('')
        w('Sessions: %d (%s); maps: %s; events: %d.' % (len(s.sessions), ', '.join(sorted(set(
            x['_file'] for x in s.sessions))), dict(s.maps), len(s.evs)))
        for kind in sorted(s.kinds):
            k = s.kinds[kind]
            if not (k['states'] or k['trans'] or k['spawns'] or k['attacks'] or k['sounds']):
                continue
            w('')
            w('## %s' % kind)
            w('')
            w('Instances seen: %d, spawns: %d, lifetimes (frames) %s' % (len(k['inst']), k['spawns'],
                                                                         fmt_mmm(mmm(k['lifetimes']))))
            if k['trans']:
                w('')
                w('| transition | count |')
                w('|---|---|')
                for (a, b), n in sorted(k['trans'].items()):
                    w('| %s -> %s | %d |' % (a, b, n))
            if k['states']:
                w('')
                w('| state | frames in state (min / median / max) | speed x / y per frame (median) |')
                w('|---|---|---|')
                for sid in sorted(set(k['states']) | set(k['speeds'])):
                    sp = k['speeds'].get(sid) or []
                    vx = statistics.median([a for a, _b, _c in sp]) if sp else None
                    vy = statistics.median([b for _a, b, _c in sp]) if sp else None
                    w('| %s | %s | %s |' % (sid, fmt_mmm(mmm(k['states'].get(sid, []))),
                                            '-' if vx is None else '%g / %g (n=%d)' % (vx, vy, len(sp))))
            for title, key in (('Attacks', 'attacks'), ('Effects', 'effects'), ('Sounds', 'sounds')):
                if not k[key]:
                    continue
                w('')
                w('%s (state: frame offset from the state\'s start -> what):' % title)
                for sid in sorted(k[key], key=lambda x: (x is None, x)):
                    for r in k[key][sid][:40]:
                        if key == 'attacks':
                            fl = r['fields'] or {}
                            w('- state %s, on %s, off %s: %s' % (sid, r['on'], r.get('off'), ', '.join(
                                '%s %s' % (n, fl[n]) for n in ('id', 'part', 'node', 'power', 'angle', 'kbg', 'fkb',
                                                                'bkb', 'size', 'x', 'y', 'z') if n in fl)))
                        else:
                            w('- state %s, frame %s: %s 0x%X' % (sid, r['at'], r['hook'].split('(')[0],
                                                                  r['id'] if isinstance(r['id'], int) else 0))
            if k['ai']:
                w('')
                w('AI calls (first 30):')
                for r in k['ai'][:30]:
                    w('- f%s state %s +%s: %s %s -> %s' % (r['f'], r['state'], r['at'], r['hook'].split('(')[0],
                                                          json.dumps({a: v for a, v in r['args'].items()
                                                                      if a != 'this'}), r['ret']))
            if k['rng']:
                w('')
                w('RNG calls: %d; by site: %s' % (len(k['rng']), dict(Counter(
                    ('0x%X' % r['site']) if r['site'] else r['hook'].split('(')[0] for r in k['rng']))))
            if k['leave']:
                w('')
                w('Leave calls: %s' % dict(Counter((r['hook'].split('(')[0], r['state']) for r in k['leave'])))
            if k['params']:
                w('')
                w('Params in RAM: %s' % '; '.join('P%d: %s' % (g['index'], g['values'][:4]) for g in k['params']))
        # spawns
        w('')
        w('## Spawns')
        by = Counter((x.get('stage'), x.get('kind') or x.get('hook', '').split('(')[0]) for x in s.spawns)
        frames = [e['f'] for e in s.evs if e.get('f') is not None]
        minutes = (max(frames) - min(frames)) / FPS / 60.0 if frames else 0
        w('')
        w('| stage / room | kind (or spawner call) | count | per minute |')
        w('|---|---|---|---|')
        for (st, kd), n in sorted(by.items(), key=lambda x: -x[1]):
            w('| %s | %s | %d | %s |' % (st, kd, n, '%.2f' % (n / minutes) if minutes else '-'))
        # items / chests / stats
        w('')
        w('## Items, drops, chests, power-ups')
        w('')
        w('Item calls: %s' % dict(Counter(x['hook'].split('(')[0] for x in s.items)))
        vals = Counter((x['hook'].split('(')[0], json.dumps(x['args'].get('a0')), x.get('owner')) for x in s.items)
        for (h, a0, own), n in vals.most_common(40):
            w('- %s a0=%s owner=%s: %d' % (h, a0, own, n))
        w('')
        w('Chest calls: %s' % dict(Counter(x['hook'].split('(')[0] for x in s.chests)))
        w('')
        tot = defaultdict(float)
        for x in s.stats:
            if 'set_power_up_point' in x['hook']:
                kd, v = x['args'].get('a0'), x['args'].get('a1')
                if isinstance(v, (int, float)):
                    tot[kd] = v
        w('Stat calls: %s; last set_power_up_point value per stat kind: %s' % (
            dict(Counter(x['hook'].split('(')[0] for x in s.stats)), dict(tot)))
        if s.power_levels:
            curve = defaultdict(set)
            for kd, v in s.power_levels:
                curve[kd].add(v)
            w('power_up_level samples per stat kind: %s' % {k: sorted(v)[:20] for k, v in curve.items()})
        # doors / hazards
        w('')
        w('## Doors and hazards')
        w('')
        for d in s.doors[:200]:
            w('- f%s %s %s %s' % (d['f'], d['hook'].split('(')[0], d['this'],
                                 json.dumps({a: v for a, v in d['args'].items() if a != 'this'})))
        cls = Counter(o['class'] for o in s.objects)
        if cls:
            w('')
            w('Objects in RAM dumps: %s' % dict(cls))
        for obj, calls in list(s.hazards.items())[:100]:
            seq = [(c['f'], c['hook'].split('(')[0].split('::')[-1]) for c in calls]
            gaps = defaultdict(list)
            for (f1, h1), (f2, h2) in zip(seq, seq[1:]):
                if f1 is not None and f2 is not None:
                    gaps[(h1, h2)].append(f2 - f1)
            w('- hazard %s: %d calls; phases %s' % (obj, len(calls), {
                '%s->%s' % k: fmt_mmm(mmm(v)) for k, v in gaps.items()}))
        if s.rng_all:
            w('')
            w('## RNG')
            w('')
            w('Calls by function: %s' % dict(Counter(x['hook'].split('(')[0] for x in s.rng_all)))
        return '\n'.join(L) + '\n'

    # ------------------------------------------------------------------------------------------------ spec diff
    def diff(s, specs_dir, hand_read):
        exact_sites = s.maps.get('update', 0) > 0 and len(s.maps) == 1
        out = {}
        for kind, k in s.kinds.items():
            p = os.path.join(specs_dir, kind + '.json')
            if not os.path.exists(p):
                continue
            sp = json.load(open(p))
            conf, mis = [], []
            allowed = defaultdict(set)
            sounds = defaultdict(set)
            effects = defaultdict(set)
            for st in sp.get('states', []):
                for lst in st.get('summary', {}).values():
                    for it in lst:
                        if it.get('cat') == 'state' and isinstance(it.get('state'), int):
                            allowed[st['id']].add(it['state'])
                        if it.get('cat') == 'sound' and it.get('args'):
                            try:
                                sounds[st['id']].add(int(it['args'][0], 16))
                            except (ValueError, TypeError):
                                pass
                        if it.get('cat') == 'effect' and it.get('args'):
                            try:
                                effects[st['id']].add(int(it['args'][0], 0))
                            except (ValueError, TypeError):
                                pass
            for (a, b), n in k['trans'].items():
                if b in allowed.get(a, ()):
                    conf.append('transition %s -> %s (seen %d)' % (a, b, n))
                else:
                    mis.append('transition %s -> %s seen %d times; the spec\'s state %s code names %s' % (
                        a, b, n, a, sorted(allowed.get(a, [])) or 'none'))
            for sid, lst in k['sounds'].items():
                for r in lst:
                    if not isinstance(r['id'], int):
                        continue
                    if r['id'] in sounds.get(sid, ()):
                        conf.append('sound 0x%X in state %s (frame %s)' % (r['id'], sid, r['at']))
                    elif any(r['id'] in v for v in sounds.values()):
                        mis.append('sound 0x%X played in state %s; the spec has it in state(s) %s' % (
                            r['id'], sid, [x for x, v in sounds.items() if r['id'] in v]))
                    else:
                        mis.append('sound 0x%X in state %s: not in the spec' % (r['id'], sid))
            for sid, lst in k['effects'].items():
                for r in lst:
                    if isinstance(r['id'], int) and r['id'] in effects.get(sid, ()):
                        conf.append('effect 0x%X in state %s' % (r['id'], sid))
            for sid, lst in k['attacks'].items():
                for r in lst:
                    fl = r['fields'] or {}
                    if 'power' not in fl:
                        continue
                    cand = [a for a in sp.get('attacks', []) if a.get('state') == fl.get('state')
                            and a.get('id') == fl.get('id')]
                    if not cand:
                        mis.append('attack state %s id %s (power %s angle %s): no P2 entry in the spec' % (
                            fl.get('state'), fl.get('id'), fl.get('power'), fl.get('angle')))
                        continue
                    a = cand[0]
                    bad = [n for n in ('power', 'angle', 'kbg', 'fkb', 'bkb', 'size', 'node', 'x', 'y', 'z')
                           if n in fl and n in a and abs(float(fl[n]) - float(a[n])) > 1e-4]
                    if bad:
                        mis.append('attack entry %s: %s' % (a.get('entry'), ', '.join(
                            '%s trace %s spec %s' % (n, fl[n], a[n]) for n in bad)))
                    else:
                        conf.append('attack entry %s (state %s): every field; on at frame %s, off %s' % (
                            a.get('entry'), fl.get('state'), r['on'], r.get('off')))
            if k['params']:
                sv = {m['index']: m['values'] for m in sp.get('params', {}).get('members', [])
                      if m.get('type') == 'array'}
                for g in k['params']:
                    ref = sv.get(g['index'])
                    if ref is None:
                        continue
                    diffs = []
                    for e, (ra, rb) in enumerate(zip(g['values'], ref)):
                        for j, (x, y) in enumerate(zip(ra, rb)):
                            if isinstance(x, (int, float)) and isinstance(y, (int, float)) and abs(x - y) > 1e-4:
                                diffs.append('P%d[%d].f%d trace %s spec %s' % (g['index'], e, j, x, y))
                    if diffs:
                        mis += diffs[:20]
                    else:
                        conf.append('params P%d (%d entries) equal the vl values' % (g['index'], len(g['values'])))
            if exact_sites:
                spec_sites = set()
                for st in sp.get('states', []):
                    for lst in st.get('summary', {}).values():
                        for it in lst:
                            if it.get('at'):
                                spec_sites.add(int(it['at'], 16))
                for key in ('sounds', 'effects'):
                    for lst in k[key].values():
                        for r in lst:
                            if r['site'] is not None and r['site'] in spec_sites:
                                conf.append('%s call site 0x%X' % (key[:-1], r['site']))
            durations = {sid: mmm(v) for sid, v in k['states'].items()}
            out[kind] = {'confirmed': sorted(set(conf)), 'mismatches': sorted(set(mis)),
                         'state_frames': durations, 'hand_read_states': (hand_read.get(kind) or {}).get('states')}
        return out


def diff_md(d):
    L = ['', '# Diff against the port specs', '']
    for kind in sorted(d):
        x = d[kind]
        L.append('## %s' % kind)
        L.append('')
        for c in x['confirmed']:
            L.append('- CONFIRMED: ' + c)
        for m in x['mismatches']:
            L.append('- MISMATCH: ' + m)
        for sid, mm in sorted(x['state_frames'].items(), key=lambda t: (t[0] is None, t[0])):
            hr = (x.get('hand_read_states') or {}).get(str(sid))
            L.append('- state %s lasted %s frames%s' % (sid, fmt_mmm(mm), ('; hand read: ' + hr[:160]) if hr else ''))
        L.append('')
    return '\n'.join(L) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('logs', nargs='+')
    ap.add_argument('--out')
    ap.add_argument('--json')
    ap.add_argument('--specs', default=REPO_SPECS)
    ap.add_argument('--hand-read')
    ap.add_argument('--apply-confirmations', action='store_true')
    a = ap.parse_args(argv)
    evs, sessions = load(a.logs)
    an = Analysis(evs, sessions)
    hr_path = a.hand_read or os.path.join(a.specs, 'hand_read.json')
    hand = json.load(open(hr_path)) if os.path.exists(hr_path) else {}
    d = an.diff(a.specs, hand) if os.path.isdir(a.specs) else {}
    text = an.report() + diff_md(d)
    if a.out:
        open(a.out, 'w', encoding='utf-8').write(text)
    else:
        sys.stdout.write(text)
    if a.json:
        json.dump({'diff': d, 'spawns': an.spawns, 'items': an.items, 'chests': an.chests, 'stats': an.stats,
                   'doors': an.doors}, open(a.json, 'w'), indent=1, default=str)
    if a.apply_confirmations and hand:
        files = sorted(set(x['_file'] for x in sessions))
        for kind, x in d.items():
            if kind in hand and (x['confirmed'] or x['mismatches']):
                hand[kind]['azahar_trace'] = {'note': 'confirmed by Azahar trace (tools/smashrun_trace/analyse.py)',
                                              'sessions': files, 'confirmed': x['confirmed'],
                                              'mismatches': x['mismatches']}
        json.dump(hand, open(hr_path, 'w'), indent=1, ensure_ascii=False)
        print('hand_read.json: azahar_trace written for %d kinds' % sum(1 for k in d if k in hand), file=sys.stderr)
    return an, d


if __name__ == '__main__':
    main()
