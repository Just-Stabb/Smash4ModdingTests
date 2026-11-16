#!/usr/bin/env python3
"""A new fighter's announcer call and victory fanfare (docs/new-fighter-slot.md "Announcer and fanfare").

  python3 tools/fighter_extras.py narration CHARACALL_BANK SOUNDLABELTABLE CALL_VOICE_DB_DIR OUT \\
      --ult-bank ULT_SOUND/bank/narration/vc_narration_characall --ult-tone poketrainer --name Pzenigame --id 64
  python3 tools/fighter_extras.py fanfare BGM_FIGHTER_FBB OUT --set 0x46=0xa [--set KIND=LIKE_KIND ...]
  python3 tools/fighter_extras.py common COMMONSOUNDTABLE_CSB OUT [--set Pzenigame=Mario ...]

narration: the character select's announcer call is a sound id per character id and costume
(param/ui/ui_sound_call_voice_db.bin: id, then 16 ids, one a costume). The vanilla roster's live in
sound/se/snd_se_narration_characall.nus3bank (BINF 0x17C5, soundlabeltable row 0x38: id 0x0038LLLL); the
DLC fighters' in their own banks, whose file names the executable holds (Mewtwo, Lucas, Roy, Ryu, Cloud,
Bayonetta, Kamui: no %s form for other names). So a new fighter's call is appended to the main bank as a
new label (Ultimate's tone, IDSP as is: tools/ultimate_sound.py bank), the row grown by it, and the
character's 16 ids set to it. add_fighter.py gave a new id its base's call (Squirtle: Mario's).
Ultimate has no call for every fighter it has: its Pokemon Trainer's Pokemon are called "Pokemon Trainer"
(vc_narration_characall_poketrainer), so Squirtle takes that one.

fanfare: sound/config/bgm_fighter.fbb ('FBB\\0', u32 1, u32 count, then count entries of 5 u32, LE; the
fanfare's BGM id at +0x10) holds one entry per fighter kind, 0x00-0x39; the new kinds (0x41+) had none.
The file is extended to the highest kind asked, each new entry a copy of LIKE_KIND's (the vanilla fighter
of the same series: Pokemon -> Pikachu 0xA, Final Fantasy -> Cloud 0x37), kinds in between a copy of
Mario's (0x3).

The executable names both files' records from its own tables by record index and matches them by the fighter's
Capitalised name; records past those tables were unnamed, so a new kind's record was never found (no fanfare,
KO voices or chant) until tools/kind_expand.py grew the tables (its SOUND_NAME_TABLES): a new kind's fbb record
is its kind, its csb record 0x3E + kind - 0x41 (kind_expand.sound_record).

common: sound/config/commonsoundtable.csb ('CSB\0', u32 1, u16 4 values, u16 count, then count records of a
16-byte name (unused) and 4 u32, LE) holds per fighter the voices the game plays for it itself: three
(u16 label, u16 soundlabeltable row) pairs (Mario: MissFoot01, MissFoot02, Damage_hoshikie, the KO screams),
then the crowd's chant bank's row (u16 0, u16 row). Every new kind of tools/extra_kinds.json gets a copy of its
base's record (the port's voice and chant banks keep the base's bank ids, so the base's labels name the port's
own tones: Squirtle's MissFoot01 is his Ultimate missfoot01); --set CAP=LIKE_CAP takes another fighter's.
A record the file already holds for a new kind (anything but the empty placeholder this tool pads with) is an
earlier port's and is KEPT: only missing records are added (Squirtle's own KO-voice record, 0x43, was overwritten
with Mario's by the old every-kind rewrite). --only NAME (repeatable: name, Capitalised name or kind) limits the run
to those kinds; --replace rewrites their existing records too (never without --only).

  python3 tools/fighter_extras.py common COMMONSOUNDTABLE_CSB OUT [--only master] [--set Pzenigame=Mario ...] [--replace]

fanfare writes only the kinds given with --set (and appends Mario's entry for missing kinds below them); it says
when a --set kind's entry already existed and what it was. Tests: tools/fighter_extras_test.py."""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def narration(a):
    import add_fighter as A
    import fighter_own_bank as fb
    import s4param
    import ultimate_sound as us
    data = open(a.bank, 'rb').read()
    name, bid = fb.binf(data)
    tones, _ = us.ult_tones(a.ult_bank)
    want = 'vc_narration_characall_' + a.ult_tone
    hit = [t for t in tones if t[0] == want and t[1]]
    if not hit:
        sys.exit('%s: no tone %s' % (a.ult_bank, want))
    _n, blob, vol = hit[0]
    new, first = us.bank(data, name + '_', name, bid, [(a.name, blob, vol)], us.template_tone(data))
    tab = fb.Table(open(a.table, 'rb').read())
    row = tab.row_of(bid)
    old = tab.tones(row)
    assert len(old) == first, 'row 0x%X has %d labels, the bank %d tones' % (row, len(old), first)
    tab.set_row(row, old + [first])
    sid = row << 16 | first
    f = A.ParamEdit([a.db_dir], 'ui/ui_sound_call_voice_db.bin')
    ents = f.entries()
    x = ents[a.id - 1]
    assert x[0][1] == a.id, 'position %d holds id %d' % (a.id - 1, x[0][1])
    for k in range(1, len(x)):
        A.setv(x, k, sid)
    for rel, blob_ in (('sound/se/%s.nus3bank' % name, new), ('sound/config/soundlabeltable.bin', tab.data()),
                       ('param/ui/ui_sound_call_voice_db.bin', s4param.build(f.items, f.data[:8]))):
        p = os.path.join(a.out, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(blob_)
    print('%s: tone %d = %s (%d bytes); row 0x%X %d -> %d labels; id %d -> 0x%08X' % (
        name, first, want, len(blob), row, len(old), len(old) + 1, a.id, sid))


def fanfare(a):
    d = open(a.fbb, 'rb').read()
    assert d[:4] == b'FBB\0'
    n = struct.unpack_from('<I', d, 8)[0]
    rows = [list(struct.unpack_from('<5I', d, 0xC + 0x14 * k)) for k in range(n)]
    sets = {int(k, 0): int(v, 0) for k, v in (s.split('=') for s in a.set)}
    top = max(sets) + 1
    while len(rows) < top:
        rows.append(list(rows[0x3]))
    replaced = []
    for k, like in sets.items():
        if k < n and rows[k] != rows[like]:
            replaced.append('kind 0x%X had BGM 0x%X' % (k, rows[k][4]))
        rows[k] = list(rows[like])
    out = d[:8] + struct.pack('<I', len(rows)) + b''.join(struct.pack('<5I', *r) for r in rows)
    p = os.path.join(a.out, 'sound/config/bgm_fighter.fbb')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(out)
    print('bgm_fighter.fbb: %d -> %d entries; %s' % (n, len(rows), ', '.join(
        'kind 0x%X = 0x%X\'s (0x%X)' % (k, v, rows[k][4]) for k, v in sorted(sets.items()))))
    if replaced:
        print('  replaced (asked with --set): ' + ', '.join(replaced))


def csb_parse(d):
    """(nval, records): commonsoundtable.csb's records as bytearrays"""
    assert d[:4] == b'CSB\0'
    nval, n = struct.unpack_from('<HH', d, 8)
    size = 0x10 + 4 * nval
    assert len(d) == 0xC + size * n, 'commonsoundtable.csb: %d bytes for %d records' % (len(d), n)
    return nval, [bytearray(d[0xC + size * i:0xC + size * (i + 1)]) for i in range(n)]


def csb_build(head, nval, recs):
    return head[:8] + struct.pack('<HH', nval, len(recs)) + b''.join(bytes(x) for x in recs)


def csb_placeholder(nval):
    """the empty record padding the file up to a new kind's index (no name, no voices, no chant)"""
    return bytearray(b'\0' * 16 + b'\xff' * (4 * (nval - 1)) + b'\0' * 4)


def csb_merge(recs, nval, want, replace=False):
    """recs: the file's records; want: {index: record} to give new kinds. A record already in the file (not the
    placeholder) is an earlier port's: kept unless replace. Returns (records, [(index, 'added' / 'kept' /
    'replaced')])."""
    recs = [bytearray(x) for x in recs]
    none = csb_placeholder(nval)
    while len(recs) < max(want, default=-1) + 1:
        recs.append(bytearray(none))
    done = []
    for i, rec in sorted(want.items()):
        if recs[i] == none:
            recs[i] = bytearray(rec)
            done.append((i, 'added'))
        elif recs[i] == rec:
            done.append((i, 'kept (already this record)'))
        elif replace:
            recs[i] = bytearray(rec)
            done.append((i, 'replaced'))
        else:
            done.append((i, 'kept (the file\'s own)'))
    return recs, done


def pick_kinds(kinds, only):
    """the extra_kinds.json records named by --only (name, Capitalised name or kind)"""
    if not only:
        return kinds
    out = []
    for o in only:
        hit = [r for r in kinds if o in (r['name'], r['cap']) or (o.lower().startswith('0x') and int(o, 16) == r['kind'])]
        if not hit:
            sys.exit('--only %s: no such kind in the extra kinds' % o)
        out += [r for r in hit if r not in out]
    return out


def common(a):
    import kind_expand as K
    if a.replace and not a.only:
        sys.exit('--replace needs --only: it would overwrite every earlier port\'s own record')
    d = open(a.csb, 'rb').read()
    nval, recs = csb_parse(d)
    n = len(recs)
    img = K.Image(K.RPX)
    addr, _hi, _lo, _cmp, old = K.SOUND_NAME_TABLES['csb']
    names = [img.cstr(img.w(addr + 4 * i)) for i in range(old)]
    cap, kinds = K.load_spec(a.kinds)
    caps = [img.cstr(img.w(K.TABLES['cap'][0] + 4 * k)) for k in range(K.OLD_N)]
    like = {r['cap']: caps[r['bkind']] if 'bkind' in r else caps[K.kind_index(
        [img.cstr(img.w(K.TABLES['lower'][0] + 4 * k)) for k in range(K.OLD_N)], r['base'])] for r in kinds}
    like.update(dict(s.split('=') for s in a.set or []))
    want, src_of = {}, {}
    for r in pick_kinds(kinds, a.only):
        src = like[r['cap']]
        i = K.sound_record('csb', r['kind'])
        want[i] = recs[names.index(src) if src in names else caps.index(src)]
        src_of[i] = (r['cap'], src)
    new, done = csb_merge(recs, nval, want, a.replace)
    blob = csb_build(d, nval, new)
    p = os.path.join(a.out, 'sound/config/commonsoundtable.csb')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(blob)
    print('commonsoundtable.csb: %d -> %d records (label/row x3, 0/chant row)' % (n, len(new)))
    for i, what in done:
        v = struct.unpack_from('<%dH' % (2 * nval), new[i], 0x10)
        print('  %s (record 0x%X) %s%s: %s' % (src_of[i][0], i, what,
                                              ' = %s\'s' % src_of[i][1] if what in ('added', 'replaced') else '',
                                              ' '.join('%X/%X' % (v[2 * k], v[2 * k + 1]) for k in range(nval))))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('narration')
    p.add_argument('bank')
    p.add_argument('table')
    p.add_argument('db_dir', help='a param/ folder holding ui/ui_sound_call_voice_db.bin (the one installed)')
    p.add_argument('out')
    p.add_argument('--ult-bank', required=True, help='Ultimate\'s vc_narration_characall, without the extension')
    p.add_argument('--ult-tone', required=True, help='its tone name after vc_narration_characall_')
    p.add_argument('--name', required=True)
    p.add_argument('--id', type=int, required=True, help='the character id (ui_character_db)')
    p.set_defaults(fn=narration)
    p = sub.add_parser('fanfare')
    p.add_argument('fbb')
    p.add_argument('out')
    p.add_argument('--set', action='append', required=True, help='KIND=LIKE_KIND')
    p.set_defaults(fn=fanfare)
    p = sub.add_parser('common')
    p.add_argument('csb')
    p.add_argument('out')
    p.add_argument('--kinds', default=os.path.join(HERE, 'extra_kinds.json'))
    p.add_argument('--set', action='append', help='CAP=LIKE_CAP (Capitalised names; default: the base)')
    p.add_argument('--only', action='append', help='only this kind (name, Capitalised name or 0xKIND); repeatable')
    p.add_argument('--replace', action='store_true', help='with --only: rewrite those kinds\' existing records '
                   '(default: an existing record is an earlier port\'s own and is kept)')
    p.set_defaults(fn=common)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
