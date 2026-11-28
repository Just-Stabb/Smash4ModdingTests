"""Random select: the character select's random-fighter pool moved to a bigger set, and the per-clone choices.

The game's pool (traced from the game's code; docs/README "Random select"):
- one 96-bit set (12 bytes) at +0x98 of the random-pool object (the stage pools follow at +0xA4, +0xB4, +0xC4,
  +0xD4, 128 bits each); the object comes from 0x0300174C(0x104D162C);
- refill 0x02FFB610 (from the object's set-up 0x02FFBB0C and from the count): positions 0-0x50 of the character
  database (`li r23, 0x51`), bit i = position i = character id i, set when the entry is available, not masked
  out and not a Mii; then random's own id cleared; built in a 12-byte stack local and copied to +0x98;
- count 0x02FFC4A8 (from 0x03017BCC / 0x03017E20): bits 0-0x50 counted, under 8 -> refill;
- remove 0x02FFC5BC (from 0x03017CFC): clears bit id for ids < 0x51;
- getter 0x02FFC5B4 (+0x98), called only by the pick;
- pick 0x028E21B4 (from 0x0290A454 / 0x0290A824 / 0x0290C5F0): the set copied into a 12-byte stack local, its
  bits 0-0x50 counted; for a player (r3 != -1) a second copy without the ids the other 7 players have, used when
  7 or more remain; then a random number % count (the clock-seeded xorshift at 0x105759D0) and the n-th set bit
  0-0x50 returned as the character id (a byte); none: 0x030A0F1C's 4 (Mario);
- the available-fighters helper 0x0301CAE8 (also called from 0x0290D960 / 0x029E6CE0) sets a bit per database entry
  in a 12-byte stack local: with more than 96 entries it writes past it (ids 128 and up reach the saved registers).

The patch (all accesses but the getter replaced; the getter's +0x98 stays a mirror of ids 0-95):
- the pool: 7 words (ids 0-223) per pool object in the tool's code space (4 objects at most; an object not seen yet
  starts from its +0x98 words); refill, count, remove and pick replaced by functions that use it, the scan over
  positions 0 .. max(0x51, 59 + new ids) - 1, every bit ANDed with the allow mask ("random": false clones out);
- 0x0301CAE8 and the stages' 0x0301CCB4 (16-byte local) count at most 96 / 128 entries;
- stage pools (refills 0x02FFB76C, 0x02FFB8CC): each stored word ANDed with the stage allow mask (stage clones with
  "random": false out). Their 0x63-id bound holds every stage clone (at most 41, ids 0x38-0x60).
"""
from . import _paths  # noqa: F401
from ppcasm import Asm, ha  # noqa: E402

REFILL = 0x02FFB610
COUNT_AT, COUNT_BACK = 0x02FFC4BC, 0x02FFC4F0
REMOVE = 0x02FFC5BC
PICK = 0x028E21B4
AVAIL_COUNT = 0x0301CB40        # or. r27, r3, r3 (the database's entry count)
STAGE_AVAIL_COUNT = 0x0301CD0C  # or. r27, r3, r3
STAGE_STORE_AB = 0x02FFB814     # stwx r12, r31, r10
STAGE_STORE_CD = 0x02FFB964     # stwx r12, r31, r25
WORDS, SLOTS = 7, 4
BITS = 32 * WORDS
FIRST_ID, OLD = 59, 0x51
ORIGINALS = {REFILL: 'stwu r1, -0x38(r1)', COUNT_AT: 'li r11, 0x51', REMOVE: 'cmpwi r4, 0xff',
             PICK: 'stwu r1, -0x38(r1)', PICK + 4: 'stmw r26, 0x20(r1)', PICK + 8: 'mflr r0',
             PICK + 12: 'mr r30, r3', AVAIL_COUNT: 'or. r27, r3, r3', STAGE_AVAIL_COUNT: 'or. r27, r3, r3',
             STAGE_STORE_AB: 'stwx r12, r31, r10', STAGE_STORE_CD: 'stwx r12, r31, r25'}
DB, MASKS = 0x102F7188, 0x1034069C       # [the character database], [the masks object]
F_ENTRY, F_AVAIL, F_MASK, F_MII, F_RANDOM_ID = 0x0309FB24, 0x0301BA44, 0x0293C40C, 0x030A04C0, 0x030A0EFC
F_INIT_GUARD, F_POOLOBJ, F_PLAYERS_A, F_PLAYERS_B, F_NONE = 0x020013BC, 0x0300174C, 0x0300266C, 0x02868080, 0x030A0F1C
RNG = 0x105759C0


def slo(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def one(addr, text):
    a = Asm(addr)
    a.asm(text)
    return a.words()[0]


def scan_count(n_ids):
    return min(BITS, max(OLD, FIRST_ID + n_ids))


def mask_words(items, key, nwords):
    words = [0xFFFFFFFF] * nwords
    for f in items:
        i = f[key]
        if i < 32 * nwords and f.get('random', True) is False:
            words[i // 32] &= ~(1 << (i % 32)) & 0xFFFFFFFF
    return words


def far(fn):
    return '\nlis r12, 0x%X\naddi r12, r12, %d\nmtctr r12\nbctrl\n' % (ha(fn), slo(fn))


def lookup(obj, tab, tag):
    """r12 = the 7-word set of pool object `obj` (a register); clobbers r9-r11, cr0"""
    s = dict(o=obj, h=ha(tab), l=slo(tab), t=tag, n=SLOTS)
    return '''
        lis r10, 0x%(h)X
        addi r10, r10, %(l)d
        li r9, 0
%(t)s_a: lwz r11, 0(r10)
        cmplw r11, %(o)s
        beq %(t)s_f
        addi r10, r10, 32
        addi r9, r9, 1
        cmplwi r9, %(n)d
        blt %(t)s_a
        lis r10, 0x%(h)X
        addi r10, r10, %(l)d
        li r9, 0
%(t)s_b: lwz r11, 0(r10)
        cmpwi r11, 0
        beq %(t)s_c
        addi r10, r10, 32
        addi r9, r9, 1
        cmplwi r9, %(n)d
        blt %(t)s_b
        lis r10, 0x%(h)X
        addi r10, r10, %(l)d
%(t)s_c: stw %(o)s, 0(r10)
        lwz r11, 0x98(%(o)s)
        stw r11, 4(r10)
        lwz r11, 0x9C(%(o)s)
        stw r11, 8(r10)
        lwz r11, 0xA0(%(o)s)
        stw r11, 12(r10)
        li r11, 0
        stw r11, 16(r10)
        stw r11, 20(r10)
        stw r11, 24(r10)
        stw r11, 28(r10)
%(t)s_f: addi r12, r10, 4
''' % s


def count_bits(src, n, out, tag):
    """out = set bits 0..n-1 of the set at register src; clobbers r9-r11, cr0"""
    return '''
        li %(o)s, 0
        li r9, 0
%(t)s: srwi r10, r9, 5
        slwi r10, r10, 2
        lwzx r11, %(s)s, r10
        srw r11, r11, r9
        andi. r11, r11, 1
        add %(o)s, %(o)s, r11
        addi r9, r9, 1
        cmplwi r9, %(n)d
        blt %(t)s
''' % dict(s=src, n=n, o=out, t=tag)


def copy_words(src, dst, tag):
    return '\n' + '\n'.join('        lwz r11, %d(%s)\n        stw r11, %d(%s)' % (4 * i, src, 4 * i, dst)
                              for i in range(WORDS)) + '\n'


def source(n_fighters, at):
    n = scan_count(n_fighters)
    tab, fmask, smask = at['tab'], at['fmask'], at['smask']
    s = dict(n=n, fh=ha(fmask), fl=slo(fmask), sh=ha(smask), sl=slo(smask))
    return ('''
refill:                                 # r3 = the pool object
        stwu r1, -0x40(r1)
        stmw r23, 0x1C(r1)
        mflr r0
        stw r0, 0x44(r1)
        mr r27, r3
        lis r30, 0x%(dbh)X
        lwz r30, %(dbl)d(r30)
        lis r31, 0x%(mh)X
        lwz r31, %(ml)d(r31)
''' % dict(s, dbh=ha(DB), dbl=slo(DB), mh=ha(MASKS), ml=slo(MASKS)) + lookup('r27', tab, 'rf') + '''
        mr r29, r12
        li r11, 0
''' + '\n'.join('        stw r11, %d(r29)' % (4 * i) for i in range(WORDS)) + '''
        li r25, 0
        li r23, %(n)d
        li r24, 1
rf_loop:
        li r5, 1
        mr r4, r25
        mr r3, r30
''' % s + far(F_ENTRY) + '''
        mr r26, r3
        cmpwi r26, 0xFF
        beq rf_next
        li r4, 4
        mr r3, r26
''' + far(F_AVAIL) + '''
        mr r28, r3
        clrlwi r4, r25, 24
        mr r3, r31
''' + far(F_MASK) + '''
        and r28, r28, r3
        mr r3, r30
        mr r4, r26
''' + far(F_MII) + '''
        xori r11, r3, 1
        clrlwi r12, r11, 24
        and r28, r28, r12
        cmpwi r28, 0
        beq rf_next
        srwi r10, r25, 5
        slwi r10, r10, 2
        clrlwi r9, r25, 27
        lis r11, 0x%(fh)X
        addi r11, r11, %(fl)d
        lwzx r11, r11, r10
        srw r11, r11, r9
        andi. r11, r11, 1
        beq rf_next
        lwzx r12, r29, r10
        slw r11, r24, r9
        or r12, r12, r11
        stwx r12, r29, r10
rf_next:
        addi r23, r23, -1
        addi r25, r25, 1
        cmpwi r23, 0
        bne rf_loop
        mr r3, r30
''' % s + far(F_RANDOM_ID) + '''
        cmplwi r3, %(n)d
        bge rf_mirror
        srwi r10, r3, 5
        slwi r10, r10, 2
        clrlwi r9, r3, 27
        slw r11, r24, r9
        lwzx r12, r29, r10
        andc r12, r12, r11
        stwx r12, r29, r10
rf_mirror:
        lwz r11, 0(r29)
        stw r11, 0x98(r27)
        lwz r11, 4(r29)
        stw r11, 0x9C(r27)
        lwz r11, 8(r29)
        stw r11, 0xA0(r27)
        lmw r23, 0x1C(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

count:                                  # in 0x02FFC4A8, r31 = the object; -> r9 = bits left
''' % s + lookup('r31', tab, 'ct') + count_bits('r12', n, 'r0', 'ct_l') + '''
        mr r9, r0
        b 0x%(back)X

remove:                                 # r3 = the object, r4 = the id (leaf)
        cmpwi r4, 0xFF
        beq rm_out
        cmplwi r4, %(n)d
        bge rm_out
''' % dict(s, back=COUNT_BACK) + lookup('r3', tab, 'rm') + '''
        srwi r10, r4, 5
        slwi r10, r10, 2
        clrlwi r9, r4, 27
        li r11, 1
        slw r11, r11, r9
        lwzx r9, r12, r10
        andc r9, r9, r11
        stwx r9, r12, r10
        cmplwi r10, 8
        bgt rm_out
        addi r10, r10, 0x98
        lwzx r9, r3, r10
        andc r9, r9, r11
        stwx r9, r3, r10
rm_out: blr

pick:                                   # r3 = the player (-1: none) -> r3 = a character id
        stwu r1, -0x70(r1)
        stmw r25, 0x4C(r1)
        mflr r0
        stw r0, 0x74(r1)
        mr r30, r3
        lis r28, 0x%(gh)X
        lwzu r12, %(gl)d(r28)
        cmpwi r12, 0
        lis r29, 0x1034
        bne pk_init1
        li r12, 1
        addi r3, r29, -0x4F2C
        stw r12, 0(r28)
''' % dict(s, gh=ha(0x10492894), gl=slo(0x10492894)) + far(F_INIT_GUARD) + '''
pk_init1:
        lis r26, 0x104D
        addi r3, r26, 0x162C
''' + far(F_POOLOBJ) + lookup('r3', tab, 'pk') + '''
        addi r31, r1, 8
''' + copy_words('r12', 'r31', 'pk_c') + count_bits('r31', n, 'r27', 'pk_n') + '''
        cmpwi r30, -1
        beq pk_pick
        lwz r12, 0(r28)
        cmpwi r12, 0
        bne pk_init2
        li r12, 1
        addi r3, r29, -0x4F2C
        stw r12, 0(r28)
''' + far(F_INIT_GUARD) + '''
pk_init2:
        addi r3, r26, 0x162C
''' + far(F_PLAYERS_A) + far(F_PLAYERS_B) + '''
        mr r25, r3
        addi r12, r1, 0x24
''' + copy_words('r31', 'r12', 'pk_b') + '''
        li r5, 0
pk_pl:  cmplw r5, r30
        beq pk_pln
        slwi r8, r5, 7
        add r11, r25, r8
        lbz r7, 0x1E(r11)
        extsb r7, r7
        cmpwi r7, 1
        beq pk_pln
        lbz r7, 0x1F(r11)
        cmplwi r7, %(n)d
        bge pk_pln
        srwi r10, r7, 5
        slwi r10, r10, 2
        clrlwi r9, r7, 27
        li r6, 1
        slw r6, r6, r9
        addi r12, r1, 0x24
        lwzx r9, r12, r10
        andc r9, r9, r6
        stwx r9, r12, r10
pk_pln: addi r5, r5, 1
        cmplwi r5, 8
        blt pk_pl
        addi r12, r1, 0x24
''' % s + count_bits('r12', n, 'r5', 'pk_m') + '''
        cmplwi r5, 7
        blt pk_pick
''' + copy_words('r12', 'r31', 'pk_d') + '''
        mr r27, r5
pk_pick:
''' + far(F_NONE) + '''
        cmpwi r27, 0
        beq pk_out
        lis r10, 0x%(rh)X
        addi r10, r10, %(rl)d
        lwz r12, 0x10(r10)
        slwi r11, r12, 11
        xor r9, r12, r11
        lwz r12, 0x14(r10)
        lwz r11, 0x1C(r10)
        stw r12, 0x10(r10)
        lwz r12, 0x18(r10)
        stw r12, 0x14(r10)
        srwi r12, r11, 19
        stw r11, 0x18(r10)
        xor r11, r11, r12
        srwi r12, r9, 8
        xor r12, r9, r12
        xor r11, r11, r12
        divwu r12, r11, r27
        stw r11, 0x1C(r10)
        mullw r12, r12, r27
        subf r7, r12, r11
        li r12, -1
        li r8, 0
        li r9, 0
pk_s:   srwi r10, r9, 5
        slwi r10, r10, 2
        lwzx r11, r31, r10
        srw r11, r11, r9
        andi. r11, r11, 1
        beq pk_sn
        cmplw r8, r7
        bne pk_sk
        mr r12, r9
        b pk_found
pk_sk:  addi r8, r8, 1
pk_sn:  addi r9, r9, 1
        cmplwi r9, %(n)d
        blt pk_s
pk_found:
        clrlwi r3, r12, 24
pk_out: lmw r25, 0x4C(r1)
        lwz r0, 0x74(r1)
        mtlr r0
        addi r1, r1, 0x70
        blr

avail_clamp:                            # 0x0301CB40: the fighter helper's entry count, at most 96
        cmplwi r3, 96
        ble av_ok
        li r3, 96
av_ok:  or. r27, r3, r3
        b 0x%(av)X
stage_avail_clamp:                      # 0x0301CD0C: the stage helper's, at most 128
        cmplwi r3, 128
        ble sav_ok
        li r3, 128
sav_ok: or. r27, r3, r3
        b 0x%(sav)X
stage_ab:                               # 0x02FFB814: stwx r12, r31, r10 (r10 = the word's offset)
        lis r11, 0x%(sh)X
        addi r11, r11, %(sl)d
        lwzx r11, r11, r10
        and r12, r12, r11
        stwx r12, r31, r10
        b 0x%(ab)X
stage_cd:                               # 0x02FFB964: stwx r12, r31, r25 (cr0 of the addic. before is kept)
        lis r11, 0x%(sh)X
        addi r11, r11, %(sl)d
        lwzx r11, r11, r25
        and r12, r12, r11
        stwx r12, r31, r25
        b 0x%(cd)X
''' % dict(s, rh=ha(RNG), rl=slo(RNG), av=AVAIL_COUNT + 4, sav=STAGE_AVAIL_COUNT + 4,
           ab=STAGE_STORE_AB + 4, cd=STAGE_STORE_CD + 4))


def build(read, fighters, stages, cave, limit):
    """{address: word}: the data (pool slots, masks), the code and the hooks; read(addr) -> the view's word"""
    bad = ['0x%08X is 0x%08X, expected 0x%08X (%s)' % (a, read(a), one(a, t), t)
           for a, t in ORIGINALS.items() if read(a) != one(a, t)]
    if bad:
        raise AssertionError('random select: ' + '; '.join(bad))
    at = {'tab': cave, 'fmask': cave + 32 * SLOTS, 'smask': cave + 32 * SLOTS + 4 * WORDS}
    code = at['smask'] + 16
    a = Asm(code)
    a.asm(source(len(fighters), at))
    words = {cave + 4 * i: 0 for i in range(8 * SLOTS)}
    words.update({at['fmask'] + 4 * i: w for i, w in enumerate(mask_words(fighters, 'ui_id', WORDS))})
    words.update({at['smask'] + 4 * i: w for i, w in enumerate(mask_words(stages, 'cosmetic', 4))})
    cw = a.words()
    words.update({code + 4 * i: w for i, w in enumerate(cw)})
    assert code + 4 * len(cw) <= limit, 'random select cave full (%d bytes)' % (code + 4 * len(cw) - cave)
    pk = a.labels['pick']                 # out of a branch's reach from the pick: a far jump (r12 is free at entry)
    for i, line in enumerate(['lis r12, 0x%X' % ha(pk), 'addi r12, r12, %d' % slo(pk), 'mtctr r12', 'bctr']):
        words[PICK + 4 * i] = one(PICK + 4 * i, line)
    for site, lab in ((REFILL, 'refill'), (COUNT_AT, 'count'), (REMOVE, 'remove'),
                      (AVAIL_COUNT, 'avail_clamp'), (STAGE_AVAIL_COUNT, 'stage_avail_clamp'),
                      (STAGE_STORE_AB, 'stage_ab'), (STAGE_STORE_CD, 'stage_cd')):
        words[site] = one(site, 'b 0x%X' % a.labels[lab])
    return words, {'labels': a.labels, 'tab': at['tab'], 'count': scan_count(len(fighters))}
