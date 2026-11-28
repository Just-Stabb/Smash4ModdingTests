"""The executable side: detect what cross_f.rpx is (vanilla, already patched by this tool, or something else), and
build the clone patch from the whole clone registry.

How a patch is made (docs/clone-engine.md):
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
SIZE = 0x40000                       # the tool's code space: marker, stages, customs, effects, kinds, weapons
# offsets in the code space
PARTS = [('marker', 0x0000, 0x4000), ('stage', 0x4000, 0x5000), ('customs', 0x5000, 0x6000),
         ('effects', 0x6000, 0x8000), ('kinds', 0x8000, 0x30000), ('weapons', 0x30000, 0x40000)]
DUMMY_OFF = 0x3FF8                   # the marker block's last 8 bytes: never read or run (moved relocations land here)
# SHA-1 of the cross_f.rpx the research (docs/native-notes.md) was done on; recorded, not required (see README)
RESEARCH_SHA1 = '3b7e1b3f421f330e259a3200d391f47ee6b5931a'
WEAPON_FIRST = 0x185
FIRST_KIND, FIRST_ID = 0x41, 59


class ExeError(Exception):
    pass


def layout(base):
    return {name: (base + lo, base + hi) for name, lo, hi in PARTS}


def configure(base):
    """point the generators at the tool's code space starting at base"""
    import kind_expand as K
    import weapon_expand as W
    import base_effects_cave as BE
    import base_customs_cave as BC
    import stage_slot_cave as SS
    lay = layout(base)
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
                     % (info['sha1'], ', the research base' if info['research_sha1'] else ''))
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
                    'base_name': f.get('base_ui_name')}}
        if f.get('weapons'):
            r['weapons'] = {}
            for art in f['weapons']:
                r['weapons'][art] = '0x%X' % weapon
                weapon += 1
        kinds.append(r)
    return {'capacity': '0x60', 'kinds': kinds}


def weapon_kinds(reg):
    """{fighter name: {article: weapon kind}} as kind_spec numbers them"""
    out = {}
    for r in kind_spec(reg)['kinds']:
        out[r['name']] = {a: int(k, 16) for a, k in (r.get('weapons') or {}).items()}
    return out


# ---------------------------------------------------------------- build
def build(in_path, out_path, reg, force=False, log=print, work=None):
    """patch in_path for registry reg (every clone) into out_path; returns a summary dict"""
    import kind_expand as K
    import weapon_expand as W
    import base_effects_cave as BE
    import base_customs_cave as BC
    import stage_slot_cave as SS
    x, base, old_reg, notes = vanilla_view(in_path, force)
    for n in notes:
        log(n)
    lay = configure(base)
    lo, hi = base, base + SIZE
    work = work or os.path.dirname(os.path.abspath(out_path))
    view = os.path.join(work, '.ce_vanilla_view.rpx')
    x.save(view)
    spec_path = os.path.join(work, '.ce_spec.json')
    spec = kind_spec(reg)
    json.dump(spec, open(spec_path, 'w'), indent=1)
    words, relocs, parts = {}, [], {}

    def add(name, w, rel=()):
        for a, v in w.items():
            if a in words and words[a] != v:
                raise ExeError('%s and another part both patch 0x%08X' % (name, a))
            words[a] = v & 0xFFFFFFFF
        relocs.extend(rel)
        parts[name] = len(w)
    try:
        te = K.Image.text_end
        if base != DEFAULT_BASE:                         # patch anyway: past another mod's code
            K.Image.text_end = lambda self: base
        try:
            if reg['fighters']:
                B, info = K.build(spec_path, view)
                add('kind expansion', B.words, B.reloc_args())
                if any(f.get('weapons') for f in reg['fighters']):
                    WB, _wi = W.build(spec_path, view)
                    add('weapons', WB.words, WB.reloc_args())
                    for a, d in getattr(WB, 'extra_relocs', []):
                        relocs.append((a, d))
                E = BE.build(spec_path, view)
                add('base effects', E['patch'], E['moved'])
                if any(f.get('customs') for f in reg['fighters']):
                    cspec = dict(spec, kinds=[k for k, f in zip(spec['kinds'], reg['fighters']) if f.get('customs')])
                    json.dump(cspec, open(spec_path + '.c', 'w'))
                    C = BC.build(spec_path + '.c', view)[0]
                    add('custom moves', C)
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
        rec = {'tool': VERSION, 'registry': reg, 'orig': orig, 'relocs': [list(m) for m in moved],
               'text_end': text_end_orig, 'text_region': region_orig, 'base': base}
        mb = marker_bytes(rec)
        for i in range(0, len(mb), 4):
            out.w32(base + i, struct.unpack('>I', mb[i:i + 4])[0])
        out.save(out_path)
    finally:
        for p in (view, spec_path, spec_path + '.c'):
            if os.path.exists(p):
                os.unlink(p)
    summary = {'base': base, 'layout': lay, 'parts': parts, 'in_place': len(orig), 'relocs_moved': len(moved),
               'words': len(words), 'notes': notes, 'sha1': sha1_file(out_path)}
    log('exe: %d words (%d in place, originals kept in the marker), %d relocations moved; code space '
        '0x%08X-0x%08X; parts: %s' % (len(words), len(orig), len(moved), lo, hi,
                                        ', '.join('%s %d' % kv for kv in parts.items())))
    return summary


def plan(in_path, reg, force=False):
    """what build() would do, without writing: (notes, list of patch descriptions)"""
    x, base, old_reg, notes = vanilla_view(in_path, force)
    lay = layout(base)
    items = ['code space 0x%08X-0x%08X (%s)' % (base, base + SIZE, ', '.join(
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
    if reg['stages']:
        items.append('stage slots: %d new stage(s), kinds 0x80-0x%X' % (len(reg['stages']),
                                                                       0x80 + 2 * len(reg['stages']) - 1))
    return notes, items
