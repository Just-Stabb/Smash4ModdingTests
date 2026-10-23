#!/usr/bin/env python3
"""Usage examples for the command list (View > Commands): one real use of every vanilla ACMD command,
taken from the game's own scripts, written as Sm4shCommand writes it.

  python3 tools/Sm4shCommand/make_examples.py FIGHTER_DIR [-o tools/Sm4shCommand/vanilla_examples.json]

FIGHTER_DIR is the game's data/fighter folder (each fighter's script/animcmd/body/*.bin and
script/animcmd/weapon/*/*.bin are read). Writes {command hash: [lines]}: a "// fighter, script (file)"
line, then the command; block commands (True, False, Is_Bool, Is_Not_Bool, Else, Set_Loop) with
their block, as Sm4shCommand decompiles them (a short one is picked). make_events_cfg.py puts them in
Events.cfg as "Example:" lines (our own commands' examples are in param_labels.json, "_example").
"""
import argparse
import glob
import json
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import acmd  # noqa: E402

PREFERRED = ['mario', 'link', 'captain', 'fox', 'kirby', 'pikachu', 'samus', 'marth', 'ike', 'sonic',
             'donkey', 'koopa', 'luigi', 'peach', 'zelda', 'sheik']
FILES = ['game', 'effect', 'sound', 'expression']
CONDITIONALS = {0xA5BD4F32, 0x870CF021, 0x47810508, 0xC31DF569}     # True, False, Is_Bool, Is_Not_Bool
ELSE, LOOP, GOTO = 0x895B9275, 0x0EB375E3, 0x38A3EC78
MAX_BLOCK_LINES = 8


def text(c):
    """a command as Sm4shCommand writes it (ints in hex, variables as their ID)"""
    syn = c.info['syntax']
    parts = []
    for i, p in enumerate(c.params):
        k = c.kind(i)
        if (k == 1 or k == 2) and isinstance(p, float):
            v = ('%g' % p) if abs(p) < 1e6 else repr(p)
        elif k == 2:
            v = str(p - (1 << 32) if p >= 1 << 31 else p)    # decimal (Set_Loop, Goto): signed
        else:
            v = '0x%X' % (p & 0xFFFFFFFF) if (k == 3 or p > 9 or p < 0) else str(p)
        parts.append('%s=%s' % (syn[i], v) if i < len(syn) else v)
    return '%s(%s)' % (c.name, ', '.join(parts))


def words(c):
    return c.info['size']


def block(cmds, i, indent=''):
    """lines of the block command at i (and its Else), and the index after it; None if it's malformed"""
    c = cmds[i]
    out = [indent + text(c) + '{']
    if c.ident == LOOP:
        j = i + 1
        while j < len(cmds) and cmds[j].ident != GOTO:
            if cmds[j].ident in CONDITIONALS or cmds[j].ident in (ELSE, LOOP):
                sub = block(cmds, j, indent + '    ')
                if sub is None:
                    return None
                out += sub[0]
                j = sub[1]
            else:
                out.append(indent + '    ' + text(cmds[j]))
                j += 1
        if j >= len(cmds):
            return None
        out.append(indent + '    ' + text(cmds[j]))
        out.append(indent + '}')
        return out, j + 1
    left = c.params[0] - words(c)
    j = i + 1
    while left > 0 and j < len(cmds):
        n = cmds[j]
        if n.ident == ELSE and left - words(n) == 0 and c.ident != ELSE:
            break
        if n.ident in CONDITIONALS or n.ident in (ELSE, LOOP):
            sub = block(cmds, j, indent + '    ')
            if sub is None:
                return None
            for k in range(j, sub[1]):
                left -= words(cmds[k])
            out += sub[0]
            j = sub[1]
        else:
            out.append(indent + '    ' + text(n))
            left -= words(n)
            j += 1
    if left < 0:
        return None
    out.append(indent + '}')
    if j < len(cmds) and cmds[j].ident == ELSE and c.ident != ELSE:
        sub = block(cmds, j, indent)
        if sub is None:
            return None
        out += sub[0]
        j = sub[1]
    return out, j


def sources(root):
    fighters = sorted(os.listdir(root), key=lambda f: (PREFERRED.index(f) if f in PREFERRED else len(PREFERRED), f))
    for f in fighters:
        body = os.path.join(root, f, 'script', 'animcmd', 'body')
        for kind in FILES:
            p = os.path.join(body, kind + '.bin')
            if os.path.exists(p):
                yield f, '', kind, p
        for w in sorted(glob.glob(os.path.join(root, f, 'script', 'animcmd', 'weapon', '*'))):
            for kind in FILES:
                p = os.path.join(w, kind + '.bin')
                if os.path.exists(p):
                    yield f, os.path.basename(w), kind, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('fighter_dir')
    ap.add_argument('-o', default=os.path.join(HERE, 'vanilla_examples.json'))
    a = ap.parse_args()
    names = {}
    for line in open(os.path.join(HERE, 'SM4SHCommand', 'AnimNames.txt'), encoding='utf-8', errors='replace'):
        line = line.strip()
        if line and not line.startswith('//') and '=' not in line:
            names[zlib.crc32(line.lower().encode()) & 0xFFFFFFFF] = line
    found, blocks = {}, {}
    for fighter, weapon, kind, path in sources(a.fighter_dir):
        try:
            f = acmd.ACMDFile.load(path)
        except (SystemExit, Exception):
            continue
        for h in sorted(f.scripts, key=lambda h: names.get(h, '~%08X' % h)):
            cmds = f.scripts[h]
            where = '// %s%s, %s (%s)' % (fighter, ' ' + weapon if weapon else '', names.get(h, '0x%08X' % h), kind)
            for i, c in enumerate(cmds):
                if c.ident in CONDITIONALS or c.ident in (ELSE, LOOP):
                    if c.ident == ELSE:
                        continue                       # shown with the True / False it follows
                    b = block(cmds, i)
                    if b is None:
                        continue
                    lines = b[0]
                    if i > 0 and c.ident in CONDITIONALS and cmds[i - 1].ident not in CONDITIONALS | {ELSE, LOOP, GOTO}:
                        lines = [text(cmds[i - 1])] + lines           # the test it reads
                    body = sum(1 for x in lines if x.startswith('    ') and not x.strip().startswith('Goto('))
                    if body == 0 or len(lines) > MAX_BLOCK_LINES:
                        continue                       # an empty block says little; a long one too much
                    score = (where.find(', 0x') >= 0, len(lines))      # named scripts first, then shorter
                    best = blocks.get(c.ident)
                    if best is None or score < best[0]:
                        blocks[c.ident] = (score, [where] + lines)
                    k_else = [n for n, x in enumerate(lines) if x.startswith('Else(')]
                    k_if = [n for n, x in enumerate(lines) if x.endswith('{') and not x.startswith(' ')]
                    if k_else and any(x.startswith('    ') for x in lines[k_else[0] + 1:]) \
                            and any(x.startswith('    ') for x in lines[k_if[0] + 1:k_else[0]]):   # something in both
                        best = blocks.get(ELSE)
                        if best is None or score < best[0]:
                            blocks[ELSE] = (score, [where] + lines)
                elif c.ident not in found and c.ident != GOTO and c.ident in acmd.INFO:
                    found[c.ident] = [where, text(c)]
    found.update({k: v[1] for k, v in blocks.items()})
    if LOOP in blocks:
        found[GOTO] = blocks[LOOP][1]
    out = {'%08X' % k: v for k, v in sorted(found.items())}
    json.dump(out, open(a.o, 'w'), indent=1)
    print('%d commands with an example -> %s' % (len(out), a.o))


if __name__ == '__main__':
    main()
