#!/usr/bin/env python3
"""Transformation-final grab fix: prints rpx_patch.py args.

The fighter flags bit 0x08000000 forces "not catchable" (checked at 0x02E2528C and 0x02E28D50).
The transformation finals keep it set the whole time. These caves ignore the bit for fighter
kinds 0x3A-0x3D (koopag, warioman, littlemacg, lucariom) unless the current status kind is in
the special common range 0x139-0x151 (entry / rebirth / final / dead), so the transformation
itself stays ungrabbable.
"""
CAVE = 0x037EE600
KIND_LO, KIND_HI = 0x3A, 0x3D
ST_LO, ST_HI = 0x139, 0x151


def rlwinm(ra, rs, sh, mb, me, rc=0):
    return (21 << 26) | (rs << 21) | (ra << 16) | (sh << 11) | (mb << 6) | (me << 1) | rc
def lwz(rt, d, ra):
    return (32 << 26) | (rt << 21) | (ra << 16) | (d & 0xFFFF)
def cmpwi(ra, imm):
    return (11 << 26) | (ra << 16) | (imm & 0xFFFF)
def li(rt, imm):
    return (14 << 26) | (rt << 21) | (imm & 0xFFFF)
def lis(rt, imm):
    return (15 << 26) | (rt << 21) | (imm & 0xFFFF)
def b(src, dst):
    return (18 << 26) | ((dst - src) & 0x3FFFFFC)
def bc(bo, bi, src, dst):
    return (16 << 26) | (bo << 21) | (bi << 16) | ((dst - src) & 0xFFFC)
BEQ, BNE, BLT, BGT, BLE = (12, 2), (4, 2), (12, 0), (12, 1), (4, 1)


def stub(start, flag_reg, src_reg, fighter, scratch, ret):
    """flag_reg = src_reg & 0x08000000, cleared for transformations outside the special statuses.
    scratch must be dead at ret and must not be r0 if it's used as a base."""
    lbl = {}
    def prog():
        return [
            ('w', rlwinm(flag_reg, src_reg, 0, 4, 4, 1)),
            ('bc', BEQ, 'done'),
            ('w', lwz(scratch, 4, fighter)),             # fighter kind
            ('w', cmpwi(scratch, KIND_LO)), ('bc', BLT, 'done'),
            ('w', cmpwi(scratch, KIND_HI)), ('bc', BGT, 'done'),
            ('w', lwz(scratch, 0x7494, fighter)),        # StatusModule
            ('w', lwz(scratch, 0x48, scratch)),          # status kind
            ('w', cmpwi(scratch, ST_LO)), ('bc', BLT, 'clear'),
            ('w', cmpwi(scratch, ST_HI)), ('bc', BLE, 'done'),
            ('lbl', 'clear'), ('w', li(flag_reg, 0)),
            ('lbl', 'done'), ('b', ret),
        ]
    a = start
    for it in prog():
        if it[0] == 'lbl':
            lbl[it[1]] = a
        else:
            a += 4
    out, a = [], start
    for it in prog():
        if it[0] == 'lbl':
            continue
        if it[0] == 'w':
            w = it[1]
        elif it[0] == 'bc':
            w = bc(it[1][0], it[1][1], a, lbl[it[2]])
        else:
            w = b(a, it[1])
        out.append((a, w)); a += 4
    return out, a


def patches():
    p = []
    # site 1: fighter update, r31 = fighter, r0 = flags word, r5 dead (next: addic r5,r0,-1)
    s1, end = stub(CAVE, 0, 0, 31, 5, 0x02E25290)
    p += s1 + [(0x02E2528C, b(0x02E2528C, CAVE))]
    # site 2: r30 = fighter, r8 = flags word, result in r6; r0 dead (next: addic r0,r6,-1)
    # r0 can't be a base register, so use r6 as scratch and restore the bit when keeping it.
    c2 = end
    lbl_keep = None
    s2 = [
        rlwinm(6, 8, 0, 4, 4, 1),
        None,                                # beq done
        lwz(6, 4, 30), cmpwi(6, KIND_LO), None, cmpwi(6, KIND_HI), None,   # blt/bgt keep
        lwz(6, 0x7494, 30), lwz(6, 0x48, 6),
        cmpwi(6, ST_LO), None,               # blt clear
        cmpwi(6, ST_HI), None,               # ble keep
        li(6, 0), None,                      # clear: li r6,0; b done
        lis(6, 0x0800),                      # keep: r6 = 0x08000000
        None,                                # done: b 0x02E28D54
    ]
    A = lambda i: c2 + 4 * i
    keep, clear, done = A(15), A(13), A(16)
    s2[1] = bc(*BEQ, A(1), done)
    s2[4] = bc(*BLT, A(4), keep)
    s2[6] = bc(*BGT, A(6), keep)
    s2[10] = bc(*BLT, A(10), clear)
    s2[12] = bc(*BLE, A(12), keep)
    s2[14] = b(A(14), done)
    s2[16] = b(A(16), 0x02E28D54)
    p += [(A(i), w) for i, w in enumerate(s2)]
    p += [(0x02E28D50, b(0x02E28D50, c2))]
    assert A(17) <= 0x037EE740
    return p


if __name__ == '__main__':
    print(' '.join('0x%08X=0x%08X' % x for x in patches()))
