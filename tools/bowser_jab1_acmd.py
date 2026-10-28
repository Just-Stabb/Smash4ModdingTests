#!/usr/bin/env python3
"""Bowser's Jab 1 (Attack11) on the user's BUNDYA11 animation: nail hitboxes, a tipper, a pull-in.

  python3 tools/bowser_jab1_acmd.py BUNDYA11.fbx MODEL.vbn IN_game.bin OUT_game.bin

Only Attack11 is replaced; every other script of IN_game.bin is kept (build on the fighter's
current game.bin, not vanilla's: v3 was built on vanilla and lost the roll-off and the user's own
edits). The animation's LIndex3N stretches the finger's nail out (X scale 1 -> 28.5 -> 1 over
frames 7-39); LIndex3N isn't a joint, so every hitbox is on LHandN (joint 0x11), placed each frame
from that frame's pose (docs/fbx-animations.md).

Offsets are in LHandN's space without its scale (1.32 here): the game, like Smash Forge, doesn't
scale a hitbox's offset by its bone. Sizes are world sizes (the nail's radius x its scale).

- Frames 7-39: ID 0 finger (LIndex1N -> LIndex3N), ID 1 nail (LIndex3N -> tip), both 3% weak
  `Extra_Extended_Special_Hitbox`es (angle 180 toward Bowser, KBG 100 / FKB 50, 1.4x hitstun).
- Frames TIP_FIRST-TIP_LAST: ID 2 tipper, a sphere at the nail's tip (8%, angle 40, KBG 80, BKB
  105); the nail capsule then stops 2 radii short of the tip so the tipper isn't under it (a lower
  ID wins where they overlap). At frame 7 the nail is still unstretched (tip 38 in front, at the
  finger); at 14-18 it's 128-139 in front.
- The pull (frames 7-68, every frame): on the first frame the last fighter hit is in hitstun
  (`0x0F000050` > 0), it's sorted by that hitstun: above TIPPER_HITSTUN (the tipper gives at least
  47, the weak hit at most about 36 with the 1.4x) it was the tipper and is left alone. Otherwise,
  while still in hitstun, it's moved STEP closer each frame (`SUB_FLOAT_2` on its forward offset
  `0x0F000055`, whose write keeps its Y / Z), held at FRONT in front, and kept in hitstun (6 left)
  until it gets there.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402
import fbx_anim as A  # noqa: E402
import omo as O  # noqa: E402

NAIL_X = 2.894992863092476      # the nail's mesh along LIndex3N's X (FBX skin clusters, game axes)
NAIL_R = 1.1863626733418167     # its radius
FINGER_R = 1.18
LHAND = 0x11
FIRST, LAST, END = 7, 39, 68
TIP_FIRST, TIP_LAST = 14, 18
STEP, FRONT, TIPPER_HITSTUN = 3.5, 15.0, 40.0
LAST_HITSTUN, LAST_FWD = 0x0F000050, 0x0F000055
STEP_VAR, KIND, SEEN = 0x0F000300, 0x0F000302, 0x0F000303    # VAR_0, VAR_2 (1 = tipper), VAR_3

B = acmd.BY_NAME
HIT = [0, 0, LHAND, 3.0, 180, 100, 50, 0, 0.0, 0, 0, 0, 0, 0.0, 1.0, 1.0, 1, 1, 0, 0, 1, 3, 1, 4]
EXTRA = [0x3F, 0, 0xF, 0, 1, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0]          # HitBits .. Flinchless


def C(name, *p):
    return acmd.Command(B[name.lower()], list(p))


def cmp(var, method, value, body):
    """Float_Var_Compare + True over body (methods: 0 ==, 1 !=, 2 <=, 3 >=, 4 <, 5 >)"""
    words = sum(acmd.INFO[c.ident]["size"] for c in body)
    return [C("Float_Var_Compare", var, method, float(value)), C("True", 2 + words)] + body


def r3(v):
    return [round(float(x), 3) for x in v]


def weak(id_, r, p1, p2):
    q = list(HIT)
    q[0], q[8], q[9:12] = id_, round(float(r), 3), r3(p1)
    return acmd.Command(B["extra_extended_special_hitbox"], q + EXTRA + r3(p2) + [1.4, 0.0, 0, 0.0, 0, 0.0])


def tipper(r, p):
    q = [2, 0, LHAND, 8.0, 40, 80, 0, 105, round(float(r), 3)] + r3(p) + [0, 0.0, 1.0, 1.0, 1, 1, 0, 2, 1, 3, 1, 4]
    return acmd.Command(B["special_hitbox"], q + EXTRA + [0])


def pull():
    first = [C("SET_FLOAT", 1.0, SEEN), C("SET_FLOAT", 0.0, KIND)] + cmp(LAST_HITSTUN, 5, TIPPER_HITSTUN, [C("SET_FLOAT", 1.0, KIND)])
    move = ([C("SUB_FLOAT_2", LAST_FWD, STEP_VAR)]
            + cmp(LAST_FWD, 4, FRONT, [C("SET_FLOAT", FRONT, LAST_FWD)])
            + cmp(LAST_FWD, 5, FRONT + 0.01, [C("SET_FLOAT", 6.0, LAST_HITSTUN)]))
    return cmp(LAST_HITSTUN, 5, 0.0, cmp(SEEN, 0, 0.0, first) + cmp(KIND, 0, 0.0, move))


def attack11(fbx, vbn):
    vb = O.vbn_read(vbn)
    bones, _n = A.load(fbx)

    def world(f):
        L = A.game_locals(bones, f)
        W = {}
        for nm, p, _h in vb:
            W[nm] = (W[vb[p][0]] if 0 <= p < len(vb) else np.eye(4)) @ L[nm]
        return W

    out = [C("SET_FLOAT", STEP, STEP_VAR), C("SET_FLOAT", 0.0, SEEN), C("SET_FLOAT", 0.0, KIND)]
    tips = {}
    for f in range(FIRST, END + 1):
        out.append(C("frame", float(f)))
        if f <= LAST:
            W = world(f)
            # the game places a hitbox with its bone's rotation and position only, not its scale
            # (LHandN's is 1.32 here; v2 / v3 divided by it and fell 1.32x short of the tip)
            hand = W["LHandN"].copy()
            hand[:3, :3] /= np.linalg.norm(hand[:3, :3], axis=0)
            inv = np.linalg.inv(hand)

            def loc(m, p):
                return (inv @ m @ np.append(p, 1))[:3]
            base = loc(W["LIndex1N"], [0, 0, 0])
            joint = loc(W["LIndex3N"], [0, 0, 0])
            tip = loc(W["LIndex3N"], [NAIL_X, 0, 0])
            sc = np.linalg.norm(W["LIndex3N"][:3, :3], axis=0)
            r = NAIL_R * min(sc[1], sc[2])
            rf = FINGER_R * np.linalg.norm(W["LIndex1N"][:3, :3], axis=0)[1:].min()
            on = TIP_FIRST <= f <= TIP_LAST
            end = tip
            if on:
                d = tip - joint
                L = np.linalg.norm(d)
                end = joint + d / L * max(0.0, L - 2 * r)
                tips[f] = (W["LIndex3N"] @ np.array([NAIL_X, 0, 0, 1]))[:3]
            if f == FIRST:
                out.append(C("Set_Bone_Intangibility", 0x10, 2))
            if f == TIP_LAST + 1:
                out.append(C("Remove_Hitbox", 2))          # the tipper off; IDs 0 / 1 stay (their hit list too)
            out += [weak(0, rf, base, joint), weak(1, r, joint, end)]
            if on:
                out.append(tipper(r, tip))
        if f == LAST + 1:
            out += [C("Remove_All_Hitboxes"), C("Undo_Bone_Collision", 0), C("ON_FLAG", 0x2100000D)]
        out += pull()
    out.append(acmd.Command(acmd.END))
    return out, tips


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    fbx, vbn, src, dst = sys.argv[1:]
    s, tips = attack11(fbx, vbn)
    g = acmd.ACMDFile.load(src)
    g.scripts[acmd.crc("Attack11")] = s
    g.save(dst)
    for f, p in sorted(tips.items()):
        print("frame %d: tipper at %.1f forward, %.1f up" % (f, p[2], p[1]))
    print("Attack11: %d commands" % len(s))


if __name__ == "__main__":
    main()
