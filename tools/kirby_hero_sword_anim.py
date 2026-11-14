#!/usr/bin/env python3
"""Kirby's Hero copy fix v6: Hero's sword swung on the Stone the way Hero swings it in each sword spell.

  python3 tools/kirby_hero_sword_anim.py ULT_BRAVE KIRBY OUT [--rpx EXE.rpx] [--preview DIR]

ULT_BRAVE: Ultimate's fighter/brave (the user's brave.zip): motion/body/c00/d03speciallwskill{1,2,3}.nuanmb,
model/body/c00/model.nusktb, model/body/c00/model.numshb (Hero's height). KIRBY: Kirby's Smash 4 fighter folder
(motion/body/main.pac, model/body/c00/model.vbn, model/stone/c00/model.nud: the stone's height). OUT gets
motion/body/main.pac (Kirby's own pack + the four animations), rpx_args.txt (the motion table words, with --rpx: the
executable whose table is checked) and path.json (reference/kirby_hero_sword_path.json: the sword's path and the
arm hitbox offsets, read by tools/kirby_hero_sword_msc.py and the tests). fighters/kirby/specials.md "Hero copy fix v6".

How the sword moves (the held sword is Kirby's article 26 linked to his joint 0x18, LHaveN: fix v5):
- Kirby is invisible in the Stone and his hold motions (0x2ED / 0x2F1) have no animation, so his own LHaveN is moved:
  during a sword spell the MSC (kirby.c khm_sw_motion) plays Kirby motion SLOT[n] (0x304-0x307: empty slots between
  Final 0x300 and CaptainSpecialN 0x30B, motion.mtable hash 0, so no ACMD runs; Marth's sword aerials use 0x301-0x303)
  and sets its frame to the cast's frame every frame. The motion's animation (Kirby's body pack, NAME % n) holds
  every bone of Kirby's stone pose (SpecialLw1's last frame: the pose the transform ends in) and moves LHaveN so that
  its model-space transform is the sword model's frame on Hero in Ultimate's animation (Sword1 @ inv(S2H): the
  model is given in HaveR's frame as Sword1 sits in it in the bind pose, tools/kirby_copy_sword.py; Sword1 has its
  own tracks in the spells, so HaveR itself is up to ~50 degrees off the blade), its position scaled by SCALE about the feet (Kirby's size: the stone's top over Hero's) and
  its orientation Hero's (both models face +Z, Y up). The sword and its bone-0x18 hitboxes / effects follow it.
- SCALE (--scale): 1 by default, Hero's own path: the sword where Hero's hand is if Hero stood in the stone's place,
  as v6's decision (Hero's sword at Hero's size, "attached at Hero's hand offset", its hitboxes as on Hero; the
  spells' bone-0 hitboxes are Hero's positions too, e.g. Flame Slash's 10.5 at Y 18 Z 16). --scale kirby (the
  stone's top over Hero's, 0.415) gives Kirby's size: the preview shows that sword inside the 8-tall stone for most
  of each spell (Hero's hands are inside his own silhouette), and a Hero-size blade on that path under the floor.
- Timing: cast frame g shows Hero's motion frame mf(g), the scripts' Set_Frame_Duration (FT_MOTION_RATE) rates
  applied (tools/kirby_hero_sword_msc.py timing(), the hitboxes' own clock): ACMD frames are 1-based, so the
  animation index is mf - 1, interpolated between Ultimate's frames. One animation key a cast frame, 0 to the
  spell's end (khm_sw_end).
- Spells (Ultimate motion_list): 17 Flame Slash and 18 Kacrackle Slash play d03speciallwskill3 (their rates differ:
  two animations), 19 Metal Slash skill1, 20 Hatchet Man skill2. The ground animations serve the air casts too (the
  stone is the same either way).
- With SCALE != 1 the sword model must be scaled the same (kirby_copy_sword.py --rescale MODEL_DIR SCALE). LHaveN
  keeps scale 1 either way; the sword hitboxes' and effects' offsets along it are scaled by path.json's scale in
  tools/kirby_hero_sword_msc.py (their sizes stay Hero's).
- Hero's arm hitbox (bone 0x16, his forearm ArmR) is put on LHaveN at ArmR's origin in the grip frame at that
  frame, scaled by SCALE (path.json "arm"): the stone has no arm.
"""
import argparse
import json
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import omo  # noqa: E402
import kirby_copy_motions as KM  # noqa: E402
import kirby_hero_sword_msc as SWM  # noqa: E402

SPELLS = {0x11: 'd03speciallwskill3', 0x12: 'd03speciallwskill3', 0x13: 'd03speciallwskill1', 0x14: 'd03speciallwskill2'}
SLOT = {0x11: 0x304, 0x12: 0x305, 0x13: 0x306, 0x14: 0x307}
NAME = 'FitKirbyBodyMainD03SpecialLwBraveSword%d'          # % the spell number (17-20)
POSE_FROM = 'FitKirbyBodyMainD03SpecialLw1.omo'
POSE_SLOT = 0x2E5                                           # SpecialLw: its flags word for the new slots
MAIN_TABLE = 0x103850A4                                     # Kirby's motion table: (animation hash, flags) a motion
HAVE, ARM = 'HaveR', 'ArmR'
GRIP = 'grip'                                               # Sword1 @ inv(S2H) (hero_paths)
KIRBY_HAVE, KIRBY_HAND = 'LHaveN', 'LHandN'
BLADE = (-2.12, 12.06)                                      # Hero's sword model along LHaveN's +Y (kirby_copy_sword.py);
                                                            # fix v6 scales it by SCALE too (kirby_copy_sword.py --rescale)


def anim_hash(name):
    """the motion tables' key of an animation file (name without .omo; kirby_marth_sword.anim_hash)"""
    import zlib
    return zlib.crc32(name.encode(), 0xFFFFFFFF) & 0xFFFFFFFF


def motion_frames(n, ref):
    """[motion frame (1-based, ACMD's)] for cast frames 0 .. khm_sw_end(n)"""
    game = ref[(n, 'ground', 'game')]
    rates = sorted((f, a['Speed']) for f, nm, a in game if nm == 'Set_Frame_Duration')
    end = SWM.events(ref)[n]['end']
    out, mf = [], 0.0
    for _g in range(end + 1):
        out.append(mf)
        dur = 1.0
        for f, d in rates:
            if f <= mf + 1e-6:
                dur = d
        mf += 1.0 / dur
    return out


def slerp_rows(m0, m1, t):
    """interpolated 4x4 (position lerp, rotation nlerp of the quaternions)"""
    import kirby_copy_motions as K
    p0, q0, _s, _ = K.decompose(m0[None])
    p1, q1, _s, _ = K.decompose(m1[None])
    q0, q1 = q0[0], q1[0]
    if np.dot(q0, q1) < 0:
        q1 = -q1
    q = (1 - t) * q0 + t * q1
    q /= np.linalg.norm(q)
    return K.trs((1 - t) * p0[0] + t * p1[0], q, np.ones(3))


def hero_paths(ult, skill):
    """{bone: [F, 4, 4]} Hero's world (model space) per Ultimate frame, plus GRIP: the sword model's frame (its
    vertices are given in HaveR's frame as Sword1 sits there in the bind pose, kirby_copy_sword.sword_to_have: S2H), so
    GRIP = Sword1 @ inv(S2H): the blade exactly where Hero's (bound to Sword1) is. HaveR itself won't do: Sword1 has
    its own tracks in the spells (up to ~50 degrees off its bind relation to HaveR)"""
    import kirby_copy_sword as CS
    skel_path = os.path.join(ult, 'model/body/c00/model.nusktb')
    skel = KM.ult_skeleton(skel_path)
    tr, frames = KM.tracks(os.path.join(ult, 'motion/body/c00/%s.nuanmb' % skill))
    w = KM.ult_world(skel, tr, frames)
    w[GRIP] = w['Sword1'] @ np.linalg.inv(CS.sword_to_have(skel_path))
    return w, frames


def at_index(w, idx):
    i0 = int(math.floor(idx))
    i1 = min(i0 + 1, len(w) - 1)
    t = idx - i0
    return w[i0] if t < 1e-6 else slerp_rows(w[i0], w[i1], t)


def heights(ult, kirby):
    """(Hero's model top, the stone's top): SCALE = stone / Hero"""
    import ssbh_data_py as s
    import nud
    m = s.mesh_data.read_mesh(os.path.join(ult, 'model/body/c00/model.numshb'))
    hero = max(float(np.array(o.positions[0].data)[:, 1].max()) for o in m.objects
               if not any(k in o.name.lower() for k in ('sword', 'shield')))
    stone = 0.0
    for me in nud.read(os.path.join(kirby, 'model/stone/c00/model.nud')):
        if me.name.startswith('BodyStoneKirbyM'):
            for p in me.polygons:
                stone = max(stone, float(np.asarray(p.pos)[:, 1].max()))
    return hero, stone


def kirby_pose(kirby):
    """Kirby's skeleton, the stone pose (SpecialLw1's last frame: {hash: (pos, quat, scale)} for its nodes) and the
    world matrices of that pose (bind for the bones the animation lacks)"""
    sk = KM.s4_skeleton(os.path.join(kirby, 'model/body/c00/model.vbn'))
    pac = dict(omo.pac_read(os.path.join(kirby, 'motion/body/main.pac')))
    src = omo.Omo(pac[POSE_FROM])
    pose = {n[1]: src.sample(n[1], src.frames - 1) for n in src.nodes}
    w = {}
    for name, par, h, bind in sk:
        loc = KM.trs(np.array(pose[h][0]), np.array(pose[h][1]), np.array(pose[h][2])) if h in pose else bind
        w[name] = w[sk[par][0]] @ loc if par is not None else loc
    return sk, src, pose, w


def build(ult, kirby, ref_path=SWM.REF, scale_mode='hero'):
    ref = SWM.parse(ref_path)
    hero_top, stone_top = heights(ult, kirby)
    scale = {'hero': 1.0, 'kirby': stone_top / hero_top}.get(scale_mode)
    if scale is None:
        scale = float(scale_mode)
    sk, src, pose, kw = kirby_pose(kirby)
    have_h = next(h for n, _p, h, _b in sk if n == KIRBY_HAVE)
    parent = kw[KIRBY_HAND]
    assert next(sk[p][0] for n, p, _h, _b in sk if n == KIRBY_HAVE) == KIRBY_HAND
    inv_parent = np.linalg.inv(parent)
    anims, path = {}, {'scale': scale, 'hero_top': hero_top, 'stone_top': stone_top, 'spells': {}}
    cache = {}
    for n in sorted(SPELLS):
        skill = SPELLS[n]
        if skill not in cache:
            cache[skill] = hero_paths(ult, skill)
        w, frames = cache[skill]
        mfs = motion_frames(n, ref)
        P, Q, S, worlds, arms, idxs = [], [], [], [], [], []
        worst = 0.0
        for mf in mfs:
            idx = min(max(mf - 1.0, 0.0), frames - 1.0)
            H = at_index(w[GRIP], idx)
            A = at_index(w[ARM], idx)
            D = np.array(H)
            D[:3, 3] = H[:3, 3] * scale                        # about Hero's feet = the stone's base
            loc = inv_parent @ D
            p, q, s, shear = KM.decompose(loc[None])
            worst = max(worst, shear)
            P.append(tuple(p[0]))
            Q.append(tuple(q[0]))
            S.append(tuple(s[0]))
            worlds.append([[round(float(x), 4) for x in row] for row in D])
            arm = (np.linalg.inv(H) @ A)[:3, 3] * scale         # ArmR's origin in the grip frame, the path's scale
            arms.append([round(float(x), 4) for x in arm])
            idxs.append(round(idx, 4))
        assert worst < 1e-3, 'LHaveN local has shear %.4f' % worst
        o = omo.Omo(src.encode())
        o.frames = len(mfs)
        o.nodes = []
        for name, _par, h, _b in sk:
            if h in pose:
                p, q, s = pose[h]
                omo.set_node(o, h, [p] * o.frames, [q] * o.frames, [s] * o.frames)
        omo.set_node(o, have_h, P, Q, S)
        anims[n] = o
        path['spells']['0x%x' % n] = {'slot': '0x%x' % SLOT[n], 'anim': NAME % (n - 0x11 + 17), 'skill': skill,
                                      'motion_index': idxs, 'lhaven_world': worlds, 'arm': arms}
    return anims, path, sk


def fk_lhaven(o, sk, frame):
    """LHaveN's model-space matrix in animation o at a frame (bind for the bones it lacks)"""
    have = {n[1] for n in o.nodes}
    w = {}
    for name, par, h, bind in sk:
        smp = o.sample(h, frame) if h in have else None
        loc = KM.trs(np.array(smp[0]), np.array(smp[1]), np.array(smp[2])) if smp else bind
        w[name] = w[sk[par][0]] @ loc if par is not None else loc
    return w[KIRBY_HAVE]


def preview(path, out_dir):
    """side (Z-Y) views of the blade, a line per cast frame, the stone's box, for each spell"""
    from PIL import Image, ImageDraw
    os.makedirs(out_dir, exist_ok=True)
    names = {0x11: 'Flame Slash', 0x12: 'Kacrackle Slash', 0x13: 'Metal Slash', 0x14: 'Hatchet Man'}
    files = []
    for key, sp in sorted(path['spells'].items()):
        n = int(key, 16)
        W, H, k = 720, 560, 12.0 if path['scale'] > 0.7 else 16.0
        img = Image.new('RGB', (W, H), (250, 250, 250))
        d = ImageDraw.Draw(img)

        def px(z, y):
            return (W / 2 + z * k, H - 60 - y * k)
        d.line([px(-25, 0), px(25, 0)], fill=(120, 120, 120))
        d.rectangle([px(-6, 8), px(6, 0)], outline=(110, 90, 70), width=2)       # the stone (side view)
        frames = sp['lhaven_world']
        for g, m in enumerate(frames):
            m = np.array(m)
            a = m @ np.array([0, BLADE[0] * path['scale'], 0, 1.0])       # the model scaled too (--rescale)
            b = m @ np.array([0, BLADE[1] * path['scale'], 0, 1.0])
            t = g / max(1, len(frames) - 1)
            col = (int(40 + 200 * t), int(80 + 60 * (1 - t)), int(220 - 180 * t))
            d.line([px(a[2], a[1]), px(b[2], b[1])], fill=col, width=2)
            d.ellipse([px(a[2], a[1])[0] - 2, px(a[2], a[1])[1] - 2, px(a[2], a[1])[0] + 2, px(a[2], a[1])[1] + 2],
                      fill=col)
        d.text((10, 10), '%s (spell %d, %s): blade from grip to tip, every cast frame (blue = start, red = end)'
               % (names[n], n, sp['skill']), fill=(0, 0, 0))
        d.text((10, 26), 'side view: right = Kirby\'s facing (+Z), up = +Y; box = the stone (8 tall); 1 unit = %d px; '
               'path scale %.3f' % (k, path['scale']), fill=(0, 0, 0))
        f = os.path.join(out_dir, 'sword_path_%d.png' % n)
        img.save(f)
        files.append(f)
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('ult')
    ap.add_argument('kirby')
    ap.add_argument('out')
    ap.add_argument('--rpx', help='the executable the table words go on (checked: the slots empty)')
    ap.add_argument('--preview')
    ap.add_argument('--scale', default='hero', help='hero (1: the default), kirby (the stone\'s top / Hero\'s) or a '
                    'number: the path\'s scale about the feet; the sword model must be rescaled by it '
                    '(kirby_copy_sword.py --rescale) and kirby_hero_sword_msc.py scales the sword offsets by it')
    a = ap.parse_args()
    anims, path, sk = build(a.ult, a.kirby, scale_mode=a.scale)
    # check the encoded animations against the wanted path
    worst = 0.0
    for n, o in anims.items():
        o2 = omo.Omo(o.encode())
        for g, m in enumerate(path['spells']['0x%x' % n]['lhaven_world']):
            worst = max(worst, float(np.abs(fk_lhaven(o2, sk, g) - np.array(m))[:3].max()))
    assert worst < 0.05, 'the encoded LHaveN is %.3f off' % worst
    mdir = os.path.join(a.out, 'motion/body')
    os.makedirs(mdir, exist_ok=True)
    entries = [e for e in omo.pac_read(os.path.join(a.kirby, 'motion/body/main.pac'))
               if not e[0].startswith(NAME.split('%')[0])]
    entries += [(NAME % (n - 0x11 + 17) + '.omo', o.encode()) for n, o in sorted(anims.items())]
    entries.sort(key=lambda e: e[0])
    omo.pac_write(os.path.join(mdir, 'main.pac'), entries)
    words = {}
    flags = None
    if a.rpx:
        import rpx_patch
        d, _s, _e, secs = rpx_patch.load(a.rpx)
        flags = rpx_patch.read_u32(d, secs, MAIN_TABLE + 8 * POSE_SLOT + 4)
        for n in SLOT:
            for k in (0, 4):
                v = rpx_patch.read_u32(d, secs, MAIN_TABLE + 8 * SLOT[n] + k)
                assert v in (0, anim_hash(NAME % (n - 0x11 + 17)), flags), 'motion 0x%X is in use' % SLOT[n]
    for n in sorted(SLOT):
        words[MAIN_TABLE + 8 * SLOT[n]] = anim_hash(NAME % (n - 0x11 + 17))
        words[MAIN_TABLE + 8 * SLOT[n] + 4] = flags if flags is not None else 4
    open(os.path.join(a.out, 'rpx_args.txt'), 'w').write(' '.join('0x%08X=0x%08X' % kv for kv in sorted(words.items()))
                                                          + '\n')
    path['table'] = {'0x%08X' % k: '0x%08X' % v for k, v in sorted(words.items())}
    json.dump(path, open(os.path.join(a.out, 'path.json'), 'w'), separators=(',', ':'))
    print('scale %.4f (stone %.2f / Hero %.2f); animations %s; encoded within %.4f' % (
        path['scale'], path['stone_top'], path['hero_top'],
        ', '.join('%s %d frames' % (NAME % (n - 0x11 + 17), o.frames) for n, o in sorted(anims.items())), worst))
    if a.preview:
        print('\n'.join(preview(path, a.preview)))


if __name__ == '__main__':
    main()
