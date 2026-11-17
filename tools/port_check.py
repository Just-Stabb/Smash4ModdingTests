#!/usr/bin/env python3
"""Check an Ultimate port's package (or a fighter's whole install, packages overlaid) against every
bug class the ports so far hit in game (docs/ultimate-port-guide.md "Bug catalogue": Hero's 75
fixes, Squirtle v1-v5, Sephiroth's tests, Steve's, Incineroar's).

  python3 tools/port_check.py NAME PKG [PKG ...] [--vanilla DIR] [--ult-param PRC] [--labels CSV]
                              [--motion-list BIN] [--strict]

NAME: the port (an extra_kinds.json record: brave, pzenigame, ...). PKG: zips or folders, in the
order they were installed (later ones win, as when copied over each other: a fix package over the
version it fixes), each holding fighter/, param/, ui/, sound/ or code/ somewhere inside. --vanilla:
the vanilla game's root (fighter/<base>/script, param/fighter/fighter_param.bin): the base
comparisons. --ult-param / --labels: Ultimate's fighter_param.prc + ParamLabels.csv (the stats
expected, tools/ultimate_stats.py). --motion-list: Ultimate's motion/body/c00/motion_list.bin (the
looping motions). Defaults come from port_sources.json (tools/port_sources.py).

Each finding: ERROR (it broke in game before), WARN (likely wrong, look), INFO. Exit 1 on an ERROR
(--strict: on a WARN too). The tag after the code names the fix that found the bug.
"""
import argparse
import io
import glob
import json
import math
import os
import re
import struct
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import acmd  # noqa: E402

TOPS = ('fighter/', 'param/', 'ui/', 'sound/', 'code/', 'effect/', 'shader/', 'motion/')
JOINTS0 = 26                  # every vanilla fighter's joint table 0


class Install:
    """packages overlaid: {path from the game root: (bytes loader, package)}"""
    def __init__(self, pkgs):
        self.files = {}
        self.earlier = {}            # rel: [(loader, package)] the later packages replaced
        for p in pkgs:
            for rel, load in self._list(p):
                if rel in self.files:
                    self.earlier.setdefault(rel, []).append(self.files[rel])
                self.files[rel] = (load, os.path.basename(p))

    @staticmethod
    def _norm(path):
        path = path.replace('\\', '/')
        if 'not_for_install/' in path or 'TEST_ONLY_' in path:     # test-only builds (a diag exe / MSC) aren't the install
            return None
        # the packaging convention's install roots (docs/ultimate-port-guide.md "Packages"): INSTALL_TO_code/X is code/X
        i = path.find('INSTALL_TO_code/')
        if i >= 0:
            return 'code/' + path[i + len('INSTALL_TO_code/'):]
        for i in range(len(path)):
            if (i == 0 or path[i - 1] == '/') and path.startswith(TOPS, i):
                return path[i:]
        return None

    def _list(self, p):
        if os.path.isdir(p):
            for d, _ds, fs in os.walk(p):
                for f in fs:
                    full = os.path.join(d, f)
                    rel = self._norm(os.path.relpath(full, p))
                    if rel:
                        yield rel, (lambda full=full: open(full, 'rb').read())
        else:
            z = zipfile.ZipFile(p)
            for n in z.namelist():
                rel = self._norm(n)
                if rel and not n.endswith('/'):
                    yield rel, (lambda n=n, z=z: z.read(n))

    def get(self, rel):
        e = self.files.get(rel)
        return e[0]() if e else None

    def where(self, rel):
        e = self.files.get(rel)
        return e[1] if e else None

    def glob(self, pattern):
        r = re.compile(pattern)
        return sorted(k for k in self.files if r.fullmatch(k))


class Report:
    def __init__(self):
        self.items = []

    def add(self, sev, code, msg):
        self.items.append((sev, code, msg))

    def show(self):
        order = {'ERROR': 0, 'WARN': 1, 'INFO': 2, 'NOTE': 2}
        for sev, code, msg in sorted(self.items, key=lambda x: (order[x[0]], x[1])):
            print('%-5s %-22s %s' % (sev, code, msg))
        n = {s: sum(1 for x in self.items if x[0] == s) for s in order}
        print('\n%d errors, %d warnings, %d notes' % (n['ERROR'], n['WARN'], n['INFO'] + n['NOTE']))
        return n


def record(name):
    d = json.load(open(os.path.join(HERE, 'extra_kinds.json')))
    for r in d['kinds']:
        if r['name'] == name:
            return r
    sys.exit('%s: not in tools/extra_kinds.json' % name)


# ------------------------------------------------------------------ the model
def jtb(data):
    n1, n2 = struct.unpack('>HH', data[:4])
    v = struct.unpack('>%dh' % (n1 + n2), data[4:4 + 2 * (n1 + n2)])
    return list(v[:n1]), list(v[n1:])


def vbn_count(data):
    e = '<' if data[:4] == b' NBV' else '>'
    return struct.unpack(e + 'I', data[8:12])[0]


def nud_facts(data):
    """(first bone, last bone, [(mesh, polygon, rigged, flag byte)], texture hashes)"""
    import zlib
    if data[:2] == b'\x78\x9c':
        data = zlib.decompress(data)
    _, _ver, nmesh, bstart, bend, pstart, psize, vsize, vasize = struct.unpack('>IHhhhiiii', data[4:0x20])
    polys, texs = [], set()
    for i in range(nmesh):
        o = 0x30 + i * 0x30
        npoly, obj = struct.unpack('>hi', data[o + 42:o + 48])
        for j in range(npoly):
            q = obj + j * 0x30
            vs = data[q + 14]
            sf = struct.unpack('>H', data[q + 34:q + 36])[0]
            polys.append((i, j, vs >> 4 != 0, sf & 0xFF))
            for to in struct.unpack('>4i', data[q + 16:q + 32]):
                if not to:
                    continue
                ntex = struct.unpack('>H', data[to + 10:to + 12])[0]
                for k in range(ntex):
                    texs.add(struct.unpack('>I', data[to + 0x20 + 0x18 * k:to + 0x24 + 0x18 * k])[0])
    return bstart, bend, polys, texs


def textures_by_use(data, wanted):
    """({(texture, mesh)} on meshes with area, {...} on empty / degenerate ones)"""
    import nud
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.nud', delete=False) as f:
        f.write(data)
    try:
        meshes = nud.read(f.name)
    finally:
        os.unlink(f.name)
    drawn, empty = set(), set()
    for m in meshes:
        for p in m.polygons:
            area = 1.0 if p.nv > 3 else 0.0        # an empty slot: one 3-vertex triangle (ultimate_fighter.py)
            for mat in p.materials:
                for tx in mat.textures:
                    if tx['hash'] in wanted:
                        (drawn if area > 1e-6 else empty).add((tx['hash'], m.name))
    return drawn, empty


def face_gaps(pac, nud_data):
    """[(motion, frames with no keyed mesh shown, frames)] for a material_anime_*.pac: a pac's entry keys a
    group of meshes (the eyelid / mouth slots) and one of them should show on every frame"""
    import mta
    import nud
    import omo
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.nud', delete=False) as f:
        f.write(nud_data)
    with tempfile.NamedTemporaryFile(suffix='.pac', delete=False) as g:
        g.write(pac)
    try:
        real = {m.name for m in nud.read(f.name) if any(p.nv > 3 for p in m.polygons)}
        ents = omo.pac_read(g.name)
    finally:
        os.unlink(f.name)
        os.unlink(g.name)
    out = []
    for name, data in ents:
        if not data.startswith(b'MTA4') or name.startswith(('display', 'default')):
            continue
        m = mta.read(data)
        vis = [v for v in m['vis'] if v['name'] in real]
        if not vis:
            continue
        frames = max(1, m['frames'])
        hidden = 0
        for fr in range(frames + 1):
            if not any([k[1] for k in v['keys'] if k[0] <= fr][-1:] == [1] for v in vis):
                hidden += 1
        if hidden:
            out.append((name.replace('.mta', ''), hidden, frames + 1))
    return out


def nut_ids(data):
    import nut
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.nut', delete=False) as f:
        f.write(data)
    try:
        _d, texs = nut.load(f.name)
    finally:
        os.unlink(f.name)
    return {t.tex_id for t in texs}


def check_model(inst, name, rep):
    costumes = inst.glob(r'fighter/%s/model/body/[cl]\d\d/model\.(nud|jtb|vbn|nut)' % name)
    dirs = sorted({os.path.dirname(c) for c in costumes})
    if not dirs:
        rep.add('INFO', 'model', 'no model/body costume in the packages')
        return {}
    # M6 the low models: the off-screen magnifier and 8-player Smash draw model/body/lXX; a costume without its lXX
    # is invisible there (Squirtle v6, user)
    tags = {d.split('/')[-1] for d in dirs}
    no_low = sorted(t for t in tags if t.startswith('c') and 'l' + t[1:] not in tags)
    if no_low:
        rep.add('ERROR', 'M6 low-models', 'costumes without their low model (model/body/lXX: the magnifier and 8-player '
                'Smash draw it; copies of cXX do, ultimate_port.py low-models): %s' % ', '.join(no_low))
    joints = {}
    for d in dirs:
        tag = d.split('/')[-1]
        jb, vb, nd, nt = (inst.get(d + '/model.' + x) for x in ('jtb', 'vbn', 'nud', 'nut'))
        count = vbn_count(vb) if vb else None
        if jb:
            t0, t1 = jtb(jb)
            joints[tag] = (t0, t1)
            if len(t0) != JOINTS0:
                rep.add('ERROR', 'M1 jtb-table0', '%s: joint table 0 has %d entries (every vanilla fighter: 26; '
                        'extras go to table 1: Sephiroth test 20, Squirtle v5)' % (tag, len(t0)))
            if count:
                bad = [i for i in t0 + t1 if not 0 <= i < count]
                if bad:
                    rep.add('ERROR', 'M2 jtb-range', '%s: joint table points past the %d bones: %s' % (tag, count, bad[:5]))
            dup = sorted(set(t1) & set(t0))
            if dup and count:
                rep.add('WARN', 'M2 jtb-standin', '%s: table-1 joints share a bone with table 0 (%s): the base\'s '
                        'own code drives table-1 bones (Hero / Steve fix 9: the head came off)' % (tag, dup))
        if count and count > 138:
            rep.add('WARN', 'M6 bones', '%s: %d bones (vanilla at most 138; --max-bones)' % (tag, count))
        if nd:
            b0, b1, polys, texs = nud_facts(nd)
            if b0 < 2 or (count and b1 >= count):
                rep.add('ERROR', 'M3 nud-range', '%s: NUD bone range %d-%d (vanilla 2-N; 0-N drew a pillar / '
                        'crashed: Incineroar, Sephiroth)' % (tag, b0, b1))
            unflagged = [p for p in polys if p[2] and p[3] != 4]
            if unflagged:
                rep.add('ERROR', 'M4 nud-rigged-flag', '%s: %d rigged polygons without flag 4 (drawn unskinned: '
                        'Sephiroth test 19)' % (tag, len(unflagged)))
            own = {t for t in texs if t >> 24 not in (0x10,)}
            if not nt:
                if inst.where(d + '/model.nud') not in (None,):
                    rep.add('ERROR', 'M5 nut-missing', '%s: model.nud in %s without a model.nut in the packages '
                            '(Hero fix 17: textures in the wrong places)' % (tag, inst.where(d + '/model.nud')))
            else:
                missing = own - nut_ids(nt)
                if missing:
                    drawn, empty = textures_by_use(nd, missing)
                    if drawn:
                        rep.add('ERROR', 'M5 nut-ids', '%s: NUD textures not in model.nut on drawn meshes: %s' % (
                            tag, ', '.join('%08X %s' % x for x in sorted(drawn)[:6])))
                    if empty:
                        rep.add('WARN', 'M5 nut-ids-empty', '%s: empty mesh slots keep the base\'s textures, not in '
                                'model.nut: %s' % (tag, ', '.join(sorted({'%08X' % x[0] for x in empty}))))
                if inst.where(d + '/model.nud') != inst.where(d + '/model.nut'):
                    rep.add('WARN', 'M5 nut-stale', '%s: model.nud from %s, model.nut from %s: ship them together'
                            % (tag, inst.where(d + '/model.nud'), inst.where(d + '/model.nut')))
        for pac in ('material_anime_face.pac', 'material_anime_eyelid.pac'):
            data = inst.get(d + '/' + pac)
            if data is None and nd:
                rep.add('WARN', 'M7 material-anime', '%s: no %s (the face / visibility keys)' % (tag, pac))
            if data is not None:
                redirected = lst_redirects(data)
                if redirected:
                    rep.add('ERROR', 'F2 face-lst', '%s %s: material_anime.lst sends %d motions that have an entry of '
                            'their own to another motion\'s (the base\'s shared entries; the game takes the list: Byleth '
                            'v3 showed SpecialNStart\'s bow and no sword in Wait1; ultimate_fighter.lst_without): %s' % (
                                tag, pac, len(redirected), ', '.join(redirected[:6])))
            if data is not None and nd and tag in ('c00', 'c01'):
                gaps = face_gaps(data, nd)
                if gaps:
                    rep.add('ERROR', 'F1 face-hidden', '%s %s: %d motions show none of its meshes on some frames (a '
                            'hole / black face: the base\'s keys hide meshes that are part of the port\'s face; drive '
                            'the slots from Ultimate\'s visibility tracks): %s' % (tag, pac, len(gaps), ', '.join(
                                '%s (%d of %d frames)' % g for g in gaps[:8])))
    return joints


def check_texture_ids(inst, name, base, vanilla, src, rep):
    """T1 / T2 (tools/fighter_texture_ids.py): the game keys the textures it has loaded by id, so an id two models use
    for different pictures draws whichever loaded first on both (every port's .nut used 0x40EB0000 + k in every
    costume: a P1 Steve drew a P2 Squirtle with his textures, fighters_texid_fix_v1). Over every fighter model folder in
    the packages (other fighters' too) and the base's vanilla models; T2: every model.nud / metal.nud texture of a drawn
    mesh (and texture pattern) in its own folder's model.nut (Sephiroth's metal.nud named a texture his model.nut
    didn't have)"""
    import fighter_texture_ids as tx
    dirs = [d for d in (os.path.join(vanilla, 'fighter', base) if vanilla else None,
                        src.get('base_fighter_dirs', {}).get(base)) if d and os.path.isdir(d)]
    files = {k: v[0] for k, v in inst.files.items()}
    tx.check(files, vanilla=tx.vanilla_digests(dirs), only={name}, report=rep.add)
    if not dirs:
        rep.add('INFO', 'T1 texture-vanilla', 'no vanilla %s model folder (port_sources.json vanilla / base_fighter_dirs): '
                'textures under the base\'s ids not compared with the base\'s' % base)


# ------------------------------------------------------------------ the scripts
def scripts(inst, rel):
    data = inst.get(rel)
    if data is None:
        return None
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(data)
    try:
        return acmd.ACMDFile.load(f.name).scripts
    finally:
        os.unlink(f.name)


def bone_params(c):
    syn = c.info.get('syntax', [])
    return [c.params[i] for i, s in enumerate(syn) if s == 'Bone' and i < len(c.params)]


def check_scripts(inst, name, kind, base, joints, vanilla, rep):
    body = 'fighter/%s/script/animcmd/body/' % name
    game = scripts(inst, body + 'game.bin')
    if game is None:
        rep.add('INFO', 'scripts', 'no body game.bin in the packages')
        return
    # S1 roll-off: the universal mechanics' rolls (EscapeF / EscapeB momentum)
    for n in ('escapef', 'escapeb'):
        s = game.get(acmd.crc(n), [])
        if not any(c.name == 'Add/Set_Momentum' and c.params and abs(c.params[0]) >= 0.5 for c in s):
            rep.add('ERROR', 'S1 rolloff', '%s has no roll speed: the game.bin was built on a body without the universal '
                    'mechanics (Hero fix 57 -> 58, Bowser jabs v3 -> v4); build on universal_mechanics_all\'s' % n)
    # S2 joint ids against the joint table
    if joints:
        t0, t1 = next(iter(joints.values()))
        valid = set(range(0, len(t0) + 1)) | set(range(1000, 1000 + len(t1)))
        for fn in ('game', 'effect'):
            sc = game if fn == 'game' else scripts(inst, body + 'effect.bin') or {}
            bad = {}
            for h, cmds in sc.items():
                for c in cmds:
                    for b in bone_params(c):
                        if b not in valid and not 11000 <= b < 11100:
                            bad.setdefault(b, set()).add('%08X' % h)
            for b, hs in sorted(bad.items()):
                rep.add('ERROR' if fn == 'game' else 'WARN', 'S2 joint-ids', '%s.bin: joint %d (0x%X) not in the joint '
                        'table (0-%d, 1000-%d) in %d scripts' % (fn, b, b, len(t0), 999 + len(t1), len(hs)))
    # S3 effect ids: own bank (0x3KK....), the base's (0x3BB....: its specials / articles), common (0x1......)
    eff = scripts(inst, body + 'effect.bin') or {}
    efc = inst.get('fighter/%s/effect/%s/%s.010d0000.efc' % (name, name, name))
    n_own = None
    if efc:
        import efc as E
        n_own = len(E.Efc(efc).entries)
    base_kind = base.get('kind')
    other = {}
    for h, cmds in eff.items():
        for c in cmds:
            if c.name.startswith(('External_Graphic', 'Graphic_Effect', 'EFFECT', 'Terminate_Graphic')) and c.params:
                g = c.params[0]
                bank, idx = g >> 16, g & 0xFFFF
                if bank == 0x300 + kind and n_own is not None and idx >= n_own:
                    rep.add('ERROR', 'S3 effect-ids', 'effect 0x%07X past the bank\'s %d entries (script %08X)' % (g, n_own, h))
                elif bank >> 8 in (3, 4) and bank & 0xFF != kind and bank & 0xFF != base_kind:
                    other.setdefault(bank, set()).add(h)
    for bank, hs in other.items():
        rep.add('WARN', 'S3 effect-bank', 'effects from bank 0x%X (neither the port\'s nor its base\'s) in %d scripts'
                % (bank, len(hs)))
    # S4 Ultimate-only angles; S5 throw hitboxes that free the held fighter
    hb = ('Special_Hitbox', 'Extended_Special_Hitbox', 'Extra_Special_Hitbox', 'Extra_Extended_Special_Hitbox', 'Hitbox')
    bad_angle, freeing = set(), set()
    names = {acmd.crc(n): n for n in ('throwf', 'throwb', 'throwhi', 'throwlw')}
    for h, cmds in game.items():
        applier = any(c.name == 'Throw_Applier' for c in cmds)
        for c in cmds:
            # 367 is Smash 4's too (the victim follows the hitbox's motion, grounded ones as well: user decision
            # 2026-11-16, ultimate_acmd.py keeps Ultimate's 367); 368 (to a set point) has none: vec_target.py
            if c.name in hb and len(c.params) > 4 and c.params[4] > 367:
                bad_angle.add('%08X' % h)
            if c.name == 'Throw_Applier':
                applier = False
            if applier and c.name in hb and h in names:
                syn = c.info.get('syntax', [])
                if 'NoGrabRelease' not in syn or not c.params[syn.index('NoGrabRelease')]:
                    freeing.add(names[h])
    if bad_angle:
        rep.add('ERROR', 'S4 angle', 'angles past 367 (Ultimate\'s 368: no such angle in Smash 4, the multi-hits let '
                'go: Squirtle\'s Waterfall) in %d scripts' % len(bad_angle))
    if freeing:
        rep.add('ERROR', 'S5 throw-release', 'hitboxes before the throw\'s release without NoGrabRelease (they free the '
                'held fighter: Squirtle\'s throws): %s' % ', '.join(sorted(freeing)))
    turned, common = set(), {}
    for h, cmds in eff.items():
        for c in cmds:
            syn = c.info.get('syntax', [])
            if c.name.startswith(('External_Graphic', 'Graphic_Effect', 'EFFECT_FOLLOW')) and c.params:
                g = c.params[0]
                if g >> 16 == 0x100:
                    common.setdefault(g, set()).add(h)
                if 'Bone' in syn and 'XRot' in syn and g >> 16 == 0x300 + kind:
                    b = c.params[syn.index('Bone')]
                    rot = [c.params[syn.index(k)] for k in ('XRot', 'YRot', 'ZRot') if k in syn]
                    if b not in (0, None) and any(abs(r) > 0.5 and abs(abs(r) - 180) > 0.5 for r in rot):
                        turned.add('%08X' % h)
    if turned:
        rep.add('WARN', 'E1 effect-turn', '%d scripts turn the port\'s own effects on a bone: Smash 4 flips them for one '
                'facing (Sephiroth test 49): tools/effect_variants.py scan / vfxb_to_ptcl.py --variants' % len(turned))
    if common:
        rep.add('WARN', 'E3 common-effects', '%d Smash 4 common effects in %d scripts stand in for Ultimate\'s sys_* ones '
                '(they look like Smash 4\'s, not Ultimate\'s: convert them from ef_common.eff, vfxb_to_ptcl.py '
                '--extra-eff, as Hero\'s attack line): %s' % (len(common), len(set().union(*common.values())),
                                                         ', '.join('%07X' % g for g in sorted(common)[:12])))
    # S7 the base's own scripts still in the port's moves
    if vanilla:
        vg = os.path.join(vanilla, 'fighter', base['base'], 'script/animcmd/body/game.bin')
        mt = inst.get(body + 'motion.mtable')
        if os.path.exists(vg) and mt:
            import mtable
            vgame = acmd.ACMDFile.load(vg).scripts
            hashes = struct.unpack('>%dI' % (len(mt) // 4), mt)
            names = {i: (mtable.COMMON[i] if i < len(mtable.COMMON) else '') for i in range(len(hashes))}
            vocab = {acmd.crc(n): n for n in vocabulary()}
            same, custom = [], []
            for i, h in enumerate(hashes):
                if h and h in vgame and h in game and [str(c) for c in game[h]] == [str(c) for c in vgame[h]]:
                    if any(str(c).startswith(('Hitbox', 'Special_Hitbox', 'Extended')) for c in game[h]):
                        n = names.get(i) or vocab.get(h) or '0x%X' % i
                        (custom if re.search(r'_c[23]$', n) else same).append(n)
            if same:
                rep.add('WARN', 'S7 base-moves', '%d moves still the base\'s hitboxes: %s' % (len(same), ', '.join(same[:20])))
            if custom:
                rep.add('INFO', 'S7 base-customs', '%d custom-move slots keep the base\'s (only with custom moves '
                        'equipped: base_customs_cave): %s' % (len(custom), ', '.join(custom[:20])))
    # B1 base leftovers (user, Byleth phase 2: "make sure Zero Suit Samus' statuses don't override Byleth's, like the
    # issues we had with Sephiroth and Supamario"): every script of the four body files still byte for byte the base's
    # vanilla one that does something (hitbox / grab / body state / intangibility; an effect, sound, rumble, quake,
    # visibility) runs the base's move on the port's animation. ERROR for game scripts that act, WARN for effect /
    # sound / expression ones; port.json "base_scripts_kept" {script name: reason} lists the ones kept on purpose
    if vanilla:
        kept = {k.lower() for k in (load_port_cfg(name).get('base_scripts_kept') or {})}
        kept_crc = {acmd.crc(k) for k in kept}       # (names the vocabulary lacks: Byleth's batswing4)
        vocab = {acmd.crc(n): n for n in vocabulary()}
        acts = {'game': ('Hitbox', 'Special_Hitbox', 'Extended', 'Grab', 'Body_Collision', 'Set_Body_State',
                         'Intangib', 'Invincib', 'Super_Armor', 'Armor', 'Reflect', 'Absorb', 'Search', 'Shield',
                         'Generate_Article', 'Article'),
                'effect': ('Graphic', 'External_Graphic', 'EFFECT', 'Sword_Glow', 'LANDING', 'FOOT', 'DOWN_EFFECT'),
                'sound': ('Sound', 'PLAY', 'Voice', 'SFX'),
                'expression': ('Rumble', 'QUAKE', 'Screen', 'Visibility', 'Model_Changer', 'Flash')}
        for fn, words in acts.items():
            vp = os.path.join(vanilla, 'fighter', base['base'], 'script/animcmd/body/%s.bin' % fn)
            mine = game if fn == 'game' else (scripts(inst, body + fn + '.bin') or {})
            if not os.path.exists(vp) or not mine:
                continue
            van = acmd.ACMDFile.load(vp).scripts
            left = sorted(vocab.get(h, '%08X' % h) for h, cmds in mine.items()
                          if h in van and [str(c) for c in cmds] == [str(c) for c in van[h]]
                          and any(str(c).startswith(words) for c in cmds)
                          and vocab.get(h, '%08X' % h).lower() not in kept and h not in kept_crc)
            if left:
                rep.add('ERROR' if fn == 'game' else 'WARN', 'B1 base-leftovers', '%s.bin: %d scripts still the base\'s '
                        'vanilla ones (its move / effects / sounds on the port\'s animation; replace, empty, or list '
                        'in port.json base_scripts_kept): %s' % (fn, len(left), ', '.join(left[:24])))
    # S8 a plain Rumble on a Smash 4 kind whose pattern never ends (param/pad_rumble: ultimate_acmd.RUMBLE_ENDLESS): it
    # runs on for seconds (Squirtle's up smash, test 25: rbkind_loopattack -> Rumble 8). Vanilla plays those kinds as
    # Rumble_Loop, which the status's end stops; the base's own scripts (unchanged from vanilla) are left alone
    import ultimate_acmd
    expr = scripts(inst, body + 'expression.bin') or {}
    vexpr = {}
    if vanilla:
        ve = os.path.join(vanilla, 'fighter', base['base'], 'script/animcmd/body/expression.bin')
        vexpr = acmd.ACMDFile.load(ve).scripts if os.path.exists(ve) else {}
    endless = set()
    for h, cmds in expr.items():
        if h in vexpr and [str(c) for c in cmds] == [str(c) for c in vexpr[h]]:
            continue
        if any(c.name == 'Rumble' and c.params and int(c.params[0]) in ultimate_acmd.RUMBLE_ENDLESS for c in cmds):
            endless.add('%08X' % h)
    if endless:
        rep.add('ERROR', 'S8 rumble-endless', 'plain Rumble on a kind that never stops (%s) in %d expression scripts: '
                'it rumbles on for seconds; play it as Rumble_Loop: %s' % (', '.join(map(str, ultimate_acmd.RUMBLE_ENDLESS)),
                                                                           len(endless), ', '.join(sorted(endless)[:8])))


# ------------------------------------------------------------------ params
def fp_row(path_or_bytes, kind):
    import fighter_param as FP  # noqa: F401
    import tempfile
    if isinstance(path_or_bytes, bytes):
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(path_or_bytes)
        f.close()
        path = f.name
    else:
        path = path_or_bytes
    idx = list(range(1, 35)) + [44, 45, 48, 49, 81, 82, 86, 185, 262, 263, 264, 268]
    r = subprocess.run([sys.executable, os.path.join(HERE, 'fighter_param.py'), 'get', path, str(kind)] + [str(i) for i in idx],
                       capture_output=True, text=True)
    if isinstance(path_or_bytes, bytes):
        os.unlink(path)
    out = {}
    for line in r.stdout.splitlines():
        m = re.match(r'(\d+) = (\S+)', line)
        if m:
            out[int(m.group(1))] = float(m.group(2))
    return out


def check_params(inst, name, kind, base, vanilla, ult_param, labels, rep):
    fp = inst.get('param/fighter/fighter_param.bin')
    if fp is None:
        rep.add('INFO', 'params', 'no fighter_param.bin in the packages (the stats come from another install)')
        return
    row = fp_row(fp, kind)
    if not row:
        rep.add('ERROR', 'P1 stats-row', 'fighter_param.bin (%s) has no entry for kind 0x%X' % (inst.where('param/fighter/fighter_param.bin'), kind))
        return
    if vanilla:
        vb = fp_row(os.path.join(vanilla, 'param/fighter/fighter_param.bin'), base['base'])
        same = [i for i in row if i in vb and abs(row[i] - vb[i]) < 1e-6 and i in (1, 3, 8, 11, 17, 24, 33)]
        if len(same) >= 5:
            rep.add('ERROR', 'P1 stats-base', 'kind 0x%X\'s stats are still %s\'s (walk, dash, run, jump, gravity, weight '
                    'equal) in %s: tools/ultimate_stats.py' % (kind, base['base'], inst.where('param/fighter/fighter_param.bin')))
    if ult_param and labels:
        import ultimate_stats as US
        try:        # the port's jump scale (port.json stats.jump_scale: the ports made before the framework)
            js = tuple(json.load(open(os.path.join(ROOT, 'fighters', name, 'port.json')))['stats']['jump_scale'])
        except (OSError, KeyError, ValueError):
            js = (1.0, 1.0)
        so = US.stats_override(name)     # port.json stats.override (Incineroar's 263, fighter_params_v2)
        want = US.values(US.entry(ult_param, labels, base.get('ult', name)), js, so)
        if so:
            rep.add('INFO', 'P2 stats-ultimate', 'kind 0x%X: port.json stats.override keeps %s over Ultimate\'s' % (
                kind, ', '.join('%d %s %s' % (i, US.MAP[i][0], v) for i, v in sorted(so.items()))))
        diff = ['%d %s %s->%s' % (i, w[1], row.get(i), w[0]) for i, w in sorted(want.items())
                if i in row and abs(row[i] - float(w[0])) > 0.011 * max(1, abs(float(w[0])))]
        if diff:
            rep.add('WARN', 'P2 stats-ultimate', 'differ from Ultimate\'s (tools/ultimate_stats.py): ' + '; '.join(diff[:12]))
    # P4 size (fighter_sizes_v1: "some of the character sizes for ported characters are incorrect"): every port up to
    # then kept its base's fighter_param 44 scale (Incineroar Bowser's 0.82 for Ultimate's 1.0, Hero / Squirtle / Byleth
    # 1.0 for 0.96 / 0.94 / 1.02) and the base's shield / effect / ice sizes. The model is Ultimate's skeleton 1:1, so the
    # size in game is 44 x that model: 44 must be Ultimate's scale (ERROR), as must 49 effect_scale and 185 freeze_size
    # (equal in both games for all 57 shared fighters); 45 shield (Ultimate's x 0.88) and 48 (45 x 0.35) are a fit:
    # WARN. tools/ultimate_stats.py SIZE (the stats step; `ultimate_stats.py sizes` re-applies them alone). A port's
    # port.json "stats": {"size": {...}} (the user's call: Hero's are his pre-fighter_sizes_v1 sizes, fighter_params_v2)
    # is what's expected for those words instead of Ultimate's
    if ult_param and labels:
        import ultimate_stats as US
        try:
            ov = US.size_override(name)
            sv = US.size_values(US.entry(ult_param, labels, base.get('ult', name)), ov)
        except SystemExit:
            ov, sv = {}, {}
        if ov:
            rep.add('INFO', 'P4 size', 'kind 0x%X: port.json stats.size keeps %s over Ultimate\'s' % (
                kind, ', '.join('%d %s %g' % (i, US.SIZE_NAMES[i], v) for i, v in sorted(ov.items()))))
        bad = {}
        for i, (w, uname, _how) in sorted(sv.items()):
            if i in row and abs(row[i] - w) > 0.005 * max(1.0, abs(w)):
                bad.setdefault('ERROR' if i in (44, 49, 185) or i in ov else 'WARN', []).append(
                    '%d %s %g (%s -> %g)' % (i, US.SIZE_NAMES[i], row[i], 'port.json stats.size' if i in ov else
                                             'Ultimate\'s ' + uname, w))
        for lvl, items in sorted(bad.items()):
            rep.add(lvl, 'P4 size', 'kind 0x%X\'s size differs from Ultimate\'s%s in %s: %s. `python3 tools/ultimate_stats.py '
                    'sizes PRC LABELS FP_IN FP_OUT %s` re-applies the sizes alone' % (
                        kind, ' (or port.json stats.size)' if ov else '', inst.where('param/fighter/fighter_param.bin'),
                        '; '.join(items), name))
    # P3 rapid-count (Byleth v17: "jab 3 is inaccessible"): the common Attack status (func_270) goes into the rapid jab
    # when ENABLE_100 is on and the presses so far (0x11000003) >= fighter_param 86 (attack_100_input_count): a rapid jab
    # (264 = 1) with 86 = 0 (left from a base without one: ZSS) goes in as soon as jab 2 turns ENABLE_100 on, pressed
    # or not, so the third jab never comes. Meta Knight's own (262 = 3) has no jab chain before it
    if row.get(264) and not row.get(86) and row.get(262) != 3:
        rep.add('ERROR', 'P3 rapid-count', 'kind 0x%X has a rapid jab (fighter_param 264 = 1) needing 0 presses (86 = 0): '
                'the jab chain goes into it the moment ENABLE_100 opens (its later jabs never come). 86 = Ultimate\'s '
                'attack_100_enable_cnt + 1 (tools/ultimate_stats.py)' % kind)


def load_port_cfg(name):
    """fighters/NAME/port.json, or {} (the ports made before the framework have none)"""
    p = os.path.join(ROOT, 'fighters', name, 'port.json')
    return json.load(open(p)) if os.path.exists(p) else {}


def vocabulary():
    """motion / script names known to Sm4shCommand and the ports (their CRCs are the scripts' keys)"""
    names = set()
    for f in ('tools/Sm4shCommand/SM4SHCommand/AnimNames.txt', 'tools/Sm4shCommand/SM4SHCommand/ModAnimNames.txt',
              'reference/ultimate_motion_kinds.txt'):
        for line in open(os.path.join(ROOT, f), errors='replace'):
            w = line.split('->')[0].split('=')[0].strip()
            if w and not w.startswith(('//', '#', '0x')) and ' ' not in w:
                names.add(w.lower())
    return names


def check_vl(inst, name, base, motion_list, rep):
    vl = inst.get('param/fighter/fighter_param_vl_%s.bin' % name)
    if vl is None or not motion_list:
        return
    import fighter_param_vl as V
    import tempfile
    import ultimate_acmd as UA
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(vl)
    try:
        vf = V.load(f.name, base.get('vl_kind', base['base']))
    finally:
        os.unlink(f.name)
    mt = inst.get('fighter/%s/script/animcmd/body/motion.mtable' % name)
    if not mt:
        return
    hashes = list(struct.unpack('>%dI' % (len(mt) // 4), mt))
    loops = {e['game'] for e in UA.read_motion_list(motion_list) if e['flags'] & 2}
    # the fighter's --translate map: a Smash 4 slot can hold another Ultimate script than its name's
    # (Squirtle's specials = Ultimate's SpecialSStart, not its looping SpecialS)
    ult_of = {}
    try:
        cfg = json.load(open(os.path.join(ROOT, 'fighters', name, 'port.json')))
        tr = json.load(open(os.path.join(ROOT, 'fighters', name, cfg['specials']['acmd'])))
        for u, v in tr.items():
            if not u.startswith('_'):
                ult_of[(v['name'] if isinstance(v, dict) else v).lower()] = u
    except (OSError, KeyError, ValueError):
        pass
    wrong = []
    for n in vocabulary():
        h = acmd.crc(n)
        if h in hashes and UA.hash40('game_' + ult_of.get(n.lower(), n).lower()) in loops:
            i = hashes.index(h)
            try:
                (_p, t), = V.find(vf, 'm0[%d].0' % i, '0', {})
            except Exception:
                continue
            if t.value:
                wrong.append('0x%X %s' % (i, n))
    if wrong:
        rep.add('ERROR', 'V1 vl-loop', 'looping in Ultimate but byte 0 = 1 (plays once and holds: Hero fix 63): %s' % ', '.join(wrong))


def translate_map(name):
    """{Smash 4 script name (lower case): Ultimate script name} from the port's --translate map (port.json's
    specials.acmd, else fighters/NAME/specials_acmd.json); other scripts keep their own name"""
    path = os.path.join(ROOT, 'fighters', name, 'specials_acmd.json')
    try:
        cfg = json.load(open(os.path.join(ROOT, 'fighters', name, 'port.json')))
        path = os.path.join(ROOT, 'fighters', name, cfg['specials']['acmd'])
    except (OSError, KeyError, ValueError):
        pass
    out = {}
    try:
        for u, v in json.load(open(path)).items():
            if not u.startswith('_'):
                out[(v['name'] if isinstance(v, dict) else v).lower()] = u
    except (OSError, ValueError):
        pass
    return out


def c_functions(text):
    """{function name: body} of an MSC C source (top-level definitions, braces at column 0)"""
    out = {}
    for m in re.finditer(r'^(?:void|int|float)\s+(\w+)\s*\([^;{]*\)\s*\n\{\n(.*?)^\}', text, re.S | re.M):
        out[m.group(1)] = m.group(2)
    return out


CANCEL_TESTS = ('CancelModule(0x2713)', 'func_39()', 'func_41()')
# moves (C1 (a)); common motions (damage, downs, dodges, guard) follow Smash 4's own rules for them
CANCEL_MOVES = ('attack', 'special', 'throw', 'catchattack', 'catchwait', 'appeal', 'cliffattack', 'downattack',
                'slipattack')


FIRST_OWN_MOTION = 0x211          # the fighter's own motion kinds (specials, final, ...): docs/params/fighter_files.md


def check_vl_leftovers(inst, name, vf, hashes, ml, ult_of, rep):
    """V1: the base's vl motion bytes on the port's own slots (0x211 on): bytes 3 / 4 (the intangible window: the
    motion's xlu start / end) and 5 where the port plays an Ultimate move must be Ultimate's motion_list window (5:
    none in Ultimate); where its four scripts are empty (a base slot the port doesn't play) bytes 2-5 are 0. Supamario
    Core Breaker v11 kept Mario's intangible window; Byleth phase 2 found ZSS's Flip Jump window (3-13) on his Aymr
    slots and her Boost Kick's byte 5. Slots whose scripts port.json base_scripts_kept lists are skipped"""
    import ultimate_acmd as UA
    sc = {fn: scripts(inst, 'fighter/%s/script/animcmd/body/%s.bin' % (name, fn)) for fn in ('game', 'effect', 'sound',
                                                                                          'expression')}
    if any(v is None for v in sc.values()):
        return
    kept = {acmd.crc(k.lower()) for k in (load_port_cfg(name).get('base_scripts_kept') or {})}
    by_crc = {acmd.crc(n): n for n in vocabulary() | set(ult_of)}
    bad = []
    for i in range(FIRST_OWN_MOTION, len(hashes)):
        h = hashes[i]
        if not h or h in kept:
            continue
        try:
            b = [V_byte(vf, i, k) for k in range(6)]
        except Exception:                 # noqa: BLE001
            continue
        live = any(len([c for c in x.get(h, []) if c.ident != acmd.END]) for x in sc.values())
        n = by_crc.get(h)
        want = None
        if n is not None and live:
            uh = UA.hash40('game_' + ult_of.get(n, n).lower())
            ent = [e for e in ml if uh == e['game'] or uh in e['scripts']]
            if ent and len(ent[0]['extra']) >= 3:
                xs, xe = ent[0]['extra'][:2]
                if (b[3], b[4], b[5]) != (xs, xe, 0):
                    want = 'intangible %d-%d, byte 5 %d (Ultimate %d-%d, 0)' % (b[3], b[4], b[5], xs, xe)
        elif not live and any(b[2:]):
            want = 'not played (scripts empty) but bytes 2-5 %s' % b[2:]
        if want:
            bad.append('0x%X %s: %s' % (i, n or '%08X' % h, want))
    if bad:
        rep.add('ERROR', 'V1 vl-leftovers', 'the base\'s vl motion bytes on the port\'s own slots (Supamario Core '
                'Breaker v11, Byleth): %s' % '; '.join(bad[:16]))


def V_byte(vf, i, k):
    import fighter_param_vl as V
    (_p, t), = V.find(vf, 'm0[%d].%d' % (i, k), '0', {})
    return t.value


def check_cancel(inst, name, base, motion_list, rep):
    """C1: the cancel windows are Ultimate's (user rule, Sephiroth test 72: "down special and side special have
    different recovery than in Ultimate"; Shadow Flare's shot played to its end, Ultimate cancels it at 31).
    (a) every motion the port took from Ultimate has Ultimate's motion_list cancel frame in vl group 1 byte 2;
    (b) in the port's own MSC source, a status playing such a motion (MotionModule(0x1, ...) with its slot, then
    func_78(loop)) must test it in its loop or a function the loop calls: CancelModule(0x2713) (the vl byte) or
    the motion frame, then func_39 / func_41 (Wait / Fall checks) as Zelda's statuses do"""
    vl = inst.get('param/fighter/fighter_param_vl_%s.bin' % name)
    mt = inst.get('fighter/%s/script/animcmd/body/motion.mtable' % name)
    if vl is None or mt is None or not motion_list:
        return
    import fighter_param_vl as V
    import tempfile
    import ultimate_acmd as UA
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(vl)
    try:
        vf = V.load(f.name, base.get('vl_kind', base['base']))
    finally:
        os.unlink(f.name)
    hashes = list(struct.unpack('>%dI' % (len(mt) // 4), mt))
    ml = UA.read_motion_list(motion_list)
    ult_of = translate_map(name)
    cancel_at = {}                       # slot: Ultimate's cancel frame
    wrong = []
    # a slot whose four scripts are empty isn't played (a base special slot the port's MSC never enters: Byleth's
    # SpecialAirHi, his air up special being AirCatch): its byte 2 is V1's (0)
    body = {fn: scripts(inst, 'fighter/%s/script/animcmd/body/%s.bin' % (name, fn)) or {}
            for fn in ('game', 'effect', 'sound', 'expression')}
    unplayed = {h for h in hashes if h and not any(len([c for c in x.get(h, []) if c.ident != acmd.END])
                                                   for x in body.values())}
    for n in sorted(vocabulary() | set(ult_of)):
        if not n.startswith(CANCEL_MOVES) or n.startswith('landing') or n in UA.GAME_ONLY or acmd.crc(n) not in hashes:
            continue
        if acmd.crc(n) in unplayed and n not in ult_of:
            continue
        i = hashes.index(acmd.crc(n))
        h = UA.hash40('game_' + ult_of.get(n, n).lower())
        ent = [e for e in ml if h == e['game'] or h in e['scripts']]
        if not ent or len(ent[0]['extra']) < 3:
            continue
        want = ent[0]['extra'][2]
        try:
            (_p, t), = V.find(vf, 'm0[%d].2' % i, '0', {})
        except Exception:
            continue
        if want:
            cancel_at[i] = (n, want)
        if t.value != want:
            wrong.append('0x%X %s %d (Ultimate %d)' % (i, n, t.value, want))
    if wrong:
        rep.add('ERROR', 'C1 cancel-window', 'vl byte 2 (the cancel frame) is not Ultimate\'s: %s' % ', '.join(wrong))
    check_vl_leftovers(inst, name, vf, hashes, ml, ult_of, rep)
    try:
        cfg = json.load(open(os.path.join(ROOT, 'fighters', name, 'port.json')))
        src = os.path.join(ROOT, 'fighters', name, cfg['specials']['msc'])
    except (OSError, KeyError, ValueError):
        src = os.path.join(ROOT, 'fighters', name, name + '.c')
    if not os.path.exists(src) or not cancel_at:
        return
    fns = c_functions(open(src, errors='replace').read())

    def tests(fn, depth=0):
        body = fns.get(fn, '')
        if any(t in body for t in CANCEL_TESTS):
            return True
        return depth < 1 and any(tests(c, depth + 1) for c in set(re.findall(r'\b(\w+)\(', body)) if c in fns and c != fn)
    missing = []
    for fn, body in fns.items():
        loops = re.findall(r'func_78\((\w+)\)', body)
        if not loops:
            continue
        slots = set()
        for line in body.split('\n'):
            if 'MotionModule(0x1,' in line:
                slots.update(int(x, 16) for x in re.findall(r'0x([0-9a-fA-F]{3})\b', line))
        hit = sorted(s for s in slots if s in cancel_at)
        if hit and not any(tests(lp) for lp in loops):
            missing.append('%s -> %s (%s)' % (fn, '/'.join(loops), ', '.join('0x%X %s cancel %d' % (s, cancel_at[s][0],
                                                                                              cancel_at[s][1]) for s in hit)))
    if missing:
        rep.add('ERROR', 'C1 cancel-window', 'a status plays a motion Ultimate cancels but its loop never tests the '
                'cancel (CancelModule(0x2713) / the frame, then func_39 / func_41): %s' % '; '.join(missing))


# ------------------------------------------------------------------ MSC and sources
MSC_GLOBALS_PROVEN = 0x86       # Hero fix 79: every spell cast writes global 0x86 (brave_lw_burst) and works


def msc_max_global(data):
    """the highest global variable index an MSC file reads or writes"""
    import io
    sys.path.insert(0, os.path.join(HERE, 'mscdec'))
    from msc import MscFile
    m = MscFile()
    m.readFromFile(io.BytesIO(data))
    hi = 0
    for sc in m:
        for c in sc:
            if c.command in (0x0B, 0x1C, 0x41, 0x14, 0x15, 0x3F, 0x40) or 0x1C <= c.command <= 0x24 \
                    or 0x41 <= c.command <= 0x45:
                p = c.parameters
                if len(p) >= 2 and p[0] == 1:
                    hi = max(hi, p[1])
    return hi


JOINT_OP = re.compile(r'ModelModule\((?:0|0x0|0x1|0x7), *([^,)]+)')


def check_joint_overrides(src, rep):
    """C6: MSC joint overrides (ModelModule 0 scale / 1 rotate / 7 translate) go into the model's override list
    (0x02C64078: one 0x28-byte entry per joint, appended with no capacity check). Vanilla scripts touch a fixed one
    or two joints; Sephiroth test 79 posed 15 every frame from load and the game crashed loading him (its 0.001 hide
    scale written over a structure's count). Flags a joint op run from a loop (directly or through a helper).
    The overrides are the MotionModule's (0x02C5B000 - 0x02C66000), by joint ID as ACMD's: a fighter's table 0 below
    1000, table 1 from 1000 (test 79's 1005+ were accepted: that is how 15 got in); a weapon's jtb entry n as 0x7D0 + n
    (Mario's pump). Sephiroth's blade is 1003"""
    for d, _ds, fs in os.walk(src):
        for f in fs:
            if not f.endswith('.c') or os.sep + 'weapons' + os.sep in os.path.join(d, f):
                continue
            path = os.path.join(d, f)
            text = open(path, errors='replace').read()
            funcs = c_functions(text)
            posers = {n for n, body in funcs.items() if JOINT_OP.search(body)}
            for n, body in funcs.items():
                for m in re.finditer(r'\b(?:while|for) *\(', body):
                    i = body.find('{', m.end())
                    if i < 0:
                        continue
                    depth, j = 0, i
                    while j < len(body):
                        depth += {'{': 1, '}': -1}.get(body[j], 0)
                        if depth == 0:
                            break
                        j += 1
                    loop = body[i:j]
                    hit = JOINT_OP.search(loop) or next((p for p in posers if re.search(r'\b%s\(' % p, loop)), None)
                    if hit:
                        rep.add('ERROR', 'C6 joint-overrides', '%s %s(): ModelModule joint ops from a loop (%s): every joint '
                                'is an entry in the model\'s override list, which the game never bounds (Sephiroth test 79 '
                                'crashed loading him); pose at most a couple of joints' % (
                                    os.path.relpath(path, ROOT), n, hit if isinstance(hit, str) else 'ModelModule'))
                        break



def check_msc(inst, name, rep):
    import tempfile
    for rel in inst.glob(r'fighter/%s/script/msc/.*\.mscsb' % name):
        with tempfile.NamedTemporaryFile(suffix='.mscsb', delete=False) as f:
            f.write(inst.get(rel))
        r = subprocess.run([sys.executable, os.path.join(HERE, 'msc_stack_check.py'), f.name], capture_output=True, text=True)
        os.unlink(f.name)
        if r.returncode:
            last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()[-200:]
            rep.add('ERROR', 'C1 msc-stack', '%s: %s (msclang nested calls: Hero fix 11)' % (rel, last))
        hi = msc_max_global(inst.get(rel))
        if hi > MSC_GLOBALS_PROVEN:
            rep.add('WARN', 'C5 msc-globals', '%s: globals up to index 0x%X, past 0x%X, the most seen working in game: '
                    'Hero fix 79 / 80\'s Zoom 2 U, the only code past it (0x87-0x8A), stopped his MSC (likely the VM\'s '
                    'globals end there; not proven): reuse a global' % (rel, hi, MSC_GLOBALS_PROVEN))
    src = os.path.join(ROOT, 'fighters', name)
    check_joint_overrides(src, rep)
    for d, _ds, fs in os.walk(src):
        for f in fs:
            if not f.endswith('.c'):
                continue
            text = open(os.path.join(d, f), errors='replace').read()
            for m in re.finditer(r'PostureModuleF\(0x7\)', text):
                line = text.count('\n', 0, m.start()) + 1
                fn = re.findall(r'\n[A-Za-z_][\w ]*?\b(\w+)\([^;{}]*\)\s*\{', text[:m.start()])
                if fn and re.fullmatch(r'func_\d+', fn[-1]):
                    continue            # the base's decompiled code: its own use
                ctx = text[max(0, m.start() - 120):m.end() + 60]
                if re.search(r'lr|facing|turn|dir', ctx, re.I):
                    rep.add('WARN', 'C2 facing', '%s:%d: PostureModuleF(0x7) is the model scale, not the facing '
                            '(PostureModuleF(0)): Hero fix 68' % (os.path.relpath(os.path.join(d, f), ROOT), line))
    # C4 a speed set without the facing: kinetic energies are world X (+ = right on screen); the game's own
    # code multiplies by PostureModuleF(0) (Squirtle's Withdraw: pz_s_move set + speed, so it always slid right)
    for d, _ds, fs in os.walk(src):
        for f in fs:
            if not f.endswith('.c'):
                continue
            text = open(os.path.join(d, f), errors='replace').read()
            for m in re.finditer(r'\n(?:void|int|float) (\w+)\([^)]*\)\n\{(.*?)\n\}', text, re.S):
                fname, body = m.group(1), m.group(2)
                if re.fullmatch(r'func_\d+', fname):
                    continue
                for k in re.finditer(r'KineticModule\(0x11, (0x?[0-9a-f]+), ([^,)]+)', body):
                    energy, x = int(k.group(1), 0), k.group(2).strip()
                    if energy == 1 or x in ('0', '0.0f', '0.0'):
                        continue        # energy 1: gravity (Y)
                    if re.search(r'PostureModuleF\(0\)|\blr\b|facing', body):
                        continue        # turned by the facing
                    read = re.findall(r'(\w+) = [^;]*KineticModuleF', body)
                    if 'KineticModuleF' in x or any(re.search(r'\b%s\b' % v, x) for v in read):
                        continue        # a speed read back and scaled (roll-off)
                    line = text.count('\n', 0, m.start()) + 1
                    rep.add('WARN', 'C4 speed-facing', '%s:%d %s(): KineticModule(0x11, ..., %s) with no facing in sight: '
                            'world X, so it pushes right whichever way he faces (Squirtle\'s Withdraw)' % (
                                os.path.relpath(os.path.join(d, f), ROOT), line, fname, x))
    main_c = os.path.join(src, name + '.c')
    if os.path.exists(main_c):
        text = open(main_c, errors='replace').read()
        if 'rolloff' not in text.lower():
            rep.add('ERROR', 'C3 universal', '%s has no universal mechanics (tools/universal_mechanics.py: reverse tilts, '
                    'roll-off, tilts out of run)' % os.path.relpath(main_c, ROOT))
        elif 'rolloff_hold_update' not in text:
            rep.add('ERROR', 'C3 universal', '%s has the old roll-off momentum (the air speed cap back at Fall\'s end): '
                    'Hero\'s is the universal version (tools/universal_mechanics.py --upgrade, docs/universal-mechanics.md '
                    '"Roll-off" 6)' % os.path.relpath(main_c, ROOT))


def check_repo(name, kind, rep):
    k = open(os.path.join(ROOT, 'fighters/kirby/kirby.c'), errors='replace').read()
    m = re.search(r'int kirby_copy_trait\([^)]*\)\n\{(.*?)\n\}\n', k, re.S)
    if not m or not re.search(r'kind == (0x%x|%d)\)' % (kind, kind), m.group(1), re.I):
        rep.add('WARN', 'K1 kirby-trait', 'kirby_copy_trait() has no case for kind 0x%X (CLAUDE.md: ask for the trait)' % kind)
    t = open(os.path.join(ROOT, 'docs/character-traits.md'), errors='replace').read().lower()
    if name.lower() not in t:
        rep.add('WARN', 'K1 trait-doc', 'docs/character-traits.md doesn\'t list %s' % name)
    readme = os.path.join(ROOT, 'fighters', name, 'README.md')
    if not os.path.exists(readme):
        rep.add('WARN', 'K2 readme', 'no fighters/%s/README.md (sources of every value: CLAUDE.md)' % name)
    check_msc_effect_ids(name, rep)


def msc_effect_id_mismatches(c_text, ids):
    """(line, name, id in the C, id in the bank) for each `EffectModule(op, 0xID, ...); // name` whose name is in
    the bank's ids and gives another id"""
    out = []
    for m in re.finditer(r'EffectModule\(0x[0-9A-Fa-f]+, (0x[0-9A-Fa-f]+)[^;]*\);\s*//\s*(\S+)', c_text):
        want = ids.get(m.group(2))
        if want is not None and int(want, 0) != int(m.group(1), 0):
            out.append((c_text.count('\n', 0, m.start()) + 1, m.group(2), m.group(1), want))
    return out


def check_msc_effect_ids(name, rep):
    """E8: an effect id written into the fighter's MSC source (`EffectModule(..., 0xID, ...); // name`: Sephiroth's
    Flare charge off, test 60) against fighters/NAME/NAME_effects.json: adding effects to the bank renumbers the
    turned variants (and any common sets), and a stale id turns off nothing (or something else)"""
    c_path = os.path.join(ROOT, 'fighters', name, name + '.c')
    j_path = os.path.join(ROOT, 'fighters', name, name + '_effects.json')
    if not (os.path.exists(c_path) and os.path.exists(j_path)):
        return
    bad = msc_effect_id_mismatches(open(c_path, errors='replace').read(), json.load(open(j_path)))
    if bad:
        rep.add('ERROR', 'E8 msc-effect-id', '%d effect ids in fighters/%s/%s.c differ from %s_effects.json (rebuild the '
                'MSC): %s' % (len(bad), name, name, name, ', '.join('line %d %s %s -> %s' % b for b in bad[:6])))


def check_shield_damage(inst, name, rep):
    """S9: a hitbox's ShieldDamage (parameter 18) below 0. Ultimate gives magic negative shield damage (Hero's spells:
    -1 to -13, Sephiroth's flares and flash); Smash 4 takes the word unsigned, so 0xFFFFFFFF is a huge one: every
    hit breaks a shield (Hero, after Supamario fix 90). ERROR since the user's rule (CLAUDE.md: never negative in
    an Ultimate port; ultimate_acmd.py clamps to 0)"""
    bad = {}
    for rel in sorted(inst.files):
        if not (rel.startswith('fighter/%s/script/animcmd/' % name) and rel.endswith('/game.bin')):
            continue
        for h, cmds in (scripts(inst, rel) or {}).items():
            for c in cmds:
                if 'Hitbox' in c.name and len(c.params) > 18 and c.params[18] >= 1 << 31:
                    bad.setdefault(rel.split('/animcmd/')[1].rsplit('/', 1)[0], set()).add('%08X' % h)
    if bad:
        rep.add('ERROR', 'S9 shield-negative', 'negative ShieldDamage (a shield break every hit in Smash 4): ' +
                '; '.join('%s: %d scripts' % (k, len(v)) for k, v in sorted(bad.items())))


def check_weapons(name, rec, rep):
    """W1: a brand-new article copied from a base article with native per-frame code (port_bases.json
    weapon_nop2: Mario's fireball's life / bounce / wall puff) keeps that code unless its record turns
    those vtable 2 slots off (Squirtle v2-v5's water: a fireball's bounce, gone at close range)"""
    bases = json.load(open(os.path.join(ROOT, 'reference/port_bases.json')))
    want = bases.get(rec['base'], {}).get('weapon_nop2', {})
    for art, w in sorted(rec.get('weapons', {}).items()):
        if not isinstance(w, dict) or w.get('base') not in want:
            continue
        have = {int(x, 0) for x in w.get('nop2', [])}
        miss = [x for x in want[w['base']] if int(x, 0) not in have]
        if miss:
            rep.add('ERROR', 'W1 weapon-native', '%s (copy of %s): its base\'s native vtable 2 slots %s still run '
                    '(extra_kinds.json "nop2"; Squirtle\'s water v5)' % (art, w['base'], ', '.join(miss)))


# W8: a fighter's article instances in all: the base's own (its list's entries before the first special one) and the new
# articles' "max" counts. The ArticleModule's holder (0x11C bytes, made at 0x02C03458) keeps one pointer per instance at
# +0x10 - +0x10C: 64 at most; past that they overwrite its list count (+0x110) and list pointer (+0x114), and the next
# article lookup (0x02C057EC -> 0x02C0337C) reads through a null (Sephiroth test 123: Zelda's 9 + 64 new = 73)
ARTICLE_SLOTS = 64


def base_instances(base):
    """the base fighter's pooled article instances (vanilla build/cross_f.rpx), None if it can't be read"""
    try:
        import kind_expand as K
        import weapon_expand as W
        img = K.Image(os.path.join(ROOT, 'build', 'cross_f.rpx'))
        fd = W.fighter_descriptor(img, {'desc_from': base})
        al = img.w(fd + 8)
        ent, cnt = img.w(al), img.w(al + 4)
        rows = [(img.w(ent + 16 * i), img.w(ent + 16 * i + 4)) for i in range(cnt)]
        special = next((i for i, (k, _n) in enumerate(rows) if k & 0x80000000), cnt)
        return sum(n for _k, n in rows[:special])
    except Exception:
        return None


def check_weapon_instances(name, rec, rep):
    """W8: more than 64 article instances for one fighter: the ArticleModule holder's pointer array overflows into its
    list pointer and the game crashes loading the fighter (Sephiroth test 123)"""
    new = sum(int(w.get('max', 1)) for w in rec.get('weapons', {}).values() if isinstance(w, dict))
    base = base_instances(rec.get('base', ''))
    if base is None:
        if new > ARTICLE_SLOTS - 16:
            rep.add('WARN', 'W8 weapon-instances', '%d new-article instances and the base\'s unread: 64 in all at most '
                    '(the ArticleModule holder\'s slots)' % new)
        return
    if base + new > ARTICLE_SLOTS:
        rep.add('ERROR', 'W8 weapon-instances', '%d article instances in all (%s\'s %d + new %d, extra_kinds.json '
                '"max"): 64 at most, past that the game crashes loading him (Sephiroth test 123)' % (
                    base + new, rec.get('base'), base, new))
        return
    # the other side: an article past its own "max" isn't made (no crash, nothing drawn or hit: Sephiroth test 127's
    # trail, 12, all held by the kept Blade Dash lines, so Octaslash's line and shape glow weren't made); the counts
    # shown so a "max" set tight can be raised while there's room
    rep.add('INFO', 'W8 weapon-instances', '%d of 64 article instances (%s\'s %d + new %d: %s); %d free. An article '
            'past its "max" is silently not made' % (base + new, rec.get('base'), base, new, ', '.join(
                '%s %s' % (k, w.get('max', 1)) for k, w in rec.get('weapons', {}).items() if isinstance(w, dict)),
            ARTICLE_SLOTS - base - new))


# W11: the animation heap (22 MiB, one for the match: tools/effect_heap_patch.py's ANIM_GETTER) holds every model
# instance's motion objects and per-bone arrays; a model-bearing article (weapon flag 0x40: extra_kinds.json
# "flags_set", or a native copy with a model folder) gets them for every pooled instance as the fighter loads, and a
# failed allocation is an assert (`twu`): Cemu parks the thread, the match never starts, no crash log. exe_v10 (22 MiB):
# two Sephiroths hung at the second's 17th trail, i.e. with his own model articles all loaded once (MODEL_FAIL_FULL)
# plus the second's phantom, snakes, point and 16 trails (MODEL_FAIL_PART) (multi-instance bugs v3).
ANIM_HEAP_MIB = 22
MODEL_FAIL_FULL = {'phantom': 1, 'snake': 12, 'snaketip': 1, 'trail': 24, 'fill': 3}
MODEL_FAIL_PART = {'phantom': 1, 'snake': 12, 'snaketip': 1, 'trail': 16}


def vbn_bones(data):
    """a model.vbn's bone count (' NBV' little-endian / 'VBN ' big-endian), None if it isn't one"""
    if data[:4] == b' NBV':
        return struct.unpack('<I', data[8:12])[0]
    if data[:4] == b'VBN ':
        return struct.unpack('>I', data[8:12])[0]
    return None


def model_articles(inst, name, rec):
    """{article: (pooled instances, bones)} for the fighter's new model-bearing articles (bones from the install's
    model/<article>/c00/model.vbn; None when it isn't there)"""
    out = {}
    for art, w in sorted(rec.get('weapons', {}).items()):
        path = 'fighter/%s/model/%s/c00/model.vbn' % (name, art)
        if isinstance(w, dict):
            if not int(w.get('flags_set', '0'), 0) & 0x40:
                continue
            n = int(w.get('max', 1))
        elif path in inst.files:
            n = 1                                 # a native copy (its own kind number, the base's list entry: 1)
        else:
            continue
        out[art] = (n, vbn_bones(inst.get(path)) if path in inst.files else None)
    return out


def check_weapon_models(inst, name, rec, rep):
    """W11: model-bearing article instances against the animation heap (exe_v10's 22 MiB: two Sephiroths hung at
    load; tools/effect_heap_patch.py ANIM_GROW_MIB). Counted in bone-instances (an instance's per-bone arrays are
    most of its cost: 0x036B34A0 bones x 64, 0x036B8040 x 16 and x 0x88 ...), calibrated on what loaded on exe_v10
    before the hang; the budget for a bigger heap scales it with the heap (an estimate: the fighters' and stage's own
    share of the heap is unknown, so it assumes everything grows alike)"""
    import tempfile
    import effect_heap_patch
    import kind_expand as K
    arts = model_articles(inst, name, rec)
    if not arts:
        return
    unknown = sorted(a for a, (_n, b) in arts.items() if b is None)
    bones = {a: (b if b is not None else 8) for a, (_n, b) in arts.items()}
    load = sum(n * bones[a] for a, (n, _b) in arts.items())
    inst_n = sum(n for n, _b in arts.values())
    heap = None
    if 'code/cross_f.rpx' in inst.files:
        with tempfile.NamedTemporaryFile(suffix='.rpx') as f:
            f.write(inst.get('code/cross_f.rpx'))
            f.flush()
            img = K.Image(f.name)
            heap = (img.w(effect_heap_patch.ANIM_GETTER) & 0xFFFF) / 16.0      # lis r3, N: N x 64 KiB
    edge = record('edge')
    e_arts = model_articles(inst, 'edge', edge) if name == 'edge' else {}
    e_bones = {a: b for a, (_n, b) in e_arts.items() if b is not None}
    if set(e_bones) >= set(MODEL_FAIL_FULL):
        fail = sum(MODEL_FAIL_FULL[a] * e_bones[a] + MODEL_FAIL_PART.get(a, 0) * e_bones[a] for a in MODEL_FAIL_FULL)
    else:
        fail = 2133                               # Sephiroth's install of multi-instance bugs v3 (49-bone trails)
    budget = fail * (heap or ANIM_HEAP_MIB) / ANIM_HEAP_MIB
    what = '%d model-bearing article instances, %d bone-instances (%s)%s' % (
        inst_n, load, ', '.join('%s %d x %s' % (a, n, b if b is not None else '?') for a, (n, b) in arts.items()),
        ' (no model.vbn for %s: 8 bones assumed)' % ', '.join(unknown) if unknown else '')
    heap_s = '%g MiB animation heap' % heap if heap else 'the executable not in the install (22 MiB assumed)'
    if 2 * load > budget:
        rep.add('ERROR' if (heap or ANIM_HEAP_MIB) <= ANIM_HEAP_MIB else 'WARN', 'W11 weapon-models',
                '%s: two of him need ~%d of ~%d bone-instances the %s holds for articles (exe_v10, 22 MiB: two '
                'Sephiroths hung at load at %d); tools/effect_heap_patch.py ANIM_GROW_MIB or fewer / smaller model '
                'articles' % (what, 2 * load, budget, heap_s, fail))
    elif 4 * load > budget:
        rep.add('WARN', 'W11 weapon-models', '%s: four of him (4-player) need ~%d of ~%d bone-instances in the %s '
                '(estimate scaled from exe_v10\'s hang at %d on 22 MiB); two fit' % (what, 4 * load, budget, heap_s,
                                                                                    fail))
    else:
        rep.add('INFO', 'W11 weapon-models', '%s: four of him ~%d of ~%d bone-instances (%s)' % (
            what, 4 * load, budget, heap_s))


def check_weapon_statuses(name, rep):
    """W2: a weapon MSC (fighters/NAME/weapons/*.c, built on a vanilla weapon's MSC) registering a status at or past
    its status count (global7, set in its setup): the scaffold's status change refuses it ("g_status_kind_next >=
    g_status_kind_max") and the weapon stays where it was (Sephiroth test 64: Shadow Flare's shot never became its
    orbs, global7 2 copied from the Flare's MSC with statuses up to 4)"""
    for path in sorted(glob.glob(os.path.join(ROOT, 'fighters', name, 'weapons', '*.c'))):
        text = open(path, errors='replace').read()
        counts = [int(m, 0) for m in re.findall(r'\n    global7 = (0x[0-9a-fA-F]+|\d+);', text)]
        regs = [int(m, 0) for m in re.findall(r'sv_set_mem\(0x1, (?:0x)?[0-9a-fA-F]+, (0x[0-9a-fA-F]+|\d+), ', text)]
        if not counts or not regs:
            continue
        if max(regs) >= counts[-1]:
            rep.add('ERROR', 'W2 weapon-status-max', '%s: statuses up to %d registered, global7 (the status count) %d: '
                    'the higher ones are refused' % (os.path.relpath(path, ROOT), max(regs), counts[-1]))


def check_weapon_rehit(inst, name, rec, rep):
    """W3: a brand-new article whose hitboxes re-hit (Rehit > 0) without "on_hit" in its record: the base weapon's hit
    method removes it at its first hit, so its multi-hit (and its following effects) end there (Sephiroth test 64:
    Scintilla's flash, rehit 5, hit once)"""
    import acmd
    hb = ('Special_Hitbox', 'Extended_Special_Hitbox')
    for art, w in sorted(rec.get('weapons', {}).items()):
        if not isinstance(w, dict) or 'on_hit' in w:
            continue
        data = inst.get('fighter/%s/script/animcmd/weapon/%s/game.bin' % (name, art))
        if not data:
            continue
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.bin') as f:
            f.write(data)
            f.flush()
            try:
                scripts = acmd.ACMDFile.load(f.name).scripts
            except SystemExit:
                continue
        if any(c.name in hb and len(c.params) > 31 and c.params[31] for s in scripts.values() for c in s):
            rep.add('WARN', 'W3 weapon-rehit', '%s: re-hitting hitboxes but no "on_hit" in its extra_kinds.json record: '
                    'the base\'s hit method removes it at its first hit ("on_hit": its own status, e.g. 0 to stay)' % art)


def check_weapon_shield(rec, rep):
    """W12: a brand-new article with its own hit method ("on_hit") whose "on_hit_bits" lack the shield result (0x4): a
    shield the attack meets goes to the base's method, which removes the weapon at once (Sephiroth test 148, the user:
    Flare and its variants "instantly disappear on shield" instead of playing out their hitboxes, the snake sword's tip
    "disappear[s] when being shielded"; Supamario fix 89's Kamehameha before it). WARN for one that stays in its status
    on a hit ("on_hit": 0: it is meant to outlive its hits); INFO for one that changes status on a hit (a shield skips
    that status: an explosion, its orbs), unless its record says "shield_removes": true (meant). 0x17 keeps it"""
    import weapon_expand
    for art, w in sorted(rec.get('weapons', {}).items()):
        if not isinstance(w, dict) or 'on_hit' not in w or w.get('shield_removes'):
            continue
        bits = int(str(w.get('on_hit_bits', weapon_expand.HIT_BITS)), 0)
        if bits & 0x4:
            continue
        if int(w['on_hit']) == 0:
            rep.add('WARN', 'W12 weapon-shield', '%s: "on_hit" 0 (it stays through its hits) but no shield bit in '
                    '"on_hit_bits" (0x%X): a shield removes it at once ("on_hit_bits": "0x17")' % (art, bits))
        else:
            rep.add('INFO', 'W12 weapon-shield', '%s: a shield removes it without its status %d ("on_hit_bits": "0x17" '
                    'for it, "shield_removes": true if meant)' % (art, int(w['on_hit'])))


# hitbox ids / Parts (hit-record groups) a base weapon's AttackModule has: its kind's set-up method fills the module
# parameters (accessor init 0x02BCBD84 -> per-kind object, vt +0xC; +0xDC ids, +0xEC parts). The module never checks
# a hitbox's id or Part against them: past the end it writes over other memory and crashes on the hit.
WEAPON_ATTACK_SLOTS = {'dein': (7, 2),    # dein: 0x032107B4 (Sephiroth bisect 70: Shadow Flare's orbs on Parts 2-4)
                       'lightingbowarrow': (7, 2)}    # its singleton's vt +0xC is the same 0x032107B4


def check_weapon_parts(inst, name, rec, rep):
    """W4: a new article's hitbox with an id or Part its base weapon's AttackModule hasn't got (WEAPON_ATTACK_SLOTS):
    the hit writes past the module's arrays and the game crashes when it connects (Sephiroth bisect 70)"""
    import acmd
    import tempfile
    for art, w in sorted(rec.get('weapons', {}).items()):
        slots = WEAPON_ATTACK_SLOTS.get(w.get('base')) if isinstance(w, dict) else None
        data = inst.get('fighter/%s/script/animcmd/weapon/%s/game.bin' % (name, art)) if slots else None
        if not data:
            continue
        with tempfile.NamedTemporaryFile(suffix='.bin') as f:
            f.write(data)
            f.flush()
            try:
                scripts = acmd.ACMDFile.load(f.name).scripts
            except SystemExit:
                continue
        bad = set()
        for s in scripts.values():
            for c in s:
                syn = acmd.INFO.get(c.ident, {}).get('syntax') or []
                if 'Hitbox' in c.name and syn[:2] == ['ID', 'Part'] and len(c.params) > 1:
                    if not 0 <= c.params[0] < slots[0] or not 0 <= c.params[1] < slots[1]:
                        bad.add('ID %d Part %d' % (c.params[0], c.params[1]))
        if bad:
            rep.add('ERROR', 'W4 weapon-parts', '%s: hitboxes past its base %s\'s AttackModule (ids 0-%d, Parts 0-%d): %s; '
                    'the hit writes past its arrays and the game crashes when it connects' % (
                        art, w['base'], slots[0] - 1, slots[1] - 1, ', '.join(sorted(bad))))


# the weapon module set-up (0x02BCB5C0): a kind's row of 28 constructors (weapon_expand.MODULE_TABLE); slot 7 makes the
# MotionModule (accessor +0x44), and a kind without one ("li r3, 0; blr") never runs its ACMD (scripts follow the motion)
MOTION_SLOT = 7


def lst_redirects(pac):
    """the motions a material_anime pac's material_anime.lst sends elsewhere though the pac has their own entry"""
    import tempfile
    import omo
    from ultimate_fighter import lst_hash, lst_read
    with tempfile.NamedTemporaryFile(suffix='.pac') as f:
        f.write(pac)
        f.flush()
        ents = dict(omo.pac_read(f.name))
    lst = ents.get('material_anime.lst')
    if not lst or lst[:4] != b'MTAL':
        return []
    own = {lst_hash(n[:-4]): n[:-4] for n in ents if n.endswith('.mta')}
    return [own[e[0]] for e in lst_read(lst) if e[0] in own]


def check_weapon_msc(inst, name, rec, vanilla, rep):
    """W14: a new article copied from a base weapon whose behaviour is in an MSC of its own (vanilla
    fighter/<base>/script/msc/<weapon>/<weapon>.mscsb: ZSS's Paralyzer shot flies, times out and picks its motion
    there) shipped without one: made with no status, it never moves, hits or draws (Byleth v1-v3: "Neutral special
    also never fires its projectile")"""
    if not vanilla:
        return
    for art, w in sorted(rec.get('weapons', {}).items()):
        if not isinstance(w, dict) or 'base' not in w:
            continue
        src = os.path.join(vanilla, 'fighter', rec['base'], 'script/msc', w['base'], w['base'] + '.mscsb')
        if not os.path.exists(src):
            continue
        if not inst.get('fighter/%s/script/msc/%s/%s.mscsb' % (name, art, art)):
            rep.add('ERROR', 'W14 weapon-msc', '%s (copy of %s): no script/msc/%s/%s.mscsb, and its base\'s behaviour '
                    'is in its MSC: the article never acts' % (art, w['base'], art, art))


def check_portraits(inst, name, rep):
    """U1: a later package replacing a portrait an earlier one shipped with different art (Byleth v3 / v4 shipped
    chr_00 / chr_10 made on the vanilla stand-in templates over the user-file build's: his select-screen icon was a
    rectangular close-up spilling out of its hexagon, user v4). U2: a stock icon with almost nothing drawn (v1-v4's
    stock_90: 42 of 4096 pixels, Ultimate's chara_2 fitted into a 6 px head box)"""
    import tempfile
    sys.path.insert(0, HERE)
    import nut
    for rel, olds in sorted(inst.earlier.items()):
        if not rel.startswith('ui/replace/'):
            continue
        new = inst.get(rel)
        if all(load() != new for load, _pkg in olds):     # art no earlier package had
            rep.add('WARN', 'U1 portrait-replaced', '%s: %s\'s replaced by %s\'s (different art: is the later one '
                    'built on the user\'s templates?)' % (rel, olds[-1][1], inst.where(rel)))
    for rel in inst.glob(r'ui/replace/chr/stock_90/stock_90_[^/]+\.nut'):
        data = inst.get(rel)
        with tempfile.NamedTemporaryFile(suffix='.nut') as f:
            f.write(data)
            f.flush()
            try:
                d, ts = nut.load(f.name)
                a = nut.decode(d, ts[0])
            except Exception:
                continue
        drawn = float((a[..., 3] > 127).mean())
        if drawn < 0.15:
            rep.add('ERROR', 'U2 stock-icon', '%s: only %.1f %% of the icon drawn (a shrunk icon: '
                    'ultimate_portraits.py\'s stock fit)' % (rel, 100 * drawn))


def check_weapon_motion(inst, name, rec, rep):
    """W5: a new article whose base weapon kind has no MotionModule (its module row's slot 7 a null constructor: Zelda's
    light arrow) and no "modules" giving it one, with commands in its ACMD: its scripts never run, so no hitbox, no
    effect (Sephiroth test 82: the held forward air's point had no hitbox and no trail)"""
    import acmd
    import tempfile
    rpx = os.path.join(ROOT, 'build', 'cross_f.rpx')
    if not os.path.exists(rpx):
        rep.add('NOTE', 'W5 weapon-motion', 'no build/cross_f.rpx: the bases\' module rows not checked')
        return
    sys.path.insert(0, HERE)
    import kind_expand as K
    import weapon_expand as W
    img = K.Image(rpx)
    owner = [img.cstr(img.w(0x10418FF0 + 4 * k)) for k in range(W.OLD_N)]
    names = [img.cstr(img.w(0x10419604 + 4 * k)) for k in range(W.OLD_N)]
    for art, w in sorted(rec.get('weapons', {}).items()):
        if not isinstance(w, dict) or MOTION_SLOT in [int(s) for s in w.get('modules', {}).get('slots', [])]:
            continue
        kinds = [k for k in range(W.OLD_N) if owner[k] == rec['base'] and names[k] == w['base']]
        if not kinds:
            continue
        ctor = img.w(W.MODULE_TABLE + 0x70 * kinds[0] + 4 * MOTION_SLOT)
        if img.w(ctor) != 0x38600000:          # li r3, 0: no module
            continue
        used = []
        for fn in ('game', 'effect', 'sound'):
            data = inst.get('fighter/%s/script/animcmd/weapon/%s/%s.bin' % (name, art, fn))
            if not data:
                continue
            with tempfile.NamedTemporaryFile(suffix='.bin') as f:
                f.write(data)
                f.flush()
                try:
                    scripts = acmd.ACMDFile.load(f.name).scripts
                except SystemExit:
                    continue
            if any(c.ident != acmd.END for s in scripts.values() for c in s):
                used.append(fn)
        if used:
            rep.add('ERROR', 'W5 weapon-motion', '%s (copy of %s): its base kind has no MotionModule, so its %s scripts '
                    'never run; give it one (extra_kinds.json "modules": {"from": "dein", "slots": [%d]})' % (
                        art, w['base'], ' / '.join(used), MOTION_SLOT))


def check_weapon_facing(name, rep):
    """W6: a weapon MSC (fighters/NAME/weapons/*.c) that turns itself (PostureModule 0x2717) and never sets its facing
    (PostureModule(0, lr)): a fighter it hits takes its facing, and with none it is left facing the camera (Sephiroth
    test 83: the held forward air's point)"""
    for path in sorted(glob.glob(os.path.join(ROOT, 'fighters', name, 'weapons', '*.c'))):
        text = open(path, errors='replace').read()
        if 'PostureModule(0x2717,' in text and not re.search(r'PostureModule\(0, ', text):
            rep.add('WARN', 'W6 weapon-facing', '%s: turns itself (PostureModule 0x2717) but never sets its facing '
                    '(PostureModule(0, lr)): fighters it hits are left facing the camera' % os.path.relpath(path, ROOT))


def check_weapon_joint_facing(name, rep):
    """W9: a weapon MSC that moves its model's joints (ModelModule(0x7, ...)) and sets its facing to a constant
    (PostureModule(0, 1.0f)): that doesn't turn its model (made facing left, it stays drawn mirrored), so joint offsets
    meant in world X come out the wrong way (Sephiroth test 127, the user: up special's line "goes the wrong way if the
    move was turned after the start"); keep the facing it was made with (PostureModuleF(0)) and multiply the X offsets
    by it"""
    for path in sorted(glob.glob(os.path.join(ROOT, 'fighters', name, 'weapons', '*.c'))):
        text = open(path, errors='replace').read()
        own = text.split("// ---- ", 1)[-1] if "// ---- " in text else text   # its own code, not the base's
        if 'ModelModule(0x7,' in own and re.search(r'PostureModule\(0, -?[0-9.]+f?\)', own):
            rep.add('WARN', 'W9 weapon-joint-facing', '%s: moves its joints and sets a constant facing '
                    '(PostureModule(0, 1.0f)): its model isn\'t turned by it, so world-X joint offsets come out '
                    'mirrored when made facing left; use its facing as made (PostureModuleF(0)) on the X offsets'
                    % os.path.relpath(path, ROOT))


def check_grab_status(name, rep):
    """C8: a hand-written MSC function (any not named func_N, the decompiler's) of the fighter's that changes to status
    0x37: that's the dash grab (CatchDash); the standing grab is 0x35 (Catch, as Wait's own func_46 / the ground
    statuses' checks: 0x35 0x1E00006D, 0x37 0x1E00006E, 0x39 the pivot grab). Sephiroth tests 128 / 129: the snake
    sword's grab cancel used 0x37 (the user: "The snakesword cancel does dash grab rather than a normal grab")"""
    path = os.path.join(ROOT, 'fighters', name, '%s.c' % name)
    if not os.path.exists(path):
        return
    fn = None
    for i, line in enumerate(open(path, errors='replace'), 1):
        m = re.match(r'(?:void|int|float)\s+(\w+)\s*\(', line)
        if m:
            fn = m.group(1)
        if fn and not re.match(r'func_\d+$', fn) and re.search(r'func_16\(0x37,', line):
            rep.add('WARN', 'C8 grab-status', 'fighters/%s/%s.c:%d %s(): status 0x37 is the dash grab (CatchDash); '
                    'a standing grab is 0x35 (Catch)' % (name, name, i, fn))


def check_weapon_owner(inst, name, rec, rep):
    """W7: a weapon MSC written for an article (fighters/NAME/weapons/X.c, shipped as script/msc/X/X.mscsb; helper
    files compiled into others' aren't) that isn't one of
    the fighter's own weapon kinds (extra_kinds.json "weapons"): a weapon's files load by its kind's owner, so the
    base fighter's own kinds read the base's folder and the script is never used (Sephiroth tests 106-110: Zelda's
    Phantom, still her kind, read fighter/zelda/; its tracking never ran)"""
    own = set((rec.get('weapons') or {}).keys())
    d = os.path.join(ROOT, 'fighters', name, 'weapons')
    if not os.path.isdir(d):
        return
    for f in sorted(os.listdir(d)):
        if f.endswith('.c') and f[:-2] not in own and \
                list(inst.glob(r'fighter/%s/script/msc/%s/%s\.mscsb' % (name, f[:-2], f[:-2]))):
            rep.add('ERROR', 'W7 weapon-owner', 'fighters/%s/weapons/%s: "%s" isn\'t one of %s\'s own weapon kinds '
                    '(extra_kinds.json "weapons"): the game loads the base\'s scripts for it; give it a kind of its own '
                    '(a plain "%s": "0x..." entry replaces the base\'s article)' % (name, f, f[:-2], name, f[:-2]))


def check_weapon_custom_clamp(inst, name, rec, rep):
    """X4: the new weapon kinds' param getters (tools/weapon_expand.py getter copies) without the custom-number clamp:
    a weapon's custom number (its init block +0x5C, the owner's custom slot) picks its param block as vector data +
    custom x entry size with no bound, and the vl vectors hold 4 entries (custom 0-3); a port passing more (Hero's
    Whack / Thwack: level + 4 x his player slot) bound the weapon to what followed the vector: P2's never appeared
    (multi-instance bugs v1). Read from the install's executable: every getter copy reading this fighter's vl slot
    and indexing by the custom number (r4) must hold the clamp (weapon_expand.CLAMP_SIGNATURE)"""
    import tempfile
    import kind_expand as K
    import weapon_expand as W
    if 'code/cross_f.rpx' not in inst.files or not rec.get('weapons'):
        return
    fcap, _kinds = K.load_spec(W.SPEC)
    slot = K.mgr_layout(fcap)[0]['vl'][1] + 4 * int(rec['kind'], 0)
    with tempfile.NamedTemporaryFile(suffix='.rpx') as f:
        f.write(inst.get('code/cross_f.rpx'))
        f.flush()
        img = K.Image(f.name)
        try:
            words = [img.w(a) for a in range(W.CAVE, W.LIMIT, 4)]
        except KeyError:
            return
    bad, good = [], 0
    for i, w in enumerate(words):
        if w != 0x3D801030 or i + 1 >= len(words) or words[i + 1] != 0x818CF448:     # lis r12 / lwz r12, -0xBB8(r12)
            continue
        body = []
        for x in words[i + 2:i + 26]:
            body.append(x)
            if x == 0x4E800020:
                break
        if not any(x >> 26 == 32 and (x & 0xFFFF) == slot for x in body):
            continue
        reads_r4 = any((x >> 26 == 7 and (x >> 16) & 31 == 4) or (x >> 26 == 21 and (x >> 21) & 31 == 4) for x in body)
        if not reads_r4:
            continue
        if W.CLAMP_SIGNATURE in body:
            good += 1
        else:
            bad.append('0x%08X' % (W.CAVE + 4 * i))
    if bad:
        rep.add('ERROR', 'X4 weapon-custom', 'code/cross_f.rpx: %d of %s\'s weapon param getters index their vl vector '
                'by the custom number with no bound (%s): a custom number past 3 binds the weapon to the memory after '
                'the vector (Hero\'s Whack / Thwack for P2 and later never appeared); rebuild with the current '
                'tools/weapon_expand.py (CUSTOM_CLAMP)' % (len(bad), name, ', '.join(bad[:6])))


def check_weapon_kind_compares(inst, name, rep):
    """X5: the base fighter's native code comparing an article's kind with the base kind (weapon category, then
    `cmpwi r3, K`) where this fighter's copy has another number: never matched. Zelda's article event (0x02F97A40)
    kills her Phantom's endless alarm on her hand only for kind 0x26: Sephiroth's Phantom (0x19B) left a purple glow
    at his hand after every release (multi-instance bugs v2). tools/weapon_expand.py kind_compares sends each such
    compare through a stub that takes the copies too; this lists the ones still plain in the install's executable"""
    import tempfile
    import kind_expand as K
    import weapon_expand as W
    if 'code/cross_f.rpx' not in inst.files or not os.path.exists(W.RPX):
        return
    try:
        _B, info = W.build()
    except Exception:                     # noqa: BLE001
        return
    mine = {nk: bk for nk, (bk, r, _a) in info['new'].items() if r['name'] == name}
    if not mine:
        return
    with tempfile.NamedTemporaryFile(suffix='.rpx') as f:
        f.write(inst.get('code/cross_f.rpx'))
        f.flush()
        img = K.Image(f.name)
        left = W.kind_compare_sites(img, set(mine.values()))
    if left:
        rep.add('ERROR', 'X5 weapon-kind-compare', 'code/cross_f.rpx: the base\'s native code compares an article\'s '
                'kind with %s, which %s\'s copies (%s) never match (Sephiroth\'s Phantom: Zelda\'s alarm glow left on '
                'his hand); rebuild with the current tools/weapon_expand.py (kind_compares)' % (
                    ', '.join('0x%X at 0x%08X' % (k, a) for a, _w, k in left), name,
                    ', '.join('0x%X' % nk for nk, bk in sorted(mine.items()) if bk in {k for _a, _w, k in left})))


def check_weapon_custom_source(name, rep):
    """W10: a fighter's MSC putting a player slot into a weapon's custom number (its custom slot int 0x10000048-4B
    around a generate: level + 4 x slot). The executable keeps the param block within the 4 entries (X4), but the base
    weapon's native code may index other per-custom tables by it (Robin's Thunder's motion names, 0x031DDBA4: 4
    entries): keep the custom number 0-3 and find the owner's slot in the article (Hero's shot.c sh_find_owner)"""
    src = os.path.join(ROOT, 'fighters', name, name + '.c')
    if not os.path.exists(src):
        return
    text = open(src).read()
    gens = set()
    for m in re.finditer(r'\n\w+ (\w+)\(int (\w+), int (\w+)\)\s*\{(.*?)\n\}', text, re.S):
        if re.search(r'WorkModule\(0x7, %s, 0x1000004[89ab]\)' % re.escape(m.group(3)), m.group(4)):
            gens.add(m.group(1))
    hits = []
    for g in sorted(gens):
        for m in re.finditer(r'\b%s\(([^;]*)\);' % re.escape(g), text):
            if re.search(r'slot', m.group(1)) and re.search(r'[*+]', m.group(1)):     # a slot worked into it (not a
                                                                                    # saved custom slot put back)
                hits.append('%d: %s(%s)' % (text.count('\n', 0, m.start()) + 1, g, m.group(1)))
    for m in re.finditer(r'WorkModule\(0x7, ([^;]*slot[^;]*[*+][^;]*|[^;]*[*+][^;]*slot[^;]*), 0x1000004[89ab]\);', text):
        hits.append('%d: %s' % (text.count('\n', 0, m.start()) + 1, m.group(0)))
    if hits:
        # an ERROR since Kirby's Hero copy fix v4: confirmed in game three times (Hero's P2 Whack, multi-instance
        # bugs v1; Kirby's Hero-copy projectiles drawn invisible, Kirby fix v2; Hero's Magic Burst from any slot but
        # P1's never made, Kirby fix v4)
        rep.add('ERROR', 'W10 weapon-custom', 'fighters/%s/%s.c: a player slot in a weapon\'s custom number (%s): past 3 '
                'it reads the base weapon\'s per-custom data past its 4 entries (Hero\'s Whack / Thwack for P2, '
                'multi-instance bugs v1; his Magic Burst past P1, Kirby fix v4): keep it 0-3 and carry the slot another '
                'way (find the caster in the article: weapons/shot.c, placed.c pl_marked_hero)' % (name, name, '; '.join(hits[:4])))


LEAK_SPAN = 60      # E12: a following effect whose particles last this long after it starts outlives a cut-short move


def check_body_effect_leaks(inst, name, rec, rep):
    """E12: a following effect of the port's own bank started by a body effect script that outlives the move: its
    emitters never stop (end frame / life 0x7FFFFFFF) or its particles last LEAK_SPAN frames or more (start + emission
    + life), and the fighter's MSC (fighters/NAME/NAME.c) never kills it (EffectModule(0x2723, id)). Smash 4 doesn't
    end a following effect at a motion or status change (Byleth v7, user: Failnaught's charge glow master_bow_hold2,
    100-frame particles, "continues into other actions if the special button is held"; its Terminate at the draw's
    frame 118 never ran when he shot earlier): Ultimate removes the article carrying it or its status's end does.
    ERROR when no script ends it either, WARN when only its script does (a hit, a grab or a cancel skips that frame)"""
    import efc
    import ptcl
    kind = int(rec['kind'], 0)
    p = sorted(inst.glob(r'fighter/%s/effect/%s/[^/]+\.ptcl' % (name, name)))
    e = sorted(inst.glob(r'fighter/%s/effect/%s/[^/]+\.efc' % (name, name)))
    eff = scripts(inst, 'fighter/%s/script/animcmd/body/effect.bin' % name)
    if not (p and e and eff):
        return
    pt, ef = ptcl.Ptcl(inst.get(p[0])), efc.Efc(inst.get(e[0]))

    def span(fx):
        i = fx & 0xFFFF
        if fx >> 16 != 0x300 + kind or i >= len(ef.entries) or not ef.entries[i][1]:
            return 0
        best = 0
        for em in pt.sets[ef.entries[i][1] - 1]['emitters']:
            d = em['data']
            if d is None:
                continue
            end_, life = pt.field(d, 'end_frame'), pt.field(d, 'ptcl_life')
            if end_ >= 0x7FFFFFFF or life >= 0x7FFFFFFF:
                return 1 << 30
            best = max(best, pt.field(d, 'start_frame') + end_ + life)
        return best
    msc = os.path.join(ROOT, 'fighters', name, name + '.c')
    killed = set()
    if os.path.exists(msc):
        killed = {int(x, 16) for x in re.findall(r'EffectModule\(0x2723, (0x[0-9a-fA-F]+)', open(msc).read())}
    follow = ('External_Graphic', 'EFFECT_FLW_POS')
    bad, soft = {}, {}
    for h, cmds in eff.items():
        started, ended = set(), set()
        for c in cmds:
            if not c.params or not isinstance(c.params[0], int):
                continue
            if c.name in follow or c.name.startswith('EFFECT_FOLLOW'):
                started.add(c.params[0])
            elif c.name in ('Terminate_Graphic_Effect', 'EFFECT_DETACH_KIND'):
                ended.add(c.params[0])            # (detached: it no longer follows)
        for fx in started - killed:
            if span(fx) >= LEAK_SPAN:
                (soft if fx in ended else bad).setdefault(fx, set()).add(h)
    fmt = lambda d: ', '.join('0x%07X (%d scripts)' % (fx, len(hs)) for fx, hs in sorted(d.items()))  # noqa: E731
    if bad:
        rep.add('ERROR', 'E12 effect-leak', 'following effects that outlive their move and nothing ends (no script, no '
                'EffectModule(0x2723) in %s.c): %s' % (name, fmt(bad)))
    if soft:
        rep.add('WARN', 'E12 effect-leak', 'following effects that outlive their move, ended only at a frame of their '
                'script (a hit, a grab or a cancel skips it; kill them in the MSC at the status change): %s' % fmt(soft))


def check_msc_effect_leaks(inst, name, rec, rep):
    """E15 msc-effect-leak: an effect of the port's own bank started from the fighter's MSC (EffectModule 0x2710 /
    0x2711 / 0x2717, or a helper called with the id) whose emitters never stop (end frame or life 0x7FFFFFFF), with no
    EffectModule(0x2723, id) anywhere in the MSC: a non-following effect from MSC isn't ended by any motion or status
    change, it stays where it was put for good. Byleth v12: master_wire_wind2 (Ultimate's sword wind on the tip, its
    3 emitters endless) placed at the caught fighter: user v12 "an effect persists through the move and never
    disappears" (a red wisp left in the air, clip 42cb0c57 at 3.3 - 4.3 s). ERROR"""
    import efc
    import ptcl
    kind = int(rec['kind'], 0)
    msc = os.path.join(ROOT, 'fighters', name, name + '.c')
    p = sorted(inst.glob(r'fighter/%s/effect/%s/[^/]+\.ptcl' % (name, name)))
    e = sorted(inst.glob(r'fighter/%s/effect/%s/[^/]+\.efc' % (name, name)))
    if not (p and e and os.path.exists(msc)):
        return
    pt, ef = ptcl.Ptcl(inst.get(p[0])), efc.Efc(inst.get(e[0]))
    src = re.sub(r'//[^\n]*', '', open(msc, errors='replace').read())
    own = r'0x%X[0-9a-fA-F]{4}' % (0x300 + kind)
    killed = {int(x, 16) for x in re.findall(r'EffectModule\(0x2723, (%s)' % own, src)}
    started = {int(x, 16) for x in re.findall(r'EffectModule\(0x27(?:10|11|17), (%s)' % own, src)}
    started |= {int(x, 16) for f, x in re.findall(r'\b(\w+)\((%s)\b' % own, src) if f != 'EffectModule'}
    bad = []
    for fx in sorted(started - killed):
        i = fx & 0xFFFF
        if i >= len(ef.entries) or not ef.entries[i][1]:
            continue
        for em in pt.sets[ef.entries[i][1] - 1]['emitters']:
            d = em['data']
            if d is not None and (pt.field(d, 'end_frame') >= 0x7FFFFFFF or pt.field(d, 'ptcl_life') >= 0x7FFFFFFF):
                bad.append('0x%07X' % fx)
                break
    if bad:
        rep.add('ERROR', 'E15 msc-effect-leak', '%s.c starts effects whose emitters never stop and never kills them '
                '(EffectModule(0x2723, id) at the move\'s end and on every way out): %s' % (name, ', '.join(bad)))


# W15: a new weapon's hitbox stepping farther a frame than this many of its radii skips fighters between frames
STEP_RADII = 15
# its speed params in the port's vl, by the base weapon (fighter_param_vl names): the paralyzer shot's uncharged /
# charged speed
WEAPON_SPEED = {'paralyzer_bullet': ('0x02000000', '0x02000001')}


def check_weapon_step(inst, name, rec, rep):
    """W15: a new article copied from a moving base weapon (WEAPON_SPEED) whose speed in the port's vl is more than
    STEP_RADII radii of its smallest plain hitbox (a capsule covers the step when it is at least that long): it jumps
    over fighters between frames (Byleth v7's max arrow: 75 a frame, radius 1.2, user: "no hitbox"). The base's speeds
    are one param block its copies share (which one a copy flies at is the base's native code's choice): all checked"""
    import fighter_param_vl as V
    vl = inst.get('param/fighter/fighter_param_vl_%s.bin' % name)
    if not vl:
        return
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.bin') as f:
        f.write(vl)
        f.flush()
        try:
            vf = V.load(f.name, rec['base'])
        except Exception:                       # noqa: BLE001
            return
    for art, w in sorted(rec.get('weapons', {}).items()):
        if not isinstance(w, dict) or w.get('base') not in WEAPON_SPEED:
            continue
        speeds = []
        for key in WEAPON_SPEED[w['base']]:
            speeds += [abs(t.value) for _p, t in V.find(vf, '%s:%s' % (w['base'], key), 'all', {})]
        g = scripts(inst, 'fighter/%s/script/animcmd/weapon/%s/game.bin' % (name, art))
        if not g or not speeds:
            continue
        worst = None
        for cmds in g.values():
            for c in cmds:
                if c.name not in ('Special_Hitbox', 'Extended_Special_Hitbox'):
                    continue
                syn = c.info['syntax']
                v = {k: c.params[i] for i, k in enumerate(syn) if i < len(c.params)}
                reach = 2 * v['Size']
                if 'X2' in v:
                    reach += math.dist((v['X'], v['Y'], v['Z']), (v['X2'], v['Y2'], v['Z2']))
                if worst is None or reach < worst[0]:
                    worst = (reach, v['Size'])
        if worst and max(speeds) > max(STEP_RADII * worst[1], worst[0]):
            rep.add('ERROR', 'W15 hitbox-step', '%s: %g units a frame (its vl speeds %s) against a hitbox of radius %g '
                    '(reach %.1f): it skips fighters between frames; make the hit one line over the path (a capsule as '
                    'long as the step, Extended_Special_Hitbox) or slow it' % (art, max(speeds), speeds, worst[1], worst[0]))


def check_weapon_endless_effects(inst, name, rec, vanilla, rep):
    """E10: an article's script starting an effect with endless emitters (one_time 0) or never-dying particles
    (life 0x7FFFFFFF) that no script of that article ends (Terminate_Graphic_Effect) and its MSC doesn't kill
    (EffectModule(0x2723, id)): it outlives the move (Sephiroth's Phantom's charge glow, PtcZeldaPhantomHold, left at
    his hand after a release from any status: tests 117 / 144 / multi-instance bugs v1; its base's own status ended it)"""
    import tempfile
    import efc
    import ptcl
    kind = int(rec['kind'], 0)
    banks = {}

    def bank(kk):
        if kk in banks:
            return banks[kk]
        out = None
        if kk == kind:
            p = sorted(inst.glob(r'fighter/%s/effect/%s/[^/]+\.ptcl' % (name, name)))
            e = sorted(inst.glob(r'fighter/%s/effect/%s/[^/]+\.efc' % (name, name)))
            if p and e:
                out = (inst.get(p[0]), inst.get(e[0]))
        elif vanilla:
            b = rec['base']
            pp = os.path.join(vanilla, 'fighter', b, 'effect', b, '%s.010d0000' % b)
            if os.path.exists(pp + '.ptcl'):
                out = (open(pp + '.ptcl', 'rb').read(), open(pp + '.efc', 'rb').read())
        if out:
            pt, ef = ptcl.Ptcl(out[0]), efc.Efc(out[1])
            out = (pt, ef)
        banks[kk] = out
        return out

    def endless(fx):
        b = bank((fx >> 16) & 0xFF)
        if not b:
            return False
        pt, ef = b
        i = fx & 0xFFFF
        if i >= len(ef.entries) or not ef.entries[i][1]:
            return False
        ems = [em['data'] for em in pt.sets[ef.entries[i][1] - 1]['emitters'] if em['data']]
        return any(pt.field(e, 'one_time') == 0 or pt.field(e, 'ptcl_life') == 0x7FFFFFFF for e in ems)
    starts = ('Graphic_Effect', 'Graphic_Effect2', 'Graphic_Effect3', 'Graphic_Effect4', 'External_Graphic')
    for path in sorted(inst.glob(r'fighter/%s/script/animcmd/weapon/[^/]+/effect\.bin' % name)):
        art = path.split('/')[-2]
        with tempfile.NamedTemporaryFile() as f:
            f.write(inst.get(path))
            f.flush()
            try:
                scr = acmd.ACMDFile.load(f.name).scripts
            except Exception:                 # noqa: BLE001
                continue
        started, ended = set(), set()
        for cmds in scr.values():
            for c in cmds:
                if c.params and isinstance(c.params[0], int) and c.params[0] >> 24 == 3:
                    (started if c.name in starts else ended if c.name == 'Terminate_Graphic_Effect' else set()).add(
                        c.params[0])
        msc = os.path.join(ROOT, 'fighters', name, 'weapons', art + '.c')
        killed = set()
        if os.path.exists(msc):
            killed = {int(x, 16) for x in re.findall(r'EffectModule\(0x2723, (0x[0-9a-fA-F]+)', open(msc).read())}
        left = sorted(fx for fx in started - ended - killed if endless(fx))
        if left:
            rep.add('WARN', 'E10 weapon-endless-effects', '%s: %s start effects that never end by themselves (%s) and no '
                    'script of it ends them (Terminate_Graphic_Effect) nor its MSC (EffectModule 0x2723): they outlive '
                    'the move (Sephiroth\'s Phantom glow left at his hand)' % (
                        path, art, ', '.join('0x%X' % x for x in left)))


def check_flare_targets(name, rec, rep):
    """F1: a new fighter missing from Sephiroth's Shadow Flare table (fighters/edge/weapons/flare1.c, written by
    tools/edge_flare_targets.py from Ultimate's edge_flare_radius / node / offsets): its orbs circle it at the
    fallback 14 around its position + 9, inside a big fighter, and hit it while circling (Sephiroth test 71:
    Donkey Kong at 14 / 9 took the orbit hits)"""
    src = os.path.join(HERE, '..', 'fighters', 'edge', 'weapons', 'flare1.c')
    if not os.path.exists(src):
        return
    kind = int(rec['kind'], 0)
    if 'if (k == 0x%x)' % kind not in open(src).read():
        rep.add('WARN', 'F1 flare-targets', 'kind 0x%X (%s) has no row in flare1.c\'s Shadow Flare table: rerun '
                'tools/edge_flare_targets.py with --vbn %s=<its model.vbn> --write fighters/edge/weapons/flare1.c '
                '(and rebuild flare1.mscsb)' % (kind, name, name))


def check_loop_slots(inst, name, rec, base, vanilla, rep):
    """M9: a fighter slot (0x211 on) whose base motion loops (motion table flag 0x2) and that the port gives another
    move (its motion.mtable names another script there) without a flag override in the record's "motions": that
    move's motion never ends, and a status waiting for its end never leaves (Sephiroth test 62b: Scintilla's slash
    on Zelda's SpecialLwLoop 0x249 looped for good)"""
    import mtable
    import tempfile
    mt = inst.get('fighter/%s/script/animcmd/body/motion.mtable' % name)
    rpx = inst.get('code/cross_f.rpx') if 'code/cross_f.rpx' in inst.files else None
    van = os.path.join(vanilla or '', 'fighter', rec['base'], 'script/animcmd/body/motion.mtable')
    if mt is None or rpx is None or not os.path.exists(van):
        return
    port = list(struct.unpack('>%dI' % (len(mt) // 4), mt))
    orig = mtable.read(van)
    with tempfile.NamedTemporaryFile(suffix='.rpx') as f:
        f.write(rpx)
        f.flush()
        try:
            flags = [fl for _h, fl in mtable.motion_table(f.name, base['kind'])['main']]
        except SystemExit:
            return
    over = {int(k, 16): int(v.get('flags', '0x0'), 0) for k, v in (rec.get('motions') or {}).items() if 'flags' in v}
    bad = []
    for i in range(0x211, min(len(port), len(orig), len(flags))):
        fl = over.get(i, flags[i])
        if fl & 2 and port[i] and port[i] != orig[i]:
            bad.append('0x%X' % i)
    if bad:
        rep.add('WARN', 'M9 loop-slot', '%d slots keep the base\'s looping motion flag (0x2) under another move: a status '
                'waiting for the motion\'s end never leaves (override "flags" in the record\'s "motions" unless the move '
                'loops): %s' % (len(bad), ', '.join(bad)))


def check_root_motion(inst, name, rec, rep):
    """M12 root-motion: a motion slot the record gives an animation of its own (extra_kinds.json "motions") whose root
    (TransN) moves (Ultimate's motion_list move flag 0x4: the root's movement is the fighter's), without the move flag
    in the slot's flags: Smash 4 draws the root's translation as an offset from where the fighter is, and at the
    motion's end the model snaps back to it (Byleth v1 - v6: side special's lunge drawn 11 / 14 forward, user v6: "Side
    special teleports them back to their origin"; the wall jump 25 up). The flag 0x4 in "flags" (rebuild the executable's
    motion table: tools/kind_expand_incremental.py)"""
    import tempfile
    import omo
    pac = inst.get('fighter/%s/motion/body/main.pac' % name)
    vbn = inst.get('fighter/%s/model/body/c00/model.vbn' % name)
    if pac is None or vbn is None:
        return
    with tempfile.TemporaryDirectory() as td:
        pp, vp = os.path.join(td, 'main.pac'), os.path.join(td, 'model.vbn')
        open(pp, 'wb').write(pac)
        open(vp, 'wb').write(vbn)
        anims = dict(omo.pac_read(pp))
        bones = omo.vbn_read(vp)
    trans = [h for n, _p, h in bones if n == 'TransN']
    if not trans:
        return
    bad = []
    for slot, v in sorted((rec.get('motions') or {}).items()):
        if not isinstance(v, dict) or 'anim' not in v:
            continue
        data = anims.get(v['anim'] + '.omo')
        if data is None:
            continue
        o = omo.Omo(data)
        first = o.sample(trans[0], 0)
        if first is None:
            continue
        p0 = first[0]
        move = max(sum((a - b) ** 2 for a, b in zip((o.sample(trans[0], f) or first)[0], p0)) ** 0.5
                   for f in range(o.frames))
        if move > 1.0 and not int(v.get('flags', '0x0'), 0) & 4:
            bad.append('%s %s (the root moves %.1f)' % (slot, v['anim'], move))
    if bad:
        rep.add('ERROR', 'M12 root-motion', '%d motion slots whose root (TransN) moves have no move flag (0x4): the '
                'model is drawn away from the fighter and snaps back at the motion\'s end: %s' % (len(bad), '; '.join(bad)))


def check_tether_ledge(name, rep):
    """S13 tether-ledge: a port that registers its own main for the base's tether status 0xF1 (AirCatch: ZSS's, Byleth's
    air up special) must keep the common AirCatch loop's ledge catch (func_126: `func_99() == 1 &&
    WorkModule(0x2712, 0x2100000D)` -> 0xF2). Byleth v1 - v6's loop dropped it: the up special never caught a ledge
    in front of him (user v6: "doesn't grab ledges")"""
    src = os.path.join(ROOT, 'fighters', name, name + '.c')
    if not os.path.exists(src):
        return
    text = open(src, errors='replace').read()
    own = [m for m in re.finditer(r'sv_set_mem\(0x1, 0x1, 0xf1, (\w+)\)', text) if not re.fullmatch(r'func_\d+', m.group(1))]
    if not own:
        return
    m = own[-1]
    loops = re.findall(r'func_78\((\w+)\)', re.search(r'\n\w[\w ]*\b%s\([^)]*\)\s*\{(.*?)\n\}' % m.group(1), text, re.S).group(1))
    body = ''.join(re.search(r'\n\w[\w ]*\b%s\([^)]*\)\s*\{(.*?)\n\}' % lp, text, re.S).group(1) for lp in loops
                   if re.search(r'\b%s\(' % lp, text))
    if not (re.search(r'func_99\(\)', body) and '0xf2' in body.lower()):
        rep.add('ERROR', 'S13 tether-ledge', '%s: its 0xF1 main %s runs a loop (%s) without the common AirCatch ledge '
                'catch (func_99() and 0x2100000D -> status 0xF2: func_126)' % (os.path.basename(src), m.group(1),
                                                                             ', '.join(loops) or 'none'))


def check_status_effects(name, src, rec, rep):
    """E11 status-effects: the fighter's own effect sets (its .eff) that the port leaves out of its bank though nothing
    keeps them out: Ultimate requests some from its status code or native specializers only (Byleth's max arrow beam
    master_bow_arrow2 / _bullet / _end / _hit, Aymr's floor impact master_axe_impact / _ground), so init's list (the
    sets its ACMD calls) missed them and those moves drew without them (Byleth v1 - v6). WARN with the names: add them
    to port.json effects.own, or to effects.kept_out with the reason"""
    import port_sources  # noqa: F401
    try:
        eff = src.eff(port_sources.ult_name(name))
    except Exception:
        eff = None
    cfg = os.path.join(ROOT, 'fighters', name, 'port.json')
    if not eff or not os.path.exists(eff) or not os.path.exists(cfg):
        return
    pj = json.load(open(cfg))
    fx = pj.get('effects') or {}
    have = {n.lower() for n in fx.get('own', [])} | {n.lower() for n in fx.get('kept_out', [])}
    ult = port_sources.ult_name(name).lower()
    sets = set(re.findall(rb'\b(%s_[A-Z0-9_]+)\x00' % ult.upper().encode(), open(eff, 'rb').read()))
    miss = sorted(s.decode().lower() for s in sets if s.decode().lower() not in have)
    if miss:
        rep.add('WARN', 'E11 status-effects', '%d of the %d effect sets in ef_%s.eff are neither in the bank nor kept '
                'out (port.json effects.own / kept_out): if the status code or the ExeFS plays them, the move draws '
                'without them: %s' % (len(miss), len(sets), ult, ', '.join(miss)))


# the --have bones of ports from before port.json recorded them (ultimate_fighter.py --have LEFT,RIGHT)
HAVE_BONES = {'edge': 'SwordL1,SwordR1'}


def check_have_bones(inst, name, rep):
    """M9: a --have port's model plays the Ultimate hand bones (Sephiroth's SwordL1 / SwordR1) as LHaveN / RHaveN,
    and its motions animate those with their tracks. A model.vbn with bones of their own by those names was built
    with another skeleton (`--joints` instead of `--have`): its meshes' bone indices don't match, and nothing moves
    the bones. Sephiroth test 80 (user, clip): the coat's panels rigid, the sword never in his hand"""
    import omo
    import tempfile
    have = HAVE_BONES.get(name)
    cfg = os.path.join(ROOT, 'fighters', name, 'port.json')
    if os.path.exists(cfg):
        have = json.load(open(cfg)).get('have') or have
    if not have:
        return
    names = {h.lower() for h in have.split(',')}
    for rel in inst.glob(r'fighter/%s/model/body/c\d\d/model\.vbn' % name):
        with tempfile.NamedTemporaryFile(suffix='.vbn', delete=False) as f:
            f.write(inst.get(rel))
        try:
            bones = [b[0] for b in omo.vbn_read(f.name)]
        finally:
            os.unlink(f.name)
        own = sorted(b for b in bones if b.lower() in names)
        if own:
            rep.add('ERROR', 'M9 have-bones', '%s (%s): bones of their own named %s, which this port plays as LHaveN / '
                    'RHaveN (--have %s): the skeleton isn\'t the one its meshes and motions were built for (rebuild with '
                    '--have, as fighters/%s/README.md)' % (rel, inst.where(rel), ', '.join(own), have, name))


def check_motions(inst, name, rec, rep):
    """M8: every animation the record's motion table names ("motions": the executable's kind_expand table) is in
    the installed motion/body/main.pac, else that move T-poses (Hero fix 79: its main.pac was rebuilt from an
    older one, fighters_latest's, without fix 17's C01AttackS32: forward tilt 2 T-posed)"""
    import omo
    pac = inst.get('fighter/%s/motion/body/main.pac' % name)
    if pac is None or not rec.get('motions'):
        return
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.pac') as f:
        f.write(pac)
        f.flush()
        have = {n for n, _d in omo.pac_read(f.name)}
    miss = sorted({m['anim'] for m in rec['motions'].values() if m.get('anim') and m['anim'] + '.omo' not in have})
    if miss:
        rep.add('ERROR', 'M8 motion-missing', '%d animations the motion table names aren\'t in main.pac (%s): those '
                'moves T-pose: %s' % (len(miss), inst.where('fighter/%s/motion/body/main.pac' % name), ', '.join(miss)))


def _frames(script):
    """(frame, command) along a script, branches walked as if taken (the timers FRAME / WAIT)"""
    fr = 0.0
    for c in script:
        if c.name == 'FRAME':
            fr = float(c.params[0])
        elif c.name == 'WAIT':
            fr += float(c.params[0])
        yield fr, c


def check_grab_vs_hit(inst, name, rep):
    """S14 grab-vs-hit: a grab box out on a frame where a hitbox that hits fighters (HitBits bit 0) is out too: the hit
    takes the fighter first (its knockback; both in hitlag) and the grab box never catches it. Byleth v8's up special
    tip (Extended_Grab_Collision 0xBD with Ultimate's 3 % hits on frames 20 - 25): nothing ever caught (user's v8 clips:
    DK hit 120 -> 123 %, launched). ERROR per script; the hits there need HitBits without bit 0 (or no hitbox)"""
    game = scripts(inst, 'fighter/%s/script/animcmd/body/game.bin' % name)
    if not game:
        return
    import acmd
    names = {}
    for n in ('specialhi', 'aircatch', 'specialairhi', 'speciallw', 'specials', 'specialairs', 'specialn', 'catch',
              'catchdash', 'catchturn'):
        names[acmd.crc(n)] = n
    bad = []
    for h, sc in game.items():
        hits, grab, frames = {}, False, set()
        for fr, c in _frames(sc):
            if c.name in ('Special_Hitbox', 'Extended_Special_Hitbox', 'Hitbox', 'Extended_Hitbox'):
                syn = c.info['syntax']
                bits = int(c.params[syn.index('HitBits')]) if 'HitBits' in syn else 0x3F
                hits[c.params[0]] = bool(bits & 1)
            elif c.name in ('Remove_All_Hitboxes',):
                hits = {}
            elif c.name in ('Grab_Collision', 'Grab_Collision2', 'Extended_Grab_Collision', 'Extended_Grab_Collision2'):
                grab = True
            elif c.name in ('Remove_All_Grab_Collisions',):
                grab = False
            if grab and any(hits.values()):
                frames.add(fr)
        if frames:
            bad.append('%s (frames %s)' % (names.get(h, '0x%08X' % h), ', '.join('%g' % f for f in sorted(frames))))
    if bad:
        rep.add('ERROR', 'S14 grab-vs-hit', 'a grab box out with a fighter-hitting hitbox: the hit takes the fighter, the '
                'grab never catches: %s' % '; '.join(bad))


def check_line_tests(inst, name, rec, rep):
    """S15 line-cut / X6 line-test-exe. S15 (WARN): an article's game script with a capsule hitbox 100 units long or more
    and no Line_Test before it: Ultimate's long search lines (set_search, Byleth's max arrow: 300) stop at the first
    ground / wall; uncut, it hits through walls (Byleth v8). X6 (ERROR): a script using Line_Test
    (tools/line_test_cave.py) with no executable in the install carrying it (its CRC in the cave's table)"""
    import zlib
    lt = zlib.crc32(b'Line_Test') & 0xFFFFFFFF
    uses, long_ = [], []
    for rel in inst.glob(r'fighter/%s/script/animcmd/.*/game\.bin|fighter/%s/script/animcmd/.*/effect\.bin' % (name, name)):
        sc = scripts(inst, rel) or {}
        for h, body in sc.items():
            tested = False
            for c in body:
                if c.name == 'Line_Test':
                    tested = True
                    uses.append(rel)
                elif c.name == 'Extended_Special_Hitbox' and '/weapon/' in rel and rel.endswith('game.bin'):
                    syn = c.info['syntax']
                    v = {k: float(c.params[syn.index(k)]) for k in ('X', 'Y', 'Z', 'X2', 'Y2', 'Z2')}
                    ln = ((v['X2'] - v['X']) ** 2 + (v['Y2'] - v['Y']) ** 2 + (v['Z2'] - v['Z']) ** 2) ** 0.5
                    if ln >= 100 and not tested:
                        long_.append('%s 0x%08X (%.0f units)' % (rel.split('/animcmd/')[1], h, ln))
    if long_:
        rep.add('WARN', 'S15 line-cut', 'long line hitboxes not cut at the stage (no Line_Test before them): %s'
                % '; '.join(sorted(set(long_))))
    if not uses:
        return
    import tempfile
    import kind_expand as K
    import line_test_cave as LT
    ok = False
    if 'code/cross_f.rpx' in inst.files:
        with tempfile.NamedTemporaryFile(suffix='.rpx') as f:
            f.write(inst.get('code/cross_f.rpx'))
            f.flush()
            img = K.Image(f.name)
            try:
                ok = any(img.w(x) == lt for x in range(LT.CAVE, LT.LIMIT, 4))
            except Exception:                 # noqa: BLE001
                ok = False
    if not ok:
        rep.add('ERROR', 'X6 line-test-exe', 'Line_Test in %s but the install\'s code/cross_f.rpx has no line test '
                '(tools/line_test_cave.py: exe_v46v_line or later): the script won\'t load' % ', '.join(sorted(set(uses))))


def check_article_motions(inst, name, rec, rep):
    """X7 article-motion-slot: a body script plays an article's motion slot (Set_Anchored_Article_Action(article, slot);
    the weapon adds its custom number, 0 - 3) that the install's executable doesn't give that article's weapon kind
    (its descriptor's motion info: tools/weapon_expand.py / master_whip_motion_cave.py), or whose motion-info entry
    names no animation in the article's motion/<name>/main.pac: the article keeps its old motion. Byleth v15 grew his
    whip's motion info (exe_v46x_whipmot) for the up special's sword motions: its scripts on an older executable would
    play nothing. ERROR"""
    import tempfile
    import zlib
    import kind_expand as K
    import weapon_expand as W
    import weapon_expand_append as WA
    if 'code/cross_f.rpx' not in inst.files or not rec.get('weapons'):
        return
    game = scripts(inst, 'fighter/%s/script/animcmd/body/game.bin' % name) or {}
    uses = {}
    for k, sc in game.items():
        for c in sc:
            if c.name == 'Set_Anchored_Article_Action':
                uses.setdefault((int(c.params[0]), int(c.params[1])), set()).add(k)
    if not uses:
        return
    voc = {acmd.crc(w): w for w in vocabulary()}
    kinds = {}
    for art, v in rec['weapons'].items():
        kinds[int(v['kind'] if isinstance(v, dict) else v, 0)] = art
    bad = []
    with tempfile.NamedTemporaryFile(suffix='.rpx') as f:
        f.write(inst.get('code/cross_f.rpx'))
        f.flush()
        img = K.Image(f.name)
        try:
            d = WA.new_fighter_descriptor_any(img, int(rec['kind'], 0))
            al = img.w(d + 8)
            ents, n = img.w(al), img.w(al + 4)
            dsw = WA.parse_patched_switch(img, W.DESC_SWITCH)
            dt = WA.lis_addi_pairs(img, dsw['stub'], 32)[1]
        except (AssertionError, KeyError, IndexError) as e:
            rep.add('NOTE', 'X7 article-motion-slot', 'the executable\'s article list / descriptors not read (%s)' % e)
            return
        for (art, slot), where in sorted(uses.items()):
            if art >= n:
                continue
            wk = img.w(ents + 16 * art) & 0x3FFFFFFF
            if wk not in kinds or wk < W.OLD_N:
                continue
            case = img.w(dt + 4 * (wk - W.OLD_N))
            desc = WA.lis_addi_pairs(img, case, 3)[0] if case else 0
            mi = img.w(desc + 8) if desc else 0
            cnt = img.w(mi + 4) if mi else 0
            what = '%s (article %d, weapon 0x%X) slot %d in %s' % (kinds[wk], art, wk, slot, ', '.join(
                sorted(voc.get(k, '%08X' % k) for k in where)))
            if slot + 3 >= cnt:
                bad.append('%s: the executable gives it %d motions' % (what, cnt))
                continue
            pac = inst.get('fighter/%s/motion/%s/main.pac' % (name, kinds[wk]))
            if pac is None:
                continue
            import omo
            with tempfile.NamedTemporaryFile(suffix='.pac') as g:
                g.write(pac)
                g.flush()
                names = {zlib.crc32(nm[:-4].encode(), 0xFFFFFFFF) & 0xFFFFFFFF for nm, _d in omo.pac_read(g.name)}
            h = img.w(img.w(mi) + 8 * slot)
            if h not in names:
                bad.append('%s: its motion 0x%08X is not in motion/%s/main.pac' % (what, h, kinds[wk]))
    if bad:
        rep.add('ERROR', 'X7 article-motion-slot', '; '.join(bad))


def check_tether_window(inst, name, rep):
    """S16 tether-window: the tether status's ledge box check (the common AirCatch's func_99 while flag 0x2100000D is on,
    set by the aircatch script) closes before the tether goes out (Set_Remote_Article_Action(2, 1)): only the tether
    tip's own latch can take a ledge. Byleth v1 - v8 kept ZSS's zair window 0 - 5 with his whip out at 17 (user v8: the
    ledge grab "very specific"; Ultimate's AIR_LASSO_FLAG_CHECK is 12 - 17 with its big AIR_LASSO box). ERROR"""
    import acmd
    game = scripts(inst, 'fighter/%s/script/animcmd/body/game.bin' % name)
    sc = (game or {}).get(acmd.crc('aircatch'))
    if not sc:
        return
    on = off = out = None
    for fr, c in _frames(sc):
        if c.name == 'ON_FLAG' and c.params[0] == 0x2100000D and on is None:
            on = fr
        elif c.name == 'OFF_FLAG' and c.params[0] == 0x2100000D and off is None:
            off = fr
        elif c.name == 'Set_Remote_Article_Action' and out is None:
            out = fr
    if on is not None and out is not None and off is not None and off < out - 6:
        rep.add('ERROR', 'S16 tether-window', 'aircatch: the ledge box check (0x2100000D, frames %g - %g) closes %g '
                'frames before the tether goes out (frame %g)' % (on, off, out - off, out))


def check_smash_holds(inst, name, base, vanilla, rep):
    """E13 smash-hold: the smash attacks' hold effect scripts (attacks4hold / attackhi4hold / attacklw4hold) still the
    base fighter's (the translator has no Ultimate Charge -> Hold names): the base's charge flash on the base's hand
    (Byleth v1 - v8: ZSS's on RHaveN (0, 1.5, 2) in all three, Ultimate's sys_smash_flash_s on the weapons' heads).
    ERROR per script identical to the base's"""
    import acmd
    eff = scripts(inst, 'fighter/%s/script/animcmd/body/effect.bin' % name)
    vp = os.path.join(vanilla or '', 'fighter', base.get('base', ''), 'script', 'animcmd', 'body', 'effect.bin')
    if not eff or not vanilla or not os.path.exists(vp):
        return
    van = acmd.ACMDFile.load(vp).scripts

    def shape(sc):               # the effect ids aside (the port maps the base's common ones to its own bank)
        return [(c.name, tuple(c.params[1:]) if 'Graphic' in c.name or 'EFFECT' in c.name else tuple(c.params))
                for c in sc]
    same = [n for n in ('attacks4hold', 'attackhi4hold', 'attacklw4hold')
            if acmd.crc(n) in eff and acmd.crc(n) in van and shape(eff[acmd.crc(n)]) == shape(van[acmd.crc(n)])]
    if same:
        rep.add('ERROR', 'E13 smash-hold', 'the smash holds\' effects still the base\'s (its charge flash on its hand): %s'
                % ', '.join(same))


def check_throw_joint_hitboxes(inst, name, rep):
    """S12 throw-joint: a move's hitboxes on the throw joint (ThrowN) while its animation keeps ThrowN at the root:
    Ultimate's status code moves `throw` to where the move reaches (Byleth's up special: the Sword of the Creator's tip,
    his `throw` held at the origin in every body animation), so translated as they are the hitboxes sit at his feet
    (Byleth v1 - v5: the up special hit nothing at the whip; user: "not functioning"). The throws, pummel and grabs use it
    for the held fighter: left out. ERROR when every frame a throw hitbox is out has ThrowN within 3 units of the
    root; a motion not found by its script's name: NOTE"""
    import tempfile
    import omo
    import ultimate_acmd as UA
    body = 'fighter/%s/script/animcmd/body/' % name
    game = scripts(inst, body + 'game.bin')
    pac = inst.get('fighter/%s/motion/body/main.pac' % name)
    mdir = 'fighter/%s/model/body/c00/' % name
    vbn, jt = inst.get(mdir + 'model.vbn'), inst.get(mdir + 'model.jtb')
    if game is None or pac is None or vbn is None or jt is None:
        return
    with tempfile.TemporaryDirectory() as tmp:
        for fn, d in (('model.vbn', vbn), ('model.jtb', jt)):
            open(os.path.join(tmp, fn), 'wb').write(d)
        open(os.path.join(tmp, 'main.pac'), 'wb').write(pac)
        jid = UA.joint_ids(tmp).get('throw')
        bones = omo.vbn_read(os.path.join(tmp, 'model.vbn'))
        motions = {}
        for n, d in omo.pac_read(os.path.join(tmp, 'main.pac')):
            key = n[:-4]
            key = key[key.index('Main') + 4:] if 'Main' in key else key
            motions[key[3:].lower()] = d
    if jid is None:
        return
    names = {acmd.crc(k): k for k in motions}
    bad, odd = [], []
    for crc, sc in game.items():
        sname = names.get(crc)
        if sname is None or sname.startswith(('throw', 'catch')):
            continue
        frame, frames = 0, []
        for c in sc:
            if c.name == 'FRAME':
                frame = max(frame, int(float(c.params[0])))
            elif c.name == 'WAIT':
                frame += int(float(c.params[0]))
            elif 'Hitbox' in c.name and jid in bone_params(c):
                frames.append(frame)
        if not frames:
            continue
        o = omo.Omo(motions[sname])
        near = True
        for f in frames:
            w = omo.world(o, bones, min(f, o.frames - 1))
            t, r = w['ThrowN'], w[bones[0][0]]
            if math.hypot(*(t[i][3] - r[i][3] for i in range(3))) > 3.0:
                near = False
                break
        (bad if near else odd).append('%s (frames %s)' % (sname, ','.join(str(f) for f in sorted(set(frames)))))
    if bad:
        rep.add('ERROR', 'S12 throw-joint', 'hitboxes on the throw joint (%d) with ThrowN at the root in the move\'s '
                'animation: they hit at the fighter\'s feet (Ultimate\'s status code moves `throw`; give the motion a '
                'ThrowN track where it reaches, e.g. tools/master_whip.py bake_throw): %s' % (jid, '; '.join(bad)))
    if odd:
        rep.add('INFO', 'S12 throw-joint', 'hitboxes on the throw joint, ThrowN moved by the animation: %s' % '; '.join(odd))


def check_slot_moves(inst, name, src, ult, rep):
    """S11 slot-moves: Ultimate has a rapid jab / angled forward smash (game_attack100 / attacks4hi / lw in the dump) but
    the installed motion.mtable has no script for its common slot (0x53 - 0x55, 0x5E, 0x61): the move is missing (Byleth
    v1 on ZSS, whose table leaves them empty: extra_kinds.json "motions" + port.json motions.add, the scripts step's
    --slot-moves) [WARN]"""
    import struct
    import zlib
    mt = inst.get('fighter/%s/script/animcmd/body/motion.mtable' % name)
    dump = src.dump(ult) if ult else None
    if mt is None or not dump:
        return
    crcs = set(struct.unpack('>%dI' % (len(mt) // 4), mt))
    have = set()
    for root, _d, files in os.walk(dump):
        for f in files:
            if f.endswith('.txt') and os.path.basename(root) == ult:
                have.add(f[:-4].lower())
    want = {'attack100': 'the rapid jab', 'attack100end': 'the rapid jab\'s finisher', 'attacks4hi': 'forward smash up',
            'attacks4lw': 'forward smash down'}
    miss = ['%s (%s)' % (k, v) for k, v in want.items() if k in have and (zlib.crc32(k.encode()) & 0xFFFFFFFF) not in crcs]
    if miss:
        rep.add('WARN', 'S11 slot-moves', 'Ultimate has these moves, the port\'s motion table doesn\'t: %s (motion slots: '
                'extra_kinds.json "motions" + port.json motions.add, then the scripts step)' % ', '.join(miss))


def check_loop_spin(inst, name, rep):
    """S12 loop-spin: a script that jumps back to itself (JUMP to its own hash: Ultimate's endless `loop {}`, the
    translator's form) with nothing that waits before it (WAIT, a FRAME past the first, WAIT_LOOP_CLR, Loop_Rest): it
    runs again in the same frame, for ever (a hang). Byleth v2's first build: the run / walk effect loops (Ultimate's
    wait_loop_sync_mot) jumped back with no Loop_Rest [ERROR]"""
    bad = []
    for fn in ('game', 'effect', 'sound', 'expression'):
        sc = scripts(inst, 'fighter/%s/script/animcmd/body/%s.bin' % (name, fn))
        for h, cmds in (sc or {}).items():
            names = [c.name for c in cmds]
            if 'JUMP' not in names:
                continue
            j = names.index('JUMP')
            if cmds[j].params and int(cmds[j].params[0]) & 0xFFFFFFFF == h:
                waits = [c for c in cmds[:j] if c.name in ('WAIT', 'WAIT_LOOP_CLR', 'Loop_Rest')
                         or (c.name == 'FRAME' and c.params and float(c.params[0]) > 0)]
                if not any(c.name in ('WAIT', 'WAIT_LOOP_CLR', 'Loop_Rest') for c in waits):
                    bad.append('%s %08X' % (fn, h))
    if bad:
        rep.add('ERROR', 'S12 loop-spin', 'scripts jumping back to themselves without a wait (they spin in one frame: '
                'a hang): %s' % ', '.join(bad))


def check_assets(inst, name, base, rep):
    ui = (base.get('ui') or {}).get('name') or base.get('cap') or name.capitalize()
    for s in ('chr_00', 'chr_11', 'chr_12', 'chr_13', 'stock_90'):
        if not inst.glob(r'ui/replace/chr/%s/%s_%s_\d\d\.nut' % (s, s, re.escape(ui))):
            rep.add('INFO', 'U1 portraits', 'no %s portraits for %s in the packages' % (s, ui))
    if not inst.glob(r'fighter/%s/sound/.*' % name):
        rep.add('INFO', 'A1 sounds', 'no fighter/%s/sound in the packages (the base\'s banks play)' % name)
    elif not inst.get('sound/config/soundlabeltable.bin'):
        rep.add('WARN', 'A1 labels', 'sound banks without sound/config/soundlabeltable.bin (Hero fix 71)')


# added kinds that aren't Ultimate ports (no Ultimate win cameras to want): Supamario is a Mario variant
NON_ULTIMATE = ('supamario',)


def win_motions(inst, name):
    """{N: frames} of the win poses the install plays (fighter/NAME/motion/bodyresult/main.pac: J02WinN)"""
    import tempfile
    data = inst.get('fighter/%s/motion/bodyresult/main.pac' % name)
    if data is None:
        return {}
    import result_param as RP
    with tempfile.NamedTemporaryFile(suffix='.pac', delete=False) as f:
        f.write(data)
    try:
        return RP.win_lengths(f.name)
    finally:
        os.unlink(f.name)


def check_lod_and_camera(inst, name, src, ult, rep):
    """M10 low-lod: a costume whose Ultimate model has its own low model (model/body/cNN/lod.xmb: body_low ...) shipped
    with lNN a copy of cNN (ultimate_port.py low-models builds Ultimate's: `--lod-low`) [WARN: the copy still shows].
    R1 win-camera: Ultimate's victory cameras (camera/fighter/<ult>/c00/j02win1-3) not in the package where the
    result scene's script loads a winner's camera (motion/camera/result/NAME/N/camera_motion.omo + .vbn,
    data/script/xscene_result.xtal; tools/ultimate_camera.py) [ERROR: the scene plays its default camera]; also, for
    every added kind but NON_ULTIMATE, each win pose the install plays (fighter/NAME/motion/bodyresult/main.pac:
    J02Win1-3) without its camera, whether or not Ultimate's camera folder is configured (results_panels_v1: the five
    earlier ports had none) [ERROR]"""
    udir = src.ult_dir(ult) if ult else None
    for d in sorted({os.path.dirname(f) for f in inst.glob(r'fighter/%s/model/body/l\d\d/model\.nud' % name)}):
        nn = d[-2:]
        if udir and os.path.exists(os.path.join(udir, 'model/body/c%s/lod.xmb' % nn)):
            c, l = inst.get('fighter/%s/model/body/c%s/model.nud' % (name, nn)), inst.get(d + '/model.nud')
            if c is not None and c == l:
                rep.add('WARN', 'M10 low-lod', 'l%s is a copy of c%s but Ultimate has a low model for it (lod.xmb): '
                        'ultimate_port.py run %s low-models' % (nn, nn, name))
    try:
        import ultimate_camera
        cam = ultimate_camera.cam_source(src, ult) if ult else None
    except Exception:
        cam = None
    # the win poses the package plays (its bodyresult): each needs its camera, whether or not Ultimate's camera folder
    # is configured here (results_panels_v1: none of Hero / Sephiroth / Incineroar / Steve / Squirtle had them)
    played = sorted(win_motions(inst, name))
    wins = [w for w in (1, 2, 3) if cam and os.path.exists(os.path.join(cam, 'j02win%d.nuanmb' % w))]
    if name not in NON_ULTIMATE:
        wins = sorted(set(wins) | {w for w in played if w <= 3})
    have = [w for w in wins if inst.get('motion/camera/result/%s/%d/camera_motion.omo' % (name, w)) is not None
            and inst.get('motion/camera/result/%s/%d/camera_motion.vbn' % (name, w)) is not None]
    old = [w for w in wins if inst.get('fighter/%s/camera/result/win%d/camera_motion.omo' % (name, w)) is not None]
    if cam is None and not wins:
        rep.add('INFO', 'R1 win-camera', 'no Ultimate camera folder for %s (port_sources "ult_camera": camera-SSBU.zip)'
                % ult)
    elif len(have) < len(wins):
        rep.add('ERROR', 'R1 win-camera', 'win poses %s without their Ultimate camera where the result scene loads it '
                '(motion/camera/result/%s/N/camera_motion.omo / .vbn: data/script/xscene_result.xtal; without them the '
                'scene plays motion/camera/result/default/1/)%s: ultimate_port.py run %s camera (ultimate_camera.py '
                'convert-dir CAM/%s/c00 OUT %s --template VBN without a port.json)' % (
                    ', '.join('j02win%d' % w for w in wins if w not in have), name,
                    ' (fighter/%s/camera/result/winN is the old, unread place)' % name if old else '', name, ult, name))
    else:
        rep.add('INFO', 'R1 win-camera', 'win cameras %d in motion/camera/result/%s/ (the field of view is not in the '
                'motion: the scene\'s own is used)' % (len(have), name))


def check_motion_groups(inst, name, src, ult, kind, rep):
    """M11 motion-groups: Ultimate's costumes with motions of their own (Byleth: motion/body/c01 = the female set for
    c01 / c03 / c05 / c07) played as another costume's [WARN: port.json motions.group2 not set]; with group2 set, the
    package's fighter/NAME/motion/body2 (+ bodyentry2, bodyresult2) missing, extra_kinds.json "motion_group2" not the
    same costumes, or the executable's costume groups (tools/costume_group_cave.py: the path hook at 0x030BB1AC and the
    kind's mask byte) missing / different [ERROR: those costumes would load no motions, or the other group's]"""
    import hashlib
    cfg_path = os.path.join(ROOT, 'fighters', name, 'port.json')
    cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else {}
    g2 = (cfg.get('motions') or {}).get('group2') or {}
    costumes = g2.get('costumes') or []
    udir = src.ult_dir(ult) if ult else None
    if not costumes:
        if udir and os.path.isdir(os.path.join(udir, 'motion/body/c00')):
            digest = {}
            for c in sorted(os.listdir(os.path.join(udir, 'motion/body'))):
                f = os.path.join(udir, 'motion/body', c, 'a00wait1.nuanmb')
                if os.path.exists(f):
                    digest[c] = hashlib.sha1(open(f, 'rb').read()).hexdigest()
            own = sorted(c for c, d in digest.items() if d != digest.get('c00'))
            if own:
                rep.add('WARN', 'M11 motion-groups', 'Ultimate\'s %s have motions of their own (a00wait1 differs from '
                        'c00\'s), played as c00\'s: port.json motions.group2 (docs/ultimate-port-guide.md "Costume '
                        'groups")' % ', '.join(own))
        return
    for folder in ('body2', 'bodyentry2', 'bodyresult2'):
        if inst.get('fighter/%s/motion/%s/main.pac' % (name, folder)) is None:
            rep.add('ERROR', 'M11 motion-groups', 'fighter/%s/motion/%s/main.pac missing: %s would load no %s motions '
                    '(ultimate_port.py run %s motions-group2)' % (name, folder, ', '.join(costumes), folder, name))
    try:
        spec = json.load(open(os.path.join(HERE, 'extra_kinds.json')))
        rec = next((k for k in spec['kinds'] if k['name'] == name), {})
    except Exception:                         # noqa: BLE001
        rec = {}
    want = sorted(int(c[1:]) for c in costumes)
    if sorted(rec.get('motion_group2') or []) != want:
        rep.add('ERROR', 'M11 motion-groups', 'tools/extra_kinds.json %s "motion_group2" %s is not port.json\'s group2 '
                'costumes %s' % (name, rec.get('motion_group2'), want))
    if 'code/cross_f.rpx' not in inst.files or not kind:
        rep.add('INFO', 'M11 motion-groups', 'no code/cross_f.rpx in the packages: the costume groups aren\'t checked')
        return
    import tempfile
    import kind_expand as K
    import costume_group_cave as CG
    with tempfile.NamedTemporaryFile(suffix='.rpx') as f:
        f.write(inst.get('code/cross_f.rpx'))
        f.flush()
        img = K.Image(f.name)
        hook = img.w(CG.SITES['path'][0])
        if hook == CG.SITES['path'][1]:
            rep.add('ERROR', 'M11 motion-groups', 'code/cross_f.rpx has no costume groups (tools/costume_group_cave.py): '
                    'every costume plays motion/body')
            return
        _w, info = CG.build(spec)
        k = int(kind, 0) if isinstance(kind, str) else kind
        mask = img.b(info['tab'] + k - CG.FIRST)
    if mask != sum(1 << c for c in want):
        rep.add('ERROR', 'M11 motion-groups', 'code/cross_f.rpx: kind 0x%X\'s costume mask 0x%02X, want 0x%02X (%s): '
                'rebuild costume_group_cave.py' % (k, mask, sum(1 << c for c in want), ', '.join(costumes)))


def check_sound_tables(inst, name, kind, rep):
    """A2-A4: the game finds a fighter's records in bgm_fighter.fbb (victory fanfare) and commonsoundtable.csb
    (KO screams, the crowd's chant) by its Capitalised name, naming the records from the executable's own tables
    (tools/kind_expand.py SOUND_NAME_TABLES); a new kind needs those tables grown AND its records in the files
    (tools/fighter_extras.py fanfare / common). Squirtle extras 2: no KO voices, no chant, Mario's fanfare."""
    import tempfile
    import kind_expand as K
    if not inst.glob(r'fighter/%s/sound/.*' % name):
        return
    rpx = inst.get('code/cross_f.rpx')
    if rpx is None:
        rep.add('INFO', 'A2 sound-names', 'no code/cross_f.rpx in the packages: the executable\'s sound name tables '
                'aren\'t checked')
    else:
        with tempfile.NamedTemporaryFile(suffix='.rpx') as f:
            f.write(rpx)
            f.flush()
            img = K.Image(f.name)
            for tname, (addr, (hi_at, _h), (lo_at, _l), (cmp_at, _c), old) in K.SOUND_NAME_TABLES.items():
                at = ((img.w(hi_at) & 0xFFFF) << 16) + K.sx16(img.w(lo_at))
                i = K.sound_record(tname, kind)
                got = img.cstr(img.w(at + 4 * i)) if at != addr and i < (img.w(cmp_at) & 0xFFFF) else None
                want = record(name).get('cap') or name.capitalize()
                if got != want:
                    rep.add('ERROR', 'A2 sound-names', 'the executable names %s record %d %r, not %r: the game never '
                            'finds %s\'s %s (kind_expand.py SOUND_NAME_TABLES; Squirtle extras 2)' % (
                                {'fbb': 'bgm_fighter.fbb', 'csb': 'commonsoundtable.csb'}[tname], i, got, want, name,
                                {'fbb': 'victory fanfare', 'csb': 'KO voices and crowd chant'}[tname]))
    csb = inst.get('sound/config/commonsoundtable.csb')
    i = K.sound_record('csb', kind)
    ok = False
    if csb and csb[:4] == b'CSB\0':
        nval, n = struct.unpack_from('<HH', csb, 8)
        if i < n:
            v = struct.unpack_from('<%dH' % (2 * nval), csb, 0xC + (0x10 + 4 * nval) * i + 0x10)
            ok = any(v[2 * k] != 0xFFFF for k in range(nval - 1))
    if not ok:
        rep.add('ERROR', 'A3 common-voices', 'commonsoundtable.csb has no record %d for %s: no KO voices, no crowd chant '
                '(tools/fighter_extras.py common; Squirtle extras 2)' % (i, name))
    fbb = inst.get('sound/config/bgm_fighter.fbb')
    if not fbb or fbb[:4] != b'FBB\0' or struct.unpack_from('<I', fbb, 8)[0] <= kind:
        rep.add('WARN', 'A4 fanfare', 'bgm_fighter.fbb has no record 0x%X: no victory fanfare (tools/fighter_extras.py '
                'fanfare)' % kind)


# sound commands and which of their parameters are sound ids (Smash 4 id: row << 16 | label of
# soundlabeltable.bin; 0x80000000 | set << 16 | index: a sequence of the fighter's soundseq_<Name>.sqb)
SOUND_ID_PARAMS = {'Sound_Effect': (0,), 'Sound_Effect2': (0,), 'Sound_Effect3': (0,), 'Sound_Effect4': (0,),
                   'Transient_Sound_Effect': (0,), 'Stop_Sound_Effect': (0,), 'Low_Voice_Clip': (0,),
                   'PLAY_SE_REMAIN': (0,), 'PLAY_SE_NO_3D': (0,), 'SET_PLAY_INHIVIT': (0,), 'PLAY_FLY_VOICE': (0, 1),
                   'STOP_SE_STATUS': (0,), 'SET_TAKEOUT_SE': (0,)}


def check_sound_ids(inst, name, rep):
    """A5: every sound id the fighter's sound scripts play is in the install's soundlabeltable (its row has the label)
    and, on one of his banks' rows, names a tone his bank has; a sequence id names one of his soundseq file's. A
    later package that ships an older soundlabeltable (without his grown rows) or banks without the table would leave
    his moves silent or playing other sounds (the ids are built against the table: tools/ultimate_sound.py)"""
    import tempfile
    import fighter_own_bank as fb
    import minecraft_sound as ms
    paths = inst.glob(r'fighter/%s/script/animcmd/(body|weapon/[^/]+)/sound\.bin' % name)
    table = inst.get('sound/config/soundlabeltable.bin')
    if not paths or not table:
        return
    tab = fb.Table(table)
    banks = {}                          # row -> (bank file, tone count)
    for b in inst.glob(r'fighter/%s/sound/snd_.*\.nus3bank' % name):
        if re.search(r'_c\d\d\.nus3bank$', b):
            continue
        data = inst.get(b)
        try:
            _n, bid = fb.binf(data)
            banks[tab.row_of(bid)] = (b, len(ms.tones_of(data)[1]))
        except Exception:
            continue
    seq = {}
    for q in inst.glob(r'fighter/%s/sound/soundseq_.*\.sqb' % name):
        d = inst.get(q)
        if d[:4] == b'SQB\0':
            sid, count = struct.unpack('<HI', d[6:12])
            offs = struct.unpack('<%di' % count, d[16:16 + 4 * count])
            seq[sid] = [o >= 0 for o in offs]
    bad = []
    for path in paths:
        with tempfile.NamedTemporaryFile(suffix='.bin') as f:
            f.write(inst.get(path))
            f.flush()
            try:
                scripts = acmd.ACMDFile.load(f.name).scripts
            except SystemExit:
                continue
        for crc, sc in scripts.items():
            for c in sc:
                for k in SOUND_ID_PARAMS.get(c.name, ()):
                    if k >= len(c.params):
                        continue
                    v = int(c.params[k]) & 0xFFFFFFFF
                    if v == 0xFFFFFFFF:
                        continue
                    if v & 0x80000000:
                        sid, i = (v >> 16) & 0x7FFF, v & 0xFFFF
                        ok = sid in seq and i < len(seq[sid]) and seq[sid][i]
                    else:
                        row, label = v >> 16, v & 0xFFFF
                        ok = row < len(tab.rows) and label < len(tab.tones(row))
                        if ok and row in banks:
                            tone = tab.tones(row)[label]
                            ok = 0 <= tone < banks[row][1]
                    if not ok:
                        bad.append('%s %08X: %s 0x%X' % (path.split('/animcmd/')[1], crc, c.name, v))
    if bad:
        rep.add('ERROR', 'A5 sound-ids', '%d sound ids in his scripts name no sound of the install\'s soundlabeltable / '
                'banks / soundseq (built against another table? ship the soundlabeltable with the banks): %s' % (
                    len(bad), ', '.join(bad[:12]) + (' ...' if len(bad) > 12 else '')))


def check_sound_bank_ids(inst, name, kind, vanilla, rep):
    """A6: nus3 loads one bank an id (0x036774A4 -> 0x80000021, docs/native-notes.md "Fighter sound banks: one bank an
    id"): a later bank of an id already loaded is refused, its player's handle stays empty and all his sounds and
    voices are silent. A port's banks keeping its base's ids (Hero fix 71: Robin's 2051 / 6059) broke the later player
    with the base, another port on those ids, or a second him in another costume, in the match. ERROR: a bank of his
    with a vanilla fighter's id (its base's), two of his banks sharing an id; banks of their own ids without
    tools/sound_alias_cave.py's hooks / his aliases (reference/port_sound_ids.json) in the install's executable
    (the rows keep the base's ids: his sounds would find no bank). WARN: an id that isn't tools/sound_bank_ids.own_id
    (unique, but outside the scheme)"""
    import fighter_own_bank as fb
    import sound_alias_cave as SA
    import sound_bank_ids as SB
    try:
        _k, cap, _b = SB.kind_record(name)
    except SystemExit:
        return
    ids, mine, vanilla_ids, odd = {}, [], [], []
    for b in inst.glob(r'fighter/%s/sound/snd_(se|vc)_.*\.nus3bank' % name):
        f = b.split('/')[-1]
        c = SB.classify(f, cap)
        if c is None:
            continue
        try:
            _n, bid = fb.binf(inst.get(b))
        except Exception:                     # noqa: BLE001
            continue
        ids.setdefault(bid, []).append(f)
        if bid in SB.VANILLA_FIGHTER_IDS:
            vanilla_ids.append('%s %d' % (f, bid))
        else:
            mine.append(f)
            if bid != SB.own_id(kind, *c):
                odd.append('%s %d' % (f, bid))
    if vanilla_ids:
        rep.add('ERROR', 'A6 bank-ids', 'banks keeping a vanilla fighter\'s id (his base\'s: with that fighter, or '
                'another port on that id, in the match the later player is silent): %s; give them their own '
                '(tools/sound_bank_ids.py renumber, or rebuild with ultimate_sound.py) and rebuild the executable\'s '
                'tools/sound_alias_cave.py' % ', '.join(vanilla_ids[:6]))
    dup = ['%d: %s' % (i, ', '.join(sorted(f))) for i, f in sorted(ids.items()) if len(f) > 1]
    if dup:
        rep.add('ERROR', 'A6 bank-ids', 'banks sharing a BINF id (nus3 loads only the first: a second player of his '
                'in another costume is silent): %s' % '; '.join(dup))
    if odd:
        rep.add('WARN', 'A6 bank-ids', 'ids of their own but not sound_bank_ids.own_id\'s: %s' % ', '.join(odd[:6]))
    if mine and 'code/cross_f.rpx' in inst.files:
        import tempfile
        import kind_expand as K
        want = SA.load_aliases().get(kind)
        with tempfile.NamedTemporaryFile(suffix='.rpx') as f:
            f.write(inst.get('code/cross_f.rpx'))
            f.flush()
            img = K.Image(f.name)
            _w, hooks, _l = SA.build({})
            try:
                hooked = all(img.w(a) == w for a, w in hooks.items())
                got = SA.table_of(img, kind)
            except Exception:                 # noqa: BLE001
                hooked, got = False, None
        if want is None or not hooked or got != want:
            rep.add('ERROR', 'A6 bank-ids', 'banks of their own ids (%s) but %s: his sounds (rows of the base\'s ids) '
                    'find no bank; build it with tools/sound_alias_cave.py (v2)' % (
                        ', '.join(sorted(mine)[:3]), 'no aliases for kind 0x%X in reference/port_sound_ids.json'
                        % kind if want is None else 'the executable has no sound_alias_cave.py v2 hooks'
                        if not hooked else 'the executable gives kind 0x%X the aliases %s, not %s' % (
                            kind, got, want)))


def check_universal(p, rep):
    """E6: the universal shader path's shaders (tools/ult_shader.py: Ultimate's programs lowered; their vertex
    program reads no emitterStaticUniformBlock, every vanilla one does): a slot the pixel program samples must
    hold a texture (eft stops on "Texture Binary is None"), and every pixel input needs a vertex output of its
    semantic (else it reads 0), and the emitter takes CPU particles: eft's GPU-calc flags (emitter byte 5 bit 0x80,
    key byte 4 bit 0x02) left on from a GPU template move nothing on the CPU, the programs get birth values (parts
    frozen at the stage's origin: Squirtle's effects test 22); a program reading the last movement (v_inWldPosDf)
    needs eft to work it out (+0x308 bit 0x10), else it reads a stale slot (test 23's streaks). Returns the
    universal shader indices"""
    import eft_vertex
    import ult_to_latte
    uni, gpu_keys, reads_diff = set(), [], set()
    for i in range(p.shader_count()):
        b = bytes(p.shader_binary(i))
        h = eft_vertex.vertex_header(b)
        if h is None or any(nm == 'emitterStaticUniformBlock' for nm, _c, _s in h['blocks']):
            continue
        uni.add(i)
        ph = ult_to_latte.ps_header(b)
        missing = set(ph['inputs']) - set(ult_to_latte.vs_semantics(b))
        if missing:
            rep.add('ERROR', 'E6 universal-link', 'shader %d: pixel inputs %s without a vertex output' % (i, sorted(missing)))
        if p.shader_entry(i)[4] & 0x02:
            gpu_keys.append(i)
        if 'v_inWldPosDf' in str(h['attribs']):
            reads_diff.add(i)
    if gpu_keys:
        rep.add('ERROR', 'E6 universal-gpu', '%d universal shaders\' keys carry eft\'s GPU-calc flag (byte 4 bit 0x02): %s'
                % (len(gpu_keys), ', '.join(map(str, gpu_keys[:12]))))
    no_tex, gpu, no_diff, scaled = [], [], [], []
    for si in range(len(p.sets)):
        for x in p.sets[si]['emitters']:
            d = x['data']
            if d is None or p.field(d, 'shader_index') not in uni:
                continue
            if d[5] & 0x80:
                gpu.append('%s/%s' % (p.set_name(si), p.emitter_name(d)))
            if abs(struct.unpack_from('>f', bytes(d), 0x778)[0] - 1.0) > 1e-6:
                scaled.append('%s/%s' % (p.set_name(si), p.emitter_name(d)))
            if p.field(d, 'shader_index') in reads_diff and not d[0x30B] & 0x10:
                no_diff.append('%s/%s' % (p.set_name(si), p.emitter_name(d)))
            ph = ult_to_latte.ps_header(bytes(p.shader_binary(p.field(d, 'shader_index'))))
            for _nm, _t, slot in ph['samplers']:
                if slot == 13:
                    continue                # the game's depth texture (soft particles: ult_shader.DEPTH_SLOT)
                t = p.texres(d, slot)
                if not t['size'][0] or not t['native_size']:
                    no_tex.append('%s/%s slot %d' % (p.set_name(si), p.emitter_name(d), slot))
    if no_tex:
        rep.add('ERROR', 'E6 universal-texture', '%d universal-shader emitters sample a slot with no texture ("Texture '
                'Binary is None"): %s' % (len(no_tex), ', '.join(no_tex[:8])))
    if gpu:
        rep.add('ERROR', 'E6 universal-gpu', '%d universal-shader emitters carry eft\'s GPU-calc flag (byte 5 bit 0x80): '
                'nothing moves them, drawn at birth values (the stage origin): %s' % (len(gpu), ', '.join(gpu[:8])))
    if scaled:
        rep.add('ERROR', 'E6 universal-colour-scale', '%d universal-shader emitters with eft\'s colour scale (+0x778) '
                'not 1: their programs apply Ultimate\'s own (c9 word 236), eft\'s emc multiplies it in again (test '
                '24): %s' % (len(scaled), ', '.join(scaled[:8])))
    if no_diff:
        rep.add('ERROR', 'E6 universal-diff', '%d universal-shader emitters read the particle\'s last movement (v_inWldPosDf) '
                'without eft working it out (+0x308 bit 0x10, vanilla\'s directional types only): the stream holds the '
                'slot\'s last particle\'s (streaks to the top of the screen, test 23): %s' % (len(no_diff), ', '.join(no_diff[:8])))
    return uni


# Ultimate effect macros the script translator has no form for, known and left out on purpose (the body flash /
# burn colour overlays: not effects in Smash 4's sense, docs/ultimate-fighter-port.md "Not yet in the scripts")
EFFECT_MACRO_GAPS = ('FLASH', 'FLASH_FRM', 'FLASH_END', 'COL_NORMAL', 'BURN_COLOR', 'BURN_COLOR_FRAME', 'BURN_COLOR_NORMAL')


def check_effect_scripts(src, ult, rep):
    """E7: every effect macro in the fighter's Ultimate effect scripts has a translation (tools/ultimate_acmd.py:
    its table, LAST_EFFECT_*, or Smash 4's command of the same name). Until Squirtle's effects test 25 the
    translator dropped EFFECT_FOLLOW_FLIP_ALPHA and EFFECT_FOLLOW_RND without a word: up tilt's speed line, back
    / down / neutral air's winds missing in game"""
    import collections
    import ultimate_acmd as U
    dump = src.dump(ult)
    d = os.path.join(dump, ult) if dump else None
    if not d or not os.path.isdir(d):
        rep.add('NOTE', 'E7 effect-macros', 'no script dump for %s: effect macros not checked' % ult)
        return
    bad, gaps = collections.Counter(), collections.Counter()
    for f in sorted(os.listdir(d)):
        if not f.endswith('.txt'):
            continue
        for fn, body in U.functions(open(os.path.join(d, f)).read()).items():
            if not fn.startswith('effect_'):
                continue
            for m in re.findall(r'macros::(\w+)\(', body):
                if not re.search('EFFECT|AFTER_IMAGE|FLASH|BURN|PARTICLE', m):
                    continue
                if m in U.EFFECT_MACROS or m in U.LAST_EFFECT or m in ('EFFECT_OFF_KIND', 'AFTER_IMAGE_OFF',
                        'EFFECT_DETACH_KIND') or m.startswith('AFTER_IMAGE4_ON') or U.same_name_syntax(m):
                    continue
                (gaps if m in EFFECT_MACRO_GAPS else bad)[m] += 1
    if bad:
        rep.add('ERROR', 'E7 effect-macros', 'effect macros the script translator drops: %s'
                % ', '.join('%s x%d' % kv for kv in bad.most_common()))
    if gaps:
        rep.add('WARN', 'E7 effect-macros', 'known gaps, left out: %s' % ', '.join('%s x%d' % kv for kv in gaps.most_common()))


def effect_heap_estimate(data):
    """bytes a ptcl takes in eft's one effect heap at load (eft's loader 0x04A6CD18: a 0x6E8 object and a copy of
    each program part per shader entry, 4 bytes a shader, 0x34 a set, 0xA00 an emitter; MEMExpHeap blocks: size
    rounded to 32 + 0x10 header + alignment slack): tools/effect_heap_patch.py"""
    import ptcl

    def r32(x):
        return (x + 31) & ~31

    def blk(size, align, hdr=0x10):
        return r32(size) + hdr + max(0, align // 2 - hdr)

    def parts(b):
        out, o = {}, struct.unpack_from('>I', b, 4)[0]
        while o + 0x20 <= len(b) and b[o:o + 4] == b'BLK{':
            hs, typ, ds = (struct.unpack_from('>I', b, o + k)[0] for k in (4, 0x10, 0x14))
            out[typ] = out.get(typ, 0) + ds
            if typ == 1:
                break
            o += hs + ds
        return out
    p = ptcl.Ptcl(data)
    n, total = p.shader_count(), 0
    for i in range(n):
        b = parts(bytes(p.shader_binary(i)))
        total += blk(0x6E8, 0x80) + blk(b.get(3, 0), 0x40) + blk(b.get(5, 0), 0x100) + blk(b.get(6, 0), 0x40) + \
            blk(b.get(7, 0), 0x100) + blk(0x80, 0x100)
    nsets = len(p.sets)
    nem = sum(len(s['emitters']) for s in p.sets)
    return total + blk(4 * n, 0x80) + blk(0x34 * nsets, 0x80) + blk(0xA00 * nem, 0x100) + nsets * blk(0x6C, 0x80)


# a fighter bank's effect-heap estimate (MiB) against the vanilla 44 MiB heap, in the user's 1v1 with DK (Sephiroth:
# test 60 12.90 and a 13.28 bisect bank loaded, test 61's 13.49 crashed at match load): over the max it fails,
# over the warn it's close (more players / bigger opponents); and one that crowds even the 60 MiB heap
# (effect_heap_patch.py) in 4-player matches
HEAP_VANILLA_MAX, HEAP_VANILLA_WARN, HEAP_PATCHED_WARN = 13.3, 12.0, 20.0


def check_cave_hooks(inst, rep):
    """X2 / X3 (below): kind_expand.py's save-record map / acmd_ext_cave.py's hitbox-set hook missing. X1: tools/acmd_ext_cave.py's code in the executable but its var_entry hook (0x04B79000, position_vars_cave's
    first word) the original instruction: a later position_vars_cave put it back, and every 0x0F0003xx variable
    (VAR_ / TIMER_ / KINETIC_TYPE / TRACK_FRAMES / SPEED_ / TEAM, SLOTn_SHARED_k) reads 0 and ignores writes (the
    standard build since Hero fix 79; found for Sephiroth's Shadow Flare, test 64). Apply acmd_ext_cave last"""
    import tempfile
    import kind_expand as K
    if 'code/cross_f.rpx' not in inst.files:
        return
    with tempfile.NamedTemporaryFile(suffix='.rpx') as f:
        f.write(inst.get('code/cross_f.rpx'))
        f.flush()
        img = K.Image(f.name)
        try:
            cave, hook = img.w(0x04B90000), img.w(0x04B79000)
            kinds, rec = img.w(K.CAVE), img.w(K.SAVE_RECORD_HOOK)
            slot_set = img.w(0x02C0874C)
        except Exception:                     # noqa: BLE001
            return
    if cave != 0 and slot_set == 0x815C0014:
        rep.add('ERROR', 'X3 extra-tag', "code/cross_f.rpx: acmd_ext_cave.py's Extra hitboxes without the hitbox-set hook "
                "(0x02C0874C): their extras record was reused per hitbox ID, so a hit still being handled when the "
                "script re-issued the ID got the next hitbox's hitstun / hitstop (and a plain hitbox could keep an "
                "Extra tag); rebuild with the current acmd_ext_cave.py")
    if kinds != 0 and rec == 0x81830004:
        rep.add('ERROR', 'X2 save-records', 'code/cross_f.rpx: new fighter kinds (tools/kind_expand.py) without the save '
                'records\' index map at 0x02A53C60: the single-player modes read a null record for the database '
                'positions past the save\'s 82 (Classic mode crashed loading, user\'s Cemu log); rebuild with the '
                'current kind_expand.py')
    if cave != 0 and hook == 0x548C05BE:
        rep.add('ERROR', 'X1 cave-hook', 'code/cross_f.rpx: acmd_ext_cave.py\'s code is there but its hook at 0x04B79000 '
                'was undone (position_vars_cave.py applied after it): user / shared variables, timers and the kinetic '
                'type variable do nothing; re-apply acmd_ext_cave.py last')


def check_effect_heap(inst, name, rep):
    """E9: a bank too big for the one effect heap every bank in a match shares (eft writes through the NULL of the
    failed allocation: a crash at match load, Sephiroth test 61)"""
    import tempfile
    import effect_heap_patch
    import kind_expand as K
    patched = None
    rpx = inst.get('code/cross_f.rpx') if 'code/cross_f.rpx' in inst.files else None
    if rpx:
        with tempfile.NamedTemporaryFile(suffix='.rpx') as f:
            f.write(rpx)
            f.flush()
            img = K.Image(f.name)
            patched = all(img.w(a) == w for a, w in effect_heap_patch.patches().items())
    for path in inst.glob(r'fighter/%s/effect/[^/]+/[^/]+\.ptcl' % re.escape(name)):
        try:
            mib = effect_heap_estimate(inst.get(path)) / 2 ** 20
        except Exception:                     # noqa: BLE001
            continue
        if HEAP_VANILLA_WARN < mib <= HEAP_VANILLA_MAX and not patched:
            rep.add('WARN', 'E9 effect-heap', '%s: ~%.1f MiB of the 44 MiB effect heap every bank shares (~%.1f crashed '
                    'at load in a 1v1): tools/effect_heap_patch.py for more players / bigger opponents' % (
                        path, mib, HEAP_VANILLA_MAX))
        if mib > HEAP_VANILLA_MAX and not patched:
            rep.add('ERROR', 'E9 effect-heap', '%s: ~%.1f MiB of the 44 MiB effect heap every bank shares (over ~%.1f '
                    'crashed at load): the executable needs tools/effect_heap_patch.py (%s)' % (
                        path, mib, HEAP_VANILLA_MAX, 'not in the install' if patched is False else 'no executable'))
        elif mib > HEAP_PATCHED_WARN:
            rep.add('WARN', 'E9 effect-heap', '%s: ~%.1f MiB of the 60 MiB effect heap: crowded with several of him or '
                    'big-bank opponents (fewer shader entries / emitters)' % (path, mib))


def check_effects(inst, name, rep):
    """E4: a mesh of eft's particle type 4 aims its Y along the particle's world motion (cross_f's type-4
    vertex programs: X = normalize(emitter Y x motion), Z = X x motion); a particle that never moves has no
    frame and every vertex lands on its position: drawn as nothing (Squirtle's down-smash dust crown,
    sys_whirlwind_l / r, test 14). Non-following, with no velocity and no gravity: always so (ERROR);
    following the fighter (follow type 0): whenever the bone stands still (WARN)"""
    import ptcl
    import struct as st
    for path in inst.glob(r'fighter/%s/effect/[^/]+/[^/]+\.ptcl' % re.escape(name)):
        try:
            p = ptcl.Ptcl(inst.get(path))
        except Exception:                     # noqa: BLE001
            continue
        universal = check_universal(p, rep)
        still, follow = [], []
        for si in range(len(p.sets)):
            for x in p.sets[si]['emitters']:
                d = x['data']
                if d is None or p.field(d, 'particle_type') != 4 or p.field(d, 'primitive_index') < 0 \
                        or p.field(d, 'shader_index') in universal:
                    continue          # (a universal shader frames its mesh with Ultimate's own program)
                speed = abs(p.field(d, 'figure_velocity')) + abs(p.field(d, 'emitter_velocity'))
                grav = sum(abs(v) for v in p.field(d, 'gravity'))
                if speed > 1e-4 or grav > 1e-6:
                    continue
                label = '%s/%s' % (p.set_name(si), p.emitter_name(d))
                (follow if st.unpack_from('>I', bytes(d), 0x310)[0] == 0 else still).append(label)
        # E5: a type-4 mesh that only ever moves along its emitter's Y (no all-direction speed, no spread,
        # emitted along +-Y, gravity along Y, the emitter unturned): X = emitter Y x motion is zero, every
        # vertex of its width on one line: drawn as nothing (Squirtle's up-smash water columns, eft2 type-5
        # meshes, test 15; convert as type 3, eft2's type 5 being a directional billboard). Converted sets only: the
        # base's own vanilla sets are eft art the game draws as they are (Byleth's bank: ZSS's PtcSzerosuitSmashArc)
        own = 'Ptc' + name[:1].upper() + name[1:]
        upright = []
        for si in range(len(p.sets)):
            if not p.set_name(si).startswith(own):
                continue
            for x in p.sets[si]['emitters']:
                d = x['data']
                if d is None or p.field(d, 'particle_type') != 4 or p.field(d, 'primitive_index') < 0 \
                        or p.field(d, 'shader_index') in universal:
                    continue          # (a universal shader frames its mesh with Ultimate's own program)
                dr, g = p.field(d, 'emit_direction'), p.field(d, 'gravity')
                if abs(p.field(d, 'figure_velocity')) > 1e-4 or abs(p.field(d, 'emitter_velocity')) < 1e-4 \
                        or abs(dr[0]) > 1e-3 or abs(dr[2]) > 1e-3 or abs(p.field(d, 'dispersion_angle')) > 1e-3 \
                        or abs(g[0]) > 1e-6 or abs(g[2]) > 1e-6 or any(abs(v) > 1e-4 for v in p.field(d, 'emitter_rotation')):
                    continue
                upright.append('%s/%s' % (p.set_name(si), p.emitter_name(d)))
        # E8: a converted Ultimate line (eft2 volume 12 / 13: its own line_length, line_center, num_divide_line points
        # along Z) must be eft's line with the length in the radius's z (x, y 0) and its points an emission (cross_f
        # 0x04A51B08). Sephiroth test 73: the length / count weren't written (radius eft2's default 10, 10, 10, one
        # point): Scintilla's wall rows one hexagon each; test 74 laid them along X as arcs of a radius-1000 circle:
        # each hexagon a fin across its row (user: "stiff and still incorrect")
        own = 'Ptc' + name[:1].upper() + name[1:]
        lines = []
        for si in range(len(p.sets)):
            if not p.set_name(si).startswith(own):
                continue
            for x in p.sets[si]['emitters']:
                d = x['data']
                if d is None:
                    continue
                vt, r = p.field(d, 'volume_type'), p.field(d, 'volume_radius')
                if (vt in (12, 13) and (abs(r[0]) > 1e-4 or abs(r[1]) > 1e-4)) or (vt in (1, 2) and abs(r[0] - 1000) < 1e-3):
                    lines.append('%s/%s' % (p.set_name(si), p.emitter_name(d)))
        if lines:
            rep.add('ERROR', 'E8 eft-line-volume', '%d converted lines without their own length along Z (a default '
                    'radius, or test 74\'s arcs along X): reconvert with vfxb_to_ptcl.py: %s' % (len(lines), ', '.join(lines[:8])))
        if upright:
            rep.add('ERROR', 'E5 upright-type4-mesh', '%d type-4 meshes move only along their emitter\'s Y: '
                    'eft\'s X (emitter Y x motion) is zero, drawn as nothing (eft2 type 5: convert as type 3): %s'
                    % (len(upright), ', '.join(upright[:8])))
        if still:
            rep.add('ERROR', 'E4 still-type4-mesh', '%d type-4 meshes never move (no velocity, gravity, follow): eft '
                    'draws each as a point (convert as type 1, the emitter\'s frame): %s' % (len(still), ', '.join(still[:8])))
        if follow:
            rep.add('WARN', 'E4 still-type4-mesh', '%d type-4 meshes move only with their bone: drawn as a point '
                    'while it stands still: %s' % (len(follow), ', '.join(follow[:8])))


def check_vec_targets(src, name, ult, rep):
    """S10: every move whose Ultimate game script carries the hit fighter to a point (angle 368 +
    AttackModule::set_vec_target_pos) has its MSC pull. Smash 4 has no such hitbox field (366 / 367 only take the victim
    along with the hitbox's motion, 366 only off the ground): written as 366 alone, Sephiroth's up tilt left grounded
    fighters on the floor under the sword (test 151's fix, edge_hi3_pull, is the method). Done when the fighter's MSC
    source has the generated function (tools/vec_target.py msc: its comment `vec_target: SCRIPT`) or port.json
    `vec_target.hand_made` names the script (with how it is done)"""
    import vec_target as VT
    dump = src.dump(ult)
    d = os.path.join(dump, ult) if dump else None
    if not d or not os.path.isdir(d):
        rep.add('NOTE', 'S10 vec-target', 'no script dump for %s: set_vec_target_pos moves not checked' % ult)
        return
    moves = [k for k, v in VT.scan(d).items() if v['targets']]
    if not moves:
        return
    c = os.path.join(ROOT, 'fighters', name, name + '.c')
    text = open(c, encoding='utf-8', errors='replace').read() if os.path.exists(c) else ''
    hand = load_port_cfg(name).get('vec_target', {}).get('hand_made', {})
    missing = [m for m in moves if 'vec_target: %s ' % m not in text and m not in hand]
    if missing:
        rep.add('ERROR', 'S10 vec-target', 'Ultimate carries the hit fighter to a point (set_vec_target_pos) in %s: no MSC '
                'pull in fighters/%s/%s.c (tools/vec_target.py msc, called from the per-frame hook; or port.json '
                'vec_target.hand_made): the converted 366 leaves grounded fighters where they were hit'
                % (', '.join(missing), name, name))
    else:
        rep.add('INFO', 'S10 vec-target', 'set_vec_target_pos moves pulled in MSC: %s' % ', '.join(
            '%s (%s)' % (m, 'hand-made' if m in hand else 'generated') for m in moves))


def _c_funcs(name):
    """{function name: body} of a fighter's MSC C source (fighters/NAME/NAME.c), {} without one"""
    c = os.path.join(ROOT, 'fighters', name, name + '.c')
    if not os.path.exists(c):
        return {}
    text = open(c, encoding='utf-8', errors='replace').read()
    return {m.group(1): m.group(2) for m in re.finditer(r'\n(?:int|void|float|bool)\s+(\w+)\s*\([^)]*\)\s*\{(.*?)\n\}', text,
                                                          re.S)}


def _reach(funcs, start, depth=3):
    """start's body and the bodies of the functions it calls (and func_78 loops), `depth` calls deep"""
    seen, todo, out = set(), [(start, 0)], []
    while todo:
        f, d = todo.pop()
        if f in seen or f not in funcs:
            continue
        seen.add(f)
        out.append(funcs[f])
        if d < depth:
            todo += [(g, d + 1) for g in re.findall(r'\b(\w+)\(', funcs[f]) + re.findall(r'func_78\((\w+)\)', funcs[f])
                     if g in funcs]
    return '\n'.join(out)


def check_tether_latch(name, rep):
    """S17 tether-latch: the base's tether status (0xF1 AirCatch) hands over to the port's own hit / latch status
    (registered for 0x15B), but its end still runs the common AirCatch end (func_127: the whip article removed unless the
    next status is the ledge's 0xF2 / 0xF3) on that change too: the sword vanishes the moment it meets the wall or the
    fighter it holds (Byleth v9, user's trim frame 128). ERROR"""
    funcs = _c_funcs(name)
    if not funcs:
        return
    src = open(os.path.join(ROOT, 'fighters', name, name + '.c'), encoding='utf-8', errors='replace').read()
    own_hit = re.search(r'sv_set_mem\(0x1, 0x1, 0x15b, (\w+)\)', src)
    ends = [m.group(1) for m in re.finditer(r'sv_set_mem\(0x1, 0x2, 0xf1, (\w+)\)', src)]
    if not own_hit or not ends or re.fullmatch(r'func_\d+', own_hit.group(1)):
        return
    body = funcs.get(ends[-1], '')
    if re.search(r'^\s*func_127\(\);', body, re.M) and not re.search(r'global6\s*!=\s*0x15b', body):
        rep.add('ERROR', 'S17 tether-latch', '%s.c: the tether status 0xF1\'s end %s removes the tether (func_127) also '
                'when it hands over to the port\'s latch / hit status 0x15B (%s): the sword is gone while it holds'
                % (name, ends[-1], own_hit.group(1)))


def check_pull_gravity(name, rep):
    """S18 pull-gravity: a status that pulls the fighter with kinetic energy 3 (KineticModule(0x11, 3, x, y) with a y
    that isn't 0) under kinetic type 0xA (AIR_STOP: the gravity energy 1 still runs) without stopping the gravity energy
    (KineticModule(0x2717, 1) or its speed set to 0 each frame): he sinks under the pull, which loses to his fall speed
    (Byleth v9's SpecialAirHiHit: pulled up at 4.1 a frame, fell for 30 frames under the wall). ERROR per status"""
    funcs = _c_funcs(name)
    if not funcs:
        return
    src = open(os.path.join(ROOT, 'fighters', name, name + '.c'), encoding='utf-8', errors='replace').read()
    bad = []
    for st, main in re.findall(r'sv_set_mem\(0x1, 0x1, (0x[0-9a-f]+), (\w+)\)', src):
        if re.fullmatch(r'func_\d+', main) or main not in funcs or 'KineticModule(0, 0xa)' not in funcs[main]:
            continue
        reach = _reach(funcs, main, 4)
        pull_fn = [f for f, b in funcs.items() if re.search(r'KineticModule\(0x11, 0x3, [^;]*, y\);', b)]
        direct = [y for f in [main] + re.findall(r'\b(\w+)\(', reach) if f in funcs and f not in pull_fn
                  for y in re.findall(r'KineticModule\(0x11, 0x3, [^;]*?, ([^;,]+)\);', funcs[f])]
        via = [a for f in pull_fn for a in re.findall(r'\b%s\(([^;]*)\);' % f, reach)]
        moving = any(v.strip() not in ('0', '0.0f', 'y') for v in direct + via)
        if moving and 'KineticModule(0x2717, 0x1)' not in reach and 'KineticModule(0x11, 0x1, 0)' not in reach:
            bad.append('%s (%s)' % (st, main))
    if bad:
        rep.add('ERROR', 'S18 pull-gravity', '%s.c: statuses that pull him on kinetic energy 3 under AIR_STOP (0xA) with '
                'the gravity energy running: he sinks under the pull: %s' % (name, ', '.join(bad)))


def check_loop_speed(name, rep):
    """S21 loop-speed (WARN): a status whose per-frame loop (func_78) moves the fighter by setting kinetic energy 3's
    speed with a y that isn't 0. In game this didn't move Byleth at all (v10's SpecialAirHiHit reel: the diag log's
    height under the target the same for 20 frames, v9's trim: he sank under it), while speeds set in a status's main
    did (v9's wall jump). Move him by the self-move position variables (0x0F000004 / 5) or set the speed in a main"""
    funcs = _c_funcs(name)
    if not funcs:
        return
    pull_fn = [f for f, b in funcs.items() if re.search(r'KineticModule\(0x11, 0x3, [^;]*, y\);', b)]
    bad = []
    for f, b in funcs.items():
        for loop in re.findall(r'func_78\((\w+)\)', b):
            if loop not in funcs or re.fullmatch(r'func_\d+', loop):
                continue
            reach = _reach(funcs, loop, 3)
            direct = [y for g in [loop] + re.findall(r'\b(\w+)\(', reach) if g in funcs and g not in pull_fn
                      for st in re.findall(r'KineticModule\(0x11, 0x3, [^;]*\);', funcs[g]) if 'KineticModuleF(' not in st
                      for y in re.findall(r', ([^,]+)\);$', st)]
            via = [v for g in pull_fn for v in re.findall(r'\b%s\(([^;]*)\);' % g, reach)]
            if any(v.strip() not in ('0', '0.0f', 'y') and 'KineticModuleF(' not in v for v in direct + via):
                bad.append(loop)      # (a y read back from the energy keeps its speed: not a move)
    if bad:
        rep.add('WARN', 'S21 loop-speed', '%s.c: loops that move the fighter by energy 3 speeds (they didn\'t move '
                'Byleth in game): %s' % (name, ', '.join(sorted(set(bad)))))


FOOT_EFFECT = 0xC84B610E       # ACMD Graphic_Effect: Ultimate's FOOT_EFFECT (reference/spreadsheets Sm4sh_params ACMD events)


def check_foot_effects(inst, name, rep):
    """E14 foot-effect: an effect of the fighter's own bank (not the common 0x100 dust) requested with Graphic_Effect,
    the game's FOOT_EFFECT: its handler (0x02BE1444) asks EffectModule vt +0x32C (foot effects on: +0x9F / +0xA0 clear)
    and plays nothing when they're off, as in the air (every vanilla use is the common run / dash / turn dust and
    footsteps on the ground). Byleth v11 put Ultimate's catch effects (the sword's EFFECT_FOLLOW) in SpecialAirHiHit's
    effect script so: they never showed (user's v11 test). ERROR in a script named for an air move ('air' in the name),
    WARN elsewhere; the port's own copies of the common dust (its effects json's sys_* ids) are left out"""
    eff = scripts(inst, 'fighter/%s/script/animcmd/body/effect.bin' % name)
    if not eff:
        return
    names = {acmd.crc(n): n for n in vocabulary()}
    dust = set()                 # the port's own copies of the common dust (fighters/NAME/NAME_effects.json sys_*)
    for f in glob.glob(os.path.join(ROOT, 'fighters', name, '*_effects.json')):
        for k, v in json.load(open(f)).items():
            if k.startswith('sys_') and isinstance(v, str) and v.startswith('0x'):
                dust.add(int(v, 16))
    air, other = [], []
    for k, sc in eff.items():
        ids = sorted({int(c.params[0]) for c in sc if c.ident == FOOT_EFFECT and c.params
                      and int(c.params[0]) >> 16 not in (0, 0x100) and int(c.params[0]) not in dust})
        if not ids:
            continue
        n = names.get(k, '%08X' % k)
        (air if 'air' in n else other).append('%s (%s)' % (n, ', '.join('0x%X' % i for i in ids)))
    if air:
        rep.add('ERROR', 'E14 foot-effect', 'own effects requested as FOOT_EFFECT (Graphic_Effect: played only while '
                'foot effects are on, never in the air) in air moves: %s; use Graphic_Effect2 (EFFECT) / a following '
                'one, or MSC' % '; '.join(air))
    if other:
        rep.add('WARN', 'E14 foot-effect', 'own effects requested as FOOT_EFFECT (Graphic_Effect: ground only): %s'
                % '; '.join(other))


def check_frame_waits(inst, name, rec, rep):
    """S23 frame-past-end: a game script command (or an MSC wait, port.json "frame_waits": {slot: [frames]}) on a frame
    past its motion's last one (the own slots' animations, extra_kinds.json "motions"). A non-looping motion stands on
    its last frame: script time stops there (the command never runs) and an MSC test of MotionModuleF(1) never comes
    true. Byleth v13: SpecialAirHiHit's motion is Ultimate's 15 frames, its stop waited for frame 19 and its script sent
    the sword back at 19: everything froze for good after a catch (user's v13 test, log k8 5021 for 35 s; the script's
    19 had never run in v9 - v12 either: the sword stayed full length through the reel). ERROR for a declared wait,
    WARN for a script command"""
    import tempfile
    import omo
    pac = inst.get('fighter/%s/motion/body/main.pac' % name)
    game = scripts(inst, 'fighter/%s/script/animcmd/body/game.bin' % name)
    if pac is None or not game:
        return
    with tempfile.TemporaryDirectory() as td:
        pp = os.path.join(td, 'main.pac')
        open(pp, 'wb').write(pac)
        frames = {n[:-4]: omo.Omo(d).frames for n, d in omo.pac_read(pp)}
    waits = load_port_cfg(name).get('frame_waits') or {}
    bad, soft = [], []
    for slot, v in sorted((rec.get('motions') or {}).items()):
        if not isinstance(v, dict) or v.get('anim') not in frames:
            continue
        n = frames[v['anim']]
        key = re.sub(r'^Fit\w+?Main[A-Z]\d\d', '', v['anim']).lower()
        sc = game.get(acmd.crc(key)) or []
        fr = [float(c.params[0]) for c in sc if c.name == 'FRAME']
        late = sorted({f for f in fr if f > n - 1})
        if late:
            soft.append('%s %s (%d frames): FRAME %s' % (slot, key, n, ', '.join('%g' % f for f in late)))
        w = [f for f in waits.get(slot, []) if not str(f).startswith('_')]
        if w and max(w) > n - 1:
            bad.append('%s %s (%d frames): waits for %g' % (slot, key, n, max(w)))
    if bad:
        rep.add('ERROR', 'S23 frame-past-end', 'MSC waits for a motion frame past its motion\'s end (it stands on its '
                'last frame: the wait never ends): %s' % '; '.join(bad))
    if soft:
        rep.add('WARN', 'S23 frame-past-end', 'script commands past their motion\'s last frame (never run if the motion '
                'doesn\'t loop): %s' % '; '.join(soft))


HIT_CMDS = ('Hitbox', 'Special_Hitbox', 'Extended_Hitbox', 'Extended_Special_Hitbox', 'Extra_Special_Hitbox')


def check_status_hit_log(inst, name, rep):
    """S22 status-hit-log: scripts one status plays in turn (port.json "status_scripts": {status: [script, ...]}, e.g.
    Byleth's 0x15B: SpecialAirHiHit then SpecialAirHiOvertake) whose hitboxes share a Part: a Part's "already hit"
    record lasts the whole status (docs/acmd-extra-commands.md "Hit_Log_Clear"), so the later script's hit can't land on
    a fighter the earlier one hit. Byleth v11: the catching hit (Part 0) then the overtake's hit (Part 0) on the same
    fighter: "the follow-up never hits". ERROR, unless a Hit_Log_Clear of that Part comes first"""
    cfg = load_port_cfg(name).get('status_scripts') or {}
    game = scripts(inst, 'fighter/%s/script/animcmd/body/game.bin' % name)
    if not cfg or not game:
        return
    bad = []
    for st, seq in cfg.items():
        if st.startswith('_'):
            continue
        seen = {}
        for sname in seq:
            sc = game.get(acmd.crc(sname)) or []
            cleared, parts = set(), set()
            for c in sc:
                if c.name == 'Hit_Log_Clear' and c.params:
                    cleared |= set(seen) if int(c.params[0]) == -1 else {int(c.params[0])}
                elif c.name in HIT_CMDS:
                    part = int(c.params[c.info['syntax'].index('Part')])
                    if part in seen and part not in cleared:
                        bad.append('%s %s after %s (Part %d)' % (st, sname, seen[part], part))
                        cleared.add(part)            # one report a Part
                    parts.add(part)
            for part in parts:
                seen.setdefault(part, sname)
    if bad:
        rep.add('ERROR', 'S22 status-hit-log', 'a later script of one status hits on a Part an earlier one already '
                'hit with (its hit record lasts the status: the later hit can\'t land on the same fighter): %s; give it '
                'another Part or Hit_Log_Clear first' % '; '.join(bad))


def check_vec_pull_angle(inst, src, name, ult, rep):
    """S19 vec-pull-angle: a hit Ultimate writes at 368 with set_vec_target_pos (the fighter carried to a point) on its
    body (`top`, bone 0 here) left at the translator's 366: Smash 4's 366 takes the hitbox's own motion over the frame,
    which for bone 0 is the fighter's, its y raised to the common minimum: the fighter is launched up instead of carried
    (Byleth v9's ground up special at 16, user's clip 2: DK 0 -> 1 %, off the top in 3 frames, never in the sword's
    reach). The MSC pull (S10) carries it; the hit wants a plain angle (master_build.pull_angles). ERROR per script"""
    import vec_target as VT
    dump = src.dump(ult)
    d = os.path.join(dump, ult) if dump else None
    game = scripts(inst, 'fighter/%s/script/animcmd/body/game.bin' % name)
    if not d or not os.path.isdir(d) or not game:
        return
    import acmd
    bad = []
    for script, v in VT.scan(d).items():
        tops = {(e['frame'], e['id']) for e in v['targets'] if e['hitbox']['bone'] == 'top'}
        sc = game.get(acmd.crc(script.lower())) or (game.get(acmd.crc('aircatch')) if script == 'SpecialAirHi' else None)
        if not tops or not sc:
            continue
        left = sorted({fr for fr, c in _frames(sc) if c.name in ('Special_Hitbox', 'Extended_Special_Hitbox')
                       and (fr, c.params[0]) in tops and int(c.params[c.info['syntax'].index('Angle')]) == 366
                       and int(c.params[c.info['syntax'].index('Bone')]) == 0})
        if left:
            bad.append('%s (frames %s)' % (script, ', '.join('%g' % f for f in left)))
    if bad:
        rep.add('ERROR', 'S19 vec-pull-angle', 'Ultimate\'s 368 body hits (set_vec_target_pos) left at 366 on bone 0 (its '
                'motion is the body\'s: the fighter is launched up, not carried): %s' % '; '.join(bad))


def check_add_speed(src, name, ult, rep):
    """S20 add-speed: an Ultimate game script that moves the fighter itself (KineticModule::add_speed / set_speed /
    add_speed_outside) has no ACMD equivalent in the translation (dropped): the port's MSC must do it, its source naming
    the script with the call (a comment `SCRIPT's KineticModule::add_speed`). Byleth v1 - v9: SpecialAirLw's hop at 53
    (0, 1) was missing, so a landing at 53 - 60 cancelled Aymr before its hit (user: "landing around the hitbox frame
    gives no hitbox"). ERROR"""
    dump = src.dump(ult)
    d = os.path.join(dump, ult) if dump else None
    if not d or not os.path.isdir(d):
        return
    c = os.path.join(ROOT, 'fighters', name, name + '.c')
    text = open(c, encoding='utf-8', errors='replace').read() if os.path.exists(c) else ''
    missing = []
    for f in sorted(os.listdir(d)):
        if not f.endswith('.txt'):
            continue
        body = open(os.path.join(d, f), errors='replace').read()
        m = re.search(r'fn game_\w+\(agent[^{]*\{(.*?)\n\}', body, re.S)
        if m and re.search(r'KineticModule::(add_speed|set_speed|add_speed_outside)\(', m.group(1)):
            script = f[:-4]
            if not re.search(r"%s's KineticModule::" % re.escape(script), text):
                missing.append(script)
    if missing:
        rep.add('ERROR', 'S20 add-speed', 'Ultimate game scripts that move the fighter (KineticModule::add_speed / '
                'set_speed): not done in fighters/%s/%s.c (a comment "SCRIPT\'s KineticModule::..." where it is): %s'
                % (name, name, ', '.join(missing)))


def check_hit_sound(inst, name, src, ult, rep):
    """S25 hit-sound: a hitbox whose SFXType is 0 (Smash 4's "Nothing") where Ultimate's hitbox sounds (its
    COLLISION_SOUND_ATTR is not NONE; matched by damage / knockback / size: tools/hit_sound_fix.py). Byleth v1 - v15:
    ultimate_acmd's SFX_TYPE didn't list COLLISION_SOUND_ATTR_MASTER_AXE / _MASTER_ATTACK100END / _MASTER_ARROW_MAX and
    took 0 for them: Aymr (down special, down smash, down air), the rapid jab's finisher and the max arrow hit in
    silence (user, v15: "down special has no hit sound"). ERROR. Also WARN: an attribute in the fighter's dump that
    SFX_TYPE doesn't list (ultimate_acmd.sfx_type's stand-in)"""
    import hit_sound_fix as H
    import ultimate_acmd as U
    dump = src.dump(ult)
    if not dump or not os.path.isdir(dump):
        return
    table = H.attack_sounds(dump)
    unlisted = sorted({a for attrs in table.values() for a in attrs if a not in U.SFX_TYPE})
    if unlisted:
        rep.add('WARN', 'S25 hit-sound', 'Ultimate hit sound attributes ultimate_acmd.SFX_TYPE doesn\'t list (a '
                'stand-in sound): ' + ', '.join(unlisted))
    bad = {}
    for rel in sorted(inst.files):
        if not (rel.startswith('fighter/%s/script/animcmd/' % name) and rel.endswith('/game.bin')):
            continue
        for h, c, attr in H.scan(table, scripts(inst, rel) or {}):
            bad.setdefault(rel.split('/animcmd/')[1].rsplit('/', 1)[0], set()).add('%08X %s' % (h, attr[21:]))
    if bad:
        rep.add('ERROR', 'S25 hit-sound', 'silent hitboxes (SFXType 0; Ultimate\'s sound; fix: tools/hit_sound_fix.py '
                '--fix): ' + '; '.join('%s: %s' % (k, ', '.join(sorted(v))) for k, v in sorted(bad.items())))


def check_result_faces(inst, name, base, vanilla, rep):
    """F3 result-face: a costume's result-pose face entries (J02Win* / J02Lose in material_anime_face.pac and
    material_anime_face_lang.pac, the results scene's per-language pac) still the base fighter's own (byte for byte its
    vanilla entry): the base's keys drive the base's mouth slots, which hold the port's mouths and weapons. Byleth v1 -
    v15: ultimate_fighter's motions step wrote face entries for motion/body only; ZSS's _lang Win1Wait / Win2Wait /
    Win3 / Win3Wait hide every mouth and show Mouth_Result (his sword): user, v15: "their face is missing their mouth in
    victory animations" (fix: ultimate_fighter.result_faces, run by the motions step; `result-faces` on an install).
    ERROR"""
    import omo
    bad = {}
    for d in sorted({os.path.dirname(c) for c in inst.glob(
            r'fighter/%s/model/body/[cl]\d\d/material_anime_face(_lang)?\.pac' % name)}):
        tag = d.split('/')[-1]
        for pac in ('material_anime_face.pac', 'material_anime_face_lang.pac'):
            data = inst.get(d + '/' + pac)
            vp = os.path.join(vanilla or '', 'fighter', base.get('base', ''), 'model', 'body', 'c00', pac)
            if data is None or not vanilla or not os.path.exists(vp):
                continue
            van = dict(omo.pac_read(vp))
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(data)
            try:
                ents = omo.pac_read(f.name)
            finally:
                os.unlink(f.name)
            same = [n[:-4] for n, x in ents if ('J02Win' in n or 'J02Lose' in n) and van.get(n) == x]
            if same:
                bad.setdefault(tag, []).append('%s: %s' % (pac, ', '.join(s[s.index('J02') + 3:] for s in same)))
    if bad:
        rep.add('ERROR', 'F3 result-face', 'result poses with the base\'s face entries (its mouth keys on the port\'s '
                'slots; ultimate_fighter.py result-faces): ' + '; '.join('%s %s' % (k, ' / '.join(v))
                                                                          for k, v in sorted(bad.items())))


def _acmd_load(data):
    import acmd
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(data)
    try:
        return acmd.ACMDFile.load(f.name)
    finally:
        os.unlink(f.name)


def _script_frames(f, sc, seen=None):
    """[(frame, command)] of a flat script (FRAME / WAIT followed; one JUMP followed); None with a condition block"""
    out, t = [], 0.0
    seen = seen or set()
    for c in sc:
        if c.name in ('True', 'False', 'Else', 'IS_FLAG', 'IS_NOT_FLAG', 'Float_Var_Compare', 'Var_Compare'):
            return None
        if c.name == 'FRAME':
            t = max(t, float(c.params[0]))
        elif c.name == 'WAIT':
            t += float(c.params[0])
        elif c.name == 'JUMP':
            h = c.params[0]
            if h in f.scripts and h not in seen:
                seen.add(h)
                rest = _script_frames(f, f.scripts[h], seen)
                if rest is None:
                    return None
                out += [(t + ft, x) for ft, x in rest]
            break
        else:
            out.append((t, c))
    return out


def check_weapon_twice(inst, name, rep):
    """S27 weapon-twice (Byleth v17, user: "the sword will appear twice in taunts"): a port whose held weapon is both a
    body mesh (its visibility in the face pac's keys) and an article (Byleth: the Sword of the Creator, master_sword in
    the body and the whip article 2) must never draw both: on every frame of a body game script the article is out and
    drawn (its own game script's Visibility for the slot it plays, Article_Visibility), the body's weapon mesh is hidden.
    port.json "weapon_article": {"article", "vis" (the face pac's slot), "folder" (the article's script folder)}. Also an
    ERROR: the article made in a script whose Ultimate game script never touches that article (the base's own whip left:
    ZSS's side taunt and Win1 in Byleth v1 - v16)"""
    cfg = load_port_cfg(name).get('weapon_article')
    if not cfg:
        return
    import mta
    import mtable
    import omo
    import tempfile
    art, vis_name, folder = cfg['article'], cfg['vis'], cfg['folder']
    g = inst.get('fighter/%s/script/animcmd/body/game.bin' % name)
    face = inst.get('fighter/%s/model/body/c00/material_anime_face.pac' % name)
    ag = inst.get('fighter/%s/script/animcmd/weapon/%s/game.bin' % (name, folder))
    amt = inst.get('fighter/%s/script/animcmd/weapon/%s/motion.mtable' % (name, folder))
    if not (g and face and ag and amt):
        return
    game, agame = _acmd_load(g), _acmd_load(ag)
    slots = struct.unpack('>%dI' % (len(amt) // 4), amt)
    with tempfile.NamedTemporaryFile(suffix='.pac', delete=False) as f:
        f.write(face)
    try:
        ents = omo.pac_read(f.name)
    finally:
        os.unlink(f.name)
    keys = {}
    for n, d in ents:
        if n.endswith('.mta') and d.startswith(b'MTA4'):
            m = mta.read(d)
            v = [x for x in m['vis'] if x['name'] == vis_name]
            short = re.sub(r'^Fit\w+?(Body|Entry)Main[A-Z]\d\d', '', n[:-4]).lower()
            keys[short] = (m['frames'], v[0]['keys'] if v else [(0, 1, 0)])
    names = {mtable.crc(w): w for w in vocabulary()}

    def art_vis(slot, t):
        h = slots[slot] if 0 <= slot < len(slots) else None
        on = 1
        for ft, c in (_script_frames(agame, agame.scripts.get(h, [])) or []):
            if c.name == 'Visibility' and ft <= t:
                on = int(c.params[0])
        return on

    twice, left = [], []
    dump = None
    try:
        import port_sources
        d = port_sources.load().dump(port_sources.ult_name(name))
        dump = os.path.join(d, port_sources.ult_name(name)) if d else None
    except Exception:
        dump = None
    for h, sc in game.scripts.items():
        if not any(c.name in ('GENERATE_ARTICLE', 'Set_Anchored_Article_Action') and c.params and c.params[0] == art
                   for c in sc):
            continue
        sname = names.get(h, '0x%08X' % h)
        if dump and sname in ('appealsr', 'appealsl', 'appealhir', 'appealhil', 'win1', 'win2', 'win3'):
            uf = os.path.join(dump, {'appealsr': 'AppealSR', 'appealsl': 'AppealSL', 'appealhir': 'AppealHiR',
                                     'appealhil': 'AppealHiL', 'win1': 'Win1', 'win2': 'Win2', 'win3': 'Win3'}[sname] + '.txt')
            if os.path.exists(uf) and 'generate_article' not in open(uf, errors='replace').read():
                left.append(sname)
        fr = _script_frames(game, sc)
        k = keys.get(sname) or keys.get(sname[:-1] if sname.endswith(('r', 'l')) else sname)
        if fr is None or k is None:
            continue
        n, bkeys = k
        out, avis, slot, start, both = False, 1, None, 0.0, []
        evs = sorted(fr, key=lambda x: x[0])
        for t in range(int(n) + 1):
            for ft, c in evs:
                if int(ft) != t or not c.params or c.params[0] != art:
                    continue
                if c.name == 'GENERATE_ARTICLE':
                    out, slot = True, None
                elif c.name == 'Remove_Article':
                    out = False
                elif c.name == 'Article_Visibility':
                    avis = int(c.params[1])
                elif c.name == 'Set_Anchored_Article_Action':
                    slot, start = int(c.params[1]), float(t)
            body = ([kv[1] for kv in bkeys if kv[0] <= t][-1:] or [1])[0]
            drawn = out and avis and (slot is None or art_vis(slot, t - start))
            if drawn and body:
                both.append(t)
        if both:
            twice.append('%s frames %d-%d' % (sname, both[0], both[-1]))
    if twice or left:
        rep.add('ERROR', 'S27 weapon-twice', 'the body\'s %s and article %d both drawn: %s%s' % (
            vis_name, art, '; '.join(sorted(twice)) or '-',
            '; the article made where Ultimate\'s script makes none (the base\'s leftover): %s' % ', '.join(sorted(left))
            if left else ''))


HOLD_SCRIPTS = ('attack100', 'attack100sub')


def _ult_holding_ids(name):
    """{Smash 4 script name (Ultimate's file name lowercased): {hitbox IDs Ultimate makes as holding multi-hits}} from
    the port's Ultimate dumps (ultimate_acmd.holding: setoff off, 361, small knockback); None without dumps"""
    try:
        import port_sources
        import ultimate_acmd as U
        d = port_sources.load().dump(port_sources.ult_name(name))
        dump = os.path.join(d, port_sources.ult_name(name)) if d else None
    except Exception:              # noqa: BLE001
        return None
    if not dump or not os.path.isdir(dump):
        return None
    pat = re.compile(r'macros::ATTACK\(agent,\s*(\d+),\s*\d+,\s*Hash40::new\("[^"]*"\),\s*([-\d.]+),\s*(\d+),'
                     r'\s*(\d+),\s*(\d+),\s*(\d+),(?:[^,]*,){9}\s*\*(ATTACK_SETOFF_KIND_\w+)')
    out = {}
    for f in glob.glob(os.path.join(dump, '*.txt')):
        for m in pat.finditer(open(f, errors='replace').read()):
            hid, dmg, ang, kbg, fkb, bkb, setoff = m.groups()
            if U.holding(int(ang), int(kbg), int(fkb), int(bkb), setoff, float(dmg)):
                out.setdefault(os.path.basename(f)[:-4].lower(), set()).add(int(hid))
    return out


def check_rapid_slide(inst, name, rep):
    """S28 rapid-slide (Byleth v17: "the rapid jab's hits don't connect properly"; rapid_setoff v1): a holding
    multi-hit - an Ultimate hit with ATTACK_SETOFF_KIND_OFF, angle 361 and a small knockback (the port's dumps; without
    them a rapid-jab loop hit at 361 / under 20 degrees with KBG / BKB 30 or less) - converted without the hold:
    Smash 4 slides a grounded victim under 60 knockback at 0 degrees, out of the next hits' reach. The hold is
    Hitbox_Hold(ID or -1, 1 / 2) after the hitbox (tools/hitbox_hold_cave.py, ultimate_acmd's default); ERROR without
    it. v17's workaround (HOLD_ANGLE, ultimate_acmd --hold-angle) is a WARN (for an executable without the cave).
    X8 hold-exe (ERROR): a script using Hitbox_Hold with no executable in the install carrying the cave"""
    import acmd
    import ultimate_acmd as U
    rels = list(inst.glob(r'fighter/%s/script/animcmd/(body|weapon/[^/]+)/game\.bin' % name))
    ult = _ult_holding_ids(name)
    bad, old, uses = [], [], []
    for rel in rels:
        game = _acmd_load(inst.get(rel))
        names = {acmd.crc(n): n for n in list(HOLD_SCRIPTS) + list(ult or {})}
        for h, sc in game.scripts.items():
            if any(c.name == 'Hitbox_Hold' for c in sc):
                uses.append(rel)
            sname = names.get(h)
            want = (ult or {}).get(sname) if ult is not None and '/body/' in rel else None
            if want is None and not (ult is None and sname in HOLD_SCRIPTS and '/body/' in rel):
                continue
            for i, c in enumerate(sc):
                if 'Hitbox' not in c.name or 'Angle' not in c.info['syntax'] or c.name == 'Hitbox_Hold':
                    continue
                d = dict(zip(c.info['syntax'], c.params))
                if want is not None:
                    if d['ID'] not in want:
                        continue
                elif not ((d['Angle'] == 361 or d['Angle'] <= 20) and d['Damage'] > 0 and d['FKB'] == 0
                          and d['KBG'] <= 30 and d['BKB'] <= 30):
                    continue
                held = False
                for c2 in sc[i + 1:]:
                    if c2.name == 'Hitbox_Hold' and c2.params[0] in (d['ID'], -1, 0xFFFFFFFF) and c2.params[1] in (1, 2):
                        held = True
                        break
                    if c2.name == 'Remove_All_Hitboxes' or ('Hitbox' in c2.name and 'Angle' in c2.info['syntax']
                                                            and dict(zip(c2.info['syntax'], c2.params))['ID'] == d['ID']):
                        break
                what = '%s %s id %d angle %d' % (rel.split('/animcmd/')[1], sname, d['ID'], d['Angle'])
                if held:
                    continue
                (old if d['Angle'] == U.HOLD_ANGLE else bad).append(what)
    if bad:
        rep.add('ERROR', 'S28 rapid-slide', 'holding multi-hits (Ultimate\'s setoff off + 361 + a small knockback) without '
                'Hitbox_Hold: they slide a grounded victim out of reach: %s; tools/ultimate_acmd.py (default: Ultimate\'s '
                'angle + Hitbox_Hold)' % ', '.join(sorted(set(bad))))
    if old:
        rep.add('WARN', 'S28 rapid-slide', 'holding multi-hits at v17\'s HOLD_ANGLE %d instead of Ultimate\'s angle + '
                'Hitbox_Hold (ultimate_acmd --hold-angle: only for an executable without tools/hitbox_hold_cave.py): %s'
                % (U.HOLD_ANGLE, ', '.join(sorted(set(old)))))
    if uses and not _exe_has_hold(inst):
        rep.add('ERROR', 'X8 hold-exe', 'Hitbox_Hold in %s but the install\'s code/cross_f.rpx has no hitbox hold '
                '(tools/hitbox_hold_cave.py: exe_v46y_hold or later): the script won\'t load' % ', '.join(sorted(set(uses))))


def _exe_has_hold(inst):
    if 'code/cross_f.rpx' not in inst.files:
        return False
    import tempfile
    import kind_expand as K
    import hitbox_hold_cave as HH
    with tempfile.NamedTemporaryFile(suffix='.rpx') as f:
        f.write(inst.get('code/cross_f.rpx'))
        f.flush()
        try:
            return HH.present(K.Image(f.name).w)
        except Exception:          # noqa: BLE001
            return False


def check_article_status_reuse(inst, name, rep):
    """S29 article-status-reuse (Byleth v17, user: "the whip disappears when catching someone"): a body script that
    changes an article's status (Set_Remote_Article_Action / 2: ZSS's tether whip into another status) and then plays an
    anchored motion on that same article without making a new one (GENERATE_ARTICLE) between: the base never moves its
    tether article into an anchored motion; Byleth v15 / v16 took the tether's whip into status 0 for the up special's
    hit motion and the whip vanished at the catch. Remove it and generate a fresh one (a frame later). ERROR"""
    g = inst.get('fighter/%s/script/animcmd/body/game.bin' % name)
    if not g:
        return
    import mtable
    game = _acmd_load(g)
    names = {mtable.crc(w): w for w in vocabulary()}
    bad = []
    for h, sc in game.scripts.items():
        moved = set()
        for c in sc:
            if not c.params:
                continue
            if c.name in ('Set_Remote_Article_Action', 'Set_Remote_Article_Action2'):
                moved.add(c.params[0])
            elif c.name in ('GENERATE_ARTICLE', 'Remove_Article'):
                moved.discard(c.params[0])
            elif c.name == 'Set_Anchored_Article_Action' and c.params[0] in moved:
                bad.append(names.get(h, '0x%08X' % h))
                break
    if bad:
        rep.add('ERROR', 'S29 article-status-reuse', 'an anchored motion on an article a remote status change moved '
                '(not made anew): %s' % ', '.join(sorted(bad)))


def check_result_param(inst, name, src, rep):
    """R2 result-param (Byleth v17, user: "Byleth doesn't appear in the loss character windows"): the results scene
    frames a loser in its panel with param/ui/result_param.bin's entry for the fighter's model name (eye / to, the win
    poses' frames: tools/result_param.py); a name with no entry gets "missing" (all 0: the camera on its target, the
    panel empty). ERROR when the install's (or the vanilla) result_param.bin has no entry for the port's model name, when
    its entry's eye is its target (all 0), or when the shipped file lacks another added kind's entry (extra_kinds.json:
    the file replaces the whole table); WARN when a win frame is past the port's own J02WinN (or 0 for a win pose it
    has). ultimate_port.py's `result-param` step writes the entry (results_panels_v1).
    F4 display-face (the same test, v17: "the mouth still missing in victory animations"): the face pac's display.mta,
    the state the results scene draws, hides every mouth slot (the base's: ZSS shows only Mouth_Result, his sword)"""
    import result_param as RP
    data = inst.get('param/ui/result_param.bin')
    where = inst.where('param/ui/result_param.bin')
    if data is None and src.get('vanilla'):
        p = os.path.join(src['vanilla'], 'param/ui/result_param.bin')
        if os.path.exists(p):
            data, where = open(p, 'rb').read(), 'vanilla'
    if data is not None:
        ents = {e[0]: e[3] for e in RP.entries(data)[1]}
        if name not in ents:
            rep.add('ERROR', 'R2 result-param', 'param/ui/result_param.bin (%s) has no entry for "%s": its loser panel is '
                    'drawn empty (ultimate_port.py run %s result-param; tools/result_param.py port ... --like BASE)'
                    % (where, name, name))
        else:
            v = ents[name]
            eye, to = (v['eyex'], v['eyey'], v['eyez']), (v['tox'], v['toy'], v['toz'])
            if eye == to:
                rep.add('ERROR', 'R2 result-param', '"%s"\'s loser camera sits on its target (eye = to %s, "missing"\'s '
                        'all-0 framing): the panel is drawn empty' % (name, eye))
            played = win_motions(inst, name)
            bad = ['win%d %g (J02Win%d %s frames)' % (n, v['win%d' % n], n, played.get(n, 'none'))
                   for n in range(1, 6) if played and (v['win%d' % n] > played.get(n, 0) or
                                                       (n in played and n <= 3 and not v['win%d' % n]))]
            if bad:
                rep.add('WARN', 'R2 result-param', '"%s"\'s win frames don\'t fit its win motions: %s (result_param.py '
                        'port: the base\'s scaled by the lengths)' % (name, ', '.join(bad)))
        # the file replaces the whole table: one built from an older file drops the other added fighters' entries
        if inst.get('param/ui/result_param.bin') is not None:
            kinds = json.load(open(os.path.join(HERE, 'extra_kinds.json')))['kinds']
            gone = [r['name'] for r in kinds if r['name'] != name and r['name'] not in ents]
            if gone:
                rep.add('ERROR', 'R2 result-param', 'the shipped param/ui/result_param.bin (%s) has no entry for the other '
                        'added fighters %s: their loser panels go empty (build it on the newest one: port_sources '
                        '"result_param")' % (where, ', '.join(gone)))
    cfg = load_port_cfg(name).get('weapon_article')
    import mta
    import omo
    import tempfile
    bad = []
    for d in sorted({k.rsplit('/', 1)[0] for k in inst.glob(r'fighter/%s/model/body/[cl]\d\d/material_anime_face\.pac' % name)}):
        data = inst.get(d + '/material_anime_face.pac')
        with tempfile.NamedTemporaryFile(suffix='.pac', delete=False) as f:
            f.write(data)
        try:
            ents = dict(omo.pac_read(f.name))
        finally:
            os.unlink(f.name)
        if 'display.mta' not in ents:
            continue
        m = mta.read(ents['display.mta'])
        mouths = [v for v in m['vis'] if re.search(r'Mout[hn]', v['name']) and (not cfg or v['name'] != cfg['vis'])]
        if mouths and not any(v['keys'] and v['keys'][0][1] for v in mouths):
            bad.append(d.rsplit('/', 1)[1])
    if bad:
        rep.add('ERROR', 'F4 display-face', 'display.mta hides every mouth slot (the results scene\'s face: a hole where '
                'the mouth is; ultimate_fighter.display_entry): %s' % ', '.join(bad))


def check_turn_rot(src, name, ult, rep):
    """S26 turn-rot: an Ultimate *Turn status whose game script turns the fighter (REVERSE_LR) and then goes back to the
    move it came from (Byleth's SpecialLwTurn -> SpecialLw at the frame it left). Smash 4's Reverse_Direction (ACMD
    0x63623560, handler 0x02BD42E0) flips the facing only (PostureModule vt+0x84 -> set_lr: +0x60); the model's turn
    (+0x64 rot_y = lr x 90) waits for PostureModule vt+0xC4 (update_rot_y_lr, MSC PostureModule(0x2)), which the
    game calls on a status change: a port that resumes the move in the same status (a motion change) draws him the
    old way until the move ends (user, Byleth v15: "it turns him after the move finishes"). Ultimate's turn motion
    (d03speciallwturn: the hip turns -35 -> 122 degrees) ends on the move's pose turned 180, so the model's facing
    has to flip where the move resumes. The port's MSC must call PostureModule(0x2) there, its source naming the
    script (a comment `SCRIPT's REVERSE_LR`). ERROR"""
    dump = src.dump(ult)
    d = os.path.join(dump, ult) if dump else None
    if not d or not os.path.isdir(d):
        return
    c = os.path.join(ROOT, 'fighters', name, name + '.c')
    text = open(c, encoding='utf-8', errors='replace').read() if os.path.exists(c) else ''
    missing = []
    for f in sorted(os.listdir(d)):
        if not re.match(r'Special\w*Turn\.txt$', f):
            continue
        body = open(os.path.join(d, f), errors='replace').read()
        m = re.search(r'fn game_\w+\(agent[^{]*\{(.*?)\n\}', body, re.S)
        if m and 'REVERSE_LR' in m.group(1):
            script = f[:-4]
            if not re.search(r"%s's REVERSE_LR" % re.escape(script), text):
                missing.append(script)
    if missing:
        rep.add('ERROR', 'S26 turn-rot', 'Ultimate turn statuses (REVERSE_LR, then the move resumed): no '
                'PostureModule(0x2) where fighters/%s/%s.c resumes the move (a comment "SCRIPT\'s REVERSE_LR" there): %s'
                % (name, name, ', '.join(missing)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('pkgs', nargs='+')
    ap.add_argument('--vanilla')
    ap.add_argument('--ult-param')
    ap.add_argument('--labels')
    ap.add_argument('--motion-list')
    ap.add_argument('--strict', action='store_true')
    a = ap.parse_args()
    import port_sources
    src = port_sources.load()
    rec = record(a.name)
    kind = int(rec['kind'], 0)
    base = dict(rec)
    import fighter_kind_tables  # noqa: F401  (kind numbers by name)
    base['kind'] = port_sources.kind_of(rec['base'])
    base['ult'] = port_sources.ult_name(a.name)
    vanilla = a.vanilla or src.get('vanilla')
    ult_param = a.ult_param or src.find('ult_common', 'param/fighter_param.prc')
    labels = a.labels or src.get('labels')
    motion_list = a.motion_list or src.ult_file(base['ult'], 'motion/body/c00/motion_list.bin')
    inst = Install(a.pkgs)
    print('%s (kind 0x%X on %s): %d files from %d packages\n' % (a.name, kind, rec['base'], len(inst.files), len(a.pkgs)))
    rep = Report()
    joints = check_model(inst, a.name, rep)
    check_texture_ids(inst, a.name, rec['base'], vanilla, src, rep)
    check_scripts(inst, a.name, kind, base, joints, vanilla, rep)
    check_params(inst, a.name, kind, base, vanilla, ult_param, labels, rep)
    check_vl(inst, a.name, base, motion_list, rep)
    check_cancel(inst, a.name, base, motion_list, rep)
    check_msc(inst, a.name, rep)
    check_tether_ledge(a.name, rep)
    check_status_effects(a.name, src, rec, rep)
    check_have_bones(inst, a.name, rep)
    check_repo(a.name, kind, rep)
    check_weapons(a.name, rec, rep)
    check_weapon_statuses(a.name, rep)
    check_weapon_rehit(inst, a.name, rec, rep)
    check_weapon_shield(rec, rep)
    check_weapon_parts(inst, a.name, rec, rep)
    check_weapon_motion(inst, a.name, rec, rep)
    check_weapon_msc(inst, a.name, rec, vanilla, rep)
    check_weapon_facing(a.name, rep)
    check_weapon_joint_facing(a.name, rep)
    check_grab_status(a.name, rep)
    check_weapon_owner(inst, a.name, rec, rep)
    check_weapon_instances(a.name, rec, rep)
    check_weapon_models(inst, a.name, rec, rep)
    check_flare_targets(a.name, rec, rep)
    check_weapon_custom_clamp(inst, a.name, rec, rep)
    check_weapon_kind_compares(inst, a.name, rep)
    check_weapon_custom_source(a.name, rep)
    check_weapon_endless_effects(inst, a.name, rec, vanilla, rep)
    check_body_effect_leaks(inst, a.name, rec, rep)
    check_weapon_step(inst, a.name, rec, rep)
    check_shield_damage(inst, a.name, rep)
    check_motions(inst, a.name, rec, rep)
    check_loop_slots(inst, a.name, rec, base, vanilla, rep)
    check_root_motion(inst, a.name, rec, rep)
    check_assets(inst, a.name, base, rep)
    check_portraits(inst, a.name, rep)
    check_lod_and_camera(inst, a.name, src, base['ult'], rep)
    check_motion_groups(inst, a.name, src, base['ult'], kind, rep)
    check_slot_moves(inst, a.name, src, base['ult'], rep)
    check_throw_joint_hitboxes(inst, a.name, rep)
    check_grab_vs_hit(inst, a.name, rep)
    check_line_tests(inst, a.name, rec, rep)
    check_article_motions(inst, a.name, rec, rep)
    check_tether_window(inst, a.name, rep)
    check_smash_holds(inst, a.name, base, vanilla, rep)
    check_loop_spin(inst, a.name, rep)
    check_sound_tables(inst, a.name, kind, rep)
    check_sound_ids(inst, a.name, rep)
    check_sound_bank_ids(inst, a.name, kind, vanilla, rep)
    check_effects(inst, a.name, rep)
    check_effect_heap(inst, a.name, rep)
    check_cave_hooks(inst, rep)
    check_effect_scripts(src, base['ult'], rep)
    check_vec_targets(src, a.name, base['ult'], rep)
    check_tether_latch(a.name, rep)
    check_pull_gravity(a.name, rep)
    check_loop_speed(a.name, rep)
    check_vec_pull_angle(inst, src, a.name, base['ult'], rep)
    check_add_speed(src, a.name, base['ult'], rep)
    check_foot_effects(inst, a.name, rep)
    check_msc_effect_leaks(inst, a.name, rec, rep)
    check_status_hit_log(inst, a.name, rep)
    check_frame_waits(inst, a.name, rec, rep)
    check_hit_sound(inst, a.name, src, base['ult'], rep)
    check_turn_rot(src, a.name, base['ult'], rep)
    check_weapon_twice(inst, a.name, rep)
    check_result_param(inst, a.name, src, rep)
    check_rapid_slide(inst, a.name, rep)
    check_article_status_reuse(inst, a.name, rep)
    check_result_faces(inst, a.name, base, vanilla, rep)
    n = rep.show()
    sys.exit(1 if n['ERROR'] or (a.strict and n['WARN']) else 0)


if __name__ == '__main__':
    main()
