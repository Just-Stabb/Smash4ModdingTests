#!/usr/bin/env python3
"""Kirby copy abilities use the swallowed fighter's custom neutral special: prints rpx_patch.py args.

  python3 tools/rpx_patch.py cross_f.rpx out.rpx ... $(python3 tools/copy_custom_cave.py)

The fighter special-param loader (0x02F1BF88, WorkModule) copies each special's param block
for the fighter's custom slot (N: [params[kind]+0xFC] + custom(0x10000048) * count*4 -> WM+0xD30).
For Kirby with a copy it then calls 0x02F1B8B0, which overwrites WM+0xD30 with the copied
fighter's neutral-B block, always the DEFAULT variant: [params[copy]+0xFC], size = byte table
0x02EA9104(copy) (96 for Bowser = 24 values). The variants follow each other with that stride.

CAVE_A (swallow, hook 0x02796900, before copy_grant's arguments are set): reads the victim's custom N
slot (0x10000048; for a swallowed Kirby its copy slot) and stores it in Kirby's int 0x1000009F,
then the swallow code calls copy_grant (0x02EFCD8C). copy_grant clears ints 0x83-0xA0 (count 0x1E at 0x02EFCE14)
and writes the copied costume to 0xA5 (the first version used 0xA5 and got the costume); the
count becomes 0x1C, so 0x9F/0xA0 survive (unused by Kirby's MSC and the star copy cave).
Writing the slot after copy_grant returned was too late: the params were already loaded.
CAVE_B (copy loader, 0x02F1B910-0x02F1B928): source += Kirby's 0x1000009F * size (0-3).
CAVE_C (article generation, hook 0x02F062C0 `lwz r0, 0x120(r9)`): a fighter's generated
weapon gets its custom number (init struct +0x5C, the weapon's 0x10000005: its param block via
the weapon's getter, e.g. Bowser breath 0x031ABB8C, and its motion = ACMD variant) from the
owner's int 0x10000048 ([int array]+0x120). For Kirby (kind 8) with a copy (int 0xA4 < 0x3A)
it uses 0x1000009F instead. Found with a Cemu breakpoint on the breath getter: LR 0x02BCC414
(0x02BCC3BC, r5 = custom) <- 0x02B61A94 (custom = (s8)[init+0x5C]) <- 0x02C073DC <- 0x02F062D8.
That hook is in Bowser's breath spawner (0x02F0601C), not a shared one: every weapon kind has its own
spawner (its article record {kind, max count, spawner}: reference/FighterArticles.xml CountAddr - 4 /
+ 4; Kirby's copies use the copied fighter's records and spawners), and 36 of the 329 read the owner's
0x10000048 there themselves (lwz rX, 0x120(owner's int array) into the init block's +0x5C), so
on Kirby they read his own Inhale custom and Kirby's copy fired his slot's variant instead of the
swallowed fighter's. SPAWNERS covers all 32 of those reads in the spawners Kirby's copy tables use
(0x10135000-0x10136D20; Kirby's own star missile left out): each gets a cave doing what CAVE_C does.
Per site (checked with a path-following liveness pass over each spawner, kept in the table): the
owner register (the int array's [[[OWNER+0x726C]+8]+0]+0xC chain, and r4 at entry on every path), a
volatile scratch register dead on every path from the hook to the weapon create call, and cr0 dead
there too. Diddy Kong's gun / peanut / explosion spawners pass 0 (as for Diddy himself): his
variants come from the neutral-B params, already the copy's (CAVE_B).
Caves: hooks below 0x02B00000 (out of a branch's reach of the grown code) after CAVE_C in the Havok
cave (0x037EE400-0x037EE4F0, free in the standard build; the debug-only stage_select_debug_cave.py uses
the same words and can't be combined with this), the rest in the grown code space at 0x04B9E000
(trail_table_cave.py's limit lowered to it).
"""
CAVE_A = 0x037EE680
SLOT = 0x1000009F
HOOK_A, RET_A = 0x02796900, 0x02796904
COPY_GRANT = 0x02EFCD8C
CLEAR_COUNT = 0x02EFCE14  # li r11, 0x1E -> 0x1C
HOOK_B, RET_B = 0x02F1B910, 0x02F1B92C
SIZE_FN = 0x02EA9104
WM_GET, WM_SET = 0x84, 0x8C
LIMIT = 0x037EE73C
CAVE_C = 0x037EE400  # free (zero) part of the Havok cave
HOOK_C, RET_C = 0x02F062C0, 0x02F062C4  # last word of the Havok cave takes moved relocations (starcopy_cave.py)
# spawners reading the owner's custom slot: (hook: lwz DST, 0x120(INTS); DST, INTS = owner's int array,
# OWNER = owner object, SCRATCH = a volatile register dead from the hook to the create call, weapon kind,
# fighter/weapon)
SPAWNERS = [
    (0x02F062C0, 0, 9, 26, 12, 0x05F, 'koopa/breath'),     # CAVE_C
    (0x027B1F94, 8, 5, 29, 12, 0x0BE, 'mariod/drcapsule'),
    (0x0279B2FC, 10, 11, 29, 12, 0x134, 'koopajr/cannonball'),
    (0x027AA040, 10, 10, 28, 12, 0x16E, 'lucas/pkfreeze'),
    (0x027B3F00, 11, 10, 29, 12, 0x166, 'mewtwo/shadowball'),
    (0x027BF508, 0, 8, 31, 9, 0x15E, 'pitb/bowarrow'),
    (0x02F7609C, 10, 6, 29, 12, 0x046, 'samus/cshot'),
    (0x02F19054, 0, 8, 26, 11, 0x064, 'luigi/fireball'),
    (0x02F4783C, 11, 10, 31, 12, 0x051, 'peach/kinopio'),
    (0x02F540D8, 0, 8, 31, 9, 0x04F, 'pit/bowarrow'),
    (0x02F122A0, 0, 7, 30, 12, 0x053, 'lucario/auraball'),
    (0x02F1ADC8, 11, 9, 29, 12, 0x000, 'mario/fireball'),
    (0x02F09CC8, 0, 7, 31, 11, 0x007, 'link/bow'),
    (0x02F09E08, 10, 9, 30, 12, 0x008, 'link/bowarrow'),
    (0x02F4B530, 8, 8, 28, 12, 0x014, 'pikachu/dengekidama'),
    (0x02F3B0F0, 10, 10, 28, 12, 0x055, 'ness/pkflash'),
    (0x02F77B2C, 0, 6, 27, 12, 0x041, 'sheik/needle'),
    (0x02EE64BC, 12, 6, 30, 11, 0x0E5, 'gamewatch/food'),
    (0x02EE1634, 8, 5, 27, 12, 0x01F, 'falco/blaster_bullet'),
    (0x02F816B8, 0, 12, 28, 11, 0x037, 'szerosuit/paralyzer_bullet'),
    (0x02F50134, 6, 8, 28, 12, 0x03C, 'pikmin/pikmin'),
    (0x02F50140, 0, 8, 28, 12, 0x03C, 'pikmin/pikmin'),
    (0x02ECA9F0, 11, 8, 27, 12, 0x028, 'dedede/starmissile'),
    (0x02ECAC30, 11, 8, 27, 12, 0x028, 'dedede/starmissile'),
    (0x02F6887C, 0, 5, 29, 12, 0x0C7, 'robot/beam'),
    (0x02F843F4, 0, 7, 31, 11, 0x0CF, 'toonlink/bow'),
    (0x02F84534, 10, 9, 30, 12, 0x0D0, 'toonlink/bowarrow'),
    (0x02F0F678, 27, 7, 29, 11, 0x0DD, 'lizardon/breath'),
    (0x02F8D1B4, 0, 11, 27, 12, 0x074, 'wiifit/sunbullet'),
    (0x02F64650, 12, 9, 27, 11, 0x0B6, 'reflet/thunder'),
    (0x02EDF080, 11, 12, 28, 10, 0x10B, 'duckhunt/can'),
    (0x02EF1340, 0, 8, 30, 12, 0x0F9, 'gekkouga/shuriken'),
    (0x02EFC864, 0, 9, 29, 12, 0x013, 'kirby/rosettaticomissile'),   # Kirby's own article: his Rosalina copy's
]
GROWN = 0x04B9E000             # grown code space (trail_table_cave.py's LIMIT)
GROWN_LIMIT = 0x04BA0000       # kind_expand.py from here
NEAR = 0x02B00000              # hooks below this use the Havok cave
SPAWN_LIMIT = 0x037EE5A0       # copy_held_cave.py from here


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
    # r24 = victim's module accessor, r26 = copy kind, r31 = Kirby's accessor (all callee-saved).
    # r24 = victim's module accessor, r26 = copy kind, r31 = Kirby's accessor, r28 = 1.
    cave_a, end = assemble(CAVE_A, [
        cmplwi(26, 0x3A), ('bc', BGE, 'grant'),       # no copy (-1) / not a fighter kind
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
        'grant',
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
    p.append((CLEAR_COUNT, li(11, 0x1C)))
    # each spawner: INTS = owner's int array, OWNER = owner (its WorkModule at +0x726C; OWNER is NOT
    # the fighter base, so [OWNER+4] isn't the kind: v4 checked that and never fired). WM+0x18 =
    # fighter kind. DST is loaded last, so INTS may be DST (Pikachu, Ness, Lucas); SCRATCH is never r0
    # (as a base register r0 reads as 0).
    at = {True: CAVE_C, False: GROWN}
    for hook, dst, ints, owner, scr, _kind, _name in SPAWNERS:
        assert scr not in (0, ints, owner)
        near = hook < NEAR
        cave, end3 = assemble(at[near], [
            lwz(scr, 0x726C, owner), lwz(scr, 0x18, scr), cmpwi(scr, 8), ('bc', BNE, 'own'),
            lwz(scr, 0x290, ints), cmplwi(scr, 0x3A), ('bc', BGE, 'own'),
            lwz(dst, (SLOT & 0xFFFF) * 4, ints),      # Kirby with a copy: the copied custom slot
            ('b', hook + 4),
            'own',
            lwz(dst, 0x120, ints),                    # replaced: the owner's 0x10000048
            ('b', hook + 4),
        ])
        assert abs(at[near] - hook) < 0x1FFFFF0, (hex(hook), hex(at[near]))
        p += cave
        p.append((hook, b(hook, at[near])))
        at[near] = end3
    assert at[False] <= GROWN_LIMIT, hex(at[False])
    at = at[True]
    assert at <= SPAWN_LIMIT, hex(at)
    p.append((HOOK_B, b(HOOK_B, end)))
    return p


if __name__ == '__main__':
    print(' '.join('0x%08X=0x%08X' % x for x in patches()))
