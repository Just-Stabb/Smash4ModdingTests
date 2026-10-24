#!/usr/bin/env python3
"""Ultimate's universal effects (sys_*) -> Smash 4 common effect ids (bank 0x100), by matching the
two games' effect scripts of the same fighters and moves.

  python3 tools/ultimate_sys_effect_map.py DUMPS VANILLA OUT.json [FIGHTER ...] [--common EFC PTCL]

DUMPS: SSBU-Dumped-Scripts' smashline folder (lua2cpp_<fighter>/<fighter>/*.txt); VANILLA: Smash 4's
fighter folder (<fighter>/script/animcmd/body/effect.bin). For every effect_<move> function and the
Smash 4 effect script of the same name, each sys_* call is paired with the common-bank commands
within a frame of it; a name's id is the one it lands on most. Also prints, per Ultimate macro, the
Smash 4 commands it matched (the basis of ultimate_acmd.py's EFFECT_MACROS).

With --common (Smash 4's effect/common/common.010d0000.efc and .ptcl), a name that matches a common
entry's emitter set or model by name (sys_h_smoke_a -> PtcCommonHorizontalSmokeA, sys_atk_smoke ->
PtcCommonAttackSmoke: ABBREV expands the parts) takes that entry (the one of them it matched most in
the scripts, if several), whatever the frame matching found; the rest keep the frame matching's
(e.g. sys_attack_speedline, sys_counter_flash: no common effect of that name).

OVERRIDES fixes names whose top match is another effect that plays with them on the same frame.
"""
import collections
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

FIGHTERS = ('mario', 'zelda', 'marth', 'link', 'captain', 'fox', 'samus', 'kirby', 'pikachu', 'ike')
# sys_attack_impact plays with sys_attack_line (0x100008D) in most moves; its own is the runner-up
OVERRIDES = {'sys_attack_impact': 0x100008F}
FN = re.compile(r'unsafe extern "C" fn (effect|game|sound|expression)_(\w+)\(')
ABBREV = {'atk': 'attack', 'h': 'horizontal', 'v': 'vertical'}
CALL = re.compile(r'macros::(\w+)\(agent, Hash40::new\("(sys_\w+)"\)')


def ult_calls(text):
    """{move: [(frame, sys name, macro)]} of the effect_* functions"""
    out, cur, frame = {}, None, 0.0
    for line in text.split('\n'):
        m = FN.search(line)
        if m:
            cur = m.group(2) if m.group(1) == 'effect' else None
            frame = 0.0
            if cur:
                out[cur] = []
            continue
        if cur is None:
            continue
        m = re.search(r'\bframe\(agent\.lua_state_agent, ([\d.]+)\)', line)
        if m:
            frame = float(m.group(1))
            continue
        m = re.search(r'\bwait\(agent\.lua_state_agent, ([\d.]+)\)', line)
        if m:
            frame += float(m.group(1))
            continue
        for m in CALL.finditer(line):
            out[cur].append((frame, m.group(2), m.group(1)))
    return out


def s4_calls(script):
    """[(frame, common effect id, command name)]"""
    out, frame = [], 0.0
    for c in script:
        p = [getattr(x, 'value', x) for x in c.params]
        if c.name == 'FRAME':
            frame = float(p[0])
        elif c.name == 'WAIT':
            frame += float(p[0])
        elif p and isinstance(p[0], int) and (p[0] >> 16) == 0x100:
            out.append((frame, p[0], c.name))
    return out


def common_names(efc_path, ptcl_path):
    """{lower-case name without PtcCommon / EffCommon: [common effect ids]}"""
    import efc
    import ptcl
    e = efc.Efc(open(efc_path, 'rb').read())
    p = ptcl.Ptcl(open(ptcl_path, 'rb').read())
    out = collections.defaultdict(list)
    for i, (_fl, st, md, _ms, _mc) in enumerate(e.entries):
        for n in (p.set_name(st - 1) if st else '', e.models[md - 1] if md else ''):
            n = re.sub(r'^(Ptc|Eff)Common', '', n).lower()
            if n and 0x1000000 + i not in out[n]:
                out[n].append(0x1000000 + i)
    return out


def by_name(name, names):
    """the common ids whose name is the sys_* name's"""
    return names.get(''.join(ABBREV.get(w, w) for w in name[4:].split('_')), [])


def main():
    a = sys.argv[1:]
    names = {}
    if '--common' in a:
        i = a.index('--common')
        names = common_names(a[i + 1], a[i + 2])
        del a[i:i + 3]
    dumps, vanilla, out = a[:3]
    fighters = a[3:] or FIGHTERS
    ids = collections.defaultdict(collections.Counter)
    pairs = []
    for f in fighters:
        text = '\n'.join(open(p, errors='ignore').read()
                         for p in glob.glob(os.path.join(dumps, 'lua2cpp_' + f, f, '*.txt')))
        s4 = acmd.ACMDFile.load(os.path.join(vanilla, f, 'script/animcmd/body/effect.bin'))
        for move, calls in ult_calls(text).items():
            sc = s4.scripts.get(acmd.crc(move))
            if not sc:
                continue
            se = s4_calls(sc)
            for fr, name, macro in calls:
                for fr2, eid, cname in se:
                    if abs(fr - fr2) <= 1.0:
                        ids[name][eid] += 1
                        pairs.append((name, macro, eid, cname))
    res = {}
    for name, c in sorted(ids.items(), key=lambda kv: -sum(kv[1].values())):
        eid, n = c.most_common(1)[0]
        named = by_name(name, names)
        if named and eid not in named:
            eid = max(named, key=lambda x: (c[x], -named.index(x)))
            print('%-24s by name' % name)
        eid = OVERRIDES.get(name, eid)
        res[name] = '0x%07X' % eid
        print('%-24s 0x%07X  %3d of %3d  %s' % (name, eid, n, sum(c.values()),
                                                 ['0x%07X %d' % kv for kv in c.most_common(3)]))
    macros = collections.defaultdict(collections.Counter)
    for name, macro, eid, cname in pairs:
        if eid == int(res[name], 16):
            macros[macro][cname] += 1
    print()
    for macro, c in sorted(macros.items(), key=lambda kv: -sum(kv[1].values())):
        print('%-26s %s' % (macro, c.most_common(3)))
    res = {'_about': 'Ultimate sys_* effect -> Smash 4 common effect id (tools/ultimate_sys_effect_map.py, '
                     'fighters: %s%s)' % (', '.join(fighters), '; by name where one matches' if names else ''),
           **res}
    json.dump(res, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
