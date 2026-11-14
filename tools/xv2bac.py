#!/usr/bin/env python3
"""Dragon Ball Xenoverse 2 skill timing files: BAC (the action timeline), BCM (the move's links: which BAC
entry runs, and which ones the user / the victim play when it connects) and BAS (the skill's state header).

  python3 -I tools/xv2bac.py FILE.bac [FILE.bcm] [FILE.bas]     the timeline, entry by entry
  python3 -I tools/xv2bac.py --json FILE.bac OUT.json           every entry and item as JSON

Little-endian. Layout read from the files themselves (the 030_GOD_CSA skill, Super God Fist) against LazyBone152's
XV2-Tools names (Xv2CoreLib BAC / BCM); field names follow those where the values fit them, `?` where not known.

BAC: +0 "#BAC", +4 u16 0xFFFE, +8 u32 entry count, +16 u32 entry table offset, +0x20 12 floats (header values).
  Entry (16 bytes): u32 flags, u16 type-list count, u16, u64 type-list offset (0: an empty entry).
  Type list item (16 bytes): u16 type, u16 item count, u32, u64 offset of the items (0 when none).
  Item: u16 start frame, u16 duration, u16 ?, u16 character / flags (face animations: 1 / 2), then the type's own
  fields. Item sizes (this file's: the gap between one type's items and the next's): 0 Animation 0x24,
  1 Hitbox 0x40, 2 Movement 0x24, 3 Invulnerability 0xC, 4 TimeScale 0xC, 5 Tracking 0x10, 7 BcmCallback 0xC,
  8 Effect 0x30, 10 Camera 0x30 (none here), 11 Sound 0x10, 15 Functions 0x20, 16 ScreenEffect 0x20,
  17 ThrowHandler 0x20, 18 PhysicsObject 0x20, 20 HomingMovement 0x28, 21 EyeMovement 0x20.
  Frames are XV2's 60 a second (Smash 4's rate too).

Fields decoded (offsets in the item):
  0 Animation: +8 u16 EAN type (0 common CMN.ean, 5 character, 10 / 11 face base / forehead, 0xFFFE the skill's
    own EAN), +A u16 EAN index, +C u16 flags, +E u16 ?, +10 u16 start frame, +12 u16 end frame, +14 u16 loop start
    (0xFFFF none), +16 u16, +18 f32 speed, +1C f32 blend weight, +20 f32 blend step.
  1 Hitbox: +8 u16 BDM entry, +A u16 flags, +C u16 damage, +E u16 damage when guarded, +10 u16 stamina-broken BDM,
    +12 u16 ?, +14 u16, +16 u16, +18 f32 x 3 position, +24 f32 size, +28 f32 x 6 min / max (box hitboxes).
  2 Movement: +8 u16 flags, +A u16, +C f32 x 3 direction (per frame; +Z forward), +18 f32 x 3 drag.
  3 Invulnerability: +8 u16 type. 4 TimeScale: +8 f32 scale. 5 Tracking: +8 f32 strength, +C u16 flags.
  7 BcmCallback: +8 u16 flags (the window in which the BCM may chain another move).
  8 Effect: +8 u16 EEPK type (1 common CMN.eepk, 2 character, 3 / 5 skill effects with +C = the skill id,
    0 ?), +A u16, +C u16 skill id (0xFFFF none), +E u16, +10 u16 effect id, +12 u16 bone, +14 f32 x 3 position,
    +20 f32 x 3 rotation, +2C u16 flags (1 = off).
  11 Sound: +8 u16 ACB type (0 common SE, 3 skill SE, 10 / 11 skill voice ...), +A u16, +C u16 cue id, +E u16 flags.
  15 Functions: +8 u16 function, +A u16, +C f32 x 5 parameters.
  16 ScreenEffect: +8 u16 BPE id, +A u16 bone, +C u16, +E u16.
  17 ThrowHandler: +8 u16 flags, +A u16, +C u16 user bone, +E u16 victim bone, +10 u16 the victim's next BAC entry
    (0xFFFF none), +12 u16, +14 f32 x 3 displacement.
  20 HomingMovement / 21 EyeMovement / 18 PhysicsObject: raw words.
BCM (0x70 bytes an entry after a 0x10 header; +8 u32 count, +12 u32 offset): +0x18 u32 activator conditions,
  +0x1C u32 state, +0x20 u16 BAC entry (primary), +0x22 u16 charge entry, +0x26 u16 user's entry on connect,
  +0x28 u16 victim's entry on connect, +0x2A u16 airborne entry, +0x30 u32 ki cost (?), +0x40 u32 (?).
"""
import json
import struct
import sys

TYPES = {0: 'Animation', 1: 'Hitbox', 2: 'Movement', 3: 'Invulnerability', 4: 'TimeScale', 5: 'Tracking',
         6: 'ChargeControl', 7: 'BcmCallback', 8: 'Effect', 9: 'Projectile', 10: 'Camera', 11: 'Sound',
         12: 'TargetingAssistance', 13: 'PartInvisibility', 14: 'BoneModification', 15: 'Functions',
         16: 'ScreenEffect', 17: 'ThrowHandler', 18: 'PhysicsObject', 19: 'Aura', 20: 'HomingMovement',
         21: 'EyeMovement'}
EAN_TYPES = {0: 'CMN', 5: 'character', 10: 'face base', 11: 'face forehead', 0xFFFE: 'skill'}
EEPK_TYPES = {0: 'common?', 1: 'CMN', 2: 'character', 3: 'skill (type 3)', 5: 'skill (type 5)'}
ACB_TYPES = {0: 'common SE', 3: 'skill SE', 10: 'skill voice A', 11: 'skill voice B'}


def _u16s(b, o, n):
    return list(struct.unpack_from('<%dH' % n, b, o))


def _f32s(b, o, n):
    return [round(x, 4) for x in struct.unpack_from('<%df' % n, b, o)]


def decode(ty, b):
    """the type's fields of one item (b: its bytes)"""
    st, dur, i4, f6 = struct.unpack_from('<4H', b, 0)
    d = {'start': st, 'duration': dur, 'i4': i4, 'flags6': f6}
    if ty == 0:
        u = _u16s(b, 8, 8)
        d.update(ean_type=u[0], ean_index=u[1], anim_flags=u[2], i_e=u[3], start_frame=u[4], end_frame=u[5],
                 loop_start=u[6], i_16=u[7], speed=_f32s(b, 0x18, 1)[0], blend=_f32s(b, 0x1C, 2))
    elif ty == 1:
        u = _u16s(b, 8, 8)
        d.update(bdm_entry=u[0], hit_flags=u[1], damage=u[2], damage_guarded=u[3], stamina_bdm=u[4],
                 i_12=u[5], i_14=u[6], i_16=u[7], position=_f32s(b, 0x18, 3), size=_f32s(b, 0x24, 1)[0],
                 box=_f32s(b, 0x28, 6))
    elif ty == 2:
        u = _u16s(b, 8, 2)
        d.update(move_flags=u[0], i_a=u[1], direction=_f32s(b, 0xC, 3), drag=_f32s(b, 0x18, 3))
    elif ty == 3:
        d.update(invuln_type=_u16s(b, 8, 1)[0])
    elif ty == 4:
        d.update(time_scale=_f32s(b, 8, 1)[0])
    elif ty == 5:
        d.update(strength=_f32s(b, 8, 1)[0], track_flags=_u16s(b, 0xC, 1)[0])
    elif ty == 7:
        d.update(bcm_flags=_u16s(b, 8, 1)[0])
    elif ty == 8:
        u = _u16s(b, 8, 6)
        d.update(eepk_type=u[0], i_a=u[1], skill_id=u[2], i_e=u[3], effect_id=u[4], bone=u[5],
                 position=_f32s(b, 0x14, 3), rotation=_f32s(b, 0x20, 3), effect_flags=_u16s(b, 0x2C, 1)[0])
    elif ty == 11:
        u = _u16s(b, 8, 4)
        d.update(acb_type=u[0], i_a=u[1], cue_id=u[2], sound_flags=u[3])
    elif ty == 15:
        u = _u16s(b, 8, 2)
        d.update(function=u[0], i_a=u[1], params=_f32s(b, 0xC, 5))
    elif ty == 16:
        d.update(bpe=_u16s(b, 8, 1)[0], words=_u16s(b, 0xA, 3))
    elif ty == 17:
        u = _u16s(b, 8, 6)
        d.update(throw_flags=u[0], i_a=u[1], user_bone=u[2], victim_bone=u[3], victim_next_entry=u[4], i_12=u[5],
                 displacement=_f32s(b, 0x14, 3))
    else:
        d.update(raw=_u16s(b, 8, (len(b) - 8) // 2))
    return d


def read_bac(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'#BAC', path
    n, = struct.unpack_from('<I', d, 8)
    off, = struct.unpack_from('<I', d, 16)
    lists = []
    for i in range(n):
        _fl, tc, _u, to = struct.unpack_from('<IHHQ', d, off + 16 * i)
        lists.append([struct.unpack_from('<HHIQ', d, to + 16 * t) for t in range(tc)] if to else [])
    # item sizes: the gap to the next item block in the file (the last block runs to the file's end)
    starts = sorted({io for tl in lists for _ty, c, _x, io in tl if c and io} | {len(d)})
    size = {}
    for tl in lists:
        for ty, c, _x, io in tl:
            if c and io:
                size.setdefault(ty, (starts[starts.index(io) + 1] - io) // c)
    entries = []
    for i, tl in enumerate(lists):
        fl, = struct.unpack_from('<I', d, off + 16 * i)
        items = []
        for ty, c, _x, io in tl:
            for k in range(c):
                b = d[io + k * size[ty]:io + (k + 1) * size[ty]]
                it = decode(ty, b)
                it['type'] = ty
                items.append(it)
        entries.append({'index': i, 'flags': fl, 'types': [t[0] for t in tl], 'items': items})
    return {'header': _f32s(d, 0x20, 12), 'sizes': size, 'entries': entries}


def read_bcm(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'#BCM', path
    n, off = struct.unpack_from('<II', d, 8)
    out = []
    for i in range(n):
        o = off + 0x70 * i
        u = _u16s(d, o + 0x20, 7)
        out.append({'index': i, 'conditions': struct.unpack_from('<I', d, o + 0x18)[0],
                    'state': struct.unpack_from('<I', d, o + 0x1C)[0], 'bac_entry': u[0], 'charge_entry': u[1],
                    'user_connect': u[3], 'victim_connect': u[4], 'airborne_entry': u[5],
                    'ki_cost?': struct.unpack_from('<I', d, o + 0x30)[0]})
    return out


def read_bas(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'#BAS', path
    return {'size': len(d), 'names': [s.decode() for s in d.split(b'\0') if s.isalpha() and s.isupper() and len(s) > 2]}


def _hz(v):
    return 'none' if v == 0xFFFF else v


def line(it):
    ty = it['type']
    t = '%3d-%-3d' % (it['start'], it['start'] + it['duration'])
    name = TYPES.get(ty, 'type%d' % ty)
    if ty == 0:
        if it['ean_type'] in (10, 11):
            return None                       # the face animations (eyes / mouth), left out of the summary
        return '%s %s: %s EAN #%d frames %d-%d (loop %s) speed %g' % (
            t, name, EAN_TYPES.get(it['ean_type'], it['ean_type']), it['ean_index'], it['start_frame'],
            it['end_frame'], _hz(it['loop_start']), it['speed'])
    if ty == 1:
        return '%s %s: BDM #%d flags 0x%X damage %d (guarded %d, stamina BDM %d) at %s size %g' % (
            t, name, it['bdm_entry'], it['hit_flags'], it['damage'], it['damage_guarded'], it['stamina_bdm'],
            it['position'], it['size'])
    if ty == 2:
        return '%s %s: flags 0x%X direction %s drag %s (a frame)' % (t, name, it['move_flags'], it['direction'],
                                                                    it['drag'])
    if ty == 3:
        return '%s %s: type %d' % (t, name, it['invuln_type'])
    if ty == 4:
        return '%s %s: x%g' % (t, name, it['time_scale'])
    if ty == 5:
        return '%s %s: strength %g' % (t, name, it['strength'])
    if ty == 7:
        return '%s %s: flags 0x%X' % (t, name, it['bcm_flags'])
    if ty == 8:
        src = EEPK_TYPES.get(it['eepk_type'], it['eepk_type'])
        if it['skill_id'] != 0xFFFF:
            src += ' %d' % it['skill_id']
        return '%s %s: %s effect %d bone %d%s' % (t, name, src, it['effect_id'], it['bone'],
                                                 ' OFF' if it['effect_flags'] & 1 else '')
    if ty == 11:
        return '%s %s: %s cue %d' % (t, name, ACB_TYPES.get(it['acb_type'], it['acb_type']), it['cue_id'])
    if ty == 15:
        return '%s %s: function 0x%X params %s' % (t, name, it['function'], it['params'])
    if ty == 16:
        return '%s %s: BPE %d %s' % (t, name, it['bpe'], it['words'])
    if ty == 17:
        return '%s %s: flags 0x%X user bone %d victim bone %d victim next entry %s' % (
            t, name, it['throw_flags'], it['user_bone'], it['victim_bone'], _hz(it['victim_next_entry']))
    return '%s %s: %s' % (t, name, it.get('raw'))


def main():
    a = sys.argv[1:]
    if a and a[0] == '--json':
        json.dump(read_bac(a[1]), open(a[2], 'w'), indent=1)
        return
    if not a:
        sys.exit(__doc__)
    bac = read_bac(a[0])
    for p in a[1:]:
        if p.lower().endswith('.bcm'):
            print('BCM:')
            for e in read_bcm(p):
                if e['bac_entry'] or e['user_connect'] or e['victim_connect']:
                    print('  #%d conditions 0x%08X: BAC %d; on connect user %d, victim %d' % (
                        e['index'], e['conditions'], e['bac_entry'], e['user_connect'], e['victim_connect']))
        elif p.lower().endswith('.bas'):
            print('BAS:', read_bas(p))
    print('BAC header values:', bac['header'])
    for e in bac['entries']:
        print('entry %d:%s' % (e['index'], ' (empty)' if not e['items'] else ''))
        for it in sorted(e['items'], key=lambda i: (i['start'], i['type'])):
            s = line(it)
            if s:
                print('  ' + s)


if __name__ == '__main__':
    main()
