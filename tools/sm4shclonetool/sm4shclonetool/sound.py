"""A clone's own sound banks: its copies of the base's banks (fighter/<name>/sound/*.nus3bank, already renamed to the
clone's Cap name by the folder copy) get a BINF name and id of their own and soundlabeltable rows of their own (the
base's label lists), and the clone's ACMD sound ids move from the base's rows to its own.

How the game finds them: a fighter's banks load by file name (fighter/<folder>/sound/snd_se_<Cap>.nus3bank, the
_vc_ voice banks, by the Capitalised name the executable's table gives the kind: the clone's own), each bank's id
read from its BINF section; a sound id is (soundlabeltable row << 16) | label, and the row names the bank id it
plays from. With the base's id kept, the clone's bank and the base's answer for the same rows; with its own id and
row the clone's sounds are its own. No executable change: the clone's Cap name already picks its files.

The tones / packs are copied byte for byte (nothing re-encoded). MSC sound ids are not remapped (the tool has no MSC
reader): a clone whose MSC plays sounds by id keeps the base's sounds for those.
"""
import os
import struct

from . import _paths  # noqa: F401

BANK_IDS = (2000, 3000)          # the fighter banks' id range in soundlabeltable


def sections(d):
    assert d[:4] == b'NUS3' and d[8:16] == b'BANKTOC '
    count = struct.unpack('<I', d[20:24])[0]
    q = 24 + count * 8
    out = []
    for i in range(count):
        name, size = struct.unpack('<4sI', d[24 + i * 8:32 + i * 8])
        out.append([name, bytes(d[q + 8:q + 8 + size])])
        q += 8 + size
    return out


def build(secs):
    toc = b''.join(struct.pack('<4sI', nm, len(b)) for nm, b in secs)
    out = b'BANKTOC ' + struct.pack('<II', 4 + len(toc), len(secs)) + toc
    out += b''.join(nm + struct.pack('<I', len(b)) + b for nm, b in secs)
    return b'NUS3' + struct.pack('<I', len(out)) + out


def binf(d):
    b = dict((k, v) for k, v in sections(d))[b'BINF']
    n = b[8]
    return b[9:9 + n - 1].decode('latin1'), struct.unpack('<I', b[(9 + n + 3) & ~3:][:4])[0]


def set_binf(d, name, bank_id):
    secs = sections(d)
    assert build(secs) == d, 'nus3bank: round trip differs'
    for s in secs:
        if s[0] == b'BINF':
            b = s[1]
            n = b[8]
            rest = b[(9 + n + 3) & ~3:]
            nm = name.encode('latin1') + b'\0'
            head = b[:8] + bytes([len(nm)]) + nm
            s[1] = head.ljust((len(head) + 3) & ~3, b'\0') + struct.pack('<I', bank_id) + rest[4:]
    return build(secs)


class Table:
    """sound/config/soundlabeltable.bin: rows {bank id, label count, label offset, 0} and the label lists"""

    def __init__(self, d):
        assert d[:4] == b'STB\0'
        self.head = d[:8]
        n, size = struct.unpack('<II', d[8:16])
        assert size == 16 * n
        self.rows = [list(struct.unpack('<4I', d[16 + 16 * i:32 + 16 * i])) for i in range(n)]
        self.labels = bytearray(d[16 + size:])
        assert self.data() == d, 'soundlabeltable: round trip differs'

    def data(self):
        n = len(self.rows)
        return self.head + struct.pack('<II', n, 16 * n) + b''.join(struct.pack('<4I', *r) for r in self.rows) + \
            bytes(self.labels)

    def row_of(self, bank_id):
        rows = [i for i, r in enumerate(self.rows) if r[0] == bank_id]
        return rows[0] if len(rows) == 1 else None

    def tones(self, row):
        _b, n, off, _z = self.rows[row]
        return list(struct.unpack('<%di' % n, self.labels[off:off + 4 * n]))

    def free_row(self):
        free = [i for i, r in enumerate(self.rows) if r[0] == 0xFFFFFFFF]
        if free:
            return free[-1]
        self.rows.append([0xFFFFFFFF, 0, 0, 0])
        return len(self.rows) - 1

    def set_row(self, row, tones):
        """row's label list replaced (the label area rebuilt: every other row keeps its list, rows that shared a list
        still share it)"""
        lists = {}
        for i, r in enumerate(self.rows):
            if i != row and r[1]:
                lists.setdefault((r[2], r[1]), bytes(self.labels[r[2]:r[2] + 4 * r[1]]))
        area, where = bytearray(), {}
        for key in sorted(lists):
            where[key] = len(area)
            area += lists[key]
        for i, r in enumerate(self.rows):
            if i != row and r[1]:
                r[2] = where[(r[2], r[1])]
            elif i != row:
                r[2] = min(r[2], len(area))
        off = len(area)
        area += struct.pack('<%di' % len(tones), *tones)
        self.rows[row][1], self.rows[row][2] = len(tones), off
        self.labels = area

    def add_row(self, bank_id, tones):
        row = self.free_row()
        off = len(self.labels)
        self.labels.extend(struct.pack('<%di' % len(tones), *tones))
        self.rows[row] = [bank_id, len(tones), off, 0]
        return row


def remap_acmd(path, rows, sound_bin):
    """sound ids (row << 16 | label) on the old rows -> the new rows; sound.bin: every int parameter, other files:
    SE / Sound commands only. Returns the count."""
    import acmd
    f = acmd.ACMDFile.load(path)
    n = 0
    for cmds in f.scripts.values():
        for c in cmds:
            words = c.name.lower().split('_')
            if not sound_bin and 'se' not in words and not any('sound' in w for w in words):
                continue
            for i, v in enumerate(c.params):
                if c.kind(i) != 1 and isinstance(v, int) and v >> 16 in rows and (v & 0xFFFF) < rows[v >> 16][1]:
                    c.params[i] = rows[v >> 16][0] << 16 | (v & 0xFFFF)
                    n += 1
    if n:
        f.save(path)
    return n


def own_banks(rec, out_data, data_dir, log):
    """give the clone's banks their own ids / rows; returns {old row: new row}"""
    from . import roster as R
    d = os.path.join(out_data, 'fighter', rec['name'], 'sound')
    if not os.path.isdir(d):
        log('own sound bank: no fighter/%s/sound/ (nothing to do)' % rec['name'])
        return {}
    tp = R.first([out_data, data_dir], 'sound/config/soundlabeltable.bin')
    if not tp:
        log('own sound bank: no sound/config/soundlabeltable.bin in the data folder: the banks keep the base\'s ids')
        return {}
    table = Table(open(tp, 'rb').read())
    ids = {r[0] for r in table.rows}
    rows = {}
    alias = {}
    nxt = max([i for i in ids if BANK_IDS[0] <= i < BANK_IDS[1]] + [BANK_IDS[0]]) + 1
    cap = rec['cap']
    kinds = {'snd_se_%s.nus3bank' % cap: 'se', 'snd_vc_%s.nus3bank' % cap: 'vc',
             'snd_vc_%s_ouen.nus3bank' % cap: 'cheer', 'snd_se_%s_common.nus3bank' % cap: 'se_common'}
    for f in sorted(os.listdir(d)):
        if not f.endswith('.nus3bank'):
            continue
        if f.startswith('snd_se_vc_Kirby_copy_'):
            # Kirby's copy voices: Kirby plays them from his own handles of this bank (no alias there), by the base's
            # row: the clone's copy keeps the base's id (its own file, so its own tones)
            log('own sound bank: %s keeps its base\'s id (Kirby plays it by the base\'s row; with the base in the '
                'same match only the first one\'s copy voices load)' % f)
            continue
        p = os.path.join(d, f)
        data = open(p, 'rb').read()
        try:
            old_name, old_id = binf(data)
        except Exception as e:
            log('own sound bank: %s: no BINF (%s), left as is' % (f, e))
            continue
        while nxt in ids:
            nxt += 1
        new_id = nxt
        ids.add(new_id)
        new_name = f[:-len('.nus3bank')]
        open(p, 'wb').write(set_binf(data, new_name, new_id))
        if f in kinds:
            alias[kinds[f]] = old_id
        row = table.row_of(old_id)
        if row is None:
            log('own sound bank: %s: BINF %s id %d -> %s id %d (no soundlabeltable row of its own before)'
                % (f, old_name, old_id, new_name, new_id))
            continue
        tones = table.tones(row)
        new_row = table.add_row(new_id, tones)
        rows[row] = (new_row, len(tones))
        log('own sound bank: %s: BINF %s id %d (row %d) -> %s id %d, row %d (%d labels)'
            % (f, old_name, old_id, row, new_name, new_id, new_row, len(tones)))
    dst = os.path.join(out_data, 'sound', 'config', 'soundlabeltable.bin')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(table.data())
    # scripts: the body's and its own articles'
    total = 0
    sd = os.path.join(out_data, 'fighter', rec['name'], 'script', 'animcmd')
    for root, _ds, fs in os.walk(sd):
        for f in fs:
            if f.endswith('.bin'):
                total += remap_acmd(os.path.join(root, f), rows, f == 'sound.bin')
    rec['sound_alias'] = [alias.get(k, 0) for k in ('se', 'vc', 'cheer', 'se_common')]
    log('own sound bank: the base\'s bank ids %s answer from the clone\'s own banks (the executable\'s alias: sounds '
        'the game plays by the base\'s rows from code, MSC, the voice sequences and commonsoundtable.csb)'
        % ', '.join('%s %d' % kv for kv in zip(('se', 'vc', 'cheer', 'se_common'), rec['sound_alias']) if kv[1]))
    log('own sound bank: %d ACMD sound ids moved to the clone\'s rows %s' % (
        total, ', '.join('%d -> %d' % (a, b[0]) for a, b in sorted(rows.items()))))
    return rows
