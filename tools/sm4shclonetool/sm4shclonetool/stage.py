"""The data side of a stage clone, built on vendor/add_stage.py: the stage-select database entry and its song list
(at the clone's cosmetic id), the names (MmelStageN_ / MmelStageG_), the stage-select icons (the source's, new texture
ids, or imported PNGs) and the renamed stage folders (stage/melee/<name>, stage/end/<name>). The executable side is
vendor/stage_slot_cave.py (exe.py): kinds 0x80 + 2i (normal) / 0x81 + 2i (Omega), the cosmetic id's name."""
import copy
import os
import re

from . import _paths  # noqa: F401
from . import roster as R
from . import textures as T
import add_stage as AS  # noqa: E402
import msbt  # noqa: E402
import s4param  # noqa: E402

NAME_RX = re.compile(r'^[A-Z][A-Za-z0-9_]{1,23}$')
FIRST_COSMETIC = 0x38
ICON_SETS = ['stage_00', 'stage_10', 'stage_11', 'stage_12', 'stage_13', 'stage_30', 'stage_31', 'stage_32',
             'stage_40', 'stage_41']


class StageError(Exception):
    pass


def next_slots(reg):
    return FIRST_COSMETIC + len(reg['stages']), 0x80 + 2 * len(reg['stages'])


def source_info(src, param_dirs, reg):
    """(cosmetic id, normal kind, name) of a vanilla stage (by folder name) or a stage clone"""
    for s in reg['stages']:
        if src == s['name']:
            return s['cosmetic'], s['kind'], s['name']
    names = R.STAGE_NAMES or R.MELEE_KINDS
    if src not in names:
        raise StageError('unknown base stage %r' % src)
    g, _ = R.load_db(param_dirs, 'ui/ui_stage_db.bin')
    k = names.index(src)
    cos = next((e[0][1] for e in g[2] if e[6][1] == k and e[0][1] != 0), None)
    if cos is None:
        raise StageError('%s has no stage-select entry' % src)
    return cos, k, src


def validate(spec, param_dirs, ui_dirs, reg):
    err = []
    if not NAME_RX.match(spec['name']):
        err.append('stage name: a capital letter then letters / digits / _, 2-24 (got %r)' % spec['name'])
    if spec['name'] in (R.STAGE_NAMES or R.MELEE_KINDS) or spec['name'] in {s['name'] for s in reg['stages']}:
        err.append('stage name %r is taken' % spec['name'])
    cos, kind = next_slots(reg)
    if spec['cosmetic'] != cos:
        err.append('cosmetic id 0x%X: new ids are consecutive from 0x38 (the next is 0x%X)' % (spec['cosmetic'], cos))
    if cos > 0xC7:
        err.append('no cosmetic ids left (0x38-0xC7)')
    g, _ = R.load_db(param_dirs, 'ui/ui_stage_db.bin')
    if g is None:
        err.append('no param/ui/ui_stage_db.bin')
    elif spec['cosmetic'] in [e[0][1] for e in g[2]]:
        err.append('cosmetic id 0x%X is already in ui_stage_db.bin' % spec['cosmetic'])
    if spec.get('page', 1) == 1:
        ss = R.sss_pages(param_dirs, reg)[1] if g is not None else []
        if len(ss) >= 48:
            err.append('page 1 of the stage select has 48 slots and all are used: choose page 2')
    try:
        source_info(spec['source'], param_dirs, reg)
    except StageError as e:
        err.append(str(e))
    return err


def record(spec, param_dirs, reg):
    cos, k, name = source_info(spec['source'], param_dirs, reg)
    return {'name': spec['name'], 'cosmetic': spec['cosmetic'], 'kind': next_slots(reg)[1], 'source': name,
            'source_cosmetic': cos, 'title': spec.get('title') or spec['name'], 'series': spec.get('series'),
            'page': spec.get('page', 1)}


def _db(path_in, path_out, edit):
    data = open(path_in, 'rb').read()
    items = s4param.parse(data)
    assert s4param.build(items, data[:8]) == data, '%s: round trip differs' % path_in
    g = R.group(items)
    added = edit(g)
    new = s4param.build(items, data[:8])
    os.makedirs(os.path.dirname(path_out), exist_ok=True)
    open(path_out, 'wb').write(new)
    # check: without the added entry it rebuilds byte for byte
    chk = s4param.parse(new)
    cg = R.group(chk)
    cg[2] = [e for e in cg[2] if e != added]
    cg[1] = len(cg[2])
    assert s4param.build(chk, new[:8]) == data, '%s: unchanged part differs' % path_out
    return added


def build(rec, data_dir, ui_dir, out_data, reg, icons=None, log=print):
    """writes the stage clone's files into out_data. icons: {set: png}"""
    pd = [os.path.join(out_data, 'param'), os.path.join(data_dir, 'param')]
    ud = [os.path.join(out_data, 'ui'), ui_dir, os.path.join(data_dir, 'ui')]
    logs = []
    cos, kind, src_cos = rec['cosmetic'], rec['kind'], rec['source_cosmetic']
    page = rec.get('page', 1)

    def stage_db(g):
        e = copy.deepcopy(next(x for x in g[2] if x[0][1] == src_cos))
        order = max(x[10][1] for x in g[2] if x[0][1] < 0xC8) + 1
        run = max(x[20][1] for x in g[2]) + 1
        AS.setv(e, 0, cos)
        AS.setv(e, 1, 1)
        AS.setv(e, 3, 1 if page == 2 else 0)
        AS.setv(e, 4, 1 if page == 2 else 0)
        for i in (6, 7):
            AS.setv(e, i, kind)
        for i in (8, 9):
            AS.setv(e, i, kind + 1)
        AS.setv(e, 10, rec.get('order') or order)
        AS.setv(e, 20, run)
        AS.insert(g, cos, e)
        return e
    e = _db(R.first(pd, 'ui/ui_stage_db.bin'), os.path.join(out_data, 'param', 'ui', 'ui_stage_db.bin'), stage_db)
    logs.append('param/ui/ui_stage_db.bin: entry 0x%X (copy of 0x%X; kinds 0x%X / 0x%X, page %d, order %d); '
                'rest byte-identical' % (cos, src_cos, kind, kind + 1, page, e[10][1]))

    def sound_db(g):
        x = copy.deepcopy(next(y for y in g[2] if y[0][1] == src_cos))
        AS.setv(x, 0, cos)
        AS.insert(g, cos, x)
        return x
    p = R.first(pd, 'ui/ui_sound_db.bin')
    if p:
        _db(p, os.path.join(out_data, 'param', 'ui', 'ui_sound_db.bin'), sound_db)
        logs.append('param/ui/ui_sound_db.bin: entry 0x%X = the source\'s songs (My Music)' % cos)
    else:
        logs.append('no param/ui/ui_sound_db.bin: no song list (the stage plays no My Music list)')

    src_m = R.first(ud, 'message/melee.msbt')
    data = open(src_m, 'rb').read()
    m = msbt.Msbt(data)
    old = {lab: m.text(lab) for lab in m.labels}
    for lab in ('MmelStageN_' + rec['name'], 'MmelStageG_' + rec['name']):
        if lab in old:
            raise StageError('melee.msbt already has %s' % lab)
    m.set('MmelStageN_' + rec['name'], rec['title'])
    series = rec.get('series')
    if series is None:
        series = old.get('MmelStageG_' + rec['source'], '')
    m.set('MmelStageG_' + rec['name'], series)
    dst = os.path.join(out_data, 'ui', 'message', 'melee.msbt')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(m.build())
    chk = msbt.Msbt(open(dst, 'rb').read())
    assert all(chk.text(lab) == t for lab, t in old.items()), 'melee.msbt: an old label changed'
    logs.append('ui/message/melee.msbt: MmelStageN_%s = %r, MmelStageG_%s = %r' % (rec['name'], rec['title'],
                                                                              rec['name'], series))

    # icons: every set the source has (its texture id replaced by a new one), then the imported PNGs
    used = set()
    for d in ud:
        if d and os.path.isdir(d):
            used |= AS.used_texture_ids(d)
    tex = AS.NEW_TEXTURE_IDS + 0x10 * (cos - FIRST_COSMETIC)
    done = []
    icons = dict(icons or {})
    for st in ICON_SETS:
        for root in ('replace', 'replace/append'):
            srcf = None
            for d in ud:
                if d and os.path.exists(os.path.join(d, root, 'stage', st, '%s_%s.nut' % (st, rec['source']))):
                    srcf = os.path.join(d, root, 'stage', st, '%s_%s.nut' % (st, rec['source']))
                    break
            png = icons.pop(st, None) if root == 'replace' else None
            if srcf is None and png:                    # no source file: another stage's of that set as the format
                for d in ud:
                    sd = os.path.join(d or '', root, 'stage', st)
                    if d and os.path.isdir(sd):
                        c = sorted(f for f in os.listdir(sd) if f.endswith('.nut'))
                        if c:
                            srcf = os.path.join(sd, c[0])
                            break
            if srcf is None:
                if png:
                    blob = T.new_nut(png, _next(tex, used))
                    tex = _next(tex, used)
                    used.add(tex)
                    _write(out_data, root, st, rec['name'], blob)
                    done.append('%s/%s (new, from %s)' % (root, st, os.path.basename(png)))
                continue
            data = T.read_nut(srcf)
            if st == 'stage_13':                         # page 2's tiles share one texture id (add_stage.py)
                blob = T.put_png(data, png, [i for _o, i in T.texture_ids(data)]) if png else data
            else:
                tex = _next(tex, used)
                used.add(tex)
                blob = T.put_png(data, png, [tex]) if png else AS.with_texture_id(data, tex)
            _write(out_data, root, st, rec['name'], blob)
            done.append('%s/%s%s' % (root, st, ' (%s)' % os.path.basename(png) if png else ''))
    logs.append('icons: ' + (', '.join(done) if done else 'NONE (no stage icons of %s in the UI folders)'
                             % rec['source']))
    if page == 2 and not any('stage_13' in x for x in done):
        logs.append('  WARNING: page 2 draws its tile from append/stage/stage_13: none, the tile will be blank')

    n = 0
    for v in ('melee', 'end'):
        s = R.first([os.path.join(out_data, 'stage', v), os.path.join(data_dir, 'stage', v)], rec['source'])
        if s:
            AS.copy_stage(s, os.path.join(out_data, 'stage', v, rec['name']), rec['source'], rec['name'])
            n += sum(len(f) for _r, _d, f in os.walk(os.path.join(out_data, 'stage', v, rec['name'])))
            logs.append('stage/%s/%s/ (copy of stage/%s/%s, file names renamed)' % (v, rec['name'], v, rec['source']))
        else:
            logs.append('MISSING stage/%s/%s/ in the data folder' % (v, rec['source']))
    for line in logs:
        log(line)
    return logs


def _next(tex, used):
    while tex in used:
        tex += 1
    return tex


def _write(out_data, root, st, name, blob):
    d = os.path.join(out_data, 'ui', root, 'stage', st)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, '%s_%s.nut' % (st, name)), 'wb').write(blob)
