#!/usr/bin/env python3
"""The Hitbox Viewer's effects (Sm4shCommand v1.5.0), headless: builds the fighter folders effect_viewer_test.cs reads
and the names / lifetimes it expects (independently, from tools/efc.py and tools/ptcl.py), compiles and runs it.

  python3 tools/Sm4shCommand/effect_viewer_test.py BUILT_DIR WORK_DIR --supamario-base DIR --supamario-build DIR
      --kirby DIR --kirby-pac MAIN.pac --kirby-acmd DIR --brave DIR

BUILT_DIR: the built Sm4shCommand (SM4SHCommand.exe, SALT.dll, Events.cfg, Tooltips). Supamario: the base folder (Mario's
model, Mario's scripts) and a build (tools/supamario_*_build.py: motion, scripts, effect); Kirby: a folder with model /
motion, the main.pac with the BraveSword animations and the folder with the Kirby sword build's effect.bin; Hero: the
brave folder (effect, script).
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import efc as EFC  # noqa: E402
import ptcl as PTCL  # noqa: E402

MONO = '/usr/lib/mono/4.5'
CSC = ['dotnet', '/usr/lib/dotnet/sdk/8.0.134/Roslyn/bincore/csc.dll']


def arg(a, name):
    return a[a.index(name) + 1]


def copy(src, dst):
    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
    elif os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)


def lifetime(p, si):
    """the set's play time as the viewer works it out: max over emitters of start + emit start + end + life + random
    life; None when one never stops"""
    best = 0
    ems = [e['data'] for e in p.sets[si]['emitters'] if e['data'] is not None]
    for d in ems:
        one = d[0x2FF] != 0
        start, est, end = (int.from_bytes(d[o:o + 4], 'big', signed=True) for o in (0x448, 0x44C, 0x450))
        life, rnd = (int.from_bytes(d[o:o + 4], 'big', signed=True) for o in (0x4B0, 0x4B4))
        if not one or end >= 0x7FFFFFF or life >= 0x7FFFFFF:
            return None
        best = max(best, max(0, start) + max(0, est) + max(0, end) + max(0, life) + max(0, rnd))
    return best if ems else None


def expect(bank_dir, name, ids):
    e = EFC.Efc(open(os.path.join(bank_dir, name + '.010d0000.efc'), 'rb').read())
    p = PTCL.Ptcl(open(os.path.join(bank_dir, name + '.010d0000.ptcl'), 'rb').read())
    out = []
    for i in ids:
        fl, st, md, _a, _b = e.entries[i & 0xFFFF]
        parts = []
        if st:
            parts.append(p.set_name(st - 1))
        if md:
            parts.append('model ' + e.models[md - 1])
        life = lifetime(p, st - 1) if st else None
        out.append('0x%X\t%s\t%d' % (i, ' + '.join(parts), max(1, life) if life is not None else -1))
    return out


def main():
    a = sys.argv[1:]
    built, work = a[0], a[1]
    fighters = os.path.join(work, 'fighter')
    shutil.rmtree(work, ignore_errors=True)
    sm = os.path.join(fighters, 'supamario')
    base, build = arg(a, '--supamario-base'), arg(a, '--supamario-build')
    for sub in ('model', 'motion', 'script', 'effect'):
        copy(os.path.join(base, sub), os.path.join(sm, sub))
    for sub in ('motion', 'script', 'effect'):
        copy(os.path.join(build, sub), os.path.join(sm, sub))
    kb = os.path.join(fighters, 'kirby')
    copy(os.path.join(arg(a, '--kirby'), 'model'), os.path.join(kb, 'model'))
    copy(arg(a, '--kirby-pac'), os.path.join(kb, 'motion', 'body', 'main.pac'))
    copy(os.path.join(arg(a, '--kirby-acmd'), 'effect.bin'), os.path.join(kb, 'script', 'animcmd', 'body', 'effect.bin'))
    copy(os.path.join(arg(a, '--kirby-acmd'), 'motion.mtable'), os.path.join(kb, 'motion', 'body', 'motion.mtable'))
    br = os.path.join(fighters, 'brave')
    copy(arg(a, '--brave'), br)
    lines = expect(os.path.join(sm, 'effect', 'supamario'), 'supamario',
                   [0x341002F, 0x3410034, 0x3410056, 0x3410031, 0x341002C, 0x341000B])
    lines += expect(os.path.join(br, 'effect', 'brave'), 'brave', [0x32C0025, 0x32C000F])
    lines += expect(os.path.join(br, 'effect', 'brave'), 'brave', [0x3450078 & 0xFFFF])
    lines[-1] = '0x3450078\t' + lines[-1].split('\t', 1)[1]
    exp = os.path.join(work, 'expect.txt')
    open(exp, 'w').write('\n'.join(lines) + '\n')
    for l in lines:
        print('expect', l)
    test = os.path.join(work, 'run')
    copy(built, test)
    src = os.path.join(HERE, 'effect_viewer_test.cs')
    refs = ['-r:SALT.dll', '-r:SM4SHCommand.exe'] + ['-r:%s/%s.dll' % (MONO, n) for n in (
        'mscorlib', 'System', 'System.Core', 'System.Windows.Forms', 'System.Drawing')]
    subprocess.check_call(CSC + ['-nologo', '-out:EvTest.exe', '-nostdlib'] + refs + [src], cwd=test)
    # (Runtime and the Viewport are WinForms: an X display, xvfb-run when there's none)
    cmd = ['mono', 'EvTest.exe', 'Events.cfg', fighters, exp]
    if not os.environ.get('DISPLAY') and shutil.which('xvfb-run'):
        cmd = ['xvfb-run', '-a'] + cmd
    r = subprocess.run(cmd, cwd=test)
    sys.exit(r.returncode)


if __name__ == '__main__':
    main()
