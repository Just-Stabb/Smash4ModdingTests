#!/usr/bin/env python3
"""Sm4shCloneTool end-to-end tests (headless), on a vanilla stand-in executable and vanilla data.

  python3 tools/sm4shclonetool/tests/run_all.py WORK MODDED.rpx VPARAM VUI VFIGHTER SOUND_CONFIG [CUSTOM_CHR]

WORK gets the fixtures (make_fixtures.py), the stand-in (make_vanilla_standin.py from MODDED.rpx), three builds into one
project (1: Fox -> foxclone with its own article, custom moves, PNG portraits, placed after Fox, + stage
BattleField_f -> CloneField; 2: on build 1's executable, Zero Suit Samus -> zssclone with her portraits re-ID'd;
3: on build 2's executable, foxclone -> foxtwo, a clone of a clone), and results.txt. Repository only.
"""
import copy
import json
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
    standin = os.path.join(work, 'vanilla_standin.rpx')
    if not os.path.exists(standin):
        run([sys.executable, os.path.join(HERE, 'make_vanilla_standin.py'), modded, standin],
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
    check('stand-in executable inspects as vanilla', info['state'], 'vanilla')
    check('a modified executable (MODDED) is refused', X.inspect(modded)['state'], 'modified')

    # ---------------------------------------------------------------- build 1
    s = Session(data, out, standin, None, log=say)
    f1 = s.fighter_spec('fox', 'foxclone', ui_name='Foxclone', title='Fox Clone', weapons=['blaster'], customs=True,
                        after='Fox')
    st = s.stage_spec('BattleField_f', 'CloneField', title='Clone Field')
    portraits = {'foxclone': {(set_, '01'): os.path.join(png, 'fox_%s_01.png' % set_)
                              for set_ in ('chr_00', 'chr_10', 'chr_11', 'chr_13', 'stock_90')}}
    portraits['foxclone'][('chr_00', '02')] = os.path.join(png, 'fox_chr_00_02.png')
    s.build([f1], [st], portraits, {'CloneField': {'stage_10': os.path.join(png, 'clone_stage_10.png')}})
    e1 = os.path.join(work, 'e1.rpx')
    _copy(os.path.join(out, 'INSTALL_TO_code', 'cross_f.rpx'), e1)
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
    check('fighter/zssclone/: no article folders of the base (they load from fighter/szerosuit/)',
          os.path.exists(os.path.join(z, 'model', 'paralyzer')), False)
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
    st_icon = os.path.join(pkg, 'ui', 'replace', 'stage', 'stage_10', 'stage_10_CloneField.nut')
    check('stage icon stage_10_CloneField.nut: the imported PNG, a new texture id',
          [T.decode(st_icon) is not None, T.texture_ids(T.read_nut(st_icon))[0][1] != 0x28000999], [True, True])
    check('stage folders renamed', [os.path.exists(os.path.join(pkg, 'stage', v, 'CloneField', 'param',
                                                              'CloneField_param.bin')) for v in ('melee', 'end')],
          [True, True])
    readme = open(os.path.join(out, 'README.txt')).read()
    check('package: INSTALL_TO_data, INSTALL_TO_code/cross_f.rpx, README.txt, project file; no wrapper folder',
          sorted(os.listdir(out)), ['INSTALL_TO_code', 'INSTALL_TO_data', 'README.txt', 'sm4shclonetool_project.json'])
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

    open(os.path.join(work, 'results.txt'), 'w').write('\n'.join(RES) + '\n\n%d checks, %d failed\n' % (
        len(RES), len(FAILS)))
    print('%d checks, %d failed' % (len(RES), len(FAILS)))
    sys.exit(1 if FAILS else 0)


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
        if t0.row_of(oid) is not None:
            rowmap[t0.row_of(oid)] = t1.row_of(bid)
            same &= t1.tones(t1.row_of(bid)) == t0.tones(t0.row_of(oid))
    check('its banks: BINF names = their files, ids new and unique (%s)' % ', '.join('%s %d' % (n, i) for _f, n, i in banks),
          all(nm == f[:-9] and bid not in old_ids for f, nm, bid in banks) and len({b for _f, _n, b in banks}) == len(banks),
          True)
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
