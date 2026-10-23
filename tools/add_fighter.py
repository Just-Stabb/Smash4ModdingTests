#!/usr/bin/env python3
"""The data files for a new fighter kind (kind >= 0x41, docs/kind-expansion.md), copied from a base
fighter: every param / UI database row, the names, the portraits, and (--folder) the fighter folder.
The executable side (name tables, switches, bounds, per-kind arrays) is tools/kind_expand.py, driven
by the same "extra kinds" record (tools/extra_kinds.json).

  python3 tools/add_fighter.py --param PARAM_DIR --ui UI_DIR --out OUT_DIR
          (--kinds tools/extra_kinds.json [--only NAME ...] | --kind 0x41 --name supamario
           --cap Supamario --base mario [--ui-id 59] [--ui-name Supamario] [--title TEXT])
          [--msbt FILE] [--no-portraits]
  python3 tools/add_fighter.py ... --folder BASE_DIR OUT_DIR [--model DIR] [--articles]
          [--keep-effect-ids]

PARAM_DIR  data/param of the base game (vanilla: every new row is a copy of the base's vanilla row).
           --param can be repeated: each file is read from the first folder that has it, e.g.
           --param PACK/param --param VANILLA/param to add the rows to a pack's own edited files
           (the copied base row is then the pack's)
UI_DIR     data/ui (message/melee.msbt; replace/chr/<set>/<set>_<Name>_NN.nut and
           replace/append/chr/... when present)
OUT_DIR    gets only the changed / new files, laid out like data/:
             param/fighter/fighter_param.bin              + entry, word 0 = kind
             param/fighter/fighter_param_vl_<name>.bin    = the base's vl file
             param/ai/fighter_ai_fighter_param.bin        + entry, value 0 = kind
             param/ai/fighter_ai_nfp_learning_param.bin   + entry at position kind (amiibo)
             param/simple/simple_character_db_cafe.bin    + entry, value 0 = kind (Classic)
             param/sound/audience_ouen_param.bin          + the base's rows with the kind (cheers)
             param/ui/ui_character_db.bin                 + entry at position = character id
             param/ui/ui_layout_db.bin                    + the base's rows with the id (portrait layout)
             param/ui/ui_skill_db.bin                     + entry at position id (custom moves)
             param/ui/ui_sound_call_voice_db.bin          + entry at position id - 1 (announcer call)
             ui/message/melee.msbt                        + MmelChara{N,C,A,R}_NN_<UiName>
             ui/replace[/append]/chr/<set>/<set>_<UiName>_NN.nut   the base's, with new texture IDs
--folder BASE_DIR OUT_DIR
           BASE_DIR = the base's data/fighter/<base>/ folder; writes OUT_DIR/fighter/<name>/ with
           every file the executable finds by the fighter's name renamed (FOLDER_PATHS below), the
           ACMD effect IDs moved to the new kind (0x3KK / 0x4KK, as Dr. Mario's 0x324 / Lucina's
           0x325 scripts do; --keep-effect-ids keeps the base's), and no article folders (weapons
           load from their owner's folder, fighter/<base>/...; --articles copies them anyway), but
           those of the record's "weapons" (its own weapon kinds, tools/weapon_expand.py): copied
           with their names, their ACMD's effect IDs moved like the body's.
           --model DIR: take model/ from another copy of the base folder (DIR/model or DIR itself).

Every edited param file is re-read with tools/s4param.py and checked: with the added rows taken
out it rebuilds byte-identical to the input. melee.msbt: every old label keeps its text and the
file without the new labels rebuilds byte-identical. The vl file is the base's, byte for byte.

The record (one per kind in extra_kinds.json "kinds"; docs/kind-expansion-code.md 3.3):
  {"kind": "0x41", "name": "supamario", "cap": "Supamario", "base": "mario",
   "ui": {"id": 59, "name": "Supamario", "title": "Supamario", "series": 9, "costumes": 8,
          "sort": [61, 61, 61]}}
ui.name is the UI name (portrait files, MmelChara labels; the executable's character-name table);
ui.title the displayed name (default ui.name); series / costumes / sort default to the base's
entry and to "after every fighter". Kinds must be consecutive from 0x41 and ids from 59 (both
are positional in some files); run all records in one call (--kinds) on the vanilla files.
"""
import argparse
import copy
import json
import os
import re
import shutil
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import msbt  # noqa: E402
import s4param  # noqa: E402
from add_stage import texture_ids, used_texture_ids  # noqa: E402
from fighter_param import KINDS  # noqa: E402

# character id -> UI name (the executable's table 0x1033BE68, ids 0-58)
UI_NAMES = ['Omakase', 'Miifighter', 'Miiswordsman', 'Miigunner', 'Mario', 'Donkey', 'Link', 'Samus', 'Yoshi',
            'Kirby', 'Fox', 'Pikachu', 'Luigi', 'Captain', 'Ness', 'Peach', 'Koopa', 'Zelda', 'Sheik', 'Marth',
            'Gamewatch', 'Ganon', 'Falco', 'Wario', 'Metaknight', 'Pit', 'Szerosuit', 'Pikmin', 'Diddy',
            'Dedede', 'Ike', 'Lucario', 'Robot', 'Toonlink', 'Lizardon', 'Sonic', 'Drmario', 'Rosetta',
            'Wiifit', 'Littlemac', 'Murabito', 'Palutena', 'Reflet', 'Duckhunt', 'KoopaJr', 'Shulk', 'Purin',
            'Lucina', 'Pitb', 'Gekkouga', 'Pacman', 'Rockman', 'Mewtwo', 'Ryu', 'Lucas', 'Roy', 'Cloud',
            'Bayonetta', 'Kamui']

# fighter kind -> Capitalised name (the executable's table 0x102FF588)
CAPS = ['MiiFighter', 'MiiSwordsman', 'MiiGunner', 'Mario', 'Donkey', 'Link', 'Samus', 'Yoshi', 'Kirby', 'Fox',
        'Pikachu', 'Luigi', 'Captain', 'Ness', 'Peach', 'Koopa', 'Zelda', 'Sheik', 'Marth', 'GameWatch', 'Ganon',
        'Falco', 'Wario', 'Metaknight', 'Pit', 'SZerosuit', 'Pikmin', 'Diddy', 'Dedede', 'Ike', 'Lucario',
        'Robot', 'Toonlink', 'Lizardon', 'Sonic', 'Purin', 'MarioD', 'Lucina', 'PitB', 'Rosetta', 'Wiifit',
        'Littlemac', 'Murabito', 'Palutena', 'Reflet', 'Duckhunt', 'KoopaJr', 'Shulk', 'Gekkouga', 'Pacman',
        'Rockman', 'Mewtwo', 'Ryu', 'Lucas', 'Roy', 'Cloud', 'Bayonetta', 'Kamui', 'KoopaG', 'Warioman',
        'LittlemacG', 'LucarioM', 'MiiEnemyF', 'MiiEnemyS', 'MiiEnemyG']

# Portrait sets (docs/new-fighter-slot.md "Names, portraits and text"): 0x0291673C / 0x029169A8 /
# 0x02916B44 build <set>/<set>_<UiName>_%02d under ui/replace/chr (ui/replace/append/chr first).
# chr_70 is only the Vault sound test's replace slot (optional; copied when the base has one).
# --ui must be the UI the user's game shows (their mod's art: a vanilla portrait in a modded
# character select shows as a misfit picture), unpacked from its packed files.
PORTRAIT_SETS = ['chr_00', 'chr_10', 'chr_11', 'chr_12', 'chr_13', 'chr_40', 'chr_70', 'chr_90',
                 'chrn_11', 'chrn_12', 'chrn_40', 'chrn_41', 'stock_90']
# New portraits get texture IDs (GIDX) from here, 0x100 per character id (id - 59); the game's
# UI uses 0x28000000-0x28006395, add_stage.py's stage icons 0x2800FF00+.
NEW_TEXTURE_IDS = 0x28010000

# Paths the executable builds with the fighter's names (docs/params/fighter_files.md section 1;
# strings in cross_f.rpx): %L = lowercase folder name, %C = Capitalised name. Everything else in the
# folder is found by listing (motion/*.pac, model files), by hash (.omo inside the packs) or by a
# name stored in another file (effect model folders named in the .efc), and keeps its name.
FOLDER_PATHS = [
    'fighter/%L/model/body/c%02d/ (l%02d/ for 8-player Smash)',
    'fighter/%L/motion/%s/ (body, bodyentry, bodyresult, bodyroutemap)',
    'fighter/%L/effect/%L/ (%L.%08x.efc / .ptcl inside)',
    'fighter/%L/effect/Fin%C/ (Fin%C.%08x.efc / .ptcl inside)',
    'fighter/%L/camera/final/ (only kinds 0x0C, 0x2D, 0x2F, 0x32, 0x38, 0x39)',
    'fighter/%L/script/msc/%L.mscsb',
    'fighter/%L/script/animcmd/body/',
    'fighter/%L/script/ai/',
    'fighter/%L/sound/snd_se_%C[_c%02d][_common[_c%02d]].nus3bank',
    'fighter/%L/sound/snd_vc_%C[_c%02d][_ouen].nus3bank',
    'fighter/%L/sound/soundseq_%C.sqb',
    'fighter/%L/sound/voiceanim_%C.vat',
    'fighter/%L/sound/snd_se_vc_Kirby_copy_%C.nus3bank (loaded only for kinds <= 0x39)',
    'param/fighter/fighter_param_vl_%L.bin',
    'weapons: fighter/<owner>/model|motion/<article>/, script/animcmd/weapon/<article>/, '
    'script/msc/<article>/<article>.mscsb, with the owner name from the weapon table (0x10418FF0)',
]


# ---------------------------------------------------------------- records
def num(v):
    return int(v, 0) if isinstance(v, str) else int(v)


def load_records(a):
    if a.kinds:
        spec = json.load(open(a.kinds))
        recs = spec['kinds'] if isinstance(spec, dict) else spec
        if a.only:
            recs = [r for r in recs if r['name'] in a.only]
        src = a.kinds
    else:
        if not (a.kind and a.name and a.base):
            raise SystemExit('give --kinds FILE, or --kind, --name and --base')
        recs = [{'kind': a.kind, 'name': a.name, 'cap': a.cap or a.name.capitalize(), 'base': a.base,
                 'ui': {'id': a.ui_id, 'name': a.ui_name, 'title': a.title}}]
        src = 'command line'
    out = []
    for r in recs:
        base = r['base']
        bkind = KINDS.index(base) if base in KINDS else num(base)
        ui = dict(r.get('ui') or {})
        rec = {'kind': num(r['kind']), 'name': r['name'], 'cap': r.get('cap') or r['name'].capitalize(),
               'base': KINDS[bkind], 'bkind': bkind, 'bcap': CAPS[bkind],
               'id': num(ui['id']) if ui.get('id') is not None else None}
        rec['ui_name'] = ui.get('name') or rec['cap']
        rec['title'] = ui.get('title') or rec['ui_name']
        for k in ('series', 'costumes', 'sort'):
            rec[k] = ui.get(k)
        # weapons of its own (tools/weapon_expand.py): {article: new weapon kind}
        # (a brand-new article, {"kind", "base", "max"}, has no base files to copy: left out here)
        rec['weapons'] = {art: num(wk) for art, wk in (r.get('weapons') or {}).items() if not isinstance(wk, dict)}
        out.append(rec)
    return out, src


# ---------------------------------------------------------------- param helpers
def group(items):
    gs = [it for it in items if isinstance(it, list) and it[0] == 'group']
    assert len(gs) == 1, 'expected one group, found %d' % len(gs)
    return gs[0]


def setv(e, i, v):
    e[i] = (e[i][0], v)


class ParamEdit:
    """one s4param file: parse, add entries, write, and check that the added entries are the only change"""

    def __init__(self, param_dirs, rel):
        self.rel = rel
        self.src = find_param(param_dirs, rel)
        self.data = open(self.src, 'rb').read()
        self.items = s4param.parse(self.data)
        assert s4param.build(self.items, self.data[:8]) == self.data, '%s: round trip differs' % rel
        self.g = group(self.items)
        self.added = []            # entry objects added (identity)
        self.notes = []

    def entries(self):
        return self.g[2]

    def insert(self, pos, e, note):
        self.g[2].insert(pos, e)
        self.g[1] = len(self.g[2])
        self.added.append(e)
        self.notes.append('%s at position %d' % (note, pos))

    def write(self, out_dir):
        new = s4param.build(self.items, self.data[:8])
        path = os.path.join(out_dir, 'param', self.rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(new)
        # check: re-read the written file; without the added entries it is the input, byte for byte
        items = s4param.parse(open(path, 'rb').read())
        g = group(items)
        keep = [e for e in g[2] if not any(e == x for x in self.added)]
        assert len(keep) == len(g[2]) - len(self.added), '%s: added entries not found once' % self.rel
        g[2] = keep
        g[1] = len(keep)
        assert s4param.build(items, new[:8]) == self.data, '%s: unchanged part differs' % self.rel
        return path, len(self.data), len(new)


def find_param(dirs, rel):
    for d in dirs:
        p = os.path.join(d, rel)
        if os.path.exists(p):
            return p
    raise SystemExit('%s: not in %s' % (rel, ', '.join(dirs)))


def entry_by_value0(pe, v):
    hits = [e for e in pe.entries() if e[0][1] == v]
    if not hits:
        raise SystemExit('%s: no entry with value 0 = %d' % (pe.rel, v))
    return hits


# ---------------------------------------------------------------- the data files
def edit_params(recs, a, log):
    P = a.param
    files = {}

    def pe(rel):
        if rel not in files:
            files[rel] = ParamEdit(P, rel)
        return files[rel]

    for r in recs:
        k, bk = r['kind'], r['bkind']

        # fighter_param.bin: entries are found by word 0 (the kind; the manager's kind map loop is
        # patched to cover the new kinds); append a copy of the base's.
        f = pe('fighter/fighter_param.bin')
        assert not [e for e in f.entries() if e[0][1] == k], 'fighter_param.bin already has kind 0x%X' % k
        e = copy.deepcopy(entry_by_value0(f, bk)[0])
        setv(e, 0, k)
        f.insert(len(f.entries()), e, 'kind 0x%X (copy of %s)' % (k, r['base']))

        # AI tuning: value 0 = kind
        f = pe('ai/fighter_ai_fighter_param.bin')
        e = copy.deepcopy(entry_by_value0(f, bk)[0])
        setv(e, 0, k)
        f.insert(len(f.entries()), e, 'kind 0x%X' % k)

        # amiibo learning: entry k must be kind k (indexed by position)
        f = pe('ai/fighter_ai_nfp_learning_param.bin')
        if len(f.entries()) != k:
            raise SystemExit('fighter_ai_nfp_learning_param.bin has %d entries; kind 0x%X must be entry %d '
                             '(kinds must be consecutive from 0x41)' % (len(f.entries()), k, k))
        assert f.entries()[bk][0][1] == bk
        e = copy.deepcopy(f.entries()[bk])
        setv(e, 0, k)
        f.insert(k, e, 'kind 0x%X' % k)

        # Classic mode: value 0 = kind (the file is not in kind order)
        f = pe('simple/simple_character_db_cafe.bin')
        e = copy.deepcopy(entry_by_value0(f, bk)[0])
        setv(e, 0, k)
        f.insert(len(f.entries()), e, 'kind 0x%X' % k)

        # crowd cheers: (kind, variant) rows, kinds 0-0x39 in order; the base's rows with the new kind
        f = pe('sound/audience_ouen_param.bin')
        for e in entry_by_value0(f, bk):
            e = copy.deepcopy(e)
            setv(e, 0, k)
            f.insert(len(f.entries()), e, 'kind 0x%X variant %d' % (k, e[1][1]))

        if r['id'] is None:
            log.append('kind 0x%X: no ui id, no UI rows' % k)
            continue
        cid = r['id']

        # ui_character_db: ids <= 0xC7 are found by position, so the entry goes at position id
        f = pe('ui/ui_character_db.bin')
        ents = f.entries()
        if not all(ents[i][0][1] == i for i in range(cid)) or ents[cid][0][1] < 200:
            raise SystemExit('ui_character_db.bin: positions 0-%d must be ids 0-%d and the next entry a '
                             'special id (>= 200); ids must be consecutive from 59' % (cid - 1, cid - 1))
        bid = [e for e in ents if e[0][1] < 200 and e[5][1] == 1 and e[6][1] == bk]
        assert len(bid) == 1, 'ui_character_db.bin: %d fighter entries with kind %d' % (len(bid), bk)
        base_e = bid[0]
        r['base_id'] = base_id = base_e[0][1]
        r['base_ui'] = UI_NAMES[base_id]
        e = copy.deepcopy(base_e)
        setv(e, 0, cid)
        setv(e, 2, 1)          # +0x05 shown
        setv(e, 5, 1)          # +0x0C is a fighter (kind -> id search)
        setv(e, 6, k)          # +0x10 kind
        setv(e, 9, 0)          # +0x1C Mii
        setv(e, 10, 0)         # +0x1D DLC (no DLC list, unlock index or content check)
        if r['series'] is not None:
            setv(e, 4, num(r['series']))
        if r['costumes'] is not None:
            setv(e, 7, num(r['costumes']))
        fighters = [x for x in ents if x[0][1] < 200]
        sort = r['sort'] or [max(x[13 + j][1] for x in fighters) + 1 for j in range(3)]
        for j in range(3):     # +0x20-+0x22 sort keys (s8)
            setv(e, 13 + j, num(sort[j]))
        f.insert(cid, e, 'id %d (copy of id %d %s; kind 0x%X, sort %s)' % (cid, base_id, r['base_ui'], k,
                                                                         '/'.join(str(e[13 + j][1]) for j in range(3))))
        r['costume_count'] = e[7][1]
        r['name_idx'] = sorted(set(e[21 + j][1] for j in range(e[7][1])))

        # ui_layout_db: (id, variant) rows; lookup = exact, else first with the id, else row 0 (random)
        f = pe('ui/ui_layout_db.bin')
        ents = f.entries()
        rows = [x for x in ents if x[0][1] == base_id]
        pos = max(i for i, x in enumerate(ents) if x[0][1] < 200) + 1
        for x in rows:
            x = copy.deepcopy(x)
            setv(x, 0, cid)
            f.insert(pos, x, 'id %d variant %d' % (cid, x[1][1]))
            pos += 1

        # ui_skill_db (custom moves), ids 0-58 by position
        f = pe('ui/ui_skill_db.bin')
        ents = f.entries()
        if len(ents) != cid or ents[base_id][0][1] != base_id:
            raise SystemExit('ui_skill_db.bin: %d entries; id %d must be the next' % (len(ents), cid))
        x = copy.deepcopy(ents[base_id])
        setv(x, 0, cid)
        f.insert(cid, x, 'id %d' % cid)

        # ui_sound_call_voice_db (announcer call), ids 1-58 at position id - 1
        f = pe('ui/ui_sound_call_voice_db.bin')
        ents = f.entries()
        if len(ents) != cid - 1 or ents[base_id - 1][0][1] != base_id:
            raise SystemExit('ui_sound_call_voice_db.bin: %d entries; id %d must be the next' % (len(ents), cid))
        x = copy.deepcopy(ents[base_id - 1])
        setv(x, 0, cid)
        f.insert(cid - 1, x, 'id %d (the base\'s call, narration 0x%08X)' % (cid, x[1][1]))

    out = []
    for rel, f in files.items():
        path, n0, n1 = f.write(a.out)
        out.append(path)
        log.append('param/%s: %s (%d -> %d bytes from %s; re-read, rest byte-identical)'
                   % (rel, '; '.join(f.notes), n0, n1, f.src))

    # vl file: the base's, byte for byte
    for r in recs:
        src = find_param(P, 'fighter/fighter_param_vl_%s.bin' % r['base'])
        dst = os.path.join(a.out, 'param', 'fighter', 'fighter_param_vl_%s.bin' % r['name'])
        shutil.copyfile(src, dst)
        assert open(src, 'rb').read() == open(dst, 'rb').read()
        log.append('param/fighter/fighter_param_vl_%s.bin: copy of %s (%d bytes)'
                   % (r['name'], src, os.path.getsize(dst)))
        out.append(dst)
    return out


def edit_msbt(recs, a, log):
    src = a.msbt or os.path.join(a.ui, 'message', 'melee.msbt')
    data = open(src, 'rb').read()
    m = msbt.Msbt(data)
    assert m.build() == data, 'melee.msbt: round trip differs'
    old = {lab: m.text(lab) for lab in m.labels}
    added = []
    for r in recs:
        if r['id'] is None:
            continue
        bn, nn = r['base_ui'], r['ui_name']
        pat = re.compile(r'^MmelChara([A-Z])_(\d\d)_%s(_.*)?$' % re.escape(bn))
        for lab in sorted(old):
            mm = pat.match(lab)
            if not mm:
                continue
            letter, idx, suffix = mm.group(1), mm.group(2), mm.group(3) or ''
            new = 'MmelChara%s_%s_%s%s' % (letter, idx, nn, suffix)
            if suffix.endswith('snd') or letter == 'A':
                text = old[lab]                # title, sound-test names: the base's
            elif letter in 'CR':
                text = r['title'].upper()
            else:
                text = r['title']
            assert new not in old, 'melee.msbt already has %s' % new
            m.set(new, text)
            added.append((new, text))
        if not any(l.startswith('MmelCharaN_01_%s' % nn) for l, _ in added):
            raise SystemExit('melee.msbt: no MmelCharaN_01_%s label for the base' % bn)
    new = m.build()
    dst = os.path.join(a.out, 'ui', 'message', 'melee.msbt')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(new)
    # check: every old label keeps its text, the new ones read back; without them the input
    chk = msbt.Msbt(open(dst, 'rb').read())
    assert all(chk.text(l) == t for l, t in old.items()), 'melee.msbt: an old label changed'
    assert all(chk.text(l) == t for l, t in added)
    for idx in sorted((chk.labels.pop(l) for l, _ in added), reverse=True):
        assert idx == len(chk.texts) - 1
        chk.texts.pop()
    assert chk.build() == data, 'melee.msbt: without the new labels it differs from the input'
    log.append('ui/message/melee.msbt (from %s): %s' % (src, ', '.join('%s = %r' % x for x in added)))
    return [dst]


def copy_portraits(recs, a, log):
    out = []
    used = used_texture_ids(a.ui)
    for r in recs:
        if r['id'] is None:
            continue
        tex = NEW_TEXTURE_IDS + 0x100 * (r['id'] - 59)
        found, missing = [], []
        for root in ('replace/chr', 'replace/append/chr'):
            for st in PORTRAIT_SETS:
                d = os.path.join(a.ui, root, st)
                files = sorted(f for f in os.listdir(d) if re.match(r'%s_%s(_\d\d)?\.nut$' % (st, re.escape(r['base_ui'])), f)) \
                    if os.path.isdir(d) else []
                for f in files:
                    data = open(os.path.join(d, f), 'rb').read()
                    if data[:2] == b'\x78\x9c':        # loose files in a built pack are compressed
                        data = zlib.decompress(data)
                    n = len(texture_ids(data))
                    ids = []
                    for _ in range(n):
                        while tex in used:
                            tex += 1
                        used.add(tex)
                        ids.append(tex)
                    data = bytearray(data)
                    for (off, _), t in zip(texture_ids(data), ids):
                        struct.pack_into('>I', data, off, t)
                    nf = f.replace('_%s' % r['base_ui'], '_%s' % r['ui_name'], 1)
                    dst = os.path.join(a.out, 'ui', root, st, nf)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    open(dst, 'wb').write(bytes(data))
                    out.append(dst)
                    found.append('%s/%s/%s (texture %s)' % (root, st, nf, ', '.join('0x%08X' % t for t in ids)))
        for st in PORTRAIT_SETS:
            if st != 'chr_70' and not any('/%s/' % st in x for x in found):
                missing.append(st)
        log.append('portraits for %s from %s: %d files%s' % (r['ui_name'], r['base_ui'], len(found),
                   (': ' + '; '.join(found)) if found else ''))
        if missing:
            log.append('  MISSING (no %s file of the base under %s/replace[/append]/chr): %s'
                       % (r['base_ui'], a.ui, ', '.join(missing)))
    return out


# ---------------------------------------------------------------- the fighter folder
def is_article(rel, base):
    p = rel.split('/')
    if p[0] in ('model', 'motion') and len(p) > 2:
        return not (p[1] == 'body' if p[0] == 'model' else p[1].startswith('body'))
    if p[:3] == ['script', 'animcmd', 'weapon']:
        return True
    if p[:2] == ['script', 'msc'] and len(p) > 3:
        return True
    return False


def article_of(rel):
    """the article a file of the fighter folder belongs to (None: the fighter's own)"""
    p = rel.split('/')
    if p[0] in ('model', 'motion') and len(p) > 2:
        return p[1]
    if p[:3] == ['script', 'animcmd', 'weapon'] and len(p) > 4:
        return p[3]
    if p[:2] == ['script', 'msc'] and len(p) > 3:
        return p[2]
    return None


def new_rel(rel, r):
    """the file's path in the new folder: names the executable builds with %L / %C"""
    b, bc, n, nc = r['base'], r['bcap'], r['name'], r['cap']
    p = rel.split('/')
    if p[0] == 'effect' and len(p) >= 2:
        if p[1] == b:
            p[1] = n
            if len(p) == 3 and p[2].startswith(b + '.'):
                p[2] = n + p[2][len(b):]
        elif p[1] == 'Fin' + bc:
            p[1] = 'Fin' + nc
            if len(p) == 3 and p[2].startswith('Fin' + bc + '.'):
                p[2] = 'Fin' + nc + p[2][len('Fin' + bc):]
    elif p[:2] == ['script', 'msc'] and len(p) == 3 and p[2] == b + '.mscsb':
        p[2] = n + '.mscsb'
    elif p[0] == 'sound' and len(p) == 2:
        p[1] = re.sub(r'^(snd_se_vc_Kirby_copy_|snd_se_|snd_vc_|soundseq_|voiceanim_)%s(?=[_.])' % re.escape(bc),
                      lambda m: m.group(1) + nc, p[1])
    return '/'.join(p)


def move_effect_ids(data, bk, k):
    """ACMD: effect IDs 0x3BB.... / 0x4BB.... (the base kind's own / Final Smash effects) -> 0x3KK / 0x4KK,
    in effect commands only. Returns (new data, count)."""
    import acmd
    f = acmd.ACMDFile.load_bytes(data) if hasattr(acmd.ACMDFile, 'load_bytes') else None
    if f is None:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as t:
            t.write(data)
        f = acmd.ACMDFile.load(t.name)
        os.unlink(t.name)
    assert f.encode() == data, 'ACMD round trip differs'
    n = 0
    for cmds in f.scripts.values():
        for c in cmds:
            if not re.search(r'graphic|effect', c.name, re.I):
                continue
            for i, p in enumerate(c.params):
                if c.kind(i) != 1 and isinstance(p, int) and (p >> 24) in (3, 4) and (p >> 16) & 0xFF == bk:
                    c.params[i] = (p & 0xFF00FFFF) | (k << 16)
                    n += 1
    new = f.encode()
    assert len(new) == len(data)
    # only those words changed
    diff = [i for i in range(0, len(data), 4) if data[i:i + 4] != new[i:i + 4]]
    assert len(diff) == n
    for i in diff:
        o, w = struct.unpack('>I', data[i:i + 4])[0], struct.unpack('>I', new[i:i + 4])[0]
        assert o ^ w == ((bk ^ k) << 16)
    return new, n


def copy_folder(recs, a, log):
    base_dir, out_root = a.folder
    if len(recs) != 1:
        raise SystemExit('--folder: one record at a time (use --only NAME)')
    r = recs[0]
    model_src = None
    if a.model:
        model_src = a.model if os.path.basename(os.path.normpath(a.model)) == 'model' else os.path.join(a.model, 'model')
    dst_dir = os.path.join(out_root, 'fighter', r['name'])
    if os.path.exists(dst_dir):
        raise SystemExit('%s exists; remove it first' % dst_dir)
    files = []
    for root, _dirs, fs in os.walk(base_dir):
        for f in fs:
            rel = os.path.relpath(os.path.join(root, f), base_dir).replace(os.sep, '/')
            if model_src and rel.startswith('model/'):
                continue
            files.append((rel, os.path.join(root, f)))
    if model_src:
        for root, _dirs, fs in os.walk(model_src):
            for f in fs:
                rel = 'model/' + os.path.relpath(os.path.join(root, f), model_src).replace(os.sep, '/')
                files.append((rel, os.path.join(root, f)))
    renamed, kept_named, skipped, effects = [], [], [], []
    count = size = 0
    for rel, src in sorted(files):
        own = is_article(rel, r['base']) and article_of(rel) in r['weapons']
        if is_article(rel, r['base']) and not a.articles and not own:
            skipped.append(rel)
            continue
        nrel = new_rel(rel, r)
        dst = os.path.join(dst_dir, nrel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        data = open(src, 'rb').read()
        # its own weapons' ACMD (weapon_expand.py's kinds) gets its effect banks too; the base's weapons
        # (copied with --articles but still the base's kinds) keep the base's
        if not a.keep_effect_ids and rel.endswith('.bin') and (rel.startswith('script/animcmd/body/') or own and
                                                                rel.startswith('script/animcmd/weapon/')):
            data2, n = move_effect_ids(data, r['bkind'], r['kind'])
            if n:
                effects.append('%s: %d effect IDs 0x3%02X/0x4%02X.... -> 0x3%02X/0x4%02X....'
                               % (rel, n, r['bkind'], r['bkind'], r['kind'], r['kind']))
            data = data2
        open(dst, 'wb').write(data)
        count += 1
        size += len(data)
        if nrel != rel:
            # one line per renamed folder, plus each file whose own name changed
            dold, dnew = os.path.dirname(rel), os.path.dirname(nrel)
            while dold != dnew and os.path.basename(dold) == os.path.basename(dnew):
                dold, dnew = os.path.dirname(dold), os.path.dirname(dnew)
            line = '%s/ -> %s/' % (dold, dnew) if dold != dnew else None
            if line and line not in renamed:
                renamed.append(line)
            if os.path.basename(rel) != os.path.basename(nrel):
                renamed.append('%s -> %s' % (rel, nrel))
        elif re.search(re.escape(r['base']), rel, re.I):
            kept_named.append(rel)
    arts = sorted(set('/'.join(x.split('/')[:3]) for x in skipped))
    log.append('fighter/%s/: %d files, %.1f MB, from %s%s' % (r['name'], count, size / 1e6, base_dir,
                                                             (' (model/ from %s)' % model_src) if model_src else ''))
    log.append('  renamed (paths the executable builds with the name):\n    ' + '\n    '.join(renamed))
    if kept_named:
        log.append('  kept their names (found by listing / hash / a name inside another file):\n    '
                   + '\n    '.join(kept_named))
    log.append('  effect IDs: ' + ('; '.join(effects) if effects else 'kept (--keep-effect-ids)' if a.keep_effect_ids else 'none'))
    if r['weapons']:
        log.append('  its own weapons (tools/weapon_expand.py; files under fighter/%s/, names kept): %s'
                   % (r['name'], ', '.join('%s 0x%X' % (art, wk) for art, wk in sorted(r['weapons'].items(),
                                                                                   key=lambda x: x[1]))))
        missing = [art for art in r['weapons'] if not any(article_of(rel) == art for rel, _s in files)]
        if missing:
            log.append('  MISSING article folders in the base: %s' % ', '.join(missing))
    if skipped:
        log.append('  article folders not copied (%d files; weapons load from fighter/%s/ by owner name): %s'
                   % (len(skipped), r['base'], ', '.join(arts)))
    return dst_dir


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--param', action='append', help='data/param (vanilla); repeat: first folder with the file wins')
    ap.add_argument('--ui', help='data/ui')
    ap.add_argument('--out', help='output root for the data files (laid out like data/)')
    ap.add_argument('--kinds', help='extra kinds JSON (tools/extra_kinds.json)')
    ap.add_argument('--only', nargs='*', help='records (by name) to use')
    ap.add_argument('--kind')
    ap.add_argument('--name')
    ap.add_argument('--cap')
    ap.add_argument('--base')
    ap.add_argument('--ui-id', type=lambda s: int(s, 0))
    ap.add_argument('--ui-name')
    ap.add_argument('--title')
    ap.add_argument('--msbt', help='melee.msbt to add the names to (default UI_DIR/message/melee.msbt); '
                                   'use the pack\'s current one when it already has other edits')
    ap.add_argument('--no-portraits', action='store_true')
    ap.add_argument('--folder', nargs=2, metavar=('BASE_DIR', 'OUT_DIR'))
    ap.add_argument('--model', help='with --folder: where model/ comes from')
    ap.add_argument('--articles', action='store_true', help='with --folder: copy article folders too')
    ap.add_argument('--keep-effect-ids', action='store_true', help='with --folder: keep the base kind\'s effect IDs')
    a = ap.parse_args()
    recs, src = load_records(a)
    log = ['records from %s: %s' % (src, ', '.join('%s/%s kind 0x%X id %s base %s' % (
        r['name'], r['cap'], r['kind'], r['id'], r['base']) for r in recs))]
    for r in recs:
        if r['kind'] < 0x41:
            raise SystemExit('kind 0x%X: new kinds start at 0x41' % r['kind'])
    if a.param:
        if not (a.ui and a.out):
            raise SystemExit('--param needs --ui and --out')
        edit_params(recs, a, log)
        edit_msbt(recs, a, log)
        if not a.no_portraits:
            copy_portraits(recs, a, log)
    if a.folder:
        copy_folder(recs, a, log)
    if not (a.param or a.folder):
        raise SystemExit('nothing to do: give --param/--ui/--out and/or --folder')
    print('\n'.join(log))


if __name__ == '__main__':
    main()
