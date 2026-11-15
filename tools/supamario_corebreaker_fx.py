#!/usr/bin/env python3
"""Supamario's Core Breaker (up special; XV2 Ultimate 2070_FIT_COR): the skill's effects converted for his bank,
with the God Fist's lessons (fighters/supamario/README.md, Super God Fist v4-v9), and where each one goes.

  python3 -I tools/supamario_corebreaker_fx.py SKILL_DIR EFFECT_DIR FRAMES.json OUT_DIR

SKILL_DIR: the skill folder (2070_FIT_COR: .eepk, .pbind.emb, .ptcl.emb / .emm, the EMO / EMB / EMM / EMA, the
.cbind.emb colour fades). EFFECT_DIR: his effect/supamario (the bank to add to: supamario.010d0000.ptcl / .efc and
model/). FRAMES.json: tools/supamario_corebreaker_anim.py --json (the timeline and his joints, for the placements).
Writes OUT_DIR/effect/supamario/{supamario.010d0000.ptcl, .efc, model/EffSupamarioCb*} and OUT_DIR/corebreaker_fx.json:
every BAC effect the move plays, its EEPK parts, the converted set / model and ACMD id, the Smash bone, offset,
turn and size, and the frame of the proposed timeline. OUT_DIR/preview/: the models' renders (xv2_to_nud) and a
sheet of every converted emitter (texture shape x its colour).

Phase 1 (the bank the user has; phase 2 converts onto the current one, after the God Fist's sets). The lessons:
- every converted emitter facing-safe (`facing_safe`: its transform at the effect's origin, unturned, any spread
  a full sphere; God Fist v7);
- XV2 draws them with bloom: colour x GAIN, alpha x ALPHA (capped at 1) (v5-v7);
- XV2 metres -> his units: converted at UNIT (5.04, the body's), sizes x SIZE on top (God Fist's 1.75: XV2's
  effects read against a ~1.75 m character, his ~12 units);
- every effect on bone 0 (TopN: Z forward, Y up in both facings) where the XV2 bone is in the built motion, turned
  about Y only, or on a body bone with no offset and no turn (v6's rule; the aura's limbs).
"""
import json
import math
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)

PREFIX = 'PtcSupamarioCb'
MODEL_PREFIX = 'EffSupamarioCb'
TEX_BASE = 0x15141C00            # after the God Fist's model textures 0x15141B00-01
UNIT = 5.04
GAIN, ALPHA = 2.0, 2.0
SIZE = 1.75
TEX_MAX = 128
BASE = 'supamario.010d0000'

# XV2 bone -> Smash bone (joint the effect sits at, from the built motion)
BONES = {'g_C_Head': 'HeadN', 'g_R_Hand': 'RHandN', 'g_L_Hand': 'LHandN', 'b_C_Pelvis': 'HipN',
         'b_L_Knee': 'LKneeJ', 'b_R_Knee': 'RKneeJ', 'b_R_Foot': 'RFootJ', 'b_L_Elbow': 'LArmJ',
         'b_L_Shoulder': 'LShoulderN', 'b_R_Arm1': 'RShoulderJ', 'b_C_Chest': 'BustN'}
# the BAC's skill effects (EEPK type 6 UltimateSkill, skill 2070): id -> (BAC entry, XV2 frame on, off frames,
# proposed segment and frame in it, how it's placed)
#   'bone0': on bone 0 at the joint's place (follows him, External_Graphic), Y turn only
#   'limb':  on the Smash body bone itself (no offset, no turn)
BAC_FX = {
    0: dict(entry=1, on=45, off=[111], what='the charge (Cor_Crg_Loop, the Cor_Crg / Cor_Wev orbs at the head)',
            segment='charge', place='bone0'),
    1: dict(entry=2, on=110, off=[], what='the charge\'s end flash (Cor_Crg_End_01 / 02)', segment='flare',
            place='bone0'),
    5: dict(entry=2, on=125, off=[], what='blue flame aura on his body (Cor_Aura / Cor_Dot / Cor_Dot2)',
            segment='flare', place='limb'),
    2: dict(entry=3, on=168, off=[196, 234, 290], what='the blazing fist (Cor_Fire / _Global / Cor_Wind, the '
            'Cor_Fire cone)', segment='dive', place='bone0'),
    7: dict(entry=3, on=173, off=[], what='wind streaks on the fist, twice (173, 181)', segment='dive',
            place='bone0'),
    9: dict(entry=5, on=196, off=[], what='the landing blast after a miss (Cor_Nohit; entry 13: the release in '
            'the air)', segment='land_miss', place='bone0'),
    8: dict(entry=10, on=195, off=[290], what='the impact on the victim and its loop (Cor_Hit / Cor_Hit_Loop)',
            segment='grab_hold', place='bone0'),
    12: dict(entry=10, on=228, off=[290], what='the flare before the dive with the victim (Cor_Fire_Global_B, '
             'from its frame 10)', segment='grab_hold', place='bone0'),
    3: dict(entry=12, on=290, off=[], what='the crash explosion (Cor_Bomb_Back / Hit_01 / Hit_02 / Smoke)',
            segment='crash', place='bone0'),
}
# the common ones (EEPK type 0 Common = vfx/cmn/BTL_CMN.eepk; type 1 StageBG = the stage's own ground effects,
# BTL_CMN's ids used as stand-ins, as the God Fist did)
CMN_FX_PLAN = [
    ('type 1 (StageBG) 140', 'entry 0 at 1', 'Btl_GHitSmk: ground smoke at the take-off', 'crouch'),
    ('type 0 (Common) 40', 'entry 0 at 8', 'Fly_Wind.etr: the flight trail (a trace: not converted; Smash dash '
     'smoke / a jump ring stand in)', 'rise'),
    ('type 1 (StageBG) 640', 'entry 5 at 196', 'the landing crater after a miss (not in BTL_CMN: stage effect)',
     'land_miss'),
    ('type 1 (StageBG) 60', 'entry 5 at 216', 'stage effect (BTL_CMN 60 is an ice effect: not it)', 'land_miss'),
    ('type 1 (StageBG) 440', 'entry 12 at 290', 'BTL_CMN 440 = Btl_HitLOD / Btl_HitS (a big hit): the crash',
     'crash'),
    ('type 1 (StageBG) 160', 'entry 12 at 325; entry 20 at 2 / 16', 'Btl_PHitSmk (hit smoke): the crash and the '
     'victim\'s slide (the God Fist has it: PtcSupamarioGfBtl_PHitSmk)', 'crash'),
    ('type 1 (StageBG) 230 / 120', 'entry 20 at 45 / 52', 'Btl_RHit / Btl_MHitSmk on the victim\'s slide (120: the '
     'God Fist\'s PtcSupamarioGfBtl_MHitSmk)', 'victim'),
    ('type 0 (Common) 17', 'entry 19 at 2', 'Dmg_Wind: the wind on the blown-away victim', 'victim'),
]


def facing_safe(p, d):
    """the God Fist's (supamario_godfist_build.facing_safe, v7): its own transform at the origin, unturned, any
    spread or emitter speed a full sphere"""
    p.set_emitter_srt(d, tuple(p.field(d, 'emitter_scale')), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    if p.field(d, 'particle_type') in (1, 3) or p.field(d, 'dispersion_angle') > 0 or \
            p.field(d, 'emitter_velocity') or p.field(d, 'figure_velocity'):
        p.set_field(d, 'dispersion_angle', 180.0)


def seg_frame(frames, segment, xv2_frame=None):
    """the output frame of an XV2 source frame inside a segment (its start when None)"""
    for s in frames['segments']:
        if s['name'] == segment:
            if xv2_frame is None:
                return s['start']
            a, b = s['src']
            t = (xv2_frame - a) / float(b - a)
            return int(round(s['start'] + max(0.0, min(1.0, t)) * (s['end'] - s['start'])))
    raise KeyError(segment)


def _pbind_names(skill_dir):
    import xv2emb
    out = []
    for f in os.listdir(skill_dir):
        if f.endswith('.pbind.emb'):
            out += [n for n, _b in xv2emb.Emb(open(os.path.join(skill_dir, f), 'rb').read())]
    return out


def _emp_of(set_name, names):
    """the EMP a converted set came from: its name, or its name + '_<n>' (a split set past 16 emitters)"""
    bases = [n[:-4] for n in names if n.lower().endswith('.emp')]
    for b in sorted(bases, key=len, reverse=True):
        if set_name == b or (set_name.startswith(b + '_') and set_name[len(b) + 1:].isdigit()):
            return b
    return set_name


def convert(skill_dir, effect_dir, out_dir):
    import efc
    import ptcl
    import xv2_to_ptcl
    dst = os.path.join(out_dir, 'effect', 'supamario')
    os.makedirs(os.path.join(dst, 'model'), exist_ok=True)
    p = ptcl.Ptcl(open(os.path.join(effect_dir, BASE + '.ptcl'), 'rb').read())
    e = efc.Efc(open(os.path.join(effect_dir, BASE + '.efc'), 'rb').read())
    before = len(p.build())
    old = xv2_to_ptcl.TEX_MAX
    xv2_to_ptcl.TEX_MAX = TEX_MAX
    try:
        made, log = xv2_to_ptcl.convert_package(p, skill_dir, PREFIX, unit=UNIT, strict=False)
    finally:
        xv2_to_ptcl.TEX_MAX = old
    sets = {}
    emps = sorted({n for n in os.listdir(skill_dir)} | set(_pbind_names(skill_dir)))
    for si, name, chunk in made:
        emp = _emp_of(name[len(PREFIX):], emps)
        idx = e.add(si + 1)
        sets.setdefault(emp + '.emp', []).append({'set': name, 'efc': idx, 'id': '0x%08X' % (0x03410000 | idx),
                                                  'emitters': [en for _b, en, _n in chunk]})
        for em in p.sets[si]['emitters']:
            d = em['data']
            if d is None:
                continue
            p.set_field(d, 'color_scale', p.field(d, 'color_scale') * GAIN)
            p.set_field(d, 'alpha_init', min(1.0, p.field(d, 'alpha_init') * ALPHA))
            facing_safe(p, d)
    out = p.build()
    assert ptcl.Ptcl(out).validate() == []
    open(os.path.join(dst, BASE + '.ptcl'), 'wb').write(out)
    # the models (the EMO container: Cor_Crg, Cor_Fire, Cor_Wev), as the God Fist's Csg_Bas
    models = {}
    for k, name in enumerate(('Cor_Crg', 'Cor_Fire', 'Cor_Wev')):
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'xv2_to_nud.py'), skill_dir, name,
                            os.path.join(dst, 'model'), '--prefix', MODEL_PREFIX, '--tex-base',
                            hex(TEX_BASE + 0x10 * k), '--plain', '1', '--scale', str(UNIT), '--preview',
                            os.path.join(out_dir, 'preview')], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-2000:]
        folder = MODEL_PREFIX + name.split('_', 1)[1]
        assert os.path.exists(os.path.join(dst, 'model', folder, 'model.nud')), folder
        idx = e.add(0, folder)
        models[name + '.emo'] = {'folder': folder, 'efc': idx, 'id': '0x%08X' % (0x03410000 | idx)}
    open(os.path.join(dst, BASE + '.efc'), 'wb').write(e.build())
    return sets, models, log, before, len(out), p, made


def placements(skill_dir, frames, sets, models):
    """corebreaker_fx.json's 'effects': each BAC effect's parts placed on his skeleton"""
    import xv2vfx
    eepk = xv2vfx.read_eepk(open([os.path.join(skill_dir, f) for f in os.listdir(skill_dir)
                                  if f.endswith('.eepk')][0], 'rb').read())
    js = frames['joints']
    out = []
    for eid, plan in sorted(BAC_FX.items()):
        ef = [x for x in eepk['Effects'] if x['IndexNum'] == eid][0]
        f0 = seg_frame(frames, plan['segment'], plan['on'])
        parts = []
        for prt in ef['EffectParts']:
            files = [f for f in prt['Files'] if f]
            kind = prt['AssetType']
            item = {'xv2': '%s %s' % (kind, ','.join(files)), 'xv2_bone': prt['ESK'], 'xv2_scale': prt['ScaleMin'],
                    'xv2_pos': prt['Position'], 'xv2_start': prt['StartTime'], 'orientation': prt['Orientation']}
            if kind == 'PBIND':
                item['ptcl'] = sets.get(files[0], [])
            elif kind == 'EMO':
                item['model'] = models.get(files[0])
            else:
                item['not_converted'] = {'CBIND': 'ECF colour fade on the character (no Smash 4 equivalent; '
                                                  'Body_Color / a flash could stand in)',
                                         'LIGHT': 'EMA light (no Smash 4 equivalent)'}.get(kind, kind)
                parts.append(item)
                continue
            sm = BONES.get(prt['ESK'])
            size = round(prt['ScaleMin'] * SIZE, 3)
            if plan['place'] == 'limb' and sm:
                item.update(smash_bone=sm, offset=[0, 0, 0], rot=[0, 0, 0], size=size)
            else:
                z, y = js[f0][sm] if sm in js[f0] else (0.0, 0.0)
                rot = [0, 0, 0]
                note = None
                if kind == 'EMO' and prt['ESK'] == 'g_C_Head':
                    rot = [0, 90, 0]
                    note = 'a camera-facing disc (XV2 Orientation Camera): turned Y 90 to face the side camera'
                if prt['ESK'] == 'g_R_Hand' and plan['segment'] in ('dive', 'grab_hold'):
                    note = ('XV2 points it along the fist (UseBoneDirection): along the dive, ~48 degrees down. '
                            'Y-only turns keep it level; an X pitch on bone 0 is not proven facing-safe (check '
                            'both facings in game)')
                item.update(smash_bone='bone 0 (TopN)', at_joint=sm, offset=[0, round(y, 2), round(z, 2)],
                            rot=rot, size=size)
                if note:
                    item['note'] = note
            parts.append(item)
        out.append({'bac_effect': eid, 'what': plan['what'], 'bac_entry': plan['entry'], 'xv2_frame': plan['on'],
                    'xv2_off': plan['off'], 'segment': plan['segment'], 'frame': f0, 'parts': parts})
    return out


def preview_sheet(p, made, out_png):
    """every converted emitter: its texture shape tinted by its colour (both keys), its set and name"""
    from PIL import Image, ImageDraw
    import numpy as np
    rows = []
    for si, name, chunk in made:
        names = [en for _b, en, _n in chunk]
        for k, em in enumerate(p.sets[si]['emitters']):
            d = em['data']
            if d is None:
                continue
            try:
                rgba = p.decode_texture(d, 0)
            except Exception:                           # noqa: BLE001 (a preview only)
                rgba = None
            keys = p.color_keys(d, 0)
            rows.append((name, names[k] if k < len(names) else str(k), rgba, keys))
    cell, cols = 96, 8
    n = len(rows)
    sh = Image.new('RGB', (cols * cell, ((n + cols - 1) // cols) * (cell + 24)), (20, 20, 24))
    dr = ImageDraw.Draw(sh)
    for i, (sname, en, rgba, keys) in enumerate(rows):
        x, y = (i % cols) * cell, (i // cols) * (cell + 24)
        col = (1.0, 1.0, 1.0)
        try:
            k0 = keys[0]
            col = tuple(max(0.0, min(1.0, c)) for c in k0[0:3])
        except Exception:                               # noqa: BLE001
            pass
        if rgba is not None:
            a = np.asarray(rgba, dtype=np.float32)
            if a.ndim == 3:
                lum = a[..., 0] / 255.0
                img = np.stack([lum * col[0], lum * col[1], lum * col[2]], -1) * 255
                im = Image.fromarray(img.clip(0, 255).astype('uint8')).resize((cell - 4, cell - 4))
                sh.paste(im, (x + 2, y + 2))
        dr.text((x + 2, y + cell), sname[len(PREFIX):][:15], fill=(230, 230, 120))
        dr.text((x + 2, y + cell + 11), en[:15], fill=(200, 200, 200))
    sh.save(out_png)


def main():
    a = sys.argv[1:]
    if len(a) != 4:
        sys.exit(__doc__)
    skill_dir, effect_dir, frames_json, out_dir = a
    frames = json.load(open(frames_json))
    os.makedirs(os.path.join(out_dir, 'preview'), exist_ok=True)
    sets, models, log, before, after, p, made = convert(skill_dir, effect_dir, out_dir)
    doc = {'source': '2070_FIT_COR.eepk via tools/supamario_corebreaker_fx.py (phase 1: onto the bank in %s)' %
           os.path.basename(os.path.normpath(effect_dir)),
           'unit': UNIT, 'gain': GAIN, 'alpha': ALPHA, 'size': SIZE, 'ptcl_bytes': [before, after],
           'sets': sets, 'models': models, 'skipped': log,
           'effects': placements(skill_dir, frames, sets, models),
           'common': [dict(zip(('xv2', 'bac', 'what', 'segment'), c)) for c in CMN_FX_PLAN]}
    with open(os.path.join(out_dir, 'corebreaker_fx.json'), 'w') as fh:
        json.dump(doc, fh, indent=1)
    try:
        preview_sheet(p, made, os.path.join(out_dir, 'preview', 'ptcl_emitters.png'))
    except Exception as ex:                             # noqa: BLE001 (the sheet is a convenience)
        print('preview sheet failed:', ex)
    print('ptcl %d -> %d bytes, %d sets, %d models; skipped: %d' % (before, after, sum(len(v) for v in sets.values()),
                                                                     len(models), len(log)))
    for x in doc['effects']:
        print('effect %2d -> frame %3d (%s): %s' % (x['bac_effect'], x['frame'], x['segment'], x['what']))


if __name__ == '__main__':
    main()
