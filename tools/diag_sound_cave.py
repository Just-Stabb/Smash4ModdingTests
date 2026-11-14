#!/usr/bin/env python3
"""TEMPORARY diagnostic executable (new kinds' sounds: "players other than player 1 don't get sound effects or voice
lines" with Hero / Sephiroth): OSReport lines along a fighter's sound set-up and every failed sound, so Cemu's log
shows, per player, whether his sound banks were made and why a sound of his did not play. Not for the normal chain
build. Prints rpx_patch.py arguments.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/diag_sound_cave.py --rpx IN.rpx)

Each line is one OSReport, `S4SND <step> e=<entry> k=<kind> a=.. b=.. c=.. d=..` (Cemu: Debug > Logging >
"Coreinit Logging"; the OSReport veneer as tools/diag_crumbs_cave.py, 0x0288B4D4). Every step is capped (MAX).

How a fighter's sound works (cross_f.rpx; docs/native-notes.md "Fighter sound banks"):
- the per-player resource loader (`[[0x102F9028] + 0x58 + 4 entry]`, 0x030C3368) registers the fighter's sound
  files under ids kind * 0x11 + 6 (snd_se), + 7 (snd_vc), + 8 (snd_vc_ouen) ... (0x030C0C34; the costume's _cNN file
  when it exists);
- the fighter's SoundModule set-up (vtable 0x10093C64 + 0x2CC = 0x02761C50) takes those files from ITS player's
  loader (0x030BF0FC) and makes a bank handle of each (0x033EDD24: one bank a file, shared; 0x033EDABC parses it
  with nus3, 0x03673A94) at module + 0x18 (se), + 0x24 (vc), + 0x30 (cheer);
- a sound (row << 16 | label) is played only from the playing fighter's own handles (0x02C71B24 -> 0x02C71898: the
  row's bank id = a handle's BINF id or its csb alias +0x5C0 / +0x5C4).

Steps (a / b / c / d):
  setup     0x03121D68  the end of the SoundModule set-up (its call at 0x02762190, told apart by the return
                        address; 0x02762180 itself is out of `b` reach of the cave): a / b / c = the BINF id of the
                        se / vc / cheer handle (-1 = no bank), d = the voice costume the loader used (+0x5E4; 0 =
                        the main files)
  bankfail  0x033EDB38  a bank could not be made from a file: a = nus3's error (0x80000005 = the file has no data),
                        b = the file's data, c = the resource, d = the bank serial
  gated     0x02C71B78  a sound refused because the module's +0x5B4 is 0 while the sound manager's +0x2BD is set:
                        a = the sound id
  nobank    0x02C71C3C  a sound whose bank is none of the fighter's handles: a = the sound id, b = its bank id (the
                        soundlabeltable row's), c = the handle tried (offset in the module)
  filtered  0x02C71C64  a sound the fighter's filter (vt +0x314) refused: a = the sound id, b = the tone's kind
  ok        0x02C71C6C  a sound that passed every check (the first OK_EACH of each player): a = the sound id,
                        b = its bank id, c = the handle used (offset in the module: 0x18 se, 0x24 vc, ...)
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

# free grown .text past kind_expand.py's last word (0x04BA97B4), the space diag_crumbs_cave.py uses (never both)
CAVE = 0x04BAA000
LIMIT = 0x04BAE000
OSREPORT_VENEER = 0x0288B4D4    # the game's OSReport veneer (lis/addi r31 = OSReport, relocated; mtctr; bctr)
VENEER_WORDS = (0x9421FFF0, 0x93E1000C, None, None, 0x7FE903A6, 0x83E1000C, 0x38210010, 0x4E800420)
BANK_ID = 0x033EC060            # (handle*) -> the bank's BINF id, -1 when the handle holds no bank
OK_EACH = 4                     # 'ok' lines per player (entry & 7)
SETUP_RET = 0x02762194          # the set-up's return address from its last player call (bl 0x03121D68 at 0x02762190)

MFXER, MTXER, MFCTR = 0x7C0102A6, 0x7C0103A6, 0x7C0902A6
CRCLR_CR1EQ = 0x4CC63182

FRAME = 0xD0                    # r0 0x10, r3-r12 0x14-0x38, LR 0x40, CTR 0x44, XER 0x48, CR 0x4C, f0-f13 0x50-0xBF,
SCRATCH = 0xC0                  # scratch 0xC0-0xCF


def SLOT(n):
    return 0x10 if n == 0 else 0x14 + 4 * (n - 3)


# (tag, hook address, the word it replaces, cap, snippet: r4..r9 = e, k, a, b, c, d then `li r3, STEP; bl report`,
#  or `b skip`; r30 / r31 / r23... are the hooked function's own, intact; the original r0 / r3-r12 at SLOT(n)(r1))
STEPS = [
    ('setup', 0x03121D68, 0x80630000, 64, """
        lwz r0, 0x40(r1)
        lis r12, 0x%(setup_ret_hi)X
        ori r12, r12, 0x%(setup_ret_lo)X
        cmplw r0, r12
        bne skip
        addi r3, r30, 0x18
        bl %(bank)s
        stw r3, %(s0)d(r1)
        addi r3, r30, 0x24
        bl %(bank)s
        stw r3, %(s1)d(r1)
        addi r3, r30, 0x30
        bl %(bank)s
        mr r8, r3
        lwz r4, 0xC(r30)
        lwz r5, 8(r30)
        lwz r6, %(s0)d(r1)
        lwz r7, %(s1)d(r1)
        lwz r9, 0x5E4(r30)
        li r3, STEP
        bl report
"""),
    ('bankfail', 0x033EDB38, 0x2C030000, 64, """
        lwz r6, %(r3)d(r1)
        cmpwi r6, 0
        beq skip
        li r4, -1
        li r5, -1
        mr r7, r31
        lwz r8, 0x1C(r29)
        lwz r9, 0(r29)
        li r3, STEP
        bl report
"""),
    ('gated', 0x02C71B78, 0x2C000000, 16, """
        lwz r0, %(r0)d(r1)
        cmpwi r0, 0
        bne skip
        lwz r4, 0xC(r30)
        lwz r5, 8(r30)
        mr r6, r23
        li r7, 0
        li r8, 0
        li r9, 0
        li r3, STEP
        bl report
"""),
    ('nobank', 0x02C71C3C, 0x2C030000, 48, """
        lwz r0, %(r3)d(r1)
        cmpwi r0, 0
        bne skip
        lwz r4, 0xC(r30)
        lwz r5, 8(r30)
        mr r6, r23
        mr r7, r26
        subf r8, r30, r27
        li r9, 0
        li r3, STEP
        bl report
"""),
    ('filtered', 0x02C71C64, 0x2C030000, 16, """
        lwz r0, %(r3)d(r1)
        cmpwi r0, 0
        beq skip
        lwz r4, 0xC(r30)
        lwz r5, 8(r30)
        mr r6, r23
        mr r7, r28
        li r8, 0
        li r9, 0
        li r3, STEP
        bl report
"""),
    ('ok', 0x02C71C6C, 0x387E0594, 64, """
        lwz r4, 0xC(r30)
        clrlwi r10, r4, 29
        slwi r10, r10, 2
        lis r11, okcnt@ha
        addi r11, r11, okcnt@l
        lwzx r12, r11, r10
        cmplwi r12, %(ok_each)d
        bge skip
        addi r12, r12, 1
        stwx r12, r11, r10
        lwz r5, 8(r30)
        mr r6, r23
        mr r7, r26
        subf r8, r30, r27
        li r9, 0
        li r3, STEP
        bl report
"""),
]
FORMAT = b'S4SND %s e=%d k=%X a=%X b=%X c=%X d=%X\n\0'


def word(op):
    return '.word 0x%08X' % op


def branch(src, dst, link=False):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0, (hex(src), hex(dst))
    return (18 << 26) | (off & 0x3FFFFFC) | int(link)


def build():
    """(words, labels, hooks {address: word})"""
    a = Asm(CAVE)
    # report(r3 = step, r4..r9 = e, k, a, b, c, d): capped per step, OSReport(FORMAT, tag, e, k, a, b, c, d)
    a.asm("""
report: mflr r0
        stw r0, 4(r1)
        stwu r1, -0x20(r1)
        slwi r11, r3, 2
        lis r12, counts@ha
        addi r12, r12, counts@l
        lwzx r10, r12, r11
        lis r3, caps@ha
        addi r3, r3, caps@l
        lwzx r0, r3, r11
        cmplw r10, r0
        bge r_out
        addi r10, r10, 1
        stwx r10, r12, r11
        mr r10, r9
        mr r9, r8
        mr r8, r7
        mr r7, r6
        mr r6, r5
        mr r5, r4
        lis r12, tags@ha
        addi r12, r12, tags@l
        lwzx r4, r12, r11
        lis r3, fmt@ha
        addi r3, r3, fmt@l
        lis r12, 0x%(vh)X
        ori r12, r12, 0x%(vl)X
        mtctr r12
        %(crclr)s
        bctrl
r_out:  addi r1, r1, 0x20
        lwz r0, 4(r1)
        mtlr r0
        blr
""" % dict(vh=OSREPORT_VENEER >> 16, vl=OSREPORT_VENEER & 0xFFFF, crclr=word(CRCLR_CR1EQ)))
    save = ['stwu r1, -0x%X(r1)' % FRAME, 'stw r0, %d(r1)' % SLOT(0)]
    save += ['stw r%d, %d(r1)' % (n, SLOT(n)) for n in range(3, 13)]
    save += ['mflr r0', 'stw r0, 0x40(r1)', word(MFCTR), 'stw r0, 0x44(r1)', word(MFXER), 'stw r0, 0x48(r1)',
             'mfcr r0', 'stw r0, 0x4C(r1)']
    save += ['stfd f%d, %d(r1)' % (n, 0x50 + 8 * n) for n in range(14)]
    rest = ['lfd f%d, %d(r1)' % (n, 0x50 + 8 * n) for n in range(14)]
    rest += ['lwz r0, 0x4C(r1)', 'mtcrf 0xFF, r0', 'lwz r0, 0x48(r1)', word(MTXER), 'lwz r0, 0x44(r1)', 'mtctr r0',
             'lwz r0, 0x40(r1)', 'mtlr r0']
    rest += ['lwz r%d, %d(r1)' % (n, SLOT(n)) for n in range(3, 13)]
    rest += ['lwz r0, %d(r1)' % SLOT(0), 'addi r1, r1, 0x%X' % FRAME]
    hooks = {}
    for i, (tag, at, w0, _cap, body) in enumerate(STEPS):
        a.asm('hook%d:' % i)
        a.asm('\n'.join(save))
        text = body % dict(bank='0x%X' % BANK_ID, s0=SCRATCH, s1=SCRATCH + 4, r0=SLOT(0), r3=SLOT(3),
                           ok_each=OK_EACH, setup_ret_hi=SETUP_RET >> 16, setup_ret_lo=SETUP_RET & 0xFFFF)
        a.asm(text.replace('STEP', str(i)).replace('skip', 'skip%d' % i))
        a.asm('skip%d:' % i)
        a.asm('\n'.join(rest))
        assert w0 >> 26 not in (16, 18, 19), 'a branch at 0x%08X' % at
        a.asm('replay%d:\n.word 0x%08X\nb 0x%X' % (i, w0, at + 4))
    end = a.pc
    # data: counters, caps, tag pointers, ok counters, the format, the tags
    data = bytearray()
    counts_at = end
    data += b'\0' * (4 * len(STEPS))
    caps_at = end + len(data)
    data += b''.join(struct.pack('>I', s[3]) for s in STEPS)
    tags_at = end + len(data)
    data += b'\0' * (4 * len(STEPS))
    okcnt_at = end + len(data)
    data += b'\0' * 32
    fmt_at = end + len(data)
    data += FORMAT
    tag_at = []
    for s in STEPS:
        while len(data) % 4:
            data += b'\0'
        tag_at.append(end + len(data))
        data += s[0].encode() + b'\0'
    while len(data) % 4:
        data += b'\0'
    for i, t in enumerate(tag_at):
        struct.pack_into('>I', data, tags_at - end + 4 * i, t)
    a.labels.update(counts=counts_at, caps=caps_at, tags=tags_at, okcnt=okcnt_at, fmt=fmt_at)
    code = a.words()
    assert len(code) * 4 == end - CAVE
    for i, (tag, at, w0, _c, _b) in enumerate(STEPS):
        hooks[at] = branch(at, a.labels['hook%d' % i])
    words = code + list(struct.unpack('>%dI' % (len(data) // 4), bytes(data)))
    assert CAVE + 4 * len(words) <= LIMIT, 'cave full (0x%08X)' % (CAVE + 4 * len(words))
    return words, dict(a.labels), hooks


def check(rpx):
    import kind_expand as K
    img = K.Image(rpx)
    used = [x for x in range(CAVE, LIMIT, 4) if img.w(x)]
    assert not used, 'the diagnostic cave space is in use in %s (0x%08X)' % (rpx, used[0])
    vw = [img.w(OSREPORT_VENEER + 4 * i) for i in range(len(VENEER_WORDS))]
    assert all(w == x for w, x in zip(vw, VENEER_WORDS) if x is not None) and vw[2] >> 16 == 0x3FE0 and \
        vw[3] >> 16 == 0x3BFF, 'not the OSReport veneer at 0x%08X' % OSREPORT_VENEER
    rel = img.relocs()
    assert OSREPORT_VENEER + 8 in rel and OSREPORT_VENEER + 12 in rel, 'the veneer\'s lis / addi aren\'t relocated'
    for tag, at, w0, _c, _b in STEPS:
        assert img.w(at) == w0, '%s: 0x%08X is 0x%08X, expected 0x%08X' % (tag, at, img.w(at), w0)
        assert at not in rel, '%s: 0x%08X is relocated' % (tag, at)
    return img


def args(rpx):
    check(rpx)
    words, _labels, hooks = build()
    out = ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % (at, w) for at, w in sorted(hooks.items())]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', help='the executable it goes on: hook words checked')
    ap.add_argument('--steps', action='store_true', help='list the steps')
    a = ap.parse_args()
    if a.steps:
        for tag, at, w0, cap, _b in STEPS:
            print('%-9s 0x%08X (replaces 0x%08X), at most %d lines' % (tag, at, w0, cap))
        return
    print(' '.join(args(a.rpx)))


if __name__ == '__main__':
    main()
