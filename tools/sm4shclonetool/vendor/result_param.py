"""param/ui/result_param.bin: the results scene's per-fighter framing (the loser panel camera eye / target and the
win poses' frames), keyed by the fighter's model (folder) name: read and add entries.

Adapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; the tool
sets the code addresses itself, see its README "The executable")."""
import argparse
import os
import re
import struct
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = b'Smash'
FIELDS = ('name', 'win1', 'win2', 'win3', 'win4', 'win5', 'mvp_motion', 'mvp_motion_x', 'mvp_motion_z', 'team_motion', 'team_motion_x', 'team_motion_z', 'mvp_camera_x', 'mvp_camera_y', 'mvp_camera_z', 'team_pos_scale_factor', 'eyex', 'eyey', 'eyez', 'tox', 'toy', 'toz')

def code(name):
    b = name.encode()[::-1] if isinstance(name, str) else name
    return bytes((c ^ KEY[i % len(KEY)] for i, c in enumerate(b)))

def decode(raw):
    return bytes((c ^ KEY[i % len(KEY)] for i, c in enumerate(raw)))[::-1].decode('latin1')

def _value(d, o):
    t = d[o]
    if t == 10:
        n = struct.unpack('>I', d[o + 1:o + 5])[0]
        return (decode(d[o + 5:o + 5 + n]), o + 5 + n)
    if t == 7:
        return (struct.unpack('>f', d[o + 1:o + 5])[0], o + 5)
    if t in (5, 6):
        return (struct.unpack('>i', d[o + 1:o + 5])[0], o + 5)
    raise ValueError('type 0x%02X at 0x%X' % (t, o))

def entries(d):
    starts = [m.start() for m in re.finditer(b'\n\x00\x00\x00', d)]
    if not starts:
        raise SystemExit('no fighter entries')
    g = starts[0] - 5
    assert d[g] == 32 and struct.unpack('>I', d[g + 1:g + 5])[0] == len(starts), 'the fighter group not found'
    out = []
    for s in starts:
        o, vals = (s, {})
        for f in FIELDS:
            vals[f], o = _value(d, o)
        out.append((vals['name'], s, o, vals))
    return (g, out)
POSITION = ('mvp_motion_x', 'mvp_motion_z', 'team_motion_x', 'team_motion_z', 'mvp_camera_x', 'mvp_camera_y', 'mvp_camera_z', 'eyex', 'eyey', 'eyez', 'tox', 'toy', 'toz')
WIN_RATIO = 0.957
HEAD = ('HeadN', 'Head')

def _skeleton(path):
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
    import numpy as np
    m = np.eye(4)
    while i is not None:
        m = local(i) @ m
        i = bones[i][1]
    return float(m[1, 3])

def head_height(path):
    bones = _skeleton(path)
    return _world_y(bones, _head(bones), lambda j: bones[j][3])

def lose_head(skel, motion):
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
        m = re.search('J02Win(\\d)\\.omo$', n)
        if m:
            out[int(m.group(1))] = omo.Omo(data).frames
    return out

def port_values(base_vals, scale, wins, base_wins=None):
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
    out = bytearray(b'\n' + struct.pack('>I', len(vals['name'])) + code(vals['name']))
    for f in FIELDS[1:]:
        t, x = (vals['_types'][f], vals[f])
        out += bytes([t]) + (struct.pack('>f', float(x)) if t == 7 else struct.pack('>i', int(x)))
    return bytes(out)

def types(d, start):
    o, out = (start, {})
    for f in FIELDS:
        out[f] = d[o]
        o = _value(d, o)[1]
    return out

def set_entry(d, vals):
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
    _g, ents = entries(d)
    if any((e[0] == name for e in ents)) and (not replace):
        raise SystemExit('%s: already there (--replace rewrites it)' % name)
    base = next((e for e in ents if e[0] == like), None)
    if base is None:
        raise SystemExit('%s: no entry' % like)
    lb, lp = (lose_head(base_skel, base_result), lose_head(skel, lose))
    if lb and lp:
        hb, hp, how = (lb, lp, 'the head in the lose motions')
    else:
        hb, hp, how = (head_height(base_skel), head_height(skel), "the head joints' bind-pose heights")
    wins = win_lengths(wins_src)
    if not wins:
        raise SystemExit('%s: no win motions' % wins_src)
    bw = win_lengths(base_result) if base_result and os.path.exists(base_result) else None
    vals = port_values(base[3], hp / hb, wins, bw)
    vals['name'] = name
    vals['_types'] = types(d, base[1])
    notes = dict(base=like, scale=round(hp / hb, 4), head=round(hp, 2), base_head=round(hb, 2), how=how, wins=wins, base_wins=bw, win_rule='base x length ratio' if bw else 'length x %.3f (no base motions)' % WIN_RATIO)
    return (set_entry(d, vals), vals, notes)

def add(d, name, like, win=None):
    g, ents = entries(d)
    if any((e[0] == name for e in ents)):
        raise SystemExit('%s: already there' % name)
    base = next((e for e in ents if e[0] == like), None)
    if base is None:
        raise SystemExit('%s: no entry' % like)
    raw = bytearray(d[base[1]:base[2]])
    n = struct.unpack('>I', raw[1:5])[0]
    new = bytearray(b'\n' + struct.pack('>I', len(name)) + code(name)) + raw[5 + n:]
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
