#!/usr/bin/env python3
"""The window under a virtual display: built, roster icons loaded, CSS / SSS previews drawn with the planned clone;
screenshots for the README.

  python3 tools/sm4shclonetool/tests/gui_test.py PYTHON_WITH_TK DATA CUSTOM_UI EXE OUT SHOTS_DIR

Runs `xvfb-run PYTHON gui.py --screenshot` twice (Fighters tab on the custom UI with a Fox clone planned, Stages tab
with a page-2 stage clone planned), HOME pointed at a temporary folder (the remembered settings go there).
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(os.path.dirname(HERE), 'gui.py')


def shot(py, args, png, home):
    cmd = ['xvfb-run', '-a', '-s', '-screen 0 1600x1080x24', py, GUI, '--screenshot', png] + args
    r = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ, HOME=home), timeout=600)
    line = [x for x in r.stdout.splitlines() if x.startswith('{')]
    return json.loads(line[-1]) if line else {'error': r.stderr[-1500:]}


def main():
    py, data, cui, exe, out, shots = sys.argv[1:7]
    os.makedirs(shots, exist_ok=True)
    home = tempfile.mkdtemp(prefix='s4ct_home_')
    fails = 0
    a = shot(py, ['--data', data, '--ui', cui, '--exe', exe, '--out', out, '--fighter', 'fox:wolfclone'],
             os.path.join(shots, 'gui_fighters.png'), home)
    ok = a.get('title', '').startswith('Sm4shCloneTool') and a.get('fighters', 0) > 50 and \
        a.get('fighter_icons', 0) > 40 and a.get('css', {}).get('real_layout')
    print('%s fighters tab: %s' % ('ok  ' if ok else 'FAIL', json.dumps({k: v for k, v in a.items() if k != 'css'})))
    print('     css: %s' % json.dumps({k: a.get('css', {}).get(k) for k in ('count', 'note', 'problems')}))
    fails += not ok
    settings = json.load(open(os.path.join(home, '.sm4shclonetool.json')))
    ok = settings.get('data') == data and settings.get('exe') == exe
    print('%s folder settings remembered: %s' % ('ok  ' if ok else 'FAIL', sorted(settings)))
    fails += not ok
    b = shot(py, ['--tab', 'stages', '--stage', 'BattleField_f:CloneTwo:2'], os.path.join(shots, 'gui_stages.png'), home)
    ok = b.get('title', '').startswith('Sm4shCloneTool')
    print('%s stages tab (folders from the remembered settings): %s' % ('ok  ' if ok else 'FAIL', 'error' not in b))
    fails += not ok
    c = shot(py, ['--tab', 'extras', '--fighter', 'szerosuit:zclone'], os.path.join(shots, 'gui_extras.png'), home)
    ok = 'font DF_Mincho_SU.ttf' in c.get('plate', '') and c.get('languages', 0) >= 1
    print('%s extras tab: plate preview %r, %d language(s)' % ('ok  ' if ok else 'FAIL', c.get('plate'),
                                                            c.get('languages', 0)))
    fails += not ok
    d = shot(py, ['--tab', 'voices'], os.path.join(shots, 'gui_voices.png'), home)
    ok = d.get('voices', 0) > 0
    print('%s voices tab: %d lines of the project\'s last clone with banks listed' % ('ok  ' if ok else 'FAIL', d.get('voices', 0)))
    fails += not ok
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
