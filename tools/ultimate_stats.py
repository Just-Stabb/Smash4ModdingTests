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
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import prc  # noqa: E402

GROUND_BRAKE = 0.45
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
    263: ('attack_combo_max', 'same'),
    264: ('attack100_type', lambda v: 1 if v else 0),
    268: ('aerial_type', lambda v: 2 if v[1].endswith('_fly') else 1),
}
# left as the base's, reported with Ultimate's value: not the same quantity in both games (median
# Smash 4 / Ultimate ratio over 51 fighters in brackets) or not checked yet
REPORT = {39: 'landing_frame', 40: 'landing_heavy_frame', 44: 'scale', 45: 'shield_radius (x0.88)',
          265: 's3_combo_max', 266: 's4_combo_max', 267: 'lw4_combo_max'}


def entry(prc_path, labels_path, ult):
    labels = prc.load_labels(labels_path)
    table = prc.Prc(open(prc_path, 'rb').read(), labels).root['fighter_param_table']
    for e in table:
        if e['fighter_kind'][1] == 'fighter_kind_' + ult:
            return e
    sys.exit('no fighter_param entry for fighter_kind_%s' % ult)


def values(e, jump_scale=(1.0, 1.0)):
    """{index: (value, Ultimate name, rule text)}"""
    out = {}
    for i, (name, rule) in MAP.items():
        v = e[name]
        if rule in ('same', 'ult'):
            val, how = v, 'Ultimate %s' % ('(same in both games)' if rule == 'same' else '(by design)')
        elif rule == 'brake':
            val, how = round(v * GROUND_BRAKE, 5), 'Ultimate x %.2f' % GROUND_BRAKE
        elif rule == 'full':
            val, how = round(v * jump_scale[0], 3), 'Ultimate x %g' % jump_scale[0]
        elif rule == 'short':
            val, how = round(v * jump_scale[1], 3), 'Ultimate x %g' % jump_scale[1]
        else:
            val, how = rule(v), 'from %r' % (v[1] if isinstance(v, tuple) else v,)
        if isinstance(val, float):
            val = round(val, 6)
        out[i] = (val, name, how)
    return out


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


def main():
    ap = argparse.ArgumentParser()
    for n in ('prc', 'labels', 'ult', 'fighter_param', 'out', 'kind'):
        ap.add_argument(n)
    ap.add_argument('--jump-scale', default='1,1')
    ap.add_argument('--json')
    a = ap.parse_args()
    e = entry(a.prc, a.labels, a.ult)
    js = tuple(float(x) for x in a.jump_scale.split(','))
    vals = values(e, js)
    for i, (v, name, how) in sorted(vals.items()):
        print('%4d = %-10s %-28s %s' % (i, v, name, how))
    for i, name in sorted(REPORT.items()):
        k = name.split()[0]
        print('%4d   (base kept) Ultimate %s = %s' % (i, name, e.get(k)))
    for w in warnings(e):
        print('NOTE:', w)
    kind = str(int(a.kind, 0))
    r = subprocess.run([sys.executable, os.path.join(HERE, 'fighter_param.py'), 'set', a.fighter_param, a.out, kind]
                       + ['%d=%s' % (i, v) for i, (v, _n, _h) in sorted(vals.items())], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stdout + r.stderr)
    if a.json:
        json.dump({str(i): v for i, (v, _n, _h) in vals.items()}, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
