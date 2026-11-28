#!/usr/bin/env python3
"""Test fixture: a stand-in for a vanilla cross_f.rpx, made from an executable that has other mods' caves.

  python3 tools/sm4shclonetool/tests/make_vanilla_standin.py MODDED.rpx OUT.rpx

No vanilla cross_f.rpx was available where this tool was built, so the tests run on this stand-in: MODDED with
- its code section cut back to the game's end (0x04B77E1C) and the text region size back to the game's (0x2BB8670):
  every cave in the grown code space is gone;
- every word the Sm4shCloneTool's generators hook put back to the original the generators state (the kind expansion's
  switch bounds, per-kind array sites, table readers and immediates; the weapon tables' readers and switches; the
  effect-bank call sites; the custom-move functions), read the way tools/kind_expand_incremental.py reads an
  executable that already has those patches;
- the stage-slot sites put back to the game's instructions (the table readers' lis / addi on the game's tables, the
  counts 0x80 / 0x4F, `mflr r0` at the two DLC checks' entries); the four words at 0x030A926C (the DLC unlock index)
  stay as MODDED has them (their originals are not recorded in the research).
Other mods' words elsewhere (hooks into the cut-off code space, data edits) stay: the stand-in is for static and
emulated tests of the Sm4shCloneTool only and would not run in a game. Prints the words it restored.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sm4shclonetool import _paths  # noqa: E402,F401
sys.path.append(os.path.dirname(os.path.dirname(HERE)))   # the research tools (kind_expand_incremental)
from sm4shclonetool.rpx import Rpx  # noqa: E402
from sm4shclonetool import exe as E  # noqa: E402
import kind_expand as K  # noqa: E402
from ppcasm import ha  # noqa: E402


def slo(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def generator_originals(path):
    """{address: original} the generators state, read through kind_expand_incremental's overlay"""
    import kind_expand_incremental as KI
    import weapon_expand as W
    spec = os.path.join(os.path.dirname(os.path.abspath(sys.argv[2])), '.standin_spec.json')
    json.dump({'capacity': '0x60', 'kinds': [{'kind': '0x41', 'name': 'cecheck', 'cap': 'Cecheck', 'base': 'mario',
                                              'ui': {'id': 59, 'name': 'Cecheck', 'base_id': 4},
                                              'weapons': {'fireball': '0x185'}}]}, open(spec, 'w'))
    K.SPEC = spec                    # (the tool's kind_expand has no default spec)
    KI._install(path)
    over = dict(KI.OVER)
    # the weapon tables' generator: record its stated originals the same way (iterated: each pass reads more)
    seen = {}

    def put(self, addr, word, what, orig=None):
        if orig is not None:
            seen[addr] = K.one(addr, orig) if isinstance(orig, str) else orig
        self.words[addr] = word & 0xFFFFFFFF
        self.what[addr] = what
        if not W.CAVE <= addr < W.LIMIT:
            self.inplace.append(addr)
    W.Build.put = put
    for _ in range(4):
        n = len(KI.OVER)
        try:
            W.build(spec, path)
        except AssertionError as e:
            print('  weapons pass:', e)
        KI.OVER.update(seen)
        if len(KI.OVER) == n:
            break
    os.unlink(spec)
    over.update(KI.OVER)
    return over


def reloc_targets():
    """the game's tables whose readers the Sm4shCloneTool's generators repoint (their relocations target them)"""
    import weapon_expand as W
    import stage_slot_cave as SS
    t = {a for _n, a in W.NAME_TABLES} | {a for _n, a, _e, _i in W.STATIC_TABLES}
    t |= {v[0] for v in K.TABLES.values()} | {K.CHR_TABLE} | {v[0] for v in K.SOUND_NAME_TABLES.values()}
    t |= {v[3] for v in K.SWITCHES.values()} | {SS.KIND_TABLE, SS.KIND_TABLE + 4, SS.COSMETIC_TABLE}
    return t


DFORM = {12, 13, 14, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55}


def restore_relocs(x, targets):
    """relocations other caves moved onto a dummy word, put back where they were (the RELA entries are sorted by
    address and a moved entry keeps its place: its site is the matching instruction in the gap between its
    neighbours), and the instruction's immediate back to the relocation's value. Only relocations aimed at
    `targets`. Returns the number restored."""
    import struct as st
    n = 0
    for ri in x.reloc_sections():
        dat = x.data(ri)
        sym = x.data(x.secs[ri][6])
        ents = [list(st.unpack('>IIi', dat[o:o + 12])) for o in range(0, len(dat), 12)]
        count = {}
        for e in ents:
            count[e[0] & ~3] = count.get(e[0] & ~3, 0) + 1
        dummies = {a for a, c in count.items() if c > 2}
        moved = [j for j, e in enumerate(ents) if e[0] & ~3 in dummies]
        mset = set(moved)
        have = {e[0] for j, e in enumerate(ents) if j not in mset}
        last = -1
        ha_reg = {}                     # target -> (site, rD) of its last restored HA
        for j in moved:
            off, info, add = ents[j]
            typ = info & 0xFF
            val = st.unpack('>I', sym[16 * (info >> 8) + 4:16 * (info >> 8) + 8])[0]
            tgt = (val + add) & 0xFFFFFFFF
            if typ not in (4, 6) or tgt not in targets:
                continue
            p = j - 1
            while p >= 0 and p in mset:
                p -= 1
            q = j + 1
            while q < len(ents) and q in mset:
                q += 1
            lo = max(ents[p][0] if p >= 0 else 0, last)
            hi = ents[q][0] if q < len(ents) else lo + 0x400
            found = None
            for a in range(lo & ~3, (hi & ~3) + 4, 4):
                if a + 2 <= lo or a + 2 >= hi or a + 2 in have or not x.has(a):
                    continue
                w = x.r32(a)
                op = w >> 26
                if typ == 6 and op == 15:
                    found = a
                    break
                if typ == 4 and op in DFORM:
                    pair = ha_reg.get(tgt)
                    if pair is None or ((w >> 16) & 31 == pair[1] and a > pair[0]):
                        found = a
                        break
            if found is None:
                print('  relocation to 0x%08X (entry %d): no site found' % (tgt, j))
                continue
            imm = ha(tgt) if typ == 6 else tgt & 0xFFFF
            x.w32(found, (x.r32(found) & 0xFFFF0000) | imm)
            x.set_reloc_offset(ri, 12 * j, found + 2)
            have.add(found + 2)
            if typ == 6:
                ha_reg[tgt] = (found, (x.r32(found) >> 21) & 31)
            last = found + 2
            n += 1
    return n


def restore_weapon_switches(x):
    """the 13 weapon-kind switches: bound back to 0x184 and the dispatch after the bgt back to the game's form
    (tools/weapon_expand.py parse_switch(): the jump table follows the bctr); returns the jump tables"""
    import weapon_expand as W
    tables = []
    one = K.one
    for a in W.SWITCHES:
        w = x.r32(a)
        assert w >> 26 == 10, '0x%08X: no cmplwi' % a
        k = (w >> 16) & 0x1F
        x.w32(a, (w & 0xFFFF0000) | 0x184)
        b = a + 4 if x.r32(a + 4) >> 26 == 16 else a + 8
        assert x.r32(b) >> 26 == 16, '0x%08X: no bgt' % b
        p = b + 4
        w0 = x.r32(p)
        t = (w0 >> 21) & 31
        if x.r32(p) >> 26 == 15 and x.r32(p + 8) == one(p + 8, 'mtctr r%d' % t):     # patched: lis/addi/mtctr/bctr
            if t == 0:
                table = p + 24
                for i, line in enumerate(['lis r0, 0x%X' % ha(table), 'slwi r%d, r%d, 2' % (k, k),
                                          'addic r0, r0, %d' % slo(table), 'add r0, r%d, r0' % k]):
                    x.w32(p + 4 * i, one(p + 4 * i, line))
                assert x.r32(p + 16) == one(p + 16, 'mtctr r0') and x.r32(p + 20) == 0x4E800420
            else:
                table = p + 20
                for i, line in enumerate(['slwi r%d, r%d, 2' % (k, k), 'addis r%d, r%d, 0x%X' % (t, k, ha(table)),
                                          'addi r%d, r%d, %d' % (t, t, slo(table)), 'mtctr r%d' % t]):
                    x.w32(p + 4 * i, one(p + 4 * i, line))
                assert x.r32(p + 16) == 0x4E800420
            tables.append(table)
    for a, _reg in W.INTO_LAST:
        x.w32(a, (x.r32(a) & 0xFFFF0000) | 0x184)
    return tables


STAGE = [  # (address, original instruction) of tools/stage_slot_cave.py's in-place sites, the game's tables
    (0x02D1FE24, 'li r3, 0x80'), (0x02D1FD80, 'cmplwi r3, 0x80'),
    (0x02D1FD90, 'addis r12, r11, 0x%X' % ha(0x1011D95C)), (0x02D1FD94, 'lwz r0, %d(r12)' % slo(0x1011D95C)),
    (0x02D1FDA0, 'lis r10, 0x%X' % ha(0x1011D95C)), (0x02D1FDA8, 'addi r10, r10, %d' % slo(0x1011D95C)),
    (0x02D1FE10, 'lis r12, 0x%X' % ha(0x1011D960)), (0x02D1FE18, 'addi r12, r12, %d' % slo(0x1011D960)),
    (0x03014720, 'cmplwi r31, 0x80'), (0x0293DCE4, 'lis r3, 0x%X' % ha(0x1033C100)), (0x0293DCE8, 'li r4, 0x4F'),
    (0x0293DCEC, 'addi r3, r3, %d' % slo(0x1033C100)), (0x030A8D78, 'mflr r0'), (0x030A8E58, 'mflr r0')]
# words other mods hooked that the tests run through, put back (their originals: the game's sibling code shows them)
OTHERS = [
    (0x02D1FDD8, 'lwzx r5, r10, r8'),         # the stage path function (its siblings at 0x02D1FDEC / 0x02D1FE00)
    (0x02A53C68, 'bge 0x02A53C94'),           # the save-record getter: index >= count -> the null record
    (0x02A53C6C, 'mulli r0, r4, 0x50'),       # (then lwz r12, 0(r3); add r4, r12, r0 as at 0x02A53C70)
]


def main():
    src, dst = sys.argv[1:3]
    x = Rpx(src)
    tables = restore_weapon_switches(x)
    nrel = restore_relocs(x, reloc_targets() | set(tables))
    tmp = dst + '.relocs.rpx'
    x.save(tmp)
    over = generator_originals(tmp)
    x = Rpx(tmp)
    os.unlink(tmp)
    print('relocations restored: %d' % nrel)
    x.set_text_end(E.VANILLA_TEXT_END)
    x.set_text_region(E.VANILLA_REGION)
    n = 0
    for a, w in sorted(over.items()):
        if a < E.VANILLA_TEXT_END or a >= 0x10000000:
            if x.r32(a) != w:
                x.w32(a, w)
                n += 1
    for a, t in STAGE + OTHERS:
        w = K.one(a, t)
        if x.r32(a) != w:
            x.w32(a, w)
            n += 1
    x.save(dst)
    print('stand-in %s: %d words restored, code section cut to 0x%08X, text region 0x%X'
          % (dst, n, E.VANILLA_TEXT_END, E.VANILLA_REGION))
    info = E.inspect(dst)
    print('inspect:', info['state'], info.get('problems'))


if __name__ == '__main__':
    main()
