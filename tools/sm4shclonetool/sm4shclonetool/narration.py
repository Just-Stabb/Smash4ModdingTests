"""The announcer's call of a clone: on the character select (param/ui/ui_sound_call_voice_db.bin) and on the results
screen (the executable's call by fighter kind), both a copy of its base's call as labels of its own.

How the game calls a character (traced in cross_f.rpx):
- Character select: 0x0204CA14 calls 0x0294812C(the call database, character id, costume + 1): the entry with that id
  in ui_sound_call_voice_db.bin (16 sound ids after the id, one a costume; ids past 16 or 0 take costume 1) -> the
  sound id, played at 0x0204CA28 (0x031272B4 on the sound manager [0x102F7288]). The only reader of that database.
- Results screen ("... the winner is <name>"), and the other places that call a fighter: 0x02A65898(mode, fighter kind,
  costume, flag) (from the results script's play_result_characall_se 0x030EECB4 and three others): a switch on the
  KIND (tables 0x100C870C, 0x100C8640, 0x100C8624; costume variants for Olimar / Alph, Wii Fit Trainer, Villager, Robin,
  Bowser Jr.'s Koopalings 0x02A65790), kinds 0x3E-0x40 one call, anything past 0x40 none (-1: a clone had no call
  there), then the region's id remap 0x02A657BC (table 0x10340CE8).
- A sound id is (row << 16) | label of sound/config/soundlabeltable.bin; the vanilla roster's calls are labels of row
  0x38, bank snd_se_narration_characall (BINF 6085, sound/se/snd_se_narration_characall.nus3bank); the DLC fighters'
  of their own banks (snd_se_narration_characall_<Name>, one row each).

A clone's own call ("own", the default): every call id its base has (its 16 select ids and its results ids for every
costume) gets a new tone in the main narration bank, a copy of the base's tone (or the creator's WAV, encoded to DSP-ADPCM),
and a new label in that bank's row; the clone's 16 select ids and its results calls (exe.py's results-call table, see
clone_extras.py) point at them. "share": the clone keeps its base's ids (select) and the results call by its base's
kind. Nothing of the base's changes; the bank only grows.
"""
import os
import struct

from . import _paths  # noqa: F401
from . import audio as AU
from . import roster as R
from . import sound as SND

MAIN_BANK = 'sound/se/snd_se_narration_characall.nus3bank'
RESULTS_TABLES = {'low': 0x100C870C, 'mid': 0x100C8640, 'dlc': 0x100C8624, 'koopalings': 0x100C868C}
CALL_DB = 'ui/ui_sound_call_voice_db.bin'


def results_calls(read, kind, costume):
    """the call id 0x02A65898 gives a vanilla kind and costume before its region remap (-1: none); read(addr) ->
    the executable's word. A port of the function's switch, checked against the code itself in tests."""
    r8 = 0x380001
    k = kind
    if k >= 0x29:
        if k < 0x2D:
            if k == 0x29:
                return r8 + 0x32
            if k == 0x2A:
                return r8 + 0x52 if costume & 1 else r8 + 0x33
            if k == 0x2B:
                return r8 + 0x34
            return r8 + 0x44 if costume & 1 else r8 + 0x35          # 0x2C
        if k == 0x2D:
            return r8 + 0x36
        if k == 0x2E:
            if costume < 1 or costume > 7:
                return 0x380038
            return read(0x100C868C + 4 * costume)
        if k <= 0x39:
            return read(0x100C8624 + 4 * k)
        if k < 0x3E:
            return -1
        if k <= 0x40:
            return r8 + 0x28
        return -1
    if k < 0x1A:
        return read(0x100C870C + 4 * k)
    if k == 0x1A:
        return r8 + 0x43 if costume >= 4 else r8 + 0x17
    if k <= 0x27:
        return read(0x100C8640 + 4 * k)
    return r8 + 0x45 if costume & 1 else r8 + 0x31                   # 0x28


def base_ids(rec, param_dirs, read=None):
    """the base's call ids: its 16 select ids and its results ids for costumes 0-15 (a set, in order)"""
    import add_fighter as A
    f = A.ParamEdit(param_dirs, CALL_DB)
    row = next((e for e in f.entries() if e[0][1] == rec['base_ui_id']), None)
    out = []
    if row is not None:
        out += [row[k][1] for k in range(1, len(row))]
    if read is not None:
        from . import roster as RR
        bk = RR.KINDS.index(rec['base'])
        out += [results_calls(read, bk, c) & 0xFFFFFFFF for c in range(16)]
    seen = []
    for v in out:
        if v not in seen and v not in (0xFFFFFFFF, 0):
            seen.append(v)
    return seen


def own_call(rec, data_dir, out_data, read=None, mode='own', wav=None, log=print):
    """the clone's call: mode 'own' (copies of the base's tones), 'wav' (one tone from wav), 'share' (the base's).
    Sets rec['call_map'] = [[old id, new id], ...] for the executable's results call. Returns the written files."""
    rec['call_map'] = []
    if mode == 'share':
        log('announcer call: the base\'s (shared; the results screen calls the clone by its base\'s kind)')
        return []
    param_dirs = [os.path.join(out_data, 'param'), os.path.join(data_dir, 'param')]
    dirs = [out_data, data_dir]
    tp = R.first(dirs, 'sound/config/soundlabeltable.bin')
    bp = R.first(dirs, MAIN_BANK)
    if not tp or not bp:
        log('announcer call: no %s in the data folder: the clone keeps its base\'s call' % (
            'sound/config/soundlabeltable.bin' if not tp else MAIN_BANK))
        return []
    table = SND.Table(open(tp, 'rb').read())
    bank = AU.Bank(open(bp, 'rb').read())
    name, bid = bank.binf()
    row = table.row_of(bid)
    if row is None:
        log('announcer call: the soundlabeltable has no single row for %s (%d): kept the base\'s' % (name, bid))
        return []
    labels = table.tones(row)
    ids = base_ids(rec, param_dirs, read)
    # the banks the base's ids play from: the main one, or a DLC fighter's own (by BINF id, in sound/se/)
    others = {}
    for d in dirs:
        sd = os.path.join(d, 'sound', 'se')
        if os.path.isdir(sd):
            for f in sorted(os.listdir(sd)):
                if f.startswith('snd_se_narration_characall') and f.endswith('.nus3bank'):
                    try:
                        b = AU.Bank(open(os.path.join(sd, f), 'rb').read())
                        others.setdefault(b.binf()[1], b)
                    except Exception:
                        pass
    blob = AU.wav_to_idsp(wav) if mode == 'wav' and wav else None
    new_tone = None
    cmap = []
    for old in ids:
        r, lab = old >> 16, old & 0xFFFF
        if r >= len(table.rows) or lab >= len(table.tones(r)):
            continue
        src_bank = bank if table.rows[r][0] == bid else others.get(table.rows[r][0])
        if src_bank is None:
            log('announcer call: id 0x%08X is in bank %d, not in the data folder: left as the base\'s' % (
                old, table.rows[r][0]))
            continue
        tone = table.tones(r)[lab]
        if tone < 0 or tone >= len(src_bank.tones) or src_bank.tones[tone] is None:
            continue
        tname = 'snd_se_narration_characall_%s%s' % (rec['ui_name'], '' if not cmap else '_%02d' % len(cmap))
        if blob is not None:
            if new_tone is None:
                tmpl = next(i for i, t in enumerate(bank.tones) if t)
                new_tone = bank.add_copy(tmpl, 'snd_se_narration_characall_%s' % rec['ui_name'], blob)
                labels.append(new_tone)
            new = row << 16 | labels.index(new_tone)
        else:
            if src_bank is bank:
                t = bank.add_copy(tone, tname)
            else:                               # a DLC base: its tone copied into the main bank
                tmpl = next(i for i, t in enumerate(bank.tones) if t)
                t = bank.add_copy(tmpl, tname, src_bank.data_of(tone), src_bank.tones[tone]['volume'])
            labels.append(t)
            new = row << 16 | (len(labels) - 1)
        cmap.append([old, new])
    if not cmap:
        log('announcer call: no call of the base found to copy: the clone keeps its base\'s')
        return []
    table.set_row(row, labels)
    mp = dict(cmap)
    # the select's 16 ids
    import add_fighter as A
    import s4param
    f = A.ParamEdit(param_dirs, CALL_DB)
    e = next((x for x in f.entries() if x[0][1] == rec['ui_id']), None)
    if e is None:
        log('announcer call: ui_sound_call_voice_db.bin has no entry for id %d' % rec['ui_id'])
    else:
        for k in range(1, len(e)):
            A.setv(e, k, mp.get(e[k][1], e[k][1]))
    out = []
    for rel, data in ((MAIN_BANK, bank.data()), ('sound/config/soundlabeltable.bin', table.data()),
                      ('param/' + CALL_DB, s4param.build(f.items, f.data[:8]))):
        p = os.path.join(out_data, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(data)
        out.append(p)
    rec['call_map'] = cmap
    log('announcer call: %d tone(s) of its own in %s (row 0x%X, %d -> %d labels)%s: %s' % (
        len({n for _o, n in cmap}), name, row, len(labels) - len({n for _o, n in cmap}), len(labels),
        ' from %s' % os.path.basename(wav) if blob is not None else ' (copies of the base\'s)',
        ', '.join('0x%08X -> 0x%08X' % (a, b) for a, b in cmap)))
    return out


def call_tones(rec, data_dir, out_data):
    """[(sound id, IDSP bytes)] of the clone's select call (for the GUI's preview)"""
    import add_fighter as A
    dirs = [out_data, data_dir]
    tp, bp = R.first(dirs, 'sound/config/soundlabeltable.bin'), R.first(dirs, MAIN_BANK)
    if not tp or not bp:
        return []
    table = SND.Table(open(tp, 'rb').read())
    bank = AU.Bank(open(bp, 'rb').read())
    f = A.ParamEdit([os.path.join(out_data, 'param'), os.path.join(data_dir, 'param')], CALL_DB)
    e = next((x for x in f.entries() if x[0][1] in (rec.get('ui_id'), rec.get('base_ui_id'))), None)
    out = []
    for k in range(1, len(e or [])):
        sid = e[k][1]
        r, lab = sid >> 16, sid & 0xFFFF
        if r < len(table.rows) and table.rows[r][0] == bank.binf()[1] and lab < len(table.tones(r)):
            t = table.tones(r)[lab]
            if sid not in [s for s, _b in out]:
                out.append((sid, bank.data_of(t)))
    return out
