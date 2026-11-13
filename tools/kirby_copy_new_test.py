#!/usr/bin/env python3
"""Tests tools/kirby_copy_new_cave.py's patch: runs its code in unicorn from the patched RPX and checks its data.

  python3 tools/kirby_copy_new_test.py PATCHED.rpx ORIGINAL.rpx

- the original RPX has what the cave expects at every hook (copy_grant's mr / stw, weapon_expand.py's three bl,
  the loader's two name reads), Robin's copy header / records and Kirby's free reserve entries;
- copy_grant's map: every kind 0-0x50 -> r28 (0x41 -> 3, 0x45 / 0x42 -> 0x2C, the rest unchanged), then its store:
  the kind at +0x290 and the marker (1 / 2 / 3 / 0) at +0x280 of the int array;
- the three resource stubs map every kind the same way (the loader's keeps the real kind);
- the two name reads: Hero's / Sephiroth's slot "brave" / "edge" (motion folder) and "bravecap" / "edgecap" (hat),
  every other kind the table's own name (run with the RPX's tables);
- the hooks are bl to the stubs; Robin's copy header points at 8 records (the 6 old + fireball 0x190 / fire 0x18C);
  reserve entries 15-18 name 0x18C, 0x190, 0xB6, 0xB4.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rpx_patch  # noqa: E402
import kirby_copy_new_cave as C  # noqa: E402
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_0, UC_PPC_REG_LR  # noqa: E402

FAIL = []


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        FAIL.append(what)


class Img:
    def __init__(self, path):
        d, _o, _e, secs = rpx_patch.load(path)
        self.segs = [(s[3], bytes(rpx_patch.section_data(d, s))) for s in secs if s[1] == 1 and s[3] and s[5]]

    def read(self, a, n):
        for b, data in self.segs:
            if b <= a < b + len(data):
                return data[a - b:a - b + n]
        raise KeyError(hex(a))

    def w(self, a):
        return struct.unpack('>I', self.read(a, 4))[0]

    def cstr(self, a):
        s = b''
        while self.read(a, 1) != b'\0':
            s += self.read(a, 1)
            a += 1
        return s.decode()


def bl_target(at, w):
    off = w & 0x03FFFFFC
    return at + (off - 0x04000000 if off & 0x02000000 else off)


def emu(img):
    mu = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
    mu.mem_map(C.CAVE, C.LIMIT - C.CAVE)
    mu.mem_write(C.CAVE, img.read(C.CAVE, C.LIMIT - C.CAVE))
    mu.mem_map(0x10400000, 0x40000)          # the name tables' page (0x1041A6D0 / 0x1041A7B8) and their strings
    mu.mem_write(0x10400000, img.read(0x10400000, 0x40000))
    mu.mem_map(0x10140000, 0x20000)
    mu.mem_write(0x10140000, img.read(0x10140000, 0x20000))
    mu.mem_map(0x7F000000, 0x10000)          # scratch: the int array, the return address
    return mu


def call(mu, at, regs):
    for r, v in regs.items():
        mu.reg_write(UC_PPC_REG_0 + r, v & 0xFFFFFFFF)
    mu.reg_write(UC_PPC_REG_LR, 0x7F00FFF0)
    mu.emu_start(at, 0x7F00FFF0, count=200)


def mem_cstr(mu, a):
    s = b''
    while True:
        c = bytes(mu.mem_read(a, 1))
        if c == b'\0':
            return s.decode('latin1')
        s += c
        a += 1


def main():
    new, old = Img(sys.argv[1]), Img(sys.argv[2])
    # the original at the hooks
    check('original copy_grant 0x%08X mr r28, r6' % C.HOOK_GRANT, old.w(C.HOOK_GRANT), 0x7CDC3378)
    check('original copy_grant 0x%08X stw r28, 0x290(r7)' % C.HOOK_STORE, old.w(C.HOOK_STORE), 0x93870290)
    for hook, _reg, _k in C.RES_HOOKS:
        check('original 0x%08X is a bl (weapon_expand.py\'s stub)' % hook, (old.w(hook) >> 26, old.w(hook) & 3), (18, 1))
    check('original 0x%08X lwz r7, -0x5930(r8)' % C.HOOK_BODY, old.w(C.HOOK_BODY), 0x80E8A6D0)
    check('original 0x%08X lwzx r7, r24, r21' % C.HOOK_HAT, old.w(C.HOOK_HAT), 0x7CF8A82E)
    check('Kirby copy table [0x2C] is Robin\'s header', old.w(C.COPY_TABLE + 4 * C.ROBIN), C.ROBIN_HDR)
    recs, n = old.w(C.ROBIN_HDR), old.w(C.ROBIN_HDR + 4)
    check('original Robin copy records', (recs, [tuple(old.w(recs + 16 * i + 4 * j) for j in range(4)) for i in range(n)]),
          (C.ROBIN_RECS_OLD, list(C.ROBIN_RECORDS)))
    for i, _k in C.RESERVE:
        e = C.KIRBY_RESERVE + 0x10 * i
        check('original reserve entry %d free' % i, [old.w(e + 4 * j) for j in range(4)], [0x10, 0, 0, 0])
    for a in range(C.CAVE, C.LIMIT, 4):
        if old.w(a) if a < 0x04BD4000 else 0:
            check('cave 0x%08X free in the original' % a, old.w(a), 0)
    # the patched
    a, _res = C.args()
    lab = a.labels
    for hook, name in [(C.HOOK_GRANT, 'grant_map'), (C.HOOK_STORE, 'grant_store'), (C.HOOK_BODY, 'name_body'),
                       (C.HOOK_HAT, 'name_hat')] + [(h, 'res_%X' % h) for h, _r, _k in C.RES_HOOKS]:
        w = new.w(hook)
        check('0x%08X bl %s' % (hook, name), (w >> 26, w & 3, bl_target(hook, w)), (18, 1, lab[name]))
    mapping = {k: to for k, to, _m in C.MAP}
    marker = {k: m for k, _to, m in C.MAP}
    mu = emu(new)
    bad = []
    for k in range(0x51):
        call(mu, lab['grant_map'], {6: k, 28: 0xDEAD})
        got = mu.reg_read(UC_PPC_REG_0 + 28)
        call(mu, lab['grant_store'], {7: 0x7F000000, 28: got, 11: 0x55, 12: 0x66})
        ints = struct.unpack('>5I', bytes(mu.mem_read(0x7F000280, 20)))
        if (got, ints[0], ints[4]) != (mapping.get(k, k), marker.get(k, 0), mapping.get(k, k)):
            bad.append((hex(k), hex(got), ints))
    check('copy_grant: kinds 0-0x50 mapped, kind at +0x290, marker at +0x280', bad, [])
    for hook, reg, keep in C.RES_HOOKS:
        bad = []
        for k in range(0x51):
            call(mu, lab['res_%X' % hook], {4: k, reg: 0xDEAD})
            if mu.reg_read(UC_PPC_REG_0 + reg) != mapping.get(k, k):
                bad.append(hex(k))
            if keep and struct.unpack('>I', bytes(mu.mem_read(lab['res_kind'], 4)))[0] != k:
                bad.append('kept %x' % k)
        check('resource stub 0x%08X r%d: kinds 0-0x50 mapped%s' % (hook, reg, ', real kind kept' if keep else ''), bad, [])
    for tag, table, idx in (('body', 0x1041A6D0, 0), ('hat', 0x1041A7B8, 1)):
        bad = []
        for k in range(0x51):
            mk = mapping.get(k, k)
            if mk >= 0x3A or mk == 8:
                continue            # the loader returns before reading for these
            mu.mem_write(lab['res_kind'], struct.pack('>I', k))
            regs = {8: 0x10420000 + 4 * mk, 21: 4 * mk, 24: table, 7: 0}
            call(mu, lab['name_%s' % tag], regs)
            got = mem_cstr(mu, mu.reg_read(UC_PPC_REG_0 + 7))
            want = C.NAMES[k][idx] if k in C.NAMES else new.cstr(new.w(table + 4 * mk))
            if got != want:
                bad.append((hex(k), got, want))
        check('name read %s: Hero / Sephiroth slots %s, others the table\'s' % (
            tag, '/'.join(C.NAMES[k][idx] for k in sorted(C.NAMES))), bad, [])
    recs, n = new.w(C.ROBIN_HDR), new.w(C.ROBIN_HDR + 4)
    check('Robin copy header -> the cave list, 8 records', (recs, n), (lab['robin_list'], 8))
    check('Robin copy records', [tuple(new.w(recs + 16 * i + 4 * j) for j in range(4)) for i in range(n)],
          list(C.ROBIN_RECORDS) + list(C.NEW_RECORDS))
    for i, k in C.RESERVE:
        e = C.KIRBY_RESERVE + 0x10 * i
        check('reserve entry %d names 0x%X' % (i, k), [new.w(e + 4 * j) for j in range(4)], [k, 0, 0, 0])
    print('%d failures' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
