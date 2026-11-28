"""Every voice and sound line of a clone, by category, with replace-with-WAV (its own banks' tones; the base's files are
never touched).

Where a fighter's voices come from (cross_f.rpx; sound.py / clone_extras.py):
- ACMD (taunts / appeals, attacks, specials, jumps, ledge, victory poses' sound scripts): sound ids on the clone's own
  rows (moved by sound.own_banks), playing from its own banks;
- the game's own calls by the base's rows (the KO screams / star KO / missfoot of commonsoundtable.csb, damage voices,
  MSC scripts, the voice sequences soundseq_<Cap>.sqb, the base's native code): the clone's banks answer for the base's
  ids (the alias, clone_extras.py), so they play the clone's own tones too;
- the crowd's cheer: snd_vc_<Cap>_ouen (its own id, the cheer alias);
- the costume banks (snd_vc_<Cap>_cNN ...): own ids, same rows;
- Kirby's copy voices: snd_se_vc_Kirby_copy_<Cap> (Kirby plays it while he holds the clone's copy);
- the announcer's call (narration.py) and the victory fanfare (music.py).
So replacing a tone in the clone's bank changes that line wherever the game plays it for the clone, and nowhere for its
base. Replacement tones are the creator's WAVs encoded to DSP-ADPCM (vendor/dspadpcm.py), mono 48000 Hz, the
replaced tone's TONE settings (group, volume) kept.
"""
import os
import re

from . import _paths  # noqa: F401
from . import audio as AU

CATEGORIES = [('taunt', r'appeal'), ('victory', r'win|result'), ('hurt', r'damage(?!_hoshikie)|dmg|furafura|sleep'),
              ('KO', r'missfoot|hoshikie|dead|_ko\b|falldown'), ('attack', r'attack|smash|throw|catch|swing'),
              ('special', r'special|final'), ('jump', r'jump'), ('ledge', r'cliff|ledge'),
              ('other', r'.')]
WIN_MOTIONS = ('win1', 'win1wait', 'win2', 'win2wait', 'win3', 'win3wait', 'lose')


def bank_kind(fname, cap):
    f = fname[:-len('.nus3bank')]
    if f.startswith('snd_se_vc_Kirby_copy_'):
        return 'kirby copy'
    if f.endswith('_ouen'):
        return 'cheer'
    if f.startswith('snd_vc_'):
        return 'voice'
    return 'sound'


def category(name, bank):
    if bank == 'cheer':
        return 'cheer'
    if bank == 'kirby copy':
        return 'Kirby copy'
    low = name.lower()
    for cat, rx in CATEGORIES:
        if re.search(rx, low):
            return cat
    return 'other'


def sound_dir(rec, out_data):
    return os.path.join(out_data, 'fighter', rec['name'], 'sound')


def win_tones(rec, out_data):
    """{(bank file, tone)} played by the victory poses' sound scripts (Win1 ... Lose), through the soundlabeltable"""
    import acmd
    from . import roster as R
    from . import sound as SND
    out = set()
    p = os.path.join(out_data, 'fighter', rec['name'], 'script', 'animcmd', 'body', 'sound.bin')
    tp = R.first([out_data], 'sound/config/soundlabeltable.bin')
    if not os.path.exists(p) or not tp:
        return out
    table = SND.Table(open(tp, 'rb').read())
    files = {}
    d = sound_dir(rec, out_data)
    for f in os.listdir(d) if os.path.isdir(d) else []:
        if f.endswith('.nus3bank'):
            try:
                files[AU.Bank(open(os.path.join(d, f), 'rb').read()).binf()[1]] = f
            except Exception:
                pass
    f = acmd.ACMDFile.load(p)
    want = {acmd.crc(n) for n in WIN_MOTIONS}
    for h, cmds in f.scripts.items():
        if h not in want:
            continue
        for c in cmds:
            for i, v in enumerate(c.params):
                if c.kind(i) == 1 or not isinstance(v, int):
                    continue
                row, lab = (v >> 16) & 0xFFFF, v & 0xFFFF
                if row < len(table.rows) and table.rows[row][0] in files and lab < table.rows[row][1]:
                    out.add((files[table.rows[row][0]], table.tones(row)[lab]))
    return out


def lines(rec, out_data):
    """[{'bank', 'file', 'tone', 'name', 'category', 'seconds'}] of every tone in the clone's banks"""
    d = sound_dir(rec, out_data)
    out = []
    if not os.path.isdir(d):
        return out
    wins = win_tones(rec, out_data)
    for f in sorted(os.listdir(d)):
        if not f.endswith('.nus3bank'):
            continue
        try:
            b = AU.Bank(open(os.path.join(d, f), 'rb').read())
        except Exception:
            continue
        bk = bank_kind(f, rec['cap'])
        for i, t in enumerate(b.tones):
            if not t or not t['size']:
                continue
            cat = 'victory' if (f, i) in wins else category(t['name'], bk)
            out.append({'bank': bk, 'file': f, 'tone': i, 'name': t['name'], 'category': cat,
                        'seconds': t['samples'] / float(t['rate'] or 48000)})
    return out


def tone_data(rec, out_data, fname, tone):
    return AU.Bank(open(os.path.join(sound_dir(rec, out_data), fname), 'rb').read()).data_of(tone)


def replace(rec, out_data, fname, tone, wav):
    """tone `tone` of the clone's bank `fname` plays the WAV (encoded to DSP-ADPCM); returns the IDSP"""
    p = os.path.join(sound_dir(rec, out_data), fname)
    b = AU.Bank(open(p, 'rb').read())
    blob = AU.wav_to_idsp(wav)
    b.replace(tone, blob)
    open(p, 'wb').write(b.data())
    return blob


def _key(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def import_folder(rec, out_data, folder):
    """every WAV in folder named like a tone (the full tone name, or its part after the bank's name, case and
    punctuation ignored) replaces it; returns [(wav, bank, tone name)]"""
    done = []
    ls = lines(rec, out_data)
    for w in sorted(os.listdir(folder)):
        if not w.lower().endswith('.wav'):
            continue
        k = _key(w[:-4])
        hit = None
        for x in ls:
            nm = _key(x['name'])
            short = _key(x['name'].split('_', 3)[-1]) if x['name'].count('_') >= 3 else nm
            if k in (nm, short):
                hit = x
                break
        if hit:
            replace(rec, out_data, hit['file'], hit['tone'], os.path.join(folder, w))
            done.append((w, hit['file'], hit['name']))
    return done
