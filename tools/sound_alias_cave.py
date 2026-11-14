#!/usr/bin/env python3
"""New fighter kinds: the sound-bank alias vanilla gives costume banks through fightermodelbanktable.mtb, so a
fighter in a costume with its own sound bank (snd_se_ / snd_vc_<Cap>_cNN, own BINF id: tools/sound_bank_ids.py) still
finds its sounds. Prints rpx_patch.py arguments.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/sound_alias_cave.py --rpx IN.rpx)

The fighter SoundModule's set-up (0x02761C50, vtable 0x10093C64 + 0x2CC) sets two aliases from the MTB by the
fighter's Capitalised name: +0x5C0 = the se bank's base id, +0x5C4 = the vc bank's (0x02A64C68(MTB, name, 0 / 1);
0xFFFF when the MTB has no record, which is every new kind: the MTB's 13 records are named by the executable's table
at 0x10340CA4). The sound finder (0x02C71898) takes the se handle (+0x18) for a sound whose bank id (its
soundlabeltable row's) is the handle's BINF id OR +0x5C0 (vt +0x344, 0x02762B74), the vc handle (+0x24) for +0x5C4;
the voice player's slots (0x03121FA8 -> 0x03121E94, 7 slots with an alias each at +0x64) the same. So a costume bank
with an id of its own plays the rows of the main bank's id once the alias holds that id.

Hook: the set-up's se registration with the voice player, `bl 0x03121FA8` at 0x027620B4 (r5 = [module + 0x5C0],
r30 = the module): the callee's first word (`lwz r3, 0(r3)`) goes to the cave, which, only when called from there
(LR 0x027620B8) and for a kind in ALIASES, stores +0x5C0 = se id, +0x5C4 = vc id and passes r5 = se id; then the
replaced word, back. The vc registration right after it (0x027620B8: lwz r5, 0x5C4(r30)) and the cheer's
(0x027620E4) read the new +0x5C4. Every other caller of 0x03121FA8, and every kind not in ALIASES, unchanged.
0x02761C50 itself is beyond `b` reach of the cave space; 0x03121FA8 isn't.

ALIASES (kind: main se id, main vc id = the ids of the soundlabeltable rows his scripts play; tools/sound_bank_ids.py
prints them): Hero 0x45 2051 / 6059 (Robin's ids), Sephiroth 0x42 2018 / 6014 (Zelda's). A kind whose costume banks
keep the main id needs no entry (and an entry is harmless: the main bank's own id matches first).
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

CAVE = 0x04BAE000               # free grown .text (kind_expand.py's space; diag_sound_cave.py / diag_crumbs_cave.py
LIMIT = 0x04BAE400              # use 0x04BAA000-0x04BAE000)
HOOK = 0x03121FA8               # the voice player's bank registration (r3 player*, r4 handle*, r5 alias, r6, r7)
HOOK_WORD = 0x80630000          # lwz r3, 0(r3)
SETUP_SE_RET = 0x027620B8       # its se call from the SoundModule set-up (bl at 0x027620B4)
SETUP_WORDS = {0x027620A4: 0x80BE05C0, 0x027620B8: 0x80BE05C4, 0x027620E4: 0x80BE05C4}   # lwz r5, 0x5C0 / 0x5C4(r30)
FIRST_KIND, LAST_KIND = 0x41, 0x5F
ALIASES = {0x45: (2051, 6059), 0x42: (2018, 6014)}
SE_ALIAS, VC_ALIAS = 0x5C0, 0x5C4


def branch(src, dst):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0
    return (18 << 26) | (off & 0x3FFFFFC)


def build(aliases=None):
    aliases = ALIASES if aliases is None else aliases
    n = LAST_KIND - FIRST_KIND + 1
    a = Asm(CAVE)
    a.asm("""
alias:  mflr r12
        lis r11, 0x%(rh)X
        ori r11, r11, 0x%(rl)X
        cmplw r12, r11
        bne a_out
        lwz r11, 8(r30)
        addi r11, r11, -%(first)d
        cmplwi r11, %(n)d
        bge a_out
        slwi r11, r11, 3
        lis r12, table@ha
        addi r12, r12, table@l
        add r12, r12, r11
        lwz r11, 0(r12)
        cmpwi r11, 0
        beq a_out
        stw r11, %(se)d(r30)
        mr r5, r11
        lwz r11, 4(r12)
        cmpwi r11, 0
        beq a_out
        stw r11, %(vc)d(r30)
a_out:  .word 0x%(word)08X
        b 0x%(back)X
""" % dict(rh=SETUP_SE_RET >> 16, rl=SETUP_SE_RET & 0xFFFF, first=FIRST_KIND, n=n, se=SE_ALIAS, vc=VC_ALIAS,
           word=HOOK_WORD, back=HOOK + 4))
    table_at = a.pc
    a.labels['table'] = table_at
    code = a.words()
    table = []
    for k in range(FIRST_KIND, LAST_KIND + 1):
        se, vc = aliases.get(k, (0, 0))
        table += [se, vc]
    words = code + table
    assert CAVE + 4 * len(words) <= LIMIT
    return words, {HOOK: branch(HOOK, CAVE)}


def check(rpx):
    import kind_expand as K
    img = K.Image(rpx)
    words, _h = build()
    used = [x for x in range(CAVE, CAVE + 4 * len(words), 4) if img.w(x)]
    assert not used, 'the cave space is in use in %s (0x%08X)' % (rpx, used[0])
    assert img.w(HOOK) == HOOK_WORD, '0x%08X is 0x%08X, expected 0x%08X' % (HOOK, img.w(HOOK), HOOK_WORD)
    rel = img.relocs()
    assert HOOK not in rel, 'the hook word is relocated'
    for at in (0x027620A4, 0x027620B8, 0x027620E4):
        assert img.w(at) == SETUP_WORDS[at], 'the set-up at 0x%08X is 0x%08X' % (at, img.w(at))
    w = img.w(0x027620B4)
    assert w >> 26 == 18 and w & 1 and 0x027620B4 + ((w & 0x3FFFFFC) - ((w & 0x2000000) << 1)) == HOOK, \
        'no bl 0x%08X at 0x027620B4' % HOOK


def args(rpx):
    check(rpx)
    words, hooks = build()
    return ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)] + \
        ['0x%08X=0x%08X' % (at, w) for at, w in hooks.items()]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', required=True, help='the executable it goes on: the hook words checked')
    a = ap.parse_args()
    print(' '.join(args(a.rpx)))


if __name__ == '__main__':
    main()
