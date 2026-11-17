#!/usr/bin/env python3
"""Smash 4's param/ui/result_param.bin: the results scene's per-fighter framing (Byleth v17).

  python3 tools/result_param.py list FILE                       the fighters' entries (name, win1 - 5, ..., eye, to)
  python3 tools/result_param.py add FILE OUT NAME --like BASE [--win W1,W2,W3]
                                                                an entry for model name NAME, a copy of BASE's
  python3 tools/result_param.py port FILE OUT NAME --like BASE --base-skel VBN [--base-result PAC]
                                     --skel SKEL --wins DIR_OR_PAC [--replace]
                                                                a port's entry, made from its base's (the pipeline's
                                                                `result-param` step, tools/ultimate_port.py):
      the framing (eyex - toz, the MVP / team offsets) scaled by the port's head height over the base's (the
      `HeadN` / `Head` joint's mean height through the lose motions, --lose against the base's J02Lose in
      --base-result; without both, the joints' bind-pose heights; SKEL a model.vbn or Ultimate's model.nusktb), so the
      panel shows the port as it shows the base (the same picture, everything scaled about the floor); win1 - 3 the base's
      scaled by the port's win motions' lengths over the base's (WinN against J02WinN in the base's bodyresult
      main.pac; without it the port's length x WIN_RATIO, the vanilla median), win4 / win5 0 for a port with no
      fourth / fifth win motion; mvp_motion / team_motion / team_pos_scale_factor the base's. --replace: an
      existing entry for NAME is rewritten in place (a re-run), every other entry kept byte for byte.
  python3 tools/result_param.py measure SKEL | PAC | DIR | SKEL:LOSE ...   head heights / win lengths, as `port` reads them

The file is a generic param file (FF FF 00 00); its fighter group (61 entries in 1.1.7) holds one entry a fighter:
`name` (type 0x0A: the model folder's name reversed and XORed with "Smash" repeated), win1 - win5, mvp_motion,
mvp_motion_x / _z, team_motion, team_motion_x / _z, mvp_camera_x / _y / _z, team_pos_scale_factor, eyex / eyey / eyez,
tox / toy / toz (the field names: the scene's Xtal bindings registered at 0x030D37C4). eye / to frame the fighter in a
loser's panel; a model name with no entry gets the first one ("missing": every value 0), so its loser panel's camera
sits on its target and the panel is drawn empty (user, Byleth v16: "Byleth doesn't appear in the loss character windows";
every port of a new kind has no entry). port_check R2 result-param.
"""
import argparse
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

KEY = b'Smash'
FIELDS = ('name', 'win1', 'win2', 'win3', 'win4', 'win5', 'mvp_motion', 'mvp_motion_x', 'mvp_motion_z', 'team_motion',
          'team_motion_x', 'team_motion_z', 'mvp_camera_x', 'mvp_camera_y', 'mvp_camera_z', 'team_pos_scale_factor',
          'eyex', 'eyey', 'eyez', 'tox', 'toy', 'toz')


def code(name):
    """the name's 0x0A bytes (reversed, XOR "Smash"); its own inverse"""
    b = name.encode()[::-1] if isinstance(name, str) else name
    return bytes(c ^ KEY[i % len(KEY)] for i, c in enumerate(b))


def decode(raw):
    return bytes(c ^ KEY[i % len(KEY)] for i, c in enumerate(raw))[::-1].decode('latin1')


def _value(d, o):
    """(value, end) of the typed value at o"""
    t = d[o]
    if t == 0x0A:
        n = struct.unpack('>I', d[o + 1:o + 5])[0]
        return decode(d[o + 5:o + 5 + n]), o + 5 + n
    if t == 7:
        return struct.unpack('>f', d[o + 1:o + 5])[0], o + 5
    if t in (5, 6):
        return struct.unpack('>i', d[o + 1:o + 5])[0], o + 5
    raise ValueError('type 0x%02X at 0x%X' % (t, o))


def entries(d):
    """(group count offset, [(name, start, end, {field: value})]) of the fighter group"""
    starts = [m.start() for m in re.finditer(b'\x0a\x00\x00\x00', d)]
    if not starts:
        raise SystemExit('no fighter entries')
    g = starts[0] - 5
    assert d[g] == 0x20 and struct.unpack('>I', d[g + 1:g + 5])[0] == len(starts), 'the fighter group not found'
    out = []
    for s in starts:
        o, vals = s, {}
        for f in FIELDS:
            vals[f], o = _value(d, o)
        out.append((vals['name'], s, o, vals))
    return g, out


# the values that are lengths in the scene's space (scaled with the fighter's size); the rest are frames, motion numbers
# and the team spacing factor
POSITION = ('mvp_motion_x', 'mvp_motion_z', 'team_motion_x', 'team_motion_z', 'mvp_camera_x', 'mvp_camera_y',
            'mvp_camera_z', 'eyex', 'eyey', 'eyez', 'tox', 'toy', 'toz')
# win N / the base's J02WinN length, vanilla 1.1.7 (mario, koopa, reflet, zelda, szerosuit, mariod, pacman, link: 24
# poses, 0.80 - 1.00, mean 0.93): the median, for a base whose result motions aren't at hand (Steve on Pit)
WIN_RATIO = 0.957
HEAD = ('HeadN', 'Head')


def _skeleton(path):
    """[(name, parent index or None, hash or None, bind local 4x4)] of a model.vbn or an Ultimate model.nusktb"""
    sys.path.insert(0, HERE)
    import kirby_copy_motions as K
    if path.endswith('.nusktb'):
        names = [n for n, _p, _m in K.ult_skeleton(path)]
        return [(n, p if p is not None and 0 <= p < len(names) else None, None, m) for n, p, m in K.ult_skeleton(path)]
    return K.s4_skeleton(path)


def _head(bones):
    names = [b[0] for b in bones]
    for h in HEAD:
        if h in names:
            return names.index(h)
    raise SystemExit('no head joint (%s)' % ' / '.join(HEAD))


def _world_y(bones, i, local):
    """the height of joint i, local(j) giving each joint's local 4x4 (parents in any order)"""
    import numpy as np
    m = np.eye(4)
    while i is not None:
        m = local(i) @ m
        i = bones[i][1]
    return float(m[1, 3])


def head_height(path):
    """the bind-pose height of the head joint (HeadN, Ultimate's Head) of a model.vbn or an Ultimate model.nusktb"""
    bones = _skeleton(path)
    return _world_y(bones, _head(bones), lambda j: bones[j][3])


def lose_head(skel, motion):
    """the head joint's mean height through the lose motion (what a loser panel shows): SKEL with a bodyresult main.pac
    (its J02Lose.omo) or Ultimate's j02lose.nuanmb; None when the motion isn't there"""
    import numpy as np
    if not motion or not os.path.exists(motion):
        return None
    bones = _skeleton(skel)
    hi = _head(bones)
    sys.path.insert(0, HERE)
    if motion.endswith('.nuanmb'):
        import kirby_copy_motions as K
        tr, frames = K.tracks(motion)
        cache = {}

        def local(j, fr):
            n = bones[j][0]
            if n not in tr:
                return bones[j][3]
            if n not in cache:
                cache[n] = K.trs(*tr[n])
            return cache[n][fr]
        return float(np.mean([_world_y(bones, hi, lambda j: local(j, fr)) for fr in range(frames)]))
    import omo
    lose = [omo.Omo(d) for n, d in omo.pac_read(motion) if n.endswith('J02Lose.omo')]
    if not lose:
        return None
    o = lose[0]

    def local(j, fr):
        s = o.sample(bones[j][2], fr)
        return np.array(omo.trs(*s)) if s else bones[j][3]
    return float(np.mean([_world_y(bones, hi, lambda j: local(j, fr)) for fr in range(o.frames)]))


def win_lengths(path):
    """{N: frames} of the win motions: a bodyresult main.pac (J02WinN.omo) or Ultimate's motion/body/cNN folder
    (j02winN.nuanmb)"""
    out = {}
    if os.path.isdir(path):
        import ssbh_data_py as s
        for n in range(1, 6):
            f = os.path.join(path, 'j02win%d.nuanmb' % n)
            if os.path.exists(f):
                out[n] = int(round(s.anim_data.read_anim(f).final_frame_index)) + 1
        return out
    sys.path.insert(0, HERE)
    import omo
    for n, data in omo.pac_read(path):
        m = re.search(r'J02Win(\d)\.omo$', n)
        if m:
            out[int(m.group(1))] = omo.Omo(data).frames
    return out


def port_values(base_vals, scale, wins, base_wins=None):
    """the port's {field: value} from the base's: positions x scale, win N from its motions' lengths"""
    v = dict(base_vals)
    for f in POSITION:
        v[f] = round(base_vals[f] * scale, 3)
    for n in range(1, 6):
        f = 'win%d' % n
        if n not in wins:
            v[f] = 0.0
        elif base_wins and base_wins.get(n) and base_vals[f]:
            v[f] = float(round(base_vals[f] * wins[n] / base_wins[n]))
        else:
            v[f] = float(round(wins[n] * WIN_RATIO))
    return v


def encode(vals):
    """an entry's bytes: the name (0x0A) and every value with its type (5 / 6 int, 7 float), as FIELDS orders them"""
    out = bytearray(b'\x0a' + struct.pack('>I', len(vals['name'])) + code(vals['name']))
    for f in FIELDS[1:]:
        t, x = vals['_types'][f], vals[f]
        out += bytes([t]) + (struct.pack('>f', float(x)) if t == 7 else struct.pack('>i', int(x)))
    return bytes(out)


def types(d, start):
    """{field: type byte} of the entry at start"""
    o, out = start, {}
    for f in FIELDS:
        out[f] = d[o]
        o = _value(d, o)[1]
    return out


def set_entry(d, vals):
    """d with vals['name']'s entry rewritten (or added after the last one), every other entry byte for byte"""
    g, ents = entries(d)
    new = encode(vals)
    old = next((e for e in ents if e[0] == vals['name']), None)
    if old:
        return d[:old[1]] + new + d[old[2]:]
    end = ents[-1][2]
    out = bytearray(d[:end]) + new + d[end:]
    out[g + 1:g + 5] = struct.pack('>I', len(ents) + 1)
    return bytes(out)


def port(d, name, like, base_skel, skel, wins_src, base_result=None, replace=False, lose=None):
    """(new file, values, notes) for a port: its base's entry scaled (see the module's doc); lose: the port's lose
    motion (a bodyresult main.pac or Ultimate's j02lose.nuanmb)"""
    _g, ents = entries(d)
    if any(e[0] == name for e in ents) and not replace:
        raise SystemExit('%s: already there (--replace rewrites it)' % name)
    base = next((e for e in ents if e[0] == like), None)
    if base is None:
        raise SystemExit('%s: no entry' % like)
    lb, lp = lose_head(base_skel, base_result), lose_head(skel, lose)
    if lb and lp:                       # the loser panel shows the lose pose: the head's height in it
        hb, hp, how = lb, lp, 'the head in the lose motions'
    else:
        hb, hp, how = head_height(base_skel), head_height(skel), 'the head joints\' bind-pose heights'
    wins = win_lengths(wins_src)
    if not wins:
        raise SystemExit('%s: no win motions' % wins_src)
    bw = win_lengths(base_result) if base_result and os.path.exists(base_result) else None
    vals = port_values(base[3], hp / hb, wins, bw)
    vals['name'] = name
    vals['_types'] = types(d, base[1])
    notes = dict(base=like, scale=round(hp / hb, 4), head=round(hp, 2), base_head=round(hb, 2), how=how, wins=wins,
                 base_wins=bw, win_rule='base x length ratio' if bw else 'length x %.3f (no base motions)' % WIN_RATIO)
    return set_entry(d, vals), vals, notes


def add(d, name, like, win=None):
    g, ents = entries(d)
    if any(e[0] == name for e in ents):
        raise SystemExit('%s: already there' % name)
    base = next((e for e in ents if e[0] == like), None)
    if base is None:
        raise SystemExit('%s: no entry' % like)
    raw = bytearray(d[base[1]:base[2]])
    n = struct.unpack('>I', raw[1:5])[0]
    new = bytearray(b'\x0a' + struct.pack('>I', len(name)) + code(name)) + raw[5 + n:]
    if win:
        o = 1 + 4 + len(name)
        for w in win:
            assert new[o] == 7
            new[o + 1:o + 5] = struct.pack('>f', float(w))
            o += 5
    end = ents[-1][2]
    out = bytearray(d[:end]) + new + d[end:]
    out[g + 1:g + 5] = struct.pack('>I', len(ents) + 1)
    return bytes(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    li = sub.add_parser('list')
    li.add_argument('file')
    ad = sub.add_parser('add')
    ad.add_argument('file')
    ad.add_argument('out')
    ad.add_argument('name')
    ad.add_argument('--like', required=True)
    ad.add_argument('--win', help='win1,win2,win3 (the frames for the win poses; default the copied entry\'s)')
    po = sub.add_parser('port')
    po.add_argument('file')
    po.add_argument('out')
    po.add_argument('name')
    po.add_argument('--like', required=True, help='the base fighter\'s model name')
    po.add_argument('--base-skel', required=True, help='the base\'s model/body/c00/model.vbn')
    po.add_argument('--base-result', help='the base\'s motion/bodyresult/main.pac (its win motions\' lengths)')
    po.add_argument('--skel', required=True, help='the port\'s model.vbn or Ultimate model.nusktb')
    po.add_argument('--wins', required=True, help='the port\'s bodyresult main.pac or Ultimate motion/body/c00')
    po.add_argument('--lose', help='the port\'s lose motion (bodyresult main.pac or Ultimate j02lose.nuanmb): the scale '
                    'from the head\'s height in it against the base\'s J02Lose (--base-result), else bind poses')
    po.add_argument('--replace', action='store_true')
    me = sub.add_parser('measure')
    me.add_argument('paths', nargs='+')
    a = ap.parse_args()
    if a.cmd == 'measure':
        for p in a.paths:
            if ':' in p:                 # SKEL:LOSE (a main.pac or j02lose.nuanmb): the head through the lose motion
                sk, mo = p.split(':', 1)
                print('%s: lose head %.2f, bind head %.2f' % (p, lose_head(sk, mo), head_height(sk)))
            else:
                print('%s: %s' % (p, win_lengths(p) if p.endswith('.pac') or os.path.isdir(p) else 'head %.2f' % head_height(p)))
        return
    d = open(a.file, 'rb').read()
    if a.cmd == 'port':
        out, v, n = port(d, a.name, a.like, a.base_skel, a.skel, a.wins, a.base_result, a.replace, a.lose)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, 'wb').write(out)
        print('%s: entry %s from %s x %.4f (head %.2f / %.2f: %s), wins %s (%s): %s' % (
            a.out, a.name, a.like, n['scale'], n['head'], n['base_head'], n['how'], n['wins'], n['win_rule'],
            ' '.join('%s=%g' % (f, v[f]) for f in FIELDS[1:])))
        return
    if a.cmd == 'list':
        for name, _s, _e, v in entries(d)[1]:
            print('%-14s %s' % (name, ' '.join('%s=%g' % (f, v[f]) for f in FIELDS[1:])))
        return
    win = [float(x) for x in a.win.split(',')] if a.win else None
    out = add(d, a.name, a.like, win)
    open(a.out, 'wb').write(out)
    print('%s: entry %s (a copy of %s%s): %d -> %d bytes' % (a.out, a.name, a.like,
                                                          ', win %s' % a.win if a.win else '', len(d), len(out)))


if __name__ == '__main__':
    sys.exit(main())
