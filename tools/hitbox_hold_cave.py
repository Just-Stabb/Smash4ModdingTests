#!/usr/bin/env python3
"""Hitbox_Hold (exe_v46y_hold, rapid_setoff v1): a hitbox whose hits keep the victim where it is: no knockback
travel (the launch speed is 0), while the damage, hitstun, hitlag, SDI and the reaction (flinch animation) stay the
game's. The port pipeline gives it to Ultimate's holding multi-hits (ATTACK_SETOFF_KIND_OFF + angle 361 + a small
knockback: the rapid-jab loops) with Ultimate's own angle, in place of v17's angle-80 workaround. Prints rpx_patch.py
arguments for an executable with acmd_ext_cave.py's patches (exe_v46x_whipmot and later); asserts every word.

  python3 tools/rpx_patch.py exe_v46x_whipmot.rpx exe_v46y_hold.rpx $(python3 tools/hitbox_hold_cave.py --rpx exe_v46x_whipmot.rpx)
  python3 tools/hitbox_hold_cave.py --labels tools/Sm4shCommand/param_labels.json     (Sm4shCommand's entry)

What Ultimate's setoff is (read from Ultimate's ExeFS main.bin, docs/native-notes.md "Hitbox hold"): AttackData +0x62
`set_off_` is the CLANK kind (ON 0 clanks and rebounds, OFF 1 clanks but the move goes on, THRU 2 never clanks,
NO_STOP 3 clanks with no clank hitlag): it doesn't touch the victim's knockback. Smash 4 already has that as Clang /
Rebound (ultimate_acmd.SETOFF). What holds a rapid-jab victim is the hit itself; this command is the Smash 4 setting
that gives such hits no slide.

Command: Hitbox_Hold(ID, Mode) (index HH_INDEX, CRC of the name), 3 words.
  ID   the hitbox ID (the AttackModule slot, as the hitbox command's ID; Part doesn't pick a slot in Smash 4); -1: every
       hitbox ID the object has.
  Mode 0 off; 1 ground: a victim on the ground whose launch has no upward part (361 under 60 knockback: 0 degrees;
       0 / 180; downward) isn't moved; launches upward, and victims in the air, go as normal; 2 always: no victim is
       moved (ground or air; gravity still acts in the air). Other values: 0.
The mark lives in the hitbox's own data (+0x66, the halfword acmd_ext's Extra tag uses; no game code reads it):
  - a plain hitbox (tag 0 after acmd_ext's slot_set): 0xED00 | Mode (acmd_ext reads only 0xECxx as an Extra tag);
  - an Extra hitbox (tag 0xEC00 | n, acmd_ext's extras entry n): HH_EXT[n] = {slot, Mode}, valid while acmd_ext's
    entry n is still that slot's and the hit's data matches it (its check words, as acmd_ext's find_copy).
  Every new hitbox in the slot drops it: acmd_ext's slot_set zeroes the tag; HH_SLOTSET (chained before it) clears the
  HH_EXT entries of that slot. So the mark goes with the hitbox (removed, replaced: gone).

Hooks (each word asserted):
  VEC     0x02C25BF4  lwz r8, 0xc(r1)      the victim handler (0x02C25318) storing the launch vector (its stack
                                           0xC / 0x10: knockback x 0.03 along the angle, after the reaction kind and
                                           the bounce were decided) into the damage event's +0xC / +0x10, which the
                                           fighter's event handler (0x02E7A4DC) gives its damage energy -> hh_vec
  SLOTSET 0x02C0874C  b slot_set (acmd_ext) AttackModule set_attack, after the data copy -> hh_slotset -> slot_set
  LOOKUP / SIZE1 / SIZE2 / FETCH: as tools/line_test_cave.py (chained in front of the earlier caves' fallbacks).
Space: 0x04BD7000-0x04BD8000 (docs/native-notes.md: the free half of the gap before var_reset's region).
Test: tools/hitbox_hold_test.py (unicorn).
"""
import argparse
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402
import acmd_ext_cave as C  # noqa: E402
import line_test_cave as LT  # noqa: E402

CAVE, LIMIT = 0x04BD7000, 0x04BD8000
VEC_AT = 0x02C25BF4
VEC_WORDS = (0x8101000C, 0x81610010, 0x911E000C, 0x917E0010)   # lwz r8 / r11 from 0xC / 0x10(r1); stw to r30
SLOTSET_AT = C.SLOT_SET                                        # 0x02C0874C: acmd_ext's `b slot_set`
SLOTSET_HEAD = (0x38000000, 0xB01A0000 | C.TAG_OFF)            # slot_set: li r0, 0; sth r0, 0x66(r26)
HH_INDEX = 2100                 # Hitbox_Hold's command index (acmd_ext 584 + k, Line_Test 1096, Var_Reset_Set 2000)
CMD_NAME = 'Hitbox_Hold'
CMD_CRC = zlib.crc32(CMD_NAME.encode()) & 0xFFFFFFFF
PLAIN_TAG = 0xED00
MODES = (0, 1, 2)

NEW_CMDS = [
    (CMD_NAME, 'h_hold', [
        ('ID', 0, 'The hitbox ID to mark (the ID of the Hitbox / Special_Hitbox / Extra_... command that made it, '
                  'issued before this one). -1: every hitbox ID of this object.'),
        ('Mode', 0, '0: off (the game\'s knockback travel). 1: ground hold: a victim on the ground that the hit '
                    'doesn\'t launch upward (361 under 60 knockback, 0 / 180, downward angles) stays where it is; '
                    'upward launches and victims in the air go as normal. 2: always: no victim is moved, on the '
                    'ground or in the air (gravity still pulls an airborne one).')],
     'Marks a hitbox so its hits keep the victim in place: no knockback travel, the damage / hitstun / hitlag / SDI '
     'kept (the setting the port pipeline gives Ultimate\'s rapid-jab hits). Cleared when the hitbox is replaced. New '
     'command: needs the patched cross_f.rpx (tools/hitbox_hold_cave.py, exe_v46y_hold).'),
]


def find(orig):
    s = LT.find(orig)
    for i, w in enumerate(VEC_WORDS):
        assert orig(VEC_AT + 4 * i) == w, 'victim vector store 0x%08X: 0x%08X, not 0x%08X' % (
            VEC_AT + 4 * i, orig(VEC_AT + 4 * i), w)
    w = orig(SLOTSET_AT)
    s['slotset_to'] = LT.bdecode(SLOTSET_AT, w)
    assert not CAVE <= s['slotset_to'] < LIMIT, 'already patched (slot set hook goes into this cave)'
    assert tuple(orig(s['slotset_to'] + 4 * i) for i in range(2)) == SLOTSET_HEAD, \
        'slot set hook: 0x%08X is not acmd_ext\'s slot_set' % s['slotset_to']
    for k in ('lk_none', 's1', 's2', 'f'):
        if s[k + '_word'] >> 26 == 18:
            assert not CAVE <= LT.bdecode(s[k], s[k + '_word']) < LIMIT, 'already patched (%s)' % k
    return s


def src(s, hand):
    D = dict(base=HH_INDEX, crc=CMD_CRC, s1b=s['s1_back'], s2b=s['s2_back'], fb=s['f_back'], hand=hand,
             vec_back=VEC_AT + 8, slotset=s['slotset_to'], tag=C.TAG_OFF, TAG=C.TAG, plain=PLAIN_TAG,
             entries=C.ENTRIES, entries8=8 * C.ENTRIES, entry=C.ENTRY, table=C.TABLE)
    out = """
# --- the command tables' fallbacks --------------------------------------------------------------------------------
hh_lookup:                              # r3 = a CRC no table before has
        lis r12, %(crc_h)d
        ori r12, r12, %(crc_l)d
        cmplw r3, r12
        bne hhl_none
        li r3, %(base)d
        blr
""" % dict(D, crc_h=CMD_CRC >> 16, crc_l=CMD_CRC & 0xFFFF) + LT.replay(s['lk_none'], s['lk_none_word'], s['lk_none'] + 4,
                                                                   'hhl_none') + """
hh_size1:                               # r3 index -> r0 its size
        cmplwi r3, %(base)d
        bne hhs1_orig
        li r0, 3
        b 0x%(s1b)08X
""" % D + LT.replay(s['s1'], s['s1_word'], s['s1_back'], 'hhs1_orig') + """
hh_size2:                               # r3 index -> r12 its size
        cmplwi r3, %(base)d
        bne hhs2_orig
        li r12, 3
        b 0x%(s2b)08X
""" % D + LT.replay(s['s2'], s['s2_word'], s['s2_back'], 'hhs2_orig') + """
hh_fetch:                               # r7 index -> r0 its handler (r6 free)
        cmplwi r7, %(base)d
        bne hhf_orig
        lis r6, %(hand_h)d
        ori r0, r6, %(hand_l)d
        b 0x%(fb)08X
""" % dict(D, hand_h=hand >> 16, hand_l=hand & 0xFFFF) + ("""
hhf_orig:
        b 0x%08X
""" % LT.bdecode(s['f'], s['f_word']) if s['f_word'] >> 26 == 18 else """
hhf_orig:
        slwi r6, r7, 2
        lwzx r0, r6, r29
        b 0x%08X
""" % s['f_back']) + """
# --- Hitbox_Hold(ID, Mode): (r3 accessor, r5 script state, r6 (+8 execute), r7 parameters) -----------------------
h_hold:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stmw r28, 0x10(r1)
        mr r31, r5
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq hh_step
        bl hh_ptr
        cmpwi r0, 0
        bne hh_step
        lwz r30, 0x50(r3)               # AttackModule
        mr r3, r30
        bl hh_ptr
        cmpwi r0, 0
        bne hh_step
        lwz r29, 4(r7)                  # Mode (0 - 2, else 0)
        cmplwi r29, 2
        ble hh_m
        li r29, 0
hh_m:
        lwz r3, 0x40(r30)               # slots
        bl hh_ptr
        cmpwi r0, 0
        bne hh_step
        lwz r28, 0x3C(r30)              # count
        lwz r0, 0(r7)                   # ID
        cmpwi r0, -1
        beq hh_all
        cmplw r0, r28
        bge hh_step
        mulli r0, r0, 0x84
        add r3, r3, r0
        bl hh_mark
        b hh_count
hh_all:
        cmpwi r28, 0
        beq hh_count
        cmplwi r28, 64
        bgt hh_step
hh_alll:
        bl hh_mark
        addi r3, r3, 0x84
        addi r28, r28, -1
        cmpwi r28, 0
        bne hh_alll
hh_count:
        lis r12, hh_dbg@ha              # (addi rD, r0 reads 0: count in r11)
        lwz r11, hh_dbg@l(r12)
        addi r11, r11, 1
        stw r11, hh_dbg@l(r12)
hh_step:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne hh_ret
        lwz r11, 4(r31)
        addi r11, r11, 12
        stw r11, 4(r31)
        li r3, 2
hh_ret:
        lmw r28, 0x10(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# hh_mark(r3 slot, r29 mode): plain -> tag 0xED00 | mode (0: 0); Extra (0xEC00 | n) -> HH_EXT[n]. r0 r9-r12
hh_mark:
        lhz r9, %(tag)d(r3)
        rlwinm r10, r9, 0, 16, 23
        cmplwi r10, %(TAG)d
        beq hhm_x
        li r10, 0
        cmpwi r29, 0
        beq hhm_put
        ori r10, r29, %(plain)d
hhm_put:
        sth r10, %(tag)d(r3)
        blr
hhm_x:
        rlwinm r9, r9, 3, 21, 28        # n x 8 (n = the low byte)
        cmplwi r9, %(entries8)d
        bgelr
        lis r12, hh_ext@ha
        addi r12, r12, hh_ext@l
        add r12, r12, r9
        stw r29, 4(r12)
        li r0, 0
        cmpwi r29, 0
        beq hhm_xs
        mr r0, r3
hhm_xs:
        stw r0, 0(r12)
        blr

# hh_ptr(r3) -> r0 0 when r3 is a word-aligned pointer in 0x10000000-0x8FFFFFFF, else 1. r12
hh_ptr:
        li r0, 1
        andi. r12, r3, 3
        bnelr
        addis r12, r3, -0x1000
        srwi r12, r12, 28
        cmplwi r12, 8
        bgelr
        li r0, 0
        blr

# --- set_attack's new data in a slot (r26): drop this slot's HH_EXT marks, then acmd_ext's slot_set -------------
hh_slotset:
        li r12, %(entries)d
        mtctr r12
        lis r11, hh_ext@ha
        addi r11, r11, hh_ext@l
hhs_loop:
        lwz r0, 0(r11)
        cmplw r0, r26
        bne hhs_next
        li r0, 0
        stw r0, 0(r11)
hhs_next:
        addi r11, r11, 8
        bdnz hhs_loop
        b 0x%(slotset)08X

# --- the victim's launch vector (r28 hit info, its data copy at +0x44; r19 the victim's situation, 0 ground;
#     stack 0xC / 0x10 the vector): r8 / r11 = it, or 0 / 0 for a held hit. Free: r0 r5-r7 r9 r10 r12 ----------
hh_vec:
        lwz r8, 0xC(r1)
        lwz r11, 0x10(r1)
        addi r5, r28, 0x44
        lhz r6, %(tag)d(r5)
        rlwinm r7, r6, 0, 16, 23
        rlwinm r9, r6, 0, 24, 31
        cmplwi r7, %(plain)d
        beq hhv_mode
        cmplwi r7, %(TAG)d
        bne hhv_back
        cmplwi r9, %(entries)d
        bge hhv_back
        slwi r10, r9, 3                 # HH_EXT[n]: {slot, mode}
        lis r12, hh_ext@ha
        addi r12, r12, hh_ext@l
        add r12, r12, r10
        lwz r10, 0(r12)
        cmpwi r10, 0
        beq hhv_back
        mulli r6, r9, %(entry)d         # acmd_ext's entry n: still that slot, and this hit's hitbox
        lis r7, %(table_h)d
        ori r7, r7, %(table_l)d
        add r7, r7, r6
        lwz r0, 0(r7)
        cmplw r0, r10
        bne hhv_back
""" % dict(D, table_h=C.TABLE >> 16, table_l=C.TABLE & 0xFFFF)
    for e, d in ((4, 0x20), (8, 0x24), (0xC, 0x28), (0x10, 0x2C), (0x2C, 0x3C)):
        out += """        lwz r0, %d(r7)
        lwz r6, %d(r5)
        cmplw r0, r6
        bne hhv_back
""" % (e, d)
    out += """        lwz r9, 4(r12)
hhv_mode:
        cmpwi r9, 2
        beq hhv_hold
        cmpwi r9, 1
        bne hhv_back
        cmpwi r19, 0                    # 1: a victim on the ground, not launched upward (y bits <= 0: 0, -0, < 0)
        bne hhv_back
        cmpwi r11, 0
        bgt hhv_back
hhv_hold:
        li r8, 0
        li r11, 0
        lis r12, hh_held@ha
        lwz r10, hh_held@l(r12)
        addi r10, r10, 1
        stw r10, hh_held@l(r12)
hhv_back:
        b 0x%(vec_back)08X

hh_dbg:                                 # Hitbox_Hold runs
        .word 0
hh_held:                                # hits held
        .word 0
hh_ext:
""" % D
    return out


def build(orig):
    s = find(orig)
    hand = 0
    for _p in range(2):
        a = Asm(CAVE)
        a.asm(src(s, hand))
        hand = a.addr('h_hold')
    words = a.words()
    ext = a.addr('hh_ext')
    end = ext + 8 * C.ENTRIES
    assert end <= LIMIT, 'cave too big: 0x%08X' % end
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    for x in range(CAVE, LIMIT, 4):
        assert orig(x) == 0, 'cave word 0x%08X not free' % x
    out[s['lk_none']] = LT.branch(s['lk_none'], a.addr('hh_lookup'))
    out[s['s1']] = LT.branch(s['s1'], a.addr('hh_size1'))
    out[s['s2']] = LT.branch(s['s2'], a.addr('hh_size2'))
    out[s['f']] = LT.branch(s['f'], a.addr('hh_fetch'))
    out[SLOTSET_AT] = LT.branch(SLOTSET_AT, a.addr('hh_slotset'))
    out[VEC_AT] = LT.branch(VEC_AT, a.addr('hh_vec'))
    return out, a.labels, s


def labels(path):
    """Hitbox_Hold's entry in tools/Sm4shCommand/param_labels.json (apply_param_labels.py then puts it in Events.cfg and
    tools/acmd_info.json; its group, help and examples come from acmd_ext_help.py)"""
    import json
    from acmd_ext_help import GROUP, HELP, EXAMPLES
    d = json.load(open(path))
    for name, _h, params, desc in NEW_CMDS:
        e = {'_command': name, '_new': True, '_name': name, '_size': 1 + len(params), '_desc': desc,
             '_format': [t for _n, t, _d in params]}
        for k, (pname, _t, pdesc) in enumerate(params):
            e[str(k)] = {'name': pname, 'desc': pdesc, 'confidence': 'high'}
        e['_example'] = EXAMPLES.get(name, [])
        e['_group'], e['_help'] = GROUP.get(name), HELP.get(name, [])
        d['%08X' % LT.crc(name)] = e
    json.dump(dict(sorted(d.items())), open(path, 'w'), indent=1)


def present(img_w):
    """the executable has this cave (Hitbox_Hold's CRC in hh_lookup) - for port_check X8"""
    hi, lo = 0x3D800000 | (CMD_CRC >> 16), 0x618C0000 | (CMD_CRC & 0xFFFF)
    try:
        return any(img_w(x) == hi and img_w(x + 4) == lo for x in range(CAVE, CAVE + 0x40, 4))
    except Exception:              # noqa: BLE001
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', help='the executable to patch (acmd_ext_cave.py applied: exe_v46x_whipmot or later)')
    p.add_argument('--labels', help='update this param_labels.json with Hitbox_Hold')
    args = p.parse_args()
    if args.labels:
        labels(args.labels)
        return
    import kind_expand as K
    img = K.Image(args.rpx)
    words, lab, s = build(img.w)
    print(' '.join('0x%08X=0x%08X' % kv for kv in sorted(words.items())))
    sys.stderr.write('hitbox hold: %d words, Hitbox_Hold index %d (0x%08X), h_hold 0x%08X, hh_ext 0x%08X\n' % (
        len(words), HH_INDEX, CMD_CRC, lab['h_hold'], lab['hh_ext']))


if __name__ == '__main__':
    main()
