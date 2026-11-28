"""(1.4) Kirby's copy of a clone with scripts of its own (the data side; the executable side is clone_extras.py's
KMAP / GRANT / COPYID hooks).

How Kirby's copy motions find their scripts: each Kirby motion kind has an animation (his static motion table,
descriptor 0x103829BC: the CRC32 of the animation's file name, in the copy's motion folder fighter/kirby/motion/
<base>body/) and a script hash (fighter/kirby/script/animcmd/body/motion.mtable[motion], the CRC32 of the script's
name, found in game.bin / effect.bin / sound.bin / expression.bin). A copy ability's motions are the Kirby motions
whose animations are in that copy's folder (e.g. Zero Suit Samus's 0x3F9-0x3FF): the "runs" below.

For a clone, the tool appends to Kirby's motion.mtable one entry per motion of the base's runs (past his 1222 motions;
the script lookup 0x02E42518 reads mtable[motion] unbounded and nothing else reads the file) with a new script name of
the clone's own ("<clone><Tail>", the tail of the animation's name, e.g. "zsscloneSpecialNStart", or
"<clone>_kirbycopy_<motion>"), and copies each of those scripts under the new name, with the base's effect ids
(0x3KK.... / 0x4KK...., KK = the base's kind) moved to the clone's kind (its own effect bank, loaded with the clone,
which Kirby can only copy when it is in the match) and the base's sound rows moved to the clone's own rows (its own
banks, its own Kirby-copy bank included). The executable then plays motion lo + i of a run from entry newbase + i while
that Kirby holds the clone's copy: rec["kirby_slots"] = [[lo, hi, newbase], ...].

Sm4shCommand shows the new scripts by the names written to <project>/Sm4shCommand_names.txt (AnimNames.txt format:
paste the lines into Sm4shCommand's AnimNames.txt; "Name -> <clone>body/<file>.omo" lets its Hitbox Viewer play the
animation).
"""
import copy
import os
import re
import shutil
import struct
import zlib

from . import _paths  # noqa: F401

KIRBY_DESC = 0x103829BC          # Kirby's static descriptor {kind 8, motion info*}; info = {table*, count, parts*, n}
KIRBY_KIND, OWN_FROM = 8, 0x211
BINS = ('game.bin', 'effect.bin', 'sound.bin', 'expression.bin')
NAMES_FILE = 'Sm4shCommand_names.txt'


def crc(name):
    return zlib.crc32(name.lower().encode()) & 0xFFFFFFFF


def anim_hash(name):
    return zlib.crc32(name.encode(), 0xFFFFFFFF) & 0xFFFFFFFF


def pac_names(path):
    b = open(path, 'rb').read()
    if b[:4] != b'KCAP':
        return []
    n = struct.unpack('>I', b[8:12])[0]
    offs = struct.unpack('>%dI' % n, b[0x10:0x10 + 4 * n])
    return [b[o:b.index(b'\0', o)].decode('latin1') for o in offs]


def motion_table(read):
    """[(animation hash, flags)] of Kirby's motions, from the executable"""
    if read(KIRBY_DESC) != KIRBY_KIND:
        raise ValueError('no Kirby descriptor at 0x%08X' % KIRBY_DESC)
    info = read(KIRBY_DESC + 4)
    tbl, count = read(info), read(info + 4)
    if not 1000 < count < 4000:
        raise ValueError('Kirby\'s motion count %d' % count)
    return [(read(tbl + 8 * i), read(tbl + 8 * i + 4)) for i in range(count)]


def copy_runs(table, folder):
    """the base's copy motions: [(lo, hi)] runs of Kirby's motions whose animations are in the folder's packs (a run
    may hold motions with no animation of their own, never another copy's); and {motion: animation name}"""
    names = {}
    for f in sorted(os.listdir(folder)):
        if f.endswith('.pac'):
            for n in pac_names(os.path.join(folder, f)):
                n = n[:-4] if n.endswith('.omo') else n
                names[anim_hash(n)] = n
    mine = {i for i, (h, _f) in enumerate(table) if i >= OWN_FROM and h in names}
    runs, cur = [], None
    for i in range(OWN_FROM, len(table)):
        if i in mine:
            cur = [cur[0], i] if cur else [i, i]
        elif cur and table[i][0] != 0:
            runs.append(tuple(cur))
            cur = None
    if cur:
        runs.append(tuple(cur))
    return runs, {i: names[table[i][0]] for i in mine}


def _tail(anim):
    m = re.match(r'Fit\w+?Body[A-Z][a-z0-9]*[A-Z]\d\d(.+)$', anim or '')
    return m.group(1) if m else None


def own_scripts(rec, kind_of, data_dir, out_data, read, rows, body, log):
    """Kirby's own copy scripts for the clone (rec['kirby_slots']); rows = the clone's {base row: (row, count)}"""
    import acmd
    rec['kirby_slots'] = []
    if not rec.get('kirby', True) or rec.get('kirby_hat_mode', 'own') == 'share' or not rec.get('kirby_scripts', True):
        return
    from . import roster as R
    rel = os.path.join('fighter', 'kirby', 'script', 'animcmd', 'body')
    srcs = {f: R.first([out_data, data_dir], os.path.join(rel, f)) for f in BINS + ('motion.mtable',)}
    if not all(srcs.values()):              # each file the package's (an earlier clone's), else the data folder's
        log('Kirby: no fighter/kirby/script/animcmd/body/ (motion.mtable and the four .bin) in the data folder: his copy '
            'of the clone runs the base\'s copy scripts')
        return
    folder = R.first([out_data, data_dir], os.path.join('fighter', 'kirby', 'motion', (body or '') + 'body')) \
        if body else None
    if not folder:
        log('Kirby: no fighter/kirby/motion/%sbody/ in the data folder: his copy of the clone runs the base\'s copy '
            'scripts (the tool finds the copy\'s motions by its animations)' % (body or '?'))
        return
    try:
        table = motion_table(read)
    except Exception as e:
        log('Kirby: own copy scripts not made (%s)' % e)
        return
    runs, anims = copy_runs(table, folder)
    if not runs:
        log('Kirby: no copy motion of %sbody found in his motion table: the base\'s copy scripts' % body)
        return
    dst = os.path.join(out_data, rel)
    os.makedirs(dst, exist_ok=True)
    for f, p in srcs.items():
        if os.path.abspath(p) != os.path.abspath(os.path.join(dst, f)):
            shutil.copyfile(p, os.path.join(dst, f))
    mt_path = os.path.join(dst, 'motion.mtable')
    raw = open(mt_path, 'rb').read()
    mt = list(struct.unpack('>%dI' % (len(raw) // 4), raw))
    files = {f: acmd.ACMDFile.load(os.path.join(dst, f)) for f in BINS}
    vanilla = set(mt[:len(table)])                     # Kirby's own script names (never reused)
    bk, k = kind_of(rec['base']), rec['kind']
    names, out_runs, n_scripts, n_fx, n_snd = [], [], 0, 0, 0
    by_name, plan = {}, []
    for lo, hi in runs:
        new = []                                       # (motion, old hash, new hash) of the run
        for s in range(lo, hi + 1):
            h = mt[s] if s < len(table) else 0
            if not h:
                new.append((s, 0, 0))
                continue
            tail = _tail(anims.get(s))
            name = '%s%s' % (rec['name'], tail) if tail and crc(body + tail) == h else None
            if name is None or by_name.get(name, h) != h:
                name = '%s_kirbycopy_%03x' % (rec['name'], s)
            while crc(name) in vanilla:
                name += '_'
            by_name[name] = h
            new.append((s, h, crc(name)))
            names.append((name, anims.get(s)))
        plan.append((lo, hi, new))
    hmap = {h: nh for _lo, _hi, new in plan for _s, h, nh in new if h}
    for lo, hi, new in plan:
        seq = [nh for _s, _h, nh in new]
        newbase = next((i for i in range(len(table), len(mt) - len(seq) + 1) if mt[i:i + len(seq)] == seq), None)
        if newbase is None:                            # not there from an earlier build: appended
            newbase = len(mt)
            mt += seq
        for s, h, nh in new:
            for fname, f in files.items():
                if not h or h not in f.scripts:
                    continue
                cmds = copy.deepcopy(f.scripts[h])
                for c in cmds:
                    if c.name in ('JUMP', 'CALL'):        # a jump / call to another script of the copy: its own copy
                        c.params = [hmap.get(v, v) if isinstance(v, int) else v for v in c.params]
                        continue
                    words = c.name.lower().split('_')
                    fx = re.search('graphic|effect', c.name, re.I)
                    snd = fname == 'sound.bin' or 'se' in words or any('sound' in w for w in words)
                    for i, v in enumerate(c.params):
                        if c.kind(i) == 1 or not isinstance(v, int):
                            continue
                        if fx and v >> 24 in (3, 4) and (v >> 16) & 0xFF == bk:
                            c.params[i] = (v & 0xFF00FFFF) | (k << 16)
                            n_fx += 1
                        elif snd and rows and v >> 16 in rows and (v & 0xFFFF) < rows[v >> 16][1]:
                            c.params[i] = rows[v >> 16][0] << 16 | (v & 0xFFFF)
                            n_snd += 1
                f.scripts[nh] = cmds
                n_scripts += 1
        out_runs.append([lo, hi, newbase])
    open(mt_path, 'wb').write(struct.pack('>%dI' % len(mt), *mt))
    for fname, f in files.items():
        f.save(os.path.join(dst, fname))
    rec['kirby_slots'] = out_runs
    out = os.path.join(os.path.dirname(os.path.abspath(out_data)), NAMES_FILE)
    write_names(out, rec['name'], names, rec.get('kirby_body') or body)
    log('Kirby: his copy of the clone has scripts of its own: motions %s -> motion.mtable %s (%d scripts copied, %d '
        'effect ids to kind 0x%X, %d sound ids to the clone\'s rows); names in %s' % (
            ', '.join('0x%X-0x%X' % (lo, hi) for lo, hi, _n in out_runs),
            ', '.join('0x%X-0x%X' % (nb, nb + hi - lo) for lo, hi, nb in out_runs), n_scripts, n_fx, k, n_snd,
            NAMES_FILE))


def write_names(path, clone, names, folder):
    """the Sm4shCommand names (AnimNames.txt lines) of a clone's Kirby copy scripts, in the project's names file
    (one section per clone, replaced on a rebuild)"""
    lines = open(path, encoding='utf-8').read().split('\n') if os.path.exists(path) else [
        '// Sm4shCloneTool: names of the scripts the clones add (Sm4shCommand AnimNames.txt format: paste these lines',
        '// at the end of Sm4shCommand\'s AnimNames.txt; "Name -> folder/File.omo" lets its Hitbox Viewer play it).', '']
    head = '// ---- Kirby: his copy of %s' % clone
    out, skip = [], False
    for ln in lines:
        if ln.startswith('// ---- '):
            skip = ln == head
        if not skip:
            out.append(ln)
    while out and not out[-1]:
        out.pop()
    out += ['', head]
    out += [n for n, _a in names]
    out += ['%s -> %sbody/%s.omo' % (n, folder, a) for n, a in names if a and folder]
    open(path, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
