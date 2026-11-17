#!/usr/bin/env python3
"""Silent hits in an Ultimate port's game scripts: hitboxes whose SFXType is 0 (Smash 4's "Nothing") where Ultimate's
own hitbox has a sound (its COLLISION_SOUND_ATTR is not NONE), and their fix.

  python3 tools/hit_sound_fix.py DUMP_DIR GAME.bin [GAME.bin ...] [--fix OUT_DIR]

DUMP_DIR: the fighter's smashline dump (lua2cpp_NAME, every folder under it: the fighter and its articles). Each
translated hitbox (Hitbox / Special_Hitbox / Extended_* / Throw_Specifier) is matched to Ultimate's ATTACK / ATTACK_ABS
lines by its damage, knockback growth / base and size (the angle is remapped by the translator, the bone renamed); a
hitbox with SFXType 0 whose every match has a sounding attribute is silent by mistake. Byleth v1 - v15: ultimate_acmd's
SFX_TYPE didn't list COLLISION_SOUND_ATTR_MASTER_AXE (Aymr), _MASTER_ATTACK (the rapid jab's finisher),
_MASTER_ARROW_MAX: `SFX_TYPE.get(attr, 0)` made them 0 (user, v15: "down special has no hit sound"). --fix writes each
GAME.bin with ultimate_acmd.sfx_type(attr) in those hitboxes (OUT_DIR/<the file's name>). port_check S25 runs `scan`.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd  # noqa: E402

HITBOXES = ('Hitbox', 'Extended_Hitbox', 'Special_Hitbox', 'Extended_Special_Hitbox', 'Throw_Specifier')
ATTACK = re.compile(r'macros::ATTACK\(agent, (.*?)\);')
ATTACK_ABS = re.compile(r'macros::ATTACK_ABS\(agent, (.*?)\);')


def _num(s):
    try:
        return float(s)
    except ValueError:
        return None


def attack_sounds(dump):
    """{(damage, kbg, bkb, size): set of COLLISION_SOUND_ATTR names} over every script of the dump (size None for
    ATTACK_ABS, a throw)"""
    out = {}
    for d, _ds, fs in os.walk(dump, followlinks=True):
        for f in fs:
            if not f.endswith('.txt'):
                continue
            text = open(os.path.join(d, f), errors='replace').read()
            for m in ATTACK.finditer(text):
                a = [x.strip() for x in m.group(1).split(',')]
                if len(a) < 35:
                    continue
                attr = a[34].lstrip('*')
                key = (_num(a[3]), _num(a[5]), _num(a[7]), _num(a[8]))
                out.setdefault(key, set()).add(attr)
            for m in ATTACK_ABS.finditer(text):
                a = [x.strip() for x in m.group(1).split(',')]
                if len(a) < 15:
                    continue
                attr = a[14].lstrip('*')
                key = (_num(a[2]), _num(a[4]), _num(a[6]), None)
                out.setdefault(key, set()).add(attr)
    return out


def _key(c):
    syn = c.info.get('syntax', [])
    p = dict(zip(syn, c.params))
    if c.name == 'Throw_Specifier':
        return (float(p['Damage']), float(p['KBG']), float(p['BKB']), None)
    return (float(p['Damage']), float(p['KBG']), float(p['BKB']), round(float(p['Size']), 3))


def _match(table, key):
    for k, attrs in table.items():
        if k[0] is None or k[0] != key[0] or k[1] != key[1] or k[2] != key[2]:
            continue
        if key[3] is not None and (k[3] is None or abs(k[3] - key[3]) > 1e-3):
            continue
        if (key[3] is None) != (k[3] is None):
            continue
        yield attrs


def scan(table, scripts):
    """[(script hash, command, Ultimate attr)] for every silent hitbox whose matches all sound"""
    bad = []
    for h, cmds in scripts.items():
        for c in cmds:
            if c.name not in HITBOXES:
                continue
            syn = c.info.get('syntax', [])
            if 'SFXType' not in syn or c.params[syn.index('SFXType')] != 0:
                continue
            ms = list(_match(table, _key(c)))
            attrs = set().union(*ms) if ms else set()
            if attrs and 'COLLISION_SOUND_ATTR_NONE' not in attrs:
                bad.append((h, c, sorted(attrs)[0]))
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('dump')
    ap.add_argument('games', nargs='+')
    ap.add_argument('--fix')
    a = ap.parse_args()
    import ultimate_acmd as U
    table = attack_sounds(a.dump)
    total = 0
    for g in a.games:
        f = acmd.ACMDFile.load(g)
        bad = scan(table, f.scripts)
        total += len(bad)
        for h, c, attr in bad:
            syn = c.info['syntax']
            print('%s %08X %s ID %s %.1f%%: SFXType 0 -> %d (%s)' % (
                os.path.basename(os.path.dirname(g)) + '/' + os.path.basename(g), h, c.name,
                c.params[0], c.params[syn.index('Damage')], U.sfx_type(attr), attr))
            if a.fix:
                c.params[syn.index('SFXType')] = U.sfx_type(attr)
        if a.fix and bad:
            out = os.path.join(a.fix, os.path.basename(os.path.dirname(g)), os.path.basename(g))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            f.save(out)
            print('  ->', out)
    print('%d silent hitbox%s' % (total, '' if total == 1 else 'es'))


if __name__ == '__main__':
    main()
