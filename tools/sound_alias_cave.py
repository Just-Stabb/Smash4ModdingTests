#!/usr/bin/env python3
"""New fighter kinds: sound banks of their own BINF ids that still play the soundlabeltable rows their scripts use
(the base fighter's rows, or the port's rows of the base's id). The alias vanilla takes from
fightermodelbanktable.mtb, given per new kind. Prints rpx_patch.py arguments.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/sound_alias_cave.py --rpx IN.rpx)

Why: nus3 loads one bank an id (docs/native-notes.md "Fighter sound banks: one bank an id"): a port keeping its base's
bank ids (Hero = Robin's 2051 / 6059, Sephiroth = Zelda's, Squirtle = Mario's ...) silenced the later player when the
base, or another port on the same ids, was in the match; so every bank of a new kind gets its own id
(tools/sound_bank_ids.py, reference/port_sound_ids.json), and a sound id (row << 16 | label) still names the row of
the OLD id. The game plays a fighter's sound from his own bank handles; the SoundModule (vtable 0x10093C64) matches
the row's bank id against each handle's id or the handle's alias:
  se   handle +0x18   alias +0x5C0   (the finder 0x02C71898 through vt +0x344 = 0x02762B74, type 0)
  vc   handle +0x24   alias +0x5C4   (type 1; the voice player's slots get +0x5C0 / +0x5C4 as their aliases when
                                      the set-up registers the handles, 0x027620A4 / 0x027620B8)
  cheer handle +0x90  alias +0x5C8   (passed with the handle to the audience at 0x02761FBC)
  se_common +0x84     alias +0x580   (the Final Smash bank, set when it loads, 0x02761590, and registered with the
                                      voice player with it, bl 0x03121FA8 at 0x02761598)
The set-up (0x02761C50) fills +0x5C0 / +0x5C4 / +0x5C8 from the MTB by the fighter's name (0x02A64C68; 0xFFFF for a
new kind: the MTB's 13 records are named by the executable's table at 0x10340CA4) and only later makes the handles.

Hooks (0x02761C50 itself is beyond `b` reach of the cave space; these callees aren't; each acts only when called from
that one place, by the return address, and only for a kind in the table; r30 = the module there):
  SETUP  0x03127990 (`lwz r12, 0(r3)`, the sound manager's +0x2A4 getter), its call at 0x02761E44 (LR 0x02761E48):
         right after the MTB lookups, before the handles: +0x5C0 / +0x5C4 / +0x5C8 = the kind's old se / vc / cheer
         ids (each only when the table has one).
  FS     0x03121FA8 (`lwz r3, 0(r3)`, the voice player's bank registration), its call at 0x02761598 (LR 0x0276159C):
         +0x580 and r5 (the slot's alias) = the kind's old se_common id.
v1 (new kinds' sound fix v1) hooked 0x03121FA8 for the set-up's se call (LR 0x027620B8); v2 replaces that cave in place
(the same address), so it goes on an executable with or without v1.

The table: per kind 0x41-0x5F four words (old se, vc, cheer, se_common ids; 0 = none), from
reference/port_sound_ids.json ("alias").
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

CAVE = 0x04BAE000               # free grown .text (kind_expand.py's space; diag_sound_cave.py / diag_crumbs_cave.py
LIMIT = 0x04BAE400              # use 0x04BAA000-0x04BAE000)
SETUP_HOOK, SETUP_WORD, SETUP_RET = 0x03127990, 0x81830000, 0x02761E48
FS_HOOK, FS_WORD, FS_RET = 0x03121FA8, 0x80630000, 0x0276159C
HOOK = FS_HOOK                  # (v1's name)
SETUP_WORDS = {0x02761E3C: 0x907E05C8, 0x02761E44: None, 0x02761FBC: 0x80BE05C8, 0x027620A4: 0x80BE05C0,
               0x027620B8: 0x80BE05C4, 0x02761590: 0x90BE0580, 0x02761598: None}
FIRST_KIND, LAST_KIND = 0x41, 0x5F
SE_ALIAS, VC_ALIAS, OUEN_ALIAS, COMMON_ALIAS = 0x5C0, 0x5C4, 0x5C8, 0x580
IDS = os.path.join(HERE, '..', 'reference', 'port_sound_ids.json')


def load_aliases(path=IDS):
    """{kind: (se, vc, cheer, se_common)}: the old ids the kind's rows use"""
    d = json.load(open(path))
    out = {}
    for name, rec in d['fighters'].items():
        al = rec.get('alias', {})
        out[int(rec['kind'], 0)] = tuple(int(al.get(k) or 0) for k in ('se', 'vc', 'ouen', 'se_common'))
    return out


def branch(src, dst):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0
    return (18 << 26) | (off & 0x3FFFFFC)


def build(aliases=None):
    aliases = load_aliases() if aliases is None else aliases
    n = LAST_KIND - FIRST_KIND + 1
    a = Asm(CAVE)
    a.asm("""
fs:     mflr r12
        lis r11, 0x%(fh)X
        ori r11, r11, 0x%(fl)X
        cmplw r12, r11
        bne fs_out
        lwz r11, 8(r30)
        addi r11, r11, -%(first)d
        cmplwi r11, %(n)d
        bge fs_out
        slwi r11, r11, 4
        lis r12, table@ha
        addi r12, r12, table@l
        add r12, r12, r11
        lwz r11, 12(r12)
        cmpwi r11, 0
        beq fs_out
        stw r11, %(common)d(r30)
        mr r5, r11
fs_out: .word 0x%(fw)08X
        b 0x%(fback)X
setup:  mflr r12
        lis r11, 0x%(sh)X
        ori r11, r11, 0x%(sl)X
        cmplw r12, r11
        bne s_out
        lwz r11, 8(r30)
        addi r11, r11, -%(first)d
        cmplwi r11, %(n)d
        bge s_out
        slwi r11, r11, 4
        lis r12, table@ha
        addi r12, r12, table@l
        add r12, r12, r11
        lwz r11, 0(r12)
        cmpwi r11, 0
        beq s_vc
        stw r11, %(se)d(r30)
s_vc:   lwz r11, 4(r12)
        cmpwi r11, 0
        beq s_ou
        stw r11, %(vc)d(r30)
s_ou:   lwz r11, 8(r12)
        cmpwi r11, 0
        beq s_out
        stw r11, %(ou)d(r30)
s_out:  .word 0x%(sw)08X
        b 0x%(sback)X
""" % dict(fh=FS_RET >> 16, fl=FS_RET & 0xFFFF, sh=SETUP_RET >> 16, sl=SETUP_RET & 0xFFFF, first=FIRST_KIND, n=n,
           se=SE_ALIAS, vc=VC_ALIAS, ou=OUEN_ALIAS, common=COMMON_ALIAS, fw=FS_WORD, fback=FS_HOOK + 4,
           sw=SETUP_WORD, sback=SETUP_HOOK + 4))
    a.labels['table'] = a.pc
    code = a.words()
    table = []
    for k in range(FIRST_KIND, LAST_KIND + 1):
        table += list(aliases.get(k, (0, 0, 0, 0)))
    words = code + table
    assert CAVE + 4 * len(words) <= LIMIT
    return words, {FS_HOOK: branch(FS_HOOK, a.labels['fs']), SETUP_HOOK: branch(SETUP_HOOK, a.labels['setup'])}, \
        dict(a.labels)


def table_of(img, kind):
    """the four ids an executable's cave gives a kind (for port_check)"""
    words, _h, labels = build({})
    t = labels['table'] + 16 * (kind - FIRST_KIND)
    return tuple(img.w(t + 4 * i) for i in range(4))


def check(rpx):
    import kind_expand as K
    img = K.Image(rpx)
    words, hooks, _l = build()
    v1 = img.w(FS_HOOK) == branch(FS_HOOK, CAVE)           # new kinds' sound fix v1 there
    if not v1:
        used = [x for x in range(CAVE, CAVE + 4 * len(words), 4) if img.w(x)]
        assert not used, 'the cave space is in use in %s (0x%08X)' % (rpx, used[0])
        assert img.w(FS_HOOK) == FS_WORD, '0x%08X is 0x%08X' % (FS_HOOK, img.w(FS_HOOK))
    assert img.w(SETUP_HOOK) == SETUP_WORD, '0x%08X is 0x%08X' % (SETUP_HOOK, img.w(SETUP_HOOK))
    rel = img.relocs()
    assert FS_HOOK not in rel and SETUP_HOOK not in rel, 'a hook word is relocated'
    for at, w in SETUP_WORDS.items():
        if w is not None:
            assert img.w(at) == w, 'the set-up at 0x%08X is 0x%08X' % (at, img.w(at))
    for at, target in ((0x02761E44, SETUP_HOOK), (0x02761598, FS_HOOK)):
        w = img.w(at)
        assert w >> 26 == 18 and w & 1 and at + ((w & 0x3FFFFFC) - ((w & 0x2000000) << 1)) == target, \
            'no bl 0x%08X at 0x%08X' % (target, at)
    return v1


def args(rpx):
    check(rpx)
    words, hooks, _l = build()
    return ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)] + \
        ['0x%08X=0x%08X' % (at, w) for at, w in sorted(hooks.items())]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', required=True, help='the executable it goes on: the hook words checked')
    ap.add_argument('--table', action='store_true', help='print the alias table')
    a = ap.parse_args()
    if a.table:
        for k, v in sorted(load_aliases().items()):
            print('0x%02X se %d vc %d cheer %d se_common %d' % ((k,) + v))
        return
    print(' '.join(args(a.rpx)))


if __name__ == '__main__':
    main()
