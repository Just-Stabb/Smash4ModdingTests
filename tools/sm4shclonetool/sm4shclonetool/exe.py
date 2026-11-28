"""The executable side: detect what cross_f.rpx is (vanilla, already patched by this tool, or something else), and
build the clone patch from the whole clone registry.

How a patch is made:
1. The "vanilla view" of the input: for a vanilla executable the file itself; for one this tool patched before, the
   file with every word the tool changed outside its own code space put back to the original it recorded in its
   marker, the relocations it moved put back, its code space cut off and the text region size restored.
2. The research generators (kind_expand / weapon_expand / base_effects_cave / base_customs_cave / stage_slot_cave)
   run on that view with ALL the clones (the old ones and the new), each in its own part of the tool's code space.
   They check every word they hook against the game's original (a changed word stops the build).
3. Their words are written over the view, plus the marker (the registry and the originals), and the relocations
   they ask for are moved. So patching again is incremental and idempotent: the result only depends on the vanilla
   view and the registry.
"""
import json
import os
import struct
import tempfile
import zlib

from . import _paths  # noqa: F401
from .rpx import Rpx, sha1_file

MAGIC = b'Sm4shCloneTool\0\0'
FORMAT = 1
VANILLA_TEXT_END = 0x04B77E1C        # the game's .text ends here (v288)
VANILLA_REGION = 0x2BB8670           # RPL file info textRegionSize: code space to 0x04BB8670
DEFAULT_BASE = 0x04B78000
SIZE = 0x40000                       # the tool's code space at least (to 0x04BB8000, inside the game's text region)
MAX_SPACE = 0x300000                 # at most (3 MB: the kinds part's calls back into the game stay in a branch's reach)
# offsets in the code space; the weapons part grows with the articles, the kinds part (last) with the fighters
# (the effect wrappers stay where v1 put them: the game's own calls to imported functions point into this space in
# the file, and a wrapper on one of those addresses would look like such a call to tools that check for them)
PARTS = [('marker', 0x0000, 0x4000), ('stage', 0x4000, 0x5000), ('customs', 0x5000, 0x6000),
         ('effects', 0x6000, 0x8000), ('random', 0x8000, 0x9000)]
WEAPONS_AT = 0xA000                  # past 0x04B811D0, the last of the file's import-call targets
DUMMY_OFF = 0x3FF8                   # the marker block's last 8 bytes: never read or run (moved relocations land here)
# the game's latest update (v288) cross_f.rpx as Nintendo ships it (37 of its 48 sections zlib-compressed): its file's
# SHA-1 and its memory image's digest (Rpx.image_digest: the loaded sections, so the same for a decompressed copy).
# The research's own executable (3b7e1b3f...) is not reproduced by plainly decompressing this one (its section layout
# differs); reported when seen. None of them is required: the hooked words decide (see README)
V288_SHA1 = 'a4cc56d89726c480637c20bea992a9afe8ee9ad9'
V288_IMAGE = '57ea6573427837227fbf66df472832c76951b0c1'
RESEARCH_SHA1 = '3b7e1b3f421f330e259a3200d391f47ee6b5931a'
WEAPON_FIRST = 0x185
FIRST_KIND, FIRST_ID = 0x41, 59


class ExeError(Exception):
    pass


def n_weapons(reg):
    from . import articles as A
    return sum(len(f.get('weapons') or []) for f in (reg or {}).get('fighters', [])) + len(A.records(reg))


def layout(base, reg=None):
    out = {name: (base + lo, base + hi) for name, lo, hi in PARTS}
    wsize = (0x10000 + 0x1800 * n_weapons(reg) + 0xFFF) & ~0xFFF
    out['weapons'] = (base + WEAPONS_AT, base + WEAPONS_AT + wsize)
    from . import clone_extras as CE
    esize = CE.size_for(len((reg or {}).get('fighters', [])))
    out['extras'] = (base + WEAPONS_AT + wsize, base + WEAPONS_AT + wsize + esize)
    # (2.0) the importer's part: the grown motion tables (motion_exe.py); empty without imports, so a registry
    # without them lays out (and patches) exactly as 1.5 did
    from . import motion_exe as ME
    at = base + WEAPONS_AT + wsize + esize
    isize = ME.size_for(reg)
    out['imports'] = (at, at + isize)
    from . import articles as A
    asize = A.size_for(reg)
    out['article_hooks'] = (at + isize, at + isize + asize)
    out['kinds'] = (at + isize + asize, base + MAX_SPACE)
    return out


def configure(base, reg=None):
    """point the generators at the tool's code space starting at base"""
    import kind_expand as K
    import weapon_expand as W
    import base_effects_cave as BE
    import base_customs_cave as BC
    import stage_slot_cave as SS
    lay = layout(base, reg)
    dummy = base + DUMMY_OFF
    K.CAVE, K.LIMIT = lay['kinds']
    K.RELOC_DUMMY = dummy
    W.CAVE, W.LIMIT = lay['weapons']
    BE.CAVE, BE.LIMIT = lay['effects']
    BC.CAVE, BC.LIMIT = lay['customs']
    SS.CAVE, SS.LIMIT = lay['stage']
    SS.RELOC_DUMMY = dummy
    return lay


# ---------------------------------------------------------------- marker
def find_marker(x):
    """(base, record) of this tool's marker in the code section, or None"""
    end = x.text_end()
    for base in range(DEFAULT_BASE, end - 0x20, 0x1000):
        if base < 0x04B70000:
            continue
        try:
            head = x.blob(base, 28)
        except KeyError:
            break
        if head[:16] == MAGIC:
            fmt, n, crc = struct.unpack('>III', head[16:28])
            raw = x.blob(base + 28, n)
            if zlib.crc32(raw) & 0xFFFFFFFF != crc:
                raise ExeError('the Sm4shCloneTool marker at 0x%08X is damaged (CRC)' % base)
            rec = json.loads(zlib.decompress(raw).decode())
            rec['format'] = fmt
            return base, rec
    return None


DATA_IMPORTS = ('effects', 'sounds')       # (2.0) imports with no executable part: kept in the project file only


def marker_registry(reg):
    """the registry as the marker keeps it: without the data-only imports (effects, sounds), which the project file
    keeps (the marker block is 16 KB; Session._registry merges them back)"""
    out = dict(reg)
    if reg.get('imports'):
        out['imports'] = {k: v for k, v in reg['imports'].items() if k not in DATA_IMPORTS and v}
        if not out['imports']:
            del out['imports']
    return out


def marker_bytes(rec):
    raw = zlib.compress(json.dumps(rec, sort_keys=True, separators=(',', ':')).encode(), 9)
    blob = MAGIC + struct.pack('>III', FORMAT, len(raw), zlib.crc32(raw) & 0xFFFFFFFF) + raw
    if len(blob) > DUMMY_OFF:
        raise ExeError('the registry no longer fits the marker block (%d bytes)' % len(blob))
    return blob + b'\0' * (-len(blob) % 4)


# ---------------------------------------------------------------- detection
_INSPECTED = {}


def inspect(path):
    """what the executable is: {'state': 'vanilla' | 'patched' | 'modified', ...} (remembered per file)"""
    st = os.stat(path)
    key = (os.path.abspath(path), st.st_size, st.st_mtime)
    if key not in _INSPECTED:
        _INSPECTED[key] = _inspect(path)
    return json.loads(json.dumps(_INSPECTED[key]))


def _inspect(path):
    x = Rpx(path)
    info = {'path': path, 'sha1': sha1_file(path), 'text_end': x.text_end(), 'text_region': x.text_region()}
    info['research_sha1'] = info['sha1'] == RESEARCH_SHA1
    info['v288'] = info['sha1'] == V288_SHA1 or x.image_digest() == V288_IMAGE
    m = find_marker(x)
    if m:
        info.update(state='patched', base=m[0], registry=m[1]['registry'], tool_version=m[1].get('tool'))
        return info
    info['registry'] = {'fighters': [], 'stages': []}
    problems = []
    if x.text_end() > DEFAULT_BASE:
        problems.append('its code section ends at 0x%08X: another mod uses the code space past the game\'s '
                        '(0x%08X)' % (x.text_end(), VANILLA_TEXT_END))
    if x.text_region() < VANILLA_REGION:
        problems.append('text region 0x%X is smaller than the game\'s 0x%X' % (x.text_region(), VANILLA_REGION))
    sites = check_sites(path)
    if sites:
        problems.append('%d word(s) the Sm4shCloneTool patches are not the game\'s originals (e.g. %s)'
                        % (len(sites), sites[0]))
    info['problems'] = problems
    info['site_conflicts'] = sites
    info['state'] = 'vanilla' if not problems else 'modified'
    return info


def check_sites(path):
    """the generators' own checks, dry-run with a sample clone of every kind of patch: [] when every word they
    hook holds the game's original"""
    tmp = tempfile.mkdtemp(prefix='ce_chk_')
    spec = os.path.join(tmp, 'spec.json')
    json.dump({'capacity': '0x60', 'kinds': [{'kind': '0x41', 'name': 'cecheck', 'cap': 'Cecheck', 'base': 'mario',
                                              'ui': {'id': 59, 'name': 'Cecheck', 'base_id': 4},
                                              'weapons': {'fireball': '0x185'}}]}, open(spec, 'w'))
    configure(DEFAULT_BASE)
    import kind_expand as K
    import weapon_expand as W
    import base_effects_cave as BE
    import base_customs_cave as BC
    out = []
    te = K.Image.text_end
    K.Image.text_end = lambda self: 0              # the code space check is inspect()'s own
    try:
        for name, run in (('kind expansion', lambda: K.build(spec, path)), ('weapons', lambda: W.build(spec, path)),
                          ('base effects', lambda: BE.build(spec, path)),
                          ('customs', lambda: BC.build(spec, path))):
            try:
                run()
            except AssertionError as e:
                out.append('%s: %s' % (name, e))
        from . import random_select as RS
        from . import clone_extras as CE
        try:
            img = K.Image(path)
            RS.build(img.w, [], [], DEFAULT_BASE + 0x8000, DEFAULT_BASE + 0x9000)
        except AssertionError as e:
            out.append(str(e))
        try:
            CE.check(img.w)
        except AssertionError as e:
            out.append(str(e))
    finally:
        K.Image.text_end = te
        os.unlink(spec)
        os.rmdir(tmp)
    return out


def vanilla_view(path, force=False):
    """(Rpx of the vanilla view, base of the tool's code space, registry, notes)"""
    x = Rpx(path)
    m = find_marker(x)
    notes = []
    if m:
        base, rec = m
        for a, w in rec['orig'].items():
            x.w32(int(a, 16), w)
        for sec, entry, off in rec['relocs']:
            x.set_reloc_offset(sec, entry, off)
        x.set_text_end(rec['text_end'])
        x.set_text_region(rec['text_region'])
        notes.append('patched by Sm4shCloneTool %s before: %d fighter clone(s), %d stage clone(s) kept'
                     % (rec.get('tool'), len(rec['registry']['fighters']), len(rec['registry']['stages'])))
        return x, base, rec['registry'], notes
    info = inspect(path)
    if info['state'] == 'vanilla':
        notes.append('vanilla (every word the tool patches holds the game\'s original; SHA-1 %s%s)'
                     % (info['sha1'], ', the game\'s v288 executable' if info.get('v288') else
                        ', the research base' if info['research_sha1'] else ''))
        return x, DEFAULT_BASE, info['registry'], notes
    if info['site_conflicts']:
        raise ExeError('this cross_f.rpx is modified where the Sm4shCloneTool patches it, so it can\'t be patched '
                       'safely:\n  ' + '\n  '.join(info['site_conflicts'][:10]))
    if not force:
        raise ExeError('this cross_f.rpx is not vanilla: ' + '; '.join(info['problems']) +
                       '. Use "patch anyway" (--force) to put the clone code after its code instead.')
    base = (x.text_end() + 0xFFFF) & ~0xFFFF
    notes.append('PATCH ANYWAY: not vanilla (%s); the clone code goes at 0x%08X, after its code'
                 % ('; '.join(info['problems']), base))
    return x, base, info['registry'], notes


# ---------------------------------------------------------------- specs for the generators
def kind_spec(reg):
    kinds = []
    weapon = WEAPON_FIRST
    for f in reg['fighters']:
        r = {'kind': '0x%X' % f['kind'], 'name': f['name'], 'cap': f['cap'], 'base': f['base'], 'ai': 'base',
             'ui': {'id': f['ui_id'], 'name': f['ui_name'], 'base_id': f.get('customs_base_id', f.get('base_ui_id')),
                    'base_name': f.get('base_ui_name')},
             'effects_base': not f.get('own_effects')}
        if f.get('weapons'):
            r['weapons'] = {}
            for art in f['weapons']:
                r['weapons'][art] = '0x%X' % weapon
                weapon += 1
        kinds.append(r)
    # (2.0) imported articles / article clones: brand-new articles of a clone (its record's weapons) or of a vanilla
    # fighter (the spec's owners), numbered after every clone's own articles
    from . import articles as A
    cl, van, weapon = A.spec_entries(reg, weapon)
    for r in kinds:
        if r['name'] in cl:
            r.setdefault('weapons', {}).update(cl[r['name']])
    n = len(kinds)
    cap = max(0x60, (FIRST_KIND + n + 0xF) & ~0xF)
    wcap = max(0x1C0, (WEAPON_FIRST + n_weapons(reg) + 0xF) & ~0xF)
    out = {'capacity': '0x%X' % cap, 'weapon_capacity': '0x%X' % wcap, 'kinds': kinds}
    if van:
        out['owners'] = [{'name': o, 'weapons': w} for o, w in sorted(van.items())]
    return out


def base_articles(path, base):
    """the names of the base fighter's own articles (its article list's entries before the special ones, named by
    the executable's weapon name table)"""
    import kind_expand as K
    import weapon_expand as W
    img = K.Image(path)
    names = [img.cstr(img.w(K.TABLES['lower'][0] + 4 * k)) for k in range(K.OLD_N)]
    # the descriptor switch's own jump table (kept as it is by the kind expansion): case -> bl getter -> lis / addi
    _c, _r, _s, table = K.SWITCHES['descriptor']
    e = table + 4 * K.kind_index(names, base)
    case = K.branch_target(e, img.w(e))
    g = K.branch_target(case, img.w(case))
    fdesc = ((img.w(g) & 0xFFFF) << 16) + K.sx16(img.w(g + 4))
    alist = img.w(fdesc + 8)
    entries, count = img.w(alist), img.w(alist + 4)
    out = []
    for i in range(count):
        e = img.w(entries + W.ARTICLE * i)
        if e & 0x80000000:
            break
        k = e & 0x3FFFFFFF
        if k < W.OLD_N:
            nm = img.cstr(img.w(0x10419604 + 4 * k))
            if nm and nm not in out:
                out.append(nm)
    return out


def weapon_kinds(reg, imported=False):
    """{fighter name: {article: weapon kind}} as kind_spec numbers them (imported: the imported articles too)"""
    out = {}
    spec = kind_spec(reg)
    for r in spec['kinds'] + (spec.get('owners', []) if imported else []):
        out[r['name']] = {a: int(k['kind'] if isinstance(k, dict) else k, 16) for a, k in (r.get('weapons') or {}).items()
                          if imported or not isinstance(k, dict)}
    return out


# ---------------------------------------------------------------- build
def generate(view, base, reg):
    """run the generators on the vanilla view file `view` with the tool's code space at `base`:
    {'words': {address: word}, 'relocs': [...], 'parts': {name: count}, 'layout': ..., 'end': code space end}"""
    import kind_expand as K
    import weapon_expand as W
    import base_effects_cave as BE
    import base_customs_cave as BC
    import stage_slot_cave as SS
    lay = configure(base, reg)
    lo, hi = base, base + MAX_SPACE
    work = os.path.dirname(os.path.abspath(view))
    spec_path = os.path.join(work, '.ce_spec_%x.json' % base)
    spec = kind_spec(reg)
    json.dump(spec, open(spec_path, 'w'), indent=1)
    words, relocs, parts = {}, [], {}

    def add(name, w, rel=(), override=()):
        for a, v in w.items():
            if a in words and words[a] != v and a not in override:
                raise ExeError('%s and another part both patch 0x%08X' % (name, a))
            words[a] = v & 0xFFFFFFFF
        relocs.extend(rel)
        parts[name] = len(w)
    te = K.Image.text_end
    if base != DEFAULT_BASE:                         # patch anyway / a relocation probe: past the game's code
        K.Image.text_end = lambda self: base
    kinfo = {}
    try:
        if reg['fighters']:
            B, info = K.build(spec_path, view)
            add('kind expansion', B.words, B.reloc_args())
            kinfo = {r['kind']: (r['minfo'], r['base_desc']) for r in info['kinds']}
        from . import articles as A
        if any(f.get('weapons') for f in reg['fighters']) or A.records(reg):
            WB, _wi = W.build(spec_path, view)
            add('weapons', WB.words, WB.reloc_args())
            for a, d in getattr(WB, 'extra_relocs', []):
                relocs.append((a, d))
        if A.cross_sources(reg):
            rv = Rpx(view)
            add('article hooks', A.build_exe(rv.r32, reg, *lay['article_hooks'])[0])
        if reg['fighters']:
            E = BE.build(spec_path, view)
            add('base effects', E['patch'], E['moved'])
            if any(f.get('customs') for f in reg['fighters']):
                cspec = dict(spec, kinds=[k for k, f in zip(spec['kinds'], reg['fighters']) if f.get('customs')])
                json.dump(cspec, open(spec_path + '.c', 'w'))
                C = BC.build(spec_path + '.c', view)[0]
                add('custom moves', C)
        if reg['fighters']:
            from . import clone_extras as CE
            from . import roster as R
            rv = Rpx(view)
            add('clone extras', CE.build(rv.r32, reg['fighters'], R.KINDS.index, *lay['extras'])[0])
        from . import motion_exe as ME
        if ME.motion_records(reg):
            rv = Rpx(view)
            mw, mrel, mov, _minfo = ME.build(rv.r32, reg, _kind_of(reg), kinfo, *lay['imports'],
                                             has_reloc=lambda a: bool(rv.relocs_at(a, a + 4)))
            add('imported motions', mw, mrel, override=mov)
        if reg['fighters'] or reg['stages']:
            from . import random_select as RS
            rv = Rpx(view)
            add('random select', RS.build(rv.r32, reg['fighters'], reg['stages'], *lay['random'])[0])
        if reg['stages']:
            new = [(s['name'], s['cosmetic']) for s in reg['stages']]
            sw, sp, count = SS.build(new, view)
            w = {SS.CAVE + 4 * i: v for i, v in enumerate(sw)}
            w.update(dict(sp))
            add('stage slots', w, [a for a in SS.TABLE_SITES])
            for s, k in zip(reg['stages'], range(SS.KIND_COUNT, count, 2)):
                assert s['kind'] == k, 'stage %s: kind 0x%X, the slot cave gives 0x%X' % (s['name'], s['kind'], k)
    finally:
        K.Image.text_end = te
        for p in (spec_path, spec_path + '.c'):
            if os.path.exists(p):
                os.unlink(p)
    # the code space's end: the last word written (at least SIZE)
    hi = max(base + SIZE, (max(a for a in words if lo <= a < hi) + 4 + 0xFFF) & ~0xFFF) if words else base + SIZE
    return {'words': words, 'relocs': relocs, 'parts': parts, 'layout': lay, 'base': base, 'end': hi}


def build(in_path, out_path, reg, force=False, log=print, work=None):
    """patch in_path for registry reg (every clone) into out_path; returns a summary dict"""
    x, base, old_reg, notes = vanilla_view(in_path, force)
    for n in notes:
        log(n)
    lo = base
    work = work or os.path.dirname(os.path.abspath(out_path))
    view = os.path.join(work, '.ce_vanilla_view.rpx')
    x.save(view)
    try:
        g = generate(view, base, reg)
        words, relocs, parts, lay, hi = g['words'], g['relocs'], g['parts'], g['layout'], g['end']
        # the originals of every word outside the tool's space, read from the vanilla view
        vx = Rpx(view)
        orig = {}
        for a in sorted(words):
            if not lo <= a < hi:
                orig['0x%08X' % a] = vx.r32(a)
        # write: grow, words, marker, relocations
        out = vx
        if out.text_region() < hi - 0x02000000:
            out.set_text_region(hi - 0x02000000)
        text_end_orig, region_orig = x.text_end(), x.text_region()
        out.set_text_end(hi)
        for a, v in words.items():
            out.w32(a, v)
        moved = []
        dummy = base + DUMMY_OFF
        for item in relocs:
            if isinstance(item, tuple):
                a, d = item
            else:
                a, d = item, dummy
            moved += out.move_relocs(a, a + 4, d)
        clashes = out.reloc_clashes({a: v for a, v in words.items()})
        if clashes:
            raise ExeError('patched words a relocation would still rewrite:\n  ' + '\n  '.join(clashes[:10]))
        from . import VERSION
        rec = {'tool': VERSION, 'registry': marker_registry(reg), 'orig': orig, 'relocs': [list(m) for m in moved],
               'text_end': text_end_orig, 'text_region': region_orig, 'base': base, 'end': hi}
        mb = marker_bytes(rec)
        for i in range(0, len(mb), 4):
            out.w32(base + i, struct.unpack('>I', mb[i:i + 4])[0])
        out.save(out_path)
    finally:
        if os.path.exists(view):
            os.unlink(view)
    summary = {'base': base, 'end': hi, 'layout': lay, 'parts': parts, 'in_place': len(orig), 'relocs_moved': len(moved),
               'words': len(words), 'notes': notes, 'sha1': sha1_file(out_path)}
    log('exe: %d words (%d in place, originals kept in the marker), %d relocations moved; code space '
        '0x%08X-0x%08X; parts: %s' % (len(words), len(orig), len(moved), lo, hi,
                                        ', '.join('%s %d' % kv for kv in parts.items())))
    return summary


def _kind_of(reg):
    """fighter name -> kind (a vanilla fighter's, or a clone's)"""
    from . import roster as R
    clones = {f['name']: f['kind'] for f in reg['fighters']}
    return lambda name: clones[name] if name in clones else R.KINDS.index(name)


def plan(in_path, reg, force=False):
    """what build() would do, without writing: (notes, list of patch descriptions)"""
    x, base, old_reg, notes = vanilla_view(in_path, force)
    lay = layout(base, reg)
    items = ['code space from 0x%08X (%s)' % (base, ', '.join(
        '%s 0x%08X' % (k, v[0]) for k, v in lay.items()))]
    if reg['fighters']:
        items.append('kind expansion: %d new kind(s) 0x41-0x%X (switches, name / size / sound tables, '
                     'per-kind arrays, character names, save records)' % (len(reg['fighters']),
                                                                         FIRST_KIND + len(reg['fighters']) - 1))
        items.append('base effects: the clones load their base\'s effect banks too')
        if any(f.get('weapons') for f in reg['fighters']):
            items.append('weapon kinds: %s' % ', '.join('%s %s' % (n, ', '.join('%s 0x%X' % kv for kv in w.items()))
                                                       for n, w in weapon_kinds(reg).items() if w))
        if any(f.get('customs') for f in reg['fighters']):
            items.append('custom moves: the clones own their base\'s custom moves')
    from . import articles as A
    wk = weapon_kinds(reg, imported=True)
    for a in A.records(reg):
        items.append('article %s of %s: weapon kind 0x%X (a copy of %s\'s %s; %s\'s article list)' % (
            a['name'], a['owner'], wk[a['owner']][a['name']], a['source_owner'], a['source'], a['owner']))
    for o, s_ in A.cross_sources(reg):
        items.append('fighter_param_vl load / unload hooks: kind 0x%X also loads kind 0x%X\'s params' % (o, s_))
    from . import motion_exe as ME
    for name, recs in sorted(ME.motion_records(reg).items()):
        items.append('motion table of %s: %d imported motion(s) 0x%X-0x%X (its motion info -> a grown table)'
                     % (name, len(recs), recs[0]['index'], recs[-1]['index']))
    if reg['stages']:
        items.append('stage slots: %d new stage(s), kinds 0x80-0x%X' % (len(reg['stages']),
                                                                       0x80 + 2 * len(reg['stages']) - 1))
    return notes, items
