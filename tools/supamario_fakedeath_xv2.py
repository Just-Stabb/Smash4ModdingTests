#!/usr/bin/env python3
"""Fake Death (Dragon Ball Xenoverse 2 Super skill 116_YMC_DIE, Yamcha's) read from its files, for Supamario's GROUNDED
down special (fighters/supamario/README.md "Fake Death"; the animation: tools/supamario_fakedeath_anim.py, the effects:
tools/supamario_fakedeath_fx.py).

  python3 -I tools/supamario_fakedeath_xv2.py report SKILL_DIR CMN.bdm BTL_CMN.eepk OUT.json
        the skill as data (reference/xv2/fakedeath_skill.json): the BCM tree with every field (XV2-Tools' names),
        the BAC entries (items with the right Effect bone / Hitbox BDM-file fields, below), CMN.bdm #20 decoded with
        XV2-Tools' BDM names, BTL_CMN.eepk's effect 26, the root travel of both animations
  python3 -I tools/supamario_fakedeath_xv2.py se-extract BANK.acb OUT_DIR CUE...
        the cues' HCA (tools/xv2acb.py's reader; this bank is the older ACB layout whose waveform table names the
        in-memory AWB entry `Id`, not `MemoryAwbId`: handled here, xv2acb.py itself unchanged)
  python3 -I tools/supamario_fakedeath_xv2.py se WAV_IN_DIR WAV_OUT_DIR [PEAK_DBFS]
        levelled (tools/supamario_corebreaker_xv2.py's `level`: mono 16-bit, one peak, -0.5 dBFS as the others)

Field corrections over tools/xv2bac.py (from LazyBone152's XV2-Tools, Xv2CoreLib/BAC/BAC_File.cs; xv2bac.py is shared
and is not changed in phase 1, the fix is listed for phase 2):
- Effect (type 8): +0xA u16 is the BoneLink (xv2bac's `i_a`), +0xC u16 SkillID, +0xE UseSkillId, +0x10 **i32**
  EffectID (xv2bac's `bone` at +0x12 is the EffectID's high half, always 0), +0x2C u32 EffectFlags (1 Off, 4
  SpawnOnTarget, 8 Loop, 0x10 UserOnly).
- Hitbox (type 1): +0x10 u16 is StaminaTakenWhenBlocked (not a BDM), +0x12 low nibble BoundingBoxType, +0x13 low nibble
  the BDM file (0 Common = CMN.bdm, 1 Character, 2 Skill), +0x16 u16 BoneLink.
- EEPK types (Effect +8): 0 Common (vfx/cmn/BTL_CMN.eepk), 1 Stage BG (the stage's own), 2 Character, 3 Any skill,
  5 Super, 6 Ultimate, 7 Evasive.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import xv2bac as B  # noqa: E402
import xv2ean as X  # noqa: E402

BONE_LINKS = {0: 'b_C_Base', 1: 'b_C_Chest', 2: 'b_C_Head', 3: 'b_C_Neck1', 4: 'b_C_Pelvis', 5: 'b_C_Spine1',
              6: 'b_C_Spine2', 7: 'b_R_Hand', 8: 'b_L_Hand', 9: 'b_R_Elbow', 10: 'b_L_Elbow'}
EEPK_TYPES = {0: 'Common (BTL_CMN.eepk)', 1: 'Stage BG (the stage\'s own)', 2: 'Character', 3: 'Any skill',
              5: 'Super skill', 6: 'Ultimate skill', 7: 'Evasive skill'}
BDM_FILES = {0: 'Common (CMN.bdm)', 1: 'Character', 2: 'Skill'}
FUNCTIONS = {0x17: 'Recover Health (instant) [XV2-Tools name; params all 0 here]',
             0x22: 'BAC Loop (instant end)'}
INVULN = {0: 'All Attacks Miss'}
ANIM_FLAGS = {0x1: 'MoveWithAxis_X', 0x2: 'MoveWithAxis_Y', 0x4: 'MoveWithAxis_Z', 0x10: 'UseRootMotion',
              0x40: 'ForceYRootMotion', 0x200: 'ContinueFromLast'}
TRACK_FLAGS = {0x400: 'TrackForwardAndBackwards'}
CALLBACK = {0x1: 'Attacks', 0x2: 'Movement', 0x4: 'DisableKiBlastLink', 0x10: 'Counters', 0x80: 'BackHits',
            0x100: 'Combos', 0x200: 'Supers', 0x400: 'UltimatesAndEvasives', 0x800: 'ZVanish', 0x1000: 'KiBlasts',
            0x2000: 'Jump', 0x4000: 'Guard', 0x8000: 'FlyingAndStepDash'}
ACTIVATOR = {0x1: 'Standing', 0x2: 'Floating', 0x4: 'TouchingGround', 0x8: 'OnAttackHit', 0x10: 'AttackBlocked',
             0x20: 'CloseToTarget', 0x40: 'FarFromTarget', 0x400: 'Unk11', 0x800: 'Idle', 0x1000: 'CounterMelee',
             0x2000: 'CounterProjectile'}
STATE = {0x1: 'Idle', 0x2: 'Attacking', 0x4: 'Boosting', 0x8: 'Guarding'}
BUTTON = {0x100: 'SuperSkill1', 0x200: 'SuperSkill2', 0x400: 'SuperSkill3', 0x800: 'SuperSkill4',
          0x10000: 'SkillInput', 0x20000: 'SuperMenuPlusSkillInput'}
RECEIVER = {0x1: 'Combos', 0x2: 'Supers', 0x4: 'Ultimate / Awoken / Evasive'}


def _names(v, table):
    out = [n for b, n in sorted(table.items()) if v & b]
    rest = v & ~sum(b for b in table if v & b)
    return out + (['0x%X' % rest] if rest else [])


def read_bcm_full(path):
    """every field, XV2-Tools' Xv2CoreLib/BCM/Parser.cs offsets (0x70 bytes an entry)"""
    d = open(path, 'rb').read()
    assert d[:4] == b'#BCM', path
    n, off = struct.unpack_from('<II', d, 8)
    idx = lambda a: (a - off) // 0x70 if a else None  # noqa: E731
    out = []
    for i in range(n):
        o = off + 0x70 * i
        u32 = lambda k: struct.unpack_from('<I', d, o + k)[0]  # noqa: E731
        i16 = lambda k: struct.unpack_from('<h', d, o + k)[0]  # noqa: E731
        u16 = lambda k: struct.unpack_from('<H', d, o + k)[0]  # noqa: E731
        out.append({
            'index': i, 'sibling': idx(u32(48)), 'child': idx(u32(52)), 'parent': idx(u32(56)), 'root': idx(u32(60)),
            'DirectionalInput': u32(4), 'ButtonInput': '0x%X %s' % (u32(8), _names(u32(8), BUTTON)),
            'HoldDownConditions': '0x%X' % u32(12), 'OpponentSizeConditions': '0x%X' % u32(16),
            'MinimumLoopDuration': u16(20), 'MaximumLoopDuration': u16(22),
            'PrimaryActivatorConditions': '0x%X %s' % (u32(24), _names(u32(24), ACTIVATOR)),
            'ActivatorState': '0x%X %s' % (u32(28), _names(u32(28), STATE)),
            'BacEntryPrimary': i16(32), 'BacEntryCharge': i16(34), 'BacEntryUserConnect': i16(38),
            'BacEntryVictimConnect': i16(40), 'BacEntryAirborne': i16(42), 'RandomFlag': u16(46),
            'KiCost': u32(64), 'ReceiverLinkID': '0x%X %s' % (u32(76), _names(u32(76), RECEIVER)),
            'StaminaCost': u32(84), 'KiRequired': u32(92), 'HealthRequired': struct.unpack_from('<f', d, o + 96)[0]})
    return out


def item(it, raw):
    """one BAC item, readable, with XV2-Tools' fields where xv2bac.py's differ (raw: the item's bytes)"""
    t, s, du = it['type'], it['start'], it['duration']
    base = {'type': B.TYPES.get(t, t), 'frames': [s, s + du]}
    if t == 0:
        base.update(ean={0: 'CMN', 0xFFFE: 'skill'}.get(it['ean_type'], it['ean_type']), index=it['ean_index'],
                    src=[it['start_frame'], it['end_frame']], speed=it['speed'],
                    flags=_names(it['anim_flags'], ANIM_FLAGS))
    elif t == 1:
        base.update(bdm=it['bdm_entry'], bdm_file=BDM_FILES.get(raw[0x13] & 0xF, raw[0x13] & 0xF),
                    hitbox_flags='0x%X' % it['hit_flags'], damage=it['damage'], damage_when_blocked=it['damage_guarded'],
                    stamina_taken_when_blocked=it['stamina_bdm'],
                    bone=BONE_LINKS.get(struct.unpack_from('<H', raw, 0x16)[0]), position_m=it['position'],
                    size_m=it['size'])
    elif t == 2:
        base.update(flags='0x%X' % it['move_flags'], per_frame_m=it['direction'], drag=it['drag'],
                    note='-Z is forward (XV2 faces -Z; Core Breaker\'s dive (0, -1, -1.1) is forward)')
    elif t == 3:
        base.update(invulnerability=INVULN.get(it['invuln_type'], it['invuln_type']))
    elif t == 5:
        base.update(strength=it['strength'], flags=_names(it['track_flags'], TRACK_FLAGS))
    elif t == 7:
        base.update(link=_names(it['bcm_flags'], CALLBACK))
    elif t == 8:
        eid, = struct.unpack_from('<i', raw, 0x10)
        bone, = struct.unpack_from('<H', raw, 0xA)
        base.update(eepk=EEPK_TYPES.get(it['eepk_type'], it['eepk_type']), id=eid,
                    bone=BONE_LINKS.get(bone, bone), off=bool(it['effect_flags'] & 1))
    elif t == 11:
        base.update(acb=B.ACB_TYPES.get(it['acb_type'], it['acb_type']), cue=it['cue_id'])
    elif t == 14:
        base.update(bone_modification='0x%X (2 = Spine_Vert)' % it['raw'][0])
    elif t == 15:
        base.update(function='0x%X %s' % (it['function'], FUNCTIONS.get(it['function'], '')), params=it['params'])
    elif t == 21:
        base.update(eye_movement=it['raw'])
    return base


def _items_raw(path):
    """xv2bac.read_bac plus each item's bytes"""
    bac = B.read_bac(path)
    d = open(path, 'rb').read()
    _n, = struct.unpack_from('<I', d, 8)
    off, = struct.unpack_from('<I', d, 16)
    for e in bac['entries']:
        _fl, tc, _u, to = struct.unpack_from('<IHHQ', d, off + 16 * e['index'])
        raws = []
        for t in range(tc if to else 0):
            ty, c, _x, io = struct.unpack_from('<HHIQ', d, to + 16 * t)
            for k in range(c):
                raws.append(d[io + k * bac['sizes'][ty]:io + (k + 1) * bac['sizes'][ty]])
        assert len(raws) == len(e['items'])
        e['raw'] = raws
    return bac


BDM_NAMES = [  # XV2-Tools Xv2CoreLib/BDM/Parser.cs (type 0 entries), offset, struct format, name
    (0, 'H', 'DamageType'), (4, 'H', 'DamageAmount'), (12, 'H', 'AcbType'), (14, 'h', 'CueId'),
    (16, 'h', 'Effect1_ID'), (20, 'H', 'Effect1_EepkType'), (24, 'h', 'Effect2_ID'), (28, 'H', 'Effect2_EepkType'),
    (32, 'h', 'Effect3_ID'), (36, 'H', 'Effect3_EepkType'), (40, 'f', 'PushbackStrength'),
    (44, 'f', 'PushbackAcceleration'), (48, 'H', 'UserStun'), (50, 'H', 'VictimStun'), (52, 'H', 'KnockbackDuration'),
    (54, 'H', 'KnockbackRecoveryAfterImpactTime'), (56, 'H', 'KnockbackGroundImpactTime'),
    (60, 'f', 'KnockbackStrengthX'), (64, 'f', 'KnockbackStrengthY'), (68, 'f', 'KnockbackStrengthZ'),
    (72, 'f', 'KnockbackDragY'), (78, 'H', 'KnockbackGravityTime'), (80, 'h', 'VictimInvincibilityTime'),
    (86, 'h', 'AlimentType'), (94, 'H', 'DamageSpecial'), (100, 'H', 'StumbleType'), (102, 'H', 'DamageSecondaryType'),
    (106, 'H', 'CameraShakeTime'), (108, 'h', 'UserBpeID'), (110, 'h', 'VictimBpeID'),
    (112, 'h', 'StaminaBrokenOverrideBdmId'), (114, 'H', 'ZVanishEnableTime'), (116, 'H', 'UserAnimationTime'),
    (118, 'H', 'VictimAnimationTime'), (120, 'f', 'UserAnimationSpeed'), (124, 'f', 'VictimAnimationSpeed')]


def read_bdm_entry(path, want):
    """entry `want` of a BDM, its first sub-entry by XV2-Tools' names, and whether the 10 sub-entries differ"""
    d = open(path, 'rb').read()
    n, off = struct.unpack_from('<II', d, 8)
    for i in range(n):
        o = off + (4 + 10 * 0x80) * i
        if struct.unpack_from('<I', d, o)[0] != want:
            continue
        subs = [d[o + 4 + 0x80 * k:o + 4 + 0x80 * (k + 1)] for k in range(10)]
        dec = lambda b: {nm: round(struct.unpack_from('<' + f, b, at)[0], 4) for at, f, nm in BDM_NAMES}  # noqa
        first = dec(subs[0])
        diff = {k: {nm: v for nm, v in dec(subs[k]).items() if v != first[nm]} for k in range(1, 10)}
        return {'id': want, 'sub0': first, 'other_subs_differ': {k: v for k, v in diff.items() if v}}
    return None


def root_curve(ean, ai, step=2):
    bi = {b.name: i for i, b in enumerate(ean.bones)}
    a = ean.animations[ai]
    return [[f] + [round(v, 3) for v in ean.local(a, bi['b_C_Base'], f)[0][:3]] for f in range(0, a.frames, step)]


def report(skill_dir, cmn_bdm, btl_cmn_eepk, out):
    f = lambda ext: os.path.join(skill_dir, [n for n in os.listdir(skill_dir) if n.endswith(ext)][0])  # noqa: E731
    bac = _items_raw(f('DIE.bac'))
    doc = {'source': 'XV2 116_YMC_DIE (Fake Death, Yamcha) via tools/supamario_fakedeath_xv2.py; names: XV2-Tools',
           'bcm': read_bcm_full(f('_PLAYER.bcm')), 'entries': {}}
    for e in bac['entries']:
        doc['entries'][str(e['index'])] = [item(it, raw) for it, raw in sorted(
            zip(e['items'], e['raw']), key=lambda p: (p[0]['start'], p[0]['type']))]
    ean = X.Ean(open(f('DIE.ean'), 'rb').read(), smash_axes=True)
    doc['animations'] = [{'index': i, 'name': a.name, 'frames': a.frames} for i, a in enumerate(ean.animations)]
    doc['user_root'] = {'note': 'b_C_Base, metres, smash axes (+Z his facing, +Y up). BAC animation flags 5 = '
                                'MoveWithAxis X + Z: its X / Z move him, its Y does not',
                        '#0': root_curve(ean, 0), '#1': root_curve(ean, 1)}
    doc['bdm'] = {'20': read_bdm_entry(cmn_bdm, 20)}
    if btl_cmn_eepk:
        import xv2vfx as V
        ep = V.read_eepk(open(btl_cmn_eepk, 'rb').read(), strict=False)
        doc['btl_cmn_26'] = [{k: p[k] for k in ('AssetType', 'AttachementType', 'Orientation', 'Deactivation',
                                                'ESK', 'ScaleMin', 'ScaleMax', 'Position', 'Files', 'Flags1_names')}
                             for ef in ep['Effects'] if ef['IndexNum'] == 26 for p in ef['EffectParts']]
    with open(out, 'w') as fh:
        json.dump(doc, fh, indent=1)
    print('%s: %d BCM entries, %d BAC entries' % (out, len(doc['bcm']), len(doc['entries'])))


def se_extract(bank, out_dir, cues):
    import xv2acb as A
    acb = A.Acb(open(bank, 'rb').read())
    os.makedirs(out_dir, exist_ok=True)
    for c in cues:
        i = acb.cue_index(c)
        for n, w in enumerate(acb.cue_waves(i)):
            r = acb.wav[w]
            key = r['StreamAwbId'] if r['Streaming'] else r.get('MemoryAwbId', r.get('Id'))
            data = (acb.stream if r['Streaming'] else acb.mem).get(key)
            assert data and data[:3] == b'HCA', (i, w)
            fn = os.path.join(out_dir, '%s%s.hca' % (acb.name.get(i), '' if n == 0 else '_%d' % n))
            open(fn, 'wb').write(data)
            print('cue %d %s -> %s (%d Hz, %d samples, %.3f s; cue Length %d ms)' % (
                i, acb.name.get(i), fn, r['SamplingRate'], r['NumSamples'], r['NumSamples'] / float(r['SamplingRate']),
                acb.cues[i]['Length']))


def main():
    a = sys.argv[1:]
    if len(a) == 5 and a[0] == 'report':
        report(a[1], a[2], a[3], a[4])
    elif len(a) >= 4 and a[0] == 'se-extract':
        se_extract(a[1], a[2], a[3:])
    elif len(a) in (3, 4) and a[0] == 'se':
        import supamario_corebreaker_xv2 as C
        C.level(a[1], a[2], float(a[3]) if len(a) == 4 else -0.5)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
