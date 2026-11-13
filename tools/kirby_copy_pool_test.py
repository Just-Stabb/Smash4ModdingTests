#!/usr/bin/env python3
"""Tests tools/kirby_copy_pool_cave.py's patch (crash fix v4): runs its stub in unicorn from the patched RPX.

  python3 tools/kirby_copy_pool_test.py PATCHED.rpx ORIGINAL.rpx       (exe_v45e, exe_v45d)

- the original at the hook: `lwz r19, 4(r11)` in the pool builder, after its `rlwinm. r10, r17, 0, 0, 0` (cr0, tested
  by the `bne` right after the hook), r12 / r11 rewritten before they're read again (0x02EFDCA4 / 0x02EFDCCC);
  the cave free; the Kamehameha's getter copy reads Supamario's slot (the crash: [mgr + 0x26B4]);
- the stub, for every record kind 0-0x1A0 (with and without the flag bits) and every owner present / absent:
  r19 = the record's count, except 0 for a new weapon kind whose owner's vl slot is empty; cr0 and every register
  but r11 / r12 / cr7 as they were; a null FighterParamManager keeps the count;
- the hook is a bl to it, and no word the build changed is rewritten by a relocation (kirby_copy_new_test.py's check).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kirby_copy_pool_cave as C  # noqa: E402
from kirby_copy_new_test import Img, reloc_clashes, bl_target  # noqa: E402
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_0, UC_PPC_REG_LR, UC_PPC_REG_CR  # noqa: E402

FAIL = []
MGR = 0x7E000000
RET = 0x7F00FFF0


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        FAIL.append(what)


def main():
    new, old = Img(sys.argv[1]), Img(sys.argv[2])
    check('original 0x%08X lwz r19, 4(r11)' % C.HOOK, old.w(C.HOOK), C.HOOK_WORD)
    check('original 0x02EFDC70 rlwinm. r10, r17, 0, 0, 0 / 0x02EFDC78 bne (cr0 live across the hook)',
          (old.w(0x02EFDC70), old.w(0x02EFDC78) >> 16), (0x562A0001, 0x4082))
    check('original r12 / r11 rewritten before read (0x02EFDCA4 lwz r12, 0x24(r3); 0x02EFDCCC lwz r11, 0xC(r1))',
          (old.w(0x02EFDCA4), old.w(0x02EFDCCC)), (0x81830024, 0x8161000C))
    check('the Kamehameha getter copy reads [mgr + 0x26B4] (Supamario\'s slot; the crash at 0x04BB3350)',
          old.w(0x04BB334C) & 0xFFFF, C.vl_new() + 4 * 0x41)
    for a in range(C.CAVE, C.LIMIT, 4):
        if old.w(a):
            check('cave 0x%08X free in the original' % a, old.w(a), 0)
    a, out = C.build()
    lab = a.labels
    check('every patched word in place', [hex(k) for k, v in sorted(out.items()) if new.w(k) != v], [])
    check('0x%08X bl pool_max' % C.HOOK, bl_target(C.HOOK, new.w(C.HOOK)), lab['pool_max'])
    check('no word the build changed is rewritten by a relocation', reloc_clashes(new, old), [])
    check('cave inside the proven code region', C.CAVE >= 0x04B00000 and a.pc <= C.LIMIT <= 0x04BD4000, True)

    mu = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
    mu.mem_map(C.CAVE & ~0xFFF, 0x1000)
    mu.mem_write(C.CAVE & ~0xFFF, new.read(C.CAVE & ~0xFFF, 0x1000))
    mu.mem_map(C.PARAM_MGR & ~0xFFF, 0x1000)
    mu.mem_map(MGR, 0x4000)
    mu.mem_map(0x7F000000, 0x10000)
    own = C.owners()
    slot = C.vl_new()
    bad = []
    keep = [r for r in range(32) if r not in (11, 12, 19)]
    for mgr_set in (True, False):
        mu.mem_write(C.PARAM_MGR, struct.pack('>I', MGR if mgr_set else 0))
        for kind in range(0x1A1):
            for flags in (0, 0x40000000):
                for present in (False, True):
                    o = own.get(kind)
                    mu.mem_write(MGR, b'\0' * 0x4000)
                    for k in range(0x60):              # every other fighter loaded, the owner per `present`
                        if k != o or present:
                            mu.mem_write(MGR + slot + 4 * k, struct.pack('>I', 0x10600000 + k))
                    rec = 0x7F000100
                    mu.mem_write(rec, struct.pack('>II', kind | flags, 5))
                    regs = {r: 0x1000 + r for r in range(32)}
                    regs.update({11: rec, 17: kind | flags, 19: 0xDEAD, 1: 0x7F008000})
                    for r, v in regs.items():
                        mu.reg_write(UC_PPC_REG_0 + r, v)
                    cr = 0x20000004 | (0x8 << 4)      # cr0 "gt", cr6 / cr7 bits set
                    mu.reg_write(UC_PPC_REG_CR, cr)
                    mu.reg_write(UC_PPC_REG_LR, RET)
                    mu.emu_start(lab['pool_max'], RET, count=100)
                    want = 0 if (o is not None and not present and mgr_set) else 5
                    got = mu.reg_read(UC_PPC_REG_0 + 19)
                    regs_out = [mu.reg_read(UC_PPC_REG_0 + r) for r in keep]
                    cr_out = mu.reg_read(UC_PPC_REG_CR)
                    if got != want or regs_out != [regs[r] for r in keep] or (cr_out ^ cr) & 0xFFFFFFF0:
                        bad.append((hex(kind | flags), present, mgr_set, got, want, hex(cr_out)))
    check('stub: count kept, 0 for a new weapon kind whose owner is not loaded; cr0-cr6 and other registers kept',
          bad[:8], [])
    print('%d failures' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
