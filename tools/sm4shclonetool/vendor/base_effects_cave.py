"""A new fighter kind also registers / releases its base kind's effect banks (its articles' effects use the base's
ids): wrappers at the effect-folder and bank call sites.

Adapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; the tool
sets the code addresses itself, see its README "The executable")."""
import argparse
import os
import struct
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kind_expand as K
from ppcasm import Asm
CAVE = 79159296
LIMIT = 79167488
FX_ADD = 51120036
FX_REG = 51119848
FX_UNREG = 51122808
HOLDER_REMOVE = 51113996
HOLDER_ADD = 51113696
XFORM = 51116480
FS_ADD = 51123888
FS_REMOVE = 51124296
FS_REG = 48530648
BANK_RELEASE = 53791640
FIN_PATH = 51100652
PATH_BUILDER = 271559924
STRING_FREE = 53297664
SITES = [(51120632, FX_ADD, 'fx_add', 'effect folder add (per fighter request 0x030C0828)'), (51116768, HOLDER_REMOVE, 'fx_rem', 'effect folder remove (per fighter unload 0x030BFA8C)'), (48312688, FX_REG, 'fx_reg', 'bank 0x300 + kind register (fighter set-up)'), (48318400, FX_UNREG, 'fx_unreg', 'bank 0x300 + kind release (fighter teardown)')]
FINAL_SITES = [(48530484, FS_ADD, 'fs_add', 'Final Smash holder add (Smash Ball 0x02E48384)'), (48512016, FS_REMOVE, 'fs_rem', 'Final Smash holder remove'), (48530468, FS_REMOVE, 'fs_rem', 'Final Smash holder remove'), (48541712, FS_REMOVE, 'fs_rem', 'Final Smash holder remove'), (48356816, FS_REG, 'fs_reg', 'bank 0x400 + kind register'), (48357164, FS_REG, 'fs_reg', 'bank 0x400 + kind register'), (48512000, BANK_RELEASE, 'fs_rel', 'bank 0x400 + kind release'), (48530452, BANK_RELEASE, 'fs_rel', 'bank 0x400 + kind release'), (48541696, BANK_RELEASE, 'fs_rel', 'bank 0x400 + kind release')]
FRAME = 80

def bases(spec, rpx):
    cap, kinds = K.load_spec(spec)
    img = K.Image(rpx)
    names = [img.cstr(img.w(K.TABLES['lower'][0] + 4 * k)) for k in range(K.OLD_N)]
    raw = {K.num(r['kind']): r for r in __import__('json').load(open(spec))['kinds']}
    out = []
    for r in kinds:
        b = K.kind_index(names, r['base'])
        if raw[r['kind']].get('effects_base', True) is False:
            b = 255
        out.append(b)
    return (img, kinds, out, names)

def source(n, final):
    pro = '\n        stwu r1, -%(f)d(r1)\n        mflr r0\n        stw r0, %(lr)d(r1)\n        stmw r26, 0x30(r1)\n        mr r31, r3\n        mr r30, r4\n        mr r29, r5\n        mr r28, r6\n        mr r27, r7\n        mr r26, r8\n' % dict(f=FRAME, lr=FRAME + 4)
    restore = '\n        mr r3, r31\n        mr r5, r29\n        mr r6, r28\n        mr r7, r27\n        mr r8, r26\n'
    s = '\nbase_of:                                # r3 kind -> r3 its base, or -1 (r11 / r12 only)\n        addi r12, r3, -0x41\n        cmplwi r12, %(n)d\n        li r3, -1\n        bgelr\n        lis r11, base@ha\n        addi r11, r11, base@l\n        add r11, r11, r12\n        lbz r3, 0(r11)\n        cmpwi r3, 0xFF\n        bnelr\n        li r3, -1\n        blr\nout:\n        lmw r26, 0x30(r1)\n        lwz r0, %(lr)d(r1)\n        mtlr r0\n        addi r1, r1, %(f)d\n        blr\n' % dict(n=n, f=FRAME, lr=FRAME + 4)
    for name, fn in (('fx_add', FX_ADD), ('fx_reg', FX_REG), ('fx_unreg', FX_UNREG)):
        s += name + ':' + pro + '\n        bl 0x%(fn)08X\n        mr r3, r30\n        bl base_of\n        cmpwi r3, -1\n        beq out\n        mr r4, r3\n' % dict(fn=fn) + restore + '\n        bl 0x%(fn)08X\n        b out\n' % dict(fn=fn)
    s += 'fx_rem:' + pro + '\n        bl 0x%(rm)08X\n        mr r3, r30\n        bl base_of\n        cmpwi r3, -1\n        beq out\n        bl 0x%(xf)08X\n        mr r4, r3\n        mr r3, r31\n        bl 0x%(rm)08X\n        b out\n' % dict(rm=HOLDER_REMOVE, xf=XFORM)
    if not final:
        return s
    s += 'fs_add:' + pro + '\n        bl 0x%(add)08X\n        mr r3, r30\n        bl base_of\n        cmpwi r3, -1\n        beq out\n        mr r30, r3\n        lis r3, %(pb_hi)d\n        lwz r3, %(pb_lo)d(r3)\n        addi r4, r1, 0x20\n        mr r5, r30\n        li r6, 0\n        li r7, 0\n        bl 0x%(path)08X\n        mulli r4, r30, 9\n        addi r4, r4, 3\n        mr r3, r31\n        addi r5, r1, 0x20\n        bl 0x%(hadd)08X\n        addi r3, r1, 0x20\n        li r4, 2\n        bl 0x%(free)08X\n        b out\n' % dict(add=FS_ADD, pb_hi=K.ha(PATH_BUILDER), pb_lo=K.slo(PATH_BUILDER), path=FIN_PATH, hadd=HOLDER_ADD, free=STRING_FREE)
    s += 'fs_rem:' + pro + '\n        bl 0x%(rm)08X\n        mr r3, r30\n        bl base_of\n        cmpwi r3, -1\n        beq out\n        mulli r4, r3, 9\n        addi r4, r4, 3\n        mr r3, r31\n        bl 0x%(hrm)08X\n        b out\n' % dict(rm=FS_REMOVE, hrm=HOLDER_REMOVE)
    s += 'fs_reg:' + pro + '\n        bl 0x%(reg)08X\n        lwz r3, 0x10(r31)\n        bl base_of\n        cmpwi r3, -1\n        beq out\n        stw r3, 0x18(r1)\n        addi r3, r1, 8\n        bl 0x%(reg)08X\n        b out\n' % dict(reg=FS_REG)
    s += 'fs_rel:' + pro + '\n        bl 0x%(rel)08X\n        addi r3, r31, -0x400\n        bl base_of\n        cmpwi r3, -1\n        beq out\n        addi r3, r3, 0x400\n        bl 0x%(rel)08X\n        b out\n' % dict(rel=BANK_RELEASE)
    return s

def build(spec=K.SPEC, rpx=K.RPX, final=True):
    img, kinds, base, names = bases(spec, rpx)
    a = Asm(CAVE)
    a.asm(source(len(kinds), final))
    a.asm('base:')
    tab = bytes(base) + b'\xff' * (-len(base) % 4)
    for i in range(0, len(tab), 4):
        a.asm('.word 0x%08X' % struct.unpack('>I', tab[i:i + 4])[0])
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, 'cave full'
    patch = {CAVE + 4 * i: w for i, w in enumerate(words)}
    sites = SITES + (FINAL_SITES if final else [])
    inplace = []
    for site, orig, label, _what in sites:
        got = img.w(site)
        want = K.b_word(site, orig, link=True)
        assert got == want, '0x%08X: 0x%08X, expected bl 0x%08X: not the base this was made for' % (site, got, orig)
        if orig == BANK_RELEASE:
            prev = img.w(site - 4)
            assert prev >> 26 == 14 and prev >> 21 & 31 == 3 and (prev & 65535 == 1024), '0x%08X: not addi r3, rX, 0x400' % (site - 4)
        patch[site] = K.b_word(site, a.labels[label], link=True)
        inplace.append(site)
    rel = img.relocs()
    moved = sorted((s for s in inplace if s in rel))
    return dict(patch=patch, labels=a.labels, inplace=inplace, moved=moved, kinds=kinds, base=base, names=names, words=words, sites=sites)

def args(B):
    out = ['grow:0x%08X' % LIMIT]
    out += ['0x%08X=0x%08X' % (a, w) for a, w in sorted(B['patch'].items())]
    out += ['reloc:0x%08X-0x%08X=0x%08X' % (a, a + 4, K.RELOC_DUMMY) for a in B['moved']]
    return out
