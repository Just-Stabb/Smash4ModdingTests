#!/usr/bin/env python3
"""Smash Run enemy sounds (step 2m, docs/smash-run-port.md "Step 2m"): the 3DS sound ids, how they map to the Wii U,
and a check of the map against the files.

  python3 tools/smashrun_sound.py S3DS_STB WIIU_STB ENEMY_SRC [WIIU_SE_DIR]

  S3DS_STB / WIIU_STB: sound/config/soundlabeltable.bin of the 3DS (s3ds_unpack extract) and of the Wii U;
  ENEMY_SRC: the 3DS enemy/ folder (enemy/<kind>/snd_se_enemy_<kind>.nus3bank, the banks tools/s3ds_enemy.py ships
  unchanged); WIIU_SE_DIR: the Wii U's sound/se (the twins' snd_se_enemy_Mczako*.nus3bank).

A sound id is (row << 16) | label in both games: soundlabeltable.bin ('STB\\0', little-endian; 16-byte rows {bank id,
label count, offset, 0}, then the label lists: label -> tone index, -1 none) gives the row's bank id (the BINF id in
the .nus3bank) and the label's tone in that bank (Wii U 0x0311EC30 / 0x0311EDC4, the table [[[[0x102F7288]] + 0x29C]
+ 4]). The 3DS Smash Run banks have rows in the 3DS table (kuribo 0x28D = bank 5002, ...); the Wii U table has NO row
for any of their bank ids, and every one of those row numbers is empty (-1) in it (vanilla and the user's latest,
Sephiroth's UI sound package): so no Wii U id reaches them and every Smash Run sound is silent. Step 2m registers the
3DS rows at their own row numbers at a Smash Run battle's start (snd_rows, smashrun_walker_cave.py): the mapped Wii U
id of each 3DS id is then the 3DS id itself, label for label, tone name for tone name (checked here). The converted
ACMD Sound_Effect ids (heiho, whitebear, dekakuribo, patapata) are rows of the same table: right as they are, no
remap. The twins' AI (mczako*) plays its own Wii U rows 0xBE2 / 0xBE3 / 0xBE4 (banks 5095-5097, the Fortress twins'
banks, never loaded on a Smash Run stage); their label lists name the same tones in the same order as the Smash Run
kinds' banks (Mczakostarfos_Attack = Starfos_Attack, ...): on a Smash Run stage those three rows' bank ids are set to
the kinds' (5019 / 5037 / 5052) and put back on any other enemy battle. The common id 15 (joucyu, row 0) is
snd_se_common_Hit_Muteki in both games. Row 0x4A6 (snd_se_fs_common, 5000; e.g. Stalfos's 0x4A60079 enemy_reflect)
has no Wii U bank file and no row: not mapped.
"""
import os
import struct
import sys

# the 3DS soundlabeltable rows of the ported kinds' banks: row -> (kind, the bank's BINF id, label -> tone index)
SND_ROWS = {
    0x28D: ('kuribo', 5002, (0, 1, 2, 3, 4)),
    0x28E: ('patapata', 5004, (0, 1, 2, 3, 4, 5)),
    0x291: ('dekakuribo', 5039, (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, -1, 13)),
    0x698: ('gordo', 5009, (0,)),
    0x69B: ('heiho', 5012, (0, 2, 1, 3)),
    0x69E: ('zima', 5015, (0,)),
    0x6A2: ('plasmawisp', 5019, (0, 1, 2, 3, 4)),
    0x6A3: ('waddledee', 5020, (0, 1)),
    0x6A8: ('waddledoo', 5026, (0,)),
    0x6A9: ('furiijio', 5027, (-1, 0, 1, 2)),
    0x6B0: ('churine', 5034, (-1, 0)),
    0x6B1: ('pooka', 5035, (-1, -1, -1, -1, 0, 1, 2, 3)),
    0x6B2: ('darios', 5037, (0, 1)),
    0x6BF: ('stalfos', 5052, (0, 1, 2, 3, 4, 5)),
    0x6CC: ('whitebear', 5068, (0, 1)),
    0x6D2: ('propellerheiho', 5076, (0, 1)),
    0x6D9: ('togezo', 5083, (0,)),
    0x89C: ('tikibuzz', 5016, (0, 1, 2, 3)),
    0x8A6: ('ghos', 5018, (0,)),
}
# the twins' own rows (their AI's play_se ids) -> the Smash Run kind's row; the Wii U banks they name
TWIN_SND = {0xBE2: (0x6A2, 'Mczakoplasmawisp', 5095), 0xBE3: (0x6B2, 'Mczakodarios', 5096),
            0xBE4: (0x6BF, 'Mczakostalfos', 5097)}
COMMON = {15: 'snd_se_common_Hit_Muteki'}      # row 0 (bank 2000 snd_se_joucyu) label 15, both games

# every 3DS play_se / stop_se of the ported kinds (enemy_fs.cro; Behavior::play_se 0x7B59A8 (id, bool) ->
# SoundModuleImpl::play_se 0x4C4B84, stop_se 0x4C3148 (handle, int)): (kind, the 3DS function, its role, the call,
# the id or 'stop', the handle's field on the 3DS) -> how step 2m ports it
SITES = (
    ('kuribo', 0x33280, 'state 4 enter (notice hop)', 0x333A4, 0x28D0002, None),
    ('kuribo', 0x32340, 'state 8 enter (Collapses)', 0x323A4, 0x28D0004, None),
    ('heiho', 0x1ABE0, 'state 6 enter (wall hop)', 0x1AC50, 0x69B0002, None),
    ('heiho', 0x1BA04, 'state 7 enter (notice)', 0x1BA88, 0x69B0002, None),
    ('heiho', 0x1BD54, 'state 7 update (the second hop)', 0x1BDD0, 0x69B0002, None),
    ('heiho', 0x1B92C, 'state 11 enter (run wall hop: no caller, not ported)', 0x1B99C, 0x69B0002, None),
    ('waddledoo', 0x7D060, 'state 8 enter (BeamShot; Wii U state 11)', 0x7D0D4, 0x6A80000, 0x1A4),
    ('waddledoo', 0x7DB04, 'state 8 update (the motion\'s end)', 0x7DC18, 'stop', 0x1A4),
    ('waddledoo', 0x7DD18, 'state 8 exit', 0x7DD30, 'stop', 0x1A4),
    ('churine', 0x3D970, 'state 7 update (the powder effect; Wii U state 9)', 0x3DB28, 0x6B00001, None),
    ('ghos', 0x109C0, 'slot 41 start', 0x10AA4, 0x8A60000, 0x200),
    ('ghos', 0x11094, 'slot 11 notify_on_damage (kinetic flag 2)', 0x110F4, 'stop', 0x200),
    ('ghos', 0x11140, 'slot 28 notify_on_remove', 0x11180, 'stop', 0x200),
    ('ghos', 0x113F0, 'slot 31 (an immune hit)', 0x11454, 15, None),
    ('tikibuzz', 0x780A4, 'state 4 enter (hold)', 0x78170, 0x89C0000, None),
    ('tikibuzz', 0x77964, 'state 5 enter (dive)', 0x77A0C, 0x89C0001, None),
    ('tikibuzz', 0x77F04, 'state 10 enter (stomped)', 0x78040, 0x89C0002, None),
    ('tikibuzz', 0x77E50, 'state 11 enter (gone)', 0x77EF0, 0x89C0003, None),
    ('furiijio', 0x6D0F0, 'state 2 enter (charge)', 0x6D1EC, 0x6A90001, None),
    ('furiijio', 0x6D4F0, 'state 5 enter (charge)', 0x6D5EC, 0x6A90001, None),
    ('furiijio', 0x6C258, 'state 4 enter (beam)', 0x6C3CC, 0x6A90002, 0x260),
    ('furiijio', 0x6C980, 'state 7 enter (sweep beam)', 0x6CAF4, 0x6A90002, 0x260),
    ('furiijio', 0x6D094, 'state 4 exit', 0x6D0E0, 'stop', 0x260),
    ('furiijio', 0x6D494, 'state 7 exit', 0x6D4E0, 'stop', 0x260),
    ('furiijio', 0x6DBDC, 'slot 57 (DownBoundEnd / DownWait on the ground, once)', 0x6DC34, 0x6A90003, None),
    ('propellerheiho', 0x99010, 'slot 41 start (the loop, one per kind)', 0x990C8, 0x6D20000, 'global 0x111270'),
    ('propellerheiho', 0x99E24, 'slot 55 (the item swap)', 0x9A070, 0x6D20001, None),
    ('propellerheiho', 0x99CC4, 'state 2 update (gone: the count)', 0x99D38, 'stop', 'global 0x111270'),
    ('propellerheiho', 0x99DD8, 'slot 71 notify_on_death (the count)', 0x99E10, 'stop', 'global 0x111270'),
    ('dekakuribo', 0x85E30, 'state 2 enter (landing)', 0x85E84, 0x2910009, None),
    ('dekakuribo', 0x85954, 'state 8 enter (brake)', 0x859AC, 0x2910008, None),
    ('dekakuribo', 0x86C14, 'state 10 enter (stepped)', 0x86C70, 0x291000C, None),
    ('dekakuribo', 0x859BC, 'state 11 enter (collapse)', 0x85A20, 0x291000B, None),
    ('togezo', 0x37A0C, 'state 5 enter (hatch)', 0x37AA4, 0x6D90000, None),
    ('pooka', 0x2343C, 'state 5 enter (back-off)', 0x23540, 0x6B10006, None),
    ('pooka', 0x21DAC, 'state 6 enter (lunge)', 0x21F50, 0x6B10007, None),
    ('pooka', 0x217F4, 'state 11 enter (pop)', 0x21980, 0x6B10005, None),
    ('pooka', 0x22900, 'slot 11 notify_on_damage (HP at the threshold)', 0x22A44, 0x6B10004, None),
)


def stb(path):
    """(rows [(bank, count, offset, 0)], label base bytes) of a soundlabeltable.bin"""
    d = open(path, 'rb').read()
    assert d[:4] == b'STB\0' and struct.unpack('<I', d[4:8])[0] == 1, path
    n, size = struct.unpack('<II', d[8:16])
    rows = [struct.unpack('<4I', d[16 + 16 * i:32 + 16 * i]) for i in range(n)]
    return rows, d[16 + size:]


def labels(table, row):
    rows, lab = table
    bank, n, off, _z = rows[row]
    return bank, list(struct.unpack('<%di' % n, lab[off:off + 4 * n]))


def bank_names(path):
    """(BINF name, BINF id, [TONE names]) of a .nus3bank (little-endian TOC; tone entries: name length at +0xC)"""
    d = open(path, 'rb').read()
    assert d[:4] == b'NUS3' and d[8:16] == b'BANKTOC '
    count = struct.unpack('<I', d[20:24])[0]
    q = 24 + count * 8
    secs = {}
    for i in range(count):
        name, size = struct.unpack('<4sI', d[24 + i * 8:32 + i * 8])
        secs[name] = d[q + 8:q + 8 + size]
        q += 8 + size
    b = secs[b'BINF']
    n = b[8]
    bname = b[9:9 + n - 1].decode('latin1')
    bid = struct.unpack('<I', b[(9 + n + 3) & ~3:][:4])[0]
    t = secs[b'TONE']
    tones = []
    for i in range(struct.unpack('<I', t[:4])[0]):
        o, s = struct.unpack('<II', t[4 + 8 * i:12 + 8 * i])
        e = t[o:o + s]
        tones.append(e[0xD:0xD + e[0xC] - 1].decode('latin1') if len(e) > 0xD else '')
    return bname, bid, tones


def tone_of(sid, rows, banks):
    """the tone name a sound id resolves to: rows {row: (bank id, labels)}, banks {bank id: tone names}"""
    row, lab = sid >> 16, sid & 0xFFFF
    if row not in rows:
        return None
    bank, labs = rows[row]
    if lab >= len(labs) or labs[lab] < 0 or bank not in banks:
        return None
    return banks[bank][labs[lab]]


def wiiu_rows(wiiu, sr_stage=True):
    """the Wii U rows after snd_rows: the table's own, the 3DS rows written where empty, the twins' rows (on a Smash
    Run stage) pointed at the kinds' banks"""
    rows = {}
    for i, r in enumerate(wiiu[0]):
        if r[0] != 0xFFFFFFFF:
            rows[i] = labels(wiiu, i)
    for row, (_k, bank, labs) in SND_ROWS.items():
        if row not in rows or rows[row][0] == bank:
            rows[row] = (bank, list(labs))
    if sr_stage:
        for row, (krow, _n, _b) in TWIN_SND.items():
            rows[row] = (SND_ROWS[krow][1], rows[row][1])
    return rows


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    t3, tw, src = stb(sys.argv[1]), stb(sys.argv[2]), sys.argv[3]
    sedir = sys.argv[4] if len(sys.argv) > 4 else None
    bad = 0
    banks = {}
    for row, (k, bank, labs) in sorted(SND_ROWS.items()):
        name, bid, tones = bank_names(os.path.join(src, k, 'snd_se_enemy_%s.nus3bank' % k))
        banks[bid] = tones
        b3, l3 = labels(t3, row)
        ok = bid == bank and b3 == bank and tuple(l3) == labs and tw[0][row][0] == 0xFFFFFFFF
        bad += not ok
        print('%s row 0x%X: %s id %d, 3DS row %d %s, Wii U row %s%s' % (
            'ok  ' if ok else 'FAIL', row, name, bid, b3, l3,
            'empty' if tw[0][row][0] == 0xFFFFFFFF else 'bank %d' % tw[0][row][0], '' if ok else ' <-'))
    rows3 = {r: labels(t3, r) for r in SND_ROWS}
    rowsw = wiiu_rows(tw)
    for k, fn, role, at, sid, _f in SITES:
        if not isinstance(sid, int) or sid >> 16 == 0:
            continue
        a, b = tone_of(sid, rows3, banks), tone_of(sid, rowsw, banks)
        ok = a is not None and a == b
        bad += not ok
        print('%s %s 0x%X %s: 0x%07X 3DS %s, Wii U %s' % ('ok  ' if ok else 'FAIL', k, at, role, sid, a, b))
    if sedir:
        for trow, (krow, tname, tbank) in sorted(TWIN_SND.items()):
            name, bid, tones = bank_names(os.path.join(sedir, 'snd_se_enemy_%s.nus3bank' % tname))
            wb, wl = labels(tw, trow)
            for lab, ti in enumerate(wl):
                twin = tones[ti].replace('Mczako', '').lower() if ti >= 0 else None
                ours = tone_of((trow << 16) | lab, rowsw, banks)
                ok = bid == tbank == wb and twin is not None and ours is not None and \
                    ours.lower().replace('snd_se_enemy_', '') == twin.replace('snd_se_enemy_', '')
                bad += not ok
                print('%s twin 0x%X%04X: %s -> %s' % ('ok  ' if ok else 'FAIL', trow, lab, tones[ti] if ti >= 0
                                                        else None, ours))
    print('%d failures' % bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
