#!/usr/bin/env python3
"""Kirby's copy weapon pools: no instances of a new fighter's weapon whose owner isn't in the match (crash fix v4).

  python3 tools/rpx_patch.py EXE_V45D.rpx EXE_V45E.rpx $(python3 tools/kirby_copy_pool_cave.py)
  python3 tools/kirby_copy_pool_test.py EXE_V45E.rpx EXE_V45D.rpx

The crash (user, bisect v3, Cemu log): Kirby vs Mario, Kirby gains Mario's copy -> PPC IP 0x04BB3350
`lwz r11, 0x160(r8)` with r8 = 0, in weapon_expand.py's copy of the Kamehameha's (weapon 0x18B) param getter:
r8 = [FighterParamManager + 0x26B4] = Supamario's vl slot (0x25B0 + 4 x 0x41), empty with no Supamario in the match.
Stack: copy_grant 0x02EFCEB0 -> the copy's pool builder 0x02EFDB88 (0x02EFDCA4: an instance per record, `max` of
them) -> weapon create 0x02BF42E8 -> ... -> the module set-up's +0x18 param getter call (0x02BCB9F4).

weapon_expand.py's getter copies read the NEW fighter's vl slot (kind_expand's relocated array), which is filled
only while that fighter (or one based on it: a new kind's vl load also loads its base's) is in the match. A vanilla
copy pool only holds the copied fighter's own weapons, who is always there; this mod's copy lists hold other
fighters' weapons: Mario's (0x2C header 0x101355A4) the Kamehameha 0x18B (Supamario, fix 90), Robin's (the Hero /
Sephiroth copies) Hero's 0x190 / 0x193-0x197 and Sephiroth's 0x18C. So gaining Mario's copy without Supamario, Robin's
or Hero's without Sephiroth, or Sephiroth's without Hero read a null vl. (Nothing to do with the copy-resource loader
hooks: bisect v3's test 1 / 3 / 6 results differ only by which copy was gained.)

The fix: the pool builder's read of a record's instance count (0x02EFDC74 `lwz r19, 4(r11)`, r17 = the record's
kind word) -> a stub that keeps it, except for a new weapon kind (0x185 on) whose owner fighter's vl slot
([mgr + 0x25B0 + 4 x owner]: exactly the slot its getter reads) is empty: count 0, the path a vanilla max-0 record
takes (no instances, not registered). Such a weapon is never generated: its copy's MSC path needs the owner in the
match (0x100000A0's marker comes from copy_grant's copied kind). Owners from extra_kinds.json's "weapons".
Registers: only r11 / r12 (dead there; r12 is rewritten at 0x02EFDCA4 / the loop top, r11 at 0x02EFDCCC) and cr7;
cr0 (the `rlwinm.` at 0x02EFDC70, tested by the bne after the hook) is kept.
Space: 0x04BAFA00-0x04BAFB00, free code in kind_expand.py's region after kirby_hero_menu_cave.py's (0x04BAF700-
0x04BAFA00), the standard code region; no relocation on the hooked word (rpx_patch.py checks).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kind_expand as K  # noqa: E402
from ppcasm import Asm  # noqa: E402

CAVE = 0x04BAFA00
LIMIT = 0x04BAFB00
HOOK = 0x02EFDC74               # lwz r19, 4(r11): the record's instance count (pool builder 0x02EFDB88)
HOOK_WORD = 0x826B0004
PARAM_MGR = 0x102FF448          # [0x10300000 - 0xBB8]: FighterParamManager
FIRST_NEW = 0x185               # weapon_expand.py OLD_N


def owners(spec=K.SPEC):
    """{new weapon kind: owner fighter kind} from extra_kinds.json's "weapons" """
    out = {}
    for r in json.load(open(spec))['kinds']:
        for _art, v in (r.get('weapons') or {}).items():
            out[K.num(v['kind'] if isinstance(v, dict) else v)] = K.num(r['kind'])
    return out


def vl_new():
    fcap, _k = K.load_spec(K.SPEC)
    return K.mgr_layout(fcap)[0]['vl'][1]


def build():
    own = owners()
    last = max(own)
    assert min(own) == FIRST_NEW and all(0 < k < 0x100 for k in own.values())
    table = [own.get(k, 0) for k in range(FIRST_NEW, last + 1)]   # 0: no owner (unused kind: kept as is)
    table += [0] * (-len(table) % 4)
    slot = vl_new()
    src = ['owner_tab:'] + ['.word 0x%08X' % int.from_bytes(bytes(table[i:i + 4]), 'big')
                            for i in range(0, len(table), 4)]
    src += ['pool_max:',
            'lwz r19, 4(r11)',                      # the replaced word
            'clrlwi r12, r17, 2',                   # the record's kind (its top bits are flags)
            'cmplwi cr7, r12, 0x%X' % FIRST_NEW,
            'bltlr cr7',
            'cmplwi cr7, r12, 0x%X' % last,
            'bgtlr cr7',
            'lis r11, owner_tab@ha',
            'addi r11, r11, owner_tab@l',
            'add r11, r11, r12',
            'lbz r11, %d(r11)' % -FIRST_NEW,        # the owner fighter kind
            'cmpwi cr7, r11, 0',
            'beqlr cr7',
            'slwi r11, r11, 2',
            'lis r12, 0x%X' % ((PARAM_MGR + 0x8000) >> 16),
            'lwz r12, %d(r12)' % K.sx16(PARAM_MGR & 0xFFFF),
            'cmpwi cr7, r12, 0',
            'beqlr cr7',
            'add r12, r12, r11',
            'lwz r12, 0x%X(r12)' % slot,            # the owner's vl: what the weapon's param getter reads
            'cmpwi cr7, r12, 0',
            'bnelr cr7',
            'li r19, 0',                            # not loaded: no instances of it in the copy's pool
            'blr']
    a = Asm(CAVE)
    a.asm('\n'.join(src))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, 'kirby copy pool cave too big'
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    out[HOOK] = (18 << 26) | ((a.labels['pool_max'] - HOOK) & 0x03FFFFFC) | 1
    return a, out


def main():
    a, out = build()
    print(' '.join('0x%08X=0x%08X' % kv for kv in sorted(out.items())))
    print('kirby copy pool cave: 0x%08X-0x%08X (%d words), owners %s' % (
        CAVE, a.pc, (a.pc - CAVE) // 4, ', '.join('0x%X:0x%X' % kv for kv in sorted(owners().items()))),
        file=sys.stderr)


if __name__ == '__main__':
    main()
