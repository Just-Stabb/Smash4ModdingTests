#!/usr/bin/env python3
"""Smash 4's param/ui/result_param.bin: the results scene's per-fighter framing (Byleth v17).

  python3 tools/result_param.py list FILE                       the fighters' entries (name, win1 - 5, ..., eye, to)
  python3 tools/result_param.py add FILE OUT NAME --like BASE [--win W1,W2,W3]
                                                                an entry for model name NAME, a copy of BASE's

The file is a generic param file (FF FF 00 00); its fighter group (61 entries in 1.1.7) holds one entry a fighter:
`name` (type 0x0A: the model folder's name reversed and XORed with "Smash" repeated), win1 - win5, mvp_motion,
mvp_motion_x / _z, team_motion, team_motion_x / _z, mvp_camera_x / _y / _z, team_pos_scale_factor, eyex / eyey / eyez,
tox / toy / toz (the field names: the scene's Xtal bindings registered at 0x030D37C4). eye / to frame the fighter in a
loser's panel; a model name with no entry gets the first one ("missing": every value 0), so its loser panel's camera
sits on its target and the panel is drawn empty (user, Byleth v16: "Byleth doesn't appear in the loss character windows";
every port of a new kind has no entry). port_check R2 result-param.
"""
import argparse
import re
import struct
import sys

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
    a = ap.parse_args()
    d = open(a.file, 'rb').read()
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
