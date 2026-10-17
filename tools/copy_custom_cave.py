#!/usr/bin/env python3
"""Kirby copy abilities use the swallowed fighter's custom neutral special: prints rpx_patch.py args.

  python3 tools/rpx_patch.py cross_f.rpx out.rpx ... $(python3 tools/copy_custom_cave.py)

The fighter special-param loader (0x02F1BF88, WorkModule) copies each special's param block
for the fighter's custom slot (N: [params[kind]+0xFC] + custom(0x10000048) * count*4 -> WM+0xD30).
For Kirby with a copy it then calls 0x02F1B8B0, which overwrites WM+0xD30 with the copied
fighter's neutral-B block, always the DEFAULT variant: [params[copy]+0xFC], size = byte table
0x02EA9104(copy) (96 for Bowser = 24 values). The variants follow each other with that stride.

CAVE_A (swallow, 0x02796900, just before copy_grant 0x02EFCD8C): reads the victim's custom N
slot (0x10000048; for a swallowed Kirby its copy slot 0x100000A5) and stores it in Kirby's int
0x100000A5 (outside the 0x83-0xA0 range copy_grant clears; unused by Kirby's MSC).
CAVE_B (copy loader, 0x02F1B910-0x02F1B928): source += Kirby's 0x100000A5 * size (0-3).
Kirby's MSC also reads 0x100000A5 to pick the copied move's weapon motion (hitbox variant).
"""
CAVE_A = 0x037EE680
SLOT = 0x100000A5
HOOK_A, RET_A = 0x02796900, 0x02796904
HOOK_B, RET_B = 0x02F1B910, 0x02F1B92C
SIZE_FN = 0x02EA9104
WM_GET, WM_SET = 0x84, 0x8C
LIMIT = 0x037EE73C  # last word of the Havok cave takes moved relocations (starcopy_cave.py)


def D(op, rd, ra, imm): return (op << 26) | (rd << 21) | (ra << 16) | (imm & 0xFFFF)
def lwz(rd, d, ra): return D(32, rd, ra, d)
def stw(rs, d, ra): return D(36, rs, ra, d)
def addi(rd, ra, imm): return D(14, rd, ra, imm)
def lis(rd, imm): return D(15, rd, 0, imm)
def li(rd, imm): return D(14, rd, 0, imm)
def cmpwi(ra, imm): return D(11, 0, ra, imm)
def cmplwi(ra, imm): return D(10, 0, ra, imm)
def X(rs, ra, rb, xo, rc=0): return (31 << 26) | (rs << 21) | (ra << 16) | (rb << 11) | (xo << 1) | rc
def mr(ra, rs): return X(rs, ra, rs, 444)
def add(rd, ra, rb): return X(rd, ra, rb, 266)
def mullw(rd, ra, rb): return X(rd, ra, rb, 235)
def slwi(ra, rs, n): return (21 << 26) | (rs << 21) | (ra << 16) | (n << 11) | (0 << 6) | ((31 - n) << 1)
MTCTR0 = 0x7C0903A6
BCTRL = 0x4E800421
def b(src, dst): return (18 << 26) | ((dst - src) & 0x3FFFFFC)
def bl(src, dst): return b(src, dst) | 1
def bc(bo, bi, src, dst): return (16 << 26) | (bo << 21) | (bi << 16) | ((dst - src) & 0xFFFC)
BGE, BNE, BLE = (4, 0), (4, 2), (4, 1)


def assemble(start, prog):
    lbl, a = {}, start
    for it in prog:
        if isinstance(it, str):
            lbl[it] = a
        else:
            a += 4
    out, a = [], start
    for it in prog:
        if isinstance(it, str):
            continue
        if isinstance(it, tuple):
            kind = it[0]
            if kind == 'bc':
                w = bc(it[1][0], it[1][1], a, lbl[it[2]])
            elif kind == 'b':
                w = b(a, it[1])
            elif kind == 'bl':
                w = bl(a, it[1])
        else:
            w = it
        out.append((a, w))
        a += 4
    return out, a


def patches():
    # r24 = victim's module accessor, r26 = copy kind, r31 = Kirby's accessor, r28 = 1.
    cave_a, end = assemble(CAVE_A, [
        cmplwi(26, 0x3A), ('bc', BGE, 'done'),        # no copy (-1) / not a fighter kind
        lwz(3, 0x28, 24),                             # victim WorkModule
        lwz(12, 0, 3),
        lwz(0, 0x18, 3),                              # victim kind
        cmpwi(0, 8),
        lis(4, 0x1000), addi(4, 4, 0x48),             # custom N slot
        ('bc', BNE, 'get'),
        addi(4, 4, SLOT - 0x10000048),                # swallowed Kirby: its copy's slot
        'get',
        lwz(0, WM_GET, 12), MTCTR0, BCTRL,
        mr(5, 3),
        lwz(3, 0x28, 31),                             # Kirby WorkModule
        lwz(12, 0, 3),
        lwz(0, WM_SET, 12), MTCTR0,
        mr(4, 5), lis(5, 0x1000), addi(5, 5, SLOT & 0xFFFF),
        BCTRL,
        'done',
        mr(7, 28),                                    # replaced instruction
        ('b', RET_A),
    ])
    # r29 = Kirby WorkModule, r30 = copy kind, r31 = param manager; r3/r4 set for SIZE_FN.
    cave_b, end2 = assemble(end, [
        ('bl', SIZE_FN),
        stw(3, 8, 1),                                 # size (8(r1) is free in this frame)
        lwz(12, 0, 29), lwz(0, WM_GET, 12), MTCTR0,
        lis(4, 0x1000), addi(4, 4, SLOT & 0xFFFF),
        mr(3, 29), BCTRL,                             # r3 = custom slot
        cmplwi(3, 3), ('bc', BLE, 'ok'), li(3, 0),
        'ok',
        lwz(5, 8, 1),
        mullw(6, 3, 5),
        slwi(0, 30, 2), add(12, 31, 0), lwz(12, 0x111C, 12),
        lwz(4, 0xFC, 12), add(4, 4, 6),
        addi(3, 29, 0xD30),
        ('b', RET_B),                                 # bl memcpy there (r3 dst, r4 src, r5 size)
    ])
    assert end2 <= LIMIT, hex(end2)
    p = cave_a + cave_b
    p.append((HOOK_A, b(HOOK_A, CAVE_A)))
    p.append((HOOK_B, b(HOOK_B, end)))
    return p


if __name__ == '__main__':
    print(' '.join('0x%08X=0x%08X' % x for x in patches()))
