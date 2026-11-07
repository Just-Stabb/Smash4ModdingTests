#!/usr/bin/env python3
"""Sephiroth's counter shape (Scintilla, fighters/edge/specials.md): a group-1 shield capsule for his
fighter kind (0x42, extra_kinds.json "edge"), which runs on Zelda's native code, and the two
specializer hooks that report a hit on it to his MSC. Prints rpx_patch.py arguments.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx ... $(python3 tools/edge_counter_cave.py)

(after kind_expand.py / weapon_expand.py: tools/edge_specials_build.py --rpx applies all three.)
Research: docs/native-notes.md "Sephiroth's counter shape"; the MSC side's interface:
$S/edgenro/counter_interface.md (also in the notes).

A Smash 4 counter is a shield shape: group 1 of the fighter's kind-2 ShieldModule ([acc + 0x72F4]),
built by the kind's own setup (Marth 0x02F1E468, Link 0x02F0769C); a hit on it reaches the kind's
specializer slot 42 (+0x15C, from the shield-hit event 0x02E35794) and a body hit slot 43 (+0x164,
from the damage event 0x02E35EE4: 0 skips the damage and the reaction). Zelda's kind (vtable
0x10147F34) has no group 1 and empty slots 42 / 43, so this adds them, for kind 0x42 only (the
fighter's kind, [fighter + 4]: Zelda and everyone else run the game's code as before):

1. Setup: Zelda's specializer slot 0 (0x02F97824, `mflr r0`) branches to SETUP, which for kind 0x42
   builds group 1 with the ShieldModule's group init 0x0200C858(M, &desc, 1) (what Marth's setup does
   inline) from a constant desc {&shape, 1 shape, bytes 0, 0, 0, 1 (Marth's)} and shape {x1, y1, z1,
   x2, y2, z2, radius, bone (u16), 2 (u8: a capsule)}, switches it off (0x0200BD8C(M, 0, 0, 1), as
   Zelda's setup does with her reflector), then does `mflr r0` and goes on at 0x02F97828.
   The shape: Ultimate's vl special_lw_shield_data (joint virtualflashshield, offset1 (0, 2, 8.3),
   offset2 (0, 20, 8.3), size 6.0) on joint 0 (top): x sideways, y up, z forward, in the joint's own
   frame (the shape is placed with the joint's world matrix, 0x02C14634, so it turns with him).
2. Slot 42 (0x02F982F8, `blr`): SLOT42. For kind 0x42, a hit on group 1 (message +0x14 == 1) in status
   STATUS (0x155, his down-special stance) before the first hit was taken (status flag 0x21000010
   off), and an attack that can be countered (hit data +0x54 == 0, as Marth's): status float 0x01000006
   = the hit's damage (message +0xC), 0x01000007 = the side (Marth's: 0x02C22684, or +-1.0 from the
   positions for hit data +0x4F == 6), flag 0x21000010 on, and flag 0x21000011 on when the attacker is
   not a fighter (the collision record's +0x1C, its AttackModule owner's category id >> 28: 0 fighter,
   1 weapon, 2 item, 3 stage). No attacker freeze, no hitstop (his MSC does those).
3. Slot 43 (0x02F982FC, `li r3, 1`): SLOT43. For kind 0x42 in STATUS with flag 0x21000010 on: message
   +8 |= 1 and return 0 (no damage, no knockback: Marth's), without queueing a status (his MSC changes
   status itself); otherwise return 1 (Zelda's stub).

4. Zelda's specializer +0x13C (0x02F979EC), an article's event: for her Phantom (kind 0x26) it kills the Phantom's
   alarm on her hand (PtcZeldaPhantomAlarm 0x3100021, endless, played by the Phantom's article-list extra 0x02F97F0C on
   bone 0x11, handle at int-array +0x20C) and its sound (+0x210). Its kind compare (PHANTOM_HOOK, `cmpwi r3, 0x26`)
   branches to PHANTOM, which also takes his own Phantom kind (extra_kinds.json "phantom", 0x19B since test 111):
   without it the purple glow stayed at his hand after every Phantom release (multi-instance bugs v2, user's clip).

Space: 0x04B9D000-0x04B9E000 (grown .text: trail_table_cave.py's unused tail, its LIMIT lowered to
0x04B9D000; copy_custom_cave.py's spawners from 0x04B9E000). Calls go through ctr (the game's code is
out of `bl` reach from here). The hooks' original words are checked against --rpx when it is given.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

CAVE = 0x04B9D000
LIMIT = 0x04B9E000               # copy_custom_cave.py's spawners from here
SPEC = os.path.join(HERE, 'extra_kinds.json')
NAME = 'edge'

# the hooks: address -> the game's word there (Zelda's specializer, vtable 0x10147F34)
SETUP_HOOK = 0x02F97824          # slot 0 (entry 0x10147F40): mflr r0
SLOT42_HOOK = 0x02F982F8         # slot 42 (entry 0x10148090): blr
SLOT43_HOOK = 0x02F982FC         # slot 43 (entry 0x10148098): li r3, 1
# Zelda's specializer +0x13C (0x02F979EC: an article event, message +8 == 4, its object +0x10): for her Phantom (a
# weapon, kind 0x26) it kills the Phantom's alarm on her hand (PtcZeldaPhantomAlarm 0x3100021, endless emitters,
# played on bone 0x11 by the Phantom's article-list extra 0x02F97F0C, its handle in the specializer's +0x20C) and its
# sound (+0x210). Sephiroth's Phantom is his own kind (extra_kinds.json "phantom", test 111): that compare failed and
# the purple glow stayed at his hand after every release (multi-instance bugs v1 / v2, user's clip)
PHANTOM_HOOK = 0x02F97A40        # cmpwi r3, 0x26 (after 0x02BEF604, the object's kind; bne 0x02F97AD4 follows)
ZELDA_PHANTOM = 0x26
ORIGINAL = {SETUP_HOOK: 0x7C0802A6, SLOT42_HOOK: 0x4E800020, SLOT43_HOOK: 0x38600001, PHANTOM_HOOK: 0x2C030026}

# game functions
GROUP_INIT = 0x0200C858          # ShieldModule: (M, desc, group) -> builds the group's shapes
GROUP_STATE = 0x0200BD8C         # ShieldModule vt +0x6C: (M, shape, on, group)
SIDE = 0x02C22684                # (module [acc+0x7290], attacker AM, hit data, id, part, f1, f2) -> f1
HANDLE = 0x02BF2108              # (manager [0x102F6C30], &handle, object id, 0)
HANDLE_GONE = 0x02BEF50C         # (&handle) -> 0 while the object exists
HANDLE_POS = 0x02BEF640          # (&handle) -> its position (x at +0)
OBJ_MANAGER = 0x102F6C30

# the fighter / its modules
ACC = 0x28                       # fighter -> module accessor
KIND_AT = 4                      # fighter -> its kind
SHIELD = 0x72F4                  # accessor -> kind-2 ShieldModule (guard = group 0)
STATUS_MOD = 0x7264              # accessor -> StatusModule (+0x48 the status kind)
WORK = 0x726C                    # accessor -> WorkModule ([+8] categories, [1] = status work)
POSTURE = 0x72E4                 # accessor -> PostureModule (+0x10 x)
SIDE_MOD = 0x7290                # accessor -> the module 0x02C22684 takes (Marth's)

GROUP = 1
STATUS = 0x155                   # Zelda's down-special stance = Sephiroth's Scintilla stance
# status work: float 6 (0x01000006) damage, 7 (0x01000007) side; flag word 0: 0x21000010 = bit 16
# (oris 1), 0x21000011 = bit 17 (oris 2)
F_DAMAGE, F_SIDE = 6, 7

# Ultimate's special_lw_shield_data (vl.prc; spec_down_special.md 2.1), on joint 0 here
SHAPE = {'bone': 0, 'p1': (0.0, 2.0, 8.3), 'p2': (0.0, 20.0, 8.3), 'radius': 6.0}
SHAPE_TYPE = 2                   # byte +0x1E: capsule (0x02C14634: both ends used)
DESC_BYTES = (0, 0, 0, 1)        # desc +8..+0xB = group +0x28, +0x29, +0x2A, +0x2C (Marth's counter)


def kind(spec=SPEC, name=NAME):
    for k in json.load(open(spec))['kinds']:
        if k['name'] == name:
            assert k['base'] == 'zelda', 'the cave hooks Zelda\'s specializer: %s has base %s' % (name, k['base'])
            return int(k['kind'], 0)
    raise SystemExit('no kind %r in %s' % (name, spec))


def hilo(v):
    return v >> 16, v & 0xFFFF


def phantom_kind(spec=SPEC, name=NAME):
    """his own Phantom weapon kind (extra_kinds.json "weapons" "phantom")"""
    for k in json.load(open(spec))['kinds']:
        if k['name'] == name:
            w = k.get('weapons', {}).get('phantom')
            return int(w['kind'] if isinstance(w, dict) else w, 0)
    raise SystemExit('no phantom weapon in %s' % name)


def build(kind_id=None, phantom=None):
    """(words, labels): the cave from CAVE"""
    if kind_id is None:
        kind_id = kind()
    if phantom is None:
        phantom = phantom_kind()
    a = Asm(CAVE)
    calls = {}
    for n, v in (('init', GROUP_INIT), ('state', GROUP_STATE), ('side', SIDE), ('handle', HANDLE),
                 ('gone', HANDLE_GONE), ('pos', HANDLE_POS)):
        calls[n + '_hi'], calls[n + '_lo'] = hilo(v)
    p = dict(kind=kind_id, acc=ACC, kind_at=KIND_AT, shield=SHIELD, st=STATUS_MOD, work=WORK,
             posture=POSTURE, sidemod=SIDE_MOD, group=GROUP, status=STATUS, back=SETUP_HOOK + 4,
             fdmg=4 * F_DAMAGE, fside=4 * F_SIDE, mgr_hi=(OBJ_MANAGER + 0x8000) >> 16,
             mgr_lo=OBJ_MANAGER & 0xFFFF, **calls)
    if p['mgr_lo'] >= 0x8000:
        p['mgr_lo'] -= 0x10000
    a.asm("""
setup:  lwz r12, %(kind_at)d(r4)        # the fighter's kind
        cmpwi r12, %(kind)d
        bne setup_tail
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        stw r3, 0x8(r1)                 # the slot's arguments, for Zelda's code after
        stw r4, 0xC(r1)
        stw r5, 0x10(r1)
        lwz r12, %(acc)d(r4)
        lwz r31, %(shield)d(r12)        # M: the kind-2 ShieldModule
        cmpwi r31, 0
        beq setup_done
        mr r3, r31                      # 0x0200C858(M, &desc, 1)
        lis r4, desc@ha
        addi r4, r4, desc@l
        li r5, %(group)d
        lis r12, %(init_hi)d
        ori r12, r12, %(init_lo)d
        mtctr r12
        bctrl
        mr r3, r31                      # 0x0200BD8C(M, 0, 0, 1): its shape off
        li r4, 0
        li r5, 0
        li r6, %(group)d
        lis r12, %(state_hi)d
        ori r12, r12, %(state_lo)d
        mtctr r12
        bctrl
setup_done:
        lwz r3, 0x8(r1)
        lwz r4, 0xC(r1)
        lwz r5, 0x10(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
setup_tail:
        mflr r0                         # the replaced instruction
        b 0x%(back)08X

slot42: lwz r12, %(kind_at)d(r4)        # (spec, fighter, message)
        cmpwi r12, %(kind)d
        bnelr
        lwz r12, 0x14(r5)               # the shield group hit
        cmpwi r12, %(group)d
        bnelr
        lwz r12, %(acc)d(r4)
        lwz r11, %(st)d(r12)
        lwz r11, 0x48(r11)              # status kind
        cmpwi r11, %(status)d
        bnelr
        lwz r11, %(work)d(r12)
        lwz r11, 8(r11)
        lwz r11, 4(r11)                 # status work
        lwz r10, 0x14(r11)
        lwz r10, 0(r10)
        rlwinm. r10, r10, 0, 15, 15     # 0x21000010: a hit was taken already
        bnelr
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r27, 0x2C(r1)
        mr r31, r12                     # accessor
        mr r30, r5                      # message
        mr r29, r11                     # status work
        lwz r28, 0x10(r5)               # the collision record
        lwz r3, 8(r5)                   # the attacker's AttackModule: vt +0x194(id, part) = hit data
        lwz r12, 0(r3)
        lwz r12, 0x194(r12)
        lbz r4, 0x26(r28)
        lbz r5, 0x29(r28)
        mtctr r12
        bctrl
        mr r27, r3
        lbz r0, 0x54(r27)               # can't be countered
        cmpwi r0, 0
        bne out42
        lwz r3, %(sidemod)d(r31)        # the side (Marth's)
        lwz r4, 8(r30)
        mr r5, r27
        lbz r6, 0x26(r28)
        lbz r7, 0x29(r28)
        lfs f1, 0x18(r30)
        lfs f2, 0x1C(r30)
        lis r12, %(side_hi)d
        ori r12, r12, %(side_lo)d
        mtctr r12
        bctrl
        stfs f1, 0x10(r1)
        lbz r0, 0x4F(r27)
        cmpwi r0, 6
        bne store
        lis r3, %(mgr_hi)d              # hit data +0x4F == 6: from the positions (Marth's)
        lwz r3, %(mgr_lo)d(r3)
        addi r4, r1, 8
        lwz r5, 0x18(r28)               # the attacker's object id
        li r6, 0
        lis r12, %(handle_hi)d
        ori r12, r12, %(handle_lo)d
        mtctr r12
        bctrl
        addi r3, r1, 8
        lis r12, %(gone_hi)d
        ori r12, r12, %(gone_lo)d
        mtctr r12
        bctrl
        cmpwi r3, 0
        bne store
        addi r3, r1, 8
        lis r12, %(pos_hi)d
        ori r12, r12, %(pos_lo)d
        mtctr r12
        bctrl
        lfs f0, 0(r3)                   # the attacker's x
        lwz r12, %(posture)d(r31)
        lfs f13, 0x10(r12)              # his x
        lis r12, one@ha
        lfs f1, one@l(r12)
        fcmpu cr0, f13, f0
        blt side_set                    # he is left of it: +1.0
        fneg f1, f1
side_set:
        stfs f1, 0x10(r1)
store:  lwz r11, 4(r29)                 # status floats
        lfs f0, 0xC(r30)
        stfs f0, %(fdmg)d(r11)          # 0x01000006 = the damage
        lfs f0, 0x10(r1)
        stfs f0, %(fside)d(r11)         # 0x01000007 = the side
        lwz r11, 0x14(r29)
        lwz r0, 0(r11)
        oris r0, r0, 1                  # 0x21000010
        lbz r12, 0x1C(r28)              # the attacker's category (id >> 28): 0 = fighter
        cmpwi r12, 0
        beq flags
        oris r0, r0, 2                  # 0x21000011: not a fighter
flags:  stw r0, 0(r11)
out42:  lmw r27, 0x2C(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

slot43: li r3, 1                        # (spec, fighter, message) -> 0: no damage / reaction
        lwz r12, %(kind_at)d(r4)
        cmpwi r12, %(kind)d
        bnelr
        lwz r12, %(acc)d(r4)
        lwz r11, %(st)d(r12)
        lwz r11, 0x48(r11)
        cmpwi r11, %(status)d
        bnelr
        lwz r11, %(work)d(r12)
        lwz r11, 8(r11)
        lwz r11, 4(r11)
        lwz r11, 0x14(r11)
        lwz r11, 0(r11)
        rlwinm. r11, r11, 0, 15, 15     # 0x21000010
        beqlr
        lbz r0, 8(r5)                   # the message's handled bit (Marth's, and the damage path's)
        ori r0, r0, 1
        stb r0, 8(r5)
        li r3, 0
        blr

phantom: cmpwi r3, %(zph)d               # Zelda's Phantom (the replaced compare)
        beq phantom_back
        cmpwi r3, %(eph)d               # or his: the same eq for 0x02F97A44's bne
phantom_back:
        b 0x%(phback)08X

""" % dict(p, zph=ZELDA_PHANTOM, eph=phantom, phback=PHANTOM_HOOK + 4))
    shape_at = a.pc + 4
    a.asm("""
one:    .float 1.0
shape:  .float %(x1)r
        .float %(y1)r
        .float %(z1)r
        .float %(x2)r
        .float %(y2)r
        .float %(z2)r
        .float %(radius)r
        .word 0x%(bonetype)08X
desc:   .word 0x%(shape_at)08X
        .word 1
        .word 0x%(descbytes)08X
""" % dict(x1=SHAPE['p1'][0], y1=SHAPE['p1'][1], z1=SHAPE['p1'][2], x2=SHAPE['p2'][0], y2=SHAPE['p2'][1],
           z2=SHAPE['p2'][2], radius=SHAPE['radius'], bonetype=(SHAPE['bone'] << 16) | (SHAPE_TYPE << 8),
           shape_at=shape_at, descbytes=int.from_bytes(bytes(DESC_BYTES), 'big')))
    assert a.labels['shape'] == shape_at
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, 'cave too long'
    return words, dict(a.labels)



def branch(src, dst):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0, (hex(src), hex(dst))
    return (18 << 26) | (off & 0x3FFFFFC)


def patches(kind_id=None):
    """{address: word}: the cave and the three hooks"""
    words, labels = build(kind_id)
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    for hook, label in ((SETUP_HOOK, 'setup'), (SLOT42_HOOK, 'slot42'), (SLOT43_HOOK, 'slot43'),
                        (PHANTOM_HOOK, 'phantom')):
        out[hook] = branch(hook, labels[label])
    return out


def word_or_0(img, a):
    """a word of a kind_expand.Image, 0 past its code's end (a base whose .text isn't grown yet)"""
    try:
        return img.w(a)
    except KeyError:
        return 0


def check_base(rpx):
    """the hooks' words in the base are the game's (or this cave's own branches: re-applying)"""
    import kind_expand as K
    img = K.Image(rpx)
    p = patches()
    bad = ['0x%08X: 0x%08X' % (a, img.w(a)) for a, w in ORIGINAL.items() if img.w(a) not in (w, p[a])]
    if bad:
        raise SystemExit('edge_counter_cave: unexpected words in %s: %s' % (rpx, ', '.join(bad)))
    # an earlier build of this cave (its setup hook branching here) may hold other words: they're all rewritten
    earlier = img.w(SETUP_HOOK) == p[SETUP_HOOK]
    used = [a for a in range(CAVE, LIMIT, 4) if word_or_0(img, a) not in (0, p.get(a, 0))]
    if used and not earlier:
        raise SystemExit('edge_counter_cave: the cave space is in use in %s (0x%08X)' % (rpx, used[0]))


def args(kind_id=None):
    # grow: covers the cave over a base without the other caves' grown .text (rpx_patch.py keeps the
    # largest grow: of all, so this never shrinks theirs)
    return ['grow:0x%08X' % LIMIT] + ['0x%08X=0x%08X' % (a, w) for a, w in sorted(patches(kind_id).items())]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', help='check the hooks\' original words and the cave space in this base')
    ap.add_argument('--kinds', default=SPEC)
    a = ap.parse_args()
    if a.rpx:
        check_base(a.rpx)
    k = kind(a.kinds)
    words, labels = build(k)
    print(' '.join(args(k)))
    sys.stderr.write('edge counter: kind 0x%X, cave 0x%08X-0x%08X (%d words), hooks 0x%08X / 0x%08X / 0x%08X / 0x%08X '
                     '(his Phantom 0x%X)\n' % (k, CAVE, CAVE + 4 * len(words), len(words), SETUP_HOOK, SLOT42_HOOK,
                                               SLOT43_HOOK, PHANTOM_HOOK, phantom_kind(a.kinds)))


if __name__ == '__main__':
    main()
