#!/usr/bin/env python3
"""TEMPORARY diagnostic executable for Kirby's Hero copy fix v4 (fighters/kirby/specials.md "Hero copy fix v4"):
OSReport lines (Cemu's log, `S4KH <tag> ...`, hex words, floats as their bits) from the held sword's chain and from
the Hero spells' articles, so the user's log settles what the static reading can't. Not for the normal chain build.
Goes on the B executable (exe_v46g: the sword fix) and prints rpx_patch.py arguments:

  python3 tools/rpx_patch.py exe_v46g.rpx exe_v46g_diag.rpx $(python3 tools/diag_kirby_hero_cave.py --rpx exe_v46g.rpx)
  python3 tools/diag_kirby_hero_test.py exe_v46g_diag.rpx exe_v46g.rpx

Lines (each tag with its own cap, CAPS):
  cpy    the copy model function 0x02EFE138 (copy_grant / the copy's loss): new kind, the kind before, the grant
         kind kirby_copy_new_cave.py kept (0x45 for a Hero), the fighter (r26).
  gen    the held article's generate (article 0x1A, 0x02EFE760): the kind, the article handle (0: not made).
  res    the copy-resource loader's model path test (0x030C4978), types 0xC (hat) / 0x11 (held model): type, kind,
         costume << 8 | match entry, found (non-zero: model/<name>/cNN exists), the path's name (3 words at its 21st
         character: "brav" "eswo" "rd/c" for model/bravesword/cNN).
  stn    the held article's update in Kirby's stone statuses (0x155 / 0x175 / 0x176), one line every STN_EVERY calls:
         the status, the owner's accessor, the article's; no line: the article's update never runs in the stone.
  swd    the stone check reading Kirby's int 0x1000008B (kirby_hero_sword_cave.py hs_chk), when it is 1 (a sword
         spell being cast: the show path follows): 1, the article visible before it (its +0xA8 module, vt +0xA4: 0
         hidden, the show path then shows it), the owner's accessor, the article's. (The show path itself,
         0x02B026B4, is out of a branch's reach from the cave.)
  spawn  Robin's thunder spawner's generate (0x02F6465C) for a Kirby (8) or a Hero (0x45): owner kind, custom
         number, the new weapon's position x / y / z (the hand joint's), the owner's own z and x. The stone's casts
         should show z off the owner's (the fix puts the projectile on his plane after this line).
  hit    the hit methods of the weapons 0x190 (Frizz), 0x193 flash, 0x194 explosion, 0x195 deathball, 0x196 crash,
         0x197 sleep (weapon_expand.py's on_hit methods): kind, result bits (1 / 2 / 0x10 a hit, 4 a shield), the
         weapon's x / y / z: whether it touched anyone, and where.
Each stub (diag_stomp_cave.py's: r0, r2-r12, LR, CTR, XER, CR, f0-f13 saved; the replaced word replayed) reads the
hooked function's own r1 as r1 + FRAME. Space: 0x04BAC000-0x04BAF000 (zero in exe_v46g: kind_expand.py's free tail
before extended_memory.py's 0x04BAF000), in the code region the standard build runs.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402
import diag_stomp_cave as B  # noqa: E402
import kirby_hero_sword_cave as SW  # noqa: E402
import kirby_copy_new_cave as V44  # noqa: E402

CAVE, LIMIT = 0x04BAC000, 0x04BAF000
FRAME = B.FRAME
STN_EVERY = 60
SW_LABELS = SW.build()[0].labels
GRANT = V44.args()[0].labels['grant_kind']
HIT_METHODS = {0x190: 0x04BB5898, 0x193: 0x04BB6030, 0x194: 0x04BB62B8, 0x195: 0x04BB6540, 0x196: 0x04BB67C8,
               0x197: 0x04BB6A50}
NAMES = {'cpy': ('kind', 'prev', 'grant', 'f'), 'gen': ('kind', 'h'),
         'res': ('type', 'kind', 'cost_ent', 'found', 'n0', 'n1', 'n2'), 'stn': ('st', 'acc', 'art'),
         'swd': ('v', 'was', 'acc', 'art'),
         'spawn': ('kind', 'custom', 'x', 'y', 'z', 'oz', 'ox'), 'hit': ('kind', 'bits', 'x', 'y', 'z', 'w')}
CAPS = {'cpy': 60, 'gen': 60, 'res': 120, 'stn': 200, 'swd': 600, 'spawn': 300, 'hit': 400}


def orig_r1(dst):
    return 'addi %s, r1, 0x%X' % (dst, FRAME)


def hooks():
    """(tag, address, the word there, body: r4.. = the line's values, `skip` when no line)"""
    h = [
        ('cpy', 0x02EFE190, 0x387A000C, """           # addi r3, r26, 0xc (r27 the new kind, r23 the one before)
        mr r4, r27
        mr r5, r23
        lis r12, 0x%04X
        lwz r6, %d(r12)
        mr r7, r26
    """ % ((GRANT + 0x8000) >> 16, ((GRANT & 0xFFFF) ^ 0x8000) - 0x8000)),
        ('gen', 0x02EFE760, 0x2C030000, """           # cmpwi r3, 0 after the article 0x1A generate
        mr r4, r27
        %s
    """ % B.ld('r5', 3)),
        ('res', 0x030C4978, 0x80010008, """           # lwz r0, 8(r1): the cNN path found?
        cmpwi r29, 0xC
        beq r_ok
        cmpwi r29, 0x11
        bne skip
    r_ok:
        mr r4, r29
        mr r5, r28
        slwi r6, r30, 8
        or r6, r6, r31
        %s
        lwz r7, 8(r11)
        lwz r8, 0x5C(r11)
        lwz r9, 0x60(r11)
        lwz r10, 0x64(r11)
    """ % orig_r1('r11')),
        ('stn', SW_LABELS['held_stone'] + 0x14, 0x28030155, """           # cmplwi r3, 0x155 (r3 the status)
        %s
        cmplwi r3, 0x155
        beq s_in
        cmplwi r3, 0x175
        beq s_in
        cmplwi r3, 0x176
        bne skip
    s_in:
        lis r12, stncnt@ha
        lwz r11, stncnt@l(r12)
        addi r11, r11, 1
        stw r11, stncnt@l(r12)
        li r10, %d
        divwu r9, r11, r10
        mullw r9, r9, r10
        subf r9, r9, r11
        cmpwi r9, 1
        bne skip
        mr r4, r3
        mr r5, r27
        mr r6, r30
    """ % (B.ld('r3', 3), STN_EVERY)),
        ('swd', SW_LABELS['hs_chk'] + 0x1C, 0x2C030001, """           # cmpwi r3, 1 (r3 = Kirby's int 0x1000008B)
        %s
        cmpwi r3, 1
        bne skip
        lwz r3, 0xA8(r30)               # the article's visibility (+0xA8, vt +0xA4: visible?) before the show path
        lwz r12, 0(r3)
        lwz r12, 0xA4(r12)
        mtctr r12
        bctrl
        mr r5, r3
        li r4, 1
        mr r6, r27
        mr r7, r30
    """ % B.ld('r3', 3)),
        ('spawn', 0x02F6465C, 0x7F83E378, """           # mr r3, r28 (r27 the owner fighter; the init struct at r1 + 0x50)
        lwz r12, 0x726C(r27)
        lwz r4, 0x18(r12)
        cmpwi r4, 8
        beq p_ok
        cmpwi r4, 0x45
        bne skip
    p_ok:
        %s
        lbz r5, 0xAC(r11)
        lwz r6, 0x54(r11)
        lwz r7, 0x58(r11)
        lwz r8, 0x5C(r11)
        lwz r12, 0x72E4(r27)
        lwz r9, 0x18(r12)
        lwz r10, 0x10(r12)
    """ % orig_r1('r11')),
    ]
    for kind, at in sorted(HIT_METHODS.items()):
        h.append(('hit', at, 0x70A00013, """           # andi. r0, r5, 0x13 (r4 the weapon, r5 the result bits)
        li r4, 0x%X
        %s
        %s
        li r6, -1
        li r7, -1
        li r8, -1
        mr r9, r11
        cmpwi r11, 0
        beq h_no
        lwz r12, 0x28(r11)
        cmpwi r12, 0
        beq h_no
        lwz r12, 0x18(r12)
        cmpwi r12, 0
        beq h_no
        lwz r6, 0x10(r12)
        lwz r7, 0x14(r12)
        lwz r8, 0x18(r12)
    h_no:
    """ % (kind, B.ld('r5', 5), B.ld('r11', 4))))
    return h


def fmt_bytes(tag):
    return ('S4KH %s ' % tag + ' '.join('%s=%%X' % k for k in NAMES[tag]) + '\n').encode() + b'\0'


def build(orig):
    """(words, labels, hooks {address: word}); orig(address) -> the executable's word"""
    hk = hooks()
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
    """ % dict(vh=B.OSREPORT_VENEER >> 16, vl=B.OSREPORT_VENEER & 0xFFFF, crclr=B.word(B.CRCLR_CR1EQ)))
    save = ['stwu r1, -0x%X(r1)' % FRAME, 'stw r0, %d(r1)' % B.SLOT(0)]
    save += ['stw r%d, %d(r1)' % (n, B.SLOT(n)) for n in range(2, 13)]
    save += ['mflr r0', 'stw r0, %d(r1)' % B.LR_S, B.word(B.MFCTR), 'stw r0, %d(r1)' % B.CTR_S, B.word(B.MFXER),
             'stw r0, %d(r1)' % B.XER_S, 'mfcr r0', 'stw r0, %d(r1)' % B.CR_S]
    save += ['stfd f%d, %d(r1)' % (n, B.FPR_S + 8 * n) for n in range(14)]
    rest = ['lfd f%d, %d(r1)' % (n, B.FPR_S + 8 * n) for n in range(14)]
    rest += ['lwz r0, %d(r1)' % B.CR_S, 'mtcrf 0xFF, r0', 'lwz r0, %d(r1)' % B.XER_S, B.word(B.MTXER),
             'lwz r0, %d(r1)' % B.CTR_S, 'mtctr r0', 'lwz r0, %d(r1)' % B.LR_S, 'mtlr r0']
    rest += ['lwz r%d, %d(r1)' % (n, B.SLOT(n)) for n in range(2, 13)]
    rest += ['lwz r0, %d(r1)' % B.SLOT(0), 'addi r1, r1, 0x%X' % FRAME]
    tags = sorted(set(t for t, _a, _w, _b in hk))
    out = {}
    for i, (tag, at, w0, body) in enumerate(hk):
        w = orig(at)
        assert w == w0, '%s: 0x%08X is 0x%08X, expected 0x%08X' % (tag, at, w, w0)
        assert w >> 26 not in (16, 18, 19), 'a branch at 0x%08X' % at
        b = body
        for lab in ('skip', 'r_ok', 's_in', 'p_ok', 'h_no'):
            b = b.replace(lab, '%s%d' % (lab, i))
        cap = 'cap_%s' % tag
        a.asm('hook%d:' % i)
        a.asm('\n'.join(save))
        a.asm("""
        lis r12, %(cap)s@ha
        lwz r11, %(cap)s@l(r12)
        cmplwi r11, %(n)d
        bge skip%(i)d
        """ % dict(cap=cap, n=CAPS[tag], i=i))
        a.asm(b)
        a.asm("""
        lis r12, %(cap)s@ha
        lwz r11, %(cap)s@l(r12)
        addi r11, r11, 1
        stw r11, %(cap)s@l(r12)
        lis r3, fmt_%(tag)s@ha
        addi r3, r3, fmt_%(tag)s@l
        bl report
    skip%(i)d:
        """ % dict(cap=cap, tag=tag, i=i))
        a.asm('\n'.join(rest))
        a.asm('%s\nb 0x%X' % (B.word(w), at + 4))
        out[at] = i
    a.asm('\n'.join('cap_%s:\n.word 0' % t for t in tags) + '\nstncnt:\n.word 0')
    pos = a.pc
    data = bytearray()
    for t in tags:
        a.labels['fmt_%s' % t] = pos + len(data)
        data += fmt_bytes(t)
        while len(data) % 4:
            data += b'\0'
    code = a.words()
    words = code + list(struct.unpack('>%dI' % (len(data) // 4), bytes(data)))
    assert CAVE + 4 * len(words) <= LIMIT, 'cave full: %d words' % len(words)
    hkw = {at: B.branch(at, a.labels['hook%d' % i]) for at, i in out.items()}
    return words, dict(a.labels), hkw


def args(rpx):
    import kind_expand as K
    img = K.Image(rpx)
    used = [x for x in range(CAVE, LIMIT, 4) if img.w(x)]
    assert not used, 'the diagnostic cave space is in use in %s (0x%08X)' % (rpx, used[0])
    vw = [img.w(B.OSREPORT_VENEER + 4 * i) for i in range(len(B.VENEER_WORDS))]
    assert all(w == x for w, x in zip(vw, B.VENEER_WORDS) if x is not None) and vw[2] >> 16 == 0x3FE0 and \
        vw[3] >> 16 == 0x3BFF, 'not the OSReport veneer at 0x%08X' % B.OSREPORT_VENEER
    words, _labels, hk = build(img.w)
    outl = ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    outl += ['0x%08X=0x%08X' % (at, w) for at, w in sorted(hk.items())]
    return outl


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', required=True, help='the executable it goes on (exe_v46g): hook words checked')
    a = ap.parse_args()
    print(' '.join(args(a.rpx)))


if __name__ == '__main__':
    main()
