#!/usr/bin/env python3
"""TEMPORARY diagnostic executable for Smash Run step 2n (the step 2i crash "a bit after Ghos spawned", the Big
Goomba / Paratroopa stomp, the Paratroopa's wings): OSReport lines from the spawner, the cave enemies' state changes,
the mesh switch and the game's mesh-list rebuild, so Cemu's log shows the last things that happened before a crash or
a freeze. Not for the normal chain build. Prints rpx_patch.py arguments (hooks found on the executable given: exe_v31).

  python3 tools/rpx_patch.py exe_v31.rpx OUT.rpx $(python3 tools/diag_step2n_cave.py --rpx exe_v31.rpx [--novis])

--novis also turns the mesh switch off (h_vis / h_whole return at once: every mesh of the step 2i models drawn, as
before step 2i): the A/B build for "is the mesh switch the crash".

Lines (`S4N <tag> ...`, hex words; floats as their bits), each tag with its own cap (MAXES) so a busy tag can't use up
the others':
  hb    every 60th spawner call (once a frame on a Smash Run stage, field cave 0x04B7D28C): n, the manager. If the game
        freezes the heartbeat stops; if Cemu crashes it shows how long after the last other line.
  sp    a spawn (0x04B7D4A8, before 0x02D9BCFC(mgr, &param)): param +0 / +4 / +0x20 / +0x24 (kind, variation, ...).
  st    a cave enemy's state change request (the vtable slot 72 / 73 wrappers, 0x04B86E1C): kind, variation, state,
        new state, the function (0x026A3A44 change_state / 0x026A3AD4 change_state_interrupt), this.
  vis   a mesh switch that changes a mesh (h_vis before set_mesh_visibility_by_index, 0x04BC42E0): mesh, kind, old
        bits (0xEE: the mesh index is past the model's count), new, the model, its mesh count.
  whole h_whole (0x04BC43B8): kind, value, this.
  rb    the game's mesh-list rebuild after a visibility change (0x03424F74, in the model's per-update pass 0x03424E88):
        the model, the visible count, its command list (+0x7EC), the list (+0x7F0).
  mot   every 30th update of a Paratroopa / Koopa (w_upd 0x04B84900): state, MotionModule +0x38 (the motion),
        +0x3C (its frame), +0x50 (rate), variation.
  near  a fighter within 20 x and -10..40 y of a Big Goomba / Paratroopa in the stomp test (u_body 0x04BB808C): kind,
        state, fighter x / y, enemy x / y.
  hit   a stomp taken (0x04BB8134): kind, state, the fighter slot.
OSReport through the game's veneer 0x0288B4D4 (as tools/diag_stomp_cave.py); each stub saves r0, r2-r12, LR, CTR,
XER, CR and f0-f13, then replays the word it replaced. Space: 0x04BCC000-0x04BCE000 (zero in exe_v31, region H's
unused tail).
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

CAVE, LIMIT = 0x04BCC000, 0x04BCE000
OSREPORT_VENEER = 0x0288B4D4
VENEER_WORDS = (0x9421FFF0, 0x93E1000C, None, None, 0x7FE903A6, 0x83E1000C, 0x38210010, 0x4E800420)
CRCLR_CR1EQ = 0x4CC63182
MFXER, MTXER, MFCTR = 0x7C0102A6, 0x7C0103A6, 0x7C0902A6
FRAME = 0xC0
LR_S, CTR_S, XER_S, CR_S, FPR_S = 0x40, 0x44, 0x48, 0x4C, 0x50
FIGHTER_ENTRY = 0x76B0
MOT_FRAME = 0x3C
H_VIS, H_WHOLE = 0x04BC4260, 0x04BC43B8          # exe_v31's (checked: their first words)
H_VIS_WORD, H_WHOLE_WORD = 0x9421FFE0, 0x80630000
BLR = 0x4E800020


def SLOT(n):
    return 0x10 if n == 0 else 0x14 + 4 * (n - 2)


# (tag, address, the word there in exe_v31, cap, names, body: r4.. = the line's values, `skip` when no line)
HOOKS = [
    ('hb', 0x04B7D28C, 0x7C0802A6, 3000, ('n', 'mgr'), """
        lis r12, cnt@ha
        lwz r11, cnt@l(r12)
        addi r11, r11, 1
        stw r11, cnt@l(r12)
        li r10, 60
        divwu r9, r11, r10
        mullw r9, r9, r10
        subf r9, r9, r11
        cmpwi r9, 1
        bne skip
        mr r4, r11
        lwz r5, %d(r1)
    """ % SLOT(3)),
    ('sp', 0x04B7D4A8, 0x38810020, 400, ('a', 'b', 'c', 'd'), """
        addi r12, r1, %d
        lwz r4, 0(r12)
        lwz r5, 4(r12)
        lwz r6, 0x20(r12)
        lwz r7, 0x24(r12)
    """ % (FRAME + 0x20)),
    ('st', 0x04B86E1C, 0x81830168, 4000, ('k', 'v', 's', 'n', 'f', 'o'), """
        lwz r9, %d(r1)
        lwz r4, 8(r9)
        lwz r5, 0xC(r9)
        lwz r6, 4(r9)
        lwz r7, %d(r1)
        lwz r8, %d(r1)
    """ % (SLOT(3), SLOT(4), SLOT(11))),
    ('vis', 0x04BC42E0, 0x387F0004, 1500, ('m', 'k', 'o', 'v', 'mdl', 'n'), """
        lwz r9, 0xC(r31)
        cmpwi r9, 0
        beq skip
        lwz r10, 0x6E4(r9)
        cmpwi r10, 0
        beq skip
        lwz r10, 0x44(r10)
        lwz r4, %(S4)d(r1)
        li r6, 0xEE
        cmplw r4, r10
        bge v_out
        lwz r11, 0x7DC(r9)
        cmpwi r11, 0
        beq skip
        lwz r11, 4(r11)
        lbzx r6, r11, r4
        clrlwi r6, r6, 30
        cmpw r6, r30
        beq skip
    v_out:
        lwz r8, %(BEH)d(r1)
        lwz r5, 8(r8)
        mr r7, r30
        mr r8, r9
        mr r9, r10
    """ % dict(S4=SLOT(4), BEH=FRAME + 0x1C)),
    ('whole', 0x04BC43B8, 0x80630000, 300, ('k', 'v', 'o'), """
        lwz r6, %d(r1)
        lwz r4, 8(r6)
        lwz r5, %d(r1)
    """ % (SLOT(3), SLOT(4))),
    ('rb', 0x03424F74, 0x807F07EC, 1500, ('mdl', 'n', 'cl', 'lst'), """
        mr r4, r31
        mr r5, r30
        lwz r6, 0x7EC(r31)
        lwz r7, 0x7F0(r31)
    """),
    ('mot', 0x04B84900, 0x9421FFA0, 1500, ('s', 'm', 'fr', 'rt', 'v'), """
        lwz r9, %(S3)d(r1)
        lwz r0, 8(r9)
        cmpwi r0, 3
        bne skip
        lis r12, mcnt@ha
        lwz r11, mcnt@l(r12)
        addi r11, r11, 1
        stw r11, mcnt@l(r12)
        li r10, 30
        divwu r8, r11, r10
        mullw r8, r8, r10
        subf r8, r8, r11
        cmpwi r8, 1
        bne skip
        lwz r10, 0(r9)
        lwz r10, 0x30F0(r10)
        cmpwi r10, 0
        beq skip
        lwz r4, 4(r9)
        lwz r5, 0x38(r10)
        lwz r6, %(MF)d(r10)
        lwz r7, 0x50(r10)
        lwz r8, 0xC(r9)
    """ % dict(S3=SLOT(3), MF=MOT_FRAME)),
    ('near', 0x04BB808C, 0x819A0000, 2000, ('k', 's', 'fx', 'fy', 'ex', 'ey'), """
        lwz r9, 8(r31)
        cmpwi r9, 3
        beq n_ok
        cmpwi r9, 0x23
        bne skip
    n_ok:
        lwz r12, 0(r26)
        mulli r11, r25, %(ENT)d
        add r12, r12, r11
        lbz r11, 0x1E(r12)
        cmplwi r11, 4
        blt skip
        lwz r11, 0xC(r12)
        lwz r11, 0x18(r11)
        lis r12, consts@ha
        addi r12, r12, consts@l
        lfs f1, 0x10(r11)
        lfs f2, 0x10(r28)
        fsubs f3, f1, f2
        fabs f3, f3
        lfs f0, 0(r12)
        fcmpu cr0, f3, f0
        bgt skip
        lfs f4, 0x14(r11)
        lfs f5, 0x14(r28)
        fsubs f6, f4, f5
        lfs f0, 4(r12)
        fcmpu cr0, f6, f0
        blt skip
        lfs f0, 8(r12)
        fcmpu cr0, f6, f0
        bgt skip
        mr r4, r9
        lwz r5, 4(r31)
        stfs f1, 8(r1)
        lwz r6, 8(r1)
        stfs f4, 8(r1)
        lwz r7, 8(r1)
        stfs f2, 8(r1)
        lwz r8, 8(r1)
        stfs f5, 8(r1)
        lwz r9, 8(r1)
    """ % dict(ENT=FIGHTER_ENTRY)),
    ('hit', 0x04BB8134, 0x7FE3FB78, 300, ('k', 's', 'sl'), """
        lwz r4, 8(r31)
        lwz r5, 4(r31)
        mr r6, r25
    """),
]


def word(op):
    return '.word 0x%08X' % op


def branch(src, dst):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0, (hex(src), hex(dst))
    return (18 << 26) | (off & 0x3FFFFFC)


def fmt_bytes(tag, names):
    return ('S4N %s ' % tag + ' '.join('%s=%%X' % k for k in names) + '\n').encode() + b'\0'


def build(orig):
    """(words, labels, hooks {address: word}); orig(address) -> the executable's word"""
    a = Asm(CAVE)
    a.asm("""
    report:
        mflr r0
        stw r0, 4(r1)
        stwu r1, -0x20(r1)
        lis r12, 0x%(vh)X
        ori r12, r12, 0x%(vl)X
        mtctr r12
        %(crclr)s
        bctrl
        addi r1, r1, 0x20
        lwz r0, 4(r1)
        mtlr r0
        blr
    """ % dict(vh=OSREPORT_VENEER >> 16, vl=OSREPORT_VENEER & 0xFFFF, crclr=word(CRCLR_CR1EQ)))
    save = ['stwu r1, -0x%X(r1)' % FRAME, 'stw r0, %d(r1)' % SLOT(0)]
    save += ['stw r%d, %d(r1)' % (n, SLOT(n)) for n in range(2, 13)]
    save += ['mflr r0', 'stw r0, %d(r1)' % LR_S, word(MFCTR), 'stw r0, %d(r1)' % CTR_S, word(MFXER),
             'stw r0, %d(r1)' % XER_S, 'mfcr r0', 'stw r0, %d(r1)' % CR_S]
    save += ['stfd f%d, %d(r1)' % (n, FPR_S + 8 * n) for n in range(14)]
    rest = ['lfd f%d, %d(r1)' % (n, FPR_S + 8 * n) for n in range(14)]
    rest += ['lwz r0, %d(r1)' % CR_S, 'mtcrf 0xFF, r0', 'lwz r0, %d(r1)' % XER_S, word(MTXER),
             'lwz r0, %d(r1)' % CTR_S, 'mtctr r0', 'lwz r0, %d(r1)' % LR_S, 'mtlr r0']
    rest += ['lwz r%d, %d(r1)' % (n, SLOT(n)) for n in range(2, 13)]
    rest += ['lwz r0, %d(r1)' % SLOT(0), 'addi r1, r1, 0x%X' % FRAME]
    hooks = {}
    for i, (tag, at, w0, cap, _names, body) in enumerate(HOOKS):
        w = orig(at)
        assert w == w0, '%s: 0x%08X is 0x%08X, expected 0x%08X' % (tag, at, w, w0)
        assert w >> 26 not in (16, 18, 19), 'a branch at 0x%08X' % at
        b = body
        for lab in ('skip', 'v_out', 'n_ok'):
            b = b.replace(lab, '%s%d' % (lab, i))
        a.asm('hook%d:' % i)
        a.asm('\n'.join(save))
        a.asm("""
        lis r12, lines@ha
        addi r12, r12, lines@l
        lwz r11, %d(r12)
        cmplwi r11, %d
        bge skip%d
        """ % (4 * i, cap, i))
        a.asm(b)
        a.asm("""
        lis r12, lines@ha
        addi r12, r12, lines@l
        lwz r11, %d(r12)
        addi r11, r11, 1
        stw r11, %d(r12)
        lis r3, fmt%d@ha
        addi r3, r3, fmt%d@l
        bl report
    skip%d:
        """ % (4 * i, 4 * i, i, i, i))
        a.asm('\n'.join(rest))
        a.asm('%s\nb 0x%X' % (word(w), at + 4))
        hooks[at] = i
    a.asm('consts:\n.float 20.0\n.float -10.0\n.float 40.0')
    a.asm('lines:\n' + '\n'.join('.word 0' for _ in HOOKS))
    a.asm('cnt:\n.word 0\nmcnt:\n.word 0')
    pos = a.pc
    out = bytearray()
    for i, (tag, _at, _w, _c, names, _b) in enumerate(HOOKS):
        a.labels['fmt%d' % i] = pos + len(out)
        out += fmt_bytes(tag, names)
        while len(out) % 4:
            out += b'\0'
    code = a.words()
    words = code + list(struct.unpack('>%dI' % (len(out) // 4), bytes(out)))
    assert CAVE + 4 * len(words) <= LIMIT, 'cave full'
    hk = {at: branch(at, a.labels['hook%d' % i]) for at, i in hooks.items()}
    return words, dict(a.labels), hk


def args(rpx, novis=False):
    import smashrun_enemy_cave as E
    img = E.Image(rpx)
    used = [x for x in range(CAVE, LIMIT, 4) if img.u32(x)]
    assert not used, 'the diagnostic cave space is in use in %s (0x%08X)' % (rpx, used[0])
    vw = [img.u32(OSREPORT_VENEER + 4 * i) for i in range(len(VENEER_WORDS))]
    assert all(w == x for w, x in zip(vw, VENEER_WORDS) if x is not None) and vw[2] >> 16 == 0x3FE0 and \
        vw[3] >> 16 == 0x3BFF, 'not the OSReport veneer at 0x%08X' % OSREPORT_VENEER
    words, _labels, hooks = build(img.u32)
    out = ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % (at, w) for at, w in sorted(hooks.items())]
    if novis:
        assert img.u32(H_VIS) == H_VIS_WORD and img.u32(H_WHOLE) == H_WHOLE_WORD, 'h_vis / h_whole moved'
        out += ['0x%08X=0x%08X' % (H_VIS, BLR), '0x%08X=0x%08X' % (H_WHOLE, BLR)]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', required=True, help='the executable it goes on (exe_v31): hook words checked')
    ap.add_argument('--novis', action='store_true', help='the mesh switch off too (h_vis / h_whole return at once)')
    a = ap.parse_args()
    print(' '.join(args(a.rpx, a.novis)))


if __name__ == '__main__':
    main()
