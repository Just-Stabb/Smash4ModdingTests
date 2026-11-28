"""(2.0) New articles and article clones: a copy of an existing article (weapon) of any fighter, owned by a fighter (a
vanilla one or a clone), as a weapon kind of its own with its own name and files, spawnable by a new article id.

The executable (weapon_expand.py, the tool's vendored copy, from the registry's imports["articles"]):
- a new weapon kind (0x185 + n, numbered after the clones' own articles; the weapon tables, the 13 weapon-kind
  switches, the module rows are sized to them) whose native code is the source article's kind (its descriptor copied:
  its motion info, sub-articles, param getters; every switch sends it to its base's case);
- its name and folder = the new name, its owner = the owner fighter: its files load from fighter/<owner>/model/<name>/,
  motion/<name>/, script/animcmd/weapon/<name>/, script/msc/<name>/<name>.mscsb;
- the owner's article list gets it after the list's normal entries, before its first special one (the ArticleModule
  makes instances only for the entries before that), with the source's spawner (callback, extra) and the max count you
  give: its article id = that position (printed; ACMD / MSC make it by that id). A clone's list is its own already; a
  vanilla fighter's list is copied to the code space and its descriptor's +8 (in .data) pointed at it;
- params: the article's param getters read its owner's fighter_param_vl when the owner is the source fighter or a clone
  of it (a clone: its own vl file, so its own params); for another fighter's article they keep reading the source
  fighter's vl, which the tool's vl hooks (here) load and release with the owner (fighter_param_vl load 0x02EA6BC4 /
  unload 0x02EA5D64: their first word becomes a branch to a wrapper that, for the owner's kind, also loads / releases
  the source fighter's params; the game's own refcount keeps each loaded once).
The files (import_articles): the source's folders copied under the new name; its ACMD's effect ids moved to the owner's
effect bank (the same entries when the owner's bank is a copy of the source's; else those effects are imported into
the owner's bank, importer.import_effects, and their new ids used), its sound ids to the owner's rows (the same tones
when the owner's banks are copies of the source's; else the tones are copied into the owner's se bank as new sounds,
importer.import_sounds, and their new ids used).
"""
import os
import re
import shutil
import struct

from . import _paths  # noqa: F401
from . import roster as R

VL_LOAD, VL_UNLOAD = 0x02EA6BC4, 0x02EA5D64
VL_LOAD_FIRST, VL_UNLOAD_FIRST = 0x9421FF70, 0x9421FFD8          # stwu r1, -0x90(r1) / stwu r1, -0x28(r1)
NAME_RX = re.compile(r'^[a-z][a-z0-9_]{1,30}$')


def records(reg):
    return list(((reg or {}).get('imports') or {}).get('articles') or [])


def native(reg, name):
    """a fighter's vanilla (native) base: itself, or a clone's base"""
    return next((f['base'] for f in reg['fighters'] if f['name'] == name), name)


def cross_sources(reg):
    """[(owner kind, source fighter kind)] of the articles whose source is another fighter than the owner's native base
    (the vl hooks load the source's params with the owner)"""
    clones = {f['name']: f['kind'] for f in (reg or {}).get('fighters', [])}
    out = []
    for a in records(reg):
        so = native(reg, a['source_owner'])
        if so != native(reg, a['owner']):
            pair = (clones.get(a['owner'], R.KINDS.index(a['owner']) if a['owner'] in R.KINDS else -1), R.KINDS.index(so))
            if pair not in out:
                out.append(pair)
    return out


def size_for(reg):
    return 0x1000 if cross_sources(reg) else 0


def spec_entries(reg, first_kind):
    """the weapon_expand spec entries of the imported articles: ({clone name: {name: entry}}, {vanilla owner: {name:
    entry}}, next kind); entry = {"kind", "base" (an article of the owner's base, or "<fighter>/<article>"), "max"}"""
    clones = {f['name'] for f in reg['fighters']}
    cl, van = {}, {}
    k = first_kind
    for a in records(reg):
        so = native(reg, a['source_owner'])
        base = a['source'] if so == native(reg, a['owner']) else '%s/%s' % (so, a['source'])
        e = {'kind': '0x%X' % k, 'base': base, 'max': int(a.get('max') or 1)}
        (cl if a['owner'] in clones else van).setdefault(a['owner'], {})[a['name']] = e
        a['kind'] = k
        k += 1
    return cl, van, k


def build_exe(read, reg, lo, hi):
    """the vl load / unload hooks for cross_sources: ({address: word}, info)"""
    pairs = cross_sources(reg)
    if not pairs:
        return {}, {}
    import kind_expand as K
    from ppcasm import ha
    assert read(VL_LOAD) == VL_LOAD_FIRST and read(VL_UNLOAD) == VL_UNLOAD_FIRST, \
        'the fighter_param_vl load / unload entries are not the game\'s'
    tab = lo
    words = {}
    blob = b''.join(struct.pack('>II', o, s) for o, s in pairs) + struct.pack('>II', 0xFFFFFFFF, 0)
    for i in range(0, len(blob), 4):
        words[tab + i] = struct.unpack_from('>I', blob, i)[0]
    pc = tab + len(blob)
    info = {'table': tab, 'pairs': pairs}
    from ppcasm import Asm
    head = """
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        stw r30, 0x18(r1)
        stw r29, 0x14(r1)
        mr r31, r3
        mr r30, r4
"""
    loop = """
        lis r29, 0x%X
        addi r29, r29, %d
loop:
        lwz r0, 0(r29)
        cmpwi r0, -1
        beq done
        cmpw r0, r30
        bne next
        mr r3, r31
        lwz r4, 4(r29)
        bl body
next:
        addi r29, r29, 8
        b loop
done:
""" % (ha(tab), K.slo(tab))
    tail = """
        lwz r0, 0x24(r1)
        lwz r31, 0x1C(r1)
        lwz r30, 0x18(r1)
        lwz r29, 0x14(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
body:
        stwu r1, -0x%X(r1)
        b 0x%X
"""
    # load: the sources' params first, then the owner's (its return value returned); unload: the owner's first (its
    # return value kept at 0x10), then the sources'
    for entry, first, frame, what in ((VL_LOAD, VL_LOAD_FIRST, 0x90, 'load'), (VL_UNLOAD, VL_UNLOAD_FIRST, 0x28, 'unload')):
        at = (pc + 0xF) & ~0xF
        if what == 'load':
            src = head + loop + 'mr r3, r31\nmr r4, r30\nbl body\n' + tail % (frame, entry + 4)
        else:
            src = head + 'bl body\nstw r3, 0x10(r1)\n' + loop + 'lwz r3, 0x10(r1)\n' + tail % (frame, entry + 4)
        a = Asm(at)
        a.asm(src)
        for i, w in enumerate(a.words()):
            words[at + 4 * i] = w
        pc = at + 4 * len(a.words())
        words[entry] = (18 << 26) | ((at - entry) & 0x3FFFFFC)
        info[what] = at
    assert pc <= hi, 'the article hooks part is full'
    return words, info


# ---------------------------------------------------------------- the data side
def article_folders(root, art):
    """the source article's folders / files under a fighter folder: [(rel, kind)]"""
    out = []
    for rel in (os.path.join('model', art), os.path.join('motion', art), os.path.join('script', 'animcmd', 'weapon', art),
                os.path.join('script', 'msc', art)):
        if os.path.isdir(os.path.join(root, rel)):
            out.append(rel)
    return out


def _roots(pkg, data, fighter):
    return [os.path.join(pkg, 'fighter', fighter), os.path.join(data, 'fighter', fighter)]


def source_folders(pkg, data, fighter, art):
    """[(root, rel)] of the source article's folders: each from the package if it has it, else the data folder"""
    out = {}
    for r in reversed(_roots(pkg, data, fighter)):
        for rel in article_folders(r, art):
            out[rel] = r
    return [(r, rel) for rel, r in sorted(out.items())]


def existing_articles(pkg, data, fighter):
    names = set()
    for r in _roots(pkg, data, fighter):
        for sub in ('model', 'motion', os.path.join('script', 'animcmd', 'weapon'), os.path.join('script', 'msc')):
            d = os.path.join(r, sub)
            if os.path.isdir(d):
                names |= {n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n))}
    return names - {'body', 'bodyentry', 'bodyresult', 'bodyroutemap'}


def plan_files(it, tgt, reg, pkg, data, exe=None):
    from .importer import ImportError_
    name, so, sa = it.get('name') or '', it.get('source_owner') or '', it.get('source') or ''
    if not NAME_RX.match(name):
        raise ImportError_('article name %r: lowercase letters / digits / _, 2-31' % name)
    old = [a for a in records(reg) if a['owner'] == tgt.name and a['name'] == name]
    taken = existing_articles(pkg, data, tgt.name)
    if exe:
        from . import exe as X
        try:
            taken |= set(X.base_articles(exe, native(reg, tgt.name)))
        except Exception:                      # noqa: BLE001
            pass
    if not old and name in taken:
        raise ImportError_('%s already has an article named %s' % (tgt.name, name))
    if exe:
        _n, _t, inst = article_slots(exe, native(reg, tgt.name), instances=True)
        mine = sum(int(a.get('max') or 1) for a in records(reg) if a['owner'] == tgt.name and a['name'] != name)
        want = inst + mine + int(it.get('max') or 1)
        if want > MAX_INSTANCES:
            raise ImportError_('%s would pool %d article instances (its own %d + the new articles\' max counts %d): the '
                               'game\'s ArticleModule holds %d a fighter (more overwrite it)' % (
                                   tgt.name, want, inst, want - inst, MAX_INSTANCES))
    if so not in R.KINDS and not any(f['name'] == so for f in reg['fighters']):
        raise ImportError_('no fighter %r to copy an article from' % so)
    if not source_folders(pkg, data, so, sa):
        raise ImportError_('fighter/%s/ has no article %s (model/, motion/ or script/animcmd/weapon/%s/)' % (so, sa, sa))
    return ['fighter/%s/{model,motion,script/animcmd/weapon,script/msc}/%s/ (a copy of %s\'s %s; a new weapon kind, '
            'article id after %s\'s normal articles)' % (tgt.name, name, so, sa, tgt.name)]


MAX_INSTANCES = 64             # the ArticleModule's holder: 64 pooled instances a fighter, stored with no bound check


def article_slots(exe_path, fighter, instances=False):
    """(normal entries, total[, instances]) of a vanilla fighter's article list in the executable (its vanilla view);
    instances: the max counts of its normal entries (the ArticleModule pools that many, at most MAX_INSTANCES)"""
    from . import exe as X
    import kind_expand as K
    import weapon_expand as W
    x, _b, _r, _n = X.vanilla_view(exe_path)
    names = [x.cstr(x.r32(K.TABLES['lower'][0] + 4 * k)) for k in range(K.OLD_N)]
    _c, _r2, _s, table = K.SWITCHES['descriptor']
    e = table + 4 * K.kind_index(names, fighter)
    case = K.branch_target(e, x.r32(e))
    g = K.branch_target(case, x.r32(case))
    fdesc = ((x.r32(g) & 0xFFFF) << 16) + K.sx16(x.r32(g + 4))
    alist = x.r32(fdesc + 8)
    entries, count = x.r32(alist), x.r32(alist + 4)
    special = next((i for i in range(count) if x.r32(entries + W.ARTICLE * i) & 0x80000000), count)
    if instances:
        return special, count, sum(x.r32(entries + W.ARTICLE * i + 4) for i in range(special))
    return special, count


def _bank_kind(reg, fighter):
    """the effect bank (kind KK of 0x3KK) a fighter's scripts call: a vanilla fighter's own, a clone's own (own
    effects) or its base's"""
    rec = next((f for f in reg['fighters'] if f['name'] == fighter), None)
    if rec is None:
        return R.KINDS.index(fighter)
    return rec['kind'] if rec.get('own_effects') else R.KINDS.index(rec['base'])


def _bank_copied_from(reg, fighter):
    """for a clone with its own effect bank: the bank kind its effect folder was copied from"""
    rec = next((f for f in reg['fighters'] if f['name'] == fighter), None)
    if rec is None or not rec.get('own_effects'):
        return None
    return rec.get('source_kind', R.KINDS.index(rec['base']) if rec['base'] in R.KINDS else None)


def _rows(pkg, data, fighter, cap):
    """{bank kind ('se', 'vc', ...): (BINF id, soundlabeltable row)} of a fighter's banks"""
    from . import audio as AU
    from . import sound as SND
    tp = R.first([pkg, data], os.path.join('sound', 'config', 'soundlabeltable.bin'))
    if not tp:
        return {}
    table = SND.Table(open(tp, 'rb').read())
    out = {}
    for root in _roots(pkg, data, fighter):
        d = os.path.join(root, 'sound')
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            m = re.match(r'^snd_(se|vc)_%s(_common|_ouen)?\.nus3bank$' % re.escape(cap), f)
            if m and (m.group(1) + (m.group(2) or '')) not in out:
                try:
                    bid = AU.Bank(open(os.path.join(d, f), 'rb').read()).binf()[1]
                except Exception:              # noqa: BLE001
                    continue
                out[m.group(1) + (m.group(2) or '')] = (bid, table.row_of(bid), os.path.join(d, f))
    return out


def import_articles(tgt, items, reg, pkg, data, out_dir, log=print, exe_path=None):
    """the data side of new articles (items: {'name', 'source_owner', 'source', 'max'}); records them in
    reg['imports']['articles'] (the executable's part is built from those). Returns their records."""
    import acmd
    from . import importer as I
    recs = I.imports(reg).setdefault('articles', [])
    out = []
    for it in items:
        name, so, sa = it['name'], it['source_owner'], it['source']
        plan_files(it, tgt, reg, pkg, data, exe_path)
        rec = next((a for a in recs if a['owner'] == tgt.name and a['name'] == name), None)
        if rec is None:
            rec = {'owner': tgt.name, 'name': name, 'source_owner': so, 'source': sa, 'max': int(it.get('max') or 1)}
            recs.append(rec)
        else:
            rec.update(source_owner=so, source=sa, max=int(it.get('max') or rec.get('max') or 1))
        dst = os.path.join(pkg, 'fighter', tgt.name)
        for src, rel in source_folders(pkg, data, so, sa):
            nrel = os.path.join(os.path.dirname(rel), name)
            if os.path.isdir(os.path.join(dst, nrel)):
                shutil.rmtree(os.path.join(dst, nrel))
            shutil.copytree(os.path.join(src, rel), os.path.join(dst, nrel))
            if rel.startswith(os.path.join('script', 'msc')):
                for f in os.listdir(os.path.join(dst, nrel)):
                    if f == sa + '.mscsb':
                        os.rename(os.path.join(dst, nrel, f), os.path.join(dst, nrel, name + '.mscsb'))
        # effects
        wdir = os.path.join(dst, 'script', 'animcmd', 'weapon', name)
        sk, ok = _bank_kind(reg, so), _bank_kind(reg, tgt.name)
        fx_map, n_fx = {}, 0
        files = {f: acmd.ACMDFile.load(os.path.join(wdir, f)) for f in sorted(os.listdir(wdir)) if f.endswith('.bin')} \
            if os.path.isdir(wdir) else {}
        used_fx = sorted({v for f in files.values() for cmds in f.scripts.values() for c in cmds
                          if re.search('graphic|effect', c.name, re.I) for i, v in enumerate(c.params)
                          if c.kind(i) != 1 and isinstance(v, int) and v >> 24 == 3 and (v >> 16) & 0xFF == sk})
        if sk != ok and used_fx:
            if _bank_copied_from(reg, tgt.name) == sk:
                fx_map = {v: (v & 0xFF00FFFF) | (ok << 16) for v in used_fx}
                log('%s/%s: its %d effect ids moved to %s\'s bank 0x3%02X (a copy of 0x3%02X\'s)' % (
                    tgt.name, name, len(used_fx), tgt.name, ok, sk))
            else:
                sfolder = so if not any(f['name'] == so and not f.get('own_effects') for f in reg['fighters']) \
                    else native(reg, so)
                efc, ptcl = I.effect_source({'source': sfolder}, pkg, data)
                got = I.import_effects(tgt, [{'efc': efc, 'ptcl': ptcl, 'entry': v & 0xFFFF} for v in used_fx], reg,
                                       out_dir, log)
                fx_map = {v: e for v, (_n, e) in zip(used_fx, got)}
                log('%s/%s: its %d effects imported into %s\'s bank (from %s\'s)' % (tgt.name, name, len(used_fx),
                                                                                     tgt.name, sfolder))
        # sounds: the source's rows -> the owner's
        scap = _cap(reg, so)
        srows, orows = _rows(pkg, data, so, scap), _rows(pkg, data, tgt.name, tgt.cap)
        row_map, tone_map = {}, {}
        for k, (sbid, srow, _sp) in srows.items():
            if srow is None:
                continue
            o = orows.get(k)
            if o and o[1] == srow:
                continue                       # the same rows (the source's own banks, or a clone sharing them)
            if o and o[1] is not None and _same_labels(pkg, data, srow, o[1]):
                row_map[srow] = o[1]           # a copy of the source's bank on rows of its own
        used_snd = sorted({v for fname, f in files.items() for cmds in f.scripts.values() for c in cmds
                           for i, v in enumerate(c.params)
                           if (fname == 'sound.bin' or 'se' in c.name.lower().split('_') or 'sound' in c.name.lower())
                           and c.kind(i) != 1 and isinstance(v, int) and v >> 16 in {r for _b, r, _p in srows.values()
                                                                                     if r is not None}})
        need = [v for v in used_snd if v >> 16 not in row_map and v >> 16 not in {r for _b, r, _p in orows.values()}]
        if need and 'se' not in orows:
            log('%s/%s: %s has no sound/snd_se_%s.nus3bank in your files: the article\'s %d sound id(s) keep %s\'s rows '
                '(they play only while %s\'s banks are loaded)' % (tgt.name, name, tgt.name, tgt.cap, len(need), so, so))
        elif need:
            tone_map = _copy_tones(tgt, need, srows, reg, pkg, data, out_dir, log, '%s_%s' % (tgt.cap, name))
        n_snd = 0
        for fname, f in files.items():
            changed = False
            for cmds in f.scripts.values():
                for c in cmds:
                    fx = re.search('graphic|effect', c.name, re.I)
                    snd = fname == 'sound.bin' or 'se' in c.name.lower().split('_') or 'sound' in c.name.lower()
                    for i, v in enumerate(c.params):
                        if c.kind(i) == 1 or not isinstance(v, int):
                            continue
                        if fx and v in fx_map:
                            c.params[i] = fx_map[v]
                            n_fx += 1
                            changed = True
                        elif snd and v in tone_map:
                            c.params[i] = tone_map[v]
                            n_snd += 1
                            changed = True
                        elif snd and v >> 16 in row_map:
                            c.params[i] = row_map[v >> 16] << 16 | (v & 0xFFFF)
                            n_snd += 1
                            changed = True
            if changed:
                f.save(os.path.join(wdir, fname))
        # the article id: after the owner's normal articles and its earlier imported ones
        mine = [a for a in recs if a['owner'] == tgt.name]
        if exe_path:
            normal, _total = article_slots(exe_path, native(reg, tgt.name))
            rec['article_id'] = normal + mine.index(rec)
        else:
            rec.setdefault('article_id', -1)
        log('%s: article %s (a copy of %s\'s %s, max %d): article id %s; %d effect id(s) and %d sound id(s) in its '
            'scripts moved to %s\'s' % (tgt.name, name, so, sa, rec['max'], rec['article_id'], n_fx, n_snd, tgt.name))
        out.append(rec)
    return out


def _cap(reg, fighter):
    from .importer import CAPS
    rec = next((f for f in reg['fighters'] if f['name'] == fighter), None)
    return rec['cap'] if rec else CAPS[R.KINDS.index(fighter)]


def _same_labels(pkg, data, a, b):
    from . import sound as SND
    tp = R.first([pkg, data], os.path.join('sound', 'config', 'soundlabeltable.bin'))
    t = SND.Table(open(tp, 'rb').read())
    return t.tones(a) == t.tones(b)


def _copy_tones(tgt, ids, srows, reg, pkg, data, out_dir, log, prefix):
    """the source's tones of these sound ids copied into the owner's se bank as new sounds: {old id: new id}"""
    from . import audio as AU
    from . import importer as I
    from . import sound as SND
    import tempfile
    tp = R.first([pkg, data], os.path.join('sound', 'config', 'soundlabeltable.bin'))
    table = SND.Table(open(tp, 'rb').read())
    by_row = {r: p for _b, r, p in srows.values() if r is not None}
    tmp = tempfile.mkdtemp(prefix='s4ct_art_')
    items, keys = [], []
    try:
        for v in ids:
            row, lab = v >> 16, v & 0xFFFF
            bank = AU.Bank(open(by_row[row], 'rb').read())
            labels = table.tones(row)
            if lab >= len(labels) or labels[lab] >= len(bank.raw) or bank.tones[labels[lab]] is None:
                continue
            t = labels[lab]
            blob = bank.data_of(t)
            if blob[:4] != b'IDSP':
                continue
            p = os.path.join(tmp, '%08X.idsp' % v)
            open(p, 'wb').write(blob)
            items.append({'file': p, 'name': '%s_%s' % (re.sub(r'[^A-Za-z0-9_]', '_', bank.tones[t]['name'])[:180],
                                                        prefix),
                          'volume': bank.tones[t]['volume'], 'alias': bank.tones[t]['name']})
            keys.append(v)
        got = I.import_sounds(tgt, items, reg, out_dir, log) if items else []
    finally:
        shutil.rmtree(tmp)
    return {k: sid for k, (_n, sid) in zip(keys, got)}
