#!/usr/bin/env python3
"""Texture ids of the new fighters' models: the scheme, the in-place re-id of an installed fighter, the checks
(docs/ultimate-port-guide.md, bug catalogue "texture ids").

The game keeps the textures it has loaded by id, so two models whose .nut files use the same id with different
pictures draw with whichever was loaded first: every port used to number its textures 0x40EB0000 + k in every costume,
and a P1 Steve made a P2 Squirtle draw with Steve's textures (user, fighters_texid_fix_v1).

The vanilla convention (fighter/<f>/model/*/cNN/model.nut, checked on Bowser 0x0B, Mario 0x11, Pit 0x1D, Robin 0x1F,
Zelda 0x2D): 0x40KK0000 a fighter (KK its own byte; the vanilla ones are 0x00 - 0x4F: the effects' 0x151KKnnn run to
Corrin's 0x49), + 0x400 x NN the body costume cNN (lNN: the same ids, the same textures), its articles from + 0x4800 in
0x800 blocks (Pit's bowarrow 0x4800, bow 0x5000, three 0x5800 + 0x80 x NN, lightarrow 0x6800, chargeshot 0x7000).

The new fighters (SCHEME):
  fighter          0x40KK0000, KK = 0x80 + its kind (Supamario 0x41 -> 0x40C10000 ... Squirtle 0x46 -> 0x40C60000):
                   above every vanilla KK, and above the old ports' shared 0x40EB only from kind 0x6B on (never reached:
                   kind_expand's table ends well before)
  body cNN         + 0x400 x NN  (NN 0 - 7, up to 0x400 textures)
  body lNN         the same ids as cNN when its .nut holds the same textures (a copy: ultimate_port.py low-models),
                   else + 0x2000 + 0x400 x NN
  article a, cNN   + 0x4800 + 0x800 x a + 0x80 x NN (a: its index in the fighter's registry list; up to 0x80 textures);
                   a costume whose .nut equals an earlier costume's (the same pictures under the same ids) shares its ids
Effect models (fighter/<f>/effect/*/model/*, 0x15xxxxxx) are copies of the base's effects with its ids: left alone
(the check compares them with the base's, when the vanilla files are there).
The registry: reference/port_bases.json "_texture_ids" (fighter -> {kind, base, articles}).

  python3 tools/fighter_texture_ids.py scheme [NAME...]            the ranges
  python3 tools/fighter_texture_ids.py rewrite FIGHTER_DIR [--name NAME] [--dry-run] [--vanilla DIR]
        an installed fighter/<name> folder re-id'd in place: every model/*/[cl]NN/model.nut, model.nud, metal.nud,
        model.mta and material_anime*.pac (texture patterns); a metal.nud naming a texture its .nut doesn't have gets
        the .nut's metal one (repair_metal)
  python3 tools/fighter_texture_ids.py fix-package NAME[,NAME...] OUT(.zip|DIR) PKG [PKG...] [--prefix P]
                                       [--low-models] [--vanilla DIR]
        the packages overlaid in install order (as tools/port_check.py, without optional_* folders), each NAME's model
        folders re-id'd; only the files that change written (nothing else extracted)
  python3 tools/fighter_texture_ids.py check PKG_OR_DIR [...] [--vanilla DIR]   T1 / T2 over an install
A folder holding only a base's own textures under the base's ids (a copy: Supamario's articles, Squirtle's water,
Sephiroth's phantom) keeps them (ours()); with --vanilla, a base id whose picture differs from the base's is re-id'd.
"""
import argparse
import hashlib
import json
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

REGISTRY = os.path.join(ROOT, 'reference', 'port_bases.json')
REG_KEY = '_texture_ids'
VANILLA_KK_MAX = 0x4F                   # vanilla fighters' KK bytes (Corrin 0x49; room left)
OLD_PORT_BASE = 0x40EB0000              # the ids every port used before (ultimate_fighter.py TEX_ID)
BODY_STRIDE = 0x400
LOW_OFFSET = 0x2000
ARTICLE_START = 0x4800
ARTICLE_STRIDE = 0x800
ARTICLE_COSTUME = 0x80
COMMON_TOP = 0x10                       # 0x10xxxxxx: the game's own common textures (ramps, cube maps): never ours


# ------------------------------------------------------------------ the scheme
def fighter_base(kind):
    kk = 0x80 + int(kind)
    if not VANILLA_KK_MAX < kk <= 0xFF or kk == (OLD_PORT_BASE >> 16) & 0xFF:
        raise ValueError('kind 0x%X: no texture-id byte for it (0x80 + kind must be 0x%02X - 0xFF, not 0xEB)' % (
            kind, VANILLA_KK_MAX + 1))
    return 0x40000000 | kk << 16


def registry():
    return json.load(open(REGISTRY)).get(REG_KEY, {})


def entry(name):
    e = registry().get(name)
    if e is None:
        kind = kind_of(name)
        if kind is None:
            raise SystemExit('%s: not in reference/port_bases.json "%s" nor tools/extra_kinds.json' % (name, REG_KEY))
        e = dict(kind='0x%X' % kind, base='0x%08X' % fighter_base(kind), articles=[])
    return e


def kind_of(name):
    for r in json.load(open(os.path.join(HERE, 'extra_kinds.json')))['kinds']:
        if r['name'] == name:
            return int(r['kind'], 0)
    return None


def register(name, kind=None, articles=()):
    """add NAME (and any new article names, appended: an article keeps its index) to the registry"""
    doc = json.load(open(REGISTRY))
    reg = doc.setdefault(REG_KEY, {})
    e = reg.get(name)
    changed = e is None
    if e is None:
        kind = kind if kind is not None else kind_of(name)
        e = reg[name] = dict(kind='0x%X' % kind, base='0x%08X' % fighter_base(kind), articles=[])
    for a in articles:
        if a not in e['articles']:
            e['articles'].append(a)
            changed = True
    if changed:
        _write_registry(reg)
    return e


def _write_registry(reg):
    """port_bases.json with its "_texture_ids" block replaced (or added at the end), one fighter a line; the rest of the
    file's text as it is"""
    text = open(REGISTRY).read()
    rows = ',\n'.join('  %s: %s' % (json.dumps(n), json.dumps(reg[n])) for n in sorted(reg, key=lambda n: int(reg[n]['kind'], 0)))
    block = '"%s": {\n%s\n }' % (REG_KEY, rows)
    m = re.search(r'"%s": \{.*?\n \}' % REG_KEY, text, re.S)
    if m:
        text = text[:m.start()] + block + text[m.end():]
    else:
        end = text.rstrip().rindex('}')
        text = text[:end].rstrip() + ',\n ' + block + '\n}\n'
    json.loads(text)
    open(REGISTRY, 'w').write(text)


def base_of(name):
    return int(entry(name)['base'], 0)


def body_id(name, costume):
    """the first id of body costume 'cNN' / NN (lNN: the same as cNN; ultimate_port.py low-models copies it)"""
    nn = int(costume[1:]) if isinstance(costume, str) else int(costume)
    assert 0 <= nn < 8, costume
    return base_of(name) + BODY_STRIDE * nn


def article_id(name, article, costume=0):
    e = entry(name)
    if article not in e['articles']:
        raise SystemExit('%s: article %r not in reference/port_bases.json "%s" (fighter_texture_ids.register)' % (
            name, article, REG_KEY))
    nn = int(costume[1:]) if isinstance(costume, str) else int(costume)
    assert 0 <= nn < 16
    return int(e['base'], 0) + ARTICLE_START + ARTICLE_STRIDE * e['articles'].index(article) + ARTICLE_COSTUME * nn


def fighter_range(name):
    b = base_of(name)
    return b, b + 0x10000


# ------------------------------------------------------------------ the files
def _unz(d):
    if d[:2] == b'\x78\x9c':
        return zlib.decompress(d), True
    return d, False


def _rez(d, was):
    return zlib.compress(bytes(d), 9) if was else bytes(d)


def be16(d, o):
    return struct.unpack_from('>H', d, o)[0]


def be32(d, o):
    return struct.unpack_from('>I', d, o)[0]


def nut_textures(data):
    """[(header offset, GIDX id offset, id, content digest)] of a .nut (NTWU or NTP3). The digest covers the picture
    (format, size, mips, the GX2 surface and the data), not the id or where it sits in the file"""
    d, _ = _unz(data)
    if d[:4] not in (b'NTWU', b'NTP3'):
        raise ValueError('not a .nut: %r' % d[:4])
    out = []
    hp = 0x10
    for _ in range(be16(d, 6)):
        hs = be16(d, hp + 12)
        g = d.find(b'GIDX', hp, hp + hs)
        tid = be32(d, g + 8) if g >= 0 else None
        h = hashlib.sha1(d[hp + 8:hp + 12] + d[hp + 14:hp + 0x20])
        data_size = be32(d, hp + 8)
        off = hp + be32(d, hp + 0x20)
        h.update(d[off:off + data_size])
        if d[:4] == b'NTWU':
            mip_off = hp + be32(d, hp + 0x24)
            gtx = hp + be32(d, hp + 0x28)
            mip_size = struct.unpack_from('>i', d, gtx + 40)[0]
            h.update(d[gtx:gtx + 0x74])
            if mip_size > 0:
                h.update(d[mip_off:mip_off + mip_size])
        out.append((hp, g + 8 if g >= 0 else None, tid, h.hexdigest()))
        hp += hs
    return out


def nut_set_ids(data, mapping):
    d, z = _unz(data)
    d = bytearray(d)
    for _hp, at, tid, _h in nut_textures(bytes(d)):
        if at is not None and tid in mapping:
            struct.pack_into('>I', d, at, mapping[tid])
    return _rez(d, z)


def nud_refs(data):
    """[(offset of a texture hash, the hash, mesh name, drawn)] of a .nud's materials (each offset once). drawn: the
    polygon has more than one triangle's worth of vertices (ultimate_fighter.py fills an unused slot with one)"""
    d, _ = _unz(data)
    if d[:4] != b'NDP3':
        raise ValueError('not a .nud: %r' % d[:4])
    _, _ver, nmesh, _b0, _b1, pstart, psize, vsize, vasize = struct.unpack_from('>IHhhhiiii', d, 4)
    str_base = 0x30 + pstart + psize + vsize + vasize
    seen, out = set(), []
    for i in range(nmesh):
        o = 0x30 + i * 0x30
        name_off, _u, _bind, _bone, npoly, obj = struct.unpack_from('>iHHhhi', d, o + 32)
        name = d[str_base + name_off:d.index(b'\0', str_base + name_off)].decode('latin1')
        for j in range(npoly):
            q = obj + j * 0x30
            nv = be16(d, q + 12)
            for to in struct.unpack_from('>4i', d, q + 16):
                if not to:
                    continue
                for k in range(be16(d, to + 10)):
                    at = to + 0x20 + 0x18 * k
                    if at in seen:
                        continue
                    seen.add(at)
                    out.append((at, be32(d, at), name, nv > 3))
    return out


def nud_set_ids(data, mapping):
    d, z = _unz(data)
    d = bytearray(d)
    for at, tid, _m, _dr in nud_refs(bytes(d)):
        if tid in mapping:
            struct.pack_into('>I', d, at, mapping[tid])
    return _rez(d, z)


def mta_refs(d, base=0):
    """[(offset, id)] of an MTA4's texture patterns (the default and each key's texture id; Smash Forge MTA.cs: a key is
    (texture id, frame)); both of a key's words are given, the caller maps only ids it knows"""
    if d[base:base + 4] != b'MTA4':
        return []
    _unk, _fr, _s, _e, _rate, mc, mo, _vc, _vo = struct.unpack_from('>9I', d, base + 4)
    out = []
    for i in range(mc):
        e = base + be32(d, base + mo + 4 * i)
        has_pat = d[e + 16]
        po = be32(d, e + 20)
        if not has_pat:
            continue
        pd = be32(d, base + po)
        if not pd:
            continue
        p = base + pd
        _default, kc, ko, _pfc, _pu = struct.unpack_from('>iIIIi', d, p)
        out.append((p, be32(d, p)))
        for j in range(kc):
            k = base + ko + 8 * j
            out.append((k, be32(d, k)))
            out.append((k + 4, be32(d, k + 4)))
    return out


def pac_entries(d):
    """[(name, offset, size)] of a KCAP .pac"""
    if d[:4] != b'KCAP':
        return []
    n = be32(d, 8)
    out = []
    for i in range(n):
        no, o, s = (be32(d, 0x10 + 4 * (i + k * n)) for k in range(3))
        out.append((d[no:d.index(b'\0', no)].decode('latin1'), o, s))
    return out


def anim_refs(data):
    """[(offset, word)] of a model.mta or a material_anime*.pac's patterns"""
    d, _ = _unz(data)
    if d[:4] == b'MTA4':
        return mta_refs(d)
    out = []
    for _n, o, _s in pac_entries(d):
        out += mta_refs(d, o)
    return out


def anim_set_ids(data, mapping):
    d, z = _unz(data)
    d = bytearray(d)
    hit = 0
    for at, w in anim_refs(bytes(d)):
        if w in mapping:
            struct.pack_into('>I', d, at, mapping[w])
            hit += 1
    return (_rez(d, z) if hit else data), hit


def kind_of_file(fn):
    if fn.endswith('.nut'):
        return 'nut'
    if fn.endswith('.nud'):
        return 'nud'
    if fn.endswith('.mta') or (fn.startswith('material_anime') and fn.endswith('.pac')):
        return 'anim'
    return None


# ------------------------------------------------------------------ an install's model folders
MODEL_RE = re.compile(r'fighter/([^/]+)/model/([^/]+)/([cl])(\d\d)/([^/]+)$')
EFFECT_RE = re.compile(r'fighter/([^/]+)/effect/([^/]+)/model/([^/]+)/([^/]+)$')


def folders(files):
    """{folder: {file name: loader}} for every fighter model folder (and effect model folder) among FILES (a {rel path
    from the game root: loader} dict)"""
    out = {}
    for rel, load in files.items():
        m = MODEL_RE.match(rel) or EFFECT_RE.match(rel)
        if m:
            out.setdefault(rel.rsplit('/', 1)[0], {})[rel.rsplit('/', 1)[1]] = load
    return out


def folder_info(folder):
    """(fighter, part, letter, NN) of fighter/<f>/model/<part>/<l><NN>; effect folders: (fighter, 'effect:<bank>/<m>',
    None, None)"""
    m = re.match(r'fighter/([^/]+)/model/([^/]+)/([cl])(\d\d)$', folder)
    if m:
        return m.group(1), m.group(2), m.group(3), int(m.group(4))
    m = re.match(r'fighter/([^/]+)/effect/([^/]+)/model/([^/]+)$', folder)
    return m.group(1), 'effect:%s/%s' % (m.group(2), m.group(3)), None, None


def is_vanilla_id(tid):
    """an id in the vanilla fighters' range (0x40KKxxxx, KK <= 0x4F): a base's own texture"""
    return tid >> 24 == 0x40 and (tid >> 16) & 0xFF <= VANILLA_KK_MAX


def vanilla_digests(dirs):
    """{id: {digest}} of every model.nut under DIRS (vanilla fighter trees: the bases' own textures)"""
    out = {}
    for vd in dirs or ():
        for d, _ds, fs in os.walk(vd, followlinks=True):
            if 'model.nut' in fs:
                try:
                    texs = nut_textures(open(os.path.join(d, 'model.nut'), 'rb').read())
                except ValueError:
                    continue
                for _hp, _at, tid, dig in texs:
                    out.setdefault(tid, set()).add(dig)
    return out


def ours(texs, vanilla=None):
    """does a .nut need ids of its own: any id outside the vanilla range, or (VANILLA given) a vanilla id whose picture
    isn't the vanilla one. A copy of a base's model with the base's pictures (Supamario's articles, Squirtle's water,
    Sephiroth's phantom) shares the base's ids harmlessly and keeps them"""
    for _hp, _at, tid, dig in texs:
        if not is_vanilla_id(tid):
            return True
        if vanilla is not None and tid in vanilla and dig not in vanilla[tid]:
            return True
    return False


def plan(name, model_folders, nut_of, add_articles=True, vanilla=None, log=print):
    """{folder: {old id: new id}} for NAME's model folders that need ids of their own (ours()). model_folders:
    [folder]; nut_of(folder) -> the .nut's bytes (or None). Articles not in the registry are appended to it when
    add_articles (an article keeps its index once there)"""
    parts = {}
    for f in model_folders:
        fi, part, letter, nn = folder_info(f)
        if fi != name or letter is None:
            continue
        data = nut_of(f)
        if data is None:
            continue
        texs = nut_textures(data)
        if not ours(texs, vanilla):
            log('%s: the base\'s own textures and ids (%d), left as they are' % (f, len(texs)))
            continue
        parts.setdefault(part, []).append((letter != 'c', nn, f, texs))
    new_articles = [p for p in sorted(parts) if p != 'body' and p not in entry(name)['articles']]
    if new_articles or name not in registry():
        if not add_articles:
            raise SystemExit('%s: not in the registry with articles %s (fighter_texture_ids.register)' % (
                name, new_articles))
        register(name, articles=new_articles)
    out = {}
    for part, fl in sorted(parts.items()):
        done = []                                  # [(signature, mapping)] of this part's folders so far
        for low, nn, f, texs in sorted(fl, key=lambda x: x[:3]):
            sig = tuple(sorted((t[2], t[3]) for t in texs))
            same = next((m for s, m in done if s == sig), None)
            if same is not None:
                out[f] = dict(same)
                continue
            if part == 'body':
                start = body_id(name, nn) + (LOW_OFFSET if low else 0)
                room = BODY_STRIDE
            else:
                start = article_id(name, part, nn + (8 if low else 0))
                room = ARTICLE_COSTUME
            ids = sorted({t[2] for t in texs if t[2] is not None})
            if len(ids) > room:
                raise SystemExit('%s: %d textures, room for %d' % (f, len(ids), room))
            mapping = {old: start + k for k, old in enumerate(ids)}
            out[f] = dict(mapping)                 # its own copy: repair_metal adds to it
            done.append((sig, mapping))
    return out


def repair_metal(files, mapping, log=print):
    """metal.nud's metal texture when it names an id its .nut doesn't have: Sephiroth's body c00 - c07 (tests 79 - 82
    shipped a rebuild's metal.nud, whose metal texture was 0x40EB0019 / 0x17, with test 41's model.nut, where it is
    0x40EB0018 / 0x16; in game his metal form drew whatever another port had loaded there). The one .nut texture
    model.nud doesn't use is the metal one (ultimate_fighter.py adds it last). Adds dangling -> its new id to MAPPING"""
    if 'metal.nud' not in files or 'model.nud' not in files:
        return None
    have = set(mapping)
    dangling = sorted({t for _a, t, _m, dr in nud_refs(files['metal.nud']()) if dr and t >> 24 != COMMON_TOP
                       and not is_vanilla_id(t) and t not in have})
    unused = sorted(have - {t for _a, t, _m, _d in nud_refs(files['model.nud']())})
    if len(dangling) == 1 and len(unused) == 1:
        mapping[dangling[0]] = mapping[unused[0]]
        log('  metal.nud: its metal texture %08X isn\'t in model.nut: the unused %08X (-> %08X)' % (
            dangling[0], unused[0], mapping[unused[0]]))
        return dangling[0], unused[0]
    if dangling:
        log('  metal.nud: ids not in model.nut %s, unused %s: not repaired' % (
            ['%08X' % x for x in dangling], ['%08X' % x for x in unused]))
    return None


def rewrite_folder(files, mapping, log=print):
    """{file name: new bytes} for the files of one model folder that change; files: {file name: loader}"""
    out = {}
    for fn, load in sorted(files.items()):
        k = kind_of_file(fn)
        if k is None:
            continue
        data = load()
        if k == 'nut':
            new = nut_set_ids(data, mapping)
        elif k == 'nud':
            new = nud_set_ids(data, mapping)
        else:
            new, _hit = anim_set_ids(data, mapping)
        if new != data:
            out[fn] = new
    return out


# ------------------------------------------------------------------ checks (tools/port_check.py T1 / T2)
def check(files, ports=None, vanilla=None, report=None, only=None):
    """findings [(severity, code, message)] over an install's fighter model / effect-model folders (FILES: {rel path
    from the game root: loader}).
    T1 texture-clash: an id two folders use for different pictures (another fighter, another costume / article, or the
       vanilla model with that id: VANILLA, vanilla_digests()); folders of one model kind with the same pictures (lNN as
       cNN, an article's costumes) share ids harmlessly, as vanilla's lNN do.
    T1 texture-range: a port's (PORTS, default the registry's) model .nut with an id neither its own (its range) nor a
       vanilla one (a base's texture it copied: the clash check compares those).
    T2 texture-ref: a model.nud / metal.nud texture of a drawn mesh, or a texture pattern, not in its own folder's .nut
       (0x10xxxxxx: the game's common textures).
    ONLY: report only findings that involve these fighters' folders"""
    rep = []
    add = report or (lambda s, c, m: rep.append((s, c, m)))
    ports = set(registry()) if ports is None else set(ports)
    mine = (lambda f: True) if not only else (lambda f: folder_info(f)[0] in only)
    fl = folders(files)
    owners = {}                                   # id -> {digest: [folder]}
    nuts = {}
    outside = {}                                  # fighter -> {folder: [ids]}
    for f, fs in sorted(fl.items()):
        if 'model.nut' not in fs:
            continue
        try:
            texs = nuts[f] = nut_textures(fs['model.nut']())
        except ValueError as e:
            add('WARN', 'T1 texture-ids', '%s/model.nut: %s' % (f, e))
            continue
        for _hp, _at, tid, dig in texs:
            owners.setdefault(tid, {}).setdefault(dig, []).append(f)
        fi, part, _l, _nn = folder_info(f)
        if fi in ports and not part.startswith('effect:') and mine(f):
            lo, hi = fighter_range(fi)
            out = sorted({t[2] for t in texs if not lo <= t[2] < hi and not is_vanilla_id(t[2])})
            if out:
                outside.setdefault(fi, {})[f] = out
    for fi, by in sorted(outside.items()):
        lo, hi = fighter_range(fi)
        ids = sorted({x for v in by.values() for x in v})
        add('ERROR', 'T1 texture-range', '%s: %d model folders with texture ids outside its 0x%08X-0x%08X (%s; %s): the '
            'game keys loaded textures by id, so another model with these ids draws with this one\'s (a P1 Steve drew a '
            'P2 Squirtle with his: fighters_texid_fix_v1; tools/fighter_texture_ids.py rewrite)' % (
                fi, len(by), lo, hi - 1, ', '.join(sorted(by))[:160], ', '.join('%08X' % x for x in ids[:4])))
    for tid, digs in (vanilla or {}).items():
        if tid in owners:
            for dg in digs:
                owners[tid].setdefault(dg, []).append('vanilla')
    clashes = {}
    for tid, by in owners.items():
        if len(by) > 1:
            fs = tuple(sorted({x for v in by.values() for x in v}))
            if any(x != 'vanilla' and mine(x) for x in fs):
                clashes.setdefault(fs, []).append(tid)
    for key, tids in sorted(clashes.items()):
        who = sorted({'/'.join(folder_info(x)[:2]) if x != 'vanilla' else x for x in key})
        add('ERROR', 'T1 texture-clash', '%d ids with different pictures in %d folders (%s; %s): the game keys loaded '
            'textures by id, whichever loads first draws on all of them (a P1 Steve drew a P2 Squirtle with his '
            'textures: fighters_texid_fix_v1)' % (len(tids), len(key), ', '.join(who),
                                                   ', '.join('%08X' % t for t in sorted(tids)[:4])))
    # T2: references
    empty_by = {}
    for f, fs in sorted(fl.items()):
        if not mine(f):
            continue
        have = {t[2] for t in nuts.get(f, ())}
        for fn in ('model.nud', 'metal.nud'):
            if fn not in fs:
                continue
            try:
                refs = nud_refs(fs[fn]())
            except ValueError:
                continue
            miss = [(t, m, dr) for _at, t, m, dr in refs if t >> 24 != COMMON_TOP and t not in have]
            drawn = sorted({(t, m) for t, m, dr in miss if dr})
            if drawn:
                add('ERROR', 'T2 texture-ref', '%s/%s: textures of drawn meshes not in its own model.nut: %s (they draw '
                    'with whatever model loaded those ids; Sephiroth\'s metal.nud: fighters_texid_fix_v1)' % (
                        f, fn, ', '.join('%08X %s' % x for x in drawn[:4])))
            for t, m, dr in miss:
                if not dr:
                    empty_by.setdefault(folder_info(f)[0], set()).add(t)
        for fn in sorted(fs):
            if kind_of_file(fn) == 'anim':
                try:
                    words = anim_refs(fs[fn]())
                except Exception:          # noqa: BLE001  (a layout this reader doesn't know: no pattern read)
                    continue
                bad = sorted({w for _at, w in words if w >> 24 == 0x40 and w not in have})
                if bad:
                    add('ERROR', 'T2 texture-ref', '%s/%s: texture patterns name ids not in its model.nut: %s' % (
                        f, fn, ', '.join('%08X' % t for t in bad[:6])))
    for fi, ts in sorted(empty_by.items()):
        add('INFO', 'T2 texture-ref-empty', '%s: empty mesh slots (one triangle, nothing drawn) name %d textures not in '
            'their model.nut (the base\'s: %s...)' % (fi, len(ts), ', '.join('%08X' % t for t in sorted(ts)[:3])))
    return rep


# ------------------------------------------------------------------ commands
SKIP_PARTS = re.compile(r'(^|/)(optional[^/]*|shortcut_check[^/]*)/')


def overlay(pkgs):
    """{rel path from the game root: loader}: PKGS (zips / folders) laid over each other in order, as
    tools/port_check.py's Install, without the packages' optional_* / shortcut_check folders (alternatives the user
    may not have installed)"""
    import zipfile
    import port_check
    norm = port_check.Install._norm
    out = {}
    for p in pkgs:
        if os.path.isdir(p):
            for d, _ds, fs in os.walk(p):
                for f in fs:
                    full = os.path.join(d, f)
                    n = os.path.relpath(full, p).replace(os.sep, '/')
                    rel = norm(n)
                    if rel and not SKIP_PARTS.search(n):
                        out[rel] = (lambda full=full: open(full, 'rb').read())
        else:
            z = zipfile.ZipFile(p)
            for n in z.namelist():
                rel = norm(n)
                if rel and not n.endswith('/') and not SKIP_PARTS.search(n):
                    out[rel] = (lambda n=n, z=z: z.read(n))
    return out


def cmd_scheme(a):
    reg = registry()
    for n in a.names or sorted(reg):
        e = entry(n)
        b = int(e['base'], 0)
        print('%-10s kind %-5s 0x%08X-0x%08X  body cNN +0x400 x NN (lNN: cNN\'s, else +0x2000); articles from +0x4800, '
              '0x800 each: %s' % (n, e['kind'], b, b + 0xFFFF, ', '.join(
                  '%s 0x%08X' % (x, article_id(n, x)) for x in e['articles']) or '-'))


def reid(name, files, vanilla=None, log=print, low_from_c=False, add_articles=True):
    """[(rel, new bytes)] re-id'ing NAME's model folders among FILES ({rel: loader}); low_from_c: a body cNN without
    its lNN gets one (copies of cNN's files, ultimate_port.py low-models: port_check M6). Also returns the plan"""
    fl = folders({k: v for k, v in files.items() if k.startswith('fighter/%s/' % name)})
    nut_of = lambda f: fl[f]['model.nut']() if 'model.nut' in fl.get(f, {}) else None   # noqa: E731
    maps = plan(name, sorted(fl), nut_of, add_articles=add_articles, vanilla=vanilla, log=log)
    out = []
    for f, mapping in sorted(maps.items()):
        repair_metal(fl[f], mapping, log)
        new = rewrite_folder(fl[f], mapping)
        log('%s: %d ids -> 0x%08X-0x%08X; %s' % (f, len(set(mapping.values())), min(mapping.values()),
                                                max(mapping.values()), ', '.join(sorted(new)) or 'nothing changes'))
        out += [(f + '/' + fn, data) for fn, data in sorted(new.items())]
        fi, part, letter, nn = folder_info(f)
        low = 'fighter/%s/model/%s/l%02d' % (fi, part, nn)
        if low_from_c and part == 'body' and letter == 'c' and low not in fl:
            out += [(low + '/' + fn, new.get(fn) or load()) for fn, load in sorted(fl[f].items())]
            log('%s: a copy of %s (no low model in the install)' % (low, f))
    return out, maps


def cmd_rewrite(a):
    root = os.path.normpath(a.fighter_dir)
    name = a.name or os.path.basename(root)
    files = {}
    for d, _ds, fs in os.walk(root):
        for fn in fs:
            p = os.path.join(d, fn)
            files['fighter/%s/%s' % (name, os.path.relpath(p, root).replace(os.sep, '/'))] = (
                lambda p=p: open(p, 'rb').read())
    out, _maps = reid(name, files, vanilla_digests(a.vanilla), add_articles=not a.dry_run)
    for rel, data in out:
        if not a.dry_run:
            p = os.path.join(root, os.path.relpath(rel, 'fighter/' + name))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(data)
    print('%d files %s' % (len(out), 'would change' if a.dry_run else 'rewritten'))


def cmd_fix_package(a):
    """the changed files of each NAME straight into a zip (OUT.zip) or folder: nothing else extracted"""
    import zipfile
    files = overlay(a.pkgs)
    van = vanilla_digests(a.vanilla)
    z = zipfile.ZipFile(a.out, 'a', zipfile.ZIP_DEFLATED) if a.out.endswith('.zip') else None
    total = 0
    for name in a.names.split(','):
        out, _maps = reid(name, files, van, low_from_c=a.low_models)
        for rel, data in out:
            dst = (a.prefix + '/' if a.prefix else '') + rel
            if z is not None:
                z.writestr(dst, data)
            else:
                p = os.path.join(a.out, dst)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, 'wb').write(data)
            total += len(data)
        print('%s: %d files' % (name, len(out)))
    if z is not None:
        z.close()
    print('%.1f MB written to %s' % (total / 1e6, a.out))


def cmd_check(a):
    rep = check(overlay(a.pkgs), vanilla=vanilla_digests(a.vanilla))
    for s, c, m in rep:
        print('%-5s %-20s %s' % (s, c, m))
    n = sum(1 for s, _c, _m in rep if s == 'ERROR')
    print('\n%d errors' % n)
    sys.exit(1 if n else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('scheme')
    s.add_argument('names', nargs='*')
    s.set_defaults(fn=cmd_scheme)
    s = sub.add_parser('rewrite')
    s.add_argument('fighter_dir')
    s.add_argument('--name')
    s.add_argument('--dry-run', action='store_true')
    s.add_argument('--vanilla', action='append', help='vanilla fighter trees: a base-id texture that differs is ours')
    s.set_defaults(fn=cmd_rewrite)
    s = sub.add_parser('fix-package')
    s.add_argument('names', help='NAME[,NAME...]')
    s.add_argument('out', help='OUT.zip (appended to) or a folder')
    s.add_argument('pkgs', nargs='+')
    s.add_argument('--prefix', default='', help='a folder inside the zip (the package\'s name)')
    s.add_argument('--low-models', action='store_true', help='a body cNN without its lNN gets a copy (port_check M6)')
    s.add_argument('--vanilla', action='append')
    s.set_defaults(fn=cmd_fix_package)
    s = sub.add_parser('check')
    s.add_argument('pkgs', nargs='+')
    s.add_argument('--vanilla', action='append', help='vanilla fighter trees to compare ids with')
    s.set_defaults(fn=cmd_check)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
