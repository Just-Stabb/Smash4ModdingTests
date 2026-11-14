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
- fix v4 (the user: the sword still never shows): the copy model function run from the hat's generate (0x02EFE254)
  to its kind chain, the hat made (the Hero copy's case) and not: the Hero copy (grant 0x45, kind 0x2C) must reach
  the held article's generate 0x02EFE748 both ways, every other pair must not. A third argument (exe_v46f, fix v2's)
  shows the failure: with the hat made it went 0x02EFE284 -> 0x02EFE6A0 -> 0x02EFE7EC, past the v6 stub at
  0x02EFE664 (reached only when the hat failed). The two other reads of the held-item table for the slot
  (0x030C49D8 the c00 fallback, 0x030C4BE8 the motion folder) give "bravesword" too.

  python3 tools/kirby_hero_sword_test.py PATCHED.rpx ORIGINAL.rpx [OLD_PATCHED.rpx]   (exe_v46g, exe_v45h, exe_v46f)
- fix v5: the stone check only for the Hero copy's article (r31 0x2C) and to the new stone_show (CAVE2), whose words
  and the original show path / Sonic branch it relies on are checked here; the init's 0x2C case on the Marth path. The
  run of the whole chain with the game's own Visibility / Link modules is tools/kirby_hero_sword_vis_test.py.
  (exe_v46h = exe_v46g + sound_alias_cave.py v2 (ported_sound_ids_v1) + this: the ORIGINAL argument stays exe_v45h.)
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
                       (C.GEN_ARTICLE & ~0xFFF, 0x1000), (C.HOOK_ITEM2 & ~0xFFF, 0x1000), (0x10150000, 0x10000), (0x10400000, 0x40000)):
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


GEN_FROM = 0x02EFE254           # lwz r3, 0x7284(r24): the hat's generate (article 0x19) on a granted kind
HAT_GENERATE, HAT_ATTACH = 0x02EFE268, 0x02EFE280      # bl 0x02C03EA0 / bl 0x02C04EA4
GEN_ENDS = (0x02EFE748, 0x02EFE7EC, 0x02EFE814)        # the held article's generate / the common tails


def gen_path(img, grant, kind, hat_made):
    """where the copy model function goes from the hat's generate (the calls stubbed: the hat made or not)"""
    mu = emu(img)
    mu.mem_write(HAT_GENERATE, struct.pack('>I', 0x38600001 if hat_made else 0x38600000))     # li r3, 1 / 0
    mu.mem_write(HAT_ATTACH, struct.pack('>I', 0x60000000))
    a44, _r = V44.args()
    mu.mem_write(a44.labels['grant_kind'], struct.pack('>I', grant))
    return run(mu, GEN_FROM, {27: kind, 24: STUBS + 0x8000, 1: 0x7F008000}, set(GEN_ENDS))


def main():
    new, old = Img(sys.argv[1]), Img(sys.argv[2])
    prev = Img(sys.argv[3]) if len(sys.argv) > 3 else None
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
    for a in list(range(C.CAVE, C.LIMIT, 4)) + list(range(C.CAVE2, C.LIMIT2, 4)):      # fix v5: CAVE2 too
        if old.w(a):
            check('cave 0x%08X free in the original' % a, old.w(a), 0)
    if prev:
        check('fix v5: CAVE2 (0x%08X-0x%08X) free in %s' % (C.CAVE2, C.LIMIT2, os.path.basename(sys.argv[3])),
              [hex(a) for a in range(C.CAVE2, C.LIMIT2, 4) if prev.w(a)], [])
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
    # fix v4
    for at, w in sorted(C.ORIGINAL.items()):
        check('fix v4: original 0x%08X = 0x%08X' % (at, w), old.w(at), w)
    check('fix v4: 0x%08X bl gen_stub (the hat\'s success path)' % C.HOOK_GEN2, bl_target(C.HOOK_GEN2, new.w(C.HOOK_GEN2)),
          lab['gen_stub'])
    for h in (C.HOOK_ITEM2, C.HOOK_ITEM3):
        check('fix v4: 0x%08X bl name_item' % h, bl_target(h, new.w(h)), lab['name_item'])
    check('fix v4: the hat\'s success path compares the kind itself (0x%08X cmplwi r27, 0x22; bge 0x02EFE6A0; b 0x02EFE66C)'
          % C.HOOK_GEN2, [hex(old.w(C.HOOK_GEN2 + 4 * i)) for i in range(3)], ['0x281b0022', '0x40800418', '0x480003e0'])
    bad = []
    for grant, kind in ((0x45, 0x2C), (0x42, 0x2C), (0x2C, 0x2C), (0x45, 0x12), (0x12, 0x12), (0x41, 0x1), (0, 0x2B)):
        for hat in (True, False):
            want = 0x02EFE748 if (grant, kind) == (0x45, 0x2C) or kind in (0x1, 0x12, 0x2B) else None
            got = gen_path(new, grant, kind, hat)
            if (want and got != want) or (not want and got == 0x02EFE748):
                bad.append((hex(grant), hex(kind), hat, hex(got)))
    check('fix v4: the copy model function from the hat\'s generate: the Hero copy reaches the held article\'s generate '
          '(0x02EFE748) with the hat made and not; Robin\'s / Sephiroth\'s copy never; Marth / Ike-style kinds as before', bad, [])
    if prev:
        check('fix v4: the failure in the old build (%s): the Hero copy with its hat made never reaches the held '
              'article\'s generate (0x02EFE7EC); with the hat failing it did' % os.path.basename(sys.argv[3]),
              (hex(gen_path(prev, 0x45, 0x2C, True)), hex(gen_path(prev, 0x45, 0x2C, False))),
              (hex(0x02EFE7EC), hex(0x02EFE748)))
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
    bad = []
    for h, reg in ((C.HOOK_ITEM2, 11), (C.HOOK_ITEM3, 12)):
        for k in (0x45, 0x2C, 0x12):
            mk = mapping.get(k, k)
            mu.mem_write(a44.labels['res_kind'], struct.pack('>I', k))
            end = run(mu, h, {21: 4 * mk, reg: 4 * mk, 24: 0x1041A8A0, 28: mk, 7: 0}, {h + 4})
            got = mem_cstr(mu, mu.reg_read(UC_PPC_REG_0 + 7))
            want = C.ITEM_NAME if k == C.BRAVE else new.cstr(new.w(0x1041A8A0 + 4 * mk))
            if got != want or end != h + 4:
                bad.append((hex(h), hex(k), got, hex(end)))
    check('fix v4: the c00 fallback and motion-folder reads: "bravesword" for a Hero slot, the table\'s own else', bad, [])
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
    stone_show = lab['stone_show']
    stop = {HELD.SHOW, C.HELD_BACK, stone_show}
    for kind in (0x2C, 0x12):
        for status in (0x155, 0x175, 0x176, 0x154, 0x177, 0x222, 0):
            for motion in (0x380, 0x382, 0x384, 0x381, 0x10):
                for sword in (0, 1, 2):
                    acc, held = fake_modules(mu, status, motion, sword)
                    end = run(mu, HELD.HOOK, {27: acc, 30: held, 31: kind, 1: 0x7F008000}, stop)
                    stone = kind == C.ROBIN and status in C.STONE and sword == 1
                    want = HELD.SHOW if motion in HELD.MOTIONS else stone_show if stone else C.HELD_BACK
                    ok = end == want and (want != C.HELD_BACK or mu.reg_read(UC_PPC_REG_0 + 3) == 0x7E00A800)
                    if not ok:
                        bad.append((hex(kind), hex(status), hex(motion), sword, hex(end)))
    check('held model: shown in the Marth sword motions; the Hero copy\'s (kind 0x2C) to the fix v5 stone show path in '
          'the stone statuses with 0x1000008B == 1, never another kind\'s; else hidden (r3 = the +0xA8 module)', bad, [])
    # fix v5: the stone show path's words (its run, with the game's own modules: kirby_hero_sword_vis_test.py)
    img = new
    sw = [img.w(stone_show + 4 * i) for i in range(18)]
    check('fix v5: stone_show calls the show path\'s 0x02BF0594 (r3 = r1 + 0x68) and the item MotionModule vt +0x2F4, '
          'then goes to the Sonic branch 0x02B02794 with r7 = [r30 + 0x68], r10 = [r7] + 0x3C0',
          (sw[0], (sw[1] & 0xFFFF) << 16 | (sw[2] & 0xFFFF), sw[5:10], sw[10:13], (sw[13] & 0xFFFF) << 16 | (sw[14] & 0xFFFF),
           sw[15:17]),
          (0x38610068, C.SHOW_SYNC, [0x807E0044, 0x80C30000, 0x80E602F4, 0x7CE903A6, 0x4E800421],
           [0x80FE0068, 0x81470000, 0x394A03C0], C.SONIC_SHOW, [0x7D8903A6, 0x4E800420]))
    check('fix v5: the original show path\'s preamble and the Sonic branch are where stone_show expects them',
          (bl_target(0x02B026B8, old.w(0x02B026B8)), [hex(old.w(0x02B026BC + 4 * i)) for i in range(5)],
           [hex(old.w(0x02B02718 + 4 * i)) for i in (0, 1, 3)], [hex(old.w(C.SONIC_SHOW + 4 * i)) for i in range(6)]),
          (C.SHOW_SYNC, ['0x807e0044', '0x80c30000', '0x80e602f4', '0x7ce903a6', '0x4e800421'],
           ['0x80fe0068', '0x81470000', '0x394a03c0'],
           ['0x816a0004', '0x7d6903a6', '0x38a00007', '0x38800003', '0x7ce33b78', '0x4e800421']))
    check('fix v5: the init\'s kind 0x2C case re-aimed at the Marth path (0x02B02184 beq 0x02B022EC: li r5, 0x18; '
          'flags r28 = 0x108); original beq 0x02B02248 (joint 0x19, flags 8)',
          (hex(old.w(C.HOOK_JOINT)), hex(new.w(C.HOOK_JOINT)), hex(old.w(C.HOOK_JOINT - 8)),
           hex(old.w(C.MARTH_LINK + 0xC)), hex(old.w(0x02B02248 + 0x20))),
          ('0x418200c4', '0x41820168', '0x281f002c', '0x38a00018', '0x38800008'))
    print('%d failures' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
