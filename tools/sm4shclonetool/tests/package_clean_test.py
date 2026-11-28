#!/usr/bin/env python3
"""Fails if the standalone package names anything of the research repository's own mod: its fighters (every name in
tools/extra_kinds.json: folder, Capitalised and UI names), its executable builds and caves, its paths, the people
in its git history, the working folders. Text files are read whole; PNG screenshots are checked for text chunks.

  python3 tools/sm4shclonetool/tests/package_clean_test.py Sm4shCloneTool_v1.zip
"""
import json
import os
import re
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
REPO = os.path.dirname(TOOLS)


def forbidden():
    words = {'supamario', 'squirtle', 'zenigame', 'pzenigame', 'byleth', 'sephiroth', 'edge', 'brave', 'master',
             'gaogaen', 'incineroar', 'pickel', 'steve', 'hero', 'kamehameha', 'ultra instinct'}
    spec = json.load(open(os.path.join(TOOLS, 'extra_kinds.json')))
    for r in spec['kinds']:
        words |= {r['name'].lower(), (r.get('cap') or '').lower(), ((r.get('ui') or {}).get('name') or '').lower()}
        words |= {w.lower() for w in (r.get('weapons') or {})}
    words.discard('')
    # the article names of new kinds are often vanilla words (fireball, water, fire, ...): only the specific ones
    words -= {'fireball', 'mantle', 'pump', 'pumpwater', 'hugeflame', 'dokan', 'fire', 'flash', 'trail', 'fill',
              'water', 'explosion', 'tornado', 'spark', 'sleep', 'crash', 'whip', 'phantom', 'arrow1', 'arrow2',
              'snake', 'snaketip', 'flare1', 'flare2', 'deathball'}
    subs = ['gekkouga_clone_cave', 'exe_v46', 'exe_v45', 'exe_v44', 'extra_kinds.json', 'tools/', 'fighters/',
            'docs/', 'scratchpad', '/home/user', 'Smash4ModdingTests', 'claude', '0x037EE73C', 'kind_expand_incremental',
            'cave_fix_s4', 'poketrainer']
    try:
        for line in subprocess.run(['git', '-C', REPO, 'log', '--format=%an%n%ae'], capture_output=True,
                                   text=True).stdout.splitlines():
            if line.strip() and 'noreply' not in line and line.strip().lower() not in ('claude',):
                subs.append(line.strip())
    except Exception:
        pass
    return words, sorted(set(subs))


# the only font files the package may hold: the two bundled fonts (fonts/FONTS_NOTICE.txt), by name and SHA-256
FONTS = {'Sm4shCloneTool/fonts/DF_Mincho_SU.ttf': 'MINCHO', 'Sm4shCloneTool/fonts/DF_Gothic_SU.ttf': 'GOTHIC'}
FONT_EXT = ('.ttf', '.otf', '.ttc', '.bfttf', '.bffnt', '.bfotf', '.brf', '.woff', '.woff2')


def font_hashes():
    import hashlib
    d = os.path.join(os.path.dirname(HERE), 'fonts')
    return {k: hashlib.sha256(open(os.path.join(d, os.path.basename(k)), 'rb').read()).hexdigest() for k in FONTS}


def main():
    import hashlib
    words, subs = forbidden()
    want_fonts = font_hashes()
    rx = re.compile(r'\b(%s)\b' % '|'.join(re.escape(w) for w in sorted(words, key=len, reverse=True)), re.I)
    hits = []
    z = zipfile.ZipFile(sys.argv[1])
    n = 0
    for info in z.infolist():
        if info.is_dir():
            continue
        data = z.read(info)
        n += 1
        if info.filename.lower().endswith(FONT_EXT):
            if want_fonts.get(info.filename) != hashlib.sha256(data).hexdigest():
                hits.append('%s: a font file other than the two bundled ones (or changed)' % info.filename)
            continue
        if info.filename.endswith('.png'):
            text = b''.join(re.findall(rb'tEXt(.{0,200})', data)).decode('latin1')
        else:
            text = data.decode('utf-8', 'replace')
        for m in rx.finditer(text):
            hits.append('%s: %r' % (info.filename, text[max(0, m.start() - 30):m.end() + 30]))
        for s in subs:
            if s.lower() in text.lower() or s.lower() in info.filename.lower():
                hits.append('%s: %r' % (info.filename, s))
    names = {i.filename for i in z.infolist()}
    for k in want_fonts:
        if k not in names:
            hits.append('%s: the bundled font is missing' % k)
    print('%d files checked for %d names and %d strings; fonts: only %s' % (n, len(words), len(subs),
                                                                          ', '.join(sorted(want_fonts))))
    for h in hits[:40]:
        print('FAIL ' + h)
    print('package clean: %s (%d hits)' % ('ok' if not hits else 'FAILED', len(hits)))
    sys.exit(1 if hits else 0)


if __name__ == '__main__':
    main()
