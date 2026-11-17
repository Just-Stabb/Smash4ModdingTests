#!/usr/bin/env python3
"""Mesh_Visibility (model_commands v1, exe_v46z_outline): hide or show one of an object's meshes (model parts) by its
name, for the current animation or until changed, over the motion's own visibility animation and the visibility
groups (Model_Changer). Prints rpx_patch.py arguments for an executable with tools/outline_cave.py's patches
(exe_v46z_ol, or any later chain of the same caves); asserts every word it replaces.

  python3 tools/rpx_patch.py exe_v46z_ol.rpx exe_v46z_outline.rpx $(python3 tools/mesh_vis_cave.py --rpx exe_v46z_ol.rpx)
  python3 tools/mesh_vis_cave.py --labels tools/Sm4shCommand/param_labels.json     (Sm4shCommand's entry)

How Smash 4 shows a model's meshes (read from cross_f.rpx; docs/native-notes.md "Mesh visibility"):
  - A model instance (MI = [[accessor + 0x3C] + 0xC]: ModelModule, its handle +4, the handle's +8) keeps one byte per
    mesh at [[MI + 0x7DC] + 4] + index (the mesh count is [[MI + 0x6E4] + 0x44]): bits 0-1 the set state (0 hidden,
    1 shown, 2 follow the animation), bit 2 the animation's value, bits 4-7 last frame's result. 0x034232FC(MI, mesh,
    value, which) is the only writer: which 0 sets bits 0-1 (the visibility groups: VisibilityModule vt +0x4C ->
    0x03426140, Model_Changer / VIS_SET; by name 0x0342633C: what the game's own code uses), which 1 sets bit 2 (the
    motion's visibility animation, every frame). The instance's vt +0x74 (0x03424E88) turns them into what is drawn
    each frame: shown = bits 0-1 == 2 ? bit 2 : bits 0-1.
  - Mesh names: the model data's mesh objects ([MI + 0x6E4] + its +0x3C x 0x14: the resource; its vt +0xA4(res, i, 0)
    the mesh, the mesh's vt +0x2C its name), as 0x0342633C compares them (strcmp).
  So an override is bits 0-1 forced to 0 / 1 while it lasts (the animation's bit 2 then doesn't count), with the
  game's own writes to bits 0-1 kept aside (0x034232FC hooked: a group change during the override is what comes back
  after it) and the byte put back when it ends.

Command: Mesh_Visibility(Target, Mesh, Visible, Persist) (index MV_INDEX, CRC of the name), 5 words.
  Target   whose (acmd_ext's targets: 0 this object, ...).
  Mesh     the mesh: its name's CRC32 (Sm4shCommand: Mesh="stethoscope_VIS_O_OBJ" is hashed), or 0-255 a mesh index;
           -1: every override of this object ends (Visible / Persist unused).
  Visible  0 hide, 1 show, 2 end this mesh's override (the game's own state again).
  Persist  0 until the animation (the motion kind) changes, as vanilla visibility changes; 1 until changed, a KO, the
           match end or a training reset.
Every mesh whose name has that CRC is changed (names are unique in the game's models).

Hooks (each word asserted):
  SETVIS 0x034232FC  lwz r7, 0x6E4(r3)  (the mesh visibility setter) -> mv_set: a which-0 write to an overridden mesh
                     is kept aside (it comes back when the override ends); the rest as before
  TICK   0x032EFB78  bl (outline_cave.py's ol_tick) -> mv_tick: the earlier tick, then the overrides' frame (an override
                     of an object whose motion kind changed (Persist 0) or KO'd ends; the others written again)
  CLEAR  the clear-all chain's last `b 0x02FB349C` (outline_cave.py's ol_clear) -> mv_clear: every override ends (the
         byte put back while the object still has that model)
  LOOKUP / SIZE1 / SIZE2 / FETCH: chained in front of Outline_Set's.
  --diag: TEST ONLY OSReport lines (S4MC per command, S4MF per override and frame: the first 30 frames after a command,
  then every 30th).
Space: 0x04BE4000-0x04BE5000 (docs/native-notes.md "Mesh visibility": past the outline's, the text region grown).
Test: tools/mesh_vis_test.py (unicorn: the game's setter 0x034232FC, by-name setter 0x0342633C, the per-frame result
0x03424E88's decision, the tick, the handler, the tables).
"""
import argparse
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402
import line_test_cave as LT  # noqa: E402
import outline_cave as OL  # noqa: E402

CAVE, LIMIT = 0x04BE4000, 0x04BE5000
TEXT_REGION = LIMIT - 0x02000000
MV_INDEX = 2500
CMD_NAME = 'Mesh_Visibility'
CMD_CRC = zlib.crc32(CMD_NAME.encode()) & 0xFFFFFFFF
NPARAMS = 4
N_ENT, ENT = 32, 0x20

SETVIS = 0x034232FC             # (MI, mesh, value, which) -> r3 1 set / 0 not
SETVIS_SIG = (0x80E306E4, 0x81870044, 0x7C046040, 0x4080004C, 0x818307DC)
SETVIS_BACK = SETVIS + 4
BYNAME = 0x0342633C             # (MI, name, value, which): the game's by-name setter (the mesh walk this cave copies)
BYNAME_SIG = {0x0342635C: 0x813C06E4, 0x03426360: 0x8009003C, 0x03426364: 0x83690044, 0x03426368: 0x1D400014,
              0x03426380: 0x800C00A4, 0x0342639C: 0x80C8002C}
APPLY = 0x03424E88              # the instance's vt +0x74: what is drawn
VIS_ARR, MDATA = 0x7DC, 0x6E4
MOTION_ACC, MOTION_KIND = 0x44, 0x38
DIAG_EVERY = 30


def crc32(name):
    return zlib.crc32(name.encode()) & 0xFFFFFFFF


NEW_CMDS = [
    (CMD_NAME, 'h_meshvis', [
        ('Target', 0, OL._T),
        ('Mesh', 0, 'The mesh (model part): its name in quotes, e.g. Mesh="stethoscope_VIS_O_OBJ" (Sm4shCommand stores '
                    'its CRC32; the Hitbox Viewer\'s Model parts tab lists the names), or 0-255 a mesh index. -1: '
                    'every Mesh_Visibility override of this object ends.'),
        ('Visible', 0, '0 hide it, 1 show it, 2 end this mesh\'s override (the motion\'s visibility animation and the '
                       'visibility groups decide again).'),
        ('Persist', 0, '0: until the animation changes (as Model_Changer and the motion\'s own visibility); 1: until '
                       'changed, a KO, the match end or a training reset.')],
     'Hides or shows one of an object\'s meshes by name, for this animation or until changed, over the motion\'s '
     'visibility animation and the visibility groups. New command: needs the patched cross_f.rpx '
     '(tools/mesh_vis_cave.py, exe_v46z_outline).'),
]


def find(orig):
    s = OL.table_find(orig, CAVE, LIMIT)
    for i, want in enumerate(SETVIS_SIG):
        assert orig(SETVIS + 4 * i) == want, 'setter 0x%08X: 0x%08X, not 0x%08X' % (
            SETVIS + 4 * i, orig(SETVIS + 4 * i), want)
    for at, want in BYNAME_SIG.items():
        assert orig(at) == want, '0x%08X: 0x%08X, not 0x%08X' % (at, orig(at), want)
    for i, want in enumerate(OL.NC_TARGET_SIG):
        assert orig(OL.NC_TARGET + 4 * i) == want, 'nc_target 0x%08X' % (OL.NC_TARGET + 4 * i)
    s['tick_prev'] = OL.tick_prev(orig)
    assert not CAVE <= s['tick_prev'] < LIMIT, 'already patched (tick)'
    assert OL.CAVE <= s['tick_prev'] < OL.LIMIT, 'tick: want outline_cave.py\'s ol_tick (exe_v46z_ol)'
    s['clear_at'] = OL.clear_tail(orig)
    assert not CAVE <= s['clear_at'] < LIMIT, 'already patched (clear)'
    return s


DIAG_FMTS = [
    ('s_mc', 'S4MC tgt=%d mesh=%08X vis=%d per=%d acc=%08X mi=%08X hit=%d\n'),
    ('s_mf', 'S4MF n=%d k=%d mesh=%d byte=%02X forced=%d per=%d kind=%d\n'),
]


def src(s, hand, diag=False):
    D = dict(step=4 * (1 + NPARAMS), n=N_ENT, ent=ENT, nct=OL.NC_TARGET, tick_prev=s['tick_prev'],
             clear_to=OL.CLEAR_BACK, smvt_h=OL.FIGHTER_SM_VT >> 16, smvt_l=OL.FIGHTER_SM_VT & 0xFFFF, dead=OL.DEAD,
             back=SETVIS_BACK, va=VIS_ARR, md=MDATA, macc=MOTION_ACC, mkind=MOTION_KIND)
    chk, mi_of = OL.chk, OL.mi_of
    out = OL.table_src(s, 'mv', MV_INDEX, CMD_CRC, 1 + NPARAMS, hand)
    out += """
# --- Mesh_Visibility(Target, Mesh, Visible, Persist): (r3 accessor, r5 script state, r6 (+8 execute), r7 parameters)
# entry (0x%(ent)X): +0 accessor (0 free), +4 instance, +8 mesh index, +0xC forced (0 / 1), +0x10 the game's bits 0-1,
# +0x14 Persist, +0x18 the motion kind at the command
h_meshvis:
        stwu r1, -0x50(r1)
        mflr r0
        stw r0, 0x54(r1)
        stmw r22, 0x28(r1)
        mr r31, r5
        mr r30, r7
        mr r29, r3
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq mv_step
        lis r12, mv_g@ha
        addi r12, r12, mv_g@l
        lwz r11, 0xC(r12)               # commands run
        addi r11, r11, 1
        stw r11, 0xC(r12)
        li r0, 0
        stw r0, 0x10(r12)               # (diag: frames since)
        stw r0, 0x14(r12)               # meshes this command changed
        mr r3, r29
        lwz r4, 0(r30)                  # Target
        bl 0x%(nct)08X
        mr. r28, r3
        beq mv_step""" % D + mi_of('r28', 'r27', 'mv_step') + """
        lwz r0, 4(r30)                  # Mesh -1: every override of this object ends
        cmpwi r0, -1
        bne mv_one
        mr r3, r28
        bl mv_rel_obj
        b mv_done
mv_one:
        lwz r12, %(va)d(r27)""" % D + chk('r12', 'mv_step') + """
        lwz r12, 4(r12)""" + chk('r12', 'mv_step') + """
        lwz r26, %(md)d(r27)""" % D + chk('r26', 'mv_step') + """
        lwz r25, 0x44(r26)              # the mesh count
        lwz r0, 4(r30)
        cmplwi r0, 256
        bge mv_hash
        cmplw r0, r25                   # a mesh index
        bge mv_done
        mr r3, r0
        bl mv_apply
        b mv_done
mv_hash:                                # a name's CRC32: every mesh whose name has it (0x0342633C's walk)
        lwz r0, 0x3C(r26)
        mulli r0, r0, 0x14
        lwzx r24, r26, r0""" + chk('r24', 'mv_done') + """
        li r23, 0
mvh_loop:
        cmplw r23, r25
        bge mv_done
        lwz r12, 0(r24)
        lwz r0, 0xA4(r12)
        mtctr r0
        mr r3, r24
        mr r4, r23
        li r5, 0
        bctrl""" + chk('r3', 'mvh_next') + """
        lwz r12, 0(r3)
        lwz r0, 0x2C(r12)
        mtctr r0
        bctrl""" + chk('r3', 'mvh_next') + """
        bl mv_crc
        lwz r0, 4(r30)
        cmplw r3, r0
        bne mvh_next
        mr r3, r23
        bl mv_apply
mvh_next:
        addi r23, r23, 1
        b mvh_loop
mv_done:
        bl mv_count
        mr r3, r30
        mr r4, r28
        mr r5, r27
        bl mv_dcmd                      # (diag build: S4MC; else a blr)
mv_step:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne mv_ret
        lwz r11, 4(r31)
        addi r11, r11, %(step)d
        stw r11, 4(r31)
        li r3, 2
mv_ret:
        lmw r22, 0x28(r1)
        lwz r0, 0x54(r1)
        mtlr r0
        addi r1, r1, 0x50
        blr

# mv_apply(r3 mesh index; r28 accessor, r27 instance, r30 the parameters): this mesh's override set / ended
mv_apply:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        lis r12, mv_g@ha
        addi r12, r12, mv_g@l
        lwz r11, 0x14(r12)
        addi r11, r11, 1
        stw r11, 0x14(r12)
        lis r12, mv_tab@ha
        addi r12, r12, mv_tab@l
        li r11, %(n)d
        li r10, 0
mva_loop:
        lwz r0, 0(r12)
        cmpwi r0, 0
        bne mva_used
        cmpwi r10, 0
        bne mva_next
        mr r10, r12
        b mva_next
mva_used:
        cmplw r0, r28
        bne mva_next
        lwz r0, 4(r12)
        cmplw r0, r27
        bne mva_next
        lwz r0, 8(r12)
        cmplw r0, r3
        beq mva_have
mva_next:
        addi r12, r12, %(ent)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne mva_loop
        lwz r0, 8(r30)                  # none yet: Visible 2 ends nothing; no free entry: nothing
        cmpwi r0, 2
        beq mva_out
        cmpwi r10, 0
        beq mva_out
        mr r12, r10
        lwz r9, %(va)d(r27)             # the game's bits 0-1, kept for the end
        lwz r9, 4(r9)
        lbzx r0, r9, r3
        clrlwi r0, r0, 30
        stw r0, 0x10(r12)
        stw r28, 0(r12)
        stw r27, 4(r12)
        stw r3, 8(r12)
mva_have:
        lwz r0, 8(r30)
        cmpwi r0, 2
        bne mva_set
        mr r3, r12
        bl mv_release
        b mva_out
mva_set:
        li r9, 0                        # forced: Visible 0 hides, anything else shows
        cmpwi r0, 0
        beq mva_f
        li r9, 1
mva_f:
        stw r9, 0xC(r12)
        lwz r0, 0xC(r30)                # Persist (0 / 1)
        li r9, 0
        cmpwi r0, 0
        beq mva_p
        li r9, 1
mva_p:
        stw r9, 0x14(r12)
        lwz r9, %(macc)d(r28)           # the motion kind now (MotionModule +0x%(mkind)X; none: -1)""" % D + \
        chk('r9', 'mva_nok') + """
        lwz r9, %(mkind)d(r9)
        b mva_k
mva_nok:
        li r9, -1
mva_k:
        stw r9, 0x18(r12)
        mr r3, r12
        bl mv_force
mva_out:
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# mv_force(r3 entry): its mesh's bits 0-1 = the forced state. Leaf: r0 r9-r12
mv_force:
        lwz r12, 4(r3)
        lwz r12, %(va)d(r12)
        lwz r12, 4(r12)
        lwz r11, 8(r3)
        lbzx r0, r12, r11
        rlwinm r0, r0, 0, 0, 29
        lwz r10, 0xC(r3)
        or r0, r0, r10
        stbx r0, r12, r11
        blr

# mv_release(r3 entry): the game's bits 0-1 back, the entry freed. Leaf: r0 r9-r12
mv_release:
        lwz r12, 4(r3)
        lwz r12, %(va)d(r12)
        lwz r12, 4(r12)
        lwz r11, 8(r3)
        lbzx r0, r12, r11
        rlwinm r0, r0, 0, 0, 29
        lwz r10, 0x10(r3)
        or r0, r0, r10
        stbx r0, r12, r11
        li r0, 0
        stw r0, 0(r3)
        blr

# mv_rel_obj(r3 accessor): every override of that object ends
mv_rel_obj:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stmw r29, 0x14(r1)
        mr r31, r3
        lis r30, mv_tab@ha
        addi r30, r30, mv_tab@l
        li r29, %(n)d
mvo_loop:
        lwz r0, 0(r30)
        cmplw r0, r31
        bne mvo_next
        mr r3, r30
        bl mv_release
mvo_next:
        addi r30, r30, %(ent)d
        addi r29, r29, -1
        cmpwi r29, 0
        bne mvo_loop
        lmw r29, 0x14(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# mv_crc(r3 a C string) -> r3 its CRC32 (zlib's). Leaf: r0 r9-r12
mv_crc:
        li r12, -1
        lis r9, 0xEDB8
        ori r9, r9, 0x8320
mvc_byte:
        lbz r0, 0(r3)
        cmpwi r0, 0
        beq mvc_end
        addi r3, r3, 1
        xor r12, r12, r0
        li r11, 8
mvc_bit:
        andi. r10, r12, 1
        srwi r12, r12, 1
        beq mvc_nb
        xor r12, r12, r9
mvc_nb:
        addi r11, r11, -1
        cmpwi r11, 0
        bne mvc_bit
        b mvc_byte
mvc_end:
        li r0, -1
        xor r3, r12, r0
        blr

# mv_count: mv_g +0 = entries in use. r0 r9-r12
mv_count:
        lis r12, mv_tab@ha
        addi r12, r12, mv_tab@l
        li r11, %(n)d
        li r9, 0
mvn_loop:
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq mvn_next
        addi r9, r9, 1
mvn_next:
        addi r12, r12, %(ent)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne mvn_loop
        lis r12, mv_g@ha
        stw r9, mv_g@l(r12)
        blr

# --- mv_set: the mesh visibility setter's first word (0x034232FC: r3 MI, r4 mesh, r5 value, r6 which; a leaf): a
#     which-0 write to an overridden mesh is kept aside for its end (r3 1, as a set), the rest as before ------------
mv_set:
        lis r12, mv_g@ha
        lwz r0, mv_g@l(r12)
        cmpwi r0, 0
        beq mvs_go
        cmpwi r6, 0
        bne mvs_go
        lis r12, mv_tab@ha
        addi r12, r12, mv_tab@l
        li r11, %(n)d
mvs_loop:
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq mvs_next
        lwz r0, 4(r12)
        cmplw r0, r3
        bne mvs_next
        lwz r0, 8(r12)
        cmplw r0, r4
        bne mvs_next
        clrlwi r0, r5, 30
        stw r0, 0x10(r12)
        lis r12, mv_g@ha
        addi r12, r12, mv_g@l
        lwz r11, 0x18(r12)              # writes kept aside
        addi r11, r11, 1
        stw r11, 0x18(r12)
        li r3, 1
        blr
mvs_next:
        addi r12, r12, %(ent)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne mvs_loop
mvs_go:
        lwz r7, %(md)d(r3)
        b 0x%(back)08X

# --- mv_tick: bl from 0x032EFB78 (r3 the screen-effect manager): the earlier tick, then the overrides' frame ---------
mv_tick:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        bl 0x%(tick_prev)08X
        bl mv_frame
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

mv_frame:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r28, 0x20(r1)
        lis r12, mv_g@ha
        addi r12, r12, mv_g@l
        lwz r11, 4(r12)
        addi r11, r11, 1
        stw r11, 4(r12)
        lwz r11, 0x10(r12)
        addi r11, r11, 1
        stw r11, 0x10(r12)
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq mvf_out
        lis r31, mv_tab@ha
        addi r31, r31, mv_tab@l
        li r30, %(n)d
mvf_loop:
        lwz r29, 0(r31)
        cmpwi r29, 0
        beq mvf_next""" % D + mi_of('r29', 'r28', 'mvf_drop') + """
        lwz r0, 4(r31)                  # the object's model changed: dropped (that model isn't its own any more)
        cmplw r0, r28
        bne mvf_drop
        lwz r12, %(va)d(r28)""" % D + chk('r12', 'mvf_drop') + """
        lwz r12, 4(r12)""" + chk('r12', 'mvf_drop') + """
        lwz r12, 0x20(r29)              # a fighter KO'd: ends""" + chk('r12', 'mvf_live') + """
        lwz r11, 0(r12)
        lis r10, %(smvt_h)d
        ori r10, r10, %(smvt_l)d
        cmplw r11, r10
        bne mvf_live
        lwz r11, 0x48(r12)
        cmpwi r11, %(dead)d
        beq mvf_rel
mvf_live:
        lwz r0, 0x14(r31)               # Persist 0: ends when the motion kind changes
        cmpwi r0, 0
        bne mvf_keep
        lwz r12, %(macc)d(r29)""" % D + chk('r12', 'mvf_keep') + """
        lwz r12, %(mkind)d(r12)
        lwz r0, 0x18(r31)
        cmpw r12, r0
        bne mvf_rel
mvf_keep:
        mr r3, r31                      # written again (anything that went round the setter)
        bl mv_force
        mr r3, r31
        li r4, %(n)d
        subf r4, r30, r4
        bl mv_dtick                     # (diag: S4MF)
        b mvf_next
mvf_rel:
        mr r3, r31
        bl mv_release
        b mvf_next
mvf_drop:
        li r0, 0
        stw r0, 0(r31)
mvf_next:
        addi r31, r31, %(ent)d
        addi r30, r30, -1
        cmpwi r30, 0
        bne mvf_loop
        bl mv_count
mvf_out:
        lmw r28, 0x20(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- mv_clear: the clear-all chain (training reset, restart, match start / end; a leaf: r3 / r10 / LR kept, r0 r4-r9
#     r11 r12 free): every override ends, the byte put back while the object still has that model ------------------
mv_clear:
        lis r12, mv_tab@ha
        addi r12, r12, mv_tab@l
        li r11, %(n)d
mvx_loop:
        lwz r9, 0(r12)
        cmpwi r9, 0
        beq mvx_next""" % D + mi_of('r9', 'r8', 'mvx_free') + """
        lwz r0, 4(r12)
        cmplw r0, r8
        bne mvx_free
        lwz r8, %(va)d(r8)""" % D + chk('r8', 'mvx_free') + """
        lwz r8, 4(r8)""" + chk('r8', 'mvx_free') + """
        lwz r7, 8(r12)
        lbzx r0, r8, r7
        rlwinm r0, r0, 0, 0, 29
        lwz r6, 0x10(r12)
        or r0, r0, r6
        stbx r0, r8, r7
mvx_free:
        li r0, 0
        stw r0, 0(r12)
mvx_next:
        addi r12, r12, %(ent)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne mvx_loop
        li r0, 0
        lis r12, mv_g@ha
        stw r0, mv_g@l(r12)
        b 0x%(clear_to)08X
""" % D
    if diag:
        out += _diag_src()
    else:
        out += """
mv_dcmd:
mv_dtick:
        blr
"""
    out += """
mv_g:                                   # +0 entries in use, +4 frames ticked, +0xC commands, +0x10 frames since the last
        .word 0                         # command (diag), +0x14 meshes the last command changed, +0x18 setter writes
        .word 0                         # kept aside
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
mv_tab:
""" + '        .word 0\n' * (N_ENT * ENT // 4) + (_diag_data() if diag else '')
    return out


def _diag_src():
    import diag_godfist_cave as G
    rep = """
        lis r12, 0x%X
        ori r12, r12, 0x%X
        mtctr r12
        .word 0x%08X
        bctrl""" % (G.OSREPORT_VENEER >> 16, G.OSREPORT_VENEER & 0xFFFF, G.CRCLR_CR1EQ)
    return """
# --- diag: S4MC at every command (r3 parameters, r4 target accessor, r5 instance) -----------------------------------
mv_dcmd:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r29, 0x24(r1)
        mr r31, r3
        mr r9, r5
        mr r8, r4
        lis r3, s_mc@ha
        addi r3, r3, s_mc@l
        lwz r4, 0(r31)
        lwz r5, 4(r31)
        lwz r6, 8(r31)
        lwz r7, 0xC(r31)
        lis r12, mv_g@ha
        addi r12, r12, mv_g@l
        lwz r10, 0x14(r12)""" + rep + """
        lmw r29, 0x24(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- diag: S4MF per override and frame (r3 entry, r4 its number) ------------------------------------------------------
mv_dtick:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r29, 0x24(r1)
        mr r31, r3
        mr r30, r4
        lis r12, mv_g@ha
        addi r12, r12, mv_g@l
        lwz r11, 0x10(r12)
        cmpwi r11, %(e)d
        blt mdt_log
        li r9, %(e)d
        divwu r8, r11, r9
        mullw r8, r8, r9
        cmpw r8, r11
        bne mdt_out
mdt_log:
        lwz r12, 4(r31)
        lwz r12, %(va)d(r12)
        lwz r12, 4(r12)
        lwz r6, 8(r31)
        lbzx r7, r12, r6
        lis r3, s_mf@ha
        addi r3, r3, s_mf@l
        lis r12, mv_g@ha
        addi r12, r12, mv_g@l
        lwz r4, 4(r12)
        mr r5, r30
        lwz r8, 0xC(r31)
        lwz r9, 0x14(r31)
        lwz r10, 0x18(r31)""" % dict(e=DIAG_EVERY, va=VIS_ARR) + rep + """
mdt_out:
        lmw r29, 0x24(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
"""


def _diag_data():
    out = ''
    for lab, fmt in DIAG_FMTS:
        out += '%s:\n' % lab + OL._words(fmt)
    return out


def build(orig, diag=False):
    s = find(orig)
    hand = 0
    for _p in range(2):
        a = Asm(CAVE)
        a.asm(src(s, hand, diag))
        hand = a.addr('h_meshvis')
    words = a.words()
    end = CAVE + 4 * len(words)
    assert end <= LIMIT, 'cave too big: 0x%08X' % end
    for x in range(CAVE, LIMIT, 4):
        assert orig(x) == 0, 'cave word 0x%08X not free' % x
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    out.update(OL.table_words(s, a, 'mv'))
    out[SETVIS] = LT.branch(SETVIS, a.addr('mv_set'))
    out[OL.TICK_AT] = LT.branch(OL.TICK_AT, a.addr('mv_tick')) | 1
    out[s['clear_at']] = LT.branch(s['clear_at'], a.addr('mv_clear'))
    return out, a.labels, s


def rpx_reader(path):
    return OL.rpx_reader(path, CAVE, LIMIT)


def labels(path):
    OL.labels(path, NEW_CMDS)


def present(img_w):
    return OL.present(img_w, CMD_CRC, CAVE)


def shown(byte):
    """what the game draws from a mesh's byte (0x03424E88's rule; Python reference)"""
    v = byte & 3
    return bool((byte >> 2) & 1) if v == 2 else bool(v)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', help='the executable to patch (exe_v46z_ol: outline_cave.py\'s, or later)')
    p.add_argument('--labels', help='update this param_labels.json with Mesh_Visibility')
    p.add_argument('--diag', action='store_true', help='TEST ONLY: the OSReport build (S4MC / S4MF lines)')
    args = p.parse_args()
    if args.labels:
        labels(args.labels)
        return
    if not args.rpx:
        p.error('--rpx or --labels')
    words, lab, _s = build(rpx_reader(args.rpx), args.diag)
    print(' '.join(['textregion:0x%X' % TEXT_REGION, 'grow:0x%08X' % LIMIT] +
                   ['0x%08X=0x%08X' % kv for kv in sorted(words.items())]))
    sys.stderr.write('mesh visibility: %d words, Mesh_Visibility index %d (0x%08X), h_meshvis 0x%08X, mv_set 0x%08X, '
                     'end 0x%08X\n' % (len(words), MV_INDEX, CMD_CRC, lab['h_meshvis'], lab['mv_set'],
                                       max(a for a in words if a >= CAVE) + 4))


if __name__ == '__main__':
    main()
