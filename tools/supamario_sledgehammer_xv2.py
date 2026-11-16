#!/usr/bin/env python3
"""Sledgehammer (Dragon Ball Xenoverse 2 Super skill 164_VGT_HMR, Vegeta's) read from its files, for Supamario's AIR
down special (fighters/supamario/README.md "Sledgehammer"; the animation: tools/supamario_sledgehammer_anim.py, the
build: tools/supamario_sledgehammer_build.py).

  python3 -I tools/supamario_sledgehammer_xv2.py report SKILL_DIR CMN.bdm BTL_CMN.eepk OUT.json
        the skill as data (reference/xv2/sledgehammer_skill.json): the BCM tree with every field (XV2-Tools' names),
        the BAC entries (every item, with the raw TimeScale / ChargeControl / Sound fields), the skill BDM's two
        entries and CMN.bdm #0 decoded, the skill EEPK's effects, BTL_CMN.eepk's effect 0 (the hit effect both BDM
        entries name), the real (60 fps) frame of each BAC frame per entry
  python3 -I tools/supamario_sledgehammer_xv2.py se-extract BANK.acb OUT_DIR CUE...      (as Fake Death's)
  python3 -I tools/supamario_sledgehammer_xv2.py se WAV_IN_DIR WAV_OUT_DIR [PEAK_DBFS]   (as Fake Death's)

Fields read beyond tools/supamario_fakedeath_xv2.py's (from the bytes, XV2-Tools' BAC_Type4 / 6 / 11 layouts):
- TimeScale (type 4): +8 f32 the entry's time scale over the item's frames (1.0 elsewhere).
- ChargeControl (type 6): +0xC u32 the charge time (frames). XV2: holding the skill's button when the BAC reaches the
  item pauses the entry there; held the whole time, the BCM's BacEntryCharge plays on from that frame.
- Sound (type 11): +8 u16 the ACB (0 common SE, 3 character voice, 0xA skill SE), +0xA u16 the sound flags, +0xC
  the cue id.
- BDM (type 0 entries, 10 sub-entries of 0x80; sub-entry 0 the standing victim): +16 Effect1_ID, +18 Effect1_SkillID,
  +20 Effect1_EepkType (0 Common = vfx/cmn/BTL_CMN.eepk), +12 / +14 the hit sound's ACB / cue (0 = CAR_BTL_CMN).
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import supamario_fakedeath_xv2 as F  # noqa: E402

SKILL = '164_VGT_HMR'


def timescales(raw_items):
    """[(from, to, scale)] of an entry's TimeScale items"""
    out = []
    for it, raw in raw_items:
        if it['type'] == 4:
            out.append((it['start'], it['start'] + it['duration'], round(struct.unpack_from('<f', raw, 8)[0], 4)))
    return sorted(out)


def real_frames(ts, last=44):
    """the real frame each BAC frame 0..last is reached at (an entry's own time scales, from its frame 0)"""
    out, t = [], 0.0
    for b in range(last + 1):
        out.append(round(t, 2))
        s = next((x[2] for x in ts if x[0] <= b < x[1]), 1.0)
        t += 1.0 / s
    return out


def report(skill_dir, cmn_bdm, btl_cmn_eepk, out):
    f = lambda ext: os.path.join(skill_dir, SKILL + ext)  # noqa: E731
    bac = F._items_raw(f('.bac'))
    doc = {'source': 'XV2 %s (Sledgehammer, Vegeta) via tools/supamario_sledgehammer_xv2.py; names: XV2-Tools' % SKILL,
           'bcm': F.read_bcm_full(f('_PLAYER.bcm')), 'entries': {}, 'timescale': {}, 'real_frame_of_bac': {}}
    for e in bac['entries']:
        pairs = sorted(zip(e['items'], e['raw']), key=lambda p: (p[0]['start'], p[0]['type']))
        items = []
        for it, raw in pairs:
            d = F.item(it, raw)
            if it['type'] == 4:
                d['scale'] = round(struct.unpack_from('<f', raw, 8)[0], 4)
            elif it['type'] == 6:
                d['charge_time'] = struct.unpack_from('<I', raw, 0xC)[0]
                d['raw'] = raw.hex()
            elif it['type'] == 11:
                d['sound_flags'] = '0x%X' % struct.unpack_from('<H', raw, 0xA)[0]
            items.append(d)
        doc['entries'][str(e['index'])] = items
        ts = timescales(pairs)
        if items:
            doc['timescale'][str(e['index'])] = ts
            doc['real_frame_of_bac'][str(e['index'])] = real_frames(ts)
    doc['bdm_skill'] = {str(i): F.read_bdm_entry(f('_PLAYER.bdm'), i) for i in (0, 1)}
    doc['bdm_cmn_0'] = F.read_bdm_entry(cmn_bdm, 0)
    import xv2vfx as V
    pkg = V.load_package(skill_dir, strict=False)
    keys = ('AssetType', 'AttachementType', 'Orientation', 'Deactivation', 'ESK', 'ScaleMin', 'ScaleMax', 'Position',
            'StartTime', 'Files', 'Flags1_names')
    doc['skill_eepk'] = {str(ef['IndexNum']): [{k: p.get(k) for k in keys} for p in ef['EffectParts']]
                         for ef in pkg['eepk']['Effects']}
    ep = V.read_eepk(open(btl_cmn_eepk, 'rb').read(), strict=False)
    doc['btl_cmn_0'] = [{k: p.get(k) for k in keys} for ef in ep['Effects'] if ef['IndexNum'] == 0
                        for p in ef['EffectParts']]
    import xv2ean as X
    ean = X.Ean(open(f('.ean'), 'rb').read(), smash_axes=True)
    doc['animations'] = [{'index': i, 'name': a.name, 'frames': a.frames} for i, a in enumerate(ean.animations)]
    doc['user_root'] = {'note': 'b_C_Base, metres, smash axes (+Z his facing, +Y up)', '#0': F.root_curve(ean, 0)}
    with open(out, 'w') as fh:
        json.dump(doc, fh, indent=1)
    print('%s: %d BCM entries, %d BAC entries' % (out, len(doc['bcm']), len(doc['entries'])))


def main():
    a = sys.argv[1:]
    if len(a) == 5 and a[0] == 'report':
        report(a[1], a[2], a[3], a[4])
    elif len(a) >= 4 and a[0] == 'se-extract':
        F.se_extract(a[1], a[2], a[3:])
    elif len(a) in (3, 4) and a[0] == 'se':
        import supamario_corebreaker_xv2 as C
        C.level(a[1], a[2], float(a[3]) if len(a) == 4 else -0.5)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
