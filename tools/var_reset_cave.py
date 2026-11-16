#!/usr/bin/env python3
"""exe_v46w_vars: variable resets on a KO, a landing, a ledge grab and a hit (on exe_v46v_threads).

New_Var's optional Reset (bits 8-11 of its Scope word) and the new command Var_Reset_Set(Variable, Reset, Value,
Owner) give an object a list of variables to put back when something happens to it:
  1 KO        its Dead status (0xB1) starts; also, for a KO bit that hasn't fired yet, the fighter's set-up (the
              respawn's module reset), whichever comes first: once per KO (a KO write drops the item's KO bit)
  2 landing   its situation goes from air (2) to ground (0) (the fighters' StatusModule set_situation, vt +0xEC)
  4 ledge     its status becomes CliffCatchMove / CliffCatch (0x72 / 0x73) or a tether's AirCatchHit /
              AirCatchHang (0xF3 / 0xF4), from a status outside those four
  8 hit       a hit takes effect on it (the damage reaction decision Gravity_Set already hooks: DamageModule owner
              vt +0x14C returning 0). A hit with no reaction (armor, heavy armor, knockback under the threshold) and
              a shielded hit (it never reaches the DamageModule) don't count
The reset is a write of the item's value through the owner's WorkModule set_float (vt +0x4C): exactly what that
object's SET_FLOAT / MSC WorkModule(0, value, ID) would do then, so any float variable works (VAR_n, TIMER_n,
New_Var slots, SLOTn_SHARED_k, the input / state variables, which act on their own target). Fighters only have the
events; an article's items never fire.

Storage: VR_N blocks of VR_BLK at VR_TAB (zero at load), keyed by the owner's WorkModule (round robin past VR_N):
+0 WorkModule, items at +0x10, VR_ITEMS of 0x10: {ID (0 = free), value (float), mask, 0}. The object's set-up
(WM_RESET) fires its unfired KO items, then frees the block, as the variables themselves are cleared there.

MSC (no command there): WorkModule(0, index, 0x0F0003CA) selects the variable 0x0F000000 + index (VAR_n 0x300 + n,
SELF_INPUT_OFF 0x115, a New_Var slot 0x380 + k: an index keeps the ID exact in a float), 0x0F0003CB its value,
0x0F0003CC the owner (a target: 0 this object, 3-10 player slots 1-8, ...), then a write of the mask to 0x0F0003CD
sets it (0 removes it). Reads give the selection back; 0x0F0003CD reads the selected item's mask.

Hooks (each asserts the exe_v46v_threads word it replaces; the ones that were a branch already chain on to it):
  STATUS  0x02E88D00  stw r28, 0x48(r30)   the status change's store of the new kind -> vr_chg (KO / ledge)
  SIT     0x02E890EC  stw r28, 0x84(r29)   set_situation's store                    -> vr_sit (landing)
  HIT     gs_hit + 0x20 lwz r3, 0x10(r1)   gs_hit, a hit that takes effect           -> vr_hit
  RESET   0x02BF5864  b (hv_wmreset chain) the object set-up                        -> vr_wmreset, then the chain
  NEWVAR  cmd_handlers[New_Var]  h_newvar                                           -> vr_newvar (wraps it)
  VAR     bv_zero     b ue_zero            user_entry's unused IDs                   -> vr_var (0x3CA-0x3CD)
  LOOKUP / SIZE1 / SIZE2 / FETCH: acmd_ext_cave.py's lk_none / s1_orig / s2_orig / f_orig (the paths for a CRC not
          in its table / an index past its commands) -> vr_lookup / vr_size1 / vr_size2 / vr_fetch: Var_Reset_Set is
          index VR_INDEX (its own, far past acmd_ext's), size 5. A later cave adding a command chains the same way
          after these (docs/native-notes.md "Variable resets").

  python3 tools/rpx_patch.py exe_v46v_threads.rpx exe_v46w_vars.rpx $(python3 tools/var_reset_cave.py --rpx exe_v46v_threads.rpx)
"""
import argparse
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

VR_CODE = 0x04BD8000            # claimed region 0x04BD8000-0x04BE0000 (docs/native-notes.md "Variable resets");
VR_DATA = 0x04BD9F00            # 0x04BD6000-0x04BD8000 is left free for the next cave
VR_TAB = 0x04BDA000
VR_N = 48
VR_BLK = 0x200
VR_ITEMS = (VR_BLK - 0x10) // 0x10
VR_END = VR_TAB + VR_N * VR_BLK
assert VR_END == 0x04BE0000
TEXT_REGION = VR_END - 0x02000000

STATUS_AT, STATUS_WORD = 0x02E88D00, 0x939E0048
SIT_AT, SIT_WORD = 0x02E890EC, 0x939D0084
RESET_AT = 0x02BF5864
HIT_OFF, HIT_WORD = 0x20, 0x80610010
FIGHTER_SM_VT = 0x1012D42C      # the fighters' StatusModule vtable
WM_SET_FLOAT = 0x4C             # WorkModule vt +0x4C: set_float(r3 wm, r4 ID, f1 value)

KO, LANDING, LEDGE, HIT = 1, 2, 4, 8
DEAD = 0xB1
LEDGE_KINDS = (0x72, 0x73, 0xF3, 0xF4)
VAR_SEL, VAR_VALUE, VAR_OWNER, VAR_RESET = 0x3CA, 0x3CB, 0x3CC, 0x3CD

VR_INDEX = 2000                 # Var_Reset_Set's command index (acmd_ext_cave.py's are 584 + k, k < 64)
CMD_NAME = 'Var_Reset_Set'
CMD_SIZE = 5
CMD_CRC = zlib.crc32(CMD_NAME.encode()) & 0xFFFFFFFF

# VR_DATA words
D_BUSY, D_SEL, D_VAL, D_OWN, D_RR = 0x0, 0x4, 0x8, 0xC, 0x10
D_CNT = 0x20                    # counters: +0 KO fired, +4 landing, +8 ledge, +0xC hit, +0x10 items written,
                                # +0x14 items set, +0x18 refused (table / list full), +0x1C set-up KO fires

# for Sm4shCommand / tools/acmd.py (acmd_ext_cave.py's NEW_CMDS form: name, handler label, params, description)
_RESET = ('When to reset it (bits, add them): 1 its KO, 2 its landing, 4 its ledge grab, 8 a hit taking effect on it '
          '(not shield, not armor). 0 removes the reset.')
EXT_CMDS = [
    (CMD_NAME, 'vr_cmd', [
        ('Variable', 3, 'The variable to put back (any float variable: VAR_0, TIMER_0, a New_Var name, SLOT2_SHARED_0, '
                        'SELF_INPUT_OFF, ...), as the owner sees it.'),
        ('Reset', 0, _RESET),
        ('Value', 1, 'The value it is set to then.'),
        ('Owner', 0, 'Whose events and whose variable: 0 this object, 1 the nearest opponent, 2 the last fighter this '
                     'one hit, 3-10 player slots 1-8, 11 the last fighter that hit this one, 12 the fighter this '
                     'attack hit (as the other commands\' Target). The variable is written as the owner\'s own.')],
     'Puts a variable back to a value when its owner is KO\'d, lands, grabs a ledge or is hit (exe_v46w).'),
]


def bw(src, dst, link=False):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0, '0x%08X -> 0x%08X' % (src, dst)
    return (18 << 26) | (off & 0x3FFFFFC) | (1 if link else 0)


def b_target(at, w):
    assert w >> 26 == 18 and w & 3 == 0, '0x%08X: 0x%08X is not a plain b' % (at, w)
    off = w & 0x3FFFFFC
    if off & 0x2000000:
        off -= 0x4000000
    return (at + off) & 0xFFFFFFFF


def ext_labels():
    import acmd_ext_cave as C
    a, _w, _h = C.build()
    out = {}
    for p in [a] + [getattr(a, 'part%d' % i) for i in range(2, 10) if hasattr(a, 'part%d' % i)]:
        try:
            out.update(p.labels)
        except Exception:
            pass
    out['_newvar_index'] = [c[0] for c in C.COMMANDS].index('New_Var')
    out['_n'] = len(C.COMMANDS)
    return out


def chk(reg, fail, tmp='r0'):
    return """
        addis %(t)s, %(r)s, -0x1000
        rlwinm. %(t)s, %(t)s, 0, 0, 0
        bne %(f)s
        andi. %(t)s, %(r)s, 3
        bne %(f)s""" % dict(t=tmp, r=reg, f=fail)


def source(L, reset_chain, var_chain):
    D = dict(data=VR_DATA, tab=VR_TAB, n=VR_N, blk=VR_BLK, last=VR_BLK - 4, items=VR_ITEMS,
             busy=D_BUSY, sel=D_SEL, val=D_VAL, own=D_OWN, rr=D_RR, cnt=D_CNT,
             smvt_h=FIGHTER_SM_VT >> 16, smvt_l=FIGHTER_SM_VT & 0xFFFF, setf=WM_SET_FLOAT,
             dead=DEAD, l0=LEDGE_KINDS[0], l1=LEDGE_KINDS[1], l2=LEDGE_KINDS[2], l3=LEDGE_KINDS[3],
             status_back=STATUS_AT + 4, sit_back=SIT_AT + 4, hit_back=L['gs_hit'] + HIT_OFF + 4,
             reset_chain=reset_chain, var_chain=var_chain, h_newvar=L['h_newvar'],
             nc_target=L['nc_target'], acc_of=L['acc_of'], f2i=L['f2i'], i2f=L['i2f'], ue_out=L['ue_out'],
             vsel=VAR_SEL, vval=VAR_VALUE, vown=VAR_OWNER, vres=VAR_RESET,
             idx=VR_INDEX, crc_h=CMD_CRC >> 16, crc_l=CMD_CRC & 0xFFFF, size=CMD_SIZE,
             s1back=L['s1_orig'] + 4, s2back=L['s2_orig'] + 4, fback=L['f_orig'] + 8,
             step=4 * CMD_SIZE, c10=D_CNT + 0x10, c14=D_CNT + 0x14, c18=D_CNT + 0x18, c1C=D_CNT + 0x1C)
    return """
# --- vr_blk(r3 WorkModule, r4 create) -> r3 its block or 0; leaf: r0 r10 r11 r12 ------------------------------------
vr_blk:
        lis r12, 0x%(tab)X@ha
        addi r12, r12, 0x%(tab)X@l
        li r11, %(n)d
vb_loop:
        lwz r0, 0(r12)
        cmplw r0, r3
        beq vb_hit
        addi r12, r12, %(blk)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne vb_loop
        cmpwi r4, 0
        beq vb_none
        lis r12, 0x%(tab)X@ha
        addi r12, r12, 0x%(tab)X@l
        li r11, %(n)d
vb_free:
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq vb_take
        addi r12, r12, %(blk)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne vb_free
        lis r10, 0x%(data)X@ha          # all taken: round robin
        addi r10, r10, 0x%(data)X@l
        lwz r11, %(rr)d(r10)
        addi r0, r11, 1
        cmplwi r0, %(n)d
        blt vb_wrap
        li r0, 0
vb_wrap:
        stw r0, %(rr)d(r10)
        mulli r11, r11, %(blk)d
        lis r12, 0x%(tab)X@ha
        addi r12, r12, 0x%(tab)X@l
        add r12, r12, r11
vb_take:
        li r0, 0
        li r11, %(last)d
vb_zero:
        stwx r0, r12, r11
        addi r11, r11, -4
        cmpwi r11, 0
        bge vb_zero
        stw r3, 0(r12)
vb_hit:
        mr r3, r12
        blr
vb_none:
        li r3, 0
        blr

# --- vr_item(r3 block, r4 ID) -> r3 its item or 0, r10 a free item or 0; leaf: r0 r10 r11 r12 -----------------------
vr_item:
        addi r12, r3, 0x10
        li r11, %(items)d
        li r10, 0
        rlwinm r4, r4, 0, 4, 31          # the top nibble (the access type) doesn't name another variable
vi_loop:
        lwz r0, 0(r12)
        cmpwi r0, 0
        bne vi_cmp
        cmpwi r10, 0
        bne vi_next
        mr r10, r12
        b vi_next
vi_cmp:
        rlwinm r0, r0, 0, 4, 31
        cmplw r0, r4
        beq vi_hit
vi_next:
        addi r12, r12, 0x10
        addi r11, r11, -1
        cmpwi r11, 0
        bne vi_loop
        li r3, 0
        blr
vi_hit:
        mr r3, r12
        blr

# --- vr_put(r3 WorkModule, r4 ID, r5 mask, f1 value) -> r3 1 done / 0 refused --------------------------------------
vr_put:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stmw r29, 0x14(r1)
        mr r31, r4
        clrlwi r30, r5, 28
        rlwinm. r0, r31, 0, 4, 31
        beq vp_no                       # ID 0: nothing
        mr r4, r30                      # a mask makes the block; 0 only removes
        bl vr_blk
        mr. r29, r3
        beq vp_noblk
        mr r4, r31
        bl vr_item
        cmpwi r3, 0
        bne vp_have
        cmpwi r30, 0
        beq vp_ok
        mr. r3, r10
        beq vp_full
vp_have:
        cmpwi r30, 0
        bne vp_set
        li r0, 0
        stw r0, 0(r3)
        stw r0, 8(r3)
        b vp_ok
vp_set:
        stw r31, 0(r3)
        stfs f1, 4(r3)
        stw r30, 8(r3)
        lis r12, 0x%(data)X@ha
        addi r12, r12, 0x%(data)X@l
        lwz r0, %(c14)d(r12)
        addi r0, r0, 1
        stw r0, %(c14)d(r12)
vp_ok:
        li r3, 1
        b vp_ret
vp_noblk:
        cmpwi r30, 0
        beq vp_ok
vp_full:
        lis r12, 0x%(data)X@ha
        addi r12, r12, 0x%(data)X@l
        lwz r0, %(c18)d(r12)
        addi r0, r0, 1
        stw r0, %(c18)d(r12)
vp_no:
        li r3, 0
vp_ret:
        lmw r29, 0x14(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# --- vr_event(r3 WorkModule, r4 bit): every item of its block with the bit: its value written (set_float); a KO
#     write drops the item's KO bit (once per KO), an item left with no bits is freed ---------------------------------
vr_event:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r27, 0x1C(r1)
        mr r31, r3
        mr r30, r4""" % D + chk('r31', 've_ret') + """
        li r4, 0
        bl vr_blk
        mr. r29, r3
        beq ve_ret
        lis r27, 0x%(data)X@ha
        addi r27, r27, 0x%(data)X@l
        lwz r0, %(busy)d(r27)
        addi r0, r0, 1
        stw r0, %(busy)d(r27)
        addi r29, r29, 0x10
        li r28, %(items)d
ve_loop:
        lwz r0, 0(r29)
        cmpwi r0, 0
        beq ve_next
        lwz r0, 8(r29)
        and. r0, r0, r30
        beq ve_next
        cmpwi r30, 1
        bne ve_write
        lwz r0, 8(r29)
        rlwinm r0, r0, 0, 0, 30
        stw r0, 8(r29)
ve_write:
        lwz r4, 0(r29)
        lfs f1, 4(r29)
        mr r3, r31
        lwz r12, 0(r3)
        lwz r12, %(setf)d(r12)
        mtctr r12
        bctrl
        lwz r0, %(c10)d(r27)
        addi r0, r0, 1
        stw r0, %(c10)d(r27)
        lwz r0, 8(r29)
        cmpwi r0, 0
        bne ve_next
        stw r0, 0(r29)
ve_next:
        addi r29, r29, 0x10
        addi r28, r28, -1
        cmpwi r28, 0
        bne ve_loop
        lwz r0, %(busy)d(r27)
        addi r0, r0, -1
        stw r0, %(busy)d(r27)
ve_ret:
        lmw r27, 0x1C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- vr_count(r4 bit): its event counter + 1; leaf: r0 r11 r12 ----------------------------------------------------
vr_count:
        lis r12, 0x%(data)X@ha
        addi r12, r12, 0x%(data)X@l
        addi r12, r12, %(cnt)d
        cmpwi r4, 1
        beq vc_c
        addi r12, r12, 4
        cmpwi r4, 2
        beq vc_c
        addi r12, r12, 4
        cmpwi r4, 4
        beq vc_c
        addi r12, r12, 4
vc_c:
        lwz r11, 0(r12)
        addi r11, r11, 1
        stw r11, 0(r12)
        blr

# --- vr_sm_wm(r3 a fighter's StatusModule) -> r3 its WorkModule or 0 (fighter +0x9C, accessor [fighter +0x28], whose
#     +0x20 must be this StatusModule); leaf: r0 r12 -------------------------------------------------------------------
vr_sm_wm:""" % D + chk('r3', 'vsw_no') + """
        lwz r12, 0x9C(r3)""" + chk('r12', 'vsw_no') + """
        lwz r12, 0x28(r12)""" + chk('r12', 'vsw_no') + """
        lwz r0, 0x20(r12)
        cmplw r0, r3
        bne vsw_no
        lwz r3, 0x28(r12)""" + chk('r3', 'vsw_no') + """
        blr
vsw_no:
        li r3, 0
        blr

# --- vr_fire(r3 StatusModule, r4 bit): the fighter's event (counted); saves what it uses -------------------------
vr_fire:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        mr r31, r4
        bl vr_sm_wm
        cmpwi r3, 0
        beq vf_ret
        mr r4, r31
        bl vr_count
        mr r4, r31
        bl vr_event
vf_ret:
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# --- hook 0x02E88D00 (the status change, stw r28, 0x48(r30): r28 the new kind, r30 StatusModule; r0 r3-r12 free,
#     LR free: the function saved its own) -------------------------------------------------------------------------
vr_chg:
        lwz r12, 0x48(r30)              # the kind it leaves
        stw r28, 0x48(r30)
        cmpw r12, r28
        beq vc_back
        li r4, 1
        cmpwi r28, %(dead)d
        beq vc_fire
        cmpwi r28, %(l0)d
        beq vc_ledge
        cmpwi r28, %(l1)d
        beq vc_ledge
        cmpwi r28, %(l2)d
        beq vc_ledge
        cmpwi r28, %(l3)d
        bne vc_back
vc_ledge:
        cmpwi r12, %(l0)d               # from another catch status: the same grab
        beq vc_back
        cmpwi r12, %(l1)d
        beq vc_back
        cmpwi r12, %(l2)d
        beq vc_back
        cmpwi r12, %(l3)d
        beq vc_back
        li r4, 4
vc_fire:
        mr r3, r30
        bl vr_fire
vc_back:
        b 0x%(status_back)08X

# --- hook 0x02E890EC (set_situation, stw r28, 0x84(r29): r28 the new one, +0x88 the old; r0 r3-r12 free) ----------
vr_sit:
        stw r28, 0x84(r29)
        cmpwi r28, 0
        bne vs_back
        lwz r0, 0x88(r29)
        cmpwi r0, 2
        bne vs_back
        mr r3, r29
        li r4, 2
        bl vr_fire
vs_back:
        b 0x%(sit_back)08X

# --- hook gs_hit + 0x20 (a hit that takes effect: gs_hit's frame, its r4 (the accessor) at 0x10(r1)) -------------
vr_hit:
        lwz r3, 0x10(r1)
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)""" % D + chk('r3', 'vh_ret') + """
        lwz r3, 0x28(r3)""" + chk('r3', 'vh_ret') + """
        li r4, 8
        bl vr_count
        bl vr_event
vh_ret:
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        lwz r3, 0x10(r1)
        b 0x%(hit_back)08X

# --- hook 0x02BF5864 (the object set-up, r31 the accessor; only r0 r10 ctr free): a fighter's unfired KO items fire,
#     then its block goes; then the chain the word held ----------------------------------------------------------------
vr_wmreset:
        stwu r1, -0x110(r1)
        stmw r3, 0x10(r1)
        mflr r0
        stw r0, 0x88(r1)
        mfcr r0
        stw r0, 0x8C(r1)
        stfd f0, 0x90(r1)
        stfd f1, 0x98(r1)
        stfd f2, 0xA0(r1)
        stfd f3, 0xA8(r1)
        stfd f4, 0xB0(r1)
        stfd f5, 0xB8(r1)
        stfd f6, 0xC0(r1)
        stfd f7, 0xC8(r1)
        stfd f8, 0xD0(r1)
        stfd f9, 0xD8(r1)
        stfd f10, 0xE0(r1)
        stfd f11, 0xE8(r1)
        stfd f12, 0xF0(r1)
        stfd f13, 0xF8(r1)""" % D + chk('r31', 'vw_done') + """
        lwz r30, 0x28(r31)""" + chk('r30', 'vw_done') + """
        mr r3, r30
        li r4, 0
        bl vr_blk
        cmpwi r3, 0
        beq vw_done                     # nothing kept for it
        lwz r12, 0x20(r31)""" + chk('r12', 'vw_free') + """
        lwz r0, 0(r12)
        lis r12, 0x%(smvt_h)X
        ori r12, r12, 0x%(smvt_l)X
        cmplw r0, r12
        bne vw_free                     # not a fighter
        lis r12, 0x%(data)X@ha
        addi r12, r12, 0x%(data)X@l
        lwz r0, %(c1C)d(r12)
        addi r0, r0, 1
        stw r0, %(c1C)d(r12)
        mr r3, r30
        li r4, 1
        bl vr_event
vw_free:
        mr r3, r30
        li r4, 0
        bl vr_blk
        cmpwi r3, 0
        beq vw_done
        li r0, 0
        stw r0, 0(r3)
vw_done:
        lfd f0, 0x90(r1)
        lfd f1, 0x98(r1)
        lfd f2, 0xA0(r1)
        lfd f3, 0xA8(r1)
        lfd f4, 0xB0(r1)
        lfd f5, 0xB8(r1)
        lfd f6, 0xC0(r1)
        lfd f7, 0xC8(r1)
        lfd f8, 0xD0(r1)
        lfd f9, 0xD8(r1)
        lfd f10, 0xE0(r1)
        lfd f11, 0xE8(r1)
        lfd f12, 0xF0(r1)
        lfd f13, 0xF8(r1)
        lwz r0, 0x8C(r1)
        mtcrf 0xFF, r0
        lwz r0, 0x88(r1)
        mtlr r0
        lmw r3, 0x10(r1)
        addi r1, r1, 0x110
        b 0x%(reset_chain)08X

# --- New_Var's handler (cmd_handlers): Scope's bits 8-11 are Reset. h_newvar runs on Scope & 0xFF (the word put back
#     after), then, executed, the slot's item: (ID, Initial, Reset) on this object; Reset 0 removes one if there -------
vr_newvar:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r26, 0x18(r1)
        mr r31, r3
        mr r30, r7
        mr r29, r6
        lwz r28, 0xC(r7)
        rlwinm r27, r28, 24, 28, 31     # Reset
        clrlwi r0, r28, 24
        stw r0, 0xC(r7)
        bl 0x%(h_newvar)08X
        mr r26, r3
        stw r28, 0xC(r30)
        lbz r0, 8(r29)
        cmpwi r0, 0
        beq vn_ret""" % D + chk('r31', 'vn_ret') + """
        lwz r3, 0x28(r31)""" + chk('r3', 'vn_ret') + """
        lwz r4, 0(r30)
        rlwinm r12, r4, 0, 4, 21        # a New_Var ID (0x0F000380 + k, k < 64, any top nibble)
        lis r11, 0x0F00
        cmplw r12, r11
        bne vn_ret
        rlwinm r12, r4, 0, 22, 31
        addi r12, r12, -0x380
        cmplwi r12, 64
        bge vn_ret
        mr r5, r27
        lfs f1, 8(r30)
        bl vr_put
vn_ret:
        mr r3, r26
        lmw r26, 0x18(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- Var_Reset_Set(Variable, Reset, Value, Owner): the handler (r3 accessor, r5 state, r6 flags, r7 parameters) ------
vr_cmd:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stmw r30, 0x18(r1)
        mr r31, r5
        mr r30, r7
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq vcm_step""" % D + chk('r3', 'vcm_step') + """
        lwz r4, 0xC(r30)                # Owner (a target; 0 this object)
        bl 0x%(nc_target)08X""" % D + chk('r3', 'vcm_step') + """
        lwz r3, 0x28(r3)""" + chk('r3', 'vcm_step') + """
        lwz r4, 0(r30)
        lwz r5, 4(r30)
        lfs f1, 8(r30)
        bl vr_put
vcm_step:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne vcm_ret
        lwz r11, 4(r31)
        addi r11, r11, %(step)d
        stw r11, 4(r31)
        li r3, 2
vcm_ret:
        lmw r30, 0x18(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# --- user_entry's 0x3CA-0x3CD (from bv_zero: r31 WorkModule, r30 index, r29 write, the value at 0x18(r1); r27 r28
#     free): MSC's selection (ID index, value, owner) and the mask; anything else goes on as before --------------------
vr_var:
        cmplwi r30, %(vsel)d
        blt vv_zero
        cmplwi r30, %(vres)d
        bgt vv_zero
        lis r28, 0x%(data)X@ha
        addi r28, r28, 0x%(data)X@l
        cmpwi r29, 0
        beq vv_read
        lwz r0, %(busy)d(r28)           # not while an event writes (a reset list changed under it)
        cmpwi r0, 0
        bne vv_out
        lfs f1, 0x18(r1)
        cmplwi r30, %(vval)d
        bne vv_wint
        stfs f1, %(val)d(r28)
        b vv_out
vv_wint:
        bl 0x%(f2i)08X
        cmplwi r30, %(vsel)d
        bne vv_wown
        stw r3, %(sel)d(r28)
        b vv_out
vv_wown:
        cmplwi r30, %(vown)d
        bne vv_wmask
        stw r3, %(own)d(r28)
        b vv_out
vv_wmask:
        mr r27, r3
        bl vv_owner
        cmpwi r3, 0
        beq vv_out
        lwz r4, %(sel)d(r28)
        clrlwi r4, r4, 22
        oris r4, r4, 0x0F00
        mr r5, r27
        lfs f1, %(val)d(r28)
        bl vr_put
vv_out:
        b 0x%(ue_out)08X
vv_read:
        cmplwi r30, %(vval)d
        bne vv_rint
        lfs f1, %(val)d(r28)
        b vv_out
vv_rint:
        lwz r3, %(sel)d(r28)
        cmplwi r30, %(vsel)d
        beq vv_ri
        lwz r3, %(own)d(r28)
        cmplwi r30, %(vown)d
        beq vv_ri
        bl vv_owner                     # the selected item's mask
        cmpwi r3, 0
        beq vv_ri
        li r4, 0
        bl vr_blk
        cmpwi r3, 0
        beq vv_ri
        lwz r4, %(sel)d(r28)
        clrlwi r4, r4, 22
        oris r4, r4, 0x0F00
        bl vr_item
        cmpwi r3, 0
        beq vv_ri
        lwz r3, 8(r3)
vv_ri:
        bl 0x%(i2f)08X
        b vv_out
vv_zero:
        b 0x%(var_chain)08X

# vv_owner() -> r3 the selected owner's WorkModule or 0 (r31 the caller's WorkModule, r28 the data)
vv_owner:
        stwu r1, -0x10(r1)
        mflr r0
        stw r0, 0x14(r1)
        mr r3, r31
        bl 0x%(acc_of)08X""" % D + chk('r3', 'vo_no') + """
        lwz r4, %(own)d(r28)
        bl 0x%(nc_target)08X""" % D + chk('r3', 'vo_no') + """
        lwz r3, 0x28(r3)""" + chk('r3', 'vo_no') + """
        b vo_ret
vo_no:
        li r3, 0
vo_ret:
        lwz r0, 0x14(r1)
        mtlr r0
        addi r1, r1, 0x10
        blr

# --- the command tables' chain (acmd_ext_cave.py's not-found / past-its-commands paths) ----------------------------
vr_lookup:                              # lk_none: r3 a CRC no table has
        lis r12, 0x%(crc_h)X
        ori r12, r12, 0x%(crc_l)X
        cmplw r3, r12
        bne vl_none
        li r3, %(idx)d
        blr
vl_none:
        li r3, -1
        blr
vr_size1:                               # s1_orig: r3 the index, r10 = r3 x 4; r0 gets the size
        cmpwi r3, %(idx)d
        bne vz1_orig
        li r0, %(size)d
        b 0x%(s1back)08X
vz1_orig:
        lwzx r0, r10, r4
        b 0x%(s1back)08X
vr_size2:                               # s2_orig: r3 the index, r11 = r3 x 4; r12 gets the size
        cmpwi r3, %(idx)d
        bne vz2_orig
        li r12, %(size)d
        b 0x%(s2back)08X
vz2_orig:
        lwzx r12, r11, r30
        b 0x%(s2back)08X
vr_fetch:                               # f_orig: r7 the index; r0 gets the handler (r6 = r7 x 4 as before; r12 live)
        slwi r6, r7, 2
        cmpwi r7, %(idx)d
        bne vzf_orig
        lis r6, vr_cmd@ha               # (r6 is overwritten past fback: mr r6, r27)
        addi r0, r6, vr_cmd@l
        b 0x%(fback)08X
vzf_orig:
        lwzx r0, r6, r29
        b 0x%(fback)08X
""" % D


def build(orig):
    """orig(address) -> the word in the executable being patched. -> ({address: word}, labels)"""
    L = ext_labels()
    nv_slot = L['cmd_handlers'] + 4 * L['_newvar_index']
    gsh = L['gs_hit'] + HIT_OFF
    expect = {STATUS_AT: STATUS_WORD, SIT_AT: SIT_WORD, gsh: HIT_WORD, nv_slot: L['h_newvar'],
              L['lk_none']: 0x3860FFFF, L['s1_orig']: 0x7C0A202E, L['s2_orig']: 0x7D8BF02E,
              L['f_orig']: 0x54E6103A, L['f_orig'] + 4: 0x7C06E82E}
    for at, w in expect.items():
        assert orig(at) == w, 'not exe_v46v_threads: 0x%08X holds 0x%08X (0x%08X expected)' % (at, orig(at), w)
    reset_chain = b_target(RESET_AT, orig(RESET_AT))
    var_chain = b_target(L['bv_zero'], orig(L['bv_zero']))
    assert var_chain == L['ue_zero'], 'bv_zero no longer b ue_zero: 0x%08X' % var_chain
    a = Asm(VR_CODE)
    a.asm(source(L, reset_chain, var_chain))
    words = a.words()
    assert VR_CODE + 4 * len(words) <= VR_DATA, hex(VR_CODE + 4 * len(words))
    out = {VR_CODE + 4 * i: w for i, w in enumerate(words)}
    for x in list(out) + list(range(VR_DATA, VR_END, 4)):
        assert orig(x) == 0, 'cave word 0x%08X not free (0x%08X)' % (x, orig(x))
    out[STATUS_AT] = bw(STATUS_AT, a.addr('vr_chg'))
    out[SIT_AT] = bw(SIT_AT, a.addr('vr_sit'))
    out[gsh] = bw(gsh, a.addr('vr_hit'))
    out[RESET_AT] = bw(RESET_AT, a.addr('vr_wmreset'))
    out[nv_slot] = a.addr('vr_newvar')
    out[L['bv_zero']] = bw(L['bv_zero'], a.addr('vr_var'))
    out[L['lk_none']] = bw(L['lk_none'], a.addr('vr_lookup'))
    out[L['s1_orig']] = bw(L['s1_orig'], a.addr('vr_size1'))
    out[L['s2_orig']] = bw(L['s2_orig'], a.addr('vr_size2'))
    out[L['f_orig']] = bw(L['f_orig'], a.addr('vr_fetch'))
    labels = dict(a.labels, vr_data=VR_DATA, vr_tab=VR_TAB, reset_chain=reset_chain, var_chain=var_chain,
                  nv_slot=nv_slot, gs_hit_site=gsh)
    return out, labels


def rpx_reader(path):
    import rpx_patch as R
    d, _s, _e, secs = R.load(path)
    cache = {}

    def orig(addr):
        for i, s in enumerate(secs):
            if s[1] == 1 and s[3] and s[5]:
                if i not in cache:
                    cache[i] = R.section_data(d, s)
                data = cache[i]
                if s[3] <= addr < s[3] + len(data):
                    return struct.unpack('>I', data[addr - s[3]:addr - s[3] + 4])[0]
        if 0x04B00000 <= addr < VR_END:
            return 0                    # past the code section's end: zero once grown
        raise KeyError(hex(addr))
    return orig


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', required=True, help='the executable to patch (exe_v46v_threads)')
    args = p.parse_args()
    out, labels = build(rpx_reader(args.rpx))
    print(' '.join(['textregion:0x%X' % TEXT_REGION, 'grow:0x%08X' % VR_END] +
                   ['0x%08X=0x%08X' % kv for kv in sorted(out.items())]))
    sys.stderr.write('var_reset: %d words, %s 0x%08X index %d, code 0x%08X-0x%08X\n' % (
        len(out), CMD_NAME, CMD_CRC, VR_INDEX, VR_CODE, labels['vr_lookup']))


if __name__ == '__main__':
    main()
