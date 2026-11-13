#!/usr/bin/env python3
"""Kirby's copies of fighters granted as another fighter's copy: their params loaded, and no pooled weapon without its
owner's params (crash fixes v4 / v5). Prints rpx_patch.py arguments; reads the base executable (the one it patches):

  python3 tools/rpx_patch.py EXE_V45D.rpx EXE_V45F.rpx $(python3 tools/kirby_copy_pool_cave.py EXE_V45D.rpx)
  python3 tools/kirby_copy_pool_test.py EXE_V45F.rpx EXE_V45D.rpx

**v4 (user, bisect v3: Kirby vs Mario, gaining Mario's copy):** PPC IP 0x04BB3350 `lwz r11, 0x160(r8)`, r8 = 0:
weapon_expand.py's copy of the Kamehameha's (weapon 0x18B) param getter read Supamario's vl slot [mgr + 0x26B4], empty
with no Supamario in the match. A copy's pool builder (0x02EFDB88, called by copy_grant at 0x02EFCEAC) makes `max`
instances of every record of the copy's list (weapon create 0x02BF42E8 -> ... -> the module set-up's +0x18 param getter
call 0x02BCB9F4), and this mod's copy lists hold other fighters' weapons: Mario's the Kamehameha, Robin's (the Hero /
Sephiroth copies are granted as Robin's, kirby_copy_new_cave.py) Hero's 0x190 / 0x193-0x197 and Sephiroth's 0x18C.

**v5 (user, exe_v45e: Kirby vs Sephiroth, copying him):** PPC IP 0x031DD364 `lwz r7, 0x1B0(r8)`, r8 = 0x9F16CDAC,
r17 = 0xB6: Robin's own thunder (a vanilla weapon) in the Robin copy's pool, its getter 0x031DD350 reading Robin's
[mgr + 0x11CC] (0x111C + 4 x 0x2C) with no Robin in the match. The vl pointers are never cleared (the manager's
constructor clears the reference counts, mgr + 0x2730 + 4 x kind for all 0x60 kinds (kind_expand.py's relocated
array), not the vl arrays): an unloaded fighter's slot is whatever the heap held. Two fixes:

1. **The granted kind's params come with the fighter** (the root of v5): a fighter granted as another kind's copy
   (kirby_copy_new_cave.py MAP) runs that kind's native copy code (its special params: the loader 0x02F1B8B0 reads
   [mgr + 0x111C + 4 x copy kind]; its weapons' getters), so that kind's vl must be loaded. A new kind's vl load case
   (kind_expand.py copy_load_case) already loads its base's first (`mr r3, r29; li r4, base; bl 0x02EA6BC4`) and its
   unload case releases it last (`mr r3, r30; li r4, base; bl 0x02EA5D64; b 0x02EA6AF4`): Supamario (base Mario, granted
   Mario) and Hero (base Robin, granted Robin) are covered; Sephiroth (base Zelda, granted Robin) is not. For every
   such kind the load case's first word goes through a stub that loads the granted kind's vl first (refcounted, as the
   base's), and the unload case's final `b` through one that releases it.
2. **No pooled instance of a weapon whose owner's params aren't loaded** (v4, now for every weapon kind): the pool
   builder's read of a record's instance count (0x02EFDC74 `lwz r19, 4(r11)`, r17 = the record's kind word) -> a stub
   that keeps it, except 0 when the weapon's owner fighter has reference count 0: the path a vanilla max-0 record
   takes (no instances, not registered). Owners: the fighter whose vl slot the weapon's param getters (descriptor +0x18
   / +0x24) read (old array 0x111C + 4k or kind_expand's 0x25B0 + 4k), else the weapon's owner name (0x10418FF0) as a
   fighter name (0x102FF484), else none (kept); weapon_expand.py's kinds (0x185 on) from extra_kinds.json. A weapon left
   out is never generated: its copy path needs its owner in the match (0x100000A0's marker comes from the copied kind).
   Registers: r11 / r12 (dead there) and cr7; cr0 (the `rlwinm.` before the hook, tested after it) kept.

Space: 0x04BAFA00-0x04BB0000, free code in kind_expand.py's region after kirby_hero_menu_cave.py's, the standard code
region; no hooked word carries a relocation (rpx_patch.py refuses one).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kind_expand as K  # noqa: E402
import kirby_copy_new_cave as NEWCOPY  # noqa: E402
import weapon_expand as W  # noqa: E402
from ppcasm import Asm  # noqa: E402

CAVE = 0x04BAFA00
LIMIT = 0x04BB0000
HOOK = 0x02EFDC74               # lwz r19, 4(r11): the record's instance count (pool builder 0x02EFDB88)
HOOK_WORD = 0x826B0004
PARAM_MGR = 0x102FF448          # [0x10300000 - 0xBB8]: FighterParamManager
FIRST_NEW = W.OLD_N             # 0x185
DESC_TABLE = 0x0320D954         # the weapon descriptor getter's jump table (vanilla kinds: kept by weapon_expand.py)
WEAPON_OWNER = 0x10418FF0       # owner name per vanilla weapon kind
FIGHTER_NAME = 0x102FF484       # lowercase name per vanilla fighter kind
OLD_FIGHTERS = 0x41
VL_OLD = 0x111C
NO_OWNER = 0xFF
VL_LOAD, VL_UNLOAD, VL_UNLOAD_TAIL = K.VL_LOAD, K.VL_UNLOAD, K.VL_UNLOAD_TAIL
LOAD_SWITCH, UNLOAD_SWITCH = 0x02EA6C9C, 0x02EA5DAC     # lis r0, hi; (slwi); addic r0, r0, lo: the case tables


def layout():
    fcap, _k = K.load_spec(K.SPEC)
    lay = K.mgr_layout(fcap)[0]
    return lay['vl'][1], lay['refcnt'][1]


def new_owners(spec=K.SPEC):
    """{new weapon kind: owner fighter kind} from extra_kinds.json's "weapons" """
    out = {}
    for r in json.load(open(spec))['kinds']:
        for _art, v in (r.get('weapons') or {}).items():
            out[K.num(v['kind'] if isinstance(v, dict) else v)] = K.num(r['kind'])
    return out


def descriptor(img, kind):
    """a vanilla weapon kind's descriptor (its case: lis / addi r3; blr), or None"""
    c = W.case_target(img, DESC_TABLE, kind)
    w1, w2, w3 = img.w(c), img.w(c + 4), img.w(c + 8)
    if w1 >> 26 == 15 and (w1 >> 21) & 31 == 3 and w2 >> 26 == 14 and w3 == 0x4E800020:
        return (((w1 & 0xFFFF) << 16) + K.sx16(w2)) & 0xFFFFFFFF
    return None


def getter_fighters(img, fn, vl_new):
    """fighter kinds whose vl slot a param getter reads (`lwz rX, slot(rY)`), straight to its blr"""
    out = set()
    for i in range(48):
        w = img.w(fn + 4 * i)
        if w >> 26 == 32:
            off = w & 0xFFFF
            if VL_OLD <= off < VL_OLD + 4 * OLD_FIGHTERS and off % 4 == 0:
                out.add((off - VL_OLD) // 4)
            elif vl_new <= off < vl_new + 4 * 0x60 and off % 4 == 0:
                out.add((off - vl_new) // 4)
        if w == 0x4E800020:
            break
    return out


def owners(img):
    """{weapon kind: (owner fighter kind or None, how)} for every kind up to the last new one"""
    vl_new, _rc = layout()
    fnames = [img.cstr(img.w(FIGHTER_NAME + 4 * k)) for k in range(OLD_FIGHTERS)]
    out = {}
    for k in range(FIRST_NEW):
        d = descriptor(img, k)
        got = set()
        if d:
            for off in (0x18, 0x24):
                g = img.w(d + off)
                if 0x02000000 <= g < 0x10000000:
                    got |= getter_fighters(img, g, vl_new)
        if len(got) == 1:
            out[k] = (got.pop(), 'getter')
            continue
        assert not got, 'weapon 0x%X: its getters read several fighters\' params %s' % (k, sorted(got))
        name = img.cstr(img.w(WEAPON_OWNER + 4 * k))
        out[k] = (fnames.index(name), 'name') if name in fnames else (None, 'none')
    for k, f in new_owners().items():
        out[k] = (f, 'extra_kinds')
    assert sorted(out) == list(range(len(out))), 'weapon kinds not consecutive'
    return out


def case_table(img, at):
    """the table of a kind_expand.py switch: `lis r0, hi` at `at`, `addic r0, r0, lo` two words on"""
    w1, w2 = img.w(at), img.w(at + 8)
    assert w1 >> 16 == 0x3C00 and w2 >> 16 == 0x3000, 'switch at 0x%08X' % at
    return (((w1 & 0xFFFF) << 16) + K.sx16(w2)) & 0xFFFFFFFF


def grant_loads(img):
    """[(kind, base, granted, load case, unload case's final b)]: kinds granted as a copy kind other than their base"""
    _f, kinds = K.load_spec(K.SPEC)
    fnames = [img.cstr(img.w(FIGHTER_NAME + 4 * k)) for k in range(OLD_FIGHTERS)]
    base = {r['kind']: fnames.index(r['base']) for r in kinds}
    lt, ut = case_table(img, LOAD_SWITCH), case_table(img, UNLOAD_SWITCH)
    out = []
    for k, granted, _m in NEWCOPY.MAP:
        if base[k] == granted:
            continue
        load = img.w(lt + 4 * k)
        assert [img.w(load), img.w(load + 4) & 0xFFFF0000, W._bl_target(load + 8, img.w(load + 8))] == \
            [0x7FA3EB78, 0x38800000, VL_LOAD] and img.w(load + 4) & 0xFFFF == base[k], \
            'kind 0x%X: load case 0x%08X is not kind_expand.py\'s (mr r3, r29; li r4, base; bl load)' % (k, load)
        a = img.w(ut + 4 * k)
        for _i in range(64):
            if img.w(a) == 0x7FC3F378 and img.w(a + 4) == 0x38800000 | base[k] and \
                    W._bl_target(a + 8, img.w(a + 8)) == VL_UNLOAD and img.w(a + 12) >> 26 == 18 and \
                    not img.w(a + 12) & 3 and K.branch_target(a + 12, img.w(a + 12)) == VL_UNLOAD_TAIL:
                break
            a += 4
        else:
            raise AssertionError('kind 0x%X: no base release in its unload case' % k)
        out.append((k, base[k], granted, load, a + 12))
    return out


def build(img):
    vl_new, refcnt = layout()
    own = owners(img)
    last = max(own)
    table = [NO_OWNER if own[k][0] is None else own[k][0] for k in range(last + 1)]
    table += [NO_OWNER] * (-len(table) % 4)
    src = ['owner_tab:'] + ['.word 0x%08X' % int.from_bytes(bytes(table[i:i + 4]), 'big')
                            for i in range(0, len(table), 4)]
    src += ['pool_max:',
            'lwz r19, 4(r11)',                      # the replaced word
            'clrlwi r12, r17, 2',                   # the record's kind (its top bits are flags)
            'cmplwi cr7, r12, 0x%X' % last,
            'bgtlr cr7',
            'lis r11, owner_tab@ha',
            'addi r11, r11, owner_tab@l',
            'lbzx r11, r11, r12',                   # the owner fighter kind
            'cmplwi cr7, r11, 0x%X' % NO_OWNER,
            'beqlr cr7',
            'slwi r11, r11, 2',
            'lis r12, 0x%X' % ((PARAM_MGR + 0x8000) >> 16),
            'lwz r12, %d(r12)' % K.sx16(PARAM_MGR & 0xFFFF),
            'cmpwi cr7, r12, 0',
            'beqlr cr7',
            'add r12, r12, r11',
            'lwz r12, 0x%X(r12)' % refcnt,          # the owner's vl reference count
            'cmpwi cr7, r12, 0',
            'bnelr cr7',
            'li r19, 0',                            # not loaded: no instances of it in the copy's pool
            'blr']
    grants = grant_loads(img)
    for k, _b, granted, _load, _ub in grants:
        src += ['load_%x:' % k,                     # bl from the load case's first word (mr r3, r29), r29 = mgr
                'mflr r0', 'stwu r1, -0x10(r1)', 'stw r0, 0x14(r1)',
                'mr r3, r29', 'li r4, 0x%X' % granted, 'bl 0x%08X' % VL_LOAD,
                'lwz r0, 0x14(r1)', 'mtlr r0', 'addi r1, r1, 0x10',
                'mr r3, r29', 'blr',
                'unload_%x:' % k,                   # b from the unload case's last word, after its base's release
                'mr r3, r30', 'li r4, 0x%X' % granted, 'bl 0x%08X' % VL_UNLOAD,
                'b 0x%08X' % VL_UNLOAD_TAIL]
    a = Asm(CAVE)
    a.asm('\n'.join(src))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, 'kirby copy pool cave too big'
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    out[HOOK] = (18 << 26) | ((a.labels['pool_max'] - HOOK) & 0x03FFFFFC) | 1
    for k, _b, _g, load, ub in grants:
        out[load] = (18 << 26) | ((a.labels['load_%x' % k] - load) & 0x03FFFFFC) | 1
        out[ub] = (18 << 26) | ((a.labels['unload_%x' % k] - ub) & 0x03FFFFFC)
    return a, out, own, grants


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    img = K.Image(sys.argv[1])
    a, out, own, grants = build(img)
    print(' '.join('0x%08X=0x%08X' % kv for kv in sorted(out.items())))
    print('kirby copy pool cave: 0x%08X-0x%08X (%d words); %d weapon owners; granted kinds\' params: %s' % (
        CAVE, a.pc, (a.pc - CAVE) // 4, sum(1 for v in own.values() if v[0] is not None),
        ', '.join('0x%X loads 0x%X (load case 0x%08X, release at 0x%08X)' % (k, g, ld, ub)
                  for k, _b, g, ld, ub in grants)), file=sys.stderr)


if __name__ == '__main__':
    main()
