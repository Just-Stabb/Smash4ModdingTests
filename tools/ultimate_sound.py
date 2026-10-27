#!/usr/bin/env python3
"""An Ultimate fighter's own sounds and voice in its Smash 4 slot's banks (docs/ultimate-fighter-port.md
"Sounds").

  python3 tools/ultimate_sound.py ULT_SOUND FIGHTER_DIR SOUNDLABELTABLE OUT --name Brave --ult-name brave \\
      --dump DUMP/lua2cpp_brave [--se-id N] [--se-row N] [--vc-id N] [--vc-row N]

ULT_SOUND: Ultimate's sound/ (bank/fighter/se_<ult>.nus3audio / .nus3bank, bank/fighter_voice/
vc_<ult>[_cNN].*, sequence/fighter/<ult>.sqb). FIGHTER_DIR: the slot's fighter/<name>/ (its
sound/snd_se_<Name>.nus3bank, snd_vc_<Name>.nus3bank, soundseq_<Name>.sqb: the base's, renamed).
SOUNDLABELTABLE: the current sound/config/soundlabeltable.bin. DUMP: the lua2cpp dump (its scripts
name the sequences: Hash40::new("seq_...")).

Writes OUT/fighter/<name>/sound/ (snd_se_<Name>, snd_vc_<Name>, soundseq_<Name>.sqb),
OUT/sound/config/soundlabeltable.bin, and OUT/sound_ids.json: {Ultimate name: Smash 4 id} for every
se_ / vc_ tone and seq_ sequence, "_rows": [[base row, base labels, new row], ...] (the base's
scripts' ids move to the new rows, same labels: tools/brave_build.py --sound).

- Audio: Ultimate's tones are Namco IDSP (DSP-ADPCM, big-endian header), as Smash 4's: copied as they
  are (loops keep their IDSP loop points; the TONE loop flag follows the DSP header's). Volume (dB)
  from Ultimate's own TONE entry (the same field, +12 of the entry's data block).
- Banks: each keeps the base's tones and BINF id, its soundlabeltable row grown by the Ultimate tones
  (the base's labels stay first, so its scripts' and the game's own ids still play: the KO scream, the
  base's sequences). The game matches a sound's bank id against the banks the playing fighter loaded
  (cross_f.rpx 0x03120978, a fighter's 7 bank slots), so the base and this fighter in one match don't
  mix (two Robins, male and female, already do it). The new TONE entries copy a base one-shot's (its
  group / flags: the se bank's Special_L01, the voice bank's first), named snd_se_<Name>_<rest>.
  --new-ids instead gives the banks their own ids and empty rows (sound_ids.json "_rows": the base's
  scripts' ids must then move rows, tools/brave_build.py does it).
- Voice: the base's labelled tones the game plays itself (damage, jump, teeter, ledge, appeals, KO,
  results) take the Ultimate voice of the same use (VOICE_ALIASES, else the same name).
- Costumes: Ultimate's se_ / vc_<ult>_cNN (Hero: Erdrick, Solo and Eight's voices and swords) as
  snd_se_ / snd_vc_<Name>_cNN, same tone order and bank id; the game loads _cNN by the costume number
  (a kind past 0x39 takes it as is, so c05 - c07 are written too) and falls back to the main file
  (none written when Ultimate's is the main one's, e.g. c04). The crowd's cheer: the base's ouen bank's
  chant given vc_<ult>_cheer.
- Ultimate's random containers (a TONE with no data, +4 = 0x7F, its name at +8, e.g.
  se_brave_step_left_ll for _ll01 - _ll03):
  Smash 4's banks have none, the name maps to the first variant.
- Sequences (voice picks): Ultimate's .sqb ('SQB\\0' version 1: u16 count, u32 table size, then the offsets
  (from the table's end); a sequence: hash40 name, u16 2, u16 n, u32 0, then n 20-byte choices: hash40
  sound, u16 1, u16 weight %, 8 zero bytes; the hash40 of "none" (crc 0xEB86B427, length 8) is a
  silent pick; the _jp spell shouts pick sounds no bank holds: their _en twin's picks) appended to the
  base's soundseq (version 4, its set id: ACMD plays
  0x80000000 | set << 16 | index); the choice / sequence constants (0x4A, 0x15) are the base's.
"""
import argparse
import glob
import json
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fighter_own_bank as fb  # noqa: E402
import minecraft_music as mm  # noqa: E402
import minecraft_sound as ms  # noqa: E402

NONE40 = (8, 0xEB86B427)                # hash40("none")? a silent pick: length 8, crc as Ultimate stores it


# the base's voice labels the game plays itself (damage, KO, teeter, ledge, results...: by label or through
# the base's own sequences) -> the Ultimate voice of the same use; the rest by the same name
# (snd_vc_<Base>_appeal01 -> vc_<ult>_appeal01)
VOICE_ALIASES = {'jump': 'jump01', 'damage03': 'damage02', 'damage_hoshikie': 'damage_twinkle',
                 'win01': 'appeal02_win01', 'win02': 'special_s04_01_win02'}


def hash40(name):
    return len(name), zlib.crc32(name.encode())


# ---------------------------------------------------------------- Ultimate

def ult_tones(path):
    """[(name, IDSP bytes or None, volume dB)] in TONE order, and {container: first variant}"""
    audio = ms.ultimate(path + '.nus3audio')
    _s, tones = ms.tones_of(open(path + '.nus3bank', 'rb').read())
    out = []
    for e in tones:
        e = bytes(e)
        if len(e) < 0x10:
            continue
        if e[4:8] == struct.pack('<I', 0x7F):       # a random container: its name 4 bytes earlier, no data
            out.append((e[9:9 + e[8] - 1].decode('latin1'), None, 0.0))
            continue
        name = e[0xD:0xD + e[0xC] - 1].decode('latin1')
        q = ((0x0D + e[0x0C] + 3) & ~3) + 4
        vol = struct.unpack('<f', e[q + 12:q + 16])[0] if e[q:q + 4] == struct.pack('<I', 8) else 0.0
        out.append((name, audio.get(name), vol))
    have = [n for n, b, _v in out if b]
    first = {}
    for n, b, _v in out:
        if not b:
            kids = sorted(k for k in have if k.startswith(n) and k[len(n):].isdigit())
            if kids:
                first[n] = kids[0]
    return out, first


def ult_sqb(path):
    """[(name hash40, [(sound hash40, weight)])]"""
    d = open(path, 'rb').read()
    assert d[:4] == b'SQB\0' and struct.unpack('<H', d[4:6])[0] == 1, 'not an Ultimate .sqb'
    count, tsz = struct.unpack('<HI', d[6:12])
    offs = struct.unpack('<%dI' % count, d[0x0C:0x0C + 4 * count])
    seqs = []
    for o in offs:
        p = 0x0C + tsz + o
        crc, ln, typ, n = struct.unpack('<IIHH', d[p:p + 12])
        ch = []
        for i in range(n):
            c = p + 16 + 20 * i
            ccrc, cln, _one, w = struct.unpack('<IIHH', d[c:c + 12])
            ch.append(((cln, ccrc), w))
        seqs.append(((ln, crc), typ, ch))
    return seqs


def is_loop(idsp):
    return struct.unpack('>H', idsp[0x40 + 12:0x40 + 14])[0] != 0


# ---------------------------------------------------------------- Smash 4 bank

def bank(data, prefix, bank_name, bank_id, sounds, template, replace=None):
    """the base bank plus sounds [(name, IDSP, volume)]; (bytes, first new tone index). replace: {base
    tone index: (IDSP, volume)}, those tones' data swapped (the base's labels the game itself plays)"""
    secs = mm.sections(data)
    _s, tones = ms.tones_of(data)
    t_head, _n, t_rest = template
    pack = bytearray(dict(secs)[b'PACK'])
    first = len(tones)
    entries = [bytes(e) for e in tones]
    for i, (blob, vol) in (replace or {}).items():
        head, name, rest = ms.parse_entry(entries[i])
        pack.extend(b'\0' * (-len(pack) % 0x20))
        off = len(pack)
        pack.extend(blob)
        rate, ch, n = ms.idsp_info(blob)
        entries[i] = bytes(ms.entry(head, name, ms.set_data(rest, off, len(blob), rate, ch, n, is_loop(blob), vol)))
    for name, blob, vol in sounds:
        pack.extend(b'\0' * (-len(pack) % 0x20))
        off = len(pack)
        pack.extend(blob)
        rate, ch, n = ms.idsp_info(blob)
        rest = ms.set_data(t_rest, off, len(blob), rate, ch, n, is_loop(blob), vol)
        entries.append(bytes(ms.entry(t_head, prefix + name, rest)))
    pack.extend(b'\0' * (-len(pack) % 0x20))
    table, body = b'', b''
    base = 4 + 8 * len(entries)
    for e in entries:
        table += struct.pack('<II', base + len(body), len(e))
        body += e
    for s in secs:
        if s[0] == b'TONE':
            s[1] = struct.pack('<I', len(entries)) + table + body
        elif s[0] == b'PACK':
            s[1] = bytes(pack)
        elif s[0] == b'BINF':
            nm = bank_name.encode() + b'\0'
            b = s[1][:8] + bytes([len(nm)]) + nm
            s[1] = b.ljust((len(b) + 3) & ~3, b'\0') + struct.pack('<I', bank_id)
    toc = b''.join(struct.pack('<4sI', nm, len(b)) for nm, b in secs)
    out = b'BANKTOC ' + struct.pack('<II', 4 + len(toc), len(secs)) + toc
    out += b''.join(nm + struct.pack('<I', len(b)) + b for nm, b in secs)
    return b'NUS3' + struct.pack('<I', len(out)) + out, first


def template_tone(data, suffix=None):
    _s, tones = ms.tones_of(data)
    for e in tones:
        if len(e) < 0x10:
            continue
        head, name, rest = ms.parse_entry(e)
        if suffix is None or name.endswith(suffix):
            if struct.unpack('<I', rest[-0x0C:-0x08])[0] == 0:        # a one-shot (loop flag 0)
                return head, name, rest
    raise SystemExit('no one-shot tone%s to copy' % (' ' + suffix if suffix else ''))


# ---------------------------------------------------------------- Smash 4 sqb

def s4_sqb(d):
    assert d[:4] == b'SQB\0' and struct.unpack('<H', d[4:6])[0] == 4
    sid, count, tsz = struct.unpack('<HII', d[6:16])
    offs = struct.unpack('<%di' % count, d[16:16 + 4 * count])
    base = 16 + tsz
    seqs = []
    for o in offs:
        if o < 0:
            seqs.append(None)
            continue
        p = base + o
        n, = struct.unpack('<H', d[p + 2:p + 4])
        seqs.append(d[p:p + 8 + 16 * n])
    return sid, seqs


def s4_sqb_data(sid, seqs):
    offs, body = [], b''
    for s in seqs:
        if s is None:
            offs.append(-1)
        else:
            offs.append(len(body))
            body += s
    return b'SQB\0' + struct.pack('<HHII', 4, sid, len(seqs), 4 * len(seqs)) + \
        struct.pack('<%di' % len(seqs), *offs) + body


def s4_sequence(choices, seq_const, choice_const):
    """choices: [(sound id or -1, weight)]"""
    s = struct.pack('<HHHH', 2, len(choices), 0, seq_const)
    for sid, w in choices:
        s += struct.pack('<iHHIHH', sid, 1, w, 0, 0, choice_const)
    return s


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ult')
    ap.add_argument('fighter')
    ap.add_argument('table')
    ap.add_argument('out')
    ap.add_argument('--name', required=True)
    ap.add_argument('--ult-name', required=True)
    ap.add_argument('--dump', required=True)
    ap.add_argument('--new-ids', action='store_true', help='own BINF ids and soundlabeltable rows (default: the '
                    "base's, its rows grown: banks are matched per fighter, so the base and this fighter don't mix)")
    for k in ('se-id', 'se-row', 'vc-id', 'vc-row'):
        ap.add_argument('--' + k, type=lambda s: int(s, 0))
    a = ap.parse_args()
    folder = os.path.basename(os.path.normpath(a.fighter))
    snd = os.path.join(a.fighter, 'sound')
    out_fighter = os.path.join(a.out, 'fighter', folder)
    os.makedirs(os.path.join(out_fighter, 'sound'), exist_ok=True)
    table = fb.Table(open(a.table, 'rb').read())
    taken = {r[0] for r in table.rows}
    empty = [i for i, r in enumerate(table.rows) if r[0] == 0xFFFFFFFF]
    ids, report, moved = {}, [], []
    seq_names = set()
    for path in glob.glob(os.path.join(a.dump, '**', '*.txt'), recursive=True):
        seq_names.update(re.findall(r'Hash40::new\("(seq_[a-z0-9_]+)"\)', open(path, errors='replace').read()))
    seq_names = {hash40(n): n for n in seq_names}

    def build(kind, ult_path, lo, hi, want_id, want_row, tmpl_suffix):
        base_path = os.path.join(snd, 'snd_%s_%s.nus3bank' % (kind, a.name))
        data = open(base_path, 'rb').read()
        old_name, old_id = fb.binf(data)
        old_row = table.row_of(old_id)
        old_tones = table.tones(old_row)
        if a.new_ids:
            bank_id = want_id if want_id is not None else max(i for i in taken if lo <= i < hi) + 1
            assert bank_id not in taken, '%s bank id %d is in the table' % (kind, bank_id)
            taken.add(bank_id)
            row = want_row if want_row is not None else empty.pop()
            if row in empty:
                empty.remove(row)
        else:
            bank_id, row = old_id, old_row
        tones, first_of = ult_tones(ult_path)
        prefix = '%s_%s_' % (kind, a.ult_name)
        names = [n for n, b, _v in tones if b]
        vols = {n: v for n, b, v in tones if b}

        def costume_bank(audio, bank_name):
            """the bank with this costume's audio (by name; the main bank's where it has none)"""
            sounds = [(n[len(prefix):] if n.startswith(prefix) else n, audio.get(n) or main_audio[n], vols[n])
                      for n in names]
            replace, swapped = {}, []
            if kind == 'vc':
                by_rest = {r.lower(): (b, v) for r, b, v in sounds}
                _s, base_tones = ms.tones_of(data)
                bprefix = 'snd_vc_%s_' % old_name[len('snd_vc_'):]
                for i, e in enumerate(base_tones):
                    if len(e) < 0x10:
                        continue
                    rest = ms.parse_entry(e)[1][len(bprefix):].lower()
                    hit = by_rest.get(VOICE_ALIASES.get(rest, rest))
                    if hit:
                        replace[i] = hit
                        swapped.append(rest)
            blob, first = bank(data, 'snd_%s_%s_' % (kind, a.name), bank_name, bank_id, sounds,
                               template_tone(data, tmpl_suffix), replace)
            return blob, first, swapped

        main_audio = ms.ultimate(ult_path + '.nus3audio')
        blob, first, swapped = costume_bank(main_audio, 'snd_%s_%s' % (kind, a.name))
        labels = old_tones + [first + k for k in range(len(names))]
        if a.new_ids:
            table.add_row(row, bank_id, labels)
        else:
            table.set_row(row, labels)
        open(os.path.join(out_fighter, 'sound', os.path.basename(base_path)), 'wb').write(blob)
        # the costumes' own banks (Ultimate's _cNN: Hero's other heroes' voices and sword sounds): same tone
        # order and bank id, loaded for costume NN by file name (a kind past 0x39 takes its costume number
        # as is: _c05 for costume 5) and matched by the id, as the main bank (docs/ultimate-fighter-port.md)
        written = []
        raw_main = open(ult_path + '.nus3audio', 'rb').read()
        for nn in range(1, 8):
            cpath = '%s_c%02d' % (ult_path, nn)
            if not os.path.exists(cpath + '.nus3audio') or open(cpath + '.nus3audio', 'rb').read() == raw_main:
                continue                # none, or the main bank's own sounds: the main file serves (no _cNN)
            cname = 'snd_%s_%s_c%02d' % (kind, a.name, nn)
            cblob, cfirst, _sw = costume_bank(ms.ultimate(cpath + '.nus3audio'), cname)
            assert cfirst == first
            open(os.path.join(out_fighter, 'sound', cname + '.nus3bank'), 'wb').write(cblob)
            written.append('c%02d' % nn)
        k = len(old_tones)
        for n in names:                 # scripts name them in lower case (Ultimate's hash40 of the name)
            ids[n.lower()] = row << 16 | k
            k += 1
        for c, v in first_of.items():
            ids[c.lower()] = ids[v.lower()]
        report.append('%s: BINF %s id %d (row %d) -> id %d, row %d: %d base labels + %d Ultimate tones '
                      '(%d loops; containers -> first variant: %s); base tones given the Ultimate voice: %s; '
                      'costume banks: %s; %.1f MB' % (
                          os.path.basename(base_path), old_name, old_id, old_row, bank_id, row, len(old_tones),
                          len(names), sum(is_loop(main_audio[n]) for n in names), ', '.join(sorted(first_of)) or '-',
                          ', '.join(swapped) or '-', ', '.join(written) or '-', len(blob) / 1e6))
        if row != old_row:
            moved.append((old_row, len(old_tones), row))

    build('se', os.path.join(a.ult, 'bank/fighter/se_' + a.ult_name), 2000, 3000, a.se_id, a.se_row, 'Special_L01')
    build('vc', os.path.join(a.ult, 'bank/fighter_voice/vc_' + a.ult_name), 6000, 7000, a.vc_id, a.vc_row, None)

    # the crowd's cheer: the base's ouen bank (its first labelled tone, a stereo chant) given Ultimate's
    ouen = os.path.join(snd, 'snd_vc_%s_ouen.nus3bank' % a.name)
    cheer = os.path.join(a.ult, 'bank/fighter_voice/vc_%s_cheer' % a.ult_name)
    if os.path.exists(ouen) and os.path.exists(cheer + '.nus3audio'):
        data = open(ouen, 'rb').read()
        _n, oid = fb.binf(data)
        first_label = next(t for t in table.tones(table.row_of(oid)) if t >= 0)
        (cname, cblob, cvol), = [t for t in ult_tones(cheer)[0] if t[1]]
        blob, _f = bank(data, '', 'snd_vc_%s_ouen' % a.name, oid, [], template_tone(data), {first_label: (cblob, cvol)})
        open(os.path.join(out_fighter, 'sound', os.path.basename(ouen)), 'wb').write(blob)
        report.append('%s: tone %d = %s (%.1f s, %+.1f dB)' % (os.path.basename(ouen), first_label, cname,
                                                               ms.idsp_info(cblob)[2] / 48000, cvol))

    # sequences: the base's, then Ultimate's
    sq_path = os.path.join(snd, 'soundseq_%s.sqb' % a.name)
    sid, seqs = s4_sqb(open(sq_path, 'rb').read())
    first_seq = next(s for s in seqs if s)
    seq_const = struct.unpack('<H', first_seq[6:8])[0]
    choice_const = struct.unpack('<H', first_seq[8 + 14:8 + 16])[0]
    by_hash = {hash40(n): n for n in ids}
    remap = {r0: (n0, r1) for r0, n0, r1 in moved}
    out_seqs = []
    for s in seqs:                                  # the base's ids onto their new rows
        if s is None:
            out_seqs.append(None)
            continue
        s = bytearray(s)
        n, = struct.unpack('<H', s[2:4])
        for i in range(n):
            p = 8 + 16 * i
            v, = struct.unpack('<i', s[p:p + 4])
            if v >= 0 and v >> 16 in remap and (v & 0xFFFF) < remap[v >> 16][0]:
                s[p:p + 4] = struct.pack('<i', remap[v >> 16][1] << 16 | (v & 0xFFFF))
        out_seqs.append(bytes(s))
    unknown, unnamed = [], 0
    ult_seqs = ult_sqb(os.path.join(a.ult, 'sequence/fighter/%s.sqb' % a.ult_name))
    by_name = {seq_names.get(h): ch for h, _t, ch in ult_seqs}
    for h, _typ, ch in ult_seqs:
        name = seq_names.get(h)
        if name and name.endswith('_jp') and not any(sh in by_hash for sh, _w in ch):
            # Japanese spell shouts: hash40s not in the banks (a sound nothing names); the English twin's
            ch = by_name.get(name[:-3] + '_en', ch)
        picks = []
        for sh, w in ch:
            if sh in by_hash:
                picks.append((ids[by_hash[sh]], w))
            else:
                if sh != NONE40:
                    unknown.append('%s: %08X/%d' % (name, sh[1], sh[0]))
                picks.append((-1, w))
        idx = len(out_seqs)
        out_seqs.append(s4_sequence(picks, seq_const, choice_const))
        unnamed += name is None
        ids[name or '_seq_%08X_%d' % (h[1], h[0])] = 0x80000000 | sid << 16 | idx
    open(os.path.join(out_fighter, 'sound', os.path.basename(sq_path)), 'wb').write(s4_sqb_data(sid, out_seqs))
    report.append('%s: set 0x%X, %d base + %d Ultimate sequences (unnamed: %d; picks not in the banks: %s)' % (
        os.path.basename(sq_path), sid, len(seqs), len(out_seqs) - len(seqs),
        unnamed,
        ', '.join(unknown) or '-'))

    os.makedirs(os.path.join(a.out, 'sound', 'config'), exist_ok=True)
    open(os.path.join(a.out, 'sound', 'config', 'soundlabeltable.bin'), 'wb').write(table.data())
    ids['_rows'] = [list(m) for m in moved]
    json.dump(ids, open(os.path.join(a.out, 'sound_ids.json'), 'w'), indent=1, sort_keys=True)
    print('\n'.join(report))


if __name__ == '__main__':
    main()
