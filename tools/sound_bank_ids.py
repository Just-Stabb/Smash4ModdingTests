#!/usr/bin/env python3
"""Own BINF ids for new fighters' costume sound banks (snd_se_ / snd_vc_<Cap>_cNN), so a second player of the
fighter in another costume gets his sounds. Needs tools/sound_alias_cave.py in the executable.

  python3 tools/sound_bank_ids.py FIGHTER_SOUND_DIR [...] --out OUT [--check]

FIGHTER_SOUND_DIR: an installed fighter/<name>/sound folder (its snd_se_<Cap>.nus3bank etc.). Writes
OUT/fighter/<name>/sound/<every _cNN bank whose id changed> and prints, per fighter, the main banks' ids (the
soundlabeltable rows' ids, which sound_alias_cave.py's ALIASES must hold for his kind).

Why (docs/native-notes.md "Fighter sound banks: one bank an id"): nus3 refuses to load a bank whose BINF id is
already loaded (0x036774A4 finds it in the bank list: 0x0367CF98 -> error 0x80000021); the game then has no bank
for that fighter (0x033EDABC returns 0, the SoundModule's handle stays empty) and every sound and voice of his is
silent. A fighter's banks are loaded per player in player order, so a second Hero (costume 1: snd_se_Brave_c01, id
2051 like snd_se_Brave) was silent while the first played. Vanilla gives costume banks their own ids (Bowser Jr.'s
Koopalings, Robin's se_common) and fightermodelbanktable.mtb tells the game the base id they stand for
(SoundModule +0x5C0 se / +0x5C4 vc, read by the bank finder 0x02C71898 through vt +0x344); the MTB names its
records from a 13-name table in the executable, so new kinds get that alias from sound_alias_cave.py instead.

Ids: costume_id(main id, NN): 40000 + (id - 2000) * 8 + NN for se ids 2000-2399, 44000 + (id - 6000) * 8 + NN for vc
ids 6000-6399 (every id the game's soundlabeltable uses is below 10000; vanilla's MTB alternates are 2000s / 6000s).
Only the BINF id word changes; names, tones and data stay. --check: OUT's banks carry exactly these ids, and every
bank of each fighter has an id no other of his banks has.
"""
import argparse
import glob
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import minecraft_music as mm  # noqa: E402


def costume_id(main_id, nn):
    assert 1 <= nn <= 7, nn
    if 2000 <= main_id < 2400:
        return 40000 + (main_id - 2000) * 8 + nn
    if 6000 <= main_id < 6400:
        return 44000 + (main_id - 6000) * 8 + nn
    raise ValueError('bank id %d: not a fighter se / vc id' % main_id)


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
    _n, _old, at = binf(data)
    out = bytearray(data)
    struct.pack_into('<I', out, at, new_id)
    return bytes(out)


def plan(sound_dir):
    """[(file, old id, new id)] for one fighter's costume banks; {kind: main id}"""
    out, mains = [], {}
    for path in sorted(glob.glob(os.path.join(sound_dir, 'snd_*.nus3bank'))):
        m = re.fullmatch(r'snd_(se|vc)_([A-Za-z0-9]+)\.nus3bank', os.path.basename(path))
        if m:
            mains[m.group(1)] = binf(open(path, 'rb').read())[1]
    for path in sorted(glob.glob(os.path.join(sound_dir, 'snd_*_c[0-9][0-9].nus3bank'))):
        m = re.fullmatch(r'snd_(se|vc)_([A-Za-z0-9]+)_c(\d\d)\.nus3bank', os.path.basename(path))
        if not m or m.group(1) not in mains:
            continue
        old = binf(open(path, 'rb').read())[1]
        new = costume_id(mains[m.group(1)], int(m.group(3)))
        out.append((path, old, new))
    return out, mains


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('sound_dirs', nargs='+')
    ap.add_argument('--out', required=True)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    bad = 0
    for d in a.sound_dirs:
        name = os.path.basename(os.path.dirname(os.path.normpath(d)))
        todo, mains = plan(d)
        dst = os.path.join(a.out, 'fighter', name, 'sound')
        print('%s: main ids se %s vc %s (sound_alias_cave.py ALIASES)' % (name, mains.get('se'), mains.get('vc')))
        ids = {}
        for path, old, new in todo:
            out = os.path.join(dst, os.path.basename(path))
            if a.check:
                got = binf(open(out, 'rb').read())[1] if os.path.exists(out) else (old if old == new else None)
                ok = got == new
                bad += not ok
                print('  %s %s: id %s (want %d)' % ('ok  ' if ok else 'FAIL', os.path.basename(path), got, new))
                ids[os.path.basename(path)] = got
                continue
            if old != new:
                os.makedirs(dst, exist_ok=True)
                open(out, 'wb').write(with_id(open(path, 'rb').read(), new))
            print('  %s: id %d -> %d' % (os.path.basename(path), old, new))
            ids[os.path.basename(path)] = new
        if a.check:
            ids.update({'main ' + k: v for k, v in mains.items()})
            dup = sorted({v for v in ids.values() if list(ids.values()).count(v) > 1})
            bad += bool(dup)
            print('  %s every bank its own id%s' % ('ok  ' if not dup else 'FAIL', '' if not dup else ': %s' % dup))
    if a.check:
        print('FAILED %d' % bad if bad else 'all passed')
        sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
