#!/usr/bin/env python3
"""Kirby's Hero / Sephiroth copy sounds in his own Smash 4 banks (fighters/kirby/specials.md "Hero copy fix v1").

  python3 tools/kirby_copy_sound.py ULT_VOICE S4_KIRBY_SOUND EDGE_SE_BANK SOUNDLABELTABLE OUT [--check]

ULT_VOICE: Ultimate's sound/bank/fighter_voice (vc_kirby_copy_brave.nus3audio / .nus3bank, vc_kirby_copy_edge.*:
the user's kirby_fighter_voice_ssbu). S4_KIRBY_SOUND: Kirby's Smash 4 fighter/kirby/sound/ (snd_se_Kirby.nus3bank,
BINF id 2009; snd_vc_Kirby.nus3bank, id 6006). EDGE_SE_BANK: Sephiroth's Smash 4 snd_se_Edge.nus3bank (the port's,
ultimate_sound.py: Ultimate's se_edge tones after Zelda's, BINF 2018 = Zelda's id). SOUNDLABELTABLE: the install's
sound/config/soundlabeltable.bin.

Writes OUT/fighter/kirby/sound/snd_vc_Kirby.nus3bank and snd_se_Kirby.nus3bank (Kirby's own tones first, then the
new ones; their data and TONE volumes as the source banks have them; the new TONE entries copy the bank's first
one-shot's, as ultimate_sound.py) and OUT/sound/config/soundlabeltable.bin (Kirby's se row 10 and voice row 63 grown
by their labels, every other row as it was), and prints the ids (row << 16 | label) kirby.c plays. Kirby's own
labels stay first, so none of his ids move.

- Voice (snd_vc_Kirby): Ultimate's vc_kirby_copy_brave_01-04 / vc_kirby_copy_edge_01-04, Ultimate's IDSP as it is.
  Kirby's Ultimate copy sound scripts (reference/kirby_copy_ultimate_acmd.txt "Copy sound scripts"; the unnamed
  hashes there are these names: hash40 = length 0x15 / 0x16, crc32): Hero hold _01 (PLAY_STATUS at 2), Frizz _02
  at 8, Frizzle _03 at 11, Kafrizz _04 at 17 (an is_flag test picks these or the Japanese random
  vc_kirby_copy_brave_rnd_special_n02 / 03 / 04_jp: these are the other side); Sephiroth charge
  vc_kirby_copy_edge_01 at 2 and _04 at 119 (Gigaflare), Flare _02 at 12, Megaflare _03 at 12.
- Sephiroth's se (snd_se_Kirby): se_edge_special_n01 (the charge, PLAY_STATUS at 1), n02_01 (Flare, 2), n03_01
  (Megaflare, 2), n04_01 (Gigaflare, 119), copied from his Smash 4 bank. In Kirby's own bank because a sound id is
  matched against the banks of the fighter playing it (cross_f.rpx 0x03120978, docs/ultimate-fighter-port.md):
  Kirby's Sephiroth copy is granted as his Robin copy, so Zelda's / Sephiroth's id 2018 needn't be among his banks
  (Kirby's own vanilla scripts play a copied fighter's row only for that copy: 0x12005B, Zelda's N01, in her copy's).
  The Hero copy's se (v5) stay Hero's own ids (bank 2051 = Robin's, which Kirby's vanilla Robin copy scripts play:
  0x7640028).

--check: OUT's files hold the tones and labels as built, a second run adds nothing, and only rows 10 / 63 changed.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fighter_own_bank as fb  # noqa: E402
import minecraft_music as mm  # noqa: E402
import minecraft_sound as ms  # noqa: E402
import ultimate_sound as us  # noqa: E402

VOICES = ['vc_kirby_copy_brave_01', 'vc_kirby_copy_brave_02', 'vc_kirby_copy_brave_03', 'vc_kirby_copy_brave_04',
          'vc_kirby_copy_edge_01', 'vc_kirby_copy_edge_02', 'vc_kirby_copy_edge_03', 'vc_kirby_copy_edge_04']
EDGE_SE = ['special_n01', 'special_n02_01', 'special_n03_01', 'special_n04_01']
BANKS = {'vc': ('snd_vc_Kirby', 6006), 'se': ('snd_se_Kirby', 2009)}


def tone_names(data):
    _s, tones = ms.tones_of(data)
    return [ms.parse_entry(e)[1] if len(e) >= 0x10 else '' for e in tones]


def s4_tone(data, name):
    """(IDSP, volume dB) of a Smash 4 bank's tone"""
    pack = dict(mm.sections(data))[b'PACK']
    _s, tones = ms.tones_of(data)
    for e in tones:
        if len(e) >= 0x10:
            _h, n, rest = ms.parse_entry(e)
            if n == name:
                off, size = struct.unpack('<II', rest[4:12])
                return bytes(pack[off:off + size]), struct.unpack('<f', rest[12:16])[0]
    raise SystemExit('no tone %s' % name)


def grow(data, table, kind, sounds):
    """the bank with sounds [(rest of the name, IDSP, volume)] added once; its row's labels grown; {rest: id}"""
    name, bid = fb.binf(data)
    assert (name, bid) == BANKS[kind], (name, bid)
    row = table.row_of(bid)
    labels = table.tones(row)
    prefix = name + '_'
    new = [s for s in sounds if prefix + s[0] not in tone_names(data)]
    if new:
        data, _first = us.bank(data, prefix, name, bid, new, us.template_tone(data))
    index = {n: i for i, n in enumerate(tone_names(data))}
    lab = list(labels)
    for s in sounds:
        if index[prefix + s[0]] not in lab:
            lab.append(index[prefix + s[0]])
    if lab != labels:
        table.set_row(row, lab)
    return data, {s[0]: (row << 16) | lab.index(index[prefix + s[0]]) for s in sounds}, row


def build(ult, kirby_sound, edge_bank, table_path):
    table = fb.Table(open(table_path, 'rb').read())
    voices = []
    for v in VOICES:
        tones, _first = us.ult_tones(os.path.join(ult, v.rsplit('_', 1)[0]))
        hit = [(b, vol) for n, b, vol in tones if n == v and b]
        assert hit, v
        voices.append((v[len('vc_kirby_'):], hit[0][0], hit[0][1]))
    edge = open(edge_bank, 'rb').read()
    assert fb.binf(edge) == ('snd_se_Edge', 2018), fb.binf(edge)
    ses = [('edge_' + n,) + s4_tone(edge, 'snd_se_Edge_' + n) for n in EDGE_SE]
    vc, vc_ids, vc_row = grow(open(os.path.join(kirby_sound, 'snd_vc_Kirby.nus3bank'), 'rb').read(), table, 'vc', voices)
    se, se_ids, se_row = grow(open(os.path.join(kirby_sound, 'snd_se_Kirby.nus3bank'), 'rb').read(), table, 'se', ses)
    ids = dict(('vc_kirby_' + k, v) for k, v in vc_ids.items())
    ids.update(('se_' + k, v) for k, v in se_ids.items())
    return vc, se, table.data(), ids, (se_row, vc_row)


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) != 5:
        sys.exit(__doc__)
    ult, kirby_sound, edge_bank, table_path, out = a
    od = os.path.join(out, 'fighter', 'kirby', 'sound')
    ot = os.path.join(out, 'sound', 'config', 'soundlabeltable.bin')
    vc, se, tdata, ids, rows = build(ult, kirby_sound, edge_bank, table_path)
    if '--check' in sys.argv:
        vc2, se2, t2, ids2, _r = build(ult, od, edge_bank, ot)
        assert (vc2, se2, t2, ids2) == (open(os.path.join(od, 'snd_vc_Kirby.nus3bank'), 'rb').read(),
                                        open(os.path.join(od, 'snd_se_Kirby.nus3bank'), 'rb').read(),
                                        open(ot, 'rb').read(), ids), 'not as built'
        assert (vc, se, tdata) == (vc2, se2, t2), 'a second run changed something'
        old, new = fb.Table(open(table_path, 'rb').read()), fb.Table(t2)
        changed = [i for i in range(len(old.rows)) if old.tones(i) != new.tones(i) or old.rows[i][0] != new.rows[i][0]]
        assert changed == sorted(rows), changed
        print('check: ok (rows changed: %s; a second run adds nothing)' % changed)
    else:
        os.makedirs(od, exist_ok=True)
        os.makedirs(os.path.dirname(ot), exist_ok=True)
        open(os.path.join(od, 'snd_vc_Kirby.nus3bank'), 'wb').write(vc)
        open(os.path.join(od, 'snd_se_Kirby.nus3bank'), 'wb').write(se)
        open(ot, 'wb').write(tdata)
    for k, v in ids.items():
        print('%-26s 0x%08X' % (k, v))


if __name__ == '__main__':
    main()
