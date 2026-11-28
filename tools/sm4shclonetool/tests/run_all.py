#!/usr/bin/env python3
"""Sm4shCloneTool end-to-end tests (headless), on a vanilla stand-in executable and vanilla data.

  python3 tools/sm4shclonetool/tests/run_all.py WORK VANILLA.rpx VPARAM VUI VFIGHTER SOUND_CONFIG [CUSTOM_CHR]

VANILLA.rpx: the game's v288 cross_f.rpx (1.3 on; never in the repository: the tests take its path). A modded executable
instead (the 1.2 way) is turned into a stand-in by make_vanilla_standin.py.
WORK gets the fixtures (make_fixtures.py), three builds into one
project (1: Fox -> foxclone with its own article, custom moves, PNG portraits, placed after Fox, + stage
BattleField_f -> CloneField; 2: on build 1's executable, Zero Suit Samus -> zssclone with her portraits re-ID'd;
3: on build 2's executable, foxclone -> foxtwo, a clone of a clone), and results.txt. Repository only.
"""
import copy
import json
import re
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
TOOLS = os.path.dirname(TOOL)
sys.path.insert(0, TOOL)
from sm4shclonetool import exe as X  # noqa: E402
from sm4shclonetool import roster as R  # noqa: E402
from sm4shclonetool import preview as P  # noqa: E402
from sm4shclonetool.rpx import Rpx, sha1_file  # noqa: E402
from sm4shclonetool.session import Session  # noqa: E402
import s4param  # noqa: E402
import msbt  # noqa: E402

RES = []
FAILS = []


def check(what, got, want=True):
    ok = got == want
    RES.append('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))
    if not ok:
        FAILS.append(what)
    print(RES[-1], flush=True)
    return ok


def run(cmd, out):
    with open(out, 'w') as f:
        return subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)


def main():
    work, modded, vparam, vui, vfighter, sconf = sys.argv[1:7]
    custom = sys.argv[7] if len(sys.argv) > 7 else None
    os.makedirs(work, exist_ok=True)
    fx = os.path.join(work, 'fx')
    run([sys.executable, os.path.join(HERE, 'make_fixtures.py'), fx, vparam, vui, vfighter, sconf] +
        ([custom] if custom else []), os.path.join(work, 'fixtures.txt'))
    if os.path.exists(modded) and X.inspect(modded)['state'] == 'vanilla':
        standin = modded                       # the game's own executable
        modded = os.path.join(work, 'modified.rpx')
        mx = Rpx(standin)
        mx.w32(0x02A65898, 0x60000000)          # one word the tool hooks changed: another mod's executable
        mx.save(modded)
    else:
        standin = os.path.join(work, 'vanilla_standin.rpx')
        if not os.path.exists(standin):
            run([sys.executable, os.path.join(HERE, 'make_vanilla_standin.py'), modded, standin],
                os.path.join(work, 'standin.txt'))
        else:
            run([sys.executable, os.path.join(HERE, 'make_vanilla_standin.py'), '--others', standin],
                os.path.join(work, 'standin.txt'))
    data, png = os.path.join(fx, 'data'), os.path.join(fx, 'png')
    out = os.path.join(work, 'project')
    if os.path.exists(out):
        import shutil
        shutil.rmtree(out)
    log = open(os.path.join(work, 'build_log.txt'), 'w')
    say = lambda s: log.write(s + '\n')  # noqa: E731

    # ---------------------------------------------------------------- executable state
    info = X.inspect(standin)
    check('the vanilla executable inspects as vanilla%s' % (' (the game\'s v288: SHA-1 %s)' % info['sha1']
                                                            if info.get('v288') else ' (a stand-in)'),
          info['state'], 'vanilla')
    check('a modified executable is refused (a hooked word changed)', X.inspect(modded)['state'], 'modified')

    # ---------------------------------------------------------------- build 1
    s = Session(data, out, standin, None, log=say)
    f1 = s.fighter_spec('fox', 'foxclone', ui_name='Foxclone', title='Fox Clone', weapons=['blaster'], customs=True,
                        after='Fox', titles={'us_fr': {'title': 'Renard Clone'}})
    st = s.stage_spec('BattleField_f', 'CloneField', title='Clone Field')
    portraits = {'foxclone': {(set_, '01'): os.path.join(png, 'fox_%s_01.png' % set_)
                              for set_ in ('chr_00', 'chr_10', 'chr_11', 'chr_13', 'stock_90')}}
    portraits['foxclone'][('chr_00', '02')] = os.path.join(png, 'fox_chr_00_02.png')
    s.build([f1], [st], portraits, {'CloneField': {'stage_10': os.path.join(png, 'clone_stage_10.png')}})
    e1 = os.path.join(work, 'e1.rpx')
    _copy(os.path.join(out, 'INSTALL_TO_code', 'cross_f.rpx'), e1)
    check('build 1: a valid RPX (every section\'s CRC, zlib sizes, file info: %s)' % rpx_valid(e1), rpx_valid(e1), 'valid')
    check('build 1: executable patched, 1 fighter + 1 stage in its marker',
          [X.inspect(e1)['state'], len(X.inspect(e1)['registry']['fighters']), len(X.inspect(e1)['registry']['stages'])],
          ['patched', 1, 1])
    # ---------------------------------------------------------------- build 2 (incremental)
    s = Session(data, out, e1, None, log=say)
    f2 = s.fighter_spec('szerosuit', 'zssclone', ui_name='Zssclone', title='Zero Clone')
    s.build([f2])
    e2 = os.path.join(work, 'e2.rpx')
    _copy(os.path.join(out, 'INSTALL_TO_code', 'cross_f.rpx'), e2)
    # ---------------------------------------------------------------- build 3 (a clone of a clone)
    s = Session(data, out, e2, None, log=say)
    f3 = s.fighter_spec('foxclone', 'foxtwo', ui_name='Foxtwo', title='Fox Two', customs=True)
    s.build([f3])
    e3 = os.path.join(work, 'e3.rpx')
    _copy(os.path.join(out, 'INSTALL_TO_code', 'cross_f.rpx'), e3)
    log.close()
    reg = X.inspect(e3)['registry']
    check('build 3: the marker lists foxclone 0x41 / 59, zssclone 0x42 / 60, foxtwo 0x43 / 61 (base fox), CloneField',
          ([(f['name'], f['kind'], f['ui_id'], f['base']) for f in reg['fighters']], [x['name'] for x in reg['stages']]),
          ([('foxclone', 0x41, 59, 'fox'), ('zssclone', 0x42, 60, 'szerosuit'), ('foxtwo', 0x43, 61, 'fox')],
           ['CloneField']))

    # ---------------------------------------------------------------- incremental, idempotent, deterministic
    eall = os.path.join(work, 'eall.rpx')
    X.build(standin, eall, reg, log=lambda _s: None)
    check('three incremental builds == all clones at once (memory image)', Rpx(e3).image_digest(),
          Rpx(eall).image_digest())
    again = os.path.join(work, 'e3b.rpx')
    X.build(e3, again, reg, log=lambda _s: None)
    check('patching again with the same clones changes no byte', sha1_file(again), sha1_file(e3))
    r1 = os.path.join(work, 'e1b.rpx')
    X.build(standin, r1, X.inspect(e1)['registry'], log=lambda _s: None)
    check('build 1 rebuilds byte for byte from the stand-in and its registry', sha1_file(r1), sha1_file(e1))
    check('build 3: a valid RPX (CRCs, zlib sizes, file info)', rpx_valid(e3), 'valid')
    for p in (eall, again, r1):
        os.unlink(p)

    # ---------------------------------------------------------------- only the tool's words differ from vanilla
    base, rec = X.find_marker(Rpx(e3))
    a, b = Rpx(standin).memory(), Rpx(e3).memory()
    orig = {int(k, 16) for k in rec['orig']}
    stray = []
    for addr, blob in b.items():
        old = a.get(addr, b'')
        for o in range(0, len(blob), 4):
            w = blob[o:o + 4]
            if old[o:o + 4] != w and not (len(old) <= o and w == b'\0' * 4):     # grown zeros
                at = addr + o
                if not (base <= at < rec['end']) and at not in orig:
                    stray.append(at)
    check('every changed word is in the tool\'s code space (0x%08X-0x%08X) or recorded with its original (%d words)'
          % (base, rec['end'], len(orig)), stray[:5], [])
    va = Rpx(standin)
    vb = Rpx(e3)
    moved = {(m[0], m[1]) for m in rec['relocs']}
    rdiff = []
    for i in va.reloc_sections():
        da, db = va.data(i), vb.data(i)
        for o in range(0, len(da), 12):
            if da[o:o + 12] != db[o:o + 12] and (i, o) not in moved:
                rdiff.append((i, o))
    check('every changed relocation is one the marker records (%d moved)' % len(moved), rdiff[:5], [])
    check('the code space past the game\'s is the tool\'s alone (text ends at its end)', Rpx(e3).text_end(),
          rec['end'])

    # ---------------------------------------------------------------- the research tests on build 3
    for t in ('kind_expand_test', 'weapon_expand_test', 'base_effects_test', 'stage_slot_test', 'import_call_check'):
        o = os.path.join(work, t + '.txt')
        rc = run([sys.executable, os.path.join(HERE, 'repo_test.py'), t, e3, standin], o)
        text = open(o).read()
        oks = text.count('\nok ') + text.startswith('ok ')
        fails = [line for line in text.splitlines() if line.startswith('FAIL ')]
        if t == 'import_call_check':
            check('import_call_check: 0 direct import calls', '0 direct import call(s)' in text, True)
        elif t == 'weapon_expand_test':
            # its one Mario-specific expectation: weapon 0x185's module row is the fireball's (kind 0); here 0x185 is
            # Fox's blaster, whose row is its own
            other = [f for f in fails if 'module row of 0x185' not in f]
            check('%s: %d ok, failures only its fireball-specific check (%d)' % (t, oks, len(fails)), other, [])
        else:
            check('%s: %d ok, 0 failed (exit %d)' % (t, oks, rc), fails, [])
    customs_check(e3, standin)

    # ---------------------------------------------------------------- data
    pkg = os.path.join(out, 'INSTALL_TO_data')
    param_checks(pkg, data, reg)
    m = msbt.Msbt(open(os.path.join(pkg, 'ui', 'message', 'melee.msbt'), 'rb').read())
    check('melee.msbt: names of the three clones and the stage',
          [m.text(x) for x in ('MmelCharaN_01_Foxclone', 'MmelCharaN_01_Zssclone', 'MmelCharaN_01_Foxtwo',
                               'MmelStageN_CloneField')], ['Fox Clone', 'Zero Clone', 'Fox Two', 'Clone Field'])
    z = os.path.join(pkg, 'fighter', 'zssclone')
    check('fighter/zssclone/: the paths the game builds with the name renamed',
          [os.path.exists(os.path.join(z, p)) for p in ('script/msc/zssclone.mscsb', 'effect/zssclone',
                                                        'sound/snd_se_Zssclone.nus3bank', 'sound/snd_vc_Zssclone.nus3bank',
                                                        'script/animcmd/body/effect.bin', 'model/body/c00/model.nud')],
          [True] * 6)
    zrec = [f for f in reg['fighters'] if f['name'] == 'zssclone'][0]
    arts = sorted(d for d in os.listdir(os.path.join(z, 'model')) if d != 'body')
    check('fighter/zssclone/model/: article folders only for its own articles (%s)' % ', '.join(arts),
          set(arts) <= set(zrec['weapons']), True)
    ids = effect_ids(os.path.join(z, 'script', 'animcmd', 'body', 'effect.bin'))
    check('zssclone effect.bin: effect ids moved to bank 0x342 (%d), none left on 0x319' % ids.get(0x42, 0),
          (ids.get(0x42, 0) > 0, ids.get(0x19, 0)), (True, 0))
    two = os.path.join(pkg, 'fighter', 'foxtwo')
    check('fighter/foxtwo/ (a clone of foxclone): its effect folder renamed from foxclone\'s',
          os.path.exists(os.path.join(two, 'effect', 'foxtwo', 'foxtwo.010d0000.efc')), True)
    from sm4shclonetool import textures as T
    zp = sorted(os.listdir(os.path.join(pkg, 'ui', 'replace', 'chr', 'chr_00')))
    check('portraits: chr_00 of every clone (Foxclone 2 imported, Zssclone 8 re-ID\'d, Foxtwo 2 from Foxclone)',
          [len([f for f in zp if '_%s_' % n in f]) for n in ('Foxclone', 'Zssclone', 'Foxtwo')], [2, 8, 2])
    sp = sorted(os.listdir(os.path.join(pkg, 'ui', 'replace', 'chr', 'stock_90')))
    sids = [T.texture_ids(T.read_nut(os.path.join(pkg, 'ui', 'replace', 'chr', 'stock_90', f)))[0][1] for f in sp]
    check('stock icons (stock_90, used by the match HUD and results by UI name and costume): Zssclone\'s 8 costumes, '
          'decodable, texture ids unique (%d files)' % len(sp),
          (len([f for f in sp if '_Zssclone_' in f]), all(T.decode(os.path.join(pkg, 'ui', 'replace', 'chr', 'stock_90',
                                                                                  f)) is not None for f in sp),
           len(set(sids)) == len(sids)), (8, True, True))
    dec = [T.decode(os.path.join(pkg, 'ui', 'replace', 'chr', 'chr_00', f)) for f in zp]
    check('portraits decode (%d chr_00 files)' % len(zp), all(d is not None for d in dec), True)
    own_checks(pkg, data, reg, e3)
    extras_checks(work, out, pkg, data, reg, e3, standin, fx)
    outputs_checks(work, data, reg, e3, standin)
    rollback_checks(work, data, standin, fx)
    switch_checks(work, data, standin)
    st_icon = os.path.join(pkg, 'ui', 'replace', 'stage', 'stage_10', 'stage_10_CloneField.nut')
    check('stage icon stage_10_CloneField.nut: the imported PNG, a new texture id',
          [T.decode(st_icon) is not None, T.texture_ids(T.read_nut(st_icon))[0][1] != 0x28000999], [True, True])
    check('stage folders renamed', [os.path.exists(os.path.join(pkg, 'stage', v, 'CloneField', 'param',
                                                              'CloneField_param.bin')) for v in ('melee', 'end')],
          [True, True])
    readme = open(os.path.join(out, 'README.txt')).read()
    check('package: INSTALL_TO_data, INSTALL_TO_data(us_fr) (the region beside the data folder), INSTALL_TO_code/cross_f.rpx, '
          'README.txt, project file; no wrapper folder',
          sorted(os.listdir(out)), ['INSTALL_TO_code', 'INSTALL_TO_data', 'INSTALL_TO_data(us_fr)', 'README.txt',
                                'Sm4shCommand_names.txt', 'sm4shclonetool_project.json'])
    check('README lists the clones', all(n in readme for n in ('foxclone', 'zssclone', 'foxtwo', 'CloneField')), True)

    # ---------------------------------------------------------------- previews / placement
    pd = [os.path.join(pkg, 'param'), os.path.join(data, 'param')]
    order = [e['id'] for e in R.css_entries(pd, reg)]
    check('CSS order: Foxclone (placed after Fox) right after Fox, then Falco',
          order[order.index(10) + 1:order.index(10) + 3], [59, 22])
    shots = os.path.join(work, 'shots')
    os.makedirs(shots, exist_ok=True)
    _img, iv = P.render_css(pd, [os.path.join(pkg, 'ui'), os.path.join(data, 'ui')], reg, [59, 60, 61],
                            os.path.join(shots, 'css_vanilla_ui.png'))
    check('CSS preview, vanilla UI: no chara.lm -> approximated grid, %d entries' % iv['count'], iv['real_layout'], False)
    if custom:
        cui = os.path.join(fx, 'custom_ui')
        uid = [os.path.join(pkg, 'ui'), cui, os.path.join(data, 'ui')]
        _img, ic = P.render_css(pd, uid, reg, [59, 60, 61], os.path.join(shots, 'css_custom_ui.png'))
        pos, _n = P.lm_layout(os.path.join(cui, 'lumen', 'chara', 'chara.lm'), ic['count'])
        slot = ic['slot'][59]
        check('custom UI: the CSS layout read from its chara.lm frame num_%03d, every face placed, none overlapping'
              % ic['count'], (ic['real_layout'], ic['problems']), (True, []))
        check('custom UI: Foxclone at face_%03d, the place after Fox\'s face_%03d' % (slot, ic['slot'][10]),
              slot, ic['slot'][10] + 1)
        big = copy.deepcopy(reg)
        for i in range(60):
            big['fighters'].append(dict(reg['fighters'][0], name='x%d' % i, ui_id=62 + i, ui_name='X%d' % i,
                                        sort=None))
        _img, ib = P.render_css(pd, uid, big, [], None)
        check('custom UI with more entries than its layout has frames for (%d): reported' % ib['count'],
              bool(ib['problems']) and not ib['real_layout'], True)
    _img, isss = P.render_sss(pd, [os.path.join(pkg, 'ui'), os.path.join(data, 'ui')], reg, [0x38],
                              os.path.join(shots, 'sss_vanilla_ui.png'))
    check('SSS: CloneField on page 1, last', isss['pages'][1][-1], 0x38)

    o = os.path.join(work, 'media_test.txt')
    rc = run([sys.executable, os.path.join(HERE, 'media_test.py'), os.path.join(vui, 'replace', 'chr'), shots], o)
    text = open(o).read()
    check('media_test (DSP-ADPCM encoder = the C one, IDSP / WAV, name plates vs the game\'s, fonts): %d ok (exit %d)'
          % (text.count('\nok ') + text.startswith('ok '), rc), [x for x in text.splitlines() if x.startswith('FAIL')], [])
    open(os.path.join(work, 'results.txt'), 'w').write('\n'.join(RES) + '\n\n%d checks, %d failed\n' % (
        len(RES), len(FAILS)))
    print('%d checks, %d failed' % (len(RES), len(FAILS)))
    sys.exit(1 if FAILS else 0)


def rpx_valid(path):
    """'valid' when every section's data matches the CRC table, compressed sections inflate to their stated size,
    and the file info's text region covers the code section; else what is wrong"""
    import zlib
    import struct as st
    x = Rpx(path)
    d = bytes(x.d)
    crc_idx = next(i for i, s in enumerate(x.secs) if s[1] == 0x80000003)
    crcs = st.unpack('>%dI' % len(x.secs), bytes(x.data(crc_idx))[:4 * len(x.secs)])
    for i, s in enumerate(x.secs):
        if i == crc_idx or not s[5] or s[1] == 8:
            continue
        raw = d[s[4]:s[4] + s[5]]
        if s[2] & 0x08000000:
            n = st.unpack('>I', raw[:4])[0]
            dat = zlib.decompress(raw[4:])
            if len(dat) != n:
                return 'section %d inflates to %d bytes, not %d' % (i, len(dat), n)
        else:
            dat = raw
        if zlib.crc32(dat) & 0xFFFFFFFF != crcs[i]:
            return 'section %d: CRC differs' % i
    if x.text_region() < x.text_end() - 0x02000000:
        return 'the text region (0x%X) ends before the code (0x%08X)' % (x.text_region(), x.text_end())
    return 'valid'


def _copy(a, b):
    import shutil
    shutil.copyfile(a, b)


def own_checks(pkg, data, reg, exe_path):
    """zssclone (the default "fully independent" preset): own sound banks / rows, sound ids, effect bank, articles,
    results panel; the base's files untouched"""
    from sm4shclonetool import sound as SND
    import result_param as RP
    z = [f for f in reg['fighters'] if f['name'] == 'zssclone'][0]
    check('zssclone record: own sound, own effects, own articles %s' % z['weapons'],
          (z.get('own_sound'), z.get('own_effects'), len(z['weapons']) > 0), (True, True, True))
    sd, bd = os.path.join(pkg, 'fighter', 'zssclone', 'sound'), os.path.join(data, 'fighter', 'szerosuit', 'sound')
    t0 = SND.Table(open(os.path.join(data, 'sound', 'config', 'soundlabeltable.bin'), 'rb').read())
    t1 = SND.Table(open(os.path.join(pkg, 'sound', 'config', 'soundlabeltable.bin'), 'rb').read())
    old_ids = {r[0] for r in t0.rows}
    banks, rowmap, same = [], {}, True
    for f in sorted(os.listdir(sd)):
        if not f.endswith('.nus3bank'):
            continue
        new = open(os.path.join(sd, f), 'rb').read()
        old = open(os.path.join(bd, f.replace('Zssclone', 'SZerosuit')), 'rb').read()
        nm, bid = SND.binf(new)
        onm, oid = SND.binf(old)
        banks.append((f, nm, bid))
        same &= [s for s in SND.sections(new) if s[0] != b'BINF'] == [s for s in SND.sections(old) if s[0] != b'BINF']
        if t0.row_of(oid) is not None and not f.startswith('snd_se_vc_Kirby_copy_'):
            rowmap[t0.row_of(oid)] = t1.row_of(bid)
            same &= t1.tones(t1.row_of(bid)) == t0.tones(t0.row_of(oid))
    own = [(f, nm, bid) for f, nm, bid in banks if not f.startswith('snd_se_vc_Kirby_copy_')]
    kc = [(f, nm, bid) for f, nm, bid in banks if f.startswith('snd_se_vc_Kirby_copy_')]
    check('its banks: BINF names = their files, ids new and unique (%s)' % ', '.join('%s %d' % (n, i) for _f, n, i in own),
          all(nm == f[:-9] and bid not in old_ids for f, nm, bid in own) and len({b for _f, _n, b in own}) == len(own),
          True)
    check('its Kirby-copy voice bank has an id of its own (1.4: the base\'s and the clone\'s both load in one match; '
          'the executable lets it answer for the base\'s id) (%s)' % ', '.join('%s %d' % (n, i) for _f, n, i in kc),
          all(bid not in old_ids for _f, _n, bid in kc) and len(kc) > 0, True)
    check('its banks\' tones / packs are the base\'s byte for byte, its rows the base\'s label lists (%s)'
          % ', '.join('%d -> %s' % kv for kv in sorted(rowmap.items())), same and None not in rowmap.values(), True)
    import acmd
    ids, base_ids = [], []
    for root, _ds, fs in os.walk(os.path.join(pkg, 'fighter', 'zssclone', 'script', 'animcmd')):
        for f in fs:
            if f == 'sound.bin':
                a = acmd.ACMDFile.load(os.path.join(root, f))
                for cmds in a.scripts.values():
                    for c in cmds:
                        for i, v in enumerate(c.params):
                            if c.kind(i) != 1 and isinstance(v, int) and v >> 16 in set(rowmap.values()):
                                ids.append(v)
                            if c.kind(i) != 1 and isinstance(v, int) and v >> 16 in rowmap and (v & 0xFFFF) < len(t0.tones(v >> 16)):
                                base_ids.append(v)
    check('its sound.bin files: %d sound ids on its own rows, none left on the base\'s' % len(ids),
          (len(ids) > 0, base_ids[:3]), (True, []))
    spec = X.kind_spec(reg)
    zk = [k for k in spec['kinds'] if k['name'] == 'zssclone'][0]
    check('own effect bank: the generators don\'t load the base\'s banks for it (effects_base false)',
          zk.get('effects_base'), False)
    arts = [a for a in z['weapons'] if os.path.isdir(os.path.join(data, 'fighter', 'szerosuit', 'model', a))]
    check('its own articles\' model folders are under fighter/zssclone/ (%s)' % ', '.join(arts),
          all(os.path.isdir(os.path.join(pkg, 'fighter', 'zssclone', 'model', a)) for a in arts), True)
    rp = open(os.path.join(pkg, 'param', 'ui', 'result_param.bin'), 'rb').read()
    names = [e[0] for e in RP.entries(rp)[1]]
    check('result_param.bin: the clones\' results-panel entries', [n for n in ('foxclone', 'zssclone', 'foxtwo')
                                                                    if n in names], ['foxclone', 'zssclone', 'foxtwo'])
    check('the base\'s files are untouched (no fighter/szerosuit/ in the package)',
          os.path.exists(os.path.join(pkg, 'fighter', 'szerosuit')), False)


def extras_checks(work, out, pkg, data, reg, e3, standin, fx):
    """1.3: the executable's extras (emulated), the announcer call, fanfare, win cameras, Kirby's copy files, voices,
    languages, name plates"""
    from sm4shclonetool import audio as AU
    from sm4shclonetool import languages as L
    from sm4shclonetool import music as MU
    from sm4shclonetool import narration as N
    from sm4shclonetool import sound as SND
    from sm4shclonetool import voices as V
    import add_fighter as A
    o = os.path.join(work, 'extras_test.txt')
    rc = run([sys.executable, os.path.join(HERE, 'extras_test.py'), e3, standin], o)
    text = open(o).read()
    check('extras_test (results call, sound aliases, Kirby\'s copy: emulated): %d ok, 0 failed (exit %d)'
          % (text.count('\nok ') + text.startswith('ok '), rc),
          [x for x in text.splitlines() if x.startswith('FAIL')], [])
    check('extras_test emulated Kirby\'s own copy scripts (the lookup from all three binds) and the own copy bank',
          [sum(1 for x in text.splitlines() if x.startswith('ok') and 'the script lookup from 0x' in x),
           any(x.startswith('ok') and 'copy-handle finder' in x for x in text.splitlines())], [3, True])
    fs = {f['name']: f for f in reg['fighters']}
    # the announcer call
    t0 = SND.Table(open(os.path.join(data, 'sound', 'config', 'soundlabeltable.bin'), 'rb').read())
    t1 = SND.Table(open(os.path.join(pkg, 'sound', 'config', 'soundlabeltable.bin'), 'rb').read())
    b0 = AU.Bank(open(os.path.join(data, N.MAIN_BANK), 'rb').read())
    b1 = AU.Bank(open(os.path.join(pkg, N.MAIN_BANK), 'rb').read())
    row = t0.row_of(b0.binf()[1])
    f = A.ParamEdit([os.path.join(pkg, 'param')], N.CALL_DB)
    ok, n = True, 0
    for c in fs.values():
        e = next(x for x in f.entries() if x[0][1] == c['ui_id'])
        ids = {e[k][1] for k in range(1, len(e))}
        new = {b for _a, b in c.get('call_map') or []}
        for old, nw in c.get('call_map') or []:
            # old: the base's id (in the game's table) or, for a clone of a clone, its source's own label
            ta, tb = t1.tones(old >> 16)[old & 0xFFFF], t1.tones(nw >> 16)[nw & 0xFFFF]
            ok &= b1.data_of(tb) == b1.data_of(ta) and tb >= len(b0.tones) and ta != tb
            n += 1
        ok &= bool(new) and ids <= new | {0}
    check('announcer call: every clone\'s 16 select ids on labels of its own (%d pairs), each a new tone with its '
          'source\'s audio byte for byte (foxtwo: foxclone\'s own call)' % n, ok, True)
    check('announcer call: the bank\'s %d old tones and row 0x%X\'s old labels unchanged; the row grew by the clones\''
          % (len(b0.tones), row),
          ([b1.data_of(i) == b0.data_of(i) for i in range(len(b0.tones)) if b0.tones[i]].count(False),
           t1.tones(row)[:len(t0.tones(row))] == t0.tones(row), len(t1.tones(row)) - len(t0.tones(row))),
          (0, True, sum(len({b for _a, b in c.get('call_map') or []}) for c in fs.values())))
    # the fanfare
    z = fs['zssclone']
    import struct as _st
    fbb = open(os.path.join(pkg, 'sound', 'config', 'bgm_fighter.fbb'), 'rb').read()
    bgm = _st.unpack_from('<I', fbb, 0xC + 0x14 * z['kind'] + 0x10)[0]
    ents = MU.mpb_entries(open(os.path.join(pkg, 'sound', 'config', 'bgm_property.mpb'), 'rb').read())
    ents0 = MU.mpb_entries(open(os.path.join(data, 'sound', 'config', 'bgm_property.mpb'), 'rb').read())
    nm = ents.get(bgm, b'')[:0x3C].rstrip(b'\0').decode()
    fb = os.path.join(pkg, 'sound', 'bgm', 'snd_bgm_%s.nus3bank' % nm)
    src = AU.Bank(open(os.path.join(data, 'sound', 'bgm', 'snd_bgm_Z24_F_ZeroSamus.nus3bank'), 'rb').read())
    check('fanfare: zssclone\'s fbb record -> its own BGM %d (%s, a new bgm_property entry; the old entries unchanged), '
          'its bank a copy of the base\'s audio under its own BINF' % (bgm, nm),
          (bgm not in ents0, z.get('fanfare_bgm') == bgm, all(ents[i] == ents0[i] for i in ents0),
           os.path.exists(fb) and AU.Bank(open(fb, 'rb').read()).data_of(0) == src.data_of(0),
           os.path.exists(fb) and AU.Bank(open(fb, 'rb').read()).binf()[1] != src.binf()[1]),
          (True, True, True, True, True))
    # win cameras, Kirby
    check('win cameras: motion/camera/result/<clone>/ for the clones whose base has them (foxclone, foxtwo, zssclone)',
          [os.path.isdir(os.path.join(pkg, 'motion', 'camera', 'result', n)) for n in ('foxclone', 'foxtwo', 'zssclone')],
          [True, True, True])
    kd = os.path.join(pkg, 'fighter', 'kirby')
    check('Kirby: each clone\'s own copy hat / motions (fighter/kirby/model/<name>cap, motion/<name>body), none of the '
          'base\'s changed', [(os.path.isdir(os.path.join(kd, 'model', n + 'cap')),
                                os.path.isdir(os.path.join(kd, 'motion', n + 'body')), fs[n].get('kirby_hat'))
                               for n in ('foxclone', 'zssclone')] + [os.path.exists(os.path.join(kd, 'model', 'foxear'))],
          [(True, True, 'foxclonecap'), (True, True, 'zssclonecap'), False])
    kirby_script_checks(pkg, fx, fs, out)
    # voices
    ls = V.lines(z, pkg)
    cats = sorted({x['category'] for x in ls})
    check('voices: zssclone\'s lines by category (%s), victory lines found from its win scripts'
          % ', '.join(cats), {'victory', 'taunt', 'cheer', 'KO', 'Kirby copy'} <= set(cats), True)
    import math
    wav = os.path.join(work, 'voice_test.wav')
    AU.write_wav(wav, [int(9000 * math.sin(i * 0.02) * math.sin(i * 0.0005)) for i in range(24000)])
    t = next(x for x in ls if x['category'] == 'taunt')
    base_bank = open(os.path.join(data, 'fighter', 'szerosuit', 'sound', t['file'].replace('Zssclone', 'SZerosuit')),
                     'rb').read()
    blob = V.replace(z, pkg, t['file'], t['tone'], wav)
    rate, ch = AU.idsp_decode(V.tone_data(z, pkg, t['file'], t['tone']))
    import numpy as np
    a, b = np.array(AU.read_wav(wav), float), np.array(ch[0], float)
    snr = 10 * np.log10((a ** 2).sum() / ((a - b) ** 2).sum())
    check('voices: %s replaced by a WAV: decodes at %.1f dB SNR (> 25), the base\'s bank file untouched' % (t['name'], snr),
          (snr > 25, open(os.path.join(data, 'fighter', 'szerosuit', 'sound',
                                       t['file'].replace('Zssclone', 'SZerosuit')), 'rb').read() == base_bank),
          (True, True))
    check('voices: the base\'s ids its code plays answer from its own banks (alias se / vc / cheer = the base\'s ids)',
          z.get('sound_alias', [])[:3], [SND.binf(open(os.path.join(data, 'fighter', 'szerosuit', 'sound', '%s.nus3bank' % f),
                                                       'rb').read())[1] for f in ('snd_se_SZerosuit', 'snd_vc_SZerosuit',
                                                                                  'snd_vc_SZerosuit_ouen')])
    # languages
    miss = L.check_all(reg, data, pkg)
    import msbt
    fr = msbt.Msbt(open(os.path.join(out, 'INSTALL_TO_data(us_fr)', 'ui', 'message', 'melee.msbt'), 'rb').read())
    check('languages: every clone\'s MmelChara labels in every language (%s); foxclone\'s French title its own, the '
          'others the title' % ', '.join(sorted(miss)), (miss, fr.text('MmelCharaN_01_Foxclone'),
                                                         fr.text('MmelCharaN_01_Zssclone')),
          ({k: [] for k in miss}, 'Renard Clone', 'Zero Clone'))


def rollback_checks(work, data, standin, fx):
    """1.5.1: a build that stops part way leaves nothing behind; repairing a package a stopped build broke"""
    o = os.path.join(work, 'rollback_test.txt')
    rc = run([sys.executable, os.path.join(HERE, 'rollback_test.py'), os.path.join(work, 'rollback'), data, standin,
              os.path.join(fx, 'png')], o)
    text = open(o).read()
    check('rollback_test (a failed / killed build leaves the package as it was; repair of a broken 1.5 package): '
          '%d ok, 0 failed (exit %d)' % (text.count('\nok ') + text.startswith('ok '), rc),
          [x for x in text.splitlines() if x.startswith(('FAIL', 'Traceback'))] + ([] if rc == 0 else ['exit %d' % rc]),
          [])


def switch_checks(work, data, standin):
    """1.5.2: a built project rebuilt for another executable output (SD card -> Cemu -> rpx, from the package's own rpx)"""
    o = os.path.join(work, 'outputs_test.txt')
    rc = run([sys.executable, os.path.join(HERE, 'outputs_test.py'), os.path.join(work, 'switch'), data, standin], o)
    text = open(o).read()
    check('outputs_test (a built project written again for the SD card / Cemu / a patched rpx; outputs kept and '
          'refreshed): %d ok, 0 failed (exit %d)' % (text.count('\nok ') + text.startswith('ok '), rc),
          [x for x in text.splitlines() if x.startswith(('FAIL', 'Traceback'))] + ([] if rc == 0 else ['exit %d' % rc]),
          [])


def outputs_checks(work, data, reg, e3, standin):
    """1.5: the executable outputs: the Aroma plugin's patch file and the Cemu graphic pack (patchset_test.py), and
    their packaging (a build with --exe-output all, then aroma only)"""
    from sm4shclonetool import patchset as PS
    from sm4shclonetool import session as SE
    o = os.path.join(work, 'patchset_test.txt')
    rc = run([sys.executable, os.path.join(HERE, 'patchset_test.py'), e3, standin, os.path.join(work, 'patchset'),
              '1000'], o)
    text = open(o).read()
    check('patchset_test (the patch as data: = the patched rpx byte for byte at its base; relocated as the Aroma plugin '
          'and Cemu place it, in the extras / random / custom-move emulations; the plugin\'s C code; the Cemu syntax): '
          '%d ok, 0 failed (exit %d)' % (text.count('\nok ') + text.startswith('ok '), rc),
          [x for x in text.splitlines() if x.startswith('FAIL')] + ([] if rc == 0 else ['exit %d' % rc]), [])
    out2 = os.path.join(work, 'project_outputs')
    if os.path.exists(out2):
        import shutil
        shutil.rmtree(out2)
    s = Session(data, out2, e3, None, log=lambda _s: None, exe_output='all')
    s.build([])
    sd, cm = os.path.join(out2, 'INSTALL_TO_sd'), os.path.join(out2, 'INSTALL_TO_cemu', 'graphicPacks', SE.CEMU_PACK)
    pf = [os.path.join(sd, 'wiiu', 'sm4shclonetool', '%016X.patch' % t) for t in PS.TITLE_IDS]
    blobs = [open(p, 'rb').read() for p in pf if os.path.exists(p)]
    ps = PS.read_plugin(blobs[0]) if blobs else None
    def unmarked(path):                          # the memory image, the marker block (it names the tool's version) out
        mem = Rpx(path).memory()
        base, _rec = X.find_marker(Rpx(path))
        for a, b in mem.items():
            if a <= base < a + len(b):
                mem[a] = b[:base - a] + b[base - a + 0x4000:]
        return mem
    check('--exe-output all: INSTALL_TO_code/cross_f.rpx (= build 3\'s memory image), INSTALL_TO_sd/wiiu/sm4shclonetool/<title '
          'id>.patch for the three regions (one patch, read back: %s), INSTALL_TO_cemu/graphicPacks/%s/ rules.txt + '
          'patches.txt' % ('%d words, a %d byte cave' % (len(ps.sites), len(ps.blob)) if ps else '-', SE.CEMU_PACK),
          (unmarked(os.path.join(out2, 'INSTALL_TO_code', 'cross_f.rpx')) == unmarked(e3), len(blobs),
           len(set(blobs)), ps is not None and ps.meta['fighters'] == [f['name'] for f in reg['fighters']],
           [os.path.exists(os.path.join(cm, f)) for f in ('rules.txt', 'patches.txt')]),
          (True, 3, 1, True, [True, True]))
    plug = os.path.join(sd, 'wiiu', 'environments', 'aroma', 'plugins', 'sm4shclonetool.wps')
    check('the Aroma plugin is packaged (wiiu/environments/aroma/plugins/sm4shclonetool.wps = aroma/%s)'
          % os.path.basename(SE.AROMA_PLUGIN), os.path.exists(SE.AROMA_PLUGIN) and
          open(plug, 'rb').read() == open(SE.AROMA_PLUGIN, 'rb').read(), True)
    readme = open(os.path.join(out2, 'README.txt')).read()
    check('README.txt: install steps for the patched rpx, the Aroma plugin and the Cemu graphic pack',
          ['INSTALL_TO_code/cross_f.rpx' in readme, 'INSTALL_TO_sd/' in readme, 'INSTALL_TO_cemu/graphicPacks' in readme],
          [True, True, True])
    s = Session(data, out2, e3, None, log=lambda _s: None, exe_output='aroma')
    s.build([])
    check('--exe-output aroma on a package with all three: none removed (1.5.2: the outputs a package has are kept and '
          'made again)', sorted(d for d in os.listdir(out2) if d.startswith('INSTALL_TO_')),
          ['INSTALL_TO_cemu', 'INSTALL_TO_code', 'INSTALL_TO_data', 'INSTALL_TO_sd'])


def kirby_script_checks(pkg, fx, fs, out):
    """(1.4) Kirby's own copy scripts: his motion.mtable grown by each clone's copy runs, every new entry's scripts
    the base's copy scripts with the clone's effect ids / sound rows, jumps to its own copies; the names file"""
    import struct as st
    import zlib
    import acmd
    body = os.path.join('fighter', 'kirby', 'script', 'animcmd', 'body')
    vb = os.path.join(fx, 'data', body)
    if not os.path.exists(os.path.join(vb, 'motion.mtable')):
        check('Kirby\'s own copy scripts: no Kirby ACMD in the fixtures (skipped)', True)
        return
    rd = lambda p: list(st.unpack('>%dI' % (os.path.getsize(p) // 4), open(p, 'rb').read()))  # noqa: E731
    mt0, mt1 = rd(os.path.join(vb, 'motion.mtable')), rd(os.path.join(pkg, body, 'motion.mtable'))
    files0 = {f: acmd.ACMDFile.load(os.path.join(vb, f)) for f in ('game.bin', 'effect.bin', 'sound.bin', 'expression.bin')}
    files1 = {f: acmd.ACMDFile.load(os.path.join(pkg, body, f) if os.path.exists(os.path.join(pkg, body, f))
                                    else os.path.join(vb, f)) for f in files0}
    kinds = {f['name']: f['kind'] for f in fs.values()}
    bad, n, runs = [], 0, {}
    for name, f in fs.items():
        for lo, hi, nb in f.get('kirby_slots') or []:
            runs.setdefault(name, []).append((lo, hi, nb))
            for i in range(hi - lo + 1):
                h, nh = mt0[lo + i], mt1[nb + i]
                if not h:
                    if nh:
                        bad.append((name, hex(lo + i), 'zero'))
                    continue
                for fn in files0:
                    a, b = files0[fn].scripts.get(h), files1[fn].scripts.get(nh)
                    if (a is None) != (b is None) or a is None:
                        if (a is None) != (b is None):
                            bad.append((name, hex(lo + i), fn))
                        continue
                    n += 1
                    for c0, c1 in zip(a, b):
                        for p0, p1 in zip(c0.params, c1.params):
                            if p0 == p1:
                                continue
                            ok = (re.search('graphic|effect', c0.name, re.I) and p0 >> 24 in (3, 4) and
                                  (p1 & 0xFF00FFFF) == (p0 & 0xFF00FFFF) and (p1 >> 16) & 0xFF == kinds[name]) or \
                                (c0.name in ('JUMP', 'CALL') and p1 in mt1[nb:nb + hi - lo + 1]) or \
                                (p0 >> 16 != p1 >> 16 and p0 & 0xFFFF == p1 & 0xFFFF)
                            if not ok:
                                bad.append((name, hex(lo + i), fn, c0.name, hex(p0), hex(p1)))
    check('Kirby\'s own copy scripts: motion.mtable %d -> %d entries (the game\'s 1222 kept); %s; %d scripts are the base\'s '
          'copy scripts with only the clone\'s effect ids / sound rows / own jump targets changed'
          % (len(mt0), len(mt1), '; '.join('%s %s' % (k, ', '.join('0x%X-0x%X -> 0x%X' % r for r in v))
                                          for k, v in runs.items()), n),
          (mt1[:len(mt0)] == mt0, sorted(runs) == ['foxclone', 'foxtwo', 'zssclone'], bad[:4], n > 0),
          (True, True, [], True))
    names = open(os.path.join(out, 'Sm4shCommand_names.txt')).read().split('\n')
    hashes = {zlib.crc32(x.split('->')[0].strip().lower().encode()) & 0xFFFFFFFF for x in names
              if x.strip() and not x.startswith('//')}
    new = {h for v in runs.values() for lo, hi, nb in v for h in mt1[nb:nb + hi - lo + 1] if h}
    check('the names file (Sm4shCommand AnimNames.txt lines) names every new copy script (%d)' % len(new),
          sorted(new - hashes), [])


def customs_check(patched, original):
    sys.path.insert(0, TOOLS)
    import stage_slot_test as SST
    mp, mo = SST.machine(patched), SST.machine(original)
    sx = lambda v: v - (1 << 32) if v & 0x80000000 else v  # noqa: E731
    got = [sx(SST.call(mp, 0x02A4D40C, i)) for i in range(0, 64)]
    want = [sx(SST.call(mo, 0x02A4D40C, i)) for i in range(0, 64)]
    want[59], want[61] = 9, 9                   # foxclone and foxtwo own Fox's (id 10, row 9); zssclone has no customs
    check('custom moves (0x02A4D40C, id -> owned-moves row): ids 0-58 and 60, 62, 63 as the game, 59 / 61 -> Fox\'s row',
          got, want)


def effect_ids(path):
    sys.path.insert(0, TOOLS)
    import re
    import acmd
    f = acmd.ACMDFile.load(path)
    out = {}
    for cmds in f.scripts.values():
        for c in cmds:
            if re.search(r'graphic|effect', c.name, re.I):
                for i, p in enumerate(c.params):
                    if c.kind(i) != 1 and isinstance(p, int) and (p >> 24) in (3, 4):
                        out[(p >> 16) & 0xFF] = out.get((p >> 16) & 0xFF, 0) + 1
    return out


def param_checks(pkg, data, reg):
    """each edited database: the new rows there, and without them (and the sort keys the clone placement moved) the
    vanilla file byte for byte"""
    kinds = {f['kind'] for f in reg['fighters']}
    ids = {f['ui_id'] for f in reg['fighters']}
    coss = {x['cosmetic'] for x in reg['stages']}
    files = {'fighter/fighter_param.bin': lambda e: e[0][1] in kinds,
             'ai/fighter_ai_fighter_param.bin': lambda e: e[0][1] in kinds,
             'ai/fighter_ai_nfp_learning_param.bin': lambda e: e[0][1] in kinds,
             'simple/simple_character_db_cafe.bin': lambda e: e[0][1] in kinds,
             'sound/audience_ouen_param.bin': lambda e: e[0][1] in kinds,
             'ui/ui_character_db.bin': lambda e: e[0][1] in ids,
             'ui/ui_layout_db.bin': lambda e: e[0][1] in ids,
             'ui/ui_skill_db.bin': lambda e: e[0][1] in ids,
             'ui/ui_sound_call_voice_db.bin': lambda e: e[0][1] in ids,
             'ui/ui_stage_db.bin': lambda e: e[0][1] in coss,
             'ui/ui_sound_db.bin': lambda e: e[0][1] in coss}
    for rel, new in files.items():
        a = open(os.path.join(data, 'param', rel), 'rb').read()
        b = open(os.path.join(pkg, 'param', rel), 'rb').read()
        items = s4param.parse(b)
        g = R.group(items)
        n = sum(1 for e in g[2] if new(e))
        g[2] = [e for e in g[2] if not new(e)]
        g[1] = len(g[2])
        if rel == 'ui/ui_character_db.bin':          # the placement after Fox moved later entries' first key up by one
            va = R.group(s4param.parse(a))
            for e, o in zip(g[2], va[2]):
                if e[13][1] == o[13][1] + 1:
                    e[13] = o[13]
        check('param/%s: %d new rows; without them the vanilla file byte for byte' % (rel, n),
              s4param.build(items, b[:8]) == a, True)
    vl = [os.path.exists(os.path.join(pkg, 'param', 'fighter', 'fighter_param_vl_%s.bin' % f['name']))
          for f in reg['fighters']]
    check('vl files of the three clones', vl, [True] * 3)


if __name__ == '__main__':
    main()
