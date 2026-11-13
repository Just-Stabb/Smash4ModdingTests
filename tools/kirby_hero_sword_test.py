#!/usr/bin/env python3
"""Tests tools/kirby_hero_sword_cave.py's patch (exe_v46): runs its code in unicorn from the patched RPX.

  python3 tools/kirby_hero_sword_test.py PATCHED.rpx ORIGINAL.rpx      (exe_v46, exe_v45c)

- the original has what the patch expects: the held-item read 0x030C487C `lwzx r7, r24, r21` with r24 the held-item
  table (decoded from the loader's own lis / addi, as the hat read's check), the kind compare 0x02EFE664, the held
  article's generate at 0x02EFE748 (li r4, 0x1A, then bl 0x02C03EA0), copy_held_cave.py's hide path (0x037EE5CC
  lwz r3, 0xA8(r30); b 0x02B02734) and the hook at 0x02B02730; the cave space free; kirby_copy_new_cave.py's words
  (grant_kind / res_kind) where the stubs read them;
- the cave lies in the code region the standard build already runs (below 0x04BD4000: crash fix v1) and no section
  grew (the text section's address / size the same as the original's);
- the held-item name: "bravesword" for a Hero player's slot, every other kind the table's own (kinds 0-0x50);
- the generate stub: for (grant kind 0x45, r27 0x2C) it returns into 0x02EFE748; for every other pair (Sephiroth,
  Robin, Supamario's Mario, -1) it returns to its caller with cr0 as `cmplwi r27, 0x22` sets it;
- the held model's visibility, the whole chain from the hook (0x02B02730) with a stub status / motion / work module:
  shown (0x02B026B4) in the Marth sword motions 0x380 / 0x382 / 0x384 (as before) and in the stone statuses 0x155 /
  0x175 / 0x176 when Kirby's int 0x1000008B is 1; else hidden (0x02B02734, r3 = the module at +0xA8).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kirby_copy_new_cave as V44  # noqa: E402
import kirby_hero_sword_cave as C  # noqa: E402
import copy_held_cave as HELD  # noqa: E402
from kirby_copy_new_test import Img, bl_target, mem_cstr  # noqa: E402
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_0, UC_PPC_REG_LR, UC_PPC_REG_CR  # noqa: E402

FAIL = []
RET = 0x7F00FFF0
STUBS = 0x7E000000          # fake modules: vtables and their functions


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        FAIL.append(what)


def sections(img):
    """(address, decompressed size) of each loaded section"""
    return [(b, len(data)) for b, data in img.segs]


def emu(img):
    mu = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
    for base, size in ((C.CAVE & ~0xFFF, 0x2000), (HELD.CAVE & ~0xFFF, 0x1000), (HELD.HOOK & ~0xFFF, 0x1000),
                       (C.GEN_ARTICLE & ~0xFFF, 0x1000), (0x10150000, 0x10000), (0x10400000, 0x40000)):
        mu.mem_map(base, size)
        mu.mem_write(base, img.read(base, size))
    mu.mem_map(0x7F000000, 0x10000)
    mu.mem_map(STUBS, 0x10000)
    return mu


def run(mu, at, regs, stop):
    """runs from at until pc is in stop (a set) or the fake return; the address it stopped at"""
    for r, v in regs.items():
        mu.reg_write(UC_PPC_REG_0 + r, v & 0xFFFFFFFF)
    mu.reg_write(UC_PPC_REG_LR, RET)
    hit = []

    def hook(uc, addr, size, ud):
        if addr in stop:
            hit.append(addr)
            uc.emu_stop()
    h = mu.hook_add(UC_HOOK_CODE, hook)
    try:
        mu.emu_start(at, RET, count=400)
    finally:
        mu.hook_del(h)
    return hit[0] if hit else RET


def fake_modules(mu, status, motion, sword):
    """r27 accessor: +0x20 status module (vt +0x8C -> status), +0x28 work module (vt +0x84 -> sword for id
    0x1000008B, else 0x55), +0x44 motion module (vt +0x94 -> motion); r30 accessor: +0xA8 = 0x7E00A800"""
    def fn(at, code):
        mu.mem_write(at, b''.join(struct.pack('>I', w) for w in code))
    li = lambda r, v: (14 << 26) | (r << 21) | (v & 0xFFFF)                           # noqa: E731
    lis = lambda r, v: (15 << 26) | (r << 21) | ((v >> 16) & 0xFFFF)                  # noqa: E731
    ori = lambda r, v: (24 << 26) | (r << 21) | (r << 16) | (v & 0xFFFF)              # noqa: E731
    blr = 0x4E800020
    # functions
    fn(STUBS + 0x100, [lis(3, status), ori(3, status), blr])
    fn(STUBS + 0x200, [lis(3, motion), ori(3, motion), blr])
    # work get_int: r4 == SWORD_INT ? sword : 0x55
    fn(STUBS + 0x300, [lis(5, C.SWORD_INT), ori(5, C.SWORD_INT), 0x7C042800, 0x40820010,
                       lis(3, sword), ori(3, sword), blr, li(3, 0x55), blr])
    # vtables
    for vt, off, f in ((STUBS + 0x1000, 0x8C, STUBS + 0x100), (STUBS + 0x2000, 0x94, STUBS + 0x200),
                       (STUBS + 0x3000, 0x84, STUBS + 0x300)):
        mu.mem_write(vt + off, struct.pack('>I', f))
    # modules (their first word: the vtable)
    mu.mem_write(STUBS + 0x4000, struct.pack('>I', STUBS + 0x1000))     # status module
    mu.mem_write(STUBS + 0x4100, struct.pack('>I', STUBS + 0x2000))     # motion module
    mu.mem_write(STUBS + 0x4200, struct.pack('>I', STUBS + 0x3000))     # work module
    acc = STUBS + 0x5000
    mu.mem_write(acc + 0x20, struct.pack('>I', STUBS + 0x4000))
    mu.mem_write(acc + 0x28, struct.pack('>I', STUBS + 0x4200))
    mu.mem_write(acc + 0x44, struct.pack('>I', STUBS + 0x4100))
    held = STUBS + 0x6000
    mu.mem_write(held + 0xA8, struct.pack('>I', 0x7E00A800))
    return acc, held


def main():
    new, old = Img(sys.argv[1]), Img(sys.argv[2])
    # the original
    check('original 0x%08X lwzx r7, r24, r21' % C.HOOK_ITEM, old.w(C.HOOK_ITEM), 0x7CF8A82E)
    base = (old.w(C.HOOK_ITEM) >> 16) & 31
    adds = {}
    for a in range(0x030C46DC, 0x030C4700, 4):
        x = old.w(a)
        if x >> 26 == 14:
            adds[(x >> 21) & 31] = 0x10420000 + (((x & 0xFFFF) ^ 0x8000) - 0x8000)
    check('the item hook reads the held-item table (0x1041A8A0) through r%d' % base, adds.get(base), 0x1041A8A0)
    check('the item read is the type-0x11 branch (cmpwi r29, 0x11 before it)', old.w(C.HOOK_ITEM - 12), 0x2C1D0011)
    check('original 0x%08X cmplwi r27, 0x22' % C.HOOK_GEN, old.w(C.HOOK_GEN), 0x281B0022)
    check('original 0x%08X: the held article 0x1A generated (li r4, 0x1A; bl 0x02C03EA0)' % C.GEN_ARTICLE,
          (old.w(C.GEN_ARTICLE), old.w(C.GEN_ARTICLE + 8), bl_target(C.GEN_ARTICLE + 0x14, old.w(C.GEN_ARTICLE + 0x14))),
          (0x80787284, 0x3880001A, 0x02C03EA0))
    check('original copy_held_cave hide path (lwz r3, 0xA8(r30); b 0x02B02734)',
          (old.w(HELD.CAVE + 0x2C), bl_target(HELD.CAVE + 0x30, old.w(HELD.CAVE + 0x30) | 1)), (0x807E00A8, 0x02B02734))
    check('original 0x02B02730 b copy_held_cave', bl_target(HELD.HOOK, old.w(HELD.HOOK) | 1), HELD.CAVE)
    for a in range(C.CAVE, C.LIMIT, 4):
        if old.w(a):
            check('cave 0x%08X free in the original' % a, old.w(a), 0)
    a44, _r = V44.args()
    check('kirby_copy_new_cave.py\'s cave in the original (grant_kind / res_kind words, its code before 0x%08X)' % C.CAVE,
          (old.w(a44.labels['res_kind']), a44.pc <= C.CAVE,
           old.w(a44.labels['grant_map']) == a44.words()[(a44.labels['grant_map'] - V44.CAVE) // 4]),
          (0xFFFFFFFF, True, True))
    # crash fix v1: in the region already run, nothing grown
    a, out = C.build()
    check('cave inside the proven code region', C.CAVE >= 0x04B00000 and a.pc <= C.LIMIT <= 0x04BD4000, True)
    check('no section grew (addresses and sizes as the original\'s)', sections(new), sections(old))
    check('every patched word in place', [hex(k) for k, v in sorted(out.items()) if new.w(k) != v], [])
    lab = a.labels
    check('0x%08X bl name_item' % C.HOOK_ITEM, bl_target(C.HOOK_ITEM, new.w(C.HOOK_ITEM)), lab['name_item'])
    check('0x%08X bl gen_stub' % C.HOOK_GEN, bl_target(C.HOOK_GEN, new.w(C.HOOK_GEN)), lab['gen_stub'])
    mu = emu(new)
    mapping = {k: to for k, to, _m in V44.MAP}
    # 1. the item name
    bad = []
    for k in range(0x51):
        mk = mapping.get(k, k)
        if mk >= 0x3A or mk == 8:
            continue
        mu.mem_write(a44.labels['res_kind'], struct.pack('>I', k))
        run(mu, lab['name_item'], {21: 4 * mk, 24: 0x1041A8A0, 7: 0}, set())
        got = mem_cstr(mu, mu.reg_read(UC_PPC_REG_0 + 7))
        want = C.ITEM_NAME if k == C.BRAVE else new.cstr(new.w(0x1041A8A0 + 4 * mk))
        if got != want:
            bad.append((hex(k), got, want))
    check('held-item name: "bravesword" for a Hero slot, every other kind the table\'s own', bad, [])
    check('the table\'s Robin row is empty (the Hero copy had no held model)', new.cstr(new.w(0x1041A8A0 + 4 * 0x2C)), '')
    # 2. the generate stub
    bad = []
    for gk in (0x45, 0x42, 0x2C, 0x41, 0x12, 0):
        for r27 in (0x2C, 0x12, 0x3, 0x22, 0x21, 0x23, 0xFFFFFFFF, 0):
            mu.mem_write(a44.labels['grant_kind'], struct.pack('>I', gk))
            mu.reg_write(UC_PPC_REG_CR, 0)
            end = run(mu, lab['gen_stub'], {27: r27}, {C.GEN_ARTICLE})
            cr0 = mu.reg_read(UC_PPC_REG_CR) >> 28
            want_cr = 8 if r27 < 0x22 else 4 if r27 > 0x22 else 2
            if gk == 0x45 and r27 == 0x2C:
                ok = end == C.GEN_ARTICLE
            else:
                ok = end == RET and cr0 & 0xE == want_cr
            if not ok:
                bad.append((hex(gk), hex(r27), hex(end), cr0))
    check('generate stub: only the Hero copy (grant 0x45, kind 0x2C) goes to the article generate; else cmplwi r27, 0x22',
          bad, [])
    # 3. visibility
    bad = []
    stop = {HELD.SHOW, C.HELD_BACK}
    for status in (0x155, 0x175, 0x176, 0x154, 0x177, 0x222, 0):
        for motion in (0x380, 0x382, 0x384, 0x381, 0x10):
            for sword in (0, 1, 2):
                acc, held = fake_modules(mu, status, motion, sword)
                end = run(mu, HELD.HOOK, {27: acc, 30: held, 1: 0x7F008000}, stop)
                show = motion in HELD.MOTIONS or (status in C.STONE and sword == 1)
                want = HELD.SHOW if show else C.HELD_BACK
                ok = end == want and (show or mu.reg_read(UC_PPC_REG_0 + 3) == 0x7E00A800)
                if not ok:
                    bad.append((hex(status), hex(motion), sword, hex(end)))
    check('held model: shown in the Marth sword motions, and in the stone statuses with 0x1000008B == 1; else hidden '
          '(r3 = the +0xA8 module)', bad, [])
    print('%d failures' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
