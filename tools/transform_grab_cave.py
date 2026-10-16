#!/usr/bin/env python3
"""Transformation-final grab fix: prints rpx_patch.py args.

The fighter flags bit 0x08000000 forces "not catchable" (checked at 0x02E2528C and 0x02E28D50).
The transformation finals keep it set the whole time. These caves ignore the bit for fighter
kinds 0x3A-0x3D (koopag, warioman, littlemacg, lucariom) unless the current status kind is in
the special common range 0x139-0x151 (entry / rebirth / final / dead), so the transformation
itself stays ungrabbable.

Site 2 (status change) also requires flags +4 bit 0x20000, which only the post-respawn timer
(fighter update, [..+0xC]+0x160) sets; the transformations never run that timer, so for them
the cave jumps straight to 0x02E28D78 (catch = !(status data & 0x800)).
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
    # site 2 (status change): r30 = fighter, r8 = flags word, result in r6; r0 dead.
    # For the transformations outside the special statuses, skip both the 0x08000000 check and
    # the +4 bit 0x20000 check and go straight to catch = !(status data & 0x800).
    c2 = end
    A = lambda i: c2 + 4 * i
    s2 = [
        lwz(6, 4, 30), cmpwi(6, KIND_LO), None, cmpwi(6, KIND_HI), None,   # blt/bgt orig
        lwz(6, 0x7494, 30), lwz(6, 0x48, 6),
        cmpwi(6, ST_LO), None,               # blt open
        cmpwi(6, ST_HI), None,               # ble orig
        lwz(3, 0x74B8, 30), None,            # open: r3 = HitModule; b 0x02E28D78
        rlwinm(6, 8, 0, 4, 4), None,         # orig: original instruction; b 0x02E28D54
    ]
    opn, orig = A(11), A(13)
    s2[2] = bc(*BLT, A(2), orig)
    s2[4] = bc(*BGT, A(4), orig)
    s2[8] = bc(*BLT, A(8), opn)
    s2[10] = bc(*BLE, A(10), orig)
    s2[12] = b(A(12), 0x02E28D78)
    s2[14] = b(A(14), 0x02E28D54)
    p += [(A(i), w) for i, w in enumerate(s2)]
    p += [(0x02E28D50, b(0x02E28D50, c2))]
    assert A(15) <= 0x037EE740
    return p


if __name__ == '__main__':
    print(' '.join('0x%08X=0x%08X' % x for x in patches()))
