#!/usr/bin/env python3
"""Smash 3DS's Smash Run stages (stage/field_smash/AREA: the field MainField, the rooms MiniRoom00-05, the final
battles Race00 / Race01 / Nobore) -> a Wii U stage folder in the new-stage slot (stage/melee/NewStage01,
docs/stage-expansion.md), one area at a time, built as Minecraft World is (docs/minecraft-world.md): on the
slot's Battlefield copy, only in forms Battlefield's own loaded models have.

  python3 tools/s3ds_stage.py SRC_ROOT AREA|all BASE OUT [--preview]
      SRC_ROOT: a tools/s3ds_unpack.py extract with stage/field_smash/; BASE: the slot's melee/NewStage01
      (Battlefield's copy); OUT gets OUT/AREA/stage/melee/NewStage01 (and OUT/AREA_preview.png)

What a build holds:
- models: every 3DS model folder of the area (model/NAME/normal.bch + normal.mbn; not the broken / cracked
  crystal pieces, the shadow volumes or the shared texture file) -> model/stc_sr_NAME_set (model.nud / .nut,
  Battlefield's island's model.xmb): the objects the model shows by default, unbound (the 3DS rooms' models are
  static; their gimmicks' animations, doors / chests / crystals breaking / moving floors, need Smash Run's stage
  code and stay still). Materials: each one's texture combiner baked into its texture (s3ds_model.tev_combine,
  stage_bake: textures 1 / 2, environment maps and second UV sets, as their average colour), drawn with
  Battlefield's unlit shader 0xA2001001 (texture x vertex colour; opaque, alpha-tested >= the 3DS reference,
  alpha-blended or additive, as the 3DS material); the 3DS fragment
  lighting baked into the vertex colours (an ambient + a sun from the front-top); UVs through the body shader's
  NU_colorSamplerUV (s3ds_model.nud_sampler_uv), UV scrolls a model.mta (NU_colorSamplerUV a frame).
- Battlefield's own model folders: hidden, textures tiny (minecraft_world.hide_folder).
- collision (param/NewStage0100.lvd): every collision of the area's .lvd files (Race: its course pieces
  Test00-04 together), their bone links dropped (the models are static); Battlefield's entries filled: 8
  spawns (the 3DS ones, more spread over the floors near them when it has fewer), 8 respawns (Battlefield's
  pattern over the spawns), the camera bounds and blast zones (the 3DS ones, or the collision's bounds plus
  Battlefield's margins; the blast zones at least that wide), the item spawn paths (the widest floors in the
  camera bounds). A walled-in area (the rooms: a closed loop facing its inside, so nobody can be KO'd) also gets
  an AREA_open build without those walls.
- param/NewStage01_stprm.bin: the 3DS stage's camera values (the same typed-param layout).
- animation/light.bin held at Battlefield's midday (minecraft_world.still_light); sound, effects, render:
  Battlefield's.
"""
import argparse
import glob
import os
import shutil
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lvd  # noqa: E402
import mta  # noqa: E402
import nud  # noqa: E402
import nut  # noqa: E402
import s3ds_effect_models as em  # noqa: E402
import s3ds_model as sm  # noqa: E402
from minecraft_world import hide_folder, still_light, stage_params, two_sided  # noqa: E402
from xv2_to_nud import float_hash  # noqa: E402

AREAS = ['MiniRoom00', 'MiniRoom01', 'MiniRoom02', 'MiniRoom03', 'MiniRoom05', 'Race00', 'Race01', 'Nobore',
         'MainField']
SKIP = ('_break', '_crack')
TEX_BASE = 0x2000F000                       # the slot's own texture IDs (Battlefield's are below), as Minecraft's
XMB_FROM = 'stc_c_Ring_set'                 # Battlefield's island: drawn at every distance
UNLIT = 0xA2001001
WHITE = 127
# the 3DS fragment lighting, baked: an ambient and one sun (from the front-top, Battlefield's midday direction)
SUN = -np.array([-0.204, -0.903, -0.379])
AMBIENT, SUN_GAIN = 0.62, 0.45
CAMERA_KEYS = range(6, 11)                  # stprm: fov, distance near / far, vertical angle, look-down angle
# Battlefield's respawn pattern about its floor (0, 0): rows 70 and 98 above it
RESPAWN = [(0, 70), (36, 70), (-36, 70), (72, 70), (-18, 98), (18, 98), (-54, 98), (54, 98)]
CAMERA_PAD = 30.0
CAMERA_TOP = 130.0                          # Battlefield's camera top over its floor
BLAST_PAD = (80.0, 80.0, 62.0, 58.0)        # Battlefield's blast zones past its camera bounds (l, r, t, b)


# ---------------------------------------------------------------- textures
class Textures:
    """the slot's textures: ids from TEX_BASE + 1, one a distinct image"""
    def __init__(self):
        self.ids, self.images = {}, []

    def id(self, img):
        key = (img.shape, img.tobytes())
        if key not in self.ids:
            self.ids[key] = TEX_BASE + 1 + len(self.images)
            self.images.append((self.ids[key], img))
        return self.ids[key]

    def nut(self, ids):
        """NTWU, one mip, power-of-two 64-2048, BC1 (opaque) or BC3: as Battlefield's loaded textures"""
        from PIL import Image
        out = []
        for tid, img in self.images:
            if tid not in ids:
                continue
            h, w = img.shape[:2]
            w2, h2 = (min(2048, max(64, 1 << (max(v, 1) - 1).bit_length())) for v in (w, h))
            if (w2, h2) != (w, h):
                img = np.asarray(Image.fromarray(img, 'RGBA').resize((w2, h2), Image.BILINEAR))
            out.append((tid, 0x31 if (img[..., 3] >= 250).all() else 0x33, img))
        return nut.write_ntwu(out)


def area_textures(src, area):
    """the textures every model of the area can use: the area's stage_common.bch (crystal / crack textures)"""
    out = {}
    for f in glob.glob(os.path.join(src, 'stage', 'field_smash', area, 'model', 'common', '*.bch')):
        out.update({k: v for k, v in sm.Bch(open(f, 'rb').read()).textures().items() if not k.endswith('#format')})
    return out


# ---------------------------------------------------------------- models
def uses_lighting(mat):
    """the material's combiner reads the fragment lighting (sources 1 / 2)"""
    for r in sm.TEV_STAGES:
        s = mat.get('tev', {}).get(r, 0x0E1F0E1F)
        if s != 0x0E1F0E1F and any(((s >> j) & 0xF) in (1, 2) for j in (0, 4, 8, 16, 20, 24)):
            return True
    return False


def stage_bake(mat, textures):
    """the material's texture combiner over texture 0's texels (s3ds_model.tev_combine), primary / fragment
    lighting colour = the diffuse; textures 1 / 2 (environment maps, a second UV set: other coordinates than
    texture 0's) enter as their average colour"""
    src = textures.get(mat['textures'][0])
    if src is None:
        src = np.full((8, 8, 4), 255, np.uint8)
    if not mat.get('tev'):
        return src
    base = src.astype(np.float64) / 255.0
    units = [base]
    for j in (1, 2):
        t = textures.get(mat['textures'][j])
        units.append(None if t is None else
                     np.broadcast_to(t.reshape(-1, 4).mean(0) / 255.0, base.shape).copy())
    diff = tuple(x / 255.0 for x in mat.get('colors', {}).get('diffuse', (255, 255, 255, 255)))
    out = sm.tev_combine(mat['tev'], units, primary=diff, lit=diff)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


def stage_material(mat, tex_id, name):
    """Battlefield's unlit shader with the 3DS material's blending / alpha test / culling and its UV transform"""
    bl, at = mat.get('blend', {}), mat.get('alpha_test', {})
    src = dst = 0
    if bl.get('on'):
        src, dst = (1, 2) if bl.get('dst') == 1 else (1, 1)
    af = ref = 0
    if at.get('on') and at.get('func') in (6, 7):
        af, ref = 518, max(1, at['ref'])
    m = nud.Material(UNLIT, src, dst, af, ref, 1029)
    wrap = [{0: 3, 1: 3, 2: 1, 3: 2}.get(w & 3, 1) for w in mat['wrap'][0]] if 'wrap' in mat else [1, 1]
    m.textures.append(dict(hash=tex_id, map_mode=0, wrap_s=wrap[0], wrap_t=wrap[1], min_f=3, mag_f=2, mip=6,
                           unk=0, unk2=0))
    co = mat['coords'][0] if 'coords' in mat else dict(scale=(1, 1), translate=(0, 0), transform=0)
    uv = sm.nud_sampler_uv(co['scale'], co['translate'], co.get('transform', 0))
    _bits, val = float_hash(name)
    m.props = [('NU_colorSamplerUV', uv), ('NU_fogParams', [36000.0, 42300.0, 0.0, 0.0]),
               ('NU_fogColor', [0.0, 0.0, 0.0, 0.0]), ('NU_diffuseColor', [1.0, 1.0, 1.0, 1.0]),
               ('NU_materialHash', [val, 0.0, 0.0, 0.0])]
    return m


def model_meshes(mdir, label, tex, shared):
    """one 3DS model folder -> (NUD meshes, MTA material entries, frames, notes)"""
    bch = sm.Bch(open(os.path.join(mdir, 'normal.bch'), 'rb').read())
    models = bch.models()
    if not models:
        return [], [], 0, ['no model']
    model = models[0]
    mbn = sm.read_mbn(open(os.path.join(mdir, 'normal.mbn'), 'rb').read())
    textures = dict(shared)
    textures.update({k: v for k, v in bch.textures().items() if not k.endswith('#format')})
    manims = bch.material_animations()
    tracks = em.anim_tracks(manims[0] if manims else None)
    notes, meshes, mats = [], [], {}
    for obj, mi in zip(model['objects'], sm.match_objects(model['objects'], mbn)):
        if obj['silhouette'] or not (model['visibility'] >> obj['node']) & 1:
            continue
        mat = model['materials'][obj['material']]
        if mat['name'] not in mats:
            img = stage_bake(mat, textures)
            mats[mat['name']] = (stage_material(mat, tex.id(img), '%s/%s' % (label, mat['name'])),
                                 uses_lighting(mat))
        material, lit = mats[mat['name']]
        me = mbn[mi]
        a = me['attrs']
        for _bones, idx in me['parts']:
            if not len(idx):
                continue
            used = np.unique(idx)
            remap = np.full(me['count'], -1, np.int64)
            remap[used] = np.arange(len(used))
            p = nud.Polygon()
            p.pos = a[0][used].astype(np.float64)
            nrm = a[1][used] if 1 in a else np.tile([0.0, 0.0, 1.0], (len(used), 1))
            p.nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-8)
            col = a[2][used].astype(np.float64) if 2 in a else np.ones((len(used), 4))
            if lit:
                col[:, :3] *= (AMBIENT + SUN_GAIN * np.clip(p.nrm @ SUN, 0, None))[:, None]
            p.col = np.clip(np.round(col * WHITE), 0, 255)
            uv = a[3][used] if 3 in a else np.zeros((len(used), 2))
            p.uvs = [np.c_[uv[:, 0], 1.0 - uv[:, 1]]]
            p.idx = remap[idx]
            if mat.get('cull', 2) == 0 and not material.alpha_func:
                p.idx = two_sided(p.idx)
            p.materials = [material.copy()]
            if len(p.pos) >= 0x10000:
                raise ValueError('%s/%s: %d vertices' % (label, obj['name'], len(p.pos)))
            meshes.append(nud.Mesh(obj['name'], [p]))
    # UV scrolls (coordinator 0's scale / translation) as NU_colorSamplerUV a frame; the rest counted
    entries, frames, skipped = [], int(round(manims[0]['frames'])) if manims else 0, 0
    by_name = {m['name']: m for m in model['materials']}
    for mname, tr in tracks.items():
        if mname not in mats or mname not in by_name:
            continue
        skipped += sum(1 for k in tr if k not in ((19, 2), (21, 2)))
        if (19, 2) not in tr and (21, 2) not in tr:
            continue
        co = by_name[mname]['coords'][0]
        vals = []
        for f in range(max(frames, 1)):
            def comp(key, j, default):
                t = tr.get(key)
                v = sm.sample(t[j], f) if t and j < len(t) and t[j] is not None else None
                return default if v is None else v
            sc = [comp((19, 2), j, co['scale'][j]) for j in range(2)]
            tt = [comp((21, 2), j, co['translate'][j]) for j in range(2)]
            vals.append(sm.nud_sampler_uv(sc, tt, co.get('transform', 0)))
        if any(not np.allclose(v, vals[0]) for v in vals):
            entries.append(dict(name='%s_%s' % (label, mname), hash=float_hash('%s/%s' % (label, mname))[0],
                                props=[dict(name='NU_colorSamplerUV', values=vals, u2=1)]))
    if skipped:
        notes.append('%d material colour tracks left out' % skipped)
    return meshes, entries, frames, notes


def area_models(src, area):
    root = os.path.join(src, 'stage', 'field_smash', area, 'model')
    return [n for n in sorted(os.listdir(root)) if os.path.exists(os.path.join(root, n, 'normal.bch'))
            and os.path.exists(os.path.join(root, n, 'normal.mbn')) and not any(s in n for s in SKIP)]


# ---------------------------------------------------------------- collision
def floors(cols):
    """[(x0, y0, x1, y1)] the floor lines (normal up) of the solid collisions"""
    out = []
    for c in cols:
        for i, n in enumerate(c.normals):
            if n[1] > 0.7 and i + 1 < len(c.verts):
                (x0, y0), (x1, y1) = c.verts[i][:2], c.verts[i + 1][:2]
                out.append((min(x0, x1), y0 if x0 <= x1 else y1, max(x0, x1), y1 if x0 <= x1 else y0))
    return out


def floor_at(fl, x, y):
    """the floor under / nearest (x, y) at x: its height, or None"""
    best = None
    for x0, y0, x1, y1 in fl:
        if x0 - 1e-3 <= x <= x1 + 1e-3 and x1 > x0:
            fy = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
            if best is None or abs(fy - y) < abs(best - y):
                best = fy
    return best


def spawn_points(spawns, fl):
    """8 spawns: the 3DS ones, then more on the floors near their middle (20 apart, alternating sides)"""
    pts = [(s.x, s.y) for s in spawns][:8]
    if not pts:
        x0, y0, x1, y1 = max(fl, key=lambda f: f[2] - f[0])
        pts = [((x0 + x1) / 2, (y0 + y1) / 2 + 0.1)]
    cx, cy = np.mean([p[0] for p in pts]), np.mean([p[1] for p in pts])
    k = 1
    while len(pts) < 8 and k < 60:
        for x in (cx - 20 * k, cx + 20 * k):
            fy = floor_at(fl, x, cy)
            if fy is not None and abs(fy - cy) < 60 and len(pts) < 8 and \
                    all(abs(x - px) > 10 or abs(fy - py) > 10 for px, py in pts):
                pts.append((x, fy + 0.1))
        k += 1
    while len(pts) < 8:
        pts.append(pts[len(pts) % max(1, len(pts))])
    return pts


def enclosing(c):
    """a closed loop whose lines all face its inside: the walls / ceiling Smash Run puts around a room (the
    solid is outside it, so nobody leaves the room)"""
    if len(c.verts) < 4 or np.hypot(*np.subtract(c.verts[0][:2], c.verts[-1][:2])) > 1e-3:
        return False
    mid = np.mean([v[:2] for v in c.verts[:-1]], 0)
    for i, n in enumerate(c.normals[:len(c.verts) - 1]):
        m = (np.asarray(c.verts[i][:2]) + np.asarray(c.verts[i + 1][:2])) / 2
        if np.dot(n, mid - m) <= 0:
            return False
    return True


def area_lvd(src, area, base_lvd, open_room=False):
    """Battlefield's lvd with the area's collisions and points; open_room: without the enclosing loops"""
    paths = sorted(glob.glob(os.path.join(src, 'stage', 'field_smash', area, 'param', '*.lvd')))
    files = [lvd.LVD(p) for p in paths]
    main = max(files, key=lambda f: (len(f.spawns), len(f.collisions)))
    cols, names = [], set()
    dropped = 0
    for f in files:
        for c in f.collisions:
            if open_room and enclosing(c):
                dropped += 1
                continue
            c.bone = ''
            n = c.name
            k = 1
            while c.name in names:
                c.name = '%s_%d' % (n, k)
                k += 1
            names.add(c.name)
            cols.append(c)
    lv = lvd.LVD(base_lvd)
    lv.collisions = cols
    solid = [c for c in cols if not c.flags[3]]
    fl = floors(solid) + floors([c for c in cols if c.flags[3]])
    pts = spawn_points(main.spawns, fl)
    for e, (x, y) in zip(lv.spawns, pts):
        e.x, e.y = float(x), float(y)
    cx = float(np.mean([p[0] for p in pts]))
    base_y = float(min(p[1] for p in pts))
    for e, (dx, dy) in zip(lv.respawns, RESPAWN):
        e.x, e.y = cx + dx, base_y + dy
    xs = [v[0] for c in cols for v in c.verts]
    ys = [v[1] for c in cols for v in c.verts]
    if main.camera:
        b = main.camera[0]
        cam = (b.left, b.right, b.top, b.bottom)
    else:
        # the collision's bounds, with at least Battlefield's headroom over the spawns' floor (its camera top
        # is 130 over its floor, the respawns 70 / 98)
        cam = (min(xs) - CAMERA_PAD, max(xs) + CAMERA_PAD, max(max(ys) + CAMERA_PAD, base_y + CAMERA_TOP),
               min(ys) - CAMERA_PAD)
    lv.camera[0].left, lv.camera[0].right, lv.camera[0].top, lv.camera[0].bottom = map(float, cam)
    # the blast zones: at least the camera bounds plus Battlefield's margins (the 3DS's, tuned for the race /
    # climb modes, can sit inside the camera bounds), the 3DS's where wider
    blast = [cam[0] - BLAST_PAD[0], cam[1] + BLAST_PAD[1], cam[2] + BLAST_PAD[2], cam[3] - BLAST_PAD[3]]
    if main.blast:
        b = main.blast[0]
        blast = [min(blast[0], b.left), max(blast[1], b.right), max(blast[2], b.top), min(blast[3], b.bottom)]
    lv.blast[0].left, lv.blast[0].right, lv.blast[0].top, lv.blast[0].bottom = map(float, blast)
    # item spawn paths: the widest floors inside the camera bounds, a little above them
    inside = [f for f in fl if cam[0] <= f[0] and f[2] <= cam[1] and cam[3] <= min(f[1], f[3]) <= cam[2]]
    template = lv.items[0].sections[0]
    lv.items[0].sections = []
    for x0, y0, x1, y1 in sorted(inside, key=lambda f: f[0] - f[2])[:4]:
        sec = lvd.Shape()
        sec.type, sec.v, sec.points = template.type, list(template.v), [[x0, y0 + 19.0], [x1, y1 + 19.0]]
        lv.items[0].sections.append(sec)
    for p in lv.points:
        p.x, p.y = cx, base_y + p.y
    return lv, dict(collisions=len(cols), enclosures_dropped=dropped, spawns_3ds=len(main.spawns),
                    camera=[round(x, 1) for x in cam], blast=[round(x, 1) for x in blast])


# ---------------------------------------------------------------- the build
def build(src, area, base, out, log=print, open_room=False):
    od = os.path.join(out, area + ('_open' if open_room else ''), 'stage', 'melee', 'NewStage01')
    if os.path.exists(od):
        shutil.rmtree(od)
    shutil.copytree(base, od)
    md = os.path.join(od, 'model')
    for f in sorted(os.listdir(md)):
        hide_folder(md, f)
    xmb_src = os.path.join(base, 'model', XMB_FROM, 'model.xmb')
    tex = Textures()
    shared = area_textures(src, area)
    summary = dict(models=0, meshes=0, mtas=0)
    for name in area_models(src, area):
        mdir = os.path.join(src, 'stage', 'field_smash', area, 'model', name)
        meshes, entries, frames, notes = model_meshes(mdir, '%s/%s' % (area, name), tex, shared)
        if not meshes:
            log('  %s: nothing drawn (%s)' % (name, '; '.join(notes)))
            continue
        folder = os.path.join(md, 'stc_sr_%s_set' % name)
        os.makedirs(folder, exist_ok=True)
        open(os.path.join(folder, 'model.nud'), 'wb').write(nud.write(meshes))
        ids = {t['hash'] for m in meshes for p in m.polygons for mt in p.materials for t in mt.textures}
        open(os.path.join(folder, 'model.nut'), 'wb').write(tex.nut(ids))
        shutil.copy(xmb_src, os.path.join(folder, 'model.xmb'))
        if entries:
            open(os.path.join(folder, 'model.mta'), 'wb').write(mta.write(max(frames, 1), entries))
            summary['mtas'] += 1
        summary['models'] += 1
        summary['meshes'] += len(meshes)
        log('  %-28s %3d meshes%s%s' % (name, len(meshes), ', UV scroll' if entries else '',
                                         ('  (' + '; '.join(notes) + ')') if notes else ''))
    lv_path = glob.glob(os.path.join(od, 'param', '*.lvd'))[0]
    lv, info = area_lvd(src, area, lv_path, open_room)
    open(lv_path, 'wb').write(lv.write())
    summary.update(info)
    light = os.path.join(od, 'animation', 'light.bin')
    data = still_light(light)
    open(light, 'wb').write(data)
    prm = glob.glob(os.path.join(od, 'param', '*_stprm.bin'))[0]
    s3 = glob.glob(os.path.join(src, 'stage', 'field_smash', area, 'param', '*_stprm.bin'))
    if s3:
        cam = read_params(s3[0])
        data = stage_params(prm, {k: cam[k] for k in CAMERA_KEYS})
        open(prm, 'wb').write(data)
        summary['camera_params'] = [round(cam[k], 2) for k in CAMERA_KEYS]
    summary['textures'] = len(tex.images)
    return od, summary


def read_params(path):
    """a typed param file's values by index (floats and ints)"""
    d = open(path, 'rb').read()
    sizes = {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4, 7: 4, 0x20: 4}
    o, out = 8, []
    while o < len(d):
        t = d[o]
        n = 4 + struct.unpack('>I', d[o + 1:o + 5])[0] if t == 8 else sizes[t]
        raw = d[o + 1:o + 1 + n]
        out.append(struct.unpack('>f', raw)[0] if t == 7 else struct.unpack('>i', raw)[0] if t in (5, 6) else raw)
        o += 1 + n
    return out


# ---------------------------------------------------------------- preview
def preview(od, path, size=900):
    """the built folder from the front (orthographic, no lighting: texture x vertex colour), with the collision
    lines (floors green, walls / ceilings red, pass-through cyan), the spawns (yellow), respawns (white), the
    camera bounds (blue) and blast zones (magenta)"""
    from PIL import Image, ImageDraw
    from s3ds_preview import nud_uv, render
    items = []
    for folder in sorted(glob.glob(os.path.join(od, 'model', 'stc_sr_*'))):
        dn, texs = nut.load(os.path.join(folder, 'model.nut'))
        images = {t.tex_id: nut.decode(dn, t) for t in texs}
        for m in nud.read(os.path.join(folder, 'model.nud')):
            for p in m.polygons:
                mat = p.materials[0]
                img = images[mat.textures[0]['hash']].astype(np.float64)
                col = p.col.mean(0) / WHITE if p.col is not None else np.ones(4)
                img[..., :3] *= np.clip(col[:3], 0, 2)
                tri = np.asarray(p.idx).reshape(-1, 3)
                items.append((p.pos, nud_uv(p.uvs[0], dict(mat.props)), np.r_[tri, tri[:, ::-1]],
                              np.clip(img, 0, 255).astype(np.uint8),
                              (0 if not mat.alpha_func else 518, mat.ref_alpha, mat.src, mat.dst),
                              (mat.textures[0]['wrap_s'], mat.textures[0]['wrap_t'])))
    lv = lvd.LVD(glob.glob(os.path.join(od, 'param', '*.lvd'))[0])
    b = lv.blast[0]
    # the view: the blast zones
    span = max(b.right - b.left, b.top - b.bottom) * 1.1
    cx, cy = (b.left + b.right) / 2, (b.top + b.bottom) / 2
    img = render(items, size, 0, (cx, cy, span))
    im = Image.fromarray(img)
    dr = ImageDraw.Draw(im)

    def sc(x, y):
        return ((x - cx) / span + 0.5) * size, (0.5 - (y - cy) / span) * size
    for c in lv.collisions:
        for i in range(len(c.verts) - 1):
            n = c.normals[i] if i < len(c.normals) else (0, 1)
            colr = (0, 255, 255) if c.flags[3] else (0, 255, 0) if n[1] > 0.7 else (255, 60, 60)
            dr.line([sc(*c.verts[i][:2]), sc(*c.verts[i + 1][:2])], fill=colr, width=2)
    for pts, colr in ((lv.spawns, (255, 255, 0)), (lv.respawns, (255, 255, 255))):
        for s in pts:
            x, y = sc(s.x, s.y)
            dr.ellipse([x - 4, y - 4, x + 4, y + 4], outline=colr, width=2)
    for bb, colr in ((lv.camera[0], (80, 120, 255)), (lv.blast[0], (255, 0, 255))):
        x0, y0 = sc(bb.left, bb.top)
        x1, y1 = sc(bb.right, bb.bottom)
        dr.rectangle([x0, y0, x1, y1], outline=colr, width=2)
    im.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('src')
    ap.add_argument('area')
    ap.add_argument('base')
    ap.add_argument('out')
    ap.add_argument('--preview', action='store_true')
    a = ap.parse_args()
    for area in (AREAS if a.area == 'all' else [a.area]):
        print(area)
        od, summary = build(a.src, area, a.base, a.out)
        print('  ' + ', '.join('%s %s' % kv for kv in summary.items()))
        if a.preview:
            preview(od, os.path.join(a.out, '%s_preview.png' % area))
        # an area walled in (Smash Run's rooms): also a build without the walls, so fighters can be KO'd
        paths = glob.glob(os.path.join(a.src, 'stage', 'field_smash', area, 'param', '*.lvd'))
        if any(enclosing(c) for p in paths for c in lvd.LVD(p).collisions):
            od, summary = build(a.src, area, a.base, a.out, open_room=True, log=lambda *x: None)
            print('  open: ' + ', '.join('%s %s' % kv for kv in summary.items() if kv[0] in
                                         ('collisions', 'enclosures_dropped', 'camera', 'blast')))
            if a.preview:
                preview(od, os.path.join(a.out, '%s_open_preview.png' % area))


if __name__ == '__main__':
    main()
