#!/usr/bin/env python3
"""TEMPORARY diagnostic executable (multi-instance bugs: two Sephiroths crash / hang while loading): OSReport
breadcrumbs along a new fighter's creation and its articles' set-up, so Cemu's log shows the last step reached.
Not for the normal chain build. Prints rpx_patch.py arguments.

  python3 tools/rpx_patch.py exe_v10/code/cross_f.rpx OUT.rpx $(python3 tools/diag_crumbs_cave.py --rpx exe_v10/code/cross_f.rpx)

Each crumb is one OSReport line, `S4DIAG <step> k=<kind> a=<..> b=<..> n=<serial>`, only for new fighter kinds
(>= 0x41) and new weapon kinds (>= 0x185), so the log isn't flooded (the first-frames step is capped at STEP_MAX
lines). Cemu prints OSReport with Debug > Logging > "Coreinit Logging" checked (its log line starts "OSReport:"
or the text itself, in log.txt).

OSReport is reached through the game's own veneer OSREPORT_VENEER (0x0288B4D4: `lis r31 / addi r31` = OSReport's
address, ADDR16_HA / LO relocations the loader fills in, then `mtctr r31; bctr` with r3-r10 and cr1 untouched;
called by the game itself, bl from 0x0288B09C and five more), at its fixed .text address through ctr (out of `bl`
reach). v1 decoded the `bl OSReport` at 0x03374EA4 at run time instead: a REL24 to an import, which Cemu does not
leave as a plain `bl` to the import's thunk, so it jumped into the middle of other code (0x04185AF4: every match
crashed at the first crumb, user's Cemu log). A vararg call: cr1eq cleared (no float arguments).

Every hook replaces one word with `b stub`; the stub saves every volatile register (r0, r2-r12, LR, CTR, XER,
CR, f0-f13, FPSCR) in its own frame, computes the crumb's arguments from the saved registers, calls `crumb` when the
kind passes its filter, restores everything, then runs the replaced word (relative branches re-aimed from the stub)
and goes back. Hooks (in the order a fighter loads; STEPS below, with what a / b hold):
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

# free grown .text: kind_expand.py's space (0x04BA0000-0x04BB0000) past its last word (0x04BA97B4 in the current
# build, checked against --rpx: zeros), within `b` reach of every hook (the lowest, 0x02BCB5C0, reaches 0x04BCB5C0)
CAVE = 0x04BAA000
LIMIT = 0x04BAC000
OSREPORT_VENEER = 0x0288B4D4    # the game's OSReport veneer (lis/addi r31 = OSReport, relocated; mtctr; bctr)
VENEER_WORDS = (0x9421FFF0, 0x93E1000C, None, None, 0x7FE903A6, 0x83E1000C, 0x38210010, 0x4E800420)
STEP_MAX = 24                   # first-frames crumbs in all
KIND_FIGHTER = 0x41             # new fighter kinds from here
KIND_WEAPON = 0x185             # new weapon kinds from here

# saved-register slots in a stub's frame
FRAME = 0xE0
def SLOT(n):                     # r0 at 0x10, r2 - r12 at 0x14 + 4 x (n - 2)
    return 0x10 if n == 0 else 0x14 + 4 * (n - 2)
LR_S, CTR_S, XER_S, CR_S, FPR_S, FPSCR_S = 0x40, 0x44, 0x48, 0x4C, 0x50, 0xC0

# (tag, hook address, the word the hook replaces, args: asm leaving r4 = kind, r5 = a, r6 = b, and `skip` taken
# when the crumb isn't wanted; r3 r7-r12 r0 free; the original r3-r12 are at SLOT(n)(r1), r13-r31 as they were)
def ld(dst, n):
    return 'lwz %s, %d(r1)' % (dst, SLOT(n))


STEPS = [
    ('fighter-setup', 0x02E11C68, 0x7CBC2B78,          # mr r28, r5 (0x02E11C60: r3 fighter, r5 kind)
     ld('r4', 5) + '\ncmplwi r4, %d\nblt skip\n' % KIND_FIGHTER + ld('r5', 3) + '\n' + ld('r6', 4),
     'the fighter set-up starts (0x02E11C60): a = the fighter, b = its r4'),
    ('fighter-resources', 0x030C0BB0, 0x9421FFF0,      # stwu r1, -0x10(r1) (0x030C0BB0: r3 the request, kind +0x24)
     ld('r5', 3) + '\nlwz r4, 0x24(r5)\ncmplwi r4, %d\nblt skip\nlwz r6, 0x3C(r5)' % KIND_FIGHTER,
     'its resource request (0x030C0BB0): a = the request, b = its bytes +0x3C-0x3F'),
    ('effect-folder', 0x030C07A4, 0x7C0802A6,           # mflr r0 (0x030C07A4: r3 holder, r4 kind)
     ld('r4', 4) + '\ncmplwi r4, %d\nblt skip\n' % KIND_FIGHTER + ld('r5', 3) + '\nli r6, 0',
     'its effect folder added (0x030C07A4): a = the holder'),
    ('weapon-files', 0x030C3B78, 0x9421FFC0,            # stwu r1, -0x40(r1) (0x030C3B78: r3 holder, r4 kind, r5 color)
     ld('r4', 4) + '\ncmplwi r4, %d\nblt skip\n' % KIND_WEAPON + ld('r5', 5) + '\n' + ld('r6', 3),
     'a new weapon kind\'s files requested (0x030C3B78): a = the color, b = the holder'),
    ('effect-bank', 0x030C06E8, 0x7C6B1B78,             # mr r11, r3 (0x030C06E8: r3 fighter resources, r4 kind)
     ld('r4', 4) + '\ncmplwi r4, %d\nblt skip\n' % KIND_FIGHTER + ld('r5', 3) + '\nli r6, 0',
     'its effect bank registered (0x030C06E8)'),
    ('vl-load', 0x04BA875C, 0x7FA3EB78,                 # mr r3, r29: kind_expand's vl load case of kind 0x42
     'li r4, 0x42\n' + ld('r5', 3) + '\nmr r6, r29',
     'his params (kind_expand.py\'s vl load case for 0x42): a = r3, b = r29'),
    ('zelda-setup', 0x02F97824, None,                   # b edge_counter_cave SETUP (Zelda's specializer slot 0)
     ld('r6', 4) + '\nlwz r4, 4(r6)\ncmplwi r4, %d\nblt skip\n' % KIND_FIGHTER + ld('r5', 5),
     'Zelda\'s specializer set-up (slot 0): a = r5, b = the fighter'),
    ('counter-group', 0x04B9D078, 0x80610008,           # lwz r3, 8(r1): edge_counter_cave after the group init
     'li r4, 0x42\nlwz r5, 0x14(r31)\nmr r6, r31',
     'the counter cave\'s shield group built: a = the module\'s shape count (5 at most), b = the module'),
    ('fighter-modules', 0x02E11CF0, 0x3AC00000,         # li r22, 0: after the module set-up 0x02E3F32C
     'mr r4, r28\ncmplwi r4, %d\nblt skip\nmr r5, r27\nli r6, 0' % KIND_FIGHTER,
     'the fighter\'s modules built (0x02E3F32C returned): a = the fighter'),
    ('article-pool', 0x02C02408, 0x81430024,            # lwz r10, 0x24(r3): a pooled article instance made
     'lwz r4, 0(r22)\nclrlwi r4, r4, 2\n' + ld('r5', 3) + '\ncmpwi r5, 0\nbeq take\ncmplwi r4, %d\nblt skip\n'
     'take:\nmr r6, r30' % KIND_WEAPON,
     'an article instance taken from the weapon pool for pre-creation (0x02C02310), before its set-up: a = the object '
     '(0: the pool was empty), b = left of that entry'),
    ('weapon-modules', 0x02BCB5C0, None,                # bl weapon_expand's module-row stub (r30 the kind)
     'mr r4, r30\ncmplwi r4, %d\nblt skip\nmr r5, r31\nli r6, 0' % KIND_WEAPON,
     'a new-kind weapon object\'s modules about to be built (0x02BCB42C, the module-row stub): a = the object'),
    ('weapon-params', 0x02BCC3BC, 0x7C0802A6,           # mflr r0 (0x02BCC3BC: r4 kind, r5 custom)
     ld('r4', 4) + '\ncmplwi r4, %d\nblt skip\n' % KIND_WEAPON + ld('r5', 5) + '\n' + ld('r6', 3),
     'a new-kind weapon made, its params bound (weapon_expand.py getter): a = its custom number, b = r3'),
    ('frame', 0x02E408BC, 0xBF010018,                   # stmw r24, 0x18(r1): a fighter's step (r4 its accessor)
     'lis r12, step_n@ha\nlwz r6, step_n@l(r12)\ncmplwi r6, %d\nbge skip\n' % STEP_MAX + ld('r7', 4) +
     '\nlwz r7, 0(r7)\nlwz r4, 4(r7)\ncmplwi r4, %d\nblt skip\naddi r6, r6, 1\nstw r6, step_n@l(r12)\nlwz r5, 0(r7)'
     % KIND_FIGHTER,
     'a new fighter\'s frame step (the first %d in all): a = its object id, b = the count' % STEP_MAX),
]


def word(op):
    return '.word 0x%08X' % op


MFXER, MTXER, MFCTR = 0x7C0102A6, 0x7C0103A6, 0x7C0902A6
MFFS0, MTFSF0 = 0xFC00048E, 0xFDFE058E
CRCLR_CR1EQ = 0x4CC63182


def branch(src, dst, link=False):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0, (hex(src), hex(dst))
    return (18 << 26) | (off & 0x3FFFFFC) | int(link)


def replayed(at, w, here):
    """the replaced word at `here`: a relative b / bl re-aimed"""
    if w >> 26 == 18 and not w & 2:
        off = w & 0x3FFFFFC
        if off & 0x2000000:
            off -= 0x4000000
        return branch(here, at + off, bool(w & 1))
    assert w >> 26 not in (16, 19), 'conditional branch at 0x%08X' % at
    return w


def build(orig):
    """(words, labels, hooks {address: word}); orig(address) -> the executable's word"""
    a = Asm(CAVE)
    # crumb(r3 tag, r4 kind, r5 a, r6 b): OSReport(fmt, tag, kind, a, b, serial)
    a.asm("""
crumb:  mflr r0
        stw r0, 4(r1)
        stwu r1, -0x20(r1)
        lis r12, serial@ha
        lwz r8, serial@l(r12)
        addi r8, r8, 1
        stw r8, serial@l(r12)
        mr r7, r6
        mr r6, r5
        mr r5, r4
        mr r4, r3
        lis r3, fmt@ha
        addi r3, r3, fmt@l
        lis r12, 0x%(vh)X
        ori r12, r12, 0x%(vl)X           # the game's OSReport veneer
        mtctr r12
        %(crclr)s
        bctrl
        addi r1, r1, 0x20
        lwz r0, 4(r1)
        mtlr r0
        blr
""" % dict(vh=OSREPORT_VENEER >> 16, vl=OSREPORT_VENEER & 0xFFFF, crclr=word(CRCLR_CR1EQ)))
    hooks = {}
    for i, (tag, at, w0, args, _what) in enumerate(STEPS):
        w = orig(at)
        if w0 is not None:
            assert w == w0, '%s: 0x%08X is 0x%08X, expected 0x%08X' % (tag, at, w, w0)
        else:
            assert w >> 26 == 18, '%s: 0x%08X is 0x%08X, not a branch' % (tag, at, w)
        save = ['stwu r1, -0x%X(r1)' % FRAME, 'stw r0, %d(r1)' % SLOT(0)]
        save += ['stw r%d, %d(r1)' % (n, SLOT(n)) for n in range(2, 13)]
        save += ['mflr r0', 'stw r0, %d(r1)' % LR_S, word(MFCTR), 'stw r0, %d(r1)' % CTR_S, word(MFXER),
                 'stw r0, %d(r1)' % XER_S, 'mfcr r0', 'stw r0, %d(r1)' % CR_S]
        save += ['stfd f%d, %d(r1)' % (n, FPR_S + 8 * n) for n in range(14)]
        save += [word(MFFS0), 'stfd f0, %d(r1)' % FPSCR_S]
        rest = ['lfd f0, %d(r1)' % FPSCR_S, word(MTFSF0)]
        rest += ['lfd f%d, %d(r1)' % (n, FPR_S + 8 * n) for n in range(14)]
        rest += ['lwz r0, %d(r1)' % CR_S, 'mtcrf 0xFF, r0', 'lwz r0, %d(r1)' % XER_S, word(MTXER),
                 'lwz r0, %d(r1)' % CTR_S, 'mtctr r0', 'lwz r0, %d(r1)' % LR_S, 'mtlr r0']
        rest += ['lwz r%d, %d(r1)' % (n, SLOT(n)) for n in range(2, 13)]
        rest += ['lwz r0, %d(r1)' % SLOT(0), 'addi r1, r1, 0x%X' % FRAME]
        body = args.replace('skip', 'skip%d' % i).replace('take:', 'take%d:' % i).replace('beq take', 'beq take%d' % i)
        a.asm('hook%d:' % i)
        a.asm('\n'.join(save))
        a.asm(body)
        a.asm('lis r3, tag%d@ha\naddi r3, r3, tag%d@l\nbl crumb' % (i, i))
        a.asm('skip%d:' % i)
        a.asm('\n'.join(rest))
        a.asm('replay%d:\n.word 0\nb 0x%X' % (i, at + 4))
    a.asm('fmt:')
    blob = b'S4DIAG %s k=%X a=%X b=%X n=%d\n\0'
    tags = [(i, t[0].encode() + b'\0') for i, t in enumerate(STEPS)]
    data = [('fmt', blob)] + [('tag%d' % i, t) for i, t in tags]
    pos = a.pc - 4 * 0          # fmt label set above at the current pc
    out = bytearray()
    labels_extra = {}
    for name, b in data:
        while len(out) % 4:
            out += b'\0'
        labels_extra[name] = pos + len(out)
        out += b
    while len(out) % 4:
        out += b'\0'
    labels_extra['serial'] = pos + len(out)
    out += b'\0' * 4
    labels_extra['step_n'] = pos + len(out)
    out += b'\0' * 4
    for k, v in labels_extra.items():
        a.labels[k] = v
    code = a.words()
    for i, (tag, at, w0, _args, _w) in enumerate(STEPS):
        r = a.labels['replay%d' % i]
        code[(r - CAVE) // 4] = replayed(at, orig(at), r)
        hooks[at] = branch(at, a.labels['hook%d' % i])
    words = code + list(struct.unpack('>%dI' % (len(out) // 4), bytes(out)))
    assert CAVE + 4 * len(words) <= LIMIT, 'cave full'
    return words, dict(a.labels), hooks


def args(rpx):
    import kind_expand as K
    img = K.Image(rpx)
    used = [x for x in range(CAVE, LIMIT, 4) if img.w(x)]
    assert not used, 'the diagnostic cave space is in use in %s (0x%08X)' % (rpx, used[0])
    vw = [img.w(OSREPORT_VENEER + 4 * i) for i in range(len(VENEER_WORDS))]
    assert all(w == x for w, x in zip(vw, VENEER_WORDS) if x is not None) and vw[2] >> 16 == 0x3FE0 and \
        vw[3] >> 16 == 0x3BFF, 'not the OSReport veneer at 0x%08X' % OSREPORT_VENEER
    rel = img.relocs()
    assert OSREPORT_VENEER + 8 in rel and OSREPORT_VENEER + 12 in rel, 'the veneer\'s lis / addi aren\'t relocated'
    words, _labels, hooks = build(img.w)
    out = ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % (at, w) for at, w in sorted(hooks.items())]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', required=True, help='the executable it goes on (exe_v10\'s): hook words checked')
    ap.add_argument('--steps', action='store_true', help='list the steps')
    a = ap.parse_args()
    if a.steps:
        for i, s in enumerate(STEPS):
            print('%2d %-18s 0x%08X  %s' % (i + 1, s[0], s[1], s[4]))
        return
    print(' '.join(args(a.rpx)))


if __name__ == '__main__':
    main()
