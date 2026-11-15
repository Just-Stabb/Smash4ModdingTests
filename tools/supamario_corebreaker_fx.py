#!/usr/bin/env python3
"""Supamario's Core Breaker (up special; XV2 Ultimate 2070_FIT_COR): the skill's effects converted for his bank with
the Super God Fist's final settings (tools/xv2_smash_fx.py: scale, vibrance / HDR from each material's glare,
facing-safe emitters and calls, models turned in their own animation), where each one goes, and previews.

  python3 -I tools/supamario_corebreaker_fx.py SKILL_DIR EFFECT_DIR FRAMES.json OUT_DIR
          [--hdr glare|flat] [--vbn MODEL_VBN --motion MOTION_PAC]

SKILL_DIR: the skill folder (2070_FIT_COR). EFFECT_DIR: his effect/supamario (the bank to add to). FRAMES.json:
tools/supamario_corebreaker_anim.py --json (the timeline and his joints). Writes OUT_DIR/effect/supamario/
{supamario.010d0000.ptcl, .efc, model/EffSupamarioCb*}, OUT_DIR/corebreaker_fx.json (every BAC effect the move plays:
its EEPK parts, the converted set / model and ACMD id, bone 0 offset, size, frame; the facing check), and
OUT_DIR/preview/: the models (xv2_to_nud), every emitter's shape x colour, and with --vbn / --motion (the built
motion/body/main.pac) each effect at its final size beside his pose at its frame, facing right and left.

Phase 1: converted onto the bank given (the user's); phase 2 converts onto the current one, after the God Fist's.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import xv2_smash_fx as FX  # noqa: E402

# v3 (user: "I'd like Core Breaker's effects to be larger in scale than Super God Fist's effects"): Core Breaker's own
# scale over XV2's (the EEPK part's scale) at 5.04 units a metre, for every one of its effects. The God Fist's is
# xv2_smash_fx.SIZE / its build's SKILL_SCALE 1.75 (unchanged). In XV2 the orb is 1.3 m in radius round a 1.75 m Fu;
# in Supamario's proportion (12 units tall: 6.9 a metre) that is x1.36; 1.75 is the God Fist's; 2.25 is ~1.65x XV2's
# proportion and ~1.3x the God Fist's
CB_FX_SCALE = 2.25
PREFIX = 'PtcSupamarioCb'
MODEL_PREFIX = 'EffSupamarioCb'
TEX_BASE = 0x15141C00            # after the God Fist's model textures 0x15141B00-01
TEX_MAX = 128
BASE = 'supamario.010d0000'
DIVE_DEG = 48.0                  # the dive's angle below level (XV2 entries 3 / 4: Movement (0, -1.0, -1.1) a frame)

# the effect models (the EEPK's EMO container): the turn baked into each one's animation (its ACMD call unturned)
#   Cor_Crg: XV2 draws it facing the camera (Orientation Camera): a disc in its XY plane; turned Y 90 it faces
#            Smash's side camera (bone 0's X is the screen's depth)
#   Cor_Fire: its front (the bulb, XV2's -Z) along the fist: Y 180 (God Fist v8: XV2's front leads, the trail behind),
#            then pitched DIVE_DEG down, along the dive (XV2: UseBoneDirection on the diving fist)
#   Cor_Wev: a refraction (heat haze) material: left out
MODELS = {'Cor_Crg': FX.euler_q(0.0, 90.0, 0.0),
          'Cor_Fire': FX._qmul(FX.euler_q(DIVE_DEG, 0.0, 0.0), FX.euler_q(0.0, 180.0, 0.0)),
          'Cor_Wev': None}

# v3 (user: "the initial circle looks flat. It should cover around supamario like the auras"): the charge orb's discs
# (XV2 draws them facing the camera) made into closed shells round him (xv2_smash_fx.inflate_discs)
INFLATE = {'Cor_Crg'}

BONES = {'g_C_Head': 'HeadN', 'g_R_Hand': 'RHandN', 'g_L_Hand': 'LHandN', 'b_C_Pelvis': 'HipN',
         'b_L_Knee': 'LKneeJ', 'b_R_Knee': 'RKneeJ', 'b_R_Foot': 'RFootJ', 'b_L_Elbow': 'LArmJ',
         'b_L_Shoulder': 'LShoulderN', 'b_R_Arm1': 'RShoulderJ', 'b_C_Chest': 'BustN'}
# the BAC's skill effects (EEPK type 6 UltimateSkill, skill 2070): id -> BAC entry, XV2 frame on / off, the proposed
# segment, how placed ('bone0': on bone 0 where the XV2 bone is in the built motion, following him; 'limb': on the
# Smash body bone itself, no offset, no turn); at_frame: the segment whose first frame gives the joint's place
BAC_FX = {
    0: dict(entry=1, on=45, off=[111], what='the charge (Cor_Crg_Loop; the Cor_Crg orb at the head)',
            segment='charge', place='bone0'),
    1: dict(entry=2, on=110, off=[], what='the charge\'s end flash (Cor_Crg_End_01 / 02)', segment='flare',
            place='bone0'),
    5: dict(entry=2, on=125, off=[], what='blue flame aura on his body (Cor_Aura / Cor_Dot / Cor_Dot2)',
            segment='flare', place='limb'),
    2: dict(entry=3, on=168, off=[196, 234, 290], what='the blazing fist (Cor_Fire / _Global / Cor_Wind, the '
            'Cor_Fire cone)', segment='dive', place='bone0', at_frame='dive_loop'),
    7: dict(entry=3, on=173, off=[], what='wind streaks on the fist, twice (173, 181)', segment='dive',
            place='bone0', at_frame='dive_loop'),
    9: dict(entry=5, on=196, off=[], what='the landing blast after a miss (Cor_Nohit; entry 13: the release in '
            'the air)', segment='land_miss', place='bone0'),
    8: dict(entry=10, on=195, off=[290], what='the impact on the victim and its loop (Cor_Hit / Cor_Hit_Loop)',
            segment='grab_hold', place='bone0'),
    12: dict(entry=10, on=228, off=[290], what='the flare before the dive with the victim (Cor_Fire_Global_B, '
             'from its frame 10)', segment='grab_hold', place='bone0'),
    3: dict(entry=12, on=290, off=[], what='the crash explosion (Cor_Bomb_Back / Hit_01 / Hit_02 / Smoke)',
            segment='crash', place='bone0'),
}
# the common ones (EEPK type 0 Common = vfx/cmn/BTL_CMN.eepk; type 1 = StageBG: the stage's own ground effects, by
# XV2-Tools' EepkType names; BTL_CMN's same ids stand in, as the God Fist did)
CMN_FX_PLAN = [
    ('type 1 (StageBG) 140', 'entry 0 at 1', 'BTL_CMN 140 Btl_GHitSmk: ground smoke at the take-off', 'crouch'),
    ('type 0 (Common) 40', 'entry 0 at 8', 'Fly_Wind.etr: the flight trail (a trace: not converted; Smash\'s own '
     'jump ring / dash smoke stand in)', 'rise'),
    ('type 1 (StageBG) 640', 'entry 5 at 196', 'the landing crater after a miss (not in BTL_CMN: the stage\'s)',
     'land_miss'),
    ('type 1 (StageBG) 60', 'entry 5 at 216', 'the stage\'s (BTL_CMN 60 is an ice effect: not it)', 'land_miss'),
    ('type 1 (StageBG) 440', 'entry 12 at 290', 'BTL_CMN 440 Btl_HitLOD / Btl_HitS (a big hit): the crash', 'crash'),
    ('type 1 (StageBG) 160', 'entry 12 at 325; entry 20 at 2 / 16', 'Btl_PHitSmk (hit smoke): the crash and the '
     'victim\'s slide (the God Fist has it: PtcSupamarioGfBtl_PHitSmk)', 'crash'),
    ('type 1 (StageBG) 230 / 120', 'entry 20 at 45 / 52', 'Btl_RHit / Btl_MHitSmk on the victim\'s slide (120: the '
     'God Fist\'s PtcSupamarioGfBtl_MHitSmk)', 'victim'),
    ('type 0 (Common) 17', 'entry 19 at 2', 'Dmg_Wind: the wind on the blown-away victim', 'victim'),
]


def seg_frame(frames, segment, xv2_frame=None):
    for s in frames['segments']:
        if s['name'] == segment:
            if xv2_frame is None:
                return s['start']
            a, b = s['src']
            t = (xv2_frame - a) / float(b - a)
            return int(round(s['start'] + max(0.0, min(1.0, t)) * (s['end'] - s['start'])))
    raise KeyError(segment)


def _emp_of(set_name, names):
    """the EMP a converted set came from: its name, or its name + '_<n>' (a split set past 16 emitters)"""
    for b in sorted((n[:-4] for n in names), key=len, reverse=True):
        if set_name == b or (set_name.startswith(b + '_') and set_name[len(b) + 1:].isdigit()):
            return b + '.emp'
    return set_name + '.emp'


def convert(skill_dir, effect_dir, out_dir, hdr='glare', preview_dir=None):
    import efc
    import ptcl
    import xv2_to_ptcl
    import xv2vfx
    dst = os.path.join(out_dir, 'effect', 'supamario')
    os.makedirs(os.path.join(dst, 'model'), exist_ok=True)
    p = ptcl.Ptcl(open(os.path.join(effect_dir, BASE + '.ptcl'), 'rb').read())
    e = efc.Efc(open(os.path.join(effect_dir, BASE + '.efc'), 'rb').read())
    before = len(p.build())
    pkg = xv2vfx.load_package(skill_dir, strict=False)
    mats = FX.material_table(pkg)
    old, old_rep = xv2_to_ptcl.TEX_MAX, xv2_to_ptcl.REPEAT_UV
    xv2_to_ptcl.TEX_MAX = TEX_MAX
    xv2_to_ptcl.REPEAT_UV = True          # v2: the mirrored quarter glows (ptcl01) whole, not a square
    try:
        made, log = xv2_to_ptcl.convert_package(p, skill_dir, PREFIX, unit=FX.UNIT, strict=False)
    finally:
        xv2_to_ptcl.TEX_MAX, xv2_to_ptcl.REPEAT_UV = old, old_rep
    sets, notes = {}, []
    for si, name, chunk in made:
        emp = _emp_of(name[len(PREFIX):], list(pkg['emp']))
        idx = e.add(si + 1)
        names = [en for _b, en, _n in chunk]
        sets.setdefault(emp, []).append({'set': name, 'set_index': si, 'efc': idx, 'id': '0x%08X' % (0x03410000 | idx),
                                         'emitters': names})
        k = 0
        for em in p.sets[si]['emitters']:
            d = em['data']
            if d is None:
                continue
            en = names[k] if k < len(names) else None
            k += 1
            note = FX.hdr_emitter(p, d, mats.get(emp, {}).get(en), hdr)
            FX.facing_safe(p, d)
            notes.append('%s %s: %s' % (name, en, note))
    out = p.build()
    assert ptcl.Ptcl(out).validate() == []
    open(os.path.join(dst, BASE + '.ptcl'), 'wb').write(out)
    models = {}
    for k, (name, q) in enumerate(MODELS.items()):
        emm = pkg['emm'].get(name + '.emm', {})
        tints = FX.model_tints(emm)
        if q is None or tints is None:
            models[name + '.emo'] = {'left_out': 'refraction (heat haze) material: no Smash 4 equivalent'}
            continue
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'xv2_to_nud.py'), skill_dir, name,
                            os.path.join(dst, 'model'), '--prefix', MODEL_PREFIX, '--tex-base',
                            hex(TEX_BASE + 0x10 * k), '--plain', '1', '--scale', str(FX.UNIT),
                            '--tint', ';'.join('%s=%g,%g,%g' % ((m,) + t) for m, t in tints.items())],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-2000:]
        folder = MODEL_PREFIX + name.split('_', 1)[1]
        if name in INFLATE:
            FX.inflate_discs(os.path.join(dst, 'model', folder))
        FX.bake_model_turn(os.path.join(dst, 'model', folder), q)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'xv2_to_nud.py'), 'verify',
                            os.path.join(dst, 'model', folder), '--preview',
                            preview_dir or os.path.join(out_dir, 'preview')],
                           capture_output=True, text=True)
        assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
        idx = e.add(0, folder)
        models[name + '.emo'] = {'folder': folder, 'efc': idx, 'id': '0x%08X' % (0x03410000 | idx), 'tint': tints,
                                 'baked_turn_q': [round(v, 5) for v in q]}
    open(os.path.join(dst, BASE + '.efc'), 'wb').write(e.build())
    bad = FX.facing_emitters(p, [s['set_index'] for v in sets.values() for s in v])
    return {'sets': sets, 'models': models, 'skipped': log, 'emitter_notes': notes, 'ptcl_bytes': [before, len(out)],
            'emitter_facing_problems': bad}, p, made, pkg


def placements(pkg, frames, conv):
    js = frames['joints']
    out, calls = [], []
    for eid, plan in sorted(BAC_FX.items()):
        ef = [x for x in pkg['eepk']['Effects'] if x['IndexNum'] == eid][0]
        f0 = seg_frame(frames, plan['segment'], plan['on'])
        fj = seg_frame(frames, plan['at_frame']) if 'at_frame' in plan else f0
        parts = []
        for prt in ef['EffectParts']:
            files = [f for f in prt['Files'] if f]
            kind = prt['AssetType']
            item = {'xv2': '%s %s' % (kind, ','.join(files)), 'xv2_bone': prt['ESK'], 'xv2_scale': prt['ScaleMin'],
                    'xv2_pos': prt['Position'], 'xv2_start': prt['StartTime'], 'orientation': prt['Orientation']}
            if kind == 'PBIND':
                item['ptcl'] = [{k: v for k, v in s.items() if k != 'emitters'} for s in conv['sets'].get(files[0], [])]
            elif kind == 'EMO':
                item['model'] = conv['models'].get(files[0])
                if 'left_out' in (item['model'] or {}):
                    parts.append(item)
                    continue
            else:
                item['not_converted'] = {'CBIND': 'ECF colour fade on the character (no Smash 4 equivalent; a body '
                                                  'colour flash could stand in)',
                                         'LIGHT': 'EMA light (no Smash 4 equivalent)'}.get(kind, kind)
                parts.append(item)
                continue
            sm = BONES.get(prt['ESK'])
            size = round(prt['ScaleMin'] * CB_FX_SCALE, 3)
            if plan['place'] == 'limb' and sm:
                item.update(bone=sm, offset=[0, 0, 0], rot=[0, 0, 0], size=size)
            else:
                z, y = js[fj][sm] if sm in js[fj] else (0.0, 0.0)
                item.update(bone='bone 0 (TopN)', at_joint=sm, joint_frame=fj, offset=[0, round(y, 2), round(z, 2)],
                            rot=[0, 0, 0], size=size)
            calls.append({'name': '%d %s' % (eid, item['xv2']), 'bone': item['bone'], 'offset': item['offset'],
                          'rot': item['rot']})
            parts.append(item)
        out.append({'bac_effect': eid, 'what': plan['what'], 'bac_entry': plan['entry'], 'xv2_frame': plan['on'],
                    'xv2_off': plan['off'], 'segment': plan['segment'], 'frame': f0, 'joint_frame': fj, 'parts': parts})
    return out, FX.facing_check(calls)


# ---------------------------------------------------------------- previews
def emitter_sheet(p, made, out_png):
    """every converted emitter: its shape x its drawn colour (colour key 0 x colour scale; the label: + additive,
    - subtractive, the brightest channel drawn), 'hidden' for refraction emitters"""
    from PIL import Image, ImageDraw
    import numpy as np
    rows = []
    for si, name, chunk in made:
        names = [en for _b, en, _n in chunk]
        k = 0
        for em in p.sets[si]['emitters']:
            d = em['data']
            if d is None:
                continue
            try:
                rgba = p.decode_texture(d, 0)
            except Exception:                           # noqa: BLE001 (a preview only)
                rgba = None
            col = [c * p.field(d, 'color_scale') for c in p.color_keys(d, 0)[0][:3]]
            rows.append((name, names[k] if k < len(names) else str(k), rgba, col, p.field(d, 'alpha_init'),
                         p.field(d, 'blend_type')))
            k += 1
    cell, cols = 96, 8
    sh = Image.new('RGB', (cols * cell, ((len(rows) + cols - 1) // cols) * (cell + 24)), (20, 20, 24))
    dr = ImageDraw.Draw(sh)
    for i, (sname, en, rgba, col, a0, bl) in enumerate(rows):
        x, y = (i % cols) * cell, (i // cols) * (cell + 24)
        if rgba is not None and a0 > 0:
            lum = np.asarray(rgba, dtype=np.float32)[..., 0] / 255.0
            img = np.stack([lum * min(1.0, c) for c in col], -1) * 255
            sh.paste(Image.fromarray(img.clip(0, 255).astype('uint8')).resize((cell - 4, cell - 4)), (x + 2, y + 2))
        tag = {0: '', 1: '+', 2: '-'}.get(bl, '?') + ('%.1f' % max(col))
        dr.text((x + 2, y + cell), sname[len(PREFIX):][:12] + ' ' + tag, fill=(230, 230, 120))
        dr.text((x + 2, y + cell + 11), (en or '')[:15] if a0 > 0 else (en or '')[:9] + ' hidden', fill=(200, 200, 200))
    sh.save(out_png)


def _shim_world(A):
    """an omo module whose world() puts the model where the call does (A: 4x4 placement)"""
    import types
    import numpy as np
    import omo
    m = types.ModuleType('omo_shim')
    m.__dict__.update(omo.__dict__)
    m.world = lambda o, b, f: {k: (np.array(A) @ np.array(v)).tolist() for k, v in omo.world(o, b, f).items()}
    return m


def _place(face, y, z, size):
    """bone 0's frame facing right (1) or left (-1: turned 180 about Y), the call's offset, the size"""
    import numpy as np
    R = np.diag([face, 1.0, face, 1.0])
    T = np.eye(4)
    T[:3, 3] = (0.0, y, z)
    S = np.diag([size, size, size, 1.0])
    return R @ T @ S


def effect_previews(out_dir, fx, vbn, motion_pac, p, name='effects_on_supamario.png', size_px=300, span=48.0):
    """each BAC effect at its frame and final size beside his pose, facing right and left (the side camera: screen x
    = world Z, his facing; the models through xv2_to_nud's renderer, the particles as each emitter's shape x colour at
    its base size; no motion, no bloom: a size / place / colour check, not a render of the game). An entry's
    'hitboxes' [(label, Z, Y, size, rgb)] (bone 0 offsets, as the ACMD's) are drawn over it as circles; 'title'
    replaces the panel's caption"""
    import numpy as np
    from PIL import Image, ImageDraw
    import omo
    import xv2_to_nud as N
    bones = omo.vbn_read(vbn)
    ents = dict(omo.pac_read(motion_pac))
    o = omo.Omo(ents[[n for n in ents if n.endswith('SpecialHi.omo') and 'Air' not in n][0]])
    cy = 6.0
    bounds = ((-span / 2, cy - span / 2), span)
    tiles = []
    for x in fx:
        row = []
        f = x['joint_frame']
        w = omo.world(o, bones, f)
        tz, ty = w['TransN'][2][3], w['TransN'][1][3]
        for face in (1.0, -1.0):
            img = np.full((size_px, size_px, 3), 0.1)
            for pt in x['parts']:
                for s in pt.get('ptcl', []) or []:
                    for em in p.sets[s['set_index']]['emitters']:
                        dd = em['data']
                        if dd is None or p.field(dd, 'alpha_init') <= 0:
                            continue
                        try:
                            tx = p.decode_texture(dd, 0)
                        except Exception:               # noqa: BLE001
                            continue
                        if tx is None:
                            continue
                        sc = max(p.field(dd, 'scale')) * pt['size']
                        col = np.array([min(1.0, c * p.field(dd, 'color_scale')) for c in p.color_keys(dd, 0)[0][:3]])
                        a = min(1.0, p.field(dd, 'alpha_init')) * 0.35
                        n = max(2, int(sc / span * size_px))
                        lum = np.asarray(Image.fromarray(np.asarray(tx)[..., 0].astype('uint8')).resize((n, n)),
                                         dtype=np.float32) / 255.0
                        if pt['bone'] in w:                   # a body bone (the aura's limbs): where it is
                            zz, yy = (w[pt['bone']][2][3] - tz) * face, w[pt['bone']][1][3] - ty
                        else:
                            zz, yy = pt['offset'][2] * face, pt['offset'][1]
                        cx = int((zz + span / 2) / span * size_px) - n // 2
                        cyp = int(size_px - (yy - (cy - span / 2)) / span * size_px) - n // 2
                        x0, y0 = max(cx, 0), max(cyp, 0)
                        x1, y1 = min(cx + n, size_px), min(cyp + n, size_px)
                        if x1 <= x0 or y1 <= y0:
                            continue
                        patch = lum[y0 - cyp:y1 - cyp, x0 - cx:x1 - cx][..., None] * col[None, None, :] * a
                        sign = -1.0 if p.field(dd, 'blend_type') == FX.BLEND_SUB else 1.0
                        img[y0:y1, x0:x1] = np.clip(img[y0:y1, x0:x1] + sign * patch, 0, 1)
            for pt in x['parts']:
                mdl = pt.get('model')
                if not mdl or 'folder' not in mdl:
                    continue
                d = os.path.join(out_dir, 'effect', 'supamario', 'model', mdl['folder'])
                meshes, tex, mo, mb, anim = N._load_folder(d)
                old = N.omo
                N.omo = _shim_world(_place(face, pt['offset'][1], pt['offset'][2], pt['size']))
                try:
                    lay = N.render(meshes, tex, mo, mb, anim, mo.frames // 2, 'side', size_px, bounds, bg=0.0)
                finally:
                    N.omo = old
                img = np.clip(img + lay, 0, 1)
            im = Image.fromarray((img * 255).astype('uint8'))
            dr = ImageDraw.Draw(im)

            def P(m):
                return ((m[2][3] - tz) * face + span / 2) / span * size_px, \
                    size_px - ((m[1][3] - ty) - (cy - span / 2)) / span * size_px
            for nme, par, _h in bones:
                if par < 0 or par >= len(bones) or nme in ('ThrowN', 'RotN', 'HipN') or \
                        any(k in nme for k in ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky', 'Face', 'HLP', 'Have',
                                                'Finger')):
                    continue
                c = (255, 90, 80) if nme.startswith('R') else (90, 140, 255) if nme.startswith('L') else (235, 235, 235)
                dr.line([P(w[bones[par][0]]), P(w[nme])], fill=c, width=2)
            for lab, hz, hy, hr, hc in x.get('hitboxes', []):
                px = (hz * face + span / 2) / span * size_px
                py = size_px - (hy - (cy - span / 2)) / span * size_px
                rr = hr / span * size_px
                dr.ellipse([px - rr, py - rr, px + rr, py + rr], outline=tuple(hc), width=2)
                dr.line([px - 3, py, px + 3, py], fill=tuple(hc))
                dr.line([px, py - 3, px, py + 3], fill=tuple(hc))
                dr.text((px - rr + 2, py - rr - 12 if py - rr > 16 else py + rr + 2), lab, fill=tuple(hc))
            dr.text((4, 4), x.get('title', 'BAC effect %d' % x['bac_effect']) + ' at frame %d, facing %s' % (
                f, 'right' if face > 0 else 'left'), fill=(255, 255, 140))
            dr.text((4, size_px - 14), 'panel %.0f units; Supamario ~12 tall' % span, fill=(170, 170, 170))
            row.append(im)
        tiles.append(row)
    W = Image.new('RGB', (size_px * 4, size_px * ((len(tiles) + 1) // 2)), (0, 0, 0))
    for i, row in enumerate(tiles):
        for j, im in enumerate(row):
            W.paste(im, (((i % 2) * 2 + j) * size_px, (i // 2) * size_px))
    W.save(os.path.join(out_dir, 'preview', name))


def main():
    a = sys.argv[1:]
    opts = {}
    for k in ('--hdr', '--vbn', '--motion'):
        if k in a:
            i = a.index(k)
            opts[k] = a[i + 1]
            del a[i:i + 2]
    if len(a) != 4:
        sys.exit(__doc__)
    skill_dir, effect_dir, frames_json, out_dir = a
    frames = json.load(open(frames_json))
    os.makedirs(os.path.join(out_dir, 'preview'), exist_ok=True)
    conv, p, made, pkg = convert(skill_dir, effect_dir, out_dir, opts.get('--hdr', 'glare'))
    fx, facing = placements(pkg, frames, conv)
    doc = {'source': '2070_FIT_COR.eepk via tools/supamario_corebreaker_fx.py (phase 1: onto the bank in %s)' %
           os.path.basename(os.path.normpath(effect_dir)),
           'settings': {'unit': FX.UNIT, 'size': CB_FX_SCALE, 'hdr': opts.get('--hdr', 'glare'), 'hdr_gain': FX.HDR_GAIN,
                        'hdr_cap': FX.HDR_CAP, 'alpha': FX.ALPHA, 'model_gain': FX.MODEL_GAIN, 'dive_deg': DIVE_DEG},
           'facing_problems': facing + conv['emitter_facing_problems'], 'effects': fx,
           'common': [dict(zip(('xv2', 'bac', 'what', 'segment'), c)) for c in CMN_FX_PLAN]}
    doc.update({k: v for k, v in conv.items() if k != 'emitter_facing_problems'})
    with open(os.path.join(out_dir, 'corebreaker_fx.json'), 'w') as fh:
        json.dump(doc, fh, indent=1)
    emitter_sheet(p, made, os.path.join(out_dir, 'preview', 'ptcl_emitters.png'))
    if '--vbn' in opts and '--motion' in opts:
        effect_previews(out_dir, fx, opts['--vbn'], opts['--motion'], p)
    print('ptcl %d -> %d bytes, %d sets, %d models; skipped nodes %d; facing problems %d' % (
        conv['ptcl_bytes'][0], conv['ptcl_bytes'][1], sum(len(v) for v in conv['sets'].values()),
        sum(1 for m in conv['models'].values() if 'folder' in m), len(conv['skipped']), len(doc['facing_problems'])))
    for line in doc['facing_problems']:
        print('  FACING', line)
    for x in fx:
        print('effect %2d -> frame %3d (%s): %s' % (x['bac_effect'], x['frame'], x['segment'], x['what']))


if __name__ == '__main__':
    main()
