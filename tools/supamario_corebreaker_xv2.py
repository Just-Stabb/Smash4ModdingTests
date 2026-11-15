#!/usr/bin/env python3
"""Core Breaker (Dragon Ball Xenoverse 2 Ultimate skill 2070_FIT_COR, Fu's) read from its files, for Supamario's up
special (fighters/supamario/README.md "Core Breaker"; the animation: tools/supamario_corebreaker_anim.py, the
effects: tools/supamario_corebreaker_fx.py).

  python3 -I tools/supamario_corebreaker_xv2.py report SKILL_DIR CMN.ean OUT.json
        the skill as data (reference/xv2/corebreaker_skill.json): the BCM tree, the BAC entries the main chain plays
        (items by type), the BDM, the cameras, the user's root travel (#0 / #1, b_C_Base), the victim's chain
  python3 -I tools/supamario_corebreaker_xv2.py se WAV_IN_DIR WAV_OUT_DIR [PEAK_DBFS]
        the decoded SE (tools/xv2acb.py extract + tools/xv2acb_decode.mjs) levelled to one peak (-0.5 dBFS, as the
        God Fist's tones), mono 16-bit; prints each one's length, peak and RMS over its first 0.5 s

What the files say (tools/xv2bac.py, xv2bac.read_bcm / read_bdm; XV2-Tools' names for the BAC types, EEPK types,
functions and throw flags):
- BCM: two chains from the ultimate button. #1 (with the +0x10 0x80000 condition: the giant-opponent one) BAC 0 ->
  1 -> 2 -> 7 (a dive with no grab) -> 11 (two plain hits, 5 and 450) / 5 (missed); #9 (the normal one) BAC 0 -> 1
  -> 2 -> 3 (a target: homing first) or 4 (none), both with the user's entry 10 / the victim's 17 on connect, ->
  5 when the dive connects with nothing.
- The BAC's item frames are the skill EAN's frames (an entry starts at its animation's start frame).
"""
import json
import math
import os
import struct
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import xv2bac as B  # noqa: E402
import xv2ean as X  # noqa: E402

MAIN_CHAIN = [0, 1, 2, 3, 4, 5, 10, 12, 13]      # the user (normal chain); 17-20: the victim
VICTIM_CHAIN = [17, 18, 19, 20]
FUNCTIONS = {0x2: 'Damage', 0x6: 'Invisibility', 0xB: 'Override ThrowHandler duration', 0x28: 'Invisible opponents'}
THROW_FLAGS = {0x1: 'FixedDir_BoneEnabled', 0x2: 'FixedDir_BoneDisabled', 0x4: 'FreeDir_BoneEnabled',
               0x8: 'FreeDir_BoneDisabled', 0x20: 'BacJump_AfterDuration', 0x80: 'BacJump_ReachGround',
               0x100: 'MoveVictimToUser', 0x200: 'MoveVictimToUser_RelativeDir'}
EEPK = {0: 'Common (BTL_CMN)', 1: 'StageBG (the stage\'s)', 6: 'UltimateSkill (2070_FIT_COR.eepk)'}
INVULN = {0: 'all attacks miss', 5: 'no damage, consume stamina'}


def _flags(v, table):
    return [n for b, n in table.items() if v & b] + (['0x%X' % (v & ~sum(table))] if v & ~sum(table) else [])


def entry_items(it):
    """an item in a plain, readable form"""
    t, s, d = it['type'], it['start'], it['duration']
    base = {'type': B.TYPES.get(t, t), 'frames': [s, s + d]}
    if t == 0:
        base.update(ean={0: 'CMN', 0xFFFE: 'skill', 9: 'CommonTail'}.get(it['ean_type'], it['ean_type']),
                    index=it['ean_index'], src=[it['start_frame'], it['end_frame']], flags='0x%X' % it['anim_flags'])
    elif t == 1:
        base.update(bdm=it['bdm_entry'], connect=bool(it['hit_flags'] & 8), damage=it['damage'],
                    guarded=it['damage_guarded'], pos=it['position'], size=it['size'])
    elif t == 2:
        base.update(flags='0x%X' % it['move_flags'], per_frame=it['direction'], drag=it['drag'])
    elif t == 3:
        base.update(invuln=INVULN.get(it['invuln_type'], it['invuln_type']))
    elif t == 8:
        base.update(eepk=EEPK.get(it['eepk_type'], it['eepk_type']), id=it['effect_id'], bone=it['bone'],
                    off=bool(it['effect_flags'] & 1))
    elif t == 11:
        base.update(acb=B.ACB_TYPES.get(it['acb_type'], it['acb_type']), cue=it['cue_id'])
    elif t == 15:
        base.update(function=FUNCTIONS.get(it['function'], '0x%X' % it['function']), params=it['params'])
    elif t == 16:
        base.update(bpe=it['bpe'])
    elif t == 17:
        base.update(flags=_flags(it['throw_flags'], THROW_FLAGS), user_bone=it['user_bone'],
                    victim_bone=it['victim_bone'], next_entry=None if it['victim_next_entry'] == 0xFFFF
                    else it['victim_next_entry'])
    elif t in (10, 12, 18, 20, 21, 7, 5, 4):
        base.update({k: v for k, v in it.items() if k not in ('type', 'start', 'duration', 'i4', 'flags6')})
    return base


def root_curve(ean, ai, step=5):
    bi = {b.name: i for i, b in enumerate(ean.bones)}
    a = ean.animations[ai]
    return [[f] + [round(v, 3) for v in ean.local(a, bi['b_C_Base'], f)[0][:3]] for f in range(0, a.frames, step)]


def report(skill_dir, cmn_ean, out):
    f = lambda ext: os.path.join(skill_dir, [n for n in os.listdir(skill_dir) if n.endswith(ext)][0])  # noqa: E731
    bac = B.read_bac(f('COR.bac'))
    doc = {'source': 'XV2 2070_FIT_COR (Core Breaker) via tools/supamario_corebreaker_xv2.py',
           'bcm': [{k: v for k, v in e.items()} for e in B.read_bcm(f('_PLAYER.bcm'))],
           'bdm': [{k: v for k, v in e.items() if k != 'raw_u16'} for e in B.read_bdm(f('_PLAYER.bdm'))],
           'entries': {}}
    for e in bac['entries']:
        if e['index'] in MAIN_CHAIN + VICTIM_CHAIN + [7, 11]:
            doc['entries'][str(e['index'])] = [entry_items(it) for it in sorted(
                e['items'], key=lambda i: (i['start'], i['type'])) if not (it['type'] == 0 and it['ean_type'] in (10, 11))]
    ean = X.Ean(open(f('COR.ean'), 'rb').read(), smash_axes=True)
    doc['user_root'] = {'note': 'b_C_Base (metres; smash axes: +Z his facing, +Y up); MoveWithAxis XYZ: it moves him',
                        '#0': root_curve(ean, 0), '#1': root_curve(ean, 1)}
    cam = X.Ean(open(f('COR.cam.ean'), 'rb').read())
    doc['cameras'] = [{'index': i, 'name': a.name, 'frames': a.frames} for i, a in enumerate(cam.animations)]
    if cmn_ean:
        c = X.Ean(open(cmn_ean, 'rb').read())
        doc['victim_cmn'] = {str(i): {'name': c.animations[i].name, 'frames': c.animations[i].frames}
                             for i in (238, 239, 71, 96)}
    with open(out, 'w') as fh:
        json.dump(doc, fh, indent=1)
    print('%s: %d BCM entries, %d BDM, %d BAC entries kept' % (out, len(doc['bcm']), len(doc['bdm']),
                                                                len(doc['entries'])))


def _read_wav(p):
    w = wave.open(p)
    n, ch, sr, sw = w.getnframes(), w.getnchannels(), w.getframerate(), w.getsampwidth()
    assert sw == 2, p
    a = struct.unpack('<%dh' % (n * ch), w.readframes(n))
    if ch > 1:
        a = [sum(a[i:i + ch]) / ch for i in range(0, len(a), ch)]
    return [x / 32768.0 for x in a], sr


def level(in_dir, out_dir, peak_db=-0.5):
    os.makedirs(out_dir, exist_ok=True)
    for fn in sorted(os.listdir(in_dir)):
        if not fn.lower().endswith('.wav'):
            continue
        a, sr = _read_wav(os.path.join(in_dir, fn))
        pk = max(abs(x) for x in a) or 1.0
        g = 10 ** (peak_db / 20.0) / pk
        b = [max(-32768, min(32767, int(round(x * g * 32767)))) for x in a]
        w = wave.open(os.path.join(out_dir, fn), 'wb')
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(struct.pack('<%dh' % len(b), *b))
        w.close()
        head = b[:sr // 2]
        rms = math.sqrt(sum(x * x for x in head) / len(head)) / 32768.0
        print('%-44s %5.2f s  gain %+5.1f dB  peak %.1f dBFS  RMS(0.5 s) %.1f dB' % (
            fn, len(b) / float(sr), 20 * math.log10(g), peak_db, 20 * math.log10(max(rms, 1e-9))))


def main():
    a = sys.argv[1:]
    if len(a) == 4 and a[0] == 'report':
        report(a[1], a[2], a[3])
    elif len(a) in (3, 4) and a[0] == 'se':
        level(a[1], a[2], float(a[3]) if len(a) == 4 else -0.5)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
