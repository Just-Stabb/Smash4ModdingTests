#!/usr/bin/env python3
"""Tests Kirby's Hero copy fix v6 (the sword swung on the stone): the executable's motion table, the animations, the
sword hitboxes against Hero's blade, and the held sword's update run natively with Kirby in the new motions.

  python3 tools/kirby_hero_sword_swing_test.py NEW.rpx OLD.rpx MAIN.pac KIRBY_MAIN.pac KIRBY_VBN ULT_BRAVE [EFFECT.bin MTABLE]
      (exe_v46i, exe_v46h, the built motion/body/main.pac, Kirby's own main.pac and body/c00/model.vbn, Ultimate's
       fighter/brave: motion/body/c00/d03speciallwskill1-3.nuanmb and model/body/c00/model.nusktb)

- The executable: Kirby's motion table (0x103850A4, 8 bytes a motion) gives slots 0x304-0x307 the animations'
  hashes and SpecialLw's flags; they were empty (0) in OLD; no other word differs from OLD.
- The pack: the four animations under their names (the table's hashes), every other entry byte for byte Kirby's own.
- Each animation, decoded and posed as the game draws it (Kirby's skeleton, bind for the bones it lacks, the root's
  translation left out, the held item turned by kirby_hero_sword_anim.ITEM_TO_HAVE: fix v7, tools/kirby_hero_sword_clip.py): khm_sw_end + 1 frames (one a
  cast frame); every bone but LHaveN constant at SpecialLw1's last frame; LHaveN's model-space matrix at cast frame g
  = the sword model's frame on Hero (Sword1 @ inv(S2H), kirby_copy_sword.sword_to_have) at Ultimate frame mf(g) - 1 (the scripts' FT_MOTION_RATE clock; recomputed here from the
  Ultimate files and the reference scripts, independently of tools/kirby_hero_sword_anim.py's own numbers), the
  position scaled by the path's scale.
- The hitboxes the MSC makes (tools/kirby_hero_sword_msc.py's events, as kirby.c's generated block): every sword
  hitbox (bone 0x18) at its frame sits where Hero's sits on his blade (Hero's Sword1 at that frame x the script's
  offset, the path's scale) and inside the blade's reach; every arm hitbox where Hero's ArmR is.
- Fix v7, with EFFECT.bin / MTABLE (tools/kirby_hero_sword_acmd.py's output): each slot named BraveSword17-20 in the
  motion.mtable, its effect script's Sword_Glow / Terminate_Sword_Glow at Hero's frames (cast frames), his textures /
  shader, and both trail points on Hero's blade at that frame.
- Native (kirby_hero_sword_vis_test.World on NEW): with Kirby in each spell's motion in the stone, the update draws
  the sword while the sword int is 1 and hides it after (the motion kinds aren't the Marth / Sonic ones).
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import omo  # noqa: E402
import kirby_copy_motions as KM  # noqa: E402
import kirby_hero_sword_anim as A  # noqa: E402
import kirby_hero_sword_msc as SW  # noqa: E402
import kirby_copy_sword as CS  # noqa: E402
from kirby_copy_new_test import Img  # noqa: E402

FAIL = []


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        FAIL.append(what)


def mat_at(w, idx):
    i0 = int(np.floor(idx))
    i1 = min(i0 + 1, len(w) - 1)
    t = idx - i0
    if t < 1e-6:
        return w[i0]
    return A.slerp_rows(w[i0], w[i1], t)


def main():
    new_rpx, old_rpx, pac_path, kpac_path, vbn, ult = sys.argv[1:7]
    new, old = Img(new_rpx), Img(old_rpx)
    scale, arms = SW.load_path()
    names = {n: A.NAME % (n - 0x11 + 17) for n in A.SLOT}
    # the executable
    flags = old.w(A.MAIN_TABLE + 8 * A.POSE_SLOT + 4)
    got = {hex(A.SLOT[n]): (hex(new.w(A.MAIN_TABLE + 8 * A.SLOT[n])), hex(new.w(A.MAIN_TABLE + 8 * A.SLOT[n] + 4)),
                            old.w(A.MAIN_TABLE + 8 * A.SLOT[n]), old.w(A.MAIN_TABLE + 8 * A.SLOT[n] + 4)) for n in A.SLOT}
    want = {hex(A.SLOT[n]): (hex(A.anim_hash(names[n])), hex(flags), 0, 0) for n in A.SLOT}
    check('motion table slots 0x304-0x307: the animations\' hashes, SpecialLw\'s flags (0x%X); empty before' % flags,
          got, want)
    diff = []
    for (b0, d0), (b1, d1) in zip(old.segs, new.segs):
        assert b0 == b1 and len(d0) == len(d1)
        for i in range(0, len(d0), 4):
            if d0[i:i + 4] != d1[i:i + 4]:
                diff.append(b0 + i)
    check('no other word changed', sorted(set(diff) - {A.MAIN_TABLE + 8 * A.SLOT[n] + k for n in A.SLOT for k in (0, 4)}),
          [])
    # the pack
    pac = dict(omo.pac_read(pac_path))
    kpac = dict(omo.pac_read(kpac_path))
    check('the pack: Kirby\'s own entries byte for byte, plus the four animations',
          (sorted(set(pac) - set(kpac)), [k for k in kpac if pac.get(k) != kpac[k]]),
          (sorted(names[n] + '.omo' for n in A.SLOT), []))
    # the animations against the sword frame on Hero
    sk = KM.s4_skeleton(vbn)
    src = omo.Omo(kpac[A.POSE_FROM])
    ref = SW.parse()
    ev = SW.events(ref)
    skel = KM.ult_skeleton(os.path.join(ult, 'model/body/c00/model.nusktb'))
    have_h = next(h for n, _p, h, _b in sk if n == A.KIRBY_HAVE)
    mfs_all = {}
    for n in sorted(A.SLOT):
        o = omo.Omo(pac[names[n] + '.omo'])
        end = ev[n]['end']
        tr, frames = KM.tracks(os.path.join(ult, 'motion/body/c00/%s.nuanmb' % A.SPELLS[n]))
        w = KM.ult_world(skel, tr, frames)
        w['grip'] = w['Sword1'] @ np.linalg.inv(CS.sword_to_have(os.path.join(ult, 'model/body/c00/model.nusktb')))
        # the clock, again: game frame g -> motion frame (1-based) with the game script's rates
        rates = sorted((f, a['Speed']) for f, nm, a in ref[(n, 'ground', 'game')] if nm == 'Set_Frame_Duration')
        mf, mfs = 0.0, []
        for g in range(end + 1):
            mfs.append(mf)
            mf += 1.0 / ([d for f, d in rates if f <= mf + 1e-6] or [1.0])[-1]
        mfs_all[n] = mfs
        consts = []
        for node in o.nodes:
            if node[1] == have_h:
                continue
            vals = {tuple(np.round(np.concatenate([np.array(x, float).ravel() for x in o.sample(node[1], g)]), 3))
                    for g in range(o.frames)}
            want_v = tuple(np.round(np.concatenate([np.array(x, float).ravel()
                                                    for x in src.sample(node[1], src.frames - 1)]), 3))
            consts.append(vals == {want_v})
        worst = 0.0
        hb_bad, arm_bad = [], []
        lhw = []
        for g in range(o.frames):
            got_m = A.fk_lhaven(o, sk, g) @ A.ITEM_TO_HAVE      # fix v7: the item as the game draws it
            idx = min(max(mfs[g] - 1.0, 0.0), frames - 1.0)
            H = np.array(mat_at(w['grip'], idx))
            H[:3, 3] *= scale
            worst = max(worst, float(np.abs(got_m - H)[:3].max()))
            lhw.append(A.fk_lhaven(o, sk, g))                   # the joint (hitboxes are joint-local)
        for sit in ('ground', 'air'):
            for f, k, v in ev[n][sit]:
                if k != 'hitbox' or v[2] != SW.K_SWORD:
                    continue
                idx = min(max(mfs[f] - 1.0, 0.0), frames - 1.0)
                ours = lhw[f] @ np.array([v[9], v[10], v[11], 1.0])
                hid = v[0] - SW.ID_SHIFT
                hero_cmd = [a for mf_, nm, a in ref[(n, sit, 'game')] if nm.endswith('Special_Hitbox') and
                            a['ID'] == hid and SW.timing(ref[(n, 'ground', 'game')])(mf_) == f][0]
                S1 = np.array(mat_at(w['Sword1'], idx))
                local = np.linalg.inv(A.ITEM_TO_HAVE) @ np.linalg.inv(lhw[f]) @ ours      # in the item's frame
                on_axis = (abs(local[0] - SW.SWORD1_TO_HAVE * scale) < 0.05 and abs(local[2]) < 0.05   # Sword1's X axis
                           and A.BLADE[0] * scale <= local[1] <= A.BLADE[1] * scale)
                if hero_cmd['Bone'] == SW.SWORD_BONE:
                    # fix v8: on Hero's blade's axis at his X (his Z -2.5 / -2 / -1.5 put them off the drawn blade)
                    hero = S1 @ np.array([hero_cmd['X'], hero_cmd['Y'], 0.0, 1.0])
                    hero = hero * scale                                       # Hero's point, the path's scale
                    hero[3] = 1.0
                    if np.abs(ours - hero)[:3].max() > 0.05 or not on_axis:
                        hb_bad.append((sit, f, hid, np.round(ours[:3], 2).tolist(), np.round(hero[:3], 2).tolist()))
                else:                                       # fix v8: the arm (bone 0x16): the blade's base
                    hero = (S1 @ np.array([SW.HILT_X, 0.0, 0.0, 1.0]))[:3] * scale
                    if np.abs(ours[:3] - hero).max() > 0.05 or not on_axis:
                        arm_bad.append((sit, f, np.round(ours[:3], 2).tolist(), np.round(hero, 2).tolist()))
        check('%s: %d frames (cast 0-%d); every other bone constant at SpecialLw1\'s last frame (%d of %d)'
              % (names[n], end + 1, end, sum(consts), len(consts)), (o.frames, all(consts)), (end + 1, True))
        check('%s: LHaveN = Hero\'s sword frame (%s, FT_MOTION_RATE clock, scale %.3f) on every frame, within 0.05 (%.4f)'
              % (names[n], A.SPELLS[n], scale, worst), worst < 0.05, True)
        check('%s: fix v8: every sword hitbox on the drawn blade\'s axis, at Hero\'s X along his blade' % names[n],
              hb_bad, [])
        check('%s: fix v8: the arm hitbox on the blade\'s base (Sword1 X %.1f)' % (names[n], SW.HILT_X), arm_bad, [])
        bone0 = [x for x in ev[n].get('dropped', [])]
        check('%s: fix v8: Hero\'s bone-0 hitboxes left out (%d)' % (names[n], len(bone0)),
              [x for sit in ('ground', 'air') for _f, k, x in ev[n][sit] if k == 'hitbox' and x[2] == 0], [])
    # fix v7: the trail scripts (tools/kirby_hero_sword_acmd.py), when the built effect.bin / motion.mtable are given
    if len(sys.argv) > 8:
        import acmd
        import struct
        import kirby_hero_sword_acmd as T
        effects = acmd.ACMDFile.load(sys.argv[7])
        mt = open(sys.argv[8], 'rb').read()
        table = struct.unpack('>%dI' % (len(mt) // 4), mt)
        for n in sorted(A.SLOT):
            o = omo.Omo(pac[names[n] + '.omo'])
            tr, frames = KM.tracks(os.path.join(ult, 'motion/body/c00/%s.nuanmb' % A.SPELLS[n]))
            w = KM.ult_world(skel, tr, frames)
            at = SW.timing(ref[(n, 'ground', 'game')])
            sc = effects.script(T.name(n)) or []
            t, glows, ends_ = 0.0, [], []
            for c in sc:
                if c.name == 'FRAME':
                    t = float(c.params[0])
                elif c.name == 'Sword_Glow':
                    glows.append((t, dict(zip(acmd.INFO[c.ident]['syntax'], c.params))))
                elif c.name == 'Terminate_Sword_Glow':
                    ends_.append((t, c.params[0]))
            hero = [(at(mf), a) for mf, nm, a in ref[(n, 'ground', 'effect')] if nm == 'Sword_Glow']
            hero_end = [(at(mf), a['FadeTime']) for mf, nm, a in ref[(n, 'ground', 'effect')] if nm == 'Terminate_Sword_Glow']
            bad = []
            for (f, a), (hf, ha) in zip(glows, hero):
                idx = min(max(mfs_all[n][int(f)] - 1.0, 0.0), frames - 1.0)
                J = A.fk_lhaven(o, sk, int(f))
                S1 = np.array(mat_at(w['Sword1'], idx))
                for k1, k2 in (('X1', 'Y1'), ('X2', 'Y2')):
                    ours = J @ np.array([a[k1], a[k2], a[k1.replace('X', 'Z')], 1.0])
                    hp = S1 @ np.array([ha[k1], ha[k2], ha[k1.replace('X', 'Z')], 1.0]) * scale
                    hp[3] = 1.0
                    if np.abs(ours - hp)[:3].max() > 0.05:
                        bad.append((k1, np.round(ours[:3], 2).tolist(), np.round(hp[:3], 2).tolist()))
                if (f, a['Texture1'], a['Texture2'], a['Shader'], a['Bone1']) != (hf, ha['Texture1'], ha['Texture2'],
                                                                                  ha['Shader'], SW.K_SWORD):
                    bad.append(('params', f, hf))
            check('%s: motion.mtable 0x%X = %s; its effect script\'s trail (Hero\'s textures 0x%X / 0x%X, shader %d) from '
                  'cast frame %s to %s, both ends on Hero\'s blade at that frame'
                  % (T.name(n), A.SLOT[n], T.name(n), hero[0][1]['Texture1'], hero[0][1]['Texture2'],
                     hero[0][1]['Shader'], [x[0] for x in glows], ends_),
                  (table[A.SLOT[n]] == acmd.crc(T.name(n)), len(glows) == len(hero), ends_ == hero_end, bad),
                  (True, True, True, []))
            # fix v8: the blade's own effects (Hero's External_Graphic on his sword and their ends), in the window
            on, off = glows[0][0], ends_[0][0]
            t, made, killed, bad = 0.0, [], [], []
            for c in sc:
                if c.name == 'FRAME':
                    t = float(c.params[0])
                elif c.name == 'External_Graphic':
                    a = dict(zip(acmd.INFO[c.ident]['syntax'], c.params))
                    made.append((t, a['Graphic']))
                    hero_a = [h for mf, nm, h in ref[(n, 'ground', 'effect')] if nm == 'External_Graphic'
                              and h['Graphic'] == a['Graphic']][0]
                    idx = min(max(mfs_all[n][int(t)] - 1.0, 0.0), frames - 1.0)
                    J = A.fk_lhaven(o, sk, int(t))
                    S1 = np.array(mat_at(w['Sword1'], idx))
                    ours = J @ np.array([a['X'], a['Y'], a['Z'], 1.0])
                    hp = S1 @ np.array([hero_a['X'], hero_a['Y'], hero_a['Z'], 1.0]) * scale
                    if (np.abs(ours - hp)[:3].max() > 0.05 or a['Bone'] != SW.K_SWORD or a['Terminate'] != 0
                            or np.abs(np.array([a['XRot'], a['YRot'], a['ZRot'], a['Size']], float)
                                      - np.array([hero_a['XRot'], hero_a['YRot'], hero_a['ZRot'],
                                                  hero_a['Size'] * scale], float)).max() > 1e-4):
                        bad.append(('made', t, hex(a['Graphic'])))
                elif c.name == 'Terminate_Graphic_Effect':
                    killed.append((t, c.params[0]))
            hero_made = [h['Graphic'] for mf, nm, h in ref[(n, 'ground', 'effect')] if nm == 'External_Graphic']
            hero_killed = sorted(h['Graphic'] for mf, nm, h in ref[(n, 'ground', 'effect')]
                                 if nm == 'Terminate_Graphic_Effect' and h['Graphic'] >> 16 == SW.HERO_BANK)
            check('%s: fix v8: Hero\'s blade effects %s made in the script at the sword\'s first frame or Hero\'s, '
                  'on his blade (Sword1\'s origin), rotation and size his, Terminate 0; ended (%s) by the trail\'s end'
                  % (T.name(n), [hex(x) for x in hero_made], [hex(x) for x in hero_killed]),
                  ([x[1] for x in made], all(on <= x[0] < off for x in made), sorted(x[1] for x in killed),
                   all(x[0] <= off for x in killed), bad),
                  (hero_made, True, hero_killed, True, []))
    # native: the held sword's update with Kirby in the spells' motions
    import kirby_hero_sword_vis_test as V
    wd = V.World(new_rpx)
    bad = []
    for n in sorted(A.SLOT):
        wd.reset()
        seq = [wd.frame(status=0x175, motion=A.SLOT[n], sword=1, kind=0x2C, kirby_vis=0)[0] for _ in range(5)]
        seq += [wd.frame(status=0x175, motion=A.SLOT[n], sword=0, kind=0x2C, kirby_vis=0)[0] for _ in range(3)]
        if seq != [1] * 5 + [0] * 3:
            bad.append((hex(A.SLOT[n]), seq))
    check('native (%s): the update draws the sword with Kirby in 0x304-0x307 while the int is 1, hides it after'
          % os.path.basename(new_rpx), bad, [])
    print('%d failures' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
