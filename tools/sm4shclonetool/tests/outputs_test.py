#!/usr/bin/env python3
"""1.5.2: a built project's clones written again for another executable output (SD card / Cemu / patched rpx).

  python3 outputs_test.py WORK DATA VANILLA.rpx

DATA: run_all's fixture data folder (WORK_OF_RUN_ALL/fx/data). Prints ok / FAIL lines; exit 1 on a failure.
"""
import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
from sm4shclonetool import exe as X  # noqa: E402
from sm4shclonetool import patchset as PS  # noqa: E402
from sm4shclonetool.session import Session  # noqa: E402

FAILS = []


def check(what, got, want=True):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)), flush=True)
    if not ok:
        FAILS.append(what)
    return ok


def tree(d):
    out = {}
    if os.path.isdir(d):
        for root, _ds, fs in os.walk(d):
            for f in fs:
                p = os.path.join(root, f)
                out[os.path.relpath(p, d)] = hashlib.sha1(open(p, 'rb').read()).hexdigest()
    return out


def main():
    work, data, van = sys.argv[1:4]
    out = os.path.join(work, 'project')
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(work, exist_ok=True)
    quiet = lambda _s: None  # noqa: E731
    sess = lambda exe, o: Session(data, out, exe, None, log=quiet, exe_output=o)  # noqa: E731

    # built for the SD card (Aroma) only
    s = sess(van, 'aroma')
    try:
        s.rebuild_outputs()
        refused = None
    except X.ExeError as e:
        refused = str(e)
    check('a project with no clones: "rebuild outputs" is refused', bool(refused and 'no clones' in refused), True)
    s.build([s.fighter_spec('fox', 'foxclone', ui_name='Foxclone', title='Fox Clone')])
    s = sess(van, 'aroma')
    check('built for the SD card: the package has the Aroma output only', s.present_outputs(), ('aroma',))
    data1 = tree(os.path.join(out, 'INSTALL_TO_data'))
    sd1 = tree(os.path.join(out, 'INSTALL_TO_sd'))
    reg1 = s.reg

    # later: Cemu
    s = sess(van, 'cemu')
    s.rebuild_outputs()
    s = sess(van, 'cemu')
    check('rebuilt for Cemu: the package has Aroma and Cemu', s.present_outputs(), ('aroma', 'cemu'))
    check('... the SD files are the same (made again from the same clones)', tree(os.path.join(out, 'INSTALL_TO_sd')),
          sd1)
    check('... the data files untouched, the clones the same', (tree(os.path.join(out, 'INSTALL_TO_data')) == data1,
                                                               s.reg == reg1), (True, True))
    gp = os.path.join(out, 'INSTALL_TO_cemu', 'graphicPacks', 'Sm4shCloneTool_Clones')
    check('... the Cemu graphic pack is there', sorted(os.listdir(gp)), ['patches.txt', 'rules.txt'])

    # later: a patched rpx
    s = sess(van, 'rpx')
    s.rebuild_outputs()
    s = sess(van, 'rpx')
    pk = os.path.join(out, 'INSTALL_TO_code', 'cross_f.rpx')
    info = X.inspect(pk)
    check('rebuilt as a patched rpx: all three outputs; the rpx is patched with the clone',
          (s.present_outputs(), info['state'], [f['name'] for f in info['registry']['fighters']]),
          (('rpx', 'aroma', 'cemu'), 'patched', ['foxclone']))
    ref = os.path.join(work, 'ref.rpx')
    X.build(van, ref, reg1, log=quiet)
    check('... the rpx is the one a build straight from the game\'s executable makes',
          Rpx_digest(pk), Rpx_digest(ref))
    os.unlink(ref)

    # the project reading the package's own patched rpx; switching to the SD card no longer deletes it
    sd2 = sd_patches(out)
    s = sess(pk, 'aroma')
    s.rebuild_outputs()
    check('the executable read is the package\'s own patched rpx: rebuilding for the SD card keeps it',
          os.path.exists(pk), True)
    check('... and the SD patch files patch the same words with the same cave as from the game\'s own executable (only '
          'the record of the file they were made from differs)', sd_patches(out), sd2)

    cemu1 = open(os.path.join(gp, 'patches.txt')).read()
    # a new clone afterwards: every output the package has gets it (none left with the older set)
    s = sess(pk, 'rpx')
    s.build([s.fighter_spec('szerosuit', 'zssclone', ui_name='Zssclone', title='Zero Clone')])
    names = ['foxclone', 'zssclone']
    pd = os.path.join(out, 'INSTALL_TO_sd', 'wiiu', 'sm4shclonetool')
    aroma = [PS.read_plugin(open(os.path.join(pd, f), 'rb').read()).meta['fighters'] for f in sorted(os.listdir(pd))]
    cemu = open(os.path.join(gp, 'patches.txt')).read()
    reg2 = Session(data, out, pk, None, log=quiet).reg
    want = PS.cemu_patches(PS.export(pk, reg2, quiet, work=work), [PS.V288_CEMU_HASH])[0]
    check('a clone added with only "patched rpx" chosen: the rpx and every Aroma patch file have both clones, the Cemu '
          'pack is the one made for both',
          ([f['name'] for f in X.inspect(pk)['registry']['fighters']], aroma, cemu == want, cemu == cemu1),
          (names, [names] * len(aroma), True, False))
    shutil.rmtree(out)
    print('%d failed' % len(FAILS))
    sys.exit(1 if FAILS else 0)


def sd_patches(out):
    """the Aroma patch files decoded: what the plugin applies (meta without source_sha1, the input file's SHA-1, which
    the plugin doesn't read)"""
    pd = os.path.join(out, 'INSTALL_TO_sd', 'wiiu', 'sm4shclonetool')
    got = {}
    for f in sorted(os.listdir(pd)):
        ps = PS.read_plugin(open(os.path.join(pd, f), 'rb').read())
        meta = {k: v for k, v in ps.meta.items() if k != 'source_sha1'}
        got[f] = (repr(ps.sites), hashlib.sha1(ps.blob).hexdigest(), repr(ps.cave_relocs), repr(sorted(meta.items())),
                  repr(ps.titles), ps.version)
    return got


def Rpx_digest(p):
    from sm4shclonetool.rpx import Rpx
    return Rpx(p).image_digest()


if __name__ == '__main__':
    main()
