#!/usr/bin/env python3
"""Ultimate's "carry the hit fighter to a point" hits (angle 368 + AttackModule::set_vec_target_pos) for Smash 4 ports.

  python3 tools/vec_target.py scan DUMP_DIR [--json OUT]       every set_vec_target_pos (and 367 / 368 hitbox) of a fighter
  python3 tools/vec_target.py msc NAME DUMP_DIR [--status Script=0x33 ...] [--mask-var 0x0F00030E] [--centre 8]
          [--skip Script ...] [--out FILE.c]                      the MSC pull for the fighter's per-frame hook

DUMP_DIR: a fighter's smashline dump folder (lua2cpp_<name>/<name>, or SSBU-Dumped-Scripts smashline/<name>/<name>);
--vec-targets of tools/ultimate_acmd.py writes the same entries for the scripts it translates.

**What Ultimate does.** `ATTACK(..., angle 368, ...)` then `AttackModule::set_vec_target_pos(id, bone, Vector2f{x, y},
frames, false)` (Sephiroth's `FighterSpecializer_Edge::set_vec_target_pos` the same without the bool): a fighter that
hitbox hits is carried to the bone + (x forward, y up) over `frames` frames (Sephiroth's up tilt: lifted from the floor
into the sword, (2, 45) from his top in 5 frames, for the frame-20 hits). **Smash 4 has no such field**: its special
angles 365 - 367 take the victim along with the attacker (365) or with the hitbox's own motion (366, 367: the hit
info's +0x20 vector = the attack slot's +0xBC / +0xC0, the hitbox's per-frame movement, 0x02C17BC0; the victim's
damage energy eases its speed to it over common int 0x12000103 frames, 0x02E7C030 / 0x02E845B0), and 366 only off the
ground (0x02C25CD8: the victim's situation, StatusModule vt +0xDC). The converter writes 368 as 366 (port_check S4).

**The method** (Sephiroth's up tilt, test 151, `edge_hi3_pull`, which the user confirmed works): from the fighter's
per-frame MSC hook, while the move's status runs, every other fighter in hitstop or hitstun within a box around the
hitboxes is marked on the hit frame and the next one, and each marked one is moved, every frame the attacker is out
of hitlag, a 1 / (end - frame) part of the way to his position + (x forward, y - centre up) until end = hit frame +
frames (so it arrives on the last frame), its stage collision the air's. The position / hitstun variables of
tools/position_vars_cave.py (player slots 1-8: 0x0F000020 + 4s position, 0x0F000058 + 8s hitstun / + 3 hitstop) do the
work. Generated from the dump:
- the target y: Ultimate's y - centre (8 by default: Ultimate's point is where the victim's body goes, Smash 4's
  position is its feet; Sephiroth's hand-made up tilt has 45 -> 37);
- the box: the frame's 368 hitboxes (on `top`): forward centre their mean, half width their reach + size + 8, height
  their mean y - size - 14 to + size + 7 (test 151's box for the up tilt: 7 +- 15, -10 to 20). A hitbox on another
  bone (a sword's tip: Byleth's Sword of the Creator) is not placed: the box is then around the target, 30 wide and
  from the floor to the target (APPROXIMATED, said in the output);
- frames: the first hitbox's of that frame (the up tilt's ID 0, 5).
Every move that does this needs it (port_check S10 vec-target): the generated function's comments carry
`vec_target: SCRIPT`; a move done by hand is listed in port.json `vec_target.hand_made` (Sephiroth's).
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ultimate_acmd as UA  # noqa: E402

# Smash 4 status of a common move (reference/msc-note-sheet/Actions_Fighters.csv); a special's is the port's own (--status)
STATUS = {'Attack11': 0x25, 'Attack12': 0x25, 'Attack13': 0x25, 'AttackDash': 0x27, 'AttackS3': 0x28, 'AttackHi3': 0x29,
          'AttackLw3': 0x2A, 'AttackS4': 0x2D, 'AttackLw4': 0x30, 'AttackHi4': 0x33, 'AttackAirN': 0x34,
          'AttackAirF': 0x34, 'AttackAirB': 0x34, 'AttackAirHi': 0x34, 'AttackAirLw': 0x34}
CENTRE = 8.0
MARGIN_X, MARGIN_LO, MARGIN_HI = 8.0, 14.0, 7.0


class _Scan(UA.Translator):
    """the converter's parser, bones not needed"""
    def __init__(self):
        super().__init__({})
        self.angles = []

    def bone(self, name):
        return 0

    def call(self, name, a, raw):
        try:
            return super().call(name, a, raw)
        except (KeyError, ValueError, IndexError):     # a call the converter has no table entry for (a final's ABS)
            self.skip(name)
            return []

    def attack(self, a):
        if int(a[5]) in (365, 366, 367, 368):
            self.angles.append((self.frame, int(a[1]), int(a[5])))
        return super().attack(a)


def scan(dump):
    """{script: {'targets': [...], 'angles': [(frame, id, angle)]}} for every game script with a 365-368 hitbox or a
    set_vec_target_pos"""
    out = {}
    for path in sorted(glob.glob(os.path.join(dump, '*.txt'))):
        src = os.path.splitext(os.path.basename(path))[0]
        body = UA.functions(open(path, encoding='utf-8', errors='replace').read()).get('game_' + src.lower())
        if body is None:
            continue
        t = _Scan()
        try:
            t.script(body)
        except Exception as e:      # noqa: BLE001 (a script the converter can't parse: reported, not hidden)
            out[src] = {'error': str(e), 'targets': [], 'angles': []}
            continue
        if t.vec_targets or t.angles:
            out[src] = {'targets': t.vec_targets, 'angles': t.angles}
    return out


def _fwd(h):
    zs = [h['z']] + ([h['z2']] if isinstance(h.get('z2'), (int, float)) else [])
    return sum(zs) / len(zs), max(zs)


def segments(targets, centre=CENTRE):
    """one segment a frame that sets targets: frame, end, target (x, y feet), box, notes"""
    by = {}
    for t in targets:
        by.setdefault(t['frame'], []).append(t)
    out = []
    for fr in sorted(by):
        ts = by[fr]
        first = ts[0]
        notes = []
        if first['bone'] != 'top':
            notes.append('target on %s, taken from his top (APPROXIMATED)' % first['bone'])
        hbs = [t['hitbox'] for t in ts if t.get('hitbox') and t['hitbox']['bone'] == 'top']
        if hbs:
            cs = [_fwd(h)[0] for h in hbs]
            c = sum(cs) / len(cs)
            reach = max(_fwd(h)[1] for h in hbs) - c
            size = max(h['size'] for h in hbs)
            yc = sum(h['y'] for h in hbs) / len(hbs)
            box = (round(c), round(reach + size + MARGIN_X), round(yc - size - MARGIN_LO), round(yc + size + MARGIN_HI))
        else:
            box = (round(first['x']), 15, -10, round(first['y'] - centre + 10))
            notes.append('hitboxes on %s: the box is around the target (APPROXIMATED)' % (
                ', '.join(sorted({t['hitbox']['bone'] for t in ts if t.get('hitbox')})) or '?'))
        out.append({'frame': fr, 'end': fr + first['frames'], 'x': first['x'], 'y': first['y'] - centre,
                    'ult': [(t['id'], t['bone'], t['x'], t['y'], t['frames']) for t in ts], 'box': box, 'notes': notes})
    return out


def _f(v):
    return ('%.4f' % v).rstrip('0').rstrip('.') + ('.0f' if float(v).is_integer() else 'f')


def msc(name, script, status, segs, mask_var):
    """MSC-C for one move (edge_hi3_pull's method, fighters/edge/edge.c)"""
    fn = '%s_vt_%s' % (name, script.lower())
    lines = ['// vec_target: %s (status 0x%X). Ultimate\'s set_vec_target_pos (tools/vec_target.py, generated):' % (script, status)]
    for s in segs:
        lines.append('//   frame %g: %s -> feet (%g, %g) by frame %g; box %d +- %d forward, %d to %d up%s' % (
            s['frame'], '; '.join('ID %d %s (%g, %g) %d frames' % u for u in s['ult']), s['x'], s['y'], s['end'],
            s['box'][0], s['box'][1], s['box'][2], s['box'][3], ('; ' + '; '.join(s['notes'])) if s['notes'] else ''))
    lines += ['void %s()' % fn, '{', '    float f;', '    float x;', '    float y;', '    float tx;', '    float ty;',
              '    float k;', '    float lr;', '    float end;', '    float bx;', '    float bw;', '    float blo;',
              '    float bhi;', '    float mark;', '    int s;', '    int bit;', '    int mask;',
              '    if (global4 != 0x%X)' % status, '    {', '        return;', '    }',
              '    f = MotionModuleF(0x1);',
              '    if (f < %s)' % _f(segs[0]['frame']), '    {', '        WorkModule(0, 0.0f, 0x%08x);' % mask_var,
              '        return;', '    }']
    # the latest segment begun
    for i, s in enumerate(reversed(segs)):
        head = 'if' if i == 0 else 'else if'
        cond = '    %s (f >= %s)' % (head, _f(s['frame'])) if i < len(segs) - 1 else '    else'
        lines += [cond, '    {',
                  '        end = %s;' % _f(s['end']), '        tx = %s;' % _f(s['x']), '        ty = %s;' % _f(s['y']),
                  '        mark = %s;' % _f(s['frame'] + 2), '        bx = %s;' % _f(s['box'][0]),
                  '        bw = %s;' % _f(s['box'][1]), '        blo = %s;' % _f(s['box'][2]),
                  '        bhi = %s;' % _f(s['box'][3]), '    }']
    lines += ['    if (f >= end)', '    {', '        return;', '    }',
              '    mask = (int)WorkModuleF(0, 0x%08x);' % mask_var,
              '    lr = PostureModuleF(0);',
              '    tx = PostureModuleF(0x1) + tx * lr;',
              '    ty = PostureModuleF(0x2) + ty;',
              '    k = 1.0f / (end - f);',
              '    s = 0;', '    bit = 0x1;', '    while (s < 0x8)', '    {',
              '        x = WorkModuleF(0, 0x0f000020 + 0x4 * s);',
              '        y = WorkModuleF(0, 0x0f000021 + 0x4 * s);',
              '        if (WorkModuleF(0, 0x0f000023 + 0x4 * s) != 0.0f && (x != PostureModuleF(0x1) || y != PostureModuleF(0x2)))',
              '        {',
              '            if (f < mark && (mask / bit) - (mask / bit / 0x2) * 0x2 == 0',
              '                && (WorkModuleF(0, 0x0f00005b + 0x8 * s) > 0.0f || WorkModuleF(0, 0x0f000058 + 0x8 * s) > 0.0f)',
              '                && func_13(x - PostureModuleF(0x1) - bx * lr) < bw && y - PostureModuleF(0x2) > blo',
              '                && y - PostureModuleF(0x2) < bhi)',
              '            {', '                mask = mask + bit;', '            }',
              '            if ((mask / bit) - (mask / bit / 0x2) * 0x2 == 0x1 && WorkModuleF(0, 0x0f000043) == 0.0f)',
              '            {',
              '                WorkModule(0, x + (tx - x) * k, 0x0f000020 + 0x4 * s);',
              '                WorkModule(0, y + (ty - y) * k, 0x0f000021 + 0x4 * s);',
              '                WorkModule(0, 5.0f, 0x0f0000a0 + 0x8 * (s + 0x3) + 0x6);',
              '            }', '        }', '        s = s + 1;', '        bit = bit * 0x2;', '    }',
              '    WorkModule(0, (float)mask, 0x%08x);' % mask_var, '}']
    return fn, '\n'.join(lines)


def build(name, dump, status=None, skip=(), mask_var=0x0F00030E, centre=CENTRE):
    """(C source, [function names], [scripts]) for every set_vec_target_pos move of the dump not skipped"""
    status = dict(status or {})
    out, fns, scripts = ['// %s: Ultimate\'s set_vec_target_pos moves (tools/vec_target.py msc; call each from the '
                         'per-frame hook, as edge_hi3_pull)' % name], [], []
    for src, v in scan(dump).items():
        if not v['targets'] or src in skip:
            continue
        st = status.get(src, STATUS.get(src))
        if st is None:
            raise SystemExit('%s: no Smash 4 status for %s (--status %s=0x...)' % (name, src, src))
        fn, code = msc(name, src, st, segments(v['targets'], centre), mask_var)
        out.append(code)
        fns.append(fn)
        scripts.append(src)
    return '\n\n'.join(out) + '\n', fns, scripts


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('scan')
    p.add_argument('dump')
    p.add_argument('--json')
    p = sub.add_parser('msc')
    p.add_argument('name')
    p.add_argument('dump')
    p.add_argument('--status', action='append', default=[], metavar='SCRIPT=0xKIND')
    p.add_argument('--skip', action='append', default=[])
    p.add_argument('--mask-var', default='0x0F00030E', help='a free per-object float variable (VAR_n, 0x0F000300 + n) '
                   'for the marked fighters\' bits (Sephiroth uses VAR_14 for his up tilt\'s)')
    p.add_argument('--centre', type=float, default=CENTRE)
    p.add_argument('--out')
    a = ap.parse_args()
    if a.cmd == 'scan':
        res = scan(a.dump)
        for src, v in res.items():
            for t in v['targets']:
                h = t['hitbox'] or {}
                print('%-14s frame %-4g ID %d -> %s (%g, %g) over %d frames; hitbox %s angle %s size %s at (%s, %s)%s' % (
                    src, t['frame'], t['id'], t['bone'], t['x'], t['y'], t['frames'], h.get('bone'), h.get('angle'),
                    h.get('size'), h.get('z'), h.get('y'), ' G only' if h.get('situation') == 1 else ''))
            ang = sorted({an for _f, _i, an in v['angles']})
            if ang and not v['targets']:
                print('%-14s angles %s (no target point)' % (src, ', '.join(map(str, ang))))
        if a.json:
            json.dump(res, open(a.json, 'w'), indent=1)
        return
    status = {k: int(v, 0) for k, v in (s.split('=') for s in a.status)}
    code, fns, scripts = build(a.name, a.dump, status, a.skip, int(a.mask_var, 0), a.centre)
    if a.out:
        open(a.out, 'w').write(code)
        print('%s: %s (%s)' % (a.out, ', '.join(fns), ', '.join(scripts)))
    else:
        sys.stdout.write(code)


if __name__ == '__main__':
    main()
