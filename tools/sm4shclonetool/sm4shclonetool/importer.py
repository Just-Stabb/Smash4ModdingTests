"""(2.0) The importer: new animations (motion kinds with their script slots), effects and sounds for a fighter, a vanilla
one or a clone the tool made, written so Sm4shCommand opens the result (its fighter folder, motion.mtable, ACMD files,
sound banks and the soundlabeltable, its AnimNames / aliases files).

Everything goes into the package (INSTALL_TO_data) as every clone's files do: each file is read from the package first
(an earlier build's), then the data folder, and written into the package; the data folder is never written. The
registry records what was imported (reg["imports"]), so a rebuild finds it again (same names: same slots and ids) and
the executable's motion tables (motion_exe.py) are made from it.

Motions (import_motions): per imported animation
  - its .omo added to the fighter's motion/body/main.pac as `<prefix>Main<code><Name>.omo` (prefix: the pack's own,
    e.g. FitSZerosuitBody; code: the file's own [A-Z]NN or Z00), its part animations (hands / props) to their packs;
  - a new motion kind (index = the fighter's motion count + i): an entry in motion.mtable (the hash of the script name
    Name) and a script in game / effect / sound / expression.bin: empty (Script_End) or a copy of a chosen motion's;
  - its vl group 1 entry (fighter_param_vl_<name>.bin: 6 bytes a motion; the copied motion's, or zeros; the count must
    equal the motion count);
  - the executable's motion table grows by the same entries (motion_exe.py, through the patchset path: rpx / Aroma /
    Cemu);
  - its names for Sm4shCommand (Sm4shCommand_names.txt: "Name" and "Name -> body/<file>.omo", AnimNames.txt format).
Effects (import_effects): emitter sets of another effect bank (any fighter's .ptcl / .efc, or files you give) copied
  into the fighter's bank with their textures, shaders, shader parameters, key animations, meshes and effect models; a
  new .efc entry each: effect id 0x3KK0nnnn (KK the fighter's kind, nnnn the entry). No executable change.
Sounds (import_sounds): WAV / IDSP files added to one of the fighter's banks as new tones, with ids no other sound has,
  as Sm4shCommand's Sound Adder adds them (its rules, ported: the template tone, the TONE entry, PACK at 0x10, JUNK so
  PACK starts at 0x10, the costume banks on the same row padded to the same tone index, the row's labels = tone
  indexes, id = row << 16 | label); aliases written in Sm4shCommand's Aliases/sounds/<fighter>.txt format. No
  executable change.
"""
import copy
import os
import re
import shutil
import struct

from . import _paths  # noqa: F401
from . import pac as PAC
from . import roster as R

CAPS = ['MiiFighter', 'MiiSwordsman', 'MiiGunner', 'Mario', 'Donkey', 'Link', 'Samus', 'Yoshi', 'Kirby', 'Fox', 'Pikachu',
        'Luigi', 'Captain', 'Ness', 'Peach', 'Koopa', 'Zelda', 'Sheik', 'Marth', 'GameWatch', 'Ganon', 'Falco', 'Wario',
        'Metaknight', 'Pit', 'SZerosuit', 'Pikmin', 'Diddy', 'Dedede', 'Ike', 'Lucario', 'Robot', 'Toonlink',
        'Lizardon', 'Sonic', 'Purin', 'MarioD', 'Lucina', 'PitB', 'Rosetta', 'Wiifit', 'Littlemac', 'Murabito',
        'Palutena', 'Reflet', 'Duckhunt', 'KoopaJr', 'Shulk', 'Gekkouga', 'Pacman', 'Rockman', 'Mewtwo', 'Ryu', 'Lucas',
        'Roy', 'Cloud', 'Bayonetta', 'Kamui', 'KoopaG', 'Warioman', 'LittlemacG', 'LucarioM', 'MiiEnemyF', 'MiiEnemyS',
        'MiiEnemyG']          # the executable's Capitalised names (0x102FF588)
BINS = ('game.bin', 'effect.bin', 'sound.bin', 'expression.bin')
NAMES_FILE = 'Sm4shCommand_names.txt'
ALIASES_DIR = os.path.join('Sm4shCommand', 'Aliases', 'sounds')
NAME_RX = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,62}$')


class ImportError_(Exception):
    pass


def imports(reg):
    return reg.setdefault('imports', {})


# ---------------------------------------------------------------- the target fighter
class Target:
    """a fighter files are imported into: a vanilla fighter (by its folder name) or a clone in the registry"""

    def __init__(self, reg, name, pkg, data):
        self.pkg, self.data = pkg, data
        rec = next((f for f in reg['fighters'] if f['name'] == name), None)
        if rec:
            self.name, self.kind, self.cap, self.base, self.clone = rec['name'], rec['kind'], rec['cap'], rec['base'], True
        elif name in R.KINDS:
            self.name, self.kind, self.cap, self.base, self.clone = name, R.KINDS.index(name), CAPS[R.KINDS.index(name)], \
                name, False
            if self.kind in (0, 1, 2):
                raise ImportError_('%s: Mii fighters are not offered (their files are per-Mii)' % name)
        else:
            raise ImportError_('no fighter %r (a vanilla fighter\'s folder name, or a clone of this project)' % name)
        self.rec = rec

    def rel(self, *p):
        return os.path.join('fighter', self.name, *p)

    def find(self, rel):
        return R.first([self.pkg, self.data], rel)

    def writable(self, rel):
        """the package's copy of a file (copied there from the data folder first); None if neither has it"""
        dst = os.path.join(self.pkg, rel)
        if os.path.exists(dst):
            return dst
        src = os.path.join(self.data, rel)
        if not os.path.exists(src):
            return None
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        return dst

    def vl_rel(self):
        return os.path.join('param', 'fighter', 'fighter_param_vl_%s.bin' % self.name)


# ---------------------------------------------------------------- vl group 1 (6 bytes a motion)
def vl_group1(data):
    """(count, offset of the first entry, entries [6 ints]) of a fighter_param_vl file's first vector"""
    if data[:4] != b'\xff\xff\x00\x00' or data[8] != 0x20:
        raise ImportError_('not a fighter_param_vl file (no vector first)')
    n = struct.unpack('>I', data[9:13])[0]
    o = 13
    ents = []
    for _i in range(n):
        e = []
        for _k in range(6):
            t = data[o]
            if t not in (1, 2):
                raise ImportError_('vl group 1: a value of type %d (not a byte)' % t)
            e.append(data[o + 1])
            o += 2
        ents.append(e)
    return n, 13, ents, o


def vl_with(data, entries):
    """the vl file with group 1 = entries (its type bytes kept: the first entry's)"""
    n, first, old, end = vl_group1(data)
    types = [data[first + 2 * k] for k in range(6)] if n else [2] * 6
    body = b''.join(bytes([types[k], e[k] & 0xFF]) for e in entries for k in range(6))
    return data[:9] + struct.pack('>I', len(entries)) + body + data[end:]


# ---------------------------------------------------------------- the Sm4shCommand names file
def write_names(out_dir, head, lines):
    """a section of the project's Sm4shCommand names file (AnimNames.txt format), replaced on a rebuild"""
    path = os.path.join(out_dir, NAMES_FILE)
    old = open(path, encoding='utf-8').read().split('\n') if os.path.exists(path) else [
        '// Sm4shCloneTool: names of the scripts the clones add (Sm4shCommand AnimNames.txt format: paste these lines',
        '// at the end of Sm4shCommand\'s AnimNames.txt; "Name -> folder/File.omo" lets its Hitbox Viewer play it).', '']
    out, skip = [], False
    for ln in old:
        if ln.startswith('// ---- '):
            skip = ln == head
        if not skip:
            out.append(ln)
    while out and not out[-1]:
        out.pop()
    if lines:
        out += ['', head] + list(lines)
    open(path, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    return path


# ---------------------------------------------------------------- motions
def _prefix(pac, cap):
    for n in pac.names():
        m = re.match(r'^(Fit\w+?Body)Main[A-Z]\d\d', n)
        if m:
            return m.group(1)
    return 'Fit%sBody' % cap


def _code(fname):
    m = re.search(r'Main([A-Z]\d\d)', os.path.basename(fname))
    return m.group(1) if m else 'Z00'


def import_motions(tgt, items, reg, out_dir, log=print, read=None):
    """items: [{'name': script name, 'omo': .omo path, 'copy': motion index / script name to copy the scripts, the vl
    entry and the flags from (None: empty scripts, a zero vl entry), 'loop': bool (vl byte 1 = 6), 'parts': {part
    pac stem: .omo path}}]. Returns the fighter's import records (all of them, this build's added / replaced)."""
    import acmd
    recs = imports(reg).setdefault('motions', {}).setdefault(tgt.name, [])
    mt_rel = tgt.rel('script', 'animcmd', 'body', 'motion.mtable')
    mt_path = tgt.writable(mt_rel)
    if not mt_path:
        raise ImportError_('%s: no script/animcmd/body/motion.mtable in the data folder' % tgt.name)
    raw = open(mt_path, 'rb').read()
    mt = list(struct.unpack('>%dI' % (len(raw) // 4), raw))
    base_count = len(mt) - len(recs)
    for i, r in enumerate(recs):
        if mt[base_count + i] != acmd.crc(r['name']):
            raise ImportError_('%s: motion.mtable entry 0x%X is not the imported %s (the file was changed by hand?)'
                               % (tgt.name, base_count + i, r['name']))
    pac_rel = tgt.rel('motion', 'body', 'main.pac')
    pac_path = tgt.writable(pac_rel)
    if not pac_path:
        raise ImportError_('%s: no motion/body/main.pac in the data folder' % tgt.name)
    pac = PAC.Pac.load(pac_path)
    prefix = _prefix(pac, tgt.cap)
    vl_path = tgt.writable(tgt.vl_rel())
    if not vl_path:
        raise ImportError_('%s: no %s in the data folder' % (tgt.name, tgt.vl_rel()))
    vld = open(vl_path, 'rb').read()
    vn, _f, vents, _e = vl_group1(vld)
    if vn != len(mt):
        log('%s: fighter_param_vl group 1 has %d entries, motion.mtable %d: padded / cut to the motion count'
            % (tgt.name, vn, len(mt)))
        vents = (vents + [[0] * 6] * len(mt))[:len(mt)]
    bdir = os.path.dirname(mt_path)
    files = {}
    for f in BINS:
        p = tgt.writable(tgt.rel('script', 'animcmd', 'body', f))
        files[f] = acmd.ACMDFile.load(p) if p else acmd.ACMDFile({})
    known = {h for f in files.values() for h in f.scripts} | set(mt)
    part_pacs = {}
    for d in (os.path.dirname(pac_path), os.path.join(tgt.data, tgt.rel('motion', 'body'))):
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.endswith('.pac') and f != 'main.pac':
                part_pacs.setdefault(f[:-4].lower(), f)
    by_name = {r['name']: r for r in recs}
    added, replaced = [], []
    for it in items:
        name = it['name']
        if not NAME_RX.match(name):
            raise ImportError_('%s: motion name %r: a letter, then letters / digits / _ (up to 63)' % (tgt.name, name))
        h = acmd.crc(name)
        omo = open(it['omo'], 'rb').read()
        if omo[:4] != b'OMO ':
            raise ImportError_('%s: not an OMO animation' % it['omo'])
        anim = '%sMain%s%s.omo' % (prefix, _code(it['omo']), name)
        old = by_name.get(name)
        if old is None:
            if h in known:
                raise ImportError_('%s: a script named %s (hash 0x%08X) is already in its files: choose another name'
                                   % (tgt.name, name, h))
            if anim in pac.names() or PAC.anim_hash(anim) in {PAC.anim_hash(n) for n in pac.names()}:
                raise ImportError_('%s: main.pac already has an animation %s' % (tgt.name, anim))
            index = len(mt)
        else:
            index = old['index']
            if old['anim'] != anim[:-4]:
                pac.entries = [e for e in pac.entries if e[0] != old['anim'] + '.omo']
        pac.put(anim, omo)
        part_hashes = {}
        for stem, path in sorted((it.get('parts') or {}).items()):
            stem = stem.lower()
            if stem not in part_pacs:
                raise ImportError_('%s: no motion/body/%s.pac for the part animation %s' % (tgt.name, stem, path))
            pp = tgt.writable(tgt.rel('motion', 'body', part_pacs[stem]))
            ppac = PAC.Pac.load(pp)
            tag = _part_tag(ppac, prefix) or stem.capitalize()
            pname = '%s%s%s%s.omo' % (prefix, tag, _code(it['omo']), name)
            d = open(path, 'rb').read()
            if d[:4] != b'OMO ':
                raise ImportError_('%s: not an OMO animation' % path)
            ppac.put(pname, d)
            ppac.save(pp)
            part_hashes[stem] = PAC.anim_hash(pname)
        src = it.get('copy')
        src_i = None
        if src is not None:
            src_i = src if isinstance(src, int) else next((i for i, x in enumerate(mt) if x == acmd.crc(src)), None)
            if src_i is None or not 0 <= src_i < len(mt):
                raise ImportError_('%s: no motion %r to copy from' % (tgt.name, src))
        for f in files.values():
            sh = mt[src_i] if src_i is not None else 0
            f.scripts[h] = copy.deepcopy(f.scripts[sh]) if sh and sh in f.scripts else [acmd.Command(acmd.END)]
        ve = list(vents[src_i]) if src_i is not None else [0] * 6
        if it.get('loop') is not None:
            ve[1] = 6 if it['loop'] else (ve[1] if ve[1] != 6 else 0)
        r = {'name': name, 'anim': anim[:-4], 'hash': PAC.anim_hash(anim), 'index': index, 'flags_from': src_i,
             'part_hashes': part_hashes, 'vl': ve}
        if old is None:
            mt.append(h)
            vents.append(ve)
            recs.append(r)
            by_name[name] = r
            known.add(h)
            added.append(r)
        else:
            vents[index] = ve
            old.update(r)
            replaced.append(old)
    pac.save(pac_path)
    open(mt_path, 'wb').write(struct.pack('>%dI' % len(mt), *mt))
    open(vl_path, 'wb').write(vl_with(vld, vents))
    for f, a in files.items():
        a.save(os.path.join(bdir, f))
    for r in added + replaced:
        log('%s: motion 0x%X %s: %s (motion.mtable, the four scripts %s, vl group 1 %s)' % (
            tgt.name, r['index'], r['name'], r['anim'] + '.omo',
            'copied from motion 0x%X' % r['flags_from'] if r['flags_from'] is not None else 'empty', r['vl']))
    write_names(out_dir, '// ---- %s: imported motions' % tgt.name,
                [r['name'] for r in recs] + ['%s -> body/%s.omo' % (r['name'], r['anim']) for r in recs])
    return recs


def _part_tag(ppac, prefix):
    for n in ppac.names():
        if n.startswith(prefix):
            m = re.match(r'^(\w+?)[A-Z]\d\d', n[len(prefix):])
            if m:
                return m.group(1)
    return None


# ---------------------------------------------------------------- effects
def bank_paths(root, folder):
    """(efc, ptcl) of an effect bank folder (<root>/effect/<folder>/<folder>.010d0000.*)"""
    d = os.path.join(root, 'effect', folder)
    return os.path.join(d, folder + '.010d0000.efc'), os.path.join(d, folder + '.010d0000.ptcl')


def list_effects(efc_path, ptcl_path):
    """[(entry, set name or '', model name or '', flags)] of a bank"""
    import efc as EFC
    import ptcl as PT
    e = EFC.Efc(open(efc_path, 'rb').read())
    p = PT.Ptcl(open(ptcl_path, 'rb').read()) if os.path.exists(ptcl_path) else None
    out = []
    for i, (fl, st, mi, _mf, _mc) in enumerate(e.entries):
        out.append((i, p.set_name(st - 1) if p and st else '', e.models[mi - 1] if mi else '', fl))
    return out


def copy_set(dst, src, si, new_name):
    """src's emitter set si copied into dst under new_name, complete: every emitter with its shaders (its own and its
    child's), shader parameters, key animations, textures (its slots and its child's) and mesh. Returns the new set's
    index."""
    import ptcl as PT
    shaders, prims, texs = {}, {}, {}
    ems, names = [], []

    def tex(fmt, size, pos):
        if (pos, size) not in texs:
            data = src.tex[pos:pos + size]
            at = PT.align(len(dst.tex), PT.GX2_ALIGN.get(PT.EFT_GX2.get(fmt, 0x33), 0x2000))
            dst.tex += bytes(at - len(dst.tex)) + data
            texs[(pos, size)] = at
        return texs[(pos, size)]
    for k, e in enumerate(src.sets[si]['emitters']):
        if e['data'] is None:
            continue
        s = src.emitter_bytes(si, k)
        em = bytearray(s)
        for o in PT.Ptcl.shader_slots(s):
            i = PT.be32(s, o)
            if i not in shaders:
                shaders[i] = dst.import_shader(src, i)
            struct.pack_into('>I', em, o, shaders[i])
        size, pos = PT.be32(s, 0x2EC), PT.be32(s, 0x2F0)
        if size:
            at = PT.align(len(dst.sparam), 4)
            dst.sparam += bytes(at - len(dst.sparam)) + src.sparam[pos:pos + size]
            struct.pack_into('>I', em, 0x2F0, at)
        anims = src.key_anims(s)
        struct.pack_into('>II', em, 0x2CC, 0, 0)
        if anims:
            dst.set_key_anims(em, anims)
        offs = [PT.TEXRES + PT.TEXRES_SIZE * j for j in range(PT.TEX_SLOTS)]
        if PT.Ptcl.has_child(s):
            offs.append(PT.CHILD_TEXRES)
        for o in offs:
            fmt, tsize, tpos = struct.unpack_from('>III', s, o + 0x2C)
            if tsize:
                struct.pack_into('>I', em, o + 0x34, tex(fmt, tsize, tpos))
        pi = struct.unpack_from('>i', s, 0x2DC)[0]
        if pi >= 0:
            if pi not in prims:
                prims[pi] = dst.add_primitive(*src.primitive(pi))
            struct.pack_into('>i', em, 0x2DC, prims[pi])
        ems.append(em)
        names.append(src.emitter_name(s))
    dst.dirty_layout = True
    return dst.new_set(new_name, ems, names)


def import_effects(tgt, items, reg, out_dir, log=print):
    """items: [{'efc': path, 'ptcl': path, 'entry': n, 'name': the new set's name (default: the source set's,
    made unique), 'models': folder of the source bank's effect models}]. Returns [(name, effect id)]."""
    import efc as EFC
    import ptcl as PT
    recs = imports(reg).setdefault('effects', {}).setdefault(tgt.name, [])
    folder = tgt.name
    efc_rel = os.path.join('fighter', tgt.name, 'effect', folder, folder + '.010d0000.efc')
    ptcl_rel = efc_rel[:-4] + '.ptcl'
    efc_p, ptcl_p = tgt.writable(efc_rel), tgt.writable(ptcl_rel)
    if not efc_p or not ptcl_p:
        raise ImportError_('%s: no effect bank effect/%s/%s.010d0000.efc / .ptcl in the data folder'
                           % (tgt.name, folder, folder))
    e = EFC.Efc(open(efc_p, 'rb').read())
    p = PT.Ptcl(open(ptcl_p, 'rb').read())
    names = {p.set_name(i) for i in range(len(p.sets))}
    out = []
    by_key = {(r['source'], r['entry']): r for r in recs}
    srcs = {}
    for it in items:
        key = (os.path.abspath(it['efc']), it['entry'])
        se = srcs.get(key[0])
        if se is None:
            se = srcs[key[0]] = (EFC.Efc(open(it['efc'], 'rb').read()),
                                 PT.Ptcl(open(it['ptcl'], 'rb').read()) if os.path.exists(it['ptcl']) else None)
        sefc, sptcl = se
        if not 0 <= it['entry'] < len(sefc.entries):
            raise ImportError_('%s has no entry %d (%d entries)' % (it['efc'], it['entry'], len(sefc.entries)))
        old = by_key.get((_src_key(it), it['entry']))
        if old:
            out.append((old['name'], old['id']))
            log('%s: effect %s already imported: id 0x%08X' % (tgt.name, old['name'], old['id']))
            continue
        fl, st, mi, mf, mc = sefc.entries[it['entry']]
        set_idx = 0
        name = it.get('name') or (sptcl.set_name(st - 1) if st else 'Imported%d' % it['entry'])
        if st:
            if sptcl is None:
                raise ImportError_('%s: entry %d has an emitter set but there is no .ptcl' % (it['efc'], it['entry']))
            base, n = name, 2
            while name in names:
                name, n = '%s_%d' % (base, n), n + 1
            set_idx = copy_set(p, sptcl, st - 1, name) + 1
            names.add(name)
        model = None
        if mi:
            model = sefc.models[mi - 1]
            sdir = os.path.join(it.get('models') or os.path.join(os.path.dirname(it['efc']), 'model'), model)
            ddir = os.path.join(os.path.dirname(efc_p), 'model', model)
            in_data = os.path.isdir(os.path.join(tgt.data, os.path.relpath(ddir, tgt.pkg)))
            if os.path.isdir(sdir) and not os.path.isdir(ddir) and not in_data:
                shutil.copytree(sdir, ddir)
            elif not os.path.isdir(sdir) and not in_data:
                log('%s: effect model folder %s not found next to %s: the entry names it, the files are missing'
                    % (tgt.name, model, it['efc']))
        idx = e.add(set_idx, model, fl)
        if mc:
            first = len(e.meshes) + 1
            e.meshes += [list(x) for x in sefc.meshes[mf - 1:mf - 1 + mc]]
            e.mesh_names += sefc.mesh_names[mf - 1:mf - 1 + mc]
            e.entries[idx][3], e.entries[idx][4] = first, mc
        eid = (3 << 24) | (tgt.kind << 16) | idx
        r = {'name': name, 'id': eid, 'entry': it['entry'], 'source': _src_key(it), 'model': model}
        recs.append(r)
        out.append((name, eid))
        log('%s: effect %s (from %s entry %d) -> entry %d, effect id 0x%08X' % (
            tgt.name, name, os.path.basename(it['efc']), it['entry'], idx, eid))
    errs = p.validate()
    if errs:
        raise ImportError_('%s: the effect bank does not validate after the import: %s' % (tgt.name, '; '.join(errs[:3])))
    open(ptcl_p, 'wb').write(p.build())
    open(efc_p, 'wb').write(e.build())
    return out


def _src_key(it):
    return os.path.basename(it['efc'])


# ---------------------------------------------------------------- sounds (Sm4shCommand's Sound Adder, ported)
EMPTY_STUB = bytes([0, 0, 0, 0, 1, 0, 0, 0, 0xFF, 0, 0, 0])
MAX_LABELS = 0x10000


def _entry_info(e):
    """(name, data block offset) of a TONE entry, or None for a stub"""
    if len(e) < 0x10:
        return None
    q = ((0x0D + e[0x0C] + 3) & ~3) + 4
    if q + 4 > len(e) or struct.unpack('<I', e[q:q + 4])[0] != 8:
        return None
    return e[0x0D:0x0D + e[0x0C] - 1].decode('latin1'), q


def _template(bank, channels):
    """the one-shot a new tone's entry is copied from (Sm4shCommand's SoundAdder.Template)"""
    shots = []
    for i, e in enumerate(bank.raw):
        info = _entry_info(e)
        if not info:
            continue
        name, q = info
        off, size = struct.unpack('<II', e[q + 4:q + 12])
        blob = bank.pack[off:off + 4]
        if blob != b'IDSP' or len(e) < q + 0x30:
            continue
        rate, ch, n, _ls, _le, loop = struct.unpack('<6I', e[-0x20:-0x08])
        if loop:
            continue
        shots.append((name, ch, e))

    def pick(ts):
        return next((t for t in ts if t[0].lower().endswith('_special_l01')), ts[0] if ts else None)
    if channels == 2:
        st = pick([t for t in shots if t[1] == 2])
        if st:
            return st[2]
    return (pick([t for t in shots if t[1] == 1]) or pick(shots) or (None, None, None))[2]


def _same_tone(entries, pack, idx, blob, volume, loop):
    """whether TONE entry idx already plays blob at this volume / loop setting"""
    if idx >= len(entries):
        return False
    info = _entry_info(entries[idx])
    if not info:
        return False
    e, q = entries[idx], info[1]
    off, size, vol = struct.unpack('<IIf', e[q + 4:q + 16])
    flag = struct.unpack('<I', e[-0x0C:-0x08])[0]
    return bytes(pack[off:off + size]) == bytes(blob) and abs(vol - volume) < 1e-6 and bool(flag) == bool(loop)


def make_entry(template, name, pack_off, size, volume, rate, channels, samples, loop):
    """Sm4shCommand's SoundAdder.MakeEntry: the template's head and data block with the name, PACK offset / size,
    volume and the tail (rate, channels, samples, loop start / end / flag)"""
    _n, q = _entry_info(template)
    nm = name.encode('ascii') + b'\0'
    head = 0x0D + len(nm)
    q2 = ((head + 3) & ~3) + 4
    o = bytearray(q2 + len(template) - q)
    o[0:0x0C] = template[0:0x0C]
    o[0x0C] = len(nm)
    o[0x0D:0x0D + len(nm)] = nm
    o[q2 - 4:q2] = template[q - 4:q]
    o[q2:] = template[q:]
    struct.pack_into('<IIf', o, q2 + 4, pack_off, size, volume)
    t = len(o) - 0x20
    struct.pack_into('<6I', o, t, rate, channels, samples, 0, samples - 1 if loop else 0, 1 if loop else 0)
    return bytes(o)


def bank_build(bank, entries, pack):
    """the bank's bytes with these TONE entries and this PACK; JUNK sized so PACK's body starts at a multiple of 0x10
    (Sm4shCommand's Nus3Bank.Build(tones, pack, alignPack))"""
    from . import audio as AU
    secs = [list(s) for s in bank.secs]
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
    names = [s[0] for s in secs]
    if b'JUNK' in names and names.index(b'JUNK') + 1 < len(names) and names[names.index(b'JUNK') + 1] == b'PACK':
        j = names.index(b'JUNK')
        at = 24 + 8 * len(secs) + sum(8 + len(secs[i][1]) for i in range(j))
        size = len(secs[j][1])
        if (at + 8 + size + 8) % 16 or size < 4 or size % 4 or any(secs[j][1]):
            size = 4
            while (at + 8 + size + 8) % 16:
                size += 4
            secs[j][1] = bytes(size)
    return AU.build(secs)


def prepare_audio(path, trim=True, trim_db=-45.0, normalize=True, loop=False):
    """(IDSP bytes, channels, samples) of a WAV (Sm4shCommand's Sound Adder steps: 48 kHz, leading / trailing silence
    under trim_db dBFS trimmed, peak normalised to -0.5 dBFS, DSP-ADPCM mono or stereo) or of an IDSP file as it is"""
    import numpy as np
    from . import audio as AU
    d = open(path, 'rb').read()
    if d[:4] == b'IDSP':
        ch, _rate, n = struct.unpack('>3I', d[8:20])
        return d, ch, n
    with open(path, 'rb') as f:
        head = f.read(64)
    ch = struct.unpack('<H', head[22:24])[0] if head[:4] == b'RIFF' else 1
    ch = 2 if ch >= 2 else 1
    pcm = AU.read_wav(path, AU.RATE, ch)
    arr = np.array([pcm] if ch == 1 else pcm, dtype=np.float64)
    if trim:
        thr = 32768.0 * 10 ** (trim_db / 20)
        loud = np.nonzero(np.abs(arr).max(0) > thr)[0]
        if not len(loud):
            raise ImportError_('%s: nothing above %g dBFS (all silence?)' % (path, trim_db))
        arr = arr[:, loud[0]:loud[-1] + 1]
    if normalize and np.abs(arr).max() > 0:
        arr = arr * (32767 * 10 ** (-0.5 / 20) / np.abs(arr).max())
    arr = np.clip(np.round(arr), -32768, 32767).astype(int)
    chans = [list(map(int, c)) for c in arr]
    blob = AU.idsp_encode(chans[0] if ch == 1 else chans, AU.RATE, loop)
    return blob, ch, arr.shape[1]


def bank_kind(fname, cap):
    f = fname[:-len('.nus3bank')]
    m = re.match(r'^(snd_(?:se|vc)_%s(?:_common|_ouen)?)(?:_c(\d\d))?$' % re.escape(cap), f)
    return (m.group(1), m.group(2)) if m else (f, None)


def import_sounds(tgt, items, reg, out_dir, log=print, bank='se', costumes=True):
    """items: [{'file': WAV / IDSP path, 'name': tone name (default <bank name>_<file name>), 'alias': text,
    'volume': dB, 'loop': bool, 'trim': bool, 'normalize': bool}]; bank: 'se' / 'vc' / a bank file name. Returns
    [(tone name, sound id)]."""
    from . import audio as AU
    from . import sound as SND
    recs = imports(reg).setdefault('sounds', {}).setdefault(tgt.name, [])
    sdir_rel = tgt.rel('sound')
    fname = bank if bank.endswith('.nus3bank') else 'snd_%s_%s.nus3bank' % (bank, tgt.cap)
    main_p = tgt.writable(os.path.join(sdir_rel, fname))
    if not main_p:
        raise ImportError_('%s: no sound/%s in the data folder' % (tgt.name, fname))
    tp = tgt.writable(os.path.join('sound', 'config', 'soundlabeltable.bin'))
    if not tp:
        raise ImportError_('no sound/config/soundlabeltable.bin in the data folder')
    table = SND.Table(open(tp, 'rb').read())
    main = AU.Bank(open(main_p, 'rb').read())
    bname, bid = main.binf()
    row = table.row_of(bid)
    if row is None:
        raise ImportError_('%s: its BINF id %d has no row in soundlabeltable.bin: the game can\'t play it' % (fname, bid))
    kind, _c = bank_kind(fname, tgt.cap)
    banks = [(fname, main_p, main)]
    if costumes:
        for f in sorted(os.listdir(os.path.dirname(main_p)) + (os.listdir(os.path.join(tgt.data, sdir_rel))
                                                                if os.path.isdir(os.path.join(tgt.data, sdir_rel)) else [])):
            if f == fname or not f.endswith('.nus3bank') or any(f == b[0] for b in banks):
                continue
            k, c = bank_kind(f, tgt.cap)
            if k == kind and c:
                p = tgt.writable(os.path.join(sdir_rel, f))
                b = AU.Bank(open(p, 'rb').read())
                if table.row_of(b.binf()[1]) in (row, None):
                    banks.append((f, p, b))
    labels = table.tones(row)
    used = {r << 16 | lab for r, rr in enumerate(table.rows) for lab in range(rr[1])}
    tone_names = {(_entry_info(e) or ('',))[0] for _f, _p, b in banks for e in b.raw}
    by_name = {r['name']: r for r in recs if r.get('bank') == fname}
    first = max(len(b.raw) for _f, _p, b in banks)
    pending = []
    out = []
    for it in items:
        stem = re.sub(r'[^A-Za-z0-9_]', '_', os.path.splitext(os.path.basename(it['file']))[0]).strip('_') or 'New'
        name = it.get('name') or '%s_%s' % (bname, stem)
        if not re.match(r'^[A-Za-z0-9_]{1,254}$', name):
            raise ImportError_('%s: tone name %r: letters, digits and _ only' % (it['file'], name))
        blob, ch, n = prepare_audio(it['file'], it.get('trim', True), it.get('trim_db', -45.0),
                                    it.get('normalize', True), bool(it.get('loop')))
        old = by_name.get(name)
        if old is None and name in tone_names:
            raise ImportError_('%s: another tone is named %s' % (fname, name))
        pending.append((it, name, blob, ch, n, old))
    if len([1 for x in pending if x[5] is None]) > MAX_LABELS - len(labels):
        raise ImportError_('row 0x%X is full (%d labels)' % (row, len(labels)))
    k_new = 0
    new_banks = {}
    for f, p, b in banks:
        entries = list(b.raw)
        pack = bytearray(b.pack)
        stub = next((e for e in entries if len(e) == 12), EMPTY_STUB)
        while len(entries) < first:
            entries.append(stub)
        new_banks[f] = (p, b, entries, pack)
    for it, name, blob, ch, n, old in pending:
        vol = float(it.get('volume', 0.0))
        loop = bool(it.get('loop'))
        if old is not None:
            idx = old['tone']
            if all(_same_tone(entries, pack, idx, blob, vol, loop) for _p, _b, entries, pack in new_banks.values()):
                out.append((name, old['id']))          # already there as it would be written (a rebuild): unchanged
                old['alias'] = it.get('alias') or old.get('alias') or name
                continue
        else:
            idx = first + k_new
            k_new += 1
        for f, (p, b, entries, pack) in new_banks.items():
            pack.extend(bytes(-len(pack) % 16))
            off = len(pack)
            pack.extend(blob)
            tpl = _template(b, ch) or _template(main, ch)
            if tpl is None:
                raise ImportError_('%s has no one-shot tone to copy a TONE entry from' % f)
            e = make_entry(tpl, name, off, len(blob), vol, AU.RATE, ch, n, loop)
            if idx < len(entries):
                entries[idx] = e
            else:
                entries.append(e)
        if old is None:
            lab = len(labels)
            labels.append(idx)
            sid = row << 16 | lab
            assert sid not in used, 'sound id 0x%08X in use' % sid
            used.add(sid)
            r = {'name': name, 'id': sid, 'bank': fname, 'tone': idx, 'alias': it.get('alias') or name}
            recs.append(r)
        else:
            r = old
            r['alias'] = it.get('alias') or r.get('alias') or name
        out.append((name, r['id']))
        log('%s: sound %s (%s, %s, %.2f s) -> %s tone %d, label %d of row 0x%X: id 0x%08X' % (
            tgt.name, name, os.path.basename(it['file']), 'stereo' if ch == 2 else 'mono', n / AU.RATE, fname, r['tone'],
            r['id'] & 0xFFFF, row, r['id']))
    for f, (p, b, entries, pack) in new_banks.items():
        pack.extend(bytes(-len(pack) % 16))
        data = bank_build(b, entries, pack)
        back = AU.Bank(data)
        for name, sid in out:
            r = next(x for x in recs if x['name'] == name and x['bank'] == fname)
            info = _entry_info(back.raw[r['tone']])
            assert info and info[0] == name, '%s: tone %d does not read back as %s' % (f, r['tone'], name)
        open(p, 'wb').write(data)
    table.set_row(row, labels)
    open(tp, 'wb').write(table.data())
    write_aliases(out_dir, tgt.name, {r['id']: r.get('alias') or r['name'] for r in recs})
    return out


def write_aliases(out_dir, fighter, ids):
    """Sm4shCommand's Aliases/sounds/<fighter>.txt (its Sound Effect Viewer's format), merged with the file's own"""
    path = os.path.join(out_dir, ALIASES_DIR, re.sub(r'[^a-z0-9_-]', '', fighter.lower()) + '.txt')
    have = {}
    if os.path.exists(path):
        for ln in open(path, encoding='utf-8'):
            ln = ln.strip()
            if not ln or ln.startswith('#') or ln.startswith('//') or '=' not in ln:
                continue
            k, v = ln.split('=', 1)
            try:
                have[int(k.strip(), 0)] = v.strip()
            except ValueError:
                pass
    have.update(ids)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = ['# Sound aliases for %s: Sm4shCommand\'s Sound Effect Viewer (Tools > Sound Effect Viewer) writes this file'
             % fighter,
             '# from its Alias column; you can edit it too. One per line: sound id = your name for it. Labels only: '
             'scripts keep',
             '# the number, the editor\'s tooltip on the id shows the name.']
    lines += ['0x%08X = %s' % (k, v) for k, v in sorted(have.items())]
    open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    return path


# ---------------------------------------------------------------- the session's entry points
WHATS = ('motion', 'effect', 'sound', 'article')


def effect_source(item, pkg, data):
    """an effect item's (efc, ptcl): the files given, or a fighter's own bank ('source': its folder name)"""
    if item.get('efc'):
        efc = item['efc']
        return efc, item.get('ptcl') or efc[:-4] + '.ptcl'
    src = item.get('source')
    for root in (os.path.join(pkg, 'fighter', src), os.path.join(data, 'fighter', src)):
        efc, ptcl = bank_paths(root, src)
        if os.path.exists(efc):
            return efc, ptcl
    raise ImportError_('no effect bank fighter/%s/effect/%s/ in the package or the data folder' % (src, src))


def preview(items, reg, pkg, data):
    """a copy of reg with provisional records of the items' motions and articles (what the executable would get), for
    a plan: the motions numbered from the target's motion count, the articles after the recorded ones"""
    import acmd
    reg = copy.deepcopy(reg)
    imp = imports(reg)
    for it in items:
        try:
            tgt = Target(reg, it.get('target') or it.get('owner'), pkg, data)
        except ImportError_:
            continue
        if it.get('what') == 'motion':
            recs = imp.setdefault('motions', {}).setdefault(tgt.name, [])
            if any(r['name'] == it.get('name') for r in recs):
                continue
            mt = tgt.find(tgt.rel('script', 'animcmd', 'body', 'motion.mtable'))
            if not mt:
                continue
            n = os.path.getsize(mt) // 4 + len([1 for r in recs if r.get('preview')])
            recs.append({'name': it['name'], 'anim': '', 'hash': 0, 'index': n, 'flags_from': None, 'part_hashes': {},
                         'vl': [0] * 6, 'preview': True})
        elif it.get('what') == 'article':
            recs = imp.setdefault('articles', [])
            if not any(a['owner'] == tgt.name and a['name'] == it.get('name') for a in recs):
                recs.append({'owner': tgt.name, 'name': it.get('name'), 'source_owner': it.get('source_owner'),
                             'source': it.get('source'), 'max': int(it.get('max') or 1), 'article_id': -1})
    for k in list(imp):
        if not imp[k]:
            del imp[k]
    _ = acmd
    return reg


def plan(items, reg, pkg, data, exe=None):
    """(errors, file list) of the import items, without writing"""
    errors, files = [], []
    seen = set()
    for it in items:
        what = it.get('what')
        if what not in WHATS:
            errors.append('import: unknown kind %r (%s)' % (what, ', '.join(WHATS)))
            continue
        try:
            tgt = Target(reg, it.get('target') or it.get('owner'), pkg, data)
        except ImportError_ as e:
            errors.append('import %s: %s' % (what, e))
            continue
        try:
            if what == 'motion':
                if not NAME_RX.match(it.get('name') or ''):
                    raise ImportError_('motion name %r: a letter, then letters / digits / _' % it.get('name'))
                if not os.path.exists(it.get('omo') or ''):
                    raise ImportError_('no animation file %r' % it.get('omo'))
                if (tgt.name, 'motion', it['name'].lower()) in seen:
                    raise ImportError_('motion %s twice' % it['name'])
                seen.add((tgt.name, 'motion', it['name'].lower()))
                files.append('fighter/%s/motion/body/main.pac, script/animcmd/body/ (motion.mtable + the four .bin), '
                             'param/fighter/fighter_param_vl_%s.bin: motion %s' % (tgt.name, tgt.name, it['name']))
            elif what == 'effect':
                efc, _ptcl = effect_source(it, pkg, data)
                if not os.path.exists(efc):
                    raise ImportError_('no effect file %s' % efc)
                files.append('fighter/%s/effect/%s/ (.ptcl / .efc): entry %s of %s' % (
                    tgt.name, tgt.name, it.get('entry'), os.path.basename(efc)))
            elif what == 'sound':
                if not os.path.exists(it.get('file') or ''):
                    raise ImportError_('no sound file %r' % it.get('file'))
                files.append('fighter/%s/sound/%s (+ costume banks), sound/config/soundlabeltable.bin: %s' % (
                    tgt.name, it.get('bank', 'se'), os.path.basename(it['file'])))
            elif what == 'article':
                from . import articles as A
                files += A.plan_files(it, tgt, reg, pkg, data, exe)
        except ImportError_ as e:
            errors.append('import %s into %s: %s' % (what, tgt.name, e))
        except Exception as e:                      # noqa: BLE001 (a file the readers refuse)
            errors.append('import %s into %s: %s' % (what, tgt.name, e))
    return errors, files


def run(items, reg, pkg, data, out_dir, log=print, exe=None):
    """do the import items (in order, grouped by kind and target); returns {'motions': ..., 'effects': ...,
    'sounds': ..., 'articles': ...} of what each got"""
    out = {'motions': [], 'effects': [], 'sounds': [], 'articles': []}
    groups = []
    for it in items:
        key = (it['what'], it.get('target') or it.get('owner'), it.get('bank', 'se') if it['what'] == 'sound' else None)
        if groups and groups[-1][0] == key:
            groups[-1][1].append(it)
        else:
            groups.append((key, [it]))
    for (what, target, bank), its in groups:
        tgt = Target(reg, target, pkg, data)
        if what == 'motion':
            recs = import_motions(tgt, its, reg, out_dir, log)
            names = {i['name'] for i in its}
            out['motions'] += [(tgt.name, r['name'], r['index']) for r in recs if r['name'] in names]
        elif what == 'effect':
            src = []
            for i in its:
                efc, ptcl = effect_source(i, pkg, data)
                src.append(dict(i, efc=efc, ptcl=ptcl))
            out['effects'] += [(tgt.name, n, e) for n, e in import_effects(tgt, src, reg, out_dir, log)]
        elif what == 'sound':
            out['sounds'] += [(tgt.name, n, i) for n, i in import_sounds(tgt, its, reg, out_dir, log, bank=bank)]
        elif what == 'article':
            from . import articles as A
            out['articles'] += A.import_articles(tgt, its, reg, pkg, data, out_dir, log, exe)
    return out
