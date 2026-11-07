#!/usr/bin/env python3
"""TEMPORARY diagnostic executable (Smash Run fix v8: landing on a Goomba does nothing in game): OSReport lines from
the walker update's stomp detection (tools/smashrun_walker_cave.py, "Stomp detection"), so Cemu's log shows what it
sees. Not for the normal chain build. Prints rpx_patch.py arguments.

  python3 tools/rpx_patch.py exe_v10/code/cross_f.rpx OUT.rpx $(python3 tools/diag_stomp_cave.py --rpx exe_v10/code/cross_f.rpx)

Lines (`S4STOMP <tag> ...`, hex words; floats as their bits):
  upd   every UPD_EVERY-th w_upd call that gets past its first test (one of every walker's updates): this, its
        state, its CFG, TREAD state, death state, the fighter table, its count -- is the hook reached, for which
        kinds, with a TREAD state, does the fighter loop run.
  near  the per-fighter test past "live, last frame known", when the fighter is within NEAR_X of the enemy's x and
        between NEAR_Y0 and NEAR_Y1 above its posture: slot, fighter y, its y last frame, fighter x, enemy y, enemy x,
        enemy state -- why the crossing / box test fails.
  hit   the stomp taken (before change_state_interrupt): slot, state, fighter accessor -- the reaction or the
        StepJump fails after detection.
Every line counts against MAX_LINES (the log can't flood). OSReport through the game's veneer 0x0288B4D4 as
tools/diag_crumbs_cave.py (v2) does; each stub saves r0, r2-r12, LR, CTR, XER, CR and f0-f13 (not FPSCR: no
mtfsf, Cemu warns on it), then replays the word it replaced. Space: 0x04BAE000-0x04BAF000 (zero in exe_v10, after
diag_crumbs_cave.py's (v3) 0x04BAA000-0x04BAE000, so both go on one build: exe_diag_v3).
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

CAVE, LIMIT = 0x04BAE000, 0x04BAF000
OSREPORT_VENEER = 0x0288B4D4
VENEER_WORDS = (0x9421FFF0, 0x93E1000C, None, None, 0x7FE903A6, 0x83E1000C, 0x38210010, 0x4E800420)
CRCLR_CR1EQ = 0x4CC63182
MFXER, MTXER, MFCTR = 0x7C0102A6, 0x7C0103A6, 0x7C0902A6
MAX_LINES = 6000
UPD_EVERY = 90
NEAR_X, NEAR_Y0, NEAR_Y1 = 14.0, -6.0, 40.0
FIGHTERS = 0x1035184C

FRAME = 0xC0
def SLOT(n):
    return 0x10 if n == 0 else 0x14 + 4 * (n - 2)
LR_S, CTR_S, XER_S, CR_S, FPR_S = 0x40, 0x44, 0x48, 0x4C, 0x50


def ld(dst, n):
    return 'lwz %s, %d(r1)' % (dst, SLOT(n))


def lf(dst, n):
    return 'lfd %s, %d(r1)' % (dst, FPR_S + 8 * n)


# (tag, address, the word there in exe_v10, body: r4.. = the line's values, `skip` when no line)
HOOKS = [
    ('upd', 0x04B84934, 0x819E0020,     # lwz r12, 0x20(r30): w_upd past "TREAD != 0, not in it" (r31 this, r30 CFG)
     """
        lis r12, cnt@ha
        lwz r11, cnt@l(r12)
        addi r11, r11, 1
        stw r11, cnt@l(r12)
        li r10, %d
        divwu r9, r11, r10
        mullw r9, r9, r10
        subf r9, r9, r11
        cmpwi r9, 1
        bne skip
        mr r4, r31
        lwz r5, 4(r31)
        mr r6, r30
        lwz r7, 0x78(r30)
        lwz r8, 0x20(r30)
        lis r12, 0x%04X
        lwz r9, %d(r12)
        li r10, -1
        cmpwi r9, 0
        beq u_nt
        lwz r9, 0(r9)
        cmpwi r9, 0
        beq u_nt
        lwz r10, 8(r9)
    u_nt:
    """ % (UPD_EVERY, (FIGHTERS + 0x8000) >> 16, ((FIGHTERS & 0xFFFF) ^ 0x8000) - 0x8000)),
    ('near', 0x04BB80CC, 0xC07C0014,     # lfs f3, 0x14(r28): u_body past "live, last frame known" (r25 slot,
     """
        lwz r11, %d(r1)
        lfs f8, 0x10(r11)
        lfs f9, 0x10(r28)
        fsubs f10, f8, f9
        fabs f10, f10
        lis r12, consts@ha
        addi r12, r12, consts@l
        lfs f11, 0(r12)
        fcmpu cr0, f10, f11
        bgt skip
        lfs f8, 0x14(r11)
        lfs f9, 0x14(r28)
        fsubs f10, f8, f9
        lfs f11, 4(r12)
        fcmpu cr0, f10, f11
        blt skip
        lfs f11, 8(r12)
        fcmpu cr0, f10, f11
        bgt skip
        mr r4, r25
        lwz r5, 0x14(r11)
        %s
        lwz r7, 0x10(r11)
        lwz r8, 0x14(r28)
        lwz r9, 0x10(r28)
        lwz r10, 4(r31)
    """ % (SLOT(11), ld('r6', 0))),     # r11 the fighter's posture, r0 its y last frame (bits), r28 the enemy's
    ('hit', 0x04BB8118, 0x7FE3FB78,      # mr r3, r31: the stomp taken
     """
        mr r4, r25
        lwz r5, 4(r31)
        mr r6, r24
        mr r7, r29
    """),
]


def word(op):
    return '.word 0x%08X' % op


def branch(src, dst):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0, (hex(src), hex(dst))
    return (18 << 26) | (off & 0x3FFFFFC)


def fmt_bytes(tag):
    n = {'upd': 7, 'near': 7, 'hit': 4}[tag]
    names = {'upd': ('this', 'st', 'cfg', 'tread', 'dead', 'tab', 'n'),
             'near': ('s', 'fy', 'pv', 'fx', 'ey', 'ex', 'st'),
             'hit': ('s', 'st', 'acc', 'tread')}[tag]
    assert len(names) == n
    return ('S4STOMP %s ' % tag + ' '.join('%s=%%X' % k for k in names) + '\n').encode() + b'\0'


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
    for i, (tag, at, w0, body) in enumerate(HOOKS):
        w = orig(at)
        assert w == w0, '%s: 0x%08X is 0x%08X, expected 0x%08X' % (tag, at, w, w0)
        assert w >> 26 not in (16, 18, 19), 'a branch at 0x%08X' % at
        b = body.replace('skip', 'skip%d' % i).replace('u_nt', 'u_nt%d' % i)
        a.asm('hook%d:' % i)
        a.asm('\n'.join(save))
        a.asm("""
        lis r12, lines@ha
        lwz r11, lines@l(r12)
        cmplwi r11, %d
        bge skip%d
        """ % (MAX_LINES, i))
        a.asm(b)
        a.asm("""
        lis r12, lines@ha
        lwz r11, lines@l(r12)
        addi r11, r11, 1
        stw r11, lines@l(r12)
        lis r3, fmt%d@ha
        addi r3, r3, fmt%d@l
        bl report
    skip%d:
        """ % (i, i, i))
        a.asm('\n'.join(rest))
        a.asm('%s\nb 0x%X' % (word(w), at + 4))
        hooks[at] = i
    # data (labels placed after the code)
    a.asm('consts:\n.float %r\n.float %r\n.float %r' % (NEAR_X, NEAR_Y0, NEAR_Y1))
    a.asm('lines:\n.word 0\ncnt:\n.word 0')
    pos = a.pc
    out = bytearray()
    for i, (tag, _at, _w, _b) in enumerate(HOOKS):
        a.labels['fmt%d' % i] = pos + len(out)
        out += fmt_bytes(tag)
        while len(out) % 4:
            out += b'\0'
    code = a.words()
    words = code + list(struct.unpack('>%dI' % (len(out) // 4), bytes(out)))
    assert CAVE + 4 * len(words) <= LIMIT, 'cave full'
    hk = {at: branch(at, a.labels['hook%d' % i]) for at, i in hooks.items()}
    return words, dict(a.labels), hk


def args(rpx):
    import kind_expand as K
    img = K.Image(rpx)
    used = [x for x in range(CAVE, LIMIT, 4) if img.w(x)]
    assert not used, 'the diagnostic cave space is in use in %s (0x%08X)' % (rpx, used[0])
    vw = [img.w(OSREPORT_VENEER + 4 * i) for i in range(len(VENEER_WORDS))]
    assert all(w == x for w, x in zip(vw, VENEER_WORDS) if x is not None) and vw[2] >> 16 == 0x3FE0 and \
        vw[3] >> 16 == 0x3BFF, 'not the OSReport veneer at 0x%08X' % OSREPORT_VENEER
    words, _labels, hooks = build(img.w)
    out = ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % (at, w) for at, w in sorted(hooks.items())]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', required=True, help='the executable it goes on (exe_v10\'s): hook words checked')
    a = ap.parse_args()
    print(' '.join(args(a.rpx)))


if __name__ == '__main__':
    main()
