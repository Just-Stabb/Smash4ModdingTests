#!/usr/bin/env python3
"""New fighter kinds (tools/extra_kinds.json): also load and register their base's effect banks, so
the base's articles (weapons) still find their effects. Prints rpx_patch.py arguments.

  python3 tools/rpx_patch.py build/cross_f.rpx OUT.rpx ... $(python3 tools/kind_expand.py) \\
      $(python3 tools/base_effects_cave.py)
  python3 tools/base_effects_cave.py [--kinds FILE] [--rpx RPX] [--no-final]

Why: an ACMD effect id 0xTKKnnnn names bank 0xTKK (T = 3 a fighter's own effects, 4 its Final
Smash's; KK = the kind). A new kind's copied body ACMD uses its own bank (0x341 for kind 0x41,
add_fighter.py moves the ids), but the articles still load from the base's folder by the owner name
in the weapon table (fighter/mario/script/animcmd/weapon/*), and their ACMD uses the base's ids:
Mario's fireball / pump / pumpwater 0x303...., hugeflame (Mario Finale) 0x403..... The base's banks
are only loaded when a base player is in the match, so a lone clone's articles had no effects.

Native (fighter resource holders: docs/kind-expansion*.md):
  effect folder   per fighter, 0x030C0828 adds "fighter/<name>/effect/<name>/" to the effect holder
                  [[0x102F9028]+0x2C] under id = kind (0x030C07A4, through the transform map
                  0x030BF9C0); the holder (add 0x030BEEE0 / remove 0x030BF00C) is a refcounted
                  id -> file map; the per-fighter unload 0x030BFA8C removes it
  bank            fighter set-up 0x02E13170 -> 0x030C06E8 -> 0x030C0614(holder, kind): 8 slots
                  {kind, count} at holder +0x20; the first user registers bank 0x300 + kind
                  (0x0334CB20, effect manager [0x10353CA4], 41 banks); teardown 0x02E147C0 ->
                  0x030C1278 releases it with the last user
  Final Smash     on the Smash Ball 0x02E48384: release bank 0x400 + kind (0x0334CB98) and the
                  final holder [[0x102F9028]+0x34]'s ids (0x030C1848), then add kind*9 + 3
                  ("fighter/<name>/effect/Fin<Name>/"), +8, +7 (0x030C16B0); when loaded
                  0x02E484D8(FE) registers bank 0x400 + [FE+0x10] (0x0334CB70); the same release
                  pair also at 0x02E43C00 and 0x02E4B000

Each call site below is re-aimed (bl) at a cave wrapper that calls the original, then repeats it for
the kind's base (the table `base`, byte per new kind; 0xFF = none: "effects_base": false in the
record). The holders and the slot table are refcounted per id, so a clone next to its base (or
several clones of one base) share the base's banks like two players of one fighter do.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kind_expand as K  # noqa: E402
from ppcasm import Asm  # noqa: E402

CAVE = 0x04B88000
LIMIT = 0x04B89000

FX_ADD = 0x030C07A4         # (holder, kind): adds the effect folder (kind transformed)
FX_REG = 0x030C06E8         # (fighter res, kind): thunk -> 0x030C0614 registers bank 0x300 + kind
FX_UNREG = 0x030C1278       # (holder, kind): releases it
HOLDER_REMOVE = 0x030BF00C  # (holder, id)
HOLDER_ADD = 0x030BEEE0     # (holder, id, string*)
XFORM = 0x030BF9C0          # transform kinds -> their base (0x3A-0x3D)
FS_ADD = 0x030C16B0         # (final holder, kind, color)
FS_REMOVE = 0x030C1848      # (final holder, kind, color)
FS_REG = 0x02E484D8         # (FE): registers bank 0x400 + [FE+0x10]
BANK_RELEASE = 0x0334CB98   # (bank id)
FIN_PATH = 0x030BBBEC       # (builder, string* out, kind, type 0 = effect/Fin<Name>/, 0)
PATH_BUILDER = 0x102FACF4   # [..] its object
STRING_FREE = 0x032D4200    # (string*, 2)

# call site, original target, wrapper, what the site passes
SITES = [
    (0x030C09F8, FX_ADD, 'fx_add', 'effect folder add (per fighter request 0x030C0828)'),
    (0x030BFAE0, HOLDER_REMOVE, 'fx_rem', 'effect folder remove (per fighter unload 0x030BFA8C)'),
    (0x02E13170, FX_REG, 'fx_reg', 'bank 0x300 + kind register (fighter set-up)'),
    (0x02E147C0, FX_UNREG, 'fx_unreg', 'bank 0x300 + kind release (fighter teardown)'),
]
FINAL_SITES = [
    (0x02E48434, FS_ADD, 'fs_add', 'Final Smash holder add (Smash Ball 0x02E48384)'),
    (0x02E43C10, FS_REMOVE, 'fs_rem', 'Final Smash holder remove'),
    (0x02E48424, FS_REMOVE, 'fs_rem', 'Final Smash holder remove'),
    (0x02E4B010, FS_REMOVE, 'fs_rem', 'Final Smash holder remove'),
    (0x02E1DDD0, FS_REG, 'fs_reg', 'bank 0x400 + kind register'),
    (0x02E1DF2C, FS_REG, 'fs_reg', 'bank 0x400 + kind register'),
    (0x02E43C00, BANK_RELEASE, 'fs_rel', 'bank 0x400 + kind release'),
    (0x02E48414, BANK_RELEASE, 'fs_rel', 'bank 0x400 + kind release'),
    (0x02E4B000, BANK_RELEASE, 'fs_rel', 'bank 0x400 + kind release'),
]
# what the instruction before each FS release site must be (addi r3, rX, 0x400)
FRAME = 0x50                # stmw r26 at +0x30; fake FE at +0x08 (+0x10 = kind at +0x18); string at +0x20


def bases(spec, rpx):
    cap, kinds = K.load_spec(spec)
    img = K.Image(rpx)
    names = [img.cstr(img.w(K.TABLES['lower'][0] + 4 * k)) for k in range(K.OLD_N)]
    raw = {K.num(r['kind']): r for r in __import__('json').load(open(spec))['kinds']}
    out = []
    for r in kinds:
        b = K.kind_index(names, r['base'])
        if raw[r['kind']].get('effects_base', True) is False:
            b = 0xFF
        out.append(b)
    return img, kinds, out, names


def source(n, final):
    pro = """
        stwu r1, -%(f)d(r1)
        mflr r0
        stw r0, %(lr)d(r1)
        stmw r26, 0x30(r1)
        mr r31, r3
        mr r30, r4
        mr r29, r5
        mr r28, r6
        mr r27, r7
        mr r26, r8
""" % dict(f=FRAME, lr=FRAME + 4)
    restore = """
        mr r3, r31
        mr r5, r29
        mr r6, r28
        mr r7, r27
        mr r8, r26
"""
    s = """
base_of:                                # r3 kind -> r3 its base, or -1 (r11 / r12 only)
        addi r12, r3, -0x41
        cmplwi r12, %(n)d
        li r3, -1
        bgelr
        lis r11, base@ha
        addi r11, r11, base@l
        add r11, r11, r12
        lbz r3, 0(r11)
        cmpwi r3, 0xFF
        bnelr
        li r3, -1
        blr
out:
        lmw r26, 0x30(r1)
        lwz r0, %(lr)d(r1)
        mtlr r0
        addi r1, r1, %(f)d
        blr
""" % dict(n=n, f=FRAME, lr=FRAME + 4)
    # (r3, r4 = kind, ...): F(own), then F(r3, base, r5-r8)
    for name, fn in (('fx_add', FX_ADD), ('fx_reg', FX_REG), ('fx_unreg', FX_UNREG)):
        s += name + ':' + pro + """
        bl 0x%(fn)08X
        mr r3, r30
        bl base_of
        cmpwi r3, -1
        beq out
        mr r4, r3
""" % dict(fn=fn) + restore + """
        bl 0x%(fn)08X
        b out
""" % dict(fn=fn)
    # (holder, transformed kind): remove own, then the transformed base
    s += 'fx_rem:' + pro + """
        bl 0x%(rm)08X
        mr r3, r30
        bl base_of
        cmpwi r3, -1
        beq out
        bl 0x%(xf)08X
        mr r4, r3
        mr r3, r31
        bl 0x%(rm)08X
        b out
""" % dict(rm=HOLDER_REMOVE, xf=XFORM)
    if not final:
        return s
    s += 'fs_add:' + pro + """
        bl 0x%(add)08X
        mr r3, r30
        bl base_of
        cmpwi r3, -1
        beq out
        mr r30, r3
        lis r3, %(pb_hi)d
        lwz r3, %(pb_lo)d(r3)
        addi r4, r1, 0x20
        mr r5, r30
        li r6, 0
        li r7, 0
        bl 0x%(path)08X
        mulli r4, r30, 9
        addi r4, r4, 3
        mr r3, r31
        addi r5, r1, 0x20
        bl 0x%(hadd)08X
        addi r3, r1, 0x20
        li r4, 2
        bl 0x%(free)08X
        b out
""" % dict(add=FS_ADD, pb_hi=K.ha(PATH_BUILDER),
           pb_lo=K.slo(PATH_BUILDER), path=FIN_PATH, hadd=HOLDER_ADD, free=STRING_FREE)
    s += 'fs_rem:' + pro + """
        bl 0x%(rm)08X
        mr r3, r30
        bl base_of
        cmpwi r3, -1
        beq out
        mulli r4, r3, 9
        addi r4, r4, 3
        mr r3, r31
        bl 0x%(hrm)08X
        b out
""" % dict(rm=FS_REMOVE, hrm=HOLDER_REMOVE)
    s += 'fs_reg:' + pro + """
        bl 0x%(reg)08X
        lwz r3, 0x10(r31)
        bl base_of
        cmpwi r3, -1
        beq out
        stw r3, 0x18(r1)
        addi r3, r1, 8
        bl 0x%(reg)08X
        b out
""" % dict(reg=FS_REG)
    s += 'fs_rel:' + pro + """
        bl 0x%(rel)08X
        addi r3, r31, -0x400
        bl base_of
        cmpwi r3, -1
        beq out
        addi r3, r3, 0x400
        bl 0x%(rel)08X
        b out
""" % dict(rel=BANK_RELEASE)
    return s


def build(spec=K.SPEC, rpx=K.RPX, final=True):
    img, kinds, base, names = bases(spec, rpx)
    a = Asm(CAVE)
    a.asm(source(len(kinds), final))
    a.asm('base:')
    tab = bytes(base) + b'\xFF' * (-len(base) % 4)
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
            assert prev >> 26 == 14 and (prev >> 21) & 31 == 3 and prev & 0xFFFF == 0x400, \
                '0x%08X: not addi r3, rX, 0x400' % (site - 4)
        patch[site] = K.b_word(site, a.labels[label], link=True)
        inplace.append(site)
    rel = img.relocs()
    moved = sorted(s for s in inplace if s in rel)
    return dict(patch=patch, labels=a.labels, inplace=inplace, moved=moved, kinds=kinds, base=base,
                names=names, words=words, sites=sites)


def args(B):
    out = ['grow:0x%08X' % LIMIT]
    out += ['0x%08X=0x%08X' % (a, w) for a, w in sorted(B['patch'].items())]
    out += ['reloc:0x%08X-0x%08X=0x%08X' % (a, a + 4, K.RELOC_DUMMY) for a in B['moved']]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--kinds', default=K.SPEC)
    ap.add_argument('--rpx', default=K.RPX)
    ap.add_argument('--no-final', action='store_true', help='leave the Final Smash bank alone')
    a = ap.parse_args()
    B = build(a.kinds, a.rpx, not a.no_final)
    print(' '.join(args(B)))
    sys.stderr.write('base effects: %d cave words at 0x%08X, %d call sites, %d relocations moved; %s\n' % (
        len(B['words']), CAVE, len(B['inplace']), len(B['moved']),
        ', '.join('0x%X -> %s' % (r['kind'], B['names'][b] if b != 0xFF else 'none')
                  for r, b in zip(B['kinds'], B['base']))))


if __name__ == '__main__':
    main()
