#!/usr/bin/env python3
"""Stage line test (Byleth v9): a ray from one point to another against the stage's collision lines, for any object,
from ACMD (a new command, `Line_Test`) and from MSC / ACMD variables (`LINE_*`, 0x0F0003D0-0x0F0003DA). Prints
rpx_patch.py arguments for an executable that already has tools/acmd_ext_cave.py's patches (exe_v46v_threads and
later); it asserts every word it replaces.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/line_test_cave.py --rpx IN.rpx)
  python3 tools/line_test_cave.py --labels tools/Sm4shCommand/param_labels.json     (Sm4shCommand's entry)

The game's own test: GroundModule (accessor +0x2C) ray_check with a normal, 0x02C39FB4(GM, V2 *from, V2 *dir,
V2 *out, V2 *normal, bool all): the first stage line the segment from -> from + dir meets (0x02D4CD68 for every line,
0x02D4E724 with the mask 0x102000 when `all` is 0: the passable platforms left out), the point in *out, the line's
normal in *normal, r3 1 on a hit. It is the one the game's ledge / ground checks use (six GroundModule vtables, the
3DS's GroundModuleImpl::ray_check; docs/smash-run-port.md "get_height_from_ground").

What a test gives (docs/acmd-extra-commands.md "Line_Test"): whether it hit, the distance from the start to the hit
(the whole length when nothing is hit), the point (the end when nothing is hit), the line's kind from its normal
(1 floor: normal y >= 0.6, 3 ceiling: <= -0.6, 2 wall otherwise; 0 nothing hit) and the normal. Space 0: the points
are relative to the object (X forward along its facing, Y up, from its position; the results come back the same
way, the normal's X along the facing); space 1: world coordinates.

Hooks (each asserted: the word is the one acmd_ext_cave.py wrote, or a `b` some later cave put there, which this one
then chains to):
- acmd_ext_cave.py's `lk_none` (its command search's not-found `li r3, -1`): our CRCs -> indices LT_BASE + i.
- its size1 / size2 / fetch fallbacks (`s1_orig` / `s2_orig` / `f_orig`, the game's own table reads): our indices read
  our sizes / handlers.
- its hv_var's `hvv_zero` (`b buf_var`: user_entry IDs nothing else answers): 0x3D0-0x3DA are ours.
Space: code + data 0x04BCA000-0x04BCB800 (zero in exe_v46v; docs/native-notes.md "Stage line test").
"""
import argparse
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

CAVE = 0x04BCA000
LIMIT = 0x04BCB800
RAY_N = 0x02C39FB4                  # GroundModule ray_check(GM, from, dir, out, normal, all) -> r3 hit
RAY_N_HEAD = (0x7C0802A6, 0x9421FFE0, 0x93E1001C, 0x7CFF3B78)
POSTURE_FW = 0x030B2AF0             # MSC PostureModuleF wrapper (ctx +4 accessor, {args, count}): 0 lr, 1 x, 2 y
POSTURE_FW_HEAD = (0x7C0802A6, 0x90010004, 0x9421FFF0, 0x81830004, 0x806C0018)
LOOKUP_HOOK = 0x02BEE1BC            # the game's not-found `li r3, -1`, a `b lookup` into acmd_ext_cave.py's cave
SIZE1, SIZE2, FETCH = 0x02BEE2C0, 0x02BEE3C0, 0x02BEE84C
ACMD_NEW_BASE = 584                 # acmd_ext_cave.py's first index
LT_BASE = ACMD_NEW_BASE + 0x200     # ours (acmd_ext_cave.py's ~70 commands sit far below)
VAR_LO, VAR_HI = 0x3D0, 0x3DA       # user_entry indices (0x0F0003D0-0x0F0003DA)
HV_VAR_SIG = (0x281E03C0, None, 0x281E03C8, None)       # hv_var: cmplwi r30, 0x3C0; blt; cmplwi r30, 0x3C8; bgt
UE_OUT_SIG = (0x2C1D0000, 0x41820008, 0xC0210018, 0xBB61001C, 0x80010044, 0x7C0803A6, 0x38210040, 0x4E800020)
LT_N = 32                           # per-object entries for the variables (keyed by WorkModule)
LT_SIZE = 0x40

# name, handler, params (name, type 0 int / 1 float / 3 variable, help), description
NEW_CMDS = [
    ('Line_Test', 'h_line', [
        ('Space', 0, '0: the points are relative to this object (X forward along its facing, Y up, from its position '
                     '(TransN)); 1: world coordinates. The results come back in the same space.'),
        ('X0', 1, 'Start X.'), ('Y0', 1, 'Start Y.'), ('X1', 1, 'End X.'), ('Y1', 1, 'End Y.'),
        ('Floors', 0, '0: every stage line (passable platforms too); 1: passable (drop-through) platforms left out, '
                      'as the game\'s own ground checks do.'),
        ('Distance', 3, 'Gets the distance from the start to the first line met (the whole length when none). 0: '
                        'not stored.'),
        ('HitX', 3, 'Gets the point met, X (X1 when none). 0: not stored.'),
        ('HitY', 3, 'Gets the point met, Y (Y1 when none). 0: not stored.'),
        ('Kind', 3, 'Gets what was met: 0 nothing, 1 floor (its normal points up), 2 wall, 3 ceiling. 0: not '
                    'stored.')],
     'Tests the stage between two points (the game\'s own GroundModule ray check): where the segment first meets a '
     'floor, wall or ceiling. New command: needs the patched cross_f.rpx (tools/line_test_cave.py).'),
]
VARS = [  # index, name, note (docs, Sm4shCommand aliases)
    (0x3D0, 'LINE_X0', 'Line test start X (write; Space 0: forward along the facing from the object, 1: world)'),
    (0x3D1, 'LINE_Y0', 'Line test start Y (write)'),
    (0x3D2, 'LINE_X1', 'Line test end X (write)'),
    (0x3D3, 'LINE_Y1', 'Line test end Y (write)'),
    (0x3D4, 'LINE_TEST', 'write Space + 2 x Floors: runs the test now; read: 1 it met a line, 0 not'),
    (0x3D5, 'LINE_DIST', 'read: distance from the start to the line met (the whole length if none)'),
    (0x3D6, 'LINE_HIT_X', 'read: the point met, X (the end if none), in the test\'s space'),
    (0x3D7, 'LINE_HIT_Y', 'read: the point met, Y'),
    (0x3D8, 'LINE_KIND', 'read: 0 nothing, 1 floor, 2 wall, 3 ceiling'),
    (0x3D9, 'LINE_NX', 'read: the line\'s normal X (along the facing in Space 0)'),
    (0x3DA, 'LINE_NY', 'read: the line\'s normal Y'),
]


def crc(name):
    return zlib.crc32(name.encode()) & 0xFFFFFFFF


def bdecode(a, w):
    assert w >> 26 == 18 and not w & 3, '0x%08X: 0x%08X is not a b' % (a, w)
    off = w & 0x3FFFFFC
    return a + (off - 0x4000000 if off & 0x2000000 else off)


def bcdecode(a, w):
    assert w >> 26 == 16, '0x%08X: 0x%08X is not a bc' % (a, w)
    off = w & 0xFFFC
    return a + (off - 0x10000 if off & 0x8000 else off)


def branch(src, dst):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0
    return (18 << 26) | (off & 0x3FFFFFC)


def find(orig):
    """the sites in acmd_ext_cave.py's code, found from the game's hooks into it and by their words"""
    s = {}
    lookup = bdecode(LOOKUP_HOOK, orig(LOOKUP_HOOK))
    # lookup: ... lk_found: addi r3, r11, NEW_BASE; blr; lk_none: li r3, -1; blr
    for x in range(lookup, lookup + 0x80, 4):
        if orig(x) == 0x386B0000 | ACMD_NEW_BASE and orig(x + 4) == 0x4E800020:
            s['lk_none'] = x + 8
            break
    assert 'lk_none' in s, 'acmd_ext lookup: lk_found not found'
    # size1 / size2: slwi; stwx; addi rX, r3, -base; cmplwi rX, n; bge X_orig
    for key, hook in (('s1', SIZE1), ('s2', SIZE2)):
        at = bdecode(hook, orig(hook))
        bge = orig(at + 16)
        assert bge >> 26 == 16 and (bge >> 21) & 31 == 4, '%s: no bge at 0x%08X' % (key, at + 16)
        s[key] = bcdecode(at + 16, bge)
        s[key + '_back'] = hook + 12
    at = bdecode(FETCH, orig(FETCH))               # fetch: addi r6, r7, -base; cmplwi r6, n; bge f_orig
    bge = orig(at + 8)
    assert bge >> 26 == 16, 'fetch: no bge'
    s['f'] = bcdecode(at + 8, bge)
    s['f_back'] = FETCH + 8
    # the hooked words: the instruction acmd_ext_cave.py wrote there, or a later cave's `b`
    want = {'lk_none': 0x3860FFFF, 's1': 0x7C0A202E, 's2': 0x7D8BF02E, 'f': 0x54C6103A}
    for k, w in want.items():
        got = orig(s[k])
        assert got == w or got >> 26 == 18, '%s 0x%08X: 0x%08X (want 0x%08X or a b)' % (k, s[k], got, w)
        s[k + '_word'] = got
    # f_orig is two words (slwi r6, r7, 2; lwzx r0, r6, r29): the second must be there when we replay
    if s['f_word'] == want['f']:
        assert orig(s['f'] + 4) == 0x7C06E82E and bdecode(s['f'] + 8, orig(s['f'] + 8)) == s['f_back']
    # hv_var / hvv_zero (diag_godfist_cave.py's find_hv) and ue_out, acc_of
    for x in range(0x04B90000, 0x04BA0000, 4):
        if orig(x) == HV_VAR_SIG[0] and orig(x + 8) == HV_VAR_SIG[2]:
            s['hv_var'] = x
            break
    assert 'hv_var' in s, 'hv_var not found'
    s['hvv_zero'] = bcdecode(s['hv_var'] + 12, orig(s['hv_var'] + 12))
    s['hvv_next'] = bdecode(s['hvv_zero'], orig(s['hvv_zero']))
    for x in range(0x04B90000, 0x04BA0000, 4):
        if all(orig(x + 4 * i) == w for i, w in enumerate(UE_OUT_SIG)):
            s['ue_out'] = x
            break
    assert 'ue_out' in s, 'ue_out not found'
    s['ue_zero'] = s['ue_out'] - 8
    assert orig(s['ue_zero']) >> 16 == 0x3D80, 'ue_zero: lis r12'
    for x in range(s['hv_var'], s['hv_var'] + 0x80, 4):    # hv_var: mr r3, r31; bl acc_of
        if orig(x) == 0x7FE3FB78 and orig(x + 4) >> 26 == 18 and orig(x + 4) & 1:
            s['acc_of'] = bdecode(x + 4, orig(x + 4) & ~1)
            break
    assert 'acc_of' in s, 'acc_of not found'
    return s


def replay(at, word, back, label):
    """the hooked instruction (or the later cave's b) at our fallback, then back"""
    if word >> 26 == 18:
        return '%s:\n        b 0x%08X\n' % (label, bdecode(at, word))
    return '%s:\n        .word 0x%08X\n        b 0x%08X\n' % (label, word, back)


def build(orig):
    for i, w in enumerate(RAY_N_HEAD):
        assert orig(RAY_N + 4 * i) == w, 'ray_check word %d' % i
    for i, w in enumerate(POSTURE_FW_HEAD):
        assert orig(POSTURE_FW + 4 * i) == w, 'PostureModuleF wrapper word %d' % i
    s = find(orig)
    n = len(NEW_CMDS)
    a = Asm(CAVE)
    sizes = ''.join('        .word %d\n' % (1 + len(p)) for _n, _h, p, _d in NEW_CMDS)
    crcs = ''.join('        .word 0x%08X\n' % crc(c[0]) for c in NEW_CMDS)
    hands = ''.join('        .word %s\n' % c[1] for c in NEW_CMDS)
    a.asm("""
# --- the command tables' fallbacks: our CRCs / indices ---------------------------------------------------------------
lt_lookup:                              # r3 = a CRC neither table has (yet)
        lis r12, lt_crcs@ha
        addi r12, r12, lt_crcs@l
        li r11, 0
ltl_loop:
        cmpwi r11, %(n)d
        bge ltl_none
        slwi r0, r11, 2
        lwzx r0, r12, r0
        cmplw r0, r3
        beq ltl_found
        addi r11, r11, 1
        b ltl_loop
ltl_found:
        addi r3, r11, %(base)d
        blr
""" % dict(n=n, base=LT_BASE) + replay(s['lk_none'], s['lk_none_word'], s['lk_none'] + 4, 'ltl_none') + """
lt_size1:                               # r3 index, r10 = index x 4, r4 the game's size table: r0 = the size
        addi r0, r3, -%(base)d
        cmplwi r0, %(n)d
        bge lts1_orig
        slwi r0, r0, 2
        lis r12, lt_sizes@ha
        addi r12, r12, lt_sizes@l
        lwzx r0, r12, r0
        b 0x%(s1b)08X
""" % dict(n=n, base=LT_BASE, s1b=s['s1_back']) + replay(s['s1'], s['s1_word'], s['s1_back'], 'lts1_orig') + """
lt_size2:                               # r3 index, r11 = index x 4, r30 the game's size table: r12 = the size
        addi r12, r3, -%(base)d
        cmplwi r12, %(n)d
        bge lts2_orig
        slwi r12, r12, 2
        addis r12, r12, lt_sizes@ha
        lwz r12, lt_sizes@l(r12)
        b 0x%(s2b)08X
""" % dict(n=n, base=LT_BASE, s2b=s['s2_back']) + replay(s['s2'], s['s2_word'], s['s2_back'], 'lts2_orig') + """
lt_fetch:                               # r7 index, r29 the game's handler table: r0 = the handler (r6 free)
        addi r6, r7, -%(base)d
        cmplwi r6, %(n)d
        bge ltf_orig
        slwi r6, r6, 2
        addis r6, r6, lt_hands@ha
        lwz r0, lt_hands@l(r6)
        b 0x%(fb)08X
""" % dict(n=n, base=LT_BASE, fb=s['f_back']) + ("""
ltf_orig:
        b 0x%08X
""" % bdecode(s['f'], s['f_word']) if s['f_word'] >> 26 == 18 else """
ltf_orig:
        slwi r6, r7, 2
        lwzx r0, r6, r29
        b 0x%08X
""" % s['f_back']) + """
# --- lt_core(r3 accessor, r4 entry): the test; entry +4 x0, +8 y0, +0xC x1, +0x10 y1, +0x14 mode (int: 1 world, 2
#     passable platforms left out) -> +0x18 hit (1.0 / 0.0), +0x1C distance, +0x20 / +0x24 the point, +0x28 kind,
#     +0x2C / +0x30 the normal. Frame 0x80: 0x10 PostureF args, 0x20 from, 0x28 dir, 0x30 out, 0x38 normal, 0x40 lr,
#     0x44 px, 0x48 py, r27-r31 saved at 0x6C
lt_core:
        stwu r1, -0x80(r1)
        mflr r0
        stw r0, 0x84(r1)
        stmw r27, 0x6C(r1)
        mr r31, r3
        mr r30, r4
        lis r29, lt_k@ha
        addi r29, r29, lt_k@l           # constants: +0 0.0, +4 1.0, +8 -1.0, +0xC 0.6, +0x10 0.5, +0x14 1.5
        lfs f0, 4(r29)
        stfs f0, 0x40(r1)               # world: lr 1, origin 0
        lfs f0, 0(r29)
        stfs f0, 0x44(r1)
        stfs f0, 0x48(r1)
        lwz r0, 0x14(r30)
        andi. r0, r0, 1
        bne ltc_points
        li r28, 0
ltc_post:                               # lr, x, y: PostureModuleF(0 / 1 / 2)
        stw r28, 0x10(r1)
        li r0, 0
        stw r0, 0x50(r1)                # fake MSC context: +4 the accessor
        stw r31, 0x54(r1)
        addi r0, r1, 0x10
        stw r0, 0x58(r1)
        li r0, 1
        stw r0, 0x5C(r1)
        addi r3, r1, 0x50
        addi r4, r1, 0x58
        lis r12, 0x%(pfh)04X
        ori r12, r12, 0x%(pfl)04X
        mtctr r12
        bctrl
        slwi r0, r28, 2
        addi r12, r1, 0x40
        stwx r3, r12, r0
        addi r28, r28, 1
        cmpwi r28, 3
        blt ltc_post
ltc_points:                             # from = (px + lr x0, py + y0), dir = (lr (x1 - x0), y1 - y0)
        lfs f10, 0x40(r1)
        lfs f11, 0x44(r1)
        lfs f12, 0x48(r1)
        lfs f1, 4(r30)
        lfs f2, 8(r30)
        lfs f3, 0xC(r30)
        lfs f4, 0x10(r30)
        fmadds f5, f10, f1, f11
        fadds f6, f12, f2
        stfs f5, 0x20(r1)
        stfs f6, 0x24(r1)
        fsubs f7, f3, f1
        fmuls f7, f7, f10
        fsubs f8, f4, f2
        stfs f7, 0x28(r1)
        stfs f8, 0x2C(r1)
        lwz r3, 0x2C(r31)               # GroundModule
        cmpwi r3, 0
        beq ltc_none
        addi r4, r1, 0x20
        addi r5, r1, 0x28
        addi r6, r1, 0x30
        addi r7, r1, 0x38
        lwz r0, 0x14(r30)
        rlwinm r8, r0, 31, 31, 31       # mode bit 2 -> 1: platforms out ...
        xori r8, r8, 1                  # ... ray_check's `all` 0
        lis r12, 0x%(rh)04X
        ori r12, r12, 0x%(rl)04X
        mtctr r12
        bctrl
        cmpwi r3, 0
        beq ltc_none
        lfs f0, 4(r29)
        stfs f0, 0x18(r30)              # hit
        lfs f1, 0x30(r1)                # the point (world)
        lfs f2, 0x34(r1)
        lfs f5, 0x20(r1)
        lfs f6, 0x24(r1)
        fsubs f3, f1, f5
        fsubs f4, f2, f6
        fmuls f3, f3, f3
        fmadds f1, f4, f4, f3
        bl lt_sqrt
        stfs f1, 0x1C(r30)              # distance
        lfs f10, 0x40(r1)
        lfs f1, 0x30(r1)
        lfs f2, 0x34(r1)
        lfs f11, 0x44(r1)
        lfs f12, 0x48(r1)
        fsubs f1, f1, f11
        fmuls f1, f1, f10               # back in the test's space
        fsubs f2, f2, f12
        stfs f1, 0x20(r30)
        stfs f2, 0x24(r30)
        lfs f1, 0x38(r1)                # the normal
        lfs f2, 0x3C(r1)
        fmuls f1, f1, f10
        stfs f1, 0x2C(r30)
        stfs f2, 0x30(r30)
        lfs f3, 0xC(r29)                # kind: ny >= 0.6 floor, <= -0.6 ceiling, else wall
        lfs f0, 4(r29)
        fcmpu cr0, f2, f3
        bge ltc_kind
        fneg f3, f3
        lfs f0, 0x18(r29)               # 3.0
        fcmpu cr0, f2, f3
        ble ltc_kind
        lfs f0, 0x1C(r29)               # 2.0
ltc_kind:
        stfs f0, 0x28(r30)
        b ltc_out
ltc_none:                               # nothing met: the end, the whole length
        lfs f0, 0(r29)
        stfs f0, 0x18(r30)
        stfs f0, 0x28(r30)
        stfs f0, 0x2C(r30)
        stfs f0, 0x30(r30)
        lfs f1, 0xC(r30)
        lfs f2, 0x10(r30)
        stfs f1, 0x20(r30)
        stfs f2, 0x24(r30)
        lfs f3, 0x28(r1)
        lfs f4, 0x2C(r1)
        fmuls f3, f3, f3
        fmadds f1, f4, f4, f3
        bl lt_sqrt
        stfs f1, 0x1C(r30)
ltc_out:
        lmw r27, 0x6C(r1)
        lwz r0, 0x84(r1)
        mtlr r0
        addi r1, r1, 0x80
        blr

# --- lt_sqrt(f1) -> f1 (0 for <= 0); f0 f2 f12 f13, r12 -------------------------------------------------------------
lt_sqrt:
        lis r12, lt_k@ha
        addi r12, r12, lt_k@l
        lfs f0, 0(r12)
        fcmpu cr0, f1, f0
        bgt lts_go
        fmr f1, f0
        blr
lts_go:
        frsqrte f12, f1
        lfs f13, 0x10(r12)
        lfs f0, 0x14(r12)
        fmuls f13, f1, f13
        fmuls f2, f12, f12
        fmuls f2, f2, f13
        fsubs f2, f0, f2
        fmuls f12, f12, f2
        fmuls f2, f12, f12
        fmuls f2, f2, f13
        fsubs f2, f0, f2
        fmuls f12, f12, f2
        fmuls f2, f12, f12
        fmuls f2, f2, f13
        fsubs f2, f0, f2
        fmuls f12, f12, f2
        fmuls f1, f1, f12
        blr

# --- Line_Test(Space, X0, Y0, X1, Y1, Floors, Distance, HitX, HitY, Kind): (r3 accessor, r5 script state, r6 (+8
#     execute), r7 parameters). Frame 0x80: 0x10 the entry, r26-r31 at 0x60
h_line:
        stwu r1, -0x80(r1)
        mflr r0
        stw r0, 0x84(r1)
        stmw r26, 0x60(r1)
        mr r31, r5
        mr r30, r7
        mr r29, r3
        li r28, %(bytes)d
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq hl_out
        cmpwi r29, 0
        beq hl_out
        lwz r0, 4(r30)                  # x0 y0 x1 y1
        stw r0, 0x14(r1)
        lwz r0, 8(r30)
        stw r0, 0x18(r1)
        lwz r0, 0xC(r30)
        stw r0, 0x1C(r1)
        lwz r0, 0x10(r30)
        stw r0, 0x20(r1)
        lwz r0, 0(r30)                  # mode = Space & 1 | (Floors != 0) << 1
        andi. r0, r0, 1
        lwz r12, 0x14(r30)
        cmpwi r12, 0
        beq hl_mode
        ori r0, r0, 2
hl_mode:
        stw r0, 0x24(r1)
        mr r3, r29
        addi r4, r1, 0x10
        bl lt_core
        li r27, 0                       # Distance / HitX / HitY / Kind -> entry +0x1C / +0x20 / +0x24 / +0x28
hl_store:
        slwi r26, r27, 2
        addi r12, r26, 0x18
        lwzx r4, r30, r12               # the variable
        cmpwi r4, 0
        beq hl_next
        addi r12, r26, 0x2C
        lfsx f1, r1, r12
        lwz r3, 0x28(r29)               # WorkModule set_float(id, f1)
        cmpwi r3, 0
        beq hl_next
        lwz r12, 0(r3)
        lwz r12, 0x4C(r12)
        mtctr r12
        bctrl
hl_next:
        addi r27, r27, 1
        cmpwi r27, 4
        blt hl_store
hl_out:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne hl_ret
        lwz r11, 4(r31)
        add r11, r11, r28
        stw r11, 4(r31)
        li r3, 2
hl_ret:
        lmw r26, 0x60(r1)
        lwz r0, 0x84(r1)
        mtlr r0
        addi r1, r1, 0x80
        blr

# --- the variables (from hv_var's hvv_zero: r31 WorkModule, r30 index, r29 write; r1 = user_entry's frame, the
#     written float at 0x18; r27 r28 free; ue_out returns f1 to a read, the written value to a write) -----------------
lt_var:
        cmplwi r30, %(vlo)d
        blt ltv_next
        cmplwi r30, %(vhi)d
        bgt ltv_next
        mr r3, r31
        bl lt_entry                     # r3 = its entry (a write makes one), 0 none
        mr. r28, r3
        beq ltv_zero
        addi r27, r30, -%(vlo)d
        cmpwi r29, 0
        beq ltv_read
        cmplwi r27, 4
        bgt ltv_done                    # results: read only
        beq ltv_run
        slwi r12, r27, 2                # x0 y0 x1 y1 -> +4 ...
        addi r12, r12, 4
        lfs f1, 0x18(r1)
        stfsx f1, r28, r12
        b ltv_done
ltv_run:
        lfs f1, 0x18(r1)                # mode = the value written
        fctiwz f1, f1
        stfd f1, 0x08(r1)
        lwz r0, 0x0C(r1)
        stw r0, 0x14(r28)
        mr r3, r31
        bl 0x%(acc_of)08X                # its accessor
        cmpwi r3, 0
        beq ltv_done
        mr r4, r28
        bl lt_core
ltv_done:
        b 0x%(ue_out)08X
ltv_read:
        slwi r12, r27, 2                # 0-3: +4 + 4i; 4-10: +0x18 + 4 (i - 4) = +8 + 4i
        addi r12, r12, 4
        cmplwi r27, 4
        blt ltv_rd
        addi r12, r12, 4
ltv_rd:
        lfsx f1, r28, r12
        b 0x%(ue_out)08X
ltv_zero:
        b 0x%(ue_zero)08X
ltv_next:
        b 0x%(next)08X

# --- lt_entry(r3 WorkModule, r29 write) -> r3 its entry, made (the next in turn) on a write; 0 ----------------------
lt_entry:
        lis r11, lt_tab@ha
        addi r11, r11, lt_tab@l
        li r12, %(ltn)d
lte_loop:
        lwz r0, 0(r11)
        cmplw r0, r3
        beq lte_hit
        addi r11, r11, %(lts)d
        addi r12, r12, -1
        cmpwi r12, 0
        bne lte_loop
        cmpwi r29, 0
        beq lte_none
        lis r11, lt_next@ha
        lwz r12, lt_next@l(r11)
        addi r0, r12, 1
        cmplwi r0, %(ltn)d
        blt lte_wrap
        li r0, 0
lte_wrap:
        stw r0, lt_next@l(r11)
        mulli r12, r12, %(lts)d
        lis r11, lt_tab@ha
        addi r11, r11, lt_tab@l
        add r11, r11, r12
        stw r3, 0(r11)
        li r0, 0
        stw r0, 0x14(r11)
lte_hit:
        mr r3, r11
        blr
lte_none:
        li r3, 0
        blr

lt_k:
        .float 0.0
        .float 1.0
        .float -1.0
        .float 0.6
        .float 0.5
        .float 1.5
        .float 3.0
        .float 2.0
lt_crcs:
%(crcs)slt_sizes:
%(sizes)slt_hands:
%(hands)slt_next:
        .word 0
lt_tab:
""" % dict(pfh=POSTURE_FW >> 16, pfl=POSTURE_FW & 0xFFFF, rh=RAY_N >> 16, rl=RAY_N & 0xFFFF, bytes=4 * (1 + len(NEW_CMDS[0][2])),
           vlo=VAR_LO, vhi=VAR_HI, acc_of=s['acc_of'], ue_out=s['ue_out'], ue_zero=s['ue_zero'], next=s['hvv_next'],
           ltn=LT_N, lts=LT_SIZE, crcs=crcs, sizes=sizes, hands=hands))
    words = a.words()
    tab = a.addr('lt_tab')
    assert tab + LT_N * LT_SIZE <= LIMIT, 'cave too big: 0x%08X' % (tab + LT_N * LT_SIZE)
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    for x in list(out) + list(range(tab, tab + LT_N * LT_SIZE, 4)):
        assert orig(x) == 0, 'cave word 0x%08X not free' % x
    out[s['lk_none']] = branch(s['lk_none'], a.addr('lt_lookup'))
    out[s['s1']] = branch(s['s1'], a.addr('lt_size1'))
    out[s['s2']] = branch(s['s2'], a.addr('lt_size2'))
    out[s['f']] = branch(s['f'], a.addr('lt_fetch'))
    out[s['hvv_zero']] = branch(s['hvv_zero'], a.addr('lt_var'))
    return out, a.labels, s


def labels(path):
    """Line_Test's entry in tools/Sm4shCommand/param_labels.json (apply_param_labels.py then puts it in Events.cfg and
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
        d['%08X' % crc(name)] = e
    json.dump(dict(sorted(d.items())), open(path, 'w'), indent=1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', help='the executable to patch (acmd_ext_cave.py applied: exe_v46v_threads or later)')
    p.add_argument('--labels', help='update this param_labels.json with Line_Test')
    args = p.parse_args()
    if args.labels:
        labels(args.labels)
        return
    import kind_expand as K
    img = K.Image(args.rpx)
    words, lab, s = build(img.w)
    print(' '.join('0x%08X=0x%08X' % kv for kv in sorted(words.items())))
    sys.stderr.write('line test: %d words, Line_Test index %d (0x%08X), vars 0x0F0003%02X-0x0F0003%02X, hooks %s\n' % (
        len(words), LT_BASE, crc('Line_Test'), VAR_LO & 0xFF, VAR_HI & 0xFF,
        ', '.join('%s 0x%08X' % (k, s[k]) for k in ('lk_none', 's1', 's2', 'f', 'hvv_zero'))))


if __name__ == '__main__':
    main()
