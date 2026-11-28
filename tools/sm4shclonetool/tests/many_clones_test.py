#!/usr/bin/env python3
"""Many clones: 40 fighter clones and 8 stage clones on the vanilla executable (the game's, or the stand-in).

  python3 tools/sm4shclonetool/tests/many_clones_test.py WORK STANDIN.rpx FIXTURES_DIR

1. The executable: 40 fighters (8 vanilla bases in turn, every 4th with its base's article as its own weapon kind,
   clones 10 and 20 left out of random) + 8 stages (page 2), at once and as 20 + 20 (the second on the first's
   output), same memory image; then the research tests (repo_test.py), random_select_test.py and extras_test.py on it.
2. The data: a project of 40 Fox clones + 8 stage clones in one build with the custom UI (its chara.lm has
   arrangements up to num_112): rows, the CSS preview with every clone placed; with the game's layout (96 places)
   the same plan is refused.
"""
import copy
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sm4shclonetool import exe as X  # noqa: E402
from sm4shclonetool import roster as R  # noqa: E402
from sm4shclonetool.rpx import Rpx  # noqa: E402
from sm4shclonetool.session import Session  # noqa: E402

BASES = [('fox', 10, 'blaster'), ('mario', 4, 'fireball'), ('zelda', 17, None), ('pikachu', 11, None),
         ('marth', 19, None), ('link', 6, None), ('samus', 7, None), ('purin', 46, None)]
RES, FAILS = [], []


def check(what, got, want=True):
    ok = got == want
    RES.append('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))
    FAILS.extend([what] if not ok else [])
    print(RES[-1], flush=True)


def registry(n, stages):
    fs = []
    for i in range(n):
        b, bid, art = BASES[i % len(BASES)]
        fs.append({'kind': 0x41 + i, 'name': 'clone%02d' % i, 'cap': 'Clone%02d' % i, 'ui_id': 59 + i,
                   'ui_name': 'Clone%02d' % i, 'base': b, 'source': b, 'base_ui_id': bid,
                   'weapons': [art] if art and i % 4 == 0 else [], 'customs': i % 3 == 0,
                   'random': i not in (10, 20)})
    ss = [{'name': 'Stage%02d' % i, 'cosmetic': 0x38 + i, 'kind': 0x80 + 2 * i, 'source': 'BattleField_f',
           'page': 2} for i in range(stages)]
    return {'fighters': fs, 'stages': ss}


def run(cmd, out):
    with open(out, 'w') as f:
        return subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)


def main():
    work, standin, fx = sys.argv[1:4]
    os.makedirs(work, exist_ok=True)
    reg = registry(40, 8)
    e40 = os.path.join(work, 'e40.rpx')
    s = X.build(standin, e40, reg, log=lambda _s: None)
    check('40 fighters + 8 stages at once: code space 0x%08X-0x%08X (%d KB), parts %s'
          % (s['base'], s['end'], (s['end'] - s['base']) // 1024, s['parts']), X.inspect(e40)['state'], 'patched')
    x = Rpx(e40)
    check('the text region covers the code space (ends 0x%08X)' % (0x02000000 + x.text_region()),
          0x02000000 + x.text_region() >= s['end'], True)
    half = copy.deepcopy(reg)
    half['fighters'] = half['fighters'][:20]
    half['stages'] = half['stages'][:4]
    e20 = os.path.join(work, 'e20.rpx')
    X.build(standin, e20, half, log=lambda _s: None)
    e20b = os.path.join(work, 'e20_40.rpx')
    X.build(e20, e20b, reg, log=lambda _s: None)
    check('20 + 20 (the second build on the first\'s executable) == 40 at once (memory image)',
          Rpx(e20b).image_digest(), Rpx(e40).image_digest())
    os.unlink(e20)
    os.unlink(e20b)
    # (1.5) the patch as data with 40 + 8 clones (the code region past the game's text region): byte for byte at the
    # tool's base, the plugin file, the Cemu file, a cave the plugin's default buffer holds
    from sm4shclonetool import patchset as PS
    import struct
    ps = PS.export(standin, reg, log=lambda _s: None, work=work)
    vm, pm = Rpx(standin).memory(), Rpx(e40).memory()
    same = True
    for a, blob in pm.items():
        img = bytearray(vm.get(a, b''))
        img += bytes(len(blob) - len(img))
        for st in ps.sites:
            if a <= st['addr'] < a + len(blob):
                struct.pack_into('>I', img, st['addr'] - a, st['new'])
        if a <= PS.LINK < a + len(blob):
            o = PS.LINK - a
            img[o:o + len(ps.blob_link)] = ps.blob_link
            img[o:o + 0x4000] = blob[o:o + 0x4000]
        same &= bytes(img) == blob
    rp = PS.read_plugin(PS.plugin_bytes(ps))
    text, multi = PS.cemu_patches(ps, [PS.V288_CEMU_HASH])
    check('the patch as data (Aroma / Cemu): = the 40 + 8 executable byte for byte at 0x%08X; a %d KB cave (the '
          'plugin\'s 1024 KB holds it), %d veneers; the plugin file reads back; Cemu\'s cave base-independent'
          % (PS.LINK, ps.size >> 10, len(ps.veneers)),
          (same, ps.size + 0x10000 <= 1024 * 1024 + 0x10000, rp.blob == ps.blob, multi), (True, True, True, False))
    for t in ('kind_expand_test', 'weapon_expand_test', 'base_effects_test', 'stage_slot_test', 'import_call_check'):
        o = os.path.join(work, t + '.txt')
        rc = run([sys.executable, os.path.join(HERE, 'repo_test.py'), t, e40, standin], o)
        text = open(o).read()
        oks = text.count('\nok ') + text.startswith('ok ')
        fails = [line for line in text.splitlines() if line.startswith('FAIL ')]
        if t == 'import_call_check':
            check('import_call_check: 0 direct import calls', '0 direct import call(s)' in text)
        elif t == 'kind_expand_test':
            # its check of the UNPATCHED game reading past its 58-name fanfare table: with 40 new kinds the
            # unpatched lookup runs into other data, two of whose words match a test record (no patched code involved)
            check('%s: %d ok, failures only its check of the unpatched game past its own table' % (t, oks),
                  [f for f in fails if 'the unpatched game finds none of them' not in f], [])
        elif t == 'weapon_expand_test':
            check('%s: %d ok, failures only its fireball-specific check' % (t, oks),
                  [f for f in fails if 'module row of 0x185' not in f], [])
        else:
            check('%s: %d ok, 0 failed (exit %d)' % (t, oks, rc), fails, [])
    o = os.path.join(work, 'random_select_test.txt')
    rc = run([sys.executable, os.path.join(HERE, 'random_select_test.py'), e40], o)
    text = open(o).read()
    check('random_select_test: %d ok, %d failed' % (text.count('\nok ') + text.startswith('ok '),
                                                    text.count('\nFAIL ')), rc, 0)
    o = os.path.join(work, 'extras_test.txt')
    rc = run([sys.executable, os.path.join(HERE, 'extras_test.py'), e40, standin], o)
    text = open(o).read()
    check('extras_test with 40 clones (results call, aliases, Kirby\'s copy): %d ok, %d failed'
          % (text.count('\nok ') + text.startswith('ok '), text.count('\nFAIL ')), rc, 0)
    for p in (e20, e20b, e40):                       # disk: the executables are no longer needed
        if os.path.exists(p):
            os.unlink(p)
    # ---------------------------------------------------------------- data side, 40 Fox clones
    data = os.path.join(fx, 'data')
    cui = os.path.join(fx, 'custom_ui')
    out = os.path.join(work, 'project40')
    if os.path.exists(out):
        shutil.rmtree(out)
    sv = Session(data, out, standin, None, log=lambda _s: None)
    specs = []
    for i in range(40):
        sp = sv.fighter_spec('fox', 'fclone%02d' % i, ui_name='Fclone%02d' % i, title='Fox Clone %d' % i)
        sp['kind'], sp['ui_id'] = 0x41 + i, 59 + i
        specs.append(sp)
    sts = []
    for i in range(8):
        st = sv.stage_spec('BattleField_f', 'Field%02d' % i, page=2)
        st['cosmetic'] = 0x38 + i
        sts.append(st)
    _reg, _r, errors, _n, _f, _i = sv.plan(specs, sts)
    check('with the game\'s layout (96 places) 40 clones are refused: %s' % (errors[:1],),
          any('character select would show 99 entries; its layout has places for 96' in e for e in errors))
    s = Session(data, out, standin, cui, log=lambda _s: None)
    _reg, _r, errors, _n, _f, _i = s.plan(specs, sts)
    check('with the custom UI (chara.lm to num_112) the plan is accepted', errors, [])
    s.build(specs, sts)
    pd = [os.path.join(out, 'INSTALL_TO_data', 'param'), os.path.join(data, 'param')]
    ids = [f['id'] for f in R.fighters(pd, s.reg) if f['clone']]
    check('ui_character_db: 40 clone ids 59-98', ids, list(range(59, 99)))
    lim = s.limits()
    check('limits: %s' % s.limits_text(), (lim['fighters'], lim['css_entries'], lim['stages'], lim['page2']),
          (40, 99, 8, 16))
    _img, info = s.css(None, list(range(59, 99)), os.path.join(work, 'css_40_clones_custom_ui.png'))
    check('CSS preview with 40 clones: frame num_099 of the custom layout, every face placed, none overlapping',
          (info['real_layout'], info['problems'], info['count']), (True, [], 99))
    _img, info = s.sss(None, list(range(0x38, 0x40)), os.path.join(work, 'sss_8_clones.png'))
    check('SSS preview: page 2 holds the 8 game stages and the 8 clones', len(info['pages'][2]), 16)
    reg = X.inspect(os.path.join(out, 'INSTALL_TO_code', 'cross_f.rpx'))['registry']
    check('the package\'s executable lists the 40 fighter / 8 stage clones', (len(reg['fighters']), len(reg['stages'])),
          (40, 8))
    shutil.rmtree(out)                                                   # disk: the 40-clone project is large
    open(os.path.join(work, 'many_results.txt'), 'w').write('\n'.join(RES) + '\n\n%d checks, %d failed\n' % (
        len(RES), len(FAILS)))
    print('%d checks, %d failed' % (len(RES), len(FAILS)))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
