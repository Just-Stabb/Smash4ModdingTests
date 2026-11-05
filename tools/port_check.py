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

TOPS = ('fighter/', 'param/', 'ui/', 'sound/', 'code/', 'effect/', 'shader/')
JOINTS0 = 26                  # every vanilla fighter's joint table 0


class Install:
    """packages overlaid: {path from the game root: (bytes loader, package)}"""
    def __init__(self, pkgs):
        self.files = {}
        for p in pkgs:
            for rel, load in self._list(p):
                self.files[rel] = (load, os.path.basename(p))

    @staticmethod
    def _norm(path):
        path = path.replace('\\', '/')
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
        order = {'ERROR': 0, 'WARN': 1, 'INFO': 2}
        for sev, code, msg in sorted(self.items, key=lambda x: (order[x[0]], x[1])):
            print('%-5s %-22s %s' % (sev, code, msg))
        n = {s: sum(1 for x in self.items if x[0] == s) for s in order}
        print('\n%d errors, %d warnings, %d notes' % (n['ERROR'], n['WARN'], n['INFO']))
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
            elif nd and tag in ('c00', 'c01'):
                gaps = face_gaps(data, nd)
                if gaps:
                    rep.add('ERROR', 'F1 face-hidden', '%s %s: %d motions show none of its meshes on some frames (a '
                            'hole / black face: the base\'s keys hide meshes that are part of the port\'s face; drive '
                            'the slots from Ultimate\'s visibility tracks): %s' % (tag, pac, len(gaps), ', '.join(
                                '%s (%d of %d frames)' % g for g in gaps[:8])))
    return joints


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
            if c.name in hb and len(c.params) > 4 and c.params[4] > 366:
                bad_angle.add('%08X' % h)
            if c.name == 'Throw_Applier':
                applier = False
            if applier and c.name in hb and h in names:
                syn = c.info.get('syntax', [])
                if 'NoGrabRelease' not in syn or not c.params[syn.index('NoGrabRelease')]:
                    freeing.add(names[h])
    if bad_angle:
        rep.add('ERROR', 'S4 angle', 'angles past 366 (Ultimate\'s 367 / 368: no such angle in Smash 4, the multi-hits let '
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
    idx = list(range(1, 35)) + [263, 264, 268]
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
        want = US.values(US.entry(ult_param, labels, base.get('ult', name)), js)
        diff = ['%d %s %s->%s' % (i, w[1], row.get(i), w[0]) for i, w in sorted(want.items())
                if i in row and abs(row[i] - float(w[0])) > 0.011 * max(1, abs(float(w[0])))]
        if diff:
            rep.add('WARN', 'P2 stats-ultimate', 'differ from Ultimate\'s (tools/ultimate_stats.py): ' + '; '.join(diff[:12]))


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
    for n in sorted(vocabulary() | set(ult_of)):
        if not n.startswith(CANCEL_MOVES) or n.startswith('landing') or n in UA.GAME_ONLY or acmd.crc(n) not in hashes:
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
    scale written over a structure's count). Flags a joint op run from a loop (directly or through a helper) and
    literal table-1 joint IDs (1000+): ModelModule's joint is not ACMD's"""
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
            for m in JOINT_OP.finditer(text):
                j = m.group(1).strip()
                if re.fullmatch(r'(0x[0-9a-fA-F]+|\d+)', j) and int(j, 0) >= 1000:
                    rep.add('ERROR', 'C6 joint-overrides', '%s: ModelModule joint op on joint %s: table-1 IDs (1000+) are '
                            'ACMD\'s, not ModelModule\'s' % (os.path.relpath(path, ROOT), j))


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
    -1 to -13); Smash 4 takes the word unsigned, so 0xFFFFFFFF is a huge one: every hit breaks a shield (Hero, after
    Supamario fix 90). WARN, not ERROR: the user kept it on Hero's other spells (Woosh's set to 0: brave_build.py
    no_negative_shield)"""
    bad = {}
    for rel in sorted(inst.files):
        if not (rel.startswith('fighter/%s/script/animcmd/' % name) and rel.endswith('/game.bin')):
            continue
        for h, cmds in (scripts(inst, rel) or {}).items():
            for c in cmds:
                if 'Hitbox' in c.name and len(c.params) > 18 and c.params[18] >= 1 << 31:
                    bad.setdefault(rel.split('/animcmd/')[1].rsplit('/', 1)[0], set()).add('%08X' % h)
    if bad:
        rep.add('WARN', 'S9 shield-negative', 'negative ShieldDamage (a shield break every hit in Smash 4): ' +
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


def check_assets(inst, name, base, rep):
    ui = (base.get('ui') or {}).get('name') or base.get('cap') or name.capitalize()
    for s in ('chr_00', 'chr_11', 'chr_12', 'chr_13', 'stock_90'):
        if not inst.glob(r'ui/replace/chr/%s/%s_%s_\d\d\.nut' % (s, s, re.escape(ui))):
            rep.add('INFO', 'U1 portraits', 'no %s portraits for %s in the packages' % (s, ui))
    if not inst.glob(r'fighter/%s/sound/.*' % name):
        rep.add('INFO', 'A1 sounds', 'no fighter/%s/sound in the packages (the base\'s banks play)' % name)
    elif not inst.get('sound/config/soundlabeltable.bin'):
        rep.add('WARN', 'A1 labels', 'sound banks without sound/config/soundlabeltable.bin (Hero fix 71)')


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
    """X1: tools/acmd_ext_cave.py's code in the executable but its var_entry hook (0x04B79000, position_vars_cave's
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
        except Exception:                     # noqa: BLE001
            return
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
        # meshes, test 15; convert as type 3, eft2's type 5 being a directional billboard)
        upright = []
        for si in range(len(p.sets)):
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
    check_scripts(inst, a.name, kind, base, joints, vanilla, rep)
    check_params(inst, a.name, kind, base, vanilla, ult_param, labels, rep)
    check_vl(inst, a.name, base, motion_list, rep)
    check_cancel(inst, a.name, base, motion_list, rep)
    check_msc(inst, a.name, rep)
    check_have_bones(inst, a.name, rep)
    check_repo(a.name, kind, rep)
    check_weapons(a.name, rec, rep)
    check_weapon_statuses(a.name, rep)
    check_weapon_rehit(inst, a.name, rec, rep)
    check_weapon_parts(inst, a.name, rec, rep)
    check_weapon_motion(inst, a.name, rec, rep)
    check_flare_targets(a.name, rec, rep)
    check_shield_damage(inst, a.name, rep)
    check_motions(inst, a.name, rec, rep)
    check_loop_slots(inst, a.name, rec, base, vanilla, rep)
    check_assets(inst, a.name, base, rep)
    check_sound_tables(inst, a.name, kind, rep)
    check_effects(inst, a.name, rep)
    check_effect_heap(inst, a.name, rep)
    check_cave_hooks(inst, rep)
    check_effect_scripts(src, base['ult'], rep)
    n = rep.show()
    sys.exit(1 if n['ERROR'] or (a.strict and n['WARN']) else 0)


if __name__ == '__main__':
    main()
