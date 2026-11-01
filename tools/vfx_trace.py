#!/usr/bin/env python3
"""Reads vfx_trace.bin, the record of Ultimate's own particle engine written by the OpenSmash-Ultimate mod
tools/opensmash/vfx_trace.cpp (docs/vfx-trace.md), and checks tools/fx_render.py against it.

  python3 tools/vfx_trace.py summary TRACE                       sets, emitters, instances, particles
  python3 tools/vfx_trace.py dump TRACE EMITTER [--set PART] [--particles]   an emitter frame by frame
  python3 tools/vfx_trace.py births TRACE NAME [--set PART]      births a frame: the engine vs fx_render
                                                                 (NAME: the port, fighters/NAME/port.json)
  python3 tools/vfx_trace.py json TRACE OUT.json                 everything, for other tools
"""
import argparse
import collections
import json
import os
import struct
import sys

HEAD = b'VFXTRC1\0'
# record payloads (vfx_trace.cpp's structs, x64 MSVC layout)
S_FMT = '<Q64s64sBB6x'                                  # 'S' an emitter's names
E_FMT = '<qQQQff4iIHH8f16f4f4f9f24f4x'                  # 'E' an emitter after its frame
P_FMT = '<Qii2I3f4f4f4f4f4f4f4f4f12f4x'                 # 'P' / 'B' a particle (each frame / at birth)
P_KEYS = ('pos', 'vec', 'vec2', 'scale', 'random', 'rot', 'col0', 'col1')


def read(path):
    """{'names': {data: (set, emitter, calc, follow)}, 'table': [512 x 4] or None, 'emitters': [...],
    'particles': [...], 'births': [...]} in file order"""
    d = open(path, 'rb').read()
    if d[:8] != HEAD:
        raise SystemExit('%s: not a vfx_trace file' % path)
    out = {'names': {}, 'table': None, 'emitters': [], 'particles': [], 'births': []}
    o = 16
    while o + 8 <= len(d):
        t, n = chr(d[o]), struct.unpack_from('<I', d, o + 4)[0]
        p = d[o + 8:o + 8 + n]
        o += 8 + n
        if len(p) < n:
            break                       # cut short (the game was stopped while writing)
        if t == 'S':
            data, st, em, calc, follow = struct.unpack(S_FMT, p)
            out['names'][data] = (st.split(b'\0')[0].decode('latin1'), em.split(b'\0')[0].decode('latin1'), calc, follow)
        elif t == 'T':
            v = struct.unpack('<2048f', p)
            out['table'] = [v[i:i + 4] for i in range(0, 2048, 4)]
        elif t == 'E':
            v = struct.unpack(E_FMT, p)
            out['emitters'].append({
                'clock': v[0], 'inst': v[1], 'data': v[2], 'set': v[3], 'time': v[4], 'time2': v[5],
                'emitted': v[6], 'used': v[7], 'slots': v[8], 'next': v[9], 'rng': v[10], 'vec_index': v[11],
                'timers': v[13:21], 'm': v[21:37], 'prev': v[37:41], 'move': v[41:45], 'anim': v[45:54],
                'setm': v[54:78]})
        elif t in 'PB':
            v = struct.unpack(P_FMT, p)
            r = {'inst': v[0], 'slot': v[1], 'number': v[2], 'id': v[3], 'birth': v[5], 'life': v[6], 'time': v[7]}
            for i, k in enumerate(P_KEYS):
                r[k] = v[8 + 4 * i:12 + 4 * i]
            r['m'] = v[40:52]
            (out['births'] if t == 'B' else out['particles']).append(r)
    return out


def instances(tr):
    """{inst: {'data', 'set', 'emitter', 'frames': [E ...], 'births': [B ...]}} (an instance address can be
    reused by a later effect: a new run starts when its time goes back)"""
    runs = collections.OrderedDict()
    last = {}
    for e in tr['emitters']:
        key = (e['inst'], last.get(e['inst'], (0, None))[0])
        prev = last.get(e['inst'])
        if prev and e['time'] < prev[1]['time']:
            key = (e['inst'], prev[0] + 1)
        last[e['inst']] = (key[1], e)
        st, em, calc, follow = tr['names'].get(e['data'], ('?', '?', 0, 0))
        runs.setdefault(key, {'inst': e['inst'], 'data': e['data'], 'set': st, 'emitter': em, 'calc': calc,
                              'follow': follow, 'frames': [], 'births': []})['frames'].append(e)
    for b in tr['births']:
        cands = [r for (i, _k), r in runs.items() if i == b['inst'] and r['frames'] and
                 r['frames'][0]['time'] - 1 <= b['time'] <= r['frames'][-1]['time'] + 1]
        if cands:
            cands[0]['births'].append(b)
    return runs


def summary(tr):
    runs = instances(tr)
    print('%d emitter frames, %d particle records, %d births, random table %s' % (
        len(tr['emitters']), len(tr['particles']), len(tr['births']), 'yes' if tr['table'] else 'no'))
    by = collections.defaultdict(list)
    for r in runs.values():
        by[(r['set'], r['emitter'])].append(r)
    for (st, em), rs in sorted(by.items()):
        print('%-34s %-20s %3d runs, frames %s, births %s' % (st, em, len(rs), [len(r['frames']) for r in rs][:6],
                                                              [len(r['births']) for r in rs][:6]))


def dump(tr, emitter, set_part, show_particles):
    runs = [r for r in instances(tr).values() if r['emitter'] == emitter and set_part.lower() in r['set'].lower()]
    parts = collections.defaultdict(list)
    if show_particles:
        for p in tr['particles']:
            parts[(p['inst'], round(p['time'], 3))].append(p)
    for r in runs:
        print('== %s / %s  instance 0x%x  calc %d follow %d' % (r['set'], r['emitter'], r['inst'], r['calc'], r['follow']))
        for e in r['frames']:
            m = e['m']
            print('  t %6.2f emitted %3d used %3d rng %08x  T (%.3f %.3f %.3f)  move (%.3f %.3f %.3f)' % (
                e['time'], e['emitted'], e['used'], e['rng'], m[12], m[13], m[14], *e['move'][:3]))
            for p in parts.get((e['inst'], round(e['time'], 3)), []):
                print('     #%-3d age %5.2f/%-5.1f pos (%.3f %.3f %.3f) vec (%.3f %.3f %.3f) scale (%.3f %.3f) rot (%.3f %.3f %.3f)' % (
                    p['slot'], p['time'] - p['birth'], p['life'], *p['pos'][:3], *p['vec'][:3], *p['scale'][:2], *p['rot'][:3]))
        for b in r['births']:
            print('  born t %6.2f #%-3d n%-2d pos (%.3f %.3f %.3f) vec (%.3f %.3f %.3f) life %.1f' % (
                b['time'], b['slot'], b['number'], *b['pos'][:3], *b['vec'][:3], b['life']))


def births(tr, name, set_part):
    """particles born each frame per emitter run, against fx_render's Ultimate side for the same emitter
    (identity call: the emitter's own movement only)"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import numpy as np
    import fx_render as F
    import port_sources
    import vfxb
    cfg = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'fighters', name, 'port.json')))
    eff = vfxb.Eff(port_sources.load().eff(cfg['ult']))
    images, (names, _x), prims = eff.images(), eff.textures(), eff.primitives()
    cache = {}
    for r in instances(tr).values():
        if set_part.lower() not in r['set'].lower() or r['set'] not in eff.sets:
            continue
        si = eff.sets.index(r['set'])
        if si not in cache:
            cache[si] = {em.name: em for em in F.ult_emitters(eff, si, images, names, prims)}
        em = cache[si].get(r['emitter'])
        # an 'E' record is written after the frame, its time already advanced: the run's first frame ran at
        # the first record's time less one step (a particle's birth time is the time it was born at)
        fr = r['frames']
        t0 = fr[0]['time'] - (fr[1]['time'] - fr[0]['time'] if len(fr) > 1 else 1.0)
        game = collections.Counter(int(round(b['time'] - t0)) for b in r['births'])
        n = int(round(fr[-1]['time'] - t0))
        line = [game.get(k, 0) for k in range(n)]
        if em is None:
            print('%-30s %-16s engine %s (not drawn by fx_render)' % (r['set'], r['emitter'], line[:24]))
            continue
        sim = F.simulate(em, (0, np.eye(4), 1.0, None), range(0, n), births_only=True)
        ours = [sim.get(k, 0) for k in range(n)]
        ok = 'same' if ours == line else 'DIFFERENT'
        if ok != 'same':
            # the move's script turned the effect off (EFFECT_OFF_KIND: emission stops, the particles live on),
            # which fx_render's bare emitter doesn't know: the same up to the engine's last emission, nothing after
            last = max([k for k, v in enumerate(line) if v] or [-1])
            if ours[:last + 1] == line[:last + 1] and not any(line[last + 1:]):
                ok = 'same until the engine stopped emitting after frame %d (turned off by the script?)' % last
        print('%-30s %-16s %s\n    engine %s\n    ours   %s' % (r['set'], r['emitter'], ok, line[:24], ours[:24]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=('summary', 'dump', 'births', 'json'))
    ap.add_argument('trace')
    ap.add_argument('arg', nargs='?')
    ap.add_argument('--set', default='')
    ap.add_argument('--particles', action='store_true')
    a = ap.parse_args()
    tr = read(a.trace)
    if a.cmd == 'summary':
        summary(tr)
    elif a.cmd == 'dump':
        dump(tr, a.arg, a.set, a.particles)
    elif a.cmd == 'births':
        births(tr, a.arg, a.set)
    else:
        tr['names'] = {'0x%x' % k: v for k, v in tr['names'].items()}
        json.dump(tr, open(a.arg, 'w'))


if __name__ == '__main__':
    main()
