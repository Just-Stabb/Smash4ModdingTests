#!/usr/bin/env python3
"""Own BINF ids for every sound bank of a new fighter kind (main, costume, cheer, Final Smash), so a port never
collides with its base fighter or another port. Needs tools/sound_alias_cave.py (v2) in the executable.

  python3 tools/sound_bank_ids.py renumber FIGHTER_SOUND_DIR --name NAME --out OUT [--json reference/port_sound_ids.json]
  python3 tools/sound_bank_ids.py copy-base BASE_SOUND_DIR --name NAME --out OUT [--json ...]
  python3 tools/sound_bank_ids.py check OUT_SOUND_DIR --name NAME [--json ...]

NAME: the kind's folder name in tools/extra_kinds.json (brave, edge, ...).
- renumber: every snd_se_ / snd_vc_<Cap>[_common][_ouen][_cNN].nus3bank of an installed fighter/<name>/sound
  folder gets the kind's own id (own_id); only the BINF id word changes. The ids the banks had (the ids the
  soundlabeltable rows their sounds use: the base's) are recorded as the kind's aliases in the JSON; a bank that
  already has its own id keeps the recorded alias.
- copy-base: a port whose sound folder is still its base's banks renamed (tools/add_fighter.py: Incineroar =
  Bowser's, Steve = Pit's): the base's vanilla banks (BASE_SOUND_DIR: fighter/<base>/sound) under the port's file
  names with the port's own ids; the Kirby-copy bank is left out (never loaded for kinds past 0x39).
- check: every bank there has the kind's own id, and the JSON's aliases are the base ids.

Why (docs/native-notes.md "Fighter sound banks: one bank an id"): nus3 refuses to load a bank whose BINF id is
already loaded (0x036774A4 -> 0x80000021); the later player's handle stays empty and all his sounds and voices are
silent. A port keeping its base's ids (Hero = Robin's 2051 / 6059, Squirtle and Supamario's voice = Mario's 6001,
...) broke whenever the base (or another port on those ids) was in the match. The game plays a fighter's sound from
his own banks, matched by the row's bank id or the bank's alias (+0x5C0 se, +0x5C4 vc, +0x5C8 cheer, +0x580
se_common), which sound_alias_cave.py sets to the recorded old ids; the soundlabeltable, scripts, MSC, sequences,
csb and the executable's own sound ids stay as they are.

Ids: own_id(kind, bank) = 46000 + (kind - 0x41) * 32 + slot: se 0, vc 1, cheer 2, se_common 3, se_cNN 8 + NN,
vc_cNN 16 + NN, se_common_cNN 24 + NN (46000-46991 for kinds 0x41-0x5F; the game's soundlabeltable ids are all
below 10000, vanilla's MTB alternates 2000s / 6000s).
"""
import argparse
import glob
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import minecraft_music as mm  # noqa: E402

IDS = os.path.join(HERE, '..', 'reference', 'port_sound_ids.json')
KINDS = os.path.join(HERE, 'extra_kinds.json')
ID_BASE, FIRST_KIND = 46000, 0x41
SLOTS = {'se': 0, 'vc': 1, 'ouen': 2, 'se_common': 3}
ALIAS_OF = {'se': 'se', 'vc': 'vc', 'ouen': 'ouen', 'se_common': 'se_common'}
BANK_RE = re.compile(r'snd_(se|vc)_([A-Za-z0-9]+?)(_common)?(_ouen)?(?:_c(\d\d))?\.nus3bank$')
VANILLA_FIGHTER_IDS = set(range(2000, 2144)) | set(range(6000, 6200))   # the game's own fighter banks


def own_id(kind, bank, nn=0):
    """bank: 'se' / 'vc' / 'ouen' / 'se_common'; nn: the costume (0 = the main file)"""
    k = kind - FIRST_KIND
    assert 0 <= k < 31, hex(kind)
    if nn:
        assert 1 <= nn <= 7 and bank in ('se', 'vc', 'se_common'), (bank, nn)
        slot = {'se': 8, 'vc': 16, 'se_common': 24}[bank] + nn
    else:
        slot = SLOTS[bank]
    return ID_BASE + 32 * k + slot


def is_own(kind, bid):
    return ID_BASE + 32 * (kind - FIRST_KIND) <= bid < ID_BASE + 32 * (kind - FIRST_KIND + 1)


def costume_id(main_id, nn):
    """new kinds' sound fix v1's costume ids (superseded by own_id; kept for reading v1 installs)"""
    if 2000 <= main_id < 2400:
        return 40000 + (main_id - 2000) * 8 + nn
    if 6000 <= main_id < 6400:
        return 44000 + (main_id - 6000) * 8 + nn
    raise ValueError(main_id)


def binf(data):
    """(name, id, file offset of the id word)"""
    secs = mm.sections(data)
    q = 24 + 8 * len(secs)
    for nm, body in secs:
        if nm == b'BINF':
            n = body[8]
            at = (9 + n + 3) & ~3
            return body[9:9 + n - 1].decode('latin1'), struct.unpack('<I', body[at:at + 4])[0], q + 8 + at
        q += 8 + len(body)
    raise ValueError('no BINF')


def with_id(data, new_id):
    out = bytearray(data)
    struct.pack_into('<I', out, binf(data)[2], new_id)
    return bytes(out)


def kind_record(name):
    for r in json.load(open(KINDS))['kinds']:
        if r['name'] == name:
            return int(r['kind'], 0), r.get('cap') or name.capitalize(), r['base']
    raise SystemExit('%s: not in %s' % (name, KINDS))


def classify(fname, cap):
    """('se' / 'vc' / 'ouen' / 'se_common', costume) or None"""
    m = BANK_RE.fullmatch(fname)
    if not m or m.group(2).lower() != cap.lower():
        return None
    typ, common, ouen, nn = m.group(1), m.group(3), m.group(4), int(m.group(5) or 0)
    if ouen:
        return ('ouen', 0) if typ == 'vc' and not common and not nn else None
    if common:
        return ('se_common', nn) if typ == 'se' else None
    return typ, nn


def load_json(path):
    if os.path.exists(path):
        return json.load(open(path))
    return {'_comment': 'tools/sound_bank_ids.py: per new kind its banks\' own BINF ids and the ids their '
                        'soundlabeltable rows use (alias: sound_alias_cave.py)', 'fighters': {}}


def save_json(path, d):
    d['fighters'] = dict(sorted(d['fighters'].items(), key=lambda kv: kv[1]['kind']))
    open(path, 'w').write(json.dumps(d, indent=1) + '\n')


def renumber(files, name, out_dir, js, rename=None):
    """files: [(path, file name in the port's folder)]; writes the banks with own ids, records the aliases"""
    kind, cap, base = kind_record(name)
    rec = js['fighters'].setdefault(name, {'kind': '0x%02X' % kind, 'cap': cap, 'base': base, 'alias': {},
                                          'banks': {}})
    os.makedirs(out_dir, exist_ok=True)
    report = []
    for path, fname in files:
        c = classify(fname, cap)
        if c is None:
            continue
        typ, nn = c
        data = open(path, 'rb').read()
        _n, old, _at = binf(data)
        new = own_id(kind, typ, nn)
        if not nn and not is_own(kind, old):
            rec['alias'][ALIAS_OF[typ]] = old
        if nn and typ in ('se', 'vc', 'se_common') and ALIAS_OF[typ] not in rec['alias'] and not is_own(kind, old) \
                and old in VANILLA_FIGHTER_IDS:
            rec['alias'][ALIAS_OF[typ]] = old            # a costume bank still on the main id (fix 71)
        open(os.path.join(out_dir, fname), 'wb').write(with_id(data, new))
        rec['banks'][fname[:-len('.nus3bank')]] = new
        report.append('  %s: id %d -> %d' % (fname, old, new))
    return rec, report


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('mode', choices=('renumber', 'copy-base', 'check'))
    ap.add_argument('dir')
    ap.add_argument('--name', required=True)
    ap.add_argument('--out')
    ap.add_argument('--json', default=IDS)
    a = ap.parse_args()
    js = load_json(a.json)
    kind, cap, base = kind_record(a.name)
    if a.mode == 'check':
        rec = js['fighters'].get(a.name, {})
        bad = 0
        for p in sorted(glob.glob(os.path.join(a.dir, '*.nus3bank'))):
            c = classify(os.path.basename(p), cap)
            if c is None:
                continue
            bid = binf(open(p, 'rb').read())[1]
            ok = bid == own_id(kind, *c)
            bad += not ok
            print('%s %s: id %d (want %d)' % ('ok  ' if ok else 'FAIL', os.path.basename(p), bid, own_id(kind, *c)))
        print('aliases %s' % rec.get('alias'))
        print('FAILED %d' % bad if bad else 'all passed')
        sys.exit(1 if bad else 0)
    out_dir = os.path.join(a.out, 'fighter', a.name, 'sound')
    if a.mode == 'renumber':
        files = [(p, os.path.basename(p)) for p in sorted(glob.glob(os.path.join(a.dir, '*.nus3bank')))]
    else:
        bcap = None
        files = []
        for p in sorted(glob.glob(os.path.join(a.dir, '*.nus3bank'))):
            f = os.path.basename(p)
            m = BANK_RE.fullmatch(f)
            if not m or 'Kirby_copy' in f:
                continue
            bcap = bcap or m.group(2)
            files.append((p, f.replace('_%s' % m.group(2), '_%s' % cap, 1)))
    rec, report = renumber(files, a.name, out_dir, js)
    print('%s (kind 0x%02X, base %s): aliases %s' % (a.name, kind, base, rec['alias']))
    print('\n'.join(report))
    save_json(a.json, js)


if __name__ == '__main__':
    main()
