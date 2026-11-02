#!/usr/bin/env python3
"""A new fighter's announcer call and victory fanfare (docs/new-fighter-slot.md "Announcer and fanfare").

  python3 tools/fighter_extras.py narration CHARACALL_BANK SOUNDLABELTABLE CALL_VOICE_DB_DIR OUT \\
      --ult-bank ULT_SOUND/bank/narration/vc_narration_characall --ult-tone poketrainer --name Pzenigame --id 64
  python3 tools/fighter_extras.py fanfare BGM_FIGHTER_FBB OUT --set 0x46=0xa [--set KIND=LIKE_KIND ...]

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
Mario's (0x3)."""
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
    for k, like in sets.items():
        rows[k] = list(rows[like])
    out = d[:8] + struct.pack('<I', len(rows)) + b''.join(struct.pack('<5I', *r) for r in rows)
    p = os.path.join(a.out, 'sound/config/bgm_fighter.fbb')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(out)
    print('bgm_fighter.fbb: %d -> %d entries; %s' % (n, len(rows), ', '.join(
        'kind 0x%X = 0x%X\'s (0x%X)' % (k, v, rows[k][4]) for k, v in sorted(sets.items()))))


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
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
