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


# ------------------------------------------------------------------ MSC and sources
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
    src = os.path.join(ROOT, 'fighters', name)
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


def check_assets(inst, name, base, rep):
    ui = (base.get('ui') or {}).get('name') or base.get('cap') or name.capitalize()
    for s in ('chr_00', 'chr_11', 'chr_12', 'chr_13', 'stock_90'):
        if not inst.glob(r'ui/replace/chr/%s/%s_%s_\d\d\.nut' % (s, s, re.escape(ui))):
            rep.add('INFO', 'U1 portraits', 'no %s portraits for %s in the packages' % (s, ui))
    if not inst.glob(r'fighter/%s/sound/.*' % name):
        rep.add('INFO', 'A1 sounds', 'no fighter/%s/sound in the packages (the base\'s banks play)' % name)
    elif not inst.get('sound/config/soundlabeltable.bin'):
        rep.add('WARN', 'A1 labels', 'sound banks without sound/config/soundlabeltable.bin (Hero fix 71)')


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
    check_msc(inst, a.name, rep)
    check_repo(a.name, kind, rep)
    check_weapons(a.name, rec, rep)
    check_assets(inst, a.name, base, rep)
    check_effects(inst, a.name, rep)
    check_effect_scripts(src, base['ult'], rep)
    n = rep.show()
    sys.exit(1 if n['ERROR'] or (a.strict and n['WARN']) else 0)


if __name__ == '__main__':
    main()
