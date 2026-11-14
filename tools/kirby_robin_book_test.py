#!/usr/bin/env python3
"""Kirby's Hero copy fix v2 (tools/kirby_robin_book_cave.py, fighters/kirby/specials.md "Hero copy fix v2"): runs the
executable's own code in unicorn.

  python3 tools/kirby_robin_book_test.py PATCHED.rpx BASE.rpx

PATCHED = BASE + kirby_robin_book_cave.py (exe_v45h = exe_v45g + it, exe_v46f = exe_v46e + it).
- the words: only the cave and the hook differ from BASE; the hooked word was `mflr r0`;
- the thunder spawner's order (the evidence): 0x02F645BC calls 0x02F613B8 before 0x02F64650 reads the custom number
  (copy_custom_cave.py's hook), and 0x02F613B8 stores its book into the owner's ints 0x9F / 0xA0 / 0xA1;
- BASE's 0x02F613B8(Kirby with the Hero copy, 0), run to its end (its two module calls stubbed): ints 0x9F (the level
  the spawner reads next) and 0xA0 (the marker) zeroed: the in-game bug;
- PATCHED: Kirby with marker 2 / 3 keeps every int and returns at once (callee-saved registers kept); Kirby with
  marker 0 / 1 (the Robin copy, Supamario), Robin, Hero and Sephiroth go on into the game's code and get the book as
  before.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kirby_robin_book_cave as C  # noqa: E402
import kirby_hero_copy_fix_test as T  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_LR, UC_PPC_REG_PC  # noqa: E402

FAIL = T.FAIL
check, r32, w32 = T.check, T.r32, T.w32
MEM = 0x7E000000
STUBBED = (0x02C762C8, 0x02C5C99C)      # VisibilityModule set (group, state), the +0x727C module's op


def fighter(mu, at, kind, marker, fill=0x55):
    """a fighter object F: WorkModule at +0x726C (kind at +0x18; its ints / flags through category 0), the two
    modules 0x02F613B8 calls at +0x72B0 / +0x727C"""
    f, wm, cats, cat0, ints, flags = at, at + 0x8000, at + 0x8100, at + 0x8200, at + 0x8400, at + 0x8800
    w32(mu, f + 0x726C, wm)
    w32(mu, f + 0x72B0, at + 0x9000)
    w32(mu, f + 0x727C, at + 0x9100)
    w32(mu, wm + 0x18, kind)
    w32(mu, wm + 8, cats)
    w32(mu, cats, cat0)
    w32(mu, cat0 + 0xC, ints)
    w32(mu, cat0 + 0x14, flags)
    w32(mu, flags + 0xC, 0xFFFFFFFF)
    for i in range(0x80, 0xB0):
        w32(mu, ints + 4 * i, fill + i)
    w32(mu, ints + 4 * (C.MARKER & 0xFFFF), marker)
    return f, ints


def ints_of(mu, ints):
    return {i: r32(mu, ints + 4 * i) for i in (0x90, 0x9F, 0xA0, 0xA1)}


def run_book(mu, f, book):
    seen = []

    def hook(uc, addr, _size, _ud):
        if addr in STUBBED:
            seen.append(addr)
            uc.reg_write(UC_PPC_REG_PC, uc.reg_read(UC_PPC_REG_LR))
        if addr == C.BACK:
            seen.append(addr)
    h = mu.hook_add(UC_HOOK_CODE, hook)
    _r, _f, bad = T.run(mu, C.HOOK, {UC_PPC_REG_3: f, UC_PPC_REG_4: book})
    mu.hook_del(h)
    return seen, bad


def main():
    patched, base = sys.argv[1:3]
    a, words = C.assemble()
    expect = {C.CAVE + 4 * i: w for i, w in enumerate(words)}
    expect[C.HOOK] = (18 << 26) | ((a.labels['book_stub'] - C.HOOK) & 0x03FFFFFC)
    b0, bd = T.text_words(base)
    p0, pd = T.text_words(patched)
    n = min(len(bd), len(pd))
    diff = {b0 + o for o in range(0, n, 4) if bd[o:o + 4] != pd[o:o + 4]}
    check('code: only the cave and the hook differ from the base', sorted(hex(x) for x in diff - set(expect)), [])
    check('the cave and the hook as built', {x: struct.unpack('>I', pd[x - p0:x - p0 + 4])[0] for x in expect}, expect)
    check('the base\'s hooked word is mflr r0 (no relocation: rpx_patch.py checked it)',
          struct.unpack('>I', bd[C.HOOK - b0:C.HOOK - b0 + 4])[0], C.HOOK_WORD)
    check('the cave below its limit, in the standard code region', C.CAVE + 4 * len(words) <= C.LIMIT < 0x04BB0000, True)
    bm = machine(base)
    pm = machine(patched)
    # the evidence: the spawner calls the book code before it reads the custom number
    w = r32(bm, C.SPAWNER_CALL)
    tgt = C.SPAWNER_CALL + (((w & 0x03FFFFFC) ^ 0x02000000) - 0x02000000)
    check('thunder spawner 0x02F645BC: bl 0x02F613B8 (r4 = r31 = 0 from 0x02F645B0)',
          (w & 0xFC000003, tgt, r32(bm, C.SPAWNER_CALL - 0xC)), (0x48000001, C.HOOK, 0x3BE00000))
    check('then 0x02F64650: the custom-number read (copy_custom_cave.py\'s b to its cave), after the call',
          (r32(bm, C.CUSTOM_READ) >> 26, C.SPAWNER_CALL < C.CUSTOM_READ), (18, True))
    check('0x02F613B8 stores its book into ints 0x9F / 0xA0 / 0xA1 (stw r29, 0x27C / 0x280 / 0x284(r10))',
          [r32(bm, x) for x in C.STORES], [0x93AA027C, 0x93AA0280, 0x93AA0284])
    bm.mem_map(MEM, 0x40000)
    pm.mem_map(MEM, 0x40000)
    # BASE: the bug
    f, ints = fighter(bm, MEM, 8, 2)
    seen, bad = run_book(bm, f, 0)
    got = ints_of(bm, ints)
    check('BASE, Kirby with the Hero copy: the book code zeroes 0x9F (the level) and 0xA0 (the marker)',
          (got[0x9F], got[0xA0], got[0xA1], got[0x90]), (0, 0, 0, 0))
    check('BASE: both module calls made', [x for x in seen if x != C.BACK], list(STUBBED))
    # PATCHED
    for marker, name in ((2, 'Hero'), (3, 'Sephiroth')):
        f, ints = fighter(pm, MEM, 8, marker)
        before = ints_of(pm, ints)
        flags = r32(pm, MEM + 0x8800 + 0xC)
        seen, bad = run_book(pm, f, 0)
        check('PATCHED, Kirby with the %s copy: no int touched, no module call, the flag kept' % name,
              (ints_of(pm, ints), seen, r32(pm, MEM + 0x8800 + 0xC)), (before, [], flags))
        check('PATCHED, %s copy: callee-saved registers kept' % name, bad, [])
    for kind, marker, name in ((8, 0, 'Kirby, the Robin copy'), (8, 1, 'Kirby, Supamario marker'),
                               (0x2C, 0, 'Robin'), (0x45, 2, 'Hero'), (0x42, 3, 'Sephiroth')):
        f, ints = fighter(pm, MEM, kind, marker)
        seen, bad = run_book(pm, f, 0)
        got = ints_of(pm, ints)
        check('PATCHED, %s: the game\'s code runs (0x02F613BC, both calls) and stores the book' % name,
              (seen, got[0x9F], got[0xA0], got[0xA1]), ([C.BACK] + list(STUBBED), 0, 0, 0))
        check('PATCHED, %s: callee-saved registers kept' % name, bad, [])
    # book -1 (put away) on the Hero copy: also nothing
    f, ints = fighter(pm, MEM, 8, 2)
    before = ints_of(pm, ints)
    seen, bad = run_book(pm, f, 0xFFFFFFFF)
    check('PATCHED, Hero copy, book -1: nothing either', (ints_of(pm, ints), seen), (before, []))
    print('%d failure(s)' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
