#!/usr/bin/env python3
"""The Smash Run stages (tools/s3ds_stage.py) as stages of their own: one new stage slot each, next to NewStage01
(Minecraft World), nothing replaced. docs/stage-expansion.md has the slot machinery.

  python3 tools/smashrun_slots.py SRC_ROOT BASE_STAGE PARAM_DIR SOUND_DB MSBT UI_DIR LOGO OUT [--rpx IN.rpx]

  SRC_ROOT    a tools/s3ds_unpack.py extract with stage/field_smash/
  BASE_STAGE  the slot's data/stage (melee/NewStage01 and end/NewStage01: Battlefield's copy)
  PARAM_DIR   the installed data/param (ui/ui_stage_db.bin: with NewStage01 at 0x38)
  SOUND_DB    the installed ui_sound_db.bin (with NewStage01's songs)
  MSBT        the installed ui/message/melee.msbt
  UI_DIR      the installed data/ui (replace/stage/*/..._NewStage01.nut, replace/append/stage/stage_13/: the picture
              templates: formats, sizes)
  LOGO        the series logo for the stages (a stagel_10_*.nut: the unmodified Battlefield's, "Super Smash Bros.")
  --rpx       an executable with the earlier caves (the last test's): OUT/code/cross_f.rpx = it +
              stage_slot_cave.py with NewStage01 and every stage below

Each stage (SLOTS: folder name, the area, walled-in or open, its name; cosmetic ids 0x39 on, kinds 0x82 / 0x83 on, page
2 with the DLC stages and Minecraft World):
- stage/melee/NAME: s3ds_stage.build on Battlefield's melee copy; stage/end/NAME (Omega): the same area built on
  Battlefield's Omega copy (so Omega is the Smash Run stage too, not Battlefield's), file names renamed; without
  Battlefield's own model folders (NewStage01's builds keep them hidden; a new stage has no use for them);
- param/ui/ui_stage_db.bin: NewStage01's entry copied (Battlefield's, page 2) with the stage's id / kinds / order;
  ui_sound_db.bin: Battlefield's song list; ui/message/melee.msbt: MmelStageN_NAME (its name), MmelStageG_NAME
  "Smash Run";
- the pictures, rendered from the stage (the front view, no lighting, framed on its camera bounds), in the templates'
  formats and sizes: stage_11 (preview, 1024 x 512), stage_10 (164 x 108) / stage_13 (page-2 grid, 356 x 232) /
  stage_12 (210 x 120 of 256 x 128) / stage_30 (256 x 256) crops of it, stagen_10 the name banner
  (stage_name_banner.py), stagel_10 LOGO; each with its own texture id (stage_13's keep the shared one).
"""
import argparse
import os
import shutil
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import add_stage  # noqa: E402
import msbt  # noqa: E402
import nut  # noqa: E402
import s3ds_stage as st  # noqa: E402

# (folder name, area, open room, name on the stage select)
SLOTS = [('SR_Room00', 'MiniRoom00', False, 'Smash Run Room'),
         ('SR_Room00Open', 'MiniRoom00', True, 'Open Room'),
         ('SR_Room01', 'MiniRoom01', False, 'Crystal Room'),
         ('SR_Room02', 'MiniRoom02', False, 'Crystal Cave'),
         ('SR_Room03', 'MiniRoom03', False, 'Platform Room'),
         ('SR_Room05', 'MiniRoom05', False, 'Long Room'),
         ('SR_Race00', 'Race00', False, 'Run! Course 1'),
         ('SR_Race01', 'Race01', False, 'Run! Course 2'),
         ('SR_Climb', 'Nobore', False, 'Climb!'),
         ('SR_Field', 'MainField', False, 'Smash Run Field')]
FIRST_COSMETIC, FIRST_KIND = 0x39, 0x82          # after NewStage01's 0x38 / 0x80
SERIES = 'Smash Run'
TEMPLATE = 'NewStage01'
# the picture sets: (folder under ui/, set, crop of the 2:1 preview as x fractions of its width, the content box
# inside the texture (w, h) or None for the whole texture)
PICTURES = [('replace/stage', 'stage_11', (0.0, 1.0), None),
            ('replace/stage', 'stage_10', (64 / 512, 450 / 512), None),
            ('replace/stage', 'stage_12', (32 / 512, 478 / 512), (210, 120)),
            ('replace/stage', 'stage_30', (128 / 512, 382 / 512), None),
            ('replace/append/stage', 'stage_13', (60 / 512, 450 / 512), None)]


def slot_list():
    return [(name, FIRST_COSMETIC + i, FIRST_KIND + 2 * i, area, open_room, title)
            for i, (name, area, open_room, title) in enumerate(SLOTS)]


def drop_battlefield(od, base):
    """the build without Battlefield's own model folders (hidden in NewStage01's builds; a new stage needs no copy
    of them: 10 of its 12 MB) and their animations; the stage's light, sound, effects and render files stay"""
    for f in os.listdir(os.path.join(base, 'model')):
        shutil.rmtree(os.path.join(od, 'model', f), ignore_errors=True)
        shutil.rmtree(os.path.join(od, 'animation', f), ignore_errors=True)


def move_stage(src_dir, dst_dir, src, name):
    """add_stage.copy_stage, moving (the builds are 20-30 MB each)"""
    for root, _dirs, files in os.walk(src_dir):
        rel = os.path.relpath(root, src_dir)
        os.makedirs(os.path.join(dst_dir, rel), exist_ok=True)
        for f in files:
            os.replace(os.path.join(root, f), os.path.join(dst_dir, rel, f.replace(src, name)))
    shutil.rmtree(src_dir)


def render_preview(od, w=2048, h=1024):
    """the stage from the front (s3ds_stage.preview's renderer, no overlays), framed on its camera bounds widened
    to 2:1 (a long course: a window over its start), the background dark blue"""
    import glob
    import lvd
    from s3ds_preview import nud_uv, render
    items = []
    for folder in sorted(glob.glob(os.path.join(od, 'model', 'stc_sr_*'))):
        dn, texs = nut.load(os.path.join(folder, 'model.nut'))
        images = {t.tex_id: nut.decode(dn, t) for t in texs}
        import nud
        for m in nud.read(os.path.join(folder, 'model.nud')):
            for p in m.polygons:
                mat = p.materials[0]
                img = images[mat.textures[0]['hash']].astype(np.float64)
                col = p.col.mean(0) / st.WHITE if p.col is not None else np.ones(4)
                img[..., :3] *= np.clip(col[:3], 0, 2)
                tri = np.asarray(p.idx).reshape(-1, 3)
                items.append((p.pos, nud_uv(p.uvs[0], dict(mat.props)), np.r_[tri, tri[:, ::-1]],
                              np.clip(img, 0, 255).astype(np.uint8),
                              (0 if not mat.alpha_func else 518, mat.ref_alpha, mat.src, mat.dst),
                              (mat.textures[0]['wrap_s'], mat.textures[0]['wrap_t'])))
    lv = lvd.LVD(glob.glob(os.path.join(od, 'param', '*.lvd'))[0])
    c = lv.camera[0]
    cw, ch = c.right - c.left, c.top - c.bottom
    if cw > 4 * ch or ch > 1.5 * cw:
        # a course (the race: ~6000 x 400; the climb: ~700 x 10000): a 600 x 300 window over its start
        cx = float(np.mean([p.x for p in lv.spawns]))
        cy = float(np.mean([p.y for p in lv.spawns])) + 60
        span = 600.0
    else:
        cx, cy = (c.left + c.right) / 2, (c.top + c.bottom) / 2
        span = max(cw, 2 * ch) * 1.02
    # render() draws a square view of `span`: render the square, keep its middle half (2:1)
    sq = render(items, w, 0, (cx, cy, span)).astype(np.float64)
    out = sq[w // 4:w // 4 + h]
    dark = (out == 40).all(-1)                  # render()'s background
    out[dark] = (18, 24, 48)
    return np.clip(out, 0, 255).astype(np.uint8)


def picture(preview, crop, size, box):
    """the crop of the preview resized into SIZE (w, h) (or into BOX at the top-left of it, the rest transparent)"""
    from PIL import Image
    h, w = preview.shape[:2]
    x0, x1 = int(round(crop[0] * w)), int(round(crop[1] * w))
    bw, bh = box or size
    src = Image.fromarray(preview[:, x0:x1])
    # keep the aspect: fit the crop's height, centre-cut its width
    scale = max(bw / src.width, bh / src.height)
    src = src.resize((max(bw, int(round(src.width * scale))), max(bh, int(round(src.height * scale)))),
                     Image.LANCZOS)
    left, top = (src.width - bw) // 2, (src.height - bh) // 2
    src = np.asarray(src.crop((left, top, left + bw, top + bh)).convert('RGBA'))
    out = np.zeros((size[1], size[0], 4), np.uint8)
    out[:bh, :bw] = src
    return out


def texture_like(template, img, tex_id=None):
    """a texture with the template's format / size / tiling and IMG's pixels (nut.replace), its id set"""
    d, ts = nut.load(template)
    data = nut.replace(d, ts[0], img)
    return add_stage.with_texture_id(data, tex_id) if tex_id is not None else data


def build(a):
    out = a.out
    slots = slot_list()
    base_melee = os.path.join(a.base, 'melee', TEMPLATE)
    base_end = os.path.join(a.base, 'end', TEMPLATE)
    work = os.path.join(out, '_work')
    db_path = os.path.join(a.param, 'ui', 'ui_stage_db.bin')
    db = open(db_path, 'rb').read()
    sdb = open(a.sound_db, 'rb').read()
    m = msbt.Msbt(open(a.msbt, 'rb').read())
    used = add_stage.used_texture_ids(a.ui)
    bf_cos = 1                                   # Battlefield's cosmetic id (its song list)
    for name, cos, kind, area, open_room, title in slots:
        print('%s: %s%s, cosmetic 0x%X, kinds 0x%X / 0x%X' % (name, area, ' (open)' if open_room else '', cos, kind,
                                                            kind + 1))
        forms = {}
        for form, base in (('melee', base_melee), ('end', base_end)):
            od, summary = st.build(a.src, area, base, work, log=lambda *x: None, open_room=open_room, form=form)
            drop_battlefield(od, base)
            dst = os.path.join(out, 'stage', form, name)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            move_stage(od, dst, TEMPLATE, name)
            forms[form] = dst
        print('  %d models, %d collisions' % (summary['models'], summary['collisions']))
        # the stage-select database, songs, texts (each stage on the one before)
        tmp = os.path.join(work, 'ui_stage_db.bin')
        open(tmp, 'wb').write(db)
        db, _e = add_stage.stage_db(tmp, 0x38, cos, kind, 2)
        open(tmp, 'wb').write(sdb)
        sdb, _se = add_stage.sound_db(tmp, bf_cos, cos)
        m.set('MmelStageN_' + name, title)
        m.set('MmelStageG_' + name, SERIES)
        # pictures
        prev = render_preview(forms['melee'])
        tex_id = add_stage.NEW_TEXTURE_IDS + 0x10 * (cos - 0x38)
        for folder, sset, crop, box in PICTURES:
            tpl = os.path.join(a.ui, folder, sset, '%s_%s.nut' % (sset, TEMPLATE))
            d, ts = nut.load(tpl)
            img = picture(prev, crop, (ts[0].w, ts[0].h), box)
            if sset == 'stage_13':
                tid = None                     # the page-2 tiles share one id (add_stage.py)
            else:
                while tex_id in used:
                    tex_id += 1
                used.add(tex_id)
                tid = tex_id
            od = os.path.join(out, 'ui', folder, sset)
            os.makedirs(od, exist_ok=True)
            open(os.path.join(od, '%s_%s.nut' % (sset, name)), 'wb').write(texture_like(tpl, img, tid))
        for sset, src in (('stagen_10', None), ('stagel_10', a.logo)):
            while tex_id in used:
                tex_id += 1
            used.add(tex_id)
            od = os.path.join(out, 'ui', 'replace', 'stage', sset)
            os.makedirs(od, exist_ok=True)
            dst = os.path.join(od, '%s_%s.nut' % (sset, name))
            if sset == 'stagen_10':
                tpl = os.path.join(a.ui, 'replace', 'stage', sset, '%s_%s.nut' % (sset, TEMPLATE))
                subprocess.run([sys.executable, os.path.join(HERE, 'stage_name_banner.py'), tpl, title, dst],
                               check=True, capture_output=True)
                data = open(dst, 'rb').read()
            else:
                data = open(src, 'rb').read()
            open(dst, 'wb').write(add_stage.with_texture_id(data, tex_id))
        from PIL import Image
        os.makedirs(os.path.join(out, '_previews'), exist_ok=True)
        Image.fromarray(prev).resize((1024, 512)).save(os.path.join(out, '_previews', '%s.png' % name))
    for d in ('param/ui', 'ui/message'):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    open(os.path.join(out, 'param', 'ui', 'ui_stage_db.bin'), 'wb').write(db)
    open(os.path.join(out, 'param', 'ui', 'ui_sound_db.bin'), 'wb').write(sdb)
    open(os.path.join(out, 'ui', 'message', 'melee.msbt'), 'wb').write(m.build())
    if a.rpx:
        names = ['%s:0x%X' % (TEMPLATE, 0x38)] + ['%s:0x%X' % (s[0], s[1]) for s in slots]
        args = subprocess.run([sys.executable, os.path.join(HERE, 'stage_slot_cave.py')] + names,
                              check=True, capture_output=True, text=True).stdout.split()
        os.makedirs(os.path.join(out, 'code'), exist_ok=True)
        subprocess.run([sys.executable, os.path.join(HERE, 'rpx_patch.py'), a.rpx,
                        os.path.join(out, 'code', 'cross_f.rpx')] + args, check=True, capture_output=True)
    shutil.rmtree(work)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    for k in ('src', 'base', 'param', 'sound_db', 'msbt', 'ui', 'logo', 'out'):
        ap.add_argument(k)
    ap.add_argument('--rpx')
    build(ap.parse_args())


if __name__ == '__main__':
    main()
