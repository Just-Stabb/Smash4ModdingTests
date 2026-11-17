#!/usr/bin/env python3
"""An Ultimate port's fighter_param stats from Ultimate's own fighter_param.prc, by name.

  python3 tools/ultimate_stats.py FIGHTER_PARAM_PRC LABELS_CSV ULT_NAME FIGHTER_PARAM_BIN OUT_BIN KIND
          [--base BASE] [--jump-scale 0.82,0.9] [--json OUT.json]

FIGHTER_PARAM_PRC: Ultimate's fighter/common/param/fighter_param.prc; LABELS_CSV: ParamLabels.csv
(github.com/ultimate-research/param-labels); ULT_NAME: the Ultimate fighter (brave, pzenigame, ...);
KIND: the port's fighter kind (fighter_param entry, 0x45 = 69). Prints what it sets, with the rule
for each, and the attributes it leaves (with Ultimate's value where one exists) so a port never
again keeps its base's values by accident (Steve's Pit multi-jump, Hero's rapid jab).

The rules (MAP below) come from comparing the two games' tables over the 51 fighters both have
(docs/ultimate-port-guide.md "Stats"):
- equal in both games for most fighters (Smash 4 = Ultimate): air speeds / accels / brakes,
  gravity, fall / fast fall, jump x speeds, the double jump's height, weight, jump count, jab count
  (jumps 17 / 18: --jump-scale, below);
- Ultimate's own value (walk / run / dash, landing lags, jump squat): Ultimate changed these by
  design (walk / run x1.05 / x1.1 on every fighter, landing lag about 0.6x), so its value is the
  port's;
- ground friction: Ultimate's x 0.45 (Smash 4's are 0.45 - 0.57 of Ultimate's: Mario, Zelda, Pit,
  Robin), as every port so far;
- the move counts the game's common code reads: 263 jabs (attack_combo_max), 264 rapid jab
  (attack100_type), 268 jump type (aerial_type: normal 1, fly 2 = Pit's / Kirby's multi-jump).
  265 (side tilt count) is never set: the common side-tilt combo only repeated the first hit (Hero
  fix 16); a port with s3_combo_max > 1 needs its own loop (Hero's brave_s3_*), reported below.
--jump-scale A,B: full hop x A, short hop x B. Hero / Steve / Squirtle / Sephiroth used 0.82 / 0.9
("for Ultimate's faster full hop"); in the tables Smash 4's heights equal Ultimate's for 48 / 47 of
51 fighters, so 1,1 is the data's answer, and the default (user, for new ports); Hero / Steve / Squirtle /
Sephiroth keep 0.82,0.9 in their port.json.

Sizes (SIZE below; `sizes` re-applies only them to a fighter_param.bin, every other byte kept):
  python3 tools/ultimate_stats.py sizes FIGHTER_PARAM_PRC LABELS_CSV FIGHTER_PARAM_BIN OUT_BIN [NAME[=KIND] ...]
(no NAME: every Ultimate port of tools/extra_kinds.json whose fighter Ultimate has). The model's size in game is
fighter_param 44 `scale` x the model's own skeleton (the converter carries Ultimate's skeleton 1:1, roots at scale 1),
so the port's 44 is Ultimate's `scale` (the 57 fighters both games have: equal for 41, within 4 % for 13; only the
Miis differ, 1.0 / 1.15, whose models are built differently: Smash 4 sizes a Mii by fighter_param_etc's body table).
The other per-fighter sizes that follow it: 45 shield (Ultimate's x 0.88, the median Smash 4 / Ultimate ratio,
quartiles 0.84 - 0.95: APPROXIMATED), 48 tumble hitbox (= 45 x 0.35, 56 of 57 vanilla), 49 effect_scale and
185 freeze_size (= Ultimate's effect_scale / ice_radius for all 57). The ports up to fighter_sizes_v1 kept their
base's (Incineroar Bowser's scale 0.82 for Ultimate's 1.0).
Per-port overrides, in fighters/NAME/port.json "stats" (the user's call, or a word the port's moves can't use):
"override": {"INDEX": value} for MAP words (Incineroar, fighter_params_v2: 263 jab count 2, his moves are still
Bowser's, no Attack13), "size": {SIZE_NAMES name: value} for SIZE (Hero, fighter_params_v2: all five back to his
pre-fighter_sizes_v1 values). The stats step (--set / --size, passed by ultimate_port.py stats), `sizes` and
port_check P2 / P4 take them in place of Ultimate's.
"""
import argparse
import json
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import prc  # noqa: E402

GROUND_BRAKE = 0.45
COMBO_TYPE = {'fighter_combo_type_none': 0, 'fighter_combo_type_hit': 1, 'fighter_combo_type_succeed': 2,
              'fighter_combo_type_uniq_dance': 3}
# Smash 4 index: (Ultimate name, rule); rule: 'same' / 'ult' / 'brake' / 'full' / 'short' / a function
MAP = {
    1: ('walk_accel_mul', 'ult'), 2: ('walk_accel_add', 'ult'), 3: ('walk_speed_max', 'ult'),
    7: ('ground_brake', 'brake'), 8: ('dash_speed', 'ult'), 9: ('run_accel_mul', 'ult'),
    10: ('run_accel_add', 'ult'), 11: ('run_speed_max', 'ult'), 12: ('jump_squat_frame', 'ult'),
    13: ('jump_speed_x', 'same'), 14: ('jump_speed_x_mul', 'same'), 15: ('jump_speed_x_max', 'same'),
    16: ('jump_aerial_speed_x_mul', 'same'), 17: ('jump_y', 'full'), 18: ('mini_jump_y', 'short'),
    19: ('jump_aerial_y', 'same'), 20: ('air_accel_x_mul', 'same'), 21: ('air_accel_x_add', 'same'),
    22: ('air_speed_x_stable', 'ult'), 23: ('air_brake_x', 'same'), 24: ('air_accel_y', 'same'),
    25: ('air_speed_y_stable', 'same'), 26: ('air_brake_y', 'same'), 27: ('dive_speed_y', 'same'),
    28: ('landing_attack_air_frame_n', 'ult'), 29: ('landing_attack_air_frame_f', 'ult'),
    30: ('landing_attack_air_frame_b', 'ult'), 31: ('landing_attack_air_frame_hi', 'ult'),
    32: ('landing_attack_air_frame_lw', 'ult'), 33: ('weight', 'same'), 34: ('jump_count_max', 'same'),
    # v17 (Byleth: "jab 3 is inaccessible"): the jab chain's own values, all read by the common Attack status (ZSS's
    # func_270): 86 the presses the rapid jab needs (0x13000056; tested `presses >= it` once ENABLE_100 is on: a 0 left
    # from a base without a rapid jab sends jab 2 into the rapid jab at once, so the third jab never comes); Smash 4's
    # count is Ultimate's attack_100_enable_cnt + 1 for most fighters with both (Bayonetta, Captain Falcon, Corrin, Pit,
    # Greninja, Fox, Falco, Sheik, Mewtwo; +0 for Kirby, G&W, Little Mac, Palutena), 0 without a rapid jab; 81 / 82 the
    # jab 2 / 3 input windows (combo_attack_12_end / 13_end: equal in both games for 47 of 51); 262 the combo kind
    # (fighter_combo_type_none / hit / succeed / uniq_dance = 0 / 1 / 2 / 3: all 51 match)
    81: ('combo_attack_12_end', 'same'), 82: ('combo_attack_13_end', 'same'),
    86: ('attack_100_enable_cnt', 'rapid_count'),
    262: ('attack_combo_type', lambda v: COMBO_TYPE[v[1]]),
    263: ('attack_combo_max', 'same'),
    264: ('attack100_type', lambda v: 1 if v else 0),
    268: ('aerial_type', lambda v: 2 if v[1].endswith('_fly') else 1),
}
# The fighter's size (module doc): Smash 4 index: (Ultimate name, rule); written by the stats step and by `sizes`
SHIELD_RATIO = 0.88      # Smash 4 shield_radius / Ultimate's, median of the 57 fighters both games have (scale equal)
TUMBLE_RATIO = 0.35      # fighter_param 48 = 45 x 0.35 (56 of 57 vanilla fighters)
SIZE = {
    44: ('scale', 'same'),                 # decides the model's size in game (x the skeleton)
    45: ('shield_radius', 'shield'),
    48: ('shield_radius', 'tumble'),
    49: ('effect_scale', 'same'),
    185: ('ice_radius', 'same'),
}
SIZE_NAMES = {44: 'scale', 45: 'shield_radius', 48: 'tumble_attack_size', 49: 'effect_scale', 185: 'freeze_size'}
SIZE_INDEX = {v: k for k, v in SIZE_NAMES.items()}
# left as the base's, reported with Ultimate's value: not the same quantity in both games (median
# Smash 4 / Ultimate ratio over 51 fighters in brackets) or not checked yet
REPORT = {39: 'landing_frame', 40: 'landing_heavy_frame',
          265: 's3_combo_max', 266: 's4_combo_max', 267: 'lw4_combo_max'}


def entry(prc_path, labels_path, ult):
    labels = prc.load_labels(labels_path)
    table = prc.Prc(open(prc_path, 'rb').read(), labels).root['fighter_param_table']
    for e in table:
        if e['fighter_kind'][1] == 'fighter_kind_' + ult:
            return e
    sys.exit('no fighter_param entry for fighter_kind_%s' % ult)


def stats_override(name):
    """{index: value} of fighters/NAME/port.json "stats": {"override": {"INDEX": value}}: a MAP word the port can't take
    from Ultimate (Incineroar, fighter_params_v2: 263 jab count 2, Bowser's moves have no Attack13), {} without one"""
    p = os.path.join(os.path.dirname(HERE), 'fighters', name, 'port.json')
    try:
        d = json.load(open(p)).get('stats', {}).get('override', {})
    except (OSError, ValueError):
        return {}
    out = {}
    for k, v in d.items():
        if k.startswith('_'):
            continue
        if not k.isdigit() or int(k) not in MAP:
            sys.exit('%s: stats.override key %r is not a MAP index (%s)' % (p, k, ' '.join(map(str, sorted(MAP)))))
        out[int(k)] = v
    return out


def values(e, jump_scale=(1.0, 1.0), override=None):
    """{index: (value, Ultimate name, rule text)}; override: {index: value} (port.json stats.override,
    stats_override) in place of the rule's"""
    out = {}
    for i, (name, rule) in MAP.items():
        v = e[name]
        if override and i in override:
            out[i] = (override[i], name, 'port.json stats.override (Ultimate\'s %s)' % (v[1] if isinstance(v, tuple) else v,))
            continue
        if rule in ('same', 'ult'):
            val, how = v, 'Ultimate %s' % ('(same in both games)' if rule == 'same' else '(by design)')
        elif rule == 'brake':
            val, how = round(v * GROUND_BRAKE, 5), 'Ultimate x %.2f' % GROUND_BRAKE
        elif rule == 'full':
            val, how = round(v * jump_scale[0], 3), 'Ultimate x %g' % jump_scale[0]
        elif rule == 'rapid_count':
            val = int(v) + 1 if e['attack100_type'] else 0
            how = 'Ultimate + 1 (Smash 4\'s rapid jabs: one press more than Ultimate\'s for most)' if val else \
                'no rapid jab: 0'
        elif rule == 'short':
            val, how = round(v * jump_scale[1], 3), 'Ultimate x %g' % jump_scale[1]
        else:
            val, how = rule(v), 'from %r' % (v[1] if isinstance(v, tuple) else v,)
        if isinstance(val, float):
            val = round(val, 6)
        out[i] = (val, name, how)
    return out


def size_override(name):
    """{index: value} of fighters/NAME/port.json "stats": {"size": {...}} (keys: SIZE_NAMES names or indices; the
    user's per-port choice over Ultimate's: Hero's sizes are his pre-fighter_sizes_v1 ones), {} without one"""
    p = os.path.join(os.path.dirname(HERE), 'fighters', name, 'port.json')
    try:
        d = json.load(open(p)).get('stats', {}).get('size', {})
    except (OSError, ValueError):
        return {}
    out = {}
    for k, v in d.items():
        if k.startswith('_'):
            continue
        i = SIZE_INDEX.get(k, None) if not k.isdigit() else int(k)
        if i not in SIZE_NAMES:
            sys.exit('%s: stats.size key %r is not one of %s' % (p, k, ', '.join(SIZE_INDEX)))
        out[i] = float(v)
    return out


def size_values(e, override=None):
    """{index: (value, Ultimate name, rule text)} for the fighter's size (SIZE); override: {index: value} (the port's
    port.json stats.size, size_override) taken in place of Ultimate's"""
    out = {}
    override = override or {}
    for i, (name, rule) in SIZE.items():
        v = float(e[name])
        if i in override:
            ult = v * SHIELD_RATIO if rule == 'shield' else v * SHIELD_RATIO * TUMBLE_RATIO if rule == 'tumble' else v
            out[i] = (round(override[i], 4), name, 'port.json stats.size override (Ultimate\'s would be %g)' % round(ult, 4))
            continue
        if rule == 'same':
            val, how = v, 'Ultimate (same in both games)'
        elif rule == 'shield':
            val, how = v * SHIELD_RATIO, 'Ultimate x %.2f (APPROXIMATED: median ratio)' % SHIELD_RATIO
        else:
            val, how = v * SHIELD_RATIO * TUMBLE_RATIO, 'shield x %.2f' % TUMBLE_RATIO
        out[i] = (round(val, 4), name, how)
    return out


def ultimate_ports():
    """[(name, kind, Ultimate name)] of tools/extra_kinds.json's kinds (the Ultimate ports and others: a name Ultimate's
    fighter_param.prc lacks is skipped by apply_sizes)"""
    import port_sources
    d = json.load(open(os.path.join(HERE, 'extra_kinds.json')))
    return [(k['name'], int(k['kind'], 0), port_sources.ult_name(k['name'])) for k in d['kinds']]


def apply_sizes(prc_path, labels_path, fp_in, fp_out, ports=None, log=print):
    """Re-applicable: set only the SIZE words of each port's row in FP_IN (Ultimate's values), write FP_OUT; every
    other byte as it was. ports: [(name, kind, Ultimate name)] (default: ultimate_ports()). Returns
    [(name, kind, index, old, new)] for the words that changed."""
    import fighter_param as FP
    labels = prc.load_labels(labels_path)
    table = prc.Prc(open(prc_path, 'rb').read(), labels).root['fighter_param_table']
    ult = {e['fighter_kind'][1]: e for e in table}
    pf = FP.ParamFile(fp_in)
    rows = {e[0].v: e for e in pf.entries()}
    changed = []
    for name, kind, uname in (ports if ports is not None else ultimate_ports()):
        e = ult.get('fighter_kind_' + uname)
        if e is None or kind not in rows:
            log('%-10s skipped (%s)' % (name, 'not in Ultimate\'s fighter_param.prc' if e is None else
                                         'no row for kind 0x%X' % kind))
            continue
        row = rows[kind]
        for i, (v, uname_, how) in sorted(size_values(e, size_override(name)).items()):
            old = row[i].v
            new = struct.unpack('>f', struct.pack('>f', v))[0]
            if struct.pack('>f', old) != struct.pack('>f', new):
                row[i].v = new
                changed.append((name, kind, i, old, new))
            log('%-10s 0x%X %3d %-18s %8.4g -> %-8.4g %s' % (name, kind, i, SIZE_NAMES[i], old, new, how))
    out = pf.build()
    assert len(out) == len(pf.data)
    open(fp_out, 'wb').write(out)
    return changed


def warnings(e):
    w = []
    if e['s3_combo_max'] > 1:
        w.append('s3_combo_max %d: the side tilt has %d hits; Smash 4\'s combo (fighter_param 265) only '
                 'repeats the first: write the fighter\'s own loop (Hero fix 17, brave_s3_*)' % ((e['s3_combo_max'],) * 2))
    for k in ('s4_combo_max', 'lw4_combo_max'):
        if e[k] > 1:
            w.append('%s %d: a multi-press smash; not handled by the common code' % (k, e[k]))
    if e['aerial_type'][1].endswith('_fly'):
        w.append('aerial_type fly: multi-jump (268 = 2); the base needs multi-jump motions (Pit / Kirby)')
    return w


def main_sizes(argv):
    ap = argparse.ArgumentParser(prog='ultimate_stats.py sizes')
    for n in ('prc', 'labels', 'fighter_param', 'out'):
        ap.add_argument(n)
    ap.add_argument('ports', nargs='*', help='NAME or NAME=KIND (default: every kind in tools/extra_kinds.json)')
    a = ap.parse_args(argv)
    ports = None
    if a.ports:
        import port_sources
        known = {n: (n, k, u) for n, k, u in ultimate_ports()}
        ports = [(p.split('=')[0], int(p.split('=')[1], 0), port_sources.ult_name(p.split('=')[0])) if '=' in p
                 else known[p] for p in a.ports]
    ch = apply_sizes(a.prc, a.labels, a.fighter_param, a.out, ports)
    print('%d words changed' % len(ch))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'sizes':
        return main_sizes(sys.argv[2:])
    ap = argparse.ArgumentParser()
    for n in ('prc', 'labels', 'ult', 'fighter_param', 'out', 'kind'):
        ap.add_argument(n)
    ap.add_argument('--jump-scale', default='1,1')
    ap.add_argument('--json')
    ap.add_argument('--set', action='append', default=[], metavar='INDEX=VALUE',
                    help='a MAP word in place of Ultimate\'s (port.json stats.override; ultimate_port.py stats passes them)')
    ap.add_argument('--size', action='append', default=[], metavar='INDEX=VALUE',
                    help='a size word in place of Ultimate\'s (port.json stats.size; ultimate_port.py stats passes them)')
    a = ap.parse_args()
    e = entry(a.prc, a.labels, a.ult)
    js = tuple(float(x) for x in a.jump_scale.split(','))
    vals = values(e, js, {int(t.split('=')[0]): json.loads(t.split('=')[1]) for t in a.set})
    for i, (v, name, how) in sorted(vals.items()):
        print('%4d = %-10s %-28s %s' % (i, v, name, how))
    ov = {}
    for t in a.size:
        k, v = t.split('=')
        ov[SIZE_INDEX.get(k) or int(k)] = float(v)
    sizes = size_values(e, ov)
    for i, (v, name, how) in sorted(sizes.items()):
        print('%4d = %-10s %-28s %s (size)' % (i, v, name, how))
    for i, name in sorted(REPORT.items()):
        k = name.split()[0]
        print('%4d   (base kept) Ultimate %s = %s' % (i, name, e.get(k)))
    for w in warnings(e):
        print('NOTE:', w)
    kind = str(int(a.kind, 0))
    r = subprocess.run([sys.executable, os.path.join(HERE, 'fighter_param.py'), 'set', a.fighter_param, a.out, kind]
                       + ['%d=%s' % (i, v) for i, (v, _n, _h) in sorted(list(vals.items()) + list(sizes.items()))],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stdout + r.stderr)
    if a.json:
        json.dump({str(i): v for i, (v, _n, _h) in list(vals.items()) + list(sizes.items())}, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
