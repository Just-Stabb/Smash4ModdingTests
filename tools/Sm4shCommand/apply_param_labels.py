#!/usr/bin/env python3
"""Applies param_labels.json (the ACMD parameter research: docs/acmd-params.md) to SALT's command table
and regenerates what is made from it.

  python3 tools/Sm4shCommand/apply_param_labels.py [--check]

param_labels.json: {command hash (hex): {"_command": its current name, "_name": a new name (for
unk_XXXXXXXX commands), "_note": what the command does, "_format": [types, one per parameter: 0 int,
1 float, 2 decimal, 3 variable] (only where the old types were wrong), "_size": parameter count + 1
(only where the old size was wrong), "_desc_extra": text added to the command's description (its
real name where the table's is wrong: names are kept, scripts use them), "_new": true (a command that
isn't in the table: added with "_name", "_size", "_format", "_desc" and the slot names; see
tools/acmd_ext_cave.py), "<slot>": {"name", "desc", "values", "evidence",
"confidence": high | medium | low}}}.

Writes:
- SALT/SALT/Scripting/AnimCMD/CMD_INFO.cs: CMD_NAMES (renames), PARAM_SYNTAX (the names), PARAM_FORMAT
  and CMD_SIZES (where given);
- tools/acmd_info.json (tools/acmd.py's table) from CMD_INFO.cs;
- then run make_events_cfg.py, which adds a "Param: Name = description" line per labelled parameter
  (shown in the editor's tooltips) from param_labels.json.
--check: report what would change, write nothing.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
CMD_INFO = os.path.join(HERE, 'SALT', 'SALT', 'Scripting', 'AnimCMD', 'CMD_INFO.cs')
LABELS = os.path.join(HERE, 'param_labels.json')
ACMD_INFO = os.path.join(REPO, 'tools', 'acmd_info.json')


def clean(name):
    """a parameter name the editor's syntax accepts: letters, digits, _ and / (as Ground/Air)"""
    n = re.sub(r'[^A-Za-z0-9_/]', '', name.replace(' ', '_'))
    return n or 'Unknown'


def slots(entry):
    return sorted((int(k), v) for k, v in entry.items() if not k.startswith('_'))


def edit_table(text, table, crc, value, quote=True):
    """replace (or add) {0xCRC, value} in the C# dictionary `table`"""
    i = text.index(' %s = new Dictionary' % table)
    j = text.index('};', i)
    body = text[i:j]
    v = '"%s"' % value if quote else str(value)
    pat = re.compile(r'\{\s*0x%08X\s*,\s*(?:"(?:[^"\\]|\\.)*"|\d+)\s*\}' % crc, re.I)
    m = pat.search(body)
    if m:
        body = body[:m.start()] + '{0x%08X,%s}' % (crc, v) + body[m.end():]
    else:
        k = body.rindex('}')
        body = body[:k + 1] + ',\n            {0x%08X,%s}' % (crc, v) + body[k + 1:]
    return text[:i] + body + text[j:]


def table(text, name):
    i = text.index(' %s = new Dictionary' % name)
    j = text.index('};', i)
    body = text[i:j]
    if name == 'CMD_SIZES':
        return {int(k, 16): int(v) for k, v in re.findall(r'\{\s*0x([0-9A-Fa-f]+)\s*,\s*(\d+)\s*\}', body)}
    return {int(k, 16): v for k, v in re.findall(r'\{\s*0x([0-9A-Fa-f]+)\s*,\s*"((?:[^"\\]|\\.)*)"\s*\}', body)}


def main():
    check = '--check' in sys.argv
    labels = json.load(open(LABELS))
    text = open(CMD_INFO, encoding='utf-8-sig').read()
    names, syntax, fmt, sizes = (table(text, n) for n in ('CMD_NAMES', 'PARAM_SYNTAX', 'PARAM_FORMAT', 'CMD_SIZES'))
    changes = 0
    for h, entry in sorted(labels.items()):
        crc = int(h, 16)
        if entry.get('_new'):                                   # a new command (tools/acmd_ext_cave.py): (re)define it
            n_new = entry['_size'] - 1
            text = edit_table(text, 'CMD_NAMES', crc, clean(entry['_name']))
            text = edit_table(text, 'CMD_SIZES', crc, entry['_size'], quote=False)
            text = edit_table(text, 'PARAM_FORMAT', crc, ','.join(str(x) for x in entry['_format']) or 'NONE')
            text = edit_table(text, 'PARAM_SYNTAX', crc, ','.join(clean(entry[str(k)]['name']) for k in range(n_new)) or 'NONE')
            text = edit_table(text, 'CMD_DESC', crc, entry.get('_desc', 'NONE').replace('"', '\\"'))
            names, syntax, fmt, sizes = (table(text, n) for n in ('CMD_NAMES', 'PARAM_SYNTAX', 'PARAM_FORMAT', 'CMD_SIZES'))
            changes += 1
        if crc not in names:
            print('skip %s: not in the table' % h)
            continue
        size = entry.get('_size', sizes.get(crc, 1))
        n = size - 1
        if '_size' in entry and entry['_size'] != sizes.get(crc):
            text = edit_table(text, 'CMD_SIZES', crc, entry['_size'], quote=False)
            changes += 1
        if entry.get('_name') and entry['_name'] != names[crc]:
            text = edit_table(text, 'CMD_NAMES', crc, clean(entry['_name']))
            changes += 1
        if n <= 0:
            continue
        old = (syntax.get(crc) or '').split(',') if syntax.get(crc) not in (None, 'NONE') else []
        new = (old + ['Unknown'] * n)[:n]
        for k, s in slots(entry):
            if k < n and s.get('name'):
                new[k] = clean(s['name'])
        seen = {}
        for k, x in enumerate(new):                                 # unique names in a command
            if x in seen and x.lower() != 'unknown':
                seen[x] += 1
                new[k] = '%s%d' % (x, seen[x])
            else:
                seen.setdefault(x, 1)
        if new != old:
            text = edit_table(text, 'PARAM_SYNTAX', crc, ','.join(new))
            changes += 1
        if '_format' in entry:
            f = ','.join(str(x) for x in entry['_format'])
            assert len(entry['_format']) == n, (h, len(entry['_format']), n)
            if f != fmt.get(crc):
                text = edit_table(text, 'PARAM_FORMAT', crc, f)
                changes += 1
        elif fmt.get(crc) and len(fmt[crc].split(',')) != n:
            print('note %s %s: %d types for %d parameters' % (h, names[crc], len(fmt[crc].split(',')), n))
    print('%d table edits for %d commands' % (changes, len(labels)))
    if check:
        return
    crlf = b'\r\n' in open(CMD_INFO, 'rb').read(4096)             # keep the file's line endings
    open(CMD_INFO, 'w', encoding='utf-8-sig', newline='\r\n' if crlf else '\n').write(text.replace('\r\n', '\n'))
    names, syntax, fmt, sizes = (table(text, n) for n in ('CMD_NAMES', 'PARAM_SYNTAX', 'PARAM_FORMAT', 'CMD_SIZES'))
    cmds = {}
    for crc, name in names.items():
        f = fmt.get(crc)
        s = syntax.get(crc)
        cmds['%08X' % crc] = {
            'size': sizes.get(crc, 1), 'name': name,
            'format': [int(x) for x in f.split(',')] if f and f != 'NONE' else [],
            'syntax': s.split(',') if s and s != 'NONE' else []}
    json.dump({'_source': 'Generated from SALT (Sammi Husky, MIT license) Scripting/AnimCMD/CMD_INFO.cs, '
               'with tools/Sm4shCommand/param_labels.json applied', 'commands': cmds},
              open(ACMD_INFO, 'w'), indent=0)
    subprocess.run([sys.executable, os.path.join(HERE, 'make_events_cfg.py')], check=True)


if __name__ == '__main__':
    main()
