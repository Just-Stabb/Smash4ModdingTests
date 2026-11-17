#!/usr/bin/env python3
"""Time Skip (Dragon Ball Xenoverse 2 Super skill 1352_HIK_DSH, Hit's "Time-Skip"; the user also calls it "Jump
Spike") read from its files, for Supamario's SIDE special (fighters/supamario/README.md "Time Skip"; the animation:
tools/supamario_timeskip_anim.py, the build: tools/supamario_timeskip_build.py).

  python3 -I tools/supamario_timeskip_xv2.py report SKILL_DIR CMN.ean BTL_CMN.eepk SE.acb OUT.json
        the skill as data (reference/xv2/timeskip_skill.json): the BCM entries, every BAC entry's items (XV2-Tools'
        names, the ThrowHandler / Functions / ScreenEffect / TargetingAssistance fields decoded), the skill BDM's two
        entries, the CMN.ean animations the victim plays, BTL_CMN.eepk's effects 2 and 108, the SE bank's cues, the
        real (60 fps) frame of each BAC frame (entries 0 and 2: the 6x TimeScale), the user's root travel
  python3 -I tools/supamario_timeskip_xv2.py se WAV_IN_DIR WAV_OUT_DIR [PEAK_DBFS]     (levelled, as the others)

The files given: 1352_HIK_DSH.bac / _PLAYER.bcm / _PLAYER.bdm / .ean (+ _F, _HIK, _MAM bodies) and the skill's SE bank
CAR_BTL_S1352_DSH_SE.acb (cues 0 Basa, 1 Dash, 2 Hazure, 3 TimeStop, 4 PumchiFuri, 5 Hit_TmLck; its waveforms in the ACB:
no .awb). No EEPK (the skill's own effects 0 and 11), no BSA.

Fields read beyond tools/supamario_fakedeath_xv2.py's (LazyBone152's XV2-Tools, Xv2CoreLib/BAC/BAC_File.cs and
ValuesDictionary/BAC.cs):
- ThrowHandler (type 17): +8 u16 flags (0x1 FixedDir_BoneEnabled, 0x20 BacJump_AfterDuration, 0x80 BacJump_ReachGround,
  0x100 MoveVictimToUser, 0x200 MoveVictimToUser_RelativeDir), +0xC u16 the user's bone (BoneLinks: 0x18 g_x_LND,
  his ground point), +0xE the victim's bone, +0x10 u16 the victim's next BAC entry, +0x14 / 18 / 1C f32 the
  displacement (m; -Z is in front of the user).
- Functions (type 15): BacFunctionNames (0x2 Damage: param 1 the damage; 0x7 Bone Rotate (Y); 0xB Override
  ThrowHandler Duration; 0x2F / 0x35 unnamed).
- ScreenEffect (type 16): +8 u16 the BPE id (ScreenEffectIds: 2 Weak White Flash, 10 Small Motion Blur / Shake, 78
  Invert World Colors, 85 Flashing White Body Outline 3; the BDM's VictimBpeID 37 Black Screen).
- TargetingAssistance (type 12): +8 u16 the axis (0 X, 1 Y, 2 Z).
- Hitbox flags (type 1 +0xA): 0x2000 ImpactType_Single, 0x8 Unk4.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import supamario_fakedeath_xv2 as F  # noqa: E402

SKILL = '1352_HIK_DSH'
FUNCTIONS = {0x0: 'BAC Loop', 0x2: 'Damage', 0x7: 'Bone Rotate (Y)', 0xB: 'Override ThrowHandler Duration',
             0x22: 'BAC Loop (instant end)'}
BPE = {2: 'Weak White Flash', 10: 'Small Motion Blur/Shake', 37: 'Black Screen', 78: 'Invert World Colors',
       85: 'Flashing White Body Outline 3'}
THROW_FLAGS = {0x1: 'FixedDir_BoneEnabled', 0x2: 'FixedDir_BoneDisabled', 0x4: 'FreeDir_BoneEnabled',
               0x8: 'FreeDir_BoneDisabled', 0x10: 'Unk5', 0x20: 'BacJump_AfterDuration', 0x40: 'Unk7',
               0x80: 'BacJump_ReachGround', 0x100: 'MoveVictimToUser', 0x200: 'MoveVictimToUser_RelativeDir',
               0x400: 'Unk11'}
BONES = {0x0: 'b_C_Base', 0x18: 'g_x_LND'}
HITBOX_FLAGS = {0x8: 'Unk4', 0x2000: 'ImpactType_Single', 0x4000: 'ImpactType_Continuous'}


def real_frames(ts, last):
    """the real (60 fps) frame each BAC frame 0..last is reached at, from the entry's TimeScale items"""
    out, t = [], 0.0
    for b in range(last + 1):
        out.append(round(t, 2))
        s = next((x[2] for x in ts if x[0] <= b < x[1]), 1.0)
        t += 1.0 / s
    return out


def decode(it, raw):
    d = F.item(it, raw)
    t = it['type']
    if t == 1:
        d['hitbox_flags'] = '0x%X %s' % (it['hit_flags'], F._names(it['hit_flags'], HITBOX_FLAGS))
    elif t == 4:
        d['scale'] = round(struct.unpack_from('<f', raw, 8)[0], 4)
    elif t == 6:
        d['charge_time'] = struct.unpack_from('<I', raw, 0xC)[0]
    elif t == 11:
        d['sound_flags'] = '0x%X' % struct.unpack_from('<H', raw, 0xA)[0]
    elif t == 12:
        d['axis'] = 'XYZ'[struct.unpack_from('<h', raw, 8)[0]]
    elif t == 15:
        fn = struct.unpack_from('<H', raw, 8)[0]
        d['function'] = '0x%X %s' % (fn, FUNCTIONS.get(fn, '(unnamed)'))
    elif t == 16:
        b = struct.unpack_from('<H', raw, 8)[0]
        d.update(bpe=b, bpe_name=BPE.get(b, '?'), raw=raw.hex())
    elif t == 17:
        fl, _i, ub, vb, nxt, i18 = struct.unpack_from('<6H', raw, 8)
        disp = struct.unpack_from('<3f', raw, 0x14)
        d.update(flags='0x%X %s' % (fl, F._names(fl, THROW_FLAGS)), user_bone=BONES.get(ub, ub), victim_bone=vb,
                 next_entry=None if nxt == 0xFFFF else nxt, i18=i18, displacement_m=[round(v, 3) for v in disp],
                 character_flags=struct.unpack_from('<H', raw, 6)[0])
    elif t not in (0, 2, 3, 5, 7, 8, 14, 21):
        d['raw'] = raw.hex()
    return d


def report(skill_dir, cmn_ean, btl_cmn_eepk, acb, out):
    f = lambda ext: os.path.join(skill_dir, SKILL + ext)  # noqa: E731
    bac = F._items_raw(f('.bac'))
    doc = {'source': 'XV2 %s (Time-Skip, Hit) via tools/supamario_timeskip_xv2.py; names: XV2-Tools' % SKILL,
           'bcm': F.read_bcm_full(f('_PLAYER.bcm')), 'entries': {}, 'timescale': {}, 'real_frame_of_bac': {}}
    for e in bac['entries']:
        pairs = sorted(zip(e['items'], e['raw']), key=lambda p: (p[0]['start'], p[0]['type']))
        if not pairs:
            continue
        doc['entries'][str(e['index'])] = [decode(it, raw) for it, raw in pairs]
        ts = sorted((it['start'], it['start'] + it['duration'], round(struct.unpack_from('<f', raw, 8)[0], 4))
                    for it, raw in pairs if it['type'] == 4)
        last = max(it['start'] + it['duration'] for it, _r in pairs)
        doc['timescale'][str(e['index'])] = ts
        doc['real_frame_of_bac'][str(e['index'])] = real_frames(ts, last)
    doc['bdm_skill'] = {str(i): F.read_bdm_entry(f('_PLAYER.bdm'), i) for i in (0, 1)}
    import xv2ean as X
    cmn = X.Ean(open(cmn_ean, 'rb').read())
    doc['cmn_ean'] = {str(i): {'name': cmn.animations[i].name, 'frames': cmn.animations[i].frames}
                      for i in (76, 96, 205)}
    import xv2vfx as V
    ep = V.read_eepk(open(btl_cmn_eepk, 'rb').read(), strict=False)
    keys = ('AssetType', 'AttachementType', 'Orientation', 'Deactivation', 'ESK', 'ScaleMin', 'ScaleMax', 'Position',
            'Files', 'Flags1_names')
    doc['btl_cmn'] = {str(ef['IndexNum']): [{k: p.get(k) for k in keys} for p in ef['EffectParts']]
                      for ef in ep['Effects'] if ef['IndexNum'] in (2, 108)}
    ean = X.Ean(open(f('.ean'), 'rb').read(), smash_axes=True)
    doc['animations'] = [{'index': i, 'name': a.name, 'frames': a.frames} for i, a in enumerate(ean.animations)]
    doc['user_root'] = {'note': 'b_C_Base, metres, smash axes (+Z his facing, +Y up); MoveWithAxis X / Y / Z',
                        '#0': F.root_curve(ean, 0), '#1': F.root_curve(ean, 1)}
    import xv2acb as A
    bank = A.Acb(open(acb, 'rb').read())
    doc['se_cues'] = {str(i): bank.name.get(i) for i in range(len(bank.cues))}
    with open(out, 'w') as fh:
        json.dump(doc, fh, indent=1)
    print('%s: %d BCM entries, %d BAC entries with items' % (out, len(doc['bcm']), len(doc['entries'])))


def main():
    a = sys.argv[1:]
    if len(a) == 6 and a[0] == 'report':
        report(*a[1:])
    elif len(a) in (3, 4) and a[0] == 'se':
        import supamario_corebreaker_xv2 as C
        C.level(a[1], a[2], float(a[3]) if len(a) == 4 else -0.5)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
