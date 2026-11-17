#!/usr/bin/env python3
"""Silent status motions in an Ultimate port's expression scripts: common motions (guard on / off, landings, footstools,
down bounds, ...) whose script rumbles nowhere while the base's (vanilla) script for the motion does, and their fix.

  python3 tools/rumble_fix.py DUMP_DIR PORT_EXPRESSION.bin BASE_EXPRESSION.bin [--fix OUT.bin]

Ultimate plays those rumbles from its common status code: the dumped expression scripts only carry a
`// TODO: expression_GuardOnRumble();` comment, so ultimate_acmd wrote Ultimate's script (slope only) over the base's
and the rumble was lost (Byleth v1 - v18, user: "Byleth's shield on/off don't cause rumble like every other
character's"). The translator now keeps the base's rumble (ultimate_acmd.keep_base_rumble, run by translate_others);
this applies the same to an installed file. DUMP_DIR: the fighter's smashline dump folder (lua2cpp_NAME/NAME).
BASE_EXPRESSION: the base fighter's vanilla expression.bin. port_check S35 runs `scan`.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd  # noqa: E402


def dump_helpers(dump):
    """{script name: Ultimate's TODO rumble helper or None} for every expression_* function of the dump"""
    import ultimate_acmd as U
    out = {}
    if not dump or not os.path.isdir(dump):
        return out
    for path in sorted(os.listdir(dump)):
        if not path.endswith('.txt'):
            continue
        src = path[:-4]
        for fn, body in U.functions(open(os.path.join(dump, path), errors='replace').read()).items():
            if not fn.startswith('expression_'):
                continue
            name = fn[len('expression_'):]
            if name == src.lower():
                name = U.TRANSLATE.get(src, name)
            m = U.RUMBLE_HELPER.search(body)
            out[name] = m.group(1) if m else None
    return out


def scan(port, base, dump=None, names=None):
    """[(script name, the base's rumble commands)]: the port's status-motion scripts with no rumble whose base script
    rumbles. port / base: {crc: [Command]}"""
    import ultimate_acmd as U
    import mtable
    helpers = dump_helpers(dump)
    cands = set(helpers) | {c.lower() for c in mtable.COMMON} | set(names or ())
    out = []
    for name in sorted(cands):
        h = acmd.crc(name)
        if h not in port or not (helpers.get(name) or U.status_motion(name)):
            continue
        if any(c.name in U.RUMBLE_CMDS for c in port[h]):
            continue
        rb = U.rumble_timed(base.get(h))
        if rb:
            out.append((name, ['%s@%d' % (c, t) for t, c in rb]))
    return out


def fix(port_file, base, dump=None):
    """the port's ACMDFile with the base's rumble kept in those scripts; [names changed]"""
    import ultimate_acmd as U
    import json
    smap = json.load(open(os.path.join(HERE, '..', 'reference', 'ultimate_sound_map.json')))
    helpers = dump_helpers(dump)
    done = []
    for name, _r in scan(port_file.scripts, base, dump):
        h = acmd.crc(name)
        hp = smap.get('rumble_helpers', {}).get(helpers.get(name)) if helpers.get(name) else None
        port_file.scripts[h], kept = U.keep_base_rumble(port_file.scripts[h], base.get(h), hp)
        if kept:
            done.append(name)
    return done


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('dump')
    ap.add_argument('port')
    ap.add_argument('base')
    ap.add_argument('--fix')
    a = ap.parse_args()
    port = acmd.ACMDFile.load(a.port)
    base = acmd.ACMDFile.load(a.base).scripts
    found = scan(port.scripts, base, a.dump)
    for name, r in found:
        print('%-22s no rumble; the base\'s: %s' % (name, ', '.join(r)))
    print('%d status-motion scripts without the base\'s rumble' % len(found))
    if a.fix:
        done = fix(port, base, a.dump)
        port.save(a.fix)
        print('kept the base\'s rumble in %d: %s -> %s' % (len(done), ', '.join(done), a.fix))
        left = scan(acmd.ACMDFile.load(a.fix).scripts, base, a.dump)
        assert not left, left


if __name__ == '__main__':
    main()
