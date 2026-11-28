#!/usr/bin/env python3
"""Build the standalone Sm4shCloneTool zip: the tool, the research modules it runs on (vendor/), the launchers, the
README, the licences and the screenshots. No game data.

  python3 tools/sm4shclonetool/make_package.py OUT.zip [--screenshots DIR] [--check-exe VANILLA.rpx]

--check-exe: unpack the zip into a temporary folder and run its CLI there (python -I: nothing from this repository
on the path) on that executable.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
TOP = 'Sm4shCloneTool'
# the research modules the tool imports (copied unchanged from tools/), and their data files
VENDOR = ['rpx_patch.py', 'rpx_compact.py', 'ppcasm.py', 'kind_expand.py', 'kind_expand_ram.json', 'weapon_expand.py',
          'base_effects_cave.py', 'base_customs_cave.py', 'stage_slot_cave.py', 's4param.py', 'msbt.py',
          'add_fighter.py', 'add_stage.py', 'add_fighter_customs.py', 'fighter_extras.py', 'fighter_param.py',
          'acmd.py', 'nut.py', 'chara_layout.py']
FILES = ['cli.py', 'gui.py', 'setup.bat', 'run.bat', 'run_cli.bat', 'requirements.txt', 'README.md', 'LICENSE.txt',
         'THIRD_PARTY.txt']


def acmd_info():
    """tools/acmd_info.json (the ACMD command table, from SALT) without commands added by other projects' code
    caves: only the game's own"""
    info = json.load(open(os.path.join(TOOLS, 'acmd_info.json')))
    try:
        sys.path.insert(0, TOOLS)
        import acmd_ext_cave as ext
        import zlib
        extra = {'%X' % (zlib.crc32(n.encode()) & 0xFFFFFFFF) for n, *_r in ext.NEW_CMDS}
        extra |= {'%08X' % (zlib.crc32(n.encode()) & 0xFFFFFFFF) for n, *_r in ext.NEW_CMDS}
        names = {n for n, *_r in ext.NEW_CMDS}
    except Exception:
        extra, names = set(), set()
    cmds = {k: v for k, v in info['commands'].items() if k.upper() not in extra and v.get('name') not in names}
    info['commands'] = cmds
    return json.dumps(info, indent=0)


def build(out, shots):
    if os.path.exists(out):
        os.unlink(out)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, ds, fs in os.walk(os.path.join(HERE, 'sm4shclonetool')):
            ds[:] = [d for d in ds if d != '__pycache__']
            for f in sorted(fs):
                if f.endswith('.py'):
                    p = os.path.join(root, f)
                    z.write(p, os.path.join(TOP, os.path.relpath(p, HERE)))
        for f in FILES:
            z.write(os.path.join(HERE, f), os.path.join(TOP, f))
        for f in VENDOR:
            z.write(os.path.join(TOOLS, f), os.path.join(TOP, 'vendor', f))
        z.writestr(os.path.join(TOP, 'vendor', 'acmd_info.json'), acmd_info())
        z.writestr(os.path.join(TOP, 'vendor', 'VENDORED.txt'),
                   'Copied unchanged from the Smash 4 research repository\'s tools/ folder (the code the clone tool '
                   'runs on).\nTheir comments refer to the research and its test builds; the tool sets their code '
                   'addresses itself\n(sm4shclonetool/exe.py configure()). acmd_info.json: the ACMD command table '
                   '(Sammi Husky\'s SALT, MIT),\nthe game\'s commands only.\n')
        for d in (shots or []):
            for f in sorted(os.listdir(d)):
                if f.endswith('.png'):
                    z.write(os.path.join(d, f), os.path.join(TOP, 'screenshots', f))
    print('wrote %s (%d bytes)' % (out, os.path.getsize(out)))


def standalone_check(zpath, exe):
    tmp = tempfile.mkdtemp(prefix='s4ct_pkg_')
    try:
        zipfile.ZipFile(zpath).extractall(tmp)
        cli = os.path.join(tmp, TOP, 'cli.py')
        r = subprocess.run([sys.executable, '-I', cli, 'info', '--exe', exe], cwd=tmp, capture_output=True, text=True)
        print(r.stdout.strip()[:400], r.stderr.strip()[-800:])
        r2 = subprocess.run([sys.executable, '-I', '-c', 'import sys; sys.path.insert(0, %r); '
                             'from sm4shclonetool import _paths; import kind_expand, nut, add_fighter; '
                             'print(_paths.LIB); print(kind_expand.__file__)' % os.path.join(tmp, TOP)],
                            cwd=tmp, capture_output=True, text=True)
        print(r2.stdout.strip(), r2.stderr.strip()[-400:])
        ok = r.returncode == 0 and os.path.join(tmp, TOP, 'vendor') in r2.stdout
        print('standalone check: %s' % ('ok' if ok else 'FAILED'))
        return ok
    finally:
        shutil.rmtree(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--screenshots', action='append', help='default: ./screenshots')
    ap.add_argument('--check-exe')
    a = ap.parse_args()
    build(a.out, a.screenshots or [os.path.join(HERE, 'screenshots')])
    if a.check_exe:
        sys.exit(0 if standalone_check(a.out, a.check_exe) else 1)


if __name__ == '__main__':
    main()
