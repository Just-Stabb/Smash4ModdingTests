#!/usr/bin/env python3
"""Kirby copies Hero (kind 0x45) and Sephiroth (kind 0x42) with their own hats, motions and articles. Prints
rpx_patch.py arguments, applied after the standard build (it re-hooks weapon_expand.py's Kirby copy-resource stubs):

  python3 tools/rpx_patch.py EXE_V43.rpx EXE_V44.rpx $(python3 tools/kirby_copy_new_cave.py)
  python3 tools/kirby_copy_new_test.py EXE_V44.rpx EXE_V43.rpx

fighters/kirby/specials.md "Hero / Sephiroth copies". Kirby's copy tables (hat, motions, params, weapon pools, ~22
switches on the copy kind) have rows for kinds 0-0x39 only and copy_grant (0x02EFCD8C) refuses kinds >= 0x3A, so,
as Supamario's copy (fix 90 / 91), a new kind is granted as an old one; both are granted as Kirby's **Robin copy
(0x2C)**, the one with the most neutral-special motion slots (14: start, hold, shoot, Thoron's three; ground / air),
no held model and no copy set-up, with Kirby's int 0x100000A0 telling the MSC which it really is:

1. copy_grant (swallow and the star missile cave both call it). At its `mr r28, r6` (0x02EFCDA4) the kind is
   kept in GRANT_KIND and mapped (0x41 Supamario -> 3 Mario, 0x45 Hero -> 0x2C, 0x42 Sephiroth -> 0x2C); where it
   stores the copy kind in int 0x100000A4 (`stw r28, 0x290(r7)`, 0x02EFCEE0) the marker goes in 0x100000A0
   (+0x280): 1 Supamario, 2 Hero, 3 Sephiroth, 0 any other copy. (Before, Kirby's MSC turned a pending star copy of
   Supamario into Mario's and set 1 itself; a swallowed Supamario was refused. copy_grant clears 0x83-0x9E only:
   copy_custom_cave.py's count 0x1C.)
2. The copy resources (hat model, motion packs) load per **player slot** of the copied fighter, by its kind's row
   (0x030C4D30 calls the helper 0x030C4694 for each match entry: resource ids 0x20C + slot, Kirby's costume in the
   top bits; copy_grant's r5 is the copied fighter's entry). weapon_expand.py's stubs map the kind for the loader
   (0x030C46A8 r28), its other user (0x030C5254 r16) and the release (0x030C5BD0 r23); they're re-pointed at stubs
   that also map 0x45 / 0x42 to 0x2C, and the loader's stub keeps the real kind in RES_KIND. Two name reads in the
   loader then take the new names for that slot only: the motion folder (0x030C470C `lwz r7, -0x5930(r8)`, table
   0x1041A6D0 + "body": "brave" / "edge" -> motion/bravebody, edgebody) and the hat (0x030C4830 `lwzx r7, r23, r21`,
   table 0x1041A7B8: "bravecap" / "edgecap" -> model/bravecap/cNN, edgecap/cNN). A Robin in the same match loads
   refletcap / refletbody in its own slot as before.
3. Articles: Robin's copy record list (header 0x101356E4) copied here with two more records, the copy's articles 6
   and 7: Hero's fireball (weapon 0x190, max 3, the thunder's spawner 0x02F643A4: its level from the custom N slot,
   copy_custom_cave.py's thunder cave reads Kirby's 0x1000009F) and Sephiroth's Flare fire (0x18C, max 3, Din's
   Fire's spawner 0x02F97C90: its level from the owner's 0x10000049). copy_grant builds the copy's weapon pools from
   the list (0x02EFDB88), so the weapons' files must be loaded: Kirby's reserve article entries 15-18 name the Robin
   copy's book 0xB4 and thunder 0xB6 (with instances, never loaded in a match without Robin) and 0x190 / 0x18C
   (count 0: their files load with Kirby's; Supamario's fix 90 did the same for its kamehameha).
Code space: 0x04BAF400-0x04BAF700, free code in kind_expand.py's region (crash fix v1: exe_v44 grew the text region
past acmd_ext_cave.py's 0x04BD4000 for it, and Cemu crashed the first time a hook called into it: IP 0, in
PPCRecompiler_getJumpTableBase, the user's log). The hat read is 0x030C4830 (r23 = the hat table); exe_v44 swapped
0x030C487C, the held-item table's read (type 0x11), loading the hat as the Hero player's held item.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

CAVE = 0x04BAF400              # crash fix v1: in kind_expand.py's code space (free after extended_memory.py's
LIMIT = 0x04BAF620             # 0x04BAF000-0x04BAF100); exe_v44 grew the text region to 0x04BD6000 for it and Cemu
                               # crashed calling into it (PPCRecompiler_getJumpTableBase, IP 0: the user's log).
                               # 0x04BAF620-0x04BAF700: kirby_hero_sword_cave.py (exe_v46; this code ends at 0x04BAF618)

HOOK_GRANT = 0x02EFCDA4         # copy_grant: mr r28, r6
HOOK_STORE = 0x02EFCEE0         # copy_grant: stw r28, 0x290(r7) (int 0x100000A4)
RES_HOOKS = ((0x030C46A8, 28, True), (0x030C5254, 16, False), (0x030C5BD0, 23, False))   # bl old stub
HOOK_BODY = 0x030C470C          # lwz r7, -0x5930(r8): table 0x1041A6D0 (owner name -> motion/<name>body)
HOOK_HAT = 0x030C4830           # lwzx r7, r23, r21: table 0x1041A7B8 (hat; r23 = 0x1041A7B8 from 0x030C46E8). exe_v44
                                # hooked 0x030C487C (r24 = 0x1041A8A0: the held-item table, type 0x11) by mistake

ROBIN = 0x2C
MAP = ((0x41, 3, 1), (0x45, ROBIN, 2), (0x42, ROBIN, 3))      # copied kind -> granted kind, marker
NAMES = {0x45: ('brave', 'bravecap'), 0x42: ('edge', 'edgecap')}

COPY_TABLE = 0x1038281C
ROBIN_HDR = 0x101356E4          # [COPY_TABLE + 4 x 0x2C]: Robin's copy header {records, count}
NEW_RECORDS = ((0x190, 3, 0x02F643A4, 0), (0x18C, 3, 0x02F97C90, 0))
KIRBY_RESERVE = 0x10136AE4                  # + 0x10 x i: {kind, count, 0, 0}
RESERVE = ((18, 0xB4), (17, 0xB6), (16, 0x190), (15, 0x18C))


def words_of(s):
    b = s.encode() + b'\0'
    b += b'\0' * (-len(b) % 4)
    return ['.word 0x%08X' % struct.unpack('>I', b[i:i + 4])[0] for i in range(0, len(b), 4)]


def source(old_records):
    src = ['grant_kind:', '.word 0', 'res_kind:', '.word 0xFFFFFFFF']
    for k, (body, hat) in sorted(NAMES.items()):
        src += ['s_body_%x:' % k] + words_of(body) + ['s_hat_%x:' % k] + words_of(hat)
    src += ['robin_list:'] + ['.word 0x%08X' % w for r in list(old_records) + list(NEW_RECORDS) for w in r]
    # 1. copy_grant: keep the kind, map it
    src += ['grant_map:', 'lis r12, grant_kind@ha', 'stw r6, grant_kind@l(r12)', 'mr r28, r6']
    for i, (k, to, _m) in enumerate(MAP):
        src += ['cmplwi r6, 0x%X' % k, 'bne gm%d' % i, 'li r28, 0x%X' % to, 'gm%d:' % i]
    src += ['blr']
    # ... and the marker next to the copy kind
    src += ['grant_store:', 'stw r28, 0x290(r7)', 'lis r12, grant_kind@ha', 'lwz r12, grant_kind@l(r12)']
    for k, _to, mk in MAP:
        src += ['li r11, %d' % mk, 'cmplwi r12, 0x%X' % k, 'beq gs_put']
    src += ['li r11, 0', 'gs_put:', 'stw r11, 0x280(r7)', 'blr']
    # 2. the copy-resource stubs
    for hook, reg, keep in RES_HOOKS:
        src += ['res_%X:' % hook]
        if keep:
            src += ['lis r12, res_kind@ha', 'stw r4, res_kind@l(r12)']
        src += ['mr r%d, r4' % reg]
        for i, (k, to, _m) in enumerate(MAP):
            src += ['cmplwi r%d, 0x%X' % (reg, k), 'bne r%X_%d' % (hook, i), 'li r%d, 0x%X' % (reg, to),
                    'r%X_%d:' % (hook, i)]
        src += ['blr']
    for tag, orig in (('body', 'lwz r7, -0x5930(r8)'), ('hat', 'lwzx r7, r23, r21')):
        src += ['name_%s:' % tag, 'lis r12, res_kind@ha', 'lwz r12, res_kind@l(r12)']
        for k in sorted(NAMES):
            src += ['cmplwi r12, 0x%X' % k, 'bne n%s_%x' % (tag, k), 'lis r7, s_%s_%x@ha' % (tag, k),
                    'addi r7, r7, s_%s_%x@l' % (tag, k), 'blr', 'n%s_%x:' % (tag, k)]
        src += [orig, 'blr']
    return '\n'.join(src)


def bl(at, to):
    return (18 << 26) | ((to - at) & 0x03FFFFFC) | 1


def build(old_records):
    a = Asm(CAVE)
    a.asm(source(old_records))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, 'kirby copy cave too big'
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    lab = a.labels
    out[HOOK_GRANT] = bl(HOOK_GRANT, lab['grant_map'])
    out[HOOK_STORE] = bl(HOOK_STORE, lab['grant_store'])
    for hook, _reg, _keep in RES_HOOKS:
        out[hook] = bl(hook, lab['res_%X' % hook])
    out[HOOK_BODY] = bl(HOOK_BODY, lab['name_body'])
    out[HOOK_HAT] = bl(HOOK_HAT, lab['name_hat'])
    for i, k in RESERVE:
        out[KIRBY_RESERVE + 0x10 * i] = k
    return a, out


# Robin's copy records as the standard build leaves them (checked by kirby_copy_new_test.py against the RPX)
ROBIN_RECORDS = ((0xB4, 1, 0x02F6426C, 0), (0xB5, 0, 0, 0), (0xB6, 5, 0x02F643A4, 0), (0xB7, 0, 0, 0),
                 (0xB8, 0, 0, 0), (0xB9, 0, 0, 0))
ROBIN_RECS_OLD = 0x101365EC     # the old list (its first record's last word takes the header's moved relocation)


def args():
    a, out = build(ROBIN_RECORDS)
    lst = a.labels['robin_list']
    out[ROBIN_HDR] = lst
    out[ROBIN_HDR + 4] = len(ROBIN_RECORDS) + len(NEW_RECORDS)
    res = ['0x%08X=0x%08X' % (k, v) for k, v in sorted(out.items())]
    res += ['reloc:0x%08X-0x%08X=0x%08X' % (ROBIN_HDR, ROBIN_HDR + 4, ROBIN_RECS_OLD + 12)]
    return a, res


def main():
    a, res = args()
    print(' '.join(res))
    print('kirby copy cave: 0x%08X-0x%08X (%d words); Robin copy list 0x%08X (8 records)' % (
        CAVE, a.pc, (a.pc - CAVE) // 4, a.labels['robin_list']), file=sys.stderr)


if __name__ == '__main__':
    main()
