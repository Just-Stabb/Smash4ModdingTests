#!/usr/bin/env python3
"""Per-costume motion sets for new kinds (Byleth's female costumes), vanilla Bayonetta's costume-group mechanism
extended to the kinds of tools/extra_kinds.json, plus the costume as a variable for ACMD / MSC. Prints rpx_patch.py
arguments (ADDR=VALUE words).

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/costume_group_cave.py --rpx IN.rpx)
  python3 tools/costume_group_test.py OUT.rpx IN.rpx                        (unicorn, the real code paths)

How vanilla does it (cross_f.rpx; fighters/master/README.md "v3: female animations"): Bayonetta (kind 0x38) costumes 4-7
(not 2) play her Bayonetta 2 motions from fighter/bayonetta/motion/body2/ (+ bodyentry2, bodyresult2, bodyroutemap2).
Ten sites test `kind == 0x38` and the costume:
  - the motion path builder 0x030BB18C(r3, out, kind, type, costume) sends 0x38 to its own copy 0x030BAE08, which
    takes the "2" folder (types 0 body, 1 entry, 2 result, 3 route map);
  - in battle every player has its own resource loader ([[0x102F9028] + 0x58 + 4 entry], 0x030C3368) and the body
    motion is its id kind x 0x11 + 3 with the path built from that player's costume (0x030C0828), so two players of
    one kind in different groups load both packs with no other change;
  - the entry and result packs live in shared loaders under kind x 9 + 1; Bayonetta's second group takes kind x 9 + 2
    (entry load 0x030C199C / unload 0x030C1ADC, result load 0x030C1BE0 / unload 0x030C1E90, getter 0x030C20C4), so
    both groups coexist there too. kind x 9 + 2 is used by no other kind (every `mulli rX, kind, 9` checked).
  - the player record's byte +0x23 (read by the fighter's construction 0x02E130E4 in mode 3, and by Kirby's copy
    loader 0x030C5240 as the resource category << 28) picks a model pack (kind x 0x11 + 0 / + 1), not a motion: it
    plays no part here.

What this patch does, for a kind whose extra_kinds.json record has "motion_group2" (the costumes that play the second
set, e.g. Byleth [1, 3, 5, 7]): a mask byte per kind 0x41-0x60 (bit c = costume c) and
  1. path: 0x030BB1AC (`cmpwi r31, 0x38`) -> a cave that, for a masked costume, builds fighter/<name>/motion/body2/
     (bodyentry2/, bodyresult2/, bodyroutemap2/: vanilla's own strings) with the game's own calls, as 0x030BAE08
     does; everything else goes on as before (0x38 to 0x030BAE08, other kinds the default path);
  2. ids: the default paths of the entry load / unload, result load (both words) / unload and the getter take
     kind x 9 + 1 + group (group 1 for a masked costume), as Bayonetta's branches do;
  3. variables (WorkModule floats, read only; ACMD Float_Var_Compare / SET_FLOAT's reads, MSC WorkModuleF(0, id)):
       0x0F000500 COSTUME        the fighter's costume (0-15, from its player's loader +0x28)
       0x0F000501 COSTUME_PARITY costume & 1 (Ultimate's FIGHTER_INSTANCE_WORK_ID_INT_COLOR % 2)
       0x0F000502 MOTION_GROUP   1 when the fighter plays the second motion set (Bayonetta 2 / the mask), else 0
     on the get_float path position_vars_cave.py sends on for IDs >= 0x400 (its get_other `b`, 0x037EDC94): ours are
     answered, every other ID goes on to kirby_stat_cave.py's 0x037EE160 as before. A fighter is found as position_vars
     finds "self" (the fighter table, [[0x1035184C]]: entries of 0x76B0, live when +0x1E >= 4, accessor +0xC,
     WorkModule +0x28); an article / no fighter reads 0.
Space: 0x04BAD800-0x04BAE000 (zero in exe_v46r: kind_expand.py's free tail, after diag_threads_cave.py's 0x04BAD000-0x04BAD400, before sound_alias_cave.py's 0x04BAE000).
"""
import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm, ha, lo  # noqa: E402

CAVE, LIMIT = 0x04BAD800, 0x04BAE000
FIRST, NK = 0x41, 0x20                 # mask bytes for kinds 0x41-0x60
BAYO = 0x38
STRING_INIT, STRING_FMT, STRING_DEL, KIND_NAME = 0x032D6F6C, 0x032D94F4, 0x032D4200, 0x0275DB24
FMT = 0x10158838                       # "fighter/%s/motion/%s/"
FOLDERS2 = (0x101587A4, 0x10158860, 0x1015882C, 0x10158850)   # body2 bodyentry2 bodyresult2 bodyroutemap2
GET_OTHER, STAT_CAVE = 0x037EDC94, 0x037EE160
FIGHTERS, ENTRY_SIZE = 0x1035184C, 0x76B0
LOADERS = 0x102F9028                   # [this] + 0x58 + 4 entry: the player's resource loader (+0x28 costume)
VAR = 0x0F000500
VAR_NAMES = ('COSTUME', 'COSTUME_PARITY', 'MOTION_GROUP')

# (site, original word, what): every word this patch replaces, checked against the input
SITES = {
    'path':      (0x030BB1AC, 0x2C1F0038, 'cmpwi r31, 0x38 (the path builder\'s Bayonetta test)'),
    'entry_ld':  (0x030C1A40, 0x388C0001, 'addi r4, r12, 1 (entry load: kind r30, costume r31)'),
    'entry_ul':  (0x030C1B10, 0x388A0001, 'addi r4, r10, 1 (entry unload: kind r30, costume r31)'),
    'result_rl': (0x030C1C24, 0x389A0001, 'addi r4, r26, 1 (result load, the release: kind r28, costume r29)'),
    'result_ld': (0x030C1CDC, 0x389A0001, 'addi r4, r26, 1 (result load: kind r28, costume r29)'),
    'result_ul': (0x030C1ECC, 0x1FFE0009, 'mulli r31, r30, 9 (result unload: kind r30, costume r31)'),
    'getter':    (0x030C20E8, 0x1D850009, 'mulli r12, r5, 9 (the entry / result getter: kind r5, costume r6)'),
    'var':       (GET_OTHER, 0x480004CC, 'b 0x037EE160 (position_vars get_other)'),
}
# words after a replaced one the stubs replay or skip (checked too)
AFTER = {0x030C1ED0: 0x7FA3EB78, 0x030C1ED4: 0x389F0001, 0x030C20EC: 0x38AC0001, 0x030C20F0: 0x4BFFD00C,
         0x030BB1B0: 0x4082002C}


def masks(spec):
    """mask bytes for kinds FIRST .. FIRST + NK - 1 from the records' "motion_group2" (costume numbers)"""
    out = [0] * NK
    for k in spec.get('kinds', []):
        g = k.get('motion_group2')
        if not g:
            continue
        kind = int(k['kind'], 0) if isinstance(k['kind'], str) else k['kind']
        assert FIRST <= kind < FIRST + NK, 'kind 0x%X outside the mask table' % kind
        m = 0
        for c in g:
            assert 0 <= int(c) < 8, 'motion_group2: costumes 0-7'
            m |= 1 << int(c)
        out[kind - FIRST] = m
    return out


def grp(kr, cr, tag):
    """r11 = 1 when kind kr / costume cr plays the second motion set (Bayonetta's rule for 0x38, the mask byte for
    the table's kinds), else 0; clobbers r0, r12, cr0 (inline: some sites are leaves that tail-call)"""
    return """
        li r11, 0
        cmpwi {k}, {bayo}
        bne g1_{t}
        cmpwi {c}, 2
        beq gd_{t}
        cmplwi {c}, 4
        blt gd_{t}
        li r11, 1
        b gd_{t}
g1_{t}: addi r0, {k}, -{first}
        cmplwi r0, {nk}
        bge gd_{t}
        cmplwi {c}, 8
        bge gd_{t}
        lis r12, {th}
        addi r12, r12, {tl}
        lbzx r12, r12, r0
        srw r12, r12, {c}
        clrlwi r11, r12, 31
gd_{t}:
""".format(k=kr, c=cr, t=tag, bayo=BAYO, first=FIRST, nk=NK, th='TAB_HA', tl='TAB_LO')


def source(tab_addr):
    s = """
# --- 1. the path builder (0x030BB1AC): kind r31, out r30, type r6, costume r7; r29 saved by its prologue -------
path_hook:
        cmpwi r31, {bayo}
        beq.far 0x030BB1B4                  # Bayonetta: her own builder, as before
""" + grp('r31', 'r7', 'p') + """
        cmpwi r11, 0
        beq.far 0x030BB1DC                  # the default path
        cmplwi r6, 3
        bgt.far 0x030BB1DC
        lis r12, FOLD_HA
        addi r12, r12, FOLD_LO
        slwi r11, r6, 2
        lwzx r29, r12, r11              # "body2" / "bodyentry2" / "bodyresult2" / "bodyroutemap2"
        addi r3, r1, 8
        bl {init}
        mr r3, r31
        lis r12, {nh}
        ori r12, r12, {nl}
        mtctr r12
        bctrl                           # the kind's name (0x0275DB24: out of `bl` reach)
        mr r6, r3
        mr r4, r30
        lis r5, {fh}
        addi r5, r5, {fl}               # "fighter/%s/motion/%s/"
        addi r3, r1, 8
        mr r7, r29
        .word 0x4CC63182                # crclr 4*cr1+eq (varargs, no floats)
        bl {fmt}
        addi r3, r1, 8
        li r4, 2
        bl {dele}
        b 0x030BB1C0                    # its epilogue

# --- 2. the shared entry / result packs' ids: kind x 9 + 1 + group --------------------------------------------
entry_ld:
""" + grp('r30', 'r31', 'a') + """
        mulli r4, r30, 9
        addi r4, r4, 1
        add r4, r4, r11
        b 0x030C1A44
entry_ul:
""" + grp('r30', 'r31', 'b') + """
        mulli r4, r30, 9
        addi r4, r4, 1
        add r4, r4, r11
        b 0x030C1B14
result_rl:
""" + grp('r28', 'r29', 'c') + """
        addi r4, r26, 1
        add r4, r4, r11
        b 0x030C1C28
result_ld:
""" + grp('r28', 'r29', 'd') + """
        addi r4, r26, 1
        add r4, r4, r11
        b 0x030C1CE0
result_ul:
""" + grp('r30', 'r31', 'e') + """
        mulli r31, r30, 9
        mr r3, r29
        addi r4, r31, 1
        add r4, r4, r11
        b 0x030C1ED8
getter:
""" + grp('r5', 'r6', 'f') + """
        mulli r12, r5, 9
        addi r5, r12, 1
        add r5, r5, r11
        b 0x030BF0FC                    # a leaf tail call: LR is the caller's

# --- 3. the costume variables (get_float(r3 WorkModule, r4 id) -> f1) -------------------------------------------
var_hook:
        rlwinm r12, r4, 0, 0, 29
        lis r11, 0x0F00
        ori r11, r11, 0x0500
        cmplw r12, r11
        bne.far {stat}
        clrlwi r10, r4, 30
        cmplwi r10, 3
        bge.far {stat}
        lis r12, {fth}
        lwz r12, {ftl}(r12)
        cmpwi r12, 0
        beq vzero
        lwz r12, 0(r12)
        cmpwi r12, 0
        beq vzero
        lwz r9, 8(r12)                  # entry count
        lwz r12, 0(r12)                 # entries
        cmpwi r12, 0
        beq vzero
        li r8, 0
vloop:  cmplw r8, r9
        bge vzero
        mulli r7, r8, {esz}
        add r7, r7, r12
        lbz r0, 0x1E(r7)
        cmplwi r0, 4
        blt vnext
        lwz r6, 0xC(r7)
        cmpwi r6, 0
        beq vnext
        lwz r6, 0x28(r6)
        cmplw r6, r3
        beq vfound
vnext:  addi r8, r8, 1
        b vloop
vfound: lwz r5, 4(r7)                   # kind
        lwz r6, 8(r7)                   # its player entry (the loaders' index, 0x030C3368)
        cmplwi r6, 8
        bge vzero
        lis r12, {lh}
        lwz r12, {ll}(r12)
        cmpwi r12, 0
        beq vzero
        slwi r6, r6, 2
        add r12, r12, r6
        lwz r12, 0x58(r12)
        cmpwi r12, 0
        beq vzero
        lwz r6, 0x28(r12)               # the costume it was loaded with
        cmplwi r10, 0
        beq vret
        cmplwi r10, 1
        bne vgroup
        clrlwi r6, r6, 31
        b vret
vgroup:
""" + grp('r5', 'r6', 'v') + """
        mr r6, r11
vret:   cmplwi r6, 15
        ble vok
        li r6, 15
vok:    lis r12, FLT_HA
        addi r12, r12, FLT_LO
        slwi r6, r6, 2
        lfsx f1, r12, r6
        blr
vzero:  lis r12, FLT_HA
        addi r12, r12, FLT_LO
        lfs f1, 0(r12)
        blr
"""
    return s.format(bayo=BAYO, init=STRING_INIT, nh=KIND_NAME >> 16, nl=KIND_NAME & 0xFFFF, fmt=STRING_FMT, dele=STRING_DEL,
                    fh=ha(FMT), fl=lo(FMT) - (0x10000 if lo(FMT) & 0x8000 else 0), stat=STAT_CAVE,
                    fth=ha(FIGHTERS), ftl=lo(FIGHTERS) - (0x10000 if lo(FIGHTERS) & 0x8000 else 0), esz=ENTRY_SIZE,
                    lh=ha(LOADERS), ll=lo(LOADERS) - (0x10000 if lo(LOADERS) & 0x8000 else 0))


def build(spec):
    """{address: word} of the cave (code, the folder table, the mask table, the floats) and the hooks"""
    m = masks(spec)

    def assemble(tab, fold, flt):
        src = source(tab)
        for name, v in (('TAB', tab), ('FOLD', fold), ('FLT', flt)):
            src = src.replace(name + '_HA', str(ha(v))).replace(name + '_LO', str(lo(v) - (0x10000 if lo(v) & 0x8000 else 0)))
        a = Asm(CAVE)
        a.asm(src)
        return a
    a = assemble(0, 0, 0)                       # sizes first, then the data after the code
    code_end = CAVE + 4 * len(a.words())
    fold = (code_end + 0xF) & ~0xF
    tab = fold + 4 * len(FOLDERS2)
    flt = (tab + NK + 0xF) & ~0xF
    a = assemble(tab, fold, flt)
    words = {CAVE + 4 * i: w for i, w in enumerate(a.words())}
    for i, f in enumerate(FOLDERS2):
        words[fold + 4 * i] = f
    for i in range(0, NK, 4):
        words[tab + i] = struct.unpack('>I', bytes(m[i:i + 4]))[0]
    for i in range(16):
        words[flt + 4 * i] = struct.unpack('>I', struct.pack('>f', float(i)))[0]
    end = flt + 64
    assert end <= LIMIT, 'cave too big: 0x%08X' % end
    L = a.labels
    hooks = {SITES['path'][0]: 'path_hook', SITES['entry_ld'][0]: 'entry_ld', SITES['entry_ul'][0]: 'entry_ul',
             SITES['result_rl'][0]: 'result_rl', SITES['result_ld'][0]: 'result_ld',
             SITES['result_ul'][0]: 'result_ul', SITES['getter'][0]: 'getter', SITES['var'][0]: 'var_hook'}
    for site, label in hooks.items():
        off = L[label] - site
        assert -0x2000000 <= off < 0x2000000
        words[site] = (18 << 26) | (off & 0x3FFFFFC)
    return words, {'code_end': code_end, 'fold': fold, 'tab': tab, 'flt': flt, 'end': end, 'labels': L, 'masks': m}


def check_input(img):
    bad = []
    for name, (a, w, what) in SITES.items():
        if img.w(a) != w:
            bad.append('%s 0x%08X: 0x%08X, want 0x%08X (%s)' % (name, a, img.w(a), w, what))
    for a, w in AFTER.items():
        if img.w(a) != w:
            bad.append('0x%08X: 0x%08X, want 0x%08X' % (a, img.w(a), w))
    for a in range(CAVE, LIMIT, 4):
        if img.w(a):
            bad.append('cave 0x%08X not zero' % a)
            break
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rpx', help='the input executable (its words are checked)')
    ap.add_argument('--kinds', default=os.path.join(HERE, 'extra_kinds.json'))
    ap.add_argument('--info', action='store_true')
    a = ap.parse_args()
    spec = json.load(open(a.kinds))
    words, info = build(spec)
    if a.rpx:
        import kind_expand as K
        bad = check_input(K.Image(a.rpx))
        if bad:
            sys.exit('costume_group_cave: the input is not as expected:\n  ' + '\n  '.join(bad))
    if a.info:
        print('cave 0x%08X-0x%08X (code to 0x%08X), masks %s' % (CAVE, info['end'], info['code_end'],
              ' '.join('0x%X=0x%02X' % (FIRST + i, v) for i, v in enumerate(info['masks']) if v)))
        return
    print(' '.join('0x%08X=0x%08X' % (k, v) for k, v in sorted(words.items())))


if __name__ == '__main__':
    main()
