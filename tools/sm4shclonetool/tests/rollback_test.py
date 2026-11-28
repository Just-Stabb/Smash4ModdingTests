#!/usr/bin/env python3
"""1.5.1: a build that stops part way leaves nothing behind; a package a stopped build broke (before 1.5.1) is repaired.

  python3 rollback_test.py WORK DATA VANILLA.rpx [PNG]

DATA: run_all's fixture data folder (WORK_OF_RUN_ALL/fx/data). Prints ok / FAIL lines; exit 1 on a failure.
"""
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
from sm4shclonetool import exe as X  # noqa: E402
from sm4shclonetool import fighter as F  # noqa: E402
from sm4shclonetool import rollback as RB  # noqa: E402
from sm4shclonetool import roster as R  # noqa: E402
from sm4shclonetool.session import Session  # noqa: E402

FAILS = []
SKIP = {'README.txt', R.PROJECT}


def check(what, got, want=True):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)), flush=True)
    if not ok:
        FAILS.append(what)
    return ok


def tree(d, skip=()):
    out = {}
    for root, ds, fs in os.walk(d):
        ds[:] = [x for x in ds if x != RB.SNAP]
        for f in fs:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, d)
            if rel in skip:
                continue
            out[rel] = hashlib.sha1(open(p, 'rb').read()).hexdigest()
    return out


def diff(a, b):
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


class Boom(Exception):
    pass


def unit(work):
    """the transaction on its own: every way a build writes"""
    d = os.path.join(work, 'unit')
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(os.path.join(d, 'A', 'sub'))
    for rel, data in (('A/x.bin', b'x' * 100), ('A/sub/y.bin', b'y' * 50), ('A/z.bin', b'z'), ('top.txt', b't'),
                      ('A/gone/keep.bin', b'k')):
        os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
        open(os.path.join(d, rel), 'wb').write(data)
    before = tree(d)

    def writes():
        open(os.path.join(d, 'A', 'x.bin'), 'wb').write(b'changed')             # truncate
        with open(os.path.join(d, 'A', 'sub', 'y.bin'), 'r+b') as f:            # in place
            f.write(b'Q')
        open(os.path.join(d, 'top.txt'), 'a').write('more')                       # append
        shutil.copyfile(os.path.join(d, 'top.txt'), os.path.join(d, 'A', 'z.bin'))  # copy over
        pathlib.Path(d, 'A', 'p.bin').write_bytes(b'new')                         # pathlib, new
        pathlib.Path(d, 'A', 'sub', 'y.bin').write_bytes(b'pathlib')              # pathlib over
        shutil.rmtree(os.path.join(d, 'A', 'gone'), ignore_errors=True)
        os.makedirs(os.path.join(d, 'NEW', 'deep'), exist_ok=True)
        open(os.path.join(d, 'NEW', 'deep', 'n.bin'), 'wb').write(b'n')
        tmp = os.path.join(d, 'r.tmp')
        open(tmp, 'wb').write(b'r')
        os.replace(tmp, os.path.join(d, 'top.txt'))

    try:
        with RB.Transaction(d, log=lambda _s: None):
            writes()
            raise Boom('test')
    except Boom:
        pass
    check('transaction: after an error the folder is exactly as before (truncate, r+, append, copy over, pathlib, '
          'rmtree, new folders, replace)', diff(before, tree(d)), [])
    check('transaction: no snapshot left after the error', os.path.exists(os.path.join(d, RB.SNAP)), False)
    check('transaction: open() is the built-in again', open is RB._orig_open, True)
    with RB.Transaction(d, log=lambda _s: None):
        writes()
    after = tree(d)
    os.makedirs(os.path.join(d, 'A', 'gone'))
    open(os.path.join(d, 'A', 'gone', 'keep.bin'), 'wb').write(b'k')
    check('transaction: on success the changes stay and the snapshot is gone',
          (after.get('NEW/deep/n.bin') is not None, 'A/gone/keep.bin' in after, os.path.exists(os.path.join(d, RB.SNAP))),
          (True, False, False))
    # cut off (no __exit__): the next open of the project puts it back
    before = tree(d)
    t = RB.Transaction(d, log=lambda _s: None)
    t.__enter__()
    writes()
    open(os.path.join(d, 'A', 'x.bin'), 'wb').write(b'again')
    RB._active.clear()
    RB._uninstall()
    check('cut off: the snapshot is left behind', os.path.exists(os.path.join(d, RB.SNAP)), True)
    msgs = []
    check('cut off: recover() reports it', RB.recover(d, msgs.append), True)
    check('cut off: recover() puts the folder back', diff(before, tree(d)), [])
    # cut off while putting back: running it again finishes it
    t = RB.Transaction(d, log=lambda _s: None)
    t.__enter__()
    writes()
    RB._active.clear()
    RB._uninstall()
    snap = os.path.join(d, RB.SNAP)
    st = RB._read_state(snap)
    st['restoring'] = True
    RB._write_state(snap, st)
    first = st['top'][0]                       # one entry already moved back
    RB._remove(os.path.join(d, first))
    os.replace(os.path.join(snap, RB.TREE, first), os.path.join(d, first))
    RB.recover(d, lambda _s: None)
    check('cut off while putting back: recovering again finishes it', diff(before, tree(d)), [])
    # cut off while the snapshot was being made (nothing written yet): the folder stays, the snapshot goes
    os.makedirs(os.path.join(snap, RB.TREE))
    RB._write_state(snap, {'complete': False})
    RB.recover(d, lambda _s: None)
    check('cut off while snapshotting: the folder is untouched and the half snapshot removed',
          (diff(before, tree(d)), os.path.exists(snap)), ([], False))
    shutil.rmtree(d)


def main():
    work, data, exe = sys.argv[1:4]
    png = sys.argv[4] if len(sys.argv) > 4 else None
    os.makedirs(work, exist_ok=True)
    unit(work)
    out = os.path.join(work, 'project')
    if os.path.exists(out):
        shutil.rmtree(out)
    quiet = lambda _s: None  # noqa: E731

    s = Session(data, out, exe, None, log=quiet)
    portraits = {}
    if png:
        portraits = {'foxclone': {('chr_00', '01'): os.path.join(png, 'fox_chr_00_01.png')}}
    s.build([s.fighter_spec('fox', 'foxclone', ui_name='Foxclone', title='Fox Clone', after='Fox')], [],
            portraits)
    t1 = tree(out, SKIP)
    p1 = open(os.path.join(out, R.PROJECT)).read()

    # ---------------------------------------------------------------- a step of the fighter build fails
    orig = F.result_panel

    def boom(*a, **k):
        raise Boom('the results panel step failed (test)')
    F.result_panel = boom
    s = Session(data, out, exe, None, log=quiet)
    spec = s.fighter_spec('szerosuit', 'zssclone', ui_name='Zssclone', title='Zero Clone')
    try:
        s.build([spec])
        raised = False
    except Boom:
        raised = True
    F.result_panel = orig
    check('a fighter build failing part way (after its parameters, labels, portraits and folder) raises', raised)
    check('... and leaves the package exactly as before the build', diff(t1, tree(out, SKIP)), [])
    check('... and the project file unchanged', open(os.path.join(out, R.PROJECT)).read(), p1)
    check('... and the session\'s clone list unchanged', [f['name'] for f in s.reg['fighters']], ['foxclone'])
    spec = s.fighter_spec('szerosuit', 'zssclone', ui_name='Zssclone', title='Zero Clone')
    check('... so the same clone plans again with kind 0x42 / id 60 and no error',
          ((spec['kind'], spec['ui_id']), s.plan([spec])[2]), ((0x42, 60), []))

    # ---------------------------------------------------------------- the executable step fails
    xb = X.build

    def xboom(*a, **k):
        raise Boom('the executable step failed (test)')
    X.build = xboom
    try:
        s.build([spec])
        raised = False
    except Boom:
        raised = True
    X.build = xb
    check('a build failing at the executable (every data file written) raises and leaves the package as it was',
          (raised, diff(t1, tree(out, SKIP))), (True, []))

    # ---------------------------------------------------------------- the tool is killed mid-build
    child = ('import sys, os; sys.path.insert(0, %r)\n'
             'from sm4shclonetool import fighter as F\n'
             'from sm4shclonetool.session import Session\n'
             'F.result_panel = lambda *a, **k: os._exit(3)\n'
             's = Session(%r, %r, %r, None, log=lambda _s: None)\n'
             's.build([s.fighter_spec("szerosuit", "zssclone", ui_name="Zssclone", title="Zero Clone")])\n'
             % (TOOL, data, out, exe))
    rc = subprocess.call([sys.executable, '-c', child])
    check('killed mid-build: the process died (exit 3) with the snapshot left',
          (rc, os.path.exists(os.path.join(out, RB.SNAP))), (3, True))
    msgs = []
    s = Session(data, out, exe, None, log=msgs.append)
    check('killed mid-build: opening the project puts the package back', diff(t1, tree(out, SKIP)), [])
    check('killed mid-build: and says so', any('did not finish' in m for m in msgs), True)

    # ---------------------------------------------------------------- then it builds
    spec = s.fighter_spec('szerosuit', 'zssclone', ui_name='Zssclone', title='Zero Clone')
    s.build([spec])
    check('after the failures the clone builds: kind 0x42 / id 60',
          [(f['name'], f['kind'], f['ui_id']) for f in Session(data, out, exe, None, log=quiet).reg['fighters']],
          [('foxclone', 0x41, 59), ('zssclone', 0x42, 60)])
    t2 = tree(out, SKIP)

    # ---------------------------------------------------------------- repair: a package 1.5 left broken
    own = sorted(k for k in t2 if k.startswith('INSTALL_TO_data/fighter/zssclone/') and k.endswith('.bin'))[0]
    edit = os.path.join(out, own)
    open(edit, 'ab').write(b'\0creator edit')          # an edit the creator made to a clone's own file
    t2 = tree(out, SKIP)
    F.result_panel = boom
    s = Session(data, out, exe, None, log=quiet)
    spec = s.fighter_spec('foxclone', 'foxtwo', ui_name='Foxtwo', title='Fox Two')
    reg, recs, errors, _n, _f, _x = s.plan([spec])
    try:
        s._write(reg, recs, None, None)                 # 1.5's build: no transaction
    except Boom:
        pass
    F.result_panel = orig
    broken = tree(out, SKIP)
    s = Session(data, out, exe, None, log=quiet)
    spec = s.fighter_spec('foxclone', 'foxtwo', ui_name='Foxtwo', title='Fox Two')
    errors = s.plan([spec])[2]
    check('broken package (1.5): the next clone is refused (its kind / id / labels taken) and pointed to Repair',
          (len(diff(t2, broken)) > 0, any('kind 0x43' in e or 'id 61' in e for e in errors),
           any('Repair package' in e for e in errors)), (True, True, True))
    check('repair: nothing in the way', s.repair_problems(), [])
    summary = s.repair()
    t3 = tree(out, SKIP)
    check('repair: the package is again exactly what the two good builds made (%d files; the creator\'s edit kept)'
          % len(t3), diff(t2, t3), [])
    dropped = summary['repair']['dropped']
    check('repair: the unfinished clone\'s files dropped (%d), and only its' % len(dropped),
          (len(dropped) > 0, [x for x in dropped if 'foxtwo' not in x.lower()]), (True, []))
    check('repair: no snapshot or old package left',
          sorted(n for n in os.listdir(out) if n.startswith('.')), [])
    s = Session(data, out, exe, None, log=quiet)
    spec = s.fighter_spec('foxclone', 'foxtwo', ui_name='Foxtwo', title='Fox Two')
    check('after the repair the next clone plans with kind 0x43 / id 61 and no error',
          ((spec['kind'], spec['ui_id']), s.plan([spec])[2]), ((0x43, 61), []))
    s.build([spec])
    check('... and builds', [f['name'] for f in Session(data, out, exe, None, log=quiet).reg['fighters']],
          ['foxclone', 'zssclone', 'foxtwo'])
    # a repair that can't run leaves the package as it was
    s = Session(data, out, exe, None, log=quiet)
    before = tree(out, SKIP)
    F.result_panel = boom
    try:
        s.repair()
        raised = False
    except Boom:
        raised = True
    F.result_panel = orig
    check('a repair that fails part way leaves the package as it was', (raised, diff(before, tree(out, SKIP))),
          (True, []))
    shutil.rmtree(out)
    print('%d failed' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
