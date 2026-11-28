#!/usr/bin/env python3
"""Build the standalone Sm4shCloneTool zip: the tool, its vendor/ modules (make_vendor.py), the launchers, the README,
the licences, the screenshots and (1.5) the Aroma plugin (aroma/: source, Makefile, the built .wps). No game data.

  python3 make_package.py OUT.zip [--screenshots DIR] [--check-exe VANILLA.rpx]

--check-exe: unpack the zip into a temporary folder and run its CLI there with `python -I` (nothing but the package
on the path) on that executable.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = 'Sm4shCloneTool'
FILES = ['cli.py', 'gui.py', 'setup.bat', 'run.bat', 'run_cli.bat', 'requirements.txt', 'README.md', 'LICENSE.txt',
         'THIRD_PARTY.txt']
FONTS = ['DF_Mincho_SU.ttf', 'DF_Gothic_SU.ttf']
AROMA = ['README.md', 'Makefile', 'src/main.c', 'src/patch_core.c', 'src/patch_core.h', 'src/cave.S', 'sm4shclonetool.wps']


def build(out, shots):
    if os.path.exists(out):
        os.unlink(out)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for sub in ('sm4shclonetool', 'vendor'):
            for root, ds, fs in os.walk(os.path.join(HERE, sub)):
                ds[:] = [d for d in ds if d != '__pycache__']
                for f in sorted(fs):
                    if f.endswith(('.py', '.json', '.txt')):
                        p = os.path.join(root, f)
                        z.write(p, os.path.join(TOP, os.path.relpath(p, HERE)))
        for f in FILES:
            z.write(os.path.join(HERE, f), os.path.join(TOP, f))
        for rel in AROMA:                                   # (1.5) the Aroma plugin: its source and the built plugin
            p = os.path.join(HERE, 'aroma', rel)
            if os.path.exists(p):
                z.write(p, os.path.join(TOP, 'aroma', rel))
            elif rel.endswith('.wps'):
                print('NOTE: aroma/%s is not built: the package has the plugin\'s source only' % rel)
        for f in FONTS + ['FONTS_NOTICE.txt']:              # the bundled fonts (fonts/FONTS_NOTICE.txt)
            z.write(os.path.join(HERE, 'fonts', f), os.path.join(TOP, 'fonts', f))
        for d in shots:
            for f in sorted(os.listdir(d)):
                if f.endswith('.png'):
                    z.write(os.path.join(d, f), os.path.join(TOP, 'screenshots', f))
    print('wrote %s (%d bytes)' % (out, os.path.getsize(out)))


def standalone_check(zpath, exe):
    tmp = tempfile.mkdtemp(prefix='s4ct_pkg_')
    try:
        zipfile.ZipFile(zpath).extractall(tmp)
        top = os.path.join(tmp, TOP)
        r = subprocess.run([sys.executable, '-I', os.path.join(top, 'cli.py'), 'info', '--exe', exe], cwd=tmp,
                           capture_output=True, text=True)
        print(r.stdout.strip()[:400], r.stderr.strip()[-800:])
        r2 = subprocess.run([sys.executable, '-I', '-c', 'import sys; sys.path.insert(0, %r); '
                             'from sm4shclonetool import _paths; import kind_expand, nut, add_fighter; '
                             'print(kind_expand.__file__)' % top], cwd=tmp, capture_output=True, text=True)
        print(r2.stdout.strip(), r2.stderr.strip()[-400:])
        ok = r.returncode == 0 and os.path.join(top, 'vendor') in r2.stdout
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
