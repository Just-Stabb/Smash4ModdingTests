"""A small PowerPC (Espresso, 32-bit) register-use decoder and a forward liveness check, for the relocated patch
outputs (patchset.py): which registers an instruction reads / writes, and which registers are provably dead at an
address of the game's code (written before they are read on every path), so a far-jump veneer may use them.

Conservative by construction: an instruction it does not know reads every register; an indirect jump (bctr / a
computed branch) reads every register; a path that runs longer than the search limit counts as a read. Registers:
'r0'..'r31', 'ctr', 'lr'. Tested against capstone in tests/patchset_test.py.
"""

GPRS = ['r%d' % i for i in range(32)]
ALL = frozenset(GPRS + ['ctr', 'lr'])
# a call (bl / bla / bctrl): the callee reads the argument registers r3-r10 and the stack / TOC / small-data
# pointers, and leaves r0, r11, r12 and ctr undefined (volatile in the Wii U's EABI)
CALL_READS = frozenset(['r1', 'r2', 'r13'] + ['r%d' % i for i in range(3, 11)])
CALL_CLOBBERS = frozenset(['r0', 'r11', 'r12', 'ctr'])
# a return (blr): the caller still needs r1-r4 (the stack, toc, return values), r13-r31 (non-volatile) and lr
RET_READS = frozenset(['r1', 'r2', 'r3', 'r4', 'r13'] + ['r%d' % i for i in range(14, 32)] + ['lr'])
RET_DEAD = frozenset(['r0'] + ['r%d' % i for i in range(5, 13)] + ['ctr'])

UNKNOWN = ('unknown', ALL, frozenset())


def _r(n):
    return 'r%d' % n


def decode(w, addr=0):
    """(kind, reads, writes[, targets]) of the instruction word w at addr. kind: 'op' (falls through), 'b' (jump to
    targets), 'bc' (targets or fall through), 'call', 'ret', 'ret_cond', 'jump_ind' (bctr), 'unknown'."""
    op = w >> 26
    d, a, b = (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31
    ra0 = frozenset([_r(a)]) if a else frozenset()
    if w == 0x60000000:                                    # nop
        return ('op', frozenset(), frozenset())
    if op in (14, 15):                                     # addi / addis (rA = 0: the constant 0)
        return ('op', ra0, frozenset([_r(d)]))
    if op in (7, 8, 12, 13):                               # mulli, subfic, addic, addic.
        return ('op', frozenset([_r(a)]), frozenset([_r(d)]))
    if op in (10, 11):                                     # cmpli / cmpi
        return ('op', frozenset([_r(a)]), frozenset())
    if op in (24, 25, 26, 27, 28, 29):                     # ori oris xori xoris andi. andis.: rS -> rA
        return ('op', frozenset([_r(d)]), frozenset([_r(a)]))
    if op in (20, 21, 23):                                 # rlwimi (reads rA too), rlwinm, rlwnm (reads rB)
        rd = {_r(d)}
        if op == 20:
            rd.add(_r(a))
        if op == 23:
            rd.add(_r(b))
        return ('op', frozenset(rd), frozenset([_r(a)]))
    if op in (32, 34, 40, 42):                             # lwz lbz lhz lha
        return ('op', ra0, frozenset([_r(d)]))
    if op in (33, 35, 41, 43):                             # lwzu lbzu lhzu lhau
        return ('op', frozenset([_r(a)]), frozenset([_r(d), _r(a)]))
    if op == 46:                                           # lmw
        return ('op', ra0, frozenset(_r(i) for i in range(d, 32)))
    if op in (36, 38, 44):                                 # stw stb sth
        return ('op', frozenset([_r(d)]) | ra0, frozenset())
    if op in (37, 39, 45):                                 # stwu stbu sthu
        return ('op', frozenset([_r(d), _r(a)]), frozenset([_r(a)]))
    if op == 47:                                           # stmw
        return ('op', frozenset(_r(i) for i in range(d, 32)) | ra0, frozenset())
    if op in (48, 50, 52, 54, 56, 60):                     # lfs lfd stfs stfd psq_l psq_st (FPR data)
        return ('op', ra0, frozenset())
    if op in (49, 51, 53, 55, 57, 61):                     # the update forms
        return ('op', frozenset([_r(a)]), frozenset([_r(a)]))
    if op in (59, 63):                                     # floating point arithmetic: no GPR
        xo = (w >> 1) & 0x3FF
        if op == 63 and xo in (583, 711):                  # mffs / mtfsf
            return ('op', frozenset(), frozenset())
        return ('op', frozenset(), frozenset())
    if op == 4:                                            # paired singles; psq_lx / psq_stx (+ux) use rA, rB
        xo = (w >> 1) & 0x3F
        if xo in (6, 7):
            return ('op', ra0 | frozenset([_r(b)]), frozenset())
        if xo in (38, 39):
            return ('op', frozenset([_r(a), _r(b)]), frozenset([_r(a)]))
        return ('op', frozenset(), frozenset())
    if op == 18:                                           # b / ba / bl / bla
        off = w & 0x3FFFFFC
        if off & 0x2000000:
            off -= 0x4000000
        t = (off if w & 2 else addr + off) & 0xFFFFFFFF
        if w & 1:
            return ('call', CALL_READS, CALL_CLOBBERS | {'lr'}, (t,))
        return ('b', frozenset(), frozenset(), (t,))
    if op == 16:                                           # bc
        bo = d
        off = w & 0xFFFC
        if off & 0x8000:
            off -= 0x10000
        t = (off if w & 2 else addr + off) & 0xFFFFFFFF
        ctr = not bo & 4                                   # decrements and tests ctr
        rd = frozenset(['ctr']) if ctr else frozenset()
        wr = frozenset(['ctr']) if ctr else frozenset()
        if w & 1:
            return ('call', CALL_READS | rd, CALL_CLOBBERS | {'lr'}, (t,))
        if (bo & 0x14) == 0x14:                            # branch always
            return ('b', rd, wr, (t,))
        return ('bc', rd, wr, (t,))
    if op == 19:
        xo = (w >> 1) & 0x3FF
        bo = d
        if xo == 16:                                       # bclr
            if w & 1:
                return UNKNOWN
            always = (bo & 0x14) == 0x14
            ctr = not bo & 4
            return ('ret' if always else 'ret_cond', frozenset(['ctr']) if ctr else frozenset(), frozenset())
        if xo == 528:                                      # bcctr
            if w & 1:
                return ('call', CALL_READS | {'ctr'}, CALL_CLOBBERS | {'lr'}, ())
            return ('jump_ind', ALL, frozenset())
        if xo in (0, 33, 129, 193, 225, 257, 289, 417, 449, 150):   # mcrf, cr logic, isync
            return ('op', frozenset(), frozenset())
        return UNKNOWN
    if op == 31:
        xo = (w >> 1) & 0x3FF
        xo9 = (w >> 1) & 0x1FF
        if xo9 in (266, 10, 138, 40, 8, 136, 235, 75, 11, 491, 459):     # add addc adde subf subfc subfe mullw ..
            return ('op', frozenset([_r(a), _r(b)]), frozenset([_r(d)]))
        if xo9 in (104, 202, 200, 234, 232):                             # neg addze subfze addme subfme
            return ('op', frozenset([_r(a)]), frozenset([_r(d)]))
        if xo in (28, 444, 316, 124, 60, 412, 476, 284, 24, 536, 792):   # and or xor nor andc orc nand eqv slw srw sraw
            return ('op', frozenset([_r(d), _r(b)]), frozenset([_r(a)]))
        if xo in (824, 954, 922, 26):                                    # srawi extsb extsh cntlzw
            return ('op', frozenset([_r(d)]), frozenset([_r(a)]))
        if xo in (0, 32):                                                # cmp cmpl
            return ('op', frozenset([_r(a), _r(b)]), frozenset())
        if xo in (23, 87, 279, 343, 534, 790, 20):                       # lwzx lbzx lhzx lhax lwbrx lhbrx lwarx
            return ('op', ra0 | frozenset([_r(b)]), frozenset([_r(d)]))
        if xo in (55, 119, 311, 375):                                    # lwzux lbzux lhzux lhaux
            return ('op', frozenset([_r(a), _r(b)]), frozenset([_r(d), _r(a)]))
        if xo in (151, 215, 407, 662, 918, 150):                         # stwx stbx sthx stwbrx sthbrx stwcx.
            return ('op', frozenset([_r(d), _r(b)]) | ra0, frozenset())
        if xo in (183, 247, 439):                                        # stwux stbux sthux
            return ('op', frozenset([_r(d), _r(a), _r(b)]), frozenset([_r(a)]))
        if xo in (535, 599, 663, 727, 983):                              # lfsx lfdx stfsx stfdx stfiwx
            return ('op', ra0 | frozenset([_r(b)]), frozenset())
        if xo in (567, 631, 695, 759):                                   # the update forms
            return ('op', frozenset([_r(a), _r(b)]), frozenset([_r(a)]))
        if xo in (86, 54, 1014, 982, 278, 246, 470):                     # dcbf dcbst dcbz icbi dcbt dcbtst dcbi
            return ('op', ra0 | frozenset([_r(b)]), frozenset())
        if xo in (598, 854):                                             # sync eieio
            return ('op', frozenset(), frozenset())
        if xo == 19:                                                     # mfcr
            return ('op', frozenset(), frozenset([_r(d)]))
        if xo == 144:                                                    # mtcrf
            return ('op', frozenset([_r(d)]), frozenset())
        if xo in (339, 467, 371):                                        # mfspr mtspr mftb
            spr = ((w >> 16) & 31) | (((w >> 11) & 31) << 5)
            reg = {8: 'lr', 9: 'ctr'}.get(spr)
            if xo == 467:
                return ('op', frozenset([_r(d)]), frozenset([reg]) if reg else frozenset())
            return ('op', frozenset([reg]) if reg else frozenset(), frozenset([_r(d)]))
        return UNKNOWN
    return UNKNOWN


def dead_at(read, addr, candidates, limit=600, follow=None):
    """the registers of `candidates` that are dead at addr in the code read(a) -> word: on every path from addr, written
    before they are read. A path is followed through branches; it ends at a write, a call (for the volatile registers
    a call leaves undefined), or a return (for the volatile registers); anything else that can't be followed is a read.
    follow(target) -> True: a call to target is not an ABI call (a hook into patch code that replaced instructions
    in place): its body is followed, and its blr returns to the instruction after the call."""
    out = []
    for reg in candidates:
        if _dead(read, addr, reg, limit, follow):
            out.append(reg)
    return out


def _dead(read, start, reg, limit, follow):
    seen = set()
    todo = [(start, ())]
    steps = 0
    while todo:
        a, stack = todo.pop()
        if (a, stack) in seen:
            continue
        seen.add((a, stack))
        steps += 1
        if steps > limit:
            return False
        try:
            w = read(a)
        except Exception:
            return False
        ins = decode(w, a)
        kind, reads, writes = ins[0], ins[1], ins[2]
        if kind == 'call' and follow and ins[3] and follow(ins[3][0]):
            if len(stack) >= 4:
                return False
            todo.append((ins[3][0], stack + (a + 4,)))
            continue
        if reg in reads:
            return False
        if kind == 'call':
            if reg in writes:                  # clobbered by the call: dead from here
                continue
            todo.append((a + 4, stack))
            continue
        if reg in writes:
            continue
        if kind == 'op':
            todo.append((a + 4, stack))
        elif kind == 'b':
            todo.append((ins[3][0], stack))
        elif kind == 'bc':
            todo.append((ins[3][0], stack))
            todo.append((a + 4, stack))
        elif kind in ('ret', 'ret_cond'):
            if kind == 'ret_cond':
                todo.append((a + 4, stack))
            if stack:                          # the end of a followed hook: back after its call
                todo.append((stack[-1], stack[:-1]))
            elif reg in RET_READS or reg not in RET_DEAD:
                return False
        else:                                  # jump_ind / unknown
            return False
    return True
