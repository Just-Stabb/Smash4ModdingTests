"""The data side of a fighter clone, built on vendor/add_fighter.py (rows, names, portraits, the renamed folder),
vendor/add_fighter_customs.py (custom-move labels / icons) and the sound config files' formats (fanfare, KO
voices). Every file is read from the newest copy (the package being built, then the creator's data) and written
into the package; add_fighter's checks run on each (with the new rows taken out, every file rebuilds byte for
byte)."""
import argparse
import json
import os
import re
import shutil
import struct

from . import _paths  # noqa: F401
from . import roster as R
from . import textures as T
import add_fighter as A  # noqa: E402

PORTRAIT_SETS = A.PORTRAIT_SETS
NAME_RX = re.compile(r'^[a-z][a-z0-9]{1,15}$')
UINAME_RX = re.compile(r'^[A-Z][A-Za-z0-9]{1,15}$')


MAX_ID = 0xC7                 # ui_character_db ids up to 0xC7 are looked up by position (ids >= 200: searched)
MAX_CLONES = MAX_ID - 59 + 1  # 141 (kinds 0x41-0xCD: the kind tables hold up to 0x13F)


class CloneError(Exception):
    pass


def ns(**k):
    return argparse.Namespace(**k)


def _ui_names(reg):
    """add_fighter's id -> UI name table with the clones' ids"""
    names = list(R.UI_NAMES)
    for f in sorted(reg['fighters'], key=lambda f: f['ui_id']):
        while len(names) < f['ui_id']:
            names.append('Id%d' % len(names))
        if len(names) == f['ui_id']:
            names.append(f['ui_name'])
        else:
            names[f['ui_id']] = f['ui_name']
    return names


def source_info(src_name, reg):
    """(source kind, lowercase name, Capitalised name, UI name, native vanilla base) of a vanilla fighter or a clone"""
    for f in reg['fighters']:
        if src_name in (f['name'], f['ui_name']):
            return f['kind'], f['name'], f['cap'], f['ui_name'], f['base']
    if src_name not in R.KINDS:
        raise CloneError('unknown base fighter %r' % src_name)
    k = R.KINDS.index(src_name)
    if k in R.NO_BASE or k >= 0x3A:
        raise CloneError('%s can\'t be a base (Miis, transformations and Mii enemies are not offered)' % src_name)
    ui = next((R.UI_NAMES[i] for i in range(len(R.UI_NAMES)) if i and A_KIND_OF_ID.get(i) == k), None)
    return k, src_name, A.CAPS[k], ui, src_name


# vanilla character id -> kind (ui_character_db's +0x10 of the game's own entries)
A_KIND_OF_ID = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7, 9: 8, 10: 9, 11: 10, 12: 11, 13: 12, 14: 13, 15: 14,
                16: 15, 17: 16, 18: 17, 19: 18, 20: 19, 21: 20, 22: 21, 23: 22, 24: 23, 25: 24, 26: 25, 27: 26,
                28: 27, 29: 28, 30: 29, 31: 30, 32: 31, 33: 32, 34: 33, 35: 34, 36: 36, 37: 39, 38: 40, 39: 41,
                40: 42, 41: 43, 42: 44, 43: 45, 44: 46, 45: 47, 46: 35, 47: 37, 48: 38, 49: 48, 50: 49, 51: 50,
                52: 51, 53: 52, 54: 53, 55: 54, 56: 55, 57: 56, 58: 57}


def next_slots(param_dirs, reg):
    """(next kind, next character id): after the registry's clones, checked against the databases"""
    kind = 0x41 + len(reg['fighters'])
    cid = 59 + len(reg['fighters'])
    return kind, cid


def validate(spec, param_dirs, ui_dirs, reg):
    """[errors] for a planned fighter clone (spec: name, cap, ui_name, title, source, kind, ui_id, ...)"""
    err = []
    if not NAME_RX.match(spec['name']):
        err.append('internal name: lowercase letters / digits, 2-16, starting with a letter (got %r)' % spec['name'])
    if not re.match(r'^[A-Z][A-Za-z0-9]{1,15}$', spec['cap']):
        err.append('Cap name: a capital letter then letters / digits (got %r)' % spec['cap'])
    if not UINAME_RX.match(spec['ui_name']):
        err.append('UI name: a capital letter then letters / digits, no spaces (got %r)' % spec['ui_name'])
    taken = set(R.KINDS) | {f['name'] for f in reg['fighters']}
    if spec['name'] in taken:
        err.append('internal name %r is taken' % spec['name'])
    if spec['cap'].lower() in {c.lower() for c in A.CAPS} | {f['cap'].lower() for f in reg['fighters']}:
        err.append('Cap name %r is taken' % spec['cap'])
    if spec['ui_name'].lower() in {u.lower() for u in R.UI_NAMES} | {f['ui_name'].lower() for f in reg['fighters']}:
        err.append('UI name %r is taken' % spec['ui_name'])
    kind, cid = next_slots(param_dirs, reg)
    if spec['kind'] != kind:
        err.append('kind 0x%X: new kinds are consecutive from 0x41 (the next is 0x%X)' % (spec['kind'], kind))
    if spec['ui_id'] != cid:
        err.append('character id %d: new ids are consecutive from 59 (the next is %d)' % (spec['ui_id'], cid))
    if cid > MAX_ID:
        err.append('no character id left: ids up to 0x%X are found by their place in the database (%d clones)'
                   % (MAX_ID, MAX_CLONES))
    g, _ = R.load_db(param_dirs, 'ui/ui_character_db.bin')
    if g is not None:
        ids = [e[0][1] for e in g[2]]
        if spec['ui_id'] in ids:
            err.append('character id %d is already in ui_character_db.bin (a clone not in the registry?)' % spec['ui_id'])
    g, _ = R.load_db(param_dirs, 'fighter/fighter_param.bin')
    if g is not None and any(e[0][1] == spec['kind'] for e in g[2]):
        err.append('fighter_param.bin already has kind 0x%X' % spec['kind'])
    msbt = R.first(ui_dirs, 'message/melee.msbt')
    if msbt:
        data = open(msbt, 'rb').read()
        if ('MmelCharaN_01_%s' % spec['ui_name']).encode('utf-16-be') in data or \
                ('MmelCharaN_01_%s' % spec['ui_name']).encode() in data:
            err.append('melee.msbt already has labels for %s' % spec['ui_name'])
    else:
        err.append('no ui/message/melee.msbt in the UI / data folders')
    if not 1 <= spec.get('costumes', 8) <= 16:
        err.append('costumes: 1-16')
    try:
        source_info(spec['source'], reg)
    except CloneError as e:
        err.append(str(e))
    return err


def record(spec, reg):
    """the registry record of a planned clone"""
    sk, sname, scap, sui, native = source_info(spec['source'], reg)
    src_rec = next((f for f in reg['fighters'] if f['name'] == sname), None)
    base_ui_id = src_rec['base_ui_id'] if src_rec else next(i for i, k in A_KIND_OF_ID.items() if k == sk)
    return {'kind': spec['kind'], 'name': spec['name'], 'cap': spec['cap'], 'ui_id': spec['ui_id'],
            'ui_name': spec['ui_name'], 'title': spec.get('title') or spec['ui_name'], 'base': native,
            'source': sname, 'source_kind': sk, 'source_ui': sui, 'base_ui_id': base_ui_id,
            'base_ui_name': R.UI_NAMES[base_ui_id], 'series': spec.get('series'), 'costumes': spec.get('costumes'),
            'sort': spec.get('sort'), 'subtitle': spec.get('subtitle'),
            'weapons': list(spec.get('weapons') or []), 'customs': bool(spec.get('customs')),
            'fanfare': bool(spec.get('fanfare', True)), 'random': bool(spec.get('random', True)),
            'own_sound': bool(spec.get('own_sound', True)), 'own_effects': bool(spec.get('own_effects', True)),
            'plates': bool(spec.get('plates', True))}


def sort_keys(param_dirs, reg, after=None, value=None):
    """the clone's three sort keys: after a character (its first key + 1; the others after every entry), an
    explicit first key, or after every entry. Returns (keys, [ids whose first key moves up by one])"""
    g, _ = R.load_db(param_dirs, 'ui/ui_character_db.bin')
    fs = [e for e in g[2] if e[0][1] < 200]
    top = [max(e[13 + j][1] for e in fs) + 1 for j in range(3)]
    if value is None and after is None:
        return top, []
    if value is None:
        e = next((e for e in fs if after in (e[0][1], R.UI_NAMES[e[0][1]] if e[0][1] < 59 else None)
                  or any(f['ui_id'] == e[0][1] and after in (f['name'], f['ui_name']) for f in reg['fighters'])), None)
        if e is None:
            raise CloneError('no character %r to place the clone after' % (after,))
        value = e[13][1] + 1
    shift = [e[0][1] for e in fs if e[13][1] >= value]
    if value + 1 > 127 or top[0] + 1 > 127:
        raise CloneError('sort key past 127')
    return [value, top[1], top[2]], shift


# ---------------------------------------------------------------- build
def build(rec, data_dir, ui_dir, out_data, reg, portraits=None, log=print, renumber=(), csb_names=None):
    """writes the clone's data files into out_data (laid out like the game's data/). reg: the registry WITH rec.
    portraits: {(set, costume NN): png path}. renumber: ids whose first sort key goes up by one."""
    param_dirs = [os.path.join(out_data, 'param'), os.path.join(data_dir, 'param')]
    ui_dirs = [os.path.join(out_data, 'ui'), ui_dir, os.path.join(data_dir, 'ui')]
    A.UI_NAMES = _ui_names(reg)
    used_ui = [d for d in ui_dirs if d and os.path.isdir(d)]
    A.used_texture_ids = lambda _d: set().union(*[A.used_texture_ids_orig(x) for x in used_ui])
    sk = rec['source_kind']
    r = {'kind': rec['kind'], 'name': rec['name'], 'cap': rec['cap'], 'base': rec['source'], 'bkind': sk,
         'bcap': next(f['cap'] for f in reg['fighters'] if f['name'] == rec['source'])
         if sk >= 0x41 else A.CAPS[sk],
         'id': rec['ui_id'], 'ui_name': rec['ui_name'], 'title': rec['title'], 'subtitle': rec.get('subtitle'),
         'series': rec.get('series'), 'costumes': rec.get('costumes'), 'sort': rec.get('sort'),
         'weapons': {art: k for art, k in rec.get('weapon_kinds', {}).items()}}
    out = []
    a = ns(param=param_dirs, ui=ui_dir if os.path.isdir(os.path.join(ui_dir, 'replace')) else os.path.join(data_dir, 'ui'),
           out=out_data, msbt=R.first(ui_dirs, 'message/melee.msbt'), articles=False, keep_effect_ids=False,
           model=None, folder=None)
    logs = []
    A.edit_params([r], a, logs)
    if renumber:
        _renumber(out_data, renumber, rec['ui_id'], logs)
    A.edit_msbt([r], a, logs)
    # portraits: the base's (new texture ids), then the imported PNGs; sets the base has no file of take a
    # template (another character's file of that set) when a PNG is given
    pkg_ui = os.path.join(out_data, 'ui')
    if sk >= 0x41 and os.path.isdir(os.path.join(pkg_ui, 'replace', 'chr')) and any(
            f.startswith('%s_%s' % (st, rec['source_ui'])) for st in os.listdir(os.path.join(pkg_ui, 'replace', 'chr'))
            for f in os.listdir(os.path.join(pkg_ui, 'replace', 'chr', st))):
        A.copy_portraits([r], ns(**dict(vars(a), ui=pkg_ui)), logs)     # a clone's portraits: in the package
    else:
        A.copy_portraits([r], a, logs)
    if rec.get('plates', True):
        out += name_plates(rec, a.out, portraits or {}, logs)
    out += _portraits(r, rec, a, ui_dirs, portraits or {}, logs)
    # the fighter folder
    src = R.first([os.path.join(out_data, 'fighter'), os.path.join(data_dir, 'fighter')], rec['source'])
    if src:
        a.folder = (src, out_data)
        A.copy_folder([r], a, logs)
    else:
        logs.append('MISSING fighter/%s/ in the data folder: no fighter folder copied' % rec['source'])
    if rec.get('customs'):
        logs += customs(rec, data_dir, ui_dir, out_data, ui_dirs)
    if rec.get('fanfare', True):
        logs += sound_config(rec, data_dir, out_data, reg, csb_names)
    logs += result_panel(rec, data_dir, out_data)
    if rec.get('own_sound'):
        from . import sound
        sound.own_banks(rec, out_data, data_dir, logs.append)
    for line in logs:
        log(line)
    return logs


def _renumber(out_data, ids, cid, logs):
    import s4param
    p = os.path.join(out_data, 'param', 'ui', 'ui_character_db.bin')
    data = open(p, 'rb').read()
    items = s4param.parse(data)
    g = R.group(items)
    moved = []
    for e in g[2]:
        if e[0][1] in ids and e[0][1] != cid:
            e[13] = (e[13][0], e[13][1] + 1)
            moved.append(e[0][1])
    open(p, 'wb').write(s4param.build(items, data[:8]))
    logs.append('param/ui/ui_character_db.bin: first sort key +1 for ids %s (the clone placed between them)'
                % ', '.join(map(str, moved)))


def _portraits(r, rec, a, ui_dirs, portraits, logs):
    out = []
    tex = A.NEW_TEXTURE_IDS + 0x100 * (rec['ui_id'] - 59) + 0x80
    used = A.used_texture_ids(None)
    for (st, nn), png in sorted(portraits.items()):
        fn = '%s_%s_%s.nut' % (st, rec['ui_name'], nn) if nn else '%s_%s.nut' % (st, rec['ui_name'])
        dst = os.path.join(a.out, 'ui', 'replace', 'chr', st, fn)
        template = dst if os.path.exists(dst) else None
        if template is None:
            for d in ui_dirs:
                sd = os.path.join(d or '', 'replace', 'chr', st)
                if d and os.path.isdir(sd):
                    cands = sorted(f for f in os.listdir(sd) if f.endswith('.nut'))
                    if cands:
                        template = os.path.join(sd, cands[0])
                        break
        if template is None:
            logs.append('portrait %s %s: no file of that set to take its format from; skipped' % (st, nn))
            continue
        n = len(T.texture_ids(T.read_nut(template)))
        ids = []
        for _ in range(max(1, n)):
            while tex in used:
                tex += 1
            used.add(tex)
            ids.append(tex)
        blob = T.put_png(template, png, ids)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(blob)
        out.append(dst)
        logs.append('portrait %s/%s from %s (format of %s, texture %s)' % (st, fn, os.path.basename(png),
                                                                         os.path.basename(template),
                                                                         ', '.join('0x%08X' % i for i in ids)))
    return out


def customs(rec, data_dir, ui_dir, out_data, ui_dirs):
    """custom moves: the base's menu.msbt labels and spi_10 icons under the clone's UI name"""
    import io
    import sys
    import contextlib
    import add_fighter_customs as AC
    menu = R.first(ui_dirs, 'message/menu.msbt')
    if not menu:
        return ['custom moves: no ui/message/menu.msbt in the UI / data folders: the labels were not added '
                '(the executable still gives the clone its base\'s custom moves)']
    spec = os.path.join(out_data, '..', '.customs_spec.json')
    json.dump({'kinds': [{'name': rec['name'], 'cap': rec['cap'], 'base': rec['base'],
                          'ui': {'id': rec['ui_id'], 'name': rec['ui_name'],
                                 'base_name': rec['source_ui']}}]}, open(spec, 'w'))
    argv = sys.argv
    sys.argv = ['add_fighter_customs.py', '--ui', ui_dir, '--menu', menu, '--kinds', spec, '--out', out_data] + \
        sum([['--used-ui', d] for d in ui_dirs if d and os.path.isdir(d)], [])
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            AC.main()
    finally:
        sys.argv = argv
        os.unlink(spec)
    return ['custom moves: ' + line for line in buf.getvalue().splitlines()]


def sound_config(rec, data_dir, out_data, reg, csb_names=None):
    """the victory fanfare (bgm_fighter.fbb record = kind) and the KO voices / chant (commonsoundtable.csb record
    0x3E + kind - 0x41): copies of the source's records"""
    logs = []
    dirs = [out_data, data_dir]
    p = R.first(dirs, 'sound/config/bgm_fighter.fbb')
    if p:
        d = open(p, 'rb').read()
        n = struct.unpack_from('<I', d, 8)[0]
        rows = [list(struct.unpack_from('<5I', d, 0xC + 0x14 * k)) for k in range(n)]
        src = rec['source_kind'] if rec['source_kind'] < n else R.KINDS.index(rec['base'])
        like = rows[src] if src < n else rows[3]
        while len(rows) <= rec['kind']:
            rows.append(list(rows[3]))
        rows[rec['kind']] = list(like)
        blob = d[:8] + struct.pack('<I', len(rows)) + b''.join(struct.pack('<5I', *x) for x in rows)
        dst = os.path.join(out_data, 'sound', 'config', 'bgm_fighter.fbb')
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(blob)
        logs.append('sound/config/bgm_fighter.fbb: record 0x%X = record 0x%X\'s (BGM 0x%X); %d -> %d records'
                    % (rec['kind'], src, like[4], n, len(rows)))
    else:
        logs.append('no sound/config/bgm_fighter.fbb: no victory fanfare record (the clone has none)')
    p = R.first(dirs, 'sound/config/commonsoundtable.csb')
    if p:
        d = open(p, 'rb').read()
        nval, recs = csb_parse(d)
        i = 0x3E + rec['kind'] - 0x41
        if rec['source_kind'] >= 0x41:
            si = 0x3E + rec['source_kind'] - 0x41
        else:
            cap = A.CAPS[rec['source_kind']]
            si = csb_names.index(cap) if cap in (csb_names or []) else None
        if si is None or si >= len(recs):
            return logs + ['commonsoundtable.csb: no record of %s to copy (no KO voice record)' % rec['source']]
        new, done = csb_merge(recs, nval, {i: recs[si]})
        dst = os.path.join(out_data, 'sound', 'config', 'commonsoundtable.csb')
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(csb_build(d, nval, new))
        logs.append('sound/config/commonsoundtable.csb: record 0x%X = record 0x%X\'s (%s); %d -> %d records'
                    % (i, si, done[0][1] if done else 'none', len(recs), len(new)))
    else:
        logs.append('no sound/config/commonsoundtable.csb: no KO voice / chant record')
    return logs


A.used_texture_ids_orig = A.used_texture_ids


# commonsoundtable.csb: 'CSB\0', u32 1, u16 values a record, u16 count, then count records of a 16-byte name and
# u32 values (LE); a record the tool pads with: no name, no voices (-1), no chant (0)
def csb_parse(d):
    assert d[:4] == b'CSB\0'
    nval, n = struct.unpack_from('<HH', d, 8)
    size = 0x10 + 4 * nval
    assert len(d) == 0xC + size * n, 'commonsoundtable.csb: %d bytes for %d records' % (len(d), n)
    return nval, [bytearray(d[0xC + size * i:0xC + size * (i + 1)]) for i in range(n)]


def csb_build(head, nval, recs):
    return head[:8] + struct.pack('<HH', nval, len(recs)) + b''.join(bytes(x) for x in recs)


def csb_merge(recs, nval, want):
    """recs with {index: record} added (records the file already has for those indices are kept)"""
    recs = [bytearray(x) for x in recs]
    none = bytearray(b'\0' * 16 + b'\xff' * (4 * (nval - 1)) + b'\0' * 4)
    while len(recs) < max(want, default=-1) + 1:
        recs.append(bytearray(none))
    done = []
    for i, rec in sorted(want.items()):
        if recs[i] == none:
            recs[i] = bytearray(rec)
            done.append((i, 'added'))
        else:
            done.append((i, 'kept (the file\'s own)'))
    return recs, done


def result_panel(rec, data_dir, out_data):
    """the results screen's loser-panel framing (param/ui/result_param.bin, keyed by the model name): the source's
    entry under the clone's name (its win poses are the source's copies)"""
    import result_param as RP
    p = R.first([os.path.join(out_data, 'param'), os.path.join(data_dir, 'param')], 'ui/result_param.bin')
    if not p:
        return ['no param/ui/result_param.bin: the clone\'s loser panel is drawn empty on the results screen']
    d = open(p, 'rb').read()
    names = [e[0] for e in RP.entries(d)[1]]
    if rec['name'] in names:
        return ['param/ui/result_param.bin already has %s' % rec['name']]
    if rec['source'] not in names:
        return ['param/ui/result_param.bin has no entry for %s to copy' % rec['source']]
    new = RP.add(d, rec['name'], rec['source'])
    dst = os.path.join(out_data, 'param', 'ui', 'result_param.bin')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(new)
    assert [e[0] for e in RP.entries(new)[1]] == names + [rec['name']]
    return ['param/ui/result_param.bin: entry %s = %s\'s (loser panel camera, win frames)' % (rec['name'], rec['source'])]


PLATE_SETS = ('chrn_11', 'chrn_12', 'chrn_40', 'chrn_41')     # the name plates (pictures of the name)


def name_plates(rec, out_root, portraits, logs):
    """the clone's name plates: its copies of the base's plates (the base's name as a picture) redrawn with the clone's
    title: white capitals with a dark edge, as large as the plate allows, on a clear background, in each plate's own
    size and format (an imported PNG for a plate set wins)"""
    import tempfile
    from PIL import Image, ImageDraw, ImageFont
    done = []
    d = os.path.join(out_root, 'ui', 'replace', 'chr')
    for st in PLATE_SETS:
        sd = os.path.join(d, st)
        if not os.path.isdir(sd):
            continue
        for f in sorted(os.listdir(sd)):
            if not f.startswith('%s_%s' % (st, rec['ui_name'])) or any(k[0] == st for k in portraits):
                continue
            p = os.path.join(sd, f)
            img = T.decode(p)
            if img is None:
                continue
            w, h = img.size
            text = (rec.get('title') or rec['ui_name']).upper()
            pic = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            dr = ImageDraw.Draw(pic)
            size, font = max(8, int(h * 0.7)), None
            while size >= 8:
                for name in ('DejaVuSans-Bold.ttf', 'arialbd.ttf', 'Arial Bold.ttf', 'DejaVuSans.ttf', 'arial.ttf'):
                    try:
                        font = ImageFont.truetype(name, size)
                        break
                    except Exception:
                        font = None
                font = font or ImageFont.load_default()
                box = dr.textbbox((0, 0), text, font=font, stroke_width=max(1, size // 12))
                if box[2] - box[0] <= w * 0.94 and box[3] - box[1] <= h * 0.9:
                    break
                size -= 2
            box = dr.textbbox((0, 0), text, font=font, stroke_width=max(1, size // 12))
            x = (w - (box[2] - box[0])) / 2 - box[0]
            y = (h - (box[3] - box[1])) / 2 - box[1]
            dr.text((x, y), text, font=font, fill=(255, 255, 255, 255), stroke_width=max(1, size // 12),
                    stroke_fill=(20, 20, 30, 255))
            tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            tmp.close()
            pic.save(tmp.name)
            ids = [t for _o, t in T.texture_ids(T.read_nut(p))]
            open(p, 'wb').write(T.put_png(p, tmp.name, ids))
            os.unlink(tmp.name)
            done.append('%s/%s' % (st, f))
    logs.append('name plates redrawn with %r: %s' % ((rec.get('title') or rec['ui_name']).upper(),
                                                       ', '.join(done) or 'none (the base has no plate files)'))
    return [os.path.join(d, x) for x in done]
