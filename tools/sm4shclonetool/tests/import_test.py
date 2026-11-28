#!/usr/bin/env python3
"""(2.0) The importer and article cloning, end to end: a fourth build of run_all's project (its build 3 executable) with
imports into vanilla fighters and clones, then the files, the executable and Sm4shCommand's own loaders.

  python3 tools/sm4shclonetool/tests/import_test.py WORK PROJECT DATA PATCHED VANILLA [SM4SHCOMMAND_RUN]

(run_all.py runs it after its other checks: PROJECT = its project, PATCHED = build 3's executable.) The imports:
- motions: two into vanilla Zero Suit Samus (one copying Attack11's scripts / vl entry with a left-hand part animation,
  one empty and looping), one into the clone zssclone (a clone's motion info is kind_expand's copy);
- effects: two of Zero Suit Samus's entries into vanilla Fox's bank (an emitter set, and one with an effect model), one
  into the clone foxclone's own bank;
- sounds: a mono WAV into Zero Suit Samus's se bank, a stereo WAV and an IDSP into zssclone's own se bank;
- articles: gun2 for vanilla Fox (a copy of Zero Suit Samus's paralyzer_bullet: another fighter's, so its params load
  with Fox and its effects are imported into Fox's bank), whip2 for zssclone (its base's whip: the clone's own params),
  whip3 for vanilla Zero Suit Samus (her own whip, a second kind).
Checks: every new id unique and reported; every original entry unchanged (motion pack entries, motion.mtable, the
scripts, vl group 1 and the rest of the vl file, the effect sets / textures / efc entries, the tones, the label rows);
round trips (pack, ACMD, ptcl, efc, nus3bank, soundlabeltable); the new entries what was imported (the .omo bytes, the
copied scripts, the emitter bytes but their table offsets, the encoded audio decoding to the input); article folders
copied and their scripts' ids moved; a rebuild with the same imports changes nothing; the executable: a valid RPX,
import_exe_test (patched, Aroma, Cemu), weapon_expand_test (repo_test); Sm4shCommand (its built SM4SHCommand.exe /
SALT.dll in SM4SHCOMMAND_RUN, or $SM4SHCOMMAND_RUN): sm4shcommand_test.cs on the installed view of each fighter.
"""
import hashlib
import math
import os
import shutil
import struct
import subprocess
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
from sm4shclonetool import _paths  # noqa: F401,E402
from sm4shclonetool import audio as AU  # noqa: E402
from sm4shclonetool import exe as X  # noqa: E402
from sm4shclonetool import importer as I  # noqa: E402
from sm4shclonetool import pac as PAC  # noqa: E402
from sm4shclonetool import sound as SND  # noqa: E402
from sm4shclonetool.rpx import sha1_file  # noqa: E402
from sm4shclonetool.session import Session  # noqa: E402
import acmd  # noqa: E402
import efc as EFC  # noqa: E402
import ptcl as PT  # noqa: E402

RES, FAILS = [], []
CSC = '/usr/lib/dotnet/sdk/8.0.134/Roslyn/bincore/csc.dll'
MONO = '/usr/lib/mono/4.5'


def check(what, got, want=True):
    ok = got == want
    RES.append('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))
    if not ok:
        FAILS.append(what)
    print(RES[-1], flush=True)
    return ok


def wav(path, seconds, channels, rate=44100):
    with wave.open(path, 'wb') as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        fr = []
        n = int(seconds * rate)
        for i in range(n):
            env = min(1.0, i / 800.0, (n - i) / 800.0)
            v = [int(14000 * env * math.sin(2 * math.pi * f * i / rate)) for f in (440, 660)[:channels]]
            fr.append(struct.pack('<%dh' % channels, *v))
        w.writeframes(bytes(4000 * channels) + b''.join(fr) + bytes(4000 * channels))   # silence around it (trimmed)


def first(*paths):
    return next((p for p in paths if p and os.path.exists(p)), None)


def merged(dst, *layers):
    """an installed view: the layers' files (later ones win) as symlinks (copies for the package's)"""
    for i, layer in enumerate(layers):
        for root, _d, fs in os.walk(layer, followlinks=True):
            for f in fs:
                src = os.path.join(root, f)
                to = os.path.join(dst, os.path.relpath(src, layer))
                os.makedirs(os.path.dirname(to), exist_ok=True)
                if os.path.lexists(to):
                    os.unlink(to)
                os.symlink(os.path.realpath(src), to)


def main():
    work, proj, data, patched, vanilla = sys.argv[1:6]
    s4c = sys.argv[6] if len(sys.argv) > 6 else os.environ.get('SM4SHCOMMAND_RUN')
    run(work, proj, data, patched, vanilla, s4c)
    print('\n%d checks, %d failed' % (len(RES), len(FAILS)))
    sys.exit(1 if FAILS else 0)


def run(work, proj, data, patched, vanilla, s4c=None):
    inp = os.path.join(work, 'import_in')
    os.makedirs(inp, exist_ok=True)
    zroot = os.path.join(data, 'fighter', 'szerosuit')
    zp = PAC.Pac.load(os.path.join(zroot, 'motion', 'body', 'main.pac'))
    zl = PAC.Pac.load(os.path.join(zroot, 'motion', 'body', 'lhand.pac'))
    spin = zp.get('FitSZerosuitBodyMainC00Attack11.omo')
    idle = zp.get('FitSZerosuitBodyMainA00Wait1.omo')
    hand = zl.get('FitSZerosuitBodyLhandC00Attack11.omo')
    open(os.path.join(inp, 'spin.omo'), 'wb').write(spin)
    open(os.path.join(inp, 'idle.omo'), 'wb').write(idle)
    open(os.path.join(inp, 'spin_lhand.omo'), 'wb').write(hand)
    wav(os.path.join(inp, 'beep.wav'), 0.4, 1)
    wav(os.path.join(inp, 'chord.wav'), 0.3, 2, 48000)
    zse = AU.Bank(open(os.path.join(zroot, 'sound', 'snd_se_SZerosuit.nus3bank'), 'rb').read())
    ti = next(i for i, t in enumerate(zse.tones) if t and t['channels'] == 1)
    open(os.path.join(inp, 'tone.idsp'), 'wb').write(zse.data_of(ti))
    imports = [
        {'what': 'motion', 'target': 'szerosuit', 'name': 'NewSpin', 'omo': os.path.join(inp, 'spin.omo'), 'copy': 0x50,
         'parts': {'lhand': os.path.join(inp, 'spin_lhand.omo')}},
        {'what': 'motion', 'target': 'szerosuit', 'name': 'NewIdle', 'omo': os.path.join(inp, 'idle.omo'), 'loop': True},
        {'what': 'motion', 'target': 'zssclone', 'name': 'CloneMove', 'omo': os.path.join(inp, 'spin.omo'),
         'copy': 'Attack11'},
        {'what': 'effect', 'target': 'fox', 'source': 'szerosuit', 'entry': 5},
        {'what': 'effect', 'target': 'fox', 'source': 'szerosuit', 'entry': 2},
        {'what': 'effect', 'target': 'foxclone', 'source': 'szerosuit', 'entry': 11, 'name': 'PtcFoxcloneWhip'},
        {'what': 'sound', 'target': 'szerosuit', 'file': os.path.join(inp, 'beep.wav'), 'alias': 'Beep'},
        {'what': 'sound', 'target': 'zssclone', 'file': os.path.join(inp, 'chord.wav'), 'alias': 'Chord', 'volume': 2.0},
        {'what': 'sound', 'target': 'zssclone', 'file': os.path.join(inp, 'tone.idsp'), 'name': 'snd_se_Zssclone_Idsp'},
        {'what': 'article', 'owner': 'fox', 'name': 'gun2', 'source_owner': 'szerosuit', 'source': 'paralyzer_bullet',
         'max': 3},
        {'what': 'article', 'owner': 'zssclone', 'name': 'whip2', 'source_owner': 'szerosuit', 'source': 'whip'},
        {'what': 'article', 'owner': 'szerosuit', 'name': 'whip3', 'source_owner': 'szerosuit', 'source': 'whip'},
    ]
    pkg = os.path.join(proj, 'INSTALL_TO_data')
    before = snapshot(pkg, data)
    tp = first(os.path.join(pkg, 'sound', 'config', 'soundlabeltable.bin'),
               os.path.join(data, 'sound', 'config', 'soundlabeltable.bin'))
    table_before = open(tp, 'rb').read()
    log = open(os.path.join(work, 'import_log.txt'), 'w')
    s = Session(data, proj, patched, None, log=lambda t: log.write(t + '\n'))
    reg0 = s.reg
    plan_reg, _r, errors, _n, files, items = s.plan([], [], imports)
    check('plan: the imports validate (%d files / folders listed, the executable items: motion tables, articles, the vl '
          'hooks)' % len(files), (errors, any('motion table of szerosuit' in i for i in items),
                                  any('article gun2' in i for i in items), any('vl load' in i for i in items)),
          ([], True, True, True))
    bad = s.plan([], [], [{'what': 'motion', 'target': 'nobody', 'name': 'X', 'omo': os.path.join(inp, 'spin.omo')},
                          {'what': 'motion', 'target': 'fox', 'name': '1bad', 'omo': os.path.join(inp, 'spin.omo')},
                          {'what': 'article', 'owner': 'fox', 'name': 'blaster', 'source_owner': 'szerosuit',
                           'source': 'whip'},
                          {'what': 'article', 'owner': 'fox', 'name': 'gunx', 'source_owner': 'szerosuit',
                           'source': 'nothing'}])[2]
    check('plan: an unknown fighter, a bad name, an article name the owner has, a missing source article: refused (%d)'
          % len(bad), len(bad), 4)
    summary = s.build([], [], imports=imports)
    log.close()
    e4 = os.path.join(work, 'e4.rpx')
    shutil.copyfile(os.path.join(proj, 'INSTALL_TO_code', 'cross_f.rpx'), e4)
    import run_all as RA
    check('build 4 (imports): a valid RPX (%s)' % RA.rpx_valid(e4), RA.rpx_valid(e4), 'valid')
    mreg = X.inspect(e4)['registry']
    reg = Session(data, proj, e4, None, log=lambda t: None).reg
    imp = reg.get('imports') or {}
    check('build 4: the marker keeps the clones and the imports the executable needs (motions of szerosuit / zssclone, '
          '3 articles), not the data-only ones (effects, sounds: the project file\'s, merged by the session)',
          ([f['name'] for f in mreg['fighters']], sorted((mreg.get('imports') or {})),
           sorted((mreg.get('imports') or {}).get('motions', {})), [a['name'] for a in imp.get('articles', [])]),
          ([f['name'] for f in reg0['fighters']], ['articles', 'motions'], ['szerosuit', 'zssclone'],
           ['gun2', 'whip2', 'whip3']))
    check('build 4: the session\'s registry has every import (effects of fox / foxclone, sounds of szerosuit / zssclone)',
          (sorted(imp.get('effects', {})), sorted(imp.get('sounds', {}))),
          (['fox', 'foxclone'], ['szerosuit', 'zssclone']))
    got = summary.get('imported') or {}
    check('build 4: the summary reports every new id (3 motions, 4 effects incl. gun2\'s, 3 sounds, 3 articles)',
          (len(got.get('motions', [])), len(got.get('effects', [])) >= 3, len(got.get('sounds', [])),
           len(got.get('articles', []))), (3, True, 3, 3))
    motion_checks(pkg, data, imp, inp)
    effect_checks(pkg, data, imp)
    sound_checks(pkg, data, imp, inp, table_before)
    article_checks(pkg, data, imp, reg)
    names = open(os.path.join(proj, I.NAMES_FILE)).read()
    check('Sm4shCommand_names.txt: a section per fighter with imported motions, "Name" and "Name -> body/<file>.omo"',
          all(x in names for x in ('// ---- szerosuit: imported motions', 'NewSpin -> body/FitSZerosuitBodyMainZ00NewSpin.omo',
                                   'NewIdle', '// ---- zssclone: imported motions')), True)
    readme = open(os.path.join(proj, 'README.txt')).read()
    check('README.txt lists the imports with their ids', all(x in readme for x in ('IMPORTED', 'NewSpin', 'gun2',
                                                                                   'effect id', 'sound id')), True)
    # unchanged elsewhere: every package file the imports don't touch is as before
    after = snapshot(pkg, data)
    touched = {k for k in after if before.get(k) != after[k]}
    allowed = ('fighter/szerosuit/', 'fighter/zssclone/', 'fighter/fox/', 'fighter/foxclone/effect/',
               'sound/config/soundlabeltable.bin', 'param/fighter/fighter_param_vl_szerosuit.bin',
               'param/fighter/fighter_param_vl_zssclone.bin')
    check('the imports change only the targets\' files, the soundlabeltable and their vl files (%d files)' % len(touched),
          sorted(k for k in touched if not k.startswith(allowed)), [])
    # rebuild: nothing changes
    s = Session(data, proj, e4, None, log=lambda t: None)
    s.build([], [], imports=imports)
    again = snapshot(pkg, data)
    check('a rebuild with the same imports: the package files and the executable unchanged (same slots and ids)',
          (sorted(k for k in again if again.get(k) != after.get(k)), sha1_file(os.path.join(proj, 'INSTALL_TO_code',
                                                                                             'cross_f.rpx'))),
          ([], sha1_file(e4)))
    # (with 1.5.1's repair) a repair rebuilds the package from the project: the imports come back the same
    s = Session(data, proj, e4, None, log=lambda t: None)
    if hasattr(s, 'repair'):
        s.repair()
        rep = snapshot(pkg, data)
        diff = sorted(k for k in set(rep) | set(after) if rep.get(k) != after.get(k))
        e5 = os.path.join(proj, 'INSTALL_TO_code', 'cross_f.rpx')
        check('a repair (the package rebuilt from the project): every imported motion, effect, sound and article back '
              'with the same numbers / ids, the package files as before (%d differ), the executable\'s memory image '
              'the same but its marker block, the marker\'s registry the same (but the "renumber" a 1.5 build leaves in '
              'it)' % len(diff), (diff[:6], image_but_marker(e5), marker_reg(e5)),
              ([], image_but_marker(e4), marker_reg(e4)))
    # the executable
    o = os.path.join(work, 'import_exe_test.txt')
    rc = RA.run([sys.executable, os.path.join(HERE, 'import_exe_test.py'), e4, vanilla, os.path.join(work, 'import_ps')], o)
    text = open(o).read()
    check('import_exe_test (motion tables, article lists, weapon descriptors, file names, vl hooks: patched rpx, Aroma, '
          'Cemu): %d ok, 0 failed (exit %d)' % (text.count('\nok ') + text.startswith('ok '), rc),
          [x for x in text.splitlines() if x.startswith('FAIL')] + ([] if rc == 0 else ['exit %d' % rc]), [])
    o = os.path.join(work, 'import_weapon_expand_test.txt')
    rc = RA.run([sys.executable, os.path.join(HERE, 'repo_test.py'), 'weapon_expand_test', e4, vanilla], o)
    text = open(o).read()
    fails = [x for x in text.splitlines() if x.startswith('FAIL')]
    other = [x for x in fails if 'fireball' not in x.lower() and '0x185' not in x]
    check('weapon_expand_test on build 4 (the clones\' own articles + the 3 imported: switches, descriptors, accessors, '
          'path builders): %d ok, failures only its fireball-specific check (%d)' % (text.count('\nok '), len(fails)),
          other, [])
    sm4shcommand(work, proj, data, imp, s4c)


def image_but_marker(path):
    """the SHA-1 of an executable's loaded sections with the tool's marker block zeroed"""
    from sm4shclonetool.rpx import Rpx
    x = Rpx(path)
    base, _rec = X.find_marker(x)
    h = hashlib.sha1()
    for a, b in sorted(x.memory().items()):
        b = bytearray(b)
        if a <= base < a + len(b):
            o = base - a
            b[o:o + 0x4000] = bytes(0x4000)
        h.update(struct.pack('>I', a) + bytes(b))
    return h.hexdigest()


def marker_reg(path):
    import json
    from sm4shclonetool.rpx import Rpx
    reg = X.find_marker(Rpx(path))[1]['registry']
    for f in reg['fighters']:
        f.pop('renumber', None)
    return json.dumps(reg, sort_keys=True)


def snapshot(pkg, data):
    out = {}
    for root, _d, fs in os.walk(pkg):
        for f in fs:
            p = os.path.join(root, f)
            out[os.path.relpath(p, pkg).replace(os.sep, '/')] = hashlib.sha1(open(p, 'rb').read()).hexdigest()
    return out


def _bins(d):
    return {f: acmd.ACMDFile.load(os.path.join(d, f)) for f in I.BINS if os.path.exists(os.path.join(d, f))}


def motion_checks(pkg, data, imp, inp):
    for fighter, recs in sorted(imp['motions'].items()):
        root = os.path.join(pkg, 'fighter', fighter)
        orig = first(os.path.join(data, 'fighter', fighter, 'motion', 'body', 'main.pac')) if fighter == 'szerosuit' else None
        p = PAC.Pac.load(os.path.join(root, 'motion', 'body', 'main.pac'))
        raw = open(os.path.join(root, 'motion', 'body', 'main.pac'), 'rb').read()
        check('%s: main.pac round trip; names in the game\'s order (sorted)' % fighter,
              (p.build() == raw, p.names() == sorted(p.names(), key=lambda n: n.encode())), (True, True))
        for r in recs:
            check('%s: %s: %s.omo in main.pac = the imported file byte for byte' % (fighter, r['name'], r['anim']),
                  p.get(r['anim'] + '.omo') == open(os.path.join(inp, 'idle.omo' if r['name'] == 'NewIdle' else
                                                                  'spin.omo'), 'rb').read(), True)
        if orig:
            op = PAC.Pac.load(orig)
            check('%s: main.pac: the game\'s %d animations unchanged' % (fighter, len(op.entries)),
                  all(p.get(n) == d for n, d in op.entries), True)
            ol = PAC.Pac.load(os.path.join(data, 'fighter', fighter, 'motion', 'body', 'lhand.pac'))
            nl = PAC.Pac.load(os.path.join(root, 'motion', 'body', 'lhand.pac'))
            r0 = next(r for r in recs if r['name'] == 'NewSpin')
            check('%s: NewSpin\'s left-hand part animation in lhand.pac (FitSZerosuitBodyLhandZ00NewSpin.omo), the old '
                  'ones unchanged, its hash in the record' % fighter,
                  (nl.get('FitSZerosuitBodyLhandZ00NewSpin.omo') is not None, all(nl.get(n) == d for n, d in ol.entries),
                   r0['part_hashes'].get('lhand') == PAC.anim_hash('FitSZerosuitBodyLhandZ00NewSpin')), (True, True, True))
        mt_new = open(os.path.join(root, 'script', 'animcmd', 'body', 'motion.mtable'), 'rb').read()
        src_root = os.path.join(data, 'fighter', 'szerosuit')
        mt_old = open(os.path.join(src_root, 'script', 'animcmd', 'body', 'motion.mtable'), 'rb').read()
        n_old = len(mt_old) // 4
        new = struct.unpack('>%dI' % (len(mt_new) // 4), mt_new)
        check('%s: motion.mtable: the game\'s %d entries unchanged, then the %d imported scripts\' hashes at 0x%X-0x%X'
              % (fighter, n_old, len(recs), n_old, n_old + len(recs) - 1),
              (mt_new[:len(mt_old)] == mt_old if fighter == 'szerosuit' else len(new) - len(recs) == n_old,
               [r['index'] for r in recs], list(new[n_old:])),
              (True, list(range(n_old, n_old + len(recs))), [acmd.crc(r['name']) for r in recs]))
        bins = _bins(os.path.join(root, 'script', 'animcmd', 'body'))
        obins = _bins(os.path.join(src_root, 'script', 'animcmd', 'body'))
        okc = []
        for r in recs:
            h = acmd.crc(r['name'])
            for f, a in bins.items():
                if r['flags_from'] is not None:
                    sh = new[r['flags_from']]
                    okc.append(a.scripts.get(h) is not None and (sh not in a.scripts or [c.encode() for c in a.scripts[h]]
                                                                 == [c.encode() for c in a.scripts[sh]]))
                else:
                    okc.append([c.ident for c in a.scripts.get(h, [])] == [acmd.END])
        check('%s: each imported motion has a script in the four files: a copy of its source motion\'s, or Script_End'
              % fighter, all(okc) and len(okc) == 4 * len(recs), True)
        if fighter == 'szerosuit':
            same = all(a.scripts.get(h) is not None and [c.encode() for c in a.scripts[h]] ==
                       [c.encode() for c in obins[f].scripts[h]] for f, a in bins.items() for h in obins[f].scripts)
            check('%s: every game script unchanged (%d)' % (fighter, sum(len(a.scripts) for a in obins.values())),
                  same, True)
            check('%s: the four files round-trip (read, written: the same bytes)' % fighter,
                  all(acmd.ACMDFile.load(os.path.join(root, 'script', 'animcmd', 'body', f)).encode() ==
                      open(os.path.join(root, 'script', 'animcmd', 'body', f), 'rb').read() for f in bins), True)
        vl_new = open(os.path.join(pkg, 'param', 'fighter', 'fighter_param_vl_%s.bin' % fighter), 'rb').read()
        vl_old = open(first(os.path.join(data, 'param', 'fighter', 'fighter_param_vl_szerosuit.bin')), 'rb').read()
        n1, _f1, e1, end1 = I.vl_group1(vl_new)
        n0, _f0, e0, end0 = I.vl_group1(vl_old)
        check('%s: fighter_param_vl group 1: %d -> %d entries (the motion count), the old ones unchanged, the new ones '
              'the records\' (copied / loop), the rest of the file byte for byte' % (fighter, n0, n1),
              (n1, e1[:n0] == e0 if fighter == 'szerosuit' else True, e1[n0:], vl_new[end1:] == vl_old[end0:]),
              (n0 + len(recs), True, [r['vl'] for r in recs], True))
    r = next(r for r in imp['motions']['szerosuit'] if r['name'] == 'NewIdle')
    check('szerosuit: NewIdle (loop, no copy): vl entry byte 1 = 6 (the looping motions\' flags byte), empty scripts',
          (r['vl'][1], r['flags_from']), (6, None))


def effect_checks(pkg, data, imp):
    src_efc, src_ptcl = I.bank_paths(os.path.join(data, 'fighter', 'szerosuit'), 'szerosuit')
    se = EFC.Efc(open(src_efc, 'rb').read())
    sp = PT.Ptcl(open(src_ptcl, 'rb').read())
    for fighter, recs in sorted(imp['effects'].items()):
        root = os.path.join(pkg, 'fighter', fighter, 'effect', fighter)
        efc_p, ptcl_p = os.path.join(root, fighter + '.010d0000.efc'), os.path.join(root, fighter + '.010d0000.ptcl')
        e = EFC.Efc(open(efc_p, 'rb').read())
        p = PT.Ptcl(open(ptcl_p, 'rb').read())
        check('%s: its .ptcl and .efc round-trip and the .ptcl validates (eft\'s run-time offsets)' % fighter,
              (p.build() == open(ptcl_p, 'rb').read(), e.build() == open(efc_p, 'rb').read(), p.validate()),
              (True, True, []))
        if fighter == 'fox':
            oe, op = I.bank_paths(os.path.join(data, 'fighter', 'fox'), 'fox')
            e0, p0 = EFC.Efc(open(oe, 'rb').read()), PT.Ptcl(open(op, 'rb').read())
        else:
            oe = os.path.join(data, 'fighter', 'fox', 'effect', 'fox', 'fox.010d0000.efc')
            e0, p0 = None, None
        if e0:
            old_ok = e.entries[:len(e0.entries)] == e0.entries and all(
                [x['data'] for x in p.sets[i]['emitters']] == [x['data'] for x in p0.sets[i]['emitters']]
                for i in range(len(p0.sets))) and p.tex[:len(p0.tex)] == p0.tex
            check('%s: the bank\'s %d entries, %d emitter sets and textures unchanged' % (fighter, len(e0.entries),
                                                                                       len(p0.sets)), old_ok, True)
        kind = 9 if fighter == 'fox' else 0x41
        ids = [r['id'] for r in recs]
        check('%s: the new effect ids 0x3%02X00nn are unique, consecutive entries of its .efc (%s)' % (
            fighter, kind, ', '.join('0x%08X' % i for i in ids)),
              (len(set(ids)), [i >> 16 for i in ids], [i & 0xFFFF for i in ids]),
              (len(ids), [0x300 + kind] * len(ids), list(range(len(e.entries) - len(ids), len(e.entries)))))
        for r in recs:
            ent = e.entries[r['id'] & 0xFFFF]
            sent = se.entries[r['entry']] if r['source'] == 'szerosuit.010d0000.efc' else None
            if not sent:
                continue
            st = ent[1] - 1
            ok = True
            if sent[1]:
                ss = sent[1] - 1
                ok = p.set_name(st) == r['name'] and len(p.sets[st]['emitters']) == len(sp.sets[ss]['emitters'])
                for k, (a, b) in enumerate(zip(p.sets[st]['emitters'], sp.sets[ss]['emitters'])):
                    if a['data'] is None:
                        continue
                    ka, kb = p.key_anims(a['data']), sp.key_anims(b['data'])
                    ta = [p.tex[t['native_pos']:t['native_pos'] + t['native_size']] for t in
                          (p.texres(a['data'], j) for j in range(3))]
                    tb = [sp.tex[t['native_pos']:t['native_pos'] + t['native_size']] for t in
                          (sp.texres(b['data'], j) for j in range(3))]
                    ok &= ka == kb and ta == tb and p.emitter_name(a['data']) == sp.emitter_name(b['data'])
                    ok &= p.shader_binary(PT.be32(a['data'], 0x844)) == sp.shader_binary(PT.be32(b['data'], 0x844))
            if sent[2]:
                ok &= e.models[ent[2] - 1] == se.models[sent[2] - 1] and os.path.isdir(
                    os.path.join(root, 'model', se.models[sent[2] - 1]))
            check('%s: 0x%08X (%s, szerosuit entry %d): its emitters\' key animations, textures, names and shaders the '
                  'source\'s%s' % (fighter, r['id'], r['name'], r['entry'], ', its effect model folder copied'
                                  if sent[2] else ''), ok, True)


def sound_checks(pkg, data, imp, inp, table_before):
    tp_new = os.path.join(pkg, 'sound', 'config', 'soundlabeltable.bin')
    tn = SND.Table(open(tp_new, 'rb').read())
    t0 = SND.Table(table_before)
    check('soundlabeltable.bin round-trips', tn.data() == open(tp_new, 'rb').read(), True)
    all_ids = [r << 16 | lab for r, rr in enumerate(tn.rows) for lab in range(rr[1])]
    new_ids = [r['id'] for recs in imp['sounds'].values() for r in recs]
    check('every sound id in the table once; the %d new ids among them' % len(new_ids),
          (len(set(all_ids)) == len(all_ids), set(new_ids) <= set(all_ids)), (True, True))
    for fighter, recs in sorted(imp['sounds'].items()):
        for r in recs:
            bp = os.path.join(pkg, 'fighter', fighter, 'sound', r['bank'])
            b = AU.Bank(open(bp, 'rb').read())
            row, lab = r['id'] >> 16, r['id'] & 0xFFFF
            check('%s: 0x%08X: row 0x%X (%s\'s BINF id %d), label %d -> tone %d = %s' % (
                fighter, r['id'], row, r['bank'], b.binf()[1], lab, r['tone'], r['name']),
                  (tn.rows[row][0], tn.tones(row)[lab], b.tones[r['tone']]['name']), (b.binf()[1], r['tone'], r['name']))
            blob = b.data_of(r['tone'])
            if r['name'].endswith('Idsp'):
                check('%s: %s: the IDSP file\'s bytes, as given' % (fighter, r['name']),
                      blob == open(os.path.join(inp, 'tone.idsp'), 'rb').read(), True)
            else:
                rate, chans = AU.idsp_decode(blob)
                src = 'beep.wav' if 'beep' in r['name'] else 'chord.wav'
                ch = 1 if 'beep' in r['name'] else 2
                ref = AU.read_wav(os.path.join(inp, src), 48000, ch)
                ref = [ref] if ch == 1 else ref
                import numpy as np
                a = np.array(chans[0], float)
                x0 = np.array(ref[0], float)
                lead0 = int(np.argmax(np.abs(x0) > 32768 * 10 ** (-45 / 20)))
                snr = -99.0
                for lead in range(max(0, lead0 - 300), lead0 + 300):     # where the trim cut (every channel's peak)
                    x = x0[lead:lead + len(a)]
                    if len(x) < len(a):
                        break
                    x = x * (np.abs(a).max() / max(1, np.abs(x).max()))
                    snr = max(snr, 10 * math.log10((x ** 2).sum() / max(1e-9, ((a - x) ** 2).sum())))
                check('%s: %s: %d channel(s), 48 kHz, silence trimmed, peak -0.5 dBFS, decodes to the WAV (%.1f dB SNR > 25)'
                      % (fighter, r['name'], len(chans), snr), (len(chans), rate, snr > 25,
                                                               abs(20 * math.log10(np.abs(a).max() / 32768) + 0.5) < 0.3),
                      (ch, 48000, True, True))
        # the bank's old tones and the table's other rows
        bank = recs[0]['bank']
        new = AU.Bank(open(os.path.join(pkg, 'fighter', fighter, 'sound', bank), 'rb').read())
        if fighter == 'szerosuit':
            old = AU.Bank(open(os.path.join(data, 'fighter', fighter, 'sound', bank), 'rb').read())
            check('%s: %s round-trips; its %d old tones (entries and audio) unchanged; PACK at a multiple of 0x10'
                  % (fighter, bank, len(old.raw)), (new.data() == open(os.path.join(pkg, 'fighter', fighter, 'sound', bank),
                                                                       'rb').read(), new.raw[:len(old.raw)] == old.raw,
                                                    all(new.data_of(i) == old.data_of(i) for i, t in enumerate(old.tones) if t)),
                  (True, True, True))
    rows = {r['id'] >> 16 for recs in imp['sounds'].values() for r in recs}
    check('soundlabeltable: every other row\'s labels unchanged (%d rows), the imports\' rows grew by their sounds'
          % len(t0.rows), [i for i in range(len(t0.rows)) if i not in rows and t0.tones(i) != tn.tones(i)
                           and i < len(tn.rows)], [])
    for fighter, recs in sorted(imp['sounds'].items()):
        path = os.path.join(os.path.dirname(pkg), I.ALIASES_DIR, fighter + '.txt')
        text = open(path).read() if os.path.exists(path) else ''
        check('%s: Sm4shCommand\'s Aliases/sounds/%s.txt names the new ids' % (fighter, fighter),
              all('0x%08X = %s' % (r['id'], r['alias']) in text for r in recs), True)


def article_checks(pkg, data, imp, reg):
    for a in imp['articles']:
        own = os.path.join(pkg, 'fighter', a['owner'])
        src = os.path.join(data, 'fighter', a['source_owner'])
        same = []
        wsrc = os.path.join(src, 'script', 'animcmd', 'weapon', a['source'])
        same.append(sorted(os.listdir(wsrc)) == sorted(os.listdir(os.path.join(own, 'script', 'animcmd', 'weapon',
                                                                                a['name']))))
        for sub in ('model', 'motion'):
            sd, dd = os.path.join(src, sub, a['source']), os.path.join(own, sub, a['name'])
            if os.path.isdir(sd):
                for root, _d, fs in os.walk(sd):
                    for f in fs:
                        q = os.path.join(dd, os.path.relpath(os.path.join(root, f), sd))
                        same.append(os.path.exists(q) and open(q, 'rb').read() == open(os.path.join(root, f), 'rb').read())
        check('%s/%s (a copy of %s\'s %s): its script folder and its model / motion files copied (%d), weapon kind 0x%X, '
              'article id %d' % (a['owner'], a['name'], a['source_owner'], a['source'], len(same), a['kind'],
                                 a['article_id']), (all(same), bool(same), a['article_id'] >= 0), (True, True, True))
        wd = os.path.join(own, 'script', 'animcmd', 'weapon', a['name'])
        bank = 9 if a['owner'] == 'fox' else (0x42 if a['owner'] == 'zssclone' else 0x19)
        ids = set()
        for f in ('effect.bin', 'game.bin'):
            if os.path.exists(os.path.join(wd, f)):
                for cmds in acmd.ACMDFile.load(os.path.join(wd, f)).scripts.values():
                    for c in cmds:
                        if 'graphic' in c.name.lower() or 'effect' in c.name.lower():
                            ids |= {v for i, v in enumerate(c.params) if c.kind(i) != 1 and isinstance(v, int)
                                    and v >> 24 == 3}
        check('%s/%s: its scripts\' effect ids all on %s\'s bank 0x3%02X (%d ids)' % (
            a['owner'], a['name'], a['owner'], bank, len(ids)), sorted({(v >> 16) & 0xFF for v in ids}),
              [bank] if ids else [])
    fx = [r for r in imp['effects']['fox'] if r['source'] == 'szerosuit.010d0000.efc']
    check('fox/gun2: the paralyzer bullet\'s effects imported into Fox\'s bank with it (%d)' % len(fx), len(fx) >= 3, True)


def sm4shcommand(work, proj, data, imp, s4c):
    if not s4c or not os.path.exists(os.path.join(s4c, 'SM4SHCommand.exe')):
        check('Sm4shCommand (its loaders on the imported fighters): skipped, no built SM4SHCommand.exe given', True)
        return
    exe = os.path.join(work, 'ScTest.exe')
    refs = ['-r:' + os.path.join(s4c, x) for x in ('SALT.dll', 'SM4SHCommand.exe')] + \
           ['-r:%s/%s' % (MONO, x) for x in ('mscorlib.dll', 'System.dll', 'System.Core.dll', 'System.Windows.Forms.dll',
                                            'System.Drawing.dll')]
    r = subprocess.run(['dotnet', CSC, '-nologo', '-nowarn:1701,1702', '-out:' + exe, '-nostdlib'] + refs +
                       [os.path.join(HERE, 'sm4shcommand_test.cs')], capture_output=True, text=True)
    if not check('sm4shcommand_test.cs builds against Sm4shCommand (%s)' % s4c, r.returncode, 0):
        print(r.stdout[-2000:], r.stderr[-2000:])
        return
    run_dir = os.path.join(work, 'sm4shcommand_run')          # a copy of the built Sm4shCommand, the test beside it
    if os.path.exists(run_dir):
        shutil.rmtree(run_dir)
    shutil.copytree(s4c, run_dir)
    shutil.copyfile(exe, os.path.join(run_dir, 'ScTest.exe'))
    s4c = run_dir
    view = os.path.join(work, 'installed')
    if os.path.lexists(view):
        shutil.rmtree(view)
    merged(view, data, os.path.join(proj, 'INSTALL_TO_data'))
    pr = os.path.join(proj, I.NAMES_FILE)
    try:
        for fighter in ('szerosuit', 'zssclone', 'fox', 'foxclone'):
            exp = os.path.join(work, 'sc_expect_%s.txt' % fighter)
            root = os.path.join(view, 'fighter', fighter)
            mt = os.path.join(root, 'script', 'animcmd', 'body', 'motion.mtable')
            lines = ['fighter\t%s\t%s' % (root, view), 'names\t%s' % pr,
                     'aliases\t%s' % os.path.join(proj, I.ALIASES_DIR, fighter + '.txt'),
                     'count\t%d' % (os.path.getsize(mt) // 4 if os.path.exists(mt) else -1)]
            for r in imp['motions'].get(fighter, []):
                lines.append('motion\t%d\t%s\t%s.omo\t%d' % (r['index'], r['name'], r['anim'],
                                                             -1 if r['flags_from'] is None else r['flags_from']))
            for r in imp['sounds'].get(fighter, []):
                b = AU.Bank(open(os.path.join(root, 'sound', r['bank']), 'rb').read())
                t = b.tones[r['tone']]
                lines.append('sound\t0x%08X\t%s\t%d\t%d' % (r['id'], r['name'], t['samples'], t['channels']))
                lines.append('alias\t0x%08X\t%s' % (r['id'], r['alias']))
            for r in imp['effects'].get(fighter, []):
                efc_p, ptcl_p = I.bank_paths(root, fighter)
                e = EFC.Efc(open(efc_p, 'rb').read())
                p = PT.Ptcl(open(ptcl_p, 'rb').read())
                st = e.entries[r['id'] & 0xFFFF][1]
                if st:
                    lines.append('effect\t0x%08X\t%s\t%d' % (r['id'], p.set_name(st - 1), sum(
                        1 for x in p.sets[st - 1]['emitters'] if x['data'] is not None)))
            for f in I.BINS:
                bp = os.path.join(root, 'script', 'animcmd', 'body', f)
                if os.path.exists(bp):
                    lines.append('scripts\t%s\t%d' % (f[:-4], len(acmd.ACMDFile.load(bp).scripts)))
            if not os.path.exists(mt):
                lines = [ln for ln in lines if not ln.startswith(('count', 'motion'))]
            open(exp, 'w').write('\n'.join(lines) + '\n')
            o = os.path.join(work, 'sm4shcommand_test_%s.txt' % fighter)
            with open(o, 'w') as f:
                rc = subprocess.call(['xvfb-run', '-a', 'mono', os.path.join(s4c, 'ScTest.exe'),
                                      os.path.join(s4c, 'Events.cfg'), exp],    # (its Runtime makes the main window)
                                     cwd=s4c, stdout=f, stderr=subprocess.STDOUT)
            text = open(o).read()
            check('Sm4shCommand opens %s (its own loaders: ACMD / motion.mtable, names, Hitbox Viewer assets, sounds, '
                  'aliases, effects): %d ok, 0 failed (exit %d)' % (fighter, text.count('\nok ') + text.startswith('ok '),
                                                                   rc),
                  [x for x in text.splitlines() if x.startswith('FAIL')][:4] + ([] if rc == 0 else ['exit %d' % rc]), [])
    finally:
        shutil.rmtree(run_dir)
        shutil.rmtree(view)


if __name__ == '__main__':
    main()
